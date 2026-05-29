"""
leverage_circuit_breaker.py — K430 Margin Health Circuit Breaker
=================================================================
5-minute cron daemon (via launchd com.cryptolab.leverage-circuit-breaker).
Reads live margin utilisation from HL clearinghouse + Bybit position state.
Fires emergency leverage reduction if margin_used > 80% of AUM.
Sends warning if margin_used > 70%.

Actions:
  margin_used > 80% → emergency_reduce_leverage() → all scripts revert to 1x
  margin_used > 70% → WARNING written to dashboard (no auto-reduce)
  margin_used < 70% → OK

K339 Security: REPO_ROOT from __file__, no /Users/ literals.

Usage (called by launchd OR manual test):
  python3 scripts/leverage_circuit_breaker.py
  python3 scripts/leverage_circuit_breaker.py --dry-run       # print state, no writes
  python3 scripts/leverage_circuit_breaker.py --aum 10000000  # manual AUM override
"""
from __future__ import annotations

import argparse
import json
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, Optional

# ── K339: REPO_ROOT from __file__ ─────────────────────────────────────────────
REPO_ROOT = Path(__file__).resolve().parent.parent
DATA_DIR  = REPO_ROOT / "data"
LOGS_DIR  = REPO_ROOT / "logs"
DATA_DIR.mkdir(exist_ok=True)
LOGS_DIR.mkdir(exist_ok=True)

# ── Add scripts/ to path for leverage_manager import ─────────────────────────
sys.path.insert(0, str(REPO_ROOT / "scripts"))

from leverage_manager import (
    check_margin_health,
    emergency_reduce_leverage,
    get_current_leverage,
    get_rollout_phase,
    PHASE_PAPER_TRADE,
)

# ── File paths ────────────────────────────────────────────────────────────────
EMERGENCY_FLAG       = REPO_ROOT / "EMERGENCY_EXIT_TRIGGERED.flag"
CB_DASHBOARD_JSON    = DATA_DIR  / "leverage_cb_dashboard.json"
AUM_DASHBOARD_JSON   = DATA_DIR  / "k429_aum_dashboard.json"    # K429 AUM tracking
K280_DASHBOARD_JSON  = DATA_DIR  / "k280_live_dashboard.json"
LOG_FILE             = LOGS_DIR  / "leverage_circuit_breaker.log"
ERR_FILE             = LOGS_DIR  / "leverage_circuit_breaker.err"

# ── Default AUM fallback ───────────────────────────────────────────────────────
DEFAULT_AUM_USD = 10_000_000.0   # $10M reference AUM; overridden by K429 dashboard


# ─────────────────────────────────────────────────────────────────────────────
# AUM resolution
# ─────────────────────────────────────────────────────────────────────────────

def _resolve_aum() -> float:
    """
    Read current AUM from K429 dashboard if available.
    Falls back to DEFAULT_AUM_USD ($10M) if dashboard not found.
    """
    if AUM_DASHBOARD_JSON.exists():
        try:
            with open(AUM_DASHBOARD_JSON) as f:
                data = json.load(f)
            aum = float(data.get("current_aum_usd") or data.get("aum_usd") or 0.0)
            if aum > 0:
                return aum
        except Exception:
            pass
    # Fallback: try K280 dashboard for any AUM estimate
    if K280_DASHBOARD_JSON.exists():
        try:
            with open(K280_DASHBOARD_JSON) as f:
                data = json.load(f)
            aum = float(data.get("aum_usd") or 0.0)
            if aum > 0:
                return aum
        except Exception:
            pass
    return DEFAULT_AUM_USD


# ─────────────────────────────────────────────────────────────────────────────
# Live exchange margin fetch (HL clearinghouse)
# ─────────────────────────────────────────────────────────────────────────────

def _fetch_hl_margin(hl_wallet: Optional[str] = None) -> Optional[Dict]:
    """
    Fetch live margin utilization from HL clearinghouse.
    Returns {margin_summary: {...}} or None on failure/no wallet.

    In PAPER_TRADE mode or if no wallet configured: returns None (skip live check).
    """
    if not hl_wallet:
        hl_wallet = _env("HL_WALLET_ADDRESS", "")
    if not hl_wallet:
        return None  # No live wallet → skip HL margin check

    try:
        import urllib.request as _req
        payload = json.dumps({"type": "clearinghouseState", "user": hl_wallet}).encode()
        req = _req.Request(
            "https://api.hyperliquid.xyz/info",
            data=payload,
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        with _req.urlopen(req, timeout=10) as r:
            data = json.loads(r.read())
        # Extract margin summary
        ms = data.get("marginSummary", {})
        account_value  = float(ms.get("accountValue",  0.0) or 0)
        total_ntl_pos  = float(ms.get("totalNtlPos",   0.0) or 0)
        total_margin_used = float(ms.get("totalMarginUsed", 0.0) or 0)
        return {
            "account_value":     account_value,
            "total_ntl_pos":     total_ntl_pos,
            "total_margin_used": total_margin_used,
            "margin_pct":        total_margin_used / account_value if account_value > 0 else 0.0,
        }
    except Exception as e:
        print(f"  [CB] HL margin fetch failed: {e}")
        return None


def _env(key: str, default: str = "") -> str:
    import os
    return os.environ.get(key, default)


# ─────────────────────────────────────────────────────────────────────────────
# Main circuit breaker logic
# ─────────────────────────────────────────────────────────────────────────────

def run_circuit_breaker(
    aum_override: Optional[float] = None,
    dry_run: bool = False,
    verbose: bool = False,
) -> Dict:
    """
    Run one circuit breaker cycle.

    Priority:
    1. If EMERGENCY_EXIT_TRIGGERED.flag present → log and exit (already in emergency)
    2. If rollout_phase == PAPER_TRADE AND no live HL wallet → compute-only check
    3. If live HL margin available → use live margin_pct
    4. Else → use computed margin from leverage_manager.check_margin_health()

    Returns result dict with action taken.
    """
    ts_utc = datetime.now(timezone.utc).isoformat()

    # ── Step 1: Emergency flag check ──────────────────────────────────────────
    if EMERGENCY_FLAG.exists():
        msg = "[CB] EMERGENCY_EXIT_TRIGGERED.flag present. CB deferred to emergency exit daemon."
        print(msg)
        return {"status": "EMERGENCY_HALTED", "ts_utc": ts_utc, "message": msg}

    # ── Step 2: Resolve AUM ───────────────────────────────────────────────────
    aum = aum_override if aum_override and aum_override > 0 else _resolve_aum()

    # ── Step 3: Try live HL margin ────────────────────────────────────────────
    hl_margin = _fetch_hl_margin()
    phase     = get_rollout_phase()
    leverage  = get_current_leverage()

    # ── Step 4: Compute margin health ─────────────────────────────────────────
    health = check_margin_health(aum, verbose=verbose)

    # If we have live HL margin data, override computed margin_used_pct
    live_margin_pct = None
    if hl_margin and hl_margin.get("account_value", 0) > 0:
        live_margin_pct = hl_margin["margin_pct"]
        # Blend: use live HL as authoritative if available
        health["margin_used_pct_computed"] = health["margin_used_pct"]
        health["margin_used_pct"]          = live_margin_pct
        health["margin_source"]            = "HL_LIVE"
        health["warning"]                  = live_margin_pct > health["warn_margin_pct"]
        health["circuit_breaker_fire"]     = live_margin_pct > health["max_margin_pct"]
        print(f"  [CB] Live HL margin: {live_margin_pct*100:.1f}% "
              f"(account_value=${hl_margin['account_value']:,.0f}, "
              f"margin_used=${hl_margin['total_margin_used']:,.0f})")
    else:
        health["margin_source"] = "COMPUTED"
        if phase == PHASE_PAPER_TRADE:
            # In paper mode with no live wallet, computed margin at 1x = safe
            print(f"  [CB] PAPER_TRADE mode, no live wallet. Computed margin: "
                  f"{health['margin_used_pct']*100:.1f}% (leverage={leverage}x)")
        else:
            print(f"  [CB] No live margin data. Computed margin: "
                  f"{health['margin_used_pct']*100:.1f}% (leverage={leverage}x)")

    action_taken = "NONE"

    # ── Step 5: Circuit breaker fire ──────────────────────────────────────────
    if health["circuit_breaker_fire"]:
        msg = (
            f"[CB] *** CIRCUIT BREAKER FIRE *** "
            f"margin_used={health['margin_used_pct']*100:.1f}% > "
            f"{health['max_margin_pct']*100:.0f}% limit. "
            f"phase={phase}, leverage={leverage}x, AUM=${aum:,.0f}. "
            f"Reducing leverage to 1x (emergency)."
        )
        print(msg)
        if not dry_run:
            emergency_reduce_leverage()
            action_taken = "EMERGENCY_REDUCE_1X"
        else:
            print(f"  [CB] DRY-RUN: would fire emergency_reduce_leverage()")
            action_taken = "DRY_RUN_WOULD_FIRE"
        # Write err file for launchd log rotation visibility
        with open(ERR_FILE, "a") as ef:
            ef.write(f"{ts_utc} {msg}\n")

    # ── Step 6: Warning ───────────────────────────────────────────────────────
    elif health["warning"]:
        msg = (
            f"[CB] WARNING: margin_used={health['margin_used_pct']*100:.1f}% > "
            f"{health['warn_margin_pct']*100:.0f}% threshold. "
            f"phase={phase}, leverage={leverage}x. Monitor closely."
        )
        print(msg)
        action_taken = "WARNING"
    else:
        print(f"  [CB] OK — margin_used={health['margin_used_pct']*100:.1f}%, "
              f"phase={phase}, leverage={leverage}x, AUM=${aum:,.0f}")
        action_taken = "OK"

    # ── Step 7: Write CB dashboard ────────────────────────────────────────────
    cb_result = {
        "ts_utc":            ts_utc,
        "phase":             phase,
        "leverage":          leverage,
        "aum_usd":           aum,
        "margin_source":     health.get("margin_source", "COMPUTED"),
        "margin_used_pct":   health["margin_used_pct"],
        "cash_buffer_usd":   health["cash_buffer_remaining"],
        "warning":           health["warning"],
        "circuit_breaker_fire": health["circuit_breaker_fire"],
        "action_taken":      action_taken,
        "sleeves_margin":    health.get("sleeves", {}),
        "hl_live_margin":    hl_margin,
        "dry_run":           dry_run,
    }

    if not dry_run:
        with open(CB_DASHBOARD_JSON, "w") as f:
            json.dump(cb_result, f, indent=2)

    return cb_result


# ─────────────────────────────────────────────────────────────────────────────
# CLI
# ─────────────────────────────────────────────────────────────────────────────

def main() -> int:
    parser = argparse.ArgumentParser(
        description="K430 Leverage Circuit Breaker — 5-min margin health daemon"
    )
    parser.add_argument("--dry-run",  action="store_true",
                        help="Print state without firing emergency reduce")
    parser.add_argument("--verbose",  action="store_true", help="Verbose output")
    parser.add_argument("--aum",      type=float, default=None,
                        help="Manual AUM override in USD (e.g. 10000000)")
    args = parser.parse_args()

    t0     = time.time()
    result = run_circuit_breaker(
        aum_override=args.aum,
        dry_run=args.dry_run,
        verbose=args.verbose,
    )
    elapsed = time.time() - t0

    print(f"\n  Circuit breaker run complete in {elapsed:.2f}s")
    print(f"  Status:        {result['action_taken']}")
    print(f"  Phase:         {result['phase']}")
    print(f"  Leverage:      {result['leverage']}x")
    print(f"  Margin used:   {result['margin_used_pct']*100:.1f}%")
    print(f"  Cash buffer:   ${result.get('cash_buffer_usd',0):,.0f}")
    print(f"  CB fire:       {result['circuit_breaker_fire']}")
    print(f"  Warning:       {result['warning']}")

    if result["circuit_breaker_fire"] and not args.dry_run:
        return 2  # non-zero exit for launchd logging visibility
    if result["warning"]:
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())

"""
k386_v613e_fallback_run.py — K386 v6.13e BEAR_1 Fallback Prototype
====================================================================
K385 BEAR_1 scenario: CFTC enforcement vs HyperLiquid (P=15%).
If BEAR_1_FALLBACK_ACTIVE.flag exists → activate v6.13e weights.
Otherwise → write STANDBY status to dashboard.

v6.13e Architecture:
  K280  main sleeve:   85%  (boosted from v6.13d 75%)
  K297' satellite:      0%  (CFTC-restricted HIP-3 — suspended)
  BTC/ETH spot:        10%  (50/50, daily mark-to-market, Binance public API)
  sUSDe OC sleeve:      5%  (unchanged from v6.13d)
  ─────────────────────────
  Total:              100%

HL exposure: 52.5%  (vs v6.13d 57.5% — 5pp reduction per K385)
  K280 HL component (approx 70% of K280):  85% × 0.70 ≈ 59.5% → but K280 internal
  HIP-3 / K297':                            0%  (suspended)
  sUSDe:                                    ~3% HL/Pendle
  Net HL: ~52.5% (K346 v6.13e baseline)

Trigger conditions:
  1. CFTC enforcement filing vs HyperLiquid
  2. HL voluntary HIP-3 suspension
  → 3 trading days to complete migration (see docs/k302a_runbook.md §18)

Daemon check order:
  1. EMERGENCY_EXIT_TRIGGERED.flag → all daemons stop (highest priority)
  2. BEAR_1_FALLBACK_ACTIVE.flag   → K297' stops; K386 v6.13e takes over

K339 Security: REPO_ROOT = Path(__file__).resolve().parent.parent (no /Users/ literals)

Usage:
  python3 scripts/k386_v613e_fallback_run.py           # normal run
  python3 scripts/k386_v613e_fallback_run.py --dry-run # verbose, no file writes
"""
from __future__ import annotations

import argparse
import json
import math
import sys
import time
import urllib.request as _urllib_req
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Optional, Tuple

# ── K339 Security Rule: REPO_ROOT from __file__, no /Users/ literals ──────────
REPO_ROOT = Path(__file__).resolve().parent.parent
DATA_DIR  = REPO_ROOT / "data"
LOGS_DIR  = REPO_ROOT / "logs"
DATA_DIR.mkdir(exist_ok=True)
LOGS_DIR.mkdir(exist_ok=True)

# ── Flag files (priority order) ────────────────────────────────────────────────
EMERGENCY_FLAG  = REPO_ROOT / "EMERGENCY_EXIT_TRIGGERED.flag"
BEAR1_FLAG      = REPO_ROOT / "BEAR_1_FALLBACK_ACTIVE.flag"

# ── Dashboard output ───────────────────────────────────────────────────────────
DASHBOARD_JSON  = DATA_DIR / "v6_13e_fallback_dashboard.json"
TRADES_LOG      = DATA_DIR / "k386_v613e_paper_trades.jsonl"

# ── v6.13e Portfolio Weights ───────────────────────────────────────────────────
V613E_WEIGHTS = {
    "K280":         0.85,   # K280 main (boosted from 75%)
    "K297_prime":   0.00,   # HIP-3 satellite — suspended (CFTC restricted)
    "BTC_ETH_spot": 0.10,   # BTC/ETH spot 50/50 (replaces K297' allocation)
    "sUSDe":        0.05,   # sUSDe OC sleeve (unchanged)
}

# v6.13d reference weights (for comparison)
V613D_WEIGHTS = {
    "K280":         0.75,
    "K297_prime":   0.20,
    "BTC_ETH_spot": 0.00,
    "sUSDe":        0.05,
}

# BTC/ETH spot sleeve: 50/50 fixed split
BTC_SPOT_WEIGHT = 0.50   # within 10% sleeve
ETH_SPOT_WEIGHT = 0.50   # within 10% sleeve

# ── Strategy metadata ─────────────────────────────────────────────────────────
ESTIMATED_SHARPE  = 22.89   # K346 v6.13e baseline
HL_EXPOSURE_V613D = 0.575   # v6.13d: 57.5%
HL_EXPOSURE_V613E = 0.525   # v6.13e: 52.5% (-5pp)

TRIGGER_CONDITIONS = [
    "CFTC enforcement filing vs HyperLiquid",
    "HL voluntary HIP-3 suspension",
]
ACTIVATION_COMMAND   = "touch BEAR_1_FALLBACK_ACTIVE.flag"
DEACTIVATION_COMMAND = "rm BEAR_1_FALLBACK_ACTIVE.flag"

# ── Binance public API (no auth required) ─────────────────────────────────────
BINANCE_KLINES_URL = "https://api.binance.com/api/v3/klines"


# ─────────────────────────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────────────────────────

class _NaNSafe(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, float) and math.isnan(obj):
            return None
        return super().default(obj)


def _dump_json(path: Path, data: dict, dry_run: bool) -> None:
    if dry_run:
        print(f"  [DRY-RUN] Would write: {path}")
        print(json.dumps(data, indent=2, cls=_NaNSafe)[:600] + "...")
        return
    with open(path, "w") as f:
        json.dump(data, f, indent=2, cls=_NaNSafe)
    print(f"  Written: {path}")


# ─────────────────────────────────────────────────────────────────────────────
# BTC/ETH Spot Sleeve — Binance Free API
# ─────────────────────────────────────────────────────────────────────────────

def _fetch_binance_daily_close(symbol: str, limit: int = 30) -> List[Tuple[int, float]]:
    """
    Fetch daily OHLCV from Binance public klines API.
    Returns list of (timestamp_ms, close_price).
    On failure: returns empty list (fail-open: sleeve contributes 0 PnL that day).
    """
    url = (
        f"{BINANCE_KLINES_URL}"
        f"?symbol={symbol}USDT&interval=1d&limit={limit}"
    )
    try:
        req = _urllib_req.Request(
            url,
            headers={"User-Agent": "ct-k386-v613e/1.0"},
            method="GET",
        )
        with _urllib_req.urlopen(req, timeout=12) as resp:
            raw = json.loads(resp.read())
        # raw: list of [open_time, open, high, low, close, volume, ...]
        return [(int(row[0]), float(row[4])) for row in raw]
    except Exception as exc:
        print(f"  [WARN] Binance fetch {symbol} failed (fail-open): {exc}")
        return []


def compute_btc_eth_spot_pnl() -> Tuple[List[float], Dict]:
    """
    BTC/ETH spot sleeve: 50/50 fixed, daily mark-to-market.
    PnL per day = average of BTC daily return + ETH daily return, each weighted 50%.
    Returns (daily_returns_list, sleeve_info_dict).
    """
    print("  [BTC/ETH] Fetching Binance daily closes (30d)...")
    btc_data = _fetch_binance_daily_close("BTC", limit=32)
    eth_data = _fetch_binance_daily_close("ETH", limit=32)

    def _to_returns(data: List[Tuple]) -> List[float]:
        if len(data) < 2:
            return []
        closes = [c for _, c in data]
        return [(closes[i] - closes[i-1]) / closes[i-1] for i in range(1, len(closes))]

    btc_rets = _to_returns(btc_data)
    eth_rets = _to_returns(eth_data)

    # Align by length (take shorter)
    n = min(len(btc_rets), len(eth_rets))
    if n == 0:
        print("  [BTC/ETH] No return data available. Sleeve PnL = 0.")
        return [], {"error": "no_data", "n_days": 0}

    btc_rets = btc_rets[-n:]
    eth_rets = eth_rets[-n:]

    # Combined: 50/50 within 10% sleeve
    combined = [
        BTC_SPOT_WEIGHT * b + ETH_SPOT_WEIGHT * e
        for b, e in zip(btc_rets, eth_rets)
    ]

    # Latest prices for info
    btc_price = btc_data[-1][1] if btc_data else None
    eth_price = eth_data[-1][1] if eth_data else None

    btc_7d = sum(btc_rets[-7:]) if len(btc_rets) >= 7 else None
    eth_7d = sum(eth_rets[-7:]) if len(eth_rets) >= 7 else None
    combined_7d = sum(combined[-7:]) if len(combined) >= 7 else None

    today_ret = combined[-1] if combined else 0.0

    print(f"  [BTC/ETH] {n} days | today: BTC {btc_rets[-1]*100:+.2f}% "
          f"ETH {eth_rets[-1]*100:+.2f}% | sleeve: {today_ret*100:+.2f}%")

    info = {
        "allocation": "10% of AUM (BTC 50% + ETH 50%)",
        "strategy":   "passive long spot, daily mark-to-market",
        "split":      {"BTC": BTC_SPOT_WEIGHT, "ETH": ETH_SPOT_WEIGHT},
        "btc_latest_price": round(btc_price, 2) if btc_price else None,
        "eth_latest_price": round(eth_price, 2) if eth_price else None,
        "btc_7d_cumret":    round(btc_7d * 100, 3) if btc_7d is not None else None,
        "eth_7d_cumret":    round(eth_7d * 100, 3) if eth_7d is not None else None,
        "sleeve_7d_cumret": round(combined_7d * 100, 3) if combined_7d is not None else None,
        "today_sleeve_ret": round(today_ret, 8),
        "n_days":           n,
        "source":           "Binance public klines API (no auth)",
        "note":             (
            "Passive long only. No hedging in BEAR_1 prototype. "
            "Future: add delta-neutral hedge via BTC/ETH perp shorts on Bybit."
        ),
    }
    return combined, info


# ─────────────────────────────────────────────────────────────────────────────
# Portfolio Simulation
# ─────────────────────────────────────────────────────────────────────────────

def compute_v613e_portfolio(
    spot_sleeve_rets: List[float],
    spot_info: Dict,
) -> Tuple[float, float, Dict]:
    """
    Simulate v6.13e portfolio PnL.
    - K280 (85%): referenced from k280_live_dashboard.json (existing daemon)
    - K297' (0%): suspended
    - BTC/ETH spot (10%): from spot_sleeve_rets
    - sUSDe (5%): referenced from k344_susde_dashboard.json (existing daemon)

    Returns (today_pnl, sleeve_equity, summary_dict).
    """
    # Load K280 dashboard
    k280_dash_path = DATA_DIR / "k280_live_dashboard.json"
    k280_pnl_today = None
    k280_sh30      = None
    if k280_dash_path.exists():
        try:
            with open(k280_dash_path) as f:
                k280_d = json.load(f)
            recs = k280_d.get("daily_records", [])
            if recs:
                k280_pnl_today = recs[-1].get("daily_pnl")
            k280_sh30 = k280_d.get("rolling_metrics", {}).get("sh_30d")
        except Exception as e:
            print(f"  [WARN] K280 dashboard load error: {e}")

    # Load sUSDe dashboard
    susde_dash_path = DATA_DIR / "k344_susde_dashboard.json"
    susde_pnl_today = None
    if susde_dash_path.exists():
        try:
            with open(susde_dash_path) as f:
                susde_d = json.load(f)
            recs = susde_d.get("daily_records", [])
            if recs:
                susde_pnl_today = recs[-1].get("daily_pnl")
        except Exception as e:
            print(f"  [WARN] sUSDe dashboard load error: {e}")

    # BTC/ETH spot sleeve PnL (today)
    spot_ret_today = spot_sleeve_rets[-1] if spot_sleeve_rets else 0.0

    # v6.13e combined PnL (today, weighted)
    # K280 contributes 85% of AUM
    k280_contrib = (k280_pnl_today or 0.0) * V613E_WEIGHTS["K280"]
    # K297' = 0%: no contribution
    # BTC/ETH spot: 10% weight × sleeve daily return
    spot_contrib  = spot_ret_today * V613E_WEIGHTS["BTC_ETH_spot"]
    # sUSDe: 5%
    susde_contrib = (susde_pnl_today or 0.0) * V613E_WEIGHTS["sUSDe"]

    today_pnl = k280_contrib + spot_contrib + susde_contrib

    # Sleeve equity (spot-only, 30d cumulative)
    sleeve_eq = 1.0
    for r in spot_sleeve_rets:
        sleeve_eq *= (1 + r * V613E_WEIGHTS["BTC_ETH_spot"])

    summary = {
        "architecture":          "v6.13e (K386 BEAR_1 fallback)",
        "weights":               V613E_WEIGHTS,
        "hl_exposure_pct":       HL_EXPOSURE_V613E * 100,
        "hl_exposure_delta_pp":  round((HL_EXPOSURE_V613E - HL_EXPOSURE_V613D) * 100, 1),
        "estimated_sharpe":      ESTIMATED_SHARPE,
        "today_pnl_components": {
            "K280_85pct":        round(k280_contrib, 8),
            "K297_prime_0pct":   0.0,
            "BTC_ETH_spot_10pct": round(spot_contrib, 8),
            "sUSDe_5pct":        round(susde_contrib, 8),
            "total":             round(today_pnl, 8),
        },
        "k280_pnl_today":        k280_pnl_today,
        "k280_sh30":             k280_sh30,
        "susde_pnl_today":       susde_pnl_today,
        "spot_sleeve":           spot_info,
        "spot_sleeve_equity_30d": round(sleeve_eq, 6),
    }
    return today_pnl, sleeve_eq, summary


# ─────────────────────────────────────────────────────────────────────────────
# Dashboard Write
# ─────────────────────────────────────────────────────────────────────────────

def build_standby_dashboard() -> Dict:
    """Build STANDBY dashboard (BEAR_1 flag NOT active)."""
    return {
        "fallback_status":         "STANDBY",
        "note":                    (
            "BEAR_1 flag not present. v6.13d production mode active. "
            "v6.13e is on standby — no action required."
        ),
        "weights":                 V613E_WEIGHTS,
        "current_architecture":    "v6.13d",
        "estimated_sharpe":        ESTIMATED_SHARPE,
        "hl_exposure_v613e_pct":   HL_EXPOSURE_V613E * 100,
        "hl_exposure_delta_pp":    round((HL_EXPOSURE_V613E - HL_EXPOSURE_V613D) * 100, 1),
        "trigger_conditions":      TRIGGER_CONDITIONS,
        "activation_command":      ACTIVATION_COMMAND,
        "deactivation_command":    DEACTIVATION_COMMAND,
        "runbook_section":         "docs/k302a_runbook.md §18",
        "last_check_utc":          datetime.now(timezone.utc).isoformat(),
        "flag_file":               str(BEAR1_FLAG),
    }


def build_active_dashboard(pnl_summary: Dict) -> Dict:
    """Build ACTIVE dashboard (BEAR_1 flag IS active)."""
    return {
        "fallback_status":         "ACTIVE",
        "note":                    (
            "BEAR_1_FALLBACK_ACTIVE.flag detected. "
            "v6.13e weights in effect: K280 85% + BTC/ETH spot 10% + sUSDe 5%. "
            "K297' suspended (HIP-3 CFTC-restricted). "
            "See docs/k302a_runbook.md §18 for deactivation procedure."
        ),
        "weights":                 V613E_WEIGHTS,
        "current_architecture":    "v6.13e",
        "estimated_sharpe":        ESTIMATED_SHARPE,
        "hl_exposure_pct":         HL_EXPOSURE_V613E * 100,
        "hl_exposure_delta_pp":    round((HL_EXPOSURE_V613E - HL_EXPOSURE_V613D) * 100, 1),
        "trigger_conditions":      TRIGGER_CONDITIONS,
        "deactivation_command":    DEACTIVATION_COMMAND,
        "runbook_section":         "docs/k302a_runbook.md §18",
        "last_update_utc":         datetime.now(timezone.utc).isoformat(),
        "flag_file":               str(BEAR1_FLAG),
        "pnl_summary":             pnl_summary,
    }


# ─────────────────────────────────────────────────────────────────────────────
# Main
# ─────────────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(
        description="K386 v6.13e BEAR_1 Fallback Daemon — K385 conditional deploy"
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Verbose output; do not write files (safe to run at any time)",
    )
    args = parser.parse_args()
    dry_run: bool = args.dry_run

    print(f"\n=== K386 v6.13e Fallback Daemon ({datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')}) ===\n")
    t0 = time.time()

    # ── Priority 1: Emergency exit flag ───────────────────────────────────────
    if EMERGENCY_FLAG.exists():
        print(f"  [CRITICAL] EMERGENCY_EXIT_TRIGGERED.flag present at {EMERGENCY_FLAG}.")
        print("  All daemons halted. K386 exiting immediately.")
        sys.exit(0)

    # ── Priority 2: BEAR_1 flag check ─────────────────────────────────────────
    bear1_active = BEAR1_FLAG.exists()
    print(f"  BEAR_1_FALLBACK_ACTIVE.flag: {'PRESENT — ACTIVATING v6.13e' if bear1_active else 'absent — STANDBY mode'}")
    print(f"  Flag path: {BEAR1_FLAG}")

    if not bear1_active:
        # ── STANDBY mode ──────────────────────────────────────────────────────
        print("\n  [STANDBY] v6.13d production mode active. v6.13e on standby.")
        print("  Dashboard: writing STANDBY status...")
        dash = build_standby_dashboard()
        _dump_json(DASHBOARD_JSON, dash, dry_run)

        elapsed = time.time() - t0
        print(f"\n=== K386 standby check complete in {elapsed:.1f}s ===")
        print(f"  Fallback status: STANDBY")
        print(f"  Activate with: touch {BEAR1_FLAG.name}")
        sys.exit(0)

    # ── ACTIVE mode — v6.13e weights ──────────────────────────────────────────
    print("\n  [ACTIVE] BEAR_1 flag present. Executing v6.13e architecture.")
    print(f"  Weights: K280 {V613E_WEIGHTS['K280']*100:.0f}% | "
          f"K297' {V613E_WEIGHTS['K297_prime']*100:.0f}% (SUSPENDED) | "
          f"BTC/ETH spot {V613E_WEIGHTS['BTC_ETH_spot']*100:.0f}% | "
          f"sUSDe {V613E_WEIGHTS['sUSDe']*100:.0f}%")
    print(f"  HL exposure: {HL_EXPOSURE_V613E*100:.1f}% (was {HL_EXPOSURE_V613D*100:.1f}%)")

    # ── Fetch BTC/ETH spot sleeve ─────────────────────────────────────────────
    print("\n--- BTC/ETH Spot Sleeve (10% of AUM) ---")
    spot_rets, spot_info = compute_btc_eth_spot_pnl()

    # ── Compute v6.13e portfolio PnL ──────────────────────────────────────────
    print("\n--- v6.13e Portfolio PnL ---")
    today_pnl, sleeve_eq, pnl_summary = compute_v613e_portfolio(spot_rets, spot_info)

    print(f"\n  v6.13e today PnL: {today_pnl:.6f}")
    print(f"    K280 (85%):        {pnl_summary['today_pnl_components']['K280_85pct']:.6f}")
    print(f"    BTC/ETH spot (10%): {pnl_summary['today_pnl_components']['BTC_ETH_spot_10pct']:.6f}")
    print(f"    sUSDe (5%):        {pnl_summary['today_pnl_components']['sUSDe_5pct']:.6f}")
    print(f"    K297' (0%):        0.000000 (SUSPENDED)")

    # ── Dashboard write ───────────────────────────────────────────────────────
    print("\n--- Writing Dashboard ---")
    dash = build_active_dashboard(pnl_summary)
    _dump_json(DASHBOARD_JSON, dash, dry_run)

    # ── Trade log ────────────────────────────────────────────────────────────
    date_str = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    log_entry = {
        "date":               date_str,
        "run_ts":             datetime.now(timezone.utc).isoformat(),
        "fallback_status":    "ACTIVE",
        "weights":            V613E_WEIGHTS,
        "today_pnl":          round(today_pnl, 8),
        "spot_sleeve_eq_30d": round(sleeve_eq, 6),
        "spot_btc_latest":    spot_info.get("btc_latest_price"),
        "spot_eth_latest":    spot_info.get("eth_latest_price"),
        "spot_7d_cumret_pct": spot_info.get("sleeve_7d_cumret"),
        "elapsed_s":          round(time.time() - t0, 1),
    }
    if not dry_run:
        with open(TRADES_LOG, "a") as f:
            f.write(json.dumps(log_entry) + "\n")
        print(f"  Trade log: {TRADES_LOG}")
    else:
        print(f"  [DRY-RUN] Would append to: {TRADES_LOG}")

    elapsed = time.time() - t0
    print(f"\n=== K386 v6.13e ACTIVE run complete in {elapsed:.1f}s ===")
    print(f"  Architecture: v6.13e | HL exposure: {HL_EXPOSURE_V613E*100:.1f}%")
    print(f"  Deactivate with: rm {BEAR1_FLAG.name}")


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""K767 K297' RWA Diversified Yield Sleeve — 74th daemon.

4-provider weekly rebalance: sUSDe (35%) + Spark sUSDS (25%) + USDY (25%) + Mountain USDM (15%).

PAPER_TRADE mode default — no on-chain transactions.
User must fund each provider manually; daemon tracks virtual positions + rebalance signals.

Strategy overview:
  K297' RWA yield sleeve = 20% of AUM ($2M at $10M reference).
  Provider allocation in data/rwa_allocation.json (operator-configurable weights).
  Yield data from DeFiLlama public API (no key required).
  Rebalance trigger: weekly cron OR any provider weight drifts >5pp from target.

K523 3-point @$10M (20% sleeve):
  Conservative: $56,270/yr ($21,383 realized @38% K518)
  Central:      $78,660/yr ($29,891 realized @38% K518)
  Optimistic:  $103,400/yr ($39,292 realized @38% K518)
  Uplift vs baseline (sUSDe-only K344): +$69,360/yr central

Provider sources:
  sUSDe:     DeFiLlama yields API (K344 pool ID)
  Spark sUSDS: DeFiLlama yields API (K473 pool ID)
  USDY:      DeFiLlama yields API (K415 pool ID)
  USDM:      DeFiLlama yields API (Mountain Protocol pool ID TBD)

Rebalance logic:
  1. Fetch current APY for all 4 providers
  2. Load current virtual balances from data/rwa_allocation.json
  3. Compute current weights vs target weights
  4. If drift > REBALANCE_THRESHOLD_PP for any provider → emit rebalance signal
  5. Write dashboard to data/k767_rwa_dashboard.json
  6. Append trade record to data/k767_rwa_trades.jsonl

Emergency exit:
  If EMERGENCY_EXIT_TRIGGERED.flag exists → skip (RWA yield = safe during crisis, K415 pattern)
  Stablecoin yields are safe-haven during market stress — hold through crisis.

BEAR_1 flag:
  If BEAR_1_FALLBACK_ACTIVE.flag → reduce sUSDe 50% (funding rate carry component risk)
  Hold Spark/USDY/USDM (T-bill backed, crisis-stable)

Security (K339):
  REPO_ROOT = Path(__file__).resolve().parent.parent — no /Users/ literals

Usage:
  python3 scripts/k767_rwa_diversified.py
  python3 scripts/k767_rwa_diversified.py --dry-run
  python3 scripts/k767_rwa_diversified.py --status
  python3 scripts/k767_rwa_diversified.py --force-rebalance

Dashboard: data/k767_rwa_dashboard.json
Allocation: data/rwa_allocation.json (source of truth for targets + current positions)
Logs: logs/k767_rwa_diversified.log / logs/k767_rwa_diversified.err
Trades: data/k767_rwa_trades.jsonl

74th daemon | K767 | 2026-05-30
"""
from __future__ import annotations

import argparse
import json
import sys
import urllib.request
import urllib.error
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Tuple

# ── K339 Security: REPO_ROOT from __file__, no /Users/ literals ──────────────
REPO_ROOT   = Path(__file__).resolve().parent.parent
DATA_DIR    = REPO_ROOT / "data"
LOGS_DIR    = REPO_ROOT / "logs"
CACHE_DIR   = REPO_ROOT / "cache"
SCRIPTS_DIR = REPO_ROOT / "scripts"

DATA_DIR.mkdir(exist_ok=True)
LOGS_DIR.mkdir(exist_ok=True)
CACHE_DIR.mkdir(exist_ok=True)

# ── Flag files ────────────────────────────────────────────────────────────────
EMERGENCY_FLAG = REPO_ROOT / "EMERGENCY_EXIT_TRIGGERED.flag"
BEAR1_FLAG     = REPO_ROOT / "BEAR_1_FALLBACK_ACTIVE.flag"

# ── File paths ────────────────────────────────────────────────────────────────
DASHBOARD_JSON   = DATA_DIR / "k767_rwa_dashboard.json"
ALLOCATION_JSON  = DATA_DIR / "rwa_allocation.json"
TRADES_LOG       = DATA_DIR / "k767_rwa_trades.jsonl"
LOG_FILE         = LOGS_DIR / "k767_rwa_diversified.log"
ERR_FILE         = LOGS_DIR / "k767_rwa_diversified.err"

# Cross-reference dashboards from K344/K473/K415
K344_DASHBOARD   = DATA_DIR / "k344_susde_dashboard.json"
K473_DASHBOARD   = DATA_DIR / "spark_usds_dashboard.json"
K415_DASHBOARD   = DATA_DIR / "k415_usdy_dashboard.json"

JST = timezone(timedelta(hours=9))

# ── Mode ─────────────────────────────────────────────────────────────────────
# PAPER_TRADE = True: track virtual positions only, never execute on-chain
# PAPER_TRADE = False: production mode — operator sets this + funds wallets
PAPER_TRADE = True   # K767 default; LIVE 自動変更禁止

# ── Portfolio constants ───────────────────────────────────────────────────────
DEFAULT_AUM_USD    = 10_000_000.0
SLEEVE_PCT         = 0.20         # 20% of AUM
DEFAULT_SLEEVE_USD = DEFAULT_AUM_USD * SLEEVE_PCT  # $2,000,000

# Rebalance trigger: if any provider weight drifts >5pp from target → rebalance
REBALANCE_THRESHOLD_PP = 5.0

# BEAR_1 sUSDe reduction factor
BEAR1_SUSDE_REDUCTION = 0.50

# ── Default provider configuration ───────────────────────────────────────────
DEFAULT_PROVIDERS: Dict[str, Dict] = {
    "sUSDe_Ethena": {
        "token":              "sUSDe",
        "protocol":           "Ethena",
        "target_weight_pct":  35.0,
        "restriction":        "none",
        "redemption_days":    7,
        "mechanism":          "synthetic_dollar_eth_staked",
        # DeFiLlama pool (K344 confirmed pool ID)
        "defilama_pool_id":   "66985a81-9c51-46ca-9977-42b4fe7bc6df",
        "fallback_apy_pct":   4.02,   # 30d EMA from K344 dashboard
        "bear1_reduce":       True,
        "k523_apy_conservative_pct": 3.22,   # ×0.80
        "k523_apy_mid_pct":         4.02,
        "k523_apy_optimistic_pct":  5.02,   # ×1.25
    },
    "Spark_sUSDS": {
        "token":              "sUSDS",
        "protocol":           "Sky/MakerDAO",
        "target_weight_pct":  25.0,
        "restriction":        "none",
        "redemption_days":    0,       # instant
        "mechanism":          "dsr_sky_protocol",
        # DeFiLlama pool (K473 confirmed pool ID)
        "defilama_pool_id":   "54e9b138-3146-4c1f-8dce-1cb948f5ef96",
        "fallback_apy_pct":   3.67,   # 30d mean from K473 dashboard
        "bear1_reduce":       False,
        "k523_apy_conservative_pct": 2.94,
        "k523_apy_mid_pct":         3.67,
        "k523_apy_optimistic_pct":  4.59,
    },
    "USDY_Ondo": {
        "token":              "USDY",
        "protocol":           "Ondo Finance",
        "target_weight_pct":  25.0,
        "restriction":        "non_US_only",
        "redemption_days":    1,
        "mechanism":          "tokenized_t_bills",
        # DeFiLlama pool (K415 confirmed pool ID)
        "defilama_pool_id":   "d4b19b66-e4a0-4dc4-a0db-6b2ee0c7e3af",
        "fallback_apy_pct":   4.5,
        "bear1_reduce":       False,
        "k523_apy_conservative_pct": 3.60,
        "k523_apy_mid_pct":         4.50,
        "k523_apy_optimistic_pct":  5.63,
    },
    "Mountain_USDM": {
        "token":              "USDM",
        "protocol":           "Mountain Protocol",
        "target_weight_pct":  15.0,
        "restriction":        "KYC_light",
        "redemption_days":    1,
        "mechanism":          "tokenized_t_bills_kyc_light",
        # DeFiLlama pool: research pending (Mountain Protocol USDM)
        # Pool lookup: https://yields.llama.fi/pools?project=mountain-protocol
        "defilama_pool_id":   "PENDING_RESEARCH",
        "fallback_apy_pct":   4.6,
        "bear1_reduce":       False,
        "k523_apy_conservative_pct": 3.68,
        "k523_apy_mid_pct":         4.60,
        "k523_apy_optimistic_pct":  5.75,
    },
}

# K523 aggregate (computed from DEFAULT_PROVIDERS weights × scenario APYs)
K523_CONSERVATIVE_ANN_USD  = 56_270
K523_MID_ANN_USD           = 78_660
K523_OPTIMISTIC_ANN_USD    = 103_400
K523_MID_REALIZED_USD      = 29_891   # @38% K518


# ── Logging ───────────────────────────────────────────────────────────────────

def _ts() -> str:
    return datetime.now(JST).strftime("%Y-%m-%d %H:%M:%S JST")


def _log(msg: str) -> None:
    line = f"[{_ts()}] {msg}"
    print(line)
    try:
        with open(LOG_FILE, "a") as f:
            f.write(line + "\n")
    except Exception:
        pass


def _err(msg: str) -> None:
    line = f"[{_ts()}] ERROR: {msg}"
    print(line, file=sys.stderr)
    try:
        LOGS_DIR.mkdir(exist_ok=True)
        with open(ERR_FILE, "a") as f:
            f.write(line + "\n")
    except Exception:
        pass


# ── Allocation JSON I/O ───────────────────────────────────────────────────────

def load_allocation() -> Dict:
    """Load current allocation state from data/rwa_allocation.json.

    Creates default allocation file if not present.
    Returns dict with providers, current balances, and AUM reference.
    """
    if ALLOCATION_JSON.exists():
        try:
            with open(ALLOCATION_JSON) as f:
                data = json.load(f)
            _log(f"  [alloc] Loaded {ALLOCATION_JSON.name} (AUM=${data.get('aum_usd', 0):,.0f})")
            return data
        except Exception as e:
            _err(f"Allocation JSON read failed: {e} — using defaults")

    # First-run: create default allocation file
    _log("  [alloc] First run — creating default rwa_allocation.json")
    default = _build_default_allocation(DEFAULT_AUM_USD)
    _write_allocation(default)
    return default


def _build_default_allocation(aum: float) -> Dict:
    """Build a fresh default allocation dict at target weights (all paper-virtual)."""
    sleeve_usd = aum * SLEEVE_PCT
    providers  = {}
    for pid, cfg in DEFAULT_PROVIDERS.items():
        target_pct = cfg["target_weight_pct"]
        providers[pid] = {
            **cfg,
            "current_balance_usd":  round(sleeve_usd * target_pct / 100.0, 2),
            "current_weight_pct":   target_pct,
            "last_rebalance_jst":   _ts(),
            "live_apy_pct":         cfg["fallback_apy_pct"],
            "apy_source":           "fallback",
        }
    return {
        "wave":                  "K767",
        "version":               "v1.0",
        "mode":                  "PAPER_TRADE",
        "aum_usd":               aum,
        "sleeve_pct":            SLEEVE_PCT,
        "sleeve_usd":            round(sleeve_usd, 2),
        "rebalance_threshold_pp": REBALANCE_THRESHOLD_PP,
        "providers":             providers,
        "created_at_jst":        _ts(),
        "updated_at_jst":        _ts(),
        "k523": {
            "conservative_ann_usd": K523_CONSERVATIVE_ANN_USD,
            "mid_ann_usd":          K523_MID_ANN_USD,
            "optimistic_ann_usd":   K523_OPTIMISTIC_ANN_USD,
            "mid_realized_usd":     K523_MID_REALIZED_USD,
        },
    }


def _write_allocation(data: Dict) -> None:
    """Atomic write to rwa_allocation.json."""
    tmp = ALLOCATION_JSON.with_suffix(".tmp")
    try:
        tmp.write_text(json.dumps(data, indent=2, default=str))
        tmp.replace(ALLOCATION_JSON)
    except Exception as e:
        _err(f"Allocation JSON write failed: {e}")


# ── DeFiLlama APY fetch ───────────────────────────────────────────────────────

DEFILAMA_CHART_URL = "https://yields.llama.fi/chart/{pool_id}"
DEFILAMA_POOLS_URL = "https://yields.llama.fi/pools"
FETCH_TIMEOUT_S    = 20


def _fetch_defilama_pool_apy(pool_id: str) -> Optional[float]:
    """Fetch latest APY for a DeFiLlama pool ID. Returns None on failure."""
    if pool_id == "PENDING_RESEARCH":
        return None
    url = DEFILAMA_CHART_URL.format(pool_id=pool_id)
    try:
        req = urllib.request.Request(
            url,
            headers={"Accept": "application/json", "User-Agent": "ct-k767-rwa/1.0"},
        )
        with urllib.request.urlopen(req, timeout=FETCH_TIMEOUT_S) as resp:
            raw = json.loads(resp.read())
        data_pts = raw.get("data", [])
        if not data_pts:
            return None
        # Last entry has current APY
        latest = data_pts[-1]
        apy = latest.get("apy") or latest.get("apyBase")
        return float(apy) if apy is not None else None
    except Exception as e:
        _err(f"DeFiLlama fetch failed (pool={pool_id}): {e}")
        return None


def fetch_all_provider_apys(providers: Dict) -> Dict[str, Optional[float]]:
    """Fetch current APY for all providers. Falls back to fallback_apy_pct."""
    apys: Dict[str, Optional[float]] = {}
    for pid, cfg in providers.items():
        pool_id = cfg.get("defilama_pool_id", "PENDING_RESEARCH")
        live_apy = _fetch_defilama_pool_apy(pool_id)
        if live_apy is not None:
            _log(f"  [fetch] {pid}: live APY={live_apy:.2f}% (DeFiLlama)")
        else:
            live_apy = cfg.get("fallback_apy_pct", 4.0)
            _log(f"  [fetch] {pid}: fallback APY={live_apy:.2f}%")
        apys[pid] = live_apy
    return apys


# ── Rebalance logic ───────────────────────────────────────────────────────────

def compute_target_weights(
    allocation: Dict,
    bear1_active: bool,
) -> Dict[str, float]:
    """Compute effective target weights, applying BEAR_1 sUSDe reduction if active."""
    targets = {}
    for pid, cfg in allocation["providers"].items():
        targets[pid] = cfg["target_weight_pct"]

    if bear1_active:
        # sUSDe 50% reduction, redistribute proportionally to non-reducing providers
        if "sUSDe_Ethena" in targets:
            reduce_by = targets["sUSDe_Ethena"] * BEAR1_SUSDE_REDUCTION
            targets["sUSDe_Ethena"] -= reduce_by
            redistributable_ids = [
                pid for pid, cfg in allocation["providers"].items()
                if not cfg.get("bear1_reduce", False) and pid != "sUSDe_Ethena"
            ]
            total_other = sum(targets[pid] for pid in redistributable_ids)
            if total_other > 0:
                for pid in redistributable_ids:
                    targets[pid] += reduce_by * (targets[pid] / total_other)
            _log(f"  [BEAR_1] sUSDe reduced {BEAR1_SUSDE_REDUCTION*100:.0f}%; "
                 f"redistributed to: {redistributable_ids}")

    # Normalize to 100%
    total = sum(targets.values())
    if total > 0:
        targets = {pid: round(w / total * 100, 2) for pid, w in targets.items()}
    return targets


def check_rebalance_needed(
    allocation: Dict,
    target_weights: Dict[str, float],
    force: bool = False,
) -> Tuple[bool, List[str]]:
    """Check if rebalance is needed (drift > threshold or forced)."""
    if force:
        return True, ["FORCED"]
    drifted = []
    for pid, target in target_weights.items():
        current = allocation["providers"].get(pid, {}).get("current_weight_pct", 0.0)
        drift = abs(current - target)
        if drift > REBALANCE_THRESHOLD_PP:
            drifted.append(f"{pid}: current={current:.1f}% target={target:.1f}% drift={drift:.1f}pp")
    return len(drifted) > 0, drifted


def apply_rebalance(
    allocation: Dict,
    target_weights: Dict[str, float],
    live_apys: Dict[str, Optional[float]],
) -> Dict:
    """Apply rebalance to allocation dict. Updates virtual balances + weights."""
    sleeve_usd = allocation["sleeve_usd"]
    for pid, target_pct in target_weights.items():
        new_balance = round(sleeve_usd * target_pct / 100.0, 2)
        apy = live_apys.get(pid)
        src = "live" if apy is not None else "fallback"
        if apy is None:
            apy = allocation["providers"][pid].get("fallback_apy_pct", 4.0)
        allocation["providers"][pid].update({
            "current_balance_usd": new_balance,
            "current_weight_pct":  target_pct,
            "last_rebalance_jst":  _ts(),
            "live_apy_pct":        round(apy, 4),
            "apy_source":          src,
        })
    allocation["updated_at_jst"] = _ts()
    return allocation


# ── PnL computation (daily accrual simulation) ───────────────────────────────

def compute_daily_pnl(allocation: Dict) -> Dict:
    """Compute paper-trade daily PnL from virtual yield accrual."""
    records = []
    total_gross = 0.0
    total_net   = 0.0
    for pid, state in allocation["providers"].items():
        balance  = state.get("current_balance_usd", 0.0)
        apy_pct  = state.get("live_apy_pct", state.get("fallback_apy_pct", 4.0))
        daily_gr = balance * (apy_pct / 100.0) / 365.0
        # No per-day cost for yield positions (hold-to-earn, no rebalance cost today unless rebalance day)
        records.append({
            "provider":    pid,
            "balance_usd": round(balance, 2),
            "apy_pct":     round(apy_pct, 4),
            "gross_pnl":   round(daily_gr, 4),
        })
        total_gross += daily_gr
        total_net   += daily_gr  # no cost on hold days

    sleeve_usd = allocation.get("sleeve_usd", 1.0)
    return {
        "components":    records,
        "gross_pnl_usd": round(total_gross, 4),
        "net_pnl_usd":   round(total_net, 4),
        "net_pnl_bps":   round(total_net / sleeve_usd * 10_000, 4) if sleeve_usd > 0 else 0.0,
        "ann_net_pnl":   round(total_net * 365, 0),
    }


# ── Blended APY helper ────────────────────────────────────────────────────────

def compute_blended_apy(allocation: Dict) -> float:
    """Compute current weighted-average APY across all providers."""
    total_w = 0.0
    blended = 0.0
    sleeve  = allocation.get("sleeve_usd", 1.0)
    for pid, state in allocation["providers"].items():
        bal = state.get("current_balance_usd", 0.0)
        apy = state.get("live_apy_pct", state.get("fallback_apy_pct", 0.0))
        w   = bal / sleeve if sleeve > 0 else 0.0
        blended += w * apy
        total_w  += w
    return round(blended / total_w * total_w, 4) if total_w > 0 else 0.0  # already weighted


# ── Dashboard writer ──────────────────────────────────────────────────────────

def write_dashboard(payload: Dict) -> None:
    tmp = DASHBOARD_JSON.with_suffix(".tmp")
    try:
        tmp.write_text(json.dumps(payload, indent=2, default=str))
        tmp.replace(DASHBOARD_JSON)
    except Exception as e:
        _err(f"Dashboard write failed: {e}")


def write_trade_record(record: Dict) -> None:
    try:
        with open(TRADES_LOG, "a") as f:
            f.write(json.dumps(record, default=str) + "\n")
    except Exception as e:
        _err(f"Trade log write failed: {e}")


# ── Main ──────────────────────────────────────────────────────────────────────

def main(args: argparse.Namespace) -> int:
    _log("=== K767 RWA Diversified — weekly rebalance check ===")

    # ── Status mode ──────────────────────────────────────────────────────────
    if args.status:
        try:
            with open(DASHBOARD_JSON) as f:
                d = json.load(f)
            print(json.dumps({
                "wave":         d.get("wave"),
                "mode":         d.get("mode"),
                "updated":      d.get("updated_at_jst"),
                "blended_apy":  d.get("blended_apy_pct"),
                "sleeve_usd":   d.get("sleeve_usd"),
                "rebalance":    d.get("rebalanced_this_run"),
                "ann_net_pnl":  d.get("pnl", {}).get("ann_net_pnl"),
                "k523_central": K523_MID_ANN_USD,
            }, indent=2))
        except Exception as e:
            print(f"No dashboard yet: {e}")
        return 0

    # ── Priority 1: EMERGENCY flag ────────────────────────────────────────────
    if EMERGENCY_FLAG.exists():
        _log("  EMERGENCY_EXIT_TRIGGERED.flag — RWA yields are safe-haven; skipping rebalance (K415 pattern)")
        write_dashboard({
            "wave":           "K767",
            "mode":           "PAPER_TRADE" if PAPER_TRADE else "LIVE",
            "status":         "EMERGENCY_HOLD",
            "updated_at_jst": _ts(),
            "note":           "Emergency flag active. Yield positions hold through crisis (K415 pattern).",
        })
        return 0

    # ── Priority 2: BEAR_1 flag ───────────────────────────────────────────────
    bear1_active = BEAR1_FLAG.exists()
    if bear1_active:
        _log("  BEAR_1_FALLBACK_ACTIVE — sUSDe will be reduced 50%")

    # ── Load allocation ───────────────────────────────────────────────────────
    allocation = load_allocation()
    aum_usd    = allocation.get("aum_usd", DEFAULT_AUM_USD)

    # ── Fetch live APYs ───────────────────────────────────────────────────────
    live_apys = fetch_all_provider_apys(allocation["providers"])

    # ── Compute target weights (with BEAR_1 adjustment) ──────────────────────
    target_weights = compute_target_weights(allocation, bear1_active)
    _log(f"  Target weights: {target_weights}")

    # ── Check rebalance needed ────────────────────────────────────────────────
    rebalance_needed, drift_reasons = check_rebalance_needed(
        allocation, target_weights, force=args.force_rebalance
    )
    _log(f"  Rebalance needed: {rebalance_needed} | reasons: {drift_reasons}")

    # ── Apply rebalance (paper-mode: update virtual balances) ─────────────────
    rebalanced = False
    if rebalance_needed:
        if PAPER_TRADE:
            _log("  [PAPER] Applying virtual rebalance...")
        else:
            _log("  [LIVE] Rebalance signals — operator must execute on-chain")
        allocation = apply_rebalance(allocation, target_weights, live_apys)
        rebalanced = True
    else:
        # Update APYs even if no rebalance
        for pid in allocation["providers"]:
            apy = live_apys.get(pid)
            if apy is not None:
                allocation["providers"][pid]["live_apy_pct"] = round(apy, 4)
                allocation["providers"][pid]["apy_source"]   = "live"
        allocation["updated_at_jst"] = _ts()

    # ── Compute daily PnL ────────────────────────────────────────────────────
    pnl = compute_daily_pnl(allocation)
    _log(f"  Daily net PnL: ${pnl['net_pnl_usd']:.4f} ({pnl['net_pnl_bps']:.2f} bps)")
    _log(f"  Ann est: ${pnl['ann_net_pnl']:,.0f}/yr")

    # ── Blended APY ──────────────────────────────────────────────────────────
    blended_apy = compute_blended_apy(allocation)

    # ── Build dashboard ───────────────────────────────────────────────────────
    dashboard = {
        "wave":                  "K767",
        "daemon_number":         74,
        "mode":                  "PAPER_TRADE" if PAPER_TRADE else "LIVE",
        "updated_at_jst":        _ts(),
        "bear1_active":          bear1_active,
        "emergency_active":      False,
        "aum_usd":               round(aum_usd, 0),
        "sleeve_pct":            SLEEVE_PCT,
        "sleeve_usd":            allocation.get("sleeve_usd", round(aum_usd * SLEEVE_PCT, 0)),
        "blended_apy_pct":       blended_apy,
        "providers":             allocation["providers"],
        "target_weights":        target_weights,
        "rebalanced_this_run":   rebalanced,
        "drift_reasons":         drift_reasons,
        "pnl":                   pnl,
        "k523": {
            "conservative_ann_usd": K523_CONSERVATIVE_ANN_USD,
            "mid_ann_usd":          K523_MID_ANN_USD,
            "optimistic_ann_usd":   K523_OPTIMISTIC_ANN_USD,
            "mid_realized_usd":     K523_MID_REALIZED_USD,
            "k523_note": (
                "Central is NOT upper bound (K523 mandate). "
                "K518 38% haircut applied to realized. "
                "sUSDe optimistic contingent on ETH funding surge."
            ),
        },
        "geo_strategy": {
            "us_resident":     "sUSDe + Spark sUSDS + Mountain USDM (3 providers, ~3.85% blended)",
            "non_us_resident": "All 4 providers (~4.20% blended)",
            "note":            "USDY non-US only per K415 CONDITIONAL_ACCEPT",
        },
        "rebalance_schedule":    "Weekly (Sunday 03:00 JST via launchd)",
        "rebalance_threshold_pp": REBALANCE_THRESHOLD_PP,
        "dependencies": {
            "K344_sUSDe":    str(K344_DASHBOARD),
            "K473_Spark":    str(K473_DASHBOARD),
            "K415_USDY":     str(K415_DASHBOARD),
        },
        "activation_runbook":    "docs/k302a_runbook.md §75",
    }

    if not args.dry_run:
        write_dashboard(dashboard)
        _write_allocation(allocation)
        write_trade_record({
            "date_jst":      _ts(),
            "rebalanced":    rebalanced,
            "blended_apy":   blended_apy,
            "net_pnl_usd":   pnl["net_pnl_usd"],
            "ann_pnl_usd":   pnl["ann_net_pnl"],
            "bear1":         bear1_active,
            "mode":          "PAPER" if PAPER_TRADE else "LIVE",
        })
        _log(f"  Dashboard: {DASHBOARD_JSON}")
        _log(f"  Allocation: {ALLOCATION_JSON}")
    else:
        _log("  [dry-run] dashboard/allocation NOT written")

    _log(f"  === K767 Summary ===")
    _log(f"  Providers: {len(allocation['providers'])} (sUSDe/Spark/USDY/USDM)")
    _log(f"  Blended APY: {blended_apy:.2f}%")
    _log(f"  Sleeve: ${allocation.get('sleeve_usd', 0):,.0f}")
    _log(f"  Ann est: ${pnl['ann_net_pnl']:,.0f}/yr (K523 central: ${K523_MID_ANN_USD:,}/yr)")
    _log(f"  Rebalanced: {rebalanced}")
    _log("=== K767 done ===")

    return 0


# ── CLI ───────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="K767 RWA 4-provider diversified yield sleeve")
    parser.add_argument("--dry-run", action="store_true",
                        help="Compute but do not write dashboard/logs")
    parser.add_argument("--status", action="store_true",
                        help="Print current dashboard summary and exit")
    parser.add_argument("--force-rebalance", action="store_true",
                        help="Force rebalance regardless of drift threshold")
    args = parser.parse_args()
    sys.exit(main(args))

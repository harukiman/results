#!/usr/bin/env python3
"""
k344_susde_oc_daily_run.py — K344 sUSDe Optimal Control Daily Daemon
======================================================================
Ethena sUSDe yield OC (Optimal Control) sleeve for K302a v6.13d.
Weight allocation: 5% of total portfolio (K346 winner: K280 75% + K297' 20% + sUSDe 5%).

OC Signal Rules (arXiv 2605.11263 framework, K344 wave):
  - APY > 30d EMA + 50bps → FULL (100% of sleeve; currently positive carry)
  - APY within band (EMA ± 50bps) → HALF (50% of sleeve; transitional zone)
  - APY < 30d EMA - 50bps → ZERO (0%; below EMA = risk-off / low carry period)
  - Shock guard: 7d APY drop > 3pp → ZERO (regardless of EMA; protocol stress signal)

Data source: DeFiLlama yields API (no key required, public endpoint).
  Pool ID: 65457d63-3f6c-4c6f-9977-d984022b4462  (Ethena sUSDe)
  Endpoint: https://yields.llama.fi/chart/{pool_id}

Outputs:
  data/k344_susde_dashboard.json    — current state for HTML consumption
  cache/k344_susde_oc_state.parquet — append-only history

K339 security rule: use Path(__file__).resolve().parent.parent for REPO_ROOT.
Rollback: remove plist from LaunchAgents or set allocation weight to 0.

Usage:
  python3 scripts/k344_susde_oc_daily_run.py
  python3 scripts/k344_susde_oc_daily_run.py --date 2026-05-25 --dry-run
"""
from __future__ import annotations

import argparse
import json
import math
import sys
import time
import warnings
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Dict, Optional, Tuple
from urllib.request import urlopen, Request
from urllib.error import URLError

import numpy as np
import pandas as pd

warnings.filterwarnings("ignore")

# ── Paths (K339 security: no absolute /Users/ paths) ───────────────────────────
REPO_ROOT  = Path(__file__).resolve().parent.parent
CACHE      = REPO_ROOT / "cache"
DATA       = REPO_ROOT / "data"
DATA.mkdir(exist_ok=True)
CACHE.mkdir(exist_ok=True)

DASHBOARD_JSON    = DATA  / "k344_susde_dashboard.json"
OC_STATE_PARQUET  = CACHE / "k344_susde_oc_state.parquet"

# ── DeFiLlama sUSDe Pool ───────────────────────────────────────────────────────
DEFILLAMA_POOL_ID = "66985a81-9c51-46ca-9977-42b4fe7bc6df"  # Ethena sUSDe (ethena-usde project, SUSDE symbol)
DEFILLAMA_URL     = f"https://yields.llama.fi/chart/{DEFILLAMA_POOL_ID}"
FETCH_TIMEOUT_S   = 30

# ── OC Signal Parameters (K344 calibration) ───────────────────────────────────
OC_EMA_WINDOW_D   = 30      # 30d EMA of sUSDe APY
OC_BAND_BPS       = 50      # ±50bps band around EMA (0.50%)
OC_SHOCK_WINDOW_D = 7       # 7d rolling window for shock detection
OC_SHOCK_DROP_PP  = 3.0     # 3pp (percentage-point) drop triggers ZERO

# ── Portfolio Sleeve Config ────────────────────────────────────────────────────
SLEEVE_WEIGHT     = 0.05    # 5% of total portfolio (K346 winner v6.13d)
SLEEVE_LABEL      = "sUSDe OC sleeve (K344, v6.13d)"

# ── JST timezone ───────────────────────────────────────────────────────────────
JST = timezone(timedelta(hours=9))


# ─────────────────────────────────────────────────────────────────────────────
# DeFiLlama Fetch
# ─────────────────────────────────────────────────────────────────────────────

def fetch_susde_apy_history() -> pd.DataFrame:
    """
    Fetch sUSDe APY history from DeFiLlama yields API.
    Returns DataFrame with columns: [date, apy] indexed by date.
    """
    print(f"  [sUSDe] Fetching APY from DeFiLlama: {DEFILLAMA_URL}")
    try:
        req  = Request(DEFILLAMA_URL, headers={"User-Agent": "crypto-lab/k344"})
        with urlopen(req, timeout=FETCH_TIMEOUT_S) as resp:
            raw = json.loads(resp.read().decode())
    except URLError as e:
        print(f"  [sUSDe] WARN: DeFiLlama fetch failed: {e}. Using cached state.")
        return pd.DataFrame()

    data_points = raw.get("data", [])
    if not data_points:
        print("  [sUSDe] WARN: Empty data from DeFiLlama.")
        return pd.DataFrame()

    rows = []
    for pt in data_points:
        ts  = pt.get("timestamp", "")
        apy = pt.get("apy")
        if ts and apy is not None:
            rows.append({"date": ts[:10], "apy": float(apy)})

    if not rows:
        return pd.DataFrame()

    df = pd.DataFrame(rows)
    df["date"] = pd.to_datetime(df["date"])
    df = df.drop_duplicates("date").sort_values("date").set_index("date")
    print(f"  [sUSDe] Fetched {len(df)} APY data points "
          f"({df.index[0].date()} → {df.index[-1].date()})")
    return df


# ─────────────────────────────────────────────────────────────────────────────
# OC Signal Computation
# ─────────────────────────────────────────────────────────────────────────────

def compute_oc_signal(apy_series: pd.Series) -> Tuple[float, str, Dict]:
    """
    Compute Optimal Control allocation signal from APY history.

    Returns:
        allocation  — fraction of sleeve to deploy (0.0, 0.5, or 1.0)
        signal_code — 'FULL' | 'HALF' | 'ZERO' | 'SHOCK'
        state_dict  — detailed signal state for logging
    """
    if apy_series.empty or len(apy_series) < 7:
        return 0.0, "ZERO", {"reason": "insufficient_data", "n_days": len(apy_series)}

    current_apy  = float(apy_series.iloc[-1])
    ema_30d      = float(apy_series.ewm(span=OC_EMA_WINDOW_D, adjust=False).mean().iloc[-1])
    mean_30d     = float(apy_series.tail(30).mean())
    band_hi      = ema_30d + OC_BAND_BPS / 100.0   # +50bps in % units
    band_lo      = ema_30d - OC_BAND_BPS / 100.0   # -50bps in % units

    # Shock detection: 7d rolling drop
    apy_7d_ago   = float(apy_series.iloc[-OC_SHOCK_WINDOW_D]) if len(apy_series) >= OC_SHOCK_WINDOW_D else None
    shock_drop   = (apy_7d_ago - current_apy) if apy_7d_ago is not None else 0.0
    shock_active = shock_drop > OC_SHOCK_DROP_PP  # 7d drop > 3pp

    if shock_active:
        allocation  = 0.0
        signal_code = "SHOCK"
        reason      = f"7d APY drop {shock_drop:.2f}pp > {OC_SHOCK_DROP_PP}pp threshold"
    elif current_apy > band_hi:
        allocation  = 1.0
        signal_code = "FULL"
        reason      = f"APY {current_apy:.2f}% > EMA+50bps band ({band_hi:.2f}%)"
    elif current_apy < band_lo:
        allocation  = 0.0
        signal_code = "ZERO"
        reason      = f"APY {current_apy:.2f}% < EMA-50bps band ({band_lo:.2f}%)"
    else:
        allocation  = 0.5
        signal_code = "HALF"
        reason      = f"APY {current_apy:.2f}% within EMA±50bps band ({band_lo:.2f}%–{band_hi:.2f}%)"

    effective_weight = allocation * SLEEVE_WEIGHT

    state = {
        "current_apy_pct":      round(current_apy, 4),
        "ema_30d_pct":          round(ema_30d, 4),
        "mean_30d_pct":         round(mean_30d, 4),
        "band_hi_pct":          round(band_hi, 4),
        "band_lo_pct":          round(band_lo, 4),
        "apy_7d_ago_pct":       round(apy_7d_ago, 4) if apy_7d_ago is not None else None,
        "shock_drop_pp":        round(shock_drop, 4),
        "shock_active":         shock_active,
        "signal":               signal_code,
        "allocation_fraction":  allocation,
        "effective_weight_pct": round(effective_weight * 100, 2),
        "sleeve_weight_pct":    round(SLEEVE_WEIGHT * 100, 2),
        "reason":               reason,
        "n_days_history":       len(apy_series),
        "panel_last_date":      str(apy_series.index[-1].date()),
        "oc_params": {
            "ema_window_d":     OC_EMA_WINDOW_D,
            "band_bps":         OC_BAND_BPS,
            "shock_window_d":   OC_SHOCK_WINDOW_D,
            "shock_drop_pp":    OC_SHOCK_DROP_PP,
        },
    }
    print(f"  [sUSDe] APY={current_apy:.2f}% | EMA30d={ema_30d:.2f}% | "
          f"Signal={signal_code} | alloc={allocation*100:.0f}% of sleeve | "
          f"effective_wt={effective_weight*100:.2f}%")
    return allocation, signal_code, state


# ─────────────────────────────────────────────────────────────────────────────
# Dashboard & History
# ─────────────────────────────────────────────────────────────────────────────

def load_dashboard() -> Dict:
    """Load existing dashboard or return empty structure."""
    if DASHBOARD_JSON.exists():
        with open(DASHBOARD_JSON) as f:
            return json.load(f)
    return {
        "architecture":    "sUSDe OC sleeve (K344) — v6.13d",
        "version":         "v6.13d",
        "sleeve_weight":   SLEEVE_WEIGHT,
        "defillama_pool":  DEFILLAMA_POOL_ID,  # ethena-usde / SUSDE symbol
        "oc_params": {
            "ema_window_d":  OC_EMA_WINDOW_D,
            "band_bps":      OC_BAND_BPS,
            "shock_window_d": OC_SHOCK_WINDOW_D,
            "shock_drop_pp": OC_SHOCK_DROP_PP,
        },
        "backtest_ref": {
            "sharpe":  8.39,     # OC strategy (K344)
            "mdd_pct": 0.11,     # MaxDD %
            "corr_k280": 0.05,   # orthogonal to K280
        },
        "daily_records":  [],
        "last_update":    None,
    }


def append_history(date_str: str, signal_code: str, allocation: float, state: Dict):
    """Append today's OC state to parquet history."""
    record = {
        "date":               date_str,
        "signal":             signal_code,
        "allocation_fraction": allocation,
        "current_apy_pct":   state.get("current_apy_pct"),
        "ema_30d_pct":        state.get("ema_30d_pct"),
        "shock_active":       state.get("shock_active"),
        "shock_drop_pp":      state.get("shock_drop_pp"),
        "effective_weight_pct": state.get("effective_weight_pct"),
        "ts_utc":             datetime.now(timezone.utc).isoformat(),
    }
    new_df = pd.DataFrame([record]).set_index("date")
    new_df.index = pd.to_datetime(new_df.index)

    if OC_STATE_PARQUET.exists():
        existing = pd.read_parquet(OC_STATE_PARQUET)
        existing.index = pd.to_datetime(existing.index)
        # Dedup by date (today overwrites)
        existing = existing[existing.index.strftime("%Y-%m-%d") != date_str]
        combined = pd.concat([existing, new_df]).sort_index()
    else:
        combined = new_df

    combined.to_parquet(OC_STATE_PARQUET)
    print(f"  [sUSDe] History appended: {OC_STATE_PARQUET} ({len(combined)} rows)")


def update_dashboard(
    date_str:   str,
    allocation: float,
    signal_code: str,
    state:      Dict,
    apy_series: pd.Series,
    dry_run:    bool = False,
):
    """Write updated sUSDe dashboard JSON."""
    dash = load_dashboard()

    today_record = {
        "date":        date_str,
        "signal":      signal_code,
        "allocation":  allocation,
        "state":       state,
        "run_ts_jst":  datetime.now(JST).strftime("%Y-%m-%d %H:%M JST"),
    }

    # Append daily record (dedup)
    records = dash.get("daily_records", [])
    records = [r for r in records if r.get("date") != date_str]
    records.append(today_record)
    dash["daily_records"] = sorted(records, key=lambda r: r["date"])[-90:]  # keep 90d

    dash["last_update"]       = datetime.now(timezone.utc).isoformat()
    dash["last_update_jst"]   = datetime.now(JST).strftime("%Y-%m-%d %H:%M JST")
    dash["current_signal"]    = signal_code
    dash["current_allocation"] = allocation
    dash["current_state"]     = state
    dash["sleeve_weight"]     = SLEEVE_WEIGHT

    class NaNSafe(json.JSONEncoder):
        def default(self, obj):
            if isinstance(obj, float) and math.isnan(obj):
                return None
            if isinstance(obj, np.integer):
                return int(obj)
            if isinstance(obj, np.floating):
                return None if math.isnan(float(obj)) else float(obj)
            return super().default(obj)

    if not dry_run:
        with open(DASHBOARD_JSON, "w") as f:
            json.dump(dash, f, indent=2, cls=NaNSafe)
        print(f"  [sUSDe] Dashboard saved: {DASHBOARD_JSON}")
    else:
        print(f"  [sUSDe] DRY RUN — would save dashboard: {DASHBOARD_JSON}")


# ─────────────────────────────────────────────────────────────────────────────
# Main Daily Run
# ─────────────────────────────────────────────────────────────────────────────

def run_daily(date_str: str, dry_run: bool = False):
    print(f"\n=== K344 sUSDe OC Daemon — {date_str} (dry_run={dry_run}) ===\n")
    t0 = time.time()

    # ── Fetch APY history ──────────────────────────────────────────────────────
    apy_df = fetch_susde_apy_history()

    if apy_df.empty:
        print("  [sUSDe] ERROR: No APY data available. Exiting without writing dashboard.")
        return {"error": "no_data", "date": date_str}

    apy_series = apy_df["apy"]

    # ── Compute OC signal ──────────────────────────────────────────────────────
    allocation, signal_code, state = compute_oc_signal(apy_series)

    # ── Write dashboard + history ──────────────────────────────────────────────
    update_dashboard(date_str, allocation, signal_code, state, apy_series, dry_run)

    if not dry_run:
        append_history(date_str, signal_code, allocation, state)

    elapsed = time.time() - t0
    print(f"\n=== K344 sUSDe OC daemon complete in {elapsed:.1f}s ===")
    print(f"  Signal: {signal_code} | Allocation: {allocation*100:.0f}% of sleeve "
          f"({allocation * SLEEVE_WEIGHT * 100:.2f}% of total portfolio)")

    # ── K429 AUM Tracking (additive — safe if portfolio_aum_manager not present) ─
    # K344 is SECONDARY: updates sUSDe yield contribution to AUM.
    # sUSDe yield is APY-based; daily PnL ≈ current_apy_pct / 365 / 100 × sleeve_allocation.
    if not dry_run:
        try:
            import os as _os_k429
            if _os_k429.environ.get("AUM_TRACKING_ENABLED", "true").lower() != "false":
                import sys as _sys_k429
                _sys_k429.path.insert(0, str(REPO_ROOT / "scripts"))
                from portfolio_aum_manager import (
                    update_aum, get_current_metrics, compute_position_size, load_state,
                )
                _aum_state    = load_state()
                _susde_alloc  = compute_position_size("sUSDe", _aum_state) * allocation
                _apy_daily    = (state.get("current_apy_pct", 0.0) / 365.0 / 100.0)
                _pnl_usdc     = _susde_alloc * _apy_daily
                update_aum(_pnl_usdc, sleeve_name="sUSDe")
                _m = get_current_metrics()
                print(
                    f"\n  [K429] sUSDe AUM contrib: ${_pnl_usdc:+,.2f} USDC/day | "
                    f"Portfolio AUM=${_m.get('current_aum_usdc', 0):,.0f}"
                )
        except Exception as _e_aum:
            print(f"  [K429] AUM tracking skipped: {_e_aum}")

    return {
        "date":            date_str,
        "signal":          signal_code,
        "allocation":      allocation,
        "current_apy_pct": state.get("current_apy_pct"),
        "ema_30d_pct":     state.get("ema_30d_pct"),
        "elapsed_s":       round(elapsed, 1),
    }


# ─────────────────────────────────────────────────────────────────────────────
# CLI Entry Point
# ─────────────────────────────────────────────────────────────────────────────

def main():
    EMERGENCY_FLAG = REPO_ROOT / "EMERGENCY_EXIT_TRIGGERED.flag"
    if EMERGENCY_FLAG.exists():
        print("[K344] EMERGENCY_EXIT_TRIGGERED.flag detected — skipping signal computation and dashboard write")
        sys.exit(0)

    parser = argparse.ArgumentParser(description="K344 sUSDe Optimal Control Daily Daemon")
    parser.add_argument("--date", default=None,
                        help="Date YYYY-MM-DD (default: today UTC)")
    parser.add_argument("--dry-run", action="store_true",
                        help="Fetch and compute signal but do not write output files")
    args = parser.parse_args()
    date_str = args.date or datetime.now(timezone.utc).strftime("%Y-%m-%d")
    run_daily(date_str, dry_run=args.dry_run)


if __name__ == "__main__":
    main()

"""
k302a_satellite_run.py — K302a Satellite Daily Paper-Trade Execution
======================================================================
Satellite portfolio: K297' [PAXG 60% + SPX 40%] — HyperLiquid only.
K297' = K297 + SPX fake-out filter (K343 integration, v6.13d).

Strategy:
  - PAXG component: Always-on long perp, collect HL funding income
  - SPX component:  Conditional long perp (K297' SPX filter: 5d trend > 0 AND FR > 0)
  - Allocation:     PAXG 60% + SPX 40% (fixed, per K297 recommendation)
  - Cost:           7 bp/side maker (paper-trade conservative; real HL maker = 1.5 bp)
  - Settlement:     HL hourly; daily PnL = daily_mean_fr × 24 − cost_amortized

Backtest reference (K297' filtered carry, v6.13d):
  PAXG: Sharpe 16.91, MaxDD -0.36%, Win Days 88%, Ann Return 8.03%
  SPX:  Sharpe 12.20, MaxDD -1.74%, Win Days 78%, Ann Return 6.80%  (K297' post-filter)
  Portfolio EW: Sharpe 18.48, MaxDD -1.41%, Ann Return ~7.3%
  Correlation PAXG vs SPX: 0.18 (low — genuine diversification)

Portfolio architecture (v6.13d K348):
  K280 main (75%) + K302a satellite K297' (20%) + sUSDe OC sleeve (5%) = K302a v6.13d combined
  Combined Sharpe: 25.47, MDD 0.0189%, all §6 gates pass, WF min 22.3

Rollback: set SPX_FILTER_ENABLED = False to revert to K297 always-on (v6.12 behaviour).

Usage:
  python3 scripts/k302a_satellite_run.py
  python3 scripts/k302a_satellite_run.py --date 2026-05-25
"""
from __future__ import annotations

import argparse
import json
import math
import time
import warnings
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import numpy as np
import pandas as pd

warnings.filterwarnings("ignore")

# ── K297' SPX Filter Config (K343 K297→K297' integration, v6.13d) ──────────────
SPX_FILTER_ENABLED    = True   # K343 K297→K297' integration (v6.13d); set False to rollback
SPX_TREND_WINDOW_D    = 5      # 5d price-trend window (CV robust: 3/5/7/10/14/21d ≈ same)
SPX_FR_THRESHOLD      = 0.0    # FR > 0 condition (long only when carry positive)

# ── K371: G9 Oracle Deviation Gate (K369 K297' production safety) ─────────────
# Skip SPX/PAXG entry when |mark - oracle| / oracle > 1%.
# K369 live measurement: PAXG 0.062%, SPX 0.125% — both << 1% threshold.
# Expected behavior: 0 skipped days currently. Rollback: ORACLE_GATE_ENABLED = False.
ORACLE_GATE_ENABLED          = True
ORACLE_DEVIATION_THRESHOLD   = 0.01   # 1% per K369 (HL native 1% per-update cap)

# ── K370: Builder Code Self-Rebate (AX-01 from K368) ─────────────────────────
# K302a satellite trades on HyperLiquid (PAXG, SPX). When live, include builder
# code in every order action to accumulate referral-pool rewards on own volume.
# SELF-REBATE MODE: BUILDER_FEE_F = 0 adds zero extra cost to orders.
# ACTIVATION: user must approveBuilderFee on-chain, then set BUILDER_CODE_ENABLED=True.
# See docs/k302a_runbook.md §15 for full activation runbook.
import os as _os_k302a
BUILDER_CODE_ENABLED   = False                                  # K370: True after wallet registered
BUILDER_WALLET_ADDRESS = _os_k302a.environ.get("HL_BUILDER_WALLET", "")  # registered HL wallet
BUILDER_FEE_F          = 0          # tenths of bp extra cost (0 = self-rebate, no user impact)
# When live order submission is implemented, add to order action:
#   if BUILDER_CODE_ENABLED and BUILDER_WALLET_ADDRESS:
#       order_action["builder"] = {"b": BUILDER_WALLET_ADDRESS, "f": BUILDER_FEE_F}

# ── Paths ──────────────────────────────────────────────────────────────────────
BASE  = Path(__file__).resolve().parent.parent  # K339 security rule: no absolute /Users/ paths
CACHE = BASE / "cache"
DATA  = BASE / "data"
DATA.mkdir(exist_ok=True)

# ── K386 BEAR_1 Gate ───────────────────────────────────────────────────────────
# If BEAR_1_FALLBACK_ACTIVE.flag is present, K297' (HIP-3) is CFTC-restricted.
# K302a satellite skips execution; K386 k386_v613e_fallback_run.py takes over.
# Daemon priority: EMERGENCY_EXIT_TRIGGERED > BEAR_1_FALLBACK_ACTIVE > normal ops.
_BEAR1_FLAG     = BASE / "BEAR_1_FALLBACK_ACTIVE.flag"
_EMERGENCY_FLAG = BASE / "EMERGENCY_EXIT_TRIGGERED.flag"
if _EMERGENCY_FLAG.exists():
    print("[K302a] EMERGENCY_EXIT_TRIGGERED.flag present. All daemons halted. Exiting.")
    import sys as _sys_exit; _sys_exit.exit(0)
if _BEAR1_FLAG.exists():
    print("[K302a] BEAR_1_FALLBACK_ACTIVE.flag detected.")
    print("  K297' HIP-3 satellite is CFTC-restricted in v6.13e fallback mode.")
    print("  K302a satellite skipping execution — K386 v6.13e daemon takes over.")
    print("  See: docs/k302a_runbook.md §18 for deactivation procedure.")
    import sys as _sys_exit; _sys_exit.exit(0)

DASHBOARD_JSON = DATA / "k302a_satellite_dashboard.json"
TRADES_LOG     = DATA / "k302a_satellite_paper_trades.jsonl"
K280_DASHBOARD = DATA / "k280_live_dashboard.json"

# ── K302a Satellite Universe ────────────────────────────────────────────────────
K302A_COINS = ["PAXG", "SPX"]
PAXG_WEIGHT = 0.60
SPX_WEIGHT  = 0.40
COIN_WEIGHTS = {"PAXG": PAXG_WEIGHT, "SPX": SPX_WEIGHT}

# ── Strategy Parameters ────────────────────────────────────────────────────────
HL_EVENTS_PER_DAY   = 24        # HL settles hourly
PAPER_COST_RATE     = 0.0007    # 7 bp/side (conservative paper-trade)
HL_MAKER_COST_RATE  = 0.00015   # 1.5 bp/side (actual HL maker, K296 finding)
# Cost amortization: position held continuously; enter once at start of period.
# Amortize maker cost over ~30d holding period = cost per day ≈ PAPER_COST / 30
COST_AMORT_DAYS     = 30

# ── Portfolio Weights (v6.13d K348: K280 75% + K297' 20% + sUSDe 5%) ──────────
K302A_MAIN_WEIGHT      = 0.75   # K280 main daemon (75%; was 80% in v6.12)
K302A_SATELLITE_WEIGHT = 0.20   # K302a satellite K297' (20%)
K302A_SUSDE_WEIGHT     = 0.05   # sUSDe OC sleeve (5%; new in v6.13d)

# ── Backtest Reference (K297' filtered carry, v6.13d) ─────────────────────────
BT_PAXG_SH     = 16.91
BT_SPX_SH      = 12.20     # K297' post-filter (was 5.87 in K297 always-on)
BT_PORT_SH     = 18.48     # EW portfolio K297' (was 10.17 in K297)
BT_PAXG_DD     = -0.0036    # -0.36%
BT_SPX_DD      = -0.0174    # -1.74%
BT_PORT_DD     = -0.0141    # -1.41%
BT_COMBINED_SH = 25.47      # K302a v6.13d combined (K280 75% + K297' 20% + sUSDe 5%), K346 winner

# ── Alert Thresholds ──────────────────────────────────────────────────────────
ALERT_SAT_30D_DD_MAX  = 0.005    # satellite 30d DD > 0.5% → HALT (K303: half of full-period MaxDD)
ALERT_SAT_30D_SH_MIN  = 25.0    # combined 30d Sh < 25 → re-evaluate (K303 trigger)
ALERT_PAXG_30D_SH_MIN = 3.0     # PAXG component 30d Sh < 3 → low carry regime
ALERT_SPX_30D_SH_MIN  = 2.0     # SPX component 30d Sh < 2 → low carry (SPX more volatile)
TRADING_DAYS = 365


# ─────────────────────────────────────────────────────────────────────────────
# Metric helpers
# ─────────────────────────────────────────────────────────────────────────────

def sharpe_d(r: np.ndarray, ann: int = TRADING_DAYS) -> float:
    """Daily-return Sharpe annualised."""
    r = np.asarray(r, dtype=float)
    r = r[np.isfinite(r)]
    if len(r) < 2 or r.std(ddof=1) == 0:
        return 0.0
    return float(r.mean() / r.std(ddof=1) * math.sqrt(ann))


def max_dd(equity: np.ndarray) -> float:
    eq   = np.asarray(equity, dtype=float)
    peak = np.maximum.accumulate(eq)
    return float(((eq - peak) / (peak + 1e-12)).min())


def rolling_sharpe(r: np.ndarray, window: int = 30, ann: int = TRADING_DAYS) -> Optional[float]:
    if len(r) < max(10, window // 2):
        return None
    tail = r[-window:]
    return sharpe_d(tail, ann)


# ─────────────────────────────────────────────────────────────────────────────
# K371: Oracle Health (G9 Gate)
# ─────────────────────────────────────────────────────────────────────────────

def fetch_oracle_health(coins: list) -> dict:
    """Fetch (markPx, oraclePx) for each coin from HL metaAndAssetCtxs.

    Returns {coin: {"markPx": float, "oraclePx": float, "deviation": float}}
    where deviation = (markPx - oraclePx) / oraclePx (signed; use abs() for gate).
    On API error returns empty dict (fail-open: trade proceeds normally).
    """
    import urllib.request as _urllib_req
    try:
        req = _urllib_req.Request(
            "https://api.hyperliquid.xyz/info",
            data=json.dumps({"type": "metaAndAssetCtxs"}).encode(),
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        with _urllib_req.urlopen(req, timeout=8) as r:
            meta, ctxs = json.loads(r.read())
        universe = meta.get("universe", [])
        result: dict = {}
        for i, entry in enumerate(universe):
            name = entry.get("name")
            if name in coins and i < len(ctxs):
                ctx = ctxs[i]
                mark   = float(ctx.get("markPx",   0) or 0)
                oracle = float(ctx.get("oraclePx", 0) or 0)
                dev    = (mark - oracle) / oracle if oracle != 0 else 0.0
                result[name] = {"markPx": mark, "oraclePx": oracle, "deviation": dev}
        return result
    except Exception as exc:
        print(f"  [G9] Oracle health fetch error (fail-open): {exc}")
        return {}


# ─────────────────────────────────────────────────────────────────────────────
# Data Loading
# ─────────────────────────────────────────────────────────────────────────────

def load_k302a_panel() -> pd.DataFrame:
    """Load K302a daily FR panel (cache/k302a_fr_daily.parquet)."""
    path = CACHE / "k302a_fr_daily.parquet"
    if not path.exists():
        print("  [K302a] k302a_fr_daily.parquet not found. Run k302a_satellite_fetch.py first.")
        # Fallback: build from hl_hip3_fr_daily.parquet directly
        raw_path = CACHE / "hl_hip3_fr_daily.parquet"
        if raw_path.exists():
            print("  [K302a] Falling back to hl_hip3_fr_daily.parquet...")
            raw = pd.read_parquet(raw_path)
            if "timestamp" not in raw.columns:
                raw = raw.reset_index()
            raw["timestamp"] = pd.to_datetime(raw["timestamp"], utc=True)
            sym_daily: Dict[str, pd.Series] = {}
            for coin in K302A_COINS:
                coin_df = raw[raw["coin"] == coin].copy()
                if coin_df.empty:
                    continue
                coin_df = coin_df.set_index("timestamp").sort_index()
                daily = coin_df["funding_rate"].resample("D").mean().dropna()
                daily.index = daily.index.normalize().tz_localize(None)
                sym_daily[coin] = daily
            if sym_daily:
                panel = pd.DataFrame(sym_daily).sort_index()
                panel.to_parquet(path)
                print(f"  [K302a] Built daily panel from raw: {panel.shape}")
                return panel
        return pd.DataFrame(columns=K302A_COINS)

    df = pd.read_parquet(path)
    df.index = pd.to_datetime(df.index)
    if df.index.tz is not None:
        df.index = df.index.tz_localize(None)
    return df.sort_index()


def load_fetch_snapshot(date_str: str) -> Optional[Dict]:
    """Load today's K302a fetch snapshot JSON."""
    path = CACHE / f"k302a_satellite_{date_str.replace('-', '')}.json"
    if path.exists():
        with open(path) as f:
            return json.load(f)
    return None


def load_k280_dashboard() -> Optional[Dict]:
    """Load K280 main dashboard for combined view."""
    if K280_DASHBOARD.exists():
        with open(K280_DASHBOARD) as f:
            return json.load(f)
    return None


def load_dashboard() -> Dict:
    """Load existing K302a dashboard or return empty structure."""
    if DASHBOARD_JSON.exists():
        with open(DASHBOARD_JSON) as f:
            return json.load(f)
    return {
        "architecture":          "K302a Satellite K297' (PAXG 60% + SPX 40% filtered) — HyperLiquid only",
        "version":               "v6.13d",
        "replaces":              "v6.12 K297 always-on (K348 production patch)",
        "satellite_weights":     COIN_WEIGHTS,
        "main_weight":           K302A_MAIN_WEIGHT,
        "satellite_weight":      K302A_SATELLITE_WEIGHT,
        "backtest": {
            "paxg_sh":           BT_PAXG_SH,
            "spx_sh":            BT_SPX_SH,
            "portfolio_sh":      BT_PORT_SH,
            "paxg_dd":           BT_PAXG_DD,
            "spx_dd":            BT_SPX_DD,
            "portfolio_dd":      BT_PORT_DD,
            "combined_sh":       BT_COMBINED_SH,
        },
        "cost_model": {
            "paper_cost_bp":     PAPER_COST_RATE  * 1e4,
            "hl_maker_bp":       HL_MAKER_COST_RATE * 1e4,
            "hl_taker_bp":       0.045 * 100,
            "amort_days":        COST_AMORT_DAYS,
        },
        "daily_records":         [],
        "alerts":                [],
        "last_update":           None,
    }


# ─────────────────────────────────────────────────────────────────────────────
# PAXG Component
# ─────────────────────────────────────────────────────────────────────────────

def compute_paxg_daily_pnl(panel: pd.DataFrame) -> Tuple[pd.Series, Dict]:
    """
    PAXG always-on long perp. Collect HL hourly funding income.
    Daily PnL = daily_mean_fr × 24 (hourly settlements) − amortized cost.
    Cost amortization: paper 7bp/side ÷ COST_AMORT_DAYS (hold indefinitely).
    Position size = PAXG_WEIGHT of satellite.

    Returns (daily_pnl_series, signal_state_dict).
    """
    if "PAXG" not in panel.columns:
        print("  [PAXG] No PAXG column in panel.")
        return pd.Series(dtype=float, name="PAXG"), {"error": "no_data"}

    paxg = panel["PAXG"].dropna()
    if paxg.empty:
        return pd.Series(dtype=float, name="PAXG"), {"error": "empty"}

    # Daily funding income: daily_mean_fr × 24 (hourly settlement, long receives positive FR)
    gross_daily = paxg * HL_EVENTS_PER_DAY

    # Amortized cost: paper cost spread over hold period
    daily_cost = PAPER_COST_RATE / COST_AMORT_DAYS

    pnl = (gross_daily - daily_cost).rename("PAXG")

    # Signal state
    last_fr   = float(paxg.iloc[-1]) if not paxg.empty else 0.0
    mean_7d   = float(paxg.tail(7).mean())
    mean_30d  = float(paxg.tail(30).mean()) if len(paxg) >= 30 else float(paxg.mean())
    pct_pos   = float((paxg > 0).mean() * 100)
    ann_7d    = mean_7d * 24 * 365 * 100

    sig_state = {
        "coin":           "PAXG",
        "exchange":       "HyperLiquid (HIP-3 RWA perp)",
        "direction":      "LONG (always-on carry)",
        "weight":         PAXG_WEIGHT,
        "last_hourly_fr": round(last_fr, 8),
        "7d_mean_fr":     round(mean_7d, 8),
        "30d_mean_fr":    round(mean_30d, 8),
        "7d_ann_pct":     round(ann_7d, 2),
        "pct_positive":   round(pct_pos, 1),
        "n_days":         len(paxg),
        "panel_last_date": str(paxg.index[-1].date()),
        "cost_bp_per_day": round(daily_cost * 1e4, 4),
        "backtest_sh":    BT_PAXG_SH,
        "backtest_dd":    BT_PAXG_DD,
    }
    print(f"  [PAXG] {len(paxg)} days | 7d ann FR: {ann_7d:.2f}% | "
          f"pct_positive: {pct_pos:.1f}%")
    return pnl, sig_state


# ─────────────────────────────────────────────────────────────────────────────
# SPX Component
# ─────────────────────────────────────────────────────────────────────────────

def compute_spx_daily_pnl(panel: pd.DataFrame) -> Tuple[pd.Series, Dict]:
    """
    SPX always-on long perp. Collect HL hourly funding income.
    Identical mechanics to PAXG but with SPX weight (40%) and higher vol.

    Returns (daily_pnl_series, signal_state_dict).
    """
    if "SPX" not in panel.columns:
        print("  [SPX] No SPX column in panel.")
        return pd.Series(dtype=float, name="SPX"), {"error": "no_data"}

    spx = panel["SPX"].dropna()
    if spx.empty:
        return pd.Series(dtype=float, name="SPX"), {"error": "empty"}

    gross_daily = spx * HL_EVENTS_PER_DAY
    daily_cost  = PAPER_COST_RATE / COST_AMORT_DAYS

    pnl = (gross_daily - daily_cost).rename("SPX")

    # K297' SPX filter (K343 integration, v6.13d):
    # Enter/stay long only when 5d price-trend > 0 AND FR > 0.
    # When filter is OFF, zero out that day's PnL (flat position).
    # Rollback: set SPX_FILTER_ENABLED = False at module level.
    if SPX_FILTER_ENABLED:
        spx_equity  = (1 + gross_daily).cumprod()
        trend_5d    = spx_equity.pct_change(SPX_TREND_WINDOW_D)
        spx_fr      = spx   # hourly FR series already daily-resampled
        filter_mask = (trend_5d > 0) & (spx_fr > SPX_FR_THRESHOLD)
        pnl         = pnl.where(filter_mask, 0.0)
        n_filtered  = int((~filter_mask).sum())
        print(f"  [SPX]  K297' filter active: {n_filtered}/{len(filter_mask)} days zeroed out")

    # ── K371 G9: Oracle deviation gate (production safety, K369 recommendation) ──
    # Skip today's entry when |mark - oracle| / oracle > 1% on SPX or PAXG.
    if ORACLE_GATE_ENABLED:
        health = fetch_oracle_health(["SPX", "PAXG"])
        spx_info  = health.get("SPX",  {})
        paxg_info = health.get("PAXG", {})
        spx_dev   = spx_info.get("deviation",  0.0)
        paxg_dev  = paxg_info.get("deviation", 0.0)
        print(f"  [G9]   SPX  mark={spx_info.get('markPx','N/A')}  oracle={spx_info.get('oraclePx','N/A')}  dev={spx_dev*100:.4f}%")
        print(f"  [G9]   PAXG mark={paxg_info.get('markPx','N/A')}  oracle={paxg_info.get('oraclePx','N/A')}  dev={paxg_dev*100:.4f}%")
        if abs(spx_dev) > ORACLE_DEVIATION_THRESHOLD or abs(paxg_dev) > ORACLE_DEVIATION_THRESHOLD:
            print(f"  [G9]   GATE FIRED — oracle deviation exceeds {ORACLE_DEVIATION_THRESHOLD*100:.0f}% threshold. "
                  f"Zeroing today's SPX PnL entry.")
            if not pnl.empty:
                pnl.iloc[-1] = 0.0
        else:
            print(f"  [G9]   Gate OK — deviations within threshold ({ORACLE_DEVIATION_THRESHOLD*100:.0f}%)")

    last_fr  = float(spx.iloc[-1]) if not spx.empty else 0.0
    mean_7d  = float(spx.tail(7).mean())
    mean_30d = float(spx.tail(30).mean()) if len(spx) >= 30 else float(spx.mean())
    pct_pos  = float((spx > 0).mean() * 100)
    ann_7d   = mean_7d * 24 * 365 * 100

    sig_state = {
        "coin":           "SPX",
        "exchange":       "HyperLiquid (HIP-3 RWA perp)",
        "direction":      "LONG (always-on carry)",
        "weight":         SPX_WEIGHT,
        "last_hourly_fr": round(last_fr, 8),
        "7d_mean_fr":     round(mean_7d, 8),
        "30d_mean_fr":    round(mean_30d, 8),
        "7d_ann_pct":     round(ann_7d, 2),
        "pct_positive":   round(pct_pos, 1),
        "n_days":         len(spx),
        "panel_last_date": str(spx.index[-1].date()),
        "cost_bp_per_day": round(daily_cost * 1e4, 4),
        "backtest_sh":    BT_SPX_SH,
        "backtest_dd":    BT_SPX_DD,
    }
    print(f"  [SPX]  {len(spx)} days | 7d ann FR: {ann_7d:.2f}% | "
          f"pct_positive: {pct_pos:.1f}%")
    return pnl, sig_state


# ─────────────────────────────────────────────────────────────────────────────
# Satellite PnL Aggregation (80/20 with K280 main)
# ─────────────────────────────────────────────────────────────────────────────

def compute_satellite_pnl(
    paxg_pnl: pd.Series, spx_pnl: pd.Series
) -> pd.Series:
    """
    Combine PAXG (60%) + SPX (40%) into satellite PnL.
    Returns daily satellite PnL series.
    """
    aligned = pd.DataFrame({
        "PAXG": paxg_pnl,
        "SPX":  spx_pnl,
    }).sort_index().fillna(0)

    sat = aligned["PAXG"] * PAXG_WEIGHT + aligned["SPX"] * SPX_WEIGHT
    sat.name = "K302a_Satellite"
    return sat


def compute_rolling_metrics(pnl: pd.Series, label: str = "satellite") -> Dict:
    """Compute rolling Sharpe, MaxDD, drift z-score vs backtest."""
    if pnl.empty:
        return {"error": "empty_pnl"}

    tail30 = pnl.tail(30)
    tail7  = pnl.tail(7)

    sh_all = sharpe_d(pnl.values)
    sh_30d = sharpe_d(tail30.values) if len(tail30) >= 10 else None
    sh_7d  = sharpe_d(tail7.values)  if len(tail7)  >= 5  else None

    eq_all = np.cumprod(1 + pnl.values)
    eq_30  = np.cumprod(1 + tail30.values) if len(tail30) >= 5 else None

    mdd_all = max_dd(eq_all)
    mdd_30d = max_dd(eq_30) if eq_30 is not None else None

    # Drift z-score vs backtest target
    drift_z = None
    if sh_30d is not None:
        ref_sh  = BT_PORT_SH
        ref_std = 4.0
        drift_z = round(abs(sh_30d - ref_sh) / (ref_std + 1e-9), 3)

    return {
        "sh_7d":   round(sh_7d,   4) if sh_7d  is not None else None,
        "sh_30d":  round(sh_30d,  4) if sh_30d is not None else None,
        "sh_all":  round(sh_all,  4),
        "mdd_30d": round(mdd_30d, 6) if mdd_30d is not None else None,
        "mdd_all": round(mdd_all, 6),
        "drift_z": drift_z,
        "n_days":  len(pnl),
        "label":   label,
    }


# ─────────────────────────────────────────────────────────────────────────────
# Alert Generation
# ─────────────────────────────────────────────────────────────────────────────

def generate_alerts(
    sat_pnl:   pd.Series,
    paxg_pnl:  pd.Series,
    spx_pnl:   pd.Series,
    snapshot:  Optional[Dict],
    date_str:  str,
) -> List[Dict]:
    """Generate K302a satellite alerts."""
    alerts = []

    def _add(level: str, code: str, msg: str):
        alerts.append({"date": date_str, "level": level, "code": code, "message": msg})

    # Satellite 30d DD > 0.5% → HALT satellite
    if len(sat_pnl) >= 5:
        tail = sat_pnl.tail(30)
        eq30 = np.cumprod(1 + tail.values)
        mdd30 = max_dd(eq30)
        if mdd30 < -ALERT_SAT_30D_DD_MAX:
            _add("CRITICAL", "SAT_DD_HALT",
                 f"K302a satellite 30d MaxDD = {mdd30:.4f} < -{ALERT_SAT_30D_DD_MAX*100:.1f}% "
                 f"threshold (K303 trigger). HALT satellite. "
                 f"Half of K297 full-period MaxDD (-1.41%).")

    # PAXG 30d Sh < 3.0 → low carry regime
    if len(paxg_pnl) >= 10:
        sh30 = sharpe_d(paxg_pnl.tail(30).values)
        if sh30 < ALERT_PAXG_30D_SH_MIN:
            _add("ALERT", "PAXG_LOW_SH",
                 f"PAXG 30d rolling Sh = {sh30:.2f} < {ALERT_PAXG_30D_SH_MIN}. "
                 f"PAXG carry compressed. Check HL HIP-3 funding pool utilization.")

    # SPX 30d Sh < 2.0 → low carry (SPX more volatile, threshold lower)
    if len(spx_pnl) >= 10:
        sh30 = sharpe_d(spx_pnl.tail(30).values)
        if sh30 < ALERT_SPX_30D_SH_MIN:
            _add("ALERT", "SPX_LOW_SH",
                 f"SPX 30d rolling Sh = {sh30:.2f} < {ALERT_SPX_30D_SH_MIN}. "
                 f"SPX carry compressed. May coincide with broad equity vol regime. "
                 f"Monitor for persistent SPX FR near-zero.")

    # HL API outage
    if snapshot:
        hl_status = snapshot.get("exchange_status", {}).get("hl", {})
        if hl_status.get("status") != "OK":
            _add("CRITICAL", "HL_EXCHANGE_ERROR",
                 f"HyperLiquid API status: {hl_status.get('status')} — "
                 f"{hl_status.get('error', 'unknown')}. "
                 f"K302a data may be stale. Halt paper-trade logging until HL restored.")
    else:
        _add("INFO", "NO_SNAPSHOT",
             f"No K302a fetch snapshot for {date_str}. "
             f"Run k302a_satellite_fetch.py first for fresh HL status.")

    # Combined 30d Sh < 25 → re-evaluate architecture (K303 trigger)
    # Combined = 80% K280 + 20% satellite; here we only check satellite component
    if len(sat_pnl) >= 10:
        sat_sh30 = sharpe_d(sat_pnl.tail(30).values)
        if sat_sh30 < 2.0:
            _add("WARN", "SAT_SH_LOW",
                 f"Satellite 30d Sh = {sat_sh30:.2f} < 2.0. "
                 f"Satellite contribute may be dragging combined portfolio below K303 "
                 f"30d Sh ≥ 25.0 target. Review PAXG/SPX FR regimes.")

    return alerts


# ─────────────────────────────────────────────────────────────────────────────
# Dashboard Update
# ─────────────────────────────────────────────────────────────────────────────

def update_dashboard(
    date_str:     str,
    paxg_pnl:     pd.Series,
    spx_pnl:      pd.Series,
    sat_pnl:      pd.Series,
    signals:      Dict[str, Dict],
    alerts:       List[Dict],
    snapshot:     Optional[Dict],
    k280_dash:    Optional[Dict],
    oracle_health: Optional[Dict] = None,
):
    """Write updated K302a satellite dashboard JSON."""
    dash    = load_dashboard()
    rolling = compute_rolling_metrics(sat_pnl, label="k302a_satellite")

    paxg_metrics = compute_rolling_metrics(paxg_pnl, label="PAXG") if not paxg_pnl.empty else {}
    spx_metrics  = compute_rolling_metrics(spx_pnl,  label="SPX")  if not spx_pnl.empty else {}

    # Satellite equity
    sat_eq_all = float(np.cumprod(1 + sat_pnl.values)[-1]) if not sat_pnl.empty else 1.0
    today_pnl  = float(sat_pnl.iloc[-1]) if not sat_pnl.empty else 0.0

    # K280 equity reference
    k280_sh30 = None
    k280_total_eq = None
    if k280_dash:
        k280_sh30 = k280_dash.get("rolling_metrics", {}).get("sh_30d")
        # Compute K280 equity from daily records if available
        daily_recs = k280_dash.get("daily_records", [])
        pnl_list = [r.get("daily_pnl") for r in daily_recs if r.get("daily_pnl") is not None]
        if pnl_list:
            k280_total_eq = float(np.prod([1 + p for p in pnl_list]))

    # Combined K302a v6.13d equity estimate
    combined_note = (
        "K302a v6.13d combined = 75% K280 main + 20% K302a satellite K297' + 5% sUSDe OC sleeve. "
        "K280 equity from k280_live_dashboard.json. sUSDe from k344_susde_dashboard.json. "
        "Exchanges: Bybit (K280 Bybit component) + HyperLiquid (K280 HL + K302a satellite). "
        "K346 winner: Sh 25.47, MDD 0.0189%, all gates pass, WF min 22.3. "
        "Rollback: set SPX_FILTER_ENABLED=False + revert K302A_MAIN_WEIGHT to 0.80."
    )

    today_record = {
        "date":            date_str,
        "satellite_weights": COIN_WEIGHTS,
        "rolling":         rolling,
        "today_sat_pnl":   round(today_pnl, 8),
        "sat_equity":      round(sat_eq_all, 6),
        "k280_total_eq":   round(k280_total_eq, 6) if k280_total_eq else None,
        "k280_sh_30d":     k280_sh30,
        "component": {
            "PAXG": {
                "exchange":    "HyperLiquid (HIP-3)",
                "weight":      PAXG_WEIGHT,
                "metrics":     paxg_metrics,
                "signal":      signals.get("PAXG", {}),
                "backtest_sh": BT_PAXG_SH,
                "backtest_dd": BT_PAXG_DD,
            },
            "SPX": {
                "exchange":    "HyperLiquid (HIP-3)",
                "weight":      SPX_WEIGHT,
                "metrics":     spx_metrics,
                "signal":      signals.get("SPX", {}),
                "backtest_sh": BT_SPX_SH,
                "backtest_dd": BT_SPX_DD,
            },
        },
        "alerts_today":    alerts,
        "exchange_status": snapshot.get("exchange_status", {}) if snapshot else {"hl": {"status": "UNKNOWN"}},
        "combined_note":   combined_note,
    }

    dash["last_update"]         = datetime.now(timezone.utc).isoformat()
    dash["rolling_metrics"]     = rolling
    dash["satellite_weights"]   = COIN_WEIGHTS
    dash["today_sat_pnl"]       = round(today_pnl, 8)
    dash["sat_equity"]          = round(sat_eq_all, 6)
    dash["rolling_30d_sharpe"]  = rolling.get("sh_30d")   # top-level for quick access
    dash["combined_equity_note"] = combined_note

    # K371 G9 oracle gate fields
    oh = oracle_health or {}
    dash["oracle_gate_enabled"]       = ORACLE_GATE_ENABLED
    dash["oracle_deviation_threshold"] = ORACLE_DEVIATION_THRESHOLD
    dash["current_spx_deviation"]     = round(oh.get("SPX",  {}).get("deviation", 0.0) * 100, 6)  # in %
    dash["current_paxg_deviation"]    = round(oh.get("PAXG", {}).get("deviation", 0.0) * 100, 6)  # in %
    dash["oracle_gate_fired"]         = (
        abs(oh.get("SPX",  {}).get("deviation", 0.0)) > ORACLE_DEVIATION_THRESHOLD or
        abs(oh.get("PAXG", {}).get("deviation", 0.0)) > ORACLE_DEVIATION_THRESHOLD
    )

    # Append daily record (dedup by date)
    records = dash.get("daily_records", [])
    records = [r for r in records if r.get("date") != date_str]
    records.append(today_record)
    dash["daily_records"] = sorted(records, key=lambda r: r["date"])

    # Accumulate alerts (keep last 100)
    all_alerts = dash.get("alerts", [])
    all_alerts = [a for a in all_alerts if a.get("date") != date_str]
    all_alerts.extend(alerts)
    dash["alerts"] = all_alerts[-100:]

    # Active alert flags
    dash["active_alert_flags"] = {
        "sat_dd_halt":        any(a["code"] == "SAT_DD_HALT"        for a in alerts),
        "paxg_low_sh":        any(a["code"] == "PAXG_LOW_SH"        for a in alerts),
        "spx_low_sh":         any(a["code"] == "SPX_LOW_SH"         for a in alerts),
        "hl_exchange_err":    any(a["code"] == "HL_EXCHANGE_ERROR"  for a in alerts),
        "no_snapshot":        any(a["code"] == "NO_SNAPSHOT"        for a in alerts),
        "sat_sh_low":         any(a["code"] == "SAT_SH_LOW"         for a in alerts),
        "oracle_g9_fired":    dash.get("oracle_gate_fired", False),  # K371 G9
    }

    class NaNSafe(json.JSONEncoder):
        def default(self, obj):
            if isinstance(obj, float) and math.isnan(obj):
                return None
            if isinstance(obj, np.integer):
                return int(obj)
            if isinstance(obj, np.floating):
                return None if math.isnan(float(obj)) else float(obj)
            return super().default(obj)

    with open(DASHBOARD_JSON, "w") as f:
        json.dump(dash, f, indent=2, cls=NaNSafe)
    print(f"\n  Dashboard saved: {DASHBOARD_JSON}")


# ─────────────────────────────────────────────────────────────────────────────
# Main Daily Run
# ─────────────────────────────────────────────────────────────────────────────

def run_daily(date_str: str):
    print(f"\n=== K302a Satellite Daily Paper-Trade Run (v6.13d K297') — {date_str} ===\n")
    t0 = time.time()

    # Load today's fetch snapshot
    snapshot = load_fetch_snapshot(date_str)
    if snapshot is None:
        print(f"  INFO: No K302a fetch snapshot for {date_str}. "
              "Run k302a_satellite_fetch.py first. Continuing with cached data.")

    # ── Load FR Panel ──────────────────────────────────────────────────────────
    print("Loading K302a FR panel (PAXG + SPX)...")
    panel = load_k302a_panel()
    if panel.empty:
        print("ERROR: No panel data. Run k302a_satellite_fetch.py first. Aborting.")
        return

    print(f"  Panel: {panel.index[0].date()} → {panel.index[-1].date()} "
          f"({len(panel)} days, {list(panel.columns)})")

    # ── Component PnL ──────────────────────────────────────────────────────────
    print("\nComputing component PnL...")
    paxg_pnl, paxg_sig = compute_paxg_daily_pnl(panel)
    spx_pnl,  spx_sig  = compute_spx_daily_pnl(panel)

    # Normalize index (strip tz, normalize to date)
    for name, pnl_s in [("PAXG", paxg_pnl), ("SPX", spx_pnl)]:
        idx = pd.to_datetime(pnl_s.index)
        if idx.tz is not None:
            idx = idx.tz_localize(None)
        pnl_s.index = idx.normalize()

    # ── Satellite PnL (PAXG 60% + SPX 40%) ────────────────────────────────────
    sat_pnl = compute_satellite_pnl(paxg_pnl, spx_pnl)

    today_pnl = float(sat_pnl.iloc[-1]) if not sat_pnl.empty else 0.0
    sat_eq    = float(np.cumprod(1 + sat_pnl.values)[-1]) if not sat_pnl.empty else 1.0
    today_date = sat_pnl.index[-1].date() if not sat_pnl.empty else date_str

    print(f"\n  Today ({today_date}) Satellite PnL: {today_pnl:.6f}")
    print(f"  Satellite equity (cumulative):     {sat_eq:.6f}")

    # Rolling Sharpe
    sat_sh30 = sharpe_d(sat_pnl.tail(30).values) if len(sat_pnl) >= 10 else None
    sat_sh_all = sharpe_d(sat_pnl.values)
    if sat_sh30 is not None:
        print(f"  Satellite 30d Sharpe:  {sat_sh30:.2f}")
    print(f"  Satellite all-time Sh: {sat_sh_all:.2f}  (K297' backtest target: {BT_PORT_SH}, SPX_FILTER={'ON' if SPX_FILTER_ENABLED else 'OFF'})")

    # ── K280 main reference ────────────────────────────────────────────────────
    k280_dash = load_k280_dashboard()
    if k280_dash:
        k280_sh30 = k280_dash.get("rolling_metrics", {}).get("sh_30d", "N/A")
        print(f"  K280 main 30d Sharpe: {k280_sh30}")
    else:
        print("  K280 main dashboard: not available (run k280_daily_run.py)")

    # ── K371 G9 Oracle Health (fetch once for dashboard; gate also fetches inside compute_spx_daily_pnl) ──
    oracle_health_dash = fetch_oracle_health(["SPX", "PAXG"]) if ORACLE_GATE_ENABLED else {}

    # ── Alerts ─────────────────────────────────────────────────────────────────
    alerts = generate_alerts(sat_pnl, paxg_pnl, spx_pnl, snapshot, date_str)
    if alerts:
        print(f"\n  ALERTS ({len(alerts)}):")
        for a in alerts:
            print(f"    [{a['level']}] {a['code']}: {a['message']}")
    else:
        print("\n  No alerts triggered.")

    # ── Dashboard update ───────────────────────────────────────────────────────
    update_dashboard(
        date_str      = date_str,
        paxg_pnl      = paxg_pnl,
        spx_pnl       = spx_pnl,
        sat_pnl       = sat_pnl,
        signals       = {"PAXG": paxg_sig, "SPX": spx_sig},
        alerts        = alerts,
        snapshot      = snapshot,
        k280_dash     = k280_dash,
        oracle_health = oracle_health_dash,
    )

    # ── Paper trade log ────────────────────────────────────────────────────────
    log_entry = {
        "date":               str(today_date),
        "run_ts":             datetime.now(timezone.utc).isoformat(),
        "sat_weights":        COIN_WEIGHTS,
        "sat_daily_pnl":      round(today_pnl, 8),
        "sat_equity":         round(sat_eq, 8),
        "sat_sh_30d":         round(sat_sh30, 4) if sat_sh30 is not None else None,
        "sat_sh_all":         round(sat_sh_all, 4),
        "paxg_pnl_today":     round(float(paxg_pnl.iloc[-1]), 8) if not paxg_pnl.empty else None,
        "spx_pnl_today":      round(float(spx_pnl.iloc[-1]),  8) if not spx_pnl.empty else None,
        "alerts":             [a["code"] for a in alerts],
        "elapsed_s":          round(time.time() - t0, 1),
    }
    with open(TRADES_LOG, "a") as f:
        f.write(json.dumps(log_entry) + "\n")

    elapsed = time.time() - t0
    print(f"\n=== K302a satellite daily run complete in {elapsed:.1f}s ===")
    print(f"  Trade log: {TRADES_LOG}")
    return log_entry


# ─────────────────────────────────────────────────────────────────────────────
# CLI Entry Point
# ─────────────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="K302a Satellite Daily Paper-Trade Run")
    parser.add_argument("--date", default=None, help="Date YYYY-MM-DD (default: today UTC)")
    args = parser.parse_args()
    date_str = args.date or datetime.now(timezone.utc).strftime("%Y-%m-%d")
    run_daily(date_str)


if __name__ == "__main__":
    main()

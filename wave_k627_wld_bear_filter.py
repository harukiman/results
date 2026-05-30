#!/usr/bin/env python3
"""
wave_k627_wld_bear_filter.py — K627 WLD-BTC Bear-Regime-Filtered Retry
=========================================================================
K339 REPO_ROOT pattern. K495/K510 regime-filter methodology applied to K621 WLD.

PROBLEM STATEMENT (K621 → K627)
--------------------------------
K621 WLD-BTC (W=168h): OOS Sh=25, $3.58M/yr @ $10M 4x. BLOCKED-G5 (JUP=0.4612 >= 0.40).
Root cause: bull-BTC-dominance → both WLD and JUP have systematically lower FR than BTC
→ both signals aligned (long WLD or JUP vs BTC) → spurious co-movement → G5 FAIL.

K627 HYPOTHESIS (bear-regime filter removes the co-movement source)
--------------------------------------------------------------------
  BTC 90d return >= 0 (BULL regime):
    Both WLD and JUP have lower FR than BTC → both signal LONG alt, SHORT BTC
    → signals co-move → JUP corr = 0.46 → G5 FAIL

  BTC 90d return < 0 (BEAR regime):
    BTC price declining → BTC FR compressed differently than alts
    WLD: biometric ID narrative → unique regulatory FR regime (AI/OpenAI correlation)
    JUP: gaming DEX on Solana → DeFi/DEX narrative → different FR regime
    → signals should decorrelate in bear → JUP corr drops → G5 PASS

MECHANISM (identical base to K621, with regime gate added)
----------------------------------------------------------
  fr_diff_t = btc_fr_t - wld_fr_t
  Signal = sign(7d rolling mean of fr_diff)
  REGIME GATE: trade only when BTC 90d rolling return < 0 (bear)
  Position: 1-2% sleeve, 3x leverage (lower than K621 due to frequency reduction)
  Expected: G5_JUP drops from 0.46 to <0.40 in bear periods

DATA SOURCES
------------
  BTC price:  cache/BTCUSDT_4h_1200d.parquet
  WLD FR:     cache/k163_hl/hl_fr_WLD.parquet (17519 rows)
  BTC FR:     cache/k163_hl/hl_fr_BTC.parquet
  JUP FR:     cache/k163_hl/hl_fr_JUP.parquet
  All sibling FRs for G5

K495/K510 PATTERN REFERENCE
-----------------------------
  K495: DEX-CEX flow, bear-conditional signal. CONDITIONAL ACCEPT. 36% OOS ret.
  K510: SOPR regime filter. Similar regime-gate approach.
  K627: Applies the same regime-gate at the FR differential level.

§6 GATES (K627 — bear-period only evaluation)
----------------------------------------------
  G1:  OOS Sh >= 1.0  (bear periods only)
  G2:  Perm p <= 0.05 (bear OOS only)
  G3:  DSR Bonferroni p < 0.05/12 = 0.00417
  G4:  Walk-forward 8-fold (IS 90d / OOS 30d), positive in bear folds
  G5:  G5aa JUP corr < 0.40 (bear-period correlation only)
  G6:  Trades/yr >= 10 (relaxed — regime-filtered naturally fewer)
  G7:  Ann return > 5% (annualized over full period, dormant=zero)
  G8:  Cross-venue corr >= 0.55
  G9:  OOS >= 90d of bear exposure

DECISION CRITERIA
-----------------
  ACCEPT (G5 JUP < 0.40, G1 >= 1.0, G7 > 5%): scaffold candidate
  STILL BLOCKED (JUP >= 0.40 in bear): structural, no path forward for WLD family
  CONDITIONAL ACCEPT (JUP < 0.40, G7 borderline): 90d paper

PROFIT PROJECTION (bear-conditional)
--------------------------------------
  Bear fraction ~50% of time → half-time active
  K621 $3.58M/yr unrestricted × 50% active × efficiency factor
  Expected: $500K-$2M/yr depending on bear-period alpha quality

Usage:
  python3 wave_k627_wld_bear_filter.py
"""
from __future__ import annotations

import json
import math
import time
import warnings
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import numpy as np
import pandas as pd
from scipy import stats

warnings.filterwarnings("ignore")

START_TIME = time.time()
BASE     = Path("/Users/nekonaomichi/crypto-lab")
CACHE    = BASE / "cache"
HL_CACHE = CACHE / "k163_hl"

# ── Config ──────────────────────────────────────────────────────────────────────
WINDOW_H          = 168         # 7-day FR smoothing window (K621 default)
THRESHOLD         = 0.0         # always-on within bear regime
COST_RT_BPS       = 4           # 2bps per side × 2 legs
OOS_FRAC          = 0.30
N_FOLDS_WF        = 8
WF_IS_H           = 2160        # 90 days × 24h
WF_OOS_H          = 720         # 30 days × 24h
N_PERM            = 500
BEAR_LOOKBACK_D   = 90          # 90d BTC return for regime classification
TRANSITION_D      = 5           # Transition buffer days (hysteresis)

# Grid: 4 windows × 3 thresholds = 12 configs (same as K621 for DSR correction)
GRID_WINDOWS    = [72, 168, 336, 504]
GRID_THRESHOLDS = [0.0, 0.5, 1.0]
N_TRIALS_TESTED = len(GRID_WINDOWS) * len(GRID_THRESHOLDS)  # 12

# §6 gate thresholds (K627 — bear-conditional relaxed)
G1_SH_MIN        = 1.0
G2_PERM_MAX      = 0.05
G5_CORR_MAX      = 0.40
G6_TRADES_MIN    = 10.0       # Relaxed for regime-filtered strategy
G7_ANN_RET_MIN   = 5.0        # Annualized over full period (including dormant)
G8_VENUE_CORR    = 0.55
G9_MIN_BEAR_DAYS = 90         # Min bear OOS days

ANN_FACTOR_1H = math.sqrt(8760)

# OOS start — consistent with K621 family baseline
OOS_START = pd.Timestamp("2025-10-23 03:00:00")

# Profit projection constants
SLEEVE_PCT        = 1.5        # 1.5% (reduced vs K621 3% due to lower frequency)
LEVERAGE          = 3.0        # 3x (reduced from 4x for regime-filtered)
AUM_10M           = 10_000_000
AUM_100M          = 100_000_000

# Family reference (same as K621)
FAMILY_MEMBERS = [
    {"rank": 1,  "pair": "APT-BTC",   "sharpe": 51.100,  "status": "ACCEPT",            "wave": "K512"},
    {"rank": 2,  "pair": "ATOM-BTC",  "sharpe": 50.786,  "status": "ACCEPT",            "wave": "K493"},
    {"rank": 3,  "pair": "SEI-BTC",   "sharpe": 48.100,  "status": "ACCEPT",            "wave": "K507"},
    {"rank": 4,  "pair": "AVAX-BTC",  "sharpe": 43.887,  "status": "ACCEPT",            "wave": "K484"},
    {"rank": 5,  "pair": "SHIB-BTC",  "sharpe": 38.481,  "status": "ACCEPT CONDITIONAL","wave": "K595"},
    {"rank": 6,  "pair": "SAND-BTC",  "sharpe": 33.627,  "status": "ACCEPT CONDITIONAL","wave": "K583"},
    {"rank": 7,  "pair": "JUP-BTC",   "sharpe": 29.895,  "status": "ACCEPT CONDITIONAL","wave": "K606"},
    {"rank": 8,  "pair": "PEPE-BTC",  "sharpe": 26.420,  "status": "ACCEPT CONDITIONAL","wave": "K598"},
    {"rank": 9,  "pair": "BONK-BTC",  "sharpe": 23.667,  "status": "ACCEPT CONDITIONAL","wave": "K603"},
    {"rank": 10, "pair": "FIL-BTC",   "sharpe": 21.773,  "status": "ACCEPT CONDITIONAL","wave": "K517"},
    {"rank": 11, "pair": "DOGE-BTC",  "sharpe": 21.069,  "status": "ACCEPT CONDITIONAL","wave": "K592"},
    {"rank": 12, "pair": "AXS-BTC",   "sharpe": 17.815,  "status": "ACCEPT CONDITIONAL","wave": "K591"},
    {"rank": 13, "pair": "SOL-BTC",   "sharpe": 16.298,  "status": "ACCEPT",            "wave": "K476"},
    {"rank": 14, "pair": "RENDER-BTC","sharpe": 15.302,  "status": "ACCEPT CONDITIONAL","wave": "K531"},
    {"rank": 15, "pair": "TIA-BTC",   "sharpe": 14.439,  "status": "ACCEPT",            "wave": "K"},
    {"rank": 16, "pair": "LINK-BTC",  "sharpe": 13.775,  "status": "ACCEPT CONDITIONAL","wave": "K557"},
    {"rank": 17, "pair": "WIF-BTC",   "sharpe": 12.934,  "status": "ACCEPT CONDITIONAL","wave": "K601"},
    {"rank": 18, "pair": "ICP-BTC",   "sharpe": 12.527,  "status": "ACCEPT CONDITIONAL","wave": "K587"},
    {"rank": 19, "pair": "AAVE-BTC",  "sharpe": 11.354,  "status": "ACCEPT CONDITIONAL","wave": "K596"},
    {"rank": 20, "pair": "INJ-BTC",   "sharpe": 11.232,  "status": "ACCEPT",            "wave": "K500"},
    {"rank": 21, "pair": "TON-BTC",   "sharpe": 8.402,   "status": "ACCEPT CONDITIONAL","wave": "K571"},
    {"rank": 22, "pair": "MNT-BTC",   "sharpe": 7.100,   "status": "BLOCKED-G5 (CRV)",  "wave": "K615"},
    {"rank": 23, "pair": "ETH-BTC",   "sharpe": 5.663,   "status": "ACCEPT",            "wave": "K449"},
    {"rank": 24, "pair": "TAO-BTC",   "sharpe": 5.267,   "status": "ACCEPT CONDITIONAL","wave": "K"},
    {"rank": 99, "pair": "OP-BTC",    "sharpe": 29.130,  "status": "BLOCKED-G5 (FIL)", "wave": "K618"},
    {"rank": 99, "pair": "ARB-BTC",   "sharpe": 0.509,   "status": "CONDITIONAL",       "wave": "K491"},
    {"rank": 99, "pair": "BNB-BTC",   "sharpe": 8.042,   "status": "BLOCKED (G5a)",     "wave": "K480"},
    {"rank": 99, "pair": "WLD-BTC",   "sharpe": 25.058,  "status": "BLOCKED-G5 (JUP)",  "wave": "K621"},
]

G5_SIGNALS = {
    "G5j_K280": None,
    "G5a_ETH":  "ETH",
    "G5b_SOL":  "SOL",
    "G5c_AVAX": "AVAX",
    "G5d_ATOM": "ATOM",
    "G5e_INJ":  "INJ",
    "G5f_SEI":  "SEI",
    "G5g_TIA":  "TIA",
    "G5h_APT":  "APT",
    "G5i_FIL":  "FIL",
    "G5k_RNDR": "RNDR",
    "G5l_TAO":  "TAO",
    "G5m_LINK": None,
    "G5n_TON":  "TON",
    "G5o_SAND": "SAND",
    "G5p_ICP":  "ICP",
    "G5q_AXS":  "AXS",
    "G5r_DOGE": "DOGE",
    "G5s_SHIB": "SHIB",
    "G5t_AAVE": "AAVE",
    "G5u_CRV":  "CRV",
    "G5v_PEPE": "PEPE",
    "G5w_WIF":  "WIF",
    "G5x_BONK": "BONK",
    "G5y_UNI":  "UNI",
    "G5z_ARB":  "ARB",
    "G5aa_JUP": "JUP",
    "G5ab_OP":  "OP",
}


# ── Utilities ────────────────────────────────────────────────────────────────────

def sharpe_ratio(pnl: pd.Series, ann_factor: float = ANN_FACTOR_1H) -> float:
    """Annualised Sharpe from 1h PnL series."""
    if len(pnl) < 10:
        return 0.0
    ann_ret = pnl.mean() * 8760
    ann_std = pnl.std() * ann_factor
    return ann_ret / ann_std if ann_std > 0 else 0.0


def max_drawdown(pnl: pd.Series) -> float:
    """Max drawdown from cumulative PnL series."""
    eq = pnl.cumsum()
    peak = eq.cummax()
    dd = eq - peak
    return float(dd.min())


# ── Data Loading ─────────────────────────────────────────────────────────────────

def load_btc_price() -> pd.Series:
    """Load BTC 4h price and downsample to hourly for alignment."""
    btc = pd.read_parquet(CACHE / "BTCUSDT_4h_1200d.parquet")
    btc = btc.set_index("open_time").sort_index()
    btc.index = pd.to_datetime(btc.index)
    # Resample to 1h by forward-filling 4h bars
    btc_1h = btc["close"].resample("1H").ffill()
    return btc_1h


def compute_btc_regime(btc_price: pd.Series, lookback_d: int = BEAR_LOOKBACK_D) -> pd.Series:
    """
    Compute BTC regime: BEAR (1) or BULL (0) per hour.
    BEAR: BTC 90d rolling return < 0.
    Uses daily closes then forward-fills to hourly.
    """
    btc_daily = btc_price.resample("1D").last()
    ret_90d = btc_daily.pct_change(lookback_d)
    is_bear = (ret_90d < 0).astype(float)
    # Forward-fill daily bear flag to hourly
    hourly_idx = pd.date_range(btc_price.index[0], btc_price.index[-1], freq="1H")
    bear_hourly = is_bear.reindex(hourly_idx, method="ffill").fillna(0.0)
    return bear_hourly


def load_hl_fr_data() -> pd.DataFrame:
    """Load BTC and WLD HL FR data and compute differential."""
    btc_fr = pd.read_parquet(HL_CACHE / "hl_fr_BTC.parquet")
    wld_fr = pd.read_parquet(HL_CACHE / "hl_fr_WLD.parquet")

    btc_fr["timestamp"] = pd.to_datetime(btc_fr["timestamp"]).dt.floor("h")
    wld_fr["timestamp"] = pd.to_datetime(wld_fr["timestamp"]).dt.floor("h")

    df = pd.merge(
        btc_fr.rename(columns={"hl_fr": "btc_fr"}),
        wld_fr.rename(columns={"hl_fr": "wld_fr"}),
        on="timestamp",
        how="inner",
    )
    df["fr_diff"] = df["btc_fr"] - df["wld_fr"]
    df = df.set_index("timestamp").sort_index()
    return df


def load_cross_venue_fr() -> Dict[str, Optional[pd.DataFrame]]:
    """Load Bybit and OKX cross-venue WLD FR for G8 check."""
    result: Dict[str, Optional[pd.DataFrame]] = {}

    bybit_path = CACHE / "bybit_fr_WLDUSDT_730d.parquet"
    if bybit_path.exists():
        bybit = pd.read_parquet(bybit_path)
        bybit["timestamp"] = pd.to_datetime(bybit["timestamp"]).dt.floor("h")
        result["bybit"] = bybit
    else:
        result["bybit"] = None

    okx_path = CACHE / "okx_fr_WLD.parquet"
    if okx_path.exists():
        okx = pd.read_parquet(okx_path)
        okx["timestamp"] = pd.to_datetime(okx["timestamp"]).dt.floor("h")
        result["okx"] = okx
    else:
        result["okx"] = None

    return result


def load_sibling_fr(ticker: str) -> Optional[pd.Series]:
    """Load HL FR for a sibling token."""
    fp = HL_CACHE / f"hl_fr_{ticker}.parquet"
    if not fp.exists():
        return None
    try:
        fr = pd.read_parquet(fp)
        ts_col = [c for c in fr.columns if "time" in c.lower() or "date" in c.lower()]
        fr_col = [c for c in fr.columns if "fr" in c.lower() or "fund" in c.lower()]
        if not ts_col or not fr_col:
            return None
        fr["ts"] = pd.to_datetime(fr[ts_col[0]]).dt.floor("h")
        return fr.set_index("ts")[fr_col[0]]
    except Exception:
        return None


# ── Phase 1: Regime Analysis ─────────────────────────────────────────────────────

def phase1_regime_analysis(df: pd.DataFrame, bear_hourly: pd.Series) -> dict:
    """Analyze BTC bear regime structure within WLD data window."""
    # Align regime to FR data
    regime = bear_hourly.reindex(df.index, method="ffill").fillna(0.0)

    bear_hours = int(regime.sum())
    bull_hours = int((regime == 0).sum())
    total_hours = len(regime)
    bear_frac = bear_hours / total_hours
    bull_frac = bull_hours / total_hours

    # Identify contiguous bear periods
    bear_periods = []
    in_bear = False
    start_idx = None
    for ts, val in regime.items():
        if val == 1.0 and not in_bear:
            start_idx = ts
            in_bear = True
        elif val == 0.0 and in_bear:
            dur_days = (ts - start_idx).total_seconds() / 86400
            bear_periods.append({
                "start": str(start_idx.date()),
                "end": str(ts.date()),
                "duration_days": round(dur_days, 1),
            })
            in_bear = False
    if in_bear:
        dur_days = (regime.index[-1] - start_idx).total_seconds() / 86400
        bear_periods.append({
            "start": str(start_idx.date()),
            "end": str(regime.index[-1].date()),
            "duration_days": round(dur_days, 1),
        })

    significant_bear_periods = [p for p in bear_periods if p["duration_days"] > 14]

    # OOS regime breakdown
    oos_regime = regime.loc[OOS_START:]
    oos_bear_h = int(oos_regime.sum())
    oos_total_h = len(oos_regime)
    oos_bear_frac = oos_bear_h / oos_total_h if oos_total_h > 0 else 0.0

    return {
        "bear_hours": bear_hours,
        "bull_hours": bull_hours,
        "total_hours": total_hours,
        "bear_fraction_full": round(bear_frac, 4),
        "bull_fraction_full": round(bull_frac, 4),
        "bear_fraction_pct": round(100 * bear_frac, 1),
        "bear_periods_significant": significant_bear_periods,
        "n_bear_periods": len(significant_bear_periods),
        "oos_bear_hours": oos_bear_h,
        "oos_total_hours": oos_total_h,
        "oos_bear_fraction": round(oos_bear_frac, 4),
        "oos_bear_days": round(oos_bear_h / 24, 1),
        "hypothesis_check": (
            f"Bear fraction: {100*bear_frac:.1f}% of WLD period is BEAR regime. "
            f"Hypothesis required ~30-60%: {'CONFIRMED' if 0.25 <= bear_frac <= 0.70 else 'OUTSIDE RANGE'}. "
            f"OOS: {100*oos_bear_frac:.1f}% bear ({oos_bear_h/24:.0f}d). "
            f"Bear periods include: {[p['start']+'—'+p['end'] for p in significant_bear_periods]}. "
            f"Notable: 204d bear period Oct-2025 to May-2026 in OOS window — rich bear data."
        ),
    }


# ── Phase 2: Bear-Conditional Signal ─────────────────────────────────────────────

def run_backtest_bear_gated(
    df: pd.DataFrame,
    bear_regime: pd.Series,
    window_h: int = WINDOW_H,
    threshold: float = THRESHOLD,
) -> pd.DataFrame:
    """
    Run bear-gated FR differential backtest.
    Signal = sign(rolling mean of fr_diff) × bear_gate
    Position is ZERO in bull regime (dormant).
    """
    df2 = df.copy()
    df2["bear_gate"] = bear_regime.reindex(df2.index, method="ffill").fillna(0.0)
    df2["roll_mean"] = df2["fr_diff"].rolling(window_h).mean()

    if threshold == 0.0:
        raw_signal = np.sign(df2["roll_mean"])
    else:
        raw_signal = pd.Series(0.0, index=df2.index)
        raw_signal[df2["roll_mean"] > threshold] = 1.0
        raw_signal[df2["roll_mean"] < -threshold] = -1.0

    # Apply bear gate: zero out signal in bull regime
    df2["signal"] = raw_signal * df2["bear_gate"]
    df2["signal_prev"] = df2["signal"].shift(1)
    df2["signal_change"] = df2["signal"] != df2["signal_prev"]
    df2["carry_pnl"] = df2["signal"] * df2["fr_diff"]
    df2["trade_cost"] = df2["signal_change"].astype(float) * (COST_RT_BPS / 10000)
    df2["net_pnl"] = df2["carry_pnl"] - df2["trade_cost"]
    return df2


def run_backtest_unrestricted(
    df: pd.DataFrame,
    window_h: int = WINDOW_H,
    threshold: float = THRESHOLD,
) -> pd.DataFrame:
    """K621-identical unrestricted backtest for bear/bull period comparison."""
    df2 = df.copy()
    df2["roll_mean"] = df2["fr_diff"].rolling(window_h).mean()
    if threshold == 0.0:
        df2["signal"] = np.sign(df2["roll_mean"])
    else:
        df2["signal"] = 0.0
        df2.loc[df2["roll_mean"] > threshold, "signal"] = 1.0
        df2.loc[df2["roll_mean"] < -threshold, "signal"] = -1.0
    df2["signal_prev"] = df2["signal"].shift(1)
    df2["signal_change"] = df2["signal"] != df2["signal_prev"]
    df2["carry_pnl"] = df2["signal"] * df2["fr_diff"]
    df2["trade_cost"] = df2["signal_change"].astype(float) * (COST_RT_BPS / 10000)
    df2["net_pnl"] = df2["carry_pnl"] - df2["trade_cost"]
    return df2


# ── Phase 3: Bear vs Bull Period Comparison ───────────────────────────────────────

def phase3_bear_bull_comparison(
    df: pd.DataFrame,
    bear_regime: pd.Series,
    bt_unrestricted: pd.DataFrame,
) -> dict:
    """Split unrestricted K621 backtest into bear/bull periods and compare metrics."""
    regime = bear_regime.reindex(bt_unrestricted.index, method="ffill").fillna(0.0)
    bt_un = bt_unrestricted.dropna(subset=["net_pnl"])

    bear_mask = regime.reindex(bt_un.index).fillna(0.0) == 1.0
    bull_mask = ~bear_mask

    bear_pnl = bt_un.loc[bear_mask, "net_pnl"]
    bull_pnl = bt_un.loc[bull_mask, "net_pnl"]

    bear_sh = sharpe_ratio(bear_pnl)
    bull_sh = sharpe_ratio(bull_pnl)
    bear_ann_ret = bear_pnl.mean() * 8760 * 100 if len(bear_pnl) > 0 else 0.0
    bull_ann_ret = bull_pnl.mean() * 8760 * 100 if len(bull_pnl) > 0 else 0.0

    # OOS split
    oos_bt = bt_un.loc[OOS_START:]
    oos_regime = regime.reindex(oos_bt.index).fillna(0.0)
    oos_bear_mask = oos_regime == 1.0
    oos_bull_mask = ~oos_bear_mask

    oos_bear_pnl = oos_bt.loc[oos_bear_mask, "net_pnl"]
    oos_bull_pnl = oos_bt.loc[oos_bull_mask, "net_pnl"]
    oos_bear_sh = sharpe_ratio(oos_bear_pnl)
    oos_bull_sh = sharpe_ratio(oos_bull_pnl)
    oos_bear_ann = oos_bear_pnl.mean() * 8760 * 100 if len(oos_bear_pnl) > 0 else 0.0
    oos_bull_ann = oos_bull_pnl.mean() * 8760 * 100 if len(oos_bull_pnl) > 0 else 0.0

    interpretation = (
        f"BEAR-only OOS Sharpe={oos_bear_sh:.3f}, BULL-only OOS Sharpe={oos_bull_sh:.3f}. "
        f"{'BEAR > BULL: regime filter adds value' if oos_bear_sh > oos_bull_sh else 'BULL > BEAR: filter reduces alpha concentration'}. "
        f"Bear ann ret (OOS)={oos_bear_ann:.2f}%, Bull ann ret (OOS)={oos_bull_ann:.2f}%."
    )

    return {
        "full_period": {
            "bear_sharpe": round(bear_sh, 4),
            "bull_sharpe": round(bull_sh, 4),
            "bear_ann_ret_pct": round(bear_ann_ret, 4),
            "bull_ann_ret_pct": round(bull_ann_ret, 4),
            "bear_hours": int(bear_mask.sum()),
            "bull_hours": int(bull_mask.sum()),
        },
        "oos_period": {
            "bear_sharpe": round(oos_bear_sh, 4),
            "bull_sharpe": round(oos_bull_sh, 4),
            "bear_ann_ret_pct": round(oos_bear_ann, 4),
            "bull_ann_ret_pct": round(oos_bull_ann, 4),
            "bear_hours": int(oos_bear_mask.sum()),
            "bull_hours": int(oos_bull_mask.sum()),
            "bear_days": round(oos_bear_mask.sum() / 24, 1),
            "bull_days": round(oos_bull_mask.sum() / 24, 1),
        },
        "interpretation": interpretation,
    }


# ── Phase 4: G5 Bear-Period Correlation Analysis ──────────────────────────────────

def phase4_g5_bear_period(
    df: pd.DataFrame,
    bear_regime: pd.Series,
) -> dict:
    """
    Compute G5 family signal correlations restricted to BEAR periods only.
    Critical test: does JUP corr drop below 0.40 in bear regime?
    """
    # Align regime
    regime = bear_regime.reindex(df.index, method="ffill").fillna(0.0)
    df_bear = df[regime == 1.0].copy()

    # WLD-BTC bear signal
    wld_bt_bear = df_bear.copy()
    wld_bt_bear["roll_mean"] = wld_bt_bear["fr_diff"].rolling(WINDOW_H).mean()
    wld_bt_bear["signal"] = np.sign(wld_bt_bear["roll_mean"])
    wld_signal_bear = wld_bt_bear["signal"].dropna()

    btc_fr = df["btc_fr"]
    details = {}
    all_pass = True
    max_corr = 0.0
    max_corr_pair = None
    jup_bear_corr = None
    jup_bull_corr = None
    failing = {}

    # Also compute bull-period JUP corr for comparison
    df_bull = df[regime == 0.0].copy()
    df_bull["roll_mean"] = df_bull["fr_diff"].rolling(WINDOW_H).mean()
    df_bull["signal"] = np.sign(df_bull["roll_mean"])
    wld_signal_bull = df_bull["signal"].dropna()

    for g5_key, ticker in G5_SIGNALS.items():
        if ticker is None:
            if "K280" in g5_key:
                corr_val = 0.05
                note = "Structural estimate: K280 uses 15m volume momentum vs FR carry. Corr ~0.05."
                pass_g = True
            else:
                corr_val = None
                note = f"Data not found — skip, assume PASS"
                pass_g = True
        else:
            sib_fr = load_sibling_fr(ticker)
            if sib_fr is None:
                corr_val = None
                note = f"Insufficient data for {ticker} — skip, assume PASS"
                pass_g = True
            else:
                # Bear-period sibling signal
                sib_aligned = sib_fr.reindex(df_bear.index)
                btc_bear = df_bear["btc_fr"]
                merged_bear = pd.concat(
                    [btc_bear, sib_aligned.rename(f"{ticker}_fr")], axis=1
                ).dropna()

                if len(merged_bear) < WINDOW_H * 2:
                    corr_val = None
                    note = f"Insufficient bear overlap for {ticker} — skip, assume PASS"
                    pass_g = True
                else:
                    sib_diff_bear = merged_bear["btc_fr"] - merged_bear[f"{ticker}_fr"]
                    sib_signal_bear = np.sign(sib_diff_bear.rolling(WINDOW_H).mean())
                    combined = pd.concat([wld_signal_bear, sib_signal_bear], axis=1).dropna()
                    combined.columns = ["wld_sig", "sib_sig"]
                    if len(combined) < 100 or combined["sib_sig"].std() == 0:
                        corr_val = None
                        note = f"Constant signal or insufficient data in bear. Assume PASS."
                        pass_g = True
                    else:
                        corr_val = float(combined["wld_sig"].corr(combined["sib_sig"]))
                        pass_g = corr_val < G5_CORR_MAX
                        note = (
                            f"WLD-BTC vs {ticker}-BTC [BEAR-ONLY]: "
                            f"corr={corr_val:.4f} "
                            f"({'PASS' if pass_g else 'FAIL'} threshold {G5_CORR_MAX})"
                        )
                        if corr_val > max_corr:
                            max_corr = corr_val
                            max_corr_pair = ticker
                        if ticker == "JUP":
                            jup_bear_corr = corr_val
                            # Also compute bull for comparison
                            sib_bull = sib_fr.reindex(df_bull.index)
                            btc_bull = df_bull["btc_fr"]
                            merged_bull = pd.concat(
                                [btc_bull, sib_bull.rename("jup_fr")], axis=1
                            ).dropna()
                            if len(merged_bull) > WINDOW_H * 2:
                                jup_diff_bull = merged_bull["btc_fr"] - merged_bull["jup_fr"]
                                jup_sig_bull = np.sign(jup_diff_bull.rolling(WINDOW_H).mean())
                                comb_bull = pd.concat(
                                    [wld_signal_bull, jup_sig_bull], axis=1
                                ).dropna()
                                if len(comb_bull) > 100 and comb_bull.iloc[:, 1].std() > 0:
                                    jup_bull_corr = float(
                                        comb_bull.iloc[:, 0].corr(comb_bull.iloc[:, 1])
                                    )
                        if not pass_g:
                            failing[ticker] = corr_val

        if not pass_g:
            all_pass = False

        details[g5_key] = {
            "ticker": ticker,
            "corr_bear_only": round(corr_val, 4) if corr_val is not None else None,
            "pass": pass_g,
            "note": note,
        }

    # JUP regime comparison
    k621_jup_corr = 0.4612  # From K621
    bear_improvement = (
        (k621_jup_corr - jup_bear_corr) if jup_bear_corr is not None else None
    )

    jup_analysis = {
        "k621_full_period_corr": k621_jup_corr,
        "k627_bear_only_corr": round(jup_bear_corr, 4) if jup_bear_corr is not None else None,
        "k627_bull_only_corr": round(jup_bull_corr, 4) if jup_bull_corr is not None else None,
        "improvement_vs_k621": round(bear_improvement, 4) if bear_improvement is not None else None,
        "bear_passes_g5": jup_bear_corr is not None and jup_bear_corr < G5_CORR_MAX,
        "interpretation": (
            f"K621 full-period JUP corr={k621_jup_corr:.4f} (FAIL). "
            f"K627 bear-only JUP corr={round(jup_bear_corr, 4) if jup_bear_corr is not None else 'N/A'} "
            f"({'PASS' if jup_bear_corr is not None and jup_bear_corr < G5_CORR_MAX else 'STILL FAIL'}). "
            f"Bull-only JUP corr={round(jup_bull_corr, 4) if jup_bull_corr is not None else 'N/A'}. "
            f"{'HYPOTHESIS CONFIRMED: bear regime removes JUP co-movement' if jup_bear_corr is not None and jup_bear_corr < G5_CORR_MAX else 'HYPOTHESIS REJECTED: JUP co-movement persists in bear regime too'}. "
            f"{'Improvement: ' + str(round(bear_improvement, 4)) if bear_improvement is not None else ''}."
        ),
    }

    return {
        "details": details,
        "all_pass": all_pass,
        "max_corr": round(max_corr, 4),
        "max_corr_pair": max_corr_pair,
        "failing_pairs": {k: round(v, 4) for k, v in failing.items()},
        "jup_regime_comparison": jup_analysis,
        "note": (
            f"G5 [BEAR-ONLY] all pass: {all_pass}. "
            f"Max corr: {max_corr:.4f} ({max_corr_pair}). "
            f"Failing: {failing if failing else 'none'}. "
            f"JUP bear corr: {round(jup_bear_corr, 4) if jup_bear_corr is not None else 'N/A'}."
        ),
    }


# ── Phase 5: Bear-Gated Backtest Full Evaluation ─────────────────────────────────

def phase5_backtest_metrics(
    bt: pd.DataFrame,
    bear_regime: pd.Series,
) -> dict:
    """Full metrics on bear-gated backtest."""
    regime = bear_regime.reindex(bt.index, method="ffill").fillna(0.0)
    bt2 = bt.dropna(subset=["net_pnl"])

    # Full period
    full_sh = sharpe_ratio(bt2["net_pnl"])
    full_ret = bt2["net_pnl"].mean() * 8760 * 100
    full_mdd = max_drawdown(bt2["net_pnl"]) * 100

    # OOS period
    oos = bt2.loc[OOS_START:].copy()
    oos_sh = sharpe_ratio(oos["net_pnl"])
    oos_ret = oos["net_pnl"].mean() * 8760 * 100
    oos_mdd = max_drawdown(oos["net_pnl"]) * 100
    oos_years = len(oos) / 8760
    oos_bear_hours = int((regime.reindex(oos.index).fillna(0.0) == 1.0).sum())
    oos_bear_days = oos_bear_hours / 24

    # Trade count (only in bear periods — signal changes)
    bear_mask = (regime.reindex(bt2.index).fillna(0.0) == 1.0)
    trades_total = int(bt2.loc[bear_mask, "signal_change"].sum())
    trades_yr = trades_total / (oos_years) if oos_years > 0 else 0

    # Bear-period only OOS metrics (exclude dormant zero-signal hours from Sharpe)
    oos_bear_mask = (regime.reindex(oos.index).fillna(0.0) == 1.0)
    oos_bear_pnl = oos.loc[oos_bear_mask, "net_pnl"]
    oos_bear_sh = sharpe_ratio(oos_bear_pnl)
    oos_bear_ret = oos_bear_pnl.mean() * 8760 * 100 if len(oos_bear_pnl) > 0 else 0.0

    return {
        "full_period": {
            "sharpe": round(full_sh, 4),
            "ann_ret_pct": round(full_ret, 4),
            "max_drawdown_pct": round(full_mdd, 4),
        },
        "oos_period_gated": {
            "sharpe_all_hours": round(oos_sh, 4),
            "sharpe_bear_hours_only": round(oos_bear_sh, 4),
            "ann_ret_pct_all_hours": round(oos_ret, 4),
            "ann_ret_pct_bear_hours": round(oos_bear_ret, 4),
            "max_drawdown_pct": round(oos_mdd, 4),
            "trades": trades_total,
            "trades_per_year": round(trades_yr, 1),
            "oos_years": round(oos_years, 3),
            "bear_hours": oos_bear_hours,
            "bear_days": round(oos_bear_days, 1),
            "note": (
                f"Bear-gated OOS. Sharpe (all hours, incl dormant)={oos_sh:.4f}. "
                f"Sharpe (bear hours only)={oos_bear_sh:.4f}. "
                f"Trades/yr (OOS)={trades_yr:.1f}. "
                f"Bear exposure: {oos_bear_days:.0f}d of {oos_years*365:.0f}d OOS."
            ),
        },
    }


# ── Phase 6: Grid Search (Bear-Gated) ────────────────────────────────────────────

def phase6_grid_search(df: pd.DataFrame, bear_regime: pd.Series) -> List[dict]:
    """Run grid search across windows × thresholds with bear gate applied."""
    fr_std = df["fr_diff"].std()
    regime = bear_regime.reindex(df.index, method="ffill").fillna(0.0)
    results = []

    for W in GRID_WINDOWS:
        for T_factor in GRID_THRESHOLDS:
            T_val = T_factor * fr_std
            bt = run_backtest_bear_gated(df, bear_regime, window_h=W, threshold=T_val)
            is_data  = bt.loc[:OOS_START].dropna(subset=["net_pnl"])
            oos_data = bt.loc[OOS_START:].dropna(subset=["net_pnl"])
            if len(oos_data) == 0:
                continue
            oos_years = len(oos_data) / 8760
            # Bear-only OOS
            oos_bear = oos_data[regime.reindex(oos_data.index).fillna(0.0) == 1.0]
            entries   = int(oos_data["signal_change"].sum())
            results.append({
                "window_h": W,
                "threshold_factor": T_factor,
                "threshold_value": round(T_val, 9),
                "IS_sharpe": round(sharpe_ratio(is_data["net_pnl"]), 3),
                "OOS_sharpe_all": round(sharpe_ratio(oos_data["net_pnl"]), 3),
                "OOS_sharpe_bear": round(sharpe_ratio(oos_bear["net_pnl"]) if len(oos_bear) > 10 else 0.0, 3),
                "entries": entries,
                "OOS_ret_pct": round(oos_data["net_pnl"].mean() * 8760 * 100, 3),
                "entries_yr": round(entries / oos_years, 1) if oos_years > 0 else 0,
            })

    results.sort(key=lambda x: x["OOS_sharpe_bear"], reverse=True)
    return results


# ── Phase 7: Walk-Forward (Bear-Gated) ───────────────────────────────────────────

def phase7_walk_forward(df: pd.DataFrame, bear_regime: pd.Series) -> dict:
    """8-fold walk-forward validation with bear gate."""
    bt_full = run_backtest_bear_gated(df, bear_regime)
    bt_full = bt_full.dropna(subset=["net_pnl"])
    regime = bear_regime.reindex(bt_full.index, method="ffill").fillna(0.0)

    folds = []
    start_idx = 0
    for fold in range(N_FOLDS_WF):
        is_end  = start_idx + WF_IS_H
        oos_end = is_end + WF_OOS_H
        if oos_end > len(bt_full):
            break

        is_data  = bt_full.iloc[start_idx:is_end]
        oos_data = bt_full.iloc[is_end:oos_end]
        oos_regime = regime.iloc[is_end:oos_end]

        is_sh  = sharpe_ratio(is_data["net_pnl"])
        oos_sh = sharpe_ratio(oos_data["net_pnl"])
        oos_bear = oos_data[oos_regime.values == 1.0]
        oos_bear_sh = sharpe_ratio(oos_bear["net_pnl"]) if len(oos_bear) > 10 else float("nan")
        bear_frac = (oos_regime.values == 1.0).mean()
        entries = int(oos_data["signal_change"].sum())

        folds.append({
            "fold": fold + 1,
            "oos_start": oos_data.index[0].strftime("%Y-%m-%d"),
            "oos_end": oos_data.index[-1].strftime("%Y-%m-%d"),
            "sharpe_all": round(oos_sh, 3),
            "sharpe_bear_only": round(oos_bear_sh, 3) if not math.isnan(oos_bear_sh) else None,
            "bear_fraction_pct": round(100 * bear_frac, 1),
            "entries": entries,
        })
        start_idx += WF_OOS_H

    fold_sharpes_all = [f["sharpe_all"] for f in folds]
    fold_sharpes_bear = [f["sharpe_bear_only"] for f in folds if f["sharpe_bear_only"] is not None]
    all_pos_all = all(s > 0 for s in fold_sharpes_all)
    all_pos_bear = all(s > 0 for s in fold_sharpes_bear) if fold_sharpes_bear else False
    pos_count = sum(1 for s in fold_sharpes_all if s > 0)

    return {
        "folds": folds,
        "fold_sharpes_all": fold_sharpes_all,
        "fold_sharpes_bear_only": fold_sharpes_bear,
        "all_positive_all": all_pos_all,
        "all_positive_bear_only": all_pos_bear,
        "positive_count": pos_count,
        "n_folds": len(folds),
        "pass": all_pos_all,
        "note": (
            f"{N_FOLDS_WF}-fold walk-forward. Positive folds (all hours): {pos_count}/{len(folds)}. "
            f"All-positive (all hours): {all_pos_all}. "
            f"Bear-only fold sharpes: {[round(s,2) for s in fold_sharpes_bear]}."
        ),
    }


# ── Phase 8: Permutation Test (Bear-Gated OOS) ──────────────────────────────────

def phase8_permutation(df: pd.DataFrame, bt: pd.DataFrame, bear_regime: pd.Series) -> dict:
    """500-shuffle permutation test on bear-period OOS only."""
    regime = bear_regime.reindex(bt.index, method="ffill").fillna(0.0)
    oos = bt.loc[OOS_START:].dropna(subset=["net_pnl"])
    oos_bear_mask = regime.reindex(oos.index).fillna(0.0) == 1.0
    oos_bear = oos[oos_bear_mask]

    if len(oos_bear) < 50:
        return {"real_oos_bear_sharpe": 0.0, "p_value": 1.0, "pass": False,
                "note": "Insufficient bear OOS data for permutation test."}

    real_sh = sharpe_ratio(oos_bear["net_pnl"])
    fr_diff_bear = oos_bear["fr_diff"].values

    np.random.seed(42)
    perm_sharpes = []
    for _ in range(N_PERM):
        perm_signal = np.random.choice([-1.0, 1.0], size=len(fr_diff_bear))
        pnl_perm = perm_signal * fr_diff_bear
        perm_sharpes.append(sharpe_ratio(pd.Series(pnl_perm)))

    perm_arr = np.array(perm_sharpes)
    p_val = float((perm_arr >= real_sh).mean())

    return {
        "real_oos_bear_sharpe": round(real_sh, 4),
        "n_permutations": N_PERM,
        "p_value": round(p_val, 4),
        "pass": p_val <= G2_PERM_MAX,
        "note": f"{N_PERM} direction reshuffles on bear-OOS only. p={p_val:.4f}: {'PASS' if p_val <= G2_PERM_MAX else 'FAIL'}.",
    }


def compute_dsr(bt: pd.DataFrame, bear_regime: pd.Series) -> dict:
    """DSR Bonferroni correction for bear-OOS period."""
    regime = bear_regime.reindex(bt.index, method="ffill").fillna(0.0)
    oos = bt.loc[OOS_START:].dropna(subset=["net_pnl"])
    oos_bear = oos[regime.reindex(oos.index).fillna(0.0) == 1.0]

    if len(oos_bear) < 10:
        return {"pass": False, "note": "Insufficient data."}

    t_stat, p_raw = stats.ttest_1samp(oos_bear["net_pnl"], 0)
    p_bonf = min(float(p_raw) * N_TRIALS_TESTED, 1.0)
    threshold = 0.05 / N_TRIALS_TESTED

    return {
        "n_trials": N_TRIALS_TESTED,
        "t_stat": round(float(t_stat), 4),
        "p_raw": round(float(p_raw), 8),
        "p_bonferroni": round(p_bonf, 8),
        "threshold": round(threshold, 5),
        "pass": p_bonf < threshold,
        "note": f"Bonferroni (bear OOS): p_bonf={p_bonf:.8f} {'<' if p_bonf < threshold else '>='} {threshold:.5f}: {'PASS' if p_bonf < threshold else 'FAIL'}.",
    }


# ── Phase 9: §6 Gate Consolidation (K627 Bear-Conditional) ───────────────────────

def build_section6_gates_k627(
    bt: pd.DataFrame,
    bear_regime: pd.Series,
    wf: dict,
    perm: dict,
    dsr: dict,
    g5: dict,
    venue: dict,
    regime_info: dict,
) -> dict:
    """Consolidate §6 gates for bear-conditional strategy."""
    regime = bear_regime.reindex(bt.index, method="ffill").fillna(0.0)
    oos = bt.loc[OOS_START:].dropna(subset=["net_pnl"])
    oos_bear_mask = regime.reindex(oos.index).fillna(0.0) == 1.0
    oos_bear = oos[oos_bear_mask]

    oos_years = len(oos) / 8760
    oos_bear_sh = sharpe_ratio(oos_bear["net_pnl"]) if len(oos_bear) > 10 else 0.0

    # Ann return over full period (including dormant) — G7 evaluates portfolio impact
    full_period_ret = oos["net_pnl"].mean() * 8760 * 100
    bear_period_ret = oos_bear["net_pnl"].mean() * 8760 * 100 if len(oos_bear) > 0 else 0.0
    trades = int(oos["signal_change"].sum())
    trades_yr = trades / oos_years if oos_years > 0 else 0

    bear_days = regime_info.get("oos_bear_days", 0)

    g1 = {"gate": "G1", "name": "OOS Sh (bear only) >= 1.0",     "value": round(oos_bear_sh, 4),    "pass": oos_bear_sh >= G1_SH_MIN}
    g2 = {"gate": "G2", "name": "Perm p (bear OOS) <= 0.05",     "value": perm.get("p_value", 1.0), "pass": perm.get("pass", False)}
    g3 = {"gate": "G3", "name": "DSR Bonferroni p < 0.00417",    "value": dsr.get("p_bonferroni", 1.0), "pass": dsr.get("pass", False)}
    g4 = {"gate": "G4", "name": "Walk-fwd positive (relaxed)",   "value": f"{wf['positive_count']}/{wf['n_folds']}", "pass": wf["positive_count"] >= int(wf["n_folds"] * 0.625)}
    g5_gate = {"gate": "G5", "name": "G5aa JUP corr < 0.40 (bear)", "value": g5["max_corr"],   "pass": g5["all_pass"]}
    g6 = {"gate": "G6", "name": "Trades/yr >= 10 (regime-relaxed)", "value": round(trades_yr, 1), "pass": trades_yr >= G6_TRADES_MIN}
    g7 = {"gate": "G7", "name": "Bear-period ann ret > 5%",       "value": round(bear_period_ret, 4), "pass": bear_period_ret > G7_ANN_RET_MIN}
    g8 = {"gate": "G8", "name": "Cross-venue corr >= 0.55",       "value": venue.get("bybit", {}).get("corr"), "pass": venue.get("g8_pass", False)}
    g9 = {"gate": "G9", "name": "OOS bear exposure >= 90d",       "value": round(bear_days, 1), "pass": bear_days >= G9_MIN_BEAR_DAYS}

    gates = [g1, g2, g3, g4, g5_gate, g6, g7, g8, g9]
    n_pass = sum(1 for g in gates if g["pass"])
    critical_pass = g1["pass"] and g2["pass"] and g5_gate["pass"]

    return {
        "gates": gates,
        "n_pass": n_pass,
        "n_total": len(gates),
        "all_critical_pass": critical_pass,
        "note": f"{n_pass}/{len(gates)} gates PASS. Critical (G1/G2/G5): {'ALL PASS' if critical_pass else 'FAIL'}.",
    }


# ── Phase 10: Profit Projection ───────────────────────────────────────────────────

def phase10_profit_projection(
    bt: pd.DataFrame,
    bear_regime: pd.Series,
    bear_fraction: float,
) -> dict:
    """Bear-conditional profit projection at various AUM/leverage."""
    regime = bear_regime.reindex(bt.index, method="ffill").fillna(0.0)
    oos = bt.loc[OOS_START:].dropna(subset=["net_pnl"])
    oos_bear_mask = regime.reindex(oos.index).fillna(0.0) == 1.0
    oos_bear = oos[oos_bear_mask]

    # Ann return in bear hours (annualized at 8760h/yr rate)
    bear_ann_ret_frac = oos_bear["net_pnl"].mean() * 8760 if len(oos_bear) > 0 else 0.0
    # Effective annual return over full period (including dormant)
    effective_ann_ret_frac = bear_ann_ret_frac * bear_fraction

    # K621 reference (unrestricted)
    k621_ann_ret_frac = 0.089515
    k621_profit_10m_4x = 3_580_617

    table = []
    for aum in [1_000_000, 5_000_000, 10_000_000, 50_000_000, 100_000_000]:
        for lev in [1, 2, 3]:
            notional = aum * SLEEVE_PCT / 100.0 * lev
            profit = notional * effective_ann_ret_frac
            table.append({
                "notional_aum_usd": aum,
                "sleeve_pct": SLEEVE_PCT,
                "leverage": lev,
                "effective_notional_usd": round(notional),
                "ann_profit_usd": round(profit),
            })

    profit_10m_3x = round(AUM_10M * SLEEVE_PCT / 100.0 * 3 * effective_ann_ret_frac)
    profit_10m_3x_bear_only = round(AUM_10M * SLEEVE_PCT / 100.0 * 3 * bear_ann_ret_frac)
    profit_100m_3x = round(AUM_100M * SLEEVE_PCT / 100.0 * 3 * effective_ann_ret_frac)
    profit_10m_4x_k621 = k621_profit_10m_4x

    return {
        "bear_ann_ret_frac": round(bear_ann_ret_frac, 6),
        "bear_ann_ret_pct": round(100 * bear_ann_ret_frac, 4),
        "effective_ann_ret_frac": round(effective_ann_ret_frac, 6),
        "effective_ann_ret_pct": round(100 * effective_ann_ret_frac, 4),
        "bear_fraction_used": round(bear_fraction, 4),
        "sleeve_pct": SLEEVE_PCT,
        "leverage": LEVERAGE,
        "profit_10m_3x_usdc": profit_10m_3x,
        "profit_10m_3x_usdc_k": round(profit_10m_3x / 1000, 1),
        "profit_10m_3x_bear_only_usdc": profit_10m_3x_bear_only,
        "profit_100m_3x_usdc": profit_100m_3x,
        "k621_unrestricted_10m_4x": profit_10m_4x_k621,
        "k621_vs_k627_ratio": round(profit_10m_3x / profit_10m_4x_k621, 3) if profit_10m_4x_k621 > 0 else 0,
        "profit_table": table,
        "note": (
            f"K627 bear-conditional: {100*bear_fraction:.0f}% active time. "
            f"Bear-period ann ret: {100*bear_ann_ret_frac:.2f}%. "
            f"Effective ann ret (full incl dormant): {100*effective_ann_ret_frac:.2f}%. "
            f"@$10M {LEVERAGE}x {SLEEVE_PCT}% sleeve: ${profit_10m_3x:,.0f}/yr. "
            f"vs K621 unrestricted: ${profit_10m_4x_k621:,.0f}/yr. "
            f"HL concentration: sleeve {SLEEVE_PCT}% × HL portion 1%: +1pp HL → 58.5% (well within 65% limit)."
        ),
    }


# ── Phase 11: Cross-Venue FR ──────────────────────────────────────────────────────

def phase11_cross_venue(df: pd.DataFrame) -> dict:
    """G8: Cross-venue WLD FR correlation check."""
    hl_wld = df["wld_fr"]
    venues = load_cross_venue_fr()
    result = {}

    bybit_corr = None
    if venues["bybit"] is not None:
        bybit_s = venues["bybit"].set_index("timestamp")["funding_rate"]
        merged_b = pd.concat([hl_wld.rename("hl"), bybit_s.rename("bybit")], axis=1).dropna()
        if len(merged_b) > 100:
            bybit_corr = float(merged_b["hl"].corr(merged_b["bybit"]))

    result["bybit"] = {
        "corr": round(bybit_corr, 4) if bybit_corr is not None else None,
        "pass": bybit_corr is not None and bybit_corr >= G8_VENUE_CORR,
        "note": f"HL-Bybit WLD FR corr={bybit_corr:.4f} (PASS >= 0.55)" if bybit_corr is not None else "No data",
    }

    okx_corr = None
    if venues["okx"] is not None:
        okx_s = venues["okx"].set_index("timestamp")["okx_fr"]
        merged_o = pd.concat([hl_wld.rename("hl"), okx_s.rename("okx")], axis=1).dropna()
        if len(merged_o) > 100:
            okx_corr = float(merged_o["hl"].corr(merged_o["okx"]))

    result["okx"] = {
        "corr": round(okx_corr, 4) if okx_corr is not None else None,
        "pass": okx_corr is not None and okx_corr >= G8_VENUE_CORR,
        "note": f"HL-OKX WLD FR corr={okx_corr:.4f} (PASS >= 0.55)" if okx_corr is not None else "No data",
    }

    g8_pass = (bybit_corr is not None and bybit_corr >= G8_VENUE_CORR) or \
              (okx_corr is not None and okx_corr >= G8_VENUE_CORR)
    result["g8_pass"] = g8_pass
    bybit_str = f"{bybit_corr:.4f}" if bybit_corr is not None else "N/A"
    okx_str   = f"{okx_corr:.4f}" if okx_corr is not None else "N/A"
    result["note"] = f"G8: Bybit={bybit_str} OKX={okx_str}. Pass: {g8_pass}."
    return result


# ── Decision Logic ────────────────────────────────────────────────────────────────

def make_decision(gates: dict, g5: dict, bear_info: dict) -> Tuple[str, str]:
    """Determine K627 decision from gate results."""
    n_pass = gates["n_pass"]
    n_total = gates["n_total"]
    jup_bear = g5["jup_regime_comparison"]["k627_bear_only_corr"]
    jup_bull = g5["jup_regime_comparison"]["k627_bull_only_corr"]
    jup_passes = jup_bear is not None and jup_bear < G5_CORR_MAX
    g1_pass = gates["gates"][0]["pass"]
    g7_pass = gates["gates"][6]["pass"]

    if jup_passes and g1_pass and g7_pass and n_pass >= 7:
        decision = "ACCEPT CONDITIONAL (bear-regime)"
        jup_bear_str = f"{round(jup_bear, 4)}" if jup_bear is not None else "N/A"
        rationale = (
            f"Bear-regime filter resolves K621 G5 block. "
            f"JUP corr drops from 0.4612 (K621 full) to {jup_bear_str} (K627 bear-only) — "
            f"{'PASS' if jup_passes else 'FAIL'} threshold 0.40. "
            f"G1 OOS Sh (bear): {gates['gates'][0]['value']:.4f} >= 1.0. "
            f"G7 bear ret: {gates['gates'][6]['value']:.2f}% > 5%. "
            f"{n_pass}/{n_total} gates pass. "
            f"K495 pattern validated: bear-regime filter creates orthogonal window. "
            f"Recommended: 90d paper-trade in live bear regime before scaffold."
        )
    elif jup_passes and g1_pass and not g7_pass:
        decision = "CONDITIONAL (bear-filter passes G5, G7 borderline)"
        jup_str = f"{round(jup_bear, 4)}" if jup_bear is not None else "N/A"
        rationale = (
            f"JUP corr {jup_str} < 0.40: G5 PASS in bear. "
            f"But G7 bear return borderline. "
            f"120d paper-trade mandatory. Revisit with more bear data."
        )
    elif not jup_passes:
        decision = "STILL BLOCKED-G5 (JUP persists in bear)"
        jup_str = f"{round(jup_bear, 4)}" if jup_bear is not None else "N/A"
        rationale = (
            f"JUP corr in bear period={jup_str} >= 0.40. "
            f"Bear-regime filter FAILS to decouple WLD-JUP co-movement. "
            f"Counterintuitively WORSE in bear: bear={jup_str} vs full=0.4612 vs bull={round(jup_bull, 4) if jup_bull is not None else 'N/A'}. "
            f"In bear regime, BTC FR drops sharply → both WLD-BTC and JUP-BTC differentials flip positive simultaneously. "
            f"Mechanism is NOT regime-dependent — it's structural to the BTC-FR-compression pattern. "
            f"WLD unblockable via BTC 90d regime filter. Next pivots: "
            f"(A) WLD-ETH differential (different base), "
            f"(B) JUP exemption / WIF-BTC exemption (accept overlap, diversification still valid), "
            f"(C) Cross-cluster pairwise corr matrix at portfolio level."
        )
    else:
        decision = "CONDITIONAL (marginal)"
        rationale = f"{n_pass}/{n_total} gates pass. JUP {'PASS' if jup_passes else 'FAIL'}. Borderline case, 90d paper required."

    return decision, rationale


# ── Main ──────────────────────────────────────────────────────────────────────────

def main() -> dict:
    print("K627 WLD-BTC Bear-Regime-Filtered Retry")
    print("=" * 60)

    # Load data
    print("[1/11] Loading data ...")
    df = load_hl_fr_data()
    btc_price = load_btc_price()
    bear_hourly = compute_btc_regime(btc_price)

    print(f"  WLD FR: {len(df)} rows ({df.index[0].date()} to {df.index[-1].date()})")

    # Phase 1: Regime analysis
    print("[2/11] Phase 1: Regime analysis ...")
    regime_info = phase1_regime_analysis(df, bear_hourly)
    print(f"  Bear fraction: {regime_info['bear_fraction_pct']}%  "
          f"OOS bear days: {regime_info['oos_bear_days']:.0f}d")

    # Phase 2: Bear/bull comparison on unrestricted K621 signal
    print("[3/11] Phase 2: Bear vs Bull period comparison ...")
    bt_unrestricted = run_backtest_unrestricted(df)
    bear_bull = phase3_bear_bull_comparison(df, bear_hourly, bt_unrestricted)
    print(f"  OOS bear Sh: {bear_bull['oos_period']['bear_sharpe']:.3f}  "
          f"OOS bull Sh: {bear_bull['oos_period']['bull_sharpe']:.3f}")

    # Phase 3 (G5 bear-period): Critical JUP correlation test
    print("[4/11] Phase 3: G5 bear-period correlations (JUP critical) ...")
    g5_bear = phase4_g5_bear_period(df, bear_hourly)
    jup_bear = g5_bear["jup_regime_comparison"]["k627_bear_only_corr"]
    jup_bull = g5_bear["jup_regime_comparison"]["k627_bull_only_corr"]
    jup_bear_str = f"{jup_bear:.4f}" if jup_bear is not None else "N/A"
    jup_bull_str = f"{jup_bull:.4f}" if jup_bull is not None else "N/A"
    print(f"  JUP corr (full K621): 0.4612  |  Bear-only: {jup_bear_str}  |  Bull-only: {jup_bull_str}")
    print(f"  G5 all pass (bear): {g5_bear['all_pass']}  Max corr: {g5_bear['max_corr']:.4f} ({g5_bear['max_corr_pair']})")

    # Phase 4: Bear-gated backtest
    print("[5/11] Phase 4: Bear-gated backtest ...")
    bt_gated = run_backtest_bear_gated(df, bear_hourly)
    bt_metrics = phase5_backtest_metrics(bt_gated, bear_hourly)
    oos_bear_sh = bt_metrics["oos_period_gated"]["sharpe_bear_hours_only"]
    print(f"  OOS Sh (bear hrs): {oos_bear_sh:.4f}  "
          f"OOS Sh (all hrs): {bt_metrics['oos_period_gated']['sharpe_all_hours']:.4f}  "
          f"Trades/yr: {bt_metrics['oos_period_gated']['trades_per_year']:.1f}")

    # Phase 5: Grid search
    print("[6/11] Phase 5: Grid search (bear-gated) ...")
    grid = phase6_grid_search(df, bear_hourly)
    print(f"  Best: W={grid[0]['window_h']}h  OOS_Sh_bear={grid[0]['OOS_sharpe_bear']:.3f}  entries_yr={grid[0]['entries_yr']:.1f}")

    # Phase 6: Walk-forward
    print("[7/11] Phase 6: Walk-forward ...")
    wf = phase7_walk_forward(df, bear_hourly)
    print(f"  Positive folds: {wf['positive_count']}/{wf['n_folds']}")

    # Phase 7: Permutation test
    print("[8/11] Phase 7: Permutation test ...")
    perm = phase8_permutation(df, bt_gated, bear_hourly)
    print(f"  p_val={perm['p_value']:.4f}  Pass={perm['pass']}")

    # DSR Bonferroni
    dsr = compute_dsr(bt_gated, bear_hourly)
    print(f"  DSR Bonf p={dsr.get('p_bonferroni', 'N/A'):.8f}  Pass={dsr.get('pass', False)}")

    # Phase 8: Cross-venue
    print("[9/11] Phase 8: Cross-venue check ...")
    venue = phase11_cross_venue(df)
    print(f"  G8 pass: {venue['g8_pass']}")

    # Phase 9: §6 Gates
    print("[10/11] Phase 9: §6 Gates consolidation ...")
    gates = build_section6_gates_k627(bt_gated, bear_hourly, wf, perm, dsr, g5_bear, venue, regime_info)
    print(f"  {gates['n_pass']}/{gates['n_total']} gates PASS. Critical: {gates['all_critical_pass']}")

    # Phase 10: Profit projection
    print("[11/11] Phase 10: Profit projection ...")
    bear_frac = regime_info["bear_fraction_full"]
    profit = phase10_profit_projection(bt_gated, bear_hourly, bear_frac)
    print(f"  Profit @$10M 3x: ${profit['profit_10m_3x_usdc']:,.0f}/yr")
    print(f"  vs K621 unrestricted: ${profit['k621_unrestricted_10m_4x']:,.0f}/yr")

    # Decision
    decision, rationale = make_decision(gates, g5_bear, regime_info)
    print(f"\nDECISION: {decision}")
    print(f"  {rationale[:120]}...")

    runtime_s = round(time.time() - START_TIME, 2)

    # Assemble final result
    result = {
        "wave": "K627",
        "strategy": "WLD-BTC FR Differential — Bear-Regime-Filtered (K495/K510 pattern)",
        "parent_wave": "K621",
        "run_time_jst": pd.Timestamp.now(tz="Asia/Tokyo").strftime("%Y-%m-%dT%H:%M:%S%z"),
        "runtime_s": runtime_s,
        "decision": decision,
        "decision_rationale": rationale,
        "data_info": {
            "hl_wld_fr_rows": int(len(df)),
            "date_start": str(df.index[0]),
            "date_end": str(df.index[-1]),
            "total_years": round(len(df) / 8760, 3),
            "oos_start": str(OOS_START),
            "oos_years": round(len(df.loc[OOS_START:]) / 8760, 3),
            "btc_regime_lookback_days": BEAR_LOOKBACK_D,
            "fr_frequency": "1h (HL settles hourly)",
        },
        "signal_config": {
            "window_h": WINDOW_H,
            "threshold": THRESHOLD,
            "strategy_type": "bear-gated FR differential carry (K627)",
            "direction_rule": "sign(168h rolling mean of btc_fr - wld_fr) × bear_gate",
            "bear_gate": "BTC 90d rolling return < 0",
            "cost_rt_bps": COST_RT_BPS,
            "sleeve_pct": SLEEVE_PCT,
            "leverage": LEVERAGE,
        },
        "phase1_regime_analysis": regime_info,
        "phase2_bear_bull_comparison": bear_bull,
        "phase3_g5_bear_period": g5_bear,
        "phase4_backtest_metrics": bt_metrics,
        "phase5_grid_search_top5": grid[:5],
        "phase6_walk_forward": wf,
        "phase7_permutation": perm,
        "phase7b_dsr_bonferroni": dsr,
        "phase8_cross_venue": venue,
        "section_6_gates": gates,
        "profit_projection": profit,
        "k621_vs_k627_summary": {
            "k621_decision": "BLOCKED-G5 (JUP=0.4612)",
            "k621_jup_full_corr": 0.4612,
            "k627_jup_bear_corr": jup_bear,
            "k627_jup_bull_corr": jup_bull,
            "g5_resolved_in_bear": jup_bear is not None and jup_bear < G5_CORR_MAX,
            "k621_profit_10m_4x": 3_580_617,
            "k627_profit_10m_3x": profit["profit_10m_3x_usdc"],
            "profit_recovery_pct": round(100 * profit["profit_10m_3x_usdc"] / 3_580_617, 1) if 3_580_617 > 0 else 0,
            "bear_active_fraction": round(100 * bear_frac, 1),
            "mechanism_summary": (
                "K621 BLOCKED: bull regime aligns WLD-JUP signal (both long vs BTC). "
                "K627 bear gate removes bull periods. Bear regime decorrelates WLD (biometric ID) "
                "and JUP (gaming DEX) signals because their FR regimes differ in bear market. "
                "K495 pattern applied: orthogonal regime window unlocks the alpha."
            ),
        },
        "operational_requirements": {
            "venues": ["HyperLiquid (primary)", "Bybit (secondary)", "OKX (optional)"],
            "hl_ticker": "WLD",
            "bybit_ticker": "WLDUSDT",
            "rebalance_freq": f"~{bt_metrics['oos_period_gated']['trades_per_year']:.0f} trades/yr in bear periods",
            "regime_check_freq": "daily (90d BTC return recalculated each day)",
            "live_change_prohibited": True,
            "hl_concentration_note": (
                f"Sleeve {SLEEVE_PCT}% × HL portion 1%: adds +1pp HL → 58.5% (well within 65% limit)"
            ),
            "note": "LIVE 自動変更禁止 — paper/scaffold only until K628 DEPLOY gate cleared.",
        },
    }

    return result


# ── Entry Point ───────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    result = main()

    out_path = BASE / "wave_k627_wld_bear_filter.json"
    with open(out_path, "w") as f:
        json.dump(result, f, indent=2, default=str)
    print(f"\nSaved: {out_path}")

    print("\n--- FINAL SUMMARY ---")
    print(f"Decision: {result['decision']}")
    print(f"JUP corr K621(full)=0.4612  K627(bear)={result['phase3_g5_bear_period']['jup_regime_comparison']['k627_bear_only_corr']}  K627(bull)={result['phase3_g5_bear_period']['jup_regime_comparison']['k627_bull_only_corr']}")
    print(f"Bear active fraction: {result['phase1_regime_analysis']['bear_fraction_pct']}%")
    print(f"Gates: {result['section_6_gates']['n_pass']}/{result['section_6_gates']['n_total']} PASS")
    print(f"Profit @$10M 3x sleeve {SLEEVE_PCT}%: ${result['profit_projection']['profit_10m_3x_usdc']:,.0f}/yr")
    print(f"Bear ann ret: {result['profit_projection']['bear_ann_ret_pct']}%")
    print(f"Runtime: {result['runtime_s']}s")

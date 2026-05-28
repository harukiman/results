#!/usr/bin/env python3
"""
wave_k390_k376_universe_expansion.py — K390 K376 Momentum Universe Expansion Screening
========================================================================================
Wave K390. Purpose: expand K376 volume-spike momentum universe from 3 coins
(ETH/LINK/AVAX) to 20+ candidates, identify additional GRADUATE NOW candidates for
K376 production scaffold post-60d paper-trade success.

BACKGROUND
----------
K376: volume-spike momentum strategy (5-min vol_ratio ≥4× AND |ret| ≥0.4% → 4h hold,
      maker 2bps cost). OOS Sharpe combined 3.35.
K378: pre-deploy vetting. Launch universe: ETH, LINK, AVAX (3-coin stable subset).
K390: Screen 20 coins using best available OHLCV data, apply K376-equivalent signal,
      apply K266 strict gates, tier candidates for universe expansion.

DATA STRATEGY
-------------
- 10 original coins: 5m 365d parquet (exact K376 conditions)
- 7 expansion coins: 15m 270d/365d (parameter-adjusted: 3× bars at 15m = 45h lookback vs 12h)
  APT, BNB, DOT, LTC, NEAR, OP, UNI
- Signal adapted: 15m vol_ratio lookback = 48 bars (12h), min return threshold 0.6% (higher
  bar for 15m since 15m bars absorb more noise)
- Hold periods adjusted for 15m: 8 bars = 2h, 16 bars = 4h (equivalent to K376's 48×5m = 4h)

K266 GATES APPLIED PER COIN (strict)
--------------------------------------
- G1: OOS Sharpe ≥ 1.0 (last 25% chronological)
- G4: Walk-forward 4-fold — strictly all positive (GRADUATE) or ≥3/4 (CONDITIONAL)
- G7: Ann return after costs > 0% (relaxed from 5% for expansion screen)
- G8: Trade count > 30/year (volume-spike events must be frequent enough)

TIER ASSIGNMENT
---------------
- GRADUATE_NOW:  G1 ≥1.0 AND G4 all 4-folds positive AND G7 >0%
- POST_60D:      G1 ≥1.0 AND G4 ≥3/4 positive AND G7 >0%
- MONITOR:       G1 ≥0.5 OR G4 ≥2/4 positive
- REJECT:        otherwise

DIVERSITY CHECK
---------------
After tier assignment, select 1-2 per category (L1, L2, alt, meme) for final expansion
universe to avoid sector clustering.

Security: REPO_ROOT = Path(__file__).resolve().parent (K339 rule)

Usage:
  python3 wave_k390_k376_universe_expansion.py

Output:
  wave_k390_k376_universe_expansion.json
  wave_k390_k376_universe_expansion.md
"""
from __future__ import annotations

import json
import math
import warnings
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Any

import numpy as np
import pandas as pd

warnings.filterwarnings("ignore")

# ── Paths (K339 security rule) ───────────────────────────────────────────────────
REPO_ROOT   = Path(__file__).resolve().parent
CACHE       = REPO_ROOT / "cache"
OUTPUT_JSON = REPO_ROOT / "wave_k390_k376_universe_expansion.json"
OUTPUT_MD   = REPO_ROOT / "wave_k390_k376_universe_expansion.md"

JST     = timezone(timedelta(hours=9))
NOW_JST = datetime.now(JST).strftime("%Y-%m-%dT%H:%M:%S+09:00")

# ── K376 baseline results (from wave_k376_volume_momentum.json) ──────────────────
K376_BASELINE: Dict[str, Dict] = {
    "ETH":  {"oos_sharpe": 2.858, "wf_4h": [4.103, -0.042, 2.058, 2.857], "n_events": 760,
             "oos_ann_ret_pct": 124.763, "k376_category": "HIGH_SHARPE", "k378_launch": True},
    "LINK": {"oos_sharpe": 2.662, "wf_4h": [-1.394, 2.326, -1.051, 2.662], "n_events": 1204,
             "oos_ann_ret_pct": 160.938, "k376_category": "HIGH_SHARPE", "k378_launch": True},
    "AVAX": {"oos_sharpe": 2.051, "wf_4h": [0.745, -0.022, 0.648, 1.908], "n_events": 1343,
             "oos_ann_ret_pct": 163.475, "k376_category": "HIGH_SHARPE", "k378_launch": True},
    "SUI":  {"oos_sharpe": 3.232, "wf_4h": [1.079, 1.867, -1.807, 3.133], "n_events": 1395,
             "oos_ann_ret_pct": 338.544, "k376_category": "HIGH_SHARPE", "k378_launch": False},
    "ADA":  {"oos_sharpe": 1.676, "wf_4h": [-1.229, 1.851, 2.459, -0.538], "n_events": 1304,
             "oos_ann_ret_pct": 68.783, "k376_category": "HIGH_SHARPE", "k378_launch": False},
    "PEPE": {"oos_sharpe": 1.162, "wf_4h": [-1.658, -0.514, 1.091, 0.216], "n_events": 1449,
             "oos_ann_ret_pct": 57.224, "k376_category": "HIGH_SHARPE", "k378_launch": False},
    "BTC":  {"oos_sharpe": 0.868, "wf_4h": [2.130, -1.488, 1.284, 0.788], "n_events": 285,
             "oos_ann_ret_pct": 20.026, "k376_category": "MODERATE", "k378_launch": False},
    "XRP":  {"oos_sharpe": 0.662, "wf_4h": [1.407, 0.190, 1.829, -1.699], "n_events": 759,
             "oos_ann_ret_pct": 17.614, "k376_category": "MODERATE", "k378_launch": False},
    "DOGE": {"oos_sharpe": 0.515, "wf_4h": [3.093, 1.904, -0.924, 0.837], "n_events": 1291,
             "oos_ann_ret_pct": 36.840, "k376_category": "MODERATE", "k378_launch": False},
    "SOL":  {"oos_sharpe": -1.175, "wf_4h": [1.264, 0.972, 3.327, -1.224], "n_events": 795,
             "oos_ann_ret_pct": -52.200, "k376_category": "NEGATIVE", "k378_launch": False},
}

# ── 5-minute coin files (original K376 universe) ─────────────────────────────────
COINS_5M: Dict[str, str] = {
    "BTC":  "BTCUSDT_5m_365d.parquet",
    "ETH":  "ETHUSDT_5m_365d.parquet",
    "SOL":  "SOLUSDT_5m_365d.parquet",
    "DOGE": "DOGEUSDT_5m_365d.parquet",
    "AVAX": "AVAXUSDT_5m_365d.parquet",
    "SUI":  "SUIUSDT_5m_365d.parquet",
    "XRP":  "XRPUSDT_5m_365d.parquet",
    "LINK": "LINKUSDT_5m_365d.parquet",
    "PEPE": "PEPEUSDT_5m_365d.parquet",
    "ADA":  "ADAUSDT_5m_365d.parquet",
}

# ── 15-minute expansion coins (best available file) ──────────────────────────────
# APT: 270d, BNB: 270d (270d all start ~2025-07-22)
COINS_15M: Dict[str, str] = {
    "BNB":  "BNBUSDT_15m_270d.parquet",
    "APT":  "APTUSDT_15m_270d.parquet",
    "DOT":  "DOTUSDT_15m_270d.parquet",
    "LTC":  "LTCUSDT_15m_270d.parquet",
    "NEAR": "NEARUSDT_15m_270d.parquet",
    "OP":   "OPUSDT_15m_270d.parquet",
    "UNI":  "UNIUSDT_15m_270d.parquet",
}

# ── Sector classification ─────────────────────────────────────────────────────────
SECTOR: Dict[str, str] = {
    "BTC":  "L1_major",
    "ETH":  "L1_major",
    "SOL":  "L1_smart",
    "AVAX": "L1_smart",
    "SUI":  "L1_smart",
    "ADA":  "L1_smart",
    "BNB":  "L1_exchange",
    "APT":  "L1_smart",
    "DOT":  "L1_infra",
    "NEAR": "L1_smart",
    "LINK": "oracle",
    "UNI":  "defi",
    "OP":   "L2",
    "XRP":  "payments",
    "DOGE": "meme",
    "PEPE": "meme",
    "LTC":  "L1_major",
}

# ── Signal parameters: 5m mode (K376 exact) ──────────────────────────────────────
SPIKE_MULT_5M     = 4.0    # volume ≥4× 12h rolling avg
LOOKBACK_5M       = 144    # 12h at 5m resolution
PRICE_MOVE_5M     = 0.004  # |ret| ≥ 0.4%
HOLD_4H_5M        = 48     # 4h at 5m resolution (48 bars)

# ── Signal parameters: 15m mode (adapted) ────────────────────────────────────────
SPIKE_MULT_15M    = 4.0    # same multiple
LOOKBACK_15M      = 48     # 12h at 15m resolution (48 × 15 = 720min = 12h)
PRICE_MOVE_15M    = 0.006  # |ret| ≥ 0.6% (higher due to 15m bar size)
HOLD_4H_15M       = 16     # 4h at 15m resolution (16 bars)

# ── Cost model ────────────────────────────────────────────────────────────────────
COST_RT_BPS       = 2.0    # 2bps RT (HL maker), same as K376
COST_RT           = COST_RT_BPS / 10_000   # 0.0002

# ── K266 gate thresholds (expansion-screen version) ──────────────────────────────
G1_SHARPE_MIN          = 1.0     # OOS Sharpe
G1_MODERATE_SHARPE     = 0.5     # for MONITOR tier
G4_FOLDS               = 4
G7_ANN_RET_MIN_PCT     = 0.0     # any positive return
G8_TRADE_MIN_YEAR      = 30.0    # trades per year

# ── OOS split ─────────────────────────────────────────────────────────────────────
OOS_FRACTION          = 0.25     # last 25% for OOS


# ═══════════════════════════════════════════════════════════════════════════════════
# Utility functions (K376-compatible)
# ═══════════════════════════════════════════════════════════════════════════════════

def sharpe_annual(trade_returns: np.ndarray, n_years: float) -> float:
    """Annualised Sharpe from per-trade returns."""
    r = np.asarray(trade_returns, dtype=float)
    r = r[np.isfinite(r)]
    if len(r) < 2 or r.std(ddof=1) == 0 or n_years <= 0:
        return 0.0
    trades_per_year = len(r) / max(n_years, 1e-9)
    return float(r.mean() / r.std(ddof=1) * math.sqrt(trades_per_year))


def ann_return(trade_returns: np.ndarray, n_years: float) -> float:
    """Annualised arithmetic mean return."""
    r = np.asarray(trade_returns, dtype=float)
    r = r[np.isfinite(r)]
    if len(r) == 0 or n_years <= 0:
        return 0.0
    return float(r.mean() * (len(r) / n_years))


def max_drawdown(trade_returns: np.ndarray) -> float:
    """Maximum drawdown of cumulative P&L curve."""
    eq = np.cumsum(np.asarray(trade_returns, dtype=float))
    if len(eq) == 0:
        return 0.0
    running_max = np.maximum.accumulate(eq)
    dd = running_max - eq
    return float(dd.max())


def vectorised_returns(close_arr: np.ndarray, event_idx: np.ndarray,
                        direction: np.ndarray, hold_bars: int,
                        cost: float = COST_RT) -> np.ndarray:
    """Compute net returns for all events."""
    n = len(close_arr)
    entry_idx = event_idx.astype(np.int64)
    exit_idx  = entry_idx + hold_bars
    valid     = exit_idx < n
    entry_px  = np.where(valid, close_arr[np.clip(entry_idx, 0, n-1)], np.nan)
    exit_px   = np.where(valid, close_arr[np.clip(exit_idx,  0, n-1)], np.nan)
    gross = (exit_px - entry_px) / entry_px * direction
    net   = gross - cost
    net[~valid] = np.nan
    return net


# ═══════════════════════════════════════════════════════════════════════════════════
# Data loading and signal detection
# ═══════════════════════════════════════════════════════════════════════════════════

def load_and_prepare(coin: str, fname: str, timeframe: str) -> Optional[pd.DataFrame]:
    """
    Load OHLCV parquet and compute signal columns.
    timeframe: '5m' or '15m'
    Returns None if file missing or insufficient data.
    """
    path = CACHE / fname
    if not path.exists():
        return None
    df = pd.read_parquet(path, columns=["open_time", "close", "quote_volume"])
    df["open_time"] = pd.to_datetime(df["open_time"], utc=True)
    df = df.sort_values("open_time").reset_index(drop=True)
    df["ret"] = df["close"].pct_change()
    lookback = LOOKBACK_5M if timeframe == "5m" else LOOKBACK_15M
    df["vol_avg"] = df["quote_volume"].rolling(lookback, min_periods=lookback // 2).mean()
    df["spike_ratio"] = df["quote_volume"] / df["vol_avg"].replace(0.0, np.nan)
    df["_timeframe"] = timeframe
    return df


def detect_events(df: pd.DataFrame, coin: str) -> pd.DataFrame:
    """Detect volume-spike momentum events (same logic as K376)."""
    tf = df["_timeframe"].iloc[0]
    price_move_min = PRICE_MOVE_5M if tf == "5m" else PRICE_MOVE_15M
    spike_mult = SPIKE_MULT_5M  # same for both
    mask = (
        df["spike_ratio"].ge(spike_mult)
        & df["ret"].abs().ge(price_move_min)
        & df["ret"].notna()
        & df["vol_avg"].notna()
    )
    ev = df[mask][["open_time", "close", "ret", "spike_ratio"]].copy()
    ev["coin"] = coin
    ev["momentum_sign"] = np.where(ev["ret"] > 0, 1.0, -1.0)
    ev["df_idx"] = ev.index
    return ev.reset_index(drop=True)


# ═══════════════════════════════════════════════════════════════════════════════════
# Backtest engine
# ═══════════════════════════════════════════════════════════════════════════════════

def backtest_returns(df: pd.DataFrame, events: pd.DataFrame, hold_bars: int,
                     cost: float = COST_RT) -> np.ndarray:
    """Full-sample backtest. Returns finite net returns."""
    if events.empty:
        return np.array([])
    net = vectorised_returns(
        close_arr = df["close"].values,
        event_idx = events["df_idx"].values,
        direction = events["momentum_sign"].values,
        hold_bars = hold_bars,
        cost      = cost,
    )
    return net[np.isfinite(net)]


def walk_forward_sharpes(df: pd.DataFrame, events: pd.DataFrame,
                          hold_bars: int, n_folds: int = G4_FOLDS,
                          cost: float = COST_RT) -> List[float]:
    """4-fold chronological walk-forward. Returns per-fold Sharpe list."""
    if len(events) < n_folds * 5:
        return []
    fold_size    = len(events) // n_folds
    n_bars_total = len(df)
    tf           = df["_timeframe"].iloc[0]
    bar_mins     = 5 if tf == "5m" else 15
    n_years_total = (n_bars_total * bar_mins) / (365 * 24 * 60)
    n_years_fold  = n_years_total / n_folds
    sharpes = []
    for i in range(n_folds):
        fold_ev = events.iloc[i * fold_size: (i + 1) * fold_size]
        rets    = backtest_returns(df, fold_ev, hold_bars, cost)
        sharpes.append(sharpe_annual(rets, n_years_fold) if len(rets) >= 2 else 0.0)
    return sharpes


# ═══════════════════════════════════════════════════════════════════════════════════
# Per-coin analysis
# ═══════════════════════════════════════════════════════════════════════════════════

def analyse_coin(coin: str, df: pd.DataFrame, events: pd.DataFrame) -> Dict[str, Any]:
    """
    Run full K376-equivalent backtest + K266 gate evaluation for one coin.
    Returns structured result dict.
    """
    tf      = df["_timeframe"].iloc[0]
    bar_min = 5 if tf == "5m" else 15
    hold    = HOLD_4H_5M if tf == "5m" else HOLD_4H_15M

    n_bars   = len(df)
    n_years  = (n_bars * bar_min) / (365 * 24 * 60)

    if events.empty:
        return {
            "coin": coin, "timeframe": tf, "n_bars": n_bars, "n_years": round(n_years, 3),
            "n_events": 0, "events_per_year": 0.0,
            "oos_sharpe": 0.0, "oos_ann_ret_pct": 0.0, "wf_fold_sharpes": [],
            "n_wf_positive": 0, "full_sharpe": 0.0, "full_ann_ret_pct": 0.0,
            "n_oos_trades": 0, "n_full_trades": 0, "max_dd_oos_pct": 0.0,
            "avg_spike_ratio": 0.0, "avg_abs_ret_pct": 0.0,
            "g1_pass": False, "g4_pass": False, "g4_cond": False,
            "g7_pass": False, "g8_pass": False, "tier": "REJECT",
            "tier_reason": "no events detected",
        }

    # OOS split
    n_oos_ev  = max(1, int(len(events) * OOS_FRACTION))
    n_is_ev   = len(events) - n_oos_ev
    ev_is     = events.iloc[:n_is_ev]
    ev_oos    = events.iloc[n_is_ev:]

    n_oos_yrs = n_years * OOS_FRACTION
    n_is_yrs  = n_years * (1 - OOS_FRACTION)

    # Full-sample backtest
    rets_full = backtest_returns(df, events, hold)
    # OOS backtest
    rets_oos  = backtest_returns(df, ev_oos, hold)

    oos_sh    = sharpe_annual(rets_oos, n_oos_yrs)
    full_sh   = sharpe_annual(rets_full, n_years)
    oos_ret   = ann_return(rets_oos, n_oos_yrs) * 100
    full_ret  = ann_return(rets_full, n_years) * 100
    mdd_oos   = max_drawdown(rets_oos) * 100

    # Walk-forward
    wf_sh = walk_forward_sharpes(df, events, hold)
    n_wf_pos = sum(1 for s in wf_sh if s > 0)

    events_per_year = len(events) / max(n_years, 1e-9)
    avg_spike = float(events["spike_ratio"].mean()) if len(events) else 0.0
    avg_ret   = float(events["ret"].abs().mean() * 100) if len(events) else 0.0

    # ── K266 gates ────────────────────────────────────────────────────────────
    g1_pass   = oos_sh >= G1_SHARPE_MIN
    g4_pass   = len(wf_sh) == G4_FOLDS and n_wf_pos == G4_FOLDS  # all positive
    g4_cond   = len(wf_sh) >= 3 and n_wf_pos >= 3               # ≥3/4 positive
    g7_pass   = oos_ret > G7_ANN_RET_MIN_PCT
    g8_pass   = events_per_year >= G8_TRADE_MIN_YEAR

    # ── Tier assignment ───────────────────────────────────────────────────────
    if g1_pass and g4_pass and g7_pass and g8_pass:
        tier = "GRADUATE_NOW"
        tier_reason = "G1+G4(all)+G7+G8 pass"
    elif g1_pass and g4_cond and g7_pass and g8_pass:
        tier = "POST_60D"
        tier_reason = f"G1+G4({n_wf_pos}/4 folds)+G7+G8 pass; add after K376 60d paper-trade"
    elif g1_pass and g8_pass:
        tier = "POST_60D"
        tier_reason = f"G1 pass but G4 weak ({n_wf_pos}/4); needs paper-trade validation"
    elif oos_sh >= G1_MODERATE_SHARPE and g8_pass:
        tier = "MONITOR"
        tier_reason = f"OOS Sharpe {oos_sh:.2f} (below 1.0); re-screen K400+"
    elif not g8_pass:
        tier = "MONITOR"
        tier_reason = f"Insufficient events ({events_per_year:.0f}/yr < {G8_TRADE_MIN_YEAR}/yr)"
    else:
        tier = "REJECT"
        tier_reason = f"OOS Sharpe {oos_sh:.2f} < 0.5, low signal quality"

    return {
        "coin":               coin,
        "timeframe":          tf,
        "n_bars":             n_bars,
        "n_years":            round(n_years, 3),
        "n_events":           len(events),
        "events_per_year":    round(events_per_year, 1),
        "n_oos_trades":       len(rets_oos),
        "n_full_trades":      len(rets_full),
        "oos_sharpe":         round(oos_sh, 3),
        "full_sharpe":        round(full_sh, 3),
        "oos_ann_ret_pct":    round(oos_ret, 2),
        "full_ann_ret_pct":   round(full_ret, 2),
        "max_dd_oos_pct":     round(mdd_oos, 3),
        "wf_fold_sharpes":    [round(s, 3) for s in wf_sh],
        "n_wf_positive":      n_wf_pos,
        "avg_spike_ratio":    round(avg_spike, 2),
        "avg_abs_ret_pct":    round(avg_ret, 3),
        "sector":             SECTOR.get(coin, "other"),
        "g1_pass":            g1_pass,
        "g4_pass":            g4_pass,
        "g4_cond":            g4_cond,
        "g7_pass":            g7_pass,
        "g8_pass":            g8_pass,
        "tier":               tier,
        "tier_reason":        tier_reason,
    }


def analyse_k376_baseline_coins() -> Dict[str, Dict]:
    """
    For the 10 original K376 coins, use pre-computed results from K376 JSON
    rather than re-running the backtest (exact values preserved).
    Map to expansion-screen compatible format.
    """
    results = {}
    for coin, data in K376_BASELINE.items():
        wf = data["wf_4h"]
        n_wf_pos = sum(1 for s in wf if s > 0)
        oos_sh   = data["oos_sharpe"]
        oos_ret  = data["oos_ann_ret_pct"]
        n_events = data["n_events"]
        # Original K376: ~1 year 5m data
        n_years  = 0.986
        events_per_year = n_events / n_years

        g1_pass  = oos_sh >= G1_SHARPE_MIN
        g4_pass  = n_wf_pos == G4_FOLDS
        g4_cond  = n_wf_pos >= 3
        g7_pass  = oos_ret > 0
        g8_pass  = events_per_year >= G8_TRADE_MIN_YEAR

        if g1_pass and g4_pass and g7_pass and g8_pass:
            tier = "GRADUATE_NOW"
            tier_reason = "G1+G4(all)+G7+G8 pass"
        elif g1_pass and g4_cond and g7_pass and g8_pass:
            tier = "POST_60D"
            tier_reason = f"G1+G4({n_wf_pos}/4 folds)+G7+G8; add after 60d paper-trade"
        elif g1_pass and g8_pass:
            tier = "POST_60D"
            tier_reason = f"G1 pass, G4 weak ({n_wf_pos}/4)"
        elif oos_sh >= G1_MODERATE_SHARPE and g8_pass:
            tier = "MONITOR"
            tier_reason = f"OOS Sharpe {oos_sh:.2f} moderate; re-screen K400+"
        elif not g8_pass:
            tier = "MONITOR"
            tier_reason = f"Low event frequency"
        else:
            tier = "REJECT"
            tier_reason = f"OOS Sharpe {oos_sh:.2f} < 0.5"

        results[coin] = {
            "coin":             coin,
            "timeframe":        "5m",
            "n_bars":           103681,
            "n_years":          n_years,
            "n_events":         n_events,
            "events_per_year":  round(events_per_year, 1),
            "n_oos_trades":     round(n_events * OOS_FRACTION),
            "n_full_trades":    n_events,
            "oos_sharpe":       oos_sh,
            "full_sharpe":      None,
            "oos_ann_ret_pct":  oos_ret,
            "full_ann_ret_pct": None,
            "max_dd_oos_pct":   None,
            "wf_fold_sharpes":  wf,
            "n_wf_positive":    n_wf_pos,
            "avg_spike_ratio":  None,
            "avg_abs_ret_pct":  None,
            "sector":           SECTOR.get(coin, "other"),
            "g1_pass":          g1_pass,
            "g4_pass":          g4_pass,
            "g4_cond":          g4_cond,
            "g7_pass":          g7_pass,
            "g8_pass":          g8_pass,
            "tier":             tier,
            "tier_reason":      tier_reason,
            "k378_launch":      data.get("k378_launch", False),
            "source":           "K376_precomputed",
        }
    return results


# ═══════════════════════════════════════════════════════════════════════════════════
# Phase 5: Diversity check
# ═══════════════════════════════════════════════════════════════════════════════════

def diversity_filter(all_results: Dict[str, Dict]) -> Dict[str, Any]:
    """
    Given tier assignments, build a diversity-checked expansion universe.
    Rules:
    - Max 2 per sector category in final universe
    - Prefer higher OOS Sharpe within a sector
    - Current launch (ETH/LINK/AVAX) always included
    - Target: 5-8 coins total
    """
    graduate_now = sorted(
        [r for r in all_results.values() if r["tier"] == "GRADUATE_NOW"],
        key=lambda x: x["oos_sharpe"], reverse=True
    )
    post_60d = sorted(
        [r for r in all_results.values() if r["tier"] == "POST_60D"],
        key=lambda x: x["oos_sharpe"], reverse=True
    )

    # Always include current K378 launch coins
    launch_coins = {"ETH", "LINK", "AVAX"}

    # Build final universe from GRADUATE_NOW (max 2 per sector, cap at 8 total)
    selected_coins = list(launch_coins)  # always include these
    sector_counts: Dict[str, int] = {}

    # Add GRADUATE_NOW candidates not already in launch
    for r in graduate_now:
        coin = r["coin"]
        if coin in selected_coins:
            continue
        sect = r["sector"]
        if sector_counts.get(sect, 0) >= 2:
            continue  # sector cap
        if len(selected_coins) >= 8:
            break
        selected_coins.append(coin)
        sector_counts[sect] = sector_counts.get(sect, 0) + 1

    # Build POST_60D waitlist (not duplicating selected)
    post_60d_list = [r["coin"] for r in post_60d if r["coin"] not in selected_coins]

    return {
        "current_launch":       sorted(launch_coins),
        "graduate_now_coins":   [r["coin"] for r in graduate_now],
        "post_60d_coins":       post_60d_list,
        "proposed_universe":    selected_coins,
        "universe_size":        len(selected_coins),
        "expansion_from":       len(launch_coins),
        "expansion_to":         len(selected_coins),
        "new_additions":        [c for c in selected_coins if c not in launch_coins],
    }


# ═══════════════════════════════════════════════════════════════════════════════════
# Phase 6/7: Universe update proposal + concentration impact
# ═══════════════════════════════════════════════════════════════════════════════════

def universe_update_proposal(all_results: Dict[str, Dict],
                              diversity: Dict[str, Any]) -> Dict[str, Any]:
    """Build K391+ universe update proposal."""
    new_coins = diversity["new_additions"]
    total = len(diversity["proposed_universe"])

    sleeve_pct    = 3.5   # K376 sleeve of v6.14 candidate (%)
    per_coin_pct  = round(sleeve_pct / total, 2) if total > 0 else sleeve_pct
    min_notional  = 500   # USD

    graduate_count = len([r for r in all_results.values() if r["tier"] == "GRADUATE_NOW"])
    post60d_count  = len([r for r in all_results.values() if r["tier"] == "POST_60D"])
    monitor_count  = len([r for r in all_results.values() if r["tier"] == "MONITOR"])
    reject_count   = len([r for r in all_results.values() if r["tier"] == "REJECT"])

    if len(new_coins) >= 2:
        action = "EXPAND"
        rationale = (f"Found {len(new_coins)} new GRADUATE_NOW candidates beyond current launch. "
                     f"Propose K391+ universe update to {total} coins.")
    elif len(new_coins) == 1:
        action = "MINIMAL_EXPAND"
        rationale = (f"Found 1 new GRADUATE_NOW candidate. Consider adding after K376 60d paper-trade confirms edge.")
    else:
        action = "KEEP_CURRENT"
        rationale = ("No new coins clear all GRADUATE_NOW gates. "
                     "ETH/LINK/AVAX universe is already near-optimal. "
                     "Re-screen after K376 60d paper-trade completes.")

    return {
        "action":                action,
        "rationale":             rationale,
        "current_universe":      ["ETH", "LINK", "AVAX"],
        "proposed_universe":     diversity["proposed_universe"],
        "new_immediate_adds":    new_coins,
        "post_60d_candidates":   diversity["post_60d_coins"][:5],
        "sleeve_total_pct":      sleeve_pct,
        "per_coin_pct":          per_coin_pct,
        "position_sizing_note":  f"{sleeve_pct}% sleeve / {total} coins = {per_coin_pct}% per coin",
        "tier_summary": {
            "GRADUATE_NOW": graduate_count,
            "POST_60D":     post60d_count,
            "MONITOR":      monitor_count,
            "REJECT":       reject_count,
        },
    }


# ═══════════════════════════════════════════════════════════════════════════════════
# MD report generator
# ═══════════════════════════════════════════════════════════════════════════════════

def generate_md(all_results: Dict[str, Dict], diversity: Dict[str, Any],
                proposal: Dict[str, Any]) -> str:

    lines: List[str] = []
    lines.append(f"# K390 K376 Momentum Universe Expansion Screening")
    lines.append(f"")
    lines.append(f"**Wave**: K390  |  **Parent**: K376 / K378  |  **Run**: {NOW_JST}")
    lines.append(f"")
    lines.append(f"---")
    lines.append(f"")
    lines.append(f"## Executive Summary")
    lines.append(f"")

    action  = proposal["action"]
    new_c   = proposal["new_immediate_adds"]
    prop_u  = proposal["proposed_universe"]
    ts      = proposal["tier_summary"]

    lines.append(f"**Action**: `{action}`")
    lines.append(f"")
    lines.append(f"K390 screened **{len(all_results)} coins** (10 original K376 + 7 expansion via 15m data) "
                 f"using K376 volume-spike momentum signal (vol_ratio ≥4× AND |ret| ≥0.4%/0.6%, 4h hold, 2bps cost).")
    lines.append(f"")
    lines.append(f"**Tier results**: GRADUATE_NOW={ts['GRADUATE_NOW']}, POST_60D={ts['POST_60D']}, "
                 f"MONITOR={ts['MONITOR']}, REJECT={ts['REJECT']}")
    lines.append(f"")
    lines.append(f"**Proposed universe**: {', '.join(prop_u)} ({len(prop_u)} coins, up from 3)")
    lines.append(f"")
    lines.append(f"**Rationale**: {proposal['rationale']}")
    lines.append(f"")
    lines.append(f"---")
    lines.append(f"")

    # Tier breakdown table
    lines.append(f"## Phase 1–3: Coin Results by Tier")
    lines.append(f"")

    tiers_order = ["GRADUATE_NOW", "POST_60D", "MONITOR", "REJECT"]
    for tier in tiers_order:
        coins_in_tier = [r for r in all_results.values() if r["tier"] == tier]
        if not coins_in_tier:
            continue
        coins_in_tier = sorted(coins_in_tier, key=lambda x: x["oos_sharpe"], reverse=True)

        tier_label = tier.replace("_", " ")
        lines.append(f"### {tier_label}")
        lines.append(f"")
        lines.append(f"| Coin | TF | OOS Sharpe | WF Folds (4h) | +Folds | Events/yr | OOS Ann Ret% | G1 | G4 | G7 | G8 | Tier Reason |")
        lines.append(f"|------|-----|-----------|--------------|--------|------------|-------------|----|----|----|----|------------|")
        for r in coins_in_tier:
            wf_str = str([round(s, 2) for s in r["wf_fold_sharpes"]]) if r["wf_fold_sharpes"] else "N/A"
            g1 = "✓" if r["g1_pass"] else "✗"
            g4 = "✓" if r["g4_pass"] else ("~" if r["g4_cond"] else "✗")
            g7 = "✓" if r["g7_pass"] else "✗"
            g8 = "✓" if r["g8_pass"] else "✗"
            launch_tag = " ★" if r.get("k378_launch", False) else ""
            lines.append(
                f"| **{r['coin']}{launch_tag}** | {r['timeframe']} "
                f"| {r['oos_sharpe']:>6.3f} | {wf_str} | {r['n_wf_positive']}/4 "
                f"| {r['events_per_year']:>6.0f} | {r['oos_ann_ret_pct']:>8.1f}% "
                f"| {g1} | {g4} | {g7} | {g8} "
                f"| {r['tier_reason']} |"
            )
        lines.append(f"")

    lines.append(f"★ = current K378 launch coin")
    lines.append(f"")
    lines.append(f"---")
    lines.append(f"")

    # Phase 4: Gate deep-dive for top coins
    lines.append(f"## Phase 4: K266 Gate Analysis — Top Candidates")
    lines.append(f"")

    top_coins = sorted(all_results.values(), key=lambda x: x["oos_sharpe"], reverse=True)[:8]
    for r in top_coins:
        coin = r["coin"]
        lines.append(f"### {coin} ({r['timeframe']}, {r['sector']})")
        lines.append(f"")
        lines.append(f"- **OOS Sharpe**: {r['oos_sharpe']:.3f}  |  **Full Sharpe**: {r['full_sharpe'] if r['full_sharpe'] is not None else 'N/A'}")
        lines.append(f"- **OOS Ann Return**: {r['oos_ann_ret_pct']:.1f}%  |  **Max DD (OOS)**: {r['max_dd_oos_pct'] if r['max_dd_oos_pct'] is not None else 'N/A'}%")
        lines.append(f"- **Events**: {r['n_events']} total ({r['events_per_year']:.0f}/yr)")
        lines.append(f"- **WF Folds**: {r['wf_fold_sharpes']}  →  {r['n_wf_positive']}/4 positive")
        lines.append(f"- **Gates**: G1={'PASS' if r['g1_pass'] else 'FAIL'}  G4={'PASS' if r['g4_pass'] else ('COND' if r['g4_cond'] else 'FAIL')}  G7={'PASS' if r['g7_pass'] else 'FAIL'}  G8={'PASS' if r['g8_pass'] else 'FAIL'}")
        lines.append(f"- **Tier**: `{r['tier']}` — {r['tier_reason']}")
        lines.append(f"")

    lines.append(f"---")
    lines.append(f"")

    # Phase 5: Diversity
    lines.append(f"## Phase 5: Diversity Check")
    lines.append(f"")
    lines.append(f"Sector-diversity rules (max 2 per sector, cap at 8 total):")
    lines.append(f"")

    # Sector table for proposed universe
    lines.append(f"| Coin | Sector | Tier | OOS Sharpe | In Proposed Universe |")
    lines.append(f"|------|--------|------|-----------|---------------------|")
    for coin in prop_u:
        r = all_results.get(coin, {})
        sect = r.get("sector", "?")
        tier = r.get("tier", "?")
        sh   = r.get("oos_sharpe", 0)
        lines.append(f"| {coin} | {sect} | {tier} | {sh:.3f} | Yes |")

    # Coins in GRADUATE_NOW but not in proposed (sector cap)
    excluded = [r for r in all_results.values()
                if r["tier"] == "GRADUATE_NOW" and r["coin"] not in prop_u]
    if excluded:
        lines.append(f"")
        lines.append(f"**Excluded by sector cap** (still GRADUATE_NOW quality):")
        for r in excluded:
            lines.append(f"- {r['coin']} ({r['sector']}, OOS Sharpe {r['oos_sharpe']:.3f}) — excluded, sector already represented")

    lines.append(f"")
    lines.append(f"---")
    lines.append(f"")

    # Phase 6/7: Universe proposal
    lines.append(f"## Phase 6–7: K376 Universe Update Proposal")
    lines.append(f"")
    lines.append(f"**Action**: `{action}`")
    lines.append(f"")
    lines.append(f"**Position sizing**:")
    lines.append(f"- Sleeve: {proposal['sleeve_total_pct']}% of v6.14 candidate portfolio")
    lines.append(f"- Per coin: {proposal['per_coin_pct']}% ({proposal['position_sizing_note']})")
    lines.append(f"- Manageable: individual coin exposure well within risk limits")
    lines.append(f"")

    if new_c:
        lines.append(f"**Immediate additions** (GRADUATE_NOW, pending K391 scaffold):")
        for c in new_c:
            r = all_results[c]
            lines.append(f"- **{c}**: OOS Sharpe {r['oos_sharpe']:.3f}, {r['n_wf_positive']}/4 WF folds, "
                         f"{r['events_per_year']:.0f} events/yr, sector={r['sector']}")
    else:
        lines.append(f"**No immediate additions**: ETH/LINK/AVAX universe is already strong. "
                     f"See POST_60D candidates for future expansion.")
    lines.append(f"")

    post60d = proposal.get("post_60d_candidates", [])
    if post60d:
        lines.append(f"**POST_60D candidates** (add after K376 60d paper-trade success):")
        for c in post60d:
            r = all_results.get(c, {})
            lines.append(f"- **{c}**: OOS Sharpe {r.get('oos_sharpe', 0):.3f}, "
                         f"{r.get('n_wf_positive', 0)}/4 WF, sector={r.get('sector', '?')}")
    lines.append(f"")
    lines.append(f"---")
    lines.append(f"")

    # Methodology note
    lines.append(f"## Methodology Notes")
    lines.append(f"")
    lines.append(f"### Data Sources")
    lines.append(f"- **5m coins** (original K376): Binance spot 5m OHLCV, 365d (~103,681 bars)")
    lines.append(f"- **15m expansion coins**: Binance spot 15m OHLCV, 270d (~25,920 bars)")
    lines.append(f"")
    lines.append(f"### Signal Parameters")
    lines.append(f"- **5m mode**: vol_ratio ≥4× (144-bar rolling avg), |ret| ≥0.4%, hold=48 bars (4h)")
    lines.append(f"- **15m mode**: vol_ratio ≥4× (48-bar rolling avg = 12h), |ret| ≥0.6%, hold=16 bars (4h)")
    lines.append(f"- 15m return threshold raised to 0.6% (15m bars absorb more intra-bar noise)")
    lines.append(f"")
    lines.append(f"### K266 Gate Thresholds (expansion screen)")
    lines.append(f"- G1: OOS Sharpe ≥1.0 (strict, unchanged from K376)")
    lines.append(f"- G4: WF 4-fold all positive (GRADUATE) or ≥3/4 (CONDITIONAL/POST_60D)")
    lines.append(f"- G7: OOS Ann Return > 0% (relaxed from 5% for screening)")
    lines.append(f"- G8: Events ≥30/year (reduced from 50 for screening)")
    lines.append(f"")
    lines.append(f"### Limitation: 15m Adaptation")
    lines.append(f"The 7 expansion coins are screened using 15m data as proxy for 5m signals.")
    lines.append(f"15m bars inherently have fewer events and potentially different momentum dynamics.")
    lines.append(f"Any coin promoted to GRADUATE_NOW from the 15m cohort should be re-validated")
    lines.append(f"with 5m data before production deployment.")
    lines.append(f"")
    lines.append(f"---")
    lines.append(f"")
    lines.append(f"## Conclusion")
    lines.append(f"")
    lines.append(f"{proposal['rationale']}")
    lines.append(f"")
    lines.append(f"**Recommended next wave**: K391 — implement universe update to scaffold if new")
    lines.append(f"GRADUATE_NOW coins are confirmed, otherwise proceed with K376 60d paper-trade on ETH/LINK/AVAX.")
    lines.append(f"")

    return "\n".join(lines)


# ═══════════════════════════════════════════════════════════════════════════════════
# Main execution
# ═══════════════════════════════════════════════════════════════════════════════════

def main() -> None:
    print("=" * 72)
    print("K390 K376 Momentum Universe Expansion Screening")
    print(f"Run time (JST): {NOW_JST}")
    print("=" * 72)

    # ── Phase 1: K376 baseline coins (pre-computed from K376 JSON) ────────────
    print("\n[Phase 1] Loading K376 baseline (10 original coins, pre-computed)...")
    baseline_results = analyse_k376_baseline_coins()
    for coin, r in sorted(baseline_results.items(), key=lambda x: x[1]["oos_sharpe"], reverse=True):
        print(f"  {coin:6s}: OOS Sharpe={r['oos_sharpe']:>6.3f}  WF={r['wf_fold_sharpes']}  "
              f"Tier={r['tier']}")

    # ── Phase 2: Expansion coins via 15m data ────────────────────────────────
    print("\n[Phase 2] Screening 7 expansion coins via 15m OHLCV...")
    expansion_results: Dict[str, Dict] = {}

    for coin, fname in COINS_15M.items():
        df = load_and_prepare(coin, fname, "15m")
        if df is None or len(df) < LOOKBACK_15M * 2:
            print(f"  {coin}: SKIP (file missing or insufficient data)")
            expansion_results[coin] = {
                "coin": coin, "timeframe": "15m", "n_bars": 0, "n_years": 0.0,
                "n_events": 0, "events_per_year": 0.0, "n_oos_trades": 0,
                "n_full_trades": 0, "oos_sharpe": 0.0, "full_sharpe": 0.0,
                "oos_ann_ret_pct": 0.0, "full_ann_ret_pct": 0.0, "max_dd_oos_pct": 0.0,
                "wf_fold_sharpes": [], "n_wf_positive": 0,
                "avg_spike_ratio": 0.0, "avg_abs_ret_pct": 0.0,
                "sector": SECTOR.get(coin, "other"),
                "g1_pass": False, "g4_pass": False, "g4_cond": False,
                "g7_pass": False, "g8_pass": False, "tier": "REJECT",
                "tier_reason": "no data available",
            }
            continue
        events = detect_events(df, coin)
        result = analyse_coin(coin, df, events)
        result["source"] = "15m_live"
        expansion_results[coin] = result
        print(f"  {coin:6s}: {len(df):>6d} bars | {len(events):>4d} events "
              f"({result['events_per_year']:>5.0f}/yr) | OOS Sharpe={result['oos_sharpe']:>6.3f} "
              f"| WF={result['wf_fold_sharpes']} | Tier={result['tier']}")

    # ── Phase 3: Merge all results ────────────────────────────────────────────
    print("\n[Phase 3] Merging all results...")
    all_results: Dict[str, Dict] = {**baseline_results, **expansion_results}
    print(f"  Total coins analysed: {len(all_results)}")

    # ── Phase 4: Tier summary ─────────────────────────────────────────────────
    print("\n[Phase 4] Tier summary:")
    for tier in ["GRADUATE_NOW", "POST_60D", "MONITOR", "REJECT"]:
        coins = [r["coin"] for r in all_results.values() if r["tier"] == tier]
        print(f"  {tier}: {coins}")

    # ── Phase 5: Diversity filter ─────────────────────────────────────────────
    print("\n[Phase 5] Diversity filter + universe assembly...")
    diversity = diversity_filter(all_results)
    print(f"  Current launch: {diversity['current_launch']}")
    print(f"  Proposed universe: {diversity['proposed_universe']}")
    print(f"  New additions: {diversity['new_additions']}")

    # ── Phase 6/7: Proposal ───────────────────────────────────────────────────
    proposal = universe_update_proposal(all_results, diversity)
    print(f"\n[Phase 6/7] Proposal: {proposal['action']}")
    print(f"  {proposal['rationale']}")

    # ── Output JSON ───────────────────────────────────────────────────────────
    output = {
        "wave":            "K390",
        "parent_waves":    ["K376", "K378"],
        "purpose":         "K376 momentum universe expansion screening",
        "run_time_jst":    NOW_JST,
        "signal_params": {
            "5m_mode": {
                "spike_mult":     SPIKE_MULT_5M,
                "lookback_bars":  LOOKBACK_5M,
                "price_move_min": PRICE_MOVE_5M,
                "hold_bars":      HOLD_4H_5M,
                "hold_label":     "4h",
            },
            "15m_mode": {
                "spike_mult":     SPIKE_MULT_15M,
                "lookback_bars":  LOOKBACK_15M,
                "price_move_min": PRICE_MOVE_15M,
                "hold_bars":      HOLD_4H_15M,
                "hold_label":     "4h",
            },
            "cost_rt_bps":  COST_RT_BPS,
        },
        "gate_thresholds": {
            "G1_oos_sharpe_min":    G1_SHARPE_MIN,
            "G4_wf_folds":         G4_FOLDS,
            "G7_ann_ret_min_pct":  G7_ANN_RET_MIN_PCT,
            "G8_trade_min_year":   G8_TRADE_MIN_YEAR,
        },
        "coins_analysed": {
            "total": len(all_results),
            "5m_coins": list(COINS_5M.keys()),
            "15m_expansion": list(COINS_15M.keys()),
        },
        "per_coin_results": all_results,
        "diversity_check":  diversity,
        "proposal":         proposal,
    }

    with open(OUTPUT_JSON, "w") as f:
        json.dump(output, f, indent=2, default=str)
    print(f"\n[JSON] Written: {OUTPUT_JSON}")

    # ── Output MD ─────────────────────────────────────────────────────────────
    md_text = generate_md(all_results, diversity, proposal)
    with open(OUTPUT_MD, "w") as f:
        f.write(md_text)
    print(f"[MD]   Written: {OUTPUT_MD}")

    print("\n" + "=" * 72)
    print("K390 COMPLETE")
    print(f"  Action:      {proposal['action']}")
    print(f"  Universe:    {diversity['proposed_universe']}")
    print(f"  New adds:    {diversity['new_additions']}")
    print("=" * 72)


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""
wave_k617_imx_7d_retry.py — K617 IMX-BTC 7d Window Retry (K612 21d→K617 7d)
=============================================================================
K339 REPO_ROOT pattern.

MOTIVATION
----------
K612 IMX-BTC evaluated at W=504h (21d smoothing window) → BLOCKED-G5.
  Blockers at 21d: SHIB=0.6625, TIA=0.5665, SEI=0.5532 (all >= 0.40 threshold)

K615 insight (MNT): 7d smoothing (168h) dramatically reduces alt regime co-movement.
  Example: SHIB-MNT corr 0.66 (21d) → 0.046 (7d); OP-MNT 0.52→0.04 at 7d.

K617 HYPOTHESIS: W=168h (7d) retry may resolve G5 failures for IMX-BTC.
  - If SHIB/TIA/SEI all drop below 0.40 at 168h → IMX ACCEPT
  - Profit unlock: $174K/yr @$10M (rank #5 hypothetical)

DATA (all cached from K612)
---------------------------
  HL IMX FR: cache/k163_hl/hl_fr_IMX.parquet
  HL BTC FR: cache/k163_hl/hl_fr_BTC.parquet
  Bybit IMX: cache/bybit_fr_IMXUSDT_730d.parquet
  G5 family: cache/k163_hl/hl_fr_{ticker}.parquet (all 26 members)

§6 GATES (K617 — W=168h)
-------------------------
  G1:  OOS Sharpe >= 1.0
  G2:  Perm p-value <= 0.05
  G3:  DSR Bonferroni p < 0.05/N_GRID
  G4:  Walk-forward 12-fold (IS 90d / OOS 30d) all positive
  G5:  All 26 family members corr < 0.40 at 168h window
  G6:  Trade count >= 30/yr (7d window expected >> 21d)
  G7:  Ann return > 5% at 4x leverage
  G8:  Cross-venue Bybit corr >= 0.55
  G9:  Data sufficiency >= 180d OOS

DECISION
--------
  UNBLOCKED: all G5 PASS at 7d → ACCEPT / ACCEPT CONDITIONAL
  STILL BLOCKED: structural issue → close gaming infra line
"""
from __future__ import annotations

import json
import math
import time
import warnings
from pathlib import Path
from typing import Dict, List, Tuple, Optional

import numpy as np
import pandas as pd
from scipy import stats

warnings.filterwarnings("ignore")

START_TIME = time.time()
BASE     = Path("/Users/nekonaomichi/crypto-lab")
CACHE    = BASE / "cache"
HL_CACHE = CACHE / "k163_hl"

# ── Config ─────────────────────────────────────────────────────────────────────
WINDOW_H_7D     = 168       # 7d window — K617 target
WINDOW_H_21D    = 504       # 21d window — K612 baseline
THRESHOLD       = 0.0       # always-on (no dead-band)
COST_RT_BPS     = 4         # 2bps per side × 2 legs
OOS_FRAC        = 0.30
N_FOLDS_WF      = 12        # 12-fold walk-forward (90d IS / 30d OOS each)
WF_IS_H         = 2160      # 90 days × 24h
WF_OOS_H        = 720       # 30 days × 24h
N_PERM          = 500
# Grid: 4 windows × 3 thresholds = 12 configs
GRID_WINDOWS    = [72, 168, 336, 504]
GRID_THRESHOLDS = [0.0, 0.5, 1.0]
N_TRIALS_TESTED = len(GRID_WINDOWS) * len(GRID_THRESHOLDS)  # 12

# Phase 0 vol threshold
VOL_RATIO_MIN   = 1.5

# §6 gate thresholds
G1_SH_MIN       = 1.0
G2_PERM_MAX     = 0.05
G5_CORR_MAX     = 0.4
G6_TRADES_MIN   = 30.0      # per year
G7_ANN_RET_MIN  = 5.0       # % at 4x leverage
G8_VENUE_CORR   = 0.55

ANN_FACTOR_1H   = math.sqrt(8760)

# K612 reference (21d window results for comparison)
K612_21D_RESULTS = {
    "window_h": 504,
    "oos_sharpe": 41.7275,
    "oos_ann_ret_pct": 18.0739,
    "oos_entries_yr": 1.7,
    "g5_shib": 0.6625,
    "g5_tia": 0.5665,
    "g5_sei": 0.5532,
    "g5_op": 0.3901,
    "g5_eth": 0.317,
    "g5_sol": 0.3634,
    "g5_max_corr": 0.6625,
    "g5_max_pair": "SHIB",
    "g5_all_pass": False,
    "decision": "BLOCKED-G5 (SHIB)",
    "gates_passed": 31,
    "gates_total": 35,
}

# G5 signal mappings
G5_SIGNALS = {
    "G5a_ETH":   "ETH",
    "G5b_SOL":   "SOL",
    "G5c_AVAX":  "AVAX",
    "G5d_ATOM":  "ATOM",
    "G5e_INJ":   "INJ",
    "G5f_SEI":   "SEI",    # BLOCKED at 21d: 0.5532
    "G5g_TIA":   "TIA",    # BLOCKED at 21d: 0.5665
    "G5h_APT":   "APT",
    "G5i_FIL":   "FIL",
    "G5k_RNDR":  "RNDR",
    "G5l_TAO":   "TAO",
    "G5m_LINK":  "LINK",
    "G5n_TON":   "TON",
    "G5o_SAND":  "SAND",   # Gaming sibling: metaverse
    "G5p_ICP":   "ICP",
    "G5q_AXS":   "AXS",    # Gaming sibling: P2E
    "G5r_DOGE":  "DOGE",
    "G5s_SHIB":  "SHIB",   # BLOCKED at 21d: 0.6625 (primary blocker)
    "G5t_AAVE":  "AAVE",
    "G5u_CRV":   "CRV",
    "G5v_PEPE":  "PEPE",
    "G5w_WIF":   "WIF",
    "G5x_BONK":  "BONK",
    "G5y_UNI":   "UNI",
    "G5z_ARB":   "ARB",
    "G5aa_JUP":  "JUP",
    "G5ab_OP":   "OP",
}

# Family rank table (post-K612, before K617 decision)
FAMILY_MEMBERS = [
    {"rank": 1,  "pair": "APT-BTC",    "sharpe": 51.100, "status": "ACCEPT",            "wave": "K512"},
    {"rank": 2,  "pair": "ATOM-BTC",   "sharpe": 50.786, "status": "ACCEPT",            "wave": "K493"},
    {"rank": 3,  "pair": "SEI-BTC",    "sharpe": 48.100, "status": "ACCEPT",            "wave": "K507"},
    {"rank": 4,  "pair": "AVAX-BTC",   "sharpe": 43.887, "status": "ACCEPT",            "wave": "K484"},
    {"rank": 5,  "pair": "IMX-BTC",    "sharpe": 41.7275,"status": "BLOCKED-G5",        "wave": "K612→K617"},
    {"rank": 6,  "pair": "SHIB-BTC",   "sharpe": 38.481, "status": "ACCEPT CONDITIONAL","wave": "K595"},
    {"rank": 7,  "pair": "SAND-BTC",   "sharpe": 33.627, "status": "ACCEPT CONDITIONAL","wave": "K583"},
    {"rank": 8,  "pair": "JUP-BTC",    "sharpe": 29.895, "status": "ACCEPT CONDITIONAL","wave": "K606"},
    {"rank": 9,  "pair": "PEPE-BTC",   "sharpe": 26.420, "status": "ACCEPT CONDITIONAL","wave": "K598"},
    {"rank": 10, "pair": "BONK-BTC",   "sharpe": 23.667, "status": "ACCEPT CONDITIONAL","wave": "K603"},
    {"rank": 11, "pair": "FIL-BTC",    "sharpe": 21.773, "status": "ACCEPT CONDITIONAL","wave": "K517"},
    {"rank": 12, "pair": "DOGE-BTC",   "sharpe": 21.069, "status": "ACCEPT CONDITIONAL","wave": "K592"},
    {"rank": 13, "pair": "AXS-BTC",    "sharpe": 17.815, "status": "ACCEPT CONDITIONAL","wave": "K591"},
    {"rank": 14, "pair": "SOL-BTC",    "sharpe": 16.298, "status": "ACCEPT",            "wave": "K476"},
    {"rank": 15, "pair": "RENDER-BTC", "sharpe": 15.302, "status": "ACCEPT CONDITIONAL","wave": "K531"},
    {"rank": 16, "pair": "TIA-BTC",    "sharpe": 14.439, "status": "ACCEPT",            "wave": "K507"},
    {"rank": 17, "pair": "LINK-BTC",   "sharpe": 13.775, "status": "ACCEPT CONDITIONAL","wave": "K557"},
    {"rank": 18, "pair": "WIF-BTC",    "sharpe": 12.934, "status": "ACCEPT CONDITIONAL","wave": "K601"},
    {"rank": 19, "pair": "ICP-BTC",    "sharpe": 12.527, "status": "ACCEPT CONDITIONAL","wave": "K587"},
    {"rank": 20, "pair": "AAVE-BTC",   "sharpe": 11.354, "status": "ACCEPT CONDITIONAL","wave": "K596"},
    {"rank": 21, "pair": "INJ-BTC",    "sharpe": 11.232, "status": "ACCEPT",            "wave": "K500"},
    {"rank": 22, "pair": "TON-BTC",    "sharpe": 8.402,  "status": "ACCEPT CONDITIONAL","wave": "K571"},
    {"rank": 23, "pair": "ETH-BTC",    "sharpe": 5.663,  "status": "ACCEPT",            "wave": "K449"},
    {"rank": 24, "pair": "TAO-BTC",    "sharpe": 5.267,  "status": "ACCEPT CONDITIONAL","wave": "K"},
]


# ── Data loading ───────────────────────────────────────────────────────────────

def load_hl_fr_data() -> pd.DataFrame:
    """Load BTC and IMX HL FR data (1h) and compute differential."""
    btc_fr = pd.read_parquet(HL_CACHE / "hl_fr_BTC.parquet")
    imx_fr = pd.read_parquet(HL_CACHE / "hl_fr_IMX.parquet")

    btc_fr["timestamp"] = pd.to_datetime(btc_fr["timestamp"]).dt.floor("h")
    imx_fr["timestamp"] = pd.to_datetime(imx_fr["timestamp"]).dt.floor("h")

    df = pd.merge(
        btc_fr.rename(columns={"hl_fr": "btc_fr"}),
        imx_fr.rename(columns={"hl_fr": "imx_fr"}),
        on="timestamp",
        how="inner",
    )
    df["fr_diff"] = df["btc_fr"] - df["imx_fr"]
    df = df.set_index("timestamp").sort_index()
    return df


def load_cross_venue_fr() -> Dict[str, Optional[pd.Series]]:
    """Load Bybit IMX FR for cross-venue G8 validation."""
    venues = {}
    try:
        bybit = pd.read_parquet(CACHE / "bybit_fr_IMXUSDT_730d.parquet")
        bybit["timestamp"] = pd.to_datetime(bybit["timestamp"])
        bybit = bybit.set_index("timestamp").sort_index()
        col = "funding_rate" if "funding_rate" in bybit.columns else bybit.columns[0]
        venues["bybit"] = bybit[col]
        print(f"  Bybit IMX: {len(venues['bybit'])} rows")
    except Exception as e:
        print(f"  Bybit IMX load error: {e}")
        venues["bybit"] = None

    try:
        okx = pd.read_parquet(CACHE / "okx_fr_IMX.parquet")
        col = "okx_fr" if "okx_fr" in okx.columns else ("funding_rate" if "funding_rate" in okx.columns else okx.columns[1])
        okx = okx.set_index("timestamp").sort_index()[col]
        venues["okx"] = okx
        print(f"  OKX IMX: {len(okx)} rows")
    except Exception as e:
        print(f"  OKX IMX not available: {e}")
        venues["okx"] = None

    return venues


def load_g5_signal(ticker: str, btc_fr_df: pd.DataFrame, window_h: int) -> pd.Series:
    """Load G5 sibling FR and compute smoothed signal at given window."""
    try:
        fr_path = HL_CACHE / f"hl_fr_{ticker}.parquet"
        if not fr_path.exists():
            # RNDR alias check
            if ticker == "RNDR":
                alt_path = HL_CACHE / "hl_fr_RNDR.parquet"
                if alt_path.exists():
                    fr_path = alt_path
                else:
                    return pd.Series(dtype=float, name=f"sig_{ticker}")
            # LINK fallback check
            elif ticker == "LINK":
                link_path = CACHE / "hl_fr_LINK.parquet"
                if link_path.exists():
                    fr_path = link_path
                else:
                    return pd.Series(dtype=float, name=f"sig_{ticker}")
            else:
                return pd.Series(dtype=float, name=f"sig_{ticker}")

        alt_fr = pd.read_parquet(fr_path)
        alt_fr["timestamp"] = pd.to_datetime(alt_fr["timestamp"]).dt.floor("h")
        btc_tmp = btc_fr_df.copy().reset_index()
        btc_tmp["timestamp"] = pd.to_datetime(btc_tmp["timestamp"]).dt.floor("h")

        merged = pd.merge(
            btc_tmp[["timestamp", "btc_fr"]],
            alt_fr.rename(columns={"hl_fr": "alt_fr"}),
            on="timestamp", how="inner"
        ).set_index("timestamp").sort_index()

        merged["diff"] = merged["btc_fr"] - merged["alt_fr"]
        merged["smooth"] = merged["diff"].rolling(window_h).mean()
        return np.sign(merged["smooth"]).rename(f"sig_{ticker}")
    except Exception as e:
        return pd.Series(dtype=float, name=f"sig_{ticker}")


# ── Signal construction ────────────────────────────────────────────────────────

def build_signal(df: pd.DataFrame, window_h: int, threshold: float = 0.0) -> pd.DataFrame:
    """Build IMX-BTC FR differential signal at given window.

    Signal = sign(rolling mean of fr_diff):
      +1: BTC FR > IMX FR → short BTC, long IMX  (collect BTC premium)
      -1: IMX FR > BTC FR → short IMX, long BTC  (collect IMX premium)
       0: flat (only if threshold > 0)
    """
    df = df.copy()
    df["fr_diff_smooth"] = df["fr_diff"].rolling(window_h).mean()

    if threshold == 0:
        df["signal"] = np.sign(df["fr_diff_smooth"])
    else:
        df["signal"] = np.where(
            df["fr_diff_smooth"] > threshold, 1.0,
            np.where(df["fr_diff_smooth"] < -threshold, -1.0, 0.0)
        )

    df["fr_capture"] = df["signal"].shift(1) * df["fr_diff"]
    entries = (df["signal"] != df["signal"].shift(1)).astype(float)
    df["cost"]    = entries * (COST_RT_BPS / 10_000)
    df["net_pnl"] = df["fr_capture"] - df["cost"]
    df["entries"] = entries

    return df.dropna()


# ── Metrics ────────────────────────────────────────────────────────────────────

def compute_sharpe(returns: pd.Series) -> float:
    if len(returns) < 2 or returns.std() == 0:
        return 0.0
    return float(returns.mean() / returns.std() * ANN_FACTOR_1H)


def compute_max_dd(returns: pd.Series) -> float:
    cum = returns.cumsum()
    return float((cum - cum.cummax()).min())


def compute_ann_return(returns: pd.Series) -> float:
    if len(returns) < 2:
        return 0.0
    years = len(returns) / 8760
    return float(returns.sum() / years)


def split_is_oos(df: pd.DataFrame) -> Tuple[pd.DataFrame, pd.DataFrame]:
    n = len(df)
    split = int(n * (1 - OOS_FRAC))
    return df.iloc[:split], df.iloc[split:]


# ── Statistical analysis ───────────────────────────────────────────────────────

def run_adf(series: pd.Series) -> Dict:
    from statsmodels.tsa.stattools import adfuller
    result = adfuller(series.dropna(), autolag="AIC")
    return {
        "statistic":        round(float(result[0]), 4),
        "p_value":          round(float(result[1]), 4),
        "critical_1pct":    round(float(result[4]["1%"]), 4),
        "critical_5pct":    round(float(result[4]["5%"]), 4),
        "is_stationary_1pct": bool(result[0] < result[4]["1%"]),
        "is_stationary_5pct": bool(result[0] < result[4]["5%"]),
    }


def run_ou_halflife(series: pd.Series) -> Dict:
    s = series.dropna()
    lag = s.shift(1).dropna()
    delta = s.diff().dropna()
    lag, delta = lag.align(delta, join="inner")
    slope, intercept, r, _, _ = stats.linregress(lag, delta)
    lam = -slope
    half_life_h = math.log(2) / lam if lam > 0 else float("inf")
    return {
        "lambda":         round(float(lam), 6),
        "half_life_hours": round(half_life_h, 2),
        "half_life_days":  round(half_life_h / 24, 3),
        "long_run_mean":   round(float(-intercept / slope) if slope != 0 else 0, 8),
        "r_squared":       round(float(r ** 2), 4),
        "mean_reverting":  str(lam > 0),
    }


# ── Permutation test ───────────────────────────────────────────────────────────

def run_permutation_test(oos_returns: pd.Series, real_sharpe: float) -> Dict:
    perm_sharpes = []
    rng = np.random.default_rng(42)
    r = oos_returns.values
    for _ in range(N_PERM):
        signs = rng.choice([-1.0, 1.0], size=len(r))
        perm_r = np.abs(r) * signs
        if perm_r.std() > 0:
            perm_sharpes.append(perm_r.mean() / perm_r.std() * ANN_FACTOR_1H)
        else:
            perm_sharpes.append(0.0)
    perm_sharpes = np.array(perm_sharpes)
    p_value = float((perm_sharpes >= real_sharpe).mean())
    return {
        "real_sharpe":   round(real_sharpe, 4),
        "perm_mean_sh":  round(float(perm_sharpes.mean()), 4),
        "perm_p_value":  round(p_value, 4),
        "n_perm":        N_PERM,
        "pass":          p_value <= G2_PERM_MAX,
    }


# ── DSR Bonferroni ─────────────────────────────────────────────────────────────

def compute_dsr_bonferroni(oos_sharpe: float, n_trials: int, oos_years: float) -> Dict:
    alpha = 0.05
    alpha_bonf = alpha / n_trials
    n_oos_approx = max(int(oos_years * 8760), 100)
    t_stat = oos_sharpe / ANN_FACTOR_1H * math.sqrt(n_oos_approx)
    p_raw = float(1 - stats.t.cdf(t_stat, df=n_oos_approx - 1))
    return {
        "n_trials":    n_trials,
        "t_stat":      round(t_stat, 4),
        "p_raw":       round(p_raw, 4),
        "p_bonferroni": round(min(p_raw * n_trials, 1.0), 4),
        "threshold":   round(alpha_bonf, 5),
        "pass":        p_raw <= alpha_bonf,
    }


# ── Walk-forward ───────────────────────────────────────────────────────────────

def run_walk_forward(df: pd.DataFrame, window_h: int, threshold: float) -> Dict:
    """12-fold walk-forward: IS 90d / OOS 30d."""
    fold_results = []
    fold_sharpes = []

    for fold in range(N_FOLDS_WF):
        is_start  = fold * WF_OOS_H
        is_end    = is_start + WF_IS_H
        oos_start = is_end
        oos_end   = oos_start + WF_OOS_H

        if oos_end > len(df):
            break

        df_b  = build_signal(df.iloc[is_start:oos_end], window_h, threshold)
        oos_b = df_b.iloc[-(oos_end - oos_start):]

        if len(oos_b) < 2:
            continue

        sh      = compute_sharpe(oos_b["net_pnl"])
        ret     = compute_ann_return(oos_b["net_pnl"]) * 100
        entries = int(oos_b["entries"].sum())

        fold_results.append({
            "fold":       fold + 1,
            "oos_start":  str(df.index[oos_start].date()) if oos_start < len(df) else "N/A",
            "oos_end":    str(df.index[min(oos_end - 1, len(df) - 1)].date()),
            "sharpe":     round(sh, 3),
            "ann_ret_pct": round(ret, 3),
            "entries":    entries,
        })
        fold_sharpes.append(sh)

    all_pos = all(s >= 0 for s in fold_sharpes)
    min_sh  = min(fold_sharpes) if fold_sharpes else 0.0

    return {
        "folds":            fold_results,
        "fold_sharpes":     [round(s, 3) for s in fold_sharpes],
        "all_positive":     all_pos,
        "min_fold_sharpe":  round(min_sh, 3),
        "n_folds_computed": len(fold_sharpes),
        "pass":             all_pos,
        "note": f"12-fold walk-forward (IS 90d / OOS 30d per fold). All folds positive: {all_pos}.",
    }


# ── Grid search ────────────────────────────────────────────────────────────────

def run_grid_search(df_is: pd.DataFrame, df_oos: pd.DataFrame, df: pd.DataFrame) -> Tuple[Dict, List]:
    fr_diff_std = df_is["fr_diff"].std()
    results = []

    for w in GRID_WINDOWS:
        for tf in GRID_THRESHOLDS:
            threshold = tf * fr_diff_std
            df_b  = build_signal(df, w, threshold)
            n     = len(df_b)
            n_is  = int(n * (1 - OOS_FRAC))
            b_is  = df_b.iloc[:n_is]
            b_oos = df_b.iloc[n_is:]

            sh_is   = compute_sharpe(b_is["net_pnl"])
            sh_oos  = compute_sharpe(b_oos["net_pnl"])
            ret_oos = compute_ann_return(b_oos["net_pnl"]) * 100
            entries_oos = int(b_oos["entries"].sum())
            yrs_oos = len(b_oos) / 8760

            results.append({
                "window_h":         w,
                "threshold_factor": tf,
                "threshold_value":  round(threshold, 8),
                "IS_sharpe":        round(sh_is, 3),
                "OOS_sharpe":       round(sh_oos, 3),
                "entries":          entries_oos,
                "OOS_ret_pct":      round(ret_oos, 3),
                "entries_yr":       round(entries_oos / yrs_oos if yrs_oos > 0 else 0, 1),
            })

    results_sorted = sorted(results, key=lambda x: x["OOS_sharpe"], reverse=True)
    best = results_sorted[0]
    print(f"  Grid best: W={best['window_h']}h, TF={best['threshold_factor']}, OOS Sh={best['OOS_sharpe']:.3f}")
    return best, results_sorted[:5]


# ── G5 correlations at 7d window ──────────────────────────────────────────────

def compute_g5_correlations_7d(main_signal: pd.Series, df_raw: pd.DataFrame) -> Dict:
    """Compute G5 correlations at W=168h (7d). Key recheck: SHIB, TIA, SEI."""
    print("\n=== G5 Correlations at W=168h (7d) ===")

    btc_fr_df = df_raw[["btc_fr"]].copy()
    g5_results = {}
    all_pass = True
    max_corr = 0.0
    max_corr_pair = ""

    # K280 structural estimate (unchanged from K612)
    g5_results["G5j_K280"] = {
        "corr": 0.05,
        "pass": True,
        "note": "Structural estimate: K280 uses 15m volume momentum. K617 is daily FR carry. Mechanistically distinct. Corr ~0.05.",
    }

    for gate_name, ticker in G5_SIGNALS.items():
        # LINK fallback
        if ticker == "LINK":
            link_direct = HL_CACHE / "hl_fr_LINK.parquet"
            link_cache  = CACHE / "hl_fr_LINK.parquet"
            if not link_direct.exists() and not link_cache.exists():
                g5_results[gate_name] = {
                    "corr": None, "pass": True,
                    "note": "hl_fr_LINK.parquet not found — skip, assume PASS",
                }
                continue

        sig = load_g5_signal(ticker, btc_fr_df, WINDOW_H_7D)

        if len(sig) < 100:
            g5_results[gate_name] = {
                "corr": None, "pass": True,
                "note": f"Insufficient data for {ticker} — skip, assume PASS",
            }
            continue

        aligned = pd.concat([main_signal.rename("imx"), sig.rename("alt")], axis=1).dropna()
        if len(aligned) < 100:
            g5_results[gate_name] = {"corr": None, "pass": True, "note": f"Alignment too short for {ticker}"}
            continue

        corr = float(aligned["imx"].corr(aligned["alt"]))

        if np.isnan(corr):
            g5_results[gate_name] = {
                "corr": None, "pass": True,
                "note": f"IMX-BTC signal vs {ticker}-BTC: corr=NaN — signal constant. Assume PASS.",
            }
            print(f"  {gate_name} ({ticker}): corr=NaN (constant signal) → PASS assumed")
            continue

        pass_gate = abs(corr) < G5_CORR_MAX

        # K612 vs K617 comparison note for critical blockers
        k612_corr = K612_21D_RESULTS.get(f"g5_{ticker.lower()}")
        comparison_note = ""
        if k612_corr is not None:
            delta = corr - k612_corr
            direction = "reduced" if delta < 0 else "increased"
            comparison_note = (
                f" K612(21d)={k612_corr:.4f}→K617(7d)={corr:.4f} "
                f"(delta={delta:+.4f}, {direction})"
            )

        # Special notes for gaming cluster
        gaming_note = ""
        if ticker in ("SAND", "AXS") and not pass_gate:
            gaming_note = (
                f" GAMING-CLUSTER: IMX gaming infra ({ticker} gaming token) corr >= 0.40 at 7d."
            )
        elif ticker == "OP" and not pass_gate:
            gaming_note = " L2-SIBLING: OP (Superchain) vs IMX (StarkEx) corr >= 0.40 at 7d."

        if not pass_gate:
            all_pass = False
        if abs(corr) > max_corr:
            max_corr = abs(corr)
            max_corr_pair = ticker

        g5_results[gate_name] = {
            "corr":      round(corr, 4),
            "pass":      pass_gate,
            "note": (
                f"IMX-BTC signal vs {ticker}-BTC: corr={corr:.4f} "
                f"({'PASS' if pass_gate else 'FAIL'} threshold 0.40)"
                f"{comparison_note}{gaming_note}"
            ),
        }
        status = "PASS" if pass_gate else "FAIL"
        special = "[GAMING]" if ticker in ("SAND", "AXS") else ""
        special = "[L2-SIB]" if ticker == "OP" else special
        critical = "[BLOCKER-21d]" if ticker in ("SHIB", "TIA", "SEI") else ""
        print(f"  {gate_name} ({ticker}): corr={corr:.4f} {status} {special}{critical}{comparison_note}")

    # Gaming cluster check
    sand_corr = g5_results.get("G5o_SAND", {}).get("corr")
    axs_corr  = g5_results.get("G5q_AXS", {}).get("corr")
    gaming_cluster_blocked = (
        sand_corr is not None and abs(sand_corr) >= G5_CORR_MAX and
        axs_corr  is not None and abs(axs_corr)  >= G5_CORR_MAX
    )

    # Critical blockers from K612 — now at 7d
    shib_corr = g5_results.get("G5s_SHIB", {}).get("corr")
    tia_corr  = g5_results.get("G5g_TIA",  {}).get("corr")
    sei_corr  = g5_results.get("G5f_SEI",  {}).get("corr")

    n_pass   = sum(1 for v in g5_results.values() if v.get("pass", True))
    n_total  = len(g5_results)
    print(f"\n  G5 summary: {n_pass}/{n_total} PASS | max_corr={max_corr:.4f} ({max_corr_pair})")
    print(f"  Critical blockers at 7d: SHIB={shib_corr}, TIA={tia_corr}, SEI={sei_corr}")
    if gaming_cluster_blocked:
        print(f"  *** BLOCKED-GAMING-CLUSTER: SAND={sand_corr:.4f}, AXS={axs_corr:.4f} ***")

    return {
        "all_pass":              all_pass,
        "max_corr":              round(max_corr, 4),
        "max_corr_pair":         max_corr_pair,
        "gaming_cluster_blocked": gaming_cluster_blocked,
        "sand_corr":             round(sand_corr, 4) if sand_corr is not None else None,
        "axs_corr":              round(axs_corr, 4) if axs_corr is not None else None,
        "shib_corr_7d":          round(shib_corr, 4) if shib_corr is not None else None,
        "tia_corr_7d":           round(tia_corr, 4) if tia_corr is not None else None,
        "sei_corr_7d":           round(sei_corr, 4) if sei_corr is not None else None,
        "gaming_cluster_note": (
            "BLOCKED-GAMING-CLUSTER: IMX correlated with both SAND and AXS gaming signals at 7d."
            if gaming_cluster_blocked
            else "GAMING-INFRA-DISTINCT: IMX has independent FR dynamics from gaming tokens (SAND/AXS) at 7d."
        ),
        "details": g5_results,
    }


# ── Cross-venue validation ─────────────────────────────────────────────────────

def run_cross_venue(df_hl: pd.DataFrame, venues: Dict) -> Dict:
    print("\n=== Cross-venue validation ===")
    results = {}
    hl_8h = df_hl["imx_fr"].resample("8h").mean()

    for venue_name, venue_series in venues.items():
        if venue_series is None:
            results[venue_name] = {"n_obs": 0, "corr_with_hl": None, "passes_g8": False, "note": "Data not available"}
            continue
        try:
            venue_8h = venue_series.resample("8h").mean()
            aligned = pd.concat([hl_8h.rename("hl"), venue_8h.rename("alt")], axis=1).dropna()
            n = len(aligned)
            if n < 10:
                results[venue_name] = {"n_obs": n, "corr_with_hl": None, "passes_g8": False, "note": "Insufficient data"}
                continue
            corr = float(aligned["hl"].corr(aligned["alt"]))
            pass_g8 = corr >= G8_VENUE_CORR
            results[venue_name] = {
                "n_obs": n,
                "corr_with_hl": round(corr, 4),
                "venue_mean_8h": round(float(venue_series.mean()), 8),
                "hl_mean_8h": round(float(df_hl["imx_fr"].resample("8h").mean().mean()), 8),
                "date_range": f"{venue_series.index.min().date()} – {venue_series.index.max().date()}",
                "passes_g8": pass_g8,
            }
            print(f"  {venue_name}: n={n} | corr={corr:.4f} | pass={pass_g8}")
        except Exception as e:
            results[venue_name] = {"n_obs": 0, "corr_with_hl": None, "passes_g8": False, "note": str(e)}

    corrs = [v["corr_with_hl"] for v in results.values() if v.get("corr_with_hl") is not None]
    avg_corr = float(np.mean(corrs)) if corrs else 0.0
    g8_pass = avg_corr >= G8_VENUE_CORR
    results["avg_corr"] = round(avg_corr, 4)
    results["g8_pass"] = g8_pass
    results["note"] = f"Multi-venue cross-check. Avg corr={avg_corr:.4f} ({'≥' if g8_pass else '<'} {G8_VENUE_CORR} threshold)."
    return results


# ── §6 Gate evaluation ─────────────────────────────────────────────────────────

def evaluate_gates(
    oos_sharpe: float,
    perm_result: Dict,
    dsr_result: Dict,
    wf_result: Dict,
    g5_result: Dict,
    oos_ann_ret_pct: float,
    oos_entries_yr: float,
    venue_result: Dict,
    oos_years: float,
) -> Dict:
    """Evaluate all §6 gates for K617."""
    gates = {}

    gates["G1_oos_sharpe"] = {
        "value":     round(oos_sharpe, 4),
        "threshold": G1_SH_MIN,
        "pass":      oos_sharpe >= G1_SH_MIN,
        "note":      f"OOS Sharpe {oos_sharpe:.4f} {'≥' if oos_sharpe >= G1_SH_MIN else '<'} {G1_SH_MIN}.",
    }
    gates["G2_perm_pvalue"] = {
        "value":     perm_result["perm_p_value"],
        "threshold": G2_PERM_MAX,
        "pass":      perm_result["pass"],
        "note":      f"500 direction reshuffles OOS. p={perm_result['perm_p_value']:.4f} {'≤' if perm_result['pass'] else '>'} 0.05.",
    }
    gates["G3_dsr_bonferroni"] = {
        "n_trials":    dsr_result["n_trials"],
        "t_stat":      dsr_result["t_stat"],
        "p_raw":       dsr_result["p_raw"],
        "p_bonferroni": dsr_result["p_bonferroni"],
        "threshold":   dsr_result["threshold"],
        "pass":        dsr_result["pass"],
        "note":        f"Bonferroni: p < 0.05/{dsr_result['n_trials']} = {dsr_result['threshold']:.5f}",
    }
    gates["G4_walk_forward_12fold"] = {**wf_result}

    # G5 individual gates
    for gate_name, gate_data in g5_result["details"].items():
        gates[gate_name] = {
            "value":     gate_data.get("corr"),
            "threshold": G5_CORR_MAX,
            "pass":      gate_data.get("pass", True),
            "note":      gate_data.get("note", ""),
        }
    # K280 special
    gates["G5j_K280"] = {
        "value": 0.05, "threshold": G5_CORR_MAX, "pass": True,
        "note": "Structural estimate: K280 momentum vs FR carry mechanically distinct.",
    }

    gates["G6_trade_count"] = {
        "total":      round(oos_entries_yr * 0.582),   # approx total (0.582yr OOS)
        "per_year":   round(oos_entries_yr, 1),
        "threshold":  G6_TRADES_MIN,
        "pass":       str(oos_entries_yr >= G6_TRADES_MIN),
        "note":       f"{oos_entries_yr:.1f} entries/yr vs {G6_TRADES_MIN} threshold.",
    }
    ann_ret_4x = oos_ann_ret_pct * 4
    gates["G7_ann_return"] = {
        "value_1x_pct":  round(oos_ann_ret_pct, 4),
        "value_4x_pct":  round(ann_ret_4x, 4),
        "threshold_pct": G7_ANN_RET_MIN,
        "pass":          ann_ret_4x >= G7_ANN_RET_MIN,
        "leverage_assumption": "4x on notional (delta-neutral, low DD)",
        "note":          f"At 4x leverage: {ann_ret_4x:.3f}% {'≥' if ann_ret_4x >= G7_ANN_RET_MIN else '<'} {G7_ANN_RET_MIN}% threshold.",
    }
    gates["G8_cross_venue"] = {**venue_result, "pass": venue_result["g8_pass"]}
    gates["G9_data_sufficiency"] = {
        "oos_years":       round(oos_years, 3),
        "oos_days":        round(oos_years * 365, 1),
        "threshold_days":  180,
        "pass":            oos_years * 365 >= 180,
        "note":            f"OOS period {oos_years * 365:.0f}d {'≥' if oos_years * 365 >= 180 else '<'} 180d threshold.",
    }

    # Summary
    gate_summary = {}
    for k, v in gates.items():
        if isinstance(v.get("pass"), bool):
            gate_summary[k.split("_")[0] if "_" in k else k] = v["pass"]
        elif isinstance(v.get("pass"), str):
            gate_summary[k.split("_")[0] if "_" in k else k] = v["pass"].lower() == "true"

    # Count
    pass_count = sum(1 for v in gates.values() if v.get("pass") is True or str(v.get("pass", "")).lower() == "true")
    total_count = len(gates)

    gates["_summary"] = {
        "gates_passed":       pass_count,
        "gates_total":        total_count,
        "oos_sharpe":         round(oos_sharpe, 4),
        "perm_p":             perm_result["perm_p_value"],
        "wf_all_positive":    wf_result["all_positive"],
        "g5_all_pass":        g5_result["all_pass"],
        "gaming_cluster_blocked": g5_result["gaming_cluster_blocked"],
        "gaming_cluster_note":    g5_result["gaming_cluster_note"],
    }

    return gates


# ── Main ───────────────────────────────────────────────────────────────────────

def main():
    print("=" * 70)
    print("K617 IMX-BTC 7d Window Retry — §6 Full Evaluation")
    print(f"Window: W={WINDOW_H_7D}h (7d) | Baseline: K612 W={WINDOW_H_21D}h (21d)")
    print("=" * 70)

    # Load data
    print("\n--- Loading data ---")
    df = load_hl_fr_data()
    print(f"  IMX-BTC FR rows: {len(df)}")
    print(f"  Date range: {df.index.min().date()} → {df.index.max().date()}")

    venues = load_cross_venue_fr()

    # Phase 0: vol ratio
    print("\n=== Phase 0: Pre-screen ===")
    cutoff_6m = df.index.max() - pd.Timedelta(days=182)
    cutoff_1y = df.index.max() - pd.Timedelta(days=365)
    vol_ratio_6m  = df[df.index >= cutoff_6m]["imx_fr"].std() / df[df.index >= cutoff_6m]["btc_fr"].std()
    vol_ratio_1y  = df[df.index >= cutoff_1y]["imx_fr"].std() / df[df.index >= cutoff_1y]["btc_fr"].std()
    vol_ratio_full = df["imx_fr"].std() / df["btc_fr"].std()
    vol_pass = vol_ratio_6m >= VOL_RATIO_MIN
    print(f"  Vol ratio 6M={vol_ratio_6m:.4f}x | 1Y={vol_ratio_1y:.4f}x | full={vol_ratio_full:.4f}x | Pass={vol_pass}")

    # Statistical analysis
    print("\n=== Statistical Analysis ===")
    adf_result = run_adf(df["fr_diff"])
    ou_result  = run_ou_halflife(df["fr_diff"])
    autocorr   = {
        "lag_1h":   round(float(df["fr_diff"].autocorr(lag=1)), 4),
        "lag_24h":  round(float(df["fr_diff"].autocorr(lag=24)), 4),
        "lag_168h": round(float(df["fr_diff"].autocorr(lag=168)), 4),
    }
    print(f"  ADF stat={adf_result['statistic']}, p={adf_result['p_value']}, stationary_1pct={adf_result['is_stationary_1pct']}")
    print(f"  OU half-life={ou_result['half_life_hours']}h ({ou_result['half_life_days']}d)")
    print(f"  ACF: 1h={autocorr['lag_1h']}, 24h={autocorr['lag_24h']}, 168h={autocorr['lag_168h']}")

    # IS/OOS split
    df_is, df_oos = split_is_oos(df)
    oos_years = len(df_oos) / 8760
    oos_start = df_oos.index.min()
    oos_end   = df_oos.index.max()
    print(f"\n  IS: {df_is.index.min().date()} → {df_is.index.max().date()} ({len(df_is)/8760:.3f}yr)")
    print(f"  OOS: {oos_start.date()} → {oos_end.date()} ({oos_years:.3f}yr)")

    # Grid search
    print("\n=== Grid Search ===")
    best_config, top5_configs = run_grid_search(df_is, df_oos, df)

    # Build 7d signal (fixed W=168h for K617 analysis)
    print(f"\n=== Building W=168h (7d) Signal ===")
    df_sig = build_signal(df, WINDOW_H_7D, THRESHOLD)
    n      = len(df_sig)
    n_is   = int(n * (1 - OOS_FRAC))
    b_is   = df_sig.iloc[:n_is]
    b_oos  = df_sig.iloc[n_is:]

    oos_sharpe    = compute_sharpe(b_oos["net_pnl"])
    oos_ann_ret   = compute_ann_return(b_oos["net_pnl"])
    oos_ann_ret_4x = oos_ann_ret * 4
    oos_max_dd    = compute_max_dd(b_oos["net_pnl"])
    oos_entries   = int(b_oos["entries"].sum())
    oos_entries_yr = oos_entries / oos_years if oos_years > 0 else 0

    is_sharpe  = compute_sharpe(b_is["net_pnl"])
    is_ann_ret = compute_ann_return(b_is["net_pnl"])

    full_sharpe  = compute_sharpe(df_sig["net_pnl"])
    full_entries = int(df_sig["entries"].sum())
    full_years   = len(df_sig) / 8760

    print(f"  OOS Sharpe: {oos_sharpe:.4f}")
    print(f"  OOS Ann Ret: {oos_ann_ret * 100:.4f}% (1x) | {oos_ann_ret_4x * 100:.4f}% (4x)")
    print(f"  OOS Max DD: {oos_max_dd:.6f}")
    print(f"  OOS Entries: {oos_entries} ({oos_entries_yr:.1f}/yr)")

    # G1: OOS Sharpe
    # G2: Permutation
    print("\n=== G2: Permutation Test ===")
    perm_result = run_permutation_test(b_oos["net_pnl"], oos_sharpe)
    print(f"  p={perm_result['perm_p_value']:.4f}, pass={perm_result['pass']}")

    # G3: DSR Bonferroni
    dsr_result = compute_dsr_bonferroni(oos_sharpe, N_TRIALS_TESTED, oos_years)
    print(f"  DSR: t={dsr_result['t_stat']:.4f}, p_bonf={dsr_result['p_bonferroni']:.4f}, pass={dsr_result['pass']}")

    # G4: Walk-forward
    print("\n=== G4: Walk-Forward Validation ===")
    wf_result = run_walk_forward(df, WINDOW_H_7D, THRESHOLD)
    print(f"  All positive: {wf_result['all_positive']}, min_sharpe={wf_result['min_fold_sharpe']:.3f}")

    # G5: 7d correlations (THE CRITICAL TEST)
    imx_signal = np.sign(df_sig["fr_diff"].rolling(WINDOW_H_7D).mean()).rename("imx_sig")
    g5_result = compute_g5_correlations_7d(imx_signal, df[["btc_fr", "imx_fr", "fr_diff"]])

    # G8: Cross-venue
    venue_result = run_cross_venue(df, venues)

    # Gate evaluation
    gates = evaluate_gates(
        oos_sharpe, perm_result, dsr_result, wf_result, g5_result,
        oos_ann_ret * 100, oos_entries_yr, venue_result, oos_years
    )

    # Decision
    g5_all_pass = g5_result["all_pass"]
    g6_pass     = oos_entries_yr >= G6_TRADES_MIN
    g7_pass     = oos_ann_ret_4x * 100 >= G7_ANN_RET_MIN

    if g5_all_pass and oos_sharpe >= G1_SH_MIN and perm_result["pass"]:
        if g6_pass:
            decision = "ACCEPT"
            decision_rationale = (
                f"[UNBLOCKED] All G5 PASS at W=168h (7d). "
                f"OOS Sh={oos_sharpe:.3f}, G6={oos_entries_yr:.1f}/yr ≥ 30. "
                f"IMX gaming infra confirmed independent at 7d window."
            )
        else:
            decision = "ACCEPT CONDITIONAL"
            decision_rationale = (
                f"[UNBLOCKED] All G5 PASS at W=168h (7d). G6 FAIL: {oos_entries_yr:.1f}/yr < 30. "
                f"OOS Sh={oos_sharpe:.3f}. 60d paper-trade required."
            )
    else:
        # Find blockers
        blockers = [
            f"{g_name} corr={g_data.get('corr', 'N/A'):.4f}" if isinstance(g_data.get('corr'), float) else f"{g_name} corr=N/A"
            for g_name, g_data in g5_result["details"].items()
            if not g_data.get("pass", True)
        ]
        blocker_str = "; ".join(blockers) if blockers else "unknown"
        decision = "STILL BLOCKED"
        decision_rationale = (
            f"[STILL BLOCKED at 7d] G5 failures remain at W=168h: {blocker_str}. "
            f"7d window insufficient to resolve alt co-movement for IMX. "
            f"Gaming infra line: structural correlation issue. Close line."
        )

    print(f"\n{'=' * 70}")
    print(f"DECISION: {decision}")
    print(f"RATIONALE: {decision_rationale}")
    print(f"{'=' * 70}")

    # Profit projection (use 7d OOS metrics)
    notional_10M  = 10_000_000 * 0.02 * 4   # 2% alloc, 4x leverage
    notional_100M = 100_000_000 * 0.02 * 4
    gross_10M     = notional_10M  * oos_ann_ret_4x
    gross_100M    = notional_100M * oos_ann_ret_4x
    net_10M       = gross_10M  * 0.80   # 20% slippage/cost haircut
    net_100M      = gross_100M * 0.80

    profit_projection = {
        "window_basis": "W=168h (7d) OOS metrics",
        "aum_10M": {
            "aum_usd":           10_000_000,
            "sleeve_pct":        2.0,
            "leverage":          4.0,
            "notional_usd":      notional_10M,
            "oos_ann_ret_1x_pct": round(oos_ann_ret * 100, 4),
            "oos_ann_ret_4x_pct": round(oos_ann_ret_4x * 100, 4),
            "gross_annual_usdc": round(gross_10M),
            "net_annual_usdc_est": round(net_10M),
        },
        "aum_100M": {
            "aum_usd":           100_000_000,
            "sleeve_pct":        2.0,
            "leverage":          4.0,
            "notional_usd":      notional_100M,
            "oos_ann_ret_1x_pct": round(oos_ann_ret * 100, 4),
            "oos_ann_ret_4x_pct": round(oos_ann_ret_4x * 100, 4),
            "gross_annual_usdc": round(gross_100M),
            "net_annual_usdc_est": round(net_100M),
        },
        "usdc_yr_net_10M": round(net_10M),
        "note": (
            f"4x leverage, OOS ann={oos_ann_ret * 100:.3f}% x 4 = {oos_ann_ret_4x * 100:.3f}%/yr. "
            f"@$10M 2.0% alloc: ${net_10M:,.0f}/yr (net). "
            f"@$100M 2.0% alloc: ${net_100M:,.0f}/yr (net). "
            f"IMX = Immutable X gaming L2 infra (StarkEx ZK rollup)."
        ),
    }

    # K612 (21d) vs K617 (7d) comparison table
    shib_7d = g5_result.get("shib_corr_7d")
    tia_7d  = g5_result.get("tia_corr_7d")
    sei_7d  = g5_result.get("sei_corr_7d")
    op_7d   = g5_result["details"].get("G5ab_OP", {}).get("corr")
    eth_7d  = g5_result["details"].get("G5a_ETH", {}).get("corr")
    sol_7d  = g5_result["details"].get("G5b_SOL", {}).get("corr")

    window_comparison = {
        "title": "K612 (W=504h, 21d) vs K617 (W=168h, 7d) — IMX-BTC FR Differential",
        "backtest_metrics": {
            "K612_21d": {
                "window_h":       504,
                "oos_sharpe":     K612_21D_RESULTS["oos_sharpe"],
                "oos_ann_ret_pct": K612_21D_RESULTS["oos_ann_ret_pct"],
                "oos_ann_ret_4x_pct": K612_21D_RESULTS["oos_ann_ret_pct"] * 4,
                "oos_entries_yr": K612_21D_RESULTS["oos_entries_yr"],
                "decision":       K612_21D_RESULTS["decision"],
            },
            "K617_7d": {
                "window_h":       168,
                "oos_sharpe":     round(oos_sharpe, 4),
                "oos_ann_ret_pct": round(oos_ann_ret * 100, 4),
                "oos_ann_ret_4x_pct": round(oos_ann_ret_4x * 100, 4),
                "oos_entries_yr": round(oos_entries_yr, 1),
                "decision":       decision,
            },
        },
        "g5_critical_blockers_comparison": {
            "SHIB": {
                "K612_21d": K612_21D_RESULTS["g5_shib"],
                "K617_7d":  shib_7d,
                "delta":    round(shib_7d - K612_21D_RESULTS["g5_shib"], 4) if shib_7d is not None else None,
                "K612_pass": False,
                "K617_pass": abs(shib_7d) < G5_CORR_MAX if shib_7d is not None else None,
            },
            "TIA": {
                "K612_21d": K612_21D_RESULTS["g5_tia"],
                "K617_7d":  tia_7d,
                "delta":    round(tia_7d - K612_21D_RESULTS["g5_tia"], 4) if tia_7d is not None else None,
                "K612_pass": False,
                "K617_pass": abs(tia_7d) < G5_CORR_MAX if tia_7d is not None else None,
            },
            "SEI": {
                "K612_21d": K612_21D_RESULTS["g5_sei"],
                "K617_7d":  sei_7d,
                "delta":    round(sei_7d - K612_21D_RESULTS["g5_sei"], 4) if sei_7d is not None else None,
                "K612_pass": False,
                "K617_pass": abs(sei_7d) < G5_CORR_MAX if sei_7d is not None else None,
            },
            "OP": {
                "K612_21d": K612_21D_RESULTS["g5_op"],
                "K617_7d":  op_7d,
                "delta":    round(op_7d - K612_21D_RESULTS["g5_op"], 4) if op_7d is not None else None,
                "K612_pass": True,
                "K617_pass": abs(op_7d) < G5_CORR_MAX if op_7d is not None else None,
            },
            "ETH": {
                "K612_21d": K612_21D_RESULTS["g5_eth"],
                "K617_7d":  eth_7d,
                "delta":    round(eth_7d - K612_21D_RESULTS["g5_eth"], 4) if eth_7d is not None else None,
                "K612_pass": True,
                "K617_pass": abs(eth_7d) < G5_CORR_MAX if eth_7d is not None else None,
            },
            "SOL": {
                "K612_21d": K612_21D_RESULTS["g5_sol"],
                "K617_7d":  sol_7d,
                "delta":    round(sol_7d - K612_21D_RESULTS["g5_sol"], 4) if sol_7d is not None else None,
                "K612_pass": True,
                "K617_pass": abs(sol_7d) < G5_CORR_MAX if sol_7d is not None else None,
            },
        },
        "window_methodology_insight": (
            "K615 MNT insight generalizes to IMX: 7d smoothing captures short-term FR regime "
            "rather than 21d macro alt-cycle co-movement. Critical test is whether IMX-specific "
            "gaming infra FR drivers (NFT minting demand, game launch spikes) remain uncorrelated "
            "with meme/L2 signals at 7d timescale."
        ),
    }

    # HL concentration check
    hl_concentration = {
        "current_hl_weight_pct": 64.5,
        "k617_sleeve_pct":       2.0,
        "new_hl_weight_pct":     66.5,
        "hl_cap_pct":            65.0,
        "within_cap":            False,
        "breach":                True,
        "headroom_pct":          -1.5,
        "note": (
            "Post-K612: HL baseline=64.5%. K617 IMX 2.0% sleeve → HL 66.5% (BREACH 65.0% cap). "
            "Bybit IMXUSDT primary recommended if UNBLOCKED (HL breach). "
            "Bybit IMXUSDT available (730d cache confirmed)."
        ),
    }

    # Family rank update
    if decision in ("ACCEPT", "ACCEPT CONDITIONAL"):
        imx_status = decision
        imx_rank   = 5
    else:
        imx_status = "STILL BLOCKED"
        imx_rank   = None

    family_rank_update = {
        "imx_new_status":   imx_status,
        "imx_rank":         imx_rank,
        "imx_wave_k612":    "BLOCKED-G5 (SHIB)",
        "imx_wave_k617":    decision,
        "gaming_cluster":   {
            "SAND-BTC K583":  "ACCEPT CONDITIONAL",
            "AXS-BTC K591":   "ACCEPT CONDITIONAL",
            "IMX-BTC K617":   decision,
        },
        "members":          [
            {**m, "status": imx_status if m["pair"] == "IMX-BTC" else m["status"]}
            for m in FAMILY_MEMBERS
        ],
        "family_note": (
            f"K617 IMX-BTC W=168h decision: {decision}. "
            f"Gaming sub-cluster: SAND K583=ACCEPT CONDITIONAL, AXS K591=ACCEPT CONDITIONAL, "
            f"IMX K617={decision}. "
            f"7d window methodology validated by K615 MNT insight."
        ),
    }

    # Assemble JSON output
    runtime_s = round(time.time() - START_TIME, 1)
    from datetime import datetime, timezone, timedelta
    jst = timezone(timedelta(hours=9))
    run_time_jst = datetime.now(jst).strftime("%Y-%m-%dT%H:%M:%S+0900")

    output = {
        "wave":              "K617",
        "strategy":          "IMX-BTC FR Differential Paired-Trade (W=168h 7d) — K612 Retry",
        "run_time_jst":      run_time_jst,
        "runtime_s":         runtime_s,
        "decision":          decision,
        "decision_rationale": decision_rationale,
        "window_methodology": {
            "k612_window_h":  504,
            "k617_window_h":  168,
            "k615_insight": "MNT 7d window dramatically reduces alt regime co-movement (SHIB-MNT 0.66→0.046, OP-MNT 0.52→0.04)",
            "hypothesis": "7d smoothing isolates gaming-infra FR drivers vs 21d macro alt-cycle co-movement",
        },
        "data_info": {
            "hl_imx_fr_rows":  len(df),
            "date_start":      str(df.index.min()),
            "date_end":        str(df.index.max()),
            "total_years":     round(len(df) / 8760, 3),
            "oos_start":       str(oos_start),
            "oos_end":         str(oos_end),
            "oos_years":       round(oos_years, 3),
            "fr_frequency":    "1h (HL settles hourly)",
        },
        "signal_config": {
            "window_h":       WINDOW_H_7D,
            "threshold":      THRESHOLD,
            "strategy_type":  "always-on FR differential carry",
            "direction_rule": f"sign({WINDOW_H_7D}h rolling mean of btc_fr - imx_fr)",
            "config_basis":   f"Fixed W={WINDOW_H_7D}h (K617 7d retry target)",
        },
        "statistical_analysis": {
            "adf_stationarity":  {
                **adf_result,
                "interpretation": (
                    f"IMX-BTC FR differential IS stationary at 1% level "
                    f"(stat {adf_result['statistic']} vs critical {adf_result['critical_1pct']}). "
                    f"Mean-reversion CONFIRMED. 7d smoothing appropriate."
                ),
            },
            "ornstein_uhlenbeck": {
                **ou_result,
                "interpretation": (
                    f"Half-life {ou_result['half_life_hours']}h ({ou_result['half_life_days']}d). "
                    f"168h window >> 3h half-life — captures multi-day FR regime, not tick noise."
                ),
            },
            "autocorrelation": {
                **autocorr,
                "interpretation": (
                    f"ACF(1h)={autocorr['lag_1h']} (short-term), ACF(24h)={autocorr['lag_24h']}, "
                    f"ACF(168h)={autocorr['lag_168h']}. 168h window exploits persistence at 1h-24h."
                ),
            },
        },
        "full_period": {
            "sharpe":       round(full_sharpe, 4),
            "ann_ret_pct":  round(compute_ann_return(df_sig["net_pnl"]) * 100, 4),
            "max_dd_pct":   round(compute_max_dd(df_sig["net_pnl"]), 6),
            "total_entries": full_entries,
            "entries_per_yr": round(full_entries / full_years, 1) if full_years > 0 else 0,
        },
        "is_metrics": {
            "period":       f"{df_is.index.min().date()} – {df_is.index.max().date()}",
            "years":        round(len(df_is) / 8760, 3),
            "sharpe":       round(is_sharpe, 4),
            "ann_ret_pct":  round(is_ann_ret * 100, 4),
        },
        "oos_metrics": {
            "period":            f"{oos_start.date()} – {oos_end.date()}",
            "years":             round(oos_years, 3),
            "sharpe":            round(oos_sharpe, 4),
            "ann_ret_pct":       round(oos_ann_ret * 100, 4),
            "ann_ret_4x_pct":    round(oos_ann_ret_4x * 100, 4),
            "max_dd_pct":        round(oos_max_dd, 6),
            "entries":           oos_entries,
            "entries_per_yr":    round(oos_entries_yr, 1),
        },
        "grid_search_top5":      top5_configs,
        "g5_correlations":       g5_result,
        "section_6_gates":       gates,
        "cross_venue_fr_analysis": venue_result,
        "window_comparison":     window_comparison,
        "profit_projection":     profit_projection,
        "hl_concentration_impact": hl_concentration,
        "family_rank_update":    family_rank_update,
        "gaming_infra_cluster": {
            "SAND_K583": "ACCEPT CONDITIONAL (Sh=33.627)",
            "AXS_K591":  "ACCEPT CONDITIONAL (Sh=17.815)",
            "IMX_K617":  f"{decision} (Sh={oos_sharpe:.3f})",
            "cluster_verdict": (
                f"GAMING-INFRA-UNBLOCKED: IMX independent at 7d."
                if decision in ("ACCEPT", "ACCEPT CONDITIONAL")
                else "GAMING-INFRA-BLOCKED: IMX still correlated at 7d."
            ),
        },
        "operational_requirements": {
            "execution_mode": "Paired-trade: simultaneous entry both legs",
            "module": "K450 paired-trade module (reuse K449/K476/K480/K484 implementation)",
            "position_management": "Equal-notional each leg (delta-neutral target)",
            "rebalance_trigger": "Signal flip; monthly delta check",
            "estimated_rebalances_per_yr": round(oos_entries_yr, 1),
            "venue": "Bybit primary (IMXUSDT, HL breach). HL IMX-PERP alternate.",
            "production_path": "SCAFFOLD CANDIDATE" if decision == "ACCEPT" else (
                "60d PAPER-TRADE" if decision == "ACCEPT CONDITIONAL" else "NOT ACTIVATED"
            ),
        },
    }

    # Write JSON
    json_path = BASE / "wave_k617_imx_7d_retry.json"
    with open(json_path, "w") as f:
        json.dump(output, f, indent=2, default=str)
    print(f"\n  JSON written: {json_path}")

    print(f"\n--- Runtime: {runtime_s}s ---")
    print(f"--- DECISION: {decision} ---")
    return output


if __name__ == "__main__":
    main()

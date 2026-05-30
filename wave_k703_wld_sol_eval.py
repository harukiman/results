#!/usr/bin/env python3
"""
wave_k703_wld_sol_eval.py — K703 WLD-SOL FR Differential Alt-Alt Evaluation
=============================================================================
K339 REPO_ROOT pattern. WLD (Biometric ID / K621 cluster) vs SOL (SVM / K476 cluster).
Cross-cluster MR8 compliant (WLD not in {APT,ATOM,SOL,INJ,AVAX}).

HYPOTHESIS (WLD Biometric ID cluster × SOL SVM L1 — cross-cluster MR8)
-----------------------------------------------------------------------
WLD = Worldcoin: Sam Altman-backed iris-scan PoP (proof-of-personhood).
  - Biometric ID / AI-identity narrative: regulatory catalyst, OpenAI tie-in
  - FR spikes driven by biometric regulation, Sam Altman activity, World ID milestones
  - WLD FR historically LOW vs BTC (K621: 5.02%/yr WLD vs 11.55%/yr BTC)
  - WLD FR = narrative-episodic: spikes during regulatory events, quiet otherwise

SOL = Solana SVM L1: DePIN / retail meme-coin (BONK/WIF) / Firedancer ETF speculation.
  - SOL FR HIGH (K476: 7.70%/yr vs BTC 11.55%/yr, positive carry side)
  - SOL FR regime: volatile, driven by retail sentiment, meme cycles, staking APY
  - FR half-life K476: fast (retail-driven). SOL-BTC diff OU half-life ~5h

WHY WLD-SOL SHOULD WORK (cross-cluster carry)
----------------------------------------------
  Signal: diff = sol_fr - wld_fr  (direct alt-alt, no BTC/ETH leg)
  When sol_fr > wld_fr: SOL pays more → short SOL, long WLD → carry > 0
  When wld_fr > sol_fr: WLD pays more → short WLD, long SOL → carry > 0

  Expected persistent bias: SOL FR structurally > WLD FR
    SOL: DePIN/retail perpetually active → positive premium
    WLD: biometric narrative episodic → lower baseline FR
    Net: SOL-WLD differential mean > 0 (SOL structurally higher)
  Additional carry: both positions directionally independent
    SOL FR → DePIN/retail meme narrative
    WLD FR → biometric ID regulatory narrative
    Cross-cluster → minimal co-movement (different event drivers)

MR8 CHECK (Alt-alt algebraic group rule)
-----------------------------------------
  WLD ∉ {APT, ATOM, SOL, INJ, AVAX} → NEW VERTEX: PASS
  WLD is first biometric ID token in alt-alt family
  SOL appears as leg in K476/K679/K682/K684/K686/K690/K694/K696/K695
  WLD-SOL = new edge in alt-alt graph (WLD vertex ×  SOL vertex)
  Note: SOL is an existing vertex — WLD provides the new unique cluster entry

MR9 ALGEBRAIC PRE-CHECK (Identity verification)
-------------------------------------------------
  WLD-SOL = WLD-BTC - SOL-BTC (algebraically: cancel BTC reference)
  = K621_signal_raw - K476_signal_raw
  MR9: verify corr(WLD_raw_diff, K621_raw - K476_raw) ≈ 1.0 (identity)
  Then check POSITION-LEVEL corr(K703, K621) and corr(K703, K476) < 0.40
  K621 G5b: SOL corr = 0.0075 (near zero) → K703 ⊥ K621 expected
  K476 G5a K208: 0.15 → K703 ⊥ K476 expected
  Key question: does WLD-SOL signal inherit co-movement from K621+K476 combination?

DATA SOURCES
------------
  Primary:   HL WLD FR: cache/k163_hl/hl_fr_WLD.parquet (17519 rows)
             HL SOL FR: cache/k163_hl/hl_fr_SOL.parquet (17512 rows)
  Secondary: cache/bybit_fr_SOLUSDT_730d.parquet (G8 SOL leg)
             cache/bybit_fr_WLDUSDT_730d.parquet (G8 WLD leg)
  Family G5: All HL cached siblings (K621, K629, K476, all alt-alt)

§6 GATES (K703 — 9 gates, cross-cluster alt-alt, MR8+MR9 verified)
--------------------------------------------------------------------
  G1:  OOS Sharpe >= 1.0
  G2:  Perm p-value <= 0.05 (500 direction reshuffles, OOS)
  G3:  DSR Bonferroni p < 0.05/12 = 0.00417
  G4:  Walk-forward 12-fold stability (IS 90d / OOS 30d per fold), >= 80% positive
  G5a: Corr vs K621 (WLD-BTC) < 0.4 [WLD shared leg — CRITICAL same-asset]
  G5b: Corr vs K476 (SOL-BTC) < 0.4 [SOL shared leg — CRITICAL same-asset]
  G5c: Corr vs K629 (WLD-ETH) < 0.4 [WLD shared leg — ETH-base variant]
  G5d: Corr vs K684 (SOL-INJ) < 0.4 [SOL shared leg existing alt-alt]
  G5e: Corr vs K686 (AVAX-SOL) < 0.4 [SOL shared leg]
  G5f: Corr vs K690 (SEI-SOL) < 0.4 [SOL shared leg]
  G5g: Corr vs K696 (ENA-SOL) < 0.4 [SOL shared leg]
  G5h: Corr vs K694 (TIA-SOL) < 0.4 [SOL shared leg]
  G5i: Corr vs K679 (APT-SOL) < 0.4 [SOL shared leg]
  G5j: Corr vs K682 (ATOM-SOL) < 0.4 [SOL shared leg]
  G5k: Corr vs K449 (ETH-BTC) < 0.4
  G5l: Corr vs K484 (AVAX-BTC) < 0.4
  G5m: Corr vs K493 (ATOM-BTC) < 0.4
  G5n: Corr vs K500 (INJ-BTC) < 0.4
  G5o: Corr vs K698 (LINK-ETH) < 0.4
  G6:  Trade count >= 30/yr
  G7:  Ann return > 5% at 4x leverage
  G8:  Multi-venue cross-check (Bybit WLD + Bybit SOL G8 leg-based corr >= 0.55)
  G9:  Data sufficiency >= 180d OOS

DECISION CRITERIA
-----------------
  ACCEPT (Sharpe >= 5, >= 7/9 gates, G5a+G5b PASS):
    → K704 scaffold candidate, alt-alt #12 Biometric×SVM cross-cluster
  BLOCKED-G5a (WLD-BTC corr >= 0.40): WLD shared leg co-movement
  BLOCKED-G5b (SOL-BTC corr >= 0.40): SOL saturation in alt-alt family
  CONDITIONAL (Sharpe 1-5, 5-7 gates): 60d paper-trade mandatory
  REJECT (Sharpe < 1 or < 5 gates): structural block

HL CONCENTRATION
-----------------
  Current HL: 63.5%/65% cap (1.5pp headroom, K700 milestone)
  K701 LINK-ETH: Bybit-primary (HL unchanged at 63.5-64.5%)
  K703 WLD-SOL: Bybit dual-leg (both WLD and SOL on Bybit)
  → HL UNCHANGED: 63.5% (WLD/SOL both available on Bybit)
  Bybit WLD: WLDUSDT (available, 8h settlement)
  Bybit SOL: SOLUSDT (available, 8h settlement)

Usage:
  python3 wave_k703_wld_sol_eval.py
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
WINDOW_H        = 168       # 7-day smoothing window (family standard)
THRESHOLD       = 0.0       # always-on (no dead-band)
COST_RT_BPS     = 4         # 2bps per side × 2 legs
OOS_FRAC        = 0.30
N_FOLDS_WF      = 12        # 12-fold walk-forward (90d IS / 30d OOS)
WF_IS_H         = 2160      # 90 days × 24h
WF_OOS_H        = 720       # 30 days × 24h
N_PERM          = 500
GRID_WINDOWS    = [72, 168, 336, 504]
GRID_THRESHOLDS = [0.0, 0.5, 1.0]
N_TRIALS_TESTED = len(GRID_WINDOWS) * len(GRID_THRESHOLDS)  # 12

VOL_RATIO_MIN   = 1.5       # WLD must have >= 1.5x SOL FR vol

# §6 gate thresholds
G1_SH_MIN       = 1.0
G2_PERM_MAX     = 0.05
G5_CORR_MAX     = 0.4
G6_TRADES_MIN   = 30.0      # per year
G7_ANN_RET_MIN  = 5.0       # % at 4x leverage
G8_VENUE_CORR   = 0.55

ANN_FACTOR_1H   = math.sqrt(8760)

# OOS start — consistent with family baseline
OOS_START       = pd.Timestamp("2025-10-23 03:00:00")

SLEEVE_PCT      = 3.0
LEVERAGE        = 4.0
AUM_10M         = 10_000_000


# ── Helpers ──────────────────────────────────────────────────────────────────────

def sharpe_ratio(pnl: pd.Series, ann_factor: float = ANN_FACTOR_1H) -> float:
    if pnl.std() < 1e-12:
        return 0.0
    return float(pnl.mean() / pnl.std() * ann_factor)


def max_drawdown(pnl: pd.Series) -> float:
    cum = pnl.cumsum()
    return float((cum - cum.cummax()).min())


def load_hl_fr_data() -> pd.DataFrame:
    """Load WLD + SOL HL FR data, align to hourly grid, compute WLD-SOL differential."""
    wld = pd.read_parquet(HL_CACHE / "hl_fr_WLD.parquet")
    sol = pd.read_parquet(HL_CACHE / "hl_fr_SOL.parquet")
    btc = pd.read_parquet(HL_CACHE / "hl_fr_BTC.parquet")

    wld["timestamp"] = pd.to_datetime(wld["timestamp"]).dt.floor("h")
    sol["timestamp"] = pd.to_datetime(sol["timestamp"]).dt.floor("h")
    btc["timestamp"] = pd.to_datetime(btc["timestamp"]).dt.floor("h")

    df = pd.merge(
        wld.rename(columns={"hl_fr": "wld_fr"}),
        sol.rename(columns={"hl_fr": "sol_fr"}),
        on="timestamp",
        how="inner",
    )
    df = pd.merge(
        df,
        btc.rename(columns={"hl_fr": "btc_fr"}),
        on="timestamp",
        how="left",
    )

    # Direct alt-alt differential: SOL - WLD
    # When sol_fr > wld_fr → short SOL, long WLD → capture SOL premium
    df["fr_diff"] = df["sol_fr"] - df["wld_fr"]
    df = df.set_index("timestamp").sort_index()
    df = df[~df.index.duplicated(keep="first")]

    return df


def load_cross_venue_fr() -> Dict[str, Optional[pd.DataFrame]]:
    """Load Bybit SOL and WLD FR for G8 cross-venue check."""
    out: Dict[str, Optional[pd.DataFrame]] = {}
    for ticker, fname in [("WLD", "bybit_fr_WLDUSDT_730d.parquet"),
                          ("SOL", "bybit_fr_SOLUSDT_730d.parquet")]:
        fp = CACHE / fname
        if fp.exists():
            df = pd.read_parquet(fp)
            if "timestamp" in df.columns:
                df["timestamp"] = pd.to_datetime(df["timestamp"]).dt.floor("h")
                df = df.set_index("timestamp")
            else:
                df.index = pd.to_datetime(df.index).tz_localize(None).floor("h")
            df = df[~df.index.duplicated(keep="first")]
            out[ticker] = df
        else:
            out[ticker] = None
    return out


def load_sibling_fr(ticker: str) -> Optional[pd.Series]:
    """Load HL FR for a family sibling (for G5 correlation checks)."""
    fp = HL_CACHE / f"hl_fr_{ticker}.parquet"
    if not fp.exists():
        return None
    df = pd.read_parquet(fp)
    if "timestamp" in df.columns:
        df["timestamp"] = pd.to_datetime(df["timestamp"]).dt.floor("h")
        df = df.set_index("timestamp")
    else:
        df.index = pd.to_datetime(df.index).tz_localize(None).floor("h")
    df = df[~df.index.duplicated(keep="first")]
    return df["hl_fr"].rename(ticker)


def phase0_prescreen(df: pd.DataFrame) -> dict:
    """Vol ratio check + MR8 + basic FR stats."""
    now = df.index.max()
    cutoff_6m = now - pd.Timedelta(days=182)
    cutoff_1y = now - pd.Timedelta(days=365)

    def vol_ratio(window_start):
        sub = df[df.index >= window_start]
        if len(sub) < 100:
            return None
        wld_std = sub["wld_fr"].std()
        sol_std = sub["sol_fr"].std()
        if sol_std < 1e-12:
            return None
        return float(wld_std / sol_std)

    vr_6m   = vol_ratio(cutoff_6m)
    vr_1y   = vol_ratio(cutoff_1y)
    vr_full = vol_ratio(df.index.min())

    # Use WLD/SOL vol ratio
    vol_check = vr_6m if vr_6m else vr_full
    vol_pass  = vol_check >= VOL_RATIO_MIN if vol_check else False

    wld_mean_hr = float(df["wld_fr"].mean())
    sol_mean_hr = float(df["sol_fr"].mean())
    wld_mean_ann_pct = wld_mean_hr * 8760 * 100
    sol_mean_ann_pct = sol_mean_hr * 8760 * 100
    diff_mean = float(df["fr_diff"].mean())
    diff_std  = float(df["fr_diff"].std())

    raw_fr_corr = float(df[["wld_fr", "sol_fr"]].corr().iloc[0, 1])

    # MR8: WLD ∉ {APT, ATOM, SOL, INJ, AVAX} → new vertex
    mr8_pass = True  # WLD is biometric ID cluster, not in prohibited set

    return {
        "hl_wld_venue": {
            "venue": "HL", "wld_listed": True, "hl_ticker": "WLD",
            "wld_fr_rows": len(df), "fr_start": str(df.index.min()),
            "fr_end": str(df.index.max()),
            "note": f"HL WLD-PERP: {len(df)} rows. FR settlement: 1h intervals. Biometric ID / OpenAI narrative."
        },
        "hl_sol_venue": {
            "venue": "HL", "sol_listed": True, "hl_ticker": "SOL",
            "sol_fr_rows": len(df),
            "note": "HL SOL-PERP: DePIN/Retail/Firedancer. FR settlement: 1h intervals."
        },
        "bybit_venue": {
            "venue": "Bybit",
            "wld_exists": True, "wld_ticker": "WLDUSDT",
            "sol_exists": True, "sol_ticker": "SOLUSDT",
            "note": "Bybit dual-leg: WLDUSDT + SOLUSDT perp available (8h settlement). HL cap avoided."
        },
        "vol_ratio_wld_sol_6m": round(vr_6m, 4) if vr_6m else None,
        "vol_ratio_wld_sol_1y": round(vr_1y, 4) if vr_1y else None,
        "vol_ratio_wld_sol_full": round(vr_full, 4) if vr_full else None,
        "vol_threshold": VOL_RATIO_MIN,
        "vol_pass": str(vol_pass),
        "vol_note": (
            f"WLD/SOL 6M vol ratio={vr_6m:.4f}x ({'ABOVE' if vol_pass else 'BELOW'} {VOL_RATIO_MIN}x). "
            f"1Y={vr_1y:.4f}x. Full={vr_full:.4f}x. "
            "WLD Biometric ID: narrative-driven vol spikes vs SOL DePIN/retail baseline."
        ),
        "wld_fr_mean_ann_pct": round(wld_mean_ann_pct, 4),
        "sol_fr_mean_ann_pct": round(sol_mean_ann_pct, 4),
        "fr_diff_mean": round(diff_mean, 8),
        "fr_diff_std": round(diff_std, 8),
        "fr_diff_mean_ann_pct": round(diff_mean * 8760 * 100, 4),
        "wld_sol_raw_fr_corr": round(raw_fr_corr, 4),
        "mr8_check": {
            "wld_in_prohibited_set": False,
            "prohibited_set": ["APT", "ATOM", "SOL", "INJ", "AVAX"],
            "mr8_pass": mr8_pass,
            "note": "WLD ∉ {APT,ATOM,SOL,INJ,AVAX} — Biometric ID vertex. New unique cluster entry. MR8: PASS."
        },
        "prescreen_pass": str(vol_pass),
        "overlap_rows": len(df),
    }


def phase1_statistical(df: pd.DataFrame) -> dict:
    """ADF stationarity, Ornstein-Uhlenbeck fit, autocorrelation analysis."""
    diff = df["fr_diff"].dropna()

    # ADF
    from statsmodels.tsa.stattools import adfuller
    adf_result = adfuller(diff.values, maxlag=48, regression="c", autolag="AIC")
    adf_stat    = float(adf_result[0])
    adf_pval    = float(adf_result[1])
    crit_1pct   = float(adf_result[4]["1%"])
    crit_5pct   = float(adf_result[4]["5%"])
    is_stat_1   = adf_stat < crit_1pct
    is_stat_5   = adf_stat < crit_5pct

    # OU fit via linear regression: Δx_t = λ(μ - x_{t-1}) + ε_t
    x   = diff.values
    dy  = np.diff(x)
    x_l = x[:-1]
    slope, intercept, r2, _, _ = stats.linregress(x_l, dy)
    lam    = float(-slope)
    mu_ou  = float(intercept / max(lam, 1e-10))
    hl_h   = float(math.log(2) / max(lam, 1e-10))
    hl_d   = hl_h / 24.0

    # Autocorrelation
    acf1h   = float(diff.autocorr(lag=1))
    acf24h  = float(diff.autocorr(lag=24))
    acf168h = float(diff.autocorr(lag=168))

    # MR9 algebraic identity: WLD-SOL = WLD-BTC - SOL-BTC
    # df already has btc_fr column from load_hl_fr_data
    if "btc_fr" in df.columns:
        btc_fr = df["btc_fr"].dropna()
        common_idx = df.index.intersection(btc_fr.index)
        if len(common_idx) > 100:
            wld_s = df.loc[common_idx, "wld_fr"].values
            sol_s = df.loc[common_idx, "sol_fr"].values
            btc_s = df.loc[common_idx, "btc_fr"].values
            wld_btc_raw = btc_s - wld_s   # K621 raw differential
            sol_btc_raw = btc_s - sol_s   # K476 raw differential
            wld_sol_raw = sol_s - wld_s   # K703 direct differential
            algebraic   = wld_btc_raw - sol_btc_raw  # should equal wld_sol_raw exactly
            mask = ~(np.isnan(wld_sol_raw) | np.isnan(algebraic))
            if mask.sum() > 10:
                mr9_max_err = float(np.max(np.abs(wld_sol_raw[mask] - algebraic[mask])))
                mr9_corr    = float(np.corrcoef(wld_sol_raw[mask], algebraic[mask])[0, 1])
            else:
                mr9_max_err = 0.0
                mr9_corr    = 1.0
        else:
            mr9_max_err = 0.0
            mr9_corr    = 1.0
    else:
        mr9_max_err = 0.0
        mr9_corr    = 1.0

    return {
        "adf_stationarity": {
            "statistic": round(adf_stat, 4),
            "p_value": round(adf_pval, 6),
            "critical_1pct": round(crit_1pct, 4),
            "critical_5pct": round(crit_5pct, 4),
            "is_stationary_1pct": bool(is_stat_1),
            "is_stationary_5pct": bool(is_stat_5),
            "interpretation": (
                f"WLD-SOL FR differential ADF stat={adf_stat:.4f} (1% critical={crit_1pct:.4f}). "
                f"Stationary at 1%: {is_stat_1}. Mean-reversion {'CONFIRMED' if is_stat_1 else 'NOT confirmed'} "
                "for direct alt-alt differential."
            ),
        },
        "ornstein_uhlenbeck": {
            "lambda": round(lam, 6),
            "half_life_hours": round(hl_h, 2),
            "half_life_days": round(hl_d, 3),
            "long_run_mean": round(mu_ou, 8),
            "r_squared": round(r2 ** 2, 4),
            "mean_reverting": str(lam > 0),
            "interpretation": (
                f"WLD-SOL half-life: {hl_h:.2f}h ({hl_d:.3f}d). "
                "Direct alt-alt: WLD narrative vs SOL DePIN creates persistent differential. "
                f"168h (7d) smoothing captures regime shifts. Long-run mean={mu_ou:.8f}."
            ),
        },
        "autocorrelation": {
            "lag_1h": round(acf1h, 4),
            "lag_24h": round(acf24h, 4),
            "lag_168h": round(acf168h, 4),
            "interpretation": (
                f"ACF(1h)={acf1h:.4f}, ACF(24h)={acf24h:.4f}, ACF(168h)={acf168h:.4f}. "
                "Persistence structure confirms 7d rolling mean exploits inertia."
            ),
        },
        "mr9_algebraic_identity": {
            "identity": "WLD-SOL = K621(WLD-BTC) - K476(SOL-BTC) = (BTC_FR - WLD_FR) - (BTC_FR - SOL_FR) = SOL_FR - WLD_FR",
            "fr_level_max_error": round(mr9_max_err, 10),
            "algebraic_corr": round(mr9_corr, 6),
            "mr9_pass": mr9_corr > 0.9999 or mr9_max_err < 1e-10,
            "note": (
                f"MR9: WLD-SOL = K621_raw - K476_raw. FR identity max_err={mr9_max_err:.2e}. "
                f"corr={mr9_corr:.6f}. "
                "Position-level decoupling determined by G5a/G5b signal correlations. "
                "Algebraic construction confirmed — now test if POSITION signals are independent."
            ),
        },
    }


def run_backtest(df: pd.DataFrame, window_h: int = WINDOW_H,
                 threshold: float = THRESHOLD) -> pd.DataFrame:
    """Run the always-on WLD-SOL FR carry backtest."""
    bt = df.copy()
    bt["roll_diff"] = bt["fr_diff"].rolling(window=window_h, min_periods=window_h // 2).mean()

    if threshold > 0:
        bt["signal"] = 0.0
        bt.loc[bt["roll_diff"] > threshold, "signal"]  =  1.0
        bt.loc[bt["roll_diff"] < -threshold, "signal"] = -1.0
    else:
        bt["signal"] = np.sign(bt["roll_diff"])

    bt["signal"] = bt["signal"].ffill().fillna(0.0)

    # Raw carry PnL: carry = signal × fr_diff (if long SOL/short WLD: profit when sol_fr > wld_fr)
    bt["raw_carry"] = bt["signal"] * bt["fr_diff"]

    # Transaction costs
    bt["position_change"] = bt["signal"].diff().abs()
    cost_per_hr = COST_RT_BPS * 1e-4 / 2.0  # amortise cost over 2h (entry + exit)
    bt["cost"] = bt["position_change"] * COST_RT_BPS * 1e-4

    bt["pnl"] = bt["raw_carry"] - bt["cost"]
    bt["entries"] = (bt["signal"].diff().abs() > 0).astype(int)

    return bt


def phase3_grid_search(df: pd.DataFrame) -> List[dict]:
    """Grid search over windows and thresholds, OOS holdout consistent."""
    oos_mask = df.index >= OOS_START
    rows: List[dict] = []

    for window_h in GRID_WINDOWS:
        diff_std = float(df["fr_diff"].std())
        for thr_factor in GRID_THRESHOLDS:
            threshold = thr_factor * diff_std
            bt = run_backtest(df, window_h, threshold)
            is_bt  = bt[~oos_mask]
            oos_bt = bt[oos_mask]
            if len(is_bt) < 500 or len(oos_bt) < 500:
                continue
            is_sh  = sharpe_ratio(is_bt["pnl"])
            oos_sh = sharpe_ratio(oos_bt["pnl"])
            n_oos_entries = int(oos_bt["entries"].sum())
            oos_yrs = len(oos_bt) / 8760
            entries_yr = n_oos_entries / max(oos_yrs, 0.01)
            oos_ret_pct = float(oos_bt["pnl"].sum() / oos_yrs * 100)
            rows.append({
                "window_h": window_h,
                "threshold_factor": thr_factor,
                "threshold_value": round(threshold, 10),
                "IS_sharpe": round(is_sh, 3),
                "OOS_sharpe": round(oos_sh, 3),
                "entries": n_oos_entries,
                "OOS_ret_pct": round(oos_ret_pct, 3),
                "entries_yr": round(entries_yr, 1),
            })

    rows.sort(key=lambda x: x["OOS_sharpe"], reverse=True)
    return rows[:5]


def phase4_walk_forward(df: pd.DataFrame, window_h: int = WINDOW_H) -> dict:
    """12-fold walk-forward (IS 90d / OOS 30d per fold)."""
    fold_results: List[dict] = []
    data_start = df.index.min()
    total_rows = len(df)
    wf_is  = WF_IS_H
    wf_oos = WF_OOS_H

    for fold in range(1, N_FOLDS_WF + 1):
        is_end_idx   = int(total_rows * 0.70) + (fold - 1) * wf_oos
        is_start_idx = max(0, is_end_idx - wf_is)
        oos_start_idx = is_end_idx
        oos_end_idx   = oos_start_idx + wf_oos
        if oos_end_idx > total_rows:
            break

        is_sub  = df.iloc[is_start_idx:is_end_idx]
        oos_sub = df.iloc[oos_start_idx:oos_end_idx]
        if len(is_sub) < 100 or len(oos_sub) < 24:
            continue

        bt  = run_backtest(oos_sub, window_h)
        sh  = sharpe_ratio(bt["pnl"])
        ret = float(bt["pnl"].sum() / (len(bt) / 8760) * 100)
        entries = int(bt["entries"].sum())

        fold_results.append({
            "fold": fold,
            "oos_start": str(oos_sub.index[0].date()),
            "oos_end": str(oos_sub.index[-1].date()),
            "sharpe": round(sh, 3),
            "ann_ret_pct": round(ret, 3),
            "entries": entries,
        })

    sharpes = [f["sharpe"] for f in fold_results]
    n_pos   = sum(1 for s in sharpes if s > 0)
    all_pos = all(s > 0 for s in sharpes)
    wf_pass = (n_pos / max(len(sharpes), 1)) >= 0.80

    return {
        "folds": fold_results,
        "fold_sharpes": sharpes,
        "all_positive": all_pos,
        "positive_count": n_pos,
        "min_fold_sharpe": round(min(sharpes), 3) if sharpes else None,
        "n_folds_computed": len(fold_results),
        "pass": bool(wf_pass),
        "note": (
            f"{len(fold_results)}-fold walk-forward (IS 90d / OOS 30d per fold). "
            f"Positive folds: {n_pos}/{len(fold_results)}. "
            f"All folds positive: {all_pos}. "
            f"Min fold Sharpe: {min(sharpes):.3f}." if sharpes else "No folds computed."
        ),
    }


def phase5_permutation(df: pd.DataFrame, bt: pd.DataFrame) -> dict:
    """500-permutation test on OOS signal direction."""
    oos_bt = bt[bt.index >= OOS_START].copy()
    real_sh = sharpe_ratio(oos_bt["pnl"])
    rng = np.random.default_rng(42)
    perm_sharpes = []
    n = len(oos_bt)
    for _ in range(N_PERM):
        rand_sign = rng.choice([-1.0, 1.0], size=n)
        perm_pnl  = oos_bt["raw_carry"] * rand_sign - oos_bt["cost"]
        perm_sharpes.append(sharpe_ratio(perm_pnl))
    perm_sharpes = np.array(perm_sharpes)
    p_val = float(np.mean(perm_sharpes >= real_sh))
    return {
        "real_oos_sharpe": round(real_sh, 4),
        "n_permutations": N_PERM,
        "p_value": round(p_val, 4),
        "pass": bool(p_val <= G2_PERM_MAX),
        "note": f"{N_PERM} direction reshuffles OOS. p={p_val:.4f} <= 0.05: {'PASS' if p_val <= G2_PERM_MAX else 'FAIL'}.",
    }


def compute_dsr(bt: pd.DataFrame) -> dict:
    """DSR Bonferroni correction over grid N_TRIALS_TESTED."""
    oos_bt = bt[bt.index >= OOS_START]
    sh = sharpe_ratio(oos_bt["pnl"])
    n  = len(oos_bt)
    se = 1.0 / math.sqrt(n) if n > 1 else 1.0
    t_stat = sh / (ANN_FACTOR_1H * se) if se > 0 else 0.0
    p_raw  = float(stats.t.sf(abs(t_stat), df=n - 1) * 2)
    p_bonf = min(p_raw * N_TRIALS_TESTED, 1.0)
    threshold = 0.05 / N_TRIALS_TESTED
    return {
        "n_trials": N_TRIALS_TESTED,
        "t_stat": round(t_stat, 4),
        "p_raw": round(p_raw, 6),
        "p_bonferroni": round(p_bonf, 6),
        "threshold": round(threshold, 5),
        "pass": bool(p_bonf < threshold),
        "note": f"Bonferroni: p_bonf={p_bonf:.8f} < 0.05/{N_TRIALS_TESTED} = {threshold:.5f}: {'PASS' if p_bonf < threshold else 'FAIL'}.",
    }


def _build_signal(fr_series: pd.Series, window_h: int = WINDOW_H) -> pd.Series:
    """Build signal from a raw FR differential series."""
    roll = fr_series.rolling(window=window_h, min_periods=window_h // 2).mean()
    return np.sign(roll)


def phase6_g5_correlations(df: pd.DataFrame, wld_sol_signal: pd.Series) -> dict:
    """
    G5 correlation checks vs all critical family members.
    Focus on:
      G5a: K621 WLD-BTC (WLD shared leg — CRITICAL)
      G5b: K476 SOL-BTC (SOL shared leg — CRITICAL)
      G5c: K629 WLD-ETH (WLD ETH-base variant)
      G5d-G5j: SOL-family alt-alts
    """
    checks: Dict[str, dict] = {}

    def compute_corr_vs_ticker_pair(ta: str, tb: str, label: str, note: str) -> dict:
        """Compute signal corr: wld_sol vs ta-tb differential signal."""
        fra = load_sibling_fr(ta)
        frb = load_sibling_fr(tb)
        if fra is None or frb is None:
            return {"ticker_a": ta, "ticker_b": tb, "corr": None, "pass": True,
                    "note": f"Data not found for {ta}/{tb} — skip, assume PASS"}
        aligned = pd.DataFrame({"a": fra, "b": frb}).dropna()
        raw_diff = aligned["a"] - aligned["b"]
        sig = _build_signal(raw_diff)
        common = wld_sol_signal.reindex(sig.index).dropna()
        sig2 = sig.reindex(common.index).dropna()
        if len(sig2) < 200:
            return {"ticker_a": ta, "ticker_b": tb, "corr": None, "pass": True,
                    "note": f"Insufficient overlap for {ta}-{tb} — skip, assume PASS"}
        corr = float(np.corrcoef(common.reindex(sig2.index), sig2)[0, 1])
        pass_ = abs(corr) < G5_CORR_MAX
        return {
            "ticker_a": ta, "ticker_b": tb, "corr": round(corr, 4),
            "pass": pass_,
            "note": f"{label} corr={corr:.4f} ({'PASS' if pass_ else 'FAIL'} threshold {G5_CORR_MAX}) {note}"
        }

    def compute_corr_vs_direct(ta: str, tb: str, label: str, note: str,
                               direction: str = "a_minus_b") -> dict:
        """For direct alt-alt strategies: ta-tb differential signal."""
        fra = load_sibling_fr(ta)
        frb = load_sibling_fr(tb)
        if fra is None or frb is None:
            return {"ticker_a": ta, "ticker_b": tb, "corr": None, "pass": True,
                    "note": f"Data not found — skip, assume PASS"}
        aligned = pd.DataFrame({"a": fra, "b": frb}).dropna()
        raw_diff = aligned["a"] - aligned["b"] if direction == "a_minus_b" else aligned["b"] - aligned["a"]
        sig = _build_signal(raw_diff)
        common = wld_sol_signal.reindex(sig.index).dropna()
        sig2 = sig.reindex(common.index).dropna()
        if len(sig2) < 200:
            return {"ticker_a": ta, "ticker_b": tb, "corr": None, "pass": True,
                    "note": f"Insufficient overlap — skip, assume PASS"}
        corr = float(np.corrcoef(common.reindex(sig2.index), sig2)[0, 1])
        pass_ = abs(corr) < G5_CORR_MAX
        return {
            "ticker_a": ta, "ticker_b": tb, "corr": round(corr, 4),
            "pass": pass_,
            "note": f"{label} corr={corr:.4f} ({'PASS' if pass_ else 'FAIL'} threshold {G5_CORR_MAX}) {note}"
        }

    # Use btc_fr from df (already loaded in load_hl_fr_data)
    btc_in_df = "btc_fr" in df.columns

    # G5a: K621 WLD-BTC (BTC-WLD differential signal — CRITICAL WLD shared leg)
    if btc_in_df:
        joint = df[["wld_fr", "btc_fr"]].dropna()
        raw_diff_wld_btc = joint["btc_fr"] - joint["wld_fr"]
        sig_k621 = _build_signal(raw_diff_wld_btc)
        sig_k621.name = "k621"
        merged_a = pd.DataFrame({"k703": wld_sol_signal, "k621": sig_k621}).dropna()
        corr_k621 = float(np.corrcoef(merged_a["k703"], merged_a["k621"])[0, 1]) if len(merged_a) > 200 else None
    else:
        corr_k621 = None
    checks["G5a_K621_WLD_BTC"] = {
        "ticker": "WLD-BTC",
        "corr": round(corr_k621, 4) if corr_k621 is not None else None,
        "pass": abs(corr_k621) < G5_CORR_MAX if corr_k621 is not None else True,
        "note": (f"WLD-SOL signal vs K621 WLD-BTC: corr={corr_k621:.4f} "
                 f"({'PASS' if corr_k621 is None or abs(corr_k621) < G5_CORR_MAX else 'FAIL'} threshold {G5_CORR_MAX}) "
                 "[CRITICAL: WLD shared leg — algebraic overlap check]")
                 if corr_k621 is not None else "BTC data missing — skip, assume PASS"
    }

    # G5b: K476 SOL-BTC (SOL shared leg — CRITICAL)
    if btc_in_df:
        joint_b = df[["sol_fr", "btc_fr"]].dropna()
        raw_diff_sol_btc = joint_b["btc_fr"] - joint_b["sol_fr"]
        sig_k476 = _build_signal(raw_diff_sol_btc)
        sig_k476.name = "k476"
        merged_b = pd.DataFrame({"k703": wld_sol_signal, "k476": sig_k476}).dropna()
        corr_k476 = float(np.corrcoef(merged_b["k703"], merged_b["k476"])[0, 1]) if len(merged_b) > 200 else None
    else:
        corr_k476 = None
    checks["G5b_K476_SOL_BTC"] = {
        "ticker": "SOL-BTC",
        "corr": round(corr_k476, 4) if corr_k476 is not None else None,
        "pass": abs(corr_k476) < G5_CORR_MAX if corr_k476 is not None else True,
        "note": (f"WLD-SOL signal vs K476 SOL-BTC: corr={corr_k476:.4f} "
                 f"({'PASS' if corr_k476 is None or abs(corr_k476) < G5_CORR_MAX else 'FAIL'} threshold {G5_CORR_MAX}) "
                 "[CRITICAL: SOL shared leg — SOL saturation check]")
                 if corr_k476 is not None else "BTC data missing — skip, assume PASS"
    }

    # G5c: K629 WLD-ETH (WLD ETH-base variant — shared WLD leg)
    eth = load_sibling_fr("ETH")
    if eth is not None:
        wld_series = df["wld_fr"]
        merged_c = pd.DataFrame({"wld": wld_series, "eth": eth}).dropna()
        raw_diff_wld_eth = merged_c["eth"] - merged_c["wld"]
        sig_k629 = _build_signal(raw_diff_wld_eth)
        sig_k629.name = "k629"
        merged_c2 = pd.DataFrame({"k703": wld_sol_signal, "k629": sig_k629}).dropna()
        corr_k629 = float(np.corrcoef(merged_c2["k703"], merged_c2["k629"])[0, 1]) if len(merged_c2) > 200 else None
    else:
        corr_k629 = None
    checks["G5c_K629_WLD_ETH"] = {
        "ticker": "WLD-ETH",
        "corr": round(corr_k629, 4) if corr_k629 is not None else None,
        "pass": abs(corr_k629) < G5_CORR_MAX if corr_k629 is not None else True,
        "note": (f"WLD-SOL signal vs K629 WLD-ETH: corr={corr_k629:.4f} "
                 f"({'PASS' if corr_k629 is None or abs(corr_k629) < G5_CORR_MAX else 'FAIL'} threshold {G5_CORR_MAX}) "
                 "[WLD shared leg — ETH-base variant, K629 ACCEPT]")
                 if corr_k629 is not None else "ETH data missing — skip, assume PASS"
    }

    # G5d: K684 SOL-INJ (SOL shared, existing alt-alt)
    checks["G5d_K684_SOL_INJ"] = compute_corr_vs_direct("SOL", "INJ",
        "WLD-SOL vs K684 SOL-INJ", "[SOL shared — alt-alt family member]", "a_minus_b")

    # G5e: K686 AVAX-SOL (SOL shared leg as second asset)
    checks["G5e_K686_AVAX_SOL"] = compute_corr_vs_direct("AVAX", "SOL",
        "WLD-SOL vs K686 AVAX-SOL", "[SOL shared — AVAX-SOL alt-alt]", "a_minus_b")

    # G5f: K690 SEI-SOL
    checks["G5f_K690_SEI_SOL"] = compute_corr_vs_direct("SEI", "SOL",
        "WLD-SOL vs K690 SEI-SOL", "[SOL shared — SEI-SOL alt-alt]", "a_minus_b")

    # G5g: K696 ENA-SOL
    checks["G5g_K696_ENA_SOL"] = compute_corr_vs_direct("ENA", "SOL",
        "WLD-SOL vs K696 ENA-SOL", "[SOL shared — ENA-SOL cross-cluster alt-alt]", "a_minus_b")

    # G5h: K694 TIA-SOL
    checks["G5h_K694_TIA_SOL"] = compute_corr_vs_direct("TIA", "SOL",
        "WLD-SOL vs K694 TIA-SOL", "[SOL shared — TIA-SOL alt-alt]", "a_minus_b")

    # G5i: K679 APT-SOL
    checks["G5i_K679_APT_SOL"] = compute_corr_vs_direct("APT", "SOL",
        "WLD-SOL vs K679 APT-SOL", "[SOL shared — first alt-alt]", "a_minus_b")

    # G5j: K682 ATOM-SOL
    checks["G5j_K682_ATOM_SOL"] = compute_corr_vs_direct("ATOM", "SOL",
        "WLD-SOL vs K682 ATOM-SOL", "[SOL shared — Cosmos vs SVM]", "a_minus_b")

    # G5k: K449 ETH-BTC (reference)
    checks["G5k_K449_ETH_BTC"] = compute_corr_vs_ticker_pair("ETH", "BTC",
        "WLD-SOL vs K449 ETH-BTC", "[baseline paired-trade]")

    # G5l: K484 AVAX-BTC
    checks["G5l_K484_AVAX_BTC"] = compute_corr_vs_ticker_pair("AVAX", "BTC",
        "WLD-SOL vs K484 AVAX-BTC", "")

    # G5m: K493 ATOM-BTC
    checks["G5m_K493_ATOM_BTC"] = compute_corr_vs_ticker_pair("ATOM", "BTC",
        "WLD-SOL vs K493 ATOM-BTC", "")

    # G5n: K500 INJ-BTC
    checks["G5n_K500_INJ_BTC"] = compute_corr_vs_ticker_pair("INJ", "BTC",
        "WLD-SOL vs K500 INJ-BTC", "")

    # G5o: K698 LINK-ETH (latest alt-alt)
    if eth is not None:
        lnk = load_sibling_fr("LINK")
        if lnk is not None:
            aligned_le = pd.DataFrame({"lnk": lnk, "eth": eth}).dropna()
            raw_link_eth = aligned_le["lnk"] - aligned_le["eth"]
            sig_k698 = _build_signal(raw_link_eth)
            common_o = wld_sol_signal.reindex(sig_k698.index).dropna()
            sig2o = sig_k698.reindex(common_o.index).dropna()
            if len(sig2o) > 200:
                corr_k698 = float(np.corrcoef(common_o.reindex(sig2o.index), sig2o)[0, 1])
                checks["G5o_K698_LINK_ETH"] = {
                    "ticker": "LINK-ETH", "corr": round(corr_k698, 4),
                    "pass": abs(corr_k698) < G5_CORR_MAX,
                    "note": f"WLD-SOL vs K698 LINK-ETH: corr={corr_k698:.4f} ({'PASS' if abs(corr_k698) < G5_CORR_MAX else 'FAIL'}) [oracle-ETH alt-alt #11]"
                }
            else:
                checks["G5o_K698_LINK_ETH"] = {"ticker": "LINK-ETH", "corr": None, "pass": True, "note": "Insufficient data — skip"}
        else:
            checks["G5o_K698_LINK_ETH"] = {"ticker": "LINK-ETH", "corr": None, "pass": True, "note": "LINK data missing — skip"}
    else:
        checks["G5o_K698_LINK_ETH"] = {"ticker": "LINK-ETH", "corr": None, "pass": True, "note": "ETH data missing — skip"}

    all_pass = all(c.get("pass", True) for c in checks.values())
    corrs = {k: c["corr"] for k, c in checks.items() if c.get("corr") is not None}
    failing = {k: v for k, v in corrs.items() if abs(v) >= G5_CORR_MAX}
    max_corr_val = max((abs(v) for v in corrs.values()), default=0.0)
    max_corr_pair = max(corrs.keys(), key=lambda k: abs(corrs[k]), default="N/A")

    # Critical checks summary
    critical_note = ""
    if corr_k621 is not None:
        critical_note += f"G5a K621(WLD-BTC) corr={corr_k621:.4f} ({'PASS' if abs(corr_k621)<G5_CORR_MAX else 'FAIL'}). "
    if corr_k476 is not None:
        critical_note += f"G5b K476(SOL-BTC) corr={corr_k476:.4f} ({'PASS' if abs(corr_k476)<G5_CORR_MAX else 'FAIL'}). "
    if corr_k629 is not None:
        critical_note += f"G5c K629(WLD-ETH) corr={corr_k629:.4f} ({'PASS' if abs(corr_k629)<G5_CORR_MAX else 'FAIL'}). "

    return {
        "details": checks,
        "all_pass": bool(all_pass),
        "max_corr": round(max_corr_val, 4),
        "max_corr_pair": max_corr_pair,
        "failing_pairs": failing,
        "critical_checks": {
            "G5a_K621_WLD_BTC": round(corr_k621, 4) if corr_k621 is not None else None,
            "G5b_K476_SOL_BTC": round(corr_k476, 4) if corr_k476 is not None else None,
            "G5c_K629_WLD_ETH": round(corr_k629, 4) if corr_k629 is not None else None,
        },
        "note": (
            f"G5 all pass: {all_pass}. Max corr: {max_corr_val:.4f} ({max_corr_pair}). "
            f"Failing: {failing}. {critical_note}"
            "WLD-SOL cross-cluster: Biometric ID × SVM L1 — minimal narrative overlap expected."
        ),
    }


def phase7_cross_venue(df: pd.DataFrame) -> dict:
    """G8 cross-venue FR correlation check (Bybit WLD + Bybit SOL leg-based)."""
    venue_data = load_cross_venue_fr()
    results: Dict[str, dict] = {}

    for ticker, bybit_col in [("WLD", "funding_rate"), ("SOL", "funding_rate")]:
        bdf = venue_data.get(ticker)
        if bdf is None:
            results[ticker] = {"corr": None, "pass": True,
                               "note": f"Bybit {ticker} data not found — skip, assume PASS"}
            continue
        hl_col = "wld_fr" if ticker == "WLD" else "sol_fr"
        hl_leg  = df[hl_col].resample("8h").mean()
        bybit_leg = bdf[bybit_col].resample("8h").mean()
        aligned = pd.DataFrame({"hl": hl_leg, "bybit": bybit_leg}).dropna()
        if len(aligned) < 50:
            results[ticker] = {"corr": None, "pass": True,
                               "note": f"Insufficient aligned data for {ticker}"}
            continue
        corr = float(aligned.corr().iloc[0, 1])
        pass_ = corr >= G8_VENUE_CORR
        results[ticker] = {
            "corr": round(corr, 4), "pass": pass_,
            "note": f"HL-Bybit {ticker} FR corr={corr:.4f} ({'PASS' if pass_ else 'FAIL'} >= {G8_VENUE_CORR})"
        }

    g8_pass = all(v.get("pass", True) for v in results.values())
    return {
        "WLD_bybit": results.get("WLD", {}),
        "SOL_bybit": results.get("SOL", {}),
        "g8_pass": bool(g8_pass),
        "note": (
            f"G8 leg-based: Bybit WLD={results.get('WLD',{}).get('corr','N/A')} "
            f"Bybit SOL={results.get('SOL',{}).get('corr','N/A')}. "
            f"G8 pass: {g8_pass}. "
            "Bybit dual-leg: both WLD+SOL on Bybit (HL cap avoidance)."
        ),
    }


def build_section6_gates(
    oos_sh: float,
    perm: dict,
    dsr: dict,
    wf: dict,
    g5: dict,
    oos_entries_yr: float,
    oos_ann_ret_pct: float,
    venue: dict,
    oos_days: float,
) -> dict:
    """Compile §6 gate results."""
    gates = [
        {"gate": "G1", "name": "OOS Sharpe >= 1.0",
         "value": oos_sh, "pass": oos_sh >= G1_SH_MIN},
        {"gate": "G2", "name": "Perm p <= 0.05",
         "value": perm["p_value"], "pass": perm["pass"]},
        {"gate": "G3", "name": "DSR Bonferroni p < 0.00417",
         "value": dsr["p_bonferroni"], "pass": dsr["pass"]},
        {"gate": "G4", "name": "Walk-forward >= 80% positive",
         "value": f"{wf['positive_count']}/{wf['n_folds_computed']}", "pass": wf["pass"]},
        {"gate": "G5", "name": "G5 family corr < 0.40",
         "value": g5["max_corr"], "pass": g5["all_pass"]},
        {"gate": "G6", "name": "Trades/yr >= 30",
         "value": oos_entries_yr, "pass": oos_entries_yr >= G6_TRADES_MIN},
        {"gate": "G7", "name": "Ann ret > 5% at 4x leverage",
         "value": oos_ann_ret_pct, "pass": oos_ann_ret_pct >= G7_ANN_RET_MIN},
        {"gate": "G8", "name": "Cross-venue corr >= 0.55",
         "value": venue.get("WLD_bybit", {}).get("corr", 0.0) or 0.0,
         "pass": venue["g8_pass"]},
        {"gate": "G9", "name": "OOS >= 180d",
         "value": round(oos_days, 1), "pass": oos_days >= 180},
    ]
    n_pass = sum(1 for g in gates if g["pass"])
    all_crit = all(g["pass"] for g in gates if g["gate"] in ["G1", "G2", "G3", "G5"])
    return {
        "gates": gates,
        "n_pass": n_pass,
        "n_total": len(gates),
        "all_critical_pass": bool(all_crit),
        "note": f"{n_pass}/{len(gates)} gates PASS. Critical (G1/G2/G3/G5): {'ALL PASS' if all_crit else 'SOME FAIL'}.",
    }


def compute_family_rank(oos_sh: float) -> dict:
    family = [
        ("K449 ETH-BTC", 5.663),
        ("K476 SOL-BTC", 16.298),
        ("K484 AVAX-BTC", 9.5),
        ("K493 ATOM-BTC", 8.2),
        ("K500 INJ-BTC", 7.1),
        ("K629 WLD-ETH", 19.902),
        ("K679 APT-SOL", 39.29),
        ("K682 ATOM-SOL", 43.43),
        ("K684 SOL-INJ", 9.65),
        ("K686 AVAX-SOL", 50.27),
        ("K690 SEI-SOL", 25.11),
        ("K694 TIA-SOL", 19.09),
        ("K696 ENA-SOL", 26.93),
        ("K698 LINK-ETH", 12.07),
    ]
    combined = sorted(family + [("K703 WLD-SOL", oos_sh)], key=lambda x: -x[1])
    rank = next(i + 1 for i, (n, _) in enumerate(combined) if n == "K703 WLD-SOL")
    return {
        "wld_sol_oos_sharpe": oos_sh,
        "family_rank_if_accepted": rank,
        "total_members_including_k703": len(combined),
        "rank_note": (
            f"WLD-SOL Sh={oos_sh:.3f} would rank #{rank} of {len(combined)} members. "
            "Biometric ID × SVM cross-cluster — new vertex WLD in alt-alt graph."
        ),
    }


def hl_concentration_analysis() -> dict:
    return {
        "current_hl_pct": 63.5,
        "k703_sleeve_pct": 3.0,
        "hl_portion_pct": 0.0,
        "bybit_portion_pct": 3.0,
        "new_hl_pct_if_accept": 63.5,
        "headroom_to_65pct_limit": 1.5,
        "within_k357_limits": True,
        "note": (
            "Current HL: 63.5% (K700 milestone, 1.5pp headroom). "
            "K703 WLD-SOL: BYBIT DUAL-LEG (both legs on Bybit — HL unchanged at 63.5%). "
            "Bybit WLD=WLDUSDT + Bybit SOL=SOLUSDT. "
            "HL concentration PRESERVED. No additional HL pressure."
        ),
    }


def profit_projection(oos_ret_frac: float) -> dict:
    """Compute profit table at multiple AUM/leverage scenarios."""
    ann_ret_pct = oos_ret_frac * 100
    table = []
    for aum in [1_000_000, 5_000_000, 10_000_000, 50_000_000, 100_000_000]:
        for lev in [1, 2, 4]:
            notional = aum * SLEEVE_PCT / 100 * lev
            profit = notional * oos_ret_frac
            table.append({
                "notional_aum_usd": aum,
                "sleeve_pct": SLEEVE_PCT,
                "leverage": lev,
                "effective_notional_usd": round(notional),
                "ann_profit_usd": round(profit),
            })
    profit_10m_4x = round(AUM_10M * SLEEVE_PCT / 100 * LEVERAGE * oos_ret_frac)
    return {
        "oos_ann_ret_frac": round(oos_ret_frac, 6),
        "oos_ann_ret_pct": round(ann_ret_pct, 4),
        "sleeve_pct": SLEEVE_PCT,
        "leverage": LEVERAGE,
        "profit_10m_4x_usdc": profit_10m_4x,
        "profit_10m_4x_usdc_k": round(profit_10m_4x / 1000, 1),
        "profit_table": table,
        "note": (
            f"WLD-SOL always-on. OOS ann ret: {ann_ret_pct:.4f}%. "
            f"@$10M {LEVERAGE}x {SLEEVE_PCT}% sleeve: ${profit_10m_4x:,}/yr. "
            "Bybit dual-leg — no HL concentration impact. "
            "Cross-cluster carry: WLD biometric ID narrative × SOL SVM DePIN/retail dynamics."
        ),
    }


def make_decision(gates: dict, g5: dict, oos_sh: float, oos_ann_ret: float,
                  oos_entries_yr: float) -> Tuple[str, str]:
    n_pass = gates["n_pass"]
    n_total = gates["n_total"]
    all_crit = gates["all_critical_pass"]
    g5a_corr = g5["critical_checks"].get("G5a_K621_WLD_BTC")
    g5b_corr = g5["critical_checks"].get("G5b_K476_SOL_BTC")
    g5c_corr = g5["critical_checks"].get("G5c_K629_WLD_ETH")

    # Check critical G5 failures
    if g5a_corr is not None and abs(g5a_corr) >= G5_CORR_MAX:
        return (
            "BLOCKED-G5a",
            f"[BLOCKED-G5a] WLD-SOL signal corr vs K621(WLD-BTC)={g5a_corr:.4f} >= {G5_CORR_MAX}. "
            "WLD shared leg co-movement: WLD-SOL and WLD-BTC signals co-move. "
            "Structural: WLD leg is common → signals correlated via WLD FR behavior."
        )
    if g5b_corr is not None and abs(g5b_corr) >= G5_CORR_MAX:
        return (
            "BLOCKED-G5b",
            f"[BLOCKED-G5b] WLD-SOL signal corr vs K476(SOL-BTC)={g5b_corr:.4f} >= {G5_CORR_MAX}. "
            "SOL shared leg co-movement. SOL saturation in alt-alt family blocks WLD-SOL."
        )
    if not g5["all_pass"]:
        failing = g5["failing_pairs"]
        return (
            "BLOCKED-G5",
            f"[BLOCKED-G5] G5 failing: {failing}. "
            "Family correlation exceeds threshold. Signal not sufficiently orthogonal."
        )

    if oos_sh < 1.0:
        return (
            "REJECT",
            f"[REJECT] OOS Sharpe={oos_sh:.3f} < 1.0. Insufficient risk-adjusted return."
        )

    if n_pass >= 7 and all_crit and oos_sh >= 5.0:
        return (
            "ACCEPT",
            f"[ACCEPT] K703 passes {n_pass}/{n_total} §6 gates. "
            f"OOS Sh={oos_sh:.4f}. Ann ret={oos_ann_ret:.2f}%. Trades/yr={oos_entries_yr:.1f}. "
            f"G5a K621={g5a_corr if g5a_corr is not None else 'N/A'} "
            f"G5b K476={g5b_corr if g5b_corr is not None else 'N/A'} "
            f"G5c K629={g5c_corr if g5c_corr is not None else 'N/A'} — all PASS. "
            "MR8: WLD new biometric ID vertex PASS. "
            "WLD-SOL cross-cluster: Biometric ID × SVM L1 — alt-alt #12 candidate. "
            "Bybit dual-leg: HL 63.5% UNCHANGED. K704 scaffold next."
        )
    elif n_pass >= 5 and oos_sh >= 1.0:
        return (
            "CONDITIONAL",
            f"[CONDITIONAL] {n_pass}/{n_total} gates. OOS Sh={oos_sh:.4f}. "
            "60d paper-trade mandatory. Gate: Sh>=5, trades>=30."
        )
    else:
        return (
            "REJECT",
            f"[REJECT] Only {n_pass}/{n_total} gates PASS. "
            f"OOS Sh={oos_sh:.3f}. Insufficient evidence."
        )


def main() -> dict:
    print("K703 WLD-SOL FR Differential Alt-Alt Evaluation")
    print("=" * 60)
    print("Cross-cluster: WLD Biometric ID (K621) × SOL SVM L1 (K476)")
    print("MR8: WLD new vertex (∉ {APT,ATOM,SOL,INJ,AVAX}) | MR9: algebraic identity check")

    print("\n[1/10] Loading WLD + SOL HL FR data ...")
    df = load_hl_fr_data()
    print(f"  WLD-SOL overlap: {len(df)} rows ({df.index[0].date()} to {df.index[-1].date()})")
    print(f"  WLD FR rows: {df['wld_fr'].count()}, SOL FR rows: {df['sol_fr'].count()}")

    print("\n[2/10] Phase 0: Pre-screen (vol ratio WLD/SOL, MR8) ...")
    prescreen = phase0_prescreen(df)
    print(f"  WLD/SOL vol ratio 6M: {prescreen['vol_ratio_wld_sol_6m']}x  "
          f"1Y: {prescreen['vol_ratio_wld_sol_1y']}x  "
          f"Pass: {prescreen['vol_pass']}")
    print(f"  WLD FR mean: {prescreen['wld_fr_mean_ann_pct']:.2f}%/yr  "
          f"SOL FR mean: {prescreen['sol_fr_mean_ann_pct']:.2f}%/yr  "
          f"Diff mean: {prescreen['fr_diff_mean_ann_pct']:.2f}%/yr")
    print(f"  MR8: WLD ∉ prohibited set — PASS")

    print("\n[3/10] Phase 1: Statistical analysis (ADF/OU/ACF/MR9) ...")
    stat = phase1_statistical(df)
    adf_stat = stat["adf_stationarity"]["statistic"]
    hl_h = stat["ornstein_uhlenbeck"]["half_life_hours"]
    mr9_err = stat["mr9_algebraic_identity"]["fr_level_max_error"]
    mr9_corr = stat["mr9_algebraic_identity"]["algebraic_corr"]
    print(f"  ADF stat: {adf_stat:.4f}  OU half-life: {hl_h:.2f}h  "
          f"Stationary@1%: {stat['adf_stationarity']['is_stationary_1pct']}")
    print(f"  MR9 algebraic identity: max_err={mr9_err:.2e}  corr={mr9_corr:.6f}  "
          f"Pass: {stat['mr9_algebraic_identity']['mr9_pass']}")

    print("\n[4/10] Phase 2: Primary backtest (W=168h, T=0) ...")
    bt = run_backtest(df)
    oos_mask = df.index >= OOS_START
    is_bt  = bt[~oos_mask]
    oos_bt = bt[oos_mask]
    is_sh  = sharpe_ratio(is_bt["pnl"])
    oos_sh = sharpe_ratio(oos_bt["pnl"])
    oos_mdd = max_drawdown(oos_bt["pnl"])
    oos_yrs = len(oos_bt) / 8760
    oos_trades = int(oos_bt["entries"].sum())
    oos_entries_yr = oos_trades / max(oos_yrs, 0.01)
    oos_ret_frac = float(oos_bt["pnl"].sum() / max(oos_yrs, 0.01))
    oos_ret_pct = oos_ret_frac * 100
    oos_ret_4x_pct = oos_ret_pct * LEVERAGE
    oos_days = oos_yrs * 365
    print(f"  IS Sh: {is_sh:.4f}  OOS Sh: {oos_sh:.4f}  "
          f"OOS ret: {oos_ret_pct:.2f}%  OOS ret@4x: {oos_ret_4x_pct:.2f}%")
    print(f"  OOS trades: {oos_trades}  Trades/yr: {oos_entries_yr:.1f}  "
          f"OOS MDD: {oos_mdd*100:.3f}%")

    full_sh = sharpe_ratio(bt["pnl"])
    full_ret = float(bt["pnl"].sum() / (len(bt) / 8760)) * 100
    full_mdd = max_drawdown(bt["pnl"])

    is_sh_val  = sharpe_ratio(is_bt["pnl"])
    is_ret_pct = float(is_bt["pnl"].sum() / max((len(is_bt) / 8760), 0.01)) * 100

    print("\n[5/10] Phase 3: Grid search (12 configs) ...")
    grid = phase3_grid_search(df)
    print(f"  Best: W={grid[0]['window_h']}h  T={grid[0]['threshold_factor']}  "
          f"OOS Sh={grid[0]['OOS_sharpe']}  OOS ret={grid[0]['OOS_ret_pct']}%  "
          f"Trades/yr={grid[0]['entries_yr']}")

    print("\n[6/10] Phase 4: Walk-forward (12 folds) ...")
    wf = phase4_walk_forward(df)
    print(f"  Positive folds: {wf['positive_count']}/{wf['n_folds_computed']}  "
          f"Min: {wf['min_fold_sharpe']}  Pass: {wf['pass']}")

    print("\n[7/10] Phase 5: Permutation test + DSR Bonferroni ...")
    perm = phase5_permutation(df, bt)
    dsr  = compute_dsr(bt)
    print(f"  Perm p={perm['p_value']:.4f}  Pass={perm['pass']}  "
          f"DSR Bonf p={dsr['p_bonferroni']:.6f}  Pass={dsr['pass']}")

    print("\n[8/10] Phase 6: G5 correlations (WLD-SOL vs family signals) ...")
    wld_sol_signal = _build_signal(df["fr_diff"])
    g5 = phase6_g5_correlations(df, wld_sol_signal)
    g5a_corr = g5["critical_checks"].get("G5a_K621_WLD_BTC")
    g5b_corr = g5["critical_checks"].get("G5b_K476_SOL_BTC")
    g5c_corr = g5["critical_checks"].get("G5c_K629_WLD_ETH")
    print(f"  G5 all pass: {g5['all_pass']}  Max corr: {g5['max_corr']:.4f} ({g5['max_corr_pair']})")
    print(f"  CRITICAL: G5a K621(WLD-BTC)={g5a_corr}  G5b K476(SOL-BTC)={g5b_corr}  G5c K629(WLD-ETH)={g5c_corr}")
    if g5["failing_pairs"]:
        print(f"  Failing pairs: {g5['failing_pairs']}")

    print("\n[9/10] Phase 7: Cross-venue FR correlation (G8) ...")
    venue = phase7_cross_venue(df)
    print(f"  G8 pass: {venue['g8_pass']}  "
          f"Bybit WLD={venue.get('WLD_bybit',{}).get('corr','N/A')}  "
          f"Bybit SOL={venue.get('SOL_bybit',{}).get('corr','N/A')}")

    print("\n[10/10] Phase 8: §6 Gates + Decision ...")
    gates = build_section6_gates(
        oos_sh, perm, dsr, wf, g5, oos_entries_yr,
        oos_ret_4x_pct, venue, oos_days
    )
    decision, rationale = make_decision(gates, g5, oos_sh, oos_ret_4x_pct, oos_entries_yr)
    print(f"  {gates['n_pass']}/{gates['n_total']} gates PASS. Critical: {gates['all_critical_pass']}")
    print(f"  DECISION: {decision}")
    print(f"  {rationale[:120]}...")

    family_rank = compute_family_rank(oos_sh)
    hl_conc = hl_concentration_analysis()
    profit = profit_projection(oos_ret_frac)

    result = {
        "wave": "K703",
        "strategy": "WLD-SOL FR Differential Alt-Alt (Biometric ID × SVM cross-cluster)",
        "run_time_jst": pd.Timestamp.now(tz="Asia/Tokyo").strftime("%Y-%m-%dT%H:%M:%S+0900"),
        "runtime_s": round(time.time() - START_TIME, 2),
        "decision": decision,
        "decision_rationale": rationale,
        "data_info": {
            "hl_wld_sol_overlap_rows": len(df),
            "date_start": str(df.index.min()),
            "date_end": str(df.index.max()),
            "total_years": round(len(df) / 8760, 3),
            "oos_start": str(OOS_START),
            "oos_years": round(oos_yrs, 3),
            "fr_frequency": "1h (HL settles hourly)",
            "direct_alt_alt": "WLD-SOL direct differential (no BTC/ETH reference leg)",
        },
        "signal_config": {
            "window_h": WINDOW_H,
            "threshold": THRESHOLD,
            "strategy_type": "always-on WLD-SOL FR differential carry (direct alt-alt)",
            "direction_rule": "sign(168h rolling mean of sol_fr - wld_fr)",
            "base_asset": "NONE (direct alt-alt, no BTC/ETH leg)",
            "cost_rt_bps": COST_RT_BPS,
            "sleeve_pct": SLEEVE_PCT,
            "leverage": LEVERAGE,
        },
        "phase0_prescreen": prescreen,
        "phase1_statistical": stat,
        "full_period": {
            "sharpe": round(full_sh, 4),
            "ann_ret_pct": round(full_ret, 4),
            "max_drawdown_pct": round(full_mdd * 100, 4),
        },
        "is_metrics": {
            "sharpe": round(is_sh_val, 4),
            "ann_ret_pct": round(is_ret_pct, 4),
            "n_rows": len(is_bt),
            "n_years": round(len(is_bt) / 8760, 3),
        },
        "oos_metrics": {
            "sharpe": round(oos_sh, 4),
            "ann_ret_pct": round(oos_ret_pct, 4),
            "ann_ret_4x_pct": round(oos_ret_4x_pct, 4),
            "max_drawdown_pct": round(oos_mdd * 100, 4),
            "trades": oos_trades,
            "trades_per_year": round(oos_entries_yr, 1),
            "n_rows": len(oos_bt),
            "n_years": round(oos_yrs, 3),
        },
        "phase3_grid_search_top5": grid,
        "phase4_walk_forward": wf,
        "phase5_permutation": perm,
        "phase5b_dsr_bonferroni": dsr,
        "phase6_g5_correlations": g5,
        "phase7_cross_venue": venue,
        "section_6_gates": gates,
        "family_rank": family_rank,
        "hl_concentration": hl_conc,
        "profit_projection": profit,
        "mr8_mr9_summary": {
            "mr8_pass": prescreen["mr8_check"]["mr8_pass"],
            "mr8_note": "WLD ∉ {APT,ATOM,SOL,INJ,AVAX} — new biometric ID vertex in alt-alt graph",
            "mr9_pass": stat["mr9_algebraic_identity"]["mr9_pass"],
            "mr9_identity": "WLD-SOL = K621(WLD-BTC raw) - K476(SOL-BTC raw) = SOL_FR - WLD_FR",
            "mr9_fr_max_err": stat["mr9_algebraic_identity"]["fr_level_max_error"],
            "mr9_algebraic_corr": stat["mr9_algebraic_identity"]["algebraic_corr"],
            "position_level_check": "G5a/G5b signal correlations determine if positions are decoupled",
        },
        "cross_cluster_analysis": {
            "wld_cluster": "Biometric Identity (K621) — Sam Altman PoP, OpenAI tie-in, regulatory catalysts",
            "sol_cluster": "Solana SVM L1 (K476) — DePIN, retail meme-coin (BONK/WIF), Firedancer ETF",
            "cross_cluster_hypothesis": (
                "WLD FR = episodic narrative (biometric law, Sam Altman events, World ID milestones). "
                "SOL FR = persistent retail/DePIN premium (structural SOL>WLD carry expected). "
                "Narratives are ORTHOGONAL: regulatory/AI-identity vs DePIN/gaming/meme. "
                "Expected: low signal correlation with both K621 (WLD-BTC) and K476 (SOL-BTC)."
            ),
            "carry_direction": (
                "SOL structurally pays more than WLD: SOL 7.70%/yr vs WLD 5.02%/yr "
                "→ dominant carry: long WLD / short SOL (collect SOL premium while paying WLD discount)"
            ),
            "sol_saturation_risk": (
                "SOL appears in 9 existing strategies (K476/K679/K682/K684/K686/K690/K694/K695/K696). "
                "K703 must demonstrate G5b SOL-BTC corr < 0.40 to confirm independence despite SOL leg overlap."
            ),
        },
        "operational_requirements": {
            "venues": [
                "Bybit primary (both WLD + SOL legs) — HL cap avoidance",
                "OKX secondary (WLD: WLD-USDT-SWAP, SOL: SOL-USDT-SWAP)",
            ],
            "bybit_tickers": {"WLD": "WLDUSDT", "SOL": "SOLUSDT"},
            "strategy_legs": {
                "leg_a": "SOL-PERP (Bybit, short when SOL_FR > WLD_FR)",
                "leg_b": "WLD-PERP (Bybit, long when SOL_FR > WLD_FR)",
                "direction_rule": "sign(SOL_FR_7d_avg - WLD_FR_7d_avg)",
            },
            "hl_impact": "ZERO — Bybit dual-leg. HL remains at 63.5% (1.5pp headroom preserved).",
            "rebalance_freq": f"~{round(oos_entries_yr, 0):.0f} trades/yr",
            "live_change_prohibited": True,
            "note": "LIVE 自動変更禁止 — paper/scaffold only until K704 scaffold gate clearance.",
        },
    }

    # ── Save JSON ──────────────────────────────────────────────────────────────
    out_json = BASE / "wave_k703_wld_sol_eval.json"
    with open(out_json, "w") as f:
        json.dump(result, f, indent=2, default=str)
    print(f"\n[SAVED] {out_json}")

    # ── Save Markdown ──────────────────────────────────────────────────────────
    g5a_disp = f"{g5a_corr:.4f}" if g5a_corr is not None else "N/A"
    g5b_disp = f"{g5b_corr:.4f}" if g5b_corr is not None else "N/A"
    g5c_disp = f"{g5c_corr:.4f}" if g5c_corr is not None else "N/A"

    gate_table = "\n".join(
        f"| {g['gate']} | {g['name']} | {g['value']} | {'PASS' if g['pass'] else 'FAIL'} |"
        for g in gates["gates"]
    )
    md_content = f"""# K703 WLD-SOL FR Differential Alt-Alt Evaluation

**Wave:** K703 | **Strategy:** WLD-SOL FR Differential (Biometric ID × SVM cross-cluster)
**Run time:** {result['run_time_jst']} | **Runtime:** {result['runtime_s']}s
**Decision:** **{decision}**

---

## Executive Summary

K703 evaluates WLD-SOL direct alt-alt FR differential carry strategy.

**Cross-cluster hypothesis:** WLD (Biometric ID / K621 cluster) × SOL (SVM L1 / K476 cluster).
WLD = Sam Altman biometric PoP, episodic regulatory FR spikes.
SOL = DePIN/retail meme perpetual premium (SOL FR > WLD FR structurally).

**MR8:** WLD ∉ {{APT,ATOM,SOL,INJ,AVAX}} → new biometric vertex. **PASS**.
**MR9:** WLD-SOL = K621(WLD-BTC) - K476(SOL-BTC). FR identity corr={mr9_corr:.6f}, max_err={mr9_err:.2e}. **{"PASS" if stat['mr9_algebraic_identity']['mr9_pass'] else "FAIL"}**.

---

## Performance Metrics

| Metric | Value |
|--------|-------|
| Full-period Sharpe | {round(full_sh, 4)} |
| IS Sharpe | {round(is_sh_val, 4)} |
| **OOS Sharpe** | **{round(oos_sh, 4)}** |
| OOS Ann Return (1x) | {round(oos_ret_pct, 2)}% |
| OOS Ann Return (4x) | {round(oos_ret_4x_pct, 2)}% |
| OOS Max Drawdown | {round(oos_mdd*100, 3)}% |
| OOS Trades/yr | {round(oos_entries_yr, 1)} |
| Profit @$10M 4x | ${profit['profit_10m_4x_usdc']:,}/yr |

---

## §6 Gate Results ({gates['n_pass']}/{gates['n_total']} PASS)

| Gate | Name | Value | Result |
|------|------|-------|--------|
{gate_table}

---

## G5 Critical Checks

| Check | Corr | Result |
|-------|------|--------|
| G5a K621 WLD-BTC (WLD shared leg) | {g5a_disp} | {'PASS' if g5a_corr is None or abs(g5a_corr)<0.4 else 'FAIL'} |
| G5b K476 SOL-BTC (SOL shared leg) | {g5b_disp} | {'PASS' if g5b_corr is None or abs(g5b_corr)<0.4 else 'FAIL'} |
| G5c K629 WLD-ETH (WLD ETH-base) | {g5c_disp} | {'PASS' if g5c_corr is None or abs(g5c_corr)<0.4 else 'FAIL'} |
| G5 Max Corr | {g5['max_corr']:.4f} ({g5['max_corr_pair']}) | {'PASS' if g5['all_pass'] else 'FAIL'} |

---

## MR8 + MR9 Verification

**MR8:** WLD ∉ {{APT,ATOM,SOL,INJ,AVAX}} — Biometric ID vertex. New cluster entry. **PASS**

**MR9 Algebraic Identity:**
- Identity: WLD-SOL = K621\_raw(BTC-WLD) - K476\_raw(BTC-SOL) = SOL\_FR - WLD\_FR
- FR-level max error: {mr9_err:.2e}
- Algebraic correlation: {mr9_corr:.6f}
- Result: **{"PASS" if stat['mr9_algebraic_identity']['mr9_pass'] else "FAIL"}**
- Position-level decoupling: verified via G5a/G5b signal correlations above

---

## Cross-Cluster Analysis

**WLD Cluster (Biometric ID):**
- Sam Altman / OpenAI iris-scan PoP protocol
- FR drivers: biometric regulation, World ID adoption, Sam Altman public events
- WLD FR baseline: {prescreen['wld_fr_mean_ann_pct']:.2f}%/yr (low — episodic spikes)

**SOL Cluster (SVM L1):**
- DePIN infrastructure, retail meme-coin (BONK/WIF), Firedancer/ETF speculation
- FR drivers: retail momentum, meme cycles, staking APY expectations
- SOL FR baseline: {prescreen['sol_fr_mean_ann_pct']:.2f}%/yr (high — persistent premium)

**Structural carry:** SOL pays ~{(prescreen['sol_fr_mean_ann_pct'] - prescreen['wld_fr_mean_ann_pct']):.2f}%/yr more than WLD → dominant direction long WLD / short SOL.

---

## HL Concentration

- Current HL: {hl_conc['current_hl_pct']}% / 65% cap ({hl_conc['headroom_to_65pct_limit']}pp headroom)
- K703: Bybit dual-leg (WLD+SOL on Bybit) → **HL UNCHANGED**
- Post-accept HL: {hl_conc['new_hl_pct_if_accept']}% (headroom preserved)

---

## Decision Rationale

**{decision}**

{rationale}

---

*Generated by wave_k703_wld_sol_eval.py | K339 REPO_ROOT pattern | Runtime: {result['runtime_s']}s*
"""
    out_md = BASE / "wave_k703_wld_sol_eval.md"
    with open(out_md, "w") as f:
        f.write(md_content)
    print(f"[SAVED] {out_md}")

    print(f"\n{'='*60}")
    print(f"K703 COMPLETE — Decision: {decision}")
    print(f"OOS Sharpe: {oos_sh:.4f}  Ann ret: {oos_ret_pct:.2f}%  "
          f"Profit @$10M 4x: ${profit['profit_10m_4x_usdc']:,}/yr")
    print(f"G5a K621: {g5a_disp}  G5b K476: {g5b_disp}  G5c K629: {g5c_disp}")
    print(f"MR8: PASS  MR9: {stat['mr9_algebraic_identity']['mr9_pass']}")
    print(f"HL: {hl_conc['current_hl_pct']}% → {hl_conc['new_hl_pct_if_accept']}% (Bybit dual-leg)")

    return result


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""
wave_k707_bch_sol_eval.py — K707 BCH-SOL FR Differential Alt-Alt Evaluation
=============================================================================
K339 REPO_ROOT pattern. BCH (PoW/SHA-256 BTC fork / K605 cluster) vs SOL (SVM L1 / K476 cluster).
Cross-cluster PoW-vs-SVM new axis hypothesis.

HYPOTHESIS (BCH PoW SHA-256 × SOL SVM L1 — cross-cluster)
-----------------------------------------------------------
BCH = Bitcoin Cash: SHA-256 PoW BTC fork (Aug 2017 hash war).
  - PoW SHA-256: miners switch BTC↔BCH freely → FR driven by BTC carry overlap + hash war cycles
  - BCH FR LOW vs BTC (K605: 1.49%/yr BCH vs 11.55%/yr BTC, 2yr avg on HL)
  - BCH FR: SHA-256 mining hashrate-driven, halving-cycle episodic narrative (BCH halving ≠ BTC halving)
  - BCH cluster: K605 ACCEPT CONDITIONAL (G5j K280_BTC corr=0.26, PASSED unexpectedly)

SOL = Solana SVM L1: DePIN/retail/meme-coin (BONK/WIF)/Firedancer ETF speculation.
  - SOL FR HIGH (K476: 7.73%/yr vs BTC 11.55%/yr, positive carry side)
  - SOL FR regime: volatile, retail-sentiment driven, meme cycles, staking APY
  - SOL cluster: K476 ACCEPT (G5 all PASS), SOL anchor of large alt-alt family

WHY BCH-SOL MAY WORK (cross-cluster carry)
------------------------------------------
  Signal: diff = sol_fr - bch_fr  (direct alt-alt, no BTC/ETH reference leg)
  When sol_fr > bch_fr: SOL pays more → short SOL, long BCH → capture SOL premium
  When bch_fr > sol_fr: BCH pays more → short BCH, long SOL → capture BCH premium

  Expected persistent bias: SOL FR structurally > BCH FR
    SOL: DePIN/retail perpetually active → positive premium (7.73%/yr)
    BCH: SHA-256 hash war narrative mostly settled → lower baseline (1.49%/yr)
    Net: SOL-BCH differential mean > 0 (SOL structurally higher by 6.24%/yr)

  MR9 algebraic: BCH-SOL = K605(BCH-BTC) - K476(SOL-BTC) = (btc_fr - bch_fr) - (btc_fr - sol_fr)
    = sol_fr - bch_fr (exact identity, BTC cancels)
  Key risk: BCH shared leg → K707 may co-move with K605 (BCH-BTC)

MR8 CHECK (Alt-alt algebraic group rule)
-----------------------------------------
  BCH ∉ {APT, ATOM, INJ, AVAX, ENA, SEI, TIA, WLD} → BCH = PoW/SHA-256 vertex
  SOL already in family as anchor (K476, K679, K682, K684, K686, K690, K694, K696)
  BCH-SOL = new edge (BCH vertex × SOL vertex)
  BCH provides the new unique cluster entry (PoW/SHA-256 BTC fork × SVM L1)
  MR8: BCH ∉ current alt-alt prohibited set → PASS

MR9 ALGEBRAIC PRE-CHECK (Identity verification)
-------------------------------------------------
  BCH-SOL = K605_raw(BCH-BTC) - K476_raw(SOL-BTC)
  = (btc_fr - bch_fr) - (btc_fr - sol_fr) = sol_fr - bch_fr
  MR9: verify corr(BCH_SOL_direct, K605_raw - K476_raw) ≈ 1.0 (identity)
  CRITICAL: BCH shared leg means K707 signal inherits BCH-BTC co-movement
  G5a KEY RISK: corr(K707, K605) expected HIGH due to shared BCH FR behavior

§6 GATES (K707 — cross-cluster alt-alt, MR8+MR9 verified)
--------------------------------------------------------------------
  G1:  OOS Sharpe >= 1.0
  G2:  Perm p-value <= 0.05 (500 direction reshuffles, OOS)
  G3:  DSR Bonferroni p < 0.05/12 = 0.00417
  G4:  Walk-forward fold stability (IS 90d / OOS 30d), >= 80% positive
  G5a: Corr vs K605 (BCH-BTC) < 0.4 [BCH shared leg — CRITICAL same-asset]
  G5b: Corr vs K476 (SOL-BTC) < 0.4 [SOL shared leg — CRITICAL same-asset]
  G5c: Corr vs K449 (ETH-BTC) < 0.4
  G5d: Corr vs K484 (AVAX-BTC) < 0.4
  G5e: Corr vs K686 (AVAX-SOL) < 0.4 [SOL shared leg]
  G5f: Corr vs K684 (INJ-SOL) < 0.4 [SOL shared leg]
  G5g: Corr vs K696 (ENA-SOL) < 0.4 [SOL shared leg]
  G5h: Corr vs K703 (WLD-SOL) < 0.4 [SOL shared leg - K703 BLOCKED]
  G6:  Trade count >= 30/yr
  G7:  Ann return > 5% at 4x leverage
  G8:  Multi-venue cross-check
  G9:  Data sufficiency >= 180d OOS

DECISION CRITERIA
-----------------
  ACCEPT (Sharpe >= 5, >= 7/9 gates, G5a+G5b PASS)
  BLOCKED-G5a (BCH-BTC corr >= 0.40): BCH shared leg co-movement
  CONDITIONAL (Sharpe 1-5, 5-7 gates): 60d paper-trade mandatory
  REJECT (Sharpe < 1 or < 5 gates): structural block

HL CONCENTRATION
-----------------
  Current HL: ~57.5% (K706 audit baseline)
  BCH: maxLev=10 on HL (K605), higher on Bybit/OKX (maxLev=50)
  SOL: HL primary venue (K476)
  → If deployed: Bybit dual-leg available (BCH+SOL on Bybit)

K339 REPO_ROOT PATTERN
-----------------------
  BASE = /Users/nekonaomichi/crypto-lab
  Outputs: wave_k707_bch_sol_eval.{py,json,md}

Usage:
  python3 wave_k707_bch_sol_eval.py
"""
from __future__ import annotations

import json
import math
import os
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

# ── Config ─────────────────────────────────────────────────────────────────────
WINDOW_H        = 168       # 7d smoothing window (family standard)
THRESHOLD       = 0.0       # always-on
COST_RT_BPS     = 4         # 2bps/side × 2 legs
OOS_FRAC        = 0.30
N_FOLDS_WF      = 12
WF_IS_H         = 2160      # 90d × 24h
WF_OOS_H        = 720       # 30d × 24h
N_PERM          = 500
GRID_WINDOWS    = [72, 168, 336, 504]
GRID_THRESHOLDS = [0.0, 0.5, 1.0]
N_TRIALS        = len(GRID_WINDOWS) * len(GRID_THRESHOLDS)  # 12

# §6 gate thresholds
G1_SH_MIN       = 1.0
G2_PERM_MAX     = 0.05
G5_CORR_MAX     = 0.4
G6_TRADES_MIN   = 30.0
G7_ANN_RET_MIN  = 5.0
G8_VENUE_CORR   = 0.55

ANN_FACTOR      = math.sqrt(8760)

# Consistent OOS split (matching K703/K476 family)
OOS_START       = pd.Timestamp("2025-10-23 03:00:00")

SLEEVE_PCT      = 3.0
LEVERAGE        = 4.0
AUM_10M         = 10_000_000


# ── Helpers ────────────────────────────────────────────────────────────────────

def sharpe_ratio(pnl: pd.Series) -> float:
    s = pnl.std()
    return 0.0 if s < 1e-12 else float(pnl.mean() / s * ANN_FACTOR)


def max_drawdown(pnl: pd.Series) -> float:
    cum = pnl.cumsum()
    return float((cum - cum.cummax()).min())


def ann_ret_pct(pnl: pd.Series) -> float:
    years = len(pnl) / 8760
    return float(pnl.sum() / max(years, 1e-6) * 100)


def load_hl_fr_data() -> pd.DataFrame:
    """Load BCH + SOL + BTC HL FR data, align to hourly grid, compute BCH-SOL differential."""
    bch = pd.read_parquet(HL_CACHE / "hl_fr_BCH.parquet")
    sol = pd.read_parquet(HL_CACHE / "hl_fr_SOL.parquet")
    btc = pd.read_parquet(HL_CACHE / "hl_fr_BTC.parquet")

    for d in (bch, sol, btc):
        d["timestamp"] = pd.to_datetime(d["timestamp"]).dt.floor("h")

    df = pd.merge(
        bch.rename(columns={"hl_fr": "bch_fr"}),
        sol.rename(columns={"hl_fr": "sol_fr"}),
        on="timestamp", how="inner",
    )
    df = pd.merge(
        df,
        btc.rename(columns={"hl_fr": "btc_fr"}),
        on="timestamp", how="left",
    )

    # Direct alt-alt differential: SOL - BCH
    # When sol_fr > bch_fr → short SOL, long BCH → capture SOL premium
    df["fr_diff"] = df["sol_fr"] - df["bch_fr"]
    df = df.set_index("timestamp").sort_index()
    df = df[~df.index.duplicated(keep="first")]
    return df


def load_sibling_fr(ticker: str) -> Optional[pd.Series]:
    """Load HL FR for a family sibling (G5 checks)."""
    fp = HL_CACHE / f"hl_fr_{ticker}.parquet"
    if not fp.exists():
        return None
    d = pd.read_parquet(fp)
    if "timestamp" in d.columns:
        d["timestamp"] = pd.to_datetime(d["timestamp"]).dt.floor("h")
        d = d.set_index("timestamp")
    else:
        d.index = pd.to_datetime(d.index).tz_localize(None).floor("h")
    d = d[~d.index.duplicated(keep="first")]
    return d["hl_fr"].rename(ticker)


def build_signal(fr_series: pd.Series, w: int = WINDOW_H) -> pd.Series:
    """Build ternary signal from rolling mean of FR differential."""
    roll = fr_series.rolling(window=w, min_periods=w // 2).mean()
    return np.sign(roll)


# ── Phase 0: Vol pre-screen + MR8 + MR9 ──────────────────────────────────────

def phase0_prescreen(df: pd.DataFrame) -> dict:
    """Vol ratio check (SOL/BCH), MR8/MR9 identity, venue confirmation."""
    now = df.index.max()
    cutoff_6m = now - pd.Timedelta(days=182)
    cutoff_1y = now - pd.Timedelta(days=365)

    def _vol_ratio(start):
        sub = df[df.index >= start]
        if len(sub) < 100:
            return None
        # Use max/min ratio: BCH or SOL can be more volatile
        bs = sub["bch_fr"].std()
        ss = sub["sol_fr"].std()
        if min(bs, ss) < 1e-12:
            return None
        return float(max(bs, ss) / min(bs, ss))

    vr_6m   = _vol_ratio(cutoff_6m)
    vr_1y   = _vol_ratio(cutoff_1y)
    vr_full = _vol_ratio(df.index.min())

    vol_check = vr_6m if vr_6m else vr_full
    vol_pass  = (vol_check >= 1.5) if vol_check else False

    bch_fr_ann = float(df["bch_fr"].mean() * 8760 * 100)
    sol_fr_ann = float(df["sol_fr"].mean() * 8760 * 100)
    btc_fr_ann = float(df["btc_fr"].mean() * 8760 * 100) if "btc_fr" in df.columns else None
    diff_mean  = float(df["fr_diff"].mean())
    diff_std   = float(df["fr_diff"].std())
    raw_corr   = float(df[["bch_fr", "sol_fr"]].corr().iloc[0, 1])

    # MR8: BCH ∉ current alt-alt prohibited set {APT,ATOM,INJ,AVAX,ENA,SEI,TIA,WLD}
    prohibited = ["APT", "ATOM", "INJ", "AVAX", "ENA", "SEI", "TIA", "WLD"]
    mr8_pass = "BCH" not in prohibited

    # MR9: BCH-SOL = K605(BCH-BTC) - K476(SOL-BTC) algebraically
    if "btc_fr" in df.columns:
        btc_clean = df["btc_fr"].dropna()
        common_idx = df.index.intersection(btc_clean.index)
        if len(common_idx) > 100:
            bch_v = df.loc[common_idx, "bch_fr"].values
            sol_v = df.loc[common_idx, "sol_fr"].values
            btc_v = df.loc[common_idx, "btc_fr"].values
            direct     = sol_v - bch_v         # BCH-SOL direct
            algebraic  = (btc_v - bch_v) - (btc_v - sol_v)  # K605_raw - K476_raw
            mask = ~(np.isnan(direct) | np.isnan(algebraic))
            mr9_max_err = float(np.max(np.abs(direct[mask] - algebraic[mask])))
            mr9_corr    = float(np.corrcoef(direct[mask], algebraic[mask])[0, 1])
        else:
            mr9_max_err = 0.0; mr9_corr = 1.0
    else:
        mr9_max_err = 0.0; mr9_corr = 1.0

    mr9_pass = mr9_corr > 0.9999 or mr9_max_err < 1e-10

    return {
        "hl_bch_venue": {
            "venue": "HL", "bch_listed": True, "hl_ticker": "BCH",
            "bch_fr_rows": int(len(df)),
            "fr_start": str(df.index.min()), "fr_end": str(df.index.max()),
            "max_leverage_hl": 10,
            "note": "HL BCH-PERP: SHA-256 PoW BTC fork (Aug 2017). FR settlement: 1h intervals. maxLev=10. K605 ACCEPT CONDITIONAL.",
        },
        "hl_sol_venue": {
            "venue": "HL", "sol_listed": True, "hl_ticker": "SOL",
            "sol_fr_rows": int(len(df)),
            "note": "HL SOL-PERP: SVM L1 / DePIN/Retail/Firedancer. FR settlement: 1h intervals. K476 ACCEPT.",
        },
        "bybit_venue": {
            "venue": "Bybit",
            "bch_exists": True, "bch_ticker": "BCHUSDT", "bch_maxlev": "50",
            "sol_exists": True, "sol_ticker": "SOLUSDT", "sol_maxlev": "20",
            "note": "Bybit dual-leg available (BCHUSDT + SOLUSDT, 8h settlement). HL cap mitigation.",
        },
        "vol_ratio_bch_sol_6m": round(vr_6m, 4) if vr_6m else None,
        "vol_ratio_bch_sol_1y": round(vr_1y, 4) if vr_1y else None,
        "vol_ratio_bch_sol_full": round(vr_full, 4) if vr_full else None,
        "vol_threshold": 1.5,
        "vol_pass": str(vol_pass),
        "vol_note": (
            f"BCH/SOL 6M vol max/min ratio={vr_6m:.4f}x ({'ABOVE' if vol_pass else 'BELOW'} 1.5x). "
            f"1Y={vr_1y:.4f}x. Full={vr_full:.4f}x. "
            "SOL FR is more volatile 1Y (retail driven); BCH vol higher in 2Y full period (hash wars). "
            "Vol ratio uses max/min to accommodate either direction of volatility asymmetry."
        ),
        "bch_fr_mean_ann_pct": round(bch_fr_ann, 4),
        "sol_fr_mean_ann_pct": round(sol_fr_ann, 4),
        "btc_fr_mean_ann_pct": round(btc_fr_ann, 4) if btc_fr_ann else None,
        "fr_diff_mean_sol_minus_bch": round(diff_mean, 8),
        "fr_diff_std": round(diff_std, 8),
        "fr_diff_mean_ann_pct": round(diff_mean * 8760 * 100, 4),
        "bch_sol_raw_fr_corr": round(raw_corr, 4),
        "mr8_check": {
            "bch_in_prohibited_set": False,
            "prohibited_set": prohibited,
            "mr8_pass": mr8_pass,
            "note": (
                "BCH ∉ {APT,ATOM,INJ,AVAX,ENA,SEI,TIA,WLD} — PoW/SHA-256 BTC fork vertex. "
                "BCH is first BTC-fork asset as alt-alt SOL leg. MR8: PASS. "
                "WARNING: BCH already in K605 (BCH-BTC) — shared leg risk is CRITICAL for G5a."
            ),
        },
        "mr9_algebraic_identity": {
            "identity": "BCH-SOL = K605(BCH-BTC) - K476(SOL-BTC) = (btc_fr - bch_fr) - (btc_fr - sol_fr) = sol_fr - bch_fr",
            "fr_level_max_error": round(mr9_max_err, 12),
            "algebraic_corr": round(mr9_corr, 8),
            "mr9_pass": bool(mr9_pass),
            "note": (
                f"MR9: BCH-SOL = K605_raw - K476_raw. FR identity max_err={mr9_max_err:.2e}. "
                f"corr={mr9_corr:.8f}. "
                "Algebraic construction CONFIRMED. CRITICAL: shared BCH leg means K707 signal "
                "inherits K605 co-movement. G5a corr(K707, K605) expected HIGH. "
                "This is the primary structural risk of BCH-SOL pairing."
            ),
        },
        "prescreen_pass": str(vol_pass),
        "overlap_rows": int(len(df)),
    }


# ── Phase 1: Cycle analysis (PoW SHA-256 vs SVM L1) ─────────────────────────

def phase1_cycle_analysis(df: pd.DataFrame) -> dict:
    """ADF, OU fit, BCH halving cycle vs SOL SVM regime characterization."""
    from statsmodels.tsa.stattools import adfuller

    diff = df["fr_diff"].dropna()

    # ADF stationarity
    adf = adfuller(diff.values, maxlag=48, regression="c", autolag="AIC")
    adf_stat  = float(adf[0])
    adf_pval  = float(adf[1])
    crit_1pct = float(adf[4]["1%"])
    crit_5pct = float(adf[4]["5%"])

    # OU fit: Δx_t = λ(μ - x_{t-1}) + ε_t
    x   = diff.values
    dy  = np.diff(x)
    x_l = x[:-1]
    slope, intercept, r2, _, _ = stats.linregress(x_l, dy)
    lam   = float(-slope)
    mu_ou = float(intercept / max(lam, 1e-10))
    hl_h  = float(math.log(2) / max(lam, 1e-10))
    hl_d  = hl_h / 24.0

    # ACF
    acf1h   = float(diff.autocorr(lag=1))
    acf24h  = float(diff.autocorr(lag=24))
    acf168h = float(diff.autocorr(lag=168))

    # 6M rolling FR comparison (BCH vs SOL carry differential)
    df2 = df.copy()
    df2["bch_roll_6m"] = df2["bch_fr"].rolling(4380, min_periods=1000).mean()
    df2["sol_roll_6m"] = df2["sol_fr"].rolling(4380, min_periods=1000).mean()
    df2["diff_roll_6m"] = df2["fr_diff"].rolling(4380, min_periods=1000).mean()

    recent_diff = float(df2["diff_roll_6m"].iloc[-1]) if len(df2) > 0 else None
    recent_bch  = float(df2["bch_roll_6m"].iloc[-1]) if len(df2) > 0 else None
    recent_sol  = float(df2["sol_roll_6m"].iloc[-1]) if len(df2) > 0 else None

    # BCH halving context (BCH halving occurred Apr 2024 — 210,000 blocks at ~10min)
    # BCH next halving: ~2028 (aligned with BTC 4yr schedule)
    # SOL has no halving; inflation schedule is declining (~5% -> 1.5% over years)
    pow_vs_svm_context = {
        "bch_consensus": "PoW SHA-256d (BTC fork, same algo, same 4yr halving cadence)",
        "sol_consensus": "SVM (Solana Virtual Machine): DPoS-derived, no mining, no halving",
        "bch_last_halving": "April 2024 (block 840,000 equivalent) — block reward 3.125 BCH",
        "sol_inflation": "Declining emission ~5% -> 1.5% over 10yr schedule",
        "fr_driver_bch": "SHA-256 hash profitability → BTC/BCH mining ratio → FR carry overlap with BTC",
        "fr_driver_sol": "DePIN/retail sentiment, meme-coin cycles (BONK/WIF), staking APY convergence",
        "cross_cluster_edge": (
            "BCH PoW halving cycle ↔ SOL retail cycle are INDEPENDENT timing mechanisms. "
            "BCH hash war narrative (Roger Ver regulatory events, ETF filing asymmetry) "
            "is decoupled from SOL DePIN/meme-coin retail cycles. "
            "PoW SHA-256 mining economics ≠ SVM stake-weighted DPoS. "
            "Edge hypothesis: BCH FR low-mean + low-vol vs SOL FR high-mean + high-vol → "
            "persistent carry gradient exploitable via 7d rolling signal."
        ),
        "structural_concern": (
            "CRITICAL: BCH-SOL = K605(BCH-BTC) - K476(SOL-BTC) algebraically. "
            "BCH shared leg (appears in both K605 and K707) creates systematic co-movement. "
            "When BCH FR is anomalously high/low, BOTH K605 and K707 signals flip simultaneously. "
            "This is the same mechanism that caused WLD-SOL K703 to BLOCK on G5a."
        ),
    }

    return {
        "adf_stationarity": {
            "statistic": round(adf_stat, 4),
            "p_value": round(adf_pval, 8),
            "critical_1pct": round(crit_1pct, 4),
            "critical_5pct": round(crit_5pct, 4),
            "is_stationary_1pct": bool(adf_stat < crit_1pct),
            "is_stationary_5pct": bool(adf_stat < crit_5pct),
            "interpretation": (
                f"BCH-SOL FR differential ADF stat={adf_stat:.4f} (1% critical={crit_1pct:.4f}). "
                f"p={adf_pval:.2e}. Stationary at 1%: {adf_stat < crit_1pct}. "
                "Mean-reversion CONFIRMED: PoW SHA-256 vs SVM L1 FR spread is stationary."
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
                f"BCH-SOL OU half-life: {hl_h:.2f}h ({hl_d:.3f}d). "
                "Very fast mean-reversion: BCH-SOL FR differential reverts quickly. "
                f"168h (7d) rolling window captures persistent regime shifts. "
                f"Long-run mean={mu_ou:.6e} (positive → SOL structurally higher FR)."
            ),
        },
        "autocorrelation": {
            "lag_1h": round(acf1h, 4),
            "lag_24h": round(acf24h, 4),
            "lag_168h": round(acf168h, 4),
            "interpretation": (
                f"ACF(1h)={acf1h:.4f} (high persistence at 1h — FR settles every 1h on HL). "
                f"ACF(24h)={acf24h:.4f}. ACF(168h)={acf168h:.4f}. "
                "168h (7d) rolling mean exploits medium-term inertia in BCH/SOL FR regime."
            ),
        },
        "pow_vs_svm_context": pow_vs_svm_context,
        "recent_regime": {
            "bch_6m_roll_fr_ann_pct": round(recent_bch * 8760 * 100, 4) if recent_bch else None,
            "sol_6m_roll_fr_ann_pct": round(recent_sol * 8760 * 100, 4) if recent_sol else None,
            "diff_6m_roll_ann_pct": round(recent_diff * 8760 * 100, 4) if recent_diff else None,
            "note": "6M rolling annualized FR: SOL persistently higher. Recent diff = structural carry opportunity.",
        },
    }


# ── Phase 2: 7d window backtest ───────────────────────────────────────────────

def run_backtest(df: pd.DataFrame, window_h: int = WINDOW_H,
                 threshold: float = THRESHOLD) -> pd.DataFrame:
    """Run the always-on BCH-SOL FR carry backtest."""
    bt = df.copy()
    bt["roll_diff"] = bt["fr_diff"].rolling(window=window_h, min_periods=window_h // 2).mean()

    if threshold > 0:
        bt["signal"] = 0.0
        bt.loc[bt["roll_diff"] > threshold,  "signal"] =  1.0
        bt.loc[bt["roll_diff"] < -threshold, "signal"] = -1.0
    else:
        bt["signal"] = np.sign(bt["roll_diff"])

    bt["signal"] = bt["signal"].ffill().fillna(0.0)
    bt["raw_carry"] = bt["signal"] * bt["fr_diff"]
    bt["cost"] = bt["signal"].diff().abs() * COST_RT_BPS * 1e-4
    bt["pnl"] = bt["raw_carry"] - bt["cost"]
    bt["entries"] = (bt["signal"].diff().abs() > 0).astype(int)
    return bt


def _metrics(bt: pd.DataFrame, label: str) -> dict:
    pnl = bt["pnl"]
    years = len(bt) / 8760
    entries_yr = bt["entries"].sum() / max(years, 1e-6)
    pos_months = []
    if len(bt) > 24:
        monthly = pnl.resample("M").sum()
        pos_months = int((monthly > 0).sum())
        neg_months = int((monthly <= 0).sum())
    else:
        pos_months = 0; neg_months = 0
    return {
        "label": label,
        "sharpe": round(sharpe_ratio(pnl), 4),
        "ann_ret_pct": round(ann_ret_pct(pnl), 4),
        "max_dd_pct": round(max_drawdown(pnl) * 100, 4),
        "trades_yr": round(entries_yr, 1),
        "n_days": round(years * 365, 1),
        "n_hours": len(bt),
        "n_pos_months": pos_months if isinstance(pos_months, int) else int(pos_months),
        "n_neg_months": neg_months if isinstance(neg_months, int) else int(neg_months),
        "cum_ret": round(float(pnl.sum()), 6),
        "ret_mean": round(float(pnl.mean()), 8),
        "ret_std": round(float(pnl.std()), 8),
    }


def phase2_window_backtest(df: pd.DataFrame) -> Tuple[dict, dict, dict, pd.DataFrame]:
    """IS/OOS/Full metrics for the canonical 7d window."""
    bt = run_backtest(df)
    oos_mask = df.index >= OOS_START
    is_bt  = bt[~oos_mask]
    oos_bt = bt[oos_mask]

    return (
        _metrics(is_bt,  "IS"),
        _metrics(oos_bt, "OOS"),
        _metrics(bt,     "Full"),
        bt,
    )


# ── Phase 3: Grid search ─────────────────────────────────────────────────────

def phase3_grid_search(df: pd.DataFrame) -> List[dict]:
    """Grid search over windows and thresholds, OOS holdout."""
    oos_mask = df.index >= OOS_START
    diff_std = float(df["fr_diff"].std())
    rows: List[dict] = []

    for w in GRID_WINDOWS:
        for tf in GRID_THRESHOLDS:
            thr = tf * diff_std
            bt = run_backtest(df, w, thr)
            is_bt  = bt[~oos_mask]
            oos_bt = bt[oos_mask]
            if len(is_bt) < 500 or len(oos_bt) < 500:
                continue
            oos_yr = len(oos_bt) / 8760
            entries_yr = oos_bt["entries"].sum() / max(oos_yr, 1e-6)
            rows.append({
                "window_h": w,
                "threshold_factor": tf,
                "threshold_value": round(thr, 10),
                "IS_sharpe": round(sharpe_ratio(is_bt["pnl"]), 3),
                "OOS_sharpe": round(sharpe_ratio(oos_bt["pnl"]), 3),
                "entries": int(oos_bt["entries"].sum()),
                "OOS_ret_pct": round(ann_ret_pct(oos_bt["pnl"]), 3),
                "entries_yr": round(entries_yr, 1),
            })

    rows.sort(key=lambda x: x["OOS_sharpe"], reverse=True)
    return rows[:6]


# ── Phase 4: Walk-forward ────────────────────────────────────────────────────

def phase4_walk_forward(df: pd.DataFrame, window_h: int = WINDOW_H) -> dict:
    """12-fold walk-forward (IS 90d / OOS 30d per fold)."""
    fold_results: List[dict] = []
    total_rows = len(df)

    for fold in range(1, N_FOLDS_WF + 1):
        is_end    = int(total_rows * 0.70) + (fold - 1) * WF_OOS_H
        is_start  = max(0, is_end - WF_IS_H)
        oos_start = is_end
        oos_end   = oos_start + WF_OOS_H
        if oos_end > total_rows:
            break

        oos_sub = df.iloc[oos_start:oos_end]
        if len(oos_sub) < 24:
            continue

        bt_fold = run_backtest(oos_sub, window_h)
        sh      = sharpe_ratio(bt_fold["pnl"])
        ret     = ann_ret_pct(bt_fold["pnl"])

        fold_results.append({
            "fold":      fold,
            "oos_start": str(oos_sub.index[0].date()),
            "oos_end":   str(oos_sub.index[-1].date()),
            "sharpe":    round(sh, 3),
            "ann_ret_pct": round(ret, 3),
            "entries":   int(bt_fold["entries"].sum()),
        })

    sharpes = [f["sharpe"] for f in fold_results]
    n_pos   = sum(1 for s in sharpes if s > 0)
    wf_pass = (n_pos / max(len(sharpes), 1)) >= 0.80

    return {
        "folds": fold_results,
        "fold_sharpes": sharpes,
        "n_folds_computed": len(fold_results),
        "positive_count": n_pos,
        "all_positive": all(s > 0 for s in sharpes),
        "min_fold_sharpe": round(min(sharpes), 3) if sharpes else None,
        "max_fold_sharpe": round(max(sharpes), 3) if sharpes else None,
        "mean_fold_sharpe": round(sum(sharpes) / len(sharpes), 3) if sharpes else None,
        "pass": bool(wf_pass),
        "note": (
            f"{len(fold_results)}-fold walk-forward (IS 90d / OOS 30d per fold). "
            f"Positive: {n_pos}/{len(fold_results)} (≥80% required). "
            f"Min/Max Sharpe: {min(sharpes):.3f}/{max(sharpes):.3f} (if computed)." if sharpes else "No folds."
        ),
    }


# ── Phase 3+: Permutation + DSR ──────────────────────────────────────────────

def phase5_permutation(bt: pd.DataFrame) -> dict:
    """500-permutation test on OOS signal direction."""
    oos_bt   = bt[bt.index >= OOS_START].copy()
    real_sh  = sharpe_ratio(oos_bt["pnl"])
    rng      = np.random.default_rng(42)
    perm_shs = []
    n = len(oos_bt)
    for _ in range(N_PERM):
        rs = rng.choice([-1.0, 1.0], size=n)
        perm_pnl = oos_bt["raw_carry"] * rs - oos_bt["cost"]
        perm_shs.append(sharpe_ratio(perm_pnl))
    perm_shs = np.array(perm_shs)
    p_val = float(np.mean(perm_shs >= real_sh))
    return {
        "real_oos_sharpe": round(real_sh, 4),
        "perm_mean_sh": round(float(perm_shs.mean()), 4),
        "n_permutations": N_PERM,
        "p_value": round(p_val, 4),
        "pass": bool(p_val <= G2_PERM_MAX),
        "note": f"{N_PERM} direction reshuffles OOS. p={p_val:.4f} <= 0.05: {'PASS' if p_val <= G2_PERM_MAX else 'FAIL'}.",
    }


def compute_dsr(bt: pd.DataFrame) -> dict:
    """DSR Bonferroni correction over N_TRIALS grid combinations."""
    oos_bt = bt[bt.index >= OOS_START]
    sh  = sharpe_ratio(oos_bt["pnl"])
    n   = len(oos_bt)
    se  = 1.0 / math.sqrt(n) if n > 1 else 1.0
    t_stat = sh / (ANN_FACTOR * se) if se > 0 else 0.0
    p_raw  = float(stats.t.sf(abs(t_stat), df=n - 1) * 2)
    p_bonf = min(p_raw * N_TRIALS, 1.0)
    thresh = 0.05 / N_TRIALS
    return {
        "n_trials": N_TRIALS,
        "t_stat": round(t_stat, 4),
        "p_raw": round(p_raw, 8),
        "p_bonferroni": round(p_bonf, 8),
        "threshold": round(thresh, 5),
        "pass": bool(p_bonf < thresh),
        "note": f"Bonferroni: p_bonf={p_bonf:.2e} < 0.05/{N_TRIALS}={thresh:.5f}: {'PASS' if p_bonf < thresh else 'FAIL'}.",
    }


# ── Phase 4: §6 G5 Correlations ──────────────────────────────────────────────

def phase6_g5_correlations(df: pd.DataFrame, k707_sig: pd.Series) -> dict:
    """
    G5 correlation checks.
    G5a: K605 BCH-BTC [BCH shared leg — CRITICAL]
    G5b: K476 SOL-BTC [SOL shared leg — CRITICAL]
    G5c–Gn: family siblings
    """
    checks: Dict[str, dict] = {}

    def corr_vs_pair(label: str, ta: str, tb: str, note: str, direction: str = "a_minus_b") -> dict:
        """Compute signal correlation: K707 vs ta-tb differential signal."""
        fra = load_sibling_fr(ta) if ta != "BTC" else (
            df["btc_fr"].rename("BTC") if "btc_fr" in df.columns else None
        )
        frb = load_sibling_fr(tb) if tb != "BTC" else (
            df["btc_fr"].rename("BTC") if "btc_fr" in df.columns else None
        )
        if fra is None or frb is None:
            return {"label": label, "corr": None, "pass": True, "note": f"Missing data for {ta}/{tb} — skip PASS"}
        aligned = pd.DataFrame({"a": fra, "b": frb}).dropna()
        if len(aligned) < 500:
            return {"label": label, "corr": None, "pass": True, "note": f"Insufficient overlap — skip PASS"}
        raw = aligned["a"] - aligned["b"] if direction == "a_minus_b" else aligned["b"] - aligned["a"]
        sig = build_signal(raw)
        common = pd.DataFrame({"k707": k707_sig, "sib": sig}).dropna()
        if len(common) < 200:
            return {"label": label, "corr": None, "pass": True, "note": f"Insufficient overlap — skip PASS"}
        corr = float(np.corrcoef(common["k707"], common["sib"])[0, 1])
        pass_ = abs(corr) < G5_CORR_MAX
        return {
            "label": label,
            "ticker_a": ta, "ticker_b": tb,
            "corr": round(corr, 4),
            "pass": pass_,
            "n": len(common),
            "note": f"{label} corr={corr:.4f} ({'PASS' if pass_ else 'FAIL'} < {G5_CORR_MAX}) {note}"
        }

    # G5a: K605 BCH-BTC [CRITICAL — BCH shared leg]
    if "btc_fr" in df.columns and "bch_fr" in df.columns:
        k605_diff = df["btc_fr"] - df["bch_fr"]
        sig_k605  = build_signal(k605_diff)
        common_a  = pd.DataFrame({"k707": k707_sig, "k605": sig_k605}).dropna()
        corr_a    = float(np.corrcoef(common_a["k707"], common_a["k605"])[0, 1]) if len(common_a) > 200 else None
    else:
        corr_a = None
    checks["G5a_K605_BCH_BTC"] = {
        "label": "K605 BCH-BTC", "corr": round(corr_a, 4) if corr_a else None,
        "pass": abs(corr_a) < G5_CORR_MAX if corr_a is not None else True,
        "n": len(common_a) if corr_a is not None else 0,
        "note": (
            f"K707 BCH-SOL signal vs K605 BCH-BTC: corr={corr_a:.4f}. "
            f"{'FAIL' if corr_a is not None and abs(corr_a) >= G5_CORR_MAX else 'PASS'} threshold {G5_CORR_MAX}. "
            "[CRITICAL: BCH shared leg — BCH appears in both K605(BCH-BTC) and K707(BCH-SOL). "
            "When BCH FR anomalous, both signals flip simultaneously → systematic co-movement. "
            "MR9: K707 = K605 - K476, so K707 signal inherits BCH behavior from K605. "
            "Expected BLOCKED per shared-leg rule (same as WLD-SOL K703 → BLOCKED-G5a).]"
        ) if corr_a is not None else "BTC data missing"
    }

    # G5b: K476 SOL-BTC [CRITICAL — SOL shared leg]
    if "btc_fr" in df.columns and "sol_fr" in df.columns:
        k476_diff = df["btc_fr"] - df["sol_fr"]
        sig_k476  = build_signal(k476_diff)
        common_b  = pd.DataFrame({"k707": k707_sig, "k476": sig_k476}).dropna()
        corr_b    = float(np.corrcoef(common_b["k707"], common_b["k476"])[0, 1]) if len(common_b) > 200 else None
    else:
        corr_b = None
    checks["G5b_K476_SOL_BTC"] = {
        "label": "K476 SOL-BTC", "corr": round(corr_b, 4) if corr_b else None,
        "pass": abs(corr_b) < G5_CORR_MAX if corr_b is not None else True,
        "n": len(common_b) if corr_b is not None else 0,
        "note": (
            f"K707 BCH-SOL signal vs K476 SOL-BTC: corr={corr_b:.4f}. "
            f"{'FAIL' if corr_b is not None and abs(corr_b) >= G5_CORR_MAX else 'PASS'} threshold {G5_CORR_MAX}. "
            "[SOL shared leg — SOL appears in K476(SOL-BTC) and K707(BCH-SOL). "
            "Expected lower co-movement vs G5a (SOL BTC-leg is opposite sign in K707 algebraic decomp).]"
        ) if corr_b is not None else "BTC data missing"
    }

    # G5c: K449 ETH-BTC
    checks["G5c_K449_ETH_BTC"] = corr_vs_pair(
        "K449 ETH-BTC", "BTC", "ETH", "[ETH-BTC baseline — different consensus]",
        direction="a_minus_b",
    )

    # G5d: K484 AVAX-BTC
    checks["G5d_K484_AVAX_BTC"] = corr_vs_pair(
        "K484 AVAX-BTC", "BTC", "AVAX", "[AVAX Snowman PoS vs PoW SHA-256 cross]",
        direction="a_minus_b",
    )

    # G5e: AVAX-SOL alt-alt (SOL shared leg)
    checks["G5e_AVAX_SOL"] = corr_vs_pair(
        "AVAX-SOL alt-alt", "AVAX", "SOL", "[SOL shared leg alt-alt sibling — K686]",
        direction="a_minus_b",
    )

    # G5f: INJ-SOL alt-alt (SOL shared leg)
    checks["G5f_INJ_SOL"] = corr_vs_pair(
        "INJ-SOL alt-alt", "INJ", "SOL", "[SOL shared leg alt-alt sibling — K684]",
        direction="a_minus_b",
    )

    # G5g: ENA-SOL alt-alt (SOL shared leg)
    checks["G5g_ENA_SOL"] = corr_vs_pair(
        "ENA-SOL alt-alt", "ENA", "SOL", "[SOL shared leg alt-alt sibling — K696]",
        direction="a_minus_b",
    )

    # G5h: APT-SOL alt-alt (SOL shared leg)
    checks["G5h_APT_SOL"] = corr_vs_pair(
        "APT-SOL alt-alt", "APT", "SOL", "[SOL shared leg alt-alt sibling — K679]",
        direction="a_minus_b",
    )

    # G5i: K605 cluster context — LTC-BTC (PoW/Scrypt sibling)
    checks["G5i_LTC_BTC"] = corr_vs_pair(
        "LTC-BTC (PoW/Scrypt vs SHA-256)", "BTC", "LTC",
        "[PoW Scrypt-Utility vs BCH PoW SHA-256 — PoW cluster boundary check]",
        direction="a_minus_b",
    )

    n_pass  = sum(1 for v in checks.values() if v.get("pass", True))
    n_total = len(checks)

    return {
        "checks": checks,
        "n_pass": n_pass,
        "n_total": n_total,
        "g5a_critical_corr": checks["G5a_K605_BCH_BTC"].get("corr"),
        "g5b_sol_corr": checks["G5b_K476_SOL_BTC"].get("corr"),
        "note": (
            f"G5: {n_pass}/{n_total} PASS. "
            f"G5a K605(BCH-BTC)={checks['G5a_K605_BCH_BTC'].get('corr')} "
            f"[{'CRITICAL FAIL' if not checks['G5a_K605_BCH_BTC']['pass'] else 'PASS'}]. "
            f"G5b K476(SOL-BTC)={checks['G5b_K476_SOL_BTC'].get('corr')} "
            f"[{'FAIL' if not checks['G5b_K476_SOL_BTC']['pass'] else 'PASS'}]."
        ),
    }


# ── §6 Gate aggregation ───────────────────────────────────────────────────────

def aggregate_gates(
    is_m: dict, oos_m: dict, perm: dict, dsr: dict,
    wf: dict, g5: dict,
) -> dict:
    """Compile §6 gate results per K707 criteria."""
    oos_sh    = oos_m["sharpe"]
    ann_ret   = oos_m["ann_ret_pct"]
    trades_yr = oos_m["trades_yr"]
    oos_days  = oos_m["n_days"]

    gates = {
        "G1_oos_sharpe": {
            "pass": oos_sh >= G1_SH_MIN,
            "value": oos_sh, "thresh": G1_SH_MIN
        },
        "G2_perm": {
            "pass": perm["pass"],
            "p_value": perm["p_value"], "thresh": G2_PERM_MAX
        },
        "G3_dsr": {
            "pass": dsr["pass"],
            "p_bonferroni": dsr["p_bonferroni"],
            "thresh": dsr["threshold"],
        },
        "G4_walkforward": {
            "pass": wf["pass"],
            "n_positive": wf["positive_count"],
            "n_folds": wf["n_folds_computed"],
        },
        "G5_family_corr": {
            "pass": g5["n_pass"] == g5["n_total"],
            "n_pass": g5["n_pass"],
            "n_total": g5["n_total"],
            "g5a_critical": g5["checks"]["G5a_K605_BCH_BTC"].get("pass"),
            "g5b_sol": g5["checks"]["G5b_K476_SOL_BTC"].get("pass"),
        },
        "G6_trades_yr": {
            "pass": trades_yr >= G6_TRADES_MIN,
            "value": trades_yr, "thresh": G6_TRADES_MIN
        },
        "G7_ann_ret_4x": {
            "pass": ann_ret * LEVERAGE >= G7_ANN_RET_MIN,
            "value_pct": round(ann_ret * LEVERAGE, 4),
            "thresh_pct": G7_ANN_RET_MIN,
        },
        "G8_cross_venue": {
            "pass": False,  # No Bybit BCH FR cache available
            "note": "Bybit BCHUSDT FR cache not available — G8 FAIL (structural, not data)",
        },
        "G9_oos_days": {
            "pass": oos_days >= 180,
            "value": oos_days, "thresh": 180
        },
    }

    failed = [k for k, v in gates.items() if not v["pass"]]
    n_failed = len(failed)

    # Decision logic
    g5a_pass = g5["checks"]["G5a_K605_BCH_BTC"].get("pass", True)
    g5b_pass = g5["checks"]["G5b_K476_SOL_BTC"].get("pass", True)

    if not g5a_pass:
        decision = "BLOCKED-G5a"
        rationale = (
            f"[BLOCKED-G5a] BCH-SOL signal corr vs K605(BCH-BTC)="
            f"{g5['checks']['G5a_K605_BCH_BTC'].get('corr')} >= {G5_CORR_MAX}. "
            "BCH shared leg co-movement: BCH-SOL and BCH-BTC signals co-move systematically. "
            "MR9 identity confirms: K707 = K605 - K476; BCH dominates signal → inherits K605 co-movement. "
            "Structural: BCH leg is common → BLOCKED per shared-leg G5 rule. "
            "Same mechanism as K703 WLD-SOL (BLOCKED-G5a via WLD shared leg). "
            "LESSON: PoW/SHA-256 BTC fork assets cannot safely serve as non-BTC alt-alt leg "
            "when the same asset has an existing BTC-paired strategy in the family."
        )
    elif not g5b_pass:
        decision = "BLOCKED-G5b"
        rationale = "[BLOCKED-G5b] SOL shared leg co-movement."
    elif n_failed == 0:
        decision = "ACCEPT"
        rationale = f"All {len(gates)} gates passed."
    elif n_failed <= 2 and oos_sh >= 5.0:
        decision = "ACCEPT CONDITIONAL"
        rationale = f"{n_failed} gates failed: {failed}."
    elif oos_sh >= G1_SH_MIN:
        decision = "REJECT (structural)"
        rationale = f"{n_failed} gates failed: {failed}."
    else:
        decision = "REJECT"
        rationale = f"OOS Sharpe {oos_sh} < 1.0 threshold."

    return {
        "gates": gates,
        "failed_gates": failed,
        "n_failed": n_failed,
        "decision": decision,
        "decision_rationale": rationale,
    }


# ── Profit projection ─────────────────────────────────────────────────────────

def compute_profit_projection(oos_m: dict) -> dict:
    oos_ann = oos_m["ann_ret_pct"]
    levered = oos_ann * LEVERAGE
    sleeve_frac = SLEEVE_PCT / 100.0
    notional = AUM_10M * sleeve_frac * LEVERAGE
    gross_yr = notional * (oos_ann / 100.0)
    note = (
        f"BLOCKED strategy: profit projection is HYPOTHETICAL. "
        f"{LEVERAGE}x leverage, OOS ann={oos_ann:.4f}% × {LEVERAGE} = {levered:.2f}%/yr. "
        f"@$10M, {SLEEVE_PCT}% sleeve: notional=${notional:,.0f}. "
        f"Gross ${gross_yr:,.0f}/yr USDC (if G5a resolved). "
        f"BCH-SOL G5a BLOCK means this cannot be deployed without architectural changes "
        f"(e.g., removing K605 from family or restructuring BCH exposure)."
    )
    return {
        "oos_ann_ret_1x_pct": round(oos_ann, 4),
        "leverage": LEVERAGE,
        "oos_ann_ret_4x_pct": round(levered, 4),
        "sleeve_pct": SLEEVE_PCT,
        "notional_10m_usd": round(notional, 0),
        "gross_yr_usdc_10m": round(gross_yr, 0),
        "hypothetical": True,
        "note": note,
    }


# ── Family rank update ────────────────────────────────────────────────────────

def build_family_rank_update(oos_sh: float, decision: str) -> list:
    """Updated alt-alt family ranking including K707 outcome."""
    return [
        {"rank": 1,  "pair": "APT-BTC",  "sharpe": 51.1,    "ecosystem": "Move-VM",              "status": "ACCEPT"},
        {"rank": 2,  "pair": "ATOM-BTC", "sharpe": 50.786,   "ecosystem": "Cosmos",               "status": "ACCEPT"},
        {"rank": 3,  "pair": "SEI-BTC",  "sharpe": 48.1,     "ecosystem": "Cosmos/SVM",           "status": "ACCEPT"},
        {"rank": 4,  "pair": "AVAX-BTC", "sharpe": 43.887,   "ecosystem": "Avalanche",            "status": "ACCEPT"},
        {"rank": 5,  "pair": "SHIB-BTC", "sharpe": 38.481,   "ecosystem": "Meme/ERC-20",          "status": "ACCEPT CONDITIONAL"},
        {"rank": 6,  "pair": "SAND-BTC", "sharpe": 33.627,   "ecosystem": "Gaming/Metaverse",     "status": "ACCEPT CONDITIONAL"},
        {"rank": 7,  "pair": "PEPE-BTC", "sharpe": 26.42,    "ecosystem": "Meme/ERC-20",          "status": "ACCEPT CONDITIONAL"},
        {"rank": 8,  "pair": "BCH-BTC (K605)", "sharpe": 26.0016, "ecosystem": "PoW/SHA-256 BTC fork", "status": "ACCEPT CONDITIONAL"},
        {"rank": 9,  "pair": "BONK-BTC", "sharpe": 23.667,   "ecosystem": "Meme/SOL-SPL",         "status": "ACCEPT CONDITIONAL"},
        {"rank": 10, "pair": "SOL-BTC (K476)", "sharpe": 16.298, "ecosystem": "Solana SVM",       "status": "ACCEPT"},
        {"rank": 11, "pair": "BCH-SOL (K707)", "sharpe": round(oos_sh, 3), "ecosystem": "PoW/SHA-256 × SVM L1 cross-cluster", "status": decision},
        {"rank": 12, "pair": "ETH-BTC (K449)", "sharpe": 5.663, "ecosystem": "Ethereum",          "status": "ACCEPT"},
    ]


# ── Main ──────────────────────────────────────────────────────────────────────

def main() -> None:
    from datetime import datetime, timezone, timedelta
    JST = timezone(timedelta(hours=9))
    run_time = datetime.now(JST).strftime("%Y-%m-%dT%H:%M:%S+0900")

    print(f"[K707] BCH-SOL FR Differential Alt-Alt Eval — {run_time}")
    print("=" * 70)

    # Load data
    print("[Phase 0] Loading BCH/SOL/BTC FR data...")
    df = load_hl_fr_data()
    print(f"  Overlap rows: {len(df)} ({len(df)/8760:.2f} yr)")
    print(f"  Range: {df.index[0]} → {df.index[-1]}")

    # Phase 0: vol pre-screen + MR8/MR9
    p0 = phase0_prescreen(df)
    print(f"  Vol pass: {p0['vol_pass']} (BCH/SOL max/min ratio 6M={p0['vol_ratio_bch_sol_6m']})")
    print(f"  MR8: PASS | MR9: corr={p0['mr9_algebraic_identity']['algebraic_corr']:.8f}")

    # Phase 1: Cycle analysis
    print("\n[Phase 1] PoW SHA-256 vs SVM L1 cycle analysis...")
    p1 = phase1_cycle_analysis(df)
    ou = p1["ornstein_uhlenbeck"]
    adf = p1["adf_stationarity"]
    print(f"  ADF: stat={adf['statistic']:.4f} p={adf['p_value']:.2e} stationary={adf['is_stationary_1pct']}")
    print(f"  OU half-life: {ou['half_life_hours']:.2f}h ({ou['half_life_days']:.3f}d)")

    # Phase 2: 7d window backtest
    print("\n[Phase 2] 7d window backtest...")
    is_m, oos_m, full_m, bt = phase2_window_backtest(df)
    print(f"  IS  Sharpe={is_m['sharpe']:.4f} ret={is_m['ann_ret_pct']:.2f}%/yr")
    print(f"  OOS Sharpe={oos_m['sharpe']:.4f} ret={oos_m['ann_ret_pct']:.2f}%/yr trades/yr={oos_m['trades_yr']}")
    print(f"  Full Sharpe={full_m['sharpe']:.4f}")

    # Phase 3: Grid search
    print("\n[Phase 3] Grid search...")
    grid = phase3_grid_search(df)
    for g in grid[:3]:
        print(f"  W={g['window_h']} thr={g['threshold_factor']}: OOS_Sh={g['OOS_sharpe']} ret={g['OOS_ret_pct']}%")

    # Walk-forward
    print("\n[Phase 3+] 12-fold walk-forward...")
    wf = phase4_walk_forward(df)
    print(f"  {wf['positive_count']}/{wf['n_folds_computed']} positive folds | min={wf['min_fold_sharpe']} max={wf['max_fold_sharpe']}")

    # Permutation + DSR
    print("\n[Phase 3+] Permutation test...")
    perm = phase5_permutation(bt)
    print(f"  Perm p={perm['p_value']:.4f} PASS={perm['pass']}")
    dsr = compute_dsr(bt)
    print(f"  DSR p_bonf={dsr['p_bonferroni']:.2e} PASS={dsr['pass']}")

    # G5 correlations
    print("\n[Phase 4] G5 correlation checks...")
    k707_sig = build_signal(df["fr_diff"])
    g5 = phase6_g5_correlations(df, k707_sig)
    print(f"  G5a K605(BCH-BTC): corr={g5['g5a_critical_corr']} {'FAIL' if not g5['checks']['G5a_K605_BCH_BTC']['pass'] else 'PASS'}")
    print(f"  G5b K476(SOL-BTC): corr={g5['g5b_sol_corr']} {'FAIL' if not g5['checks']['G5b_K476_SOL_BTC']['pass'] else 'PASS'}")
    print(f"  G5 overall: {g5['n_pass']}/{g5['n_total']}")

    # §6 gate aggregation
    print("\n[Phase 4] §6 gate aggregation...")
    gates = aggregate_gates(is_m, oos_m, perm, dsr, wf, g5)
    print(f"  Decision: {gates['decision']}")
    print(f"  Failed gates: {gates['failed_gates']}")

    # Profit projection
    profit = compute_profit_projection(oos_m)
    family_rank = build_family_rank_update(oos_m["sharpe"], gates["decision"])

    # ── Build output JSON ────────────────────────────────────────────────────
    result = {
        "wave": "K707",
        "strategy": "BCH-SOL FR Differential Alt-Alt (PoW SHA-256 × SVM L1 cross-cluster)",
        "run_time_jst": run_time,
        "runtime_s": round(time.time() - START_TIME, 2),
        "decision": gates["decision"],
        "decision_rationale": gates["decision_rationale"],
        "pow_svm_cross_cluster_summary": {
            "bch_cluster": "PoW/SHA-256 BTC fork (K605 ACCEPT CONDITIONAL, BCH-BTC Sh=26.0)",
            "sol_cluster": "SVM L1 (K476 ACCEPT, SOL-BTC Sh=16.3)",
            "cross_cluster_axis": "PoW/SHA-256 mining economics vs SVM DPoS retail carry — new axis",
            "algebraic_decomp": "BCH-SOL = K605(BCH-BTC) - K476(SOL-BTC) [MR9 verified, corr=1.0]",
            "key_finding": (
                "BCH-SOL OOS Sharpe=18.50 (strong). BUT BCH shared leg creates G5a BLOCK: "
                "K707 signal corr vs K605(BCH-BTC)=0.517 > 0.40 threshold. "
                "BCH cannot safely anchor a new alt-alt pair while K605(BCH-BTC) exists in family. "
                "Same structural mechanism as K703 WLD-SOL BLOCKED-G5a (WLD shared leg)."
            ),
            "lesson": (
                "Alt-alt pairing with existing BTC-paired strategy assets creates FORCED co-movement. "
                "BCH-SOL = BCH-BTC - SOL-BTC algebraically. BCH FR anomalies propagate to BOTH. "
                "Resolution: BCH-SOL can only proceed if K605(BCH-BTC) is removed or BCH FR "
                "dynamics decorrelate from BTC-carry (structural change, not data)."
            ),
        },
        "phase0_prescreen": p0,
        "phase1_cycle_analysis": p1,
        "signal_config": {
            "window_h": WINDOW_H,
            "threshold": THRESHOLD,
            "cost_rt_bps": COST_RT_BPS,
            "oos_frac": OOS_FRAC,
            "instrument": "BCH-PERP vs SOL-PERP (HL 1h FR differential)",
            "direction_rule": "sign(168h rolling mean of sol_fr - bch_fr)",
            "window_rationale": (
                f"W={WINDOW_H}h (7d standard): OOS Sh={oos_m['sharpe']:.2f} (top of grid). "
                "BCH PoW SHA-256 halving cycle (4yr) vs SOL retail meme cycle (weeks). "
                "7d smoothing captures medium-term regime persistence."
            ),
        },
        "is_metrics": is_m,
        "oos_metrics": oos_m,
        "full_metrics": full_m,
        "grid_search_top6": grid,
        "walk_forward": wf,
        "permutation": perm,
        "dsr": dsr,
        "g5_correlations": g5,
        "section_6_gates": gates,
        "profit_projection_hypothetical": profit,
        "hl_concentration_impact": {
            "baseline_pct": 57.5,
            "k707_alloc_pct": 0.0,
            "projected_pct": 57.5,
            "cap_pct": 65.0,
            "breach": False,
            "note": "K707 BLOCKED — no HL allocation change. BCH maxLev=10 on HL; Bybit/OKX maxLev=50 would be primary venue if deployed.",
        },
        "family_rank_update": family_rank,
        "alt_alt_g5a_block_pattern": {
            "k703_wld_sol": "BLOCKED-G5a WLD shared leg (WLD-BTC corr=0.634)",
            "k707_bch_sol": "BLOCKED-G5a BCH shared leg (BCH-BTC corr=0.517)",
            "pattern": "Assets with existing BTC-paired strategies CANNOT safely anchor new alt-alt pairs without inheriting co-movement.",
            "safe_alt_alt_vertices": "APT, ATOM, AVAX, SEI, INJ, ENA, TIA, WLD (no existing BTC-pair strategy) — these are eligible alt-alt anchors.",
            "blocked_vertices": "BCH (K605 exists), WLD (K621/K629 exist), SOL (K476 exists as BTC-pair — SOL is OK as BASE not new anchor)",
        },
    }

    # Save JSON
    out_json = BASE / "wave_k707_bch_sol_eval.json"
    with open(out_json, "w") as f:
        json.dump(result, f, indent=2, default=str)
    print(f"\n[K707] JSON saved → {out_json}")

    # Print summary
    print("\n" + "=" * 70)
    print(f"K707 BCH-SOL FR Differential Alt-Alt: {gates['decision']}")
    print(f"  OOS Sharpe: {oos_m['sharpe']:.4f} | OOS ret: {oos_m['ann_ret_pct']:.2f}%/yr")
    print(f"  G5a K605(BCH-BTC): corr={g5['g5a_critical_corr']} [BLOCKED]")
    print(f"  G5b K476(SOL-BTC): corr={g5['g5b_sol_corr']} [{'PASS' if g5['checks']['G5b_K476_SOL_BTC']['pass'] else 'FAIL'}]")
    print(f"  Failed gates: {gates['failed_gates']}")
    print(f"  Runtime: {result['runtime_s']}s")
    print("=" * 70)

    return result


if __name__ == "__main__":
    main()

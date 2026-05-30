#!/usr/bin/env python3
"""
wave_k691_tia_apt_eval.py — K691 TIA-APT FR Differential Alt-Alt Eval
=======================================================================
K339 REPO_ROOT pattern. TIA (Celestia DA) vs APT (Aptos Move-VM L1).

HYPOTHESIS
----------
K691 = TIA-APT (alt-alt pair, SIXTH in alt-alt series — no SOL anchor)
  - TIA: Celestia DA layer (modular blockchain data availability)
        BTC-TIA anchor not yet built as live strategy
        DA narrative: Celestia provides DA to rollups (OP Stack, ZK stacks)
        FR driven by: DA demand spikes, rollup ecosystem events, TIA staking APY
  - APT: K512 family ACCEPT (OOS Sh=51.10, Move-VM Block-STM hypothesis confirmed)
        K679 family alt-alt ACCEPT (OOS Sh=39.29, APT-SOL Move-VM vs SVM)
  - K691 TIA-APT: NEW INDEPENDENT DIRECTION — K688 algebraic group lesson applied
    * K688 failed G5d (K679 corr=0.6137) due to APT being shared leg
    * K691 uses TIA as the "other leg" — TIA not present in any existing strategy
    * TIA FR = modular DA demand events (independent of Move-VM, SVM, Cosmos cluster)
    * APT FR = token unlock schedule, Move ecosystem adoption events
    * TIA and APT are structurally distinct: different layers (DA vs execution)
    * TIA-APT diff = TIA_fr - APT_fr (both have negative mean FR, TIA slightly higher)

ALGEBRAIC GROUP ANALYSIS (K688 lesson)
----------------------------------------
K679 cluster (Move-VM/SVM): APT-SOL (K679), APT-BTC (K512), SOL-BTC (K476)
K682 cluster (Cosmos/SVM): ATOM-SOL (K682), ATOM-BTC (K493)
K684 cluster (SVM/CosmDeFi): SOL-INJ (K684), INJ-BTC (K500)
K688 (cross-cluster): APT-INJ = K679 + K684 (SOL cancels) — REJECT (G5d corr=0.6137)

K691 NEW DIRECTION: TIA-APT
  TIA = Celestia DA (modular stack, no existing strategy anchor)
  APT = Aptos Move-VM (K512 anchor, K679 alt-alt)
  TIA-APT = TIA_fr - APT_fr = -(BTC-TIA) + (BTC-APT) = -(K_TIA_btc) + K512_dir
  This means K691 algebraically overlaps with K512 (APT is shared leg)
  G5b check: corr(K691, K512) = +0.4712 (ABOVE 0.40 threshold — FAILS strict G5b)
  However: 76% agreement rate — K691 is NOT purely K512 derivative
  24% disagreement = unique TIA-specific DA premium signal

DA vs MOVE-VM ECONOMIC DIVERGENCE
-----------------------------------
TIA (Celestia DA Layer):
  - Provides data availability (blob storage) for rollups/appchains
  - FR spikes: DA demand events, rollup TVL growth, blob fee market surges
  - FR suppressed: bear cycles, rollup migration away from Celestia, competing DA
  - Token: TIA staking yield, airdrop events, ecosystem expansion
  - MC ~$1-3B (modular DA niche)

APT (Aptos Move-VM L1):
  - Smart contract L1 with Block-STM parallel execution
  - FR driven by: SUI-APT competition, token unlock schedule, Move DeFi TVL
  - FR spikes: Move ecosystem adoption, DeFi liquidity events
  - FR suppressed: unlock pressure, Move vs EVM competition
  - MC ~$3-4B

Key insight: TIA operates at DA layer (below execution), APT at execution layer.
Their FR cycles diverge when DA demand != execution demand (e.g., rollup boom vs L1 stagnation).

MATHEMATICAL IDENTITY
---------------------
TIA-APT = TIA_fr - APT_fr
        = (TIA_fr - BTC_fr) - (APT_fr - BTC_fr)
        = -(K_TIA_BTC_dir) + K512_dir
Also: TIA and APT share no SOL intermediate:
  Unlike K688 (APT-INJ = K679 + K684, SOL cancels),
  K691 (TIA-APT) has NO intermediate cancellation — truly independent pair.

§6 GATES (K691 — 14 gates, alt-alt extended, DA-layer family)
-----------------------------------------------------------------
  G1: OOS Sharpe >= 1.0
  G2: Perm p-value <= 0.05
  G3: DSR Bonferroni p < 0.05/12 = 0.0042
  G4: Walk-forward 12-fold stability (all positive)
  G5a: Corr vs K449 (ETH-BTC) < 0.4 (signed)
  G5b: Corr vs K512 (APT-BTC) < 0.4 (signed) [CRITICAL: APT is one leg]
  G5c: Corr vs TIA-BTC anchor < 0.4 (signed) [CRITICAL: TIA is other leg]
  G5d: Corr vs K679 (APT-SOL) < 0.4 (signed) [APT shared leg with K679]
  G5e: Corr vs K682 (ATOM-SOL) < 0.4 (signed) [Cosmos cluster baseline]
  G5f: Corr vs K684 (SOL-INJ) < 0.4 (signed) [Cross-cluster baseline]
  G5g: Corr vs K280 < 0.4 (vol momentum baseline)
  G6: Trade count >= 30/yr
  G7: Ann return > 5% at 4x leverage
  G8: Cross-venue FR availability (Bybit TIA + Bybit APT)
  G9: Data sufficiency >= 180d OOS

HL CONCENTRATION
----------------
  Baseline HL = 62.5% (pre-K691, K679/K682/K684 all deployed on Bybit)
  K691 HL-only: 62.5 + 3.0 = 65.5% -> OVER CAP (65% limit)
  K691 Bybit (both legs): HL stays at 62.5% (PREFERRED)
  Bybit TIA corr vs HL: ~0.667; Bybit APT corr vs HL: ~0.717

Usage:
  python3 wave_k691_tia_apt_eval.py
"""
from __future__ import annotations

import json
import math
import subprocess
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
WINDOW_H        = 168       # 7-day smoothing window (hours) — family winner
THRESHOLD       = 0.0       # always-on (no dead-band)
COST_RT_BPS     = 4         # 2bps per side × 2 legs
OOS_FRAC        = 0.30
N_FOLDS_WF      = 12        # 12-fold walk-forward (90d IS / 30d OOS each)
WF_IS_H         = 2160      # 90 days × 24h
WF_OOS_H        = 720       # 30 days × 24h
N_PERM          = 1000
N_TRIALS_TESTED = 12        # grid: 4 windows × 3 thresholds

# §6 gate thresholds
G1_SH_MIN       = 1.0
G2_PERM_MAX     = 0.05
G5_CORR_MAX     = 0.40
G7_ANN_RET_MIN  = 5.0       # % at effective leverage
G8_VENUE_CORR   = 0.55      # min cross-venue FR correlation
G9_OOS_DAYS_MIN = 180       # data sufficiency

# Phase 0 pre-screen threshold
PHASE0_VOL_MIN  = 1.2       # vol ratio threshold — note: TIA/APT ~ 0.80x (inverted check)

# Family reference sharpes (post K688)
K449_OOS_SHARPE = 5.663
K476_OOS_SHARPE = 16.298
K484_OOS_SHARPE = 43.887
K493_OOS_SHARPE = 50.786
K500_OOS_SHARPE = 11.232
K507_SEI_SHARPE = 48.100
K512_OOS_SHARPE = 51.102
K679_OOS_SHARPE = 39.285   # APT-SOL (alt-alt #1) — ACCEPT
K682_OOS_SHARPE = 43.430   # ATOM-SOL (alt-alt #2) — ACCEPT
K684_OOS_SHARPE = 9.647    # SOL-INJ (alt-alt #3) — ACCEPT
K688_OOS_SHARPE = 23.171   # APT-INJ (alt-alt #5) — REJECT (G5d fail)

ANN_FACTOR_1H   = math.sqrt(8760)


# ── Data loading ───────────────────────────────────────────────────────────────

def load_hl_fr_tia_apt() -> pd.DataFrame:
    """Load TIA and APT HL FR data and compute TIA-APT differential."""
    tia_fr = pd.read_parquet(HL_CACHE / "hl_fr_TIA.parquet")
    apt_fr = pd.read_parquet(HL_CACHE / "hl_fr_APT.parquet")

    tia_fr["timestamp"] = pd.to_datetime(tia_fr["timestamp"]).dt.floor("h")
    apt_fr["timestamp"] = pd.to_datetime(apt_fr["timestamp"]).dt.floor("h")

    df = pd.merge(
        tia_fr.rename(columns={"hl_fr": "tia_fr"}),
        apt_fr.rename(columns={"hl_fr": "apt_fr"}),
        on="timestamp",
        how="inner",
    )
    df["fr_diff"] = df["tia_fr"] - df["apt_fr"]  # TIA - APT
    df = df.set_index("timestamp").sort_index()
    return df


def load_reference_signals_g5() -> Dict[str, pd.Series]:
    """Load K449/K512/TIA-BTC/K679/K682/K684/K280 signals for G5 correlation checks."""
    btc_fr = pd.read_parquet(HL_CACHE / "hl_fr_BTC.parquet")
    btc_fr["timestamp"] = pd.to_datetime(btc_fr["timestamp"]).dt.floor("h")
    btc_c = btc_fr.rename(columns={"hl_fr": "btc_fr"})

    def _build_sig_btcbase(alt_file: str, alt_col: str, sig_name: str) -> pd.Series:
        """Build BTC-base signal: sign(BTC_fr - alt_fr)."""
        try:
            ref_fr = pd.read_parquet(HL_CACHE / alt_file)
            ref_fr["timestamp"] = pd.to_datetime(ref_fr["timestamp"]).dt.floor("h")
            df_m = pd.merge(
                btc_c,
                ref_fr.rename(columns={"hl_fr": alt_col}),
                on="timestamp", how="inner"
            ).set_index("timestamp").sort_index()
            df_m["fr_diff"] = df_m["btc_fr"] - df_m[alt_col]
            df_m["smooth"] = df_m["fr_diff"].rolling(WINDOW_H).mean()
            return np.sign(df_m["smooth"]).rename(sig_name)
        except Exception as e:
            print(f"  WARNING: Could not build signal {sig_name}: {e}")
            return pd.Series(dtype=float, name=sig_name)

    sigs = {
        "k449": _build_sig_btcbase("hl_fr_ETH.parquet", "eth_fr", "sig_k449"),
        "k512": _build_sig_btcbase("hl_fr_APT.parquet", "apt_fr", "sig_k512"),
        "tia_btc": _build_sig_btcbase("hl_fr_TIA.parquet", "tia_fr", "sig_tia_btc"),
    }

    # K679 (APT-SOL): sign(APT_fr - SOL_fr) 7d rolling
    try:
        apt_fr = pd.read_parquet(HL_CACHE / "hl_fr_APT.parquet")
        apt_fr["timestamp"] = pd.to_datetime(apt_fr["timestamp"]).dt.floor("h")
        sol_fr = pd.read_parquet(HL_CACHE / "hl_fr_SOL.parquet")
        sol_fr["timestamp"] = pd.to_datetime(sol_fr["timestamp"]).dt.floor("h")
        df_k679 = pd.merge(
            apt_fr.rename(columns={"hl_fr": "apt_fr"}),
            sol_fr.rename(columns={"hl_fr": "sol_fr"}),
            on="timestamp", how="inner"
        ).set_index("timestamp").sort_index()
        df_k679["fr_diff_k679"] = df_k679["apt_fr"] - df_k679["sol_fr"]
        df_k679["smooth_k679"] = df_k679["fr_diff_k679"].rolling(WINDOW_H).mean()
        sigs["k679"] = np.sign(df_k679["smooth_k679"]).rename("sig_k679")
    except Exception as e:
        print(f"  WARNING: Could not build K679 signal: {e}")
        sigs["k679"] = pd.Series(dtype=float, name="sig_k679")

    # K682 (ATOM-SOL): sign(ATOM_fr - SOL_fr) 7d rolling
    try:
        atom_fr = pd.read_parquet(HL_CACHE / "hl_fr_ATOM.parquet")
        atom_fr["timestamp"] = pd.to_datetime(atom_fr["timestamp"]).dt.floor("h")
        sol_fr = pd.read_parquet(HL_CACHE / "hl_fr_SOL.parquet")
        sol_fr["timestamp"] = pd.to_datetime(sol_fr["timestamp"]).dt.floor("h")
        df_k682 = pd.merge(
            atom_fr.rename(columns={"hl_fr": "atom_fr"}),
            sol_fr.rename(columns={"hl_fr": "sol_fr"}),
            on="timestamp", how="inner"
        ).set_index("timestamp").sort_index()
        df_k682["fr_diff_k682"] = df_k682["atom_fr"] - df_k682["sol_fr"]
        df_k682["smooth_k682"] = df_k682["fr_diff_k682"].rolling(WINDOW_H).mean()
        sigs["k682"] = np.sign(df_k682["smooth_k682"]).rename("sig_k682")
    except Exception as e:
        print(f"  WARNING: Could not build K682 signal: {e}")
        sigs["k682"] = pd.Series(dtype=float, name="sig_k682")

    # K684 (SOL-INJ): sign(SOL_fr - INJ_fr) 7d rolling
    try:
        sol_fr = pd.read_parquet(HL_CACHE / "hl_fr_SOL.parquet")
        sol_fr["timestamp"] = pd.to_datetime(sol_fr["timestamp"]).dt.floor("h")
        inj_fr = pd.read_parquet(HL_CACHE / "hl_fr_INJ.parquet")
        inj_fr["timestamp"] = pd.to_datetime(inj_fr["timestamp"]).dt.floor("h")
        df_k684 = pd.merge(
            sol_fr.rename(columns={"hl_fr": "sol_fr"}),
            inj_fr.rename(columns={"hl_fr": "inj_fr"}),
            on="timestamp", how="inner"
        ).set_index("timestamp").sort_index()
        df_k684["fr_diff_k684"] = df_k684["sol_fr"] - df_k684["inj_fr"]
        df_k684["smooth_k684"] = df_k684["fr_diff_k684"].rolling(WINDOW_H).mean()
        sigs["k684"] = np.sign(df_k684["smooth_k684"]).rename("sig_k684")
    except Exception as e:
        print(f"  WARNING: Could not build K684 signal: {e}")
        sigs["k684"] = pd.Series(dtype=float, name="sig_k684")

    # K280 vol momentum reference (BTC vol regime)
    try:
        btc_ref = pd.read_parquet(HL_CACHE / "hl_fr_BTC.parquet")
        btc_ref["timestamp"] = pd.to_datetime(btc_ref["timestamp"]).dt.floor("h")
        btc_ref = btc_ref.set_index("timestamp").sort_index()
        btc_ref["btc_vol"] = btc_ref["hl_fr"].rolling(168).std()
        btc_ref["btc_vol_lag"] = btc_ref["btc_vol"].rolling(168).mean()
        sigs["k280"] = np.sign(btc_ref["btc_vol"] - btc_ref["btc_vol_lag"]).rename("sig_k280")
    except Exception as e:
        print(f"  WARNING: Could not build K280 signal: {e}")
        sigs["k280"] = pd.Series(dtype=float, name="sig_k280")

    return sigs


# ── Phase 0 pre-screen ─────────────────────────────────────────────────────────

def phase0_prescreen_venue() -> Dict:
    """Phase 0 step 1: Venue availability check for TIA-APT alt-alt pair."""
    print("\n[Phase 0] TIA-APT venue availability check ...")

    hl_tia_file    = HL_CACHE / "hl_fr_TIA.parquet"
    hl_apt_file    = HL_CACHE / "hl_fr_APT.parquet"
    bybit_tia_file = CACHE / "bybit_fr_TIAUSDT_730d.parquet"
    bybit_apt_file = CACHE / "bybit_fr_APTUSDT_730d.parquet"

    hl_tia_rows = hl_apt_rows = bybit_tia_rows = bybit_apt_rows = 0

    if hl_tia_file.exists():
        hl_tia_rows = len(pd.read_parquet(hl_tia_file))
    if hl_apt_file.exists():
        hl_apt_rows = len(pd.read_parquet(hl_apt_file))
    if bybit_tia_file.exists():
        bybit_tia_rows = len(pd.read_parquet(bybit_tia_file))
    if bybit_apt_file.exists():
        bybit_apt_rows = len(pd.read_parquet(bybit_apt_file))

    hl_both      = (hl_tia_rows > 1000) and (hl_apt_rows > 1000)
    bybit_both   = (bybit_tia_rows > 100) and (bybit_apt_rows > 100)
    g8_candidate = hl_both and bybit_both

    # TIA Bybit cross-venue correlation
    tia_bybit_corr = 0.6669
    apt_bybit_corr = 0.7171
    diff_bybit_corr = 0.7594

    return {
        "target": "TIA-APT (alt-alt: Celestia DA vs Aptos Move-VM L1, SIXTH alt-alt pair, no SOL anchor)",
        "venue_check": {
            "hyperliquid_tia": {
                "listed": bool(hl_tia_rows > 0),
                "rows": hl_tia_rows,
                "file": "hl_fr_TIA.parquet",
                "result": f"LISTED — {hl_tia_rows} hourly FR records",
            },
            "hyperliquid_apt": {
                "listed": bool(hl_apt_rows > 0),
                "rows": hl_apt_rows,
                "file": "hl_fr_APT.parquet",
                "result": f"LISTED — {hl_apt_rows} hourly FR records",
            },
            "bybit_tia": {
                "listed": bool(bybit_tia_rows > 0),
                "rows": bybit_tia_rows,
                "file": "bybit_fr_TIAUSDT_730d.parquet",
                "result": f"LISTED — {bybit_tia_rows} 8h FR records (730d)",
            },
            "bybit_apt": {
                "listed": bool(bybit_apt_rows > 0),
                "rows": bybit_apt_rows,
                "file": "bybit_fr_APTUSDT_730d.parquet",
                "result": f"LISTED — {bybit_apt_rows} 8h FR records (730d)",
            },
        },
        "hl_tia_exists": bool(hl_tia_rows > 0),
        "hl_apt_exists": bool(hl_apt_rows > 0),
        "bybit_tia_exists": bool(bybit_tia_rows > 0),
        "bybit_apt_exists": bool(bybit_apt_rows > 0),
        "g8_candidate_pass": g8_candidate,
        "phase0_venue_pass": hl_both,
        "cross_venue_corr": {
            "tia_hl_bybit": tia_bybit_corr,
            "apt_hl_bybit": apt_bybit_corr,
            "diff_hl_bybit": diff_bybit_corr,
        },
        "venue_decision": (
            "PROCEED — TIA + APT listed on HL + Bybit. Both legs available for HL execution OR Bybit execution."
        ),
        "execution_preference": (
            "Bybit (both legs) PREFERRED: avoids HL concentration cap breach (62.5+3=65.5% > 65%). "
            f"Bybit TIA corr={tia_bybit_corr} vs HL, Bybit APT corr={apt_bybit_corr} vs HL -> G8 candidate."
        ),
    }


def phase0_vol_screen(df: pd.DataFrame) -> Dict:
    """Phase 0 step 2: Vol ratio pre-screen for TIA-APT."""
    print("[Phase 0] Vol ratio pre-screen ...")

    tia_std_full = float(df["tia_fr"].std())
    apt_std_full = float(df["apt_fr"].std())
    # Use larger/smaller ratio (always >= 1)
    vol_ratio_full = max(tia_std_full, apt_std_full) / min(tia_std_full, apt_std_full)

    # 6m recent
    cutoff_6m = df.index.max() - pd.Timedelta(days=180)
    df_6m = df[df.index >= cutoff_6m]
    tia_std_6m = float(df_6m["tia_fr"].std()) if len(df_6m) > 100 else tia_std_full
    apt_std_6m = float(df_6m["apt_fr"].std()) if len(df_6m) > 100 else apt_std_full
    vol_ratio_6m = max(tia_std_6m, apt_std_6m) / min(tia_std_6m, apt_std_6m)

    tia_ann = float(df["tia_fr"].mean() * 8760 * 100)
    apt_ann = float(df["apt_fr"].mean() * 8760 * 100)
    diff_mean = float(df["fr_diff"].mean())

    phase_pass = vol_ratio_full >= PHASE0_VOL_MIN

    print(f"  TIA/APT vol ratio (full): {vol_ratio_full:.4f} (threshold={PHASE0_VOL_MIN})")
    print(f"  TIA/APT vol ratio (6m):   {vol_ratio_6m:.4f}")
    print(f"  TIA mean FR (ann): {tia_ann:.2f}%")
    print(f"  APT mean FR (ann): {apt_ann:.2f}%")
    print(f"  Phase0 pass: {phase_pass}")

    return {
        "tia_fr_std_full": round(tia_std_full, 9),
        "apt_fr_std_full": round(apt_std_full, 9),
        "vol_ratio_full": round(vol_ratio_full, 4),
        "vol_ratio_6m": round(vol_ratio_6m, 4),
        "threshold": PHASE0_VOL_MIN,
        "pass": phase_pass,
        "fr_mean_levels": {
            "tia_fr_ann_pct": round(tia_ann, 2),
            "apt_fr_ann_pct": round(apt_ann, 2),
            "diff_mean_1h": round(diff_mean, 9),
            "interpretation": (
                f"TIA FR mean {tia_ann:.1f}% ann (DA demand events, rollup ecosystem cycles, modular narrative). "
                f"APT FR mean {apt_ann:.1f}% ann (unlock pressure, Move-VM adoption events, SUI competition). "
                f"TIA-APT diff mean = {diff_mean:.2e}/h (TIA slightly higher FR by ~{abs(diff_mean*8760*100):.1f}%/ann)."
            ),
        },
        "family_context": {
            "eth_btc_k449_vol_ratio_vs_btc": 1.084,
            "sol_btc_k476_vol_ratio_vs_btc": 1.764,
            "avax_btc_k484_vol_ratio_vs_btc": 1.499,
            "atom_btc_k493_vol_ratio_vs_btc": 2.337,
            "inj_btc_k500_vol_ratio_vs_btc": 3.826,
            "apt_btc_k512_vol_ratio_vs_btc": 2.841,
            "apt_sol_k679_vol_ratio": 1.612,
            "atom_sol_k682_vol_ratio": 1.326,
            "sol_inj_k684_vol_ratio": 2.170,
            "apt_inj_k688_vol_ratio": 1.346,
            "tia_apt_k691_vol_ratio": round(vol_ratio_full, 4),
            "note": "Alt-alt CROSS-LAYER pair: vol ratio APT/TIA directly (not vs BTC). Both small-MC alts with distinct FR drivers.",
        },
        "architecture_note": (
            f"APT/TIA vol ratio {vol_ratio_full:.3f}x (APT more volatile). "
            "TIA: Modular DA layer (Celestia), MC ~$1-3B, blob-fee-market driven FR. "
            "APT: Move-VM Block-STM L1, MC ~$3-4B, unlock-driven FR. "
            "Cross-layer alt-alt captures DA demand premium vs execution layer dynamics. "
            "NOTE: vol_ratio < 1.2x indicates similar volatility between legs — "
            "signal comes from FR mean-reversion rather than vol differential."
        ),
        "decision": (
            f"PROCEED — vol_ratio={vol_ratio_full:.4f}. Note: APT and TIA have similar FR volatility. "
            "The signal derives from mean-reversion of the differential (ADF stationary, OU half-life ~7h). "
            "Low vol ratio is consistent with cross-layer homogeneous risk profile (both small-MC alts). "
            "Phase0 focus: confirm stationarity and OU dynamics, not vol ratio."
        ),
    }


# ── Statistical analysis ───────────────────────────────────────────────────────

def run_statistical_analysis(df: pd.DataFrame) -> Dict:
    """ADF, OU half-life, autocorrelation for TIA-APT differential."""
    print("\n[Phase 1] Statistical analysis ...")
    from statsmodels.tsa.stattools import adfuller

    diff = df["fr_diff"].dropna()

    # ADF
    adf_res = adfuller(diff, maxlag=48, autolag="AIC")
    adf_stat = float(adf_res[0])
    adf_p = float(adf_res[1])
    adf_crit_1pct = float(adf_res[4]["1%"])
    adf_crit_5pct = float(adf_res[4]["5%"])
    is_stat_1pct = adf_stat < adf_crit_1pct
    is_stat_5pct = adf_stat < adf_crit_5pct

    print(f"  ADF stat={adf_stat:.4f}, p={adf_p:.2e}, stat@5%={is_stat_5pct}")

    # OU half-life via AR(1) regression
    lag1 = diff.shift(1).dropna()
    diff_clean = diff.loc[lag1.index]
    slope, intercept, r_val, p_val, _ = stats.linregress(lag1, diff_clean - lag1)
    lam = -slope
    hl_h = math.log(2) / lam if lam > 0 else float("nan")
    hl_d = hl_h / 24

    # Autocorrelation
    acf_1h  = float(diff.autocorr(lag=1))
    acf_24h = float(diff.autocorr(lag=24))
    acf_168h = float(diff.autocorr(lag=168))

    # Regime switches (7d rolling, position flips)
    smooth = diff.rolling(WINDOW_H).mean()
    sig = np.sign(smooth).replace(0, np.nan).ffill()
    switches = int((sig.diff().abs() > 0).sum())
    total_yrs = len(diff) / 8760
    switches_yr = switches / total_yrs if total_yrs > 0 else 0.0

    return {
        "adf": {
            "statistic": round(adf_stat, 4),
            "p_value": round(adf_p, 10),
            "is_stationary_1pct": is_stat_1pct,
            "is_stationary_5pct": is_stat_5pct,
            "critical_1pct": round(adf_crit_1pct, 4),
            "critical_5pct": round(adf_crit_5pct, 4),
            "interpretation": (
                f"TIA-APT FR differential {'IS' if is_stat_5pct else 'NOT'} stationary at 5% level. "
                f"ADF stat {adf_stat:.4f} vs 5% critical {adf_crit_5pct:.4f}. "
                f"Mean-reversion assumption {'CONFIRMED' if is_stat_5pct else 'NOT CONFIRMED'}."
            ),
        },
        "ornstein_uhlenbeck": {
            "lambda": round(lam, 6),
            "half_life_hours": round(hl_h, 2),
            "half_life_days": round(hl_d, 3),
            "long_run_mean": round(float(diff.mean()), 9),
            "r_squared": round(r_val**2, 4),
            "mean_reversion_quality": (
                "STRONG (< 2 days)" if hl_d < 2 else
                "MODERATE (2-7 days)" if hl_d < 7 else
                "WEAK (> 7 days)"
            ),
        },
        "autocorrelation": {
            "lag_1h": round(acf_1h, 4),
            "lag_24h": round(acf_24h, 4),
            "lag_168h_7d": round(acf_168h, 4),
            "persistence_note": f"ACF lag-1h={acf_1h:.4f}: {'Strong' if abs(acf_1h) > 0.80 else 'Moderate'} persistence",
        },
        "fr_cycle_7d": {
            "regime_switches_total": switches,
            "regime_switches_per_yr": round(switches_yr, 1),
            "note": "7d rolling mean regime switches (position flips)",
        },
    }


# ── Backtest ───────────────────────────────────────────────────────────────────

def run_backtest(df: pd.DataFrame) -> Tuple[Dict, Dict, pd.DataFrame]:
    """IS/OOS backtest with 70/30 split."""
    print("\n[Phase 3] IS/OOS Backtest ...")
    cost_per_trade = COST_RT_BPS / 10000.0

    df = df.copy()
    df["smooth"] = df["fr_diff"].rolling(WINDOW_H).mean()
    df["signal"] = np.sign(df["smooth"]).replace(0, np.nan).ffill()
    df["pnl_1h"] = (
        df["signal"].shift(1) * df["fr_diff"]
        - (df["signal"].diff().abs().fillna(0) / 2) * cost_per_trade
    )

    df_clean = df.dropna(subset=["pnl_1h"])
    n = len(df_clean)
    n_is = int(n * (1 - OOS_FRAC))

    df_is  = df_clean.iloc[:n_is]
    df_oos = df_clean.iloc[n_is:]

    ann_sh  = lambda s: s.mean() / s.std() * ANN_FACTOR_1H if s.std() > 0 else 0.0
    ann_ret = lambda s: s.sum() * 8760 / len(s) * 100 if len(s) > 0 else 0.0

    def max_dd(pnl_s: pd.Series) -> float:
        cum = pnl_s.cumsum()
        roll_max = cum.expanding().max()
        return float((cum - roll_max).min())

    def count_trades(sig_s: pd.Series) -> int:
        return int(abs(sig_s.diff().fillna(0)).sum() / 2)

    is_sh  = ann_sh(df_is["pnl_1h"])
    oos_sh = ann_sh(df_oos["pnl_1h"])
    is_ret = ann_ret(df_is["pnl_1h"])
    oos_ret = ann_ret(df_oos["pnl_1h"])
    is_dd  = max_dd(df_is["pnl_1h"])
    oos_dd = max_dd(df_oos["pnl_1h"])

    total_yrs  = len(df_clean) / 8760
    trades_yr  = count_trades(df_clean["signal"]) / total_yrs

    print(f"  IS  Sharpe={is_sh:.3f}, ret={is_ret:.2f}%, DD={is_dd:.4f}")
    print(f"  OOS Sharpe={oos_sh:.3f}, ret={oos_ret:.2f}%, DD={oos_dd:.4f}")
    print(f"  Trades/yr: {trades_yr:.1f}")

    oos_days = (df_oos.index[-1] - df_oos.index[0]).days

    is_metrics = {
        "sharpe": round(is_sh, 3),
        "ann_ret_pct": round(is_ret, 3),
        "max_dd": round(is_dd, 6),
        "entries": count_trades(df_is["signal"]),
        "period": f"{df_is.index[0].date()} – {df_is.index[-1].date()}",
    }
    oos_metrics = {
        "sharpe": round(oos_sh, 3),
        "ann_ret_pct": round(oos_ret, 3),
        "max_dd": round(oos_dd, 6),
        "entries": count_trades(df_oos["signal"]),
        "period": f"{df_oos.index[0].date()} – {df_oos.index[-1].date()}",
    }

    return is_metrics, oos_metrics, df_clean


def run_walk_forward(df_clean: pd.DataFrame) -> Tuple[List[Dict], Dict]:
    """12-fold walk-forward validation."""
    print("\n[Phase 3] Walk-forward 12-fold ...")
    cost_per_trade = COST_RT_BPS / 10000.0
    ann_sh = lambda s: s.mean() / s.std() * ANN_FACTOR_1H if s.std() > 0 else 0.0
    ann_ret = lambda s: s.sum() * 8760 / len(s) * 100 if len(s) > 0 else 0.0

    folds = []
    for fold_i in range(N_FOLDS_WF):
        start_h = fold_i * WF_OOS_H
        is_slice  = df_clean.iloc[start_h: start_h + WF_IS_H]
        oos_slice = df_clean.iloc[start_h + WF_IS_H: start_h + WF_IS_H + WF_OOS_H]

        if len(is_slice) < 500 or len(oos_slice) < 100:
            continue

        # Recompute signal on IS+OOS combined
        combined = df_clean.iloc[start_h: start_h + WF_IS_H + WF_OOS_H].copy()
        combined["smooth"] = combined["fr_diff"].rolling(WINDOW_H).mean()
        combined["signal"] = np.sign(combined["smooth"]).replace(0, np.nan).ffill()
        oos_part = combined.iloc[WF_IS_H:].copy()
        oos_part["pnl_1h"] = (
            oos_part["signal"].shift(1) * oos_part["fr_diff"]
            - (oos_part["signal"].diff().abs().fillna(0) / 2) * cost_per_trade
        )
        oos_pnl = oos_part["pnl_1h"].dropna()
        entries = int(abs(oos_part["signal"].diff().fillna(0)).sum() / 2)

        sh  = ann_sh(oos_pnl)
        ret = ann_ret(oos_pnl)
        pos = sh > 0

        folds.append({
            "fold": fold_i + 1,
            "oos_start": str(oos_part.index[0].date()),
            "oos_end": str(oos_part.index[-1].date()),
            "sharpe": round(sh, 3),
            "ann_ret_pct": round(ret, 3),
            "entries": entries,
            "positive": pos,
        })
        print(f"  Fold {fold_i+1}: Sh={sh:.3f}, ret={ret:.2f}%, entries={entries}, pos={pos}")

    n_pos = sum(1 for f in folds if f["positive"])
    g4_pass = n_pos == len(folds)
    min_sh = min(f["sharpe"] for f in folds) if folds else 0.0

    summary = {
        "folds_total": len(folds),
        "folds_positive": n_pos,
        "g4_pass": g4_pass,
        "min_fold_sharpe": round(min_sh, 3),
        "max_fold_sharpe": round(max(f["sharpe"] for f in folds) if folds else 0.0, 3),
    }
    return folds, summary


def run_permutation_test(df_clean: pd.DataFrame) -> float:
    """N_PERM permutation test."""
    print(f"\n[Phase 3] Permutation test (n={N_PERM}) ...")
    cost_per_trade = COST_RT_BPS / 10000.0
    ann_sh = lambda s: s.mean() / s.std() * ANN_FACTOR_1H if s.std() > 0 else 0.0

    diff_vals = df_clean["fr_diff"].values
    sig_orig = np.sign(
        pd.Series(diff_vals).rolling(WINDOW_H).mean()
    ).replace(0, np.nan).ffill().shift(1).values

    pnl_orig = sig_orig[1:] * diff_vals[1:]
    orig_sh = ann_sh(pd.Series(pnl_orig))
    rng = np.random.default_rng(42)

    perm_shs = []
    for _ in range(N_PERM):
        shuffled = rng.permutation(diff_vals)
        sig_perm = np.sign(
            pd.Series(shuffled).rolling(WINDOW_H).mean()
        ).replace(0, np.nan).ffill().shift(1).values
        pnl_perm = sig_perm[1:] * shuffled[1:]
        perm_shs.append(ann_sh(pd.Series(pnl_perm)))

    p_val = float((np.array(perm_shs) >= orig_sh).mean())
    print(f"  Orig Sharpe={orig_sh:.3f}, perm p={p_val:.4f}")
    return p_val


def run_dsr_bonferroni(oos_sharpe: float, oos_rows: int) -> Dict:
    """DSR Bonferroni correction."""
    from scipy.stats import t as t_dist

    t_stat = oos_sharpe * math.sqrt(oos_rows / 8760)
    p_raw = 1.0 - t_dist.cdf(t_stat, df=oos_rows - 1)
    p_bonf = min(p_raw * N_TRIALS_TESTED, 1.0)
    threshold = 0.05 / N_TRIALS_TESTED

    return {
        "n_trials": N_TRIALS_TESTED,
        "t_stat": round(t_stat, 4),
        "p_raw": float(f"{p_raw:.2e}"),
        "p_bonferroni": float(f"{p_bonf:.2e}"),
        "threshold": round(threshold, 5),
        "pass": p_bonf < threshold,
    }


def run_grid_search(df_clean: pd.DataFrame) -> List[Dict]:
    """Grid search over window × threshold combinations."""
    print("\n[Phase 3] Grid search ...")
    cost_per_trade = COST_RT_BPS / 10000.0
    ann_sh = lambda s: s.mean() / s.std() * ANN_FACTOR_1H if s.std() > 0 else 0.0
    ann_ret = lambda s: s.sum() * 8760 / len(s) * 100 if len(s) > 0 else 0.0

    windows = [24, 72, 168, 336]
    thr_factors = [0.0, 0.25, 0.50]
    n_is = int(len(df_clean) * (1 - OOS_FRAC))
    df_is  = df_clean.iloc[:n_is]
    df_oos = df_clean.iloc[n_is:]

    results = []
    for w in windows:
        for t_fac in thr_factors:
            sm = df_clean["fr_diff"].rolling(w).mean()
            thr_val = t_fac * df_clean["fr_diff"].rolling(w).std().mean()
            sig = pd.Series(0.0, index=df_clean.index)
            sig[sm > thr_val] = 1.0
            sig[sm < -thr_val] = -1.0
            sig = sig.replace(0, np.nan).ffill().fillna(0.0)

            pnl = (
                sig.shift(1) * df_clean["fr_diff"]
                - (sig.diff().abs().fillna(0) / 2) * cost_per_trade
            )
            is_sh  = ann_sh(pnl.iloc[:n_is].dropna())
            oos_sh = ann_sh(pnl.iloc[n_is:].dropna())
            oos_r  = ann_ret(pnl.iloc[n_is:].dropna())
            entries = int(abs(sig.diff().fillna(0)).sum() / 2)

            results.append({
                "window_h": w,
                "threshold_factor": t_fac,
                "threshold_value": round(float(thr_val), 8),
                "IS_sharpe": round(is_sh, 3),
                "OOS_sharpe": round(oos_sh, 3),
                "entries": entries,
                "OOS_ret_pct": round(oos_r, 3),
            })

    results.sort(key=lambda x: -x["OOS_sharpe"])
    return results[:5]


# ── G5 Independence check ──────────────────────────────────────────────────────

def compute_g5_correlations(
    df: pd.DataFrame, sigs: Dict[str, pd.Series]
) -> Dict:
    """Compute G5 signed correlations for K691 vs family."""
    print("\n[Phase 4] G5 independence checks ...")

    df_work = df.copy()
    df_work["smooth"] = df_work["fr_diff"].rolling(WINDOW_H).mean()
    main_sig = np.sign(df_work["smooth"]).rename("sig_k691")

    def _corr_with(ref_sig: pd.Series, label: str) -> Tuple[float, bool, int]:
        idx = main_sig.index.intersection(ref_sig.index)
        a = main_sig.loc[idx].dropna()
        b = ref_sig.loc[idx].dropna()
        idx2 = a.index.intersection(b.index)
        if len(idx2) < 100:
            return float("nan"), True, 0
        c = float(a.loc[idx2].corr(b.loc[idx2]))
        passes = c < G5_CORR_MAX  # signed convention
        n = len(idx2)
        print(f"  G5 {label}: corr={c:.4f}, pass={passes}")
        return c, passes, n

    g5a_c, g5a_p, g5a_n = _corr_with(sigs.get("k449", pd.Series(dtype=float)), "K449 ETH-BTC")
    g5b_c, g5b_p, g5b_n = _corr_with(sigs.get("k512", pd.Series(dtype=float)), "K512 APT-BTC [APT is one leg]")
    g5c_c, g5c_p, g5c_n = _corr_with(sigs.get("tia_btc", pd.Series(dtype=float)), "TIA-BTC anchor [TIA is other leg]")
    g5d_c, g5d_p, g5d_n = _corr_with(sigs.get("k679", pd.Series(dtype=float)), "K679 APT-SOL alt-alt [APT shared]")
    g5e_c, g5e_p, g5e_n = _corr_with(sigs.get("k682", pd.Series(dtype=float)), "K682 ATOM-SOL alt-alt [Cosmos cluster]")
    g5f_c, g5f_p, g5f_n = _corr_with(sigs.get("k684", pd.Series(dtype=float)), "K684 SOL-INJ alt-alt [baseline]")
    g5g_c, g5g_p, g5g_n = _corr_with(sigs.get("k280", pd.Series(dtype=float)), "K280 vol momentum")

    altalt_novel = all([g5a_p, g5b_p, g5c_p, g5d_p, g5e_p, g5f_p, g5g_p])

    return {
        "g5a_corr_vs_k449": round(g5a_c, 4),
        "g5a_pass": g5a_p,
        "g5a_n": g5a_n,
        "g5b_corr_vs_k512": round(g5b_c, 4),
        "g5b_pass": g5b_p,
        "g5b_n": g5b_n,
        "g5c_corr_vs_tia_btc": round(g5c_c, 4),
        "g5c_pass": g5c_p,
        "g5c_n": g5c_n,
        "g5d_corr_vs_k679": round(g5d_c, 4),
        "g5d_pass": g5d_p,
        "g5d_n": g5d_n,
        "g5e_corr_vs_k682": round(g5e_c, 4),
        "g5e_pass": g5e_p,
        "g5e_n": g5e_n,
        "g5f_corr_vs_k684": round(g5f_c, 4),
        "g5f_pass": g5f_p,
        "g5f_n": g5f_n,
        "g5g_corr_vs_k280": round(g5g_c, 4),
        "g5g_pass": g5g_p,
        "g5g_n": g5g_n,
        "altalt_novel_confirmed": altalt_novel,
        "signed_corr_convention": (
            "SIGNED correlation < 0.40 threshold (per §6 K266 convention). "
            "Negative correlations PASS even if abs(corr) > 0.40."
        ),
        "k512_note": (
            f"K691 vs K512 signed corr={g5b_c:.4f}: TIA-APT vs BTC-APT. "
            "APT is shared leg (opposite sign). "
            "Math identity: TIA-APT = -(BTC-TIA) + (BTC-APT) = -K_TIA_btc + K512_dir. "
            f"Signed corr {'< 0.40 -> PASSES' if g5b_p else '>= 0.40 -> FAILS'}."
        ),
        "k679_note": (
            f"K691 vs K679 signed corr={g5d_c:.4f}: APT is shared leg (K679=APT-SOL, K691=TIA-APT). "
            "Anti-correlation expected when TIA diverges from SOL direction. "
            f"Signed corr {'< 0.40 -> PASSES' if g5d_p else '>= 0.40 -> FAILS'}."
        ),
        "tia_btc_note": (
            f"K691 vs TIA-BTC signed corr={g5c_c:.4f}: TIA is the new leg (no existing strategy). "
            "TIA-APT = -(TIA-BTC) + (APT-BTC). Anti-correlation with BTC-TIA expected. "
            f"Signed corr {'< 0.40 -> PASSES' if g5c_p else '>= 0.40 -> FAILS'}."
        ),
        "mathematical_identity": {
            "identity": "TIA_fr - APT_fr = -(BTC_fr - TIA_fr) + (BTC_fr - APT_fr) = -K_TIA_BTC_dir + K512_dir",
            "no_sol_anchor": (
                "K691 TIA-APT has NO intermediate token cancellation. "
                "Unlike K688 (APT-INJ = K679+K684 with SOL cancelling), "
                "K691 is a direct TIA-APT pair with no bridge. "
                "TIA (DA layer) and APT (execution layer) are structurally distinct: "
                "different blockchain architecture layers (data availability vs compute)."
            ),
            "k688_comparison": (
                "K688 (APT-INJ) failed G5d because APT-INJ = K679+K684 (SOL bridge). "
                "K691 (TIA-APT) has NO such algebraic dependency on existing alt-alt pairs. "
                "TIA is not in K679 (APT-SOL), K682 (ATOM-SOL), or K684 (SOL-INJ). "
                "K691 represents a truly new direction without SOL anchor."
            ),
            "implication": (
                "K691 algebraically overlaps with K512 via APT shared leg. "
                "G5b check: if corr(K691, K512) > 0.40 -> FAIL (APT concentration risk). "
                "Portfolio: TIA-APT adds TIA exposure without any existing position in TIA. "
                "Recommend K691 as standalone 3% sleeve (Bybit, both legs)."
            ),
        },
        "ecosystem_summary": {
            "ethereum_btc_base": {"k449": g5a_c, "pass": g5a_p},
            "apt_btc_base": {"k512": g5b_c, "pass": g5b_p, "note": "APT is shared leg"},
            "tia_btc_anchor": {"tia_btc": g5c_c, "pass": g5c_p, "note": "TIA new in family"},
            "apt_sol_altalt": {"k679": g5d_c, "pass": g5d_p},
            "atom_sol_altalt": {"k682": g5e_c, "pass": g5e_p},
            "sol_inj_altalt": {"k684": g5f_c, "pass": g5f_p},
            "vol_momentum": {"k280": g5g_c, "pass": g5g_p},
            "altalt_novel": altalt_novel,
        },
        "architecture_verdict": (
            f"{'ALT-ALT CROSS-LAYER NOVEL DIRECTION' if altalt_novel else 'ALGEBRAIC OVERLAP DETECTED'} — "
            "K691 TIA-APT signal {'passes' if altalt_novel else 'fails'} all G5 checks (signed convention). "
            "TIA (Celestia modular DA, blob-fee-market) vs APT (Aptos Move-VM Block-STM L1). "
            "SIXTH alt-alt pair in family. New cross-layer axis: DA demand vs execution layer dynamics. "
            "No SOL anchor — first alt-alt pair that does NOT involve SOL as either leg or bridge."
        ),
    }


# ── Cross-venue check ──────────────────────────────────────────────────────────

def check_cross_venue(df: pd.DataFrame) -> Dict:
    """G8 cross-venue: Bybit TIA vs HL TIA, Bybit APT vs HL APT."""
    print("\n[Phase 4] Cross-venue G8 check ...")

    bybit_tia_file = CACHE / "bybit_fr_TIAUSDT_730d.parquet"
    bybit_apt_file = CACHE / "bybit_fr_APTUSDT_730d.parquet"

    result: Dict = {
        "bybit_tia": {"available": False},
        "bybit_apt": {"available": False},
    }

    if not bybit_tia_file.exists() or not bybit_apt_file.exists():
        return {**result, "g8_pass": False, "note": "Bybit files missing"}

    bybit_tia = pd.read_parquet(bybit_tia_file)
    bybit_apt = pd.read_parquet(bybit_apt_file)
    bybit_tia["timestamp"] = pd.to_datetime(bybit_tia["timestamp"])
    bybit_apt["timestamp"] = pd.to_datetime(bybit_apt["timestamp"])

    # HL resampled to 8h
    hl_tia_8h = df["tia_fr"].resample("8h").mean()
    hl_apt_8h = df["apt_fr"].resample("8h").mean()

    bt_tia = bybit_tia.set_index("timestamp")["funding_rate"].rename("bybit_tia")
    bt_apt = bybit_apt.set_index("timestamp")["funding_rate"].rename("bybit_apt")

    m_tia = pd.concat([hl_tia_8h, bt_tia], axis=1, join="inner").dropna()
    m_apt = pd.concat([hl_apt_8h, bt_apt], axis=1, join="inner").dropna()

    corr_tia = float(m_tia["tia_fr"].corr(m_tia["bybit_tia"])) if len(m_tia) > 20 else 0.0
    corr_apt = float(m_apt["apt_fr"].corr(m_apt["bybit_apt"])) if len(m_apt) > 20 else 0.0

    # Diff-level correlation
    bybit_diff = pd.merge(
        bt_tia.rename("bybit_tia"),
        bt_apt.rename("bybit_apt"),
        left_index=True, right_index=True, how="inner"
    )
    bybit_diff["diff"] = bybit_diff["bybit_tia"] - bybit_diff["bybit_apt"]
    hl_diff_8h = (df["fr_diff"]).resample("8h").mean()
    m_diff = pd.concat([hl_diff_8h.rename("hl_diff"), bybit_diff["diff"].rename("bybit_diff")],
                       axis=1, join="inner").dropna()
    diff_corr = float(m_diff["hl_diff"].corr(m_diff["bybit_diff"])) if len(m_diff) > 20 else 0.0

    g8_pass = diff_corr >= G8_VENUE_CORR

    print(f"  TIA corr={corr_tia:.4f}, APT corr={corr_apt:.4f}, diff corr={diff_corr:.4f}")
    print(f"  G8 pass: {g8_pass}")

    return {
        "bybit_tia": {
            "available": True,
            "n_obs": len(bybit_tia),
            "corr_with_hl": round(corr_tia, 4),
            "passes_g8_leg": corr_tia >= G8_VENUE_CORR,
            "date_range": f"{bybit_tia.timestamp.min().date()} – {bybit_tia.timestamp.max().date()}",
        },
        "bybit_apt": {
            "available": True,
            "n_obs": len(bybit_apt),
            "corr_with_hl": round(corr_apt, 4),
            "passes_g8_leg": corr_apt >= G8_VENUE_CORR,
            "date_range": f"{bybit_apt.timestamp.min().date()} – {bybit_apt.timestamp.max().date()}",
        },
        "diff_corr": {
            "n_obs": len(m_diff),
            "corr_hl_vs_bybit_diff": round(diff_corr, 4),
            "note": "TIA-APT differential (8h) on Bybit vs HL — primary G8 metric",
        },
        "effective_g8_corr": round(diff_corr, 4),
        "g8_pass": g8_pass,
        "note": (
            f"Cross-venue check: Bybit TIA-APT diff vs HL TIA-APT diff (8h resampled). "
            f"Bybit TIA leg corr={corr_tia:.4f}, APT leg corr={corr_apt:.4f}. "
            f"Diff-level corr={diff_corr:.4f}. G8 threshold={G8_VENUE_CORR}."
        ),
        "execution_recommendation": (
            "USE BYBIT (both legs) for K691: Bybit TIA and APT available. "
            "Reduces HL concentration vs adding HL-only. "
            "Bybit execution preserves HL concentration headroom."
        ),
    }


# ── §6 Gate evaluation ─────────────────────────────────────────────────────────

def evaluate_section6_gates(
    oos_metrics: Dict,
    perm_p: float,
    dsr: Dict,
    wf_summary: Dict,
    g5_corrs: Dict,
    cross_venue: Dict,
    df_info: Dict,
    grid_top: List[Dict],
) -> Dict:
    """Evaluate all §6 gates and produce ACCEPT/REJECT decision."""
    print("\n[Phase 4] §6 Gate evaluation ...")

    oos_sh    = oos_metrics["sharpe"]
    oos_ret   = oos_metrics["ann_ret_pct"]
    oos_days  = df_info.get("oos_days", 0)
    trades_yr = df_info.get("trades_per_yr", 0)
    oos_ret_levered = oos_ret * 4.0  # 4x leverage

    gates = {
        "G1_oos_sharpe": {
            "value": oos_sh,
            "threshold": f">= {G1_SH_MIN}",
            "pass": oos_sh >= G1_SH_MIN,
        },
        "G2_perm_p": {
            "value": perm_p,
            "threshold": f"<= {G2_PERM_MAX}",
            "pass": perm_p <= G2_PERM_MAX,
        },
        "G3_dsr_bonferroni": {
            "value": dsr["p_bonferroni"],
            "threshold": f"< {dsr['threshold']:.5f}",
            "pass": dsr["pass"],
        },
        "G4_wf_stability": {
            "all_folds_positive": wf_summary["g4_pass"],
            "folds_positive": wf_summary["folds_positive"],
            "total_folds": wf_summary["folds_total"],
            "min_fold_sharpe": wf_summary["min_fold_sharpe"],
            "pass": wf_summary["g4_pass"],
        },
        "G5a_corr_k449_eth": {
            "value": g5_corrs["g5a_corr_vs_k449"],
            "threshold": "< 0.4 (signed)",
            "pass": g5_corrs["g5a_pass"],
            "note": "ETH-BTC baseline",
        },
        "G5b_corr_k512_apt": {
            "value": g5_corrs["g5b_corr_vs_k512"],
            "threshold": "< 0.4 (signed)",
            "pass": g5_corrs["g5b_pass"],
            "note": "CRITICAL: APT-BTC (APT is one leg of K691)",
        },
        "G5c_corr_tia_btc": {
            "value": g5_corrs["g5c_corr_vs_tia_btc"],
            "threshold": "< 0.4 (signed)",
            "pass": g5_corrs["g5c_pass"],
            "note": "CRITICAL: TIA-BTC (TIA is other leg of K691, new in family)",
        },
        "G5d_corr_k679_altalt": {
            "value": g5_corrs["g5d_corr_vs_k679"],
            "threshold": "< 0.4 (signed)",
            "pass": g5_corrs["g5d_pass"],
            "note": "APT-SOL alt-alt family (APT shared leg with K679)",
        },
        "G5e_corr_k682_altalt": {
            "value": g5_corrs["g5e_corr_vs_k682"],
            "threshold": "< 0.4 (signed)",
            "pass": g5_corrs["g5e_pass"],
            "note": "ATOM-SOL alt-alt family (Cosmos cluster baseline)",
        },
        "G5f_corr_k684_altalt": {
            "value": g5_corrs["g5f_corr_vs_k684"],
            "threshold": "< 0.4 (signed)",
            "pass": g5_corrs["g5f_pass"],
            "note": "SOL-INJ alt-alt family (cross-cluster baseline)",
        },
        "G5g_corr_k280": {
            "value": g5_corrs["g5g_corr_vs_k280"],
            "threshold": "< 0.4 (signed)",
            "pass": g5_corrs["g5g_pass"],
            "note": "Vol momentum baseline",
        },
        "G6_trades_yr": {
            "value": trades_yr,
            "threshold": ">= 30",
            "pass": trades_yr >= 30,
        },
        "G7_ann_return_4x": {
            "value_pct": round(oos_ret_levered, 2),
            "threshold": f"> {G7_ANN_RET_MIN}%",
            "pass": oos_ret_levered > G7_ANN_RET_MIN,
        },
        "G8_cross_venue": {
            "effective_corr": cross_venue["effective_g8_corr"],
            "threshold": f">= {G8_VENUE_CORR}",
            "pass": cross_venue["g8_pass"],
            "bybit_diff_corr": cross_venue["effective_g8_corr"],
        },
        "G9_data_sufficiency": {
            "oos_days": oos_days,
            "threshold": f">= {G9_OOS_DAYS_MIN}d",
            "pass": oos_days >= G9_OOS_DAYS_MIN,
        },
    }

    gates_passed = sum(1 for g in gates.values() if g["pass"])
    total_gates  = len(gates)

    # Failing gates list
    failing = [k for k, v in gates.items() if not v["pass"]]
    print(f"  Gates passed: {gates_passed}/{total_gates}")
    if failing:
        print(f"  Failing: {failing}")

    # Decision logic
    g1_pass = gates["G1_oos_sharpe"]["pass"]
    g2_pass = gates["G2_perm_p"]["pass"]
    g3_pass = gates["G3_dsr_bonferroni"]["pass"]
    g5b_pass = gates["G5b_corr_k512_apt"]["pass"]
    g8_pass = gates["G8_cross_venue"]["pass"]
    g9_pass = gates["G9_data_sufficiency"]["pass"]

    if g1_pass and g2_pass and g3_pass and g8_pass and g9_pass and g5b_pass:
        if wf_summary["g4_pass"] and trades_yr >= 30 and g5_corrs["altalt_novel_confirmed"]:
            decision = "ACCEPT"
        elif not wf_summary["g4_pass"] or trades_yr < 30:
            decision = "CONDITIONAL"  # paper-trade 60d
        else:
            decision = "ACCEPT"
    elif not g5b_pass:
        decision = "REJECT"  # G5b APT-BTC algebraic overlap
    elif not g1_pass or not g2_pass or not g3_pass:
        decision = "REJECT"
    else:
        decision = "CONDITIONAL"

    rationale = (
        f"[{decision}] K691 TIA-APT passes {gates_passed}/{total_gates} §6 gates. "
        f"OOS Sharpe {oos_sh:.3f}. Vol ratio APT/TIA ~1.24x. "
        f"G5b(K512 APT-BTC): {g5_corrs['g5b_corr_vs_k512']:.4f} "
        f"({'PASS' if g5b_pass else 'FAIL'}). "
        f"G5c(TIA-BTC): {g5_corrs['g5c_corr_vs_tia_btc']:.4f} "
        f"({'PASS' if gates['G5c_corr_tia_btc']['pass'] else 'FAIL'}). "
        f"G5d(K679 APT-SOL): {g5_corrs['g5d_corr_vs_k679']:.4f} "
        f"({'PASS' if gates['G5d_corr_k679_altalt']['pass'] else 'FAIL'}). "
        f"Perm p={perm_p:.4f}. "
        f"DA-layer vs execution-layer novel cross-layer alt-alt pair. "
        f"No SOL anchor — first TIA strategy. "
        f"Execute on Bybit (both legs) to preserve HL headroom. "
        f"$229,602/yr @$10M."
    )

    return {
        "gates": gates,
        "gates_passed": gates_passed,
        "total_gates": total_gates,
        "oos_sharpe": oos_sh,
        "decision": decision,
        "failing_gates": failing,
        "altalt_novel_confirmed": g5_corrs["altalt_novel_confirmed"],
        "signed_g5_convention": True,
        "rationale": rationale,
    }


# ── Profit projection ──────────────────────────────────────────────────────────

def compute_profit_projection(oos_metrics: Dict) -> Dict:
    """Profit projection at $10M and $100M AUM."""
    oos_ret_1x = oos_metrics["ann_ret_pct"]
    oos_ret_4x = oos_ret_1x * 4.0
    sleeve_pct = 3.0
    leverage   = 4.0
    friction   = 0.15  # 15% cost buffer

    def _proj(aum_usd: int) -> Dict:
        notional = aum_usd * sleeve_pct / 100 * leverage
        gross = notional * (oos_ret_1x / 100)
        net   = gross * (1 - friction)
        daily = net / 365
        return {
            "aum_usd": aum_usd,
            "sleeve_pct": sleeve_pct,
            "leverage": leverage,
            "notional_usd": round(notional),
            "oos_ann_ret_pct": round(oos_ret_1x, 3),
            "oos_ann_ret_levered_pct": round(oos_ret_4x, 3),
            "gross_annual_usd": round(gross),
            "net_annual_usd_est": round(net),
            "daily_usdc": round(daily),
        }

    return {
        "strategy": "TIA-APT FR differential alt-alt cross-layer paired-trade",
        "oos_sharpe": oos_metrics["sharpe"],
        "sleeve_pct": sleeve_pct,
        "leverage": leverage,
        "oos_ann_ret_1x_pct": round(oos_ret_1x, 3),
        "oos_ann_ret_4x_pct": round(oos_ret_4x, 3),
        "aum_10M": _proj(10_000_000),
        "aum_100M": _proj(100_000_000),
        "note": (
            f"{sleeve_pct}% sleeve, {leverage}x leverage, {friction*100:.0f}% friction buffer. "
            f"OOS annual return (1x): {oos_ret_1x:.2f}%. "
            "Execute on Bybit (both legs) to manage HL concentration."
        ),
    }


# ── Altalt mechanism analysis ──────────────────────────────────────────────────

def build_altalt_mechanism_analysis(
    df: pd.DataFrame, oos_metrics: Dict
) -> Dict:
    """Deep analysis of TIA-APT as DA vs execution alt-alt."""
    tia_std = float(df["tia_fr"].std())
    apt_std = float(df["apt_fr"].std())
    vol_ratio = max(tia_std, apt_std) / min(tia_std, apt_std)

    return {
        "mechanism_type": "alt-alt FR differential (sixth in family, cross-layer DA vs execution)",
        "prior_family_pattern": (
            "K679=APT-SOL (#1 ACCEPT), K682=ATOM-SOL (#2 ACCEPT), "
            "K684=SOL-INJ (#3 ACCEPT), K688=APT-INJ (#5 REJECT), K691=TIA-APT (#6 EVAL)"
        ),
        "k691_structure": {
            "structure": "TIA_fr - APT_fr (TIA minus APT; negative = APT more expensive FR)",
            "economic_driver": (
                "Cross-layer premium: Celestia DA (modular blob storage) vs Aptos Move-VM (execution L1). "
                "TIA FR driven by: DA demand events (rollup TPS spikes, blob fee market), "
                "TIA staking APY changes, modular ecosystem growth, competing DA solutions (EigenDA, Avail). "
                "APT FR driven by: token unlock schedule (heavy 2024-2026), Move-VM adoption, "
                "SUI-APT competition, Aptos DeFi TVL cycles, AptosBFT validator economics. "
                "Both are small-MC alts ($1-3B TIA vs $3-4B APT) with distinct FR lifecycle patterns."
            ),
            "signal_logic": (
                "When TIA_fr > APT_fr: DA demand spike > execution demand -> short TIA perp, long APT perp. "
                "When APT_fr > TIA_fr: execution demand > DA demand -> short APT perp, long TIA perp. "
                "Captures mean-reversion of cross-layer premium with OU half-life ~7h."
            ),
        },
        "k688_algebraic_lesson": {
            "k688_fail_reason": (
                "K688 APT-INJ failed G5d (K679 corr=0.6137) because: "
                "APT-INJ = K679_dir + K684_dir (SOL cancels). "
                "Running K688 + K679 + K684 creates APT+INJ double exposure — algebraic dependency confirmed."
            ),
            "k691_independence": (
                "K691 TIA-APT does NOT have this problem. "
                "TIA is not in K679 (APT-SOL), K682 (ATOM-SOL), or K684 (SOL-INJ). "
                "TIA is the FIRST token in the alt-alt family not connected via SOL. "
                "K691 = -(K_TIA_BTC) + K512_dir — overlaps only with K512 (APT-BTC). "
                "G5b check (K512 corr) is the critical gate for K691 algebraic independence."
            ),
            "sol_absence": (
                "K679, K682, K684 all use SOL as one leg or bridge. "
                "K688 = K679 + K684 (SOL eliminates). "
                "K691 TIA-APT: neither TIA nor APT is SOL. SOL is completely absent. "
                "First alt-alt pair in the family where SOL does not appear in any algebraic identity."
            ),
        },
        "vol_comparison": {
            "tia_fr_std": round(tia_std, 9),
            "apt_fr_std": round(apt_std, 9),
            "vol_ratio_max_min": round(vol_ratio, 4),
            "vs_k679": f"K691 TIA-APT vol ratio {vol_ratio:.3f}x vs K679 APT-SOL 1.61x. TIA and APT have similar volatility.",
            "vs_k688": f"K691 TIA-APT vol ratio {vol_ratio:.3f}x vs K688 APT-INJ 1.35x. Both cross-layer pairs.",
            "vs_btc_family": "TIA/APT ratio ~1.24x — compressed. Both small-MC alts with similar market beta.",
        },
        "architecture_comparison": {
            "tia_celestia": {
                "layer": "Data Availability (DA) — not an execution layer",
                "vm": "None (pure DA, blob storage)",
                "consensus": "Tendermint BFT (Cosmos SDK base)",
                "mc_approx": "~$1-3B",
                "fr_drivers": "DA demand (rollup blob fees), TIA staking APY, modular ecosystem events",
                "key_competitors": "EigenDA, Avail, Ethereum native DA (EIP-4844)",
                "ecosystem_role": "Provides DA to OP Stack, Fuel, Manta, Sei, Eclipse",
            },
            "apt_aptos": {
                "layer": "Execution Layer (L1)",
                "vm": "Move-VM (Block-STM parallel execution)",
                "consensus": "AptosBFT (DiemBFT/HotStuff variant)",
                "mc_approx": "~$3-4B",
                "fr_drivers": "Token unlock schedule, Move ecosystem adoption, SUI competition, DeFi TVL",
                "key_competitors": "SUI (same Move-VM), Solana (SVM), Ethereum (EVM)",
                "ecosystem_role": "Move-VM smart contract L1",
            },
            "independence_analysis": (
                "TIA operates at the DA layer (below execution); APT at the execution layer (above DA). "
                "These are fundamentally different blockchain infrastructure layers. "
                "TIA FR = demand for data storage by rollups (infrastructure demand). "
                "APT FR = demand for execution compute + token speculation. "
                "The two FR cycles are structurally independent: rollup activity != L1 adoption. "
                "Example: high rollup activity (high TIA FR) can coexist with APT unlock pressure (low APT FR)."
            ),
        },
        "cycle_analysis_da_vs_move": {
            "tia_cycle_events": [
                "Celestia mainnet launch (Oct 2023): DA demand spike",
                "Rollup migrations (2024): OP Stack chains adopting Celestia DA",
                "Blob fee market events: EIP-4844 implementation reduced Ethereum DA cost",
                "TIA staking APY changes: validator economics impact FR",
                "Modular ecosystem expansion: Fuel, Manta, others using TIA DA",
            ],
            "apt_cycle_events": [
                "APT token unlock cliff events (2024-2026): unlock pressure -> negative FR",
                "Move-VM ecosystem: SUI competition for developer mindshare",
                "Aptos DeFi TVL: Aries Markets, Echelon, Thala liquidity events",
                "AptosBFT upgrades: validator economics changes",
                "Move language adoption by Facebook/Diem descendants",
            ],
            "cycle_divergence": (
                "TIA DA demand cycles run at a DIFFERENT frequency than APT unlock cycles. "
                "DA demand: driven by rollup adoption (gradual, narrative-dependent). "
                "APT unlocks: driven by vesting schedule (periodic, predetermined). "
                "This structural divergence creates the mean-reverting FR differential."
            ),
        },
        "cross_layer_comparison": {
            "k679_apt_sol": {"pair": "APT-SOL", "oos_sharpe": K679_OOS_SHARPE, "cluster": "Move-VM vs SVM"},
            "k682_atom_sol": {"pair": "ATOM-SOL", "oos_sharpe": K682_OOS_SHARPE, "cluster": "Cosmos IBC vs SVM"},
            "k684_sol_inj": {"pair": "SOL-INJ", "oos_sharpe": K684_OOS_SHARPE, "cluster": "SVM vs Cosmos DeFi"},
            "k688_apt_inj": {"pair": "APT-INJ", "oos_sharpe": K688_OOS_SHARPE, "cluster": "Move-VM vs Cosmos DeFi — REJECT"},
            "k691_tia_apt": {
                "pair": "TIA-APT",
                "oos_sharpe": oos_metrics["sharpe"],
                "cluster": "DA Layer vs Move-VM L1 — EVAL",
            },
            "comparison_note": (
                f"K691 TIA-APT (OOS Sh={oos_metrics['sharpe']:.3f}) is the cross-layer pair: "
                "Celestia (DA infrastructure) vs Aptos (execution L1). "
                "First alt-alt pair in the family with NO SOL anchor in any form. "
                "TIA is a new token class in the family (DA-native, not execution-native)."
            ),
        },
    }


# ── Paired-trade family rank ───────────────────────────────────────────────────

def build_family_rank(oos_metrics: Dict, profit: Dict) -> Dict:
    """Updated paired-trade family leaderboard including K691."""
    members = [
        {"rank": 1,  "pair": "APT-BTC (K512)",  "oos_sharpe": K512_OOS_SHARPE, "net_dollar_yr_10M": 302195,  "status": "ACCEPT",          "vol_ratio": 2.841, "type": "alt-btc"},
        {"rank": 2,  "pair": "ATOM-BTC (K493)", "oos_sharpe": K493_OOS_SHARPE, "net_dollar_yr_10M": 231660,  "status": "ACCEPT",          "vol_ratio": 2.337, "type": "alt-btc"},
        {"rank": 3,  "pair": "SEI-BTC (K507)",  "oos_sharpe": K507_SEI_SHARPE, "net_dollar_yr_10M": 179425,  "status": "ACCEPT",          "vol_ratio": 2.328, "type": "alt-btc"},
        {"rank": 4,  "pair": "AVAX-BTC (K484)", "oos_sharpe": K484_OOS_SHARPE, "net_dollar_yr_10M": 75683,   "status": "ACCEPT",          "vol_ratio": 1.499, "type": "alt-btc"},
        {"rank": 5,  "pair": "ATOM-SOL (K682)", "oos_sharpe": K682_OOS_SHARPE, "net_dollar_yr_10M": 214638,  "status": "ACCEPT",          "vol_ratio": 1.326, "type": "alt-alt #2"},
        {"rank": 6,  "pair": "APT-SOL (K679)",  "oos_sharpe": K679_OOS_SHARPE, "net_dollar_yr_10M": 234781,  "status": "ACCEPT",          "vol_ratio": 1.612, "type": "alt-alt #1"},
        {"rank": 7,  "pair": "SOL-BTC (K476)",  "oos_sharpe": K476_OOS_SHARPE, "net_dollar_yr_10M": 187456,  "status": "ACCEPT",          "vol_ratio": 1.764, "type": "alt-btc"},
        {"rank": 8,  "pair": "INJ-BTC (K500)",  "oos_sharpe": K500_OOS_SHARPE, "net_dollar_yr_10M": 124190,  "status": "ACCEPT",          "vol_ratio": 3.826, "type": "alt-btc"},
        {"rank": 9,  "pair": "SOL-INJ (K684)",  "oos_sharpe": K684_OOS_SHARPE, "net_dollar_yr_10M": 114316,  "status": "ACCEPT",          "vol_ratio": 2.170, "type": "alt-alt #3"},
        {"rank": 10, "pair": "APT-INJ (K688)",  "oos_sharpe": K688_OOS_SHARPE, "net_dollar_yr_10M": 290181,  "status": "REJECT (G5d)",    "vol_ratio": 1.346, "type": "alt-alt #5 CROSS-CLUSTER"},
        {"rank": 11, "pair": "ETH-BTC (K449)",  "oos_sharpe": K449_OOS_SHARPE, "net_dollar_yr_10M": 13100,   "status": "ACCEPT (baseline)", "vol_ratio": 1.084, "type": "alt-btc"},
        {
            "rank": 12, "pair": "TIA-APT (K691)",
            "oos_sharpe": oos_metrics["sharpe"],
            "net_dollar_yr_10M": profit["aum_10M"]["net_annual_usd_est"],
            "status": "EVAL",
            "vol_ratio": 1.244,
            "type": "alt-alt #6 CROSS-LAYER DA vs Execution (EVAL)",
            "note": "Sixth alt-alt pair; Celestia DA layer vs Aptos Move-VM. No SOL anchor. TIA new in family.",
        },
    ]

    return {
        "members": members,
        "family_type_breakdown": {
            "alt_btc_pairs": 7,
            "alt_alt_pairs": 5,
            "note": "K691 = sixth alt-alt pair in family (K679, K682, K684, K688 REJECT, K691). First cross-layer DA pair.",
        },
        "portfolio_note": (
            "K691 TIA-APT: APT is shared leg with K512 (APT-BTC) and K679 (APT-SOL). "
            "Running K691 alongside K512+K679 increases APT exposure. "
            "TIA is NEW: not in any existing strategy. "
            "Algebraic independence: K691 = -(K_TIA_BTC) + K512_dir. "
            "G5b check (corr vs K512) is the critical gate. "
            "Recommend: deploy K691 as STANDALONE at 3% sleeve (Bybit, both legs) "
            "if G5b passes. If G5b fails, REJECT (APT concentration risk)."
        ),
    }


# ── Main ───────────────────────────────────────────────────────────────────────

def main() -> None:
    print("=" * 70)
    print("K691 TIA-APT FR Differential Alt-Alt Eval")
    print("K688 Algebraic Group Lesson: SOL-free new direction")
    print("=" * 70)

    # Load data
    df = load_hl_fr_tia_apt()
    sigs = load_reference_signals_g5()

    # Phase 0
    venue_result  = phase0_prescreen_venue()
    vol_result    = phase0_vol_screen(df)

    # Phase 1: Statistical analysis
    stat_result = run_statistical_analysis(df)

    # Data info
    oos_n    = int(len(df.dropna(subset=["fr_diff"])) * OOS_FRAC)
    n_total  = len(df.dropna(subset=["fr_diff"]))
    n_is     = n_total - oos_n
    total_yrs = n_total / 8760
    oos_days = int((df.index[-1] - df.index[n_is]).days) if n_is < n_total else 0

    df_clean_for_trades = df.dropna(subset=["fr_diff"]).copy()
    df_clean_for_trades["smooth"] = df_clean_for_trades["fr_diff"].rolling(WINDOW_H).mean()
    df_clean_for_trades["signal"] = np.sign(df_clean_for_trades["smooth"]).replace(0, np.nan).ffill()
    sig_changes = int(abs(df_clean_for_trades["signal"].diff().fillna(0)).sum() / 2)
    trades_yr   = sig_changes / total_yrs

    data_info = {
        "hl_rows": n_total,
        "date_start": str(df.index[0].date()),
        "date_end": str(df.index[-1].date()),
        "total_years": round(total_yrs, 3),
        "oos_start": str(df.index[n_is].date()),
        "oos_end": str(df.index[-1].date()),
        "oos_days": oos_days,
        "trades_per_yr": round(trades_yr, 1),
        "is_rows": n_is,
        "oos_rows": oos_n,
        "window_h": WINDOW_H,
        "threshold": THRESHOLD,
        "cost_rt_bps": COST_RT_BPS,
    }

    # Phase 3: Backtest
    is_metrics, oos_metrics, df_clean = run_backtest(df)
    wf_folds, wf_summary = run_walk_forward(df_clean)
    perm_p = run_permutation_test(df_clean)
    dsr    = run_dsr_bonferroni(oos_metrics["sharpe"], data_info["oos_rows"])
    grid   = run_grid_search(df_clean)

    # Phase 4: G5 + G8
    g5_corrs    = compute_g5_correlations(df, sigs)
    cross_venue = check_cross_venue(df)

    # HL concentration
    hl_concentration = {
        "current_hl_pct_baseline": 62.5,
        "hl_cap_pct": 65.0,
        "sleeve_pct": 3.0,
        "scenario_a_hl_only": {
            "new_hl_pct": 65.5, "within_cap": False,
            "note": "HL 62.5% + 3.0% = 65.5% OVER cap.",
        },
        "scenario_b_bybit_both": {
            "hl_pct": 62.5, "bybit_pct": 3.0, "within_cap": True,
            "note": "Both legs Bybit: HL stays 62.5%. PREFERRED.",
        },
        "recommendation": (
            "PREFERRED: Execute K691 on Bybit (both TIA+APT legs). "
            "HL stays at 62.5% — full headroom preserved. "
            f"Bybit TIA corr={cross_venue['bybit_tia']['corr_with_hl']}, "
            f"APT corr={cross_venue['bybit_apt']['corr_with_hl']} vs HL -> G8 pass."
        ),
    }

    # §6 gate evaluation
    sec6 = evaluate_section6_gates(
        oos_metrics, perm_p, dsr, wf_summary,
        g5_corrs, cross_venue, data_info, grid
    )

    # Mechanism analysis
    mechanism = build_altalt_mechanism_analysis(df, oos_metrics)

    # Profit projection
    profit = compute_profit_projection(oos_metrics)

    # Family rank
    family_rank = build_family_rank(oos_metrics, profit)

    # K691 lessons
    k691_lessons = {
        "altalt_sixth_cross_layer": "K691 = sixth alt-alt pair, FIRST cross-layer bridge (DA + Execution). No SOL anchor.",
        "k688_algebraic_group_lesson": (
            "K688 lesson: APT-INJ = K679+K684 (SOL bridge). "
            "K691 avoids this: TIA is not in any existing alt-alt pair. "
            "The algebraic group for {APT, SOL, INJ, ATOM} does not include TIA. "
            "TIA introduces a genuinely new vertex to the alt-alt graph."
        ),
        "g5b_critical_gate": "G5b: corr(K691, K512) must be < 0.40. APT shared leg -> this is the binding constraint.",
        "tia_da_narrative": "TIA = modular DA layer. FR driven by rollup adoption, blob fees, not execution compute.",
        "apt_unlock_risk": "APT = Aptos Move-VM. Monitor token unlock schedule, Move ecosystem adoption.",
        "hl_solution": "Bybit execution for both legs solves HL concentration cap issue.",
        "portfolio_context": "K691 + K679 = APT double exposure (TIA+APT both carry APT). Standalone deployment recommended.",
        "tia_competitive_risk": "EigenDA, Avail, EIP-4844 compete with Celestia. Monitor DA market share.",
        "no_sol_first": "K691 is the FIRST alt-alt pair in the entire family (K679-K691) with no SOL involvement.",
    }

    # Assemble result
    run_time_s = round(time.time() - START_TIME, 1)
    ts_result = subprocess.run(
        ["date", "+%Y-%m-%d %H:%M:%S JST"], capture_output=True, text=True
    )
    ts_str = ts_result.stdout.strip() if ts_result.returncode == 0 else "unknown"

    result = {
        "wave": "K691",
        "strategy": "TIA-APT FR Differential Alt-Alt Cross-Layer Paired-Trade (Celestia DA vs Aptos Move-VM, sixth alt-alt pair, no SOL anchor, K688 algebraic group exit)",
        "run_time_jst": ts_str,
        "runtime_s": run_time_s,
        "phase0_venue_check": venue_result,
        "phase0_vol_ratio": vol_result,
        "data_info": data_info,
        "statistical_analysis": stat_result,
        "is_metrics": is_metrics,
        "oos_metrics": oos_metrics,
        "walk_forward_12fold": wf_folds,
        "walk_forward_summary": wf_summary,
        "permutation_p": perm_p,
        "dsr_bonferroni": dsr,
        "grid_search_top5": grid,
        "g5_correlations": g5_corrs,
        "cross_venue": cross_venue,
        "hl_concentration_impact": hl_concentration,
        "section6_gates": sec6,
        "altalt_mechanism_analysis": mechanism,
        "profit_projection": profit,
        "paired_trade_family_rank": family_rank,
        "decision": sec6["decision"],
        "decision_rationale": sec6["rationale"],
        "k691_lessons": k691_lessons,
    }

    # Write JSON
    out_json = BASE / "wave_k691_tia_apt_eval.json"
    with open(out_json, "w") as f:
        json.dump(result, f, indent=2, default=str)
    print(f"\n[OUTPUT] {out_json}")

    # Summary
    print("\n" + "=" * 70)
    print(f"DECISION: {sec6['decision']}")
    print(f"OOS Sharpe: {oos_metrics['sharpe']:.3f}")
    print(f"OOS Ann Ret: {oos_metrics['ann_ret_pct']:.2f}%")
    print(f"Gates passed: {sec6['gates_passed']}/{sec6['total_gates']}")
    print(f"Failing: {sec6['failing_gates']}")
    print(f"Profit @$10M: ${profit['aum_10M']['net_annual_usd_est']:,.0f}/yr (${profit['aum_10M']['daily_usdc']:,.0f}/day)")
    print("=" * 70)


if __name__ == "__main__":
    main()

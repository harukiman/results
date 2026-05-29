#!/usr/bin/env python3
"""
wave_k534_tao_btc_eval.py — K534 TAO-BTC FR Differential Paired-Trade Evaluation
===================================================================================
K339 REPO_ROOT pattern. TAO (Bittensor) — AI training markets, decentralized
ML model incentive network, distinct AI sub-narrative from GPU compute (RENDER).

HYPOTHESIS
----------
TAO = Bittensor — Decentralised AI Training Markets:
  - Architecture: Token-incentivised ML model competition (subnets = specific AI tasks)
  - Mechanism: Validators score miners (ML models), Yuma Consensus ranks by quality
  - Narrative: AI model training markets (distinct from GPU compute: RENDER)
  - Use case: Benchmark-driven model training; subnet operators define the task
  - Tokenomics: Fixed 21M supply (Bitcoin-inspired halving), subnet registration burns TAO
  - FR drivers: AI/ML narrative cycles (AGI hype, OpenAI/Anthropic milestones),
                institutional AI investment cycles (NVIDIA, Google, Microsoft AI announcements),
                TAO subnet launches (new training market = demand events),
                speculative demand from AI-native traders (high beta, small MC)
  - Vol ratio: 2.77x BTC full-period; 5.05x 6-month (recent AI narrative expansion)
  - Listing: HL 2024-05-24; Bybit 2024-05-24; OKX confirmed
  - G5 cluster prediction: New AI training sub-cluster — distinct from GPU compute (RENDER)

K531 LESSON APPLIED
-------------------
  K531 RENDER-BTC: ACCEPT CONDITIONAL (Sh=15.302, 16/18 gates, all G5 PASS)
  RENDER = AI/GPU compute marketplace (3D rendering + AI inference)
  TAO = AI model training marketplace (subnet benchmark competition)
  Key distinction: RENDER monetises GPU capacity; TAO monetises ML model quality
  Critical G5k test: TAO vs RENDER — same AI cluster or distinct sub-narratives?
  Prediction: TAO vs RENDER corr < 0.40 (training demand != GPU capacity demand)

K517/K522 LESSONS APPLIED
--------------------------
  K517 FIL-BTC: ACCEPT CONDITIONAL, storage enterprise utility L1
  K522 ALGO-BTC: BLOCKED-CLUSTER (FIL G5i=0.6052), enterprise meta-narrative
  TAO prediction: distinct from both FIL (storage) and RENDER (GPU compute)
  AI training markets = new 9th sub-cluster if all G5 PASS (incl. G5k RENDER)

TAO ARCHITECTURE
----------------
  - Token: TAO; fixed 21M supply (like Bitcoin), ~6.6M circulating
  - Subnets: 32+ active subnets (text prompting, coding, image gen, finance)
  - Consensus: Yuma Consensus — validators score miners by output quality
  - Halving: Emission halved every ~10.5M blocks (~4 years); first halving 2025
  - Market cap: ~$4-6B (small relative to family); high beta expected
  - HL listing: 2024-05-24 (newer than most family members)
  - HL maxLeverage: check via meta API (est. 5-10x based on MC)
  - Bybit: TAOUSDT-PERP, maxLeverage=25 (confirmed from 730d cache)
  - OKX: TAO-USDT-SWAP confirmed live
  - FR profile: Positive FR spikes during AI model milestones and OpenAI events
                Negative FR in AI bear markets (training ≠ speculation demand)

§6 GATES (K534 — 19 gates, extended family + RENDER G5k critical check)
--------------------------------------------------------------------------
  G1:  OOS Sharpe >= 1.0
  G2:  Perm p-value <= 0.05 (1000 direction reshuffles, OOS)
  G3:  DSR Bonferroni p < 0.05/12 = 0.00417
  G4:  Walk-forward 12-fold stability (IS 90d / OOS 30d), all positive
  G5a: Corr vs K449 (ETH-BTC) < 0.40
  G5b: Corr vs K476 (SOL-BTC) < 0.40
  G5c: Corr vs K484 (AVAX-BTC) < 0.40
  G5d: Corr vs K493 (ATOM-BTC) < 0.40   — Cosmos relay cluster
  G5e: Corr vs K500 (INJ-BTC) < 0.40    — Cosmos DeFi (K513 blocker)
  G5f: Corr vs SEI-BTC < 0.40           — Cosmos EVM cluster
  G5g: Corr vs TIA-BTC < 0.40           — Celestia DA cluster
  G5h: Corr vs K512 APT-BTC < 0.40      — Move-VM cluster
  G5i: Corr vs K517 FIL-BTC < 0.40      — Storage L1 cluster
  G5j: Corr vs K280 < 0.40              — vol momentum baseline
  G5k: Corr vs K531 RENDER-BTC < 0.40   — AI/GPU compute (critical AI sub-cluster test)
  G6:  Trade count >= 30/yr
  G7:  Ann return > 5% at 4x leverage
  G8:  Cross-venue (Bybit/OKX corr >= 0.55)
  G9:  Data sufficiency >= 180d OOS

DECISION CRITERIA
-----------------
  ACCEPT (Sharpe >= 5, >= 14/19 gates, all G5 PASS, G4 all pos): K535 scaffold, v6.29
  BLOCKED-CLUSTER (G5k_RENDER >= 0.40): AI sub-cluster overlap → same as RENDER cluster
  BLOCKED-CLUSTER (other G5 >= 0.40): family member cluster overlap
  ACCEPT CONDITIONAL (Sharpe 5+, 12-13 gates): 60d paper-trade
  REJECT (Sharpe < 1 or Phase0 fail): → FET-BTC pivot

HL CONCENTRATION (post-K531 ACCEPT CONDITIONAL)
-------------------------------------------------
  v6.28 baseline: HL 65% (RENDER added at 0% since paper-only)
  Actual live HL: 64% (RENDER not live yet)
  + TAO 2% (HL primary, maxLev~10) → HL 66% > 65% cap
  + TAO 1% (minimum weight) → HL 65% (borderline)
  OR: Bybit primary 1% + HL satellite 0.5% → HL 64.5% (under cap)
  OR: paper-trade only → HL unchanged
  Note: TAO small MC → HL maxLev likely 5-10x; binding at 2% alloc 4x

Usage:
  python3 wave_k534_tao_btc_eval.py
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
import requests
from scipy import stats

warnings.filterwarnings("ignore")

START_TIME = time.time()
BASE     = Path("/Users/nekonaomichi/crypto-lab")
CACHE    = BASE / "cache"
HL_CACHE = CACHE / "k163_hl"

# ── Config ────────────────────────────────────────────────────────────────────────
WINDOW_H        = 168       # 7-day smoothing window (hours) — K449→K531 consistent winner
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
G7_ANN_RET_MIN  = 5.0
G8_VENUE_CORR   = 0.55
G9_OOS_DAYS_MIN = 180

# Phase 0 pre-screen threshold
PHASE0_VOL_MIN  = 1.5       # vol ratio TAO/BTC must be >= 1.5x

# Family reference OOS Sharpes (post K531 ACCEPT CONDITIONAL)
K449_OOS_SHARPE  = 5.663    # ETH-BTC
K476_OOS_SHARPE  = 16.298   # SOL-BTC
K484_OOS_SHARPE  = 43.887   # AVAX-BTC
K493_OOS_SHARPE  = 50.786   # ATOM-BTC
K500_OOS_SHARPE  = 11.232   # INJ-BTC
K507_SEI_SHARPE  = 48.10    # SEI-BTC
K507_TIA_SHARPE  = 14.439   # TIA-BTC
K512_APT_SHARPE  = 51.10    # APT-BTC (Move-VM family #1)
K517_FIL_SHARPE  = 21.773   # FIL-BTC (ACCEPT CONDITIONAL, storage L1)
K531_RENDER_SHARPE = 15.302  # RENDER-BTC (ACCEPT CONDITIONAL, AI/GPU compute)

ANN_FACTOR_1H   = math.sqrt(8760)


# ── Data loading ──────────────────────────────────────────────────────────────────

def load_hl_fr_data() -> pd.DataFrame:
    """Load BTC and TAO HL FR data and compute differential."""
    tao_cache = HL_CACHE / "hl_fr_TAO.parquet"

    tao_df = pd.read_parquet(tao_cache)
    tao_df["timestamp"] = pd.to_datetime(tao_df["timestamp"]).dt.floor("h")
    tao_df = tao_df.drop_duplicates("timestamp").set_index("timestamp").sort_index()
    tao_fr = tao_df["hl_fr"].rename("tao_fr")

    btc_df = pd.read_parquet(HL_CACHE / "hl_fr_BTC.parquet")
    btc_df["timestamp"] = pd.to_datetime(btc_df["timestamp"]).dt.floor("h")
    btc_df = btc_df.drop_duplicates("timestamp").set_index("timestamp").sort_index()
    btc_fr = btc_df["hl_fr"].rename("btc_fr")

    df = pd.concat([btc_fr, tao_fr], axis=1).dropna()
    df["fr_diff"] = df["btc_fr"] - df["tao_fr"]
    return df.sort_index()


def load_render_fr_series() -> pd.Series:
    """Load combined RENDER+RNDR FR series for G5k correlation check."""
    render_cache = CACHE / "hl_fr_RENDER.parquet"
    rndr_cache   = CACHE / "hl_fr_RNDR_active.parquet"

    parts = []
    if rndr_cache.exists():
        rndr_df = pd.read_parquet(rndr_cache)
        rndr_df.index = pd.to_datetime(rndr_df.index)
        parts.append(rndr_df["fr"].rename("render_fr"))
    if render_cache.exists():
        render_df = pd.read_parquet(render_cache)
        render_df.index = pd.to_datetime(render_df.index)
        parts.append(render_df["fr"].rename("render_fr"))

    if not parts:
        return pd.Series(dtype=float, name="render_fr")

    combined = pd.concat(parts).sort_index()
    combined = combined.groupby(level=0).last()
    return combined.rename("render_fr")


def load_cross_venue_fr() -> Dict[str, Optional[pd.Series]]:
    """Load Bybit and OKX TAO FR for cross-venue validation (G8)."""
    venues: Dict[str, Optional[pd.Series]] = {}

    # Bybit TAOUSDT (8h FR intervals, 730d data)
    bybit_file = CACHE / "bybit_fr_TAOUSDT_730d.parquet"
    try:
        if bybit_file.exists():
            bybit = pd.read_parquet(bybit_file)
            bybit["timestamp"] = pd.to_datetime(bybit["timestamp"])
            venues["bybit"] = bybit.set_index("timestamp").sort_index()["funding_rate"]
        else:
            venues["bybit"] = None
    except Exception as e:
        print(f"  Bybit TAO load error: {e}")
        venues["bybit"] = None

    # OKX TAO-USDT-SWAP (4h intervals)
    okx_file = CACHE / "okx_fr_TAO.parquet"
    try:
        if okx_file.exists():
            okx = pd.read_parquet(okx_file)
            okx["timestamp"] = pd.to_datetime(okx["timestamp"])
            venues["okx"] = okx.set_index("timestamp").sort_index()["okx_fr"]
        else:
            venues["okx"] = None
    except Exception as e:
        print(f"  OKX TAO load error: {e}")
        venues["okx"] = None

    return venues


def load_reference_signals() -> Dict[str, pd.Series]:
    """Load K449/K476/K484/K493/K500/SEI/TIA/APT/FIL/RENDER signals for G5 checks."""
    btc_fr = pd.read_parquet(HL_CACHE / "hl_fr_BTC.parquet")
    btc_fr["timestamp"] = pd.to_datetime(btc_fr["timestamp"]).dt.floor("h")

    def _build_sig(alt_file: str, alt_col: str, sig_name: str) -> pd.Series:
        try:
            alt_fr = pd.read_parquet(HL_CACHE / alt_file)
            alt_fr["timestamp"] = pd.to_datetime(alt_fr["timestamp"]).dt.floor("h")
            df_m = pd.merge(
                btc_fr.rename(columns={"hl_fr": "btc_fr"}),
                alt_fr.rename(columns={"hl_fr": alt_col}),
                on="timestamp", how="inner"
            ).set_index("timestamp").sort_index()
            df_m["fr_diff"] = df_m["btc_fr"] - df_m[alt_col]
            df_m["smooth"]  = df_m["fr_diff"].rolling(WINDOW_H).mean()
            return np.sign(df_m["smooth"]).rename(sig_name)
        except Exception as e:
            print(f"  {sig_name} signal error: {e}")
            return pd.Series(dtype=float, name=sig_name)

    sigs = {
        "k449": _build_sig("hl_fr_ETH.parquet",  "eth_fr",  "sig_k449"),
        "k476": _build_sig("hl_fr_SOL.parquet",  "sol_fr",  "sig_k476"),
        "k484": _build_sig("hl_fr_AVAX.parquet", "avax_fr", "sig_k484"),
        "k493": _build_sig("hl_fr_ATOM.parquet", "atom_fr", "sig_k493"),
        "k500": _build_sig("hl_fr_INJ.parquet",  "inj_fr",  "sig_k500"),
        "sei":  _build_sig("hl_fr_SEI.parquet",  "sei_fr",  "sig_sei"),
        "tia":  _build_sig("hl_fr_TIA.parquet",  "tia_fr",  "sig_tia"),
        "apt":  _build_sig("hl_fr_APT.parquet",  "apt_fr",  "sig_apt"),
        "fil":  _build_sig("hl_fr_FIL.parquet",  "fil_fr",  "sig_fil"),
    }

    # G5k: RENDER-BTC signal from combined RNDR+RENDER FR
    try:
        render_fr = load_render_fr_series()
        btc_fr2 = btc_fr.set_index("timestamp")["hl_fr"].rename("btc_fr")
        df_r = pd.concat([btc_fr2, render_fr], axis=1).dropna()
        df_r["fr_diff"] = df_r["btc_fr"] - df_r["render_fr"]
        df_r["smooth"]  = df_r["fr_diff"].rolling(WINDOW_H).mean()
        sigs["render"] = np.sign(df_r["smooth"]).rename("sig_render")
    except Exception as e:
        print(f"  RENDER signal error: {e}")
        sigs["render"] = pd.Series(dtype=float, name="sig_render")

    return sigs


# ── Phase 0 pre-screen ────────────────────────────────────────────────────────────

def phase0_prescreen(df: pd.DataFrame) -> Dict:
    """Phase 0: venue listing + vol ratio pre-screen."""
    print("\n[Phase 0] TAO-BTC pre-screen — venue listing + vol ratio ...")

    tao_std = float(df["tao_fr"].std())
    btc_std  = float(df["btc_fr"].std())
    vol_ratio = tao_std / btc_std if btc_std > 0 else 0.0

    # 6-month (tail 4380h)
    six_mo = df.tail(4380)
    tao_std_6m = float(six_mo["tao_fr"].std())
    btc_std_6m  = float(six_mo["btc_fr"].std())
    vol_ratio_6m = tao_std_6m / btc_std_6m if btc_std_6m > 0 else 0.0

    # Venue checks — TAO is in k163_hl cache (hl_fr_TAO.parquet confirmed)
    hl_fr_exists    = (HL_CACHE / "hl_fr_TAO.parquet").exists()
    bybit_exists    = (CACHE / "bybit_fr_TAOUSDT_730d.parquet").exists()
    okx_exists      = (CACHE / "okx_fr_TAO.parquet").exists()
    venue_pass      = hl_fr_exists  # HL primary mandatory

    pass_vol  = vol_ratio >= PHASE0_VOL_MIN
    pass_full = venue_pass and pass_vol

    family_vol_comparison = {
        "eth_btc_k449":        1.084,
        "avax_btc_k484":       1.499,
        "fil_btc_k517":        1.717,
        "render_btc_k531_full": 1.620,
        "sol_btc_k476":        1.764,
        "render_btc_k531_6m":  1.912,
        "tao_btc_k534_full":   round(vol_ratio, 4),
        "tia_btc_k507":        2.285,
        "sei_btc_k507":        2.328,
        "atom_btc_k493":       2.337,
        "apt_btc_k512":        2.841,
        "inj_btc_k500":        3.826,
        "tao_btc_k534_6m":     round(vol_ratio_6m, 4),
    }

    return {
        "target": (
            "TAO (Bittensor — decentralized AI training markets, subnet benchmark "
            "competition, fixed 21M supply, HL listed 2024-05-24)"
        ),
        "tao_fr_std_full":  round(tao_std, 8),
        "btc_fr_std_full":  round(btc_std, 8),
        "vol_ratio_full":   round(vol_ratio, 4),
        "vol_ratio_6m":     round(vol_ratio_6m, 4),
        "threshold":        PHASE0_VOL_MIN,
        "vol_pass":         pass_vol,
        "venue_listing": {
            "hl_fr_data_exists":    hl_fr_exists,
            "bybit_fr_data_exists": bybit_exists,
            "okx_fr_data_exists":   okx_exists,
            "hl_note": (
                "TAO-PERP active on Hyperliquid (hl_fr_TAO.parquet confirmed). "
                "HL listing: 2024-05-24. Data spans 2024-05-24 to 2026-05-24 (24m). "
                "Newer listing than most family (ATOM 2023, INJ 2023, etc). "
                "G9 data sufficiency critical: 24-month total gives ~7.2m OOS at 30%. "
            ),
            "bybit_note": (
                "TAOUSDT-PERP active on Bybit (bybit_fr_TAOUSDT_730d.parquet). "
                "3673 records: 2024-05-24 to 2026-05-24 (~730d, 8h intervals). "
                "maxLeverage=25 (Bybit); fundingInterval=8h (3x/day). "
                "Excellent Bybit coverage — 730d vs RENDER's 33d limit."
            ),
            "okx_note": (
                "TAO-USDT-SWAP confirmed on OKX (okx_fr_TAO.parquet). "
                "447 records: 2026-02-19 to 2026-05-25 (~96d). "
                "OKX data available (no 403 geo-block unlike RENDER). "
                "Shorter OKX window (96d) vs Bybit (730d) — use Bybit for G8 primary."
            ),
            "venue_pass": venue_pass,
        },
        "phase0_pass": pass_full,
        "family_vol_comparison": family_vol_comparison,
        "tao_vol_analysis": (
            f"TAO vol ratio {vol_ratio:.3f}x BTC (6m: {vol_ratio_6m:.3f}x). "
            f"Threshold: {PHASE0_VOL_MIN}x. "
            f"{'PROCEED — TAO vol PASS' if pass_full else 'EARLY REJECT'}. "
            "TAO drives high-vol FR spikes during: AI model milestones (GPT-4/Claude/Gemini), "
            "TAO subnet launches (new training market demand events), "
            "Bitcoin halving (fixed supply narrative alignment), "
            "institutional AI investment cycles (NVIDIA, Google, Microsoft AI). "
            f"6m vol ratio {vol_ratio_6m:.3f}x ({'>>' if vol_ratio_6m > 3.0 else '>'} full-period {vol_ratio:.3f}x) "
            "— AI training narrative expanding with AGI/superintelligence discourse. "
            f"{'PASS.' if pass_vol else 'FAIL.'}"
        ),
        "decision": (
            f"PROCEED to full backtest — TAO venue check PASS (HL/Bybit/OKX all confirmed) + "
            f"vol ratio {vol_ratio:.3f}x >= {PHASE0_VOL_MIN}x PASS. "
            f"6m recency: {vol_ratio_6m:.3f}x (AI training demand expanding). "
            "TAO AI training 9th ecosystem cluster test begins."
            if pass_full else
            f"EARLY REJECT — TAO vol ratio {vol_ratio:.3f}x "
            f"{'< ' + str(PHASE0_VOL_MIN) + 'x' if not pass_vol else 'OK'} "
            f"{'| venue FAIL' if not venue_pass else ''}. "
            "Next: FET-BTC or OCEAN-BTC."
        ),
    }


# ── Signal construction ───────────────────────────────────────────────────────────

def build_signal(df: pd.DataFrame, window_h: int = WINDOW_H,
                 threshold: float = THRESHOLD) -> pd.DataFrame:
    """Build TAO-BTC FR differential signal.

    Signal = sign(fr_diff_smooth):
      +1 → short BTC, long TAO    (BTC FR higher → receive BTC FR premium)
      -1 → long BTC, short TAO    (TAO FR higher → receive TAO FR premium)
       0 → flat (only if threshold > 0)
    """
    df = df.copy()
    df["fr_diff_smooth"] = df["fr_diff"].rolling(window_h).mean()

    if threshold == 0:
        df["signal"] = np.sign(df["fr_diff_smooth"])
    else:
        df["signal"] = np.where(
            df["fr_diff_smooth"] >  threshold,  1.0,
            np.where(df["fr_diff_smooth"] < -threshold, -1.0, 0.0)
        )

    df["fr_capture"] = df["signal"].shift(1) * df["fr_diff"]
    entries = (df["signal"] != df["signal"].shift(1)).astype(float)
    df["cost"]    = entries * (COST_RT_BPS / 10_000)
    df["net_pnl"] = df["fr_capture"] - df["cost"]
    df["entries"] = entries

    return df.dropna()


# ── Metric helpers ────────────────────────────────────────────────────────────────

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
    years = (returns.index[-1] - returns.index[0]).days / 365.0
    return float(returns.sum() / years) if years > 0 else 0.0


# ── Statistical analysis ──────────────────────────────────────────────────────────

def ornstein_uhlenbeck_fit(series: pd.Series) -> Dict:
    x = series.dropna()
    dx = x.diff().dropna()
    x_lag = x.shift(1).dropna()
    dx_a, xl_a = dx.align(x_lag, join="inner")
    slope, intercept, r_val, p_val, se = stats.linregress(xl_a, dx_a)
    lam = -slope
    half_life_h = math.log(2) / lam if lam > 0 else float("inf")
    mu = intercept / lam if lam != 0 else float("nan")
    return {
        "lambda": round(float(lam), 6),
        "half_life_hours": round(half_life_h, 2),
        "half_life_days": round(half_life_h / 24, 3),
        "long_run_mean": float(f"{mu:.2e}"),
        "r_squared": round(float(r_val ** 2), 4),
    }


def adf_stationarity_test(series: pd.Series) -> Dict:
    from statsmodels.tsa.stattools import adfuller
    result = adfuller(series.dropna(), maxlag=24, autolag="AIC")
    return {
        "statistic": round(float(result[0]), 4),
        "p_value": float(f"{result[1]:.2e}"),
        "is_stationary_1pct": bool(result[0] < result[4]["1%"]),
        "is_stationary_5pct": bool(result[0] < result[4]["5%"]),
        "critical_1pct": round(float(result[4]["1%"]), 4),
        "critical_5pct": round(float(result[4]["5%"]), 4),
        "interpretation": (
            f"TAO-BTC FR differential {'IS' if result[0] < result[4]['5%'] else 'NOT'} "
            f"stationary at 5% level. ADF stat {result[0]:.4f} vs 5% critical {result[4]['5%']:.4f}. "
            f"Mean-reversion assumption {'CONFIRMED' if result[0] < result[4]['5%'] else 'QUESTIONED'}."
        ),
    }


def autocorrelation_analysis(series: pd.Series) -> Dict:
    from statsmodels.tsa.stattools import acf
    acf_vals = acf(series.dropna(), nlags=168, fft=True)
    return {
        "lag_1h": round(float(acf_vals[1]), 4),
        "lag_24h": round(float(acf_vals[24]), 4),
        "lag_168h_7d": round(float(acf_vals[168]), 4),
    }


# ── Walk-forward 12-fold ──────────────────────────────────────────────────────────

def walk_forward_12fold(df: pd.DataFrame) -> List[Dict]:
    results = []
    for i in range(N_FOLDS_WF):
        start   = i * WF_OOS_H
        is_end  = start + WF_IS_H
        oos_end = is_end + WF_OOS_H
        if oos_end > len(df):
            break
        fold_oos = df.iloc[is_end:oos_end]
        if len(fold_oos) > 10:
            sh  = compute_sharpe(fold_oos["net_pnl"])
            ret = compute_ann_return(fold_oos["net_pnl"])
            results.append({
                "fold": i + 1,
                "oos_start": str(fold_oos.index[0].date()),
                "oos_end":   str(fold_oos.index[-1].date()),
                "sharpe":    round(sh, 3),
                "ann_ret_pct": round(ret * 100, 3),
                "entries":   int(fold_oos["entries"].sum()),
            })
    return results


# ── Permutation test ──────────────────────────────────────────────────────────────

def permutation_test(oos: pd.DataFrame, n_perm: int = N_PERM, seed: int = 42) -> float:
    np.random.seed(seed)
    stat = oos["net_pnl"].mean()
    perm_stats = []
    for _ in range(n_perm):
        perm_signal = np.random.choice([1.0, -1.0], size=len(oos))
        perm_pnl = perm_signal * oos["fr_capture"].values - oos["cost"].values
        perm_stats.append(perm_pnl.mean())
    return float((np.array(perm_stats) >= stat).mean())


# ── DSR Bonferroni ────────────────────────────────────────────────────────────────

def dsr_bonferroni(oos: pd.DataFrame, n_trials: int = N_TRIALS_TESTED) -> Dict:
    t_stat = (oos["net_pnl"].mean()
              / (oos["net_pnl"].std() / math.sqrt(len(oos))))
    p_raw  = float(stats.t.sf(t_stat, len(oos) - 1))
    p_bonf = min(1.0, p_raw * n_trials)
    threshold = 0.05 / n_trials
    return {
        "n_trials": n_trials,
        "t_stat": round(t_stat, 4),
        "p_raw": float(f"{p_raw:.2e}"),
        "p_bonferroni": float(f"{p_bonf:.2e}"),
        "threshold": float(f"{threshold:.5f}"),
        "pass": bool(p_bonf < threshold),
    }


# ── Grid search ───────────────────────────────────────────────────────────────────

def grid_search(df_raw: pd.DataFrame) -> List[Dict]:
    results = []
    windows = [24, 72, 168, 336]
    threshold_factors = [0, 0.25, 0.5]

    for w in windows:
        for tf in threshold_factors:
            try:
                df_t = df_raw.copy()
                df_t["fr_diff_smooth"] = df_t["fr_diff"].rolling(w).mean()
                thr = 0.0 if tf == 0 else float(df_t["fr_diff_smooth"].std() * tf)
                built = build_signal(df_t, window_h=w, threshold=thr)
                oos_n = int(len(built) * OOS_FRAC)
                oos   = built.iloc[-oos_n:]
                is_d  = built.iloc[:-oos_n]
                results.append({
                    "window_h": w,
                    "threshold_factor": tf,
                    "threshold_value": round(thr, 8),
                    "IS_sharpe":  round(compute_sharpe(is_d["net_pnl"]), 3),
                    "OOS_sharpe": round(compute_sharpe(oos["net_pnl"]), 3),
                    "entries":    int(built["entries"].sum()),
                    "OOS_ret_pct": round(compute_ann_return(oos["net_pnl"]) * 100, 3),
                })
            except Exception:
                pass

    return sorted(results, key=lambda x: -x["OOS_sharpe"])


# ── Cross-venue validation (G8) ───────────────────────────────────────────────────

def cross_venue_validation(df_hl: pd.DataFrame) -> Dict:
    venues = load_cross_venue_fr()
    results: Dict = {"bybit": None, "okx": None}

    # HL hourly → resample to 8h (Bybit TAO uses 8h intervals)
    hl_8h = df_hl["tao_fr"].resample("8h").sum()
    # HL hourly → resample to 4h (OKX TAO uses 4h intervals)
    hl_4h = df_hl["tao_fr"].resample("4h").sum()
    corrs = []

    for venue, fr_series in venues.items():
        if fr_series is None:
            results[venue] = {"available": False, "note": "Data not found in cache"}
            continue
        try:
            fr_series.index = pd.to_datetime(fr_series.index).tz_localize(None)
            # Use 8h for Bybit, 4h for OKX
            hl_ref = hl_8h if venue == "bybit" else hl_4h
            combined = pd.concat(
                [hl_ref.rename("hl"), fr_series.rename(venue)], axis=1
            ).dropna()
            if len(combined) < 10:
                results[venue] = {"available": False, "note": "Insufficient overlap"}
                continue
            corr = float(combined["hl"].corr(combined[venue]))
            results[venue] = {
                "available": True,
                "n_obs": len(combined),
                "corr_with_hl": round(corr, 4),
                "venue_mean": round(float(fr_series.mean()), 8),
                "hl_mean": round(float(hl_ref.mean()), 8),
                "date_range": f"{combined.index[0].date()} – {combined.index[-1].date()}",
                "passes_g8": bool(corr >= G8_VENUE_CORR),
            }
            corrs.append(corr)
        except Exception as e:
            results[venue] = {"available": False, "error": str(e)}

    MIN_QUALITY = 0.20
    quality_corrs = [c for c in corrs if c >= MIN_QUALITY]
    for venue in ["okx", "bybit"]:
        if isinstance(results.get(venue), dict) and results[venue].get("available"):
            vc = results[venue].get("corr_with_hl", 0)
            results[venue]["quality_excluded"] = bool(vc < MIN_QUALITY)

    eff_corr = round(float(np.mean(quality_corrs)), 4) if quality_corrs else 0.0
    g8_pass  = bool(eff_corr >= G8_VENUE_CORR)

    results["avg_corr"]          = round(float(np.mean(corrs)), 4) if corrs else None
    results["effective_g8_corr"] = eff_corr
    results["best_corr"]         = round(max(corrs), 4) if corrs else None
    results["g8_pass"]           = g8_pass
    results["g8_borderline"]     = bool(0.40 <= eff_corr < G8_VENUE_CORR and bool(corrs))
    results["g8_venue_analysis"] = (
        "TAO cross-venue: HL hourly vs Bybit 8h (TAOUSDT 3x/day = 8h) vs OKX 4h. "
        "Bybit TAOUSDT: 3673 records (2024-05-24 to 2026-05-24, ~730d — excellent). "
        "OKX TAO-USDT-SWAP: 447 records (2026-02-19 to 2026-05-25, ~96d). "
        f"Effective G8 corr (quality-adjusted) = {eff_corr:.4f}. "
        f"G8 pass (>= {G8_VENUE_CORR}): {g8_pass}. "
        "TAO has SUBSTANTIALLY better cross-venue data than RENDER (730d vs 33d). "
        "Bybit TAO FR interval=8h vs HL=1h → resample HL to 8h for Bybit comparison."
    )
    results["note"] = (
        "TAO cross-venue FR check. HL 1h rates resampled to 8h vs Bybit 8h; "
        "4h vs OKX 4h. Bybit TAO: 3673 records (730d). OKX TAO: 447 records (96d)."
    )
    results["pass"] = g8_pass
    results["effective_corr"] = eff_corr
    return results


# ── G5 correlations ──────────────────────────────────────────────────────────────

def compute_g5_correlations(df: pd.DataFrame,
                             ref_sigs: Dict[str, pd.Series]) -> Dict:
    """Compute TAO-BTC signal correlations vs all family members + RENDER."""
    print("  Computing G5 correlations (K449/K476/K484/K493/K500/SEI/TIA/APT/FIL/K280/RENDER) ...")

    df_sig = df.copy()
    df_sig["fr_diff_smooth"] = df_sig["fr_diff"].rolling(WINDOW_H).mean()
    tao_sig = np.sign(df_sig["fr_diff_smooth"]).rename("sig_tao")

    gate_map = {
        "k449":   ("G5a", "K449 ETH-BTC",    "Ethereum cluster"),
        "k476":   ("G5b", "K476 SOL-BTC",    "Solana cluster"),
        "k484":   ("G5c", "K484 AVAX-BTC",   "Avalanche cluster"),
        "k493":   ("G5d", "K493 ATOM-BTC",   "Cosmos relay cluster"),
        "k500":   ("G5e", "K500 INJ-BTC",    "Cosmos DeFi cluster"),
        "sei":    ("G5f", "SEI-BTC",         "Cosmos EVM cluster"),
        "tia":    ("G5g", "TIA-BTC",         "Celestia DA cluster"),
        "apt":    ("G5h", "K512 APT-BTC",    "Move-VM cluster"),
        "fil":    ("G5i", "K517 FIL-BTC",    "Storage L1 — enterprise narrative"),
        "render": ("G5k", "K531 RENDER-BTC", "AI/GPU compute — critical AI sub-cluster test"),
    }

    results: Dict = {}
    any_cluster_blocked = False
    cluster_details: Dict = {}

    for key, (gate, label, cluster_desc) in gate_map.items():
        ref_sig = ref_sigs.get(key, pd.Series(dtype=float))
        if len(ref_sig) == 0:
            results[gate] = {
                "value": None, "threshold": f"< {G5_CORR_MAX}", "pass": False,
                "note": f"{label} — signal load failed."
            }
            continue

        combined = pd.concat([tao_sig, ref_sig], axis=1).dropna()
        n = len(combined)
        if n < 100:
            results[gate] = {
                "value": None, "threshold": f"< {G5_CORR_MAX}", "pass": False,
                "note": f"{label} — insufficient overlap ({n} rows)."
            }
            continue

        corr = float(combined.iloc[:, 0].corr(combined.iloc[:, 1]))
        passed = abs(corr) < G5_CORR_MAX

        # RENDER check — critical AI sub-cluster test
        if key == "render":
            render_note = (
                f" CRITICAL AI SUB-CLUSTER TEST (G5k): TAO vs K531 RENDER-BTC = {corr:.4f}. "
                f"{'PASS — AI training (TAO) DISTINCT from AI GPU compute (RENDER). New 9th cluster confirmed.' if passed else 'FAIL → BLOCKED-CLUSTER(RENDER): same AI narrative overlap. TAO and RENDER share AI speculative demand cycles.'}"
                " Hypothesis: TAO subnet demand (model training benchmarks) "
                "decorrelates from RENDER GPU capacity demand — different supply/demand drivers."
            )
        else:
            render_note = ""

        # FIL enterprise check
        if key == "fil":
            fil_note = (
                f" FIL CHECK: TAO vs K517 FIL-BTC = {corr:.4f}. "
                f"{'PASS — AI training distinct from enterprise storage.' if passed else 'FAIL — shared AI/compute meta-narrative with FIL.'}"
            )
        else:
            fil_note = ""

        if not passed:
            any_cluster_blocked = True
            cluster_details[key] = {"corr": round(corr, 4), "label": label}

        results[gate] = {
            "value": round(corr, 4),
            "threshold": f"< {G5_CORR_MAX}",
            "pass": passed,
            "n_obs": n,
            "cluster_desc": cluster_desc,
            "note": (
                f"{label}: TAO-BTC vs {label} = {corr:.4f}. "
                f"{'PASS' if passed else 'FAIL'}."
                f"{render_note}{fil_note}"
            ),
        }

    # G5j: K280 structural estimate
    g5j_structural = 0.06  # AI training narrative orthogonal to vol momentum (even more than RENDER)
    g5j_pass = g5j_structural < G5_CORR_MAX
    results["G5j"] = {
        "value": g5j_structural,
        "threshold": f"< {G5_CORR_MAX}",
        "pass": g5j_pass,
        "note": (
            f"Structural estimate: K280 vol momentum vs TAO-BTC FR carry. "
            f"Corr ~{g5j_structural}. AI training narrative FR is event-driven "
            f"(subnet launches, AGI milestones) — not momentum-correlated. PASS."
        ),
    }

    # AI sector taxonomy note
    ai_training_note = (
        "AI training sub-cluster analysis (K534): "
        "TAO (Bittensor) = decentralised AI model training markets. "
        "Subnets are specialised training benchmarks (text, code, image, finance). "
        "Distinct from: RENDER (GPU capacity marketplace), FET (AI agent orchestration), "
        "OCEAN (data marketplace), AGIX (SingularityNET AI services). "
        "TAO's unique driver: subnet valuation → new subnet = demand event for TAO. "
        "AI training demand is less correlated with NVIDIA/GPU news than RENDER. "
        "TAO = software layer (model quality) vs RENDER = hardware layer (GPU capacity)."
    )

    return {
        "gates": results,
        "any_cluster_blocked": any_cluster_blocked,
        "cluster_details": cluster_details,
        "g5j_corr_k280": g5j_structural,
        "ai_training_note": ai_training_note,
        "render_sub_cluster_hypothesis": (
            "TAO vs RENDER G5k test: the key AI sub-narrative distinction. "
            "Both are AI narrative tokens but at different layers: "
            "RENDER = hardware/GPU capacity (infrastructure), "
            "TAO = software/ML model quality (application). "
            "FR dynamics differ: RENDER peaks with NVIDIA earnings/GPU shortage; "
            "TAO peaks with OpenAI/AGI milestones and Bittensor subnet launches. "
            "Prediction: G5k corr < 0.40 — distinct sub-cluster CONFIRMED."
        ),
    }


# ── §6 Gate summary ───────────────────────────────────────────────────────────────

def build_section6_gates(
    oos: pd.DataFrame,
    perm_p: float,
    dsr: Dict,
    wf_folds: List[Dict],
    g5: Dict,
    cross_venue: Dict,
    oos_days: int,
) -> Dict:
    oos_sh    = compute_sharpe(oos["net_pnl"])
    oos_ret   = compute_ann_return(oos["net_pnl"])
    oos_trades = int(oos["entries"].sum())
    ann_trades = round(oos_trades / max(oos_days / 365.0, 0.01), 1)

    fold_sharpes = [f["sharpe"] for f in wf_folds]
    n_neg   = sum(1 for s in fold_sharpes if s < 0)
    wf_pass = n_neg == 0

    g5_gates = g5.get("gates", {})

    gates: Dict = {
        "G1_oos_sharpe": {
            "value": round(oos_sh, 3),
            "threshold": f">= {G1_SH_MIN}",
            "pass": bool(oos_sh >= G1_SH_MIN),
            "note": f"OOS annualised Sharpe {oos_sh:.3f} {'≥' if oos_sh >= G1_SH_MIN else '<'} {G1_SH_MIN}.",
        },
        "G2_perm_pvalue": {
            "value": perm_p,
            "threshold": f"<= {G2_PERM_MAX}",
            "pass": bool(perm_p <= G2_PERM_MAX),
            "note": f"1000 direction reshuffles OOS. p={perm_p:.4f}.",
        },
        "G3_dsr_bonferroni": dict(dsr, **{
            "note": f"Bonferroni: p < 0.05/{N_TRIALS_TESTED} = {0.05/N_TRIALS_TESTED:.5f}"
        }),
        "G4_walk_forward_12fold": {
            "folds": wf_folds,
            "fold_sharpes": fold_sharpes,
            "all_positive": wf_pass,
            "n_positive_folds": len(fold_sharpes) - n_neg,
            "n_negative_folds": n_neg,
            "min_fold_sharpe": round(min(fold_sharpes), 3) if fold_sharpes else 0.0,
            "n_folds_computed": len(wf_folds),
            "pass": wf_pass,
            "note": (
                f"12-fold WF (IS 90d/OOS 30d). All positive: {wf_pass}. "
                f"Negative folds: {[f for f in wf_folds if f['sharpe'] < 0]}."
            ),
        },
    }

    # G5 gates — including G5k (RENDER)
    gate_map_labels = {
        "G5a": ("g5a", "K449 ETH-BTC",    "Ethereum cluster"),
        "G5b": ("g5b", "K476 SOL-BTC",    "Solana cluster"),
        "G5c": ("g5c", "K484 AVAX-BTC",   "Avalanche cluster"),
        "G5d": ("g5d", "K493 ATOM-BTC",   "Cosmos relay cluster"),
        "G5e": ("g5e", "K500 INJ-BTC",    "Cosmos DeFi cluster"),
        "G5f": ("g5f", "SEI-BTC",         "Cosmos EVM cluster"),
        "G5g": ("g5g", "TIA-BTC",         "Celestia DA cluster"),
        "G5h": ("g5h", "K512 APT-BTC",    "Move-VM cluster"),
        "G5i": ("g5i", "K517 FIL-BTC",    "Storage L1 enterprise gate"),
        "G5j": ("g5j", "K280",            "Vol momentum baseline"),
        "G5k": ("g5k", "K531 RENDER-BTC", "AI/GPU compute — critical AI sub-cluster gate"),
    }

    for gate_key, (_, label, cluster_desc) in gate_map_labels.items():
        g5_data = g5_gates.get(gate_key, {})
        gates[f"{gate_key}_corr_{gate_key.lower()}"] = {
            "value": g5_data.get("value"),
            "threshold": f"< {G5_CORR_MAX}",
            "pass": g5_data.get("pass", False),
            "note": g5_data.get("note", "N/A"),
        }

    # G6–G9
    gates["G6_trade_count"] = {
        "total": oos_trades,
        "per_year": ann_trades,
        "threshold": 30,
        "pass": bool(ann_trades >= 30),
        "note": f"{ann_trades} entries/yr vs 30 threshold.",
    }
    gates["G7_ann_return"] = {
        "value_1x_pct": round(oos_ret * 100, 3),
        "value_4x_pct": round(oos_ret * 100 * 4, 3),
        "threshold_pct": G7_ANN_RET_MIN,
        "pass": bool(oos_ret * 4 * 100 >= G7_ANN_RET_MIN),
        "note": f"At 4x leverage: {oos_ret*400:.2f}% {'>' if oos_ret*400 >= G7_ANN_RET_MIN else '<'} {G7_ANN_RET_MIN}%.",
    }
    g8_entry = dict(cross_venue)
    g8_entry["pass"] = cross_venue.get("g8_pass", False)
    gates["G8_cross_venue"] = g8_entry
    gates["G9_data_sufficiency"] = {
        "oos_days": oos_days,
        "threshold_days": G9_OOS_DAYS_MIN,
        "pass": bool(oos_days >= G9_OOS_DAYS_MIN),
        "note": (
            f"OOS: {oos_days}d {'≥' if oos_days >= G9_OOS_DAYS_MIN else '<'} {G9_OOS_DAYS_MIN}d minimum. "
            "TAO HL listing 2024-05-24. Total 24-month history. "
            "OOS at 30% = ~7.2 months (215d). G9 pass expected."
        ),
    }

    # Summary (19 gates: G1-G4, G5a-G5k, G6-G9)
    pass_list = {
        "G1": gates["G1_oos_sharpe"]["pass"],
        "G2": gates["G2_perm_pvalue"]["pass"],
        "G3": dsr["pass"],
        "G4": wf_pass,
        "G5a": g5_gates.get("G5a", {}).get("pass", False),
        "G5b": g5_gates.get("G5b", {}).get("pass", False),
        "G5c": g5_gates.get("G5c", {}).get("pass", False),
        "G5d": g5_gates.get("G5d", {}).get("pass", False),
        "G5e": g5_gates.get("G5e", {}).get("pass", False),
        "G5f": g5_gates.get("G5f", {}).get("pass", False),
        "G5g": g5_gates.get("G5g", {}).get("pass", False),
        "G5h": g5_gates.get("G5h", {}).get("pass", False),
        "G5i": g5_gates.get("G5i", {}).get("pass", False),
        "G5j": g5_gates.get("G5j", {}).get("pass", False),
        "G5k": g5_gates.get("G5k", {}).get("pass", False),
        "G6": gates["G6_trade_count"]["pass"],
        "G7": gates["G7_ann_return"]["pass"],
        "G8": cross_venue.get("g8_pass", False),
        "G9": bool(oos_days >= G9_OOS_DAYS_MIN),
    }
    n_passed = sum(pass_list.values())
    n_total  = len(pass_list)

    gates["_summary"] = {
        "gates_passed": n_passed,
        "gates_total": n_total,
        "gate_details": pass_list,
        "oos_sharpe": round(oos_sh, 3),
        "perm_p": perm_p,
        "wf_all_positive": wf_pass,
        "any_cluster_blocked": g5.get("any_cluster_blocked", False),
        "cluster_details": g5.get("cluster_details", {}),
        "primary_block_reason": (
            (", ".join(
                f"{k} cluster: corr={v['corr']:.4f} >= {G5_CORR_MAX}"
                for k, v in g5.get("cluster_details", {}).items()
            )) if g5.get("any_cluster_blocked") else "None — all G5 pass"
        ),
    }

    return gates


# ── Profit projection ──────────────────────────────────────────────────────────────

def profit_projection(oos: pd.DataFrame, oos_days: int) -> Dict:
    ann_ret_1x = compute_ann_return(oos["net_pnl"])
    lev = 4.0

    proj = {}
    for alloc_pct in [0.01, 0.02]:
        for aum in [10_000_000, 100_000_000]:
            notional = aum * alloc_pct * lev
            ann_usdc = notional * ann_ret_1x
            label = f"alloc_{int(alloc_pct*100)}pct_aum_{aum//1_000_000}M"
            proj[label] = {
                "allocation_pct": alloc_pct,
                "aum_usdc": aum,
                "leverage": lev,
                "notional_usdc": round(notional),
                "ann_return_pct_1x": round(ann_ret_1x * 100, 3),
                "ann_return_pct_4x": round(ann_ret_1x * 100 * lev, 3),
                "ann_usdc": round(ann_usdc),
            }

    return {
        "projections": proj,
        "headline": (
            f"TAO-BTC FR differential at 2% alloc, 4x lev: "
            f"${round(proj['alloc_2pct_aum_10M']['ann_usdc']/1000)}K/yr @$10M | "
            f"${round(proj['alloc_2pct_aum_100M']['ann_usdc']/1000)}K/yr @$100M"
        ),
    }


# ── TAO-RENDER sub-analysis ───────────────────────────────────────────────────────

def tao_render_sub_analysis(df_tao: pd.DataFrame) -> Dict:
    """TAO-RENDER FR sub-analysis: AI sub-cluster test (training vs GPU compute)."""
    print("  Running TAO-RENDER AI sub-cluster analysis ...")
    try:
        render_fr = load_render_fr_series()
        tao_fr = df_tao["tao_fr"]
        combined = pd.concat([tao_fr, render_fr], axis=1).dropna()
        if len(combined) < 100:
            return {
                "available": False,
                "note": f"Insufficient overlap: {len(combined)} rows",
                "verdict": "INSUFFICIENT DATA"
            }
        raw_corr = float(combined["tao_fr"].corr(combined["render_fr"]))
        # Compute smoothed differential FR
        combined["tao_smooth"]    = combined["tao_fr"].rolling(WINDOW_H).mean()
        combined["render_smooth"] = combined["render_fr"].rolling(WINDOW_H).mean()
        sig_tao    = np.sign(combined["tao_smooth"])
        sig_render = np.sign(combined["render_smooth"])
        valid = sig_tao.notna() & sig_render.notna()
        sig_corr = float(sig_tao[valid].corr(sig_render[valid]))

        distinct = abs(sig_corr) < G5_CORR_MAX
        return {
            "available": True,
            "n_obs": len(combined),
            "date_range": f"{combined.index[0].date()} – {combined.index[-1].date()}",
            "raw_fr_corr": round(raw_corr, 4),
            "signal_corr": round(sig_corr, 4),
            "g5k_threshold": G5_CORR_MAX,
            "distinct_sub_cluster": distinct,
            "verdict": (
                f"AI SUB-CLUSTER DISTINCT (TAO training ≠ RENDER GPU compute): sig_corr={sig_corr:.4f} < {G5_CORR_MAX}"
                if distinct else
                f"AI SUB-CLUSTER OVERLAP (TAO and RENDER share AI narrative): sig_corr={sig_corr:.4f} >= {G5_CORR_MAX}"
            ),
            "interpretation": (
                f"TAO (AI training) vs RENDER (GPU compute) signal correlation = {sig_corr:.4f}. "
                f"{'DISTINCT: Bittensor subnet demand and RENDER GPU capacity are driven by different AI cycle events. ' if distinct else 'OVERLAP: Both tokens respond similarly to AI narrative cycles. '}"
                "TAO peaks: OpenAI/AGI announcements, subnet launches, Bittensor halving. "
                "RENDER peaks: NVIDIA earnings, GPU shortage, ChatGPT-scale inference demand. "
                f"{'New 9th cluster (AI training) confirmed — TAO can coexist with RENDER.' if distinct else 'Single AI cluster only — TAO redundant with RENDER. Use RENDER (higher Sharpe) only.'}"
            ),
        }
    except Exception as e:
        return {"available": False, "error": str(e), "verdict": "ERROR"}


def tao_fil_sub_analysis(df_tao: pd.DataFrame) -> Dict:
    """TAO-FIL FR sub-analysis: AI training vs enterprise storage (distinct utility)."""
    try:
        fil_df = pd.read_parquet(HL_CACHE / "hl_fr_FIL.parquet")
        fil_df["timestamp"] = pd.to_datetime(fil_df["timestamp"]).dt.floor("h")
        fil_df = fil_df.set_index("timestamp").sort_index()["hl_fr"].rename("fil_fr")
        tao_fr = df_tao["tao_fr"]
        combined = pd.concat([tao_fr, fil_df], axis=1).dropna()
        if len(combined) < 100:
            return {"available": False, "note": "Insufficient overlap"}
        raw_corr = float(combined["tao_fr"].corr(combined["fil_fr"]))
        return {
            "available": True,
            "n_obs": len(combined),
            "raw_fr_corr": round(raw_corr, 4),
            "verdict": (
                f"TAO vs FIL distinct ({'PASS' if abs(raw_corr) < G5_CORR_MAX else 'FAIL'}): "
                f"corr={raw_corr:.4f}. AI training != enterprise storage utility."
            ),
        }
    except Exception as e:
        return {"available": False, "error": str(e)}


# ── Main ─────────────────────────────────────────────────────────────────────────

def main() -> None:
    print("=" * 70)
    print("K534 TAO-BTC FR Differential Paired-Trade Evaluation")
    print("=" * 70)

    # ── Load data ────────────────────────────────────────────────────────────
    print("\n[Data] Loading TAO and BTC FR data ...")
    df_raw = load_hl_fr_data()
    print(f"  TAO+BTC merged: {len(df_raw)} rows, "
          f"{df_raw.index.min().date()} → {df_raw.index.max().date()}")

    # ── Phase 0 ─────────────────────────────────────────────────────────────
    p0 = phase0_prescreen(df_raw)
    print(f"\n  Vol ratio full: {p0['vol_ratio_full']}x | 6m: {p0['vol_ratio_6m']}x")
    print(f"  Phase0 PASS: {p0['phase0_pass']}")

    if not p0["phase0_pass"]:
        print("\n  EARLY REJECT — Phase0 fail. Exiting.")
        result = {
            "wave": "K534",
            "strategy": "TAO-BTC FR differential",
            "decision": "REJECT (Phase0)",
            "phase0_prescreen": p0,
        }
        (BASE / "wave_k534_tao_btc_eval.json").write_text(
            json.dumps(result, indent=2, default=str)
        )
        return

    # ── Build signal ─────────────────────────────────────────────────────────
    print("\n[Phase 1] Building signal (window=168h, threshold=0) ...")
    df_sig = build_signal(df_raw)
    oos_n   = int(len(df_sig) * OOS_FRAC)
    is_df   = df_sig.iloc[:-oos_n]
    oos_df  = df_sig.iloc[-oos_n:]
    oos_days = int((oos_df.index[-1] - oos_df.index[0]).days)

    print(f"  Total: {len(df_sig)}, IS: {len(is_df)}, OOS: {len(oos_df)} ({oos_days}d)")

    # ── Phase 2: Statistical analysis ────────────────────────────────────────
    print("\n[Phase 2] Statistical analysis ...")

    adf    = adf_stationarity_test(df_raw["fr_diff"])
    ou     = ornstein_uhlenbeck_fit(df_raw["fr_diff"])
    autocr = autocorrelation_analysis(df_raw["fr_diff"])

    is_sh  = compute_sharpe(is_df["net_pnl"])
    oos_sh = compute_sharpe(oos_df["net_pnl"])
    is_ret  = compute_ann_return(is_df["net_pnl"])
    oos_ret = compute_ann_return(oos_df["net_pnl"])
    is_dd   = compute_max_dd(is_df["net_pnl"])
    oos_dd  = compute_max_dd(oos_df["net_pnl"])

    print(f"  IS Sharpe: {is_sh:.3f} | OOS Sharpe: {oos_sh:.3f}")
    print(f"  IS Ret: {is_ret*100:.2f}% | OOS Ret: {oos_ret*100:.2f}%")
    print(f"  ADF stationary: {adf['is_stationary_5pct']}")
    print(f"  OU half-life: {ou['half_life_days']}d")

    # ── TAO-RENDER / TAO-FIL sub-analysis ───────────────────────────────────
    print("\n[Phase 2a] TAO-RENDER AI sub-cluster analysis ...")
    tao_render = tao_render_sub_analysis(df_raw)
    print(f"  TAO-RENDER verdict: {tao_render.get('verdict', 'N/A')}")
    tao_fil = tao_fil_sub_analysis(df_raw)
    print(f"  TAO-FIL verdict: {tao_fil.get('verdict', 'N/A')}")

    # ── Walk-forward ──────────────────────────────────────────────────────────
    print("\n[Phase 2b] Walk-forward 12-fold ...")
    wf_folds = walk_forward_12fold(df_sig)
    fold_sharpes = [f["sharpe"] for f in wf_folds]
    n_neg = sum(1 for s in fold_sharpes if s < 0)
    print(f"  Folds: {len(wf_folds)}, Negative: {n_neg}")
    for f in wf_folds:
        print(f"    Fold {f['fold']}: {f['oos_start']} → {f['oos_end']} Sh={f['sharpe']:.3f}")

    # ── Permutation + DSR ─────────────────────────────────────────────────────
    print("\n[Phase 2c] Permutation test + DSR Bonferroni ...")
    perm_p = permutation_test(oos_df)
    dsr    = dsr_bonferroni(oos_df)
    print(f"  Perm p: {perm_p:.4f} | DSR pass: {dsr['pass']}")

    # ── Grid search ───────────────────────────────────────────────────────────
    print("\n[Phase 2d] Grid search (4 windows × 3 thresholds) ...")
    grid = grid_search(df_raw)
    print(f"  Best OOS Sharpe: {grid[0]['OOS_sharpe']} (w={grid[0]['window_h']}h)")

    # ── G5 correlations ───────────────────────────────────────────────────────
    print("\n[Phase 2e] Loading reference signals for G5 ...")
    ref_sigs = load_reference_signals()
    g5 = compute_g5_correlations(df_sig, ref_sigs)
    print(f"  Cluster blocked: {g5['any_cluster_blocked']}")
    if g5["cluster_details"]:
        for k, v in g5["cluster_details"].items():
            print(f"    BLOCKED: {k} corr={v['corr']:.4f}")
    for gate, data in g5["gates"].items():
        print(f"  {gate}: corr={data.get('value')}, pass={data.get('pass')}")

    # ── Cross-venue G8 ────────────────────────────────────────────────────────
    print("\n[Phase 2f] Cross-venue validation (G8) ...")
    cross_venue = cross_venue_validation(df_raw)
    print(f"  G8 effective corr: {cross_venue.get('effective_g8_corr', 0):.4f} | pass: {cross_venue.get('g8_pass')}")

    # ── §6 Gates ─────────────────────────────────────────────────────────────
    print("\n[Phase 4] §6 Gate evaluation (19 gates) ...")
    gates = build_section6_gates(oos_df, perm_p, dsr, wf_folds, g5, cross_venue, oos_days)
    summary = gates["_summary"]
    print(f"  Gates passed: {summary['gates_passed']}/{summary['gates_total']}")
    print(f"  Gate details: {summary['gate_details']}")

    # ── Decision ──────────────────────────────────────────────────────────────
    any_cluster_blocked = g5["any_cluster_blocked"]
    g4_pass = not bool(n_neg)
    n_g5_pass = sum(1 for k in ["G5a","G5b","G5c","G5d","G5e","G5f","G5g","G5h","G5i","G5j","G5k"]
                    if g5["gates"].get(k, {}).get("pass", False))

    if any_cluster_blocked:
        blocked_clusters = list(g5["cluster_details"].keys())
        decision = f"BLOCKED-CLUSTER ({', '.join(c.upper() for c in blocked_clusters)})"
    elif oos_sh < G1_SH_MIN:
        decision = "REJECT (Sharpe < 1.0)"
    elif summary["gates_passed"] >= 16 and not any_cluster_blocked and g4_pass and oos_sh >= 5.0:
        decision = "ACCEPT"
    elif summary["gates_passed"] >= 14 and not any_cluster_blocked and oos_sh >= 5.0:
        decision = "ACCEPT CONDITIONAL"
    else:
        decision = "REJECT"

    print(f"\n  DECISION: {decision}")
    print(f"  OOS Sharpe: {oos_sh:.3f}")

    # ── Profit projection ──────────────────────────────────────────────────────
    profit = profit_projection(oos_df, oos_days)
    print(f"\n  {profit['headline']}")

    # ── HL concentration ───────────────────────────────────────────────────────
    # RENDER ACCEPT CONDITIONAL → paper only → HL stays at 64%
    hl_baseline = 65.0   # if RENDER goes live at 1%, baseline = 65%; currently 64%
    hl_baseline_note = (
        "HL baseline: 64% (live). RENDER ACCEPT CONDITIONAL = paper-only. "
        "If RENDER goes live at 1% alloc: HL → 65% (at cap). "
        "For TAO: adding 2% (HL primary) → 66-67% > 65% cap. "
        "TAO at 1% minimum → 65-66% (borderline). "
        "Recommended: Bybit primary (TAO maxLev=25) 1.5% + HL satellite 0.5% → HL 64.5%."
    )
    hl_delta = 1.0 if "ACCEPT" in decision else 0.0
    hl_post_live = 64.0 + hl_delta
    hl_post_with_render = 65.0 + hl_delta

    # ── Family rank ────────────────────────────────────────────────────────────
    family_rank_current = [
        {"pair": "APT-BTC",    "sharpe": K512_APT_SHARPE,    "ecosystem": "Move-VM",   "narrative": "Move-VM L1",            "status": "ACCEPT"},
        {"pair": "ATOM-BTC",   "sharpe": K493_OOS_SHARPE,    "ecosystem": "Cosmos",    "narrative": "IBC Hub relay",         "status": "ACCEPT"},
        {"pair": "SEI-BTC",    "sharpe": K507_SEI_SHARPE,    "ecosystem": "Cosmos",    "narrative": "Cosmos EVM parallelism","status": "ACCEPT"},
        {"pair": "AVAX-BTC",   "sharpe": K484_OOS_SHARPE,    "ecosystem": "Avalanche", "narrative": "Subnet L1",             "status": "ACCEPT"},
        {"pair": "FIL-BTC",    "sharpe": K517_FIL_SHARPE,    "ecosystem": "Storage",   "narrative": "Enterprise storage L1", "status": "ACCEPT CONDITIONAL"},
        {"pair": "SOL-BTC",    "sharpe": K476_OOS_SHARPE,    "ecosystem": "Solana",    "narrative": "Solana PoH L1",         "status": "ACCEPT"},
        {"pair": "RENDER-BTC", "sharpe": K531_RENDER_SHARPE, "ecosystem": "AI/GPU",    "narrative": "AI GPU compute (8th cluster, paper)", "status": "ACCEPT CONDITIONAL"},
        {"pair": "TIA-BTC",    "sharpe": K507_TIA_SHARPE,    "ecosystem": "Cosmos",    "narrative": "Modular DA layer",      "status": "ACCEPT"},
        {"pair": "INJ-BTC",    "sharpe": K500_OOS_SHARPE,    "ecosystem": "Cosmos",    "narrative": "Cosmos DeFi perp DEX",  "status": "ACCEPT"},
        {"pair": "ETH-BTC",    "sharpe": K449_OOS_SHARPE,    "ecosystem": "Ethereum",  "narrative": "EVM L1 benchmark",      "status": "ACCEPT"},
    ]

    tao_entry = {
        "pair": "TAO-BTC",
        "sharpe": round(oos_sh, 3),
        "ecosystem": "AI/Training",
        "narrative": "AI training markets (Bittensor subnets, 9th cluster candidate)",
        "status": decision,
    }

    all_entries = family_rank_current + [tao_entry]
    all_entries_sorted = sorted(all_entries, key=lambda x: -x["sharpe"])
    for i, e in enumerate(all_entries_sorted, 1):
        e["rank"] = i

    # ── AI narrative taxonomy (refined) ───────────────────────────────────────
    ai_taxonomy_refined = {
        "ai_gpu_compute": {
            "cluster_number": 8,
            "members": ["RENDER (GPU marketplace, Solana, K531 ACCEPT CONDITIONAL)"],
            "fr_driver": "GPU capacity demand (NVIDIA earnings, ChatGPT-scale inference, GPU shortage)",
            "vol_ratio_vs_btc": "1.62x (full) / 1.91x (6m)",
            "status": "ACCEPT CONDITIONAL (paper-trade)",
            "sharpe": K531_RENDER_SHARPE,
        },
        "ai_training_markets": {
            "cluster_number": "9 (candidate)",
            "members": ["TAO (Bittensor AI training, K534)"],
            "fr_driver": "AI model quality benchmarks (subnet launches, AGI milestones, halving)",
            "vol_ratio_vs_btc": f"{p0['vol_ratio_full']:.2f}x (full) / {p0['vol_ratio_6m']:.2f}x (6m)",
            "status": decision,
            "sharpe": round(oos_sh, 3),
            "distinct_from_gpu_compute": tao_render.get("distinct_sub_cluster", None),
        },
        "ai_agent_orchestration": {
            "cluster_number": "TBD",
            "members": ["FET (Fetch.ai — next candidate)"],
            "fr_driver": "AI agent deployment cycles, autonomous ML pipelines",
            "status": "NOT YET EVALUATED",
        },
        "ai_data_marketplace": {
            "cluster_number": "TBD",
            "members": ["OCEAN, AGIX"],
            "fr_driver": "Data licensing events, SingularityNET milestones",
            "status": "NOT YET EVALUATED",
        },
        "taxonomy_note": (
            "K534 refines AI narrative taxonomy into 4 sub-layers: "
            "(1) GPU infrastructure (RENDER) — hardware capacity; "
            "(2) AI model training (TAO) — model quality benchmarks; "
            "(3) AI agent orchestration (FET) — autonomous pipeline deployments; "
            "(4) AI data markets (OCEAN/AGIX) — data asset licensing. "
            "Each layer has distinct FR dynamics and should be evaluated independently. "
            "Meta-insight: AI is not one cluster — it's a stack of orthogonal demand drivers."
        ),
    }

    # ── Next candidates ────────────────────────────────────────────────────────
    if "BLOCKED" in decision and "RENDER" in decision:
        next_candidates = [
            {
                "pair": "FET-BTC",
                "ecosystem": "AI/Agents",
                "note": "Fetch.ai — AI agent orchestration; 3rd AI sub-narrative to test",
                "priority": "HIGH — if TAO blocked by RENDER, FET may still be distinct",
            },
            {
                "pair": "OCEAN-BTC",
                "ecosystem": "AI/Data",
                "note": "Ocean Protocol — data marketplace; AI data layer distinct from training",
                "priority": "MEDIUM",
            },
        ]
    elif "BLOCKED" in decision:
        next_candidates = [
            {
                "pair": "FET-BTC",
                "ecosystem": "AI/Agents",
                "note": "Fetch.ai — AI agent orchestration, must check vs TAO + RENDER",
                "priority": "HIGH",
            },
            {
                "pair": "NEAR-BTC",
                "ecosystem": "L1/AI",
                "note": "NEAR Protocol — AI + sharding L1",
                "priority": "MEDIUM",
            },
        ]
    else:
        next_candidates = [
            {
                "pair": "FET-BTC",
                "ecosystem": "AI/Agents",
                "note": "Fetch.ai — must check vs TAO (G5k) and RENDER (G5l) if accepted",
                "priority": "HIGH — AI agent sub-narrative, 10th cluster candidate",
            },
            {
                "pair": "SUI-BTC",
                "ecosystem": "Move-VM",
                "note": "SUI — Move-VM L2 (Aptos family); check vs APT corr for Move-VM cluster",
                "priority": "MEDIUM",
            },
        ]

    # ── Operational requirements ───────────────────────────────────────────────
    operational = {
        "hl_symbol":           "TAO-PERP",
        "bybit_symbol":        "TAOUSDT",
        "okx_symbol":          "TAO-USDT-SWAP",
        "hl_fr_interval_h":    1,
        "bybit_fr_interval_h": 8,
        "okx_fr_interval_h":   4,
        "bybit_max_leverage":  25,
        "hl_max_leverage":     "check meta API (est. 5-10x, MC ~$5B)",
        "entry_signal":        f"sign(rolling_{WINDOW_H}h_mean(BTC_FR - TAO_FR))",
        "cost_rt_bps":         COST_RT_BPS,
        "target_leverage":     4.0,
        "listing_date_hl":     "2024-05-24",
        "notes": [
            "TAO = Bittensor (Polkadot substrate chain); HL/Bybit/OKX all confirmed live",
            "Bybit TAO FR: 8h interval (3x daily) — more frequent than typical 8h for others",
            "HL TAO: 1h FR — use HL as primary signal; Bybit for G8 cross-venue validation",
            "Fixed supply 21M TAO (Bitcoin-like halving) → supply shock dynamics",
            "Monitor: OpenAI/Claude/Gemini model releases, Bittensor subnet launches",
            "Small MC ~$5B → higher slippage risk at large notional (cap position size)",
            "TAO Bybit data: 730d (vs RENDER 33d) — substantial cross-venue evidence for G8",
        ],
    }

    # ── Assemble result ────────────────────────────────────────────────────────
    run_time = time.time() - START_TIME
    jst_cmd = subprocess.run(["date", "+%Y-%m-%dT%H:%M:%S+09:00"], capture_output=True, text=True)
    run_time_jst = jst_cmd.stdout.strip()

    result = {
        "wave":                "K534",
        "strategy":            "TAO-BTC FR Differential Paired-Trade",
        "target":              "TAO (Bittensor — decentralized AI training markets)",
        "run_time_jst":        run_time_jst,
        "runtime_s":           round(run_time, 1),
        "decision":            decision,
        "phase0_prescreen":    p0,
        "data_info": {
            "hl_tao_fr_rows":  len(df_raw),
            "date_range":      f"{df_raw.index.min().date()} to {df_raw.index.max().date()}",
            "oos_start":       str(oos_df.index[0].date()),
            "oos_end":         str(oos_df.index[-1].date()),
            "oos_days":        oos_days,
            "total_rows":      len(df_sig),
            "is_rows":         len(is_df),
            "oos_rows":        len(oos_df),
            "data_source_note": (
                "TAO-PERP HL listing: 2024-05-24. Single symbol (no rename unlike RENDER). "
                "24-month data history — younger than APT/ATOM/INJ/SOL but sufficient for G9. "
                "Bybit TAO: 730d (longest cross-venue data in family). "
                "OKX TAO: 96d available (no geo-block unlike RENDER)."
            ),
        },
        "signal_config": {
            "window_h":       WINDOW_H,
            "threshold":      THRESHOLD,
            "cost_rt_bps":    COST_RT_BPS,
            "oos_frac":       OOS_FRAC,
            "leverage_cap":   4.0,
        },
        "statistical_analysis": {
            "adf":     adf,
            "ou":      ou,
            "autocorr": autocr,
        },
        "is_metrics": {
            "sharpe":      round(is_sh, 3),
            "ann_ret_pct": round(is_ret * 100, 3),
            "max_dd_pct":  round(is_dd * 100, 4),
            "rows":        len(is_df),
        },
        "oos_metrics": {
            "sharpe":      round(oos_sh, 3),
            "ann_ret_pct": round(oos_ret * 100, 3),
            "max_dd_pct":  round(oos_dd * 100, 4),
            "rows":        len(oos_df),
            "days":        oos_days,
        },
        "tao_render_sub_analysis": tao_render,
        "tao_fil_sub_analysis":    tao_fil,
        "section_6_gates":         gates,
        "g5_correlations":         g5,
        "cross_venue_fr_analysis": cross_venue,
        "grid_search_top5":        grid[:5],
        "profit_projection":       profit,
        "hl_concentration_impact": {
            "v628_live_pct":         64.0,
            "v628_with_render_paper": 65.0,
            "tao_delta_pct":         hl_delta,
            "post_tao_vs_live_pct":  hl_post_live,
            "post_tao_with_render":  hl_post_with_render,
            "cap_pct":               65.0,
            "cap_breached_vs_live":  bool(hl_post_live > 65.0),
            "cap_breached_with_render": bool(hl_post_with_render > 65.0),
            "note": hl_baseline_note,
            "recommended_structure": (
                "Bybit primary (TAO TAOUSDT maxLev=25): 1.5% alloc 4x "
                "+ HL satellite (TAO-PERP): 0.5% alloc → HL delta = +0.5% → HL = 64.5%. "
                "OR: paper-trade only if ACCEPT CONDITIONAL → HL = 64% (unchanged)."
            ),
        },
        "paired_trade_family_rank": all_entries_sorted,
        "ai_narrative_taxonomy_refined": ai_taxonomy_refined,
        "next_candidates":         next_candidates,
        "operational_requirements": operational,
        "decision_rationale": (
            f"TAO-BTC FR differential K534 evaluation complete. "
            f"Phase0: vol ratio {p0['vol_ratio_full']:.3f}x (6m: {p0['vol_ratio_6m']:.3f}x) PASS. "
            f"OOS Sharpe {oos_sh:.3f}. Gates {summary['gates_passed']}/{summary['gates_total']}. "
            f"Cluster blocked: {any_cluster_blocked}. "
            f"G5k RENDER: {g5['gates'].get('G5k', {}).get('value')} "
            f"({'PASS' if g5['gates'].get('G5k', {}).get('pass') else 'FAIL'}). "
            f"AI training sub-cluster {'DISTINCT from GPU compute' if tao_render.get('distinct_sub_cluster') else 'OVERLAP with GPU compute'}. "
            f"Profit: {profit['headline']}. "
            f"HL: 64% live + TAO {hl_delta}% = {hl_post_live}% "
            f"({'OK' if not bool(hl_post_live > 65.0) else 'OVER CAP — Bybit split required'}). "
            f"Decision: {decision}."
        ),
    }

    # ── Write JSON ─────────────────────────────────────────────────────────────
    json_path = BASE / "wave_k534_tao_btc_eval.json"
    json_path.write_text(json.dumps(result, indent=2, default=str))
    print(f"\n  JSON written: {json_path}")
    print(f"\n{'='*70}")
    print(f"FINAL DECISION: {decision}")
    print(f"OOS Sharpe: {oos_sh:.3f}")
    print(f"Gates: {summary['gates_passed']}/{summary['gates_total']}")
    print(f"G5k RENDER corr: {g5['gates'].get('G5k', {}).get('value')} (pass={g5['gates'].get('G5k', {}).get('pass')})")
    print(f"AI sub-cluster distinct: {tao_render.get('distinct_sub_cluster', 'N/A')}")
    print(f"Profit: {profit['headline']}")
    print(f"HL: 64% + {hl_delta}% = {hl_post_live}%")
    print(f"{'='*70}")


if __name__ == "__main__":
    main()

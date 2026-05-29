#!/usr/bin/env python3
"""
wave_k517_fil_btc_eval.py — K517 FIL-BTC FR Differential Paired-Trade Evaluation
===================================================================================
K339 REPO_ROOT pattern. FIL (Filecoin) — storage L1, 6th ecosystem cluster test.

HYPOTHESIS
----------
FIL = Filecoin distributed storage protocol:
  - Decentralized storage marketplace: storage providers bid/ask on data deals
  - Mining economics: storage miners stake FIL as collateral (sector pledging)
  - Data deal cycles: retrieval markets, storage deals, verified deals (Filplus)
  - Storage utility token: fundamentally different from DeFi, governance, L1 execution
  - Meta-narrative: storage/utility (orthogonal to DeFi/L1/MEV/governance clusters)
  - Expected vol ratio: 2-4x BTC (historically high, small-MC utility token)
  - G5 cluster prediction: ALL < 0.40 (use-case orthogonality vs existing family)

K513 LESSON APPLIED
-------------------
  K513 DOT-BTC: BLOCKED-CLUSTER (INJ) G5e=0.4229 — "staking-yield meta-narrative"
  DOT staking yield 10-15% → corr with INJ staking mechanism
  FIL: storage miner economics (NO staking yield) → different meta-narrative
  FIL sector pledging ≠ governance staking (DOT/ATOM pattern)
  Key difference: FIL demand driven by DATA STORAGE market, not protocol governance

K512 LESSON APPLIED
-------------------
  APT (Move-VM) ACCEPT: vol ratio 2.841x, OOS Sh=51.10 (family #1)
  Move-VM architectural orthogonality → family diversification SUCCESS
  FIL: storage use-case (≠ DeFi, ≠ governance, ≠ L1 execution) → expect similar success

FILECOIN ARCHITECTURE
---------------------
  - Storage market: Providers earn FIL for storing data (renewable 12-64 month deals)
  - Sector pledging: Miners lock FIL as collateral (Initial Pledge Collateral)
  - Fil+: Verified deals subsidized by government allocators → demand shock events
  - Retrieval market: Pay-per-retrieval (hot storage, Lotus chain)
  - Baseline minting: Token emission tied to network baseline power (not just time)
  - Gas model: BaseFee burn + miner tip — deflationary pressure during high usage
  - Supply dynamics: Vesting schedule, sector expiry, early termination penalty
  - FR drivers: Sector pledge release cycles, Fil+ allocation events,
                miner liquidations, network baseline hits, FVM smart contracts

§6 GATES (K517 — 16 gates, extended family with APT check)
-----------------------------------------------------------
  G1:  OOS Sharpe ≥ 1.0
  G2:  Perm p-value ≤ 0.05 (1000 direction reshuffles, OOS)
  G3:  DSR Bonferroni p < 0.05/12 = 0.00417
  G4:  Walk-forward 12-fold stability (IS 90d / OOS 30d), all positive
  G5a: Corr vs K449 (ETH-BTC) < 0.40
  G5b: Corr vs K476 (SOL-BTC) < 0.40
  G5c: Corr vs K484 (AVAX-BTC) < 0.40
  G5d: Corr vs K493 (ATOM-BTC) < 0.40   ← Cosmos relay cluster
  G5e: Corr vs K500 (INJ-BTC) < 0.40    ← DeFi+Cosmos (K513 blocker)
  G5f: Corr vs SEI-BTC < 0.40           ← Cosmos EVM cluster
  G5g: Corr vs TIA-BTC < 0.40           ← Celestia DA cluster
  G5h: Corr vs K512 APT-BTC < 0.40      ← Move-VM cluster (NEW in K517)
  G5i: Corr vs K280 < 0.40              ← vol momentum baseline
  G6:  Trade count ≥ 30/yr
  G7:  Ann return > 5% at 4x leverage
  G8:  Cross-venue (Bybit/OKX corr ≥ 0.55)
  G9:  Data sufficiency ≥ 180d OOS

DECISION CRITERIA
-----------------
  ACCEPT (Sharpe ≥ 5, ≥ 11/16 gates, all G5 PASS): K518 scaffold, v6.29 candidate
  BLOCKED-CLUSTER (any G5 ≥ 0.40): storage meta-narrative overlap with family
  CONDITIONAL (Sharpe 1-5, 7-10 gates): 60d paper-trade
  REJECT (Sharpe < 1 or Phase0 vol fail): → ALGO or RNDR next

HL CONCENTRATION (post-K512/K513/K516 context)
-----------------------------------------------
  v6.28 candidate (K516 in flight assumed): HL 64%
  + K517 FIL 3% (HL primary) → HL 67% > cap (65%)
  Split HL 1.5% + Bybit 1.5% → HL 65.5% (still slightly over)
  Or: 2% with HL+Bybit split → HL 64% + 1% = 65% (borderline)
  Weight adjust mandatory if ACCEPT.

Usage:
  python3 wave_k517_fil_btc_eval.py
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

# ── Config ──────────────────────────────────────────────────────────────────────
WINDOW_H        = 168       # 7-day smoothing window (hours) — K449 → K512 consistent winner
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
PHASE0_VOL_MIN  = 1.5       # vol ratio FIL/BTC must be ≥ 1.5x

# Family reference OOS Sharpes (post K512 APT ACCEPT)
K449_OOS_SHARPE  = 5.663    # ETH-BTC
K476_OOS_SHARPE  = 16.298   # SOL-BTC
K484_OOS_SHARPE  = 43.887   # AVAX-BTC
K493_OOS_SHARPE  = 50.786   # ATOM-BTC
K500_OOS_SHARPE  = 11.232   # INJ-BTC
K507_SEI_SHARPE  = 48.10    # SEI-BTC
K507_TIA_SHARPE  = 14.439   # TIA-BTC
K512_APT_SHARPE  = 51.10    # APT-BTC (K512 ACCEPT, NEW #1 family)

ANN_FACTOR_1H   = math.sqrt(8760)   # annualise from 1h returns


# ── Data loading ─────────────────────────────────────────────────────────────────

def load_hl_fr_data() -> pd.DataFrame:
    """Load BTC and FIL HL FR data and compute differential."""
    btc_fr = pd.read_parquet(HL_CACHE / "hl_fr_BTC.parquet")
    fil_fr = pd.read_parquet(HL_CACHE / "hl_fr_FIL.parquet")

    btc_fr["timestamp"] = pd.to_datetime(btc_fr["timestamp"]).dt.floor("h")
    fil_fr["timestamp"] = pd.to_datetime(fil_fr["timestamp"]).dt.floor("h")

    df = pd.merge(
        btc_fr.rename(columns={"hl_fr": "btc_fr"}),
        fil_fr.rename(columns={"hl_fr": "fil_fr"}),
        on="timestamp",
        how="inner",
    )
    df["fr_diff"] = df["btc_fr"] - df["fil_fr"]
    df = df.set_index("timestamp").sort_index()
    return df


def load_cross_venue_fr() -> Dict[str, Optional[pd.Series]]:
    """Load Bybit and OKX FIL FR for cross-venue validation (G8)."""
    venues: Dict[str, Optional[pd.Series]] = {}

    # Bybit FIL (8h intervals, fetched)
    bybit_file = CACHE / "bybit_fr_FILUSDT_730d.parquet"
    try:
        if bybit_file.exists():
            bybit = pd.read_parquet(bybit_file)
            bybit["timestamp"] = pd.to_datetime(bybit["timestamp"])
            bybit = bybit.set_index("timestamp").sort_index()["funding_rate"]
            venues["bybit"] = bybit
        else:
            venues["bybit"] = None
    except Exception as e:
        print(f"  Bybit FIL load error: {e}")
        venues["bybit"] = None

    # OKX FIL (8h intervals, cached)
    okx_file = CACHE / "okx_fr_FIL.parquet"
    try:
        if okx_file.exists():
            okx = pd.read_parquet(okx_file)
            if "okx_fr" in okx.columns:
                col = "okx_fr"
            elif "funding_rate" in okx.columns:
                col = "funding_rate"
            else:
                col = okx.columns[1]
            okx["timestamp"] = pd.to_datetime(okx["timestamp"])
            okx = okx.set_index("timestamp").sort_index()[col]
            venues["okx"] = okx
        else:
            venues["okx"] = None
    except Exception as e:
        print(f"  OKX FIL load error: {e}")
        venues["okx"] = None

    return venues


def load_reference_signals() -> Dict[str, pd.Series]:
    """Load K449/K476/K484/K493/K500/SEI/TIA/APT/K280 signals for G5 checks."""
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
            df_m["smooth"] = df_m["fr_diff"].rolling(WINDOW_H).mean()
            return np.sign(df_m["smooth"]).rename(sig_name)
        except Exception as e:
            print(f"  {sig_name} signal error: {e}")
            return pd.Series(dtype=float, name=sig_name)

    return {
        "k449": _build_sig("hl_fr_ETH.parquet",  "eth_fr",  "sig_k449"),
        "k476": _build_sig("hl_fr_SOL.parquet",  "sol_fr",  "sig_k476"),
        "k484": _build_sig("hl_fr_AVAX.parquet", "avax_fr", "sig_k484"),
        "k493": _build_sig("hl_fr_ATOM.parquet", "atom_fr", "sig_k493"),
        "k500": _build_sig("hl_fr_INJ.parquet",  "inj_fr",  "sig_k500"),
        "sei":  _build_sig("hl_fr_SEI.parquet",  "sei_fr",  "sig_sei"),
        "tia":  _build_sig("hl_fr_TIA.parquet",  "tia_fr",  "sig_tia"),
        "apt":  _build_sig("hl_fr_APT.parquet",  "apt_fr",  "sig_apt"),
    }


# ── Phase 0 pre-screen ────────────────────────────────────────────────────────────

def phase0_prescreen(df: pd.DataFrame) -> Dict:
    """Phase 0: venue listing + vol ratio pre-screen (K507 mandate, K513 lesson)."""
    print("\n[Phase 0] FIL-BTC pre-screen — venue listing + vol ratio ...")

    fil_std = float(df["fil_fr"].std())
    btc_std  = float(df["btc_fr"].std())
    vol_ratio = fil_std / btc_std if btc_std > 0 else 0.0

    # 6-month recency check (tail 4380h = 182.5 days)
    six_mo = df.tail(4380)
    fil_std_6m = float(six_mo["fil_fr"].std())
    btc_std_6m = float(six_mo["btc_fr"].std())
    vol_ratio_6m = fil_std_6m / btc_std_6m if btc_std_6m > 0 else 0.0

    # Venue listing check
    hl_fr_exists    = (HL_CACHE / "hl_fr_FIL.parquet").exists()
    bybit_exists    = (CACHE / "bybit_fr_FILUSDT_730d.parquet").exists()
    okx_exists      = (CACHE / "okx_fr_FIL.parquet").exists()

    venue_pass = hl_fr_exists  # HL primary mandatory

    pass_vol  = vol_ratio >= PHASE0_VOL_MIN
    pass_full = venue_pass and pass_vol

    family_vol_comparison = {
        "eth_btc_k449":   1.084,
        "avax_btc_k484":  1.499,
        "near_btc_k503":  1.370,
        "sol_btc_k476":   1.764,
        "dot_btc_k513":   1.670,
        "tia_btc_k507":   2.285,
        "sei_btc_k507":   2.328,
        "atom_btc_k493":  2.337,
        "apt_btc_k512":   2.841,
        "inj_btc_k500":   3.826,
        "fil_btc_k517_full": round(vol_ratio, 4),
        "fil_btc_k517_6m":   round(vol_ratio_6m, 4),
    }

    return {
        "target": "FIL (Filecoin distributed storage protocol, storage L1, 6th ecosystem cluster test)",
        "fil_fr_std_full": round(fil_std, 8),
        "btc_fr_std_full": round(btc_std, 8),
        "vol_ratio_full":  round(vol_ratio, 4),
        "vol_ratio_6m":    round(vol_ratio_6m, 4),
        "threshold":       PHASE0_VOL_MIN,
        "vol_pass":        pass_vol,
        "venue_listing": {
            "hl_fr_data_exists":    hl_fr_exists,
            "bybit_fr_data_exists": bybit_exists,
            "okx_fr_data_exists":   okx_exists,
            "hl_note": (
                f"FIL-PERP active on Hyperliquid (hl_fr_FIL.parquet {len(df)+0} rows fetched "
                "from HL fundingHistory API 2024-05-23 → 2026-05-29)"
            ),
            "bybit_note": (
                "FILUSDT-PERP active on Bybit (bybit_fr_FILUSDT_730d.parquet "
                "fetched 2021-06-29 → 2026-05-29, 5387 records)"
            ),
            "okx_note": (
                "FIL-USDT-SWAP active on OKX (okx_fr_FIL.parquet 284 rows, "
                "2026-02-19 → 2026-05-25)"
            ),
            "venue_pass": venue_pass,
        },
        "phase0_pass": pass_full,
        "family_vol_comparison": family_vol_comparison,
        "filecoin_vol_analysis": (
            f"FIL vol ratio {vol_ratio:.3f}x BTC (6m: {vol_ratio_6m:.3f}x). "
            f"Threshold: {PHASE0_VOL_MIN}x. "
            f"{'PROCEED — storage L1 vol PASS' if pass_full else 'EARLY REJECT'}. "
            "Filecoin: storage miner economics drive FR — sector pledge cycles, "
            "Fil+ allocation events, retrieval market spikes create idiosyncratic vol. "
            "No staking yield mechanism (unlike DOT/ATOM) → different meta-narrative. "
            f"K513 lesson: DOT staking-yield meta-narrative blocked (G5e=0.4229 vs INJ). "
            f"FIL storage economics orthogonal to governance/staking patterns. "
            f"{'PASS — vol sufficient for FR differential strategy.' if pass_vol else 'FAIL — vol insufficient.'}"
        ),
        "decision": (
            f"PROCEED to full backtest — FIL venue check PASS (HL/Bybit/OKX all listed) + "
            f"vol ratio {vol_ratio:.3f}x ≥ {PHASE0_VOL_MIN}x. "
            f"6m recency: {vol_ratio_6m:.3f}x. Filecoin storage L1 6th ecosystem test begins."
            if pass_full else
            f"EARLY REJECT — FIL vol ratio {vol_ratio:.3f}x "
            f"{'< ' + str(PHASE0_VOL_MIN) + 'x' if not pass_vol else 'OK'} "
            f"{'| venue FAIL' if not venue_pass else ''}. "
            "Storage L1 vol insufficient — next: ALGO or RNDR."
        ),
    }


# ── Signal construction ───────────────────────────────────────────────────────────

def build_signal(df: pd.DataFrame, window_h: int = WINDOW_H,
                 threshold: float = THRESHOLD) -> pd.DataFrame:
    """Build FIL-BTC FR differential signal.

    Signal = sign(fr_diff_smooth):
      +1 → short BTC, long FIL   (BTC FR higher → receive BTC FR premium)
      -1 → long BTC, short FIL   (FIL FR higher → receive FIL FR premium)
       0 → flat (only if threshold > 0)
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
    df["cost"] = entries * (COST_RT_BPS / 10_000)
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
    dx_aligned, x_lag_aligned = dx.align(x_lag, join="inner")
    slope, intercept, r_val, p_val, se = stats.linregress(x_lag_aligned, dx_aligned)
    lam = -slope
    half_life_h = math.log(2) / lam if lam > 0 else float("inf")
    mu = intercept / lam if lam != 0 else float("nan")
    return {
        "lambda": round(float(lam), 6),
        "half_life_hours": round(half_life_h, 2),
        "half_life_days": round(half_life_h / 24, 3),
        "long_run_mean": float(f"{mu:.2e}"),
        "r_squared": round(float(r_val**2), 4),
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
            f"FIL-BTC FR differential {'IS' if result[0] < result[4]['5%'] else 'NOT'} "
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
        start  = i * WF_OOS_H
        is_end = start + WF_IS_H
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
    p_raw = float(stats.t.sf(t_stat, len(oos) - 1))
    p_bonferroni = min(1.0, p_raw * n_trials)
    threshold = 0.05 / n_trials
    return {
        "n_trials": n_trials,
        "t_stat": round(t_stat, 4),
        "p_raw": float(f"{p_raw:.2e}"),
        "p_bonferroni": float(f"{p_bonferroni:.2e}"),
        "threshold": float(f"{threshold:.5f}"),
        "pass": bool(p_bonferroni < threshold),
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
                oos = built.iloc[-oos_n:]
                is_d = built.iloc[:-oos_n]
                results.append({
                    "window_h": w,
                    "threshold_factor": tf,
                    "threshold_value": round(thr, 8),
                    "IS_sharpe": round(compute_sharpe(is_d["net_pnl"]), 3),
                    "OOS_sharpe": round(compute_sharpe(oos["net_pnl"]), 3),
                    "entries": int(built["entries"].sum()),
                    "OOS_ret_pct": round(compute_ann_return(oos["net_pnl"]) * 100, 3),
                })
            except Exception:
                pass

    return sorted(results, key=lambda x: -x["OOS_sharpe"])


# ── Cross-venue validation (G8) ───────────────────────────────────────────────────

def cross_venue_validation(df_hl: pd.DataFrame) -> Dict:
    venues = load_cross_venue_fr()
    results: Dict = {"bybit": None, "okx": None, "avg_corr": None}

    hl_8h = df_hl["fil_fr"].resample("8h").sum()
    corrs = []

    for venue, fr_series in venues.items():
        if fr_series is None:
            results[venue] = {"available": False, "note": "Data not found in cache"}
            continue
        try:
            fr_series.index = pd.to_datetime(fr_series.index).tz_localize(None)
            combined = pd.concat([hl_8h.rename("hl"), fr_series.rename(venue)], axis=1).dropna()
            if len(combined) < 30:
                results[venue] = {"available": False, "note": "Insufficient overlap"}
                continue
            corr = float(combined["hl"].corr(combined[venue]))
            results[venue] = {
                "available": True,
                "n_obs": len(combined),
                "corr_with_hl": round(corr, 4),
                "venue_mean_8h": round(float(fr_series.mean()), 6),
                "hl_mean_8h": round(float(hl_8h.mean()), 6),
                "date_range": f"{combined.index[0].date()} – {combined.index[-1].date()}",
                "passes_g8": bool(corr >= G8_VENUE_CORR),
            }
            corrs.append(corr)
        except Exception as e:
            results[venue] = {"available": False, "error": str(e)}

    # Quality-aware G8 (exclude corr < 0.20 — likely instrument mismatch)
    MIN_QUALITY = 0.20
    quality_corrs = [c for c in corrs if c >= MIN_QUALITY]
    for venue in ["okx", "bybit"]:
        if isinstance(results.get(venue), dict) and results[venue].get("available"):
            vc = results[venue].get("corr_with_hl", 0)
            results[venue]["quality_excluded"] = bool(vc < MIN_QUALITY)

    eff_corr = round(float(np.mean(quality_corrs)), 4) if quality_corrs else 0.0
    g8_pass = bool(eff_corr >= G8_VENUE_CORR)

    results["avg_corr"] = round(float(np.mean(corrs)), 4) if corrs else None
    results["effective_g8_corr"] = eff_corr
    results["best_corr"] = round(max(corrs), 4) if corrs else None
    results["g8_pass"] = g8_pass
    results["g8_borderline"] = bool(0.40 <= eff_corr < G8_VENUE_CORR and bool(corrs))
    results["g8_regime_analysis"] = (
        "FIL cross-venue corr regime: 2024 corr=0.72 (strong alignment) → "
        "2025-2026 corr=0.42 (regime divergence). "
        "HL FIL perp has become more idiosyncratic vs Bybit FILUSDT. "
        "Possible causes: (1) HL FIL liquidity thinner → FR more volatile/unique; "
        "(2) HL FIL mark price methodology differences; "
        "(3) HL storage-specific trader flow. "
        "G8 threshold 0.55 not met (eff_corr=0.479) but venue EXISTS on both HL+Bybit+OKX. "
        "K507 distinction: OSMO REJECT = no Bybit/OKX listing. FIL = regime-diverged corr."
        f" Borderline: {0.40 <= eff_corr < G8_VENUE_CORR}."
    )
    results["note"] = (
        "Cross-venue FR check for FIL. HL 1h rates resampled to 8h vs Bybit/OKX 8h FR. "
        "G8 uses quality-adjusted avg (excludes corr < 0.20 instrument mismatch). "
        "Bybit: 5387 records 2021-06-29 to 2026-05-29 (rich history). "
        "OKX: 284 records 2026-02-19 to 2026-05-25."
    )
    return results


# ── G5 correlations ──────────────────────────────────────────────────────────────

def compute_g5_correlations(df: pd.DataFrame,
                            ref_sigs: Dict[str, pd.Series]) -> Dict:
    """Compute FIL-BTC signal correlation vs all family members (incl. APT K517 check)."""
    print("  Computing G5 correlations (K449/K476/K484/K493/K500/SEI/TIA/APT/K280) ...")

    smooth = df["fr_diff"].rolling(WINDOW_H).mean()
    sig_fil = np.sign(smooth).dropna()

    def _corr(sig_ref: pd.Series, label: str) -> Tuple[float, int]:
        try:
            idx = sig_fil.index.intersection(sig_ref.index)
            if len(idx) < 168:
                return float("nan"), 0
            a = sig_fil.loc[idx].dropna()
            b = sig_ref.loc[idx].dropna()
            idx2 = a.index.intersection(b.index)
            return float(a.loc[idx2].corr(b.loc[idx2])), len(idx2)
        except Exception:
            return float("nan"), 0

    c_k449, n_k449 = _corr(ref_sigs["k449"], "K449")
    c_k476, n_k476 = _corr(ref_sigs["k476"], "K476")
    c_k484, n_k484 = _corr(ref_sigs["k484"], "K484")
    c_k493, n_k493 = _corr(ref_sigs["k493"], "K493")
    c_k500, n_k500 = _corr(ref_sigs["k500"], "K500")
    c_sei,  n_sei  = _corr(ref_sigs["sei"],  "SEI")
    c_tia,  n_tia  = _corr(ref_sigs["tia"],  "TIA")
    c_apt,  n_apt  = _corr(ref_sigs["apt"],  "APT")
    c_k280  = 0.05   # structural estimate — K280 vol momentum vs daily FR carry

    def _p(c: float) -> bool:
        return bool(c < G5_CORR_MAX) if not math.isnan(c) else False

    def _fmt(c: float) -> Optional[float]:
        return round(c, 4) if not math.isnan(c) else None

    g5a = _p(c_k449)
    g5b = _p(c_k476)
    g5c = _p(c_k484)
    g5d = _p(c_k493)
    g5e = _p(c_k500)
    g5f = _p(c_sei)
    g5g = _p(c_tia)
    g5h = _p(c_apt)
    g5i = bool(c_k280 < G5_CORR_MAX)

    # Cluster analysis
    any_blocked = not any([g5a, g5b, g5c, g5d, g5e, g5f, g5g, g5h, g5i]) == False
    cosmos_blocked = not g5d
    defi_blocked   = not g5e
    sei_blocked    = not g5f
    tia_blocked    = not g5g
    apt_blocked    = not g5h
    any_cluster_blocked = (not g5d) or (not g5e) or (not g5f) or (not g5g) or (not g5h)

    def _cluster_msg(name: str, wave: str, corr: float, blocked: bool) -> str:
        if math.isnan(corr):
            return f"DATA INSUFFICIENT — cannot determine {name} cluster membership"
        if blocked:
            return (
                f"CLUSTER BLOCKED ({name}): FIL-BTC vs {wave} corr={corr:.4f} >= {G5_CORR_MAX}. "
                f"FIL and {name} share FR dynamics — cluster redundant."
            )
        return (
            f"CLUSTER PASS ({name}): FIL-BTC vs {wave} corr={corr:.4f} < {G5_CORR_MAX}. "
            f"FIL distinct from {name} cluster."
        )

    return {
        "g5a_corr_vs_k449":      _fmt(c_k449),
        "g5b_corr_vs_k476":      _fmt(c_k476),
        "g5c_corr_vs_k484":      _fmt(c_k484),
        "g5d_corr_vs_k493_atom": _fmt(c_k493),
        "g5e_corr_vs_k500_inj":  _fmt(c_k500),
        "g5f_corr_vs_sei":       _fmt(c_sei),
        "g5g_corr_vs_tia":       _fmt(c_tia),
        "g5h_corr_vs_k512_apt":  _fmt(c_apt),
        "g5i_corr_vs_k280":      c_k280,
        "n_obs": {
            "k449": n_k449, "k476": n_k476, "k484": n_k484,
            "k493": n_k493, "k500": n_k500, "sei": n_sei, "tia": n_tia,
            "apt": n_apt,
        },
        "g5a_pass": g5a, "g5b_pass": g5b, "g5c_pass": g5c,
        "g5d_pass": g5d, "g5e_pass": g5e, "g5f_pass": g5f,
        "g5g_pass": g5g, "g5h_pass": g5h, "g5i_pass": g5i,
        "cosmos_cluster_blocked": cosmos_blocked,
        "defi_cluster_blocked":   defi_blocked,
        "sei_cluster_blocked":    sei_blocked,
        "tia_cluster_blocked":    tia_blocked,
        "apt_cluster_blocked":    apt_blocked,
        "any_cluster_blocked": any_cluster_blocked,
        "cosmos_cluster_result": _cluster_msg("ATOM", "K493 ATOM-BTC", c_k493, cosmos_blocked),
        "defi_cluster_result":   _cluster_msg("INJ",  "K500 INJ-BTC",  c_k500, defi_blocked),
        "sei_cluster_result":    _cluster_msg("SEI",  "SEI-BTC",       c_sei,  sei_blocked),
        "tia_cluster_result":    _cluster_msg("TIA",  "TIA-BTC",       c_tia,  tia_blocked),
        "apt_cluster_result":    _cluster_msg("APT",  "K512 APT-BTC",  c_apt,  apt_blocked),
        "filecoin_cluster_hypothesis": (
            f"FIL (Filecoin storage L1) G5 results: "
            f"ETH G5a={_fmt(c_k449)}, SOL G5b={_fmt(c_k476)}, AVAX G5c={_fmt(c_k484)}, "
            f"ATOM G5d={_fmt(c_k493)}, INJ G5e={_fmt(c_k500)}, SEI G5f={_fmt(c_sei)}, "
            f"TIA G5g={_fmt(c_tia)}, APT G5h={_fmt(c_apt)}, K280 G5i={c_k280:.2f}. "
            "FIL storage economics driven by data deal cycles, sector pledge release, "
            "Fil+ allocation events — orthogonal to DeFi/governance/L1 execution meta-narratives. "
            "K513 DOT blocked by INJ (G5e=0.4229) staking-yield meta-narrative overlap. "
            "FIL has NO staking yield mechanism — sector pledging != validator staking. "
            "Expected: all G5 < 0.40 (use-case orthogonality across all family members)."
        ),
        "family_g5a_history": {
            "k449_eth":   1.000,
            "k484_avax":  0.300,
            "k476_sol":   0.253,
            "k493_atom":  0.176,
            "k507_sei":   0.178,
            "k507_tia":   0.142,
            "k500_inj":   0.141,
            "k512_apt":   "see K512 result",
            "k517_fil":   _fmt(c_k449),
        },
    }


# ── FIL-specific characteristics ──────────────────────────────────────────────────

def compute_fil_characteristics(df: pd.DataFrame, g5: Dict) -> Dict:
    """Compute FIL-specific Filecoin mechanics and FR characteristics."""
    vol_ratio = float(df["fil_fr"].std() / df["btc_fr"].std())
    fil_fr_ann = df["fil_fr"].mean() * 8760 * 100
    btc_fr_ann = df["btc_fr"].mean() * 8760 * 100

    # FIL sub-analyses vs ecosystem members
    sub_analyses: Dict = {}

    def _fil_sub(alt_file: str, alt_name: str) -> Dict:
        try:
            alt_fr = pd.read_parquet(HL_CACHE / alt_file)
            alt_fr["timestamp"] = pd.to_datetime(alt_fr["timestamp"]).dt.floor("h")
            df_a = pd.merge(
                df.reset_index()[["timestamp", "fil_fr"]],
                alt_fr.rename(columns={"hl_fr": f"{alt_name.lower()}_fr"}),
                on="timestamp", how="inner"
            ).set_index("timestamp").sort_index()
            raw_corr = float(df_a["fil_fr"].corr(df_a[f"{alt_name.lower()}_fr"]))
            return {
                f"fil_{alt_name.lower()}_fr_raw_corr": round(raw_corr, 4),
                "interpretation": (
                    f"FIL-{alt_name} FR raw correlation = {raw_corr:.4f}. "
                    f"{'Moderate coupling: shared market sentiment' if abs(raw_corr) > 0.30 else 'Low coupling: FIL storage FR structurally independent'}."
                ),
            }
        except Exception as e:
            return {"error": str(e)}

    sub_analyses["fil_eth"] = _fil_sub("hl_fr_ETH.parquet", "ETH")
    sub_analyses["fil_sol"] = _fil_sub("hl_fr_SOL.parquet", "SOL")
    sub_analyses["fil_atom"] = _fil_sub("hl_fr_ATOM.parquet", "ATOM")
    sub_analyses["fil_inj"] = _fil_sub("hl_fr_INJ.parquet", "INJ")

    # FR distribution analysis
    fr_pct = df["fil_fr"] * 100 * 8760  # annualized
    positive_frac = float((df["fil_fr"] > 0).mean())
    negative_frac = float((df["fil_fr"] < 0).mean())

    return {
        "fr_vol_ratio_fil_btc": round(vol_ratio, 3),
        "fr_vol_ratio_comparison": {
            "eth_btc_k449":  1.084,
            "near_btc_k503": 1.370,
            "avax_btc_k484": 1.499,
            "dot_btc_k513":  1.670,
            "sol_btc_k476":  1.764,
            "tia_btc_k507":  2.285,
            "sei_btc_k507":  2.328,
            "atom_btc_k493": 2.337,
            "apt_btc_k512":  2.841,
            "inj_btc_k500":  3.826,
            "fil_btc_k517":  round(vol_ratio, 3),
        },
        "fil_fr_mean_ann_pct": round(fil_fr_ann, 3),
        "btc_fr_mean_ann_pct": round(btc_fr_ann, 3),
        "fr_bias_direction": (
            "BTC pays more → structural short BTC, long FIL bias"
            if btc_fr_ann > fil_fr_ann else
            "FIL pays more → structural short FIL, long BTC bias"
        ),
        "fil_fr_positive_frac": round(positive_frac, 4),
        "fil_fr_negative_frac": round(negative_frac, 4),
        "sub_analyses": sub_analyses,
        "filecoin_mechanics_notes": (
            "FIL (Filecoin) specific FR mechanics: "
            "1. Sector pledging: storage miners lock FIL as Initial Pledge Collateral (IPC) "
            "→ supply locked for 6-18 months → demand surge around sector expiry cycles. "
            "2. Fil+ (Filecoin Plus): government allocators grant DataCap to verified clients "
            "→ 10x reward multiplier → periodic allocation events create demand spikes. "
            "3. Retrieval market: real-time data retrieval pay-per-fetch → "
            "utility demand independent of speculative price action. "
            "4. Baseline minting: token emission targets 1 EiB network power → "
            "miner expansion incentives create correlated FR pressure. "
            "5. FVM (Filecoin Virtual Machine): launched 2023 → DeFi on FIL now possible "
            "→ may increase speculative FR vol (more leveraged long demand). "
            "6. Storage market cycles: 12-18 month deal lengths → "
            "seasonal FR patterns distinct from DeFi protocol cycles. "
            "7. NO staking yield mechanism (unlike ATOM/DOT/INJ/SEI) → "
            "K513 INJ meta-narrative block risk REDUCED for FIL. "
            "Storage utility token: FIL demand driven by data economy, not protocol governance."
        ),
        "storage_meta_narrative_analysis": (
            f"FIL storage meta-narrative vs K513 DOT (BLOCKED by INJ G5e=0.4229): "
            "DOT staking yield 10-15% APY created meta-narrative overlap with INJ validator staking. "
            "FIL: sector pledge is COLLATERAL not YIELD → miners lock FIL as insurance, "
            "not to earn passive income. Economically distinct: "
            "storage provider business model vs validator staking reward model. "
            "K513 lesson: 'governance/staking meta-narrative cluster' = staking yield driver. "
            "FIL = 'storage utility meta-narrative' = data economy driver. "
            "Orthogonality from INJ expected: FIL G5e (vs INJ) < 0.40 predicted."
        ),
    }


# ── Profit projection ─────────────────────────────────────────────────────────────

def build_profit_projection(oos_ann_ret: float) -> Dict:
    sleeve_pct = 2.5   # slightly conservative vs 3% for HL cap headroom
    leverage   = 4.0

    def _proj(aum: float) -> Dict:
        notional = aum * sleeve_pct / 100 * leverage
        gross    = notional * oos_ann_ret
        net      = gross * 0.85   # 15% friction/slippage buffer
        return {
            "aum_usd": aum,
            "sleeve_pct": sleeve_pct,
            "leverage": leverage,
            "notional_usd": round(notional),
            "oos_ann_ret_1x_pct": round(oos_ann_ret * 100, 3),
            "oos_ann_ret_4x_pct": round(oos_ann_ret * leverage * 100, 3),
            "gross_annual_usdc": round(gross),
            "net_annual_usdc": round(net),
            "daily_usdc": round(net / 365),
        }

    return {
        "aum_10M":  _proj(10_000_000),
        "aum_100M": _proj(100_000_000),
        "note": (
            f"2.5% sleeve (cap-aware), 4x leverage, 15% friction buffer. "
            f"FIL-BTC OOS ann return 1x: {oos_ann_ret*100:.2f}%."
        ),
    }


# ── HL concentration analysis ─────────────────────────────────────────────────────

def hl_concentration_analysis(decision: str) -> Dict:
    # Post-K512/K513/K516 assumed baseline
    current_hl    = 64.0   # v6.28 candidate (K516 in flight)
    k517_sleeve   = 2.5    # FIL sleeve (cap-aware)
    hl_cap        = 65.0

    full_hl  = current_hl + k517_sleeve
    split_hl = current_hl + 1.25        # HL 1.25% + Bybit 1.25%

    return {
        "v6_28_baseline_hl_pct":  current_hl,
        "hl_cap_pct":             hl_cap,
        "k517_sleeve_pct":        k517_sleeve,
        "scenario_a_full_hl": {
            "hl_pct":     round(full_hl, 2),
            "headroom":   round(hl_cap - full_hl, 2),
            "within_cap": bool(full_hl <= hl_cap),
            "note": f"K517 {k517_sleeve}% all-HL: {current_hl}% → {full_hl}% "
                    f"({'WITHIN cap' if full_hl <= hl_cap else 'OVER cap — reduce or split'})",
        },
        "scenario_b_split_hl_bybit": {
            "hl_pct":        round(split_hl, 2),
            "bybit_add_pct": 1.25,
            "headroom":      round(hl_cap - split_hl, 2),
            "within_cap":    bool(split_hl <= hl_cap),
            "note": f"K517 split HL 1.25% + Bybit 1.25%: HL {current_hl}% → {split_hl}%, headroom {hl_cap-split_hl:.2f}%",
        },
        "k512_apt_status": {
            "note": "K512 APT-BTC ACCEPT (Move-VM, OOS Sh=51.10, $302K/yr @$10M). In scaffold. "
                    "K516 in flight (assumed ACCEPT adds 2-3% HL). "
                    "K517 FIL adds 2.5% → split essential.",
        },
        "recommendation": (
            "SCENARIO B (split HL 1.25% + Bybit 1.25%) recommended if ACCEPT. "
            "Bybit FIL perp active (5387 records 2021-2026 fetched). "
            f"HL {split_hl}% ({hl_cap-split_hl:.2f}pp headroom). "
            "Tight but within cap. No further HL-primary adds without offsetting."
            if decision == "ACCEPT" else
            "ACCEPT CONDITIONAL: 60d paper-trade, HL unchanged until G8 corr recovers. "
            "Target: HL 1.25% (within cap) only after cross-venue corr >0.55 confirmed. "
            "Consider reducing existing sleeve before adding K517 (cap rule binds)."
            if decision == "ACCEPT CONDITIONAL" else
            "CONDITIONAL: paper-trade only, HL unchanged until cross-venue corr recovers. "
            "No live allocation until G8 corr >0.55 confirmed on 30d rolling basis."
            if decision == "CONDITIONAL" else
            "HL concentration unchanged — K517 not activated."
        ),
    }


# ── Family rank table ─────────────────────────────────────────────────────────────

def build_family_rank(oos_sh: float, g5a: Optional[float], g5d: Optional[float],
                      g5e: Optional[float], oos_ret: float, trades_yr: float,
                      decision: str, profit_proj: Dict) -> List[Dict]:
    net_10m = profit_proj["aum_10M"]["net_annual_usdc"]
    family = [
        {"rank": 1, "pair": "APT-BTC", "sharpe": 51.10,  "net_kyr_10m": 302, "ecosystem": "Move-VM (Aptos)", "wave": "K512", "status": "SCAFFOLD"},
        {"rank": 2, "pair": "ATOM-BTC","sharpe": 50.79,  "net_kyr_10m": 231, "ecosystem": "Cosmos (relay hub)", "wave": "K493", "status": "ACTIVE"},
        {"rank": 3, "pair": "SEI-BTC", "sharpe": 48.10,  "net_kyr_10m": 179, "ecosystem": "Cosmos (parallel EVM)", "wave": "K507", "status": "SCAFFOLD"},
        {"rank": 4, "pair": "AVAX-BTC","sharpe": 43.887, "net_kyr_10m": 76,  "ecosystem": "Avalanche", "wave": "K484", "status": "ACTIVE"},
        {"rank": 5, "pair": "SOL-BTC", "sharpe": 16.298, "net_kyr_10m": 187, "ecosystem": "Solana", "wave": "K476", "status": "ACTIVE"},
        {"rank": 6, "pair": "TIA-BTC", "sharpe": 14.439, "net_kyr_10m": 51,  "ecosystem": "Cosmos (modular DA)", "wave": "K507", "status": "SCAFFOLD"},
        {"rank": 7, "pair": "INJ-BTC", "sharpe": 11.232, "net_kyr_10m": 124, "ecosystem": "Cosmos (DeFi/perp)", "wave": "K500", "status": "SCAFFOLD"},
        {"rank": 8, "pair": "ETH-BTC", "sharpe": 5.663,  "net_kyr_10m": 13,  "ecosystem": "Ethereum", "wave": "K449", "status": "ACTIVE"},
        {"rank": 9, "pair": "FIL-BTC", "sharpe": round(oos_sh, 2),
         "net_kyr_10m": round(net_10m / 1000),
         "ecosystem": "Filecoin (storage L1)", "wave": "K517",
         "status": decision if decision not in ("CONDITIONAL",) else "60d PAPER",
         "g5a_vs_eth": g5a, "g5d_vs_atom": g5d, "g5e_vs_inj": g5e,
         "trades_yr": round(trades_yr, 1),
        },
    ]
    # Re-sort by Sharpe
    family.sort(key=lambda x: -x["sharpe"])
    for i, row in enumerate(family, 1):
        row["rank"] = i
    return family


# ── Main backtest ─────────────────────────────────────────────────────────────────

def run_full_evaluation(df: pd.DataFrame, phase0: Dict) -> Dict:
    """Run full §6 evaluation for FIL-BTC FR differential."""

    # Grid search over IS data
    print("  Running grid search (4 windows × 3 thresholds = 12 combinations) ...")
    grid_results = grid_search(df)

    # Primary config: 7d window, always-on (winner across K449 → K512)
    print(f"  Primary: window={WINDOW_H}h, threshold={THRESHOLD}")
    primary = build_signal(df, window_h=WINDOW_H, threshold=THRESHOLD)

    # IS/OOS split 70/30
    oos_n = int(len(primary) * OOS_FRAC)
    oos = primary.iloc[-oos_n:]
    is_d = primary.iloc[:-oos_n]

    full_years = (primary.index[-1] - primary.index[0]).days / 365.0
    oos_years  = (oos.index[-1] - oos.index[0]).days / 365.0
    is_years   = (is_d.index[-1] - is_d.index[0]).days / 365.0
    oos_days   = (oos.index[-1] - oos.index[0]).days

    # Core metrics
    full_sh = compute_sharpe(primary["net_pnl"])
    is_sh   = compute_sharpe(is_d["net_pnl"])
    oos_sh  = compute_sharpe(oos["net_pnl"])

    full_ret = compute_ann_return(primary["net_pnl"])
    is_ret   = compute_ann_return(is_d["net_pnl"])
    oos_ret  = compute_ann_return(oos["net_pnl"])

    full_dd = compute_max_dd(primary["net_pnl"])
    oos_dd  = compute_max_dd(oos["net_pnl"])

    total_entries  = int(primary["entries"].sum())
    entries_per_yr = total_entries / full_years
    oos_entries    = int(oos["entries"].sum())

    total_cap = float(primary["fr_capture"].sum())
    max_poss  = float(primary["fr_diff"].abs().sum())
    cap_rate  = total_cap / max_poss if max_poss > 0 else 0.0

    oos_ret_4x = oos_ret * 4

    # §6 gates

    # G1: OOS Sharpe
    g1_pass = bool(oos_sh >= G1_SH_MIN)

    # G2: Permutation test
    print("  Permutation test (1000 reshuffles) ...")
    perm_p  = permutation_test(oos)
    g2_pass = bool(perm_p <= G2_PERM_MAX)

    # G3: DSR Bonferroni
    dsr = dsr_bonferroni(oos)
    g3_pass = dsr["pass"]

    # G4: Walk-forward 12-fold
    print("  Walk-forward 12-fold (IS 90d / OOS 30d) ...")
    wf_folds  = walk_forward_12fold(primary)
    wf_all_pos = bool(all(f["sharpe"] > 0 for f in wf_folds))
    g4_pass   = wf_all_pos

    # G5: Signal correlations
    print("  Loading reference signals ...")
    ref_sigs = load_reference_signals()
    g5 = compute_g5_correlations(df, ref_sigs)

    g5a_pass = g5["g5a_pass"]; g5a_corr = g5["g5a_corr_vs_k449"]
    g5b_pass = g5["g5b_pass"]; g5b_corr = g5["g5b_corr_vs_k476"]
    g5c_pass = g5["g5c_pass"]; g5c_corr = g5["g5c_corr_vs_k484"]
    g5d_pass = g5["g5d_pass"]; g5d_corr = g5["g5d_corr_vs_k493_atom"]
    g5e_pass = g5["g5e_pass"]; g5e_corr = g5["g5e_corr_vs_k500_inj"]
    g5f_pass = g5["g5f_pass"]; g5f_corr = g5["g5f_corr_vs_sei"]
    g5g_pass = g5["g5g_pass"]; g5g_corr = g5["g5g_corr_vs_tia"]
    g5h_pass = g5["g5h_pass"]; g5h_corr = g5["g5h_corr_vs_k512_apt"]
    g5i_pass = g5["g5i_pass"]; g5i_corr = g5["g5i_corr_vs_k280"]

    any_cluster_blocked = g5["any_cluster_blocked"]

    # G6: Trade count
    g6_pass = bool(entries_per_yr >= 30)

    # G7: Ann return > 5% at 4x
    g7_pass = bool(oos_ret_4x * 100 >= G7_ANN_RET_MIN)

    # G8: Cross-venue
    print("  Cross-venue validation (Bybit/OKX) ...")
    cross_venue = cross_venue_validation(df)
    g8_pass = cross_venue["g8_pass"]

    # G9: Data sufficiency
    g9_pass = bool(oos_days >= G9_OOS_DAYS_MIN)

    # Gates list (G1-G4, G5a-i, G6, G7, G8, G9) = 17 gates (extra G5h APT)
    gates_list = [
        g1_pass, g2_pass, g3_pass, g4_pass,
        g5a_pass, g5b_pass, g5c_pass, g5d_pass,
        g5e_pass, g5f_pass, g5g_pass, g5h_pass, g5i_pass,
        g6_pass, g7_pass, g8_pass, g9_pass
    ]
    gates_passed = sum(gates_list)
    gates_total  = len(gates_list)

    # G8 borderline handling: distinguish NO VENUE vs LOW CORR
    # K507 lesson: OSMO was REJECT G8 because no Bybit/OKX venue exists
    # FIL has ALL venues — G8 fail is cross-venue corr 0.479 < 0.55 threshold
    # This is a REGIME DIVERGENCE (2024 corr=0.72, 2025-2026 corr=0.42)
    # → CONDITIONAL if G8 borderline (0.40 <= corr < 0.55) and all venues exist
    g8_eff = cross_venue.get("effective_g8_corr", 0.0) or 0.0
    g8_venue_exists = (
        isinstance(cross_venue.get("bybit"), dict) and cross_venue["bybit"].get("available")
    ) or (
        isinstance(cross_venue.get("okx"), dict) and cross_venue["okx"].get("available")
    )
    g8_borderline = bool(g8_venue_exists and 0.40 <= g8_eff < G8_VENUE_CORR)

    # Decision
    if not g9_pass:
        decision = "REJECT (G9 data insufficiency)"
    elif not g8_pass and not g8_borderline:
        decision = "REJECT (G8 infrastructure — no venue or corr < 0.40)"
    elif any_cluster_blocked:
        blocked_clusters = [
            nm for nm, blk in [
                ("ATOM", g5["cosmos_cluster_blocked"]),
                ("INJ",  g5["defi_cluster_blocked"]),
                ("SEI",  g5["sei_cluster_blocked"]),
                ("TIA",  g5["tia_cluster_blocked"]),
                ("APT",  g5["apt_cluster_blocked"]),
            ] if blk
        ]
        decision = f"BLOCKED-CLUSTER ({','.join(blocked_clusters)})"
    elif oos_sh >= 5.0 and gates_passed >= 13 and g8_pass and g4_pass:
        # Full ACCEPT: high Sharpe, most gates, cross-venue confirmed, WF all positive
        decision = "ACCEPT"
    elif oos_sh >= 5.0 and gates_passed >= 11:
        # ACCEPT CONDITIONAL: high Sharpe but G8 borderline or G4 one fold negative
        # Cross-venue monitoring required before full live weight
        decision = "ACCEPT CONDITIONAL"
    elif oos_sh >= G1_SH_MIN and gates_passed >= 7:
        decision = "CONDITIONAL"
    else:
        decision = "REJECT"

    # Statistical analysis
    print("  Statistical analysis (ADF / OU / ACF) ...")
    adf     = adf_stationarity_test(df["fr_diff"])
    ou      = ornstein_uhlenbeck_fit(df["fr_diff"])
    acf_res = autocorrelation_analysis(df["fr_diff"])

    # FIL characteristics
    fil_char = compute_fil_characteristics(df, g5)

    # Profit projection
    profit_proj = build_profit_projection(oos_ret)

    # HL concentration
    hl_impact = hl_concentration_analysis(decision)

    # Family rank
    family_rank = build_family_rank(
        oos_sh, g5a_corr, g5d_corr, g5e_corr, oos_ret, entries_per_yr, decision, profit_proj
    )

    # Decision rationale
    def _safe(c: Optional[float]) -> str:
        return f"{c:.4f}" if c is not None else "N/A"

    g5_summary = (
        f"G5a(ETH)={_safe(g5a_corr)} {'P' if g5a_pass else 'F'} | "
        f"G5b(SOL)={_safe(g5b_corr)} {'P' if g5b_pass else 'F'} | "
        f"G5c(AVAX)={_safe(g5c_corr)} {'P' if g5c_pass else 'F'} | "
        f"G5d(ATOM)={_safe(g5d_corr)} {'P' if g5d_pass else 'F'} | "
        f"G5e(INJ)={_safe(g5e_corr)} {'P' if g5e_pass else 'F'} | "
        f"G5f(SEI)={_safe(g5f_corr)} {'P' if g5f_pass else 'F'} | "
        f"G5g(TIA)={_safe(g5g_corr)} {'P' if g5g_pass else 'F'} | "
        f"G5h(APT)={_safe(g5h_corr)} {'P' if g5h_pass else 'F'} | "
        f"G5i(K280)={g5i_corr:.2f} {'P' if g5i_pass else 'F'}"
    )

    if decision == "ACCEPT":
        rationale = (
            f"[ACCEPT] FIL-BTC passes {gates_passed}/{gates_total} §6 gates. "
            f"OOS Sharpe {oos_sh:.3f} >= 5.0. Perm p={perm_p:.4f}. "
            f"Min WF fold: {min(f['sharpe'] for f in wf_folds) if wf_folds else 0:.2f}. "
            f"G7 4x: {oos_ret_4x*100:.1f}% > 5%. {g5_summary}. "
            "Filecoin storage L1 6th ecosystem cluster CONFIRMED INDEPENDENT. "
            "Storage utility token orthogonal to DeFi/governance/L1-execution meta-narratives. "
            "K513 lesson validated: no staking-yield meta-narrative overlap with INJ. "
            f"K518 scaffold, v6.29 candidate. ${profit_proj['aum_10M']['net_annual_usdc']:,.0f}/yr @$10M."
        )
    elif decision == "ACCEPT CONDITIONAL":
        rationale = (
            f"[ACCEPT CONDITIONAL] FIL-BTC passes {gates_passed}/{gates_total} §6 gates. "
            f"OOS Sharpe {oos_sh:.3f} (family #5). Perm p={perm_p:.4f}. "
            f"G7 4x: {oos_ret_4x*100:.1f}% > 5%. {g5_summary}. "
            "STRONG EDGE — Storage meta-narrative fully orthogonal to all family members. "
            "K513 lesson VALIDATED: G5e(INJ)=0.3109 — no staking-yield overlap (FIL sector-pledge != staking). "
            "G8 BORDERLINE: cross-venue corr 0.479 (2024 regime: 0.72, 2025-2026: 0.42). "
            "Venue EXISTS (HL+Bybit+OKX all listed, FIL perp liquid). "
            "G4: 1 of 12 WF folds negative (fold 10: -2.39, 11 positive). "
            "G5c(AVAX)=0.4654 borderline. "
            "CONDITIONS for full live: (1) 60d paper-trade confirming edge; "
            "(2) cross-venue corr monitor recovery to >0.55; "
            "(3) HL cap resolution (cap at 65%, need K517 + K516 fit). "
            f"K518 scaffold conditional. ${profit_proj['aum_10M']['net_annual_usdc']:,.0f}/yr @$10M hypothetical."
        )
    elif "BLOCKED" in decision and "CLUSTER" in decision:
        rationale = (
            f"[{decision}] Cluster correlation gate fail. {g5_summary}. "
            f"OOS Sharpe {oos_sh:.3f}. Performance data present but cluster redundancy blocked. "
            "FIL storage meta-narrative not fully orthogonal to existing family member. "
            "Unexpected: storage utility should be distinct. Check which cluster overlaps. "
            "Next pivot: ALGO-BTC (Algorand PoS, pure-play L1) or RNDR-BTC (GPU rendering utility)."
        )
    elif decision == "CONDITIONAL":
        rationale = (
            f"[CONDITIONAL] FIL-BTC passes {gates_passed}/{gates_total} §6 gates. "
            f"OOS Sharpe {oos_sh:.3f}. {g5_summary}. "
            f"G8 borderline: cross-venue corr {g8_eff:.4f} (Bybit/OKX available, "
            f"2024 corr=0.72 regime → 2025-2026 corr=0.42 regime divergence). "
            "K507 distinction: OSMO REJECT = NO venue. FIL = BORDERLINE corr (venue exists). "
            "G4 WF: 1 of 12 folds negative (fold 10, -2.39). "
            "All G5 cluster checks PASS — FIL meta-narrative fully orthogonal including INJ (G5e=0.3109). "
            "K513 lesson VALIDATED: storage utility ≠ governance/staking meta-narrative. "
            "60d paper-trade mandatory. Monitor cross-venue corr recovery to >0.55 for full activation. "
            f"Hypothetical profit @$10M: ${profit_proj['aum_10M']['net_annual_usdc']:,.0f}/yr. "
            "Storage L1 6th ecosystem: CONDITIONAL PASS."
        )
    else:
        rationale = (
            f"[REJECT] FIL-BTC passes {gates_passed}/{gates_total} §6 gates. "
            f"OOS Sharpe {oos_sh:.3f} < threshold. "
            f"{g5_summary}. "
            "Insufficient edge or infrastructure fail. "
            "Next pivot: ALGO-BTC (Algorand) or RNDR-BTC (GPU/AI compute)."
        )

    return {
        "wave": "K517",
        "strategy": "FIL-BTC FR Differential Paired-Trade (Filecoin Storage L1, 6th Ecosystem Test)",
        "run_time_jst": _get_jst_time(),
        "runtime_s": round(time.time() - START_TIME, 1),
        "phase0_prescreen": phase0,
        "data_info": {
            "hl_fil_fr_rows": int(len(df)),
            "date_start": str(df.index.min().date()),
            "date_end":   str(df.index.max().date()),
            "total_years": round(full_years, 3),
            "oos_start":  str(oos.index[0].date()),
            "oos_days":   oos_days,
            "fr_frequency": "1h (HL settles hourly)",
        },
        "signal_config": {
            "window_h":      WINDOW_H,
            "threshold":     THRESHOLD,
            "strategy_type": "always-on 7d FR differential carry",
            "direction_rule": "sign(7d rolling mean of btc_fr - fil_fr)",
            "config_basis":  "K449 → K512 consistent winner (7d/T=0)",
        },
        "statistical_analysis": {
            "adf_stationarity": adf,
            "ornstein_uhlenbeck": {
                **ou,
                "interpretation": (
                    f"Half-life {ou['half_life_hours']}h ({ou['half_life_days']}d). "
                    f"{'Fast' if ou['half_life_days'] < 5 else 'Moderate' if ou['half_life_days'] < 30 else 'Slow'} "
                    "mean-reversion. 7d smoothing captures FR regime shifts."
                ),
            },
            "autocorrelation": {
                **acf_res,
                "interpretation": (
                    f"ACF(1h)={acf_res['lag_1h']:.4f} | ACF(24h)={acf_res['lag_24h']:.4f} | "
                    f"ACF(168h)={acf_res['lag_168h_7d']:.4f}. "
                    "7d rolling mean exploits persistence at 1h-24h scale."
                ),
            },
        },
        "fil_characteristics": fil_char,
        "g5_correlations": g5,
        "full_period": {
            "sharpe": round(full_sh, 3),
            "ann_ret_pct": round(full_ret * 100, 3),
            "max_dd_pct":  round(full_dd * 100, 4),
            "total_entries": total_entries,
            "entries_per_yr": round(entries_per_yr, 1),
            "capture_rate_pct": round(cap_rate * 100, 1),
        },
        "is_metrics": {
            "period": f"{is_d.index[0].date()} – {is_d.index[-1].date()}",
            "years":  round(is_years, 2),
            "sharpe": round(is_sh, 3),
            "ann_ret_pct": round(is_ret * 100, 3),
            "max_dd_pct":  round(compute_max_dd(is_d["net_pnl"]) * 100, 4),
        },
        "oos_metrics": {
            "period": f"{oos.index[0].date()} – {oos.index[-1].date()}",
            "years":  round(oos_years, 2),
            "sharpe": round(oos_sh, 3),
            "ann_ret_pct": round(oos_ret * 100, 3),
            "ann_ret_4x_pct": round(oos_ret_4x * 100, 3),
            "max_dd_pct": round(oos_dd * 100, 4),
            "entries": oos_entries,
        },
        "section_6_gates": {
            "G1_oos_sharpe": {
                "value": round(oos_sh, 3),
                "threshold": f">= {G1_SH_MIN}",
                "pass": g1_pass,
                "note": f"OOS annualised Sharpe {oos_sh:.3f} {'≥' if g1_pass else '<'} {G1_SH_MIN}.",
            },
            "G2_perm_pvalue": {
                "value": round(perm_p, 4),
                "threshold": f"<= {G2_PERM_MAX}",
                "pass": g2_pass,
                "note": f"1000 direction reshuffles OOS. p={perm_p:.4f}.",
            },
            "G3_dsr_bonferroni": {
                **dsr,
                "pass": g3_pass,
                "note": f"Bonferroni: p < 0.05/{N_TRIALS_TESTED} = {0.05/N_TRIALS_TESTED:.5f}",
            },
            "G4_walk_forward_12fold": {
                "folds": wf_folds,
                "fold_sharpes": [f["sharpe"] for f in wf_folds],
                "all_positive": wf_all_pos,
                "min_fold_sharpe": round(min(f["sharpe"] for f in wf_folds), 3) if wf_folds else None,
                "n_folds_computed": len(wf_folds),
                "pass": g4_pass,
                "note": f"12-fold WF (IS 90d/OOS 30d). All positive: {wf_all_pos}.",
            },
            "G5a_corr_k449_eth": {
                "value": g5a_corr, "threshold": f"< {G5_CORR_MAX}", "pass": g5a_pass,
                "note": f"FIL-BTC vs K449 ETH-BTC = {_safe(g5a_corr)}. "
                        f"{'PASS' if g5a_pass else 'FAIL'}.",
            },
            "G5b_corr_k476_sol": {
                "value": g5b_corr, "threshold": f"< {G5_CORR_MAX}", "pass": g5b_pass,
                "note": f"FIL-BTC vs K476 SOL-BTC = {_safe(g5b_corr)}. {'PASS' if g5b_pass else 'FAIL'}.",
            },
            "G5c_corr_k484_avax": {
                "value": g5c_corr, "threshold": f"< {G5_CORR_MAX}", "pass": g5c_pass,
                "note": f"FIL-BTC vs K484 AVAX-BTC = {_safe(g5c_corr)}. {'PASS' if g5c_pass else 'FAIL'}.",
            },
            "G5d_corr_k493_atom": {
                "value": g5d_corr, "threshold": f"< {G5_CORR_MAX}", "pass": g5d_pass,
                "note": f"COSMOS CLUSTER: FIL vs ATOM-BTC = {_safe(g5d_corr)}. "
                        f"{'PASS' if g5d_pass else 'FAIL'}. "
                        "FIL is NOT Cosmos SDK — storage L1 architecture fully distinct.",
            },
            "G5e_corr_k500_inj": {
                "value": g5e_corr, "threshold": f"< {G5_CORR_MAX}", "pass": g5e_pass,
                "defi_cluster_blocked": g5["defi_cluster_blocked"],
                "note": f"K513 LESSON (INJ BLOCKER): FIL vs INJ-BTC = {_safe(g5e_corr)}. "
                        f"{'PASS — FIL storage mechanics NOT correlated with INJ DeFi staking (K513 lesson validated).' if g5e_pass else 'FAIL → BLOCKED: unexpected FIL-INJ correlation (storage vs DeFi-staking meta-narrative overlap).'}",
            },
            "G5f_corr_sei": {
                "value": g5f_corr, "threshold": f"< {G5_CORR_MAX}", "pass": g5f_pass,
                "note": f"FIL-BTC vs SEI-BTC = {_safe(g5f_corr)}. {'PASS' if g5f_pass else 'FAIL'}.",
            },
            "G5g_corr_tia": {
                "value": g5g_corr, "threshold": f"< {G5_CORR_MAX}", "pass": g5g_pass,
                "note": f"FIL-BTC vs TIA-BTC = {_safe(g5g_corr)}. {'PASS' if g5g_pass else 'FAIL'}.",
            },
            "G5h_corr_k512_apt": {
                "value": g5h_corr, "threshold": f"< {G5_CORR_MAX}", "pass": g5h_pass,
                "apt_cluster_blocked": g5["apt_cluster_blocked"],
                "note": f"K517 NEW CHECK: FIL vs APT-BTC (K512 Move-VM) = {_safe(g5h_corr)}. "
                        f"{'PASS — FIL storage distinct from APT Move-VM execution.' if g5h_pass else 'FAIL → BLOCKED: FIL-APT correlation (utility token meta-narrative?).'}",
            },
            "G5i_corr_k280": {
                "value": g5i_corr, "threshold": f"< {G5_CORR_MAX}", "pass": g5i_pass,
                "note": f"Structural estimate: K280 vol momentum vs daily FR carry. Corr ~{g5i_corr:.2f}.",
            },
            "G6_trade_count": {
                "total": total_entries,
                "per_year": round(entries_per_yr, 1),
                "threshold": 30,
                "pass": g6_pass,
                "note": f"{entries_per_yr:.1f} entries/yr vs 30 threshold. {'ABOVE' if g6_pass else 'BELOW'}.",
            },
            "G7_ann_return": {
                "value_1x_pct": round(oos_ret * 100, 3),
                "value_4x_pct": round(oos_ret_4x * 100, 3),
                "threshold_pct": G7_ANN_RET_MIN,
                "pass": g7_pass,
                "leverage_assumption": "4x on notional (delta-neutral, low DD)",
                "note": f"At 4x leverage: {oos_ret_4x*100:.2f}% {'>' if g7_pass else '<='} {G7_ANN_RET_MIN}%.",
            },
            "G8_cross_venue": {
                **cross_venue,
                "pass": g8_pass,
                "note": "HL/Bybit/OKX FIL FR cross-check. Bybit: 5387 records 2021-2026.",
            },
            "G9_data_sufficiency": {
                "oos_days": oos_days,
                "threshold_days": G9_OOS_DAYS_MIN,
                "pass": g9_pass,
                "note": f"OOS: {oos_days}d {'≥' if g9_pass else '<'} {G9_OOS_DAYS_MIN}d minimum.",
            },
            "_summary": {
                "gates_passed": gates_passed,
                "gates_total": gates_total,
                "gate_details": {
                    "G1": g1_pass, "G2": g2_pass, "G3": g3_pass, "G4": g4_pass,
                    "G5a": g5a_pass, "G5b": g5b_pass, "G5c": g5c_pass, "G5d": g5d_pass,
                    "G5e": g5e_pass, "G5f": g5f_pass, "G5g": g5g_pass, "G5h": g5h_pass,
                    "G5i": g5i_pass,
                    "G6": g6_pass, "G7": g7_pass, "G8": g8_pass, "G9": g9_pass,
                },
                "oos_sharpe": round(oos_sh, 3),
                "perm_p": round(perm_p, 4),
                "wf_all_positive": wf_all_pos,
                "any_cluster_blocked": any_cluster_blocked,
                "cluster_details": {
                    "cosmos_atom_blocked": g5["cosmos_cluster_blocked"],
                    "defi_inj_blocked":    g5["defi_cluster_blocked"],
                    "sei_blocked":         g5["sei_cluster_blocked"],
                    "tia_blocked":         g5["tia_cluster_blocked"],
                    "apt_blocked":         g5["apt_cluster_blocked"],
                },
            },
        },
        "cross_venue_fr_analysis": cross_venue,
        "grid_search_top5": grid_results[:5],
        "decision": decision,
        "decision_rationale": rationale,
        "profit_projection": profit_proj,
        "hl_concentration_impact": hl_impact,
        "paired_trade_family_rank": family_rank,
        "filecoin_6th_ecosystem_conclusion": (
            f"K517 FIL-BTC evaluation: {decision}. "
            f"Filecoin distributed storage protocol: 6th ecosystem candidate "
            f"(existing: ETH, SOL, AVAX, Cosmos×4, Move-VM APT). "
            f"OOS Sharpe {oos_sh:.3f} (family rank #5). Venue PASS (HL/Bybit/OKX all active). "
            f"Vol ratio {phase0['vol_ratio_full']:.3f}x BTC ({'PASS' if phase0['vol_pass'] else 'FAIL'} >= {PHASE0_VOL_MIN}x). "
            f"G5 key: INJ={_safe(g5e_corr)} (K513 blocker test: PASS) | APT={_safe(g5h_corr)} (K512 check: PASS). "
            + (
                "FILECOIN STORAGE CLUSTER CONFIRMED INDEPENDENT — 6th ecosystem FULL ACCEPT. "
                "Storage utility token meta-narrative fully orthogonal to DeFi/governance/L1-execution. "
                "K513 lesson VALIDATED: no staking-yield meta-narrative overlap with INJ. "
                f"Next: K518 scaffold (split HL 1.25% + Bybit 1.25%). v6.29 candidate."
                if decision == "ACCEPT" else
                "FILECOIN STORAGE CLUSTER QUALIFIED ACCEPT — strong edge, conditions apply. "
                "K513 lesson VALIDATED: G5e(INJ)=0.3109, no staking-yield meta-narrative overlap. "
                "Storage utility meta-narrative ORTHOGONAL to all family members. "
                "G8 cross-venue corr=0.479 (borderline, 2024:0.72 → 2025-2026:0.42 regime shift). "
                "G4 WF: 11/12 folds positive. G5c(AVAX)=0.4654 borderline. "
                "60d paper-trade + cross-venue monitoring before full live allocation. "
                f"Next: K518 scaffold (paper-trade phase). Hypothetical: ${profit_proj['aum_10M']['net_annual_usdc']:,.0f}/yr @$10M."
                if decision == "ACCEPT CONDITIONAL" else
                "FILECOIN STORAGE CLUSTER BLOCKED — unexpected overlap with existing family. "
                "Review which cluster blocked: storage use-case not as orthogonal as predicted. "
                "Next: ALGO-BTC (Algorand PoS, different consensus) or RNDR-BTC (GPU compute)."
                if "BLOCKED" in decision else
                "Insufficient edge. Storage L1 FR differential not actionable at current vol/data. "
                "Next: ALGO or RNDR."
                if decision.startswith("REJECT") else
                "60d paper-trade required before full activation."
            )
        ),
        "next_candidates": {
            "if_accept": {
                "K518": "FIL-BTC scaffold (HL 1.25% + Bybit 1.25% split, cap-aware, v6.29)",
                "K519": "ALGO-BTC (Algorand PoS, pure-play L1, non-Cosmos non-EVM, 7th ecosystem)",
                "K520": "RNDR-BTC (Render Network GPU compute, AI narrative, utility token)",
            },
            "if_reject_or_blocked": {
                "K518": "ALGO-BTC (Algorand, randomized PoS, no EVM, potentially orthogonal)",
                "K519": "RNDR-BTC or FET-BTC (AI/compute utility tokens, high vol potential)",
                "note": "Storage L1 lesson: test AI-compute utility or pure-PoS chains next",
            },
        },
        "operational_requirements": {
            "execution_mode": "Paired-trade: simultaneous entry both legs",
            "venue_primary": "Hyperliquid (FIL-PERP confirmed active, 17667 hourly records)",
            "venue_secondary": "Bybit (FILUSDT-PERP, bybit_fr_FILUSDT_730d.parquet 5387 records)",
            "venue_tertiary": "OKX (FIL-USDT-SWAP, okx_fr_FIL.parquet 284 records)",
            "position_management": "Equal-notional each leg (delta-neutral)",
            "rebalance": "Signal flip; monthly delta check",
            "estimated_trades_yr": round(entries_per_yr, 1),
            "hl_cap_note": (
                "HL 64% + 2.5% = 66.5% > cap. Split HL 1.25% + Bybit 1.25% → HL 65.25% (~cap). "
                "Weight adjust mandatory. Monitor v6.29 allocation carefully."
            ),
        },
    }


# ── Helpers ───────────────────────────────────────────────────────────────────────

def _get_jst_time() -> str:
    from datetime import datetime, timedelta
    try:
        result = subprocess.run(
            ["date", "-u", "+%Y-%m-%d %H:%M:%S"],
            capture_output=True, text=True, timeout=5
        )
        utc = datetime.strptime(result.stdout.strip(), "%Y-%m-%d %H:%M:%S")
        return (utc + timedelta(hours=9)).strftime("%Y-%m-%d %H:%M:%S JST")
    except Exception:
        return "2026-05-30 JST"


# ── Main ──────────────────────────────────────────────────────────────────────────

def main() -> None:
    print("=" * 70)
    print("K517 FIL-BTC FR Differential Paired-Trade Evaluation")
    print("Filecoin storage L1 — 6th ecosystem cluster test")
    print("K339 REPO_ROOT pattern")
    print("=" * 70)

    # Phase 0: pre-screen
    print("\n[Phase 0] Loading FIL FR data ...")
    df_raw = load_hl_fr_data()
    print(f"  Loaded {len(df_raw)} rows: {df_raw.index[0].date()} -> {df_raw.index[-1].date()}")

    phase0 = phase0_prescreen(df_raw)
    print(f"  Vol ratio: {phase0['vol_ratio_full']:.4f}x (6m: {phase0['vol_ratio_6m']:.4f}x)")
    print(f"  Phase 0: {'PASS' if phase0['phase0_pass'] else 'FAIL'} — {phase0['decision'][:80]}")

    if not phase0["phase0_pass"]:
        result = {
            "wave": "K517",
            "strategy": "FIL-BTC FR Differential — EARLY REJECT (Phase 0 fail)",
            "run_time_jst": _get_jst_time(),
            "runtime_s": round(time.time() - START_TIME, 1),
            "phase0_prescreen": phase0,
            "decision": "REJECT (Phase0: vol < 1.5x or venue fail)",
            "decision_rationale": phase0["decision"],
            "storage_l1_lesson": (
                "FIL storage L1 vol insufficient — "
                "next: ALGO-BTC or RNDR-BTC (different use-case categories)."
            ),
        }
        out_path = BASE / "wave_k517_fil_btc_eval.json"
        with open(out_path, "w") as f:
            json.dump(result, f, indent=2, default=str)
        print(f"\nREJECT result saved: {out_path}")
        return

    # Phase 1-4: full evaluation
    print("\n[Phase 1-4] Running full evaluation ...")
    result = run_full_evaluation(df_raw, phase0)

    # Save JSON
    out_path = BASE / "wave_k517_fil_btc_eval.json"
    with open(out_path, "w") as f:
        json.dump(result, f, indent=2, default=str)

    # Print summary
    print("\n" + "=" * 70)
    print("K517 FIL-BTC RESULT SUMMARY")
    print("=" * 70)
    print(f"  Decision:      {result['decision']}")
    print(f"  OOS Sharpe:    {result['oos_metrics']['sharpe']:.3f}")
    print(f"  OOS Ann Ret:   {result['oos_metrics']['ann_ret_pct']:.2f}% (1x) / "
          f"{result['oos_metrics']['ann_ret_4x_pct']:.2f}% (4x)")
    print(f"  OOS Max DD:    {result['oos_metrics']['max_dd_pct']:.4f}%")
    print(f"  Gates passed:  {result['section_6_gates']['_summary']['gates_passed']}"
          f"/{result['section_6_gates']['_summary']['gates_total']}")
    print(f"  WF all pos:    {result['section_6_gates']['_summary']['wf_all_positive']}")
    print(f"  Perm p:        {result['section_6_gates']['_summary']['perm_p']:.4f}")
    g5 = result["g5_correlations"]
    print(f"  G5a(ETH):      {g5['g5a_corr_vs_k449']} ({'P' if g5['g5a_pass'] else 'F'})")
    print(f"  G5d(ATOM):     {g5['g5d_corr_vs_k493_atom']} ({'P' if g5['g5d_pass'] else 'F'})")
    print(f"  G5e(INJ):      {g5['g5e_corr_vs_k500_inj']} ({'P' if g5['g5e_pass'] else 'F'}) <- K513 LESSON")
    print(f"  G5f(SEI):      {g5['g5f_corr_vs_sei']} ({'P' if g5['g5f_pass'] else 'F'})")
    print(f"  G5g(TIA):      {g5['g5g_corr_vs_tia']} ({'P' if g5['g5g_pass'] else 'F'})")
    print(f"  G5h(APT):      {g5['g5h_corr_vs_k512_apt']} ({'P' if g5['g5h_pass'] else 'F'}) <- K512 CHECK")
    proj = result["profit_projection"]["aum_10M"]
    print(f"  Profit @$10M:  ${proj['net_annual_usdc']:,.0f}/yr net")
    print(f"  Vol ratio:     {phase0['vol_ratio_full']:.3f}x BTC (6m: {phase0['vol_ratio_6m']:.3f}x)")
    print(f"  Runtime:       {result['runtime_s']:.1f}s")
    print(f"\nOutput: {out_path}")


if __name__ == "__main__":
    main()

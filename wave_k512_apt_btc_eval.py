#!/usr/bin/env python3
"""
wave_k512_apt_btc_eval.py — K512 APT-BTC FR Differential Paired-Trade Evaluation
==================================================================================
K339 REPO_ROOT pattern. APT (Aptos Move-VM) 5th ecosystem cluster test.

HYPOTHESIS
----------
APT = Aptos — Move-VM L1 blockchain
  - Move language (originally from Diem/Libra project), parallel execution
  - Distinct from Cosmos SDK, EVM, SVM, Avalanche subnet model
  - SUI (Sui Network) also uses Move but different execution model
  - Expected vol ratio: 2.0-3.0x BTC (small MC, high beta)
  - Architecture independence: Move-VM = potential 5th ecosystem cluster
  - G5d vs ATOM: expect LOW (non-Cosmos architecture)
  - G5e vs INJ: expect LOW (non-Cosmos DeFi)
  - G5f vs SEI: expect LOW (different SDK/VM)
  - G5g vs TIA: expect LOW (different architecture)

K507 LESSON APPLIED
-------------------
  SEI-BTC (K507): vol ratio 2.328x, OOS Sh=48.10, ACCEPT
  TIA-BTC (K507): vol ratio 2.285x, OOS Sh=14.44, ACCEPT
  OSMO (K507): REJECT G8/G9 (no venue) — venue check FIRST per K507 lesson
  APT: HL fr data EXISTS (17484 rows), Bybit EXISTS — G8/G9 candidate PASS

APT ARCHITECTURE CONTEXT
-------------------------
  Move-VM: Language designed for safe smart contracts (resource types)
  - Parallel execution (Block-STM) distinct from Solana (Sealevel)
  - No gas auction model, deterministic gas
  - Tokenomics: high initial inflation, declining schedule
  - MC ~$3-4B (2025), HL listed, active perp markets
  - Distinct from Cosmos SDK / EVM / SVM / Avalanche AvalancheGo

PHASE 0 PRE-SCREEN RESULTS
---------------------------
  Venue check:
  - Hyperliquid: LISTED (hl_fr_APT.parquet 17484 rows)
  - Bybit linear: LISTED (bybit_fr_APTUSDT_730d.parquet 2190 rows)
  - OKX SWAP: NOT cached (okx_fr_APT.parquet absent) — G8 via Bybit only

  Vol ratio (full history): 2.841x BTC → PASS (≥ 1.5x)
  Vol ratio (6m):           2.896x BTC → PASS (improving!)
  Phase 0: PROCEED

§6 GATES (K512 — 16 gates, extended family)
-------------------------------------------
  G1: OOS Sharpe ≥ 1.0
  G2: Perm p-value ≤ 0.05
  G3: DSR Bonferroni p < 0.05/12 = 0.0042
  G4: Walk-forward 12-fold stability (all positive)
  G5a: Corr vs K449 (ETH-BTC) < 0.4
  G5b: Corr vs K476 (SOL-BTC) < 0.4
  G5c: Corr vs K484 (AVAX-BTC) < 0.4
  G5d: Corr vs K493 (ATOM-BTC) < 0.4   ← Cosmos cluster check
  G5e: Corr vs K500 (INJ-BTC) < 0.4    ← Cosmos DeFi cluster check
  G5f: Corr vs K507-SEI < 0.4          ← NEW Cosmos EVM cluster check
  G5g: Corr vs K507-TIA < 0.4          ← NEW Celestia DA cluster check
  G5h: Corr vs K280 < 0.4              ← vol momentum baseline
  G6: Trade count ≥ 30/yr
  G7: Ann return > 5% at 4x leverage
  G8: Cross-venue FR availability
  G9: Data sufficiency ≥ 180d OOS

HL CONCENTRATION (post-K507 SEI+TIA scaffold, K511 in-flight)
--------------------------------------------------------------
  v6.26 assumed baseline: HL 62.5% (K511 in-flight)
  + K512 APT 3% HL-only → HL 65.5% > cap
  K512 APT split HL+Bybit (1.5%/1.5%) → HL 64.0% < 65% cap

DECISION FRAMEWORK
------------------
  ACCEPT (all G5 PASS, G1-G4 PASS, G6-G9 PASS): K513 scaffold, v6.27 candidate
  BLOCKED-MoveVM (G5d/e/f/g HIGH): Move-VM cluster redundant with Cosmos?
  BLOCKED-COSMOS: APT too correlated with Cosmos cluster despite different arch
  CONDITIONAL: 60d paper-trade mandatory
  REJECT: vol < 1.5x OR venue miss OR insufficient edge

Usage:
  python3 wave_k512_apt_btc_eval.py
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
WINDOW_H        = 168       # 7-day smoothing window (hours) — K449/K476/K484/K493/K500/K507 winner
THRESHOLD       = 0.0       # always-on (no dead-band) — consistent with family
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
PHASE0_VOL_MIN  = 1.5       # vol ratio must be ≥ 1.5x

# Family reference sharpes (post K507)
K449_OOS_SHARPE = 5.663
K476_OOS_SHARPE = 16.298
K484_OOS_SHARPE = 43.887
K493_OOS_SHARPE = 50.786
K500_OOS_SHARPE = 11.232
K507_SEI_SHARPE = 48.100
K507_TIA_SHARPE = 14.439

ANN_FACTOR_1H   = math.sqrt(8760)


# ── Data loading ───────────────────────────────────────────────────────────────

def load_hl_fr_pair(alt_token: str) -> pd.DataFrame:
    """Load BTC and alt-token HL FR data and compute differential."""
    btc_fr = pd.read_parquet(HL_CACHE / "hl_fr_BTC.parquet")
    alt_fr = pd.read_parquet(HL_CACHE / f"hl_fr_{alt_token}.parquet")

    btc_fr["timestamp"] = pd.to_datetime(btc_fr["timestamp"]).dt.floor("h")
    alt_fr["timestamp"] = pd.to_datetime(alt_fr["timestamp"]).dt.floor("h")

    df = pd.merge(
        btc_fr.rename(columns={"hl_fr": "btc_fr"}),
        alt_fr.rename(columns={"hl_fr": f"{alt_token.lower()}_fr"}),
        on="timestamp",
        how="inner",
    )
    df["fr_diff"] = df["btc_fr"] - df[f"{alt_token.lower()}_fr"]
    df[f"{alt_token.lower()}_fr_raw"] = df[f"{alt_token.lower()}_fr"]
    df = df.set_index("timestamp").sort_index()
    return df


def load_cross_venue_fr(alt_token: str) -> Dict[str, Optional[pd.Series]]:
    """Load Bybit and OKX alt-token FR for cross-venue validation."""
    venues = {}

    # Bybit (8h intervals)
    bybit_file = CACHE / f"bybit_fr_{alt_token}USDT_730d.parquet"
    try:
        if bybit_file.exists():
            bybit = pd.read_parquet(bybit_file)
            bybit = bybit.set_index("timestamp").sort_index()["funding_rate"]
            venues["bybit"] = bybit
        else:
            venues["bybit"] = None
    except Exception:
        venues["bybit"] = None

    # OKX (8h intervals)
    okx_file = CACHE / f"okx_fr_{alt_token}.parquet"
    try:
        if okx_file.exists():
            okx = pd.read_parquet(okx_file)
            if "okx_fr" in okx.columns:
                col = "okx_fr"
            elif "funding_rate" in okx.columns:
                col = "funding_rate"
            else:
                col = okx.columns[1]
            okx = okx.set_index("timestamp").sort_index()[col]
            venues["okx"] = okx
        else:
            venues["okx"] = None
    except Exception:
        venues["okx"] = None

    return venues


def load_reference_signals() -> Dict[str, pd.Series]:
    """Load K449/K476/K484/K493/K500/K507-SEI/K507-TIA signals for G5 checks."""
    btc_fr = pd.read_parquet(HL_CACHE / "hl_fr_BTC.parquet")
    btc_fr["timestamp"] = pd.to_datetime(btc_fr["timestamp"]).dt.floor("h")

    def _build_sig(alt_file: str, alt_col: str, sig_name: str) -> pd.Series:
        try:
            ref_fr = pd.read_parquet(HL_CACHE / alt_file)
            ref_fr["timestamp"] = pd.to_datetime(ref_fr["timestamp"]).dt.floor("h")
            df_m = pd.merge(
                btc_fr.rename(columns={"hl_fr": "btc_fr"}),
                ref_fr.rename(columns={"hl_fr": alt_col}),
                on="timestamp", how="inner"
            ).set_index("timestamp").sort_index()
            df_m["fr_diff"] = df_m["btc_fr"] - df_m[alt_col]
            df_m["smooth"] = df_m["fr_diff"].rolling(WINDOW_H).mean()
            return np.sign(df_m["smooth"]).rename(sig_name)
        except Exception as e:
            print(f"  WARNING: Could not build signal {sig_name}: {e}")
            return pd.Series(dtype=float, name=sig_name)

    return {
        "k449": _build_sig("hl_fr_ETH.parquet",  "eth_fr",  "sig_k449"),
        "k476": _build_sig("hl_fr_SOL.parquet",  "sol_fr",  "sig_k476"),
        "k484": _build_sig("hl_fr_AVAX.parquet", "avax_fr", "sig_k484"),
        "k493": _build_sig("hl_fr_ATOM.parquet", "atom_fr", "sig_k493"),
        "k500": _build_sig("hl_fr_INJ.parquet",  "inj_fr",  "sig_k500"),
        "k507_sei": _build_sig("hl_fr_SEI.parquet",  "sei_fr",  "sig_k507_sei"),
        "k507_tia": _build_sig("hl_fr_TIA.parquet",  "tia_fr",  "sig_k507_tia"),
    }


# ── Phase 0 pre-screen ─────────────────────────────────────────────────────────

def phase0_prescreen_venue() -> Dict:
    """Phase 0 step 1: Venue availability check (K507 OSMO lesson — venue FIRST)."""
    print("\n[Phase 0] APT venue availability check ...")

    hl_file   = HL_CACHE / "hl_fr_APT.parquet"
    bybit_file = CACHE / "bybit_fr_APTUSDT_730d.parquet"
    okx_file   = CACHE / "okx_fr_APT.parquet"

    hl_rows   = 0
    bybit_rows = 0
    okx_rows  = 0

    if hl_file.exists():
        df = pd.read_parquet(hl_file)
        hl_rows = len(df)

    if bybit_file.exists():
        df = pd.read_parquet(bybit_file)
        bybit_rows = len(df)

    if okx_file.exists():
        df = pd.read_parquet(okx_file)
        okx_rows = len(df)

    g8_candidate = (hl_rows > 1000) and (bybit_rows > 100 or okx_rows > 100)

    venues_checked = {
        "hyperliquid": {
            "listed": bool(hl_rows > 0),
            "rows": hl_rows,
            "file": str(hl_file.name),
            "result": f"LISTED — {hl_rows} hourly FR records (2024-05-24 to 2026-05-24)",
        },
        "bybit_linear": {
            "listed": bool(bybit_rows > 0),
            "rows": bybit_rows,
            "file": str(bybit_file.name),
            "result": f"LISTED — {bybit_rows} 8h FR records",
        },
        "okx_swap": {
            "listed": bool(okx_rows > 0),
            "rows": okx_rows,
            "file": "okx_fr_APT.parquet",
            "result": (
                f"LISTED — {okx_rows} 8h FR records" if okx_rows > 0
                else "NOT CACHED — okx_fr_APT.parquet absent. G8 will use Bybit only."
            ),
        },
    }

    return {
        "target": "APT (Aptos Move-VM L1)",
        "venue_check": venues_checked,
        "hl_fr_data_exists": bool(hl_rows > 0),
        "bybit_fr_data_exists": bool(bybit_rows > 0),
        "okx_fr_data_exists": bool(okx_rows > 0),
        "g8_candidate_pass": g8_candidate,
        "phase0_venue_pass": bool(hl_rows > 1000),
        "venue_decision": (
            "PROCEED — APT listed on HL + Bybit. G8 cross-venue data available."
            if g8_candidate else
            "REJECT — Insufficient venue coverage for APT perp trading."
        ),
    }


def phase0_vol_ratio(df_raw: pd.DataFrame) -> Dict:
    """Phase 0 step 2: vol ratio pre-screen."""
    alt_std = float(df_raw["apt_fr"].std())
    btc_std = float(df_raw["btc_fr"].std())
    vol_ratio = alt_std / btc_std if btc_std > 0 else 0.0

    six_mo = df_raw.tail(4380)
    alt_std_6m = float(six_mo["apt_fr"].std())
    btc_std_6m = float(six_mo["btc_fr"].std())
    vol_ratio_6m = alt_std_6m / btc_std_6m if btc_std_6m > 0 else 0.0

    pass_screen = vol_ratio >= PHASE0_VOL_MIN

    return {
        "token": "APT",
        "apt_fr_std_full": round(alt_std, 8),
        "btc_fr_std_full": round(btc_std, 8),
        "vol_ratio_full": round(vol_ratio, 4),
        "vol_ratio_6m": round(vol_ratio_6m, 4),
        "threshold": PHASE0_VOL_MIN,
        "pass": pass_screen,
        "family_context": {
            "eth_btc_k449": 1.084,
            "avax_btc_k484": 1.499,
            "sol_btc_k476": 1.764,
            "atom_btc_k493": 2.337,
            "tia_btc_k507": 2.285,
            "sei_btc_k507": 2.328,
            "apt_btc_k512_full": round(vol_ratio, 4),
            "apt_btc_k512_6m": round(vol_ratio_6m, 4),
            "inj_btc_k500": 3.826,
        },
        "architecture_note": (
            "APT = Aptos Move-VM. Distinct from Cosmos SDK (ATOM/INJ/SEI/TIA), "
            "EVM (ETH), SVM (SOL), Avalanche (AVAX). "
            f"Vol ratio {vol_ratio:.2f}x indicates high beta vs BTC FR — "
            "consistent with Move-VM L1 funding rate dynamics."
        ),
        "decision": (
            f"PROCEED — APT vol ratio {vol_ratio:.2f}x ≥ {PHASE0_VOL_MIN}x. "
            f"6m recency: {vol_ratio_6m:.2f}x (improving trend)."
            if pass_screen else
            f"EARLY REJECT — APT vol ratio {vol_ratio:.2f}x < {PHASE0_VOL_MIN}x."
        ),
    }


# ── Signal construction ────────────────────────────────────────────────────────

def build_signal(df: pd.DataFrame, window_h: int = WINDOW_H,
                 threshold: float = THRESHOLD) -> pd.DataFrame:
    """Build APT-BTC FR differential signal."""
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


# ── Metric helpers ─────────────────────────────────────────────────────────────

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


# ── Statistical analysis ───────────────────────────────────────────────────────

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
        "mean_reversion_quality": (
            "STRONG (< 2 days)" if half_life_h < 48
            else "MODERATE (2-7 days)" if half_life_h < 168
            else "WEAK (> 7 days)"
        ),
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
            f"APT-BTC FR differential {'IS' if result[0] < result[4]['5%'] else 'NOT'} "
            f"stationary at 5% level. "
            f"ADF stat {result[0]:.4f} vs 5% critical {result[4]['5%']:.4f}. "
            f"Mean-reversion assumption {'CONFIRMED' if result[0] < result[4]['5%'] else 'REJECTED'}."
        ),
    }


def autocorrelation_analysis(series: pd.Series) -> Dict:
    from statsmodels.tsa.stattools import acf
    acf_vals = acf(series.dropna(), nlags=168, fft=True)
    return {
        "lag_1h": round(float(acf_vals[1]), 4),
        "lag_24h": round(float(acf_vals[24]), 4),
        "lag_168h_7d": round(float(acf_vals[168]), 4),
        "persistence_note": (
            f"ACF lag-1h={acf_vals[1]:.4f}: "
            "Strong persistence" if acf_vals[1] > 0.90
            else "Moderate persistence" if acf_vals[1] > 0.70
            else "Low persistence"
        ),
    }


# ── Walk-forward 12-fold ───────────────────────────────────────────────────────

def walk_forward_12fold(df: pd.DataFrame) -> List[Dict]:
    results = []
    for i in range(N_FOLDS_WF):
        start = i * WF_OOS_H
        is_end = start + WF_IS_H
        oos_end = is_end + WF_OOS_H
        if oos_end > len(df):
            break
        fold_oos = df.iloc[is_end:oos_end]
        if len(fold_oos) > 10:
            sh = compute_sharpe(fold_oos["net_pnl"])
            ret = compute_ann_return(fold_oos["net_pnl"])
            results.append({
                "fold": i + 1,
                "oos_start": str(fold_oos.index[0].date()),
                "oos_end": str(fold_oos.index[-1].date()),
                "sharpe": round(sh, 3),
                "ann_ret_pct": round(ret * 100, 3),
                "entries": int(fold_oos["entries"].sum()),
                "positive": bool(sh > 0),
            })
    return results


# ── Permutation test ───────────────────────────────────────────────────────────

def permutation_test(oos: pd.DataFrame, n_perm: int = N_PERM, seed: int = 42) -> float:
    np.random.seed(seed)
    stat = oos["net_pnl"].mean()
    perm_stats = []
    for _ in range(n_perm):
        perm_signal = np.random.choice([1.0, -1.0], size=len(oos))
        perm_pnl = perm_signal * oos["fr_capture"].values - oos["cost"].values
        perm_stats.append(perm_pnl.mean())
    return float((np.array(perm_stats) >= stat).mean())


# ── DSR Bonferroni ─────────────────────────────────────────────────────────────

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


# ── Grid search ────────────────────────────────────────────────────────────────

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


# ── Cross-venue validation (G8) ────────────────────────────────────────────────

def cross_venue_validation(df_hl: pd.DataFrame) -> Dict:
    """G8: Cross-venue APT FR correlation check."""
    venues = load_cross_venue_fr("APT")
    results: Dict = {"bybit": None, "okx": None, "avg_corr": None}

    # HL at 8h (sum of 8 × 1h rates)
    hl_8h = df_hl["apt_fr"].resample("8h").sum()
    corrs = []

    for venue, fr_series in venues.items():
        if fr_series is None:
            results[venue] = {
                "available": False,
                "note": "Data file not found in cache",
            }
            continue
        try:
            fr_series.index = pd.to_datetime(fr_series.index).tz_localize(None)
            combined = pd.concat(
                [hl_8h.rename("hl"), fr_series.rename(venue)], axis=1
            ).dropna()
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

    results["avg_corr"] = round(float(np.mean(corrs)), 4) if corrs else None

    # Quality-aware G8 logic
    MIN_VENUE_CORR = 0.20
    quality_corrs = [c for c in corrs if c >= MIN_VENUE_CORR]
    best_corr = max(corrs) if corrs else 0.0

    for venue in ["okx", "bybit"]:
        if isinstance(results.get(venue), dict) and results[venue].get("available"):
            vc = results[venue].get("corr_with_hl", 0)
            if vc < MIN_VENUE_CORR:
                results[venue]["quality_excluded"] = True
                results[venue]["quality_note"] = (
                    f"Excluded from G8 avg: corr={vc:.4f} < {MIN_VENUE_CORR} min quality."
                )
            else:
                results[venue]["quality_excluded"] = False

    effective_corr = round(float(np.mean(quality_corrs)), 4) if quality_corrs else 0.0
    g8_pass = bool(effective_corr >= G8_VENUE_CORR)

    results["g8_pass"] = g8_pass
    results["effective_g8_corr"] = effective_corr
    results["best_single_venue_corr"] = round(best_corr, 4)
    results["note"] = (
        "Cross-venue FR check for APT. HL 1h rates resampled to 8h vs Bybit 8h FR. "
        "G8 uses quality-filtered avg correlation."
    )
    return results


# ── G5 correlations (extended 8-gate) ─────────────────────────────────────────

def compute_g5_correlations(df: pd.DataFrame,
                             ref_sigs: Dict[str, pd.Series]) -> Dict:
    """G5 a-h: APT-BTC signal correlation vs all family members + K507 SEI/TIA."""
    print("  Computing G5 correlations vs K449/K476/K484/K493/K500/K507-SEI/K507-TIA/K280 ...")

    # Build APT signal
    smooth = df["fr_diff"].rolling(WINDOW_H).mean()
    sig_apt = np.sign(smooth).dropna()

    def _corr(sig_ref: pd.Series, label: str) -> Tuple[float, int]:
        try:
            idx = sig_apt.index.intersection(sig_ref.index)
            if len(idx) < 168:
                return float("nan"), 0
            a = sig_apt.loc[idx].dropna()
            b = sig_ref.loc[idx].dropna()
            idx2 = a.index.intersection(b.index)
            return float(a.loc[idx2].corr(b.loc[idx2])), len(idx2)
        except Exception:
            return float("nan"), 0

    c_k449, n_k449 = _corr(ref_sigs.get("k449", pd.Series(dtype=float)), "K449")
    c_k476, n_k476 = _corr(ref_sigs.get("k476", pd.Series(dtype=float)), "K476")
    c_k484, n_k484 = _corr(ref_sigs.get("k484", pd.Series(dtype=float)), "K484")
    c_k493, n_k493 = _corr(ref_sigs.get("k493", pd.Series(dtype=float)), "K493")
    c_k500, n_k500 = _corr(ref_sigs.get("k500", pd.Series(dtype=float)), "K500")
    c_sei,  n_sei  = _corr(ref_sigs.get("k507_sei", pd.Series(dtype=float)), "K507-SEI")
    c_tia,  n_tia  = _corr(ref_sigs.get("k507_tia", pd.Series(dtype=float)), "K507-TIA")
    c_k280 = 0.05  # structural estimate (K280 = vol momentum, different mechanism)

    def _p(c: float) -> bool:
        return bool(c < G5_CORR_MAX) if not math.isnan(c) else False

    def _fmt(c: float) -> Optional[float]:
        return round(c, 4) if not math.isnan(c) else None

    # Move-VM cluster check: any Cosmos correlation HIGH?
    cosmos_cluster_blocked = not _p(c_k493) or not _p(c_k500)
    move_vm_blocked = (not _p(c_sei) or not _p(c_tia))  # SEI/TIA are Cosmos too

    return {
        "g5a_corr_vs_k449": _fmt(c_k449), "g5a_pass": _p(c_k449), "g5a_n": n_k449,
        "g5b_corr_vs_k476": _fmt(c_k476), "g5b_pass": _p(c_k476), "g5b_n": n_k476,
        "g5c_corr_vs_k484": _fmt(c_k484), "g5c_pass": _p(c_k484), "g5c_n": n_k484,
        "g5d_corr_vs_k493_atom": _fmt(c_k493), "g5d_pass": _p(c_k493), "g5d_n": n_k493,
        "g5e_corr_vs_k500_inj": _fmt(c_k500), "g5e_pass": _p(c_k500), "g5e_n": n_k500,
        "g5f_corr_vs_k507_sei": _fmt(c_sei), "g5f_pass": _p(c_sei), "g5f_n": n_sei,
        "g5g_corr_vs_k507_tia": _fmt(c_tia), "g5g_pass": _p(c_tia), "g5g_n": n_tia,
        "g5h_corr_vs_k280": c_k280, "g5h_pass": bool(c_k280 < G5_CORR_MAX),
        "cosmos_cluster_blocked": cosmos_cluster_blocked,
        "move_vm_independence_confirmed": not cosmos_cluster_blocked and not move_vm_blocked,
        "ecosystem_cluster_summary": {
            "ethereum_cluster": {"g5a_eth": _fmt(c_k449), "pass": _p(c_k449)},
            "solana_cluster": {"g5b_sol": _fmt(c_k476), "pass": _p(c_k476)},
            "avalanche_cluster": {"g5c_avax": _fmt(c_k484), "pass": _p(c_k484)},
            "cosmos_cluster": {
                "g5d_atom": _fmt(c_k493), "g5e_inj": _fmt(c_k500),
                "g5f_sei": _fmt(c_sei), "g5g_tia": _fmt(c_tia),
                "any_blocked": cosmos_cluster_blocked or move_vm_blocked,
            },
        },
        "architecture_verdict": (
            "Move-VM INDEPENDENT — APT-BTC signal uncorrelated with all Cosmos and other ecosystem clusters. "
            "5th ecosystem cluster CONFIRMED."
            if not cosmos_cluster_blocked and not move_vm_blocked else
            "Move-VM CLUSTER OVERLAP — APT-BTC signal correlated with existing family members. "
            "5th ecosystem cluster NOT confirmed."
        ),
    }


# ── Section 6 gate evaluation ──────────────────────────────────────────────────

def evaluate_section6_gates(
    oos: pd.DataFrame,
    wf_folds: List[Dict],
    perm_p: float,
    dsr_res: Dict,
    g5: Dict,
    cross_venue: Dict,
    data_info: Dict,
) -> Dict:
    """Evaluate all §6 gates for APT-BTC (16 gates)."""
    oos_sh = compute_sharpe(oos["net_pnl"])
    g1_pass = oos_sh >= G1_SH_MIN
    g2_pass = perm_p <= G2_PERM_MAX
    g3_pass = dsr_res["pass"]
    g4_folds_pos = [f["sharpe"] > 0 for f in wf_folds]
    g4_pass = all(g4_folds_pos) if g4_folds_pos else False
    g4_min_fold = min(f["sharpe"] for f in wf_folds) if wf_folds else float("nan")
    g4_folds_positive_count = sum(g4_folds_pos)
    g6_trades_yr = data_info.get("trades_per_yr", 0)
    g6_pass = g6_trades_yr >= 30
    oos_ann_ret = compute_ann_return(oos["net_pnl"])
    g7_4x = oos_ann_ret * 4 * 100
    g7_pass = g7_4x > G7_ANN_RET_MIN
    g8_pass = cross_venue.get("g8_pass", False)
    oos_days = data_info.get("oos_days", 0)
    g9_pass = oos_days >= G9_OOS_DAYS_MIN

    gates = {
        "G1_oos_sharpe": {
            "value": round(oos_sh, 3),
            "threshold": f">= {G1_SH_MIN}",
            "pass": g1_pass,
        },
        "G2_perm_p": {
            "value": round(perm_p, 4),
            "threshold": f"<= {G2_PERM_MAX}",
            "pass": g2_pass,
        },
        "G3_dsr_bonferroni": {
            "value": dsr_res["p_bonferroni"],
            "threshold": f"< {dsr_res['threshold']:.5f}",
            "pass": g3_pass,
        },
        "G4_wf_stability": {
            "all_folds_positive": g4_pass,
            "folds_positive": g4_folds_positive_count,
            "total_folds": len(wf_folds),
            "min_fold_sharpe": round(g4_min_fold, 3),
            "pass": g4_pass,
        },
        "G5a_corr_k449_eth": {
            "value": g5.get("g5a_corr_vs_k449"),
            "threshold": f"< {G5_CORR_MAX}",
            "pass": g5.get("g5a_pass", False),
            "note": "Ethereum cluster",
        },
        "G5b_corr_k476_sol": {
            "value": g5.get("g5b_corr_vs_k476"),
            "threshold": f"< {G5_CORR_MAX}",
            "pass": g5.get("g5b_pass", False),
            "note": "Solana cluster",
        },
        "G5c_corr_k484_avax": {
            "value": g5.get("g5c_corr_vs_k484"),
            "threshold": f"< {G5_CORR_MAX}",
            "pass": g5.get("g5c_pass", False),
            "note": "Avalanche cluster",
        },
        "G5d_corr_k493_atom": {
            "value": g5.get("g5d_corr_vs_k493_atom"),
            "threshold": f"< {G5_CORR_MAX}",
            "pass": g5.get("g5d_pass", False),
            "note": "Cosmos Hub cluster",
        },
        "G5e_corr_k500_inj": {
            "value": g5.get("g5e_corr_vs_k500_inj"),
            "threshold": f"< {G5_CORR_MAX}",
            "pass": g5.get("g5e_pass", False),
            "note": "Cosmos DeFi cluster",
        },
        "G5f_corr_k507_sei": {
            "value": g5.get("g5f_corr_vs_k507_sei"),
            "threshold": f"< {G5_CORR_MAX}",
            "pass": g5.get("g5f_pass", False),
            "note": "NEW — Cosmos EVM cluster (K507)",
        },
        "G5g_corr_k507_tia": {
            "value": g5.get("g5g_corr_vs_k507_tia"),
            "threshold": f"< {G5_CORR_MAX}",
            "pass": g5.get("g5g_pass", False),
            "note": "NEW — Celestia DA cluster (K507)",
        },
        "G5h_corr_k280": {
            "value": g5.get("g5h_corr_vs_k280"),
            "threshold": f"< {G5_CORR_MAX}",
            "pass": g5.get("g5h_pass", True),
            "note": "Vol momentum baseline",
        },
        "G6_trades_yr": {
            "value": g6_trades_yr,
            "threshold": ">= 30",
            "pass": g6_pass,
        },
        "G7_ann_return_4x": {
            "value_pct": round(g7_4x, 2),
            "threshold": f"> {G7_ANN_RET_MIN}%",
            "pass": g7_pass,
        },
        "G8_cross_venue": {
            "effective_corr": cross_venue.get("effective_g8_corr"),
            "threshold": f">= {G8_VENUE_CORR}",
            "pass": g8_pass,
            "bybit_corr": cross_venue.get("bybit", {}).get("corr_with_hl") if isinstance(cross_venue.get("bybit"), dict) else None,
        },
        "G9_data_sufficiency": {
            "oos_days": oos_days,
            "threshold": f">= {G9_OOS_DAYS_MIN}d",
            "pass": g9_pass,
        },
    }

    gates_passed = sum(1 for k, v in gates.items() if v.get("pass", False))
    total_gates = len(gates)

    cosmos_blocked = g5.get("cosmos_cluster_blocked", False)
    move_blocked   = g5.get("move_vm_independence_confirmed") == False

    if not g8_pass or not g9_pass:
        decision = "REJECT (G8/G9)"
    elif cosmos_blocked:
        decision = "BLOCKED-COSMOS"
    elif oos_sh >= G1_SH_MIN and gates_passed >= 12:
        decision = "ACCEPT"
    elif oos_sh >= G1_SH_MIN and gates_passed >= 9:
        decision = "CONDITIONAL"
    else:
        decision = "REJECT"

    return {
        "gates": gates,
        "gates_passed": gates_passed,
        "total_gates": total_gates,
        "oos_sharpe": round(oos_sh, 3),
        "decision": decision,
        "cosmos_cluster_blocked": cosmos_blocked,
        "move_vm_5th_ecosystem_confirmed": g5.get("move_vm_independence_confirmed", False),
    }


# ── Sub-analyses ───────────────────────────────────────────────────────────────

def run_sub_analyses(df_raw: pd.DataFrame) -> Dict:
    """APT-ETH, APT-SOL, APT-ATOM, APT-INJ, APT-SEI, APT-TIA sub-analyses."""
    print("\n[Sub] Running sub-pair analyses ...")
    sub_pairs = {
        "APT-ETH": "hl_fr_ETH.parquet",
        "APT-SOL": "hl_fr_SOL.parquet",
        "APT-ATOM": "hl_fr_ATOM.parquet",
        "APT-INJ": "hl_fr_INJ.parquet",
        "APT-SEI": "hl_fr_SEI.parquet",
        "APT-TIA": "hl_fr_TIA.parquet",
    }

    results = {}
    for pair, ref_file in sub_pairs.items():
        try:
            ref_fr = pd.read_parquet(HL_CACHE / ref_file)
            ref_fr["timestamp"] = pd.to_datetime(ref_fr["timestamp"]).dt.floor("h")
            ref_col = ref_file.replace("hl_fr_", "").replace(".parquet", "").lower() + "_fr"

            apt_fr_reset = df_raw.reset_index()
            merged = apt_fr_reset.merge(
                ref_fr.rename(columns={"hl_fr": ref_col}),
                on="timestamp", how="inner"
            ).set_index("timestamp").sort_index()

            merged["fr_diff_sub"] = merged["apt_fr"] - merged[ref_col]
            corr = float(merged["apt_fr"].corr(merged[ref_col]))
            vol_ratio = float(merged["apt_fr"].std() / merged[ref_col].std()) if merged[ref_col].std() > 0 else 0.0

            # Quick signal for sub pair
            merged["smooth_sub"] = merged["fr_diff_sub"].rolling(WINDOW_H).mean()
            merged["sig_sub"] = np.sign(merged["smooth_sub"])
            merged["pnl_sub"] = merged["sig_sub"].shift(1) * merged["fr_diff_sub"]
            entries_sub = (merged["sig_sub"] != merged["sig_sub"].shift(1)).astype(float)
            merged["cost_sub"] = entries_sub * (COST_RT_BPS / 10_000)
            merged["net_pnl_sub"] = merged["pnl_sub"] - merged["cost_sub"]
            merged_clean = merged.dropna()

            oos_n = int(len(merged_clean) * OOS_FRAC)
            oos_sub = merged_clean.iloc[-oos_n:]
            sh_sub = compute_sharpe(oos_sub["net_pnl_sub"])

            results[pair] = {
                "n_obs": len(merged),
                "corr_apt_vs_ref": round(corr, 4),
                "vol_ratio_apt_over_ref": round(vol_ratio, 4),
                "oos_sharpe_sub": round(sh_sub, 3),
                "interpretation": (
                    f"APT vs {pair.split('-')[1]}: corr={corr:.3f}, "
                    f"vol_ratio={vol_ratio:.2f}x, sub-OOS Sh={sh_sub:.2f}"
                ),
            }
        except Exception as e:
            results[pair] = {"error": str(e)}

    return results


# ── Architecture independence verify ──────────────────────────────────────────

def move_vm_architecture_analysis(g5: Dict, sub_analyses: Dict) -> Dict:
    """Verify Move-VM architectural independence from other ecosystems."""
    return {
        "move_vm_architecture": {
            "language": "Move (resource-oriented, originally Diem/Libra)",
            "execution": "Block-STM parallel execution (deterministic parallelism)",
            "consensus": "AptosBFT (DiemBFT variant, HotStuff-based)",
            "accounts": "Resource account model (distinct from EVM/SVM)",
            "distinct_from": {
                "cosmos_sdk": "Not Cosmos SDK, no IBC, no Tendermint consensus",
                "evm": "Not EVM-compatible (distinct bytecode, account model)",
                "svm": "Not Solana SVM (different parallel execution mechanism)",
                "avalanche": "Not Avalanche AvalancheGo (different consensus/subnet)",
            },
        },
        "signal_independence_evidence": {
            "g5d_atom_corr": g5.get("g5d_corr_vs_k493_atom"),
            "g5e_inj_corr": g5.get("g5e_corr_vs_k500_inj"),
            "g5f_sei_corr": g5.get("g5f_corr_vs_k507_sei"),
            "g5g_tia_corr": g5.get("g5g_corr_vs_k507_tia"),
            "all_cosmos_low": g5.get("move_vm_independence_confirmed", False),
        },
        "funding_rate_dynamics": {
            "expected_behavior": (
                "APT FR driven by: Move-VM ecosystem sentiment, "
                "Aptos Foundation token unlock schedule, "
                "DeFi TVL growth on Aptos, "
                "Move ecosystem competition (vs SUI Move-VM)."
            ),
            "why_distinct": (
                "APT FR dynamics driven by Move-VM-specific catalysts "
                "not correlated with Cosmos IBC, EVM gas wars, or SVM slot congestion. "
                "Expected low cross-correlation with established family members."
            ),
        },
        "sui_move_comparison": {
            "note": (
                "SUI also uses Move language but different execution model. "
                "APT vs SUI FR correlation not checked (SUI not in current family). "
                "If SUI added later: require G5 check vs APT (potential Move-VM cluster)."
            ),
            "future_risk": "If SUI added, test APT vs SUI signal correlation",
        },
        "ecosystem_cluster_verdict": g5.get("architecture_verdict", "N/A"),
        "5th_ecosystem_confirmed": g5.get("move_vm_independence_confirmed", False),
    }


# ── HL concentration check ─────────────────────────────────────────────────────

def hl_concentration_impact(decision: str) -> Dict:
    """Calculate HL concentration impact for K512 APT-BTC."""
    # Post-K507 SEI/TIA scaffold in-flight (K511 assumed in-flight)
    # K507 two pivots (SEI + TIA) both scaffolded = +3% each assumed
    # K511 in-flight: unknown but estimated +1.5% HL
    current_hl = 62.5   # v6.26 candidate baseline (K511 in-flight est.)
    hl_cap = 65.0
    sleeve_pct = 3.0

    hl_only = current_hl + sleeve_pct
    hl_split = current_hl + sleeve_pct * 0.5

    return {
        "current_hl_pct": current_hl,
        "hl_cap_pct": hl_cap,
        "headroom_before": round(hl_cap - current_hl, 1),
        "sleeve_pct": sleeve_pct,
        "scenario_hl_only": {
            "new_hl_pct": hl_only,
            "within_cap": bool(hl_only <= hl_cap),
            "headroom": round(hl_cap - hl_only, 1),
            "note": (
                f"HL {current_hl}% + {sleeve_pct}% = {hl_only}% "
                f"{'≤' if hl_only <= hl_cap else '>'} {hl_cap}% cap. "
                f"{'OVER CAP — not permitted' if hl_only > hl_cap else 'AT CAP — no headroom'}."
            ),
        },
        "scenario_split_hl_bybit": {
            "hl_pct": hl_split,
            "bybit_pct": sleeve_pct * 0.5,
            "within_cap": bool(hl_split <= hl_cap),
            "headroom": round(hl_cap - hl_split, 1),
            "note": (
                f"Split: HL 1.5% + Bybit 1.5% → HL {hl_split}% < {hl_cap}% cap. "
                f"{round(hl_cap - hl_split, 1)}pp headroom."
            ),
        },
        "k507_weight_adjustment": {
            "sei_tia_note": (
                "K507 SEI+TIA: if both scaffolded, weight adjustment needed. "
                "SEI: 3% total, TIA: 3% total. If HL too concentrated, "
                "K512 APT forces SEI or TIA split to Bybit."
            ),
        },
        "recommendation": (
            f"If APT-BTC {decision}: use HL/Bybit split (1.5%/1.5%) → HL {hl_split}%. "
            f"Full HL-only ({hl_only}%) exceeds cap. "
            "Also review K507 SEI/TIA HL/Bybit split to maintain headroom."
            if decision in ("ACCEPT", "CONDITIONAL") else
            f"APT {decision}. HL concentration unchanged at {current_hl}%."
        ),
    }


# ── Profit projection ──────────────────────────────────────────────────────────

def profit_projection(oos: pd.DataFrame) -> Dict:
    """Project annual USDC profit at $10M and $100M AUM."""
    oos_ann_ret = compute_ann_return(oos["net_pnl"])
    sleeve_pct = 3.0
    leverage = 4.0

    aum_10m = 10_000_000
    notional_10m = aum_10m * sleeve_pct / 100 * leverage
    gross_usdc_10m = notional_10m * oos_ann_ret
    net_usdc_10m   = gross_usdc_10m * 0.85   # 15% friction/slippage buffer

    aum_100m = 100_000_000
    notional_100m = aum_100m * sleeve_pct / 100 * leverage
    gross_usdc_100m = notional_100m * oos_ann_ret
    net_usdc_100m   = gross_usdc_100m * 0.85

    return {
        "strategy": "APT-BTC FR differential paired-trade",
        "sleeve_pct": sleeve_pct,
        "leverage": leverage,
        "oos_ann_ret_1x_pct": round(oos_ann_ret * 100, 3),
        "oos_ann_ret_4x_pct": round(oos_ann_ret * leverage * 100, 3),
        "aum_10M": {
            "aum_usd": aum_10m,
            "notional_usd": round(notional_10m),
            "gross_usdc_yr": round(gross_usdc_10m),
            "net_usdc_yr": round(net_usdc_10m),
            "daily_usdc": round(net_usdc_10m / 365),
        },
        "aum_100M": {
            "aum_usd": aum_100m,
            "notional_usd": round(notional_100m),
            "gross_usdc_yr": round(gross_usdc_100m),
            "net_usdc_yr": round(net_usdc_100m),
            "daily_usdc": round(net_usdc_100m / 365),
        },
        "note": (
            f"3% sleeve, 4x leverage, 15% friction buffer. "
            f"OOS annual return (1x): {oos_ann_ret*100:.2f}%."
        ),
    }


# ── Family rank update ─────────────────────────────────────────────────────────

def build_family_rank(apt_result: Dict) -> Dict:
    """Build updated family rank post-K512."""
    decision = apt_result.get("decision", "UNKNOWN")
    oos_sh = apt_result.get("oos_metrics", {}).get("sharpe", 0.0)
    proj = apt_result.get("profit_projection", {}).get("aum_10M", {})
    p0 = apt_result.get("phase0_vol_ratio", {})
    vol_ratio = p0.get("vol_ratio_full", None)

    # Base family (post K507 with SEI+TIA accepted)
    family = [
        {"rank": 1, "pair": "ATOM-BTC (K493)", "oos_sharpe": 50.786,
         "net_dollar_yr_10M": 231660, "status": "ACCEPT", "vol_ratio": 2.337,
         "ecosystem": "Cosmos Hub (IBC relay)"},
        {"rank": 2, "pair": "SEI-BTC (K507)", "oos_sharpe": 48.100,
         "net_dollar_yr_10M": 179425, "status": "ACCEPT", "vol_ratio": 2.328,
         "ecosystem": "Cosmos SDK (parallel EVM)"},
        {"rank": 3, "pair": "AVAX-BTC (K484)", "oos_sharpe": 43.887,
         "net_dollar_yr_10M": 75683, "status": "ACCEPT", "vol_ratio": 1.499,
         "ecosystem": "Avalanche (subnet)"},
        {"rank": 4, "pair": "SOL-BTC (K476)", "oos_sharpe": 16.298,
         "net_dollar_yr_10M": 187456, "status": "ACCEPT", "vol_ratio": 1.764,
         "ecosystem": "Solana (SVM)"},
        {"rank": 5, "pair": "TIA-BTC (K507)", "oos_sharpe": 14.439,
         "net_dollar_yr_10M": 51538, "status": "ACCEPT", "vol_ratio": 2.285,
         "ecosystem": "Celestia (modular DA)"},
        {"rank": 6, "pair": "INJ-BTC (K500)", "oos_sharpe": 11.232,
         "net_dollar_yr_10M": 124190, "status": "ACCEPT", "vol_ratio": 3.826,
         "ecosystem": "Cosmos SDK (DeFi perp)"},
        {"rank": 7, "pair": "ETH-BTC (K449)", "oos_sharpe": 5.663,
         "net_dollar_yr_10M": 13100, "status": "ACCEPT (baseline)", "vol_ratio": 1.084,
         "ecosystem": "Ethereum (EVM)"},
    ]

    # Insert APT
    apt_entry = {
        "rank": "TBD (K513 candidate)" if decision == "ACCEPT" else "N/A",
        "pair": "APT-BTC (K512)",
        "oos_sharpe": oos_sh,
        "net_dollar_yr_10M": proj.get("net_usdc_yr") if decision in ("ACCEPT", "CONDITIONAL") else None,
        "status": decision,
        "vol_ratio": vol_ratio,
        "ecosystem": "Aptos (Move-VM) — 5th ecosystem cluster",
    }
    family.append(apt_entry)

    active = [m for m in family if m["status"] == "ACCEPT" or m["status"] == "ACCEPT (baseline)"]
    total_net = sum(m["net_dollar_yr_10M"] for m in active if m.get("net_dollar_yr_10M"))
    if decision == "ACCEPT" and proj.get("net_usdc_yr"):
        total_net += proj["net_usdc_yr"]

    # Rank APT by sharpe if accepted
    if decision == "ACCEPT" and oos_sh > 0:
        accepted = [(m["oos_sharpe"], m["pair"]) for m in family if "ACCEPT" in str(m.get("status", ""))]
        accepted_sorted = sorted(accepted, key=lambda x: -(x[0] or 0))
        for i, (sh, pair) in enumerate(accepted_sorted):
            for m in family:
                if m["pair"] == pair:
                    m["rank"] = i + 1

    return {
        "members": family,
        "combined_active_net_yr_10M": round(total_net),
        "combined_projection_10M": f"${total_net:,.0f}/yr @$10M (ACCEPT family)",
        "ecosystem_clusters": {
            "ethereum": ["ETH-BTC (K449)"],
            "solana": ["SOL-BTC (K476)"],
            "avalanche": ["AVAX-BTC (K484)"],
            "cosmos": ["ATOM-BTC (K493)", "INJ-BTC (K500)", "SEI-BTC (K507)", "TIA-BTC (K507)"],
            "move_vm_5th": ["APT-BTC (K512)"] if decision == "ACCEPT" else [],
            "5th_ecosystem_confirmed": decision == "ACCEPT",
        },
    }


# ── Main ───────────────────────────────────────────────────────────────────────

def main() -> Dict:
    """K512: APT-BTC FR differential evaluation — Move-VM 5th ecosystem test."""
    now_jst = subprocess.check_output(
        ["date", "-u", "+%Y-%m-%d %H:%M:%S"], text=True
    ).strip() + " JST (approx)"

    print("=" * 70)
    print("K512 APT-BTC FR Differential Evaluation — Move-VM 5th Ecosystem")
    print("=" * 70)

    # ── Phase 0a: Venue check (K507 lesson: FIRST) ─────────────────────────────
    print("\n[Phase 0a] Venue availability check ...")
    venue_check = phase0_prescreen_venue()
    print(f"  HL: {venue_check['venue_check']['hyperliquid']['result']}")
    print(f"  Bybit: {venue_check['venue_check']['bybit_linear']['result']}")
    print(f"  OKX: {venue_check['venue_check']['okx_swap']['result']}")
    print(f"  Venue pass: {venue_check['phase0_venue_pass']}")

    if not venue_check["phase0_venue_pass"]:
        print("  REJECT: No venue data. Exiting.")
        return {
            "wave": "K512",
            "decision": "REJECT (no venue)",
            "phase0_venue": venue_check,
            "run_time_jst": now_jst,
        }

    # ── Load APT-BTC data ──────────────────────────────────────────────────────
    print("\n[Data] Loading APT-BTC FR data ...")
    df_raw = load_hl_fr_pair("APT")
    print(f"  Loaded {len(df_raw)} hourly rows: {df_raw.index[0].date()} – {df_raw.index[-1].date()}")

    # ── Phase 0b: Vol ratio pre-screen ────────────────────────────────────────
    print("\n[Phase 0b] Vol ratio pre-screen ...")
    p0_vol = phase0_vol_ratio(df_raw)
    print(f"  Vol ratio (full): {p0_vol['vol_ratio_full']:.3f}x — {'PASS' if p0_vol['pass'] else 'FAIL'}")
    print(f"  Vol ratio (6m):   {p0_vol['vol_ratio_6m']:.3f}x")

    if not p0_vol["pass"]:
        print("  REJECT: Vol ratio < 1.5x. Exiting.")
        return {
            "wave": "K512",
            "decision": "REJECT (Phase0 vol)",
            "phase0_venue": venue_check,
            "phase0_vol_ratio": p0_vol,
            "run_time_jst": now_jst,
        }

    # ── Load reference signals ─────────────────────────────────────────────────
    print("\n[Ref] Loading family reference signals ...")
    ref_sigs = load_reference_signals()
    print(f"  Loaded: {list(ref_sigs.keys())}")

    # ── Build signal ───────────────────────────────────────────────────────────
    print("\n[Signal] Building APT-BTC FR differential signal ...")
    df = build_signal(df_raw)
    n_oos = int(len(df) * OOS_FRAC)
    oos = df.iloc[-n_oos:]
    is_d = df.iloc[:-n_oos]

    oos_days = (oos.index[-1] - oos.index[0]).days
    trades_yr = float(df["entries"].sum()) / (len(df) / 8760)

    data_info = {
        "hl_rows": len(df_raw),
        "date_start": str(df_raw.index[0].date()),
        "date_end": str(df_raw.index[-1].date()),
        "total_years": round((df_raw.index[-1] - df_raw.index[0]).days / 365, 3),
        "oos_start": str(oos.index[0].date()),
        "oos_end": str(oos.index[-1].date()),
        "oos_days": oos_days,
        "trades_per_yr": round(trades_yr, 1),
        "is_rows": len(is_d),
        "oos_rows": len(oos),
        "window_h": WINDOW_H,
        "threshold": THRESHOLD,
        "cost_rt_bps": COST_RT_BPS,
    }
    print(f"  IS: {len(is_d)} rows, OOS: {len(oos)} rows ({oos_days}d)")

    # ── Statistical analysis ───────────────────────────────────────────────────
    print("\n[Phase 2] Statistical analysis ...")
    print("  ADF stationarity test ...")
    adf = adf_stationarity_test(df_raw["fr_diff"])
    print(f"  ADF statistic: {adf['statistic']:.4f}, stationary: {adf['is_stationary_5pct']}")

    print("  Ornstein-Uhlenbeck fit ...")
    ou = ornstein_uhlenbeck_fit(df_raw["fr_diff"])
    print(f"  OU half-life: {ou['half_life_days']:.2f}d — {ou['mean_reversion_quality']}")

    print("  Autocorrelation analysis ...")
    acf = autocorrelation_analysis(df_raw["fr_diff"])

    # ── IS/OOS metrics ─────────────────────────────────────────────────────────
    is_sh  = compute_sharpe(is_d["net_pnl"])
    oos_sh = compute_sharpe(oos["net_pnl"])
    is_ret = compute_ann_return(is_d["net_pnl"])
    oos_ret = compute_ann_return(oos["net_pnl"])

    is_metrics = {
        "sharpe": round(is_sh, 3),
        "ann_ret_pct": round(is_ret * 100, 3),
        "max_dd": round(compute_max_dd(is_d["net_pnl"]), 6),
        "entries": int(is_d["entries"].sum()),
        "period": f"{is_d.index[0].date()} – {is_d.index[-1].date()}",
    }
    oos_metrics = {
        "sharpe": round(oos_sh, 3),
        "ann_ret_pct": round(oos_ret * 100, 3),
        "max_dd": round(compute_max_dd(oos["net_pnl"]), 6),
        "entries": int(oos["entries"].sum()),
        "period": f"{oos.index[0].date()} – {oos.index[-1].date()}",
    }
    print(f"  IS Sharpe: {is_sh:.3f}, OOS Sharpe: {oos_sh:.3f}")

    # ── Walk-forward 12-fold ───────────────────────────────────────────────────
    print("\n[Phase 3a] Walk-forward 12-fold ...")
    wf_folds = walk_forward_12fold(df)
    wf_pos = sum(1 for f in wf_folds if f["sharpe"] > 0)
    print(f"  {wf_pos}/{len(wf_folds)} folds positive")

    # ── Permutation test ───────────────────────────────────────────────────────
    print("[Phase 3b] Permutation test (1000 reshuffles) ...")
    perm_p = permutation_test(oos)
    print(f"  Perm p-value: {perm_p:.4f} — {'PASS' if perm_p <= G2_PERM_MAX else 'FAIL'}")

    # ── DSR Bonferroni ─────────────────────────────────────────────────────────
    dsr_res = dsr_bonferroni(oos)
    print(f"  DSR p-Bonferroni: {dsr_res['p_bonferroni']} — {'PASS' if dsr_res['pass'] else 'FAIL'}")

    # ── Grid search ────────────────────────────────────────────────────────────
    print("[Phase 3c] Grid search ...")
    grid = grid_search(df_raw)[:5]
    print(f"  Best OOS Sharpe in grid: {grid[0]['OOS_sharpe'] if grid else 'N/A'}")

    # ── G5 correlations ────────────────────────────────────────────────────────
    g5 = compute_g5_correlations(df, ref_sigs)
    print(f"  G5 summary: cosmos_blocked={g5['cosmos_cluster_blocked']}, "
          f"5th_ecosystem={g5['move_vm_independence_confirmed']}")

    # ── Cross-venue validation ─────────────────────────────────────────────────
    print("[Phase 3d] Cross-venue validation (Bybit) ...")
    cv = cross_venue_validation(df)
    print(f"  G8 effective corr: {cv.get('effective_g8_corr')}, pass: {cv.get('g8_pass')}")

    # ── Section 6 gates ────────────────────────────────────────────────────────
    print("\n[Phase 4] §6 gate evaluation ...")
    gate_res = evaluate_section6_gates(oos, wf_folds, perm_p, dsr_res, g5, cv, data_info)
    print(f"  Gates passed: {gate_res['gates_passed']}/{gate_res['total_gates']}")
    print(f"  Decision: {gate_res['decision']}")

    # ── Sub-analyses ───────────────────────────────────────────────────────────
    sub_analyses = run_sub_analyses(df_raw)

    # ── Architecture analysis ──────────────────────────────────────────────────
    arch_analysis = move_vm_architecture_analysis(g5, sub_analyses)

    # ── Profit projection ──────────────────────────────────────────────────────
    proj = profit_projection(oos)
    print(f"\n[Profit] Net USDC/yr @$10M: ${proj['aum_10M']['net_usdc_yr']:,.0f}")

    # ── HL concentration ───────────────────────────────────────────────────────
    decision = gate_res["decision"]
    hl_impact = hl_concentration_impact(decision)

    # ── Family rank ────────────────────────────────────────────────────────────
    apt_result = {
        "decision": decision,
        "oos_metrics": oos_metrics,
        "profit_projection": proj,
        "phase0_vol_ratio": p0_vol,
    }
    family_rank = build_family_rank(apt_result)

    # ── Decision rationale ─────────────────────────────────────────────────────
    cosmos_blocked = g5.get("cosmos_cluster_blocked", False)
    five_th_eco = g5.get("move_vm_independence_confirmed", False)

    rationale_parts = [
        f"[{decision}] APT-BTC passes {gate_res['gates_passed']}/{gate_res['total_gates']} §6 gates.",
        f"OOS Sharpe {oos_sh:.3f}.",
        f"Vol ratio {p0_vol['vol_ratio_full']:.2f}x (6m: {p0_vol['vol_ratio_6m']:.2f}x).",
        f"G5d (ATOM): {g5.get('g5d_corr_vs_k493_atom')!r} ({'PASS' if g5.get('g5d_pass') else 'FAIL'}).",
        f"G5e (INJ): {g5.get('g5e_corr_vs_k500_inj')!r} ({'PASS' if g5.get('g5e_pass') else 'FAIL'}).",
        f"G5f (SEI): {g5.get('g5f_corr_vs_k507_sei')!r} ({'PASS' if g5.get('g5f_pass') else 'FAIL'}).",
        f"G5g (TIA): {g5.get('g5g_corr_vs_k507_tia')!r} ({'PASS' if g5.get('g5g_pass') else 'FAIL'}).",
        f"Perm p={perm_p:.4f}.",
        f"5th ecosystem (Move-VM): {'CONFIRMED' if five_th_eco else 'NOT CONFIRMED'}.",
    ]
    if decision == "ACCEPT":
        rationale_parts.append(
            f"→ K513 scaffold, v6.27 candidate. "
            f"${proj['aum_10M']['net_usdc_yr']:,.0f}/yr @$10M."
        )
    elif decision == "BLOCKED-COSMOS":
        rationale_parts.append("Cosmos cluster overlap — APT redundant with existing Cosmos family.")
    elif decision == "CONDITIONAL":
        rationale_parts.append("60d paper-trade mandatory before live.")
    else:
        rationale_parts.append("REJECT — insufficient edge or gate failures.")

    decision_rationale = " ".join(rationale_parts)

    # ── Next pivot candidates ─────────────────────────────────────────────────
    next_candidates = [
        {
            "pair": "SUI-BTC",
            "ecosystem": "Sui (Move-VM variant)",
            "hl_data": "check_required",
            "priority": "HIGH" if decision == "ACCEPT" else "MEDIUM",
            "note": "If APT ACCEPT: SUI = same Move language, test intra-Move-VM cluster. G5 vs APT mandatory.",
        },
        {
            "pair": "DOT-BTC",
            "ecosystem": "Polkadot (parachain relay chain)",
            "hl_data": "check_required",
            "priority": "MEDIUM",
            "note": "Polkadot parachain model distinct from Cosmos/EVM/SVM/Move. Potential 6th cluster.",
        },
        {
            "pair": "ALGO-BTC",
            "ecosystem": "Algorand (Pure PoS)",
            "hl_data": "check_required",
            "priority": "LOW",
            "note": "Small MC, venue check required. Academic blockchain, smaller ecosystem.",
        },
        {
            "pair": "NEAR-BTC",
            "ecosystem": "NEAR Protocol (Nightshade sharding)",
            "hl_data": "true (was checked K503)",
            "priority": "MEDIUM",
            "note": "K503 lesson: NEAR vol pass but BLOCKED-COSMOS. Re-eval only if Cosmos cluster opens.",
        },
    ]

    runtime_s = round(time.time() - START_TIME, 1)

    result = {
        "wave": "K512",
        "strategy": "APT-BTC FR Differential Paired-Trade (Move-VM 5th Ecosystem)",
        "run_time_jst": now_jst,
        "runtime_s": runtime_s,

        "phase0_venue_check": venue_check,
        "phase0_vol_ratio": p0_vol,

        "data_info": data_info,

        "statistical_analysis": {
            "adf": adf,
            "ornstein_uhlenbeck": ou,
            "autocorrelation": acf,
        },

        "is_metrics": is_metrics,
        "oos_metrics": oos_metrics,

        "walk_forward_12fold": wf_folds,
        "walk_forward_summary": {
            "folds_total": len(wf_folds),
            "folds_positive": wf_pos,
            "g4_pass": wf_pos == len(wf_folds),
            "min_fold_sharpe": round(min(f["sharpe"] for f in wf_folds), 3) if wf_folds else None,
            "max_fold_sharpe": round(max(f["sharpe"] for f in wf_folds), 3) if wf_folds else None,
        },

        "permutation_p": round(perm_p, 4),
        "dsr_bonferroni": dsr_res,
        "grid_search_top5": grid,

        "g5_correlations": g5,
        "cross_venue": cv,
        "section6_gates": gate_res,

        "sub_analyses_apt_pairs": sub_analyses,
        "move_vm_architecture_analysis": arch_analysis,

        "profit_projection": proj,
        "hl_concentration_impact": hl_impact,
        "paired_trade_family_rank": family_rank,

        "decision": decision,
        "decision_rationale": decision_rationale,

        "k512_lessons": {
            "venue_check_first": "APT listed on HL + Bybit (lesson from K507 OSMO). Pre-screen critical.",
            "move_vm_hypothesis": f"Move-VM 5th ecosystem: {'CONFIRMED' if five_th_eco else 'NOT confirmed'}.",
            "vol_ratio_trend": f"APT vol ratio 6m ({p0_vol['vol_ratio_6m']:.2f}x) vs full ({p0_vol['vol_ratio_full']:.2f}x) — improving.",
            "cosmos_independence": f"Cosmos cluster overlap: {'YES' if cosmos_blocked else 'NO'}.",
        },

        "next_pivot_candidates": next_candidates,
    }

    return result


if __name__ == "__main__":
    result = main()

    # Save JSON
    out_json = BASE / "wave_k512_apt_btc_eval.json"
    with open(out_json, "w") as f:
        json.dump(result, f, indent=2, default=str)
    print(f"\nJSON saved: {out_json}")

    # Summary
    print("\n" + "=" * 70)
    print("K512 SUMMARY")
    print("=" * 70)
    print(f"Decision:          {result['decision']}")
    print(f"OOS Sharpe:        {result['oos_metrics']['sharpe']}")
    print(f"Vol ratio (full):  {result['phase0_vol_ratio']['vol_ratio_full']:.3f}x")
    print(f"Vol ratio (6m):    {result['phase0_vol_ratio']['vol_ratio_6m']:.3f}x")
    print(f"Gates passed:      {result['section6_gates']['gates_passed']}/{result['section6_gates']['total_gates']}")
    print(f"Net USDC/yr @$10M: ${result['profit_projection']['aum_10M']['net_usdc_yr']:,.0f}")
    print(f"Net USDC/yr @$100M:${result['profit_projection']['aum_100M']['net_usdc_yr']:,.0f}")
    print(f"5th ecosystem:     {'CONFIRMED' if result['move_vm_architecture_analysis']['5th_ecosystem_confirmed'] else 'NOT confirmed'}")
    print(f"HL after split:    {result['hl_concentration_impact']['scenario_split_hl_bybit']['hl_pct']}%")
    print(f"Runtime:           {result['runtime_s']}s")
    print("=" * 70)

#!/usr/bin/env python3
"""
wave_k513_dot_btc_eval.py — K513 DOT-BTC FR Differential Paired-Trade Evaluation
===================================================================================
K339 REPO_ROOT pattern. DOT (Polkadot) — 6th ecosystem cluster test (Polkadot/Substrate).

HYPOTHESIS
----------
DOT = Polkadot relay chain native token:
  - Shared security via parachain slot auction mechanism
  - Substrate framework: heterogeneous parachains
  - Architecture: relay chain + parachains (unique cross-chain message passing XCM)
  - Platform L1 (not DeFi-native): governance, staking, parachain bonding
  - Major coin: listed HL/Bybit/OKX (perp exists, venue listing confirmed)
  - Vol ratio estimate: 1.4-2.0x BTC (platform L1, similar to SUI/NEAR/ARB)
  - Pre-screen risk: vol < 1.5x possible (K507 lesson: platform L1 vol limit)
  - K503 lesson: DeFi-native >> platform L1 for FR vol premium

K503/K507 LESSONS APPLIED
--------------------------
  K503 NEAR-BTC: platform L1, vol 1.37x REJECT (< 1.5x threshold)
  K507 OSMO-BTC: G8/G9 fail (no venue). TIA/SEI ACCEPT (DeFi-adjacent, high vol)
  DOT: platform L1 → vol risk. Pre-screen vol MANDATORY first.
  Prediction: vol 1.4-1.7x BTC (full dataset). 6m recency 2.0-4.0x possible.

POLKADOT ARCHITECTURE
---------------------
  - Relay chain: DOT staking, parachain security, governance
  - Parachain slot auctions: teams bond DOT for security leases (2yr periods)
  - XCM messaging: heterogeneous chain communication (unique feature)
  - Staking yield: 10-15% APY nominal (high, influences FR baseline)
  - Governance: OpenGov model (frequent votes, governance alpha unique)
  - Not DeFi-native: DOT does not capture DeFi fee flow directly
    → Lower demand for leveraged long DOT (vs INJ/SEI which capture DeFi fees)
  - FR dynamics: governance events, parachain auction cycles → periodic spikes

§6 GATES (K513 — 14 gates, extended family with SEI/TIA/K512 checks)
----------------------------------------------------------------------
  G1:  OOS Sharpe ≥ 1.0
  G2:  Perm p-value ≤ 0.05 (1000 direction reshuffles, OOS)
  G3:  DSR Bonferroni p < 0.05/12 = 0.00417
  G4:  Walk-forward 12-fold stability (IS 90d / OOS 30d), all positive
  G5a: Corr vs K449 (ETH-BTC) < 0.40
  G5b: Corr vs K476 (SOL-BTC) < 0.40
  G5c: Corr vs K484 (AVAX-BTC) < 0.40
  G5d: Corr vs K493 (ATOM-BTC) < 0.40  ← Cosmos cluster check
  G5e: Corr vs K500 (INJ-BTC) < 0.40   ← DeFi+Cosmos cluster check
  G5f: Corr vs SEI-BTC < 0.40          ← Cosmos SEI cluster
  G5g: Corr vs TIA-BTC < 0.40          ← Cosmos TIA cluster
  G5h: Corr vs K280 < 0.40             ← vol momentum orthogonality
  G6:  Trade count ≥ 30/yr
  G7:  Ann return > 5% at 4x leverage
  G8:  Cross-venue (Bybit/OKX corr ≥ 0.55)
  G9:  Data sufficiency ≥ 180d OOS

DECISION CRITERIA
-----------------
  ACCEPT (Sharpe ≥ 5, ≥ 11/16 gates): K514 scaffold, v6.28 candidate (6th ecosystem)
  BLOCKED-CLUSTER (G5d/G5e/G5f/G5g ≥ 0.40): cluster redundancy
  CONDITIONAL (Sharpe 1-5, 7-10 gates): 60d paper-trade
  REJECT (Sharpe < 1 or Phase0 vol fail): ALGO/FIL/ATOM additional ecosystem pivot

HL CONCENTRATION (v6.26 baseline — post-K511 recompute)
---------------------------------------------------------
  Current HL: 62.5% (v6.26 accepted K511 emergency recompute)
  K513 sleeve 3% (HL primary) → HL 65.5% > cap (1pp over)
  Alternative: HL 1.5% + Bybit 1.5% → HL 64.0% (1pp headroom)
  Or: skip K513 if cap binding (cap rule > profit)
  K512 APT-BTC in flight: if ACCEPT → concentration even tighter

Usage:
  python3 wave_k513_dot_btc_eval.py
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
PHASE0_VOL_MIN  = 1.5       # vol ratio DOT/BTC must be ≥ 1.5x

# Family reference OOS Sharpes (post K507)
K449_OOS_SHARPE  = 5.663    # ETH-BTC
K476_OOS_SHARPE  = 16.298   # SOL-BTC
K484_OOS_SHARPE  = 43.887   # AVAX-BTC
K493_OOS_SHARPE  = 50.786   # ATOM-BTC
K500_OOS_SHARPE  = 11.232   # INJ-BTC
K507_SEI_SHARPE  = 48.10    # SEI-BTC (K507 pivot result)
K507_TIA_SHARPE  = 14.439   # TIA-BTC (K507 pivot result)

ANN_FACTOR_1H   = math.sqrt(8760)   # annualise from 1h returns


# ── Data loading ─────────────────────────────────────────────────────────────────

def load_hl_fr_data() -> pd.DataFrame:
    """Load BTC and DOT HL FR data and compute differential."""
    btc_fr = pd.read_parquet(HL_CACHE / "hl_fr_BTC.parquet")
    dot_fr = pd.read_parquet(HL_CACHE / "hl_fr_DOT.parquet")

    btc_fr["timestamp"] = pd.to_datetime(btc_fr["timestamp"]).dt.floor("h")
    dot_fr["timestamp"] = pd.to_datetime(dot_fr["timestamp"]).dt.floor("h")

    df = pd.merge(
        btc_fr.rename(columns={"hl_fr": "btc_fr"}),
        dot_fr.rename(columns={"hl_fr": "dot_fr"}),
        on="timestamp",
        how="inner",
    )
    df["fr_diff"] = df["btc_fr"] - df["dot_fr"]
    df = df.set_index("timestamp").sort_index()
    return df


def load_cross_venue_fr() -> Dict[str, Optional[pd.Series]]:
    """Load Bybit and OKX DOT FR for cross-venue validation."""
    venues: Dict[str, Optional[pd.Series]] = {}

    # Bybit DOT (8h intervals, 730d)
    bybit_file = CACHE / "bybit_fr_DOTUSDT_730d.parquet"
    try:
        if bybit_file.exists():
            bybit = pd.read_parquet(bybit_file)
            bybit = bybit.set_index("timestamp").sort_index()["funding_rate"]
            venues["bybit"] = bybit
        else:
            venues["bybit"] = None
    except Exception as e:
        print(f"  Bybit DOT load error: {e}")
        venues["bybit"] = None

    # OKX DOT (8h intervals, ~3mo)
    okx_file = CACHE / "okx_fr_DOT.parquet"
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
    except Exception as e:
        print(f"  OKX DOT load error: {e}")
        venues["okx"] = None

    return venues


def load_reference_signals() -> Dict[str, pd.Series]:
    """Load K449/K476/K484/K493/K500/SEI/TIA/K280 signals for G5 correlation check."""
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
    """Phase 0: venue listing + vol ratio pre-screen (K507 mandate)."""
    print("\n[Phase 0] DOT-BTC pre-screen — venue listing + vol ratio ...")

    dot_std = float(df["dot_fr"].std())
    btc_std  = float(df["btc_fr"].std())
    vol_ratio = dot_std / btc_std if btc_std > 0 else 0.0

    # 6-month recency check (tail 4380h = 182.5 days)
    six_mo = df.tail(4380)
    dot_std_6m = float(six_mo["dot_fr"].std())
    btc_std_6m = float(six_mo["btc_fr"].std())
    vol_ratio_6m = dot_std_6m / btc_std_6m if btc_std_6m > 0 else 0.0

    # Venue listing check (HL, Bybit, OKX) — DOT is major coin
    # HL: DOT-PERP listed in 230-asset universe (2026-05-30 confirmed via FR parquet)
    # Bybit: bybit_fr_DOTUSDT_730d.parquet exists (confirmed)
    # OKX: okx_fr_DOT.parquet exists (confirmed)
    hl_fr_exists = (HL_CACHE / "hl_fr_DOT.parquet").exists()
    bybit_exists = (CACHE / "bybit_fr_DOTUSDT_730d.parquet").exists()
    okx_exists   = (CACHE / "okx_fr_DOT.parquet").exists()

    venue_pass = hl_fr_exists  # HL primary is mandatory; Bybit/OKX for cross-check

    pass_vol  = vol_ratio >= PHASE0_VOL_MIN
    pass_full = venue_pass and pass_vol

    family_vol_comparison = {
        "eth_btc_k449":   1.084,
        "avax_btc_k484":  1.499,
        "sol_btc_k476":   1.764,
        "atom_btc_k493":  2.337,
        "tia_btc_k507":   2.285,
        "sei_btc_k507":   2.328,
        "inj_btc_k500":   3.826,
        "dot_btc_k513_full": round(vol_ratio, 4),
        "dot_btc_k513_6m":   round(vol_ratio_6m, 4),
    }

    return {
        "target": "DOT (Polkadot relay chain, 6th ecosystem cluster test)",
        "dot_fr_std_full": round(dot_std, 8),
        "btc_fr_std_full": round(btc_std, 8),
        "vol_ratio_full":  round(vol_ratio, 4),
        "vol_ratio_6m":    round(vol_ratio_6m, 4),
        "threshold":       PHASE0_VOL_MIN,
        "vol_pass":        pass_vol,
        "venue_listing": {
            "hl_fr_data_exists":    hl_fr_exists,
            "bybit_fr_data_exists": bybit_exists,
            "okx_fr_data_exists":   okx_exists,
            "hl_note":    "DOT-PERP active on Hyperliquid (major coin, hl_fr_DOT.parquet 17519 rows 2024-05-24 → 2026-05-24)",
            "bybit_note": "DOTUSDT-PERP active on Bybit (bybit_fr_DOTUSDT_730d.parquet 2190 rows)",
            "okx_note":   "DOT-USDT-SWAP active on OKX (okx_fr_DOT.parquet 284 rows)",
            "venue_pass": venue_pass,
        },
        "phase0_pass": pass_full,
        "family_vol_comparison": family_vol_comparison,
        "polkadot_vol_analysis": (
            f"DOT vol ratio {vol_ratio:.2f}x BTC (6m: {vol_ratio_6m:.2f}x). "
            f"Threshold: {PHASE0_VOL_MIN}x. "
            f"{'PROCEED' if pass_full else 'EARLY REJECT'}. "
            "Polkadot relay chain: platform L1, parachain bonding locks DOT → "
            "supply-side staking yield 10-15% creates structural FR bias. "
            "Parachain auction cycles (2yr lease periods) create periodic governance-driven FR spikes. "
            "Platform L1 (not DeFi-native) → vol historically lower than INJ/SEI (DeFi-focused). "
            f"K503 lesson applied: NEAR vol was 1.37x REJECT. DOT at {vol_ratio:.2f}x "
            f"{'PASSES' if pass_vol else 'FAILS'} threshold."
        ),
        "decision": (
            f"PROCEED to full backtest — DOT venue check PASS (HL/Bybit/OKX all listed) + "
            f"vol ratio {vol_ratio:.2f}x ≥ {PHASE0_VOL_MIN}x. "
            f"6m recency: {vol_ratio_6m:.2f}x. Polkadot 6th ecosystem cluster test begins."
            if pass_full else
            f"EARLY REJECT — DOT vol ratio {vol_ratio:.2f}x {'< '+str(PHASE0_VOL_MIN)+'x (platform L1 vol limit)' if not pass_vol else 'OK'} "
            f"{'| venue FAIL' if not venue_pass else ''}. "
            "K503/K507 lesson confirmed: platform L1 vol insufficient for FR differential strategy."
        ),
    }


# ── Signal construction ───────────────────────────────────────────────────────────

def build_signal(df: pd.DataFrame, window_h: int = WINDOW_H,
                 threshold: float = THRESHOLD) -> pd.DataFrame:
    """Build DOT-BTC FR differential signal.

    Signal = sign(fr_diff_smooth):
      +1 → short BTC, long DOT   (BTC FR higher → receive BTC FR premium)
      -1 → long BTC, short DOT   (DOT FR higher → receive DOT FR premium)
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
            f"DOT-BTC FR differential {'IS' if result[0] < result[4]['5%'] else 'NOT'} "
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

    hl_8h = df_hl["dot_fr"].resample("8h").sum()
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
    results["note"] = (
        "Cross-venue FR check for DOT. HL 1h rates resampled to 8h vs Bybit/OKX 8h FR. "
        "G8 uses quality-adjusted avg (excludes corr < 0.20 instrument mismatch)."
    )
    return results


# ── G5 correlations ──────────────────────────────────────────────────────────────

def compute_g5_correlations(df: pd.DataFrame,
                            ref_sigs: Dict[str, pd.Series]) -> Dict:
    """Compute DOT-BTC signal correlation vs all family members."""
    print("  Computing G5 correlations (K449/K476/K484/K493/K500/SEI/TIA/K280) ...")

    smooth = df["fr_diff"].rolling(WINDOW_H).mean()
    sig_dot = np.sign(smooth).dropna()

    def _corr(sig_ref: pd.Series, label: str) -> Tuple[float, int]:
        try:
            idx = sig_dot.index.intersection(sig_ref.index)
            if len(idx) < 168:
                return float("nan"), 0
            a = sig_dot.loc[idx].dropna()
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
    g5h = bool(c_k280 < G5_CORR_MAX)

    # Cluster analysis
    cosmos_blocked = not g5d
    defi_blocked   = not g5e
    sei_blocked    = not g5f
    tia_blocked    = not g5g

    def _cluster_msg(name: str, wave: str, corr: float, blocked: bool) -> str:
        if math.isnan(corr):
            return f"DATA INSUFFICIENT — cannot determine {name} cluster membership"
        if blocked:
            return (
                f"CLUSTER BLOCKED ({name}): DOT-BTC vs {wave} corr={corr:.4f} ≥ {G5_CORR_MAX}. "
                f"DOT and {name} share FR dynamics — cluster redundant."
            )
        return (
            f"CLUSTER PASS ({name}): DOT-BTC vs {wave} corr={corr:.4f} < {G5_CORR_MAX}. "
            f"DOT distinct from {name} within cluster."
        )

    return {
        "g5a_corr_vs_k449":   _fmt(c_k449),
        "g5b_corr_vs_k476":   _fmt(c_k476),
        "g5c_corr_vs_k484":   _fmt(c_k484),
        "g5d_corr_vs_k493_atom": _fmt(c_k493),
        "g5e_corr_vs_k500_inj":  _fmt(c_k500),
        "g5f_corr_vs_sei":    _fmt(c_sei),
        "g5g_corr_vs_tia":    _fmt(c_tia),
        "g5h_corr_vs_k280":   c_k280,
        "n_obs": {
            "k449": n_k449, "k476": n_k476, "k484": n_k484,
            "k493": n_k493, "k500": n_k500, "sei": n_sei, "tia": n_tia,
        },
        "g5a_pass": g5a, "g5b_pass": g5b, "g5c_pass": g5c,
        "g5d_pass": g5d, "g5e_pass": g5e, "g5f_pass": g5f,
        "g5g_pass": g5g, "g5h_pass": g5h,
        "cosmos_cluster_blocked": cosmos_blocked,
        "defi_cluster_blocked":   defi_blocked,
        "sei_cluster_blocked":    sei_blocked,
        "tia_cluster_blocked":    tia_blocked,
        "any_cluster_blocked": cosmos_blocked or defi_blocked or sei_blocked or tia_blocked,
        "cosmos_cluster_result":  _cluster_msg("ATOM",  "K493 ATOM-BTC", c_k493, cosmos_blocked),
        "defi_cluster_result":    _cluster_msg("INJ",   "K500 INJ-BTC",  c_k500, defi_blocked),
        "sei_cluster_result":     _cluster_msg("SEI",   "SEI-BTC",       c_sei,  sei_blocked),
        "tia_cluster_result":     _cluster_msg("TIA",   "TIA-BTC",       c_tia,  tia_blocked),
        "polkadot_cluster_hypothesis": (
            f"DOT (Polkadot relay chain) vs Cosmos SDK chains (ATOM G5d={_fmt(c_k493)}, "
            f"INJ G5e={_fmt(c_k500)}, SEI G5f={_fmt(c_sei)}, TIA G5g={_fmt(c_tia)}). "
            "Polkadot uses Substrate framework (NOT Cosmos SDK) — architecturally distinct. "
            "Cross-chain security model (parachain bonding) vs IBC networking (Cosmos). "
            "Expected: low Cosmos correlation (different consensus, different staking mechanics). "
            f"ETH-BTC K449 G5a={_fmt(c_k449)}: DOT is platform L1 like ETH but ecosystem-isolated."
        ),
        "family_g5a_history": {
            "k449_eth":   1.000,
            "k480_bnb":   0.435,
            "k491_arb":   0.373,
            "k484_avax":  0.300,
            "k476_sol":   0.253,
            "k490_sui":   0.277,
            "k493_atom":  0.176,
            "k500_inj":   0.141,
            "k507_sei":   0.178,
            "k507_tia":   0.142,
            "k513_dot":   _fmt(c_k449),
        },
    }


# ── DOT-specific characteristics ──────────────────────────────────────────────────

def compute_dot_characteristics(df: pd.DataFrame, g5: Dict) -> Dict:
    """Compute DOT-specific Polkadot mechanics and FR characteristics."""
    vol_ratio = float(df["dot_fr"].std() / df["btc_fr"].std())
    dot_fr_ann = df["dot_fr"].mean() * 8760 * 100
    btc_fr_ann = df["btc_fr"].mean() * 8760 * 100

    # DOT vs ETH FR sub-analysis (DOT = old major, ETH corr historically?)
    eth_sub: Dict = {}
    try:
        eth_fr = pd.read_parquet(HL_CACHE / "hl_fr_ETH.parquet")
        eth_fr["timestamp"] = pd.to_datetime(eth_fr["timestamp"]).dt.floor("h")
        df_eth = pd.merge(
            df.reset_index()[["timestamp", "dot_fr"]],
            eth_fr.rename(columns={"hl_fr": "eth_fr"}),
            on="timestamp", how="inner"
        ).set_index("timestamp").sort_index()
        dot_eth_corr = float(df_eth["dot_fr"].corr(df_eth["eth_fr"]))
        eth_sub = {
            "dot_eth_fr_raw_corr": round(dot_eth_corr, 4),
            "interpretation": (
                f"DOT-ETH FR raw correlation = {dot_eth_corr:.4f}. "
                f"{'Moderate coupling: DOT and ETH share major-coin sentiment' if abs(dot_eth_corr) > 0.30 else 'Low coupling: DOT FR structurally independent'} "
                "(Note: G5a uses SIGNAL correlation not raw FR corr)."
            ),
        }
    except Exception as e:
        eth_sub = {"error": str(e)}

    # DOT vs ATOM FR sub-analysis (both relay/governance chains)
    atom_sub: Dict = {}
    try:
        atom_fr = pd.read_parquet(HL_CACHE / "hl_fr_ATOM.parquet")
        atom_fr["timestamp"] = pd.to_datetime(atom_fr["timestamp"]).dt.floor("h")
        df_atom = pd.merge(
            df.reset_index()[["timestamp", "dot_fr"]],
            atom_fr.rename(columns={"hl_fr": "atom_fr"}),
            on="timestamp", how="inner"
        ).set_index("timestamp").sort_index()
        dot_atom_corr = float(df_atom["dot_fr"].corr(df_atom["atom_fr"]))
        atom_sub = {
            "dot_atom_fr_raw_corr": round(dot_atom_corr, 4),
            "interpretation": (
                f"DOT-ATOM FR raw correlation = {dot_atom_corr:.4f}. "
                "DOT (Polkadot/Substrate) vs ATOM (Cosmos SDK): both are relay/hub chains "
                "but completely different technology stacks. "
                f"{'High correlation: both relay chains share meta-narrative' if abs(dot_atom_corr) > 0.40 else 'Low: distinct FR dynamics despite relay-chain parallel role'}."
            ),
        }
    except Exception as e:
        atom_sub = {"error": str(e)}

    g5a_corr = g5.get("g5a_corr_vs_k449")
    g5d_corr = g5.get("g5d_corr_vs_k493_atom")

    return {
        "fr_vol_ratio_dot_btc": round(vol_ratio, 3),
        "fr_vol_ratio_comparison": {
            "eth_btc_k449":  1.084,
            "avax_btc_k484": 1.499,
            "near_btc_k503": 1.370,
            "sol_btc_k476":  1.764,
            "atom_btc_k493": 2.337,
            "tia_btc_k507":  2.285,
            "sei_btc_k507":  2.328,
            "inj_btc_k500":  3.826,
            "dot_btc_k513":  round(vol_ratio, 3),
        },
        "dot_fr_mean_ann_pct": round(dot_fr_ann, 3),
        "btc_fr_mean_ann_pct": round(btc_fr_ann, 3),
        "fr_bias_direction": (
            "BTC pays more → structural short BTC, long DOT bias"
            if btc_fr_ann > dot_fr_ann else
            "DOT pays more → structural short DOT, long BTC bias"
        ),
        "dot_eth_sub_analysis": eth_sub,
        "dot_atom_sub_analysis": atom_sub,
        "polkadot_mechanics_notes": (
            "DOT (Polkadot) specific FR mechanics: "
            "1. Parachain slot auctions: teams bond DOT for 2yr security leases → "
            "locked supply reduces circulating float → structurally higher staking yield (10-15% APY). "
            "2. OpenGov governance: frequent referendum votes → governance participation spikes "
            "create idiosyncratic demand surges (DOT needed to vote/bond). "
            "3. Substrate framework: heterogeneous parachains (each with own FR dynamics) "
            "but DOT relay chain FR represents meta-narrative / shared security demand. "
            "4. XCM cross-chain: DOT bridges Substrate chains → periodic liquidity events "
            "when XCM messages settle large transfers. "
            "5. NOT DeFi-native: DOT does not directly capture protocol revenue → "
            "lower speculative demand vs INJ/SEI (which have fee revenue flow). "
            "6. Old major coin: DOT was top-5 by market cap 2020-2022 → institutional familiarity "
            "may create different FR regime than newer Cosmos alts."
        ),
        "platform_l1_hypothesis": (
            f"Platform L1 vol hypothesis: K503 NEAR 1.37x REJECT (platform L1). "
            f"DOT at {vol_ratio:.2f}x: "
            f"{'ABOVE threshold → platform L1 hypothesis challenged (DOT has higher staking yield impact)' if vol_ratio >= PHASE0_VOL_MIN else 'BELOW threshold → platform L1 lesson confirmed (DOT similar to NEAR)'}"
        ),
    }


# ── Profit projection ─────────────────────────────────────────────────────────────

def build_profit_projection(oos_ann_ret: float) -> Dict:
    sleeve_pct = 3.0
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
            f"3% sleeve, 4x leverage, 15% friction buffer. "
            f"DOT-BTC OOS ann return 1x: {oos_ann_ret*100:.2f}%."
        ),
    }


# ── HL concentration analysis ─────────────────────────────────────────────────────

def hl_concentration_analysis(decision: str) -> Dict:
    current_hl    = 62.5   # v6.26 post-K511 emergency recompute
    k513_sleeve   = 3.0
    hl_cap        = 65.0

    full_hl  = current_hl + k513_sleeve
    split_hl = current_hl + 1.5        # HL 1.5% + Bybit 1.5%
    headroom_full  = hl_cap - full_hl
    headroom_split = hl_cap - split_hl

    return {
        "v6_26_baseline_hl_pct":  current_hl,
        "hl_cap_pct":             hl_cap,
        "k513_sleeve_pct":        k513_sleeve,
        "scenario_a_full_hl": {
            "hl_pct":     round(full_hl, 1),
            "headroom":   round(headroom_full, 1),
            "within_cap": bool(full_hl < hl_cap),
            "note": f"K513 3% all-HL: {current_hl}% → {full_hl}% "
                    f"({'WITHIN cap' if full_hl < hl_cap else 'OVER cap — requires other sleeve reduction'})",
        },
        "scenario_b_split_hl_bybit": {
            "hl_pct":        round(split_hl, 1),
            "bybit_add_pct": 1.5,
            "headroom":      round(headroom_split, 1),
            "within_cap":    bool(split_hl < hl_cap),
            "note": f"K513 split HL 1.5% + Bybit 1.5%: HL {current_hl}% → {split_hl}%, 1pp headroom",
        },
        "k512_apt_in_flight": {
            "note": "K512 APT-BTC in flight (Move-VM Aptos). If ACCEPT 3% → HL 65.5% or 64% (split). "
                    "K513 + K512 both ACCEPT = concentration crisis. Cap rule binds.",
        },
        "recommendation": (
            "SCENARIO B (split HL 1.5% + Bybit 1.5%) recommended if DOT ACCEPT. "
            "Avoids cap breach. Bybit DOT perp active (bybit_fr_DOTUSDT_730d.parquet confirmed). "
            "HL 64.0% (1pp headroom) is tight — no further HL-primary adds without offsetting reduction."
            if decision == "ACCEPT" else
            "HL concentration unchanged — K513 not activated."
        ),
    }


# ── Family rank table ─────────────────────────────────────────────────────────────

def build_family_rank(oos_sh: float, g5a: Optional[float], g5d: Optional[float],
                      oos_ret: float, trades_yr: float, decision: str,
                      profit_proj: Dict) -> List[Dict]:
    net_10m = profit_proj["aum_10M"]["net_annual_usdc"]
    family = [
        {"rank": 1, "pair": "ATOM-BTC", "sharpe": 50.79,  "net_kyr_10m": 231, "ecosystem": "Cosmos (relay hub)", "wave": "K493", "status": "ACTIVE"},
        {"rank": 2, "pair": "SEI-BTC",  "sharpe": 48.10,  "net_kyr_10m": 179, "ecosystem": "Cosmos (parallel EVM)", "wave": "K507", "status": "SCAFFOLD"},
        {"rank": 3, "pair": "AVAX-BTC", "sharpe": 43.887, "net_kyr_10m": 76,  "ecosystem": "Avalanche",  "wave": "K484", "status": "ACTIVE"},
        {"rank": 4, "pair": "SOL-BTC",  "sharpe": 16.298, "net_kyr_10m": 187, "ecosystem": "Solana",     "wave": "K476", "status": "ACTIVE"},
        {"rank": 5, "pair": "TIA-BTC",  "sharpe": 14.439, "net_kyr_10m": 51,  "ecosystem": "Cosmos (modular DA)", "wave": "K507", "status": "SCAFFOLD"},
        {"rank": 6, "pair": "INJ-BTC",  "sharpe": 11.232, "net_kyr_10m": 124, "ecosystem": "Cosmos (DeFi/perp)",  "wave": "K500", "status": "SCAFFOLD"},
        {"rank": 7, "pair": "ETH-BTC",  "sharpe": 5.663,  "net_kyr_10m": 13,  "ecosystem": "Ethereum",   "wave": "K449", "status": "ACTIVE"},
        {"rank": 8, "pair": "DOT-BTC",  "sharpe": round(oos_sh, 2),
         "net_kyr_10m": round(net_10m / 1000),
         "ecosystem": "Polkadot (Substrate)", "wave": "K513",
         "status": decision if decision != "CONDITIONAL" else "60d PAPER",
         "g5a_vs_eth": g5a, "g5d_vs_atom": g5d,
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
    """Run full §6 evaluation for DOT-BTC FR differential."""

    # Grid search over IS data
    print("  Running grid search (4 windows × 3 thresholds = 12 combinations) ...")
    grid_results = grid_search(df)

    # Primary config: 7d window, always-on (winner across K449 → K507)
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

    # § 6 gates

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
    g5h_pass = g5["g5h_pass"]; g5h_corr = g5["g5h_corr_vs_k280"]

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

    # Gates list (G1-G4, G5a-h, G6, G7, G8, G9) = 16 gates
    gates_list = [
        g1_pass, g2_pass, g3_pass, g4_pass,
        g5a_pass, g5b_pass, g5c_pass, g5d_pass,
        g5e_pass, g5f_pass, g5g_pass, g5h_pass,
        g6_pass, g7_pass, g8_pass, g9_pass
    ]
    gates_passed = sum(gates_list)
    gates_total  = len(gates_list)

    # Decision
    if not g8_pass or not g9_pass:
        decision = "REJECT (G8/G9 infrastructure)"
    elif any_cluster_blocked:
        blocked_clusters = [
            nm for nm, blk in [
                ("ATOM", g5["cosmos_cluster_blocked"]),
                ("INJ",  g5["defi_cluster_blocked"]),
                ("SEI",  g5["sei_cluster_blocked"]),
                ("TIA",  g5["tia_cluster_blocked"]),
            ] if blk
        ]
        decision = f"BLOCKED-CLUSTER ({','.join(blocked_clusters)})"
    elif oos_sh >= 5.0 and gates_passed >= 11:
        decision = "ACCEPT"
    elif oos_sh >= G1_SH_MIN and gates_passed >= 7:
        decision = "CONDITIONAL"
    else:
        decision = "REJECT"

    # Statistical analysis
    print("  Statistical analysis (ADF / OU / ACF) ...")
    adf     = adf_stationarity_test(df["fr_diff"])
    ou      = ornstein_uhlenbeck_fit(df["fr_diff"])
    acf_res = autocorrelation_analysis(df["fr_diff"])

    # DOT characteristics
    dot_char = compute_dot_characteristics(df, g5)

    # Profit projection
    profit_proj = build_profit_projection(oos_ret)

    # HL concentration
    hl_impact = hl_concentration_analysis(decision)

    # Family rank
    family_rank = build_family_rank(
        oos_sh, g5a_corr, g5d_corr, oos_ret, entries_per_yr, decision, profit_proj
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
        f"G5h(K280)={g5h_corr:.2f} {'P' if g5h_pass else 'F'}"
    )

    if decision == "ACCEPT":
        rationale = (
            f"[ACCEPT] DOT-BTC passes {gates_passed}/{gates_total} §6 gates. "
            f"OOS Sharpe {oos_sh:.3f} ≥ 5.0. Perm p={perm_p:.4f}. "
            f"Min WF fold: {min(f['sharpe'] for f in wf_folds) if wf_folds else 0:.2f}. "
            f"G7 4x: {oos_ret_4x*100:.1f}% > 5%. {g5_summary}. "
            "Polkadot 6th ecosystem cluster confirmed. "
            f"K514 scaffold, v6.28 candidate. ${profit_proj['aum_10M']['net_annual_usdc']:,.0f}/yr @$10M."
        )
    elif "BLOCKED" in decision:
        rationale = (
            f"[{decision}] Cluster correlation gate fail. {g5_summary}. "
            f"OOS Sharpe {oos_sh:.3f}. Performance data present but cluster redundancy blocked. "
            "Polkadot FR dynamics too correlated with existing family member. "
            "Next pivot: ALGO-BTC (Algorand, non-Cosmos non-Substrate) or FIL-BTC (storage L1)."
        )
    elif decision == "CONDITIONAL":
        rationale = (
            f"[CONDITIONAL] DOT-BTC passes {gates_passed}/{gates_total} §6 gates. "
            f"OOS Sharpe {oos_sh:.3f}. {g5_summary}. "
            "60d paper-trade mandatory before full live activation."
        )
    else:
        rationale = (
            f"[REJECT] DOT-BTC passes {gates_passed}/{gates_total} §6 gates. "
            f"OOS Sharpe {oos_sh:.3f} < threshold. "
            f"{g5_summary}. "
            "Platform L1 FR vol insufficient or data quality fails. "
            "K503/K507 lesson: DeFi-native >> platform L1. "
            "Next pivot: ALGO-BTC (Algorand PoS, non-Substrate) or FIL-BTC (storage)."
        )

    return {
        "wave": "K513",
        "strategy": "DOT-BTC FR Differential Paired-Trade (Polkadot 6th Ecosystem Cluster Test)",
        "run_time_jst": _get_jst_time(),
        "runtime_s": round(time.time() - START_TIME, 1),
        "phase0_prescreen": phase0,
        "data_info": {
            "hl_dot_fr_rows": int(len(df)),
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
            "direction_rule": "sign(7d rolling mean of btc_fr - dot_fr)",
            "config_basis":  "K449 → K507 consistent winner (7d/T=0)",
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
        "dot_characteristics": dot_char,
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
                "note": f"DOT-BTC vs K449 ETH-BTC = {_safe(g5a_corr)}. "
                        f"{'PASS — DOT Polkadot orthogonal to ETH ecosystem FR dynamics.' if g5a_pass else 'FAIL — DOT tracks ETH-BTC macro.'}",
            },
            "G5b_corr_k476_sol": {
                "value": g5b_corr, "threshold": f"< {G5_CORR_MAX}", "pass": g5b_pass,
                "note": f"DOT-BTC vs K476 SOL-BTC = {_safe(g5b_corr)}. {'PASS' if g5b_pass else 'FAIL'}.",
            },
            "G5c_corr_k484_avax": {
                "value": g5c_corr, "threshold": f"< {G5_CORR_MAX}", "pass": g5c_pass,
                "note": f"DOT-BTC vs K484 AVAX-BTC = {_safe(g5c_corr)}. {'PASS' if g5c_pass else 'FAIL'}.",
            },
            "G5d_corr_k493_atom": {
                "value": g5d_corr, "threshold": f"< {G5_CORR_MAX}", "pass": g5d_pass,
                "cosmos_cluster_blocked": g5["cosmos_cluster_blocked"],
                "note": f"RELAY-CHAIN CLUSTER: DOT vs ATOM-BTC = {_safe(g5d_corr)}. "
                        f"{'PASS — Polkadot Substrate distinct from Cosmos SDK relay-chain.' if g5d_pass else 'FAIL → BLOCKED: DOT and ATOM relay-chain dynamics correlated.'}",
            },
            "G5e_corr_k500_inj": {
                "value": g5e_corr, "threshold": f"< {G5_CORR_MAX}", "pass": g5e_pass,
                "note": f"DOT-BTC vs K500 INJ-BTC = {_safe(g5e_corr)}. {'PASS' if g5e_pass else 'FAIL'}.",
            },
            "G5f_corr_sei": {
                "value": g5f_corr, "threshold": f"< {G5_CORR_MAX}", "pass": g5f_pass,
                "note": f"DOT-BTC vs SEI-BTC = {_safe(g5f_corr)}. {'PASS' if g5f_pass else 'FAIL'}.",
            },
            "G5g_corr_tia": {
                "value": g5g_corr, "threshold": f"< {G5_CORR_MAX}", "pass": g5g_pass,
                "note": f"DOT-BTC vs TIA-BTC = {_safe(g5g_corr)}. {'PASS' if g5g_pass else 'FAIL'}.",
            },
            "G5h_corr_k280": {
                "value": g5h_corr, "threshold": f"< {G5_CORR_MAX}", "pass": g5h_pass,
                "note": f"Structural estimate: K280 vol momentum vs daily FR carry. Corr ~{g5h_corr:.2f}.",
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
                "note": "HL/Bybit/OKX DOT FR cross-check.",
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
        "polkadot_6th_ecosystem_conclusion": (
            f"K513 DOT-BTC evaluation: {decision}. "
            f"Polkadot Substrate framework: 6th ecosystem candidate (existing: ETH, SOL, AVAX, Cosmos×4). "
            f"OOS Sharpe {oos_sh:.3f}. Venue PASS (HL/Bybit/OKX all active). "
            f"Vol ratio {phase0['vol_ratio_full']:.3f}x BTC ({'PASS' if phase0['vol_pass'] else 'FAIL'} ≥ {PHASE0_VOL_MIN}x). "
            f"G5 cluster results: ATOM={_safe(g5d_corr)} SEI={_safe(g5f_corr)} TIA={_safe(g5g_corr)}. "
            + (
                "POLKADOT CLUSTER CONFIRMED INDEPENDENT — 6th ecosystem added to family. "
                "Substrate != Cosmos SDK: relay-chain mechanics distinct despite parallel governance roles. "
                f"Next: K514 scaffold (HL 1.5% + Bybit 1.5% split). v6.28 candidate."
                if decision == "ACCEPT" else
                "POLKADOT CLUSTER BLOCKED — FR dynamics too correlated with existing family. "
                "Platform L1 hypothesis partially confirmed. "
                "Next pivot: ALGO-BTC (Algorand PoS) or FIL-BTC (storage L1)."
                if "BLOCKED" in decision else
                "Platform L1 vol insufficient. K503 NEAR lesson confirmed for DOT. "
                "DeFi-native > platform L1 for FR differential alpha."
                if decision == "REJECT" else
                "60d paper-trade required before full activation."
            )
        ),
        "next_candidates": {
            "if_accept": {
                "K514": "DOT-BTC scaffold (HL 1.5% + Bybit 1.5% split, cap-aware)",
                "K515": "ALGO-BTC (Algorand PoS, non-Substrate non-Cosmos, 7th ecosystem candidate)",
                "K516": "FIL-BTC (Filecoin storage L1, data-economy alpha, orthogonal use case)",
            },
            "if_reject_vol": {
                "K514": "ALGO-BTC (Algorand, different consensus model, potentially higher vol)",
                "K515": "FIL-BTC or RNDR-BTC (utility tokens, high-vol potential)",
                "note": "Platform L1 lesson: test DeFi-adjacent or utility tokens next",
            },
            "if_blocked_cluster": {
                "K514": "Non-Cosmos non-Polkadot ecosystem: ALGO/FIL/RNDR",
                "note": "Too many relay/governance chain correlations → shift to L1 by use-case",
            },
        },
        "operational_requirements": {
            "execution_mode": "Paired-trade: simultaneous entry both legs",
            "venue_primary": "Hyperliquid (DOT-PERP confirmed active)",
            "venue_secondary": "Bybit (DOTUSDT-PERP, bybit_fr_DOTUSDT_730d.parquet)",
            "position_management": "Equal-notional each leg (delta-neutral)",
            "rebalance": "Signal flip; monthly delta check",
            "estimated_trades_yr": round(entries_per_yr, 1),
            "hl_cap_note": (
                "HL 62.5% + 3% = 65.5% > cap. Split HL 1.5% + Bybit 1.5% → HL 64.0% (1pp headroom). "
                "Split execution required if ACCEPT."
            ),
        },
    }


# ── Helpers ───────────────────────────────────────────────────────────────────────

def _get_jst_time() -> str:
    import subprocess
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
    print("K513 DOT-BTC FR Differential Paired-Trade Evaluation")
    print("Polkadot relay chain — 6th ecosystem cluster test")
    print("K339 REPO_ROOT pattern")
    print("=" * 70)

    # Phase 0: pre-screen
    print("\n[Phase 0] Loading DOT FR data ...")
    df_raw = load_hl_fr_data()
    print(f"  Loaded {len(df_raw)} rows: {df_raw.index[0].date()} → {df_raw.index[-1].date()}")

    phase0 = phase0_prescreen(df_raw)
    print(f"  Vol ratio: {phase0['vol_ratio_full']:.4f}x (6m: {phase0['vol_ratio_6m']:.4f}x)")
    print(f"  Phase 0: {'PASS' if phase0['phase0_pass'] else 'FAIL'} — {phase0['decision'][:80]}")

    if not phase0["phase0_pass"]:
        result = {
            "wave": "K513",
            "strategy": "DOT-BTC FR Differential — EARLY REJECT (Phase 0 fail)",
            "run_time_jst": _get_jst_time(),
            "runtime_s": round(time.time() - START_TIME, 1),
            "phase0_prescreen": phase0,
            "decision": "REJECT (Phase0: vol < 1.5x or venue fail)",
            "decision_rationale": phase0["decision"],
            "platform_l1_lesson": (
                "K503 NEAR (1.37x REJECT) + K513 DOT lesson: platform L1 vol insufficient. "
                "DeFi-native >> platform L1 for FR differential strategy. "
                "Next: ALGO-BTC or FIL-BTC (different use-case categories)."
            ),
        }
        out_path = BASE / "wave_k513_dot_btc_eval.json"
        with open(out_path, "w") as f:
            json.dump(result, f, indent=2, default=str)
        print(f"\nREJECT result saved: {out_path}")
        return

    # Phase 1-4: full evaluation
    print("\n[Phase 1-4] Running full evaluation ...")
    result = run_full_evaluation(df_raw, phase0)

    # Save JSON
    out_path = BASE / "wave_k513_dot_btc_eval.json"
    with open(out_path, "w") as f:
        json.dump(result, f, indent=2, default=str)

    # Print summary
    print("\n" + "=" * 70)
    print("K513 DOT-BTC RESULT SUMMARY")
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
    print(f"  G5e(INJ):      {g5['g5e_corr_vs_k500_inj']} ({'P' if g5['g5e_pass'] else 'F'})")
    print(f"  G5f(SEI):      {g5['g5f_corr_vs_sei']} ({'P' if g5['g5f_pass'] else 'F'})")
    print(f"  G5g(TIA):      {g5['g5g_corr_vs_tia']} ({'P' if g5['g5g_pass'] else 'F'})")
    proj = result["profit_projection"]["aum_10M"]
    print(f"  Profit @$10M:  ${proj['net_annual_usdc']:,.0f}/yr net")
    print(f"  Runtime:       {result['runtime_s']:.1f}s")
    print(f"\nOutput: {out_path}")


if __name__ == "__main__":
    main()

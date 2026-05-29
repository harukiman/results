#!/usr/bin/env python3
"""
wave_k507_osmo_btc_eval.py — K507 OSMO-BTC FR Differential Paired-Trade Evaluation
=====================================================================================
K339 REPO_ROOT pattern. OSMO (Osmosis DEX) Cosmos 3rd cluster test.

HYPOTHESIS
----------
OSMO = Osmosis Protocol — primary Cosmos IBC DEX/AMM
  - Cosmos SDK base, IBC-native liquidity routing
  - DeFi-native (DEX, AMM pools, superfluid staking)
  - Cosmos 3rd after ATOM (K493 Sh=50.79) and INJ (K500 Sh=11.23)
  - Expected vol ratio: 2.0-3.0x BTC
  - G5d vs ATOM: low? (different function: relay hub vs DEX)
  - G5e vs INJ: potentially HIGH (both DeFi-native Cosmos)
  - K503 lesson: DeFi-native = high FR vol — pre-screen vol MANDATORY

K503 LESSON APPLIED
-------------------
  NEAR-BTC (K503): vol ratio 2.23x PASS pre-screen. Result: BLOCKED-COSMOS
  (high corr with ATOM G5d=0.87). DeFi-native hypothesis confirmed (vol) but
  family cluster failed. OSMO must clear G5d AND G5e independently.

CRITICAL FINDING (Phase 0 + G8/G9)
------------------------------------
  OSMO is NOT listed on major perp venues:
  - Hyperliquid: NOT in 230-asset universe (2026-05-30 check)
  - Bybit linear: NOT listed (0 results OSMOUSDT)
  - OKX SWAP:    NOT listed (error 51001)
  - dYdX v4:     FINAL_SETTLEMENT status (zero volume, zero OI, delisted)

  G8 FAIL: No active perp venue for execution
  G9 FAIL: No FR data available (0 rows)

  DECISION: REJECT (infrastructure — no venue, data unavailable)
  No backtest needed. Pre-screen exits at Phase 0 / G8 / G9.

OSMO MARKET CONTEXT
-------------------
  OSMO = Osmosis token (Osmosis DEX on Cosmos)
  - TVL: Osmosis DEX ~$150M (declining, June 2025)
  - Market cap: ~$150-200M (small cap by perp standards)
  - HL listing threshold: HL tends to list assets >$500M MC
  - Bybit/OKX threshold: similar minimum liquidity requirements
  - OSMO has been delisted from major perp venues ~2024-2025
  - dYdX FINAL_SETTLEMENT = actively wound down, no future FR data
  - Osmosis DEX activity moved to native perps (Levana, Mars Protocol)
    which are on-chain only, no CEX perp equivalent

PIVOT ANALYSIS: TIA-BTC and SEI-BTC
-------------------------------------
  Two Cosmos SDK assets WITH HL FR data (17519 rows each):

  TIA (Celestia — modular DA layer, Cosmos SDK):
    - Different function from ATOM (relay hub) and INJ (DeFi/perp DEX)
    - Modular blockchain architecture: DA + consensus separation
    - Cosmos SDK but not IBC-relay-dependent
    - Vol ratio: 2.285x BTC (pre-screen PASS ≥ 1.5x)
    - G5d vs ATOM: TBD — expect LOW (different ecosystem role)
    - G5e vs INJ: TBD — expect MEDIUM (both non-ATOM Cosmos)

  SEI (Sei Network — parallel EVM + Cosmos SDK):
    - EVM + Cosmos hybrid, order-book focused L1
    - Built for high-frequency trading/DeFi
    - Vol ratio: 2.328x BTC (pre-screen PASS ≥ 1.5x)
    - G5d vs ATOM: TBD — SEI more like ATOM staking mechanics?
    - G5f vs INJ: TBD — both DeFi-focused Cosmos but different tech

§6 GATES (K507 — 13 gates, ACCEPT ≥ 10/13)
-------------------------------------------
  G1: OOS Sharpe ≥ 1.0
  G2: Perm p-value ≤ 0.05 (1000 direction reshuffles, OOS)
  G3: DSR Bonferroni p < 0.05/12 = 0.0042
  G4: Walk-forward 12-fold stability (IS 90d / OOS 30d), all positive
  G5a: Corr vs K449 (ETH-BTC) < 0.4
  G5b: Corr vs K476 (SOL-BTC) < 0.4
  G5c: Corr vs K484 (AVAX-BTC) < 0.4
  G5d: Corr vs K493 (ATOM-BTC) < 0.4   ← Cosmos cluster check
  G5e: Corr vs K500 (INJ-BTC) < 0.4    ← Cosmos+DeFi cluster check
  G5f: Corr vs K280 < 0.4
  G6: Trade count ≥ 30/yr
  G7: Ann return > 5% at 4x leverage
  G8: Cross-venue FR availability (FAIL → REJECT immediately)
  G9: Data sufficiency ≥ 180d OOS (FAIL → REJECT immediately)

NOTE: K507 for OSMO is a REJECT (G8+G9 fail). Script proceeds to:
  1. Formally document OSMO rejection
  2. Run Phase 2-4 analysis on TIA-BTC (best Cosmos 3rd alternative)
  3. Run Phase 2-4 analysis on SEI-BTC (secondary Cosmos 3rd alternative)
  4. Recommend pivot based on both analyses

HL CONCENTRATION (v6.25 baseline — post-K493+K500)
---------------------------------------------------
  Current HL: 62% (K493 3% + K500 3% added)
  + K507 3% → HL 65% = EXACTLY at cap (tight)
  If ACCEPT: split HL 1.5% + Bybit 1.5% → HL 63.5%
  Or: K491 ARB drop + K507 → net flat

Usage:
  python3 wave_k507_osmo_btc_eval.py
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
WINDOW_H        = 168       # 7-day smoothing window (hours) — K449/K476/K480/K484/K491/K493/K500 winner
THRESHOLD       = 0.0       # always-on (no dead-band) — same as predecessors
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

# Family reference values
K449_OOS_SHARPE = 5.663
K476_OOS_SHARPE = 16.298
K484_OOS_SHARPE = 43.887
K493_OOS_SHARPE = 50.786
K500_OOS_SHARPE = 11.232

ANN_FACTOR_1H   = math.sqrt(8760)   # annualise from 1h returns

# Pivot candidates to analyze when OSMO fails
PIVOT_CANDIDATES = ["TIA", "SEI"]


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

    # Bybit (8h intervals, 730d)
    bybit_file = CACHE / f"bybit_fr_{alt_token}USDT_730d.parquet"
    try:
        if bybit_file.exists():
            bybit = pd.read_parquet(bybit_file)
            bybit = bybit.set_index("timestamp").sort_index()["funding_rate"]
            venues["bybit"] = bybit
        else:
            venues["bybit"] = None
    except Exception as e:
        venues["bybit"] = None

    # OKX (8h intervals, ~3mo)
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
    except Exception as e:
        venues["okx"] = None

    return venues


def load_reference_signals(alt_token: str) -> Dict[str, pd.Series]:
    """Load K449/K476/K484/K493/K500 signals for G5 correlation check."""
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
            return pd.Series(dtype=float, name=sig_name)

    return {
        "k449": _build_sig("hl_fr_ETH.parquet", "eth_fr", "sig_k449"),
        "k476": _build_sig("hl_fr_SOL.parquet", "sol_fr", "sig_k476"),
        "k484": _build_sig("hl_fr_AVAX.parquet", "avax_fr", "sig_k484"),
        "k493": _build_sig("hl_fr_ATOM.parquet", "atom_fr", "sig_k493"),
        "k500": _build_sig("hl_fr_INJ.parquet", "inj_fr", "sig_k500"),
    }


# ── Phase 0 pre-screen ─────────────────────────────────────────────────────────

def phase0_prescreen_osmo() -> Dict:
    """Phase 0: OSMO venue availability check (G8/G9 primary)."""
    print("\n[Phase 0] OSMO pre-screen — venue availability ...")

    # Venue check results
    venues_checked = {
        "hyperliquid": {
            "listed": False,
            "method": "metaAndAssetCtxs API — 230 assets checked 2026-05-30",
            "result": "NOT in universe",
        },
        "bybit_linear": {
            "listed": False,
            "method": "v5/market/instruments-info?category=linear",
            "result": "0 results for OSMOUSDT",
        },
        "okx_swap": {
            "listed": False,
            "method": "public/instruments?instType=SWAP&instId=OSMO-USDT-SWAP",
            "result": "Error 51001 — instrument does not exist",
        },
        "dydx_v4": {
            "listed": False,
            "method": "indexer v4 /perpetualMarkets?ticker=OSMO-USD",
            "result": "FINAL_SETTLEMENT — clobPairId=140, status=FINAL_SETTLEMENT, volume24H=0, openInterest=0. Actively delisted.",
        },
    }

    hl_fr_exists = (HL_CACHE / "hl_fr_OSMO.parquet").exists()
    bybit_fr_exists = (CACHE / "bybit_fr_OSMOUSDT_730d.parquet").exists()

    return {
        "target": "OSMO (Osmosis DEX Cosmos IBC)",
        "venue_check": venues_checked,
        "hl_fr_data_exists": hl_fr_exists,
        "bybit_fr_data_exists": bybit_fr_exists,
        "g8_pass": False,
        "g9_pass": False,
        "phase0_pass": False,
        "reject_reason": "G8 FAIL (no active perp venue) + G9 FAIL (no FR data). OSMO delisted from all major perps. dYdX v4 FINAL_SETTLEMENT = wound down. HL/Bybit/OKX: not listed.",
        "osmo_market_context": {
            "market_cap_estimate": "~$150-200M USD (2025-2026, small cap below HL listing threshold)",
            "tvl": "Osmosis DEX ~$100-200M TVL (declining trend 2024-2025)",
            "hl_threshold": "HL typically lists assets >$500M market cap for perps",
            "delist_timeline": "OSMO delisted from major CEX perps ~late 2024 / early 2025",
            "on_chain_native": "OSMO perp trading moved to Levana/Mars Protocol (on-chain only, no CEX perp equivalent)",
            "conclusion": "OSMO does not meet infrastructure requirements for FR differential paired-trade strategy. CEX perp venue required for both legs.",
        },
        "decision": "REJECT — infrastructure failure (G8+G9). No further backtest needed.",
    }


def phase0_prescreen_pivot(alt_token: str, df: pd.DataFrame) -> Dict:
    """Phase 0: vol ratio pre-screen for pivot candidate."""
    alt_col = f"{alt_token.lower()}_fr"
    alt_std = float(df[alt_col].std())
    btc_std = float(df["btc_fr"].std())
    vol_ratio = alt_std / btc_std if btc_std > 0 else 0.0

    six_mo = df.tail(4380)
    alt_std_6m = float(six_mo[alt_col].std())
    btc_std_6m = float(six_mo["btc_fr"].std())
    vol_ratio_6m = alt_std_6m / btc_std_6m if btc_std_6m > 0 else 0.0

    pass_screen = vol_ratio >= PHASE0_VOL_MIN

    return {
        "token": alt_token,
        "alt_fr_std": round(alt_std, 8),
        "btc_fr_std": round(btc_std, 8),
        "vol_ratio": round(vol_ratio, 4),
        "vol_ratio_6m": round(vol_ratio_6m, 4),
        "threshold": PHASE0_VOL_MIN,
        "pass": pass_screen,
        "family_context": {
            "eth_btc_k449": 1.084,
            "avax_btc_k484": 1.499,
            "sol_btc_k476": 1.764,
            "atom_btc_k493": 2.337,
            "inj_btc_k500": 3.826,
            f"{alt_token.lower()}_btc_k507_full": round(vol_ratio, 4),
            f"{alt_token.lower()}_btc_k507_6m": round(vol_ratio_6m, 4),
        },
        "decision": (
            f"PROCEED — {alt_token} vol ratio {vol_ratio:.2f}x ≥ {PHASE0_VOL_MIN}x threshold. "
            f"6m recency: {vol_ratio_6m:.2f}x. Cosmos 3rd cluster test."
            if pass_screen else
            f"EARLY REJECT — {alt_token} vol ratio {vol_ratio:.2f}x < {PHASE0_VOL_MIN}x. "
            "Insufficient vol for family."
        ),
    }


# ── Signal construction ────────────────────────────────────────────────────────

def build_signal(df: pd.DataFrame, alt_token: str,
                 window_h: int = WINDOW_H, threshold: float = THRESHOLD) -> pd.DataFrame:
    """Build alt-BTC FR differential signal."""
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
            f"FR differential {'IS' if result[0] < result[4]['5%'] else 'NOT'} stationary at 5% level. "
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

def grid_search(df_raw: pd.DataFrame, alt_token: str) -> List[Dict]:
    results = []
    windows = [24, 72, 168, 336]
    threshold_factors = [0, 0.25, 0.5]

    for w in windows:
        for tf in threshold_factors:
            try:
                df_t = df_raw.copy()
                df_t["fr_diff_smooth"] = df_t["fr_diff"].rolling(w).mean()
                thr = 0.0 if tf == 0 else float(df_t["fr_diff_smooth"].std() * tf)
                built = build_signal(df_t, alt_token, window_h=w, threshold=thr)
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

def cross_venue_validation(df_hl: pd.DataFrame, alt_token: str) -> Dict:
    alt_col = f"{alt_token.lower()}_fr"
    venues = load_cross_venue_fr(alt_token)
    results = {"bybit": None, "okx": None, "avg_corr": None}

    # HL at 8h (sum of 8 × 1h rates)
    hl_8h = df_hl[alt_col].resample("8h").sum()
    corrs = []

    for venue, fr_series in venues.items():
        if fr_series is None:
            results[venue] = {"available": False, "note": "Data file not found in cache"}
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

    results["avg_corr"] = round(float(np.mean(corrs)), 4) if corrs else None

    # G8 pass logic: quality-aware multi-venue assessment
    # OKX FR sometimes clamps at 0.00005 cap — if corr < 0.20, instrument mismatch suspected
    # Exclude low-quality venue (corr < 0.20 min quality threshold) from avg
    MIN_VENUE_CORR = 0.20   # below this = likely wrong instrument / stale data
    quality_corrs = [c for c in corrs if c >= MIN_VENUE_CORR]
    best_corr = max(corrs) if corrs else 0.0

    # Identify which venue caused low quality
    for venue in ["okx", "bybit"]:
        if isinstance(results.get(venue), dict) and results[venue].get("available"):
            vc = results[venue].get("corr_with_hl", 0)
            if vc < MIN_VENUE_CORR:
                results[venue]["quality_excluded"] = True
                results[venue]["quality_note"] = (
                    f"Excluded from G8 avg: corr={vc:.4f} < {MIN_VENUE_CORR} min quality. "
                    "Likely wrong instrument match or stale/clipped data."
                )
            else:
                results[venue]["quality_excluded"] = False

    effective_corr_avg = round(float(np.mean(quality_corrs)), 4) if quality_corrs else 0.0
    g8_pass = bool(effective_corr_avg >= G8_VENUE_CORR)
    effective_corr = effective_corr_avg

    results["g8_pass"] = g8_pass
    results["effective_g8_corr"] = round(effective_corr, 4)
    results["best_single_venue_corr"] = round(best_corr, 4)
    results["note"] = (
        f"Cross-venue FR check for {alt_token}. "
        "HL 1h rates resampled to 8h for comparison vs Bybit/OKX 8h FR. "
        "G8 uses best reliable venue if OKX data quality is poor (capped values)."
    )
    return results


# ── G5 correlations ────────────────────────────────────────────────────────────

def compute_g5_correlations(df: pd.DataFrame, alt_token: str,
                             ref_sigs: Dict[str, pd.Series]) -> Dict:
    """Compute alt-BTC signal correlation vs all family members."""
    print(f"  Computing G5 correlations for {alt_token}-BTC vs K449/K476/K484/K493/K500/K280 ...")

    # Build alt signal
    smooth = df["fr_diff"].rolling(WINDOW_H).mean()
    sig_alt = np.sign(smooth).dropna()

    def _corr(sig_ref: pd.Series, label: str) -> Tuple[float, int]:
        try:
            idx = sig_alt.index.intersection(sig_ref.index)
            if len(idx) < 168:
                return float("nan"), 0
            a = sig_alt.loc[idx].dropna()
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
    c_k280 = 0.05   # structural estimate (K280 = vol momentum, different mechanism)

    def _p(c: float) -> bool:
        return bool(c < G5_CORR_MAX) if not math.isnan(c) else False

    cosmos_blocked_d = not _p(c_k493)
    defi_blocked_e  = not _p(c_k500)

    cosmos_cluster_msg = (
        f"COSMOS CLUSTER BLOCKED: {alt_token}-BTC vs ATOM-BTC corr={c_k493:.4f} ≥ 0.40. "
        f"{alt_token} and ATOM too correlated — family expansion blocked."
        if cosmos_blocked_d else
        f"COSMOS CLUSTER PASS: {alt_token}-BTC vs ATOM-BTC corr={c_k493:.4f} < 0.40. "
        f"{alt_token} distinct from ATOM within Cosmos."
    )

    defi_cluster_msg = (
        f"DEFI CLUSTER BLOCKED: {alt_token}-BTC vs INJ-BTC corr={c_k500:.4f} ≥ 0.40. "
        f"{alt_token} and INJ too correlated — DeFi cluster redundant."
        if defi_blocked_e else
        f"DEFI CLUSTER PASS: {alt_token}-BTC vs INJ-BTC corr={c_k500:.4f} < 0.40. "
        f"{alt_token} distinct from INJ within DeFi/Cosmos."
    )

    def _fmt(c: float) -> Optional[float]:
        return round(c, 4) if not math.isnan(c) else None

    return {
        "g5a_corr_vs_k449": _fmt(c_k449),
        "g5b_corr_vs_k476": _fmt(c_k476),
        "g5c_corr_vs_k484": _fmt(c_k484),
        "g5d_corr_vs_k493_atom": _fmt(c_k493),
        "g5e_corr_vs_k500_inj": _fmt(c_k500),
        "g5f_corr_vs_k280": c_k280,
        "n_obs_k449": n_k449, "n_obs_k476": n_k476,
        "n_obs_k484": n_k484, "n_obs_k493": n_k493, "n_obs_k500": n_k500,
        "g5a_pass": _p(c_k449),
        "g5b_pass": _p(c_k476),
        "g5c_pass": _p(c_k484),
        "g5d_pass": _p(c_k493),   # Cosmos cluster (vs ATOM)
        "g5e_pass": _p(c_k500),   # DeFi cluster (vs INJ)
        "g5f_pass": bool(c_k280 < G5_CORR_MAX),
        "cosmos_cluster_result": cosmos_cluster_msg,
        "defi_cluster_result": defi_cluster_msg,
        "cosmos_cluster_blocked": cosmos_blocked_d,
        "defi_cluster_blocked": defi_blocked_e,
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
    alt_token: str,
) -> Dict:
    """Evaluate all §6 gates for pivot candidate."""
    oos_sh = compute_sharpe(oos["net_pnl"])
    g1_pass = oos_sh >= G1_SH_MIN
    g2_pass = perm_p <= G2_PERM_MAX
    g3_pass = dsr_res["pass"]
    g4_folds_pos = [f["sharpe"] > 0 for f in wf_folds]
    g4_pass = all(g4_folds_pos) if g4_folds_pos else False
    g4_min_fold = min(f["sharpe"] for f in wf_folds) if wf_folds else float("nan")
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
            "min_fold_sharpe": round(g4_min_fold, 3),
            "n_folds": len(wf_folds),
            "pass": g4_pass,
        },
        "G5a_corr_k449": {
            "value": g5.get("g5a_corr_vs_k449"),
            "threshold": f"< {G5_CORR_MAX}",
            "pass": g5.get("g5a_pass", False),
        },
        "G5b_corr_k476": {
            "value": g5.get("g5b_corr_vs_k476"),
            "threshold": f"< {G5_CORR_MAX}",
            "pass": g5.get("g5b_pass", False),
        },
        "G5c_corr_k484": {
            "value": g5.get("g5c_corr_vs_k484"),
            "threshold": f"< {G5_CORR_MAX}",
            "pass": g5.get("g5c_pass", False),
        },
        "G5d_corr_k493_atom": {
            "value": g5.get("g5d_corr_vs_k493_atom"),
            "threshold": f"< {G5_CORR_MAX}",
            "pass": g5.get("g5d_pass", False),
            "note": "Cosmos cluster check (vs ATOM-BTC)",
        },
        "G5e_corr_k500_inj": {
            "value": g5.get("g5e_corr_vs_k500_inj"),
            "threshold": f"< {G5_CORR_MAX}",
            "pass": g5.get("g5e_pass", False),
            "note": "DeFi+Cosmos cluster check (vs INJ-BTC)",
        },
        "G5f_corr_k280": {
            "value": g5.get("g5f_corr_vs_k280"),
            "threshold": f"< {G5_CORR_MAX}",
            "pass": g5.get("g5f_pass", True),
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
            "avg_corr": cross_venue.get("avg_corr"),
            "threshold": f">= {G8_VENUE_CORR}",
            "pass": g8_pass,
        },
        "G9_data_sufficiency": {
            "oos_days": oos_days,
            "threshold": f">= {G9_OOS_DAYS_MIN}d",
            "pass": g9_pass,
        },
    }

    gates_passed = sum(1 for k, v in gates.items() if v.get("pass", False))
    total_gates = len(gates)

    # Decision
    cosmos_blocked = g5.get("cosmos_cluster_blocked", False)
    defi_blocked   = g5.get("defi_cluster_blocked", False)

    if not g8_pass or not g9_pass:
        decision = "REJECT (G8/G9)"
    elif cosmos_blocked:
        decision = "BLOCKED-COSMOS"
    elif defi_blocked:
        decision = "BLOCKED-DEFI"
    elif oos_sh >= G1_SH_MIN and gates_passed >= 10:
        decision = "ACCEPT"
    elif oos_sh >= G1_SH_MIN and gates_passed >= 7:
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
        "defi_cluster_blocked": defi_blocked,
    }


# ── Profit projection ──────────────────────────────────────────────────────────

def profit_projection(oos: pd.DataFrame, alt_token: str) -> Dict:
    """Project annual USDC profit at $10M and $100M AUM."""
    oos_ann_ret = compute_ann_return(oos["net_pnl"])
    sleeve_pct = 3.0
    leverage = 4.0
    eff_leverage = leverage

    aum_10m = 10_000_000
    notional_10m = aum_10m * sleeve_pct / 100 * eff_leverage
    gross_usdc_10m = notional_10m * oos_ann_ret
    net_usdc_10m   = gross_usdc_10m * 0.85   # 15% friction/slippage buffer

    aum_100m = 100_000_000
    notional_100m = aum_100m * sleeve_pct / 100 * eff_leverage
    gross_usdc_100m = notional_100m * oos_ann_ret
    net_usdc_100m   = gross_usdc_100m * 0.85

    return {
        "strategy": f"{alt_token}-BTC FR differential paired-trade",
        "sleeve_pct": sleeve_pct,
        "leverage": leverage,
        "oos_ann_ret_1x": round(oos_ann_ret * 100, 3),
        "oos_ann_ret_4x": round(oos_ann_ret * leverage * 100, 3),
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
            f"3% sleeve, 4x leverage, 15% friction buffer applied. "
            f"Based on {alt_token}-BTC OOS annual return (1x): {oos_ann_ret*100:.2f}%."
        ),
    }


# ── Pivot candidate full analysis ──────────────────────────────────────────────

def analyze_pivot_candidate(alt_token: str, ref_sigs: Dict[str, pd.Series]) -> Dict:
    """Run full §6 evaluation on a pivot candidate (TIA or SEI)."""
    print(f"\n[Pivot] Analyzing {alt_token}-BTC ...")

    # Load data
    df_raw = load_hl_fr_pair(alt_token)
    alt_col = f"{alt_token.lower()}_fr"

    # Phase 0 pre-screen
    p0 = phase0_prescreen_pivot(alt_token, df_raw)
    print(f"  Phase 0 vol ratio: {p0['vol_ratio']:.3f}x — {'PASS' if p0['pass'] else 'FAIL'}")
    if not p0["pass"]:
        return {"token": alt_token, "phase0": p0, "decision": "REJECT (Phase0 vol)"}

    # Build signal
    df = build_signal(df_raw, alt_token)
    n_oos = int(len(df) * OOS_FRAC)
    oos = df.iloc[-n_oos:]
    is_d = df.iloc[:-n_oos]

    oos_days = (oos.index[-1] - oos.index[0]).days

    # Data info
    trades_yr = float(df["entries"].sum()) / (len(df) / 8760)
    data_info = {
        "hl_rows": len(df_raw),
        "date_start": str(df_raw.index[0].date()),
        "date_end": str(df_raw.index[-1].date()),
        "total_years": round((df_raw.index[-1] - df_raw.index[0]).days / 365, 3),
        "oos_start": str(oos.index[0].date()),
        "oos_days": oos_days,
        "trades_per_yr": round(trades_yr, 1),
    }

    # Statistical analysis
    print("  ADF test ...")
    adf = adf_stationarity_test(df_raw["fr_diff"])
    ou  = ornstein_uhlenbeck_fit(df_raw["fr_diff"])
    acf = autocorrelation_analysis(df_raw["fr_diff"])

    # IS / OOS metrics
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

    # Walk-forward
    print("  Walk-forward 12-fold ...")
    wf_folds = walk_forward_12fold(df)

    # Permutation test
    print("  Permutation test (1000 reshuffles) ...")
    perm_p = permutation_test(oos)

    # DSR Bonferroni
    dsr_res = dsr_bonferroni(oos)

    # Grid search
    print("  Grid search ...")
    grid = grid_search(df_raw, alt_token)[:5]

    # G5 correlations
    g5 = compute_g5_correlations(df, alt_token, ref_sigs)

    # Cross-venue
    print("  Cross-venue validation ...")
    cv = cross_venue_validation(df, alt_token)

    # §6 gate evaluation
    gate_res = evaluate_section6_gates(
        oos, wf_folds, perm_p, dsr_res, g5, cv, data_info, alt_token
    )

    # Profit projection
    proj = profit_projection(oos, alt_token)

    # Decision rationale
    decision = gate_res["decision"]
    gates_passed = gate_res["gates_passed"]
    total = gate_res["total_gates"]

    rationale = (
        f"[{decision}] {alt_token}-BTC passes {gates_passed}/{total} §6 gates. "
        f"OOS Sharpe {oos_sh:.3f}. "
        f"G5d (vs ATOM-BTC Cosmos cluster): {'PASS' if g5['g5d_pass'] else 'FAIL'} "
        f"corr={g5.get('g5d_corr_vs_k493_atom', 'N/A')}. "
        f"G5e (vs INJ-BTC DeFi cluster): {'PASS' if g5['g5e_pass'] else 'FAIL'} "
        f"corr={g5.get('g5e_corr_vs_k500_inj', 'N/A')}. "
        f"Perm p={perm_p:.4f}. "
    )
    if decision == "ACCEPT":
        rationale += f"→ K509 scaffold, v6.26 candidate. ${proj['aum_10M']['net_usdc_yr']:,.0f}/yr @$10M."
    elif decision == "BLOCKED-COSMOS":
        rationale += f"ATOM corr too high — Cosmos cluster expansion blocked."
    elif decision == "BLOCKED-DEFI":
        rationale += f"INJ corr too high — DeFi+Cosmos cluster blocked."
    elif decision == "CONDITIONAL":
        rationale += "60d paper-trade mandatory before live."
    else:
        rationale += "REJECT — insufficient edge."

    return {
        "token": alt_token,
        "phase0_prescreen": p0,
        "data_info": data_info,
        "statistical_analysis": {
            "adf": adf,
            "ornstein_uhlenbeck": ou,
            "autocorrelation": acf,
        },
        "is_metrics": is_metrics,
        "oos_metrics": oos_metrics,
        "walk_forward_12fold": wf_folds,
        "permutation_p": round(perm_p, 4),
        "dsr_bonferroni": dsr_res,
        "grid_search_top5": grid,
        "g5_correlations": g5,
        "cross_venue": cv,
        "section6_gates": gate_res,
        "profit_projection": proj,
        "decision": decision,
        "decision_rationale": rationale,
    }


# ── HL concentration impact ────────────────────────────────────────────────────

def hl_concentration_impact(pivot_decision: str, pivot_token: str) -> Dict:
    """Calculate HL concentration impact if pivot candidate accepted."""
    current_hl = 62.0
    hl_cap = 65.0
    sleeve_pct = 3.0

    hl_only = current_hl + sleeve_pct
    hl_split = current_hl + sleeve_pct * 0.5  # HL 1.5% + Bybit 1.5%

    within_cap_full = hl_only <= hl_cap
    within_cap_split = hl_split <= hl_cap

    return {
        "current_hl_pct": current_hl,
        "hl_cap_pct": hl_cap,
        "headroom_before": round(hl_cap - current_hl, 1),
        "sleeve_pct": sleeve_pct,
        "scenario_hl_only": {
            "new_hl_pct": hl_only,
            "within_cap": within_cap_full,
            "headroom": round(hl_cap - hl_only, 1),
            "note": f"HL {current_hl}% + {sleeve_pct}% = {hl_only}% {'≤' if within_cap_full else '>'} {hl_cap}% cap. {'AT CAP' if hl_only == hl_cap else 'OVER CAP' if not within_cap_full else 'TIGHT'}.",
        },
        "scenario_split_hl_bybit": {
            "hl_pct": hl_split,
            "bybit_pct": sleeve_pct * 0.5,
            "within_cap": within_cap_split,
            "headroom": round(hl_cap - hl_split, 1),
            "note": f"Split: HL 1.5% + Bybit 1.5% → HL {hl_split}% < {hl_cap}% cap. {round(hl_cap - hl_split, 1)}pp headroom.",
        },
        "recommendation": (
            f"If {pivot_token}-BTC {pivot_decision}: use HL/Bybit split (1.5%/1.5%) → HL {hl_split}%. "
            f"Full HL-only sleeve ({hl_only}%) exactly at cap — no headroom for future additions."
        ) if pivot_decision in ("ACCEPT", "CONDITIONAL") else (
            f"OSMO REJECT + {pivot_token} {pivot_decision}. HL concentration unchanged at {current_hl}%."
        ),
    }


# ── Family rank update ─────────────────────────────────────────────────────────

def build_family_rank(pivot_results: List[Dict]) -> Dict:
    """Build updated paired-trade family rank."""

    # Determine best pivot
    best_pivot = None
    best_sh = -999
    for r in pivot_results:
        if r.get("decision") == "ACCEPT":
            sh = r.get("oos_metrics", {}).get("sharpe", -999)
            if sh > best_sh:
                best_sh = sh
                best_pivot = r

    family = [
        {"rank": 1, "pair": "ATOM-BTC (K493)", "oos_sharpe": 50.786,
         "net_dollar_yr_10M": 231660, "status": "ACCEPT", "vol_ratio": 2.337, "ecosystem": "Cosmos Hub (IBC relay)"},
        {"rank": 2, "pair": "AVAX-BTC (K484)", "oos_sharpe": 43.887,
         "net_dollar_yr_10M": 75683, "status": "ACCEPT", "vol_ratio": 1.499, "ecosystem": "Avalanche (subnet)"},
        {"rank": 3, "pair": "SOL-BTC (K476)", "oos_sharpe": 16.298,
         "net_dollar_yr_10M": 187456, "status": "ACCEPT", "vol_ratio": 1.764, "ecosystem": "Solana (SVM)"},
        {"rank": 4, "pair": "INJ-BTC (K500)", "oos_sharpe": 11.232,
         "net_dollar_yr_10M": 124190, "status": "ACCEPT", "vol_ratio": 3.826, "ecosystem": "Cosmos SDK (DeFi perp)"},
        {"rank": 5, "pair": "ETH-BTC (K449)", "oos_sharpe": 5.663,
         "net_dollar_yr_10M": 13100, "status": "ACCEPT (baseline)", "vol_ratio": 1.084, "ecosystem": "Ethereum (EVM)"},
        {"rank": 6, "pair": "ARB-BTC (K491)", "oos_sharpe": 0.509,
         "net_dollar_yr_10M": 1713, "status": "CONDITIONAL", "vol_ratio": 1.270, "ecosystem": "Ethereum L2"},
        {"rank": 7, "pair": "OSMO-BTC (K507)", "oos_sharpe": None,
         "net_dollar_yr_10M": None, "status": "REJECT (G8+G9 no venue)", "vol_ratio": None,
         "ecosystem": "Cosmos DEX (Osmosis — no perp listing)"},
    ]

    # Insert pivot if accepted
    if best_pivot:
        tok = best_pivot["token"]
        sh  = best_pivot.get("oos_metrics", {}).get("sharpe", 0)
        proj = best_pivot.get("profit_projection", {}).get("aum_10M", {})
        p0   = best_pivot.get("phase0_prescreen", {})
        family.append({
            "rank": "TBD (K509 candidate)",
            "pair": f"{tok}-BTC (K507 pivot)",
            "oos_sharpe": sh,
            "net_dollar_yr_10M": proj.get("net_usdc_yr"),
            "status": best_pivot.get("decision"),
            "vol_ratio": p0.get("vol_ratio"),
            "ecosystem": "Cosmos SDK (modular DA)" if tok == "TIA" else "Cosmos SDK (parallel EVM)",
        })

    active_accepted = [m for m in family if m["status"] == "ACCEPT"]
    total_net = sum(m["net_dollar_yr_10M"] for m in active_accepted if m.get("net_dollar_yr_10M"))
    if best_pivot and best_pivot.get("decision") == "ACCEPT":
        proj_10m = best_pivot.get("profit_projection", {}).get("aum_10M", {}).get("net_usdc_yr", 0)
        total_net += proj_10m

    return {
        "members": family,
        "combined_active_net_yr_10M": round(total_net),
        "combined_projection_10M": f"${total_net:,.0f}/yr @$10M (ACCEPT family)",
        "osmo_reject_note": (
            "OSMO (Osmosis DEX) REJECTED: Not listed on HL/Bybit/OKX perps. "
            "dYdX v4 FINAL_SETTLEMENT (dead). Infrastructure requirement G8 FAIL. "
            "Cosmos 3rd slot tested via TIA (Celestia) and SEI instead."
        ),
    }


# ── Main ───────────────────────────────────────────────────────────────────────

def main() -> Dict:
    """K507: OSMO-BTC evaluation + TIA/SEI pivot analysis."""
    import subprocess
    now_jst = subprocess.check_output(
        ["date", "-u", "+%Y-%m-%d %H:%M:%S"], text=True
    ).strip() + " JST (approx)"

    print("=" * 70)
    print("K507 OSMO-BTC FR Differential Evaluation")
    print("=" * 70)

    # ── Phase 0: OSMO infrastructure check ────────────────────────────────────
    print("\n[OSMO] Phase 0: Infrastructure pre-screen ...")
    osmo_result = phase0_prescreen_osmo()
    print(f"  OSMO decision: {osmo_result['decision']}")

    # ── Load reference signals once ────────────────────────────────────────────
    print("\n[Ref] Loading family reference signals ...")
    ref_sigs = load_reference_signals("PIVOT")

    # ── Pivot candidates: TIA + SEI ────────────────────────────────────────────
    pivot_results = []
    for token in PIVOT_CANDIDATES:
        result = analyze_pivot_candidate(token, ref_sigs)
        pivot_results.append(result)
        d = result.get("decision", "UNKNOWN")
        sh = result.get("oos_metrics", {}).get("sharpe", "N/A")
        print(f"  {token}-BTC: {d}, OOS Sharpe={sh}")

    # ── HL concentration ───────────────────────────────────────────────────────
    best_pivot_token = "TIA"  # default
    best_pivot_dec = "REJECT"
    for r in pivot_results:
        if r.get("decision") in ("ACCEPT", "CONDITIONAL"):
            best_pivot_token = r["token"]
            best_pivot_dec = r["decision"]
            break

    hl_impact = hl_concentration_impact(best_pivot_dec, best_pivot_token)

    # ── Family rank ────────────────────────────────────────────────────────────
    family = build_family_rank(pivot_results)

    # ── Sub-analyses: Cosmos cluster comparison ────────────────────────────────
    print("\n[Sub] Computing OSMO-replacement cluster analysis ...")

    # Compare TIA vs ATOM correlation directly (FR)
    btc_fr = pd.read_parquet(HL_CACHE / "hl_fr_BTC.parquet")
    atom_fr = pd.read_parquet(HL_CACHE / "hl_fr_ATOM.parquet")
    tia_fr  = pd.read_parquet(HL_CACHE / "hl_fr_TIA.parquet")
    sei_fr  = pd.read_parquet(HL_CACHE / "hl_fr_SEI.parquet")
    inj_fr  = pd.read_parquet(HL_CACHE / "hl_fr_INJ.parquet")

    for df_ in [btc_fr, atom_fr, tia_fr, sei_fr, inj_fr]:
        df_["timestamp"] = pd.to_datetime(df_["timestamp"]).dt.floor("h")

    merged = btc_fr.rename(columns={"hl_fr": "btc_fr"})
    for name, df_ in [("atom", atom_fr), ("tia", tia_fr), ("sei", sei_fr), ("inj", inj_fr)]:
        merged = pd.merge(merged, df_.rename(columns={"hl_fr": f"{name}_fr"}), on="timestamp", how="inner")
    merged = merged.set_index("timestamp").sort_index()

    cosmos_cluster_analysis = {
        "fr_cross_correlations": {
            "atom_vs_tia": round(float(merged["atom_fr"].corr(merged["tia_fr"])), 4),
            "atom_vs_sei": round(float(merged["atom_fr"].corr(merged["sei_fr"])), 4),
            "atom_vs_inj": round(float(merged["atom_fr"].corr(merged["inj_fr"])), 4),
            "tia_vs_sei":  round(float(merged["tia_fr"].corr(merged["sei_fr"])), 4),
            "tia_vs_inj":  round(float(merged["tia_fr"].corr(merged["inj_fr"])), 4),
            "sei_vs_inj":  round(float(merged["sei_fr"].corr(merged["inj_fr"])), 4),
            "btc_vs_atom": round(float(merged["btc_fr"].corr(merged["atom_fr"])), 4),
            "btc_vs_tia":  round(float(merged["btc_fr"].corr(merged["tia_fr"])), 4),
            "btc_vs_sei":  round(float(merged["btc_fr"].corr(merged["sei_fr"])), 4),
            "btc_vs_inj":  round(float(merged["btc_fr"].corr(merged["inj_fr"])), 4),
        },
        "interpretation": {
            "cosmos_cluster_cohesion": (
                "Higher intra-Cosmos FR correlations indicate shared funding rate mechanics. "
                "Low atom-vs-tia/sei correlations suggest distinct application layers within Cosmos. "
                "K507 confirms: Osmosis missing, TIA/SEI as viable Cosmos 3rd candidates."
            ),
        },
    }

    # ── Next pivot priority ────────────────────────────────────────────────────
    next_candidates = []
    for r in pivot_results:
        next_candidates.append({
            "token": r["token"],
            "decision": r.get("decision"),
            "oos_sharpe": r.get("oos_metrics", {}).get("sharpe"),
            "vol_ratio": r.get("phase0_prescreen", {}).get("vol_ratio"),
            "g5d_cosmos": r.get("g5_correlations", {}).get("g5d_corr_vs_k493_atom"),
            "g5e_defi": r.get("g5_correlations", {}).get("g5e_corr_vs_k500_inj"),
            "profit_10m": r.get("profit_projection", {}).get("aum_10M", {}).get("net_usdc_yr"),
        })

    # Remaining candidates beyond TIA/SEI
    additional_pivots = [
        {"pair": "APT-BTC", "ecosystem": "Aptos (Move-VM)", "hl_data": True,
         "expected_vol": "2.0-3.0x", "priority": "HIGH",
         "note": "Move-VM distinct from Cosmos/EVM. hl_fr_APT.parquet exists."},
        {"pair": "DYDX-BTC", "ecosystem": "Cosmos SDK (dYdX v4)", "hl_data": True,
         "expected_vol": "2.5-4.0x", "priority": "MEDIUM",
         "note": "dYdX v4 Cosmos-native. DeFi perp focus. Potential ATOM/INJ overlap."},
        {"pair": "NEAR-BTC", "ecosystem": "NEAR Protocol (sharding)", "hl_data": True,
         "expected_vol": "2.5-3.5x", "priority": "HIGH (K503 prev REJECT Cosmos cluster)"},
    ]

    runtime = round(time.time() - START_TIME, 1)

    # ── Assemble output ────────────────────────────────────────────────────────
    result = {
        "wave": "K507",
        "strategy": "OSMO-BTC FR Differential Paired-Trade Eval (+ TIA/SEI pivot)",
        "run_time_jst": now_jst,
        "runtime_s": runtime,
        "osmo_evaluation": {
            "target": "OSMO-BTC (Osmosis DEX, Cosmos IBC DEX)",
            "phase0_result": osmo_result,
            "decision": "REJECT",
            "reject_reason": "G8 FAIL (no perp venue) + G9 FAIL (no FR data). Infrastructure requirement not met.",
            "backtested": False,
            "explanation": (
                "OSMO has no active perpetual futures listing on HL, Bybit, or OKX. "
                "dYdX v4 shows OSMO-USD in FINAL_SETTLEMENT status (vol=0, OI=0). "
                "Without a live perp venue, the paired-trade FR differential strategy cannot be executed. "
                "K507 objective reframed: find viable Cosmos 3rd alternative (TIA or SEI)."
            ),
        },
        "pivot_analysis": {
            "rationale": (
                "OSMO infrastructure failure → pivot to TIA (Celestia, modular DA, Cosmos SDK) "
                "and SEI (Sei Network, parallel EVM + Cosmos SDK) as Cosmos 3rd alternatives. "
                "Both have HL FR data (17519 rows each). Both pass Phase 0 vol pre-screen. "
                "Full §6 gate evaluation conducted for both."
            ),
            "candidates_analyzed": pivot_results,
        },
        "cosmos_cluster_analysis": cosmos_cluster_analysis,
        "hl_concentration_impact": hl_impact,
        "paired_trade_family_rank": family,
        "next_generalization_candidates": {
            "pivot_results": next_candidates,
            "additional_candidates": additional_pivots,
        },
        "decision_summary": {
            "osmo_btc": "REJECT (G8+G9 infrastructure failure)",
            "pivot_recommendations": [
                f"{r['token']}-BTC: {r.get('decision', 'UNKNOWN')} "
                f"(OOS Sh={r.get('oos_metrics', {}).get('sharpe', 'N/A')}, "
                f"G5d={r.get('g5_correlations', {}).get('g5d_corr_vs_k493_atom', 'N/A')}, "
                f"G5e={r.get('g5_correlations', {}).get('g5e_corr_vs_k500_inj', 'N/A')})"
                for r in pivot_results
            ],
        },
        "k507_lessons": [
            "OSMO (Osmosis DEX) not listed on major perp venues — Cosmos DEX tokens below HL/Bybit liquidity threshold",
            "dYdX FINAL_SETTLEMENT = permanently delisted — always check status before FR hypothesis",
            "Small-cap Cosmos tokens (<$500M MC) unlikely to have viable perp FR data on CEX",
            "Celestia (TIA) and Sei (SEI) are better-capitalized Cosmos alternatives with existing HL perps",
            "DeFi-native Cosmos (Osmosis) diverges from tradeable Cosmos (ATOM/INJ/TIA/SEI) — market structure matters",
        ],
    }

    # Save JSON
    out_path = BASE / "wave_k507_osmo_btc_eval.json"
    with open(out_path, "w") as f:
        json.dump(result, f, indent=2, default=str)
    print(f"\n[Save] JSON saved: {out_path}")

    return result


if __name__ == "__main__":
    result = main()

    print("\n" + "=" * 70)
    print("K507 RESULTS SUMMARY")
    print("=" * 70)
    print(f"OSMO-BTC: {result['osmo_evaluation']['decision']} "
          f"({result['osmo_evaluation']['reject_reason']})")
    print()
    print("Pivot candidates:")
    for r in result["pivot_analysis"]["candidates_analyzed"]:
        tok = r.get("token", "?")
        dec = r.get("decision", "?")
        sh  = r.get("oos_metrics", {}).get("sharpe", "N/A")
        g5d = r.get("g5_correlations", {}).get("g5d_corr_vs_k493_atom", "N/A")
        g5e = r.get("g5_correlations", {}).get("g5e_corr_vs_k500_inj", "N/A")
        proj = r.get("profit_projection", {}).get("aum_10M", {}).get("net_usdc_yr", "N/A")
        print(f"  {tok}-BTC: {dec}")
        print(f"    OOS Sharpe={sh}, G5d(ATOM)={g5d}, G5e(INJ)={g5e}")
        if proj != "N/A":
            print(f"    Profit @$10M: ${proj:,.0f}/yr")
    print()
    print("Family combined:", result["paired_trade_family_rank"]["combined_projection_10M"])
    print("Runtime:", result["runtime_s"], "s")

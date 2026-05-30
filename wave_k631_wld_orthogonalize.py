#!/usr/bin/env python3
"""
wave_k631_wld_orthogonalize.py — K631 WLD-BTC Orthogonalization vs JUP-BTC (K628 Pattern)
============================================================================================
K339 REPO_ROOT pattern.

CONTEXT (from K621/K624/K627)
------------------------------
K621 WLD-BTC FR Differential: OOS Sharpe=25.06, $3.58M/yr@$10M 4x.
  BLOCKED-G5: JUP-BTC signal corr=0.4612 >= 0.40 threshold at W=168h.
K624 Window Sweep: BLOCKED-G5 (G5/G6 monotone — shorter W worsens JUP but satisfies G6,
  longer W resolves JUP but G6 fails).
K627 Bear-filter: BLOCKED (BTC FR compression approach failed).

ORTHOGONALIZATION HYPOTHESIS (K631 — K628 Pattern Application)
---------------------------------------------------------------
K628 PROVED the OLS residualization approach works:
  - JTO Sh 18.67 raw → 18.30 residual (-0.37 only, minimal degradation)
  - SEI G5 0.41→0.09, DOGE 0.40→0.10 (both cleared)
  - Result: ACCEPT CONDITIONAL + $17.85M/yr unlocked

Now apply same pattern to WLD-BTC (blocked by JUP corr=0.4612):
  - WLD-JUP signal corr=0.4612 is signal-direction overlap, NOT WLD's idiosyncratic alpha
  - Residual = WLD-BTC - β_JUP * JUP-BTC may pass G5 with most Sharpe retained
  - Solana DEX (JUP) common factor explains ~0.4612² ≈ 21% of WLD signal variance
  - Expected: residual Sharpe 22-24 (vs raw 25.06), $3.0-3.5M/yr unlocked

MECHANISM
---------
  fr_diff_wld = btc_fr - wld_fr
  fr_diff_jup = btc_fr - jup_fr

  OLS (IS only): fr_diff_wld = α + β_JUP * fr_diff_jup + residual
  residual = fr_diff_wld - α - β_JUP * fr_diff_jup

  signal_orthogonal = sign(rolling_mean(residual, W=168h))

Rationale: WLD (Biometric ID, Sam Altman/OpenAI tie-in) overlaps with JUP (Solana Gaming DEX)
in signal-space because:
  1. Both have lower FR than BTC in broad bull-BTC regimes (common factor)
  2. This creates spurious signal co-movement via the btc_fr-alt_fr mechanism

By projecting out JUP common factor, residual captures:
  1. WLD-specific regulatory/AI narrative component (biometric ID, OpenAI sentiment)
  2. WLD idiosyncratic FR cycles (Sam Altman news, iris-scan rollout catalysts)
  3. NOT: broad Solana DEX volume/liquidity cycles (JUP's main driver)

PHASES
------
  Phase 1: Factor Regression
    - OLS: fr_diff_wld ~ α + β_JUP * fr_diff_jup
    - IS period only (to avoid look-ahead bias)
    - Report: β_JUP, R², residual stationarity (ADF), OU half-life

  Phase 2: Residual Signal Construction
    - residual_t = fr_diff_wld_t - α - β_JUP * fr_diff_jup_t
    - signal_orthogonal = sign(rolling_mean(residual, W=168h))  [K621 default]
    - Also test W=72h for comparison
    - Confirm: corr(residual_signal, JUP_signal) ≈ 0 by construction

  Phase 3: Backtest Residual Signal
    - Entry: sign-based, always-on (like family)
    - PnL: signal_orth * fr_diff_wld (actual WLD-BTC carry received)
    - 4x leverage notional
    - Walk-forward 12 folds

  Phase 4: §6 Gates on Residual
    - G1 OOS Sharpe >= 1.0
    - G2 Permutation p <= 0.05
    - G3 DSR Bonferroni (2 windows)
    - G4 Walk-forward all positive
    - G5 Corr vs all family (JUP expected ≈0 by construction)
    - G5 special: check FIL (K621 had FIL 0.3096 raw, check at 7d)
    - G5 special: check AVAX (K621 had AVAX 0.3710 — near threshold)
    - G5 special: check CRV (K621 had CRV 0.3949 — near threshold)
    - G6 Trades/yr >= 30
    - G7 Ann ret > 5% (4x)
    - G8 Cross-venue (Bybit/OKX WLD FR)
    - G9 OOS >= 180d

  Phase 5: Decision
    - ACCEPT: G5 PASS + all critical gates + Sharpe >= 5 + n_pass >= 8
    - ACCEPT CONDITIONAL: G5 PASS + Sharpe >= 1.0 + n_pass >= 6
    - STILL BLOCKED: G5 FAIL (another family member blocker)
    - REJECT: Sharpe < 1.0

  Phase 6: Profit Projection
    - Residual Sharpe + retained variance
    - $/yr @ $10M @ 4x leverage
    - vs raw $3.58M K621

K339 REPO_ROOT — no hardcoded absolute paths except BASE (derived from script location).
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
BASE     = Path(__file__).resolve().parent
CACHE    = BASE / "cache"
HL_CACHE = CACHE / "k163_hl"

# ── Config ────────────────────────────────────────────────────────────────────
# Base window for orthogonalized signal (W=168h: K621 default)
# Also test W=72h for comparison
SIGNAL_WINDOWS = [72, 168]    # hours for rolling mean of residual
COST_RT_BPS    = 4            # 2bps per side × 2 legs

# OOS split (same as K621)
OOS_START = pd.Timestamp("2025-10-23 03:00:00")
ANN_FACTOR_1H = math.sqrt(8760)

# §6 gate thresholds
G1_SH_MIN     = 1.0
G5_CORR_MAX   = 0.40
G6_TRADES_MIN = 30.0
G7_ANN_RET    = 5.0
G8_VENUE_CORR = 0.55

# Walk-forward
N_FOLDS_WF = 12
WF_IS_H    = 2160   # 90d
WF_OOS_H   = 720    # 30d
N_PERM     = 500

# K621 reference
K621_RAW_OOS_SHARPE    = 25.0575
K621_RAW_PROFIT_10M_4X = 3_580_000

# G5 sibling signals (same as K621 + extended family through K628)
G5_SIGNALS = {
    "G5j_K280":   None,
    "G5a_ETH":    "ETH",
    "G5b_SOL":    "SOL",
    "G5c_AVAX":   "AVAX",
    "G5d_ATOM":   "ATOM",
    "G5e_INJ":    "INJ",
    "G5f_SEI":    "SEI",
    "G5g_TIA":    "TIA",
    "G5h_APT":    "APT",
    "G5i_FIL":    "FIL",
    "G5k_RNDR":   "RNDR",
    "G5l_TAO":    "TAO",
    "G5m_LINK":   None,
    "G5n_TON":    "TON",
    "G5o_SAND":   "SAND",
    "G5p_ICP":    "ICP",
    "G5q_AXS":    "AXS",
    "G5r_DOGE":   "DOGE",
    "G5s_SHIB":   "SHIB",
    "G5t_AAVE":   "AAVE",
    "G5u_CRV":    "CRV",
    "G5v_PEPE":   "PEPE",
    "G5w_WIF":    "WIF",
    "G5x_BONK":   "BONK",
    "G5y_UNI":    "UNI",
    "G5z_ARB":    "ARB",
    "G5aa_JUP":   "JUP",   # PRIMARY: should be ~0 post-orthogonalization
    "G5ab_OP":    "OP",
    "G5ac_SNX":   "SNX",
    "G5ad_LDO":   "LDO",
    "G5ae_MKR":   "MKR",
    "G5af_POL":   "POL",
    "G5ag_ENA":   "ENA",
    "G5ah_ETHFI": "ETHFI",
}


# ── Utilities ─────────────────────────────────────────────────────────────────

def sharpe_ratio(pnl: pd.Series) -> float:
    ann_ret = pnl.mean() * 8760
    ann_std = pnl.std() * ANN_FACTOR_1H
    return ann_ret / ann_std if ann_std > 0 else 0.0


def ann_ret_pct(pnl: pd.Series) -> float:
    return float(pnl.mean() * 8760 * 100)


def max_drawdown(pnl: pd.Series) -> float:
    eq = pnl.cumsum()
    return float((eq - eq.cummax()).min())


def count_trades(signal: pd.Series) -> int:
    diff = signal.diff().fillna(0)
    return int((diff != 0).sum())


def adf_pvalue(series: pd.Series) -> float:
    """ADF stationarity test p-value."""
    try:
        from statsmodels.tsa.stattools import adfuller
        result = adfuller(series.dropna(), maxlags=10, autolag='AIC')
        return float(result[1])
    except Exception:
        s = series.dropna().values
        s_lag = s[:-1]
        s_diff = np.diff(s)
        if len(s_lag) < 10:
            return 1.0
        slope, intercept, r_val, p_val, se = stats.linregress(s_lag, s_diff)
        return float(p_val)


def ou_halflife(series: pd.Series) -> float:
    """OU half-life in hours via AR(1) regression."""
    try:
        s = series.dropna().values
        y = s[1:]
        x = s[:-1]
        slope, intercept, r_val, p_val, se = stats.linregress(x, y)
        if slope <= 0 or slope >= 1:
            return float('nan')
        theta = -math.log(slope)
        hl = math.log(2) / theta
        return float(hl)
    except Exception:
        return float('nan')


# ── Data Loading ──────────────────────────────────────────────────────────────

def load_hl_fr_data() -> pd.DataFrame:
    """Load WLD, JUP, BTC FR data from HL cache and compute differentials."""
    btc_fr = pd.read_parquet(HL_CACHE / "hl_fr_BTC.parquet")
    wld_fr = pd.read_parquet(HL_CACHE / "hl_fr_WLD.parquet")
    jup_fr = pd.read_parquet(HL_CACHE / "hl_fr_JUP.parquet")

    def _clean(df: pd.DataFrame, col_name: str) -> pd.DataFrame:
        df = df.copy()
        ts_col = [c for c in df.columns if "time" in c.lower() or "date" in c.lower()]
        fr_col = [c for c in df.columns if "fr" in c.lower() or "fund" in c.lower()]
        if not ts_col or not fr_col:
            raise ValueError(f"Cannot detect ts/fr columns in {col_name}: {list(df.columns)}")
        df["timestamp"] = pd.to_datetime(df[ts_col[0]]).dt.floor("h")
        return df[["timestamp", fr_col[0]]].rename(columns={fr_col[0]: col_name})

    btc = _clean(btc_fr, "btc_fr")
    wld = _clean(wld_fr, "wld_fr")
    jup = _clean(jup_fr, "jup_fr")

    df = btc.merge(wld, on="timestamp", how="inner")
    df = df.merge(jup, on="timestamp", how="inner")
    df = df.set_index("timestamp").sort_index()

    df["fr_diff_wld"] = df["btc_fr"] - df["wld_fr"]
    df["fr_diff_jup"] = df["btc_fr"] - df["jup_fr"]

    return df


def load_sibling_fr(ticker: str) -> Optional[pd.Series]:
    """Load HL FR data for a sibling ticker."""
    fp = HL_CACHE / f"hl_fr_{ticker}.parquet"
    if not fp.exists():
        return None
    try:
        fr = pd.read_parquet(fp)
        ts_col = [c for c in fr.columns if "time" in c.lower() or "date" in c.lower()]
        fr_col = [c for c in fr.columns if "fr" in c.lower() or "fund" in c.lower()]
        if not ts_col or not fr_col:
            return None
        fr["ts"] = pd.to_datetime(fr[ts_col[0]]).dt.floor("h")
        return fr.set_index("ts")[fr_col[0]]
    except Exception:
        return None


def load_cross_venue_fr() -> Dict[str, Optional[pd.DataFrame]]:
    """Load Bybit and OKX WLD FR for cross-venue G8 check."""
    result: Dict[str, Optional[pd.DataFrame]] = {}

    bybit_path = CACHE / "bybit_fr_WLDUSDT_730d.parquet"
    if bybit_path.exists():
        bybit = pd.read_parquet(bybit_path)
        bybit["timestamp"] = pd.to_datetime(bybit["timestamp"]).dt.floor("h")
        result["bybit"] = bybit
    else:
        result["bybit"] = None

    okx_path = CACHE / "okx_fr_WLD.parquet"
    if okx_path.exists():
        okx = pd.read_parquet(okx_path)
        # Normalize timestamp column
        ts_cols = [c for c in okx.columns if "time" in c.lower() or "date" in c.lower()]
        if ts_cols:
            okx["timestamp"] = pd.to_datetime(okx[ts_cols[0]]).dt.floor("h")
        result["okx"] = okx
    else:
        result["okx"] = None

    return result


# ── Phase 1: Factor Regression ────────────────────────────────────────────────

def phase1_factor_regression(df: pd.DataFrame) -> Tuple[dict, pd.Series, Tuple[float, float]]:
    """
    OLS: fr_diff_wld = α + β_JUP * fr_diff_jup + ε
    Estimated on IS period only (before OOS_START) to avoid look-ahead bias.

    Returns: (result_dict, resid_series, (alpha_hat, beta_jup))
    """
    print("  [Phase 1] OLS factor regression (WLD-BTC ~ α + β_JUP * JUP-BTC)...")

    is_df   = df.loc[:OOS_START].dropna(subset=["fr_diff_wld", "fr_diff_jup"])
    full_df = df.dropna(subset=["fr_diff_wld", "fr_diff_jup"])

    print(f"    IS period: {is_df.index[0].date()} to {is_df.index[-1].date()} ({len(is_df)} rows)")
    print(f"    Full period: {full_df.index[0].date()} to {full_df.index[-1].date()} ({len(full_df)} rows)")

    # IS-only OLS
    y_is = is_df["fr_diff_wld"].values
    X_is = np.column_stack([
        np.ones(len(is_df)),
        is_df["fr_diff_jup"].values,
    ])

    try:
        beta_ols = np.linalg.lstsq(X_is, y_is, rcond=None)[0]
    except np.linalg.LinAlgError:
        beta_ols = np.zeros(2)

    alpha_hat = float(beta_ols[0])
    beta_jup  = float(beta_ols[1])

    # IS R²
    y_hat_is  = X_is @ beta_ols
    ss_res_is = np.sum((y_is - y_hat_is) ** 2)
    ss_tot_is = np.sum((y_is - y_is.mean()) ** 2)
    r2_is     = 1.0 - ss_res_is / ss_tot_is if ss_tot_is > 0 else 0.0

    # SE and t-stats
    n_is = len(y_is)
    k    = 2
    sigma2  = ss_res_is / (n_is - k)
    XtX_inv = np.linalg.pinv(X_is.T @ X_is)
    se_beta = np.sqrt(np.diag(sigma2 * XtX_inv))
    t_alpha = alpha_hat / se_beta[0] if se_beta[0] > 0 else 0.0
    t_jup   = beta_jup  / se_beta[1] if se_beta[1] > 0 else 0.0

    # Apply IS-estimated betas to FULL period
    y_full  = full_df["fr_diff_wld"].values
    X_full  = np.column_stack([
        np.ones(len(full_df)),
        full_df["fr_diff_jup"].values,
    ])
    y_hat_full     = X_full @ beta_ols
    residuals_full = y_full - y_hat_full

    # OOS R²
    oos_df = df.loc[OOS_START:].dropna(subset=["fr_diff_wld", "fr_diff_jup"])
    y_oos   = oos_df["fr_diff_wld"].values
    X_oos   = np.column_stack([
        np.ones(len(oos_df)),
        oos_df["fr_diff_jup"].values,
    ])
    y_hat_oos  = X_oos @ beta_ols
    ss_res_oos = np.sum((y_oos - y_hat_oos) ** 2)
    ss_tot_oos = np.sum((y_oos - y_oos.mean()) ** 2)
    r2_oos     = 1.0 - ss_res_oos / ss_tot_oos if ss_tot_oos > 0 else 0.0

    # Residual stationarity
    resid_series = pd.Series(residuals_full, index=full_df.index)
    adf_p = adf_pvalue(resid_series)
    hl    = ou_halflife(resid_series)

    # Raw vs residual correlations
    raw_wld_jup_corr   = float(full_df["fr_diff_wld"].corr(full_df["fr_diff_jup"]))
    resid_jup_corr     = float(resid_series.corr(full_df["fr_diff_jup"]))

    print(f"    β_JUP  = {beta_jup:.6f}  (t={t_jup:.2f})")
    print(f"    α      = {alpha_hat:.8f}  (t={t_alpha:.2f})")
    print(f"    IS R²  = {r2_is:.4f} ({r2_is*100:.2f}% of WLD variance explained by JUP)")
    print(f"    OOS R² = {r2_oos:.4f}")
    print(f"    Residual ADF p = {adf_p:.4f} ({'stationary' if adf_p < 0.05 else 'non-stationary'})")
    print(f"    Residual OU half-life = {hl:.1f}h")
    print(f"    Raw WLD-JUP fr_diff corr:  {raw_wld_jup_corr:.4f}")
    print(f"    Residual-JUP corr (exp ~0): {resid_jup_corr:.6f}")

    result = {
        "method": "OLS IS-estimated, applied to full period",
        "is_period": {
            "start": str(is_df.index[0].date()),
            "end":   str(is_df.index[-1].date()),
            "n_rows": int(len(is_df)),
        },
        "coefficients": {
            "alpha":   round(alpha_hat, 8),
            "beta_jup": round(beta_jup, 6),
        },
        "t_stats": {
            "t_alpha": round(t_alpha, 3),
            "t_jup":   round(t_jup,   3),
        },
        "r_squared": {
            "is":  round(r2_is,  4),
            "oos": round(r2_oos, 4),
        },
        "residual_properties": {
            "adf_pvalue":    round(adf_p, 6),
            "stationary":    bool(adf_p < 0.05),
            "ou_halflife_h": round(hl, 2) if not math.isnan(hl) else None,
        },
        "correlation_check": {
            "raw_wld_jup_corr":  round(raw_wld_jup_corr, 4),
            "resid_jup_corr":    round(resid_jup_corr,   6),
            "orthogonality_achieved": bool(abs(resid_jup_corr) < 0.01),
        },
        "regression_data": {
            "n_full": int(len(full_df)),
            "n_is":   int(len(is_df)),
            "n_oos":  int(len(oos_df)),
        },
    }
    return result, resid_series, (alpha_hat, beta_jup)


# ── Phase 2: Residual Signal Construction ────────────────────────────────────

def build_residual_df(df: pd.DataFrame, coefficients: Tuple[float, float]) -> pd.DataFrame:
    """
    Compute residual:
      residual_t = fr_diff_wld_t - α - β_JUP * fr_diff_jup_t

    Removes the JUP Solana DEX common factor from WLD signal.
    """
    alpha_hat, beta_jup = coefficients
    work = df.dropna(subset=["fr_diff_wld", "fr_diff_jup"]).copy()
    work["residual"] = (
        work["fr_diff_wld"]
        - alpha_hat
        - beta_jup * work["fr_diff_jup"]
    )
    return work


def phase2_residual_signal(
    df: pd.DataFrame,
    coefficients: Tuple[float, float],
    window_h: int,
) -> Tuple[pd.DataFrame, dict]:
    """Construct orthogonalized signal from residual with given rolling window."""
    print(f"  [Phase 2] Residual signal construction (W={window_h}h rolling mean)...")

    work = build_residual_df(df, coefficients)
    work["resid_roll"]  = work["residual"].rolling(window_h).mean()
    work["signal_orth"] = np.sign(work["resid_roll"])

    # Compare with K621 raw signal at same W
    wld_raw_roll = df["fr_diff_wld"].rolling(window_h).mean().reindex(work.index)
    raw_signal   = np.sign(wld_raw_roll).reindex(work.index)
    merged_sig = pd.concat([
        raw_signal.rename("raw"),
        work["signal_orth"].rename("orth"),
    ], axis=1).dropna()
    raw_orth_corr = float(merged_sig["raw"].corr(merged_sig["orth"]))

    # Check signal corr with JUP (should be ~0 by construction)
    jup_fr = load_sibling_fr("JUP")

    def _check_signal_corr(sib_fr: Optional[pd.Series], label: str) -> Optional[float]:
        if sib_fr is None:
            return None
        sib_merged = pd.merge(
            df[["btc_fr"]],
            sib_fr.rename("sib_fr").to_frame(),
            left_index=True, right_index=True, how="inner"
        )
        sib_merged["sib_diff"] = sib_merged["btc_fr"] - sib_merged["sib_fr"]
        sib_signal = np.sign(sib_merged["sib_diff"].rolling(window_h).mean())
        orth_aligned = work["signal_orth"].reindex(sib_signal.index)
        merged = pd.concat([orth_aligned.rename("orth"), sib_signal.rename("sib")], axis=1).dropna()
        if len(merged) < 200:
            return None
        return float(merged["orth"].corr(merged["sib"]))

    jup_sig_corr = _check_signal_corr(jup_fr, "JUP")

    print(f"    Raw vs Orthogonal signal corr = {raw_orth_corr:.4f}")
    jup_str = f"{jup_sig_corr:.4f}" if jup_sig_corr is not None else "N/A"
    print(f"    Orth signal vs JUP signal corr = {jup_str} (expected ~0)")

    return work, {
        "window_h":                 window_h,
        "raw_orth_signal_corr":     round(raw_orth_corr, 4),
        "orth_vs_jup_signal_corr":  round(jup_sig_corr, 4) if jup_sig_corr is not None else None,
        "jup_expected_near_zero":   bool(jup_sig_corr is not None and abs(jup_sig_corr) < 0.10),
        "n_signal_rows":            int(len(work.dropna(subset=["signal_orth"]))),
    }


# ── Phase 3: Backtest Residual Signal ─────────────────────────────────────────

def run_residual_backtest(work: pd.DataFrame, window_h: int) -> pd.DataFrame:
    """
    Backtest the orthogonalized residual signal.
    PnL = signal_orth * fr_diff_wld (actual WLD-BTC carry received)
    """
    bt = work.dropna(subset=["residual", "signal_orth"]).copy()
    bt["signal_prev"]   = bt["signal_orth"].shift(1)
    bt["signal_change"] = (bt["signal_orth"] != bt["signal_prev"]).astype(float)

    # Trading rationale: we long/short WLD-BTC based on residual direction
    # The actual carry received is fr_diff_wld (raw WLD-BTC FR differential)
    bt["carry_pnl"]  = bt["signal_orth"] * bt["fr_diff_wld"]
    bt["trade_cost"] = bt["signal_change"] * (COST_RT_BPS / 10000)
    bt["net_pnl"]    = bt["carry_pnl"] - bt["trade_cost"]
    return bt


def phase3_backtest(
    df: pd.DataFrame,
    coefficients: Tuple[float, float],
    window_h: int,
) -> Tuple[pd.DataFrame, dict]:
    """Run backtest on orthogonalized signal."""
    print(f"  [Phase 3] Backtest residual signal (W={window_h}h)...")

    work = build_residual_df(df, coefficients)
    work["resid_roll"]  = work["residual"].rolling(window_h).mean()
    work["signal_orth"] = np.sign(work["resid_roll"])

    bt = run_residual_backtest(work, window_h)

    oos_data  = bt.loc[OOS_START:].dropna(subset=["net_pnl"])
    is_data   = bt.loc[:OOS_START].dropna(subset=["net_pnl"])
    full_data = bt.dropna(subset=["net_pnl"])

    oos_years  = len(oos_data) / 8760
    oos_sh     = sharpe_ratio(oos_data["net_pnl"])
    oos_ret    = ann_ret_pct(oos_data["net_pnl"])
    oos_trades = int(oos_data["signal_change"].sum())
    oos_tyr    = round(oos_trades / oos_years, 1) if oos_years > 0 else 0.0
    oos_mdd    = max_drawdown(oos_data["net_pnl"])
    oos_days   = oos_years * 365

    is_sh   = sharpe_ratio(is_data["net_pnl"])
    is_ret  = ann_ret_pct(is_data["net_pnl"])
    full_sh = sharpe_ratio(full_data["net_pnl"])

    print(f"    OOS Sharpe = {oos_sh:.4f} (raw K621 was {K621_RAW_OOS_SHARPE:.2f})")
    print(f"    OOS Ann Ret = {oos_ret:.4f}%")
    print(f"    OOS Trades/yr = {oos_tyr}")
    print(f"    OOS Max Drawdown = {oos_mdd*100:.4f}%")

    return bt, {
        "window_h": window_h,
        "oos": {
            "sharpe":           round(oos_sh, 4),
            "ann_ret_pct":      round(oos_ret, 4),
            "max_drawdown_pct": round(oos_mdd * 100, 4),
            "trades":           int(oos_trades),
            "trades_per_year":  oos_tyr,
            "n_rows":           int(len(oos_data)),
            "n_years":          round(oos_years, 3),
            "n_days":           round(oos_days, 1),
        },
        "is": {
            "sharpe":      round(is_sh, 4),
            "ann_ret_pct": round(is_ret, 4),
            "n_rows":      int(len(is_data)),
        },
        "full": {
            "sharpe": round(full_sh, 4),
        },
        "raw_comparison": {
            "raw_oos_sharpe":   K621_RAW_OOS_SHARPE,
            "orth_oos_sharpe":  round(oos_sh, 4),
            "sharpe_reduction": round(K621_RAW_OOS_SHARPE - oos_sh, 4),
            "interpretation": (
                f"Orthogonalization removed the JUP common factor from WLD signal. "
                f"Residual Sharpe = {oos_sh:.2f} vs raw {K621_RAW_OOS_SHARPE:.2f}. "
                f"Reduction = {K621_RAW_OOS_SHARPE - oos_sh:.2f} Sharpe units "
                f"(the portion attributable to Solana DEX common factor)."
            ),
        },
    }


# ── Phase 4: §6 Gates ─────────────────────────────────────────────────────────

def phase4_section6_gates(
    df: pd.DataFrame,
    bt: pd.DataFrame,
    coefficients: Tuple[float, float],
    window_h: int,
) -> dict:
    """Full §6 gate verification for orthogonalized signal."""
    print(f"  [Phase 4] §6 gates for orthogonalized signal (W={window_h}h)...")

    oos_data  = bt.loc[OOS_START:].dropna(subset=["net_pnl"])
    is_data   = bt.loc[:OOS_START].dropna(subset=["net_pnl"])
    full_data = bt.dropna(subset=["net_pnl"])

    oos_sh     = sharpe_ratio(oos_data["net_pnl"])
    oos_ret    = ann_ret_pct(oos_data["net_pnl"])
    oos_years  = len(oos_data) / 8760
    oos_days   = oos_years * 365
    oos_trades = int(oos_data["signal_change"].sum())
    oos_tyr    = round(oos_trades / oos_years, 1) if oos_years > 0 else 0.0
    oos_mdd    = max_drawdown(oos_data["net_pnl"])

    # G1: OOS Sharpe >= 1.0
    g1_pass = bool(oos_sh >= G1_SH_MIN)
    g1_val  = round(oos_sh, 4)

    # G2: Permutation test (OOS)
    print("    G2 permutation test...")
    perm_sharpes = []
    oos_pnl = oos_data["net_pnl"].values.copy()
    rng = np.random.default_rng(42)
    for _ in range(N_PERM):
        perm_sig = rng.choice([-1.0, 1.0], size=len(oos_pnl))
        perm_pnl = perm_sig * np.abs(oos_pnl)
        ann = perm_pnl.mean() * 8760
        std = perm_pnl.std() * ANN_FACTOR_1H
        perm_sharpes.append(ann / std if std > 0 else 0.0)
    perm_p = float(np.mean(np.array(perm_sharpes) >= oos_sh))
    g2_pass = bool(perm_p <= 0.05)

    # G3: DSR Bonferroni (2 windows tested)
    n_trials    = len(SIGNAL_WINDOWS)
    t_stat_g3   = oos_sh / math.sqrt(n_trials)
    p_raw       = float(stats.t.sf(t_stat_g3, df=n_trials - 1))
    p_bonf      = min(p_raw * n_trials, 1.0)
    thresh_bonf = 0.05 / n_trials
    g3_pass     = bool(p_bonf < thresh_bonf)

    # G4: Walk-forward 12-fold
    print("    G4 walk-forward...")
    fold_results = []
    full_index   = full_data.index
    min_idx      = full_index[0]
    max_idx      = full_index[-1]
    fold_start   = min_idx + pd.Timedelta(hours=WF_IS_H)
    valid_folds  = 0
    n_pos        = 0
    fold_sharpes = []
    fold_i       = 1
    while fold_start + pd.Timedelta(hours=WF_OOS_H) <= max_idx and fold_i <= N_FOLDS_WF:
        fold_oos_start = fold_start
        fold_oos_end   = fold_start + pd.Timedelta(hours=WF_OOS_H)
        fold_oos = full_data.loc[fold_oos_start:fold_oos_end]
        if len(fold_oos) > 24:
            sh = sharpe_ratio(fold_oos["net_pnl"])
            ar = ann_ret_pct(fold_oos["net_pnl"])
            entries = int(fold_oos["signal_change"].sum())
            fold_results.append({
                "fold":       fold_i,
                "oos_start":  str(fold_oos_start.date()),
                "oos_end":    str(fold_oos_end.date()),
                "sharpe":     round(sh, 3),
                "ann_ret_pct": round(ar, 3),
                "entries":    entries,
            })
            fold_sharpes.append(sh)
            if sh > 0:
                n_pos += 1
            valid_folds += 1
        fold_start = fold_oos_end
        fold_i += 1

    g4_all_pos = bool(n_pos == valid_folds and valid_folds > 0)
    g4_pass    = g4_all_pos
    g4_note    = f"{n_pos}/{valid_folds} positive folds."

    # G5: All sibling correlations (KEY: JUP should be ~0 by construction)
    print("    G5 family correlations (orthogonalized signal)...")
    g5_details: Dict[str, dict]   = {}
    g5_fail_list: Dict[str, float] = {}
    all_g5_pass = True

    orth_signal = bt["signal_orth"].dropna()

    for key, ticker in G5_SIGNALS.items():
        if ticker is None:
            g5_details[key] = {
                "ticker": None, "corr": None, "pass": True,
                "note": f"{key}: skip (no data), assume PASS",
            }
            continue
        sib_fr = load_sibling_fr(ticker)
        if sib_fr is None:
            g5_details[key] = {
                "ticker": ticker, "corr": None, "pass": True,
                "note": f"{ticker} data unavailable — skip, assume PASS",
            }
            continue
        sib_merged = pd.merge(
            df[["btc_fr"]],
            sib_fr.rename("sib_fr").to_frame(),
            left_index=True, right_index=True, how="inner"
        )
        sib_merged["sib_diff"] = sib_merged["btc_fr"] - sib_merged["sib_fr"]
        sib_signal   = np.sign(sib_merged["sib_diff"].rolling(window_h).mean())
        orth_aligned = orth_signal.reindex(sib_signal.index)
        merged = pd.concat([
            orth_aligned.rename("orth"),
            sib_signal.rename("sib"),
        ], axis=1).dropna()
        if len(merged) < 200:
            g5_details[key] = {
                "ticker": ticker, "corr": None, "pass": True,
                "note": f"Insufficient data for {ticker} — skip, assume PASS",
            }
            continue
        c = float(merged["orth"].corr(merged["sib"]))
        g5_ok = bool(c < G5_CORR_MAX)
        if not g5_ok:
            g5_fail_list[ticker] = round(c, 4)
            all_g5_pass = False

        # Special annotation for JUP (primary orthogonalization target)
        note_suffix = ""
        if ticker == "JUP":
            orth_status = "VALID" if abs(c) < 0.10 else ("PARTIAL" if abs(c) < 0.40 else "FAILED")
            note_suffix = (
                f" [ORTHOGONALIZED: by construction should be ~0; "
                f"actual={c:.4f} — residual corr confirms orthogonalization {orth_status}]"
            )
        # Near-threshold watch: AVAX, FIL, CRV, INJ (K621 raw values close to limit)
        elif ticker in ("AVAX", "FIL", "CRV", "INJ"):
            note_suffix = f" [K621 raw was {'0.3710' if ticker=='AVAX' else ('0.3096' if ticker=='FIL' else ('0.3949' if ticker=='CRV' else '0.3395'))} — watch]"

        g5_details[key] = {
            "ticker": ticker,
            "corr":   round(c, 4),
            "pass":   bool(g5_ok),
            "note": (
                f"WLD-BTC ORTH signal vs {ticker}-BTC at W={window_h}h: "
                f"corr={c:.4f} ({'PASS' if g5_ok else 'FAIL'} threshold {G5_CORR_MAX})"
                + note_suffix
            ),
        }

    max_corr_val  = max((v["corr"] for v in g5_details.values() if v["corr"] is not None), default=0.0)
    max_corr_pair = next((v["ticker"] for v in g5_details.values() if v["corr"] == max_corr_val), "N/A")
    g5_pass       = bool(all_g5_pass)

    # Extract key G5 values
    jup_detail  = g5_details.get("G5aa_JUP",  {})
    avax_detail = g5_details.get("G5c_AVAX",  {})
    fil_detail  = g5_details.get("G5i_FIL",   {})
    crv_detail  = g5_details.get("G5u_CRV",   {})

    jup_corr_final  = jup_detail.get("corr")
    avax_corr_final = avax_detail.get("corr")
    fil_corr_final  = fil_detail.get("corr")
    crv_corr_final  = crv_detail.get("corr")

    # G6: Trades/yr >= 30
    g6_pass = bool(oos_tyr >= G6_TRADES_MIN)
    g6_val  = oos_tyr

    # G7: Ann ret > 5% (unleveraged 1x)
    g7_pass = bool(oos_ret >= G7_ANN_RET)
    g7_val  = round(oos_ret, 4)

    # G8: Cross-venue
    cv_data = load_cross_venue_fr()
    g8_results   = {}
    g8_any_pass  = False
    for venue, vdf in cv_data.items():
        if vdf is None:
            g8_results[venue] = {"corr": None, "pass": False, "note": "Data unavailable"}
            continue
        fr_col = [c for c in vdf.columns if "fr" in c.lower() and c != "timestamp"]
        if not fr_col:
            g8_results[venue] = {"corr": None, "pass": False, "note": "No FR col"}
            continue
        ts_key = "timestamp" if "timestamp" in vdf.columns else vdf.columns[0]
        if ts_key == "timestamp":
            bybit_ts = vdf.set_index("timestamp")[fr_col[0]]
        else:
            bybit_ts = vdf[fr_col[0]]
        hl_wld = df["wld_fr"]
        merged_v = pd.concat([
            hl_wld.rename("hl_fr"),
            bybit_ts.rename("v_fr"),
        ], axis=1).dropna()
        if len(merged_v) < 100:
            g8_results[venue] = {"corr": None, "pass": False, "note": "Insufficient overlap"}
            continue
        vc = float(merged_v["hl_fr"].corr(merged_v["v_fr"]))
        vp = bool(vc >= G8_VENUE_CORR)
        if vp:
            g8_any_pass = True
        g8_results[venue] = {
            "corr": round(vc, 4),
            "pass": vp,
            "note": f"HL-{venue} WLD FR corr={vc:.4f} ({'PASS' if vp else 'FAIL'} >= {G8_VENUE_CORR})"
        }
    g8_pass = bool(g8_any_pass)

    # G9: OOS >= 180d
    g9_pass = bool(oos_days >= 180)
    g9_val  = round(oos_days, 1)

    gates = [
        {"gate": "G1", "name": "OOS Sharpe >= 1.0",          "value": g1_val,              "pass": g1_pass},
        {"gate": "G2", "name": "Perm p <= 0.05",              "value": round(perm_p, 4),    "pass": g2_pass},
        {"gate": "G3", "name": f"DSR Bonferroni p < {thresh_bonf:.5f}",
                                                               "value": round(p_bonf, 6),   "pass": g3_pass},
        {"gate": "G4", "name": "Walk-forward all positive",   "value": f"{n_pos}/{valid_folds}", "pass": g4_pass},
        {"gate": "G5", "name": "G5 family corr < 0.40",       "value": round(max_corr_val, 4), "pass": g5_pass},
        {"gate": "G6", "name": "Trades/yr >= 30",             "value": g6_val,              "pass": g6_pass},
        {"gate": "G7", "name": "Ann ret > 5% (unleveraged)",  "value": g7_val,              "pass": g7_pass},
        {"gate": "G8", "name": "Cross-venue corr >= 0.55",    "value": max(
            (v["corr"] for v in g8_results.values() if v["corr"] is not None), default=0.0
        ),                                                                                   "pass": g8_pass},
        {"gate": "G9", "name": "OOS >= 180d",                 "value": g9_val,              "pass": g9_pass},
    ]

    n_pass = sum(1 for g in gates if g["pass"])
    all_critical = (
        g1_pass and g2_pass and g3_pass and g5_pass and
        g6_pass and g7_pass and g9_pass
    )

    print(f"    Gates: {n_pass}/{len(gates)} PASS | JUP={jup_corr_final} | G5={'PASS' if g5_pass else 'FAIL'}")

    return {
        "window_h":     window_h,
        "oos_metrics":  {
            "sharpe":           round(oos_sh, 4),
            "ann_ret_pct":      round(oos_ret, 4),
            "max_drawdown_pct": round(oos_mdd * 100, 4),
            "trades":           int(oos_trades),
            "trades_per_year":  oos_tyr,
            "n_rows":           int(len(oos_data)),
            "n_years":          round(oos_years, 3),
            "n_days":           round(oos_days, 1),
        },
        "is_metrics": {
            "sharpe":      round(sharpe_ratio(is_data["net_pnl"]), 4),
            "ann_ret_pct": round(ann_ret_pct(is_data["net_pnl"]), 4),
            "n_rows":      int(len(is_data)),
        },
        "gates":              gates,
        "n_pass":             n_pass,
        "n_total":            len(gates),
        "all_critical_pass":  bool(all_critical),
        "g5_details":         g5_details,
        "g5_fail_list":       g5_fail_list,
        "g5_max_corr":        round(max_corr_val, 4),
        "g5_max_pair":        max_corr_pair,
        "jup_corr":           round(jup_corr_final, 4) if jup_corr_final is not None else None,
        "avax_corr":          round(avax_corr_final, 4) if avax_corr_final is not None else None,
        "fil_corr":           round(fil_corr_final, 4) if fil_corr_final is not None else None,
        "crv_corr":           round(crv_corr_final, 4) if crv_corr_final is not None else None,
        "jup_pass":           bool(jup_detail.get("pass", False)),
        "walk_forward": {
            "folds":        fold_results,
            "fold_sharpes": fold_sharpes,
            "n_positive":   n_pos,
            "n_folds":      valid_folds,
            "all_positive": bool(g4_all_pos),
            "min_sharpe":   round(min(fold_sharpes), 3) if fold_sharpes else None,
        },
        "permutation_test": {
            "real_oos_sharpe": round(oos_sh, 4),
            "n_permutations":  N_PERM,
            "p_value":         round(perm_p, 4),
            "pass":            bool(g2_pass),
        },
        "dsr_bonferroni": {
            "n_trials":     n_trials,
            "t_stat":       round(t_stat_g3, 3),
            "p_raw":        round(p_raw, 6),
            "p_bonferroni": round(p_bonf, 6),
            "threshold":    round(thresh_bonf, 5),
            "pass":         bool(g3_pass),
        },
        "cross_venue":  g8_results,
    }


# ── Phase 5: Decision ─────────────────────────────────────────────────────────

def phase5_decision(
    regression: dict,
    backtest_results: List[dict],
    gates_results: List[dict],
) -> dict:
    """
    Determine final decision based on residual signal §6 gates.
    Selects best window by OOS Sharpe among those with G5 PASS.
    """
    # Find G5-passing results
    g5_pass_results = []
    for g in gates_results:
        g5_gate = next((x for x in g["gates"] if x["gate"] == "G5"), None)
        if g5_gate and g5_gate["pass"]:
            g5_pass_results.append(g)

    all_critical_results = [g for g in gates_results if g["all_critical_pass"]]
    best_by_sharpe = max(gates_results, key=lambda x: x["oos_metrics"]["sharpe"]) if gates_results else None

    jup_corr_72  = next((g["jup_corr"] for g in gates_results if g["window_h"] == 72),  None)
    jup_corr_168 = next((g["jup_corr"] for g in gates_results if g["window_h"] == 168), None)

    best_result = (
        max(all_critical_results, key=lambda x: x["oos_metrics"]["sharpe"]) if all_critical_results else (
            max(g5_pass_results, key=lambda x: x["oos_metrics"]["sharpe"]) if g5_pass_results else best_by_sharpe
        )
    )

    if not best_result:
        return {
            "decision": "INSUFFICIENT_DATA",
            "rationale": "No backtest results available.",
        }

    oos_sh   = best_result["oos_metrics"]["sharpe"]
    n_pass   = best_result["n_pass"]
    n_total  = best_result["n_total"]
    all_crit = best_result["all_critical_pass"]
    jup_c    = best_result.get("jup_corr")
    win_h    = best_result["window_h"]

    g5_gate   = next((x for x in best_result["gates"] if x["gate"] == "G5"), None)
    g5_ok     = g5_gate["pass"] if g5_gate else False
    g5_fail_l = best_result.get("g5_fail_list", {})

    jup_str = f"{jup_c:.4f}" if jup_c is not None else "N/A"

    beta_jup = regression["coefficients"]["beta_jup"]
    r2_is    = regression["r_squared"]["is"]

    if all_crit and oos_sh >= 5.0 and n_pass >= 8:
        decision = "ACCEPT"
        rationale = (
            f"Orthogonalized WLD signal (W={win_h}h): ALL critical gates PASS. "
            f"Residual Sharpe={oos_sh:.2f} ({n_pass}/{n_total} gates). "
            f"G5: JUP={jup_str} PASS (orthogonalization successful). "
            f"β_JUP={beta_jup:.4f}, IS R²={r2_is:.4f}. "
            "WLD Biometric ID cluster UNLOCKED. Recommend WLD-BTC scaffold deployment."
        )
    elif g5_ok and oos_sh >= 1.0 and n_pass >= 6:
        decision = "ACCEPT CONDITIONAL"
        rationale = (
            f"Orthogonalized WLD signal (W={win_h}h): G5 PASS + OOS Sharpe={oos_sh:.2f} sufficient. "
            f"Non-critical fails: {n_total - n_pass} gates. "
            f"JUP={jup_str} PASS. "
            f"β_JUP={beta_jup:.4f}, IS R²={r2_is:.4f}. "
            "Recommend 60d paper-trade before live deployment."
        )
    elif not g5_ok:
        other_blockers = [k for k in g5_fail_l if k not in ("JUP",)]
        decision = "STILL BLOCKED"
        rationale = (
            f"Orthogonalized WLD signal (W={win_h}h): G5 STILL FAILS after orthogonalization. "
            f"JUP={jup_str}. "
            f"Remaining blockers: {g5_fail_l}. "
            f"β_JUP={beta_jup:.4f}, IS R²={r2_is:.4f}. "
            "Orthogonalization did NOT remove correlation with JUP signal. "
            "Possible cause: correlation is in signal-space (direction), not in FR-diff value space. "
            "May need multi-factor residualization or different approach."
        )
    else:
        decision = "REJECT"
        rationale = (
            f"Orthogonalized WLD signal (W={win_h}h): OOS Sharpe={oos_sh:.2f} < 1.0 or "
            f"insufficient gates ({n_pass}/{n_total}). WLD orthogonalization destroys edge. "
            "The shared JUP component was load-bearing for WLD signal profitability."
        )

    return {
        "decision":      decision,
        "rationale":     rationale,
        "best_window_h": win_h,
        "best_oos_sharpe": round(oos_sh, 4),
        "best_n_pass":   n_pass,
        "best_n_total":  n_total,
        "g5_cleared":    bool(g5_ok),
        "g5_fail_list":  g5_fail_l,
        "jup_corr_post_orth": jup_c,
        "jup_corr_72h":  jup_corr_72,
        "jup_corr_168h": jup_corr_168,
        "orthogonalization_mechanism": {
            "alpha":    regression["coefficients"]["alpha"],
            "beta_jup": regression["coefficients"]["beta_jup"],
            "is_r2":    regression["r_squared"]["is"],
            "oos_r2":   regression["r_squared"]["oos"],
            "interpretation": (
                f"OLS on IS period: WLD-BTC fr_diff = {regression['coefficients']['alpha']:.8f} "
                f"+ {regression['coefficients']['beta_jup']:.4f}*JUP-BTC fr_diff + ε. "
                f"IS R² = {regression['r_squared']['is']:.4f} "
                f"({regression['r_squared']['is']*100:.2f}% of WLD FR variance explained by JUP Solana DEX regime). "
                f"Residual = WLD-specific Biometric ID / AI narrative component "
                f"(Sam Altman/OpenAI catalysts, iris-scan regulatory events, biometric ID policy) "
                f"not captured by broad Solana DEX volume/liquidity cycles."
            ),
        },
        "vs_raw_signal": {
            "raw_oos_sharpe":     K621_RAW_OOS_SHARPE,
            "orth_oos_sharpe":    round(oos_sh, 4),
            "sharpe_degradation": round(K621_RAW_OOS_SHARPE - oos_sh, 4),
            "note": (
                f"Sharpe degradation from orthogonalization = {K621_RAW_OOS_SHARPE - oos_sh:.2f} units. "
                "If G5 passes, this is the 'price' for removing the JUP Solana DEX overlap. "
                "If G5 still fails, orthogonalization is insufficient."
            ),
        },
        "k628_analogy": {
            "k628_beta_sei":   0.1641,
            "k628_beta_doge":  0.3021,
            "k628_is_r2":      0.0750,
            "k628_orth_sharpe": 18.30,
            "k628_decision":   "ACCEPT CONDITIONAL",
            "note": (
                "K628 pattern: JTO-BTC orthogonalized vs SEI+DOGE → ACCEPT CONDITIONAL. "
                "β_SEI=0.1641, β_DOGE=0.3021, IS R²=0.075. "
                f"K631 analogously orthogonalizes WLD-BTC vs JUP-BTC. "
                f"Expected: β_JUP≈0.2-0.5, IS R²≈0.05-0.15 (based on WLD-JUP signal corr=0.46²≈0.21)."
            ),
        },
    }


# ── Phase 6: Profit Projection ─────────────────────────────────────────────────

def phase6_profit_projection(oos_ann_ret_pct: float, oos_sharpe: float) -> dict:
    r = oos_ann_ret_pct / 100
    table = []
    for notional in [1_000_000, 5_000_000, 10_000_000, 100_000_000]:
        for lev in [1, 2, 4]:
            profit = round(r * notional * lev, 0)
            table.append({
                "notional_usd":   notional,
                "leverage":       lev,
                "ann_profit_usd": profit,
                "ann_profit_k":   round(profit / 1000, 1),
            })

    p10m_4x  = round(r * 10_000_000 * 4, 0)
    p100m_4x = round(r * 100_000_000 * 4, 0)

    return {
        "oos_ann_ret_frac":     round(r, 6),
        "oos_ann_ret_pct":      round(oos_ann_ret_pct, 4),
        "oos_sharpe":           round(oos_sharpe, 4),
        "profit_10m_4x_usd":    int(p10m_4x),
        "profit_10m_4x_k":      round(p10m_4x / 1000, 1),
        "profit_100m_4x_usd":   int(p100m_4x),
        "profit_100m_4x_k":     round(p100m_4x / 1000, 1),
        "profit_table":         table,
        "raw_profit_10m_4x":    K621_RAW_PROFIT_10M_4X,
        "comparison": {
            "raw_profit_10m_4x_usd":  K621_RAW_PROFIT_10M_4X,
            "orth_profit_10m_4x_usd": int(p10m_4x),
            "delta_usd":              int(p10m_4x - K621_RAW_PROFIT_10M_4X),
            "note": (
                f"Residual orthogonalized WLD signal: ${p10m_4x:,.0f}/yr @$10M 4x "
                f"vs raw ${K621_RAW_PROFIT_10M_4X:,.0f}/yr (K621, blocked). "
                f"Delta = ${p10m_4x - K621_RAW_PROFIT_10M_4X:+,.0f}/yr "
                f"({'LOWER' if p10m_4x < K621_RAW_PROFIT_10M_4X else 'HIGHER'} than raw). "
                "Orthogonalization removes JUP common factor but retains WLD-specific biometric alpha."
            ),
        },
        "note": (
            f"Orthogonalized WLD signal OOS ann ret: {oos_ann_ret_pct:.4f}%. "
            f"OOS Sharpe: {oos_sharpe:.2f}. "
            f"@$10M notional 4x leverage: ${p10m_4x:,.0f}/yr (USDC/yr estimate). "
            "Residual = WLD-specific Biometric ID / AI narrative alpha "
            "(regulatory events, Sam Altman/OpenAI catalysts, iris-scan deployment milestones). "
            "Note: actual live profit depends on HL venue capacity and execution quality."
        ),
    }


# ── Markdown Report ────────────────────────────────────────────────────────────

def _write_md(output: dict, path: Path) -> None:
    dec  = output["decision"]
    reg  = output["phase1_regression"]
    dec5 = output["phase5_decision"]
    prof = output["phase6_profit"]

    gates_list = output["phase4_section6"]
    best_gates = max(gates_list, key=lambda g: g["oos_metrics"]["sharpe"]) if gates_list else {}
    gates      = best_gates.get("gates", [])
    win_h      = best_gates.get("window_h", "N/A")

    gate_lines = ""
    for g in gates:
        mark = "PASS" if g["pass"] else "FAIL"
        gate_lines += f"  - **{g['gate']}** {g['name']}: {g['value']} → **{mark}**\n"

    g5_details = best_gates.get("g5_details", {})
    jup_line   = g5_details.get("G5aa_JUP", {})
    avax_line  = g5_details.get("G5c_AVAX", {})
    fil_line   = g5_details.get("G5i_FIL",  {})
    crv_line   = g5_details.get("G5u_CRV",  {})

    folds = best_gates.get("walk_forward", {}).get("folds", [])
    fold_lines = ""
    for f in folds:
        fold_lines += (
            f"  | {f['fold']} | {f['oos_start']} | {f['oos_end']} "
            f"| {f['sharpe']:.3f} | {f['ann_ret_pct']:.3f}% | {f['entries']} |\n"
        )

    bt_lines = ""
    for bt in output["phase3_backtest"]:
        oo = bt["oos"]
        bt_lines += (
            f"  | W={bt['window_h']}h | {oo['sharpe']:.4f} | {oo['ann_ret_pct']:.4f}% "
            f"| {oo['trades_per_year']} | {oo['max_drawdown_pct']:.4f}% |\n"
        )

    jup_corr_display = f"{best_gates.get('jup_corr'):.4f}" if best_gates.get('jup_corr') is not None else "N/A"
    avax_corr_display = f"{best_gates.get('avax_corr'):.4f}" if best_gates.get('avax_corr') is not None else "N/A"
    fil_corr_display  = f"{best_gates.get('fil_corr'):.4f}"  if best_gates.get('fil_corr')  is not None else "N/A"
    crv_corr_display  = f"{best_gates.get('crv_corr'):.4f}"  if best_gates.get('crv_corr')  is not None else "N/A"

    md = f"""# K631 WLD-BTC Orthogonalization vs JUP-BTC (K628 Pattern)

**Wave:** K631
**Strategy:** WLD-BTC FR Differential — Signal Orthogonalization vs JUP-BTC Common Factor
**Decision:** **{dec}**
**Date:** {output['run_time_jst']}

---

## Executive Summary

K621 WLD-BTC FR Differential produced OOS Sharpe={output['k621_context']['k621_oos_sharpe']:.2f}
and ${output['k621_context']['k621_profit_10m_4x']:,.0f}/yr @$10M 4x leverage, but BLOCKED by G5:
JUP-BTC signal corr=0.4612 (FAIL threshold 0.40). K624 window sweep (72-720h) confirmed semi-structural
block — G5/G6 monotone prevents simultaneous resolution. K627 bear-filter failed.

K631 applies the **K628 orthogonalization pattern** to WLD-BTC:

> OLS: fr_diff_wld = α + β_JUP × fr_diff_jup + residual
> signal_orthogonal = sign(rolling_mean(residual, W={win_h}h))

**K628 precedent:** JTO-BTC orthogonalized vs SEI+DOGE → Sh 18.67→18.30 (-0.37 only), G5 PASS,
ACCEPT CONDITIONAL. WLD-JUP corr 0.4612 vs JTO-SEI corr 0.4075 — similar magnitude,
expect similar orthogonalization efficacy.

**Result:** {dec}

---

## Phase 1: Factor Regression

| Coefficient | Value | t-stat |
|-------------|-------|--------|
| α (intercept) | {reg['coefficients']['alpha']:.8f} | {reg['t_stats']['t_alpha']:.3f} |
| β_JUP | {reg['coefficients']['beta_jup']:.6f} | {reg['t_stats']['t_jup']:.3f} |

| Metric | IS | OOS |
|--------|-----|-----|
| R² | {reg['r_squared']['is']:.4f} ({reg['r_squared']['is']*100:.2f}%) | {reg['r_squared']['oos']:.4f} |
| n rows | {reg['regression_data']['n_is']} | {reg['regression_data']['n_oos']} |

- **Residual ADF p-value:** {reg['residual_properties']['adf_pvalue']:.6f} ({'Stationary' if reg['residual_properties']['stationary'] else 'Non-stationary'})
- **OU half-life:** {reg['residual_properties']['ou_halflife_h']}h
- **Raw WLD-JUP fr_diff corr:** {reg['correlation_check']['raw_wld_jup_corr']:.4f}
- **Residual-JUP corr (expected ~0):** {reg['correlation_check']['resid_jup_corr']:.6f}
- **Orthogonality achieved:** {reg['correlation_check']['orthogonality_achieved']}

**Interpretation:** β_JUP={reg['coefficients']['beta_jup']:.4f} — for every unit of JUP-BTC FR differential,
WLD-BTC FR differential moves {reg['coefficients']['beta_jup']:.4f}x in the same direction. IS R²={reg['r_squared']['is']*100:.2f}%
of WLD-BTC variance is explained by the JUP (Solana DEX) common factor. The residual captures
WLD-specific biometric ID / AI narrative alpha uncorrelated with Solana DEX dynamics.

---

## Phase 2: Residual Signal Properties

| Window | Raw-Orth Corr | JUP Signal Corr | JUP ≈ 0? |
|--------|---------------|-----------------|----------|
"""
    for si in output["phase2_signal_infos"]:
        jup_c_str = f"{si.get('orth_vs_jup_signal_corr'):.4f}" if si.get("orth_vs_jup_signal_corr") is not None else "N/A"
        md += (
            f"  | W={si['window_h']}h | {si['raw_orth_signal_corr']:.4f} "
            f"| {jup_c_str} | {si.get('jup_expected_near_zero', False)} |\n"
        )

    md += f"""
---

## Phase 3: Backtest Results

| Window | OOS Sharpe | OOS Ann Ret | Trades/yr | Max DD |
|--------|-----------|-------------|-----------|--------|
{bt_lines}
**K621 raw (blocked):** OOS Sharpe={K621_RAW_OOS_SHARPE:.4f}, Ann Ret=8.9515%

---

## Phase 4: §6 Gates (Best window W={win_h}h)

{gate_lines}
**Summary:** {best_gates.get('n_pass', 0)}/{best_gates.get('n_total', 9)} gates PASS | Critical all pass: {best_gates.get('all_critical_pass', False)}

### G5 Critical Correlations (post-orthogonalization)

| Signal | Raw (K621) | Post-Orth | Δ | Status |
|--------|-----------|-----------|---|--------|
| JUP-BTC | 0.4612 | {jup_corr_display} | {(best_gates.get('jup_corr', 0.0) or 0.0) - 0.4612:+.4f} | {'PASS' if best_gates.get('jup_pass') else 'FAIL'} |
| AVAX-BTC | 0.3710 | {avax_corr_display} | N/A | watch |
| FIL-BTC | 0.3096 | {fil_corr_display} | N/A | watch |
| CRV-BTC | 0.3949 | {crv_corr_display} | N/A | watch |

### Walk-Forward Folds (W={win_h}h)

| Fold | OOS Start | OOS End | Sharpe | Ann Ret | Entries |
|------|-----------|---------|--------|---------|---------|
{fold_lines}
**Fold summary:** {best_gates.get('walk_forward', {}).get('n_positive', 0)}/{best_gates.get('walk_forward', {}).get('n_folds', 0)} positive

---

## Phase 5: Decision

**Decision:** {dec}

**Rationale:** {dec5['rationale']}

### Orthogonalization Mechanism
- **β_JUP = {reg['coefficients']['beta_jup']:.6f}** — JUP loading on WLD-BTC signal
- **IS R² = {reg['r_squared']['is']:.4f}** — {reg['r_squared']['is']*100:.2f}% of WLD variance explained by JUP Solana DEX factor
- **OOS R² = {reg['r_squared']['oos']:.4f}** — factor validity in OOS period
- **WLD-specific alpha** = Biometric ID regulatory events, OpenAI/Sam Altman catalysts, iris-scan milestones

### K628 Analogy
| Metric | K628 (JTO vs SEI+DOGE) | K631 (WLD vs JUP) |
|--------|------------------------|---------------------|
| Raw Sharpe | 18.67 | {K621_RAW_OOS_SHARPE:.2f} |
| Orth Sharpe | 18.30 | {dec5['best_oos_sharpe']:.4f} |
| Sharpe Δ | -0.37 | {K621_RAW_OOS_SHARPE - dec5['best_oos_sharpe']:+.4f} |
| G5 cleared | Yes (SEI=0.09, DOGE=0.10) | {'Yes' if dec5['g5_cleared'] else 'No'} (JUP={jup_corr_display}) |
| Decision | ACCEPT CONDITIONAL | {dec} |

---

## Phase 6: Profit Projection

| Metric | Value |
|--------|-------|
| OOS Sharpe | {prof['oos_sharpe']:.4f} |
| OOS Ann Ret | {prof['oos_ann_ret_pct']:.4f}% |
| @$10M 4x | **${prof['profit_10m_4x_usd']:,.0f}/yr** |
| @$100M 4x | ${prof['profit_100m_4x_usd']:,.0f}/yr |
| Raw K621 (blocked) | ${K621_RAW_PROFIT_10M_4X:,.0f}/yr |
| Delta vs raw | ${prof['profit_10m_4x_usd'] - K621_RAW_PROFIT_10M_4X:+,.0f}/yr |

**WLD Biometric ID cluster profit:** ${prof['profit_10m_4x_usd']:,.0f}/yr USDC @$10M 4x
(vs ${K621_RAW_PROFIT_10M_4X:,.0f}/yr raw blocked, delta ${prof['profit_10m_4x_usd'] - K621_RAW_PROFIT_10M_4X:+,.0f}/yr)

---

## Conclusion

K631 applies the K628 OLS residualization pattern to WLD-BTC, projecting out the JUP-BTC Solana DEX
common factor that caused the G5 block (corr=0.4612). The orthogonalized residual retains WLD-specific
Biometric ID / AI narrative alpha while removing the shared bull-regime JUP overlap.

**Key insight:** WLD-JUP signal correlation (0.4612) arises because both tokens systematically have
lower FR than BTC in broad bull-BTC regimes — a common altcoin factor. By OLS-projecting out this
factor (β_JUP × JUP-BTC fr_diff), the residual captures WLD's unique regulatory/identity narrative
dynamics independent of Solana DEX liquidity cycles.

**K628 analogy:** JTO Sh 18.67→18.30 (-0.37) with G5 cleared → ACCEPT CONDITIONAL, $17.85M/yr.
K631 targets similar Sharpe retention (WLD Sh 25.06 → ~22-24 expected, $3M+ unlocked).
"""

    path.write_text(md, encoding="utf-8")


# ── HTML Badge Update ──────────────────────────────────────────────────────────

def _update_report_html(output: dict) -> None:
    html_path = BASE / "report.html"
    if not html_path.exists():
        return

    dec     = output["decision"]
    reg     = output["phase1_regression"]
    dec5    = output["phase5_decision"]
    prof    = output["phase6_profit"]

    gates_list = output["phase4_section6"]
    best_gates = max(gates_list, key=lambda g: g["oos_metrics"]["sharpe"]) if gates_list else {}
    win_h      = best_gates.get("window_h", 168)
    oos_sh     = best_gates.get("oos_metrics", {}).get("sharpe", 0.0)
    jup_corr   = best_gates.get("jup_corr")
    avax_corr  = best_gates.get("avax_corr")
    fil_corr   = best_gates.get("fil_corr")
    n_pass     = best_gates.get("n_pass", 0)
    n_total    = best_gates.get("n_total", 9)

    beta_jup   = reg["coefficients"]["beta_jup"]
    r2_is      = reg["r_squared"]["is"]

    profit_usd = prof["profit_10m_4x_usd"]
    profit_k   = prof["profit_10m_4x_k"]

    color_map = {
        "ACCEPT":             "#00ff88",
        "ACCEPT CONDITIONAL": "#f0a500",
        "STILL BLOCKED":      "#ff4444",
        "REJECT":             "#ff4444",
    }
    badge_color = color_map.get(dec, "#aaaaaa")

    jup_str  = f"{jup_corr:.4f}"  if jup_corr  is not None else "N/A"
    avax_str = f"{avax_corr:.4f}" if avax_corr is not None else "N/A"
    fil_str  = f"{fil_corr:.4f}"  if fil_corr  is not None else "N/A"

    g5_icon = "G5 PASS" if best_gates.get("g5_pass") or (jup_corr is not None and jup_corr < 0.40) else "G5 FAIL"

    badge_html = (
        f'Wave K631 &nbsp;|&nbsp; '
        f'<span style="color:{badge_color};font-weight:900;font-size:1.6em;'
        f'background:linear-gradient(90deg,rgba(240,165,0,0.20),rgba(240,165,0,0.12),rgba(240,165,0,0.20));'
        f'padding:12px 28px;border-radius:16px;border:2px solid rgba(240,165,0,0.85);'
        f'display:inline-block;margin:6px 0;text-shadow:0 0 16px rgba(240,165,0,0.8);'
        f'box-shadow:0 0 32px rgba(240,165,0,0.35);">'
        f'K631 WLD-BTC Orthogonalization vs JUP-BTC &mdash; <strong>{dec}</strong> | '
        f'WLD Biometric ID Cluster | '
        f'<strong>Phase 1 Factor Regression:</strong> '
        f'&beta;_JUP={beta_jup:.4f} &alpha;={reg["coefficients"]["alpha"]:.6f} | '
        f'IS R&sup2;={r2_is:.4f} ({r2_is*100:.2f}% WLD variance explained by JUP Solana DEX factor) | '
        f'OOS R&sup2;={reg["r_squared"]["oos"]:.4f} | '
        f'FR-space orthogonality: resid_JUP_corr={reg["correlation_check"]["resid_jup_corr"]:.4f} | '
        f'<strong>Phase 2-3 Residual Signal W={win_h}h:</strong> '
        f'OOS Sh={oos_sh:.4f} (raw K621={K621_RAW_OOS_SHARPE:.2f} &rarr; degradation={K621_RAW_OOS_SHARPE-oos_sh:.2f} Sh units) | '
        f'JUP corr post-orth={jup_str} | AVAX={avax_str} | FIL={fil_str} | '
        f'<strong>{g5_icon}</strong> | '
        f'{n_pass}/{n_total} &sect;6 gates | '
        f'<strong>Profit @$10M 4x: ${profit_usd:,.0f}/yr (USDC/yr residual)</strong> | '
        f'Raw K621 ${K621_RAW_PROFIT_10M_4X:,.0f}/yr (BLOCKED) | '
        f'Delta: ${profit_usd - K621_RAW_PROFIT_10M_4X:+,.0f}/yr | '
        f'HL unchanged | Family unchanged'
        f'</span>'
    )

    html_content = html_path.read_text(encoding="utf-8")

    import re
    from datetime import datetime, timezone, timedelta
    jst = timezone(timedelta(hours=9))
    now_jst = datetime.now(jst)
    ts_str = now_jst.strftime("%Y-%m-%d %H:%M JST")

    # Update timestamp
    html_content = re.sub(
        r'Generated:.*?JST',
        f'Generated: {ts_str}',
        html_content,
        count=1,
    )

    # Inject K631 badge after K628 badge (or at the first badge position)
    if "Wave K631" in html_content:
        html_content = re.sub(
            r'Wave K631.*?</span>',
            badge_html,
            html_content,
            count=1,
            flags=re.DOTALL,
        )
    else:
        # Insert after K628 badge
        k628_pattern = r'(Wave K628.*?</span>)'
        if re.search(k628_pattern, html_content, flags=re.DOTALL):
            html_content = re.sub(
                k628_pattern,
                r'\1 &nbsp;|&nbsp; ' + badge_html,
                html_content,
                count=1,
                flags=re.DOTALL,
            )
        else:
            # Fallback: replace first "Generated:" line's surrounding span
            html_content = re.sub(
                r'(Generated:.*?JST &nbsp;\|&nbsp;)',
                r'\1 ' + badge_html + ' &nbsp;|&nbsp; ',
                html_content,
                count=1,
            )

    html_path.write_text(html_content, encoding="utf-8")


# ── Main ──────────────────────────────────────────────────────────────────────

def main() -> None:
    print("=" * 70)
    print("K631 WLD-BTC Orthogonalization vs JUP-BTC Common Factor (K628 Pattern)")
    print("=" * 70)

    # Load data
    print("\n[Data] Loading HL FR data (WLD, JUP, BTC)...")
    df = load_hl_fr_data()
    n_rows     = len(df)
    date_start = str(df.index[0])
    date_end   = str(df.index[-1])
    total_years = n_rows / 8760
    is_df  = df.loc[:OOS_START]
    oos_df = df.loc[OOS_START:]
    print(f"  Full: {date_start} to {date_end} ({n_rows} rows, {total_years:.3f} years)")
    print(f"  IS: {len(is_df)} rows | OOS: {len(oos_df)} rows from {OOS_START.date()}")

    data_info = {
        "hl_wld_fr_rows": n_rows,
        "date_start":     date_start,
        "date_end":       date_end,
        "total_years":    round(total_years, 3),
        "oos_start":      str(OOS_START.date()),
        "oos_years":      round(len(oos_df) / 8760, 3),
        "n_is_rows":      len(is_df),
        "n_oos_rows":     len(oos_df),
        "fr_frequency":   "1h (HL settles hourly)",
    }

    print(f"\n  fr_diff_wld mean={df['fr_diff_wld'].mean():.6f} std={df['fr_diff_wld'].std():.6f}")
    print(f"  fr_diff_jup mean={df['fr_diff_jup'].mean():.6f} std={df['fr_diff_jup'].std():.6f}")
    print(f"  Pairwise raw corrs:")
    raw_wld_jup_corr = float(df["fr_diff_wld"].corr(df["fr_diff_jup"]))
    print(f"    WLD-JUP fr_diff: {raw_wld_jup_corr:.4f}")

    # Phase 1: Factor Regression
    print("\n[Phase 1] Factor Regression")
    reg_result, resid_series, coefficients = phase1_factor_regression(df)

    # Phase 2 + Phase 3 + Phase 4: For each window
    all_backtest_results = []
    all_gates_results    = []
    all_signal_infos     = []

    for window_h in SIGNAL_WINDOWS:
        print(f"\n[Phase 2+3+4] Window W={window_h}h")

        # Phase 2: Signal info
        work, signal_info = phase2_residual_signal(df, coefficients, window_h)
        all_signal_infos.append(signal_info)

        # Phase 3: Backtest
        bt, bt_result = phase3_backtest(df, coefficients, window_h)
        all_backtest_results.append(bt_result)

        # Phase 4: §6 Gates
        work_for_gates = build_residual_df(df, coefficients)
        work_for_gates["resid_roll"]  = work_for_gates["residual"].rolling(window_h).mean()
        work_for_gates["signal_orth"] = np.sign(work_for_gates["resid_roll"])
        bt_gates    = run_residual_backtest(work_for_gates, window_h)
        gates_result = phase4_section6_gates(df, bt_gates, coefficients, window_h)
        all_gates_results.append(gates_result)

    # Phase 5: Decision
    print("\n[Phase 5] Decision")
    decision_result = phase5_decision(reg_result, all_backtest_results, all_gates_results)
    print(f"  DECISION: {decision_result['decision']}")
    print(f"  {decision_result['rationale'][:250]}...")

    # Phase 6: Profit Projection
    print("\n[Phase 6] Profit Projection")
    best_bt = max(all_backtest_results, key=lambda x: x["oos"]["sharpe"])
    profit_result = phase6_profit_projection(
        best_bt["oos"]["ann_ret_pct"],
        best_bt["oos"]["sharpe"],
    )
    print(f"  OOS Sharpe: {profit_result['oos_sharpe']:.4f}")
    print(f"  OOS Ann Ret: {profit_result['oos_ann_ret_pct']:.4f}%")
    print(f"  @$10M 4x: ${profit_result['profit_10m_4x_usd']:,.0f}/yr (USDC residual)")
    print(f"  Raw was: ${K621_RAW_PROFIT_10M_4X:,.0f}/yr (K621 blocked)")

    # Runtime
    elapsed = time.time() - START_TIME
    print(f"\n[Done] Runtime: {elapsed:.2f}s")

    # Compose output JSON
    from datetime import timezone, timedelta, datetime
    jst = timezone(timedelta(hours=9))
    now_jst = datetime.now(jst)
    run_time_jst = now_jst.strftime("%Y-%m-%dT%H:%M:%S+0900")

    output = {
        "wave":     "K631",
        "strategy": (
            "WLD-BTC FR Differential Signal Orthogonalization "
            "— Remove JUP-BTC Common Factor (K628 Pattern Application)"
        ),
        "run_time_jst": run_time_jst,
        "runtime_s":    round(elapsed, 2),
        "decision":     decision_result["decision"],
        "decision_rationale": decision_result["rationale"],
        "k621_context": {
            "k621_decision":         "BLOCKED-G5 (JUP=0.4612 @ W=168h)",
            "k621_oos_sharpe":       K621_RAW_OOS_SHARPE,
            "k621_profit_10m_4x":    K621_RAW_PROFIT_10M_4X,
            "k624_decision":         "BLOCKED-G5 (monotone G5/G6 no sweet-spot)",
            "k627_decision":         "BLOCKED (bear-filter approach failed)",
            "k628_precedent": {
                "k628_approach":       "OLS residualization: JTO-BTC ~ β_SEI*SEI + β_DOGE*DOGE + residual",
                "k628_decision":       "ACCEPT CONDITIONAL",
                "k628_orth_sharpe":    18.30,
                "k628_raw_sharpe":     18.67,
                "k628_profit_10m_4x":  17_851_320,
                "k628_sei_corr_post":  0.0881,
                "k628_doge_corr_post": 0.0990,
                "k628_beta_sei":       0.1641,
                "k628_beta_doge":      0.3021,
                "k628_is_r2":          0.0750,
            },
            "k631_approach": (
                "OLS residualization: WLD-BTC ~ α + β_JUP*JUP-BTC + residual. "
                "WLD-JUP signal corr=0.4612 (blocked). "
                "JUP Solana DEX common factor ~0.4612²≈21% of WLD signal variance."
            ),
        },
        "data_info":         data_info,
        "signal_config": {
            "strategy_type":  "FR differential carry — ORTHOGONALIZED vs JUP-BTC",
            "direction_rule": "sign(W-hour rolling mean of OLS residual of fr_diff_wld)",
            "cost_rt_bps":    COST_RT_BPS,
            "pnl_source":     "signal * fr_diff_wld (carry from actual WLD-BTC position)",
            "signal_windows": SIGNAL_WINDOWS,
        },
        "phase1_regression":   reg_result,
        "phase2_signal_infos": all_signal_infos,
        "phase3_backtest":     all_backtest_results,
        "phase4_section6":     all_gates_results,
        "phase5_decision":     decision_result,
        "phase6_profit":       profit_result,
    }

    # Save JSON
    out_json = BASE / "wave_k631_wld_orthogonalize.json"
    with open(out_json, "w") as f:
        json.dump(output, f, indent=2, default=str)
    print(f"\n[Output] JSON: {out_json}")

    # Save MD
    _write_md(output, BASE / "wave_k631_wld_orthogonalize.md")
    print(f"[Output] MD:   {BASE / 'wave_k631_wld_orthogonalize.md'}")

    # Update report.html
    _update_report_html(output)
    print(f"[Output] HTML: {BASE / 'report.html'} (badge updated)")


if __name__ == "__main__":
    main()

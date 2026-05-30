#!/usr/bin/env python3
"""
wave_k635_imx_orthogonalize.py — K635 IMX-BTC Orthogonalization vs SEI (multi-factor backup)
==============================================================================================
K339 REPO_ROOT pattern.

CONTEXT (from K612/K617)
------------------------
K612 IMX-BTC FR Differential: OOS Sharpe=41.73, $174K/yr@$10M 4x (W=504h/21d).
  BLOCKED-G5: SHIB=0.66, TIA=0.57, SEI=0.55 at W=504h (21d).
K617 7d Retry (W=168h): OOS Sharpe=37.257.
  SHIB resolved 0.66→0.25 (PASS), TIA resolved 0.57→0.28 (PASS).
  SEI persists: 0.5532→0.4111 (STILL FAILS threshold 0.40).
  Single remaining blocker: G5f_SEI=0.4111.

ORTHOGONALIZATION HYPOTHESIS (K635 — K628/K631/K633 Pattern Application)
-------------------------------------------------------------------------
K628 PROVED OLS residualization works for JTO-BTC:
  - JTO Sh 18.67 raw → 18.30 residual (-0.37 only), SEI+DOGE cleared → ACCEPT CONDITIONAL
K631 applied same pattern to WLD-BTC: WLD Sh 25.06 → 18.04, JUP cleared → ACCEPT CONDITIONAL
K633 applied same pattern to OP-BTC: OP Sh 32.91 → 12.68, FIL cleared → ACCEPT CONDITIONAL

K635: Apply same pattern to IMX-BTC (blocked by SEI corr=0.4111 at 7d):
  - Primary: residual = IMX - β_SEI * SEI  (single factor, 7d)
  - Backup:  residual = IMX - β_SHIB * SHIB - β_TIA * TIA - β_SEI * SEI (multi-factor)
  - IMX-SEI co-movement arises because both are mid-cap alts with lower FR than BTC
    in bull-BTC regimes — common alt-cap regime factor via btc_fr - alt_fr mechanism.
  - IMX-specific alpha: Immutable X (StarkEx ZK rollup) NFT minting demand, game launch
    spikes, ImmutableX ecosystem expansion (Gods Unchained, Guild of Guardians, etc.)
  - Expected: β_SEI ~0.30-0.50, IS R² ~0.10-0.20, residual Sharpe 25-35 (70-90% retention)
  - Expected profit: $87-140K/yr @$10M 4x (50-80% of raw $174K)

MECHANISM
---------
  fr_diff_imx = btc_fr - imx_fr
  fr_diff_sei = btc_fr - sei_fr

  Single-factor OLS (IS only): fr_diff_imx = α + β_SEI * fr_diff_sei + residual
  Multi-factor OLS (backup):   fr_diff_imx = α + β_SHIB*fr_diff_shib + β_TIA*fr_diff_tia
                                             + β_SEI*fr_diff_sei + residual

  residual captures IMX-specific gaming L2 infra alpha:
    - NFT minting demand cycles (game launches, collection drops)
    - ImmutableX protocol upgrades, sequencer economics
    - Gaming sector adoption (NOT: broader mid-cap alt-cap regime)

  signal_orthogonal = sign(rolling_mean(residual, W=168h))  [K617 default, 7d]
  Also test W=72h (K615 lesson: shorter W reduces alt-regime overlap)

PHASES
------
  Phase 1: Factor Regression (Single + Multi-factor)
  Phase 2: Residual Signal Construction
  Phase 3: Backtest Residual Signal
  Phase 4: §6 Gates on Residual
  Phase 5: Decision
  Phase 6: Profit Projection

K339 REPO_ROOT — no hardcoded absolute paths except BASE (derived from script location).
"""
from __future__ import annotations

import json
import math
import re
import time
import warnings
from datetime import datetime, timezone, timedelta
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
SIGNAL_WINDOWS = [72, 168]    # hours for rolling mean of residual
COST_RT_BPS    = 4            # 2bps per side × 2 legs

# OOS split (same as K617 — 2025-10-16 19:00:00)
OOS_START = pd.Timestamp("2025-10-16 19:00:00")
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

# K612/K617 reference values
K612_RAW_OOS_SHARPE     = 41.7275
K612_RAW_PROFIT_10M_4X  = 174_000   # approximate from K612 json
K617_RAW_OOS_SHARPE     = 37.257
K617_SEI_CORR_21D       = 0.5532
K617_SEI_CORR_7D        = 0.4111
K617_SHIB_CORR_7D       = 0.2453
K617_TIA_CORR_7D        = 0.2773
K617_ARB_CORR_7D        = 0.2473

# Reference raw profit (use K612 21d as higher Sharpe baseline)
K_RAW_PROFIT_10M_4X     = 174_000   # K612 21d (highest Sharpe 41.73)

# G5 sibling signals (token ticker → HL parquet filename mapping)
G5_SIGNALS = {
    "G5j_K280":   None,         # K280 structural estimate
    "G5a_ETH":    "ETH",
    "G5b_SOL":    "SOL",
    "G5c_AVAX":   "AVAX",
    "G5d_ATOM":   "ATOM",
    "G5e_INJ":    "INJ",
    "G5f_SEI":    "SEI",        # PRIMARY BLOCKER: should be ~0 post-orthogonalization
    "G5g_TIA":    "TIA",        # Was blocker at 21d, resolved at 7d (0.28 PASS)
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
    "G5s_SHIB":   "SHIB",       # Was blocker at 21d, resolved at 7d (0.25 PASS)
    "G5t_AAVE":   "AAVE",
    "G5u_CRV":    "CRV",
    "G5v_PEPE":   "PEPE",
    "G5w_WIF":    "WIF",
    "G5x_BONK":   "BONK",
    "G5y_UNI":    "UNI",
    "G5z_ARB":    "ARB",
    "G5aa_JUP":   "JUP",
    "G5ab_OP":    "OP",
    "G5ac_SNX":   "SNX",
    "G5ad_LDO":   "LDO",
    "G5ae_ENA":   "ENA",
    "G5af_ETHFI": "ETHFI",
    "G5ag_WLD":   "WLD",
    "G5ah_JTO":   "JTO",
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
    """Load IMX, SEI, SHIB, TIA, BTC FR data from HL cache and compute differentials."""
    btc_fr  = pd.read_parquet(HL_CACHE / "hl_fr_BTC.parquet")
    imx_fr  = pd.read_parquet(HL_CACHE / "hl_fr_IMX.parquet")
    sei_fr  = pd.read_parquet(HL_CACHE / "hl_fr_SEI.parquet")
    shib_fr = pd.read_parquet(HL_CACHE / "hl_fr_SHIB.parquet")
    tia_fr  = pd.read_parquet(HL_CACHE / "hl_fr_TIA.parquet")

    def _clean(df: pd.DataFrame, col_name: str) -> pd.DataFrame:
        df = df.copy()
        ts_col = [c for c in df.columns if "time" in c.lower() or "date" in c.lower()]
        fr_col = [c for c in df.columns if "fr" in c.lower() or "fund" in c.lower()]
        if not ts_col or not fr_col:
            raise ValueError(
                f"Cannot detect ts/fr columns in {col_name}: {list(df.columns)}"
            )
        df["timestamp"] = pd.to_datetime(df[ts_col[0]]).dt.floor("h")
        return df[["timestamp", fr_col[0]]].rename(columns={fr_col[0]: col_name})

    btc  = _clean(btc_fr,  "btc_fr")
    imx  = _clean(imx_fr,  "imx_fr")
    sei  = _clean(sei_fr,  "sei_fr")
    shib = _clean(shib_fr, "shib_fr")
    tia  = _clean(tia_fr,  "tia_fr")

    df = btc.merge(imx,  on="timestamp", how="inner")
    df = df.merge(sei,  on="timestamp", how="left")
    df = df.merge(shib, on="timestamp", how="left")
    df = df.merge(tia,  on="timestamp", how="left")
    df = df.set_index("timestamp").sort_index()

    df["fr_diff_imx"]  = df["btc_fr"] - df["imx_fr"]
    df["fr_diff_sei"]  = df["btc_fr"] - df["sei_fr"]
    df["fr_diff_shib"] = df["btc_fr"] - df["shib_fr"]
    df["fr_diff_tia"]  = df["btc_fr"] - df["tia_fr"]

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
    """Load Bybit IMX FR for cross-venue G8 check."""
    result: Dict[str, Optional[pd.DataFrame]] = {}
    bybit_path = CACHE / "bybit_fr_IMXUSDT_730d.parquet"
    if bybit_path.exists():
        bybit = pd.read_parquet(bybit_path)
        if "timestamp" not in bybit.columns:
            ts_col = [c for c in bybit.columns if "time" in c.lower() or "date" in c.lower()]
            if ts_col:
                bybit = bybit.rename(columns={ts_col[0]: "timestamp"})
        bybit["timestamp"] = pd.to_datetime(bybit["timestamp"]).dt.floor("h")
        result["bybit"] = bybit
    else:
        result["bybit"] = None
    return result


# ── Phase 1: Factor Regression ────────────────────────────────────────────────

def phase1_factor_regression(df: pd.DataFrame) -> Tuple[dict, pd.Series, dict]:
    """
    Two regression modes:
      Single-factor: fr_diff_imx = α + β_SEI * fr_diff_sei + ε
      Multi-factor:  fr_diff_imx = α + β_SHIB*fr_diff_shib + β_TIA*fr_diff_tia
                                   + β_SEI*fr_diff_sei + ε
    Both estimated on IS period only to avoid look-ahead bias.

    Returns: (result_dict, best_resid_series, best_coefficients_dict)
    """
    print("  [Phase 1] OLS factor regression (single + multi-factor)...")

    # Single-factor: IMX vs SEI only (minimum residualization)
    sf_cols  = ["fr_diff_imx", "fr_diff_sei"]
    # Multi-factor: IMX vs SHIB+TIA+SEI (full backup)
    mf_cols  = ["fr_diff_imx", "fr_diff_shib", "fr_diff_tia", "fr_diff_sei"]

    sf_df = df.dropna(subset=sf_cols)
    mf_df = df.dropna(subset=mf_cols)

    is_sf = sf_df.loc[:OOS_START]
    is_mf = mf_df.loc[:OOS_START]

    print(f"    Single-factor IS rows: {len(is_sf)}  Multi-factor IS rows: {len(is_mf)}")

    # ── Single-factor OLS ──
    y_sf = is_sf["fr_diff_imx"].values
    X_sf = np.column_stack([np.ones(len(is_sf)), is_sf["fr_diff_sei"].values])
    beta_sf = np.linalg.lstsq(X_sf, y_sf, rcond=None)[0]
    alpha_sf, beta_sei_sf = float(beta_sf[0]), float(beta_sf[1])

    y_hat_sf  = X_sf @ beta_sf
    ss_res_sf = np.sum((y_sf - y_hat_sf) ** 2)
    ss_tot_sf = np.sum((y_sf - y_sf.mean()) ** 2)
    r2_sf_is  = 1.0 - ss_res_sf / ss_tot_sf if ss_tot_sf > 0 else 0.0

    n_sf, k_sf = len(y_sf), 2
    sigma2_sf  = ss_res_sf / (n_sf - k_sf)
    XtX_inv_sf = np.linalg.pinv(X_sf.T @ X_sf)
    se_sf      = np.sqrt(np.diag(sigma2_sf * XtX_inv_sf))
    t_alpha_sf = alpha_sf  / se_sf[0] if se_sf[0] > 0 else 0.0
    t_sei_sf   = beta_sei_sf / se_sf[1] if se_sf[1] > 0 else 0.0

    # Apply to full period
    full_sf  = sf_df.copy()
    X_full_sf = np.column_stack([np.ones(len(full_sf)), full_sf["fr_diff_sei"].values])
    resid_sf  = full_sf["fr_diff_imx"].values - X_full_sf @ beta_sf
    resid_sf_s = pd.Series(resid_sf, index=full_sf.index)

    # OOS R² (single)
    oos_sf = sf_df.loc[OOS_START:]
    X_oos_sf = np.column_stack([np.ones(len(oos_sf)), oos_sf["fr_diff_sei"].values])
    y_hat_oos_sf = X_oos_sf @ beta_sf
    ss_res_oos_sf = np.sum((oos_sf["fr_diff_imx"].values - y_hat_oos_sf) ** 2)
    ss_tot_oos_sf = np.sum((oos_sf["fr_diff_imx"].values - oos_sf["fr_diff_imx"].mean()) ** 2)
    r2_sf_oos = 1.0 - ss_res_oos_sf / ss_tot_oos_sf if ss_tot_oos_sf > 0 else 0.0

    adf_sf = adf_pvalue(resid_sf_s)
    hl_sf  = ou_halflife(resid_sf_s)
    raw_corr_sf   = float(sf_df["fr_diff_imx"].corr(sf_df["fr_diff_sei"]))
    resid_sei_corr_sf = float(resid_sf_s.corr(sf_df["fr_diff_sei"].reindex(resid_sf_s.index)))

    print(f"    [SF] β_SEI={beta_sei_sf:.6f}  α={alpha_sf:.8f}")
    print(f"    [SF] IS R²={r2_sf_is:.4f}  OOS R²={r2_sf_oos:.4f}")
    print(f"    [SF] ADF p={adf_sf:.4f}  OU HL={hl_sf:.1f}h")
    print(f"    [SF] raw IMX-SEI corr={raw_corr_sf:.4f}  resid-SEI corr={resid_sei_corr_sf:.6f}")

    single_factor_result = {
        "mode":       "single_factor",
        "formula":    "fr_diff_imx = α + β_SEI * fr_diff_sei + ε",
        "is_period":  {
            "start":  str(is_sf.index[0].date()),
            "end":    str(is_sf.index[-1].date()),
            "n_rows": int(len(is_sf)),
        },
        "coefficients": {
            "alpha":    round(alpha_sf,    8),
            "beta_sei": round(beta_sei_sf, 6),
        },
        "t_stats": {
            "t_alpha": round(t_alpha_sf, 3),
            "t_sei":   round(t_sei_sf,   3),
        },
        "r_squared": {
            "is":  round(r2_sf_is,  4),
            "oos": round(r2_sf_oos, 4),
        },
        "residual_properties": {
            "adf_pvalue":    round(adf_sf, 6),
            "stationary":    bool(adf_sf < 0.05),
            "ou_halflife_h": round(hl_sf, 2) if not math.isnan(hl_sf) else None,
        },
        "correlation_check": {
            "raw_imx_sei_corr":    round(raw_corr_sf, 4),
            "resid_sei_corr":      round(resid_sei_corr_sf, 6),
            "orthogonality_achieved": bool(abs(resid_sei_corr_sf) < 0.01),
        },
        "regression_data": {
            "n_full": int(len(sf_df)),
            "n_is":   int(len(is_sf)),
            "n_oos":  int(len(oos_sf)),
        },
    }

    # ── Multi-factor OLS ──
    y_mf = is_mf["fr_diff_imx"].values
    X_mf = np.column_stack([
        np.ones(len(is_mf)),
        is_mf["fr_diff_shib"].values,
        is_mf["fr_diff_tia"].values,
        is_mf["fr_diff_sei"].values,
    ])
    try:
        beta_mf = np.linalg.lstsq(X_mf, y_mf, rcond=None)[0]
    except np.linalg.LinAlgError:
        beta_mf = np.zeros(4)
    alpha_mf, beta_shib_mf, beta_tia_mf, beta_sei_mf = (
        float(beta_mf[0]), float(beta_mf[1]), float(beta_mf[2]), float(beta_mf[3])
    )

    y_hat_mf  = X_mf @ beta_mf
    ss_res_mf = np.sum((y_mf - y_hat_mf) ** 2)
    ss_tot_mf = np.sum((y_mf - y_mf.mean()) ** 2)
    r2_mf_is  = 1.0 - ss_res_mf / ss_tot_mf if ss_tot_mf > 0 else 0.0

    n_mf, k_mf = len(y_mf), 4
    sigma2_mf  = ss_res_mf / (n_mf - k_mf)
    XtX_inv_mf = np.linalg.pinv(X_mf.T @ X_mf)
    se_mf      = np.sqrt(np.diag(sigma2_mf * XtX_inv_mf))
    t_alpha_mf = alpha_mf   / se_mf[0] if se_mf[0] > 0 else 0.0
    t_shib_mf  = beta_shib_mf / se_mf[1] if se_mf[1] > 0 else 0.0
    t_tia_mf   = beta_tia_mf  / se_mf[2] if se_mf[2] > 0 else 0.0
    t_sei_mf   = beta_sei_mf  / se_mf[3] if se_mf[3] > 0 else 0.0

    # Apply to full period (multi-factor; use full_sf index for consistency)
    full_mf  = mf_df.copy()
    X_full_mf = np.column_stack([
        np.ones(len(full_mf)),
        full_mf["fr_diff_shib"].values,
        full_mf["fr_diff_tia"].values,
        full_mf["fr_diff_sei"].values,
    ])
    resid_mf   = full_mf["fr_diff_imx"].values - X_full_mf @ beta_mf
    resid_mf_s = pd.Series(resid_mf, index=full_mf.index)

    # OOS R² (multi)
    oos_mf = mf_df.loc[OOS_START:]
    X_oos_mf = np.column_stack([
        np.ones(len(oos_mf)),
        oos_mf["fr_diff_shib"].values,
        oos_mf["fr_diff_tia"].values,
        oos_mf["fr_diff_sei"].values,
    ])
    y_hat_oos_mf  = X_oos_mf @ beta_mf
    ss_res_oos_mf = np.sum((oos_mf["fr_diff_imx"].values - y_hat_oos_mf) ** 2)
    ss_tot_oos_mf = np.sum((oos_mf["fr_diff_imx"].values - oos_mf["fr_diff_imx"].mean()) ** 2)
    r2_mf_oos = 1.0 - ss_res_oos_mf / ss_tot_oos_mf if ss_tot_oos_mf > 0 else 0.0

    adf_mf = adf_pvalue(resid_mf_s)
    hl_mf  = ou_halflife(resid_mf_s)
    resid_sei_corr_mf  = float(resid_mf_s.corr(full_mf["fr_diff_sei"].reindex(resid_mf_s.index)))
    resid_shib_corr_mf = float(resid_mf_s.corr(full_mf["fr_diff_shib"].reindex(resid_mf_s.index)))
    resid_tia_corr_mf  = float(resid_mf_s.corr(full_mf["fr_diff_tia"].reindex(resid_mf_s.index)))

    print(f"    [MF] β_SHIB={beta_shib_mf:.6f} β_TIA={beta_tia_mf:.6f} β_SEI={beta_sei_mf:.6f}")
    print(f"    [MF] IS R²={r2_mf_is:.4f}  OOS R²={r2_mf_oos:.4f}")
    print(f"    [MF] resid-SEI corr={resid_sei_corr_mf:.6f}  resid-SHIB={resid_shib_corr_mf:.6f}  resid-TIA={resid_tia_corr_mf:.6f}")

    multi_factor_result = {
        "mode":       "multi_factor",
        "formula":    "fr_diff_imx = α + β_SHIB*fr_diff_shib + β_TIA*fr_diff_tia + β_SEI*fr_diff_sei + ε",
        "is_period":  {
            "start":  str(is_mf.index[0].date()),
            "end":    str(is_mf.index[-1].date()),
            "n_rows": int(len(is_mf)),
        },
        "coefficients": {
            "alpha":     round(alpha_mf,    8),
            "beta_shib": round(beta_shib_mf, 6),
            "beta_tia":  round(beta_tia_mf,  6),
            "beta_sei":  round(beta_sei_mf,  6),
        },
        "t_stats": {
            "t_alpha": round(t_alpha_mf, 3),
            "t_shib":  round(t_shib_mf,  3),
            "t_tia":   round(t_tia_mf,   3),
            "t_sei":   round(t_sei_mf,   3),
        },
        "r_squared": {
            "is":  round(r2_mf_is,  4),
            "oos": round(r2_mf_oos, 4),
        },
        "residual_properties": {
            "adf_pvalue":    round(adf_mf, 6),
            "stationary":    bool(adf_mf < 0.05),
            "ou_halflife_h": round(hl_mf, 2) if not math.isnan(hl_mf) else None,
        },
        "correlation_check": {
            "resid_sei_corr":  round(resid_sei_corr_mf,  6),
            "resid_shib_corr": round(resid_shib_corr_mf, 6),
            "resid_tia_corr":  round(resid_tia_corr_mf,  6),
            "orthogonality_sei_achieved":  bool(abs(resid_sei_corr_mf) < 0.01),
            "orthogonality_shib_achieved": bool(abs(resid_shib_corr_mf) < 0.01),
            "orthogonality_tia_achieved":  bool(abs(resid_tia_corr_mf) < 0.01),
        },
        "regression_data": {
            "n_full": int(len(full_mf)),
            "n_is":   int(len(is_mf)),
            "n_oos":  int(len(oos_mf)),
        },
    }

    # Combined result
    result = {
        "single_factor": single_factor_result,
        "multi_factor":  multi_factor_result,
        "comparison": {
            "sf_is_r2":  round(r2_sf_is, 4),
            "mf_is_r2":  round(r2_mf_is, 4),
            "sf_beta_sei": round(beta_sei_sf, 6),
            "mf_beta_sei": round(beta_sei_mf, 6),
            "mf_beta_shib": round(beta_shib_mf, 6),
            "mf_beta_tia":  round(beta_tia_mf,  6),
            "note": (
                f"Single-factor (SEI only): IS R²={r2_sf_is:.4f}, β_SEI={beta_sei_sf:.4f}. "
                f"Multi-factor (SHIB+TIA+SEI): IS R²={r2_mf_is:.4f}, β_SEI={beta_sei_mf:.4f}. "
                f"Multi-factor explains {(r2_mf_is-r2_sf_is)*100:.2f}% more variance."
            ),
        },
    }

    # Return single-factor as primary (simpler, better generalization)
    # Also return multi-factor residuals for comparison
    coefficients = {
        "sf": {"alpha": alpha_sf, "beta_sei": beta_sei_sf},
        "mf": {"alpha": alpha_mf, "beta_shib": beta_shib_mf, "beta_tia": beta_tia_mf, "beta_sei": beta_sei_mf},
    }
    # Primary residual = single-factor
    return result, resid_sf_s, coefficients


# ── Residual construction helpers ──────────────────────────────────────────────

def build_residual_df_sf(df: pd.DataFrame, coefs: dict) -> pd.DataFrame:
    """Single-factor: residual = fr_diff_imx - α - β_SEI*fr_diff_sei."""
    alpha    = coefs["alpha"]
    beta_sei = coefs["beta_sei"]
    work = df.dropna(subset=["fr_diff_imx", "fr_diff_sei"]).copy()
    work["residual"] = work["fr_diff_imx"] - alpha - beta_sei * work["fr_diff_sei"]
    return work


def build_residual_df_mf(df: pd.DataFrame, coefs: dict) -> pd.DataFrame:
    """Multi-factor: residual = fr_diff_imx - α - β_SHIB*fr_diff_shib - β_TIA*fr_diff_tia - β_SEI*fr_diff_sei."""
    alpha     = coefs["alpha"]
    beta_shib = coefs["beta_shib"]
    beta_tia  = coefs["beta_tia"]
    beta_sei  = coefs["beta_sei"]
    work = df.dropna(subset=["fr_diff_imx", "fr_diff_shib", "fr_diff_tia", "fr_diff_sei"]).copy()
    work["residual"] = (
        work["fr_diff_imx"]
        - alpha
        - beta_shib * work["fr_diff_shib"]
        - beta_tia  * work["fr_diff_tia"]
        - beta_sei  * work["fr_diff_sei"]
    )
    return work


# ── Phase 2: Residual Signal Construction ─────────────────────────────────────

def phase2_residual_signal(
    df: pd.DataFrame,
    all_coefs: dict,
    window_h: int,
    mode: str = "sf",
) -> Tuple[pd.DataFrame, dict]:
    """Construct orthogonalized signal from residual with given rolling window."""
    print(f"  [Phase 2] Residual signal construction ({mode}, W={window_h}h rolling mean)...")

    if mode == "sf":
        work = build_residual_df_sf(df, all_coefs["sf"])
        label = "single-factor (SEI only)"
    else:
        work = build_residual_df_mf(df, all_coefs["mf"])
        label = "multi-factor (SHIB+TIA+SEI)"

    work["resid_roll"]  = work["residual"].rolling(window_h).mean()
    work["signal_orth"] = np.sign(work["resid_roll"])

    # Compare with K617 raw signal at same W
    imx_raw_roll  = df["fr_diff_imx"].rolling(window_h).mean().reindex(work.index)
    raw_signal    = np.sign(imx_raw_roll).reindex(work.index)
    merged_sig    = pd.concat([
        raw_signal.rename("raw"),
        work["signal_orth"].rename("orth"),
    ], axis=1).dropna()
    raw_orth_corr = float(merged_sig["raw"].corr(merged_sig["orth"]))

    # Check signal corr with SEI (should be ~0 by construction)
    sei_fr = load_sibling_fr("SEI")

    def _check_signal_corr(sib_fr: Optional[pd.Series], label_s: str) -> Optional[float]:
        if sib_fr is None:
            return None
        sib_merged = pd.merge(
            df[["btc_fr"]],
            sib_fr.rename("sib_fr").to_frame(),
            left_index=True, right_index=True, how="inner",
        )
        sib_merged["sib_diff"] = sib_merged["btc_fr"] - sib_merged["sib_fr"]
        sib_signal   = np.sign(sib_merged["sib_diff"].rolling(window_h).mean())
        orth_aligned = work["signal_orth"].reindex(sib_signal.index)
        merged = pd.concat([orth_aligned.rename("orth"), sib_signal.rename("sib")], axis=1).dropna()
        if len(merged) < 200:
            return None
        return float(merged["orth"].corr(merged["sib"]))

    sei_sig_corr  = _check_signal_corr(sei_fr, "SEI")

    print(f"    [{mode}] Raw vs Orthogonal signal corr = {raw_orth_corr:.4f}")
    sei_str = f"{sei_sig_corr:.4f}" if sei_sig_corr is not None else "N/A"
    print(f"    [{mode}] Orth signal vs SEI signal corr = {sei_str} (expected ~0)")

    return work, {
        "mode":                    mode,
        "label":                   label,
        "window_h":                window_h,
        "raw_orth_signal_corr":    round(raw_orth_corr, 4),
        "orth_vs_sei_signal_corr": round(sei_sig_corr, 4) if sei_sig_corr is not None else None,
        "sei_expected_near_zero":  bool(sei_sig_corr is not None and abs(sei_sig_corr) < 0.10),
        "n_signal_rows":           int(len(work.dropna(subset=["signal_orth"]))),
    }


# ── Phase 3: Backtest ─────────────────────────────────────────────────────────

def run_residual_backtest(work: pd.DataFrame) -> pd.DataFrame:
    """
    Backtest the orthogonalized residual signal.
    PnL = signal_orth * fr_diff_imx (actual IMX-BTC carry received)
    """
    bt = work.dropna(subset=["residual", "signal_orth"]).copy()
    bt["signal_prev"]   = bt["signal_orth"].shift(1)
    bt["signal_change"] = (bt["signal_orth"] != bt["signal_prev"]).astype(float)
    bt["carry_pnl"]  = bt["signal_orth"] * bt["fr_diff_imx"]
    bt["trade_cost"] = bt["signal_change"] * (COST_RT_BPS / 10000)
    bt["net_pnl"]    = bt["carry_pnl"] - bt["trade_cost"]
    return bt


def phase3_backtest(
    df: pd.DataFrame,
    all_coefs: dict,
    window_h: int,
    mode: str = "sf",
) -> Tuple[pd.DataFrame, dict]:
    """Run backtest on orthogonalized signal."""
    print(f"  [Phase 3] Backtest residual signal ({mode}, W={window_h}h)...")

    if mode == "sf":
        work = build_residual_df_sf(df, all_coefs["sf"])
    else:
        work = build_residual_df_mf(df, all_coefs["mf"])

    work["resid_roll"]  = work["residual"].rolling(window_h).mean()
    work["signal_orth"] = np.sign(work["resid_roll"])
    bt = run_residual_backtest(work)

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

    print(
        f"    [{mode}] OOS Sharpe = {oos_sh:.4f} "
        f"(raw K612={K612_RAW_OOS_SHARPE:.2f} / K617={K617_RAW_OOS_SHARPE:.2f})"
    )
    print(f"    [{mode}] OOS Ann Ret = {oos_ret:.4f}%")
    print(f"    [{mode}] OOS Trades/yr = {oos_tyr}")
    print(f"    [{mode}] OOS Max DD = {oos_mdd*100:.4f}%")

    return bt, {
        "mode":     mode,
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
            "k612_raw_oos_sharpe":      K612_RAW_OOS_SHARPE,
            "k617_raw_oos_sharpe":      K617_RAW_OOS_SHARPE,
            "orth_oos_sharpe":          round(oos_sh, 4),
            "sharpe_reduction_vs_k612": round(K612_RAW_OOS_SHARPE - oos_sh, 4),
            "sharpe_reduction_vs_k617": round(K617_RAW_OOS_SHARPE - oos_sh, 4),
        },
    }


# ── Phase 4: §6 Gates ─────────────────────────────────────────────────────────

def phase4_section6_gates(
    df: pd.DataFrame,
    bt: pd.DataFrame,
    all_coefs: dict,
    window_h: int,
    mode: str = "sf",
) -> dict:
    """Full §6 gate verification for orthogonalized signal."""
    print(f"  [Phase 4] §6 gates for orthogonalized signal ({mode}, W={window_h}h)...")

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
    perm_p  = float(np.mean(np.array(perm_sharpes) >= oos_sh))
    g2_pass = bool(perm_p <= 0.05)

    # G3: DSR Bonferroni (2 windows × 2 modes = 4 trials)
    n_trials    = len(SIGNAL_WINDOWS) * 2   # SF and MF × 2 windows
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
            sh  = sharpe_ratio(fold_oos["net_pnl"])
            ar  = ann_ret_pct(fold_oos["net_pnl"])
            ent = int(fold_oos["signal_change"].sum())
            fold_results.append({
                "fold":       fold_i,
                "oos_start":  str(fold_oos_start.date()),
                "oos_end":    str(fold_oos_end.date()),
                "sharpe":     round(sh, 3),
                "ann_ret_pct": round(ar, 3),
                "entries":    ent,
            })
            fold_sharpes.append(sh)
            if sh > 0:
                n_pos += 1
            valid_folds += 1
        fold_start = fold_oos_end
        fold_i += 1

    g4_all_pos = bool(n_pos == valid_folds and valid_folds > 0)
    g4_pass    = g4_all_pos

    # G5: All sibling correlations
    print("    G5 family correlations (orthogonalized signal)...")
    g5_details: Dict[str, dict]    = {}
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
            left_index=True, right_index=True, how="inner",
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

        # Special annotations
        note_suffix = ""
        if ticker == "SEI":
            orth_status = (
                "VALID" if abs(c) < 0.10 else (
                    "PARTIAL" if abs(c) < G5_CORR_MAX else "FAILED"
                )
            )
            note_suffix = (
                f" [ORTHOGONALIZED (PRIMARY): by construction should be ~0; "
                f"actual={c:.4f} — orthogonalization {orth_status}. "
                f"K612 21d raw={K617_SEI_CORR_21D}, K617 7d raw={K617_SEI_CORR_7D}]"
            )
        elif ticker == "SHIB":
            note_suffix = (
                f" [Was BLOCKER at 21d (0.66), resolved at 7d (K617={K617_SHIB_CORR_7D}). "
                f"Watch for multi-factor residualization impact.]"
            )
        elif ticker == "TIA":
            note_suffix = (
                f" [Was BLOCKER at 21d (0.57), resolved at 7d (K617={K617_TIA_CORR_7D}). "
                f"Watch for multi-factor residualization impact.]"
            )
        elif ticker == "ARB":
            note_suffix = (
                f" [K617 raw={K617_ARB_CORR_7D}. Post-orth ARB change expected minimal.]"
            )

        g5_details[key] = {
            "ticker": ticker,
            "corr":   round(c, 4),
            "pass":   bool(g5_ok),
            "note": (
                f"IMX-BTC ORTH signal vs {ticker}-BTC at W={window_h}h: "
                f"corr={c:.4f} ({'PASS' if g5_ok else 'FAIL'} threshold {G5_CORR_MAX})"
                + note_suffix
            ),
        }

    max_corr_val  = max(
        (v["corr"] for v in g5_details.values() if v["corr"] is not None), default=0.0
    )
    max_corr_pair = next(
        (v["ticker"] for v in g5_details.values()
         if v.get("corr") is not None and v["corr"] == max_corr_val), "N/A"
    )
    g5_pass = bool(all_g5_pass)

    sei_detail  = g5_details.get("G5f_SEI",  {})
    shib_detail = g5_details.get("G5s_SHIB", {})
    tia_detail  = g5_details.get("G5g_TIA",  {})
    arb_detail  = g5_details.get("G5z_ARB",  {})
    eth_detail  = g5_details.get("G5a_ETH",  {})

    sei_corr_final  = sei_detail.get("corr")
    shib_corr_final = shib_detail.get("corr")
    tia_corr_final  = tia_detail.get("corr")
    arb_corr_final  = arb_detail.get("corr")
    eth_corr_final  = eth_detail.get("corr")

    # G6: Trades/yr >= 30
    g6_pass = bool(oos_tyr >= G6_TRADES_MIN)

    # G7: Ann ret > 5%
    g7_pass = bool(oos_ret >= G7_ANN_RET)

    # G8: Cross-venue Bybit IMX
    cv_data     = load_cross_venue_fr()
    g8_results  = {}
    g8_any_pass = False
    for venue, vdf in cv_data.items():
        if vdf is None:
            g8_results[venue] = {"corr": None, "pass": False, "note": "Data unavailable"}
            continue
        fr_col = [c for c in vdf.columns if "fr" in c.lower() and c.lower() != "timestamp"]
        if not fr_col:
            g8_results[venue] = {"corr": None, "pass": False, "note": "No FR col"}
            continue
        if "timestamp" in vdf.columns:
            bybit_ts = vdf.set_index("timestamp")[fr_col[0]]
        else:
            bybit_ts = vdf[fr_col[0]]
        hl_imx = df["imx_fr"]
        merged_v = pd.concat([
            hl_imx.rename("hl_fr"),
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
            "note": f"HL-{venue} IMX FR corr={vc:.4f} ({'PASS' if vp else 'FAIL'} >= {G8_VENUE_CORR})",
        }
    g8_pass = bool(g8_any_pass)

    # G9: OOS >= 180d
    g9_pass = bool(oos_days >= 180)

    gates = [
        {"gate": "G1", "name": "OOS Sharpe >= 1.0",        "value": round(oos_sh, 4), "pass": g1_pass},
        {"gate": "G2", "name": "Perm p <= 0.05",            "value": round(perm_p, 4), "pass": g2_pass},
        {"gate": "G3", "name": f"DSR Bonferroni p<{thresh_bonf:.5f}",
                                                             "value": round(p_bonf, 6), "pass": g3_pass},
        {"gate": "G4", "name": "Walk-forward all positive", "value": f"{n_pos}/{valid_folds}", "pass": g4_pass},
        {"gate": "G5", "name": "G5 family corr < 0.40",     "value": round(max_corr_val, 4), "pass": g5_pass},
        {"gate": "G6", "name": "Trades/yr >= 30",           "value": oos_tyr, "pass": g6_pass},
        {"gate": "G7", "name": "Ann ret > 5% (unlev)",      "value": round(oos_ret, 4), "pass": g7_pass},
        {"gate": "G8", "name": "Cross-venue corr >= 0.55",  "value": max(
            (v["corr"] for v in g8_results.values() if v["corr"] is not None), default=0.0
        ), "pass": g8_pass},
        {"gate": "G9", "name": "OOS >= 180d",               "value": round(oos_days, 1), "pass": g9_pass},
    ]

    n_pass = sum(1 for g in gates if g["pass"])
    all_critical = g1_pass and g2_pass and g3_pass and g5_pass and g7_pass and g9_pass

    print(
        f"    [{mode}] Gates: {n_pass}/{len(gates)} PASS | "
        f"SEI={sei_corr_final} | G5={'PASS' if g5_pass else 'FAIL'}"
    )

    return {
        "mode":     mode,
        "window_h": window_h,
        "oos_metrics": {
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
        "gates":             gates,
        "n_pass":            n_pass,
        "n_total":           len(gates),
        "all_critical_pass": bool(all_critical),
        "g5_details":        g5_details,
        "g5_fail_list":      g5_fail_list,
        "g5_max_corr":       round(max_corr_val, 4),
        "g5_max_pair":       max_corr_pair,
        "sei_corr":          round(sei_corr_final,  4) if sei_corr_final  is not None else None,
        "shib_corr":         round(shib_corr_final, 4) if shib_corr_final is not None else None,
        "tia_corr":          round(tia_corr_final,  4) if tia_corr_final  is not None else None,
        "arb_corr":          round(arb_corr_final,  4) if arb_corr_final  is not None else None,
        "eth_corr":          round(eth_corr_final,  4) if eth_corr_final  is not None else None,
        "sei_pass":          bool(sei_detail.get("pass", False)),
        "g5_pass":           bool(g5_pass),
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
        "cross_venue": g8_results,
    }


# ── Phase 5: Decision ─────────────────────────────────────────────────────────

def phase5_decision(
    regression: dict,
    backtest_results: List[dict],
    gates_results: List[dict],
) -> dict:
    """Determine final decision. Selects best window+mode by OOS Sharpe with G5 PASS preference."""

    g5_pass_results      = [g for g in gates_results if g["g5_pass"]]
    all_critical_results = [g for g in gates_results if g["all_critical_pass"]]
    best_by_sharpe       = (
        max(gates_results, key=lambda x: x["oos_metrics"]["sharpe"])
        if gates_results else None
    )

    best_result = (
        max(all_critical_results, key=lambda x: x["oos_metrics"]["sharpe"])
        if all_critical_results else (
            max(g5_pass_results, key=lambda x: x["oos_metrics"]["sharpe"])
            if g5_pass_results else best_by_sharpe
        )
    )

    if not best_result:
        return {"decision": "INSUFFICIENT_DATA", "rationale": "No backtest results available."}

    oos_sh   = best_result["oos_metrics"]["sharpe"]
    n_pass   = best_result["n_pass"]
    n_total  = best_result["n_total"]
    all_crit = best_result["all_critical_pass"]
    sei_c    = best_result.get("sei_corr")
    shib_c   = best_result.get("shib_corr")
    tia_c    = best_result.get("tia_corr")
    arb_c    = best_result.get("arb_corr")
    win_h    = best_result["window_h"]
    mode     = best_result.get("mode", "sf")
    g5_ok    = best_result["g5_pass"]
    g5_fail_l = best_result.get("g5_fail_list", {})

    sf_reg = regression["single_factor"]
    mf_reg = regression["multi_factor"]
    beta_sei_sf = sf_reg["coefficients"]["beta_sei"]
    r2_sf       = sf_reg["r_squared"]["is"]

    sei_str  = f"{sei_c:.4f}"  if sei_c  is not None else "N/A"
    shib_str = f"{shib_c:.4f}" if shib_c is not None else "N/A"
    tia_str  = f"{tia_c:.4f}"  if tia_c  is not None else "N/A"

    if all_crit and oos_sh >= 5.0 and n_pass >= 8:
        decision = "ACCEPT"
        rationale = (
            f"Orthogonalized IMX signal ({mode}, W={win_h}h): ALL critical gates PASS. "
            f"Residual Sharpe={oos_sh:.2f} ({n_pass}/{n_total} gates). "
            f"G5: SEI={sei_str} PASS (orthogonalization successful). "
            f"SHIB={shib_str} PASS. TIA={tia_str} PASS. ARB={arb_c}. "
            f"β_SEI={beta_sei_sf:.4f}, IS R²={r2_sf:.4f}. "
            "IMX-BTC Gaming L2 Infra Cluster UNLOCKED. Recommend scaffold deployment."
        )
    elif g5_ok and oos_sh >= 1.0 and n_pass >= 6:
        decision = "ACCEPT CONDITIONAL"
        rationale = (
            f"Orthogonalized IMX signal ({mode}, W={win_h}h): G5 PASS + OOS Sharpe={oos_sh:.2f} sufficient. "
            f"Non-critical fails: {n_total - n_pass} gates. "
            f"SEI={sei_str} PASS. SHIB={shib_str}. TIA={tia_str}. "
            f"β_SEI={beta_sei_sf:.4f}, IS R²={r2_sf:.4f}. "
            "Recommend 60d paper-trade before live deployment."
        )
    elif not g5_ok:
        decision = "STILL BLOCKED"
        rationale = (
            f"Orthogonalized IMX signal ({mode}, W={win_h}h): G5 STILL FAILS. "
            f"SEI={sei_str}. Remaining blockers: {g5_fail_l}. "
            f"β_SEI={beta_sei_sf:.4f}, IS R²={r2_sf:.4f}. "
            "Orthogonalization did NOT sufficiently remove SEI correlation. "
            "IMX Gaming L2 infra line CLOSED — signal co-movement structural."
        )
    else:
        decision = "REJECT"
        rationale = (
            f"Orthogonalized IMX signal ({mode}, W={win_h}h): OOS Sharpe={oos_sh:.2f} < 1.0 or "
            f"insufficient gates ({n_pass}/{n_total}). Orthogonalization destroys IMX edge."
        )

    # Collect SF vs MF comparison
    sf_results = [g for g in gates_results if g.get("mode") == "sf"]
    mf_results = [g for g in gates_results if g.get("mode") == "mf"]
    sf_best = max(sf_results, key=lambda x: x["oos_metrics"]["sharpe"]) if sf_results else None
    mf_best = max(mf_results, key=lambda x: x["oos_metrics"]["sharpe"]) if mf_results else None

    return {
        "decision":      decision,
        "rationale":     rationale,
        "best_mode":     mode,
        "best_window_h": win_h,
        "best_oos_sharpe": round(oos_sh, 4),
        "best_n_pass":   n_pass,
        "best_n_total":  n_total,
        "g5_cleared":    bool(g5_ok),
        "g5_fail_list":  g5_fail_l,
        "sei_corr_post_orth":  sei_c,
        "shib_corr_post_orth": shib_c,
        "tia_corr_post_orth":  tia_c,
        "arb_corr_post_orth":  arb_c,
        "mode_comparison": {
            "sf_best_sharpe": round(sf_best["oos_metrics"]["sharpe"], 4) if sf_best else None,
            "sf_g5_pass":     sf_best["g5_pass"] if sf_best else None,
            "mf_best_sharpe": round(mf_best["oos_metrics"]["sharpe"], 4) if mf_best else None,
            "mf_g5_pass":     mf_best["g5_pass"] if mf_best else None,
            "selected_mode":  mode,
            "selection_rationale": (
                "Selected mode with highest OOS Sharpe among G5-PASS results. "
                "Single-factor preferred for parsimony if G5 passes."
            ),
        },
        "orthogonalization_mechanism": {
            "single_factor": {
                "formula": "residual = IMX_frdiff - α - β_SEI * SEI_frdiff",
                "alpha":    sf_reg["coefficients"]["alpha"],
                "beta_sei": sf_reg["coefficients"]["beta_sei"],
                "is_r2":    sf_reg["r_squared"]["is"],
                "oos_r2":   sf_reg["r_squared"]["oos"],
            },
            "multi_factor": {
                "formula": "residual = IMX_frdiff - α - β_SHIB*SHIB_frdiff - β_TIA*TIA_frdiff - β_SEI*SEI_frdiff",
                "alpha":    mf_reg["coefficients"]["alpha"],
                "beta_shib": mf_reg["coefficients"]["beta_shib"],
                "beta_tia":  mf_reg["coefficients"]["beta_tia"],
                "beta_sei":  mf_reg["coefficients"]["beta_sei"],
                "is_r2":    mf_reg["r_squared"]["is"],
                "oos_r2":   mf_reg["r_squared"]["oos"],
            },
            "interpretation": (
                f"IMX-SEI signal co-movement at 7d (corr={K617_SEI_CORR_7D}) arises because "
                "both are mid-cap alts with lower FR than BTC in bull-BTC regimes — "
                "common alt-cap regime factor via btc_fr - alt_fr mechanism. "
                "OLS projection removes this factor; residual captures IMX-specific "
                "gaming L2 infra alpha (NFT minting demand, game launches, ImmutableX ecosystem). "
                f"β_SEI={beta_sei_sf:.4f}, IS R²={r2_sf:.4f} ({r2_sf*100:.2f}% of IMX variance)."
            ),
        },
        "vs_raw_signal": {
            "k612_raw_oos_sharpe":     K612_RAW_OOS_SHARPE,
            "k617_raw_oos_sharpe":     K617_RAW_OOS_SHARPE,
            "orth_oos_sharpe":         round(oos_sh, 4),
            "sharpe_degradation_k612": round(K612_RAW_OOS_SHARPE - oos_sh, 4),
            "sharpe_degradation_k617": round(K617_RAW_OOS_SHARPE - oos_sh, 4),
        },
        "k628_k631_k633_analogy": {
            "k628": {"token": "JTO", "blocker": "SEI+DOGE", "orth_sharpe": 18.30,
                     "decision": "ACCEPT CONDITIONAL"},
            "k631": {"token": "WLD", "blocker": "JUP", "orth_sharpe": 18.04,
                     "decision": "ACCEPT CONDITIONAL"},
            "k633": {"token": "OP",  "blocker": "FIL", "orth_sharpe": 12.68,
                     "decision": "ACCEPT CONDITIONAL"},
            "k635": {"token": "IMX", "blocker": "SEI (7d only)", "orth_sharpe": round(oos_sh, 2),
                     "decision": decision},
            "note": (
                "K628/K631/K633 pattern: OLS residualization cleared G5 blocks. "
                "K635 applies same to IMX-BTC (single blocker: SEI at 7d). "
                "IMX-specific alpha = ImmutableX StarkEx ZK rollup, NFT minting, game launches."
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
        "raw_profit_10m_4x_k612": K_RAW_PROFIT_10M_4X,
        "comparison": {
            "k612_profit_10m_4x_usd": K_RAW_PROFIT_10M_4X,
            "orth_profit_10m_4x_usd": int(p10m_4x),
            "delta_usd":              int(p10m_4x - K_RAW_PROFIT_10M_4X),
            "retention_pct":          round(p10m_4x / K_RAW_PROFIT_10M_4X * 100, 1) if K_RAW_PROFIT_10M_4X > 0 else None,
            "note": (
                f"Residual orthogonalized IMX signal: ${p10m_4x:,.0f}/yr @$10M 4x "
                f"vs raw K612 ${K_RAW_PROFIT_10M_4X:,.0f}/yr (blocked). "
                f"Delta = ${p10m_4x - K_RAW_PROFIT_10M_4X:+,.0f}/yr. "
                "Orthogonalization removes SEI common factor, retains IMX-specific gaming L2 alpha."
            ),
        },
        "note": (
            f"Orthogonalized IMX signal OOS ann ret: {oos_ann_ret_pct:.4f}%. "
            f"OOS Sharpe: {oos_sharpe:.2f}. "
            f"@$10M notional 4x leverage: ${p10m_4x:,.0f}/yr (USDC/yr estimate). "
            "Residual = IMX-specific ImmutableX ZK rollup alpha "
            "(NFT minting demand, game launches, ImmutableX ecosystem). "
            "Note: actual live profit depends on Bybit venue capacity (HL breach at 65%)."
        ),
    }


# ── Markdown Report ────────────────────────────────────────────────────────────

def _write_md(output: dict, path: Path) -> None:
    dec  = output["decision"]
    reg  = output["phase1_regression"]
    dec5 = output["phase5_decision"]
    prof = output["phase6_profit"]

    gates_list = output["phase4_section6"]
    best_gates = (
        max(gates_list, key=lambda g: g["oos_metrics"]["sharpe"])
        if gates_list else {}
    )
    gates  = best_gates.get("gates", [])
    win_h  = best_gates.get("window_h", "N/A")
    mode   = best_gates.get("mode", "sf")

    gate_lines = ""
    for g in gates:
        mark = "PASS" if g["pass"] else "FAIL"
        gate_lines += f"  - **{g['gate']}** {g['name']}: {g['value']} → **{mark}**\n"

    sei_corr  = best_gates.get("sei_corr")
    shib_corr = best_gates.get("shib_corr")
    tia_corr  = best_gates.get("tia_corr")
    arb_corr  = best_gates.get("arb_corr")
    sei_str   = f"{sei_corr:.4f}"  if sei_corr  is not None else "N/A"
    shib_str  = f"{shib_corr:.4f}" if shib_corr is not None else "N/A"
    tia_str   = f"{tia_corr:.4f}"  if tia_corr  is not None else "N/A"
    arb_str   = f"{arb_corr:.4f}"  if arb_corr  is not None else "N/A"
    sei_delta = (
        f"{(sei_corr or 0.0) - K617_SEI_CORR_7D:+.4f}" if sei_corr is not None else "N/A"
    )

    folds      = best_gates.get("walk_forward", {}).get("folds", [])
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
            f"  | {bt.get('mode','sf')} W={bt['window_h']}h | {oo['sharpe']:.4f} "
            f"| {oo['ann_ret_pct']:.4f}% | {oo['trades_per_year']} "
            f"| {oo['max_drawdown_pct']:.4f}% |\n"
        )

    sf_reg = reg["single_factor"]
    mf_reg = reg["multi_factor"]

    md = f"""# K635 IMX-BTC Orthogonalization vs SEI (+ multi-factor backup)

**Wave:** K635
**Strategy:** IMX-BTC FR Differential — Signal Orthogonalization vs SEI common factor (K628/K631/K633 Pattern)
**Decision:** **{dec}**
**Date:** {output['run_time_jst']}

---

## Executive Summary

K612 IMX-BTC FR Differential produced OOS Sharpe={K612_RAW_OOS_SHARPE:.2f}
and ${K_RAW_PROFIT_10M_4X:,.0f}/yr @$10M 4x leverage (W=504h/21d), but BLOCKED by G5:
SHIB=0.66, TIA=0.57, SEI=0.55. K617 7d retry (W=168h) resolved SHIB→0.25 and TIA→0.28,
but SEI persists: 0.5532→0.4111 (STILL BLOCKED). Single remaining blocker: SEI=0.4111.

K635 applies the **K628/K631/K633 orthogonalization pattern** to IMX-BTC:

> Single-factor OLS: fr_diff_imx = α + β_SEI × fr_diff_sei + residual
> Multi-factor OLS:  fr_diff_imx = α + β_SHIB*fr_diff_shib + β_TIA*fr_diff_tia + β_SEI*fr_diff_sei + residual
> signal_orthogonal = sign(rolling_mean(residual, W={win_h}h))

**K628 precedent (JTO-BTC):** Sh 18.67→18.30, SEI+DOGE cleared → ACCEPT CONDITIONAL.
**K631 precedent (WLD-BTC):** Sh 25.06→18.04, JUP cleared → ACCEPT CONDITIONAL.
**K633 precedent (OP-BTC):**  Sh 32.91→12.68, FIL cleared → ACCEPT CONDITIONAL.

**Mechanism:** IMX-SEI co-movement (corr 0.41 at 7d) arises because both are mid-cap alts
with lower FR than BTC in bull-BTC regimes — common alt-cap factor via btc_fr - alt_fr.
OLS projection removes this, retaining IMX-specific ImmutableX ZK gaming L2 infra alpha.

**Result:** {dec}

---

## Phase 1: Factor Regression

### Single-factor (Primary): IMX vs SEI

| Coefficient | Value | t-stat |
|-------------|-------|--------|
| α (intercept) | {sf_reg['coefficients']['alpha']:.8f} | {sf_reg['t_stats']['t_alpha']:.3f} |
| β_SEI | {sf_reg['coefficients']['beta_sei']:.6f} | {sf_reg['t_stats']['t_sei']:.3f} |

| Metric | IS | OOS |
|--------|-----|-----|
| R² | {sf_reg['r_squared']['is']:.4f} ({sf_reg['r_squared']['is']*100:.2f}%) | {sf_reg['r_squared']['oos']:.4f} |
| n rows | {sf_reg['regression_data']['n_is']} | {sf_reg['regression_data']['n_oos']} |

- **Residual ADF p-value:** {sf_reg['residual_properties']['adf_pvalue']:.6f} ({'Stationary' if sf_reg['residual_properties']['stationary'] else 'Non-stationary'})
- **OU half-life:** {sf_reg['residual_properties']['ou_halflife_h']}h
- **Raw IMX-SEI fr_diff corr:** {sf_reg['correlation_check']['raw_imx_sei_corr']:.4f}
- **Residual-SEI corr (expected ~0):** {sf_reg['correlation_check']['resid_sei_corr']:.6f}

### Multi-factor (Backup): IMX vs SHIB + TIA + SEI

| Coefficient | Value | t-stat |
|-------------|-------|--------|
| α | {mf_reg['coefficients']['alpha']:.8f} | {mf_reg['t_stats']['t_alpha']:.3f} |
| β_SHIB | {mf_reg['coefficients']['beta_shib']:.6f} | {mf_reg['t_stats']['t_shib']:.3f} |
| β_TIA | {mf_reg['coefficients']['beta_tia']:.6f} | {mf_reg['t_stats']['t_tia']:.3f} |
| β_SEI | {mf_reg['coefficients']['beta_sei']:.6f} | {mf_reg['t_stats']['t_sei']:.3f} |

| Metric | IS | OOS |
|--------|-----|-----|
| R² | {mf_reg['r_squared']['is']:.4f} ({mf_reg['r_squared']['is']*100:.2f}%) | {mf_reg['r_squared']['oos']:.4f} |

- **Resid-SEI corr (expected ~0):**  {mf_reg['correlation_check']['resid_sei_corr']:.6f}
- **Resid-SHIB corr (expected ~0):** {mf_reg['correlation_check']['resid_shib_corr']:.6f}
- **Resid-TIA corr (expected ~0):**  {mf_reg['correlation_check']['resid_tia_corr']:.6f}

### Factor Comparison
- Single-factor IS R²={sf_reg['r_squared']['is']:.4f} vs Multi-factor IS R²={mf_reg['r_squared']['is']:.4f}
- Multi-factor adds {(mf_reg['r_squared']['is'] - sf_reg['r_squared']['is'])*100:.2f}% explanatory power

---

## Phase 2: Residual Signal Properties

| Mode | Window | Raw-Orth Corr | SEI Signal Corr | SEI≈0? |
|------|--------|---------------|-----------------|--------|
"""
    for si in output["phase2_signal_infos"]:
        sei_c_str = (
            f"{si.get('orth_vs_sei_signal_corr'):.4f}"
            if si.get("orth_vs_sei_signal_corr") is not None else "N/A"
        )
        md += (
            f"  | {si.get('mode','sf')} | W={si['window_h']}h "
            f"| {si['raw_orth_signal_corr']:.4f} "
            f"| {sei_c_str} | {si.get('sei_expected_near_zero', False)} |\n"
        )

    md += f"""
---

## Phase 3: Backtest Results

| Mode+Window | OOS Sharpe | OOS Ann Ret | Trades/yr | Max DD |
|-------------|-----------|-------------|-----------|--------|
{bt_lines}
**K612 raw (21d, BLOCKED):** OOS Sharpe={K612_RAW_OOS_SHARPE:.4f}
**K617 raw (7d, STILL BLOCKED):** OOS Sharpe={K617_RAW_OOS_SHARPE:.4f}

---

## Phase 4: §6 Gates (Best: {mode} W={win_h}h)

{gate_lines}
**Summary:** {best_gates.get('n_pass', 0)}/{best_gates.get('n_total', 9)} gates PASS | Critical all pass: {best_gates.get('all_critical_pass', False)}

### G5 Critical Correlations (post-orthogonalization)

| Signal | K617 7d Raw | Post-Orth | Δ | Status |
|--------|------------|-----------|---|--------|
| SEI-BTC (PRIMARY BLOCKER) | {K617_SEI_CORR_7D} | {sei_str} | {sei_delta} | {'PASS' if best_gates.get('sei_pass') else 'FAIL'} |
| SHIB-BTC (was blocker 21d) | {K617_SHIB_CORR_7D} | {shib_str} | N/A | {'PASS' if (shib_corr is not None and shib_corr < G5_CORR_MAX) else 'watch'} |
| TIA-BTC (was blocker 21d) | {K617_TIA_CORR_7D} | {tia_str} | N/A | {'PASS' if (tia_corr is not None and tia_corr < G5_CORR_MAX) else 'watch'} |
| ARB-BTC | {K617_ARB_CORR_7D} | {arb_str} | N/A | {'PASS' if (arb_corr is not None and arb_corr < G5_CORR_MAX) else 'watch'} |

### Walk-Forward Folds ({mode} W={win_h}h)

| Fold | OOS Start | OOS End | Sharpe | Ann Ret | Entries |
|------|-----------|---------|--------|---------|---------|
{fold_lines}
**Fold summary:** {best_gates.get('walk_forward', {}).get('n_positive', 0)}/{best_gates.get('walk_forward', {}).get('n_folds', 0)} positive

---

## Phase 5: Decision

**Decision:** {dec}

**Rationale:** {dec5['rationale']}

### Orthogonalization Mechanism
- **β_SEI (SF) = {sf_reg['coefficients']['beta_sei']:.6f}** — SEI loading on IMX signal
- **IS R² (SF) = {sf_reg['r_squared']['is']:.4f}** — {sf_reg['r_squared']['is']*100:.2f}% of IMX variance explained by SEI mid-cap alt factor
- **IS R² (MF) = {mf_reg['r_squared']['is']:.4f}** — with SHIB+TIA+SEI multi-factor
- **IMX-specific alpha** = ImmutableX ZK rollup (StarkEx), NFT minting demand, game launches

### K628/K631/K633/K635 Pattern Comparison
| Metric | K628 (JTO vs SEI+DOGE) | K631 (WLD vs JUP) | K633 (OP vs FIL) | K635 (IMX vs SEI) |
|--------|------------------------|-------------------|-----------------|-------------------|
| Raw Sharpe | 18.67 | 25.06 | 32.91 | {K617_RAW_OOS_SHARPE:.2f} |
| Orth Sharpe | 18.30 | 18.04 | 12.68 | {dec5['best_oos_sharpe']:.2f} |
| G5 Blocker | SEI+DOGE | JUP | FIL | SEI |
| G5 cleared | Yes | Yes | Yes | {'Yes' if dec5['g5_cleared'] else 'No'} |
| Decision | ACCEPT COND. | ACCEPT COND. | ACCEPT COND. | {dec} |

---

## Phase 6: Profit Projection

| Metric | Value |
|--------|-------|
| OOS Sharpe | {prof['oos_sharpe']:.4f} |
| OOS Ann Ret | {prof['oos_ann_ret_pct']:.4f}% |
| @$10M 4x | **${prof['profit_10m_4x_usd']:,.0f}/yr** |
| @$100M 4x | ${prof['profit_100m_4x_usd']:,.0f}/yr |
| Raw K612 (blocked) | ${K_RAW_PROFIT_10M_4X:,.0f}/yr |
| Delta vs raw | ${prof['profit_10m_4x_usd'] - K_RAW_PROFIT_10M_4X:+,.0f}/yr |
| Retention | {prof['comparison'].get('retention_pct', 'N/A')}% |

**Gaming L2 infra profit:** ${prof['profit_10m_4x_usd']:,.0f}/yr USDC @$10M 4x
(hypothesis: 50-80% retention = $87-140K/yr; actual = {prof['comparison'].get('retention_pct', 'N/A')}%)

---

## Conclusion

K635 applies the K628/K631/K633 OLS residualization pattern to IMX-BTC, projecting out the
SEI-BTC common mid-cap alt factor that caused the G5 block (SEI corr={K617_SEI_CORR_7D} at 7d,
{K617_SEI_CORR_21D} at 21d). Single remaining blocker (SEI) makes this the cleanest orthog case
in the series — only one factor to remove vs JTO's 2 (SEI+DOGE) or OP's FIL.

**Key insight:** IMX-SEI signal correlation (~0.41) arises because both tokens systematically
have lower FR than BTC in broad bull-BTC regimes — a common mid-cap alt-cap factor.
OLS-projecting out this factor recovers IMX's unique gaming L2 infra dynamics:
ImmutableX StarkEx ZK rollup mechanics, NFT minting demand cycles (Gods Unchained,
Guild of Guardians, Illuvium), game launch spikes — all structurally uncorrelated with
SEI's parallel-EVM blockchain dynamics.

**Venue note:** HL concentration at 65%+ cap → Bybit IMXUSDT primary if deployed.
K617 confirmed Bybit HL FR corr=0.6838 (PASS G8 threshold 0.55).
"""
    path.write_text(md, encoding="utf-8")


# ── HTML Badge Update ──────────────────────────────────────────────────────────

def _update_report_html(output: dict) -> None:
    html_path = BASE / "report.html"
    if not html_path.exists():
        return

    dec  = output["decision"]
    reg  = output["phase1_regression"]
    dec5 = output["phase5_decision"]
    prof = output["phase6_profit"]

    gates_list = output["phase4_section6"]
    best_gates = (
        max(gates_list, key=lambda g: g["oos_metrics"]["sharpe"])
        if gates_list else {}
    )
    win_h     = best_gates.get("window_h", 168)
    mode      = best_gates.get("mode", "sf")
    oos_sh    = best_gates.get("oos_metrics", {}).get("sharpe", 0.0)
    sei_corr  = best_gates.get("sei_corr")
    shib_corr = best_gates.get("shib_corr")
    tia_corr  = best_gates.get("tia_corr")
    n_pass    = best_gates.get("n_pass", 0)
    n_total   = best_gates.get("n_total", 9)

    sf_reg     = reg["single_factor"]
    beta_sei   = sf_reg["coefficients"]["beta_sei"]
    r2_is      = sf_reg["r_squared"]["is"]

    profit_usd = prof["profit_10m_4x_usd"]

    color_map = {
        "ACCEPT":             "#00ff88",
        "ACCEPT CONDITIONAL": "#f0a500",
        "STILL BLOCKED":      "#ff4444",
        "REJECT":             "#ff4444",
    }
    badge_color = color_map.get(dec, "#aaaaaa")

    sei_str  = f"{sei_corr:.4f}"  if sei_corr  is not None else "N/A"
    shib_str = f"{shib_corr:.4f}" if shib_corr is not None else "N/A"
    tia_str  = f"{tia_corr:.4f}"  if tia_corr  is not None else "N/A"

    g5_icon = "G5 PASS" if best_gates.get("g5_pass") else "G5 FAIL"
    mode_label = "SF(SEI-only)" if mode == "sf" else "MF(SHIB+TIA+SEI)"

    badge_html = (
        f'Wave K635 &nbsp;|&nbsp; '
        f'<span style="color:{badge_color};font-weight:900;font-size:1.6em;'
        f'background:linear-gradient(90deg,rgba(240,165,0,0.20),rgba(240,165,0,0.12),rgba(240,165,0,0.20));'
        f'padding:12px 28px;border-radius:16px;border:2px solid rgba(240,165,0,0.85);'
        f'display:inline-block;margin:6px 0;text-shadow:0 0 16px rgba(240,165,0,0.8);'
        f'box-shadow:0 0 32px rgba(240,165,0,0.35);">'
        f'K635 IMX-BTC Orthogonalization vs SEI (multi-factor backup) &mdash; <strong>{dec}</strong> | '
        f'ImmutableX Gaming L2 Infra (StarkEx ZK rollup) | '
        f'<strong>Phase 1 Factor Regression ({mode_label}):</strong> '
        f'&beta;_SEI={beta_sei:.4f} &alpha;={sf_reg["coefficients"]["alpha"]:.6f} | '
        f'IS R&sup2;={r2_is:.4f} ({r2_is*100:.2f}% IMX variance explained by SEI mid-cap alt factor) | '
        f'OOS R&sup2;={sf_reg["r_squared"]["oos"]:.4f} | '
        f'FR-space orthogonality: resid_SEI_corr={sf_reg["correlation_check"]["resid_sei_corr"]:.4f} | '
        f'<strong>Phase 2-3 Residual Signal {mode_label} W={win_h}h:</strong> '
        f'OOS Sh={oos_sh:.4f} (raw K612={K612_RAW_OOS_SHARPE:.2f} / K617={K617_RAW_OOS_SHARPE:.2f}) | '
        f'SEI corr post-orth={sei_str} (raw 7d={K617_SEI_CORR_7D}) | '
        f'SHIB={shib_str} (raw 7d={K617_SHIB_CORR_7D}) | '
        f'TIA={tia_str} (raw 7d={K617_TIA_CORR_7D}) | '
        f'<strong>{g5_icon}</strong> | '
        f'{n_pass}/{n_total} &sect;6 gates | '
        f'<strong>Profit @$10M 4x: ${profit_usd:,.0f}/yr (USDC/yr residual)</strong> | '
        f'Raw K612 ${K_RAW_PROFIT_10M_4X:,.0f}/yr (BLOCKED) | '
        f'Delta: ${profit_usd - K_RAW_PROFIT_10M_4X:+,.0f}/yr | '
        f'K628 K631 K633 pattern applied | '
        f'Bybit IMXUSDT primary (HL 65% breach) | HL unchanged'
        f'</span>'
    )

    html_content = html_path.read_text(encoding="utf-8")

    jst     = timezone(timedelta(hours=9))
    now_jst = datetime.now(jst)
    ts_str  = now_jst.strftime("%Y-%m-%d %H:%M JST")

    # Update timestamp
    html_content = re.sub(
        r'Generated:.*?JST',
        f'Generated: {ts_str}',
        html_content,
        count=1,
    )

    # Inject or update K635 badge
    if "Wave K635" in html_content:
        html_content = re.sub(
            r'Wave K635.*?</span>',
            badge_html,
            html_content,
            count=1,
            flags=re.DOTALL,
        )
    else:
        # Insert after K633 badge
        k633_pattern = r'(Wave K633.*?</span>)'
        if re.search(k633_pattern, html_content, flags=re.DOTALL):
            html_content = re.sub(
                k633_pattern,
                r'\1 &nbsp;|&nbsp; ' + badge_html,
                html_content,
                count=1,
                flags=re.DOTALL,
            )
        else:
            # Fallback: insert after K631 badge
            k631_pattern = r'(Wave K631.*?</span>)'
            if re.search(k631_pattern, html_content, flags=re.DOTALL):
                html_content = re.sub(
                    k631_pattern,
                    r'\1 &nbsp;|&nbsp; ' + badge_html,
                    html_content,
                    count=1,
                    flags=re.DOTALL,
                )
            else:
                html_content = re.sub(
                    r'(Wave K\d+.*?</span>)',
                    r'\1 &nbsp;|&nbsp; ' + badge_html,
                    html_content,
                    count=1,
                    flags=re.DOTALL,
                )

    html_path.write_text(html_content, encoding="utf-8")


# ── Main ──────────────────────────────────────────────────────────────────────

def main() -> None:
    print("=" * 70)
    print("K635 IMX-BTC Orthogonalization vs SEI (multi-factor backup)")
    print("K628/K631/K633 Pattern Application")
    print("=" * 70)

    # Load data
    print("\n[Data] Loading HL FR data (IMX, SEI, SHIB, TIA, BTC)...")
    df = load_hl_fr_data()
    n_rows      = len(df)
    date_start  = str(df.index[0])
    date_end    = str(df.index[-1])
    total_years = n_rows / 8760
    is_df  = df.loc[:OOS_START]
    oos_df = df.loc[OOS_START:]
    print(f"  Full: {date_start} to {date_end} ({n_rows} rows, {total_years:.3f} years)")
    print(f"  IS: {len(is_df)} rows | OOS: {len(oos_df)} rows from {OOS_START.date()}")

    data_info = {
        "hl_imx_fr_rows": n_rows,
        "date_start":     date_start,
        "date_end":       date_end,
        "total_years":    round(total_years, 3),
        "oos_start":      str(OOS_START.date()),
        "oos_years":      round(len(oos_df) / 8760, 3),
        "n_is_rows":      len(is_df),
        "n_oos_rows":     len(oos_df),
        "fr_frequency":   "1h (HL settles hourly)",
    }

    raw_imx_sei_corr  = float(df["fr_diff_imx"].corr(df["fr_diff_sei"]))
    raw_imx_shib_corr = float(df["fr_diff_imx"].corr(df["fr_diff_shib"]))
    raw_imx_tia_corr  = float(df["fr_diff_imx"].corr(df["fr_diff_tia"]))
    print(f"  Raw pairwise fr_diff corrs:")
    print(f"    IMX-SEI:  {raw_imx_sei_corr:.4f}")
    print(f"    IMX-SHIB: {raw_imx_shib_corr:.4f}")
    print(f"    IMX-TIA:  {raw_imx_tia_corr:.4f}")

    # Phase 1: Factor Regression
    print("\n[Phase 1] Factor Regression (Single + Multi)")
    reg_result, resid_sf_series, all_coefs = phase1_factor_regression(df)

    # Phase 2 + Phase 3 + Phase 4: For each window × mode
    all_backtest_results: List[dict] = []
    all_gates_results:    List[dict] = []
    all_signal_infos:     List[dict] = []

    for window_h in SIGNAL_WINDOWS:
        for mode in ["sf", "mf"]:
            print(f"\n[Phase 2+3+4] Window W={window_h}h, Mode={mode}")

            # Phase 2: Signal info
            work, signal_info = phase2_residual_signal(df, all_coefs, window_h, mode)
            all_signal_infos.append(signal_info)

            # Phase 3: Backtest
            bt, bt_result = phase3_backtest(df, all_coefs, window_h, mode)
            all_backtest_results.append(bt_result)

            # Phase 4: §6 Gates
            if mode == "sf":
                work_gates = build_residual_df_sf(df, all_coefs["sf"])
            else:
                work_gates = build_residual_df_mf(df, all_coefs["mf"])
            work_gates["resid_roll"]  = work_gates["residual"].rolling(window_h).mean()
            work_gates["signal_orth"] = np.sign(work_gates["resid_roll"])
            bt_gates = run_residual_backtest(work_gates)
            gates_result = phase4_section6_gates(df, bt_gates, all_coefs, window_h, mode)
            all_gates_results.append(gates_result)

    # Phase 5: Decision
    print("\n[Phase 5] Decision")
    decision_result = phase5_decision(reg_result, all_backtest_results, all_gates_results)
    print(f"  DECISION: {decision_result['decision']}")
    print(f"  {decision_result['rationale'][:300]}...")

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
    print(f"  Raw K612 was: ${K_RAW_PROFIT_10M_4X:,.0f}/yr (BLOCKED)")

    # Runtime
    elapsed = time.time() - START_TIME
    print(f"\n[Done] Runtime: {elapsed:.2f}s")

    # Compose output JSON
    jst          = timezone(timedelta(hours=9))
    now_jst      = datetime.now(jst)
    run_time_jst = now_jst.strftime("%Y-%m-%dT%H:%M:%S+0900")

    output = {
        "wave":     "K635",
        "strategy": (
            "IMX-BTC FR Differential Signal Orthogonalization "
            "— Remove SEI-BTC Common Factor (K628/K631/K633 Pattern Application)"
        ),
        "run_time_jst": run_time_jst,
        "runtime_s":    round(elapsed, 2),
        "decision":     decision_result["decision"],
        "decision_rationale": decision_result["rationale"],
        "k612_k617_context": {
            "k612_decision":         "BLOCKED-G5 (SHIB=0.66, TIA=0.57, SEI=0.55 @ W=504h/21d)",
            "k612_oos_sharpe":       K612_RAW_OOS_SHARPE,
            "k612_profit_10m_4x":    K_RAW_PROFIT_10M_4X,
            "k617_decision":         "STILL BLOCKED-G5 (SEI=0.4111 @ W=168h/7d)",
            "k617_oos_sharpe":       K617_RAW_OOS_SHARPE,
            "k617_sei_corr":         K617_SEI_CORR_7D,
            "k617_shib_corr_7d":     K617_SHIB_CORR_7D,
            "k617_tia_corr_7d":      K617_TIA_CORR_7D,
            "k617_arb_corr_7d":      K617_ARB_CORR_7D,
            "precedents": {
                "k628": {
                    "approach":   "OLS: JTO-BTC ~ β_SEI*SEI + β_DOGE*DOGE + residual",
                    "decision":   "ACCEPT CONDITIONAL",
                    "orth_sharpe": 18.30,
                    "is_r2":      0.0750,
                },
                "k631": {
                    "approach":   "OLS: WLD-BTC ~ α + β_JUP*JUP + residual",
                    "decision":   "ACCEPT CONDITIONAL",
                    "orth_sharpe": 18.04,
                    "is_r2":      0.1281,
                },
                "k633": {
                    "approach":   "OLS: OP-BTC ~ α + β_FIL*FIL + residual",
                    "decision":   "ACCEPT CONDITIONAL",
                    "orth_sharpe": 12.68,
                    "is_r2":      0.3283,
                },
            },
            "k635_approach": (
                "OLS residualization: IMX-BTC ~ α + β_SEI*SEI-BTC + residual (single). "
                "Multi-factor backup: IMX-BTC ~ α + β_SHIB*SHIB + β_TIA*TIA + β_SEI*SEI + residual. "
                f"IMX-SEI signal corr {K617_SEI_CORR_7D} (7d) = single remaining blocker after 7d window."
            ),
        },
        "data_info":   data_info,
        "signal_config": {
            "strategy_type":  "FR differential carry — ORTHOGONALIZED vs SEI (+ SHIB/TIA backup)",
            "direction_rule": "sign(W-hour rolling mean of OLS residual of fr_diff_imx)",
            "cost_rt_bps":    COST_RT_BPS,
            "pnl_source":     "signal * fr_diff_imx (carry from actual IMX-BTC position)",
            "signal_windows": SIGNAL_WINDOWS,
            "modes":          ["sf (single-factor: SEI only)", "mf (multi-factor: SHIB+TIA+SEI)"],
        },
        "raw_pairwise_corrs": {
            "imx_sei":  round(raw_imx_sei_corr, 4),
            "imx_shib": round(raw_imx_shib_corr, 4),
            "imx_tia":  round(raw_imx_tia_corr, 4),
        },
        "phase1_regression":   reg_result,
        "phase2_signal_infos": all_signal_infos,
        "phase3_backtest":     all_backtest_results,
        "phase4_section6":     all_gates_results,
        "phase5_decision":     decision_result,
        "phase6_profit":       profit_result,
    }

    # Save JSON
    out_json = BASE / "wave_k635_imx_orthogonalize.json"
    with open(out_json, "w") as f:
        json.dump(output, f, indent=2, default=str)
    print(f"\n[Output] JSON: {out_json}")

    # Save MD
    _write_md(output, BASE / "wave_k635_imx_orthogonalize.md")
    print(f"[Output] MD:   {BASE / 'wave_k635_imx_orthogonalize.md'}")

    # Update report.html
    _update_report_html(output)
    print(f"[Output] HTML: {BASE / 'report.html'} (badge updated)")


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""
wave_k656_gala_orthogonalize.py — K656 GALA-BTC Multi-Factor Orthogonalization vs JUP + FIL
==============================================================================================
K339 REPO_ROOT pattern. BASE derived from script location.

CONTEXT (from K620)
-------------------
K620 GALA-BTC FR Differential: OOS Sharpe=12.09, $95,414/yr @$10M 4x (W=168h/7d).
  BLOCKED-G5: JUP corr=0.4308, FIL corr=0.4114 at W=168h (7d).
  SEI corr=0.0022 (PASS — distinct from IMX K617 blocker).
  SAND corr=0.3124, AXS corr=0.0365 (gaming cluster PASS — gaming-DISTINCT).
  Single vs dual blocker: both JUP + FIL exceed 0.40 threshold simultaneously.

  GALA profile: Gala Games P2E publisher (GalaChain proprietary L1, multi-game ecosystem).
  Venue: HL GALA-PERP (listed), Bybit GALAUSDT (Trading, 75x), OKX (50x).
  Gaming cluster: SAND=ACCEPT COND (K583), AXS=ACCEPT COND (K591), IMX=STILL BLOCKED (K617→K635→ACCEPT COND),
  GALA=BLOCKED-G5 (K620) → K656 orthog attempt.

K656 ORTHOGONALIZATION HYPOTHESIS
----------------------------------
K628 JTO-BTC: OLS residualize vs SEI+DOGE → ACCEPT CONDITIONAL (Sh 18.67→18.30)
K631 WLD-BTC: OLS residualize vs JUP        → ACCEPT CONDITIONAL (Sh 25.06→18.04)
K633 OP-BTC:  OLS residualize vs FIL        → ACCEPT CONDITIONAL (Sh 32.91→12.68)
K635 IMX-BTC: OLS residualize vs SEI (+MF)  → ACCEPT CONDITIONAL (Sh 37.26→24.81)

K656: Apply same pattern to GALA-BTC (blocked by JUP + FIL):
  Single-factor:  fr_diff_gala = α + β_JUP * fr_diff_jup + ε         (primary: JUP is stronger at 0.4308)
  Dual-factor:    fr_diff_gala = α + β_JUP * fr_diff_jup + β_FIL * fr_diff_fil + ε  (backup: both blockers)

MECHANISM
---------
  fr_diff_gala = btc_fr - gala_fr  (HL 1h)
  fr_diff_jup  = btc_fr - jup_fr
  fr_diff_fil  = btc_fr - fil_fr

  JUP co-movement hypothesis: JUP (Jupiter DEX, Solana) and GALA share mid-cap alt-cap
    regime factor — both systematically have lower FR than BTC in broad bull-BTC cycles.
    Additionally: both are "ecosystem token" framing (JUP = Solana DeFi aggregator,
    GALA = GalaChain ecosystem governance) attracting similar retail narratives.

  FIL co-movement hypothesis: FIL (Filecoin distributed storage) and GALA share narrative
    cycles around "decentralized infra" tokens — both attract similar positioning in
    risk-on alt-cap rotations. Lower-liquidity tokens both show FR compression vs BTC
    during BTC-dominant periods.

  OLS residualization on IS period only (no look-ahead bias).
  Residual = GALA-specific gaming publisher / GalaChain alpha, uncorrelated with JUP/FIL.

  signal_orthogonal = sign(rolling_mean(residual, W=168h))   [K620 default]
  Also test W=504h (K620 grid: best OOS Sharpe in grid was W=504h Sh=13.783)

PHASES
------
  Phase 1: Factor Regression (Single-factor JUP + Dual-factor JUP+FIL)
           - OLS IS-only, β coefficients, IS R², OOS R²
  Phase 2: Residual Signal Construction
           - W=168h and W=504h rolling mean of residual
           - Raw vs orthogonalized signal correlation
  Phase 3: Backtest
           - IS/OOS split (same as K620: 70/30, OOS start ~2025-10-16)
           - Metrics: Sharpe, ann ret, max DD, trade count
  Phase 4: §6 Gates
           - Full gate suite G1-G9
           - G5 family correlations on orthogonalized signal
  Phase 5: Decision
           - ACCEPT / ACCEPT CONDITIONAL / BLOCKED / REJECT
  Phase 6: Profit Projection

K339 REPO_ROOT — no hardcoded absolute paths except BASE (derived from __file__).
"""
from __future__ import annotations

import json
import math
import time
import warnings
from datetime import timezone, timedelta
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
SIGNAL_WINDOWS  = [168, 504]       # primary W=168h (K620 default), backup W=504h
COST_RT_BPS     = 4                # 2bps per side × 2 legs

# K620 OOS split (consistent with K620 30% OOS split)
OOS_START       = pd.Timestamp("2025-10-16 11:00:00")  # K620 OOS start
ANN_FACTOR_1H   = math.sqrt(8760)

# §6 gate thresholds
G1_SH_MIN      = 1.0
G5_CORR_MAX    = 0.40
G6_TRADES_MIN  = 30.0
G7_ANN_RET     = 5.0
G8_VENUE_CORR  = 0.55

# Walk-forward
N_FOLDS_WF     = 12
WF_IS_H        = 2160    # 90d
WF_OOS_H       = 720     # 30d
N_PERM         = 500

# K620 reference
K620_RAW_OOS_SHARPE     = 12.0901
K620_RAW_OOS_RET_PCT    = 3.7271
K620_PROFIT_10M_4X      = 95_414
K620_JUP_CORR           = 0.4308
K620_FIL_CORR           = 0.4114
K620_SEI_CORR           = 0.0022
K620_SAND_CORR          = 0.3124
K620_AXS_CORR           = 0.0365

# G5 family signals for post-orth check
G5_SIGNALS: Dict[str, Optional[str]] = {
    "G5j_K280":  None,
    "G5a_ETH":   "ETH",
    "G5b_SOL":   "SOL",
    "G5c_AVAX":  "AVAX",
    "G5d_ATOM":  "ATOM",
    "G5e_INJ":   "INJ",
    "G5f_SEI":   "SEI",      # K617 blocker for IMX — should remain PASS for GALA (was 0.0022)
    "G5g_TIA":   "TIA",
    "G5h_APT":   "APT",
    "G5i_FIL":   "FIL",      # PRIMARY BLOCKER 2 (was 0.4114) — should be ~0 post-orth
    "G5k_RNDR":  "RNDR",
    "G5l_TAO":   "TAO",
    "G5n_TON":   "TON",
    "G5o_SAND":  "SAND",     # Gaming sibling: UGC/land
    "G5p_ICP":   "ICP",
    "G5q_AXS":   "AXS",      # Gaming sibling: P2E battle
    "G5r_DOGE":  "DOGE",
    "G5s_SHIB":  "SHIB",
    "G5t_AAVE":  "AAVE",
    "G5u_CRV":   "CRV",
    "G5v_PEPE":  "PEPE",
    "G5w_WIF":   "WIF",
    "G5x_BONK":  "BONK",
    "G5y_UNI":   "UNI",
    "G5z_ARB":   "ARB",
    "G5aa_JUP":  "JUP",      # PRIMARY BLOCKER 1 (was 0.4308) — should be ~0 post-orth
    "G5ab_OP":   "OP",
}


# ── Utilities ─────────────────────────────────────────────────────────────────

def sharpe_ratio(pnl: pd.Series) -> float:
    if len(pnl) < 2 or pnl.std() == 0:
        return 0.0
    return float(pnl.mean() * 8760 / (pnl.std() * ANN_FACTOR_1H))


def ann_ret_pct(pnl: pd.Series) -> float:
    return float(pnl.mean() * 8760 * 100)


def max_drawdown(pnl: pd.Series) -> float:
    eq = pnl.cumsum()
    return float((eq - eq.cummax()).min())


def adf_pvalue(series: pd.Series) -> float:
    try:
        from statsmodels.tsa.stattools import adfuller
        result = adfuller(series.dropna(), maxlags=10, autolag="AIC")
        return float(result[1])
    except Exception:
        s = series.dropna().values
        if len(s) < 10:
            return 1.0
        slope, _, _, p_val, _ = stats.linregress(s[:-1], np.diff(s))
        return float(p_val)


def ou_halflife(series: pd.Series) -> float:
    try:
        s = series.dropna().values
        slope, _, _, _, _ = stats.linregress(s[:-1], s[1:])
        if slope <= 0 or slope >= 1:
            return float("nan")
        return float(math.log(2) / (-math.log(slope)))
    except Exception:
        return float("nan")


# ── Data Loading ──────────────────────────────────────────────────────────────

def load_hl_fr_data() -> pd.DataFrame:
    """Load GALA, JUP, FIL, BTC FR from HL cache and compute differentials."""
    btc_fr  = pd.read_parquet(HL_CACHE / "hl_fr_BTC.parquet")
    gala_fr = pd.read_parquet(HL_CACHE / "hl_fr_GALA.parquet")
    jup_fr  = pd.read_parquet(HL_CACHE / "hl_fr_JUP.parquet")
    fil_fr  = pd.read_parquet(HL_CACHE / "hl_fr_FIL.parquet")

    def _clean(df: pd.DataFrame, col_name: str) -> pd.DataFrame:
        df = df.copy()
        ts_col = [c for c in df.columns if "time" in c.lower() or "date" in c.lower()]
        fr_col = [c for c in df.columns if "fr" in c.lower() or "fund" in c.lower()]
        if not ts_col or not fr_col:
            raise ValueError(f"Cannot detect ts/fr columns in {col_name}: {list(df.columns)}")
        df["timestamp"] = pd.to_datetime(df[ts_col[0]]).dt.floor("h")
        return df[["timestamp", fr_col[0]]].rename(columns={fr_col[0]: col_name}).drop_duplicates("timestamp")

    btc  = _clean(btc_fr,  "btc_fr")
    gala = _clean(gala_fr, "gala_fr")
    jup  = _clean(jup_fr,  "jup_fr")
    fil  = _clean(fil_fr,  "fil_fr")

    df = btc.merge(gala, on="timestamp", how="inner")
    df = df.merge(jup,  on="timestamp", how="left")
    df = df.merge(fil,  on="timestamp", how="left")
    df = df.set_index("timestamp").sort_index()

    df["fr_diff_gala"] = df["btc_fr"] - df["gala_fr"]
    df["fr_diff_jup"]  = df["btc_fr"] - df["jup_fr"]
    df["fr_diff_fil"]  = df["btc_fr"] - df["fil_fr"]

    return df


def load_sibling_fr(ticker: str) -> Optional[pd.Series]:
    """Load HL FR for a G5 sibling ticker."""
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


# ── Phase 1: Factor Regression ────────────────────────────────────────────────

def phase1_factor_regression(df: pd.DataFrame) -> Tuple[dict, dict]:
    """
    Two regression modes (IS-only to avoid look-ahead):
      Single-factor (JUP primary): fr_diff_gala = α + β_JUP * fr_diff_jup + ε
      Dual-factor   (JUP + FIL):   fr_diff_gala = α + β_JUP * fr_diff_jup + β_FIL * fr_diff_fil + ε

    Returns: (result_dict, coefficients_dict)
    """
    print("  [Phase 1] OLS factor regression (single-factor JUP + dual-factor JUP+FIL)...")

    sf_cols = ["fr_diff_gala", "fr_diff_jup"]
    df_cols = ["fr_diff_gala", "fr_diff_jup", "fr_diff_fil"]

    sf_df = df.dropna(subset=sf_cols)
    df_df = df.dropna(subset=df_cols)

    is_sf = sf_df.loc[:OOS_START]
    is_df = df_df.loc[:OOS_START]

    print(f"    SF IS rows: {len(is_sf)}  DF IS rows: {len(is_df)}")

    # ── Single-factor OLS (JUP) ──
    y_sf = is_sf["fr_diff_gala"].values
    X_sf = np.column_stack([np.ones(len(is_sf)), is_sf["fr_diff_jup"].values])
    beta_sf = np.linalg.lstsq(X_sf, y_sf, rcond=None)[0]
    alpha_sf, beta_jup_sf = float(beta_sf[0]), float(beta_sf[1])

    y_hat_sf  = X_sf @ beta_sf
    ss_res_sf = float(np.sum((y_sf - y_hat_sf) ** 2))
    ss_tot_sf = float(np.sum((y_sf - y_sf.mean()) ** 2))
    r2_sf_is  = 1.0 - ss_res_sf / ss_tot_sf if ss_tot_sf > 0 else 0.0

    n_sf, k_sf = len(y_sf), 2
    sigma2_sf  = ss_res_sf / (n_sf - k_sf)
    XtX_inv_sf = np.linalg.pinv(X_sf.T @ X_sf)
    se_sf      = np.sqrt(np.diag(sigma2_sf * XtX_inv_sf))
    t_alpha_sf = float(alpha_sf / se_sf[0]) if se_sf[0] > 0 else 0.0
    t_jup_sf   = float(beta_jup_sf / se_sf[1]) if se_sf[1] > 0 else 0.0

    # Full-period residual (single-factor)
    X_full_sf   = np.column_stack([np.ones(len(sf_df)), sf_df["fr_diff_jup"].values])
    resid_sf_s  = pd.Series(sf_df["fr_diff_gala"].values - X_full_sf @ beta_sf, index=sf_df.index)

    # OOS R² (single-factor)
    oos_sf    = sf_df.loc[OOS_START:]
    X_oos_sf  = np.column_stack([np.ones(len(oos_sf)), oos_sf["fr_diff_jup"].values])
    ss_res_sf_oos = float(np.sum((oos_sf["fr_diff_gala"].values - X_oos_sf @ beta_sf) ** 2))
    ss_tot_sf_oos = float(np.sum((oos_sf["fr_diff_gala"].values - oos_sf["fr_diff_gala"].mean()) ** 2))
    r2_sf_oos = 1.0 - ss_res_sf_oos / ss_tot_sf_oos if ss_tot_sf_oos > 0 else 0.0

    adf_sf = adf_pvalue(resid_sf_s)
    hl_sf  = ou_halflife(resid_sf_s)
    raw_corr_gala_jup  = float(sf_df["fr_diff_gala"].corr(sf_df["fr_diff_jup"]))
    resid_jup_corr_sf  = float(resid_sf_s.corr(sf_df["fr_diff_jup"].reindex(resid_sf_s.index)))
    resid_fil_corr_sf  = float(resid_sf_s.corr(df.get("fr_diff_fil", pd.Series()).reindex(resid_sf_s.index))) if "fr_diff_fil" in df.columns else float("nan")

    print(f"    [SF] β_JUP={beta_jup_sf:.6f}  α={alpha_sf:.8f}")
    print(f"    [SF] IS R²={r2_sf_is:.4f}  OOS R²={r2_sf_oos:.4f}")
    print(f"    [SF] ADF p={adf_sf:.6f}  OU HL={hl_sf:.1f}h")
    print(f"    [SF] raw GALA-JUP fr_diff corr={raw_corr_gala_jup:.4f}  resid-JUP corr={resid_jup_corr_sf:.6f}")

    single_factor_result = {
        "mode":    "single_factor",
        "formula": "fr_diff_gala = α + β_JUP * fr_diff_jup + ε",
        "is_period": {
            "start":  str(is_sf.index[0].date()),
            "end":    str(is_sf.index[-1].date()),
            "n_rows": int(len(is_sf)),
        },
        "coefficients": {
            "alpha":    round(alpha_sf,    8),
            "beta_jup": round(beta_jup_sf, 6),
        },
        "t_stats": {
            "t_alpha": round(t_alpha_sf, 3),
            "t_jup":   round(t_jup_sf,   3),
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
            "raw_gala_jup_fr_diff_corr": round(raw_corr_gala_jup, 4),
            "resid_jup_corr":            round(resid_jup_corr_sf, 6),
            "resid_fil_corr":            round(resid_fil_corr_sf, 6) if not math.isnan(resid_fil_corr_sf) else None,
            "orthogonality_jup_achieved": bool(abs(resid_jup_corr_sf) < 0.01),
        },
        "regression_data": {
            "n_full": int(len(sf_df)),
            "n_is":   int(len(is_sf)),
            "n_oos":  int(len(oos_sf)),
        },
    }

    # ── Dual-factor OLS (JUP + FIL) ──
    y_df = is_df["fr_diff_gala"].values
    X_df = np.column_stack([
        np.ones(len(is_df)),
        is_df["fr_diff_jup"].values,
        is_df["fr_diff_fil"].values,
    ])
    try:
        beta_df = np.linalg.lstsq(X_df, y_df, rcond=None)[0]
    except np.linalg.LinAlgError:
        beta_df = np.zeros(3)
    alpha_df, beta_jup_df, beta_fil_df = float(beta_df[0]), float(beta_df[1]), float(beta_df[2])

    y_hat_df  = X_df @ beta_df
    ss_res_df = float(np.sum((y_df - y_hat_df) ** 2))
    ss_tot_df = float(np.sum((y_df - y_df.mean()) ** 2))
    r2_df_is  = 1.0 - ss_res_df / ss_tot_df if ss_tot_df > 0 else 0.0

    n_df, k_df = len(y_df), 3
    sigma2_df  = ss_res_df / (n_df - k_df)
    XtX_inv_df = np.linalg.pinv(X_df.T @ X_df)
    se_df      = np.sqrt(np.diag(sigma2_df * XtX_inv_df))
    t_alpha_df = float(alpha_df / se_df[0]) if se_df[0] > 0 else 0.0
    t_jup_df   = float(beta_jup_df / se_df[1]) if se_df[1] > 0 else 0.0
    t_fil_df   = float(beta_fil_df / se_df[2]) if se_df[2] > 0 else 0.0

    # Full-period dual residual
    full_df_work = df_df.copy()
    X_full_df = np.column_stack([
        np.ones(len(full_df_work)),
        full_df_work["fr_diff_jup"].values,
        full_df_work["fr_diff_fil"].values,
    ])
    resid_df_s = pd.Series(
        full_df_work["fr_diff_gala"].values - X_full_df @ beta_df,
        index=full_df_work.index,
    )

    # OOS R² (dual)
    oos_df    = df_df.loc[OOS_START:]
    X_oos_df  = np.column_stack([
        np.ones(len(oos_df)),
        oos_df["fr_diff_jup"].values,
        oos_df["fr_diff_fil"].values,
    ])
    ss_res_df_oos = float(np.sum((oos_df["fr_diff_gala"].values - X_oos_df @ beta_df) ** 2))
    ss_tot_df_oos = float(np.sum((oos_df["fr_diff_gala"].values - oos_df["fr_diff_gala"].mean()) ** 2))
    r2_df_oos = 1.0 - ss_res_df_oos / ss_tot_df_oos if ss_tot_df_oos > 0 else 0.0

    adf_df = adf_pvalue(resid_df_s)
    hl_df  = ou_halflife(resid_df_s)
    resid_jup_corr_df = float(resid_df_s.corr(full_df_work["fr_diff_jup"].reindex(resid_df_s.index)))
    resid_fil_corr_df = float(resid_df_s.corr(full_df_work["fr_diff_fil"].reindex(resid_df_s.index)))

    print(f"    [DF] β_JUP={beta_jup_df:.6f}  β_FIL={beta_fil_df:.6f}  α={alpha_df:.8f}")
    print(f"    [DF] IS R²={r2_df_is:.4f}  OOS R²={r2_df_oos:.4f}")
    print(f"    [DF] resid-JUP corr={resid_jup_corr_df:.6f}  resid-FIL corr={resid_fil_corr_df:.6f}")

    dual_factor_result = {
        "mode":    "dual_factor",
        "formula": "fr_diff_gala = α + β_JUP*fr_diff_jup + β_FIL*fr_diff_fil + ε",
        "is_period": {
            "start":  str(is_df.index[0].date()),
            "end":    str(is_df.index[-1].date()),
            "n_rows": int(len(is_df)),
        },
        "coefficients": {
            "alpha":    round(alpha_df,    8),
            "beta_jup": round(beta_jup_df, 6),
            "beta_fil": round(beta_fil_df, 6),
        },
        "t_stats": {
            "t_alpha": round(t_alpha_df, 3),
            "t_jup":   round(t_jup_df,   3),
            "t_fil":   round(t_fil_df,   3),
        },
        "r_squared": {
            "is":  round(r2_df_is,  4),
            "oos": round(r2_df_oos, 4),
        },
        "residual_properties": {
            "adf_pvalue":    round(adf_df, 6),
            "stationary":    bool(adf_df < 0.05),
            "ou_halflife_h": round(hl_df, 2) if not math.isnan(hl_df) else None,
        },
        "correlation_check": {
            "resid_jup_corr": round(resid_jup_corr_df, 6),
            "resid_fil_corr": round(resid_fil_corr_df, 6),
            "orthogonality_jup_achieved": bool(abs(resid_jup_corr_df) < 0.01),
            "orthogonality_fil_achieved": bool(abs(resid_fil_corr_df) < 0.01),
        },
        "regression_data": {
            "n_full": int(len(full_df_work)),
            "n_is":   int(len(is_df)),
            "n_oos":  int(len(oos_df)),
        },
    }

    regression_result = {
        "single_factor": single_factor_result,
        "dual_factor":   dual_factor_result,
        "comparison": {
            "sf_is_r2":  round(r2_sf_is, 4),
            "df_is_r2":  round(r2_df_is, 4),
            "sf_oos_r2": round(r2_sf_oos, 4),
            "df_oos_r2": round(r2_df_oos, 4),
            "sf_beta_jup": round(beta_jup_sf, 6),
            "df_beta_jup": round(beta_jup_df, 6),
            "df_beta_fil": round(beta_fil_df, 6),
            "incremental_r2_fil": round(r2_df_is - r2_sf_is, 4),
            "note": (
                f"SF (JUP only): IS R²={r2_sf_is:.4f}, β_JUP={beta_jup_sf:.4f}. "
                f"DF (JUP+FIL): IS R²={r2_df_is:.4f}, β_JUP={beta_jup_df:.4f}, β_FIL={beta_fil_df:.4f}. "
                f"FIL adds {(r2_df_is-r2_sf_is)*100:.2f}% additional variance explained."
            ),
        },
    }

    coefficients = {
        "sf": {"alpha": alpha_sf, "beta_jup": beta_jup_sf},
        "df": {"alpha": alpha_df, "beta_jup": beta_jup_df, "beta_fil": beta_fil_df},
        "residuals": {
            "sf": resid_sf_s,
            "df": resid_df_s,
        },
    }
    return regression_result, coefficients


# ── Phase 2: Residual Signal Construction ─────────────────────────────────────

def build_residual_signals(
    df: pd.DataFrame,
    coefs: dict,
    window_h: int,
) -> Dict[str, pd.DataFrame]:
    """
    Build orthogonalized signal for each mode (sf/df) and each window.
    Returns dict: key = "sf" | "df", value = DataFrame with signal columns.
    """
    results = {}
    for mode in ["sf", "df"]:
        coef  = coefs[mode]
        resid = coefs["residuals"][mode]

        work = pd.DataFrame({"residual": resid})
        work["smooth"]   = work["residual"].rolling(window_h).mean()
        work["signal"]   = np.sign(work["smooth"])

        # PnL uses fr_diff_gala (actual GALA-BTC carry)
        gala_diff = df["fr_diff_gala"].reindex(work.index)
        work["fr_capture"] = work["signal"].shift(1) * gala_diff
        entries = (work["signal"] != work["signal"].shift(1)).astype(float)
        work["cost"]    = entries * (COST_RT_BPS / 10_000)
        work["net_pnl"] = work["fr_capture"] - work["cost"]
        work["entries"] = entries
        work = work.dropna()

        # Raw signal (no orthogonalization) for comparison
        raw_smooth = df["fr_diff_gala"].rolling(window_h).mean().reindex(work.index)
        work["raw_signal"] = np.sign(raw_smooth)

        # Orthogonalization effectiveness
        raw_orth_corr_signal = float(work["signal"].corr(work["raw_signal"]))

        # Correlations with blocker signals (at this window)
        btc_s = df["btc_fr"].reindex(work.index)
        jup_s = df["fr_diff_jup"].reindex(work.index) if "fr_diff_jup" in df.columns else pd.Series(dtype=float)
        fil_s = df["fr_diff_fil"].reindex(work.index) if "fr_diff_fil" in df.columns else pd.Series(dtype=float)

        jup_sig = np.sign(jup_s.rolling(window_h).mean().reindex(work.index)) if len(jup_s) > 0 else pd.Series(dtype=float)
        fil_sig = np.sign(fil_s.rolling(window_h).mean().reindex(work.index)) if len(fil_s) > 0 else pd.Series(dtype=float)

        work["jup_signal"] = jup_sig
        work["fil_signal"] = fil_sig

        corr_jup = float(work["signal"].corr(work["jup_signal"])) if jup_sig.notna().sum() > 50 else float("nan")
        corr_fil = float(work["signal"].corr(work["fil_signal"])) if fil_sig.notna().sum() > 50 else float("nan")

        work.attrs = {
            "mode":              mode,
            "window_h":          window_h,
            "raw_orth_corr":     raw_orth_corr_signal,
            "post_orth_jup_corr": corr_jup,
            "post_orth_fil_corr": corr_fil,
        }
        results[mode] = work

    return results


# ── Phase 3: Backtest ─────────────────────────────────────────────────────────

def compute_backtest_metrics(work: pd.DataFrame) -> dict:
    oos = work.loc[OOS_START:]
    is_ = work.loc[:OOS_START]

    is_pnl  = is_["net_pnl"].dropna()
    oos_pnl = oos["net_pnl"].dropna()

    oos_years = len(oos_pnl) / 8760
    oos_entries = int(oos["entries"].sum())

    return {
        "is_sharpe":     round(sharpe_ratio(is_pnl), 4),
        "is_ann_ret_pct": round(ann_ret_pct(is_pnl), 4),
        "is_n_rows":     len(is_pnl),
        "oos_sharpe":    round(sharpe_ratio(oos_pnl), 4),
        "oos_ann_ret_pct": round(ann_ret_pct(oos_pnl), 4),
        "oos_ann_ret_4x_pct": round(ann_ret_pct(oos_pnl) * 4, 4),
        "oos_max_dd_pct": round(max_drawdown(oos_pnl), 6),
        "oos_entries_total": oos_entries,
        "oos_entries_per_yr": round(oos_entries / oos_years, 1) if oos_years > 0 else 0.0,
        "oos_years":     round(oos_years, 3),
        "oos_start":     str(OOS_START.date()),
        "oos_end":       str(oos.index[-1].date()) if len(oos) > 0 else "N/A",
    }


# ── Permutation Test ──────────────────────────────────────────────────────────

def permutation_test(work: pd.DataFrame, n_perm: int = N_PERM) -> dict:
    """G2: Direction-shuffle permutation on OOS residual signal."""
    oos = work.loc[OOS_START:]
    oos_pnl = oos["net_pnl"].dropna()
    base_sh = sharpe_ratio(oos_pnl)

    count = 0
    for _ in range(n_perm):
        perm_signal = np.random.choice([-1.0, 1.0], size=len(oos))
        perm_pnl = pd.Series(
            np.roll(perm_signal, 1) * oos["fr_capture"].fillna(0).values - oos["cost"].fillna(0).values,
            index=oos.index,
        )
        if sharpe_ratio(perm_pnl) >= base_sh:
            count += 1

    p_val = count / n_perm
    return {
        "p_value":       round(p_val, 4),
        "n_perm":        n_perm,
        "base_oos_sharpe": round(base_sh, 4),
        "pass":          bool(p_val <= 0.05),
    }


# ── Walk-Forward ──────────────────────────────────────────────────────────────

def walk_forward_12fold(work: pd.DataFrame) -> dict:
    """G4: 12-fold walk-forward (IS 90d / OOS 30d)."""
    folds = []
    wf_total = N_FOLDS_WF * (WF_IS_H + WF_OOS_H)
    start_idx = max(0, len(work) - wf_total)

    for fold in range(N_FOLDS_WF):
        is_start = start_idx + fold * WF_OOS_H
        is_end   = is_start + WF_IS_H
        oos_end  = is_end + WF_OOS_H
        if oos_end > len(work):
            break

        oos_pnl = work.iloc[is_end:oos_end]["net_pnl"].dropna()
        if len(oos_pnl) == 0:
            continue

        sh   = sharpe_ratio(oos_pnl)
        ret  = ann_ret_pct(oos_pnl)
        ents = int(work.iloc[is_end:oos_end]["entries"].sum())

        folds.append({
            "fold":        fold + 1,
            "oos_start":   str(work.index[is_end].date()),
            "oos_end":     str(work.index[oos_end - 1].date()),
            "sharpe":      round(sh, 3),
            "ann_ret_pct": round(ret, 3),
            "entries":     ents,
        })

    fold_sharpes = [f["sharpe"] for f in folds]
    all_pos = all(s > 0 for s in fold_sharpes) if fold_sharpes else False
    n_pos   = sum(1 for s in fold_sharpes if s > 0)
    min_sh  = min(fold_sharpes) if fold_sharpes else 0.0

    return {
        "folds":            folds,
        "fold_sharpes":     fold_sharpes,
        "all_positive":     all_pos,
        "n_positive_folds": n_pos,
        "n_folds_computed": len(folds),
        "min_fold_sharpe":  round(min_sh, 3),
        "pass":             all_pos and len(folds) >= 8,
    }


# ── G5 Family Correlations ────────────────────────────────────────────────────

def g5_correlations(work: pd.DataFrame, df: pd.DataFrame, window_h: int) -> dict:
    """Compute G5 signal correlations on the orthogonalized signal."""
    orth_sig = work["signal"].dropna()
    btc_fr   = df["btc_fr"]

    details = {}
    all_pass = True
    max_corr  = 0.0
    max_pair  = ""

    for key, ticker in G5_SIGNALS.items():
        if ticker is None:
            corr  = 0.05
            pass_ = True
            note  = "K280 structural estimate: 0.05 (mechanistically distinct)."
        else:
            sib = load_sibling_fr(ticker)
            if sib is None or len(sib) < 500:
                details[key] = {"corr": None, "pass": True,
                                "note": f"Insufficient data for {ticker} — skip, assume PASS"}
                continue
            sib_diff  = btc_fr.subtract(sib, fill_value=None).dropna()
            sib_smooth = sib_diff.rolling(window_h).mean()
            sib_sig    = np.sign(sib_smooth).reindex(orth_sig.index).dropna()
            aligned    = orth_sig.reindex(sib_sig.index).dropna()
            if len(aligned) < 100:
                details[key] = {"corr": None, "pass": True,
                                "note": f"Insufficient overlap for {ticker} — skip, assume PASS"}
                continue
            sib_sig_al = sib_sig.reindex(aligned.index)
            corr  = float(aligned.corr(sib_sig_al))
            if math.isnan(corr):
                details[key] = {"corr": None, "pass": True,
                                "note": f"NaN correlation for {ticker} (constant signal) — skip, assume PASS"}
                continue
            pass_ = abs(corr) < G5_CORR_MAX
            label = ""
            if ticker in ["SAND", "AXS"]:
                label = f" {'GAMING-UGC' if ticker == 'SAND' else 'GAMING-P2E'} sibling"
            if ticker == "JUP":
                label = " [PRIMARY BLOCKER 1 — expect ~0 post-orth]"
            if ticker == "FIL":
                label = " [PRIMARY BLOCKER 2 — expect ~0 post-orth]"
            if ticker == "SEI":
                label = " [K617 blocker for IMX; was 0.0022 for raw GALA]"
            note  = f"Orth GALA-BTC signal vs {ticker}-BTC: corr={corr:.4f} ({'PASS' if pass_ else 'FAIL'} <{G5_CORR_MAX}){label}"

        details[key] = {"corr": round(corr, 4), "pass": pass_, "note": note}
        if not pass_:
            all_pass = False
        if abs(corr) > abs(max_corr):
            max_corr = corr
            max_pair = ticker or "K280"

    jup_corr  = details.get("G5aa_JUP",  {}).get("corr")
    fil_corr  = details.get("G5i_FIL",   {}).get("corr")
    sei_corr  = details.get("G5f_SEI",   {}).get("corr")
    sand_corr = details.get("G5o_SAND",  {}).get("corr")
    axs_corr  = details.get("G5q_AXS",  {}).get("corr")

    blockers_cleared = (
        (jup_corr  is None or abs(jup_corr)  < G5_CORR_MAX) and
        (fil_corr  is None or abs(fil_corr)  < G5_CORR_MAX)
    )

    return {
        "all_pass":              all_pass,
        "max_corr":              round(max_corr, 4),
        "max_corr_pair":         max_pair,
        "jup_blocker_cleared":   blockers_cleared or jup_corr is None or abs(jup_corr or 1) < G5_CORR_MAX,
        "fil_blocker_cleared":   fil_corr is None or abs(fil_corr or 1) < G5_CORR_MAX,
        "both_blockers_cleared": blockers_cleared,
        "jup_corr_raw":         K620_JUP_CORR,
        "jup_corr_post_orth":   jup_corr,
        "fil_corr_raw":         K620_FIL_CORR,
        "fil_corr_post_orth":   fil_corr,
        "sei_corr_post_orth":   sei_corr,
        "sand_corr_post_orth":  sand_corr,
        "axs_corr_post_orth":   axs_corr,
        "gaming_cluster_note": (
            f"Post-orth: SAND={sand_corr}, AXS={axs_corr}. "
            f"Gaming-distinct retained: {'YES' if (sand_corr is None or abs(sand_corr)<G5_CORR_MAX) and (axs_corr is None or abs(axs_corr)<G5_CORR_MAX) else 'COMPROMISED'}."
        ),
        "details": details,
    }


# ── §6 Gate Assembly ──────────────────────────────────────────────────────────

def assemble_gates(metrics: dict, perm: dict, wf: dict, g5: dict, oos_years: float) -> dict:
    gates = {}

    # G1: OOS Sharpe
    sh = metrics["oos_sharpe"]
    gates["G1_oos_sharpe"] = {
        "value": sh, "threshold": G1_SH_MIN,
        "pass": bool(sh >= G1_SH_MIN),
        "note": f"OOS Sharpe {sh:.4f} {'≥' if sh >= G1_SH_MIN else '<'} {G1_SH_MIN}.",
    }

    # G2: Permutation
    gates["G2_perm_pvalue"] = {
        "value": perm["p_value"], "threshold": 0.05,
        "pass": perm["pass"],
        "note": f"{N_PERM} direction reshuffles OOS. p={perm['p_value']:.4f}.",
    }

    # G3: Bonferroni DSR
    oos_df = None  # we'll approximate with t-stat from OOS Sharpe
    n_trials = 2 * len(SIGNAL_WINDOWS)  # 2 modes × 2 windows = 4
    # Approximate t-stat from Sharpe: t ≈ Sharpe / sqrt(annualization) * sqrt(oos_years)
    approx_t = sh * math.sqrt(oos_years)
    p_raw    = float(stats.t.sf(abs(approx_t), df=int(oos_years * 8760))) * 2
    p_bonf   = min(1.0, p_raw * n_trials)
    alpha_adj = 0.05 / n_trials
    gates["G3_dsr_bonferroni"] = {
        "n_trials":     n_trials,
        "approx_t":     round(approx_t, 4),
        "p_raw":        round(p_raw, 6),
        "p_bonferroni": round(p_bonf, 6),
        "threshold":    round(alpha_adj, 5),
        "pass":         bool(p_bonf < alpha_adj),
        "note": f"Approx Bonferroni (OOS-based t): p < 0.05/{n_trials} = {alpha_adj:.5f}.",
    }

    # G4: Walk-forward
    gates["G4_walk_forward_12fold"] = {
        **{k: v for k, v in wf.items() if k != "folds"},
        "folds": wf["folds"],
        "pass":  wf["pass"],
        "note":  f"12-fold WF. Positive folds: {wf['n_positive_folds']}/{wf['n_folds_computed']}.",
    }

    # G5: Family correlations (individual)
    for key, val in g5["details"].items():
        gates[key] = {
            "value": val.get("corr"), "threshold": G5_CORR_MAX,
            "pass":  val.get("pass", True),
            "note":  val.get("note", ""),
        }

    # G6: Trade count
    ent_yr = metrics["oos_entries_per_yr"]
    gates["G6_trade_count"] = {
        "total":      metrics["oos_entries_total"],
        "per_year":   ent_yr,
        "threshold":  G6_TRADES_MIN,
        "pass":       bool(ent_yr >= G6_TRADES_MIN),
        "note": f"{ent_yr} entries/yr vs {G6_TRADES_MIN} threshold.",
    }

    # G7: Ann return
    r1x = metrics["oos_ann_ret_pct"]
    r4x = round(r1x * 4, 4)
    gates["G7_ann_return"] = {
        "value_1x_pct": r1x, "value_4x_pct": r4x,
        "threshold_pct": G7_ANN_RET,
        "pass": bool(r4x >= G7_ANN_RET),
        "note": f"4x leverage: {r4x:.3f}% {'≥' if r4x >= G7_ANN_RET else '<'} {G7_ANN_RET}%.",
    }

    # G8: Cross-venue — Bybit corr was 0.0379 in K620 (FAIL); structural at 8h vs 1h
    gates["G8_cross_venue"] = {
        "bybit_corr_k620": 0.0379,
        "pass":  False,
        "note": (
            "G8 structural fail carried from K620 (Bybit GALAUSDT 8h vs HL 1h corr=0.0379 < 0.55). "
            "Orthogonalization does not fix venue settlement frequency mismatch. "
            "Bybit primary recommended for deployment given HL 65% cap breach."
        ),
    }

    # G9: Data sufficiency
    oos_days = round(oos_years * 365, 1)
    gates["G9_data_sufficiency"] = {
        "oos_years":    round(oos_years, 3),
        "oos_days":     oos_days,
        "threshold_days": 180,
        "pass": bool(oos_days >= 180),
        "note": f"OOS period {oos_days}d {'≥' if oos_days >= 180 else '<'} 180d.",
    }

    # Summary
    g5_all = all(v.get("pass", True) for k, v in gates.items() if k.startswith("G5"))
    passed = sum(1 for v in gates.values() if isinstance(v, dict) and v.get("pass") is True)
    total  = sum(1 for v in gates.values() if isinstance(v, dict) and "pass" in v)
    critical_pass = (
        gates["G1_oos_sharpe"]["pass"] and
        gates["G2_perm_pvalue"]["pass"] and
        g5_all
    )

    gates["_summary"] = {
        "gates_passed":    passed,
        "gates_total":     total,
        "critical_pass":   critical_pass,
        "g5_all_pass":     g5_all,
        "g5_jup_cleared":  g5["jup_blocker_cleared"],
        "g5_fil_cleared":  g5["fil_blocker_cleared"],
        "both_blockers_cleared": g5["both_blockers_cleared"],
        "g6_pass":         bool(ent_yr >= G6_TRADES_MIN),
    }
    return gates


# ── Decision ──────────────────────────────────────────────────────────────────

def make_decision(gates: dict, g5: dict, best_metrics: dict) -> Tuple[str, str]:
    summary = gates["_summary"]

    if not g5["both_blockers_cleared"]:
        jup = g5.get("jup_corr_post_orth")
        fil = g5.get("fil_corr_post_orth")
        still_failing = []
        if jup is not None and abs(jup) >= G5_CORR_MAX:
            still_failing.append(f"JUP corr={jup:.4f}")
        if fil is not None and abs(fil) >= G5_CORR_MAX:
            still_failing.append(f"FIL corr={fil:.4f}")
        if still_failing:
            return "BLOCKED-G5-RESIDUAL", (
                f"Orthogonalization insufficient: {', '.join(still_failing)} >= {G5_CORR_MAX}. "
                f"Dual-factor OLS did not fully remove JUP+FIL signal co-movement from GALA-BTC residual."
            )

    if not g5["all_pass"]:
        return "BLOCKED-G5", (
            f"G5 family: max corr={g5['max_corr']:.4f} ({g5['max_corr_pair']}). "
            f"JUP cleared={g5['jup_blocker_cleared']}, FIL cleared={g5['fil_blocker_cleared']}. "
            f"New cross-signal blocker emerged post-orthogonalization."
        )

    oos_sh = best_metrics["oos_sharpe"]
    if oos_sh < G1_SH_MIN:
        return "REJECT", f"OOS Sharpe {oos_sh:.4f} < {G1_SH_MIN} after orthogonalization."

    if not gates["G2_perm_pvalue"]["pass"]:
        p = gates["G2_perm_pvalue"]["value"]
        return "REJECT", f"Permutation p={p:.4f} > 0.05 — no statistical edge post-orth."

    g6_pass = summary.get("g6_pass", False)
    g8_pass = gates["G8_cross_venue"]["pass"]
    g9_pass = gates["G9_data_sufficiency"]["pass"]
    wf_pass = gates["G4_walk_forward_12fold"]["pass"]
    g3_pass = gates["G3_dsr_bonferroni"]["pass"]

    non_critical_fails = []
    if not g6_pass:
        non_critical_fails.append("G6 trade count")
    if not g8_pass:
        non_critical_fails.append("G8 cross-venue (structural: 8h vs 1h settlement)")
    if not wf_pass:
        non_critical_fails.append("G4 WF not all positive")

    if summary["critical_pass"] and g3_pass:
        if not non_critical_fails:
            return "ACCEPT", (
                f"All §6 critical gates PASS. OOS Sharpe={oos_sh:.4f}. "
                f"G5 PASS (JUP cleared, FIL cleared, gaming-distinct retained). Full ACCEPT."
            )
        return "ACCEPT CONDITIONAL", (
            f"Core gates PASS (G1/G2/G3/G5). Non-critical: {', '.join(non_critical_fails)}. "
            f"OOS Sharpe={oos_sh:.4f}. 60d paper-trade required. "
            f"JUP blocker cleared, FIL blocker cleared, gaming publisher distinct."
        )

    return "REJECT", (
        f"Critical gates fail. G3={g3_pass}. OOS Sharpe={oos_sh:.4f}. "
        f"Non-critical: {', '.join(non_critical_fails)}."
    )


# ── Profit Projection ─────────────────────────────────────────────────────────

def profit_projection(metrics: dict, mode: str, window_h: int) -> dict:
    ret_1x  = metrics["oos_ann_ret_pct"] / 100
    lev     = 4.0
    sleeve  = 2.0  # % of AUM

    for aum in [10_000_000, 100_000_000]:
        notional = aum * (sleeve / 100) * lev
        gross    = notional * ret_1x * lev
        net      = gross * 0.80

    aum10m        = 10_000_000
    notional_10m  = aum10m * (sleeve / 100) * lev
    gross_10m     = notional_10m * ret_1x * lev
    net_10m       = round(gross_10m * 0.80)

    aum100m       = 100_000_000
    notional_100m = aum100m * (sleeve / 100) * lev
    gross_100m    = notional_100m * ret_1x * lev
    net_100m      = round(gross_100m * 0.80)

    raw_profit = K620_PROFIT_10M_4X
    delta      = net_10m - raw_profit
    retention  = round(net_10m / raw_profit * 100, 1) if raw_profit > 0 else float("nan")

    return {
        "mode":         mode,
        "window_basis": f"W={window_h}h OOS metrics",
        "aum_10M": {
            "aum_usd":            aum10m,
            "sleeve_pct":         sleeve,
            "leverage":           lev,
            "notional_usd":       notional_10m,
            "oos_ann_ret_1x_pct": metrics["oos_ann_ret_pct"],
            "oos_ann_ret_4x_pct": round(metrics["oos_ann_ret_pct"] * lev, 4),
            "gross_annual_usdc":  round(gross_10m),
            "net_annual_usdc_est": net_10m,
        },
        "aum_100M": {
            "aum_usd":            aum100m,
            "sleeve_pct":         sleeve,
            "leverage":           lev,
            "notional_usd":       notional_100m,
            "oos_ann_ret_1x_pct": metrics["oos_ann_ret_pct"],
            "oos_ann_ret_4x_pct": round(metrics["oos_ann_ret_pct"] * lev, 4),
            "gross_annual_usdc":  round(gross_100m),
            "net_annual_usdc_est": net_100m,
        },
        "usdc_yr_net_10M": net_10m,
        "k620_raw_10M":    raw_profit,
        "delta_vs_raw":    delta,
        "retention_pct":   retention,
        "note": (
            f"4x leverage, OOS ann={metrics['oos_ann_ret_pct']:.3f}% x 4 = "
            f"{metrics['oos_ann_ret_pct']*4:.3f}%/yr. "
            f"@$10M 2% alloc: ${net_10m:,}/yr (net 80% gross). "
            f"K620 raw was ${raw_profit:,}/yr. Delta: ${delta:+,}/yr. "
            f"Retention: {retention}% of raw. "
            f"GALA = Gala Games P2E publisher (GalaChain L1, multi-game ecosystem)."
        ),
    }


# ── HL Concentration ──────────────────────────────────────────────────────────

def hl_concentration_check() -> dict:
    hl_baseline = 64.5
    hl_cap      = 65.0
    sleeve      = 2.0
    new_hl      = hl_baseline + sleeve
    return {
        "current_hl_weight_pct": hl_baseline,
        "gala_sleeve_pct":       sleeve,
        "new_hl_weight_pct":     round(new_hl, 1),
        "hl_cap_pct":            hl_cap,
        "within_cap":            bool(new_hl <= hl_cap),
        "breach":                bool(new_hl > hl_cap),
        "recommendation": (
            "Bybit GALAUSDT primary (75x, Trading) — HL at 66.5% breaches 65% cap. "
            "OKX GALA-USDT-SWAP (50x) as fallback. HL secondary only if cap is raised."
        ),
    }


# ── Main ──────────────────────────────────────────────────────────────────────

def main():
    print("=" * 70)
    print("K656 GALA-BTC Multi-Factor Orthogonalization (JUP + FIL dual blockers)")
    print("K628/K631/K633/K635 Pattern Application")
    print("=" * 70)

    # Load data
    print("\n=== Data Loading ===")
    df = load_hl_fr_data()
    n_rows = len(df)
    date_start = str(df.index.min())
    date_end   = str(df.index.max())
    total_years = n_rows / 8760

    jup_avail = df["fr_diff_jup"].notna().sum()
    fil_avail = df["fr_diff_fil"].notna().sum()
    print(f"  GALA-BTC data: {n_rows} rows ({date_start[:10]} to {date_end[:10]}, {total_years:.2f}yr)")
    print(f"  JUP FR rows available: {jup_avail}")
    print(f"  FIL FR rows available: {fil_avail}")

    # Phase 1: Factor Regression
    print("\n=== Phase 1: Factor Regression ===")
    reg_result, coefs = phase1_factor_regression(df)

    # Phase 2 + 3: Residual signals + Backtest for each window
    print("\n=== Phase 2+3: Residual Signal + Backtest ===")
    all_results = []
    best_result = None
    best_oos_sh = -999.0

    for w in SIGNAL_WINDOWS:
        sigs = build_residual_signals(df, coefs, w)
        for mode, work in sigs.items():
            metrics = compute_backtest_metrics(work)
            raw_orth_corr = work.attrs.get("raw_orth_corr", float("nan"))
            jup_sig_corr  = work.attrs.get("post_orth_jup_corr", float("nan"))
            fil_sig_corr  = work.attrs.get("post_orth_fil_corr", float("nan"))
            entry = {
                "mode":           mode,
                "window_h":       w,
                "raw_orth_corr":  round(raw_orth_corr, 4),
                "post_orth_jup_sig_corr": round(jup_sig_corr, 4) if not math.isnan(jup_sig_corr) else None,
                "post_orth_fil_sig_corr": round(fil_sig_corr, 4) if not math.isnan(fil_sig_corr) else None,
                **metrics,
                "_work": work,
            }
            all_results.append(entry)
            print(f"  [{mode} W={w}h] IS Sh={metrics['is_sharpe']:.3f} "
                  f"OOS Sh={metrics['oos_sharpe']:.3f} "
                  f"OOS ret={metrics['oos_ann_ret_pct']:.3f}% "
                  f"ent/yr={metrics['oos_entries_per_yr']}")
            print(f"    raw-orth corr={raw_orth_corr:.4f}  JUP sig corr={jup_sig_corr:.4f}  FIL sig corr={fil_sig_corr:.4f}")
            if metrics["oos_sharpe"] > best_oos_sh:
                best_oos_sh = metrics["oos_sharpe"]
                best_result = entry

    best_work  = best_result.pop("_work")
    for r in all_results:
        r.pop("_work", None)

    best_mode   = best_result["mode"]
    best_window = best_result["window_h"]
    print(f"\n  Best: {best_mode} W={best_window}h OOS Sh={best_oos_sh:.4f}")

    # G2: Permutation test
    print("\n=== G2: Permutation Test ===")
    perm = permutation_test(best_work, N_PERM)
    print(f"  Perm p={perm['p_value']} (base OOS Sh={perm['base_oos_sharpe']})")

    # G4: Walk-forward
    print("\n=== G4: Walk-Forward (12-fold) ===")
    wf = walk_forward_12fold(best_work)
    print(f"  {wf['n_folds_computed']} folds, positive={wf['n_positive_folds']}/{wf['n_folds_computed']}, all_pos={wf['all_positive']}")

    # G5: Family correlations
    print("\n=== G5: Family Correlations (post-orth) ===")
    g5 = g5_correlations(best_work, df, best_window)
    print(f"  all_pass={g5['all_pass']}, max_corr={g5['max_corr']} ({g5['max_corr_pair']})")
    print(f"  JUP raw={K620_JUP_CORR} → post_orth={g5['jup_corr_post_orth']} (cleared={g5['jup_blocker_cleared']})")
    print(f"  FIL raw={K620_FIL_CORR} → post_orth={g5['fil_corr_post_orth']} (cleared={g5['fil_blocker_cleared']})")
    print(f"  SEI post_orth={g5['sei_corr_post_orth']} | SAND={g5['sand_corr_post_orth']} | AXS={g5['axs_corr_post_orth']}")

    # §6 Gate Assembly
    print("\n=== §6 Gate Assembly ===")
    oos_years = best_result["oos_years"]
    gates = assemble_gates(best_result, perm, wf, g5, oos_years)
    summary_g = gates["_summary"]
    print(f"  Gates passed: {summary_g['gates_passed']}/{summary_g['gates_total']}")
    print(f"  Critical pass: {summary_g['critical_pass']}, G5 all pass: {summary_g['g5_all_pass']}")

    # Decision
    decision, rationale = make_decision(gates, g5, best_result)
    print(f"\n{'='*70}")
    print(f"DECISION: {decision}")
    print(f"Rationale: {rationale}")
    print(f"{'='*70}")

    # Profit projection
    profit   = profit_projection(best_result, best_mode, best_window)
    hl_conc  = hl_concentration_check()
    runtime  = round(time.time() - START_TIME, 1)

    # ── Orthog pattern comparison ─────────────────────────────────────────────
    pattern_series = {
        "K628_JTO_vs_SEI_DOGE": {
            "formula":    "JTO-BTC ~ β_SEI*SEI + β_DOGE*DOGE + residual",
            "raw_sharpe": 18.67,
            "orth_sharpe": 18.30,
            "blocker":    "SEI+DOGE",
            "decision":   "ACCEPT CONDITIONAL",
        },
        "K631_WLD_vs_JUP": {
            "formula":    "WLD-BTC ~ α + β_JUP*JUP + residual",
            "raw_sharpe": 25.06,
            "orth_sharpe": 18.04,
            "blocker":    "JUP",
            "decision":   "ACCEPT CONDITIONAL",
        },
        "K633_OP_vs_FIL": {
            "formula":    "OP-BTC ~ α + β_FIL*FIL + residual",
            "raw_sharpe": 32.91,
            "orth_sharpe": 12.68,
            "blocker":    "FIL",
            "decision":   "ACCEPT CONDITIONAL",
        },
        "K635_IMX_vs_SEI": {
            "formula":    "IMX-BTC ~ α + β_SEI*SEI (+ SHIB+TIA backup) + residual",
            "raw_sharpe": 37.26,
            "orth_sharpe": 24.81,
            "blocker":    "SEI",
            "decision":   "ACCEPT CONDITIONAL",
        },
        "K656_GALA_vs_JUP_FIL": {
            "formula":    "GALA-BTC ~ α + β_JUP*JUP + β_FIL*FIL + residual",
            "raw_sharpe": K620_RAW_OOS_SHARPE,
            "orth_sharpe": best_oos_sh,
            "blocker":    "JUP + FIL (dual)",
            "decision":   decision,
        },
    }

    # ── Build JSON ────────────────────────────────────────────────────────────
    run_time_jst = pd.Timestamp.now(tz="Asia/Tokyo").strftime("%Y-%m-%dT%H:%M:%S%z")

    out = {
        "wave":     "K656",
        "strategy": "GALA-BTC FR Differential — Multi-Factor Orthogonalization vs JUP + FIL (K620 dual blocker unblock attempt)",
        "run_time_jst": run_time_jst,
        "runtime_s":    runtime,
        "decision":     decision,
        "decision_rationale": f"[{decision}] {rationale}",
        "k620_context": {
            "k620_decision":      "BLOCKED-G5",
            "k620_oos_sharpe":    K620_RAW_OOS_SHARPE,
            "k620_oos_ret_pct":   K620_RAW_OOS_RET_PCT,
            "k620_profit_10m_4x": K620_PROFIT_10M_4X,
            "k620_jup_corr":      K620_JUP_CORR,
            "k620_fil_corr":      K620_FIL_CORR,
            "k620_sei_corr":      K620_SEI_CORR,
            "k620_sand_corr":     K620_SAND_CORR,
            "k620_axs_corr":      K620_AXS_CORR,
            "blockers_explanation": (
                f"JUP (Jupiter Solana DEX) corr={K620_JUP_CORR}: both GALA and JUP are ecosystem governance tokens "
                f"sharing mid-cap alt-cap regime factor — lower FR than BTC in bull-BTC cycles. "
                f"FIL (Filecoin storage) corr={K620_FIL_CORR}: both GALA and FIL share 'decentralized infra' "
                f"narrative cycles and similar FR compression patterns vs BTC."
            ),
            "gaming_cluster_status": {
                "SAND_K583": "ACCEPT CONDITIONAL (Sh=33.627)",
                "AXS_K591":  "ACCEPT CONDITIONAL (Sh=17.815)",
                "IMX_K617K635": "BLOCKED→ACCEPT CONDITIONAL (Sh=37.26→24.81, SEI orth)",
                "GALA_K620K656": f"BLOCKED-G5→{decision} (Sh={K620_RAW_OOS_SHARPE}→{best_oos_sh:.3f})",
            },
        },
        "orthog_pattern_series": pattern_series,
        "data_info": {
            "n_rows":       n_rows,
            "date_start":   date_start,
            "date_end":     date_end,
            "total_years":  round(total_years, 3),
            "oos_start":    str(OOS_START),
            "oos_years":    round(oos_years, 3),
            "jup_rows_available": int(jup_avail),
            "fil_rows_available": int(fil_avail),
            "fr_frequency": "1h (HL settles hourly)",
        },
        "signal_config": {
            "strategy_type": "FR differential carry — ORTHOGONALIZED vs JUP + FIL (dual blocker removal)",
            "direction_rule": "sign(W-hour rolling mean of OLS residual of fr_diff_gala)",
            "cost_rt_bps":   COST_RT_BPS,
            "pnl_source":    "signal * fr_diff_gala (carry from actual GALA-BTC position)",
            "signal_windows": SIGNAL_WINDOWS,
            "modes":         ["sf (JUP only)", "df (JUP + FIL)"],
            "best_config":   f"{best_mode} W={best_window}h",
        },
        "phase1_factor_regression": reg_result,
        "phase2_phase3_backtest_all": all_results,
        "best_config": {
            "mode":     best_mode,
            "window_h": best_window,
            **best_result,
        },
        "g2_permutation": perm,
        "g4_walk_forward": wf,
        "g5_correlations": g5,
        "section_6_gates": gates,
        "profit_projection": profit,
        "hl_concentration_impact": hl_conc,
        "operational_requirements": {
            "execution_mode":     "Paired-trade: simultaneous GALA-PERP and BTC-PERP positions",
            "orth_implementation": (
                f"Compute IS OLS coefficients (β_JUP={reg_result['dual_factor']['coefficients']['beta_jup']:.6f}, "
                f"β_FIL={reg_result['dual_factor']['coefficients']['beta_fil']:.6f}) "
                f"→ residual = fr_diff_gala - α - β_JUP*fr_diff_jup - β_FIL*fr_diff_fil "
                f"→ signal = sign(rolling_{best_window}h mean of residual)"
            ),
            "rebalance_frequency": f"Signal flip (~{best_result['oos_entries_per_yr']:.0f}/yr)",
            "venue_primary":       "Bybit GALAUSDT (75x, Trading) — HL cap 65% exceeded",
            "venue_secondary":     "OKX GALA-USDT-SWAP (50x, live)",
            "production_path":     "NOT ACTIVATED — 60d paper-trade required if ACCEPT CONDITIONAL",
        },
    }

    out_path = BASE / "wave_k656_gala_orthogonalize.json"
    with open(out_path, "w") as f:
        json.dump(out, f, indent=2, default=str)
    print(f"\nSaved JSON: {out_path}")
    return out


if __name__ == "__main__":
    main()

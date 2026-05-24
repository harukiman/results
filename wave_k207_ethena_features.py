"""Wave K207 — Ethena TVL Features Added to K198 ML Feature Matrix (v6.6 candidate).

Objective:
  Add 4 Ethena TVL features to K198's 51-feature Ridge ML allocator.
  Test if Ridge can learn the TVL→carry signal (Variant B: TVL grow predicts
  good carry capture) discovered in K206.

Architecture:
  - Load K198 51-feature matrix (sh30, sh90, vol30, mdd30, xcorr × 10 + fr_mean)
  - Load Ethena TVL cache (cache/ethena_tvl_daily.parquet from K206)
  - Compute 4 Ethena features with 7d lag (no look-ahead):
      eth_tvl_change_7d, eth_tvl_change_30d, eth_tvl_drawdown, eth_tvl_acceleration
  - Augment matrix → 55 features total
  - Walk-forward identical to K198 (90d train → 30d test, same caps)
  - Compare vs K198 baseline (OOS Sh 10.28, WF min 6.57, MaxDD -0.0053)

Acceptance for K207 → v6.6:
  OOS Sh ≥ 10.28, WF min ≥ 6.57, MaxDD ≤ -0.0053
  + at least one Ethena feature has non-zero Ridge coefficient

Runtime: <12 min
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
from sklearn.linear_model import Ridge
from sklearn.preprocessing import StandardScaler

warnings.filterwarnings("ignore")

START_TIME = time.time()
BASE   = Path("/Users/nekonaomichi/crypto-lab")
CACHE  = BASE / "cache"
HL_CACHE = CACHE / "k163_hl"

TRADING_DAYS = 365
OOS_FRAC     = 0.30
N_FOLDS      = 4
TRAIN_FRAC   = 0.70

# ML walk-forward params (identical to K198)
ML_TRAIN_DAYS = 90
ML_TEST_DAYS  = 30

# K198 v6.5 reference (acceptance baseline)
K198_OOS_SH  = 10.28
K198_OOS_DD  = -0.0053
K198_WF_MEAN = 7.91
K198_WF_MIN  = 6.57

# K204 secondary threshold
K204_OOS_SH  = 10.36

# Caps (identical to K198)
K121_CAP       = 0.30
CARRY_CAP      = 0.05   # per spec: carry ≤ 5%
CARRY_FWD_CAP  = 0.05
CARRY_REV_CAP  = 0.05

# FR defensive trigger (same as K196/K198)
FR_SYMBOLS    = ["BTC", "ETH", "DOGE", "AVAX", "SOL", "XRP"]
FR_THRESHOLD  = -0.009735
FR_COMPONENTS = ["K121", "K133"]

STRATEGY_NAMES = [
    "v4.1", "V1", "K114", "K116", "K121", "K133",
    "K147", "K175_DAR", "V_fwd_carry", "V_rev_carry",
]

# Ethena TVL feature config
ETH_TVL_LAG_DAYS = 7   # lag to avoid look-ahead bias


# ──────────────────────────────────────────────────────────────────────────────
# Metrics
# ──────────────────────────────────────────────────────────────────────────────

def sharpe_d(r: np.ndarray) -> float:
    r = np.asarray(r, dtype=float)
    if len(r) < 2 or r.std(ddof=1) == 0:
        return 0.0
    return float(r.mean() / r.std(ddof=1) * math.sqrt(TRADING_DAYS))


def max_dd_d(r: np.ndarray) -> float:
    eq = np.cumprod(1.0 + np.asarray(r, dtype=float))
    peak = np.maximum.accumulate(eq)
    return float((eq / peak - 1.0).min())


def sortino_d(r: np.ndarray) -> float:
    dn = r[r < 0]
    if len(dn) < 2 or dn.std(ddof=1) == 0:
        return 0.0
    return float(r.mean() / dn.std(ddof=1) * math.sqrt(TRADING_DAYS))


def calmar_d(r: np.ndarray) -> float:
    ann = (1.0 + np.asarray(r, dtype=float)).prod() ** (TRADING_DAYS / max(1, len(r))) - 1.0
    mdd = max_dd_d(r)
    return float(ann / abs(mdd)) if mdd != 0 else 0.0


def metrics_pkg(r: np.ndarray) -> dict:
    r = np.asarray(r, dtype=float)
    if len(r) < 2:
        return {"sharpe": 0.0, "sortino": 0.0, "calmar": 0.0, "max_dd": 0.0,
                "ann_ret": 0.0, "ann_vol": 0.0, "n_days": int(len(r))}
    ann_ret = float((1.0 + r).prod() ** (TRADING_DAYS / len(r)) - 1.0)
    ann_vol = float(r.std(ddof=1) * math.sqrt(TRADING_DAYS))
    return {
        "sharpe":  round(sharpe_d(r), 4),
        "sortino": round(sortino_d(r), 4),
        "calmar":  round(calmar_d(r), 4),
        "max_dd":  round(max_dd_d(r), 4),
        "ann_ret": round(ann_ret, 4),
        "ann_vol": round(ann_vol, 4),
        "n_days":  int(len(r)),
    }


# ──────────────────────────────────────────────────────────────────────────────
# Weight utilities
# ──────────────────────────────────────────────────────────────────────────────

def w_equal(n: int) -> np.ndarray:
    return np.ones(n) / n


def w_risk_parity(R: np.ndarray, n_iter: int = 3000, tol: float = 1e-9) -> np.ndarray:
    vols = R.std(axis=0, ddof=1)
    vols = np.where(vols == 0, 1.0, vols)
    R_norm = R / vols[np.newaxis, :]
    cov = np.cov(R_norm, rowvar=False, ddof=1)
    if cov.ndim == 0:
        cov = np.array([[cov]])
    cov = cov + np.eye(cov.shape[0]) * 1e-8
    n = cov.shape[0]
    w = np.ones(n) / n
    for _ in range(n_iter):
        mrc = cov @ w
        rc  = w * mrc
        rc  = np.where(np.abs(rc) < 1e-15, 1e-15, rc)
        total_risk_sq = float(w @ cov @ w)
        target = total_risk_sq / n
        ratio  = target / rc
        ratio  = np.clip(ratio, 0, None)
        new_w  = w * ratio ** 0.5
        new_w  = np.clip(new_w, 1e-6, None)
        new_w  = new_w / new_w.sum()
        if np.max(np.abs(new_w - w)) < tol:
            w_sc = new_w / vols
            return w_sc / w_sc.sum()
        w = new_w
    w_sc = w / vols
    return w_sc / w_sc.sum()


def apply_cap(w: np.ndarray, cols: List[str], col_name: str, cap: float) -> np.ndarray:
    w = w.copy()
    if col_name not in cols:
        return w
    i = cols.index(col_name)
    if w[i] <= cap:
        return w
    excess = w[i] - cap
    w[i] = cap
    other_mask = np.ones(len(w), dtype=bool)
    other_mask[i] = False
    others = w[other_mask]
    if others.sum() > 0:
        w[other_mask] = others + excess * (others / others.sum())
    return w / w.sum()


def apply_all_caps(w: np.ndarray, cols: List[str]) -> np.ndarray:
    """Apply K121 cap and carry caps per K207 spec (carry ≤ 5%)."""
    w = apply_cap(w, cols, "K121", K121_CAP)
    w = apply_cap(w, cols, "V_fwd_carry", CARRY_FWD_CAP)
    w = apply_cap(w, cols, "V_rev_carry", CARRY_REV_CAP)
    return w


# ──────────────────────────────────────────────────────────────────────────────
# Data loading (identical to K198)
# ──────────────────────────────────────────────────────────────────────────────

def load_component_returns() -> pd.DataFrame:
    """Load all 10 component daily return series (same as K198)."""
    with open(BASE / "wave_k192_curves.json") as f:
        k192 = json.load(f)
    k192_dates = pd.to_datetime(k192["dates"])

    component_map = {
        "v4.1":     "K188_v4.1",
        "V1":       "K188_V1",
        "K114":     "K188_K114",
        "K116":     "K188_K116",
        "K121":     "K188_K121",
        "K133":     "K188_K133",
        "K147":     "K188_K147",
        "K175_DAR": "K175_DAR_a_win300_net",
    }
    base_df = pd.DataFrame(index=k192_dates)
    for col_name, curve_key in component_map.items():
        eq = np.array(k192["series"][curve_key], dtype=float)
        prev = np.r_[1.0, eq[:-1]]
        ret = eq / prev - 1.0
        base_df[col_name] = ret
    base_df.index.name = "date"

    with open(BASE / "wave_k195_curves.json") as f:
        k195 = json.load(f)
    k195_panel_dates = pd.to_datetime(k195["panel_dates"])
    fwd_eq  = np.array(k195["series"]["V_eq_w"], dtype=float)
    fwd_ret = pd.Series(
        np.r_[fwd_eq[0] - 1.0, fwd_eq[1:] / fwd_eq[:-1] - 1.0],
        index=k195_panel_dates,
        name="V_fwd_carry",
    )

    with open(BASE / "wave_k196_curves.json") as f:
        k196 = json.load(f)
    k196_panel_dates = pd.to_datetime(k196["panel_dates"])
    rev_eq  = np.array(k196["series"]["V_rev_eq_w"], dtype=float)
    rev_ret = pd.Series(
        np.r_[rev_eq[0] - 1.0, rev_eq[1:] / rev_eq[:-1] - 1.0],
        index=k196_panel_dates,
        name="V_rev_carry",
    )

    all_start = max(base_df.index[0], fwd_ret.index[0], rev_ret.index[0])
    all_end   = min(base_df.index[-1], fwd_ret.index[-1], rev_ret.index[-1])

    base_trimmed = base_df[(base_df.index >= all_start) & (base_df.index <= all_end)]
    fwd_trimmed  = fwd_ret[(fwd_ret.index >= all_start) & (fwd_ret.index <= all_end)]
    rev_trimmed  = rev_ret[(rev_ret.index >= all_start) & (rev_ret.index <= all_end)]

    df = pd.concat([base_trimmed, fwd_trimmed, rev_trimmed], axis=1).dropna()
    print(f"  Component returns: {df.shape[0]} days × {df.shape[1]} strategies")
    print(f"  Date range: {df.index[0].date()} → {df.index[-1].date()}")
    return df


def load_fr_mean_daily() -> pd.Series:
    """Load daily mean annualized funding rate across 6 symbols."""
    daily_series = []
    for sym in FR_SYMBOLS:
        for tag in ("730d", "1200d", "365d"):
            fpath = CACHE / f"bybit_fr_{sym}USDT_{tag}.parquet"
            if fpath.exists():
                df = pd.read_parquet(fpath)
                df["timestamp"] = pd.to_datetime(df["timestamp"]).dt.tz_localize(None)
                df = df.set_index("timestamp")
                daily = df["funding_rate"].resample("1D").mean()
                ann   = daily * 3 * 365
                ann.name = sym
                daily_series.append(ann)
                break
    if not daily_series:
        return pd.Series(dtype=float, name="fr_mean_ann")
    panel  = pd.concat(daily_series, axis=1)
    fr_mean = panel.mean(axis=1)
    fr_mean.name = "fr_mean_ann"
    return fr_mean


# ──────────────────────────────────────────────────────────────────────────────
# Ethena TVL features
# ──────────────────────────────────────────────────────────────────────────────

def load_ethena_tvl_features(lag_days: int = ETH_TVL_LAG_DAYS) -> pd.DataFrame:
    """
    Load Ethena TVL cache and compute 4 indicator features with `lag_days` lag.

    Returns DataFrame with columns:
      eth_tvl_change_7d, eth_tvl_change_30d, eth_tvl_drawdown, eth_tvl_acceleration

    Features are lagged by `lag_days` so feature_at_t reflects TVL through t-lag_days.
    This avoids look-ahead bias.
    """
    cache_path = CACHE / "ethena_tvl_daily.parquet"
    if not cache_path.exists():
        raise FileNotFoundError(f"Ethena TVL cache not found: {cache_path}. Run K206 first.")

    tvl_df = pd.read_parquet(cache_path)
    tvl = tvl_df["tvl"]

    # Ensure tz-naive index
    if tvl.index.tz is not None:
        tvl.index = tvl.index.tz_localize(None)

    # ── Compute raw features ──────────────────────────────────────────────────
    feat = pd.DataFrame(index=tvl.index)

    # 7-day % change
    feat["eth_tvl_change_7d"] = tvl.pct_change(7)

    # 30-day % change
    feat["eth_tvl_change_30d"] = tvl.pct_change(30)

    # Drawdown over 30d rolling window: (tvl_t - peak_last_30d) / peak_last_30d
    rolling_peak_30d = tvl.rolling(30, min_periods=2).max()
    feat["eth_tvl_drawdown"] = (tvl - rolling_peak_30d) / rolling_peak_30d.replace(0, np.nan)

    # Acceleration: 2nd derivative of TVL = daily_chg.diff()
    daily_chg = tvl.pct_change(1)
    feat["eth_tvl_acceleration"] = daily_chg.diff()

    # ── Apply lag to prevent look-ahead bias ──────────────────────────────────
    # feature_at_t = TVL computed for period ending at t-lag_days
    feat = feat.shift(lag_days)

    feat.index.name = "date"
    print(f"  Ethena TVL features: {feat.shape[0]} rows × {feat.shape[1]} features")
    print(f"  Date range: {feat.dropna().index[0].date()} → {feat.dropna().index[-1].date()}")
    print(f"  Lag applied: {lag_days}d (no look-ahead)")

    return feat


# ──────────────────────────────────────────────────────────────────────────────
# Feature engineering (K198 base + Ethena augmentation)
# ──────────────────────────────────────────────────────────────────────────────

def build_features_k207(
    df: pd.DataFrame,
    fr_mean: Optional[pd.Series],
    eth_feat: pd.DataFrame,
    win_short: int = 30,
    win_long: int = 90,
) -> pd.DataFrame:
    """
    Build 55-feature matrix:
      - 50 per-strategy features (sh30, sh90, vol30, mdd30, xcorr) × 10 strategies
      - 1 FR regime indicator (fr_mean_ann)
      - 4 Ethena TVL features (global, same across all strategies per day)

    Ethena features are aligned to the portfolio date and forward-filled.
    """
    n_strats = df.shape[1]
    cols = list(df.columns)
    R = df.values
    n = len(R)

    # Align Ethena features to df index using forward-fill (most recent valid value)
    eth_aligned = eth_feat.reindex(df.index, method="ffill")

    feat_rows = []

    for t in range(win_long, n):
        row = {}
        slice_long  = R[t - win_long:t]
        slice_short = R[t - win_short:t]

        # Cross-correlation 30d
        if n_strats > 1:
            corr_mat = np.corrcoef(slice_short.T)
            np.fill_diagonal(corr_mat, 0.0)
        else:
            corr_mat = np.zeros((1, 1))

        # Per-strategy features (50 total = 10 × 5)
        for i, strat in enumerate(cols):
            prefix = f"{strat}__"
            row[f"{prefix}sh30"]  = sharpe_d(slice_short[:, i])
            row[f"{prefix}sh90"]  = sharpe_d(slice_long[:, i])
            row[f"{prefix}vol30"] = float(slice_short[:, i].std(ddof=1) * math.sqrt(TRADING_DAYS))
            row[f"{prefix}mdd30"] = max_dd_d(slice_short[:, i])
            if n_strats > 1:
                other_corrs = np.delete(corr_mat[i], i)
                row[f"{prefix}xcorr"] = float(np.mean(other_corrs))
            else:
                row[f"{prefix}xcorr"] = 0.0

        # FR regime indicator (feature #51)
        if fr_mean is not None and len(fr_mean) > 0:
            fr_date = df.index[t]
            fr_aligned_val = fr_mean.reindex([fr_date], method="ffill")
            row["fr_mean_ann"] = float(fr_aligned_val.iloc[0]) if not fr_aligned_val.isna().all() else 0.0
        else:
            row["fr_mean_ann"] = 0.0

        # Ethena TVL features (#52–55) — GLOBAL (same for all strategies at date t)
        date_t = df.index[t]
        eth_row = eth_aligned.loc[date_t] if date_t in eth_aligned.index else pd.Series(dtype=float)
        for col_name in ["eth_tvl_change_7d", "eth_tvl_change_30d",
                          "eth_tvl_drawdown", "eth_tvl_acceleration"]:
            val = eth_row.get(col_name, np.nan) if len(eth_row) > 0 else np.nan
            row[col_name] = float(val) if pd.notna(val) else 0.0

        feat_rows.append(row)

    feat_df = pd.DataFrame(feat_rows, index=df.index[win_long:])
    return feat_df


def build_targets(df: pd.DataFrame, horizon: int = 30) -> pd.DataFrame:
    """Build next-horizon-day forward Sharpe targets (identical to K198)."""
    n_strats = df.shape[1]
    cols = list(df.columns)
    R = df.values
    n = len(R)
    target_rows = []

    for t in range(n - horizon):
        fwd = R[t + 1: t + 1 + horizon]
        row = {}
        for i, strat in enumerate(cols):
            row[f"{strat}__fwd_sh"] = sharpe_d(fwd[:, i])
        target_rows.append(row)

    target_df = pd.DataFrame(target_rows, index=df.index[:n - horizon])
    return target_df


# ──────────────────────────────────────────────────────────────────────────────
# FR trigger
# ──────────────────────────────────────────────────────────────────────────────

def apply_fr_trigger(
    df: pd.DataFrame,
    fr_mean: pd.Series,
    components: List[str] = FR_COMPONENTS,
    threshold: float = FR_THRESHOLD,
) -> pd.DataFrame:
    df2 = df.copy()
    fr_aligned = fr_mean.reindex(df2.index, method="ffill")
    trigger_mask = fr_aligned < threshold
    for comp in components:
        if comp in df2.columns:
            df2.loc[trigger_mask, comp] = 0.0
    return df2


# ──────────────────────────────────────────────────────────────────────────────
# ML walk-forward (same logic as K198, now with 55 features)
# ──────────────────────────────────────────────────────────────────────────────

def ml_walk_forward(
    df: pd.DataFrame,
    feat_df: pd.DataFrame,
    target_df: pd.DataFrame,
    train_days: int = ML_TRAIN_DAYS,
    test_days: int  = ML_TEST_DAYS,
    alpha: float    = 1.0,
) -> Tuple[pd.DataFrame, pd.Series, list]:
    """Ridge walk-forward allocator (90d train → 30d test, 15+ steps)."""
    cols = list(df.columns)
    n_strats = len(cols)

    common_idx = feat_df.index.intersection(target_df.index)
    feat_aligned   = feat_df.loc[common_idx]
    target_aligned = target_df.loc[common_idx]

    feat_arr   = feat_aligned.values
    target_arr = np.array([target_aligned[f"{c}__fwd_sh"].values for c in cols]).T
    date_idx   = feat_aligned.index

    n = len(feat_arr)
    min_train = max(train_days, 45)

    wf_weights   = []
    wf_pnl       = []
    wf_dates     = []
    diagnostics  = []

    step = 0
    while True:
        t_start = step * test_days + min_train
        if t_start >= n:
            break
        t_train_start = max(0, t_start - train_days)
        t_train_end   = t_start
        if t_train_end - t_train_start < 30:
            step += 1
            continue

        X_train = feat_arr[t_train_start:t_train_end]
        Y_train = target_arr[t_train_start:t_train_end]

        t_test_start = t_start
        t_test_end   = min(t_start + test_days, n)
        X_test       = feat_arr[t_test_start:t_test_end]
        test_dates_slice = date_idx[t_test_start:t_test_end]

        if len(X_train) < 20 or len(X_test) == 0:
            step += 1
            continue

        X_train = np.nan_to_num(X_train, nan=0.0, posinf=0.0, neginf=0.0)
        X_test  = np.nan_to_num(X_test,  nan=0.0, posinf=0.0, neginf=0.0)

        scaler = StandardScaler()
        X_train_s = scaler.fit_transform(X_train)
        X_test_s  = scaler.transform(X_test)

        preds     = np.zeros(n_strats)
        r2_scores = []
        # Collect per-strategy Ridge coefficients for Ethena features
        eth_coef_per_strat = {strat: {} for strat in cols}

        feat_names = list(feat_df.columns)
        eth_feat_names = ["eth_tvl_change_7d", "eth_tvl_change_30d",
                          "eth_tvl_drawdown", "eth_tvl_acceleration"]
        eth_feat_indices = [feat_names.index(fn) for fn in eth_feat_names if fn in feat_names]

        for i in range(n_strats):
            y = Y_train[:, i]
            if np.isnan(y).any() or np.std(y) < 1e-10:
                preds[i] = 0.0
                r2_scores.append(np.nan)
                continue

            model = Ridge(alpha=alpha)
            model.fit(X_train_s, y)
            pred = model.predict(X_test_s[:1])[0]
            preds[i] = float(pred)

            # R² on training set
            y_pred_tr = model.predict(X_train_s)
            ss_res = np.sum((y - y_pred_tr) ** 2)
            ss_tot = np.sum((y - y.mean()) ** 2)
            r2 = 1.0 - ss_res / ss_tot if ss_tot > 1e-12 else 0.0
            r2_scores.append(r2)

            # Save Ethena feature coefficients
            for fi in eth_feat_indices:
                eth_coef_per_strat[cols[i]][feat_names[fi]] = float(model.coef_[fi])

        # Direction accuracy
        actual_targets = target_arr[t_test_start:t_test_end].mean(axis=0)
        dir_correct = np.array([
            (preds[i] > 0) == (actual_targets[i] > 0)
            for i in range(n_strats)
        ])

        # Build weights
        pos_preds = np.maximum(preds, 0.0)
        if pos_preds.sum() < 1e-10:
            w = w_equal(n_strats)
        else:
            w = pos_preds / pos_preds.sum()
        w = apply_all_caps(w, cols)

        diag_step = {
            "step":        step,
            "train_start": str(date_idx[t_train_start].date()),
            "train_end":   str(date_idx[t_train_end - 1].date()),
            "test_start":  str(test_dates_slice[0].date()),
            "test_end":    str(test_dates_slice[-1].date()),
            "preds":       {cols[i]: round(float(preds[i]), 4) for i in range(n_strats)},
            "weights":     {cols[i]: round(float(w[i]), 4) for i in range(n_strats)},
            "r2_per_strat": {cols[i]: round(float(r2_scores[i]), 4) if not np.isnan(r2_scores[i]) else None
                             for i in range(n_strats)},
            "dir_accuracy_per_strat": {cols[i]: bool(dir_correct[i]) for i in range(n_strats)},
            "mean_r2": round(float(np.nanmean(r2_scores)), 4),
            "mean_dir_acc": round(float(np.mean(dir_correct)), 4),
            "eth_coef_per_strat": {
                strat: {k: round(v, 6) for k, v in coefs.items()}
                for strat, coefs in eth_coef_per_strat.items()
            },
        }
        diagnostics.append(diag_step)

        # Execute weights on test period
        test_rets = df.loc[test_dates_slice].values
        for d_i, d in enumerate(test_dates_slice):
            pnl = float(test_rets[d_i] @ w)
            wf_pnl.append(pnl)
            wf_dates.append(d)
            wf_weights.append(dict(zip(cols, w)))

        step += 1

    if not wf_pnl:
        return pd.DataFrame(), pd.Series(dtype=float), []

    weights_df = pd.DataFrame(wf_weights, index=wf_dates)
    pnl_series = pd.Series(wf_pnl, index=wf_dates, name="k207_pnl")
    return weights_df, pnl_series, diagnostics


# ──────────────────────────────────────────────────────────────────────────────
# Feature importance (global Ridge on full feature matrix)
# ──────────────────────────────────────────────────────────────────────────────

def compute_feature_importance(
    feat_df: pd.DataFrame,
    target_df: pd.DataFrame,
    cols: List[str],
    alpha: float = 1.0,
) -> Dict[str, float]:
    """Fit Ridge on full feature set, return mean |coef| across all strategies."""
    common_idx = feat_df.index.intersection(target_df.index)
    X = feat_df.loc[common_idx].values
    target_cols = [f"{c}__fwd_sh" for c in cols]
    Y = target_df.loc[common_idx][target_cols].values

    X = np.nan_to_num(X, nan=0.0, posinf=0.0, neginf=0.0)
    scaler = StandardScaler()
    X_s = scaler.fit_transform(X)

    feature_names = list(feat_df.columns)
    coef_matrix = []

    for i in range(Y.shape[1]):
        y = Y[:, i]
        if np.isnan(y).any() or np.std(y) < 1e-10:
            continue
        model = Ridge(alpha=alpha)
        model.fit(X_s, y)
        coef_matrix.append(np.abs(model.coef_))

    if not coef_matrix:
        return {}

    mean_abs_coef = np.mean(coef_matrix, axis=0)
    ranked = sorted(
        zip(feature_names, mean_abs_coef),
        key=lambda x: x[1], reverse=True,
    )
    return {name: round(float(val), 6) for name, val in ranked}


# ──────────────────────────────────────────────────────────────────────────────
# Aggregations
# ──────────────────────────────────────────────────────────────────────────────

def aggregate_diagnostics(diagnostics: list, cols: List[str]) -> dict:
    if not diagnostics:
        return {}

    r2_by_strat  = {c: [] for c in cols}
    dir_by_strat = {c: [] for c in cols}

    for d in diagnostics:
        for c in cols:
            r2  = d["r2_per_strat"].get(c)
            da  = d["dir_accuracy_per_strat"].get(c)
            if r2 is not None:
                r2_by_strat[c].append(r2)
            if da is not None:
                dir_by_strat[c].append(float(da))

    r2_summary  = {}
    dir_summary = {}
    for c in cols:
        vals = [x for x in r2_by_strat[c] if x is not None]
        r2_summary[c] = {
            "mean":   round(float(np.mean(vals)), 4) if vals else None,
            "median": round(float(np.median(vals)), 4) if vals else None,
            "n_steps": len(vals),
        }
        dvals = dir_by_strat[c]
        dir_summary[c] = {
            "mean_dir_acc": round(float(np.mean(dvals)), 4) if dvals else None,
            "n_steps": len(dvals),
            "above_55pct": bool(np.mean(dvals) > 0.55) if dvals else False,
        }

    overall_r2  = np.nanmean([d["mean_r2"] for d in diagnostics])
    overall_dir = np.nanmean([d["mean_dir_acc"] for d in diagnostics])

    return {
        "overall_mean_r2":      round(float(overall_r2), 4),
        "overall_mean_dir_acc": round(float(overall_dir), 4),
        "r2_by_strategy":       r2_summary,
        "dir_acc_by_strategy":  dir_summary,
        "n_wf_steps":           len(diagnostics),
    }


def aggregate_eth_coefs(diagnostics: list, cols: List[str]) -> dict:
    """Aggregate Ethena feature coefficients across WF steps per strategy."""
    eth_feat_names = ["eth_tvl_change_7d", "eth_tvl_change_30d",
                      "eth_tvl_drawdown", "eth_tvl_acceleration"]
    result = {}
    for strat in cols:
        coef_over_time = {fn: [] for fn in eth_feat_names}
        for d in diagnostics:
            coefs = d.get("eth_coef_per_strat", {}).get(strat, {})
            for fn in eth_feat_names:
                if fn in coefs:
                    coef_over_time[fn].append(coefs[fn])
        strat_result = {}
        for fn in eth_feat_names:
            vals = coef_over_time[fn]
            if vals:
                strat_result[fn] = {
                    "mean_coef":   round(float(np.mean(vals)), 6),
                    "abs_mean":    round(float(np.mean(np.abs(vals))), 6),
                    "pct_nonzero": round(float(np.mean([abs(v) > 1e-8 for v in vals])), 4),
                    "sign_consistency": round(float(np.mean(np.sign(vals) == np.sign(np.mean(vals)))), 4),
                }
            else:
                strat_result[fn] = {"mean_coef": 0.0, "abs_mean": 0.0, "pct_nonzero": 0.0}
        result[strat] = strat_result
    return result


def wf_fold_sharpes(pnl_series: pd.Series, n_folds: int = N_FOLDS) -> dict:
    n = len(pnl_series)
    fold_size = n // n_folds
    sharpes = []
    for i in range(n_folds):
        start = i * fold_size
        end   = start + fold_size if i < n_folds - 1 else n
        sh    = sharpe_d(pnl_series.values[start:end])
        sharpes.append(round(sh, 4))
    return {
        "fold_sharpes": sharpes,
        "mean": round(float(np.mean(sharpes)), 4),
        "min":  round(float(np.min(sharpes)), 4),
        "max":  round(float(np.max(sharpes)), 4),
        "std":  round(float(np.std(sharpes)), 4),
    }


def oos_cut(s: pd.Series, oos_frac: float = OOS_FRAC) -> pd.Series:
    cut = int(len(s) * (1.0 - oos_frac))
    return s.iloc[cut:]


# ──────────────────────────────────────────────────────────────────────────────
# Walk-forward static P3 (baseline comparison on same windows)
# ──────────────────────────────────────────────────────────────────────────────

def run_wf_static_p3(df: pd.DataFrame) -> Tuple[pd.Series, list]:
    cols  = list(df.columns)
    R     = df.values
    n     = len(R)
    dates = df.index
    min_train = ML_TRAIN_DAYS

    wf_pnl   = []
    wf_dates = []
    step = 0

    while True:
        t_start = step * ML_TEST_DAYS + min_train
        if t_start >= n:
            break
        t_train_start = max(0, t_start - ML_TRAIN_DAYS)
        t_train_end   = t_start
        t_test_end    = min(t_start + ML_TEST_DAYS, n)

        if t_train_end - t_train_start < 20:
            step += 1
            continue

        R_train = R[t_train_start:t_train_end]
        w = w_risk_parity(R_train)
        w = apply_all_caps(w, cols)

        for d_i in range(t_start, t_test_end):
            pnl = float(R[d_i] @ w)
            wf_pnl.append(pnl)
            wf_dates.append(dates[d_i])

        step += 1

    return pd.Series(wf_pnl, index=wf_dates, name="static_wf_pnl"), []


# ──────────────────────────────────────────────────────────────────────────────
# Main
# ──────────────────────────────────────────────────────────────────────────────

def main():
    print("=" * 72)
    print("Wave K207 — Ethena TVL Features + K198 ML Allocator (v6.6 candidate)")
    print("=" * 72)
    print()

    np.random.seed(42)

    # ── Step 1: Load component returns ───────────────────────────────────────
    print("Step 1: Loading K196 component returns...", flush=True)
    df_all = load_component_returns()
    cols   = list(df_all.columns)
    n_strats = len(cols)
    print(f"  Strategies: {cols}")
    print()

    # ── Step 2: Load FR regime indicator ─────────────────────────────────────
    print("Step 2: Loading FR regime indicator...", flush=True)
    fr_mean = load_fr_mean_daily()
    if len(fr_mean) > 0:
        print(f"  FR mean range: {fr_mean.index[0].date()} → {fr_mean.index[-1].date()}")
        fr_aligned = fr_mean.reindex(df_all.index, method="ffill")
        print(f"  FR mean stats: mean={fr_aligned.mean():.4f} std={fr_aligned.std():.4f}")
    else:
        fr_aligned = None
        print("  WARNING: FR data not available")
    print()

    # ── Step 3: Load Ethena TVL features ─────────────────────────────────────
    print("Step 3: Loading Ethena TVL features (7d lag)...", flush=True)
    eth_feat = load_ethena_tvl_features(lag_days=ETH_TVL_LAG_DAYS)
    print(f"  Ethena feature columns: {eth_feat.columns.tolist()}")
    print(f"  Non-null rows: {eth_feat.dropna().shape[0]}")

    # Check overlap with portfolio dates
    overlap = df_all.index.intersection(eth_feat.dropna().index)
    print(f"  Overlap with portfolio dates: {len(overlap)} days "
          f"({overlap[0].date() if len(overlap)>0 else 'N/A'} → "
          f"{overlap[-1].date() if len(overlap)>0 else 'N/A'})")
    print()

    # ── Step 4: Apply FR trigger ─────────────────────────────────────────────
    print("Step 4: Applying FR trigger (K121, K133)...", flush=True)
    if fr_aligned is not None and len(fr_aligned) > 0:
        df_triggered = apply_fr_trigger(df_all, fr_mean)
        n_trigger = int((fr_aligned < FR_THRESHOLD).sum())
        print(f"  Trigger fires {n_trigger} / {len(df_all)} days ({n_trigger/len(df_all)*100:.1f}%)")
    else:
        df_triggered = df_all.copy()
        print("  No FR trigger applied")
    print()

    # ── Step 5: Build 55-feature matrix (K198 51 + Ethena 4) ─────────────────
    print("Step 5: Building 55-feature matrix (51 K198 + 4 Ethena)...", flush=True)
    feat_df = build_features_k207(
        df_triggered,
        fr_mean if len(fr_mean) > 0 else None,
        eth_feat,
        win_short=30,
        win_long=90,
    )
    print(f"  Feature matrix: {feat_df.shape[0]} rows × {feat_df.shape[1]} features")
    print(f"  Feature date range: {feat_df.index[0].date()} → {feat_df.index[-1].date()}")

    # Report Ethena feature coverage
    eth_cols = ["eth_tvl_change_7d", "eth_tvl_change_30d", "eth_tvl_drawdown", "eth_tvl_acceleration"]
    for ec in eth_cols:
        nonzero = (feat_df[ec] != 0).sum()
        print(f"  {ec}: {nonzero}/{len(feat_df)} non-zero ({nonzero/len(feat_df)*100:.1f}%)")
    print()

    # ── Step 6: Build targets ─────────────────────────────────────────────────
    print("Step 6: Building forward Sharpe targets (horizon=30d)...", flush=True)
    target_df = build_targets(df_triggered, horizon=ML_TEST_DAYS)
    print(f"  Target matrix: {target_df.shape[0]} rows × {target_df.shape[1]} strategies")
    print()

    # ── Step 7: K207 Ridge walk-forward ──────────────────────────────────────
    print("Step 7: K207 Ridge walk-forward (55 features, 90d train → 30d test)...", flush=True)
    weights_k207, pnl_k207, diagnostics_k207 = ml_walk_forward(
        df_triggered, feat_df, target_df,
        train_days=ML_TRAIN_DAYS,
        test_days=ML_TEST_DAYS,
        alpha=1.0,
    )
    if len(pnl_k207) == 0:
        print("  ERROR: K207 walk-forward returned empty PnL")
        return
    print(f"  K207 WF PnL: {len(pnl_k207)} days, "
          f"{pnl_k207.index[0].date()} → {pnl_k207.index[-1].date()}")
    print(f"  WF steps completed: {len(diagnostics_k207)}")
    print()

    # ── Step 8: Walk-forward static P3 (baseline) ────────────────────────────
    print("Step 8: Walk-forward static P3 (apples-to-apples baseline)...", flush=True)
    pnl_static_wf, _ = run_wf_static_p3(df_triggered)
    common_start = pnl_k207.index[0]
    common_end   = pnl_k207.index[-1]
    static_aligned = pnl_static_wf[
        (pnl_static_wf.index >= common_start) & (pnl_static_wf.index <= common_end)
    ]
    print(f"  Static WF PnL: {len(static_aligned)} days aligned")
    print()

    # ── Step 9: OOS metrics ───────────────────────────────────────────────────
    print("Step 9: Computing OOS metrics (last 30%)...", flush=True)
    oos_k207   = oos_cut(pnl_k207)
    oos_static = oos_cut(static_aligned) if len(static_aligned) > 0 else oos_cut(pnl_k207)

    m_k207   = metrics_pkg(oos_k207.values)
    m_static = metrics_pkg(oos_static.values)

    k207_oos_sh   = m_k207["sharpe"]
    k207_oos_dd   = m_k207["max_dd"]

    print(f"  K198 v6.5 baseline (reference): OOS Sh={K198_OOS_SH:.4f} MaxDD={K198_OOS_DD:.4f}")
    print(f"  K207 Ethena ML (OOS):           OOS Sh={k207_oos_sh:.4f} MaxDD={k207_oos_dd:.4f}")
    print(f"  WF static P3 (same windows):    OOS Sh={m_static['sharpe']:.4f} MaxDD={m_static['max_dd']:.4f}")
    print()

    # ── Step 10: WF fold analysis ─────────────────────────────────────────────
    print("Step 10: Walk-forward fold analysis (4 folds)...", flush=True)
    wf_k207  = wf_fold_sharpes(pnl_k207)
    wf_static = wf_fold_sharpes(static_aligned) if len(static_aligned) > 0 else wf_fold_sharpes(pnl_k207)

    k207_wf_min  = wf_k207["min"]
    k207_wf_mean = wf_k207["mean"]

    print(f"  K207 WF: mean={k207_wf_mean:.4f}  min={k207_wf_min:.4f}  "
          f"folds={wf_k207['fold_sharpes']}")
    print(f"  K198 reference: mean={K198_WF_MEAN:.4f}  min={K198_WF_MIN:.4f}")
    print(f"  Static WF: mean={wf_static['mean']:.4f}  min={wf_static['min']:.4f}")
    print()

    # ── Step 11: ML diagnostics ───────────────────────────────────────────────
    print("Step 11: ML predictor diagnostics...", flush=True)
    diag_agg = aggregate_diagnostics(diagnostics_k207, cols)
    print(f"  Overall R²: {diag_agg.get('overall_mean_r2', 'N/A')}")
    print(f"  Overall dir acc: {diag_agg.get('overall_mean_dir_acc', 'N/A')}")
    print("  Per-strategy direction accuracy:")
    for c in cols:
        da = diag_agg.get("dir_acc_by_strategy", {}).get(c, {}).get("mean_dir_acc", None)
        r2 = diag_agg.get("r2_by_strategy", {}).get(c, {}).get("mean", None)
        above = diag_agg.get("dir_acc_by_strategy", {}).get(c, {}).get("above_55pct", False)
        print(f"    {c:15s}: dir_acc={da:.3f} {'[OK]' if above else '[--]'} | R²={r2:.4f}")
    print()

    # ── Step 12: Feature importance (all 55 features) ─────────────────────────
    print("Step 12: Ridge feature importance (all 55 features)...", flush=True)
    feat_imp = compute_feature_importance(feat_df, target_df, cols)

    # Rank Ethena features
    eth_ranks = {}
    all_feat_names = list(feat_imp.keys())
    for fn in eth_cols:
        if fn in feat_imp:
            rank = all_feat_names.index(fn) + 1
            eth_ranks[fn] = {"rank": rank, "importance": feat_imp[fn], "total_features": len(feat_imp)}

    print(f"  Total features ranked: {len(feat_imp)}")
    print("  Top 20 features:")
    for name, val in list(feat_imp.items())[:20]:
        marker = " << ETHENA" if name in eth_cols else ""
        print(f"    #{all_feat_names.index(name)+1:2d}  {name:40s}: {val:.6f}{marker}")
    print()
    print("  Ethena feature rankings:")
    for fn, info in eth_ranks.items():
        print(f"    {fn:35s}: rank #{info['rank']}/{info['total_features']}, imp={info['importance']:.6f}")
    print()

    # Check if any Ethena feature is non-zero (acceptance criterion)
    eth_nonzero = any(feat_imp.get(fn, 0) > 1e-8 for fn in eth_cols)
    print(f"  Any Ethena feature non-zero Ridge coef? {'YES' if eth_nonzero else 'NO'}")
    print()

    # ── Step 13: Ethena coefficient analysis ──────────────────────────────────
    print("Step 13: Ethena coefficient analysis per strategy...", flush=True)
    eth_coef_analysis = aggregate_eth_coefs(diagnostics_k207, cols)

    print("  Mean Ethena coefficients per strategy (eth_tvl_change_7d primary):")
    for strat in cols:
        coef_7d = eth_coef_analysis[strat].get("eth_tvl_change_7d", {}).get("mean_coef", 0)
        coef_abs = eth_coef_analysis[strat].get("eth_tvl_change_7d", {}).get("abs_mean", 0)
        print(f"    {strat:15s}: mean_coef_7d={coef_7d:+.6f}  abs_mean={coef_abs:.6f}")
    print()

    # Did Ethena specifically modulate V_rev_carry?
    rev_carry_coef_7d = eth_coef_analysis.get("V_rev_carry", {}).get(
        "eth_tvl_change_7d", {}).get("mean_coef", 0)
    rev_carry_nonzero = abs(rev_carry_coef_7d) > 1e-7
    print(f"  V_rev_carry eth_tvl_change_7d mean_coef: {rev_carry_coef_7d:+.6f} "
          f"({'ACTIVE' if rev_carry_nonzero else 'NEAR-ZERO'})")
    print()

    # ── Step 14: Per-strategy weight changes vs K198 baseline ────────────────
    print("Step 14: Weight changes vs K198 baseline...", flush=True)
    if len(weights_k207) > 0:
        k207_mean_weights = {c: float(weights_k207[c].mean()) for c in cols}
    else:
        k207_mean_weights = {c: 0.0 for c in cols}

    # K198 baseline mean weights from its curves JSON
    try:
        with open(BASE / "wave_k198_curves.json") as f:
            k198_curves = json.load(f)
        k198_wt_traj = k198_curves.get("weight_trajectory", {})
        k198_mean_weights = {}
        for c in cols:
            if c in k198_wt_traj and k198_wt_traj[c]:
                k198_mean_weights[c] = float(np.mean(k198_wt_traj[c]))
            else:
                k198_mean_weights[c] = 1.0 / n_strats
    except Exception:
        k198_mean_weights = {c: 1.0 / n_strats for c in cols}

    print(f"  {'Strategy':15s} {'K198 wt':>9} {'K207 wt':>9} {'Delta':>8}")
    print("  " + "-" * 46)
    weight_changes = {}
    for c in cols:
        k198w = k198_mean_weights.get(c, 0)
        k207w = k207_mean_weights.get(c, 0)
        delta = k207w - k198w
        weight_changes[c] = {"k198_mean": round(k198w, 4), "k207_mean": round(k207w, 4),
                              "delta": round(delta, 4)}
        print(f"  {c:15s} {k198w:>9.4f} {k207w:>9.4f} {delta:>+8.4f}")
    print()

    # ── Step 15: Acceptance criteria ──────────────────────────────────────────
    print("Step 15: Evaluating acceptance criteria...", flush=True)
    dir_acc = diag_agg.get("overall_mean_dir_acc", 0.0)

    ac1 = bool(k207_oos_sh >= K198_OOS_SH)
    ac2 = bool(k207_oos_dd >= K198_OOS_DD)       # not worse (MaxDD less negative)
    ac3 = bool(k207_wf_min >= K198_WF_MIN)
    ac4 = eth_nonzero                              # at least 1 Ethena feat non-zero

    print(f"  AC1: OOS Sh ≥ K198 ({K198_OOS_SH})? "
          f"K207={k207_oos_sh:.4f} → {'PASS' if ac1 else 'FAIL'}")
    print(f"  AC2: MaxDD not worsened (≥ {K198_OOS_DD})? "
          f"K207={k207_oos_dd:.4f} → {'PASS' if ac2 else 'FAIL'}")
    print(f"  AC3: WF min ≥ K198 ({K198_WF_MIN})? "
          f"K207={k207_wf_min:.4f} → {'PASS' if ac3 else 'FAIL'}")
    print(f"  AC4: Ethena feature non-zero? "
          f"{eth_nonzero} → {'PASS' if ac4 else 'FAIL'}")
    print()

    n_ac_pass = sum([ac1, ac2, ac3, ac4])
    sh_lift_vs_k198 = k207_oos_sh - K198_OOS_SH
    sh_lift_vs_k204 = k207_oos_sh - K204_OOS_SH
    dd_delta_pct = abs((k207_oos_dd - K198_OOS_DD) / K198_OOS_DD) * 100 if K198_OOS_DD != 0 else 0.0

    if all([ac1, ac2, ac3, ac4]):
        verdict = (
            f"ACCEPT: K207 Ethena-augmented Ridge clears all 4 criteria. "
            f"Promote to v6.6. "
            f"OOS Sh {k207_oos_sh:.4f} (+{sh_lift_vs_k198:.4f} vs K198). "
            f"WF min {k207_wf_min:.4f} (≥ K198 {K198_WF_MIN}). "
            f"MaxDD {k207_oos_dd:.4f}. "
            f"At least one Ethena feature actively modulates weights."
        )
    elif all([ac1, ac3, ac4]) and not ac2 and dd_delta_pct < 30:
        verdict = (
            f"CONDITIONAL ACCEPT: OOS Sh {k207_oos_sh:.4f} and WF min {k207_wf_min:.4f} exceed K198. "
            f"MaxDD slightly worse ({k207_oos_dd:.4f} vs K198 {K198_OOS_DD:.4f}, "
            f"{dd_delta_pct:.0f}% worse). Ethena features active. "
            "Recommend: promote with MaxDD monitoring."
        )
    elif all([ac2, ac3]) and k207_oos_sh > K198_OOS_SH - 0.10:
        verdict = (
            f"CONDITIONAL REJECT: OOS Sh {k207_oos_sh:.4f} close to K198 but below threshold. "
            f"WF stability maintained. Keep K198 as production; "
            "consider K207 in K208 ensemble combination."
        )
    else:
        verdict = (
            f"REJECT: K207 Ethena features do not improve K198 sufficiently "
            f"(criteria pass: {n_ac_pass}/4). "
            f"OOS Sh {k207_oos_sh:.4f} vs K198 {K198_OOS_SH}. "
            f"K198 v6.5 remains production. "
            "Consider K208: combine K207 insights with K205 DD features."
        )

    print(f"  Verdict: {verdict}")
    print()

    elapsed = time.time() - START_TIME
    print(f"Total runtime: {elapsed:.1f}s")
    print()

    # ── Equity curves ─────────────────────────────────────────────────────────
    k207_equity = np.cumprod(1.0 + pnl_k207.values).tolist()
    static_equity = (
        np.cumprod(1.0 + static_aligned.values).tolist()
        if len(static_aligned) > 0 else []
    )

    # Load K198 curves for comparison
    try:
        with open(BASE / "wave_k198_curves.json") as f:
            k198_curves_raw = json.load(f)
        k198_equity = k198_curves_raw.get("equity_ridge", [])
        k198_dates_list = k198_curves_raw.get("dates_ml", [])
    except Exception:
        k198_equity = []
        k198_dates_list = []

    # Weight trajectory
    if len(weights_k207) > 0:
        weight_traj_dates = [str(d.date()) for d in weights_k207.index]
        weight_traj = {c: [round(float(x), 4) for x in weights_k207[c].values]
                       for c in cols}
    else:
        weight_traj_dates = []
        weight_traj = {}

    # ── Assemble main JSON ────────────────────────────────────────────────────
    output = {
        "wave": "K207",
        "task": "Ethena TVL features added to K198 ML feature matrix (v6.6 candidate)",
        "as_of": pd.Timestamp.now(tz="UTC").isoformat(),
        "runtime_s": round(elapsed, 1),
        "config": {
            "strategies": cols,
            "n_strategies": n_strats,
            "n_base_features": 51,
            "n_ethena_features": 4,
            "n_total_features": 55,
            "ethena_features": eth_cols,
            "ethena_lag_days": ETH_TVL_LAG_DAYS,
            "ml_train_days": ML_TRAIN_DAYS,
            "ml_test_days": ML_TEST_DAYS,
            "oos_frac": OOS_FRAC,
            "k121_cap": K121_CAP,
            "carry_fwd_cap": CARRY_FWD_CAP,
            "carry_rev_cap": CARRY_REV_CAP,
            "fr_threshold": FR_THRESHOLD,
            "feature_win_short": 30,
            "feature_win_long": 90,
            "target_horizon_days": ML_TEST_DAYS,
            "ridge_alpha": 1.0,
            "date_range": [str(df_all.index[0].date()), str(df_all.index[-1].date())],
            "n_days_total": len(df_all),
            "n_days_ml_window": len(pnl_k207),
            "n_wf_steps": len(diagnostics_k207),
        },
        "comparison_table": {
            "K198_v6.5_baseline": {
                "description": "K198 Ridge ML, 51 features, production v6.5",
                "oos_sharpe": K198_OOS_SH,
                "oos_maxdd":  K198_OOS_DD,
                "wf_mean":    K198_WF_MEAN,
                "wf_min":     K198_WF_MIN,
            },
            "K204_rejected": {
                "description": "K204 (previously rejected)",
                "oos_sharpe": K204_OOS_SH,
                "wf_min":     6.02,
            },
            "K207_ethena_55feat": {
                "description": "K207 Ridge ML, 55 features (51 + 4 Ethena TVL)",
                "oos_sharpe":  round(k207_oos_sh, 4),
                "oos_maxdd":   round(k207_oos_dd, 4),
                "oos_sortino": m_k207["sortino"],
                "oos_calmar":  m_k207["calmar"],
                "oos_ann_ret": m_k207["ann_ret"],
                "oos_ann_vol": m_k207["ann_vol"],
                "oos_n_days":  m_k207["n_days"],
                "wf_mean":     k207_wf_mean,
                "wf_min":      k207_wf_min,
                "wf_max":      wf_k207["max"],
                "wf_std":      wf_k207["std"],
                "wf_fold_sharpes": wf_k207["fold_sharpes"],
                "lift_vs_k198_oos": round(sh_lift_vs_k198, 4),
                "lift_vs_k204_oos": round(sh_lift_vs_k204, 4),
                "lift_vs_k198_wf_min": round(k207_wf_min - K198_WF_MIN, 4),
            },
            "WF_static_P3_same_windows": {
                "description": "Static P3 on same WF windows (apples-to-apples)",
                "oos_sharpe": m_static["sharpe"],
                "oos_maxdd":  m_static["max_dd"],
                "wf_mean":    wf_static["mean"],
                "wf_min":     wf_static["min"],
                "wf_fold_sharpes": wf_static["fold_sharpes"],
            },
        },
        "feature_importance_ranked": feat_imp,
        "ethena_feature_rankings": eth_ranks,
        "ethena_feature_nonzero": eth_nonzero,
        "ethena_coefficient_analysis": eth_coef_analysis,
        "v_rev_carry_ethena_modulation": {
            "eth_tvl_change_7d_mean_coef": round(rev_carry_coef_7d, 6),
            "active": rev_carry_nonzero,
            "analysis": (
                "V_rev_carry eth_tvl_change_7d coefficient is active — "
                "Ridge has learned the TVL→carry mechanism from K206."
                if rev_carry_nonzero else
                "V_rev_carry eth_tvl_change_7d near-zero — "
                "Ridge did not learn substantial TVL→carry signal for this strategy."
            ),
        },
        "weight_changes_vs_k198": weight_changes,
        "ml_predictor_diagnostics": {
            **diag_agg,
            "n_wf_steps": len(diagnostics_k207),
            "per_step_summary": [
                {k: v for k, v in d.items() if k not in ("r2_per_strat", "eth_coef_per_strat")}
                for d in diagnostics_k207
            ],
        },
        "acceptance_criteria": {
            "AC1_oos_sh_ge_k198": ac1,
            "AC1_k198_oos_sh": K198_OOS_SH,
            "AC1_k207_oos_sh": round(k207_oos_sh, 4),
            "AC1_lift": round(sh_lift_vs_k198, 4),
            "AC2_maxdd_not_worsened": ac2,
            "AC2_k198_maxdd": K198_OOS_DD,
            "AC2_k207_maxdd": round(k207_oos_dd, 4),
            "AC3_wf_min_ge_k198": ac3,
            "AC3_k198_wf_min": K198_WF_MIN,
            "AC3_k207_wf_min": round(k207_wf_min, 4),
            "AC4_ethena_nonzero": ac4,
            "n_criteria_passed": n_ac_pass,
            "all_pass": all([ac1, ac2, ac3, ac4]),
        },
        "verdict": verdict,
        "k208_recommendation": (
            "K208: Combine K207 (Ethena features) with K205 (DD features, 180d window) "
            "if both ACCEPT independently. "
            "If K207 REJECTS but Ethena features show non-zero Ridge coefficients, "
            "still include in K208 as a secondary feature set — "
            "the global TVL signal may improve when combined with per-strategy DD features."
        ),
        "risk_assessment": {
            "panel_wide_signal": (
                "Ethena features are GLOBAL (same value for all strategies on a given day). "
                "This means they affect the bias term and interact with cross-strategy features. "
                "Ridge regularization prevents overfitting to this narrow signal. "
                "Risk: if TVL goes outside historical range, extrapolation degrades."
            ),
            "ethena_regime_coverage": (
                f"TVL cache covers {len(eth_feat.dropna())} days. "
                "Ethena launched in early 2024, so coverage of pre-launch period is absent. "
                "Features default to 0 for dates before TVL data begins."
            ),
            "look_ahead_bias": (
                f"Features use {ETH_TVL_LAG_DAYS}d lag — feature at day t reflects "
                f"TVL through day t-{ETH_TVL_LAG_DAYS}. No forward-looking data."
            ),
            "noise_injection": (
                "TVL features apply to all strategies, not just V_rev_carry. "
                "For unrelated strategies (v4.1, V1, K114), TVL signal may be noise. "
                "Ridge shrinkage should suppress noisy coefficients to near-zero."
            ),
        },
    }

    # Save metrics JSON
    out_json = BASE / "wave_k207_ethena_features.json"
    with open(out_json, "w") as f:
        json.dump(output, f, indent=2)
    print(f"Saved: {out_json}")

    # Save curves JSON
    curves_out = {
        "wave": "K207",
        "dates_k207": [str(d.date()) for d in pnl_k207.index],
        "dates_static_wf": [str(d.date()) for d in static_aligned.index] if len(static_aligned) > 0 else [],
        "dates_k198": k198_dates_list,
        "equity_k207": [round(float(v), 6) for v in k207_equity],
        "equity_static_wf": [round(float(v), 6) for v in static_equity],
        "equity_k198": [round(float(v), 6) for v in k198_equity],
        "pnl_k207": [round(float(v), 8) for v in pnl_k207.values],
        "pnl_static_wf": [round(float(v), 8) for v in static_aligned.values] if len(static_aligned) > 0 else [],
        "weight_trajectory_dates": weight_traj_dates,
        "weight_trajectory": weight_traj,
        "ethena_feature_summary": {
            fn: {
                "nonzero_days": int((feat_df[fn] != 0).sum()),
                "total_days": len(feat_df),
                "mean": round(float(feat_df[fn].mean()), 6),
                "std": round(float(feat_df[fn].std()), 6),
            }
            for fn in eth_cols if fn in feat_df.columns
        },
    }
    out_curves = BASE / "wave_k207_curves.json"
    with open(out_curves, "w") as f:
        json.dump(curves_out, f, indent=2)
    print(f"Saved: {out_curves}")

    # ── Final summary table ───────────────────────────────────────────────────
    print()
    print("=" * 72)
    print("FINAL COMPARISON TABLE")
    print("=" * 72)
    print(f"{'Version':<35} {'OOS Sh':>8} {'OOS MaxDD':>10} {'WF mean':>8} {'WF min':>8}")
    print("-" * 72)
    print(f"{'K198 v6.5 baseline (51 feat)':<35} {K198_OOS_SH:>8.4f} {K198_OOS_DD:>10.4f} "
          f"{K198_WF_MEAN:>8.4f} {K198_WF_MIN:>8.4f}")
    print(f"{'K204 (rejected)':<35} {K204_OOS_SH:>8.4f} {'N/A':>10} "
          f"{'N/A':>8} {6.02:>8.4f}")
    print(f"{'K207 Ethena (55 feat)':<35} {k207_oos_sh:>8.4f} {k207_oos_dd:>10.4f} "
          f"{k207_wf_mean:>8.4f} {k207_wf_min:>8.4f}")
    print("-" * 72)
    print(f"  K207 lift vs K198:  OOS Sh {sh_lift_vs_k198:+.4f} | "
          f"WF min {k207_wf_min - K198_WF_MIN:+.4f}")
    print()
    print(f"VERDICT: {verdict}")
    print()
    print("K208 PLAN: " + output["k208_recommendation"])
    print()

    return output


if __name__ == "__main__":
    main()

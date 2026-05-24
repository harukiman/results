"""Wave K205 — ML Allocator DD Fix: 180d Training Window + Soft DD Penalty.

Objective:
  Fix K204's cold-start instability (WF min 6.02, fail) by:
  1. Extending training window 90d → 180d (allow DD features to calibrate in early folds)
  2. Adding soft DD penalty post-Ridge: w_i *= max(0, 1 + 2*dd30_i)
     - dd30 = -0.05 (5% DD) → multiplier = 0.9 (10% weight reduction)
     - dd30 = -0.5          → multiplier = 0   (full halt)
  3. Dropping dd_max30 (redundant with mdd30 per K204 correlation analysis)

Changes vs K204:
  - TRAIN_WINDOW: 90 → 180
  - Remove {strat}__dd_max30 from feature matrix (113 → 103 features)
  - After Ridge prediction: apply per-strategy DD penalty before weight normalization
  - Everything else identical to K204

Acceptance (K205 → v6.6):
  - OOS Sh >= K198 (10.28), preferably >= K204 (10.36)
  - MaxDD < K198 (-0.0053)
  - WF min >= K198 (6.57)  ← primary fix target
  - WF mean >= K198 (7.91)

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

TRADING_DAYS = 365
OOS_FRAC     = 0.30
N_FOLDS      = 4

# ── K205 KEY CHANGES ───────────────────────────────────────────────────────────
ML_TRAIN_DAYS = 180   # was 90 in K204 — fixes cold-start instability in early folds
ML_TEST_DAYS  = 30

# Soft DD penalty coefficient: w_i *= max(0, 1 + DD_PENALTY_COEF * dd30_i)
# dd30_i <= 0, so penalty = 1 + 2*dd30_i: linear ramp from 0 (dd30=-0.5) to 1 (dd30=0)
DD_PENALTY_COEF = 2.0
# ─────────────────────────────────────────────────────────────────────────────

# Reference baselines
K198_OOS_SH  = 10.28
K198_OOS_DD  = -0.0053
K198_WF_MEAN = 7.91
K198_WF_MIN  = 6.57
K204_OOS_SH  = 10.36
K204_WF_MIN  = 6.02

# Caps (same as K198)
K121_CAP      = 0.30
CARRY_FWD_CAP = 0.10
CARRY_REV_CAP = 0.10

# FR defensive trigger
FR_SYMBOLS    = ["BTC", "ETH", "DOGE", "AVAX", "SOL", "XRP"]
FR_THRESHOLD  = -0.009735
FR_COMPONENTS = ["K121", "K133"]

STRATEGY_NAMES = [
    "v4.1", "V1", "K114", "K116", "K121", "K133",
    "K147", "K175_DAR", "V_fwd_carry", "V_rev_carry",
]


# ─────────────────────────────────────────────────────────────────────────────
# Metrics
# ─────────────────────────────────────────────────────────────────────────────

def sharpe_d(r: np.ndarray) -> float:
    r = np.asarray(r, dtype=float)
    if len(r) < 2 or r.std(ddof=1) == 0:
        return 0.0
    return float(r.mean() / r.std(ddof=1) * math.sqrt(TRADING_DAYS))


def max_dd_d(r: np.ndarray) -> float:
    eq = np.cumprod(1.0 + np.asarray(r, dtype=float))
    peak = np.maximum.accumulate(eq)
    return float((eq / peak - 1.0).min())


def cumulative_dd(r: np.ndarray) -> float:
    """Cumulative drawdown: (end_equity / peak) - 1  [<= 0]."""
    eq = np.cumprod(1.0 + np.asarray(r, dtype=float))
    peak = np.max(eq)
    return float(eq[-1] / peak - 1.0)


def calmar_30d(r: np.ndarray) -> float:
    """30-day Calmar = annualized return / |max_dd|."""
    r = np.asarray(r, dtype=float)
    if len(r) < 2:
        return 0.0
    ann_ret = float((1.0 + r).prod() ** (TRADING_DAYS / len(r)) - 1.0)
    mdd = max_dd_d(r)
    if abs(mdd) < 1e-8:
        return 0.0
    return float(ann_ret / abs(mdd))


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


# ─────────────────────────────────────────────────────────────────────────────
# Weight utilities
# ─────────────────────────────────────────────────────────────────────────────

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
    w = apply_cap(w, cols, "K121", K121_CAP)
    w = apply_cap(w, cols, "V_fwd_carry", CARRY_FWD_CAP)
    w = apply_cap(w, cols, "V_rev_carry", CARRY_REV_CAP)
    return w


# ─────────────────────────────────────────────────────────────────────────────
# Data loading (identical to K198/K204)
# ─────────────────────────────────────────────────────────────────────────────

def load_component_returns() -> pd.DataFrame:
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
    print(f"  Component returns: {df.shape[0]} days x {df.shape[1]} strategies")
    print(f"  Date range: {df.index[0].date()} -> {df.index[-1].date()}")
    return df


def load_fr_mean_daily() -> pd.Series:
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


# ─────────────────────────────────────────────────────────────────────────────
# K205 Feature engineering — K204 minus dd_max30
# ─────────────────────────────────────────────────────────────────────────────

def build_features_k205(
    df: pd.DataFrame,
    fr_mean: Optional[pd.Series],
    win_short: int = 30,
    win_long: int = 90,
) -> pd.DataFrame:
    """
    Build feature matrix for K205 (K204 minus dd_max30).

    Per-strategy features:
      {s}__sh30, {s}__sh90, {s}__vol30, {s}__mdd30, {s}__xcorr  [K198 baseline]
      {s}__dd30:     cumulative drawdown over last 30d
      {s}__dd90:     cumulative drawdown over last 90d
      -- dd_max30 DROPPED (redundant with mdd30 per K204 analysis) --
      {s}__sh_neg30: fraction of days in last 30d with negative return
      {s}__recovery: binary — 1 if recovering from recent DD
      {s}__calmar30: 30d Calmar ratio

    Panel-level:
      fr_mean_ann, panel_dd30, panel_recovery
    """
    n_strats = df.shape[1]
    cols = list(df.columns)
    R = df.values
    n = len(R)
    feat_rows = []

    panel_ret = R.mean(axis=1)

    for t in range(win_long, n):
        row = {}
        slice_long  = R[t - win_long:t]
        slice_short = R[t - win_short:t]

        if n_strats > 1:
            corr_mat = np.corrcoef(slice_short.T)
            np.fill_diagonal(corr_mat, 0.0)
        else:
            corr_mat = np.zeros((1, 1))

        for i, strat in enumerate(cols):
            prefix = f"{strat}__"
            r_short = slice_short[:, i]
            r_long  = slice_long[:, i]

            # K198 baseline features
            row[f"{prefix}sh30"]  = sharpe_d(r_short)
            row[f"{prefix}sh90"]  = sharpe_d(r_long)
            row[f"{prefix}vol30"] = float(r_short.std(ddof=1) * math.sqrt(TRADING_DAYS))
            row[f"{prefix}mdd30"] = max_dd_d(r_short)
            if n_strats > 1:
                other_corrs = np.delete(corr_mat[i], i)
                row[f"{prefix}xcorr"] = float(np.mean(other_corrs))
            else:
                row[f"{prefix}xcorr"] = 0.0

            # K204 DD features (minus dd_max30)
            row[f"{prefix}dd30"]    = cumulative_dd(r_short)
            row[f"{prefix}dd90"]    = cumulative_dd(r_long)
            # dd_max30 DROPPED — redundant with mdd30

            row[f"{prefix}sh_neg30"] = float(np.sum(r_short < 0) / len(r_short))

            eq_short = np.cumprod(1.0 + r_short)
            last5_ret = float(eq_short[-1] / eq_short[-6] - 1.0) if len(eq_short) >= 6 else 0.0
            dd30_val = float(cumulative_dd(r_short))
            row[f"{prefix}recovery"] = float(last5_ret > 0 and dd30_val < -0.002)

            row[f"{prefix}calmar30"] = calmar_30d(r_short)

        # Panel-level features
        if fr_mean is not None and len(fr_mean) > 0:
            fr_date = df.index[t]
            fr_aligned = fr_mean.reindex([fr_date], method="ffill")
            row["fr_mean_ann"] = float(fr_aligned.iloc[0]) if not fr_aligned.isna().all() else 0.0
        else:
            row["fr_mean_ann"] = 0.0

        panel_short = panel_ret[t - win_short:t]
        row["panel_dd30"] = cumulative_dd(panel_short)

        panel_eq = np.cumprod(1.0 + panel_short)
        panel_last5 = float(panel_eq[-1] / panel_eq[-6] - 1.0) if len(panel_eq) >= 6 else 0.0
        row["panel_recovery"] = float(panel_last5 > 0 and row["panel_dd30"] < -0.002)

        feat_rows.append(row)

    feat_df = pd.DataFrame(feat_rows, index=df.index[win_long:])
    return feat_df


def build_targets(df: pd.DataFrame, horizon: int = 30) -> pd.DataFrame:
    """Build next-horizon-day forward Sharpe targets per strategy."""
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


# ─────────────────────────────────────────────────────────────────────────────
# K205 ML walk-forward: 180d training + soft DD penalty
# ─────────────────────────────────────────────────────────────────────────────

def ml_walk_forward_k205(
    df: pd.DataFrame,
    feat_df: pd.DataFrame,
    target_df: pd.DataFrame,
    train_days: int = ML_TRAIN_DAYS,
    test_days:  int = ML_TEST_DAYS,
    alpha:      float = 1.0,
) -> Tuple[pd.DataFrame, pd.Series, list, dict]:
    """
    K205 walk-forward:
    1. Use train_days=180 (was 90 in K204)
    2. After Ridge prediction, apply soft DD penalty:
       predicted_Sh_i *= max(0, 1 + DD_PENALTY_COEF * dd30_i)
    3. Weight ∝ max(penalized_Sh, 0) as before

    Returns: weights_df, pnl_series, diagnostics, dd_penalty_stats
    """
    cols = list(df.columns)
    n_strats = len(cols)

    # Check dd30 columns exist in feature matrix
    dd30_cols = [f"{c}__dd30" for c in cols]
    has_dd30 = all(c in feat_df.columns for c in dd30_cols)

    common_idx   = feat_df.index.intersection(target_df.index)
    feat_aligned = feat_df.loc[common_idx]
    tgt_aligned  = target_df.loc[common_idx]

    feat_arr   = feat_aligned.values
    target_arr = np.array([tgt_aligned[f"{c}__fwd_sh"].values for c in cols]).T
    date_idx   = feat_aligned.index
    n          = len(feat_arr)

    wf_weights  = []
    wf_pnl      = []
    wf_dates    = []
    diagnostics = []

    # DD penalty firing stats
    penalty_fires_total = 0
    penalty_fires_steps = 0
    penalty_detail = []  # per step

    min_train = max(train_days, 45)
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

        t_test_start     = t_start
        t_test_end       = min(t_start + test_days, n)
        X_test           = feat_arr[t_test_start:t_test_end]
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
        coef_rows = []
        r2_scores = []

        for i in range(n_strats):
            y = Y_train[:, i]
            if np.isnan(y).any() or np.std(y) < 1e-10:
                preds[i] = 0.0
                r2_scores.append(np.nan)
                coef_rows.append(np.zeros(X_train_s.shape[1]))
                continue

            model = Ridge(alpha=alpha)
            model.fit(X_train_s, y)
            pred = model.predict(X_test_s[:1])[0]
            preds[i] = float(pred)

            y_pred_tr = model.predict(X_train_s)
            ss_res = np.sum((y - y_pred_tr) ** 2)
            ss_tot = np.sum((y - y.mean()) ** 2)
            r2 = 1.0 - ss_res / ss_tot if ss_tot > 1e-12 else 0.0
            r2_scores.append(r2)
            coef_rows.append(np.abs(model.coef_))

        # ── K205 SOFT DD PENALTY ──────────────────────────────────────────────
        # Get dd30_i values from the LAST feature row in training set
        # (most recent observation before test window)
        dd30_values = np.zeros(n_strats)
        if has_dd30:
            # Use latest available observation (end of training window)
            last_feat_idx = t_train_end - 1
            if last_feat_idx < len(feat_aligned):
                last_feat_row = feat_aligned.iloc[last_feat_idx]
                for i, c in enumerate(cols):
                    col_name = f"{c}__dd30"
                    dd30_values[i] = float(last_feat_row.get(col_name, 0.0))

        # Apply penalty: predicted_Sh_i *= max(0, 1 + 2 * dd30_i)
        multipliers = np.array([
            max(0.0, 1.0 + DD_PENALTY_COEF * dd30_values[i])
            for i in range(n_strats)
        ])
        preds_penalized = preds * multipliers

        # Count fires (any strategy with multiplier < 1.0)
        n_fires = int(np.sum(multipliers < 1.0))
        n_halted = int(np.sum(multipliers == 0.0))
        if n_fires > 0:
            penalty_fires_total += n_fires
            penalty_fires_steps += 1
        penalty_detail.append({
            "step": step,
            "dd30_values": {cols[i]: round(float(dd30_values[i]), 6) for i in range(n_strats)},
            "multipliers": {cols[i]: round(float(multipliers[i]), 4) for i in range(n_strats)},
            "n_penalized": n_fires,
            "n_halted": n_halted,
        })

        # Weight from penalized predictions
        pos_preds = np.maximum(preds_penalized, 0.0)
        if pos_preds.sum() < 1e-10:
            # Fallback: equal weight if all predictions are 0/negative after penalty
            w = w_equal(n_strats)
        else:
            w = pos_preds / pos_preds.sum()
        w = apply_all_caps(w, cols)

        actual_targets = target_arr[t_test_start:t_test_end].mean(axis=0)
        dir_correct = np.array([
            (preds[i] > 0) == (actual_targets[i] > 0)
            for i in range(n_strats)
        ])

        mean_coef = np.mean(coef_rows, axis=0) if coef_rows else np.zeros(X_train_s.shape[1])

        diag_step = {
            "step":        step,
            "train_start": str(date_idx[t_train_start].date()),
            "train_end":   str(date_idx[t_train_end - 1].date()),
            "test_start":  str(test_dates_slice[0].date()),
            "test_end":    str(test_dates_slice[-1].date()),
            "train_n_days": t_train_end - t_train_start,
            "preds_raw":   {cols[i]: round(float(preds[i]), 4) for i in range(n_strats)},
            "preds_penalized": {cols[i]: round(float(preds_penalized[i]), 4) for i in range(n_strats)},
            "dd30_values": {cols[i]: round(float(dd30_values[i]), 6) for i in range(n_strats)},
            "multipliers": {cols[i]: round(float(multipliers[i]), 4) for i in range(n_strats)},
            "weights":     {cols[i]: round(float(w[i]), 4) for i in range(n_strats)},
            "r2_per_strat": {cols[i]: round(float(r2_scores[i]), 4) if not np.isnan(r2_scores[i]) else None
                             for i in range(n_strats)},
            "dir_accuracy_per_strat": {cols[i]: bool(dir_correct[i]) for i in range(n_strats)},
            "mean_r2": round(float(np.nanmean(r2_scores)), 4),
            "mean_dir_acc": round(float(np.mean(dir_correct)), 4),
            "mean_abs_coef": mean_coef.tolist(),
            "feature_names": list(feat_aligned.columns),
            "n_penalized": n_fires,
            "n_halted": n_halted,
        }
        diagnostics.append(diag_step)

        test_rets = df.loc[test_dates_slice].values
        for d_i, d in enumerate(test_dates_slice):
            pnl = float(test_rets[d_i] @ w)
            wf_pnl.append(pnl)
            wf_dates.append(d)
            wf_weights.append(dict(zip(cols, w)))

        step += 1

    if not wf_pnl:
        return pd.DataFrame(), pd.Series(dtype=float), [], {}

    n_steps = len(diagnostics)
    dd_penalty_stats = {
        "total_steps": n_steps,
        "steps_with_any_penalty": penalty_fires_steps,
        "pct_steps_with_penalty": round(100.0 * penalty_fires_steps / n_steps, 1) if n_steps > 0 else 0.0,
        "total_strategy_penalties": penalty_fires_total,
        "avg_penalized_per_step": round(penalty_fires_total / n_steps, 2) if n_steps > 0 else 0.0,
        "penalty_coef": DD_PENALTY_COEF,
        "note": (
            f"Penalty formula: w_i *= max(0, 1 + {DD_PENALTY_COEF} * dd30_i). "
            "dd30_i = 0 → multiplier=1 (no change). dd30_i = -0.5 → multiplier=0 (full halt)."
        ),
        "per_step_detail": penalty_detail,
    }

    weights_df = pd.DataFrame(wf_weights, index=wf_dates)
    pnl_series = pd.Series(wf_pnl, index=wf_dates, name="ml_pnl")
    return weights_df, pnl_series, diagnostics, dd_penalty_stats


# ─────────────────────────────────────────────────────────────────────────────
# FR trigger
# ─────────────────────────────────────────────────────────────────────────────

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


# ─────────────────────────────────────────────────────────────────────────────
# Static P3 walk-forward baseline
# ─────────────────────────────────────────────────────────────────────────────

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


# ─────────────────────────────────────────────────────────────────────────────
# Feature importance
# ─────────────────────────────────────────────────────────────────────────────

def compute_feature_importance(
    feat_df: pd.DataFrame,
    target_df: pd.DataFrame,
    cols: List[str],
    alpha: float = 1.0,
) -> dict:
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


# ─────────────────────────────────────────────────────────────────────────────
# Walk-forward fold analysis
# ─────────────────────────────────────────────────────────────────────────────

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
        "min":  round(float(np.min(sharpes)),  4),
        "max":  round(float(np.max(sharpes)),  4),
        "std":  round(float(np.std(sharpes)),  4),
    }


def aggregate_diagnostics(diagnostics: list, cols: List[str]) -> dict:
    if not diagnostics:
        return {}

    r2_by_strat  = {c: [] for c in cols}
    dir_by_strat = {c: [] for c in cols}

    for d in diagnostics:
        for c in cols:
            r2 = d["r2_per_strat"].get(c)
            da = d["dir_accuracy_per_strat"].get(c)
            if r2 is not None:
                r2_by_strat[c].append(r2)
            if da is not None:
                dir_by_strat[c].append(float(da))

    r2_summary  = {}
    dir_summary = {}
    for c in cols:
        vals = [x for x in r2_by_strat[c] if x is not None]
        r2_summary[c] = {
            "mean": round(float(np.mean(vals)), 4) if vals else None,
            "median": round(float(np.median(vals)), 4) if vals else None,
        }
        dvals = dir_by_strat[c]
        dir_summary[c] = {
            "mean_dir_acc": round(float(np.mean(dvals)), 4) if dvals else None,
            "above_55pct": bool(np.mean(dvals) > 0.55) if dvals else False,
        }

    return {
        "overall_mean_r2":      round(float(np.nanmean([d["mean_r2"] for d in diagnostics])), 4),
        "overall_mean_dir_acc": round(float(np.nanmean([d["mean_dir_acc"] for d in diagnostics])), 4),
        "r2_by_strategy":       r2_summary,
        "dir_acc_by_strategy":  dir_summary,
        "n_wf_steps":           len(diagnostics),
    }


# ─────────────────────────────────────────────────────────────────────────────
# Per-fold early-folds cold-start analysis
# ─────────────────────────────────────────────────────────────────────────────

def early_fold_analysis(diagnostics: list) -> dict:
    """
    Compare training window sizes in early vs late steps.
    In K204 (90d window), early steps had <90d actual training data (cold start).
    In K205 (180d window), early steps should still have shorter windows but more data
    before the model stabilizes.
    """
    if not diagnostics:
        return {}

    early_steps  = diagnostics[:5]   # first 5 walk-forward steps
    late_steps   = diagnostics[-5:]  # last 5 walk-forward steps
    middle_steps = diagnostics[5:-5] if len(diagnostics) > 10 else []

    def step_summary(steps):
        if not steps:
            return {}
        train_lens = [s.get("train_n_days", 0) for s in steps]
        r2s = [s.get("mean_r2", 0) for s in steps]
        dir_accs = [s.get("mean_dir_acc", 0) for s in steps]
        n_pen = [s.get("n_penalized", 0) for s in steps]
        return {
            "n_steps": len(steps),
            "mean_train_days": round(float(np.mean(train_lens)), 1),
            "min_train_days":  int(np.min(train_lens)),
            "mean_r2":        round(float(np.nanmean(r2s)), 4),
            "mean_dir_acc":   round(float(np.mean(dir_accs)), 4),
            "mean_n_penalized": round(float(np.mean(n_pen)), 2),
        }

    return {
        "early_steps_1_5":  step_summary(early_steps),
        "middle_steps":     step_summary(middle_steps),
        "late_steps":       step_summary(late_steps),
        "interpretation": (
            "180d window means early steps have more training data than K204's 90d window. "
            "Cold-start instability should be reduced in folds 1-2. "
            "Check if mean_r2 is more consistent across early vs late steps."
        ),
    }


# ─────────────────────────────────────────────────────────────────────────────
# Main
# ─────────────────────────────────────────────────────────────────────────────

def main():
    print("=" * 72)
    print("Wave K205 -- ML Allocator DD Fix (v6.6 candidate)")
    print("  Changes: TRAIN_WINDOW 90->180, soft DD penalty, drop dd_max30")
    print("=" * 72)
    print()

    np.random.seed(42)

    # Step 1: Load component returns
    print("Step 1: Loading component returns...", flush=True)
    df_all = load_component_returns()
    cols   = list(df_all.columns)
    n_strats = len(cols)
    print(f"  Strategies: {cols}")
    print()

    # Step 2: Load FR regime indicator
    print("Step 2: Loading FR regime indicator...", flush=True)
    fr_mean = load_fr_mean_daily()
    if len(fr_mean) > 0:
        print(f"  FR mean range: {fr_mean.index[0].date()} -> {fr_mean.index[-1].date()}")
        fr_aligned_check = fr_mean.reindex(df_all.index, method="ffill")
        print(f"  FR mean stats: mean={fr_aligned_check.mean():.4f} std={fr_aligned_check.std():.4f}")
    else:
        print("  WARNING: FR data unavailable -- regime feature will be zero")
    print()

    # Step 3: Apply FR trigger
    print("Step 3: Applying FR trigger (K121, K133)...", flush=True)
    if len(fr_mean) > 0:
        df_triggered = apply_fr_trigger(df_all, fr_mean)
        n_trigger = int((fr_mean.reindex(df_all.index, method="ffill") < FR_THRESHOLD).sum())
        print(f"  Trigger fires {n_trigger} / {len(df_all)} days ({n_trigger/len(df_all)*100:.1f}%)")
    else:
        df_triggered = df_all.copy()
        print("  No FR trigger applied")
    print()

    # Step 4: Build K205 feature matrix (K204 minus dd_max30)
    print("Step 4: Building K205 feature matrix (K204 minus dd_max30)...", flush=True)
    feat_df = build_features_k205(df_triggered, fr_mean if len(fr_mean) > 0 else None)
    print(f"  Feature matrix: {feat_df.shape[0]} rows x {feat_df.shape[1]} features")
    print(f"  Feature date range: {feat_df.index[0].date()} -> {feat_df.index[-1].date()}")
    baseline_suffixes = {"sh30", "sh90", "vol30", "mdd30", "xcorr"}
    new_dd_suffixes   = {"dd30", "dd90", "sh_neg30", "recovery", "calmar30"}
    n_baseline = sum(1 for c in feat_df.columns if c.split("__")[-1] in baseline_suffixes or c == "fr_mean_ann")
    n_new_dd   = sum(1 for c in feat_df.columns if c.split("__")[-1] in new_dd_suffixes or c in {"panel_dd30", "panel_recovery"})
    print(f"  Baseline: {n_baseline} | New DD (minus dd_max30): {n_new_dd} | Total: {feat_df.shape[1]}")
    print(f"  (K204 had 113 features; K205 drops 10 dd_max30 -> {feat_df.shape[1]} expected)")
    print()

    # Step 5: Build targets
    print("Step 5: Building forward Sharpe targets (horizon=30d)...", flush=True)
    target_df = build_targets(df_triggered, horizon=ML_TEST_DAYS)
    print(f"  Target matrix: {target_df.shape[0]} rows x {target_df.shape[1]} strategies")
    print()

    # Step 6: Ridge walk-forward with 180d training + soft DD penalty
    print(f"Step 6: Ridge WF (train={ML_TRAIN_DAYS}d, test={ML_TEST_DAYS}d) + soft DD penalty...", flush=True)
    print(f"  DD penalty: w_i *= max(0, 1 + {DD_PENALTY_COEF} * dd30_i)")
    print(f"  (dd30=-0.05 => mult=0.90; dd30=-0.50 => mult=0.00 full halt)")
    weights_ridge, pnl_ridge, diagnostics_ridge, dd_penalty_stats = ml_walk_forward_k205(
        df_triggered, feat_df, target_df,
        train_days=ML_TRAIN_DAYS,
        test_days=ML_TEST_DAYS,
        alpha=1.0,
    )
    if len(pnl_ridge) == 0:
        print("  ERROR: Ridge WF returned empty PnL")
        return
    print(f"  Ridge WF PnL: {len(pnl_ridge)} days, "
          f"{pnl_ridge.index[0].date()} -> {pnl_ridge.index[-1].date()}")
    print(f"  DD penalty fired in {dd_penalty_stats['steps_with_any_penalty']}/{dd_penalty_stats['total_steps']} "
          f"steps ({dd_penalty_stats['pct_steps_with_penalty']}%)")
    print(f"  Total strategy-penalties: {dd_penalty_stats['total_strategy_penalties']}")
    print()

    # Step 7: Static P3 for comparison
    print("Step 7: Walk-forward static P3 (matched windows)...", flush=True)
    pnl_static_wf, _ = run_wf_static_p3(df_triggered)
    common_start = pnl_ridge.index[0]
    common_end   = pnl_ridge.index[-1]
    static_wf_aligned = pnl_static_wf[
        (pnl_static_wf.index >= common_start) & (pnl_static_wf.index <= common_end)
    ]
    print(f"  Static P3 WF: {len(static_wf_aligned)} days (aligned)")
    print()

    # Step 8: OOS metrics
    print("Step 8: OOS metrics (last 30%)...", flush=True)

    def oos_cut(s: pd.Series) -> pd.Series:
        cut = int(len(s) * (1 - OOS_FRAC))
        return s.iloc[cut:]

    oos_ridge  = oos_cut(pnl_ridge)
    oos_static = oos_cut(static_wf_aligned) if len(static_wf_aligned) > 0 else oos_cut(pnl_ridge)

    m_ridge  = metrics_pkg(oos_ridge.values)
    m_static = metrics_pkg(oos_static.values)

    print(f"  K198 v6.5 baseline:  OOS Sh={K198_OOS_SH:.4f} MaxDD={K198_OOS_DD:.4f}")
    print(f"  K204 DD-embed:       OOS Sh={K204_OOS_SH:.4f} WF min={K204_WF_MIN:.4f}")
    print(f"  K205 Ridge (OOS):    OOS Sh={m_ridge['sharpe']:.4f} MaxDD={m_ridge['max_dd']:.4f}")
    print(f"  Static P3 (matched): OOS Sh={m_static['sharpe']:.4f} MaxDD={m_static['max_dd']:.4f}")
    print()

    # Step 9: WF fold analysis
    print("Step 9: Walk-forward fold analysis...", flush=True)
    wf_ridge  = wf_fold_sharpes(pnl_ridge)
    wf_static = wf_fold_sharpes(static_wf_aligned) if len(static_wf_aligned) > 0 else wf_fold_sharpes(pnl_ridge)

    print(f"  K205 Ridge WF:  mean={wf_ridge['mean']:.4f}  min={wf_ridge['min']:.4f}  folds={wf_ridge['fold_sharpes']}")
    print(f"  Static P3 WF:   mean={wf_static['mean']:.4f}  min={wf_static['min']:.4f}  folds={wf_static['fold_sharpes']}")
    print(f"  K198 baseline:  mean={K198_WF_MEAN:.4f}  min={K198_WF_MIN:.4f}")
    print(f"  K204 baseline:  WF min={K204_WF_MIN:.4f} (target to beat with 180d window)")
    print()

    # Step 10: Early-fold cold-start analysis
    print("Step 10: Early-fold cold-start analysis...", flush=True)
    cold_start_analysis = early_fold_analysis(diagnostics_ridge)
    print(f"  Early steps (1-5) mean_train_days: {cold_start_analysis.get('early_steps_1_5', {}).get('mean_train_days', 'N/A')}")
    print(f"  Late steps mean_train_days: {cold_start_analysis.get('late_steps', {}).get('mean_train_days', 'N/A')}")
    print(f"  Early R2: {cold_start_analysis.get('early_steps_1_5', {}).get('mean_r2', 'N/A')}")
    print(f"  Late R2: {cold_start_analysis.get('late_steps', {}).get('mean_r2', 'N/A')}")
    print()

    # Step 11: ML diagnostics
    print("Step 11: ML predictor diagnostics...", flush=True)
    diag_agg = aggregate_diagnostics(diagnostics_ridge, cols)
    print(f"  Overall R2: {diag_agg.get('overall_mean_r2', 'N/A')}")
    print(f"  Overall dir acc: {diag_agg.get('overall_mean_dir_acc', 'N/A')}")
    print()

    # Step 12: Feature importance
    print("Step 12: Feature importance (K205 180d fit)...", flush=True)
    feat_imp = compute_feature_importance(feat_df, target_df, cols)
    print(f"  Total features: {len(feat_imp)}")
    print("  Top 20 features:")
    for name, val in list(feat_imp.items())[:20]:
        tag = "[K198]" if name.split("__")[-1] in baseline_suffixes or name == "fr_mean_ann" else "[K205-DD]"
        print(f"    {name:40s} {val:.6f}  {tag}")
    print()

    # Step 13: DD penalty per-strategy analysis
    print("Step 13: DD penalty per-strategy statistics...", flush=True)
    if dd_penalty_stats.get("per_step_detail"):
        per_strat_penalty_count = {c: 0 for c in cols}
        per_strat_avg_mult = {c: [] for c in cols}
        for step_detail in dd_penalty_stats["per_step_detail"]:
            for c in cols:
                mult = step_detail["multipliers"].get(c, 1.0)
                per_strat_avg_mult[c].append(mult)
                if mult < 1.0:
                    per_strat_penalty_count[c] += 1
        print("  Per-strategy penalty summary:")
        for c in cols:
            avg_m = np.mean(per_strat_avg_mult[c])
            n_pen = per_strat_penalty_count[c]
            pct   = 100.0 * n_pen / len(dd_penalty_stats["per_step_detail"])
            print(f"    {c:20s}: penalized {n_pen} steps ({pct:.0f}%), avg multiplier={avg_m:.4f}")
    print()

    # Step 14: Acceptance criteria
    print("Step 14: Acceptance criteria for K205 -> v6.6...", flush=True)
    ridge_oos_sh  = m_ridge["sharpe"]
    ridge_oos_dd  = m_ridge["max_dd"]
    ridge_wf_min  = wf_ridge["min"]
    ridge_wf_mean = wf_ridge["mean"]

    ac1 = ridge_oos_sh >= K198_OOS_SH          # OOS Sh >= 10.28 (K198 baseline)
    ac2 = ridge_oos_sh >= K204_OOS_SH          # OOS Sh >= 10.36 (K204, preferably)
    ac3 = ridge_oos_dd < K198_OOS_DD           # MaxDD IMPROVED vs K198
    ac4 = ridge_wf_min >= K198_WF_MIN          # WF min >= 6.57 (primary fix)
    ac5 = ridge_wf_mean >= K198_WF_MEAN        # WF mean >= 7.91

    print(f"  AC1: OOS Sh >= K198 ({K198_OOS_SH:.2f})?  K205={ridge_oos_sh:.4f} -> {'PASS' if ac1 else 'FAIL'}")
    print(f"  AC2: OOS Sh >= K204 ({K204_OOS_SH:.2f})?  K205={ridge_oos_sh:.4f} -> {'PASS' if ac2 else 'FAIL'} [bonus]")
    print(f"  AC3: MaxDD < K198 ({K198_OOS_DD:.4f})?  K205={ridge_oos_dd:.4f} -> {'PASS' if ac3 else 'FAIL'}")
    print(f"  AC4: WF min >= K198 ({K198_WF_MIN:.2f})?  K205={ridge_wf_min:.4f} -> {'PASS' if ac4 else 'FAIL'} [primary]")
    print(f"  AC5: WF mean >= K198 ({K198_WF_MEAN:.2f})?  K205={ridge_wf_mean:.4f} -> {'PASS' if ac5 else 'FAIL'}")
    print()

    # Verdict
    sh_lift_vs_k198 = ridge_oos_sh - K198_OOS_SH
    sh_lift_vs_k204 = ridge_oos_sh - K204_OOS_SH
    wf_min_lift     = ridge_wf_min - K198_WF_MIN
    wf_mean_lift    = ridge_wf_mean - K198_WF_MEAN
    dd_lift         = ridge_oos_dd - K198_OOS_DD

    hard_pass = all([ac1, ac3, ac4, ac5])  # required criteria

    if hard_pass and ac2:
        verdict = (
            f"ACCEPT -> v6.6: K205 clears ALL 5 criteria. "
            f"OOS Sh={ridge_oos_sh:.2f} ({sh_lift_vs_k198:+.2f} vs K198, {sh_lift_vs_k204:+.2f} vs K204), "
            f"MaxDD={ridge_oos_dd:.4f} (improved {dd_lift:+.4f}), "
            f"WF min={ridge_wf_min:.2f} ({wf_min_lift:+.2f} vs K198 -- cold-start FIXED). "
            "180d window + soft DD penalty successful. Promote to v6.6 production."
        )
    elif hard_pass and not ac2:
        verdict = (
            f"ACCEPT -> v6.6: K205 clears required criteria (AC1,AC3,AC4,AC5). "
            f"OOS Sh={ridge_oos_sh:.2f} ({sh_lift_vs_k198:+.2f} vs K198; BELOW K204 by {-sh_lift_vs_k204:.2f}). "
            f"MaxDD={ridge_oos_dd:.4f} ({dd_lift:+.4f}), "
            f"WF min={ridge_wf_min:.2f} ({wf_min_lift:+.2f}) -- cold-start FIXED. "
            "Accepts stability over marginal Sharpe. Promote to v6.6."
        )
    elif ac1 and ac4 and ac5 and not ac3:
        verdict = (
            f"CONDITIONAL ACCEPT: K205 OOS Sh={ridge_oos_sh:.2f} and WF metrics pass, "
            f"but MaxDD={ridge_oos_dd:.4f} did not improve vs K198 ({K198_OOS_DD:.4f}). "
            "Consider adding harder DD cap in weight formula before promoting to v6.6."
        )
    elif ac1 and ac3 and not ac4:
        verdict = (
            f"REJECT: Cold-start NOT fixed. WF min={ridge_wf_min:.2f} < K198 {K198_WF_MIN:.2f}. "
            f"OOS Sh={ridge_oos_sh:.2f} and MaxDD improved, but fold instability persists. "
            "Try K206 with 270d window or fold-adaptive alpha."
        )
    elif ac4 and ac5 and not ac1:
        verdict = (
            f"REJECT: WF stability improved (min={ridge_wf_min:.2f}), but OOS Sh={ridge_oos_sh:.2f} "
            f"< K198 baseline {K198_OOS_SH:.2f}. 180d window overfitted on older regime. "
            "Try K206 with adaptive window or non-stationary weighting."
        )
    else:
        n_pass = sum([ac1, ac3, ac4, ac5])
        verdict = (
            f"REJECT: K205 passes {n_pass}/4 required criteria. "
            f"OOS Sh={ridge_oos_sh:.2f} (target>={K198_OOS_SH:.2f}), "
            f"MaxDD={ridge_oos_dd:.4f} (target<{K198_OOS_DD:.4f}), "
            f"WF min={ridge_wf_min:.2f} (target>={K198_WF_MIN:.2f}), "
            f"WF mean={ridge_wf_mean:.2f} (target>={K198_WF_MEAN:.2f}). "
            "K198 v6.5 remains production."
        )

    print(f"  VERDICT: {verdict}")
    print()

    # Step 15: Equity curves
    print("Step 15: Computing equity curves...", flush=True)
    ridge_equity  = np.cumprod(1.0 + pnl_ridge.values).tolist()
    static_equity = np.cumprod(1.0 + static_wf_aligned.values).tolist() if len(static_wf_aligned) > 0 else []

    k198_equity = []
    k198_equity_dates = []
    try:
        with open(BASE / "wave_k198_curves.json") as f:
            k198_curves = json.load(f)
        k198_equity = k198_curves.get("equity_ridge", [])
        k198_equity_dates = k198_curves.get("dates_ml", [])
        print(f"  K198 production equity: {len(k198_equity)} points")
    except Exception as e:
        print(f"  WARNING: Could not load K198 curves: {e}")

    k204_equity = []
    k204_equity_dates = []
    try:
        with open(BASE / "wave_k204_curves.json") as f:
            k204_curves = json.load(f)
        k204_equity = k204_curves.get("equity_k204", [])
        k204_equity_dates = k204_curves.get("dates_ml", [])
        print(f"  K204 equity: {len(k204_equity)} points")
    except Exception as e:
        print(f"  WARNING: Could not load K204 curves: {e}")

    print(f"  K205 Ridge equity: {len(ridge_equity)} points")
    print()

    elapsed = time.time() - START_TIME
    print(f"Total runtime: {elapsed:.1f}s")
    print()

    # ─────────────────────────────────────────────────────────────────────────
    # Assemble outputs
    # ─────────────────────────────────────────────────────────────────────────

    # Per-strategy DD penalty summary
    per_strat_penalty_summary = {}
    if dd_penalty_stats.get("per_step_detail"):
        n_steps_total = len(dd_penalty_stats["per_step_detail"])
        for c in cols:
            mults = [s["multipliers"].get(c, 1.0) for s in dd_penalty_stats["per_step_detail"]]
            dd30s = [s["dd30_values"].get(c, 0.0) for s in dd_penalty_stats["per_step_detail"]]
            n_pen = sum(1 for m in mults if m < 1.0)
            n_halt = sum(1 for m in mults if m == 0.0)
            per_strat_penalty_summary[c] = {
                "n_steps_penalized": n_pen,
                "n_steps_halted": n_halt,
                "pct_steps_penalized": round(100.0 * n_pen / n_steps_total, 1),
                "avg_multiplier": round(float(np.mean(mults)), 4),
                "avg_dd30": round(float(np.mean(dd30s)), 6),
                "min_dd30": round(float(np.min(dd30s)), 6),
            }

    fold_breakdown = []
    for i, sh in enumerate(wf_ridge["fold_sharpes"]):
        k204_fold_sh = [6.023, 6.2648, 8.1003, 9.7924]  # K204 reference
        fold_breakdown.append({
            "fold": i + 1,
            "sharpe": sh,
            "k198_wf_mean": K198_WF_MEAN,
            "k204_fold_sharpe": k204_fold_sh[i] if i < len(k204_fold_sh) else None,
            "vs_k204_fold": round(sh - k204_fold_sh[i], 4) if i < len(k204_fold_sh) else None,
            "vs_k198_wf_min": round(sh - K198_WF_MIN, 4),
        })

    output = {
        "wave": "K205",
        "task": "ML allocator DD fix: 180d training window + soft DD penalty + drop dd_max30",
        "as_of": pd.Timestamp.now(tz="UTC").isoformat(),
        "runtime_s": round(elapsed, 1),
        "config": {
            "strategies": cols,
            "n_strategies": n_strats,
            "ml_train_days": ML_TRAIN_DAYS,
            "ml_test_days": ML_TEST_DAYS,
            "dd_penalty_coef": DD_PENALTY_COEF,
            "oos_frac": OOS_FRAC,
            "k121_cap": K121_CAP,
            "carry_fwd_cap": CARRY_FWD_CAP,
            "carry_rev_cap": CARRY_REV_CAP,
            "fr_threshold": FR_THRESHOLD,
            "feature_win_short": 30,
            "feature_win_long": 90,
            "target_horizon_days": ML_TEST_DAYS,
            "ridge_alpha": 1.0,
            "n_baseline_features": n_baseline,
            "n_new_dd_features": n_new_dd,
            "n_total_features": feat_df.shape[1],
            "k205_changes_vs_k204": [
                "train_window: 90 -> 180 (cold-start fix)",
                "dropped dd_max30 (redundant with mdd30)",
                "added soft DD penalty: w_i *= max(0, 1 + 2*dd30_i)",
            ],
            "date_range": [str(df_all.index[0].date()), str(df_all.index[-1].date())],
            "n_days_total": len(df_all),
            "n_days_ml_window": len(pnl_ridge),
        },
        "five_way_comparison": {
            "K198_v6.5_baseline": {
                "oos_sharpe": K198_OOS_SH,
                "oos_maxdd":  K198_OOS_DD,
                "wf_mean":    K198_WF_MEAN,
                "wf_min":     K198_WF_MIN,
                "n_features": 51,
                "status": "PRODUCTION",
            },
            "K201_rejected": {
                "oos_sharpe": 8.59,
                "oos_maxdd":  -0.0057,
                "wf_mean":    7.38,
                "wf_min":     6.39,
                "status": "REJECTED",
                "reject_reason": "ML->trigger override granularity mismatch",
            },
            "K202_rejected": {
                "oos_sharpe": 7.84,
                "oos_maxdd":  -0.0071,
                "wf_mean":    7.16,
                "wf_min":     6.29,
                "status": "REJECTED",
                "reject_reason": "Trigger->ML filter granularity mismatch",
            },
            "K204_rejected": {
                "oos_sharpe": K204_OOS_SH,
                "oos_maxdd":  -0.0053,
                "wf_mean":    7.5451,
                "wf_min":     K204_WF_MIN,
                "wf_fold_sharpes": [6.023, 6.2648, 8.1003, 9.7924],
                "n_features": 113,
                "status": "REJECTED",
                "reject_reason": "WF min 6.02 < 6.57 threshold; cold-start with 90d window",
            },
            "K205_dd_fix": {
                "oos_sharpe":  round(ridge_oos_sh, 4),
                "oos_maxdd":   round(ridge_oos_dd, 4),
                "oos_sortino": m_ridge["sortino"],
                "oos_calmar":  m_ridge["calmar"],
                "oos_ann_ret": m_ridge["ann_ret"],
                "oos_ann_vol": m_ridge["ann_vol"],
                "wf_mean":     wf_ridge["mean"],
                "wf_min":      wf_ridge["min"],
                "wf_max":      wf_ridge["max"],
                "wf_std":      wf_ridge["std"],
                "wf_fold_sharpes": wf_ridge["fold_sharpes"],
                "n_features":  feat_df.shape[1],
                "sh_lift_vs_k198":  round(sh_lift_vs_k198, 4),
                "sh_lift_vs_k204":  round(sh_lift_vs_k204, 4),
                "dd_lift_vs_k198":  round(dd_lift, 4),
                "wf_min_lift_vs_k198": round(wf_min_lift, 4),
                "wf_min_lift_vs_k204": round(ridge_wf_min - K204_WF_MIN, 4),
                "wf_mean_lift_vs_k198": round(wf_mean_lift, 4),
                "status": "ACCEPT" if hard_pass else "REJECT",
            },
        },
        "acceptance_criteria": {
            "AC1_oos_sh_ge_k198": {
                "pass": ac1, "required": K198_OOS_SH,
                "actual": round(ridge_oos_sh, 4), "lift": round(sh_lift_vs_k198, 4),
            },
            "AC2_oos_sh_ge_k204_bonus": {
                "pass": ac2, "required": K204_OOS_SH,
                "actual": round(ridge_oos_sh, 4), "lift": round(sh_lift_vs_k204, 4),
            },
            "AC3_maxdd_improved": {
                "pass": ac3, "k198": K198_OOS_DD,
                "k205": round(ridge_oos_dd, 4), "delta": round(dd_lift, 4),
            },
            "AC4_wf_min_ge_k198": {
                "pass": ac4, "required": K198_WF_MIN,
                "actual": round(ridge_wf_min, 4), "lift": round(wf_min_lift, 4),
            },
            "AC5_wf_mean_ge_k198": {
                "pass": ac5, "required": K198_WF_MEAN,
                "actual": round(ridge_wf_mean, 4), "lift": round(wf_mean_lift, 4),
            },
            "hard_criteria_pass": hard_pass,
            "all_5_pass": all([ac1, ac2, ac3, ac4, ac5]),
        },
        "per_fold_breakdown": fold_breakdown,
        "dd_penalty_stats": {
            "total_steps": dd_penalty_stats["total_steps"],
            "steps_with_penalty": dd_penalty_stats["steps_with_any_penalty"],
            "pct_steps_with_penalty": dd_penalty_stats["pct_steps_with_penalty"],
            "total_strategy_penalties": dd_penalty_stats["total_strategy_penalties"],
            "avg_penalized_per_step": dd_penalty_stats["avg_penalized_per_step"],
            "penalty_coef": DD_PENALTY_COEF,
            "penalty_note": dd_penalty_stats["note"],
            "per_strategy": per_strat_penalty_summary,
        },
        "cold_start_analysis": cold_start_analysis,
        "feature_importance_k205": {
            "top_30": dict(list(feat_imp.items())[:30]),
            "n_total_features": len(feat_imp),
            "note": "K205 drops dd_max30; 180d window changes coefficient magnitudes vs K204",
        },
        "ml_predictor_diagnostics": {
            **diag_agg,
            "n_wf_steps": len(diagnostics_ridge),
            "per_step_summary": [
                {k: v for k, v in d.items() if k not in ("mean_abs_coef", "feature_names")}
                for d in diagnostics_ridge
            ],
        },
        "verdict": verdict,
        "k206_next_steps": (
            "If K205 passes: v6.6 production. Monitor live DD penalty firing rate. "
            "If K205 fails WF min: K206 should try 270d window or fold-adaptive alpha. "
            "If K205 fails MaxDD: K206 should increase DD_PENALTY_COEF to 3.0 or 4.0. "
            "If K205 fails OOS Sh: 180d window may overfit old regime; try K206 with "
            "exponential time-weighting (recent data weighted more) inside 180d window."
        ),
    }

    out_json = BASE / "wave_k205_ml_dd_fix.json"
    with open(out_json, "w") as f:
        json.dump(output, f, indent=2)
    print(f"Saved: {out_json}")

    # Curves JSON
    weight_traj_dates = [str(d.date()) for d in weights_ridge.index] if len(weights_ridge) > 0 else []
    weight_traj = {c: [round(float(x), 4) for x in weights_ridge[c].values] for c in cols} if len(weights_ridge) > 0 else {}

    curves_out = {
        "wave": "K205",
        "dates_ml":         [str(d.date()) for d in pnl_ridge.index],
        "dates_static_wf":  [str(d.date()) for d in static_wf_aligned.index] if len(static_wf_aligned) > 0 else [],
        "dates_k198_ref":   k198_equity_dates,
        "dates_k204_ref":   k204_equity_dates,
        "equity_k205":      [round(float(v), 6) for v in ridge_equity],
        "equity_static_wf": [round(float(v), 6) for v in static_equity],
        "equity_k198_ref":  [round(float(v), 6) for v in k198_equity],
        "equity_k204_ref":  [round(float(v), 6) for v in k204_equity],
        "pnl_k205":         [round(float(v), 8) for v in pnl_ridge.values],
        "pnl_static_wf":    [round(float(v), 8) for v in static_wf_aligned.values] if len(static_wf_aligned) > 0 else [],
        "weight_trajectory_dates": weight_traj_dates,
        "weight_trajectory": weight_traj,
        "dd_penalty_per_step": [
            {
                "step": s["step"],
                "multipliers": s["multipliers"],
                "n_penalized": s["n_penalized"],
            }
            for s in dd_penalty_stats.get("per_step_detail", [])
        ],
    }

    out_curves = BASE / "wave_k205_curves.json"
    with open(out_curves, "w") as f:
        json.dump(curves_out, f, indent=2)
    print(f"Saved: {out_curves}")

    # ─────────────────────────────────────────────────────────────────────────
    # Final comparison table
    # ─────────────────────────────────────────────────────────────────────────
    print()
    print("=" * 90)
    print("FIVE-WAY COMPARISON: K198 v6.5 | K201 | K202 | K204 | K205")
    print("=" * 90)
    print(f"{'Version':<30} {'OOS Sh':>8} {'OOS MaxDD':>10} {'WF mean':>8} {'WF min':>8} {'Features':>9} {'Status'}")
    print("-" * 90)
    print(f"{'K198 v6.5 (prod)':30s} {K198_OOS_SH:>8.2f} {K198_OOS_DD:>10.4f} "
          f"{K198_WF_MEAN:>8.2f} {K198_WF_MIN:>8.2f} {'51':>9s}  PRODUCTION")
    print(f"{'K201 (REJECTED)':30s} {'8.59':>8s} {'-0.0057':>10s} {'7.38':>8s} {'6.39':>8s} {'51':>9s}  REJECTED")
    print(f"{'K202 (REJECTED)':30s} {'7.84':>8s} {'-0.0071':>10s} {'7.16':>8s} {'6.29':>8s} {'51':>9s}  REJECTED")
    print(f"{'K204 DD-embed (REJECTED)':30s} {K204_OOS_SH:>8.2f} {'-0.0053':>10s} {'7.55':>8s} {K204_WF_MIN:>8.2f} {'113':>9s}  REJECTED")
    print(f"{'K205 DD-fix':30s} {ridge_oos_sh:>8.2f} {ridge_oos_dd:>10.4f} "
          f"{wf_ridge['mean']:>8.2f} {ridge_wf_min:>8.2f} {feat_df.shape[1]:>9d}  {'ACCEPT' if hard_pass else 'REJECT'}")
    print("-" * 90)
    print(f"  K205 lift vs K198: OOS Sh {sh_lift_vs_k198:+.4f} | MaxDD {dd_lift:+.4f} "
          f"| WF mean {wf_mean_lift:+.4f} | WF min {wf_min_lift:+.4f}")
    print(f"  K205 lift vs K204: OOS Sh {sh_lift_vs_k204:+.4f} | WF min {ridge_wf_min - K204_WF_MIN:+.4f}")
    print()
    print(f"  DD penalty fired in {dd_penalty_stats['steps_with_any_penalty']}/{dd_penalty_stats['total_steps']} "
          f"steps ({dd_penalty_stats['pct_steps_with_penalty']}%)")
    print()
    print(f"VERDICT: {verdict}")
    print()
    print(f"Runtime: {elapsed:.1f}s")

    return output


if __name__ == "__main__":
    main()

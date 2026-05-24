"""Wave K204 — ML Allocator with Embedded Drawdown & Regime Features (v6.6 candidate).

Objective:
  Extend K198's 51-feature Ridge ML allocator with drawdown/recovery features
  embedded directly into the feature matrix. Model self-modulates based on
  DD/regime risk — no external gate or override.

Changes vs K198 (v6.5 baseline):
  Per-strategy new features (×10 strategies = +60 cols):
    {strat}__dd30:        30-day cumulative drawdown (peak-to-current loss)
    {strat}__dd90:        90-day cumulative drawdown
    {strat}__dd_max30:    rolling 30d max drawdown (worst trough)
    {strat}__sh_neg30:    count of days in last 30d with negative daily return
    {strat}__recovery:    binary — 1 if strategy is recovering from recent DD
    {strat}__calmar30:    30d Calmar ratio (ann_ret / |max_dd|)

  Panel-level new features (+2):
    fr_mean_ann_t:        same as K198 (already present, kept for continuity)
    panel_dd30:           equal-weight panel 30d drawdown
    panel_recovery:       binary — panel recovering from DD

  Total: ~51 + 62 = ~113 features (after deduplications; Ridge L2 handles collinearity)

Acceptance criteria vs K198:
  - OOS Sh >= 10.28
  - MaxDD < -0.0053 (must IMPROVE)
  - WF min >= 6.57
  - DD features must have non-zero Ridge coefficients

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
TRAIN_FRAC   = 0.70

ML_TRAIN_DAYS = 90
ML_TEST_DAYS  = 30

# K198 v6.5 baseline reference
K198_OOS_SH  = 10.28
K198_OOS_DD  = -0.0053
K198_WF_MEAN = 7.91
K198_WF_MIN  = 6.57

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
    """30/90d cumulative drawdown: (end_equity / peak) - 1."""
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
# Weight utilities (identical to K198)
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
# Data loading (identical to K198)
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
    fwd_trimmed  = fwd_ret[(fwd_ret.index >= all_start)  & (fwd_ret.index <= all_end)]
    rev_trimmed  = rev_ret[(rev_ret.index >= all_start)  & (rev_ret.index <= all_end)]

    df = pd.concat([base_trimmed, fwd_trimmed, rev_trimmed], axis=1).dropna()
    print(f"  Component returns: {df.shape[0]} days × {df.shape[1]} strategies")
    print(f"  Date range: {df.index[0].date()} → {df.index[-1].date()}")
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
# K204 Feature engineering — extended with DD features
# ─────────────────────────────────────────────────────────────────────────────

def build_features_k204(
    df: pd.DataFrame,
    fr_mean: Optional[pd.Series],
    win_short: int = 30,
    win_long: int = 90,
) -> pd.DataFrame:
    """
    Build extended feature matrix for K204.

    Per-strategy features (same as K198):
      {s}__sh30, {s}__sh90, {s}__vol30, {s}__mdd30, {s}__xcorr

    NEW per-strategy features:
      {s}__dd30:     cumulative drawdown over last 30d (peak-to-current)
      {s}__dd90:     cumulative drawdown over last 90d
      {s}__dd_max30: rolling 30d max drawdown (worst trough in window)
      {s}__sh_neg30: fraction of days in last 30d with negative daily return
      {s}__recovery: binary — 1 if current equity > equity 5d ago AND mdd30 < -0.005
      {s}__calmar30: 30d Calmar ratio

    Panel-level features:
      fr_mean_ann:   panel FR mean (same as K198)
      panel_dd30:    equal-weight panel 30d cumulative drawdown
      panel_recovery: binary — panel in recovery mode
    """
    n_strats = df.shape[1]
    cols = list(df.columns)
    R = df.values  # shape (n_days, n_strats)
    n = len(R)
    feat_rows = []

    # Precompute equal-weight panel returns for panel-level DD features
    panel_ret = R.mean(axis=1)  # shape (n_days,)

    for t in range(win_long, n):
        row = {}
        slice_long  = R[t - win_long:t]   # shape (90, n_strats)
        slice_short = R[t - win_short:t]  # shape (30, n_strats)

        # Cross-correlation 30d
        if n_strats > 1:
            corr_mat = np.corrcoef(slice_short.T)
            np.fill_diagonal(corr_mat, 0.0)
        else:
            corr_mat = np.zeros((1, 1))

        for i, strat in enumerate(cols):
            prefix = f"{strat}__"
            r_short = slice_short[:, i]
            r_long  = slice_long[:, i]

            # ── K198 baseline features ──────────────────────────────────────
            row[f"{prefix}sh30"]  = sharpe_d(r_short)
            row[f"{prefix}sh90"]  = sharpe_d(r_long)
            row[f"{prefix}vol30"] = float(r_short.std(ddof=1) * math.sqrt(TRADING_DAYS))
            row[f"{prefix}mdd30"] = max_dd_d(r_short)
            if n_strats > 1:
                other_corrs = np.delete(corr_mat[i], i)
                row[f"{prefix}xcorr"] = float(np.mean(other_corrs))
            else:
                row[f"{prefix}xcorr"] = 0.0

            # ── K204 NEW DD features ────────────────────────────────────────
            # dd30: cumulative 30d drawdown (negative = loss from peak in window)
            row[f"{prefix}dd30"] = cumulative_dd(r_short)

            # dd90: cumulative 90d drawdown
            row[f"{prefix}dd90"] = cumulative_dd(r_long)

            # dd_max30: rolling 30d max drawdown (same as mdd30 but explicit for clarity)
            row[f"{prefix}dd_max30"] = max_dd_d(r_short)

            # sh_neg30: fraction of negative daily returns in last 30d
            row[f"{prefix}sh_neg30"] = float(np.sum(r_short < 0) / len(r_short))

            # recovery: binary — in recovery if current equity is rising from recent trough
            # heuristic: last 5d cumret > 0 AND 30d drawdown < -0.002
            eq_short = np.cumprod(1.0 + r_short)
            last5_ret = float(eq_short[-1] / eq_short[-6] - 1.0) if len(eq_short) >= 6 else 0.0
            dd30_val = float(cumulative_dd(r_short))
            row[f"{prefix}recovery"] = float(last5_ret > 0 and dd30_val < -0.002)

            # calmar30: 30d Calmar
            row[f"{prefix}calmar30"] = calmar_30d(r_short)

        # ── Panel-level features ────────────────────────────────────────────
        # FR regime indicator (same as K198)
        if fr_mean is not None and len(fr_mean) > 0:
            fr_date = df.index[t]
            fr_aligned = fr_mean.reindex([fr_date], method="ffill")
            row["fr_mean_ann"] = float(fr_aligned.iloc[0]) if not fr_aligned.isna().all() else 0.0
        else:
            row["fr_mean_ann"] = 0.0

        # panel_dd30: equal-weight panel 30d cumulative drawdown
        panel_short = panel_ret[t - win_short:t]
        row["panel_dd30"] = cumulative_dd(panel_short)

        # panel_recovery: panel in recovery mode
        panel_eq = np.cumprod(1.0 + panel_short)
        panel_last5 = float(panel_eq[-1] / panel_eq[-6] - 1.0) if len(panel_eq) >= 6 else 0.0
        row["panel_recovery"] = float(panel_last5 > 0 and row["panel_dd30"] < -0.002)

        feat_rows.append(row)

    feat_df = pd.DataFrame(feat_rows, index=df.index[win_long:])
    return feat_df


def build_targets(df: pd.DataFrame, horizon: int = 30) -> pd.DataFrame:
    """Build next-horizon-day forward Sharpe targets per strategy (identical to K198)."""
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
# ML walk-forward (identical logic to K198, uses extended features)
# ─────────────────────────────────────────────────────────────────────────────

def ml_walk_forward(
    df: pd.DataFrame,
    feat_df: pd.DataFrame,
    target_df: pd.DataFrame,
    train_days: int = ML_TRAIN_DAYS,
    test_days:  int = ML_TEST_DAYS,
    alpha:      float = 1.0,
) -> Tuple[pd.DataFrame, pd.Series, list]:
    cols = list(df.columns)
    n_strats = len(cols)

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

        t_test_start    = t_start
        t_test_end      = min(t_start + test_days, n)
        X_test          = feat_arr[t_test_start:t_test_end]
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

        actual_targets = target_arr[t_test_start:t_test_end].mean(axis=0)
        dir_correct = np.array([
            (preds[i] > 0) == (actual_targets[i] > 0)
            for i in range(n_strats)
        ])

        pos_preds = np.maximum(preds, 0.0)
        if pos_preds.sum() < 1e-10:
            w = w_equal(n_strats)
        else:
            w = pos_preds / pos_preds.sum()
        w = apply_all_caps(w, cols)

        # Store mean |coef| for this step (for feature importance over time)
        mean_coef = np.mean(coef_rows, axis=0) if coef_rows else np.zeros(X_train_s.shape[1])

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
            "mean_abs_coef": mean_coef.tolist(),
            "feature_names": list(feat_aligned.columns),
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
        return pd.DataFrame(), pd.Series(dtype=float), []

    weights_df = pd.DataFrame(wf_weights, index=wf_dates)
    pnl_series = pd.Series(wf_pnl, index=wf_dates, name="ml_pnl")
    return weights_df, pnl_series, diagnostics


# ─────────────────────────────────────────────────────────────────────────────
# FR trigger (same as K198)
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
# Feature importance (full-period Ridge fit)
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


def dd_feature_importance(feat_imp: dict) -> dict:
    """Extract just the new K204 DD features from feature importance."""
    dd_keys = ["dd30", "dd90", "dd_max30", "sh_neg30", "recovery", "calmar30", "panel_dd30", "panel_recovery"]
    result = {}
    for k, v in feat_imp.items():
        suffix = k.split("__")[-1] if "__" in k else k
        if suffix in dd_keys or k in ["panel_dd30", "panel_recovery"]:
            result[k] = v
    return dict(sorted(result.items(), key=lambda x: x[1], reverse=True))


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
# Weight trajectory analysis: does K204 reduce exposure during DD?
# ─────────────────────────────────────────────────────────────────────────────

def analyze_dd_aware_weights(
    weights_df: pd.DataFrame,
    df_all: pd.DataFrame,
    feat_df: pd.DataFrame,
) -> dict:
    """
    Compare average weights during high-DD vs low-DD periods.
    High-DD: panel_dd30 < -0.01 (panel losing >1% from 30d peak).
    Low-DD: panel_dd30 > -0.002.
    """
    if "panel_dd30" not in feat_df.columns or len(weights_df) == 0:
        return {"note": "panel_dd30 not available or no weights"}

    panel_dd = feat_df["panel_dd30"].reindex(weights_df.index, method="ffill")

    high_dd_mask = panel_dd < -0.01
    low_dd_mask  = panel_dd > -0.002

    result = {}
    for col in weights_df.columns:
        w_high = weights_df.loc[high_dd_mask, col].mean() if high_dd_mask.sum() > 0 else None
        w_low  = weights_df.loc[low_dd_mask,  col].mean() if low_dd_mask.sum()  > 0 else None
        result[col] = {
            "weight_high_dd":  round(float(w_high), 4) if w_high is not None else None,
            "weight_low_dd":   round(float(w_low),  4) if w_low  is not None else None,
            "dd_sensitivity":  round(float(w_low - w_high), 4) if (w_high is not None and w_low is not None) else None,
        }

    return {
        "n_high_dd_days": int(high_dd_mask.sum()),
        "n_low_dd_days":  int(low_dd_mask.sum()),
        "per_strategy":   result,
        "interpretation": (
            "dd_sensitivity > 0 means strategy gets MORE weight when DD is low (healthy). "
            "dd_sensitivity < 0 means strategy gets LESS weight when DD is low (unusual). "
            "The ML model learns this pattern from embedded DD features."
        ),
    }


# ─────────────────────────────────────────────────────────────────────────────
# VIF check (Ridge-compatible — just Pearson correlation matrix)
# ─────────────────────────────────────────────────────────────────────────────

def vif_check(feat_df: pd.DataFrame, top_n: int = 10) -> dict:
    """
    Compute max pairwise Pearson correlation for new DD features.
    Ridge handles multicollinearity, but we flag extreme correlations.
    """
    dd_cols = [c for c in feat_df.columns if any(
        s in c for s in ["dd30", "dd90", "dd_max30", "sh_neg30", "recovery", "calmar30"]
    )]
    if len(dd_cols) < 2:
        return {"note": "Too few DD columns for VIF"}

    sub = feat_df[dd_cols].dropna()
    if len(sub) < 10:
        return {"note": "Insufficient data for correlation"}

    X = np.nan_to_num(sub.values, nan=0.0)
    corr = np.corrcoef(X.T)
    np.fill_diagonal(corr, 0.0)

    # Find top correlations
    pairs = []
    for i in range(len(dd_cols)):
        for j in range(i + 1, len(dd_cols)):
            pairs.append((dd_cols[i], dd_cols[j], float(corr[i, j])))

    pairs.sort(key=lambda x: abs(x[2]), reverse=True)
    top_pairs = [{"feat_a": a, "feat_b": b, "corr": round(c, 4)}
                 for a, b, c in pairs[:top_n]]

    max_corr = max(abs(p["corr"]) for p in top_pairs) if top_pairs else 0.0

    return {
        "max_pairwise_corr_dd_features": round(max_corr, 4),
        "ridge_handles_multicollinearity": True,
        "concern_threshold": 0.95,
        "flagged": bool(max_corr > 0.95),
        "top_correlations": top_pairs,
    }


# ─────────────────────────────────────────────────────────────────────────────
# Main
# ─────────────────────────────────────────────────────────────────────────────

def main():
    print("=" * 72)
    print("Wave K204 — ML Allocator with Embedded DD Features (v6.6 candidate)")
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
        print(f"  FR mean range: {fr_mean.index[0].date()} → {fr_mean.index[-1].date()}")
        fr_aligned_check = fr_mean.reindex(df_all.index, method="ffill")
        print(f"  FR mean stats: mean={fr_aligned_check.mean():.4f} std={fr_aligned_check.std():.4f}")
    else:
        print("  WARNING: FR data unavailable — regime feature will be zero")
    print()

    # Step 3: Apply FR trigger (same as K198)
    print("Step 3: Applying FR trigger (K121, K133)...", flush=True)
    if len(fr_mean) > 0:
        df_triggered = apply_fr_trigger(df_all, fr_mean)
        n_trigger = int((fr_mean.reindex(df_all.index, method="ffill") < FR_THRESHOLD).sum())
        print(f"  Trigger fires {n_trigger} / {len(df_all)} days ({n_trigger/len(df_all)*100:.1f}%)")
    else:
        df_triggered = df_all.copy()
        print("  No FR trigger applied")
    print()

    # Step 4: Build K204 extended feature matrix
    print("Step 4: Building K204 extended feature matrix (51 baseline + DD features)...", flush=True)
    feat_df = build_features_k204(df_triggered, fr_mean if len(fr_mean) > 0 else None)
    print(f"  Feature matrix: {feat_df.shape[0]} rows × {feat_df.shape[1]} features")
    print(f"  Feature date range: {feat_df.index[0].date()} → {feat_df.index[-1].date()}")
    # Identify new vs baseline features
    baseline_suffixes = {"sh30", "sh90", "vol30", "mdd30", "xcorr"}
    new_dd_suffixes   = {"dd30", "dd90", "dd_max30", "sh_neg30", "recovery", "calmar30"}
    n_baseline = sum(1 for c in feat_df.columns if c.split("__")[-1] in baseline_suffixes or c == "fr_mean_ann")
    n_new_dd   = sum(1 for c in feat_df.columns if c.split("__")[-1] in new_dd_suffixes or c in {"panel_dd30", "panel_recovery"})
    print(f"  Baseline features: {n_baseline} | New DD features: {n_new_dd} | Total: {feat_df.shape[1]}")
    print()

    # Step 5: Build targets
    print("Step 5: Building forward Sharpe targets (horizon=30d)...", flush=True)
    target_df = build_targets(df_triggered, horizon=ML_TEST_DAYS)
    print(f"  Target matrix: {target_df.shape[0]} rows × {target_df.shape[1]} strategies")
    print()

    # Step 6: VIF / correlation check on new DD features
    print("Step 6: Multicollinearity check on new DD features...", flush=True)
    vif_result = vif_check(feat_df)
    print(f"  Max pairwise corr (DD features): {vif_result.get('max_pairwise_corr_dd_features', 'N/A')}")
    if vif_result.get("flagged"):
        print("  WARNING: extreme correlation detected (>0.95) — Ridge L2 still handles")
    else:
        print("  OK: no extreme multicollinearity")
    print()

    # Step 7: Ridge walk-forward with extended features
    print("Step 7: Ridge regression walk-forward (90d train → 30d test)...", flush=True)
    weights_ridge, pnl_ridge, diagnostics_ridge = ml_walk_forward(
        df_triggered, feat_df, target_df,
        train_days=ML_TRAIN_DAYS,
        test_days=ML_TEST_DAYS,
        alpha=1.0,
    )
    if len(pnl_ridge) == 0:
        print("  ERROR: Ridge WF returned empty PnL")
        return
    print(f"  Ridge WF PnL: {len(pnl_ridge)} days, "
          f"{pnl_ridge.index[0].date()} → {pnl_ridge.index[-1].date()}")
    print()

    # Step 8: Walk-forward static P3 (same windows, for comparison)
    print("Step 8: Walk-forward static P3 (matched windows)...", flush=True)
    pnl_static_wf, _ = run_wf_static_p3(df_triggered)
    common_start = pnl_ridge.index[0]
    common_end   = pnl_ridge.index[-1]
    static_wf_aligned = pnl_static_wf[
        (pnl_static_wf.index >= common_start) & (pnl_static_wf.index <= common_end)
    ]
    print(f"  Static P3 WF: {len(static_wf_aligned)} days (aligned)")
    print()

    # Step 9: OOS metrics
    print("Step 9: OOS metrics (last 30%)...", flush=True)

    def oos_cut(s: pd.Series) -> pd.Series:
        cut = int(len(s) * (1 - OOS_FRAC))
        return s.iloc[cut:]

    oos_ridge  = oos_cut(pnl_ridge)
    oos_static = oos_cut(static_wf_aligned) if len(static_wf_aligned) > 0 else oos_cut(pnl_ridge)

    m_ridge  = metrics_pkg(oos_ridge.values)
    m_static = metrics_pkg(oos_static.values)

    print(f"  K198 v6.5 baseline:  OOS Sh={K198_OOS_SH:.4f} MaxDD={K198_OOS_DD:.4f}")
    print(f"  K204 Ridge (OOS):    OOS Sh={m_ridge['sharpe']:.4f} MaxDD={m_ridge['max_dd']:.4f}")
    print(f"  Static P3 (matched): OOS Sh={m_static['sharpe']:.4f} MaxDD={m_static['max_dd']:.4f}")
    print()

    # Step 10: WF fold analysis
    print("Step 10: Walk-forward fold analysis...", flush=True)
    wf_ridge  = wf_fold_sharpes(pnl_ridge)
    wf_static = wf_fold_sharpes(static_wf_aligned) if len(static_wf_aligned) > 0 else wf_fold_sharpes(pnl_ridge)

    print(f"  K204 Ridge WF:  mean={wf_ridge['mean']:.4f}  min={wf_ridge['min']:.4f}  folds={wf_ridge['fold_sharpes']}")
    print(f"  Static P3 WF:   mean={wf_static['mean']:.4f}  min={wf_static['min']:.4f}  folds={wf_static['fold_sharpes']}")
    print()

    # Step 11: ML predictor diagnostics
    print("Step 11: ML predictor diagnostics...", flush=True)
    diag_agg = aggregate_diagnostics(diagnostics_ridge, cols)
    print(f"  Overall R²: {diag_agg.get('overall_mean_r2', 'N/A')}")
    print(f"  Overall dir acc: {diag_agg.get('overall_mean_dir_acc', 'N/A')}")
    print()

    # Step 12: Feature importance (full-period fit)
    print("Step 12: Feature importance (K204 extended vs K198 baseline)...", flush=True)
    feat_imp = compute_feature_importance(feat_df, target_df, cols)
    print(f"  Total features: {len(feat_imp)}")
    print("  Top 20 features:")
    for name, val in list(feat_imp.items())[:20]:
        tag = "[K198]" if name.split("__")[-1] in baseline_suffixes or name == "fr_mean_ann" else "[K204-NEW]"
        print(f"    {name:40s} {val:.6f}  {tag}")
    print()

    # Extract DD-specific feature importance
    dd_feat_imp = dd_feature_importance(feat_imp)
    print("  New DD features (K204 additions):")
    for name, val in list(dd_feat_imp.items())[:20]:
        print(f"    {name:40s} {val:.6f}")
    has_nonzero_dd = any(v > 1e-8 for v in dd_feat_imp.values())
    print(f"  DD features non-zero: {has_nonzero_dd} ({sum(1 for v in dd_feat_imp.values() if v > 1e-8)}/{len(dd_feat_imp)} features)")
    print()

    # Step 13: DD-aware weight trajectory analysis
    print("Step 13: DD-aware weight analysis (high-DD vs low-DD periods)...", flush=True)
    dd_weight_analysis = analyze_dd_aware_weights(weights_ridge, df_all, feat_df)
    print(f"  High-DD days (panel_dd30 < -1%): {dd_weight_analysis.get('n_high_dd_days', 0)}")
    print(f"  Low-DD days  (panel_dd30 > -0.2%): {dd_weight_analysis.get('n_low_dd_days', 0)}")
    if "per_strategy" in dd_weight_analysis:
        print("  Per-strategy DD sensitivity (w_low_DD - w_high_DD, positive = risk-on during calm):")
        for strat, vals in dd_weight_analysis["per_strategy"].items():
            sens = vals.get("dd_sensitivity")
            if sens is not None:
                direction = "risk-on during calm" if sens > 0 else "risk-off during calm"
                print(f"    {strat:20s}: high_DD_w={vals['weight_high_dd']:.4f}  low_DD_w={vals['weight_low_dd']:.4f}  sensitivity={sens:+.4f}  ({direction})")
    print()

    # Step 14: Acceptance criteria
    print("Step 14: Acceptance criteria for K204 → v6.6...", flush=True)
    ridge_oos_sh  = m_ridge["sharpe"]
    ridge_oos_dd  = m_ridge["max_dd"]
    ridge_wf_min  = wf_ridge["min"]
    ridge_wf_mean = wf_ridge["mean"]
    dir_acc       = diag_agg.get("overall_mean_dir_acc", 0.0)

    # K204-specific acceptance criteria (vs K198, not K196)
    ac1 = ridge_oos_sh >= K198_OOS_SH          # OOS Sh >= 10.28
    ac2 = ridge_oos_dd > K198_OOS_DD            # MaxDD IMPROVED (less negative)
    ac3 = ridge_wf_min >= K198_WF_MIN           # WF min >= 6.57
    ac4 = has_nonzero_dd                         # DD features demonstrably used

    print(f"  AC1: OOS Sh >= {K198_OOS_SH:.2f}?  K204={ridge_oos_sh:.4f} → {'PASS' if ac1 else 'FAIL'}")
    print(f"  AC2: MaxDD < {K198_OOS_DD:.4f} (improve)?  K204={ridge_oos_dd:.4f} → {'PASS' if ac2 else 'FAIL'}")
    print(f"  AC3: WF min >= {K198_WF_MIN:.2f}?  K204={ridge_wf_min:.4f} → {'PASS' if ac3 else 'FAIL'}")
    print(f"  AC4: DD features non-zero? {has_nonzero_dd} → {'PASS' if ac4 else 'FAIL'}")
    print()

    n_pass = sum([ac1, ac2, ac3, ac4])
    sh_lift = ridge_oos_sh - K198_OOS_SH
    dd_improvement = ridge_oos_dd - K198_OOS_DD  # positive = improved (less negative)

    if all([ac1, ac2, ac3, ac4]):
        verdict = (
            f"ACCEPT: K204 clears all 4 criteria. "
            f"OOS Sh={ridge_oos_sh:.2f} (+{sh_lift:.2f} vs K198), "
            f"MaxDD={ridge_oos_dd:.4f} (improved {dd_improvement:+.4f}), "
            f"WF min={ridge_wf_min:.2f}. "
            "Promote to v6.6 production. DD embedding works as intended."
        )
    elif all([ac1, ac3, ac4]) and not ac2:
        verdict = (
            f"CONDITIONAL ACCEPT: K204 OOS Sh={ridge_oos_sh:.2f} ({sh_lift:+.2f} vs K198) "
            f"and WF min={ridge_wf_min:.2f} exceed K198. "
            f"MaxDD={ridge_oos_dd:.4f} did not improve (K198={K198_OOS_DD:.4f}). "
            "DD features are active in model. Monitor MaxDD live; consider v6.6 with DD alert."
        )
    elif all([ac2, ac3, ac4]) and not ac1:
        verdict = (
            f"PARTIAL: K204 improves DD ({ridge_oos_dd:.4f} vs K198 {K198_OOS_DD:.4f}) "
            f"and WF min={ridge_wf_min:.2f}, but OOS Sh={ridge_oos_sh:.2f} "
            f"does not meet K198 hurdle ({K198_OOS_SH:.2f}). "
            "Consider K205 with stronger DD regularization or different feature engineering."
        )
    elif all([ac1, ac2]) and not ac3:
        verdict = (
            f"PARTIAL: K204 OOS Sh={ridge_oos_sh:.2f} and MaxDD improved, "
            f"but WF min={ridge_wf_min:.2f} < K198 threshold {K198_WF_MIN:.2f}. "
            "Tail-fold instability. Consider K205 with longer training window."
        )
    else:
        verdict = (
            f"REJECT: K204 passes only {n_pass}/4 criteria. "
            f"OOS Sh={ridge_oos_sh:.2f} (target≥{K198_OOS_SH:.2f}), "
            f"MaxDD={ridge_oos_dd:.4f} (target<{K198_OOS_DD:.4f}), "
            f"WF min={ridge_wf_min:.2f} (target≥{K198_WF_MIN:.2f}). "
            "K198 v6.5 remains production. Investigate K205."
        )

    print(f"  Verdict: {verdict}")
    print()

    # Step 15: Equity curves
    print("Step 15: Computing equity curves...", flush=True)
    ridge_equity  = np.cumprod(1.0 + pnl_ridge.values).tolist()
    static_equity = np.cumprod(1.0 + static_wf_aligned.values).tolist() if len(static_wf_aligned) > 0 else []

    # Load K198 production equity for comparison
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

    print(f"  K204 Ridge equity: {len(ridge_equity)} points")
    print(f"  Static P3 equity: {len(static_equity)} points")
    print()

    # Step 16: Weight trajectory
    print("Step 16: Weight trajectory...", flush=True)
    if len(weights_ridge) > 0:
        weight_traj_dates = [str(d.date()) for d in weights_ridge.index]
        weight_traj = {c: [round(float(x), 4) for x in weights_ridge[c].values] for c in cols}
        print(f"  Weight trajectory: {len(weight_traj_dates)} data points")
    else:
        weight_traj_dates = []
        weight_traj = {}
    print()

    elapsed = time.time() - START_TIME
    print(f"Total runtime: {elapsed:.1f}s")
    print()

    # ─────────────────────────────────────────────────────────────────────────
    # Assemble outputs
    # ─────────────────────────────────────────────────────────────────────────

    # Per-fold breakdown
    fold_breakdown = []
    for i, sh in enumerate(wf_ridge["fold_sharpes"]):
        fold_breakdown.append({
            "fold": i + 1,
            "sharpe": sh,
            "vs_k198_wf_fold": round(sh - (K198_WF_MIN if i == 0 else K198_WF_MEAN), 4),
        })

    output = {
        "wave": "K204",
        "task": "ML allocator with embedded DD/recovery features (v6.6 candidate)",
        "as_of": pd.Timestamp.now(tz="UTC").isoformat(),
        "runtime_s": round(elapsed, 1),
        "config": {
            "strategies": cols,
            "n_strategies": n_strats,
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
            "n_baseline_features": n_baseline,
            "n_new_dd_features": n_new_dd,
            "n_total_features": feat_df.shape[1],
            "date_range": [str(df_all.index[0].date()), str(df_all.index[-1].date())],
            "n_days_total": len(df_all),
            "n_days_ml_window": len(pnl_ridge),
        },
        "version_comparison": {
            "K198_v6.5_baseline": {
                "oos_sharpe": K198_OOS_SH,
                "oos_maxdd":  K198_OOS_DD,
                "wf_mean":    K198_WF_MEAN,
                "wf_min":     K198_WF_MIN,
                "n_features": 51,
            },
            "K201_rejected": {
                "oos_sharpe": 8.59,
                "oos_maxdd":  -0.0057,
                "wf_mean":    7.38,
                "wf_min":     6.39,
                "reject_reason": "ML→trigger override granularity mismatch",
            },
            "K202_rejected": {
                "oos_sharpe": 7.84,
                "oos_maxdd":  -0.0071,
                "wf_mean":    7.16,
                "wf_min":     6.29,
                "reject_reason": "Trigger→ML filter granularity mismatch",
            },
            "K204_dd_embedded": {
                "oos_sharpe": round(ridge_oos_sh, 4),
                "oos_maxdd":  round(ridge_oos_dd, 4),
                "oos_sortino": m_ridge["sortino"],
                "oos_calmar":  m_ridge["calmar"],
                "oos_ann_ret": m_ridge["ann_ret"],
                "oos_ann_vol": m_ridge["ann_vol"],
                "wf_mean":    wf_ridge["mean"],
                "wf_min":     wf_ridge["min"],
                "wf_max":     wf_ridge["max"],
                "wf_std":     wf_ridge["std"],
                "wf_fold_sharpes": wf_ridge["fold_sharpes"],
                "n_features": feat_df.shape[1],
                "sh_lift_vs_k198":  round(sh_lift, 4),
                "dd_improvement_vs_k198": round(dd_improvement, 4),
                "wf_min_lift_vs_k198": round(ridge_wf_min - K198_WF_MIN, 4),
            },
        },
        "feature_importance": {
            "top_30_all_features": dict(list(feat_imp.items())[:30]),
            "new_dd_features_only": dd_feat_imp,
            "dd_features_nonzero_count": sum(1 for v in dd_feat_imp.values() if v > 1e-8),
            "dd_features_total_count": len(dd_feat_imp),
            "dd_features_all_nonzero": has_nonzero_dd,
            "k198_vs_k204_comparison": {
                "k198_top_features": [
                    "K116__sh90", "V_rev_carry__sh90", "V_rev_carry__mdd30",
                    "V_rev_carry__sh30", "K114__vol30", "K116__vol30",
                ],
                "k204_new_entrants": [
                    k for k in list(feat_imp.keys())[:15]
                    if k.split("__")[-1] in new_dd_suffixes or k in {"panel_dd30", "panel_recovery"}
                ],
            },
        },
        "per_fold_breakdown": fold_breakdown,
        "ml_predictor_diagnostics": {
            **diag_agg,
            "n_wf_steps": len(diagnostics_ridge),
            "per_step_summary": [
                {k: v for k, v in d.items() if k not in ("mean_abs_coef", "feature_names")}
                for d in diagnostics_ridge
            ],
        },
        "dd_aware_weight_analysis": dd_weight_analysis,
        "multicollinearity_check": vif_result,
        "acceptance_criteria": {
            "AC1_oos_sh_ge_k198": {
                "pass": ac1,
                "required": K198_OOS_SH,
                "actual":   round(ridge_oos_sh, 4),
                "lift":     round(sh_lift, 4),
            },
            "AC2_maxdd_improved_vs_k198": {
                "pass": ac2,
                "k198":   K198_OOS_DD,
                "k204":   round(ridge_oos_dd, 4),
                "delta":  round(dd_improvement, 4),
            },
            "AC3_wf_min_ge_k198": {
                "pass": ac3,
                "required": K198_WF_MIN,
                "actual":   round(ridge_wf_min, 4),
                "lift":     round(ridge_wf_min - K198_WF_MIN, 4),
            },
            "AC4_dd_features_nonzero": {
                "pass": ac4,
                "nonzero_count": sum(1 for v in dd_feat_imp.values() if v > 1e-8),
                "total_dd_features": len(dd_feat_imp),
            },
            "n_criteria_passed": n_pass,
            "all_pass": all([ac1, ac2, ac3, ac4]),
        },
        "verdict": verdict,
        "k205_next_steps": (
            "If K204 passes: K205 should explore (a) longer training window (180d) "
            "to reduce fold variance, (b) adaptive alpha tuning per-fold, "
            "(c) non-linear interaction between DD features and Sharpe signals. "
            "If K204 fails AC2 (DD): K205 should add stronger DD penalty directly "
            "in weight formula: w_i *= (1 + dd30_i) to further reduce exposure. "
            "If K204 fails AC1 (Sh): K205 should investigate LightGBM with DD features "
            "as the non-linearity may matter for DD-regime interaction."
        ),
    }

    # Save metrics JSON
    out_json = BASE / "wave_k204_ml_dd_embed.json"
    with open(out_json, "w") as f:
        json.dump(output, f, indent=2)
    print(f"Saved: {out_json}")

    # Save curves JSON
    curves_out = {
        "wave": "K204",
        "dates_ml":         [str(d.date()) for d in pnl_ridge.index],
        "dates_static_wf":  [str(d.date()) for d in static_wf_aligned.index] if len(static_wf_aligned) > 0 else [],
        "dates_k198_ref":   k198_equity_dates,
        "equity_k204":      [round(float(v), 6) for v in ridge_equity],
        "equity_static_wf": [round(float(v), 6) for v in static_equity],
        "equity_k198_ref":  [round(float(v), 6) for v in k198_equity],
        "pnl_k204":         [round(float(v), 8) for v in pnl_ridge.values],
        "pnl_static_wf":    [round(float(v), 8) for v in static_wf_aligned.values] if len(static_wf_aligned) > 0 else [],
        "weight_trajectory_dates": weight_traj_dates,
        "weight_trajectory": weight_traj,
        "dd_weight_analysis": dd_weight_analysis,
    }

    out_curves = BASE / "wave_k204_curves.json"
    with open(out_curves, "w") as f:
        json.dump(curves_out, f, indent=2)
    print(f"Saved: {out_curves}")

    # ─────────────────────────────────────────────────────────────────────────
    # Final summary table
    # ─────────────────────────────────────────────────────────────────────────
    print()
    print("=" * 80)
    print("FINAL COMPARISON: K198 v6.5 vs K204 DD-Embedded vs Rejected K201/K202")
    print("=" * 80)
    print(f"{'Version':<30} {'OOS Sh':>8} {'OOS MaxDD':>10} {'WF mean':>8} {'WF min':>8} {'Features':>9}")
    print("-" * 80)
    print(f"{'K198 v6.5 (prod baseline)':30s} {K198_OOS_SH:>8.2f} {K198_OOS_DD:>10.4f} "
          f"{K198_WF_MEAN:>8.2f} {K198_WF_MIN:>8.2f} {'51':>9s}")
    print(f"{'K201 (REJECTED)':30s} {'8.59':>8s} {'-0.0057':>10s} {'7.38':>8s} {'6.39':>8s} {'51':>9s}")
    print(f"{'K202 (REJECTED)':30s} {'7.84':>8s} {'-0.0071':>10s} {'7.16':>8s} {'6.29':>8s} {'51':>9s}")
    print(f"{'K204 DD-embed':30s} {ridge_oos_sh:>8.2f} {ridge_oos_dd:>10.4f} "
          f"{ridge_wf_mean:>8.2f} {ridge_wf_min:>8.2f} {feat_df.shape[1]:>9d}")
    print("-" * 80)
    lift_dd = ridge_oos_dd - K198_OOS_DD
    print(f"  K204 lift vs K198:  OOS Sh {sh_lift:+.4f} | MaxDD {lift_dd:+.4f} "
          f"({'improved' if lift_dd > 0 else 'worsened'}) | WF min {ridge_wf_min - K198_WF_MIN:+.4f}")
    print()
    print(f"VERDICT: {verdict}")
    print()
    print(f"Runtime: {elapsed:.1f}s")

    return output


if __name__ == "__main__":
    main()

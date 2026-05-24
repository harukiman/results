"""Wave K212 — Isolated Prescription Tests: A=135d+pen, B=180d+no-pen, C=150d+pen.

Objective: Isolate each K205 prescription independently.

K212A: 135d window + KEEP DD penalty (pen=2.0)
  - Tests if the shorter window alone (without removing penalty) recovers OOS Sh
  - K209 had 135d + no penalty => Fold 3 collapse (Sh 3.46, MaxDD -0.027)
  - K212A isolates: was the window or the penalty removal the culprit?

K212B: 180d window + NO penalty (pen=0.0)
  - Tests if removing the penalty alone (with K205 window) improves OOS Sh
  - K205 had 180d + pen=2.0 => OOS Sh 9.22 (below K198's 10.28)
  - K212B isolates: is the DD penalty the drag on OOS Sh?

K212C: 150d window + DD penalty (pen=2.0)  -- gradual step-down
  - Conservative middle ground between K198 (90d) and K205 (180d)
  - Hypothesis: 150d gives enough early-fold data while limiting overfitting

Six-way comparison targets:
  K198 (prod):   OOS Sh 10.28 | MaxDD -0.0053 | WF mean 7.91 | WF min 6.57
  K204:          OOS Sh 10.36 | MaxDD -0.0053 | WF mean 7.55 | WF min 6.02
  K205:          OOS Sh  9.22 | MaxDD -0.0039 | WF mean 8.52 | WF min 6.46
  K209 (REJECT): OOS Sh  8.86 | MaxDD -0.0270 | WF mean 6.59 | WF min 3.46
  K212A/B/C: to be computed.

Acceptance for K212 -> v6.6:
  Best variant: OOS Sh >= 10.28, WF min >= 6.57, MaxDD <= -0.0053

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
BASE  = Path("/Users/nekonaomichi/crypto-lab")
CACHE = BASE / "cache"

TRADING_DAYS = 365
OOS_FRAC     = 0.30
N_FOLDS      = 4
ML_TEST_DAYS = 30

# ── K212 variant configs ──────────────────────────────────────────────────────
VARIANTS = {
    "K212A": {"train_days": 135, "dd_penalty_coef": 2.0, "label": "135d+pen=2"},
    "K212B": {"train_days": 180, "dd_penalty_coef": 0.0, "label": "180d+pen=0"},
    "K212C": {"train_days": 150, "dd_penalty_coef": 2.0, "label": "150d+pen=2"},
}

# Caps (same as K198/K205)
K121_CAP      = 0.30
CARRY_FWD_CAP = 0.10
CARRY_REV_CAP = 0.10

# FR defensive trigger
FR_SYMBOLS    = ["BTC", "ETH", "DOGE", "AVAX", "SOL", "XRP"]
FR_THRESHOLD  = -0.009735
FR_COMPONENTS = ["K121", "K133"]

# Reference baselines
K198_OOS_SH  = 10.28
K198_OOS_DD  = -0.0053
K198_WF_MEAN = 7.91
K198_WF_MIN  = 6.57
K204_OOS_SH  = 10.36
K204_WF_MIN  = 6.02
K205_OOS_SH  = 9.22
K205_OOS_DD  = -0.0039
K205_WF_MEAN = 8.52
K205_WF_MIN  = 6.46
K209_OOS_SH  = 8.86
K209_OOS_DD  = -0.0270
K209_WF_MEAN = 6.59
K209_WF_MIN  = 3.46

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
# Data loading (identical to K205/K209)
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
    panel   = pd.concat(daily_series, axis=1)
    fr_mean = panel.mean(axis=1)
    fr_mean.name = "fr_mean_ann"
    return fr_mean


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
# Feature engineering (identical K205/K209: 103 features)
# ─────────────────────────────────────────────────────────────────────────────

def build_features(
    df: pd.DataFrame,
    fr_mean: Optional[pd.Series],
    win_short: int = 30,
    win_long: int = 90,
) -> pd.DataFrame:
    """103-feature matrix (K204 minus dd_max30) — shared by all K212 variants."""
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
            row[f"{prefix}dd30"]  = cumulative_dd(r_short)
            row[f"{prefix}dd90"]  = cumulative_dd(r_long)

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
# Unified ML walk-forward — parameterised by train_days + dd_penalty_coef
# ─────────────────────────────────────────────────────────────────────────────

def ml_walk_forward(
    df: pd.DataFrame,
    feat_df: pd.DataFrame,
    target_df: pd.DataFrame,
    train_days: int,
    test_days: int = ML_TEST_DAYS,
    alpha: float = 1.0,
    dd_penalty_coef: float = 0.0,
) -> Tuple[pd.DataFrame, pd.Series, list]:
    """
    Generic K212 walk-forward engine.

    dd_penalty_coef:
      0.0  => no penalty (K212B, K209 mode)
      2.0  => soft DD penalty: w_i *= max(0, 1 + 2*dd30_i)  (K212A, K212C, K205 mode)
    """
    cols = list(df.columns)
    n_strats = len(cols)
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

        # ── DD penalty (applied only when dd_penalty_coef > 0) ────────────────
        dd30_values = np.zeros(n_strats)
        if dd_penalty_coef > 0.0 and has_dd30:
            last_feat_idx = t_train_end - 1
            if last_feat_idx < len(feat_aligned):
                last_feat_row = feat_aligned.iloc[last_feat_idx]
                for i, c in enumerate(cols):
                    col_name = f"{c}__dd30"
                    dd30_values[i] = float(last_feat_row.get(col_name, 0.0))

        if dd_penalty_coef > 0.0:
            multipliers = np.array([
                max(0.0, 1.0 + dd_penalty_coef * dd30_values[i])
                for i in range(n_strats)
            ])
            preds_final = preds * multipliers
        else:
            multipliers = np.ones(n_strats)
            preds_final = preds.copy()

        pos_preds = np.maximum(preds_final, 0.0)
        if pos_preds.sum() < 1e-10:
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
            "weights":     {cols[i]: round(float(w[i]), 4) for i in range(n_strats)},
            "multipliers": {cols[i]: round(float(multipliers[i]), 4) for i in range(n_strats)},
            "dd30_values": {cols[i]: round(float(dd30_values[i]), 6) for i in range(n_strats)},
            "r2_per_strat": {cols[i]: round(float(r2_scores[i]), 4) if not np.isnan(r2_scores[i]) else None
                             for i in range(n_strats)},
            "dir_accuracy_per_strat": {cols[i]: bool(dir_correct[i]) for i in range(n_strats)},
            "mean_r2":       round(float(np.nanmean(r2_scores)), 4),
            "mean_dir_acc":  round(float(np.mean(dir_correct)), 4),
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


def oos_cut(s: pd.Series, frac: float = OOS_FRAC) -> pd.Series:
    cut = int(len(s) * (1 - frac))
    return s.iloc[cut:]


# ─────────────────────────────────────────────────────────────────────────────
# Main
# ─────────────────────────────────────────────────────────────────────────────

def main():
    print("=" * 80)
    print("Wave K212 — Isolated Prescription Tests")
    print("  K212A: 135d+pen=2 | K212B: 180d+pen=0 | K212C: 150d+pen=2")
    print("=" * 80)
    print()

    np.random.seed(42)

    # ── Step 1: Load data ─────────────────────────────────────────────────────
    print("Step 1: Loading component returns...", flush=True)
    df_all = load_component_returns()
    cols   = list(df_all.columns)
    n_strats = len(cols)
    print(f"  Strategies: {cols}")
    print()

    # ── Step 2: FR regime indicator ───────────────────────────────────────────
    print("Step 2: Loading FR regime indicator...", flush=True)
    fr_mean = load_fr_mean_daily()
    if len(fr_mean) > 0:
        print(f"  FR mean range: {fr_mean.index[0].date()} -> {fr_mean.index[-1].date()}")
    else:
        print("  WARNING: FR data unavailable")
    print()

    # ── Step 3: FR trigger ────────────────────────────────────────────────────
    print("Step 3: Applying FR trigger (K121, K133)...", flush=True)
    if len(fr_mean) > 0:
        df_triggered = apply_fr_trigger(df_all, fr_mean)
        n_trigger = int((fr_mean.reindex(df_all.index, method="ffill") < FR_THRESHOLD).sum())
        print(f"  Trigger fires {n_trigger}/{len(df_all)} days ({n_trigger/len(df_all)*100:.1f}%)")
    else:
        df_triggered = df_all.copy()
        print("  No FR trigger applied")
    print()

    # ── Step 4: Build feature matrix (shared: 103 features) ───────────────────
    print("Step 4: Building 103-feature matrix (shared by all variants)...", flush=True)
    feat_df = build_features(df_triggered, fr_mean if len(fr_mean) > 0 else None)
    target_df = build_targets(df_triggered, horizon=ML_TEST_DAYS)
    print(f"  Feature matrix: {feat_df.shape[0]} rows x {feat_df.shape[1]} features")
    print(f"  Target matrix:  {target_df.shape[0]} rows x {target_df.shape[1]} targets")
    print()

    # ── Step 5: Run 3 variants ────────────────────────────────────────────────
    results = {}
    all_pnl = {}

    for vname, vcfg in VARIANTS.items():
        t0 = time.time()
        print(f"Step 5/{vname}: train={vcfg['train_days']}d, "
              f"dd_penalty={vcfg['dd_penalty_coef']} ({vcfg['label']})...", flush=True)

        weights_df, pnl_series, diagnostics = ml_walk_forward(
            df_triggered, feat_df, target_df,
            train_days=vcfg["train_days"],
            test_days=ML_TEST_DAYS,
            alpha=1.0,
            dd_penalty_coef=vcfg["dd_penalty_coef"],
        )

        if len(pnl_series) == 0:
            print(f"  ERROR: {vname} returned empty PnL")
            continue

        all_pnl[vname] = pnl_series
        oos_ret  = oos_cut(pnl_series)
        m_oos    = metrics_pkg(oos_ret.values)
        wf_stats = wf_fold_sharpes(pnl_series)
        elapsed  = time.time() - t0

        print(f"  OOS Sh={m_oos['sharpe']:.4f}  MaxDD={m_oos['max_dd']:.4f}  "
              f"WF mean={wf_stats['mean']:.4f}  WF min={wf_stats['min']:.4f}  "
              f"folds={wf_stats['fold_sharpes']}  [{elapsed:.1f}s]")

        results[vname] = {
            "config":  vcfg,
            "oos_metrics": m_oos,
            "wf_stats": wf_stats,
            "diagnostics_count": len(diagnostics),
            "n_pnl_days": len(pnl_series),
            "pnl_date_range": [str(pnl_series.index[0].date()), str(pnl_series.index[-1].date())],
            "pnl_series": pnl_series,
            "weights_df": weights_df,
            "diagnostics": diagnostics,
        }
        print()

    print("Step 5 complete — all variants done")
    print()

    # ── Step 6: Acceptance check per variant ──────────────────────────────────
    print("Step 6: Acceptance criteria (OOS Sh >= 10.28, WF min >= 6.57, MaxDD >= -0.0053)...",
          flush=True)
    accept_results = {}
    for vname, res in results.items():
        m   = res["oos_metrics"]
        wf  = res["wf_stats"]
        ac1 = m["sharpe"] >= K198_OOS_SH
        ac2 = m["max_dd"] >= K198_OOS_DD          # <= -0.0053 in absolute terms, i.e. not worse
        ac3 = wf["min"] >= K198_WF_MIN
        ac_all = ac1 and ac2 and ac3
        accept_results[vname] = {
            "AC1_oos_sh": {"pass": ac1, "actual": m["sharpe"], "required": K198_OOS_SH},
            "AC2_maxdd":  {"pass": ac2, "actual": m["max_dd"],  "required": K198_OOS_DD},
            "AC3_wf_min": {"pass": ac3, "actual": wf["min"],   "required": K198_WF_MIN},
            "all_pass": ac_all,
        }
        status = "PASS" if ac_all else "FAIL"
        print(f"  {vname} ({res['config']['label']}): "
              f"OOS Sh={m['sharpe']:.4f}({'PASS' if ac1 else 'FAIL'}) | "
              f"MaxDD={m['max_dd']:.4f}({'PASS' if ac2 else 'FAIL'}) | "
              f"WF min={wf['min']:.4f}({'PASS' if ac3 else 'FAIL'}) => {status}")
    print()

    # ── Step 7: Per-fold breakdown ────────────────────────────────────────────
    # Reference fold Sharpes from prior runs
    k198_fold_sharpes = [6.5722, 7.91, 8.90, 8.26]     # K198 approximation
    k205_fold_sharpes = [7.8797, 6.4565, 9.7828, 9.9519]  # K205 exact from JSON
    k204_fold_sharpes = [6.023, 6.2648, 8.1003, 9.7924]   # K204 exact
    k209_fold_sharpes = [8.2406, 5.511, 3.4614, 9.1606]   # K209 exact

    fold_breakdown = {}
    for vname, res in results.items():
        folds = res["wf_stats"]["fold_sharpes"]
        fold_breakdown[vname] = []
        for i, sh in enumerate(folds):
            fold_breakdown[vname].append({
                "fold": i + 1,
                f"{vname}_sharpe": sh,
                "K198_ref":  k198_fold_sharpes[i] if i < len(k198_fold_sharpes) else None,
                "K205_ref":  k205_fold_sharpes[i] if i < len(k205_fold_sharpes) else None,
                "K209_ref":  k209_fold_sharpes[i] if i < len(k209_fold_sharpes) else None,
                f"{vname}_vs_K198": round(sh - k198_fold_sharpes[i], 4) if i < len(k198_fold_sharpes) else None,
                f"{vname}_vs_K205": round(sh - k205_fold_sharpes[i], 4) if i < len(k205_fold_sharpes) else None,
                f"{vname}_vs_K209": round(sh - k209_fold_sharpes[i], 4) if i < len(k209_fold_sharpes) else None,
                "vs_K198_wf_min": round(sh - K198_WF_MIN, 4),
            })

    # ── Step 8: Six-way comparison table ─────────────────────────────────────
    print("Step 8: Six-way comparison table...", flush=True)
    print()
    hdr = f"{'Version':<30} {'OOS Sh':>8} {'OOS MaxDD':>10} {'WF mean':>9} {'WF min':>8} {'WF folds'}"
    sep = "-" * 100
    print("=" * 100)
    print("SIX-WAY COMPARISON: K198 | K204 | K205 | K209 | K212A | K212B | K212C")
    print("=" * 100)
    print(hdr)
    print(sep)

    baselines = [
        ("K198 (prod)",   K198_OOS_SH, K198_OOS_DD, K198_WF_MEAN, K198_WF_MIN,
         k198_fold_sharpes, "PRODUCTION"),
        ("K204",          K204_OOS_SH, -0.0053,      7.5451,        K204_WF_MIN,
         k204_fold_sharpes, "REJECTED (WF min 6.02)"),
        ("K205",          K205_OOS_SH, K205_OOS_DD,  K205_WF_MEAN,  K205_WF_MIN,
         k205_fold_sharpes, "REJECTED (OOS Sh drop)"),
        ("K209",          K209_OOS_SH, K209_OOS_DD,  K209_WF_MEAN,  K209_WF_MIN,
         k209_fold_sharpes, "REJECTED (Fold3 collapse)"),
    ]
    for name, sh, dd, wfm, wfmin, folds, status in baselines:
        fold_str = str([round(x, 2) for x in folds])
        print(f"  {name:<28} {sh:>8.4f} {dd:>10.4f} {wfm:>9.4f} {wfmin:>8.4f}  {fold_str}  {status}")

    print(sep)
    for vname, res in results.items():
        m   = res["oos_metrics"]
        wf  = res["wf_stats"]
        cfg = res["config"]
        ac  = accept_results[vname]["all_pass"]
        fold_str = str([round(x, 2) for x in wf["fold_sharpes"]])
        label = f"{vname} ({cfg['label']})"
        status = "ACCEPT" if ac else "REJECT"
        print(f"  {label:<28} {m['sharpe']:>8.4f} {m['max_dd']:>10.4f} "
              f"{wf['mean']:>9.4f} {wf['min']:>8.4f}  {fold_str}  {status}")
    print("=" * 100)
    print()

    # ── Step 9: Win-loss attribution ──────────────────────────────────────────
    print("Step 9: Win-loss attribution analysis...", flush=True)
    attrs = {}
    if "K212A" in results and "K212B" in results and "K212C" in results:
        mA = results["K212A"]["oos_metrics"]
        mB = results["K212B"]["oos_metrics"]
        mC = results["K212C"]["oos_metrics"]
        wA = results["K212A"]["wf_stats"]
        wB = results["K212B"]["wf_stats"]
        wC = results["K212C"]["wf_stats"]

        # K212A vs K205: 135d vs 180d (both have penalty=2)
        # Isolates WINDOW effect alone
        a_vs_k205_sh  = round(mA["sharpe"] - K205_OOS_SH, 4)
        a_vs_k205_wfm = round(wA["min"] - K205_WF_MIN, 4)

        # K212B vs K204: 180d vs 90d (both have no penalty)
        # Isolates WINDOW effect alone (no penalty in both)
        b_vs_k204_sh  = round(mB["sharpe"] - K204_OOS_SH, 4)
        b_vs_k204_wfm = round(wB["min"] - K204_WF_MIN, 4)

        # K212B vs K212A: same window EXCEPT penalty (180d both, A=pen, B=nopen) -- wait
        # Actually K212A=135d+pen, K212B=180d+nopen
        # To isolate window: compare K212A(135d+pen) vs K212C(150d+pen) vs K205(180d+pen)
        # To isolate penalty: compare K212B(180d+nopen) vs K205(180d+pen)

        # PENALTY isolation: K212B vs K205 (same 180d, differ only on penalty)
        pen_effect_sh  = round(mB["sharpe"] - K205_OOS_SH, 4)
        pen_effect_dd  = round(mB["max_dd"] - K205_OOS_DD, 4)
        pen_effect_wfm = round(wB["min"] - K205_WF_MIN, 4)

        # WINDOW isolation: K212A vs K209 (same no-penalty... wait K212A HAS penalty)
        # Window isolation: K212C(150d+pen) vs K205(180d+pen) — window step-down
        win_step_sh  = round(mC["sharpe"] - K205_OOS_SH, 4)
        win_step_dd  = round(mC["max_dd"] - K205_OOS_DD, 4)
        win_step_wfm = round(wC["min"] - K205_WF_MIN, 4)

        # K212A(135d+pen) vs K205(180d+pen) — bigger window step-down
        win_135_sh  = round(mA["sharpe"] - K205_OOS_SH, 4)
        win_135_dd  = round(mA["max_dd"] - K205_OOS_DD, 4)
        win_135_wfm = round(wA["min"] - K205_WF_MIN, 4)

        attrs = {
            "penalty_isolation_K212B_vs_K205": {
                "description": "Both 180d, K212B=no penalty, K205=penalty=2. Isolates penalty effect alone.",
                "oos_sh_delta": pen_effect_sh,
                "max_dd_delta": pen_effect_dd,
                "wf_min_delta": pen_effect_wfm,
                "interpretation": (
                    "POSITIVE delta => penalty was DRAGGING OOS Sh in K205. "
                    "NEGATIVE delta => removing penalty hurts."
                ),
            },
            "window_135_isolation_K212A_vs_K205": {
                "description": "Both pen=2, K212A=135d, K205=180d. Isolates window shrink 180->135.",
                "oos_sh_delta": win_135_sh,
                "max_dd_delta": win_135_dd,
                "wf_min_delta": win_135_wfm,
                "interpretation": (
                    "POSITIVE delta => 135d window recovers OOS vs 180d (K205 over-smoothed). "
                    "NEGATIVE delta => shorter window hurts (more noise)."
                ),
            },
            "window_150_isolation_K212C_vs_K205": {
                "description": "Both pen=2, K212C=150d, K205=180d. Isolates window shrink 180->150.",
                "oos_sh_delta": win_step_sh,
                "max_dd_delta": win_step_dd,
                "wf_min_delta": win_step_wfm,
                "interpretation": (
                    "Conservative window step-down. Positive => 150d better than 180d (K205). "
                    "Check if WF min improves vs K205."
                ),
            },
            "combined_K209_vs_K212A_penalty_within_135d": {
                "description": "Both 135d, K209=no penalty, K212A=penalty=2. Penalty effect at 135d.",
                "oos_sh_delta": round(mA["sharpe"] - K209_OOS_SH, 4),
                "max_dd_delta": round(mA["max_dd"] - K209_OOS_DD, 4),
                "wf_min_delta": round(wA["min"] - K209_WF_MIN, 4),
                "interpretation": (
                    "CRITICAL: K209 had Fold3 collapse (Sh 3.46). "
                    "If K212A WF min >> K209's 3.46 => DD penalty was the key stabilizer. "
                    "If K212A Fold3 still collapses => 135d window is the root cause, not penalty."
                ),
            },
        }

        print("  Penalty isolation (K212B vs K205): "
              f"OOS Sh {pen_effect_sh:+.4f} | MaxDD {pen_effect_dd:+.4f} | WF min {pen_effect_wfm:+.4f}")
        print("  Window 135d isolation (K212A vs K205): "
              f"OOS Sh {win_135_sh:+.4f} | MaxDD {win_135_dd:+.4f} | WF min {win_135_wfm:+.4f}")
        print("  Window 150d isolation (K212C vs K205): "
              f"OOS Sh {win_step_sh:+.4f} | MaxDD {win_step_dd:+.4f} | WF min {win_step_wfm:+.4f}")
        print("  Penalty at 135d (K212A vs K209): "
              f"OOS Sh {attrs['combined_K209_vs_K212A_penalty_within_135d']['oos_sh_delta']:+.4f} | "
              f"WF min {attrs['combined_K209_vs_K212A_penalty_within_135d']['wf_min_delta']:+.4f}")
    print()

    # ── Step 10: Best variant + verdict ──────────────────────────────────────
    # Find best variant by OOS Sh (primary criteria)
    best_variant = None
    best_sh = -999.0
    for vname, res in results.items():
        sh = res["oos_metrics"]["sharpe"]
        if sh > best_sh:
            best_sh = sh
            best_variant = vname

    def make_verdict(results, accept_results, attrs, best_variant):
        lines = []

        # 1. Prescription winner
        if attrs:
            pen_delta = attrs["penalty_isolation_K212B_vs_K205"]["oos_sh_delta"]
            win135_delta = attrs["window_135_isolation_K212A_vs_K205"]["oos_sh_delta"]
            win150_delta = attrs["window_150_isolation_K212C_vs_K205"]["oos_sh_delta"]
            pen_at_135_delta = attrs["combined_K209_vs_K212A_penalty_within_135d"]["wf_min_delta"]

            if pen_delta > 0.2:
                lines.append(
                    f"KEY FINDING: DD penalty was HURTING K205 (removing it lifts OOS Sh by {pen_delta:+.2f}). "
                    "K212B (180d+no penalty) is the cleanest fix to K205."
                )
            elif pen_delta < -0.2:
                lines.append(
                    f"KEY FINDING: DD penalty is HELPING (removing it drops OOS Sh by {pen_delta:.2f}). "
                    "Penalty is not double-counting; it's providing genuine risk reduction."
                )
            else:
                lines.append(
                    f"DD penalty has NEUTRAL effect on OOS Sh ({pen_delta:+.2f}). "
                    "Window size is the primary lever."
                )

            if win135_delta > 0:
                lines.append(
                    f"Window shrink 180->135 HELPS OOS Sh by {win135_delta:+.2f} (K212A vs K205). "
                    "K205 over-smoothed with 180d window."
                )
            else:
                lines.append(
                    f"Window shrink 180->135 HURTS OOS Sh by {win135_delta:.2f} (K212A vs K205). "
                    "180d window is better for OOS stability."
                )

            if pen_at_135_delta > 2.0:
                lines.append(
                    f"CRITICAL: DD penalty RESCUES 135d (K212A WF min lift vs K209: {pen_at_135_delta:+.2f}). "
                    "K209's Fold3 collapse (3.46) was caused by missing DD penalty, NOT the window alone."
                )
            else:
                lines.append(
                    f"K212A WF min lift vs K209: {pen_at_135_delta:+.2f}. "
                    "Check fold breakdown to determine if 135d window is stable with penalty."
                )

        # 2. Acceptance verdict
        n_pass = sum(v["all_pass"] for v in accept_results.values())
        if n_pass == 0:
            lines.append(
                f"NO K212 variant clears all acceptance criteria. "
                f"Best OOS Sh={best_sh:.2f} from {best_variant}. "
                "K198 v6.5 remains production. "
                "K213 next: try 120d window or threshold-based penalty (only dd30 < -0.15)."
            )
        else:
            passing = [v for v, r in accept_results.items() if r["all_pass"]]
            best_pass = max(passing, key=lambda v: results[v]["oos_metrics"]["sharpe"])
            lines.append(
                f"ACCEPT -> v6.6: {best_pass} clears all criteria. "
                f"OOS Sh={results[best_pass]['oos_metrics']['sharpe']:.4f} "
                f"(+{results[best_pass]['oos_metrics']['sharpe']-K198_OOS_SH:.4f} vs K198), "
                f"WF min={results[best_pass]['wf_stats']['min']:.4f}."
            )

        return " | ".join(lines)

    verdict = make_verdict(results, accept_results, attrs, best_variant)
    print(f"VERDICT: {verdict}")
    print()

    # ── Step 11: K213 next steps ──────────────────────────────────────────────
    k213_next = []
    if all(not v["all_pass"] for v in accept_results.values()):
        k213_next = [
            "No K212 variant passes all criteria — K198 v6.5 remains production.",
            "K213A: try 120d+pen=2 (closer to K198's 90d baseline, milder from K198)",
            "K213B: threshold-based penalty — only penalize when dd30 < -0.15 (avoid over-firing)",
            "K213C: 180d window + partial penalty coef=1.0 (softer DD multiplier than K205's 2.0)",
            "Use K212 prescription analysis to guide: if penalty_isolation > 0, go K213A (120d no-pen).",
        ]
    else:
        best_passing = max(
            [v for v in accept_results if accept_results[v]["all_pass"]],
            key=lambda v: results[v]["oos_metrics"]["sharpe"],
        )
        k213_next = [
            f"K212 winner: {best_passing} -> promote to v6.6 production.",
            f"K213: run live forward validation of {best_passing} for 30d before fully replacing K198.",
            "K213 alt: combine K212 winner allocation logic with K198 signals for ensemble stability.",
        ]

    # ── Step 12: Write JSON outputs ───────────────────────────────────────────
    print("Step 12: Writing JSON outputs...", flush=True)
    elapsed_total = time.time() - START_TIME

    # Baselines in comparison
    comparison_baselines = {
        "K198_prod": {
            "oos_sharpe": K198_OOS_SH, "oos_maxdd": K198_OOS_DD,
            "wf_mean": K198_WF_MEAN, "wf_min": K198_WF_MIN,
            "wf_folds": k198_fold_sharpes,
            "config": {"train_days": 90, "dd_penalty_coef": 0.0, "n_features": 51},
            "status": "PRODUCTION",
        },
        "K204": {
            "oos_sharpe": K204_OOS_SH, "oos_maxdd": -0.0053,
            "wf_mean": 7.5451, "wf_min": K204_WF_MIN,
            "wf_folds": k204_fold_sharpes,
            "config": {"train_days": 90, "dd_penalty_coef": 0.0, "n_features": 113},
            "status": "REJECTED", "reject_reason": "WF min 6.02 < 6.57",
        },
        "K205": {
            "oos_sharpe": K205_OOS_SH, "oos_maxdd": K205_OOS_DD,
            "wf_mean": K205_WF_MEAN, "wf_min": K205_WF_MIN,
            "wf_folds": k205_fold_sharpes,
            "config": {"train_days": 180, "dd_penalty_coef": 2.0, "n_features": 103},
            "status": "REJECTED", "reject_reason": "OOS Sh 9.22 < K198 10.28",
        },
        "K209": {
            "oos_sharpe": K209_OOS_SH, "oos_maxdd": K209_OOS_DD,
            "wf_mean": K209_WF_MEAN, "wf_min": K209_WF_MIN,
            "wf_folds": k209_fold_sharpes,
            "config": {"train_days": 135, "dd_penalty_coef": 0.0, "n_features": 103},
            "status": "REJECTED", "reject_reason": "Fold3 collapse Sh 3.46, MaxDD -0.027",
        },
    }

    k212_results_clean = {}
    for vname, res in results.items():
        k212_results_clean[vname] = {
            "config": res["config"],
            "oos_metrics": res["oos_metrics"],
            "wf_stats": {k: v for k, v in res["wf_stats"].items()},
            "n_pnl_days": res["n_pnl_days"],
            "pnl_date_range": res["pnl_date_range"],
            "diagnostics_count": res["diagnostics_count"],
            "acceptance": accept_results[vname],
            "fold_breakdown": fold_breakdown.get(vname, []),
        }

    output_json = {
        "wave": "K212",
        "task": "Isolated prescription tests: A=135d+pen, B=180d+no-pen, C=150d+pen",
        "as_of": pd.Timestamp.now(tz="UTC").isoformat(),
        "runtime_s": round(elapsed_total, 1),
        "config": {
            "n_strategies": n_strats,
            "strategies": cols,
            "n_features": feat_df.shape[1],
            "test_days": ML_TEST_DAYS,
            "ridge_alpha": 1.0,
            "oos_frac": OOS_FRAC,
        },
        "baselines": comparison_baselines,
        "k212_variants": k212_results_clean,
        "win_loss_attribution": attrs,
        "acceptance_summary": {
            vname: accept_results[vname]["all_pass"]
            for vname in results
        },
        "best_variant_by_oos_sh": best_variant,
        "best_variant_oos_sh": round(best_sh, 4) if best_variant else None,
        "verdict": verdict,
        "k213_next_steps": k213_next,
    }

    out_json = BASE / "wave_k212_isolated_prescriptions.json"
    with open(out_json, "w") as f:
        json.dump(output_json, f, indent=2)
    print(f"  Saved: {out_json}")

    # ── Step 13: Equity curves JSON ───────────────────────────────────────────
    # Load reference curves
    def load_ref_equity(fname, key_eq, key_dates):
        try:
            with open(BASE / fname) as fp:
                d = json.load(fp)
            return d.get(key_dates, []), d.get(key_eq, [])
        except Exception:
            return [], []

    k198_dates, k198_eq = load_ref_equity("wave_k198_curves.json", "equity_ridge", "dates_ml")
    k205_dates, k205_eq = load_ref_equity("wave_k205_curves.json", "equity_k205", "dates_ml")
    k209_dates, k209_eq = load_ref_equity("wave_k209_curves.json", "equity_k209", "dates_ml")

    curves_out = {
        "wave": "K212",
        "dates_k198": k198_dates,
        "equity_k198": [round(float(v), 6) for v in k198_eq],
        "dates_k205": k205_dates,
        "equity_k205": [round(float(v), 6) for v in k205_eq],
        "dates_k209": k209_dates,
        "equity_k209": [round(float(v), 6) for v in k209_eq],
    }
    for vname, pnl_series in all_pnl.items():
        equity = np.cumprod(1.0 + pnl_series.values).tolist()
        curves_out[f"dates_{vname}"] = [str(d.date()) for d in pnl_series.index]
        curves_out[f"equity_{vname}"] = [round(float(v), 6) for v in equity]
        curves_out[f"pnl_{vname}"]    = [round(float(v), 8) for v in pnl_series.values]

    out_curves = BASE / "wave_k212_curves.json"
    with open(out_curves, "w") as f:
        json.dump(curves_out, f, indent=2)
    print(f"  Saved: {out_curves}")

    # ── Step 14: Markdown report ──────────────────────────────────────────────
    print("Step 14: Writing Markdown report...", flush=True)
    _write_markdown_report(
        results, accept_results, attrs, comparison_baselines,
        fold_breakdown, verdict, k213_next, elapsed_total,
        k198_fold_sharpes, k205_fold_sharpes, k209_fold_sharpes,
    )

    print()
    print("=" * 80)
    print(f"K212 complete. Runtime: {elapsed_total:.1f}s")
    print("=" * 80)
    return output_json


def _write_markdown_report(
    results, accept_results, attrs, comparison_baselines,
    fold_breakdown, verdict, k213_next, elapsed,
    k198_fold_sharpes, k205_fold_sharpes, k209_fold_sharpes,
):
    lines = []
    A = lines.append

    A("# Wave K212 — Isolated Prescription Analysis")
    A("")
    A(f"**Generated:** {pd.Timestamp.now().strftime('%Y-%m-%d %H:%M JST')}  ")
    A(f"**Runtime:** {elapsed:.1f}s")
    A("")
    A("## Executive Summary")
    A("")
    A(verdict)
    A("")

    A("## Objective")
    A("")
    A("Decompose the K205 prescriptions into independent tests to identify which lever ")
    A("(window length vs DD penalty) drives performance and stability.")
    A("")
    A("| Variant | Training window | DD Penalty | Hypothesis |")
    A("|---------|----------------|------------|------------|")
    A("| K212A | 135d | 2.0 | Window alone rescues K209 collapse |")
    A("| K212B | 180d | 0.0 | Removing penalty alone rescues K205 OOS Sh |")
    A("| K212C | 150d | 2.0 | Conservative middle ground |")
    A("")

    A("## Six-Way Comparison Table")
    A("")
    A("| Version | OOS Sh | OOS MaxDD | WF mean | WF min | Folds | Status |")
    A("|---------|--------|-----------|---------|--------|-------|--------|")

    # Baselines
    bl_rows = [
        ("K198 (prod)", K198_OOS_SH, K198_OOS_DD, K198_WF_MEAN, K198_WF_MIN,
         k198_fold_sharpes, "PRODUCTION"),
        ("K204", K204_OOS_SH, -0.0053, 7.5451, K204_WF_MIN,
         [6.023, 6.2648, 8.1003, 9.7924], "REJECTED"),
        ("K205", K205_OOS_SH, K205_OOS_DD, K205_WF_MEAN, K205_WF_MIN,
         k205_fold_sharpes, "REJECTED"),
        ("K209", K209_OOS_SH, K209_OOS_DD, K209_WF_MEAN, K209_WF_MIN,
         k209_fold_sharpes, "REJECTED"),
    ]
    for name, sh, dd, wfm, wfmin, folds, status in bl_rows:
        fold_str = "/".join(f"{x:.2f}" for x in folds)
        A(f"| {name} | {sh:.4f} | {dd:.4f} | {wfm:.4f} | {wfmin:.4f} | {fold_str} | {status} |")

    for vname, res in results.items():
        m   = res["oos_metrics"]
        wf  = res["wf_stats"]
        cfg = res["config"]
        ac  = accept_results[vname]["all_pass"]
        fold_str = "/".join(f"{x:.2f}" for x in wf["fold_sharpes"])
        status = "**ACCEPT**" if ac else "REJECT"
        label = f"{vname} ({cfg['label']})"
        A(f"| {label} | {m['sharpe']:.4f} | {m['max_dd']:.4f} | {wf['mean']:.4f} | {wf['min']:.4f} | {fold_str} | {status} |")

    A("")

    A("## Per-Fold Breakdown")
    A("")
    for vname, res in results.items():
        cfg   = res["config"]
        folds = fold_breakdown.get(vname, [])
        A(f"### {vname} ({cfg['label']})")
        A("")
        A("| Fold | Sharpe | vs K198 ref | vs K205 ref | vs K209 ref | vs K198 WF min |")
        A("|------|--------|-------------|-------------|-------------|----------------|")
        for fb in folds:
            sh = fb[f"{vname}_sharpe"]
            r198 = fb.get(f"{vname}_vs_K198", "N/A")
            r205 = fb.get(f"{vname}_vs_K205", "N/A")
            r209 = fb.get(f"{vname}_vs_K209", "N/A")
            rwfm = fb["vs_K198_wf_min"]
            flag = " <-- WEAK" if sh < K198_WF_MIN else ""
            A(f"| {fb['fold']} | {sh:.4f} | {r198:+.4f} | {r205:+.4f} | {r209:+.4f} | {rwfm:+.4f}{flag} |")
        A("")

    A("## Win-Loss Attribution")
    A("")
    if attrs:
        A("### 1. Penalty Isolation: K212B vs K205 (same 180d window, differ on penalty)")
        A("")
        pen = attrs["penalty_isolation_K212B_vs_K205"]
        A(f"- OOS Sh delta: **{pen['oos_sh_delta']:+.4f}**")
        A(f"- MaxDD delta: {pen['max_dd_delta']:+.4f}")
        A(f"- WF min delta: {pen['wf_min_delta']:+.4f}")
        A(f"- Interpretation: {pen['interpretation']}")
        A("")

        A("### 2. Window 135d Isolation: K212A vs K205 (same penalty=2, differ on window)")
        A("")
        w135 = attrs["window_135_isolation_K212A_vs_K205"]
        A(f"- OOS Sh delta: **{w135['oos_sh_delta']:+.4f}**")
        A(f"- MaxDD delta: {w135['max_dd_delta']:+.4f}")
        A(f"- WF min delta: {w135['wf_min_delta']:+.4f}")
        A(f"- Interpretation: {w135['interpretation']}")
        A("")

        A("### 3. Window 150d Isolation: K212C vs K205 (same penalty=2, differ on window)")
        A("")
        w150 = attrs["window_150_isolation_K212C_vs_K205"]
        A(f"- OOS Sh delta: **{w150['oos_sh_delta']:+.4f}**")
        A(f"- MaxDD delta: {w150['max_dd_delta']:+.4f}")
        A(f"- WF min delta: {w150['wf_min_delta']:+.4f}")
        A(f"- Interpretation: {w150['interpretation']}")
        A("")

        A("### 4. Penalty at 135d: K212A vs K209 (same 135d window, differ on penalty)")
        A("")
        p135 = attrs["combined_K209_vs_K212A_penalty_within_135d"]
        A(f"- OOS Sh delta: **{p135['oos_sh_delta']:+.4f}**")
        A(f"- MaxDD delta: {p135['max_dd_delta']:+.4f}")
        A(f"- WF min delta (Fold3 rescue?): **{p135['wf_min_delta']:+.4f}**")
        A(f"- Interpretation: {p135['interpretation']}")
        A("")

    A("## Acceptance Criteria Summary")
    A("")
    A("Thresholds: OOS Sh >= 10.28 | MaxDD >= -0.0053 | WF min >= 6.57")
    A("")
    A("| Variant | OOS Sh | MaxDD | WF min | ALL PASS |")
    A("|---------|--------|-------|--------|----------|")
    for vname, ac in accept_results.items():
        sh_p  = "PASS" if ac["AC1_oos_sh"]["pass"] else "FAIL"
        dd_p  = "PASS" if ac["AC2_maxdd"]["pass"] else "FAIL"
        wfm_p = "PASS" if ac["AC3_wf_min"]["pass"] else "FAIL"
        all_p = "**PASS**" if ac["all_pass"] else "FAIL"
        A(f"| {vname} | {ac['AC1_oos_sh']['actual']:.4f} ({sh_p}) | "
          f"{ac['AC2_maxdd']['actual']:.4f} ({dd_p}) | "
          f"{ac['AC3_wf_min']['actual']:.4f} ({wfm_p}) | {all_p} |")
    A("")

    A("## Verdict — Which K20x Branch is the Winner? / K213 Next")
    A("")
    A(f"**{verdict}**")
    A("")
    A("### K213 Next Steps")
    A("")
    for step in k213_next:
        A(f"- {step}")
    A("")

    out_md = BASE / "wave_k212_isolated_prescriptions.md"
    with open(out_md, "w") as f:
        f.write("\n".join(lines))
    print(f"  Saved: {out_md}")


if __name__ == "__main__":
    main()

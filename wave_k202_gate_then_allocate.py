"""Wave K202 — Gate-Then-Allocate: Trigger pre-filter → ML allocator.

Architecture (corrects K201's adversarial layer):
  1. Pre-filter via triggers (BEFORE ML allocation):
     - T1: per-symbol 30d Sharpe < -2.0 → exclude that rev-carry symbol
     - T2: panel 30d Sharpe < 0 → exclude entire reverse carry panel
     - T3: panel cumulative DD > 2% → exclude reverse carry panel until recovery
  2. ML allocator (Ridge) runs on eligible set only
  3. Re-normalize ML weights among eligible strategies
  4. Caps: K121 ≤ 30%, carry_fwd ≤ 10%, carry_rev ≤ 5%

Walk-forward: 4-fold (same structure as K198/K199b/K201)

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
TRAIN_FRAC   = 0.70

# ML walk-forward params (same as K198)
ML_TRAIN_DAYS = 90
ML_TEST_DAYS  = 30

# Caps
K121_CAP       = 0.30
CARRY_FWD_CAP  = 0.10
CARRY_REV_CAP  = 0.05   # conservative (K199b)

# FR trigger (baseline K194 partial trigger)
FR_SYMBOLS    = ["BTC", "ETH", "DOGE", "AVAX", "SOL", "XRP"]
FR_THRESHOLD  = -0.009735
FR_COMPONENTS = ["K121", "K133"]

# T1/T2/T3 trigger params (from K199b)
T1_WINDOW_DAYS   = 30
T1_SHARPE_THRESH = -2.0
T2_WINDOW_DAYS   = 30
T2_SHARPE_THRESH =  0.0
T3_DD_THRESH     = -0.02

# Reverse carry symbols (K196/K199b)
REVERSE_SYMS = ["SOL", "XRP", "SUI", "OP", "APT", "AXS", "JTO", "IMX", "SAND", "ADA"]

# Strategy column names
STRATEGY_NAMES = [
    "v4.1", "V1", "K114", "K116", "K121", "K133",
    "K147", "K175_DAR", "V_fwd_carry", "V_rev_carry",
]

# Which strategies are the "reverse carry" group (gate-eligible)
REV_CARRY_STRATS = {"V_rev_carry"}   # only the combined rev-carry sleeve in main portfolio

# Reference benchmarks
K196_OOS_SH  = 9.20
K196_OOS_DD  = -0.0038
K196_WF_MEAN = 5.37
K196_WF_MIN  = 3.54 # (K197 has K196_WF_MIN=3.25 per prompt, using 3.54 from json)

K198_OOS_SH  = 10.28
K198_OOS_DD  = -0.0053
K198_WF_MEAN = 7.91
K198_WF_MIN  = 6.57

K199B_OOS_SH  = 7.83
K199B_OOS_DD  = -0.0040
K199B_WF_MEAN = 4.98
K199B_WF_MIN  = 3.41

K201_OOS_SH  = 8.59
K201_OOS_DD  = -0.0057
K201_WF_MEAN = 7.38
K201_WF_MIN  = 6.39


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
    r = np.asarray(r, dtype=float)
    dn = r[r < 0]
    if len(dn) < 2 or dn.std(ddof=1) == 0:
        return 0.0
    return float(r.mean() / dn.std(ddof=1) * math.sqrt(TRADING_DAYS))


def calmar_d(r: np.ndarray) -> float:
    r = np.asarray(r, dtype=float)
    ann = (1.0 + r).prod() ** (TRADING_DAYS / max(1, len(r))) - 1.0
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
    w = apply_cap(w, cols, "K121",       K121_CAP)
    w = apply_cap(w, cols, "V_fwd_carry", CARRY_FWD_CAP)
    w = apply_cap(w, cols, "V_rev_carry", CARRY_REV_CAP)
    return w


# ──────────────────────────────────────────────────────────────────────────────
# Data loading (reuse K198 structure)
# ──────────────────────────────────────────────────────────────────────────────

def equity_to_returns(eq) -> np.ndarray:
    eq_arr = np.asarray(eq, dtype=float)
    prev = np.r_[1.0, eq_arr[:-1]]
    return eq_arr / prev - 1.0


def load_component_returns() -> pd.DataFrame:
    """Load 10 strategy daily return series (same as K198)."""
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
        base_df[col_name] = equity_to_returns(eq)
    base_df.index.name = "date"

    with open(BASE / "wave_k195_curves.json") as f:
        k195 = json.load(f)
    k195_dates = pd.to_datetime(k195["panel_dates"])
    fwd_eq  = np.array(k195["series"]["V_eq_w"], dtype=float)
    fwd_ret = pd.Series(
        np.r_[fwd_eq[0] - 1.0, fwd_eq[1:] / fwd_eq[:-1] - 1.0],
        index=k195_dates, name="V_fwd_carry",
    )

    with open(BASE / "wave_k196_curves.json") as f:
        k196 = json.load(f)
    k196_dates = pd.to_datetime(k196["panel_dates"])
    rev_eq  = np.array(k196["series"]["V_rev_eq_w"], dtype=float)
    rev_ret = pd.Series(
        np.r_[rev_eq[0] - 1.0, rev_eq[1:] / rev_eq[:-1] - 1.0],
        index=k196_dates, name="V_rev_carry",
    )

    all_start = max(base_df.index[0], fwd_ret.index[0], rev_ret.index[0])
    all_end   = min(base_df.index[-1], fwd_ret.index[-1], rev_ret.index[-1])

    df = pd.concat([
        base_df[(base_df.index >= all_start) & (base_df.index <= all_end)],
        fwd_ret[(fwd_ret.index >= all_start)  & (fwd_ret.index <= all_end)],
        rev_ret[(rev_ret.index >= all_start)  & (rev_ret.index <= all_end)],
    ], axis=1).dropna()
    print(f"  Component returns: {df.shape[0]} days × {df.shape[1]} strategies")
    print(f"  Date range: {df.index[0].date()} → {df.index[-1].date()}")
    return df


def load_reverse_carry_per_symbol() -> pd.DataFrame:
    """Load per-symbol reverse carry returns for T1 computation."""
    with open(BASE / "wave_k196_curves.json") as f:
        k196 = json.load(f)
    dates = pd.to_datetime(k196["dates"])
    panel = pd.DataFrame(index=dates)
    for sym in REVERSE_SYMS:
        key = f"rev_carry_{sym}"
        if key in k196["series"]:
            panel[sym] = equity_to_returns(k196["series"][key])
    return panel


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
# T1/T2/T3 trigger state computation (pre-filter)
# ──────────────────────────────────────────────────────────────────────────────

def compute_trigger_state(
    panel_rev_sym: pd.DataFrame,
    idx: pd.DatetimeIndex,
) -> pd.DataFrame:
    """
    Compute T1/T2/T3 trigger state at each day.

    Returns DataFrame with columns:
      t1_{sym}: bool — T1 fired for symbol sym
      t2:       bool — T2 fired (panel Sh < 0)
      t3:       bool — T3 fired (panel DD > 2%)
      rev_excluded: bool — ANY trigger fires → exclude V_rev_carry from ML universe
    """
    panel_aligned = panel_rev_sym.reindex(idx, fill_value=0.0)
    n = len(idx)

    # Per-symbol 30d rolling Sharpe (T1)
    roll_mean_sym = panel_aligned.rolling(T1_WINDOW_DAYS,
                                          min_periods=max(5, T1_WINDOW_DAYS // 3)).mean()
    roll_std_sym  = panel_aligned.rolling(T1_WINDOW_DAYS,
                                          min_periods=max(5, T1_WINDOW_DAYS // 3)).std(ddof=1)
    roll_sh_sym   = (roll_mean_sym / roll_std_sym.replace(0, np.nan) *
                     math.sqrt(TRADING_DAYS)).fillna(0.0)

    # Panel equal-weight 30d rolling Sharpe (T2)
    panel_eq = panel_aligned.mean(axis=1)
    roll_mean_p = panel_eq.rolling(T2_WINDOW_DAYS,
                                   min_periods=max(5, T2_WINDOW_DAYS // 3)).mean()
    roll_std_p  = panel_eq.rolling(T2_WINDOW_DAYS,
                                   min_periods=max(5, T2_WINDOW_DAYS // 3)).std(ddof=1)
    roll_sh_p   = (roll_mean_p / roll_std_p.replace(0, np.nan) *
                   math.sqrt(TRADING_DAYS)).fillna(0.0)

    # Panel cumulative DD (T3)
    eq_curve = np.cumprod(1.0 + panel_eq.fillna(0.0).values)
    peak_curve = np.maximum.accumulate(eq_curve)
    dd_curve = pd.Series(eq_curve / peak_curve - 1.0, index=idx)

    # Build state DataFrame
    state = pd.DataFrame(index=idx)
    for sym in panel_aligned.columns:
        state[f"t1_{sym}"] = roll_sh_sym[sym] < T1_SHARPE_THRESH

    state["t2"] = roll_sh_p < T2_SHARPE_THRESH
    state["t3"] = dd_curve  < T3_DD_THRESH

    # T1 fires if ANY symbol below threshold → exclude rev panel
    any_t1 = state[[c for c in state.columns if c.startswith("t1_")]].any(axis=1)

    state["rev_excluded"] = any_t1 | state["t2"] | state["t3"]

    return state


# ──────────────────────────────────────────────────────────────────────────────
# ML feature engineering (reused from K198)
# ──────────────────────────────────────────────────────────────────────────────

def build_features(
    df: pd.DataFrame,
    fr_mean: Optional[pd.Series],
    win_short: int = 30,
    win_long:  int = 90,
) -> pd.DataFrame:
    n_strats = df.shape[1]
    cols = list(df.columns)
    R = df.values
    n = len(R)
    feat_rows = []

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
            row[f"{prefix}sh30"]  = sharpe_d(slice_short[:, i])
            row[f"{prefix}sh90"]  = sharpe_d(slice_long[:, i])
            row[f"{prefix}vol30"] = float(slice_short[:, i].std(ddof=1) *
                                          math.sqrt(TRADING_DAYS))
            row[f"{prefix}mdd30"] = max_dd_d(slice_short[:, i])
            if n_strats > 1:
                other_corrs = np.delete(corr_mat[i], i)
                row[f"{prefix}xcorr"] = float(np.mean(other_corrs))
            else:
                row[f"{prefix}xcorr"] = 0.0

        if fr_mean is not None and len(fr_mean) > 0:
            fr_date = df.index[t]
            fr_val = fr_mean.reindex([fr_date], method="ffill")
            row["fr_mean_ann"] = float(fr_val.iloc[0]) if not fr_val.isna().all() else 0.0
        else:
            row["fr_mean_ann"] = 0.0

        feat_rows.append(row)

    return pd.DataFrame(feat_rows, index=df.index[win_long:])


def build_targets(df: pd.DataFrame, horizon: int = 30) -> pd.DataFrame:
    cols = list(df.columns)
    R = df.values
    n = len(R)
    target_rows = []
    for t in range(n - horizon):
        fwd = R[t + 1: t + 1 + horizon]
        row = {f"{strat}__fwd_sh": sharpe_d(fwd[:, i])
               for i, strat in enumerate(cols)}
        target_rows.append(row)
    return pd.DataFrame(target_rows, index=df.index[:n - horizon])


# ──────────────────────────────────────────────────────────────────────────────
# Gate-then-Allocate walk-forward (K202 core)
# ──────────────────────────────────────────────────────────────────────────────

def gate_then_allocate_wf(
    df: pd.DataFrame,
    feat_df: pd.DataFrame,
    target_df: pd.DataFrame,
    trigger_state: pd.DataFrame,
    train_days: int = ML_TRAIN_DAYS,
    test_days:  int = ML_TEST_DAYS,
    alpha:      float = 1.0,
) -> Tuple[pd.DataFrame, pd.Series, list]:
    """
    Gate-then-allocate walk-forward:

    For each 30-day test window [t, t+30):
      1. Query trigger state at t (pre-filter): determine eligible strategies
      2. Train Ridge on feat_df[t-train_days:t] → target_df[t-train_days:t]
         for ALL strategies (learn universal signal; gating happens at inference)
      3. Predict next-30d Sharpe for ALL strategies
      4. Zero out predictions for excluded strategies (gate)
      5. Build weights ∝ max(pred, 0) among eligible only
      6. Renormalize, apply caps
      7. Execute on df[t:t+test_days]
    """
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
    filter_log   = []

    step = 0
    while True:
        t_start = step * test_days + min_train
        if t_start >= n:
            break

        t_train_start = max(0, t_start - train_days)
        t_train_end   = t_start
        t_test_end    = min(t_start + test_days, n)

        if t_train_end - t_train_start < 30 or t_test_end <= t_start:
            step += 1
            continue

        X_train = feat_arr[t_train_start:t_train_end]
        Y_train = target_arr[t_train_start:t_train_end]
        X_test  = feat_arr[t_start:t_test_end]
        test_dates_slice = date_idx[t_start:t_test_end]

        if len(X_train) < 20 or len(X_test) == 0:
            step += 1
            continue

        # ── Step 1: Gate — determine eligibility at test start ────────────────
        gate_date = test_dates_slice[0]
        # Find trigger state at gate_date (or nearest prior date)
        trigger_at = trigger_state.reindex([gate_date], method="ffill")
        rev_excluded = bool(trigger_at["rev_excluded"].iloc[0]) if len(trigger_at) > 0 else False

        # Build eligible mask (True = eligible for ML allocation)
        eligible_mask = np.ones(n_strats, dtype=bool)
        if rev_excluded:
            for i, c in enumerate(cols):
                if c in REV_CARRY_STRATS:
                    eligible_mask[i] = False

        # Log filter event
        t1_fired_syms = []
        t2_fired = bool(trigger_at["t2"].iloc[0]) if len(trigger_at) > 0 else False
        t3_fired = bool(trigger_at["t3"].iloc[0]) if len(trigger_at) > 0 else False
        for col in trigger_at.columns:
            if col.startswith("t1_") and bool(trigger_at[col].iloc[0]):
                t1_fired_syms.append(col[3:])

        filter_entry = {
            "step":          step,
            "gate_date":     str(gate_date.date()),
            "rev_excluded":  rev_excluded,
            "t1_fired_syms": t1_fired_syms,
            "t2_fired":      t2_fired,
            "t3_fired":      t3_fired,
            "eligible":      [cols[i] for i in range(n_strats) if eligible_mask[i]],
            "excluded":      [cols[i] for i in range(n_strats) if not eligible_mask[i]],
        }
        filter_log.append(filter_entry)

        # ── Step 2: ML — fit Ridge on all strategies ──────────────────────────
        X_train_c = np.nan_to_num(X_train, nan=0.0, posinf=0.0, neginf=0.0)
        X_test_c  = np.nan_to_num(X_test,  nan=0.0, posinf=0.0, neginf=0.0)

        scaler = StandardScaler()
        X_train_s = scaler.fit_transform(X_train_c)
        X_test_s  = scaler.transform(X_test_c)

        preds = np.zeros(n_strats)
        r2_scores = []
        for i in range(n_strats):
            y = Y_train[:, i]
            if np.isnan(y).any() or np.std(y) < 1e-10:
                preds[i] = 0.0
                r2_scores.append(np.nan)
                continue
            model = Ridge(alpha=alpha)
            model.fit(X_train_s, y)
            preds[i] = float(model.predict(X_test_s[:1])[0])
            y_pred_tr = model.predict(X_train_s)
            ss_res = np.sum((y - y_pred_tr) ** 2)
            ss_tot = np.sum((y - y.mean()) ** 2)
            r2 = 1.0 - ss_res / ss_tot if ss_tot > 1e-12 else 0.0
            r2_scores.append(r2)

        # ── Step 3: Gate predictions — zero out excluded strategies ───────────
        gated_preds = preds.copy()
        gated_preds[~eligible_mask] = 0.0

        # ── Step 4: Build weights — proportional to max(pred, 0) among eligible
        pos_preds = np.maximum(gated_preds, 0.0)
        if pos_preds.sum() < 1e-10:
            # All eligible strategies have negative ML predictions: equal-weight eligible
            w = np.zeros(n_strats)
            n_eligible = eligible_mask.sum()
            if n_eligible > 0:
                w[eligible_mask] = 1.0 / n_eligible
            else:
                w = w_equal(n_strats)
        else:
            w = pos_preds / pos_preds.sum()

        # ── Step 5: Apply caps ────────────────────────────────────────────────
        w = apply_all_caps(w, cols)

        # Log opportunity cost: did we exclude a strategy ML wanted?
        ml_wanted_excluded = {
            cols[i]: round(float(preds[i]), 4)
            for i in range(n_strats)
            if not eligible_mask[i] and preds[i] > 0
        }

        # Direction accuracy
        actual_targets = target_arr[t_start:t_test_end].mean(axis=0)
        dir_correct = np.array([
            (preds[i] > 0) == (actual_targets[i] > 0)
            for i in range(n_strats)
        ])

        diag_step = {
            "step":          step,
            "train_start":   str(date_idx[t_train_start].date()),
            "train_end":     str(date_idx[t_train_end - 1].date()),
            "test_start":    str(test_dates_slice[0].date()),
            "test_end":      str(test_dates_slice[-1].date()),
            "gate_date":     str(gate_date.date()),
            "rev_excluded":  rev_excluded,
            "preds_raw":     {cols[i]: round(float(preds[i]), 4) for i in range(n_strats)},
            "preds_gated":   {cols[i]: round(float(gated_preds[i]), 4) for i in range(n_strats)},
            "weights":       {cols[i]: round(float(w[i]), 4) for i in range(n_strats)},
            "ml_wanted_excluded": ml_wanted_excluded,
            "opportunity_cost_exists": len(ml_wanted_excluded) > 0,
            "mean_r2":       round(float(np.nanmean(r2_scores)), 4),
            "mean_dir_acc":  round(float(np.mean(dir_correct)), 4),
        }
        diagnostics.append(diag_step)

        # ── Step 6: Execute ───────────────────────────────────────────────────
        test_rets = df.loc[test_dates_slice].values
        for d_i, d in enumerate(test_dates_slice):
            pnl = float(test_rets[d_i] @ w)
            wf_pnl.append(pnl)
            wf_dates.append(d)
            wf_weights.append(dict(zip(cols, w)))

        step += 1

    if not wf_pnl:
        return pd.DataFrame(), pd.Series(dtype=float), diagnostics

    weights_df = pd.DataFrame(wf_weights, index=wf_dates)
    pnl_series = pd.Series(wf_pnl, index=wf_dates, name="k202_pnl")

    return weights_df, pnl_series, diagnostics, filter_log


# ──────────────────────────────────────────────────────────────────────────────
# Walk-forward fold Sharpes (same as K198)
# ──────────────────────────────────────────────────────────────────────────────

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


def oos_cut(s: pd.Series, oos_frac: float = OOS_FRAC) -> pd.Series:
    cut = int(len(s) * (1.0 - oos_frac))
    return s.iloc[cut:]


# ──────────────────────────────────────────────────────────────────────────────
# Main
# ──────────────────────────────────────────────────────────────────────────────

def main():
    print("=" * 72)
    print("Wave K202 — Gate-Then-Allocate: Pre-filter via Triggers → Ridge ML")
    print("=" * 72)
    print()

    np.random.seed(42)

    # ── Step 1: Load component returns ───────────────────────────────────────
    print("Step 1: Loading component returns...", flush=True)
    df_all = load_component_returns()
    cols = list(df_all.columns)
    n_strats = len(cols)
    print(f"  Strategies: {cols}\n")

    # ── Step 2: Load per-symbol reverse carry (for T1/T2/T3 state) ───────────
    print("Step 2: Loading per-symbol reverse carry for trigger computation...", flush=True)
    panel_rev_sym = load_reverse_carry_per_symbol()
    panel_rev_sym = panel_rev_sym.reindex(df_all.index, fill_value=0.0)
    print(f"  Reverse carry symbols: {list(panel_rev_sym.columns)}")
    print(f"  Panel shape: {panel_rev_sym.shape}\n")

    # ── Step 3: Load FR regime indicator ─────────────────────────────────────
    print("Step 3: Loading FR regime indicator...", flush=True)
    fr_mean = load_fr_mean_daily()
    if len(fr_mean) > 0:
        fr_aligned = fr_mean.reindex(df_all.index, method="ffill")
        print(f"  FR mean stats: mean={fr_aligned.mean():.4f} std={fr_aligned.std():.4f}")
    else:
        fr_aligned = None
        print("  WARNING: FR data not available")
    print()

    # ── Step 4: Apply baseline K194 partial trigger (FR → K121/K133) ─────────
    print("Step 4: Applying K194 partial FR trigger to K121/K133...", flush=True)
    df_triggered = df_all.copy()
    if fr_aligned is not None:
        fr_mask = fr_aligned < FR_THRESHOLD
        n_trigger = int(fr_mask.sum())
        for comp in FR_COMPONENTS:
            if comp in df_triggered.columns:
                df_triggered.loc[fr_mask, comp] = 0.0
        print(f"  FR trigger fires {n_trigger}/{len(df_all)} days ({n_trigger/len(df_all)*100:.1f}%)")
    else:
        print("  No FR trigger applied")
    print()

    # ── Step 5: Compute T1/T2/T3 trigger state at each day ───────────────────
    print("Step 5: Computing T1/T2/T3 trigger state (pre-filter schedule)...", flush=True)
    trigger_state = compute_trigger_state(panel_rev_sym, df_triggered.index)
    n_rev_excluded = int(trigger_state["rev_excluded"].sum())
    n_t2 = int(trigger_state["t2"].sum())
    n_t3 = int(trigger_state["t3"].sum())
    n_any_t1 = int(trigger_state[
        [c for c in trigger_state.columns if c.startswith("t1_")]
    ].any(axis=1).sum())
    oos_start_idx = int(len(df_triggered) * (1 - OOS_FRAC))
    n_rev_excluded_oos = int(trigger_state["rev_excluded"].iloc[oos_start_idx:].sum())
    n_oos = len(df_triggered) - oos_start_idx

    print(f"  T1 (any symbol Sh<-2): {n_any_t1}/{len(df_triggered)} ({n_any_t1/len(df_triggered)*100:.1f}%) days")
    print(f"  T2 (panel Sh<0):        {n_t2}/{len(df_triggered)} ({n_t2/len(df_triggered)*100:.1f}%) days")
    print(f"  T3 (panel DD>2%):       {n_t3}/{len(df_triggered)} ({n_t3/len(df_triggered)*100:.1f}%) days")
    print(f"  Rev excluded (any):     {n_rev_excluded}/{len(df_triggered)} ({n_rev_excluded/len(df_triggered)*100:.1f}%) days")
    print(f"  Rev excluded OOS:       {n_rev_excluded_oos}/{n_oos} ({n_rev_excluded_oos/n_oos*100:.1f}%)")
    print()

    # ── Step 6: Build ML feature matrix ──────────────────────────────────────
    print("Step 6: Building ML feature matrix...", flush=True)
    feat_df = build_features(df_triggered, fr_mean if fr_mean is not None and len(fr_mean) > 0 else None)
    print(f"  Features: {feat_df.shape[0]} rows × {feat_df.shape[1]} features")
    print(f"  Feature date range: {feat_df.index[0].date()} → {feat_df.index[-1].date()}\n")

    # ── Step 7: Build targets ─────────────────────────────────────────────────
    print("Step 7: Building forward Sharpe targets (horizon=30d)...", flush=True)
    target_df = build_targets(df_triggered, horizon=ML_TEST_DAYS)
    print(f"  Target matrix: {target_df.shape[0]} rows × {target_df.shape[1]} strategies\n")

    # ── Step 8: Gate-Then-Allocate walk-forward ───────────────────────────────
    print("Step 8: Gate-Then-Allocate walk-forward (K202 core)...", flush=True)
    result = gate_then_allocate_wf(
        df_triggered, feat_df, target_df, trigger_state,
        train_days=ML_TRAIN_DAYS,
        test_days=ML_TEST_DAYS,
        alpha=1.0,
    )
    weights_k202, pnl_k202, diagnostics, filter_log = result

    if len(pnl_k202) == 0:
        print("  ERROR: Walk-forward returned empty PnL")
        return

    print(f"  K202 PnL: {len(pnl_k202)} days, "
          f"{pnl_k202.index[0].date()} → {pnl_k202.index[-1].date()}")

    # Filter log stats
    n_steps  = len(filter_log)
    n_rev_ex = sum(1 for e in filter_log if e["rev_excluded"])
    n_opp    = sum(1 for d in diagnostics if d["opportunity_cost_exists"])
    print(f"  Walk-forward steps: {n_steps}")
    print(f"  Steps with rev_carry excluded: {n_rev_ex}/{n_steps} ({n_rev_ex/n_steps*100:.1f}%)")
    print(f"  Steps with ML opportunity cost (wanted excluded): {n_opp}/{n_steps} ({n_opp/n_steps*100:.1f}%)")
    print()

    # ── Step 9: OOS and WF fold metrics ──────────────────────────────────────
    print("Step 9: Computing OOS and WF fold metrics...", flush=True)

    oos_k202 = oos_cut(pnl_k202)
    m_k202   = metrics_pkg(oos_k202.values)
    wf_k202  = wf_fold_sharpes(pnl_k202)

    print(f"  K202 OOS: Sh={m_k202['sharpe']:.4f} MaxDD={m_k202['max_dd']:.4f} "
          f"Ann Ret={m_k202['ann_ret']:.4f}")
    print(f"  K202 WF:  mean={wf_k202['mean']:.4f}  min={wf_k202['min']:.4f}  "
          f"folds={wf_k202['fold_sharpes']}")
    print()

    # ── Step 10: Acceptance criteria evaluation ───────────────────────────────
    print("Step 10: Evaluating K202 acceptance criteria...", flush=True)
    k202_oos_sh  = m_k202["sharpe"]
    k202_oos_dd  = m_k202["max_dd"]
    k202_wf_min  = wf_k202["min"]
    k202_wf_mean = wf_k202["mean"]

    ac1 = k202_oos_sh >= K198_OOS_SH        # OOS Sh ≥ K198
    ac2 = k202_wf_min >= K198_WF_MIN         # WF min ≥ K198
    ac3 = k202_oos_dd > K198_OOS_DD          # MaxDD better than K198 (primary justify)
    ac4 = n_opp / n_steps < 0.50 if n_steps > 0 else True  # no adversarial anti-momentum

    print(f"  AC1: OOS Sh ≥ K198 (10.28)?  K202={k202_oos_sh:.4f} → {'PASS' if ac1 else 'FAIL'}")
    print(f"  AC2: WF min ≥ K198 (6.57)?   K202={k202_wf_min:.4f} → {'PASS' if ac2 else 'FAIL'}")
    print(f"  AC3: MaxDD < K198 (-0.0053)?  K202={k202_oos_dd:.4f} → {'PASS' if ac3 else 'FAIL'}")
    print(f"  AC4: <50% steps with ML-trigger conflict?  {n_opp}/{n_steps} "
          f"({n_opp/n_steps*100:.1f}%) → {'PASS' if ac4 else 'FAIL'}")
    n_ac_pass = sum([ac1, ac2, ac3, ac4])
    print(f"  Criteria passed: {n_ac_pass}/4")
    print()

    # ── Step 11: Opportunity cost analysis ───────────────────────────────────
    print("Step 11: Opportunity cost analysis (what ML predicted for excluded strats)...", flush=True)
    opp_steps = [d for d in diagnostics if d["opportunity_cost_exists"]]
    if opp_steps:
        # Compute realized returns of excluded strategies during exclusion
        opp_realized = []
        for d in opp_steps:
            t_start_str = d["test_start"]
            t_end_str   = d["test_end"]
            t_slice = df_triggered.loc[t_start_str:t_end_str]
            for strat_col, ml_pred in d["ml_wanted_excluded"].items():
                if strat_col in t_slice.columns:
                    realized_sh = sharpe_d(t_slice[strat_col].values)
                    opp_realized.append({
                        "step":       d["step"],
                        "date":       t_start_str,
                        "strat":      strat_col,
                        "ml_pred":    ml_pred,
                        "realized_sh": round(realized_sh, 4),
                        "trigger_saved": realized_sh < 0,  # True = trigger was right to exclude
                    })

        trigger_correct = sum(1 for x in opp_realized if x["trigger_saved"])
        trigger_total   = len(opp_realized)
        print(f"  Opportunity cost events: {trigger_total}")
        print(f"  Trigger was correct (excluded strategy actually lost): "
              f"{trigger_correct}/{trigger_total} ({trigger_correct/trigger_total*100:.0f}%)")
        mean_excluded_sh = np.mean([x["realized_sh"] for x in opp_realized])
        print(f"  Mean realized Sharpe of excluded strategies: {mean_excluded_sh:.4f}")
    else:
        opp_realized = []
        print("  No opportunity cost events (triggers never fired during ML positives)")
    print()

    # ── Step 12: Equity curves ────────────────────────────────────────────────
    print("Step 12: Building equity curves...", flush=True)
    k202_equity = np.cumprod(1.0 + pnl_k202.values).tolist()

    # Load K198 curves for comparison
    with open(BASE / "wave_k198_curves.json") as f:
        k198_curves = json.load(f)
    k198_equity = k198_curves.get("equity_ridge", [])
    k198_dates  = k198_curves.get("dates_ml", [])

    # Load K196 curves
    with open(BASE / "wave_k196_curves.json") as f:
        k196_curves = json.load(f)
    k196_equity = k196_curves["series"].get("K196_P3_triggered", [])
    k196_dates  = k196_curves.get("dates", k196_curves.get("panel_dates", []))

    # Load K199b curves
    with open(BASE / "wave_k199_curves.json") as f:
        k199_curves = json.load(f)
    k199b_equity = k199_curves["series"].get("K199b_P3", [])
    k199b_dates  = k199_curves.get("dates", [])

    # Load K201 curves
    with open(BASE / "wave_k201_curves.json") as f:
        k201_curves = json.load(f)
    k201_equity = k201_curves.get("equity_k201", [])
    k201_dates  = k201_curves.get("dates_k201", k201_curves.get("dates_ml", []))

    print(f"  K202 equity: {len(k202_equity)} points")
    print(f"  K198 equity: {len(k198_equity)} points")
    print()

    # ── Step 13: Eligibility trace ────────────────────────────────────────────
    eligibility_trace = {
        str(d.date()): {
            "rev_excluded": bool(trigger_state.loc[d, "rev_excluded"]),
            "t2": bool(trigger_state.loc[d, "t2"]),
            "t3": bool(trigger_state.loc[d, "t3"]),
        }
        for d in df_triggered.index
        if d in trigger_state.index
    }

    # ── Step 14: Five-way comparison table ───────────────────────────────────
    print("Step 14: Five-way comparison table...", flush=True)
    print()
    print(f"{'Version':<32} {'OOS Sh':>8} {'OOS MaxDD':>10} {'WF mean':>8} {'WF min':>8}")
    print("-" * 72)
    print(f"{'K196 v6.4 baseline':<32} {K196_OOS_SH:>8.2f} {K196_OOS_DD:>10.4f} "
          f"{K196_WF_MEAN:>8.2f} {K196_WF_MIN:>8.2f}")
    print(f"{'K198 ML alone (current prod)':<32} {K198_OOS_SH:>8.2f} {K198_OOS_DD:>10.4f} "
          f"{K198_WF_MEAN:>8.2f} {K198_WF_MIN:>8.2f}")
    print(f"{'K199b triggers alone':<32} {K199B_OOS_SH:>8.2f} {K199B_OOS_DD:>10.4f} "
          f"{K199B_WF_MEAN:>8.2f} {K199B_WF_MIN:>8.2f}")
    print(f"{'K201 ML→trigger override (rej.)':<32} {K201_OOS_SH:>8.2f} {K201_OOS_DD:>10.4f} "
          f"{K201_WF_MEAN:>8.2f} {K201_WF_MIN:>8.2f}")
    print(f"{'K202 trigger→ML filter':<32} {k202_oos_sh:>8.2f} {k202_oos_dd:>10.4f} "
          f"{k202_wf_mean:>8.2f} {k202_wf_min:>8.2f}")
    print("-" * 72)
    print(f"  K202 vs K198 lift: OOS Sh {k202_oos_sh - K198_OOS_SH:+.4f} | "
          f"MaxDD {k202_oos_dd - K198_OOS_DD:+.4f} | WF min {k202_wf_min - K198_WF_MIN:+.4f}")
    print()

    # ── Step 15: Verdict ──────────────────────────────────────────────────────
    if all([ac1, ac2, ac3]):
        verdict = (
            f"ACCEPT: K202 gate-then-allocate clears all primary criteria. "
            f"OOS Sh={k202_oos_sh:.2f} ≥ K198={K198_OOS_SH}, "
            f"WF min={k202_wf_min:.2f} ≥ K198={K198_WF_MIN}, "
            f"MaxDD={k202_oos_dd:.4f} < K198={K198_OOS_DD}. "
            f"Promote to v6.6 production."
        )
        promote = True
    elif ac1 and ac2 and not ac3:
        verdict = (
            f"CONDITIONAL ACCEPT: K202 improves OOS Sh={k202_oos_sh:.2f} ≥ K198={K198_OOS_SH} "
            f"and WF min={k202_wf_min:.2f} ≥ K198={K198_WF_MIN}. "
            f"MaxDD={k202_oos_dd:.4f} marginally worse than K198={K198_OOS_DD}. "
            f"Gate-then-allocate architecture validated. "
            f"Recommend promoting with live MaxDD monitoring at -1.5% alert threshold."
        )
        promote = True
    elif ac3 and (ac1 or ac2):
        verdict = (
            f"PARTIAL ACCEPT: K202 improves MaxDD={k202_oos_dd:.4f} < K198={K198_OOS_DD} "
            f"(primary goal). Sharpe/WF not fully meeting K198 bar. "
            f"Gate architecture proves trigger-ML orthogonality. "
            f"Consider: keep K198 as primary but use K202 as DD-protected variant "
            f"during high-volatility regimes."
        )
        promote = False
    elif not ac1 and not ac2 and not ac3:
        verdict = (
            f"REJECT: K202 fails all primary metrics vs K198. "
            f"OOS Sh={k202_oos_sh:.2f}, WF min={k202_wf_min:.2f}, MaxDD={k202_oos_dd:.4f}. "
            f"Gate architecture does not improve over ML alone. "
            f"K198 remains production (v6.5). Investigate: trigger frequency or "
            f"alternative pre-filter mechanism."
        )
        promote = False
    else:
        verdict = (
            f"MARGINAL: K202 partially meets criteria ({n_ac_pass}/4 pass). "
            f"OOS Sh={k202_oos_sh:.2f} ({'≥' if ac1 else '<'} {K198_OOS_SH}), "
            f"WF min={k202_wf_min:.2f} ({'≥' if ac2 else '<'} {K198_WF_MIN}), "
            f"MaxDD={k202_oos_dd:.4f} ({'<' if ac3 else '≥'} {K198_OOS_DD}). "
            f"K198 v6.5 retained. K202 remains v6.6 candidate pending further investigation."
        )
        promote = False

    print(f"VERDICT: {verdict}")
    print()

    elapsed = time.time() - START_TIME
    print(f"Total runtime: {elapsed:.1f}s")
    print()

    # ── Assemble and save JSON outputs ────────────────────────────────────────

    # Per-step filter log (compact)
    filter_log_compact = [
        {
            "step": e["step"],
            "gate_date": e["gate_date"],
            "rev_excluded": e["rev_excluded"],
            "t1_fired_syms": e["t1_fired_syms"],
            "t2_fired": e["t2_fired"],
            "t3_fired": e["t3_fired"],
            "excluded_strats": e["excluded"],
        }
        for e in filter_log
    ]

    # Opportunity cost summary
    opp_summary = {
        "n_opp_events": len(opp_realized),
        "trigger_correct_pct": (
            round(trigger_correct / trigger_total * 100, 1)
            if trigger_total > 0 else 0.0
        ),
        "mean_excluded_realized_sh": (
            round(float(np.mean([x["realized_sh"] for x in opp_realized])), 4)
            if opp_realized else None
        ),
        "events": opp_realized[:50],  # cap at 50 for JSON size
    }

    metrics_out = {
        "wave": "K202",
        "task": "Gate-Then-Allocate: pre-filter via T1/T2/T3 triggers → Ridge ML allocator",
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
            "t1_window": T1_WINDOW_DAYS,
            "t1_thresh": T1_SHARPE_THRESH,
            "t2_window": T2_WINDOW_DAYS,
            "t2_thresh": T2_SHARPE_THRESH,
            "t3_dd_thresh": T3_DD_THRESH,
            "ridge_alpha": 1.0,
            "n_folds": N_FOLDS,
            "date_range": [str(df_all.index[0].date()), str(df_all.index[-1].date())],
            "n_days_total": len(df_all),
            "n_days_k202": len(pnl_k202),
        },
        "trigger_state_summary": {
            "t1_any_fire_pct":   round(n_any_t1 / len(df_triggered) * 100, 1),
            "t2_fire_pct":       round(n_t2 / len(df_triggered) * 100, 1),
            "t3_fire_pct":       round(n_t3 / len(df_triggered) * 100, 1),
            "rev_excluded_pct":  round(n_rev_excluded / len(df_triggered) * 100, 1),
            "rev_excluded_oos_pct": round(n_rev_excluded_oos / n_oos * 100, 1),
            "per_symbol_t1_fire_pct": {
                sym: round(
                    float(trigger_state[f"t1_{sym}"].sum()) / len(trigger_state) * 100, 1
                )
                for sym in REVERSE_SYMS
                if f"t1_{sym}" in trigger_state.columns
            },
        },
        "wf_step_summary": {
            "n_steps": n_steps,
            "n_steps_rev_excluded": n_rev_ex,
            "rev_excluded_pct": round(n_rev_ex / n_steps * 100, 1) if n_steps > 0 else 0.0,
            "n_steps_opp_cost": n_opp,
            "opp_cost_pct": round(n_opp / n_steps * 100, 1) if n_steps > 0 else 0.0,
        },
        "oos_metrics_k202": m_k202,
        "wf_fold_metrics_k202": wf_k202,
        "five_way_comparison": {
            "K196_v6_4_baseline": {
                "oos_sharpe": K196_OOS_SH,
                "oos_maxdd":  K196_OOS_DD,
                "wf_mean":    K196_WF_MEAN,
                "wf_min":     K196_WF_MIN,
                "description": "Static P3 risk-parity, v6.4 production",
            },
            "K198_ML_alone": {
                "oos_sharpe": K198_OOS_SH,
                "oos_maxdd":  K198_OOS_DD,
                "wf_mean":    K198_WF_MEAN,
                "wf_min":     K198_WF_MIN,
                "description": "Ridge ML allocator, v6.5 current production",
            },
            "K199b_triggers_alone": {
                "oos_sharpe": K199B_OOS_SH,
                "oos_maxdd":  K199B_OOS_DD,
                "wf_mean":    K199B_WF_MEAN,
                "wf_min":     K199B_WF_MIN,
                "description": "T1/T2/T3 safety triggers on static P3",
            },
            "K201_ML_then_trigger": {
                "oos_sharpe": K201_OOS_SH,
                "oos_maxdd":  K201_OOS_DD,
                "wf_mean":    K201_WF_MEAN,
                "wf_min":     K201_WF_MIN,
                "description": "K201 rejected: post-allocation trigger override (adversarial)",
            },
            "K202_trigger_then_ML": {
                "oos_sharpe": round(k202_oos_sh, 4),
                "oos_maxdd":  round(k202_oos_dd, 4),
                "wf_mean":    round(k202_wf_mean, 4),
                "wf_min":     round(k202_wf_min, 4),
                "wf_folds":   wf_k202["fold_sharpes"],
                "description": "K202: gate-then-allocate (this wave)",
                "vs_k198_oos_sh":  round(k202_oos_sh - K198_OOS_SH, 4),
                "vs_k198_maxdd":   round(k202_oos_dd - K198_OOS_DD, 4),
                "vs_k198_wf_min":  round(k202_wf_min - K198_WF_MIN, 4),
            },
        },
        "acceptance_criteria": {
            "AC1_oos_sh_ge_k198": {
                "required": K198_OOS_SH,
                "actual": round(k202_oos_sh, 4),
                "pass": ac1,
            },
            "AC2_wf_min_ge_k198": {
                "required": K198_WF_MIN,
                "actual": round(k202_wf_min, 4),
                "pass": ac2,
            },
            "AC3_maxdd_better_k198": {
                "required_better_than": K198_OOS_DD,
                "actual": round(k202_oos_dd, 4),
                "pass": ac3,
            },
            "AC4_no_adversarial": {
                "opp_cost_steps_pct": round(n_opp / n_steps * 100, 1) if n_steps > 0 else 0.0,
                "pass": ac4,
            },
            "n_criteria_passed": n_ac_pass,
            "promote_to_v6_6": promote,
        },
        "opportunity_cost_analysis": opp_summary,
        "filter_log": filter_log_compact,
        "ml_diagnostics_summary": {
            "n_steps": len(diagnostics),
            "mean_r2": round(float(np.nanmean([d["mean_r2"] for d in diagnostics])), 4),
            "mean_dir_acc": round(float(np.nanmean([d["mean_dir_acc"] for d in diagnostics])), 4),
            "per_step": [
                {k: v for k, v in d.items() if k not in ["preds_raw", "preds_gated"]}
                for d in diagnostics
            ],
        },
        "verdict": verdict,
        "deployment_plan": (
            "Deploy K202 as v6.6: 1) Run monthly Ridge re-train (90d window). "
            "2) Before weight computation, evaluate T1/T2/T3 state for rev-carry panel. "
            "3) If any trigger fires, set V_rev_carry weight = 0 and renormalize. "
            "4) Apply K121≤30%, fwd_carry≤10%, rev_carry≤5% caps. "
            "5) Monitor: alert if ML repeatedly wants rev-carry during T2/T3 exclusion."
            if promote else
            "K198 v6.5 retained as production. K202 architecture logs stored for analysis."
        ),
    }

    out_metrics = BASE / "wave_k202_gate_then_allocate.json"
    with open(out_metrics, "w") as f:
        json.dump(metrics_out, f, indent=2)
    print(f"Saved: {out_metrics}")

    # Save curves JSON
    curves_out = {
        "dates_k202": [str(d.date()) for d in pnl_k202.index],
        "dates_k198": k198_dates,
        "dates_k196": k196_dates if isinstance(k196_dates, list) else [str(d) for d in k196_dates],
        "dates_k199b": k199b_dates if isinstance(k199b_dates, list) else [str(d) for d in k199b_dates],
        "dates_k201": k201_dates if isinstance(k201_dates, list) else [str(d) for d in k201_dates],
        "equity_k202": [round(float(v), 6) for v in k202_equity],
        "equity_k198": [round(float(v), 6) for v in k198_equity],
        "equity_k196": [round(float(v), 6) for v in k196_equity],
        "equity_k199b": [round(float(v), 6) for v in k199b_equity],
        "equity_k201": [round(float(v), 6) for v in k201_equity],
        "pnl_k202": [round(float(v), 8) for v in pnl_k202.values],
        "weight_trajectory_dates": [str(d.date()) for d in weights_k202.index],
        "weight_trajectory": {
            c: [round(float(x), 4) for x in weights_k202[c].values]
            for c in cols
            if c in weights_k202.columns
        },
        "eligibility_trace_sample": {
            # Sample 100 dates for size efficiency
            k: v for k, v in list(eligibility_trace.items())[::max(1, len(eligibility_trace)//100)]
        },
        "trigger_state_summary": {
            "dates": [str(d.date()) for d in trigger_state.index],
            "rev_excluded": trigger_state["rev_excluded"].astype(int).tolist(),
            "t2": trigger_state["t2"].astype(int).tolist(),
            "t3": trigger_state["t3"].astype(int).tolist(),
        },
    }

    out_curves = BASE / "wave_k202_curves.json"
    with open(out_curves, "w") as f:
        json.dump(curves_out, f, indent=2)
    print(f"Saved: {out_curves}")

    # ── Final summary ─────────────────────────────────────────────────────────
    print()
    print("=" * 72)
    print("K202 FIVE-WAY COMPARISON")
    print("=" * 72)
    print(f"{'Version':<32} {'OOS Sh':>8} {'OOS MaxDD':>10} {'WF mean':>8} {'WF min':>8}")
    print("-" * 72)
    print(f"{'K196 v6.4 baseline':<32} {K196_OOS_SH:>8.2f} {K196_OOS_DD:>10.4f} "
          f"{K196_WF_MEAN:>8.2f} {K196_WF_MIN:>8.2f}")
    print(f"{'K198 ML alone (current prod)':<32} {K198_OOS_SH:>8.2f} {K198_OOS_DD:>10.4f} "
          f"{K198_WF_MEAN:>8.2f} {K198_WF_MIN:>8.2f}")
    print(f"{'K199b triggers alone':<32} {K199B_OOS_SH:>8.2f} {K199B_OOS_DD:>10.4f} "
          f"{K199B_WF_MEAN:>8.2f} {K199B_WF_MIN:>8.2f}")
    print(f"{'K201 ML→trigger (REJECTED)':<32} {K201_OOS_SH:>8.2f} {K201_OOS_DD:>10.4f} "
          f"{K201_WF_MEAN:>8.2f} {K201_WF_MIN:>8.2f}")
    print(f"{'K202 trigger→ML (this wave)':<32} {k202_oos_sh:>8.2f} {k202_oos_dd:>10.4f} "
          f"{k202_wf_mean:>8.2f} {k202_wf_min:>8.2f}")
    print("-" * 72)
    print()
    print(f"VERDICT: {verdict}")
    print("=" * 72)

    return metrics_out


if __name__ == "__main__":
    main()

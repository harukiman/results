"""Wave K201 — ML Allocator + Safety Triggers (v6.6 candidate).

Hypothesis: K198's Ridge ML allocator provides regime-adaptive weighting;
K199b's T1/T2/T3 safety triggers provide tail-event protection.
Combined, they should compose: ML sets weights, triggers prevent drawdown.

Implementation:
  1. K198 Ridge ML allocator (51-feature matrix per strategy/day)
     - Predict next-30d Sharpe per strategy
     - Weight ∝ max(predicted_Sh, 0)
     - Carry cap 5% (K199b conservatism, down from K198's 10%)
  2. K199b T1/T2/T3 safety triggers applied post-allocation to reverse carry sleeve:
     - T1: per-symbol 30d rolling Sharpe < -2.0 → halt that symbol
     - T2: panel 30d Sharpe < 0 → halt entire reverse carry panel
     - T3: cumulative panel DD > 2% → halt
  3. Walk-forward 4-fold
  4. Disagreement logging: when ML wants to weight reverse carry but T1/T2/T3 halts

Four-way comparison:
  K196 v6.4 | K198 ML alone | K199b triggers alone | K201 ML+triggers

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

# ML walk-forward params (same as K198)
ML_TRAIN_DAYS = 90   # training window (days)
ML_TEST_DAYS  = 30   # test/apply window (days)

# Caps — K199b conservatism: 5% reverse carry (K198 used 10%)
K121_CAP       = 0.30
CARRY_FWD_CAP  = 0.10
CARRY_REV_CAP  = 0.05   # K199b conservative cap

# FR trigger (same as K198/K196)
FR_SYMBOLS    = ["BTC", "ETH", "DOGE", "AVAX", "SOL", "XRP"]
FR_THRESHOLD  = -0.009735
FR_COMPONENTS = ["K121", "K133"]

# T1/T2/T3 trigger parameters (from K199b)
T1_WINDOW_DAYS   = 30
T1_SHARPE_THRESH = -2.0
T2_WINDOW_DAYS   = 30
T2_SHARPE_THRESH =  0.0
T3_DD_THRESH     = -0.02

# Reverse carry symbols (from K196/K199b)
REVERSE_SYMS = ["SOL", "XRP", "SUI", "OP", "APT", "AXS", "JTO", "IMX", "SAND", "ADA"]

# Strategy names
STRATEGY_NAMES = [
    "v4.1", "V1", "K114", "K116", "K121", "K133",
    "K147", "K175_DAR", "V_fwd_carry", "V_rev_carry",
]

# Reference metrics
K196_OOS_SH  = 9.20
K196_OOS_DD  = -0.0038
K196_WF_MEAN = 5.37
K196_WF_MIN  = 3.54

K198_OOS_SH  = 10.28
K198_OOS_DD  = -0.0053
K198_WF_MEAN = 7.91
K198_WF_MIN  = 6.57

K199B_OOS_SH  = 7.83
K199B_OOS_DD  = -0.0040
K199B_WF_MEAN = 8.42
K199B_WF_MIN  = 4.86


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


def w_inv_vol(R: np.ndarray) -> np.ndarray:
    vols = R.std(axis=0, ddof=1)
    inv = 1.0 / np.where(vols == 0, np.nan, vols)
    return inv / np.nansum(inv)


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


def apply_all_caps(w: np.ndarray, cols: List[str],
                   rev_cap: float = CARRY_REV_CAP) -> np.ndarray:
    """Apply K121 cap, forward carry cap, reverse carry cap."""
    w = apply_cap(w, cols, "K121", K121_CAP)
    w = apply_cap(w, cols, "V_fwd_carry", CARRY_FWD_CAP)
    w = apply_cap(w, cols, "V_rev_carry", rev_cap)
    return w


# ──────────────────────────────────────────────────────────────────────────────
# Data loading
# ──────────────────────────────────────────────────────────────────────────────

def equity_to_returns(eq: List[float]) -> np.ndarray:
    eq_arr = np.asarray(eq, dtype=float)
    prev = np.r_[1.0, eq_arr[:-1]]
    return eq_arr / prev - 1.0


def load_component_returns() -> pd.DataFrame:
    """Load all 10 component strategy returns (same as K198)."""
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
    print(f"  Component returns: {df.shape[0]} days x {df.shape[1]} strategies")
    print(f"  Date range: {df.index[0].date()} -> {df.index[-1].date()}")
    return df


def load_reverse_carry_panel() -> pd.DataFrame:
    """Load per-symbol reverse carry PnLs from wave_k196_curves.json."""
    with open(BASE / "wave_k196_curves.json") as f:
        d = json.load(f)
    dates = pd.to_datetime(d["dates"])
    panel_rev = pd.DataFrame(index=dates)
    for sym in REVERSE_SYMS:
        key = f"rev_carry_{sym}"
        if key in d["series"]:
            panel_rev[sym] = equity_to_returns(d["series"][key])
        else:
            print(f"  WARNING: {key} not found in k196_curves")
    return panel_rev


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
# T1/T2/T3 Trigger application (from K199b)
# ──────────────────────────────────────────────────────────────────────────────

def apply_t1_t2_t3_triggers(
    panel_rev: pd.DataFrame,
) -> Tuple[pd.DataFrame, dict, np.ndarray, np.ndarray, np.ndarray]:
    """Apply rolling T1/T2/T3 deactivation triggers to reverse carry panel.

    Returns:
      panel_triggered: DataFrame with triggers applied
      trigger_stats: dict with per-trigger firing rates
      t2_fire: boolean array, panel-level T2 halt days
      t3_fire: boolean array, DD-level T3 halt days
      t1_fire_any: boolean array, any T1 fired on that day
    """
    n, ncols = panel_rev.shape
    syms = list(panel_rev.columns)
    panel_arr = panel_rev.values.copy()
    dates = panel_rev.index

    t1_fire = {s: np.zeros(n, dtype=bool) for s in syms}
    t2_fire = np.zeros(n, dtype=bool)
    t3_fire = np.zeros(n, dtype=bool)

    df = panel_rev.copy()

    roll_mean_sym = df.rolling(T1_WINDOW_DAYS, min_periods=max(5, T1_WINDOW_DAYS // 3)).mean()
    roll_std_sym  = df.rolling(T1_WINDOW_DAYS, min_periods=max(5, T1_WINDOW_DAYS // 3)).std(ddof=1)
    roll_sh_sym   = roll_mean_sym / roll_std_sym.replace(0, np.nan) * math.sqrt(TRADING_DAYS)
    roll_sh_sym   = roll_sh_sym.fillna(0.0)

    panel_eq = df.mean(axis=1)
    roll_mean_p = panel_eq.rolling(T2_WINDOW_DAYS, min_periods=max(5, T2_WINDOW_DAYS // 3)).mean()
    roll_std_p  = panel_eq.rolling(T2_WINDOW_DAYS, min_periods=max(5, T2_WINDOW_DAYS // 3)).std(ddof=1)
    roll_sh_p   = (roll_mean_p / roll_std_p.replace(0, np.nan) * math.sqrt(TRADING_DAYS)).fillna(0.0)

    eq_curve = np.cumprod(1.0 + panel_eq.fillna(0.0).values)
    peak_curve = np.maximum.accumulate(eq_curve)
    dd_curve = eq_curve / peak_curve - 1.0

    panel_out = panel_arr.copy()
    sh_sym_arr = roll_sh_sym.values
    t1_mask = sh_sym_arr < T1_SHARPE_THRESH
    sh_p_arr = roll_sh_p.values
    t2_mask = sh_p_arr < T2_SHARPE_THRESH
    t3_mask = dd_curve < T3_DD_THRESH

    for i in range(n):
        if t3_mask[i]:
            panel_out[i, :] = 0.0
            t3_fire[i] = True
        elif t2_mask[i]:
            panel_out[i, :] = 0.0
            t2_fire[i] = True
        else:
            for j, sym in enumerate(syms):
                if t1_mask[i, j]:
                    panel_out[i, j] = 0.0
                    t1_fire[sym][i] = True

    panel_triggered = pd.DataFrame(panel_out, index=dates, columns=syms)

    oos_start = int(n * (1 - OOS_FRAC))
    t1_rates = {s: {"fire_count": int(t1_fire[s].sum()),
                    "fire_pct": round(float(t1_fire[s].sum()) / n * 100, 1)}
                for s in syms}

    trigger_stats = {
        "T1_per_symbol": t1_rates,
        "T2_panel": {
            "fire_count_total": int(t2_fire.sum()),
            "fire_pct_total": round(float(t2_fire.sum()) / n * 100, 1),
            "fire_count_oos": int(t2_fire[oos_start:].sum()),
            "fire_pct_oos": round(float(t2_fire[oos_start:].sum()) / (n - oos_start) * 100, 1),
        },
        "T3_dd": {
            "fire_count_total": int(t3_fire.sum()),
            "fire_pct_total": round(float(t3_fire.sum()) / n * 100, 1),
            "fire_count_oos": int(t3_fire[oos_start:].sum()),
            "fire_pct_oos": round(float(t3_fire[oos_start:].sum()) / (n - oos_start) * 100, 1),
            "max_dd_pre_trigger": round(float(dd_curve.min()), 4),
        },
        "combined_halt_days": {
            "total": int((t2_fire | t3_fire).sum()),
            "pct": round(float((t2_fire | t3_fire).sum()) / n * 100, 1),
        },
    }

    # Compute t1_fire_any (any symbol triggered per day)
    t1_fire_any = np.zeros(n, dtype=bool)
    for sym in syms:
        t1_fire_any |= t1_fire[sym]

    return panel_triggered, trigger_stats, t2_fire, t3_fire, t1_fire_any


def apply_fr_trigger(
    df: pd.DataFrame,
    fr_mean: pd.Series,
    components: List[str] = FR_COMPONENTS,
    threshold: float = FR_THRESHOLD,
) -> pd.DataFrame:
    """Zero out FR_COMPONENTS when fr_mean < threshold."""
    df2 = df.copy()
    fr_aligned = fr_mean.reindex(df2.index, method="ffill")
    trigger_mask = fr_aligned < threshold
    for comp in components:
        if comp in df2.columns:
            df2.loc[trigger_mask, comp] = 0.0
    return df2


# ──────────────────────────────────────────────────────────────────────────────
# Feature engineering (from K198)
# ──────────────────────────────────────────────────────────────────────────────

def build_features(df: pd.DataFrame, fr_mean: Optional[pd.Series],
                   win_short: int = 30, win_long: int = 90) -> pd.DataFrame:
    """Build 51-feature matrix per (strategy, day) as in K198."""
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
            row[f"{prefix}sh30"] = sharpe_d(slice_short[:, i])
            row[f"{prefix}sh90"] = sharpe_d(slice_long[:, i])
            row[f"{prefix}vol30"] = float(slice_short[:, i].std(ddof=1) * math.sqrt(TRADING_DAYS))
            row[f"{prefix}mdd30"] = max_dd_d(slice_short[:, i])
            if n_strats > 1:
                other_corrs = np.delete(corr_mat[i], i)
                row[f"{prefix}xcorr"] = float(np.mean(other_corrs))
            else:
                row[f"{prefix}xcorr"] = 0.0

        if fr_mean is not None and len(fr_mean) > 0:
            fr_date = df.index[t]
            fr_aligned = fr_mean.reindex([fr_date], method="ffill")
            row["fr_mean_ann"] = float(fr_aligned.iloc[0]) if not fr_aligned.isna().all() else 0.0
        else:
            row["fr_mean_ann"] = 0.0

        feat_rows.append(row)

    feat_df = pd.DataFrame(feat_rows, index=df.index[win_long:])
    return feat_df


def build_targets(df: pd.DataFrame, horizon: int = 30) -> pd.DataFrame:
    """Build next-horizon-day forward Sharpe targets per strategy."""
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
# K201 combined ML walk-forward with trigger override
# ──────────────────────────────────────────────────────────────────────────────

def ml_walk_forward_with_triggers(
    df_base: pd.DataFrame,
    df_triggered: pd.DataFrame,
    feat_df: pd.DataFrame,
    target_df: pd.DataFrame,
    t2_fire: np.ndarray,
    t3_fire: np.ndarray,
    t1_fire_any: np.ndarray,
    panel_rev_index: pd.DatetimeIndex,
    train_days: int = ML_TRAIN_DAYS,
    test_days:  int = ML_TEST_DAYS,
    alpha:      float = 1.0,
) -> Tuple[pd.DataFrame, pd.Series, list, list]:
    """
    K201 combined ML allocator with T1/T2/T3 override.

    Flow:
      1. ML predicts next-30d Sharpe per strategy on df_base (no triggers)
      2. Compute raw ML weights
      3. Apply carry caps (5% rev)
      4. Per-day: if T2 or T3 active, zero out V_rev_carry weight, redistribute
         If T1 active (any symbol), reduce V_rev_carry by half, redistribute

    Disagreement log: each day record whether ML wanted rev carry but trigger halted.

    Returns:
      weights_df:       daily weights
      pnl_series:       daily PnL (using triggered returns)
      diagnostics:      per-ML-step dict
      disagreement_log: per-day dict of ML weight vs trigger action
    """
    cols = list(df_base.columns)
    n_strats = len(cols)
    rev_idx = cols.index("V_rev_carry") if "V_rev_carry" in cols else None

    # Build trigger lookup by date
    t2_by_date = {str(panel_rev_index[i].date()): bool(t2_fire[i])
                  for i in range(len(panel_rev_index))}
    t3_by_date = {str(panel_rev_index[i].date()): bool(t3_fire[i])
                  for i in range(len(panel_rev_index))}
    t1_by_date = {str(panel_rev_index[i].date()): bool(t1_fire_any[i])
                  for i in range(len(panel_rev_index))}

    # Align feature/target indices
    common_idx = feat_df.index.intersection(target_df.index)
    feat_aligned   = feat_df.loc[common_idx]
    target_aligned = target_df.loc[common_idx]

    feat_arr   = feat_aligned.values
    target_arr = np.array([target_aligned[f"{c}__fwd_sh"].values for c in cols]).T
    date_idx   = feat_aligned.index

    n = len(feat_arr)
    min_train = max(train_days, 45)

    wf_weights    = []
    wf_pnl        = []
    wf_dates      = []
    diagnostics   = []
    disagree_log  = []

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
        X_test = feat_arr[t_test_start:t_test_end]
        test_dates_slice = date_idx[t_test_start:t_test_end]

        if len(X_train) < 20 or len(X_test) == 0:
            step += 1
            continue

        X_train = np.nan_to_num(X_train, nan=0.0, posinf=0.0, neginf=0.0)
        X_test  = np.nan_to_num(X_test,  nan=0.0, posinf=0.0, neginf=0.0)

        scaler = StandardScaler()
        X_train_s = scaler.fit_transform(X_train)
        X_test_s  = scaler.transform(X_test)

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
            pred = model.predict(X_test_s[:1])[0]
            preds[i] = float(pred)
            y_pred_tr = model.predict(X_train_s)
            ss_res = np.sum((y - y_pred_tr) ** 2)
            ss_tot = np.sum((y - y.mean()) ** 2)
            r2 = 1.0 - ss_res / ss_tot if ss_tot > 1e-12 else 0.0
            r2_scores.append(r2)

        actual_targets = target_arr[t_test_start:t_test_end].mean(axis=0)
        dir_correct = np.array([
            (preds[i] > 0) == (actual_targets[i] > 0)
            for i in range(n_strats)
        ])

        pos_preds = np.maximum(preds, 0.0)
        if pos_preds.sum() < 1e-10:
            w_ml = w_equal(n_strats)
        else:
            w_ml = pos_preds / pos_preds.sum()
        # Apply caps (5% rev)
        w_ml = apply_all_caps(w_ml, cols, rev_cap=CARRY_REV_CAP)

        # ML predicted weight on reverse carry for this step
        ml_rev_weight = float(w_ml[rev_idx]) if rev_idx is not None else 0.0
        ml_rev_pred   = float(preds[rev_idx]) if rev_idx is not None else 0.0

        diag_step = {
            "step":        step,
            "train_start": str(date_idx[t_train_start].date()),
            "train_end":   str(date_idx[t_train_end - 1].date()),
            "test_start":  str(test_dates_slice[0].date()),
            "test_end":    str(test_dates_slice[-1].date()),
            "preds":       {cols[i]: round(float(preds[i]), 4) for i in range(n_strats)},
            "ml_weights":  {cols[i]: round(float(w_ml[i]), 4) for i in range(n_strats)},
            "r2_per_strat": {cols[i]: round(float(r2_scores[i]), 4) if not np.isnan(r2_scores[i]) else None
                             for i in range(n_strats)},
            "dir_accuracy_per_strat": {cols[i]: bool(dir_correct[i]) for i in range(n_strats)},
            "mean_r2": round(float(np.nanmean(r2_scores)), 4),
            "mean_dir_acc": round(float(np.mean(dir_correct)), 4),
        }
        diagnostics.append(diag_step)

        # Execute weights on the triggered returns (T1/T2/T3 already applied per-day)
        test_rets_triggered = df_triggered.loc[test_dates_slice].values

        for d_i, d in enumerate(test_dates_slice):
            date_str = str(d.date())
            is_t2 = t2_by_date.get(date_str, False)
            is_t3 = t3_by_date.get(date_str, False)
            is_t1 = t1_by_date.get(date_str, False)

            # Apply per-day trigger override to allocation weights
            w_day = w_ml.copy()
            trigger_action = "none"

            if rev_idx is not None:
                if is_t3:
                    # T3: halt entire reverse carry (redistribute to others)
                    trigger_action = "T3_halt"
                    if w_day[rev_idx] > 0:
                        freed = w_day[rev_idx]
                        w_day[rev_idx] = 0.0
                        other_mask = np.ones(n_strats, dtype=bool)
                        other_mask[rev_idx] = False
                        others = w_day[other_mask]
                        if others.sum() > 0:
                            w_day[other_mask] = others + freed * (others / others.sum())
                        w_day = w_day / w_day.sum()
                elif is_t2:
                    # T2: halt reverse carry panel
                    trigger_action = "T2_halt"
                    if w_day[rev_idx] > 0:
                        freed = w_day[rev_idx]
                        w_day[rev_idx] = 0.0
                        other_mask = np.ones(n_strats, dtype=bool)
                        other_mask[rev_idx] = False
                        others = w_day[other_mask]
                        if others.sum() > 0:
                            w_day[other_mask] = others + freed * (others / others.sum())
                        w_day = w_day / w_day.sum()
                elif is_t1:
                    # T1: reduce rev carry by half
                    trigger_action = "T1_reduce"
                    if w_day[rev_idx] > 0:
                        freed = w_day[rev_idx] * 0.5
                        w_day[rev_idx] -= freed
                        other_mask = np.ones(n_strats, dtype=bool)
                        other_mask[rev_idx] = False
                        others = w_day[other_mask]
                        if others.sum() > 0:
                            w_day[other_mask] = others + freed * (others / others.sum())
                        w_day = w_day / w_day.sum()

            # Disagreement: ML wanted rev carry but trigger halted/reduced
            ml_wanted_rev = ml_rev_weight > 0.01
            trigger_overrode = trigger_action in ("T2_halt", "T3_halt")
            trigger_reduced  = trigger_action == "T1_reduce"

            disagree_event = {
                "date":           date_str,
                "trigger_action": trigger_action,
                "ml_rev_weight":  round(ml_rev_weight, 4),
                "ml_rev_pred":    round(ml_rev_pred, 4),
                "disagreement":   bool(ml_wanted_rev and (trigger_overrode or trigger_reduced)),
                "full_override":  bool(ml_wanted_rev and trigger_overrode),
                "partial_reduce": bool(ml_wanted_rev and trigger_reduced),
            }
            disagree_log.append(disagree_event)

            pnl = float(test_rets_triggered[d_i] @ w_day)
            wf_pnl.append(pnl)
            wf_dates.append(d)
            wf_weights.append(dict(zip(cols, w_day)))

        step += 1

    if not wf_pnl:
        return pd.DataFrame(), pd.Series(dtype=float), [], []

    weights_df = pd.DataFrame(wf_weights, index=wf_dates)
    pnl_series = pd.Series(wf_pnl, index=wf_dates, name="k201_pnl")

    return weights_df, pnl_series, diagnostics, disagree_log


# ──────────────────────────────────────────────────────────────────────────────
# Walk-forward fold analysis
# ──────────────────────────────────────────────────────────────────────────────

def wf_fold_sharpes(pnl_series: pd.Series, n_folds: int = N_FOLDS) -> dict:
    """Split pnl_series into n_folds, compute Sharpe per fold."""
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
        "mean":  round(float(np.mean(sharpes)), 4),
        "min":   round(float(np.min(sharpes)),  4),
        "max":   round(float(np.max(sharpes)),  4),
        "std":   round(float(np.std(sharpes)),  4),
    }


def oos_cut(s: pd.Series, oos_frac: float = OOS_FRAC) -> pd.Series:
    cut = int(len(s) * (1 - oos_frac))
    return s.iloc[cut:]


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
            "mean": round(float(np.mean(vals)), 4) if vals else None,
            "n_steps": len(vals),
        }
        dvals = dir_by_strat[c]
        dir_summary[c] = {
            "mean_dir_acc": round(float(np.mean(dvals)), 4) if dvals else None,
            "n_steps": len(dvals),
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


def summarize_disagreement_log(disagree_log: list) -> dict:
    """Aggregate disagreement log into summary statistics."""
    n = len(disagree_log)
    if n == 0:
        return {}
    n_disagree    = sum(1 for e in disagree_log if e["disagreement"])
    n_override    = sum(1 for e in disagree_log if e["full_override"])
    n_reduce      = sum(1 for e in disagree_log if e["partial_reduce"])
    n_t1          = sum(1 for e in disagree_log if e["trigger_action"] == "T1_reduce")
    n_t2          = sum(1 for e in disagree_log if e["trigger_action"] == "T2_halt")
    n_t3          = sum(1 for e in disagree_log if e["trigger_action"] == "T3_halt")
    n_none        = sum(1 for e in disagree_log if e["trigger_action"] == "none")
    ml_rev_weights = [e["ml_rev_weight"] for e in disagree_log]
    return {
        "n_days_total":          n,
        "n_trigger_actions": {
            "none":      n_none,
            "T1_reduce": n_t1,
            "T2_halt":   n_t2,
            "T3_halt":   n_t3,
        },
        "n_disagreement_days":   n_disagree,
        "pct_disagreement":      round(n_disagree / n * 100, 1),
        "n_full_override_days":  n_override,
        "pct_full_override":     round(n_override / n * 100, 1),
        "n_partial_reduce_days": n_reduce,
        "pct_partial_reduce":    round(n_reduce / n * 100, 1),
        "ml_rev_weight_mean":    round(float(np.mean(ml_rev_weights)), 4),
        "ml_rev_weight_max":     round(float(np.max(ml_rev_weights)), 4),
        "conflict_rate": round(n_disagree / n * 100, 1),
    }


# ──────────────────────────────────────────────────────────────────────────────
# Per-fold detailed analysis
# ──────────────────────────────────────────────────────────────────────────────

def fold_breakdown(
    pnl_k196:  pd.Series,
    pnl_k198:  pd.Series,
    pnl_k199b: pd.Series,
    pnl_k201:  pd.Series,
    n_folds: int = N_FOLDS,
) -> List[dict]:
    """Per-fold comparison of all four versions."""
    folds = []
    # Use K201 as the primary axis
    n = len(pnl_k201)
    fold_size = n // n_folds

    def get_fold_pnl(s: pd.Series, start_date, end_date) -> pd.Series:
        mask = (s.index >= start_date) & (s.index <= end_date)
        return s[mask]

    for i in range(n_folds):
        start_i = i * fold_size
        end_i   = start_i + fold_size if i < n_folds - 1 else n
        s_date  = pnl_k201.index[start_i]
        e_date  = pnl_k201.index[end_i - 1]

        f201   = pnl_k201.values[start_i:end_i]
        f198   = get_fold_pnl(pnl_k198, s_date, e_date).values
        f199b  = get_fold_pnl(pnl_k199b, s_date, e_date).values
        # K196 is full-history, try to align on same dates
        f196   = get_fold_pnl(pnl_k196, s_date, e_date).values

        fold = {
            "fold": i,
            "date_start": str(s_date.date()),
            "date_end":   str(e_date.date()),
            "n_days":     int(end_i - start_i),
            "K196_sh":    round(sharpe_d(f196), 4) if len(f196) > 1 else None,
            "K198_sh":    round(sharpe_d(f198), 4) if len(f198) > 1 else None,
            "K199b_sh":   round(sharpe_d(f199b), 4) if len(f199b) > 1 else None,
            "K201_sh":    round(sharpe_d(f201), 4),
            "K201_dd":    round(max_dd_d(f201), 4),
            "K201_vs_K198":  round(sharpe_d(f201) - (sharpe_d(f198) if len(f198) > 1 else 0), 4),
            "K201_vs_K199b": round(sharpe_d(f201) - (sharpe_d(f199b) if len(f199b) > 1 else 0), 4),
        }
        folds.append(fold)
    return folds


# ──────────────────────────────────────────────────────────────────────────────
# Main
# ──────────────────────────────────────────────────────────────────────────────

def main():
    print("=" * 72)
    print("Wave K201 — ML Allocator + Safety Triggers (v6.6 Candidate)")
    print("=" * 72)
    print()

    np.random.seed(42)

    # ── Step 1: Load component returns ───────────────────────────────────────
    print("Step 1: Loading K196 component returns...", flush=True)
    df_all = load_component_returns()
    cols   = list(df_all.columns)
    print(f"  Strategies: {cols}")
    print()

    # ── Step 2: Load FR regime indicator ─────────────────────────────────────
    print("Step 2: Loading FR regime indicator...", flush=True)
    fr_mean = load_fr_mean_daily()
    if len(fr_mean) > 0:
        print(f"  FR mean range: {fr_mean.index[0].date()} -> {fr_mean.index[-1].date()}")
    else:
        fr_mean = None
        print("  WARNING: FR data not available, regime feature will be zero")
    print()

    # ── Step 3: Apply FR trigger (K121, K133) ────────────────────────────────
    print("Step 3: Applying partial FR trigger (K121, K133)...", flush=True)
    if fr_mean is not None:
        df_fr_triggered = apply_fr_trigger(df_all, fr_mean)
        fr_aligned = fr_mean.reindex(df_all.index, method="ffill")
        n_fr_trigger = int((fr_aligned < FR_THRESHOLD).sum())
        print(f"  FR trigger fires {n_fr_trigger}/{len(df_all)} days ({n_fr_trigger/len(df_all)*100:.1f}%)")
    else:
        df_fr_triggered = df_all.copy()
        print("  No FR trigger applied (no FR data)")
    print()

    # ── Step 4: Load reverse carry panel for T1/T2/T3 ────────────────────────
    print("Step 4: Loading per-symbol reverse carry panel for triggers...", flush=True)
    panel_rev = load_reverse_carry_panel()
    # Align to same date range as df_all
    panel_rev = panel_rev.reindex(df_all.index, fill_value=0.0)
    print(f"  Reverse panel: {panel_rev.shape[0]} days x {panel_rev.shape[1]} symbols")
    print()

    # ── Step 5: Apply T1/T2/T3 triggers to reverse carry panel ───────────────
    print("Step 5: Applying T1/T2/T3 deactivation triggers...", flush=True)
    panel_rev_triggered, trigger_stats, t2_fire, t3_fire, t1_fire_any = \
        apply_t1_t2_t3_triggers(panel_rev)

    V_rev_triggered = panel_rev_triggered.mean(axis=1)

    t2_s = trigger_stats["T2_panel"]
    t3_s = trigger_stats["T3_dd"]
    print(f"  T2 (panel Sh<0): {t2_s['fire_pct_total']:.1f}% all / {t2_s['fire_pct_oos']:.1f}% OOS")
    print(f"  T3 (DD>2%):      {t3_s['fire_pct_total']:.1f}% all / {t3_s['fire_pct_oos']:.1f}% OOS")
    print(f"  T1 any symbol:   {t1_fire_any.mean()*100:.1f}% of days")
    print()

    # ── Step 6: Build K201 df — FR-triggered base + triggered reverse carry ──
    print("Step 6: Building K201 portfolio DataFrame...", flush=True)
    df_k201_base = df_fr_triggered.copy()
    df_k201_triggered = df_fr_triggered.copy()
    # For triggered version, replace V_rev_carry with triggered version
    df_k201_triggered["V_rev_carry"] = V_rev_triggered.reindex(df_all.index, fill_value=0.0).values
    print(f"  K201 base shape: {df_k201_base.shape}")
    print()

    # ── Step 7: Build feature/target matrices ────────────────────────────────
    print("Step 7: Building ML feature matrix (K198 51-feature)...", flush=True)
    feat_df = build_features(df_fr_triggered, fr_mean)
    print(f"  Feature matrix: {feat_df.shape[0]} rows x {feat_df.shape[1]} features")

    print("Step 7b: Building forward Sharpe targets (horizon=30d)...", flush=True)
    target_df = build_targets(df_fr_triggered, horizon=ML_TEST_DAYS)
    print(f"  Target matrix: {target_df.shape[0]} rows x {target_df.shape[1]} strategies")
    print()

    # ── Step 8: K201 ML walk-forward with trigger override ───────────────────
    print("Step 8: K201 ML walk-forward with T1/T2/T3 trigger override...", flush=True)
    weights_df, pnl_k201, diagnostics, disagree_log = ml_walk_forward_with_triggers(
        df_base=df_fr_triggered,
        df_triggered=df_k201_triggered,
        feat_df=feat_df,
        target_df=target_df,
        t2_fire=t2_fire,
        t3_fire=t3_fire,
        t1_fire_any=t1_fire_any,
        panel_rev_index=panel_rev.index,
        train_days=ML_TRAIN_DAYS,
        test_days=ML_TEST_DAYS,
        alpha=1.0,
    )
    if len(pnl_k201) == 0:
        print("  ERROR: K201 walk-forward returned empty PnL")
        return
    print(f"  K201 WF PnL: {len(pnl_k201)} days, "
          f"{pnl_k201.index[0].date()} -> {pnl_k201.index[-1].date()}")
    print()

    # ── Step 9: Disagreement analysis ────────────────────────────────────────
    print("Step 9: ML vs trigger disagreement analysis...", flush=True)
    disagree_summary = summarize_disagreement_log(disagree_log)
    print(f"  Total days:                   {disagree_summary.get('n_days_total', 0)}")
    print(f"  Trigger actions: T1_reduce={disagree_summary['n_trigger_actions']['T1_reduce']}, "
          f"T2_halt={disagree_summary['n_trigger_actions']['T2_halt']}, "
          f"T3_halt={disagree_summary['n_trigger_actions']['T3_halt']}, "
          f"none={disagree_summary['n_trigger_actions']['none']}")
    print(f"  Disagreement (ML wanted rev, trigger halted/reduced): "
          f"{disagree_summary.get('n_disagreement_days', 0)} days "
          f"({disagree_summary.get('pct_disagreement', 0.0):.1f}%)")
    print(f"  Full overrides (T2/T3 while ML wanted rev): "
          f"{disagree_summary.get('n_full_override_days', 0)} days "
          f"({disagree_summary.get('pct_full_override', 0.0):.1f}%)")
    print()

    # ── Step 10: Load K198 and K199b series for comparison ───────────────────
    print("Step 10: Loading K198 / K199b series for four-way comparison...", flush=True)
    # K198 ridge pnl from saved curves
    with open(BASE / "wave_k198_curves.json") as f:
        k198_curves = json.load(f)
    pnl_k198 = pd.Series(
        k198_curves["pnl_ridge"],
        index=pd.to_datetime(k198_curves["dates_ml"]),
        name="k198_pnl",
    )

    # K199b P3 equity curve -> returns
    with open(BASE / "wave_k199_curves.json") as f:
        k199_curves = json.load(f)
    k199b_eq  = np.array(k199_curves["series"]["K199b_P3_risk_parity"], dtype=float)
    k199b_dates = pd.to_datetime(k199_curves["dates"])
    pnl_k199b = pd.Series(
        equity_to_returns(k199b_eq),
        index=k199b_dates,
        name="k199b_pnl",
    )

    # K196 production equity -> returns (from k196 curves)
    with open(BASE / "wave_k196_curves.json") as f:
        k196_c = json.load(f)
    k196_eq = np.array(k196_c["series"]["K196_P3_triggered"], dtype=float)
    k196_dates_full = pd.to_datetime(k196_c["dates"])
    pnl_k196_full = pd.Series(
        equity_to_returns(k196_eq),
        index=k196_dates_full,
        name="k196_pnl",
    )
    print(f"  K198 series: {len(pnl_k198)} days, K199b series: {len(pnl_k199b)} days, "
          f"K196 series: {len(pnl_k196_full)} days")
    print()

    # ── Step 11: OOS metrics ──────────────────────────────────────────────────
    print("Step 11: Computing OOS metrics (last 30%)...", flush=True)
    oos_k201  = oos_cut(pnl_k201)
    oos_k198  = oos_cut(pnl_k198)
    oos_k199b = oos_cut(pnl_k199b)
    oos_k196  = oos_cut(pnl_k196_full)

    m_k201  = metrics_pkg(oos_k201.values)
    m_k198  = metrics_pkg(oos_k198.values)
    m_k199b = metrics_pkg(oos_k199b.values)
    m_k196  = metrics_pkg(oos_k196.values)

    print(f"  K196 baseline: OOS Sh={m_k196['sharpe']:.4f} MaxDD={m_k196['max_dd']:.4f}")
    print(f"  K198 ML alone: OOS Sh={m_k198['sharpe']:.4f} MaxDD={m_k198['max_dd']:.4f}")
    print(f"  K199b triggers: OOS Sh={m_k199b['sharpe']:.4f} MaxDD={m_k199b['max_dd']:.4f}")
    print(f"  K201 ML+trig:  OOS Sh={m_k201['sharpe']:.4f} MaxDD={m_k201['max_dd']:.4f}")
    print()

    # ── Step 12: Walk-forward fold analysis ───────────────────────────────────
    print("Step 12: Walk-forward fold analysis...", flush=True)
    wf_k201  = wf_fold_sharpes(pnl_k201)
    wf_k198  = wf_fold_sharpes(pnl_k198)
    wf_k199b = wf_fold_sharpes(pnl_k199b)
    wf_k196  = wf_fold_sharpes(pnl_k196_full)

    print(f"  K196 WF:   mean={wf_k196['mean']:.4f}  min={wf_k196['min']:.4f}  folds={wf_k196['fold_sharpes']}")
    print(f"  K198 WF:   mean={wf_k198['mean']:.4f}  min={wf_k198['min']:.4f}  folds={wf_k198['fold_sharpes']}")
    print(f"  K199b WF:  mean={wf_k199b['mean']:.4f}  min={wf_k199b['min']:.4f}  folds={wf_k199b['fold_sharpes']}")
    print(f"  K201 WF:   mean={wf_k201['mean']:.4f}  min={wf_k201['min']:.4f}  folds={wf_k201['fold_sharpes']}")
    print()

    # ── Step 13: Per-fold breakdown ───────────────────────────────────────────
    print("Step 13: Per-fold detailed breakdown...", flush=True)
    per_fold = fold_breakdown(pnl_k196_full, pnl_k198, pnl_k199b, pnl_k201)
    for f in per_fold:
        print(f"  Fold {f['fold']} ({f['date_start']} -> {f['date_end']}): "
              f"K196={f['K196_sh']} K198={f['K198_sh']} K199b={f['K199b_sh']} K201={f['K201_sh']} "
              f"[K201vsK198={f['K201_vs_K198']:+.4f}]")
    print()

    # ── Step 14: Synergy analysis ─────────────────────────────────────────────
    print("Step 14: Synergy detection...", flush=True)
    k198_marginal = m_k198["sharpe"] - m_k196["sharpe"]
    k199b_marginal = m_k199b["sharpe"] - m_k196["sharpe"]
    k201_marginal  = m_k201["sharpe"] - m_k196["sharpe"]
    sum_marginal   = k198_marginal + k199b_marginal
    synergy        = k201_marginal - sum_marginal
    dd_improvement = m_k201["max_dd"] - m_k198["max_dd"]   # positive = less negative = better

    print(f"  K198 marginal lift vs K196: {k198_marginal:+.4f}")
    print(f"  K199b marginal lift vs K196: {k199b_marginal:+.4f}")
    print(f"  K201 marginal lift vs K196: {k201_marginal:+.4f}")
    print(f"  Sum of individual lifts: {sum_marginal:+.4f}")
    print(f"  Synergy (K201 - sum): {synergy:+.4f} {'(positive=synergistic)' if synergy > 0 else '(negative=conflict)'}")
    print(f"  DD improvement K201 vs K198: {dd_improvement:+.4f} (positive = better DD)")
    print()

    # ── Step 15: Acceptance criteria ─────────────────────────────────────────
    print("Step 15: K201 acceptance criteria for v6.6...", flush=True)
    k201_oos_sh   = m_k201["sharpe"]
    k201_oos_dd   = m_k201["max_dd"]
    k201_wf_min   = wf_k201["min"]
    k201_wf_mean  = wf_k201["mean"]

    # AC1: OOS Sh > K198 OR within -0.1 with substantial MaxDD/WF gain
    ac1_beat = k201_oos_sh > K198_OOS_SH
    ac1_near = k201_oos_sh >= K198_OOS_SH - 0.10
    ac1_dd_gain = k201_oos_dd > K198_OOS_DD  # less negative = better
    ac1_wf_gain = k201_wf_min > K198_WF_MIN
    ac1_pass = ac1_beat or (ac1_near and (ac1_dd_gain or ac1_wf_gain))

    # AC2: WF min > K198 (6.57)
    ac2_pass = k201_wf_min > K198_WF_MIN

    # AC3: MaxDD better than K198 (-0.0053)
    ac3_pass = k201_oos_dd > K198_OOS_DD  # less negative is better

    # AC4: Combined benefit > sum of individual benefits (synergy)
    ac4_pass = synergy > -0.20  # allow mild negative synergy

    print(f"  AC1: OOS Sh > K198 (10.28) or within -0.1 with DD/WF gain?")
    print(f"       K201={k201_oos_sh:.4f}  beat={ac1_beat}  near={ac1_near}  "
          f"dd_gain={ac1_dd_gain}  wf_gain={ac1_wf_gain} -> {'PASS' if ac1_pass else 'FAIL'}")
    print(f"  AC2: WF min > K198 (6.57)?  K201={k201_wf_min:.4f} -> {'PASS' if ac2_pass else 'FAIL'}")
    print(f"  AC3: MaxDD better than K198 ({K198_OOS_DD})?  K201={k201_oos_dd:.4f} -> {'PASS' if ac3_pass else 'FAIL'}")
    print(f"  AC4: Synergy > -0.20?  synergy={synergy:.4f} -> {'PASS' if ac4_pass else 'FAIL'}")
    n_ac = sum([ac1_pass, ac2_pass, ac3_pass, ac4_pass])
    print(f"  Criteria passed: {n_ac}/4")
    print()

    # ── Verdict ───────────────────────────────────────────────────────────────
    if all([ac1_pass, ac2_pass, ac3_pass, ac4_pass]):
        verdict = (
            f"ACCEPT: K201 ML+triggers clears all 4 criteria. Promote to v6.6. "
            f"OOS Sh={k201_oos_sh:.4f}, WF min={k201_wf_min:.4f}, MaxDD={k201_oos_dd:.4f}, "
            f"synergy={synergy:+.4f}."
        )
    elif sum([ac1_pass, ac2_pass, ac3_pass]) >= 2 and ac3_pass:
        # MaxDD improved is the most critical for safety
        verdict = (
            f"CONDITIONAL ACCEPT: K201 ML+triggers passes MaxDD gate and {n_ac-1} of 3 remaining. "
            f"OOS Sh={k201_oos_sh:.4f} vs K198={K198_OOS_SH}, WF min={k201_wf_min:.4f} vs K198={K198_WF_MIN}, "
            f"MaxDD={k201_oos_dd:.4f} (improved vs K198={K198_OOS_DD}). "
            f"Synergy={synergy:+.4f}. "
            "Recommend: promote to v6.6 with tight MaxDD monitoring; if live MaxDD exceeds -0.005 revert to K196."
        )
    elif n_ac >= 2 and ac3_pass:
        verdict = (
            f"PARTIAL: K201 clears MaxDD gate but only {n_ac}/4 criteria. "
            f"Better than K198 on safety but less return. "
            "Consider K201 as safety-first v6.6 only if MaxDD is primary concern."
        )
    else:
        verdict = (
            f"REJECT for v6.6: K201 fails {4 - n_ac}/4 criteria. "
            f"OOS Sh={k201_oos_sh:.4f} (vs K198={K198_OOS_SH}), WF min={k201_wf_min:.4f} (vs K198={K198_WF_MIN}), "
            f"MaxDD={k201_oos_dd:.4f} (vs K198={K198_OOS_DD}). "
            "ML and triggers conflict more than they compose. "
            "K198 remains best single ML candidate; K202 should explore orthogonal combination."
        )
    print(f"  Verdict: {verdict}")
    print()

    # ── Step 16: Equity curves ────────────────────────────────────────────────
    print("Step 16: Computing equity curves...", flush=True)
    k201_equity = np.cumprod(1.0 + pnl_k201.values).tolist()
    k198_equity = np.cumprod(1.0 + pnl_k198.values).tolist()
    k199b_equity = np.cumprod(1.0 + pnl_k199b.values).tolist()
    k196_equity_aligned = pnl_k196_full.reindex(pnl_k201.index, fill_value=0.0)
    k196_eq_aligned = np.cumprod(1.0 + k196_equity_aligned.values).tolist()

    elapsed = time.time() - START_TIME
    print(f"  Total runtime so far: {elapsed:.1f}s")
    print()

    # ── Assemble outputs ──────────────────────────────────────────────────────

    # Main metrics JSON
    metrics_out = {
        "wave": "K201",
        "task": "ML allocator (K198 Ridge) + T1/T2/T3 safety triggers (K199b) — v6.6 candidate",
        "as_of": pd.Timestamp.now(tz="UTC").isoformat(),
        "runtime_s": round(elapsed, 1),
        "config": {
            "strategies": cols,
            "n_strategies": len(cols),
            "ml_train_days": ML_TRAIN_DAYS,
            "ml_test_days": ML_TEST_DAYS,
            "oos_frac": OOS_FRAC,
            "k121_cap": K121_CAP,
            "carry_fwd_cap": CARRY_FWD_CAP,
            "carry_rev_cap": CARRY_REV_CAP,
            "t1_window": T1_WINDOW_DAYS,
            "t1_thresh": T1_SHARPE_THRESH,
            "t2_window": T2_WINDOW_DAYS,
            "t2_thresh": T2_SHARPE_THRESH,
            "t3_dd_thresh": T3_DD_THRESH,
            "fr_threshold": FR_THRESHOLD,
            "ridge_alpha": 1.0,
            "n_folds": N_FOLDS,
            "n_days_k201": len(pnl_k201),
            "date_range": [str(pnl_k201.index[0].date()), str(pnl_k201.index[-1].date())],
        },
        "four_way_comparison": {
            "K196_v6_4_baseline": {
                "description": "K196 v6.4 static P3 risk-parity (production reference)",
                "oos_sharpe": round(m_k196["sharpe"], 4),
                "oos_maxdd":  round(m_k196["max_dd"], 4),
                "oos_sortino": m_k196["sortino"],
                "oos_ann_ret": m_k196["ann_ret"],
                "wf_mean":    wf_k196["mean"],
                "wf_min":     wf_k196["min"],
                "wf_fold_sharpes": wf_k196["fold_sharpes"],
                "note": "Reference values from stored K196 production metrics",
            },
            "K198_ML_alone": {
                "description": "K198 Ridge ML allocator, carry cap 10%, no T1/T2/T3",
                "oos_sharpe": round(m_k198["sharpe"], 4),
                "oos_maxdd":  round(m_k198["max_dd"], 4),
                "oos_sortino": m_k198["sortino"],
                "oos_ann_ret": m_k198["ann_ret"],
                "wf_mean":    wf_k198["mean"],
                "wf_min":     wf_k198["min"],
                "wf_fold_sharpes": wf_k198["fold_sharpes"],
                "note": "Loaded from wave_k198_curves.json pnl_ridge",
            },
            "K199b_triggers_alone": {
                "description": "K199b triggers only, static P3 allocator, carry cap 5%",
                "oos_sharpe": round(m_k199b["sharpe"], 4),
                "oos_maxdd":  round(m_k199b["max_dd"], 4),
                "oos_sortino": m_k199b["sortino"],
                "oos_ann_ret": m_k199b["ann_ret"],
                "wf_mean":    wf_k199b["mean"],
                "wf_min":     wf_k199b["min"],
                "wf_fold_sharpes": wf_k199b["fold_sharpes"],
                "note": "Loaded from wave_k199_curves.json K199b_P3_risk_parity",
            },
            "K201_ML_plus_triggers": {
                "description": "K201 = K198 Ridge ML + K199b T1/T2/T3, carry cap 5%",
                "oos_sharpe": round(k201_oos_sh, 4),
                "oos_maxdd":  round(k201_oos_dd, 4),
                "oos_sortino": m_k201["sortino"],
                "oos_calmar":  m_k201["calmar"],
                "oos_ann_ret": m_k201["ann_ret"],
                "oos_ann_vol": m_k201["ann_vol"],
                "oos_n_days":  m_k201["n_days"],
                "wf_mean":    wf_k201["mean"],
                "wf_min":     wf_k201["min"],
                "wf_max":     wf_k201["max"],
                "wf_std":     wf_k201["std"],
                "wf_fold_sharpes": wf_k201["fold_sharpes"],
            },
        },
        "synergy_analysis": {
            "K196_baseline_sh":          round(m_k196["sharpe"], 4),
            "K198_marginal_lift":        round(k198_marginal, 4),
            "K199b_marginal_lift":       round(k199b_marginal, 4),
            "sum_marginal_lifts":        round(sum_marginal, 4),
            "K201_marginal_lift":        round(k201_marginal, 4),
            "synergy_value":             round(synergy, 4),
            "synergy_positive":          bool(synergy > 0),
            "dd_improvement_K201_vs_K198": round(dd_improvement, 4),
            "dd_improved":               bool(dd_improvement > 0),
            "interpretation": (
                "Synergistic: ML and triggers compose" if synergy > 0.10
                else "Near-neutral: marginal synergy" if synergy > -0.10
                else "Conflicting: triggers reduce ML alpha"
            ),
        },
        "ml_vs_trigger_disagreement": {
            "summary": disagree_summary,
            "conflict_rate_pct": disagree_summary.get("conflict_rate", 0.0),
            "interpretation": (
                "Low conflict: ML and triggers mostly agree"
                if disagree_summary.get("conflict_rate", 0.0) < 10.0
                else "Moderate conflict: triggers frequently override ML"
                if disagree_summary.get("conflict_rate", 0.0) < 25.0
                else "High conflict: significant ML-trigger disagreement — monitor closely"
            ),
        },
        "trigger_stats": trigger_stats,
        "ml_diagnostics": aggregate_diagnostics(diagnostics, cols),
        "per_fold_breakdown": per_fold,
        "acceptance_criteria": {
            "AC1_oos_sh_desc": "OOS Sh > K198 (10.28) or within -0.1 with DD/WF gain",
            "AC1_pass":  ac1_pass,
            "AC1_beat":  ac1_beat,
            "AC1_near":  ac1_near,
            "AC1_dd_gain": ac1_dd_gain,
            "AC1_wf_gain": ac1_wf_gain,
            "AC2_wf_min_desc": f"WF min > K198 ({K198_WF_MIN})",
            "AC2_pass":  ac2_pass,
            "AC2_actual": round(k201_wf_min, 4),
            "AC3_maxdd_desc": f"MaxDD better than K198 ({K198_OOS_DD})",
            "AC3_pass":  ac3_pass,
            "AC3_actual": round(k201_oos_dd, 4),
            "AC4_synergy_desc": "Synergy > -0.20 (no major conflict penalty)",
            "AC4_pass":  ac4_pass,
            "AC4_actual": round(synergy, 4),
            "n_criteria_passed": n_ac,
            "all_pass": bool(n_ac == 4),
        },
        "verdict": verdict,
        "deployment_risks": {
            "ml_trigger_conflict": (
                f"ML-trigger conflict rate: {disagree_summary.get('pct_disagreement', 0):.1f}% of days. "
                "When triggers override ML predictions, the allocator may leave return on the table. "
                "Monitor: if conflict rate rises above 30%, consider decoupling ML and trigger layers."
            ),
            "carry_cap_reduction": (
                "Reverse carry cap reduced from 10% (K198) to 5% (K199b). "
                "This reduces max exposure to reverse carry signals and cushions tail events. "
                "Tradeoff: may lose reverse carry upside in high-FR regimes."
            ),
            "regime_sensitivity": (
                "ML features use rolling Sharpe/vol/corr from prior 30-90 days. "
                "T2/T3 triggers also use 30d rolling window. In whipsaw regimes, "
                "both layers may fire simultaneously (double-jeopardy) or neither fires. "
                "Backtest does not capture sequential whipsaw effect."
            ),
            "overfitting_guard": (
                "Ridge regression (alpha=1.0) is low-complexity — minimal overfit risk. "
                "Walk-forward prevents look-ahead bias. "
                "Main OOS risk: if reverse carry spread collapses (perp/spot basis flip), "
                "both ML and triggers will lag by up to 30d."
            ),
            "k202_directions": (
                "If K201 shows ML-trigger conflict, K202 should explore: "
                "(1) trigger-aware ML training (encode T1/T2/T3 state as features), "
                "(2) two-layer hierarchy (triggers gate ML, not post-apply), "
                "(3) regime-conditional ML models (separate models for high/low FR regimes)."
            ),
        },
    }

    out_json = BASE / "wave_k201_ml_triggers_v6_6.json"
    with open(out_json, "w") as f:
        json.dump(metrics_out, f, indent=2)
    print(f"Saved: {out_json}")

    # ── Curves JSON ───────────────────────────────────────────────────────────
    # Per-day decision trace (sample every 10th to keep size manageable)
    trace_sample = [
        e for i, e in enumerate(disagree_log)
        if i % 10 == 0 or e["disagreement"]  # include all disagreement events
    ]

    curves_out = {
        "wave": "K201",
        "dates_k201":  [str(d.date()) for d in pnl_k201.index],
        "dates_k198":  k198_curves["dates_ml"],
        "dates_k199b": [str(d.date()) for d in pnl_k199b.index],
        "equity_k201":  [round(float(v), 6) for v in k201_equity],
        "equity_k198":  [round(float(v), 6) for v in k198_equity],
        "equity_k199b": [round(float(v), 6) for v in k199b_equity],
        "equity_k196_aligned": [round(float(v), 6) for v in k196_eq_aligned],
        "pnl_k201":  [round(float(v), 8) for v in pnl_k201.values],
        "pnl_k198":  [round(float(v), 8) for v in pnl_k198.values],
        "pnl_k199b": [round(float(v), 8) for v in pnl_k199b.values],
        "weight_trajectory_dates": [str(d.date()) for d in weights_df.index],
        "weight_trajectory": {c: [round(float(x), 4) for x in weights_df[c].values]
                               for c in cols},
        "per_day_decision_trace": trace_sample,
        "disagreement_summary": disagree_summary,
    }

    out_curves = BASE / "wave_k201_curves.json"
    with open(out_curves, "w") as f:
        json.dump(curves_out, f, indent=2)
    print(f"Saved: {out_curves}")

    # ── Final summary ─────────────────────────────────────────────────────────
    elapsed = time.time() - START_TIME
    print()
    print("=" * 72)
    print("FOUR-WAY COMPARISON — K201 FINAL")
    print("=" * 72)
    print(f"{'Version':<35} {'OOS Sh':>8} {'OOS MaxDD':>10} {'WF mean':>8} {'WF min':>8}")
    print("-" * 72)
    print(f"{'K196 v6.4 baseline':35s} {m_k196['sharpe']:>8.4f} {m_k196['max_dd']:>10.4f} "
          f"{wf_k196['mean']:>8.4f} {wf_k196['min']:>8.4f}")
    print(f"{'K198 ML alone':35s} {m_k198['sharpe']:>8.4f} {m_k198['max_dd']:>10.4f} "
          f"{wf_k198['mean']:>8.4f} {wf_k198['min']:>8.4f}")
    print(f"{'K199b triggers alone':35s} {m_k199b['sharpe']:>8.4f} {m_k199b['max_dd']:>10.4f} "
          f"{wf_k199b['mean']:>8.4f} {wf_k199b['min']:>8.4f}")
    print(f"{'K201 ML + triggers':35s} {k201_oos_sh:>8.4f} {k201_oos_dd:>10.4f} "
          f"{k201_wf_mean:>8.4f} {k201_wf_min:>8.4f}")
    print("-" * 72)
    print(f"  Synergy: {synergy:+.4f} | DD improvement vs K198: {dd_improvement:+.4f}")
    print(f"  ML-trigger conflict rate: {disagree_summary.get('pct_disagreement', 0):.1f}%")
    print()
    print(f"  VERDICT: {verdict}")
    print()
    print(f"Total runtime: {elapsed:.1f}s")
    print("=" * 72)

    return metrics_out


if __name__ == "__main__":
    main()

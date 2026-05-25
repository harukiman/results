"""Wave K255 — K198_NoK116: Fine-Tune K198 by Removing K116 Sub-Component.

Objective:
  K252 identified K116 as the worst fold-2 marginal contributor (-1.22).
  Test if removing K116 from K198's ensemble improves K246a v6.9.

K198 Original 10 subs:
  v4.1, V1, K114, K116, K121, K133, K147, K175_DAR, V_fwd_carry, V_rev_carry

K255 K198_NoK116 = 9 subs:
  v4.1, V1, K114, K121, K133, K147, K175_DAR, V_fwd_carry, V_rev_carry

Test:
  1. Reconstruct K198_NoK116 with same Ridge ML allocator + caps
  2. Walk-forward 4-fold standalone metrics
  3. K255_a = K198_NoK116 + K208 + K226 (inv-vol + K226 cap 20%)
  4. Compare vs K246a baseline (OOS Sh 12.69, WF min 8.93, Fold2 8.93)

Acceptance gates vs K246a v6.9:
  - OOS Sh >= 12.69
  - WF min >= 8.93
  - Fold 2 Sh improved by at least +0.5
  - MaxDD <= -0.00115

Runtime: <12 min
"""
from __future__ import annotations

import json
import math
import time
import warnings
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import numpy as np
import pandas as pd
from sklearn.linear_model import Ridge
from sklearn.preprocessing import StandardScaler

warnings.filterwarnings("ignore")

t0 = time.time()
BASE = Path("/Users/nekonaomichi/crypto-lab")
CACHE = BASE / "cache"

TRADING_DAYS = 365
OOS_FRAC = 0.30
N_FOLDS = 4

# ML walk-forward params (same as K198)
ML_TRAIN_DAYS = 90
ML_TEST_DAYS = 30

# K198 original strategy names
STRATEGY_NAMES_FULL = [
    "v4.1", "V1", "K114", "K116", "K121", "K133",
    "K147", "K175_DAR", "V_fwd_carry", "V_rev_carry",
]

# K198_NoK116: remove K116
STRATEGY_NAMES_NO_K116 = [
    "v4.1", "V1", "K114", "K121", "K133",
    "K147", "K175_DAR", "V_fwd_carry", "V_rev_carry",
]

# Caps (same as K198)
K121_CAP = 0.30
CARRY_FWD_CAP = 0.10
CARRY_REV_CAP = 0.10

# FR trigger (same as K198)
FR_SYMBOLS = ["BTC", "ETH", "DOGE", "AVAX", "SOL", "XRP"]
FR_THRESHOLD = -0.009735
FR_COMPONENTS = ["K121", "K133"]

# K246a v6.9 baseline
K246A_OOS_SH = 12.6929
K246A_WF_MIN = 8.9347
K246A_WF_MEAN = 12.2462
K246A_MAXDD = -0.001145
K246A_FOLDS = [13.6029, 8.9347, 13.8374, 12.6097]
K246A_FOLD2 = 8.9347

# Acceptance gates
GATE_OOS_SH = 12.69
GATE_WF_MIN = 8.93
GATE_FOLD2_IMPROVEMENT = 0.50
GATE_MAXDD = -0.00115

ANN = math.sqrt(TRADING_DAYS)

print("=" * 70)
print("Wave K255: K198_NoK116 — Remove K116 Sub-Component Fine-Tune")
print("=" * 70)

# ─────────────────────────────────────────────────────────────────────────────
# Metric utilities
# ─────────────────────────────────────────────────────────────────────────────

def sharpe(r: np.ndarray) -> float:
    r = np.asarray(r, dtype=float)
    r = r[~np.isnan(r)]
    if len(r) < 2 or r.std(ddof=1) == 0:
        return 0.0
    return float(r.mean() / r.std(ddof=1) * ANN)


def maxdd(r: np.ndarray) -> float:
    eq = np.cumprod(1.0 + np.asarray(r, dtype=float))
    peak = np.maximum.accumulate(eq)
    return float((eq / peak - 1.0).min())


def equity_curve(rets: np.ndarray) -> List[float]:
    eq = np.empty(len(rets) + 1)
    eq[0] = 1.0
    eq[1:] = np.cumprod(1 + rets)
    return [round(float(v), 8) for v in eq.tolist()]


def oos_metrics_arr(rets: np.ndarray, oos_frac: float = OOS_FRAC) -> Dict:
    cut = int(len(rets) * (1 - oos_frac))
    oos = rets[cut:]
    if len(oos) < 5:
        return {"oos_sharpe": 0.0, "oos_maxdd": 0.0, "oos_n_days": 0}
    return {
        "oos_sharpe": round(sharpe(oos), 4),
        "oos_maxdd": round(maxdd(oos), 6),
        "oos_n_days": int(len(oos)),
        "oos_ann_ret": round(float(np.mean(oos) * TRADING_DAYS), 4),
    }


def wf_stats(rets: np.ndarray, dates: List[str], n_folds: int = N_FOLDS) -> Dict:
    fold_size = len(rets) // n_folds
    fold_sharpes, fold_details = [], []
    for i in range(n_folds):
        s = i * fold_size
        e = (i + 1) * fold_size if i < n_folds - 1 else len(rets)
        fs = sharpe(rets[s:e])
        fold_sharpes.append(fs)
        fold_details.append({
            "fold": i + 1,
            "start_idx": s, "end_idx": e, "n_days": e - s,
            "sharpe": round(float(fs), 4),
            "start_date": dates[s] if s < len(dates) else "",
            "end_date": dates[min(e - 1, len(dates) - 1)] if dates else "",
        })
    return {
        "fold_sharpes": [round(s, 4) for s in fold_sharpes],
        "fold_details": fold_details,
        "wf_mean": round(float(np.mean(fold_sharpes)), 4),
        "wf_min": round(float(np.min(fold_sharpes)), 4),
        "wf_max": round(float(np.max(fold_sharpes)), 4),
    }


# ─────────────────────────────────────────────────────────────────────────────
# Weight utilities (identical to K198)
# ─────────────────────────────────────────────────────────────────────────────

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
# Data loading
# ─────────────────────────────────────────────────────────────────────────────

def load_component_returns(strategy_names: List[str]) -> pd.DataFrame:
    """Load sub-component returns from K192/K195/K196 (same as K198)."""
    # 8 base components from K192
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

    # Forward carry from K195
    with open(BASE / "wave_k195_curves.json") as f:
        k195 = json.load(f)
    k195_panel_dates = pd.to_datetime(k195["panel_dates"])
    fwd_eq = np.array(k195["series"]["V_eq_w"], dtype=float)
    fwd_ret = pd.Series(
        np.r_[fwd_eq[0] - 1.0, fwd_eq[1:] / fwd_eq[:-1] - 1.0],
        index=k195_panel_dates, name="V_fwd_carry",
    )

    # Reverse carry from K196
    with open(BASE / "wave_k196_curves.json") as f:
        k196 = json.load(f)
    k196_panel_dates = pd.to_datetime(k196["panel_dates"])
    rev_eq = np.array(k196["series"]["V_rev_eq_w"], dtype=float)
    rev_ret = pd.Series(
        np.r_[rev_eq[0] - 1.0, rev_eq[1:] / rev_eq[:-1] - 1.0],
        index=k196_panel_dates, name="V_rev_carry",
    )

    # Align on common dates
    all_start = max(base_df.index[0], fwd_ret.index[0], rev_ret.index[0])
    all_end = min(base_df.index[-1], fwd_ret.index[-1], rev_ret.index[-1])

    base_trimmed = base_df[(base_df.index >= all_start) & (base_df.index <= all_end)]
    fwd_trimmed = fwd_ret[(fwd_ret.index >= all_start) & (fwd_ret.index <= all_end)]
    rev_trimmed = rev_ret[(rev_ret.index >= all_start) & (rev_ret.index <= all_end)]

    df_all = pd.concat([base_trimmed, fwd_trimmed, rev_trimmed], axis=1).dropna()

    # Select only the requested strategy names
    available = [c for c in strategy_names if c in df_all.columns]
    df = df_all[available]
    print(f"  Component returns: {df.shape[0]} days x {df.shape[1]} strategies")
    print(f"  Date range: {df.index[0].date()} -> {df.index[-1].date()}")
    return df


def load_fr_mean_daily() -> pd.Series:
    """Load daily mean annualized funding rate (same as K198)."""
    daily_series = []
    for sym in FR_SYMBOLS:
        for tag in ("730d", "1200d", "365d"):
            fpath = CACHE / f"bybit_fr_{sym}USDT_{tag}.parquet"
            if fpath.exists():
                df = pd.read_parquet(fpath)
                df["timestamp"] = pd.to_datetime(df["timestamp"]).dt.tz_localize(None)
                df = df.set_index("timestamp")
                daily = df["funding_rate"].resample("1D").mean()
                ann = daily * 3 * 365
                ann.name = sym
                daily_series.append(ann)
                break
    if not daily_series:
        return pd.Series(dtype=float, name="fr_mean_ann")
    panel = pd.concat(daily_series, axis=1)
    return panel.mean(axis=1).rename("fr_mean_ann")


def apply_fr_trigger(df: pd.DataFrame, fr_mean: pd.Series) -> pd.DataFrame:
    """Zero out FR_COMPONENTS when fr_mean < threshold."""
    df2 = df.copy()
    fr_aligned = fr_mean.reindex(df2.index, method="ffill")
    trigger_mask = fr_aligned < FR_THRESHOLD
    for comp in FR_COMPONENTS:
        if comp in df2.columns:
            df2.loc[trigger_mask, comp] = 0.0
    return df2


# ─────────────────────────────────────────────────────────────────────────────
# Feature and target engineering (same as K198)
# ─────────────────────────────────────────────────────────────────────────────

def build_features(df: pd.DataFrame, fr_mean: Optional[pd.Series],
                   win_short: int = 30, win_long: int = 90) -> pd.DataFrame:
    cols = list(df.columns)
    n_strats = len(cols)
    R = df.values
    n = len(R)
    feat_rows = []

    for t in range(win_long, n):
        row = {}
        slice_long = R[t - win_long:t]
        slice_short = R[t - win_short:t]

        if n_strats > 1:
            corr_mat = np.corrcoef(slice_short.T)
            np.fill_diagonal(corr_mat, 0.0)
        else:
            corr_mat = np.zeros((1, 1))

        for i, strat in enumerate(cols):
            prefix = f"{strat}__"
            row[f"{prefix}sh30"] = sharpe(slice_short[:, i])
            row[f"{prefix}sh90"] = sharpe(slice_long[:, i])
            row[f"{prefix}vol30"] = float(slice_short[:, i].std(ddof=1) * ANN)
            eq_s = np.cumprod(1.0 + slice_short[:, i])
            pk = np.maximum.accumulate(eq_s)
            row[f"{prefix}mdd30"] = float((eq_s / pk - 1.0).min())
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

    return pd.DataFrame(feat_rows, index=df.index[win_long:])


def build_targets(df: pd.DataFrame, horizon: int = 30) -> pd.DataFrame:
    cols = list(df.columns)
    R = df.values
    n = len(R)
    target_rows = []

    for t in range(n - horizon):
        fwd = R[t + 1: t + 1 + horizon]
        row = {}
        for i, strat in enumerate(cols):
            row[f"{strat}__fwd_sh"] = sharpe(fwd[:, i])
        target_rows.append(row)

    return pd.DataFrame(target_rows, index=df.index[:n - horizon])


# ─────────────────────────────────────────────────────────────────────────────
# Ridge walk-forward ML allocator (same methodology as K198)
# ─────────────────────────────────────────────────────────────────────────────

def ml_walk_forward(
    df: pd.DataFrame,
    feat_df: pd.DataFrame,
    target_df: pd.DataFrame,
    train_days: int = ML_TRAIN_DAYS,
    test_days: int = ML_TEST_DAYS,
    alpha: float = 1.0,
) -> Tuple[pd.DataFrame, pd.Series]:
    """Ridge regression walk-forward allocator (same as K198)."""
    cols = list(df.columns)
    n_strats = len(cols)

    common_idx = feat_df.index.intersection(target_df.index)
    feat_aligned = feat_df.loc[common_idx]
    target_aligned = target_df.loc[common_idx]

    feat_arr = feat_aligned.values
    target_arr = np.array([target_aligned[f"{c}__fwd_sh"].values for c in cols]).T
    date_idx = feat_aligned.index

    n = len(feat_arr)
    min_train = max(train_days, 45)

    wf_weights = []
    wf_pnl = []
    wf_dates = []

    step = 0
    while True:
        t_start = step * test_days + min_train
        if t_start >= n:
            break

        t_train_start = max(0, t_start - train_days)
        t_train_end = t_start
        t_test_end = min(t_start + test_days, n)

        if t_train_end - t_train_start < 20:
            step += 1
            continue

        X_train = feat_arr[t_train_start:t_train_end]
        Y_train = target_arr[t_train_start:t_train_end]
        X_test = feat_arr[t_start:t_test_end]
        test_dates_slice = date_idx[t_start:t_test_end]

        if len(X_train) < 20 or len(X_test) == 0:
            step += 1
            continue

        X_train = np.nan_to_num(X_train, nan=0.0, posinf=0.0, neginf=0.0)
        X_test = np.nan_to_num(X_test, nan=0.0, posinf=0.0, neginf=0.0)

        scaler = StandardScaler()
        X_train_s = scaler.fit_transform(X_train)
        X_test_s = scaler.transform(X_test)

        preds = np.zeros(n_strats)
        for i in range(n_strats):
            y = Y_train[:, i]
            if np.isnan(y).any() or np.std(y) < 1e-10:
                preds[i] = 0.0
                continue
            model = Ridge(alpha=alpha)
            model.fit(X_train_s, y)
            preds[i] = float(model.predict(X_test_s[:1])[0])

        pos_preds = np.maximum(preds, 0.0)
        if pos_preds.sum() < 1e-10:
            w = np.ones(n_strats) / n_strats
        else:
            w = pos_preds / pos_preds.sum()
        w = apply_all_caps(w, cols)

        test_rets = df.loc[test_dates_slice].values
        for d_i, d in enumerate(test_dates_slice):
            pnl = float(test_rets[d_i] @ w)
            wf_pnl.append(pnl)
            wf_dates.append(d)
            wf_weights.append(dict(zip(cols, w)))

        step += 1

    if not wf_pnl:
        return pd.DataFrame(), pd.Series(dtype=float)

    weights_df = pd.DataFrame(wf_weights, index=wf_dates)
    pnl_series = pd.Series(wf_pnl, index=wf_dates, name="K198_NoK116_pnl")
    return weights_df, pnl_series


# ─────────────────────────────────────────────────────────────────────────────
# Inverse-vol blend (same as K246a methodology)
# ─────────────────────────────────────────────────────────────────────────────

def inv_vol_blend(
    rets_list: List[np.ndarray],
    cap_idx: Optional[int] = None,
    cap_val: float = 0.20,
    roll: int = 30,
) -> Tuple[np.ndarray, np.ndarray]:
    """Inverse-vol weighted blend with optional component cap."""
    n_comp = len(rets_list)
    n_t = len(rets_list[0])
    blended = np.zeros(n_t)
    w_traj = np.zeros((n_t, n_comp))

    for i in range(n_t):
        start_w = max(0, i - roll)
        vols = []
        for r in rets_list:
            seg = r[start_w: i + 1]
            v = np.std(seg, ddof=1) if len(seg) >= 3 else 1e-6
            vols.append(max(v, 1e-9))

        ivols = [1.0 / v for v in vols]
        total = sum(ivols)
        w = np.array([iv / total for iv in ivols])

        if cap_idx is not None and w[cap_idx] > cap_val:
            w[cap_idx] = cap_val
            rest_ivols = [ivols[j] for j in range(n_comp) if j != cap_idx]
            rest_sum = sum(rest_ivols)
            if rest_sum > 0:
                for j in range(n_comp):
                    if j != cap_idx:
                        w[j] = (ivols[j] / rest_sum) * (1.0 - cap_val)

        w_traj[i] = w
        blended[i] = sum(w[j] * rets_list[j][i] for j in range(n_comp))

    return blended, w_traj


# ─────────────────────────────────────────────────────────────────────────────
# STEP 1: Load K198 original PnL (for K246a baseline reproduction)
# ─────────────────────────────────────────────────────────────────────────────
print("\n=== STEP 1: Load K198 original equity + K208 + K226 ===")

with open(BASE / "wave_k198_curves.json") as f:
    k198_raw = json.load(f)

dates_ml = k198_raw["dates_ml"]       # 448 date strings
eq198 = np.array(k198_raw["equity_ridge"])  # shape (448,)
print(f"K198: {len(dates_ml)} days  {dates_ml[0]} -> {dates_ml[-1]}")

# K208
with open(BASE / "wave_k208_curves.json") as f:
    k208_raw = json.load(f)

k208_daily: Dict[str, float] = {}
for ts_str, cpnl in zip(
    k208_raw["K208_filtered"]["timestamps"],
    k208_raw["K208_filtered"]["cumulative_pnl"],
):
    k208_daily[ts_str[:10]] = cpnl

k208_eq_values: List[float] = []
missing_k208 = 0
for d in dates_ml:
    if d in k208_daily:
        k208_eq_values.append(1.0 + k208_daily[d])
    else:
        missing_k208 += 1
        k208_eq_values.append(k208_eq_values[-1] if k208_eq_values else 1.0)
eq208 = np.array(k208_eq_values)
eq208 = eq208 / eq208[0]
print(f"K208: {len(eq208)} days aligned  missing={missing_k208}")

# K226
with open(BASE / "wave_k226_curves.json") as f:
    k226_raw = json.load(f)

k226_eq_daily: Dict[str, float] = {}
for d, eq in zip(k226_raw["dates"], k226_raw["strategy_equity"]):
    k226_eq_daily[d] = eq

k226_eq_values: List[float] = []
missing_k226 = 0
for d in dates_ml:
    if d in k226_eq_daily:
        k226_eq_values.append(k226_eq_daily[d])
    else:
        missing_k226 += 1
        k226_eq_values.append(k226_eq_values[-1] if k226_eq_values else 1.0)
eq226_aligned = np.array(k226_eq_values)
eq226 = eq226_aligned / eq226_aligned[0]
print(f"K226: {len(eq226)} days aligned  missing={missing_k226}")

n = len(dates_ml)

# Return series
ret198 = np.diff(eq198) / eq198[:-1]
ret208 = np.diff(eq208) / eq208[:-1]
ret226 = np.diff(eq226) / eq226[:-1]
ret_dates = dates_ml[1:]
n_ret = len(ret198)
print(f"Return series: {n_ret} days  ({ret_dates[0]} -> {ret_dates[-1]})")

# ─────────────────────────────────────────────────────────────────────────────
# STEP 2: K246a Baseline Reproduction
# ─────────────────────────────────────────────────────────────────────────────
print("\n=== STEP 2: Reproduce K246a (K198+K208+K226, K226 cap 20%) ===")

ret_k246a, w_k246a = inv_vol_blend([ret198, ret208, ret226], cap_idx=2, cap_val=0.20)
m_k246a = oos_metrics_arr(ret_k246a)
wf_k246a = wf_stats(ret_k246a, ret_dates)
avg_w_k246a = [round(float(w_k246a[:, j].mean()), 4) for j in range(3)]
print(f"  K246a repro: OOS Sh={m_k246a['oos_sharpe']:.4f}  MaxDD={m_k246a['oos_maxdd']:.6f}")
print(f"  WF mean={wf_k246a['wf_mean']:.4f}  WF min={wf_k246a['wf_min']:.4f}")
print(f"  Folds: {wf_k246a['fold_sharpes']}")
print(f"  Avg weights: K198={avg_w_k246a[0]:.4f}  K208={avg_w_k246a[1]:.4f}  K226={avg_w_k246a[2]:.4f}")

# ─────────────────────────────────────────────────────────────────────────────
# STEP 3: Build K198_NoK116 sub-component data
# ─────────────────────────────────────────────────────────────────────────────
print("\n=== STEP 3: Build K198_NoK116 sub-component data ===")
print(f"  Using {len(STRATEGY_NAMES_NO_K116)} subs: {STRATEGY_NAMES_NO_K116}")

df_no_k116 = load_component_returns(STRATEGY_NAMES_NO_K116)
cols_no_k116 = list(df_no_k116.columns)

# Load FR and apply trigger
print("\n  Loading FR regime indicator...")
fr_mean = load_fr_mean_daily()
if len(fr_mean) > 0:
    print(f"  FR available: {fr_mean.index[0].date()} -> {fr_mean.index[-1].date()}")
    df_triggered = apply_fr_trigger(df_no_k116, fr_mean)
    n_trigger = int((fr_mean.reindex(df_no_k116.index, method="ffill") < FR_THRESHOLD).sum())
    print(f"  FR trigger fires {n_trigger}/{len(df_no_k116)} days")
else:
    print("  WARNING: FR data not available")
    df_triggered = df_no_k116.copy()
    fr_mean = None

# ─────────────────────────────────────────────────────────────────────────────
# STEP 4: Build features + targets for K198_NoK116
# ─────────────────────────────────────────────────────────────────────────────
print("\n=== STEP 4: Build features + targets ===")
feat_df = build_features(df_triggered, fr_mean)
target_df = build_targets(df_triggered, horizon=ML_TEST_DAYS)
print(f"  Features: {feat_df.shape[0]} rows x {feat_df.shape[1]} cols")
print(f"  Targets:  {target_df.shape[0]} rows x {target_df.shape[1]} cols")

# ─────────────────────────────────────────────────────────────────────────────
# STEP 5: Ridge walk-forward for K198_NoK116
# ─────────────────────────────────────────────────────────────────────────────
print("\n=== STEP 5: Ridge walk-forward (K198_NoK116) ===")
weights_nok116, pnl_nok116 = ml_walk_forward(
    df_triggered, feat_df, target_df,
    train_days=ML_TRAIN_DAYS, test_days=ML_TEST_DAYS, alpha=1.0,
)

if len(pnl_nok116) == 0:
    raise RuntimeError("K198_NoK116 walk-forward returned empty PnL — check data.")

pnl_nok116_arr = pnl_nok116.values
pnl_dates_nok116 = [str(d.date()) for d in pnl_nok116.index]
print(f"  K198_NoK116 ML PnL: {len(pnl_nok116)} days  "
      f"{pnl_dates_nok116[0]} -> {pnl_dates_nok116[-1]}")

# ─────────────────────────────────────────────────────────────────────────────
# STEP 6: K198_NoK116 standalone metrics
# ─────────────────────────────────────────────────────────────────────────────
print("\n=== STEP 6: K198_NoK116 Standalone Metrics ===")

m_nok116_standalone = oos_metrics_arr(pnl_nok116_arr)
wf_nok116_standalone = wf_stats(pnl_nok116_arr, pnl_dates_nok116)

print(f"  Full window Sh  : {sharpe(pnl_nok116_arr):.4f}")
print(f"  OOS Sh (30%)    : {m_nok116_standalone['oos_sharpe']:.4f}")
print(f"  OOS MaxDD       : {m_nok116_standalone['oos_maxdd']:.6f}")
print(f"  WF mean         : {wf_nok116_standalone['wf_mean']:.4f}")
print(f"  WF min          : {wf_nok116_standalone['wf_min']:.4f}")
print(f"  WF folds        : {wf_nok116_standalone['fold_sharpes']}")

# Compare vs K198 original standalone
with open(BASE / "wave_k198_ml_allocator.json") as f:
    k198_meta = json.load(f)

k198_standalone_oos = k198_meta["three_way_comparison"]["K198_ridge_ML"]["oos_sharpe"]
k198_standalone_wf_min = k198_meta["three_way_comparison"]["K198_ridge_ML"]["wf_min"]
k198_standalone_folds = k198_meta["three_way_comparison"]["K198_ridge_ML"]["wf_fold_sharpes"]

print(f"\n  vs K198 original (standalone):")
print(f"    K198:        OOS Sh={k198_standalone_oos:.4f}  WF min={k198_standalone_wf_min:.4f}  folds={k198_standalone_folds}")
print(f"    K198_NoK116: OOS Sh={m_nok116_standalone['oos_sharpe']:.4f}  "
      f"WF min={wf_nok116_standalone['wf_min']:.4f}  folds={wf_nok116_standalone['fold_sharpes']}")
delta_standalone_oos = m_nok116_standalone['oos_sharpe'] - k198_standalone_oos
delta_standalone_wfmin = wf_nok116_standalone['wf_min'] - k198_standalone_wf_min
print(f"    Delta: OOS Sh {delta_standalone_oos:+.4f}  WF min {delta_standalone_wfmin:+.4f}")

# ─────────────────────────────────────────────────────────────────────────────
# STEP 7: Align K198_NoK116 to K246a ML window dates
# ─────────────────────────────────────────────────────────────────────────────
print("\n=== STEP 7: Align K198_NoK116 to K246a ML window ===")

# Build daily dict from K198_NoK116 ML PnL
nok116_pnl_by_date: Dict[str, float] = {}
for d, pnl_val in zip(pnl_dates_nok116, pnl_nok116_arr):
    nok116_pnl_by_date[d] = pnl_val

# Align to K246a dates_ml (same as K198 ML window)
# Start from second date (returns) aligned with ret_dates
nok116_eq_values = [1.0]  # equity starts at 1.0
missing_nok116 = 0
for d in ret_dates:
    if d in nok116_pnl_by_date:
        pnl_val = nok116_pnl_by_date[d]
        nok116_eq_values.append(nok116_eq_values[-1] * (1.0 + pnl_val))
    else:
        missing_nok116 += 1
        nok116_eq_values.append(nok116_eq_values[-1])  # flat day

# Convert equity to returns
nok116_eq_arr = np.array(nok116_eq_values)
ret_nok116 = np.diff(nok116_eq_arr) / nok116_eq_arr[:-1]
print(f"  K198_NoK116 aligned: {len(ret_nok116)} days  missing={missing_nok116}")
print(f"  K198_NoK116 full window Sh: {sharpe(ret_nok116):.4f}")

# ─────────────────────────────────────────────────────────────────────────────
# STEP 8: K255_a = K198_NoK116 + K208 + K226 (inv-vol + K226 cap 20%)
# ─────────────────────────────────────────────────────────────────────────────
print("\n=== STEP 8: K255_a = K198_NoK116 + K208 + K226 ===")

ret_k255a, w_k255a = inv_vol_blend([ret_nok116, ret208, ret226], cap_idx=2, cap_val=0.20)
m_k255a = oos_metrics_arr(ret_k255a)
wf_k255a = wf_stats(ret_k255a, ret_dates)
avg_w_k255a = [round(float(w_k255a[:, j].mean()), 4) for j in range(3)]

print(f"  OOS Sh : {m_k255a['oos_sharpe']:.4f}")
print(f"  MaxDD  : {m_k255a['oos_maxdd']:.6f}")
print(f"  WF mean: {wf_k255a['wf_mean']:.4f}")
print(f"  WF min : {wf_k255a['wf_min']:.4f}")
print(f"  Folds  : {wf_k255a['fold_sharpes']}")
print(f"  Avg weights: K198_NoK116={avg_w_k255a[0]:.4f}  K208={avg_w_k255a[1]:.4f}  K226={avg_w_k255a[2]:.4f}")

# ─────────────────────────────────────────────────────────────────────────────
# STEP 9: Acceptance gate evaluation
# ─────────────────────────────────────────────────────────────────────────────
print("\n=== STEP 9: Acceptance Gates ===")

fold2_k246a = K246A_FOLDS[1]  # 8.9347
fold2_k255a = wf_k255a["fold_sharpes"][1]
fold2_improvement = fold2_k255a - fold2_k246a

g1 = m_k255a["oos_sharpe"] >= GATE_OOS_SH
g2 = wf_k255a["wf_min"] >= GATE_WF_MIN
g3 = fold2_improvement >= GATE_FOLD2_IMPROVEMENT
g4 = m_k255a["oos_maxdd"] >= GATE_MAXDD  # maxdd must not worsen (less negative)

all_pass = g1 and g2 and g3 and g4

print(f"  Gate 1: OOS Sh >= {GATE_OOS_SH}  "
      f"  K255_a={m_k255a['oos_sharpe']:.4f}  -> {'PASS' if g1 else 'FAIL'}")
print(f"  Gate 2: WF min >= {GATE_WF_MIN}  "
      f"  K255_a={wf_k255a['wf_min']:.4f}   -> {'PASS' if g2 else 'FAIL'}")
print(f"  Gate 3: Fold2 improvement >= +{GATE_FOLD2_IMPROVEMENT}  "
      f"  K246a fold2={fold2_k246a:.4f}  K255_a fold2={fold2_k255a:.4f}  "
      f"delta={fold2_improvement:+.4f}  -> {'PASS' if g3 else 'FAIL'}")
print(f"  Gate 4: MaxDD <= {GATE_MAXDD}  "
      f"  K255_a={m_k255a['oos_maxdd']:.6f}  -> {'PASS' if g4 else 'FAIL'}")
print(f"  ALL PASS: {all_pass}")

# ─────────────────────────────────────────────────────────────────────────────
# STEP 10: Final comparison table
# ─────────────────────────────────────────────────────────────────────────────
print("\n=== STEP 10: Final Comparison ===")
print(f"{'Version':<25} {'OOS Sh':>8} {'MaxDD':>10} {'WF mean':>8} {'WF min':>8} {'Fold2':>8}")
print("-" * 75)
print(f"  {'K246a v6.9 (reported)':<23} {K246A_OOS_SH:>8.4f} {K246A_MAXDD:>10.6f} "
      f"{K246A_WF_MEAN:>8.4f} {K246A_WF_MIN:>8.4f} {K246A_FOLD2:>8.4f}")
print(f"  {'K246a (repro)':<23} {m_k246a['oos_sharpe']:>8.4f} {m_k246a['oos_maxdd']:>10.6f} "
      f"{wf_k246a['wf_mean']:>8.4f} {wf_k246a['wf_min']:>8.4f} {wf_k246a['fold_sharpes'][1]:>8.4f}")
print(f"  {'K255_a (no K116)':<23} {m_k255a['oos_sharpe']:>8.4f} {m_k255a['oos_maxdd']:>10.6f} "
      f"{wf_k255a['wf_mean']:>8.4f} {wf_k255a['wf_min']:>8.4f} {fold2_k255a:>8.4f}")
print()
delta_oos = m_k255a["oos_sharpe"] - K246A_OOS_SH
delta_wfmin = wf_k255a["wf_min"] - K246A_WF_MIN
delta_maxdd = m_k255a["oos_maxdd"] - K246A_MAXDD
print(f"  Delta K255_a vs K246a reported: OOS Sh {delta_oos:+.4f}  WF min {delta_wfmin:+.4f}  "
      f"Fold2 {fold2_improvement:+.4f}  MaxDD {delta_maxdd:+.6f}")

# ─────────────────────────────────────────────────────────────────────────────
# STEP 11: Verdict on K198 fine-tunability
# ─────────────────────────────────────────────────────────────────────────────
print("\n=== STEP 11: Verdict on K198 Fine-Tunability ===")

if all_pass:
    verdict = "ACCEPT"
    verdict_summary = (
        f"K255_a (K198_NoK116 + K208 + K226) passes all gates. "
        f"OOS Sh {m_k255a['oos_sharpe']:.4f} >= {GATE_OOS_SH}, "
        f"WF min {wf_k255a['wf_min']:.4f} >= {GATE_WF_MIN}, "
        f"Fold2 delta {fold2_improvement:+.4f} >= +{GATE_FOLD2_IMPROVEMENT}, "
        f"MaxDD {m_k255a['oos_maxdd']:.6f} >= {GATE_MAXDD}. "
        "Promote to v6.9.1 fine-tune."
    )
    k198_finetune_verdict = (
        "K198 IS fine-tunable by removing K116. "
        "K116 was a net drag in fold 2 (marginal contribution -1.22) "
        "AND its removal improves the ensemble without degrading other folds."
    )
else:
    failed_gates = []
    if not g1:
        failed_gates.append(f"OOS Sh {m_k255a['oos_sharpe']:.4f} < {GATE_OOS_SH}")
    if not g2:
        failed_gates.append(f"WF min {wf_k255a['wf_min']:.4f} < {GATE_WF_MIN}")
    if not g3:
        failed_gates.append(f"Fold2 delta {fold2_improvement:+.4f} < +{GATE_FOLD2_IMPROVEMENT}")
    if not g4:
        failed_gates.append(f"MaxDD {m_k255a['oos_maxdd']:.6f} < {GATE_MAXDD}")

    verdict = "REJECT"
    verdict_summary = (
        f"K255_a fails gates: {'; '.join(failed_gates)}. "
        "K246a v6.9 remains production."
    )
    k198_finetune_verdict = (
        "K198 is NOT fine-tunable by removing K116. "
        "K116's fold-2 marginal drag (-1.22) does not outweigh its contributions "
        "in other folds (fold3: +1.91, fold1: -0.25). "
        "K198 is a genuine irreducible ensemble — K252 GENUINE_ENSEMBLE verdict confirmed."
    )

print(f"\n  VERDICT: {verdict}")
print(f"  {verdict_summary}")
print(f"\n  K198 Fine-Tunability: {k198_finetune_verdict}")

# ─────────────────────────────────────────────────────────────────────────────
# Save JSON outputs
# ─────────────────────────────────────────────────────────────────────────────
runtime = round(time.time() - t0, 1)

output = {
    "wave": "K255",
    "objective": "Remove K116 from K198 ensemble (fold2 marginal -1.22) and test vs K246a",
    "as_of": datetime.now(timezone.utc).isoformat(),
    "runtime_s": runtime,

    "config": {
        "k198_original_subs": STRATEGY_NAMES_FULL,
        "k198_no_k116_subs": STRATEGY_NAMES_NO_K116,
        "ml_train_days": ML_TRAIN_DAYS,
        "ml_test_days": ML_TEST_DAYS,
        "ridge_alpha": 1.0,
        "k226_cap": 0.20,
        "n_days_ml_window": n,
        "n_returns": n_ret,
        "missing_k208": missing_k208,
        "missing_k226": missing_k226,
        "missing_nok116_align": missing_nok116,
    },

    "k246a_reference": {
        "oos_sharpe": K246A_OOS_SH,
        "wf_mean": K246A_WF_MEAN,
        "wf_min": K246A_WF_MIN,
        "maxdd": K246A_MAXDD,
        "fold_sharpes": K246A_FOLDS,
        "fold2": K246A_FOLD2,
        "components": ["K198", "K208", "K226"],
    },

    "k246a_reproduction": {
        "oos_sharpe": m_k246a["oos_sharpe"],
        "oos_maxdd": m_k246a["oos_maxdd"],
        "wf_mean": wf_k246a["wf_mean"],
        "wf_min": wf_k246a["wf_min"],
        "fold_sharpes": wf_k246a["fold_sharpes"],
        "avg_weights_k198_k208_k226": avg_w_k246a,
    },

    "k198_no_k116_standalone": {
        "description": "K198_NoK116 Ridge ML allocator on 9-sub ensemble",
        "n_days": len(pnl_nok116),
        "date_range": [pnl_dates_nok116[0], pnl_dates_nok116[-1]],
        "full_window_sharpe": round(sharpe(pnl_nok116_arr), 4),
        "oos_sharpe": m_nok116_standalone["oos_sharpe"],
        "oos_maxdd": m_nok116_standalone["oos_maxdd"],
        "wf_mean": wf_nok116_standalone["wf_mean"],
        "wf_min": wf_nok116_standalone["wf_min"],
        "fold_sharpes": wf_nok116_standalone["fold_sharpes"],
        "vs_k198_original": {
            "k198_oos_sh": k198_standalone_oos,
            "k198_wf_min": k198_standalone_wf_min,
            "k198_folds": k198_standalone_folds,
            "delta_oos_sh": round(delta_standalone_oos, 4),
            "delta_wf_min": round(delta_standalone_wfmin, 4),
        },
    },

    "k255_a": {
        "description": "K198_NoK116 + K208 + K226, inv-vol + K226 cap 20%",
        "oos_sharpe": m_k255a["oos_sharpe"],
        "oos_maxdd": m_k255a["oos_maxdd"],
        "oos_ann_ret": m_k255a.get("oos_ann_ret", None),
        "wf_mean": wf_k255a["wf_mean"],
        "wf_min": wf_k255a["wf_min"],
        "fold_sharpes": wf_k255a["fold_sharpes"],
        "fold2_sharpe": fold2_k255a,
        "avg_weights_nok116_k208_k226": avg_w_k255a,
        "delta_vs_k246a": {
            "oos_sharpe": round(delta_oos, 4),
            "wf_min": round(delta_wfmin, 4),
            "fold2": round(fold2_improvement, 4),
            "maxdd": round(delta_maxdd, 6),
        },
    },

    "acceptance_gates": {
        "gate1_oos_sh": {"required": GATE_OOS_SH, "actual": m_k255a["oos_sharpe"], "pass": g1},
        "gate2_wf_min": {"required": GATE_WF_MIN, "actual": wf_k255a["wf_min"], "pass": g2},
        "gate3_fold2_improvement": {
            "required": GATE_FOLD2_IMPROVEMENT,
            "actual": round(fold2_improvement, 4),
            "k246a_fold2": fold2_k246a,
            "k255a_fold2": fold2_k255a,
            "pass": g3,
        },
        "gate4_maxdd": {"required": GATE_MAXDD, "actual": m_k255a["oos_maxdd"], "pass": g4},
        "all_pass": all_pass,
    },

    "verdict": {
        "decision": verdict,
        "summary": verdict_summary,
        "k198_fine_tunability": k198_finetune_verdict,
        "production_label": "v6.9.1" if all_pass else "v6.9 (unchanged)",
        "k116_marginal_contribution_fold2": -1.2186,
        "k116_marginal_contribution_fold3": 1.9131,
        "k116_positive_folds": 1,
        "conclusion": (
            "K116 has only 1 positive-marginal fold (fold3=+1.91) vs 3 negative/neutral. "
            "Fold2 drag of -1.22 is the strongest signal. "
            "Fine-tune verdict depends on ensemble test outcome above."
        ),
    },
}

json_path = BASE / "wave_k255_k198_no_k116.json"
json_path.write_text(json.dumps(output, indent=2, default=str))
print(f"\nWrote {json_path}  ({json_path.stat().st_size:,} bytes)")

# ─────────────────────────────────────────────────────────────────────────────
# Equity curves JSON
# ─────────────────────────────────────────────────────────────────────────────
curves_out = {
    "dates": [dates_ml[0]] + list(ret_dates),
    "K246a_repro": equity_curve(ret_k246a),
    "K255_a": equity_curve(ret_k255a),
    "K198_original": equity_curve(ret198),
    "K198_NoK116_aligned": equity_curve(ret_nok116),
    "K208_ref": equity_curve(ret208),
    "K226_ref": equity_curve(ret226),
}

curves_path = BASE / "wave_k255_curves.json"
curves_path.write_text(json.dumps(curves_out, default=str))
print(f"Wrote {curves_path}  ({curves_path.stat().st_size:,} bytes)")

# ─────────────────────────────────────────────────────────────────────────────
# Markdown report
# ─────────────────────────────────────────────────────────────────────────────
md_lines = [
    "# Wave K255 — K198_NoK116: Fine-Tune K198 by Removing K116",
    f"*Generated: {output['as_of']}  |  Runtime: {runtime}s*",
    "",
    "## Executive Summary",
    "",
    f"**VERDICT: {verdict} — {verdict_summary}**",
    "",
    f"**K198 Fine-Tunability: {k198_finetune_verdict}**",
    "",
    "## 1. Background: Why K116?",
    "",
    "K252 decomposed K198's 10 sub-components and computed marginal contributions per fold.",
    "K116 showed the worst fold-2 marginal contribution: **-1.22** (K147 best at +1.95).",
    "",
    "| Sub | Fold1 MC | Fold2 MC | Fold3 MC | Fold4 MC | +ve Folds |",
    "|-----|----------|----------|----------|----------|-----------|",
    "| K116 | -0.25 | **-1.22** | +1.91 | -0.26 | 1 |",
    "| K147 | +1.58 | **+1.95** | +0.34 | +0.38 | 4 |",
    "",
    "K116 is negative in 3 of 4 folds; only fold3 shows benefit.",
    "",
    "## 2. K198_NoK116 Standalone Metrics",
    "",
    "Ridge ML allocator with 9 subs (K116 excluded), same caps and walk-forward methodology:",
    "",
    "| Metric | K198 (original) | K198_NoK116 | Delta |",
    "|--------|-----------------|-------------|-------|",
    f"| OOS Sh | {k198_standalone_oos:.4f} | {m_nok116_standalone['oos_sharpe']:.4f} | {delta_standalone_oos:+.4f} |",
    f"| WF min | {k198_standalone_wf_min:.4f} | {wf_nok116_standalone['wf_min']:.4f} | {delta_standalone_wfmin:+.4f} |",
    f"| WF folds | {k198_standalone_folds} | {wf_nok116_standalone['fold_sharpes']} | — |",
    "",
    "## 3. K255_a vs K246a Comparison",
    "",
    "K255_a = K198_NoK116 + K208 + K226 (inv-vol + K226 cap 20%, K246a methodology)",
    "",
    "| Version | OOS Sh | MaxDD | WF Mean | WF Min | Fold2 |",
    "|---------|--------|-------|---------|--------|-------|",
    f"| K246a v6.9 (reported) | {K246A_OOS_SH:.4f} | {K246A_MAXDD:.6f} | {K246A_WF_MEAN:.4f} | {K246A_WF_MIN:.4f} | {K246A_FOLD2:.4f} |",
    f"| K246a (repro) | {m_k246a['oos_sharpe']:.4f} | {m_k246a['oos_maxdd']:.6f} | {wf_k246a['wf_mean']:.4f} | {wf_k246a['wf_min']:.4f} | {wf_k246a['fold_sharpes'][1]:.4f} |",
    f"| K255_a (no K116) | {m_k255a['oos_sharpe']:.4f} | {m_k255a['oos_maxdd']:.6f} | {wf_k255a['wf_mean']:.4f} | {wf_k255a['wf_min']:.4f} | {fold2_k255a:.4f} |",
    f"| **Delta** | **{delta_oos:+.4f}** | **{delta_maxdd:+.6f}** | — | **{delta_wfmin:+.4f}** | **{fold2_improvement:+.4f}** |",
    "",
    "## 4. Per-Fold Breakdown (K255_a)",
    "",
    "| Fold | Period | K255_a Sh | K246a Sh | Delta |",
    "|------|--------|-----------|----------|-------|",
]
for i, (fsh_255, fsh_246) in enumerate(zip(wf_k255a["fold_sharpes"], K246A_FOLDS)):
    d = fsh_255 - fsh_246
    fd = wf_k255a["fold_details"][i]
    md_lines.append(
        f"| {i+1} | {fd['start_date']}..{fd['end_date']} | "
        f"{fsh_255:.4f} | {fsh_246:.4f} | {d:+.4f} |"
    )
md_lines += [
    "",
    "## 5. Acceptance Gates",
    "",
    f"| Gate | Criterion | K255_a | Result |",
    f"|------|-----------|--------|--------|",
    f"| G1 | OOS Sh >= {GATE_OOS_SH} | {m_k255a['oos_sharpe']:.4f} | {'PASS' if g1 else 'FAIL'} |",
    f"| G2 | WF min >= {GATE_WF_MIN} | {wf_k255a['wf_min']:.4f} | {'PASS' if g2 else 'FAIL'} |",
    f"| G3 | Fold2 delta >= +{GATE_FOLD2_IMPROVEMENT} | {fold2_improvement:+.4f} | {'PASS' if g3 else 'FAIL'} |",
    f"| G4 | MaxDD <= {GATE_MAXDD} | {m_k255a['oos_maxdd']:.6f} | {'PASS' if g4 else 'FAIL'} |",
    f"| **ALL** | — | — | **{'PASS' if all_pass else 'FAIL'}** |",
    "",
    "## 6. Verdict on K198 Fine-Tunability",
    "",
    f"**{verdict}**",
    "",
    k198_finetune_verdict,
    "",
    "### K116 Profile Summary",
    "- Fold1 MC: -0.25 (negative)",
    "- Fold2 MC: -1.22 (worst of all 10 subs)",
    "- Fold3 MC: +1.91 (only positive fold)",
    "- Fold4 MC: -0.26 (negative)",
    "- Positive-marginal folds: 1/4",
    "",
    "### Implications",
    f"- K252 verdict: GENUINE_ENSEMBLE confirmed" + (" — K116 removal does not improve ensemble" if not all_pass else " but K116 removal still improves"),
    f"- {'K198 is irreducible: all 10 subs contribute net positive value across folds.' if not all_pass else 'K116 is a net drag; 9-sub ensemble is superior.'}",
    f"- {'K246a v6.9 remains PRODUCTION unchanged.' if not all_pass else 'K255_a promoted to v6.9.1.'}",
    "",
    "---",
    f"*Wave K255 | crypto-lab | {output['as_of']}*",
]

md_path = BASE / "wave_k255_k198_no_k116.md"
md_path.write_text("\n".join(md_lines))
print(f"Wrote {md_path}  ({md_path.stat().st_size:,} bytes)")

# ─────────────────────────────────────────────────────────────────────────────
print(f"\n{'=' * 70}")
print(f"K255 COMPLETE — Runtime {runtime}s")
print(f"VERDICT: {verdict}")
print(f"K255_a: OOS Sh={m_k255a['oos_sharpe']:.4f}  WF min={wf_k255a['wf_min']:.4f}  "
      f"Fold2={fold2_k255a:.4f}  MaxDD={m_k255a['oos_maxdd']:.6f}")
print(f"vs K246a: OOS Sh {delta_oos:+.4f}  WF min {delta_wfmin:+.4f}  "
      f"Fold2 {fold2_improvement:+.4f}")
print(f"{'=' * 70}")

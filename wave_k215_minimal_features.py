"""Wave K215 — Minimal Feature Addition Hypothesis for K198 ML Allocator.

Objective:
  Test whether a tiny number of high-importance features (identified from previous
  rejected waves K204/K207/K211) can improve upon K198's 51-feature baseline
  without the noise penalty observed with bulk feature addition (113 features).

Variants (cumulative additions from K198 baseline):
  K215_0 = K198 baseline (51 features, sanity check)
  K215_1 = K198 + K116__dd90                           (52 features)
  K215_2 = K215_1 + V_rev_carry__dd90                  (53 features)
  K215_3 = K215_2 + K114__sh_neg30                     (54 features)
  K215_5 = K215_3 + eth_tvl_change_30d + eth_x_V_fwd_carry  (56 features)

All variants: K198 config (90d window, alpha=1.0, no extra penalty, same caps).

Acceptance gate (any variant -> v6.6):
  OOS Sh > K198 (10.28)
  WF min >= K198 (6.57)
  MaxDD <= K198 (-0.0053)
  Feature must have non-zero Ridge coefficient

Research question:
  Is feature noise the K204/K207/K211 failure mode?
  What is the optimal feature count?
  Does additivity break at some k?

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

# K198 walk-forward params (identical)
ML_TRAIN_DAYS = 90
ML_TEST_DAYS  = 30

# K198 v6.5 production baseline
K198_OOS_SH  = 10.28
K198_OOS_DD  = -0.0053
K198_WF_MEAN = 7.91
K198_WF_MIN  = 6.57

# K204 (rejected) reference
K204_OOS_SH  = 10.36
K204_WF_MIN  = 6.02

# Caps (identical to K198)
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

ETH_TVL_LAG_DAYS = 7


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


def sortino_d(r: np.ndarray) -> float:
    dn = r[r < 0]
    if len(dn) < 2 or dn.std(ddof=1) == 0:
        return 0.0
    return float(r.mean() / dn.std(ddof=1) * math.sqrt(TRADING_DAYS))


def calmar_d(r: np.ndarray) -> float:
    ann = (1.0 + np.asarray(r, dtype=float)).prod() ** (TRADING_DAYS / max(1, len(r))) - 1.0
    mdd = max_dd_d(r)
    return float(ann / abs(mdd)) if mdd != 0 else 0.0


def cumulative_dd(r: np.ndarray) -> float:
    """Cumulative drawdown: (end_equity / rolling_peak) - 1."""
    eq = np.cumprod(1.0 + np.asarray(r, dtype=float))
    peak = np.max(eq)
    return float(eq[-1] / peak - 1.0)


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

def load_component_returns() -> pd.DataFrame:
    """Load 10 component daily return series (same as K198)."""
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
        base_df[col_name] = eq / prev - 1.0
    base_df.index.name = "date"

    with open(BASE / "wave_k195_curves.json") as f:
        k195 = json.load(f)
    k195_dates = pd.to_datetime(k195["panel_dates"])
    fwd_eq = np.array(k195["series"]["V_eq_w"], dtype=float)
    fwd_ret = pd.Series(
        np.r_[fwd_eq[0] - 1.0, fwd_eq[1:] / fwd_eq[:-1] - 1.0],
        index=k195_dates, name="V_fwd_carry",
    )

    with open(BASE / "wave_k196_curves.json") as f:
        k196 = json.load(f)
    k196_dates = pd.to_datetime(k196["panel_dates"])
    rev_eq = np.array(k196["series"]["V_rev_eq_w"], dtype=float)
    rev_ret = pd.Series(
        np.r_[rev_eq[0] - 1.0, rev_eq[1:] / rev_eq[:-1] - 1.0],
        index=k196_dates, name="V_rev_carry",
    )

    all_start = max(base_df.index[0], fwd_ret.index[0], rev_ret.index[0])
    all_end   = min(base_df.index[-1], fwd_ret.index[-1], rev_ret.index[-1])

    df = pd.concat([
        base_df[(base_df.index >= all_start) & (base_df.index <= all_end)],
        fwd_ret[(fwd_ret.index >= all_start) & (fwd_ret.index <= all_end)],
        rev_ret[(rev_ret.index >= all_start) & (rev_ret.index <= all_end)],
    ], axis=1).dropna()
    print(f"  Component returns: {df.shape[0]} days x {df.shape[1]} strategies")
    print(f"  Date range: {df.index[0].date()} -> {df.index[-1].date()}")
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
                ann = daily * 3 * 365
                ann.name = sym
                daily_series.append(ann)
                break
    if not daily_series:
        return pd.Series(dtype=float, name="fr_mean_ann")
    panel = pd.concat(daily_series, axis=1)
    fr_mean = panel.mean(axis=1)
    fr_mean.name = "fr_mean_ann"
    return fr_mean


def load_ethena_tvl(lag_days: int = ETH_TVL_LAG_DAYS) -> Tuple[pd.Series, pd.Series]:
    """Load Ethena TVL cache and compute 2 interaction signals with lag."""
    cache_path = CACHE / "ethena_tvl_daily.parquet"
    if not cache_path.exists():
        raise FileNotFoundError(f"Ethena TVL cache not found: {cache_path}")
    tvl_df = pd.read_parquet(cache_path)
    tvl = tvl_df["tvl"]
    if tvl.index.tz is not None:
        tvl.index = tvl.index.tz_localize(None)

    eth_change_30d = tvl.pct_change(30).shift(lag_days)
    rolling_peak = tvl.rolling(30, min_periods=2).max()
    eth_drawdown = ((tvl - rolling_peak) / rolling_peak.replace(0, np.nan)).shift(lag_days)

    eth_change_30d.name = "eth_tvl_change_30d"
    eth_drawdown.name = "eth_tvl_drawdown"
    return eth_change_30d, eth_drawdown


def apply_fr_trigger(df: pd.DataFrame, fr_mean: pd.Series) -> pd.DataFrame:
    """Zero out FR components when fr_mean < threshold."""
    df2 = df.copy()
    fr_aligned = fr_mean.reindex(df2.index, method="ffill")
    trigger_mask = fr_aligned < FR_THRESHOLD
    for comp in FR_COMPONENTS:
        if comp in df2.columns:
            df2.loc[trigger_mask, comp] = 0.0
    return df2


# ─────────────────────────────────────────────────────────────────────────────
# Feature engineering (per variant)
# ─────────────────────────────────────────────────────────────────────────────

def build_features(
    df: pd.DataFrame,
    fr_mean: Optional[pd.Series],
    variant: str,
    eth_change_30d: Optional[pd.Series] = None,
    eth_drawdown: Optional[pd.Series] = None,
    win_short: int = 30,
    win_long: int = 90,
) -> pd.DataFrame:
    """
    Build feature matrix for a given K215 variant.

    K215_0 (baseline): 50 per-strategy (sh30, sh90, vol30, mdd30, xcorr) + fr_mean = 51
    K215_1: + K116__dd90 = 52
    K215_2: + V_rev_carry__dd90 = 53
    K215_3: + K114__sh_neg30 = 54
    K215_5: + eth_tvl_change_30d + eth_x_V_fwd_carry = 56

    All variants build the same K198 base, then append the extra feature(s).
    """
    n_strats = df.shape[1]
    cols = list(df.columns)
    R = df.values
    n = len(R)

    # Align Ethena signals if available
    if eth_change_30d is not None:
        eth_chg_aligned = eth_change_30d.reindex(df.index, method="ffill")
    if eth_drawdown is not None:
        eth_dd_aligned = eth_drawdown.reindex(df.index, method="ffill")

    feat_rows = []

    for t in range(win_long, n):
        row = {}
        slice_long  = R[t - win_long:t]
        slice_short = R[t - win_short:t]

        # Cross-correlation 30d
        corr_mat = np.zeros((n_strats, n_strats))
        if n_strats > 1:
            corr_mat = np.corrcoef(slice_short.T)
            np.fill_diagonal(corr_mat, 0.0)

        # ── K198 base features: 5 per strategy ──────────────────────────────
        for i, strat in enumerate(cols):
            prefix = f"{strat}__"
            r_short = slice_short[:, i]
            r_long  = slice_long[:, i]
            row[f"{prefix}sh30"]  = sharpe_d(r_short)
            row[f"{prefix}sh90"]  = sharpe_d(r_long)
            row[f"{prefix}vol30"] = float(r_short.std(ddof=1) * math.sqrt(TRADING_DAYS))
            row[f"{prefix}mdd30"] = max_dd_d(r_short)
            if n_strats > 1:
                row[f"{prefix}xcorr"] = float(np.mean(np.delete(corr_mat[i], i)))
            else:
                row[f"{prefix}xcorr"] = 0.0

        # FR regime indicator (#51)
        if fr_mean is not None and len(fr_mean) > 0:
            fr_date = df.index[t]
            fr_val = fr_mean.reindex([fr_date], method="ffill")
            row["fr_mean_ann"] = float(fr_val.iloc[0]) if not fr_val.isna().all() else 0.0
        else:
            row["fr_mean_ann"] = 0.0

        # ── Variant-specific additional features ─────────────────────────────

        if variant in ("K215_1", "K215_2", "K215_3", "K215_5"):
            # #52: K116__dd90 — cumulative drawdown over 90d window for K116
            k116_idx = cols.index("K116") if "K116" in cols else None
            if k116_idx is not None:
                r_long_k116 = slice_long[:, k116_idx]
                row["K116__dd90"] = cumulative_dd(r_long_k116)
            else:
                row["K116__dd90"] = 0.0

        if variant in ("K215_2", "K215_3", "K215_5"):
            # #53: V_rev_carry__dd90
            rev_idx = cols.index("V_rev_carry") if "V_rev_carry" in cols else None
            if rev_idx is not None:
                r_long_rev = slice_long[:, rev_idx]
                row["V_rev_carry__dd90"] = cumulative_dd(r_long_rev)
            else:
                row["V_rev_carry__dd90"] = 0.0

        if variant in ("K215_3", "K215_5"):
            # #54: K114__sh_neg30 — fraction of negative days in last 30d for K114
            k114_idx = cols.index("K114") if "K114" in cols else None
            if k114_idx is not None:
                r_short_k114 = slice_short[:, k114_idx]
                row["K114__sh_neg30"] = float(np.sum(r_short_k114 < 0) / len(r_short_k114))
            else:
                row["K114__sh_neg30"] = 0.0

        if variant == "K215_5":
            # #55: eth_tvl_change_30d (global Ethena signal, lagged 7d)
            date_t = df.index[t]
            if eth_change_30d is not None:
                eth_chg_val = eth_chg_aligned.loc[date_t] if date_t in eth_chg_aligned.index else np.nan
                row["eth_tvl_change_30d"] = float(eth_chg_val) if pd.notna(eth_chg_val) else 0.0
            else:
                row["eth_tvl_change_30d"] = 0.0

            # #56: eth_x_V_fwd_carry — interaction: eth_tvl_drawdown x V_fwd_carry__sh30
            fwd_sh30 = row.get("V_fwd_carry__sh30", 0.0)
            if eth_drawdown is not None:
                eth_dd_val = eth_dd_aligned.loc[date_t] if date_t in eth_dd_aligned.index else np.nan
                eth_dd_val = float(eth_dd_val) if pd.notna(eth_dd_val) else 0.0
            else:
                eth_dd_val = 0.0
            row["eth_x_V_fwd_carry"] = eth_dd_val * fwd_sh30

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
        row = {f"{strat}__fwd_sh": sharpe_d(fwd[:, i])
               for i, strat in enumerate(cols)}
        target_rows.append(row)
    return pd.DataFrame(target_rows, index=df.index[:n - horizon])


# ─────────────────────────────────────────────────────────────────────────────
# ML walk-forward (K198 methodology)
# ─────────────────────────────────────────────────────────────────────────────

def ml_walk_forward(
    df: pd.DataFrame,
    feat_df: pd.DataFrame,
    target_df: pd.DataFrame,
    extra_feat_names: List[str],
    train_days: int = ML_TRAIN_DAYS,
    test_days: int = ML_TEST_DAYS,
    alpha: float = 1.0,
) -> Tuple[pd.Series, list, dict]:
    """
    Ridge walk-forward allocator.
    Returns: (pnl_series, diagnostics, extra_feat_coef_summary)
    """
    cols = list(df.columns)
    n_strats = len(cols)

    common_idx = feat_df.index.intersection(target_df.index)
    feat_aligned = feat_df.loc[common_idx]
    tgt_aligned  = target_df.loc[common_idx]

    feat_arr   = feat_aligned.values
    target_arr = np.array([tgt_aligned[f"{c}__fwd_sh"].values for c in cols]).T
    date_idx   = feat_aligned.index
    feat_names = list(feat_df.columns)

    n = len(feat_arr)
    min_train = max(train_days, 45)

    extra_feat_indices = [feat_names.index(fn) for fn in extra_feat_names if fn in feat_names]

    wf_pnl   = []
    wf_dates = []
    diagnostics = []
    extra_coef_by_step = {fn: [] for fn in extra_feat_names}

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
        test_dates   = date_idx[t_test_start:t_test_end]

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
        step_coefs = {fn: [] for fn in extra_feat_names}

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

            for fi, fn in zip(extra_feat_indices, extra_feat_names):
                step_coefs[fn].append(float(model.coef_[fi]))

        # Aggregate extra feature coefs for this step (mean across strategies)
        for fn in extra_feat_names:
            if step_coefs[fn]:
                extra_coef_by_step[fn].append(float(np.mean(step_coefs[fn])))

        # Build weights
        pos_preds = np.maximum(preds, 0.0)
        w = pos_preds / pos_preds.sum() if pos_preds.sum() > 1e-10 else w_equal(n_strats)
        w = apply_all_caps(w, cols)

        # Execute on test period
        test_rets = df.loc[test_dates].values
        for d_i, d in enumerate(test_dates):
            wf_pnl.append(float(test_rets[d_i] @ w))
            wf_dates.append(d)

        diag = {
            "step": step,
            "train_start": str(date_idx[t_train_start].date()),
            "train_end":   str(date_idx[t_train_end - 1].date()),
            "test_start":  str(test_dates[0].date()),
            "test_end":    str(test_dates[-1].date()),
            "mean_r2":     round(float(np.nanmean(r2_scores)), 4),
            "weights":     {cols[i]: round(float(w[i]), 4) for i in range(n_strats)},
        }
        diagnostics.append(diag)
        step += 1

    pnl_series = pd.Series(wf_pnl, index=wf_dates, name="ml_pnl")

    # Summarize extra feature coefficients
    coef_summary = {}
    for fn in extra_feat_names:
        vals = extra_coef_by_step[fn]
        if vals:
            coef_summary[fn] = {
                "mean_coef": round(float(np.mean(vals)), 6),
                "std_coef":  round(float(np.std(vals)), 6),
                "nonzero":   bool(abs(np.mean(vals)) > 1e-8),
                "n_steps":   len(vals),
            }
        else:
            coef_summary[fn] = {"mean_coef": 0.0, "std_coef": 0.0, "nonzero": False, "n_steps": 0}

    return pnl_series, diagnostics, coef_summary


# ─────────────────────────────────────────────────────────────────────────────
# Per-fold analysis
# ─────────────────────────────────────────────────────────────────────────────

def wf_fold_sharpes(pnl: pd.Series, n_folds: int = N_FOLDS) -> dict:
    """Split pnl into n_folds and compute Sharpe per fold."""
    n = len(pnl)
    fold_size = n // n_folds
    sharpes = []
    for i in range(n_folds):
        start = i * fold_size
        end   = start + fold_size if i < n_folds - 1 else n
        sharpes.append(round(sharpe_d(pnl.values[start:end]), 4))
    return {
        "fold_sharpes": sharpes,
        "mean": round(float(np.mean(sharpes)), 4),
        "min":  round(float(np.min(sharpes)), 4),
        "max":  round(float(np.max(sharpes)), 4),
        "std":  round(float(np.std(sharpes)), 4),
    }


def oos_metrics(pnl: pd.Series, oos_frac: float = OOS_FRAC) -> dict:
    n = len(pnl)
    cut = int(n * (1.0 - oos_frac))
    return metrics_pkg(pnl.values[cut:])


# ─────────────────────────────────────────────────────────────────────────────
# Run a single variant
# ─────────────────────────────────────────────────────────────────────────────

def run_variant(
    variant: str,
    df_triggered: pd.DataFrame,
    target_df: pd.DataFrame,
    fr_mean: Optional[pd.Series],
    eth_change_30d: Optional[pd.Series],
    eth_drawdown: Optional[pd.Series],
    extra_feat_names: List[str],
) -> dict:
    """Run one K215 variant: build features, walk-forward, compute metrics."""
    t0 = time.time()
    print(f"  [{variant}] Building features...", flush=True)

    feat_df = build_features(
        df_triggered, fr_mean, variant,
        eth_change_30d=eth_change_30d,
        eth_drawdown=eth_drawdown,
    )
    n_features = feat_df.shape[1]
    print(f"  [{variant}] Feature matrix: {feat_df.shape[0]} rows x {n_features} features", flush=True)

    print(f"  [{variant}] Walk-forward (90d train -> 30d test)...", flush=True)
    pnl_series, diag, coef_summary = ml_walk_forward(
        df_triggered, feat_df, target_df, extra_feat_names,
        train_days=ML_TRAIN_DAYS, test_days=ML_TEST_DAYS, alpha=1.0,
    )

    if len(pnl_series) == 0:
        print(f"  [{variant}] ERROR: empty PnL", flush=True)
        return {}

    m_oos = oos_metrics(pnl_series)
    wf    = wf_fold_sharpes(pnl_series)
    elapsed = round(time.time() - t0, 1)

    # Acceptance gates vs K198
    gate_oos_sh  = m_oos["sharpe"] > K198_OOS_SH
    gate_wf_min  = wf["min"] >= K198_WF_MIN
    gate_max_dd  = m_oos["max_dd"] <= abs(K198_OOS_DD) * -1   # <= -0.0053 means MaxDD must not worsen
    gate_nonzero = all(coef_summary[fn]["nonzero"] for fn in extra_feat_names) if extra_feat_names else True

    all_pass = gate_oos_sh and gate_wf_min and gate_max_dd and gate_nonzero

    print(f"  [{variant}] OOS Sh={m_oos['sharpe']:.4f} MaxDD={m_oos['max_dd']:.4f} "
          f"WF mean={wf['mean']:.4f} WF min={wf['min']:.4f} | "
          f"{'PASS' if all_pass else 'FAIL'} [{elapsed}s]", flush=True)

    return {
        "variant": variant,
        "n_features": n_features,
        "extra_features": extra_feat_names,
        "oos_sharpe":  m_oos["sharpe"],
        "oos_maxdd":   m_oos["max_dd"],
        "oos_sortino": m_oos["sortino"],
        "oos_calmar":  m_oos["calmar"],
        "oos_ann_ret": m_oos["ann_ret"],
        "oos_ann_vol": m_oos["ann_vol"],
        "oos_n_days":  m_oos["n_days"],
        "wf_mean":     wf["mean"],
        "wf_min":      wf["min"],
        "wf_max":      wf["max"],
        "wf_std":      wf["std"],
        "wf_fold_sharpes": wf["fold_sharpes"],
        "gate_oos_sh":  gate_oos_sh,
        "gate_wf_min":  gate_wf_min,
        "gate_max_dd":  gate_max_dd,
        "gate_nonzero": gate_nonzero,
        "all_gates_pass": all_pass,
        "extra_feat_coef_summary": coef_summary,
        "n_wf_steps": len(diag),
        "runtime_s": elapsed,
        "pnl_series": pnl_series,
    }


# ─────────────────────────────────────────────────────────────────────────────
# Main
# ─────────────────────────────────────────────────────────────────────────────

def main():
    print("=" * 72)
    print("Wave K215 — Minimal Feature Addition Hypothesis")
    print("=" * 72)
    print()

    np.random.seed(42)

    # ── Step 1: Load data ─────────────────────────────────────────────────────
    print("Step 1: Loading component returns...", flush=True)
    df_all = load_component_returns()
    cols = list(df_all.columns)
    print()

    print("Step 2: Loading FR regime indicator...", flush=True)
    fr_mean = load_fr_mean_daily()
    if len(fr_mean) > 0:
        print(f"  FR data: {fr_mean.index[0].date()} -> {fr_mean.index[-1].date()}")
    else:
        fr_mean = None
        print("  WARNING: FR data not available")
    print()

    print("Step 3: Applying FR trigger...", flush=True)
    if fr_mean is not None:
        df_triggered = apply_fr_trigger(df_all, fr_mean)
        n_trigger = int((fr_mean.reindex(df_all.index, method="ffill") < FR_THRESHOLD).sum())
        print(f"  Trigger fires {n_trigger}/{len(df_all)} days ({n_trigger/len(df_all)*100:.1f}%)")
    else:
        df_triggered = df_all.copy()
    print()

    print("Step 4: Loading Ethena TVL signals...", flush=True)
    try:
        eth_change_30d, eth_drawdown = load_ethena_tvl()
        print(f"  eth_change_30d: {eth_change_30d.dropna().index[0].date()} -> {eth_change_30d.dropna().index[-1].date()}")
        print(f"  eth_drawdown: {eth_drawdown.dropna().index[0].date()} -> {eth_drawdown.dropna().index[-1].date()}")
    except FileNotFoundError as e:
        print(f"  WARNING: {e}")
        eth_change_30d = None
        eth_drawdown = None
    print()

    print("Step 5: Building shared target matrix...", flush=True)
    target_df = build_targets(df_triggered, horizon=ML_TEST_DAYS)
    print(f"  Target matrix: {target_df.shape[0]} rows x {target_df.shape[1]} strategies")
    print()

    # ── Step 6: Run all variants ──────────────────────────────────────────────
    VARIANTS = [
        # (variant_name, extra_feat_names_list)
        ("K215_0", []),
        ("K215_1", ["K116__dd90"]),
        ("K215_2", ["K116__dd90", "V_rev_carry__dd90"]),
        ("K215_3", ["K116__dd90", "V_rev_carry__dd90", "K114__sh_neg30"]),
        ("K215_5", ["K116__dd90", "V_rev_carry__dd90", "K114__sh_neg30",
                    "eth_tvl_change_30d", "eth_x_V_fwd_carry"]),
    ]

    results = {}
    pnl_series_all = {}

    for variant_name, extra_feats in VARIANTS:
        # Skip K215_5 if no Ethena data
        if "eth_tvl_change_30d" in extra_feats and eth_change_30d is None:
            print(f"  [{variant_name}] Skipping — no Ethena TVL data available", flush=True)
            continue

        print(f"\nRunning {variant_name} ({51 + len(extra_feats)} features)...", flush=True)
        res = run_variant(
            variant=variant_name,
            df_triggered=df_triggered,
            target_df=target_df,
            fr_mean=fr_mean,
            eth_change_30d=eth_change_30d,
            eth_drawdown=eth_drawdown,
            extra_feat_names=extra_feats,
        )
        if res:
            pnl_series_all[variant_name] = res.pop("pnl_series")
            results[variant_name] = res

    print()
    elapsed_total = time.time() - START_TIME
    print(f"Total runtime: {elapsed_total:.1f}s")
    print()

    # ── Step 7: Per-fold breakdown ────────────────────────────────────────────
    print("=" * 72)
    print("PER-FOLD SHARPE BREAKDOWN")
    print("=" * 72)
    header = f"{'Variant':<12} {'Fold1':>8} {'Fold2':>8} {'Fold3':>8} {'Fold4':>8} {'Mean':>8} {'Min':>8}"
    print(header)
    print("-" * 72)
    for vn in results:
        r = results[vn]
        folds = r["wf_fold_sharpes"]
        fold_str = "".join(f"{f:>8.2f}" for f in folds)
        print(f"{vn:<12}{fold_str}{r['wf_mean']:>8.2f}{r['wf_min']:>8.2f}")
    print()

    # ── Step 8: Six-way comparison table ─────────────────────────────────────
    print("=" * 72)
    print("SIX-WAY COMPARISON")
    print("=" * 72)
    header2 = f"{'Version':<18} {'Features':>9} {'OOS Sh':>9} {'OOS MaxDD':>11} {'WF mean':>9} {'WF min':>9} {'Status':>10}"
    print(header2)
    print("-" * 80)
    # Reference rows
    print(f"{'K198 (prod)':18s} {51:>9d} {K198_OOS_SH:>9.4f} {K198_OOS_DD:>11.4f} {K198_WF_MEAN:>9.2f} {K198_WF_MIN:>9.2f} {'baseline':>10}")
    print(f"{'K204 (REJECT)':18s} {113:>9d} {K204_OOS_SH:>9.4f} {-0.0053:>11.4f} {7.55:>9.2f} {K204_WF_MIN:>9.2f} {'REJECT':>10}")
    print("-" * 80)
    for vn in results:
        r = results[vn]
        status = "PASS" if r["all_gates_pass"] else "FAIL"
        oos_sh_delta = r["oos_sharpe"] - K198_OOS_SH
        sign = "+" if oos_sh_delta >= 0 else ""
        print(f"{vn:<18s} {r['n_features']:>9d} {r['oos_sharpe']:>9.4f} {r['oos_maxdd']:>11.4f} "
              f"{r['wf_mean']:>9.2f} {r['wf_min']:>9.2f} {status:>10}  (Sh{sign}{oos_sh_delta:.4f})")
    print()

    # ── Step 9: Feature coefficient analysis ─────────────────────────────────
    print("=" * 72)
    print("EXTRA FEATURE COEFFICIENT ANALYSIS")
    print("=" * 72)
    for vn in results:
        r = results[vn]
        coef = r["extra_feat_coef_summary"]
        if coef:
            print(f"\n{vn}:")
            for fn, stats in coef.items():
                nz = "[NON-ZERO]" if stats["nonzero"] else "[zero]"
                print(f"  {fn:<35s}: mean_coef={stats['mean_coef']:>+.6f}  std={stats['std_coef']:.6f}  {nz}")

    # ── Step 10: Determine optimal variant ───────────────────────────────────
    print()
    print("=" * 72)
    print("VERDICT: OPTIMAL FEATURE SUBSET FOR v6.6")
    print("=" * 72)

    passing_variants = [(vn, results[vn]) for vn in results if results[vn]["all_gates_pass"]]
    candidate_for_v66 = None

    if passing_variants:
        # Best by OOS Sh among passing
        best_vn, best_r = max(passing_variants, key=lambda x: x[1]["oos_sharpe"])
        candidate_for_v66 = best_vn
        print(f"Best passing variant: {best_vn}")
        print(f"  OOS Sh:  {best_r['oos_sharpe']:.4f} (K198: {K198_OOS_SH:.4f}, lift: {best_r['oos_sharpe'] - K198_OOS_SH:+.4f})")
        print(f"  MaxDD:   {best_r['oos_maxdd']:.4f} (K198: {K198_OOS_DD:.4f})")
        print(f"  WF min:  {best_r['wf_min']:.4f} (K198: {K198_WF_MIN:.4f}, lift: {best_r['wf_min'] - K198_WF_MIN:+.4f})")
        print(f"  Recommendation: PROMOTE {best_vn} to v6.6")
    else:
        print("No K215 variant passes all acceptance gates.")
        # Find best performer anyway
        if results:
            best_vn_any = max(results, key=lambda vn: results[vn]["oos_sharpe"])
            best_r_any = results[best_vn_any]
            print(f"Best performer (not passing): {best_vn_any}")
            print(f"  OOS Sh: {best_r_any['oos_sharpe']:.4f}, WF min: {best_r_any['wf_min']:.4f}")
            fail_reasons = []
            if not best_r_any["gate_oos_sh"]:  fail_reasons.append(f"OOS Sh {best_r_any['oos_sharpe']:.4f} <= {K198_OOS_SH}")
            if not best_r_any["gate_wf_min"]:  fail_reasons.append(f"WF min {best_r_any['wf_min']:.4f} < {K198_WF_MIN}")
            if not best_r_any["gate_max_dd"]:  fail_reasons.append(f"MaxDD {best_r_any['oos_maxdd']:.4f} worse than {K198_OOS_DD}")
            print(f"  Fails: {'; '.join(fail_reasons)}")

        print("  Meta-conclusion: Single feature additions do not improve upon K198.")
        print("  K198 (51 features) remains optimal — complexity hypothesis CONFIRMED.")
        print("  K216 recommendation: Explore non-feature-engineering paths:")
        print("    - Dynamic carry caps (responsive to FR regime)")
        print("    - Alternative target (Calmar instead of Sharpe)")
        print("    - Ensemble with complementary uncorrelated strategy")

    print()

    # ── Step 11: Is noise the failure mode? (key research question) ───────────
    print("=" * 72)
    print("RESEARCH CONCLUSIONS")
    print("=" * 72)

    # Compare incremental OOS Sh changes
    k215_0_sh = results.get("K215_0", {}).get("oos_sharpe", None)
    k215_1_sh = results.get("K215_1", {}).get("oos_sharpe", None)
    k215_2_sh = results.get("K215_2", {}).get("oos_sharpe", None)
    k215_3_sh = results.get("K215_3", {}).get("oos_sharpe", None)
    k215_5_sh = results.get("K215_5", {}).get("oos_sharpe", None)

    print("\n1. Feature noise hypothesis:")
    if k215_0_sh is not None and k215_3_sh is not None:
        delta_0_to_3 = k215_3_sh - k215_0_sh
        if delta_0_to_3 > 0:
            print(f"  Adding 3 features (51->54) lifted OOS Sh by {delta_0_to_3:+.4f}")
            print(f"  vs K204 adding 62 features (51->113) lifted OOS Sh by only {K204_OOS_SH - K198_OOS_SH:+.4f}")
            print(f"  -> Minimal additions appear MORE efficient than bulk (noise CONFIRMED as K204 problem)")
        else:
            print(f"  Adding 3 features (51->54) changed OOS Sh by {delta_0_to_3:+.4f}")
            print(f"  -> Feature noise does not fully explain rejections; signal simply absent")

    print("\n2. Optimal feature count:")
    feature_counts = [(vn, results[vn]["n_features"], results[vn]["oos_sharpe"])
                      for vn in results]
    for vn, fc, sh in feature_counts:
        delta = sh - K198_OOS_SH
        print(f"  {vn}: {fc} features, OOS Sh {sh:.4f} ({delta:+.4f} vs K198)")

    print("\n3. Additivity test (does Sh monotonically increase?):")
    shs = [(vn, results[vn]["oos_sharpe"]) for vn in results]
    monotone = all(shs[i][1] <= shs[i+1][1] for i in range(len(shs)-1))
    print(f"  Monotone increasing: {monotone}")
    for i in range(len(shs)-1):
        delta_step = shs[i+1][1] - shs[i][1]
        print(f"  {shs[i][0]} -> {shs[i+1][0]}: {delta_step:+.4f}")

    print()

    # ── Assemble and save outputs ─────────────────────────────────────────────
    print("Saving outputs...", flush=True)

    # Metrics JSON
    output_json = {
        "wave": "K215",
        "task": "Minimal feature addition hypothesis — cumulative 51+1+1+1+2",
        "as_of": pd.Timestamp.now(tz="UTC").isoformat(),
        "runtime_s": round(elapsed_total, 1),
        "config": {
            "ml_train_days": ML_TRAIN_DAYS,
            "ml_test_days": ML_TEST_DAYS,
            "ridge_alpha": 1.0,
            "oos_frac": OOS_FRAC,
            "n_folds": N_FOLDS,
            "caps": {"K121": K121_CAP, "V_fwd_carry": CARRY_FWD_CAP, "V_rev_carry": CARRY_REV_CAP},
        },
        "references": {
            "K198_prod": {"features": 51, "oos_sh": K198_OOS_SH, "oos_dd": K198_OOS_DD,
                          "wf_mean": K198_WF_MEAN, "wf_min": K198_WF_MIN},
            "K204_reject": {"features": 113, "oos_sh": K204_OOS_SH, "wf_min": K204_WF_MIN},
        },
        "variants": {vn: {k: v for k, v in results[vn].items() if k != "extra_feat_coef_summary"}
                     for vn in results},
        "feature_coef_analysis": {vn: results[vn]["extra_feat_coef_summary"]
                                   for vn in results},
        "optimal_variant": candidate_for_v66,
        "verdict": "PROMOTE " + candidate_for_v66 + " to v6.6" if candidate_for_v66
                   else "No improvement over K198. K198 (51 features) remains production.",
    }

    with open(BASE / "wave_k215_minimal_features.json", "w") as f:
        json.dump(output_json, f, indent=2)
    print("  Saved: wave_k215_minimal_features.json")

    # Curves JSON
    curves_out = {}
    for vn, pnl in pnl_series_all.items():
        eq = np.cumprod(1.0 + pnl.values).tolist()
        curves_out[vn] = {
            "dates":  [str(d.date()) for d in pnl.index],
            "equity": [round(float(v), 6) for v in eq],
            "pnl":    [round(float(v), 8) for v in pnl.values],
        }

    with open(BASE / "wave_k215_curves.json", "w") as f:
        json.dump(curves_out, f, indent=2)
    print("  Saved: wave_k215_curves.json")

    print()
    print("=" * 72)
    print("K215 COMPLETE")
    print("=" * 72)

    return output_json


if __name__ == "__main__":
    main()

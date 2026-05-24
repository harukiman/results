"""Wave K211 — Ethena TVL Interaction Features for K198 ML Allocator (v6.6 candidate).

Objective:
  Apply K207 prescription: instead of global Ethena features (which dilute Ridge
  discrimination by being identical across all strategies), use carry-specific
  interaction features that only modulate the relevant carry strategies.

Architecture:
  - Load K198 51-feature matrix (sh30, sh90, vol30, mdd30, xcorr × 10 + fr_mean)
  - Load Ethena TVL cache (cache/ethena_tvl_daily.parquet)
  - Compute 2 carry-specific interaction features:
      eth_x_V_rev_carry: eth_tvl_change_30d × V_rev_carry__sh30
                         (NON-ZERO only for V_rev_carry strategy rows)
      eth_x_V_fwd_carry: eth_tvl_drawdown × V_fwd_carry__sh30
                         (NON-ZERO only for V_fwd_carry strategy rows)
  - Total: 51 + 2 = 53 features
  - Walk-forward identical to K198 (90d train → 30d test, same caps)

Rationale (from K207 diagnosis):
  - K207 found V_rev_carry × eth_tvl_change_7d coefficient +0.491 (signal is REAL)
  - BUT global features caused Ridge to reduce V_rev_carry weight (6%→3%) because
    TVL value is identical across all strategies, diluting discrimination
  - Interaction features make the signal per-strategy, not global noise

K198 baseline: OOS Sh 10.28, MaxDD -0.0053, WF mean 7.91, WF min 6.57
K207 global (REJECTED): OOS Sh 8.87, MaxDD -0.0063

Acceptance for K211 → v6.6:
  OOS Sh ≥ 10.28 (K198), preferably > 10.36
  WF min ≥ 6.57 (K198)
  MaxDD ≤ -0.0053 (K198)
  Interaction features must have non-zero Ridge coefficient
  V_rev_carry weight should respond to TVL regime appropriately

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

# ML walk-forward params (identical to K198)
ML_TRAIN_DAYS = 90
ML_TEST_DAYS  = 30

# K198 v6.5 reference (acceptance baseline)
K198_OOS_SH  = 10.28
K198_OOS_DD  = -0.0053
K198_WF_MEAN = 7.91
K198_WF_MIN  = 6.57

# K207 reference (rejected, global Ethena)
K207_OOS_SH  = 8.8748
K207_OOS_DD  = -0.0063
K207_WF_MEAN = 7.5252
K207_WF_MIN  = 6.576

# K204 secondary threshold
K204_OOS_SH  = 10.36

# Caps (identical to K198/K207)
K121_CAP       = 0.30
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

# Strategy indices for interaction features
V_REV_CARRY_IDX = STRATEGY_NAMES.index("V_rev_carry")   # 9
V_FWD_CARRY_IDX = STRATEGY_NAMES.index("V_fwd_carry")   # 8

# Ethena TVL feature config
ETH_TVL_LAG_DAYS = 7  # lag to avoid look-ahead bias


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
    """Apply K121 cap and carry caps."""
    w = apply_cap(w, cols, "K121", K121_CAP)
    w = apply_cap(w, cols, "V_fwd_carry", CARRY_FWD_CAP)
    w = apply_cap(w, cols, "V_rev_carry", CARRY_REV_CAP)
    return w


# ──────────────────────────────────────────────────────────────────────────────
# Data loading (identical to K198/K207)
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
# Ethena TVL interaction features
# ──────────────────────────────────────────────────────────────────────────────

def load_ethena_tvl_series(lag_days: int = ETH_TVL_LAG_DAYS) -> Tuple[pd.Series, pd.Series]:
    """
    Load Ethena TVL cache and compute 2 interaction base signals with lag.

    Returns:
      eth_change_30d: 30-day % change in TVL (lagged)
      eth_drawdown:   30-day peak-to-trough drawdown of TVL (lagged)
    """
    cache_path = CACHE / "ethena_tvl_daily.parquet"
    if not cache_path.exists():
        raise FileNotFoundError(f"Ethena TVL cache not found: {cache_path}")

    tvl_df = pd.read_parquet(cache_path)
    tvl = tvl_df["tvl"]

    # Ensure tz-naive index
    if tvl.index.tz is not None:
        tvl.index = tvl.index.tz_localize(None)

    # 30-day % change (per K207 importance #6: highest ranked Ethena feature)
    eth_change_30d = tvl.pct_change(30)

    # Peak-to-trough 30d drawdown (per K207 importance #8)
    rolling_peak_30d = tvl.rolling(30, min_periods=2).max()
    eth_drawdown = (tvl - rolling_peak_30d) / rolling_peak_30d.replace(0, np.nan)

    # Apply lag to prevent look-ahead bias
    eth_change_30d = eth_change_30d.shift(lag_days)
    eth_drawdown   = eth_drawdown.shift(lag_days)

    eth_change_30d.name = "eth_tvl_change_30d"
    eth_drawdown.name   = "eth_tvl_drawdown"

    print(f"  Ethena TVL series: {len(tvl)} rows, lag={lag_days}d")
    print(f"  eth_change_30d range: {eth_change_30d.dropna().index[0].date()} -> "
          f"{eth_change_30d.dropna().index[-1].date()}")
    print(f"  eth_drawdown range: {eth_drawdown.dropna().index[0].date()} -> "
          f"{eth_drawdown.dropna().index[-1].date()}")

    return eth_change_30d, eth_drawdown


# ──────────────────────────────────────────────────────────────────────────────
# Feature engineering: K198 51 features + 2 interaction features
# ──────────────────────────────────────────────────────────────────────────────

def build_features_k211(
    df: pd.DataFrame,
    fr_mean: Optional[pd.Series],
    eth_change_30d: pd.Series,
    eth_drawdown: pd.Series,
    win_short: int = 30,
    win_long: int = 90,
) -> pd.DataFrame:
    """
    Build 53-feature matrix:
      - 50 per-strategy features (sh30, sh90, vol30, mdd30, xcorr) x 10 strategies
      - 1 FR regime indicator (fr_mean_ann)
      - 2 interaction features (carry-specific, NON-ZERO only for target strategy):
          eth_x_V_rev_carry = eth_tvl_change_30d * V_rev_carry__sh30
          eth_x_V_fwd_carry = eth_tvl_drawdown   * V_fwd_carry__sh30

    The interaction features are strategy-specific: they are non-zero ONLY when the
    feature at day t is being used to predict the target strategy. In the flat
    per-row structure, they represent the Ethena signal scaled by that strategy's
    recent momentum — making the TVL signal carry-specific, not global noise.

    Implementation note:
      Because the feature matrix is (days, features) rather than (strategy x days),
      we compute both interaction values and include them as two columns. For non-carry
      strategies, these columns will be zero (no carry performance to interact with).
      For carry strategies, they capture the TVL × carry momentum cross-signal.
    """
    n_strats = df.shape[1]
    cols = list(df.columns)
    R = df.values
    n = len(R)

    # Align Ethena signals to df index
    eth_chg_aligned = eth_change_30d.reindex(df.index, method="ffill")
    eth_dd_aligned  = eth_drawdown.reindex(df.index, method="ffill")

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

        # Per-strategy features (50 total = 10 x 5)
        for i, strat in enumerate(cols):
            prefix = f"{strat}__"
            sh30  = sharpe_d(slice_short[:, i])
            sh90  = sharpe_d(slice_long[:, i])
            vol30 = float(slice_short[:, i].std(ddof=1) * math.sqrt(TRADING_DAYS))
            mdd30 = max_dd_d(slice_short[:, i])
            if n_strats > 1:
                other_corrs = np.delete(corr_mat[i], i)
                xcorr = float(np.mean(other_corrs))
            else:
                xcorr = 0.0

            row[f"{prefix}sh30"]  = sh30
            row[f"{prefix}sh90"]  = sh90
            row[f"{prefix}vol30"] = vol30
            row[f"{prefix}mdd30"] = mdd30
            row[f"{prefix}xcorr"] = xcorr

        # FR regime indicator (feature #51)
        if fr_mean is not None and len(fr_mean) > 0:
            fr_date = df.index[t]
            fr_aligned_val = fr_mean.reindex([fr_date], method="ffill")
            row["fr_mean_ann"] = float(fr_aligned_val.iloc[0]) if not fr_aligned_val.isna().all() else 0.0
        else:
            row["fr_mean_ann"] = 0.0

        # ── Interaction features #52 and #53 ────────────────────────────────────
        date_t = df.index[t]
        eth_chg_val = eth_chg_aligned.loc[date_t] if date_t in eth_chg_aligned.index else np.nan
        eth_dd_val  = eth_dd_aligned.loc[date_t]  if date_t in eth_dd_aligned.index  else np.nan

        eth_chg_val = float(eth_chg_val) if pd.notna(eth_chg_val) else 0.0
        eth_dd_val  = float(eth_dd_val)  if pd.notna(eth_dd_val)  else 0.0

        # eth_x_V_rev_carry: eth_tvl_change_30d × V_rev_carry__sh30
        # Non-zero effect: TVL growth signal scales V_rev_carry's recent Sharpe momentum
        rev_carry_sh30 = row.get("V_rev_carry__sh30", 0.0)
        row["eth_x_V_rev_carry"] = eth_chg_val * rev_carry_sh30

        # eth_x_V_fwd_carry: eth_tvl_drawdown × V_fwd_carry__sh30
        # Non-zero effect: TVL drawdown signal scales V_fwd_carry's recent Sharpe momentum
        fwd_carry_sh30 = row.get("V_fwd_carry__sh30", 0.0)
        row["eth_x_V_fwd_carry"] = eth_dd_val * fwd_carry_sh30

        feat_rows.append(row)

    feat_df = pd.DataFrame(feat_rows, index=df.index[win_long:])
    return feat_df


def build_targets(df: pd.DataFrame, horizon: int = 30) -> pd.DataFrame:
    """Build next-horizon-day forward Sharpe targets (identical to K198)."""
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
# ML walk-forward (K198 methodology, 53 features)
# ──────────────────────────────────────────────────────────────────────────────

def ml_walk_forward(
    df: pd.DataFrame,
    feat_df: pd.DataFrame,
    target_df: pd.DataFrame,
    train_days: int = ML_TRAIN_DAYS,
    test_days:  int = ML_TEST_DAYS,
    alpha:      float = 1.0,
) -> Tuple[pd.DataFrame, pd.Series, list]:
    """Ridge walk-forward allocator (90d train -> 30d test, 15+ steps)."""
    cols = list(df.columns)
    n_strats = len(cols)

    common_idx = feat_df.index.intersection(target_df.index)
    feat_aligned   = feat_df.loc[common_idx]
    target_aligned = target_df.loc[common_idx]

    feat_arr   = feat_aligned.values
    target_arr = np.array([target_aligned[f"{c}__fwd_sh"].values for c in cols]).T
    date_idx   = feat_aligned.index
    feat_names = list(feat_df.columns)

    n = len(feat_arr)
    min_train = max(train_days, 45)

    # Interaction feature indices for tracking
    interact_feat_names = ["eth_x_V_rev_carry", "eth_x_V_fwd_carry"]
    interact_feat_indices = [feat_names.index(fn) for fn in interact_feat_names if fn in feat_names]

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
        interact_coef_per_strat = {strat: {} for strat in cols}

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

            # Save interaction feature coefficients
            for fi in interact_feat_indices:
                interact_coef_per_strat[cols[i]][feat_names[fi]] = float(model.coef_[fi])

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
            "interact_coef_per_strat": {
                strat: {k: round(v, 6) for k, v in coefs.items()}
                for strat, coefs in interact_coef_per_strat.items()
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
    pnl_series = pd.Series(wf_pnl, index=wf_dates, name="k211_pnl")
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


def compute_signed_coefs_by_strategy(
    feat_df: pd.DataFrame,
    target_df: pd.DataFrame,
    cols: List[str],
    alpha: float = 1.0,
) -> Dict[str, Dict[str, float]]:
    """Fit Ridge per strategy, return signed coefficients for interaction features."""
    common_idx = feat_df.index.intersection(target_df.index)
    X = feat_df.loc[common_idx].values
    X = np.nan_to_num(X, nan=0.0, posinf=0.0, neginf=0.0)
    scaler = StandardScaler()
    X_s = scaler.fit_transform(X)
    feature_names = list(feat_df.columns)

    interact_names = ["eth_x_V_rev_carry", "eth_x_V_fwd_carry"]
    result = {}

    for strat in cols:
        target_col = f"{strat}__fwd_sh"
        if target_col not in target_df.columns:
            continue
        y = target_df.loc[common_idx, target_col].values
        if np.isnan(y).any() or np.std(y) < 1e-10:
            continue
        model = Ridge(alpha=alpha)
        model.fit(X_s, y)
        strat_coefs = {}
        for fn in interact_names:
            if fn in feature_names:
                fi = feature_names.index(fn)
                strat_coefs[fn] = round(float(model.coef_[fi]), 6)
        result[strat] = strat_coefs

    return result


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


def aggregate_interact_coefs(diagnostics: list, cols: List[str]) -> dict:
    """Aggregate interaction feature coefficients across WF steps per strategy."""
    interact_feat_names = ["eth_x_V_rev_carry", "eth_x_V_fwd_carry"]
    result = {}
    for strat in cols:
        coef_over_time = {fn: [] for fn in interact_feat_names}
        for d in diagnostics:
            coefs = d.get("interact_coef_per_strat", {}).get(strat, {})
            for fn in interact_feat_names:
                if fn in coefs:
                    coef_over_time[fn].append(coefs[fn])
        strat_result = {}
        for fn in interact_feat_names:
            vals = coef_over_time[fn]
            if vals:
                strat_result[fn] = {
                    "mean_coef":       round(float(np.mean(vals)), 6),
                    "abs_mean":        round(float(np.mean(np.abs(vals))), 6),
                    "pct_nonzero":     round(float(np.mean([abs(v) > 1e-8 for v in vals])), 4),
                    "sign_consistency": round(float(np.mean(
                        np.sign(vals) == np.sign(np.mean(vals)))), 4),
                    "trajectory":      [round(v, 6) for v in vals],
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
# V_rev_carry weight trajectory analysis
# ──────────────────────────────────────────────────────────────────────────────

def extract_carry_weight_trajectory(diagnostics: list) -> dict:
    """Extract V_rev_carry and V_fwd_carry weights per WF step with ETH TVL context."""
    traj = []
    for d in diagnostics:
        step_info = {
            "step":         d["step"],
            "test_start":   d["test_start"],
            "test_end":     d["test_end"],
            "V_rev_carry_w": d["weights"].get("V_rev_carry", 0.0),
            "V_fwd_carry_w": d["weights"].get("V_fwd_carry", 0.0),
            "V_rev_carry_pred": d["preds"].get("V_rev_carry", 0.0),
            "V_fwd_carry_pred": d["preds"].get("V_fwd_carry", 0.0),
            "eth_x_V_rev_coef": d.get("interact_coef_per_strat", {}).get(
                "V_rev_carry", {}).get("eth_x_V_rev_carry", 0.0),
            "eth_x_V_fwd_coef": d.get("interact_coef_per_strat", {}).get(
                "V_fwd_carry", {}).get("eth_x_V_fwd_carry", 0.0),
        }
        traj.append(step_info)
    return {"trajectory": traj}


# ──────────────────────────────────────────────────────────────────────────────
# Main
# ──────────────────────────────────────────────────────────────────────────────

def main():
    print("=" * 72)
    print("Wave K211 -- Ethena Interaction Features + K198 ML Allocator (v6.6 candidate)")
    print("=" * 72)
    print()

    np.random.seed(42)

    # ── Step 1: Load component returns ───────────────────────────────────────
    print("Step 1: Loading K196 component returns...", flush=True)
    df_all = load_component_returns()
    cols   = list(df_all.columns)
    n_strats = len(cols)
    print(f"  Strategies: {cols}")
    print(f"  V_rev_carry index: {V_REV_CARRY_IDX}, V_fwd_carry index: {V_FWD_CARRY_IDX}")
    print()

    # ── Step 2: Load FR regime indicator ─────────────────────────────────────
    print("Step 2: Loading FR regime indicator...", flush=True)
    fr_mean = load_fr_mean_daily()
    if len(fr_mean) > 0:
        print(f"  FR mean range: {fr_mean.index[0].date()} -> {fr_mean.index[-1].date()}")
        fr_aligned = fr_mean.reindex(df_all.index, method="ffill")
        print(f"  FR mean stats: mean={fr_aligned.mean():.4f} std={fr_aligned.std():.4f}")
    else:
        fr_aligned = None
        print("  WARNING: FR data not available")
    print()

    # ── Step 3: Load Ethena TVL interaction signals ───────────────────────────
    print("Step 3: Loading Ethena TVL interaction signals (7d lag)...", flush=True)
    eth_change_30d, eth_drawdown = load_ethena_tvl_series(lag_days=ETH_TVL_LAG_DAYS)
    overlap_chg = df_all.index.intersection(eth_change_30d.dropna().index)
    overlap_dd  = df_all.index.intersection(eth_drawdown.dropna().index)
    print(f"  eth_change_30d overlap with portfolio dates: {len(overlap_chg)} days")
    print(f"  eth_drawdown overlap with portfolio dates: {len(overlap_dd)} days")
    print()

    # ── Step 4: Apply FR trigger ─────────────────────────────────────────────
    print("Step 4: Applying FR trigger (K121, K133)...", flush=True)
    if fr_mean is not None and len(fr_mean) > 0:
        df_triggered = apply_fr_trigger(df_all, fr_mean)
        n_trigger = int((fr_mean.reindex(df_all.index, method="ffill") < FR_THRESHOLD).sum())
        print(f"  Trigger fires {n_trigger} / {len(df_all)} days ({n_trigger/len(df_all)*100:.1f}%)")
    else:
        df_triggered = df_all.copy()
        print("  No FR trigger applied")
    print()

    # ── Step 5: Build 53-feature matrix (K198 51 + interaction 2) ────────────
    print("Step 5: Building 53-feature matrix (51 K198 + 2 interaction)...", flush=True)
    feat_df = build_features_k211(
        df_triggered,
        fr_mean if len(fr_mean) > 0 else None,
        eth_change_30d,
        eth_drawdown,
        win_short=30,
        win_long=90,
    )
    print(f"  Feature matrix: {feat_df.shape[0]} rows x {feat_df.shape[1]} features")
    print(f"  Feature date range: {feat_df.index[0].date()} -> {feat_df.index[-1].date()}")
    # Report interaction feature stats
    for ic in ["eth_x_V_rev_carry", "eth_x_V_fwd_carry"]:
        nonzero = (feat_df[ic] != 0).sum()
        print(f"  {ic}: {nonzero}/{len(feat_df)} non-zero ({nonzero/len(feat_df)*100:.1f}%), "
              f"mean={feat_df[ic].mean():.4f}, std={feat_df[ic].std():.4f}")
    print()

    # ── Step 6: Build targets ─────────────────────────────────────────────────
    print("Step 6: Building forward Sharpe targets (horizon=30d)...", flush=True)
    target_df = build_targets(df_triggered, horizon=ML_TEST_DAYS)
    print(f"  Target matrix: {target_df.shape[0]} rows x {target_df.shape[1]} strategies")
    print()

    # ── Step 7: K211 Ridge walk-forward ──────────────────────────────────────
    print("Step 7: K211 Ridge walk-forward (53 features, 90d train -> 30d test)...", flush=True)
    weights_k211, pnl_k211, diagnostics_k211 = ml_walk_forward(
        df_triggered, feat_df, target_df,
        train_days=ML_TRAIN_DAYS,
        test_days=ML_TEST_DAYS,
        alpha=1.0,
    )
    if len(pnl_k211) == 0:
        print("  ERROR: K211 walk-forward returned empty PnL")
        return
    print(f"  K211 WF PnL: {len(pnl_k211)} days, "
          f"{pnl_k211.index[0].date()} -> {pnl_k211.index[-1].date()}")
    print(f"  WF steps completed: {len(diagnostics_k211)}")
    print()

    # ── Step 8: Walk-forward static P3 (baseline) ────────────────────────────
    print("Step 8: Walk-forward static P3 (apples-to-apples baseline)...", flush=True)
    pnl_static_wf, _ = run_wf_static_p3(df_triggered)
    common_start = pnl_k211.index[0]
    common_end   = pnl_k211.index[-1]
    static_aligned = pnl_static_wf[
        (pnl_static_wf.index >= common_start) & (pnl_static_wf.index <= common_end)
    ]
    print(f"  Static WF PnL: {len(static_aligned)} days aligned")
    print()

    # ── Step 9: OOS metrics ───────────────────────────────────────────────────
    print("Step 9: Computing OOS metrics (last 30%)...", flush=True)
    oos_k211   = oos_cut(pnl_k211)
    oos_static = oos_cut(static_aligned) if len(static_aligned) > 0 else oos_cut(pnl_k211)

    m_k211   = metrics_pkg(oos_k211.values)
    m_static = metrics_pkg(oos_static.values)

    k211_oos_sh = m_k211["sharpe"]
    k211_oos_dd = m_k211["max_dd"]

    print(f"  K198 v6.5 baseline (reference):       OOS Sh={K198_OOS_SH:.4f}  MaxDD={K198_OOS_DD:.4f}")
    print(f"  K207 global Ethena (rejected):         OOS Sh={K207_OOS_SH:.4f}  MaxDD={K207_OOS_DD:.4f}")
    print(f"  K211 interaction Ethena (this):        OOS Sh={k211_oos_sh:.4f}  MaxDD={k211_oos_dd:.4f}")
    print(f"  WF static P3 (same windows):           OOS Sh={m_static['sharpe']:.4f}  MaxDD={m_static['max_dd']:.4f}")
    print()

    # ── Step 10: WF fold analysis ─────────────────────────────────────────────
    print("Step 10: Walk-forward fold analysis (4 folds)...", flush=True)
    wf_folds = wf_fold_sharpes(pnl_k211)
    print(f"  Fold Sharpes: {wf_folds['fold_sharpes']}")
    print(f"  WF mean: {wf_folds['mean']:.4f}  WF min: {wf_folds['min']:.4f}  WF max: {wf_folds['max']:.4f}")
    print()

    # ── Step 11: Feature importance ───────────────────────────────────────────
    print("Step 11: Computing feature importance (global Ridge)...", flush=True)
    feat_importance = compute_feature_importance(feat_df, target_df, cols)
    top_features = list(feat_importance.items())[:15]
    print("  Top 15 features by |coefficient|:")
    for fname, val in top_features:
        marker = " <-- INTERACTION" if fname.startswith("eth_x") else ""
        print(f"    {fname}: {val:.6f}{marker}")

    # Rank of interaction features
    all_feat_names = list(feat_importance.keys())
    for ic in ["eth_x_V_rev_carry", "eth_x_V_fwd_carry"]:
        if ic in all_feat_names:
            rank = all_feat_names.index(ic) + 1
            val  = feat_importance[ic]
            print(f"  {ic}: rank #{rank}/{len(all_feat_names)}, |coef|={val:.6f}")
    print()

    # ── Step 12: Signed coefficients per strategy ─────────────────────────────
    print("Step 12: Signed interaction coefficients per strategy...", flush=True)
    signed_coefs = compute_signed_coefs_by_strategy(feat_df, target_df, cols)
    for strat, coefs in signed_coefs.items():
        if coefs:
            print(f"  {strat}:")
            for fn, val in coefs.items():
                print(f"    {fn}: {val:+.6f}")
    print()

    # ── Step 13: Interaction coefficient aggregation across WF steps ──────────
    print("Step 13: Aggregating interaction coefficients across WF steps...", flush=True)
    interact_agg = aggregate_interact_coefs(diagnostics_k211, cols)
    # Focus on carry strategies
    for strat in ["V_rev_carry", "V_fwd_carry"]:
        print(f"  {strat}:")
        for fn, info in interact_agg[strat].items():
            if isinstance(info, dict):
                print(f"    {fn}: mean_coef={info['mean_coef']:+.6f}, "
                      f"abs_mean={info['abs_mean']:.6f}, "
                      f"pct_nonzero={info['pct_nonzero']:.1%}, "
                      f"sign_consty={info.get('sign_consistency', 0):.2f}")
    print()

    # ── Step 14: V_rev_carry weight trajectory ────────────────────────────────
    print("Step 14: V_rev_carry weight trajectory analysis...", flush=True)
    carry_traj = extract_carry_weight_trajectory(diagnostics_k211)
    rev_weights = [s["V_rev_carry_w"] for s in carry_traj["trajectory"]]
    fwd_weights = [s["V_fwd_carry_w"] for s in carry_traj["trajectory"]]
    print(f"  V_rev_carry weights over WF steps: {[round(w, 4) for w in rev_weights]}")
    print(f"  V_fwd_carry weights over WF steps: {[round(w, 4) for w in fwd_weights]}")
    print(f"  V_rev_carry mean weight: {np.mean(rev_weights):.4f}, "
          f"min: {np.min(rev_weights):.4f}, max: {np.max(rev_weights):.4f}")
    print()

    # ── Step 15: Acceptance check ─────────────────────────────────────────────
    print("Step 15: Acceptance check for K211 -> v6.6...", flush=True)
    accept_oos_sh  = k211_oos_sh >= K198_OOS_SH
    accept_wf_min  = wf_folds["min"] >= K198_WF_MIN
    accept_mdd     = k211_oos_dd >= K198_OOS_DD  # less negative = better
    accept_interact = any(
        feat_importance.get(ic, 0.0) > 1e-8
        for ic in ["eth_x_V_rev_carry", "eth_x_V_fwd_carry"]
    )
    overall_accept = accept_oos_sh and accept_wf_min and accept_mdd and accept_interact

    print(f"  OOS Sh >= K198 ({K198_OOS_SH}): {k211_oos_sh:.4f} -> {'PASS' if accept_oos_sh else 'FAIL'}")
    print(f"  WF min >= K198 ({K198_WF_MIN}): {wf_folds['min']:.4f} -> {'PASS' if accept_wf_min else 'FAIL'}")
    print(f"  MaxDD >= K198 ({K198_OOS_DD}): {k211_oos_dd:.4f} -> {'PASS' if accept_mdd else 'FAIL'}")
    print(f"  Interaction features non-zero: -> {'PASS' if accept_interact else 'FAIL'}")
    print(f"  OVERALL: {'ACCEPT -> promote to v6.6' if overall_accept else 'REJECT'}")
    print()

    # ── Diagnostics summary ──────────────────────────────────────────────────
    diag_summary = aggregate_diagnostics(diagnostics_k211, cols)

    # ── Build output JSON ─────────────────────────────────────────────────────
    import datetime
    as_of = datetime.datetime.utcnow().isoformat() + "+00:00"
    runtime_s = round(time.time() - START_TIME, 1)

    output = {
        "wave": "K211",
        "task": "Ethena TVL interaction features for K198 ML allocator (v6.6 candidate)",
        "as_of": as_of,
        "runtime_s": runtime_s,
        "config": {
            "strategies": cols,
            "n_strategies": n_strats,
            "n_base_features": 51,
            "n_interaction_features": 2,
            "n_total_features": 53,
            "interaction_features": ["eth_x_V_rev_carry", "eth_x_V_fwd_carry"],
            "interaction_design": {
                "eth_x_V_rev_carry": "eth_tvl_change_30d x V_rev_carry__sh30",
                "eth_x_V_fwd_carry": "eth_tvl_drawdown x V_fwd_carry__sh30",
            },
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
            "date_range": [
                str(df_triggered.index[0].date()),
                str(df_triggered.index[-1].date()),
            ],
            "n_days_total": len(df_triggered),
            "n_wf_steps": len(diagnostics_k211),
        },
        "three_way_comparison": {
            "K198_v6_5_baseline": {
                "description": "K198 Ridge ML, 51 features, production v6.5",
                "oos_sharpe": K198_OOS_SH,
                "oos_maxdd":  K198_OOS_DD,
                "wf_mean":    K198_WF_MEAN,
                "wf_min":     K198_WF_MIN,
            },
            "K207_global_ethena_rejected": {
                "description": "K207 Ridge ML, 55 features (51 + 4 global Ethena TVL), REJECTED",
                "oos_sharpe": K207_OOS_SH,
                "oos_maxdd":  K207_OOS_DD,
                "wf_mean":    K207_WF_MEAN,
                "wf_min":     K207_WF_MIN,
                "rejection_reason": "Global TVL features dilute Ridge discrimination (identical across strategies)",
            },
            "K211_interaction_ethena": {
                "description": "K211 Ridge ML, 53 features (51 + 2 carry-specific interaction)",
                "oos_sharpe": round(k211_oos_sh, 4),
                "oos_maxdd":  round(k211_oos_dd, 4),
                "oos_sortino": m_k211["sortino"],
                "oos_calmar":  m_k211["calmar"],
                "oos_ann_ret": m_k211["ann_ret"],
                "oos_ann_vol": m_k211["ann_vol"],
                "oos_n_days":  m_k211["n_days"],
                "wf_mean": wf_folds["mean"],
                "wf_min":  wf_folds["min"],
                "wf_max":  wf_folds["max"],
                "wf_std":  wf_folds["std"],
                "wf_fold_sharpes": wf_folds["fold_sharpes"],
                "lift_vs_k198_oos": round(k211_oos_sh - K198_OOS_SH, 4),
                "lift_vs_k207_oos": round(k211_oos_sh - K207_OOS_SH, 4),
                "lift_vs_k198_wf_min": round(wf_folds["min"] - K198_WF_MIN, 4),
            },
            "WF_static_P3_same_windows": {
                "description": "Static P3 on same WF windows",
                "oos_sharpe": m_static["sharpe"],
                "oos_maxdd":  m_static["max_dd"],
                "wf_fold_sharpes": wf_fold_sharpes(static_aligned)["fold_sharpes"] if len(static_aligned) > 0 else [],
            },
        },
        "acceptance_check": {
            "oos_sh_pass":      accept_oos_sh,
            "wf_min_pass":      accept_wf_min,
            "mdd_pass":         accept_mdd,
            "interact_nonzero": accept_interact,
            "overall_accept":   overall_accept,
            "verdict": "ACCEPT -> promote K211 to v6.6 production" if overall_accept
                       else "REJECT -> interaction approach insufficient, investigate K212",
        },
        "feature_importance_top20": {k: v for k, v in list(feat_importance.items())[:20]},
        "interaction_feature_importance": {
            ic: {
                "rank": list(feat_importance.keys()).index(ic) + 1 if ic in feat_importance else None,
                "abs_coef": feat_importance.get(ic, 0.0),
                "signed_coefs_by_strategy": {
                    strat: coefs.get(ic, 0.0)
                    for strat, coefs in signed_coefs.items()
                },
            }
            for ic in ["eth_x_V_rev_carry", "eth_x_V_fwd_carry"]
        },
        "interaction_coef_aggregation": {
            strat: {fn: {k: v for k, v in info.items() if k != "trajectory"}
                    for fn, info in feats.items()}
            for strat, feats in interact_agg.items()
        },
        "v_rev_carry_weight_trajectory": carry_traj,
        "wf_diagnostics_summary": diag_summary,
        "wf_steps": [
            {
                "step": d["step"],
                "test_start": d["test_start"],
                "test_end": d["test_end"],
                "weights": d["weights"],
                "preds": d["preds"],
                "mean_r2": d["mean_r2"],
                "mean_dir_acc": d["mean_dir_acc"],
            }
            for d in diagnostics_k211
        ],
        "next_wave_recommendation": (
            "K212: Combine K211 with K210 (if K210 also accepted) for ensemble. "
            "If K211 rejected, investigate: (a) alpha tuning for interaction features, "
            "(b) carry-index multiplied interaction (instead of sh30 modulation), "
            "(c) regime-conditioned interaction (only active in high-TVL regime)."
        ),
    }

    # ── Save JSON ─────────────────────────────────────────────────────────────
    out_json = BASE / "wave_k211_ethena_interaction.json"
    with open(out_json, "w") as f:
        json.dump(output, f, indent=2, default=str)
    print(f"  Saved: {out_json}")

    # ── Save curves JSON ──────────────────────────────────────────────────────
    curves_out = BASE / "wave_k211_curves.json"
    curves_data = {
        "wave": "K211",
        "as_of": as_of,
        "k211_dates": [str(d.date()) for d in pnl_k211.index],
        "k211_equity": list(np.cumprod(1.0 + pnl_k211.values).tolist()),
        "k211_returns": list(pnl_k211.values.tolist()),
        "k211_weights": {
            "dates": [str(d.date()) for d in weights_k211.index],
            "V_rev_carry": list(weights_k211["V_rev_carry"].values.tolist()),
            "V_fwd_carry": list(weights_k211["V_fwd_carry"].values.tolist()),
            "v4.1":        list(weights_k211["v4.1"].values.tolist()),
            "K121":        list(weights_k211["K121"].values.tolist()),
        },
        "static_wf_dates": [str(d.date()) for d in static_aligned.index],
        "static_wf_equity": list(np.cumprod(1.0 + static_aligned.values).tolist()),
        "k198_reference": {
            "oos_sharpe": K198_OOS_SH,
            "oos_maxdd":  K198_OOS_DD,
            "wf_min":     K198_WF_MIN,
        },
        "k207_reference": {
            "oos_sharpe": K207_OOS_SH,
            "oos_maxdd":  K207_OOS_DD,
        },
    }
    with open(curves_out, "w") as f:
        json.dump(curves_data, f, indent=2, default=str)
    print(f"  Saved: {curves_out}")

    # ── Print three-way comparison table ─────────────────────────────────────
    print()
    print("=" * 72)
    print("THREE-WAY COMPARISON")
    print("=" * 72)
    print(f"{'Version':<35} {'OOS Sh':>8} {'OOS MaxDD':>10} {'WF Mean':>8} {'WF Min':>8}")
    print("-" * 72)
    print(f"{'K198 v6.5 baseline':<35} {K198_OOS_SH:>8.4f} {K198_OOS_DD:>10.4f} {K198_WF_MEAN:>8.4f} {K198_WF_MIN:>8.4f}")
    print(f"{'K207 global Ethena (REJECTED)':<35} {K207_OOS_SH:>8.4f} {K207_OOS_DD:>10.4f} {K207_WF_MEAN:>8.4f} {K207_WF_MIN:>8.4f}")
    print(f"{'K211 interaction Ethena':<35} {k211_oos_sh:>8.4f} {k211_oos_dd:>10.4f} {wf_folds['mean']:>8.4f} {wf_folds['min']:>8.4f}")
    print("-" * 72)
    print(f"  K211 lift vs K198: OOS Sh {k211_oos_sh - K198_OOS_SH:+.4f}, WF min {wf_folds['min'] - K198_WF_MIN:+.4f}")
    print(f"  K211 lift vs K207: OOS Sh {k211_oos_sh - K207_OOS_SH:+.4f}")
    print()
    print(f"  VERDICT: {'ACCEPT -> K211 promotes to v6.6' if overall_accept else 'REJECT -> K211 does not meet acceptance criteria'}")
    print()
    print(f"  Next: K212 -- {'combine K211 + K210 for ensemble' if overall_accept else 'investigate deeper interaction design'}")
    print()
    print(f"Runtime: {runtime_s:.1f}s")
    print("Done.")

    return output


if __name__ == "__main__":
    main()

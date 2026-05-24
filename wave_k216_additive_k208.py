"""Wave K216 — Additive K208-Filtered V_rev_carry as 11th Component (v6.6 Candidate).

Objective:
  Add K208-filtered V_rev_carry as an ADDITIVE 11th component to K198's existing 10.
  Leave all K198 components UNCHANGED so Ridge ML's learned weights are not disrupted.

Key design principle:
  - K198's 10 components are loaded identically to K198 production
  - V_rev_carry_filtered is added as NEW slot #11 using K208 DAR(2,1) daily panel
  - Ridge ML now operates on 11-component feature matrix (55 features)
  - Two correlated V_rev_carry components coexist; Ridge learns to weight them

Caps:
  - K121 ≤ 30%
  - V_fwd_carry ≤ 5%
  - V_rev_carry (unfiltered) ≤ 5%
  - V_rev_carry_filtered ≤ 5%
  - Total carry sleeve (V_fwd + V_rev + V_rev_filtered) ≤ 15%

Walk-forward: 90d train → 30d test, 15 steps (same as K198)

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
BASE     = Path("/Users/nekonaomichi/crypto-lab")
CACHE    = BASE / "cache"
HL_CACHE = CACHE / "k163_hl"

TRADING_DAYS   = 365
EVENTS_PER_DAY = 3
EVENTS_PER_YEAR = TRADING_DAYS * EVENTS_PER_DAY

OOS_FRAC   = 0.30
N_FOLDS    = 4
TRAIN_FRAC = 0.70

# ML walk-forward params (identical to K198)
ML_TRAIN_DAYS = 90
ML_TEST_DAYS  = 30

# Reference baselines
K198_OOS_SH  = 10.28
K198_OOS_DD  = -0.0053
K198_WF_MEAN = 7.91
K198_WF_MIN  = 6.57

# Caps (K216 extended)
K121_CAP              = 0.30
CARRY_FWD_CAP         = 0.05   # individual cap
CARRY_REV_CAP         = 0.05   # unfiltered individual cap
CARRY_REV_FILT_CAP    = 0.05   # filtered individual cap
CARRY_SLEEVE_CAP      = 0.15   # combined fwd + rev + rev_filtered cap

# FR defensive trigger (same as K198)
FR_SYMBOLS    = ["BTC", "ETH", "DOGE", "AVAX", "SOL", "XRP"]
FR_THRESHOLD  = -0.009735
FR_COMPONENTS = ["K121", "K133"]

# DAR config (same as K208)
DAR_P     = 2
DAR_Q     = 1
DAR_WIN   = 300
DAR_REFIT = 50

# K208 reverse carry symbols
REVERSE_9  = ["SOL", "XRP", "SUI", "OP", "APT", "JTO", "IMX", "SAND", "ADA"]
AXS_ALWAYS = ["AXS"]
REVERSE_10 = REVERSE_9 + AXS_ALWAYS

# 11-component strategy names
STRATEGY_NAMES = [
    "v4.1", "V1", "K114", "K116", "K121", "K133",
    "K147", "K175_DAR", "V_fwd_carry", "V_rev_carry",
    "V_rev_carry_filtered",   # NEW: 11th component
]


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
    """Apply K216 caps: K121 ≤30%, each carry ≤5%, total carry sleeve ≤15%."""
    w = apply_cap(w, cols, "K121", K121_CAP)
    w = apply_cap(w, cols, "V_fwd_carry", CARRY_FWD_CAP)
    w = apply_cap(w, cols, "V_rev_carry", CARRY_REV_CAP)
    w = apply_cap(w, cols, "V_rev_carry_filtered", CARRY_REV_FILT_CAP)

    # Combined carry sleeve cap
    carry_names = ["V_fwd_carry", "V_rev_carry", "V_rev_carry_filtered"]
    carry_idxs  = [cols.index(c) for c in carry_names if c in cols]
    if not carry_idxs:
        return w
    carry_total = sum(w[i] for i in carry_idxs)
    if carry_total > CARRY_SLEEVE_CAP:
        # Scale down proportionally
        scale = CARRY_SLEEVE_CAP / carry_total
        excess = carry_total - CARRY_SLEEVE_CAP
        non_carry_idxs = [i for i in range(len(w)) if i not in carry_idxs]
        for i in carry_idxs:
            w[i] *= scale
        # Redistribute excess to non-carry
        non_carry_total = sum(w[i] for i in non_carry_idxs)
        if non_carry_total > 1e-10:
            for i in non_carry_idxs:
                w[i] += excess * (w[i] / non_carry_total)
        w = w / w.sum()
    return w


# ──────────────────────────────────────────────────────────────────────────────
# Data loading helpers (8h panel for DAR)
# ──────────────────────────────────────────────────────────────────────────────

def load_hl_fr(sym: str) -> Optional[pd.Series]:
    f = HL_CACHE / f"hl_fr_{sym}.parquet"
    if not f.exists():
        return None
    df = pd.read_parquet(f)
    col = "hl_fr" if "hl_fr" in df.columns else df.columns[0]
    if "timestamp" in df.columns:
        df = df.set_index("timestamp")
    s = df[col].astype(float).sort_index()
    s = s[~s.index.duplicated(keep="last")]
    s.name = sym
    return s


def load_bybit_fr(sym: str) -> Optional[pd.Series]:
    for tag in ("730d", "1200d", "365d"):
        f = CACHE / f"bybit_fr_{sym}USDT_{tag}.parquet"
        if f.exists():
            df = pd.read_parquet(f)
            col = "funding_rate" if "funding_rate" in df.columns else df.columns[0]
            if "timestamp" in df.columns:
                df = df.set_index("timestamp")
            s = df[col].astype(float).sort_index()
            s = s[~s.index.duplicated(keep="last")]
            s.name = sym
            return s
    return None


def build_panel_8h(sym: str) -> Optional[pd.DataFrame]:
    hl = load_hl_fr(sym)
    by = load_bybit_fr(sym)
    if hl is None or by is None:
        return None
    hl_8h = hl.resample("8h", label="right", closed="right").sum(min_count=1)
    idx = by.index
    df = pd.DataFrame({"bybit_fr": by}, index=idx)
    df["hl_fr_8h"] = hl_8h.reindex(idx)
    df = df.dropna()
    if len(df) < 50:
        return None
    df["spread"] = df["bybit_fr"] - df["hl_fr_8h"]
    df["rev_carry_pnl"] = df["spread"].shift(-1)
    df = df.dropna(subset=["rev_carry_pnl"])
    if len(df) < 50:
        return None
    return df


# ──────────────────────────────────────────────────────────────────────────────
# DAR(2,1) model (same as K208/K210)
# ──────────────────────────────────────────────────────────────────────────────

def _ols_fit(X: np.ndarray, y: np.ndarray) -> np.ndarray:
    try:
        coeffs, _, _, _ = np.linalg.lstsq(X, y, rcond=None)
        return coeffs
    except Exception:
        return np.zeros(X.shape[1])


def build_dar_design(
    fr_arr: np.ndarray,
    spread_z_arr: np.ndarray,
    p: int,
    q: int,
    idx: int,
) -> Optional[np.ndarray]:
    if idx < max(p, q):
        return None
    row = [1.0]
    for lag in range(1, p + 1):
        row.append(fr_arr[idx - lag])
    for lag in range(1, q + 1):
        row.append(spread_z_arr[idx - lag])
    return np.array(row, dtype=float)


def zscore_rolling(s: pd.Series, win: int = 30) -> pd.Series:
    mu = s.rolling(win, min_periods=win).mean()
    sd = s.rolling(win, min_periods=win).std()
    return (s - mu) / (sd + 1e-12)


def dar_walk_forward(
    fr: np.ndarray,
    spread_z: np.ndarray,
    p: int = DAR_P,
    q: int = DAR_Q,
    win: int = DAR_WIN,
    refit: int = DAR_REFIT,
) -> Tuple[np.ndarray, np.ndarray, Dict]:
    n = len(fr)
    pred_fr  = np.full(n, np.nan)
    is_valid = np.zeros(n, dtype=bool)
    min_lag  = max(p, q)
    coeffs   = None

    for i in range(min_lag + win, n):
        if (i - (min_lag + win)) % refit == 0 or coeffs is None:
            start = i - win
            rows, targets = [], []
            for t in range(start + min_lag, i):
                row = build_dar_design(fr, spread_z, p, q, t)
                if row is None:
                    continue
                rows.append(row)
                targets.append(fr[t])
            if len(rows) < p + q + 10:
                continue
            X = np.array(rows, dtype=float)
            y = np.array(targets, dtype=float)
            coeffs = _ols_fit(X, y)

        if coeffs is not None:
            row = build_dar_design(fr, spread_z, p, q, i - 1)
            if row is not None:
                pred_fr[i]  = float(np.dot(row, coeffs))
                is_valid[i] = True

    valid_idx = np.where(is_valid)[0]
    if len(valid_idx) < 30:
        return pred_fr, is_valid, {"oos_r2": float("nan"), "direction_acc": float("nan"), "n_oos": 0}

    y_true = fr[valid_idx]
    y_pred  = pred_fr[valid_idx]
    ss_res  = np.sum((y_true - y_pred) ** 2)
    ss_tot  = np.sum((y_true - y_true.mean()) ** 2)
    oos_r2  = float(1 - ss_res / (ss_tot + 1e-30))

    actual_delta = np.diff(y_true)
    pred_sign    = np.sign(y_pred[1:] - y_true[:-1])
    actual_sign  = np.sign(actual_delta)
    nz = actual_sign != 0
    dir_acc = float((pred_sign[nz] == actual_sign[nz]).mean()) if nz.sum() > 0 else 0.5

    return pred_fr, is_valid, {
        "oos_r2": round(oos_r2, 5),
        "direction_acc": round(dir_acc, 4),
        "n_oos": int(len(valid_idx)),
    }


# ──────────────────────────────────────────────────────────────────────────────
# Build K208-filtered V_rev_carry daily series (11th component)
# ──────────────────────────────────────────────────────────────────────────────

def build_k208_filtered_daily() -> Tuple[pd.Series, dict]:
    """
    Build K208 DAR(2,1) filtered reverse carry as daily return series.

    For REVERSE_9: apply DAR(2,1) gate (pred_spread > 0, lagged by 1).
    For AXS: always-on (no DAR filter).
    Aggregate: equal weight across 10 symbols → mean daily PnL.
    Return: daily PnL series (same scale as K196 V_rev_carry daily returns).
    """
    per_sym_daily: Dict[str, pd.Series] = {}
    dar_diag:      Dict[str, dict] = {}
    filter_stats:  Dict[str, dict] = {}

    for sym in REVERSE_10:
        df = build_panel_8h(sym)
        if df is None:
            print(f"    SKIP {sym}: panel build failed")
            continue

        if sym in AXS_ALWAYS:
            daily_pnl = df["rev_carry_pnl"].resample("1D").sum(min_count=1).fillna(0.0)
            per_sym_daily[sym] = daily_pnl
            dar_diag[sym]      = {"note": "always-on", "direction_acc": float("nan")}
            filter_stats[sym]  = {"pct_in_market": 100.0, "filter_rate_pct": 0.0}
        else:
            fr_arr   = df["bybit_fr"].values.copy()
            spread_z = zscore_rolling(df["spread"], 30).fillna(0.0).values
            hl_arr   = df["hl_fr_8h"].values.copy()

            pred_fr, is_valid, diag = dar_walk_forward(fr_arr, spread_z)
            dar_diag[sym] = diag

            gate = np.zeros(len(df), dtype=bool)
            for i in range(len(df)):
                if not is_valid[i]:
                    continue
                if pred_fr[i] - hl_arr[i] > 0:
                    gate[i] = True

            gate_series = pd.Series(gate, index=df.index)
            gate_lagged = gate_series.shift(1).fillna(False)

            base_pnl     = df["rev_carry_pnl"].copy()
            filtered_pnl = base_pnl.where(gate_lagged, 0.0)
            daily_pnl    = filtered_pnl.resample("1D").sum(min_count=1).fillna(0.0)
            per_sym_daily[sym] = daily_pnl

            n_total  = int((~base_pnl.isna()).sum())
            n_active = int((gate_lagged & ~base_pnl.isna()).sum())
            pct_in   = round(100 * n_active / max(n_total, 1), 1)
            filter_stats[sym] = {
                "n_total_events": n_total,
                "n_active_filtered": n_active,
                "pct_in_market": pct_in,
                "filter_rate_pct": round(100 - pct_in, 1),
            }
            dir_acc_val = diag.get("direction_acc", float("nan"))
            dir_str = f"{dir_acc_val:.4f}" if not (isinstance(dir_acc_val, float) and math.isnan(dir_acc_val)) else "nan"
            print(f"    {sym}: dir_acc={dir_str}  in_market={pct_in:.0f}%")

    if not per_sym_daily:
        raise RuntimeError("No daily panels built for K208 filtered")

    aligned     = pd.concat(per_sym_daily, axis=1).fillna(0.0)
    panel_daily = aligned.mean(axis=1)
    panel_daily.name = "V_rev_carry_filtered"

    avg_filter = float(np.mean([s.get("filter_rate_pct", 0) for s in filter_stats.values()]))
    metadata = {
        "dar_diag": dar_diag,
        "filter_stats": filter_stats,
        "avg_filter_pct": round(avg_filter, 1),
        "avg_in_market_pct": round(100 - avg_filter, 1),
        "n_symbols": len(per_sym_daily),
        "date_range": [str(panel_daily.index[0].date()), str(panel_daily.index[-1].date())],
        "n_days": int(len(panel_daily)),
    }
    return panel_daily, metadata


# ──────────────────────────────────────────────────────────────────────────────
# Component returns loading (K198 10 components, unchanged)
# ──────────────────────────────────────────────────────────────────────────────

def load_k198_components() -> pd.DataFrame:
    """
    Load all 10 K198 components IDENTICALLY to K198 production.
    Components: v4.1, V1, K114, K116, K121, K133, K147, K175_DAR (from K192)
                V_fwd_carry (K195), V_rev_carry (K196)
    """
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
    k195_dates = pd.to_datetime(k195["panel_dates"])
    fwd_eq  = np.array(k195["series"]["V_eq_w"], dtype=float)
    fwd_ret = pd.Series(
        np.r_[fwd_eq[0] - 1.0, fwd_eq[1:] / fwd_eq[:-1] - 1.0],
        index=k195_dates,
        name="V_fwd_carry",
    )

    with open(BASE / "wave_k196_curves.json") as f:
        k196 = json.load(f)
    k196_dates = pd.to_datetime(k196["panel_dates"])
    rev_eq  = np.array(k196["series"]["V_rev_eq_w"], dtype=float)
    rev_ret = pd.Series(
        np.r_[rev_eq[0] - 1.0, rev_eq[1:] / rev_eq[:-1] - 1.0],
        index=k196_dates,
        name="V_rev_carry",
    )

    all_start = max(base_df.index[0], fwd_ret.index[0], rev_ret.index[0])
    all_end   = min(base_df.index[-1], fwd_ret.index[-1], rev_ret.index[-1])

    base_trimmed = base_df[(base_df.index >= all_start) & (base_df.index <= all_end)]
    fwd_trimmed  = fwd_ret[(fwd_ret.index >= all_start)  & (fwd_ret.index <= all_end)]
    rev_trimmed  = rev_ret[(rev_ret.index >= all_start)  & (rev_ret.index <= all_end)]

    df = pd.concat([base_trimmed, fwd_trimmed, rev_trimmed], axis=1).dropna()
    return df


# ──────────────────────────────────────────────────────────────────────────────
# FR regime indicator
# ──────────────────────────────────────────────────────────────────────────────

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
# Feature engineering (11 strategies × 5 features + 1 FR = 56 features)
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
            row[f"{prefix}sh30"]   = sharpe_d(slice_short[:, i])
            row[f"{prefix}sh90"]   = sharpe_d(slice_long[:, i])
            row[f"{prefix}vol30"]  = float(slice_short[:, i].std(ddof=1) * math.sqrt(TRADING_DAYS))
            row[f"{prefix}mdd30"]  = max_dd_d(slice_short[:, i])
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
# ML Walk-forward (Ridge, 11 components)
# ──────────────────────────────────────────────────────────────────────────────

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

    common_idx     = feat_df.index.intersection(target_df.index)
    feat_aligned   = feat_df.loc[common_idx]
    target_aligned = target_df.loc[common_idx]

    feat_arr   = feat_aligned.values
    target_arr = np.array([target_aligned[f"{c}__fwd_sh"].values for c in cols]).T
    date_idx   = feat_aligned.index

    n = len(feat_arr)

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

        t_test_start = t_start
        t_test_end   = min(t_start + test_days, n)
        X_test       = feat_arr[t_test_start:t_test_end]
        test_dates_slice = date_idx[t_test_start:t_test_end]

        if len(X_train) < 20 or len(X_test) == 0:
            step += 1
            continue

        X_train = np.nan_to_num(X_train, nan=0.0, posinf=0.0, neginf=0.0)
        X_test  = np.nan_to_num(X_test,  nan=0.0, posinf=0.0, neginf=0.0)

        scaler    = StandardScaler()
        X_train_s = scaler.fit_transform(X_train)
        X_test_s  = scaler.transform(X_test)

        preds     = np.zeros(n_strats)
        r2_scores = []
        ridge_coefs = np.zeros((n_strats, X_train_s.shape[1]))

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
            ridge_coefs[i] = model.coef_
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
            "preds":    {cols[i]: round(float(preds[i]), 4) for i in range(n_strats)},
            "weights":  {cols[i]: round(float(w[i]), 4) for i in range(n_strats)},
            "r2_per_strat": {cols[i]: round(float(r2_scores[i]), 4)
                             if not (isinstance(r2_scores[i], float) and math.isnan(r2_scores[i])) else None
                             for i in range(n_strats)},
            "dir_accuracy_per_strat": {cols[i]: bool(dir_correct[i]) for i in range(n_strats)},
            "mean_r2":      round(float(np.nanmean(r2_scores)), 4),
            "mean_dir_acc": round(float(np.mean(dir_correct)), 4),
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


# ──────────────────────────────────────────────────────────────────────────────
# Walk-forward fold Sharpe statistics
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


def oos_cut(s: pd.Series, frac: float = OOS_FRAC) -> pd.Series:
    cut = int(len(s) * (1 - frac))
    return s.iloc[cut:]


# ──────────────────────────────────────────────────────────────────────────────
# Weight evolution analysis
# ──────────────────────────────────────────────────────────────────────────────

def compute_weight_evolution(
    weights_df_k198: pd.DataFrame,
    weights_df_k216: pd.DataFrame,
    cols_k198: List[str],
    cols_k216: List[str],
) -> dict:
    """Compare per-component weight statistics K198 vs K216."""
    result = {}
    for c in cols_k216:
        w216 = weights_df_k216[c].values if c in weights_df_k216.columns else np.array([0.0])
        w198 = weights_df_k198[c].values if c in weights_df_k198.columns else np.array([0.0])
        result[c] = {
            "k216_mean":    round(float(np.mean(w216)), 4),
            "k216_min":     round(float(np.min(w216)),  4),
            "k216_max":     round(float(np.max(w216)),  4),
            "k216_nonzero_pct": round(float(np.mean(w216 > 0.001)) * 100, 1),
            "k198_mean":    round(float(np.mean(w198)), 4) if len(w198) > 1 else None,
            "k198_max":     round(float(np.max(w198)),  4) if len(w198) > 1 else None,
            "delta_mean":   round(float(np.mean(w216) - np.mean(w198)), 4) if len(w198) > 1 else None,
        }
    return result


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


# ──────────────────────────────────────────────────────────────────────────────
# Lift attribution
# ──────────────────────────────────────────────────────────────────────────────

def compute_lift_attribution(
    weights_df: pd.DataFrame,
    df: pd.DataFrame,
    pnl_k216: pd.Series,
) -> dict:
    """
    Estimate how much OOS Sh is attributable to V_rev_carry_filtered.
    Method: counter-factual — zero out V_rev_carry_filtered weight and redistribute,
    recompute OOS Sharpe, compare.
    """
    cols = list(df.columns)
    if "V_rev_carry_filtered" not in cols:
        return {"error": "V_rev_carry_filtered not in columns"}

    # Rebuild PnL without V_rev_carry_filtered
    no_filt_pnl = []
    for idx in weights_df.index:
        if idx not in df.index:
            continue
        w = weights_df.loc[idx].values.copy()
        filt_idx = cols.index("V_rev_carry_filtered")
        excess   = w[filt_idx]
        w[filt_idx] = 0.0
        other_mask = np.ones(len(w), dtype=bool)
        other_mask[filt_idx] = False
        others = w[other_mask]
        if others.sum() > 1e-10:
            w[other_mask] = others + excess * (others / others.sum())
        if w.sum() > 1e-10:
            w = w / w.sum()
        ret = df.loc[idx].values
        no_filt_pnl.append(float(ret @ w))

    no_filt_series = pd.Series(no_filt_pnl, index=weights_df.index[:len(no_filt_pnl)])
    oos_k216  = oos_cut(pnl_k216)
    oos_nofilt = oos_cut(no_filt_series)
    sh_k216    = sharpe_d(oos_k216.values)
    sh_nofilt  = sharpe_d(oos_nofilt.values)

    return {
        "oos_sh_k216":          round(sh_k216, 4),
        "oos_sh_without_filt":  round(sh_nofilt, 4),
        "lift_from_filt":       round(sh_k216 - sh_nofilt, 4),
        "lift_pct":             round((sh_k216 - sh_nofilt) / abs(sh_nofilt) * 100, 2) if abs(sh_nofilt) > 0.01 else 0.0,
    }


# ──────────────────────────────────────────────────────────────────────────────
# Main
# ──────────────────────────────────────────────────────────────────────────────

def main():
    print("=" * 72)
    print("Wave K216 — Additive K208-Filtered 11th Component (v6.6 Candidate)")
    print("=" * 72)
    print()

    np.random.seed(42)

    # ── Step 1: Build K208-filtered V_rev_carry (11th component) ─────────────
    print("Step 1: Building K208-filtered V_rev_carry (DAR(2,1) per-symbol)...", flush=True)
    filt_daily, filt_metadata = build_k208_filtered_daily()
    print(f"  K208 filtered: {filt_metadata['n_days']} days  "
          f"{filt_metadata['date_range'][0]} → {filt_metadata['date_range'][1]}")
    print(f"  Avg events filtered: {filt_metadata['avg_filter_pct']}%  "
          f"in-market: {filt_metadata['avg_in_market_pct']}%")
    print()

    # ── Step 2: Load K198 10 components (UNCHANGED) ───────────────────────────
    print("Step 2: Loading K198 10 components (unchanged)...", flush=True)
    df_k198 = load_k198_components()
    print(f"  K198 10 components: {df_k198.shape[0]} days × {df_k198.shape[1]} strategies")
    print(f"  Date range: {df_k198.index[0].date()} → {df_k198.index[-1].date()}")
    print()

    # ── Step 3: Add 11th component (V_rev_carry_filtered) ────────────────────
    print("Step 3: Adding V_rev_carry_filtered as 11th component...", flush=True)

    # Align filtered daily with K198's date range
    filt_aligned = filt_daily.reindex(df_k198.index, method="ffill").fillna(0.0)

    df_k216 = df_k198.copy()
    df_k216["V_rev_carry_filtered"] = filt_aligned.values

    # Find common valid range
    df_k216 = df_k216.dropna()
    print(f"  K216 11 components: {df_k216.shape[0]} days × {df_k216.shape[1]} strategies")
    print(f"  Strategy list: {list(df_k216.columns)}")
    cols_k216 = list(df_k216.columns)
    print()

    # ── Step 4: Correlation between unfiltered and filtered V_rev_carry ────────
    print("Step 4: Correlation analysis (unfiltered vs filtered V_rev_carry)...", flush=True)
    rev_unf = df_k216["V_rev_carry"].values
    rev_filt = df_k216["V_rev_carry_filtered"].values
    corr_rev = float(np.corrcoef(rev_unf, rev_filt)[0, 1])
    print(f"  V_rev_carry (unfiltered) vs V_rev_carry_filtered correlation: {corr_rev:.4f}")
    print(f"  V_rev_carry std: {rev_unf.std():.6f}  filtered std: {rev_filt.std():.6f}")
    print(f"  Std ratio (filtered/unfiltered): {rev_filt.std() / max(rev_unf.std(), 1e-10):.4f}")
    print()

    # ── Step 5: Load FR regime indicator ─────────────────────────────────────
    print("Step 5: Loading FR regime indicator...", flush=True)
    fr_mean = load_fr_mean_daily()
    if len(fr_mean) > 0:
        print(f"  FR range: {fr_mean.index[0].date()} → {fr_mean.index[-1].date()}")
    else:
        print("  WARNING: FR data not available")
    print()

    # ── Step 6: Apply FR trigger ──────────────────────────────────────────────
    print("Step 6: Applying FR trigger (K121, K133 zeroed when FR < threshold)...", flush=True)
    if len(fr_mean) > 0:
        df_triggered = apply_fr_trigger(df_k216, fr_mean)
        fr_aligned   = fr_mean.reindex(df_k216.index, method="ffill")
        n_trigger    = int((fr_aligned < FR_THRESHOLD).sum())
        print(f"  Trigger fires {n_trigger}/{len(df_k216)} days ({n_trigger/len(df_k216)*100:.1f}%)")
    else:
        df_triggered = df_k216.copy()
        print("  No FR trigger applied")
    print()

    # ── Step 7: Build feature matrix (11×5 + 1 = 56 features) ───────────────
    print("Step 7: Building ML feature matrix (11 strategies × 5 + 1 FR)...", flush=True)
    feat_df = build_features(df_triggered, fr_mean if len(fr_mean) > 0 else None)
    print(f"  Feature matrix: {feat_df.shape[0]} rows × {feat_df.shape[1]} features")
    print()

    # ── Step 8: Build targets ─────────────────────────────────────────────────
    print("Step 8: Building forward Sharpe targets...", flush=True)
    target_df = build_targets(df_triggered, horizon=ML_TEST_DAYS)
    print(f"  Target matrix: {target_df.shape[0]} rows × {target_df.shape[1]} cols")
    print()

    # ── Step 9: Ridge walk-forward (11 components) ───────────────────────────
    print("Step 9: Ridge walk-forward (90d train → 30d test, 11 components)...", flush=True)
    weights_k216, pnl_k216, diagnostics_k216 = ml_walk_forward(
        df_triggered, feat_df, target_df,
        train_days=ML_TRAIN_DAYS,
        test_days=ML_TEST_DAYS,
        alpha=1.0,
    )
    if len(pnl_k216) == 0:
        print("  ERROR: Ridge walk-forward returned empty PnL")
        return
    print(f"  K216 Ridge PnL: {len(pnl_k216)} days  "
          f"{pnl_k216.index[0].date()} → {pnl_k216.index[-1].date()}")
    n_wf_steps = len(diagnostics_k216)
    print(f"  WF steps: {n_wf_steps}")
    print()

    # ── Step 10: OOS metrics ──────────────────────────────────────────────────
    print("Step 10: Computing OOS metrics (last 30%)...", flush=True)
    oos_pnl   = oos_cut(pnl_k216)
    m_k216    = metrics_pkg(oos_pnl.values)
    wf_k216   = wf_fold_sharpes(pnl_k216)

    print(f"  K198 v6.5 baseline:   OOS Sh={K198_OOS_SH:.4f} MaxDD={K198_OOS_DD:.4f} "
          f"WF_mean={K198_WF_MEAN:.2f} WF_min={K198_WF_MIN:.2f}")
    print(f"  K216 additive 11th:   OOS Sh={m_k216['sharpe']:.4f} MaxDD={m_k216['max_dd']:.4f} "
          f"WF_mean={wf_k216['mean']:.2f} WF_min={wf_k216['min']:.2f}")
    print(f"  Δ vs K198:            OOS Sh {m_k216['sharpe']-K198_OOS_SH:+.4f} "
          f"MaxDD {m_k216['max_dd']-K198_OOS_DD:+.4f} "
          f"WF_min {wf_k216['min']-K198_WF_MIN:+.4f}")
    print()

    # ── Step 11: Weight evolution analysis ───────────────────────────────────
    print("Step 11: Weight evolution analysis...", flush=True)
    # Load K198 weights for comparison
    with open(BASE / "wave_k198_curves.json") as f:
        k198_curves = json.load(f)
    k198_wt_raw = k198_curves.get("weight_trajectory", {})
    k198_wt_dates = k198_curves.get("weight_trajectory_dates", [])
    weights_k198_df = pd.DataFrame(k198_wt_raw, index=pd.to_datetime(k198_wt_dates))

    weight_evolution = compute_weight_evolution(
        weights_k198_df, weights_k216, list(weights_k198_df.columns), cols_k216
    )

    print(f"  {'Component':<25} {'K216 mean':>10} {'K216 max':>10} {'Non-zero%':>10} {'K198 mean':>10} {'Delta':>10}")
    print(f"  {'-'*75}")
    for c in cols_k216:
        ev = weight_evolution.get(c, {})
        k198m = ev.get("k198_mean")
        delta = ev.get("delta_mean")
        k198m_str = f"{k198m:10.4f}" if k198m is not None else "        N/A"
        delta_str  = f"{delta:10.4f}" if delta is not None else "        N/A"
        print(f"  {c:<25} {ev.get('k216_mean', 0):10.4f} {ev.get('k216_max', 0):10.4f} "
              f"{ev.get('k216_nonzero_pct', 0):9.1f}% "
              f"{k198m_str} "
              f"{delta_str}")
    print()

    # Verify all K198 components have non-zero weights
    k198_10_names = ["v4.1", "V1", "K114", "K116", "K121", "K133",
                     "K147", "K175_DAR", "V_fwd_carry", "V_rev_carry"]
    nonzero_check = {c: weight_evolution.get(c, {}).get("k216_nonzero_pct", 0.0) > 5.0
                     for c in k198_10_names}
    all_10_nonzero = all(nonzero_check.values())
    filt_nonzero   = weight_evolution.get("V_rev_carry_filtered", {}).get("k216_nonzero_pct", 0.0) > 5.0
    print(f"  All K198 10 components have non-zero weights: {all_10_nonzero}")
    print(f"  V_rev_carry_filtered has non-zero weight: {filt_nonzero}")
    print()

    # ── Step 12: Lift attribution ──────────────────────────────────────────────
    print("Step 12: Lift attribution from V_rev_carry_filtered...", flush=True)
    lift_attr = compute_lift_attribution(weights_k216, df_triggered, pnl_k216)
    print(f"  OOS Sh with V_rev_carry_filtered: {lift_attr.get('oos_sh_k216', 0):.4f}")
    print(f"  OOS Sh without V_rev_carry_filtered: {lift_attr.get('oos_sh_without_filt', 0):.4f}")
    print(f"  Lift from 11th component: {lift_attr.get('lift_from_filt', 0):+.4f}")
    print()

    # ── Step 13: Diagnostics aggregation ─────────────────────────────────────
    print("Step 13: ML predictor diagnostics...", flush=True)
    diag_agg = aggregate_diagnostics(diagnostics_k216, cols_k216)
    print(f"  Overall mean R²: {diag_agg.get('overall_mean_r2', 'N/A')}")
    print(f"  Overall dir acc: {diag_agg.get('overall_mean_dir_acc', 'N/A')}")
    print()

    # ── Step 14: Acceptance criteria ─────────────────────────────────────────
    print("Step 14: Evaluating acceptance criteria...", flush=True)
    oos_sh  = m_k216["sharpe"]
    oos_dd  = m_k216["max_dd"]
    wf_min  = wf_k216["min"]
    wf_mean = wf_k216["mean"]

    ac1 = oos_sh >= K198_OOS_SH + 0.05        # OOS Sh ≥ K198 + 0.05
    ac2 = oos_dd >= K198_OOS_DD               # MaxDD ≤ K198 (not worsened)
    ac3 = wf_min >= K198_WF_MIN               # WF min ≥ K198 (6.57)
    ac4 = all_10_nonzero                       # All K198 components retain non-zero weights
    ac5 = filt_nonzero                         # K208-filtered has non-zero Ridge coefficient

    n_ac_pass = sum([ac1, ac2, ac3, ac4, ac5])

    print(f"  AC1: OOS Sh ≥ {K198_OOS_SH+0.05:.2f} (K198+0.05)?  "
          f"K216={oos_sh:.4f} → {'PASS' if ac1 else 'FAIL'}")
    print(f"  AC2: MaxDD not worsened?           "
          f"K216={oos_dd:.4f} vs K198={K198_OOS_DD:.4f} → {'PASS' if ac2 else 'FAIL'}")
    print(f"  AC3: WF min ≥ {K198_WF_MIN:.2f}?              "
          f"K216={wf_min:.4f} → {'PASS' if ac3 else 'FAIL'}")
    print(f"  AC4: All K198 components non-zero? → {'PASS' if ac4 else 'FAIL'}")
    print(f"  AC5: V_rev_carry_filtered non-zero? → {'PASS' if ac5 else 'FAIL'}")
    print(f"  Total: {n_ac_pass}/5 criteria pass")
    print()

    # ── Step 15: Verdict ──────────────────────────────────────────────────────
    print("Step 15: Final verdict...", flush=True)
    dd_worsening_pct = abs((oos_dd - K198_OOS_DD) / K198_OOS_DD) * 100 if K198_OOS_DD != 0 else 0.0

    if all([ac1, ac2, ac3, ac4, ac5]):
        verdict = (
            f"ACCEPT → K216 v6.6: All 5 criteria pass. "
            f"OOS Sh={oos_sh:.2f} (+{oos_sh-K198_OOS_SH:+.2f} vs K198), "
            f"WF min={wf_min:.2f}, MaxDD={oos_dd:.4f}. "
            f"K208-filtered V_rev_carry adds lift as 11th component."
        )
        deploy_action = "promote_to_v6.6"
    elif sum([ac1, ac2, ac3]) >= 2 and ac4 and ac5:
        verdict = (
            f"CONDITIONAL ACCEPT: {n_ac_pass}/5 criteria pass. "
            f"OOS Sh={oos_sh:.2f} ({oos_sh-K198_OOS_SH:+.2f} vs K198), "
            f"WF min={wf_min:.2f} vs K198={K198_WF_MIN:.2f}. "
            f"11th component has non-zero weight (ensemble intact). "
            f"Marginal improvement — consider 30-day paper-trade before production."
        )
        deploy_action = "conditional_paper_trade"
    elif not ac1 and all([ac2, ac3, ac4, ac5]):
        verdict = (
            f"REJECT for promotion: OOS Sh={oos_sh:.2f} misses {K198_OOS_SH+0.05:.2f} hurdle. "
            f"Two correlated V_rev_carry components competing for weight without additive lift. "
            f"K198 v6.5 remains production."
        )
        deploy_action = "reject_keep_k198"
    else:
        verdict = (
            f"REJECT: K216 fails {5-n_ac_pass}/5 criteria. "
            f"OOS Sh={oos_sh:.2f}, WF min={wf_min:.2f}, MaxDD={oos_dd:.4f}. "
            f"K198 v6.5 remains production."
        )
        deploy_action = "reject_keep_k198"

    print(f"  VERDICT: {verdict}")
    print()

    elapsed = time.time() - START_TIME
    print(f"Total runtime: {elapsed:.1f}s")

    # ── Step 16: Build equity curves ──────────────────────────────────────────
    k216_equity = np.cumprod(1.0 + pnl_k216.values).tolist()
    k198_equity = k198_curves.get("equity_ridge", [])
    k198_dates_list = k198_curves.get("dates_ml", [])

    # ── Step 17: Assemble outputs ─────────────────────────────────────────────
    output_json = {
        "wave":    "K216",
        "task":    "Additive K208-filtered V_rev_carry as 11th component (v6.6 candidate)",
        "as_of":   pd.Timestamp.now(tz="UTC").isoformat(),
        "runtime_s": round(elapsed, 1),

        "config": {
            "n_strategies":         11,
            "strategies":           cols_k216,
            "k198_10_components":   k198_10_names,
            "new_11th_component":   "V_rev_carry_filtered",
            "ml_train_days":        ML_TRAIN_DAYS,
            "ml_test_days":         ML_TEST_DAYS,
            "oos_frac":             OOS_FRAC,
            "caps": {
                "K121":                  K121_CAP,
                "V_fwd_carry":           CARRY_FWD_CAP,
                "V_rev_carry":           CARRY_REV_CAP,
                "V_rev_carry_filtered":  CARRY_REV_FILT_CAP,
                "carry_sleeve_total":    CARRY_SLEEVE_CAP,
            },
            "date_range":  [str(df_k216.index[0].date()), str(df_k216.index[-1].date())],
            "n_days_total": len(df_k216),
            "n_days_ml":   len(pnl_k216),
            "n_wf_steps":  n_wf_steps,
            "ridge_alpha": 1.0,
        },

        "k208_filter_metadata": filt_metadata,

        "correlation_analysis": {
            "V_rev_carry_vs_V_rev_carry_filtered": round(corr_rev, 4),
            "V_rev_carry_std":           round(float(rev_unf.std()), 6),
            "V_rev_carry_filtered_std":  round(float(rev_filt.std()), 6),
            "std_ratio_filt_over_unfilt": round(float(rev_filt.std() / max(rev_unf.std(), 1e-10)), 4),
            "note": (
                "Correlation < 1.0 because filtered series is zero during ~60% of events. "
                "Lower std of filtered component means Ridge may upweight it proportionally."
            ),
        },

        "comparison_table": {
            "K198_v6.5_baseline": {
                "description": "K198 v6.5 Ridge ML, 10 components",
                "oos_sharpe":  K198_OOS_SH,
                "oos_maxdd":   K198_OOS_DD,
                "wf_mean":     K198_WF_MEAN,
                "wf_min":      K198_WF_MIN,
            },
            "K210b_rejected": {
                "description": "K210b V_rev_carry replacement (rejected)",
                "oos_sharpe": 8.34,
                "oos_maxdd":  -0.0050,
                "wf_mean":    7.59,
                "wf_min":     7.04,
            },
            "K214_rejected": {
                "description": "K214 hybrid V_rev_carry (rejected)",
                "oos_sharpe": 8.03,
                "oos_maxdd":  -0.0053,
                "wf_mean":    7.47,
                "wf_min":     6.92,
            },
            "K216_additive_11th": {
                "description": "K216 additive 11th component (this wave)",
                "oos_sharpe":  round(oos_sh, 4),
                "oos_maxdd":   round(oos_dd, 4),
                "oos_sortino": m_k216["sortino"],
                "oos_calmar":  m_k216["calmar"],
                "oos_ann_ret": m_k216["ann_ret"],
                "oos_ann_vol": m_k216["ann_vol"],
                "oos_n_days":  m_k216["n_days"],
                "wf_mean":     wf_k216["mean"],
                "wf_min":      wf_k216["min"],
                "wf_max":      wf_k216["max"],
                "wf_std":      wf_k216["std"],
                "wf_fold_sharpes": wf_k216["fold_sharpes"],
                "lift_vs_k198_oos":    round(oos_sh - K198_OOS_SH, 4),
                "lift_vs_k198_wf_min": round(wf_min - K198_WF_MIN, 4),
            },
        },

        "weight_evolution": weight_evolution,
        "nonzero_weight_check": {
            "all_k198_10_nonzero": all_10_nonzero,
            "per_component": nonzero_check,
            "v_rev_carry_filtered_nonzero": filt_nonzero,
        },

        "lift_attribution": lift_attr,

        "ml_diagnostics": {
            **diag_agg,
            "n_wf_steps": n_wf_steps,
        },

        "acceptance_criteria": {
            "AC1_oos_sh_pass":       ac1,
            "AC1_k198_oos_sh":       K198_OOS_SH,
            "AC1_k216_oos_sh":       round(oos_sh, 4),
            "AC1_required":          K198_OOS_SH + 0.05,
            "AC1_lift":              round(oos_sh - K198_OOS_SH, 4),
            "AC2_maxdd_pass":        ac2,
            "AC2_k198_maxdd":        K198_OOS_DD,
            "AC2_k216_maxdd":        round(oos_dd, 4),
            "AC3_wf_min_pass":       ac3,
            "AC3_required":          K198_WF_MIN,
            "AC3_k216_wf_min":       round(wf_min, 4),
            "AC4_k198_intact_pass":  ac4,
            "AC5_filt_nonzero_pass": ac5,
            "n_criteria_passed":     n_ac_pass,
            "all_pass":              all([ac1, ac2, ac3, ac4, ac5]),
        },

        "verdict": verdict,
        "deploy_action": deploy_action,

        "risk_analysis": {
            "correlated_components": (
                f"V_rev_carry and V_rev_carry_filtered correlation = {corr_rev:.3f}. "
                "Ridge regularization penalizes collinear features — may allocate weight to "
                "one or the other, not both equally. Cap structure (5% each, 15% sleeve) "
                "bounds worst-case concentration."
            ),
            "scale_asymmetry": (
                f"Filtered series std ({rev_filt.std():.6f}) << unfiltered ({rev_unf.std():.6f}). "
                "Ridge on standardized features equalizes this. Both components contribute equally "
                "to feature matrix but Ridge coefs may differ in magnitude."
            ),
            "additive_vs_replacement": (
                "K210/K214 failed because replacing V_rev_carry disrupted Ridge's learned weights. "
                "K216 preserves V_rev_carry (unfiltered) unchanged, adding filtered as new slot. "
                "Ridge re-learns from scratch with 11-component feature matrix."
            ),
            "cap_saturation": (
                f"Individual caps: V_fwd={CARRY_FWD_CAP*100:.0f}%, "
                f"V_rev={CARRY_REV_CAP*100:.0f}%, V_rev_filt={CARRY_REV_FILT_CAP*100:.0f}%. "
                f"Sleeve cap={CARRY_SLEEVE_CAP*100:.0f}%. "
                "If both rev carry components hit 5% cap simultaneously: total carry = 5+5+5=15%, "
                "which equals sleeve cap. No distortion from interaction."
            ),
        },
    }

    # Save metrics JSON
    json_path = BASE / "wave_k216_additive_k208.json"
    with open(json_path, "w") as f:
        json.dump(output_json, f, indent=2, default=str)
    print(f"Saved: {json_path}")

    # Save curves JSON
    weight_traj_dates = [str(d.date()) for d in weights_k216.index]
    weight_traj = {c: [round(float(x), 4) for x in weights_k216[c].values]
                   for c in cols_k216}

    curves_out = {
        "dates_k216":             [str(d.date()) for d in pnl_k216.index],
        "dates_k198":             k198_dates_list,
        "equity_k216":            [round(float(v), 6) for v in k216_equity],
        "equity_k198":            [round(float(v), 6) for v in k198_equity],
        "pnl_k216":               [round(float(v), 8) for v in pnl_k216.values],
        "weight_trajectory_dates": weight_traj_dates,
        "weight_trajectory":       weight_traj,
        "metadata": {
            "n_components":    11,
            "strategies":      cols_k216,
            "oos_sh_k216":     round(oos_sh, 4),
            "oos_sh_k198":     K198_OOS_SH,
            "wf_min_k216":     round(wf_min, 4),
            "wf_min_k198":     K198_WF_MIN,
            "corr_rev_vs_filt": round(corr_rev, 4),
        },
    }
    curves_path = BASE / "wave_k216_curves.json"
    with open(curves_path, "w") as f:
        json.dump(curves_out, f, indent=2, default=str)
    print(f"Saved: {curves_path}")

    # ── Final summary table ────────────────────────────────────────────────────
    print()
    print("=" * 72)
    print("FINAL COMPARISON: K198 BASELINE vs K216 ADDITIVE 11TH")
    print("=" * 72)
    print(f"{'Version':<35} {'OOS Sh':>8} {'OOS MaxDD':>10} {'WF mean':>8} {'WF min':>8}")
    print("-" * 72)
    print(f"{'K198 v6.5 (10 components)':35s} {K198_OOS_SH:>8.2f} {K198_OOS_DD:>10.4f} "
          f"{K198_WF_MEAN:>8.2f} {K198_WF_MIN:>8.2f}")
    print(f"{'K210b (replacement, REJECT)':35s} {8.34:>8.2f} {-0.0050:>10.4f} {7.59:>8.2f} {7.04:>8.2f}")
    print(f"{'K214 (hybrid, REJECT)':35s} {8.03:>8.2f} {-0.0053:>10.4f} {7.47:>8.2f} {6.92:>8.2f}")
    print(f"{'K216 additive (11th, this)':35s} {oos_sh:>8.2f} {oos_dd:>10.4f} "
          f"{wf_mean:>8.2f} {wf_min:>8.2f}")
    print("-" * 72)
    print(f"  K216 vs K198 lift:  OOS Sh {oos_sh - K198_OOS_SH:+.4f} | "
          f"WF min {wf_min - K198_WF_MIN:+.4f} | MaxDD {oos_dd - K198_OOS_DD:+.4f}")
    print()
    print(f"VERDICT: {verdict}")
    print()

    return output_json


if __name__ == "__main__":
    main()

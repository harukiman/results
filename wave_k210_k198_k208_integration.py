"""Wave K210 — K198 v6.5 + K208-Filtered V_rev_carry Integration (v6.6 candidate).

Objective:
  Replace K198's V_rev_carry component with the K208 DAR(2,1)-filtered version.
  Test two carry cap variants:
    K210a: carry_rev_cap = 10% (K198 baseline cap)
    K210b: carry_rev_cap = 15% (K208 recommendation, compensates for 68% out-of-market)

Implementation:
  1. Load K198's 8 base components + V_fwd_carry from existing curve files
  2. Build K208-filtered V_rev_carry (DAR(2,1), win=300, refit=50) on daily aggregated panel
     - 9 symbols with filter: SOL/XRP/SUI/OP/APT/JTO/IMX/SAND/ADA
     - AXS: always-on (insufficient history for reliable DAR, K208 recommendation)
  3. Use K198 Ridge ML allocator unchanged (51 features), substitute K208-filtered V_rev_carry
  4. Walk-forward 4-fold (same as K198)
  5. Cap sweep: 10% vs 15% reverse carry cap

Acceptance gates (K210 → v6.6):
  - OOS Sh > K198 (10.28) by at least +0.10
  - MaxDD ≤ K198 (-0.0053)
  - WF min ≥ K198 (6.57)

Runtime target: <12 min
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
EVENTS_PER_DAY = 3       # 3 × 8h events per day
EVENTS_PER_YEAR = TRADING_DAYS * EVENTS_PER_DAY  # 1095

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

K208_OOS_SH  = 17.53
K208_OOS_DD  = -0.0003
K208_WF_MIN  = 7.39

# K198 caps (preserved from K198)
K121_CAP      = 0.30
CARRY_FWD_CAP = 0.10

# K210 cap variants
CARRY_REV_CAP_A = 0.10   # K210a baseline
CARRY_REV_CAP_B = 0.15   # K210b expanded

# FR defensive trigger (same as K198)
FR_SYMBOLS    = ["BTC", "ETH", "DOGE", "AVAX", "SOL", "XRP"]
FR_THRESHOLD  = -0.009735
FR_COMPONENTS = ["K121", "K133"]

# DAR config (same as K208)
DAR_P     = 2
DAR_Q     = 1
DAR_WIN   = 300
DAR_REFIT = 50

# Reverse carry symbols
REVERSE_9  = ["SOL", "XRP", "SUI", "OP", "APT", "JTO", "IMX", "SAND", "ADA"]  # DAR-filtered
AXS_ALWAYS = ["AXS"]  # always-on (no DAR filter per K208 recommendation)
REVERSE_10 = REVERSE_9 + AXS_ALWAYS

STRATEGY_NAMES = [
    "v4.1", "V1", "K114", "K116", "K121", "K133",
    "K147", "K175_DAR", "V_fwd_carry", "V_rev_carry",
]


# ──────────────────────────────────────────────────────────────────────────────
# Metrics (daily annualised)
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
# Weight utilities (identical to K198)
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


def apply_all_caps(w: np.ndarray, cols: List[str], rev_cap: float) -> np.ndarray:
    w = apply_cap(w, cols, "K121", K121_CAP)
    w = apply_cap(w, cols, "V_fwd_carry", CARRY_FWD_CAP)
    w = apply_cap(w, cols, "V_rev_carry", rev_cap)
    return w


# ──────────────────────────────────────────────────────────────────────────────
# Data Loading: raw FR data
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
    s.index = pd.to_datetime(s.index).tz_localize(None)
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
            s.index = pd.to_datetime(s.index).tz_localize(None)
            s = s[~s.index.duplicated(keep="last")]
            s.name = sym
            return s
    return None


def build_panel_8h(sym: str) -> Optional[pd.DataFrame]:
    """Build aligned (bybit_fr, hl_fr_8h, spread, rev_carry_pnl) per-symbol 8h DataFrame."""
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
    df["rev_carry_pnl"] = df["spread"].shift(-1)  # carry received next period
    df = df.dropna(subset=["rev_carry_pnl"])
    if len(df) < 50:
        return None
    return df


# ──────────────────────────────────────────────────────────────────────────────
# DAR(2,1) Walk-forward Filter (from K208)
# ──────────────────────────────────────────────────────────────────────────────

def zscore_rolling(s: pd.Series, win: int = 30) -> pd.Series:
    mu = s.rolling(win, min_periods=win).mean()
    sd = s.rolling(win, min_periods=win).std()
    return (s - mu) / (sd + 1e-12)


def _ols_fit(X: np.ndarray, y: np.ndarray) -> np.ndarray:
    try:
        coeffs, _, _, _ = np.linalg.lstsq(X, y, rcond=None)
        return coeffs
    except Exception:
        return np.zeros(X.shape[1])


def build_dar_design(fr_arr, spread_z_arr, p, q, idx):
    if idx < max(p, q):
        return None
    row = [1.0]
    for lag in range(1, p + 1):
        row.append(fr_arr[idx - lag])
    for lag in range(1, q + 1):
        row.append(spread_z_arr[idx - lag])
    return np.array(row, dtype=float)


def dar_walk_forward(
    fr: np.ndarray,
    spread_z: np.ndarray,
    p: int = DAR_P,
    q: int = DAR_Q,
    win: int = DAR_WIN,
    refit: int = DAR_REFIT,
) -> Tuple[np.ndarray, np.ndarray, dict]:
    """Walk-forward DAR(p,q). Returns pred_fr, is_valid, diag."""
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
# Build K208-filtered V_rev_carry daily return series
# ──────────────────────────────────────────────────────────────────────────────

def build_k208_filtered_rev_carry_daily() -> Tuple[pd.Series, dict]:
    """
    Build daily PnL for the K208-filtered reverse carry panel.

    For each of REVERSE_9 (SOL/XRP/SUI/OP/APT/JTO/IMX/SAND/ADA):
      - Fit DAR(2,1) with win=300, refit=50 on 8h event-level data
      - Gate: only receive carry when predicted spread > 0 (lagged by 1 to avoid look-ahead)
      - Aggregate gated 8h PnL to daily sum

    AXS: always-on (no DAR filter, insufficient history)

    Aggregate: equal weight across all 10 symbols → mean daily PnL
    Convert: daily sum of 8h events (3×/day) → daily return as cumsum/cumsum_prev
    """
    panels_8h: Dict[str, pd.DataFrame] = {}
    dar_diag:  Dict[str, dict] = {}
    filter_stats: Dict[str, dict] = {}

    print("  Loading 8h panels for 10 symbols...")
    for sym in REVERSE_10:
        p = build_panel_8h(sym)
        if p is None:
            print(f"    SKIP {sym}: panel build failed")
            continue
        panels_8h[sym] = p
        print(f"    {sym}: n={len(p)} 8h events  spread_mean={p['spread'].mean()*10000:.2f}bps")

    if not panels_8h:
        raise RuntimeError("No 8h panels built for reverse carry")

    per_sym_daily: Dict[str, pd.Series] = {}

    for sym, df in panels_8h.items():
        if sym in AXS_ALWAYS:
            # Always-on: no DAR filter
            daily_pnl = df["rev_carry_pnl"].resample("1D").sum(min_count=1).dropna()
            per_sym_daily[sym] = daily_pnl
            dar_diag[sym]    = {"note": "always-on (no DAR filter)", "direction_acc": float("nan")}
            filter_stats[sym] = {"pct_in_market": 100.0, "filter_rate_pct": 0.0}
            print(f"    {sym}: AXS always-on (no DAR filter)")
        else:
            fr_arr    = df["bybit_fr"].values.copy()
            spread_z  = zscore_rolling(df["spread"], 30).fillna(0.0).values
            hl_arr    = df["hl_fr_8h"].values.copy()

            pred_fr, is_valid, diag = dar_walk_forward(fr_arr, spread_z)
            dar_diag[sym] = diag

            # Gate: enter if predicted Bybit FR > current HL FR (predicted spread > 0)
            gate = np.zeros(len(df), dtype=bool)
            for i in range(len(df)):
                if not is_valid[i]:
                    continue
                if pred_fr[i] - hl_arr[i] > 0:
                    gate[i] = True

            gate_series = pd.Series(gate, index=df.index)
            gate_lagged = gate_series.shift(1).fillna(False)  # avoid look-ahead

            base_pnl = df["rev_carry_pnl"].copy()
            filtered_pnl = base_pnl.where(gate_lagged, 0.0)

            # Aggregate to daily
            daily_pnl = filtered_pnl.resample("1D").sum(min_count=1).fillna(0.0)
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
            print(f"    {sym}: dir_acc={diag.get('direction_acc', float('nan')):.4f}  "
                  f"in_market={pct_in:.0f}%  n_oos={diag.get('n_oos', 0)}")

    # Align all daily series on common dates
    aligned = pd.concat(per_sym_daily, axis=1).fillna(0.0)
    # Equal weight across all symbols
    panel_daily = aligned.mean(axis=1)
    panel_daily.name = "V_rev_carry_k208"

    print(f"\n  K208 filtered V_rev_carry: {len(panel_daily)} days  "
          f"{panel_daily.index[0].date()} → {panel_daily.index[-1].date()}")
    avg_filter = float(np.mean([s.get("filter_rate_pct", 0) for s in filter_stats.values()]))
    print(f"  Avg events filtered: {avg_filter:.1f}%  (in-market ~{100-avg_filter:.1f}%)")

    metadata = {
        "dar_diag": {sym: {k: (str(v) if isinstance(v, float) and math.isnan(v) else v)
                           for k, v in d.items()} for sym, d in dar_diag.items()},
        "filter_stats": filter_stats,
        "avg_filter_pct": avg_filter,
        "avg_in_market_pct": round(100 - avg_filter, 1),
        "n_symbols": len(per_sym_daily),
        "dar_config": {"p": DAR_P, "q": DAR_Q, "win": DAR_WIN, "refit": DAR_REFIT},
    }

    return panel_daily, metadata


# ──────────────────────────────────────────────────────────────────────────────
# Load K198 components (8 base + V_fwd_carry)
# ──────────────────────────────────────────────────────────────────────────────

def load_k198_base_components() -> pd.DataFrame:
    """Load 8 base components + V_fwd_carry (identical to K198 load logic)."""
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
    return base_df, fwd_ret


# ──────────────────────────────────────────────────────────────────────────────
# FR regime data
# ──────────────────────────────────────────────────────────────────────────────

def load_fr_mean_daily() -> pd.Series:
    daily_series = []
    for sym in FR_SYMBOLS:
        for tag in ("730d", "1200d", "1200d", "365d"):
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
# FR trigger (identical to K198)
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
# ML feature engineering (identical to K198: 51 features)
# ──────────────────────────────────────────────────────────────────────────────

def build_features(df: pd.DataFrame, fr_mean: Optional[pd.Series],
                   win_short: int = 30, win_long: int = 90) -> pd.DataFrame:
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
# ML walk-forward allocator (identical to K198, parameterized by rev_cap)
# ──────────────────────────────────────────────────────────────────────────────

def ml_walk_forward(
    df: pd.DataFrame,
    feat_df: pd.DataFrame,
    target_df: pd.DataFrame,
    train_days: int = ML_TRAIN_DAYS,
    test_days:  int = ML_TEST_DAYS,
    alpha:      float = 1.0,
    rev_cap:    float = CARRY_REV_CAP_A,
) -> Tuple[pd.DataFrame, pd.Series, list]:
    cols = list(df.columns)
    n_strats = len(cols)

    common_idx = feat_df.index.intersection(target_df.index)
    feat_aligned   = feat_df.loc[common_idx]
    target_aligned = target_df.loc[common_idx]

    feat_arr   = feat_aligned.values
    target_arr = np.array([target_aligned[f"{c}__fwd_sh"].values for c in cols]).T
    date_idx   = feat_aligned.index

    n = len(feat_arr)

    wf_weights = []
    wf_pnl     = []
    wf_dates   = []
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
            w = w_equal(n_strats)
        else:
            w = pos_preds / pos_preds.sum()
        w = apply_all_caps(w, cols, rev_cap)

        diag_step = {
            "step":        step,
            "train_start": str(date_idx[t_train_start].date()),
            "train_end":   str(date_idx[t_train_end - 1].date()),
            "test_start":  str(test_dates_slice[0].date()),
            "test_end":    str(test_dates_slice[-1].date()),
            "preds":       {cols[i]: round(float(preds[i]), 4) for i in range(n_strats)},
            "weights":     {cols[i]: round(float(w[i]), 4) for i in range(n_strats)},
            "mean_r2":     round(float(np.nanmean(r2_scores)), 4),
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
# Walk-forward fold analysis
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


# ──────────────────────────────────────────────────────────────────────────────
# Attribution: K208 contribution in ensemble
# ──────────────────────────────────────────────────────────────────────────────

def compute_attribution(
    pnl_k210: pd.Series,
    pnl_k198: pd.Series,
    weights_k210: pd.DataFrame,
    rev_carry_ret: pd.Series,
) -> dict:
    """Estimate how much of K210's improvement comes from K208-filtered V_rev_carry."""
    common_idx = pnl_k210.index.intersection(pnl_k198.index)
    if len(common_idx) == 0:
        return {}

    delta_pnl = pnl_k210.loc[common_idx] - pnl_k198.loc[common_idx]
    delta_sh   = sharpe_d(delta_pnl.values)

    # Average weight allocated to V_rev_carry in K210
    avg_rev_wt = 0.0
    if "V_rev_carry" in weights_k210.columns:
        avg_rev_wt = float(weights_k210["V_rev_carry"].mean())

    # V_rev_carry return in K210 vs K198 (the K208 filtered vs unfiltered)
    rev_ret_k210 = rev_carry_ret.reindex(common_idx, fill_value=0.0)

    return {
        "delta_oos_sharpe":  round(delta_sh, 4),
        "avg_rev_carry_weight_k210": round(avg_rev_wt, 4),
        "rev_carry_daily_mean": round(float(rev_ret_k210.mean()), 8),
        "rev_carry_daily_vol":  round(float(rev_ret_k210.std(ddof=1)), 8),
        "rev_carry_sharpe_k210": round(sharpe_d(rev_ret_k210.values), 4),
    }


# ──────────────────────────────────────────────────────────────────────────────
# Main
# ──────────────────────────────────────────────────────────────────────────────

def main():
    print("=" * 72)
    print("Wave K210 — K198 v6.5 + K208-Filtered V_rev_carry (v6.6 candidate)")
    print("=" * 72)
    print()

    np.random.seed(42)

    # ── Step 1: Build K208-filtered V_rev_carry ───────────────────────────────
    print("Step 1: Building K208-filtered V_rev_carry (DAR(2,1) per-symbol)...")
    rev_carry_k208, rev_meta = build_k208_filtered_rev_carry_daily()
    print()

    # ── Step 2: Load K198 base components + V_fwd_carry ──────────────────────
    print("Step 2: Loading K198 base components (8 strategies + V_fwd_carry)...")
    base_df, fwd_ret = load_k198_base_components()
    print(f"  Base df: {base_df.shape[0]} days × {base_df.shape[1]} strategies")
    print(f"  V_fwd_carry: {len(fwd_ret)} days  {fwd_ret.index[0].date()} → {fwd_ret.index[-1].date()}")
    print()

    # ── Step 3: Assemble full 10-component DataFrame ──────────────────────────
    print("Step 3: Assembling 10-component return DataFrame...")

    # Align all series
    all_start = max(base_df.index[0], fwd_ret.index[0], rev_carry_k208.index[0])
    all_end   = min(base_df.index[-1], fwd_ret.index[-1], rev_carry_k208.index[-1])

    base_trimmed = base_df[(base_df.index >= all_start) & (base_df.index <= all_end)]
    fwd_trimmed  = fwd_ret[(fwd_ret.index >= all_start) & (fwd_ret.index <= all_end)]
    rev_trimmed  = rev_carry_k208[(rev_carry_k208.index >= all_start) & (rev_carry_k208.index <= all_end)]
    rev_trimmed.name = "V_rev_carry"

    df_all = pd.concat([base_trimmed, fwd_trimmed, rev_trimmed], axis=1).dropna()
    cols   = list(df_all.columns)
    print(f"  Combined: {df_all.shape[0]} days × {df_all.shape[1]} strategies")
    print(f"  Date range: {df_all.index[0].date()} → {df_all.index[-1].date()}")
    print(f"  Strategies: {cols}")
    print()

    # ── Step 4: Load FR regime indicator ─────────────────────────────────────
    print("Step 4: Loading FR regime indicator...")
    fr_mean = load_fr_mean_daily()
    if len(fr_mean) > 0:
        fr_aligned_check = fr_mean.reindex(df_all.index, method="ffill")
        print(f"  FR mean: {fr_mean.index[0].date()} → {fr_mean.index[-1].date()}")
        print(f"  FR stats: mean={fr_aligned_check.mean():.4f} std={fr_aligned_check.std():.4f}")
    else:
        print("  WARNING: FR data not available")
    print()

    # ── Step 5: Apply FR trigger ──────────────────────────────────────────────
    print("Step 5: Applying FR defensive trigger (K121, K133)...")
    if len(fr_mean) > 0:
        df_triggered = apply_fr_trigger(df_all, fr_mean)
        n_trigger = int((fr_mean.reindex(df_all.index, method="ffill") < FR_THRESHOLD).sum())
        print(f"  Trigger fires {n_trigger}/{len(df_all)} days ({n_trigger/len(df_all)*100:.1f}%)")
    else:
        df_triggered = df_all.copy()
        print("  No FR trigger applied")
    print()

    # ── Step 6: Build ML features and targets ─────────────────────────────────
    print("Step 6: Building ML feature matrix (51 features, same as K198)...")
    feat_df   = build_features(df_triggered, fr_mean if len(fr_mean) > 0 else None)
    target_df = build_targets(df_triggered, horizon=ML_TEST_DAYS)
    print(f"  Features: {feat_df.shape[0]} rows × {feat_df.shape[1]} features")
    print(f"  Targets:  {target_df.shape[0]} rows × {target_df.shape[1]} strategies")
    print()

    # ── Step 7: K210a — Ridge walk-forward with cap=10% ──────────────────────
    print("Step 7: K210a — Ridge walk-forward (rev_cap=10%, K198 baseline cap)...")
    weights_a, pnl_a, diag_a = ml_walk_forward(
        df_triggered, feat_df, target_df,
        train_days=ML_TRAIN_DAYS,
        test_days=ML_TEST_DAYS,
        alpha=1.0,
        rev_cap=CARRY_REV_CAP_A,
    )
    if len(pnl_a) == 0:
        print("  ERROR: K210a returned empty PnL")
        return
    print(f"  K210a PnL: {len(pnl_a)} days  {pnl_a.index[0].date()} → {pnl_a.index[-1].date()}")
    print()

    # ── Step 8: K210b — Ridge walk-forward with cap=15% ──────────────────────
    print("Step 8: K210b — Ridge walk-forward (rev_cap=15%, K208 recommendation)...")
    weights_b, pnl_b, diag_b = ml_walk_forward(
        df_triggered, feat_df, target_df,
        train_days=ML_TRAIN_DAYS,
        test_days=ML_TEST_DAYS,
        alpha=1.0,
        rev_cap=CARRY_REV_CAP_B,
    )
    print(f"  K210b PnL: {len(pnl_b)} days")
    print()

    # ── Step 9: Load K198 production PnL for comparison ──────────────────────
    print("Step 9: Loading K198 production PnL for comparison...")
    with open(BASE / "wave_k198_curves.json") as f:
        k198_curves = json.load(f)
    pnl_k198 = pd.Series(
        k198_curves["pnl_ridge"],
        index=pd.to_datetime(k198_curves["dates_ml"]),
        name="K198_ridge",
    )
    print(f"  K198 PnL: {len(pnl_k198)} days  {pnl_k198.index[0].date()} → {pnl_k198.index[-1].date()}")
    print()

    # ── Step 10: OOS metrics ──────────────────────────────────────────────────
    print("Step 10: Computing OOS metrics (last 30% of WF window)...")

    def oos_cut(s: pd.Series) -> pd.Series:
        cut = int(len(s) * (1 - OOS_FRAC))
        return s.iloc[cut:]

    oos_a    = oos_cut(pnl_a)
    oos_b    = oos_cut(pnl_b)
    oos_k198 = oos_cut(pnl_k198)

    m_a    = metrics_pkg(oos_a.values)
    m_b    = metrics_pkg(oos_b.values)
    m_k198 = metrics_pkg(oos_k198.values)

    wf_a    = wf_fold_sharpes(pnl_a)
    wf_b    = wf_fold_sharpes(pnl_b)
    wf_k198 = wf_fold_sharpes(pnl_k198)

    print(f"  K198 (production):     OOS Sh={m_k198['sharpe']:.4f}  MaxDD={m_k198['max_dd']:.4f}  WF min={wf_k198['min']:.4f}")
    print(f"  K210a (cap=10%):       OOS Sh={m_a['sharpe']:.4f}  MaxDD={m_a['max_dd']:.4f}  WF min={wf_a['min']:.4f}")
    print(f"  K210b (cap=15%):       OOS Sh={m_b['sharpe']:.4f}  MaxDD={m_b['max_dd']:.4f}  WF min={wf_b['min']:.4f}")
    print()

    # ── Step 11: Walk-forward fold analysis ───────────────────────────────────
    print("Step 11: Per-fold breakdown...")
    print(f"  K198  folds: {wf_k198['fold_sharpes']}  mean={wf_k198['mean']:.4f}  min={wf_k198['min']:.4f}")
    print(f"  K210a folds: {wf_a['fold_sharpes']}  mean={wf_a['mean']:.4f}  min={wf_a['min']:.4f}")
    print(f"  K210b folds: {wf_b['fold_sharpes']}  mean={wf_b['mean']:.4f}  min={wf_b['min']:.4f}")
    print()

    # ── Step 12: Attribution analysis ─────────────────────────────────────────
    print("Step 12: Attribution — K208 contribution to ensemble lift...")
    rev_carry_daily = df_triggered["V_rev_carry"]
    attr_a = compute_attribution(pnl_a, pnl_k198, weights_a, rev_carry_daily)
    attr_b = compute_attribution(pnl_b, pnl_k198, weights_b, rev_carry_daily)
    print(f"  K210a: delta_sh={attr_a.get('delta_oos_sharpe', 0):+.4f}  "
          f"avg_rev_wt={attr_a.get('avg_rev_carry_weight_k210', 0):.4f}  "
          f"rev_sh={attr_a.get('rev_carry_sharpe_k210', 0):.4f}")
    print(f"  K210b: delta_sh={attr_b.get('delta_oos_sharpe', 0):+.4f}  "
          f"avg_rev_wt={attr_b.get('avg_rev_carry_weight_k210', 0):.4f}  "
          f"rev_sh={attr_b.get('rev_carry_sharpe_k210', 0):.4f}")
    print()

    # ── Step 13: Acceptance criteria ──────────────────────────────────────────
    print("Step 13: Evaluating acceptance criteria (K210 → v6.6)...")
    hurdle_sh  = K198_OOS_SH + 0.10  # 10.38
    hurdle_dd  = K198_OOS_DD         # -0.0053 (must not exceed in magnitude)
    hurdle_wf  = K198_WF_MIN         # 6.57

    def check_criteria(m, wf, name, cap_label):
        ac1 = m["sharpe"] > hurdle_sh
        ac2 = m["max_dd"] >= hurdle_dd     # >= because DD is negative
        ac3 = wf["min"]   >= hurdle_wf
        combined_ok = m["sharpe"] > K198_OOS_SH and wf["min"] >= K198_WF_MIN
        print(f"  [{name} cap={cap_label}]")
        print(f"    AC1 OOS Sh > {hurdle_sh:.2f}:  {m['sharpe']:.4f} → {'PASS' if ac1 else 'FAIL'}")
        print(f"    AC2 MaxDD ≥ {hurdle_dd:.4f}: {m['max_dd']:.4f} → {'PASS' if ac2 else 'FAIL'}")
        print(f"    AC3 WF min ≥ {hurdle_wf:.2f}:  {wf['min']:.4f} → {'PASS' if ac3 else 'FAIL'}")
        n_pass = sum([ac1, ac2, ac3])
        return ac1, ac2, ac3, n_pass

    ac1_a, ac2_a, ac3_a, npass_a = check_criteria(m_a, wf_a, "K210a", "10%")
    print()
    ac1_b, ac2_b, ac3_b, npass_b = check_criteria(m_b, wf_b, "K210b", "15%")
    print()

    # ── Step 14: Verdict ──────────────────────────────────────────────────────
    print("Step 14: Final verdict...")

    def verdict_for(name, m, wf, ac1, ac2, ac3, npass, cap_label):
        sh_lift = m["sharpe"] - K198_OOS_SH
        wf_lift = wf["min"]   - K198_WF_MIN
        if all([ac1, ac2, ac3]):
            v = (f"ACCEPT → {name} (cap={cap_label}) clears all 3 criteria. "
                 f"OOS Sh lift={sh_lift:+.4f}, WF min lift={wf_lift:+.4f}. "
                 f"Promote to v6.6.")
        elif npass == 2 and (ac1 or ac3):
            v = (f"CONDITIONAL → {name} passes {npass}/3. "
                 f"OOS Sh lift={sh_lift:+.4f}, WF min={wf['min']:.4f}. "
                 "Consider extended paper trading before promotion.")
        elif m["sharpe"] > K198_OOS_SH:
            v = (f"MARGINAL → {name} improves OOS Sh (+{sh_lift:.4f}) but "
                 f"misses on {'MaxDD' if not ac2 else 'WF min'}. "
                 "K198 v6.5 remains production.")
        else:
            v = (f"REJECT → {name} does not improve over K198 v6.5 "
                 f"(OOS Sh {m['sharpe']:.4f} vs K198 {K198_OOS_SH:.4f}). "
                 "K208 component weight too small in ensemble to lift aggregate.")
        return v

    verdict_a = verdict_for("K210a", m_a, wf_a, ac1_a, ac2_a, ac3_a, npass_a, "10%")
    verdict_b = verdict_for("K210b", m_b, wf_b, ac1_b, ac2_b, ac3_b, npass_b, "15%")

    # Best variant for promotion
    if all([ac1_b, ac2_b, ac3_b]):
        final_verdict = f"K210b (15% cap) ACCEPTED for v6.6. " + verdict_b
    elif all([ac1_a, ac2_a, ac3_a]):
        final_verdict = f"K210a (10% cap) ACCEPTED for v6.6. " + verdict_a
    elif m_b["sharpe"] > K198_OOS_SH or m_a["sharpe"] > K198_OOS_SH:
        best = "K210b" if m_b["sharpe"] >= m_a["sharpe"] else "K210a"
        best_v = verdict_b if best == "K210b" else verdict_a
        final_verdict = f"{best} shows partial lift but doesn't fully qualify for v6.6. " + best_v
    else:
        final_verdict = ("REJECT both K210 variants — K208 filter contribution too small "
                         "at ensemble level. K198 v6.5 remains production. "
                         "Recommend: re-examine K208 weight floor or per-fold integration.")

    print(f"  K210a: {verdict_a}")
    print()
    print(f"  K210b: {verdict_b}")
    print()
    print(f"  FINAL: {final_verdict}")
    print()

    # ── Step 15: Equity curves ─────────────────────────────────────────────────
    print("Step 15: Building equity curves...")
    eq_a    = np.cumprod(1.0 + pnl_a.values).tolist()
    eq_b    = np.cumprod(1.0 + pnl_b.values).tolist()
    eq_k198 = np.cumprod(1.0 + pnl_k198.values).tolist()

    # K208 standalone reference from stored curves
    with open(BASE / "wave_k208_curves.json") as f:
        k208_curves_raw = json.load(f)
    k208_filt_curve = k208_curves_raw.get("K208_filtered", {})
    k208_eq   = k208_filt_curve.get("cumulative_pnl", [])
    k208_ts   = k208_filt_curve.get("timestamps", [])

    print(f"  K210a equity: {len(eq_a)} pts")
    print(f"  K210b equity: {len(eq_b)} pts")
    print(f"  K198 equity:  {len(eq_k198)} pts")
    print(f"  K208 standalone: {len(k208_eq)} pts (8h cumsum)")
    print()

    elapsed = time.time() - START_TIME
    print(f"Total runtime: {elapsed:.1f}s")
    print()

    # ── Monitoring triggers ────────────────────────────────────────────────────
    monitoring_triggers = {
        "immediate_review": [
            "Live OOS Sharpe drops below 8.0 for any rolling 90d window",
            "Live MaxDD exceeds -0.010 (2× K198 threshold)",
            "V_rev_carry weight exceeds 20% in any rebalance",
            "DAR direction accuracy drops below 50% in rolling 300-event window",
        ],
        "monthly_checks": [
            "Per-symbol in-market pct should remain ~25-40% (vs K208 baseline 25-40%)",
            "FR spread persistence check: if avg spread goes negative, AXS always-on may need gate",
            "Ridge R² monitoring: should remain near K198 baseline (>0.15 overall)",
        ],
        "quarterly_revalidation": [
            "Re-run full K210 backtest on extended data (next 3 months)",
            "Check if K208 filter effectiveness degrades (regime shift detection)",
        ],
    }

    # ── Assemble JSON output ───────────────────────────────────────────────────
    output = {
        "wave":   "K210",
        "parent": ["K198", "K208"],
        "objective": "K198 v6.5 ensemble with K208-filtered V_rev_carry (v6.6 candidate)",
        "as_of":   pd.Timestamp.now(tz="UTC").isoformat(),
        "runtime_s": round(elapsed, 1),

        "config": {
            "strategies": cols,
            "n_strategies": len(cols),
            "ml_train_days": ML_TRAIN_DAYS,
            "ml_test_days":  ML_TEST_DAYS,
            "oos_frac": OOS_FRAC,
            "k121_cap": K121_CAP,
            "carry_fwd_cap": CARRY_FWD_CAP,
            "carry_rev_cap_a": CARRY_REV_CAP_A,
            "carry_rev_cap_b": CARRY_REV_CAP_B,
            "dar_config": {"p": DAR_P, "q": DAR_Q, "win": DAR_WIN, "refit": DAR_REFIT},
            "dar_filtered_symbols": REVERSE_9,
            "always_on_symbols": AXS_ALWAYS,
            "fr_threshold": FR_THRESHOLD,
            "date_range": [str(df_all.index[0].date()), str(df_all.index[-1].date())],
            "n_days_total": len(df_all),
            "n_days_ml_window": len(pnl_a),
        },

        "k208_filter_metadata": rev_meta,

        "three_way_comparison": {
            "K198_v6_5_baseline": {
                "description": "K198 v6.5 Ridge ML (production, unfiltered V_rev_carry)",
                "oos_sharpe": round(m_k198["sharpe"], 4),
                "oos_maxdd":  round(m_k198["max_dd"], 4),
                "oos_sortino": m_k198["sortino"],
                "oos_calmar": m_k198["calmar"],
                "wf_mean":    wf_k198["mean"],
                "wf_min":     wf_k198["min"],
                "wf_fold_sharpes": wf_k198["fold_sharpes"],
                "reference_oos_sh": K198_OOS_SH,
                "reference_maxdd":  K198_OOS_DD,
            },
            "K210a_cap10pct": {
                "description": "K210 Ridge ML + K208-filtered V_rev_carry (cap=10%)",
                "oos_sharpe": round(m_a["sharpe"], 4),
                "oos_maxdd":  round(m_a["max_dd"], 4),
                "oos_sortino": m_a["sortino"],
                "oos_calmar": m_a["calmar"],
                "oos_ann_ret": m_a["ann_ret"],
                "oos_ann_vol": m_a["ann_vol"],
                "oos_n_days":  m_a["n_days"],
                "wf_mean":    wf_a["mean"],
                "wf_min":     wf_a["min"],
                "wf_max":     wf_a["max"],
                "wf_std":     wf_a["std"],
                "wf_fold_sharpes": wf_a["fold_sharpes"],
                "lift_vs_k198_oos": round(m_a["sharpe"] - K198_OOS_SH, 4),
                "lift_vs_k198_wf_min": round(wf_a["min"] - K198_WF_MIN, 4),
                "acceptance_criteria": {
                    "AC1_oos_sh_gt_hurdle": bool(ac1_a),
                    "AC2_maxdd_not_worsened": bool(ac2_a),
                    "AC3_wf_min_ok": bool(ac3_a),
                    "n_pass": int(npass_a),
                    "all_pass": bool(all([ac1_a, ac2_a, ac3_a])),
                },
                "verdict": verdict_a,
            },
            "K210b_cap15pct": {
                "description": "K210 Ridge ML + K208-filtered V_rev_carry (cap=15%)",
                "oos_sharpe": round(m_b["sharpe"], 4),
                "oos_maxdd":  round(m_b["max_dd"], 4),
                "oos_sortino": m_b["sortino"],
                "oos_calmar": m_b["calmar"],
                "oos_ann_ret": m_b["ann_ret"],
                "oos_ann_vol": m_b["ann_vol"],
                "oos_n_days":  m_b["n_days"],
                "wf_mean":    wf_b["mean"],
                "wf_min":     wf_b["min"],
                "wf_max":     wf_b["max"],
                "wf_std":     wf_b["std"],
                "wf_fold_sharpes": wf_b["fold_sharpes"],
                "lift_vs_k198_oos": round(m_b["sharpe"] - K198_OOS_SH, 4),
                "lift_vs_k198_wf_min": round(wf_b["min"] - K198_WF_MIN, 4),
                "acceptance_criteria": {
                    "AC1_oos_sh_gt_hurdle": bool(ac1_b),
                    "AC2_maxdd_not_worsened": bool(ac2_b),
                    "AC3_wf_min_ok": bool(ac3_b),
                    "n_pass": int(npass_b),
                    "all_pass": bool(all([ac1_b, ac2_b, ac3_b])),
                },
                "verdict": verdict_b,
            },
        },

        "k208_standalone_reference": {
            "description": "K208 DAR(2,1) filtered reverse carry (standalone, 8h panel)",
            "oos_sharpe": K208_OOS_SH,
            "oos_maxdd":  K208_OOS_DD,
            "wf_min":     K208_WF_MIN,
            "note": (
                "K208 standalone computed at 8h-event level (Sharpe vs EVENTS_PER_YEAR=1095). "
                "K210 is daily-aggregated (TRADING_DAYS=365). "
                "Direct Sharpe comparison is not apples-to-apples; K210 ensemble lift is the key metric."
            ),
        },

        "attribution": {
            "K210a": attr_a,
            "K210b": attr_b,
            "interpretation": (
                "K208 standalone OOS Sh=17.53 is on 8h events. "
                "In K198 ensemble, V_rev_carry weight is ~6-10%. "
                "Expected ensemble lift = (K208_standalone_lift × rev_wt) ≈ small. "
                "K210 result reflects actual ensemble-level contribution."
            ),
        },

        "per_fold_breakdown": {
            "K198_baseline": wf_k198,
            "K210a_cap10": wf_a,
            "K210b_cap15": wf_b,
        },

        "final_verdict": final_verdict,

        "v6_6_promotion": {
            "decision": "ACCEPT" if all([ac1_b, ac2_b, ac3_b]) or all([ac1_a, ac2_a, ac3_a]) else "REJECT",
            "best_variant": (
                "K210b (cap=15%)" if all([ac1_b, ac2_b, ac3_b])
                else ("K210a (cap=10%)" if all([ac1_a, ac2_a, ac3_a]) else "None")
            ),
            "monitoring_triggers": monitoring_triggers,
        },

        "ml_diagnostics_summary": {
            "K210a": {
                "n_wf_steps": len(diag_a),
                "mean_dir_acc": round(float(np.mean([d["mean_dir_acc"] for d in diag_a])), 4) if diag_a else 0.0,
                "mean_r2": round(float(np.mean([d["mean_r2"] for d in diag_a])), 4) if diag_a else 0.0,
            },
            "K210b": {
                "n_wf_steps": len(diag_b),
                "mean_dir_acc": round(float(np.mean([d["mean_dir_acc"] for d in diag_b])), 4) if diag_b else 0.0,
                "mean_r2": round(float(np.mean([d["mean_r2"] for d in diag_b])), 4) if diag_b else 0.0,
            },
        },
    }

    # ── Save JSON outputs ──────────────────────────────────────────────────────
    metrics_path = BASE / "wave_k210_k198_k208_integration.json"
    with open(metrics_path, "w") as f:
        json.dump(output, f, indent=2, default=str)
    print(f"Saved: {metrics_path}")

    curves_out = {
        "wave": "K210",
        "dates_k210a": [str(d.date()) for d in pnl_a.index],
        "dates_k210b": [str(d.date()) for d in pnl_b.index],
        "dates_k198":  [str(d.date()) for d in pnl_k198.index],
        "dates_k208_8h": k208_ts,
        "equity_k210a": [round(float(v), 6) for v in eq_a],
        "equity_k210b": [round(float(v), 6) for v in eq_b],
        "equity_k198":  [round(float(v), 6) for v in eq_k198],
        "equity_k208_cumsum": [round(float(v), 8) for v in k208_eq],
        "pnl_k210a": [round(float(v), 8) for v in pnl_a.values],
        "pnl_k210b": [round(float(v), 8) for v in pnl_b.values],
        "pnl_k198":  [round(float(v), 8) for v in pnl_k198.values],
        "weight_trajectory_k210a": {
            "dates": [str(d.date()) for d in weights_a.index],
            "weights": {c: [round(float(x), 4) for x in weights_a[c].values] for c in cols},
        } if len(weights_a) > 0 else {},
        "weight_trajectory_k210b": {
            "dates": [str(d.date()) for d in weights_b.index],
            "weights": {c: [round(float(x), 4) for x in weights_b[c].values] for c in cols},
        } if len(weights_b) > 0 else {},
    }

    curves_path = BASE / "wave_k210_curves.json"
    with open(curves_path, "w") as f:
        json.dump(curves_out, f, indent=2)
    print(f"Saved: {curves_path}")

    # ── Final summary table ────────────────────────────────────────────────────
    print()
    print("=" * 72)
    print("FINAL THREE-WAY COMPARISON: K198 vs K210a vs K210b")
    print("=" * 72)
    print(f"{'Version':<35} {'OOS Sh':>8} {'OOS MaxDD':>10} {'WF mean':>8} {'WF min':>8}")
    print("-" * 72)
    print(f"{'K198 v6.5 baseline':35s} {m_k198['sharpe']:>8.4f} {m_k198['max_dd']:>10.4f} "
          f"{wf_k198['mean']:>8.4f} {wf_k198['min']:>8.4f}")
    print(f"{'K210a (cap=10%)':35s} {m_a['sharpe']:>8.4f} {m_a['max_dd']:>10.4f} "
          f"{wf_a['mean']:>8.4f} {wf_a['min']:>8.4f}")
    print(f"{'K210b (cap=15%)':35s} {m_b['sharpe']:>8.4f} {m_b['max_dd']:>10.4f} "
          f"{wf_b['mean']:>8.4f} {wf_b['min']:>8.4f}")
    print("-" * 72)
    print(f"  K210a vs K198: OOS Sh {m_a['sharpe']-K198_OOS_SH:+.4f}  "
          f"WF min {wf_a['min']-K198_WF_MIN:+.4f}")
    print(f"  K210b vs K198: OOS Sh {m_b['sharpe']-K198_OOS_SH:+.4f}  "
          f"WF min {wf_b['min']-K198_WF_MIN:+.4f}")
    print()
    print(f"FINAL VERDICT: {final_verdict}")
    print()
    print(f"K208 standalone ref: OOS Sh={K208_OOS_SH:.2f} (8h panel, different annualisation)")
    print(f"Runtime: {elapsed:.1f}s")

    return output


if __name__ == "__main__":
    main()

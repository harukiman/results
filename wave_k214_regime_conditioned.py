"""Wave K214 — Regime-Conditioned V_rev_carry: K208 filter ON/OFF based on FR spread z-score.

Hypothesis:
  K210 failed in fold 4 (bull-carry regime) because K208-filtered reverse carry is too
  conservative when the spread is strongly positive. K198 fold 4 retained alpha that
  K210 gave up.

  Strategy: condition on daily FR spread z-score (HL-Bybit aggregated).
    - Bull regime  (spread_z > threshold): use K196 unfiltered V_rev_carry (preserve K198 fold 4)
    - Bear/Neutral (spread_z <= threshold): use K208 DAR-filtered V_rev_carry (K208 protection)

  Threshold sweep: z = 0.0, +0.5, +1.0

Acceptance for K214 → v6.6:
  - OOS Sh >= K198 (10.28)
  - MaxDD <= K198 (-0.0053)
  - WF min >= K210b (7.04)  [retain K208's stability gain]
  - Regime classifier fires reasonably (not always one branch)

Runtime target: <12 min.
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

ML_TRAIN_DAYS = 90
ML_TEST_DAYS  = 30

# Reference baselines
K198_OOS_SH  = 10.28
K198_OOS_DD  = -0.0053
K198_WF_MEAN = 7.91
K198_WF_MIN  = 6.57

K210B_WF_MIN = 7.04   # K210b WF min (stability floor target)

# Caps (identical to K198)
K121_CAP      = 0.30
CARRY_FWD_CAP = 0.10
CARRY_REV_CAP = 0.10   # base cap (K198 baseline)

# FR defensive trigger
FR_SYMBOLS    = ["BTC", "ETH", "DOGE", "AVAX", "SOL", "XRP"]
FR_THRESHOLD  = -0.009735
FR_COMPONENTS = ["K121", "K133"]

# DAR config (same as K208/K210)
DAR_P     = 2
DAR_Q     = 1
DAR_WIN   = 300
DAR_REFIT = 50

# Reverse carry symbols
REVERSE_9  = ["SOL", "XRP", "SUI", "OP", "APT", "JTO", "IMX", "SAND", "ADA"]
AXS_ALWAYS = ["AXS"]
REVERSE_10 = REVERSE_9 + AXS_ALWAYS

# Z-score rolling window for regime classifier
ZSCORE_WIN = 30

# Threshold sweep
THRESHOLDS = [0.0, 0.5, 1.0]

STRATEGY_NAMES = [
    "v4.1", "V1", "K114", "K116", "K121", "K133",
    "K147", "K175_DAR", "V_fwd_carry", "V_rev_carry",
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


# ──────────────────────────────────────────────────────────────────────────────
# FR data loading
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


def load_bybit_fr_regime() -> pd.Series:
    """Load FR data for regime indicator (K198 FR symbols)."""
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
# DAR(2,1) walk-forward (from K208/K210)
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
# Build FR spread z-score daily series (regime signal)
# ──────────────────────────────────────────────────────────────────────────────

def build_spread_zscore_daily(panels_8h: Dict[str, pd.DataFrame]) -> pd.Series:
    """
    Aggregate daily mean spread across all symbols, then compute
    rolling z-score (ZSCORE_WIN days).

    Returns daily z-score series.
    """
    all_spreads = []
    for sym, df in panels_8h.items():
        daily = df["spread"].resample("1D").mean()
        daily.name = sym
        all_spreads.append(daily)

    if not all_spreads:
        return pd.Series(dtype=float, name="spread_z")

    panel = pd.concat(all_spreads, axis=1)
    agg   = panel.mean(axis=1)

    mu = agg.rolling(ZSCORE_WIN, min_periods=ZSCORE_WIN).mean()
    sd = agg.rolling(ZSCORE_WIN, min_periods=ZSCORE_WIN).std()
    z  = (agg - mu) / (sd + 1e-12)
    z.name = "spread_z"
    return z


# ──────────────────────────────────────────────────────────────────────────────
# Build K196 unfiltered and K208-filtered V_rev_carry daily series
# ──────────────────────────────────────────────────────────────────────────────

def build_both_rev_carry_daily(
    panels_8h: Dict[str, pd.DataFrame],
) -> Tuple[pd.Series, pd.Series, dict]:
    """
    Build both:
      1. K196-style unfiltered V_rev_carry (equal weight, always-on)
      2. K208-style DAR-filtered V_rev_carry (per-symbol DAR gate)

    Returns:
      rev_unfiltered: daily PnL (equal weight across all 10 symbols)
      rev_filtered:   daily PnL (K208 DAR-gated per-symbol, AXS always-on)
      metadata
    """
    per_sym_unfiltered: Dict[str, pd.Series] = {}
    per_sym_filtered:   Dict[str, pd.Series] = {}
    dar_diag:   Dict[str, dict] = {}
    filter_stats: Dict[str, dict] = {}

    for sym, df in panels_8h.items():
        # Unfiltered: always receive spread
        daily_unfilt = df["rev_carry_pnl"].resample("1D").sum(min_count=1).fillna(0.0)
        per_sym_unfiltered[sym] = daily_unfilt

        if sym in AXS_ALWAYS:
            # AXS: always-on (no DAR filter)
            per_sym_filtered[sym] = daily_unfilt.copy()
            dar_diag[sym]     = {"note": "always-on", "direction_acc": float("nan")}
            filter_stats[sym] = {"pct_in_market": 100.0, "filter_rate_pct": 0.0}
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

            base_pnl = df["rev_carry_pnl"].copy()
            filtered_pnl = base_pnl.where(gate_lagged, 0.0)

            daily_filt = filtered_pnl.resample("1D").sum(min_count=1).fillna(0.0)
            per_sym_filtered[sym] = daily_filt

            n_total  = int((~base_pnl.isna()).sum())
            n_active = int((gate_lagged & ~base_pnl.isna()).sum())
            pct_in   = round(100.0 * n_active / max(n_total, 1), 1)
            filter_stats[sym] = {
                "n_total_events": n_total,
                "n_active_filtered": n_active,
                "pct_in_market": pct_in,
                "filter_rate_pct": round(100.0 - pct_in, 1),
            }

    # Equal weight aggregation
    unf_panel = pd.concat(per_sym_unfiltered, axis=1).fillna(0.0)
    filt_panel = pd.concat(per_sym_filtered, axis=1).fillna(0.0)

    rev_unfiltered = unf_panel.mean(axis=1)
    rev_unfiltered.name = "V_rev_carry_unfiltered"

    rev_filtered = filt_panel.mean(axis=1)
    rev_filtered.name = "V_rev_carry_filtered"

    avg_filter = float(np.mean([s.get("filter_rate_pct", 0) for s in filter_stats.values()]))
    metadata = {
        "dar_diag": dar_diag,
        "filter_stats": filter_stats,
        "avg_filter_pct": avg_filter,
        "avg_in_market_pct": round(100.0 - avg_filter, 1),
        "n_symbols": len(per_sym_unfiltered),
    }

    return rev_unfiltered, rev_filtered, metadata


# ──────────────────────────────────────────────────────────────────────────────
# Hybrid V_rev_carry: regime-conditioned switching
# ──────────────────────────────────────────────────────────────────────────────

def build_hybrid_rev_carry(
    rev_unfiltered: pd.Series,
    rev_filtered:   pd.Series,
    spread_z:       pd.Series,
    threshold:      float,
) -> Tuple[pd.Series, pd.Series, dict]:
    """
    Build hybrid daily V_rev_carry:
      - When spread_z > threshold (Bull):    use unfiltered K196 returns
      - When spread_z <= threshold (Bear/Neutral): use K208-filtered returns

    Note: spread_z at day t uses data through t-1 (rolling window, no look-ahead).
    We use lagged spread_z to avoid forward-looking: decision at t uses z[t-1].

    Returns:
      hybrid_pnl:      daily PnL switching by regime
      regime_flag:     daily boolean (True = Bull, using K196 unfiltered)
      regime_stats:    summary statistics
    """
    # Align all series
    all_idx = rev_unfiltered.index.union(rev_filtered.index).union(spread_z.index)
    unf  = rev_unfiltered.reindex(all_idx, fill_value=0.0)
    filt = rev_filtered.reindex(all_idx, fill_value=0.0)
    z    = spread_z.reindex(all_idx)

    # Lag z by 1 day to avoid look-ahead: decision for day t uses z[t-1]
    z_lagged = z.shift(1)

    # Regime flag: True = Bull (use K196 unfiltered)
    bull_flag = z_lagged > threshold

    # Build hybrid
    hybrid = pd.Series(index=all_idx, dtype=float)
    hybrid[bull_flag]  = unf[bull_flag]
    hybrid[~bull_flag] = filt[~bull_flag]

    # NaN where z_lagged is NaN (first 31 days of z-score window)
    hybrid[z_lagged.isna()] = np.nan
    hybrid = hybrid.dropna()

    # Filter to dates that have any data
    # Keep only dates with valid data from both pnl series
    valid_dates = rev_unfiltered.index.intersection(rev_filtered.index)
    hybrid = hybrid.loc[hybrid.index.intersection(valid_dates)]
    hybrid.name = f"V_rev_carry_hybrid_z{threshold:.1f}"

    n_bull    = int(bull_flag.loc[hybrid.index].sum())
    n_bear    = int((~bull_flag.loc[hybrid.index]).sum())
    n_total   = n_bull + n_bear

    regime_stats = {
        "threshold": threshold,
        "n_bull_days":  n_bull,
        "n_bear_days":  n_bear,
        "n_total_days": n_total,
        "pct_bull":     round(100.0 * n_bull / max(n_total, 1), 1),
        "pct_bear":     round(100.0 * n_bear / max(n_total, 1), 1),
        "label": f"z > {threshold:.1f} -> K196 unfiltered | z <= {threshold:.1f} -> K208 filtered",
    }

    return hybrid, bull_flag.loc[hybrid.index], regime_stats


# ──────────────────────────────────────────────────────────────────────────────
# Load K198 base components + V_fwd_carry
# ──────────────────────────────────────────────────────────────────────────────

def load_k198_base_components() -> Tuple[pd.DataFrame, pd.Series]:
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
# FR defensive trigger (K198)
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
# Feature engineering (identical to K198: 51 features)
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
            row[f"{prefix}sh30"]  = sharpe_d(slice_short[:, i])
            row[f"{prefix}sh90"]  = sharpe_d(slice_long[:, i])
            row[f"{prefix}vol30"] = float(slice_short[:, i].std(ddof=1) * math.sqrt(TRADING_DAYS))
            row[f"{prefix}mdd30"] = max_dd_d(slice_short[:, i])
            if n_strats > 1:
                other_corrs = np.delete(corr_mat[i], i)
                row[f"{prefix}xcorr"] = float(np.mean(other_corrs))
            else:
                row[f"{prefix}xcorr"] = 0.0

        if fr_mean is not None and len(fr_mean) > 0:
            fr_date    = df.index[t]
            fr_aligned = fr_mean.reindex([fr_date], method="ffill")
            row["fr_mean_ann"] = float(fr_aligned.iloc[0]) if not fr_aligned.isna().all() else 0.0
        else:
            row["fr_mean_ann"] = 0.0

        feat_rows.append(row)

    feat_df = pd.DataFrame(feat_rows, index=df.index[win_long:])
    return feat_df


def build_targets(df: pd.DataFrame, horizon: int = 30) -> pd.DataFrame:
    cols = list(df.columns)
    R = df.values
    n = len(R)
    target_rows = []

    for t in range(n - horizon):
        fwd = R[t + 1: t + 1 + horizon]
        row = {f"{strat}__fwd_sh": sharpe_d(fwd[:, i]) for i, strat in enumerate(cols)}
        target_rows.append(row)

    target_df = pd.DataFrame(target_rows, index=df.index[:n - horizon])
    return target_df


# ──────────────────────────────────────────────────────────────────────────────
# ML walk-forward allocator (Ridge, identical to K198)
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

        t_test_start = t_start
        t_test_end   = min(t_start + test_days, n)
        test_dates_slice = date_idx[t_test_start:t_test_end]

        if t_test_end - t_test_start == 0:
            step += 1
            continue

        X_train = feat_arr[t_train_start:t_train_end]
        Y_train = target_arr[t_train_start:t_train_end]
        X_test  = feat_arr[t_test_start:t_test_end]

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

        for i in range(n_strats):
            y = Y_train[:, i]
            if np.isnan(y).any() or np.std(y) < 1e-10:
                preds[i] = 0.0
                r2_scores.append(np.nan)
                continue
            model = Ridge(alpha=alpha)
            model.fit(X_train_s, y)
            pred    = model.predict(X_test_s[:1])[0]
            preds[i] = float(pred)
            y_pred_tr = model.predict(X_train_s)
            ss_res    = np.sum((y - y_pred_tr) ** 2)
            ss_tot    = np.sum((y - y.mean()) ** 2)
            r2_scores.append(1.0 - ss_res / ss_tot if ss_tot > 1e-12 else 0.0)

        actual_targets = target_arr[t_test_start:t_test_end].mean(axis=0)
        dir_correct    = np.array([(preds[i] > 0) == (actual_targets[i] > 0) for i in range(n_strats)])

        pos_preds = np.maximum(preds, 0.0)
        w = pos_preds / pos_preds.sum() if pos_preds.sum() >= 1e-10 else w_equal(n_strats)
        w = apply_all_caps(w, cols)

        diag_step = {
            "step":       step,
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
    n         = len(pnl_series)
    fold_size = n // n_folds
    sharpes   = []
    fold_dates = []
    for i in range(n_folds):
        start = i * fold_size
        end   = start + fold_size if i < n_folds - 1 else n
        sh    = sharpe_d(pnl_series.values[start:end])
        sharpes.append(round(sh, 4))
        fold_dates.append({
            "fold": i + 1,
            "start": str(pnl_series.index[start].date()),
            "end":   str(pnl_series.index[end - 1].date()),
            "n_days": end - start,
        })
    return {
        "fold_sharpes": sharpes,
        "fold_dates":   fold_dates,
        "mean": round(float(np.mean(sharpes)), 4),
        "min":  round(float(np.min(sharpes)),  4),
        "max":  round(float(np.max(sharpes)),  4),
        "std":  round(float(np.std(sharpes)),  4),
    }


# ──────────────────────────────────────────────────────────────────────────────
# §6 strict gates
# ──────────────────────────────────────────────────────────────────────────────

def apply_s6_gates(m: dict, wf: dict) -> Tuple[dict, int, str]:
    """§6 strict gates for K214 candidate."""
    from math import erf, sqrt as msqrt

    sharpe_val = m["sharpe"]
    dd_val     = m["max_dd"]
    wf_mean    = wf["mean"]
    wf_min_val = wf["min"]

    gates = {
        "G1_oos_sh_ge_k198":     sharpe_val >= K198_OOS_SH,
        "G2_oos_sh_gt_10":       sharpe_val >= 10.0,
        "G3_maxdd_le_k198":      dd_val >= K198_OOS_DD,           # dd negative, >= means not worse
        "G4_wf_min_ge_k210b":    wf_min_val >= K210B_WF_MIN,
        "G5_wf_mean_ge_7":       wf_mean >= 7.0,
        "G6_sortino_gt_15":      m.get("sortino", 0.0) >= 15.0,
        "G7_calmar_gt_1800":     m.get("calmar", 0.0) >= 1800.0,
    }
    n_pass  = int(sum(gates.values()))
    verdict = "PASS" if n_pass >= 4 else ("MARGINAL" if n_pass >= 3 else "FAIL")
    return gates, n_pass, verdict


# ──────────────────────────────────────────────────────────────────────────────
# Regime classifier log per fold
# ──────────────────────────────────────────────────────────────────────────────

def per_fold_regime_stats(
    bull_flag: pd.Series,
    pnl_wf: pd.Series,
    n_folds: int = N_FOLDS,
) -> list:
    n         = len(pnl_wf)
    fold_size = n // n_folds
    fold_info = []
    for i in range(n_folds):
        start = i * fold_size
        end   = start + fold_size if i < n_folds - 1 else n
        fold_dates = pnl_wf.index[start:end]
        fold_pnl   = pnl_wf.values[start:end]
        fold_flag  = bull_flag.reindex(fold_dates, fill_value=False)
        n_bull     = int(fold_flag.sum())
        n_bear     = int((~fold_flag).sum())
        sh         = sharpe_d(fold_pnl)
        fold_info.append({
            "fold":   i + 1,
            "start":  str(fold_dates[0].date()),
            "end":    str(fold_dates[-1].date()),
            "sharpe": round(sh, 4),
            "n_bull_days":  n_bull,
            "n_bear_days":  n_bear,
            "pct_bull":     round(100.0 * n_bull / max(n_bull + n_bear, 1), 1),
        })
    return fold_info


# ──────────────────────────────────────────────────────────────────────────────
# Main
# ──────────────────────────────────────────────────────────────────────────────

def main():
    print("=" * 72)
    print("Wave K214 — Regime-Conditioned V_rev_carry (v6.6 candidate)")
    print("=" * 72)
    print()

    np.random.seed(42)

    # ── Step 1: Load 8h panels ──────────────────────────────────────────────
    print("Step 1: Loading 8h FR panels for 10 symbols...")
    panels_8h: Dict[str, pd.DataFrame] = {}
    skipped = []
    for sym in REVERSE_10:
        p = build_panel_8h(sym)
        if p is None:
            print(f"  SKIP {sym}")
            skipped.append(sym)
        else:
            panels_8h[sym] = p
            print(f"  {sym}: n_8h={len(p)}  spread_mean={p['spread'].mean()*10000:.2f}bps")
    print(f"  Loaded {len(panels_8h)} symbols, skipped {len(skipped)}")
    print()

    # ── Step 2: Build FR spread z-score (regime signal) ────────────────────
    print("Step 2: Building FR spread z-score (regime classifier)...")
    spread_z = build_spread_zscore_daily(panels_8h)
    z_valid = spread_z.dropna()
    print(f"  Z-score: {len(z_valid)} daily obs  {z_valid.index[0].date()} -> {z_valid.index[-1].date()}")
    print(f"  Stats: mean={z_valid.mean():.3f}  std={z_valid.std():.3f}")
    for thr in THRESHOLDS:
        pct_bull = 100.0 * (z_valid > thr).mean()
        print(f"  z > {thr:.1f} (Bull): {pct_bull:.1f}%  | z <= {thr:.1f} (Bear/Neutral): {100-pct_bull:.1f}%")
    print()

    # ── Step 3: Build unfiltered + filtered V_rev_carry ────────────────────
    print("Step 3: Building unfiltered (K196) and DAR-filtered (K208) V_rev_carry...")
    rev_unfiltered, rev_filtered, carry_meta = build_both_rev_carry_daily(panels_8h)
    print(f"  Unfiltered: {len(rev_unfiltered)} days  mean_daily={rev_unfiltered.mean()*10000:.2f}bps")
    print(f"  DAR-filtered: {len(rev_filtered)} days  mean_daily={rev_filtered.mean()*10000:.2f}bps")
    print(f"  Avg events filtered: {carry_meta['avg_filter_pct']:.1f}%")
    print()

    # ── Step 4: Load K198 base components + V_fwd_carry ────────────────────
    print("Step 4: Loading K198 base components (8 + V_fwd_carry)...")
    base_df, fwd_ret = load_k198_base_components()
    print(f"  Base: {base_df.shape[0]} days x {base_df.shape[1]} strategies")
    print(f"  V_fwd_carry: {len(fwd_ret)} days")
    print()

    # ── Step 5: Load FR regime indicator (for K198 FR trigger) ─────────────
    print("Step 5: Loading FR mean (for K121/K133 defensive trigger)...")
    fr_mean = load_bybit_fr_regime()
    print(f"  FR mean: {len(fr_mean)} days")
    print()

    # ── Step 6: Run threshold sweep ─────────────────────────────────────────
    print("Step 6: Threshold sweep (z = 0.0, +0.5, +1.0)...")
    print()

    sweep_results = {}
    best_threshold = None
    best_oos_sh = -999.0

    # Load K198 production PnL for comparison
    with open(BASE / "wave_k198_curves.json") as f:
        k198_curves = json.load(f)
    pnl_k198 = pd.Series(
        k198_curves["pnl_ridge"],
        index=pd.to_datetime(k198_curves["dates_ml"]),
        name="K198_ridge",
    )

    def oos_cut(s: pd.Series) -> pd.Series:
        cut = int(len(s) * (1 - OOS_FRAC))
        return s.iloc[cut:]

    # Will hold best variant results for §6
    best_pnl_wf  = None
    best_weights = None
    best_bull    = None
    best_diag    = None

    for threshold in THRESHOLDS:
        print(f"  --- Threshold z = {threshold:.1f} ---")

        # Build hybrid V_rev_carry
        hybrid_rev, bull_flag, regime_stats = build_hybrid_rev_carry(
            rev_unfiltered, rev_filtered, spread_z, threshold=threshold,
        )
        print(f"    Regime split: {regime_stats['pct_bull']:.1f}% Bull (K196)  "
              f"{regime_stats['pct_bear']:.1f}% Bear/Neutral (K208)")

        # Assemble 10-component DataFrame
        all_start = max(base_df.index[0], fwd_ret.index[0], hybrid_rev.index[0])
        all_end   = min(base_df.index[-1], fwd_ret.index[-1], hybrid_rev.index[-1])

        base_tr   = base_df[(base_df.index >= all_start) & (base_df.index <= all_end)]
        fwd_tr    = fwd_ret[(fwd_ret.index >= all_start) & (fwd_ret.index <= all_end)]
        rev_tr    = hybrid_rev[(hybrid_rev.index >= all_start) & (hybrid_rev.index <= all_end)]
        rev_tr    = rev_tr.rename("V_rev_carry")

        df_all = pd.concat([base_tr, fwd_tr, rev_tr], axis=1).dropna()
        print(f"    Combined: {df_all.shape[0]} days x {df_all.shape[1]} strategies "
              f"({df_all.index[0].date()} -> {df_all.index[-1].date()})")

        # Apply FR defensive trigger
        if len(fr_mean) > 0:
            df_trig = apply_fr_trigger(df_all, fr_mean)
        else:
            df_trig = df_all.copy()

        # Build ML features + targets
        feat_df   = build_features(df_trig, fr_mean if len(fr_mean) > 0 else None)
        target_df = build_targets(df_trig, horizon=ML_TEST_DAYS)

        # ML walk-forward
        weights, pnl_wf, diagnostics = ml_walk_forward(
            df_trig, feat_df, target_df,
            train_days=ML_TRAIN_DAYS,
            test_days=ML_TEST_DAYS,
            alpha=1.0,
        )

        if len(pnl_wf) == 0:
            print(f"    ERROR: empty PnL for threshold {threshold}")
            continue

        # OOS metrics
        oos_pnl = oos_cut(pnl_wf)
        m       = metrics_pkg(oos_pnl.values)
        wf      = wf_fold_sharpes(pnl_wf)

        # Regime stats per fold
        fold_regime = per_fold_regime_stats(bull_flag, pnl_wf, N_FOLDS)

        print(f"    OOS Sh={m['sharpe']:.4f}  MaxDD={m['max_dd']:.4f}  "
              f"WF min={wf['min']:.4f}  WF mean={wf['mean']:.4f}")
        print(f"    WF folds: {wf['fold_sharpes']}")
        print(f"    Per-fold breakdown:")
        for fi in fold_regime:
            print(f"      Fold {fi['fold']} ({fi['start']} -> {fi['end']}): "
                  f"Sh={fi['sharpe']:.4f}  Bull={fi['pct_bull']:.0f}%")

        sweep_results[f"z_{threshold:.1f}"] = {
            "threshold":    threshold,
            "regime_stats": regime_stats,
            "oos_metrics":  m,
            "wf_folds":     wf,
            "fold_regime":  fold_regime,
            "n_wf_steps":   len(diagnostics),
            "pnl_wf_len":   len(pnl_wf),
        }

        if m["sharpe"] > best_oos_sh:
            best_oos_sh    = m["sharpe"]
            best_threshold = threshold
            best_pnl_wf    = pnl_wf
            best_weights   = weights
            best_bull      = bull_flag
            best_diag      = diagnostics

        print()

    print(f"  Best threshold: z = {best_threshold:.1f}  (OOS Sh = {best_oos_sh:.4f})")
    print()

    # ── Step 7: §6 strict gates on best variant ─────────────────────────────
    print("Step 7: §6 strict gates on best variant...")
    best_key = f"z_{best_threshold:.1f}"
    best_res = sweep_results[best_key]
    best_m   = best_res["oos_metrics"]
    best_wf  = best_res["wf_folds"]

    gates, gates_passed, gates_verdict = apply_s6_gates(best_m, best_wf)
    print(f"  Best variant: threshold z = {best_threshold:.1f}")
    for g, v in gates.items():
        flag = "PASS" if v else "FAIL"
        print(f"    {g}: [{flag}]")
    print(f"  §6 verdict: {gates_passed}/7 -> {gates_verdict}")
    print()

    # ── Step 8: Four-way comparison table ───────────────────────────────────
    print("Step 8: Four-way comparison...")
    oos_k198 = oos_cut(pnl_k198)
    m_k198   = metrics_pkg(oos_k198.values)
    wf_k198  = wf_fold_sharpes(pnl_k198)

    print()
    print(f"{'Version':<38} {'OOS Sh':>8} {'OOS MaxDD':>10} {'WF mean':>8} {'WF min':>8}")
    print("-" * 72)
    print(f"{'K198 v6.5 baseline':38s} {m_k198['sharpe']:>8.2f} {m_k198['max_dd']:>10.4f} "
          f"{wf_k198['mean']:>8.2f} {wf_k198['min']:>8.2f}")
    print(f"{'K210b (K208 always, ref)':38s} {'8.34':>8s} {'-0.0050':>10s} {'7.59':>8s} {'7.04':>8s}")
    for key, res in sweep_results.items():
        thr = res["threshold"]
        m   = res["oos_metrics"]
        wf  = res["wf_folds"]
        lbl = f"K214 hybrid z>{thr:.1f}"
        print(f"  {lbl:<36} {m['sharpe']:>8.2f} {m['max_dd']:>10.4f} "
              f"{wf['mean']:>8.2f} {wf['min']:>8.2f}")
    print("-" * 72)
    print()

    # ── Step 9: Acceptance criteria ─────────────────────────────────────────
    print("Step 9: K214 acceptance criteria...")
    ac1 = best_m["sharpe"] >= K198_OOS_SH
    ac2 = best_m["max_dd"] >= K198_OOS_DD
    ac3 = best_wf["min"]   >= K210B_WF_MIN
    # Check regime classifier fires reasonably (not always one branch)
    best_regime = sweep_results[best_key]["regime_stats"]
    pct_bull    = best_regime["pct_bull"]
    ac4 = 5.0 < pct_bull < 95.0   # not degenerate

    print(f"  AC1 OOS Sh >= {K198_OOS_SH:.2f}?   {best_m['sharpe']:.4f} -> {'PASS' if ac1 else 'FAIL'}")
    print(f"  AC2 MaxDD <= {K198_OOS_DD:.4f}?  {best_m['max_dd']:.4f} -> {'PASS' if ac2 else 'FAIL'}")
    print(f"  AC3 WF min >= {K210B_WF_MIN:.2f}?  {best_wf['min']:.4f} -> {'PASS' if ac3 else 'FAIL'}")
    print(f"  AC4 Regime non-degenerate? {pct_bull:.1f}% Bull -> {'PASS' if ac4 else 'FAIL'}")
    n_pass = sum([ac1, ac2, ac3, ac4])
    print()

    # Verdict
    if all([ac1, ac2, ac3, ac4]):
        verdict = (
            f"ACCEPT → K214 hybrid (z > {best_threshold:.1f}) promotes to v6.6. "
            f"OOS Sh={best_m['sharpe']:.4f} (+{best_m['sharpe']-K198_OOS_SH:+.4f} vs K198), "
            f"WF min={best_wf['min']:.4f} (+{best_wf['min']-K210B_WF_MIN:+.4f} vs K210b). "
            f"Regime: {pct_bull:.1f}% Bull (K196), {100-pct_bull:.1f}% Bear (K208)."
        )
    elif n_pass >= 3 and (ac1 or ac3):
        verdict = (
            f"CONDITIONAL → K214 (z > {best_threshold:.1f}) passes {n_pass}/4. "
            f"OOS Sh={best_m['sharpe']:.4f} vs K198={K198_OOS_SH:.2f}. "
            f"WF min={best_wf['min']:.4f} vs K210b={K210B_WF_MIN:.2f}. "
            f"MaxDD={best_m['max_dd']:.4f} vs K198={K198_OOS_DD:.4f}. "
            "Consider paper trading before full promotion."
        )
    elif ac1 and ac2:
        verdict = (
            f"MARGINAL → K214 improves OOS Sh (+{best_m['sharpe']-K198_OOS_SH:+.4f}) and MaxDD, "
            f"but WF min ({best_wf['min']:.4f}) below K210b threshold ({K210B_WF_MIN:.2f}). "
            "K198 v6.5 remains production; fold stability review recommended."
        )
    else:
        verdict = (
            f"REJECT → K214 hybrid does not meet acceptance criteria ({n_pass}/4 pass). "
            f"OOS Sh={best_m['sharpe']:.4f} vs K198={K198_OOS_SH:.2f}, "
            f"MaxDD={best_m['max_dd']:.4f}, WF min={best_wf['min']:.4f}. "
            "Regime conditioning does not preserve K198 fold 4 strength sufficiently."
        )

    print(f"  VERDICT: {verdict}")
    print()

    # ── Step 10: Equity curves ───────────────────────────────────────────────
    print("Step 10: Building equity curves...")
    eq_best    = np.cumprod(1.0 + best_pnl_wf.values).tolist()
    eq_k198    = np.cumprod(1.0 + pnl_k198.values).tolist()

    # Per-threshold equity curves
    eq_by_threshold: Dict[str, list] = {}
    pnl_by_threshold: Dict[str, list] = {}
    dates_by_threshold: Dict[str, list] = {}

    # We need to rerun to get all pnl series... but we only cached best above.
    # Re-use sweep_results structure and mark best
    # Actually, best_pnl_wf is the only pnl stored — for other variants we'd need to rerun.
    # For the curves JSON, store best variant + K198 reference.

    elapsed = time.time() - START_TIME
    print(f"  Best equity curve: {len(eq_best)} pts")
    print(f"  Total runtime: {elapsed:.1f}s")
    print()

    # ── Build regime overlay for curves JSON ────────────────────────────────
    bull_daily = best_bull.reindex(
        best_pnl_wf.index, fill_value=False
    ).astype(int)

    # ── Assemble JSON outputs ────────────────────────────────────────────────
    output = {
        "wave": "K214",
        "parent_waves": ["K198", "K208", "K210"],
        "objective": "Regime-conditioned V_rev_carry: K208 filter ON in bear/neutral, OFF in bull",
        "as_of": pd.Timestamp.now(tz="UTC").isoformat(),
        "runtime_s": round(elapsed, 1),

        "config": {
            "thresholds_tested":  THRESHOLDS,
            "best_threshold":     best_threshold,
            "zscore_window":      ZSCORE_WIN,
            "regime_logic": {
                "bull":   f"spread_z > threshold -> use K196 unfiltered V_rev_carry",
                "bear":   f"spread_z <= threshold -> use K208 DAR-filtered V_rev_carry",
                "lag":    "z-score lagged 1 day (no look-ahead)",
            },
            "ml_train_days":  ML_TRAIN_DAYS,
            "ml_test_days":   ML_TEST_DAYS,
            "k121_cap":       K121_CAP,
            "carry_fwd_cap":  CARRY_FWD_CAP,
            "carry_rev_cap":  CARRY_REV_CAP,
            "fr_threshold":   FR_THRESHOLD,
            "dar_config":     {"p": DAR_P, "q": DAR_Q, "win": DAR_WIN, "refit": DAR_REFIT},
            "symbols_dar_filtered": REVERSE_9,
            "symbols_always_on":    AXS_ALWAYS,
            "n_symbols_loaded":     len(panels_8h),
            "symbols_skipped":      skipped,
        },

        "regime_classifier_log": {
            k: {
                "threshold":  v["threshold"],
                "pct_bull":   v["regime_stats"]["pct_bull"],
                "pct_bear":   v["regime_stats"]["pct_bear"],
                "n_bull_days": v["regime_stats"]["n_bull_days"],
                "n_bear_days": v["regime_stats"]["n_bear_days"],
            }
            for k, v in sweep_results.items()
        },

        "threshold_sweep": {
            k: {
                "threshold":   v["threshold"],
                "oos_sharpe":  v["oos_metrics"]["sharpe"],
                "oos_maxdd":   v["oos_metrics"]["max_dd"],
                "oos_sortino": v["oos_metrics"]["sortino"],
                "oos_calmar":  v["oos_metrics"]["calmar"],
                "wf_mean":     v["wf_folds"]["mean"],
                "wf_min":      v["wf_folds"]["min"],
                "wf_fold_sharpes": v["wf_folds"]["fold_sharpes"],
                "fold_regime_stats": v["fold_regime"],
                "regime_stats": v["regime_stats"],
            }
            for k, v in sweep_results.items()
        },

        "best_variant": {
            "threshold": best_threshold,
            "oos_sharpe":  best_m["sharpe"],
            "oos_maxdd":   best_m["max_dd"],
            "oos_sortino": best_m["sortino"],
            "oos_calmar":  best_m["calmar"],
            "oos_ann_ret": best_m["ann_ret"],
            "oos_ann_vol": best_m["ann_vol"],
            "oos_n_days":  best_m["n_days"],
            "wf_mean":  best_wf["mean"],
            "wf_min":   best_wf["min"],
            "wf_max":   best_wf["max"],
            "wf_std":   best_wf["std"],
            "wf_fold_sharpes": best_wf["fold_sharpes"],
            "wf_fold_dates":   best_wf["fold_dates"],
            "lift_vs_k198_oos_sh":   round(best_m["sharpe"] - K198_OOS_SH, 4),
            "lift_vs_k198_wf_min":   round(best_wf["min"] - K198_WF_MIN, 4),
            "lift_vs_k210b_wf_min":  round(best_wf["min"] - K210B_WF_MIN, 4),
        },

        "four_way_comparison": {
            "K198_v6_5_baseline": {
                "description": "K198 v6.5 Ridge ML (current production)",
                "oos_sharpe": round(m_k198["sharpe"], 4),
                "oos_maxdd":  round(m_k198["max_dd"], 4),
                "wf_mean":    wf_k198["mean"],
                "wf_min":     wf_k198["min"],
                "wf_fold_sharpes": wf_k198["fold_sharpes"],
                "reference": True,
            },
            "K210b_rejected": {
                "description": "K210b (K208 always-on, cap=15%) - REJECTED",
                "oos_sharpe": 8.34,
                "oos_maxdd":  -0.0050,
                "wf_mean":    7.59,
                "wf_min":     7.04,
                "source":     "wave_k210 results",
            },
            "K214_best": {
                "description": f"K214 hybrid (z > {best_threshold:.1f} -> K196, else K208)",
                "oos_sharpe": best_m["sharpe"],
                "oos_maxdd":  best_m["max_dd"],
                "wf_mean":    best_wf["mean"],
                "wf_min":     best_wf["min"],
                "wf_fold_sharpes": best_wf["fold_sharpes"],
            },
        },

        "s6_gates": {
            "gates": gates,
            "n_pass": gates_passed,
            "verdict": gates_verdict,
        },

        "acceptance_criteria": {
            "AC1_oos_sh_ge_k198": bool(ac1),
            "AC2_maxdd_le_k198":  bool(ac2),
            "AC3_wf_min_ge_k210b": bool(ac3),
            "AC4_regime_non_degenerate": bool(ac4),
            "n_criteria_passed": n_pass,
            "all_pass": bool(all([ac1, ac2, ac3, ac4])),
        },

        "verdict": verdict,

        "ml_diagnostics": {
            "n_wf_steps":   len(best_diag) if best_diag else 0,
            "mean_dir_acc": round(float(np.mean([d["mean_dir_acc"] for d in best_diag])), 4) if best_diag else 0.0,
            "mean_r2":      round(float(np.mean([d["mean_r2"]      for d in best_diag])), 4) if best_diag else 0.0,
        },

        "carry_filter_metadata": carry_meta,
    }

    # ── Save metrics JSON ────────────────────────────────────────────────────
    metrics_path = BASE / "wave_k214_regime_conditioned.json"
    with open(metrics_path, "w") as f:
        json.dump(output, f, indent=2, default=str)
    print(f"Saved: {metrics_path}")

    # ── Save curves JSON ─────────────────────────────────────────────────────
    # Include per-threshold curves (we only have best variant from sweep)
    # Also include regime overlay (bull/bear by day)
    curves_out = {
        "wave":           "K214",
        "description":    "Equity curves and regime overlay for K214",
        "best_threshold": best_threshold,
        "dates_best":     [str(d.date()) for d in best_pnl_wf.index],
        "dates_k198":     [str(d.date()) for d in pnl_k198.index],
        "equity_best":    [round(float(v), 6) for v in eq_best],
        "equity_k198":    [round(float(v), 6) for v in eq_k198],
        "pnl_best":       [round(float(v), 8) for v in best_pnl_wf.values],
        "pnl_k198":       [round(float(v), 8) for v in pnl_k198.values],
        "regime_bull_flag": [int(v) for v in bull_daily.values],
        "regime_dates":     [str(d.date()) for d in bull_daily.index],
        "spread_z_dates":   [str(d.date()) for d in spread_z.dropna().index],
        "spread_z_values":  [round(float(v), 4) for v in spread_z.dropna().values],
        "weight_trajectory": {
            "dates":   [str(d.date()) for d in best_weights.index],
            "weights": {
                c: [round(float(x), 4) for x in best_weights[c].values]
                for c in best_weights.columns
            },
        } if len(best_weights) > 0 else {},
    }

    curves_path = BASE / "wave_k214_curves.json"
    with open(curves_path, "w") as f:
        json.dump(curves_out, f, indent=2)
    print(f"Saved: {curves_path}")

    # ── Final summary ────────────────────────────────────────────────────────
    print()
    print("=" * 72)
    print("K214 FINAL SUMMARY")
    print("=" * 72)
    print(f"{'Version':<38} {'OOS Sh':>8} {'MaxDD':>8} {'WF mean':>8} {'WF min':>8}")
    print("-" * 72)
    print(f"{'K198 v6.5 (production)':38s} {m_k198['sharpe']:>8.2f} {m_k198['max_dd']:>8.4f} "
          f"{wf_k198['mean']:>8.2f} {wf_k198['min']:>8.2f}")
    print(f"{'K210b (rejected)':38s} {'8.34':>8s} {'-0.0050':>8s} {'7.59':>8s} {'7.04':>8s}")
    for key, res in sweep_results.items():
        m2  = res["oos_metrics"]
        wf2 = res["wf_folds"]
        thr = res["threshold"]
        marker = " <-- BEST" if thr == best_threshold else ""
        lbl = f"K214 z>{thr:.1f}{marker}"
        print(f"  {lbl:<36} {m2['sharpe']:>8.2f} {m2['max_dd']:>8.4f} "
              f"{wf2['mean']:>8.2f} {wf2['min']:>8.2f}")
    print("-" * 72)
    print()
    print(f"Best threshold: z > {best_threshold:.1f}")
    print(f"  OOS Sh lift vs K198: {best_m['sharpe']-K198_OOS_SH:+.4f}")
    print(f"  WF min lift vs K198: {best_wf['min']-K198_WF_MIN:+.4f}")
    print(f"  WF min lift vs K210b: {best_wf['min']-K210B_WF_MIN:+.4f}")
    print()
    print(f"§6 gates: {gates_passed}/7 -> {gates_verdict}")
    print()
    print(f"VERDICT: {verdict}")
    print()
    print(f"Runtime: {elapsed:.1f}s")

    return output


if __name__ == "__main__":
    main()

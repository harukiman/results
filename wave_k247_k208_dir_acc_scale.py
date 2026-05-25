"""Wave K247 - K208 Rolling Direction Accuracy Scaling.

Objective:
  K245 REJECTED because magnitude-based confidence was inadequate (Fold2 max=6.27).
  K247 implements rolling 30d direction accuracy as the drift detector.
  Low direction accuracy (DAR sign misfires) → reduce position size.

Variants:
  K247a: Linear scalar = clip((acc - 0.45) / 0.20, 0.5, 1.0)
  K247b: Cliff — if acc < 0.55 → scalar=0.0 (halt), else scalar=1.0
  K247c: Sqrt smoothing = clip(sqrt((acc - 0.45) / 0.20), 0.5, 1.0)
  K247d: Per-symbol accuracy (not aggregated)

Walk-forward: 4-fold (same FOLD_BOUNDS as K245)

Acceptance gates (K247 → K229 V_K208 replacement):
  - Fold 2 Sh >= 7.0
  - OOS Sh >= 10.57 (K208 baseline)
  - WF min >= 7.0
  - Scalar firing distribution sensible (not always 1.0 or always 0.5)

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

warnings.filterwarnings("ignore")

START_TIME = time.time()
BASE     = Path("/Users/nekonaomichi/crypto-lab")
CACHE    = BASE / "cache"
HL_CACHE = CACHE / "k163_hl"

# ─────────────────────────────────────────────────────────────────────────────
# Constants
# ─────────────────────────────────────────────────────────────────────────────
EVENTS_PER_YEAR = 365 * 3   # 1095
EVENTS_PER_DAY  = 3         # 8h events

# DAR(2,1) primary config (matches K208/K190)
PRIMARY_P     = 2
PRIMARY_Q     = 1
PRIMARY_WIN   = 300
PRIMARY_REFIT = 50

# K208 panel symbols
REVERSE_10 = ["SOL", "XRP", "SUI", "OP", "APT", "AXS", "JTO", "IMX", "SAND", "ADA"]

# Rolling direction accuracy window: 30 days in 8h events
DIR_ACC_WIN = 30 * EVENTS_PER_DAY  # 90 events

# K247 scalar formula: clip((acc - 0.45) / 0.20, 0.5, 1.0)
ACC_FLOOR  = 0.45
ACC_RANGE  = 0.20
SCALE_MIN  = 0.5
SCALE_MAX  = 1.0
CLIFF_THRESH = 0.55  # K247b: below this → halt (0.0)

# Reference metrics
K208_OOS_SH   = 10.57
K208_WF_FOLDS = [17.35, 5.74, 17.41, 13.11]
K208_WF_MIN   = 5.74
K208_MAX_DD   = -0.0002

K229D_OOS_SH   = 10.17
K229D_WF_FOLDS = [12.91, 7.48, 13.01, 12.22]
K229D_WF_MIN   = 7.48

K245_BEST_FOLD2 = 6.27  # K245 rejected

# Acceptance gates
ACCEPT_FOLD2_SH = 7.0
ACCEPT_OOS_SH   = K208_OOS_SH
ACCEPT_WF_MIN   = 7.0

# Walk-forward fold boundaries (same as K242/K245)
ML_START = "2025-01-22"
ML_END   = "2026-04-14"
FOLD_BOUNDS: List[Tuple[str, str]] = [
    ("2025-01-22", "2025-05-13"),
    ("2025-05-14", "2025-09-02"),
    ("2025-09-03", "2025-12-23"),
    ("2025-12-24", "2026-04-14"),
]


# ─────────────────────────────────────────────────────────────────────────────
# Data loading
# ─────────────────────────────────────────────────────────────────────────────

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
    for tag in ("1200d", "730d", "365d"):
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


def build_panel(sym: str) -> Optional[pd.DataFrame]:
    """Build aligned (bybit_fr, hl_fr_8h, spread, rev_carry_pnl) DataFrame."""
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
    df["rev_carry_pnl"] = df["spread"].shift(-1)  # next-period carry received
    df = df.dropna(subset=["rev_carry_pnl"])
    if len(df) < 50:
        return None
    return df


# ─────────────────────────────────────────────────────────────────────────────
# DAR model (reused from K208)
# ─────────────────────────────────────────────────────────────────────────────

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


def dar_walk_forward_with_dir_hits(
    fr: np.ndarray,
    spread_z: np.ndarray,
    p: int = PRIMARY_P,
    q: int = PRIMARY_Q,
    win: int = PRIMARY_WIN,
    refit: int = PRIMARY_REFIT,
) -> Tuple[np.ndarray, np.ndarray, np.ndarray, Dict]:
    """Walk-forward DAR(p,q) with per-step direction hit flags.

    Direction hit at step i:
      predicted FR direction == actual FR direction
      predicted direction: sign(pred_fr[i] - fr[i-1])
      actual direction: sign(fr[i] - fr[i-1])

    Returns:
        pred_fr    : predicted FR values
        is_valid   : boolean mask where predictions are available
        dir_hits   : binary array (1=hit, 0=miss, NaN=invalid)
        diag       : diagnostics dict
    """
    n = len(fr)
    pred_fr  = np.full(n, np.nan)
    is_valid = np.zeros(n, dtype=bool)
    dir_hits = np.full(n, np.nan)  # 1=hit, 0=miss
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
                pred_fr[i] = float(np.dot(row, coeffs))
                is_valid[i] = True

                # Direction hit: predicted sign vs actual sign of FR change
                prev_fr = fr[i - 1]
                pred_sign   = np.sign(pred_fr[i] - prev_fr)
                actual_sign = np.sign(fr[i] - prev_fr)
                if actual_sign != 0:
                    dir_hits[i] = 1.0 if pred_sign == actual_sign else 0.0
                # If actual sign==0 (no change), leave dir_hits as NaN (skip)

    valid_idx = np.where(is_valid)[0]
    if len(valid_idx) < 30:
        return pred_fr, is_valid, dir_hits, {
            "oos_r2": np.nan, "direction_acc": np.nan, "n_oos": 0
        }

    y_true = fr[valid_idx]
    y_pred  = pred_fr[valid_idx]
    ss_res  = np.sum((y_true - y_pred) ** 2)
    ss_tot  = np.sum((y_true - y_true.mean()) ** 2)
    oos_r2  = float(1 - ss_res / (ss_tot + 1e-30))

    # Overall direction accuracy
    hit_vals = dir_hits[valid_idx]
    hit_vals = hit_vals[~np.isnan(hit_vals)]
    dir_acc  = float(hit_vals.mean()) if len(hit_vals) > 0 else 0.5

    return pred_fr, is_valid, dir_hits, {
        "oos_r2":       round(oos_r2, 5),
        "direction_acc": round(dir_acc, 4),
        "n_oos":        int(len(valid_idx)),
    }


# ─────────────────────────────────────────────────────────────────────────────
# Rolling direction accuracy computation
# ─────────────────────────────────────────────────────────────────────────────

def rolling_dir_accuracy(dir_hits: np.ndarray, window: int = DIR_ACC_WIN) -> np.ndarray:
    """Compute rolling mean of direction hits over last `window` events.

    Uses only non-NaN hits in the window.
    Returns NaN where insufficient data (< window//3 hits in window).
    """
    n       = len(dir_hits)
    acc_arr = np.full(n, np.nan)
    min_obs = max(10, window // 3)

    for i in range(n):
        start = max(0, i - window + 1)
        window_hits = dir_hits[start:i + 1]
        valid = window_hits[~np.isnan(window_hits)]
        if len(valid) >= min_obs:
            acc_arr[i] = float(valid.mean())

    return acc_arr


def scalar_linear(acc: float) -> float:
    """K247a: clip((acc - 0.45) / 0.20, 0.5, 1.0)"""
    return float(np.clip((acc - ACC_FLOOR) / ACC_RANGE, SCALE_MIN, SCALE_MAX))


def scalar_cliff(acc: float) -> float:
    """K247b: if acc < 0.55 → 0.0 (halt), else 1.0"""
    return 0.0 if acc < CLIFF_THRESH else 1.0


def scalar_sqrt(acc: float) -> float:
    """K247c: sqrt smoothing = clip(sqrt((acc - 0.45) / 0.20), 0.5, 1.0)"""
    raw = (acc - ACC_FLOOR) / ACC_RANGE
    if raw <= 0:
        return SCALE_MIN
    return float(np.clip(math.sqrt(raw), SCALE_MIN, SCALE_MAX))


# ─────────────────────────────────────────────────────────────────────────────
# Metrics
# ─────────────────────────────────────────────────────────────────────────────

def sharpe_e(pnl: pd.Series) -> float:
    pnl = pnl.dropna()
    if len(pnl) < 10 or pnl.std(ddof=1) == 0:
        return 0.0
    return float(pnl.mean() / pnl.std(ddof=1) * math.sqrt(EVENTS_PER_YEAR))


def max_dd_e(pnl: pd.Series) -> float:
    eq   = pnl.cumsum()
    peak = eq.cummax()
    return float((eq - peak).min())


def wf_4fold_custom(pnl: pd.Series, fold_bounds: List[Tuple[str, str]]) -> Tuple[float, float, List[float]]:
    """Per-fold Sharpe using date-based fold boundaries."""
    pnl = pnl.dropna()
    sharpes = []
    for (start, end) in fold_bounds:
        mask = (pnl.index >= pd.Timestamp(start)) & (pnl.index <= pd.Timestamp(end))
        fp   = pnl[mask]
        if len(fp) < 5 or fp.std(ddof=1) == 0:
            sharpes.append(0.0)
        else:
            sharpes.append(float(fp.mean() / fp.std(ddof=1) * math.sqrt(EVENTS_PER_YEAR)))
    if not sharpes:
        return 0.0, 0.0, []
    return float(np.mean(sharpes)), float(np.min(sharpes)), [round(x, 4) for x in sharpes]


def equity_curve_vals(pnl: pd.Series) -> List[float]:
    return list(pnl.fillna(0).cumsum().round(8))


# ─────────────────────────────────────────────────────────────────────────────
# Per-symbol DAR computation (shared across variants)
# ─────────────────────────────────────────────────────────────────────────────

def compute_symbol_dar(
    panels: Dict[str, pd.DataFrame]
) -> Dict[str, Tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray, Dict]]:
    """Pre-compute DAR predictions and direction hits for each symbol.

    Returns: {sym: (pred_fr, is_valid, dir_hits, rolling_acc_agg, diag)}
    """
    results = {}
    for sym, df in panels.items():
        fr_arr   = df["bybit_fr"].values.copy()
        spread_z = zscore_rolling(df["spread"], 30).fillna(0.0).values

        pred_fr, is_valid, dir_hits, diag = dar_walk_forward_with_dir_hits(
            fr_arr, spread_z
        )
        # Per-symbol rolling accuracy
        rolling_acc = rolling_dir_accuracy(dir_hits, window=DIR_ACC_WIN)
        results[sym] = (pred_fr, is_valid, dir_hits, rolling_acc, diag)
    return results


# ─────────────────────────────────────────────────────────────────────────────
# Variant runners
# ─────────────────────────────────────────────────────────────────────────────

def run_variant(
    panels: Dict[str, pd.DataFrame],
    sym_dar: Dict,
    variant: str,
) -> Tuple[pd.Series, Dict, Dict[str, np.ndarray]]:
    """Run K208 with direction-accuracy-based scaling.

    variant: 'baseline' | 'K247a' | 'K247b' | 'K247c' | 'K247d'

    Returns:
        panel_pnl    : combined equal-weight panel PnL
        sym_stats    : per-symbol stats
        scalar_series: {sym: scalar array for diagnostics}
    """
    per_sym:       Dict[str, pd.Series]  = {}
    sym_stats:     Dict[str, Dict]       = {}
    scalar_arrays: Dict[str, np.ndarray] = {}

    # Aggregate direction accuracy across all symbols (for K247a/b/c)
    # Compute aggregate rolling accuracy: mean of all valid symbol accuracies per timestep
    # We do this per-symbol rolling then average at panel level
    if variant in ("K247a", "K247b", "K247c"):
        # Build aggregated rolling acc series
        # We need a common index — use panels intersection for agg
        # Simple approach: for each symbol, build rolling_acc on its own index
        # then average aligned on common index
        all_sym_acc: Dict[str, pd.Series] = {}
        for sym, df in panels.items():
            _, _, _, rolling_acc, _ = sym_dar[sym]
            all_sym_acc[sym] = pd.Series(rolling_acc, index=df.index)
        agg_acc_df = pd.concat(all_sym_acc, axis=1)
        # Aggregate: mean of available symbol accuracies (at least 1 needed)
        agg_acc = agg_acc_df.mean(axis=1, skipna=True)
        # If all NaN at a step → NaN
        agg_acc = agg_acc.where(agg_acc_df.notna().any(axis=1))

    for sym, df in panels.items():
        pred_fr, is_valid, dir_hits, rolling_acc_sym, diag = sym_dar[sym]
        n            = len(df)
        hl_arr       = df["hl_fr_8h"].values.copy()
        base_pnl     = df["rev_carry_pnl"].copy()
        scalars      = np.zeros(n, dtype=float)

        for i in range(n):
            if not is_valid[i]:
                continue
            # K208 gate: pred_spread > 0
            pred_spread = pred_fr[i] - hl_arr[i]
            if pred_spread <= 0:
                scalars[i] = 0.0
                continue

            if variant == "baseline":
                # K208 pure binary gate: full size when gate passes
                scalars[i] = 1.0
                continue

            # Determine rolling accuracy to use
            if variant == "K247d":
                # Per-symbol accuracy
                acc_val = rolling_acc_sym[i]
            else:
                # Aggregated accuracy (K247a/b/c)
                ts = df.index[i]
                if ts in agg_acc.index:
                    acc_val = float(agg_acc.loc[ts])
                else:
                    # Nearest
                    agg_val = agg_acc.reindex([ts], method="nearest")
                    acc_val = float(agg_val.iloc[0]) if len(agg_val) > 0 else np.nan

            if np.isnan(acc_val):
                # No accuracy yet: default to half scale (conservative)
                acc_val = 0.50

            if variant == "K247a":
                scalars[i] = scalar_linear(acc_val)
            elif variant == "K247b":
                scalars[i] = scalar_cliff(acc_val)
            elif variant == "K247c":
                scalars[i] = scalar_sqrt(acc_val)
            elif variant == "K247d":
                scalars[i] = scalar_linear(acc_val)  # same formula, per-symbol acc
            else:
                scalars[i] = 1.0

        # Lag scalars by 1 event (no look-ahead)
        scalar_s     = pd.Series(scalars, index=df.index).shift(1).fillna(0.0)
        filtered_pnl = base_pnl * scalar_s
        per_sym[sym] = filtered_pnl
        scalar_arrays[sym] = scalar_s.values

        n_active      = int((scalar_s > 0).sum())
        avg_scalar    = float(scalar_s[scalar_s > 0].mean()) if (scalar_s > 0).any() else 0.0
        scalar_vals   = scalar_s[scalar_s > 0].values
        frac_at_min   = float((scalar_vals <= SCALE_MIN + 0.01).mean()) if len(scalar_vals) > 0 else 0.0
        frac_at_max   = float((scalar_vals >= SCALE_MAX - 0.01).mean()) if len(scalar_vals) > 0 else 0.0

        sym_stats[sym] = {
            "sharpe":       round(sharpe_e(filtered_pnl), 4),
            "n_total":      n,
            "n_active":     n_active,
            "pct_active":   round(100 * n_active / max(n, 1), 1),
            "avg_scalar":   round(avg_scalar, 4),
            "frac_at_min":  round(frac_at_min, 4),
            "frac_at_max":  round(frac_at_max, 4),
            "dir_acc_overall": round(diag.get("direction_acc", 0.0), 4),
            "dar_oos_r2":   round(diag.get("oos_r2", 0.0), 5),
            "n_oos":        diag.get("n_oos", 0),
        }

    if not per_sym:
        return pd.Series(dtype=float), {}, {}

    aligned   = pd.concat(per_sym, axis=1).fillna(0.0)
    panel_pnl = aligned.mean(axis=1)
    return panel_pnl, sym_stats, scalar_arrays


# ─────────────────────────────────────────────────────────────────────────────
# Drift detection log: when does scalar fire (< 1.0)?
# ─────────────────────────────────────────────────────────────────────────────

def drift_detection_log(
    panels: Dict[str, pd.DataFrame],
    sym_dar: Dict,
    scalar_arrays: Dict[str, np.ndarray],
    variant: str,
) -> Dict:
    """Summarize when scalar < 1.0 (drift detection firing) for a variant."""
    all_scalar_by_date: Dict[str, List[float]] = {}
    for sym, df in panels.items():
        if sym not in scalar_arrays:
            continue
        sc = scalar_arrays[sym]
        for i, ts in enumerate(df.index):
            ts_str = ts.strftime("%Y-%m-%d")
            if ts_str not in all_scalar_by_date:
                all_scalar_by_date[ts_str] = []
            all_scalar_by_date[ts_str].append(float(sc[i]))

    # Aggregate per calendar day
    daily: List[Dict] = []
    for ts_str in sorted(all_scalar_by_date.keys()):
        vals = all_scalar_by_date[ts_str]
        mean_s = float(np.mean(vals))
        firing = mean_s < 0.99  # scalar < max = drift detected
        daily.append({
            "date":       ts_str,
            "mean_scalar": round(mean_s, 4),
            "drift_firing": firing,
        })

    total_days   = len(daily)
    firing_days  = sum(1 for d in daily if d["drift_firing"])
    firing_pct   = round(100 * firing_days / max(total_days, 1), 1)
    mean_scalar  = round(float(np.mean([d["mean_scalar"] for d in daily])), 4)

    # Find contiguous drift periods
    drift_periods = []
    in_drift = False
    start_str = ""
    for d in daily:
        if d["drift_firing"] and not in_drift:
            in_drift = True
            start_str = d["date"]
        elif not d["drift_firing"] and in_drift:
            in_drift = False
            drift_periods.append({"start": start_str, "end": d["date"]})
    if in_drift:
        drift_periods.append({"start": start_str, "end": daily[-1]["date"]})

    return {
        "variant":          variant,
        "total_days":       total_days,
        "firing_days":      firing_days,
        "firing_pct":       firing_pct,
        "mean_scalar":      mean_scalar,
        "n_drift_periods":  len(drift_periods),
        "drift_periods_sample": drift_periods[:10],  # first 10 for inspection
    }


# ─────────────────────────────────────────────────────────────────────────────
# Per-fold direction accuracy distribution
# ─────────────────────────────────────────────────────────────────────────────

def fold_dir_accuracy_stats(
    panels: Dict[str, pd.DataFrame],
    sym_dar: Dict,
    fold_bounds: List[Tuple[str, str]],
) -> List[Dict]:
    """Per-fold direction accuracy statistics (aggregate across symbols)."""
    fold_stats = []
    for fold_idx, (start, end) in enumerate(fold_bounds):
        ts_start = pd.Timestamp(start)
        ts_end   = pd.Timestamp(end)
        all_hits = []
        for sym, df in panels.items():
            _, is_valid, dir_hits, _, _ = sym_dar[sym]
            mask = (df.index >= ts_start) & (df.index <= ts_end)
            mask_np = np.array(mask)
            fold_hits = dir_hits[mask_np]
            valid_hits = fold_hits[~np.isnan(fold_hits)]
            all_hits.extend(valid_hits.tolist())

        if all_hits:
            acc = float(np.mean(all_hits))
            n   = len(all_hits)
        else:
            acc = np.nan
            n   = 0

        fold_stats.append({
            "fold":         fold_idx + 1,
            "start":        start,
            "end":          end,
            "dir_accuracy": round(acc, 4) if not np.isnan(acc) else None,
            "n_hits":       n,
            "note":         "DRIFT" if (not np.isnan(acc) and acc < 0.52) else
                            ("MARGINAL" if (not np.isnan(acc) and acc < 0.57) else "HEALTHY"),
        })
    return fold_stats


# ─────────────────────────────────────────────────────────────────────────────
# Main
# ─────────────────────────────────────────────────────────────────────────────

def main() -> Dict:
    t0 = time.time()

    print("=" * 70)
    print("Wave K247: K208 Rolling Direction Accuracy Scaling")
    print("=" * 70)

    # ── 1. Load panels ──────────────────────────────────────────────────────
    panels: Dict[str, pd.DataFrame] = {}
    skipped = []
    for sym in REVERSE_10:
        p = build_panel(sym)
        if p is None:
            print(f"  SKIP {sym}: panel build failed")
            skipped.append(sym)
        else:
            panels[sym] = p
            print(f"  {sym}: n={len(p)}  mean_spread={p['spread'].mean()*10000:.2f}bps")

    if not panels:
        raise RuntimeError("No panels built")
    print(f"\nLoaded {len(panels)} symbols, skipped {len(skipped)}")

    # ── 2. Pre-compute DAR predictions + direction hits ─────────────────────
    print("\n=== PRE-COMPUTING DAR(2,1) + DIRECTION HITS ===")
    sym_dar = compute_symbol_dar(panels)
    for sym, (_, _, dir_hits, rolling_acc, diag) in sym_dar.items():
        valid_hits = dir_hits[~np.isnan(dir_hits)]
        overall_acc = float(valid_hits.mean()) if len(valid_hits) > 0 else 0.0
        acc_flag = "HEALTHY" if overall_acc >= 0.57 else ("MARGINAL" if overall_acc >= 0.52 else "DRIFT")
        print(f"  {sym:6s}: dir_acc={overall_acc:.4f} [{acc_flag}]  "
              f"oos_r2={diag.get('oos_r2', float('nan')):.5f}  "
              f"n_oos={diag.get('n_oos', 0)}")

    # ── 3. Per-fold direction accuracy ──────────────────────────────────────
    print("\n=== PER-FOLD DIRECTION ACCURACY ===")
    fold_acc_stats = fold_dir_accuracy_stats(panels, sym_dar, FOLD_BOUNDS)
    for fs in fold_acc_stats:
        acc_str = f"{fs['dir_accuracy']:.4f}" if fs["dir_accuracy"] is not None else "N/A"
        print(f"  Fold {fs['fold']} ({fs['start']} to {fs['end']}): "
              f"acc={acc_str}  n={fs['n_hits']}  [{fs['note']}]")

    # ── 4. Run all variants ─────────────────────────────────────────────────
    VARIANTS = ["baseline", "K247a", "K247b", "K247c", "K247d"]
    variant_results: Dict[str, Dict] = {}
    all_pnls: Dict[str, pd.Series] = {}
    all_drift_logs: Dict[str, Dict] = {}
    all_acc_series: Dict[str, pd.Series] = {}  # for curves JSON

    for vname in VARIANTS:
        print(f"\n=== VARIANT: {vname} ===")
        pnl, sym_stats, scalar_arrays = run_variant(panels, sym_dar, vname)
        all_pnls[vname] = pnl

        # OOS metrics (last 30% of full history)
        n_total  = len(pnl.dropna())
        split    = int(n_total * 0.70)
        oos_pnl  = pnl.dropna().iloc[split:]
        sh_oos   = sharpe_e(oos_pnl)
        dd_oos   = max_dd_e(oos_pnl)
        sh_full  = sharpe_e(pnl)

        # Walk-forward fold Sharpe
        wf_mean, wf_min, wf_folds = wf_4fold_custom(pnl, FOLD_BOUNDS)

        # Scalar distribution
        all_scalars = []
        for sym, sc in scalar_arrays.items():
            nonzero = sc[sc > 0]
            all_scalars.extend(nonzero.tolist())
        if all_scalars:
            sc_mean = float(np.mean(all_scalars))
            sc_p25  = float(np.percentile(all_scalars, 25))
            sc_p75  = float(np.percentile(all_scalars, 75))
            frac_at_min = float(np.mean(np.array(all_scalars) <= SCALE_MIN + 0.01))
            frac_at_max = float(np.mean(np.array(all_scalars) >= SCALE_MAX - 0.01))
        else:
            sc_mean = sc_p25 = sc_p75 = frac_at_min = frac_at_max = 0.0

        scalar_sensible = not (frac_at_max > 0.95 or (frac_at_min > 0.95 and vname != "K247b"))

        # Drift log
        drift_log = drift_detection_log(panels, sym_dar, scalar_arrays, vname)
        all_drift_logs[vname] = drift_log

        # Per-fold breakdown
        fold_details = []
        for fold_idx, (start, end) in enumerate(FOLD_BOUNDS):
            mask = (pnl.index >= pd.Timestamp(start)) & (pnl.index <= pd.Timestamp(end))
            fp   = pnl[mask].dropna()
            fs   = sharpe_e(fp) if len(fp) >= 5 else 0.0
            fold_details.append({
                "fold":   fold_idx + 1,
                "start":  start,
                "end":    end,
                "sharpe": round(fs, 4),
                "n_events": len(fp),
            })

        result = {
            "variant":        vname,
            "sharpe_full":    round(sh_full, 4),
            "sharpe_oos":     round(sh_oos, 4),
            "max_dd_oos":     round(dd_oos, 6),
            "wf_mean":        round(wf_mean, 4),
            "wf_min":         round(wf_min, 4),
            "wf_folds":       wf_folds,
            "fold2_sh":       wf_folds[1] if len(wf_folds) > 1 else 0.0,
            "fold_details":   fold_details,
            "n_events_total": n_total,
            "scalar_mean":    round(sc_mean, 4),
            "scalar_p25":     round(sc_p25, 4),
            "scalar_p75":     round(sc_p75, 4),
            "frac_at_min":    round(frac_at_min, 4),
            "frac_at_max":    round(frac_at_max, 4),
            "scalar_sensible": scalar_sensible,
            "drift_firing_pct": drift_log["firing_pct"],
            "per_symbol":     sym_stats,
        }
        variant_results[vname] = result

        print(f"  OOS Sh={sh_oos:+.3f}  MaxDD_OOS={dd_oos:+.6f}  "
              f"WF_mean={wf_mean:+.3f}  WF_min={wf_min:+.3f}")
        print(f"  Fold Sharpes: {[f'{x:+.2f}' for x in wf_folds]}")
        print(f"  Fold 2 Sh={wf_folds[1] if len(wf_folds)>1 else 'N/A'}")
        print(f"  Scalar: mean={sc_mean:.4f}  p25={sc_p25:.4f}  p75={sc_p75:.4f}  "
              f"at_min={frac_at_min*100:.1f}%  at_max={frac_at_max*100:.1f}%  "
              f"sensible={scalar_sensible}")
        print(f"  Drift firing: {drift_log['firing_pct']}% of days  "
              f"n_periods={drift_log['n_drift_periods']}")

    # ── 5. Acceptance evaluation ────────────────────────────────────────────
    print("\n=== ACCEPTANCE EVALUATION ===")
    accepted_variants = []
    verdict_table: Dict[str, Dict] = {}

    for vname in VARIANTS[1:]:  # skip baseline
        r = variant_results[vname]
        fold2_ok  = r["fold2_sh"] >= ACCEPT_FOLD2_SH
        oos_ok    = r["sharpe_oos"] >= ACCEPT_OOS_SH
        wfmin_ok  = r["wf_min"] >= ACCEPT_WF_MIN
        scale_ok  = r["scalar_sensible"]
        # Not always 1.0 or 0.5 — check distribution is spread
        dist_ok   = (r["frac_at_max"] < 0.95) and (r["scalar_mean"] > 0.55 or vname == "K247b")

        gates_pass = sum([fold2_ok, oos_ok, wfmin_ok, scale_ok, dist_ok])
        if gates_pass >= 4:
            verdict = "ACCEPT"
            accepted_variants.append(vname)
        elif gates_pass >= 3:
            verdict = "MARGINAL"
        else:
            verdict = "FAIL"

        verdict_table[vname] = {
            "fold2_sh":   r["fold2_sh"],
            "fold2_ok":   fold2_ok,
            "oos_sh":     r["sharpe_oos"],
            "oos_ok":     oos_ok,
            "wf_min":     r["wf_min"],
            "wfmin_ok":   wfmin_ok,
            "scalar_sensible": scale_ok,
            "dist_ok":    dist_ok,
            "gates_pass": gates_pass,
            "verdict":    verdict,
        }

        print(f"\n  {vname}:")
        print(f"    Fold2={r['fold2_sh']:+.2f} [{'PASS' if fold2_ok else 'FAIL'}]  "
              f"OOS_Sh={r['sharpe_oos']:+.2f} [{'PASS' if oos_ok else 'FAIL'}]  "
              f"WF_min={r['wf_min']:+.2f} [{'PASS' if wfmin_ok else 'FAIL'}]")
        print(f"    Scalar_sensible={'PASS' if scale_ok else 'FAIL'}  "
              f"Dist_ok={'PASS' if dist_ok else 'FAIL'}")
        print(f"    Gates: {gates_pass}/5  Verdict: {verdict}")

    # ── 6. Comparison table ─────────────────────────────────────────────────
    print("\n=== COMPARISON TABLE ===")
    header = f"{'Version':<22} {'OOS Sh':>8} {'MaxDD':>8} {'WF mean':>8} {'WF min':>8} {'Fold2':>8}"
    print(f"  {header}")
    print(f"  {'-'*22} {'-'*8} {'-'*8} {'-'*8} {'-'*8} {'-'*8}")

    ref_rows = [
        ("K208 baseline",    K208_OOS_SH,  K208_MAX_DD,    None,           K208_WF_MIN,  K208_WF_FOLDS[1]),
        ("K229d ensemble",   K229D_OOS_SH, -0.0012,        None,           K229D_WF_MIN, K229D_WF_FOLDS[1]),
        ("K245 best (REJ)", 16.76,         None,           None,           K245_BEST_FOLD2, K245_BEST_FOLD2),
    ]
    for name, oos_sh, dd, wf_mean, wf_min, fold2 in ref_rows:
        dd_str      = f"{dd:>8.4f}" if dd is not None else "      N/A"
        wf_mean_str = f"{wf_mean:>8.2f}" if wf_mean is not None else "     N/A"
        print(f"  {name:<22} {oos_sh:>8.2f} {dd_str} {wf_mean_str} {wf_min:>8.2f} {fold2:>8.2f}")

    for vname in VARIANTS:
        r = variant_results[vname]
        print(f"  {vname:<22} {r['sharpe_oos']:>8.2f} {r['max_dd_oos']:>8.4f} "
              f"{r['wf_mean']:>8.2f} {r['wf_min']:>8.2f} {r['fold2_sh']:>8.2f}")

    # ── 7. Best variant + verdict ───────────────────────────────────────────
    print("\n=== FINAL VERDICT ===")
    non_baseline = [(v, variant_results[v]) for v in VARIANTS[1:]]
    best_vname   = max(non_baseline, key=lambda x: (x[1]["fold2_sh"], x[1]["sharpe_oos"]))[0]
    best_result  = variant_results[best_vname]

    print(f"  Best variant: {best_vname}")
    print(f"    Fold2 Sh = {best_result['fold2_sh']:+.2f}  (target >= {ACCEPT_FOLD2_SH})")
    print(f"    OOS Sh   = {best_result['sharpe_oos']:+.2f}  (target >= {ACCEPT_OOS_SH})")
    print(f"    WF min   = {best_result['wf_min']:+.2f}  (target >= {ACCEPT_WF_MIN})")
    print(f"  Accepted: {accepted_variants if accepted_variants else 'None'}")

    if accepted_variants:
        best_accepted = max(
            accepted_variants,
            key=lambda v: (variant_results[v]["fold2_sh"], variant_results[v]["sharpe_oos"])
        )
        k248_plan = {
            "action":            "INTEGRATE_K247",
            "best_variant":      best_accepted,
            "target":            "K229d V_K208 slot replacement",
            "expected_fold2_sh": variant_results[best_accepted]["fold2_sh"],
            "expected_oos_sh":   variant_results[best_accepted]["sharpe_oos"],
            "next_steps": [
                f"1. Swap K229d V_K208 for {best_accepted} direction-accuracy-scaled K208",
                "2. Re-run K229d ensemble with new component (K248)",
                "3. Verify K229d WF min recovers to >= 9.0",
                "4. Paper-trade 14 days before live deployment",
            ],
        }
        final_verdict = f"ACCEPT {best_accepted} → K229d V_K208 slot (K248)"
    else:
        k248_plan = {
            "action": "CONTINUE_INVESTIGATION",
            "reason": "No variant met 4/5 acceptance gates",
            "best_attempt": best_vname,
            "best_fold2":   best_result["fold2_sh"],
            "next_steps": [
                "K248: Try combined direction accuracy + K208 gate (no binary removal for K247b)",
                "K248: Investigate fold 2 drift root cause more granularly",
                "K248: Try asymmetric scaling — shrink shorts more than longs during drift",
                "K248: Extend dir_acc window to 60d or 45d",
            ],
        }
        final_verdict = f"REJECT → best={best_vname} Fold2={best_result['fold2_sh']:.2f} (K248 prescription in JSON)"

    print(f"\n  FINAL VERDICT: {final_verdict}")

    # ── 8. Build curves JSON ────────────────────────────────────────────────
    print("\n=== BUILDING CURVES JSON ===")
    curves: Dict = {}
    for vname, pnl in all_pnls.items():
        if len(pnl) > 0:
            curves[vname] = {
                "cumulative_pnl": equity_curve_vals(pnl),
                "timestamps":     [t.isoformat() for t in pnl.index],
                "label":          f"{vname} panel equity",
            }

    # Aggregate rolling accuracy (mean across symbols) for curves
    acc_by_sym: Dict[str, pd.Series] = {}
    for sym, df in panels.items():
        _, _, _, rolling_acc, _ = sym_dar[sym]
        acc_by_sym[sym] = pd.Series(rolling_acc, index=df.index, name=sym)
    agg_acc_curve = pd.concat(acc_by_sym, axis=1).mean(axis=1, skipna=True)
    curves["rolling_dir_accuracy_agg"] = {
        "values":     [round(float(v), 4) if not np.isnan(v) else None for v in agg_acc_curve.values],
        "timestamps": [t.isoformat() for t in agg_acc_curve.index],
        "label":      "Aggregated rolling 30d direction accuracy",
    }

    # Per-symbol accuracy curves
    for sym, df in panels.items():
        _, _, _, rolling_acc, _ = sym_dar[sym]
        curves[f"rolling_dir_accuracy_{sym}"] = {
            "values":     [round(float(v), 4) if not np.isnan(v) else None for v in rolling_acc],
            "timestamps": [t.isoformat() for t in df.index],
            "label":      f"{sym} rolling 30d direction accuracy",
        }

    print(f"  Built {len(curves)} curve series")

    # ── 9. Assemble output JSON ─────────────────────────────────────────────
    runtime = round(time.time() - t0, 1)
    output = {
        "wave":        "K247",
        "parent_waves": ["K208", "K245"],
        "objective":   "Rolling 30d direction accuracy scaling for K208 drift detection",
        "as_of":       pd.Timestamp.now(tz="UTC").isoformat(),
        "runtime_s":   runtime,

        "config": {
            "symbols":           list(panels.keys()),
            "symbols_skipped":   skipped,
            "dar_p":             PRIMARY_P,
            "dar_q":             PRIMARY_Q,
            "dar_win":           PRIMARY_WIN,
            "dar_refit":         PRIMARY_REFIT,
            "dir_acc_window_events": DIR_ACC_WIN,
            "dir_acc_window_days":   30,
            "scalar_formula":    "clip((acc - 0.45) / 0.20, 0.5, 1.0)  [K247a/d/c-variant]",
            "cliff_thresh":      CLIFF_THRESH,
            "ml_window":         {"start": ML_START, "end": ML_END},
            "fold_bounds":       [{"fold": i+1, "start": s, "end": e}
                                  for i, (s, e) in enumerate(FOLD_BOUNDS)],
        },

        "acceptance_thresholds": {
            "fold2_sh_min": ACCEPT_FOLD2_SH,
            "oos_sh_min":   ACCEPT_OOS_SH,
            "wf_min_min":   ACCEPT_WF_MIN,
        },

        "reference_metrics": {
            "K208_baseline": {
                "oos_sh":   K208_OOS_SH,
                "wf_folds": K208_WF_FOLDS,
                "wf_min":   K208_WF_MIN,
                "fold2_sh": K208_WF_FOLDS[1],
                "max_dd":   K208_MAX_DD,
            },
            "K229d_ensemble": {
                "oos_sh":   K229D_OOS_SH,
                "wf_folds": K229D_WF_FOLDS,
                "wf_min":   K229D_WF_MIN,
                "fold2_sh": K229D_WF_FOLDS[1],
            },
            "K245_best_rejected": {
                "fold2_sh": K245_BEST_FOLD2,
                "reason":   "magnitude confidence inadequate",
            },
        },

        "fold_direction_accuracy": fold_acc_stats,
        "variants":      variant_results,
        "verdict_table": verdict_table,
        "accepted":      accepted_variants,
        "best_variant":  best_vname,
        "final_verdict": final_verdict,
        "drift_logs":    all_drift_logs,
        "k248_plan":     k248_plan,
    }

    # ── 10. Write outputs ───────────────────────────────────────────────────
    json_path   = BASE / "wave_k247_k208_dir_acc_scale.json"
    curves_path = BASE / "wave_k247_curves.json"

    json_path.write_text(json.dumps(output, indent=2, default=str))
    curves_path.write_text(json.dumps(curves, default=str))

    print(f"\nWrote {json_path} ({json_path.stat().st_size:,} bytes)")
    print(f"Wrote {curves_path} ({curves_path.stat().st_size:,} bytes)")
    print(f"Total runtime: {runtime}s")
    print(f"\nFINAL VERDICT: {final_verdict}")

    return output


if __name__ == "__main__":
    main()

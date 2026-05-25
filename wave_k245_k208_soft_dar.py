"""Wave K245 - K208 Soft DAR Confidence Scaling.

Hypothesis:
  K208 fold 2 weakness (Sh=5.74) is caused by diffuse DAR(2,1) sign misfires
  across 112 days. Binary gating (K242) proved too blunt. Solution: replace
  hard gate with continuous soft position scaling based on DAR(2,1) prediction
  confidence. Low-confidence predictions → reduced position; high-confidence → full.

Variants:
  K245a: Linear scaling (conf as multiplier, clipped to [0.5, 1.0])
  K245b: Threshold scaling (conf < 0.5 → 0.5, conf >= 0.5 → 1.0)
  K245c: Tanh smoothing (gradual, center=0.5, scale=2.0)
  K245d: Regime-conditional (soft scaling only when fr_mean_ann_6maj > 5%, else full size)

Confidence metric:
  confidence_i = |pred_fr_change_i| / rolling_30d_std(pred_fr_change)
  where pred_fr_change_i = pred_fr[i] - fr[i-1]
  confidence is clipped to [0, 1] and mapped to position scalar [0.5, 1.0].

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
TRADING_DAYS    = 365

# DAR(2,1) primary config (matches K208/K190)
PRIMARY_P     = 2
PRIMARY_Q     = 1
PRIMARY_WIN   = 300
PRIMARY_REFIT = 50

# K208 panel symbols
REVERSE_10 = ["SOL", "XRP", "SUI", "OP", "APT", "AXS", "JTO", "IMX", "SAND", "ADA"]

# 6 majors for FR regime detection (K242d)
MAJOR_6 = ["BTC", "ETH", "SOL", "XRP", "BNB", "DOT"]

# K208 reference (from K240)
K208_OOS_SH   = 10.57
K208_WF_FOLDS = [17.35, 5.74, 17.41, 13.11]
K208_WF_MIN   = 5.74
K208_MAX_DD   = -0.0002

# K229d reference
K229D_OOS_SH   = 10.17
K229D_WF_FOLDS = [12.91, 7.48, 13.01, 12.22]
K229D_WF_MIN   = 7.48

# Acceptance gates
ACCEPT_FOLD2_SH = 7.0
ACCEPT_OOS_SH   = 10.57  # must beat K208 baseline
ACCEPT_WF_MIN   = 7.0

# Soft scaling parameters
CONF_SCALE_MIN = 0.5  # minimum position scalar (never go below 50%)
CONF_SCALE_MAX = 1.0  # maximum position scalar

# FR regime threshold (K245d)
FR_REGIME_THRESH = 0.05  # 5% annualized = apply scaling above this level

# ML window / fold config (matching K242)
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


def load_fr_panel_for_regime() -> Optional[pd.Series]:
    """Load 6-major FR, compute daily mean ann FR for regime detection."""
    syms_ok = []
    for sym in MAJOR_6:
        s = load_bybit_fr(sym)
        if s is not None:
            syms_ok.append(s)
    if not syms_ok:
        return None
    combined = pd.concat(syms_ok, axis=1).mean(axis=1)
    # Annualize: each event is 8h, so annual = FR * 3 * 365
    combined_ann = combined * EVENTS_PER_YEAR
    # Resample to 8h-aligned, forward fill
    return combined_ann.sort_index()


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


def dar_walk_forward_with_confidence(
    fr: np.ndarray,
    spread_z: np.ndarray,
    p: int = PRIMARY_P,
    q: int = PRIMARY_Q,
    win: int = PRIMARY_WIN,
    refit: int = PRIMARY_REFIT,
    conf_window: int = 90,  # ~30 days in 8h events
) -> Tuple[np.ndarray, np.ndarray, np.ndarray, Dict]:
    """Walk-forward DAR(p,q) with per-step confidence scores.

    Confidence = |pred_fr_change| / rolling_std(pred_fr_change, conf_window)
    pred_fr_change[i] = pred_fr[i] - fr[i-1]

    Returns:
        pred_fr   : predicted FR values
        is_valid  : boolean mask
        confidence: raw confidence score (clipped 0..1)
        diag      : diagnostics dict
    """
    n = len(fr)
    pred_fr    = np.full(n, np.nan)
    is_valid   = np.zeros(n, dtype=bool)
    pred_delta = np.full(n, np.nan)  # pred_fr[i] - fr[i-1]
    min_lag    = max(p, q)
    coeffs     = None

    for i in range(min_lag + win, n):
        # Refit on schedule
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
                pred_fr[i]    = float(np.dot(row, coeffs))
                pred_delta[i] = pred_fr[i] - fr[i - 1]
                is_valid[i]   = True

    # Compute confidence: |pred_delta| / rolling_std(pred_delta)
    pred_delta_s = pd.Series(pred_delta)
    rolling_std  = pred_delta_s.abs().rolling(conf_window, min_periods=max(10, conf_window // 3)).mean()
    raw_conf     = pred_delta_s.abs() / (rolling_std + 1e-12)
    # Clip and normalize to [0, 1]
    conf_arr = np.clip(raw_conf.values, 0, None)
    p95      = np.nanpercentile(conf_arr[is_valid], 95) if is_valid.sum() > 10 else 1.0
    if p95 > 0:
        conf_arr = np.clip(conf_arr / p95, 0.0, 1.0)

    # Fill NaN confidence with 0 for invalid steps
    conf_arr = np.where(is_valid, conf_arr, np.nan)

    # Diagnostics
    valid_idx = np.where(is_valid)[0]
    if len(valid_idx) < 30:
        return pred_fr, is_valid, conf_arr, {"oos_r2": np.nan, "direction_acc": np.nan, "n_oos": 0}

    y_true = fr[valid_idx]
    y_pred  = pred_fr[valid_idx]
    ss_res  = np.sum((y_true - y_pred) ** 2)
    ss_tot  = np.sum((y_true - y_true.mean()) ** 2)
    oos_r2  = float(1 - ss_res / (ss_tot + 1e-30))

    actual_delta = np.diff(y_true)
    pred_sign    = np.sign(y_pred[1:] - y_true[:-1])
    actual_sign  = np.sign(actual_delta)
    nz           = actual_sign != 0
    dir_acc = float((pred_sign[nz] == actual_sign[nz]).mean()) if nz.sum() > 0 else 0.5

    conf_valid = conf_arr[valid_idx]
    conf_valid = conf_valid[~np.isnan(conf_valid)]

    return pred_fr, is_valid, conf_arr, {
        "oos_r2":          round(oos_r2, 5),
        "direction_acc":   round(dir_acc, 4),
        "n_oos":           int(len(valid_idx)),
        "conf_mean":       round(float(np.nanmean(conf_valid)), 4) if len(conf_valid) > 0 else 0.0,
        "conf_p25":        round(float(np.nanpercentile(conf_valid, 25)), 4) if len(conf_valid) > 0 else 0.0,
        "conf_p75":        round(float(np.nanpercentile(conf_valid, 75)), 4) if len(conf_valid) > 0 else 0.0,
        "conf_frac_above_half": round(float((conf_valid >= 0.5).mean()), 4) if len(conf_valid) > 0 else 0.0,
    }


# ─────────────────────────────────────────────────────────────────────────────
# Scaling functions
# ─────────────────────────────────────────────────────────────────────────────

def scale_linear(conf: float) -> float:
    """K245a: linear mapping conf ∈ [0,1] → scalar ∈ [0.5, 1.0]."""
    c = float(np.clip(conf, 0.0, 1.0))
    return CONF_SCALE_MIN + c * (CONF_SCALE_MAX - CONF_SCALE_MIN)


def scale_threshold(conf: float) -> float:
    """K245b: binary threshold at 0.5."""
    return CONF_SCALE_MAX if conf >= 0.5 else CONF_SCALE_MIN


def scale_tanh(conf: float, center: float = 0.5, steepness: float = 4.0) -> float:
    """K245c: tanh smoothing, gradual transition around center."""
    c = float(np.clip(conf, 0.0, 1.0))
    t = math.tanh(steepness * (c - center))
    # Map tanh output (-1, 1) → (CONF_SCALE_MIN, CONF_SCALE_MAX)
    scaled = 0.5 + 0.5 * t
    return CONF_SCALE_MIN + scaled * (CONF_SCALE_MAX - CONF_SCALE_MIN)


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
# Core strategy runner
# ─────────────────────────────────────────────────────────────────────────────

def run_k208_variant(
    panels: Dict[str, pd.DataFrame],
    variant: str,
    fr_regime_series: Optional[pd.Series] = None,
) -> Tuple[pd.Series, Dict, Dict[str, np.ndarray]]:
    """Run K208 + soft DAR scaling variant.

    variant: 'baseline' | 'K245a' | 'K245b' | 'K245c' | 'K245d'

    Returns:
        panel_pnl    : combined equal-weight panel PnL series
        stats        : per-symbol stats dict
        conf_arrays  : {sym: confidence_array}
    """
    per_sym:     Dict[str, pd.Series] = {}
    stats:       Dict[str, Dict]      = {}
    conf_arrays: Dict[str, np.ndarray] = {}

    for sym, df in panels.items():
        fr_arr   = df["bybit_fr"].values.copy()
        spread_z = zscore_rolling(df["spread"], 30).fillna(0.0).values
        n        = len(df)

        # K208 original DAR gate: pred_spread > 0 (pred_bybit_fr > current hl_fr_8h)
        pred_fr, is_valid, conf_arr, diag = dar_walk_forward_with_confidence(
            fr_arr, spread_z
        )
        conf_arrays[sym] = conf_arr

        hl_arr       = df["hl_fr_8h"].values.copy()
        base_pnl     = df["rev_carry_pnl"].copy()

        # Build per-event position scalars
        scalars = np.zeros(n, dtype=float)
        for i in range(n):
            if not is_valid[i]:
                continue
            pred_spread = pred_fr[i] - hl_arr[i]
            if pred_spread <= 0:
                # K208 gate: no position when predicted spread <= 0
                scalars[i] = 0.0
                continue

            conf = float(conf_arr[i]) if not np.isnan(conf_arr[i]) else 0.5

            if variant == "baseline":
                # K208 pure binary gate: 1.0 when gate passes
                scalars[i] = 1.0
            elif variant == "K245a":
                scalars[i] = scale_linear(conf)
            elif variant == "K245b":
                scalars[i] = scale_threshold(conf)
            elif variant == "K245c":
                scalars[i] = scale_tanh(conf)
            elif variant == "K245d":
                # Regime-conditional: only apply soft scaling if FR regime high
                if fr_regime_series is not None:
                    # Find regime FR at this timestamp
                    ts = df.index[i]
                    ts_fr = fr_regime_series.reindex([ts], method="nearest", tolerance=pd.Timedelta("24h"))
                    regime_fr = float(ts_fr.iloc[0]) if len(ts_fr) > 0 and not ts_fr.isna().all() else 0.0
                else:
                    regime_fr = 0.0

                if regime_fr > FR_REGIME_THRESH:
                    # High FR regime: apply soft scaling
                    scalars[i] = scale_linear(conf)
                else:
                    # Normal regime: full size
                    scalars[i] = 1.0
            else:
                scalars[i] = 1.0

        # Lag scalars by 1 event (no look-ahead)
        scalar_series = pd.Series(scalars, index=df.index).shift(1).fillna(0.0)
        filtered_pnl  = base_pnl * scalar_series

        per_sym[sym] = filtered_pnl

        n_active    = int((scalar_series > 0).sum())
        n_total     = n
        avg_scalar  = float(scalar_series[scalar_series > 0].mean()) if (scalar_series > 0).any() else 0.0
        stats[sym]  = {
            "variant":       variant,
            "sharpe":        round(sharpe_e(filtered_pnl), 4),
            "n_total":       n_total,
            "n_active":      n_active,
            "pct_active":    round(100 * n_active / max(n_total, 1), 1),
            "avg_scalar":    round(avg_scalar, 4),
            "dar_dir_acc":   round(diag.get("direction_acc", 0.0), 4),
            "dar_oos_r2":    round(diag.get("oos_r2", 0.0), 5),
            "conf_mean":     round(diag.get("conf_mean", 0.0), 4),
            "conf_p25":      round(diag.get("conf_p25", 0.0), 4),
            "conf_p75":      round(diag.get("conf_p75", 0.0), 4),
            "conf_above_half": round(diag.get("conf_frac_above_half", 0.0), 4),
        }

    if not per_sym:
        return pd.Series(dtype=float), {}, {}

    aligned   = pd.concat(per_sym, axis=1).fillna(0.0)
    panel_pnl = aligned.mean(axis=1)
    return panel_pnl, stats, conf_arrays


# ─────────────────────────────────────────────────────────────────────────────
# Main
# ─────────────────────────────────────────────────────────────────────────────

def main() -> Dict:
    t0 = time.time()

    print("=" * 70)
    print("Wave K245: K208 Soft DAR Confidence Scaling")
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
            print(f"  {sym}: n={len(p)}  mean_spread={p['spread'].mean()*10000:.2f}bps  "
                  f"spread_std={p['spread'].std()*10000:.2f}bps")

    if not panels:
        raise RuntimeError("No panels built")

    print(f"\nLoaded {len(panels)} symbols, skipped {len(skipped)}")

    # ── 2. Load FR regime series (for K245d) ────────────────────────────────
    print("\n=== LOADING REGIME DATA (for K245d) ===")
    fr_regime = load_fr_panel_for_regime()
    if fr_regime is not None:
        print(f"  FR regime series: n={len(fr_regime)}, "
              f"mean_ann={fr_regime.mean():.4f}, "
              f"pct_above_5pct={100*(fr_regime > FR_REGIME_THRESH).mean():.1f}%")
    else:
        print("  FR regime series: UNAVAILABLE, K245d will use full size everywhere")

    # ── 3. Run all 5 variants ────────────────────────────────────────────────
    VARIANTS = ["baseline", "K245a", "K245b", "K245c", "K245d"]
    variant_results: Dict[str, Dict] = {}
    all_conf_arrays: Dict[str, Dict[str, np.ndarray]] = {}
    all_pnls: Dict[str, pd.Series] = {}

    for vname in VARIANTS:
        print(f"\n=== VARIANT: {vname} ===")
        pnl, sym_stats, conf_arrays = run_k208_variant(panels, vname, fr_regime)
        all_pnls[vname]       = pnl
        all_conf_arrays[vname] = conf_arrays

        # Full-period OOS metrics (last 30% of total history)
        n_total = len(pnl.dropna())
        split   = int(n_total * 0.70)
        oos_pnl = pnl.dropna().iloc[split:]
        sh_oos  = sharpe_e(oos_pnl)
        dd_oos  = max_dd_e(oos_pnl)
        sh_full = sharpe_e(pnl)

        # Walk-forward fold Sharpe (ML window only)
        wf_mean, wf_min, wf_folds = wf_4fold_custom(pnl, FOLD_BOUNDS)

        # Confidence distribution (aggregate across symbols)
        all_conf_vals: List[float] = []
        for sym, ca in conf_arrays.items():
            valid = ca[~np.isnan(ca)]
            if len(valid) > 0:
                all_conf_vals.extend(valid.tolist())
        conf_p25 = float(np.percentile(all_conf_vals, 25)) if all_conf_vals else 0.0
        conf_p50 = float(np.percentile(all_conf_vals, 50)) if all_conf_vals else 0.0
        conf_p75 = float(np.percentile(all_conf_vals, 75)) if all_conf_vals else 0.0
        conf_above_half = float(np.mean([c >= 0.5 for c in all_conf_vals])) if all_conf_vals else 0.0

        # Average position scalar
        avg_scalars = [s.get("avg_scalar", 0.0) for s in sym_stats.values() if s.get("avg_scalar", 0.0) > 0]
        avg_scalar_panel = float(np.mean(avg_scalars)) if avg_scalars else 0.0
        pct_actives = [s.get("pct_active", 0.0) for s in sym_stats.values()]
        avg_pct_active = float(np.mean(pct_actives)) if pct_actives else 0.0

        result = {
            "variant":        vname,
            "sharpe_full":    round(sh_full, 4),
            "sharpe_oos":     round(sh_oos, 4),
            "max_dd_oos":     round(dd_oos, 6),
            "wf_mean":        round(wf_mean, 4),
            "wf_min":         round(wf_min, 4),
            "wf_folds":       wf_folds,
            "fold2_sh":       wf_folds[1] if len(wf_folds) > 1 else 0.0,
            "n_events_total": n_total,
            "avg_scalar":     round(avg_scalar_panel, 4),
            "avg_pct_active": round(avg_pct_active, 1),
            "conf_p25":       round(conf_p25, 4),
            "conf_p50":       round(conf_p50, 4),
            "conf_p75":       round(conf_p75, 4),
            "conf_above_half": round(conf_above_half, 4),
            "per_symbol":     sym_stats,
        }
        variant_results[vname] = result

        print(f"  OOS Sh={sh_oos:+.3f}  MaxDD_OOS={dd_oos:+.6f}  "
              f"WF_mean={wf_mean:+.3f}  WF_min={wf_min:+.3f}")
        print(f"  Fold Sharpes: {[f'{x:+.2f}' for x in wf_folds]}")
        print(f"  Fold 2 Sh={wf_folds[1] if len(wf_folds)>1 else 'N/A':}")
        print(f"  Avg scalar={avg_scalar_panel:.4f}  Avg pct_active={avg_pct_active:.1f}%")
        print(f"  Conf p25={conf_p25:.3f}  p50={conf_p50:.3f}  p75={conf_p75:.3f}  "
              f"above_half={conf_above_half*100:.1f}%")

    # ── 4. Acceptance evaluation ─────────────────────────────────────────────
    print("\n=== ACCEPTANCE EVALUATION ===")
    accepted_variants = []
    verdict_table: Dict[str, Dict] = {}

    for vname in VARIANTS[1:]:  # skip baseline
        r = variant_results[vname]
        fold2_ok = r["fold2_sh"] >= ACCEPT_FOLD2_SH
        oos_ok   = r["sharpe_oos"] >= ACCEPT_OOS_SH
        wfmin_ok = r["wf_min"] >= ACCEPT_WF_MIN
        # Scaling reasonableness: avg_scalar between 0.52 and 0.99
        scale_ok = 0.52 <= r["avg_scalar"] <= 0.99
        # Confidence distribution non-degenerate: conf_above_half in [0.3, 0.9]
        conf_ok  = 0.30 <= r["conf_above_half"] <= 0.90

        gates_pass = sum([fold2_ok, oos_ok, wfmin_ok, scale_ok, conf_ok])
        if gates_pass >= 4:
            verdict = "ACCEPT"
            accepted_variants.append(vname)
        elif gates_pass >= 3:
            verdict = "MARGINAL"
        else:
            verdict = "FAIL"

        verdict_table[vname] = {
            "fold2_sh":         r["fold2_sh"],
            "fold2_ok":         fold2_ok,
            "oos_sh":           r["sharpe_oos"],
            "oos_ok":           oos_ok,
            "wf_min":           r["wf_min"],
            "wfmin_ok":         wfmin_ok,
            "avg_scalar":       r["avg_scalar"],
            "scale_ok":         scale_ok,
            "conf_above_half":  r["conf_above_half"],
            "conf_ok":          conf_ok,
            "gates_pass":       gates_pass,
            "verdict":          verdict,
        }

        fold2_flag = "PASS" if fold2_ok else "FAIL"
        oos_flag   = "PASS" if oos_ok   else "FAIL"
        wfmin_flag = "PASS" if wfmin_ok else "FAIL"
        scale_flag = "PASS" if scale_ok else "FAIL"
        conf_flag  = "PASS" if conf_ok  else "FAIL"
        print(f"\n  {vname}:")
        print(f"    Fold2={r['fold2_sh']:+.2f} [{fold2_flag}]  "
              f"OOS_Sh={r['sharpe_oos']:+.2f} [{oos_flag}]  "
              f"WF_min={r['wf_min']:+.2f} [{wfmin_flag}]")
        print(f"    Avg_scalar={r['avg_scalar']:.4f} [{scale_flag}]  "
              f"Conf_above_half={r['conf_above_half']:.3f} [{conf_flag}]")
        print(f"    Gates: {gates_pass}/5  Verdict: {verdict}")

    # ── 5. Comparison table ──────────────────────────────────────────────────
    print("\n=== COMPARISON TABLE ===")
    header = f"{'Version':<20} {'OOS Sh':>8} {'MaxDD_OOS':>10} {'WF mean':>8} {'WF min':>8} {'Fold2':>8}"
    print(f"  {header}")
    print(f"  {'-'*20} {'-'*8} {'-'*10} {'-'*8} {'-'*8} {'-'*8}")

    ref_rows = [
        ("K208 baseline", K208_OOS_SH, K208_MAX_DD, None, K208_WF_MIN, K208_WF_FOLDS[1]),
        ("K229d ensemble", K229D_OOS_SH, -0.0012, None, K229D_WF_MIN, K229D_WF_FOLDS[1]),
    ]
    for name, oos_sh, dd, wf_mean, wf_min, fold2 in ref_rows:
        wf_mean_str = f"{wf_mean:>8.2f}" if wf_mean is not None else "     N/A"
        print(f"  {name:<20} {oos_sh:>8.2f} {dd:>10.4f} {wf_mean_str} {wf_min:>8.2f} {fold2:>8.2f}")

    for vname in VARIANTS:
        r = variant_results[vname]
        print(f"  {vname:<20} {r['sharpe_oos']:>8.2f} {r['max_dd_oos']:>10.4f} "
              f"{r['wf_mean']:>8.2f} {r['wf_min']:>8.2f} {r['fold2_sh']:>8.2f}")

    # ── 6. Best variant selection ────────────────────────────────────────────
    print("\n=== FINAL VERDICT ===")
    # Rank by fold2_sh first (primary K245 objective), then OOS_Sh
    non_baseline = [(v, variant_results[v]) for v in VARIANTS[1:]]
    best_vname   = max(non_baseline, key=lambda x: (x[1]["fold2_sh"], x[1]["sharpe_oos"]))[0]
    best_result  = variant_results[best_vname]

    print(f"  Best variant: {best_vname}")
    print(f"    Fold2 Sh = {best_result['fold2_sh']:+.2f}  "
          f"(target >= {ACCEPT_FOLD2_SH}; K208 base = {K208_WF_FOLDS[1]:+.2f})")
    print(f"    OOS Sh   = {best_result['sharpe_oos']:+.2f}  "
          f"(target >= {ACCEPT_OOS_SH}; K208 base = {K208_OOS_SH:+.2f})")
    print(f"    WF min   = {best_result['wf_min']:+.2f}  (target >= {ACCEPT_WF_MIN})")
    print(f"  Accepted variants: {accepted_variants if accepted_variants else 'None'}")

    if accepted_variants:
        best_accepted = max(
            accepted_variants,
            key=lambda v: (variant_results[v]["fold2_sh"], variant_results[v]["sharpe_oos"])
        )
        k246_plan = {
            "action":              "INTEGRATE_K245",
            "best_variant":        best_accepted,
            "integration_target":  "K229d V_K208 slot replacement",
            "expected_fold2_sh":   variant_results[best_accepted]["fold2_sh"],
            "expected_oos_sh":     variant_results[best_accepted]["sharpe_oos"],
            "next_steps": [
                f"1. Swap K229d V_K208 for {best_accepted} soft-scaled K208",
                "2. Re-run K229d ensemble with replaced component",
                "3. Verify K229d WF min recovers to >= 9.0",
                "4. Paper-trade 14 days before live deployment",
            ],
        }
        final_verdict = f"ACCEPT {best_accepted} → K229d V_K208 slot"
    else:
        k246_plan = {
            "action": "CONTINUE_INVESTIGATION",
            "reason": "No variant met all 5 acceptance gates",
            "next_steps": [
                "K246: Try asymmetric confidence (separate long/short scalars)",
                "K246: Try confidence windows of 60d and 45d",
                "K246: Add multi-symbol confidence aggregation before scaling",
            ],
        }
        best_accepted = best_vname
        final_verdict = f"REJECT → best={best_vname} Fold2={best_result['fold2_sh']:.2f}"

    print(f"\n  FINAL VERDICT: {final_verdict}")

    # ── 7. Build curves JSON ─────────────────────────────────────────────────
    print("\n=== BUILDING CURVES JSON ===")
    curves: Dict = {}
    for vname, pnl in all_pnls.items():
        if len(pnl) > 0:
            # Panel equity curve
            curves[vname] = {
                "cumulative_pnl": equity_curve_vals(pnl),
                "timestamps":     [t.isoformat() for t in pnl.index],
                "label":          f"{vname} panel equity",
            }
            # Aggregate confidence (mean across symbols per timestep)
            conf_by_ts: Dict[str, List[float]] = {}
            for sym, ca in all_conf_arrays.get(vname, {}).items():
                panels_sym_idx = panels[sym].index
                for i, ts in enumerate(panels_sym_idx):
                    ts_str = ts.isoformat()
                    if ts_str not in conf_by_ts:
                        conf_by_ts[ts_str] = []
                    if i < len(ca) and not np.isnan(ca[i]):
                        conf_by_ts[ts_str].append(float(ca[i]))

            sorted_ts = sorted(conf_by_ts.keys())
            mean_conf = [
                round(float(np.mean(conf_by_ts[ts])), 4) if conf_by_ts[ts] else float("nan")
                for ts in sorted_ts
            ]
            curves[f"{vname}_confidence"] = {
                "mean_confidence": mean_conf,
                "timestamps":      sorted_ts,
                "label":           f"{vname} mean DAR confidence",
            }

    print(f"  Built {len(curves)} curve series")

    # ── 8. Assemble output JSON ──────────────────────────────────────────────
    runtime = round(time.time() - t0, 1)
    output  = {
        "wave":       "K245",
        "parent_waves": ["K208", "K190", "K242"],
        "objective":  "Soft DAR(2,1) confidence scaling for K208 fold 2 recovery",
        "as_of":      pd.Timestamp.now(tz="UTC").isoformat(),
        "runtime_s":  runtime,

        "config": {
            "symbols":          list(panels.keys()),
            "symbols_skipped":  skipped,
            "dar_p":            PRIMARY_P,
            "dar_q":            PRIMARY_Q,
            "dar_win":          PRIMARY_WIN,
            "dar_refit":        PRIMARY_REFIT,
            "conf_window_events": 90,
            "conf_scale_min":   CONF_SCALE_MIN,
            "conf_scale_max":   CONF_SCALE_MAX,
            "fr_regime_thresh": FR_REGIME_THRESH,
            "ml_window_start":  ML_START,
            "ml_window_end":    ML_END,
            "fold_bounds":      [{"fold": i+1, "start": s, "end": e}
                                 for i, (s, e) in enumerate(FOLD_BOUNDS)],
        },

        "acceptance_thresholds": {
            "fold2_sh_min":   ACCEPT_FOLD2_SH,
            "oos_sh_min":     ACCEPT_OOS_SH,
            "wf_min_min":     ACCEPT_WF_MIN,
            "scale_range":    [0.52, 0.99],
            "conf_above_half_range": [0.30, 0.90],
        },

        "reference_metrics": {
            "K208_standalone": {
                "oos_sh":    K208_OOS_SH,
                "wf_folds":  K208_WF_FOLDS,
                "wf_min":    K208_WF_MIN,
                "fold2_sh":  K208_WF_FOLDS[1],
                "max_dd":    K208_MAX_DD,
                "source":    "K240",
            },
            "K229d_ensemble": {
                "oos_sh":   K229D_OOS_SH,
                "wf_folds": K229D_WF_FOLDS,
                "wf_min":   K229D_WF_MIN,
                "fold2_sh": K229D_WF_FOLDS[1],
                "source":   "K240",
            },
        },

        "variants":      variant_results,
        "verdict_table": verdict_table,
        "accepted":      accepted_variants,
        "best_variant":  best_vname,
        "final_verdict": final_verdict,
        "k246_plan":     k246_plan,
    }

    # ── 9. Write outputs ─────────────────────────────────────────────────────
    json_path   = BASE / "wave_k245_k208_soft_dar.json"
    curves_path = BASE / "wave_k245_curves.json"

    json_path.write_text(json.dumps(output, indent=2, default=str))
    curves_path.write_text(json.dumps(curves, default=str))

    print(f"\nWrote {json_path} ({json_path.stat().st_size:,} bytes)")
    print(f"Wrote {curves_path} ({curves_path.stat().st_size:,} bytes)")
    print(f"Total runtime: {runtime}s")
    print(f"\nFINAL VERDICT: {final_verdict}")

    return output


if __name__ == "__main__":
    main()

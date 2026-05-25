"""Wave K259 - K256_Ridge Rebuilt Without AXS (AXS-Free 9-Symbol Universe).

Hypothesis: K256_Ridge has genuine orthogonal alpha (daily rho=0.5694 vs K208)
but AXS data contaminates WF fold 2 causing WF min=0.32.
K259: Rebuild K256_Ridge with 9 symbols (AXS excluded), verify all WF folds > 0.

Acceptance gates (Gate 0 for K260 integration):
  - All WF folds > 0
  - Standalone OOS Sh >= 1.5
  - Daily rho vs K208 <= 0.7 (genuine orthogonal)
  - If any gate fails -> abort K260

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

warnings.filterwarnings("ignore")

t_start = time.time()
BASE     = Path("/Users/nekonaomichi/crypto-lab")
CACHE    = BASE / "cache"
HL_CACHE = CACHE / "k163_hl"

# ─────────────────────────────────────────────────────────────────────────────
# Constants
# ─────────────────────────────────────────────────────────────────────────────
EVENTS_PER_YEAR = 365 * 3   # 1095 (8h events)
EVENTS_PER_DAY  = 3

# DAR(2,1) primary config (matches K208/K256)
PRIMARY_P     = 2
PRIMARY_Q     = 1
PRIMARY_WIN   = 300
PRIMARY_REFIT = 50

# K259: 9-symbol universe - AXS EXCLUDED
# Original K256: [SOL, XRP, SUI, OP, APT, AXS, JTO, IMX, SAND, ADA]
REVERSE_9 = ["SOL", "XRP", "SUI", "OP", "APT", "JTO", "IMX", "SAND", "ADA"]

COST_PER_SIDE = 0.0  # Match K208/K256 baseline methodology

# 8h spread gate: rolling 90-event window (30 days), halt at p25
SPREAD_GATE_WIN = 90
SPREAD_GATE_PCT = 25

# Ridge allocator config (identical to K256)
RIDGE_FEAT_WIN   = 30
RIDGE_TRAIN_WIN  = 90
RIDGE_REFIT      = 30
RIDGE_ALPHA      = 1.0
MAX_WEIGHT       = 0.30

# Walk-forward fold boundaries (same as K208/K246a/K256)
ML_START = "2025-01-22"
ML_END   = "2026-04-14"
FOLD_BOUNDS: List[Tuple[str, str]] = [
    ("2025-01-22", "2025-05-13"),
    ("2025-05-14", "2025-09-02"),
    ("2025-09-03", "2025-12-23"),
    ("2025-12-24", "2026-04-14"),
]

# Reference metrics
K208_OOS_SH   = 10.57
K208_WF_FOLDS = [17.35, 5.74, 17.41, 13.11]
K208_WF_MIN   = 5.74
K246A_OOS_SH  = 12.69
K246A_WF_MIN  = 8.93

# K256 reference (for comparison)
K256_EQWT_OOS_SH   = 11.7478
K256_EQWT_WF_MIN   = 7.0596
K256_RIDGE_OOS_SH  = 11.9863
K256_RIDGE_WF_MIN  = 0.3172  # AXS contamination
K256_RIDGE_RHO_K208 = 0.5694

# Gate 0 acceptance for K259 standalone
GATE_WF_ALL_POSITIVE = True    # All 4 WF folds > 0
GATE_OOS_SH_MIN      = 1.5    # Standalone OOS Sh
GATE_RHO_K208_MAX    = 0.70   # Daily rho vs K208


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
    """Build 8h-event-level (bybit_fr, hl_fr_8h, spread) DataFrame."""
    hl = load_hl_fr(sym)
    by = load_bybit_fr(sym)
    if hl is None or by is None:
        return None
    hl_8h = hl.resample("8h", label="right", closed="right").sum(min_count=1)
    df = pd.DataFrame({"bybit_fr": by}, index=by.index)
    df["hl_fr_8h"] = hl_8h.reindex(by.index)
    df = df.dropna()
    if len(df) < 100:
        return None
    df["spread"]     = df["bybit_fr"] - df["hl_fr_8h"]
    df["abs_spread"] = df["spread"].abs()
    df["rev_carry_pnl"] = df["spread"].shift(-1)
    df = df.dropna(subset=["rev_carry_pnl"])
    if len(df) < 100:
        return None
    return df


# ─────────────────────────────────────────────────────────────────────────────
# DAR(2,1) walk-forward (identical to K208/K256)
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


def zscore_rolling(arr: np.ndarray, win: int = 30) -> np.ndarray:
    out = np.zeros_like(arr)
    for i in range(len(arr)):
        if i < win - 1:
            out[i] = 0.0
        else:
            chunk = arr[i - win + 1 : i + 1]
            mu = np.mean(chunk)
            sd = np.std(chunk, ddof=1)
            out[i] = (arr[i] - mu) / (sd + 1e-12)
    return out


def dar_walk_forward_arr(
    fr: np.ndarray,
    spread_z: np.ndarray,
    p: int = PRIMARY_P,
    q: int = PRIMARY_Q,
    win: int = PRIMARY_WIN,
    refit: int = PRIMARY_REFIT,
) -> Tuple[np.ndarray, np.ndarray]:
    """Walk-forward DAR(p,q). Returns (pred_fr, is_valid) arrays."""
    n        = len(fr)
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

    return pred_fr, is_valid


# ─────────────────────────────────────────────────────────────────────────────
# Per-symbol event-level PnL with spread gate
# ─────────────────────────────────────────────────────────────────────────────

def compute_sym_pnl_8h(df: pd.DataFrame) -> pd.DataFrame:
    """Compute event-level PnL with DAR gate and 8h spread gate."""
    n          = len(df)
    fr_arr     = df["bybit_fr"].values.copy()
    abs_sp_arr = df["abs_spread"].values.copy()
    hl_arr     = df["hl_fr_8h"].values.copy()
    pnl_arr    = df["rev_carry_pnl"].values.copy()

    spread_z = zscore_rolling(df["spread"].values.copy(), 30)

    pred_fr, is_valid = dar_walk_forward_arr(fr_arr, spread_z)

    # Spread gate: rolling 90-event p25 threshold (causal)
    spread_gate = np.zeros(n, dtype=bool)
    for i in range(n):
        if i < SPREAD_GATE_WIN:
            window = abs_sp_arr[:i] if i > 0 else abs_sp_arr[:1]
        else:
            window = abs_sp_arr[i - SPREAD_GATE_WIN : i]
        if len(window) == 0:
            threshold = 0.0
        else:
            threshold = float(np.percentile(window, SPREAD_GATE_PCT))
        spread_gate[i] = abs_sp_arr[i] >= threshold

    # DAR position: long if predicted spread > 0
    position = np.zeros(n, dtype=float)
    for i in range(n):
        if is_valid[i]:
            pred_spread = pred_fr[i] - hl_arr[i]
            if pred_spread > 0:
                position[i] = 1.0

    position_lagged = np.roll(position, 1)
    position_lagged[0] = 0.0

    gate_lagged = np.roll(spread_gate.astype(float), 1)
    gate_lagged[0] = 0.0

    raw_pnl    = position_lagged * pnl_arr
    gated_pnl  = raw_pnl * gate_lagged  # no explicit cost (matches K208)

    result = pd.DataFrame({
        "raw_pnl":            raw_pnl,
        "gated_pnl":          gated_pnl,
        "position":           position_lagged,
        "spread_gate_active": gate_lagged,
        "abs_spread":         abs_sp_arr,
    }, index=df.index)
    return result


# ─────────────────────────────────────────────────────────────────────────────
# Metrics
# ─────────────────────────────────────────────────────────────────────────────

def sharpe_e(pnl: np.ndarray) -> float:
    pnl = pnl[~np.isnan(pnl)]
    if len(pnl) < 10 or np.std(pnl, ddof=1) == 0:
        return 0.0
    return float(np.mean(pnl) / np.std(pnl, ddof=1) * math.sqrt(EVENTS_PER_YEAR))


def max_dd_e(pnl: np.ndarray) -> float:
    eq   = np.cumsum(pnl)
    peak = np.maximum.accumulate(eq)
    return float(np.min(eq - peak))


def wf_4fold_arr(pnl: pd.Series) -> Tuple[float, float, List[float]]:
    pnl    = pnl.dropna()
    sharpes = []
    for start, end in FOLD_BOUNDS:
        mask = (pnl.index >= pd.Timestamp(start)) & (pnl.index <= pd.Timestamp(end))
        fp   = pnl[mask].values
        if len(fp) < 5 or np.std(fp, ddof=1) == 0:
            sharpes.append(0.0)
        else:
            sharpes.append(float(np.mean(fp) / np.std(fp, ddof=1) * math.sqrt(EVENTS_PER_YEAR)))
    return (float(np.mean(sharpes)) if sharpes else 0.0,
            float(np.min(sharpes))  if sharpes else 0.0,
            [round(x, 4) for x in sharpes])


# ─────────────────────────────────────────────────────────────────────────────
# 8h Ridge Allocator (identical to K256)
# ─────────────────────────────────────────────────────────────────────────────

def extract_features(sym_pnls: Dict[str, np.ndarray], idx: int, win: int = RIDGE_FEAT_WIN) -> np.ndarray:
    feats = []
    for sym, pnl in sym_pnls.items():
        start  = max(0, idx - win)
        chunk  = pnl[start:idx]
        if len(chunk) < 3:
            feats.extend([0.0, 1.0, 0.0])
            continue
        mu  = float(np.mean(chunk))
        std = float(np.std(chunk, ddof=1)) + 1e-12
        sh  = mu / std * math.sqrt(EVENTS_PER_YEAR)
        eq   = np.cumsum(chunk)
        peak = np.maximum.accumulate(eq)
        mdd  = float(np.min(eq - peak))
        feats.extend([sh, std, mdd])
    return np.array(feats, dtype=float)


def ridge_allocator_8h(
    aligned: pd.DataFrame,
    sym_order: List[str],
) -> pd.DataFrame:
    """Walk-forward Ridge allocator at 8h event resolution."""
    n_sym  = len(sym_order)
    n      = len(aligned)
    pnl_mat = aligned[sym_order].values

    weights = np.ones((n, n_sym)) / n_sym

    ridge_model = Ridge(alpha=RIDGE_ALPHA)
    coeffs      = None
    last_refit  = -RIDGE_REFIT

    sym_pnls_dict = {sym: pnl_mat[:, i] for i, sym in enumerate(sym_order)}

    min_start = RIDGE_TRAIN_WIN + RIDGE_FEAT_WIN

    for i in range(min_start, n):
        if i - last_refit >= RIDGE_REFIT or coeffs is None:
            X_rows, y_rows = [], []
            train_start = i - RIDGE_TRAIN_WIN
            for t in range(train_start, i - RIDGE_FEAT_WIN):
                feat = extract_features(sym_pnls_dict, t, RIDGE_FEAT_WIN)
                targets = []
                for j in range(n_sym):
                    fwd = pnl_mat[t : t + RIDGE_FEAT_WIN, j]
                    if len(fwd) < 3 or np.std(fwd, ddof=1) == 0:
                        targets.append(0.0)
                    else:
                        sh = float(np.mean(fwd) / np.std(fwd, ddof=1) * math.sqrt(EVENTS_PER_YEAR))
                        targets.append(sh)
                X_rows.append(feat)
                y_rows.append(targets)

            if len(X_rows) >= 10:
                X = np.array(X_rows, dtype=float)
                y = np.array(y_rows, dtype=float)
                X_mu  = X.mean(axis=0)
                X_std = X.std(axis=0) + 1e-12
                X_n   = (X - X_mu) / X_std

                try:
                    ridge_model.fit(X_n, y)
                    coeffs = (ridge_model.coef_, ridge_model.intercept_, X_mu, X_std)
                except Exception:
                    coeffs = None

            last_refit = i

        if coeffs is not None:
            coef, intercept, X_mu, X_std = coeffs
            feat    = extract_features(sym_pnls_dict, i, RIDGE_FEAT_WIN)
            feat_n  = (feat - X_mu) / (X_std + 1e-12)
            pred_sh = feat_n @ coef.T + intercept

            recent_vols = []
            for j in range(n_sym):
                chunk = pnl_mat[max(0, i - RIDGE_FEAT_WIN) : i, j]
                if len(chunk) < 3:
                    recent_vols.append(1.0)
                else:
                    recent_vols.append(float(np.std(chunk, ddof=1)) + 1e-12)
            inv_vol = np.array([1.0 / v for v in recent_vols])

            scale      = np.clip(pred_sh, 0.0, None)
            scale_norm = scale / (scale.sum() + 1e-12)

            raw_w = inv_vol * (1.0 + scale_norm)
            raw_w = np.clip(raw_w, 0.0, None)
            raw_w /= raw_w.sum() + 1e-12

            for _ in range(20):
                capped = np.clip(raw_w, 0.0, MAX_WEIGHT)
                excess = raw_w - capped
                if excess.sum() < 1e-10:
                    raw_w = capped
                    break
                not_capped = capped < MAX_WEIGHT
                if not_capped.sum() == 0:
                    raw_w = capped
                    break
                total_excess = excess.sum()
                dist = np.zeros_like(raw_w)
                dist[not_capped] = (capped[not_capped] / (capped[not_capped].sum() + 1e-12)) * total_excess
                raw_w = capped + dist
                raw_w /= raw_w.sum() + 1e-12

            weights[i] = raw_w
        else:
            weights[i] = np.ones(n_sym) / n_sym

    return pd.DataFrame(weights, index=aligned.index, columns=sym_order)


# ─────────────────────────────────────────────────────────────────────────────
# Daily-resample & K208 correlation
# ─────────────────────────────────────────────────────────────────────────────

def to_daily(pnl_8h: pd.Series) -> pd.Series:
    return pnl_8h.resample("D").sum()


def load_k208_daily() -> Optional[pd.Series]:
    for fname in ["wave_k249_curves.json", "wave_k208_dar_reverse_carry.json"]:
        f = BASE / fname
        if not f.exists():
            continue
        with open(f) as fh:
            data = json.load(fh)
        for key in ["baseline", "k208_filtered"]:
            if key in data:
                ts   = data[key].get("timestamps", [])
                cpnl = data[key].get("cumulative_pnl", [])
                if len(ts) > 0 and len(cpnl) > 0:
                    pnl_vals = np.diff([0.0] + cpnl)
                    idx = pd.to_datetime(ts)
                    return pd.Series(pnl_vals, index=idx, name="K208_daily")
    return None


# ─────────────────────────────────────────────────────────────────────────────
# Main
# ─────────────────────────────────────────────────────────────────────────────

def main() -> Dict:
    print("=" * 70)
    print("Wave K259: K256_Ridge Rebuilt WITHOUT AXS (9-Symbol Universe)")
    print("=" * 70)
    print(f"Symbols: {REVERSE_9}")
    print(f"AXS excluded: True")

    # ── 1. Load panels ──────────────────────────────────────────────────────
    print("\n=== LOADING PANELS ===")
    panels: Dict[str, pd.DataFrame] = {}
    skipped: List[str] = []
    for sym in REVERSE_9:
        p = build_panel(sym)
        if p is None:
            print(f"  SKIP {sym}: panel build failed")
            skipped.append(sym)
        else:
            panels[sym] = p
            print(f"  {sym}: n={len(p)}  mean_abs_spread={p['abs_spread'].mean()*10000:.2f}bps  "
                  f"date_range={p.index[0].date()}..{p.index[-1].date()}")

    if not panels:
        raise RuntimeError("No panels loaded")
    print(f"\nLoaded {len(panels)} symbols, skipped: {skipped}")

    # ── 2. Per-symbol event-level PnL (DAR + spread gate) ────────────────────
    print("\n=== COMPUTING PER-SYMBOL EVENT-LEVEL PnL ===")
    sym_results: Dict[str, pd.DataFrame] = {}
    for sym, df in panels.items():
        res = compute_sym_pnl_8h(df)
        sym_results[sym] = res
        n_active = int(res["spread_gate_active"].sum())
        pnl_arr  = res["gated_pnl"].values
        sh_sym   = sharpe_e(pnl_arr)
        print(f"  {sym:6s}: Sh={sh_sym:+.3f}  active={100*n_active/len(res):.1f}%  "
              f"n_events={len(res)}")

    # ── 3. Align to common index ─────────────────────────────────────────────
    print("\n=== ALIGNING TO COMMON INDEX ===")
    pnl_dict = {sym: res["gated_pnl"] for sym, res in sym_results.items()}
    aligned  = pd.concat(pnl_dict, axis=1).fillna(0.0)
    aligned.columns = list(pnl_dict.keys())
    sym_order = list(aligned.columns)
    print(f"  Aligned: shape={aligned.shape}  date_range={aligned.index[0]}..{aligned.index[-1]}")

    # ── 4. Equal-weight baseline ─────────────────────────────────────────────
    print("\n=== EQUAL-WEIGHT BASELINE (AXS excluded) ===")
    eq_weight_pnl = aligned.mean(axis=1)
    sh_eq  = sharpe_e(eq_weight_pnl.values)
    dd_eq  = max_dd_e(eq_weight_pnl.values)
    wm_eq, wmin_eq, wf_eq = wf_4fold_arr(eq_weight_pnl)
    print(f"  Equal-weight: Sh={sh_eq:+.3f}  MaxDD={dd_eq:+.6f}  WF_min={wmin_eq:+.3f}")
    print(f"  WF folds: {[f'{x:+.2f}' for x in wf_eq]}")

    # ── 5. 8h Ridge Allocator ────────────────────────────────────────────────
    print("\n=== 8h RIDGE ALLOCATOR (9 symbols, AXS-free) ===")
    print(f"  Training window: {RIDGE_TRAIN_WIN} events, feature window: {RIDGE_FEAT_WIN} events")
    print(f"  Refit every: {RIDGE_REFIT} events, alpha={RIDGE_ALPHA}, max_weight={MAX_WEIGHT}")
    t_ridge = time.time()
    weight_df = ridge_allocator_8h(aligned, sym_order)
    print(f"  Ridge fitting time: {time.time()-t_ridge:.1f}s")

    weight_df_lagged = weight_df.shift(1).fillna(1.0 / len(sym_order))
    ridge_pnl_causal = (aligned * weight_df_lagged).sum(axis=1)

    sh_ridge  = sharpe_e(ridge_pnl_causal.values)
    dd_ridge  = max_dd_e(ridge_pnl_causal.values)
    wm_ridge, wmin_ridge, wf_ridge = wf_4fold_arr(ridge_pnl_causal)
    print(f"  Ridge-weighted (causal): Sh={sh_ridge:+.3f}  MaxDD={dd_ridge:+.6f}  WF_min={wmin_ridge:+.3f}")
    print(f"  WF folds: {[f'{x:+.2f}' for x in wf_ridge]}")

    # ── 6. Gate 0 WF fold check ──────────────────────────────────────────────
    print("\n=== GATE 0: WF FOLDS POSITIVE CHECK ===")
    folds_all_positive = all(f > 0 for f in wf_ridge)
    for i, (start, end) in enumerate(FOLD_BOUNDS):
        status = "PASS" if wf_ridge[i] > 0 else "FAIL"
        print(f"  Fold {i+1} ({start}..{end}): Sh={wf_ridge[i]:+.4f} -> {status}")

    # ── 7. Daily resample & K208 correlation ─────────────────────────────────
    print("\n=== DAILY RESAMPLE & K208 CORRELATION ===")
    ridge_daily = to_daily(ridge_pnl_causal)
    eq_daily    = to_daily(eq_weight_pnl)

    k208_daily_pnl = load_k208_daily()
    corr_ridge_k208 = None
    if k208_daily_pnl is not None:
        common_idx = ridge_daily.index.intersection(k208_daily_pnl.index)
        if len(common_idx) > 20:
            corr_ridge_k208 = float(
                pd.Series(ridge_daily.reindex(common_idx).values).corr(
                    pd.Series(k208_daily_pnl.reindex(common_idx).values)
                )
            )
            corr_eq_k208 = float(
                pd.Series(eq_daily.reindex(common_idx).values).corr(
                    pd.Series(k208_daily_pnl.reindex(common_idx).values)
                )
            )
            print(f"  K259 Ridge vs K208 daily corr: {corr_ridge_k208:+.4f}")
            print(f"  K259 EqWt  vs K208 daily corr: {corr_eq_k208:+.4f}")
        else:
            print("  K208 daily PnL insufficient overlap for correlation")
    else:
        print("  K208 daily PnL not available")

    # ── 8. Gate 0 evaluation ────────────────────────────────────────────────
    print("\n=== GATE 0 EVALUATION (K259 Standalone) ===")
    gate_wf_ok  = folds_all_positive
    gate_oos_ok = sh_ridge >= GATE_OOS_SH_MIN
    gate_rho_ok = (corr_ridge_k208 is not None and corr_ridge_k208 <= GATE_RHO_K208_MAX)

    print(f"  [Gate 1] All WF folds > 0:           {'PASS' if gate_wf_ok else 'FAIL'}")
    print(f"           Folds: {[f'{x:+.2f}' for x in wf_ridge]}")
    print(f"  [Gate 2] Standalone OOS Sh >= {GATE_OOS_SH_MIN}: "
          f"{'PASS' if gate_oos_ok else 'FAIL'} ({sh_ridge:.4f})")
    if corr_ridge_k208 is not None:
        print(f"  [Gate 3] Daily rho vs K208 <= {GATE_RHO_K208_MAX}:   "
              f"{'PASS' if gate_rho_ok else 'FAIL'} ({corr_ridge_k208:.4f})")
    else:
        print(f"  [Gate 3] Daily rho vs K208:           N/A (K208 baseline unavailable)")
        gate_rho_ok = None

    gates_passed = sum([g for g in [gate_wf_ok, gate_oos_ok, gate_rho_ok] if g is not None])
    gates_total  = sum([1 for g in [gate_wf_ok, gate_oos_ok, gate_rho_ok] if g is not None])

    if gate_wf_ok and gate_oos_ok and (gate_rho_ok is None or gate_rho_ok):
        verdict = "PASS"
        action  = "K260 integration APPROVED: K198 + K259 + K226 5-way meta integration"
    elif not gate_wf_ok:
        verdict = "FAIL"
        action  = ("ABORT K260. WF fold(s) still negative after AXS exclusion. "
                   "Ridge allocator instability not caused solely by AXS. "
                   "Investigate further or confirm K246a v6.9 (K198+K208+K226) as production final.")
    elif not gate_oos_ok:
        verdict = "FAIL"
        action  = ("ABORT K260. OOS Sharpe below 1.5 threshold. "
                   "K259 lacks standalone alpha. Confirm K246a v6.9 as production final.")
    else:
        verdict = "FAIL"
        action  = ("ABORT K260. Daily rho vs K208 > 0.7. "
                   "K259 is not genuinely orthogonal to K208. "
                   "Confirm K246a v6.9 as production final.")

    print(f"\n  VERDICT: {verdict}  ({gates_passed}/{gates_total} gates)")
    print(f"  ACTION: {action}")

    # ── 9. Comparison table ──────────────────────────────────────────────────
    print("\n=== COMPARISON TABLE ===")
    print(f"  {'Version':<30} {'OOS Sh':>8} {'WF min':>8}  WF folds")
    print(f"  {'-'*85}")
    rows = [
        ("K208 daily (baseline)",    K208_OOS_SH,       K208_WF_MIN,       K208_WF_FOLDS),
        ("K246a v6.9 production",    K246A_OOS_SH,      K246A_WF_MIN,      []),
        ("K256_EqWt 10-sym+AXS",     K256_EQWT_OOS_SH,  K256_EQWT_WF_MIN,  []),
        ("K256_Ridge 10-sym+AXS",    K256_RIDGE_OOS_SH, K256_RIDGE_WF_MIN, []),
        ("K259_EqWt 9-sym (no AXS)", sh_eq,             wmin_eq,           wf_eq),
        ("K259_Ridge 9-sym (no AXS)",sh_ridge,          wmin_ridge,        wf_ridge),
    ]
    for name, oos, wfmin, folds in rows:
        fold_s = str([f'{x:+.2f}' for x in folds]) if folds else "  N/A"
        print(f"  {name:<30} {oos:>8.2f} {wfmin:>8.2f}  {fold_s}")

    # ── 10. Weight statistics ─────────────────────────────────────────────────
    print("\n=== WEIGHT STATISTICS ===")
    for sym in sym_order:
        w = weight_df_lagged[sym].values
        print(f"  {sym:6s}: mean={w.mean():.3f}  std={w.std():.3f}  min={w.min():.3f}  max={w.max():.3f}")

    # ── 11. Build curves JSON ─────────────────────────────────────────────────
    print("\n=== BUILDING CURVES ===")
    curves: Dict = {
        "K259_ridge_8h": {
            "cumulative_pnl": [round(float(v), 8) for v in ridge_pnl_causal.fillna(0).cumsum()],
            "timestamps":     [t.isoformat() for t in ridge_pnl_causal.index],
            "label":          "K259 Ridge 9-sym (no AXS) 8h native equity",
        },
        "K259_eqwt_8h": {
            "cumulative_pnl": [round(float(v), 8) for v in eq_weight_pnl.fillna(0).cumsum()],
            "timestamps":     [t.isoformat() for t in eq_weight_pnl.index],
            "label":          "K259 Equal-weight 9-sym (no AXS) 8h equity",
        },
        "K259_ridge_daily": {
            "cumulative_pnl": [round(float(v), 8) for v in ridge_daily.fillna(0).cumsum()],
            "timestamps":     [t.isoformat() for t in ridge_daily.index],
            "label":          "K259 Ridge daily-aggregated equity",
        },
        "K259_eqwt_daily": {
            "cumulative_pnl": [round(float(v), 8) for v in eq_daily.fillna(0).cumsum()],
            "timestamps":     [t.isoformat() for t in eq_daily.index],
            "label":          "K259 EqWt daily-aggregated equity",
        },
    }

    for sym in sym_order:
        sample_idx = list(range(0, len(weight_df_lagged), 30))
        curves[f"weight_{sym}"] = {
            "values":     [round(float(weight_df_lagged[sym].iloc[i]), 4) for i in sample_idx],
            "timestamps": [weight_df_lagged.index[i].isoformat() for i in sample_idx],
            "label":      f"K259 weight for {sym}",
        }

    print(f"  Built {len(curves)} curve series")

    # ── 12. Assemble output JSON ──────────────────────────────────────────────
    runtime = round(time.time() - t_start, 1)
    output  = {
        "wave":         "K259",
        "parent_waves": ["K256", "K258"],
        "objective":    "K256_Ridge rebuilt without AXS (9-symbol universe). Verify WF stability.",
        "hypothesis":   "AXS data contaminates K256_Ridge WF fold 2 (WF min=0.32). Remove AXS -> all folds positive.",
        "as_of":        pd.Timestamp.now(tz="UTC").isoformat(),
        "runtime_s":    runtime,

        "config": {
            "symbols":           sym_order,
            "symbols_excluded":  ["AXS"],
            "n_symbols":         len(sym_order),
            "dar_p":             PRIMARY_P,
            "dar_q":             PRIMARY_Q,
            "dar_win":           PRIMARY_WIN,
            "dar_refit":         PRIMARY_REFIT,
            "spread_gate_win":   SPREAD_GATE_WIN,
            "spread_gate_pct":   SPREAD_GATE_PCT,
            "ridge_feat_win":    RIDGE_FEAT_WIN,
            "ridge_train_win":   RIDGE_TRAIN_WIN,
            "ridge_refit":       RIDGE_REFIT,
            "ridge_alpha":       RIDGE_ALPHA,
            "max_weight":        MAX_WEIGHT,
            "cost_per_side_bps": 0.0,
            "events_per_year":   EVENTS_PER_YEAR,
            "ml_window":         {"start": ML_START, "end": ML_END},
            "fold_bounds":       [{"fold": i+1, "start": s, "end": e}
                                   for i, (s, e) in enumerate(FOLD_BOUNDS)],
        },

        "gate0_thresholds": {
            "wf_all_folds_positive": True,
            "oos_sh_min":            GATE_OOS_SH_MIN,
            "rho_k208_max":          GATE_RHO_K208_MAX,
        },

        "reference_metrics": {
            "K208_daily":       {"oos_sh": K208_OOS_SH,       "wf_min": K208_WF_MIN,       "wf_folds": K208_WF_FOLDS},
            "K246a_v6_9":       {"oos_sh": K246A_OOS_SH,      "wf_min": K246A_WF_MIN},
            "K256_EqWt_10sym":  {"oos_sh": K256_EQWT_OOS_SH,  "wf_min": K256_EQWT_WF_MIN},
            "K256_Ridge_10sym": {"oos_sh": K256_RIDGE_OOS_SH, "wf_min": K256_RIDGE_WF_MIN,
                                 "rho_k208": K256_RIDGE_RHO_K208,
                                 "note": "AXS contaminated fold 2"},
        },

        "results": {
            "K259_eqwt_9sym": {
                "sharpe_oos":   round(sh_eq, 4),
                "max_dd":       round(dd_eq, 6),
                "wf_mean":      round(wm_eq, 4),
                "wf_min":       round(wmin_eq, 4),
                "wf_folds":     wf_eq,
            },
            "K259_ridge_9sym": {
                "sharpe_oos":   round(sh_ridge, 4),
                "max_dd":       round(dd_ridge, 6),
                "wf_mean":      round(wm_ridge, 4),
                "wf_min":       round(wmin_ridge, 4),
                "wf_folds":     wf_ridge,
                "wf_all_positive": folds_all_positive,
                "corr_k208_daily": round(corr_ridge_k208, 4) if corr_ridge_k208 is not None else None,
            },
        },

        "per_symbol": {},

        "gate0": {
            "gate1_wf_all_positive": gate_wf_ok,
            "gate2_oos_sh_ok":       gate_oos_ok,
            "gate3_rho_ok":          gate_rho_ok,
            "gates_passed":          gates_passed,
            "gates_total":           gates_total,
            "verdict":               verdict,
            "action":                action,
        },

        "comparison": {
            "K208_daily":             {"oos_sh": K208_OOS_SH,       "wf_min": K208_WF_MIN},
            "K246a_v6_9":             {"oos_sh": K246A_OOS_SH,      "wf_min": K246A_WF_MIN},
            "K256_EqWt_10sym_AXS":    {"oos_sh": K256_EQWT_OOS_SH,  "wf_min": K256_EQWT_WF_MIN},
            "K256_Ridge_10sym_AXS":   {"oos_sh": K256_RIDGE_OOS_SH, "wf_min": K256_RIDGE_WF_MIN,
                                       "rho_k208": K256_RIDGE_RHO_K208},
            "K259_EqWt_9sym_noAXS":   {"oos_sh": round(sh_eq,4),    "wf_min": round(wmin_eq,4)},
            "K259_Ridge_9sym_noAXS":  {"oos_sh": round(sh_ridge,4), "wf_min": round(wmin_ridge,4),
                                       "rho_k208": round(corr_ridge_k208,4) if corr_ridge_k208 is not None else None},
        },
    }

    for sym, res in sym_results.items():
        pnl_arr = res["gated_pnl"].values
        output["per_symbol"][sym] = {
            "n_events":   len(res),
            "n_active":   int(res["spread_gate_active"].sum()),
            "pct_active": round(100 * float(res["spread_gate_active"].mean()), 1),
            "sharpe":     round(sharpe_e(pnl_arr), 4),
            "max_dd":     round(max_dd_e(pnl_arr), 6),
        }

    # ── 13. Write outputs ─────────────────────────────────────────────────────
    json_path   = BASE / "wave_k259_k256_ridge_no_axs.json"
    curves_path = BASE / "wave_k259_curves.json"

    json_path.write_text(json.dumps(output, indent=2, default=str))
    curves_path.write_text(json.dumps(curves, default=str))

    print(f"\nWrote {json_path} ({json_path.stat().st_size:,} bytes)")
    print(f"Wrote {curves_path} ({curves_path.stat().st_size:,} bytes)")
    print(f"Total runtime: {runtime}s")
    print(f"\n{'='*70}")
    print(f"FINAL VERDICT: {verdict}")
    print(f"ACTION: {action}")
    print(f"{'='*70}")

    return output


if __name__ == "__main__":
    main()

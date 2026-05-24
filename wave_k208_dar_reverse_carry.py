"""Wave K208 - DAR(2,1) FR Predictor Filter for K196 Reverse Carry Panel.

Hypothesis (K190 extension):
  K190 showed DAR(2,1) has OOS direction accuracy 66.3% for XRP+SUI in K175.
  Apply same per-symbol DAR(2,1) walk-forward filter to all 10 K196 reverse
  carry symbols (SOL/XRP/SUI/OP/APT/AXS/JTO/IMX/SAND/ADA).

K196 reverse carry logic:
  LONG HL + SHORT Bybit = receive (Bybit_FR - HL_FR) per 8h event.
  K196-favorable direction: Bybit FR > HL FR (i.e., spread > 0).

DAR(2,1) filter:
  At each 8h event, predict next period Bybit FR (pred_fr_{t+1}).
  K196 entry gate: only receive if predicted spread is positive,
  i.e., pred_bybit_fr > hl_fr_8h (predicted Bybit will remain above HL).

Walk-forward parameters (same as K190 primary):
  - Rolling window: 300 events
  - Refit every: 50 events
  - Features: intercept, FR_{t-1}, FR_{t-2}, spread_z_{t-1}

Variants:
  1. Baseline (no filter) = K196 reverse carry panel
  2. K208 filtered = DAR(2,1) gate applied per-symbol
  3. K208 filtered + K198 ML allocator ensemble

§6 gates applied if standalone panel OOS Sh improvement >= +0.05.

Runtime target: <12 min.
"""
from __future__ import annotations

import json
import math
import time
import warnings
from math import erf, sqrt
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import numpy as np
import pandas as pd

warnings.filterwarnings("ignore")

START_TIME = time.time()
BASE     = Path("/Users/nekonaomichi/crypto-lab")
CACHE    = BASE / "cache"
HL_CACHE = CACHE / "k163_hl"

TRADING_DAYS = 365     # annualisation basis for daily Sharpe
EVENTS_PER_DAY = 3     # 3 × 8h events per day
EVENTS_PER_YEAR = TRADING_DAYS * EVENTS_PER_DAY   # 1095

OOS_FRAC   = 0.30
N_FOLDS    = 4
TRAIN_FRAC = 0.70

# 10 reverse carry symbols from K196
REVERSE_10 = ["SOL", "XRP", "SUI", "OP", "APT", "AXS", "JTO", "IMX", "SAND", "ADA"]

# Primary DAR config (matches K190 winning variant)
PRIMARY_P     = 2
PRIMARY_Q     = 1
PRIMARY_WIN   = 300
PRIMARY_REFIT = 50

# K196 reference metrics for comparison table
K196_OOS_SH  = 9.20
K196_OOS_DD  = -0.0038
K196_WF_MEAN = 5.37
K196_WF_MIN  = 3.54

# K198 reference metrics
K198_OOS_SH  = 10.28
K198_OOS_DD  = -0.0053
K198_WF_MEAN = 7.91
K198_WF_MIN  = 6.57

# §6 acceptance gates config
S6_MIN_GATES_PASS = 4  # out of 7 → PASS


# ──────────────────────────────────────────────────────────────────────────────
# Data Loading
# ──────────────────────────────────────────────────────────────────────────────

def load_hl_fr(sym: str) -> Optional[pd.Series]:
    f = HL_CACHE / f"hl_fr_{sym}.parquet"
    if not f.exists():
        return None
    df = pd.read_parquet(f)
    # Column may be 'hl_fr' or 'funding_rate'
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


def build_panel(sym: str) -> Optional[pd.DataFrame]:
    """Build aligned (bybit_fr, hl_fr_8h, spread, fwd_spread) per-symbol DataFrame."""
    hl = load_hl_fr(sym)
    by = load_bybit_fr(sym)
    if hl is None or by is None:
        return None

    # Resample HL to 8h sums (matching Bybit 8h settlement)
    hl_8h = hl.resample("8h", label="right", closed="right").sum(min_count=1)

    idx = by.index
    df = pd.DataFrame({"bybit_fr": by}, index=idx)
    df["hl_fr_8h"] = hl_8h.reindex(idx)
    df = df.dropna()
    if len(df) < 50:
        return None

    df["spread"] = df["bybit_fr"] - df["hl_fr_8h"]
    # Reverse carry PnL per event = spread (receive Bybit_FR - HL_FR)
    df["rev_carry_pnl"] = df["spread"].shift(-1)  # next period carry received
    df = df.dropna(subset=["rev_carry_pnl"])

    if len(df) < 50:
        return None
    return df


# ──────────────────────────────────────────────────────────────────────────────
# DAR Model
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
    """Build single design row for DAR(p,q) at position idx.
    Features: intercept, FR_{t-1..t-p}, spread_z_{t-1..t-q}.
    """
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
    p: int = 2,
    q: int = 1,
    win: int = 300,
    refit: int = 50,
) -> Tuple[np.ndarray, np.ndarray, Dict]:
    """Walk-forward DAR(p,q) predictor.

    Returns:
        pred_fr   : predicted FR values (NaN where unavailable)
        is_valid  : boolean mask where predictions are available
        diag      : OOS R², direction_acc, n_oos
    """
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
        return pred_fr, is_valid, {"oos_r2": np.nan, "direction_acc": np.nan, "n_oos": 0}

    y_true = fr[valid_idx]
    y_pred  = pred_fr[valid_idx]
    ss_res  = np.sum((y_true - y_pred) ** 2)
    ss_tot  = np.sum((y_true - y_true.mean()) ** 2)
    oos_r2  = float(1 - ss_res / (ss_tot + 1e-30))

    # Direction accuracy: predicted direction of next change vs actual
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
# Metrics (8h event-level → annualise using EVENTS_PER_YEAR)
# ──────────────────────────────────────────────────────────────────────────────

def sharpe_e(pnl: pd.Series) -> float:
    """Annualised Sharpe using 8h events."""
    pnl = pnl.dropna()
    if len(pnl) < 10 or pnl.std(ddof=1) == 0:
        return 0.0
    return float(pnl.mean() / pnl.std(ddof=1) * math.sqrt(EVENTS_PER_YEAR))


def max_dd_e(pnl: pd.Series) -> float:
    eq   = pnl.cumsum()
    peak = eq.cummax()
    return float((eq - peak).min())


def wf_4fold(pnl: pd.Series) -> Tuple[float, float, List[float]]:
    pnl = pnl.dropna()
    if len(pnl) < 40:
        return 0.0, 0.0, []
    folds = np.array_split(pnl.values, 4)
    sharpes = []
    for f in folds:
        s = pd.Series(f)
        if len(s) < 5 or s.std(ddof=1) == 0:
            sharpes.append(0.0)
        else:
            sharpes.append(float(s.mean() / s.std(ddof=1) * math.sqrt(EVENTS_PER_YEAR)))
    return float(np.mean(sharpes)), float(np.min(sharpes)), [round(x, 4) for x in sharpes]


def perm_test(pnl: pd.Series, n: int = 300, seed: int = 7) -> float:
    rng  = np.random.default_rng(seed)
    obs  = sharpe_e(pnl)
    vals = pnl.dropna().values
    if len(vals) < 10 or pnl.std() == 0:
        return 1.0
    null = []
    for _ in range(n):
        sp = rng.permutation(vals)
        s  = pd.Series(sp)
        null.append(float(s.mean() / (s.std(ddof=1) + 1e-12) * math.sqrt(EVENTS_PER_YEAR)))
    arr = np.array(null)
    return float((arr >= obs).mean()) if obs > 0 else float((arr <= obs).mean())


def bootstrap_ci(pnl: pd.Series, n: int = 300, seed: int = 11) -> Tuple[float, float]:
    rng  = np.random.default_rng(seed)
    vals = pnl.dropna().values
    if len(vals) < 30:
        return 0.0, 0.0
    sharpes = []
    for _ in range(n):
        s = pd.Series(vals[rng.integers(0, len(vals), size=len(vals))])
        sharpes.append(float(s.mean() / (s.std(ddof=1) + 1e-12) * math.sqrt(EVENTS_PER_YEAR)))
    return float(np.percentile(sharpes, 5)), float(np.percentile(sharpes, 95))


def dsr_score(pnl: pd.Series, n_trials: int = 4) -> float:
    pnl = pnl.dropna()
    if len(pnl) < 30 or pnl.std(ddof=1) == 0:
        return 0.0
    sr = pnl.mean() / pnl.std(ddof=1)
    T  = len(pnl)
    sk = float(((pnl - pnl.mean()) ** 3).mean() / (pnl.std() ** 3 + 1e-12))
    kt = float(((pnl - pnl.mean()) ** 4).mean() / (pnl.std() ** 4 + 1e-12))
    emc   = 0.5772
    e_max = math.sqrt(2 * math.log(max(n_trials, 2))) - emc / math.sqrt(2 * math.log(max(n_trials, 2)))
    inner = (1 - sk * sr + (kt - 1) / 4 * sr ** 2) / max(T - 1, 1)
    if inner <= 0:
        return 0.0
    denom = math.sqrt(inner)
    if denom <= 0:
        return 0.0
    z = (sr - e_max) / denom
    return float(0.5 * (1 + erf(z / sqrt(2))))


def equity_curve(pnl: pd.Series) -> List[float]:
    return list(pnl.fillna(0).cumsum().round(8))


def full_metrics(name: str, pnl: pd.Series) -> Dict:
    pnl    = pnl.dropna()
    n      = len(pnl)
    split  = int(n * TRAIN_FRAC)
    is_pnl = pnl.iloc[:split]
    oos_pnl = pnl.iloc[split:]
    sh_full  = sharpe_e(pnl)
    sh_is    = sharpe_e(is_pnl)
    sh_oos   = sharpe_e(oos_pnl)
    dd_full  = max_dd_e(pnl)
    dd_oos   = max_dd_e(oos_pnl)
    wf_mean, wf_min, wf_folds = wf_4fold(pnl)
    perm_p  = perm_test(pnl)
    ci_lo, ci_hi = bootstrap_ci(pnl)
    dsr_p   = dsr_score(pnl)
    trades_per_year = n / (n / EVENTS_PER_YEAR) if n > 0 else 0  # 100% always active
    return {
        "variant": name,
        "sharpe_full": round(sh_full, 4),
        "sharpe_is": round(sh_is, 4),
        "sharpe_oos": round(sh_oos, 4),
        "max_dd_full": round(dd_full, 6),
        "max_dd_oos": round(dd_oos, 6),
        "wf_mean": round(wf_mean, 4),
        "wf_min": round(wf_min, 4),
        "wf_folds": wf_folds,
        "perm_pvalue": round(perm_p, 4),
        "bootstrap_ci_5_95": [round(ci_lo, 4), round(ci_hi, 4)],
        "dsr": round(dsr_p, 4),
        "n_events": int(n),
    }


# ──────────────────────────────────────────────────────────────────────────────
# Reverse Carry Strategies
# ──────────────────────────────────────────────────────────────────────────────

def zscore_rolling(s: pd.Series, win: int = 30) -> pd.Series:
    mu = s.rolling(win, min_periods=win).mean()
    sd = s.rolling(win, min_periods=win).std()
    return (s - mu) / (sd + 1e-12)


def run_baseline_reverse_panel(
    panels: Dict[str, pd.DataFrame],
) -> Tuple[pd.Series, Dict[str, pd.Series], Dict[str, float]]:
    """K196 reverse carry: always-on equal weight, receive spread each event."""
    per_sym: Dict[str, pd.Series] = {}
    per_sh: Dict[str, float] = {}
    for sym, df in panels.items():
        pnl = df["rev_carry_pnl"].copy()
        per_sym[sym] = pnl
        per_sh[sym] = sharpe_e(pnl)

    if not per_sym:
        return pd.Series(dtype=float), {}, {}

    aligned = pd.concat(per_sym, axis=1).fillna(0.0)
    panel_pnl = aligned.mean(axis=1)
    return panel_pnl, per_sym, per_sh


def run_dar_filtered_reverse_panel(
    panels: Dict[str, pd.DataFrame],
    p: int = PRIMARY_P,
    q: int = PRIMARY_Q,
    win: int = PRIMARY_WIN,
    refit: int = PRIMARY_REFIT,
) -> Tuple[pd.Series, Dict[str, pd.Series], Dict[str, float], Dict[str, Dict], Dict[str, Dict]]:
    """K208: DAR(p,q) filter applied per-symbol before entering reverse carry.

    Filter gate:
      Only receive carry at event t+1 if pred_bybit_fr[t+1] > hl_fr_8h[t]
      (i.e., predicted Bybit FR will still exceed HL FR next period).
      Equivalently: pred_spread > 0.
    """
    per_sym:     Dict[str, pd.Series] = {}
    per_sh:      Dict[str, float] = {}
    dar_diag:    Dict[str, Dict] = {}
    filter_stats: Dict[str, Dict] = {}

    for sym, df in panels.items():
        fr_arr      = df["bybit_fr"].values.copy()
        spread_arr  = df["spread"].values.copy()
        spread_z    = zscore_rolling(df["spread"], 30).fillna(0.0).values

        # Walk-forward DAR prediction
        pred_fr, is_valid, diag = dar_walk_forward(fr_arr, spread_z, p=p, q=q, win=win, refit=refit)
        dar_diag[sym] = diag

        # Build per-event filter mask:
        # predict whether next period spread > 0 (i.e., pred_bybit_fr > current hl_fr_8h)
        # We use current HL FR as best estimate of next HL FR (HL tends to be persistent)
        hl_arr  = df["hl_fr_8h"].values.copy()
        n       = len(df)
        gate    = np.zeros(n, dtype=bool)

        for i in range(n):
            if not is_valid[i]:
                continue
            pred_spread = pred_fr[i] - hl_arr[i]
            if pred_spread > 0:
                gate[i] = True

        # Apply gate: only hold position (receive carry) when gate is True
        # rev_carry_pnl at index i is the carry received at event i+1
        # So gate at i controls whether we receive pnl at i
        gate_series = pd.Series(gate, index=df.index)
        # Shift gate by 1 to avoid look-ahead: decide at i-1 to enter at i
        gate_lagged = gate_series.shift(1).fillna(False)

        base_pnl = df["rev_carry_pnl"].copy()
        filtered_pnl = base_pnl.where(gate_lagged, 0.0)

        per_sym[sym] = filtered_pnl
        per_sh[sym]  = sharpe_e(filtered_pnl)

        n_total   = int((~base_pnl.isna()).sum())
        n_active  = int((gate_lagged & ~base_pnl.isna()).sum())
        n_baseline = int((~base_pnl.isna()).sum())
        filter_stats[sym] = {
            "n_total_events": n_total,
            "n_active_filtered": n_active,
            "filter_rate_pct": round(100 * (1 - n_active / max(n_baseline, 1)), 1),
            "pct_in_market": round(100 * n_active / max(n_baseline, 1), 1),
        }

    if not per_sym:
        return pd.Series(dtype=float), {}, {}, {}, {}

    aligned   = pd.concat(per_sym, axis=1).fillna(0.0)
    panel_pnl = aligned.mean(axis=1)
    return panel_pnl, per_sym, per_sh, dar_diag, filter_stats


# ──────────────────────────────────────────────────────────────────────────────
# §6 Strict Gates
# ──────────────────────────────────────────────────────────────────────────────

def apply_s6_gates(m: Dict) -> Tuple[Dict, int, str]:
    """§6 strict gates on K208 filtered reverse panel."""
    gates = {
        "G1_oos_sharpe_gt_5": m["sharpe_oos"] >= 5.0,
        "G2_oos_sharpe_gt_k196": m["sharpe_oos"] >= K196_OOS_SH,
        "G3_oos_dd_not_worse": m["max_dd_oos"] >= K196_OOS_DD * 1.5,  # max 50% worse
        "G4_wf_mean_gt_5": m["wf_mean"] >= 5.0,
        "G5_wf_min_gt_3p5": m["wf_min"] >= 3.5,
        "G6_perm_p_le_0p1": m["perm_pvalue"] <= 0.10,
        "G7_dsr_gt_0p5": m["dsr"] >= 0.5,
    }
    n_pass  = int(sum(gates.values()))
    verdict = "PASS" if n_pass >= S6_MIN_GATES_PASS else ("MARGINAL" if n_pass >= 3 else "FAIL")
    return gates, n_pass, verdict


# ──────────────────────────────────────────────────────────────────────────────
# Main
# ──────────────────────────────────────────────────────────────────────────────

def main() -> Dict:
    t0 = time.time()

    # ── 1. Load panels ──────────────────────────────────────────────────────
    print("=" * 70)
    print("Wave K208: DAR(2,1) Filter for K196 Reverse Carry Panel")
    print("=" * 70)

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

    # ── 2. Baseline: K196 reverse carry (no filter) ─────────────────────────
    print("\n=== BASELINE: K196 Reverse Carry (No Filter) ===")
    bl_panel, bl_per_sym, bl_per_sh = run_baseline_reverse_panel(panels)
    bl_metrics = full_metrics("K196_baseline_no_filter", bl_panel)

    print(f"  Sh_full={bl_metrics['sharpe_full']:+.3f}  Sh_OOS={bl_metrics['sharpe_oos']:+.3f}  "
          f"MaxDD_OOS={bl_metrics['max_dd_oos']:+.4f}  "
          f"WF_mean={bl_metrics['wf_mean']:+.2f}  WF_min={bl_metrics['wf_min']:+.2f}")
    print(f"  Per-symbol Sh: {', '.join(f'{s}={v:+.2f}' for s, v in sorted(bl_per_sh.items()))}")

    # ── 3. DAR model diagnostics per symbol ─────────────────────────────────
    print("\n=== DAR(2,1) MODEL DIAGNOSTICS (PRIMARY CONFIG) ===")
    dar_standalone_diag: Dict[str, Dict] = {}
    for sym, df in panels.items():
        fr_arr   = df["bybit_fr"].values.copy()
        spread_z = zscore_rolling(df["spread"], 30).fillna(0.0).values
        _, _, diag = dar_walk_forward(fr_arr, spread_z, p=PRIMARY_P, q=PRIMARY_Q,
                                      win=PRIMARY_WIN, refit=PRIMARY_REFIT)
        dar_standalone_diag[sym] = diag
        acc_flag = "PASS" if diag.get("direction_acc", 0) >= 0.55 else "FAIL"
        print(f"  {sym:6s}: OOS_R2={diag.get('oos_r2', float('nan')):.4f}  "
              f"dir_acc={diag.get('direction_acc', float('nan')):.4f} [{acc_flag}]  "
              f"n_oos={diag.get('n_oos', 0)}")

    n_pass_dir = sum(1 for d in dar_standalone_diag.values()
                     if d.get("direction_acc", 0) >= 0.55)
    print(f"\n  Direction accuracy >55%: {n_pass_dir}/{len(dar_standalone_diag)} symbols")

    # ── 4. K208 filtered reverse carry ──────────────────────────────────────
    print("\n=== K208: DAR(2,1) Filtered Reverse Carry ===")
    filt_panel, filt_per_sym, filt_per_sh, filt_dar_diag, filt_stats = (
        run_dar_filtered_reverse_panel(panels)
    )
    filt_metrics = full_metrics("K208_dar_filtered", filt_panel)

    print(f"  Sh_full={filt_metrics['sharpe_full']:+.3f}  Sh_OOS={filt_metrics['sharpe_oos']:+.3f}  "
          f"MaxDD_OOS={filt_metrics['max_dd_oos']:+.4f}  "
          f"WF_mean={filt_metrics['wf_mean']:+.2f}  WF_min={filt_metrics['wf_min']:+.2f}")

    delta_oos = filt_metrics["sharpe_oos"] - bl_metrics["sharpe_oos"]
    print(f"\n  ΔOOS Sharpe vs baseline: {delta_oos:+.3f} "
          f"(acceptance threshold: >= +0.05)")

    # Per-symbol comparison
    print("\n  Per-symbol comparison (baseline vs filtered):")
    per_sym_comparison = {}
    for sym in sorted(panels.keys()):
        bl_sh = bl_per_sh.get(sym, 0.0)
        f_sh  = filt_per_sh.get(sym, 0.0)
        fs    = filt_stats.get(sym, {})
        pct_in = fs.get("pct_in_market", 0.0)
        filt_rate = fs.get("filter_rate_pct", 0.0)
        delta = f_sh - bl_sh
        print(f"    {sym:6s}: BL={bl_sh:+.2f}  Filt={f_sh:+.2f}  "
              f"Δ={delta:+.2f}  InMarket={pct_in:.0f}%  Filtered={filt_rate:.0f}%")
        per_sym_comparison[sym] = {
            "baseline_sharpe": round(bl_sh, 4),
            "filtered_sharpe": round(f_sh, 4),
            "delta_sharpe": round(delta, 4),
            "pct_in_market": pct_in,
            "filter_rate_pct": filt_rate,
            "dar_direction_acc": round(filt_dar_diag.get(sym, {}).get("direction_acc", float("nan")), 4),
            "dar_oos_r2": round(filt_dar_diag.get(sym, {}).get("oos_r2", float("nan")), 5),
        }

    # ── 5. §6 Gates on filtered panel ───────────────────────────────────────
    print("\n=== §6 STRICT GATES ===")
    lift_qualifies = delta_oos >= 0.05
    gates, gates_passed, gates_verdict = apply_s6_gates(filt_metrics)
    print(f"  Lift qualifies for §6: {lift_qualifies} (Δ={delta_oos:+.3f} >= 0.05)")
    for g, v in gates.items():
        flag = "PASS" if v else "FAIL"
        print(f"    {g}: [{flag}]")
    print(f"  §6 verdict: {gates_passed}/7 → {gates_verdict}")

    # ── 6. Five-way comparison table ─────────────────────────────────────────
    print("\n=== FIVE-WAY COMPARISON TABLE ===")
    five_way = {
        "K196_baseline": {
            "description": "K196 reverse carry panel (no filter)",
            "oos_sharpe": K196_OOS_SH,
            "oos_max_dd": K196_OOS_DD,
            "wf_mean": K196_WF_MEAN,
            "wf_min": K196_WF_MIN,
            "source": "K196 JSON"
        },
        "K198_ML_alone": {
            "description": "K198 Ridge ML allocator (current production)",
            "oos_sharpe": K198_OOS_SH,
            "oos_max_dd": K198_OOS_DD,
            "wf_mean": K198_WF_MEAN,
            "wf_min": K198_WF_MIN,
            "source": "K198 JSON"
        },
        "K208_reverse_filtered_standalone": {
            "description": "K208 DAR(2,1) filtered reverse panel (standalone)",
            "oos_sharpe": round(filt_metrics["sharpe_oos"], 4),
            "oos_max_dd": round(filt_metrics["max_dd_oos"], 6),
            "wf_mean": round(filt_metrics["wf_mean"], 4),
            "wf_min": round(filt_metrics["wf_min"], 4),
            "source": "computed"
        },
        "K208_vs_K196_delta": {
            "description": "Delta: K208 standalone vs K196 baseline",
            "oos_sharpe": round(filt_metrics["sharpe_oos"] - K196_OOS_SH, 4),
            "oos_max_dd": round(filt_metrics["max_dd_oos"] - K196_OOS_DD, 6),
            "wf_mean": round(filt_metrics["wf_mean"] - K196_WF_MEAN, 4),
            "wf_min": round(filt_metrics["wf_min"] - K196_WF_MIN, 4),
            "source": "computed"
        },
    }

    header = f"{'Version':<40} {'OOS Sh':>8} {'OOS MaxDD':>10} {'WF mean':>8} {'WF min':>8}"
    print(f"\n  {header}")
    print(f"  {'-'*40} {'-'*8} {'-'*10} {'-'*8} {'-'*8}")
    for k, v in five_way.items():
        if k.endswith("_delta"):
            print(f"  {'  ' + k:<40} {v['oos_sharpe']:>+8.2f} {v['oos_max_dd']:>+10.4f} "
                  f"{v['wf_mean']:>+8.2f} {v['wf_min']:>+8.2f}")
        else:
            print(f"  {k:<40} {v['oos_sharpe']:>8.2f} {v['oos_max_dd']:>10.4f} "
                  f"{v['wf_mean']:>8.2f} {v['wf_min']:>8.2f}")

    # ── 7. Acceptance verdict ─────────────────────────────────────────────────
    print("\n=== ACCEPTANCE VERDICT ===")
    criteria = {
        "dir_acc_gt55_most": n_pass_dir >= len(panels) * 0.6,
        "oos_sh_improvement": delta_oos >= 0.0,
        "oos_sh_clear_lift": delta_oos >= 0.05,
        "trade_reduction": (
            np.mean([s.get("filter_rate_pct", 0) for s in filt_stats.values()]) >= 10
        ),
        "s6_gates_pass": gates_passed >= S6_MIN_GATES_PASS,
    }
    n_crit = sum(criteria.values())

    if n_crit >= 4:
        verdict = "ACCEPT → integrate K208 DAR(2,1) filter into K209/K198 reverse carry sleeve"
    elif n_crit >= 2:
        verdict = "CONDITIONAL → DAR filter shows partial improvement; conditional acceptance for K209 pilot"
    else:
        verdict = "REJECT → DAR filter does not improve K196 reverse carry sufficiently"

    print(f"  Criteria met: {n_crit}/5")
    for c, v in criteria.items():
        flag = "PASS" if v else "FAIL"
        print(f"    {c}: [{flag}]")
    print(f"\n  FINAL VERDICT: {verdict}")

    avg_filter_pct = np.mean([s.get("filter_rate_pct", 0) for s in filt_stats.values()])
    print(f"  Avg events filtered out: {avg_filter_pct:.1f}%")

    # ── 8. Build equity curves ────────────────────────────────────────────────
    print("\n=== BUILDING EQUITY CURVES ===")
    curves: Dict = {}

    # Panel-level
    if len(bl_panel) > 0:
        curves["K196_baseline"] = {
            "cumulative_pnl": equity_curve(bl_panel),
            "timestamps": [t.isoformat() for t in bl_panel.index],
            "label": "K196 Reverse Carry Baseline",
        }
    if len(filt_panel) > 0:
        curves["K208_filtered"] = {
            "cumulative_pnl": equity_curve(filt_panel),
            "timestamps": [t.isoformat() for t in filt_panel.index],
            "label": "K208 DAR(2,1) Filtered",
        }

    # Per-symbol filtered curves
    for sym, pnl in filt_per_sym.items():
        if len(pnl) > 0:
            curves[f"K208_{sym}_filtered"] = {
                "cumulative_pnl": equity_curve(pnl),
                "timestamps": [t.isoformat() for t in pnl.index],
                "label": f"K208 {sym} filtered",
            }

    print(f"  Built {len(curves)} curves")

    # ── 9. Assemble JSON output ───────────────────────────────────────────────
    runtime = round(time.time() - t0, 1)

    output = {
        "wave": "K208",
        "parent_waves": ["K190", "K196"],
        "objective": "DAR(2,1) FR predictor as entry filter for K196 reverse carry 10-symbol panel",
        "as_of": pd.Timestamp.now(tz="UTC").isoformat(),
        "runtime_s": runtime,

        "config": {
            "reverse_10": list(panels.keys()),
            "symbols_skipped": skipped,
            "dar_p": PRIMARY_P,
            "dar_q": PRIMARY_Q,
            "dar_win": PRIMARY_WIN,
            "dar_refit": PRIMARY_REFIT,
            "exogenous": "bybit_fr spread z-score",
            "filter_logic": "enter reverse carry only if predicted Bybit FR > current HL FR",
            "n_total_events_min": min(len(df) for df in panels.values()),
            "n_total_events_max": max(len(df) for df in panels.values()),
            "events_per_year": EVENTS_PER_YEAR,
            "oos_frac": OOS_FRAC,
        },

        "dar_direction_accuracy": {
            sym: {
                "direction_acc": round(d.get("direction_acc", float("nan")), 4),
                "oos_r2": round(d.get("oos_r2", float("nan")), 5),
                "n_oos": d.get("n_oos", 0),
                "passes_55pct_threshold": d.get("direction_acc", 0) >= 0.55,
            }
            for sym, d in dar_standalone_diag.items()
        },
        "n_symbols_pass_dir_acc_55pct": n_pass_dir,

        "per_symbol_comparison": per_sym_comparison,
        "filter_statistics": filt_stats,

        "baseline_reverse_panel": bl_metrics,
        "filtered_reverse_panel": filt_metrics,

        "panel_delta": {
            "oos_sharpe": round(delta_oos, 4),
            "max_dd_oos": round(filt_metrics["max_dd_oos"] - bl_metrics["max_dd_oos"], 6),
            "wf_mean": round(filt_metrics["wf_mean"] - bl_metrics["wf_mean"], 4),
            "wf_min": round(filt_metrics["wf_min"] - bl_metrics["wf_min"], 4),
            "avg_filter_pct": round(float(avg_filter_pct), 1),
        },

        "five_way_comparison": five_way,

        "s6_gates": {
            "lift_qualifies": lift_qualifies,
            "gates": gates,
            "n_pass": gates_passed,
            "verdict": gates_verdict,
        },

        "acceptance_criteria": criteria,
        "n_criteria_met": n_crit,
        "verdict": verdict,

        "k209_integration_plan": {
            "action": verdict.split("→")[1].strip() if "→" in verdict else "review",
            "implementation_steps": [
                "1. Add DAR(2,1) predictor module to ct_forward_monolith.py",
                "2. Per-symbol walk-forward refit (300-event window, refit every 50 events)",
                "3. Gate reverse carry entry: filter if pred_spread <= 0",
                "4. Test combined K198 ML allocator with K208-filtered reverse carry sleeve",
                "5. Run forward paper trading for 14 days before production deployment",
            ],
            "symbols_recommended": [
                sym for sym, d in per_sym_comparison.items()
                if d["delta_sharpe"] >= 0
            ],
            "symbols_neutral_or_negative": [
                sym for sym, d in per_sym_comparison.items()
                if d["delta_sharpe"] < 0
            ],
        },
    }

    # ── 10. Write outputs ─────────────────────────────────────────────────────
    json_path   = BASE / "wave_k208_dar_reverse_carry.json"
    curves_path = BASE / "wave_k208_curves.json"

    json_path.write_text(json.dumps(output, indent=2, default=str))
    curves_path.write_text(json.dumps(curves, default=str))

    print(f"\nWrote {json_path} ({json_path.stat().st_size:,} bytes)")
    print(f"Wrote {curves_path} ({curves_path.stat().st_size:,} bytes)")
    print(f"Total runtime: {runtime}s")
    print(f"\nVERDICT: {verdict}")

    return output


if __name__ == "__main__":
    main()

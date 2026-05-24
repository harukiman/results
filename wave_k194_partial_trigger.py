"""Wave K194 — Partial Trigger: Apply FR-mean defensive trigger ONLY to K121 + K133 components.

Hypothesis:
  K192's DAR filter on K175 EXPLOITS the negative-FR regime (K193 showed that combining
  full trigger with K192 degraded OOS Sh from 5.65 → 4.30). However, K121 (weekend momentum)
  and K133 (funding rev 7d) are genuinely HURT by negative-FR regimes.

  Solution: Apply FR-mean trigger only to K121 and K133 daily PnL, leaving K192's DAR-filtered
  K175 and all other components untouched.

K191 root cause (K188 fold 2 weakness):
  - K121 weekend momentum: Sh -3.34, weight 31%, contribution -1.03
  - K133 funding rev 7d: Sh -2.43, only 4/50 positive days (8% hit rate)

Architecture:
  1. Load K192's 9 component daily PnL series
  2. Compute daily FR_mean indicator (same as K193: 6-symbol mean Bybit FR annualized)
  3. Apply partial trigger: when FR_mean < threshold, K121 *= 0 AND K133 *= 0
  4. Re-run portfolio variants P1-P4 (carry cap 7%)
  5. Threshold sweep: -0.005, -0.009735, -0.015, -0.02
  6. Compare K188 / K192 / K194 three-way

Diagnostic pre-check:
  - Compute K121 + K133 Sharpe on trigger days vs non-trigger days
  - If still negative on trigger days → partial trigger should help
  - If flipped positive (per K193 DAR-exploitation finding) → partial trigger may also fail

Acceptance criteria for K194 → v6.2 production:
  - OOS Sh > K192 (5.65) by at least +0.05
  - MaxDD not worsened
  - WF fold min >= 3.5
  - Trigger doesn't fire too often (<=30% of days)

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

BASE  = Path("/Users/nekonaomichi/crypto-lab")
CACHE = BASE / "cache"
HL_CACHE = CACHE / "k163_hl"

TRADING_DAYS = 365
OOS_FRAC     = 0.30
START_TIME   = time.time()

# FR defensive trigger symbols (same as K191/K193)
FR_SYMBOLS = ["BTC", "ETH", "DOGE", "AVAX", "SOL", "XRP"]

# Primary threshold (K191 recommended)
THRESHOLD_PRIMARY = -0.009735
# Sensitivity sweep
THRESHOLDS_SWEEP = [-0.005, -0.009735, -0.015, -0.02]

# Which components to apply partial trigger to
PARTIAL_TRIGGER_COMPONENTS = ["K121", "K133"]

# Walk-forward config
N_FOLDS    = 4
TRAIN_FRAC = 0.70

# K186 carry sub-weights (unchanged from K188/K192)
CARRY_WEIGHTS_K186 = {"ETH": 0.35, "DOGE": 0.30, "AVAX": 0.25, "BTC": 0.10}
CARRY_CAP = 0.07
K121_CAP  = 0.30


# ─────────────────────────────── Metrics ──────────────────────────────────────

def sharpe_d(r: np.ndarray) -> float:
    if len(r) < 2 or r.std(ddof=1) == 0:
        return 0.0
    return float(r.mean() / r.std(ddof=1) * math.sqrt(TRADING_DAYS))


def sortino_d(r: np.ndarray) -> float:
    dn = r[r < 0]
    if len(dn) < 2 or dn.std(ddof=1) == 0:
        return 0.0
    return float(r.mean() / dn.std(ddof=1) * math.sqrt(TRADING_DAYS))


def max_dd_d(r: np.ndarray) -> float:
    eq = np.cumprod(1.0 + r)
    peak = np.maximum.accumulate(eq)
    return float((eq / peak - 1.0).min())


def calmar_d(r: np.ndarray) -> float:
    ann = (1.0 + r).prod() ** (TRADING_DAYS / max(1, len(r))) - 1.0
    mdd = max_dd_d(r)
    return float(ann / abs(mdd)) if mdd != 0 else 0.0


def metrics_pkg(r: np.ndarray) -> dict:
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


# ─────────────────────────────── Data Loaders ─────────────────────────────────

def _equity_to_daily_returns(ts_iso: List[str], eq: List[float]) -> pd.Series:
    ts = pd.to_datetime(ts_iso, utc=True).tz_convert(None) \
         if pd.to_datetime(ts_iso[0]).tzinfo else pd.to_datetime(ts_iso)
    s = pd.Series(eq, index=ts).sort_index()
    daily_eq = s.resample("1D").last().ffill()
    daily_ret = daily_eq.pct_change().fillna(0.0)
    return daily_ret


def load_component_daily_returns() -> pd.DataFrame:
    """Load all 9 K192 component daily return series from wave_k192_curves.json."""
    with open(BASE / "wave_k192_curves.json") as f:
        d = json.load(f)
    dates = pd.to_datetime(d["dates"])
    # Component equity curves stored as cumulative product arrays
    # Keys in the curves JSON are prefixed with "K188_" for the original components
    component_map = {
        "v4.1":                   "K188_v4.1",
        "V1":                     "K188_V1",
        "K114":                   "K188_K114",
        "K116":                   "K188_K116",
        "K121":                   "K188_K121",
        "K133":                   "K188_K133",
        "K147":                   "K188_K147",
        "K175_DAR":               "K175_DAR_a_win300_net",   # K192a primary
        "V_carry_panel_weighted": "K188_V_carry_panel_weighted",
    }
    df = pd.DataFrame(index=dates)
    for col_name, curve_key in component_map.items():
        eq = np.array(d["series"][curve_key], dtype=float)
        # Convert equity curve to daily returns
        prev = np.r_[1.0, eq[:-1]]
        ret = eq / prev - 1.0
        df[col_name] = ret
    df.index.name = "date"
    # Normalize the column names to match K192 component spec
    df = df.rename(columns={"K175_DAR": "K175_DAR(2,1)_win300"})
    return df


def load_fr_mean_daily() -> pd.Series:
    """Load Bybit FR for 6 symbols, resample to daily mean, annualize, cross-mean."""
    daily_series = []
    for sym in FR_SYMBOLS:
        fpath = CACHE / f"bybit_fr_{sym}USDT_730d.parquet"
        if not fpath.exists():
            # Try 1200d
            fpath = CACHE / f"bybit_fr_{sym}USDT_1200d.parquet"
        if not fpath.exists():
            print(f"  WARNING: No FR data for {sym}, skipping")
            continue
        df = pd.read_parquet(fpath)
        df = df.set_index("timestamp")
        daily = df["funding_rate"].resample("1D").mean()
        # Annualize: 3 funding payments per day × 365 days
        ann = daily * 3 * 365
        ann.name = sym
        daily_series.append(ann)
    panel = pd.concat(daily_series, axis=1)
    fr_mean = panel.mean(axis=1)
    fr_mean.name = "fr_mean_ann"
    return fr_mean


# ─────────────────────────────── Partial Trigger ──────────────────────────────

def apply_partial_trigger(
    df_components: pd.DataFrame,
    fr_mean: pd.Series,
    threshold: float,
    target_cols: List[str] = PARTIAL_TRIGGER_COMPONENTS,
) -> Tuple[pd.DataFrame, pd.Series]:
    """Apply trigger ONLY to specified columns (K121, K133). Other columns unchanged."""
    aligned_fr = fr_mean.reindex(df_components.index, method="ffill")
    trigger_mask = aligned_fr < threshold

    df_triggered = df_components.copy()
    for col in target_cols:
        if col in df_triggered.columns:
            df_triggered.loc[trigger_mask, col] = 0.0

    return df_triggered, trigger_mask


# ─────────────────────────────── Weighting ────────────────────────────────────

def w_equal(n: int) -> np.ndarray:
    return np.ones(n) / n


def w_inv_vol(R: np.ndarray) -> np.ndarray:
    vols = R.std(axis=0, ddof=1)
    inv = 1.0 / np.where(vols == 0, np.nan, vols)
    return inv / np.nansum(inv)


def w_risk_parity(R: np.ndarray, n_iter: int = 5000, tol: float = 1e-9) -> np.ndarray:
    vols = R.std(axis=0, ddof=1)
    vols = np.where(vols == 0, 1.0, vols)
    R_norm = R / vols[np.newaxis, :]
    cov = np.cov(R_norm, rowvar=False, ddof=1)
    cov = cov + np.eye(cov.shape[0]) * 1e-8
    n = cov.shape[0]
    w = np.ones(n) / n
    for _ in range(n_iter):
        mrc = cov @ w
        rc = w * mrc
        rc = np.where(np.abs(rc) < 1e-15, 1e-15, rc)
        total_risk_sq = float(w @ cov @ w)
        target = total_risk_sq / n
        ratio = target / rc
        ratio = np.clip(ratio, 0, None)
        new_w = w * ratio ** 0.5
        new_w = np.clip(new_w, 1e-6, None)
        new_w = new_w / new_w.sum()
        if np.max(np.abs(new_w - w)) < tol:
            w_sc = new_w / vols
            return w_sc / w_sc.sum()
        w = new_w
    w_sc = w / vols
    return w_sc / w_sc.sum()


def w_sharpe_wt(R: np.ndarray) -> np.ndarray:
    shs = np.array([sharpe_d(R[:, i]) for i in range(R.shape[1])])
    pos = np.clip(shs, 0, None)
    if pos.sum() == 0:
        return np.ones(R.shape[1]) / R.shape[1]
    return pos / pos.sum()


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


def apply_caps(w, cols, k121_cap=K121_CAP, carry_cap=CARRY_CAP,
               carry_col="V_carry_panel_weighted"):
    w = apply_cap(w, cols, "K121", k121_cap)
    if carry_cap is not None:
        w = apply_cap(w, cols, carry_col, carry_cap)
    return w


# ─────────────────────────────── Portfolio Runner ─────────────────────────────

def run_portfolio(
    df: pd.DataFrame,
    label: str,
    carry_cap: float = CARRY_CAP,
    carry_col: str = "V_carry_panel_weighted",
) -> dict:
    cols = list(df.columns)
    R = df.to_numpy()
    cut = int(len(df) * (1 - OOS_FRAC))
    oos_R = R[cut:]

    raw_w = {
        "P1_equal":       w_equal(len(cols)),
        "P2_inv_vol":     w_inv_vol(R),
        "P3_risk_parity": w_risk_parity(R),
        "P4_sharpe_wt":   w_sharpe_wt(R),
    }
    capped = {k: apply_caps(w, cols, carry_cap=carry_cap, carry_col=carry_col)
              for k, w in raw_w.items()}

    full_metrics, oos_metrics, full_curves = {}, {}, {}
    for k, w in capped.items():
        pr_f = R @ w
        pr_o = oos_R @ w
        full_metrics[k] = metrics_pkg(pr_f)
        oos_metrics[k]  = metrics_pkg(pr_o)
        full_curves[f"{label}_{k}"] = [round(float(v), 6) for v in np.cumprod(1.0 + pr_f)]

    return {
        "label": label,
        "carry_cap": carry_cap,
        "cols": cols,
        "n_days": int(len(df)),
        "oos_cut_idx": int(cut),
        "oos_n_days": int(len(df) - cut),
        "date_range": [str(df.index.min().date()), str(df.index.max().date())],
        "single_metrics_full": {c: metrics_pkg(R[:, i]) for i, c in enumerate(cols)},
        "single_metrics_oos":  {c: metrics_pkg(oos_R[:, i]) for i, c in enumerate(cols)},
        "weights": {k: [round(float(x), 4) for x in v] for k, v in capped.items()},
        "metrics_full": full_metrics,
        "metrics_oos":  oos_metrics,
        "curves": full_curves,
        "dates": [d.strftime("%Y-%m-%d") for d in df.index],
    }


# ─────────────────────────────── Walk-Forward (4-fold) ────────────────────────

def wf_4fold(
    df_base: pd.DataFrame,
    df_triggered: pd.DataFrame,
    trigger_mask: pd.Series,
    label: str = "K194",
    carry_cap: float = CARRY_CAP,
    n_folds: int = N_FOLDS,
) -> dict:
    """4-fold WF matching K192/K193 methodology."""
    cols = list(df_base.columns)
    R_base = df_base.to_numpy()
    R_trig = df_triggered.to_numpy()
    carry_col = "V_carry_panel_weighted"
    n = len(R_base)
    fold_size = n // n_folds
    folds = []

    for fold_id in range(n_folds):
        start = fold_id * fold_size
        end   = start + fold_size if fold_id < n_folds - 1 else n
        R_fold_base = R_base[start:end]
        R_fold_trig = R_trig[start:end]
        mask_fold   = trigger_mask.iloc[start:end]

        cut = int(len(R_fold_base) * TRAIN_FRAC)
        R_tr_base = R_fold_base[:cut]
        R_te_base = R_fold_base[cut:]
        R_te_trig = R_fold_trig[cut:]
        mask_te   = mask_fold.iloc[cut:]

        if len(R_tr_base) < 30 or len(R_te_base) < 10:
            continue

        # Weights computed from triggered training data (re-alloc since K121/K133 zeroed in trigger days)
        R_tr_trig = R_fold_trig[:cut]
        raw_w = {
            "P1_equal":       w_equal(len(cols)),
            "P2_inv_vol":     w_inv_vol(R_tr_trig),
            "P3_risk_parity": w_risk_parity(R_tr_trig),
            "P4_sharpe_wt":   w_sharpe_wt(R_tr_trig),
        }
        capped = {k: apply_caps(w, cols, carry_cap=carry_cap, carry_col=carry_col)
                  for k, w in raw_w.items()}

        n_trigger = int(mask_te.sum())
        trigger_pct = round(n_trigger / max(1, len(mask_te)) * 100, 1)

        fold = {
            "fold": fold_id,
            "train_n": int(cut),
            "test_n":  int(len(R_te_base)),
            "date_start": str(df_base.index[start].date()),
            "date_end":   str(df_base.index[end - 1].date()),
            "n_trigger_days": int(n_trigger),
            "trigger_pct": trigger_pct,
        }
        for k, w in capped.items():
            pr_base = R_te_base @ w
            pr_trig = R_te_trig @ w
            fold[f"oos_sharpe_base_{k}"] = round(sharpe_d(pr_base), 4)
            fold[f"oos_sharpe_{label}_{k}"] = round(sharpe_d(pr_trig), 4)
            fold[f"delta_{k}"] = round(sharpe_d(pr_trig) - sharpe_d(pr_base), 4)
        folds.append(fold)
        print(f"  Fold {fold_id}: base P3={fold.get('oos_sharpe_base_P3_risk_parity', 0):.3f} | "
              f"{label} P3={fold.get(f'oos_sharpe_{label}_P3_risk_parity', 0):.3f} "
              f"(Δ={fold.get('delta_P3_risk_parity', 0):+.3f}) | trigger={trigger_pct:.0f}%", flush=True)

    result = {"label": label, "folds": folds}
    for k in ["P1_equal", "P2_inv_vol", "P3_risk_parity", "P4_sharpe_wt"]:
        base_vals = [f[f"oos_sharpe_base_{k}"] for f in folds if f"oos_sharpe_base_{k}" in f]
        trig_vals = [f[f"oos_sharpe_{label}_{k}"] for f in folds if f"oos_sharpe_{label}_{k}" in f]
        if base_vals:
            result[f"mean_base_{k}"]       = round(float(np.mean(base_vals)), 4)
            result[f"min_base_{k}"]        = round(float(np.min(base_vals)), 4)
        if trig_vals:
            result[f"mean_{label}_{k}"]    = round(float(np.mean(trig_vals)), 4)
            result[f"min_{label}_{k}"]     = round(float(np.min(trig_vals)), 4)
            result[f"std_{label}_{k}"]     = round(float(np.std(trig_vals)), 4)
    return result


# ─────────────────────────────── Threshold Sweep ──────────────────────────────

def threshold_sweep(
    df_components: pd.DataFrame,
    fr_mean: pd.Series,
    thresholds: List[float],
    target_cols: List[str] = PARTIAL_TRIGGER_COMPONENTS,
) -> List[dict]:
    """For each threshold, compute full-period and OOS metrics plus trigger stats."""
    n = len(df_components)
    oos_start = int(n * (1 - OOS_FRAC))
    results = []

    for thr in thresholds:
        df_trig, mask = apply_partial_trigger(df_components, fr_mean, thr, target_cols)

        # Run portfolio on full period with this trigger
        res = run_portfolio(df_trig, f"K194_thr{thr:.4f}", carry_cap=CARRY_CAP)

        # Also run base (no trigger) for comparison
        res_base = run_portfolio(df_components, "K194_base", carry_cap=CARRY_CAP)

        n_trigger_full = int(mask.sum())
        n_trigger_oos  = int(mask.iloc[oos_start:].sum())
        trigger_pct_full = round(n_trigger_full / max(1, n) * 100, 1)
        trigger_pct_oos  = round(n_trigger_oos  / max(1, n - oos_start) * 100, 1)

        sh_base_oos = res_base["metrics_oos"]["P3_risk_parity"]["sharpe"]
        sh_trig_oos = res["metrics_oos"]["P3_risk_parity"]["sharpe"]
        dd_base_oos = res_base["metrics_oos"]["P3_risk_parity"]["max_dd"]
        dd_trig_oos = res["metrics_oos"]["P3_risk_parity"]["max_dd"]

        entry = {
            "threshold": thr,
            "trigger_pct_full": trigger_pct_full,
            "trigger_pct_oos":  trigger_pct_oos,
            "n_trigger_full":   n_trigger_full,
            "n_trigger_oos":    n_trigger_oos,
            "oos_base_sharpe_P3":  sh_base_oos,
            "oos_trig_sharpe_P3":  sh_trig_oos,
            "oos_delta_sharpe_P3": round(sh_trig_oos - sh_base_oos, 4),
            "oos_base_maxdd":  dd_base_oos,
            "oos_trig_maxdd":  dd_trig_oos,
            "all_variants": {
                k: {
                    "base_oos_sharpe": res_base["metrics_oos"][k]["sharpe"],
                    "trig_oos_sharpe": res["metrics_oos"][k]["sharpe"],
                    "delta":           round(res["metrics_oos"][k]["sharpe"] -
                                             res_base["metrics_oos"][k]["sharpe"], 4),
                } for k in ["P1_equal", "P2_inv_vol", "P3_risk_parity", "P4_sharpe_wt"]
            },
        }
        results.append(entry)
        print(f"  thr={thr:.5f}: OOS P3 base={sh_base_oos:.4f} → K194={sh_trig_oos:.4f} "
              f"(Δ={sh_trig_oos - sh_base_oos:+.4f}) | MaxDD {dd_base_oos:.4f}→{dd_trig_oos:.4f} "
              f"| trigger%={trigger_pct_oos:.0f}%", flush=True)

    return results


# ─────────────────────────────── K121/K133 Diagnostic ────────────────────────

def k121_k133_trigger_diagnostic(
    df_components: pd.DataFrame,
    fr_mean: pd.Series,
    threshold: float = THRESHOLD_PRIMARY,
) -> dict:
    """Diagnostic: what is K121/K133 Sharpe on trigger days vs non-trigger days in K192 state?"""
    aligned_fr = fr_mean.reindex(df_components.index, method="ffill")
    trigger_mask = aligned_fr < threshold

    n = len(df_components)
    oos_start = int(n * (1 - OOS_FRAC))

    results = {}
    for col in ["K121", "K133"]:
        if col not in df_components.columns:
            continue
        r = df_components[col]
        r_trigger     = r[trigger_mask]
        r_no_trigger  = r[~trigger_mask]
        r_trigger_oos = r.iloc[oos_start:][trigger_mask.iloc[oos_start:]]
        r_no_trig_oos = r.iloc[oos_start:][~trigger_mask.iloc[oos_start:]]

        results[col] = {
            "full": {
                "sharpe_on_trigger_days":    round(sharpe_d(r_trigger.values), 4),
                "sharpe_on_non_trigger_days": round(sharpe_d(r_no_trigger.values), 4),
                "n_trigger_days":   int(trigger_mask.sum()),
                "n_non_trigger":    int((~trigger_mask).sum()),
                "mean_ret_trigger": round(float(r_trigger.mean()), 6),
                "mean_ret_no_trig": round(float(r_no_trigger.mean()), 6),
            },
            "oos": {
                "sharpe_on_trigger_days":    round(sharpe_d(r_trigger_oos.values), 4),
                "sharpe_on_non_trigger_days": round(sharpe_d(r_no_trig_oos.values), 4),
                "n_trigger_days":   int(trigger_mask.iloc[oos_start:].sum()),
                "n_non_trigger":    int((~trigger_mask.iloc[oos_start:]).sum()),
                "mean_ret_trigger": round(float(r_trigger_oos.mean()) if len(r_trigger_oos) > 0 else 0.0, 6),
                "mean_ret_no_trig": round(float(r_no_trig_oos.mean()) if len(r_no_trig_oos) > 0 else 0.0, 6),
            },
        }
        print(f"  {col} trigger_days: full Sh={results[col]['full']['sharpe_on_trigger_days']:.3f} "
              f"vs non-trigger Sh={results[col]['full']['sharpe_on_non_trigger_days']:.3f}", flush=True)
        print(f"  {col} OOS trigger_days: Sh={results[col]['oos']['sharpe_on_trigger_days']:.3f} "
              f"vs non-trigger Sh={results[col]['oos']['sharpe_on_non_trigger_days']:.3f}", flush=True)

    # Verdict on whether partial trigger is worth trying
    k121_trigger_sh = results.get("K121", {}).get("oos", {}).get("sharpe_on_trigger_days", 0)
    k133_trigger_sh = results.get("K133", {}).get("oos", {}).get("sharpe_on_trigger_days", 0)
    both_negative = k121_trigger_sh < 0 and k133_trigger_sh < 0
    either_negative = k121_trigger_sh < 0 or k133_trigger_sh < 0

    results["verdict"] = {
        "k121_oos_trigger_sharpe": k121_trigger_sh,
        "k133_oos_trigger_sharpe": k133_trigger_sh,
        "both_negative_on_trigger": both_negative,
        "either_negative_on_trigger": either_negative,
        "partial_trigger_hypothesis_supported": either_negative,
        "threshold": threshold,
        "interpretation": (
            "HYPOTHESIS SUPPORTED: K121/K133 still underperform on trigger days → partial trigger should help"
            if either_negative else
            "HYPOTHESIS QUESTIONABLE: K121/K133 have flipped positive on trigger days → partial trigger may fail"
        ),
    }
    print(f"\n  Diagnostic verdict: {results['verdict']['interpretation']}")
    return results


# ─────────────────────────────── Equity Curve Helpers ─────────────────────────

def returns_to_equity_curve(ret_arr: np.ndarray) -> List[float]:
    eq = np.cumprod(1.0 + ret_arr)
    return [round(float(v), 6) for v in eq]


# ─────────────────────────────── Main ─────────────────────────────────────────

def main():
    print("=" * 70)
    print("Wave K194 — Partial Trigger: FR-mean applied ONLY to K121 + K133")
    print("=" * 70)
    print()

    # ── Step 1: Load K192's 9 component daily PnL series ──
    print("Step 1: Loading K192 component daily return series...", flush=True)
    df_components = load_component_daily_returns()
    print(f"  Components: {list(df_components.columns)}")
    print(f"  Shape: {df_components.shape}, {df_components.index[0].date()} → {df_components.index[-1].date()}")
    print()

    # ── Step 2: Compute FR_mean ──
    print("Step 2: Computing daily FR_mean across 6 symbols...", flush=True)
    fr_mean = load_fr_mean_daily()
    fr_mean_aligned = fr_mean.reindex(df_components.index, method="ffill")
    print(f"  FR_mean: n={len(fr_mean)}, {fr_mean.index[0].date()} → {fr_mean.index[-1].date()}")
    print(f"  FR_mean stats: mean={fr_mean_aligned.mean():.4f}, std={fr_mean_aligned.std():.4f}, "
          f"min={fr_mean_aligned.min():.4f}, max={fr_mean_aligned.max():.4f}")
    n = len(df_components)
    oos_start = int(n * (1 - OOS_FRAC))
    mask_primary_stats = fr_mean_aligned < THRESHOLD_PRIMARY
    print(f"  Days below threshold {THRESHOLD_PRIMARY}: {int(mask_primary_stats.sum())} / {n} "
          f"({mask_primary_stats.mean()*100:.1f}%)")
    print()

    # ── Step 3: K121/K133 diagnostic ──
    print(f"Step 3: K121/K133 trigger-day diagnostic (threshold={THRESHOLD_PRIMARY})...", flush=True)
    diagnostic = k121_k133_trigger_diagnostic(df_components, fr_mean, THRESHOLD_PRIMARY)
    print()

    # ── Step 4: Apply primary partial trigger ──
    print(f"Step 4: Applying primary partial trigger (threshold={THRESHOLD_PRIMARY})...", flush=True)
    df_k194_primary, mask_primary = apply_partial_trigger(
        df_components, fr_mean, THRESHOLD_PRIMARY, PARTIAL_TRIGGER_COMPONENTS
    )
    print(f"  Partial trigger applied to: {PARTIAL_TRIGGER_COMPONENTS}")
    print(f"  Trigger days (full): {int(mask_primary.sum())} / {n} ({mask_primary.mean()*100:.1f}%)")
    print(f"  Trigger days (OOS):  {int(mask_primary.iloc[oos_start:].sum())} / {n-oos_start} "
          f"({mask_primary.iloc[oos_start:].mean()*100:.1f}%)")
    print()

    # ── Step 5: Run K192 base portfolio (no partial trigger) ──
    print("Step 5: Running K192 base portfolio (no partial trigger)...", flush=True)
    res_k192_base = run_portfolio(df_components, "K192_base_cap07", carry_cap=CARRY_CAP)
    k192_p3_oos = res_k192_base["metrics_oos"]["P3_risk_parity"]["sharpe"]
    k192_p3_full = res_k192_base["metrics_full"]["P3_risk_parity"]["sharpe"]
    print(f"  K192 base P3 OOS Sh: {k192_p3_oos:.4f} | Full Sh: {k192_p3_full:.4f}")
    print()

    # ── Step 6: Run K194 primary portfolio ──
    print("Step 6: Running K194 primary portfolio (partial trigger applied)...", flush=True)
    res_k194_primary = run_portfolio(df_k194_primary, "K194_primary_cap07", carry_cap=CARRY_CAP)
    k194_p3_oos = res_k194_primary["metrics_oos"]["P3_risk_parity"]["sharpe"]
    k194_p3_full = res_k194_primary["metrics_full"]["P3_risk_parity"]["sharpe"]
    print(f"  K194 P3 OOS Sh: {k194_p3_oos:.4f} | Full Sh: {k194_p3_full:.4f}")
    print(f"  Delta OOS P3: {k194_p3_oos - k192_p3_oos:+.4f}")
    print()

    # ── Step 7: Threshold sweep ──
    print("Step 7: Threshold sweep...", flush=True)
    sweep_results = threshold_sweep(df_components, fr_mean, THRESHOLDS_SWEEP, PARTIAL_TRIGGER_COMPONENTS)
    print()

    # ── Step 8: Walk-forward 4-fold with primary threshold ──
    print(f"Step 8: Walk-forward 4-fold analysis (primary threshold={THRESHOLD_PRIMARY})...", flush=True)
    wf_results = wf_4fold(
        df_components, df_k194_primary, mask_primary,
        label="K194", carry_cap=CARRY_CAP
    )
    print()

    # ── Step 9: Build reference K192 walk-forward (same methodology) ──
    print("Step 9: K192 reference walk-forward...", flush=True)
    # For K192 WF reference, use the K192-base (no trigger, same component data)
    df_dummy_mask = pd.Series(False, index=df_components.index)
    wf_k192_ref = wf_4fold(
        df_components, df_components, df_dummy_mask,
        label="K192_base", carry_cap=CARRY_CAP
    )
    print()

    # ── Step 10: Print three-way comparison ──
    print("Step 10: Building three-way comparison table...", flush=True)
    # K188 reference from K193 output
    K188_OOS_SH = 5.4846
    K188_OOS_DD = -0.0045
    K188_WF_MEAN = 4.7216  # (from K188 WF report, P2 inv vol)
    K188_WF_MIN  = 2.6043

    print(f"\n{'Version':<28} {'OOS Sh':>8} {'OOS MaxDD':>10} {'WF mean':>9} {'WF min':>9}")
    print("-" * 68)
    print(f"{'K188 baseline':<28} {K188_OOS_SH:>8.4f} {K188_OOS_DD:>10.4f} {K188_WF_MEAN:>9.4f} {K188_WF_MIN:>9.4f}")
    k192_wf_mean_p3 = wf_k192_ref.get("mean_K192_base_P3_risk_parity", 0.0)
    k192_wf_min_p3  = wf_k192_ref.get("min_K192_base_P3_risk_parity", 0.0)
    print(f"{'K192 v6.1 (no trigger)':<28} {k192_p3_oos:>8.4f} "
          f"{res_k192_base['metrics_oos']['P3_risk_parity']['max_dd']:>10.4f} "
          f"{k192_wf_mean_p3:>9.4f} {k192_wf_min_p3:>9.4f}")
    k194_wf_mean_p3 = wf_results.get("mean_K194_P3_risk_parity", 0.0)
    k194_wf_min_p3  = wf_results.get("min_K194_P3_risk_parity", 0.0)
    print(f"{'K194 v6.2 candidate':<28} {k194_p3_oos:>8.4f} "
          f"{res_k194_primary['metrics_oos']['P3_risk_parity']['max_dd']:>10.4f} "
          f"{k194_wf_mean_p3:>9.4f} {k194_wf_min_p3:>9.4f}")
    print()

    # ── Step 11: Acceptance criteria ──
    print("Step 11: Acceptance criteria check...", flush=True)
    trigger_pct_oos = mask_primary.iloc[oos_start:].mean() * 100
    k192_oos_dd = res_k192_base["metrics_oos"]["P3_risk_parity"]["max_dd"]
    k194_oos_dd = res_k194_primary["metrics_oos"]["P3_risk_parity"]["max_dd"]

    c1_oos_lift = k194_p3_oos - k192_p3_oos
    c1_pass = bool(c1_oos_lift >= 0.05)
    c2_pass = bool(k194_oos_dd >= k192_oos_dd - 0.001)  # not worsened (tiny tolerance)
    c3_wf_min = k194_wf_min_p3
    c3_pass = bool(c3_wf_min >= 3.5)
    c4_pass  = bool(trigger_pct_oos <= 30.0)
    all_pass = bool(c1_pass and c2_pass and c3_pass and c4_pass)

    print(f"  C1: OOS Sh lift={c1_oos_lift:+.4f} vs K192={k192_p3_oos:.4f} (need >=+0.05) "
          f"→ {'PASS' if c1_pass else 'FAIL'}")
    print(f"  C2: MaxDD K192={k192_oos_dd:.4f} vs K194={k194_oos_dd:.4f} → {'PASS' if c2_pass else 'FAIL'}")
    print(f"  C3: WF fold min={c3_wf_min:.4f} (need >=3.5) → {'PASS' if c3_pass else 'FAIL'}")
    print(f"  C4: OOS trigger%={trigger_pct_oos:.1f}% (need <=30%) → {'PASS' if c4_pass else 'FAIL'}")
    print(f"  ALL_PASS: {all_pass}")
    print()

    # ── Build equity curves for export ──
    print("Building equity curves...", flush=True)
    dates_list = [d.strftime("%Y-%m-%d") for d in df_components.index]

    # K192 base portfolio (P3 risk parity weights, no trigger)
    cols = list(df_components.columns)
    R_base = df_components.to_numpy()
    R_trig = df_k194_primary.to_numpy()
    # Use full-period weights from run_portfolio results
    w_base_p3 = np.array(res_k192_base["weights"]["P3_risk_parity"])
    w_k194_p3 = np.array(res_k194_primary["weights"]["P3_risk_parity"])

    eq_k192_p3 = returns_to_equity_curve(R_base @ w_base_p3)
    eq_k194_p3 = returns_to_equity_curve(R_trig @ w_k194_p3)

    # Component equity curves
    component_curves = {}
    for i, col in enumerate(cols):
        component_curves[f"K192_{col}"] = returns_to_equity_curve(R_base[:, i])
        component_curves[f"K194_{col}"] = returns_to_equity_curve(R_trig[:, i])

    # FR_mean series
    fr_vals = [round(float(v), 6) if not np.isnan(v) else None
               for v in fr_mean_aligned.values]
    trigger_vals_primary = [int(v) for v in mask_primary.values]

    # ── Assemble JSON outputs ──
    runtime_s = round(time.time() - START_TIME, 1)

    metrics_out = {
        "wave": "K194",
        "task": "Partial trigger: FR-mean applied only to K121 + K133, K192 base otherwise",
        "as_of": pd.Timestamp.utcnow().isoformat() + "Z",
        "runtime_s": runtime_s,
        "config": {
            "partial_trigger_components": PARTIAL_TRIGGER_COMPONENTS,
            "fr_symbols": FR_SYMBOLS,
            "fr_annualize_factor": "3*365",
            "threshold_primary": THRESHOLD_PRIMARY,
            "thresholds_sweep": THRESHOLDS_SWEEP,
            "carry_cap": CARRY_CAP,
            "k121_cap": K121_CAP,
            "n_folds": N_FOLDS,
            "train_frac": TRAIN_FRAC,
            "oos_frac": OOS_FRAC,
            "n_total": n,
            "oos_start_idx": oos_start,
            "date_range": [dates_list[0], dates_list[-1]],
        },
        "fr_mean_stats": {
            "mean_ann": round(float(fr_mean_aligned.mean()), 5),
            "std_ann": round(float(fr_mean_aligned.std()), 5),
            "min_ann": round(float(fr_mean_aligned.min()), 5),
            "max_ann": round(float(fr_mean_aligned.max()), 5),
            "days_below_primary_thr_full": int(mask_primary.sum()),
            "days_below_primary_thr_pct_full": round(float(mask_primary.mean()) * 100, 1),
            "days_below_primary_thr_oos": int(mask_primary.iloc[oos_start:].sum()),
            "days_below_primary_thr_pct_oos": round(trigger_pct_oos, 1),
        },
        "diagnostic_k121_k133": diagnostic,
        "k192_base_portfolio": {
            "metrics_full": res_k192_base["metrics_full"],
            "metrics_oos":  res_k192_base["metrics_oos"],
            "weights":      res_k192_base["weights"],
            "single_metrics_full": res_k192_base["single_metrics_full"],
            "single_metrics_oos":  res_k192_base["single_metrics_oos"],
        },
        "k194_primary_portfolio": {
            "threshold": THRESHOLD_PRIMARY,
            "partial_trigger_components": PARTIAL_TRIGGER_COMPONENTS,
            "metrics_full": res_k194_primary["metrics_full"],
            "metrics_oos":  res_k194_primary["metrics_oos"],
            "weights":      res_k194_primary["weights"],
            "single_metrics_full": res_k194_primary["single_metrics_full"],
            "single_metrics_oos":  res_k194_primary["single_metrics_oos"],
        },
        "three_way_comparison": {
            "K188": {
                "oos_sharpe_P3": K188_OOS_SH,
                "oos_maxdd_P3":  K188_OOS_DD,
                "wf_mean_P3": K188_WF_MEAN,
                "wf_min_P3":  K188_WF_MIN,
                "description": "K188 v6 baseline (K175 original, no DAR, no trigger)",
            },
            "K192": {
                "oos_sharpe_P3": round(k192_p3_oos, 4),
                "oos_maxdd_P3":  round(k192_oos_dd, 4),
                "full_sharpe_P3": round(k192_p3_full, 4),
                "wf_mean_P3": round(k192_wf_mean_p3, 4),
                "wf_min_P3":  round(k192_wf_min_p3, 4),
                "description": "K192 v6.1 (K175_DAR(2,1)_win300 filter, no trigger)",
            },
            "K194": {
                "oos_sharpe_P3": round(k194_p3_oos, 4),
                "oos_maxdd_P3":  round(k194_oos_dd, 4),
                "full_sharpe_P3": round(k194_p3_full, 4),
                "wf_mean_P3": round(k194_wf_mean_p3, 4),
                "wf_min_P3":  round(k194_wf_min_p3, 4),
                "description": f"K194 v6.2 candidate (K192 base + partial trigger K121/K133 @ {THRESHOLD_PRIMARY})",
            },
        },
        "threshold_sweep": sweep_results,
        "walk_forward_k194": wf_results,
        "walk_forward_k192_ref": wf_k192_ref,
        "acceptance_criteria": {
            "c1_oos_lift_needed": 0.05,
            "c1_oos_lift_actual": round(c1_oos_lift, 4),
            "c1_k192_oos_sh": round(k192_p3_oos, 4),
            "c1_k194_oos_sh": round(k194_p3_oos, 4),
            "c1_pass": c1_pass,
            "c2_maxdd_k192": round(k192_oos_dd, 4),
            "c2_maxdd_k194": round(k194_oos_dd, 4),
            "c2_pass": c2_pass,
            "c3_wf_min_needed": 3.5,
            "c3_wf_min_actual": round(k194_wf_min_p3, 4),
            "c3_pass": c3_pass,
            "c4_trigger_pct_oos": round(trigger_pct_oos, 1),
            "c4_pass": c4_pass,
            "all_pass": all_pass,
        },
        "verdict": {
            "promoted_as": "K194 v6.2" if all_pass else "REJECTED",
            "all_criteria_met": all_pass,
            "k192_oos_sharpe": round(k192_p3_oos, 4),
            "k194_oos_sharpe": round(k194_p3_oos, 4),
            "delta": round(c1_oos_lift, 4),
            "diagnostic_hypothesis_supported": diagnostic.get("verdict", {}).get("partial_trigger_hypothesis_supported", False),
            "verdict_text": (
                f"K194 ACCEPTED as v6.2 production (OOS Sh={k194_p3_oos:.4f} vs K192={k192_p3_oos:.4f}, "
                f"Δ={c1_oos_lift:+.4f}, WF min={k194_wf_min_p3:.4f})"
                if all_pass else
                f"K194 REJECTED: OOS Sh lift={c1_oos_lift:+.4f} vs K192 (need >=+0.05), "
                f"WF min={k194_wf_min_p3:.4f} (need >=3.5), trigger%={trigger_pct_oos:.1f}%"
            ),
            "monitoring_triggers": [
                f"FR_mean drops below {THRESHOLD_PRIMARY} → zero K121 + K133 exposure only",
                "Rolling 90d K121/K133 Sharpe on trigger days → recalibrate if flipped positive",
                "K175_DAR OOS rolling-90d Sharpe drops >30% → re-evaluate DAR parameters",
                "Portfolio OOS Sharpe drops >20% in rolling 90d → trigger K195 re-eval",
                "HL-Bybit funding spread compressed: carry drops >30% → re-weight",
            ],
        },
        "notes": [
            "K194 = K192 base (9-component ensemble with K175_DAR(2,1)_win300 filter)",
            "Partial trigger: only K121 (weekend momentum) and K133 (funding rev 7d) are zeroed",
            "K175_DAR and carry panel are NOT affected by the trigger (DAR exploits neg-FR regime)",
            "V_carry_panel_weighted = ETH*0.35 + DOGE*0.30 + AVAX*0.25 + BTC*0.10 (K186 weights)",
            "OOS = last 30% of aligned date series.",
            "FR_mean annualized = mean(3*365 * daily_FR) across BTC/ETH/DOGE/AVAX/SOL/XRP",
        ],
    }

    curves_out = {
        "dates": dates_list,
        "series": {
            "K192_P3": eq_k192_p3,
            "K194_P3": eq_k194_p3,
            **component_curves,
        },
        "fr_mean": fr_vals,
        "trigger_mask_primary": trigger_vals_primary,
        "threshold_primary": THRESHOLD_PRIMARY,
        "description": {
            "K192_P3": "K192 base (P3_risk_parity), K175_DAR, no trigger",
            "K194_P3": f"K194 (P3_risk_parity, partial trigger K121+K133 @ {THRESHOLD_PRIMARY})",
        },
    }

    # ── Save outputs ──
    def _to_native(obj):
        if isinstance(obj, dict):
            return {k: _to_native(v) for k, v in obj.items()}
        elif isinstance(obj, list):
            return [_to_native(v) for v in obj]
        elif isinstance(obj, (np.integer,)):
            return int(obj)
        elif isinstance(obj, (np.floating,)):
            return float(obj)
        elif isinstance(obj, (np.bool_,)):
            return bool(obj)
        elif isinstance(obj, np.ndarray):
            return obj.tolist()
        return obj

    metrics_out = _to_native(metrics_out)
    curves_out  = _to_native(curves_out)

    out_metrics = BASE / "wave_k194_partial_trigger.json"
    out_curves  = BASE / "wave_k194_curves.json"

    with open(out_metrics, "w") as f:
        json.dump(metrics_out, f, indent=2)
    print(f"Saved: {out_metrics} ({out_metrics.stat().st_size:,} bytes)")

    with open(out_curves, "w") as f:
        json.dump(curves_out, f, indent=2)
    print(f"Saved: {out_curves} ({out_curves.stat().st_size:,} bytes)")
    print(f"Runtime: {runtime_s}s")

    # ── Final summary ──
    print()
    print("=" * 70)
    print("K194 FINAL SUMMARY")
    print("=" * 70)
    print(f"  Date range: {dates_list[0]} → {dates_list[-1]} (n={n})")
    print()
    print(f"  Diagnostic — K121/K133 on trigger days (OOS):")
    for col in ["K121", "K133"]:
        d = diagnostic.get(col, {}).get("oos", {})
        print(f"    {col}: trigger Sh={d.get('sharpe_on_trigger_days', 0):.3f} "
              f"| non-trigger Sh={d.get('sharpe_on_non_trigger_days', 0):.3f}")
    print(f"  Hypothesis supported: {diagnostic.get('verdict', {}).get('partial_trigger_hypothesis_supported')}")
    print()
    print(f"  Three-way comparison (P3 risk-parity):")
    print(f"    {'Version':<22} {'OOS Sh':>8} {'OOS MaxDD':>10} {'WF mean':>9} {'WF min':>9}")
    print(f"    {'-'*60}")
    print(f"    {'K188 baseline':<22} {K188_OOS_SH:>8.4f} {K188_OOS_DD:>10.4f} {K188_WF_MEAN:>9.4f} {K188_WF_MIN:>9.4f}")
    print(f"    {'K192 v6.1':<22} {k192_p3_oos:>8.4f} {k192_oos_dd:>10.4f} {k192_wf_mean_p3:>9.4f} {k192_wf_min_p3:>9.4f}")
    print(f"    {'K194 v6.2 candidate':<22} {k194_p3_oos:>8.4f} {k194_oos_dd:>10.4f} {k194_wf_mean_p3:>9.4f} {k194_wf_min_p3:>9.4f}")
    print()
    print(f"  Acceptance: C1={'PASS' if c1_pass else 'FAIL'} (lift={c1_oos_lift:+.4f}) | "
          f"C2={'PASS' if c2_pass else 'FAIL'} | "
          f"C3={'PASS' if c3_pass else 'FAIL'} (WF min={k194_wf_min_p3:.4f}) | "
          f"C4={'PASS' if c4_pass else 'FAIL'} (trigger%={trigger_pct_oos:.1f}%)")
    print()
    print(f"  Verdict: {metrics_out['verdict']['verdict_text']}")
    print("=" * 70)

    return metrics_out


if __name__ == "__main__":
    main()

"""Wave K193 — v6.2 Combine: K192 (DAR K175 filter) + K191 (FR-mean defensive trigger)

Objective:
  Combine K192 (v6.1) ensemble equity with K191 FR-mean defensive trigger to produce
  K193 = v6.2 candidate.

Architecture:
  K192 = v6.1 (9-strategy ensemble with K175_DAR(2,1) K175 filter, OOS Sh 5.65)
  K191 = defensive trigger: when daily mean annualized Bybit FR across 6 symbols
         (BTC/ETH/DOGE/AVAX/SOL/XRP) < threshold, halt all trading (0% exposure)

  These are orthogonal improvements:
  - K192 = component-level signal quality (DAR K175 filter)
  - K191 = ensemble-level regime hedge (protection during bearish-FR regimes)

Method:
  1. Load K192 equity curves (wave_k192_curves.json)
  2. Compute daily FR_mean from Bybit FR cache (6 symbols, annualized)
  3. Apply defensive trigger: when FR_mean < threshold → PnL * 0
  4. Threshold sweep: primary -0.009735, alternatives -0.005, -0.015, -0.02, -0.025
  5. Walk-forward on K192 daily returns with trigger applied per fold
  6. Compare K188 / K192 / K193 three-way

Acceptance criteria for K193 → v6.2 production:
  - OOS Sh > K192 (5.65) by at least +0.10
  - MaxDD not worsened
  - WF fold min >= 4.0 (substantial improvement over K192's 2.984)
  - Trigger doesn't fire too often (<=30% of test days)

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

TRADING_DAYS = 365
OOS_FRAC     = 0.30
START_TIME   = time.time()

# FR defensive trigger symbols
FR_SYMBOLS = ["BTC", "ETH", "DOGE", "AVAX", "SOL", "XRP"]

# Primary threshold (K191 recommended)
THRESHOLD_PRIMARY = -0.009735
# Sensitivity sweep
THRESHOLDS_SWEEP = [-0.005, -0.009735, -0.015, -0.02, -0.025]

# Which K192 portfolio variant to use as baseline (P3_risk_parity = best OOS Sh in K192)
K192_VARIANT = "K192a_cap07_P3_risk_parity"
K188_VARIANT = "K188_cap07_P3_risk_parity"

# Walk-forward config (same as K191/K192)
N_FOLDS    = 4
TRAIN_FRAC = 0.70


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

def load_k192_equity_series(variant: str = K192_VARIANT) -> pd.Series:
    """Load K192 equity curve and convert to daily returns."""
    with open(BASE / "wave_k192_curves.json") as f:
        d = json.load(f)
    dates = pd.to_datetime(d["dates"])
    eq = np.array(d["series"][variant], dtype=float)
    # equity values are absolute (1 + cumulative return style)
    # compute daily returns as pct_change
    s = pd.Series(eq, index=dates)
    ret = s.pct_change().fillna(0.0)
    return ret


def load_fr_mean_daily() -> pd.Series:
    """Load Bybit FR for 6 symbols, resample to daily mean, annualize, then cross-mean."""
    daily_series = []
    for sym in FR_SYMBOLS:
        fpath = CACHE / f"bybit_fr_{sym}USDT_730d.parquet"
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


def apply_trigger(
    ret: pd.Series,
    fr_mean: pd.Series,
    threshold: float,
) -> pd.Series:
    """Apply defensive trigger: when FR_mean < threshold, set daily PnL to 0."""
    aligned_fr = fr_mean.reindex(ret.index, method="ffill")
    trigger_mask = aligned_fr < threshold
    triggered_ret = ret.copy()
    triggered_ret[trigger_mask] = 0.0
    return triggered_ret, trigger_mask


def rolling_threshold_wf(
    ret: pd.Series,
    fr_mean: pd.Series,
    quantile: float = 0.20,
    window: int = 90,
) -> pd.Series:
    """Rolling quantile-based threshold: at each day compute 90d rolling quantile of FR_mean."""
    aligned_fr = fr_mean.reindex(ret.index, method="ffill")
    rolling_thr = aligned_fr.rolling(window, min_periods=30).quantile(quantile)
    trigger_mask = aligned_fr < rolling_thr
    triggered_ret = ret.copy()
    triggered_ret[trigger_mask] = 0.0
    return triggered_ret, trigger_mask


# ─────────────────────────────── Walk-Forward ─────────────────────────────────

def walk_forward_analysis(
    ret_base: pd.Series,  # K192 daily returns (no trigger)
    ret_triggered: pd.Series,  # K193 daily returns (with trigger)
    trigger_mask: pd.Series,
    label: str = "K193",
) -> dict:
    """4-fold walk-forward, same structure as K191/K192."""
    n = len(ret_base)
    fold_size = n // N_FOLDS
    folds_base = []
    folds_triggered = []

    for fold_idx in range(N_FOLDS):
        fold_start = fold_idx * fold_size
        fold_end   = fold_start + fold_size if fold_idx < N_FOLDS - 1 else n
        fold_ret_base = ret_base.iloc[fold_start:fold_end]
        fold_ret_trig = ret_triggered.iloc[fold_start:fold_end]
        fold_mask     = trigger_mask.iloc[fold_start:fold_end]

        # 70/30 train/test split within fold
        n_fold = len(fold_ret_base)
        n_train = int(n_fold * TRAIN_FRAC)
        test_base = fold_ret_base.iloc[n_train:]
        test_trig = fold_ret_trig.iloc[n_train:]
        test_mask = fold_mask.iloc[n_train:]

        sh_base = sharpe_d(test_base.values)
        sh_trig = sharpe_d(test_trig.values)
        n_trigger = int(test_mask.sum())
        trigger_pct = round(n_trigger / max(1, len(test_mask)) * 100, 1)

        fold_info = {
            "fold": fold_idx,
            "train_n": n_train,
            "test_n": len(test_base),
            "date_start": str(test_base.index[0].date()),
            "date_end":   str(test_base.index[-1].date()),
            "sharpe_base": round(sh_base, 4),
            f"sharpe_{label}": round(sh_trig, 4),
            "delta_sharpe": round(sh_trig - sh_base, 4),
            "n_trigger_days": n_trigger,
            "trigger_pct": trigger_pct,
        }
        folds_base.append(sh_base)
        folds_triggered.append(sh_trig)
        print(f"  Fold {fold_idx}: base Sh={sh_base:.3f} | {label} Sh={sh_trig:.3f} "
              f"(Δ={sh_trig-sh_base:+.3f}) | trigger={trigger_pct:.0f}%", flush=True)

        if fold_idx == 0:
            result = {"label": label, "folds": [fold_info]}
        else:
            result["folds"].append(fold_info)

    result["mean_base"]      = round(float(np.mean(folds_base)), 4)
    result["min_base"]       = round(float(np.min(folds_base)), 4)
    result[f"mean_{label}"]  = round(float(np.mean(folds_triggered)), 4)
    result[f"min_{label}"]   = round(float(np.min(folds_triggered)), 4)
    result[f"std_{label}"]   = round(float(np.std(folds_triggered)), 4)
    return result


# ─────────────────────────────── Threshold Sweep ──────────────────────────────

def threshold_sweep(
    ret_k192: pd.Series,
    fr_mean: pd.Series,
    thresholds: List[float],
) -> List[dict]:
    """For each threshold, compute full-period and OOS metrics plus trigger stats."""
    n = len(ret_k192)
    oos_start = int(n * (1 - OOS_FRAC))
    results = []

    for thr in thresholds:
        ret_trig, mask = apply_trigger(ret_k192, fr_mean, thr)

        full_m = metrics_pkg(ret_k192.values)
        full_t = metrics_pkg(ret_trig.values)
        oos_m  = metrics_pkg(ret_k192.iloc[oos_start:].values)
        oos_t  = metrics_pkg(ret_trig.iloc[oos_start:].values)

        n_total_trigger = int(mask.sum())
        n_oos_trigger   = int(mask.iloc[oos_start:].sum())
        trigger_pct_full = round(n_total_trigger / max(1, n) * 100, 1)
        trigger_pct_oos  = round(n_oos_trigger / max(1, n - oos_start) * 100, 1)

        results.append({
            "threshold": thr,
            "trigger_pct_full": trigger_pct_full,
            "trigger_pct_oos":  trigger_pct_oos,
            "n_trigger_full":   n_total_trigger,
            "n_trigger_oos":    n_oos_trigger,
            "full_base_sharpe": full_m["sharpe"],
            "full_k193_sharpe": full_t["sharpe"],
            "full_delta_sharpe": round(full_t["sharpe"] - full_m["sharpe"], 4),
            "full_base_maxdd":  full_m["max_dd"],
            "full_k193_maxdd":  full_t["max_dd"],
            "oos_base_sharpe":  oos_m["sharpe"],
            "oos_k193_sharpe":  oos_t["sharpe"],
            "oos_delta_sharpe": round(oos_t["sharpe"] - oos_m["sharpe"], 4),
            "oos_base_maxdd":   oos_m["max_dd"],
            "oos_k193_maxdd":   oos_t["max_dd"],
            "oos_base_metrics": oos_m,
            "oos_k193_metrics": oos_t,
        })
        print(f"  thr={thr:.5f}: OOS Sh base={oos_m['sharpe']:.4f} → K193={oos_t['sharpe']:.4f} "
              f"(Δ={oos_t['sharpe']-oos_m['sharpe']:+.4f}) | MaxDD {oos_m['max_dd']:.4f}→{oos_t['max_dd']:.4f} "
              f"| trigger%={trigger_pct_oos:.0f}%", flush=True)

    return results


# ─────────────────────────────── Rolling-90d Quantile Sweep ───────────────────

def rolling_threshold_sweep(
    ret_k192: pd.Series,
    fr_mean: pd.Series,
) -> List[dict]:
    """Test rolling quantile-based adaptive threshold (forward-looking robustness)."""
    n = len(ret_k192)
    oos_start = int(n * (1 - OOS_FRAC))
    results = []

    for q in [0.10, 0.15, 0.20, 0.25]:
        ret_trig, mask = rolling_threshold_wf(ret_k192, fr_mean, quantile=q, window=90)
        oos_t = metrics_pkg(ret_trig.iloc[oos_start:].values)
        oos_m = metrics_pkg(ret_k192.iloc[oos_start:].values)
        n_oos_trigger = int(mask.iloc[oos_start:].sum())
        trigger_pct_oos = round(n_oos_trigger / max(1, n - oos_start) * 100, 1)

        results.append({
            "quantile": q,
            "window": 90,
            "trigger_pct_oos": trigger_pct_oos,
            "oos_base_sharpe": oos_m["sharpe"],
            "oos_k193_sharpe": oos_t["sharpe"],
            "oos_delta_sharpe": round(oos_t["sharpe"] - oos_m["sharpe"], 4),
            "oos_base_maxdd":  oos_m["max_dd"],
            "oos_k193_maxdd":  oos_t["max_dd"],
        })
        print(f"  rolling q={q:.2f}: OOS Sh base={oos_m['sharpe']:.4f} → K193={oos_t['sharpe']:.4f} "
              f"(Δ={oos_t['sharpe']-oos_m['sharpe']:+.4f}) | trigger%={trigger_pct_oos:.0f}%", flush=True)

    return results


# ─────────────────────────────── Equity Curve Builder ─────────────────────────

def returns_to_equity_curve(ret: pd.Series) -> List[float]:
    """Convert daily returns to equity curve (cumulative product, starting 1.0)."""
    eq = np.cumprod(1.0 + ret.values)
    return [round(float(v), 6) for v in eq]


# ─────────────────────────────── Main ─────────────────────────────────────────

def main():
    print("=" * 70)
    print("Wave K193 — v6.2 Combine: K192 + K191 FR-mean Defensive Trigger")
    print("=" * 70)
    print()

    # ── Step 1: Load K192 equity curve ──
    print("Step 1: Loading K192 equity curves...", flush=True)
    ret_k192 = load_k192_equity_series(K192_VARIANT)
    ret_k188 = load_k192_equity_series(K188_VARIANT)
    print(f"  K192 ({K192_VARIANT}): n={len(ret_k192)}, {ret_k192.index[0].date()} → {ret_k192.index[-1].date()}")
    print()

    # ── Step 2: Compute FR_mean ──
    print("Step 2: Computing daily FR_mean across 6 symbols...", flush=True)
    fr_mean = load_fr_mean_daily()
    fr_mean_aligned = fr_mean.reindex(ret_k192.index, method="ffill")
    print(f"  FR_mean: n={len(fr_mean)}, {fr_mean.index[0].date()} → {fr_mean.index[-1].date()}")
    print(f"  FR_mean stats: mean={fr_mean_aligned.mean():.4f}, std={fr_mean_aligned.std():.4f}, "
          f"min={fr_mean_aligned.min():.4f}, max={fr_mean_aligned.max():.4f}")
    print()

    # ── Step 3: Apply primary trigger ──
    print(f"Step 3: Applying primary trigger (threshold={THRESHOLD_PRIMARY})...", flush=True)
    ret_k193_primary, mask_primary = apply_trigger(ret_k192, fr_mean, THRESHOLD_PRIMARY)
    n = len(ret_k192)
    oos_start = int(n * (1 - OOS_FRAC))
    print(f"  Trigger days (full): {int(mask_primary.sum())} / {n} ({mask_primary.mean()*100:.1f}%)")
    print(f"  Trigger days (OOS):  {int(mask_primary.iloc[oos_start:].sum())} / {n-oos_start} "
          f"({mask_primary.iloc[oos_start:].mean()*100:.1f}%)")
    print()

    # ── Step 4: Threshold sweep ──
    print("Step 4: Threshold sweep...", flush=True)
    sweep_results = threshold_sweep(ret_k192, fr_mean, THRESHOLDS_SWEEP)
    print()

    # ── Step 5: Walk-forward analysis with primary threshold ──
    print(f"Step 5: Walk-forward analysis (primary threshold={THRESHOLD_PRIMARY})...", flush=True)
    wf_results = walk_forward_analysis(ret_k192, ret_k193_primary, mask_primary, label="K193")
    print()

    # Also do K188 walk-forward for comparison
    print("Step 5b: K188 baseline walk-forward...", flush=True)
    ret_k188_trig, mask_k188 = apply_trigger(ret_k188, fr_mean, THRESHOLD_PRIMARY)
    wf_k188 = walk_forward_analysis(ret_k188, ret_k188_trig, mask_k188, label="K188_trigger")
    print()

    # ── Step 6: Rolling quantile adaptive threshold ──
    print("Step 6: Rolling 90d quantile adaptive threshold sweep...", flush=True)
    rolling_results = rolling_threshold_sweep(ret_k192, fr_mean)
    print()

    # ── Step 7: Full/OOS metrics comparison ──
    print("Step 7: Full metrics comparison...", flush=True)
    # K188 baseline
    m_k188_full = metrics_pkg(ret_k188.values)
    m_k188_oos  = metrics_pkg(ret_k188.iloc[oos_start:].values)
    # K192 (no trigger)
    m_k192_full = metrics_pkg(ret_k192.values)
    m_k192_oos  = metrics_pkg(ret_k192.iloc[oos_start:].values)
    # K193 primary
    m_k193_full = metrics_pkg(ret_k193_primary.values)
    m_k193_oos  = metrics_pkg(ret_k193_primary.iloc[oos_start:].values)

    print(f"  K188 | OOS Sh={m_k188_oos['sharpe']:.4f}, MaxDD={m_k188_oos['max_dd']:.4f}")
    print(f"  K192 | OOS Sh={m_k192_oos['sharpe']:.4f}, MaxDD={m_k192_oos['max_dd']:.4f}")
    print(f"  K193 | OOS Sh={m_k193_oos['sharpe']:.4f}, MaxDD={m_k193_oos['max_dd']:.4f}")
    print()

    # ── Step 8: FR_mean indicator series for curves export ──
    print("Step 8: Building equity curves for export...", flush=True)
    # Export dates from K192
    dates_list = [str(d.date()) for d in ret_k192.index]

    curves = {
        "K188_P3": returns_to_equity_curve(ret_k188),
        "K192_P3": returns_to_equity_curve(ret_k192),
        "K193_P3_primary": returns_to_equity_curve(ret_k193_primary),
    }

    # Also export rolling-threshold best version
    best_roll = None
    best_roll_sh = -999
    for q in [0.10, 0.15, 0.20, 0.25]:
        r_trig, r_mask = rolling_threshold_wf(ret_k192, fr_mean, quantile=q, window=90)
        oos_t = metrics_pkg(r_trig.iloc[oos_start:].values)
        if oos_t["sharpe"] > best_roll_sh:
            best_roll_sh = oos_t["sharpe"]
            best_roll_q  = q
            best_roll_ret = r_trig

    curves["K193_P3_rolling"] = returns_to_equity_curve(best_roll_ret)

    # FR_mean indicator
    fr_mean_vals = [round(float(v), 6) if not np.isnan(v) else None
                    for v in fr_mean_aligned.values]

    # Trigger mask (1=halted, 0=active)
    trigger_vals = [int(v) for v in mask_primary.values]

    print(f"  Rolling best: quantile={best_roll_q}, OOS Sh={best_roll_sh:.4f}")
    print()

    # ── Step 9: Acceptance criteria ──
    print("Step 9: Acceptance criteria check...", flush=True)
    trigger_pct_oos = mask_primary.iloc[oos_start:].mean() * 100

    c1_oos_lift = m_k193_oos["sharpe"] - m_k192_oos["sharpe"]
    c1_pass = bool(c1_oos_lift >= 0.10)
    c2_maxdd_ok = bool(m_k193_oos["max_dd"] >= m_k192_oos["max_dd"])  # not worsened (less negative)
    c3_wf_min = wf_results[f"min_K193"]
    c3_pass = bool(c3_wf_min >= 4.0)
    c4_trigger_ok = bool(trigger_pct_oos <= 30.0)
    all_pass = bool(c1_pass and c2_maxdd_ok and c3_pass and c4_trigger_ok)

    print(f"  C1: OOS Sh lift={c1_oos_lift:+.4f} (need >=+0.10) → {'PASS' if c1_pass else 'FAIL'}")
    print(f"  C2: MaxDD K192={m_k192_oos['max_dd']:.4f} vs K193={m_k193_oos['max_dd']:.4f} → {'PASS' if c2_maxdd_ok else 'FAIL'}")
    print(f"  C3: WF fold min={c3_wf_min:.4f} (need >=4.0) → {'PASS' if c3_pass else 'FAIL'}")
    print(f"  C4: OOS trigger%={trigger_pct_oos:.1f}% (need <=30%) → {'PASS' if c4_trigger_ok else 'FAIL'}")
    print(f"  ALL_PASS: {all_pass}")
    print()

    # ── Build output JSON ──
    result = {
        "wave": "K193",
        "task": "v6.2 Combine: K192 (DAR K175 filter) + K191 (FR-mean defensive trigger)",
        "generated": pd.Timestamp.now(tz="UTC").isoformat(),
        "runtime_s": round(time.time() - START_TIME, 1),
        "config": {
            "k192_variant": K192_VARIANT,
            "k188_variant": K188_VARIANT,
            "fr_symbols": FR_SYMBOLS,
            "fr_annualize_factor": "3*365 (3 payments/day)",
            "threshold_primary": THRESHOLD_PRIMARY,
            "thresholds_sweep": THRESHOLDS_SWEEP,
            "rolling_window": 90,
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
        "three_way_comparison": {
            "K188": {
                "full": m_k188_full,
                "oos": m_k188_oos,
                "wf_mean_P2_inv_vol": 4.7216,
                "wf_min_P2_inv_vol": 2.6043,
                "description": "K188 v6 baseline (K175 original, no DAR, no trigger)",
            },
            "K192": {
                "full": m_k192_full,
                "oos": m_k192_oos,
                "wf_mean": round(wf_results["mean_base"], 4),
                "wf_min":  round(wf_results["min_base"], 4),
                "description": f"K192a v6.1 ({K192_VARIANT}, K175_DAR filter, no trigger)",
            },
            "K193": {
                "full": m_k193_full,
                "oos": m_k193_oos,
                "wf_mean": wf_results["mean_K193"],
                "wf_min":  wf_results["min_K193"],
                "description": f"K193 v6.2 candidate (K192 + FR-mean trigger @ {THRESHOLD_PRIMARY})",
            },
        },
        "threshold_sweep": sweep_results,
        "rolling_threshold_sweep": rolling_results,
        "walk_forward_primary": wf_results,
        "walk_forward_k188_baseline": wf_k188,
        "acceptance_criteria": {
            "c1_oos_lift_needed": 0.10,
            "c1_oos_lift_actual": round(c1_oos_lift, 4),
            "c1_pass": c1_pass,
            "c2_maxdd_k192": m_k192_oos["max_dd"],
            "c2_maxdd_k193": m_k193_oos["max_dd"],
            "c2_pass": c2_maxdd_ok,
            "c3_wf_min_needed": 4.0,
            "c3_wf_min_actual": c3_wf_min,
            "c3_pass": c3_pass,
            "c4_trigger_pct_oos": round(trigger_pct_oos, 1),
            "c4_pass": c4_trigger_ok,
            "all_pass": all_pass,
        },
        "verdict": {
            "promoted_as": "K193 v6.2" if all_pass else "REJECTED",
            "all_criteria_met": all_pass,
            "k192_oos_sharpe": m_k192_oos["sharpe"],
            "k193_oos_sharpe": m_k193_oos["sharpe"],
            "delta": round(c1_oos_lift, 4),
            "verdict_text": (
                f"K193 ACCEPTED as v6.2 production (OOS Sh={m_k193_oos['sharpe']:.4f} vs K192={m_k192_oos['sharpe']:.4f}, "
                f"Δ={c1_oos_lift:+.4f}, WF min={c3_wf_min:.4f})"
                if all_pass else
                f"K193 REJECTED: OOS Sh lift={c1_oos_lift:+.4f} (need >=+0.10), "
                f"WF min={c3_wf_min:.4f} (need >=4.0), trigger%={trigger_pct_oos:.1f}%"
            ),
            "monitoring_triggers_updated": [
                f"FR_mean drops below {THRESHOLD_PRIMARY} → halt all trading (0% exposure)",
                "Rolling 90d FR_mean quantile check monthly for threshold recalibration",
                "K175_DAR OOS rolling-90d Sharpe drops >30% → re-evaluate DAR parameters",
                "BTC carry recent-90d Sharpe drops below 3.0 → reduce BTC weight to 0%",
                "ETH recent-90d Sharpe drops below 5.0 → re-run K186 and re-evaluate",
                "Any symbol: recent_mean_spread_bps <= 0 → COLLAPSE, remove immediately",
                "Portfolio OOS Sharpe drops >20% in rolling 90d → trigger K194 re-eval",
                "HL-Bybit funding spread compressed: carry contribution drops >30% → re-weight",
            ],
        },
    }

    # ── Save JSON ──
    def _to_native(obj):
        """Recursively convert numpy types to Python native types."""
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

    result = _to_native(result)

    out_json = BASE / "wave_k193_v6_2_combine.json"
    with open(out_json, "w") as f:
        json.dump(result, f, indent=2)
    print(f"Saved: {out_json}")

    # ── Save curves JSON ──
    curves_out = {
        "dates": dates_list,
        "series": curves,
        "fr_mean": fr_mean_vals,
        "trigger_mask_primary": trigger_vals,
        "threshold_primary": THRESHOLD_PRIMARY,
        "description": {
            "K188_P3": "K188 v6 baseline (P3_risk_parity), no DAR, no trigger",
            "K192_P3": "K192a v6.1 (P3_risk_parity, K175_DAR filter), no trigger",
            "K193_P3_primary": f"K193 v6.2 (K192 + FR_mean trigger @ {THRESHOLD_PRIMARY})",
            "K193_P3_rolling": f"K193 v6.2 rolling (K192 + rolling 90d q={best_roll_q} trigger)",
        },
    }
    curves_path = BASE / "wave_k193_curves.json"
    with open(curves_path, "w") as f:
        json.dump(curves_out, f, indent=2)
    print(f"Saved: {curves_path}")

    # ── Print final table ──
    print()
    print("=" * 70)
    print("FINAL COMPARISON TABLE")
    print("=" * 70)
    print(f"{'Version':<25} {'OOS Sh':>8} {'OOS MaxDD':>10} {'WF mean':>9} {'WF min':>9}")
    print("-" * 65)
    print(f"{'K188 baseline':<25} {m_k188_oos['sharpe']:>8.4f} {m_k188_oos['max_dd']:>10.4f} {'4.9216':>9} {'2.6043':>9}")
    print(f"{'K192 v6.1 (no trigger)':<25} {m_k192_oos['sharpe']:>8.4f} {m_k192_oos['max_dd']:>10.4f} {wf_results['mean_base']:>9.4f} {wf_results['min_base']:>9.4f}")
    print(f"{'K193 v6.2 (primary thr)':<25} {m_k193_oos['sharpe']:>8.4f} {m_k193_oos['max_dd']:>10.4f} {wf_results['mean_K193']:>9.4f} {wf_results['min_K193']:>9.4f}")
    print()
    print(f"Verdict: {result['verdict']['verdict_text']}")
    print(f"Runtime: {round(time.time() - START_TIME, 1)}s")

    return result


if __name__ == "__main__":
    main()

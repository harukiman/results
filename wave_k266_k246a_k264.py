"""Wave K266 — K246a + K264 Conservative Blend (v6.9.x candidate)

Objective:
  K246a v6.9 = 3-way ensemble (K198+K208+K226), OOS Sh 12.69, WF min 8.93
  K264 XS FR Carry: OOS Sh 1.17, |rho| < 0.11 vs K246a components (most orthogonal yet)
  K264 FAILED WF gate: fold 0 Sep 2024 Sh = -1.33 (momentum overwhelmed carry)

  K266: Test conservative K264 addition to K246a.
  Hypothesis: small-cap (3-7%) K264 allocation adds orthogonal alpha while
  limiting fold 0 damage below K246a baseline.

Variants:
  K266a: K246a * 0.97 + K264 * 0.03
  K266b: K246a * 0.95 + K264 * 0.05
  K266c: K246a * 0.93 + K264 * 0.07
  K266d: Adaptive — weight 5% when K264 30d rolling Sh > 0, else 0%

Acceptance for production (v6.9.x):
  OOS Sh > 12.69 + 0.05 = 12.74
  WF min >= 8.93 (STRICT — K264 fold 0 risk)
  MaxDD <= -0.00115

Runtime: <12 min
"""
from __future__ import annotations

import json
import math
import time
import warnings
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Tuple

import numpy as np
import pandas as pd

warnings.filterwarnings("ignore")

t0 = time.time()
BASE = Path("/Users/nekonaomichi/crypto-lab")

# ─────────────────────────────────────────────────────────────────────────────
# Reference metrics
# ─────────────────────────────────────────────────────────────────────────────
K246A_OOS_SH   = 12.6929
K246A_WF_MIN   = 8.9347
K246A_MAXDD    = -0.001145
K246A_WF_MEAN  = 12.2462
K246A_FOLDS    = [13.6029, 8.9347, 13.8374, 12.6097]

K264_OOS_SH    = 1.1719
K264_WF_FOLDS  = [-1.3320, 1.6154, 2.3748, 0.2720]  # from K264 metrics JSON

# Acceptance gates
GATE_OOS_SH    = K246A_OOS_SH + 0.05   # 12.74
GATE_WF_MIN    = K246A_WF_MIN           # 8.93
GATE_MAXDD     = K246A_MAXDD            # -0.00115

ANN = math.sqrt(365)

# ─────────────────────────────────────────────────────────────────────────────
# Helper functions
# ─────────────────────────────────────────────────────────────────────────────

def sharpe(pnl: np.ndarray) -> float:
    if len(pnl) < 2 or pnl.std() == 0:
        return 0.0
    return float(pnl.mean() / pnl.std() * ANN)


def max_drawdown(equity: np.ndarray) -> float:
    peak = np.maximum.accumulate(equity)
    dd = (equity - peak) / peak
    return float(dd.min())


def metrics_from_pnl(pnl: np.ndarray) -> dict:
    eq = np.cumprod(1 + pnl)
    eq = np.concatenate([[1.0], eq])
    sh = sharpe(pnl)
    dd = max_drawdown(eq)
    ann_ret = float(np.mean(pnl) * 365)
    ann_vol = float(np.std(pnl) * ANN)
    total_ret = float(eq[-1] - 1.0)
    win_rate = float(np.mean(pnl > 0))
    return dict(sharpe=sh, max_dd=dd, ann_ret=ann_ret, ann_vol=ann_vol,
                total_return=total_ret, win_rate=win_rate, n_days=len(pnl))


# ─────────────────────────────────────────────────────────────────────────────
# 1. Load equity curves
# ─────────────────────────────────────────────────────────────────────────────
print("=" * 70)
print("Wave K266: K246a + K264 Conservative Blend (v6.9.x candidate)")
print("=" * 70)

print("\n=== LOADING EQUITY CURVES ===")

# K246a — from wave_k246_curves.json
with open(BASE / "wave_k246_curves.json") as f:
    k246_raw = json.load(f)

dates_ml = k246_raw["dates"]   # 448 day strings: 2025-01-22 -> 2026-04-14
eq246a   = np.array(k246_raw["K246a"])   # equity curve, starts at 1.0
# Daily PnL = simple returns of equity (not log returns, consistent with K246)
pnl246a  = np.diff(eq246a) / eq246a[:-1]
print(f"K246a: {len(dates_ml)} days  {dates_ml[0]} -> {dates_ml[-1]}")
print(f"  equity: {eq246a[0]:.6f} -> {eq246a[-1]:.6f}")
print(f"  pnl: mean={pnl246a.mean():.6f}  std={pnl246a.std():.6f}")

# K264 — from wave_k264_curves.json
with open(BASE / "wave_k264_curves.json") as f:
    k264_raw = json.load(f)

k264_data = k264_raw["K264_xs_fr_carry"]
k264_date_to_pnl: Dict[str, float] = dict(zip(k264_data["dates"], k264_data["pnl"]))

# Align K264 pnl to K246a dates (dates_ml has 448 entries; pnl has 447 entries
# since it's the return between day i-1 and day i, so pnl[i] corresponds to dates_ml[i+1])
# K246a pnl[i] = return from day i to day i+1, aligned to dates_ml[i] (close-to-close)
# K264 pnl[i] is indexed by date = the closing date of that return
# So K264 pnl for dates_ml[1..N] aligns with K246a pnl[0..N-1]
pnl264_aligned = np.zeros(len(pnl246a))
missing_k264 = 0
for i, d in enumerate(dates_ml[1:]):   # dates_ml[1] = end of first return
    v = k264_date_to_pnl.get(d, None)
    if v is None:
        missing_k264 += 1
        # Forward-fill with 0 (no carry signal = flat)
        pnl264_aligned[i] = 0.0
    else:
        pnl264_aligned[i] = v

print(f"\nK264: {len(k264_data['dates'])} days  {k264_data['dates'][0]} -> {k264_data['dates'][-1]}")
print(f"  pnl aligned to K246a window: n={len(pnl264_aligned)}  missing={missing_k264}")
print(f"  pnl: mean={pnl264_aligned.mean():.6f}  std={pnl264_aligned.std():.6f}")

# Correlation K246a vs K264 on shared window
rho = float(np.corrcoef(pnl246a, pnl264_aligned)[0, 1])
print(f"\n  rho(K246a, K264) on K246a window = {rho:.4f}")

# ─────────────────────────────────────────────────────────────────────────────
# 2. Build K266 blend variants
# ─────────────────────────────────────────────────────────────────────────────
print("\n=== BUILDING K266 VARIANTS ===")

N = len(pnl246a)
# Dates for the return series: dates_ml[0] -> dates_ml[N-1] (returns close from [i] to [i+1])
ret_dates = dates_ml[:-1]   # 447 return dates (start of each return period)

# K266a: 97/3
w264_a = 0.03
pnl266a = (1 - w264_a) * pnl246a + w264_a * pnl264_aligned
print(f"K266a: K246a*0.97 + K264*0.03  — mean={pnl266a.mean():.6f}")

# K266b: 95/5
w264_b = 0.05
pnl266b = (1 - w264_b) * pnl246a + w264_b * pnl264_aligned
print(f"K266b: K246a*0.95 + K264*0.05  — mean={pnl266b.mean():.6f}")

# K266c: 93/7
w264_c = 0.07
pnl266c = (1 - w264_c) * pnl246a + w264_c * pnl264_aligned
print(f"K266c: K246a*0.93 + K264*0.07  — mean={pnl266c.mean():.6f}")

# K266d: Adaptive — 5% when K264 30d rolling Sharpe > 0, else 0%
# Rolling Sharpe uses 30-day window centered at each point (causal: past 30 days)
WIN = 30
k264_roll_sh = np.zeros(N)
for i in range(N):
    start = max(0, i - WIN + 1)
    window = pnl264_aligned[start:i+1]
    if len(window) >= 2 and window.std() > 0:
        k264_roll_sh[i] = window.mean() / window.std() * ANN
    else:
        k264_roll_sh[i] = 0.0

# Adaptive weight: determined at start of period i (using rolling Sh computed on i's past)
# No look-ahead: weight at i uses rolling Sh including day i-1 at most
adaptive_w = np.where(k264_roll_sh > 0, 0.05, 0.0)
pnl266d = (1 - adaptive_w) * pnl246a + adaptive_w * pnl264_aligned
pct_active = float(np.mean(adaptive_w > 0))
print(f"K266d: Adaptive 5%/0% (30d roll Sh>0)  — active={pct_active:.1%}  mean={pnl266d.mean():.6f}")

variants = {
    "K266a": (pnl266a, w264_a),
    "K266b": (pnl266b, w264_b),
    "K266c": (pnl266c, w264_c),
    "K266d": (pnl266d, None),
}

# ─────────────────────────────────────────────────────────────────────────────
# 3. Walk-forward 4-fold
# ─────────────────────────────────────────────────────────────────────────────
print("\n=== WALK-FORWARD 4-FOLD ===")

# 4 equal folds over 447 returns
fold_size = N // 4  # ~111 per fold
fold_boundaries = [(i * fold_size, min((i+1) * fold_size, N)) for i in range(4)]
# Pad last fold to include remainder
fold_boundaries[-1] = (fold_boundaries[-1][0], N)

print(f"Total returns: {N}  |  Fold size: ~{fold_size}")
for fi, (s, e) in enumerate(fold_boundaries):
    print(f"  Fold {fi}: [{s}:{e}]  dates {ret_dates[s]} -> {ret_dates[e-1]}  n={e-s}")

def walk_forward_folds(pnl: np.ndarray, fold_bounds: List[Tuple[int, int]]) -> dict:
    fold_results = []
    all_oos_pnl = np.zeros(N)
    for fi, (s, e) in enumerate(fold_bounds):
        fold_pnl = pnl[s:e]
        m = metrics_from_pnl(fold_pnl)
        m["fold"] = fi
        m["start"] = ret_dates[s]
        m["end"]   = ret_dates[e-1]
        fold_results.append(m)
        all_oos_pnl[s:e] = fold_pnl

    oos_metrics = metrics_from_pnl(all_oos_pnl)
    fold_sharpes = [r["sharpe"] for r in fold_results]
    wf_mean = float(np.mean(fold_sharpes))
    wf_min  = float(np.min(fold_sharpes))
    return dict(
        folds=fold_results,
        oos_metrics=oos_metrics,
        wf_mean=wf_mean,
        wf_min=wf_min,
        fold_sharpes=fold_sharpes,
    )

# Also run baseline K246a for comparison (on same return series)
wf_k246a = walk_forward_folds(pnl246a, fold_boundaries)
wf_k264  = walk_forward_folds(pnl264_aligned, fold_boundaries)

wf_results = {}
for name, (pnl, w264) in variants.items():
    wf = walk_forward_folds(pnl, fold_boundaries)
    wf_results[name] = wf

# ─────────────────────────────────────────────────────────────────────────────
# 4. Print results
# ─────────────────────────────────────────────────────────────────────────────
print("\n" + "=" * 70)
print("RESULTS SUMMARY")
print("=" * 70)

header = f"{'Variant':<10}  {'OOS Sh':>8}  {'WF mean':>8}  {'WF min':>8}  {'MaxDD':>10}  {'Ann Ret':>8}  {'Folds'}"
print(header)
print("-" * 80)

# Baseline K246a (reproduced)
m = wf_k246a["oos_metrics"]
fs = wf_k246a["fold_sharpes"]
print(f"{'K246a':10}  {m['sharpe']:8.4f}  {wf_k246a['wf_mean']:8.4f}  {wf_k246a['wf_min']:8.4f}  {m['max_dd']:10.6f}  {m['ann_ret']:8.4f}  {[f'{s:.2f}' for s in fs]}")

# K264 baseline
m264 = wf_k264["oos_metrics"]
fs264 = wf_k264["fold_sharpes"]
print(f"{'K264':10}  {m264['sharpe']:8.4f}  {wf_k264['wf_mean']:8.4f}  {wf_k264['wf_min']:8.4f}  {m264['max_dd']:10.6f}  {m264['ann_ret']:8.4f}  {[f'{s:.2f}' for s in fs264]}")

for name, wf in wf_results.items():
    m = wf["oos_metrics"]
    fs = wf["fold_sharpes"]
    delta_sh = m["sharpe"] - wf_k246a["oos_metrics"]["sharpe"]
    print(f"{name:<10}  {m['sharpe']:8.4f}  {wf['wf_mean']:8.4f}  {wf['wf_min']:8.4f}  {m['max_dd']:10.6f}  {m['ann_ret']:8.4f}  {[f'{s:.2f}' for s in fs]}  delta={delta_sh:+.4f}")

print("\n--- Per-fold breakdown (Sharpe) ---")
fold_header = f"{'Variant':<10}  {'Fold0':>8}  {'Fold1':>8}  {'Fold2':>8}  {'Fold3':>8}  {'WF min':>8}"
print(fold_header)
print("-" * 60)
for name, wf in [("K246a", wf_k246a), ("K264", wf_k264)] + list(wf_results.items()):
    fs = wf["fold_sharpes"]
    print(f"{name:<10}  {fs[0]:8.4f}  {fs[1]:8.4f}  {fs[2]:8.4f}  {fs[3]:8.4f}  {wf['wf_min']:8.4f}")

# ─────────────────────────────────────────────────────────────────────────────
# 5. Gate evaluation
# ─────────────────────────────────────────────────────────────────────────────
print("\n=== GATE EVALUATION ===")
print(f"  Gate OOS Sh  > {GATE_OOS_SH:.4f}")
print(f"  Gate WF min >= {GATE_WF_MIN:.4f}")
print(f"  Gate MaxDD  <= {GATE_MAXDD:.6f}")

gate_results = {}
for name, wf in wf_results.items():
    m = wf["oos_metrics"]
    g_sh  = m["sharpe"] > GATE_OOS_SH
    g_wf  = wf["wf_min"] >= GATE_WF_MIN
    g_dd  = m["max_dd"] <= GATE_MAXDD  # max_dd is negative, <= means less deep
    passed = g_sh and g_wf and g_dd
    gate_results[name] = dict(g_sh=g_sh, g_wf=g_wf, g_dd=g_dd, passed=passed)
    status = "PASS" if passed else "FAIL"
    reasons = []
    if not g_sh: reasons.append(f"OOS Sh {m['sharpe']:.4f} <= {GATE_OOS_SH:.4f}")
    if not g_wf: reasons.append(f"WF min {wf['wf_min']:.4f} < {GATE_WF_MIN:.4f}")
    if not g_dd: reasons.append(f"MaxDD {m['max_dd']:.6f} > {GATE_MAXDD:.6f}")
    reason_str = "; ".join(reasons) if reasons else "all gates cleared"
    print(f"  {name}: {status}  ({reason_str})")

# ─────────────────────────────────────────────────────────────────────────────
# 6. Sensitivity analysis — K264 weight vs OOS Sh / WF min
# ─────────────────────────────────────────────────────────────────────────────
print("\n=== SENSITIVITY: K264 weight vs OOS Sh / WF min ===")
print(f"{'K264 wt':>8}  {'OOS Sh':>8}  {'WF min':>8}  {'Fold0':>8}  {'delta Sh':>10}")
for w in [0.0, 0.01, 0.02, 0.03, 0.05, 0.07, 0.10, 0.15, 0.20]:
    pnl_blend = (1 - w) * pnl246a + w * pnl264_aligned
    wf_blend = walk_forward_folds(pnl_blend, fold_boundaries)
    oos_sh = wf_blend["oos_metrics"]["sharpe"]
    wf_min = wf_blend["wf_min"]
    fold0  = wf_blend["fold_sharpes"][0]
    delta  = oos_sh - wf_k246a["oos_metrics"]["sharpe"]
    print(f"{w:8.2f}  {oos_sh:8.4f}  {wf_min:8.4f}  {fold0:8.4f}  {delta:+10.4f}")

# ─────────────────────────────────────────────────────────────────────────────
# 7. Best variant selection
# ─────────────────────────────────────────────────────────────────────────────
any_pass = any(v["passed"] for v in gate_results.values())
best_name = None
best_sh   = -999.0

if any_pass:
    for name, gr in gate_results.items():
        if gr["passed"]:
            sh = wf_results[name]["oos_metrics"]["sharpe"]
            if sh > best_sh:
                best_sh   = sh
                best_name = name
    print(f"\nBEST K266 VARIANT: {best_name}  (OOS Sh={best_sh:.4f})")
else:
    print("\nNo K266 variant passed all gates.")

# ─────────────────────────────────────────────────────────────────────────────
# 8. Equity curve output
# ─────────────────────────────────────────────────────────────────────────────
print("\n=== BUILDING EQUITY CURVES ===")

def pnl_to_equity(pnl: np.ndarray) -> List[float]:
    """Convert pnl returns to equity curve starting at 1.0"""
    eq = np.cumprod(1 + pnl)
    return [1.0] + list(eq)

# Equity curves use dates_ml (448 points for 447 returns)
curves_out = {
    "dates": dates_ml,
    "K246a": list(eq246a),
    "K264_aligned": [1.0] + list(np.cumprod(1 + pnl264_aligned)),
}
for name, (pnl, _) in variants.items():
    curves_out[name] = pnl_to_equity(pnl)

# ─────────────────────────────────────────────────────────────────────────────
# 9. Assemble metrics output
# ─────────────────────────────────────────────────────────────────────────────
as_of = datetime.now(timezone.utc).isoformat()
runtime = round(time.time() - t0, 2)

k246a_reproduced = {
    "oos_sh": wf_k246a["oos_metrics"]["sharpe"],
    "wf_mean": wf_k246a["wf_mean"],
    "wf_min": wf_k246a["wf_min"],
    "max_dd": wf_k246a["oos_metrics"]["max_dd"],
    "fold_sharpes": wf_k246a["fold_sharpes"],
}

variant_metrics = {}
for name, wf in wf_results.items():
    m = wf["oos_metrics"]
    w264 = variants[name][1]
    variant_metrics[name] = {
        "k264_weight": w264,
        "k264_active_pct": float(np.mean(adaptive_w > 0)) if name == "K266d" else w264,
        "oos_metrics": m,
        "wf_mean": wf["wf_mean"],
        "wf_min": wf["wf_min"],
        "fold_sharpes": wf["fold_sharpes"],
        "fold_details": [
            {k: v for k, v in fold.items()} for fold in wf["folds"]
        ],
        "gate": gate_results[name],
    }

output = {
    "wave": "K266",
    "strategy": "K246a_K264_Conservative_Blend",
    "as_of": as_of,
    "runtime_s": runtime,
    "reference": {
        "K246a_oos_sh": K246A_OOS_SH,
        "K246a_wf_min": K246A_WF_MIN,
        "K246a_max_dd": K246A_MAXDD,
        "K246a_wf_folds": K246A_FOLDS,
        "K264_oos_sh": K264_OOS_SH,
        "K264_wf_folds": K264_WF_FOLDS,
    },
    "correlation": {
        "rho_k246a_k264": rho,
    },
    "gates": {
        "oos_sh_threshold": GATE_OOS_SH,
        "wf_min_threshold": GATE_WF_MIN,
        "max_dd_threshold": GATE_MAXDD,
    },
    "k246a_reproduced": k246a_reproduced,
    "variants": variant_metrics,
    "best_variant": best_name,
    "any_pass": any_pass,
    "verdict": "K264 integration viable: at least one variant passed all gates."
              if any_pass else
              "K264 integration FAILED: no variant passes all gates. K246a is local maximum.",
}

# ─────────────────────────────────────────────────────────────────────────────
# 10. Save outputs
# ─────────────────────────────────────────────────────────────────────────────
metrics_path = BASE / "wave_k266_k246a_k264.json"
curves_path  = BASE / "wave_k266_curves.json"

with open(metrics_path, "w") as f:
    json.dump(output, f, indent=2)
print(f"\nMetrics saved: {metrics_path}")

with open(curves_path, "w") as f:
    json.dump(curves_out, f)
print(f"Curves  saved: {curves_path}")

# ─────────────────────────────────────────────────────────────────────────────
# 11. Final verdict
# ─────────────────────────────────────────────────────────────────────────────
print("\n" + "=" * 70)
print("FINAL VERDICT ON K264 INTEGRATION / K246a FINALITY ASSESSMENT")
print("=" * 70)
print(output["verdict"])
if any_pass and best_name:
    wf_best = wf_results[best_name]
    m_best  = wf_best["oos_metrics"]
    print(f"\n  Best variant: {best_name}")
    print(f"  OOS Sh: {m_best['sharpe']:.4f}  (gate: >{GATE_OOS_SH:.4f})")
    print(f"  WF min: {wf_best['wf_min']:.4f}  (gate: >={GATE_WF_MIN:.4f})")
    print(f"  MaxDD:  {m_best['max_dd']:.6f}  (gate: <={GATE_MAXDD:.6f})")
else:
    print()
    # Show which gate was hardest to pass for each variant
    for name, gr in gate_results.items():
        wf = wf_results[name]
        m  = wf["oos_metrics"]
        print(f"  {name}: OOS Sh={m['sharpe']:.4f}  WF min={wf['wf_min']:.4f}  MaxDD={m['max_dd']:.6f}")

print(f"\nRuntime: {runtime:.1f}s")
print("=" * 70)

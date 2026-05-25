"""
Wave K244 — K229d OOS Sharpe Distribution across Window Cuts
Objective: Honest deployment confidence intervals via ±15d start-date perturbations.

Base ML window: 90d train + 30d test × 15 steps = 448 days
Strategy: K229d = 4-way meta (K198 × K204 × K208 × K226), inv-vol + K226 cap 20%
Benchmarks: K198, K208 standalone, K218e_ref (3-way)

Runtime: < 3 minutes
"""

import json
import numpy as np
from datetime import datetime
import time

t0 = time.time()

# ─────────────────────────────────────────────────────────────────────────────
# 1. Load equity series from wave_k229_curves.json
# ─────────────────────────────────────────────────────────────────────────────
with open("/Users/nekonaomichi/crypto-lab/wave_k229_curves.json") as f:
    curves = json.load(f)

dates_all = curves["dates"]          # 448 dates: 2025-01-22 → 2026-04-14
eq_k229d  = np.array(curves["K229d"])
eq_k198   = np.array(curves["K198"])
eq_k208   = np.array(curves["K208"])
eq_k218e  = np.array(curves["K218e_ref"])
eq_k226   = np.array(curves["K226"])

N_TOTAL = len(eq_k229d)  # 448

print(f"Loaded curves: {N_TOTAL} days ({dates_all[0]} → {dates_all[-1]})")
print(f"Strategies: K229d, K198, K208, K218e_ref, K226")

# ─────────────────────────────────────────────────────────────────────────────
# 2. Utility functions (same as K229 script)
# ─────────────────────────────────────────────────────────────────────────────
ANN = np.sqrt(365)

def sharpe(rets):
    """Annualised Sharpe (daily returns)."""
    rets = np.asarray(rets)
    if len(rets) < 10:
        return np.nan
    mu  = np.mean(rets) * 365
    sig = np.std(rets, ddof=1) * ANN
    return float(mu / sig) if sig > 1e-12 else np.nan

def maxdd(rets):
    """Maximum drawdown (negative number)."""
    rets = np.asarray(rets)
    eq = np.cumprod(1 + rets)
    roll_max = np.maximum.accumulate(eq)
    dd = (eq - roll_max) / roll_max
    return float(dd.min())

def calmar(rets):
    """Calmar ratio = annualised return / abs(MaxDD)."""
    rets = np.asarray(rets)
    ann_ret = float(np.mean(rets) * 365)
    dd = maxdd(rets)
    if abs(dd) < 1e-9:
        return np.nan
    return ann_ret / abs(dd)

def wf_stats(rets, n_folds=4):
    """Walk-forward 4-fold chronological splits."""
    rets = np.asarray(rets)
    fold_size = len(rets) // n_folds
    fold_sharpes = []
    for i in range(n_folds):
        start = i * fold_size
        end   = (i + 1) * fold_size if i < n_folds - 1 else len(rets)
        fs = sharpe(rets[start:end])
        fold_sharpes.append(fs)
    fold_sharpes = [s for s in fold_sharpes if not np.isnan(s)]
    if not fold_sharpes:
        return {"wf_mean": np.nan, "wf_min": np.nan, "fold_sharpes": []}
    return {
        "wf_mean":       round(float(np.mean(fold_sharpes)), 4),
        "wf_min":        round(float(np.min(fold_sharpes)), 4),
        "fold_sharpes":  [round(s, 4) for s in fold_sharpes],
    }

def oos_metrics(rets, oos_frac=0.3):
    """OOS metrics on final oos_frac of the return series."""
    rets = np.asarray(rets)
    oos_start = int(len(rets) * (1 - oos_frac))
    oos_rets  = rets[oos_start:]
    return {
        "oos_sharpe":  round(sharpe(oos_rets), 4),
        "oos_maxdd":   round(maxdd(oos_rets), 6),
        "oos_calmar":  round(calmar(oos_rets), 4),
        "oos_n_days":  len(oos_rets),
        "oos_ann_ret": round(float(np.mean(oos_rets) * 365), 4),
    }

def equity_to_returns(equity):
    """Convert equity curve to daily returns."""
    eq = np.asarray(equity, dtype=float)
    ret = np.diff(eq) / eq[:-1]
    return ret

def compute_cut_metrics(eq_slice, label=""):
    """Given an equity slice [N], compute OOS + WF metrics."""
    rets = equity_to_returns(eq_slice)
    oos  = oos_metrics(rets)
    wf   = wf_stats(rets)
    return {
        "label":      label,
        "n_days":     len(eq_slice),
        "oos_sharpe": oos["oos_sharpe"],
        "oos_maxdd":  oos["oos_maxdd"],
        "oos_calmar": oos["oos_calmar"],
        "oos_n_days": oos["oos_n_days"],
        "wf_mean":    wf["wf_mean"],
        "wf_min":     wf["wf_min"],
        "fold_sharpes": wf["fold_sharpes"],
    }

# ─────────────────────────────────────────────────────────────────────────────
# 3. Define window cut variants
#    Base window: full 448 days (idx 0..447)
#    Shift start by -15 to +15 days in steps of 3
#    Also vary end clipping to test cut sensitivity
# ─────────────────────────────────────────────────────────────────────────────

# Strategy: we have 448 days. We will test windows by:
# (a) Shifting start index: 0, 3, 6, 9, 12, 15 (shift forward = shorter window)
# (b) Shifting negative: impossible without padding; instead trim end
#     Shift start -15 equiv = keep more days at end: trim end from 448 to extend start
# Since we cannot go before day 0, we simulate "earlier start" by
# considering subwindows of the AVAILABLE data.
#
# Approach:
#   - Base = idx 0 : 448 (full)
#   - +Nd start shifts: idx N : 448 (shift start forward, drop first N days)
#   - -Nd start shifts: idx 0 : (448-N) (trim end, equivalent to earlier-end cut)
#   This gives symmetric ±15d perturbation of the window's OOS boundary.

MIN_WINDOW = 300  # need enough days for meaningful OOS

cuts = []

# Base window (original K229 evaluation)
cuts.append({"name": "Base (0d shift)", "start": 0, "end": 448, "shift": 0})

# Forward start shifts (+3d to +15d): drop first N days → window shrinks from left
for shift in [3, 6, 9, 12, 15]:
    start = shift
    end   = 448
    if end - start >= MIN_WINDOW:
        cuts.append({"name": f"+{shift}d start", "start": start, "end": end, "shift": shift})

# Backward-equivalent shifts (trim end by N days):
# represents "if OOS was measured from N days earlier"
for shift in [3, 6, 9, 12, 15]:
    start = 0
    end   = 448 - shift
    if end - start >= MIN_WINDOW:
        cuts.append({"name": f"-{shift}d end", "start": start, "end": end, "shift": -shift})

# Mixed cuts: shift both start and end asymmetrically
cuts.append({"name": "+5d start -10d end", "start": 5, "end": 438, "shift": 5})
cuts.append({"name": "+10d start -5d end", "start": 10, "end": 443, "shift": 10})
cuts.append({"name": "+8d start +8d end-trim", "start": 8, "end": 440, "shift": 8})

print(f"\nGenerated {len(cuts)} window cuts")
for c in cuts:
    n = c["end"] - c["start"]
    print(f"  {c['name']:30s}: idx [{c['start']:3d}:{c['end']:3d}] = {n} days")

# ─────────────────────────────────────────────────────────────────────────────
# 4. Compute metrics for each cut × each strategy
# ─────────────────────────────────────────────────────────────────────────────
strategies = {
    "K229d":   eq_k229d,
    "K198":    eq_k198,
    "K208":    eq_k208,
    "K218e":   eq_k218e,
}

results = []   # list of dicts: {cut, strategy, metrics...}

print("\n" + "="*70)
print("COMPUTING METRICS PER WINDOW CUT")
print("="*70)

for cut in cuts:
    s = cut["start"]
    e = cut["end"]
    row = {
        "cut_name":  cut["name"],
        "cut_start": s,
        "cut_end":   e,
        "n_days":    e - s,
        "strategies": {}
    }
    line = f"\n{cut['name']:30s} [{s}:{e}] n={e-s}:"
    print(line)
    for strat_name, eq_arr in strategies.items():
        eq_slice = eq_arr[s:e]
        # Re-normalize to start at 1.0
        if eq_slice[0] != 0:
            eq_slice = eq_slice / eq_slice[0]
        m = compute_cut_metrics(eq_slice, label=strat_name)
        row["strategies"][strat_name] = m
        print(f"  {strat_name:10s}: OOS Sh={m['oos_sharpe']:6.3f}  "
              f"WF min={m['wf_min']:6.3f}  MaxDD={m['oos_maxdd']:8.5f}  "
              f"Calmar={m['oos_calmar']:6.2f}")
    results.append(row)

# ─────────────────────────────────────────────────────────────────────────────
# 5. Distribution statistics per strategy
# ─────────────────────────────────────────────────────────────────────────────
print("\n" + "="*70)
print("DISTRIBUTION SUMMARY")
print("="*70)

dist_stats = {}
for strat_name in strategies:
    oos_sharpes = [r["strategies"][strat_name]["oos_sharpe"] for r in results
                   if not np.isnan(r["strategies"][strat_name]["oos_sharpe"])]
    wf_mins     = [r["strategies"][strat_name]["wf_min"] for r in results
                   if not np.isnan(r["strategies"][strat_name]["wf_min"])]
    maxdds      = [r["strategies"][strat_name]["oos_maxdd"] for r in results
                   if not np.isnan(r["strategies"][strat_name]["oos_maxdd"])]
    calvars     = [r["strategies"][strat_name]["oos_calmar"] for r in results
                   if not np.isnan(r["strategies"][strat_name]["oos_calmar"])]

    def pct(arr, p):
        return float(np.percentile(arr, p)) if arr else np.nan

    stats = {
        "strategy":    strat_name,
        "n_cuts":      len(oos_sharpes),
        "oos_sh_mean": round(pct(oos_sharpes, 50) if False else float(np.mean(oos_sharpes)), 4),
        "oos_sh_median": round(float(np.median(oos_sharpes)), 4),
        "oos_sh_std":  round(float(np.std(oos_sharpes, ddof=1)), 4),
        "oos_sh_min":  round(float(np.min(oos_sharpes)), 4),
        "oos_sh_max":  round(float(np.max(oos_sharpes)), 4),
        "oos_sh_p10":  round(pct(oos_sharpes, 10), 4),
        "oos_sh_p25":  round(pct(oos_sharpes, 25), 4),
        "oos_sh_p75":  round(pct(oos_sharpes, 75), 4),
        "oos_sh_p90":  round(pct(oos_sharpes, 90), 4),
        "wf_min_mean": round(float(np.mean(wf_mins)), 4) if wf_mins else np.nan,
        "wf_min_p10":  round(pct(wf_mins, 10), 4),
        "maxdd_mean":  round(float(np.mean(maxdds)), 6) if maxdds else np.nan,
        "calmar_mean": round(float(np.mean(calvars)), 4) if calvars else np.nan,
    }
    dist_stats[strat_name] = stats

    print(f"\n{strat_name}:")
    print(f"  OOS Sh  | Mean={stats['oos_sh_mean']:7.3f}  Median={stats['oos_sh_median']:7.3f}  "
          f"Std={stats['oos_sh_std']:5.3f}  Min={stats['oos_sh_min']:7.3f}  Max={stats['oos_sh_max']:7.3f}")
    print(f"          | P10={stats['oos_sh_p10']:7.3f}   P25={stats['oos_sh_p25']:7.3f}   "
          f"P75={stats['oos_sh_p75']:7.3f}   P90={stats['oos_sh_p90']:7.3f}")
    print(f"  WF min  | Mean={stats['wf_min_mean']:7.3f}  P10={stats['wf_min_p10']:7.3f}")
    print(f"  MaxDD   | Mean={stats['maxdd_mean']:9.5f}")
    print(f"  Calmar  | Mean={stats['calmar_mean']:7.2f}")

# ─────────────────────────────────────────────────────────────────────────────
# 6. Acceptance gate check
# ─────────────────────────────────────────────────────────────────────────────
print("\n" + "="*70)
print("ACCEPTANCE GATE CHECK")
print("="*70)

k229d_p10  = dist_stats["K229d"]["oos_sh_p10"]
k198_p50   = dist_stats["K198"]["oos_sh_median"]
k229d_std  = dist_stats["K229d"]["oos_sh_std"]
k229d_med  = dist_stats["K229d"]["oos_sh_median"]
k229d_mean = dist_stats["K229d"]["oos_sh_mean"]

gate1 = k229d_p10 > k198_p50
gate2 = k229d_std < 5.0   # reasonable std (< 5 Sharpe points)
gate3 = abs(k229d_med - 12.61) < 3.0  # median within 3 of baseline

print(f"\nGate 1: K229d P10 ({k229d_p10:.3f}) > K198 P50 ({k198_p50:.3f}) -> {'PASS' if gate1 else 'FAIL'}")
print(f"Gate 2: K229d Std ({k229d_std:.3f}) < 5.0 -> {'PASS' if gate2 else 'FAIL (too volatile)'}")
print(f"Gate 3: K229d Median ({k229d_med:.3f}) ≈ baseline 12.61 (within ±3) -> {'PASS' if gate3 else 'FAIL (inconsistent)'}")

# ─────────────────────────────────────────────────────────────────────────────
# 7. Deployment Sharpe estimate
# ─────────────────────────────────────────────────────────────────────────────
deployment = {
    "conservative_p10":  k229d_p10,
    "median_estimate":   k229d_med,
    "optimistic_p90":    dist_stats["K229d"]["oos_sh_p90"],
    "k229_original_reported": 12.61,
    "k240_measurement":       10.17,
    "overstated_by":    round(12.61 - k229d_med, 3),
    "realistic_range":  f"{k229d_p10:.2f} – {dist_stats['K229d']['oos_sh_p90']:.2f}",
    "recommendation":   ""
}

if k229d_med < 10.0:
    deployment["recommendation"] = "CAUTION: Median OOS Sh < 10.0; original 12.61 materially overstated"
elif k229d_med >= 10.0 and k229d_med < 11.5:
    deployment["recommendation"] = "MODERATE: Median in 10-11.5 range; original 12.61 somewhat optimistic but edge real"
else:
    deployment["recommendation"] = "CONSISTENT: Median close to 12.61; deployment confidence high"

print(f"\nDeployment Sharpe Estimates:")
print(f"  Conservative (P10): {deployment['conservative_p10']:.2f}")
print(f"  Median:             {deployment['median_estimate']:.2f}")
print(f"  Optimistic (P90):   {deployment['optimistic_p90']:.2f}")
print(f"  Original reported:  {deployment['k229_original_reported']:.2f}")
print(f"  K240 measurement:   {deployment['k240_measurement']:.2f}")
print(f"  Overstated by:      {deployment['overstated_by']:.3f} Sh points (vs median)")
print(f"  Recommendation:     {deployment['recommendation']}")

# ─────────────────────────────────────────────────────────────────────────────
# 8. Per-cut equity curves for wave_k244_curves.json
# ─────────────────────────────────────────────────────────────────────────────
print("\nBuilding per-cut equity curves...")

cut_curves = {}
for cut in cuts:
    s = cut["start"]
    e = cut["end"]
    cut_name = cut["name"]
    cut_curves[cut_name] = {
        "dates": dates_all[s:e],
        "start": s,
        "end":   e,
        "curves": {}
    }
    for strat_name, eq_arr in strategies.items():
        eq_slice = eq_arr[s:e].tolist()
        # Re-normalize
        if eq_slice[0] != 0:
            norm_val = eq_slice[0]
            eq_slice = [v / norm_val for v in eq_slice]
        cut_curves[cut_name]["curves"][strat_name] = [round(v, 6) for v in eq_slice]

# ─────────────────────────────────────────────────────────────────────────────
# 9. Save outputs
# ─────────────────────────────────────────────────────────────────────────────
elapsed = round(time.time() - t0, 2)
print(f"\nElapsed: {elapsed}s")

# Main distribution JSON
output_json = {
    "meta": {
        "wave":         "K244",
        "timestamp":    datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ"),
        "n_cuts":       len(cuts),
        "elapsed_s":    elapsed,
        "base_window":  {"start": 0, "end": 448, "n_days": 448},
        "strategies_tested": list(strategies.keys()),
    },
    "cuts": results,
    "distribution_stats": dist_stats,
    "deployment": deployment,
    "acceptance_gates": {
        "gate1_k229d_p10_gt_k198_p50": {"pass": gate1, "k229d_p10": k229d_p10, "k198_p50": k198_p50},
        "gate2_std_lt_5":              {"pass": gate2, "k229d_std": k229d_std},
        "gate3_median_vs_baseline":    {"pass": gate3, "k229d_median": k229d_med, "baseline": 12.61},
    }
}

with open("/Users/nekonaomichi/crypto-lab/wave_k244_k229_window_sensitivity.json", "w") as f:
    json.dump(output_json, f, indent=2)
print("Saved: wave_k244_k229_window_sensitivity.json")

with open("/Users/nekonaomichi/crypto-lab/wave_k244_curves.json", "w") as f:
    json.dump(cut_curves, f, indent=2)
print("Saved: wave_k244_curves.json")

# ─────────────────────────────────────────────────────────────────────────────
# 10. Comparison table print
# ─────────────────────────────────────────────────────────────────────────────
print("\n" + "="*90)
print("COMPARISON TABLE: Per Window Cut")
print("="*90)
header = f"{'Window':30s}  {'K229d Sh':>9}  {'WF min':>7}  {'MaxDD':>9}  {'Calmar':>8}"
print(header)
print("-"*90)
for r in results:
    k = r["strategies"]["K229d"]
    print(f"{r['cut_name']:30s}  {k['oos_sharpe']:9.3f}  {k['wf_min']:7.3f}  "
          f"{k['oos_maxdd']:9.5f}  {k['oos_calmar']:8.2f}")

print("\n" + "="*90)
print("DISTRIBUTION TABLE: OOS Sharpe by Strategy")
print("="*90)
print(f"{'Strategy':12s}  {'Mean':>7}  {'Median':>7}  {'Std':>5}  {'Min':>7}  "
      f"{'Max':>7}  {'P10':>7}  {'P90':>7}")
print("-"*90)
for strat_name, s in dist_stats.items():
    print(f"{strat_name:12s}  {s['oos_sh_mean']:7.3f}  {s['oos_sh_median']:7.3f}  "
          f"{s['oos_sh_std']:5.3f}  {s['oos_sh_min']:7.3f}  {s['oos_sh_max']:7.3f}  "
          f"{s['oos_sh_p10']:7.3f}  {s['oos_sh_p90']:7.3f}")

print(f"\nDone in {elapsed}s")

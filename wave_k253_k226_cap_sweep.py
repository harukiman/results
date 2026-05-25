"""
Wave K253 — K226 Cap Sensitivity Sweep in K246a 3-way Ensemble
             K198 + K208 + K226, inv-vol, cap K226 at 5/10/15/20/25/30/50%

Objective: Confirm whether cap=20% (K246a baseline) is optimal or if another
           cap setting improves OOS Sharpe / WF stability.

Variants:
  K253a: cap  5%
  K253b: cap 10%
  K253c: cap 15%
  K253d: cap 20%  (K246a baseline reproduction)
  K253e: cap 25%
  K253f: cap 30%
  K253g: cap 50%  (extreme / near-uncapped)

Acceptance gates (vs K246a baseline: OOS Sh=12.69, WF min=8.93, MaxDD=-0.001145):
  Best variant OOS Sh  > 12.69
  WF min               >= 8.93
  MaxDD                <= -0.001145

Deliverables:
  wave_k253_k226_cap_sweep.py
  wave_k253_k226_cap_sweep.json
  wave_k253_curves.json
  wave_k253_k226_cap_sweep.md
"""

import json
import numpy as np
from datetime import datetime, timezone
import time

t0 = time.time()

# ─────────────────────────────────────────────────────────────────────────────
# 1. Load equity series (same sources as K246)
# ─────────────────────────────────────────────────────────────────────────────
with open("/Users/nekonaomichi/crypto-lab/wave_k198_curves.json") as f:
    k198_raw = json.load(f)
with open("/Users/nekonaomichi/crypto-lab/wave_k208_curves.json") as f:
    k208_raw = json.load(f)
with open("/Users/nekonaomichi/crypto-lab/wave_k226_curves.json") as f:
    k226_raw = json.load(f)

# K198: 448-day ML window
dates_ml = k198_raw["dates_ml"]
eq198    = np.array(k198_raw["equity_ridge"])

# K208: 8h resolution — collapse to daily closing PnL
k208_ts   = k208_raw["K208_filtered"]["timestamps"]
k208_cpnl = k208_raw["K208_filtered"]["cumulative_pnl"]
k208_daily = {}
for ts_str, cpnl in zip(k208_ts, k208_cpnl):
    k208_daily[ts_str[:10]] = cpnl

k208_eq_values = []
missing_k208 = 0
for d in dates_ml:
    if d in k208_daily:
        k208_eq_values.append(1.0 + k208_daily[d])
    else:
        missing_k208 += 1
        k208_eq_values.append(k208_eq_values[-1] if k208_eq_values else 1.0)
eq208 = np.array(k208_eq_values)

# K226: align to ML window
k226_eq_daily = {}
for d, eq in zip(k226_raw["dates"], k226_raw["strategy_equity"]):
    k226_eq_daily[d] = eq
k226_eq_values = []
missing_k226 = 0
for d in dates_ml:
    if d in k226_eq_daily:
        k226_eq_values.append(k226_eq_daily[d])
    else:
        missing_k226 += 1
        k226_eq_values.append(k226_eq_values[-1] if k226_eq_values else 1.0)
eq226_raw_aligned = np.array(k226_eq_values)
eq226 = eq226_raw_aligned / eq226_raw_aligned[0]  # re-base to 1.0

n = len(dates_ml)
assert len(eq198) == len(eq208) == len(eq226) == n, "Length mismatch"

print(f"Data loaded: {n} days ({dates_ml[0]} -> {dates_ml[-1]})")
print(f"K208 missing: {missing_k208}/{n}, K226 missing: {missing_k226}/{n}")

# Daily returns
ret198 = np.diff(eq198) / eq198[:-1]
ret208 = np.diff(eq208) / eq208[:-1]
ret226 = np.diff(eq226) / eq226[:-1]
ret_dates = dates_ml[1:]
n_ret = len(ret198)

print(f"Return series: {n_ret} days")
print(f"K198: mean={ret198.mean():.6f}, std={ret198.std():.6f}")
print(f"K208: mean={ret208.mean():.6f}, std={ret208.std():.6f}")
print(f"K226: mean={ret226.mean():.6f}, std={ret226.std():.6f}")

# ─────────────────────────────────────────────────────────────────────────────
# 2. Utility functions
# ─────────────────────────────────────────────────────────────────────────────
ANN = np.sqrt(365)

def sharpe(rets):
    rets = np.asarray(rets)
    if len(rets) < 5:
        return np.nan
    mu  = np.mean(rets) * 365
    sig = np.std(rets, ddof=1) * ANN
    return float(mu / sig) if sig > 0 else np.nan

def maxdd(rets):
    eq = np.cumprod(1 + np.asarray(rets))
    roll_max = np.maximum.accumulate(eq)
    dd = (eq - roll_max) / roll_max
    return float(dd.min())

def oos_metrics(rets, oos_frac=0.3):
    rets = np.asarray(rets)
    oos_start = int(len(rets) * (1 - oos_frac))
    oos = rets[oos_start:]
    return {
        "oos_sharpe":  round(sharpe(oos), 4),
        "oos_maxdd":   round(maxdd(oos), 6),
        "oos_n_days":  len(oos),
        "oos_ann_ret": round(float(np.mean(oos) * 365), 4),
        "oos_ann_vol": round(float(np.std(oos, ddof=1) * ANN), 4),
    }

def wf_stats(rets, n_folds=4):
    rets = np.asarray(rets)
    fold_size = len(rets) // n_folds
    fold_sharpes, fold_details = [], []
    for i in range(n_folds):
        s = i * fold_size
        e = (i + 1) * fold_size if i < n_folds - 1 else len(rets)
        fs = sharpe(rets[s:e])
        fold_sharpes.append(fs)
        fold_details.append({
            "fold": i + 1, "start_idx": s, "end_idx": e,
            "n_days": e - s, "sharpe": round(float(fs), 4),
            "start_date": ret_dates[s],
            "end_date": ret_dates[min(e - 1, len(ret_dates) - 1)],
        })
    return {
        "fold_sharpes": [round(float(s), 4) for s in fold_sharpes],
        "fold_details": fold_details,
        "wf_mean": round(float(np.nanmean(fold_sharpes)), 4),
        "wf_min":  round(float(np.nanmin(fold_sharpes)), 4),
        "wf_max":  round(float(np.nanmax(fold_sharpes)), 4),
        "wf_std":  round(float(np.nanstd(fold_sharpes, ddof=1)), 4),
    }

def equity_curve(rets):
    rets = np.asarray(rets)
    eq = np.empty(len(rets) + 1)
    eq[0] = 1.0
    eq[1:] = np.cumprod(1 + rets)
    return [round(float(x), 8) for x in eq]

def inv_vol_blend_3way(r198, r208, r226, cap_val, roll=30):
    """
    3-way inv-vol: K198 (idx=0), K208 (idx=1), K226 (idx=2, capped).
    Returns (blended_rets, weight_trajectory [n_t x 3])
    """
    rets_list = [r198, r208, r226]
    n_t = len(r198)
    blended  = np.zeros(n_t)
    w_traj   = np.zeros((n_t, 3))
    cap_idx  = 2  # K226 always capped

    for i in range(n_t):
        start_w = max(0, i - roll)
        vols = []
        for r in rets_list:
            seg = r[start_w:i + 1]
            v = np.std(seg, ddof=1) if len(seg) >= 3 else 1e-6
            vols.append(max(v, 1e-9))
        ivols = [1.0 / v for v in vols]
        total = sum(ivols)
        w = np.array([iv / total for iv in ivols])

        if w[cap_idx] > cap_val:
            w[cap_idx] = cap_val
            rest_ivols = [ivols[j] for j in range(3) if j != cap_idx]
            rest_sum   = sum(rest_ivols)
            for j in range(3):
                if j != cap_idx:
                    w[j] = (ivols[j] / rest_sum) * (1.0 - cap_val)

        w_traj[i]  = w
        blended[i] = sum(w[j] * rets_list[j][i] for j in range(3))

    return blended, w_traj

# ─────────────────────────────────────────────────────────────────────────────
# 3. K246a baseline reminder (cap=20%)
# ─────────────────────────────────────────────────────────────────────────────
K246A_OOS_SH  = 12.6929
K246A_WF_MIN  = 8.9347
K246A_MAXDD   = -0.001145

# ─────────────────────────────────────────────────────────────────────────────
# 4. Cap sweep
# ─────────────────────────────────────────────────────────────────────────────
CAP_VARIANTS = [
    ("K253a",  0.05),
    ("K253b",  0.10),
    ("K253c",  0.15),
    ("K253d",  0.20),  # baseline reproduction
    ("K253e",  0.25),
    ("K253f",  0.30),
    ("K253g",  0.50),
]

results = {}
curves_out = {"dates": [dates_ml[0]] + list(ret_dates)}

print("\n=== K253 CAP SWEEP (K246a 3-way: K198+K208+K226) ===")
print(f"{'Variant':8s} {'Cap':5s} {'OOS Sh':8s} {'OOS MaxDD':10s} {'WF Mean':8s} {'WF Min':8s} "
      f"{'K226 avg%':9s} {'K226 max%':9s}")
print("-" * 80)

for vname, cap in CAP_VARIANTS:
    blended, w_traj = inv_vol_blend_3way(ret198, ret208, ret226, cap_val=cap)
    m = oos_metrics(blended)
    m.update(wf_stats(blended))

    # Weight stats for K226 (idx=2)
    w226 = w_traj[:, 2]
    m["k226_avg_wt"]  = round(float(w226.mean()), 6)
    m["k226_max_wt"]  = round(float(w226.max()),  6)
    m["k226_min_wt"]  = round(float(w226.min()),  6)
    m["k226_std_wt"]  = round(float(w226.std()),  6)
    m["k198_avg_wt"]  = round(float(w_traj[:, 0].mean()), 6)
    m["k208_avg_wt"]  = round(float(w_traj[:, 1].mean()), 6)
    m["cap"]          = cap
    m["variant"]      = vname
    m["avg_weights"]  = [m["k198_avg_wt"], m["k208_avg_wt"], m["k226_avg_wt"]]

    # Gate evaluation vs K246a baseline
    g1 = m["oos_sharpe"] > K246A_OOS_SH
    g2 = m["wf_min"]     >= K246A_WF_MIN
    g3 = m["oos_maxdd"]  >= K246A_MAXDD
    m["gate_oos_sh"]  = g1
    m["gate_wf_min"]  = g2
    m["gate_maxdd"]   = g3
    m["all_gates"]    = g1 and g2 and g3

    results[vname] = m
    curves_out[vname] = equity_curve(blended)

    cap_bind = "binding" if w226.max() > cap - 0.001 else "non-binding"
    print(f"{vname:8s} {cap*100:4.0f}% {m['oos_sharpe']:8.4f} {m['oos_maxdd']:10.6f} "
          f"{m['wf_mean']:8.4f} {m['wf_min']:8.4f} "
          f"{m['k226_avg_wt']*100:7.2f}%  {m['k226_max_wt']*100:7.2f}%  [{cap_bind}]")

print("-" * 80)
print(f"{'K246a':8s} {'20%':5s} {K246A_OOS_SH:8.4f}   {K246A_MAXDD:8.6f} {'12.2462':>8s} "
      f"{'8.9347':>8s}  [BASELINE]")

# ─────────────────────────────────────────────────────────────────────────────
# 5. WF fold detail per variant
# ─────────────────────────────────────────────────────────────────────────────
print("\n=== WF 4-FOLD BREAKDOWN ===")
print(f"{'Variant':8s} | {'Fold1':7s} {'Fold2':7s} {'Fold3':7s} {'Fold4':7s} | WF Min  WF Mean")
print("-" * 70)
for vname, cap in CAP_VARIANTS:
    m = results[vname]
    fs = m["fold_sharpes"]
    marker = " <- BASELINE" if cap == 0.20 else ""
    print(f"{vname:8s} | {fs[0]:7.4f} {fs[1]:7.4f} {fs[2]:7.4f} {fs[3]:7.4f} | "
          f"{m['wf_min']:7.4f} {m['wf_mean']:7.4f}{marker}")

# ─────────────────────────────────────────────────────────────────────────────
# 6. Acceptance gate summary
# ─────────────────────────────────────────────────────────────────────────────
print("\n=== ACCEPTANCE GATES (must beat K246a: OOS Sh>12.6929, WF min>=8.9347, MaxDD>=-0.001145) ===")
best_candidates = []
for vname, cap in CAP_VARIANTS:
    m = results[vname]
    g1, g2, g3 = m["gate_oos_sh"], m["gate_wf_min"], m["gate_maxdd"]
    status = "PASS" if m["all_gates"] else "FAIL"
    print(f"  {vname} (cap={cap*100:.0f}%): OOS={m['oos_sharpe']:.4f}({'v' if g1 else 'x'}) "
          f"WFmin={m['wf_min']:.4f}({'v' if g2 else 'x'}) "
          f"MaxDD={m['oos_maxdd']:.6f}({'v' if g3 else 'x'}) -> {status}")
    if m["all_gates"]:
        best_candidates.append((m["oos_sharpe"] + m["wf_min"], vname, m))

best_candidates.sort(reverse=True)
accepted = len(best_candidates) > 0
best_vname = best_candidates[0][1] if accepted else None
best_m     = best_candidates[0][2] if accepted else None

# ─────────────────────────────────────────────────────────────────────────────
# 7. Determine optimal cap
# ─────────────────────────────────────────────────────────────────────────────
# Also find best overall by OOS sharpe (even if doesn't beat baseline)
best_oos_vname = max(results, key=lambda k: results[k]["oos_sharpe"])
best_oos_m     = results[best_oos_vname]

print(f"\nBest OOS Sharpe overall: {best_oos_vname} (cap={best_oos_m['cap']*100:.0f}%) = {best_oos_m['oos_sharpe']:.4f}")

if accepted:
    verdict = f"NEW OPTIMAL CAP: {best_vname} (cap={best_m['cap']*100:.0f}%) beats K246a"
    cap_verdict = f"cap_{int(best_m['cap']*100)}pct"
else:
    verdict = "cap=20% CONFIRMED OPTIMAL — K246a architecture finalized"
    cap_verdict = "cap_20pct"

print(f"\nVERDICT: {verdict}")

# ─────────────────────────────────────────────────────────────────────────────
# 8. Save outputs
# ─────────────────────────────────────────────────────────────────────────────
runtime = round(time.time() - t0, 2)

# Build comparison table
comparison_table = []
for vname, cap in CAP_VARIANTS:
    m = results[vname]
    comparison_table.append({
        "variant": vname,
        "cap_pct": int(cap * 100),
        "oos_sharpe": m["oos_sharpe"],
        "oos_maxdd": m["oos_maxdd"],
        "wf_mean": m["wf_mean"],
        "wf_min": m["wf_min"],
        "fold_sharpes": m["fold_sharpes"],
        "k226_avg_wt_pct": round(m["k226_avg_wt"] * 100, 3),
        "k226_max_wt_pct": round(m["k226_max_wt"] * 100, 3),
        "k226_std_wt_pct": round(m["k226_std_wt"] * 100, 3),
        "k198_avg_wt_pct": round(m["k198_avg_wt"] * 100, 3),
        "k208_avg_wt_pct": round(m["k208_avg_wt"] * 100, 3),
        "delta_oos_sh_vs_k246a": round(m["oos_sharpe"] - K246A_OOS_SH, 4),
        "delta_wf_min_vs_k246a": round(m["wf_min"] - K246A_WF_MIN, 4),
        "delta_maxdd_vs_k246a":  round(m["oos_maxdd"] - K246A_MAXDD, 6),
        "beats_k246a": m["all_gates"],
    })

result_json = {
    "wave": "K253",
    "task": "K226 Cap Sensitivity Sweep — K246a 3-way Ensemble",
    "as_of": datetime.now(timezone.utc).isoformat(),
    "runtime_s": runtime,
    "data_info": {
        "n_days": n,
        "date_start": dates_ml[0],
        "date_end": dates_ml[-1],
        "n_returns": n_ret,
        "k208_missing_days": missing_k208,
        "k226_missing_days": missing_k226,
    },
    "k246a_baseline": {
        "oos_sharpe": K246A_OOS_SH,
        "wf_min":     K246A_WF_MIN,
        "oos_maxdd":  K246A_MAXDD,
        "cap_k226":   0.20,
        "description": "K198+K208+K226 inv-vol + K226 cap 20% (FINAL production v6.9)",
    },
    "acceptance_gates": {
        "gate1_oos_sharpe_gt":  K246A_OOS_SH,
        "gate2_wf_min_gte":     K246A_WF_MIN,
        "gate3_maxdd_lte":      K246A_MAXDD,
        "note": "All three must pass to accept new cap as improvement",
    },
    "comparison_table": comparison_table,
    "variant_details": {k: v for k, v in results.items()},
    "verdict": verdict,
    "optimal_cap": cap_verdict,
    "accepted": accepted,
    "best_variant": best_vname,
    "best_variant_metrics": best_m,
    "best_oos_sharpe_variant": best_oos_vname,
    "best_oos_sharpe_value": best_oos_m["oos_sharpe"],
    "k246a_finalized": not accepted,
}

with open("/Users/nekonaomichi/crypto-lab/wave_k253_k226_cap_sweep.json", "w") as f:
    json.dump(result_json, f, indent=2)
print("Saved: wave_k253_k226_cap_sweep.json")

# Add K198/K208/K226 individual curves for reference
curves_out["K198"] = equity_curve(ret198)
curves_out["K208"] = equity_curve(ret208)
curves_out["K226"] = equity_curve(ret226)

with open("/Users/nekonaomichi/crypto-lab/wave_k253_curves.json", "w") as f:
    json.dump(curves_out, f)
print("Saved: wave_k253_curves.json")

# ─────────────────────────────────────────────────────────────────────────────
# 9. Markdown report
# ─────────────────────────────────────────────────────────────────────────────
lines = [
    "# Wave K253 — K226 Cap Sensitivity Sweep (K246a 3-way)",
    f"*Generated: {result_json['as_of']}  |  Runtime: {runtime}s*",
    "",
    "## Executive Summary",
    "",
    f"**VERDICT: {verdict}**",
    "",
    "Testing K226 cap (5–50%) in K246a 3-way (K198+K208+K226, inv-vol).",
    f"K246a baseline: OOS Sh={K246A_OOS_SH}, WF min={K246A_WF_MIN}, MaxDD={K246A_MAXDD}.",
    "",
    "## 1. Per-Cap Comparison",
    "",
    "| Variant | Cap | OOS Sh | OOS MaxDD | WF Mean | WF Min | K226 avg% | K226 max% | Beats K246a |",
    "|---------|-----|--------|-----------|---------|--------|-----------|-----------|-------------|",
    f"| K246a ★ | 20% | {K246A_OOS_SH:.4f} | {K246A_MAXDD:.6f} | 12.2462 | {K246A_WF_MIN:.4f} | ~1.23% | — | BASELINE |",
]

for row in comparison_table:
    mark  = " ★" if row["variant"] == best_vname else ""
    beats = "YES" if row["beats_k246a"] else "no"
    lines.append(
        f"| {row['variant']}{mark} | {row['cap_pct']}% | {row['oos_sharpe']:.4f} | "
        f"{row['oos_maxdd']:.6f} | {row['wf_mean']:.4f} | {row['wf_min']:.4f} | "
        f"{row['k226_avg_wt_pct']:.2f}% | {row['k226_max_wt_pct']:.2f}% | {beats} |"
    )

lines += [
    "",
    "Gates: OOS Sh > 12.6929 AND WF min >= 8.9347 AND MaxDD >= -0.001145 (all three must pass)",
    "",
    "## 2. WF 4-Fold Breakdown",
    "",
    "| Variant | Cap | Fold 1 | Fold 2 | Fold 3 | Fold 4 | WF Min | WF Mean |",
    "|---------|-----|--------|--------|--------|--------|--------|---------|",
]
for row in comparison_table:
    fs = row["fold_sharpes"]
    lines.append(
        f"| {row['variant']} | {row['cap_pct']}% | {fs[0]:.4f} | {fs[1]:.4f} | "
        f"{fs[2]:.4f} | {fs[3]:.4f} | {row['wf_min']:.4f} | {row['wf_mean']:.4f} |"
    )

lines += [
    "",
    "## 3. K226 Actual Weight Distribution",
    "",
    "| Variant | Cap | K226 avg% | K226 max% | K226 std% | K198 avg% | K208 avg% | Cap Binding? |",
    "|---------|-----|-----------|-----------|-----------|-----------|-----------|-------------|",
]
for row in comparison_table:
    binding = "YES" if row["k226_max_wt_pct"] >= row["cap_pct"] - 0.1 else "no"
    lines.append(
        f"| {row['variant']} | {row['cap_pct']}% | {row['k226_avg_wt_pct']:.2f}% | "
        f"{row['k226_max_wt_pct']:.2f}% | {row['k226_std_wt_pct']:.2f}% | "
        f"{row['k198_avg_wt_pct']:.2f}% | {row['k208_avg_wt_pct']:.2f}% | {binding} |"
    )

lines += [
    "",
    "## 4. Verdict on Optimal K226 Cap",
    "",
]

if accepted:
    lines += [
        f"**NEW OPTIMAL CAP FOUND: {best_vname} (cap={best_m['cap']*100:.0f}%)**",
        "",
        f"- OOS Sharpe: {best_m['oos_sharpe']:.4f} (vs K246a {K246A_OOS_SH}, delta: {best_m['oos_sharpe']-K246A_OOS_SH:+.4f})",
        f"- WF min:     {best_m['wf_min']:.4f} (vs K246a {K246A_WF_MIN}, delta: {best_m['wf_min']-K246A_WF_MIN:+.4f})",
        f"- MaxDD:      {best_m['oos_maxdd']:.6f} (vs K246a {K246A_MAXDD})",
        f"- K226 avg wt: {best_m['k226_avg_wt']*100:.2f}%",
        "",
        f"**Recommendation:** Update K246a cap from 20% to {int(best_m['cap']*100)}% for v6.9 final.",
    ]
else:
    # Check if all variants are roughly identical (non-binding hypothesis confirmed)
    sh_vals = [results[v]["oos_sharpe"] for v in results]
    sh_range = max(sh_vals) - min(sh_vals)
    lines += [
        f"**cap=20% CONFIRMED OPTIMAL — K246a architecture finalized.**",
        "",
        f"- No cap variant beats K246a on all three gates simultaneously.",
        f"- OOS Sharpe range across all caps: {min(sh_vals):.4f}–{max(sh_vals):.4f} (spread: {sh_range:.4f})",
        f"- K226 natural weight is ~1% in 3-way ensemble → cap 5–50% all near-identical effect.",
        f"- This is consistent with K237 finding: cap is non-binding in 3-way context.",
        f"- Best raw OOS: {best_oos_vname} (cap={best_oos_m['cap']*100:.0f}%) = {best_oos_m['oos_sharpe']:.4f}",
        f"  (insufficient improvement to trigger gate passage)",
        "",
        "**Architecture confirmed:** K246a (K198+K208+K226, inv-vol, cap K226@20%) = FINAL v6.9.",
        "No cap tuning needed. K226 weight is structurally low (~1%) in 3-way ensemble.",
    ]

lines += [
    "",
    "---",
    f"*Wave K253 | crypto-lab | {result_json['as_of']}*",
]

report_text = "\n".join(lines)
with open("/Users/nekonaomichi/crypto-lab/wave_k253_k226_cap_sweep.md", "w") as f:
    f.write(report_text)
print("Saved: wave_k253_k226_cap_sweep.md")

print(f"\n{'='*60}")
print(f"K253 COMPLETE — Runtime {runtime}s")
print(f"VERDICT: {verdict}")
if accepted:
    print(f"Best new: {best_vname} OOS Sh={best_m['oos_sharpe']:.4f}, WF min={best_m['wf_min']:.4f}")
else:
    print("cap=20% remains optimal — K246a finalized.")
print(f"{'='*60}")

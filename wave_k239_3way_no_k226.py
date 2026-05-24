"""
Wave K239 — 3-Way Meta-Ensemble Validation: K198 × K204 × K208 (no K226)

K237g finding: dropping K226 from K229 INCREASES OOS Sh from 12.61 -> 12.858 (+0.25)
This wave formally validates whether K198+K204+K208 (no K226) is a better
production configuration than K229d (K198+K204+K208+K226, 4-way).

K226 context: cap parameter (5-30%) had ZERO effect — natural weight 0.7-1.4%.
K237g achilles heel: "Remove K226" degradation = -1.12 Sh, confirming it adds noise.

Variants:
  K239a — Inv-vol weighted (30d rolling)          [mirrors K229b without K226]
  K239b — Inv-vol + K208 cap 30%                  [mirror K218e allocator]
  K239c — MVP (Minimum Variance Portfolio)
  K239d — Equal weight 33/33/33

Acceptance gates vs K229d v6.8 (simplification upgrade):
  Best variant OOS Sh >= 12.61   (K229d)
  WF min >= 7.44                 (K229d min fold)
  MaxDD <= -0.0012               (K229d)
  Simpler architecture (3 components vs 4)

Same ML window as K229: 448 days, 2025-01-22 -> 2026-04-14
"""

import json
import numpy as np
from datetime import datetime, timezone
import time

t0 = time.time()

# ─────────────────────────────────────────────────────────────────────────────
# 1. Load equity series (K198, K204, K208 only — no K226)
# ─────────────────────────────────────────────────────────────────────────────
with open("/Users/nekonaomichi/crypto-lab/wave_k198_curves.json") as f:
    k198_raw = json.load(f)
with open("/Users/nekonaomichi/crypto-lab/wave_k204_curves.json") as f:
    k204_raw = json.load(f)
with open("/Users/nekonaomichi/crypto-lab/wave_k208_curves.json") as f:
    k208_raw = json.load(f)

# 448-day ML window: 2025-01-22 -> 2026-04-14
dates_ml = k198_raw["dates_ml"]
eq198    = np.array(k198_raw["equity_ridge"])
eq204    = np.array(k204_raw["equity_k204"])

# K208 is 8h resolution — collapse to daily closing PnL (same method as K229)
k208_ts   = k208_raw["K208_filtered"]["timestamps"]
k208_cpnl = k208_raw["K208_filtered"]["cumulative_pnl"]

k208_daily = {}
for ts_str, cpnl in zip(k208_ts, k208_cpnl):
    date_part = ts_str[:10]
    k208_daily[date_part] = cpnl  # last entry of day wins

k208_eq_values = []
missing_k208 = 0
for d in dates_ml:
    if d in k208_daily:
        k208_eq_values.append(1.0 + k208_daily[d])
    else:
        missing_k208 += 1
        if k208_eq_values:
            k208_eq_values.append(k208_eq_values[-1])
        else:
            k208_eq_values.append(1.0)

eq208 = np.array(k208_eq_values)

n = len(dates_ml)
assert len(eq198) == len(eq204) == len(eq208) == n, (
    f"Length mismatch: K198={len(eq198)}, K204={len(eq204)}, K208={len(eq208)}, dates={n}"
)

print(f"Data loaded: {n} days ({dates_ml[0]} -> {dates_ml[-1]})")
print(f"K208 missing days filled forward: {missing_k208}/{n}")
print(f"K198 equity range: [{eq198.min():.4f}, {eq198.max():.4f}]")
print(f"K204 equity range: [{eq204.min():.4f}, {eq204.max():.4f}]")
print(f"K208 equity range: [{eq208.min():.4f}, {eq208.max():.4f}]")

# Daily returns (geometric)
ret198 = np.diff(eq198) / eq198[:-1]
ret204 = np.diff(eq204) / eq204[:-1]
ret208 = np.diff(eq208) / eq208[:-1]
ret_dates = dates_ml[1:]   # n-1 return dates
n_ret = len(ret198)

print(f"\nReturn series length: {n_ret}")
print(f"K198 daily ret: mean={ret198.mean():.6f}, std={ret198.std():.6f}")
print(f"K204 daily ret: mean={ret204.mean():.6f}, std={ret204.std():.6f}")
print(f"K208 daily ret: mean={ret208.mean():.6f}, std={ret208.std():.6f}")

# ─────────────────────────────────────────────────────────────────────────────
# 2. Utility functions (identical to K229)
# ─────────────────────────────────────────────────────────────────────────────
ANN = np.sqrt(365)

def sharpe(rets):
    if len(rets) < 5:
        return np.nan
    mu  = np.mean(rets) * 365
    sig = np.std(rets, ddof=1) * ANN
    return float(mu / sig) if sig > 0 else np.nan

def maxdd(rets):
    eq = np.cumprod(1 + np.array(rets))
    roll_max = np.maximum.accumulate(eq)
    dd = (eq - roll_max) / roll_max
    return float(dd.min())

def wf_stats(rets, n_folds=4):
    fold_size = len(rets) // n_folds
    fold_sharpes = []
    fold_details = []
    for i in range(n_folds):
        start = i * fold_size
        end   = (i + 1) * fold_size if i < n_folds - 1 else len(rets)
        fs = sharpe(rets[start:end])
        fold_sharpes.append(fs)
        fold_details.append({
            "fold":      i + 1,
            "start_idx": start,
            "end_idx":   end,
            "n_days":    end - start,
            "sharpe":    round(float(fs), 4),
        })
    return {
        "fold_sharpes": [round(s, 4) for s in fold_sharpes],
        "fold_details": fold_details,
        "wf_mean":      round(float(np.mean(fold_sharpes)), 4),
        "wf_min":       round(float(np.min(fold_sharpes)), 4),
        "wf_max":       round(float(np.max(fold_sharpes)), 4),
        "wf_std":       round(float(np.std(fold_sharpes, ddof=1)), 4),
    }

def oos_metrics(rets, oos_frac=0.3):
    oos_start = int(len(rets) * (1 - oos_frac))
    oos_rets  = rets[oos_start:]
    return {
        "oos_sharpe":  round(sharpe(oos_rets), 4),
        "oos_maxdd":   round(maxdd(oos_rets), 6),
        "oos_n_days":  len(oos_rets),
        "oos_ann_ret": round(float(np.mean(oos_rets) * 365), 4),
        "oos_ann_vol": round(float(np.std(oos_rets, ddof=1) * ANN), 4),
    }

def equity_curve(rets):
    eq = np.empty(len(rets) + 1)
    eq[0] = 1.0
    eq[1:] = np.cumprod(1 + rets)
    return eq.tolist()

def diversification_ratio(w, rets_matrix):
    w = np.array(w)
    individual_vols = np.array([np.std(r, ddof=1) for r in rets_matrix])
    weighted_vol_sum = float(np.dot(w, individual_vols))
    port_rets = np.dot(w, rets_matrix)
    port_vol  = float(np.std(port_rets, ddof=1))
    if port_vol < 1e-12:
        return np.nan
    return round(weighted_vol_sum / port_vol, 4)

def mvp_weights_3(cov_matrix):
    ones = np.ones(3)
    try:
        sigma_inv = np.linalg.inv(cov_matrix)
        w_raw = sigma_inv @ ones
        w_raw = np.maximum(w_raw, 0.0)
        s = w_raw.sum()
        if s < 1e-12:
            return np.array([1/3, 1/3, 1/3])
        return w_raw / s
    except np.linalg.LinAlgError:
        return np.array([1/3, 1/3, 1/3])

# ─────────────────────────────────────────────────────────────────────────────
# 3. Baseline metrics (K198, K204, K208 standalone on ML window)
# ─────────────────────────────────────────────────────────────────────────────
print("\n--- Baseline metrics (on ML-window returns) ---")
rets_all = np.stack([ret198, ret204, ret208], axis=0)  # (3, T)
baseline = {}
for name, rets in [("K198", ret198), ("K204", ret204), ("K208", ret208)]:
    m = oos_metrics(rets)
    m.update(wf_stats(rets))
    baseline[name] = m
    print(f"{name}: OOS Sh={m['oos_sharpe']:.4f}  MaxDD={m['oos_maxdd']:.6f}  "
          f"WF mean={m['wf_mean']:.4f}  WF min={m['wf_min']:.4f}")

# 3x3 correlation
rho_matrix = np.corrcoef(rets_all)
labels3 = ["K198", "K204", "K208"]
rho_198_204 = float(rho_matrix[0, 1])
rho_198_208 = float(rho_matrix[0, 2])
rho_204_208 = float(rho_matrix[1, 2])
print(f"\nCorrelations: K198-K204={rho_198_204:.4f}, K198-K208={rho_198_208:.4f}, K204-K208={rho_204_208:.4f}")

# ─────────────────────────────────────────────────────────────────────────────
# 4. 3-Way meta-allocator variants (K239a–K239d)
# ─────────────────────────────────────────────────────────────────────────────
variants     = {}
variant_rets = {}

ROLL     = 30   # rolling window for inv-vol weighting
ROLL_MVP = 60   # rolling window for MVP

# ── K239a: Inv-vol weighted (30d rolling) ────────────────────────────────────
print("\n--- K239a: Inv-vol weighted (30d rolling) ---")
inv_vol_rets_a = np.zeros(n_ret)
w_traj_a       = np.zeros((n_ret, 3))
for i in range(n_ret):
    start_w = max(0, i - ROLL)
    v198 = np.std(ret198[start_w:i+1], ddof=1) if i - start_w >= 2 else 1e-6
    v204 = np.std(ret204[start_w:i+1], ddof=1) if i - start_w >= 2 else 1e-6
    v208 = np.std(ret208[start_w:i+1], ddof=1) if i - start_w >= 2 else 1e-6
    iv198 = 1.0 / max(v198, 1e-9)
    iv204 = 1.0 / max(v204, 1e-9)
    iv208 = 1.0 / max(v208, 1e-9)
    total = iv198 + iv204 + iv208
    wa = np.array([iv198/total, iv204/total, iv208/total])
    w_traj_a[i] = wa
    inv_vol_rets_a[i] = wa[0]*ret198[i] + wa[1]*ret204[i] + wa[2]*ret208[i]

m = oos_metrics(inv_vol_rets_a)
m.update(wf_stats(inv_vol_rets_a))
m["description"]           = "Inv-vol weighted (30d rolling)"
m["avg_weights"]           = [round(float(w_traj_a[:,j].mean()), 4) for j in range(3)]
m["diversification_ratio"] = diversification_ratio(w_traj_a.mean(axis=0), rets_all)
variants["K239a"]     = m
variant_rets["K239a"] = inv_vol_rets_a
print(f"K239a: OOS Sh={m['oos_sharpe']:.4f}  MaxDD={m['oos_maxdd']:.6f}  "
      f"WF mean={m['wf_mean']:.4f}  WF min={m['wf_min']:.4f}  DR={m['diversification_ratio']:.4f}")
print(f"       Avg weights: K198={m['avg_weights'][0]:.3f}, K204={m['avg_weights'][1]:.3f}, K208={m['avg_weights'][2]:.3f}")

# ── K239b: Inv-vol + K208 cap 30% ────────────────────────────────────────────
print("\n--- K239b: Inv-vol + K208 cap 30% (30d rolling) ---")
CAP208_B       = 0.30
inv_vol_rets_b = np.zeros(n_ret)
w_traj_b       = np.zeros((n_ret, 3))
for i in range(n_ret):
    start_w = max(0, i - ROLL)
    v198 = np.std(ret198[start_w:i+1], ddof=1) if i - start_w >= 2 else 1e-6
    v204 = np.std(ret204[start_w:i+1], ddof=1) if i - start_w >= 2 else 1e-6
    v208 = np.std(ret208[start_w:i+1], ddof=1) if i - start_w >= 2 else 1e-6
    iv198 = 1.0 / max(v198, 1e-9)
    iv204 = 1.0 / max(v204, 1e-9)
    iv208 = 1.0 / max(v208, 1e-9)
    total = iv198 + iv204 + iv208
    wb = np.array([iv198/total, iv204/total, iv208/total])
    # Apply K208 cap at 30%
    if wb[2] > CAP208_B:
        wb[2] = CAP208_B
        iv_rest = np.array([iv198, iv204])
        wb[:2] = iv_rest / iv_rest.sum() * (1.0 - CAP208_B)
    w_traj_b[i] = wb
    inv_vol_rets_b[i] = wb[0]*ret198[i] + wb[1]*ret204[i] + wb[2]*ret208[i]

m = oos_metrics(inv_vol_rets_b)
m.update(wf_stats(inv_vol_rets_b))
m["description"]           = "Inv-vol weighted (30d rolling) + K208 cap 30%"
m["avg_weights"]           = [round(float(w_traj_b[:,j].mean()), 4) for j in range(3)]
m["diversification_ratio"] = diversification_ratio(w_traj_b.mean(axis=0), rets_all)
variants["K239b"]     = m
variant_rets["K239b"] = inv_vol_rets_b
print(f"K239b: OOS Sh={m['oos_sharpe']:.4f}  MaxDD={m['oos_maxdd']:.6f}  "
      f"WF mean={m['wf_mean']:.4f}  WF min={m['wf_min']:.4f}  DR={m['diversification_ratio']:.4f}")
print(f"       Avg weights: K198={m['avg_weights'][0]:.3f}, K204={m['avg_weights'][1]:.3f}, K208={m['avg_weights'][2]:.3f}")

# ── K239c: MVP (Minimum Variance Portfolio, rolling 60d covariance) ───────────
print("\n--- K239c: MVP (rolling 60d covariance, long-only) ---")
mvp_rets_c = np.zeros(n_ret)
w_traj_c   = np.zeros((n_ret, 3))
for i in range(n_ret):
    start_w = max(0, i - ROLL_MVP)
    seg = np.stack([
        ret198[start_w:i+1],
        ret204[start_w:i+1],
        ret208[start_w:i+1],
    ], axis=0)
    if seg.shape[1] >= 5:
        cov = np.cov(seg)
        wc  = mvp_weights_3(cov)
    else:
        wc = np.array([1/3, 1/3, 1/3])
    w_traj_c[i] = wc
    mvp_rets_c[i] = wc[0]*ret198[i] + wc[1]*ret204[i] + wc[2]*ret208[i]

m = oos_metrics(mvp_rets_c)
m.update(wf_stats(mvp_rets_c))
m["description"]           = "Minimum Variance Portfolio (rolling 60d covariance)"
m["avg_weights"]           = [round(float(w_traj_c[:,j].mean()), 4) for j in range(3)]
m["diversification_ratio"] = diversification_ratio(w_traj_c.mean(axis=0), rets_all)
variants["K239c"]     = m
variant_rets["K239c"] = mvp_rets_c
print(f"K239c: OOS Sh={m['oos_sharpe']:.4f}  MaxDD={m['oos_maxdd']:.6f}  "
      f"WF mean={m['wf_mean']:.4f}  WF min={m['wf_min']:.4f}  DR={m['diversification_ratio']:.4f}")
print(f"       Avg weights: K198={m['avg_weights'][0]:.3f}, K204={m['avg_weights'][1]:.3f}, K208={m['avg_weights'][2]:.3f}")

# ── K239d: Equal weight 33/33/33 ─────────────────────────────────────────────
print("\n--- K239d: Equal weight 33/33/33 ---")
w_eq  = np.array([1/3, 1/3, 1/3])
ret_d = w_eq[0]*ret198 + w_eq[1]*ret204 + w_eq[2]*ret208
m     = oos_metrics(ret_d)
m.update(wf_stats(ret_d))
m["description"]           = "Equal weight 33/33/33"
m["avg_weights"]           = [round(float(w), 4) for w in w_eq]
m["diversification_ratio"] = diversification_ratio(w_eq, rets_all)
variants["K239d"]     = m
variant_rets["K239d"] = ret_d
print(f"K239d: OOS Sh={m['oos_sharpe']:.4f}  MaxDD={m['oos_maxdd']:.6f}  "
      f"WF mean={m['wf_mean']:.4f}  WF min={m['wf_min']:.4f}  DR={m['diversification_ratio']:.4f}")

# ─────────────────────────────────────────────────────────────────────────────
# 5. Acceptance gates vs K229d v6.8 (simplification upgrade threshold)
# ─────────────────────────────────────────────────────────────────────────────
K229D_OOS_SH  = 12.61
K229D_WF_MIN  = 7.44   # fold_min from K229d: [12.8545, 7.4435, 12.9221, 12.4798]
K229D_MAXDD   = -0.001201
K229D_WF_MEAN = round((12.8545 + 7.4435 + 12.9221 + 12.4798) / 4, 4)

# Gates: K239 must be at least as good as K229d to justify simplification
GATE_OOS_SH = K229D_OOS_SH   # >= 12.61
GATE_WF_MIN = K229D_WF_MIN   # >= 7.44
GATE_MAXDD  = K229D_MAXDD    # <= -0.001201 (i.e., maxdd >= -0.001201)

print(f"\n--- Acceptance Gates (vs K229d v6.8) ---")
print(f"Gate 1: Best variant OOS Sh >= {GATE_OOS_SH:.4f}")
print(f"Gate 2: WF min >= {GATE_WF_MIN:.4f}")
print(f"Gate 3: MaxDD <= {GATE_MAXDD:.6f}")

candidates = []
for vname, vm in variants.items():
    sh_pass  = vm["oos_sharpe"] >= GATE_OOS_SH
    wf_pass  = vm["wf_min"] >= GATE_WF_MIN
    dd_pass  = vm["oos_maxdd"] >= GATE_MAXDD
    all_pass = sh_pass and wf_pass and dd_pass
    score    = vm["oos_sharpe"] + vm["wf_min"]

    print(f"  {vname}: OOS={vm['oos_sharpe']:.4f}({'v' if sh_pass else 'x'})  "
          f"WFmin={vm['wf_min']:.4f}({'v' if wf_pass else 'x'})  "
          f"MaxDD={vm['oos_maxdd']:.6f}({'v' if dd_pass else 'x'})  "
          f"-> {'PASS' if all_pass else 'FAIL'}")
    if all_pass:
        candidates.append((score, vname, vm))

candidates.sort(reverse=True)
best_name = candidates[0][1] if candidates else None
best_vm   = candidates[0][2] if candidates else None
accepted  = best_name is not None

# ─────────────────────────────────────────────────────────────────────────────
# 6. Build equity curves for output
# ─────────────────────────────────────────────────────────────────────────────
# K229d reference: inv-vol + K226 cap 20% (from K229 curves)
with open("/Users/nekonaomichi/crypto-lab/wave_k229_curves.json") as f:
    k229_curves = json.load(f)

curves = {
    "K198":      equity_curve(ret198),
    "K204":      equity_curve(ret204),
    "K208":      equity_curve(ret208),
    "K239a":     equity_curve(variant_rets["K239a"]),
    "K239b":     equity_curve(variant_rets["K239b"]),
    "K239c":     equity_curve(variant_rets["K239c"]),
    "K239d":     equity_curve(variant_rets["K239d"]),
    "K229d_ref": k229_curves["K229d"],   # 4-way K229d reference for comparison
    "dates":     [dates_ml[0]] + list(ret_dates),
}

# ─────────────────────────────────────────────────────────────────────────────
# 7. Save JSON outputs
# ─────────────────────────────────────────────────────────────────────────────
runtime = round(time.time() - t0, 2)

best_vm_report = best_vm if best_vm else max(variants.values(), key=lambda x: x["oos_sharpe"])
best_name_report = best_name if best_name else max(variants.items(), key=lambda x: x[1]["oos_sharpe"])[0]

if accepted:
    verdict = f"ACCEPT simplification to v6.8.1 — best variant: {best_name} (3-way, no K226)"
else:
    verdict = f"REJECT — no K239 variant meets K229d thresholds; maintain K229d v6.8"

fold_breakdown = {vname: vm["fold_details"] for vname, vm in variants.items()}

corr_mat_list = [[round(rho_matrix[i,j], 4) for j in range(3)] for i in range(3)]

# Synergy vs K229d
sh_best = best_vm_report["oos_sharpe"]
delta_vs_k229d = round(sh_best - K229D_OOS_SH, 4)
wf_delta = round(best_vm_report["wf_min"] - K229D_WF_MIN, 4)

result = {
    "wave":    "K239",
    "task":    "3-Way Meta-Ensemble Validation: K198 x K204 x K208 (no K226)",
    "as_of":   datetime.now(timezone.utc).isoformat(),
    "runtime_s": runtime,
    "data_info": {
        "n_days":            n,
        "date_start":        dates_ml[0],
        "date_end":          dates_ml[-1],
        "n_returns":         n_ret,
        "k208_missing_days": missing_k208,
        "rationale":         "K237g found K226 adds noise (natural weight 0.7-1.4%, cap 5-30% all equivalent)",
        "k237g_oos_sh":      12.858,
        "k237g_delta_vs_k229d": 0.248,
    },
    "correlation_matrix": {
        "labels": labels3,
        "matrix": corr_mat_list,
        "pairwise": {
            "rho_198_204": round(rho_198_204, 4),
            "rho_198_208": round(rho_198_208, 4),
            "rho_204_208": round(rho_204_208, 4),
        },
    },
    "acceptance_gates": {
        "gate1_oos_sharpe": GATE_OOS_SH,
        "gate2_wf_min":     GATE_WF_MIN,
        "gate3_maxdd":      GATE_MAXDD,
        "reference":        "K229d v6.8",
        "simplification":   "3 components vs 4 (drop K226)",
    },
    "baselines": baseline,
    "variants":  variants,
    "fold_breakdown": fold_breakdown,
    "comparison_k229d": {
        "k229d_oos_sh":   K229D_OOS_SH,
        "k229d_wf_min":   K229D_WF_MIN,
        "k229d_wf_mean":  K229D_WF_MEAN,
        "k229d_maxdd":    K229D_MAXDD,
        "best_k239_name": best_name_report,
        "best_k239_oos_sh": sh_best,
        "delta_oos_sh":   delta_vs_k229d,
        "best_k239_wf_min": best_vm_report["wf_min"],
        "delta_wf_min":   wf_delta,
        "best_k239_maxdd": best_vm_report["oos_maxdd"],
        "delta_maxdd":    round(best_vm_report["oos_maxdd"] - K229D_MAXDD, 6),
    },
    "verdict":       verdict,
    "accepted":      accepted,
    "best_variant":  best_name,
    "best_variant_metrics": best_vm,
}

with open("/Users/nekonaomichi/crypto-lab/wave_k239_3way_no_k226.json", "w") as f:
    json.dump(result, f, indent=2)
print("\nSaved: wave_k239_3way_no_k226.json")

with open("/Users/nekonaomichi/crypto-lab/wave_k239_curves.json", "w") as f:
    json.dump(curves, f)
print("Saved: wave_k239_curves.json")

print(f"\nRuntime: {runtime}s")
print(f"\nVERDICT: {verdict}")

# ─────────────────────────────────────────────────────────────────────────────
# 8. Generate Markdown report (SHORT — under 100 lines)
# ─────────────────────────────────────────────────────────────────────────────
comp = result["comparison_k229d"]

report_lines = [
    "# Wave K239 — 3-Way Meta-Ensemble Validation (no K226)",
    f"*Generated: {result['as_of']}  |  Runtime: {runtime}s*",
    "",
    f"## Verdict: {'ACCEPT v6.8.1 simplification' if accepted else 'REJECT — maintain K229d v6.8'}",
    "",
    "**K237g finding**: dropping K226 from K229 raises OOS Sh 12.61 → 12.858.",
    "**K239 objective**: formal validation with proper 3-way ensemble variants.",
    "",
    "## 4-Variant Comparison Table",
    "",
    "| Variant | Description | OOS Sh | MaxDD | WF Mean | WF Min | DR | K198/K204/K208 | Gate |",
    "|---------|-------------|--------|-------|---------|--------|----|-----------------|------|",
]
for vname, vm in variants.items():
    wts = vm["avg_weights"]
    sh_ok = vm["oos_sharpe"] >= GATE_OOS_SH
    wf_ok = vm["wf_min"] >= GATE_WF_MIN
    dd_ok = vm["oos_maxdd"] >= GATE_MAXDD
    gate = "PASS" if (sh_ok and wf_ok and dd_ok) else "FAIL"
    report_lines.append(
        f"| {vname} | {vm['description'][:28]} | {vm['oos_sharpe']:.4f} | "
        f"{vm['oos_maxdd']:.6f} | {vm['wf_mean']:.4f} | {vm['wf_min']:.4f} | "
        f"{vm['diversification_ratio']:.3f} | {wts[0]:.2f}/{wts[1]:.2f}/{wts[2]:.2f} | **{gate}** |"
    )

report_lines += [
    "",
    "## vs K229d Reference",
    "",
    "| Metric | K229d (4-way, with K226) | Best K239 | Delta |",
    "|--------|--------------------------|-----------|-------|",
    f"| OOS Sharpe | {K229D_OOS_SH:.4f} | {comp['best_k239_oos_sh']:.4f} ({comp['best_k239_name']}) | {comp['delta_oos_sh']:+.4f} |",
    f"| WF Min | {K229D_WF_MIN:.4f} | {comp['best_k239_wf_min']:.4f} | {comp['delta_wf_min']:+.4f} |",
    f"| WF Mean | {K229D_WF_MEAN:.4f} | {best_vm_report['wf_mean']:.4f} | {round(best_vm_report['wf_mean']-K229D_WF_MEAN,4):+.4f} |",
    f"| MaxDD | {K229D_MAXDD:.6f} | {comp['best_k239_maxdd']:.6f} | {comp['delta_maxdd']:+.6f} |",
    f"| Components | 4 | 3 | -1 (simpler) |",
    "",
    "## Per-Fold Breakdown (best variant)",
    "",
]
best_folds = best_vm_report["fold_sharpes"] if best_vm_report else [np.nan]*4
report_lines += [
    f"| Variant | Fold 1 | Fold 2 | Fold 3 | Fold 4 | WF Min | WF Mean |",
    "|---------|--------|--------|--------|--------|--------|---------|",
    f"| K229d (ref) | 12.8545 | 7.4435 | 12.9221 | 12.4798 | 7.4435 | {K229D_WF_MEAN:.4f} |",
    f"| {best_name_report} | {best_folds[0]:.4f} | {best_folds[1]:.4f} | {best_folds[2]:.4f} | {best_folds[3]:.4f} | {best_vm_report['wf_min']:.4f} | {best_vm_report['wf_mean']:.4f} |",
    "",
    "## All Variants Per-Fold",
    "",
    "| Variant | Fold 1 | Fold 2 | Fold 3 | Fold 4 | WF Min |",
    "|---------|--------|--------|--------|--------|--------|",
]
for vname, vm in variants.items():
    fs = vm["fold_sharpes"]
    report_lines.append(f"| {vname} | {fs[0]:.4f} | {fs[1]:.4f} | {fs[2]:.4f} | {fs[3]:.4f} | {vm['wf_min']:.4f} |")

report_lines += [
    "",
    f"## Verdict Line",
    "",
    f"**{verdict}**",
    "",
    f"Gates (vs K229d): OOS Sh >= {GATE_OOS_SH} | WF Min >= {GATE_WF_MIN} | MaxDD <= {GATE_MAXDD}",
    "",
    f"---",
    f"*Wave K239 | crypto-lab | {result['as_of']}*",
]

report_text = "\n".join(report_lines)
with open("/Users/nekonaomichi/crypto-lab/wave_k239_3way_no_k226.md", "w") as f:
    f.write(report_text)
print("Saved: wave_k239_3way_no_k226.md")

print(f"\n{'='*60}")
print(f"K239 COMPLETE — Runtime {runtime}s")
print(f"VERDICT: {verdict}")
print(f"{'='*60}")

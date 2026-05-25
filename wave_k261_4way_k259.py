"""
Wave K261 — K246a (K198+K208+K226) + K259 as 4th component
           4-way portfolio evaluation with multiple cap variants

Objective: Add K259 (K256_Ridge no-AXS) as 4th additive component to K246a.
           Gate 0: Validate K259 on K246a's exact ML window (448 days).
           Expected lift from K259's ρ=0.58 vs K208.

Variants:
  K261a: Inv-vol + K226 cap 20% (K246a methodology — 3-way baseline replication)
  K261b: K261a + K259 cap 15%
  K261c: K261a + K259 cap 20%
  K261d: K261a + K259 cap 25%
  K261e: Inv-vol uncapped (no caps, 4-way)
  K261f: MVP (minimum variance portfolio, 4-way)

Acceptance gates for K261 → v6.9.2 production:
  Gate 0: K259 ML window WF folds all positive
  OOS Sh > 12.79 (K246a 12.69 + 0.10)
  WF min >= 8.93
  MaxDD <= -0.00115
  All 4 components get non-zero weight

Deliverables:
  wave_k261_4way_k259.py
  wave_k261_4way_k259.json
  wave_k261_curves.json
  wave_k261_4way_k259.md
"""

import json
import numpy as np
from datetime import datetime, timezone
import time

t0 = time.time()

# ─────────────────────────────────────────────────────────────────────────────
# 1. Load equity series
# ─────────────────────────────────────────────────────────────────────────────
with open("/Users/nekonaomichi/crypto-lab/wave_k198_curves.json") as f:
    k198_raw = json.load(f)
with open("/Users/nekonaomichi/crypto-lab/wave_k208_curves.json") as f:
    k208_raw = json.load(f)
with open("/Users/nekonaomichi/crypto-lab/wave_k226_curves.json") as f:
    k226_raw = json.load(f)
with open("/Users/nekonaomichi/crypto-lab/wave_k259_curves.json") as f:
    k259_raw = json.load(f)

# ML window from K246a (448 days: 2025-01-22 -> 2026-04-14)
dates_ml = k198_raw["dates_ml"]
eq198 = np.array(k198_raw["equity_ridge"])

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

# K259: use ridge_daily series, align to ML window
k259_daily_map = {}
for ts_str, cpnl in zip(k259_raw["K259_ridge_daily"]["timestamps"],
                          k259_raw["K259_ridge_daily"]["cumulative_pnl"]):
    k259_daily_map[ts_str[:10]] = cpnl

k259_eq_values = []
missing_k259 = 0
for d in dates_ml:
    if d in k259_daily_map:
        k259_eq_values.append(1.0 + k259_daily_map[d])
    else:
        missing_k259 += 1
        k259_eq_values.append(k259_eq_values[-1] if k259_eq_values else 1.0)
eq259 = np.array(k259_eq_values)

n = len(dates_ml)
assert len(eq198) == len(eq208) == len(eq226) == len(eq259) == n, \
    f"Length mismatch: {len(eq198)}, {len(eq208)}, {len(eq226)}, {len(eq259)}"

print(f"Data loaded: {n} days ({dates_ml[0]} -> {dates_ml[-1]})")
print(f"K208 missing: {missing_k208}/{n}, K226 missing: {missing_k226}/{n}, K259 missing: {missing_k259}/{n}")

# Daily returns
ret198 = np.diff(eq198) / eq198[:-1]
ret208 = np.diff(eq208) / eq208[:-1]
ret226 = np.diff(eq226) / eq226[:-1]
ret259 = np.diff(eq259) / eq259[:-1]
ret_dates = dates_ml[1:]
n_ret = len(ret198)

print(f"Return series: {n_ret} days")
print(f"K198: mean={ret198.mean():.6f}, std={ret198.std():.6f}")
print(f"K208: mean={ret208.mean():.6f}, std={ret208.std():.6f}")
print(f"K226: mean={ret226.mean():.6f}, std={ret226.std():.6f}")
print(f"K259: mean={ret259.mean():.6f}, std={ret259.std():.6f}")

# ─────────────────────────────────────────────────────────────────────────────
# 2. Utility functions
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

def oos_metrics(rets, oos_frac=0.3):
    oos_start = int(len(rets) * (1 - oos_frac))
    oos_rets  = rets[oos_start:]
    return {
        "oos_sharpe":    round(sharpe(oos_rets), 4),
        "oos_maxdd":     round(maxdd(oos_rets), 6),
        "oos_n_days":    len(oos_rets),
        "oos_ann_ret":   round(float(np.mean(oos_rets) * 365), 4),
        "oos_ann_vol":   round(float(np.std(oos_rets, ddof=1) * ANN), 4),
        "oos_start_date": ret_dates[oos_start],
    }

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
            "fold": i + 1, "start_idx": start, "end_idx": end,
            "n_days": end - start, "sharpe": round(float(fs), 4),
            "start_date": ret_dates[start],
            "end_date": ret_dates[min(end-1, len(ret_dates)-1)],
        })
    return {
        "fold_sharpes": [round(s, 4) for s in fold_sharpes],
        "fold_details": fold_details,
        "wf_mean": round(float(np.mean(fold_sharpes)), 4),
        "wf_min":  round(float(np.min(fold_sharpes)), 4),
        "wf_max":  round(float(np.max(fold_sharpes)), 4),
        "wf_std":  round(float(np.std(fold_sharpes, ddof=1)), 4),
    }

def equity_curve(rets):
    eq = np.empty(len(rets) + 1)
    eq[0] = 1.0
    eq[1:] = np.cumprod(1 + rets)
    return eq.tolist()

def inv_vol_blend(rets_list, cap_pairs=None, roll=30):
    """
    Inverse-volatility weighted blend with optional per-component caps.
    cap_pairs: list of (idx, cap_val) tuples applied sequentially
    """
    n_comp = len(rets_list)
    n_t    = len(rets_list[0])
    blended = np.zeros(n_t)
    w_traj  = np.zeros((n_t, n_comp))

    for i in range(n_t):
        start_w = max(0, i - roll)
        vols = []
        for r in rets_list:
            seg = r[start_w:i+1]
            v = np.std(seg, ddof=1) if len(seg) >= 3 else 1e-6
            vols.append(max(v, 1e-9))
        ivols = np.array([1.0 / v for v in vols])
        total = ivols.sum()
        w = ivols / total

        # Apply caps sequentially
        if cap_pairs:
            for cap_idx, cap_val in cap_pairs:
                if w[cap_idx] > cap_val:
                    excess = w[cap_idx] - cap_val
                    w[cap_idx] = cap_val
                    # redistribute excess proportionally to uncapped components
                    mask = np.ones(n_comp, dtype=bool)
                    mask[cap_idx] = False
                    # also respect already-capped components
                    rest_sum = w[mask].sum()
                    if rest_sum > 0:
                        w[mask] += excess * (w[mask] / rest_sum)

        w_traj[i] = w
        blended[i] = sum(w[j] * rets_list[j][i] for j in range(n_comp))

    return blended, w_traj

def mvp_blend(rets_list, roll=60, reg=1e-4):
    """
    Minimum Variance Portfolio (rolling, long-only, normalized).
    """
    n_comp = len(rets_list)
    n_t    = len(rets_list[0])
    blended = np.zeros(n_t)
    w_traj  = np.zeros((n_t, n_comp))
    R = np.stack(rets_list, axis=1)  # (n_t, n_comp)

    for i in range(n_t):
        start_w = max(0, i - roll)
        seg = R[start_w:i+1]
        if len(seg) < n_comp + 2:
            # Fallback to equal weight
            w = np.ones(n_comp) / n_comp
        else:
            cov = np.cov(seg.T) + reg * np.eye(n_comp)
            try:
                inv_cov = np.linalg.inv(cov)
                ones = np.ones(n_comp)
                raw_w = inv_cov @ ones
                raw_w = np.maximum(raw_w, 0)
                denom = raw_w.sum()
                w = raw_w / denom if denom > 0 else np.ones(n_comp) / n_comp
            except np.linalg.LinAlgError:
                w = np.ones(n_comp) / n_comp
        w_traj[i] = w
        blended[i] = sum(w[j] * rets_list[j][i] for j in range(n_comp))

    return blended, w_traj

# ─────────────────────────────────────────────────────────────────────────────
# 3. Gate 0: K259 validation on K246a's ML window
# ─────────────────────────────────────────────────────────────────────────────
print("\n=== GATE 0: K259 standalone on K246a ML window ===")
gate0_oos = oos_metrics(ret259)
gate0_wf  = wf_stats(ret259)
gate0_pass = all(s > 0 for s in gate0_wf["fold_sharpes"])

print(f"K259 standalone: OOS Sh={gate0_oos['oos_sharpe']:.4f}, MaxDD={gate0_oos['oos_maxdd']:.6f}")
print(f"WF folds: {gate0_wf['fold_sharpes']}")
print(f"WF min={gate0_wf['wf_min']:.4f}, WF mean={gate0_wf['wf_mean']:.4f}")
print(f"Gate 0 PASS (all folds positive): {gate0_pass}")

# ─────────────────────────────────────────────────────────────────────────────
# 4. 4x4 Correlation matrix
# ─────────────────────────────────────────────────────────────────────────────
print("\n=== 4x4 Correlation Matrix ===")
all_rets = np.stack([ret198, ret208, ret226, ret259], axis=1)
corr_matrix = np.corrcoef(all_rets.T)
comp_names = ["K198", "K208", "K226", "K259"]
print("       " + "  ".join(f"{n:>6}" for n in comp_names))
for i, name in enumerate(comp_names):
    row = "  ".join(f"{corr_matrix[i,j]:6.3f}" for j in range(4))
    print(f"{name:>6}: {row}")

corr_dict = {}
for i, n1 in enumerate(comp_names):
    for j, n2 in enumerate(comp_names):
        corr_dict[f"{n1}_vs_{n2}"] = round(float(corr_matrix[i,j]), 4)

# ─────────────────────────────────────────────────────────────────────────────
# 5. Portfolio variants
# ─────────────────────────────────────────────────────────────────────────────
results = {}
curves_out = {}

# K261a: 3-way baseline (K246a replication)
print("\n=== K261a: 3-way (K198+K208+K226) inv-vol + K226 cap 20% ===")
ret_k261a, w_k261a = inv_vol_blend(
    [ret198, ret208, ret226], cap_pairs=[(2, 0.20)]
)
m_k261a = oos_metrics(ret_k261a)
m_k261a.update(wf_stats(ret_k261a))
m_k261a["avg_weights"] = {
    "K198": round(float(w_k261a[:, 0].mean()), 4),
    "K208": round(float(w_k261a[:, 1].mean()), 4),
    "K226": round(float(w_k261a[:, 2].mean()), 4),
}
m_k261a["description"] = "3-way K246a replication: inv-vol + K226 cap 20%"
m_k261a["components"] = ["K198", "K208", "K226"]
results["K261a"] = m_k261a
curves_out["K261a"] = {"equity": equity_curve(ret_k261a), "dates": [dates_ml[0]] + ret_dates}
print(f"K261a: OOS Sh={m_k261a['oos_sharpe']:.4f}, WF mean={m_k261a['wf_mean']:.4f}, "
      f"WF min={m_k261a['wf_min']:.4f}, MaxDD={m_k261a['oos_maxdd']:.6f}")
print(f"  Folds: {m_k261a['fold_sharpes']}")

# K261b: 4-way + K259 cap 15%
print("\n=== K261b: 4-way inv-vol + K226 cap 20% + K259 cap 15% ===")
ret_k261b, w_k261b = inv_vol_blend(
    [ret198, ret208, ret226, ret259], cap_pairs=[(2, 0.20), (3, 0.15)]
)
m_k261b = oos_metrics(ret_k261b)
m_k261b.update(wf_stats(ret_k261b))
m_k261b["avg_weights"] = {
    "K198": round(float(w_k261b[:, 0].mean()), 4),
    "K208": round(float(w_k261b[:, 1].mean()), 4),
    "K226": round(float(w_k261b[:, 2].mean()), 4),
    "K259": round(float(w_k261b[:, 3].mean()), 4),
}
m_k261b["description"] = "4-way: K198+K208+K226+K259 inv-vol + K226≤20% + K259≤15%"
m_k261b["components"] = ["K198", "K208", "K226", "K259"]
results["K261b"] = m_k261b
curves_out["K261b"] = {"equity": equity_curve(ret_k261b), "dates": [dates_ml[0]] + ret_dates}
print(f"K261b: OOS Sh={m_k261b['oos_sharpe']:.4f}, WF mean={m_k261b['wf_mean']:.4f}, "
      f"WF min={m_k261b['wf_min']:.4f}, MaxDD={m_k261b['oos_maxdd']:.6f}")
print(f"  Folds: {m_k261b['fold_sharpes']}")
print(f"  Avg wts: {m_k261b['avg_weights']}")

# K261c: 4-way + K259 cap 20%
print("\n=== K261c: 4-way inv-vol + K226 cap 20% + K259 cap 20% ===")
ret_k261c, w_k261c = inv_vol_blend(
    [ret198, ret208, ret226, ret259], cap_pairs=[(2, 0.20), (3, 0.20)]
)
m_k261c = oos_metrics(ret_k261c)
m_k261c.update(wf_stats(ret_k261c))
m_k261c["avg_weights"] = {
    "K198": round(float(w_k261c[:, 0].mean()), 4),
    "K208": round(float(w_k261c[:, 1].mean()), 4),
    "K226": round(float(w_k261c[:, 2].mean()), 4),
    "K259": round(float(w_k261c[:, 3].mean()), 4),
}
m_k261c["description"] = "4-way: K198+K208+K226+K259 inv-vol + K226≤20% + K259≤20%"
m_k261c["components"] = ["K198", "K208", "K226", "K259"]
results["K261c"] = m_k261c
curves_out["K261c"] = {"equity": equity_curve(ret_k261c), "dates": [dates_ml[0]] + ret_dates}
print(f"K261c: OOS Sh={m_k261c['oos_sharpe']:.4f}, WF mean={m_k261c['wf_mean']:.4f}, "
      f"WF min={m_k261c['wf_min']:.4f}, MaxDD={m_k261c['oos_maxdd']:.6f}")
print(f"  Folds: {m_k261c['fold_sharpes']}")
print(f"  Avg wts: {m_k261c['avg_weights']}")

# K261d: 4-way + K259 cap 25%
print("\n=== K261d: 4-way inv-vol + K226 cap 20% + K259 cap 25% ===")
ret_k261d, w_k261d = inv_vol_blend(
    [ret198, ret208, ret226, ret259], cap_pairs=[(2, 0.20), (3, 0.25)]
)
m_k261d = oos_metrics(ret_k261d)
m_k261d.update(wf_stats(ret_k261d))
m_k261d["avg_weights"] = {
    "K198": round(float(w_k261d[:, 0].mean()), 4),
    "K208": round(float(w_k261d[:, 1].mean()), 4),
    "K226": round(float(w_k261d[:, 2].mean()), 4),
    "K259": round(float(w_k261d[:, 3].mean()), 4),
}
m_k261d["description"] = "4-way: K198+K208+K226+K259 inv-vol + K226≤20% + K259≤25%"
m_k261d["components"] = ["K198", "K208", "K226", "K259"]
results["K261d"] = m_k261d
curves_out["K261d"] = {"equity": equity_curve(ret_k261d), "dates": [dates_ml[0]] + ret_dates}
print(f"K261d: OOS Sh={m_k261d['oos_sharpe']:.4f}, WF mean={m_k261d['wf_mean']:.4f}, "
      f"WF min={m_k261d['wf_min']:.4f}, MaxDD={m_k261d['oos_maxdd']:.6f}")
print(f"  Folds: {m_k261d['fold_sharpes']}")
print(f"  Avg wts: {m_k261d['avg_weights']}")

# K261e: 4-way uncapped inv-vol
print("\n=== K261e: 4-way inv-vol uncapped ===")
ret_k261e, w_k261e = inv_vol_blend(
    [ret198, ret208, ret226, ret259], cap_pairs=None
)
m_k261e = oos_metrics(ret_k261e)
m_k261e.update(wf_stats(ret_k261e))
m_k261e["avg_weights"] = {
    "K198": round(float(w_k261e[:, 0].mean()), 4),
    "K208": round(float(w_k261e[:, 1].mean()), 4),
    "K226": round(float(w_k261e[:, 2].mean()), 4),
    "K259": round(float(w_k261e[:, 3].mean()), 4),
}
m_k261e["description"] = "4-way: K198+K208+K226+K259 inv-vol uncapped"
m_k261e["components"] = ["K198", "K208", "K226", "K259"]
results["K261e"] = m_k261e
curves_out["K261e"] = {"equity": equity_curve(ret_k261e), "dates": [dates_ml[0]] + ret_dates}
print(f"K261e: OOS Sh={m_k261e['oos_sharpe']:.4f}, WF mean={m_k261e['wf_mean']:.4f}, "
      f"WF min={m_k261e['wf_min']:.4f}, MaxDD={m_k261e['oos_maxdd']:.6f}")
print(f"  Folds: {m_k261e['fold_sharpes']}")
print(f"  Avg wts: {m_k261e['avg_weights']}")

# K261f: MVP
print("\n=== K261f: 4-way MVP (minimum variance) ===")
ret_k261f, w_k261f = mvp_blend(
    [ret198, ret208, ret226, ret259], roll=60
)
m_k261f = oos_metrics(ret_k261f)
m_k261f.update(wf_stats(ret_k261f))
m_k261f["avg_weights"] = {
    "K198": round(float(w_k261f[:, 0].mean()), 4),
    "K208": round(float(w_k261f[:, 1].mean()), 4),
    "K226": round(float(w_k261f[:, 2].mean()), 4),
    "K259": round(float(w_k261f[:, 3].mean()), 4),
}
m_k261f["description"] = "4-way MVP: K198+K208+K226+K259 min-variance (roll=60d)"
m_k261f["components"] = ["K198", "K208", "K226", "K259"]
results["K261f"] = m_k261f
curves_out["K261f"] = {"equity": equity_curve(ret_k261f), "dates": [dates_ml[0]] + ret_dates}
print(f"K261f: OOS Sh={m_k261f['oos_sharpe']:.4f}, WF mean={m_k261f['wf_mean']:.4f}, "
      f"WF min={m_k261f['wf_min']:.4f}, MaxDD={m_k261f['oos_maxdd']:.6f}")
print(f"  Folds: {m_k261f['fold_sharpes']}")
print(f"  Avg wts: {m_k261f['avg_weights']}")

# ─────────────────────────────────────────────────────────────────────────────
# 6. Acceptance gate evaluation
# ─────────────────────────────────────────────────────────────────────────────
print("\n=== ACCEPTANCE GATE EVALUATION ===")
K246A_OOS_SH  = 12.69
K246A_WF_MIN  = 8.93
K246A_MAX_DD  = -0.00115
TARGET_OOS_SH = K246A_OOS_SH + 0.10  # 12.79

best_variant = None
best_oos_sh  = -np.inf

gate_results = {}
for name, m in results.items():
    if name == "K261a":
        continue  # baseline, no K259
    oos_sh  = m["oos_sharpe"]
    wf_min  = m["wf_min"]
    max_dd  = m["oos_maxdd"]
    wts     = m["avg_weights"]
    all_nonzero = all(v > 0.001 for v in wts.values())

    pass_oos = oos_sh > TARGET_OOS_SH
    pass_wf  = wf_min >= K246A_WF_MIN
    pass_dd  = max_dd >= K246A_MAX_DD  # less negative = better
    pass_wts = all_nonzero
    passed   = pass_oos and pass_wf and pass_dd and pass_wts

    gate_results[name] = {
        "oos_sh": oos_sh, "wf_min": wf_min, "max_dd": max_dd,
        "pass_oos_sh": pass_oos, "pass_wf_min": pass_wf,
        "pass_max_dd": pass_dd, "pass_all_nonzero": pass_wts,
        "overall_pass": passed,
    }
    status = "PASS" if passed else "FAIL"
    print(f"{name}: OOS Sh={oos_sh:.4f}(>{TARGET_OOS_SH:.2f}:{pass_oos}), "
          f"WF min={wf_min:.4f}(>={K246A_WF_MIN:.2f}:{pass_wf}), "
          f"MaxDD={max_dd:.6f}(<={K246A_MAX_DD:.6f}:{pass_dd}), "
          f"NonZero:{pass_wts} → {status}")

    if oos_sh > best_oos_sh:
        best_oos_sh = oos_sh
        best_variant = name

print(f"\nBest OOS Sh: {best_variant} = {best_oos_sh:.4f}")
print(f"Gate 0 (K259 all folds positive): {gate0_pass}")

# ─────────────────────────────────────────────────────────────────────────────
# 7. Per-variant per-fold breakdown
# ─────────────────────────────────────────────────────────────────────────────
print("\n=== PER-VARIANT PER-FOLD BREAKDOWN ===")
for name, m in results.items():
    folds = m["fold_sharpes"]
    print(f"{name}: {folds} | mean={m['wf_mean']:.4f} min={m['wf_min']:.4f}")

# ─────────────────────────────────────────────────────────────────────────────
# 8. Verdict
# ─────────────────────────────────────────────────────────────────────────────
any_pass = any(v["overall_pass"] for v in gate_results.values())
best_passing = None
best_passing_sh = -np.inf
for name, gr in gate_results.items():
    if gr["overall_pass"] and gr["oos_sh"] > best_passing_sh:
        best_passing_sh = gr["oos_sh"]
        best_passing = name

if not gate0_pass:
    verdict = "REJECT: Gate 0 FAIL — K259 has negative WF folds on K246a window"
elif not any_pass:
    verdict = "REJECT: No variant clears all acceptance gates"
else:
    verdict = f"ACCEPT: {best_passing} qualifies → promote to v6.9.2 production"

print(f"\n=== VERDICT ===")
print(verdict)

# ─────────────────────────────────────────────────────────────────────────────
# 9. Save outputs
# ─────────────────────────────────────────────────────────────────────────────
runtime = time.time() - t0
output = {
    "wave": "K261",
    "parent_waves": ["K246", "K259"],
    "objective": "Add K259 as 4th component to K246a (K198+K208+K226); find best cap variant.",
    "as_of": datetime.now(timezone.utc).isoformat(),
    "runtime_s": round(runtime, 2),
    "ml_window": {"start": dates_ml[0], "end": dates_ml[-1], "n_days": n},
    "gate0": {
        "description": "K259 standalone on K246a 448-day window",
        "oos_sharpe": gate0_oos["oos_sharpe"],
        "oos_maxdd":  gate0_oos["oos_maxdd"],
        "wf_folds":   gate0_wf["fold_sharpes"],
        "wf_min":     gate0_wf["wf_min"],
        "wf_mean":    gate0_wf["wf_mean"],
        "all_folds_positive": gate0_pass,
        "missing_days": missing_k259,
    },
    "correlation_matrix": corr_dict,
    "reference_metrics": {
        "K246a_v6_9": {
            "oos_sh": K246A_OOS_SH, "wf_min": K246A_WF_MIN, "max_dd": K246A_MAX_DD,
            "description": "3-way FINAL production"
        }
    },
    "acceptance_gates": {
        "oos_sh_target":  round(TARGET_OOS_SH, 4),
        "wf_min_target":  K246A_WF_MIN,
        "max_dd_target":  K246A_MAX_DD,
        "all_nonzero_weight": True,
    },
    "results": results,
    "gate_results": gate_results,
    "verdict": verdict,
    "best_variant_by_oos_sh": best_variant,
    "best_passing_variant": best_passing,
    "promoted_to_v6_9_2": best_passing is not None and gate0_pass,
}

with open("/Users/nekonaomichi/crypto-lab/wave_k261_4way_k259.json", "w") as f:
    json.dump(output, f, indent=2)
print(f"\nSaved wave_k261_4way_k259.json")

# Save curves
curves_full = {
    "dates": [dates_ml[0]] + ret_dates,
    "K259_standalone": {"equity": equity_curve(ret259)},
}
curves_full.update(curves_out)

with open("/Users/nekonaomichi/crypto-lab/wave_k261_curves.json", "w") as f:
    json.dump(curves_full, f)
print(f"Saved wave_k261_curves.json")
print(f"\nRuntime: {runtime:.1f}s")

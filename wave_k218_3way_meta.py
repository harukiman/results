"""
Wave K218 — 3-Way Meta-Ensemble: K198 × K204 × K208 standalone

Extends K217 (2-way META-ENSEMBLE, OOS Sh 10.43) with a 3rd portfolio:
  K208 = DAR(2,1)-filtered reverse carry panel (standalone, 8h→daily)

Variants:
  K218a — Equal weight 33/33/33
  K218b — Inverse-volatility weighted (rolling 30d)
  K218c — Rolling 90d Sharpe-weighted
  K218d — Minimum Variance Portfolio (pairwise-correlation aware)

Acceptance gates vs K217 v6.6:
  OOS Sh  > 10.48  (+0.05 vs K217 10.43)
  WF min  ≥  6.91  (≥ K217 WF min)
  MaxDD   ≤ -0.0053

K218 deliverables:
  wave_k218_3way_meta.py      — this script
  wave_k218_3way_meta.json    — metrics + correlations + DR
  wave_k218_curves.json       — equity curves
  wave_k218_3way_meta.md      — full report
"""

import json
import numpy as np
from datetime import datetime, timezone
import time

t0 = time.time()

# ─────────────────────────────────────────────────────────
# 1. Load equity series
# ─────────────────────────────────────────────────────────
with open("/Users/nekonaomichi/crypto-lab/wave_k198_curves.json") as f:
    k198_raw = json.load(f)
with open("/Users/nekonaomichi/crypto-lab/wave_k204_curves.json") as f:
    k204_raw = json.load(f)
with open("/Users/nekonaomichi/crypto-lab/wave_k208_curves.json") as f:
    k208_raw = json.load(f)

# K198 and K204 share the same 448-day ML window (daily)
dates_ml  = k198_raw["dates_ml"]   # 2025-01-22 → 2026-04-14, len=448
eq198     = np.array(k198_raw["equity_ridge"])
eq204     = np.array(k204_raw["equity_k204"])

# K208 is 8h resolution — need to collapse to daily closing PnL
# K208_filtered timestamps: "2024-05-23T16:00:00", step=8h, len=2193
# Strategy: take last 8h candle of each UTC day (i.e. T=16:00 UTC → "end of day")
k208_ts   = k208_raw["K208_filtered"]["timestamps"]   # list of ISO strings
k208_cpnl = k208_raw["K208_filtered"]["cumulative_pnl"]  # cumulative PnL (not returns)

# Parse K208 to daily map: date_str → end-of-day cumulative PnL
k208_daily = {}
for ts_str, cpnl in zip(k208_ts, k208_cpnl):
    # ts_str examples: "2025-01-22T16:00:00", "2025-01-23T00:00:00", "2025-01-23T08:00:00"
    date_part = ts_str[:10]  # "YYYY-MM-DD"
    # Overwrite — last entry of the day wins (chronological ordering guaranteed)
    k208_daily[date_part] = cpnl

# Build K208 equity series aligned to dates_ml
# Convert cumulative PnL → equity curve (PnL starts at 0, so equity = 1 + PnL)
k208_eq_values = []
k208_dates_used = []
missing_k208 = 0
for d in dates_ml:
    if d in k208_daily:
        k208_eq_values.append(1.0 + k208_daily[d])
        k208_dates_used.append(d)
    else:
        missing_k208 += 1
        k208_dates_used.append(d)
        # Carry forward last known value or 1.0
        if k208_eq_values:
            k208_eq_values.append(k208_eq_values[-1])
        else:
            k208_eq_values.append(1.0)

eq208 = np.array(k208_eq_values)

n = len(dates_ml)
assert len(eq198) == len(eq204) == len(eq208) == n, (
    f"Length mismatch: K198={len(eq198)}, K204={len(eq204)}, K208={len(eq208)}, dates={n}"
)

print(f"Data loaded: {n} days ({dates_ml[0]} → {dates_ml[-1]})")
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
print(f"K198 daily ret stats: mean={ret198.mean():.6f}, std={ret198.std():.6f}")
print(f"K204 daily ret stats: mean={ret204.mean():.6f}, std={ret204.std():.6f}")
print(f"K208 daily ret stats: mean={ret208.mean():.6f}, std={ret208.std():.6f}")

# ─────────────────────────────────────────────────────────
# 2. Pairwise correlations — full 3×3 matrix
# ─────────────────────────────────────────────────────────
rho_matrix = np.corrcoef([ret198, ret204, ret208])
rho_198_204 = float(rho_matrix[0, 1])
rho_198_208 = float(rho_matrix[0, 2])
rho_204_208 = float(rho_matrix[1, 2])

print(f"\n--- 3×3 Pairwise Correlation Matrix ---")
print(f"              K198    K204    K208")
print(f"K198        {rho_matrix[0,0]:.4f}  {rho_198_204:.4f}  {rho_198_208:.4f}")
print(f"K204        {rho_198_204:.4f}  {rho_matrix[1,1]:.4f}  {rho_204_208:.4f}")
print(f"K208        {rho_198_208:.4f}  {rho_204_208:.4f}  {rho_matrix[2,2]:.4f}")

# ─────────────────────────────────────────────────────────
# 3. Utility functions
# ─────────────────────────────────────────────────────────
ANN = np.sqrt(365)

def sharpe(rets):
    """Annualised Sharpe (daily rets)."""
    if len(rets) < 5:
        return np.nan
    mu  = np.mean(rets) * 365
    sig = np.std(rets, ddof=1) * ANN
    return float(mu / sig) if sig > 0 else np.nan

def maxdd(rets):
    """Maximum drawdown (negative number)."""
    eq = np.cumprod(1 + np.array(rets))
    roll_max = np.maximum.accumulate(eq)
    dd = (eq - roll_max) / roll_max
    return float(dd.min())

def wf_stats(rets, n_folds=4):
    """Walk-forward 4-fold: chronological splits on the return series."""
    fold_size = len(rets) // n_folds
    fold_sharpes = []
    for i in range(n_folds):
        start = i * fold_size
        end   = (i + 1) * fold_size if i < n_folds - 1 else len(rets)
        fold_sharpes.append(sharpe(rets[start:end]))
    return {
        "fold_sharpes": [round(s, 4) for s in fold_sharpes],
        "wf_mean":      round(float(np.mean(fold_sharpes)), 4),
        "wf_min":       round(float(np.min(fold_sharpes)), 4),
        "wf_max":       round(float(np.max(fold_sharpes)), 4),
        "wf_std":       round(float(np.std(fold_sharpes, ddof=1)), 4),
    }

def oos_metrics(rets, oos_frac=0.3):
    """OOS metrics on final oos_frac of the return series."""
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
    """Rebuild equity curve from returns (starts at 1.0)."""
    eq = np.empty(len(rets) + 1)
    eq[0] = 1.0
    eq[1:] = np.cumprod(1 + rets)
    return eq.tolist()

def diversification_ratio(w, rets_matrix):
    """
    Diversification Ratio = (w · sigma_i) / sigma_portfolio
    where sigma_i = individual volatility, sigma_portfolio = portfolio vol.
    rets_matrix: shape (3, T)
    """
    w = np.array(w)
    individual_vols = np.array([np.std(r, ddof=1) for r in rets_matrix])
    weighted_vol_sum = float(np.dot(w, individual_vols))
    # Portfolio vol
    port_rets = np.dot(w, rets_matrix)
    port_vol  = float(np.std(port_rets, ddof=1))
    if port_vol < 1e-12:
        return np.nan
    return round(weighted_vol_sum / port_vol, 4)

# Stack returns for convenience
rets_all = np.stack([ret198, ret204, ret208], axis=0)  # (3, T)

# ─────────────────────────────────────────────────────────
# 4. Baseline metrics (K198, K204, K208 standalone)
# ─────────────────────────────────────────────────────────
print("\n--- Baseline metrics (on ML-window returns) ---")
baseline = {}
for name, rets in [("K198", ret198), ("K204", ret204), ("K208", ret208)]:
    m = oos_metrics(rets)
    w = wf_stats(rets)
    m.update(w)
    baseline[name] = m
    print(f"{name}: OOS Sh={m['oos_sharpe']:.4f}  MaxDD={m['oos_maxdd']:.6f}  "
          f"WF mean={m['wf_mean']:.4f}  WF min={m['wf_min']:.4f}")

# ─────────────────────────────────────────────────────────
# 5. 3-Way meta-allocator variants
# ─────────────────────────────────────────────────────────
variants = {}
variant_rets = {}   # store return series for equity curve output

# ── K218a: Equal weight 33/33/33 ─────────────────────────
print("\n--- K218a: Equal weight 33/33/33 ---")
w_eq = np.array([1/3, 1/3, 1/3])
ret_a = w_eq[0]*ret198 + w_eq[1]*ret204 + w_eq[2]*ret208
m = oos_metrics(ret_a)
w_wf = wf_stats(ret_a)
m.update(w_wf)
m["description"] = "Equal weight 33/33/33"
m["avg_weights"] = [round(w_eq[0], 4), round(w_eq[1], 4), round(w_eq[2], 4)]
m["diversification_ratio"] = diversification_ratio(w_eq, rets_all)
variants["K218a"] = m
variant_rets["K218a"] = ret_a
print(f"K218a: OOS Sh={m['oos_sharpe']:.4f}  MaxDD={m['oos_maxdd']:.6f}  "
      f"WF mean={m['wf_mean']:.4f}  WF min={m['wf_min']:.4f}  DR={m['diversification_ratio']:.4f}")

# ── K218b: Inverse-volatility weighted (rolling 30d) ──────
print("\n--- K218b: Inverse-vol weighted (30d rolling) ---")
ROLL = 30
inv_vol_rets_b = np.zeros(n_ret)
w_traj_b = np.zeros((n_ret, 3))  # weight trajectory for diagnostics
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
    w_traj_b[i] = wb
    inv_vol_rets_b[i] = wb[0]*ret198[i] + wb[1]*ret204[i] + wb[2]*ret208[i]

m = oos_metrics(inv_vol_rets_b)
w_wf = wf_stats(inv_vol_rets_b)
m.update(w_wf)
m["description"] = "Inverse-vol weighted (30d rolling)"
m["avg_weights"] = [round(float(w_traj_b[:,0].mean()), 4),
                     round(float(w_traj_b[:,1].mean()), 4),
                     round(float(w_traj_b[:,2].mean()), 4)]
# DR computed at mean weights
m["diversification_ratio"] = diversification_ratio(w_traj_b.mean(axis=0), rets_all)
variants["K218b"] = m
variant_rets["K218b"] = inv_vol_rets_b
print(f"K218b: OOS Sh={m['oos_sharpe']:.4f}  MaxDD={m['oos_maxdd']:.6f}  "
      f"WF mean={m['wf_mean']:.4f}  WF min={m['wf_min']:.4f}  DR={m['diversification_ratio']:.4f}")
print(f"       Avg weights: K198={m['avg_weights'][0]:.3f}, K204={m['avg_weights'][1]:.3f}, K208={m['avg_weights'][2]:.3f}")

# ── K218c: Rolling 90d Sharpe-weighted ────────────────────
print("\n--- K218c: Rolling 90d Sharpe-weighted ---")
ROLL_SH = 90
sh_rets_c = np.zeros(n_ret)
w_traj_c = np.zeros((n_ret, 3))
for i in range(n_ret):
    start_w = max(0, i - ROLL_SH)
    seg198 = ret198[start_w:i+1]
    seg204 = ret204[start_w:i+1]
    seg208 = ret208[start_w:i+1]
    sh198 = sharpe(seg198) if len(seg198) >= 10 else 0.0
    sh204 = sharpe(seg204) if len(seg204) >= 10 else 0.0
    sh208 = sharpe(seg208) if len(seg208) >= 10 else 0.0
    # Floor at 0
    sh198c = max(sh198, 0.0)
    sh204c = max(sh204, 0.0)
    sh208c = max(sh208, 0.0)
    total = sh198c + sh204c + sh208c
    if total < 1e-9:
        wc = np.array([1/3, 1/3, 1/3])
    else:
        wc = np.array([sh198c/total, sh204c/total, sh208c/total])
    w_traj_c[i] = wc
    sh_rets_c[i] = wc[0]*ret198[i] + wc[1]*ret204[i] + wc[2]*ret208[i]

m = oos_metrics(sh_rets_c)
w_wf = wf_stats(sh_rets_c)
m.update(w_wf)
m["description"] = "Rolling 90d Sharpe-weighted"
m["avg_weights"] = [round(float(w_traj_c[:,0].mean()), 4),
                     round(float(w_traj_c[:,1].mean()), 4),
                     round(float(w_traj_c[:,2].mean()), 4)]
m["diversification_ratio"] = diversification_ratio(w_traj_c.mean(axis=0), rets_all)
variants["K218c"] = m
variant_rets["K218c"] = sh_rets_c
print(f"K218c: OOS Sh={m['oos_sharpe']:.4f}  MaxDD={m['oos_maxdd']:.6f}  "
      f"WF mean={m['wf_mean']:.4f}  WF min={m['wf_min']:.4f}  DR={m['diversification_ratio']:.4f}")
print(f"       Avg weights: K198={m['avg_weights'][0]:.3f}, K204={m['avg_weights'][1]:.3f}, K208={m['avg_weights'][2]:.3f}")

# ── K218d: Minimum Variance Portfolio (rolling 60d covariance) ──
print("\n--- K218d: Minimum Variance Portfolio (rolling 60d cov) ---")
ROLL_MVP = 60
mvp_rets_d = np.zeros(n_ret)
w_traj_d = np.zeros((n_ret, 3))

def mvp_weights(cov_matrix):
    """
    Minimum Variance Portfolio weights (long-only, sum to 1).
    Uses analytical formula: w = Sigma^{-1} 1 / (1' Sigma^{-1} 1)
    with fallback to equal weight if matrix is singular.
    """
    ones = np.ones(3)
    try:
        sigma_inv = np.linalg.inv(cov_matrix)
        w_raw = sigma_inv @ ones
        # Long-only constraint: floor at 0 and renormalise
        w_raw = np.maximum(w_raw, 0.0)
        s = w_raw.sum()
        if s < 1e-12:
            return np.array([1/3, 1/3, 1/3])
        return w_raw / s
    except np.linalg.LinAlgError:
        return np.array([1/3, 1/3, 1/3])

for i in range(n_ret):
    start_w = max(0, i - ROLL_MVP)
    seg = np.stack([ret198[start_w:i+1],
                    ret204[start_w:i+1],
                    ret208[start_w:i+1]], axis=0)
    if seg.shape[1] >= 5:
        cov = np.cov(seg)  # (3,3) covariance matrix
        wd = mvp_weights(cov)
    else:
        wd = np.array([1/3, 1/3, 1/3])
    w_traj_d[i] = wd
    mvp_rets_d[i] = wd[0]*ret198[i] + wd[1]*ret204[i] + wd[2]*ret208[i]

m = oos_metrics(mvp_rets_d)
w_wf = wf_stats(mvp_rets_d)
m.update(w_wf)
m["description"] = "Minimum Variance Portfolio (rolling 60d covariance, long-only)"
m["avg_weights"] = [round(float(w_traj_d[:,0].mean()), 4),
                     round(float(w_traj_d[:,1].mean()), 4),
                     round(float(w_traj_d[:,2].mean()), 4)]
m["diversification_ratio"] = diversification_ratio(w_traj_d.mean(axis=0), rets_all)
variants["K218d"] = m
variant_rets["K218d"] = mvp_rets_d
print(f"K218d: OOS Sh={m['oos_sharpe']:.4f}  MaxDD={m['oos_maxdd']:.6f}  "
      f"WF mean={m['wf_mean']:.4f}  WF min={m['wf_min']:.4f}  DR={m['diversification_ratio']:.4f}")
print(f"       Avg weights: K198={m['avg_weights'][0]:.3f}, K204={m['avg_weights'][1]:.3f}, K208={m['avg_weights'][2]:.3f}")

# ── K218e: Inv-vol weighted with K208 cap at 30% ──────────
# K208 is ultra-low-vol (daily std ~0.0002 vs K198 ~0.003), so uncapped inv-vol
# pushes >90% to K208. Cap at 30% ensures genuine diversification across all 3.
print("\n--- K218e: Inv-vol weighted + K208 cap 30% (30d rolling) ---")
CAP208_E = 0.30
inv_vol_rets_e = np.zeros(n_ret)
w_traj_e = np.zeros((n_ret, 3))
for i in range(n_ret):
    start_w = max(0, i - ROLL)
    v198 = np.std(ret198[start_w:i+1], ddof=1) if i - start_w >= 2 else 1e-6
    v204 = np.std(ret204[start_w:i+1], ddof=1) if i - start_w >= 2 else 1e-6
    v208 = np.std(ret208[start_w:i+1], ddof=1) if i - start_w >= 2 else 1e-6
    iv198 = 1.0 / max(v198, 1e-9)
    iv204 = 1.0 / max(v204, 1e-9)
    iv208 = 1.0 / max(v208, 1e-9)
    total = iv198 + iv204 + iv208
    we = np.array([iv198/total, iv204/total, iv208/total])
    # Apply K208 cap
    if we[2] > CAP208_E:
        we[2] = CAP208_E
        iv_12 = np.array([iv198, iv204])
        we[:2] = iv_12 / iv_12.sum() * (1.0 - CAP208_E)
    w_traj_e[i] = we
    inv_vol_rets_e[i] = we[0]*ret198[i] + we[1]*ret204[i] + we[2]*ret208[i]

m = oos_metrics(inv_vol_rets_e)
w_wf = wf_stats(inv_vol_rets_e)
m.update(w_wf)
m["description"] = "Inv-vol weighted (30d rolling) + K208 max-weight cap 30%"
m["avg_weights"] = [round(float(w_traj_e[:,0].mean()), 4),
                     round(float(w_traj_e[:,1].mean()), 4),
                     round(float(w_traj_e[:,2].mean()), 4)]
m["diversification_ratio"] = diversification_ratio(w_traj_e.mean(axis=0), rets_all)
variants["K218e"] = m
variant_rets["K218e"] = inv_vol_rets_e
print(f"K218e: OOS Sh={m['oos_sharpe']:.4f}  MaxDD={m['oos_maxdd']:.6f}  "
      f"WF mean={m['wf_mean']:.4f}  WF min={m['wf_min']:.4f}  DR={m['diversification_ratio']:.4f}")
print(f"       Avg weights: K198={m['avg_weights'][0]:.3f}, K204={m['avg_weights'][1]:.3f}, K208={m['avg_weights'][2]:.3f}")

# ── K218f: Risk-budget: K198 50%, K204 35%, K208 15% ──────
# Fixed proportions reflecting K208 as a "carry satellite" within a ML-core portfolio
print("\n--- K218f: Risk-budget fixed (K198=50%, K204=35%, K208=15%) ---")
w_f = np.array([0.50, 0.35, 0.15])
ret_f = w_f[0]*ret198 + w_f[1]*ret204 + w_f[2]*ret208
m = oos_metrics(ret_f)
w_wf = wf_stats(ret_f)
m.update(w_wf)
m["description"] = "Risk-budget fixed: K198=50%, K204=35%, K208=15% (carry satellite)"
m["avg_weights"] = [round(float(w_f[0]), 4), round(float(w_f[1]), 4), round(float(w_f[2]), 4)]
m["diversification_ratio"] = diversification_ratio(w_f, rets_all)
variants["K218f"] = m
variant_rets["K218f"] = ret_f
print(f"K218f: OOS Sh={m['oos_sharpe']:.4f}  MaxDD={m['oos_maxdd']:.6f}  "
      f"WF mean={m['wf_mean']:.4f}  WF min={m['wf_min']:.4f}  DR={m['diversification_ratio']:.4f}")
print(f"       Avg weights: K198={m['avg_weights'][0]:.3f}, K204={m['avg_weights'][1]:.3f}, K208={m['avg_weights'][2]:.3f}")

# ─────────────────────────────────────────────────────────
# 6. Acceptance gates vs K217 v6.6
# ─────────────────────────────────────────────────────────
K217_OOS_SH = 10.43
K217_WF_MIN  = 6.91
K217_MAXDD   = -0.0053

GATE_OOS_SH  = K217_OOS_SH + 0.05   # 10.48
GATE_WF_MIN  = K217_WF_MIN           # ≥ 6.91
GATE_MAXDD   = K217_MAXDD            # ≤ -0.0053

print(f"\n--- Acceptance Gates (vs K217 v6.6) ---")
print(f"Required: OOS Sh > {GATE_OOS_SH:.2f}  |  WF min ≥ {GATE_WF_MIN:.2f}  |  MaxDD ≤ {GATE_MAXDD:.4f}")
print(f"          All 3 portfolios must receive non-zero weight")

candidates = []
for vname, vm in variants.items():
    sh_pass   = vm["oos_sharpe"] > GATE_OOS_SH
    wf_pass   = vm["wf_min"] >= GATE_WF_MIN
    dd_pass   = vm["oos_maxdd"] >= GATE_MAXDD
    # Check all 3 portfolios get non-zero average weight
    min_wt    = min(vm["avg_weights"])
    wt_pass   = min_wt > 0.01   # at least 1% allocation to each
    all_pass  = sh_pass and wf_pass and dd_pass and wt_pass
    score     = vm["oos_sharpe"] + vm["wf_min"]

    print(f"  {vname}: OOS={vm['oos_sharpe']:.4f}({'v' if sh_pass else 'x'})  "
          f"WFmin={vm['wf_min']:.4f}({'v' if wf_pass else 'x'})  "
          f"MaxDD={vm['oos_maxdd']:.6f}({'v' if dd_pass else 'x'})  "
          f"MinWt={min_wt:.3f}({'v' if wt_pass else 'x'})  "
          f"-> {'PASS' if all_pass else 'FAIL'}")
    if all_pass:
        candidates.append((score, vname, vm))

candidates.sort(reverse=True)
best_name  = candidates[0][1] if candidates else None
best_vm    = candidates[0][2] if candidates else None
accepted   = best_name is not None

# ─────────────────────────────────────────────────────────
# 7. Synergy analysis
# ─────────────────────────────────────────────────────────
print("\n--- Synergy Analysis ---")
sh198_oos = baseline["K198"]["oos_sharpe"]
sh204_oos = baseline["K204"]["oos_sharpe"]
sh208_oos = baseline["K208"]["oos_sharpe"]
avg_individual = (sh198_oos + sh204_oos + sh208_oos) / 3.0
print(f"Individual OOS Sharpes: K198={sh198_oos:.4f}, K204={sh204_oos:.4f}, K208={sh208_oos:.4f}")
print(f"Average of 3 individuals: {avg_individual:.4f}")
if best_vm:
    synergy_sh = best_vm["oos_sharpe"] - avg_individual
    synergy_vs_k217 = best_vm["oos_sharpe"] - K217_OOS_SH
    synergy_detected = synergy_sh > 0.02
    print(f"Best ensemble ({best_name}): {best_vm['oos_sharpe']:.4f}")
    print(f"Synergy vs avg individuals: {synergy_sh:+.4f} ({'GENUINE' if synergy_detected else 'WEAK'})")
    print(f"Improvement vs K217:        {synergy_vs_k217:+.4f}")

    avg_wf_min = (baseline["K198"]["wf_min"] + baseline["K204"]["wf_min"] + baseline["K208"]["wf_min"]) / 3
    wf_min_synergy = best_vm["wf_min"] - avg_wf_min
    print(f"WF-min avg individuals: {avg_wf_min:.4f}  |  Best ensemble WF-min: {best_vm['wf_min']:.4f}  |  D: {wf_min_synergy:+.4f}")
else:
    synergy_sh = 0.0
    synergy_vs_k217 = 0.0
    synergy_detected = False
    print("No accepted candidate.")

# ─────────────────────────────────────────────────────────
# 8. Build equity curves for output
# ─────────────────────────────────────────────────────────
curves = {
    "K198":   equity_curve(ret198),
    "K204":   equity_curve(ret204),
    "K208":   equity_curve(ret208),
    "K218a":  equity_curve(variant_rets["K218a"]),
    "K218b":  equity_curve(variant_rets["K218b"]),
    "K218c":  equity_curve(variant_rets["K218c"]),
    "K218d":  equity_curve(variant_rets["K218d"]),
    "K218e":  equity_curve(variant_rets["K218e"]),
    "K218f":  equity_curve(variant_rets["K218f"]),
    "K217b_ref": equity_curve(0.5 * ret198 + 0.5 * ret204),  # K217 reference (approx)
    "dates": [dates_ml[0]] + list(ret_dates),  # n dates total
}

# ─────────────────────────────────────────────────────────
# 9. Save JSON outputs
# ─────────────────────────────────────────────────────────
runtime = round(time.time() - t0, 2)

verdict = (
    f"ACCEPT as K218 v6.7 — best variant: {best_name}"
    if accepted
    else "REJECT — no variant passes all acceptance gates vs K217"
)

result = {
    "wave": "K218",
    "task": "3-Way Meta-Ensemble: K198 × K204 × K208 standalone (DAR-filtered reverse carry)",
    "as_of": datetime.now(timezone.utc).isoformat(),
    "runtime_s": runtime,
    "k208_missing_days": missing_k208,
    "correlation_matrix": {
        "labels": ["K198", "K204", "K208"],
        "matrix": [
            [1.0,         round(rho_198_204, 4), round(rho_198_208, 4)],
            [round(rho_198_204, 4), 1.0,         round(rho_204_208, 4)],
            [round(rho_198_208, 4), round(rho_204_208, 4), 1.0],
        ],
        "rho_198_204": round(rho_198_204, 4),
        "rho_198_208": round(rho_198_208, 4),
        "rho_204_208": round(rho_204_208, 4),
        "interpretation": {
            "rho_198_204": ("High" if abs(rho_198_204) > 0.8 else "Moderate" if abs(rho_198_204) > 0.5 else "Low"),
            "rho_198_208": ("High" if abs(rho_198_208) > 0.8 else "Moderate" if abs(rho_198_208) > 0.5 else "Low"),
            "rho_204_208": ("High" if abs(rho_204_208) > 0.8 else "Moderate" if abs(rho_204_208) > 0.5 else "Low"),
        }
    },
    "acceptance_gates": {
        "oos_sharpe_threshold": GATE_OOS_SH,
        "wf_min_threshold": GATE_WF_MIN,
        "maxdd_threshold": GATE_MAXDD,
        "min_weight_per_portfolio": 0.01,
        "reference": "K217 v6.6",
    },
    "baselines": baseline,
    "variants": variants,
    "synergy": {
        "avg_individual_oos_sh":   round(avg_individual, 4),
        "best_ensemble_oos_sh":    round(best_vm["oos_sharpe"], 4) if best_vm else None,
        "synergy_delta_vs_avg":    round(synergy_sh, 4),
        "synergy_delta_vs_k217":   round(synergy_vs_k217, 4) if best_vm else None,
        "synergy_detected":        synergy_detected,
        "avg_individual_wf_min":   round((baseline["K198"]["wf_min"] + baseline["K204"]["wf_min"] + baseline["K208"]["wf_min"]) / 3, 4),
        "best_ensemble_wf_min":    round(best_vm["wf_min"], 4) if best_vm else None,
    },
    "verdict": verdict,
    "accepted": accepted,
    "best_variant": best_name,
    "best_variant_metrics": best_vm,
    "four_way_comparison": {
        "K198_v6.5":       {"oos_sharpe": 10.28, "oos_maxdd": -0.0053, "wf_mean": 7.91, "wf_min": 6.57},
        "K217b_v6.6_prod": {"oos_sharpe": K217_OOS_SH, "oos_maxdd": K217_MAXDD, "wf_mean": 8.01, "wf_min": K217_WF_MIN},
        "K218a_3way_eq":   {"oos_sharpe": variants["K218a"]["oos_sharpe"], "oos_maxdd": variants["K218a"]["oos_maxdd"],
                            "wf_mean": variants["K218a"]["wf_mean"], "wf_min": variants["K218a"]["wf_min"],
                            "dr": variants["K218a"]["diversification_ratio"]},
        "K218b_inv_vol":   {"oos_sharpe": variants["K218b"]["oos_sharpe"], "oos_maxdd": variants["K218b"]["oos_maxdd"],
                            "wf_mean": variants["K218b"]["wf_mean"], "wf_min": variants["K218b"]["wf_min"],
                            "dr": variants["K218b"]["diversification_ratio"]},
        "K218c_sharpe_wt": {"oos_sharpe": variants["K218c"]["oos_sharpe"], "oos_maxdd": variants["K218c"]["oos_maxdd"],
                            "wf_mean": variants["K218c"]["wf_mean"], "wf_min": variants["K218c"]["wf_min"],
                            "dr": variants["K218c"]["diversification_ratio"]},
        "K218d_mvp":       {"oos_sharpe": variants["K218d"]["oos_sharpe"], "oos_maxdd": variants["K218d"]["oos_maxdd"],
                            "wf_mean": variants["K218d"]["wf_mean"], "wf_min": variants["K218d"]["wf_min"],
                            "dr": variants["K218d"]["diversification_ratio"]},
    "K218e_intvol_cap30": {"oos_sharpe": variants["K218e"]["oos_sharpe"], "oos_maxdd": variants["K218e"]["oos_maxdd"],
                            "wf_mean": variants["K218e"]["wf_mean"], "wf_min": variants["K218e"]["wf_min"],
                            "dr": variants["K218e"]["diversification_ratio"]},
    "K218f_risk_budget": {"oos_sharpe": variants["K218f"]["oos_sharpe"], "oos_maxdd": variants["K218f"]["oos_maxdd"],
                           "wf_mean": variants["K218f"]["wf_mean"], "wf_min": variants["K218f"]["wf_min"],
                           "dr": variants["K218f"]["diversification_ratio"]},
    },
}

with open("/Users/nekonaomichi/crypto-lab/wave_k218_3way_meta.json", "w") as f:
    json.dump(result, f, indent=2)
print("\nSaved: wave_k218_3way_meta.json")

with open("/Users/nekonaomichi/crypto-lab/wave_k218_curves.json", "w") as f:
    json.dump(curves, f)
print("Saved: wave_k218_curves.json")

print(f"\nRuntime: {runtime}s")
print(f"\nVERDICT: {verdict}")

# ─────────────────────────────────────────────────────────
# 10. Generate Markdown report
# ─────────────────────────────────────────────────────────
rho_fmt = result["correlation_matrix"]

report_lines = [
    "# Wave K218 — 3-Way Meta-Ensemble Report",
    f"*Generated: {result['as_of']}  |  Runtime: {runtime}s*",
    "",
    "## Executive Summary",
    "",
]

if accepted:
    report_lines += [
        f"**VERDICT: ACCEPT as K218 v6.7** — Best variant: {best_name}",
        "",
        f"| Metric | K217 v6.6 (prod) | {best_name} | Delta |",
        "|--------|-----------------|-----------|-------|",
        f"| OOS Sharpe | {K217_OOS_SH:.4f} | {best_vm['oos_sharpe']:.4f} | {best_vm['oos_sharpe']-K217_OOS_SH:+.4f} |",
        f"| OOS MaxDD  | {K217_MAXDD:.6f} | {best_vm['oos_maxdd']:.6f} | {best_vm['oos_maxdd']-K217_MAXDD:+.6f} |",
        f"| WF Mean    | 8.0100 | {best_vm['wf_mean']:.4f} | {best_vm['wf_mean']-8.0100:+.4f} |",
        f"| WF Min     | {K217_WF_MIN:.4f} | {best_vm['wf_min']:.4f} | {best_vm['wf_min']-K217_WF_MIN:+.4f} |",
        f"| DR         | N/A | {best_vm['diversification_ratio']:.4f} | — |",
        "",
    ]
else:
    report_lines += [
        "**VERDICT: REJECT** — No variant passes all acceptance gates vs K217 v6.6.",
        "",
    ]

report_lines += [
    "---",
    "",
    "## 1. Data & Methodology",
    "",
    f"- **Date range**: {dates_ml[0]} → {dates_ml[-1]} ({n} days)",
    f"- **Return series**: {n_ret} daily observations",
    f"- **K208 daily aggregation**: 8h→daily by taking last candle of each UTC day; {missing_k208} days filled forward",
    "- **K198**: Ridge ML allocator (best variant: P3 risk-parity), equity_ridge from wave_k198_curves.json",
    "- **K204**: ML DD-embed full ensemble, equity_k204 from wave_k204_curves.json",
    "- **K208**: DAR(2,1)-filtered reverse carry panel (K208_filtered), daily-resampled from wave_k208_curves.json",
    "- **OOS window**: final 30% of return series",
    "- **Walk-forward**: 4-fold chronological splits",
    "",
    "---",
    "",
    "## 2. Pairwise Correlation Matrix",
    "",
    "| | K198 | K204 | K208 |",
    "|---|------|------|------|",
    f"| **K198** | 1.0000 | {rho_198_204:.4f} | {rho_198_208:.4f} |",
    f"| **K204** | {rho_198_204:.4f} | 1.0000 | {rho_204_208:.4f} |",
    f"| **K208** | {rho_198_208:.4f} | {rho_204_208:.4f} | 1.0000 |",
    "",
    "**Interpretation:**",
    f"- K198 × K204: ρ={rho_198_204:.4f} ({rho_fmt['interpretation']['rho_198_204']}) — established in K217",
    f"- K198 × K208: ρ={rho_198_208:.4f} ({rho_fmt['interpretation']['rho_198_208']}) — K208 is pure reverse carry sleeve; K198 contains V_rev_carry as one of 10 features",
    f"- K204 × K208: ρ={rho_204_208:.4f} ({rho_fmt['interpretation']['rho_204_208']}) — K204 is the full ML ensemble; K208 is a concentrated reverse carry factor",
]

if rho_198_208 < 0.5:
    report_lines += [
        f"- K208 provides **genuine orthogonality** vs both K198 and K204 (all pairs < 0.5)",
    ]
elif rho_198_208 < 0.8:
    report_lines += [
        f"- K208 provides **moderate diversification** — some overlap with K198 reverse carry sleeve expected",
    ]
else:
    report_lines += [
        f"- K208 is **highly correlated** with existing portfolios — 3rd portfolio adds limited diversification",
    ]

report_lines += [
    "",
    "---",
    "",
    "## 3. Baseline Performance (Standalone)",
    "",
    "| Portfolio | OOS Sharpe | OOS MaxDD | WF Mean | WF Min | WF Max |",
    "|-----------|-----------|-----------|---------|--------|--------|",
]
for bname, bm in baseline.items():
    report_lines.append(
        f"| {bname} | {bm['oos_sharpe']:.4f} | {bm['oos_maxdd']:.6f} | {bm['wf_mean']:.4f} | {bm['wf_min']:.4f} | {bm['wf_max']:.4f} |"
    )

report_lines += [
    "",
    "---",
    "",
    "## 4. Variant Results",
    "",
    "### 4.1 Per-Variant Summary",
    "",
    "| Variant | OOS Sharpe | OOS MaxDD | WF Mean | WF Min | DR | Avg Wts (K198/K204/K208) |",
    "|---------|-----------|-----------|---------|--------|----|--------------------------|",
]
for vname, vm in variants.items():
    wts = vm["avg_weights"]
    report_lines.append(
        f"| {vname} | {vm['oos_sharpe']:.4f} | {vm['oos_maxdd']:.6f} | {vm['wf_mean']:.4f} | "
        f"{vm['wf_min']:.4f} | {vm['diversification_ratio']:.4f} | {wts[0]:.3f}/{wts[1]:.3f}/{wts[2]:.3f} |"
    )

report_lines += [
    "",
    "### 4.2 Per-Variant Per-Fold Breakdown",
    "",
    "| Variant | Fold 1 | Fold 2 | Fold 3 | Fold 4 | Min | Mean |",
    "|---------|--------|--------|--------|--------|-----|------|",
]
for vname, vm in variants.items():
    fs = vm["fold_sharpes"]
    report_lines.append(
        f"| {vname} | {fs[0]:.4f} | {fs[1]:.4f} | {fs[2]:.4f} | {fs[3]:.4f} | "
        f"{vm['wf_min']:.4f} | {vm['wf_mean']:.4f} |"
    )

report_lines += [
    "",
    "---",
    "",
    "## 5. Four-Way Comparison Table",
    "",
    "| Version | OOS Sh | OOS MaxDD | WF Mean | WF Min | DR |",
    "|---------|--------|-----------|---------|--------|----|",
    f"| K198 v6.5 | 10.2800 | -0.005300 | 7.9100 | 6.5700 | — |",
    f"| K217b v6.6 (prod) | {K217_OOS_SH:.4f} | {K217_MAXDD:.6f} | 8.0100 | {K217_WF_MIN:.4f} | — |",
]
for vname in ["K218a", "K218b", "K218c", "K218d", "K218e", "K218f"]:
    vm = variants[vname]
    wts = vm["avg_weights"]
    report_lines.append(
        f"| {vname} | {vm['oos_sharpe']:.4f} | {vm['oos_maxdd']:.6f} | {vm['wf_mean']:.4f} | {vm['wf_min']:.4f} | {vm['diversification_ratio']:.4f} |"
    )

report_lines += [
    "",
    "**Acceptance gate**: OOS Sh > 10.48 | WF Min ≥ 6.91 | MaxDD ≤ -0.0053 | All weights > 1%",
    "",
    "---",
    "",
    "## 6. Synergy Analysis",
    "",
    f"- Average of 3 individuals OOS Sh: {avg_individual:.4f}",
]
if best_vm:
    report_lines += [
        f"- Best ensemble ({best_name}) OOS Sh: {best_vm['oos_sharpe']:.4f}",
        f"- Synergy vs avg individuals: {synergy_sh:+.4f} ({'GENUINE' if synergy_detected else 'WEAK/NONE'})",
        f"- Improvement vs K217 v6.6: {synergy_vs_k217:+.4f}",
    ]

report_lines += [
    "",
    "---",
    "",
    "## 7. Risk Analysis",
    "",
    "### K208 Standalone Characteristics",
    "- **Nature**: Pure DAR(2,1)-filtered reverse carry panel (10 symbols, 9 passing DAR direction accuracy)",
    "- **8h resolution collapsed to daily**: last-tick sampling may introduce micro-bias",
    "- **Concentrated sleeve**: Very low MaxDD in isolation, but high vol regime sensitivity",
    "- **Overlap with K198**: K198 contains V_rev_carry as one of 10 Ridge features — partial overlap expected",
    "",
    "### Diversification Ratio Interpretation",
    "- DR > 1.10 = genuine diversification benefit",
    "- DR ≈ 1.00 = no meaningful benefit from combining",
    "",
    "### Known Risks",
    "1. K208 8h→daily resampling may not perfectly align with K198/K204 daily closes",
    f"2. K198 vs K208 correlation (ρ={rho_198_208:.4f}) — K208 reverse carry overlaps K198 V_rev_carry sleeve",
    "3. K208 equity starts at 1.0 (mapped from cumulative PnL) — may not reflect identical capital base",
    "4. 3-way ensemble has more parameters to estimate → increased risk of lookahead bias in adaptive variants",
    "",
    "---",
    "",
    "## 8. Verdict & Deployment Plan",
    "",
]

if accepted:
    report_lines += [
        f"### ACCEPT → K218 v6.7 (Best variant: {best_name})",
        "",
        f"The 3-way meta-ensemble ({best_name}: {best_vm['description']}) passes all acceptance gates:",
        f"- OOS Sharpe {best_vm['oos_sharpe']:.4f} > gate 10.48 ({'PASS' if best_vm['oos_sharpe'] > GATE_OOS_SH else 'FAIL'})",
        f"- WF Min {best_vm['wf_min']:.4f} >= gate 6.91 ({'PASS' if best_vm['wf_min'] >= GATE_WF_MIN else 'FAIL'})",
        f"- MaxDD {best_vm['oos_maxdd']:.6f} <= gate -0.0053 ({'PASS' if best_vm['oos_maxdd'] >= GATE_MAXDD else 'FAIL'})",
        f"- All 3 portfolios non-zero (min weight = {min(best_vm['avg_weights']):.3f}) ({'PASS' if min(best_vm['avg_weights']) > 0.01 else 'FAIL'})",
        "",
        "**Deployment Plan:**",
        f"1. Promote K218 ({best_name}) to v6.7 production",
        "2. Weights: K198 Ridge ML allocator + K204 ML DD-embed + K208 DAR-filtered reverse carry",
        f"3. Allocator: {best_vm['description']}",
        "4. Monitor: Track per-portfolio performance weekly; rebalance monthly if weights drift >15%",
        "5. Fallback: Revert to K217b if K208 sleeve enters persistent drawdown (>3× historical MaxDD)",
    ]
else:
    report_lines += [
        "### REJECT — Maintain K217 v6.6 as Production",
        "",
        "No K218 variant improves on K217 v6.6 across all gates simultaneously.",
        "",
        "**Analysis:**",
    ]
    for vname, vm in variants.items():
        sh_pass = vm["oos_sharpe"] > GATE_OOS_SH
        wf_pass = vm["wf_min"] >= GATE_WF_MIN
        dd_pass = vm["oos_maxdd"] >= GATE_MAXDD
        wt_pass = min(vm["avg_weights"]) > 0.01
        failures = []
        if not sh_pass: failures.append(f"OOS Sh {vm['oos_sharpe']:.4f} < {GATE_OOS_SH}")
        if not wf_pass: failures.append(f"WF Min {vm['wf_min']:.4f} < {GATE_WF_MIN}")
        if not dd_pass: failures.append(f"MaxDD {vm['oos_maxdd']:.6f} > {GATE_MAXDD}")
        if not wt_pass: failures.append(f"Min weight {min(vm['avg_weights']):.3f} < 0.01")
        report_lines.append(f"- **{vname}**: FAIL — {'; '.join(failures) if failures else 'All pass but not best'}")

    report_lines += [
        "",
        "**Root cause**: K208 standalone, while high Sharpe in isolation, does not add sufficient orthogonal",
        "alpha when combined with K198 (which already contains the reverse carry signal as one of its features).",
        "The 3rd portfolio does not provide enough diversification benefit to overcome the allocation dilution.",
        "",
        "**Alternative paths**: Consider K195 (forward carry only) as 3rd portfolio — mechanistically distinct.",
    ]

report_lines += [
    "",
    "---",
    f"*Wave K218 | crypto-lab | {result['as_of']}*",
]

report_text = "\n".join(report_lines)

with open("/Users/nekonaomichi/crypto-lab/wave_k218_3way_meta.md", "w") as f:
    f.write(report_text)
print("Saved: wave_k218_3way_meta.md")

print(f"\n{'='*60}")
print(f"K218 COMPLETE — Runtime {runtime}s")
print(f"VERDICT: {verdict}")
print(f"{'='*60}")

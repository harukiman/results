"""
Wave K230 — 4-Way Meta-Ensemble: K198 × K204 × K208 × K228

Extends K218 v6.7 (3-way meta, OOS Sh 11.03, WF min 6.93) by adding:
  K228 = Stablecoin mint/burn momentum (daily signal, 85% cash days)

CRITICAL FIRST STEP: Validate K228 on K218 ML window (448 days: 2025-01-22 → 2026-04-14)
  If K228 ML-window OOS Sh < 1.5 → ABORT 4-way and report

Variants:
  K230a — Equal weight 25/25/25/25
  K230b — Inverse-vol weighted (30d rolling)
  K230c — Inv-vol + K228 cap 10%
  K230d — Inv-vol + K228 cap 20%
  K230e — Inv-vol + K208 and K228 both cap 25%
  K230f — MVP (Minimum Variance Portfolio, rolling 60d)

Acceptance gates vs K218 v6.7 (best variant K218e):
  K228 ML-window OOS Sh ≥ 1.5
  Best variant OOS Sh > 11.03 + 0.10 = 11.13
  WF min ≥ 6.93
  MaxDD ≤ -0.0036
  All 4 portfolios get non-zero weight

Deliverables:
  wave_k230_4way_k228.py      — this script
  wave_k230_4way_k228.json    — metrics + ML window validation
  wave_k230_curves.json       — equity curves
  wave_k230_4way_k228.md      — full report
"""

import json
import numpy as np
from datetime import datetime, timezone
import time

t0 = time.time()
ANN = np.sqrt(365)

# ─────────────────────────────────────────────────────────────────────────────
# 1. Load equity series
# ─────────────────────────────────────────────────────────────────────────────
with open("/Users/nekonaomichi/crypto-lab/wave_k198_curves.json") as f:
    k198_raw = json.load(f)
with open("/Users/nekonaomichi/crypto-lab/wave_k204_curves.json") as f:
    k204_raw = json.load(f)
with open("/Users/nekonaomichi/crypto-lab/wave_k208_curves.json") as f:
    k208_raw = json.load(f)
with open("/Users/nekonaomichi/crypto-lab/wave_k228_curves.json") as f:
    k228_raw = json.load(f)

# K218 ML window: 448 days, 2025-01-22 → 2026-04-14
dates_ml = k198_raw["dates_ml"]   # list of 448 date strings
eq198    = np.array(k198_raw["equity_ridge"])
eq204    = np.array(k204_raw["equity_k204"])

# ── K208: 8h resolution → daily closing PnL ───────────────────────────────
k208_ts   = k208_raw["K208_filtered"]["timestamps"]
k208_cpnl = k208_raw["K208_filtered"]["cumulative_pnl"]
k208_daily = {}
for ts_str, cpnl in zip(k208_ts, k208_cpnl):
    date_part = ts_str[:10]
    k208_daily[date_part] = cpnl   # last 8h bar wins

k208_eq_values = []
missing_k208 = 0
for d in dates_ml:
    if d in k208_daily:
        k208_eq_values.append(1.0 + k208_daily[d])
    else:
        missing_k208 += 1
        k208_eq_values.append(k208_eq_values[-1] if k208_eq_values else 1.0)
eq208 = np.array(k208_eq_values)

# ── K228: daily, 2024-05-23 → 2026-05-22 (730 days) — reslice to ML window ─
k228_dates_full = k228_raw["dates"]
k228_ret_full   = np.nan_to_num(np.array(k228_raw["strat_daily_ret"], dtype=float), nan=0.0)
k228_date_map   = {d: r for d, r in zip(k228_dates_full, k228_ret_full)}

# Build K228 equity curve on ML window dates
k228_eq_ml = []
missing_k228 = 0
running_eq = 1.0
for d in dates_ml:
    if d in k228_date_map:
        running_eq *= (1.0 + k228_date_map[d])
    else:
        missing_k228 += 1
    k228_eq_ml.append(running_eq)
eq228 = np.array(k228_eq_ml)

n = len(dates_ml)
assert len(eq198) == len(eq204) == len(eq208) == len(eq228) == n

print(f"Data loaded: {n} days ({dates_ml[0]} → {dates_ml[-1]})")
print(f"K208 missing days (filled forward): {missing_k208}/{n}")
print(f"K228 missing days: {missing_k228}/{n}")
print(f"K198 equity range: [{eq198.min():.4f}, {eq198.max():.4f}]")
print(f"K204 equity range: [{eq204.min():.4f}, {eq204.max():.4f}]")
print(f"K208 equity range: [{eq208.min():.4f}, {eq208.max():.4f}]")
print(f"K228 equity range: [{eq228.min():.4f}, {eq228.max():.4f}]")

# Daily geometric returns (n-1 values)
ret198 = np.diff(eq198) / eq198[:-1]
ret204 = np.diff(eq204) / eq204[:-1]
ret208 = np.diff(eq208) / eq208[:-1]
ret228 = np.diff(eq228) / eq228[:-1]
ret_dates = dates_ml[1:]
n_ret = len(ret198)

# K228 non-zero active trading days
k228_nonzero = int(np.count_nonzero(ret228))
print(f"\nK228 ML-window: {n_ret} return days, {k228_nonzero} active ({100*k228_nonzero/n_ret:.1f}%)")

# ─────────────────────────────────────────────────────────────────────────────
# 2. Utility functions
# ─────────────────────────────────────────────────────────────────────────────

def sharpe(rets):
    """Annualised Sharpe (daily returns)."""
    rets = np.asarray(rets)
    if len(rets) < 5:
        return np.nan
    mu  = np.mean(rets) * 365
    sig = np.std(rets, ddof=1) * ANN
    return float(mu / sig) if sig > 1e-14 else np.nan

def maxdd(rets):
    """Maximum drawdown (negative number)."""
    eq = np.cumprod(1 + np.asarray(rets))
    roll_max = np.maximum.accumulate(eq)
    dd = (eq - roll_max) / roll_max
    return float(dd.min())

def wf_stats(rets, n_folds=4):
    """Walk-forward 4-fold chronological splits."""
    rets = np.asarray(rets)
    fold_size = len(rets) // n_folds
    fold_sharpes = []
    for i in range(n_folds):
        start = i * fold_size
        end   = (i + 1) * fold_size if i < n_folds - 1 else len(rets)
        fold_sharpes.append(sharpe(rets[start:end]))
    return {
        "fold_sharpes": [round(float(s), 4) for s in fold_sharpes],
        "wf_mean":      round(float(np.mean(fold_sharpes)), 4),
        "wf_min":       round(float(np.min(fold_sharpes)), 4),
        "wf_max":       round(float(np.max(fold_sharpes)), 4),
        "wf_std":       round(float(np.std(fold_sharpes, ddof=1)), 4),
    }

def oos_metrics(rets, oos_frac=0.3):
    """OOS metrics on final oos_frac of the return series."""
    rets = np.asarray(rets)
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
    """Equity curve from returns (starts at 1.0)."""
    rets = np.asarray(rets)
    eq = np.empty(len(rets) + 1)
    eq[0] = 1.0
    eq[1:] = np.cumprod(1 + rets)
    return [round(float(v), 8) for v in eq]

def diversification_ratio(w, rets_matrix):
    """DR = (w·sigma_i) / sigma_portfolio  (4-asset version)."""
    w = np.asarray(w)
    individual_vols = np.array([np.std(r, ddof=1) for r in rets_matrix])
    weighted_vol_sum = float(np.dot(w, individual_vols))
    port_rets = np.dot(w, rets_matrix)
    port_vol  = float(np.std(port_rets, ddof=1))
    if port_vol < 1e-12:
        return np.nan
    return round(weighted_vol_sum / port_vol, 4)

def mvp_weights_4(cov_matrix):
    """Long-only MVP weights for 4-asset portfolio."""
    ones = np.ones(4)
    try:
        sigma_inv = np.linalg.inv(cov_matrix)
        w_raw = sigma_inv @ ones
        w_raw = np.maximum(w_raw, 0.0)
        s = w_raw.sum()
        if s < 1e-12:
            return np.array([0.25, 0.25, 0.25, 0.25])
        return w_raw / s
    except np.linalg.LinAlgError:
        return np.array([0.25, 0.25, 0.25, 0.25])

# Stack all 4 return series
rets_all4 = np.stack([ret198, ret204, ret208, ret228], axis=0)  # (4, T)

# ─────────────────────────────────────────────────────────────────────────────
# 3. CRITICAL: K228 ML-Window Standalone Validation
# ─────────────────────────────────────────────────────────────────────────────
print("\n" + "="*65)
print("CRITICAL VALIDATION: K228 on K218 ML Window (448 days)")
print("="*65)

k228_oos   = oos_metrics(ret228)
k228_wf    = wf_stats(ret228)
k228_full_sh = sharpe(ret228)
k228_full_dd = maxdd(ret228)

print(f"K228 standalone on ML window:")
print(f"  Full-window Sharpe : {k228_full_sh:.4f}")
print(f"  OOS Sharpe (30%)   : {k228_oos['oos_sharpe']:.4f}")
print(f"  OOS MaxDD          : {k228_oos['oos_maxdd']:.6f}")
print(f"  WF folds           : {k228_wf['fold_sharpes']}")
print(f"  WF min             : {k228_wf['wf_min']:.4f}")

K228_ML_THRESHOLD = 1.5
k228_portability_ok = k228_oos['oos_sharpe'] >= K228_ML_THRESHOLD

print(f"\n  K228 ML-window OOS Sh ≥ {K228_ML_THRESHOLD}? → {'PASS ✓' if k228_portability_ok else 'FAIL ✗'}")
if not k228_portability_ok:
    print(f"\n  ABORT 4-way integration — K228 fails portability gate.")
    print(f"  Recommendation: Use K226 or compound regime-gate K225 instead.")
else:
    print(f"\n  K228 portability confirmed. Proceeding with 4-way ensemble.")
print("="*65)

# ─────────────────────────────────────────────────────────────────────────────
# 4. 4×4 Pairwise Correlation Matrix
# ─────────────────────────────────────────────────────────────────────────────
rho = np.corrcoef(rets_all4)
portfolios = ["K198", "K204", "K208", "K228"]
print("\n--- 4×4 Pairwise Correlation Matrix ---")
print("         " + "  ".join(f"{p:>7}" for p in portfolios))
for i, pi in enumerate(portfolios):
    row = "  ".join(f"{rho[i,j]:7.4f}" for j in range(4))
    print(f"{pi:7}  {row}")

corr_matrix = {
    pi: {pj: round(float(rho[i,j]), 4) for j, pj in enumerate(portfolios)}
    for i, pi in enumerate(portfolios)
}

# ─────────────────────────────────────────────────────────────────────────────
# 5. Baseline metrics (standalone on ML window)
# ─────────────────────────────────────────────────────────────────────────────
print("\n--- Baseline metrics (standalone on ML window) ---")
baseline = {}
for name, rets in zip(portfolios, [ret198, ret204, ret208, ret228]):
    m = oos_metrics(rets)
    w = wf_stats(rets)
    m.update(w)
    baseline[name] = m
    print(f"{name}: OOS Sh={m['oos_sharpe']:.4f}  MaxDD={m['oos_maxdd']:.6f}  "
          f"WF min={m['wf_min']:.4f}  WF folds={m['fold_sharpes']}")

# ─────────────────────────────────────────────────────────────────────────────
# 6. 4-Way Meta-Allocator Variants
# ─────────────────────────────────────────────────────────────────────────────
variants     = {}
variant_rets = {}
ROLL = 30
ROLL_MVP = 60

# ── K230a: Equal weight 25/25/25/25 ──────────────────────────────────────────
print("\n--- K230a: Equal weight 25/25/25/25 ---")
w_a = np.array([0.25, 0.25, 0.25, 0.25])
ret_a = w_a[0]*ret198 + w_a[1]*ret204 + w_a[2]*ret208 + w_a[3]*ret228
m = oos_metrics(ret_a); m.update(wf_stats(ret_a))
m["description"] = "Equal weight 25/25/25/25"
m["avg_weights"]  = [round(float(x), 4) for x in w_a]
m["diversification_ratio"] = diversification_ratio(w_a, rets_all4)
variants["K230a"] = m; variant_rets["K230a"] = ret_a
print(f"K230a: OOS Sh={m['oos_sharpe']:.4f}  MaxDD={m['oos_maxdd']:.6f}  "
      f"WF min={m['wf_min']:.4f}  WF folds={m['fold_sharpes']}  DR={m['diversification_ratio']:.4f}")

# ── K230b: Inverse-vol weighted (30d rolling) ─────────────────────────────
print("\n--- K230b: Inverse-vol weighted (30d rolling) ---")
ret_b = np.zeros(n_ret)
w_traj_b = np.zeros((n_ret, 4))
for i in range(n_ret):
    s = max(0, i - ROLL)
    vols = [np.std(r[s:i+1], ddof=1) if i - s >= 2 else 1e-6
            for r in [ret198, ret204, ret208, ret228]]
    ivols = [1.0 / max(v, 1e-9) for v in vols]
    total = sum(ivols)
    wb = np.array([iv / total for iv in ivols])
    w_traj_b[i] = wb
    ret_b[i] = sum(wb[j] * [ret198, ret204, ret208, ret228][j][i] for j in range(4))

m = oos_metrics(ret_b); m.update(wf_stats(ret_b))
m["description"] = "Inverse-vol weighted (30d rolling)"
m["avg_weights"]  = [round(float(w_traj_b[:,j].mean()), 4) for j in range(4)]
m["diversification_ratio"] = diversification_ratio(w_traj_b.mean(axis=0), rets_all4)
variants["K230b"] = m; variant_rets["K230b"] = ret_b
print(f"K230b: OOS Sh={m['oos_sharpe']:.4f}  MaxDD={m['oos_maxdd']:.6f}  "
      f"WF min={m['wf_min']:.4f}  WF folds={m['fold_sharpes']}  DR={m['diversification_ratio']:.4f}")
print(f"       Avg weights: {dict(zip(portfolios, m['avg_weights']))}")

# ── K230c: Inv-vol + K228 cap 10% ────────────────────────────────────────
print("\n--- K230c: Inv-vol + K228 cap 10% ---")
CAP228_C = 0.10
ret_c = np.zeros(n_ret)
w_traj_c = np.zeros((n_ret, 4))
rets4_list = [ret198, ret204, ret208, ret228]
for i in range(n_ret):
    s = max(0, i - ROLL)
    vols = [np.std(r[s:i+1], ddof=1) if i - s >= 2 else 1e-6 for r in rets4_list]
    ivols = np.array([1.0 / max(v, 1e-9) for v in vols])
    total = ivols.sum()
    wc = ivols / total
    # Apply K228 cap
    if wc[3] > CAP228_C:
        excess = wc[3] - CAP228_C
        wc[3] = CAP228_C
        rescale = ivols[:3] / ivols[:3].sum()
        wc[:3] += excess * rescale
    w_traj_c[i] = wc
    ret_c[i] = sum(wc[j] * rets4_list[j][i] for j in range(4))

m = oos_metrics(ret_c); m.update(wf_stats(ret_c))
m["description"] = "Inv-vol weighted (30d) + K228 cap 10%"
m["avg_weights"]  = [round(float(w_traj_c[:,j].mean()), 4) for j in range(4)]
m["diversification_ratio"] = diversification_ratio(w_traj_c.mean(axis=0), rets_all4)
variants["K230c"] = m; variant_rets["K230c"] = ret_c
print(f"K230c: OOS Sh={m['oos_sharpe']:.4f}  MaxDD={m['oos_maxdd']:.6f}  "
      f"WF min={m['wf_min']:.4f}  WF folds={m['fold_sharpes']}  DR={m['diversification_ratio']:.4f}")
print(f"       Avg weights: {dict(zip(portfolios, m['avg_weights']))}")

# ── K230d: Inv-vol + K228 cap 20% ────────────────────────────────────────
print("\n--- K230d: Inv-vol + K228 cap 20% ---")
CAP228_D = 0.20
ret_d = np.zeros(n_ret)
w_traj_d = np.zeros((n_ret, 4))
for i in range(n_ret):
    s = max(0, i - ROLL)
    vols = [np.std(r[s:i+1], ddof=1) if i - s >= 2 else 1e-6 for r in rets4_list]
    ivols = np.array([1.0 / max(v, 1e-9) for v in vols])
    total = ivols.sum()
    wd = ivols / total
    if wd[3] > CAP228_D:
        excess = wd[3] - CAP228_D
        wd[3] = CAP228_D
        rescale = ivols[:3] / ivols[:3].sum()
        wd[:3] += excess * rescale
    w_traj_d[i] = wd
    ret_d[i] = sum(wd[j] * rets4_list[j][i] for j in range(4))

m = oos_metrics(ret_d); m.update(wf_stats(ret_d))
m["description"] = "Inv-vol weighted (30d) + K228 cap 20%"
m["avg_weights"]  = [round(float(w_traj_d[:,j].mean()), 4) for j in range(4)]
m["diversification_ratio"] = diversification_ratio(w_traj_d.mean(axis=0), rets_all4)
variants["K230d"] = m; variant_rets["K230d"] = ret_d
print(f"K230d: OOS Sh={m['oos_sharpe']:.4f}  MaxDD={m['oos_maxdd']:.6f}  "
      f"WF min={m['wf_min']:.4f}  WF folds={m['fold_sharpes']}  DR={m['diversification_ratio']:.4f}")
print(f"       Avg weights: {dict(zip(portfolios, m['avg_weights']))}")

# ── K230e: Inv-vol + K208 and K228 both cap 25% ──────────────────────────
print("\n--- K230e: Inv-vol + K208 cap 25% and K228 cap 25% ---")
CAP208_E = 0.25
CAP228_E = 0.25
ret_e = np.zeros(n_ret)
w_traj_e = np.zeros((n_ret, 4))
for i in range(n_ret):
    s = max(0, i - ROLL)
    vols = [np.std(r[s:i+1], ddof=1) if i - s >= 2 else 1e-6 for r in rets4_list]
    ivols = np.array([1.0 / max(v, 1e-9) for v in vols])
    total = ivols.sum()
    we = ivols / total
    # Apply K208 cap (index 2)
    if we[2] > CAP208_E:
        excess208 = we[2] - CAP208_E
        we[2] = CAP208_E
        # Redistribute excess to K198, K204, K228 proportional to their inv-vol
        others_iv = np.array([ivols[0], ivols[1], ivols[3]])
        others_sum = others_iv.sum()
        if others_sum > 1e-12:
            others_rescale = others_iv / others_sum
            we[0] += excess208 * others_rescale[0]
            we[1] += excess208 * others_rescale[1]
            we[3] += excess208 * others_rescale[2]
    # Apply K228 cap (index 3) — after K208 cap
    if we[3] > CAP228_E:
        excess228 = we[3] - CAP228_E
        we[3] = CAP228_E
        others_iv2 = np.array([ivols[0], ivols[1]])
        others_sum2 = others_iv2.sum()
        if others_sum2 > 1e-12:
            rescale2 = others_iv2 / others_sum2
            we[0] += excess228 * rescale2[0]
            we[1] += excess228 * rescale2[1]
    # Renormalize to ensure sum=1
    we = np.maximum(we, 0.0)
    we /= we.sum()
    w_traj_e[i] = we
    ret_e[i] = sum(we[j] * rets4_list[j][i] for j in range(4))

m = oos_metrics(ret_e); m.update(wf_stats(ret_e))
m["description"] = "Inv-vol weighted (30d) + K208 cap 25% + K228 cap 25%"
m["avg_weights"]  = [round(float(w_traj_e[:,j].mean()), 4) for j in range(4)]
m["diversification_ratio"] = diversification_ratio(w_traj_e.mean(axis=0), rets_all4)
variants["K230e"] = m; variant_rets["K230e"] = ret_e
print(f"K230e: OOS Sh={m['oos_sharpe']:.4f}  MaxDD={m['oos_maxdd']:.6f}  "
      f"WF min={m['wf_min']:.4f}  WF folds={m['fold_sharpes']}  DR={m['diversification_ratio']:.4f}")
print(f"       Avg weights: {dict(zip(portfolios, m['avg_weights']))}")

# ── K230f: MVP (Minimum Variance Portfolio, rolling 60d) ─────────────────
print("\n--- K230f: MVP (rolling 60d covariance, long-only) ---")
ret_f = np.zeros(n_ret)
w_traj_f = np.zeros((n_ret, 4))
for i in range(n_ret):
    s = max(0, i - ROLL_MVP)
    seg = np.stack([r[s:i+1] for r in rets4_list], axis=0)
    if seg.shape[1] >= 6:
        cov = np.cov(seg)
        wf_mvp = mvp_weights_4(cov)
    else:
        wf_mvp = np.array([0.25, 0.25, 0.25, 0.25])
    w_traj_f[i] = wf_mvp
    ret_f[i] = sum(wf_mvp[j] * rets4_list[j][i] for j in range(4))

m = oos_metrics(ret_f); m.update(wf_stats(ret_f))
m["description"] = "MVP (rolling 60d covariance, long-only)"
m["avg_weights"]  = [round(float(w_traj_f[:,j].mean()), 4) for j in range(4)]
m["diversification_ratio"] = diversification_ratio(w_traj_f.mean(axis=0), rets_all4)
variants["K230f"] = m; variant_rets["K230f"] = ret_f
print(f"K230f: OOS Sh={m['oos_sharpe']:.4f}  MaxDD={m['oos_maxdd']:.6f}  "
      f"WF min={m['wf_min']:.4f}  WF folds={m['fold_sharpes']}  DR={m['diversification_ratio']:.4f}")
print(f"       Avg weights: {dict(zip(portfolios, m['avg_weights']))}")

# ─────────────────────────────────────────────────────────────────────────────
# 7. Acceptance Gates
# ─────────────────────────────────────────────────────────────────────────────
# K218 v6.7 benchmarks (K218e best variant)
K218_OOS_SH  = 11.03
K218_WF_MIN  = 6.93
K218_MAX_DD  = -0.0036

# K230 gates
GATE_K228_ML_SH   = 1.5          # K228 portability gate
GATE_OOS_SH       = K218_OOS_SH + 0.10   # = 11.13
GATE_WF_MIN       = K218_WF_MIN           # = 6.93
GATE_MAXDD        = K218_MAX_DD           # = -0.0036

print("\n--- Acceptance Gates vs K218 v6.7 ---")
print(f"  K228 ML-window OOS Sh ≥ {GATE_K228_ML_SH}: {k228_oos['oos_sharpe']:.4f} → {'PASS' if k228_portability_ok else 'FAIL'}")

best_v = None
best_sh = -np.inf
for vname, vm in variants.items():
    sh  = vm["oos_sharpe"]
    wfm = vm["wf_min"]
    dd  = vm["oos_maxdd"]
    wts = vm["avg_weights"]
    nonzero_wts = all(w > 0.001 for w in wts)
    gate_sh  = sh > GATE_OOS_SH
    gate_wf  = wfm >= GATE_WF_MIN
    gate_dd  = dd  >= GATE_MAXDD
    gate_wts = nonzero_wts
    all_pass = gate_sh and gate_wf and gate_dd and gate_wts and k228_portability_ok
    vm["gate_sh"]  = gate_sh
    vm["gate_wf"]  = gate_wf
    vm["gate_dd"]  = gate_dd
    vm["gate_wts"] = gate_wts
    vm["all_gates_pass"] = all_pass
    print(f"  {vname}: Sh={sh:.4f}({'✓' if gate_sh else '✗'})  "
          f"WFmin={wfm:.4f}({'✓' if gate_wf else '✗'})  "
          f"DD={dd:.6f}({'✓' if gate_dd else '✗'})  "
          f"Wts={'✓' if gate_wts else '✗'}  → {'PASS' if all_pass else 'FAIL'}")
    if sh > best_sh:
        best_sh = sh
        best_v  = vname

# Find best that passes all gates
best_passing = [vn for vn, vm in variants.items() if vm["all_gates_pass"]]
best_variant_name = None
if best_passing:
    best_variant_name = max(best_passing, key=lambda vn: variants[vn]["oos_sharpe"])
    print(f"\n  Best passing variant: {best_variant_name} (OOS Sh={variants[best_variant_name]['oos_sharpe']:.4f})")
else:
    print(f"\n  No variant passes all gates. Best by Sharpe: {best_v} (Sh={best_sh:.4f})")

accepted = bool(best_passing) and k228_portability_ok

# ─────────────────────────────────────────────────────────────────────────────
# 8. Synergy Analysis
# ─────────────────────────────────────────────────────────────────────────────
print("\n--- Synergy Analysis ---")
k218e_oos_sh = K218_OOS_SH  # reference

synergy = {}
for vname, vm in variants.items():
    delta_sh = vm["oos_sharpe"] - k218e_oos_sh
    delta_wf  = vm["wf_min"] - K218_WF_MIN
    delta_dd  = vm["oos_maxdd"] - K218_MAX_DD
    synergy[vname] = {
        "delta_oos_sh":  round(delta_sh, 4),
        "delta_wf_min":  round(delta_wf, 4),
        "delta_maxdd":   round(delta_dd, 6),
    }
    print(f"  {vname}: ΔSh={delta_sh:+.4f}  ΔWFmin={delta_wf:+.4f}  ΔDD={delta_dd:+.6f}")

# K228 marginal contribution
best_3way_sh = K218_OOS_SH
best_4way_sh = max(vm["oos_sharpe"] for vm in variants.values())
k228_marginal = best_4way_sh - best_3way_sh
print(f"\n  K228 marginal lift (best 4-way vs K218): {k228_marginal:+.4f} Sharpe points")

# ─────────────────────────────────────────────────────────────────────────────
# 9. Equity Curves Output
# ─────────────────────────────────────────────────────────────────────────────
curves_out = {
    "generated_at": datetime.now(timezone.utc).isoformat(),
    "dates": dates_ml,
    "K198":  equity_curve(ret198),
    "K204":  equity_curve(ret204),
    "K208":  equity_curve(ret208),
    "K228_ml": equity_curve(ret228),
}
for vname, vrets in variant_rets.items():
    curves_out[vname] = equity_curve(vrets)

# Add K218 reference curve (K218e = best variant)
with open("/Users/nekonaomichi/crypto-lab/wave_k218_curves.json") as f:
    k218c = json.load(f)
curves_out["K218e_ref"] = k218c["K218e"]

with open("/Users/nekonaomichi/crypto-lab/wave_k230_curves.json", "w") as f:
    json.dump(curves_out, f, indent=2)
print("\nSaved wave_k230_curves.json")

# ─────────────────────────────────────────────────────────────────────────────
# 10. Verdict
# ─────────────────────────────────────────────────────────────────────────────
if accepted and best_variant_name:
    bm = variants[best_variant_name]
    verdict = (f"ACCEPT as K230 v6.8 — best variant: {best_variant_name}  "
               f"(OOS Sh={bm['oos_sharpe']:.4f}, WF min={bm['wf_min']:.4f}, "
               f"MaxDD={bm['oos_maxdd']:.6f})")
else:
    verdict = (f"REJECT — {'K228 fails portability gate' if not k228_portability_ok else 'no variant passes all gates'}. "
               f"Consider K226 integration or regime-gated K225.")

print(f"\n{'='*65}")
print(f"VERDICT: {verdict}")
print(f"{'='*65}")

runtime = time.time() - t0
print(f"\nRuntime: {runtime:.1f}s")

# ─────────────────────────────────────────────────────────────────────────────
# 11. Save Metrics JSON
# ─────────────────────────────────────────────────────────────────────────────

# Per-variant per-fold breakdown for reporting
fold_breakdown = {}
for vname, vrets in variant_rets.items():
    vrets = np.asarray(vrets)
    fold_size = len(vrets) // 4
    fold_breakdown[vname] = []
    for fi in range(4):
        start = fi * fold_size
        end   = (fi + 1) * fold_size if fi < 3 else len(vrets)
        fold_rets = vrets[start:end]
        fold_breakdown[vname].append({
            "fold": fi + 1,
            "start_date": ret_dates[start],
            "end_date":   ret_dates[end - 1],
            "n_days":     len(fold_rets),
            "sharpe":     round(sharpe(fold_rets), 4),
            "ann_ret":    round(float(np.mean(fold_rets) * 365), 4),
            "maxdd":      round(maxdd(fold_rets), 6),
        })

out = {
    "wave": "K230",
    "task": "4-Way Meta-Ensemble: K198 × K204 × K208 × K228",
    "as_of": datetime.now(timezone.utc).isoformat(),
    "runtime_s": round(runtime, 1),
    "k218_reference": {
        "version": "v6.7",
        "best_variant": "K218e",
        "oos_sharpe": K218_OOS_SH,
        "wf_min": K218_WF_MIN,
        "maxdd": K218_MAX_DD,
    },
    "k228_ml_window_validation": {
        "ml_window": f"{dates_ml[0]} → {dates_ml[-1]}",
        "n_days": n,
        "k228_active_days_pct": round(100 * k228_nonzero / n_ret, 1),
        "full_window_sharpe":   round(float(k228_full_sh), 4),
        "oos_sharpe":           k228_oos["oos_sharpe"],
        "oos_maxdd":            k228_oos["oos_maxdd"],
        "oos_ann_ret":          k228_oos["oos_ann_ret"],
        "oos_ann_vol":          k228_oos["oos_ann_vol"],
        "wf_folds":             k228_wf["fold_sharpes"],
        "wf_min":               k228_wf["wf_min"],
        "wf_max":               k228_wf["wf_max"],
        "portability_gate":     f"OOS Sh ≥ {K228_ML_THRESHOLD}",
        "portability_pass":     k228_portability_ok,
        "missing_days":         missing_k228,
    },
    "data_info": {
        "ml_window": f"{dates_ml[0]} → {dates_ml[-1]}",
        "n_days_equity": n,
        "n_days_returns": n_ret,
        "k208_missing_days": missing_k208,
        "k228_missing_days": missing_k228,
    },
    "correlation_matrix": corr_matrix,
    "acceptance_gates": {
        "gate_k228_ml_sh":   f"≥ {K228_ML_THRESHOLD}",
        "gate_oos_sh":       f"> {GATE_OOS_SH}",
        "gate_wf_min":       f"≥ {GATE_WF_MIN}",
        "gate_maxdd":        f"≥ {GATE_MAXDD}",
        "gate_nonzero_wts":  "all > 0.001",
        "k228_portability_pass": k228_portability_ok,
    },
    "baselines": baseline,
    "variants": variants,
    "fold_breakdown": fold_breakdown,
    "synergy": {
        "k228_marginal_lift": round(k228_marginal, 4),
        "per_variant": synergy,
    },
    "verdict": verdict,
    "accepted": accepted,
    "best_variant": best_variant_name,
    "best_variant_metrics": variants[best_variant_name] if best_variant_name else None,
}

with open("/Users/nekonaomichi/crypto-lab/wave_k230_4way_k228.json", "w") as f:
    json.dump(out, f, indent=2)
print("Saved wave_k230_4way_k228.json")

# ─────────────────────────────────────────────────────────────────────────────
# 12. Markdown Report
# ─────────────────────────────────────────────────────────────────────────────

if best_variant_name:
    bm = variants[best_variant_name]
else:
    bm = variants[max(variants, key=lambda k: variants[k]["oos_sharpe"])]
    best_variant_name = max(variants, key=lambda k: variants[k]["oos_sharpe"])

k228v = out["k228_ml_window_validation"]

md_lines = [
    "# Wave K230 — 4-Way Meta-Ensemble: K198 × K204 × K208 × K228",
    "",
    f"> Generated: {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')}  ",
    f"> Runtime: {runtime:.1f}s  ",
    f"> ML Window: {dates_ml[0]} → {dates_ml[-1]} ({n} days)",
    "",
    "---",
    "",
    "## PRIMARY HEADER — K228 ML-Window Standalone Validation",
    "",
    "| Metric | Value | Gate | Result |",
    "|--------|-------|------|--------|",
    f"| OOS Sharpe (30%, ~135d) | {k228v['oos_sharpe']:.4f} | ≥ 1.5 | {'**PASS**' if k228v['portability_pass'] else '**FAIL**'} |",
    f"| OOS MaxDD | {k228v['oos_maxdd']:.6f} | — | — |",
    f"| OOS Ann Return | {k228v['oos_ann_ret']:.4f} | — | — |",
    f"| Full-window Sharpe | {k228v['full_window_sharpe']:.4f} | — | — |",
    f"| WF min (4-fold) | {k228v['wf_min']:.4f} | — | — |",
    f"| WF folds | {k228v['wf_folds']} | — | — |",
    f"| Active trading days | {k228v['k228_active_days_pct']:.1f}% | — | — |",
    "",
]

if k228v["portability_pass"]:
    md_lines += [
        f"> **K228 portability confirmed** (OOS Sh {k228v['oos_sharpe']:.4f} ≥ 1.5).  ",
        "> K225 lesson avoided — window mismatch not present. Proceeding with 4-way ensemble.",
        "",
    ]
else:
    md_lines += [
        f"> **K228 portability FAILED** (OOS Sh {k228v['oos_sharpe']:.4f} < 1.5).  ",
        "> ABORT 4-way integration. Recommend K226 or compound regime-gate K225.",
        "",
    ]

md_lines += [
    "---",
    "",
    "## 4×4 Correlation Matrix",
    "",
    "| | K198 | K204 | K208 | K228 |",
    "|---|---|---|---|---|",
]
for pi in portfolios:
    row_vals = " | ".join(f"{corr_matrix[pi][pj]:.4f}" for pj in portfolios)
    md_lines.append(f"| {pi} | {row_vals} |")

md_lines += [
    "",
    "*All K228 pairwise correlations expected < 0.5 for genuine diversification.*",
    "",
    "---",
    "",
    "## Standalone Baselines (ML Window)",
    "",
    "| Portfolio | OOS Sh | WF Min | WF Folds | OOS MaxDD | Active% |",
    "|-----------|--------|--------|----------|-----------|---------|",
]
for pi, rets in zip(portfolios, [ret198, ret204, ret208, ret228]):
    bsl = baseline[pi]
    act = "—"
    if pi == "K228":
        act = f"{k228v['k228_active_days_pct']:.1f}%"
    elif pi == "K208":
        act = "~67% (8h bars → daily)"
    else:
        act = "100%"
    md_lines.append(
        f"| {pi} | {bsl['oos_sharpe']:.4f} | {bsl['wf_min']:.4f} | {bsl['fold_sharpes']} | "
        f"{bsl['oos_maxdd']:.6f} | {act} |"
    )

md_lines += [
    "",
    "---",
    "",
    "## Variant Results",
    "",
    "| Variant | Description | OOS Sh | WF Min | WF Folds | OOS MaxDD | DR | Gates |",
    "|---------|-------------|--------|--------|----------|-----------|----|-------|",
]
for vname, vm in variants.items():
    gates_str = ("ALL PASS" if vm["all_gates_pass"]
                 else ("Sh✗" if not vm["gate_sh"] else "") +
                      (" WF✗" if not vm["gate_wf"] else "") +
                      (" DD✗" if not vm["gate_dd"] else "") +
                      (" Wts✗" if not vm["gate_wts"] else ""))
    md_lines.append(
        f"| {vname} | {vm['description']} | {vm['oos_sharpe']:.4f} | "
        f"{vm['wf_min']:.4f} | {vm['fold_sharpes']} | {vm['oos_maxdd']:.6f} | "
        f"{vm['diversification_ratio']:.4f} | {gates_str} |"
    )

md_lines += [
    "",
    "---",
    "",
    "## Per-Variant Per-Fold Breakdown",
    "",
]
for vname in variants:
    md_lines.append(f"### {vname} — {variants[vname]['description']}")
    md_lines.append("")
    md_lines.append("| Fold | Period | Days | Sharpe | Ann Ret | MaxDD |")
    md_lines.append("|------|--------|------|--------|---------|-------|")
    for fd in fold_breakdown[vname]:
        md_lines.append(
            f"| {fd['fold']} | {fd['start_date']} → {fd['end_date']} | {fd['n_days']} | "
            f"{fd['sharpe']:.4f} | {fd['ann_ret']:.4f} | {fd['maxdd']:.6f} |"
        )
    md_lines.append("")
    md_lines.append(f"Avg weights: " +
                    ", ".join(f"{p}={w:.3f}" for p, w in zip(portfolios, variants[vname]["avg_weights"])))
    md_lines.append("")

md_lines += [
    "---",
    "",
    "## Synergy Analysis",
    "",
    f"**K228 marginal lift** (best 4-way vs K218 v6.7): **{k228_marginal:+.4f} Sharpe points**",
    "",
    "| Variant | ΔOos Sh | ΔWF Min | ΔMaxDD |",
    "|---------|---------|---------|--------|",
]
for vname, sv in synergy.items():
    md_lines.append(
        f"| {vname} | {sv['delta_oos_sh']:+.4f} | {sv['delta_wf_min']:+.4f} | {sv['delta_maxdd']:+.6f} |"
    )

md_lines += [
    "",
    "---",
    "",
    "## Verdict — K230 v6.8 if Accepted",
    "",
    f"**{verdict}**",
    "",
    "### Acceptance Gate Summary",
    "",
    f"| Gate | Threshold | Result |",
    f"|------|-----------|--------|",
    f"| K228 ML-window OOS Sh | ≥ 1.5 | {k228v['oos_sharpe']:.4f} → {'PASS' if k228_portability_ok else 'FAIL'} |",
    f"| Best variant OOS Sh | > {GATE_OOS_SH:.2f} | {bm['oos_sharpe']:.4f} → {'PASS' if bm['gate_sh'] else 'FAIL'} |",
    f"| WF min | ≥ {GATE_WF_MIN} | {bm['wf_min']:.4f} → {'PASS' if bm['gate_wf'] else 'FAIL'} |",
    f"| MaxDD | ≥ {GATE_MAXDD} | {bm['oos_maxdd']:.6f} → {'PASS' if bm['gate_dd'] else 'FAIL'} |",
    f"| Non-zero weights | all > 0.001 | {'PASS' if bm['gate_wts'] else 'FAIL'} |",
    "",
]

if accepted and best_variant_name:
    md_lines += [
        f"### {best_variant_name} Configuration (Production v6.8)",
        "",
        f"| Component | Weight | Role |",
        f"|-----------|--------|------|",
    ]
    for p, w in zip(portfolios, bm["avg_weights"]):
        roles = {
            "K198": "ML ridge regression momentum core",
            "K204": "ML drawdown-embedded signals",
            "K208": "DAR(2,1) reverse-carry panel (ultra-low vol)",
            "K228": "Stablecoin mint/burn momentum (sparse signal)",
        }
        md_lines.append(f"| {p} | {w:.3f} | {roles[p]} |")
    md_lines += [
        "",
        f"OOS Sharpe: **{bm['oos_sharpe']:.4f}** (vs K218 {K218_OOS_SH:.2f}, Δ{bm['oos_sharpe']-K218_OOS_SH:+.4f})  ",
        f"WF min: **{bm['wf_min']:.4f}** (vs K218 {K218_WF_MIN:.2f})  ",
        f"MaxDD: **{bm['oos_maxdd']:.6f}** (vs K218 {K218_MAX_DD:.4f})  ",
        "",
    ]
else:
    md_lines += [
        "### Recommendations",
        "",
        "- K228 ML-window validation failed OR no variant passes all gates",
        "- Alternative path 1: Integrate K226 (ETH validator queue strategy)",
        "- Alternative path 2: Compound regime-gate for K225 (ETF flow regime)",
        "- Revisit K228 with narrower window alignment or signal smoothing",
        "",
    ]

md_lines += [
    "---",
    "",
    f"*Wave K230 | Runtime {runtime:.1f}s | {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')}*",
]

report_text = "\n".join(md_lines)
with open("/Users/nekonaomichi/crypto-lab/wave_k230_4way_k228.md", "w") as f:
    f.write(report_text)
print("Saved wave_k230_4way_k228.md")

# Summary
print("\n" + "="*65)
print("SUMMARY")
print("="*65)
print(f"K228 portability gate (OOS Sh ≥ 1.5): {'PASS' if k228_portability_ok else 'FAIL'} ({k228_oos['oos_sharpe']:.4f})")
print(f"Best variant: {best_variant_name}")
if best_variant_name:
    bm2 = variants[best_variant_name]
    print(f"  OOS Sh: {bm2['oos_sharpe']:.4f} (gate: > {GATE_OOS_SH:.2f})")
    print(f"  WF min: {bm2['wf_min']:.4f} (gate: ≥ {GATE_WF_MIN:.2f})")
    print(f"  MaxDD:  {bm2['oos_maxdd']:.6f} (gate: ≥ {GATE_MAXDD:.4f})")
print(f"Accepted: {accepted}")
print(f"Verdict: {verdict}")
print("="*65)

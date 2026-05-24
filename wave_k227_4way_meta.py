"""
Wave K227 — 4-Way Meta-Ensemble: K198 × K204 × K208 × K225

Extends K218 v6.7 (3-way meta-ensemble, OOS Sh 11.03) with a 4th portfolio:
  K225 = Spot BTC ETF 7-Day Flow Regime (z=1.25, hold=14d)
  |ρ| vs K218 components: 0.009/−0.030/0.014 (essentially zero — orthogonal)

Variants:
  K227a — Equal weight 25/25/25/25
  K227b — Inverse-volatility weighted (rolling 30d)
  K227c — Inv-vol + K225 cap 25%
  K227d — Inv-vol + K208/K225 both cap 25%
  K227e — MVP (Minimum Variance Portfolio across 4, rolling 60d covariance)

Acceptance gates vs K218 v6.7:
  OOS Sh  > 11.13  (+0.10 vs K218e 11.03)
  WF min  ≥  6.93  (≥ K218e WF min)
  MaxDD   ≤ -0.0036  (≤ K218e MaxDD)
  All 4 portfolios get non-zero weight (genuine diversification)

K227 deliverables:
  wave_k227_4way_meta.py      — this script
  wave_k227_4way_meta.json    — metrics + correlations + DR
  wave_k227_curves.json       — equity curves
  wave_k227_4way_meta.md      — full report
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
with open("/Users/nekonaomichi/crypto-lab/wave_k225_curves.json") as f:
    k225_raw = json.load(f)

# K198 and K204 share the same 448-day ML window (daily)
dates_ml = k198_raw["dates_ml"]   # 2025-01-22 → 2026-04-14, len=448
eq198    = np.array(k198_raw["equity_ridge"])
eq204    = np.array(k204_raw["equity_k204"])

# K208 is 8h resolution — collapse to daily closing PnL
k208_ts   = k208_raw["K208_filtered"]["timestamps"]
k208_cpnl = k208_raw["K208_filtered"]["cumulative_pnl"]

k208_daily = {}
for ts_str, cpnl in zip(k208_ts, k208_cpnl):
    date_part = ts_str[:10]
    k208_daily[date_part] = cpnl  # last entry of day wins

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
        if k208_eq_values:
            k208_eq_values.append(k208_eq_values[-1])
        else:
            k208_eq_values.append(1.0)

eq208 = np.array(k208_eq_values)

# K225 — primary_btc_z1 (z=1.25, hold=14d) daily equity
# Date range: 2024-05-23 → 2026-05-22; need to align to dates_ml
k225_se    = k225_raw["strategy_equity"]["primary_btc_z1"]
k225_dates = k225_se["dates"]   # list of "YYYY-MM-DD"
k225_eq    = k225_se["equity"]  # cumulative equity (starts at ~1.0)

# Build a date → equity map for K225
k225_daily = {}
for d, eq in zip(k225_dates, k225_eq):
    k225_daily[d] = eq

# Align K225 to dates_ml window (carry-forward if missing)
k225_eq_values = []
missing_k225 = 0
for d in dates_ml:
    if d in k225_daily:
        k225_eq_values.append(k225_daily[d])
    else:
        missing_k225 += 1
        if k225_eq_values:
            k225_eq_values.append(k225_eq_values[-1])
        else:
            # Look for nearest prior date
            k225_eq_values.append(1.0)

eq225 = np.array(k225_eq_values)

# Re-base K225 so it starts at 1.0 on first dates_ml date
eq225 = eq225 / eq225[0]

n = len(dates_ml)
assert len(eq198) == len(eq204) == len(eq208) == len(eq225) == n, (
    f"Length mismatch: K198={len(eq198)}, K204={len(eq204)}, K208={len(eq208)}, K225={len(eq225)}, dates={n}"
)

print(f"Data loaded: {n} days ({dates_ml[0]} -> {dates_ml[-1]})")
print(f"K208 missing days filled forward: {missing_k208}/{n}")
print(f"K225 missing days filled forward: {missing_k225}/{n}")
print(f"K198 equity range: [{eq198.min():.4f}, {eq198.max():.4f}]")
print(f"K204 equity range: [{eq204.min():.4f}, {eq204.max():.4f}]")
print(f"K208 equity range: [{eq208.min():.4f}, {eq208.max():.4f}]")
print(f"K225 equity range: [{eq225.min():.4f}, {eq225.max():.4f}]")

# Daily returns (geometric)
ret198 = np.diff(eq198) / eq198[:-1]
ret204 = np.diff(eq204) / eq204[:-1]
ret208 = np.diff(eq208) / eq208[:-1]
ret225 = np.diff(eq225) / eq225[:-1]
ret_dates = dates_ml[1:]   # n-1 return dates
n_ret = len(ret198)

print(f"\nReturn series length: {n_ret}")
print(f"K198 daily ret stats: mean={ret198.mean():.6f}, std={ret198.std():.6f}")
print(f"K204 daily ret stats: mean={ret204.mean():.6f}, std={ret204.std():.6f}")
print(f"K208 daily ret stats: mean={ret208.mean():.6f}, std={ret208.std():.6f}")
print(f"K225 daily ret stats: mean={ret225.mean():.6f}, std={ret225.std():.6f}")

# ─────────────────────────────────────────────────────────
# 2. 4×4 correlation matrix
# ─────────────────────────────────────────────────────────
rets_all = np.stack([ret198, ret204, ret208, ret225], axis=0)  # (4, T)
rho_matrix = np.corrcoef(rets_all)

labels = ["K198", "K204", "K208", "K225"]
print(f"\n--- 4x4 Pairwise Correlation Matrix ---")
header = "              " + "  ".join(f"{l:>8}" for l in labels)
print(header)
for i, li in enumerate(labels):
    row = f"{li:10}    " + "  ".join(f"{rho_matrix[i,j]:8.4f}" for j in range(4))
    print(row)

rho_198_204 = float(rho_matrix[0, 1])
rho_198_208 = float(rho_matrix[0, 2])
rho_198_225 = float(rho_matrix[0, 3])
rho_204_208 = float(rho_matrix[1, 2])
rho_204_225 = float(rho_matrix[1, 3])
rho_208_225 = float(rho_matrix[2, 3])

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
    fold_details = []
    for i in range(n_folds):
        start = i * fold_size
        end   = (i + 1) * fold_size if i < n_folds - 1 else len(rets)
        fs = sharpe(rets[start:end])
        fold_sharpes.append(fs)
        fold_details.append({
            "fold": i + 1,
            "start_idx": start,
            "end_idx": end,
            "n_days": end - start,
            "sharpe": round(float(fs), 4),
        })
    return {
        "fold_sharpes":  [round(s, 4) for s in fold_sharpes],
        "fold_details":  fold_details,
        "wf_mean":       round(float(np.mean(fold_sharpes)), 4),
        "wf_min":        round(float(np.min(fold_sharpes)), 4),
        "wf_max":        round(float(np.max(fold_sharpes)), 4),
        "wf_std":        round(float(np.std(fold_sharpes, ddof=1)), 4),
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
    Diversification Ratio = (w . sigma_i) / sigma_portfolio
    rets_matrix: shape (4, T)
    """
    w = np.array(w)
    individual_vols = np.array([np.std(r, ddof=1) for r in rets_matrix])
    weighted_vol_sum = float(np.dot(w, individual_vols))
    port_rets = np.dot(w, rets_matrix)
    port_vol  = float(np.std(port_rets, ddof=1))
    if port_vol < 1e-12:
        return np.nan
    return round(weighted_vol_sum / port_vol, 4)

# ─────────────────────────────────────────────────────────
# 4. Baseline metrics (K198, K204, K208, K225 standalone)
# ─────────────────────────────────────────────────────────
print("\n--- Baseline metrics (on ML-window returns) ---")
baseline = {}
for name, rets in [("K198", ret198), ("K204", ret204), ("K208", ret208), ("K225", ret225)]:
    m = oos_metrics(rets)
    w = wf_stats(rets)
    m.update(w)
    baseline[name] = m
    print(f"{name}: OOS Sh={m['oos_sharpe']:.4f}  MaxDD={m['oos_maxdd']:.6f}  "
          f"WF mean={m['wf_mean']:.4f}  WF min={m['wf_min']:.4f}")

# ─────────────────────────────────────────────────────────
# 5. 4-Way meta-allocator variants
# ─────────────────────────────────────────────────────────
variants = {}
variant_rets = {}

ROLL = 30  # rolling window for inv-vol
ROLL_MVP = 60  # rolling window for MVP

# ── K227a: Equal weight 25/25/25/25 ──────────────────────
print("\n--- K227a: Equal weight 25/25/25/25 ---")
w_eq = np.array([0.25, 0.25, 0.25, 0.25])
ret_a = w_eq[0]*ret198 + w_eq[1]*ret204 + w_eq[2]*ret208 + w_eq[3]*ret225
m = oos_metrics(ret_a)
w_wf = wf_stats(ret_a)
m.update(w_wf)
m["description"] = "Equal weight 25/25/25/25"
m["avg_weights"] = [round(float(w), 4) for w in w_eq]
m["diversification_ratio"] = diversification_ratio(w_eq, rets_all)
variants["K227a"] = m
variant_rets["K227a"] = ret_a
print(f"K227a: OOS Sh={m['oos_sharpe']:.4f}  MaxDD={m['oos_maxdd']:.6f}  "
      f"WF mean={m['wf_mean']:.4f}  WF min={m['wf_min']:.4f}  DR={m['diversification_ratio']:.4f}")

# ── K227b: Inv-vol weighted (rolling 30d) ────────────────
print("\n--- K227b: Inv-vol weighted (30d rolling) ---")
inv_vol_rets_b = np.zeros(n_ret)
w_traj_b = np.zeros((n_ret, 4))
for i in range(n_ret):
    start_w = max(0, i - ROLL)
    v198 = np.std(ret198[start_w:i+1], ddof=1) if i - start_w >= 2 else 1e-6
    v204 = np.std(ret204[start_w:i+1], ddof=1) if i - start_w >= 2 else 1e-6
    v208 = np.std(ret208[start_w:i+1], ddof=1) if i - start_w >= 2 else 1e-6
    v225 = np.std(ret225[start_w:i+1], ddof=1) if i - start_w >= 2 else 1e-6
    iv198 = 1.0 / max(v198, 1e-9)
    iv204 = 1.0 / max(v204, 1e-9)
    iv208 = 1.0 / max(v208, 1e-9)
    iv225 = 1.0 / max(v225, 1e-9)
    total = iv198 + iv204 + iv208 + iv225
    wb = np.array([iv198/total, iv204/total, iv208/total, iv225/total])
    w_traj_b[i] = wb
    inv_vol_rets_b[i] = wb[0]*ret198[i] + wb[1]*ret204[i] + wb[2]*ret208[i] + wb[3]*ret225[i]

m = oos_metrics(inv_vol_rets_b)
w_wf = wf_stats(inv_vol_rets_b)
m.update(w_wf)
m["description"] = "Inverse-vol weighted (30d rolling)"
m["avg_weights"] = [round(float(w_traj_b[:,j].mean()), 4) for j in range(4)]
m["diversification_ratio"] = diversification_ratio(w_traj_b.mean(axis=0), rets_all)
variants["K227b"] = m
variant_rets["K227b"] = inv_vol_rets_b
print(f"K227b: OOS Sh={m['oos_sharpe']:.4f}  MaxDD={m['oos_maxdd']:.6f}  "
      f"WF mean={m['wf_mean']:.4f}  WF min={m['wf_min']:.4f}  DR={m['diversification_ratio']:.4f}")
print(f"       Avg weights: K198={m['avg_weights'][0]:.3f}, K204={m['avg_weights'][1]:.3f}, "
      f"K208={m['avg_weights'][2]:.3f}, K225={m['avg_weights'][3]:.3f}")

# ── K227c: Inv-vol + K225 cap 25% ────────────────────────
print("\n--- K227c: Inv-vol + K225 cap 25% (30d rolling) ---")
CAP225_C = 0.25
inv_vol_rets_c = np.zeros(n_ret)
w_traj_c = np.zeros((n_ret, 4))
for i in range(n_ret):
    start_w = max(0, i - ROLL)
    v198 = np.std(ret198[start_w:i+1], ddof=1) if i - start_w >= 2 else 1e-6
    v204 = np.std(ret204[start_w:i+1], ddof=1) if i - start_w >= 2 else 1e-6
    v208 = np.std(ret208[start_w:i+1], ddof=1) if i - start_w >= 2 else 1e-6
    v225 = np.std(ret225[start_w:i+1], ddof=1) if i - start_w >= 2 else 1e-6
    iv198 = 1.0 / max(v198, 1e-9)
    iv204 = 1.0 / max(v204, 1e-9)
    iv208 = 1.0 / max(v208, 1e-9)
    iv225 = 1.0 / max(v225, 1e-9)
    total = iv198 + iv204 + iv208 + iv225
    wc = np.array([iv198/total, iv204/total, iv208/total, iv225/total])
    # Apply K225 cap
    if wc[3] > CAP225_C:
        wc[3] = CAP225_C
        iv_rest = np.array([iv198, iv204, iv208])
        wc[:3] = iv_rest / iv_rest.sum() * (1.0 - CAP225_C)
    w_traj_c[i] = wc
    inv_vol_rets_c[i] = wc[0]*ret198[i] + wc[1]*ret204[i] + wc[2]*ret208[i] + wc[3]*ret225[i]

m = oos_metrics(inv_vol_rets_c)
w_wf = wf_stats(inv_vol_rets_c)
m.update(w_wf)
m["description"] = "Inv-vol weighted (30d rolling) + K225 max-weight cap 25%"
m["avg_weights"] = [round(float(w_traj_c[:,j].mean()), 4) for j in range(4)]
m["diversification_ratio"] = diversification_ratio(w_traj_c.mean(axis=0), rets_all)
variants["K227c"] = m
variant_rets["K227c"] = inv_vol_rets_c
print(f"K227c: OOS Sh={m['oos_sharpe']:.4f}  MaxDD={m['oos_maxdd']:.6f}  "
      f"WF mean={m['wf_mean']:.4f}  WF min={m['wf_min']:.4f}  DR={m['diversification_ratio']:.4f}")
print(f"       Avg weights: K198={m['avg_weights'][0]:.3f}, K204={m['avg_weights'][1]:.3f}, "
      f"K208={m['avg_weights'][2]:.3f}, K225={m['avg_weights'][3]:.3f}")

# ── K227d: Inv-vol + K208 cap 25% + K225 cap 25% ─────────
print("\n--- K227d: Inv-vol + K208/K225 both cap 25% (30d rolling) ---")
CAP208_D = 0.25
CAP225_D = 0.25
inv_vol_rets_d = np.zeros(n_ret)
w_traj_d = np.zeros((n_ret, 4))

def apply_two_caps(iv198, iv204, iv208, iv225, cap208, cap225):
    """
    Apply caps to K208 (idx=2) and K225 (idx=3) iteratively.
    Redistribute excess to K198 and K204 proportionally.
    """
    iv = np.array([iv198, iv204, iv208, iv225])
    w = iv / iv.sum()
    # Iterative cap application (max 3 iterations)
    for _ in range(3):
        changed = False
        if w[2] > cap208:
            excess = w[2] - cap208
            w[2] = cap208
            # Redistribute to K198, K204, K225 proportionally by iv
            iv_others = np.array([iv198, iv204, iv225])
            w[:2] += iv_others[:2] / iv_others.sum() * excess
            w[3] += iv_others[2] / iv_others.sum() * excess
            changed = True
        if w[3] > cap225:
            excess = w[3] - cap225
            w[3] = cap225
            iv_others = np.array([iv198, iv204, iv208])
            w[:3] += iv_others / iv_others.sum() * excess
            changed = True
        if not changed:
            break
    # Final normalise (floating point safety)
    w = np.maximum(w, 0.0)
    s = w.sum()
    if s > 1e-12:
        w = w / s
    return w

for i in range(n_ret):
    start_w = max(0, i - ROLL)
    v198 = np.std(ret198[start_w:i+1], ddof=1) if i - start_w >= 2 else 1e-6
    v204 = np.std(ret204[start_w:i+1], ddof=1) if i - start_w >= 2 else 1e-6
    v208 = np.std(ret208[start_w:i+1], ddof=1) if i - start_w >= 2 else 1e-6
    v225 = np.std(ret225[start_w:i+1], ddof=1) if i - start_w >= 2 else 1e-6
    iv198 = 1.0 / max(v198, 1e-9)
    iv204 = 1.0 / max(v204, 1e-9)
    iv208 = 1.0 / max(v208, 1e-9)
    iv225 = 1.0 / max(v225, 1e-9)
    wd = apply_two_caps(iv198, iv204, iv208, iv225, CAP208_D, CAP225_D)
    w_traj_d[i] = wd
    inv_vol_rets_d[i] = wd[0]*ret198[i] + wd[1]*ret204[i] + wd[2]*ret208[i] + wd[3]*ret225[i]

m = oos_metrics(inv_vol_rets_d)
w_wf = wf_stats(inv_vol_rets_d)
m.update(w_wf)
m["description"] = "Inv-vol weighted (30d rolling) + K208 cap 25% + K225 cap 25%"
m["avg_weights"] = [round(float(w_traj_d[:,j].mean()), 4) for j in range(4)]
m["diversification_ratio"] = diversification_ratio(w_traj_d.mean(axis=0), rets_all)
variants["K227d"] = m
variant_rets["K227d"] = inv_vol_rets_d
print(f"K227d: OOS Sh={m['oos_sharpe']:.4f}  MaxDD={m['oos_maxdd']:.6f}  "
      f"WF mean={m['wf_mean']:.4f}  WF min={m['wf_min']:.4f}  DR={m['diversification_ratio']:.4f}")
print(f"       Avg weights: K198={m['avg_weights'][0]:.3f}, K204={m['avg_weights'][1]:.3f}, "
      f"K208={m['avg_weights'][2]:.3f}, K225={m['avg_weights'][3]:.3f}")

# ── K227e: Minimum Variance Portfolio (rolling 60d covariance) ──
print("\n--- K227e: Minimum Variance Portfolio (rolling 60d covariance) ---")
mvp_rets_e = np.zeros(n_ret)
w_traj_e = np.zeros((n_ret, 4))

def mvp_weights_4(cov_matrix):
    """
    Minimum Variance Portfolio weights (long-only, sum to 1) for 4 assets.
    w = Sigma^{-1} 1 / (1' Sigma^{-1} 1), with long-only floor.
    """
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

for i in range(n_ret):
    start_w = max(0, i - ROLL_MVP)
    seg = np.stack([ret198[start_w:i+1],
                    ret204[start_w:i+1],
                    ret208[start_w:i+1],
                    ret225[start_w:i+1]], axis=0)
    if seg.shape[1] >= 5:
        cov = np.cov(seg)  # (4,4)
        we = mvp_weights_4(cov)
    else:
        we = np.array([0.25, 0.25, 0.25, 0.25])
    w_traj_e[i] = we
    mvp_rets_e[i] = we[0]*ret198[i] + we[1]*ret204[i] + we[2]*ret208[i] + we[3]*ret225[i]

m = oos_metrics(mvp_rets_e)
w_wf = wf_stats(mvp_rets_e)
m.update(w_wf)
m["description"] = "Minimum Variance Portfolio (rolling 60d covariance, long-only)"
m["avg_weights"] = [round(float(w_traj_e[:,j].mean()), 4) for j in range(4)]
m["diversification_ratio"] = diversification_ratio(w_traj_e.mean(axis=0), rets_all)
variants["K227e"] = m
variant_rets["K227e"] = mvp_rets_e
print(f"K227e: OOS Sh={m['oos_sharpe']:.4f}  MaxDD={m['oos_maxdd']:.6f}  "
      f"WF mean={m['wf_mean']:.4f}  WF min={m['wf_min']:.4f}  DR={m['diversification_ratio']:.4f}")
print(f"       Avg weights: K198={m['avg_weights'][0]:.3f}, K204={m['avg_weights'][1]:.3f}, "
      f"K208={m['avg_weights'][2]:.3f}, K225={m['avg_weights'][3]:.3f}")

# ─────────────────────────────────────────────────────────
# 6. Acceptance gates vs K218 v6.7 (K218e)
# ─────────────────────────────────────────────────────────
K218_OOS_SH  = 11.031
K218_WF_MIN  = 6.9282
K218_WF_MEAN = 8.316
K218_MAXDD   = -0.00364

GATE_OOS_SH  = K218_OOS_SH + 0.10   # 11.131
GATE_WF_MIN  = K218_WF_MIN           # >= 6.9282
GATE_MAXDD   = K218_MAXDD            # <= -0.0036

print(f"\n--- Acceptance Gates (vs K218 v6.7) ---")
print(f"Required: OOS Sh > {GATE_OOS_SH:.4f}  |  WF min >= {GATE_WF_MIN:.4f}  |  MaxDD <= {GATE_MAXDD:.6f}")
print(f"          All 4 portfolios must receive non-zero weight (>1%)")

candidates = []
for vname, vm in variants.items():
    sh_pass  = vm["oos_sharpe"] > GATE_OOS_SH
    wf_pass  = vm["wf_min"] >= GATE_WF_MIN
    dd_pass  = vm["oos_maxdd"] >= GATE_MAXDD
    min_wt   = min(vm["avg_weights"])
    wt_pass  = min_wt > 0.01
    all_pass = sh_pass and wf_pass and dd_pass and wt_pass
    score    = vm["oos_sharpe"] + vm["wf_min"]

    print(f"  {vname}: OOS={vm['oos_sharpe']:.4f}({'v' if sh_pass else 'x'})  "
          f"WFmin={vm['wf_min']:.4f}({'v' if wf_pass else 'x'})  "
          f"MaxDD={vm['oos_maxdd']:.6f}({'v' if dd_pass else 'x'})  "
          f"MinWt={min_wt:.3f}({'v' if wt_pass else 'x'})  "
          f"-> {'PASS' if all_pass else 'FAIL'}")
    if all_pass:
        candidates.append((score, vname, vm))

candidates.sort(reverse=True)
best_name = candidates[0][1] if candidates else None
best_vm   = candidates[0][2] if candidates else None
accepted  = best_name is not None

# ─────────────────────────────────────────────────────────
# 7. Synergy analysis
# ─────────────────────────────────────────────────────────
print("\n--- Synergy Analysis ---")
sh198_oos = baseline["K198"]["oos_sharpe"]
sh204_oos = baseline["K204"]["oos_sharpe"]
sh208_oos = baseline["K208"]["oos_sharpe"]
sh225_oos = baseline["K225"]["oos_sharpe"]
avg_individual = (sh198_oos + sh204_oos + sh208_oos + sh225_oos) / 4.0
print(f"Individual OOS Sharpes: K198={sh198_oos:.4f}, K204={sh204_oos:.4f}, "
      f"K208={sh208_oos:.4f}, K225={sh225_oos:.4f}")
print(f"Average of 4 individuals: {avg_individual:.4f}")

if best_vm:
    synergy_sh = best_vm["oos_sharpe"] - avg_individual
    synergy_vs_k218 = best_vm["oos_sharpe"] - K218_OOS_SH
    synergy_detected = synergy_sh > 0.02
    print(f"Best ensemble ({best_name}): {best_vm['oos_sharpe']:.4f}")
    print(f"Synergy vs avg individuals:  {synergy_sh:+.4f} ({'GENUINE' if synergy_detected else 'WEAK'})")
    print(f"Improvement vs K218 v6.7:    {synergy_vs_k218:+.4f}")
    avg_wf_min = np.mean([baseline[n]["wf_min"] for n in ["K198","K204","K208","K225"]])
    wf_min_synergy = best_vm["wf_min"] - avg_wf_min
    print(f"WF-min avg individuals: {avg_wf_min:.4f}  |  Best ensemble WF-min: {best_vm['wf_min']:.4f}  |  D: {wf_min_synergy:+.4f}")
else:
    synergy_sh = 0.0
    synergy_vs_k218 = 0.0
    synergy_detected = False
    print("No accepted candidate. Reporting best-by-OOS-Sh variant:")
    # Still compute for reporting
    best_oos = max(variants.items(), key=lambda x: x[1]["oos_sharpe"])
    best_name_report = best_oos[0]
    best_vm_report = best_oos[1]
    print(f"  Best (OOS Sh): {best_name_report}: {best_vm_report['oos_sharpe']:.4f}")

# ─────────────────────────────────────────────────────────
# 8. Build equity curves for output
# ─────────────────────────────────────────────────────────
curves = {
    "K198":   equity_curve(ret198),
    "K204":   equity_curve(ret204),
    "K208":   equity_curve(ret208),
    "K225":   equity_curve(ret225),
    "K227a":  equity_curve(variant_rets["K227a"]),
    "K227b":  equity_curve(variant_rets["K227b"]),
    "K227c":  equity_curve(variant_rets["K227c"]),
    "K227d":  equity_curve(variant_rets["K227d"]),
    "K227e":  equity_curve(variant_rets["K227e"]),
    "K218e_ref": equity_curve(  # K218e reference from K198+K204+K208 with inv-vol + cap30%
        0.35 * ret198 + 0.35 * ret204 + 0.30 * ret208  # approx K218e avg weights
    ),
    "dates": [dates_ml[0]] + list(ret_dates),
}

# ─────────────────────────────────────────────────────────
# 9. Save JSON outputs
# ─────────────────────────────────────────────────────────
runtime = round(time.time() - t0, 2)

verdict = (
    f"ACCEPT as K227 v6.8 — best variant: {best_name}"
    if accepted
    else "REJECT — no variant passes all acceptance gates vs K218 v6.7"
)

def corr_interp(rho):
    a = abs(rho)
    if a > 0.8:
        return "High"
    elif a > 0.5:
        return "Moderate"
    else:
        return "Low"

corr_mat_list = [[round(rho_matrix[i,j], 4) for j in range(4)] for i in range(4)]

# Per-variant fold breakdown for report
fold_breakdown = {}
for vname, vm in variants.items():
    fold_breakdown[vname] = vm["fold_details"]

synergy_block = {
    "individual_oos_sharpes": {
        "K198": sh198_oos,
        "K204": sh204_oos,
        "K208": sh208_oos,
        "K225": sh225_oos,
    },
    "avg_individual_oos_sh":  round(avg_individual, 4),
    "best_ensemble_name":     best_name,
    "best_ensemble_oos_sh":   round(best_vm["oos_sharpe"], 4) if best_vm else None,
    "synergy_delta_vs_avg":   round(synergy_sh, 4),
    "synergy_delta_vs_k218":  round(synergy_vs_k218, 4),
    "synergy_detected":       synergy_detected,
    "avg_individual_wf_min":  round(float(np.mean([baseline[n]["wf_min"] for n in ["K198","K204","K208","K225"]])), 4),
    "best_ensemble_wf_min":   round(best_vm["wf_min"], 4) if best_vm else None,
}

five_way_comparison = {
    "K198_v6.5":    {"oos_sharpe": 10.28,  "oos_maxdd": -0.0053, "wf_mean": 7.91, "wf_min": 6.57,   "components": 1},
    "K217_v6.6":    {"oos_sharpe": 10.43,  "oos_maxdd": -0.0053, "wf_mean": 8.01, "wf_min": 6.91,   "components": 2},
    "K218e_v6.7":   {"oos_sharpe": K218_OOS_SH, "oos_maxdd": K218_MAXDD, "wf_mean": K218_WF_MEAN, "wf_min": K218_WF_MIN, "components": 3},
}
for vname, vm in variants.items():
    five_way_comparison[f"K227_{vname[-1]}"] = {
        "oos_sharpe": vm["oos_sharpe"],
        "oos_maxdd":  vm["oos_maxdd"],
        "wf_mean":    vm["wf_mean"],
        "wf_min":     vm["wf_min"],
        "dr":         vm["diversification_ratio"],
        "components": 4,
        "avg_weights": vm["avg_weights"],
    }

result = {
    "wave": "K227",
    "task": "4-Way Meta-Ensemble: K198 x K204 x K208 x K225 (ETF Flow Regime)",
    "as_of": datetime.now(timezone.utc).isoformat(),
    "runtime_s": runtime,
    "data_info": {
        "n_days": n,
        "date_start": dates_ml[0],
        "date_end": dates_ml[-1],
        "n_returns": n_ret,
        "k208_missing_days": missing_k208,
        "k225_missing_days": missing_k225,
        "k225_variant": "primary_btc_z1 (z=1.25, hold=14d)",
    },
    "correlation_matrix": {
        "labels": labels,
        "matrix": corr_mat_list,
        "pairwise": {
            "rho_198_204": round(rho_198_204, 4),
            "rho_198_208": round(rho_198_208, 4),
            "rho_198_225": round(rho_198_225, 4),
            "rho_204_208": round(rho_204_208, 4),
            "rho_204_225": round(rho_204_225, 4),
            "rho_208_225": round(rho_208_225, 4),
        },
        "interpretation": {
            "rho_198_204": corr_interp(rho_198_204),
            "rho_198_208": corr_interp(rho_198_208),
            "rho_198_225": corr_interp(rho_198_225),
            "rho_204_208": corr_interp(rho_204_208),
            "rho_204_225": corr_interp(rho_204_225),
            "rho_208_225": corr_interp(rho_208_225),
        }
    },
    "acceptance_gates": {
        "oos_sharpe_threshold": GATE_OOS_SH,
        "wf_min_threshold":     GATE_WF_MIN,
        "maxdd_threshold":      GATE_MAXDD,
        "min_weight_per_portfolio": 0.01,
        "reference": "K218e v6.7",
    },
    "baselines": baseline,
    "variants": variants,
    "fold_breakdown": fold_breakdown,
    "synergy": synergy_block,
    "five_way_comparison": five_way_comparison,
    "verdict": verdict,
    "accepted": accepted,
    "best_variant": best_name,
    "best_variant_metrics": best_vm,
}

with open("/Users/nekonaomichi/crypto-lab/wave_k227_4way_meta.json", "w") as f:
    json.dump(result, f, indent=2)
print("\nSaved: wave_k227_4way_meta.json")

with open("/Users/nekonaomichi/crypto-lab/wave_k227_curves.json", "w") as f:
    json.dump(curves, f)
print("Saved: wave_k227_curves.json")

print(f"\nRuntime: {runtime}s")
print(f"\nVERDICT: {verdict}")

# ─────────────────────────────────────────────────────────
# 10. Generate Markdown report
# ─────────────────────────────────────────────────────────
rho = result["correlation_matrix"]["pairwise"]

report_lines = [
    "# Wave K227 — 4-Way Meta-Ensemble Report",
    f"*Generated: {result['as_of']}  |  Runtime: {runtime}s*",
    "",
    "## Executive Summary",
    "",
]

if accepted:
    report_lines += [
        f"**VERDICT: ACCEPT as K227 v6.8** — Best variant: {best_name}",
        "",
        f"| Metric | K218e v6.7 (prod) | {best_name} | Delta |",
        "|--------|------------------|-----------|-------|",
        f"| OOS Sharpe | {K218_OOS_SH:.4f} | {best_vm['oos_sharpe']:.4f} | {best_vm['oos_sharpe']-K218_OOS_SH:+.4f} |",
        f"| OOS MaxDD  | {K218_MAXDD:.6f} | {best_vm['oos_maxdd']:.6f} | {best_vm['oos_maxdd']-K218_MAXDD:+.6f} |",
        f"| WF Mean    | {K218_WF_MEAN:.4f} | {best_vm['wf_mean']:.4f} | {best_vm['wf_mean']-K218_WF_MEAN:+.4f} |",
        f"| WF Min     | {K218_WF_MIN:.4f} | {best_vm['wf_min']:.4f} | {best_vm['wf_min']-K218_WF_MIN:+.4f} |",
        f"| DR         | — | {best_vm['diversification_ratio']:.4f} | — |",
        "",
    ]
else:
    # Show the best variant even if not accepted
    best_any = max(variants.items(), key=lambda x: x[1]["oos_sharpe"])
    report_lines += [
        "**VERDICT: REJECT** — No variant passes all acceptance gates vs K218e v6.7.",
        "",
        f"Best attempted: {best_any[0]} with OOS Sh={best_any[1]['oos_sharpe']:.4f}",
        "",
    ]

report_lines += [
    "---",
    "",
    "## 1. Data & Methodology",
    "",
    f"- **Date range**: {dates_ml[0]} -> {dates_ml[-1]} ({n} days)",
    f"- **Return series**: {n_ret} daily observations",
    f"- **K208 daily aggregation**: 8h->daily by last candle of each UTC day; {missing_k208} days filled forward",
    f"- **K225 alignment**: primary_btc_z1 (z=1.25, hold=14d) mapped to ML window; {missing_k225} days filled forward; re-based to 1.0 at window start",
    "- **K198**: Ridge ML allocator (equity_ridge from wave_k198_curves.json)",
    "- **K204**: ML DD-embed full ensemble (equity_k204 from wave_k204_curves.json)",
    "- **K208**: DAR(2,1)-filtered reverse carry panel (K208_filtered, daily-resampled)",
    "- **K225**: Spot BTC ETF 7-Day Flow Regime (primary_btc_z1, z=1.25, hold=14d)",
    "- **OOS window**: final 30% of return series",
    "- **Walk-forward**: 4-fold chronological splits",
    "",
    "---",
    "",
    "## 2. 4x4 Correlation Matrix",
    "",
    "| | K198 | K204 | K208 | K225 |",
    "|---|------|------|------|------|",
    f"| **K198** | 1.0000 | {rho['rho_198_204']:.4f} | {rho['rho_198_208']:.4f} | {rho['rho_198_225']:.4f} |",
    f"| **K204** | {rho['rho_198_204']:.4f} | 1.0000 | {rho['rho_204_208']:.4f} | {rho['rho_204_225']:.4f} |",
    f"| **K208** | {rho['rho_198_208']:.4f} | {rho['rho_204_208']:.4f} | 1.0000 | {rho['rho_208_225']:.4f} |",
    f"| **K225** | {rho['rho_198_225']:.4f} | {rho['rho_204_225']:.4f} | {rho['rho_208_225']:.4f} | 1.0000 |",
    "",
    "**Interpretation:**",
    f"- K198 x K204: rho={rho['rho_198_204']:.4f} ({result['correlation_matrix']['interpretation']['rho_198_204']}) — established in K217",
    f"- K198 x K208: rho={rho['rho_198_208']:.4f} ({result['correlation_matrix']['interpretation']['rho_198_208']}) — DAR-filtered carry vs ML allocator",
    f"- K198 x K225: rho={rho['rho_198_225']:.4f} ({result['correlation_matrix']['interpretation']['rho_198_225']}) — ETF flow regime vs ML allocator",
    f"- K204 x K208: rho={rho['rho_204_208']:.4f} ({result['correlation_matrix']['interpretation']['rho_204_208']}) — ML ensemble vs reverse carry",
    f"- K204 x K225: rho={rho['rho_204_225']:.4f} ({result['correlation_matrix']['interpretation']['rho_204_225']}) — ML ensemble vs ETF flow",
    f"- K208 x K225: rho={rho['rho_208_225']:.4f} ({result['correlation_matrix']['interpretation']['rho_208_225']}) — DAR carry vs ETF flow regime",
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
    "| Variant | OOS Sharpe | OOS MaxDD | WF Mean | WF Min | DR | Avg Wts (K198/K204/K208/K225) |",
    "|---------|-----------|-----------|---------|--------|----|-------------------------------|",
]
for vname, vm in variants.items():
    wts = vm["avg_weights"]
    gate_sh  = "v" if vm["oos_sharpe"] > GATE_OOS_SH else "x"
    gate_wf  = "v" if vm["wf_min"] >= GATE_WF_MIN else "x"
    gate_dd  = "v" if vm["oos_maxdd"] >= GATE_MAXDD else "x"
    report_lines.append(
        f"| {vname} ({gate_sh}{gate_wf}{gate_dd}) | {vm['oos_sharpe']:.4f} | {vm['oos_maxdd']:.6f} | "
        f"{vm['wf_mean']:.4f} | {vm['wf_min']:.4f} | {vm['diversification_ratio']:.4f} | "
        f"{wts[0]:.3f}/{wts[1]:.3f}/{wts[2]:.3f}/{wts[3]:.3f} |"
    )

report_lines += [
    "",
    "Gates: v=pass x=fail. Gate indicators: [OOS Sh][WF min][MaxDD]",
    "",
    "### 4.2 Per-Variant Per-Fold Breakdown",
    "",
    "| Variant | Fold 1 | Fold 2 | Fold 3 | Fold 4 | WF Min | WF Mean |",
    "|---------|--------|--------|--------|--------|--------|---------|",
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
    "## 5. Five-Way Comparison Table",
    "",
    "| Version | OOS Sh | OOS MaxDD | WF Mean | WF Min | Components |",
    "|---------|--------|-----------|---------|--------|-----------|",
    f"| K198 v6.5 | 10.2800 | -0.005300 | 7.9100 | 6.5700 | 1 |",
    f"| K217 v6.6 | 10.4300 | -0.005300 | 8.0100 | 6.9100 | 2 |",
    f"| K218e v6.7 | {K218_OOS_SH:.4f} | {K218_MAXDD:.6f} | {K218_WF_MEAN:.4f} | {K218_WF_MIN:.4f} | 3 |",
]
for vname, vm in variants.items():
    wts = vm["avg_weights"]
    report_lines.append(
        f"| K227 {vname[-1]} ({vm['description'][:25]}...) | {vm['oos_sharpe']:.4f} | "
        f"{vm['oos_maxdd']:.6f} | {vm['wf_mean']:.4f} | {vm['wf_min']:.4f} | 4 |"
    )

report_lines += [
    "",
    f"**Acceptance gate**: OOS Sh > {GATE_OOS_SH:.4f} | WF Min >= {GATE_WF_MIN:.4f} | MaxDD <= {GATE_MAXDD:.6f} | All weights > 1%",
    "",
    "---",
    "",
    "## 6. Synergy Analysis",
    "",
    f"- Individual OOS Sharpes: K198={sh198_oos:.4f}, K204={sh204_oos:.4f}, K208={sh208_oos:.4f}, K225={sh225_oos:.4f}",
    f"- Average of 4 individuals OOS Sh: {avg_individual:.4f}",
]
if best_vm:
    report_lines += [
        f"- Best ensemble ({best_name}) OOS Sh: {best_vm['oos_sharpe']:.4f}",
        f"- Synergy vs avg individuals: {synergy_sh:+.4f} ({'GENUINE' if synergy_detected else 'WEAK/NONE'})",
        f"- Improvement vs K218 v6.7:   {synergy_vs_k218:+.4f}",
        f"- Diversification Ratio: {best_vm['diversification_ratio']:.4f} (>1.10 = genuine benefit)",
    ]

report_lines += [
    "",
    "---",
    "",
    "## 7. Risk Analysis",
    "",
    "### K225 Specific Risks",
    "- **Fold 3 weakness**: K225 standalone WF fold 3 Sh=-1.58 (May-Nov 2025) — ETF flow signal was adversarial",
    "- **Regime sensitivity**: ETF flow regime is a binary trigger (z>1.25) — regime changes can create abrupt switches",
    "- **Low vol characteristic**: K225 may have low daily vol on flat-flow periods, attracting disproportionate inv-vol weight",
    "- **Cap rationale**: K225 cap at 25% prevents overallocation during K225 low-vol regimes (mirrors K208 cap logic in K218)",
    "",
    "### Diversification Quality",
    f"- K225 vs K198: rho={rho['rho_198_225']:.4f} — orthogonal signal (ETF flow vs ML technical)",
    f"- K225 vs K204: rho={rho['rho_204_225']:.4f} — orthogonal (ML ensemble vs flow regime)",
    f"- K225 vs K208: rho={rho['rho_208_225']:.4f} — relationship between carry and ETF flow",
    "- DR > 1.10 confirms genuine diversification; DR measured at mean portfolio weights",
    "",
    "### Known Risks",
    "1. K225 fold 3 weakness may depress WF stability in 4-way ensemble during May-Nov 2025 fold",
    f"2. 4 carry-adjacent strategies may share hidden common factor (crypto funding/liquidity regime)",
    "3. Rolling window alignment: K225 starts 2024-05-23, K198 ML window starts 2025-01-22 — 8 months pre-window data not used",
    "4. K208 8h->daily resampling and K225 daily equity may have different time-of-day settlement",
    "",
    "---",
    "",
    "## 8. Verdict, K227 v6.8 if Accepted, K228 Next Steps",
    "",
]

if accepted:
    report_lines += [
        f"### ACCEPT -> K227 v6.8 (Best variant: {best_name})",
        "",
        f"The 4-way meta-ensemble ({best_name}: {best_vm['description']}) passes all acceptance gates:",
        f"- OOS Sharpe {best_vm['oos_sharpe']:.4f} > gate {GATE_OOS_SH:.4f} ({'PASS' if best_vm['oos_sharpe'] > GATE_OOS_SH else 'FAIL'})",
        f"- WF Min {best_vm['wf_min']:.4f} >= gate {GATE_WF_MIN:.4f} ({'PASS' if best_vm['wf_min'] >= GATE_WF_MIN else 'FAIL'})",
        f"- MaxDD {best_vm['oos_maxdd']:.6f} <= gate {GATE_MAXDD:.6f} ({'PASS' if best_vm['oos_maxdd'] >= GATE_MAXDD else 'FAIL'})",
        f"- All 4 portfolios non-zero weight (min={min(best_vm['avg_weights']):.3f}) ({'PASS' if min(best_vm['avg_weights']) > 0.01 else 'FAIL'})",
        "",
        "**Deployment Plan:**",
        f"1. Promote K227 ({best_name}) to v6.8 production",
        "2. Components: K198 Ridge ML + K204 ML DD-embed + K208 DAR reverse carry + K225 ETF flow regime",
        f"3. Allocator: {best_vm['description']}",
        "4. Monitor K225 fold 3-type regime weekly; if ETF flow signal inverts for >30d, cap K225 at 10%",
        "5. Rebalance monthly if weights drift >15% from avg",
        "",
        "**K228 Next Steps:**",
        "1. On-chain native signal: OP/ARB bridge flow or Jito MEV capture rate (not in current feature set)",
        "2. 5th orthogonal candidate: explore hash ribbon or miner capitulation signal (K220 result: not yet integrated)",
        "3. Regime-conditional rebalancing: allow K225 weight to increase to 40% during high ETF flow regime",
        "4. Tail risk: CVaR-optimised allocation variant (5th variant K227f) to reduce fold-3 drawdown sensitivity",
        "5. Production monitoring dashboard: per-strategy daily PnL + weight trajectory tracking",
    ]
else:
    report_lines += [
        "### REJECT — Maintain K218 v6.7 as Production",
        "",
        "No K227 variant improves on K218e v6.7 across all gates simultaneously.",
        "",
        "**Analysis:**",
    ]
    for vname, vm in variants.items():
        sh_pass = vm["oos_sharpe"] > GATE_OOS_SH
        wf_pass = vm["wf_min"] >= GATE_WF_MIN
        dd_pass = vm["oos_maxdd"] >= GATE_MAXDD
        wt_pass = min(vm["avg_weights"]) > 0.01
        failures = []
        if not sh_pass: failures.append(f"OOS Sh {vm['oos_sharpe']:.4f} < {GATE_OOS_SH:.4f}")
        if not wf_pass: failures.append(f"WF Min {vm['wf_min']:.4f} < {GATE_WF_MIN:.4f}")
        if not dd_pass: failures.append(f"MaxDD {vm['oos_maxdd']:.6f} > {GATE_MAXDD:.6f}")
        if not wt_pass: failures.append(f"Min weight {min(vm['avg_weights']):.3f} < 0.01")
        report_lines.append(f"- **{vname}**: {'PASS' if not failures else 'FAIL — ' + '; '.join(failures)}")

    report_lines += [
        "",
        "**Root cause analysis:**",
        f"- K225 fold 3 weakness (Sh=-1.58 in May-Nov 2025) drags 4-way WF stability",
        f"- Adding K225 dilutes the well-performing K198+K204+K208 core without sufficient WF improvement",
        f"- Uncapped inv-vol likely over-weights K225 in low-volatility periods, concentrating fold-3 damage",
        "",
        "**K228 Next Steps:**",
        "1. K225 regime-gate: only include K225 when ETF flow is in positive-regime; otherwise zero-weight",
        "2. Conditional 4-way: K225 active only when BTC-ETF 7d z-score > 1.0 (regime filter, not full signal)",
        "3. Explore purely orthogonal 4th signal: hash ribbon, miner capitulation, or on-chain stablecoin flow",
        "4. Increase K225 OOS Sh requirement: target standalone Sh > 3.0 on ML window before ensemble integration",
        "5. Extend K225 walk-forward training: use full 514-day history rather than 448-day ML window alignment",
    ]

report_lines += [
    "",
    "---",
    f"*Wave K227 | crypto-lab | {result['as_of']}*",
]

report_text = "\n".join(report_lines)

with open("/Users/nekonaomichi/crypto-lab/wave_k227_4way_meta.md", "w") as f:
    f.write(report_text)
print("Saved: wave_k227_4way_meta.md")

print(f"\n{'='*60}")
print(f"K227 COMPLETE — Runtime {runtime}s")
print(f"VERDICT: {verdict}")
print(f"{'='*60}")

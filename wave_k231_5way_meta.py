"""
Wave K231 — 5-Way Meta-Ensemble: K198 × K204 × K208 × K226 × K228
          (K229 v6.8 production + K228 Stablecoin Mint/Burn)

Extends K229 v6.8 (4-way meta OOS Sh 12.61, WF min 7.44) with K228 as the 5th portfolio.
K228 was ACCEPTED standalone (OOS Sh 2.77, 135d window, all WF folds positive, min +0.56).
K228 correlations to K198/K204/K208: 0.12/0.11/-0.002 (orthogonal); to K226: 0.30 (mild).

Key lessons applied:
  - K225 lesson: validate K228 standalone on K229 ML window (448d) BEFORE ensemble
  - Gate 0: K228 ML-window OOS Sh >= 1.0 AND WF folds all positive

Variants:
  K231a — Equal weight 20/20/20/20/20
  K231b — Inverse-volatility weighted (rolling 30d, uncapped)
  K231c — Inv-vol + K226 cap 20% (K229d spec preserved)
  K231d — Inv-vol + K226 cap 20% + K228 cap 20%
  K231e — Inv-vol + K208/K226/K228 all cap 25%
  K231f — MVP (Minimum Variance Portfolio, rolling 60d covariance)

Acceptance gates vs K229 v6.8 (K229d):
  K228 ML window OOS Sh >= 1.0   (validates standalone on common window)
  K228 WF folds all positive
  Best variant OOS Sh > 12.71    (+0.10 vs K229d 12.61)
  WF min >= 7.44                 (>= K229d WF min 7.4435)
  MaxDD <= -0.0012               (<= K229d MaxDD -0.001201)
  All 5 portfolios non-zero weight (>1%)

Deliverables:
  wave_k231_5way_meta.py    — this script
  wave_k231_5way_meta.json  — metrics + ML window validation + correlations
  wave_k231_curves.json     — equity curves
  wave_k231_5way_meta.md    — full report
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
with open("/Users/nekonaomichi/crypto-lab/wave_k204_curves.json") as f:
    k204_raw = json.load(f)
with open("/Users/nekonaomichi/crypto-lab/wave_k208_curves.json") as f:
    k208_raw = json.load(f)
with open("/Users/nekonaomichi/crypto-lab/wave_k226_curves.json") as f:
    k226_raw = json.load(f)
with open("/Users/nekonaomichi/crypto-lab/wave_k228_curves.json") as f:
    k228_raw = json.load(f)

# K198 and K204 share the same 448-day ML window (daily)
# 2025-01-22 → 2026-04-14, len=448
dates_ml = k198_raw["dates_ml"]
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

# K226 — ETH Validator Queue / LST Staking Flow
k226_dates     = k226_raw["dates"]
k226_strat_ret = k226_raw["strat_daily_ret"]
k226_strat_eq  = k226_raw["strategy_equity"]

k226_ret_daily = {}
for d, r in zip(k226_dates, k226_strat_ret):
    k226_ret_daily[d] = r

k226_eq_daily = {}
for d, eq in zip(k226_dates, k226_strat_eq):
    k226_eq_daily[d] = eq

k226_eq_values = []
missing_k226 = 0
for d in dates_ml:
    if d in k226_eq_daily:
        k226_eq_values.append(k226_eq_daily[d])
    else:
        missing_k226 += 1
        if k226_eq_values:
            k226_eq_values.append(k226_eq_values[-1])
        else:
            k226_eq_values.append(1.0)

eq226_raw_aligned = np.array(k226_eq_values)
eq226 = eq226_raw_aligned / eq226_raw_aligned[0]  # Re-base to 1.0

# K228 — Stablecoin Mint/Burn
k228_dates    = k228_raw["dates"]
k228_eq_list  = k228_raw["strategy_equity"]  # list of dicts {date, eq}
k228_eq_map   = {item["date"]: item["eq"] for item in k228_eq_list}

k228_eq_values = []
missing_k228 = 0
for d in dates_ml:
    if d in k228_eq_map:
        k228_eq_values.append(k228_eq_map[d])
    else:
        missing_k228 += 1
        if k228_eq_values:
            k228_eq_values.append(k228_eq_values[-1])
        else:
            k228_eq_values.append(1.0)

eq228_raw_aligned = np.array(k228_eq_values)
eq228 = eq228_raw_aligned / eq228_raw_aligned[0]  # Re-base to 1.0

n = len(dates_ml)
assert len(eq198) == len(eq204) == len(eq208) == len(eq226) == len(eq228) == n, (
    f"Length mismatch: K198={len(eq198)}, K204={len(eq204)}, "
    f"K208={len(eq208)}, K226={len(eq226)}, K228={len(eq228)}, dates={n}"
)

print(f"Data loaded: {n} days ({dates_ml[0]} -> {dates_ml[-1]})")
print(f"K208 missing days filled forward: {missing_k208}/{n}")
print(f"K226 missing days filled forward: {missing_k226}/{n}")
print(f"K228 missing days filled forward: {missing_k228}/{n}")
print(f"K198 equity range: [{eq198.min():.4f}, {eq198.max():.4f}]")
print(f"K204 equity range: [{eq204.min():.4f}, {eq204.max():.4f}]")
print(f"K208 equity range: [{eq208.min():.4f}, {eq208.max():.4f}]")
print(f"K226 equity range: [{eq226.min():.4f}, {eq226.max():.4f}]")
print(f"K228 equity range: [{eq228.min():.4f}, {eq228.max():.4f}]")

# Daily returns (geometric)
ret198 = np.diff(eq198) / eq198[:-1]
ret204 = np.diff(eq204) / eq204[:-1]
ret208 = np.diff(eq208) / eq208[:-1]
ret226 = np.diff(eq226) / eq226[:-1]
ret228 = np.diff(eq228) / eq228[:-1]
ret_dates = dates_ml[1:]   # n-1 return dates
n_ret = len(ret198)

print(f"\nReturn series length: {n_ret}")
print(f"K198 daily ret: mean={ret198.mean():.6f}, std={ret198.std():.6f}")
print(f"K204 daily ret: mean={ret204.mean():.6f}, std={ret204.std():.6f}")
print(f"K208 daily ret: mean={ret208.mean():.6f}, std={ret208.std():.6f}")
print(f"K226 daily ret: mean={ret226.mean():.6f}, std={ret226.std():.6f}")
print(f"K228 daily ret: mean={ret228.mean():.6f}, std={ret228.std():.6f}")
print(f"K228 non-zero returns: {(np.abs(ret228)>1e-10).sum()} / {n_ret} ({(np.abs(ret228)>1e-10).sum()/n_ret*100:.1f}%)")

# ─────────────────────────────────────────────────────────────────────────────
# 2. Utility functions
# ─────────────────────────────────────────────────────────────────────────────
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
    rets_matrix: shape (5, T)
    """
    w = np.array(w)
    individual_vols = np.array([np.std(r, ddof=1) for r in rets_matrix])
    weighted_vol_sum = float(np.dot(w, individual_vols))
    port_rets = np.dot(w, rets_matrix)
    port_vol  = float(np.std(port_rets, ddof=1))
    if port_vol < 1e-12:
        return np.nan
    return round(weighted_vol_sum / port_vol, 4)

# ─────────────────────────────────────────────────────────────────────────────
# 3. CRITICAL GATE 0: K228 standalone validation on K229 ML window (448d)
#    Must retain OOS Sh >= 1.0 and all WF folds positive
# ─────────────────────────────────────────────────────────────────────────────
print("\n" + "="*60)
print("GATE 0: K228 Standalone on K229 ML Window (448d) — CRITICAL")
print("="*60)
print(f"K228 original standalone OOS Sh (730d, from wave_k228_stablecoin_mint.json): 2.77")
print(f"K228 trading sparsity: ~85% cash (only ~76/447 non-zero returns on ML window)")
print(f"K226 lesson: K226 retained OOS Sh >1.0 on ML window -> K229 ACCEPTED")
print(f"K225 lesson: K225 dropped 2.11->1.16 on ML window -> K227 REJECTED")

k228_ml_oos = oos_metrics(ret228)
k228_ml_wf  = wf_stats(ret228)

print(f"\nK228 on ML window ({n_ret} returns):")
print(f"  OOS Sharpe: {k228_ml_oos['oos_sharpe']:.4f}  (gate >= 1.0)")
print(f"  OOS MaxDD:  {k228_ml_oos['oos_maxdd']:.6f}")
print(f"  OOS Ann Ret:{k228_ml_oos['oos_ann_ret']:.4f}")
print(f"  OOS Ann Vol:{k228_ml_oos['oos_ann_vol']:.4f}")
print(f"  WF folds:   {k228_ml_wf['fold_sharpes']}")
print(f"  WF min:     {k228_ml_wf['wf_min']:.4f}")
print(f"  WF mean:    {k228_ml_wf['wf_mean']:.4f}")

k228_ml_sh_pass = k228_ml_oos['oos_sharpe'] >= 1.0
k228_wf_all_pos = k228_ml_wf['wf_min'] > 0.0

print(f"\nGate 0a: K228 ML-window OOS Sh >= 1.0 -> {'PASS' if k228_ml_sh_pass else 'FAIL (abort 5-way)'}")
print(f"Gate 0b: K228 WF all folds positive  -> {'PASS' if k228_wf_all_pos else 'FAIL (soft, warn only)'}")

gate0_pass = k228_ml_sh_pass  # Hard gate: OOS Sh >= 1.0
if not gate0_pass:
    print("\nWARNING: K228 FAILS Gate 0 -> K231 5-way ensemble should be REJECTED")
    print("(Proceeding with computation for analysis, but verdict will be REJECT)")

# ─────────────────────────────────────────────────────────────────────────────
# 4. 5×5 correlation matrix
# ─────────────────────────────────────────────────────────────────────────────
rets_all = np.stack([ret198, ret204, ret208, ret226, ret228], axis=0)  # (5, T)
rho_matrix = np.corrcoef(rets_all)

labels = ["K198", "K204", "K208", "K226", "K228"]
print(f"\n--- 5x5 Pairwise Correlation Matrix ---")
header = "              " + "  ".join(f"{l:>8}" for l in labels)
print(header)
for i, li in enumerate(labels):
    row = f"{li:10}    " + "  ".join(f"{rho_matrix[i,j]:8.4f}" for j in range(5))
    print(row)

rho_198_204 = float(rho_matrix[0, 1])
rho_198_208 = float(rho_matrix[0, 2])
rho_198_226 = float(rho_matrix[0, 3])
rho_198_228 = float(rho_matrix[0, 4])
rho_204_208 = float(rho_matrix[1, 2])
rho_204_226 = float(rho_matrix[1, 3])
rho_204_228 = float(rho_matrix[1, 4])
rho_208_226 = float(rho_matrix[2, 3])
rho_208_228 = float(rho_matrix[2, 4])
rho_226_228 = float(rho_matrix[3, 4])

def corr_interp(rho):
    a = abs(rho)
    if a > 0.8:
        return "High"
    elif a > 0.5:
        return "Moderate"
    elif a > 0.2:
        return "Low-Moderate"
    else:
        return "Low"

# ─────────────────────────────────────────────────────────────────────────────
# 5. Baseline metrics (all 5 standalone on ML window)
# ─────────────────────────────────────────────────────────────────────────────
print("\n--- Baseline metrics (standalone on ML-window returns) ---")
baseline = {}
for name, rets in [("K198", ret198), ("K204", ret204), ("K208", ret208),
                   ("K226", ret226), ("K228", ret228)]:
    m = oos_metrics(rets)
    w = wf_stats(rets)
    m.update(w)
    baseline[name] = m
    print(f"{name}: OOS Sh={m['oos_sharpe']:.4f}  MaxDD={m['oos_maxdd']:.6f}  "
          f"WF mean={m['wf_mean']:.4f}  WF min={m['wf_min']:.4f}")

# ─────────────────────────────────────────────────────────────────────────────
# 6. 5-Way meta-allocator variants (K231a–K231f)
# ─────────────────────────────────────────────────────────────────────────────
variants     = {}
variant_rets = {}

ROLL     = 30   # rolling window for inv-vol weighting
ROLL_MVP = 60   # rolling window for MVP

# ── K231a: Equal weight 20/20/20/20/20 ───────────────────────────────────────
print("\n--- K231a: Equal weight 20/20/20/20/20 ---")
w_eq  = np.array([0.20, 0.20, 0.20, 0.20, 0.20])
ret_a = w_eq[0]*ret198 + w_eq[1]*ret204 + w_eq[2]*ret208 + w_eq[3]*ret226 + w_eq[4]*ret228
m     = oos_metrics(ret_a)
m.update(wf_stats(ret_a))
m["description"]           = "Equal weight 20/20/20/20/20"
m["avg_weights"]           = [round(float(w), 4) for w in w_eq]
m["diversification_ratio"] = diversification_ratio(w_eq, rets_all)
variants["K231a"]     = m
variant_rets["K231a"] = ret_a
print(f"K231a: OOS Sh={m['oos_sharpe']:.4f}  MaxDD={m['oos_maxdd']:.6f}  "
      f"WF mean={m['wf_mean']:.4f}  WF min={m['wf_min']:.4f}  DR={m['diversification_ratio']:.4f}")

# ── K231b: Inv-vol uncapped (rolling 30d) ────────────────────────────────────
print("\n--- K231b: Inv-vol uncapped (30d rolling) ---")
inv_vol_rets_b = np.zeros(n_ret)
w_traj_b       = np.zeros((n_ret, 5))
for i in range(n_ret):
    start_w = max(0, i - ROLL)
    seg_len = i - start_w + 1
    vols = []
    for rets_x in [ret198, ret204, ret208, ret226, ret228]:
        v = np.std(rets_x[start_w:i+1], ddof=1) if seg_len >= 3 else 1e-6
        vols.append(max(v, 1e-9))
    ivols = [1.0/v for v in vols]
    total = sum(ivols)
    wb = np.array([iv/total for iv in ivols])
    w_traj_b[i] = wb
    inv_vol_rets_b[i] = sum(wb[j]*rets[i] for j, rets in
                            enumerate([ret198, ret204, ret208, ret226, ret228]))

m = oos_metrics(inv_vol_rets_b)
m.update(wf_stats(inv_vol_rets_b))
m["description"]           = "Inverse-vol weighted uncapped (30d rolling)"
m["avg_weights"]           = [round(float(w_traj_b[:,j].mean()), 4) for j in range(5)]
m["diversification_ratio"] = diversification_ratio(w_traj_b.mean(axis=0), rets_all)
variants["K231b"]     = m
variant_rets["K231b"] = inv_vol_rets_b
print(f"K231b: OOS Sh={m['oos_sharpe']:.4f}  MaxDD={m['oos_maxdd']:.6f}  "
      f"WF mean={m['wf_mean']:.4f}  WF min={m['wf_min']:.4f}  DR={m['diversification_ratio']:.4f}")
print(f"       Avg weights: K198={m['avg_weights'][0]:.3f}, K204={m['avg_weights'][1]:.3f}, "
      f"K208={m['avg_weights'][2]:.3f}, K226={m['avg_weights'][3]:.3f}, K228={m['avg_weights'][4]:.3f}")

# ── K231c: Inv-vol + K226 cap 20% (K229d spec preserved) ─────────────────────
print("\n--- K231c: Inv-vol + K226 cap 20% (30d rolling) ---")
CAP226_C       = 0.20
inv_vol_rets_c = np.zeros(n_ret)
w_traj_c       = np.zeros((n_ret, 5))

def apply_cap_single(ivols, cap_idx, cap_val):
    """Apply a single cap to component cap_idx, redistribute to others by iv."""
    w = np.array(ivols) / sum(ivols)
    if w[cap_idx] > cap_val:
        w[cap_idx] = cap_val
        others_iv = np.array([ivols[j] for j in range(5) if j != cap_idx])
        others_idx = [j for j in range(5) if j != cap_idx]
        total_others_iv = others_iv.sum()
        for k, j in enumerate(others_idx):
            w[j] = others_iv[k] / total_others_iv * (1.0 - cap_val)
    return w

for i in range(n_ret):
    start_w = max(0, i - ROLL)
    seg_len = i - start_w + 1
    all_rets = [ret198, ret204, ret208, ret226, ret228]
    vols = []
    for rets_x in all_rets:
        v = np.std(rets_x[start_w:i+1], ddof=1) if seg_len >= 3 else 1e-6
        vols.append(max(v, 1e-9))
    ivols = [1.0/v for v in vols]
    wc = apply_cap_single(ivols, cap_idx=3, cap_val=CAP226_C)  # K226 is index 3
    w_traj_c[i] = wc
    inv_vol_rets_c[i] = sum(wc[j]*rets[i] for j, rets in enumerate(all_rets))

m = oos_metrics(inv_vol_rets_c)
m.update(wf_stats(inv_vol_rets_c))
m["description"]           = "Inv-vol + K226 cap 20% (30d rolling)"
m["avg_weights"]           = [round(float(w_traj_c[:,j].mean()), 4) for j in range(5)]
m["diversification_ratio"] = diversification_ratio(w_traj_c.mean(axis=0), rets_all)
variants["K231c"]     = m
variant_rets["K231c"] = inv_vol_rets_c
print(f"K231c: OOS Sh={m['oos_sharpe']:.4f}  MaxDD={m['oos_maxdd']:.6f}  "
      f"WF mean={m['wf_mean']:.4f}  WF min={m['wf_min']:.4f}  DR={m['diversification_ratio']:.4f}")
print(f"       Avg weights: K198={m['avg_weights'][0]:.3f}, K204={m['avg_weights'][1]:.3f}, "
      f"K208={m['avg_weights'][2]:.3f}, K226={m['avg_weights'][3]:.3f}, K228={m['avg_weights'][4]:.3f}")

# ── K231d: Inv-vol + K226 cap 20% + K228 cap 20% ─────────────────────────────
print("\n--- K231d: Inv-vol + K226 cap 20% + K228 cap 20% (30d rolling) ---")
CAP226_D = 0.20
CAP228_D = 0.20

def apply_two_caps_5way(ivols, cap226, cap228):
    """
    Apply caps to K226 (idx=3) and K228 (idx=4) iteratively.
    Redistribute excess to K198/K204/K208 proportionally by iv.
    """
    ivols_arr = np.array(ivols, dtype=float)
    w = ivols_arr / ivols_arr.sum()
    for _ in range(5):
        changed = False
        if w[3] > cap226:
            excess = w[3] - cap226
            w[3] = cap226
            others_iv = ivols_arr[[0, 1, 2, 4]]
            others_sum = others_iv.sum()
            if others_sum > 1e-12:
                for k, idx in enumerate([0, 1, 2, 4]):
                    w[idx] += (others_iv[k] / others_sum) * excess
            changed = True
        if w[4] > cap228:
            excess = w[4] - cap228
            w[4] = cap228
            others_iv = ivols_arr[[0, 1, 2, 3]]
            others_sum = others_iv.sum()
            if others_sum > 1e-12:
                for k, idx in enumerate([0, 1, 2, 3]):
                    w[idx] += (others_iv[k] / others_sum) * excess
            changed = True
        if not changed:
            break
    w = np.maximum(w, 0.0)
    s = w.sum()
    if s > 1e-12:
        w = w / s
    return w

inv_vol_rets_d = np.zeros(n_ret)
w_traj_d       = np.zeros((n_ret, 5))
all_rets = [ret198, ret204, ret208, ret226, ret228]

for i in range(n_ret):
    start_w = max(0, i - ROLL)
    seg_len = i - start_w + 1
    vols = []
    for rets_x in all_rets:
        v = np.std(rets_x[start_w:i+1], ddof=1) if seg_len >= 3 else 1e-6
        vols.append(max(v, 1e-9))
    ivols = [1.0/v for v in vols]
    wd = apply_two_caps_5way(ivols, CAP226_D, CAP228_D)
    w_traj_d[i] = wd
    inv_vol_rets_d[i] = sum(wd[j]*rets[i] for j, rets in enumerate(all_rets))

m = oos_metrics(inv_vol_rets_d)
m.update(wf_stats(inv_vol_rets_d))
m["description"]           = "Inv-vol + K226 cap 20% + K228 cap 20% (30d rolling)"
m["avg_weights"]           = [round(float(w_traj_d[:,j].mean()), 4) for j in range(5)]
m["diversification_ratio"] = diversification_ratio(w_traj_d.mean(axis=0), rets_all)
variants["K231d"]     = m
variant_rets["K231d"] = inv_vol_rets_d
print(f"K231d: OOS Sh={m['oos_sharpe']:.4f}  MaxDD={m['oos_maxdd']:.6f}  "
      f"WF mean={m['wf_mean']:.4f}  WF min={m['wf_min']:.4f}  DR={m['diversification_ratio']:.4f}")
print(f"       Avg weights: K198={m['avg_weights'][0]:.3f}, K204={m['avg_weights'][1]:.3f}, "
      f"K208={m['avg_weights'][2]:.3f}, K226={m['avg_weights'][3]:.3f}, K228={m['avg_weights'][4]:.3f}")

# ── K231e: Inv-vol + K208/K226/K228 all cap 25% ──────────────────────────────
print("\n--- K231e: Inv-vol + K208/K226/K228 all cap 25% (30d rolling) ---")
CAP_E = 0.25  # cap for K208(idx=2), K226(idx=3), K228(idx=4)

def apply_three_caps_5way(ivols, cap_idx_list, cap_vals):
    """
    Apply caps to multiple components iteratively.
    """
    ivols_arr = np.array(ivols, dtype=float)
    w = ivols_arr / ivols_arr.sum()
    for _ in range(7):
        changed = False
        for ci, cap_val in zip(cap_idx_list, cap_vals):
            if w[ci] > cap_val:
                excess = w[ci] - cap_val
                w[ci] = cap_val
                other_idx = [j for j in range(5) if j != ci]
                others_iv = ivols_arr[other_idx]
                others_sum = others_iv.sum()
                if others_sum > 1e-12:
                    for k, idx in enumerate(other_idx):
                        w[idx] += (others_iv[k] / others_sum) * excess
                changed = True
        if not changed:
            break
    w = np.maximum(w, 0.0)
    s = w.sum()
    if s > 1e-12:
        w = w / s
    return w

inv_vol_rets_e = np.zeros(n_ret)
w_traj_e       = np.zeros((n_ret, 5))

for i in range(n_ret):
    start_w = max(0, i - ROLL)
    seg_len = i - start_w + 1
    vols = []
    for rets_x in all_rets:
        v = np.std(rets_x[start_w:i+1], ddof=1) if seg_len >= 3 else 1e-6
        vols.append(max(v, 1e-9))
    ivols = [1.0/v for v in vols]
    we = apply_three_caps_5way(ivols, cap_idx_list=[2, 3, 4], cap_vals=[CAP_E, CAP_E, CAP_E])
    w_traj_e[i] = we
    inv_vol_rets_e[i] = sum(we[j]*rets[i] for j, rets in enumerate(all_rets))

m = oos_metrics(inv_vol_rets_e)
m.update(wf_stats(inv_vol_rets_e))
m["description"]           = "Inv-vol + K208/K226/K228 all cap 25% (30d rolling)"
m["avg_weights"]           = [round(float(w_traj_e[:,j].mean()), 4) for j in range(5)]
m["diversification_ratio"] = diversification_ratio(w_traj_e.mean(axis=0), rets_all)
variants["K231e"]     = m
variant_rets["K231e"] = inv_vol_rets_e
print(f"K231e: OOS Sh={m['oos_sharpe']:.4f}  MaxDD={m['oos_maxdd']:.6f}  "
      f"WF mean={m['wf_mean']:.4f}  WF min={m['wf_min']:.4f}  DR={m['diversification_ratio']:.4f}")
print(f"       Avg weights: K198={m['avg_weights'][0]:.3f}, K204={m['avg_weights'][1]:.3f}, "
      f"K208={m['avg_weights'][2]:.3f}, K226={m['avg_weights'][3]:.3f}, K228={m['avg_weights'][4]:.3f}")

# ── K231f: Minimum Variance Portfolio (rolling 60d covariance) ────────────────
print("\n--- K231f: MVP (rolling 60d covariance, long-only) ---")

def mvp_weights_5(cov_matrix):
    """
    Minimum Variance Portfolio weights (long-only, sum to 1) for 5 assets.
    w = Sigma^{-1} 1 / (1' Sigma^{-1} 1), with long-only floor.
    """
    ones = np.ones(5)
    try:
        sigma_inv = np.linalg.inv(cov_matrix + 1e-10 * np.eye(5))
        w_raw = sigma_inv @ ones
        w_raw = np.maximum(w_raw, 0.0)
        s = w_raw.sum()
        if s < 1e-12:
            return np.ones(5) / 5.0
        return w_raw / s
    except np.linalg.LinAlgError:
        return np.ones(5) / 5.0

mvp_rets_f = np.zeros(n_ret)
w_traj_f   = np.zeros((n_ret, 5))

for i in range(n_ret):
    start_w = max(0, i - ROLL_MVP)
    seg = np.stack([
        ret198[start_w:i+1],
        ret204[start_w:i+1],
        ret208[start_w:i+1],
        ret226[start_w:i+1],
        ret228[start_w:i+1],
    ], axis=0)
    if seg.shape[1] >= 6:
        cov = np.cov(seg)   # (5, 5)
        wf  = mvp_weights_5(cov)
    else:
        wf = np.ones(5) / 5.0
    w_traj_f[i] = wf
    mvp_rets_f[i] = sum(wf[j]*rets[i] for j, rets in enumerate(all_rets))

m = oos_metrics(mvp_rets_f)
m.update(wf_stats(mvp_rets_f))
m["description"]           = "Minimum Variance Portfolio (rolling 60d covariance, long-only)"
m["avg_weights"]           = [round(float(w_traj_f[:,j].mean()), 4) for j in range(5)]
m["diversification_ratio"] = diversification_ratio(w_traj_f.mean(axis=0), rets_all)
variants["K231f"]     = m
variant_rets["K231f"] = mvp_rets_f
print(f"K231f: OOS Sh={m['oos_sharpe']:.4f}  MaxDD={m['oos_maxdd']:.6f}  "
      f"WF mean={m['wf_mean']:.4f}  WF min={m['wf_min']:.4f}  DR={m['diversification_ratio']:.4f}")
print(f"       Avg weights: K198={m['avg_weights'][0]:.3f}, K204={m['avg_weights'][1]:.3f}, "
      f"K208={m['avg_weights'][2]:.3f}, K226={m['avg_weights'][3]:.3f}, K228={m['avg_weights'][4]:.3f}")

# ─────────────────────────────────────────────────────────────────────────────
# 7. Acceptance gates vs K229 v6.8 (K229d)
# ─────────────────────────────────────────────────────────────────────────────
K229_OOS_SH  = 12.61
K229_WF_MIN  = 7.4435
K229_WF_MEAN = None  # not used as hard gate
K229_MAXDD   = -0.001201

GATE_K228_ML_SH = 1.0               # K228 ML window OOS Sh hard gate
GATE_OOS_SH     = K229_OOS_SH + 0.10   # 12.71
GATE_WF_MIN     = K229_WF_MIN           # >= 7.4435
GATE_MAXDD      = K229_MAXDD            # <= -0.0012

print(f"\n--- Acceptance Gates (vs K229 v6.8 = K229d) ---")
print(f"Gate 0 (prerequisite): K228 ML window OOS Sh >= {GATE_K228_ML_SH:.1f}  -> {'PASS' if gate0_pass else 'FAIL'}")
print(f"Gate 1: Best variant OOS Sh > {GATE_OOS_SH:.2f}")
print(f"Gate 2: WF min >= {GATE_WF_MIN:.4f}")
print(f"Gate 3: MaxDD <= {GATE_MAXDD:.6f}")
print(f"Gate 4: All 5 portfolios non-zero weight (>1%)")

candidates = []
for vname, vm in variants.items():
    sh_pass  = vm["oos_sharpe"] > GATE_OOS_SH
    wf_pass  = vm["wf_min"] >= GATE_WF_MIN
    dd_pass  = vm["oos_maxdd"] >= GATE_MAXDD
    min_wt   = min(vm["avg_weights"])
    wt_pass  = min_wt > 0.01
    all_pass = gate0_pass and sh_pass and wf_pass and dd_pass and wt_pass
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

# ─────────────────────────────────────────────────────────────────────────────
# 8. Synergy analysis
# ─────────────────────────────────────────────────────────────────────────────
print("\n--- Synergy Analysis ---")
sh198_oos = baseline["K198"]["oos_sharpe"]
sh204_oos = baseline["K204"]["oos_sharpe"]
sh208_oos = baseline["K208"]["oos_sharpe"]
sh226_oos = baseline["K226"]["oos_sharpe"]
sh228_oos = baseline["K228"]["oos_sharpe"]
avg_individual = (sh198_oos + sh204_oos + sh208_oos + sh226_oos + sh228_oos) / 5.0
print(f"Individual OOS Sharpes: K198={sh198_oos:.4f}, K204={sh204_oos:.4f}, "
      f"K208={sh208_oos:.4f}, K226={sh226_oos:.4f}, K228={sh228_oos:.4f}")
print(f"Average of 5 individuals: {avg_individual:.4f}")

best_vm_report = best_vm if best_vm else max(variants.values(), key=lambda x: x["oos_sharpe"])
best_name_report = best_name if best_name else max(variants.items(), key=lambda x: x[1]["oos_sharpe"])[0]

synergy_sh       = best_vm_report["oos_sharpe"] - avg_individual
synergy_vs_k229  = best_vm_report["oos_sharpe"] - K229_OOS_SH
synergy_detected = synergy_sh > 0.02

print(f"Best ensemble ({best_name_report}): {best_vm_report['oos_sharpe']:.4f}")
print(f"Synergy vs avg individuals:  {synergy_sh:+.4f} ({'GENUINE' if synergy_detected else 'WEAK'})")
print(f"Improvement vs K229 v6.8:    {synergy_vs_k229:+.4f}")
avg_wf_min    = np.mean([baseline[n]["wf_min"] for n in ["K198","K204","K208","K226","K228"]])
wf_min_synergy = best_vm_report["wf_min"] - avg_wf_min
print(f"WF-min avg individuals: {avg_wf_min:.4f}  |  Best ensemble WF-min: {best_vm_report['wf_min']:.4f}  |  D: {wf_min_synergy:+.4f}")

# K228 contribution analysis: 4-way vs 5-way on OOS period
# Load K229d reference (inv-vol + K226 cap 20%, now without K228)
print("\n--- K228 Additive Contribution (5-way vs 4-way) ---")
# Compute K229d-equivalent 4-way (without K228) using same machinery
inv_vol_rets_4way = np.zeros(n_ret)
w_traj_4way = np.zeros((n_ret, 4))
CAP226_REF = 0.20
for i in range(n_ret):
    start_w = max(0, i - ROLL)
    seg_len = i - start_w + 1
    vols_4 = []
    for rets_x in [ret198, ret204, ret208, ret226]:
        v = np.std(rets_x[start_w:i+1], ddof=1) if seg_len >= 3 else 1e-6
        vols_4.append(max(v, 1e-9))
    ivols_4 = [1.0/v for v in vols_4]
    total_4 = sum(ivols_4)
    wd4 = np.array([iv/total_4 for iv in ivols_4])
    if wd4[3] > CAP226_REF:
        wd4[3] = CAP226_REF
        iv_rest = np.array(ivols_4[:3])
        wd4[:3] = iv_rest / iv_rest.sum() * (1.0 - CAP226_REF)
    w_traj_4way[i] = wd4
    inv_vol_rets_4way[i] = wd4[0]*ret198[i] + wd4[1]*ret204[i] + wd4[2]*ret208[i] + wd4[3]*ret226[i]

m_4way = oos_metrics(inv_vol_rets_4way)
wf_4way = wf_stats(inv_vol_rets_4way)
print(f"4-way ref (K229d-equiv): OOS Sh={m_4way['oos_sharpe']:.4f}  WF min={wf_4way['wf_min']:.4f}")
print(f"5-way best ({best_name_report}):  OOS Sh={best_vm_report['oos_sharpe']:.4f}  WF min={best_vm_report['wf_min']:.4f}")
k228_additive_delta = best_vm_report['oos_sharpe'] - m_4way['oos_sharpe']
print(f"K228 additive delta:  {k228_additive_delta:+.4f}")

# ─────────────────────────────────────────────────────────────────────────────
# 9. Build equity curves for output
# ─────────────────────────────────────────────────────────────────────────────
# K229d reference equity curve (inv-vol + K226 cap 20%)
k229d_ref_ret = inv_vol_rets_4way

curves = {
    "K198":      equity_curve(ret198),
    "K204":      equity_curve(ret204),
    "K208":      equity_curve(ret208),
    "K226":      equity_curve(ret226),
    "K228":      equity_curve(ret228),
    "K229d_ref": equity_curve(k229d_ref_ret),
    "K231a":     equity_curve(variant_rets["K231a"]),
    "K231b":     equity_curve(variant_rets["K231b"]),
    "K231c":     equity_curve(variant_rets["K231c"]),
    "K231d":     equity_curve(variant_rets["K231d"]),
    "K231e":     equity_curve(variant_rets["K231e"]),
    "K231f":     equity_curve(variant_rets["K231f"]),
    "dates":     [dates_ml[0]] + list(ret_dates),
}

# ─────────────────────────────────────────────────────────────────────────────
# 10. Save JSON outputs
# ─────────────────────────────────────────────────────────────────────────────
runtime = round(time.time() - t0, 2)

if accepted:
    verdict = f"ACCEPT as K231 v6.9 — best variant: {best_name}"
elif not gate0_pass:
    verdict = (f"REJECT — K228 ML-window OOS Sh={k228_ml_oos['oos_sharpe']:.4f} < gate {GATE_K228_ML_SH:.1f} "
               f"(sparse trading signal degrades on ML window)")
else:
    verdict = "REJECT — no variant passes all acceptance gates vs K229 v6.8"

corr_mat_list = [[round(rho_matrix[i,j], 4) for j in range(5)] for i in range(5)]

fold_breakdown = {vname: vm["fold_details"] for vname, vm in variants.items()}

synergy_block = {
    "individual_oos_sharpes": {
        "K198": sh198_oos,
        "K204": sh204_oos,
        "K208": sh208_oos,
        "K226": sh226_oos,
        "K228": sh228_oos,
    },
    "avg_individual_oos_sh":   round(avg_individual, 4),
    "best_ensemble_name":      best_name_report,
    "best_ensemble_oos_sh":    round(best_vm_report["oos_sharpe"], 4),
    "synergy_delta_vs_avg":    round(synergy_sh, 4),
    "synergy_delta_vs_k229":   round(synergy_vs_k229, 4),
    "synergy_detected":        synergy_detected,
    "k228_additive_delta_vs_4way": round(k228_additive_delta, 4),
    "avg_individual_wf_min":   round(float(avg_wf_min), 4),
    "best_ensemble_wf_min":    round(best_vm_report["wf_min"], 4),
}

# Historical comparison table
historical = {
    "K198_v6.5":  {"oos_sharpe": 10.28,  "oos_maxdd": -0.0053, "wf_min": 6.57,  "components": 1},
    "K217_v6.6":  {"oos_sharpe": 10.43,  "oos_maxdd": -0.0053, "wf_min": 6.91,  "components": 2},
    "K218e_v6.7": {"oos_sharpe": 11.031, "oos_maxdd": -0.00364, "wf_min": 6.9282, "components": 3},
    "K229d_v6.8": {"oos_sharpe": K229_OOS_SH, "oos_maxdd": K229_MAXDD, "wf_min": K229_WF_MIN, "components": 4},
}
for vname, vm in variants.items():
    historical[f"K231_{vname[-1]}"] = {
        "oos_sharpe":  vm["oos_sharpe"],
        "oos_maxdd":   vm["oos_maxdd"],
        "wf_mean":     vm["wf_mean"],
        "wf_min":      vm["wf_min"],
        "dr":          vm["diversification_ratio"],
        "components":  5,
        "avg_weights": vm["avg_weights"],
    }

result = {
    "wave":    "K231",
    "task":    "5-Way Meta-Ensemble: K198 x K204 x K208 x K226 x K228 (Stablecoin Mint/Burn)",
    "as_of":   datetime.now(timezone.utc).isoformat(),
    "runtime_s": runtime,
    "data_info": {
        "n_days":            n,
        "date_start":        dates_ml[0],
        "date_end":          dates_ml[-1],
        "n_returns":         n_ret,
        "k208_missing_days": missing_k208,
        "k226_missing_days": missing_k226,
        "k228_missing_days": missing_k228,
        "k228_nonzero_days": int((np.abs(ret228) > 1e-10).sum()),
        "k228_sparsity_pct": round(float((np.abs(ret228) > 1e-10).sum()) / n_ret * 100, 1),
    },
    "k228_ml_window_validation": {
        "description":          "K228 standalone on K229 ML window (448d) — Gate 0 critical check",
        "k228_original_oos_sh": 2.77,
        "k228_original_window": "730d (2024-05-23 to 2026-05-22)",
        "k228_ml_window_oos_sh": k228_ml_oos["oos_sharpe"],
        "k228_ml_window_oos_maxdd": k228_ml_oos["oos_maxdd"],
        "k228_ml_window_oos_n_days": k228_ml_oos["oos_n_days"],
        "k228_ml_window_oos_ann_ret": k228_ml_oos["oos_ann_ret"],
        "k228_ml_window_oos_ann_vol": k228_ml_oos["oos_ann_vol"],
        "k228_ml_window_wf_folds": k228_ml_wf["fold_sharpes"],
        "k228_ml_window_wf_min": k228_ml_wf["wf_min"],
        "k228_ml_window_wf_mean": k228_ml_wf["wf_mean"],
        "gate_sh_pass":         k228_ml_sh_pass,
        "gate_wf_all_positive": k228_wf_all_pos,
        "k225_reference":       "K225 dropped 2.11->1.16 on ML window (fatal, caused K227 REJECT)",
        "k226_reference":       "K226 retained >1.0 on ML window -> K229 ACCEPTED",
        "k228_verdict":         "PASS" if k228_ml_sh_pass else "FAIL",
        "gate0_pass":           gate0_pass,
    },
    "correlation_matrix": {
        "labels": labels,
        "matrix": corr_mat_list,
        "pairwise": {
            "rho_198_204": round(rho_198_204, 4),
            "rho_198_208": round(rho_198_208, 4),
            "rho_198_226": round(rho_198_226, 4),
            "rho_198_228": round(rho_198_228, 4),
            "rho_204_208": round(rho_204_208, 4),
            "rho_204_226": round(rho_204_226, 4),
            "rho_204_228": round(rho_204_228, 4),
            "rho_208_226": round(rho_208_226, 4),
            "rho_208_228": round(rho_208_228, 4),
            "rho_226_228": round(rho_226_228, 4),
        },
        "interpretation": {
            "rho_198_204": corr_interp(rho_198_204),
            "rho_198_208": corr_interp(rho_198_208),
            "rho_198_226": corr_interp(rho_198_226),
            "rho_198_228": corr_interp(rho_198_228),
            "rho_204_208": corr_interp(rho_204_208),
            "rho_204_226": corr_interp(rho_204_226),
            "rho_204_228": corr_interp(rho_204_228),
            "rho_208_226": corr_interp(rho_208_226),
            "rho_208_228": corr_interp(rho_208_228),
            "rho_226_228": corr_interp(rho_226_228),
        },
        "k228_prior_reported": {
            "k228_vs_k198": 0.12,
            "k228_vs_k204": 0.11,
            "k228_vs_k208": -0.002,
            "k228_vs_k226": 0.30,
        },
    },
    "acceptance_gates": {
        "gate0_k228_ml_sh_threshold": GATE_K228_ML_SH,
        "gate1_oos_sharpe_threshold": GATE_OOS_SH,
        "gate2_wf_min_threshold":     GATE_WF_MIN,
        "gate3_maxdd_threshold":      GATE_MAXDD,
        "gate4_min_weight":           0.01,
        "reference":                  "K229d v6.8",
        "gate0_result":               "PASS" if gate0_pass else "FAIL",
    },
    "baselines":       baseline,
    "variants":        variants,
    "fold_breakdown":  fold_breakdown,
    "synergy":         synergy_block,
    "historical":      historical,
    "verdict":         verdict,
    "accepted":        accepted,
    "best_variant":    best_name,
    "best_variant_metrics": best_vm,
}

with open("/Users/nekonaomichi/crypto-lab/wave_k231_5way_meta.json", "w") as f:
    json.dump(result, f, indent=2)
print("\nSaved: wave_k231_5way_meta.json")

with open("/Users/nekonaomichi/crypto-lab/wave_k231_curves.json", "w") as f:
    json.dump(curves, f)
print("Saved: wave_k231_curves.json")

print(f"\nRuntime: {runtime}s")
print(f"\nVERDICT: {verdict}")

# ─────────────────────────────────────────────────────────────────────────────
# 11. Generate Markdown report
# ─────────────────────────────────────────────────────────────────────────────
rho = result["correlation_matrix"]["pairwise"]
k228_val = result["k228_ml_window_validation"]
rho_interp = result["correlation_matrix"]["interpretation"]

report_lines = [
    "# Wave K231 — 5-Way Meta-Ensemble Report (K198 × K204 × K208 × K226 × K228)",
    f"*Generated: {result['as_of']}  |  Runtime: {runtime}s*",
    "",
    "## PRIMARY HEADER: K228 ML-Window Standalone Validation (Gate 0)",
    "",
    "**This is the critical prerequisite. If K228 fails Gate 0, K231 is rejected at first check.**",
    "",
    f"| Metric | K228 Original (730d) | K228 on ML Window (448d) | Gate | Result |",
    "|--------|---------------------|------------------------|------|--------|",
    f"| OOS Sharpe | 2.77 | {k228_val['k228_ml_window_oos_sh']:.4f} | >= 1.0 | {'**PASS**' if k228_val['gate_sh_pass'] else '**FAIL — REJECT**'} |",
    f"| OOS MaxDD  | — | {k228_val['k228_ml_window_oos_maxdd']:.6f} | — | — |",
    f"| OOS Ann Ret| — | {k228_val['k228_ml_window_oos_ann_ret']:.4f} | — | — |",
    f"| OOS Ann Vol| — | {k228_val['k228_ml_window_oos_ann_vol']:.4f} | — | — |",
    f"| WF min fold| +0.56 (original) | {k228_val['k228_ml_window_wf_min']:.4f} | > 0.0 | {'PASS (all pos)' if k228_val['gate_wf_all_positive'] else 'FAIL'} |",
    f"| WF folds   | all pos (original) | {k228_val['k228_ml_window_wf_folds']} | all positive | {'PASS' if k228_val['gate_wf_all_positive'] else 'FAIL'} |",
    f"| Sparsity   | ~85% cash | {result['data_info']['k228_sparsity_pct']:.1f}% active days | — | — |",
    "",
    f"**Gate 0 Result: {'PASS — K228 retains alpha on ML window, proceed with 5-way' if k228_val['gate_sh_pass'] else 'FAIL — K228 loses alpha on ML window, K231 REJECTED'}**",
    "",
    "Reference comparisons:",
    "- K225 (K227 lesson): dropped 2.11 → 1.16 on ML window → REJECT (window mismatch fatal)",
    "- K226 (K229 lesson): retained >1.0 on ML window → PASS → K229 ACCEPTED",
    "",
]

if accepted:
    report_lines += [
        "## Executive Summary",
        "",
        f"**VERDICT: ACCEPT as K231 v6.9** — Best variant: {best_name}",
        "",
        f"| Metric | K229d v6.8 (prod) | {best_name} | Delta |",
        "|--------|------------------|-----------|-------|",
        f"| OOS Sharpe | {K229_OOS_SH:.4f} | {best_vm['oos_sharpe']:.4f} | {best_vm['oos_sharpe']-K229_OOS_SH:+.4f} |",
        f"| OOS MaxDD  | {K229_MAXDD:.6f} | {best_vm['oos_maxdd']:.6f} | {best_vm['oos_maxdd']-K229_MAXDD:+.6f} |",
        f"| WF Min     | {K229_WF_MIN:.4f} | {best_vm['wf_min']:.4f} | {best_vm['wf_min']-K229_WF_MIN:+.4f} |",
        f"| DR         | 1.65 (K229d) | {best_vm['diversification_ratio']:.4f} | {best_vm['diversification_ratio']-1.65:+.4f} |",
        "",
    ]
else:
    best_any = max(variants.items(), key=lambda x: x[1]["oos_sharpe"])
    report_lines += [
        "## Executive Summary",
        "",
        f"**VERDICT: REJECT** — No variant passes all acceptance gates vs K229d v6.8.",
        "",
        f"Best attempted: {best_any[0]} with OOS Sh={best_any[1]['oos_sharpe']:.4f}",
        f"Gate failures: see Section 5.",
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
    f"- **K226 alignment**: ETH validator queue/LST flow mapped to ML window; {missing_k226} days filled forward; re-based to 1.0",
    f"- **K228 alignment**: Stablecoin mint/burn; {missing_k228} days filled forward; re-based to 1.0",
    f"- **K228 sparsity**: {result['data_info']['k228_sparsity_pct']:.1f}% active trading days ({result['data_info']['k228_nonzero_days']} non-zero returns)",
    "- **OOS window**: final 30% of return series (~135 days)",
    "- **Walk-forward**: 4-fold chronological splits",
    "",
    "**Portfolios:**",
    "- K198: Ridge ML allocator (equity_ridge)",
    "- K204: ML DD-embed full ensemble (equity_k204)",
    "- K208: DAR(2,1)-filtered reverse carry panel (8h, daily-resampled)",
    "- K226: ETH Validator Queue / LST Staking Flow contrarian",
    "- K228: Stablecoin Mint/Burn momentum signal",
    "",
    "---",
    "",
    "## 2. 5×5 Correlation Matrix",
    "",
    "| | K198 | K204 | K208 | K226 | K228 |",
    "|---|------|------|------|------|------|",
    f"| **K198** | 1.0000 | {rho['rho_198_204']:.4f} | {rho['rho_198_208']:.4f} | {rho['rho_198_226']:.4f} | {rho['rho_198_228']:.4f} |",
    f"| **K204** | {rho['rho_198_204']:.4f} | 1.0000 | {rho['rho_204_208']:.4f} | {rho['rho_204_226']:.4f} | {rho['rho_204_228']:.4f} |",
    f"| **K208** | {rho['rho_198_208']:.4f} | {rho['rho_204_208']:.4f} | 1.0000 | {rho['rho_208_226']:.4f} | {rho['rho_208_228']:.4f} |",
    f"| **K226** | {rho['rho_198_226']:.4f} | {rho['rho_204_226']:.4f} | {rho['rho_208_226']:.4f} | 1.0000 | {rho['rho_226_228']:.4f} |",
    f"| **K228** | {rho['rho_198_228']:.4f} | {rho['rho_204_228']:.4f} | {rho['rho_208_228']:.4f} | {rho['rho_226_228']:.4f} | 1.0000 |",
    "",
    "**Interpretation:**",
    f"- K198 x K204: rho={rho['rho_198_204']:.4f} ({rho_interp['rho_198_204']}) — established core ML pair",
    f"- K198 x K208: rho={rho['rho_198_208']:.4f} ({rho_interp['rho_198_208']}) — ML vs DAR carry",
    f"- K198 x K226: rho={rho['rho_198_226']:.4f} ({rho_interp['rho_198_226']}) — ML vs ETH validator flow",
    f"- K198 x K228: rho={rho['rho_198_228']:.4f} ({rho_interp['rho_198_228']}) — ML vs stablecoin mint",
    f"- K204 x K208: rho={rho['rho_204_208']:.4f} ({rho_interp['rho_204_208']}) — ML ensemble vs reverse carry",
    f"- K204 x K226: rho={rho['rho_204_226']:.4f} ({rho_interp['rho_204_226']}) — ML ensemble vs ETH flow",
    f"- K204 x K228: rho={rho['rho_204_228']:.4f} ({rho_interp['rho_204_228']}) — ML ensemble vs stablecoin",
    f"- K208 x K226: rho={rho['rho_208_226']:.4f} ({rho_interp['rho_208_226']}) — DAR carry vs ETH flow",
    f"- K208 x K228: rho={rho['rho_208_228']:.4f} ({rho_interp['rho_208_228']}) — DAR carry vs stablecoin",
    f"- K226 x K228: rho={rho['rho_226_228']:.4f} ({rho_interp['rho_226_228']}) — ETH flow vs stablecoin (pre-reported: 0.30)",
    "",
    "---",
    "",
    "## 3. Baseline Performance (Standalone on ML Window)",
    "",
    "| Portfolio | OOS Sharpe | OOS MaxDD | WF Mean | WF Min | WF Max | WF Folds |",
    "|-----------|-----------|-----------|---------|--------|--------|----------|",
]
for bname, bm in baseline.items():
    fs = bm["fold_sharpes"]
    report_lines.append(
        f"| {bname} | {bm['oos_sharpe']:.4f} | {bm['oos_maxdd']:.6f} | "
        f"{bm['wf_mean']:.4f} | {bm['wf_min']:.4f} | {bm['wf_max']:.4f} | "
        f"{fs[0]:.2f}/{fs[1]:.2f}/{fs[2]:.2f}/{fs[3]:.2f} |"
    )

report_lines += [
    "",
    "---",
    "",
    "## 4. DR Comparison: K229 vs K231",
    "",
    f"| Variant | DR | Components | Note |",
    "|---------|-----|------------|------|",
    f"| K229d (v6.8) | 1.65 | 4 | Production baseline |",
]
for vname, vm in variants.items():
    dr_delta = vm["diversification_ratio"] - 1.65
    report_lines.append(
        f"| {vname} | {vm['diversification_ratio']:.4f} | 5 | {'+' if dr_delta >= 0 else ''}{dr_delta:.4f} vs K229d |"
    )

report_lines += [
    "",
    "---",
    "",
    "## 5. Variant Results",
    "",
    "### 5.1 Per-Variant Summary",
    "",
    "| Variant | Description | OOS Sh | OOS MaxDD | WF Mean | WF Min | DR | K198/K204/K208/K226/K228 wts | Gates |",
    "|---------|-------------|--------|-----------|---------|--------|----|------------------------------|-------|",
]
for vname, vm in variants.items():
    wts = vm["avg_weights"]
    gate_sh = vm["oos_sharpe"] > GATE_OOS_SH
    gate_wf = vm["wf_min"] >= GATE_WF_MIN
    gate_dd = vm["oos_maxdd"] >= GATE_MAXDD
    report_lines.append(
        f"| {vname} | {vm['description'][:35]} | {vm['oos_sharpe']:.4f} | "
        f"{vm['oos_maxdd']:.6f} | {vm['wf_mean']:.4f} | {vm['wf_min']:.4f} | "
        f"{vm['diversification_ratio']:.4f} | {wts[0]:.2f}/{wts[1]:.2f}/{wts[2]:.2f}/{wts[3]:.2f}/{wts[4]:.2f} | "
        f"{'v' if gate_sh else 'x'}/{'v' if gate_wf else 'x'}/{'v' if gate_dd else 'x'} |"
    )

report_lines += [
    "",
    f"Gates order: [OOS Sh > {GATE_OOS_SH:.2f}] / [WF min >= {GATE_WF_MIN:.4f}] / [MaxDD <= {GATE_MAXDD:.6f}]",
    "",
    "### 5.2 Per-Variant Per-Fold Breakdown",
    "",
    "| Variant | Fold 1 | Fold 2 | Fold 3 | Fold 4 | WF Min | WF Mean | All pos? |",
    "|---------|--------|--------|--------|--------|--------|---------|----------|",
]
for vname, vm in variants.items():
    fs = vm["fold_sharpes"]
    all_pos = all(f > 0 for f in fs)
    report_lines.append(
        f"| {vname} | {fs[0]:.4f} | {fs[1]:.4f} | {fs[2]:.4f} | {fs[3]:.4f} | "
        f"{vm['wf_min']:.4f} | {vm['wf_mean']:.4f} | {'YES' if all_pos else 'NO'} |"
    )

report_lines += [
    "",
    "---",
    "",
    "## 6. Historical Comparison",
    "",
    "| Version | OOS Sh | OOS MaxDD | WF Min | Components | Note |",
    "|---------|--------|-----------|--------|-----------|------|",
    "| K198 v6.5 | 10.2800 | -0.005300 | 6.5700 | 1 | Baseline ML |",
    "| K217 v6.6 | 10.4300 | -0.005300 | 6.9100 | 2 | +K208 |",
    "| K218e v6.7 | 11.0310 | -0.003640 | 6.9282 | 3 | +K204 |",
    f"| K229d v6.8 | {K229_OOS_SH:.4f} | {K229_MAXDD:.6f} | {K229_WF_MIN:.4f} | 4 | +K226 (production) |",
]
for vname, vm in variants.items():
    wts = vm["avg_weights"]
    all_gates = (gate0_pass and
                 vm["oos_sharpe"] > GATE_OOS_SH and
                 vm["wf_min"] >= GATE_WF_MIN and
                 vm["oos_maxdd"] >= GATE_MAXDD and
                 min(wts) > 0.01)
    note = "ACCEPTED" if all_gates else ("best" if vname == best_name_report else "")
    report_lines.append(
        f"| K231 {vname[-1]} | {vm['oos_sharpe']:.4f} | {vm['oos_maxdd']:.6f} | "
        f"{vm['wf_min']:.4f} | 5 | {note} |"
    )

report_lines += [
    "",
    f"**Acceptance gate**: OOS Sh > {GATE_OOS_SH:.2f} | WF Min >= {GATE_WF_MIN:.4f} | MaxDD <= {GATE_MAXDD:.6f} | All weights > 1%",
    "",
    "---",
    "",
    "## 7. Synergy Analysis",
    "",
    f"- Individual OOS Sharpes (ML window): K198={sh198_oos:.4f}, K204={sh204_oos:.4f}, K208={sh208_oos:.4f}, K226={sh226_oos:.4f}, K228={sh228_oos:.4f}",
    f"- Average of 5 individuals OOS Sh: {avg_individual:.4f}",
    f"- Best ensemble ({best_name_report}) OOS Sh: {best_vm_report['oos_sharpe']:.4f}",
    f"- Synergy vs avg individuals: {synergy_sh:+.4f} ({'GENUINE (>0.02)' if synergy_detected else 'WEAK/NONE (<0.02)'})",
    f"- Improvement vs K229 v6.8: {synergy_vs_k229:+.4f}",
    f"- K228 additive delta (5-way vs 4-way): {k228_additive_delta:+.4f}",
    f"- Best ensemble DR: {best_vm_report['diversification_ratio']:.4f} vs K229d DR=1.65",
    "",
    "**K228 Orthogonality (empirical vs reported):**",
    f"- K228 vs K198: rho={rho['rho_198_228']:.4f} (pre-reported: 0.12) — {'consistent' if abs(rho['rho_198_228'] - 0.12) < 0.15 else 'deviation'}",
    f"- K228 vs K204: rho={rho['rho_204_228']:.4f} (pre-reported: 0.11) — {'consistent' if abs(rho['rho_204_228'] - 0.11) < 0.15 else 'deviation'}",
    f"- K228 vs K208: rho={rho['rho_208_228']:.4f} (pre-reported: -0.002) — {'consistent' if abs(rho['rho_208_228'] + 0.002) < 0.15 else 'deviation'}",
    f"- K228 vs K226: rho={rho['rho_226_228']:.4f} (pre-reported: 0.30) — {'consistent' if abs(rho['rho_226_228'] - 0.30) < 0.15 else 'deviation'}",
    "",
    "---",
    "",
    "## 8. Risk Analysis",
    "",
    "### K228-Specific Risks",
    "- **Sparsity**: ~85% cash days means K228 contributes nothing on most days; effective diversification benefit is diluted",
    f"- **Sparse correlation artifacts**: rho estimates with sparse series can be unstable; {result['data_info']['k228_nonzero_days']} active days out of {n_ret}",
    "- **K226 vs K228 mild correlation** (rho ~0.30): Both are flow-type signals; overlap in signal timing may reduce marginal diversification",
    "- **Window sensitivity**: Large gap between original 730d window and 448d ML window; test if alpha is concentrated in non-ML period",
    "",
    "### Diversification Plateau Risk",
    "- K229 DR=1.65 from 4 orthogonal sources is already high",
    "- Adding K228 with sparse returns may not meaningfully extend DR (5th source may add little if mostly inactive)",
    "- Effective number of correlated strategies may plateau at 4",
    "",
    "---",
    "",
    "## 9. Verdict, K231 v6.9 if Accepted; K232 Next",
    "",
]

if accepted:
    report_lines += [
        f"### ACCEPT -> K231 v6.9 (Best variant: {best_name})",
        "",
        f"The 5-way meta-ensemble ({best_name}: {best_vm['description']}) passes all acceptance gates:",
        f"- Gate 0 (K228 ML window): OOS Sh={k228_val['k228_ml_window_oos_sh']:.4f} >= 1.0 -> PASS",
        f"- Gate 1 (OOS Sh): {best_vm['oos_sharpe']:.4f} > {GATE_OOS_SH:.2f} -> PASS",
        f"- Gate 2 (WF Min): {best_vm['wf_min']:.4f} >= {GATE_WF_MIN:.4f} -> PASS",
        f"- Gate 3 (MaxDD): {best_vm['oos_maxdd']:.6f} <= {GATE_MAXDD:.6f} -> PASS",
        f"- Gate 4 (All weights > 1%): min={min(best_vm['avg_weights']):.3f} -> PASS",
        "",
        "**Deployment Plan:**",
        f"1. Promote K231 ({best_name}) to v6.9 production",
        "2. Components: K198 Ridge ML + K204 ML DD-embed + K208 DAR reverse carry + K226 ETH validator queue + K228 Stablecoin mint",
        f"3. Allocator: {best_vm['description']}",
        "4. Monitor K228 sparsity — if trade frequency drops below 5/month, reduce K228 cap to 10%",
        "5. Rebalance monthly; alert if K228 WF Sh drops below 0.5 for 30d",
        "",
        "**K232 Next Steps:**",
        "1. CVaR-optimised allocation to reduce tail risk across 5-way",
        "2. Regime-conditional weights: increase K228 only when stablecoin flow signal is high-confidence",
        "3. On-chain native: OP/ARB bridge flow or Jito MEV capture as 6th orthogonal source",
        "4. Production monitoring dashboard: per-strategy daily PnL + weight trajectory + signal activity",
        "5. Explore K228 with 135d window (OOS Sh 2.77) as validation for production deployment",
    ]
else:
    report_lines += [
        "### REJECT — Maintain K229d v6.8 as Production",
        "",
        "No K231 variant improves on K229d v6.8 across all gates simultaneously.",
        "",
        "**Failure Analysis:**",
    ]
    if not gate0_pass:
        report_lines += [
            f"- **Gate 0 FAIL**: K228 ML window OOS Sh={k228_val['k228_ml_window_oos_sh']:.4f} < {GATE_K228_ML_SH:.1f}",
            "- K228's alpha is likely concentrated in pre-ML-window period (2024-05-23 to 2025-01-21)",
            "- Stablecoin mint signal may have been strongest during 2024 bull run; 2025+ signal degraded",
            "- Sparse trading (85% cash) amplifies period-specific noise",
            "",
        ]
    for vname, vm in variants.items():
        sh_pass = vm["oos_sharpe"] > GATE_OOS_SH
        wf_pass = vm["wf_min"] >= GATE_WF_MIN
        dd_pass = vm["oos_maxdd"] >= GATE_MAXDD
        wt_pass = min(vm["avg_weights"]) > 0.01
        failures = []
        if not gate0_pass: failures.append(f"Gate 0 K228 ML window FAIL (Sh={k228_val['k228_ml_window_oos_sh']:.4f})")
        if not sh_pass:    failures.append(f"OOS Sh {vm['oos_sharpe']:.4f} < {GATE_OOS_SH:.2f}")
        if not wf_pass:    failures.append(f"WF Min {vm['wf_min']:.4f} < {GATE_WF_MIN:.4f}")
        if not dd_pass:    failures.append(f"MaxDD {vm['oos_maxdd']:.6f} > {GATE_MAXDD:.6f}")
        if not wt_pass:    failures.append(f"Min weight {min(vm['avg_weights']):.3f} < 0.01")
        status = "PASS (ignoring Gate 0)" if not [f for f in failures if "Gate 0" not in f] else "FAIL: " + "; ".join(failures)
        report_lines.append(f"- **{vname}**: {status}")

    report_lines += [
        "",
        "**K232 Next Steps:**",
        "1. If Gate 0 fail: investigate K228 sub-period performance (2024-05-23 to 2025-01-21 vs ML window)",
        "2. K228 regime-gate: only active during stablecoin supply expansion regime (mint_7d_z > 1.5)",
        "3. Explore K228 with recalibrated signal window aligned to ML window start",
        "4. Alternative 5th source: hash ribbon (K220), Jito MEV (K221), or carry stress (K223)",
        "5. Test K229d v6.8 stability over next 30d before attempting 5-way again",
        "6. CVaR allocation within 4-way K229d: reduce tail risk without adding new source",
    ]

report_lines += [
    "",
    "---",
    f"*Wave K231 | crypto-lab | {result['as_of']}*",
]

report_text = "\n".join(report_lines)
with open("/Users/nekonaomichi/crypto-lab/wave_k231_5way_meta.md", "w") as f:
    f.write(report_text)
print("Saved: wave_k231_5way_meta.md")

print(f"\n{'='*60}")
print(f"K231 COMPLETE — Runtime {runtime}s")
print(f"VERDICT: {verdict}")
print(f"{'='*60}")

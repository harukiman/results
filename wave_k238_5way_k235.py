"""
Wave K238 — 5-Way Meta-Ensemble: K198 × K204 × K208 × K226 × K235
          (K229 v6.8 + Hawkes Liquidation Cascade Predictor)

Context:
  K229 v6.8 is the current production: 4-way meta (K198+K204+K208+K226)
    OOS Sh=12.61, WF folds all positive, WF min=7.44, MaxDD=-0.0012
  K235 = Hawkes liquidation predictor:
    - Counterintuitive direction (long after cascade down-shock)
    - Only 4% active days (highly selective)
    - WF all folds positive [1.45, 0.92, 0.18, 1.25], WF min=0.18 (fold 3 weak)
    - Negative correlation with K226 (-0.23), low correlation with K198/K204/K208

CRITICAL FIRST STEP (Gate 0):
  Validate K235 standalone on K229 ML window (448 days, 2025-01-22 to 2026-04-14).
  K235 own window is 700d (2024-06-22 to 2026-05-22). Re-slice to ML window.
  If fold 3 turns negative on common date cuts → REJECT preemptively.

Variants:
  K238a — Equal weight 20/20/20/20/20
  K238b — Inv-vol uncapped
  K238c — Inv-vol + K226 cap 20% (K229 spec, no K235 constraint)
  K238d — Inv-vol + K226 cap 20% + K235 cap 5%
  K238e — Inv-vol + K226 cap 20% + K235 cap 10%
  K238f — Inv-vol + K226 cap 20% + K235 cap 15%
  K238g — MVP (Minimum Variance Portfolio, rolling 60d)

Acceptance gates vs K229 v6.8:
  Gate 0: K235 ML window WF folds all > 0
  Gate 1: Best variant OOS Sh > K229 OOS Sh (12.61) + 0.10 = 12.71
  Gate 2: WF min >= K229 WF min (7.44)
  Gate 3: MaxDD <= K229 MaxDD (-0.0012)
  Gate 4: All 5 portfolios get non-zero weight (>1%)

Deliverables:
  wave_k238_5way_k235.py    — this script
  wave_k238_5way_k235.json  — metrics + ML validation + correlations
  wave_k238_curves.json     — equity curves
  wave_k238_5way_k235.md    — full report
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
with open("/Users/nekonaomichi/crypto-lab/wave_k235_curves.json") as f:
    k235_raw = json.load(f)

# K198 ML window: 2025-01-22 → 2026-04-14 (448 days)
dates_ml = k198_raw["dates_ml"]   # list of 448 date strings
eq198    = np.array(k198_raw["equity_ridge"])  # len=448
eq204    = np.array(k204_raw["equity_k204"])   # len=448

# K208 is 8h resolution — collapse to daily closing equity
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
eq226 = eq226_raw_aligned / eq226_raw_aligned[0]  # re-base to 1.0

# K235 — Hawkes Liquidation Cascade Predictor
# K235 dates: 2024-06-22 → 2026-05-22 (700 days)
# Need to align to K229 ML window: 2025-01-22 → 2026-04-14 (448 days)
k235_dates  = k235_raw["dates"]       # len=700
k235_equity = k235_raw["strategy_equity"]  # len=700
k235_pnl    = k235_raw["strategy_pnl"]    # len=700 (daily pnl)
k235_signal = k235_raw["signal"]          # len=700

# Build date → values maps for K235
k235_eq_daily  = {}
k235_pnl_daily = {}
k235_sig_daily = {}
for d, eq, pnl, sig in zip(k235_dates, k235_equity, k235_pnl, k235_signal):
    k235_eq_daily[d]  = eq
    k235_pnl_daily[d] = pnl
    k235_sig_daily[d] = sig

k235_eq_values = []
missing_k235 = 0
for d in dates_ml:
    if d in k235_eq_daily:
        k235_eq_values.append(k235_eq_daily[d])
    else:
        missing_k235 += 1
        if k235_eq_values:
            k235_eq_values.append(k235_eq_values[-1])
        else:
            k235_eq_values.append(1.0)

eq235_raw_aligned = np.array(k235_eq_values)
# Re-base K235 to 1.0 on the first ML window date
eq235 = eq235_raw_aligned / eq235_raw_aligned[0]

n = len(dates_ml)
assert len(eq198) == len(eq204) == len(eq208) == len(eq226) == len(eq235) == n, (
    f"Length mismatch: K198={len(eq198)}, K204={len(eq204)}, "
    f"K208={len(eq208)}, K226={len(eq226)}, K235={len(eq235)}, dates={n}"
)

print(f"Data loaded: {n} days ({dates_ml[0]} -> {dates_ml[-1]})")
print(f"K208 missing days filled forward: {missing_k208}/{n}")
print(f"K226 missing days filled forward: {missing_k226}/{n}")
print(f"K235 missing days filled forward: {missing_k235}/{n}")
print(f"K198 equity range: [{eq198.min():.4f}, {eq198.max():.4f}]")
print(f"K204 equity range: [{eq204.min():.4f}, {eq204.max():.4f}]")
print(f"K208 equity range: [{eq208.min():.4f}, {eq208.max():.4f}]")
print(f"K226 equity range: [{eq226.min():.4f}, {eq226.max():.4f}]")
print(f"K235 equity range: [{eq235.min():.4f}, {eq235.max():.4f}]")

# Active days analysis for K235 on ML window
k235_active_days_ml = sum(1 for d in dates_ml if k235_sig_daily.get(d, 0) > 0)
k235_active_pct_ml  = 100.0 * k235_active_days_ml / n
print(f"\nK235 active days on ML window: {k235_active_days_ml}/{n} ({k235_active_pct_ml:.1f}%)")

# Daily returns (geometric)
ret198 = np.diff(eq198) / eq198[:-1]
ret204 = np.diff(eq204) / eq204[:-1]
ret208 = np.diff(eq208) / eq208[:-1]
ret226 = np.diff(eq226) / eq226[:-1]
ret235 = np.diff(eq235) / eq235[:-1]
ret_dates = dates_ml[1:]   # n-1 return dates
n_ret = len(ret198)

print(f"\nReturn series length: {n_ret}")
print(f"K198 daily ret: mean={ret198.mean():.6f}, std={ret198.std():.6f}")
print(f"K204 daily ret: mean={ret204.mean():.6f}, std={ret204.std():.6f}")
print(f"K208 daily ret: mean={ret208.mean():.6f}, std={ret208.std():.6f}")
print(f"K226 daily ret: mean={ret226.mean():.6f}, std={ret226.std():.6f}")
print(f"K235 daily ret: mean={ret235.mean():.6f}, std={ret235.std():.6f}")

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
            "start_date": ret_dates[start],
            "end_date":   ret_dates[end - 1],
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
        "all_positive": bool(np.all(np.array(fold_sharpes) > 0)),
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

def corr_interp(rho):
    a = abs(rho)
    if a > 0.8:
        return "High"
    elif a > 0.5:
        return "Moderate"
    else:
        return "Low"

# ─────────────────────────────────────────────────────────────────────────────
# 3. GATE 0 CRITICAL: K235 standalone validation on K229 ML window (448d)
#    K235 own WF used its 700d window. Re-slice to ML window date cuts.
#    Fold 3 was only 0.18 on 700d window — does it hold on 448d cuts?
# ─────────────────────────────────────────────────────────────────────────────
print("\n" + "="*70)
print("GATE 0 CRITICAL: K235 Standalone on K229 ML Window (448d)")
print("K235 original WF on 700d window: [1.45, 0.92, 0.18, 1.25] all positive")
print("="*70)

k235_ml_oos = oos_metrics(ret235)
k235_ml_wf  = wf_stats(ret235)

print(f"\nK235 on ML window ({n_ret} returns, {dates_ml[0]} -> {dates_ml[-1]}):")
print(f"  OOS Sharpe: {k235_ml_oos['oos_sharpe']:.4f}")
print(f"  OOS MaxDD:  {k235_ml_oos['oos_maxdd']:.6f}")
print(f"  OOS Ann Ret:{k235_ml_oos['oos_ann_ret']:.4f}")
print(f"  OOS Ann Vol:{k235_ml_oos['oos_ann_vol']:.4f}")
print(f"  WF folds:   {k235_ml_wf['fold_sharpes']}")
print(f"  WF min:     {k235_ml_wf['wf_min']:.4f}")
print(f"  WF mean:    {k235_ml_wf['wf_mean']:.4f}")
print(f"  All positive: {k235_ml_wf['all_positive']}")

gate0_pass = k235_ml_wf["all_positive"]
print(f"\nGate 0 (K235 ML window WF all positive): {'PASS' if gate0_pass else 'FAIL -> PREEMPTIVE REJECT'}")
if not gate0_pass:
    failing_folds = [i+1 for i,s in enumerate(k235_ml_wf['fold_sharpes']) if s <= 0]
    print(f"  Failing folds: {failing_folds}")
    print(f"  Fold sharpes: {k235_ml_wf['fold_sharpes']}")

# Show per-fold date ranges for K235 ML window
print(f"\nK235 ML window WF fold details:")
for fd in k235_ml_wf["fold_details"]:
    print(f"  Fold {fd['fold']}: {fd['start_date']} -> {fd['end_date']} "
          f"({fd['n_days']}d) Sh={fd['sharpe']:.4f}")

# ─────────────────────────────────────────────────────────────────────────────
# 4. 5×5 correlation matrix
# ─────────────────────────────────────────────────────────────────────────────
rets_all = np.stack([ret198, ret204, ret208, ret226, ret235], axis=0)  # (5, T)
rho_matrix = np.corrcoef(rets_all)

labels = ["K198", "K204", "K208", "K226", "K235"]
print(f"\n--- 5x5 Pairwise Correlation Matrix ---")
header = "              " + "  ".join(f"{l:>8}" for l in labels)
print(header)
for i, li in enumerate(labels):
    row = f"{li:10}    " + "  ".join(f"{rho_matrix[i,j]:8.4f}" for j in range(5))
    print(row)

# Extract all pairwise
rho_pairs = {}
for i in range(5):
    for j in range(i+1, 5):
        key = f"rho_{labels[i]}_{labels[j]}"
        rho_pairs[key] = round(float(rho_matrix[i, j]), 4)

print("\nPairwise correlations with K235:")
for k, v in rho_pairs.items():
    if "K235" in k:
        print(f"  {k}: {v:.4f}  ({corr_interp(v)})")

# ─────────────────────────────────────────────────────────────────────────────
# 5. Baseline metrics (standalone on ML window)
# ─────────────────────────────────────────────────────────────────────────────
print("\n--- Baseline metrics (on ML-window returns) ---")
baseline = {}
for name, rets in [("K198", ret198), ("K204", ret204), ("K208", ret208),
                    ("K226", ret226), ("K235", ret235)]:
    m = oos_metrics(rets)
    w = wf_stats(rets)
    m.update(w)
    baseline[name] = m
    print(f"{name}: OOS Sh={m['oos_sharpe']:.4f}  MaxDD={m['oos_maxdd']:.6f}  "
          f"WF mean={m['wf_mean']:.4f}  WF min={m['wf_min']:.4f}  AllPos={m['all_positive']}")

# ─────────────────────────────────────────────────────────────────────────────
# 6. 5-Way meta-allocator variants (K238a–K238g)
# ─────────────────────────────────────────────────────────────────────────────
variants     = {}
variant_rets = {}

ROLL     = 30   # rolling window for inv-vol weighting
ROLL_MVP = 60   # rolling window for MVP

# ── K238a: Equal weight 20/20/20/20/20 ───────────────────────────────────────
print("\n--- K238a: Equal weight 20/20/20/20/20 ---")
w_eq  = np.array([0.20, 0.20, 0.20, 0.20, 0.20])
ret_a = w_eq[0]*ret198 + w_eq[1]*ret204 + w_eq[2]*ret208 + w_eq[3]*ret226 + w_eq[4]*ret235
m     = oos_metrics(ret_a)
m.update(wf_stats(ret_a))
m["description"]           = "Equal weight 20/20/20/20/20"
m["avg_weights"]           = [round(float(w), 4) for w in w_eq]
m["diversification_ratio"] = diversification_ratio(w_eq, rets_all)
variants["K238a"]     = m
variant_rets["K238a"] = ret_a
print(f"K238a: OOS Sh={m['oos_sharpe']:.4f}  MaxDD={m['oos_maxdd']:.6f}  "
      f"WF mean={m['wf_mean']:.4f}  WF min={m['wf_min']:.4f}  DR={m['diversification_ratio']:.4f}")

# ── K238b: Inv-vol uncapped ───────────────────────────────────────────────────
print("\n--- K238b: Inv-vol uncapped (30d rolling) ---")
inv_vol_rets_b = np.zeros(n_ret)
w_traj_b       = np.zeros((n_ret, 5))
for i in range(n_ret):
    start_w = max(0, i - ROLL)
    vols = []
    for r in [ret198, ret204, ret208, ret226, ret235]:
        v = np.std(r[start_w:i+1], ddof=1) if i - start_w >= 2 else 1e-6
        vols.append(max(v, 1e-9))
    ivols = np.array([1.0/v for v in vols])
    total = ivols.sum()
    wb = ivols / total
    w_traj_b[i] = wb
    inv_vol_rets_b[i] = np.dot(wb, [ret198[i], ret204[i], ret208[i], ret226[i], ret235[i]])

m = oos_metrics(inv_vol_rets_b)
m.update(wf_stats(inv_vol_rets_b))
m["description"]           = "Inverse-vol weighted uncapped (30d rolling)"
m["avg_weights"]           = [round(float(w_traj_b[:,j].mean()), 4) for j in range(5)]
m["diversification_ratio"] = diversification_ratio(w_traj_b.mean(axis=0), rets_all)
variants["K238b"]     = m
variant_rets["K238b"] = inv_vol_rets_b
print(f"K238b: OOS Sh={m['oos_sharpe']:.4f}  MaxDD={m['oos_maxdd']:.6f}  "
      f"WF mean={m['wf_mean']:.4f}  WF min={m['wf_min']:.4f}  DR={m['diversification_ratio']:.4f}")
print(f"       Avg weights: " + " ".join(f"{l}={m['avg_weights'][j]:.3f}" for j,l in enumerate(labels)))

# ── K238c: Inv-vol + K226 cap 20% (K229 spec, no K235 constraint) ────────────
print("\n--- K238c: Inv-vol + K226 cap 20% (30d rolling) ---")
CAP226_C       = 0.20
inv_vol_rets_c = np.zeros(n_ret)
w_traj_c       = np.zeros((n_ret, 5))
for i in range(n_ret):
    start_w = max(0, i - ROLL)
    vols = []
    for r in [ret198, ret204, ret208, ret226, ret235]:
        v = np.std(r[start_w:i+1], ddof=1) if i - start_w >= 2 else 1e-6
        vols.append(max(v, 1e-9))
    ivols = np.array([1.0/v for v in vols])
    total = ivols.sum()
    wc = ivols / total
    # Apply K226 cap at 20% (index 3)
    if wc[3] > CAP226_C:
        wc[3] = CAP226_C
        iv_rest = np.array([ivols[0], ivols[1], ivols[2], ivols[4]])
        rest_total = iv_rest.sum()
        wc[0] = iv_rest[0] / rest_total * (1.0 - CAP226_C)
        wc[1] = iv_rest[1] / rest_total * (1.0 - CAP226_C)
        wc[2] = iv_rest[2] / rest_total * (1.0 - CAP226_C)
        wc[4] = iv_rest[3] / rest_total * (1.0 - CAP226_C)
    w_traj_c[i] = wc
    inv_vol_rets_c[i] = np.dot(wc, [ret198[i], ret204[i], ret208[i], ret226[i], ret235[i]])

m = oos_metrics(inv_vol_rets_c)
m.update(wf_stats(inv_vol_rets_c))
m["description"]           = "Inv-vol (30d rolling) + K226 cap 20%"
m["avg_weights"]           = [round(float(w_traj_c[:,j].mean()), 4) for j in range(5)]
m["diversification_ratio"] = diversification_ratio(w_traj_c.mean(axis=0), rets_all)
variants["K238c"]     = m
variant_rets["K238c"] = inv_vol_rets_c
print(f"K238c: OOS Sh={m['oos_sharpe']:.4f}  MaxDD={m['oos_maxdd']:.6f}  "
      f"WF mean={m['wf_mean']:.4f}  WF min={m['wf_min']:.4f}  DR={m['diversification_ratio']:.4f}")
print(f"       Avg weights: " + " ".join(f"{l}={m['avg_weights'][j]:.3f}" for j,l in enumerate(labels)))

# Helper: apply multi-cap with iterative redistribution
def apply_caps_5way(ivols, caps, n_iter=5):
    """
    Apply caps to 5-way inv-vol weights iteratively.
    ivols: array of 5 inverse-vol values
    caps:  array of 5 caps (None or float)
    Returns: normalized weight array summing to 1.0
    """
    w = ivols.copy() / ivols.sum()
    for _ in range(n_iter):
        changed = False
        for idx, cap in enumerate(caps):
            if cap is not None and w[idx] > cap:
                excess = w[idx] - cap
                w[idx] = cap
                # redistribute excess proportionally to non-capped components
                others = [j for j in range(5) if j != idx]
                iv_others = ivols[others]
                iv_others_sum = iv_others.sum()
                if iv_others_sum > 1e-12:
                    for k, j in enumerate(others):
                        w[j] += iv_others[k] / iv_others_sum * excess
                changed = True
        if not changed:
            break
    # Safety normalization
    w = np.maximum(w, 0.0)
    s = w.sum()
    if s > 1e-12:
        w = w / s
    return w

# ── K238d: Inv-vol + K226 cap 20% + K235 cap 5% ──────────────────────────────
print("\n--- K238d: Inv-vol + K226 cap 20% + K235 cap 5% (30d rolling) ---")
inv_vol_rets_d = np.zeros(n_ret)
w_traj_d       = np.zeros((n_ret, 5))
caps_d = [None, None, None, 0.20, 0.05]  # K226=20%, K235=5%
for i in range(n_ret):
    start_w = max(0, i - ROLL)
    vols = []
    for r in [ret198, ret204, ret208, ret226, ret235]:
        v = np.std(r[start_w:i+1], ddof=1) if i - start_w >= 2 else 1e-6
        vols.append(max(v, 1e-9))
    ivols = np.array([1.0/v for v in vols])
    wd = apply_caps_5way(ivols, caps_d)
    w_traj_d[i] = wd
    inv_vol_rets_d[i] = np.dot(wd, [ret198[i], ret204[i], ret208[i], ret226[i], ret235[i]])

m = oos_metrics(inv_vol_rets_d)
m.update(wf_stats(inv_vol_rets_d))
m["description"]           = "Inv-vol (30d rolling) + K226 cap 20% + K235 cap 5%"
m["avg_weights"]           = [round(float(w_traj_d[:,j].mean()), 4) for j in range(5)]
m["diversification_ratio"] = diversification_ratio(w_traj_d.mean(axis=0), rets_all)
variants["K238d"]     = m
variant_rets["K238d"] = inv_vol_rets_d
print(f"K238d: OOS Sh={m['oos_sharpe']:.4f}  MaxDD={m['oos_maxdd']:.6f}  "
      f"WF mean={m['wf_mean']:.4f}  WF min={m['wf_min']:.4f}  DR={m['diversification_ratio']:.4f}")
print(f"       Avg weights: " + " ".join(f"{l}={m['avg_weights'][j]:.3f}" for j,l in enumerate(labels)))

# ── K238e: Inv-vol + K226 cap 20% + K235 cap 10% ─────────────────────────────
print("\n--- K238e: Inv-vol + K226 cap 20% + K235 cap 10% (30d rolling) ---")
inv_vol_rets_e = np.zeros(n_ret)
w_traj_e       = np.zeros((n_ret, 5))
caps_e = [None, None, None, 0.20, 0.10]  # K226=20%, K235=10%
for i in range(n_ret):
    start_w = max(0, i - ROLL)
    vols = []
    for r in [ret198, ret204, ret208, ret226, ret235]:
        v = np.std(r[start_w:i+1], ddof=1) if i - start_w >= 2 else 1e-6
        vols.append(max(v, 1e-9))
    ivols = np.array([1.0/v for v in vols])
    we = apply_caps_5way(ivols, caps_e)
    w_traj_e[i] = we
    inv_vol_rets_e[i] = np.dot(we, [ret198[i], ret204[i], ret208[i], ret226[i], ret235[i]])

m = oos_metrics(inv_vol_rets_e)
m.update(wf_stats(inv_vol_rets_e))
m["description"]           = "Inv-vol (30d rolling) + K226 cap 20% + K235 cap 10%"
m["avg_weights"]           = [round(float(w_traj_e[:,j].mean()), 4) for j in range(5)]
m["diversification_ratio"] = diversification_ratio(w_traj_e.mean(axis=0), rets_all)
variants["K238e"]     = m
variant_rets["K238e"] = inv_vol_rets_e
print(f"K238e: OOS Sh={m['oos_sharpe']:.4f}  MaxDD={m['oos_maxdd']:.6f}  "
      f"WF mean={m['wf_mean']:.4f}  WF min={m['wf_min']:.4f}  DR={m['diversification_ratio']:.4f}")
print(f"       Avg weights: " + " ".join(f"{l}={m['avg_weights'][j]:.3f}" for j,l in enumerate(labels)))

# ── K238f: Inv-vol + K226 cap 20% + K235 cap 15% ─────────────────────────────
print("\n--- K238f: Inv-vol + K226 cap 20% + K235 cap 15% (30d rolling) ---")
inv_vol_rets_f = np.zeros(n_ret)
w_traj_f       = np.zeros((n_ret, 5))
caps_f = [None, None, None, 0.20, 0.15]  # K226=20%, K235=15%
for i in range(n_ret):
    start_w = max(0, i - ROLL)
    vols = []
    for r in [ret198, ret204, ret208, ret226, ret235]:
        v = np.std(r[start_w:i+1], ddof=1) if i - start_w >= 2 else 1e-6
        vols.append(max(v, 1e-9))
    ivols = np.array([1.0/v for v in vols])
    wf = apply_caps_5way(ivols, caps_f)
    w_traj_f[i] = wf
    inv_vol_rets_f[i] = np.dot(wf, [ret198[i], ret204[i], ret208[i], ret226[i], ret235[i]])

m = oos_metrics(inv_vol_rets_f)
m.update(wf_stats(inv_vol_rets_f))
m["description"]           = "Inv-vol (30d rolling) + K226 cap 20% + K235 cap 15%"
m["avg_weights"]           = [round(float(w_traj_f[:,j].mean()), 4) for j in range(5)]
m["diversification_ratio"] = diversification_ratio(w_traj_f.mean(axis=0), rets_all)
variants["K238f"]     = m
variant_rets["K238f"] = inv_vol_rets_f
print(f"K238f: OOS Sh={m['oos_sharpe']:.4f}  MaxDD={m['oos_maxdd']:.6f}  "
      f"WF mean={m['wf_mean']:.4f}  WF min={m['wf_min']:.4f}  DR={m['diversification_ratio']:.4f}")
print(f"       Avg weights: " + " ".join(f"{l}={m['avg_weights'][j]:.3f}" for j,l in enumerate(labels)))

# ── K238g: Minimum Variance Portfolio (rolling 60d covariance) ───────────────
print("\n--- K238g: MVP (rolling 60d covariance, long-only) ---")

def mvp_weights_5(cov_matrix):
    """
    Minimum Variance Portfolio weights (long-only, sum to 1) for 5 assets.
    w = Sigma^{-1} 1 / (1' Sigma^{-1} 1), with long-only floor.
    """
    ones = np.ones(5)
    try:
        sigma_inv = np.linalg.inv(cov_matrix)
        w_raw = sigma_inv @ ones
        w_raw = np.maximum(w_raw, 0.0)
        s = w_raw.sum()
        if s < 1e-12:
            return np.full(5, 0.2)
        return w_raw / s
    except np.linalg.LinAlgError:
        return np.full(5, 0.2)

mvp_rets_g = np.zeros(n_ret)
w_traj_g   = np.zeros((n_ret, 5))
for i in range(n_ret):
    start_w = max(0, i - ROLL_MVP)
    seg = np.stack([
        ret198[start_w:i+1],
        ret204[start_w:i+1],
        ret208[start_w:i+1],
        ret226[start_w:i+1],
        ret235[start_w:i+1],
    ], axis=0)
    if seg.shape[1] >= 6:
        cov = np.cov(seg)   # (5, 5)
        wg  = mvp_weights_5(cov)
    else:
        wg = np.full(5, 0.2)
    w_traj_g[i] = wg
    mvp_rets_g[i] = np.dot(wg, [ret198[i], ret204[i], ret208[i], ret226[i], ret235[i]])

m = oos_metrics(mvp_rets_g)
m.update(wf_stats(mvp_rets_g))
m["description"]           = "Minimum Variance Portfolio (rolling 60d covariance, long-only)"
m["avg_weights"]           = [round(float(w_traj_g[:,j].mean()), 4) for j in range(5)]
m["diversification_ratio"] = diversification_ratio(w_traj_g.mean(axis=0), rets_all)
variants["K238g"]     = m
variant_rets["K238g"] = mvp_rets_g
print(f"K238g: OOS Sh={m['oos_sharpe']:.4f}  MaxDD={m['oos_maxdd']:.6f}  "
      f"WF mean={m['wf_mean']:.4f}  WF min={m['wf_min']:.4f}  DR={m['diversification_ratio']:.4f}")
print(f"       Avg weights: " + " ".join(f"{l}={m['avg_weights'][j]:.3f}" for j,l in enumerate(labels)))

# ─────────────────────────────────────────────────────────────────────────────
# 7. Acceptance gates vs K229 v6.8
# ─────────────────────────────────────────────────────────────────────────────
K229_OOS_SH  = 12.61
K229_WF_MIN  = 7.4435
K229_MAXDD   = -0.001201

GATE_OOS_SH  = K229_OOS_SH + 0.10   # > 12.71
GATE_WF_MIN  = K229_WF_MIN           # >= 7.4435
GATE_MAXDD   = K229_MAXDD            # <= -0.001201

print(f"\n{'='*70}")
print(f"--- Acceptance Gates (vs K229 v6.8) ---")
print(f"Gate 0 (prerequisite): K235 ML window WF all folds > 0 -> {'PASS' if gate0_pass else 'FAIL'}")
print(f"Gate 1: Best variant OOS Sh > {GATE_OOS_SH:.2f}")
print(f"Gate 2: WF min >= {GATE_WF_MIN:.4f}")
print(f"Gate 3: MaxDD <= {GATE_MAXDD:.6f}")
print(f"Gate 4: All 5 portfolios must receive non-zero weight (>1%)")
print(f"{'='*70}")

candidates = []
for vname, vm in variants.items():
    sh_pass  = vm["oos_sharpe"] > GATE_OOS_SH
    wf_pass  = vm["wf_min"] >= GATE_WF_MIN
    dd_pass  = vm["oos_maxdd"] >= GATE_MAXDD
    min_wt   = min(vm["avg_weights"])
    wt_pass  = min_wt > 0.01
    gate0_ok = gate0_pass  # K235 ML window must be valid
    all_pass = gate0_ok and sh_pass and wf_pass and dd_pass and wt_pass
    score    = vm["oos_sharpe"] + vm["wf_min"]

    print(f"  {vname}: OOS={vm['oos_sharpe']:.4f}({'v' if sh_pass else 'x'})  "
          f"WFmin={vm['wf_min']:.4f}({'v' if wf_pass else 'x'})  "
          f"MaxDD={vm['oos_maxdd']:.6f}({'v' if dd_pass else 'x'})  "
          f"MinWt={min_wt:.3f}({'v' if wt_pass else 'x'})  "
          f"G0={'v' if gate0_ok else 'x'}  "
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
sh235_oos = baseline["K235"]["oos_sharpe"]
avg_individual = (sh198_oos + sh204_oos + sh208_oos + sh226_oos + sh235_oos) / 5.0
avg_individual_4way = (sh198_oos + sh204_oos + sh208_oos + sh226_oos) / 4.0

print(f"Individual OOS Sharpes: K198={sh198_oos:.4f}, K204={sh204_oos:.4f}, "
      f"K208={sh208_oos:.4f}, K226={sh226_oos:.4f}, K235={sh235_oos:.4f}")
print(f"Average of 5 individuals: {avg_individual:.4f}")
print(f"Average of 4 individuals (K229 components): {avg_individual_4way:.4f}")

best_for_report = best_vm if best_vm else max(variants.values(), key=lambda x: x["oos_sharpe"])
best_name_report = best_name if best_name else max(variants.items(), key=lambda x: x[1]["oos_sharpe"])[0]

synergy_sh       = best_for_report["oos_sharpe"] - avg_individual
synergy_vs_k229  = best_for_report["oos_sharpe"] - K229_OOS_SH
synergy_detected = synergy_sh > 0.02

print(f"Best ensemble ({best_name_report}): {best_for_report['oos_sharpe']:.4f}")
print(f"Synergy vs avg individuals:  {synergy_sh:+.4f} ({'GENUINE' if synergy_detected else 'WEAK'})")
print(f"Improvement vs K229 v6.8:    {synergy_vs_k229:+.4f}")
avg_wf_min_5    = np.mean([baseline[n]["wf_min"] for n in ["K198","K204","K208","K226","K235"]])
wf_min_synergy  = best_for_report["wf_min"] - avg_wf_min_5
print(f"WF-min avg (5 individuals): {avg_wf_min_5:.4f}  |  Best ensemble WF-min: {best_for_report['wf_min']:.4f}  |  D: {wf_min_synergy:+.4f}")

# ─────────────────────────────────────────────────────────────────────────────
# 9. K235 active-days analysis within ensemble folds
# ─────────────────────────────────────────────────────────────────────────────
print("\n--- K235 Active Days Analysis ---")
# Count signal days per fold using ret_dates
fold_size_ret = n_ret // 4
for fi in range(4):
    fold_start = fi * fold_size_ret
    fold_end   = (fi + 1) * fold_size_ret if fi < 3 else n_ret
    fold_dates = ret_dates[fold_start:fold_end]
    active_in_fold = sum(1 for d in fold_dates if k235_sig_daily.get(d, 0) > 0)
    total_in_fold  = len(fold_dates)
    pct = 100.0 * active_in_fold / total_in_fold if total_in_fold > 0 else 0
    print(f"  Fold {fi+1}: {fold_dates[0]} -> {fold_dates[-1]}  "
          f"active={active_in_fold}/{total_in_fold} ({pct:.1f}%)  "
          f"K235 Sh={baseline['K235']['fold_sharpes'][fi]:.4f}")

print(f"\n  Total ML window: {k235_active_days_ml}/{n} days active ({k235_active_pct_ml:.1f}%)")
print(f"  K235 original (700d): 28/730 active days (~4%)")

# ─────────────────────────────────────────────────────────────────────────────
# 10. Build equity curves for output
# ─────────────────────────────────────────────────────────────────────────────
# Include K229d reference
k229d_rets = variant_rets.get("K229d_ref", None)
# Reconstruct K229d using the K229 production weights (K229d = inv-vol + K226 cap 20% on 4-way)
# We'll use the existing K229d equity from K229_curves.json as reference
with open("/Users/nekonaomichi/crypto-lab/wave_k229_curves.json") as f:
    k229_curves = json.load(f)

curves = {
    "K198":      equity_curve(ret198),
    "K204":      equity_curve(ret204),
    "K208":      equity_curve(ret208),
    "K226":      equity_curve(ret226),
    "K235_ml":   equity_curve(ret235),
    "K229d_ref": k229_curves.get("K229d", None),  # production reference (same ML window)
}
for vname, vrets in variant_rets.items():
    curves[vname] = equity_curve(vrets)

curves["dates"] = [dates_ml[0]] + list(ret_dates)

# ─────────────────────────────────────────────────────────────────────────────
# 11. Save JSON outputs
# ─────────────────────────────────────────────────────────────────────────────
runtime = round(time.time() - t0, 2)

if not gate0_pass:
    verdict = (f"REJECT — K235 fails Gate 0: ML window WF fold(s) negative "
               f"[{k235_ml_wf['fold_sharpes']}] — window mismatch fatal (K225 lesson)")
elif accepted:
    verdict = f"ACCEPT as K238 v6.9 — best variant: {best_name}"
else:
    verdict = (f"REJECT — no variant passes all acceptance gates vs K229 v6.8 "
               f"(OOS threshold={GATE_OOS_SH:.2f}, WF min threshold={GATE_WF_MIN:.4f})")

corr_mat_list = [[round(rho_matrix[i,j], 4) for j in range(5)] for i in range(5)]
fold_breakdown = {vname: vm["fold_details"] for vname, vm in variants.items()}

synergy_block = {
    "individual_oos_sharpes": {n: baseline[n]["oos_sharpe"] for n in labels},
    "avg_individual_oos_sh":   round(avg_individual, 4),
    "avg_4way_oos_sh":         round(avg_individual_4way, 4),
    "best_ensemble_name":      best_name_report,
    "best_ensemble_oos_sh":    round(best_for_report["oos_sharpe"], 4),
    "synergy_delta_vs_avg":    round(synergy_sh, 4),
    "synergy_delta_vs_k229":   round(synergy_vs_k229, 4),
    "synergy_detected":        synergy_detected,
    "avg_individual_wf_min":   round(float(avg_wf_min_5), 4),
    "best_ensemble_wf_min":    round(best_for_report["wf_min"], 4),
    "wf_min_synergy":          round(float(wf_min_synergy), 4),
}

historical = {
    "K198_v6.5":  {"oos_sharpe": 10.28,  "oos_maxdd": -0.0053, "wf_mean": 7.91, "wf_min": 6.57,  "components": 1},
    "K217_v6.6":  {"oos_sharpe": 10.43,  "oos_maxdd": -0.0053, "wf_mean": 8.01, "wf_min": 6.91,  "components": 2},
    "K218e_v6.7": {"oos_sharpe": 11.03,  "oos_maxdd": -0.0036, "wf_mean": 8.316, "wf_min": 6.928, "components": 3},
    "K229d_v6.8": {"oos_sharpe": K229_OOS_SH, "oos_maxdd": K229_MAXDD,
                   "wf_mean": None, "wf_min": K229_WF_MIN, "components": 4},
}
for vname, vm in variants.items():
    historical[f"K238_{vname[-1]}"] = {
        "oos_sharpe":  vm["oos_sharpe"],
        "oos_maxdd":   vm["oos_maxdd"],
        "wf_mean":     vm["wf_mean"],
        "wf_min":      vm["wf_min"],
        "dr":          vm["diversification_ratio"],
        "components":  5,
        "avg_weights": vm["avg_weights"],
    }

result = {
    "wave":    "K238",
    "task":    "5-Way Meta-Ensemble: K198 x K204 x K208 x K226 x K235 (Hawkes Liquidation)",
    "as_of":   datetime.now(timezone.utc).isoformat(),
    "runtime_s": runtime,
    "data_info": {
        "n_days":            n,
        "date_start":        dates_ml[0],
        "date_end":          dates_ml[-1],
        "n_returns":         n_ret,
        "k208_missing_days": missing_k208,
        "k226_missing_days": missing_k226,
        "k235_missing_days": missing_k235,
        "k235_active_days_ml": k235_active_days_ml,
        "k235_active_pct_ml":  round(k235_active_pct_ml, 2),
        "k235_strategy":     "Hawkes liquidation cascade predictor (long after cascade-down)",
    },
    "k235_ml_window_validation": {
        "description":           "K235 standalone on K229 ML window (448d) — Gate 0 check",
        "k235_original_wf_folds": [1.4541, 0.9148, 0.1755, 1.251],
        "k235_original_wf_min":   0.1755,
        "k235_original_window":   "700d (2024-06-22 -> 2026-05-22)",
        "ml_window_applied":      f"{dates_ml[0]} -> {dates_ml[-1]} ({n_ret} returns)",
        "k235_ml_oos_sharpe":     k235_ml_oos["oos_sharpe"],
        "k235_ml_oos_maxdd":      k235_ml_oos["oos_maxdd"],
        "k235_ml_oos_ann_ret":    k235_ml_oos["oos_ann_ret"],
        "k235_ml_wf_folds":       k235_ml_wf["fold_sharpes"],
        "k235_ml_wf_min":         k235_ml_wf["wf_min"],
        "k235_ml_wf_mean":        k235_ml_wf["wf_mean"],
        "k235_ml_all_positive":   k235_ml_wf["all_positive"],
        "k235_ml_fold_details":   k235_ml_wf["fold_details"],
        "gate0_pass":             gate0_pass,
        "gate0_verdict":          "PASS" if gate0_pass else "FAIL",
        "note_fold3":             f"Fold 3 Sh={k235_ml_wf['fold_sharpes'][2]:.4f} (was 0.18 on 700d cuts)",
    },
    "correlation_matrix": {
        "labels": labels,
        "matrix": corr_mat_list,
        "pairwise": rho_pairs,
        "interpretation": {k: corr_interp(v) for k, v in rho_pairs.items()},
        "k235_max_abs_rho_with_k229": round(max(
            abs(rho_matrix[4, 0]),  # K235 vs K198
            abs(rho_matrix[4, 1]),  # K235 vs K204
            abs(rho_matrix[4, 2]),  # K235 vs K208
            abs(rho_matrix[4, 3]),  # K235 vs K226
        ), 4),
    },
    "acceptance_gates": {
        "gate0_description":    "K235 ML window WF all folds > 0",
        "gate0_result":         "PASS" if gate0_pass else "FAIL",
        "gate1_oos_threshold":  GATE_OOS_SH,
        "gate2_wf_min":         GATE_WF_MIN,
        "gate3_maxdd":          GATE_MAXDD,
        "gate4_min_weight":     0.01,
        "reference":            "K229d v6.8",
    },
    "active_days_analysis": {
        "k235_active_days_ml_window":  k235_active_days_ml,
        "k235_active_pct_ml_window":   round(k235_active_pct_ml, 2),
        "k235_active_days_original_700d": 28,
        "k235_active_pct_original":    round(28/700*100, 2),
        "note": "K235 is extremely selective (4% active). On ML window it may differ.",
    },
    "baselines":       baseline,
    "variants":        variants,
    "fold_breakdown":  fold_breakdown,
    "synergy":         synergy_block,
    "historical":      historical,
    "verdict":         verdict,
    "accepted":        accepted,
    "gate0_pass":      gate0_pass,
    "best_variant":    best_name,
    "best_variant_metrics": best_vm,
}

with open("/Users/nekonaomichi/crypto-lab/wave_k238_5way_k235.json", "w") as f:
    json.dump(result, f, indent=2)
print("\nSaved: wave_k238_5way_k235.json")

with open("/Users/nekonaomichi/crypto-lab/wave_k238_curves.json", "w") as f:
    json.dump(curves, f)
print("Saved: wave_k238_curves.json")

print(f"\nRuntime: {runtime}s")
print(f"\nVERDICT: {verdict}")

# ─────────────────────────────────────────────────────────────────────────────
# 12. Generate Markdown report
# ─────────────────────────────────────────────────────────────────────────────
k235_val = result["k235_ml_window_validation"]
rho = result["correlation_matrix"]["pairwise"]

gate0_icon = "PASS" if gate0_pass else "FAIL"
verdict_icon = "ACCEPT" if accepted else "REJECT"

report_lines = [
    "# Wave K238 — 5-Way Meta-Ensemble Report (K198 × K204 × K208 × K226 × K235)",
    f"*Generated: {result['as_of']}  |  Runtime: {runtime}s*",
    "",
    "---",
    "",
    "## PRIMARY HEADER: K235 ML Window Validation (Gate 0)",
    "",
    f"**Gate 0 Result: {gate0_icon}**",
    "",
    "| Metric | 700d Original | 448d ML Window |",
    "|--------|--------------|----------------|",
    f"| OOS Sharpe | 1.0419 | {k235_val['k235_ml_oos_sharpe']:.4f} |",
    f"| OOS MaxDD | -0.0700 | {k235_val['k235_ml_oos_maxdd']:.6f} |",
    f"| OOS Ann Ret | 20.6% | {k235_val['k235_ml_oos_ann_ret']*100:.1f}% |",
    f"| WF Folds | [1.45, 0.92, 0.18, 1.25] | {k235_val['k235_ml_wf_folds']} |",
    f"| WF Min | 0.1755 | {k235_val['k235_ml_wf_min']:.4f} |",
    f"| WF Mean | 0.9488 | {k235_val['k235_ml_wf_mean']:.4f} |",
    f"| All Positive | YES | {'YES' if k235_val['k235_ml_all_positive'] else 'NO'} |",
    "",
]

# Per-fold detail table for K235 ML window
report_lines += [
    "### K235 ML Window WF Fold Details",
    "",
    "| Fold | Start | End | N Days | Sharpe |",
    "|------|-------|-----|--------|--------|",
]
for fd in k235_val["k235_ml_fold_details"]:
    report_lines.append(
        f"| {fd['fold']} | {fd['start_date']} | {fd['end_date']} | {fd['n_days']} | {fd['sharpe']:.4f} |"
    )

report_lines += [
    "",
    f"> Note: Fold 3 = {k235_val['note_fold3']}. " +
    ("This is the critical weak fold — must be positive for Gate 0 PASS." if not gate0_pass
     else "Fold 3 remains positive on ML window cuts — Gate 0 confirmed."),
    "",
    "---",
    "",
    "## Executive Summary",
    "",
]

if accepted:
    report_lines += [
        f"**ACCEPT — K238 qualifies as v6.9 production.** Best variant: **{best_name}**",
        "",
        f"- OOS Sharpe: {best_vm['oos_sharpe']:.4f} (vs K229 12.61, threshold 12.71)",
        f"- WF min: {best_vm['wf_min']:.4f} (vs K229 7.4435)",
        f"- MaxDD: {best_vm['oos_maxdd']:.6f} (vs K229 -0.0012)",
        f"- Improvement vs K229: {best_vm['oos_sharpe'] - K229_OOS_SH:+.4f} OOS Sh",
        "",
    ]
elif not gate0_pass:
    report_lines += [
        f"**REJECT — Gate 0 FAIL.** K235 has negative WF fold(s) on K229 ML window.",
        "",
        f"- K235 ML window WF folds: {k235_val['k235_ml_wf_folds']}",
        f"- Failing folds: {[i+1 for i,s in enumerate(k235_val['k235_ml_wf_folds']) if s <= 0]}",
        "- This is the same window-mismatch problem that caused K231/K234/K236 REJECT.",
        "- Preemptive REJECT without ensemble test (K225 lesson applied).",
        "",
    ]
else:
    best_any = max(variants.items(), key=lambda x: x[1]["oos_sharpe"])
    report_lines += [
        f"**REJECT — No variant meets all gates vs K229 v6.8.**",
        "",
        f"- Best OOS Sh: {best_any[1]['oos_sharpe']:.4f} ({best_any[0]}) — threshold: {GATE_OOS_SH:.2f}",
        f"- K229 remains v6.8 production.",
        "",
    ]

# Add K229 context
report_lines += [
    "### Context: K229 v6.8 Production Reference",
    "",
    "| Metric | K229d v6.8 |",
    "|--------|-----------|",
    f"| OOS Sharpe | 12.61 |",
    f"| WF Min | 7.4435 |",
    f"| MaxDD | -0.001201 |",
    f"| Components | K198 + K204 + K208 + K226 (4-way) |",
    "",
    "### K238 Context: Why K235 Was Added",
    "",
    "- K235 Hawkes predictor: **counterintuitive direction** (long after cascade down-shock)",
    "- **Only 4% active days** → highly selective, low interference with K229 components",
    "- **Negative correlation with K226** (ρ = -0.23): rare partial hedge property",
    "- K233/K228/K236 all failed due to window-mismatch (negative fold 3 on K229 cuts)",
    "- K235 fold 3 was only 0.18 on 700d window — the critical weak spot to validate",
    "",
    "---",
    "",
    "## 5x5 Correlation Matrix",
    "",
    "| | K198 | K204 | K208 | K226 | K235 |",
    "|--|------|------|------|------|------|",
]

for i, li in enumerate(labels):
    row = f"| **{li}** | " + " | ".join(f"{rho_matrix[i,j]:.4f}" for j in range(5)) + " |"
    report_lines.append(row)

report_lines += [
    "",
    "**Key correlations with K235:**",
    "",
]
for k, v in rho_pairs.items():
    if "K235" in k:
        report_lines.append(f"- {k.replace('rho_', '')}: ρ = {v:.4f} ({corr_interp(v)})")

report_lines += [
    "",
    f"> K235 max |ρ| with K229 components: {result['correlation_matrix']['k235_max_abs_rho_with_k229']:.4f} (Low, no dominant correlation)",
    "",
    "---",
    "",
    "## Baseline Metrics (ML Window: 448 days)",
    "",
    "| Strategy | OOS Sh | OOS MaxDD | WF Mean | WF Min | WF Folds | All+ |",
    "|----------|--------|-----------|---------|--------|----------|------|",
]
for name in labels:
    b = baseline[name]
    report_lines.append(
        f"| {name} | {b['oos_sharpe']:.4f} | {b['oos_maxdd']:.6f} | "
        f"{b['wf_mean']:.4f} | {b['wf_min']:.4f} | {b['fold_sharpes']} | "
        f"{'YES' if b['all_positive'] else 'NO'} |"
    )

report_lines += [
    "",
    "---",
    "",
    "## Variant Performance Summary",
    "",
    f"Thresholds: OOS Sh > {GATE_OOS_SH:.2f} | WF min >= {GATE_WF_MIN:.4f} | MaxDD <= {GATE_MAXDD:.6f}",
    "",
    "| Variant | OOS Sh | WF Min | WF Mean | MaxDD | Min Wt | DR | Pass? |",
    "|---------|--------|--------|---------|-------|--------|-----|-------|",
]
for vname, vm in variants.items():
    sh_p  = vm["oos_sharpe"] > GATE_OOS_SH
    wf_p  = vm["wf_min"] >= GATE_WF_MIN
    dd_p  = vm["oos_maxdd"] >= GATE_MAXDD
    mw    = min(vm["avg_weights"])
    mw_p  = mw > 0.01
    all_p = gate0_pass and sh_p and wf_p and dd_p and mw_p
    report_lines.append(
        f"| **{vname}** | {vm['oos_sharpe']:.4f} {'v' if sh_p else 'x'} | "
        f"{vm['wf_min']:.4f} {'v' if wf_p else 'x'} | {vm['wf_mean']:.4f} | "
        f"{vm['oos_maxdd']:.6f} {'v' if dd_p else 'x'} | {mw:.3f} {'v' if mw_p else 'x'} | "
        f"{vm['diversification_ratio']:.4f} | {'**PASS**' if all_p else 'FAIL'} |"
    )

report_lines += [
    "",
    "---",
    "",
    "## Per-Variant Per-Fold Breakdown",
    "",
]
for vname, vm in variants.items():
    report_lines.append(f"### {vname}: {vm['description']}")
    report_lines.append(f"**Avg weights:** " + ", ".join(f"{labels[j]}={vm['avg_weights'][j]:.3f}" for j in range(5)))
    report_lines.append("")
    report_lines.append("| Fold | Start | End | N Days | Sharpe |")
    report_lines.append("|------|-------|-----|--------|--------|")
    for fd in vm["fold_details"]:
        report_lines.append(
            f"| {fd['fold']} | {fd.get('start_date','?')} | {fd.get('end_date','?')} | "
            f"{fd['n_days']} | {fd['sharpe']:.4f} |"
        )
    report_lines.append("")

report_lines += [
    "---",
    "",
    "## K235 Active Days Analysis",
    "",
    "| Fold | Start | End | N Days | Active | Active% | K235 Fold Sh |",
    "|------|-------|-----|--------|--------|---------|--------------|",
]
fold_size_ret = n_ret // 4
for fi in range(4):
    fold_start = fi * fold_size_ret
    fold_end   = (fi + 1) * fold_size_ret if fi < 3 else n_ret
    fold_dates_slice = ret_dates[fold_start:fold_end]
    active_in_fold = sum(1 for d in fold_dates_slice if k235_sig_daily.get(d, 0) > 0)
    total_in_fold  = len(fold_dates_slice)
    pct = 100.0 * active_in_fold / total_in_fold if total_in_fold > 0 else 0
    k235_fold_sh = baseline["K235"]["fold_sharpes"][fi]
    report_lines.append(
        f"| {fi+1} | {fold_dates_slice[0]} | {fold_dates_slice[-1]} | "
        f"{total_in_fold} | {active_in_fold} | {pct:.1f}% | {k235_fold_sh:.4f} |"
    )

report_lines += [
    "",
    f"**Total ML window:** {k235_active_days_ml}/{n} days active ({k235_active_pct_ml:.1f}%)",
    f"**Original 700d window:** 28/700 (~4.0%)",
    "",
    "> K235 is the most selective strategy in the ensemble. Its low active rate means it acts",
    "> as a *spike enhancer* on specific cascade events, not a continuous alpha source.",
    "> This property is why a cap (5–15%) rather than free inv-vol allocation is preferred.",
    "",
    "---",
    "",
    "## Synergy Analysis",
    "",
    f"| Metric | Value |",
    f"|--------|-------|",
    f"| Avg individual OOS Sh (5-way) | {avg_individual:.4f} |",
    f"| Avg individual OOS Sh (4-way K229) | {avg_individual_4way:.4f} |",
    f"| Best ensemble ({best_name_report}) OOS Sh | {best_for_report['oos_sharpe']:.4f} |",
    f"| Synergy vs avg individuals | {synergy_sh:+.4f} |",
    f"| Improvement vs K229 v6.8 | {synergy_vs_k229:+.4f} |",
    f"| WF-min avg individuals | {avg_wf_min_5:.4f} |",
    f"| Best ensemble WF-min | {best_for_report['wf_min']:.4f} |",
    f"| WF-min synergy | {wf_min_synergy:+.4f} |",
    "",
    "---",
    "",
    "## Historical Evolution",
    "",
    "| Version | OOS Sh | WF Min | MaxDD | Components |",
    "|---------|--------|--------|-------|------------|",
    "| K198 v6.5 | 10.28 | 6.57 | -0.0053 | 1 |",
    "| K217 v6.6 | 10.43 | 6.91 | -0.0053 | 2 |",
    "| K218e v6.7 | 11.03 | 6.928 | -0.0036 | 3 |",
    f"| K229d v6.8 | 12.61 | 7.4435 | -0.001201 | 4 |",
]
for vname, vm in variants.items():
    all_p = gate0_pass and vm["oos_sharpe"] > GATE_OOS_SH and vm["wf_min"] >= GATE_WF_MIN and vm["oos_maxdd"] >= GATE_MAXDD and min(vm["avg_weights"]) > 0.01
    marker = " **[ACCEPTED]**" if all_p else ""
    report_lines.append(
        f"| K238 {vname[-1]} v6.9 | {vm['oos_sharpe']:.4f} | {vm['wf_min']:.4f} | "
        f"{vm['oos_maxdd']:.6f} | 5{marker} |"
    )

report_lines += [
    "",
    "---",
    "",
    "## Verdict: K238 v6.9 if Accepted",
    "",
]
if accepted:
    report_lines += [
        f"### **ACCEPT — K238 → v6.9 Production**",
        "",
        f"Best variant: **{best_name}** — {best_vm['description']}",
        "",
        f"| Gate | Requirement | Result | Pass? |",
        f"|------|-------------|--------|-------|",
        f"| Gate 0 | K235 ML WF all positive | {k235_val['k235_ml_wf_folds']} | {'PASS' if gate0_pass else 'FAIL'} |",
        f"| Gate 1 | OOS Sh > {GATE_OOS_SH:.2f} | {best_vm['oos_sharpe']:.4f} | PASS |",
        f"| Gate 2 | WF min >= {GATE_WF_MIN:.4f} | {best_vm['wf_min']:.4f} | PASS |",
        f"| Gate 3 | MaxDD <= {GATE_MAXDD:.6f} | {best_vm['oos_maxdd']:.6f} | PASS |",
        f"| Gate 4 | All weights > 1% | min={min(best_vm['avg_weights']):.3f} | PASS |",
        "",
        f"**Production config:**",
        f"- Allocator: {best_vm['description']}",
        f"- Weights: " + ", ".join(f"{labels[j]}={best_vm['avg_weights'][j]*100:.1f}%" for j in range(5)),
        f"- K235 acts as a low-frequency spike enhancer (cascade exhaustion bounces)",
        "",
    ]
elif not gate0_pass:
    report_lines += [
        f"### **REJECT — Gate 0 FAIL (Window Mismatch)**",
        "",
        f"K235 has negative WF fold(s) on the K229 ML window (448d cuts):",
        f"- K235 ML WF folds: {k235_val['k235_ml_wf_folds']}",
        f"- Same failure pattern as K231 (K228), K234 (K232b), K236 (K233)",
        "",
        "**K229d v6.8 remains production.** K235 is a valid standalone strategy (ACCEPT from K235 wave)",
        "but is incompatible with K229's ML window cuts.",
        "",
        "**Next steps:** Explore alternative window alignment or a new 5th candidate with better ML-window stability.",
    ]
else:
    report_lines += [
        f"### **REJECT — Gates Not Met**",
        "",
        f"K235 passes Gate 0 (ML window WF all positive) but no variant achieves sufficient",
        f"OOS Sh improvement (+{(max(vm['oos_sharpe'] for vm in variants.values())-K229_OOS_SH):+.4f} vs threshold +0.10).",
        "",
        "**K229d v6.8 remains production.**",
    ]

report_lines += [
    "",
    "---",
    f"*Wave K238 | {result['as_of']} | Runtime: {runtime}s*",
]

md_content = "\n".join(report_lines)
with open("/Users/nekonaomichi/crypto-lab/wave_k238_5way_k235.md", "w") as f:
    f.write(md_content)
print("Saved: wave_k238_5way_k235.md")

print(f"\n{'='*70}")
print(f"K238 COMPLETE")
print(f"Gate 0 (K235 ML WF all positive): {'PASS' if gate0_pass else 'FAIL'}")
print(f"Accepted: {accepted}")
print(f"Best variant: {best_name}")
print(f"VERDICT: {verdict}")
print(f"{'='*70}")

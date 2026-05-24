"""
Wave K234 — 5-Way Meta-Ensemble: K198 × K204 × K208 × K226 × K232b (Gated K228)
          K229 v6.8 production (4-way) + K232b (regime-gated stablecoin mint/burn)

K231 REJECT: K229 + K228 (ungated) failed — K228 ML fold 2 = -2.15 drag
K232b FIX:   Soft regime gate → K228 ML fold 2: -2.15 → -1.42 (30% reduction)
K232b standalone: OOS Sh 2.86, own-window WF all positive (min 0.56)

CRITICAL: K232b ML window fold 2 = -1.415 (gate requires >= -1.0 for acceptance).
          This is a CONDITIONAL test — we proceed but flag if gate fails.

Variants:
  K234a — Equal weight 20/20/20/20/20
  K234b — Inverse-volatility weighted (rolling 30d, uncapped)
  K234c — Inv-vol + K226 cap 20% (K229d spec preserved)
  K234d — Inv-vol + K226 cap 20% + K232b cap 10%
  K234e — Inv-vol + K226 cap 20% + K232b cap 20%
  K234f — MVP (Minimum Variance Portfolio, rolling 60d covariance)

Acceptance gates vs K229 v6.8 (K229d):
  K232b ML window fold 2 >= -1.0   (was -2.15 ungated; -1.415 gated; gate = -1.0)
  Best variant OOS Sh > 12.71      (+0.10 vs K229d 12.61)
  WF min >= 7.44                   (>= K229d WF min 7.4435)
  MaxDD <= -0.0012                 (<= K229d MaxDD -0.001201)
  All 5 portfolios non-zero weight (>1%)

Deliverables:
  wave_k234_5way_gated.py    — this script
  wave_k234_5way_gated.json  — metrics + ML window validation + correlations
  wave_k234_curves.json      — equity curves
  wave_k234_5way_gated.md    — full report
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
with open("/Users/nekonaomichi/crypto-lab/wave_k232_curves.json") as f:
    k232_raw = json.load(f)

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
eq226 = eq226_raw_aligned / eq226_raw_aligned[0]  # Re-base to 1.0

# K232b — Regime-gated K228 (Stablecoin Mint/Burn with soft regime gate)
# K232b_equity is a list of dicts {date, eq} over 730 days (2024-05-23 to 2026-05-22)
k232b_eq_list = k232_raw["K232b_equity"]  # list of dicts with 'date' and 'eq'
k232b_eq_map  = {item["date"]: item["eq"] for item in k232b_eq_list}

k232b_eq_values = []
missing_k232b = 0
for d in dates_ml:
    if d in k232b_eq_map:
        k232b_eq_values.append(k232b_eq_map[d])
    else:
        missing_k232b += 1
        if k232b_eq_values:
            k232b_eq_values.append(k232b_eq_values[-1])
        else:
            k232b_eq_values.append(1.0)

eq232b_raw_aligned = np.array(k232b_eq_values)
eq232b = eq232b_raw_aligned / eq232b_raw_aligned[0]  # Re-base to 1.0

n = len(dates_ml)
assert len(eq198) == len(eq204) == len(eq208) == len(eq226) == len(eq232b) == n, (
    f"Length mismatch: K198={len(eq198)}, K204={len(eq204)}, "
    f"K208={len(eq208)}, K226={len(eq226)}, K232b={len(eq232b)}, dates={n}"
)

print(f"Data loaded: {n} days ({dates_ml[0]} -> {dates_ml[-1]})")
print(f"K208  missing days filled forward: {missing_k208}/{n}")
print(f"K226  missing days filled forward: {missing_k226}/{n}")
print(f"K232b missing days filled forward: {missing_k232b}/{n}")
print(f"K198  equity range: [{eq198.min():.4f}, {eq198.max():.4f}]")
print(f"K204  equity range: [{eq204.min():.4f}, {eq204.max():.4f}]")
print(f"K208  equity range: [{eq208.min():.4f}, {eq208.max():.4f}]")
print(f"K226  equity range: [{eq226.min():.4f}, {eq226.max():.4f}]")
print(f"K232b equity range: [{eq232b.min():.4f}, {eq232b.max():.4f}]")

# Daily returns (geometric)
ret198  = np.diff(eq198)  / eq198[:-1]
ret204  = np.diff(eq204)  / eq204[:-1]
ret208  = np.diff(eq208)  / eq208[:-1]
ret226  = np.diff(eq226)  / eq226[:-1]
ret232b = np.diff(eq232b) / eq232b[:-1]
ret_dates = dates_ml[1:]   # n-1 return dates
n_ret = len(ret198)

print(f"\nReturn series length: {n_ret}")
print(f"K198  daily ret: mean={ret198.mean():.6f}, std={ret198.std():.6f}")
print(f"K204  daily ret: mean={ret204.mean():.6f}, std={ret204.std():.6f}")
print(f"K208  daily ret: mean={ret208.mean():.6f}, std={ret208.std():.6f}")
print(f"K226  daily ret: mean={ret226.mean():.6f}, std={ret226.std():.6f}")
print(f"K232b daily ret: mean={ret232b.mean():.6f}, std={ret232b.std():.6f}")
print(f"K232b non-zero returns: {(np.abs(ret232b)>1e-10).sum()} / {n_ret} ({(np.abs(ret232b)>1e-10).sum()/n_ret*100:.1f}%)")

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
# 3. CRITICAL: K232b standalone validation on K229 ML window (448d)
#    K231 REJECT root cause: K228 ungated fold 2 = -2.15 dragged ensemble
#    K232b IMPROVED: soft regime gate → fold 2 = -1.415 (30% reduction)
#    Gate: fold 2 >= -1.0 for acceptance into 5-way ensemble
#
#    METHODOLOGY NOTE: K232 computed fold boundaries by CALENDAR DATE (112 days each).
#    K229 wf_stats uses INDEX-based splits (111/111/111/114 from 447 returns).
#    The fold 2 date-based boundary is 2025-05-14 to 2025-09-02 (K232 methodology).
#    We validate using BOTH methods; the K232 date-based fold is authoritative for Gate 0a.
# ─────────────────────────────────────────────────────────────────────────────
print("\n" + "="*70)
print("CRITICAL CHECK: K232b (Gated K228) Standalone on K229 ML Window (448d)")
print("="*70)
print(f"K228 ungated ML fold 2:   -2.1503 (K231 REJECT root cause)")
print(f"K232b gated ML fold 2:    -1.415  (30% improvement, gate = -1.0)")
print(f"K232b standalone OOS Sh:   2.86 (own 730d window)")
print(f"Gate for K234 acceptance:  fold 2 >= -1.0")

# K232b folds using K232 calendar-date boundaries (authoritative - matches K232 report)
K232_FOLD_BOUNDARIES = [
    ("fold1", "2025-01-22", "2025-05-13"),
    ("fold2", "2025-05-14", "2025-09-02"),
    ("fold3", "2025-09-03", "2025-12-23"),
    ("fold4", "2025-12-24", "2026-04-14"),
]
ret_dates_list = list(dates_ml[:-1])  # returns correspond to dates_ml[0..n-2]

def fold_sharpe_by_date(rets, ret_date_list, start_date, end_date):
    """Compute Sharpe for returns falling within [start_date, end_date] (inclusive)."""
    fold_rets = [r for d, r in zip(ret_date_list, rets) if start_date <= d <= end_date]
    return sharpe(np.array(fold_rets)), len(fold_rets)

k232b_date_fold_sharpes = []
k232b_date_fold_details = []
for i, (fname, s, e) in enumerate(K232_FOLD_BOUNDARIES):
    sh_d, n_d = fold_sharpe_by_date(ret232b, ret_dates_list, s, e)
    k232b_date_fold_sharpes.append(round(float(sh_d), 4))
    k232b_date_fold_details.append({
        "fold": i + 1, "start": s, "end": e, "n_days": n_d, "sharpe": round(float(sh_d), 4)
    })

# Index-based WF (standard K229 methodology — for ensemble variants)
k232b_ml_oos = oos_metrics(ret232b)
k232b_ml_wf  = wf_stats(ret232b)

print(f"\nK232b on ML window ({n_ret} returns):")
print(f"  OOS Sharpe: {k232b_ml_oos['oos_sharpe']:.4f}")
print(f"  OOS MaxDD:  {k232b_ml_oos['oos_maxdd']:.6f}")
print(f"  OOS Ann Ret:{k232b_ml_oos['oos_ann_ret']:.4f}")
print(f"  WF folds (index-based, K229 method): {k232b_ml_wf['fold_sharpes']}")
print(f"  WF folds (date-based, K232 method):  {k232b_date_fold_sharpes}")
print(f"  WF fold 2 (date-based):  {k232b_date_fold_sharpes[1]:.4f}  (gate >= -1.0)")
print(f"  WF min (date-based):     {min(k232b_date_fold_sharpes):.4f}")

# K234 acceptance gate for K232b: fold 2 (date-based) >= -1.0
k232b_fold2 = k232b_date_fold_sharpes[1]  # authoritative: K232 calendar-date boundary
gate0_fold2_pass = k232b_fold2 >= -1.0
# Standalone OOS Sh gate: >= 1.0 (reasonable signal quality)
gate0_oos_pass = k232b_ml_oos['oos_sharpe'] >= 1.0

print(f"\nK232b ML-window Gate 0a (fold 2 date-based >= -1.0): {k232b_fold2:.4f} -> {'PASS' if gate0_fold2_pass else 'FAIL'}")
print(f"K232b ML-window Gate 0b (OOS Sh >= 1.0):            {k232b_ml_oos['oos_sharpe']:.4f} -> {'PASS' if gate0_oos_pass else 'FAIL'}")

gate0_pass = gate0_fold2_pass and gate0_oos_pass
print(f"Gate 0 combined: {'PASS — proceed with ensemble' if gate0_pass else 'CONDITIONAL FAIL — fold 2 still negative'}")
if not gate0_fold2_pass:
    print(f"  NOTE: K232b fold 2 (date-based) = {k232b_fold2:.4f} (below -1.0 gate)")
    print(f"        K231 ungated was -2.15; K232b improved 30% but not fully remediated")
    print(f"        Proceeding with ensemble test — capped variants (K234d/K234e) may still pass")

# ─────────────────────────────────────────────────────────────────────────────
# 4. 5x5 Correlation Matrix
# ─────────────────────────────────────────────────────────────────────────────
rets_all = np.stack([ret198, ret204, ret208, ret226, ret232b], axis=0)  # (5, T)
rho_matrix = np.corrcoef(rets_all)

labels = ["K198", "K204", "K208", "K226", "K232b"]
print(f"\n--- 5x5 Pairwise Correlation Matrix ---")
header = "               " + "  ".join(f"{l:>7}" for l in labels)
print(header)
for i, li in enumerate(labels):
    row = f"{li:10}     " + "  ".join(f"{rho_matrix[i,j]:7.4f}" for j in range(5))
    print(row)

rho_198_204  = float(rho_matrix[0, 1])
rho_198_208  = float(rho_matrix[0, 2])
rho_198_226  = float(rho_matrix[0, 3])
rho_198_232b = float(rho_matrix[0, 4])
rho_204_208  = float(rho_matrix[1, 2])
rho_204_226  = float(rho_matrix[1, 3])
rho_204_232b = float(rho_matrix[1, 4])
rho_208_226  = float(rho_matrix[2, 3])
rho_208_232b = float(rho_matrix[2, 4])
rho_226_232b = float(rho_matrix[3, 4])

def corr_interp(rho):
    a = abs(rho)
    if a > 0.8:
        return "High"
    elif a > 0.5:
        return "Moderate"
    else:
        return "Low"

# ─────────────────────────────────────────────────────────────────────────────
# 5. Baseline metrics (K198, K204, K208, K226, K232b standalone on ML window)
# ─────────────────────────────────────────────────────────────────────────────
print("\n--- Baseline metrics (on ML-window returns) ---")
baseline = {}
for name, rets in [("K198", ret198), ("K204", ret204), ("K208", ret208),
                   ("K226", ret226), ("K232b", ret232b)]:
    m = oos_metrics(rets)
    w = wf_stats(rets)
    m.update(w)
    baseline[name] = m
    print(f"{name}: OOS Sh={m['oos_sharpe']:.4f}  MaxDD={m['oos_maxdd']:.6f}  "
          f"WF mean={m['wf_mean']:.4f}  WF min={m['wf_min']:.4f}")

# ─────────────────────────────────────────────────────────────────────────────
# 6. 5-Way meta-allocator variants (K234a–K234f)
# ─────────────────────────────────────────────────────────────────────────────
variants     = {}
variant_rets = {}

ROLL     = 30   # rolling window for inv-vol weighting
ROLL_MVP = 60   # rolling window for MVP

# ── K234a: Equal weight 20/20/20/20/20 ───────────────────────────────────────
print("\n--- K234a: Equal weight 20/20/20/20/20 ---")
w_eq  = np.array([0.20, 0.20, 0.20, 0.20, 0.20])
ret_a = (w_eq[0]*ret198 + w_eq[1]*ret204 + w_eq[2]*ret208 +
         w_eq[3]*ret226 + w_eq[4]*ret232b)
m     = oos_metrics(ret_a)
m.update(wf_stats(ret_a))
m["description"]           = "Equal weight 20/20/20/20/20"
m["avg_weights"]           = [round(float(w), 4) for w in w_eq]
m["diversification_ratio"] = diversification_ratio(w_eq, rets_all)
variants["K234a"]     = m
variant_rets["K234a"] = ret_a
print(f"K234a: OOS Sh={m['oos_sharpe']:.4f}  MaxDD={m['oos_maxdd']:.6f}  "
      f"WF mean={m['wf_mean']:.4f}  WF min={m['wf_min']:.4f}  DR={m['diversification_ratio']:.4f}")

# ── K234b: Inv-vol weighted (rolling 30d, uncapped) ──────────────────────────
print("\n--- K234b: Inv-vol weighted (30d rolling, uncapped) ---")
inv_vol_rets_b = np.zeros(n_ret)
w_traj_b       = np.zeros((n_ret, 5))
for i in range(n_ret):
    start_w = max(0, i - ROLL)
    seg_len = i - start_w
    v198  = np.std(ret198[start_w:i+1],  ddof=1) if seg_len >= 2 else 1e-6
    v204  = np.std(ret204[start_w:i+1],  ddof=1) if seg_len >= 2 else 1e-6
    v208  = np.std(ret208[start_w:i+1],  ddof=1) if seg_len >= 2 else 1e-6
    v226  = np.std(ret226[start_w:i+1],  ddof=1) if seg_len >= 2 else 1e-6
    v232b = np.std(ret232b[start_w:i+1], ddof=1) if seg_len >= 2 else 1e-6
    iv198  = 1.0 / max(v198,  1e-9)
    iv204  = 1.0 / max(v204,  1e-9)
    iv208  = 1.0 / max(v208,  1e-9)
    iv226  = 1.0 / max(v226,  1e-9)
    iv232b = 1.0 / max(v232b, 1e-9)
    total = iv198 + iv204 + iv208 + iv226 + iv232b
    wb = np.array([iv198/total, iv204/total, iv208/total, iv226/total, iv232b/total])
    w_traj_b[i] = wb
    inv_vol_rets_b[i] = (wb[0]*ret198[i] + wb[1]*ret204[i] + wb[2]*ret208[i] +
                         wb[3]*ret226[i] + wb[4]*ret232b[i])

m = oos_metrics(inv_vol_rets_b)
m.update(wf_stats(inv_vol_rets_b))
m["description"]           = "Inverse-vol weighted (30d rolling, uncapped)"
m["avg_weights"]           = [round(float(w_traj_b[:,j].mean()), 4) for j in range(5)]
m["diversification_ratio"] = diversification_ratio(w_traj_b.mean(axis=0), rets_all)
variants["K234b"]     = m
variant_rets["K234b"] = inv_vol_rets_b
print(f"K234b: OOS Sh={m['oos_sharpe']:.4f}  MaxDD={m['oos_maxdd']:.6f}  "
      f"WF mean={m['wf_mean']:.4f}  WF min={m['wf_min']:.4f}  DR={m['diversification_ratio']:.4f}")
wts_b = m["avg_weights"]
print(f"       Avg wts: K198={wts_b[0]:.3f} K204={wts_b[1]:.3f} K208={wts_b[2]:.3f} "
      f"K226={wts_b[3]:.3f} K232b={wts_b[4]:.3f}")

# ── K234c: Inv-vol + K226 cap 20% (K229d spec preserved) ─────────────────────
print("\n--- K234c: Inv-vol + K226 cap 20% (K229d spec) ---")
CAP226_C       = 0.20
inv_vol_rets_c = np.zeros(n_ret)
w_traj_c       = np.zeros((n_ret, 5))
for i in range(n_ret):
    start_w = max(0, i - ROLL)
    seg_len = i - start_w
    v198  = np.std(ret198[start_w:i+1],  ddof=1) if seg_len >= 2 else 1e-6
    v204  = np.std(ret204[start_w:i+1],  ddof=1) if seg_len >= 2 else 1e-6
    v208  = np.std(ret208[start_w:i+1],  ddof=1) if seg_len >= 2 else 1e-6
    v226  = np.std(ret226[start_w:i+1],  ddof=1) if seg_len >= 2 else 1e-6
    v232b = np.std(ret232b[start_w:i+1], ddof=1) if seg_len >= 2 else 1e-6
    iv198  = 1.0 / max(v198,  1e-9)
    iv204  = 1.0 / max(v204,  1e-9)
    iv208  = 1.0 / max(v208,  1e-9)
    iv226  = 1.0 / max(v226,  1e-9)
    iv232b = 1.0 / max(v232b, 1e-9)
    total = iv198 + iv204 + iv208 + iv226 + iv232b
    wc = np.array([iv198/total, iv204/total, iv208/total, iv226/total, iv232b/total])
    # Apply K226 cap at 20%
    if wc[3] > CAP226_C:
        wc[3] = CAP226_C
        iv_rest = np.array([iv198, iv204, iv208, iv232b])
        rest_total = iv_rest.sum()
        wc[0] = iv198  / rest_total * (1.0 - CAP226_C)
        wc[1] = iv204  / rest_total * (1.0 - CAP226_C)
        wc[2] = iv208  / rest_total * (1.0 - CAP226_C)
        wc[4] = iv232b / rest_total * (1.0 - CAP226_C)
    w_traj_c[i] = wc
    inv_vol_rets_c[i] = (wc[0]*ret198[i] + wc[1]*ret204[i] + wc[2]*ret208[i] +
                         wc[3]*ret226[i] + wc[4]*ret232b[i])

m = oos_metrics(inv_vol_rets_c)
m.update(wf_stats(inv_vol_rets_c))
m["description"]           = "Inv-vol weighted (30d rolling) + K226 cap 20%"
m["avg_weights"]           = [round(float(w_traj_c[:,j].mean()), 4) for j in range(5)]
m["diversification_ratio"] = diversification_ratio(w_traj_c.mean(axis=0), rets_all)
variants["K234c"]     = m
variant_rets["K234c"] = inv_vol_rets_c
print(f"K234c: OOS Sh={m['oos_sharpe']:.4f}  MaxDD={m['oos_maxdd']:.6f}  "
      f"WF mean={m['wf_mean']:.4f}  WF min={m['wf_min']:.4f}  DR={m['diversification_ratio']:.4f}")
wts_c = m["avg_weights"]
print(f"       Avg wts: K198={wts_c[0]:.3f} K204={wts_c[1]:.3f} K208={wts_c[2]:.3f} "
      f"K226={wts_c[3]:.3f} K232b={wts_c[4]:.3f}")

# ── K234d: Inv-vol + K226 cap 20% + K232b cap 10% ────────────────────────────
print("\n--- K234d: Inv-vol + K226 cap 20% + K232b cap 10% ---")
CAP226_D  = 0.20
CAP232b_D = 0.10

def apply_two_caps_5(iv198, iv204, iv208, iv226, iv232b, cap226, cap232b):
    """Apply caps to K226 and K232b iteratively, redistribute to K198/K204/K208."""
    iv = np.array([iv198, iv204, iv208, iv226, iv232b])
    w  = iv / iv.sum()
    for _ in range(5):
        changed = False
        if w[3] > cap226:
            excess = w[3] - cap226
            w[3] = cap226
            # Redistribute excess to K198, K204, K208, K232b by relative iv
            iv_others = np.array([iv198, iv204, iv208, iv232b])
            scale = iv_others / iv_others.sum()
            w[0] += scale[0] * excess
            w[1] += scale[1] * excess
            w[2] += scale[2] * excess
            w[4] += scale[3] * excess
            changed = True
        if w[4] > cap232b:
            excess = w[4] - cap232b
            w[4] = cap232b
            iv_others = np.array([iv198, iv204, iv208, iv226])
            scale = iv_others / iv_others.sum()
            w[0] += scale[0] * excess
            w[1] += scale[1] * excess
            w[2] += scale[2] * excess
            w[3] += scale[3] * excess
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
for i in range(n_ret):
    start_w = max(0, i - ROLL)
    seg_len = i - start_w
    v198  = np.std(ret198[start_w:i+1],  ddof=1) if seg_len >= 2 else 1e-6
    v204  = np.std(ret204[start_w:i+1],  ddof=1) if seg_len >= 2 else 1e-6
    v208  = np.std(ret208[start_w:i+1],  ddof=1) if seg_len >= 2 else 1e-6
    v226  = np.std(ret226[start_w:i+1],  ddof=1) if seg_len >= 2 else 1e-6
    v232b = np.std(ret232b[start_w:i+1], ddof=1) if seg_len >= 2 else 1e-6
    iv198  = 1.0 / max(v198,  1e-9)
    iv204  = 1.0 / max(v204,  1e-9)
    iv208  = 1.0 / max(v208,  1e-9)
    iv226  = 1.0 / max(v226,  1e-9)
    iv232b = 1.0 / max(v232b, 1e-9)
    wd = apply_two_caps_5(iv198, iv204, iv208, iv226, iv232b, CAP226_D, CAP232b_D)
    w_traj_d[i] = wd
    inv_vol_rets_d[i] = (wd[0]*ret198[i] + wd[1]*ret204[i] + wd[2]*ret208[i] +
                         wd[3]*ret226[i] + wd[4]*ret232b[i])

m = oos_metrics(inv_vol_rets_d)
m.update(wf_stats(inv_vol_rets_d))
m["description"]           = "Inv-vol (30d) + K226 cap 20% + K232b cap 10%"
m["avg_weights"]           = [round(float(w_traj_d[:,j].mean()), 4) for j in range(5)]
m["diversification_ratio"] = diversification_ratio(w_traj_d.mean(axis=0), rets_all)
variants["K234d"]     = m
variant_rets["K234d"] = inv_vol_rets_d
print(f"K234d: OOS Sh={m['oos_sharpe']:.4f}  MaxDD={m['oos_maxdd']:.6f}  "
      f"WF mean={m['wf_mean']:.4f}  WF min={m['wf_min']:.4f}  DR={m['diversification_ratio']:.4f}")
wts_d = m["avg_weights"]
print(f"       Avg wts: K198={wts_d[0]:.3f} K204={wts_d[1]:.3f} K208={wts_d[2]:.3f} "
      f"K226={wts_d[3]:.3f} K232b={wts_d[4]:.3f}")

# ── K234e: Inv-vol + K226 cap 20% + K232b cap 20% ────────────────────────────
print("\n--- K234e: Inv-vol + K226 cap 20% + K232b cap 20% ---")
CAP226_E  = 0.20
CAP232b_E = 0.20

inv_vol_rets_e = np.zeros(n_ret)
w_traj_e       = np.zeros((n_ret, 5))
for i in range(n_ret):
    start_w = max(0, i - ROLL)
    seg_len = i - start_w
    v198  = np.std(ret198[start_w:i+1],  ddof=1) if seg_len >= 2 else 1e-6
    v204  = np.std(ret204[start_w:i+1],  ddof=1) if seg_len >= 2 else 1e-6
    v208  = np.std(ret208[start_w:i+1],  ddof=1) if seg_len >= 2 else 1e-6
    v226  = np.std(ret226[start_w:i+1],  ddof=1) if seg_len >= 2 else 1e-6
    v232b = np.std(ret232b[start_w:i+1], ddof=1) if seg_len >= 2 else 1e-6
    iv198  = 1.0 / max(v198,  1e-9)
    iv204  = 1.0 / max(v204,  1e-9)
    iv208  = 1.0 / max(v208,  1e-9)
    iv226  = 1.0 / max(v226,  1e-9)
    iv232b = 1.0 / max(v232b, 1e-9)
    we = apply_two_caps_5(iv198, iv204, iv208, iv226, iv232b, CAP226_E, CAP232b_E)
    w_traj_e[i] = we
    inv_vol_rets_e[i] = (we[0]*ret198[i] + we[1]*ret204[i] + we[2]*ret208[i] +
                         we[3]*ret226[i] + we[4]*ret232b[i])

m = oos_metrics(inv_vol_rets_e)
m.update(wf_stats(inv_vol_rets_e))
m["description"]           = "Inv-vol (30d) + K226 cap 20% + K232b cap 20%"
m["avg_weights"]           = [round(float(w_traj_e[:,j].mean()), 4) for j in range(5)]
m["diversification_ratio"] = diversification_ratio(w_traj_e.mean(axis=0), rets_all)
variants["K234e"]     = m
variant_rets["K234e"] = inv_vol_rets_e
print(f"K234e: OOS Sh={m['oos_sharpe']:.4f}  MaxDD={m['oos_maxdd']:.6f}  "
      f"WF mean={m['wf_mean']:.4f}  WF min={m['wf_min']:.4f}  DR={m['diversification_ratio']:.4f}")
wts_e = m["avg_weights"]
print(f"       Avg wts: K198={wts_e[0]:.3f} K204={wts_e[1]:.3f} K208={wts_e[2]:.3f} "
      f"K226={wts_e[3]:.3f} K232b={wts_e[4]:.3f}")

# ── K234f: Minimum Variance Portfolio (rolling 60d covariance) ────────────────
print("\n--- K234f: MVP (rolling 60d covariance, long-only) ---")

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
            return np.array([0.20, 0.20, 0.20, 0.20, 0.20])
        return w_raw / s
    except np.linalg.LinAlgError:
        return np.array([0.20, 0.20, 0.20, 0.20, 0.20])

mvp_rets_f = np.zeros(n_ret)
w_traj_f   = np.zeros((n_ret, 5))
for i in range(n_ret):
    start_w = max(0, i - ROLL_MVP)
    seg = np.stack([
        ret198[start_w:i+1],
        ret204[start_w:i+1],
        ret208[start_w:i+1],
        ret226[start_w:i+1],
        ret232b[start_w:i+1],
    ], axis=0)
    if seg.shape[1] >= 5:
        cov = np.cov(seg)   # (5, 5)
        wf  = mvp_weights_5(cov)
    else:
        wf = np.array([0.20, 0.20, 0.20, 0.20, 0.20])
    w_traj_f[i] = wf
    mvp_rets_f[i] = (wf[0]*ret198[i] + wf[1]*ret204[i] + wf[2]*ret208[i] +
                     wf[3]*ret226[i] + wf[4]*ret232b[i])

m = oos_metrics(mvp_rets_f)
m.update(wf_stats(mvp_rets_f))
m["description"]           = "Minimum Variance Portfolio (rolling 60d covariance, long-only)"
m["avg_weights"]           = [round(float(w_traj_f[:,j].mean()), 4) for j in range(5)]
m["diversification_ratio"] = diversification_ratio(w_traj_f.mean(axis=0), rets_all)
variants["K234f"]     = m
variant_rets["K234f"] = mvp_rets_f
print(f"K234f: OOS Sh={m['oos_sharpe']:.4f}  MaxDD={m['oos_maxdd']:.6f}  "
      f"WF mean={m['wf_mean']:.4f}  WF min={m['wf_min']:.4f}  DR={m['diversification_ratio']:.4f}")
wts_f = m["avg_weights"]
print(f"       Avg wts: K198={wts_f[0]:.3f} K204={wts_f[1]:.3f} K208={wts_f[2]:.3f} "
      f"K226={wts_f[3]:.3f} K232b={wts_f[4]:.3f}")

# ─────────────────────────────────────────────────────────────────────────────
# 7. Acceptance gates vs K229 v6.8 (K229d)
# ─────────────────────────────────────────────────────────────────────────────
K229_OOS_SH  = 12.61
K229_WF_MIN  = 7.4435
K229_WF_MEAN = 11.425
K229_MAXDD   = -0.001201

GATE_K232b_FOLD2 = -1.0       # K232b ML fold 2 >= -1.0
GATE_OOS_SH      = K229_OOS_SH + 0.10   # > 12.71
GATE_WF_MIN      = K229_WF_MIN           # >= 7.44
GATE_MAXDD       = K229_MAXDD            # <= -0.0012

print(f"\n--- Acceptance Gates (vs K229 v6.8 K229d) ---")
print(f"Gate 0a: K232b ML window fold 2 >= {GATE_K232b_FOLD2:.1f} (was -2.15 ungated)")
print(f"Gate 1 : Best variant OOS Sh > {GATE_OOS_SH:.2f}")
print(f"Gate 2 : WF min >= {GATE_WF_MIN:.4f}")
print(f"Gate 3 : MaxDD <= {GATE_MAXDD:.6f}")
print(f"Gate 4 : All 5 portfolios non-zero weight (>1%)")

print(f"\nGate 0a (K232b ML fold 2): {k232b_fold2:.4f} -> {'PASS' if gate0_fold2_pass else 'FAIL (conditional)'}")
print(f"Gate 0b (K232b OOS Sh):    {k232b_ml_oos['oos_sharpe']:.4f} -> {'PASS' if gate0_oos_pass else 'FAIL'}")

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
# 8. Synergy analysis vs K229 v6.8
# ─────────────────────────────────────────────────────────────────────────────
print("\n--- Synergy Analysis ---")
sh198_oos  = baseline["K198"]["oos_sharpe"]
sh204_oos  = baseline["K204"]["oos_sharpe"]
sh208_oos  = baseline["K208"]["oos_sharpe"]
sh226_oos  = baseline["K226"]["oos_sharpe"]
sh232b_oos = baseline["K232b"]["oos_sharpe"]
avg_individual = (sh198_oos + sh204_oos + sh208_oos + sh226_oos + sh232b_oos) / 5.0
print(f"Individual OOS Sharpes: K198={sh198_oos:.4f}, K204={sh204_oos:.4f}, "
      f"K208={sh208_oos:.4f}, K226={sh226_oos:.4f}, K232b={sh232b_oos:.4f}")
print(f"Average of 5 individuals: {avg_individual:.4f}")

# Use best accepted or best any for reporting
best_vm_report    = best_vm   if best_vm   else max(variants.values(), key=lambda x: x["oos_sharpe"])
best_name_report  = best_name if best_name else max(variants.items(),  key=lambda x: x[1]["oos_sharpe"])[0]

synergy_sh      = best_vm_report["oos_sharpe"] - avg_individual
synergy_vs_k229 = best_vm_report["oos_sharpe"] - K229_OOS_SH
synergy_detected = synergy_sh > 0.02
print(f"Best ensemble ({best_name_report}): {best_vm_report['oos_sharpe']:.4f}")
print(f"Synergy vs avg individuals: {synergy_sh:+.4f} ({'GENUINE' if synergy_detected else 'WEAK'})")
print(f"Improvement vs K229 v6.8:   {synergy_vs_k229:+.4f}")
avg_wf_min_indiv = np.mean([baseline[n]["wf_min"] for n in ["K198","K204","K208","K226","K232b"]])
print(f"WF-min avg individuals: {avg_wf_min_indiv:.4f}  |  Best ensemble WF-min: {best_vm_report['wf_min']:.4f}")

# DR comparison
print(f"\nDiversification Ratio comparison:")
print(f"  K229d (prod): DR=1.6526")
print(f"  K234 {best_name_report}: DR={best_vm_report['diversification_ratio']:.4f}")

# ─────────────────────────────────────────────────────────────────────────────
# 9. Build equity curves for output
# ─────────────────────────────────────────────────────────────────────────────
# K229d reference: inv-vol + K226 cap 20% using K198/K204/K208/K226
# approximate using known avg weights from K229d: [0.0439, 0.0367, 0.9075, 0.012]
k229d_ref_ret = (
    0.0439 * ret198 + 0.0367 * ret204 + 0.9075 * ret208 + 0.012 * ret226
)

curves = {
    "K198":      equity_curve(ret198),
    "K204":      equity_curve(ret204),
    "K208":      equity_curve(ret208),
    "K226":      equity_curve(ret226),
    "K232b":     equity_curve(ret232b),
    "K234a":     equity_curve(variant_rets["K234a"]),
    "K234b":     equity_curve(variant_rets["K234b"]),
    "K234c":     equity_curve(variant_rets["K234c"]),
    "K234d":     equity_curve(variant_rets["K234d"]),
    "K234e":     equity_curve(variant_rets["K234e"]),
    "K234f":     equity_curve(variant_rets["K234f"]),
    "K229d_ref": equity_curve(k229d_ref_ret),
    "dates":     [dates_ml[0]] + list(ret_dates),
}

# ─────────────────────────────────────────────────────────────────────────────
# 10. Save JSON outputs
# ─────────────────────────────────────────────────────────────────────────────
runtime = round(time.time() - t0, 2)

if accepted:
    verdict = f"ACCEPT as K234 v6.9 — best variant: {best_name}"
elif not gate0_fold2_pass:
    verdict = (f"REJECT — K232b ML-window fold 2 (date-based) = {k232b_fold2:.4f} < gate {GATE_K232b_FOLD2:.1f} "
               f"(30% improvement from -2.1503 ungated; gate requires >= -1.0; K235 needs harder gate)")
else:
    verdict = "REJECT — no variant passes all acceptance gates vs K229 v6.8"

corr_mat_list = [[round(rho_matrix[i,j], 4) for j in range(5)] for i in range(5)]

# Per-variant fold breakdown
fold_breakdown = {vname: vm["fold_details"] for vname, vm in variants.items()}

synergy_block = {
    "individual_oos_sharpes": {
        "K198":  sh198_oos,
        "K204":  sh204_oos,
        "K208":  sh208_oos,
        "K226":  sh226_oos,
        "K232b": sh232b_oos,
    },
    "avg_individual_oos_sh":   round(avg_individual, 4),
    "best_ensemble_name":      best_name_report,
    "best_ensemble_oos_sh":    round(best_vm_report["oos_sharpe"], 4),
    "synergy_delta_vs_avg":    round(synergy_sh, 4),
    "synergy_delta_vs_k229":   round(synergy_vs_k229, 4),
    "synergy_detected":        synergy_detected,
    "avg_individual_wf_min":   round(float(avg_wf_min_indiv), 4),
    "best_ensemble_wf_min":    round(best_vm_report["wf_min"], 4),
    "k229d_dr":                1.6526,
    "best_k234_dr":            best_vm_report["diversification_ratio"],
}

# Historical comparison table
historical = {
    "K198_v6.5":  {"oos_sharpe": 10.28,  "oos_maxdd": -0.0053, "wf_mean": 7.91,  "wf_min": 6.57,   "components": 1},
    "K217_v6.6":  {"oos_sharpe": 10.43,  "oos_maxdd": -0.0053, "wf_mean": 8.01,  "wf_min": 6.91,   "components": 2},
    "K218e_v6.7": {"oos_sharpe": 11.031, "oos_maxdd": -0.0036, "wf_mean": 8.316, "wf_min": 6.9282, "components": 3},
    "K229d_v6.8": {"oos_sharpe": 12.61,  "oos_maxdd": -0.001201, "wf_mean": 11.425, "wf_min": 7.4435, "components": 4},
    "K231_REJECT":{"oos_sharpe": None,   "note": "K228 ungated fold 2=-2.15 drag", "components": 5},
    "K232b_fixed":{"oos_sharpe": 2.86,   "note": "K228 soft-gated, fold 2=-1.415 (30% improvement)", "components": 1},
}
for vname, vm in variants.items():
    historical[f"K234_{vname[-1]}"] = {
        "oos_sharpe":  vm["oos_sharpe"],
        "oos_maxdd":   vm["oos_maxdd"],
        "wf_mean":     vm["wf_mean"],
        "wf_min":      vm["wf_min"],
        "dr":          vm["diversification_ratio"],
        "components":  5,
        "avg_weights": vm["avg_weights"],
    }

result = {
    "wave":    "K234",
    "task":    "5-Way Meta-Ensemble: K198 x K204 x K208 x K226 x K232b (Gated K228)",
    "as_of":   datetime.now(timezone.utc).isoformat(),
    "runtime_s": runtime,
    "data_info": {
        "n_days":             n,
        "date_start":         dates_ml[0],
        "date_end":           dates_ml[-1],
        "n_returns":          n_ret,
        "k208_missing_days":  missing_k208,
        "k226_missing_days":  missing_k226,
        "k232b_missing_days": missing_k232b,
        "k232b_nonzero_days": int((np.abs(ret232b) > 1e-10).sum()),
        "k232b_sparsity_pct": round(float((np.abs(ret232b) > 1e-10).sum() / n_ret * 100), 1),
        "k232b_strategy":     "Regime-gated K228 stablecoin mint/burn (soft supply-trend gate)",
    },
    "k232b_ml_window_validation": {
        "description":              "K232b (gated K228) standalone on K229 ML window (448d) — Gate 0",
        "methodology_note":         "Fold boundaries: K232 calendar-date method (112d each), authoritative for Gate 0a. Index-based (111/111/111/114) used for ensemble variants.",
        "k228_ungated_ml_fold2":    -2.1503,
        "k232b_gated_ml_fold2":     k232b_fold2,
        "fold2_improvement_pct":    round((k232b_fold2 - (-2.1503)) / abs(-2.1503) * 100, 1),
        "gate_fold2_threshold":     GATE_K232b_FOLD2,
        "gate_fold2_pass":          gate0_fold2_pass,
        "k232b_ml_window_oos_sh":   k232b_ml_oos["oos_sharpe"],
        "k232b_ml_window_oos_maxdd":k232b_ml_oos["oos_maxdd"],
        "k232b_ml_window_oos_n_days":k232b_ml_oos["oos_n_days"],
        "k232b_ml_window_wf_folds_date_based":  k232b_date_fold_sharpes,
        "k232b_ml_window_wf_folds_index_based": k232b_ml_wf["fold_sharpes"],
        "k232b_ml_window_wf_fold_details":      k232b_date_fold_details,
        "k232b_ml_window_wf_min_date_based":    round(min(k232b_date_fold_sharpes), 4),
        "k232b_ml_window_wf_mean_date_based":   round(float(np.mean(k232b_date_fold_sharpes)), 4),
        "k232b_ml_window_wf_min_index":         k232b_ml_wf["wf_min"],
        "gate_oos_pass":            gate0_oos_pass,
        "gate0_combined_pass":      gate0_pass,
        "k231_reference":           "K231 REJECT: K228 ungated ML fold 2 = -2.15 caused WF drag",
        "k232b_standalone_oos_sh":  2.86,
        "k232b_standalone_window":  "730d own window (2024-05-23 to 2026-05-22)",
        "k232b_verdict":            "PASS" if gate0_fold2_pass else "CONDITIONAL FAIL",
        "note":                     ("Fold 2 (date-based) = -1.415 (improved 30% from -2.15 ungated, gate -1.0). "
                                     "Gate 0a fails; ensemble capped variants may still pass.") if not gate0_fold2_pass else (
                                     "Fold 2 gate passed — proceed with full ensemble."),
    },
    "correlation_matrix": {
        "labels": labels,
        "matrix": corr_mat_list,
        "pairwise": {
            "rho_198_204":  round(rho_198_204,  4),
            "rho_198_208":  round(rho_198_208,  4),
            "rho_198_226":  round(rho_198_226,  4),
            "rho_198_232b": round(rho_198_232b, 4),
            "rho_204_208":  round(rho_204_208,  4),
            "rho_204_226":  round(rho_204_226,  4),
            "rho_204_232b": round(rho_204_232b, 4),
            "rho_208_226":  round(rho_208_226,  4),
            "rho_208_232b": round(rho_208_232b, 4),
            "rho_226_232b": round(rho_226_232b, 4),
        },
        "interpretation": {
            "rho_198_204":  corr_interp(rho_198_204),
            "rho_198_208":  corr_interp(rho_198_208),
            "rho_198_226":  corr_interp(rho_198_226),
            "rho_198_232b": corr_interp(rho_198_232b),
            "rho_204_208":  corr_interp(rho_204_208),
            "rho_204_226":  corr_interp(rho_204_226),
            "rho_204_232b": corr_interp(rho_204_232b),
            "rho_208_226":  corr_interp(rho_208_226),
            "rho_208_232b": corr_interp(rho_208_232b),
            "rho_226_232b": corr_interp(rho_226_232b),
        },
    },
    "acceptance_gates": {
        "gate0a_k232b_fold2_threshold": GATE_K232b_FOLD2,
        "gate0a_result":              "PASS" if gate0_fold2_pass else "FAIL",
        "gate1_oos_sharpe_threshold": GATE_OOS_SH,
        "gate2_wf_min_threshold":     GATE_WF_MIN,
        "gate3_maxdd_threshold":      GATE_MAXDD,
        "gate4_min_weight":           0.01,
        "reference":                  "K229d v6.8",
        "gate0_combined":             "PASS" if gate0_pass else "FAIL",
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

with open("/Users/nekonaomichi/crypto-lab/wave_k234_5way_gated.json", "w") as f:
    json.dump(result, f, indent=2)
print("\nSaved: wave_k234_5way_gated.json")

with open("/Users/nekonaomichi/crypto-lab/wave_k234_curves.json", "w") as f:
    json.dump(curves, f)
print("Saved: wave_k234_curves.json")

print(f"\nRuntime: {runtime}s")
print(f"\nVERDICT: {verdict}")

# ─────────────────────────────────────────────────────────────────────────────
# 11. Generate Markdown report
# ─────────────────────────────────────────────────────────────────────────────
k232b_val = result["k232b_ml_window_validation"]
rho       = result["correlation_matrix"]["pairwise"]

report_lines = [
    "# Wave K234 — 5-Way Meta-Ensemble Report (K198 × K204 × K208 × K226 × K232b)",
    f"*Generated: {result['as_of']}  |  Runtime: {runtime}s*",
    "",
    "## Executive Summary",
    "",
]

if accepted:
    report_lines += [
        f"**VERDICT: ACCEPT as K234 v6.9** — Best variant: {best_name}",
        "",
        f"| Metric | K229d v6.8 (prod) | {best_name} | Delta |",
        "|--------|-------------------|-----------|-------|",
        f"| OOS Sharpe | {K229_OOS_SH:.4f} | {best_vm['oos_sharpe']:.4f} | {best_vm['oos_sharpe']-K229_OOS_SH:+.4f} |",
        f"| OOS MaxDD  | {K229_MAXDD:.6f} | {best_vm['oos_maxdd']:.6f} | {best_vm['oos_maxdd']-K229_MAXDD:+.6f} |",
        f"| WF Mean    | {K229_WF_MEAN:.4f} | {best_vm['wf_mean']:.4f} | {best_vm['wf_mean']-K229_WF_MEAN:+.4f} |",
        f"| WF Min     | {K229_WF_MIN:.4f} | {best_vm['wf_min']:.4f} | {best_vm['wf_min']-K229_WF_MIN:+.4f} |",
        f"| DR         | 1.6526 | {best_vm['diversification_ratio']:.4f} | {best_vm['diversification_ratio']-1.6526:+.4f} |",
        "",
    ]
else:
    best_any = max(variants.items(), key=lambda x: x[1]["oos_sharpe"])
    report_lines += [
        f"**VERDICT: REJECT** — No variant passes all acceptance gates vs K229d v6.8.",
        "",
        f"Best attempted: {best_any[0]} with OOS Sh={best_any[1]['oos_sharpe']:.4f}",
        "",
        "**Root cause:** K232b ML-window fold 2 = "
        f"{k232b_fold2:.4f} (gate requires >= -1.0; ungated K228 was -2.15 [-31% improved but insufficient])",
        "",
    ]

report_lines += [
    "---",
    "",
    "## 1. K232b ML-Window Validation (CRITICAL CHECK — Gate 0)",
    "",
    "**Context:**",
    "- K231 REJECT: K229 + K228 (ungated) failed because K228 ML fold 2 = -2.15 caused WF drag",
    "- K232b FIX: Soft regime gate on supply trend (z-score < -1.0 = contraction → K228 inactive)",
    "- K232b standalone: OOS Sh 2.86, own-window all WF folds positive (min +0.56)",
    "- Gate 0a: K232b ML fold 2 >= -1.0 (30% improvement milestone)",
    "",
    f"| Metric | K228 Ungated (K231) | K232b Gated | Gate | Result |",
    f"|--------|---------------------|-------------|------|--------|",
    f"| ML fold 2 Sh (date-based) | -2.1503 | {k232b_fold2:.4f} | >= -1.0 | {'PASS' if gate0_fold2_pass else 'FAIL'} |",
    f"| Improvement  | baseline | {k232b_val['fold2_improvement_pct']:+.1f}% | >= 30% | {'PASS' if k232b_val['fold2_improvement_pct'] >= 30 else 'FAIL'} |",
    f"| ML OOS Sh    | 2.1641 | {k232b_ml_oos['oos_sharpe']:.4f} | >= 1.0 | {'PASS' if gate0_oos_pass else 'FAIL'} |",
    f"| ML WF folds (date-based) | [1.23, -2.15, 3.03, 2.49] | {k232b_date_fold_sharpes} | — | — |",
    f"| ML WF folds (index-based)| [1.23, -2.15, 3.03, 2.49] | {k232b_ml_wf['fold_sharpes']} | — | — |",
    "",
    f"**Gate 0 result: {'PASS' if gate0_pass else 'CONDITIONAL FAIL'} — "
    f"fold 2 = {k232b_fold2:.4f} {'passes' if gate0_fold2_pass else 'still below'} -1.0 threshold**",
    "",
    f"Fold 2 corresponds to 2025-05-14 to 2025-09-02 (stablecoin contraction regime).",
    "The soft gate reduced impact but did not fully neutralize the contraction-period drag.",
    "",
    "---",
    "",
    "## 2. Data & Methodology",
    "",
    f"- **Date range**: {dates_ml[0]} -> {dates_ml[-1]} ({n} days)",
    f"- **Return series**: {n_ret} daily observations",
    f"- **K208 daily aggregation**: 8h->daily by last candle of each UTC day; {missing_k208} days filled forward",
    f"- **K226 alignment**: ETH validator queue/LST flow strategy mapped to ML window; {missing_k226} days filled forward",
    f"- **K232b alignment**: Regime-gated K228 equity curve mapped to ML window; {missing_k232b} days filled forward",
    f"- **K232b active days**: {result['data_info']['k232b_nonzero_days']} / {n_ret} ({result['data_info']['k232b_sparsity_pct']}%)",
    "- **K198**: Ridge ML allocator (equity_ridge from wave_k198_curves.json)",
    "- **K204**: ML DD-embed full ensemble (equity_k204 from wave_k204_curves.json)",
    "- **K208**: DAR(2,1)-filtered reverse carry panel (K208_filtered, daily-resampled)",
    "- **K226**: ETH Validator Queue / LST Staking Flow contrarian (wave_k226_curves.json)",
    "- **K232b**: K228 Stablecoin Mint/Burn with soft supply-trend regime gate (wave_k232_curves.json)",
    "- **OOS window**: final 30% of return series (~135 days)",
    "- **Walk-forward**: 4-fold chronological splits",
    "",
    "---",
    "",
    "## 3. 5x5 Correlation Matrix",
    "",
    "| | K198 | K204 | K208 | K226 | K232b |",
    "|---|------|------|------|------|-------|",
    f"| **K198**  | 1.0000 | {rho['rho_198_204']:.4f} | {rho['rho_198_208']:.4f} | {rho['rho_198_226']:.4f} | {rho['rho_198_232b']:.4f} |",
    f"| **K204**  | {rho['rho_198_204']:.4f} | 1.0000 | {rho['rho_204_208']:.4f} | {rho['rho_204_226']:.4f} | {rho['rho_204_232b']:.4f} |",
    f"| **K208**  | {rho['rho_198_208']:.4f} | {rho['rho_204_208']:.4f} | 1.0000 | {rho['rho_208_226']:.4f} | {rho['rho_208_232b']:.4f} |",
    f"| **K226**  | {rho['rho_198_226']:.4f} | {rho['rho_204_226']:.4f} | {rho['rho_208_226']:.4f} | 1.0000 | {rho['rho_226_232b']:.4f} |",
    f"| **K232b** | {rho['rho_198_232b']:.4f} | {rho['rho_204_232b']:.4f} | {rho['rho_208_232b']:.4f} | {rho['rho_226_232b']:.4f} | 1.0000 |",
    "",
    "**Interpretation (K232b correlations):**",
    f"- K232b vs K198: rho={rho['rho_198_232b']:.4f} ({corr_interp(rho_198_232b)}) — stablecoin mint vs ML allocator",
    f"- K232b vs K204: rho={rho['rho_204_232b']:.4f} ({corr_interp(rho_204_232b)}) — stablecoin mint vs ML DD-embed",
    f"- K232b vs K208: rho={rho['rho_208_232b']:.4f} ({corr_interp(rho_208_232b)}) — stablecoin mint vs reverse carry",
    f"- K232b vs K226: rho={rho['rho_226_232b']:.4f} ({corr_interp(rho_226_232b)}) — stablecoin mint vs ETH staking flow",
    f"- K198 vs K204: rho={rho['rho_198_204']:.4f} ({corr_interp(rho_198_204)}) — established core pair (unchanged from K229)",
    "",
    "---",
    "",
    "## 4. Baseline Performance (Standalone on ML Window)",
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
    "## 5. Variant Results",
    "",
    "### 5.1 Per-Variant Summary",
    "",
    "| Variant | Description | OOS Sh | OOS MaxDD | WF Mean | WF Min | DR | K198/K204/K208/K226/K232b wts | Gates |",
    "|---------|-------------|--------|-----------|---------|--------|----|-------------------------------|-------|",
]
for vname, vm in variants.items():
    wts = vm["avg_weights"]
    gate_sh = "v" if vm["oos_sharpe"] > GATE_OOS_SH else "x"
    gate_wf = "v" if vm["wf_min"] >= GATE_WF_MIN else "x"
    gate_dd = "v" if vm["oos_maxdd"] >= GATE_MAXDD else "x"
    report_lines.append(
        f"| {vname} | {vm['description'][:32]} | {vm['oos_sharpe']:.4f} | "
        f"{vm['oos_maxdd']:.6f} | {vm['wf_mean']:.4f} | {vm['wf_min']:.4f} | "
        f"{vm['diversification_ratio']:.4f} | {wts[0]:.2f}/{wts[1]:.2f}/{wts[2]:.2f}/{wts[3]:.2f}/{wts[4]:.2f} | "
        f"{gate_sh}/{gate_wf}/{gate_dd} |"
    )

report_lines += [
    "",
    "Gates order: [OOS Sh > 12.71] / [WF min >= 7.44] / [MaxDD <= -0.0012]",
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
    "## 6. Historical Comparison (Production Progression)",
    "",
    "| Version | OOS Sh | OOS MaxDD | WF Mean | WF Min | Components | Note |",
    "|---------|--------|-----------|---------|--------|------------|------|",
    f"| K198 v6.5 | 10.2800 | -0.005300 | 7.9100 | 6.5700 | 1 | Baseline ML |",
    f"| K217 v6.6 | 10.4300 | -0.005300 | 8.0100 | 6.9100 | 2 | +K208 reverse carry |",
    f"| K218e v6.7 | 11.0310 | -0.003640 | 8.3160 | 6.9282 | 3 | 3-way meta |",
    f"| K229d v6.8 | {K229_OOS_SH:.4f} | {K229_MAXDD:.6f} | {K229_WF_MEAN:.4f} | {K229_WF_MIN:.4f} | 4 | +K226 ETH validator |",
    f"| K231 REJECT | — | — | — | — | 5 | K228 ungated fold 2=-2.15 |",
    f"| K232b fix | 2.86 | — | — | — | 1 | K228 soft-gated fold 2=-1.415 |",
]
for vname, vm in variants.items():
    wts = vm["avg_weights"]
    all_gates = (vm["oos_sharpe"] > GATE_OOS_SH and
                 vm["wf_min"] >= GATE_WF_MIN and
                 vm["oos_maxdd"] >= GATE_MAXDD and
                 min(wts) > 0.01 and gate0_pass)
    note = "ACCEPTED" if all_gates else ("best" if vname == best_name_report else "")
    report_lines.append(
        f"| K234 {vname[-1]} | {vm['oos_sharpe']:.4f} | {vm['oos_maxdd']:.6f} | "
        f"{vm['wf_mean']:.4f} | {vm['wf_min']:.4f} | 5 | {note} |"
    )

report_lines += [
    "",
    f"**Acceptance gate**: OOS Sh > {GATE_OOS_SH:.2f} | WF Min >= {GATE_WF_MIN:.4f} | MaxDD <= {GATE_MAXDD:.6f} | All weights > 1%",
    "",
    "---",
    "",
    "## 7. Synergy Analysis & DR Comparison",
    "",
    f"- Individual OOS Sharpes (ML window): K198={sh198_oos:.4f}, K204={sh204_oos:.4f}, K208={sh208_oos:.4f}, K226={sh226_oos:.4f}, K232b={sh232b_oos:.4f}",
    f"- Average of 5 individuals OOS Sh: {avg_individual:.4f}",
    f"- Best ensemble ({best_name_report}) OOS Sh: {best_vm_report['oos_sharpe']:.4f}",
    f"- Synergy vs avg individuals: {synergy_sh:+.4f} ({'GENUINE (>0.02)' if synergy_detected else 'WEAK/NONE (<0.02)'})",
    f"- Improvement vs K229 v6.8: {synergy_vs_k229:+.4f}",
    f"- Diversification Ratio — K229d: 1.6526  |  K234 {best_name_report}: {best_vm_report['diversification_ratio']:.4f}",
    "",
    f"**K232b orthogonality vs core ensemble:**",
    f"- K232b vs K198: rho={rho['rho_198_232b']:.4f} ({corr_interp(rho_198_232b)}) — orthogonal if |rho| < 0.3",
    f"- K232b vs K226: rho={rho['rho_226_232b']:.4f} ({corr_interp(rho_226_232b)}) — mild co-movement (both on-chain flow signals)",
    f"- K232b vs K208: rho={rho['rho_208_232b']:.4f} ({corr_interp(rho_208_232b)}) — carry vs stablecoin (structural independence)",
    "",
    "---",
    "",
    "## 8. Risk Analysis",
    "",
    "### K232b-Specific Risks",
    "- **Regime gate effectiveness**: soft gate (-1.415 fold 2) shows 30% improvement but not full remediation",
    "- **Stablecoin data dependency**: requires reliable supply data (DeFiLlama/Coinglass); outage = stale signal",
    "- **Contraction regime**: K232b signal reversal risk during rapid USDT/USDC contraction periods",
    "- **Sparsity**: K232b only active ~17% of days — inv-vol may assign disproportionate weight on active days",
    "",
    "### Ensemble-Level Risks",
    "- **K208 dominance**: inv-vol still likely assigns 80-90% to K208 (ultra-low vol); capped variants mitigate",
    "- **Gate 0a failure implication**: if fold 2 gate fails, K234 cannot be accepted even with good ensemble metrics",
    "- **Window boundary**: ML window ends 2026-04-14; any regime shift post-boundary not captured",
    "",
    "---",
    "",
    "## 9. Verdict, K234 v6.9 if Accepted; K235 Next Steps",
    "",
]

if accepted:
    report_lines += [
        f"### ACCEPT -> K234 v6.9 (Best variant: {best_name})",
        "",
        f"The 5-way meta-ensemble ({best_name}: {best_vm['description']}) passes all acceptance gates:",
        f"- Gate 0a (K232b fold 2): {k232b_fold2:.4f} >= -1.0 -> PASS",
        f"- Gate 1 (OOS Sh): {best_vm['oos_sharpe']:.4f} > {GATE_OOS_SH:.2f} -> PASS",
        f"- Gate 2 (WF Min): {best_vm['wf_min']:.4f} >= {GATE_WF_MIN:.4f} -> PASS",
        f"- Gate 3 (MaxDD): {best_vm['oos_maxdd']:.6f} <= {GATE_MAXDD:.6f} -> PASS",
        f"- Gate 4 (All weights > 1%): min={min(best_vm['avg_weights']):.3f} -> PASS",
        "",
        "**Deployment Plan:**",
        f"1. Promote K234 ({best_name}) to v6.9 production",
        "2. Components: K198 Ridge ML + K204 ML DD-embed + K208 DAR reverse carry + K226 ETH validator queue + K232b Gated K228",
        f"3. Allocator: {best_vm['description']}",
        "4. Monitor K232b regime gate monthly; if fold 2 < -1.5 for 30d, increase gate stringency",
        "5. Rebalance monthly if weights drift >15% from avg",
        "",
        "**K235 Next Steps:**",
        "1. Strengthen K232b regime gate (stricter threshold e.g. z < -1.5) to fully remediate fold 2",
        "2. On-chain native signal: OP/ARB bridge flow or Jito MEV capture rate",
        "3. Hash ribbon or miner capitulation signal integration",
        "4. CVaR-optimised allocation to reduce tail risk across 5-way ensemble",
        "5. Production monitoring: per-strategy daily PnL + weight trajectory dashboard",
    ]
else:
    report_lines += [
        "### REJECT — Maintain K229d v6.8 as Production",
        "",
        "No K234 variant improves on K229d v6.8 across all gates simultaneously.",
        "",
        "**Failure Analysis:**",
    ]
    if not gate0_fold2_pass:
        report_lines += [
            f"- **Gate 0a FAIL**: K232b ML fold 2 = {k232b_fold2:.4f} < threshold {GATE_K232b_FOLD2:.1f}",
            f"  - K231 ungated: -2.1503  ->  K232b gated: {k232b_fold2:.4f}  (improvement: {k232b_val['fold2_improvement_pct']:+.1f}%)",
            "  - Soft gate partially effective but fold 2 period (2025-05-14 to 2025-09-02) remains negative",
            "  - Implication: harder gate needed (e.g. supply_z < -1.5 or rolling 90d trend crossover)",
            "",
        ]
    for vname, vm in variants.items():
        sh_pass = vm["oos_sharpe"] > GATE_OOS_SH
        wf_pass = vm["wf_min"] >= GATE_WF_MIN
        dd_pass = vm["oos_maxdd"] >= GATE_MAXDD
        wt_pass = min(vm["avg_weights"]) > 0.01
        failures = []
        if not gate0_fold2_pass: failures.append(f"Gate 0a K232b fold 2 FAIL ({k232b_fold2:.4f}<-1.0)")
        if not sh_pass:          failures.append(f"OOS Sh {vm['oos_sharpe']:.4f} < {GATE_OOS_SH:.2f}")
        if not wf_pass:          failures.append(f"WF Min {vm['wf_min']:.4f} < {GATE_WF_MIN:.4f}")
        if not dd_pass:          failures.append(f"MaxDD {vm['oos_maxdd']:.6f} > {GATE_MAXDD:.6f}")
        if not wt_pass:          failures.append(f"Min weight {min(vm['avg_weights']):.3f} < 0.01")
        status = "PASS" if not failures else "FAIL: " + "; ".join(failures)
        report_lines.append(f"- **{vname}**: {status}")

    report_lines += [
        "",
        "**K235 Next Steps:**",
        "1. K233/K235: Harder K228 regime gate — supply_z < -1.5 (vs -1.0 soft gate in K232b)",
        "   Goal: fully eliminate fold 2 drag to achieve fold 2 >= 0.0",
        "2. Alternative 5th signal: OP/ARB bridge flow, Jito MEV, or hash ribbon (non-stablecoin)",
        "3. Investigate K232b fold 2 root cause: 2025-07/08 stablecoin contraction → specific dates",
        "4. Portfolio-level regime gate: suspend K232b at ensemble level during broad crypto contraction",
        "5. Return to K229d v6.8 as stable production — WF min 7.44 remains excellent",
    ]

report_lines += [
    "",
    "---",
    f"*Wave K234 | crypto-lab | {result['as_of']}*",
]

report_text = "\n".join(report_lines)
with open("/Users/nekonaomichi/crypto-lab/wave_k234_5way_gated.md", "w") as f:
    f.write(report_text)
print("Saved: wave_k234_5way_gated.md")

print(f"\n{'='*70}")
print(f"K234 COMPLETE — Runtime {runtime}s")
print(f"VERDICT: {verdict}")
print(f"{'='*70}")

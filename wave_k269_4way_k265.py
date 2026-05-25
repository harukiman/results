"""
Wave K269: K246a + K265 4-way Meta-Ensemble
K246a (K198+K208+K226) + K265 HL LongTail FR → v6.10 candidate
Gate 0: K265 ML window validation (K246a window: 2025-01-22 to 2026-04-14, 448 days)
"""

import json
import numpy as np
from datetime import datetime, date
import time

START = time.time()

# ─── Load curves ──────────────────────────────────────────────────────────────

with open("/Users/nekonaomichi/crypto-lab/wave_k246_curves.json") as f:
    d246 = json.load(f)

with open("/Users/nekonaomichi/crypto-lab/wave_k265_curves.json") as f:
    d265 = json.load(f)

with open("/Users/nekonaomichi/crypto-lab/wave_k265_hl_longtail_fr.json") as f:
    m265 = json.load(f)

with open("/Users/nekonaomichi/crypto-lab/wave_k246_k198_k204_contribution.json") as f:
    m246 = json.load(f)

# ─── K246a window ─────────────────────────────────────────────────────────────
WIN_DATES = d246["dates"]           # 448 dates: 2025-01-22 → 2026-04-14
WIN_SET   = set(WIN_DATES)
WIN_START = WIN_DATES[0]
WIN_END   = WIN_DATES[-1]
N_WIN     = len(WIN_DATES)          # 448

# Individual equity curves on K246a window (already aligned)
pnl_k198 = np.diff(np.array(d246["K198"]), prepend=d246["K198"][0])
pnl_k198 = np.array(d246["K198"])  # equity, convert to pnl below
eq_k198  = np.array(d246["K198"])
eq_k208  = np.array(d246["K208"])
eq_k226  = np.array(d246["K226"])

def eq_to_pnl(eq):
    """Daily PnL from equity curve (relative, day-over-day)."""
    r = np.diff(np.log(eq))
    return np.concatenate([[0.0], r])

pnl_k198 = eq_to_pnl(eq_k198)
pnl_k208 = eq_to_pnl(eq_k208)
pnl_k226 = eq_to_pnl(eq_k226)

# ─── K265 on K246a window ─────────────────────────────────────────────────────
k265_dates  = d265["dates"]   # 733 dates
k265_equity = np.array(d265["equity"])
k265_pnl_full = eq_to_pnl(k265_equity)

# Slice to K246a window
k265_date_to_idx = {d: i for i, d in enumerate(k265_dates)}
win_k265_mask = [k265_date_to_idx[d] for d in WIN_DATES if d in k265_date_to_idx]
missing = [d for d in WIN_DATES if d not in k265_date_to_idx]

if len(missing) > 0:
    print(f"WARNING: {len(missing)} K246a window dates missing from K265")

pnl_k265_win = np.array([k265_pnl_full[i] for i in win_k265_mask])
eq_k265_win  = np.exp(np.cumsum(pnl_k265_win))
eq_k265_win  = eq_k265_win / eq_k265_win[0]  # normalize to 1

print(f"K265 window slice: {len(pnl_k265_win)} days (expected 448)")


# ─── Metrics helpers ──────────────────────────────────────────────────────────
TRADING_DAYS = 252

def sharpe(pnl, ann=TRADING_DAYS):
    pnl = np.array(pnl)
    mu  = np.mean(pnl) * ann
    sd  = np.std(pnl, ddof=1) * np.sqrt(ann)
    return mu / sd if sd > 1e-12 else 0.0

def maxdd(eq):
    eq = np.array(eq)
    running_max = np.maximum.accumulate(eq)
    dd = (eq - running_max) / running_max
    return float(np.min(dd))

def ann_ret(eq, ann=TRADING_DAYS):
    total = eq[-1] / eq[0] - 1
    n = len(eq)
    return (1 + total) ** (ann / n) - 1

def ann_vol(pnl, ann=TRADING_DAYS):
    return float(np.std(pnl, ddof=1) * np.sqrt(ann))

def metrics(pnl_arr, label=""):
    pnl = np.array(pnl_arr)
    eq  = np.exp(np.cumsum(pnl))
    eq  = eq / eq[0]
    sh  = sharpe(pnl)
    md  = maxdd(eq)
    ar  = ann_ret(eq)
    av  = ann_vol(pnl)
    wr  = float(np.mean(pnl > 0))
    return {"sharpe": round(sh,4), "max_dd": round(md,6),
            "ann_ret": round(ar,6), "ann_vol": round(av,6),
            "win_rate": round(wr,6), "n_days": len(pnl)}


# ─── GATE 0: K265 ML window validation ───────────────────────────────────────
print("\n=== GATE 0: K265 on K246a ML window ===")
gate0_full = metrics(pnl_k265_win)
print(f"  Full window Sharpe: {gate0_full['sharpe']:.4f}  MaxDD: {gate0_full['max_dd']:.6f}")

# WF 4-fold on K246a window (same fold structure as K246)
N_FOLDS   = 4
fold_size = N_WIN // N_FOLDS
gate0_folds = []
for fi in range(N_FOLDS):
    s = fi * fold_size
    e = (fi+1)*fold_size if fi < N_FOLDS-1 else N_WIN
    fp = pnl_k265_win[s:e]
    feq = np.exp(np.cumsum(fp))
    fm  = metrics(fp)
    gate0_folds.append({
        "fold": fi+1,
        "start_date": WIN_DATES[s],
        "end_date": WIN_DATES[e-1],
        "n_days": e-s,
        **fm
    })
    print(f"  Fold {fi+1}: [{WIN_DATES[s]} → {WIN_DATES[e-1]}] Sh={fm['sharpe']:.4f}  MaxDD={fm['max_dd']:.6f}")

gate0_sharpes = [f["sharpe"] for f in gate0_folds]
gate0_all_pos = all(s > 0 for s in gate0_sharpes)
gate0_min_sh  = min(gate0_sharpes)
print(f"  WF min Sh: {gate0_min_sh:.4f}  all_positive: {gate0_all_pos}")
gate0_pass = gate0_all_pos
print(f"  GATE 0 PASS: {gate0_pass}")


# ─── 4x4 Correlation matrix ───────────────────────────────────────────────────
print("\n=== 4x4 Correlation matrix (K246a window) ===")
strategies = ["K198", "K208", "K226", "K265"]
pnls_win   = [pnl_k198, pnl_k208, pnl_k226, pnl_k265_win]
corr_matrix = {}
for i, si in enumerate(strategies):
    corr_matrix[si] = {}
    for j, sj in enumerate(strategies):
        c = float(np.corrcoef(pnls_win[i], pnls_win[j])[0,1])
        corr_matrix[si][sj] = round(c, 4)
    print(f"  {si}: " + "  ".join(f"{strategies[j]}={corr_matrix[si][strategies[j]]:+.4f}" for j in range(4)))


# ─── Meta-allocator helpers ───────────────────────────────────────────────────

def inv_vol_weights(pnl_list, caps=None):
    """Inverse-vol weights. caps = dict {idx: max_weight}."""
    vols = np.array([np.std(p, ddof=1) for p in pnl_list])
    vols = np.where(vols < 1e-12, 1e-12, vols)
    w = 1.0 / vols
    w = w / w.sum()
    if caps:
        # iterative capping
        for _ in range(50):
            changed = False
            for idx, cap in caps.items():
                if w[idx] > cap:
                    excess = w[idx] - cap
                    w[idx] = cap
                    others = [k for k in range(len(w)) if k != idx]
                    w[others] += excess * (w[others] / w[others].sum())
                    changed = True
            if not changed:
                break
    return w / w.sum()

def mvp_weights(pnl_list):
    """Minimum variance portfolio (closed-form)."""
    mat = np.vstack(pnl_list).T  # T x N
    cov = np.cov(mat.T)
    n   = len(pnl_list)
    ones= np.ones(n)
    try:
        inv = np.linalg.inv(cov + 1e-10*np.eye(n))
    except np.linalg.LinAlgError:
        return np.ones(n)/n
    w = inv @ ones
    return w / w.sum()

def portfolio_pnl(pnls, weights):
    """Weighted sum of pnls."""
    return sum(w * np.array(p) for w, p in zip(weights, pnls))


# ─── Define 6 variants ────────────────────────────────────────────────────────
# Indices: 0=K198, 1=K208, 2=K226, 3=K265

def make_variants(pnl_list):
    variants = {}

    # K269a: Inv-vol + K226 cap 20% + K265 cap 20% (K246a methodology extended)
    wa = inv_vol_weights(pnl_list, caps={2: 0.20, 3: 0.20})
    variants["K269a"] = wa

    # K269b: Inv-vol uncapped
    wb = inv_vol_weights(pnl_list, caps=None)
    variants["K269b"] = wb

    # K269c: K269a + K265 cap 25%
    wc = inv_vol_weights(pnl_list, caps={2: 0.20, 3: 0.25})
    variants["K269c"] = wc

    # K269d: K269a + K265 cap 30%
    wd = inv_vol_weights(pnl_list, caps={2: 0.20, 3: 0.30})
    variants["K269d"] = wd

    # K269e: Equal weight 25/25/25/25
    we = np.array([0.25, 0.25, 0.25, 0.25])
    variants["K269e"] = we

    # K269f: MVP
    wf = mvp_weights(pnl_list)
    variants["K269f"] = wf

    return variants


# ─── Walk-forward 4-fold evaluation ──────────────────────────────────────────
print("\n=== Walk-forward 4-fold evaluation ===")

all_pnls_win = [pnl_k198, pnl_k208, pnl_k226, pnl_k265_win]
variant_results = {}

for vname, w_full in make_variants(all_pnls_win).items():
    fold_metrics_list = []
    for fi in range(N_FOLDS):
        s  = fi * fold_size
        e  = (fi+1)*fold_size if fi < N_FOLDS-1 else N_WIN
        fp = [p[s:e] for p in all_pnls_win]
        # Recompute weights on IN-SAMPLE (all folds except current)
        is_mask = list(range(0, s)) + list(range(e, N_WIN))
        pnl_is  = [p[is_mask] for p in all_pnls_win]
        w_fold  = make_variants(pnl_is)[vname]
        pp      = portfolio_pnl(fp, w_fold)
        fm      = metrics(pp)
        fm["fold"]       = fi+1
        fm["start_date"] = WIN_DATES[s]
        fm["end_date"]   = WIN_DATES[e-1]
        fm["weights"]    = [round(float(x), 4) for x in w_fold]
        fold_metrics_list.append(fm)

    fold_sharpes = [f["sharpe"] for f in fold_metrics_list]
    wf_min       = min(fold_sharpes)
    wf_mean      = float(np.mean(fold_sharpes))
    all_pos      = all(s > 0 for s in fold_sharpes)

    # Full-window OOS Sharpe: weights from full IS → OOS slice
    # Use last 20% as "pseudo OOS" for ensemble (same as K246a approach: last 135 days)
    # K246a OOS = last 135 of 448 window
    OOS_DAYS = 135
    oos_s    = N_WIN - OOS_DAYS
    pnl_is_oos = [p[:oos_s] for p in all_pnls_win]
    w_oos    = make_variants(pnl_is_oos)[vname]
    pnl_oos  = portfolio_pnl([p[oos_s:] for p in all_pnls_win], w_oos)
    oos_m    = metrics(pnl_oos)
    oos_sh   = oos_m["sharpe"]
    oos_mdd  = oos_m["max_dd"]

    non_zero = all(float(w) > 0.001 for w in w_oos)

    variant_results[vname] = {
        "oos_sharpe":   round(oos_sh, 4),
        "oos_maxdd":    round(oos_mdd, 6),
        "oos_ann_ret":  oos_m["ann_ret"],
        "oos_ann_vol":  oos_m["ann_vol"],
        "wf_mean":      round(wf_mean, 4),
        "wf_min":       round(wf_min, 4),
        "wf_all_pos":   all_pos,
        "non_zero_weights": non_zero,
        "weights_oos":  [round(float(x), 4) for x in w_oos],
        "fold_details": fold_metrics_list,
    }

    print(f"  {vname}: OOS_Sh={oos_sh:.4f}  WF_min={wf_min:.4f}  OOS_MDD={oos_mdd:.6f}  "
          f"w={[round(float(x),3) for x in w_oos]}  allpos={all_pos}  nonzero={non_zero}")


# ─── Gate evaluation ─────────────────────────────────────────────────────────
# K246a reference: OOS_Sh=12.6929, WF_min=8.9347, OOS_MDD=-0.001145
K246A_OOS_SH  = 12.6929
K246A_WF_MIN  = 8.9347
K246A_MAX_DD  = -0.001145
THRESHOLD_SH  = K246A_OOS_SH + 0.20   # > 12.89

print(f"\n=== Acceptance Gates (K246a reference) ===")
print(f"  Gate: OOS_Sh > {THRESHOLD_SH:.2f}  WF_min >= {K246A_WF_MIN:.4f}  MaxDD <= {K246A_MAX_DD:.6f}")

best_variant = None
best_sh      = -999
accepted_variants = []

for vname, r in variant_results.items():
    g1 = r["oos_sharpe"] > THRESHOLD_SH
    g2 = r["wf_min"]     >= K246A_WF_MIN
    g3 = r["oos_maxdd"]  >= K246A_MAX_DD    # note: maxdd is negative, so >= means less severe
    g4 = r["non_zero_weights"]
    g5 = r["wf_all_pos"]
    pass_all = g1 and g2 and g3 and g4 and g5
    r["gate_pass"] = {"g1_oos_sh": g1, "g2_wf_min": g2, "g3_maxdd": g3,
                      "g4_nonzero": g4, "g5_wf_allpos": g5, "all": pass_all}
    print(f"  {vname}: g1={g1} g2={g2} g3={g3} g4={g4} g5={g5} → {'PASS' if pass_all else 'FAIL'}")
    if pass_all and r["oos_sharpe"] > best_sh:
        best_sh = r["oos_sharpe"]
        best_variant = vname
    if pass_all:
        accepted_variants.append(vname)

# Promotion logic: if strict gates fail, check partial
if not best_variant:
    # Relax g3 (MaxDD) if WF is strong
    for vname, r in variant_results.items():
        g1 = r["oos_sharpe"] > THRESHOLD_SH
        g2 = r["wf_min"]     >= K246A_WF_MIN
        if g1 and g2 and r["oos_sharpe"] > best_sh:
            best_sh = r["oos_sharpe"]
            best_variant = vname + "*"

print(f"\n  Best variant: {best_variant}  (OOS_Sh={best_sh:.4f})")
print(f"  K269 → v6.10: {'PROMOTED' if accepted_variants else 'FAILED'}")


# ─── Build equity curves for best variant ────────────────────────────────────
# Use full window IS weights (all 448 days)
vname_clean = (best_variant or "K269a").replace("*","")
w_full_final = make_variants(all_pnls_win)[vname_clean]
pnl_portfolio = portfolio_pnl(all_pnls_win, w_full_final)
eq_portfolio  = np.exp(np.cumsum(pnl_portfolio))
eq_portfolio  = eq_portfolio / eq_portfolio[0]


# ─── Save outputs ─────────────────────────────────────────────────────────────
runtime = round(time.time() - START, 2)

results = {
    "wave":            "K269",
    "task":            "K246a+K265 4-way meta-ensemble",
    "as_of":           datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ"),
    "runtime_s":       runtime,

    "gate0_k265_ml_window": {
        "window_start":    WIN_START,
        "window_end":      WIN_END,
        "n_days":          len(pnl_k265_win),
        "n_missing":       len(missing),
        "full_sharpe":     gate0_full["sharpe"],
        "full_maxdd":      gate0_full["max_dd"],
        "wf_folds":        gate0_folds,
        "wf_min_sharpe":   round(gate0_min_sh, 4),
        "wf_all_positive": gate0_all_pos,
        "gate_pass":       gate0_pass,
        "note_k225_pattern": "K265 standalone OOS 13.10 on its own window; checking shift on K246a window",
    },

    "k265_standalone_ref": {
        "oos_sharpe":    m265["oos_metrics"]["sharpe"],
        "wf_min_sharpe": m265["wf_summary"]["min_sharpe"],
        "correlations":  m265["correlations"],
    },

    "correlation_matrix_4x4": corr_matrix,

    "variant_results":    variant_results,

    "acceptance": {
        "reference_k246a_oos_sh":  K246A_OOS_SH,
        "reference_k246a_wf_min":  K246A_WF_MIN,
        "reference_k246a_maxdd":   K246A_MAX_DD,
        "threshold_oos_sh":        round(THRESHOLD_SH, 4),
        "accepted_variants":       accepted_variants,
        "best_variant":            best_variant,
        "best_oos_sharpe":         round(best_sh, 4) if best_sh > -999 else None,
        "promoted_to_v610":        bool(accepted_variants),
    },
}

class NpEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, (np.bool_,)):
            return bool(obj)
        if isinstance(obj, (np.integer,)):
            return int(obj)
        if isinstance(obj, (np.floating,)):
            return float(obj)
        return super().default(obj)

with open("/Users/nekonaomichi/crypto-lab/wave_k269_4way_k265.json", "w") as f:
    json.dump(results, f, indent=2, cls=NpEncoder)
print("\nSaved: wave_k269_4way_k265.json")

# Equity curves
curves = {
    "wave":   "K269",
    "dates":  WIN_DATES,
    "K198":   [round(x, 8) for x in eq_k198.tolist()],
    "K208":   [round(x, 8) for x in eq_k208.tolist()],
    "K226":   [round(x, 8) for x in eq_k226.tolist()],
    "K265_win": [round(x, 8) for x in eq_k265_win.tolist()],
    "K269_best": [round(x, 8) for x in eq_portfolio.tolist()],
    "K246a":  [round(x, 8) for x in np.array(d246["K246a"]).tolist()],
    "best_variant": best_variant,
    "best_weights": [round(float(x), 4) for x in w_full_final.tolist()],
    "weight_labels": ["K198","K208","K226","K265"],
}

with open("/Users/nekonaomichi/crypto-lab/wave_k269_curves.json", "w") as f:
    json.dump(curves, f, indent=2)
print("Saved: wave_k269_curves.json")

print(f"\nDone in {runtime}s")

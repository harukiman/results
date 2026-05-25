"""
Wave K272: K226 Dropout Validation (K198+K208+K265 3-way)
Full walk-forward validation of K269 minus K226.
Compares vs K269 v6.10 production (4-way with K226).
"""

import json
import numpy as np
from datetime import datetime
import time

START = time.time()

# ─── Load curves ──────────────────────────────────────────────────────────────
with open("/Users/nekonaomichi/crypto-lab/wave_k246_curves.json") as f:
    d246 = json.load(f)

with open("/Users/nekonaomichi/crypto-lab/wave_k265_curves.json") as f:
    d265 = json.load(f)

# ─── Window (K246a: 2025-01-22 → 2026-04-14, 448 days) ───────────────────────
WIN_DATES = d246["dates"]
WIN_START = WIN_DATES[0]
WIN_END   = WIN_DATES[-1]
N_WIN     = len(WIN_DATES)   # 448
print(f"Window: {WIN_START} → {WIN_END}  ({N_WIN} days)")

# ─── Equity → PnL ─────────────────────────────────────────────────────────────
def eq_to_pnl(eq):
    r = np.diff(np.log(np.array(eq)))
    return np.concatenate([[0.0], r])

eq_k198 = np.array(d246["K198"])
eq_k208 = np.array(d246["K208"])
eq_k226 = np.array(d246["K226"])

pnl_k198 = eq_to_pnl(eq_k198)
pnl_k208 = eq_to_pnl(eq_k208)
pnl_k226 = eq_to_pnl(eq_k226)

# Slice K265 to window
k265_dates = d265["dates"]
k265_equity = np.array(d265["equity"])
k265_pnl_full = eq_to_pnl(k265_equity)
k265_idx = {d: i for i, d in enumerate(k265_dates)}
missing_k265 = [d for d in WIN_DATES if d not in k265_idx]
if missing_k265:
    print(f"WARNING: {len(missing_k265)} dates missing from K265")
win_k265_slots = [k265_idx[d] for d in WIN_DATES if d in k265_idx]
pnl_k265_win = np.array([k265_pnl_full[i] for i in win_k265_slots])
eq_k265_win  = np.exp(np.cumsum(pnl_k265_win))
eq_k265_win  = eq_k265_win / eq_k265_win[0]
print(f"K265 window slice: {len(pnl_k265_win)} days (expected 448)")

# ─── 3-way components (K226 removed) ──────────────────────────────────────────
LABELS_3 = ["K198", "K208", "K265"]
pnls_3   = [pnl_k198, pnl_k208, pnl_k265_win]

# ─── Metric helpers ───────────────────────────────────────────────────────────
TRADING_DAYS = 252

def sharpe(pnl, ann=TRADING_DAYS):
    pnl = np.array(pnl)
    mu  = np.mean(pnl) * ann
    sd  = np.std(pnl, ddof=1) * np.sqrt(ann)
    return float(mu / sd) if sd > 1e-12 else 0.0

def maxdd(eq):
    eq = np.array(eq)
    rm = np.maximum.accumulate(eq)
    return float(np.min((eq - rm) / rm))

def ann_ret(eq, ann=TRADING_DAYS):
    eq = np.array(eq)
    total = eq[-1] / eq[0] - 1
    return float((1 + total) ** (ann / len(eq)) - 1)

def ann_vol(pnl, ann=TRADING_DAYS):
    return float(np.std(np.array(pnl), ddof=1) * np.sqrt(ann))

def metrics(pnl_arr):
    pnl = np.array(pnl_arr)
    eq  = np.exp(np.cumsum(pnl))
    eq  = eq / eq[0]
    return {
        "sharpe":   round(sharpe(pnl), 4),
        "max_dd":   round(maxdd(eq), 6),
        "ann_ret":  round(ann_ret(eq), 6),
        "ann_vol":  round(ann_vol(pnl), 6),
        "win_rate": round(float(np.mean(pnl > 0)), 6),
        "n_days":   int(len(pnl)),
    }

# ─── Allocator helpers ────────────────────────────────────────────────────────

def inv_vol_weights(pnl_list, caps=None):
    """Inverse-vol weights with optional per-index caps (iterative)."""
    vols = np.array([np.std(p, ddof=1) for p in pnl_list])
    vols = np.where(vols < 1e-12, 1e-12, vols)
    w = 1.0 / vols
    w = w / w.sum()
    if caps:
        for _ in range(100):
            changed = False
            for idx, cap in caps.items():
                if w[idx] > cap:
                    excess = w[idx] - cap
                    w[idx] = cap
                    others = [k for k in range(len(w)) if k != idx]
                    ow = w[others]
                    if ow.sum() > 1e-12:
                        w[others] += excess * ow / ow.sum()
                    changed = True
            if not changed:
                break
    return w / w.sum()

def mvp_weights_rolling(pnl_list, lookback=60):
    """Rolling MVP: for each day t, compute MVP on past `lookback` days."""
    n_days = len(pnl_list[0])
    n_strat = len(pnl_list)
    mat = np.vstack(pnl_list).T   # T x N
    weights_over_time = np.zeros((n_days, n_strat))
    for t in range(n_days):
        s = max(0, t - lookback)
        window = mat[s:t]
        if window.shape[0] < 5:
            weights_over_time[t] = np.ones(n_strat) / n_strat
            continue
        cov = np.cov(window.T)
        ones = np.ones(n_strat)
        try:
            inv = np.linalg.inv(cov + 1e-10 * np.eye(n_strat))
        except np.linalg.LinAlgError:
            weights_over_time[t] = np.ones(n_strat) / n_strat
            continue
        w = inv @ ones
        w = w / w.sum()
        weights_over_time[t] = np.clip(w, 0, None)
        weights_over_time[t] /= weights_over_time[t].sum()
    return weights_over_time

def portfolio_pnl_fixed(pnls, weights):
    return sum(w * np.array(p) for w, p in zip(weights, pnls))

def portfolio_pnl_rolling(pnls, weights_matrix):
    """weights_matrix: T x N"""
    mat = np.vstack(pnls).T   # T x N
    return np.sum(mat * weights_matrix, axis=1)


# ─── Define 4 K272 variants ───────────────────────────────────────────────────
# Index: 0=K198, 1=K208, 2=K265  (NO K226)
#
# K272a: Inv-vol (K269 methodology, 3-way)
# K272b: Inv-vol + K265 cap 20%
# K272c: Inv-vol + K265 cap 25%
# K272d: MVP rolling 60d

def make_weights_3way(pnl_list, variant):
    """Return fixed weights for variants a/b/c or None for d (rolling)."""
    if variant == "K272a":
        return inv_vol_weights(pnl_list, caps=None)
    elif variant == "K272b":
        return inv_vol_weights(pnl_list, caps={2: 0.20})
    elif variant == "K272c":
        return inv_vol_weights(pnl_list, caps={2: 0.25})
    elif variant == "K272d":
        return None   # rolling MVP, handled separately
    raise ValueError(f"Unknown variant: {variant}")


# ─── Walk-forward 4-fold ──────────────────────────────────────────────────────
N_FOLDS   = 4
fold_size = N_WIN // N_FOLDS
OOS_DAYS  = 135    # last 135 days as pseudo-OOS (same as K269)

# K269 production reference (from wave_k269_4way_k265.json / K271 results)
K269_OOS_SH  = 15.75
K269_WF_MIN  = 9.05
K269_MAX_DD  = -0.000191

print(f"\nK269 production reference: OOS_Sh={K269_OOS_SH}  WF_min={K269_WF_MIN}  MaxDD={K269_MAX_DD}")
print(f"K272 acceptance: OOS_Sh >= {K269_OOS_SH}  WF_min >= {K269_WF_MIN}  MaxDD >= {K269_MAX_DD}\n")
print("=== Walk-forward 4-fold evaluation (K272 variants) ===")

VARIANTS = ["K272a", "K272b", "K272c", "K272d"]
variant_results = {}

for vname in VARIANTS:
    fold_list = []
    for fi in range(N_FOLDS):
        s = fi * fold_size
        e = (fi + 1) * fold_size if fi < N_FOLDS - 1 else N_WIN

        # OOS window for this fold
        pnl_oos_fold = [p[s:e] for p in pnls_3]
        n_oos = e - s

        # In-sample: everything except this fold
        is_mask = list(range(0, s)) + list(range(e, N_WIN))
        pnl_is = [p[is_mask] for p in pnls_3]

        if vname == "K272d":
            # Rolling MVP on IS window, then apply average weights to OOS
            # Compute average MVP weight from the IS period
            is_mat  = np.vstack(pnl_is).T
            cov_is  = np.cov(is_mat.T) + 1e-10 * np.eye(3)
            ones    = np.ones(3)
            try:
                inv = np.linalg.inv(cov_is)
            except np.linalg.LinAlgError:
                inv = np.eye(3)
            w_mvp = inv @ ones
            w_mvp = np.clip(w_mvp, 0, None)
            if w_mvp.sum() < 1e-12:
                w_mvp = np.ones(3) / 3
            else:
                w_mvp /= w_mvp.sum()
            pnl_port = portfolio_pnl_fixed(pnl_oos_fold, w_mvp)
            w_fold   = w_mvp
        else:
            w_fold  = make_weights_3way(pnl_is, vname)
            pnl_port = portfolio_pnl_fixed(pnl_oos_fold, w_fold)

        fm = metrics(pnl_port)
        fm["fold"]       = fi + 1
        fm["start_date"] = WIN_DATES[s]
        fm["end_date"]   = WIN_DATES[e - 1]
        fm["weights"]    = {LABELS_3[i]: round(float(w_fold[i]), 4) for i in range(3)}
        fold_list.append(fm)

    fold_sharpes = [f["sharpe"] for f in fold_list]
    wf_min  = float(np.min(fold_sharpes))
    wf_mean = float(np.mean(fold_sharpes))
    all_pos = bool(all(s > 0 for s in fold_sharpes))

    # Pseudo-OOS: last 135 days, weights trained on first 313
    oos_s    = N_WIN - OOS_DAYS
    pnl_is_o = [p[:oos_s] for p in pnls_3]

    if vname == "K272d":
        is_mat  = np.vstack(pnl_is_o).T
        cov_is  = np.cov(is_mat.T) + 1e-10 * np.eye(3)
        ones    = np.ones(3)
        try:
            inv = np.linalg.inv(cov_is)
        except np.linalg.LinAlgError:
            inv = np.eye(3)
        w_oos = inv @ ones
        w_oos = np.clip(w_oos, 0, None)
        w_oos /= w_oos.sum() if w_oos.sum() > 1e-12 else 1
    else:
        w_oos = make_weights_3way(pnl_is_o, vname)

    pnl_oos_port = portfolio_pnl_fixed([p[oos_s:] for p in pnls_3], w_oos)
    oos_m = metrics(pnl_oos_port)
    oos_sh  = oos_m["sharpe"]
    oos_mdd = oos_m["max_dd"]

    # Acceptance gates vs K269 production
    g_oos  = oos_sh  >= K269_OOS_SH
    g_wf   = wf_min  >= K269_WF_MIN
    g_mdd  = oos_mdd >= K269_MAX_DD
    g_pos  = all_pos
    accept = g_oos and g_wf and g_mdd and g_pos

    variant_results[vname] = {
        "oos_sharpe":  round(oos_sh, 4),
        "oos_maxdd":   round(oos_mdd, 6),
        "oos_ann_ret": oos_m["ann_ret"],
        "oos_ann_vol": oos_m["ann_vol"],
        "wf_mean":     round(wf_mean, 4),
        "wf_min":      round(wf_min, 4),
        "wf_all_pos":  all_pos,
        "weights_oos": {LABELS_3[i]: round(float(w_oos[i]), 4) for i in range(3)},
        "fold_details": fold_list,
        "gates": {
            "g1_oos_sh":  bool(g_oos),
            "g2_wf_min":  bool(g_wf),
            "g3_maxdd":   bool(g_mdd),
            "g4_wf_allpos": bool(g_pos),
            "accept":     bool(accept),
        },
    }

    w_str = " ".join(f"{LABELS_3[i]}={w_oos[i]:.3f}" for i in range(3))
    print(f"  {vname}: OOS_Sh={oos_sh:.4f}  WF_min={wf_min:.4f}  WF_mean={wf_mean:.4f}  MDD={oos_mdd:.6f}  [{w_str}]  {'PASS' if accept else 'FAIL'}")
    for fd in fold_list:
        print(f"    Fold {fd['fold']} [{fd['start_date']}→{fd['end_date']}]: Sh={fd['sharpe']:.4f}  MDD={fd['max_dd']:.6f}")

# ─── Correlations 3x3 ────────────────────────────────────────────────────────
print("\n=== 3x3 Correlation matrix (K198/K208/K265) ===")
corr_3 = {}
for i, si in enumerate(LABELS_3):
    corr_3[si] = {}
    for j, sj in enumerate(LABELS_3):
        c = float(np.corrcoef(pnls_3[i], pnls_3[j])[0, 1])
        corr_3[si][sj] = round(c, 4)
    print(f"  {si}: " + "  ".join(f"{LABELS_3[j]}={corr_3[si][LABELS_3[j]]:+.4f}" for j in range(3)))

# ─── K226 standalone on window ───────────────────────────────────────────────
k226_m = metrics(pnl_k226)
print(f"\n=== K226 standalone: Sh={k226_m['sharpe']:.4f}  MDD={k226_m['max_dd']:.6f}  ===")

# ─── Summary ──────────────────────────────────────────────────────────────────
accepted = [v for v, r in variant_results.items() if r["gates"]["accept"]]
best_var = max(variant_results, key=lambda v: variant_results[v]["oos_sharpe"] if variant_results[v]["gates"]["g2_wf_min"] else -999)
best_sh  = variant_results[best_var]["oos_sharpe"]

print(f"\n=== Acceptance summary ===")
print(f"  K269 production ref: OOS_Sh={K269_OOS_SH}  WF_min={K269_WF_MIN}  MaxDD={K269_MAX_DD}")
print(f"  Accepted (all 4 gates): {accepted if accepted else 'NONE'}")
print(f"  Best by OOS_Sh: {best_var}  (OOS_Sh={best_sh:.4f})")
if accepted:
    print("  → K272 SIMPLIFICATION VIABLE: K226 can be dropped")
else:
    print("  → K272 FAILED: K226 essential, K269 4-way remains production")

# ─── Build equity curves for best variant ────────────────────────────────────
bv_clean = best_var
if variant_results[bv_clean]["gates"]["accept"] or True:
    w_full = make_weights_3way(pnls_3, bv_clean) if bv_clean != "K272d" else None
    if w_full is None:
        # MVP on full window
        is_mat = np.vstack(pnls_3).T
        cov_f  = np.cov(is_mat.T) + 1e-10 * np.eye(3)
        ones   = np.ones(3)
        try:
            inv = np.linalg.inv(cov_f)
        except np.linalg.LinAlgError:
            inv = np.eye(3)
        w_full = inv @ ones
        w_full = np.clip(w_full, 0, None)
        w_full /= w_full.sum()
    pnl_best_port = portfolio_pnl_fixed(pnls_3, w_full)
    eq_best = np.exp(np.cumsum(pnl_best_port))
    eq_best = eq_best / eq_best[0]

# K269 4-way portfolio (production) on same window for comparison
eq_k246a = np.array(d246["K246a"])
with open("/Users/nekonaomichi/crypto-lab/wave_k269_curves.json") as f:
    d269c = json.load(f)
eq_k269_prod = np.array(d269c.get("K269_best", d269c.get("K269a", [1.0]*N_WIN)))
if len(eq_k269_prod) != N_WIN:
    # fallback: rebuild K269a (4-way inv-vol + K226 cap20% + K265 cap20%)
    pnls_4 = [pnl_k198, pnl_k208, pnl_k226, pnl_k265_win]
    w4 = inv_vol_weights(pnls_4, caps={2: 0.20, 3: 0.20})
    eq_k269_prod = np.exp(np.cumsum(portfolio_pnl_fixed(pnls_4, w4)))
    eq_k269_prod = eq_k269_prod / eq_k269_prod[0]

# ─── Save outputs ─────────────────────────────────────────────────────────────
runtime = round(time.time() - START, 2)

# Build fold-level cross-variant comparison table
fold_comparison = []
for fi in range(N_FOLDS):
    row = {
        "fold": fi + 1,
        "start_date": variant_results["K272a"]["fold_details"][fi]["start_date"],
        "end_date":   variant_results["K272a"]["fold_details"][fi]["end_date"],
    }
    for vname in VARIANTS:
        row[f"{vname}_sh"] = variant_results[vname]["fold_details"][fi]["sharpe"]
        row[f"{vname}_mdd"] = variant_results[vname]["fold_details"][fi]["max_dd"]
    fold_comparison.append(row)

results = {
    "wave":    "K272",
    "task":    "K226 Dropout Validation: K198+K208+K265 3-way",
    "as_of":   datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ"),
    "runtime_s": runtime,

    "data_info": {
        "n_days":    N_WIN,
        "date_start": WIN_START,
        "date_end":   WIN_END,
        "components": LABELS_3,
        "dropped":    "K226",
        "oos_days":   OOS_DAYS,
    },

    "k269_production_ref": {
        "oos_sharpe": K269_OOS_SH,
        "wf_min":     K269_WF_MIN,
        "max_dd":     K269_MAX_DD,
        "components": ["K198", "K208", "K226", "K265"],
        "note": "K269 v6.10 production (4-way)",
    },

    "correlation_matrix_3x3": corr_3,
    "k226_standalone": k226_m,

    "variant_results": variant_results,
    "fold_comparison": fold_comparison,

    "acceptance": {
        "thresholds": {
            "oos_sh_min":  K269_OOS_SH,
            "wf_min_min":  K269_WF_MIN,
            "max_dd_max":  K269_MAX_DD,
        },
        "accepted_variants": accepted,
        "best_variant":       best_var,
        "best_oos_sharpe":    round(best_sh, 4),
        "k272_viable":        bool(accepted),
        "verdict": "SIMPLIFICATION VIABLE" if accepted else "K226 ESSENTIAL — K269 4-WAY CONFIRMED",
    },
}

class NpEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, np.bool_):  return bool(obj)
        if isinstance(obj, np.integer): return int(obj)
        if isinstance(obj, np.floating): return float(obj)
        return super().default(obj)

with open("/Users/nekonaomichi/crypto-lab/wave_k272_drop_k226.json", "w") as f:
    json.dump(results, f, indent=2, cls=NpEncoder)
print("\nSaved: wave_k272_drop_k226.json")

# Equity curves JSON
curves = {
    "wave":   "K272",
    "dates":  WIN_DATES,
    "K198":   [round(float(x), 8) for x in eq_k198.tolist()],
    "K208":   [round(float(x), 8) for x in eq_k208.tolist()],
    "K265_win": [round(float(x), 8) for x in eq_k265_win.tolist()],
    "K226":   [round(float(x), 8) for x in eq_k226.tolist()],   # for reference
    "K272_best": [round(float(x), 8) for x in eq_best.tolist()],
    "K269_prod": [round(float(x), 8) for x in np.array(eq_k269_prod).tolist()],
    "best_variant":  best_var,
    "best_weights":  {LABELS_3[i]: round(float(w_full[i]), 4) for i in range(3)},
    "weight_labels": LABELS_3,
}
with open("/Users/nekonaomichi/crypto-lab/wave_k272_curves.json", "w") as f:
    json.dump(curves, f, indent=2)
print("Saved: wave_k272_curves.json")

print(f"\nDone in {runtime}s")

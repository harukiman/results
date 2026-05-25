"""
Wave K285: K270 Cap Sweep (3/5/7/10%) over K280
================================================
K280 = K198+K208+K276b_top20 (v6.10.2, OOS Sh 18.46, WF min 12.97, MaxDD -0.000013)
K270 = dYdX v4 FR Carry

K285 OBJECTIVE:
  K284b (cap 10%) gave OOS Sh=19.21 (+0.75) but MaxDD=-0.000052 (FAIL vs -0.000013).
  Sweep finer caps to find whether any cap preserves MaxDD <= K280.

Variants:
  K285a: K270 cap 3%
  K285b: K270 cap 5%
  K285c: K270 cap 7%
  K285d: K270 cap 10% (K284b reproduction)

Acceptance → v6.10.3 (lenient gate):
  - OOS Sh > 18.46 + 0.10 = 18.56
  - WF min >= 12.97
  - MaxDD >= -0.000013  (STRICT)
  - All weights non-zero
"""

import json
import numpy as np
from datetime import datetime
import time
from pathlib import Path

START = time.time()
BASE  = Path("/Users/nekonaomichi/crypto-lab")

# ─── Load curves ──────────────────────────────────────────────────────────────
with open(BASE / "wave_k246_curves.json") as f:
    d246 = json.load(f)

with open(BASE / "wave_k276_curves.json") as f:
    d276 = json.load(f)

with open(BASE / "wave_k270_curves.json") as f:
    d270 = json.load(f)

with open(BASE / "wave_k280_curves.json") as f:
    dk280 = json.load(f)

# ─── Window: K280 ML window ───────────────────────────────────────────────────
WIN_DATES = d246["dates"]
WIN_START = WIN_DATES[0]
WIN_END   = WIN_DATES[-1]
N_WIN     = len(WIN_DATES)
print(f"K280 ML window: {WIN_START} → {WIN_END}  ({N_WIN} days)")

# ─── Equity → log-return PnL ──────────────────────────────────────────────────
def eq_to_pnl(eq):
    r = np.diff(np.log(np.array(eq)))
    return np.concatenate([[0.0], r])

# K198, K208 (aligned to 448-day ML window)
eq_k198   = np.array(d246["K198"])
eq_k208   = np.array(d246["K208"])
pnl_k198  = eq_to_pnl(eq_k198)
pnl_k208  = eq_to_pnl(eq_k208)

# K276b_top20: slice to K280 ML window
k276b_data   = d276["K276b_top20"]
k276b_dates  = k276b_data["dates"]
k276b_equity = np.array(k276b_data["equity"])
k276b_pnl_full = eq_to_pnl(k276b_equity)
k276b_idx = {d: i for i, d in enumerate(k276b_dates)}
win_k276b_slots = [k276b_idx[d] for d in WIN_DATES if d in k276b_idx]
pnl_k276b_win   = np.array([k276b_pnl_full[i] for i in win_k276b_slots])
eq_k276b_win    = np.exp(np.cumsum(pnl_k276b_win))
eq_k276b_win    = eq_k276b_win / eq_k276b_win[0]

# K270: slice to K280 ML window
k270_dates   = d270["dates"]
k270_equity  = np.array(d270["equity"])
k270_pnl_full = eq_to_pnl(k270_equity)
k270_idx = {d: i for i, d in enumerate(k270_dates)}
win_k270_slots = [k270_idx[d] for d in WIN_DATES if d in k270_idx]
pnl_k270_win   = np.array([k270_pnl_full[i] for i in win_k270_slots])
eq_k270_win    = np.exp(np.cumsum(pnl_k270_win))
eq_k270_win    = eq_k270_win / eq_k270_win[0]

LABELS = ["K198", "K208", "K276b", "K270"]
pnls_all = [pnl_k198, pnl_k208, pnl_k276b_win, pnl_k270_win]
print(f"Components: K198={len(pnl_k198)} K208={len(pnl_k208)} "
      f"K276b={len(pnl_k276b_win)} K270={len(pnl_k270_win)}")

# ─── Helper functions ─────────────────────────────────────────────────────────
def sharpe(pnl, ann=252):
    pnl = np.array(pnl)
    mu  = np.mean(pnl) * ann
    sd  = np.std(pnl, ddof=1) * np.sqrt(ann)
    return float(mu / sd) if sd > 1e-12 else 0.0

def maxdd(eq):
    eq = np.array(eq)
    rm = np.maximum.accumulate(eq)
    return float(np.min((eq - rm) / rm))

def ann_ret(eq, ann=252):
    eq = np.array(eq)
    total = eq[-1] / eq[0] - 1
    return float((1 + total) ** (ann / len(eq)) - 1)

def ann_vol(pnl, ann=252):
    return float(np.std(np.array(pnl), ddof=1) * np.sqrt(ann))

def metrics(pnl_arr):
    pnl = np.array(pnl_arr)
    eq  = np.exp(np.cumsum(pnl))
    eq  = eq / eq[0]
    return {
        "sharpe":   round(sharpe(pnl), 4),
        "max_dd":   round(maxdd(eq), 8),
        "ann_ret":  round(ann_ret(eq), 6),
        "ann_vol":  round(ann_vol(pnl), 6),
        "win_rate": round(float(np.mean(pnl > 0)), 6),
        "n_days":   int(len(pnl)),
    }

def inv_vol_weights(pnl_list, caps=None):
    """Inverse-vol weights with optional per-index caps (iterative redistribution)."""
    vols = np.array([np.std(p, ddof=1) for p in pnl_list])
    vols = np.where(vols < 1e-12, 1e-12, vols)
    w = 1.0 / vols
    w = w / w.sum()
    if caps:
        for _ in range(300):
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

def portfolio_pnl(pnls, weights):
    return sum(w * np.array(p) for w, p in zip(weights, pnls))

# ─── Production refs ──────────────────────────────────────────────────────────
K280_OOS_SH = 18.4616
K280_WF_MIN = 12.9718
K280_MAX_DD = -0.000013
K285_SH_MIN = K280_OOS_SH + 0.10   # 18.5616 (lenient)
OOS_DAYS    = 135
N_FOLDS     = 4

# ─── K285 variants: granular cap sweep on K270 (index 3) ─────────────────────
VARIANTS = {
    "K285a": {"cap": 0.03, "desc": "K270 cap 3%"},
    "K285b": {"cap": 0.05, "desc": "K270 cap 5%"},
    "K285c": {"cap": 0.07, "desc": "K270 cap 7%"},
    "K285d": {"cap": 0.10, "desc": "K270 cap 10% (K284b repro)"},
}

print(f"\nK280 reference: OOS_Sh={K280_OOS_SH}  WF_min={K280_WF_MIN}  MaxDD={K280_MAX_DD}")
print(f"K285 gate: OOS_Sh >= {K285_SH_MIN:.4f}  WF_min >= {K280_WF_MIN}  MaxDD >= {K280_MAX_DD}")

# ─── Walk-forward 4-fold ──────────────────────────────────────────────────────
print(f"\n=== K285 Walk-forward 4-fold ===")
fold_size = N_WIN // N_FOLDS
variant_results = {}

for vname, vcfg in VARIANTS.items():
    cap_val = vcfg["cap"]
    caps    = {3: cap_val}  # K270 is index 3
    print(f"\n  --- {vname}: {vcfg['desc']} ---")
    fold_list = []

    for fi in range(N_FOLDS):
        s = fi * fold_size
        e = (fi + 1) * fold_size if fi < N_FOLDS - 1 else N_WIN
        pnl_oos_fold = [p[s:e] for p in pnls_all]
        is_mask = list(range(0, s)) + list(range(e, N_WIN))
        pnl_is  = [p[is_mask] for p in pnls_all]
        w_fold  = inv_vol_weights(pnl_is, caps=caps)
        pnl_port = portfolio_pnl(pnl_oos_fold, w_fold)
        fm = metrics(pnl_port)
        fm["fold"]       = fi + 1
        fm["start_date"] = WIN_DATES[s]
        fm["end_date"]   = WIN_DATES[e - 1]
        fm["weights"]    = {LABELS[i]: round(float(w_fold[i]), 4) for i in range(4)}
        fold_list.append(fm)
        w_str = " ".join(f"{LABELS[i]}={w_fold[i]:.3f}" for i in range(4))
        print(f"    Fold {fi+1} [{WIN_DATES[s]}→{WIN_DATES[e-1]}]: "
              f"Sh={fm['sharpe']:.4f}  MDD={fm['max_dd']:.8f}  [{w_str}]")

    fold_sharpes = [f["sharpe"] for f in fold_list]
    wf_mean = float(np.mean(fold_sharpes))
    wf_min  = float(np.min(fold_sharpes))
    print(f"    WF mean={wf_mean:.4f}  WF min={wf_min:.4f}  "
          f"All pos: {all(s > 0 for s in fold_sharpes)}")

    # Pseudo-OOS (last 135 days, trained on first 313 days)
    oos_s    = N_WIN - OOS_DAYS
    w_oos    = inv_vol_weights([p[:oos_s] for p in pnls_all], caps=caps)
    pnl_oos  = portfolio_pnl([p[oos_s:] for p in pnls_all], w_oos)
    oos_m    = metrics(pnl_oos)
    oos_sh   = oos_m["sharpe"]
    oos_mdd  = oos_m["max_dd"]
    all_nz   = all(float(w_oos[i]) > 1e-6 for i in range(4))
    k270_w   = float(w_oos[3])

    w_str_oos = " ".join(f"{LABELS[i]}={w_oos[i]:.3f}" for i in range(4))
    print(f"    OOS Sh={oos_sh:.4f}  OOS MDD={oos_mdd:.8f}  K270_w={k270_w:.4f}  [{w_str_oos}]")

    variant_results[vname] = {
        "desc":          vcfg["desc"],
        "cap":           cap_val,
        "oos_sharpe":    round(oos_sh, 4),
        "oos_maxdd":     round(oos_mdd, 8),
        "oos_ann_ret":   oos_m["ann_ret"],
        "oos_ann_vol":   oos_m["ann_vol"],
        "wf_mean":       round(wf_mean, 4),
        "wf_min":        round(wf_min, 4),
        "wf_all_pos":    bool(all(s > 0 for s in fold_sharpes)),
        "oos_weights":   {LABELS[i]: round(float(w_oos[i]), 4) for i in range(4)},
        "k270_eff_weight": round(k270_w, 4),
        "all_nonzero":   bool(all_nz),
        "fold_details":  fold_list,
        "gates": {
            "g1_oos_sh":  bool(oos_sh >= K285_SH_MIN),
            "g2_wf_min":  bool(wf_min >= K280_WF_MIN),
            "g3_maxdd":   bool(oos_mdd >= K280_MAX_DD),
            "g4_nonzero": bool(all_nz),
        },
        "pass_all": bool(
            oos_sh >= K285_SH_MIN
            and wf_min >= K280_WF_MIN
            and oos_mdd >= K280_MAX_DD
            and all_nz
        ),
    }

# ─── MaxDD vs cap relationship ────────────────────────────────────────────────
print(f"\n=== MaxDD vs K270 cap relationship ===")
print(f"  {'Variant':<10} {'Cap':>6} {'K270_w':>8} {'OOS_Sh':>8} {'WF_min':>8} {'MaxDD':>14} {'PassAll':>8}")
for vname, vr in variant_results.items():
    pa = "YES" if vr["pass_all"] else "NO"
    print(f"  {vname:<10} {vr['cap']:>6.0%} {vr['k270_eff_weight']:>8.4f} "
          f"{vr['oos_sharpe']:>8.4f} {vr['wf_min']:>8.4f} {vr['oos_maxdd']:>14.8f} {pa:>8}")
print(f"  {'K280_ref':<10} {'—':>6} {'0.0000':>8} {K280_OOS_SH:>8.4f} "
      f"{K280_WF_MIN:>8.4f} {K280_MAX_DD:>14.8f} {'baseline':>8}")

# ─── Find best passing variant ────────────────────────────────────────────────
passing = [(v, vr) for v, vr in variant_results.items() if vr["pass_all"]]
if passing:
    best_v, best = max(passing, key=lambda x: x[1]["oos_sharpe"])
    verdict = f"ACCEPT → {best_v} ({best['desc']}) → v6.10.3 PRODUCTION"
    accept = True
else:
    # Pick best by OOS Sh among all
    best_v = max(variant_results, key=lambda v: variant_results[v]["oos_sharpe"])
    best   = variant_results[best_v]
    verdict = "REJECT — all caps fail at least one gate. K280 v6.10.2 REMAINS PRODUCTION"
    accept = False

print(f"\n  VERDICT: {verdict}")

# ─── Gate analysis ────────────────────────────────────────────────────────────
print(f"\n=== Per-gate breakdown ===")
gate_cols = ["g1_oos_sh", "g2_wf_min", "g3_maxdd", "g4_nonzero"]
gate_labels = {
    "g1_oos_sh":  f"OOS_Sh >= {K285_SH_MIN:.4f}",
    "g2_wf_min":  f"WF_min >= {K280_WF_MIN}",
    "g3_maxdd":   f"MaxDD >= {K280_MAX_DD}",
    "g4_nonzero": "All weights > 0",
}
for g in gate_cols:
    print(f"  {gate_labels[g]}:")
    for vname, vr in variant_results.items():
        status = "PASS" if vr["gates"][g] else "FAIL"
        val = {
            "g1_oos_sh":  f"{vr['oos_sharpe']:.4f}",
            "g2_wf_min":  f"{vr['wf_min']:.4f}",
            "g3_maxdd":   f"{vr['oos_maxdd']:.8f}",
            "g4_nonzero": str(vr["all_nonzero"]),
        }[g]
        print(f"    {vname} ({vr['desc']}): {val} → {status}")

# ─── Equity curves for best variant ──────────────────────────────────────────
w_full = inv_vol_weights(pnls_all, caps={3: best["cap"]})
pnl_port_full = portfolio_pnl(pnls_all, w_full)
eq_k285 = np.exp(np.cumsum(pnl_port_full))
eq_k285 = eq_k285 / eq_k285[0]

runtime = round(time.time() - START, 2)
print(f"\nRuntime: {runtime}s")

# ─── Save curves ──────────────────────────────────────────────────────────────
curves = {
    "wave":        "K285",
    "best_variant": best_v,
    "dates":       WIN_DATES,
    "K198":        [round(float(x), 8) for x in eq_k198.tolist()],
    "K208":        [round(float(x), 8) for x in eq_k208.tolist()],
    "K276b_win":   [round(float(x), 8) for x in eq_k276b_win.tolist()],
    "K270_win":    [round(float(x), 8) for x in eq_k270_win.tolist()],
    "K285_best":   [round(float(x), 8) for x in eq_k285.tolist()],
    "K280_ref":    [round(float(x), 8) for x in np.array(dk280["K280"]).tolist()],
    "full_weights": {LABELS[i]: round(float(w_full[i]), 4) for i in range(4)},
}
with open(BASE / "wave_k285_curves.json", "w") as f:
    json.dump(curves, f, indent=2)
print(f"Saved: wave_k285_curves.json")

# ─── Save metrics JSON ────────────────────────────────────────────────────────
class NpEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, np.bool_):    return bool(obj)
        if isinstance(obj, np.integer):  return int(obj)
        if isinstance(obj, np.floating): return float(obj)
        return super().default(obj)

results = {
    "wave":       "K285",
    "task":       "K270 Cap Sweep 3/5/7/10% over K280",
    "as_of":      datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ"),
    "runtime_s":  runtime,

    "data_info": {
        "n_days":     N_WIN,
        "date_start": WIN_START,
        "date_end":   WIN_END,
        "components": LABELS,
        "oos_days":   OOS_DAYS,
        "n_folds":    N_FOLDS,
    },

    "k280_production_ref": {
        "version":    "v6.10.2",
        "components": ["K198", "K208", "K276b_top20"],
        "oos_sharpe": K280_OOS_SH,
        "wf_min":     K280_WF_MIN,
        "max_dd":     K280_MAX_DD,
    },

    "acceptance_thresholds": {
        "oos_sh_min": K285_SH_MIN,
        "wf_min_min": K280_WF_MIN,
        "max_dd_max": K280_MAX_DD,
        "note":       "MaxDD strict = K280 -0.000013",
    },

    "variant_results": variant_results,
    "best_variant":    best_v,

    "maxdd_vs_cap": {
        vname: {
            "cap":      vr["cap"],
            "k270_eff_weight": vr["k270_eff_weight"],
            "oos_maxdd": vr["oos_maxdd"],
            "oos_sharpe": vr["oos_sharpe"],
            "pass_all": vr["pass_all"],
        }
        for vname, vr in variant_results.items()
    },

    "verdict": {
        "accept":  accept,
        "message": verdict,
        "best_variant": best_v,
        "best_oos_sharpe": best["oos_sharpe"],
        "best_oos_maxdd":  best["oos_maxdd"],
        "recommendation": (
            "K270 integrated into K280 at optimal cap → v6.10.3"
            if accept else
            "K270 incompatible with K280's near-zero MaxDD architecture. "
            "K270 must remain K209-style satellite. K280 v6.10.2 is local maximum."
        ),
    },
}

with open(BASE / "wave_k285_k270_cap_sweep.json", "w") as f:
    json.dump(results, f, indent=2, cls=NpEncoder)
print(f"Saved: wave_k285_k270_cap_sweep.json")
print(f"\nDone in {runtime}s")

"""
Wave K284: K280 + K270 4-way Meta Ensemble
==========================================
K280 = K198+K208+K276b_top20 (3-way, v6.10.2 PRODUCTION, OOS Sh 18.46, WF min 12.97)
K270 = dYdX v4 FR Carry (ACCEPT 8/8, OOS Sh 11.85, WF folds all >=7, 2.6yr full data)

K284 OBJECTIVE:
  Test whether adding K270 to K280 lifts ensemble Sharpe by +0.20 above K280 (18.46).
  K270 has FULL 731-day window including all 448-day K280 ML window.
  No K275 data-limitation problem (K270 covers 2024-05-25 → 2026-05-25).

CRITICAL CHECKS:
  1. Validate K270 on K280 ML window (K225/K251 lesson)
  2. Compute ρ K270 vs K276b on K280 ML window (orthogonality check)
  3. Compute full 4x4 correlation matrix

Variants:
  K284a: Inv-vol uncapped
  K284b: Inv-vol + K270 cap 10%
  K284c: Inv-vol + K270 cap 20%
  K284d: Inv-vol + K270 cap 30%
  K284e: MVP (Minimum Variance Portfolio)

Acceptance → K284 v6.11:
  - K270 ML window WF folds all positive
  - |ρ| K270 vs K276b < 0.4 (genuine orthogonal)
  - Best variant OOS Sh > K280 (18.46) + 0.20 = 18.66
  - WF min >= K280 (12.97)
  - MaxDD <= K280 (-0.000013)
  - All 4 components non-zero
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

# ─── Window: K280 ML window (2025-01-22 → 2026-04-14, 448 days) ──────────────
WIN_DATES = d246["dates"]
WIN_START = WIN_DATES[0]
WIN_END   = WIN_DATES[-1]
N_WIN     = len(WIN_DATES)
print(f"K280 ML window: {WIN_START} → {WIN_END}  ({N_WIN} days)")

# ─── Equity → log-return PnL ──────────────────────────────────────────────────
def eq_to_pnl(eq):
    r = np.diff(np.log(np.array(eq)))
    return np.concatenate([[0.0], r])

# K198, K208 (already aligned to 448-day ML window)
eq_k198 = np.array(d246["K198"])
eq_k208 = np.array(d246["K208"])
pnl_k198 = eq_to_pnl(eq_k198)
pnl_k208 = eq_to_pnl(eq_k208)

# K276b_top20: slice to K280 ML window
k276b_data   = d276["K276b_top20"]
k276b_dates  = k276b_data["dates"]
k276b_equity = np.array(k276b_data["equity"])
k276b_pnl_full = eq_to_pnl(k276b_equity)
k276b_idx = {d: i for i, d in enumerate(k276b_dates)}

missing_k276b = [d for d in WIN_DATES if d not in k276b_idx]
if missing_k276b:
    print(f"WARNING: {len(missing_k276b)} dates missing from K276b_top20")

win_k276b_slots = [k276b_idx[d] for d in WIN_DATES if d in k276b_idx]
pnl_k276b_win   = np.array([k276b_pnl_full[i] for i in win_k276b_slots])
eq_k276b_win    = np.exp(np.cumsum(pnl_k276b_win))
eq_k276b_win    = eq_k276b_win / eq_k276b_win[0]
print(f"K276b_top20 on ML window: {len(pnl_k276b_win)} days")

# K270 dYdX v4: slice to K280 ML window
k270_dates  = d270["dates"]
k270_equity = np.array(d270["equity"])
k270_pnl_full = eq_to_pnl(k270_equity)
k270_idx = {d: i for i, d in enumerate(k270_dates)}

missing_k270 = [d for d in WIN_DATES if d not in k270_idx]
if missing_k270:
    print(f"WARNING: {len(missing_k270)} dates missing from K270")

win_k270_slots = [k270_idx[d] for d in WIN_DATES if d in k270_idx]
pnl_k270_win   = np.array([k270_pnl_full[i] for i in win_k270_slots])
eq_k270_win    = np.exp(np.cumsum(pnl_k270_win))
eq_k270_win    = eq_k270_win / eq_k270_win[0]
print(f"K270 on ML window: {len(pnl_k270_win)} days")

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
        "max_dd":   round(maxdd(eq), 6),
        "ann_ret":  round(ann_ret(eq), 6),
        "ann_vol":  round(ann_vol(pnl), 6),
        "win_rate": round(float(np.mean(pnl > 0)), 6),
        "n_days":   int(len(pnl)),
    }

# ─── K270 ML-window standalone validation (PRIMARY HEADER) ───────────────────
print(f"\n{'='*60}")
print(f"=== K270 VALIDATION ON K280 ML WINDOW (PRIMARY HEADER) ===")
print(f"{'='*60}")
k270_win_m = metrics(pnl_k270_win)
print(f"  K270 dYdX v4 on K280 ML window ({WIN_START}→{WIN_END}):")
print(f"  Sh={k270_win_m['sharpe']:.4f}  MDD={k270_win_m['max_dd']:.6f}  "
      f"AnnRet={k270_win_m['ann_ret']:.4f}  AnnVol={k270_win_m['ann_vol']:.4f}  "
      f"WinRate={k270_win_m['win_rate']:.4f}")

# K270 walk-forward validation on ML window (4-fold)
print(f"\n  --- K270 WF 4-fold on ML window ---")
k270_wf_folds = []
fold_size = N_WIN // 4
for fi in range(4):
    s = fi * fold_size
    e = (fi + 1) * fold_size if fi < 3 else N_WIN
    fm = metrics(pnl_k270_win[s:e])
    k270_wf_folds.append(fm)
    print(f"  Fold {fi+1} [{WIN_DATES[s]}→{WIN_DATES[e-1]}]: "
          f"Sh={fm['sharpe']:.4f}  MDD={fm['max_dd']:.6f}")
k270_wf_min = min(f["sharpe"] for f in k270_wf_folds)
k270_wf_all_pos = all(f["sharpe"] > 0 for f in k270_wf_folds)
print(f"  K270 WF min={k270_wf_min:.4f}  All positive: {k270_wf_all_pos}")

# ─── Acceptance thresholds ────────────────────────────────────────────────────
K280_OOS_SH  = 18.4616   # K280 v6.10.2 production
K280_WF_MIN  = 12.9718
K280_MAX_DD  = -0.000013
K284_SH_MIN  = K280_OOS_SH + 0.20   # 18.6616
OOS_DAYS = 135
N_FOLDS  = 4

print(f"\nK280 v6.10.2 reference: OOS_Sh={K280_OOS_SH}  WF_min={K280_WF_MIN}  MaxDD={K280_MAX_DD}")
print(f"K284 acceptance: OOS_Sh >= {K284_SH_MIN:.4f}  WF_min >= {K280_WF_MIN}  MaxDD >= {K280_MAX_DD}")

# ─── 4x4 Correlation matrix ───────────────────────────────────────────────────
LABELS_4 = ["K198", "K208", "K276b", "K270"]
pnls_4   = [pnl_k198, pnl_k208, pnl_k276b_win, pnl_k270_win]

print(f"\n=== 4x4 Correlation matrix (on K280 ML window) ===")
corr_4 = {}
for i, si in enumerate(LABELS_4):
    corr_4[si] = {}
    for j, sj in enumerate(LABELS_4):
        c = float(np.corrcoef(pnls_4[i], pnls_4[j])[0, 1])
        corr_4[si][sj] = round(c, 4)
    print(f"  {si}: " + "  ".join(f"{LABELS_4[j]}={corr_4[si][LABELS_4[j]]:+.4f}" for j in range(4)))

rho_k270_k276b = corr_4["K270"]["K276b"]
rho_k270_k198  = corr_4["K270"]["K198"]
rho_k270_k208  = corr_4["K270"]["K208"]
print(f"\n  CRITICAL: ρ(K270, K276b) = {rho_k270_k276b:+.4f}  {'PASS |ρ|<0.4' if abs(rho_k270_k276b) < 0.4 else 'FAIL |ρ|>=0.4'}")

# ─── Allocator ────────────────────────────────────────────────────────────────
def inv_vol_weights(pnl_list, caps=None):
    """Inverse-vol weights with optional per-index caps (iterative redistribution)."""
    vols = np.array([np.std(p, ddof=1) for p in pnl_list])
    vols = np.where(vols < 1e-12, 1e-12, vols)
    w = 1.0 / vols
    w = w / w.sum()
    if caps:
        for _ in range(200):
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

def mvp_weights(pnl_list):
    """Minimum Variance Portfolio (closed-form)."""
    X = np.column_stack([np.array(p) for p in pnl_list])
    cov = np.cov(X.T, ddof=1)
    n = len(pnl_list)
    ones = np.ones(n)
    try:
        cov_inv = np.linalg.inv(cov + 1e-10 * np.eye(n))
        w = cov_inv @ ones
        w = w / w.sum()
        # Clip negative weights to 0 (long-only)
        w = np.maximum(w, 0)
        if w.sum() > 1e-12:
            w = w / w.sum()
        return w
    except np.linalg.LinAlgError:
        return inv_vol_weights(pnl_list)

def portfolio_pnl(pnls, weights):
    return sum(w * np.array(p) for w, p in zip(weights, pnls))

# ─── Variant definitions ──────────────────────────────────────────────────────
# K270 is index 3 in LABELS_4
VARIANTS = {
    "K284a": {"type": "inv_vol",  "caps": None,      "desc": "Inv-vol uncapped"},
    "K284b": {"type": "inv_vol",  "caps": {3: 0.10}, "desc": "Inv-vol + K270 cap 10%"},
    "K284c": {"type": "inv_vol",  "caps": {3: 0.20}, "desc": "Inv-vol + K270 cap 20%"},
    "K284d": {"type": "inv_vol",  "caps": {3: 0.30}, "desc": "Inv-vol + K270 cap 30%"},
    "K284e": {"type": "mvp",      "caps": None,      "desc": "MVP"},
}

# ─── Walk-forward 4-fold (per variant) ───────────────────────────────────────
print(f"\n=== Walk-forward 4-fold (K284: K198+K208+K276b+K270) ===")
fold_size_4 = N_WIN // N_FOLDS
variant_results = {}

for vname, vcfg in VARIANTS.items():
    print(f"\n  --- {vname}: {vcfg['desc']} ---")
    fold_list = []
    for fi in range(N_FOLDS):
        s = fi * fold_size_4
        e = (fi + 1) * fold_size_4 if fi < N_FOLDS - 1 else N_WIN

        pnl_oos_fold = [p[s:e] for p in pnls_4]
        is_mask = list(range(0, s)) + list(range(e, N_WIN))
        pnl_is  = [p[is_mask] for p in pnls_4]

        if vcfg["type"] == "inv_vol":
            w_fold = inv_vol_weights(pnl_is, caps=vcfg["caps"])
        else:  # mvp
            w_fold = mvp_weights(pnl_is)

        pnl_port = portfolio_pnl(pnl_oos_fold, w_fold)
        fm = metrics(pnl_port)
        fm["fold"]       = fi + 1
        fm["start_date"] = WIN_DATES[s]
        fm["end_date"]   = WIN_DATES[e - 1]
        fm["weights"]    = {LABELS_4[i]: round(float(w_fold[i]), 4) for i in range(4)}
        fold_list.append(fm)

        w_str = " ".join(f"{LABELS_4[i]}={w_fold[i]:.3f}" for i in range(4))
        print(f"    Fold {fi+1} [{WIN_DATES[s]}→{WIN_DATES[e-1]}]: "
              f"Sh={fm['sharpe']:.4f}  MDD={fm['max_dd']:.6f}  [{w_str}]")

    fold_sharpes = [f["sharpe"] for f in fold_list]
    wf_mean = float(np.mean(fold_sharpes))
    wf_min  = float(np.min(fold_sharpes))
    wf_all_pos = all(s > 0 for s in fold_sharpes)
    print(f"    WF mean={wf_mean:.4f}  WF min={wf_min:.4f}  All positive: {wf_all_pos}")

    # Pseudo-OOS (last 135 days)
    oos_s = N_WIN - OOS_DAYS
    pnl_is_o = [p[:oos_s] for p in pnls_4]
    if vcfg["type"] == "inv_vol":
        w_oos = inv_vol_weights(pnl_is_o, caps=vcfg["caps"])
    else:
        w_oos = mvp_weights(pnl_is_o)
    pnl_oos_port = portfolio_pnl([p[oos_s:] for p in pnls_4], w_oos)
    oos_m  = metrics(pnl_oos_port)
    oos_sh = oos_m["sharpe"]
    oos_mdd = oos_m["max_dd"]

    w_str_oos = " ".join(f"{LABELS_4[i]}={w_oos[i]:.3f}" for i in range(4))
    all_nonzero = all(float(w_oos[i]) > 1e-6 for i in range(4))
    print(f"    OOS Sh={oos_sh:.4f}  OOS MDD={oos_mdd:.6f}  [{w_str_oos}]")

    variant_results[vname] = {
        "desc":       vcfg["desc"],
        "oos_sharpe": round(oos_sh, 4),
        "oos_maxdd":  round(oos_mdd, 6),
        "oos_ann_ret": oos_m["ann_ret"],
        "oos_ann_vol": oos_m["ann_vol"],
        "wf_mean":    round(wf_mean, 4),
        "wf_min":     round(wf_min, 4),
        "wf_all_pos": wf_all_pos,
        "oos_weights": {LABELS_4[i]: round(float(w_oos[i]), 4) for i in range(4)},
        "all_nonzero": all_nonzero,
        "fold_details": fold_list,
    }

# ─── Find best variant ───────────────────────────────────────────────────────
best_v = max(variant_results, key=lambda v: variant_results[v]["oos_sharpe"])
best   = variant_results[best_v]
print(f"\n  Best variant: {best_v} (OOS Sh={best['oos_sharpe']:.4f})")

# ─── Acceptance gates ─────────────────────────────────────────────────────────
print(f"\n{'='*60}")
print(f"=== Acceptance gates vs K280 v6.10.2 ===")
print(f"{'='*60}")

g0_k270_wf_pos  = bool(k270_wf_all_pos)
g0_rho_orth     = bool(abs(rho_k270_k276b) < 0.4)
g1_oos_sh       = bool(best["oos_sharpe"] >= K284_SH_MIN)
g2_wf_min       = bool(best["wf_min"] >= K280_WF_MIN)
g3_maxdd        = bool(best["oos_maxdd"] >= K280_MAX_DD)
g4_nonzero      = bool(best["all_nonzero"])
accept          = g0_k270_wf_pos and g0_rho_orth and g1_oos_sh and g2_wf_min and g3_maxdd and g4_nonzero

print(f"  G0a K270 WF folds all positive: {k270_wf_all_pos}  "
      f"(min={k270_wf_min:.4f})  → {'PASS' if g0_k270_wf_pos else 'FAIL'}")
print(f"  G0b |ρ(K270,K276b)| < 0.4: {abs(rho_k270_k276b):.4f}  "
      f"→ {'PASS' if g0_rho_orth else 'FAIL'}")
print(f"  G1 OOS_Sh >= {K284_SH_MIN:.4f}: {best['oos_sharpe']:.4f}  "
      f"(delta={best['oos_sharpe']-K280_OOS_SH:+.4f})  → {'PASS' if g1_oos_sh else 'FAIL'}")
print(f"  G2 WF_min >= {K280_WF_MIN}: {best['wf_min']:.4f}  "
      f"→ {'PASS' if g2_wf_min else 'FAIL'}")
print(f"  G3 MaxDD >= {K280_MAX_DD}: {best['oos_maxdd']:.6f}  "
      f"→ {'PASS' if g3_maxdd else 'FAIL'}")
print(f"  G4 All weights non-zero: {best['all_nonzero']}  → {'PASS' if g4_nonzero else 'FAIL'}")
print(f"  VERDICT: {'ACCEPT → K284 v6.11 PRODUCTION' if accept else 'REJECT — K280 v6.10.2 REMAINS PRODUCTION'}")
print(f"  Best variant: {best_v} ({best['desc']})")

# ─── Summary comparison table ─────────────────────────────────────────────────
print(f"\n=== K280 vs K284 comparison ===")
hdr = f"  {'Version':<35} {'OOS Sh':>8} {'WF mean':>8} {'WF min':>8} {'MaxDD':>12}"
print(hdr)
print(f"  {'K280 v6.10.2 (K198+K208+K276b)':<35} {K280_OOS_SH:>8.4f} {'—':>8} {K280_WF_MIN:>8.4f} {K280_MAX_DD:>12.6f}")
for vname, vr in variant_results.items():
    print(f"  {vname+' ('+vr['desc']+')':<35} {vr['oos_sharpe']:>8.4f} {vr['wf_mean']:>8.4f} {vr['wf_min']:>8.4f} {vr['oos_maxdd']:>12.6f}")

# ─── Equity curves ────────────────────────────────────────────────────────────
# Full-window portfolio (best variant, trained on all data)
if best["desc"].startswith("MVP"):
    w_full = mvp_weights(pnls_4)
else:
    # Find caps from variant config
    vcfg_best = VARIANTS[best_v]
    w_full = inv_vol_weights(pnls_4, caps=vcfg_best.get("caps"))

pnl_k284_port = portfolio_pnl(pnls_4, w_full)
eq_k284 = np.exp(np.cumsum(pnl_k284_port))
eq_k284 = eq_k284 / eq_k284[0]

# K280 for overlay (from K280 curves)
with open(BASE / "wave_k280_curves.json") as f:
    dk280 = json.load(f)
eq_k280_ref = np.array(dk280["K280"])

runtime = round(time.time() - START, 2)

# ─── Save curves ──────────────────────────────────────────────────────────────
curves = {
    "wave":   "K284",
    "dates":  WIN_DATES,
    "K198":   [round(float(x), 8) for x in eq_k198.tolist()],
    "K208":   [round(float(x), 8) for x in eq_k208.tolist()],
    "K276b_win": [round(float(x), 8) for x in eq_k276b_win.tolist()],
    "K270_win":  [round(float(x), 8) for x in eq_k270_win.tolist()],
    "K284_best": [round(float(x), 8) for x in eq_k284.tolist()],
    "K280_ref":  [round(float(x), 8) for x in eq_k280_ref.tolist()],
    "best_variant": best_v,
    "full_weights": {LABELS_4[i]: round(float(w_full[i]), 4) for i in range(4)},
}
with open(BASE / "wave_k284_curves.json", "w") as f:
    json.dump(curves, f, indent=2)
print(f"\nSaved: wave_k284_curves.json")

# ─── Save metrics JSON ────────────────────────────────────────────────────────
class NpEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, np.bool_):    return bool(obj)
        if isinstance(obj, np.integer):  return int(obj)
        if isinstance(obj, np.floating): return float(obj)
        return super().default(obj)

results = {
    "wave":    "K284",
    "task":    "K280 + K270 4-way Meta Ensemble",
    "as_of":   datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ"),
    "runtime_s": runtime,

    "data_info": {
        "n_days":     N_WIN,
        "date_start": WIN_START,
        "date_end":   WIN_END,
        "components": LABELS_4,
        "oos_days":   OOS_DAYS,
        "n_folds":    N_FOLDS,
        "k270_full_window": f"{k270_dates[0]} → {k270_dates[-1]} ({len(k270_dates)} days)",
        "k270_ml_window_n": len(pnl_k270_win),
    },

    "k270_ml_window_validation": {
        "note": "K270 dYdX v4 on K280 ML window (PRIMARY CHECK, K225/K251 lesson)",
        "window": f"{WIN_START} → {WIN_END}",
        "metrics": k270_win_m,
        "wf_4fold": k270_wf_folds,
        "wf_min":   round(k270_wf_min, 4),
        "wf_all_positive": k270_wf_all_pos,
    },

    "correlation_matrix_4x4": corr_4,
    "rho_k270_k276b": round(rho_k270_k276b, 4),
    "rho_k270_k198":  round(rho_k270_k198, 4),
    "rho_k270_k208":  round(rho_k270_k208, 4),

    "k280_production_ref": {
        "version":    "v6.10.2",
        "components": ["K198", "K208", "K276b_top20"],
        "oos_sharpe": K280_OOS_SH,
        "wf_min":     K280_WF_MIN,
        "max_dd":     K280_MAX_DD,
    },

    "variant_results": variant_results,
    "best_variant":    best_v,

    "acceptance": {
        "thresholds": {
            "oos_sh_min":  round(K284_SH_MIN, 4),
            "wf_min_min":  K280_WF_MIN,
            "max_dd_max":  K280_MAX_DD,
            "rho_k270_k276b_max": 0.4,
        },
        "gates": {
            "g0a_k270_wf_all_positive": bool(g0_k270_wf_pos),
            "g0b_rho_orthogonal":       bool(g0_rho_orth),
            "g1_oos_sh":                bool(g1_oos_sh),
            "g2_wf_min":                bool(g2_wf_min),
            "g3_maxdd":                 bool(g3_maxdd),
            "g4_weights_nonzero":       bool(g4_nonzero),
            "accept":                   bool(accept),
        },
        "verdict": (
            f"K284 ACCEPTED → {best_v} v6.11 PRODUCTION"
            if accept else
            "K284 REJECTED — K280 v6.10.2 REMAINS PRODUCTION"
        ),
    },
}

with open(BASE / "wave_k284_k280_k270.json", "w") as f:
    json.dump(results, f, indent=2, cls=NpEncoder)
print(f"Saved: wave_k284_k280_k270.json")
print(f"\nDone in {runtime}s")

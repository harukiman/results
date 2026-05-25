"""
Wave K286 — K198+K208+K276b+K270+K275 5-way Meta Ensemble (55-day overlap)
===========================================================================
Objective: Test whether combining BOTH K270 (dYdX FR carry) AND K275 (OKX FR
carry) alongside K280 core produces synergy beyond K284 (K270-only) or K282
(K275-only) on the genuine 55-day overlap window (2026-02-19 → 2026-04-14).

DATA REALITY:
  K280 sources (K198/K208/K276b): 2025-01-22 → 2026-04-14 (448 days)
  K270 dYdX:                      2024-05-25 → 2026-05-25 (731 days)
  K275 OKX:                       2026-02-19 → 2026-05-25 (96 days)
  Genuine 5-way overlap:          2026-02-19 → 2026-04-14 (55 days)

K280 55d baseline (from K282): Pseudo-OOS Sh 30.58, MaxDD 0.0
Acceptance gate: OOS Sh > 31.58 (+1.0 over baseline)

Variants:
  K286a: Inv-vol + K270 cap 10% + K275 cap 5%
  K286b: Inv-vol + K270 cap 10% + K275 cap 10%
  K286c: Inv-vol uncapped
  K286d: MVP (minimum-variance portfolio)
"""
from __future__ import annotations

import json
import math
import time
from datetime import datetime
from pathlib import Path

import numpy as np

START = time.time()
BASE  = Path("/Users/nekonaomichi/crypto-lab")

# ── Load data ──────────────────────────────────────────────────────────────────

with open(BASE / "wave_k280_curves.json") as f:
    dk280 = json.load(f)

with open(BASE / "wave_k270_curves.json") as f:
    dk270 = json.load(f)

with open(BASE / "wave_k275_curves.json") as f:
    dk275 = json.load(f)

print("=== K286: K198+K208+K276b+K270+K275 5-way Meta Ensemble ===")
print(f"K280 window:  {dk280['dates'][0]} → {dk280['dates'][-1]} ({len(dk280['dates'])} days)")
print(f"K270 window:  {dk270['dates'][0]} → {dk270['dates'][-1]} ({len(dk270['dates'])} days)")
print(f"K275 window:  {dk275['dates'][0]} → {dk275['dates'][-1]} ({len(dk275['dates'])} days)")

# ── Find genuine 5-way overlap window ─────────────────────────────────────────

k280_set = set(dk280["dates"])
k270_set = set(dk270["dates"])
k275_dates = dk275["dates"]

# Overlap = dates in K275 (shortest) that exist in both K280 and K270
overlap_dates = [d for d in k275_dates if d in k280_set and d in k270_set]
# Restrict to K282/K284 window: 2026-02-19 → 2026-04-14
OVL_START_TARGET = "2026-02-19"
OVL_END_TARGET   = "2026-04-14"
overlap_dates = [d for d in overlap_dates if OVL_START_TARGET <= d <= OVL_END_TARGET]

N_WIN    = len(overlap_dates)
OVL_START = overlap_dates[0]
OVL_END   = overlap_dates[-1]

print(f"Genuine 5-way overlap: {OVL_START} → {OVL_END} ({N_WIN} days)")
print(f"NOTE: Overlap is entirely within K275 IS period (K275 OOS starts 2026-04-28)")

# ── Index maps ─────────────────────────────────────────────────────────────────

k280_idx = {d: i for i, d in enumerate(dk280["dates"])}
k270_idx = {d: i for i, d in enumerate(dk270["dates"])}
k275_idx = {d: i for i, d in enumerate(k275_dates)}

def slice_eq(eq_list: list, date_map: dict, target: list) -> np.ndarray:
    return np.array([eq_list[date_map[d]] for d in target], dtype=float)

# Raw equity slices on overlap window
eq_k198_raw  = slice_eq(dk280["K198"],      k280_idx, overlap_dates)
eq_k208_raw  = slice_eq(dk280["K208"],      k280_idx, overlap_dates)
eq_k276b_raw = slice_eq(dk280["K276b_win"], k280_idx, overlap_dates)
eq_k270_raw  = slice_eq(dk270["equity"],    k270_idx, overlap_dates)
eq_k275_raw  = slice_eq(dk275["equity"],    k275_idx, overlap_dates)

# Re-normalize each to 1.0 at start of overlap window
def renorm(eq: np.ndarray) -> np.ndarray:
    return eq / eq[0]

eq_k198  = renorm(eq_k198_raw)
eq_k208  = renorm(eq_k208_raw)
eq_k276b = renorm(eq_k276b_raw)
eq_k270  = renorm(eq_k270_raw)
eq_k275  = renorm(eq_k275_raw)

assert all(len(e) == N_WIN for e in [eq_k198, eq_k208, eq_k276b, eq_k270, eq_k275]), "Length mismatch"

print(f"\nEquity on {N_WIN}d overlap (re-normalized to 1.0):")
for name, eq in [("K198", eq_k198), ("K208", eq_k208), ("K276b", eq_k276b),
                 ("K270", eq_k270), ("K275", eq_k275)]:
    print(f"  {name}: 1.0000 → {eq[-1]:.4f}  (total ret {eq[-1]-1:.4%})")

# ── Daily log-returns ──────────────────────────────────────────────────────────

def eq_to_pnl(eq: np.ndarray) -> np.ndarray:
    r = np.diff(np.log(np.where(eq > 0, eq, 1e-10)))
    return np.concatenate([[0.0], r])

pnl_k198  = eq_to_pnl(eq_k198)
pnl_k208  = eq_to_pnl(eq_k208)
pnl_k276b = eq_to_pnl(eq_k276b)
pnl_k270  = eq_to_pnl(eq_k270)
pnl_k275  = eq_to_pnl(eq_k275)

LABELS  = ["K198", "K208", "K276b", "K270", "K275"]
PNLS_5  = [pnl_k198, pnl_k208, pnl_k276b, pnl_k270, pnl_k275]
PNLS_3  = [pnl_k198, pnl_k208, pnl_k276b]   # K280 3-way baseline

# ── Metric helpers ─────────────────────────────────────────────────────────────

ANN = 365.0

def sharpe(pnl: np.ndarray) -> float:
    p = np.array(pnl, dtype=float)
    sd = np.std(p, ddof=1)
    return float(p.mean() / sd * math.sqrt(ANN)) if sd > 1e-12 else 0.0

def maxdd(eq: np.ndarray) -> float:
    rm = np.maximum.accumulate(eq)
    return float(np.min((eq - rm) / np.where(rm > 0, rm, 1e-10)))

def ann_ret(eq: np.ndarray) -> float:
    return float((eq[-1] / eq[0]) ** (ANN / len(eq)) - 1)

def ann_vol(pnl: np.ndarray) -> float:
    return float(np.std(pnl, ddof=1) * math.sqrt(ANN))

def metrics(pnl: np.ndarray) -> dict:
    eq = np.exp(np.cumsum(pnl))
    eq = eq / eq[0]
    return {
        "sharpe":   round(sharpe(pnl), 4),
        "max_dd":   round(maxdd(eq), 6),
        "ann_ret":  round(ann_ret(eq), 6),
        "ann_vol":  round(ann_vol(pnl), 6),
        "win_rate": round(float(np.mean(pnl > 0)), 4),
        "n_days":   int(len(pnl)),
    }

# ── Allocators ─────────────────────────────────────────────────────────────────

def inv_vol_weights(pnl_list: list, caps: dict | None = None) -> np.ndarray:
    vols = np.array([np.std(p, ddof=1) for p in pnl_list])
    vols = np.where(vols < 1e-12, 1e-12, vols)
    w = 1.0 / vols
    w = w / w.sum()
    if caps:
        for _ in range(400):
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

def mvp_weights(pnl_list: list, caps: dict | None = None) -> np.ndarray:
    """Minimum variance portfolio via closed-form (pseudo-inverse)."""
    R = np.column_stack(pnl_list)
    cov = np.cov(R.T, ddof=1)
    n = len(pnl_list)
    try:
        cov_inv = np.linalg.pinv(cov)
        ones = np.ones(n)
        w = cov_inv @ ones
        w = w / w.sum()
        # Clip negatives (long-only)
        w = np.clip(w, 0.0, None)
        if w.sum() < 1e-12:
            w = np.ones(n) / n
        else:
            w = w / w.sum()
    except Exception:
        w = np.ones(n) / n
    return w

def portfolio_pnl(pnls: list, weights: np.ndarray) -> np.ndarray:
    return sum(w * np.array(p) for w, p in zip(weights, pnls))

# ── 5x5 Correlation matrix ─────────────────────────────────────────────────────

print(f"\n=== 5x5 Correlation matrix ({N_WIN}-day genuine overlap) ===")
corr_5x5: dict[str, dict[str, float]] = {}
for i, si in enumerate(LABELS):
    corr_5x5[si] = {}
    for j, sj in enumerate(LABELS):
        c = float(np.corrcoef(PNLS_5[i], PNLS_5[j])[0, 1])
        corr_5x5[si][sj] = round(c, 4)
    print(f"  {si}: " + "  ".join(f"{LABELS[j]}={corr_5x5[si][LABELS[j]]:+.4f}" for j in range(5)))

rho_k270_k275 = corr_5x5["K270"]["K275"]
print(f"\n  KEY: rho(K270,K275) = {rho_k270_k275:+.4f}  (inter-carry correlation)")

# ── K280 55d baseline (critical reference, consistent with K282) ───────────────

OOS_DAYS = 18   # consistent with K282 measurement
IS_DAYS  = N_WIN - OOS_DAYS

w_k280_full = inv_vol_weights(PNLS_3)
pnl_k280_full = portfolio_pnl(PNLS_3, w_k280_full)
m_k280_full   = metrics(pnl_k280_full)

w_k280_oos = inv_vol_weights([p[:IS_DAYS] for p in PNLS_3])
m_k280_oos = metrics(portfolio_pnl([p[IS_DAYS:] for p in PNLS_3], w_k280_oos))
K280_55D_OOS_SH = m_k280_oos["sharpe"]

# Use the K282-measured baseline (30.58) as primary reference per task spec
K280_BASELINE_SPEC = 30.58
THRESHOLD_OOS_SH   = K280_BASELINE_SPEC + 1.0   # 31.58

print(f"\n=== K280 3-way baseline on {N_WIN}d overlap (re-computed) ===")
print(f"  Full-window  Sh={m_k280_full['sharpe']:.4f}  MDD={m_k280_full['max_dd']:.6f}")
print(f"  Pseudo-OOS ({OOS_DAYS}d) Sh={K280_55D_OOS_SH:.4f}  MDD={m_k280_oos['max_dd']:.6f}")
print(f"  Spec baseline (from K282): {K280_BASELINE_SPEC:.2f}  → threshold: {THRESHOLD_OOS_SH:.2f}")

# ── Variant definitions ────────────────────────────────────────────────────────
# K270 index=3, K275 index=4

VARIANT_DEFS: dict[str, dict] = {
    "K286a": {
        "type":  "inv_vol",
        "caps":  {3: 0.10, 4: 0.05},   # K270≤10%, K275≤5%
        "label": "Inv-vol + K270 cap10% + K275 cap5%",
    },
    "K286b": {
        "type":  "inv_vol",
        "caps":  {3: 0.10, 4: 0.10},   # K270≤10%, K275≤10%
        "label": "Inv-vol + K270 cap10% + K275 cap10%",
    },
    "K286c": {
        "type":  "inv_vol",
        "caps":  None,
        "label": "Inv-vol uncapped",
    },
    "K286d": {
        "type":  "mvp",
        "caps":  None,
        "label": "MVP (min-variance)",
    },
}

def make_weights_5way(pnl_list: list, variant: str) -> np.ndarray:
    vdef = VARIANT_DEFS[variant]
    if vdef["type"] == "mvp":
        return mvp_weights(pnl_list)
    return inv_vol_weights(pnl_list, caps=vdef["caps"])

# ── Walk-forward 2-fold ────────────────────────────────────────────────────────

N_FOLDS   = 2
fold_size = N_WIN // N_FOLDS

print(f"\n=== Walk-forward 2-fold evaluation (K286 5-way variants) ===")
print(f"  N={N_WIN} days, {N_FOLDS} folds of ~{fold_size}d each")

VARIANTS = list(VARIANT_DEFS.keys())
variant_results: dict[str, dict] = {}

for vname in VARIANTS:
    fold_list = []
    for fi in range(N_FOLDS):
        s = fi * fold_size
        e = (fi + 1) * fold_size if fi < N_FOLDS - 1 else N_WIN
        is_mask = list(range(0, s)) + list(range(e, N_WIN))

        pnl_oos = [p[s:e] for p in PNLS_5]
        pnl_is  = [p[is_mask] for p in PNLS_5]

        w_fold   = make_weights_5way(pnl_is, vname)
        pnl_port = portfolio_pnl(pnl_oos, w_fold)
        fm = metrics(pnl_port)
        fm["fold"]       = fi + 1
        fm["start_date"] = overlap_dates[s]
        fm["end_date"]   = overlap_dates[e - 1]
        fm["weights"]    = {LABELS[i]: round(float(w_fold[i]), 4) for i in range(5)}
        fold_list.append(fm)

    fold_sharpes = [f["sharpe"] for f in fold_list]
    wf_min  = float(np.min(fold_sharpes))
    wf_mean = float(np.mean(fold_sharpes))
    all_pos = bool(all(s > 0 for s in fold_sharpes))

    # Pseudo-OOS: train on first IS_DAYS, test on last OOS_DAYS
    w_oos     = make_weights_5way([p[:IS_DAYS] for p in PNLS_5], vname)
    m_oos     = metrics(portfolio_pnl([p[IS_DAYS:] for p in PNLS_5], w_oos))
    oos_sh    = m_oos["sharpe"]
    k270_w    = float(w_oos[3])
    k275_w    = float(w_oos[4])

    g1 = oos_sh > THRESHOLD_OOS_SH
    g2 = all_pos
    g3 = k270_w > 0.0 and k275_w > 0.0   # both non-zero

    variant_results[vname] = {
        "label":        VARIANT_DEFS[vname]["label"],
        "oos_sharpe":   round(oos_sh, 4),
        "oos_maxdd":    m_oos["max_dd"],
        "oos_ann_ret":  m_oos["ann_ret"],
        "oos_ann_vol":  m_oos["ann_vol"],
        "wf_mean":      round(wf_mean, 4),
        "wf_min":       round(wf_min, 4),
        "wf_all_pos":   all_pos,
        "oos_weights":  {LABELS[i]: round(float(w_oos[i]), 4) for i in range(5)},
        "k270_weight":  round(k270_w, 4),
        "k275_weight":  round(k275_w, 4),
        "fold_details": fold_list,
        "gates": {
            "g1_oos_sh_gt_31.58":        bool(g1),
            "g2_wf_all_pos":             bool(g2),
            "g3_k270_and_k275_nonzero":  bool(g3),
            "threshold_oos_sh":          round(THRESHOLD_OOS_SH, 4),
            "all_pass":                  bool(g1 and g2 and g3),
        },
    }

    status = "PASS" if (g1 and g2 and g3) else "FAIL"
    w_str  = " ".join(f"{LABELS[i]}={w_oos[i]:.3f}" for i in range(5))
    print(f"  {vname} ({VARIANT_DEFS[vname]['label']}):")
    print(f"    OOS_Sh={oos_sh:.4f}  WF_min={wf_min:.4f}  K270w={k270_w:.3f}  K275w={k275_w:.3f}  [{w_str}]  {status}")
    for fd in fold_list:
        print(f"    Fold {fd['fold']} [{fd['start_date']}→{fd['end_date']}]: Sh={fd['sharpe']:.4f}  MDD={fd['max_dd']:.6f}")

# ── Summary ────────────────────────────────────────────────────────────────────

accepted = [v for v, r in variant_results.items() if r["gates"]["all_pass"]]
best_var = max(
    variant_results,
    key=lambda v: variant_results[v]["oos_sharpe"] if variant_results[v]["wf_all_pos"] else -999,
)
best_sh = variant_results[best_var]["oos_sharpe"]

print(f"\n=== K286 acceptance summary ===")
print(f"  Overlap window: {N_WIN}d ({OVL_START} → {OVL_END})")
print(f"  K280 55d baseline OOS Sh (spec): {K280_BASELINE_SPEC:.2f}  threshold: {THRESHOLD_OOS_SH:.2f}")
print(f"  Passed all gates: {accepted if accepted else 'NONE'}")
print(f"  Best by OOS_Sh: {best_var}  (OOS_Sh={best_sh:.4f})")

# ── Synergy analysis vs K282 / K284 ──────────────────────────────────────────
# K282 best: K282b OOS_Sh=28.43 (K275-only add)
# K284 best: K284b OOS_Sh=19.21 (K270-only add, 448d window — not directly comparable)
# For synergy, compare best 5-way vs K280 baseline on same 55d

SYNERGY_K282_BEST = 28.4307   # K282b on 55d
SYNERGY_K284_55D  = None      # K284 used 448d window — no direct 55d comparison
synergy_delta_vs_k280    = round(best_sh - K280_BASELINE_SPEC, 4)
synergy_delta_vs_k282b   = round(best_sh - SYNERGY_K282_BEST, 4)

print(f"\n=== Synergy analysis ===")
print(f"  K280 55d baseline:    {K280_BASELINE_SPEC:.4f}")
print(f"  K282 best (K275-only): {SYNERGY_K282_BEST:.4f}")
print(f"  K286 best (5-way):    {best_sh:.4f}")
print(f"  K286 vs K280 delta:   {synergy_delta_vs_k280:+.4f}")
print(f"  K286 vs K282b delta:  {synergy_delta_vs_k282b:+.4f}")
has_synergy = synergy_delta_vs_k282b > 0
print(f"  Synergy over K282:    {'YES' if has_synergy else 'NO'}")

# ── Build equity curves output ─────────────────────────────────────────────────

def build_equity(pnls: list, w: np.ndarray) -> list:
    pnl = portfolio_pnl(pnls, w)
    eq  = np.exp(np.cumsum(pnl))
    eq  = eq / eq[0]
    return [round(float(x), 8) for x in eq.tolist()]

w_k280_3way = inv_vol_weights(PNLS_3)

curves_out: dict = {
    "wave":         "K286",
    "dates":        overlap_dates,
    "window_start": OVL_START,
    "window_end":   OVL_END,
    "n_days":       N_WIN,
    "note":         (f"Genuine 5-way overlap: {N_WIN} days ({OVL_START} → {OVL_END}). "
                     f"Entirely within K275 IS period. rho(K270,K275)={rho_k270_k275:+.4f}."),
    "K198":         [round(float(x), 8) for x in eq_k198.tolist()],
    "K208":         [round(float(x), 8) for x in eq_k208.tolist()],
    "K276b":        [round(float(x), 8) for x in eq_k276b.tolist()],
    "K270":         [round(float(x), 8) for x in eq_k270.tolist()],
    "K275":         [round(float(x), 8) for x in eq_k275.tolist()],
    "K280_3way":    build_equity(PNLS_3, w_k280_3way),
}

for vname in VARIANTS:
    w_full = make_weights_5way(PNLS_5, vname)
    curves_out[vname] = build_equity(PNLS_5, w_full)
    curves_out[f"{vname}_weights"] = {LABELS[i]: round(float(w_full[i]), 4) for i in range(5)}

# ── Save outputs ───────────────────────────────────────────────────────────────

runtime = round(time.time() - START, 2)
print(f"\nRuntime: {runtime:.1f}s")

class NpEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, np.bool_):    return bool(obj)
        if isinstance(obj, np.integer):  return int(obj)
        if isinstance(obj, np.floating): return float(obj)
        return super().default(obj)

results_out = {
    "wave":      "K286",
    "task":      "K198+K208+K276b+K270+K275 5-way Meta Ensemble (55-day overlap)",
    "as_of":     datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ"),
    "runtime_s": runtime,

    "data_info": {
        "n_days_overlap":  N_WIN,
        "date_start":      OVL_START,
        "date_end":        OVL_END,
        "components":      LABELS,
        "n_folds":         N_FOLDS,
        "oos_days":        OOS_DAYS,
        "caveat_data": (
            f"K280 ends {dk280['dates'][-1]}; K270 ends {dk270['dates'][-1]}; "
            f"K275 covers {dk275['dates'][0]}→{dk275['dates'][-1]}. "
            f"Genuine 5-way overlap = {N_WIN}d. Entirely within K275 IS period."
        ),
    },

    "k280_55d_baseline": {
        "source":        "K280 v6.10.2 PRODUCTION (K198+K208+K276b_top20)",
        "recomputed_sh": round(K280_55D_OOS_SH, 4),
        "spec_sh":       K280_BASELINE_SPEC,
        "oos_days":      OOS_DAYS,
        "threshold":     THRESHOLD_OOS_SH,
        "note":          "Spec baseline from K282 = 30.58. Acceptance gate = 31.58.",
    },

    "correlation_matrix_5x5": corr_5x5,

    "key_correlations": {
        "rho_k270_k275":  corr_5x5["K270"]["K275"],
        "rho_k270_k276b": corr_5x5["K270"]["K276b"],
        "rho_k275_k276b": corr_5x5["K275"]["K276b"],
        "rho_k270_k198":  corr_5x5["K270"]["K198"],
        "rho_k270_k208":  corr_5x5["K270"]["K208"],
        "rho_k275_k198":  corr_5x5["K275"]["K198"],
        "rho_k275_k208":  corr_5x5["K275"]["K208"],
    },

    "variant_results": variant_results,

    "best_variant": best_var,

    "acceptance": {
        "threshold_oos_sh":    THRESHOLD_OOS_SH,
        "baseline_oos_sh":     K280_BASELINE_SPEC,
        "accepted_variants":   accepted,
        "best_variant":        best_var,
        "best_oos_sh":         best_sh,
        "provisional_verdict": "ACCEPT_PROVISIONAL" if accepted else "FAIL",
        "gates_description": [
            f"G1: OOS Sh > {THRESHOLD_OOS_SH:.2f} (K280 baseline {K280_BASELINE_SPEC:.2f} + 1.0)",
            "G2: WF 2-fold all positive",
            "G3: K270 AND K275 weights both non-zero",
            "Mandatory: 30d paper trade before production",
        ],
    },

    "synergy_analysis": {
        "k280_55d_baseline":       K280_BASELINE_SPEC,
        "k282b_best_55d":          SYNERGY_K282_BEST,
        "k284_note":               "K284 tested on 448d window — no direct 55d comparison available",
        "k286_best_5way":          best_sh,
        "delta_vs_k280":           synergy_delta_vs_k280,
        "delta_vs_k282b":          synergy_delta_vs_k282b,
        "synergy_over_k282":       has_synergy,
        "interpretation": (
            f"K286 5-way achieves OOS Sh {best_sh:.4f} vs K282b (K275-only) {SYNERGY_K282_BEST:.4f}. "
            f"{'Positive synergy detected: joint K270+K275 outperforms K275 alone.' if has_synergy else 'No synergy: K275 alone (K282) outperforms joint addition.'}"
        ),
    },

    "caveats": [
        f"Genuine 5-way overlap is only {N_WIN} days — insufficient for robust statistics",
        "K280 curves end 2026-04-14; entire overlap falls within K275 IS period (NO true 5-way OOS)",
        "2-fold WF on 55d = two ~27d periods. Statistical power is extremely low.",
        "K270 on 55d overlap window may differ from its 448d behaviour",
        "K270 and K275 both carry strategies — rho(K270,K275) instability possible",
        "DO NOT promote to production without paper trade AND independent OOS extension",
    ],
}

with open(BASE / "wave_k286_5way_provisional.json", "w") as f:
    json.dump(results_out, f, indent=2, cls=NpEncoder)
print("Saved wave_k286_5way_provisional.json")

with open(BASE / "wave_k286_curves.json", "w") as f:
    json.dump(curves_out, f, indent=2, cls=NpEncoder)
print("Saved wave_k286_curves.json")

# ── Markdown report (<70 lines) ────────────────────────────────────────────────

def corr_row(si: str) -> str:
    return "| " + si + " | " + " | ".join(f"{corr_5x5[si][sj]:+.3f}" for sj in LABELS) + " |"

def verdict_line(vname: str) -> str:
    r = variant_results[vname]
    g = r["gates"]
    st = "PASS" if g["all_pass"] else "FAIL"
    return (f"| {vname} | {r['label']} | {r['oos_sharpe']:.2f} | "
            f"{r['wf_min']:.2f} | {r['k270_weight']:.3f} | {r['k275_weight']:.3f} | "
            f"{r['wf_all_pos']} | {st} |")

accept_str = ", ".join(accepted) if accepted else "NONE"
verdict    = "ACCEPT_PROVISIONAL" if accepted else "FAIL"

md = f"""# Wave K286: 5-way Meta Ensemble (K198+K208+K276b+K270+K275)
Generated: {datetime.utcnow().strftime('%Y-%m-%d %H:%M UTC')} | Runtime: {runtime:.1f}s

## Setup
- Window: {OVL_START} → {OVL_END} ({N_WIN} days, genuine 5-way overlap)
- K280 55d baseline OOS Sh: {K280_BASELINE_SPEC:.2f} | Acceptance gate: **{THRESHOLD_OOS_SH:.2f}**
- 2-fold WF, OOS_DAYS={OOS_DAYS}

## 5x5 Correlation Matrix ({N_WIN}-day overlap)

| | K198 | K208 | K276b | K270 | K275 |
|---|---|---|---|---|---|
{chr(10).join(corr_row(si) for si in LABELS)}

KEY: rho(K270,K275)={rho_k270_k275:+.3f} | rho(K270,K276b)={corr_5x5['K270']['K276b']:+.3f} | rho(K275,K276b)={corr_5x5['K275']['K276b']:+.3f}

## Variant Results

| Variant | Description | OOS Sh | WF Min | K270 wt | K275 wt | WF All+ | Gate |
|---------|-------------|--------|--------|---------|---------|---------|------|
| K280 (baseline) | 3-way {N_WIN}d | {K280_BASELINE_SPEC:.2f} | — | — | — | — | BASELINE |
{chr(10).join(verdict_line(v) for v in VARIANTS)}

## Fold Details (2-fold, ~{fold_size}d each)

| Variant | Fold | Start | End | Sharpe | MaxDD |
|---------|------|-------|-----|--------|-------|
{"".join("| " + v + " | " + str(fd['fold']) + " | " + fd['start_date'] + " | " + fd['end_date'] + " | " + f"{fd['sharpe']:.2f}" + " | " + f"{fd['max_dd']:.6f}" + " |" + chr(10) for v in VARIANTS for fd in variant_results[v]['fold_details'])}
## OOS Weights

| Variant | K198 | K208 | K276b | K270 | K275 |
|---------|------|------|-------|------|------|
{"".join("| " + v + " | " + " | ".join(f"{variant_results[v]['oos_weights'][l]:.3f}" for l in LABELS) + " |" + chr(10) for v in VARIANTS)}
## Synergy Analysis (K286 vs K284 vs K282)

| Ensemble | Window | OOS Sh | vs K280 |
|----------|--------|--------|---------|
| K280 baseline | 55d | {K280_BASELINE_SPEC:.2f} | 0.00 |
| K282b (K275 only) | 55d | {SYNERGY_K282_BEST:.2f} | {SYNERGY_K282_BEST - K280_BASELINE_SPEC:+.2f} |
| K284b (K270 only) | 448d | 19.21 | N/A (different window) |
| K286 best ({best_var}) | 55d | {best_sh:.2f} | {synergy_delta_vs_k280:+.2f} |

K286 vs K282b delta: **{synergy_delta_vs_k282b:+.4f}** — {'Synergy CONFIRMED' if has_synergy else 'No synergy over K275-alone'}

## Acceptance Summary

- Accepted variants: **{accept_str}**
- Best: **{best_var}** (OOS Sh = {best_sh:.4f})
- Verdict: **{verdict}**

## Provisional Verdict + 30d Paper Trade Plan

**Verdict: {verdict}**

{'Accepted variant: ' + accept_str if accepted else 'No variant cleared all three gates.'}

**30d paper trade plan (mandatory):**
1. Shadow-deploy {best_var} alongside K280 v6.10.2 from today (2026-05-25)
2. Track daily PnL for K286 vs K280 on live data (true OOS from 2026-04-15)
3. After 30d: require K286 Sharpe >= K280 Sharpe + 0.5 on same 30d window
4. Monitor K270 weight (must remain > 0%) and K275 weight (must remain > 0%)
5. Alert if rho(K270,K275) rolling 30d exceeds 0.5 (carry crowding signal)
6. Alert if rho(K275,K276b) rolling 30d exceeds 0.4 (diversification loss)
7. Promotion to v6.11 ONLY after paper trade passes AND both OOS windows ≥ 60d
8. Revisit K270+K275 combo on extended K280 curves once available (post-2026-06-15)
"""

with open(BASE / "wave_k286_5way_provisional.md", "w") as f:
    f.write(md)
print("Saved wave_k286_5way_provisional.md")

print(f"\n=== K286 COMPLETE ({runtime:.1f}s) ===")
print(f"  Overlap window: {N_WIN}d ({OVL_START} → {OVL_END})")
print(f"  K280 55d baseline: {K280_BASELINE_SPEC:.2f}  threshold: {THRESHOLD_OOS_SH:.2f}")
print(f"  Accepted variants: {accepted if accepted else 'NONE'}")
print(f"  Best: {best_var} (OOS Sh={best_sh:.4f})")
print(f"  Synergy vs K282b: {synergy_delta_vs_k282b:+.4f}")

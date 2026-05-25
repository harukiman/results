"""
Wave K282 — K280 + K275 4-way Meta Ensemble (55-day overlap window)
===================================================================
K280 = K198+K208+K276b_top20 (3-way, v6.10.2 PRODUCTION, OOS Sh 18.46)
K275 = OKX FR Carry (ACCEPT 8/8, OOS Sh 30.25, ρ vs K265 = -0.529)
Objective: Test whether adding K275 to K280 lifts ensemble Sh by +1.0
           on the genuine 55-day overlap window (2026-02-19 → 2026-04-14).

DATA REALITY (critical):
  K280 sources (K198/K208/K276b): 2025-01-22 → 2026-04-14 (448 days)
  K275:                           2026-02-19 → 2026-05-25 (96 days)
  Genuine 4-way overlap:          2026-02-19 → 2026-04-14 (55 days)

  The 55-day overlap falls entirely within K275's IS period
  (K275 OOS starts 2026-04-28). No simultaneous 4-way OOS window exists.

Variants:
  K282a: Inv-vol uncapped
  K282b: Inv-vol + K275 cap 15%
  K282c: Inv-vol + K275 cap 25%
  K282d: Equal weight 25/25/25/25

Acceptance (provisional, subject to paper trade):
  - 55d OOS Sh > K280_55d_baseline + 1.0
  - WF 2-fold all positive
  - K275 contribution > 5%
  - All caveats acknowledged
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

# ── Load data ─────────────────────────────────────────────────────────────────

with open(BASE / "wave_k280_curves.json") as f:
    dk280 = json.load(f)

with open(BASE / "wave_k275_curves.json") as f:
    dk275 = json.load(f)

print("=== K282: K280 + K275 4-way Meta Ensemble ===")
print(f"K280 window:     {dk280['dates'][0]} → {dk280['dates'][-1]} ({len(dk280['dates'])} days)")
print(f"K275 window:     {dk275['dates'][0]} → {dk275['dates'][-1]} ({len(dk275['dates'])} days)")

# ── Find genuine overlap window ───────────────────────────────────────────────

k280_date_set = set(dk280["dates"])
k275_dates    = dk275["dates"]

overlap_dates = [d for d in k275_dates if d in k280_date_set]
N_WIN         = len(overlap_dates)
OVL_START     = overlap_dates[0]
OVL_END       = overlap_dates[-1]

print(f"Genuine overlap: {OVL_START} → {OVL_END} ({N_WIN} days)")
print(f"NOTE: Overlap is entirely within K275 IS period (K275 OOS starts 2026-04-28)")

# ── Slice curves to overlap window ────────────────────────────────────────────

k280_idx = {d: i for i, d in enumerate(dk280["dates"])}
k275_idx = {d: i for i, d in enumerate(k275_dates)}

def slice_eq(eq_list: list, date_map: dict, target: list) -> np.ndarray:
    return np.array([eq_list[date_map[d]] for d in target], dtype=float)

# K198, K208, K276b from K280 curves (normalized to overlap window start)
eq_k198_raw  = slice_eq(dk280["K198"],     k280_idx, overlap_dates)
eq_k208_raw  = slice_eq(dk280["K208"],     k280_idx, overlap_dates)
eq_k276b_raw = slice_eq(dk280["K276b_win"], k280_idx, overlap_dates)
eq_k275_raw  = slice_eq(dk275["equity"],   k275_idx, overlap_dates)

# Re-normalize each to 1.0 at start of overlap window
def renorm(eq: np.ndarray) -> np.ndarray:
    return eq / eq[0]

eq_k198  = renorm(eq_k198_raw)
eq_k208  = renorm(eq_k208_raw)
eq_k276b = renorm(eq_k276b_raw)
eq_k275  = renorm(eq_k275_raw)

assert len(eq_k198) == N_WIN == len(eq_k208) == len(eq_k276b) == len(eq_k275), "Length mismatch"

print(f"\nEquity ranges on {N_WIN}d overlap (re-normalized to 1.0):")
for name, eq in [("K198", eq_k198), ("K208", eq_k208), ("K276b", eq_k276b), ("K275", eq_k275)]:
    print(f"  {name}: {eq[0]:.4f} → {eq[-1]:.4f}  (total ret {eq[-1]/eq[0]-1:.4%})")

# ── Daily log-returns ─────────────────────────────────────────────────────────

def eq_to_pnl(eq: np.ndarray) -> np.ndarray:
    r = np.diff(np.log(np.where(eq > 0, eq, 1e-10)))
    return np.concatenate([[0.0], r])

pnl_k198  = eq_to_pnl(eq_k198)
pnl_k208  = eq_to_pnl(eq_k208)
pnl_k276b = eq_to_pnl(eq_k276b)
pnl_k275  = eq_to_pnl(eq_k275)

LABELS  = ["K198", "K208", "K276b", "K275"]
PNLS_4  = [pnl_k198, pnl_k208, pnl_k276b, pnl_k275]
PNLS_3  = [pnl_k198, pnl_k208, pnl_k276b]   # K280 3-way (on overlap window)

# ── Metric helpers ────────────────────────────────────────────────────────────

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

# ── Allocators ────────────────────────────────────────────────────────────────

def inv_vol_weights(pnl_list: list, caps: dict | None = None) -> np.ndarray:
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

def equal_weights(n: int) -> np.ndarray:
    return np.ones(n) / n

def portfolio_pnl(pnls: list, weights: np.ndarray) -> np.ndarray:
    return sum(w * np.array(p) for w, p in zip(weights, pnls))

# ── 4x4 Correlation matrix ────────────────────────────────────────────────────

print(f"\n=== 4x4 Correlation matrix ({N_WIN}-day genuine overlap) ===")
corr_4x4: dict[str, dict[str, float]] = {}
for i, si in enumerate(LABELS):
    corr_4x4[si] = {}
    for j, sj in enumerate(LABELS):
        c = float(np.corrcoef(PNLS_4[i], PNLS_4[j])[0, 1])
        corr_4x4[si][sj] = round(c, 4)
    print(f"  {si}: " + "  ".join(f"{LABELS[j]}={corr_4x4[si][LABELS[j]]:+.4f}" for j in range(4)))

# ── K280 baseline on 55-day overlap window (PRIMARY COMPARISON) ──────────────
# Pseudo-OOS: last OOS_DAYS (1/3 of 55d), IS = first IS_DAYS

OOS_DAYS = 18   # ~1/3 of 55d — consistent with K277 methodology
IS_DAYS  = N_WIN - OOS_DAYS

w_k280_full = inv_vol_weights(PNLS_3)
pnl_k280_full = portfolio_pnl(PNLS_3, w_k280_full)
m_k280_full   = metrics(pnl_k280_full)

w_k280_oos = inv_vol_weights([p[:IS_DAYS] for p in PNLS_3])
m_k280_oos = metrics(portfolio_pnl([p[IS_DAYS:] for p in PNLS_3], w_k280_oos))
K280_55D_OOS_SH = m_k280_oos["sharpe"]

print(f"\n=== K280 3-way baseline on {N_WIN}d overlap window (PRIMARY HEADER) ===")
print(f"  Full-window  Sh={m_k280_full['sharpe']:.4f}  MDD={m_k280_full['max_dd']:.6f}  AnnRet={m_k280_full['ann_ret']:.4f}")
print(f"  Pseudo-OOS ({OOS_DAYS}d) Sh={K280_55D_OOS_SH:.4f}  MDD={m_k280_oos['max_dd']:.6f}  AnnRet={m_k280_oos['ann_ret']:.4f}")
print(f"  Weights: " + " ".join(f"{LABELS[i]}={w_k280_full[i]:.4f}" for i in range(3)))
print(f"  K282 acceptance threshold: {K280_55D_OOS_SH:.4f} + 1.0 = {K280_55D_OOS_SH + 1.0:.4f}")
print(f"  (K280 production OOS Sh = 18.46 on 448d — not comparable here)")

# ── K282 variant definitions ──────────────────────────────────────────────────

VARIANT_DEFS: dict[str, dict] = {
    "K282a": {"type": "inv_vol", "caps": None,      "label": "Inv-vol uncapped"},
    "K282b": {"type": "inv_vol", "caps": {3: 0.15}, "label": "Inv-vol + K275 cap 15%"},
    "K282c": {"type": "inv_vol", "caps": {3: 0.25}, "label": "Inv-vol + K275 cap 25%"},
    "K282d": {"type": "equal",   "caps": None,      "label": "Equal weight 25/25/25/25"},
}

def make_weights_4way(pnl_list: list, variant: str) -> np.ndarray:
    vdef = VARIANT_DEFS[variant]
    if vdef["type"] == "equal":
        return equal_weights(4)
    return inv_vol_weights(pnl_list, caps=vdef["caps"])

# ── Walk-forward 2-fold ───────────────────────────────────────────────────────
# 55d → 2 folds: fold 1 OOS = days 0–27, fold 2 OOS = days 27–54

N_FOLDS   = 2
fold_size = N_WIN // N_FOLDS  # 27

print(f"\n=== Walk-forward 2-fold evaluation (K282 4-way variants) ===")
print(f"  N={N_WIN} days, {N_FOLDS} folds of ~{fold_size}d each")

VARIANTS = list(VARIANT_DEFS.keys())
variant_results: dict[str, dict] = {}

for vname in VARIANTS:
    fold_list = []
    for fi in range(N_FOLDS):
        s = fi * fold_size
        e = (fi + 1) * fold_size if fi < N_FOLDS - 1 else N_WIN
        is_mask = list(range(0, s)) + list(range(e, N_WIN))

        pnl_oos = [p[s:e] for p in PNLS_4]
        pnl_is  = [p[is_mask] for p in PNLS_4]

        w_fold   = make_weights_4way(pnl_is, vname)
        pnl_port = portfolio_pnl(pnl_oos, w_fold)
        fm = metrics(pnl_port)
        fm["fold"]       = fi + 1
        fm["start_date"] = overlap_dates[s]
        fm["end_date"]   = overlap_dates[e - 1]
        fm["weights"]    = {LABELS[i]: round(float(w_fold[i]), 4) for i in range(4)}
        fold_list.append(fm)

    fold_sharpes = [f["sharpe"] for f in fold_list]
    wf_min  = float(np.min(fold_sharpes))
    wf_mean = float(np.mean(fold_sharpes))
    all_pos = bool(all(s > 0 for s in fold_sharpes))

    # Pseudo-OOS: last OOS_DAYS, IS = first IS_DAYS
    w_oos     = make_weights_4way([p[:IS_DAYS] for p in PNLS_4], vname)
    m_oos     = metrics(portfolio_pnl([p[IS_DAYS:] for p in PNLS_4], w_oos))
    oos_sh    = m_oos["sharpe"]
    k275_w    = float(w_oos[3])

    threshold = K280_55D_OOS_SH + 1.0
    g1 = oos_sh > threshold
    g2 = all_pos
    g3 = k275_w > 0.05

    variant_results[vname] = {
        "label":        VARIANT_DEFS[vname]["label"],
        "oos_sharpe":   round(oos_sh, 4),
        "oos_maxdd":    m_oos["max_dd"],
        "oos_ann_ret":  m_oos["ann_ret"],
        "oos_ann_vol":  m_oos["ann_vol"],
        "wf_mean":      round(wf_mean, 4),
        "wf_min":       round(wf_min, 4),
        "wf_all_pos":   all_pos,
        "weights_oos":  {LABELS[i]: round(float(w_oos[i]), 4) for i in range(4)},
        "k275_weight":  round(k275_w, 4),
        "fold_details": fold_list,
        "gates": {
            "g1_oos_sh_gt_baseline+1": bool(g1),
            "g2_wf_all_pos":           bool(g2),
            "g3_k275_contribution":    bool(g3),
            "threshold_oos_sh":        round(threshold, 4),
            "all_pass":                bool(g1 and g2 and g3),
        },
    }

    status = "PASS" if (g1 and g2 and g3) else "FAIL"
    w_str  = " ".join(f"{LABELS[i]}={w_oos[i]:.3f}" for i in range(4))
    print(f"  {vname} ({VARIANT_DEFS[vname]['label']}): OOS_Sh={oos_sh:.4f}  WF_min={wf_min:.4f}  "
          f"K275w={k275_w:.3f}  [{w_str}]  {status}")
    for fd in fold_list:
        print(f"    Fold {fd['fold']} [{fd['start_date']}→{fd['end_date']}]: Sh={fd['sharpe']:.4f}  MDD={fd['max_dd']:.6f}")

# ── Summary ───────────────────────────────────────────────────────────────────

accepted = [v for v, r in variant_results.items() if r["gates"]["all_pass"]]
best_var = max(variant_results, key=lambda v: variant_results[v]["oos_sharpe"] if variant_results[v]["wf_all_pos"] else -999)
best_sh  = variant_results[best_var]["oos_sharpe"]

print(f"\n=== K282 acceptance summary ===")
print(f"  Overlap window: {N_WIN}d ({OVL_START} → {OVL_END})")
print(f"  K280 {N_WIN}d baseline OOS Sh = {K280_55D_OOS_SH:.4f}  (threshold = {K280_55D_OOS_SH + 1.0:.4f})")
print(f"  Passed all gates: {accepted if accepted else 'NONE'}")
print(f"  Best by OOS_Sh: {best_var}  (OOS_Sh={best_sh:.4f})")

# ── Build equity curves output ────────────────────────────────────────────────

def build_equity(pnls: list, w: np.ndarray) -> list:
    pnl = portfolio_pnl(pnls, w)
    eq  = np.exp(np.cumsum(pnl))
    eq  = eq / eq[0]
    return [round(float(x), 8) for x in eq.tolist()]

w_k280_full_3 = inv_vol_weights(PNLS_3)  # K280 3-way full weights on overlap

curves_out: dict = {
    "wave":         "K282",
    "dates":        overlap_dates,
    "window_start": OVL_START,
    "window_end":   OVL_END,
    "n_days":       N_WIN,
    "note":         (f"Genuine 4-way overlap: all strategies have data on these {N_WIN} days. "
                     f"Overlap falls entirely within K275 IS period."),
    "K198":         [round(float(x), 8) for x in eq_k198.tolist()],
    "K208":         [round(float(x), 8) for x in eq_k208.tolist()],
    "K276b":        [round(float(x), 8) for x in eq_k276b.tolist()],
    "K275":         [round(float(x), 8) for x in eq_k275.tolist()],
    "K280_3way":    build_equity(PNLS_3, w_k280_full_3),
}

for vname in VARIANTS:
    w_full = make_weights_4way(PNLS_4, vname)
    curves_out[vname] = build_equity(PNLS_4, w_full)
    curves_out[f"{vname}_weights"] = {LABELS[i]: round(float(w_full[i]), 4) for i in range(4)}

# ── Save outputs ──────────────────────────────────────────────────────────────

runtime = round(time.time() - START, 2)
print(f"\nRuntime: {runtime:.1f}s")

class NpEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, np.bool_):    return bool(obj)
        if isinstance(obj, np.integer):  return int(obj)
        if isinstance(obj, np.floating): return float(obj)
        return super().default(obj)

results_out = {
    "wave":      "K282",
    "task":      "K280 + K275 4-way Meta Ensemble (55-day overlap)",
    "as_of":     datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ"),
    "runtime_s": runtime,

    "data_info": {
        "n_days_overlap":   N_WIN,
        "date_start":       OVL_START,
        "date_end":         OVL_END,
        "components":       LABELS,
        "n_folds":          N_FOLDS,
        "oos_days":         OOS_DAYS,
        "caveat_data": (
            f"K280 curves end {dk280['dates'][-1]}; K275 covers {k275_dates[0]}→{k275_dates[-1]}. "
            f"Genuine 4-way overlap = {N_WIN}d. Overlap falls entirely within K275 IS period "
            "(K275 OOS starts 2026-04-28). NO simultaneous 4-way OOS window exists."
        ),
    },

    "k280_55d_baseline": {
        "source":       "K280 v6.10.2 PRODUCTION (K198+K208+K276b_top20)",
        "full_sharpe":  m_k280_full["sharpe"],
        "full_maxdd":   m_k280_full["max_dd"],
        "oos_sharpe":   round(K280_55D_OOS_SH, 4),
        "oos_days":     OOS_DAYS,
        "oos_maxdd":    m_k280_oos["max_dd"],
        "weights":      {LABELS[i]: round(float(w_k280_full[i]), 4) for i in range(3)},
        "production_oos_sh_448d": 18.46,
        "note": (f"K280 (3-way) on genuine {N_WIN}d overlap window. "
                 "NOT comparable to production 448d OOS Sh=18.46."),
    },

    "k275_source_metrics": {
        "oos_sharpe_96d":  30.25,
        "wf_min_sharpe":   5.94,
        "correlations_k275_96d": {"K198": -0.018, "K208": -0.076, "K265": -0.529},
        "n_days_total":    96,
        "n_days_oos":      28,
        "n_gates_passed":  8,
        "note": "From wave_k275_okx_fr.json (ACCEPT 8/8). OOS 2026-04-28→2026-05-25 NOT in overlap.",
    },

    "correlation_matrix_4x4": corr_4x4,

    "variant_results": variant_results,

    "acceptance": {
        "threshold_oos_sh":    round(K280_55D_OOS_SH + 1.0, 4),
        "baseline_oos_sh":     round(K280_55D_OOS_SH, 4),
        "accepted_variants":   accepted,
        "best_variant":        best_var,
        "best_oos_sh":         best_sh,
        "provisional_verdict": "ACCEPT_PROVISIONAL" if accepted else "FAIL",
        "conditions": [
            f"55d OOS Sh > K280_55d ({K280_55D_OOS_SH:.4f}) + 1.0 = {K280_55D_OOS_SH + 1.0:.4f}",
            "WF 2-fold all positive",
            "K275 weight > 5%",
            "CAVEAT: 55d overlap is insufficient for robust production validation",
            "Final acceptance pending paper trade (K275 OOS extension to 2026-06-25+)",
        ],
    },

    "vs_k277_comparison": {
        "k277_baseline_used":    "K272a (K198+K208+K265)",
        "k282_baseline_used":    "K280 (K198+K208+K276b_top20)",
        "k277_best_oos_sh_55d":  25.1408,
        "k282_best_oos_sh_55d":  best_sh,
        "key_diff":              "K282 uses K276b (Sh=17.20 on 448d) instead of K265 (Sh=8.42)",
        "note":                  "K277 was PROVISIONAL on K272a; K282 tests K280-level integration",
    },

    "caveats": [
        f"Genuine 4-way overlap is only {N_WIN} days — insufficient for robust statistics",
        "K280 curves end 2026-04-14; K275 OOS (28d, 2026-04-28→2026-05-25) has NO K198/K208/K276b counterpart",
        "All 55 overlap days fall within K275's in-sample period — NO true 4-way OOS",
        "K280 55d Sharpe differs substantially from 448d production Sh=18.46",
        "2-fold WF on 55d = two ~27d periods. Statistical power is extremely low.",
        "K275 OOS Sh=30.25 measured on 28 days only — regime-specific, not robust",
        "ρ(K275,K276b) on 55d may differ from longer-window correlation",
        "DO NOT promote to production without paper trade AND K275 OOS extension ≥60d",
    ],
}

with open(BASE / "wave_k282_4way_k280_k275.json", "w") as f:
    json.dump(results_out, f, indent=2, cls=NpEncoder)
print("Saved wave_k282_4way_k280_k275.json")

with open(BASE / "wave_k282_curves.json", "w") as f:
    json.dump(curves_out, f, indent=2, cls=NpEncoder)
print("Saved wave_k282_curves.json")

# ── Markdown report ───────────────────────────────────────────────────────────

def verdict_line(vname: str) -> str:
    r = variant_results[vname]
    g = r["gates"]
    st = "PASS" if g["all_pass"] else "FAIL"
    return (f"| {vname} | {r['label']} | {r['oos_sharpe']:.2f} | "
            f"{r['wf_min']:.2f} | {r['k275_weight']:.3f} | "
            f"{r['wf_all_pos']} | {st} |")

fold_rows = []
for vname in VARIANTS:
    for fd in variant_results[vname]["fold_details"]:
        fold_rows.append(
            f"| {vname} | {fd['fold']} | {fd['start_date']} | {fd['end_date']} | "
            f"{fd['sharpe']:.2f} | {fd['max_dd']:.6f} |"
        )

def corr_row(si):
    return "| " + si + " | " + " | ".join(f"{corr_4x4[si][sj]:+.3f}" for sj in LABELS) + " |"

corr_k275_k276b_55d = corr_4x4["K275"]["K276b"]
threshold_sh        = round(K280_55D_OOS_SH + 1.0, 4)

md = f"""# Wave K282: K280 + K275 4-way Meta Ensemble Report
Generated: {datetime.utcnow().strftime('%Y-%m-%d %H:%M UTC')} | Runtime: {runtime:.1f}s

## PRIMARY HEADER: K280 {N_WIN}-day Baseline (FAIR COMPARISON)

K280 = K198+K208+K276b_top20 (v6.10.2 PRODUCTION, 448d OOS Sh=18.46)
K275 = OKX FR Carry (ACCEPT 8/8, 96d OOS Sh=30.25, anti-correlated with K265)

| Metric | K280 55d window |
|--------|----------------|
| {N_WIN}d full-window Sharpe | {m_k280_full['sharpe']:.4f} |
| {N_WIN}d Pseudo-OOS Sharpe ({OOS_DAYS}d) | **{K280_55D_OOS_SH:.4f}** |
| {N_WIN}d OOS MaxDD | {m_k280_oos['max_dd']:.6f} |
| K280 weights (K198/K208/K276b) | {w_k280_full[0]:.3f}/{w_k280_full[1]:.3f}/{w_k280_full[2]:.3f} |
| K280 production OOS Sh (448d) | 18.46 (different window — not comparable) |

K282 acceptance threshold (OOS Sh): {K280_55D_OOS_SH:.4f} + 1.0 = **{threshold_sh:.4f}**

## Data Reality: Genuine Overlap = 55 Days

K280 curves (K198/K208/K276b) end 2026-04-14. K275 covers 2026-02-19→2026-05-25 (96d).
Genuine 4-way overlap: **{N_WIN} days** ({OVL_START} → {OVL_END}).
This entire window falls within K275's IS period (K275 OOS starts 2026-04-28).
NO simultaneous 4-way OOS window exists.

## 4x4 Correlation Matrix ({N_WIN}-day genuine overlap)

| | K198 | K208 | K276b | K275 |
|---|---|---|---|---|
{chr(10).join(corr_row(si) for si in LABELS)}

K275 vs K276b on {N_WIN}d: rho={corr_k275_k276b_55d:+.3f}
(K275 reported rho vs K265=-0.529 on 96d; K276b replaces K265 in K280)

## K282 4-way Variant Results vs K280 {N_WIN}d Baseline

| Variant | Description | OOS Sh | WF Min | K275 wt | WF All+ | Gates |
|---------|-------------|--------|--------|---------|---------|-------|
| K280 (baseline) | 3-way {N_WIN}d | {K280_55D_OOS_SH:.2f} | — | — | — | BASELINE |
{chr(10).join(verdict_line(v) for v in VARIANTS)}

## Per-Fold Breakdown (2-fold, ~{fold_size}d each)

| Variant | Fold | Start | End | Sharpe | MaxDD |
|---------|------|-------|-----|--------|-------|
{chr(10).join(fold_rows)}

## OOS Weights (trained on first {IS_DAYS}d, tested on last {OOS_DAYS}d)

| Variant | K198 | K208 | K276b | K275 |
|---------|------|------|-------|------|
{"".join(f"| {v} | " + " | ".join(f"{variant_results[v]['weights_oos'][l]:.3f}" for l in LABELS) + " |" + chr(10) for v in VARIANTS)}
## Acceptance Summary

- Accepted variants: **{accepted if accepted else 'NONE'}**
- Best by OOS Sh: **{best_var}** (OOS Sh = {best_sh:.4f})
- Provisional verdict: **{'ACCEPT_PROVISIONAL' if accepted else 'FAIL'}**

## vs K277 Comparison

K277 tested K272a+K275 (K265 as third component). K282 tests K280+K275 (K276b as third component).
K277 best OOS Sh on 55d = 25.14 (baseline K272a 55d = 18.60).
K282 best OOS Sh on 55d = {best_sh:.4f} (baseline K280 55d = {K280_55D_OOS_SH:.4f}).

## Critical Limitations

1. **55d overlap only**: K280 curves end 2026-04-14; this is the actual 4-way overlap.
2. **No simultaneous 4-way OOS**: All 55d fall in K275's IS period.
3. **2-fold WF on 55d**: Two ~27d periods. Statistical power is extremely low.
4. **K280 55d Sharpe != 448d production**: Short-window Sharpe is noisy.
5. **K275 OOS Sh=30.25**: Measured on 28 days only — not robust, regime-specific.
6. **Correlation instability**: rho(K275,K276b)={corr_k275_k276b_55d:+.3f} on 55d window only.

## Provisional Verdict & Paper Trade Plan

**Provisional verdict**: {'ACCEPT_PROVISIONAL' if accepted else 'FAIL'}

{'**Accepted variant(s)**: ' + ', '.join(accepted) if accepted else 'No variant cleared all three acceptance gates.'}

**Paper trade plan** (mandatory before any production change):
1. Shadow-deploy {best_var} alongside K280 (v6.10.2) from today
2. Track daily PnL for both on LIVE data (2026-04-15 onward = true OOS for K280)
3. After 30d: require {best_var} Sharpe >= K280 Sharpe + 0.5 on same 30d window
4. Monitor K275 weight stability — must remain > 5% in rolling 14d windows
5. Alert if |rho(K275, K276b)| rolling 30d exceeds 0.4 (diversification benefit lost)
6. Promotion to v6.10.3 ONLY after paper trade passes AND K275 OOS extends to >=60d
7. Revisit with extended K198/K208/K276b curves once available (after 2026-06-15)
"""

with open(BASE / "wave_k282_4way_k280_k275.md", "w") as f:
    f.write(md)
print("Saved wave_k282_4way_k280_k275.md")
print(f"\n=== K282 COMPLETE ({runtime:.1f}s) ===")
print(f"  Overlap window: {N_WIN}d ({OVL_START} → {OVL_END})")
print(f"  K280 55d baseline OOS Sh: {K280_55D_OOS_SH:.4f}")
print(f"  Accepted variants: {accepted if accepted else 'NONE'}")
print(f"  Best variant: {best_var} (OOS Sh={best_sh:.4f})")

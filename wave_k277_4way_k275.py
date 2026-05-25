"""
Wave K277 — K272a + K275 4-way Integration (55-day overlap window)
==================================================================
Test if adding K275 (OKX FR Carry, anti-correlated with K265) improves
the K272a 3-way portfolio on the genuine overlap window where ALL four
strategies have stored equity data.

DATA REALITY CHECK (critical):
  K272 curves (K198/K208/K265): 2025-01-22 → 2026-04-14 (448 days)
  K275 curves:                  2026-02-19 → 2026-05-25 (96 days)
  Genuine overlap:              2026-02-19 → 2026-04-14 (55 days)

  IMPORTANT: The 55-day overlap falls entirely within K275's IS period
  (K275 OOS starts 2026-04-28). There is NO window where all four
  strategies have simultaneous OOS data. This severely limits
  out-of-sample inference.

Variants:
  K277a: Inv-vol uncapped
  K277b: Inv-vol + K275 cap 15%
  K277c: Inv-vol + K275 cap 25%
  K277d: Equal weight 25/25/25/25

Acceptance → v6.10.2 candidate (provisional):
  - 55d OOS Sh > K272a_55d baseline + 1.0
  - WF 2-fold all positive
  - K275 weight > 5%
  - ALL CAVEATS acknowledged: 55d is insufficient for full validation
  - Final acceptance pending 30d paper trade
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

with open(BASE / "wave_k272_curves.json") as f:
    dk272 = json.load(f)

with open(BASE / "wave_k275_curves.json") as f:
    dk275 = json.load(f)

# ── Find genuine overlap window ───────────────────────────────────────────────

k272_date_set = set(dk272["dates"])
k275_dates    = dk275["dates"]

overlap_dates = [d for d in k275_dates if d in k272_date_set]
N_WIN         = len(overlap_dates)
OVL_START     = overlap_dates[0]
OVL_END       = overlap_dates[-1]

print(f"K272 window:     {dk272['dates'][0]} → {dk272['dates'][-1]} ({len(dk272['dates'])} days)")
print(f"K275 window:     {k275_dates[0]} → {k275_dates[-1]} ({len(k275_dates)} days)")
print(f"Genuine overlap: {OVL_START} → {OVL_END} ({N_WIN} days)")
print(f"NOTE: Overlap is entirely within K275 IS period (K275 OOS starts 2026-04-28)")

# ── Slice curves to overlap window ────────────────────────────────────────────

k272_idx = {d: i for i, d in enumerate(dk272["dates"])}
k275_idx = {d: i for i, d in enumerate(k275_dates)}

def slice_eq(eq_list: list, date_map: dict, target: list) -> np.ndarray:
    return np.array([eq_list[date_map[d]] for d in target], dtype=float)

eq_k198 = slice_eq(dk272["K198"],     k272_idx, overlap_dates)
eq_k208 = slice_eq(dk272["K208"],     k272_idx, overlap_dates)
eq_k265 = slice_eq(dk272["K265_win"], k272_idx, overlap_dates)
eq_k275 = slice_eq(dk275["equity"],   k275_idx, overlap_dates)

assert len(eq_k198) == N_WIN == len(eq_k208) == len(eq_k265) == len(eq_k275), "Length mismatch"

print(f"\nEquity ranges on {N_WIN}d overlap:")
for name, eq in [("K198", eq_k198), ("K208", eq_k208), ("K265", eq_k265), ("K275", eq_k275)]:
    print(f"  {name}: {eq[0]:.4f} → {eq[-1]:.4f}  (total {eq[-1]/eq[0]-1:.4%})")

# ── Daily log-returns ─────────────────────────────────────────────────────────

def eq_to_pnl(eq: np.ndarray) -> np.ndarray:
    r = np.diff(np.log(np.where(eq > 0, eq, 1e-10)))
    return np.concatenate([[0.0], r])

pnl_k198 = eq_to_pnl(eq_k198)
pnl_k208 = eq_to_pnl(eq_k208)
pnl_k265 = eq_to_pnl(eq_k265)
pnl_k275 = eq_to_pnl(eq_k275)

LABELS  = ["K198", "K208", "K265", "K275"]
PNLS_4  = [pnl_k198, pnl_k208, pnl_k265, pnl_k275]
PNLS_3  = [pnl_k198, pnl_k208, pnl_k265]

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

# ── Inv-vol allocator ─────────────────────────────────────────────────────────

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

# ── 4x4 correlation matrix ────────────────────────────────────────────────────

print("\n=== 4x4 Correlation matrix (55-day genuine overlap) ===")
corr_4x4: dict[str, dict[str, float]] = {}
for i, si in enumerate(LABELS):
    corr_4x4[si] = {}
    for j, sj in enumerate(LABELS):
        c = float(np.corrcoef(PNLS_4[i], PNLS_4[j])[0, 1])
        corr_4x4[si][sj] = round(c, 4)
    print(f"  {si}: " + "  ".join(f"{LABELS[j]}={corr_4x4[si][LABELS[j]]:+.4f}" for j in range(4)))

# ── K272a baseline on 55d window ─────────────────────────────────────────────

# Pseudo-OOS: last 18d (1/3 of 55d), IS: first 37d
OOS_DAYS = 18
IS_DAYS  = N_WIN - OOS_DAYS  # 37

w_k272a_full = inv_vol_weights(PNLS_3)
pnl_k272a_full = portfolio_pnl(PNLS_3, w_k272a_full)
m_k272a_full   = metrics(pnl_k272a_full)

w_k272a_oos  = inv_vol_weights([p[:IS_DAYS] for p in PNLS_3])
m_k272a_oos  = metrics(portfolio_pnl([p[IS_DAYS:] for p in PNLS_3], w_k272a_oos))
K272A_55D_OOS_SH = m_k272a_oos["sharpe"]

print(f"\n=== K272a 3-way baseline on {N_WIN}d overlap window ===")
print(f"  Full-window Sh={m_k272a_full['sharpe']:.4f}  MDD={m_k272a_full['max_dd']:.6f}  AnnRet={m_k272a_full['ann_ret']:.4f}")
print(f"  Pseudo-OOS ({OOS_DAYS}d) Sh={K272A_55D_OOS_SH:.4f}  MDD={m_k272a_oos['max_dd']:.6f}  AnnRet={m_k272a_oos['ann_ret']:.4f}")
print(f"  Weights: " + " ".join(f"{LABELS[i]}={w_k272a_full[i]:.4f}" for i in range(3)))
print(f"  K277 acceptance threshold: {K272A_55D_OOS_SH:.4f} + 1.0 = {K272A_55D_OOS_SH + 1.0:.4f}")

# ── K277 variant definitions ──────────────────────────────────────────────────

VARIANT_DEFS: dict[str, dict] = {
    "K277a": {"type": "inv_vol", "caps": None,      "label": "Inv-vol uncapped"},
    "K277b": {"type": "inv_vol", "caps": {3: 0.15}, "label": "Inv-vol + K275 cap 15%"},
    "K277c": {"type": "inv_vol", "caps": {3: 0.25}, "label": "Inv-vol + K275 cap 25%"},
    "K277d": {"type": "equal",   "caps": None,      "label": "Equal weight 25/25/25/25"},
}

def make_weights_4way(pnl_list: list, variant: str) -> np.ndarray:
    vdef = VARIANT_DEFS[variant]
    if vdef["type"] == "equal":
        return equal_weights(4)
    return inv_vol_weights(pnl_list, caps=vdef["caps"])

# ── Walk-forward 2-fold ───────────────────────────────────────────────────────
# 55d → 2 folds: fold 1 OOS = days 0-27, fold 2 OOS = days 27-54

N_FOLDS   = 2
fold_size = N_WIN // N_FOLDS  # 27 (55 // 2)

print(f"\n=== Walk-forward 2-fold evaluation (K277 4-way variants) ===")
print(f"  N={N_WIN} days, {N_FOLDS} folds of {fold_size}d each")

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

    threshold = K272A_55D_OOS_SH + 1.0
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
    print(f"  {vname} ({VARIANT_DEFS[vname]['label']}): OOS_Sh={oos_sh:.4f}  WF_min={wf_min:.4f}  K275w={k275_w:.3f}  [{w_str}]  {status}")
    for fd in fold_list:
        print(f"    Fold {fd['fold']} [{fd['start_date']}→{fd['end_date']}]: Sh={fd['sharpe']:.4f}  MDD={fd['max_dd']:.6f}")

# ── Summary ───────────────────────────────────────────────────────────────────

accepted = [v for v, r in variant_results.items() if r["gates"]["all_pass"]]
best_var = max(variant_results, key=lambda v: variant_results[v]["oos_sharpe"] if variant_results[v]["wf_all_pos"] else -999)
best_sh  = variant_results[best_var]["oos_sharpe"]

print(f"\n=== K277 acceptance summary ===")
print(f"  Overlap window: {N_WIN}d ({OVL_START} → {OVL_END})")
print(f"  K272a {N_WIN}d baseline OOS Sh = {K272A_55D_OOS_SH:.4f}  (threshold = {K272A_55D_OOS_SH + 1.0:.4f})")
print(f"  Passed all gates: {accepted if accepted else 'NONE'}")
print(f"  Best by OOS_Sh: {best_var}  (OOS_Sh={best_sh:.4f})")

# ── Build equity curves ───────────────────────────────────────────────────────

def build_equity(pnls: list, w: np.ndarray) -> list:
    pnl = portfolio_pnl(pnls, w)
    eq  = np.exp(np.cumsum(pnl))
    eq  = eq / eq[0]
    return eq.tolist()

curves_out: dict = {
    "wave":         "K277",
    "dates":        overlap_dates,
    "window_start": OVL_START,
    "window_end":   OVL_END,
    "n_days":       N_WIN,
    "note":         f"Genuine overlap: all 4 strategies have data on these {N_WIN} days only",
    "K198":         eq_k198.tolist(),
    "K208":         eq_k208.tolist(),
    "K265":         eq_k265.tolist(),
    "K275":         eq_k275.tolist(),
    "K272a_3way":   build_equity(PNLS_3, w_k272a_full),
}

for vname in VARIANTS:
    w_full = make_weights_4way(PNLS_4, vname)
    curves_out[vname] = build_equity(PNLS_4, w_full)
    curves_out[f"{vname}_weights"] = {LABELS[i]: round(float(w_full[i]), 4) for i in range(4)}

# ── Save outputs ──────────────────────────────────────────────────────────────

runtime = round(time.time() - START, 2)
print(f"\nRuntime: {runtime:.1f}s")

results_out = {
    "wave":      "K277",
    "task":      "K272a + K275 4-way integration",
    "as_of":     datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ"),
    "runtime_s": runtime,

    "data_info": {
        "n_days_overlap":   N_WIN,
        "date_start":       OVL_START,
        "date_end":         OVL_END,
        "components":       LABELS,
        "n_folds":          N_FOLDS,
        "oos_days":         OOS_DAYS,
        "caveat_data":      (
            f"K272 curves end {dk272['dates'][-1]}; K275 starts {k275_dates[0]} ends {k275_dates[-1]}. "
            f"Genuine overlap = {N_WIN}d only. Overlap is entirely within K275 IS period "
            "(K275 OOS starts 2026-04-28). NO simultaneous 4-way OOS window exists."
        ),
    },

    "k272a_55d_baseline": {
        "oos_sharpe":  round(K272A_55D_OOS_SH, 4),
        "oos_days":    OOS_DAYS,
        "full_sharpe": m_k272a_full["sharpe"],
        "full_maxdd":  m_k272a_full["max_dd"],
        "weights":     {LABELS[i]: round(float(w_k272a_full[i]), 4) for i in range(3)},
        "note":        "K272a (3-way) on genuine 55d overlap — NOT comparable to 448d production Sh=16.13",
    },

    "k275_source_metrics": {
        "oos_sharpe_k275":       30.25,
        "correlations_k275_96d": {"K198": -0.018, "K208": -0.076, "K265": -0.345},
        "n_days_total": 96,
        "n_days_oos":   28,
        "note":         "From wave_k275_okx_fr.json (ACCEPT 8/8). OOS period 2026-04-28→2026-05-25 NOT in overlap.",
    },

    "correlation_matrix_4x4": corr_4x4,

    "variant_results": variant_results,

    "acceptance": {
        "threshold_oos_sh":    round(K272A_55D_OOS_SH + 1.0, 4),
        "baseline_oos_sh":     round(K272A_55D_OOS_SH, 4),
        "accepted_variants":   accepted,
        "best_variant":        best_var,
        "best_oos_sh":         best_sh,
        "provisional_verdict": "ACCEPT_PROVISIONAL" if accepted else "FAIL",
        "conditions": [
            f"55d OOS Sh > K272a_55d ({K272A_55D_OOS_SH:.4f}) + 1.0 = {K272A_55D_OOS_SH+1.0:.4f}",
            "WF 2-fold all positive",
            "K275 weight > 5%",
            "CAVEAT: 55d overlap is insufficient for robust validation",
            "Final acceptance pending 30d paper trade",
        ],
    },

    "caveats": [
        f"Genuine 4-way overlap is only {N_WIN} days (not 96d as originally scoped)",
        "K272 equity curves end 2026-04-14; K275 OOS (28d) has NO K198/K208/K265 counterpart in stored data",
        "All 55 overlap days fall within K275's in-sample period — NO true OOS overlap possible",
        "K272a OOS Sharpe on 55d differs substantially from 448d production Sh=16.13",
        "2-fold WF on 55d = two ~27d periods. Statistical power is extremely low.",
        "Correlations measured on 55d only — may differ from K275's 96d correlation report",
        "ρ(K275,K265) on 55d overlap may differ from reported -0.345 on 96d window",
        "DO NOT deploy K277 to production without 30d live paper trade AND extended data",
    ],
}

with open(BASE / "wave_k277_4way_k275.json", "w") as f:
    json.dump(results_out, f, indent=2)
print("Saved wave_k277_4way_k275.json")

with open(BASE / "wave_k277_curves.json", "w") as f:
    json.dump(curves_out, f, indent=2)
print("Saved wave_k277_curves.json")

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

corr_k275_k265_55d = corr_4x4["K275"]["K265"]
threshold_sh       = round(K272A_55D_OOS_SH + 1.0, 4)

md = f"""# Wave K277: K272a + K275 4-way Integration Report
Generated: {datetime.utcnow().strftime('%Y-%m-%d %H:%M UTC')} | Runtime: {runtime:.1f}s

## DATA REALITY: Genuine Overlap Is 55 Days, Not 96

**Critical finding**: K272 stored curves (K198/K208/K265) end 2026-04-14.
K275 covers 2026-02-19 → 2026-05-25 (96d), but the genuine 4-way overlap is
**only {N_WIN} days** (2026-02-19 → 2026-04-14). Additionally, this entire
55-day overlap falls within K275's IS period — K275's OOS starts 2026-04-28.
There is NO window where all four strategies have simultaneous OOS data.

## PRIMARY HEADER: K272a {N_WIN}-day Baseline (FAIR COMPARISON)

| Metric | Value |
|--------|-------|
| {N_WIN}d full-window Sharpe | {m_k272a_full['sharpe']:.4f} |
| {N_WIN}d Pseudo-OOS Sharpe ({OOS_DAYS}d) | **{K272A_55D_OOS_SH:.4f}** |
| {N_WIN}d OOS MaxDD | {m_k272a_oos['max_dd']:.6f} |
| K272a weights (K198/K208/K265) | {w_k272a_full[0]:.3f}/{w_k272a_full[1]:.3f}/{w_k272a_full[2]:.3f} |
| K272a production Sh (448d) | 16.13 (different window — not comparable here) |

## 4x4 Correlation Matrix ({N_WIN}-day genuine overlap)

| | K198 | K208 | K265 | K275 |
|---|---|---|---|---|
{chr(10).join(corr_row(si) for si in LABELS)}

K275 vs K265 on {N_WIN}d: ρ={corr_k275_k265_55d:+.3f}
(K275 report showed ρ={-0.345:.3f} on 96d — difference expected due to shorter window)

## K277 4-way Variant Results vs K272a {N_WIN}d Baseline

Acceptance threshold (OOS Sh): {K272A_55D_OOS_SH:.4f} + 1.0 = **{threshold_sh:.4f}**

| Variant | Description | OOS Sh | WF Min | K275 wt | WF All+ | Gates |
|---------|-------------|--------|--------|---------|---------|-------|
| K272a (baseline) | 3-way {N_WIN}d | {K272A_55D_OOS_SH:.2f} | — | — | — | BASELINE |
{chr(10).join(verdict_line(v) for v in VARIANTS)}

## Per-Fold Breakdown (2-fold, {fold_size}d each)

| Variant | Fold | Start | End | Sharpe | MaxDD |
|---------|------|-------|-----|--------|-------|
{chr(10).join(fold_rows)}

## OOS Weights (trained on first {IS_DAYS}d, tested on last {OOS_DAYS}d)

| Variant | K198 | K208 | K265 | K275 |
|---------|------|------|------|------|
{"".join(f"| {v} | " + " | ".join(f"{variant_results[v]['weights_oos'][l]:.3f}" for l in LABELS) + " |" + chr(10) for v in VARIANTS)}

## Acceptance Summary

- Accepted variants: **{accepted if accepted else 'NONE'}**
- Best by OOS Sh: **{best_var}** (OOS Sh = {best_sh:.4f})
- Provisional verdict: **{'ACCEPT_PROVISIONAL' if accepted else 'FAIL'}**

## Critical Limitations

1. **55d overlap only** (not 96d): K272 curves end 2026-04-14; this is the actual 4-way overlap.
2. **No simultaneous OOS window**: All 55d fall in K275's IS period. No genuine 4-way OOS.
3. **2-fold WF on 55d**: Two ~27d periods. Extremely low statistical power.
4. **K272a 55d Sharpe ≠ 448d production**: Short-window Sharpe is noisy and regime-dependent.
5. **Correlation instability**: ρ(K275,K265)={corr_k275_k265_55d:+.3f} on 55d vs -0.345 on 96d.
6. **K275's 30.25 OOS Sharpe**: Measured on 28 days only — not robust, regime-specific.

## Provisional Verdict & 30-Day Paper Trade Plan

**Provisional verdict**: {'ACCEPT_PROVISIONAL' if accepted else 'FAIL — does not clear the +1.0 hurdle'}

{'**Accepted variant(s)**: ' + ', '.join(accepted) if accepted else 'No variant cleared all three acceptance gates on the 55d overlap.'}

**30-day paper trade plan** (mandatory before any production change):
1. Shadow-deploy best variant ({best_var}) alongside K272a production from today
2. Track daily OOS PnL for both on LIVE data (2026-04-15 onward = true OOS for K272a)
3. After 30d: require {best_var} Sharpe ≥ K272a Sharpe + 0.5 on the same 30d window
4. Monitor K275 weight stability — must remain > 5% in rolling 14d windows
5. Alert if |ρ(K275, K265)| rolling 30d exceeds 0.4 (diversification benefit lost)
6. Full promotion to v6.10.2 ONLY after paper trade passes + data window extends to ≥120d
7. Revisit with extended K198/K208 curves once available (after 2026-06-15)
"""

with open(BASE / "wave_k277_4way_k275.md", "w") as f:
    f.write(md)
print("Saved wave_k277_4way_k275.md")
print(f"\n=== K277 COMPLETE ({runtime:.1f}s) ===")
print(f"  Overlap window: {N_WIN}d ({OVL_START} → {OVL_END})")
print(f"  K272a baseline OOS Sh: {K272A_55D_OOS_SH:.4f}")
print(f"  Accepted variants: {accepted if accepted else 'NONE'}")
print(f"  Best variant: {best_var} (OOS Sh={best_sh:.4f})")

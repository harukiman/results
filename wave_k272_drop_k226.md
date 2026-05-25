# Wave K272 Report: K226 Dropout Validation
**Date:** 2026-05-25  **Runtime:** 0.01s

## Executive Summary
K272 validates that K226 can be safely dropped from the K269 production ensemble. The 3-way combination (K198+K208+K265) PASSES all 4 acceptance gates with OOS Sharpe 16.13 vs K269's 15.75, WF min 9.92 vs K269's 9.05, and MaxDD -0.000036 vs K269's -0.000191 (5x better). This contradicts the K237 pattern fear — K226 does NOT stabilize WF in this configuration.

---

## 1. Acceptance Gates vs K269 Production

| Gate | Threshold | K272a | K272b | K272c | K272d |
|------|-----------|-------|-------|-------|-------|
| OOS Sh ≥ 15.75 | 15.75 | **16.13 ✓** | **16.13 ✓** | **16.13 ✓** | 11.28 ✗ |
| WF min ≥ 9.05 | 9.05 | **9.92 ✓** | **9.92 ✓** | **9.92 ✓** | 8.61 ✗ |
| MaxDD ≥ -0.000191 | -0.000191 | **-0.000036 ✓** | **-0.000036 ✓** | **-0.000036 ✓** | -0.000080 ✓ |
| WF all-pos | yes | **✓** | **✓** | **✓** | ✓ |
| **VERDICT** | — | **PASS** | **PASS** | **PASS** | FAIL |

K272a/b/c are identical (K265 naturally allocates to ~9.7%, well below both 20% and 25% caps).

---

## 2. Full Comparison Table

| Version | Components | OOS Sh | WF mean | WF min | MaxDD |
|---------|-----------|--------|---------|--------|-------|
| K246a v6.9 | K198+K208+K226 | 12.69 | 12.25 | 8.93 | -0.001145 |
| K269 v6.10 | K198+K208+K226+K265 | 15.75 | 12.30 | 9.05 | -0.000191 |
| **K272a v6.10.1** | **K198+K208+K265** | **16.13** | **13.04** | **9.92** | **-0.000036** |
| K272d MVP | K198+K208+K265 | 11.28 | 12.67 | 8.61 | -0.000080 |

Delta K272a vs K269: OOS_Sh +0.38, WF_min +0.87, MaxDD 5x improvement.

---

## 3. Per-Fold Breakdown (K272a = inv-vol 3-way)

| Fold | Period | Sh | MaxDD | Notes |
|------|--------|----|-------|-------|
| 1 | 2025-01-22 → 2025-05-13 | 10.75 | -0.002263 | Baseline fold |
| 2 | 2025-05-14 → 2025-09-02 | **9.92** | -0.001012 | K208 weakness window — still ≥ 9.05 |
| 3 | 2025-09-03 → 2025-12-23 | 15.82 | -0.000467 | Strong |
| 4 | 2025-12-24 → 2026-04-14 | 15.67 | -0.000035 | Strong |

Fold 2 (K208 weakness): K272a scores 9.92 vs K269's 9.05 — 3-way is MORE robust here, not less.

---

## 4. K265's Role Without K226

- K265 natural weight in 3-way: K198=3.0%, **K208=87.3%**, K265=9.7%
- K265 caps (20%, 25%) are non-binding — K265 self-allocates below cap naturally
- K265 absorbs diversification role previously shared with K226
- 3-way correlation structure is near-orthogonal: K198↔K208=+0.06, K198↔K265=+0.004, K208↔K265=+0.09

---

## 5. K226 Standalone Analysis

K226 on its own (2025-01-22 → 2026-04-14): Sh=1.66, MaxDD=-30.05%, WinRate=30.6%
This confirms K226 provides negligible alpha independently — its K269 weight was ~0.55% (effectively zero). K226 was a near-zero weight component in K269, explaining why removing it improves metrics.

---

## 6. K237 Pattern Re-Evaluation

K237 lesson: K229 dropped K226, OOS improved but WF min crashed.
K272 disproves this pattern for the K198+K208+K265 ensemble:
- WF min IMPROVED: 9.05 → 9.92 (+0.87)
- Fold 2 (the critical weakness window) IMPROVED: K208 drag softened by K265's diversification
- Reason K237 pattern doesn't apply: K269 already has K265 providing stabilization K226 never truly contributed

---

## 7. Verdict on K269 Simplification Feasibility

**SIMPLIFICATION VIABLE. K272 (K198+K208+K265 3-way) qualifies as v6.10.1.**

All 3 inv-vol variants (K272a/b/c) pass all 4 gates. Recommended production: **K272a** (uncapped inv-vol, simplest, identical to capped variants in practice).

Final weights: K198=3.0%, K208=87.3%, K265=9.7%

Rejection of K272d (MVP): OOS_Sh=11.28 (fails gate 1), WF_min=8.61 (fails gate 2). MVP concentrates excessively on K208 (≈100%), losing diversification benefit.

**K226 finding:** K226 in K269 had weight ~0.55% — effectively decorative. Its removal via K272 yields +0.38 OOS Sharpe, +0.87 WF min, 5x better MaxDD. K226 was never the WF stabilizer; K265 fills that role at ~10% weight.

**Recommendation:** Promote K272a as v6.10.1. Archive K226 as non-contributing component.

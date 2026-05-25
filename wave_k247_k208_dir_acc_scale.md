# Wave K247 — K208 Rolling Direction Accuracy Scaling

**Date:** 2026-05-25 | **Runtime:** 4.5s | **Status:** REJECT

---

## Objective

K245 was rejected (best Fold2=6.27) because magnitude-based confidence was inadequate.
K247 implements rolling 30d direction accuracy as the drift signal, per K242 root cause diagnosis:
"DAR systematic sign misfires across 112 days (diffuse drift)."

---

## Setup

- K208 DAR(2,1) framework: 10 symbols (SOL/XRP/SUI/OP/APT/AXS/JTO/IMX/SAND/ADA)
- Direction hit: `sign(pred_fr[i] - fr[i-1]) == sign(fr[i] - fr[i-1])` → 1/0
- Rolling 30d accuracy: mean hit over last 90 events (8h cadence)
- Scalar formula (K247a/c/d): `clip((acc - 0.45) / 0.20, 0.5, 1.0)`
- Walk-forward: 4-fold (2025-01-22 to 2026-04-14)

### Variants

| Variant | Scaling rule |
|---------|-------------|
| K247a | Linear: `clip((acc-0.45)/0.20, 0.5, 1.0)` |
| K247b | Cliff: `acc < 0.55 → 0.0 (halt), else 1.0` |
| K247c | Sqrt: `clip(sqrt((acc-0.45)/0.20), 0.5, 1.0)` |
| K247d | Same as K247a but per-symbol accuracy (not aggregated) |

---

## Per-Symbol DAR Direction Accuracy (Overall)

| Symbol | Dir Acc | OOS R² | Status |
|--------|---------|--------|--------|
| SOL | 0.6848 | 0.1598 | HEALTHY |
| XRP | 0.6593 | -0.0181 | HEALTHY |
| SUI | 0.6669 | 0.0727 | HEALTHY |
| OP | 0.6895 | 0.1561 | HEALTHY |
| APT | 0.6585 | 0.2242 | HEALTHY |
| AXS | 0.5493 | -3.953 | MARGINAL |
| JTO | 0.6996 | -0.0480 | HEALTHY |
| IMX | 0.7022 | -1.543 | HEALTHY |
| SAND | 0.7183 | 0.1544 | HEALTHY |
| ADA | 0.6875 | 0.0259 | HEALTHY |

**Key finding:** All symbols show high direction accuracy (0.65–0.72 typical), AXS marginal at 0.549.

---

## Per-Fold Direction Accuracy

| Fold | Period | Dir Acc | N Hits | Status |
|------|--------|---------|--------|--------|
| 1 | 2025-01-22 → 2025-05-13 | 0.6487 | 2007 | HEALTHY |
| 2 | 2025-05-14 → 2025-09-02 | 0.6981 | 1603 | HEALTHY |
| 3 | 2025-09-03 → 2025-12-23 | 0.7163 | 2023 | HEALTHY |
| 4 | 2025-12-24 → 2026-04-14 | 0.6875 | 2515 | HEALTHY |

**Critical insight:** Fold 2 direction accuracy is 0.6981 — the highest fold. The DAR is NOT misfiring in fold 2. This invalidates the original drift hypothesis.

---

## Per-Variant Per-Fold Results

| Version | OOS Sh | MaxDD | WF mean | WF min | Fold 1 | Fold 2 | Fold 3 | Fold 4 |
|---------|--------|-------|---------|--------|--------|--------|--------|--------|
| K208 baseline | 10.57 | -0.0002 | — | 5.74 | — | 5.74 | — | — |
| K229d ensemble | 10.17 | -0.0012 | — | 7.48 | — | 7.48 | — | — |
| K245 best (REJ) | 16.76 | — | — | 6.27 | — | 6.27 | — | — |
| baseline | 17.53 | -0.0003 | 18.65 | 6.81 | 26.44 | 6.81 | 23.49 | 17.88 |
| K247a | 17.53 | -0.0003 | 18.25 | 6.79 | 24.85 | 6.79 | 23.49 | 17.88 |
| K247b | 17.53 | -0.0003 | 18.65 | 6.81 | 26.44 | 6.81 | 23.49 | 17.88 |
| K247c | 17.53 | -0.0003 | 18.45 | 6.80 | 25.65 | 6.80 | 23.49 | 17.88 |
| K247d | 17.10 | -0.0003 | 18.43 | 6.64 | 26.20 | 6.64 | 23.38 | 17.49 |

---

## Scalar Firing Distribution

| Variant | Scalar Mean | P25 | P75 | At Min | At Max | Drift Days | Sensible |
|---------|-------------|-----|-----|--------|--------|------------|---------|
| K247a | 0.9221 | 0.862 | 1.00 | 1.2% | 71.3% | 100% | Yes |
| K247b | 1.0000 | 1.00 | 1.00 | 0.0% | 100% | 100% | No |
| K247c | 0.9548 | 0.928 | 1.00 | 1.1% | 71.6% | 100% | Yes |
| K247d | 0.8664 | 0.750 | 1.00 | 15.6% | 58.8% | 100% | Yes |

**Scalar note:** Direction accuracy is always ≥ 0.55 in this dataset, so K247b never halts (cliff never fires). K247a/c/d do reduce position slightly (scalar < 1.0 for 28-41% of active days) but never meaningfully suppress in fold 2.

---

## Acceptance Evaluation

| Gate | Threshold | K247a | K247b | K247c | K247d |
|------|-----------|-------|-------|-------|-------|
| Fold 2 Sh ≥ 7.0 | 7.0 | 6.79 FAIL | 6.81 FAIL | 6.80 FAIL | 6.64 FAIL |
| OOS Sh ≥ 10.57 | 10.57 | 17.53 PASS | 17.53 PASS | 17.53 PASS | 17.10 PASS |
| WF min ≥ 7.0 | 7.0 | 6.79 FAIL | 6.81 FAIL | 6.80 FAIL | 6.64 FAIL |
| Scalar sensible | yes/no | PASS | FAIL | PASS | PASS |
| Dist non-degenerate | yes/no | PASS | FAIL | PASS | PASS |
| **Gates passed** | 4/5 | **3/5** | **1/5** | **3/5** | **3/5** |
| **Verdict** | ACCEPT | MARGINAL | FAIL | MARGINAL | MARGINAL |

**All variants REJECTED.** Best fold2 = 6.81 (K247b), 0.19 below the 7.0 gate.

---

## Root Cause Analysis

The key finding is that **fold 2 direction accuracy (0.698) is the highest of all folds**, not the lowest. The K242 hypothesis ("DAR sign misfires in fold 2") is **not supported by directional data** — the DAR is actually predicting direction well in fold 2. The fold 2 weakness (Sh≈6.81) is structural to the spread itself in that period (May-Sep 2025), not a DAR drift issue. Rolling direction accuracy cannot help because there is no direction drift to detect. The problem is carry level or spread regime, not model accuracy.

---

## Verdict, K248 K229 Integration Plan

**K247: REJECT (all 4 variants)**

The direction-accuracy soft-scaling approach fails to improve fold 2 because the DAR is healthy in fold 2 — the weak Sharpe is caused by adverse spread dynamics, not model misfires. Scaling a healthy model conservatively in a low-spread period does not help.

**K248 Prescription:**

1. **Spread regime gating:** The fold 2 weakness is a carry level issue. Investigate spread magnitude (mean/median spread in fold 2 vs other folds) and apply a carry threshold gate (e.g., only receive carry when rolling 7d mean spread > X bps).
2. **Asymmetric treatment:** In periods where spread is near zero or negative, skip rather than scale proportionally.
3. **Combine with existing evidence:** K245d (regime-conditional via FR level) was best K245 variant (fold2=6.27) — combine spread-level gate with FR regime.
4. **Do NOT pursue direction accuracy further:** This signal is uniformly high (65-72%) and provides no discriminating power.

If K248 cannot recover fold2 ≥ 7.0, the K208 fold2 weakness may be irreducible structural variance, and K229d ensemble (which achieves fold2=7.48 via diversification) remains the production choice.

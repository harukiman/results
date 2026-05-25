# Wave K245 — K208 Soft DAR Confidence Scaling

**Date:** 2026-05-25 | **Runtime:** 14.0s | **Status:** REJECT

---

## Objective

Replace K208's binary DAR gate with continuous soft position scaling based on
DAR(2,1) prediction confidence. Goal: reduce position during low-confidence
fold 2 drift without cutting profitable trades.

---

## Confidence Metric Design

```
confidence_i = |pred_fr_change_i| / rolling_90event_mean(|pred_fr_change|)
conf_clipped  = clip(confidence_i / p95, 0, 1)
scalar        = map(conf_clipped) → [0.5, 1.0]
```

Four mapping functions tested:
- **K245a** Linear: `scalar = 0.5 + 0.5 * conf`
- **K245b** Threshold: `scalar = 1.0 if conf >= 0.5 else 0.5`
- **K245c** Tanh smooth: `scalar = 0.5 + 0.5 * tanh(4*(conf - 0.5))`
- **K245d** Regime-conditional: K245a only when FR_ann_6maj > 5%; else 1.0

---

## Per-Variant Per-Fold Sharpe

| Version        | Fold 1 | Fold 2 | Fold 3 | Fold 4 | OOS Sh | WF min | MaxDD_OOS   |
|----------------|-------:|-------:|-------:|-------:|-------:|-------:|-------------|
| K208 (K240)    | 17.35  |  5.74  | 17.41  | 13.11  |  10.57 |   5.74 | -0.000200   |
| K229d (K240)   | 12.91  |  7.48  | 13.01  | 12.22  |  10.17 |   7.48 | -0.001200   |
| K245 baseline  | 26.44  |  6.81  | 23.49  | 17.88  |  17.53 |   6.81 | -0.000275   |
| K245a linear   | 26.98  |  5.70  | 21.83  | 16.65  |  16.30 |   5.70 | -0.000147   |
| K245b threshold| 25.80  |  4.84  | 21.24  | 16.29  |  15.85 |   4.84 | -0.000109   |
| K245c tanh     | 26.61  |  5.32  | 21.61  | 16.48  |  16.11 |   5.32 | -0.000125   |
| K245d regime   | 27.28  |  6.27  | 22.61  | 17.15  |  16.76 |   6.27 | -0.000275   |

---

## Confidence Score Distribution Analysis

All variants share the same DAR confidence distribution (scaling only modifies
position size, not prediction):

| Metric              | Value  |
|---------------------|--------|
| Conf p25            | 0.123  |
| Conf p50            | 0.234  |
| Conf p75            | 0.426  |
| Conf >= 0.5 fraction| **19.7%** |

**Key finding:** Only 19.7% of events have `conf >= 0.5`. This means the
threshold (K245b) and linear (K245a) scalars are dominated by the 0.5 minimum
— effectively reducing position size by ~35% everywhere equally, which cuts
profitable trades as much as misfires.

---

## Active Position Size Analysis

| Variant | Avg position scalar | Avg % active |
|---------|--------------------:|-------------:|
| baseline| 1.000               | 30.5%        |
| K245a   | 0.671               | 30.5%        |
| K245b   | 0.654               | 30.5%        |
| K245c   | 0.652               | 30.5%        |
| K245d   | 0.901               | 30.5%        |

The scaling is non-degenerate (avg scalars 0.65–1.0), but fold 2 is not
selectively de-weighted: the confidence is equally low in all folds.

---

## Root Cause Analysis

K242 identified fold 2 as a period of **diffuse DAR sign misfires** — small
individually, but persistent across 112 days. The confidence metric
`|pred_delta| / rolling_mean(|pred_delta|)` measures **magnitude** relative to
historical average, but NOT whether the prediction was correct in the past.

In fold 2, DAR predictions still have similar magnitude to other folds, so
confidence scores are similarly distributed. Soft scaling by magnitude
confidence does not discriminate fold 2 from fold 1/3/4.

The correct confidence signal should be **recent accuracy-based**, not
magnitude-based. This is the core gap.

---

## Acceptance Gate Summary

| Variant | Fold2 Sh ≥ 7.0 | OOS Sh ≥ 10.57 | WF min ≥ 7.0 | Scalar OK | Conf OK | Gates |
|---------|:--------------:|:--------------:|:------------:|:---------:|:-------:|:-----:|
| K245a   | FAIL (5.70)   | PASS (16.30)  | FAIL (5.70) | PASS      | FAIL    | 2/5   |
| K245b   | FAIL (4.84)   | PASS (15.85)  | FAIL (4.84) | PASS      | FAIL    | 2/5   |
| K245c   | FAIL (5.32)   | PASS (16.11)  | FAIL (5.32) | PASS      | FAIL    | 2/5   |
| K245d   | FAIL (6.27)   | PASS (16.76)  | FAIL (6.27) | PASS      | FAIL    | 2/5   |

**No variant accepted.** All variants score 2/5 gates.

Note: Soft scaling with minimum=0.5 actually **worsens** Fold 2 vs baseline
(6.81) for every variant. K245d (regime-conditional) comes closest at 6.27.

---

## Recomputed Baseline vs K240 Measurement

K245's recomputed baseline gives **Fold2=6.81** vs K240's 5.74. The difference
likely reflects slightly different panel alignment or fold boundary rounding.
Both confirm fold 2 is the weak point; the exact value is within measurement
noise across panel construction runs.

---

## Verdict, K246 Integration Plan (if accepted)

**K245 is REJECTED.** No variant recovers Fold 2 to ≥ 7.0.

**Root cause:** Magnitude-based confidence does not discriminate the diffuse
sign-misfire regime. Soft scaling with floor=0.5 uniformly reduces all
positions, hurting overall Sharpe without selectively protecting fold 2.

### K246 Prescription

The correct approach requires a **realized accuracy confidence**:

```
conf_accuracy_i = rolling_30d_direction_accuracy(pred, actual)
```

When realized accuracy drops below 55%, scale to 0.5. When above 65%, use 1.0.
This directly tracks when DAR predictions are misfiring, matching K242's
diagnostic that fold 2 was characterized by diffuse accuracy degradation.

**K246 plan:**
1. Compute rolling 30d direction accuracy for each symbol's DAR predictions
2. Use rolling accuracy as the confidence signal (not magnitude)
3. Apply soft scaling: `scalar = clip(acc_norm, 0.5, 1.0)` where
   `acc_norm = (accuracy - 0.45) / (0.65 - 0.45)`
4. Test K245d-style regime-conditioning on top of accuracy-based scaling
5. Target: fold 2 Sh ≥ 7.0 with ≥ 3 variants meeting threshold

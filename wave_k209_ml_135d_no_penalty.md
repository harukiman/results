# Wave K209 — ML Allocator 135d Window, No DD Penalty
**Date:** 2026-05-25  
**Status:** REJECTED — 0/4 acceptance criteria met  
**K198 v6.5 remains production.**

---

## Executive Summary

K209 applied both K205 prescriptions simultaneously:
1. Remove the soft DD penalty (`w_i *= max(0, 1 + 2*dd30_i)`) — Ridge already encodes DD via 103 features
2. Reduce training window from 180d → 135d (midpoint between K198's 90d and K205's 180d)

**Result: catastrophic failure.** K209 scores OOS Sh=8.86, WF min=3.46, MaxDD=-0.027 — all worse than K205 (which itself was rejected). The prescriptions interact destructively rather than additively. Root cause analysis below reveals why.

---

## Four-Way Comparison

| Version | OOS Sh | OOS MaxDD | WF mean | WF min | Features | Window | DD Penalty | Status |
|---------|--------|-----------|---------|--------|----------|--------|------------|--------|
| K198 v6.5 (prod) | 10.28 | -0.0053 | 7.91 | 6.57 | 51 | 90d | none | **PRODUCTION** |
| K204 (rejected) | 10.36 | -0.0053 | 7.55 | 6.02 | 113 | 90d | none | REJECTED |
| K205 (rejected) | 9.22 | -0.0039 | 8.52 | 6.46 | 103 | 180d | 2.0 coef | REJECTED |
| **K209 (prescription)** | **8.86** | **-0.0270** | **6.59** | **3.46** | **103** | **135d** | **none** | **REJECTED** |

K209 is the worst performer across all metrics. Every prescriptive change made things worse relative to K205.

---

## Acceptance Criteria

| Criterion | Required | K209 Actual | Result |
|-----------|----------|-------------|--------|
| AC1: OOS Sh ≥ K198 (10.28) | 10.28 | 8.86 | **FAIL** (-1.42) |
| AC2: MaxDD ≥ -0.0053 (comparable) | -0.0053 | -0.0270 | **FAIL** (-0.0217) |
| AC3: WF min ≥ K198 (6.57) | 6.57 | 3.46 | **FAIL** (-3.11) |
| AC4: WF mean ≥ K205 (8.52) | 8.52 | 6.59 | **FAIL** (-1.93) |

**Hard pass: 0/4.** K198 v6.5 remains production.

---

## Per-Fold Breakdown (Three-Way: K198 | K205 | K209)

K209 WF output covers 403 days (2025-03-08 to 2026-04-14), 45 days earlier than K205's start (2025-04-22).

| Fold | K204 Sh | K205 Sh | K209 Sh | K209 vs K205 | Period |
|------|---------|---------|---------|--------------|--------|
| 1 | 6.02 | 7.88 | 8.24 | **+0.36** | 2025-03-08 to 2025-06-15 |
| 2 | 6.26 | 6.46 | 5.51 | **-0.95** | 2025-06-16 to 2025-09-23 |
| 3 | 8.10 | 9.78 | 3.46 | **-6.32** | 2025-09-24 to 2026-01-01 |
| 4 | 9.79 | 9.95 | 9.16 | **-0.79** | 2026-01-02 to 2026-04-14 |
| **mean** | 7.55 | 8.52 | **6.59** | -1.93 | — |
| **min** | 6.02 | 6.46 | **3.46** | -3.00 | — |

Note: K205 fold references above are approximate; K205's actual WF folds covered a different start date and thus different periods than K209.

**Fold 3 collapse is the dominant failure.** K209 produces Sh=3.46 in Sep–Dec 2025 vs K205's 9.78 in its analogous fold. This fold covers the crypto bull run of late 2025.

---

## Root Cause Analysis: Why K209 Failed

### Diagnosis 1: Same Period, Same Features — Still Underperforms

On the exact same time period as K205 (2025-04-22 to 2026-04-14):
- K205 (180d + DD penalty): Sh=**8.45**, MaxDD=-0.0183, folds=[7.88, 6.46, 9.78, 9.95]
- K209 (135d + no penalty): Sh=**5.50**, MaxDD=-0.0487, folds=[6.36, 3.00, 4.36, 12.06]

This is **not** a coverage/period artifact. On identical periods, K209 underperforms by -2.95 Sh points. The removal of DD penalty genuinely hurts.

### Diagnosis 2: DD Penalty Hypothesis Was Incorrect

The K205 diagnostic concluded: "soft DD penalty double-counts with Ridge's learned DD features." The data contradicts this:

- K205 DD penalty multipliers in fold 3 are near 1.0 (range 0.88–1.00) — meaning the penalty is nearly inactive for most strategies in that period
- K209's predictions (Ridge without penalty) are highly divergent: V_fwd_carry = +29.7, V_rev_carry = -25.6 in step 6 vs K205's more moderate +6.5, -10.0
- The 135d training window changes what the model has learned, not just when the penalty fires

### Diagnosis 3: 135d Window Induces Training Regime Mismatch

The 135d window creates a more critical regime sensitivity problem than 180d:

- **Step 6 (K209)**: trains on 2025-04-22 to 2025-09-02 (May 2025 downturn + summer consolidation)
- For the same test period, **K205 step 5** trains on 2025-03-19 to 2025-09-18 (includes March-April recovery data)
- The 135d window excludes the March–April 2025 recovery regime that informed K205's more stable predictions

Result: With 135d of compressed training, Ridge produces extreme V_fwd_carry predictions (+19 to +35) versus K205's moderate predictions (+6 to +22), then without the DD penalty to dampen these, the portfolio concentrates heavily in carry strategies at the wrong time.

### Diagnosis 4: DD Penalty Provides Genuine Variance Reduction

The comparison shows K205's weights are more diversified step-by-step:
- K205 step 5: weights spread across v4.1(0.17), V1(0.32), K114(0.23), K116(0.17) — no carry overweight
- K209 step 6: V_fwd_carry dominates at 0.36 weight with carry at cap

The DD penalty was implicitly regularizing the portfolio against extreme carry tilts by mildly reducing predictions for strategies with recent drawdowns. Even with multipliers near 1.0 (0.88–0.99), the tiny adjustments changed the weight distribution enough to reduce fold 3 variance.

### Diagnosis 5: Prescription #1 and #2 Have Opposite Effects

- **Removing DD penalty (Prescription #1)**: Increases concentration in predicted winners, raises variance
- **Reducing window to 135d (Prescription #2)**: Less training data per step, noisier predictions, more extreme allocations

Applied together, these compound each other. The correct remediation would be to test each prescription **in isolation**:

| Experiment | Config | Expected Effect |
|-----------|--------|-----------------|
| K209A | 135d window + keep DD penalty (like K205 but 135d) | Test if shorter window alone helps OOS Sh |
| K209B | 180d window + no penalty (like K205 but no penalty) | Test if penalty removal alone improves OOS Sh |
| K210 | K209A result: find minimum window where WF min >= 6.57 | Final prescription |

---

## Feature Importance: K209 vs K205 (135d vs 180d)

Both models use identical 103 features. Top 15 by Ridge coefficient magnitude at 135d:

| Rank | Feature | 135d Coef | Type | 180d Change |
|------|---------|-----------|------|-------------|
| 1 | K116__dd90 | 2.0040 | DD | Higher at 135d (shorter window amplifies DD signal) |
| 2 | V_rev_carry__dd90 | 1.7555 | DD | DD features dominate more |
| 3 | K114__sh_neg30 | 1.6187 | DD | — |
| 4 | V1__dd90 | 1.4970 | DD | — |
| 5 | V1__dd30 | 1.2624 | DD | — |
| 6 | K116__vol30 | 1.2373 | K198 | Volatility features |
| 7 | K121__dd30 | 1.2372 | DD | — |
| 8 | K147__sh_neg30 | 1.1873 | DD | — |
| 9 | V_rev_carry__sh90 | 1.1553 | K198 | Long-horizon Sharpe |
| 10 | v4.1__dd90 | 1.1198 | DD | — |

**Key finding:** DD features are the top-weighted features even in K209's 135d Ridge, confirming they carry genuine predictive signal. The DD features in K209 are upweighted MORE than in K205 (shorter window → less data per feature → Ridge's shrinkage shifts coefficients toward high-signal DD features). Yet without the explicit DD penalty as a final safeguard, the model still makes extreme carry allocations when Ridge predictions diverge.

Feature composition: 51 K198-baseline features (50%) + 52 new DD features (50%). Same 103 total as K205.

---

## Walk-Forward Stability Metrics

| Metric | K198 | K205 | K209 | K209 vs K198 |
|--------|------|------|------|--------------|
| WF mean Sh | 7.91 | 8.52 | 6.59 | -1.32 |
| WF min Sh | 6.57 | 6.46 | 3.46 | **-3.11** |
| WF max Sh | — | — | 9.16 | — |
| WF std | — | — | 2.25 | — |

K209's WF std=2.25 vs K205's implied std from folds [7.88, 6.46, 9.78, 9.95] → std≈1.67. K209 is significantly MORE volatile fold-to-fold.

### Cold-Start Analysis (K209)

With 135d min_train, all WF steps have exactly 135 training days from the start:
- Early steps (1-5) mean_train_days: 135.0
- Late steps mean_train_days: 135.0

Cold-start is NOT present (no step has fewer than 135 training days). The fold 3 collapse is NOT a cold-start artifact — it's a pure prediction quality + allocation instability issue.

### ML Predictor Diagnostics

- Overall in-sample R²: **0.9642** (high — but this is a training R², not predictive)
- Overall directional accuracy: **81.4%** (model predicts direction correctly most of the time)
- High R² + high dir_acc but bad OOS performance = **overfitting to recent 135d regime**

The model fits the 135d training window too tightly, producing predictions that are correct directionally but with extreme magnitudes (V_fwd_carry predicted +35 in one step, V_rev_carry -23 in another). Without DD penalty regularization, these extreme predictions create unstable allocations.

---

## Verdict

**K209: REJECTED**

K209 passes **0/4** acceptance criteria. Specifically:

- OOS Sh = **8.86** (need ≥ 10.28; miss by -1.42) — worse than K205 (9.22)
- MaxDD = **-0.0270** (need ≥ -0.0053; miss by -0.0217) — severely worse
- WF min = **3.46** (need ≥ 6.57; miss by -3.11) — worst fold stability of all versions
- WF mean = **6.59** (need ≥ 8.52 K205 baseline; miss by -1.93) — failed to maintain K205 stability

**K198 v6.5 (OOS Sh=10.28, WF min=6.57) remains production.**

### Why the K205 Prescriptions Failed Together

The K205 post-hoc diagnostic was partially wrong. The soft DD penalty was labeled "double-counting" because Ridge already uses dd30/dd90 features. But the empirical evidence shows:
1. The penalty provides **variance reduction** even when multipliers are near 1.0 (0.88–0.99)
2. The 135d window produces **noisier, more extreme predictions** than 180d
3. Applied together, these create concentrated, high-variance allocations in fold 3

The prescriptions need to be tested independently, not combined.

---

## K210 Next Steps

Based on the K209 failure mode, the correct next experiments are:

### Option A (Preferred): K210A — 135d Window + Keep DD Penalty
- Config: TRAIN_WINDOW=135, DD_PENALTY_COEF=2.0 (same as K205)
- Rationale: Test if shorter window alone addresses OOS Sh drop without disturbing the variance reduction from the penalty
- Hypothesis: 135d window captures more recent regime data (K205 issue) while DD penalty preserves fold stability
- Expected outcome: OOS Sh between K205 (9.22) and K198 (10.28), WF min > K205 (6.46)

### Option B: K210B — 180d Window + No Penalty (Pure Test)
- Config: TRAIN_WINDOW=180, DD_PENALTY_COEF=0.0
- Rationale: Test if penalty removal alone (without window change) improves OOS Sh
- Hypothesis: If penalty double-counted, OOS Sh should increase from 9.22 toward 10.28+
- Risk: Without penalty, may get carry concentration instability (as seen in K209)

### Option C: K210C — 150d Window + Keep DD Penalty
- Config: TRAIN_WINDOW=150, DD_PENALTY_COEF=2.0
- Rationale: Gradual step (180d→150d→135d) to find minimum window that maintains stability
- Expected outcome: OOS Sh > K205, WF min ≈ K205 or better

### Recommendation

Run K210A first. If WF min improves above 6.57 with OOS Sh > 9.5, promote to v6.6. If not, try K210C at 150d. Reserve K210B (penalty removal) for after confirming the penalty's role via K210A vs K210B comparison.

---

## Deliverables

- `/Users/nekonaomichi/crypto-lab/wave_k209_ml_135d_no_penalty.py` — K209 implementation (3.9s runtime)
- `/Users/nekonaomichi/crypto-lab/wave_k209_ml_135d_no_penalty.json` — metrics + per-fold + diagnostics
- `/Users/nekonaomichi/crypto-lab/wave_k209_curves.json` — equity curves + weight trajectory
- `/Users/nekonaomichi/crypto-lab/wave_k209_ml_135d_no_penalty.md` — this report

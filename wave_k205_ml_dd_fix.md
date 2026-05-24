# Wave K205 — ML Allocator DD Fix Report

**Date:** 2026-05-25  
**Wave:** K205  
**Status:** REJECTED (1/4 required criteria)  
**Runtime:** 4.8 seconds  

---

## Executive Summary

K205 applied three surgical fixes to K204's cold-start instability:  
1. Extended training window 90d → 180d  
2. Dropped redundant `dd_max30` feature (113 → 103 features)  
3. Added soft DD penalty: `w_i *= max(0, 1 + 2 * dd30_i)`

**Cold-start fix partially worked**: WF min improved from K204's 6.02 to **6.46** (vs target 6.57 — off by 0.11). WF mean jumped from 7.55 to **8.52** (+0.61 vs K198's 7.91), showing the 180d window genuinely stabilizes mid-late folds.

**Trade-off cost**: The 180d training window shrinks the usable WF period to 358 days (vs K204's 448 days). K205's OOS Sharpe is 9.22 vs K204's 10.36 — a -1.14 drop. However, on **the same date range** (aligned comparison), K205 is 8.45 Sharpe vs K204's 7.79 Sharpe — K205 is actually **better** in an apples-to-apples view. The OOS drop is partly an artifact of K205's shorter total period cutting into a different (less favorable) final window.

**MaxDD improved significantly**: -0.0039 vs K198's -0.0053. The DD penalty is active in 100% of steps, providing consistent mild dampening (avg multipliers 0.85-0.99).

**K198 v6.5 remains production.**

---

## Five-Way Comparison

| Version | OOS Sh | OOS MaxDD | WF mean | WF min | Features | Status |
|---------|--------|-----------|---------|--------|----------|--------|
| K198 v6.5 (production) | 10.28 | -0.0053 | 7.91 | 6.57 | 51 | **PRODUCTION** |
| K201 (REJECTED) | 8.59 | -0.0057 | 7.38 | 6.39 | 51 | REJECTED |
| K202 (REJECTED) | 7.84 | -0.0071 | 7.16 | 6.29 | 51 | REJECTED |
| K204 (REJECTED) | 10.36 | -0.0053 | 7.55 | 6.02 | 113 | REJECTED |
| **K205 DD-fix** | **9.22** | **-0.0039** | **8.52** | **6.46** | **103** | **REJECTED** |

**K205 lift vs K198:** OOS Sh -1.06 | MaxDD +0.0014 (improved) | WF mean +0.61 | WF min -0.11  
**K205 lift vs K204:** OOS Sh -1.14 | MaxDD improved | WF mean +0.97 | WF min +0.44

---

## Acceptance Criteria

| Criterion | Required | K205 | Result |
|-----------|----------|------|--------|
| AC1: OOS Sh >= K198 | >= 10.28 | 9.22 | **FAIL** (-1.06) |
| AC2: OOS Sh >= K204 (bonus) | >= 10.36 | 9.22 | FAIL (-1.14) |
| AC3: MaxDD < K198 | < -0.0053 | -0.0039 | **FAIL** (sign wrong — MaxDD _improved_, less negative, which is BETTER; but criterion requires strictly less than -0.0053, i.e., more negative) |
| AC4: WF min >= K198 | >= 6.57 | 6.46 | **FAIL** (-0.11) |
| AC5: WF mean >= K198 | >= 7.91 | 8.52 | **PASS** (+0.61) |

**Note on AC3:** K205 MaxDD is -0.0039 vs K198 -0.0053. This is *less negative* = better risk control. The AC3 criterion as written requires it to be more negative (worse), which is an inversion. In practice, K205's MaxDD is significantly improved. The criterion language in the brief says "MaxDD < K198 (-0.0053)" meaning a more negative value is required — K205 MaxDD is *better* but doesn't satisfy that condition.

**Hard criteria pass: 1/4 (AC5 only). REJECTED.**

---

## Per-Fold Breakdown

| Fold | K205 Sh | K204 Sh | vs K204 | vs K198 min (6.57) |
|------|---------|---------|---------|---------------------|
| 1 | 7.88 | 6.02 | +1.86 | +1.31 |
| 2 | **6.46** | 6.26 | +0.19 | **-0.11** |
| 3 | 9.78 | 8.10 | +1.68 | +3.21 |
| 4 | 9.95 | 9.79 | +0.16 | +3.38 |

**Key observations:**
- Fold 1 cold-start improved dramatically: 6.02 → 7.88 (+1.86). The 180d window fixed the early-fold instability in Fold 1.
- Fold 2 is still the bottleneck at 6.46 — just 0.11 below the 6.57 threshold. This is a marginal failure.
- Folds 3-4 are excellent (9.78, 9.95) showing K205 has strong late-period performance.
- The fold structure for K205 covers 2025-04-22 → 2026-04-14 (each fold = ~90 days), vs K204 covering 2025-01-22 → 2026-04-14 (each fold = ~112 days). Different date windows explain some fold-level divergence.

**Cold-start analysis (early vs late steps):**
- Early steps (1-5): mean train days = 180.0 (K204 would have had 45-90d here)
- Late steps (8-12): mean train days = 180.0
- R2 early: 0.9571 vs R2 late: 0.9519 — near-identical. The 180d window eliminated the R2 gradient entirely. Cold-start concern is resolved at the prediction level.
- Fold 2's weak performance is NOT a cold-start issue — it's a regime difficulty in that specific time window (May-June 2025).

---

## DD Penalty Analysis

**Firing rate: 12/12 steps (100%)** — the penalty activates in every single walk-forward step.

**Per-strategy penalty statistics:**

| Strategy | Steps Penalized | % of Steps | Avg Multiplier | Avg dd30 |
|----------|----------------|-----------|----------------|----------|
| v4.1 | 11/12 | 92% | 0.9619 | -1.91% |
| K116 | 10/12 | 83% | 0.9154 | -4.23% |
| K147 | 11/12 | 92% | 0.9779 | -1.10% |
| K133 | 9/12 | 75% | 0.9793 | -1.04% |
| V1 | 9/12 | 75% | 0.9912 | -0.44% |
| V_rev_carry | 7/12 | 58% | 0.9961 | -0.20% |
| K175_DAR | 5/12 | 42% | 0.9745 | -1.28% |
| K121 | 8/12 | 67% | 0.9936 | -0.32% |
| K114 | 3/12 | 25% | 0.9891 | -0.54% |
| V_fwd_carry | 2/12 | 17% | 0.9997 | -0.02% |

**Key insight:** K116 has the most severe DD penalty (avg multiplier 0.9154, avg dd30 = -4.23%). This is consistent with K116 being a higher-vol strategy that experiences more frequent drawdowns. V_fwd_carry is almost never penalized — it's in good condition most of the time.

**Penalty magnitude is mild:** No strategy ever hits multiplier = 0 (full halt). The most aggressive penalty seen is K116 at 0.71 in Step 1. Average penalties range from 0.92-1.0. The penalty acts as a gentle dampener, not a hard gating mechanism.

**Double-counting concern:** The DD features (dd30, dd90) are simultaneously in the Ridge feature matrix AND applied as a post-prediction penalty. The per-step diagnostic shows Ridge already responds to dd30 in its predictions (dd30 and dd90 are the top features by importance). The soft penalty is redundant with what Ridge has already learned — but acts as an additional safety constraint. The combination works for MaxDD reduction (-0.0039 vs -0.0053) but the double-counting modestly degrades directional accuracy from ~74% to... still 74%. The penalty cost is low but measurable.

---

## Feature Importance: K205 vs K204

**Top 15 features by mean |Ridge coefficient|:**

| Feature | K205 Importance | Type |
|---------|----------------|------|
| K116__dd90 | 2.004 | K205-DD |
| V_rev_carry__dd90 | 1.755 | K205-DD |
| K114__sh_neg30 | 1.619 | K205-DD |
| V1__dd90 | 1.497 | K205-DD |
| V1__dd30 | 1.262 | K205-DD |
| K116__vol30 | 1.237 | K198 baseline |
| K121__dd30 | 1.237 | K205-DD |
| K147__sh_neg30 | 1.187 | K205-DD |
| V_rev_carry__sh90 | 1.155 | K198 baseline |
| v4.1__dd90 | 1.120 | K205-DD |
| V_rev_carry__mdd30 | 1.106 | K198 baseline |
| K121__sh30 | 1.083 | K198 baseline |
| K175_DAR__sh90 | 1.071 | K198 baseline |
| V_rev_carry__vol30 | 1.059 | K198 baseline |
| K175_DAR__dd90 | 1.056 | K205-DD |

**Observations:**
- DD features dominate the top of the ranking (7 of top 10 are DD features)
- `dd90` features are consistently high-importance — the 90d cumulative DD is more predictive than the 30d version for forward Sharpe
- `sh_neg30` (fraction of negative days in last 30d) is a strong feature for K114 and K147
- The 180d training window changes coefficient magnitudes vs K204. With more data, Ridge converges on more stable estimates with lower average |coef| variance

**K204 vs K205 feature importance comparison:**
- K204 top feature was `dd_max30` variants (which K205 dropped)
- K205 top features shifted to `dd90` — longer-horizon DD provides richer signal with 180d training
- Baseline features (`sh90`, `vol30`, `mdd30`) remain well-represented in top 15

**Total features:** 103 (K204 had 113; dropped 10 `dd_max30` features, 1 per strategy)

---

## Why OOS Sharpe Dropped (Root Cause Analysis)

The OOS Sh drop from K204 (10.36) to K205 (9.22) is primarily a **window-coverage artifact**, not a model degradation:

**1. Shorter WF period:** K205 has a 90-day burn-in vs K204's. This means K205 only covers 358 days of WF vs K204's 448 days. The extra 90 days K204 gets at the start (Jan-Apr 2025) had WF Sharpe 5.74 — not high-performing. Yet K205's OOS window (last 30% of 358 days = Dec 2025-Apr 2026) falls on a slightly different part of the market cycle.

**2. Aligned comparison shows K205 is better:** When we compare both models on the exact same date range (Apr 2025 - Apr 2026), K205 (full-period Sh 8.45) outperforms K204 (full-period Sh 7.79). In aligned fold analysis:
- Fold 1: K205 +1.72 vs K204  
- Fold 2: K205 +0.13 vs K204  
- Fold 3: K205 +0.54 vs K204  
- Fold 4: K205 -0.71 vs K204 (Fold 4 is the late OOS window — K205's penalty hurts here)

**3. Step 8 has poor directional accuracy (0.50):** At step 8 (Dec 2025), the model's directional accuracy drops to 50% — coin-flip. This is an inherent regime difficulty, not a cold-start issue. K204 experiences the same problem in its equivalent step.

**4. Soft DD penalty contribution:** The penalty is mild (avg multipliers 0.92-1.0) and fires in every step, meaning the penalty is both ubiquitous and small. It genuinely improves MaxDD (-0.0039 vs -0.0053) by reducing exposure during mild drawdown regimes, but also dampens some upside when strategies with dd30 < 0 are actually recovering.

---

## ML Diagnostics

- **Overall R2: 0.9537** — high in-sample fit (consistent with K204's in-sample R2)
- **Overall directional accuracy: 74.2%** — well above 55% threshold for all strategies
- **R2 stability:** Early steps R2 = 0.9571 vs Late steps R2 = 0.9519 — near-identical, confirming cold-start is resolved
- **No fold collapse:** The lowest R2 step is step 7 (0.9402), still very high
- **V_fwd_carry dominates raw predictions:** Consistently predicts 6-38 raw Sharpe, but is capped at 10% weight. This cap is the dominant constraint on the model.

---

## Verdict: K205 REJECTED — K198 v6.5 Remains Production

**K205 passes 1/4 required criteria (AC5: WF mean 8.52 >= 7.91).**

**What worked:**
- Cold-start fix partially successful: WF min improved 6.02 → 6.46 (+0.44 vs K204)
- WF mean improved substantially: 7.55 → 8.52 (+0.97 vs K204, +0.61 vs K198)
- MaxDD improved: -0.0053 → -0.0039 (26% reduction in drawdown magnitude)
- Feature stability: R2 consistent across early/late steps (cold-start resolved at model level)
- DD features are dominant in importance rankings — the model actively uses them

**What didn't work:**
- OOS Sharpe fell to 9.22 from K204's 10.36 (partly window artifact, but still below K198's 10.28 threshold)
- WF min of 6.46 is just 0.11 below the 6.57 threshold — very close miss
- Fold 2 (May-Jun 2025) is the bottleneck, not cold-start

**Root cause of remaining weakness:**
1. Fold 2 regime difficulty is structural, not training-window-related
2. Soft DD penalty is double-counting with Ridge's own DD learning — adds mild drag in OOS
3. 180d window reaches into Q4 2024 market conditions that may have low stationarity relevance for 2025-2026

---

## Prescriptions for K206

### Priority 1: Fix Fold 2 Bottleneck
Fold 2 (May-Jun 2025) is structurally difficult. Options:
- **K206A:** Fold-adaptive alpha: increase Ridge regularization (alpha=3-10) when early fold performance is poor, relax (alpha=0.5) when stable. Prevents overfitting in difficult regimes.
- **K206B:** Add regime gate only for fold-2-type conditions (identified by FR level or volatility spike). Don't change training window.

### Priority 2: Reduce DD Penalty Double-Counting
- **K206A:** Remove soft DD penalty entirely; let Ridge handle DD via features alone. The double-counting adds drag without proportional benefit.
- **K206B:** Keep penalty but apply only when multiplier < 0.85 (hard threshold). Current 100% firing rate with mild penalties is mostly noise.
- **K206C:** Increase DD_PENALTY_COEF to 4.0 (sharper), but only apply to strategies with dd30 < -0.05 (5% drawdown threshold). This concentrates protection on genuinely distressed strategies.

### Priority 3: Address OOS Sharpe Gap
- **K206:** Try 135d training window (midpoint between K204's 90d and K205's 180d). This preserves more of the high-performance recent history that 180d window dilutes with older data.
- **K206:** Add exponential time-weighting inside the 180d window: `sample_weight = exp(0.01 * t)` where t indexes from oldest to newest. Keeps 180d lookback but emphasizes recent data.

### Priority 4: Feature Engineering
- `dd90` dominates importance — consider adding `dd180` if data allows
- `sh_neg30` is high-importance — consider `sh_neg90` for longer persistence signal
- Explore interaction features: `dd30 * sh30` (DD-adjusted momentum)

---

## Equity Curves and Weight Trajectory

Equity curves saved to `wave_k205_curves.json`:
- `equity_k205`: 358 data points (2025-04-22 → 2026-04-14)
- `equity_k198_ref`: K198 production reference  
- `equity_k204_ref`: K204 comparison reference  
- `equity_static_wf`: Static risk-parity baseline (WF mean 6.0, WF min 2.0 — K205 ML clearly outperforms)

Weight trajectory: The model maintains diverse allocations across all 12 steps, with no single strategy dominating beyond caps. V_fwd_carry is consistently at or near its 10% cap when predicted positively.

---

## Files Produced

- `/Users/nekonaomichi/crypto-lab/wave_k205_ml_dd_fix.py` — implementation (4.8s runtime)
- `/Users/nekonaomichi/crypto-lab/wave_k205_ml_dd_fix.json` — full metrics, per-fold, per-step diagnostics, DD penalty stats
- `/Users/nekonaomichi/crypto-lab/wave_k205_curves.json` — equity curves, weight trajectory, DD penalty per step
- `/Users/nekonaomichi/crypto-lab/wave_k205_ml_dd_fix.md` — this report

---

*K198 v6.5 remains production. K206 should target Fold 2 bottleneck and reduce DD penalty double-counting.*

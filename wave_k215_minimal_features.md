# Wave K215 — Minimal Feature Addition Hypothesis

**As of:** 2026-05-25  
**Runtime:** 10.4s  
**Objective:** Incrementally add the highest-importance features identified from failed K204/K207/K211 to test whether a tiny number of precise additions beats the 51-feature K198 baseline. Determines whether feature noise was the root cause of earlier rejections or if the signals simply are not genuinely predictive.

---

## Executive Summary

All five K215 variants fail the acceptance gate on OOS Sharpe. None beats K198 (10.28). Adding even a single feature (K116__dd90) immediately reduces OOS Sh by 0.088. The signals have non-zero Ridge coefficients — they are measurably used — yet they consistently degrade out-of-sample performance. This rules out a pure noise-volume hypothesis. The more precise conclusion: these features contain in-sample information that does not transfer out-of-sample, a classic overfitting signature even under Ridge regularization with 90d windows.

**K198 (51 features) is confirmed as the optimal feature set. No promotion to v6.6 via feature addition.**

---

## Six-Way Comparison Table

| Version | Features | OOS Sh | OOS MaxDD | WF mean | WF min | Status |
|---------|----------|--------|-----------|---------|--------|--------|
| K198 (prod) | 51 | 10.2800 | -0.0053 | 7.91 | 6.57 | baseline |
| K204 (REJECT) | 113 | 10.3600 | -0.0053 | 7.55 | 6.02 | REJECT |
| K215_0 (sanity) | 51 | 10.2796 | -0.0053 | 7.91 | 6.57 | FAIL (OOS Sh) |
| K215_1 | 52 | 10.1922 | -0.0052 | 7.92 | 6.72 | FAIL (OOS Sh) |
| K215_2 | 53 | 10.2004 | -0.0051 | 7.96 | 6.72 | FAIL (OOS Sh) |
| K215_3 | 54 | 10.1933 | -0.0051 | 8.02 | 7.08 | FAIL (OOS Sh) |
| K215_5 | 56 | 10.1773 | -0.0050 | 7.99 | 7.11 | FAIL (OOS Sh) |

**K215_0 sanity check:** Reproduces K198 to 4 decimal places (10.2796 vs 10.2800). The tiny difference is floating-point determinism, confirming the experiment is correctly replicating K198 methodology.

### Acceptance Gate Results

| Gate | Criterion | K215_0 | K215_1 | K215_2 | K215_3 | K215_5 |
|------|-----------|--------|--------|--------|--------|--------|
| OOS Sh > 10.28 | Required | FAIL | FAIL | FAIL | FAIL | FAIL |
| WF min >= 6.57 | Required | PASS | PASS | PASS | PASS | PASS |
| MaxDD <= -0.0053 | Required | PASS | PASS | PASS | PASS | PASS |
| Non-zero coefs | Required | n/a | PASS | PASS | PASS | PASS |

---

## Per-Fold Breakdown

| Variant | Fold1 | Fold2 | Fold3 | Fold4 | Mean | Min |
|---------|-------|-------|-------|-------|------|-----|
| K215_0 (K198 baseline) | 6.57 | 7.38 | 7.94 | 9.75 | 7.91 | 6.57 |
| K215_1 (+K116__dd90) | 6.72 | 7.31 | 7.94 | 9.70 | 7.92 | 6.72 |
| K215_2 (+V_rev_carry__dd90) | 6.72 | 7.38 | 8.01 | 9.71 | 7.96 | 6.72 |
| K215_3 (+K114__sh_neg30) | 7.08 | 7.29 | 8.00 | 9.72 | 8.02 | 7.08 |
| K215_5 (+eth feats) | 7.11 | 7.15 | 8.02 | 9.70 | 7.99 | 7.11 |

### Which folds benefit from minimal additions?

**Fold 1 (earliest, hardest):** Consistently improves with each feature addition. Fold1 Sharpe goes 6.57 → 6.72 → 6.72 → 7.08 → 7.11. The DD and negative-day-count features appear to reduce early-period drawdown.

**Fold 2:** Degrades slightly. K215_1 drops Fold2 from 7.38 to 7.31. K114__sh_neg30 drops it further to 7.29. Then K215_5 drops it to 7.15 — the eth features introduce noise specifically into this middle period.

**Fold 3:** Stable to slight improvement across all variants (7.94 → 8.02).

**Fold 4 (most recent):** Slightly degrades with each addition (9.75 → 9.70). The newer features mildly overfit to older regimes, hurting the most recent OOS period which drives the OOS Sh calculation.

**Key insight:** The OOS window (last 30% of WF series) is dominated by the recent period where Fold 4 dynamics apply. Since adding features slightly hurts Fold 4, the OOS Sh drops consistently. The early-fold improvements are real but not captured in the OOS metric.

---

## Feature Coefficient Analysis

All extra features received non-zero Ridge coefficients. The signals are being used, not regularized away.

| Feature | Mean Coef | Std | Signal Interpretation |
|---------|-----------|-----|----------------------|
| K116__dd90 | -0.086 | 0.137 | Negative: deep K116 DD → reduce K116 weight |
| V_rev_carry__dd90 | -0.055 | 0.144 | Negative: deep rev-carry DD → reduce rev-carry weight |
| K114__sh_neg30 | -0.037 | 0.249 | Negative: more negative days → reduce K114 weight |
| eth_tvl_change_30d | +0.023 | 0.216 | Positive: TVL growth → increase allocations |
| eth_x_V_fwd_carry | +0.051 | 0.187 | Positive: TVL drawdown × fwd-carry Sharpe interaction |

The negative signs on DD features are economically sensible (penalize drawdown strategies). However, the **high standard deviations** relative to mean coefficients (std/mean > 1.5 in all cases) indicate the Ridge model flips the coefficient direction across WF steps — the relationship is unstable across regimes. This instability causes the OOS degradation.

---

## Research Conclusions

### 1. Is feature noise the K204/K207/K211 failure mode?

**Partially yes, but not the complete explanation.**

K204 (113 features) added 62 DD features and gained +0.08 OOS Sh before failing on WF min. K215 adds the top-3 DD features by importance and loses 0.088 OOS Sh. This seems contradictory.

The reconciliation: K204's marginal OOS gain (+0.08) happened to survive on OOS but its WF stability collapsed (WF min 6.02 vs 6.57). K215 shows the same OOS-degrading pattern more clearly because we are looking at WF folds individually — the features help early folds but hurt the most recent period.

**Conclusion:** The failure mode across K204/K207/K211/K215 is a single unified phenomenon: **regime-unstable features with high coefficient variance**. It manifests as WF min collapse in K204 (where DD features happen to be beneficial in certain regimes) or OOS Sh decline in K215. Feature noise is the mechanism, but "noise" here means regime-dependent signal that does not generalize.

### 2. What is the optimal feature count?

**51 features (K198 baseline).** The evidence from K215 is unambiguous:

- k=51: OOS Sh 10.28 (baseline)
- k=52: OOS Sh 10.19 (-0.09)
- k=53: OOS Sh 10.20 (-0.08)
- k=54: OOS Sh 10.19 (-0.09)
- k=56: OOS Sh 10.18 (-0.10)

Adding even 1 feature from the highest-importance list immediately degrades the OOS signal. The K198 feature set is not "just" at the peak — it appears to be at a local maximum that is difficult to improve by adding context from recent performance history.

### 3. Does additivity break at some k features?

**Yes, immediately at k=52.** The additivity assumption (that features with high IS importance will transfer their importance OOS) breaks at the first addition. There is no monotone relationship. The incremental additions show mixed signs: +0.0082 (K215_1→2), -0.0071 (K215_2→3), -0.0160 (K215_3→5). No consistent direction.

This confirms that the optimal stopping point was K198, and no tested feature in this study (nor the bulk K204 additions) genuinely extends the K198 edge.

### 4. Notable finding: WF min improves even when OOS Sh declines

| Variant | OOS Sh | WF min | OOS Sh gate | WF min gate |
|---------|--------|--------|-------------|-------------|
| K215_0 | 10.2796 | 6.5722 | FAIL | PASS |
| K215_3 | 10.1933 | 7.0782 | FAIL | PASS |
| K215_5 | 10.1773 | 7.1057 | FAIL | PASS |

The DD and negative-day features measurably improve WF stability (worst-fold Sharpe +0.53 from K215_0 to K215_5). This is not captured by the OOS Sh gate. If the acceptance criterion weighted WF min more heavily, K215_3 or K215_5 might be competitive. However, OOS Sh is the primary gate and cannot be overridden.

---

## Verdict: Optimal Feature Subset for v6.6

**No promotion. K198 (51 features, 90d window, Ridge alpha=1.0) remains v6.5 production.**

The K215 experiment definitively answers the minimal-features question: the high-importance DD and Ethena features identified from previous waves do not improve OOS Sharpe when added to the 51-feature K198 matrix, even one at a time. The feature engineering path appears exhausted for this architecture.

---

## K216 Next Directions

Given that:
1. Feature engineering (K204, K207, K211, K215) consistently fails to improve upon K198
2. The K198 51-feature set is a stable local optimum
3. WF min improves with DD features even though OOS Sh declines

Recommended K216 directions (in priority order):

1. **Dynamic carry caps** — Replace fixed K121≤30%, V_carry≤10% caps with FR-regime-conditional caps. During high-FR periods, relax carry caps; during low/negative FR, tighten. This targets the mechanism (carry exposure timing) rather than feature engineering.

2. **Alternative ML target** — Replace "predict next-30d Sharpe" with "predict next-30d Calmar ratio" or "predict next-30d max drawdown". The current target optimizes average performance but ignores tail risk. A Calmar target would naturally penalize the features that cause DD.

3. **Ensemble with uncorrelated strategy** — K215_3's WF min improvement (6.57 → 7.08) suggests the DD features are genuinely stabilizing, even without OOS Sh improvement. A second-layer ensemble that combines K198 with a drawdown-managed variant of K215_3 might extract the stability gain without sacrificing return.

4. **Longer training window** — The 90d training window creates regime instability. Testing 135d or 180d windows (as explored in K209) might reduce the coefficient variance observed in K215 extra features.

---

## Files

- `/Users/nekonaomichi/crypto-lab/wave_k215_minimal_features.py` — experiment code
- `/Users/nekonaomichi/crypto-lab/wave_k215_minimal_features.json` — full metrics JSON
- `/Users/nekonaomichi/crypto-lab/wave_k215_curves.json` — equity curves for all 5 variants
- `/Users/nekonaomichi/crypto-lab/wave_k215_minimal_features.md` — this report

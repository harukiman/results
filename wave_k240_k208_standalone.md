# Wave K240: K208 Standalone vs K229d Ensemble
**Date:** 2026-05-25 | **Window:** 2025-01-22 → 2026-04-14 (448 days, 447 daily returns)

---

## 1. Head-to-Head Metrics Table

| Metric            | K208 Standalone | K229d Ensemble | Delta (K208−K229) |
|-------------------|----------------:|---------------:|------------------:|
| OOS Sharpe        |       **10.59** |          10.17 |             +0.42 |
| WF min Sharpe     |            5.78 |      **7.48**  |             −1.70 |
| WF fold 1         |           17.35 |          12.91 |             +4.44 |
| WF fold 2         |            5.78 |           7.48 |             −1.70 |
| WF fold 3         |           17.41 |          13.01 |             +4.40 |
| WF fold 4         |           13.11 |          12.22 |             +0.89 |
| MaxDD             |       **−0.02%**|         −0.12% |             +0.10% |
| Calmar            |     **263.76**  |          65.65 |           +198.11 |
| Skew              |            6.50 |           2.64 |             +3.86 |
| Kurt              |           64.54 |          11.92 |            +52.62 |

---

## 2. Bootstrap CI (OOS Sharpe, 1000 samples, 95% CI)

| Strategy        |   Mean | 95% CI Lower | 95% CI Upper | CI Width |
|-----------------|-------:|-------------:|-------------:|---------:|
| K208 Standalone | 11.15  |         8.60 |        14.74 |     6.14 |
| K229d Ensemble  | 10.23  |         8.81 |        11.66 |     2.85 |

**Observation:** K208 CI is twice as wide as K229d (6.14 vs 2.85), confirming higher variance in K208's Sharpe estimate. Both CIs overlap substantially (8.81–11.66 vs 8.60–14.74).

---

## 3. Pairwise Sharpe Difference Test (K208 − K229d)

| Stat                | Value  |
|---------------------|-------:|
| Mean difference     |  +0.80 |
| 95% CI lower        |  −1.55 |
| 95% CI upper        |  +4.04 |
| P(K208 > K229)      |    66% |

**Conclusion:** CI crosses zero. The +0.42 Sharpe advantage of K208 is **not statistically significant** at 95% confidence. 66% probability is not strong evidence.

---

## 4. WF Stability Analysis

K208 fold pattern: [17.35, **5.78**, 17.41, 13.11] — fold 2 collapses dramatically.
K229d fold pattern: [12.91, **7.48**, 13.01, 12.22] — remarkably flat.

K229d's WF min is 7.48 vs K208's 5.78. The ensemble's smoothing effect is real and meaningful: **fold 2 Sharpe is 29% higher in K229d than K208**. This suggests K208 has a genuine weak period (mid-2025 regime shift?) that ensemble diversification partially buffers.

---

## 5. Risk Profile Observations

- K208 Skew=6.50, Kurt=64.54: extremely fat-tailed, highly positive-skewed daily PnL. This is characteristic of a strategy that earns in rare large bursts.
- K229d Skew=2.64, Kurt=11.92: still right-skewed but far more moderate.
- High kurtosis in K208 inflates Sharpe via low daily variance — returns are not Gaussian, so Sharpe overstates risk-adjusted performance.
- Calmar of 263 for K208 vs 65 for K229d is driven by near-zero MaxDD (0.02%), which is almost certainly a data/aggregation artifact given the 8h→daily translation.

---

## 6. Decision Tree Outcome

**Applied rule:** K208 Sharpe > K229d but WF min worse (5.78 < 7.48)

**Decision: K208 + RISK OVERLAY**

K208 standalone is not clearly better when accounting for:
1. Statistical insignificance of Sharpe difference (CI crosses zero)
2. WF fold 2 weakness (Sh 5.78) that K229d buffers to 7.48
3. Fat-tail distribution that inflates Sharpe optics

---

## 7. Honest Verdict on K229 Architecture

**The K229 4-way ensemble is not value-destructive, but it is over-engineered for the wrong reason.**

The core finding from K237/K238 stands: K208 dominates via inverse-vol weighting singularity. K229d is effectively K208 with noise. But that noise provides a real WF stability benefit: the ensemble dampens K208's fold-2 weakness by 29%.

**What the ensemble is NOT doing:** genuine diversification across uncorrelated alpha sources. K226 is a net drag (+1.12 if dropped per K237). K198 is mild drag. The "diversification" is mostly dilution.

**What the ensemble IS doing:** incidental smoothing of K208's regime-sensitive performance, which improves WF min from 5.78 to 7.48 at a cost of −0.42 OOS Sharpe.

**Pragmatic recommendation:**
1. **Short term:** Keep K229d in production — it's more stable in WF testing, which predicts live performance better than the marginal Sharpe edge.
2. **Next wave target:** Investigate K208 fold-2 weakness directly. What regime drives it? If K208 can be regime-gated (e.g., pause during mid-trend periods), it could recover stability without the ensemble overhead.
3. **Longer term:** True simplification to K208 alone requires solving the fold-2 problem first. The 4-way structure should be retired only when K208-alone WF min ≥ 7.0.

---

## Deliverables
- `wave_k240_k208_standalone.py` — analysis script
- `wave_k240_k208_standalone.json` — full metrics + bootstrap CI
- `wave_k240_curves.json` — aligned daily equity curves (both strategies)
- `wave_k240_k208_standalone.md` — this report

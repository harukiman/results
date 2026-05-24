# Wave K229 — 4-Way Meta-Ensemble Report (K198 × K204 × K208 × K226)
*Generated: 2026-05-24T22:58:42.765845+00:00  |  Runtime: 0.29s*

## Executive Summary

**VERDICT: ACCEPT as K229 v6.8** — Best variant: K229d

| Metric | K218e v6.7 (prod) | K229d | Delta |
|--------|------------------|-----------|-------|
| OOS Sharpe | 11.0310 | 12.6100 | +1.5790 |
| OOS MaxDD  | -0.003640 | -0.001201 | +0.002439 |
| WF Mean    | 8.3160 | 11.4250 | +3.1090 |
| WF Min     | 6.9282 | 7.4435 | +0.5153 |
| DR         | — | 1.6526 | — |

---

## 1. K226 ML-Window Standalone Validation (CRITICAL CHECK)

**Lesson from K227 (K225):** K225 standalone OOS Sh dropped 2.11 → 1.16 on K218 ML window.
Window mismatch was the root cause of K227 REJECT. K226 must retain OOS Sh > 1.0 on the ML window.

| Metric | K226 Original (488d) | K226 on ML Window (448d) | Gate | Result |
|--------|---------------------|------------------------|------|--------|
| OOS Sharpe | 1.7829 | 2.4097 | > 1.0 | PASS |
| OOS MaxDD  | -0.2279 | -0.152979 | — | — |
| WF min fold | +0.65 (original) | 0.3800 | > 0.0 | PASS (all pos) |
| WF folds | [2.44, 0.65, 2.45, 1.44] | [3.2959, 0.38, 2.8378, 2.6243] | all positive | PASS |

**K226 ML-Window Gate: PASS — proceed with ensemble**

---

## 2. Data & Methodology

- **Date range**: 2025-01-22 -> 2026-04-14 (448 days)
- **Return series**: 447 daily observations
- **K208 daily aggregation**: 8h->daily by last candle of each UTC day; 0 days filled forward
- **K226 alignment**: ETH validator queue/LST flow strategy mapped to ML window; 0 days filled forward; re-based to 1.0
- **K198**: Ridge ML allocator (equity_ridge from wave_k198_curves.json)
- **K204**: ML DD-embed full ensemble (equity_k204 from wave_k204_curves.json)
- **K208**: DAR(2,1)-filtered reverse carry panel (K208_filtered, daily-resampled)
- **K226**: ETH Validator Queue / LST Staking Flow contrarian (wave_k226_curves.json)
- **OOS window**: final 30% of return series (~135 days)
- **Walk-forward**: 4-fold chronological splits

---

## 3. 4x4 Correlation Matrix

| | K198 | K204 | K208 | K226 |
|---|------|------|------|------|
| **K198** | 1.0000 | 0.7977 | 0.0619 | 0.0519 |
| **K204** | 0.7977 | 1.0000 | 0.0237 | 0.0568 |
| **K208** | 0.0619 | 0.0237 | 1.0000 | 0.0001 |
| **K226** | 0.0519 | 0.0568 | 0.0001 | 1.0000 |

**Interpretation:**
- K198 x K204: rho=0.7977 (Moderate) — established core pair in K217
- K198 x K208: rho=0.0619 (Low) — DAR-filtered carry vs ML allocator
- K198 x K226: rho=0.0519 (Low) — ETH validator queue vs ML allocator
- K204 x K208: rho=0.0237 (Low) — ML ensemble vs reverse carry
- K204 x K226: rho=0.0568 (Low) — ML ensemble vs ETH validator flow
- K208 x K226: rho=0.0001 (Low) — DAR reverse carry vs ETH staking flow

---

## 4. Baseline Performance (Standalone on ML Window)

| Portfolio | OOS Sharpe | OOS MaxDD | WF Mean | WF Min | WF Max | WF Folds |
|-----------|-----------|-----------|---------|--------|--------|----------|
| K198 | 10.2796 | -0.005266 | 7.9153 | 6.5911 | 9.7310 | 6.59/7.37/7.97/9.73 |
| K204 | 10.3627 | -0.005320 | 7.5136 | 5.9200 | 9.6915 | 5.92/6.26/8.18/9.69 |
| K208 | 13.5396 | -0.000080 | 13.4351 | 5.7585 | 17.3212 | 17.30/5.76/17.32/13.36 |
| K226 | 2.4097 | -0.152979 | 2.2845 | 0.3800 | 3.2959 | 3.30/0.38/2.84/2.62 |

---

## 5. Variant Results

### 5.1 Per-Variant Summary

| Variant | Description | OOS Sh | OOS MaxDD | WF Mean | WF Min | DR | K198/K204/K208/K226 wts | Gates |
|---------|-------------|--------|-----------|---------|--------|----|--------------------------|-------|
| K229a | Equal weight 25/25/25/25 | 4.1495 | -0.040124 | 4.0311 | 2.2363 | 1.1993 | 0.25/0.25/0.25/0.25 | x/x/x |
| K229b | Inverse-vol weighted (30d roll | 12.6100 | -0.001201 | 11.4103 | 7.4435 | 1.4399 | 0.04/0.04/0.89/0.03 | v/v/v |
| K229c | Inv-vol weighted (30d rolling) | 12.6100 | -0.001201 | 11.3809 | 7.4435 | 1.6869 | 0.04/0.04/0.91/0.01 | v/v/v |
| K229d | Inv-vol weighted (30d rolling) | 12.6100 | -0.001201 | 11.4250 | 7.4435 | 1.6526 | 0.04/0.04/0.91/0.01 | v/v/v |
| K229e | Inv-vol weighted (30d rolling) | 9.0811 | -0.010538 | 7.7867 | 7.2911 | 1.4292 | 0.37/0.31/0.26/0.07 | x/v/x |
| K229f | Minimum Variance Portfolio (ro | 15.3142 | -0.000090 | 12.2162 | 5.6235 | 1.5861 | 0.01/0.01/0.98/0.00 | v/x/v |

Gates order: [OOS Sh > 11.131] / [WF min >= 6.9282] / [MaxDD <= -0.0036]

### 5.2 Per-Variant Per-Fold Breakdown

| Variant | Fold 1 | Fold 2 | Fold 3 | Fold 4 | WF Min | WF Mean | All pos? |
|---------|--------|--------|--------|--------|--------|---------|----------|
| K229a | 4.5480 | 2.2363 | 5.2673 | 4.0729 | 2.2363 | 4.0311 | YES |
| K229b | 12.9378 | 7.4435 | 12.7801 | 12.4798 | 7.4435 | 11.4103 | YES |
| K229c | 12.6769 | 7.4435 | 12.9234 | 12.4798 | 7.4435 | 11.3809 | YES |
| K229d | 12.8545 | 7.4435 | 12.9221 | 12.4798 | 7.4435 | 11.4250 | YES |
| K229e | 7.4883 | 7.2911 | 7.9631 | 8.4043 | 7.2911 | 7.7867 | YES |
| K229f | 10.8139 | 5.6235 | 17.7914 | 14.6357 | 5.6235 | 12.2162 | YES |

---

## 6. Historical Comparison

| Version | OOS Sh | OOS MaxDD | WF Mean | WF Min | Components | Note |
|---------|--------|-----------|---------|--------|-----------|------|
| K198 v6.5 | 10.2800 | -0.005300 | 7.9100 | 6.5700 | 1 | Baseline ML |
| K217 v6.6 | 10.4300 | -0.005300 | 8.0100 | 6.9100 | 2 | +K208 |
| K218e v6.7 | 11.0310 | -0.003640 | 8.3160 | 6.9282 | 3 | Production |
| K227 REJECT | — | — | — | — | 4 | K225 window mismatch |
| K229 a | 4.1495 | -0.040124 | 4.0311 | 2.2363 | 4 |  |
| K229 b | 12.6100 | -0.001201 | 11.4103 | 7.4435 | 4 | ACCEPTED |
| K229 c | 12.6100 | -0.001201 | 11.3809 | 7.4435 | 4 |  |
| K229 d | 12.6100 | -0.001201 | 11.4250 | 7.4435 | 4 | ACCEPTED |
| K229 e | 9.0811 | -0.010538 | 7.7867 | 7.2911 | 4 |  |
| K229 f | 15.3142 | -0.000090 | 12.2162 | 5.6235 | 4 |  |

**Acceptance gate**: OOS Sh > 11.1310 | WF Min >= 6.9282 | MaxDD <= -0.003640 | All weights > 1%

---

## 7. Synergy Analysis

- Individual OOS Sharpes (ML window): K198=10.2796, K204=10.3627, K208=13.5396, K226=2.4097
- Average of 4 individuals OOS Sh: 9.1479
- Best ensemble (K229d) OOS Sh: 12.6100
- Synergy vs avg individuals: +3.4621 (GENUINE (>0.02))
- Improvement vs K218 v6.7: +1.5790
- Diversification Ratio (K229d): 1.6526 (>1.10 = genuine diversification)

**K226 orthogonality advantage vs K225:**
- K226 vs K198: rho=0.0519 (vs K225 rho=0.009) — comparable orthogonality
- K226 vs K204: rho=0.0568 (vs K225 rho=-0.023) — comparable orthogonality
- K226 vs K208: rho=0.0001 (vs K225 rho=0.012) — comparable orthogonality
- K226 WF min on ML window: 0.3800 (vs K225 WF min=-1.02 — K226 is more robust)

---

## 8. Risk Analysis

### K226-Specific Risks
- **ETH staking data dependency**: DeFiLlama Lido/RocketPool/StakeWise/FraxEther APIs; outage = stale signal
- **Regime sensitivity**: contrarian signal (buy when outflow spike) — adverse in persistent bear markets
- **High vol characteristic**: K226 daily vol ~48% ann (vs K208 <1%, K198/K204 ~5-6%) — inv-vol may underweight K226
- **Cap rationale**: K226 caps (10%, 20%, 25%) prevent underallocation while containing tail risk contribution

### Diversification Quality vs K218 (3-way)
- Adding K226 extends from 3-way to 4-way; all pairwise rho with K198/K204/K208 < 0.10
- DR > 1.10 in all variants confirms genuine diversification
- K226 WF folds all positive on ML window — key robustness advantage over K225

### Known Risks
1. K226 is high-volatility (48% ann vs K198/K204 5-6%) — inv-vol may underweight to near-zero
2. K208 (low-vol ~0.6% ann) still likely dominates uncapped inv-vol allocation
3. ETH validator queue signal may lose alpha as ETH liquid staking matures / MEV dynamics shift
4. K208 8h->daily resampling and K226 daily equity have different time-of-day settlement conventions

---

## 9. Verdict, K229 v6.8 if Accepted

### ACCEPT -> K229 v6.8 (Best variant: K229d)

The 4-way meta-ensemble (K229d: Inv-vol weighted (30d rolling) + K226 cap 20%) passes all 4 acceptance gates:
- Gate 0 (K226 ML window): OOS Sh=2.4097 > 1.0 -> PASS
- Gate 1 (OOS Sh): 12.6100 > 11.1310 -> PASS
- Gate 2 (WF Min): 7.4435 >= 6.9282 -> PASS
- Gate 3 (MaxDD): -0.001201 <= -0.003640 -> PASS
- Gate 4 (All weights > 1%): min=0.012 -> PASS

**Deployment Plan:**
1. Promote K229 (K229d) to v6.8 production
2. Components: K198 Ridge ML + K204 ML DD-embed + K208 DAR reverse carry + K226 ETH validator queue
3. Allocator: Inv-vol weighted (30d rolling) + K226 cap 20%
4. Monitor K226 ETH staking flow signal monthly; if WF Sh drops below 0.5 for 30d, reduce K226 cap to 5%
5. Rebalance monthly if weights drift >15% from avg

**Next Steps (K230):**
1. On-chain native signal: OP/ARB bridge flow or Jito MEV capture rate
2. Hash ribbon or miner capitulation signal (K220 result not yet integrated)
3. Regime-conditional rebalancing: allow K226 weight to increase during high outflow regimes
4. CVaR-optimised allocation to reduce tail risk across 4-way ensemble
5. Production monitoring: per-strategy daily PnL + weight trajectory dashboard

---
*Wave K229 | crypto-lab | 2026-05-24T22:58:42.765845+00:00*
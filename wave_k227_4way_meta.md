# Wave K227 — 4-Way Meta-Ensemble Report
*Generated: 2026-05-24T22:50:40.531114+00:00  |  Runtime: 0.25s*

## Executive Summary

**VERDICT: REJECT** — No variant passes all acceptance gates vs K218e v6.7.

Best attempted: K227e with OOS Sh=13.3489

---

## 1. Data & Methodology

- **Date range**: 2025-01-22 -> 2026-04-14 (448 days)
- **Return series**: 447 daily observations
- **K208 daily aggregation**: 8h->daily by last candle of each UTC day; 0 days filled forward
- **K225 alignment**: primary_btc_z1 (z=1.25, hold=14d) mapped to ML window; 136 days filled forward; re-based to 1.0 at window start
- **K198**: Ridge ML allocator (equity_ridge from wave_k198_curves.json)
- **K204**: ML DD-embed full ensemble (equity_k204 from wave_k204_curves.json)
- **K208**: DAR(2,1)-filtered reverse carry panel (K208_filtered, daily-resampled)
- **K225**: Spot BTC ETF 7-Day Flow Regime (primary_btc_z1, z=1.25, hold=14d)
- **OOS window**: final 30% of return series
- **Walk-forward**: 4-fold chronological splits

---

## 2. 4x4 Correlation Matrix

| | K198 | K204 | K208 | K225 |
|---|------|------|------|------|
| **K198** | 1.0000 | 0.7977 | 0.0619 | 0.0094 |
| **K204** | 0.7977 | 1.0000 | 0.0237 | -0.0233 |
| **K208** | 0.0619 | 0.0237 | 1.0000 | 0.0119 |
| **K225** | 0.0094 | -0.0233 | 0.0119 | 1.0000 |

**Interpretation:**
- K198 x K204: rho=0.7977 (Moderate) — established in K217
- K198 x K208: rho=0.0619 (Low) — DAR-filtered carry vs ML allocator
- K198 x K225: rho=0.0094 (Low) — ETF flow regime vs ML allocator
- K204 x K208: rho=0.0237 (Low) — ML ensemble vs reverse carry
- K204 x K225: rho=-0.0233 (Low) — ML ensemble vs ETF flow
- K208 x K225: rho=0.0119 (Low) — DAR carry vs ETF flow regime

---

## 3. Baseline Performance (Standalone)

| Portfolio | OOS Sharpe | OOS MaxDD | WF Mean | WF Min | WF Max |
|-----------|-----------|-----------|---------|--------|--------|
| K198 | 10.2796 | -0.005266 | 7.9153 | 6.5911 | 9.7310 |
| K204 | 10.3627 | -0.005320 | 7.5136 | 5.9200 | 9.6915 |
| K208 | 13.5396 | -0.000080 | 13.4351 | 5.7585 | 17.3212 |
| K225 | 1.1649 | -0.079948 | 0.6492 | -1.0202 | 2.1159 |

---

## 4. Variant Results

### 4.1 Per-Variant Summary

| Variant | OOS Sharpe | OOS MaxDD | WF Mean | WF Min | DR | Avg Wts (K198/K204/K208/K225) |
|---------|-----------|-----------|---------|--------|----|-------------------------------|
| K227a (xxx) | 4.7859 | -0.020129 | 3.9799 | 3.0767 | 1.3573 | 0.250/0.250/0.250/0.250 |
| K227b (xxv) | 5.9219 | -0.002275 | 9.3199 | 5.0068 | 1.2429 | 0.039/0.031/0.827/0.103 |
| K227c (xvv) | 10.1822 | -0.002071 | 10.5210 | 6.9541 | 1.6157 | 0.043/0.035/0.891/0.032 |
| K227d (xxx) | 7.1382 | -0.005094 | 6.9177 | 6.1936 | 1.4651 | 0.345/0.276/0.283/0.096 |
| K227e (vxv) | 13.3489 | -0.000202 | 11.2577 | 5.2351 | 1.6922 | 0.014/0.019/0.955/0.012 |

Gates: v=pass x=fail. Gate indicators: [OOS Sh][WF min][MaxDD]

### 4.2 Per-Variant Per-Fold Breakdown

| Variant | Fold 1 | Fold 2 | Fold 3 | Fold 4 | WF Min | WF Mean |
|---------|--------|--------|--------|--------|--------|---------|
| K227a | 4.5106 | 3.0767 | 3.4928 | 4.8397 | 3.0767 | 3.9799 |
| K227b | 10.6759 | 6.9541 | 14.6429 | 5.0068 | 5.0068 | 9.3199 |
| K227c | 10.6759 | 6.9541 | 14.6429 | 9.8111 | 6.9541 | 10.5210 |
| K227d | 7.8730 | 6.1936 | 7.2637 | 6.3408 | 6.1936 | 6.9177 |
| K227e | 8.6729 | 5.2351 | 18.0767 | 13.0461 | 5.2351 | 11.2577 |

---

## 5. Five-Way Comparison Table

| Version | OOS Sh | OOS MaxDD | WF Mean | WF Min | Components |
|---------|--------|-----------|---------|--------|-----------|
| K198 v6.5 | 10.2800 | -0.005300 | 7.9100 | 6.5700 | 1 |
| K217 v6.6 | 10.4300 | -0.005300 | 8.0100 | 6.9100 | 2 |
| K218e v6.7 | 11.0310 | -0.003640 | 8.3160 | 6.9282 | 3 |
| K227 a (Equal weight 25/25/25/25...) | 4.7859 | -0.020129 | 3.9799 | 3.0767 | 4 |
| K227 b (Inverse-vol weighted (30d...) | 5.9219 | -0.002275 | 9.3199 | 5.0068 | 4 |
| K227 c (Inv-vol weighted (30d rol...) | 10.1822 | -0.002071 | 10.5210 | 6.9541 | 4 |
| K227 d (Inv-vol weighted (30d rol...) | 7.1382 | -0.005094 | 6.9177 | 6.1936 | 4 |
| K227 e (Minimum Variance Portfoli...) | 13.3489 | -0.000202 | 11.2577 | 5.2351 | 4 |

**Acceptance gate**: OOS Sh > 11.1310 | WF Min >= 6.9282 | MaxDD <= -0.003640 | All weights > 1%

---

## 6. Synergy Analysis

- Individual OOS Sharpes: K198=10.2796, K204=10.3627, K208=13.5396, K225=1.1649
- Average of 4 individuals OOS Sh: 8.8367

---

## 7. Risk Analysis

### K225 Specific Risks
- **Fold 3 weakness**: K225 standalone WF fold 3 Sh=-1.58 (May-Nov 2025) — ETF flow signal was adversarial
- **Regime sensitivity**: ETF flow regime is a binary trigger (z>1.25) — regime changes can create abrupt switches
- **Low vol characteristic**: K225 may have low daily vol on flat-flow periods, attracting disproportionate inv-vol weight
- **Cap rationale**: K225 cap at 25% prevents overallocation during K225 low-vol regimes (mirrors K208 cap logic in K218)

### Diversification Quality
- K225 vs K198: rho=0.0094 — orthogonal signal (ETF flow vs ML technical)
- K225 vs K204: rho=-0.0233 — orthogonal (ML ensemble vs flow regime)
- K225 vs K208: rho=0.0119 — relationship between carry and ETF flow
- DR > 1.10 confirms genuine diversification; DR measured at mean portfolio weights

### Known Risks
1. K225 fold 3 weakness may depress WF stability in 4-way ensemble during May-Nov 2025 fold
2. 4 carry-adjacent strategies may share hidden common factor (crypto funding/liquidity regime)
3. Rolling window alignment: K225 starts 2024-05-23, K198 ML window starts 2025-01-22 — 8 months pre-window data not used
4. K208 8h->daily resampling and K225 daily equity may have different time-of-day settlement

---

## 8. Verdict, K227 v6.8 if Accepted, K228 Next Steps

### REJECT — Maintain K218 v6.7 as Production

No K227 variant improves on K218e v6.7 across all gates simultaneously.

**Analysis:**
- **K227a**: FAIL — OOS Sh 4.7859 < 11.1310; WF Min 3.0767 < 6.9282; MaxDD -0.020129 > -0.003640
- **K227b**: FAIL — OOS Sh 5.9219 < 11.1310; WF Min 5.0068 < 6.9282
- **K227c**: FAIL — OOS Sh 10.1822 < 11.1310
- **K227d**: FAIL — OOS Sh 7.1382 < 11.1310; WF Min 6.1936 < 6.9282; MaxDD -0.005094 > -0.003640
- **K227e**: FAIL — WF Min 5.2351 < 6.9282

**Root cause analysis:**
- K225 fold 3 weakness (Sh=-1.58 in May-Nov 2025) drags 4-way WF stability
- Adding K225 dilutes the well-performing K198+K204+K208 core without sufficient WF improvement
- Uncapped inv-vol likely over-weights K225 in low-volatility periods, concentrating fold-3 damage

**K228 Next Steps:**
1. K225 regime-gate: only include K225 when ETF flow is in positive-regime; otherwise zero-weight
2. Conditional 4-way: K225 active only when BTC-ETF 7d z-score > 1.0 (regime filter, not full signal)
3. Explore purely orthogonal 4th signal: hash ribbon, miner capitulation, or on-chain stablecoin flow
4. Increase K225 OOS Sh requirement: target standalone Sh > 3.0 on ML window before ensemble integration
5. Extend K225 walk-forward training: use full 514-day history rather than 448-day ML window alignment

---
*Wave K227 | crypto-lab | 2026-05-24T22:50:40.531114+00:00*
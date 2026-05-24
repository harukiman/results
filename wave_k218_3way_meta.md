# Wave K218 — 3-Way Meta-Ensemble Report
*Generated: 2026-05-24T22:13:16.614927+00:00  |  Runtime: 0.19s*

## Executive Summary

**VERDICT: ACCEPT as K218 v6.7** — Best variant: K218e

| Metric | K217 v6.6 (prod) | K218e | Delta |
|--------|-----------------|-----------|-------|
| OOS Sharpe | 10.4300 | 11.0310 | +0.6010 |
| OOS MaxDD  | -0.005300 | -0.003640 | +0.001660 |
| WF Mean    | 8.0100 | 8.3160 | +0.3060 |
| WF Min     | 6.9100 | 6.9282 | +0.0182 |
| DR         | N/A | 1.0795 | — |

---

## 1. Data & Methodology

- **Date range**: 2025-01-22 → 2026-04-14 (448 days)
- **Return series**: 447 daily observations
- **K208 daily aggregation**: 8h→daily by taking last candle of each UTC day; 0 days filled forward
- **K198**: Ridge ML allocator (best variant: P3 risk-parity), equity_ridge from wave_k198_curves.json
- **K204**: ML DD-embed full ensemble, equity_k204 from wave_k204_curves.json
- **K208**: DAR(2,1)-filtered reverse carry panel (K208_filtered), daily-resampled from wave_k208_curves.json
- **OOS window**: final 30% of return series
- **Walk-forward**: 4-fold chronological splits

---

## 2. Pairwise Correlation Matrix

| | K198 | K204 | K208 |
|---|------|------|------|
| **K198** | 1.0000 | 0.7977 | 0.0619 |
| **K204** | 0.7977 | 1.0000 | 0.0237 |
| **K208** | 0.0619 | 0.0237 | 1.0000 |

**Interpretation:**
- K198 × K204: ρ=0.7977 (Moderate) — established in K217
- K198 × K208: ρ=0.0619 (Low) — K208 is pure reverse carry sleeve; K198 contains V_rev_carry as one of 10 features
- K204 × K208: ρ=0.0237 (Low) — K204 is the full ML ensemble; K208 is a concentrated reverse carry factor
- K208 provides **genuine orthogonality** vs both K198 and K204 (all pairs < 0.5)

---

## 3. Baseline Performance (Standalone)

| Portfolio | OOS Sharpe | OOS MaxDD | WF Mean | WF Min | WF Max |
|-----------|-----------|-----------|---------|--------|--------|
| K198 | 10.2796 | -0.005266 | 7.9153 | 6.5911 | 9.7310 |
| K204 | 10.3627 | -0.005320 | 7.5136 | 5.9200 | 9.6915 |
| K208 | 13.5396 | -0.000080 | 13.4351 | 5.7585 | 17.3212 |

---

## 4. Variant Results

### 4.1 Per-Variant Summary

| Variant | OOS Sharpe | OOS MaxDD | WF Mean | WF Min | DR | Avg Wts (K198/K204/K208) |
|---------|-----------|-----------|---------|--------|----|--------------------------|
| K218a | 11.1297 | -0.003456 | 8.2739 | 6.8540 | 1.0823 | 0.333/0.333/0.333 |
| K218b | 13.7295 | -0.001353 | 12.1662 | 6.8984 | 1.4070 | 0.045/0.037/0.918 |
| K218c | 11.6917 | -0.002568 | 8.0404 | 6.3079 | 1.1008 | 0.270/0.274/0.457 |
| K218d | 15.2029 | -0.000062 | 11.8191 | 5.2333 | 1.2887 | 0.007/0.014/0.979 |
| K218e | 11.0310 | -0.003640 | 8.3160 | 6.9282 | 1.0795 | 0.385/0.315/0.300 |
| K218f | 10.6703 | -0.004462 | 8.1210 | 6.9405 | 1.0650 | 0.500/0.350/0.150 |

### 4.2 Per-Variant Per-Fold Breakdown

| Variant | Fold 1 | Fold 2 | Fold 3 | Fold 4 | Min | Mean |
|---------|--------|--------|--------|--------|-----|------|
| K218a | 7.2789 | 6.8540 | 8.3844 | 10.5782 | 6.8540 | 8.2739 |
| K218b | 12.2676 | 6.8984 | 15.9773 | 13.5214 | 6.8984 | 12.1662 |
| K218c | 6.3079 | 7.2559 | 7.4690 | 11.1290 | 6.3079 | 8.0404 |
| K218d | 9.2182 | 5.2333 | 18.2913 | 14.5338 | 5.2333 | 11.8191 |
| K218e | 7.5144 | 6.9282 | 8.3475 | 10.4739 | 6.9282 | 8.3160 |
| K218f | 7.2452 | 6.9405 | 8.1991 | 10.0993 | 6.9405 | 8.1210 |

---

## 5. Four-Way Comparison Table

| Version | OOS Sh | OOS MaxDD | WF Mean | WF Min | DR |
|---------|--------|-----------|---------|--------|----|
| K198 v6.5 | 10.2800 | -0.005300 | 7.9100 | 6.5700 | — |
| K217b v6.6 (prod) | 10.4300 | -0.005300 | 8.0100 | 6.9100 | — |
| K218a | 11.1297 | -0.003456 | 8.2739 | 6.8540 | 1.0823 |
| K218b | 13.7295 | -0.001353 | 12.1662 | 6.8984 | 1.4070 |
| K218c | 11.6917 | -0.002568 | 8.0404 | 6.3079 | 1.1008 |
| K218d | 15.2029 | -0.000062 | 11.8191 | 5.2333 | 1.2887 |
| K218e | 11.0310 | -0.003640 | 8.3160 | 6.9282 | 1.0795 |
| K218f | 10.6703 | -0.004462 | 8.1210 | 6.9405 | 1.0650 |

**Acceptance gate**: OOS Sh > 10.48 | WF Min ≥ 6.91 | MaxDD ≤ -0.0053 | All weights > 1%

---

## 6. Synergy Analysis

- Average of 3 individuals OOS Sh: 11.3940
- Best ensemble (K218e) OOS Sh: 11.0310
- Synergy vs avg individuals: -0.3630 (WEAK/NONE)
- Improvement vs K217 v6.6: +0.6010

---

## 7. Risk Analysis

### K208 Standalone Characteristics
- **Nature**: Pure DAR(2,1)-filtered reverse carry panel (10 symbols, 9 passing DAR direction accuracy)
- **8h resolution collapsed to daily**: last-tick sampling may introduce micro-bias
- **Concentrated sleeve**: Very low MaxDD in isolation, but high vol regime sensitivity
- **Overlap with K198**: K198 contains V_rev_carry as one of 10 Ridge features — partial overlap expected

### Diversification Ratio Interpretation
- DR > 1.10 = genuine diversification benefit
- DR ≈ 1.00 = no meaningful benefit from combining

### Known Risks
1. K208 8h→daily resampling may not perfectly align with K198/K204 daily closes
2. K198 vs K208 correlation (ρ=0.0619) — K208 reverse carry overlaps K198 V_rev_carry sleeve
3. K208 equity starts at 1.0 (mapped from cumulative PnL) — may not reflect identical capital base
4. 3-way ensemble has more parameters to estimate → increased risk of lookahead bias in adaptive variants

---

## 8. Verdict & Deployment Plan

### ACCEPT → K218 v6.7 (Best variant: K218e)

The 3-way meta-ensemble (K218e: Inv-vol weighted (30d rolling) + K208 max-weight cap 30%) passes all acceptance gates:
- OOS Sharpe 11.0310 > gate 10.48 (PASS)
- WF Min 6.9282 >= gate 6.91 (PASS)
- MaxDD -0.003640 <= gate -0.0053 (PASS)
- All 3 portfolios non-zero (min weight = 0.300) (PASS)

**Deployment Plan:**
1. Promote K218 (K218e) to v6.7 production
2. Weights: K198 Ridge ML allocator + K204 ML DD-embed + K208 DAR-filtered reverse carry
3. Allocator: Inv-vol weighted (30d rolling) + K208 max-weight cap 30%
4. Monitor: Track per-portfolio performance weekly; rebalance monthly if weights drift >15%
5. Fallback: Revert to K217b if K208 sleeve enters persistent drawdown (>3× historical MaxDD)

---
*Wave K218 | crypto-lab | 2026-05-24T22:13:16.614927+00:00*
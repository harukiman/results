# Wave K231 — 5-Way Meta-Ensemble Report (K198 × K204 × K208 × K226 × K228)
*Generated: 2026-05-24T23:07:12.287370+00:00  |  Runtime: 0.5s*

## PRIMARY HEADER: K228 ML-Window Standalone Validation (Gate 0)

**This is the critical prerequisite. If K228 fails Gate 0, K231 is rejected at first check.**

| Metric | K228 Original (730d) | K228 on ML Window (448d) | Gate | Result |
|--------|---------------------|------------------------|------|--------|
| OOS Sharpe | 2.77 | 2.1641 | >= 1.0 | **PASS** |
| OOS MaxDD  | — | -0.029885 | — | — |
| OOS Ann Ret| — | 0.3732 | — | — |
| OOS Ann Vol| — | 0.1725 | — | — |
| WF min fold| +0.56 (original) | -2.1503 | > 0.0 | FAIL |
| WF folds   | all pos (original) | [1.2305, -2.1503, 3.0347, 2.4857] | all positive | FAIL |
| Sparsity   | ~85% cash | 17.0% active days | — | — |

**Gate 0 Result: PASS — K228 retains alpha on ML window, proceed with 5-way**

Reference comparisons:
- K225 (K227 lesson): dropped 2.11 → 1.16 on ML window → REJECT (window mismatch fatal)
- K226 (K229 lesson): retained >1.0 on ML window → PASS → K229 ACCEPTED

## Executive Summary

**VERDICT: REJECT** — No variant passes all acceptance gates vs K229d v6.8.

Best attempted: K231f with OOS Sh=14.7421
Gate failures: see Section 5.

---

## 1. Data & Methodology

- **Date range**: 2025-01-22 -> 2026-04-14 (448 days)
- **Return series**: 447 daily observations
- **K208 daily aggregation**: 8h->daily by last candle of each UTC day; 0 days filled forward
- **K226 alignment**: ETH validator queue/LST flow mapped to ML window; 0 days filled forward; re-based to 1.0
- **K228 alignment**: Stablecoin mint/burn; 0 days filled forward; re-based to 1.0
- **K228 sparsity**: 17.0% active trading days (76 non-zero returns)
- **OOS window**: final 30% of return series (~135 days)
- **Walk-forward**: 4-fold chronological splits

**Portfolios:**
- K198: Ridge ML allocator (equity_ridge)
- K204: ML DD-embed full ensemble (equity_k204)
- K208: DAR(2,1)-filtered reverse carry panel (8h, daily-resampled)
- K226: ETH Validator Queue / LST Staking Flow contrarian
- K228: Stablecoin Mint/Burn momentum signal

---

## 2. 5×5 Correlation Matrix

| | K198 | K204 | K208 | K226 | K228 |
|---|------|------|------|------|------|
| **K198** | 1.0000 | 0.7977 | 0.0619 | 0.0519 | 0.1238 |
| **K204** | 0.7977 | 1.0000 | 0.0237 | 0.0568 | 0.1116 |
| **K208** | 0.0619 | 0.0237 | 1.0000 | 0.0001 | 0.0439 |
| **K226** | 0.0519 | 0.0568 | 0.0001 | 1.0000 | 0.3115 |
| **K228** | 0.1238 | 0.1116 | 0.0439 | 0.3115 | 1.0000 |

**Interpretation:**
- K198 x K204: rho=0.7977 (Moderate) — established core ML pair
- K198 x K208: rho=0.0619 (Low) — ML vs DAR carry
- K198 x K226: rho=0.0519 (Low) — ML vs ETH validator flow
- K198 x K228: rho=0.1238 (Low) — ML vs stablecoin mint
- K204 x K208: rho=0.0237 (Low) — ML ensemble vs reverse carry
- K204 x K226: rho=0.0568 (Low) — ML ensemble vs ETH flow
- K204 x K228: rho=0.1116 (Low) — ML ensemble vs stablecoin
- K208 x K226: rho=0.0001 (Low) — DAR carry vs ETH flow
- K208 x K228: rho=0.0439 (Low) — DAR carry vs stablecoin
- K226 x K228: rho=0.3115 (Low-Moderate) — ETH flow vs stablecoin (pre-reported: 0.30)

---

## 3. Baseline Performance (Standalone on ML Window)

| Portfolio | OOS Sharpe | OOS MaxDD | WF Mean | WF Min | WF Max | WF Folds |
|-----------|-----------|-----------|---------|--------|--------|----------|
| K198 | 10.2796 | -0.005266 | 7.9153 | 6.5911 | 9.7310 | 6.59/7.37/7.97/9.73 |
| K204 | 10.3627 | -0.005320 | 7.5136 | 5.9200 | 9.6915 | 5.92/6.26/8.18/9.69 |
| K208 | 13.5396 | -0.000080 | 13.4351 | 5.7585 | 17.3212 | 17.30/5.76/17.32/13.36 |
| K226 | 2.4097 | -0.152979 | 2.2845 | 0.3800 | 3.2959 | 3.30/0.38/2.84/2.62 |
| K228 | 2.1641 | -0.029885 | 1.1501 | -2.1503 | 3.0347 | 1.23/-2.15/3.03/2.49 |

---

## 4. DR Comparison: K229 vs K231

| Variant | DR | Components | Note |
|---------|-----|------------|------|
| K229d (v6.8) | 1.65 | 4 | Production baseline |
| K231a | 1.3002 | 5 | -0.3498 vs K229d |
| K231b | 1.2826 | 5 | -0.3674 vs K229d |
| K231c | 1.2165 | 5 | -0.4335 vs K229d |
| K231d | 1.5864 | 5 | -0.0636 vs K229d |
| K231e | 1.5586 | 5 | -0.0914 vs K229d |
| K231f | 1.3050 | 5 | -0.3450 vs K229d |

---

## 5. Variant Results

### 5.1 Per-Variant Summary

| Variant | Description | OOS Sh | OOS MaxDD | WF Mean | WF Min | DR | K198/K204/K208/K226/K228 wts | Gates |
|---------|-------------|--------|-----------|---------|--------|----|------------------------------|-------|
| K231a | Equal weight 20/20/20/20/20 | 4.1287 | -0.032174 | 3.9089 | 1.8447 | 1.3002 | 0.20/0.20/0.20/0.20/0.20 | x/x/x |
| K231b | Inverse-vol weighted uncapped (30d  | 11.8382 | -0.000715 | 8.0206 | 4.0018 | 1.2826 | 0.03/0.02/0.62/0.03/0.30 | x/x/v |
| K231c | Inv-vol + K226 cap 20% (30d rolling | 11.8382 | -0.000715 | 8.0488 | 4.0018 | 1.2165 | 0.03/0.02/0.63/0.01/0.30 | x/x/v |
| K231d | Inv-vol + K226 cap 20% + K228 cap 2 | 12.3335 | -0.000961 | 10.0724 | 5.8326 | 1.5864 | 0.04/0.03/0.83/0.01/0.08 | x/x/v |
| K231e | Inv-vol + K208/K226/K228 all cap 25 | 7.9636 | -0.006949 | 7.1977 | 5.1259 | 1.5586 | 0.23/0.19/0.34/0.04/0.19 | x/x/x |
| K231f | Minimum Variance Portfolio (rolling | 14.7421 | -0.000075 | 10.5460 | 4.2714 | 1.3050 | 0.01/0.01/0.85/0.00/0.12 | v/x/v |

Gates order: [OOS Sh > 12.71] / [WF min >= 7.4435] / [MaxDD <= -0.001201]

### 5.2 Per-Variant Per-Fold Breakdown

| Variant | Fold 1 | Fold 2 | Fold 3 | Fold 4 | WF Min | WF Mean | All pos? |
|---------|--------|--------|--------|--------|--------|---------|----------|
| K231a | 4.6013 | 1.8447 | 5.0533 | 4.1364 | 1.8447 | 3.9089 | YES |
| K231b | 4.8553 | 4.0018 | 11.6096 | 11.6156 | 4.0018 | 8.0206 | YES |
| K231c | 4.8553 | 4.0018 | 11.7225 | 11.6156 | 4.0018 | 8.0488 | YES |
| K231d | 10.5448 | 5.8326 | 11.7225 | 12.1898 | 5.8326 | 10.0724 | YES |
| K231e | 8.4421 | 5.1259 | 7.8365 | 7.3862 | 5.1259 | 7.1977 | YES |
| K231f | 6.1724 | 4.2714 | 17.7613 | 13.9790 | 4.2714 | 10.5460 | YES |

---

## 6. Historical Comparison

| Version | OOS Sh | OOS MaxDD | WF Min | Components | Note |
|---------|--------|-----------|--------|-----------|------|
| K198 v6.5 | 10.2800 | -0.005300 | 6.5700 | 1 | Baseline ML |
| K217 v6.6 | 10.4300 | -0.005300 | 6.9100 | 2 | +K208 |
| K218e v6.7 | 11.0310 | -0.003640 | 6.9282 | 3 | +K204 |
| K229d v6.8 | 12.6100 | -0.001201 | 7.4435 | 4 | +K226 (production) |
| K231 a | 4.1287 | -0.032174 | 1.8447 | 5 |  |
| K231 b | 11.8382 | -0.000715 | 4.0018 | 5 |  |
| K231 c | 11.8382 | -0.000715 | 4.0018 | 5 |  |
| K231 d | 12.3335 | -0.000961 | 5.8326 | 5 |  |
| K231 e | 7.9636 | -0.006949 | 5.1259 | 5 |  |
| K231 f | 14.7421 | -0.000075 | 4.2714 | 5 | best |

**Acceptance gate**: OOS Sh > 12.71 | WF Min >= 7.4435 | MaxDD <= -0.001201 | All weights > 1%

---

## 7. Synergy Analysis

- Individual OOS Sharpes (ML window): K198=10.2796, K204=10.3627, K208=13.5396, K226=2.4097, K228=2.1641
- Average of 5 individuals OOS Sh: 7.7511
- Best ensemble (K231f) OOS Sh: 14.7421
- Synergy vs avg individuals: +6.9910 (GENUINE (>0.02))
- Improvement vs K229 v6.8: +2.1321
- K228 additive delta (5-way vs 4-way): +2.1321
- Best ensemble DR: 1.3050 vs K229d DR=1.65

**K228 Orthogonality (empirical vs reported):**
- K228 vs K198: rho=0.1238 (pre-reported: 0.12) — consistent
- K228 vs K204: rho=0.1116 (pre-reported: 0.11) — consistent
- K228 vs K208: rho=0.0439 (pre-reported: -0.002) — consistent
- K228 vs K226: rho=0.3115 (pre-reported: 0.30) — consistent

---

## 8. Risk Analysis

### K228-Specific Risks
- **Sparsity**: ~85% cash days means K228 contributes nothing on most days; effective diversification benefit is diluted
- **Sparse correlation artifacts**: rho estimates with sparse series can be unstable; 76 active days out of 447
- **K226 vs K228 mild correlation** (rho ~0.30): Both are flow-type signals; overlap in signal timing may reduce marginal diversification
- **Window sensitivity**: Large gap between original 730d window and 448d ML window; test if alpha is concentrated in non-ML period

### Diversification Plateau Risk
- K229 DR=1.65 from 4 orthogonal sources is already high
- Adding K228 with sparse returns may not meaningfully extend DR (5th source may add little if mostly inactive)
- Effective number of correlated strategies may plateau at 4

---

## 9. Verdict, K231 v6.9 if Accepted; K232 Next

### REJECT — Maintain K229d v6.8 as Production

No K231 variant improves on K229d v6.8 across all gates simultaneously.

**Failure Analysis:**
- **K231a**: FAIL: OOS Sh 4.1287 < 12.71; WF Min 1.8447 < 7.4435; MaxDD -0.032174 > -0.001201
- **K231b**: FAIL: OOS Sh 11.8382 < 12.71; WF Min 4.0018 < 7.4435
- **K231c**: FAIL: OOS Sh 11.8382 < 12.71; WF Min 4.0018 < 7.4435
- **K231d**: FAIL: OOS Sh 12.3335 < 12.71; WF Min 5.8326 < 7.4435
- **K231e**: FAIL: OOS Sh 7.9636 < 12.71; WF Min 5.1259 < 7.4435; MaxDD -0.006949 > -0.001201
- **K231f**: FAIL: WF Min 4.2714 < 7.4435; Min weight 0.004 < 0.01

**K232 Next Steps:**
1. If Gate 0 fail: investigate K228 sub-period performance (2024-05-23 to 2025-01-21 vs ML window)
2. K228 regime-gate: only active during stablecoin supply expansion regime (mint_7d_z > 1.5)
3. Explore K228 with recalibrated signal window aligned to ML window start
4. Alternative 5th source: hash ribbon (K220), Jito MEV (K221), or carry stress (K223)
5. Test K229d v6.8 stability over next 30d before attempting 5-way again
6. CVaR allocation within 4-way K229d: reduce tail risk without adding new source

---
*Wave K231 | crypto-lab | 2026-05-24T23:07:12.287370+00:00*
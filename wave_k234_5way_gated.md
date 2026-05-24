# Wave K234 — 5-Way Meta-Ensemble Report (K198 × K204 × K208 × K226 × K232b)
*Generated: 2026-05-24T23:22:43.061493+00:00  |  Runtime: 0.36s*

## Executive Summary

**VERDICT: REJECT** — No variant passes all acceptance gates vs K229d v6.8.

Best attempted: K234f with OOS Sh=14.7603

**Root cause:** K232b ML-window fold 2 = -1.4087 (gate requires >= -1.0; ungated K228 was -2.15 [-31% improved but insufficient])

---

## 1. K232b ML-Window Validation (CRITICAL CHECK — Gate 0)

**Context:**
- K231 REJECT: K229 + K228 (ungated) failed because K228 ML fold 2 = -2.15 caused WF drag
- K232b FIX: Soft regime gate on supply trend (z-score < -1.0 = contraction → K228 inactive)
- K232b standalone: OOS Sh 2.86, own-window all WF folds positive (min +0.56)
- Gate 0a: K232b ML fold 2 >= -1.0 (30% improvement milestone)

| Metric | K228 Ungated (K231) | K232b Gated | Gate | Result |
|--------|---------------------|-------------|------|--------|
| ML fold 2 Sh (date-based) | -2.1503 | -1.4087 | >= -1.0 | FAIL |
| Improvement  | baseline | +34.5% | >= 30% | PASS |
| ML OOS Sh    | 2.1641 | 1.8859 | >= 1.0 | PASS |
| ML WF folds (date-based) | [1.23, -2.15, 3.03, 2.49] | [1.225, -1.4087, 2.7242, 2.3266] | — | — |
| ML WF folds (index-based)| [1.23, -2.15, 3.03, 2.49] | [1.2305, -2.1503, 3.0261, 2.2956] | — | — |

**Gate 0 result: CONDITIONAL FAIL — fold 2 = -1.4087 still below -1.0 threshold**

Fold 2 corresponds to 2025-05-14 to 2025-09-02 (stablecoin contraction regime).
The soft gate reduced impact but did not fully neutralize the contraction-period drag.

---

## 2. Data & Methodology

- **Date range**: 2025-01-22 -> 2026-04-14 (448 days)
- **Return series**: 447 daily observations
- **K208 daily aggregation**: 8h->daily by last candle of each UTC day; 0 days filled forward
- **K226 alignment**: ETH validator queue/LST flow strategy mapped to ML window; 0 days filled forward
- **K232b alignment**: Regime-gated K228 equity curve mapped to ML window; 0 days filled forward
- **K232b active days**: 76 / 447 (17.0%)
- **K198**: Ridge ML allocator (equity_ridge from wave_k198_curves.json)
- **K204**: ML DD-embed full ensemble (equity_k204 from wave_k204_curves.json)
- **K208**: DAR(2,1)-filtered reverse carry panel (K208_filtered, daily-resampled)
- **K226**: ETH Validator Queue / LST Staking Flow contrarian (wave_k226_curves.json)
- **K232b**: K228 Stablecoin Mint/Burn with soft supply-trend regime gate (wave_k232_curves.json)
- **OOS window**: final 30% of return series (~135 days)
- **Walk-forward**: 4-fold chronological splits

---

## 3. 5x5 Correlation Matrix

| | K198 | K204 | K208 | K226 | K232b |
|---|------|------|------|------|-------|
| **K198**  | 1.0000 | 0.7977 | 0.0619 | 0.0519 | 0.0715 |
| **K204**  | 0.7977 | 1.0000 | 0.0237 | 0.0568 | 0.0802 |
| **K208**  | 0.0619 | 0.0237 | 1.0000 | 0.0001 | 0.0266 |
| **K226**  | 0.0519 | 0.0568 | 0.0001 | 1.0000 | 0.2915 |
| **K232b** | 0.0715 | 0.0802 | 0.0266 | 0.2915 | 1.0000 |

**Interpretation (K232b correlations):**
- K232b vs K198: rho=0.0715 (Low) — stablecoin mint vs ML allocator
- K232b vs K204: rho=0.0802 (Low) — stablecoin mint vs ML DD-embed
- K232b vs K208: rho=0.0266 (Low) — stablecoin mint vs reverse carry
- K232b vs K226: rho=0.2915 (Low) — stablecoin mint vs ETH staking flow
- K198 vs K204: rho=0.7977 (Moderate) — established core pair (unchanged from K229)

---

## 4. Baseline Performance (Standalone on ML Window)

| Portfolio | OOS Sharpe | OOS MaxDD | WF Mean | WF Min | WF Max | WF Folds |
|-----------|-----------|-----------|---------|--------|--------|----------|
| K198 | 10.2796 | -0.005266 | 7.9153 | 6.5911 | 9.7310 | 6.59/7.37/7.97/9.73 |
| K204 | 10.3627 | -0.005320 | 7.5136 | 5.9200 | 9.6915 | 5.92/6.26/8.18/9.69 |
| K208 | 13.5396 | -0.000080 | 13.4351 | 5.7585 | 17.3212 | 17.30/5.76/17.32/13.36 |
| K226 | 2.4097 | -0.152979 | 2.2845 | 0.3800 | 3.2959 | 3.30/0.38/2.84/2.62 |
| K232b | 1.8859 | -0.020724 | 1.1005 | -2.1503 | 3.0261 | 1.23/-2.15/3.03/2.30 |

---

## 5. Variant Results

### 5.1 Per-Variant Summary

| Variant | Description | OOS Sh | OOS MaxDD | WF Mean | WF Min | DR | K198/K204/K208/K226/K232b wts | Gates |
|---------|-------------|--------|-----------|---------|--------|----|-------------------------------|-------|
| K234a | Equal weight 20/20/20/20/20 | 4.1286 | -0.032174 | 3.9022 | 1.8447 | 1.2923 | 0.20/0.20/0.20/0.20/0.20 | x/x/x |
| K234b | Inverse-vol weighted (30d rollin | 11.9288 | -0.000715 | 8.0384 | 4.0019 | 1.3318 | 0.03/0.02/0.62/0.03/0.30 | x/x/v |
| K234c | Inv-vol weighted (30d rolling) + | 11.9288 | -0.000715 | 8.0666 | 4.0019 | 1.2646 | 0.03/0.02/0.63/0.01/0.30 | x/x/v |
| K234d | Inv-vol (30d) + K226 cap 20% + K | 12.3956 | -0.001081 | 10.4843 | 6.1448 | 1.7359 | 0.04/0.03/0.86/0.01/0.05 | x/x/v |
| K234e | Inv-vol (30d) + K226 cap 20% + K | 12.4265 | -0.000961 | 10.0913 | 5.8330 | 1.6539 | 0.04/0.03/0.83/0.01/0.09 | x/x/v |
| K234f | Minimum Variance Portfolio (roll | 14.7603 | -0.000075 | 8.1047 | -2.2297 | 1.5288 | 0.03/0.04/0.87/0.02/0.04 | v/x/v |

Gates order: [OOS Sh > 12.71] / [WF min >= 7.44] / [MaxDD <= -0.0012]

### 5.2 Per-Variant Per-Fold Breakdown

| Variant | Fold 1 | Fold 2 | Fold 3 | Fold 4 | WF Min | WF Mean | All pos? |
|---------|--------|--------|--------|--------|--------|---------|----------|
| K234a | 4.6013 | 1.8447 | 5.0511 | 4.1117 | 1.8447 | 3.9022 | YES |
| K234b | 4.8551 | 4.0019 | 11.6087 | 11.6880 | 4.0019 | 8.0384 | YES |
| K234c | 4.8551 | 4.0019 | 11.7216 | 11.6880 | 4.0019 | 8.0666 | YES |
| K234d | 11.8082 | 6.1448 | 11.7216 | 12.2627 | 6.1448 | 10.4843 | YES |
| K234e | 10.5446 | 5.8330 | 11.7216 | 12.2661 | 5.8330 | 10.0913 | YES |
| K234f | 2.8872 | -2.2297 | 17.7612 | 13.9999 | -2.2297 | 8.1047 | NO |

---

## 6. Historical Comparison (Production Progression)

| Version | OOS Sh | OOS MaxDD | WF Mean | WF Min | Components | Note |
|---------|--------|-----------|---------|--------|------------|------|
| K198 v6.5 | 10.2800 | -0.005300 | 7.9100 | 6.5700 | 1 | Baseline ML |
| K217 v6.6 | 10.4300 | -0.005300 | 8.0100 | 6.9100 | 2 | +K208 reverse carry |
| K218e v6.7 | 11.0310 | -0.003640 | 8.3160 | 6.9282 | 3 | 3-way meta |
| K229d v6.8 | 12.6100 | -0.001201 | 11.4250 | 7.4435 | 4 | +K226 ETH validator |
| K231 REJECT | — | — | — | — | 5 | K228 ungated fold 2=-2.15 |
| K232b fix | 2.86 | — | — | — | 1 | K228 soft-gated fold 2=-1.415 |
| K234 a | 4.1286 | -0.032174 | 3.9022 | 1.8447 | 5 |  |
| K234 b | 11.9288 | -0.000715 | 8.0384 | 4.0019 | 5 |  |
| K234 c | 11.9288 | -0.000715 | 8.0666 | 4.0019 | 5 |  |
| K234 d | 12.3956 | -0.001081 | 10.4843 | 6.1448 | 5 |  |
| K234 e | 12.4265 | -0.000961 | 10.0913 | 5.8330 | 5 |  |
| K234 f | 14.7603 | -0.000075 | 8.1047 | -2.2297 | 5 | best |

**Acceptance gate**: OOS Sh > 12.71 | WF Min >= 7.4435 | MaxDD <= -0.001201 | All weights > 1%

---

## 7. Synergy Analysis & DR Comparison

- Individual OOS Sharpes (ML window): K198=10.2796, K204=10.3627, K208=13.5396, K226=2.4097, K232b=1.8859
- Average of 5 individuals OOS Sh: 7.6955
- Best ensemble (K234f) OOS Sh: 14.7603
- Synergy vs avg individuals: +7.0648 (GENUINE (>0.02))
- Improvement vs K229 v6.8: +2.1503
- Diversification Ratio — K229d: 1.6526  |  K234 K234f: 1.5288

**K232b orthogonality vs core ensemble:**
- K232b vs K198: rho=0.0715 (Low) — orthogonal if |rho| < 0.3
- K232b vs K226: rho=0.2915 (Low) — mild co-movement (both on-chain flow signals)
- K232b vs K208: rho=0.0266 (Low) — carry vs stablecoin (structural independence)

---

## 8. Risk Analysis

### K232b-Specific Risks
- **Regime gate effectiveness**: soft gate (-1.415 fold 2) shows 30% improvement but not full remediation
- **Stablecoin data dependency**: requires reliable supply data (DeFiLlama/Coinglass); outage = stale signal
- **Contraction regime**: K232b signal reversal risk during rapid USDT/USDC contraction periods
- **Sparsity**: K232b only active ~17% of days — inv-vol may assign disproportionate weight on active days

### Ensemble-Level Risks
- **K208 dominance**: inv-vol still likely assigns 80-90% to K208 (ultra-low vol); capped variants mitigate
- **Gate 0a failure implication**: if fold 2 gate fails, K234 cannot be accepted even with good ensemble metrics
- **Window boundary**: ML window ends 2026-04-14; any regime shift post-boundary not captured

---

## 9. Verdict, K234 v6.9 if Accepted; K235 Next Steps

### REJECT — Maintain K229d v6.8 as Production

No K234 variant improves on K229d v6.8 across all gates simultaneously.

**Failure Analysis:**
- **Gate 0a FAIL**: K232b ML fold 2 = -1.4087 < threshold -1.0
  - K231 ungated: -2.1503  ->  K232b gated: -1.4087  (improvement: +34.5%)
  - Soft gate partially effective but fold 2 period (2025-05-14 to 2025-09-02) remains negative
  - Implication: harder gate needed (e.g. supply_z < -1.5 or rolling 90d trend crossover)

- **K234a**: FAIL: Gate 0a K232b fold 2 FAIL (-1.4087<-1.0); OOS Sh 4.1286 < 12.71; WF Min 1.8447 < 7.4435; MaxDD -0.032174 > -0.001201
- **K234b**: FAIL: Gate 0a K232b fold 2 FAIL (-1.4087<-1.0); OOS Sh 11.9288 < 12.71; WF Min 4.0019 < 7.4435
- **K234c**: FAIL: Gate 0a K232b fold 2 FAIL (-1.4087<-1.0); OOS Sh 11.9288 < 12.71; WF Min 4.0019 < 7.4435
- **K234d**: FAIL: Gate 0a K232b fold 2 FAIL (-1.4087<-1.0); OOS Sh 12.3956 < 12.71; WF Min 6.1448 < 7.4435
- **K234e**: FAIL: Gate 0a K232b fold 2 FAIL (-1.4087<-1.0); OOS Sh 12.4265 < 12.71; WF Min 5.8330 < 7.4435
- **K234f**: FAIL: Gate 0a K232b fold 2 FAIL (-1.4087<-1.0); WF Min -2.2297 < 7.4435

**K235 Next Steps:**
1. K233/K235: Harder K228 regime gate — supply_z < -1.5 (vs -1.0 soft gate in K232b)
   Goal: fully eliminate fold 2 drag to achieve fold 2 >= 0.0
2. Alternative 5th signal: OP/ARB bridge flow, Jito MEV, or hash ribbon (non-stablecoin)
3. Investigate K232b fold 2 root cause: 2025-07/08 stablecoin contraction → specific dates
4. Portfolio-level regime gate: suspend K232b at ensemble level during broad crypto contraction
5. Return to K229d v6.8 as stable production — WF min 7.44 remains excellent

---
*Wave K234 | crypto-lab | 2026-05-24T23:22:43.061493+00:00*
# Wave K509 — K208 Funding Rate Decay Verification (R15-12)

**Date:** 2026-05-30
**Status:** VERIFICATION COMPLETE — **CONFIRM decay**
**Verdict:** Sharpe degraded -67.0% from 2024H2 to 2026YTD. R15-12 claim of -60% Y/Y is substantiated. Urgent K280 rebalance recommended.
**Recommended action:** URGENT: Reduce K280 K208 sleeve weight from 65-75% to 35-45%. Activate K492 Variant E immediately. Initiate K208+orderfl...

---

## Executive Summary

R15-12 (K508 scraper) claimed -60% Y/Y decay in K208 single-factor funding rate edge, sourced
from botter lab's "Funding Rate Edge Degradation Trajectory" (note.com, SECONDARY source).
With K208 weighted 65-75% in K280 sleeve ($10M AUM → ~$1M/yr), this claim required immediate
ground-truth verification.

**Verdict: CONFIRM**

| Metric | Value |
|--------|-------|
| K208 Baseline Sharpe (K438 full period) | 19.12 |
| K208 K492E Sharpe (best variant) | 25.31 |
| Early period (2024H2) Sharpe | 22.61 |
| 2025H1 Sharpe | 19.18 |
| 2025H2 Sharpe | 8.83 |
| Recent period (2026YTD) Sharpe | 7.46 |
| Sharpe Y/Y change | -67.0% |
| R15-12 claimed decay | -60% |
| Spread magnitude decay | -14.5% |

---

## 1. R15-12 Claim Background

**Source:** botter lab note.com article "Funding Rate Edge Degradation Trajectory" (2026-05-27)
**Source quality:** SECONDARY (note.com blog, not primary exchange data)
**Verification label in K508:** STRICT_VERIFIED (but via secondary source — methodology unclear)

**Key claim:** Single-factor funding rate strategies degraded from 5-8 bps/day to 2-3 bps/day
(−60% profitability), with full threshold breach predicted by end-2026.

**Claimed mechanisms:**
1. Large trader copycatting → crowded spread → compressed edge
2. Exchange anti-edge design (dynamic funding curves, HIP-3/HIP-4)
3. Stablecoin supply compression (funding pool exhaustion)

**Critical flag:** R15-12 is a SECONDARY source. The K508 wave labeled it "STRICT_VERIFIED"
but this was based on the article's internal methodology, not independent data verification.
K509 (this wave) provides the actual data-backed ground truth.

---

## 2. Period-Wise Sharpe Analysis

### K208 Panel Sharpe by Period (9 symbols, equal-weight)

| Period | Panel Sharpe | Min Sh | Max Sh | Mean Spread (bps) | Win Rate |
|--------|-------------|--------|--------|-------------------|----------|
| 2024H1 | 24.03 | 20.01 | 26.87 | 0.835 | 90.1% |
| 2024H2 | 22.61 | 19.53 | 25.06 | 0.835 | 89.4% |
| 2025H1 | 19.18 | 2.03 | 33.33 | 0.266 | 83.4% |
| 2025H2 | 8.83 | 0.10 | 28.18 | 0.071 | 83.6% |
| 2026YTD | 7.46 | -3.21 | 20.32 | -0.137 | 68.4% |

**Note:** Sharpe values are computed using simplified DAR baseline (persistence signal) on
historical HL+Bybit data. K438 full-period OOS Sharpe of 19.12 is the reference benchmark.
Period Sharpe values represent the strategy's performance in each specific window, not
cumulative backtests. Differences from K438 aggregate Sharpe are expected (different
period weighting, simplified signal without DAR(2,1) walk-forward).

---

## 3. Funding Rate Spread Magnitude (Crowding Proxy)

### Absolute Spread by Period (panel average, 9 K208 symbols)

| Period | Mean Spread (bps) | Abs Spread (bps) | % Positive Spread |
|--------|------------------|------------------|-------------------|
| 2024H1 | 0.835 | 1.040 | 85.3% |
| 2024H2 | 0.835 | 1.062 | 84.0% |
| 2025H1 | 0.266 | 0.721 | 74.0% |
| 2025H2 | 0.071 | 0.889 | 74.5% |
| 2026YTD | -0.137 | 0.908 | 59.0% |

**Interpretation:**
- Declining absolute spread = less carry harvest opportunity → crowding signal
- Declining % positive spread = more frequent adverse carry → strategy degrades
- Flat/rising absolute spread = crowding NOT occurring at data level

---

## 4. Rolling 6-Month Sharpe Trend

| Window | Period | Panel Sharpe | Mean Spread (bps) |
|--------|--------|-------------|-------------------|
| W1_May24-Oct24 | 2024-05-23 → 2024-10-31 | 29.75 | 0.487 |
| W2_Jul24-Dec24 | 2024-07-01 → 2024-12-31 | 22.61 | 0.835 |
| W3_Sep24-Feb25 | 2024-09-01 → 2025-02-28 | 21.95 | 0.766 |
| W4_Nov24-Apr25 | 2024-11-01 → 2025-04-30 | 19.23 | 0.632 |
| W5_Jan25-Jun25 | 2025-01-01 → 2025-06-30 | 19.18 | 0.266 |
| W6_Mar25-Aug25 | 2025-03-01 → 2025-08-31 | 23.29 | 0.304 |
| W7_May25-Oct25 | 2025-05-01 → 2025-10-31 | 9.68 | 0.201 |
| W8_Jul25-Dec25 | 2025-07-01 → 2025-12-31 | 8.83 | 0.071 |
| W9_Sep25-Feb26 | 2025-09-01 → 2026-02-28 | 4.67 | -0.129 |
| W10_Nov25-Apr26 | 2025-11-01 → 2026-04-30 | 7.80 | -0.136 |
| W11_Jan26-May26 | 2026-01-01 → 2026-05-23 | 7.46 | -0.137 |

**Rolling trend analysis:** The 6-month rolling windows reveal whether decay is progressive
or episodic. Progressive decay supports the R15-12 crowding hypothesis; episodic decay
suggests regime/market-structure effects rather than structural degradation.

---

## 5. Decay Mechanism Analysis

### 5.1 Crowding (Copycatting)
- **Evidence needed:** Decreasing spread over time = more participants harvesting same edge
- **Data signal:** Absolute spread decay % above
- **Assessment:** See spread decay table — if abs_spread declining >20%, crowding confirmed

### 5.2 Exchange Anti-Edge Design (HIP-3/HIP-4)
- HL HIP-3: Variable funding rate formula (introduced late 2024)
- HIP-4: Vault-based liquidity expansion (Q1 2025)
- **Effect:** More efficient price discovery → FR closer to fair value → less HL-Bybit divergence
- **HL data:** 2024H2 vs 2025H2 spread changes directly capture this

### 5.3 Stablecoin Supply Compression
- USDC supply compression reduces available collateral for long/short carry
- Effect on FR: less leveraged long demand → lower positive funding on HL
- **Evidence:** Declining mean positive spread in 2025H2 vs 2024H2

### 5.4 ETF Flow Impact (Positive for BTC/ETH, mixed for alts)
- Spot ETF flows push BTC/ETH prices → cascading alt funding rate compression
- K208 symbols are ALT-heavy (SOL, XRP, SUI, OP, APT, etc.)
- Alt funding may have compressed less than BTC/ETH → K208 may be more resilient

---

## 6. Multi-Factor Pivot Recommendations

Regardless of verdict, these augmentations improve K208's robustness:

### K492_Variant_E
- **Status:** AVAILABLE
- **Priority:** HIGH — activate immediately regardless of verdict
- **Sharpe lift:** +6.19
- **USD lift @ $10M:** +$222,919/yr

### K208_plus_orderflow_K495
- **Status:** AVAILABLE (K495 daemon live)
- **Description:** DEX-CEX flow imbalance as regime filter
- **Priority:** HIGH if CONFIRM/PARTIAL

### K208_plus_MVRV_K504
- **Status:** RESEARCH
- **Description:** On-chain MVRV as macro regime gate (K504 related)
- **Priority:** MEDIUM

### K208_plus_crossvenue_K498
- **Status:** PARTIALLY_AVAILABLE (K498 smart router)
- **Description:** Multi-venue spread harvest: HL+Bybit+OKX+Vertex
- **Priority:** HIGH if CONFIRM

---

## 7. Updated 5-Year Projections

| Scenario | K280 Ann. Return | K280 Ann. USD ($10M) | K280 5y Terminal ($10M) |
|----------|-----------------|---------------------|------------------------|
| Current (no decay) | 10.0% | $1,000,900 | $31,400,000 |
| CONFIRM (-60% decay) | 4.0% | $400,360 | $12,168,634 |
| PARTIAL (-30% decay) | 7.0% | $700,630 | $14,029,646 |
| **Actual (CONFIRM)** | **4.0%** | **$400,360** | **$12,168,635** |

---

## 8. Verdict & Action

### VERDICT: CONFIRM

Sharpe degraded -67.0% from 2024H2 to 2026YTD. R15-12 claim of -60% Y/Y is substantiated. Urgent K280 rebalance recommended.

### Recommended Action

URGENT: Reduce K280 K208 sleeve weight from 65-75% to 35-45%. Activate K492 Variant E immediately. Initiate K208+orderflow (K495) and K208+MVRV (K504) multi-factor combination. Recompute v6.26 projections with adjusted Sharpe 7-10.

### R15-12 Reliability Assessment

R15-12 VINDICATED. Secondary source (botter lab) correctly identified real decay trend. R15 findings reliability MAINTAINED.

---

## 9. §6 Gate Assessment (Verification Quality)

| Gate | Criterion | Result |
|------|-----------|--------|
| G1: Data coverage | ≥18 months HL+Bybit data | PASS (24 months) |
| G2: Symbol coverage | ≥7 of 9 K208 symbols | PASS (9/9) |
| G3: Period granularity | ≥4 distinct periods | PASS (5 periods) |
| G4: Rolling windows | ≥8 6-month windows | PASS (11 windows) |
| G5: Source independence | Data from HL/Bybit API cache | PASS (independent of R15-12) |
| G6: Decay metric | Explicit Sharpe + spread decay % | PASS |

**Verification quality: 6/6 PASS**

---

## 10. Memory Snapshot (K509)

**K208 Health Snapshot 2026-05-30:**
- OOS Sharpe (K438 baseline): 19.12
- OOS Sharpe (K492E variant): 25.31
- Observed decay 2024H2→2026YTD: -67.0%
- Verdict: CONFIRM

**R15-12 Reliability:**
- Finding: -60% Y/Y decay claim (botter lab, SECONDARY)
- Ground truth result: CONFIRM
- Reliability update: R15-12 VINDICATED. Secondary source (botter lab) correctly identified real decay...

---

*Generated by wave_k509_k208_decay_verify.py | K339 REPO_ROOT pattern | Runtime: 3.0s*

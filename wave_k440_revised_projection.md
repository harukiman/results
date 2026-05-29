# K440 Updated Profit Projection
**Wave:** K440 | **Generated:** 2026-05-29 23:19 JST | **Status:** AUTHORITATIVE

> Consolidates K437 HYPE price correction + K438 K208 alpha lift into the new canonical 5-year forecast.
> Supersedes K433 base projections.

---

## Executive Summary

```
K440 CONFIRMED BASE CASE
  $10M → $28,556,300 over 5 years
  CAGR:   23.35%
  Source: K433 base ($25.47M) + K438 lift (+$3.08M)
  K438 included:  YES (limit ladder + predictedFR)
  Uncaptured upside: +$338K/yr → true base may be $30–32M

CONSERVATIVE:  $10M → $15,116,464  (CAGR 8.62%)
AGGRESSIVE:    $10M → $33,140,631  (CAGR 27.08%)
```

---

## Table of Contents

1. [K437 HYPE Price Correction](#1-k437-hype-price-correction)
2. [Execution Edge Stack Reconciliation](#2-execution-edge-stack-reconciliation)
3. [K438 K208 Alpha Lift Summary](#3-k438-k208-alpha-lift-summary)
4. [K440 Revised Three-Case Table](#4-k440-revised-three-case-table)
5. [Uncaptured Upside (Not in $28.56M)](#5-uncaptured-upside-not-in-2856m)
6. [Profit-Driving Stack: All Components](#6-profit-driving-stack-all-components)
7. [Yearly AUM Trajectories](#7-yearly-aum-trajectories)
8. [Risk Analysis](#8-risk-analysis)
9. [Decision](#9-decision)
10. [Next Actions (Priority Order)](#10-next-actions-priority-order)
11. [K436 Master Playbook Update Notes](#11-k436-master-playbook-update-notes)

---

## 1. K437 HYPE Price Correction

### The Error

K432 (execution edge wave) estimated HYPE Gold tier at ~$13,000 cost based on the Nov-2024 airdrop price of **$1.30/HYPE**. By 2026-05-29, HYPE is trading at **$59.00/HYPE** — a **45x increase**.

| Metric | K432 Assumed | K437 Corrected |
|--------|-------------|----------------|
| HYPE price | $1.30 | $59.00 |
| Gold tier cost (10,000 HYPE) | $13,000 | $590,000 |
| Gold tier annual benefit | $30,314 | $30,314 |
| Gold tier ROI at $10M | 19.5% | **2.9%** |

A 2.9% ROI is worse than parking funds in sUSDe (5%+ APY). Gold is therefore **NOT recommended** at $10M AUM.

### Corrected Recommendation: Bronze Tier

| Tier | HYPE Req | Cost @ $59 | Annual Benefit | ROI | Payback |
|------|----------|-----------|----------------|-----|---------|
| Bronze | 100 | $5,900 | $8,623 | **143.9%** | 8.2 mo |
| Silver | 1,000 | $59,000 | $14,068 | 21.6% | 50 mo |
| Gold | 10,000 | $590,000 | $30,314 | 2.9% | 233 mo |

**Bronze ($5,900) is optimal at $10M AUM.** Upgrade to Silver when AUM reaches $50M (ROI 87%).

### K432 Corrected Total (Bronze, not Gold)

| Component | K432 Original | K440 Corrected |
|-----------|--------------|----------------|
| Bybit VIP5 + POST_ONLY | $154,264 | $154,264 |
| HL HYPE stake | $2,534 (Gold assumed) | $8,623 (Bronze) |
| Slippage limit ladder (K297p) | $9,600 | $9,600 |
| Smart routing mid-est | $175,500 | $175,500 |
| **Total** | **$341,898/yr** | **$347,987/yr** |

The Bronze correction adds +$6,089/yr vs K432 Gold-assumed estimate.

---

## 2. Execution Edge Stack Reconciliation

### Problem

K438 found POST_ONLY limit ladder = **$228,735/yr** at $10M (vs K432 estimate of $23,166). A 10x underestimate.

### Critical: No Double-Counting

K438's 5-year terminal projection **already includes** the limit ladder $228K benefit (via Sharpe lift). Adding it again would double-count.

### Correct Stack Attribution

| Component | Annual Lift @ $10M | Wave | In K440 $28.56M? |
|-----------|-------------------|------|-----------------|
| Smart router | $175,500 | K434 | **NO — additive** |
| Bybit VIP5 fee tier | $154,264 | K432 | NO — additive |
| HYPE Bronze stake | $8,623 | K437 | NO — additive |
| Limit ladder + predictedFR | $228,735 | K438 | **YES — included** |
| Builder rebate (low) | $94,000 | K370 | NO — additive |
| Builder rebate (high) | $472,000 | K370 | NO — additive |

**Incremental above K440 $28.56M:**

| Scenario | Annual Lift | Source |
|----------|-------------|--------|
| Minimum (router + HYPE) | +$184K/yr | K434 + K437 |
| Base (+ Bybit VIP5) | +$338K/yr | + K432 |
| Optimistic (+ builder low) | +$432K/yr | + K370 |
| Maximum (+ builder high) | +$810K/yr | + K370 |

---

## 3. K438 K208 Alpha Lift Summary

K438 analyzed two enhancements to K208 (the core funding-rate carry strategy):

### 3a. PredictedFR Signal

| Metric | K208 Baseline | K299 Proxy | Estimated (predictedFR) |
|--------|--------------|------------|------------------------|
| OOS Sharpe | 17.53 | 16.52 | 16.55 |
| WF Mean | 13.94 | 17.10 | 17.01 |
| WF Min | 7.39 | 14.28 | 14.07 |

Key insight: predictedFR does not improve raw OOS Sharpe but **dramatically improves walk-forward stability** (WF min +6.68). This is regime-robustness, not overfitting.

### 3b. Limit Ladder (POST_ONLY)

| Metric | Value |
|--------|-------|
| HL venue fraction | 65% |
| Bybit venue fraction | 35% |
| Blended fee delta | 4.59 bps |
| Annual fee savings | $228,735 at $10M |
| Annual slippage savings | $49,725 at $10M |
| Sharpe lift (fee-est) | +2.44 |

### 3c. Combined K280 Impact

| Metric | Baseline | K438 Refined | Delta |
|--------|----------|-------------|-------|
| K208 OOS Sharpe | 17.53 | 19.12 | +1.59 |
| K280 OOS Sharpe | 20.25 | **22.12** | **+1.87** |

### 3d. 5-Year Profit Lift (K438)

| Item | Value |
|------|-------|
| K433 Base terminal | $25,472,463 |
| K438 terminal | **$28,556,300** |
| Delta | **+$3,083,837 (+$3.08M)** |
| Fee CAGR lift | +2.29pp |
| Signal CAGR lift (conservative) | +0.50pp |
| K438 total CAGR lift | **+2.79pp** |

§6 gates: **PASS 7/7.** Decision: **ACCEPT.**

---

## 4. K440 Revised Three-Case Table

| Case | K433 Baseline | K438 Lift | **K440 Revised** | CAGR |
|------|--------------|-----------|-----------------|------|
| Conservative | $13,484,015 | +$1,632,449 | **$15,116,464** | 8.62% |
| **Base** | $25,472,463 | **+$3,083,837** | **$28,556,300** | **23.35%** |
| Aggressive | $29,561,725 | +$3,578,906 | **$33,140,631** | 27.08% |

### CAGR Comparison

| Case | K433 CAGR | K440 CAGR | Lift |
|------|----------|----------|------|
| Conservative | 6.16% | 8.62% | +2.46pp |
| **Base** | 20.56% | **23.35%** | **+2.79pp** |
| Aggressive | 24.21% | 27.08% | +2.87pp |

### Methodology

K438 delta $3.08M applied as proportional ratio (12.1%) to K433 conservative and aggressive terminals. Base case uses K438 JSON directly ($28,556,299.66).

---

## 5. Uncaptured Upside (Not in $28.56M)

The $28.56M **does not include**:

| Item | Annual Lift @ $10M | Why Not Included |
|------|-------------------|-----------------|
| K434 Smart router | +$175,500 | Not in K438 Sharpe baseline |
| K432 Bybit VIP5 | +$154,264 | Not explicitly in K438 |
| K437 HYPE Bronze | +$8,623 | Small; separate action |
| K370 Builder rebate (low) | +$94,000 | User action required |
| K370 Builder rebate (high) | +$472,000 | User action required |

### True Base Case Range

| Scenario | 5y Terminal | CAGR | What's Added |
|----------|------------|------|-------------|
| K440 Confirmed Base | $28,556,300 | 23.35% | K438 only |
| + Router + HYPE + Bybit | ~$30.3M | ~24.5% | +$338K/yr |
| + Builder rebate (low) | ~$31.0M | ~25.0% | +$432K/yr |
| + Builder rebate (high) | ~$33.7M+ | ~27.5% | +$810K/yr |

**True Base: $30–32M at $10M start when router and builder rebate activated.**

---

## 6. Profit-Driving Stack: All Components

Complete view of all value drivers at $10M AUM:

| Wave | Action | $10M Annual Lift | Status |
|------|--------|-----------------|--------|
| K426 | 3x leverage | +$2,200,000 (baseline) | Deploy via leverage_manager.py |
| K428 | Daily reinvest | Compound multiplier | Enable AUM_TRACKING_ENABLED=true |
| K431 | Multi-venue m6 | Activates at $15M+ | Month 6 trigger |
| K432 | Bybit VIP5 | +$154,264 | Fund $2M+ to Bybit |
| K434 | Smart router | +$175,500 | Load daemon (5 min) |
| K437 | HYPE Bronze stake | +$8,623 | Buy 100 HYPE ≈ $5,900 |
| K438 | Limit ladder + predictedFR | +$228,735 | Load predicted monitor daemon |
| K370 | Builder rebate | +$94K–$472K | approveBuilderFee on HL (30 min) |
| K429 | AUM compounding | Implicit | Unlocked by K428 |

**Combined quantified (excl K426):** $567K–$1,039K/yr at $10M

**Total combined incl K426 low:** ~$2.77M/yr at $10M
**Total combined incl K426 high:** ~$3.24M/yr at $10M

---

## 7. Yearly AUM Trajectories

### Base Case ($28.56M, 23.35% CAGR)

| Year | AUM | Annual Profit |
|------|-----|--------------|
| Start | $10,000,000 | — |
| Y1 | $12,335,035 | +$2,335,035 |
| Y2 | $15,215,309 | +$2,880,274 |
| Y3 | $18,768,137 | +$3,552,828 |
| Y4 | $23,150,562 | +$4,382,425 |
| Y5 | $28,556,300 | +$5,405,738 |

### Conservative ($15.12M, 8.62% CAGR)

| Year | AUM |
|------|-----|
| Y1 | ~$10,862,000 |
| Y2 | ~$11,789,000 |
| Y3 | ~$12,806,000 |
| Y4 | ~$13,909,000 |
| Y5 | ~$15,116,000 |

### Aggressive ($33.14M, 27.08% CAGR)

| Year | AUM |
|------|-----|
| Y1 | ~$12,708,000 |
| Y2 | ~$16,150,000 |
| Y3 | ~$20,522,000 |
| Y4 | ~$26,086,000 |
| Y5 | ~$33,141,000 |

---

## 8. Risk Analysis

### Sharpe Trajectory

| Version | K280 Sharpe | K346 Portfolio Sharpe |
|---------|------------|----------------------|
| K433 Base | 13.43 | 25.47 |
| K438 Refined | **22.12** | ~26.87 |
| Delta | **+1.87** | ~+1.40 |

### Maximum Drawdown

| Case | Max DD % | Source |
|------|----------|--------|
| K433 Base | 0.62% | K433 simulation |
| K438 (K280 refined) | ~0.034% | K438 phase 5 estimate |
| K440 Base | ~0.65% | Conservative estimate |

### Key Risks

| Risk | Severity | Mitigation |
|------|----------|-----------|
| HYPE price drop >22% before payback | Low (Bronze only $5.9K stake) | Optional 1x short hedge |
| Smart router non-fill | Low (graceful degradation) | Market order fallback at T-5min |
| Builder rebate not activating | Medium | 72h wait; contact HL support |
| K297' slippage at $50M+ | High | Real ceiling ~$35–45M effective AUM |
| Leverage margin call | Very Low (CB daemon) | Circuit breaker at 80% margin |

---

## 9. Decision

### K440 Authoritative Projections

```
CONFIRMED BASE (conservative, K438-included):
  $10M → $28,556,300  CAGR 23.35%  [USE THIS FOR PLANNING]

OPTIMISTIC BASE (+ smart router + builder rebate low):
  $10M → ~$31.0M      CAGR ~25.0%  [Achievable with 2 user actions]

AGGRESSIVE (+ K431 multi-venue scaling to $30–50M AUM y3):
  $10M → $33–35M      CAGR 27–29%  [Requires scaling + all uncaptured]
```

### Trajectory to $50M+

$50M in 5 years requires CAGR ~37.8% — **not achievable from $10M base with current stack alone**.

Realistic path to $50M: requires external capital raise OR 7–8 year horizon at aggressive CAGR 27%.

At base CAGR 23.35%, $10M → $50M = **approximately 7.5 years**.

---

## 10. Next Actions (Priority Order)

### Immediate (Zero Cost, <30 Minutes)

1. **K370 Builder rebate** — `approveBuilderFee` on HL wallet
   - Cost: $0, Time: 30 min, Benefit: $94K–$472K/yr
   - **HIGHEST ROI action in entire playbook**

2. **K434 Smart router daemon** — load `com.cryptolab.smart-router.plist`
   - Cost: $0, Time: 5 min, Benefit: +$175K/yr

3. **K438 Predicted FR daemon** — load `com.cryptolab.hl-predicted-monitor.plist`
   - Cost: $0, Time: 5 min, Benefit: enables K208 refinement

### Low Cost, High ROI

4. **HYPE Bronze stake** — buy 100 HYPE ≈ $5,900
   - ROI 143.9%, payback 8.2 months
   - Do NOT buy Gold (2.9% ROI at $10M AUM)

5. **Bybit VIP5** — fund Bybit account $2M+
   - Instant VIP5; +$154K/yr fee reduction

### Medium Term

6. **K438 implementation** — `predicted_fr_signal.py` + `k280_live_fetch.py` patch (~230 LOC)
   - 14-day paper comparison before production switch

---

## 11. K436 Master Playbook Update Notes

Updates required to `docs/k302a_master_deployment.md`:

### Action 8 Correction (HYPE Stake)

Old text: "HL HYPE Gold stake (10K HYPE ≈ $13K) → $2,534/yr"
New text: "HL HYPE Bronze stake (100 HYPE ≈ $5,900) → $8,623/yr (K437 corrected)"

### Expected Outcomes Update (§7)

Old: "Year 5: ~$25.47M | CAGR 20.56%"
New: "Year 5: ~$28.56M | CAGR 23.35% (K438 lift +$3.08M included)"

### New Row in Source Wave Reference (§10)

| Action | Wave | Runbook Section |
|--------|------|-----------------|
| K437 HYPE Bronze correction | K437 | §25 (HYPE stake corrected) |
| K438 K208 limit ladder + predictedFR | K438 | §26 (K208 refinement) |
| K440 Updated 5y projection | K440 | wave_k440_revised_projection.md |

---

## Source References

| Wave | Title | Key Finding |
|------|-------|-------------|
| K433 | Combined 5-Year Simulation | Base: $25.47M, CAGR 20.56% |
| K437 | HYPE Stake Corrected | HYPE $59 (not $1.30); Bronze optimal at $10M |
| K438 | K208 Signal Refinement | K280 Sharpe 20.25→22.12; +$3.08M over 5y |
| K434 | Smart Router | +$175K/yr at $10M; NOT in K438 baseline |
| K432 | Execution Edge | Bybit VIP5 +$154K/yr; limit ladder underestimate corrected |
| K370 | Builder Rebate | +$94K–$472K/yr; ZERO cost; user action pending |

---

*K440 — Generated 2026-05-29 23:19 JST*
*Authoritative revision of K433. Next projection update: K450 (Month 6 Bybit milestone).*

# K375 — Solana Priority Fees + Drift Execution Revival (R12-04)

**Wave:** K375 | **Generated:** 2026-05-27 09:01 JST | **Decision:** **REJECT — K358 LINE CLOSED**

---

## Executive Summary

K375 investigates R12-04: whether Solana priority fees can reduce Drift execution cost
enough to revive K358 (HL-Drift SOL-PERP cross-venue FR arb, REJECTed at 15 bps round-trip).

**Verdict: No. K358 line is closed.**

The fundamental issue is categorical, not marginal:
- Priority fees affect **inclusion order and latency**, not execution fee rates
- Priority fees are **additive cost** to Drift's taker/maker fees
- Even the best-case execution path (DLOB maker + DRIFT staking: 3.3 bps RT) requires a
  **90h breakeven hold** against a mean spread of 0.88 bps/day
- Observed spread persistence is **9.4h** — breakeven is **10x** the persistence window

All 9 cost scenarios fail K266 §6 gates. No scenario achieves positive annualized return.

---

## 1. Solana Priority Fee Mechanics

### 1.1 Fee Structure (from docs.solana.com/core/fees)

| Component | Value |
|-----------|-------|
| Base fee | 5,000 lamports per signature |
| Base fee split | 50% burned / 50% to validator |
| Priority fee formula | `ceil(micro_lamports/CU × compute_units / 1,000,000)` lamports |
| Priority fee recipient | 100% to validators |
| Drift order CU estimate | ~300,000 compute units |
| Max CU per transaction | 1,400,000 |

### 1.2 Priority Fee Cost at Different Levels

| Scenario | Micro-lamports/CU | Total lamports | Cost (USD) | Cost (bps @ $50k) |
|----------|-------------------|----------------|------------|-------------------|
| none | 0 | 5,000 | $0.0007 | 0.0001 bps |
| low | 1,000 | 5,300 | $0.0007 | 0.0001 bps |
| medium | 10,000 | 8,000 | $0.0011 | 0.0002 bps |
| high | 100,000 | 35,000 | $0.0049 | 0.0010 bps |
| ultra | 1,000,000 | 305,000 | $0.0427 | 0.0085 bps |

*Assumes SOL price = $140 USD (May 2026)*

**Critical insight:** Even "ultra" priority ($0.04/tx, 1M micro-lamports/CU) costs only
**0.0085 bps** at $50k notional. Priority fees are essentially negligible relative to
execution fees — they are **not a meaningful cost reduction lever**.

### 1.3 arXiv 2602.10798 — Relevance to K358

The paper "Trading in CEXs and DEXs with Priority Fees and Stochastic Delays" develops
a mathematical framework for **optimal latency management** via priority fee selection.

Key findings applicable here:
- Priority fees allow traders to choose mean delay distribution for their transactions
- The optimal strategy involves dynamic fee selection based on execution urgency
- The paper demonstrates "significant outperformance over non-strategic fee selection"

**What the paper does NOT do:** Reduce taker/maker fee rates. The paper's contribution is
about **timing execution** under stochastic inclusion delays — managing the risk that a
trade executes at an unfavorable price due to latency. It does not alter the underlying
fee schedule at the exchange level.

For K358, the relevant risk is not latency (which priority fees address) but **cost per
round-trip** relative to spread magnitude — a fundamentally different problem.

---

## 2. Drift Fee Structure Update (Post-Aug 5, 2025)

### 2.1 Taker Fee Tiers (New Structure)

Drift overhauled its fee model on August 5, 2025 with volume-based tiers and DRIFT
staking discounts. K358 used an estimated 5 bps taker fee (old structure).

| 30d Volume | Taker Fee | Maker Rebate |
|------------|-----------|--------------|
| ≤ $2M (Tier 1) | 3.50 bps | -0.25 bps |
| > $2M (Tier 2) | 3.00 bps | -0.25 bps |
| > $10M (Tier 3) | 2.75 bps | -0.25 bps |
| > $20M (Tier 4) | 2.50 bps | -0.25 bps |
| > $80M (Tier 5) | 2.25 bps | -0.25 bps |
| > $200M (VIP) | 2.00 bps | -0.25 bps |

**K358 error:** Used 5 bps taker (old pre-Aug-2025 structure). Actual Tier1 = **3.5 bps**.

### 2.2 DRIFT Staking Discounts

| Staking Tier | DRIFT Required | Taker Discount | Maker Rebate Boost |
|-------------|----------------|----------------|---------------------|
| Rookie | 0 | 0% | 0% |
| Kickstarter | 1,000 | -5% | +5% |
| Racer | 10,000 | -10% | +10% |
| Elite | 50,000 | -20% | +20% |
| Master | 100,000 | -30% | +30% |
| Champion | 250,000 | -40% | +40% |

### 2.3 Drift Order Execution Flow

1. **JIT Auction**: Market orders first hit a Just-In-Time auction where market makers
   can fill at the oracle price
2. **DLOB**: Remaining volume routes to the Decentralized Limit Order Book
3. **AMM**: Unfilled remainder hits the protocol vAMM as last resort

**Maker rebate requirement:** Must use `post-only` flag to ensure DLOB maker treatment.
Market orders always pay taker fee. Only resting limit orders with post-only flag earn
the -0.25 bps rebate.

**Priority fee role for maker orders:** Priority fees improve the probability that a
post-only limit order is included in a block before being crossed. This reduces the risk
of the order remaining unfilled during fast price movement — an operational benefit, but
not a fee reduction.

---

## 3. Cost Scenario Matrix

### 3.1 Round-Trip Cost Scenarios

| Scenario | HL leg | Drift leg | Priority fee | Slippage | Total RT | BEH* | Viable? |
|----------|--------|-----------|--------------|----------|----------|------|---------|
| K358 baseline (REJECT) | 1.5 bps | 5.00 bps | 0 | 1.0 bps | 14.0 bps | 382h | NO |
| Drift Tier1 taker | 1.5 bps | 3.50 bps | ~0 bps | 1.0 bps | 11.0 bps | 301h | NO |
| Drift Tier1 + priority=low | 1.5 bps | 3.50 bps | 0.0003 bps | 1.0 bps | 11.0 bps | 301h | NO |
| Drift Tier1 + priority=medium | 1.5 bps | 3.50 bps | 0.0004 bps | 1.0 bps | 11.0 bps | 301h | NO |
| DLOB maker (rebate) | 1.5 bps | -0.25 bps | ~0 bps | 1.0 bps | 3.50 bps | 96h | NO |
| DLOB maker + priority=low | 1.5 bps | -0.25 bps | 0.0003 bps | 1.0 bps | 3.50 bps | 96h | NO |
| DLOB maker + priority=medium | 1.5 bps | -0.25 bps | 0.0004 bps | 1.0 bps | 3.50 bps | 96h | NO |
| DLOB maker + staked | 1.5 bps | -0.35 bps | ~0 bps | 1.0 bps | 3.30 bps | 90h | NO |
| DLOB maker + staked + priority=low | 1.5 bps | -0.35 bps | 0.0003 bps | 1.0 bps | 3.30 bps | 90h | NO |

*BEH = Breakeven Hold Hours at mean spread of 0.88 bps/day. Observed persistence = 9.4h.

### 3.2 Breakeven Analysis

```
Mean spread:               0.88 bps/day  (K358, 5915 hours)
Observed avg hold:         9.4h
Required hold to BEV:      RT_bps / 0.88 * 24 hours

K358 baseline (14 bps):    14.0 / 0.88 * 24 = 382h  [persistence ratio: 40.6x]
New Tier1 taker (11 bps):  11.0 / 0.88 * 24 = 300h  [persistence ratio: 31.9x]
DLOB maker best (3.3 bps):  3.3 / 0.88 * 24 =  90h  [persistence ratio:  9.6x]
```

Even the absolute best-case execution (DLOB maker + staked DRIFT, 3.3 bps RT):
**90h breakeven vs 9.4h persistence = 9.6x gap. Still deeply unviable.**

---

## 4. Backtest Re-Run (K358 Data, New Cost Assumptions)

**Data:** K358 cache `drift_sol_fr.parquet` + `hl_fr_SOL.parquet`
**Period:** 2024-05-23 to 2026-04-01 (246 days, 5,915 hourly rows)
**Method:** K208-style bilateral carry backtest (replicates K358 logic exactly)

### 4.1 Full-Sample Backtest Results

| Scenario | RT Cost | Final Equity | Ann Return | Sharpe | Win Rate |
|----------|---------|--------------|------------|--------|----------|
| K358 baseline | 15.0 bps | 0.657 | **-46.4%** | -27.26 | 36.3% |
| New Tier1 taker | 11.0 bps | 0.750 | **-34.7%** | -25.09 | 36.3% |
| DLOB maker | 3.5 bps | 0.963 | **-5.4%** | -9.09 | 36.3% |
| DLOB maker + staked | 3.3 bps | 0.970 | **-4.5%** | -7.82 | 36.3% |

*Note: K358 reported -60.6% (different metric convention). This backtest uses a corrected
version that more precisely replicates the K208 bilateral spread P&L model.*

### 4.2 Walk-Forward Results (3 Folds)

**K358 baseline (15 bps):**

| Fold | Days | Ann Return | Sharpe | Trades | Positive |
|------|------|------------|--------|--------|----------|
| 1 | 82.1 | -52.6% | -31.14 | 125 | NO |
| 2 | 82.1 | -34.8% | -22.65 | 75 | NO |
| 3 | 82.2 | -50.1% | -27.72 | 133 | NO |

**DLOB maker + staked (3.3 bps) — best case:**

| Fold | Days | Ann Return | Sharpe | Trades | Positive |
|------|------|------------|--------|--------|----------|
| 1 | 82.1 | -9.1% | -16.08 | 125 | NO |
| 2 | 82.1 | -3.7% | -8.37 | 75 | NO |
| 3 | 82.2 | -0.3% | -0.48 | 133 | NO |

The best-case DLOB maker scenario shows Fold 3 approaching zero (-0.3% ann return,
Sharpe -0.48). This is the closest any scenario gets to viability — but still negative
across all folds.

### 4.3 K266 §6 Gate Results

All scenarios fail all gates:

| Gate | K358 baseline | DLOB maker+staked | Threshold | Status |
|------|---------------|-------------------|-----------|--------|
| G1 OOS Sharpe | -27.26 | -7.82 | ≥ 1.0 | ALL FAIL |
| G2 Perm p-val | n/a | n/a | ≤ 0.05 | ALL FAIL |
| G3 DSR proxy | 0.0 | 0.0 | ≥ 1.0 | ALL FAIL |
| G4 WF pos/folds | 0/3 | 0/3 | all positive | ALL FAIL |
| G7 Ann return | -46.4% | -4.5% | ≥ 5% | ALL FAIL |

---

## 5. Priority Fee Role in Execution — Clarified

### 5.1 What Priority Fees DO

1. **Increase inclusion probability** in the next block during congestion
2. **Reduce latency** from submission to execution (~400ms baseline Solana slot time)
3. **Improve maker fill rate** for DLOB post-only orders by getting the order into the
   queue before a competing taker order crosses it
4. **Optimize stochastic delay** as modeled in arXiv 2602.10798 — reduce variance of
   execution time for time-sensitive positions

### 5.2 What Priority Fees Do NOT Do

1. **Reduce Drift taker or maker fee rates** — fees are protocol-level, not tx-level
2. **Alter the spread economics** — priority fees are additive cost
3. **Compensate for insufficient spread** — no amount of priority fee optimization
   changes the fact that mean spread (0.88 bps/day) < cost hurdle
4. **Speed up spread convergence** — spread persistence is market-driven, not execution-speed-driven

### 5.3 Why Priority Fees Are Essentially Zero-Cost Here

At $50,000 notional, even "ultra" priority (1M micro-lamports/CU = ~$0.04/tx) is
only 0.0085 bps — essentially noise relative to 3-15 bps execution fees. The "priority
fee problem" for K358 doesn't exist because Solana fees are extremely cheap at this
scale. The real problem is the Drift protocol-level fee vs. spread ratio.

---

## 6. K266 §6 Decision

**Decision: REJECT — K358 LINE CLOSED**

### Primary Rejection Reasons

1. **Structural cost-spread mismatch**: Even best-case execution (3.3 bps RT) requires
   90h to break even at mean spread. Observed persistence is 9.4h (10x gap).

2. **Priority fees are irrelevant**: At typical notional sizes, priority fee cost is
   < 0.01 bps — negligible. They improve execution quality (latency/fill rate) but
   cannot address the fundamental economics.

3. **DLOB maker path is theoretical**: Requires post-only limit orders to fill against
   taker flow. Fill rate is not 100% — in fast markets (when arb opportunities are
   largest), maker orders are more likely to be crossed or cancelled. The backtest
   treats all trades as maker-filled, which overstates real-world performance.

4. **Drift fee update helps, but not enough**: New Tier1 (3.5 bps vs 5 bps) reduces
   round-trip from 14 to 11 bps for taker path. Still 30x the breakeven gap.

5. **All walk-forward folds negative**: No time period shows positive return, indicating
   this is not regime-dependent — it is a structural fee problem throughout.

---

## 7. Generalization: Solana Priority Fees for Other DEX Arbs

### 7.1 Applicability

Priority fees apply to all Solana DEXs:
- **Drift** (perp): analyzed above
- **Jupiter** (spot aggregator): aggregates Raydium/Orca/etc.
- **Raydium** (spot AMM): CLMM with fixed-spread LP
- **Orca** (spot AMM): Whirlpools, concentrated liquidity

### 7.2 Key Difference from K358

For **spot DEX arb** (e.g., Jupiter vs CEX), latency matters more because:
- Price moves faster on spot than FR accumulates on perp
- Priority fee timing directly affects arb capture window
- The relevant metric is "can I execute before price moves?" not "can I accumulate FR?"

For spot arb, arXiv 2602.10798's framework is directly applicable — optimal priority
fee selection minimizes the probability of executing at a stale price. However, this
also requires co-location / low-latency infrastructure, not available in the CT Lab
current stack.

### 7.3 Infrastructure Note (Not a Trade Signal)

Priority fees + Jito bundles (MEV-aware execution) could be valuable for:
- Cross-venue spot arb (Jupiter vs Binance)
- JIT auction participation on Drift
- Liquidation sniper bots

These require dedicated infrastructure investment and are outside K375 scope.

---

## 8. Conditions for K358 Reopening

K358 is closed, but can be reopened if market structure changes:

| Condition | Current | Required | Likelihood |
|-----------|---------|----------|------------|
| Mean spread | 0.88 bps/day | >5 bps/day | Low (structural) |
| Spread persistence | 9.4h avg hold | >90h for DLOB maker path | Very low |
| Drift institutional fee | 2.0 bps (VIP) | <0.5 bps total | Unlikely |
| HL-Drift FR divergence regime | Normal | Bull cycle peak with >10 bps divergence | Possible in cycle |

**Bull cycle scenario**: During peak 2025 bull run (Jan 2025 - Mar 2025, inaccessible in
K358 data), HL-Drift FR spreads may have exceeded 10-20 bps/day for extended periods.
The 13-month data gap (Jan 2025 - Feb 2026) limits K358's statistical power. This is
worth monitoring at next regime inflection.

---

## 9. Summary

| Item | Result |
|------|--------|
| Priority fees reduce Drift fees? | **No** — additive Solana tx cost only |
| Priority fees at $50k notional | **< 0.01 bps** — negligible |
| Drift fee update (Aug 2025) | Tier1 now 3.5 bps (was 5 bps in K358 estimate) |
| DLOB maker path | -0.25 bps rebate available, but fill not guaranteed |
| Best-case RT cost | 3.3 bps (DLOB maker + staked DRIFT) |
| Best-case breakeven hold | 90h vs 9.4h observed persistence (10x gap) |
| Best-case backtest result | -4.5% ann, Sharpe -7.82, 0/3 WF folds positive |
| K266 gates passed | 0/5 for all scenarios |
| K358 revival via priority fees | **No** |
| K358 line status | **CLOSED** |
| Reopen condition | Mean spread >5 bps/day (10x current) or major regime change |

---

## 10. arXiv 2602.10798 — Extraction for CT Lab Research Archive

**Title:** "Trading in CEXs and DEXs with Priority Fees and Stochastic Delays"

**Core contribution:** Dynamic programming framework for optimal priority fee selection
under stochastic execution delays on DEXs. Traders can choose delay distribution by
adjusting priority fee. Models joint optimization of CEX+DEX positions under asynchronous
execution timing.

**Applicable to CT Lab when:**
- Executing latency-sensitive strategies on Solana (spot arb, liquidations)
- Managing execution risk on DLOB maker orders (JIT auction participation)
- Designing strategies where execution lag creates adverse selection cost

**Not applicable to K358 because:** K358's problem is cost vs. spread magnitude, not
execution timing. Priority fee optimization (the paper's solution) doesn't address fee rates.

**Archive status:** Stored in R12 external findings (round12). K375 = full evaluation complete.

---

*K375 | Wave runtime: 0.2s | Cache: cache/drift_sol_fr.parquet | K358 line: CLOSED*

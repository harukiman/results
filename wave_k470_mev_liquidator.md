# K470 — MEV / Liquidator Strategy Exploration

**Wave:** K470 | **Date:** 2026-05-25 | **Status:** ANALYSIS COMPLETE  
**Decision:** DEFER — pursue v6.20 scaling first; MEV liquidator is 5-10x effort for 1-50% revenue lift  
**Immediate Action:** HL cascade signal enhancement (K372 reactivation, 5-day implementation)

---

## Executive Summary

K470 explores MEV liquidator strategies as a novel alpha class orthogonal to the existing v6.20
carry/momentum portfolio. Liquidation MEV is event-driven, episodic, and structurally uncorrelated
(expected correlation 0.05-0.10 vs K208/K376/K449/K457). However, competitive dynamics on Ethereum
mainnet are extreme (30+ sophisticated bots), implementation requires 4-6 months and $60-80K capex
including mandatory smart contract audits, and revenue is capacity-limited by event count rather than
scalable with AUM.

**Key finding:** At the boutique level (1-5% market share), net annual revenue is $214K-$1.3M —
comparable to v6.20 baseline but requiring 10-50x more engineering complexity and ongoing operational
overhead. The recommended path is to DEFER full MEV bot implementation and IMMEDIATELY pursue the
lighter alternative: HL liquidation cascade as a signal enhancer for K376 momentum (5-day effort,
no smart contracts, uses existing infrastructure).

---

## 1. Strategy Class Overview

MEV (Maximal Extractable Value) liquidations represent a fundamentally different alpha class than
carry or momentum strategies:

| Dimension        | Carry (K208/K449)     | Momentum (K376)       | MEV Liquidator            |
|-----------------|----------------------|----------------------|---------------------------|
| Alpha source     | Funding rate premium  | Price trend          | Collateral shortfall bonus|
| Frequency        | Continuous (hourly)   | Daily signals        | Event-driven (rare)       |
| Mechanism        | Passive FR collection | Directional exposure | Forced on-chain execution |
| Infrastructure   | REST API / exchange   | REST API / exchange  | RPC node + smart contract |
| Capital lockup   | 1x (hedged)           | 1x directional       | 0x (flash loans)          |
| Smart contract   | None                  | None                 | Required + audit          |
| Latency req.     | Seconds               | Minutes              | Milliseconds              |

### 1.1 Venue Landscape

Five venues were analyzed for liquidation MEV opportunities:

**Aave V3 (Multi-chain)**
The dominant DeFi lending protocol with ~$15B TVL across Ethereum, Polygon, Arbitrum, Optimism,
and Base. Liquidations trigger when Health Factor (HF) < 1.0. At HF < 0.95, 100% of debt can
be repaid (max close factor); above 0.95, only 50% (default close factor).

Core mechanics from LiquidationLogic.sol:
- `DEFAULT_LIQUIDATION_CLOSE_FACTOR = 50%` (applied when HF > 0.95)
- `MAX_LIQUIDATION_CLOSE_FACTOR = 100%` (applied when HF < 0.95)
- `CLOSE_FACTOR_HF_THRESHOLD = 0.95`
- Liquidator receives collateral at a bonus: WBTC/WETH 5%, LINK 7.5%, UNI 8.5%, AAVE 10%
- Protocol takes 10% cut of the bonus (net bonus to liquidator: ~4.5% for WETH)
- eMode (stablecoin-stablecoin): bonus compressed to 1% only
- Flash loan fee on Aave V3: 9bps (can use same protocol's flash loans)

**Compound V3**
Smaller TVL (~$3B), similar bonus structure (~5%), fewer active liquidators (~15 bots).
Gross annual profit pool estimated at $4M; boutique at 3% share = ~$60K net.

**HyperLiquid HLP**
HyperLiquid's backstop liquidation system is democratized through the HLP community vault.
External bots cannot participate directly — liquidations go through HLP's automated system.
Primary liquidation occurs via order book (no fee charged to liquidated user). Backstop via HLP.
**Not accessible to external MEV bots.** Alternative: hold HLP for indirect exposure (~5% APY).

**dYdX v4 (Cosmos chain)**
Cosmos SDK-based perp DEX. Fewer competing searchers due to Cosmos-specific infrastructure
requirements. Estimated gross pool $1.25M; boutique at 15% share = ~$127K net.
Barrier: Cosmos node operation, CosmWasm or Go liquidator implementation.

**Drift Protocol (Solana)**
Post-hack recovery; accessible to external bots. Estimated gross pool $750K; boutique at 8% =
~$0K net after $60K infra cost. Marginal opportunity at current volumes.

---

## 2. Economics Deep-Dive: Aave V3

### 2.1 Market Size

| Metric                          | Bear Market   | Base Case     | Bull Crash    |
|--------------------------------|--------------|--------------|--------------|
| Annual liquidation volume       | $100M        | $500M        | $2,000M      |
| Avg bonus (blended)            | 5.5%         | 5.5%         | 5.5%         |
| Gross profit pool               | $5.5M        | $27.5M       | $110M        |
| Protocol fee (10% of bonus)    | -$0.55M      | -$2.75M      | -$11M        |
| Net pool to all liquidators     | $4.95M       | $24.75M      | $99M         |

### 2.2 Competition Structure

Approximately 30 active sophisticated liquidator bots compete on Aave mainnet:

- Top 3 bots: ~60% of market share (established infrastructure, private relays, optimal gas)
- Top 10 bots: ~85% of market share
- Remaining 20 bots: ~15% of market share (mostly occasional / niche collateral types)
- New entrant realistic share (Year 1): 1-3% of market

Top-tier bots characteristics:
- Sub-100ms block detection (dedicated node + co-located infrastructure)
- Private mempool access via Flashbots MEV-Share (avoid public mempool sandwich attacks)
- Custom smart contracts with gas-optimized liquidation paths
- Dynamic priority fee bidding (EIP-1559 tip optimization)
- Multi-chain monitoring with chain-specific gas strategies

### 2.3 Per-Liquidation Economics

```
Liquidation size:          $100,000 (typical mid-size event)
Gross bonus (5.5%):        $5,500
Protocol fee (10% of bonus): -$550
Flash loan fee (9bps):     -$90
Gas cost (400K gas @ 15 gwei, ETH=$2500): -$15
MEV-Share searcher share (30% of net): varies
---
Net to liquidator (flash loan route): ~$4,845 per event
```

Gas is negligible (~$15/liquidation) because the profit per event is large.
The dominant cost is the protocol fee ($550) and MEV relay sharing.

### 2.4 Boutique Revenue Scenarios

| Scenario         | Market Share | Gross Revenue | Gas Cost | Infra Cost | Net Revenue |
|-----------------|-------------|--------------|---------|-----------|------------|
| Pessimistic     | 1%          | $275,000     | $750    | $60,000   | $214,250   |
| Base            | 2%          | $550,000     | $1,500  | $60,000   | $488,500   |
| Optimistic      | 5%          | $1,375,000   | $3,750  | $60,000   | $1,311,250 |

Note: Infrastructure cost ($5K/month = $60K/year) dominates gas cost. The major drag is
competition-driven: achieving 5% market share against established bots requires significant
initial investment in latency and gas bidding sophistication.

---

## 3. Infrastructure Requirements

Full production liquidator bot requires:

### 3.1 Compute & Networking

| Component                    | Provider                    | Monthly Cost | Notes                          |
|-----------------------------|----------------------------|-------------|-------------------------------|
| Dedicated Ethereum node      | Blastapi/Alchemy dedicated  | $300        | Archive preferred for queries  |
| Private mempool relay        | Flashbots MEV-Share         | $0          | 70% of MEV returned to users  |
| Oracle price feeds           | Chainlink + Pyth            | $50         | <1s price update latency       |
| Health factor monitor        | Custom (block-by-block)     | $200        | Polls all Aave positions       |
| Monitoring & alerting        | Grafana + Prometheus        | $100        | 24/7 uptime required           |
| Multi-chain RPC (L2s)        | Alchemy/Infura              | $200        | Polygon, Arbitrum, Base        |
| **Total monthly infra**      |                             | **$850**    | Plus buffer = ~$5K/month       |

### 3.2 One-Time Development Costs

| Item                              | Cost     | Notes                                      |
|----------------------------------|---------|-------------------------------------------|
| Liquidator smart contract (EVM)   | $20,000  | Flash loan callback + liquidation logic    |
| Smart contract audit              | $30,000  | Mandatory — contract holds protocol flows  |
| Health factor scanner             | $5,000   | Off-chain monitoring service               |
| Gas bidding engine                | $5,000   | EIP-1559 priority fee optimizer            |
| MEV-Share integration             | $5,000   | Bundle submission + inclusion monitoring   |
| Testing + simulation harness      | $10,000  | Mainnet fork testing, scenario simulation  |
| **Total initial capex**           | **$75,000** |                                         |

### 3.3 Operational Requirements

- **24/7 monitoring**: Liquidation opportunities appear at any time (especially during crashes)
- **Incident response**: Smart contract bugs, node failures, gas estimation errors
- **Ongoing tuning**: Gas bidding strategy, new asset types, protocol upgrades
- **Estimated ongoing engineer time**: 20 hours/month minimum

### 3.4 MEV Relay Economics

Running without private mempool access is not viable:

```
Without private relay (public mempool):
  - Sandwich bots detect pending liquidation → front-run or sandwich
  - Expected loss from sandwich attacks: 70-80% of profit
  - Net profit: near zero or negative

With Flashbots MEV-Share:
  - Searcher keeps ~30% of extracted MEV
  - 70% refunded to users/protocol
  - Inclusion rate: ~95% with proper tip
  - Trade-off: share significant profit but avoid being sandwiched
```

---

## 4. K266 Strict Gate Assessment

MEV liquidator strategies do not map cleanly to K266 gates designed for continuous strategies:

### G1 — OOS Sharpe
**NOT APPLICABLE.** No continuous daily PnL stream. Events are episodic; 1-10 liquidations/day
during volatile periods, zero during calm markets. Cannot compute meaningful Sharpe ratio.

Alternative qualifying metric: average profit per event > 3x gas cost (easily satisfied at $5K
profit vs $15 gas). But this does not substitute for Sharpe in portfolio context.

### G3 — DSR (Daily Sortino Ratio)
**PARTIAL.** Event-driven revenue does not produce smooth daily return distribution.
In calm months: 0 liquidations, 0 revenue, negative Sortino (infra costs ongoing).
In crash events: multiple large liquidations in 1-2 days, massive positive spike.
DSR would show high variance and negative Sortino in most months.

### G6 — Trade Count
**PASSES.** Estimated 1-3 liquidations/day at boutique share. Frequency exceeds minimum threshold.
Note: trade count is limited by market events, not by signal generation capacity.

### G7 — Annual Return
**PARTIAL PASS.** Revenue absolute rather than percentage (flash loans = no capital deployed).
Net revenue $214K-$1.3M is meaningful in absolute terms. However:
- Cannot express as % return on deployed capital (capital = 0 via flash loans)
- As a % of AUM if added as sleeve: $214K on $100K allocated = 214% (misleading)
- More accurately: compare absolute revenue to cost (ROI on $75K capex: 186-1648%)

**Overall Gate Status:** INCOMPLETE — event-driven model incompatible with G1/G3 continuous
Sharpe gates. Strategy requires separate evaluation framework for MEV/keeper strategies.

---

## 5. Orthogonality Analysis

MEV liquidator strategies are structurally orthogonal to all existing v6.20 sleeves:

| Sleeve          | Mechanism              | Expected Corr vs MEV | Reason                                    |
|----------------|----------------------|---------------------|------------------------------------------|
| K208 FR carry   | Funding rate premium  | 0.05                | FR levels don't drive liquidation events  |
| K376 momentum   | Price trend following | 0.10                | Cascades cause momentum but profits differ|
| K449 ETH-BTC    | Cross-asset FR diff   | 0.05                | Same FR reasoning                         |
| K457 basket     | Multi-asset carry     | 0.05                | Same carry reasoning                      |

**Key insight:** Liquidation events often *cause* volatility spikes that K376 momentum profits
from. MEV and momentum are complementary — both profit during crash events but via different
mechanisms. This suggests positive scenario dependence (both do well in crashes) rather than
true independence, but PnL streams are uncorrelated because timing differs (MEV: instant at
liquidation trigger; momentum: over hours/days post-event).

**Verdict: True alpha class addition with genuine portfolio diversification value.**

---

## 6. Capital Structure

### Flash Loan Route (Recommended)
```
Capital required:          $0
Max liquidation size:      Unlimited (bounded by Aave flash loan pool)
Process:
  1. Detect undercollateralized position (HF < 1.0)
  2. Compute profit: bonus_collateral - debt_to_repay - flash_fee - gas
  3. If profitable: submit bundle via Flashbots MEV-Share
  4. Smart contract: borrow debt token via flash loan
  5. Call liquidationCall() on Aave V3 → receive collateral
  6. Swap collateral for debt token (Uniswap V3)
  7. Repay flash loan + fee
  8. Net profit: collateral_value - debt - fees (all in one transaction)
```

### Pre-Funded Route (Speed Advantage, Top Bots)
```
Capital required:          $500K+ (to repay debt without flash loan overhead)
Advantage:                 100-200ms faster (no flash loan callback)
Disadvantage:              Capital lockup, liquidity management required
Used by:                   Top 3 bots (Wintermute MEV, institutional desks)
```

---

## 7. Venue Comparison Summary

| Venue                    | Gross Pool  | Competition  | Boutique Share | Est. Net Revenue | Accessible |
|-------------------------|------------|-------------|---------------|-----------------|-----------|
| Aave V3 Ethereum         | $27.5M     | EXTREME     | 1%            | $214K           | Yes        |
| Aave V3 L2 chains        | $5M        | MEDIUM      | 10%           | $440K           | Yes        |
| Compound V3              | $4M        | HIGH        | 3%            | $60K            | Yes        |
| HyperLiquid HLP          | $20M est.  | N/A         | 0%            | $0              | NO         |
| dYdX v4 (Cosmos)         | $1.25M     | LOW         | 15%           | $127K           | Yes        |
| Drift (Solana)           | $750K      | MEDIUM      | 8%            | ~$0             | Yes        |
| **Multi-venue boutique** | **$9.25M** | MIXED       | **varies**    | **~$567K**      | Partial    |

**Best single-venue opportunity:** Aave V3 L2 chains — medium competition, meaningful pool,
lower gas costs (L2 gas 10-100x cheaper than mainnet).

**Best multi-venue portfolio:** Aave V3 L2 + dYdX v4 = ~$567K net, two complementary chains,
avoids extreme mainnet competition while covering EVM + Cosmos.

---

## 8. Lighter Alternative: HL Cascade Signal (K372 Reactivation)

K372 originally explored fading liquidation cascades as a trading signal and was rejected.
However, reactivating the cascade DETECTION logic as an ENHANCEMENT to K376 momentum requires
only 5 days of work and zero smart contract risk:

### Mechanism
```
Input: HL open interest changes + mark price delta per 15-minute bar
Signal: cascade_volume_t > 2.0 × rolling_avg(cascade_volume, 48h)
  → Liquidation cascade detected

Effect on K376:
  - Increase position sizing: K376 signal × (1 + cascade_multiplier)
  - cascade_multiplier: 0.3 during cascade, decays over 4-8h
  
Effect on K208:
  - FR spike expected within 1-4h post-cascade
  - Temporarily increase FR carry position in cascade direction
```

### Expected Impact
- Incremental alpha: ~15bps per cascade event
- Cascade frequency: ~5-15 events/month on HL (volatile crypto market)
- Annual incremental revenue: ~$30-70K at $10M AUM (conservative)
- Implementation: 5 days, Python only, existing HL API

### Why This First
1. No smart contracts — no audit required, no catastrophic risk
2. Uses existing HL infrastructure already in production (K376 plist, K208 plist)
3. Compatible with K266 gates (continuous signal, daily Sharpe computable)
4. Captures liquidation event alpha without MEV bot complexity
5. Acts as "proof of concept" for cascade signal before committing to full MEV bot

---

## 9. Implementation Effort vs Revenue

| Strategy                  | Net Revenue/yr | Effort (months) | Capex  | ROI (1yr) | Status      |
|--------------------------|---------------|----------------|-------|----------|-------------|
| v6.20 (existing)          | $1,000,000    | 0              | $0    | ∞        | PRODUCTION  |
| MEV bot — Aave mainnet    | $214K         | 6              | $75K  | 185%     | DEFER       |
| MEV bot — Aave L2         | $440K         | 4              | $60K  | 633%     | DEFER       |
| MEV bot — dYdX v4         | $127K         | 5              | $70K  | 81%      | DEFER       |
| Multi-venue MEV bot       | $567K         | 6              | $90K  | 530%     | DEFER       |
| HL cascade signal (K372)  | $50K inc.     | 0.25           | $0    | ∞        | PURSUE NOW  |

**Observation:** While MEV ROI on capex looks attractive (530-633%), the opportunity cost is
6+ months of engineering that could instead be used to scale v6.20 AUM from $10M to $50M
($4M/yr vs $1M/yr), which is a 4x revenue lift for equivalent engineering effort.

---

## 10. Risk Assessment

### 10.1 Smart Contract Risk
- **Severity: CRITICAL** — liquidator contracts interact with DeFi protocols at scale
- Bug in flash loan callback: could lose entire flash loan amount (up to $10M+)
- Reentrancy attacks: must follow checks-effects-interactions pattern
- Oracle manipulation: adversary could manipulate oracle to trigger fake liquidations
- Mitigation: mandatory audit ($30K+), mainnet fork testing, circuit breakers

### 10.2 MEV Competition Risk
- **Severity: HIGH** — established bots with sub-50ms latency will outcompete initially
- Searcher tip wars: each liquidation triggers gas auction; loser pays gas for failed tx
- Front-running: without private relay, profitable bundles extracted by sandwich bots
- Mitigation: Flashbots MEV-Share, gradual market entry targeting niche collateral types

### 10.3 Operational Risk
- **Severity: MEDIUM** — 24/7 infrastructure uptime required
- Node downtime → miss liquidation events
- Gas estimation errors → unprofitable transactions
- Exchange rate slippage on collateral swap → profit erosion
- Mitigation: redundant nodes, conservative profit thresholds, simulation testing

### 10.4 Regulatory Risk
- **Severity: LOW-MEDIUM** — MEV legality varies by jurisdiction
- MiCA framework (EU): MEV activities may require licensing as "crypto-asset service provider"
- US: unclear; CFTC/SEC have not ruled on MEV specifically
- Mitigation: legal counsel before deployment, avoid front-running (only liquidations, not sandwiching)

---

## 11. Decision Matrix

### Primary Recommendation: DEFER

**Rationale:**
1. Revenue potential ($214K-$567K/yr boutique) is 22-57% of v6.20 baseline at $10M AUM
2. Implementation requires 4-6 months and $60-90K capex — equivalent to scaling v6.20 to $50M
3. Smart contract risk introduces tail loss not present in current portfolio
4. Competition from institutional MEV desks makes boutique market share uncertain
5. Revenue is capacity-limited (event-driven), not scalable with AUM

**Defer Trigger Conditions:**
- $100M+ AUM achieved (MEV becomes meaningful diversifier: 0.5-5% portfolio allocation)
- Dedicated MEV engineer hired (not founder/PM time)
- v6.20 production stable 6+ months with live track record
- Smart contract audit partner identified and budgeted

**Defer Review Date:** 2027-12-31

### Immediate Action: HL Cascade Signal (K372 Reactivation)

**Decision: PURSUE — 5-day implementation, no smart contracts**

This captures liquidation cascade alpha via signal enhancement to K376/K208 without MEV bot
infrastructure. Estimated $30-70K incremental revenue annually. Directly compatible with existing
production systems. No new risk categories introduced.

### Complete Reject: No

MEV liquidator is not permanently rejected — deferred with clear trigger conditions.
At $100M AUM, $500K-$5M MEV revenue becomes strategically meaningful (0.5-5% of portfolio).

---

## 12. Sleeve Weight Analysis

If MEV liquidator is eventually ACCEPTED as a sleeve:

```
AUM: $10M
  - MEV sleeve capital: $50K-100K (0.5-1%)
  - Flash loan based: capital is deployment buffer only, not trading capital
  - Revenue: $214K-$567K/yr absolute (not % of sleeve capital)
  - As % of total AUM return: 2.1-5.7% additional return contribution

AUM: $100M
  - MEV sleeve capital: $500K-1M (0.5-1%)
  - Revenue: same absolute $214K-$567K/yr (event-limited, not AUM-scalable)
  - As % of total AUM return: 0.2-0.6% additional return contribution
  - At $100M AUM, MEV contribution becomes negligible vs v6.20 at $10M/yr revenue

AUM: $1B+
  - MEV becomes truly negligible (<0.1% contribution)
  - Only viable as separate operation with institutional MEV desk infrastructure
```

**Conclusion:** MEV liquidator has higher strategic value at $10-50M AUM phase than at $100M+.
The optimal window for deployment is DURING the scaling phase, not after reaching large AUM.
This creates urgency for the 2027 review — if AUM reaches $50M before 2027, reassess sooner.

---

## 13. Memory Rule & Deferred List

**MEV Liquidator added to Deferred Strategy List:**

| Field                  | Value                                                          |
|-----------------------|---------------------------------------------------------------|
| Strategy name          | MEV Liquidator Bot (Aave V3 / dYdX v4 focus)                 |
| Wave                   | K470                                                          |
| Decision               | DEFER                                                         |
| Review trigger         | $100M+ AUM OR dedicated MEV engineer hired                    |
| Review date            | 2027-12-31                                                    |
| Expected revenue       | $214K-$567K/yr boutique, $1-5M/yr institutional              |
| Immediate alternative  | K372 cascade signal for K376 (5-day, pursue now)             |
| Risk flag              | Smart contract audit mandatory before any deployment          |

---

## Appendix A: On-Chain Parameter Reference

### Aave V3 LiquidationLogic.sol Constants

```solidity
uint256 internal constant DEFAULT_LIQUIDATION_CLOSE_FACTOR = 0.5e4;  // 50%
uint256 internal constant MAX_LIQUIDATION_CLOSE_FACTOR = 1e4;        // 100%
uint256 internal constant CLOSE_FACTOR_HF_THRESHOLD = 0.95e18;       // 0.95
```

### Typical Liquidation Bonus by Asset (Aave V3)

| Asset  | Bonus | Net (after 10% protocol fee) | Risk Tier |
|-------|------|------------------------------|-----------|
| WBTC  | 5%   | 4.5%                        | Low       |
| WETH  | 5%   | 4.5%                        | Low       |
| USDC  | 4.5% | 4.05%                       | Low       |
| DAI   | 4.5% | 4.05%                       | Low       |
| LINK  | 7.5% | 6.75%                       | Medium    |
| UNI   | 8.5% | 7.65%                       | Medium    |
| AAVE  | 10%  | 9.0%                        | High      |
| eMode | 1%   | 0.9%                        | Minimal   |

### Flash Loan Parameters
- Aave V3 flash loan fee: 9bps (0.09%)
- Can flash loan from same protocol being liquidated
- Maximum flash loan: limited by reserve liquidity (typically $100M+ for major assets)

---

## Appendix B: MEV-Share Revenue Split

```
Without MEV-Share (public mempool):
  Liquidation bundle → mempool → sandwich bots detect → front-run
  Liquidator keeps: 0-20% of theoretical profit (80% extracted by sandwichers)

With Flashbots MEV-Share:
  Liquidation bundle → private relay → validator
  MEV-Share split (approximate):
    - Searcher (liquidator): 30% of extracted value
    - User refund: 40% (returned to user being liquidated — unusual but MEV-Share design)
    - Validator tip: 30%
  Inclusion rate: ~95%
  Net to liquidator: 30% × gross_bonus (roughly 1.35% of liquidated amount on 4.5% bonus)
  Still profitable on large liquidations ($1M+), marginal on small ($50K)

Flashbots Protect (alternative):
  - 10% tip to validators
  - Searcher keeps 90% of bonus
  - Used for smaller liquidations where MEV-Share split is too punitive
```

---

## Appendix C: Gas Economics on L2 vs Mainnet

| Chain     | Gas Units | Gas Price | ETH Price | Cost/Liq | Bonus ($100K liq) | Net Viable |
|----------|----------|----------|----------|---------|------------------|-----------|
| Ethereum | 400K     | 15 gwei  | $2,500   | $15.00  | $4,500           | Yes        |
| Polygon  | 400K     | 200 gwei | $2,500   | $0.04   | $4,500           | Yes        |
| Arbitrum | 400K     | 0.1 gwei | $2,500   | $0.001  | $4,500           | Yes        |
| Base     | 400K     | 0.05 gwei| $2,500   | $0.0005 | $4,500           | Yes        |

**Key insight:** L2 gas costs are 3-4 orders of magnitude lower than Ethereum mainnet.
On L2, even small liquidations ($5K-$10K) are economically viable. This dramatically
expands the opportunity set for boutique liquidators on L2 chains where competition
is also significantly lower (fewer bots monitor L2 vs Ethereum mainnet).

**Recommended entry strategy (if ACCEPTED in 2027):** Start on Arbitrum + Base (Aave V3),
establish market share vs fewer competitors, then expand to mainnet once profitable.

---

*Wave K470 complete. Analysis only — no production scripts modified. K339 security rule upheld.*
*Next action: K471 should implement HL cascade signal detection (K372 reactivation) as K376 enhancer.*

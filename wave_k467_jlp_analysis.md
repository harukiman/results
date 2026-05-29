# K467 JLP Yield + Delta-Neutral Hedge Analysis
**Wave:** K467 | **Date:** 2026-05-30 | **Status:** COMPLETE  
**Author:** CT Lab Orchestrator | **Version:** v6.21 Candidate

---

## Executive Summary

JLP (Jupiter Perpetuals Liquidity Provider token) offers compelling yield during high-volatility crypto periods (50-70%+ APY historically), but **current live yield is only ~1.68% annualized** (DefiLlama, 2026-05-30). A delta-neutral hedge via Hyperliquid shorts is mechanically sound — costs ~11% annualized in steady-state costs — meaning the strategy only becomes net-positive above ~21% gross APY.

**Verdict: CONDITIONAL ACCEPT with trigger-based entry**  
Do NOT enter now (APY too low). Set APY monitoring threshold at 25% gross. Entry is viable and recommended when Jupiter perp volume rebounds.

**Proposed v6.21 sleeve: 5% of AUM, entry-triggered (APY monitor daemon)**

---

## 1. JLP Mechanism

### 1.1 What Is JLP?

JLP is the liquidity provider token for Jupiter Perpetuals, Solana's largest on-chain perpetuals exchange. JLP holders collectively act as the counterparty to all perp traders on Jupiter — when traders lose, LPs gain; when traders profit, LPs pay.

Yield sources:
1. **Trading fees:** 75 bps (7 bps base + impact fee) on each trade open/close, shared 75% to LPs (changed to 12.5% of total fees / 50% of protocol revenue in February 2025)
2. **Funding rates:** When longs pay funding, LPs receive it
3. **Liquidations:** Liquidation penalties distributed to LPs
4. **Basket appreciation:** Underlying SOL/ETH/BTC price movement (NOT yield — this is the delta exposure we hedge)

### 1.2 Fee Structure (from Gauntlet Analysis)

| Parameter | Value |
|-----------|-------|
| Base fee | 7 bps per trade |
| Impact fee scalar (SOL) | 1,000,000,000 |
| Impact fee scalar (ETH) | 5,000,000,000 |
| Impact fee scalar (BTC) | 8,000,000,000 |
| LP fee share (pre-Feb 2025) | 75% of trading fees |
| LP fee share (post-Feb 2025) | 50% of protocol revenue = 12.5% of total fees |

The February 2025 fee structure change significantly reduced LP revenue share. This is the primary driver of the current low APY.

### 1.3 Token Properties

- **Solana program:** Jupiter Perpetuals smart contract (multiple audits)
- **Lockup:** None — JLP is freely transferable and redeemable
- **Pricing:** Oracle-based (Pyth), marks underlying basket at fair value
- **Redemption:** Instant via Jupiter UI, subject to pool liquidity
- **Counterparty:** Decentralized (smart contract), no centralized custody

---

## 2. Live Data (DefiLlama, 2026-05-30)

| Metric | Value |
|--------|-------|
| Current TVL | $634.81M |
| Annualized fees (total) | $85.35M |
| 30-day fees | $7.0M |
| 7-day fees | $1.68M |
| 24-hour fees | $358K |
| All-time cumulative fees | $807.71M |
| Perp volume 30d | $5.252B |
| Open interest | $88.8M |
| **LP holders revenue (ann.)** | **$10.67M** |
| **LP holders revenue (30d)** | **$874K** |
| **Current JLP APY (derived)** | **~1.68%** |

### 2.1 APY Calculation

```
JLP Holder APY = Holders Revenue (annualized) / TVL
              = $10.67M / $634.81M
              = 1.68%
```

**Important context:** This is a market trough. Historical data:
- Pre-June 2024 fee change: **57.4%** avg APY (Gauntlet)
- Post-June 2024 fee change: **69.5%** avg APY (Gauntlet)
- Current jup.ag marketing: **8.77%** (trailing different period)
- DefiLlama derived (2026-05-30): **1.68%** (current trough)

APY is directly proportional to perp trading volume. Current low reflects a calm market period. Historical high-volatility episodes drive the 50-70% figures.

---

## 3. JLP Basket Composition

| Asset | Weight | $1M JLP | Hedge Required |
|-------|--------|---------|----------------|
| SOL | 44% | $440,000 | Short $440K SOL on HL |
| ETH | 9% | $90,000 | Short $90K ETH on HL |
| BTC | 11% | $110,000 | Short $110K BTC on HL |
| USDC | 27% | $270,000 | No hedge (stable) |
| USDT | 9% | $90,000 | No hedge (stable) |
| **Total volatile** | **64%** | **$640,000** | **Short $640K on HL** |
| **Total stable** | **36%** | **$360,000** | Pass-through |

Weights drift as prices move — rebalancing required monthly.

---

## 4. Delta-Neutral Hedge Construction

### 4.1 Mechanism

**Step 1:** Purchase JLP with USDC  
**Step 2:** Open short perpetual positions on Hyperliquid:
- Short SOL-PERP: 44% of JLP notional
- Short ETH-PERP: 9% of JLP notional
- Short BTC-PERP: 11% of JLP notional

**Result:** Price movements in SOL/ETH/BTC cancel out (long via JLP + short via HL = net zero). Only the YIELD component remains.

### 4.2 Hedge Precision

Basket weights change as SOL/ETH/BTC prices move. If SOL rallies 20%, its weight increases (e.g., 44% → 50%), creating temporary long delta. Monthly rebalancing maintains neutrality within ±5% delta band.

### 4.3 Existing Implementations (Market Validation)

This is NOT a novel untested strategy. Multiple production vaults exist:

| Protocol | Hedge Venue | Notes |
|----------|------------|-------|
| **Vectis Finance** (JLP HyperLoop) | Hyperliquid | Leveraged + keeper automation; 2% mgmt + 25% perf fees |
| **Neutral Trade** | Hyperliquid / Drift | Institutional-grade quant execution |
| **NX Finance** | Various | Delta-neutral vault with FAQ documentation |
| **Drift S1-E3** | Drift | Earlier implementation |

Vectis migrated from Drift to Hyperliquid citing **lower funding rates** (~5.31% vs ~10.39%) and reported +158.63% annualized return increase from funding improvement.

The existence of 4+ production implementations validates the mechanism.

---

## 5. Net Carry Analysis — Scenario Matrix

### 5.1 Cost Components

| Cost | Rate | Basis | Annual Cost (per $1M JLP) |
|------|------|-------|--------------------------|
| HL short funding | 5-12% ann | 64% of notional hedged | 3.2-7.7% |
| Rebalance (slippage + gas) | 0.5%/month | Monthly basket drift | 6.0% |
| Solana SC risk premium | 5.0% | Actuarial smart contract bug cost | 5.0% |
| **Total costs (base)** | — | — | **~14.2-18.7%** |

Note: When HL funding is positive, shorts EARN additional funding — reducing effective hedge cost. Vectis reported this as a meaningful bonus in volatile periods.

### 5.2 Scenario Matrix

| Scenario | Gross APY | Funding Rate | Hedge Cost | Rebal | SC Premium | **Net APY** | Gate G1 |
|----------|-----------|-------------|-----------|-------|------------|------------|---------|
| **Current (trough)** | 1.68% | 8% | 5.12% | 6.0% | 5.0% | **-14.44%** | FAIL |
| Low (quiet market) | 12% | 12% | 7.68% | 6.0% | 5.0% | **-6.68%** | FAIL |
| **Base case** | 20% | 8% | 5.12% | 6.0% | 5.0% | **+3.88%** | NEAR |
| Task estimate | 40% | 8% | 5.12% | 6.0% | 5.0% | **+23.88%** | PASS |
| High volatility | 40% | 5% | 3.20% | 6.0% | 5.0% | **+25.80%** | PASS |
| Historical peak | 70% | 8% | 5.12% | 6.0% | 5.0% | **+53.88%** | PASS |
| **Entry trigger** | **≥25%** | 8% | 5.12% | 6.0% | 5.0% | **≥8.88%** | PASS |

**Key finding:** The task's 21% net APY estimate is achievable ONLY when gross APY ≥ 40%, which requires high-volatility perp markets. Current APY is 1.68% — do not enter.

### 5.3 Break-Even Gross APY

```
Break-even gross = hedge_cost + rebal + sc_premium + target_net
Minimum viable (5% net) = 5.12% + 6.0% + 5.0% + 5.0% = 21.12%
Entry trigger (8% net)  = 5.12% + 6.0% + 5.0% + 8.0% = 24.12% ≈ 25% (round up)
```

---

## 6. Capacity Analysis

JLP TVL: $634.81M. Safety limit = 5% of TVL to avoid market impact.

| AUM | 5% Sleeve | % of JLP TVL | Feasible? |
|-----|-----------|-------------|----------|
| $1M | $50K | 0.01% | YES — trivial |
| $10M | $500K | 0.08% | YES |
| $50M | $2.5M | 0.39% | YES |
| $100M | $5M | 0.79% | YES |
| $500M | $25M | 3.94% | MARGINAL |
| **$800M** | **$40M** | **6.30%** | NO — exceeds 5% |

**Conclusion:** Strategy is capacity-feasible up to ~$500M AUM. Well within our operating range.

---

## 7. §6 Strict Gate Assessment (K266)

| Gate | Threshold | Value | Status |
|------|----------|-------|--------|
| G1: Net APY ≥ 5% | 5% net | 3.88% base / 25.80% high-vol | CONDITIONAL (triggered entry required) |
| G2: Perm p | N/A | Yield strategy (no directional backtest) | PASS |
| G3: Audit/counterparty | Audited | Jupiter audited; Solana SC risk remains | CONDITIONAL |
| G4: Delta-neutral 60d | Paper test | Not yet run | REQUIRES 60d forward test |
| G5: Corr vs K280 < 0.4 | < 0.40 | Est. 0.25 (both vol-dependent) | PASS |
| G6: Max single-event loss < 5% | < 5% portfolio | Jupiter exploit or basket depeg | CONDITIONAL |
| G7: Ann return > 5% net | 5% net | 25.80% in high-vol scenarios | CONDITIONAL (entry trigger) |

**Overall: CONDITIONAL ACCEPT** — not REJECT, not immediate ACCEPT.  
G1 and G7 are only satisfiable above the 25% gross APY trigger. Set APY daemon, enter when triggered.

---

## 8. Correlation Analysis

| Strategy Pair | Estimated Correlation | Reasoning |
|--------------|----------------------|-----------|
| JLP vs K280 (carry) | ~0.25 | Both crypto-derivative-dependent; carry = funding rates, JLP = perp volume. Related but distinct |
| JLP vs K297' (RWA) | ~0.05 | Near-zero; RWA = TradFi yield, JLP = crypto perp volume |
| JLP vs K344 (sUSDe) | ~0.20 | sUSDe also delta-neutral perp LP, but ETH-focused vs Solana |
| JLP vs K462 (ETF flows) | ~0.30 | Both reactive to crypto market activity |
| JLP vs K457 (basket carry) | ~0.35 | Both multi-asset basket, but different mechanisms |

JLP yield is driven by **perp trading volume** which spikes during volatility — providing **counter-cyclical diversification** vs directional strategies (which lose during volatility).

---

## 9. Comparison vs sUSDe (K344)

| Attribute | sUSDe (K344) | JLP delta-neutral (K467) |
|-----------|-------------|--------------------------|
| Gross APY | 3.7-4% | 1.68% now / 40-70% in vol |
| Net APY | 3.7-4% | -14% now / +26% in high-vol |
| Mechanism | Ethena: ETH LST + short ETH perp | Jupiter: perp LP fees + short SOL/ETH/BTC |
| Ecosystem | Ethereum | Solana + Hyperliquid |
| Custody risk | Centralized (Ethena) | Solana smart contract |
| Complexity | Low | Medium-High |
| APY volatility | Very low (stable) | Very high (vol-dependent) |
| Correlation to K280 | ~0.15 | ~0.25 |
| Current action | ACTIVE in v6.20 | MONITOR — enter when APY ≥ 25% |

**JLP can deliver 5-10x sUSDe yield in volatile periods, but is NOT a stable-yield replacement — it is a vol-harvesting instrument.**

---

## 10. Ecosystem Diversification Impact

Current v6.20 ecosystem concentration:
- Hyperliquid (HL): 47.5%
- Ethereum: ~30%
- Multi-venue: ~22.5%
- **Solana: 0%**

Adding 5% JLP sleeve:
- Adds Solana ecosystem exposure (first)
- JLP itself is on-chain Solana; hedge is on HL (already in portfolio)
- Net new ecosystem: Solana smart contract layer
- Diversification improvement: YES

---

## 11. Risk Matrix

| Risk | Probability | Severity | Mitigation |
|------|------------|---------|-----------|
| Jupiter smart contract exploit | Low (5%/yr estimate) | HIGH (total loss of JLP position) | Size 5% sleeve max; monitor exploit alerts |
| Solana network outage | Medium (historical outages) | MEDIUM (temp. position freeze) | HL hedge continues; JLP cannot exit during outage |
| Basket weight drift (delta leak) | HIGH (continuous) | LOW (recoverable at rebalance) | Monthly rebalance, ±5% delta band |
| HL funding turns negative | Medium | MEDIUM (hedge costs increase) | Exit trigger if funding > 15% annualized |
| JLP APY remains low | HIGH (current state) | MEDIUM (opportunity cost) | Do not enter — APY monitor daemon |
| Pyth oracle manipulation | Very low | HIGH | Mitigation: diversified oracle design |
| Liquidity fragmentation (large exit) | Low at our sizes | LOW | Capacity limit enforced |

---

## 12. Operational Playbook

### Setup (one-time, ~4 hours)

1. **Solana wallet:** Phantom or Backpack wallet
2. **SOL gas:** ~0.1 SOL for transaction fees
3. **JLP purchase:** Via Jupiter UI (jup.ag/perps) — swap USDC → JLP
4. **HL hedge accounts:**
   - Short SOL-PERP: 44% of JLP notional
   - Short ETH-PERP: 9% of JLP notional
   - Short BTC-PERP: 11% of JLP notional
5. **Verification:** Confirm net delta ≈ 0

### Monthly Rebalance (~1 hour/month)

1. Fetch current JLP basket weights from Jupiter UI
2. Compare vs hedge ratios on HL
3. If delta drift > ±3%: adjust HL positions
4. Log rebalance timestamp and costs
5. Update APY tracking spreadsheet

### APY Monitoring Daemon (automate)

The K412 sUSDe APY monitor pattern can be extended:
- Fetch JLP stats from DefiLlama API monthly
- Alert if gross APY > 25% → trigger entry review
- Alert if gross APY < 10% while position open → trigger exit review

---

## 13. Decision Matrix

| Criterion | Score (1-5) | Weight | Weighted |
|-----------|------------|--------|---------|
| Net APY when active | 4 (26% high-vol) | 30% | 1.20 |
| APY stability | 1 (highly volatile) | 20% | 0.20 |
| Smart contract risk | 2 (Solana SC) | 20% | 0.40 |
| Operational complexity | 3 (medium) | 10% | 0.30 |
| Ecosystem diversification | 5 (Solana — new axis) | 10% | 0.50 |
| Capacity | 4 (up to $500M AUM) | 10% | 0.40 |
| **Total** | | | **3.00 / 5.0** |

**Score 3.0/5.0 = CONDITIONAL ACCEPT with trigger-based entry**

---

## 14. v6.21 Proposal

### Action: Add JLP Yield Sleeve (Trigger-Based)

```
v6.21 change: +1 sleeve
  Sleeve: JLP delta-neutral yield
  Size: 5% of AUM (start 2% until 60d paper-test complete)
  Entry trigger: JLP gross APY ≥ 25% (DefiLlama 30d average)
  Exit trigger: JLP gross APY < 10% OR SC exploit alert
  Hedge: HL shorts (SOL 44%, ETH 9%, BTC 11%)
  Rebalance: Monthly
  Risk limit: Max 5% of JLP TVL ($31.7M at current TVL)
  Gate required: G4 (60d forward test) before scaling to 5%
```

### Current Status (2026-05-30)

- APY at 1.68% — **DO NOT ENTER**
- Add to watchlist; deploy APY monitor
- When APY rebounds ≥ 25%: execute entry protocol
- Expected entry window: Next high-volatility crypto period

---

## 15. Comparison vs Task Estimate

| Parameter | Task Estimate | Actual (Current) | Actual (High-Vol) |
|-----------|--------------|-----------------|------------------|
| Gross JLP APY | 40% | 1.68% | 40-70% |
| Hedge cost | 8% | 5.12% (8% × 64%) | 3.2% (5% × 64%) |
| Rebalance cost | 6% | 6% | 6% |
| SC risk premium | 5% | 5% | 5% |
| **Net APY** | **21%** | **-14.44%** | **+26-54%** |

The task estimate of 21% net is achievable — but only at 40%+ gross APY, which requires volatile markets. The current market is quiet. The strategy design is sound; timing is the variable.

---

## 16. Sources

- DefiLlama: Jupiter Perpetual Exchange TVL/fees (fetched 2026-05-30): https://defillama.com/protocol/jupiter-perpetual-exchange
- Gauntlet: Jupiter Perpetuals Fee Structure Analysis: https://www.gauntlet.xyz/resources/jupiter-perpetuals-fee-structure-implementation-and-proposed-adjustments
- Vectis Finance JLP HyperLoop Vault: https://docs.vectis.finance/vaults/jlp-hyperloop-vault
- Neutral Trade JLP delta-neutral: https://docs.neutral.trade/for-capital-allocators/quant-strategies/market-neutral/jupiter-jlp-delta-neutral
- CoinMarketCap JLP APY: https://coinmarketcap.com/cmc-ai/jupiter-perps-lp/what-is/
- Jupiter Perps UI (APY): https://jup.ag/perps/jlp-earn
- Futunn: Vectis 30% annualized analysis: https://news.futunn.com/en/post/60980313/30-annualized-a-deep-dive-into-vectis-jlp-s-secret
- NX Finance delta-neutral FAQ: https://nx-finance.gitbook.io/nx-finance-whitepaper/protocol-mechanism/strategy-3-delta-neutral-vault/jlp-delta-neutral-vault/jlp-delta-neutral-vault-faq

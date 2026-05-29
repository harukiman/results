# K437 — HL HYPE Staking Action Plan
**Wave:** K437 | **Generated:** 2026-05-29 23:03 JST | **Status:** COMPLETE

---

## Executive Summary

**Critical Price Correction:** K432 estimated Gold tier cost at ~$13,000 (using $1.30/HYPE from Nov-2024 airdrop era). HYPE is now **$59/token** — 45x higher. The Gold tier (10,000 HYPE) now costs **$590,000**, not $13,000. This completely changes the ROI calculus.

**Revised Recommendation:**
- **Immediate action:** Stake **100 HYPE = ~$5,900** for **Bronze tier** (10% fee discount)
- **ROI at Bronze:** $8,623/yr benefit on $5,900 cost = **143.9% annual ROI** ✓
- **Do NOT stake Gold** at $10M AUM: $590K cost for $30K/yr benefit = 2.9% ROI (below sUSDe APY)
- **Gold tier trigger:** Revisit when AUM ≥ $100M

---

## 1. HYPE Market Data (2026-05-29)

| Metric | Value |
|--------|-------|
| Current price | $59.00 (range: $56.77–$62) |
| All-time high | $64.63 (2026-05-26) |
| Market cap | $15.6B (CMC rank #9) |
| Staking APY | 2.26%/yr (auto-compound, no lock) |
| K432 assumed price | $1.30 (Nov-2024 airdrop) |
| Price increase since K432 estimate | **45x** |

---

## 2. Staking Mechanics

### 2.1 How It Works

HYPE uses a validator-delegation model on Hyperliquid L1:

1. Transfer HYPE from spot account → staking account (instant)
2. Delegate to a validator (Foundation validator recommended)
3. 1-day lockup after delegation before undelegation allowed
4. Rewards accrue every minute, auto-compound daily

### 2.2 Key Parameters

| Parameter | Detail |
|-----------|--------|
| Minimum stake | None (validators need 10K HYPE; delegators have no minimum) |
| Unstaking queue | **7 days** (staking account → spot account) |
| Slashing risk | **ZERO** (no automatic slashing; validators are jailed, not slashed) |
| Auto-compound | **YES** (rewards re-delegated automatically) |
| Staking APY | ~2.26% at current total stake (~400M HYPE staked) |
| Commission | Varies by validator; capped (cannot increase unless new rate ≤ 1%) |

### 2.3 Fee Discount Tiers

| Tier | HYPE Required | Cost at $59 | Discount | Discount Type |
|------|---------------|-------------|----------|---------------|
| None | 0 | $0 | 0% | Baseline |
| Wood | 10 | $590 | 5% | Applied to all HL fees |
| Bronze | 100 | $5,900 | 10% | Applied to all HL fees |
| Silver | 1,000 | $59,000 | 15% | Applied to all HL fees |
| **Gold** | **10,000** | **$590,000** | **20%** | Applied to all HL fees |
| Platinum | 100,000 | $5,900,000 | 30% | Applied to all HL fees |
| Diamond | 500,000 | $29,500,000 | 40% | Applied to all HL fees |

Discount stacks **multiplicatively** with volume tier fees. E.g., at volume Tier 1 (1.2 bps maker), Bronze gives 0.2% × (1 - 10%) = 1.08 bps effective maker fee.

---

## 3. HL Volume Model (K302a @ 3x Leverage)

K302a routes ~60% of capital through HyperLiquid:

| Sleeve | HL Notional | RT/yr | Annual HL Volume |
|--------|------------|-------|-----------------|
| K208 HL leg (31.7% AUM × 3x) | $9.5M | 26 | $247.5M |
| K297p satellite (20% AUM × 3x) | $6.0M | 4 | $24M |
| K276b HL (35.2% AUM × 3x) | $10.6M | 26 | $275.6M |
| **Conservative (K208+K297p)** | — | — | **$375M/yr** |
| **Full estimate (all sleeves)** | — | — | **$580M/yr** |

At $375M annual HL volume → 14-day proxy = $14.4M → **Volume Tier 1** (threshold: $5M 14d)

---

## 4. ROI Analysis at $10M AUM

### 4.1 Fee Schedule at Volume Tier 1

| Fee Type | Rate |
|----------|------|
| Perps taker | 4.0 bps (0.040%) |
| Perps maker | 1.2 bps (0.012%) |
| Maker fill rate | 62% (K378 central estimate) |

**Annual baseline HL fees (no stake, $375M volume):**
- Maker: $375M × 62% × 0.012% = $27,900
- Taker: $375M × 38% × 0.040% = $57,000
- **Total: $84,900/yr**

### 4.2 Tier ROI Table at $10M AUM

| Tier | Stake Cost | Ann Fee | Fee Saving | Stk Yield | Total Benefit | ROI | Payback |
|------|-----------|---------|-----------|-----------|--------------|-----|---------|
| None | $0 | $84,900 | — | — | — | — | — |
| Wood | $590 | $80,655 | $4,245 | $13 | $4,258 | **719.5%** | 1.7mo |
| **Bronze** | **$5,900** | **$76,410** | **$8,490** | **$133** | **$8,623** | **143.9%** | **8.2mo** |
| Silver | $59,000 | $72,165 | $12,735 | $1,333 | $14,068 | 21.6% | 50.3mo |
| Gold | $590,000 | $67,920 | $16,980 | $13,334 | $30,314 | 2.9% | 233.6mo |
| Platinum | $5,900,000 | $59,430 | $25,470 | $133,340 | $158,810 | 0.4% | 445.8mo |

**Winner at $10M AUM: Bronze tier.** 143.9% ROI, 8.2-month payback, $5,900 stake cost (trivial).

### 4.3 Why Not Gold at $10M AUM?

- Gold = $590,000 locked in HYPE (6% of $10M AUM)
- Annual benefit = $30,314 (fee saving + staking yield)
- ROI = 2.9% — **less than sUSDe 5% APY** or BTC yield
- Opportunity cost: $590K in sUSDe = ~$29,500/yr at 5% (similar total benefit, no HYPE price risk)
- HYPE breakeven: HYPE can only drop 5.1% before 1-year net is negative
- At ATH territory ($59, ATH $64.63), downside risk is real

---

## 5. ROI Analysis at $50M AUM

At $50M: HL volume = $1,875M/yr → 14d proxy = $71.9M → **Volume Tier 2**

### 5.1 Fee Schedule at Volume Tier 2

| Fee Type | Rate |
|----------|------|
| Perps taker | 3.5 bps |
| Perps maker | 0.8 bps |

**Annual baseline fees: $342,375/yr**

### 5.2 Tier ROI Table at $50M AUM

| Tier | Stake Cost | Fee Saving | ROI | Payback |
|------|-----------|-----------|-----|---------|
| Wood | $590 | $17,119 | **2901.5%** | 0.4mo |
| Bronze | $5,900 | $34,238 | **580.3%** | 2.1mo |
| Silver | $59,000 | $51,356 | **87.0%** | 13.4mo |
| Gold | $590,000 | $68,475 | **11.6%** | 86.5mo |
| Platinum | $5,900,000 | $102,712 | 1.7% | 299.9mo |

At $50M AUM, **Silver** (1,000 HYPE = $59,000) becomes highly attractive: 87% ROI, 13.4-month payback. Gold at 11.6% is marginal.

---

## 6. Corrected vs K432 Mandate Estimates

| Item | K432 Mandate | K437 Corrected | Error Source |
|------|-------------|---------------|-------------|
| HYPE price | $1.30 | **$59.00** | 45x underestimate (airdrop price) |
| Gold tier cost | $13,000 | **$590,000** | Price × 45 |
| Gold ROI @$10M | 19.5% | **2.9%** | Cost 45x higher |
| Optimal tier | Gold | **Bronze** | Cost-ROI analysis |
| Optimal tier cost | $13,000 | **$5,900** | Different tier |
| Annual benefit (optimal) | $2,534 | **$8,623** | Bronze saves more per dollar |
| Recommended stake @$50M | 50K HYPE | **1,000 HYPE (Silver)** | Cost reality check |

---

## 7. HYPE Price Risk Analysis

### 7.1 Bronze Tier ($5,900 stake)

| Scenario | 1-Year P&L |
|----------|-----------|
| HYPE +50% (to $88.50) | +$2,950 capital gain + $8,623 benefit = +$11,573 |
| HYPE flat ($59) | $0 + $8,623 = +$8,623 |
| HYPE -20% (to $47.20) | -$1,180 + $8,623 = +$7,443 |
| HYPE -50% (to $29.50) | -$2,950 + $8,623 = +$5,673 |
| Breakeven exit price | **$45.77** (22.4% drop from current) |

Bronze tier is robust: HYPE must drop >22% AND stay there for a full year to produce a net loss.

### 7.2 Gold Tier ($590,000 stake) — Why Risky at $10M AUM

| Scenario | 1-Year P&L |
|----------|-----------|
| HYPE flat | $0 + $30,314 = +$30,314 |
| HYPE -10% (to $53.10) | -$59,000 + $30,314 = **-$28,686** |
| HYPE -50% (to $29.50) | -$295,000 + $30,314 = **-$264,686** |
| Breakeven exit price | **$55.97** (only 5.1% drop from current) |

Gold tier at $10M AUM has near-ATH HYPE exposure with very thin margin of safety.

### 7.3 Hedge Strategy (Optional)

Open 1x HYPE-USD short on HL perps to neutralize price exposure:
- Removes all HYPE price risk
- Cost: ~1–3% annual funding (HYPE typically mild positive FR)
- Net annual benefit after hedge (Bronze): ~$8,490 + $133 - ~$60 hedge = **~$8,560/yr**
- Not necessary for Bronze (small size). Worth it for Silver/Gold positions.

---

## 8. User Procurement Playbook

### Step-by-Step: Bronze Tier (Recommended)

1. **Buy 100 HYPE on HL spot**
   - Go to app.hyperliquid.xyz → Spot → HYPE/USDC
   - Buy 100 HYPE at market (~$5,900)
   - Alternatively: buy on Coinbase/Bybit, withdraw to HL wallet

2. **Transfer to Staking Account**
   - HL dashboard → Portfolio → Transfer → Spot → Staking
   - Amount: 100 HYPE
   - Instant (no fee, no delay)

3. **Delegate to Validator**
   - Go to app.hyperliquid.xyz/staking
   - Select a Foundation validator (check commission < 5%)
   - Click "Delegate" → enter 100 HYPE
   - Confirm transaction

4. **Verify Fee Tier**
   - HL trading dashboard → Account → Fee Tier
   - Should show "Bronze" with 10% discount
   - Allow up to 1 trading session (a few minutes) for activation

5. **Monitor Monthly**
   - Check staking rewards accrued (auto-compound, visible in staking balance)
   - Confirm Bronze tier remains active
   - At $50M AUM: upgrade to Silver (buy 900 more HYPE, delegate)

### Unstaking if Needed

1. Go to staking page → Undelegate
2. Wait 1 day (delegation lockup)
3. Transfer: Staking Account → Spot Account
4. **Wait 7 days** (unstaking queue)
5. HYPE now in spot, freely tradeable

**Note:** 5 pending withdrawals maximum per address. Plan unstakes accordingly.

---

## 9. Integration with K434 Smart Router

The K434 smart router scores venues by: `FR_capture + maker_rebate/8 - spread/2`

With HYPE staking active:
- HL effective maker fee decreases (10% discount at Bronze)
- HL routing score marginally improves
- More K208 volume routed to HL → more fee savings from staking discount → virtuous cycle

**Combined effect at Bronze ($10M AUM):**
- K434 smart router: +$175K/yr (primary lever)
- HYPE Bronze stake: +$8.6K/yr (secondary lever)
- Total: ~$183.6K/yr additional benefit vs baseline

---

## 10. Scaling Path

| AUM | Optimal Tier | Stake Cost | Annual Benefit | ROI |
|-----|-------------|-----------|---------------|-----|
| $10M now | **Bronze** | $5,900 | $8,623 | 143.9% |
| $25M | **Bronze→Silver** | +$53,100 | +$25,000 incremental | ~47% marginal |
| $50M | **Silver** | $59,000 | $51,356 | 87.0% |
| $100M+ | **Gold** | $590,000 | ~$137K | ~23% |
| $500M+ | **Platinum** | $5,900,000 | ~$686K | ~11.6% |

---

## 11. Decision

### Recommended Action (Immediate, $10M AUM)

```
BUY: 100 HYPE on HL spot
COST: ~$5,900
STAKE: app.hyperliquid.xyz/staking → delegate to Foundation validator
TIER: Bronze (10% fee discount, activated immediately)
ANNUAL BENEFIT: ~$8,623/yr (fee saving + staking yield)
ROI: 143.9%/yr
PAYBACK: 8.2 months
HYPE RISK: Low — needs 22%+ sustained drop for net loss
```

### Do NOT Do (for now)

```
DO NOT stake Gold at $10M AUM:
  - 10,000 HYPE = $590,000 at current prices
  - Annual benefit = $30,314/yr
  - ROI = 2.9% (worse than sUSDe 5% APY, below inflation)
  - HYPE breakeven = $55.97 (only 5.1% drop erases 1yr)
  - HYPE is near ATH — poor risk/reward
  - Revisit at AUM ≥ $100M
```

---

## 12. Risk Summary

| Risk | Bronze ($5,900) | Gold ($590,000) |
|------|----------------|----------------|
| Capital at risk | $5,900 (0.059% of AUM) | $590,000 (5.9% of AUM) |
| Break-even HYPE drop | 22.4% | 5.1% |
| 7-day liquidity lock | Yes (unstaking queue) | Yes (same) |
| Slashing | None | None |
| Validator jailing | Temporary reward pause only | Same |
| Opportunity cost | Negligible | ~$29,500/yr (vs sUSDe 5%) |
| Verdict | **PROCEED** | **DEFER to $100M+ AUM** |

---

## References

| Wave | Content |
|------|---------|
| K432 | Original HYPE Gold stake estimate ($13K cost, 19.5% ROI — now corrected) |
| K434 | Smart router daemon scaffold (primary HL lever, $175K/yr @ $10M) |
| K370 | Builder rebate (zero cost, highest absolute ROI lever) |
| K302a | v6.12 production architecture (HL 60% capital, K208+K276b+K297p) |

---

*K437 — HL HYPE Staking Action Plan — 2026-05-29 23:03 JST*

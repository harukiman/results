# K354 — USDH Stablecoin Yield Arb Exploration (R11-8)

**Wave**: K354 | **Generated**: 2026-05-27T07:11:42+09:00
**Task**: Deep-dive USDH as v6.14 sleeve complement to K344 sUSDe
**Decision**: **REJECT**

---

## Executive Summary

USDH, Hyperliquid's native stablecoin, is being **sunset as of May 2026**. Coinbase acquired the USDH brand assets and is replacing USDH with USDC as Hyperliquid's primary quote asset. This fundamentally invalidates the premise of USDH as a K344 sUSDe sleeve complement:

1. **0% direct yield to holders** — USDH reserve yield is distributed to HL Assistance Fund (50%) and builder grants (50%), not passed through to token holders. Unlike sUSDe (3.72% APY to holders), USDH is a non-yielding stablecoin.
2. **Sunset in progress** — Market cap declining ($90.7M → $62.4M in days), secondary market thinning, HypurrFi USDH pool winding down.
3. **Gates cleared: 2/5** — Only G2 (peg deviation) and G3 (audit) pass. G1 (yield), G4 (effective TVL), G5 (correlation) all fail.

**Verdict: REJECT — do not add to v6.14 portfolio.**

---

## Phase 1: Protocol Intelligence

### Protocol Structure

| Field | Value |
|-------|-------|
| Name | USDH |
| Issuer | Native Markets / Bridge Building Inc. |
| Chain | HyperEVM (Hyperliquid L1) |
| Launch | September 2024 |
| Type | Fiat-backed stablecoin |
| Peg | 1:1 USD |
| Reserve Assets | Cash, short-term US Treasuries, repo agreements |
| Reserve Managers | BlackRock (BUIDL), Superstate (USTB) |
| Custody | JPMorgan Chase + Fireblocks |
| Issuance Platform | Stripe Bridge |
| GENIUS Act Compliant | Yes |
| Audit | Monthly independent attestation (ongoing) |

### Market Data (2026-05-27 snapshot)

| Metric | Value |
|--------|-------|
| Price | $0.9874 (-1.26% below peg) |
| Market Cap | $62.44M (declining from ~$90.7M) |
| Circulating Supply | 63.24M USDH |
| ATH | $1.01 (Feb 6, 2026) → +1.0% above peg |
| ATL | $0.9845 (Oct 10, 2025) → -1.55% below peg |
| 24h Volume | $6.41M |

---

## Phase 2: Critical Event — USDH Sunset (May 2026)

### What Happened

In mid-May 2026, **Coinbase acquired the USDH brand assets** from Native Markets and became Hyperliquid's official USDC treasury deployer under the Aligned Quote Asset (AQA) framework.

**Key terms:**
- Native Markets granted Coinbase the right to purchase USDH brand assets
- Coinbase deploys USDC across HL spot, perp, and HIP-4 markets
- **Coinbase shares ~90% of USDC reserve yield with Hyperliquid protocol**
- HYPE buyback mechanism preserved: USDC yield → HL Assistance Fund → HYPE buyback
- USDH holders can redeem 1:1 feeless via Native Markets dashboard (no hard deadline)

### Why USDH Failed to Scale

- USDH market cap peaked at ~$101.75M vs $5B+ in USDC circulating on Hyperliquid
- No yield pass-through to holders → no incentive to hold USDH over USDC
- Thin secondary market liquidity limited institutional adoption

### Impact on Infrastructure

| Component | Status |
|-----------|--------|
| USDH Dashboard | Active (feeless redemption) |
| HypurrFi USDH isolated pool | Winding down (TVL was $854K at K337) |
| HL spot markets (USDH-quoted) | Migrating to USDC |
| HL perp markets | USDC primary (was already dominant) |

---

## Phase 3: Yield Mechanism Analysis

### USDH Yield Structure

**Critical finding: USDH passes 0% yield to token holders.**

```
Reserve yield from US Treasuries (~4-5% APY on backing)
    ├── 50% → HL Assistance Fund → HYPE token buyback
    └── 50% → USDH Growth Fund → Developer grants & ecosystem incentives
        └── 0% → USDH holders
```

This is fundamentally different from:
- **sUSDe**: ETH staking + Ethena delta-neutral hedge → ~3.72% APY *directly to sUSDe holders*
- **USDC on Aave/Compound**: ~3.5% APY *directly to depositors*
- **USDT**: 0% to holders (similar model to USDH)

### Yield Comparison

| Asset | Direct Holder APY | Mechanism |
|-------|------------------|-----------|
| USDC (plain) | 0% | No yield |
| USDH | **0%** | Yield redirected to HL ecosystem |
| USDC on Aave | ~3.5% | Lending market rate |
| sUSDe (K344) | **3.72%** | ETH staking + delta-neutral hedge |
| sUSDe 7d MA | 4.04% | Same mechanism |
| sUSDe historical mean | 10.30% | Same mechanism (2024-2026) |
| USDH on HypurrFi isolated | ~9-15%* | Lending market rate (pool winding down) |

*HypurrFi USDH lending APY is conditional on the pool surviving the sunset. TVL was $854K at K337 (too small), now likely declining further.

### Trading Benefits (Non-Yield)

USDH offered trading perks on Hyperliquid:
- 0% lower taker fees on USDH-quoted markets
- 50% higher maker rebates for LPs
- 20% amplified volume for fee tier calculations

These are **execution cost reductions for active traders, not passive yield**.

---

## Phase 4: Peg Arb Opportunity Quantification

### Price History

| Metric | Value |
|--------|-------|
| ATH | $1.01 (+1.00% above peg) |
| ATL | $0.9845 (-1.55% below peg) |
| Current | $0.9874 (-1.26% below peg) |
| Formal depeg incidents | 0 |

*Note: 30d tick data unavailable — CoinGecko API returned 404 for this token ID; CMC free tier blocks granular history. Analysis based on CMC ATH/ATL metadata.*

### Current Discount — Sunset Risk Premium

The current -1.26% discount is **NOT a clean peg arb**. It represents:

1. **Redemption uncertainty**: No hard deadline for USDH→USDC conversion announced
2. **Counterparty wind-down risk**: Native Markets is transitioning operations
3. **Liquidity thinning**: Market makers withdrawing as protocol winds down
4. **Opportunity cost**: Capital locked during uncertain redemption timeline

**One-time arb math:**

| Component | Value |
|-----------|-------|
| Buy price | $0.9874 |
| Par redemption | $1.0000 |
| Gross spread | +1.26% |
| Slippage | -0.20% |
| Gas (HyperEVM) | -0.01% |
| Redemption delay risk | -0.50% |
| **Net spread** | **+0.55%** |

**Conclusion**: ~0.55% one-time gain. Trivial. One-directional (buy the dip, redeem). Not a systematic yield strategy or portfolio sleeve.

---

## Phase 5: K344 sUSDe Correlation Assessment

### Mechanistic Comparison

| Dimension | sUSDe (K344) | USDH (K354) |
|-----------|-------------|-------------|
| Yield driver | ETH staking + Ethena delta-neutral | US Treasury yield (NOT passed to holders) |
| Holder APY | 3.72% (current), 10.30% (hist mean) | **0%** |
| Peg mechanism | Soft peg via redemption + market | Hard peg via fiat reserve |
| Risk type | ETH price + funding rate | Treasury + counterparty (Stripe/Bridge) |
| Orthogonality | — | Mechanistically orthogonal |
| Practical | — | **Irrelevant (0% yield)** |

### Correlation Computation

Statistical ρ between sUSDe APY and USDH holder yield cannot be computed:
- sUSDe APY series: available (K344 data, 831 days)
- USDH holder yield series: **all zeros** (no pass-through mechanism)
- ρ(constant, anything) = undefined / 0

**G5 assessment**: The two assets are *mechanistically* orthogonal (different yield drivers), but USDH provides **no yield axis to be orthogonal on**. The combined sleeve would simply be: sUSDe 5% allocation earning 3.72% + USDH 3-5% allocation earning 0% = blended underperformance vs pure sUSDe.

---

## Phase 6: K266 Strict Gate Results

| Gate | Criterion | Threshold | Actual | Pass |
|------|-----------|-----------|--------|------|
| G1 | Net APY ≥ 5% | 5.0% | **0.0%** (holder yield) | FAIL |
| G2 | Max peg deviation < 5% | 5.0% | 1.55% (ATL) | PASS |
| G3 | Audit status verified | Monthly attestation | Active ongoing | PASS |
| G4 | TVL > $20M + institutional backing | $20M | $62.4M MCap (declining) | FAIL* |
| G5 | Orthogonal to K344 (\|ρ\| < 0.4) | 0.4 | Undefined (0% yield) | FAIL |

*G4: Market cap technically > $20M but sunset in progress, TVL declining ~$1M/day, effective operational TVL → 0.

**Summary: 2/5 gates cleared (G2, G3). REJECT.**

---

## Final Decision

### REJECT — USDH as v6.14 Sleeve Candidate

**Reasons:**
1. **Sunset**: USDH is deprecated. Coinbase/USDC replaces it as HL's native quote asset.
2. **No yield**: 0% direct yield to holders eliminates the entire premise.
3. **Gate failures**: G1 (yield), G4 (effective), G5 (correlation) — 3/5 gates fail.
4. **Not orthogonal yield diversification**: Adding a 0%-yielding stable dilutes K344 sUSDe.
5. **One-time arb**: The ~0.55% sunset discount arb is a one-off, not a strategy.

### Alternative: USDC-on-Hyperliquid via Coinbase Deal

The Coinbase/HL deal creates a more interesting potential sleeve:
- Coinbase shares **~90% of USDC reserve yield** with HL protocol
- If HL distributes any portion to HYPE stakers, LP providers, or users → potential yield mechanism
- Monitor: does the USDC reserve yield share flow to any on-chain claimable product?
- **K355+**: If a USDC yield product emerges on Hyperliquid post-sunset, revisit as sleeve

### v6.14 Portfolio Status

| Component | Status | Allocation |
|-----------|--------|-----------|
| K344 sUSDe (Ethena) | ACTIVE | 5% (pending v6.14 decision) |
| K354 USDH | **REJECTED** | 0% |
| USDC-HL yield (Coinbase deal) | MONITOR | TBD (K355+) |

---

## Data Sources

| Source | URL | Quality |
|--------|-----|---------|
| USDH Official | https://usdh.com/ | Fetched |
| CoinMarketCap USDH | https://coinmarketcap.com/currencies/hyperliquid-usd/ | Fetched |
| The Block — Coinbase/HL deal | https://www.theblock.co/post/401233/coinbase-hyperliquid-official-deployer-usdc | Searched |
| Unchained Crypto — USDH sunset | https://unchainedcrypto.com/coinbase-becomes-hyperliquids-official-usdc-treasury-deployer-as-usdh-sunsets/ | Searched |
| BeinCrypto — Coinbase USDH | https://beincrypto.com/coinbase-usdh-hyperliquid-shifts-to-usdc/ | Fetched |
| DefiLlama HypurrFi | https://defillama.com/protocol/hypurrfi | Fetched |
| wave_k337_hypurrfi_euler.json | local | Exact |
| wave_k344_ethena_optimal_control.json | local | Exact |

### Research Gaps

- CoinGecko USDH 30d price tick data: API 404 (token not indexed or endpoint deprecated)
- DefiLlama USDH stablecoin page: 403 Forbidden
- HypurrFi USDH isolated pool current APY: requires app.hypurrfi.com (auth-gated)
- Coinbase USDC revenue share pass-through: ~90% to HL protocol, recipient mechanism TBD

---

*K354 complete. USDH: REJECT. Monitor USDC-on-HL Coinbase deal yield mechanism for K355+.*

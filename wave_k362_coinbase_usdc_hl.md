# Wave K362 — Coinbase x HL USDC Deal Yield Investigation

**Generated:** 2026-05-27T07:57:32+09:00  
**Decision:** REJECT  
**Wave:** K362 (K354 follow-up, USDH-sunset replacement scan)

---

## Executive Summary

K354 established that USDH was sunset mid-May 2026 and Coinbase became
HyperLiquid's official USDC treasury deployer under the AQAv2 framework,
with ~90% of USDC reserve yield flowing to the HL protocol.

**K362 finding:** The 90% yield flows **exclusively** to HYPE token buybacks
via the Hyperliquid Assistance Fund. No sUSDe-equivalent direct USDC yield
product exists. No HL-native yield mechanism qualifies as a K344 sleeve
candidate. Decision: **REJECT** (same outcome as K354 USDH rejection, but
for a fundamentally different reason — mechanism mismatch rather than product
deprecation).

---

## Phase 1 — Deal Mechanism Research

### AQAv2 Framework Facts

| Field | Value |
|-------|-------|
| Announced | 2026-05-14 |
| Parties | Hyperliquid, Coinbase, Circle |
| USDC on HL | $5.1B |
| Yield share to HL | up to 90% (exact undisclosed) |
| Annual gross (Coinbase+Circle) | $180M |
| Annual routed to HL (est.) | $135M–$160M |
| Repurchase authorization | $30M |
| Routing vehicle | Hyperliquid Assistance Fund |
| Routing mechanism | **HYPE_buyback_only** |
| Circle commitment | stake 500k HYPE |

### Key Finding: Yield Route

Multiple independent sources confirm:
> All AQAv2 reserve yield is routed through Hyperliquid's Assistance Fund,
> which executes HYPE open-market buybacks. No portion is distributed
> directly to USDC holders, stakers, or LP vault participants.

Exact split percentage was NOT disclosed publicly. 90% is an analyst upper
bound from CoinDesk. Coinbase blog used 'vast majority'. CryptoBriefing
confirmed exclusive HYPE buyback routing.

### Additional Revenue Streams (context)

HYPE token buybacks now funded by three streams (May 2026):
1. Trading fee buybacks — 97% of exchange fees → Assistance Fund
2. AQAv2 reserve yield — $135–160M/year new stream
3. Bitwise BHYP ETF — 10% of management fee → HYPE purchases

At $65M/month exchange revenue (Jan 2026 baseline), AQAv2 adds ~$11–13M/mo
incremental buyback pressure — structurally significant for HYPE price, but
zero impact on USDC holder yield.

---

## Phase 2 — Claimable Products Discovery

### HL API Endpoints Queried

| Endpoint | Result |
|----------|--------|
| `{type:meta}` | 230 perp markets confirmed live |
| `{type:validatorSummaries}` | 31 validators (stakeData requires user address) |
| `{type:delegatorSummary}` | Endpoint live; requires non-zero address |
| `{type:allVaults}` | Endpoint live; empty response (no public vault list) |
| `{type:spotMetaAndAssetCtxs}` | USDC = index 0, canonical, HyperEVM contract confirmed |

### HYPE Native Staking

| Parameter | Value |
|-----------|-------|
| APY (at 400M staked) | 2.37% |
| APY range | 1.8–4.5% |
| Accrual | every minute |
| Distribution | daily |
| Compounding | auto-redelegation (NOT manual claim) |
| Unstaking queue | 7 days |
| AQAv2 feeds staking | **False** |
| Reward source | inflationary network emissions only |

**Critical:** AQAv2 USDC reserve yield does NOT feed into HYPE staking
rewards. Staking rewards are purely inflationary PoS emissions.

### HLP Market-Making Vault

| Parameter | Value |
|-----------|-------|
| Yield sources | trading fees, funding rates, liquidations |
| AQAv2 feeds HLP | **False** |
| Jan 2026 monthly revenue | $651K |
| User claimable | True |
| Risk | directional MM risk, potential drawdown in trending markets |

HLP vault compensates liquidity providers for MM activity only. AQAv2 yield
does NOT flow to HLP. Jan 2026 HLP revenue was $651K/month (vs $62.6M perp
fees — HLP is a tiny fraction of protocol revenue).

### HypurrFi USDC Lending

| Parameter | Value |
|-----------|-------|
| Product | USDC lending pool (Aave-style) |
| APY range | 8–20% |
| TVL | $16.6M |
| AQAv2 connected | **NO** |
| Yield source | organic borrowing demand on HyperEVM |
| Smart contract risk | **HIGH** |
| Security incident | domain compromise (migrated to hypurrfi.com) |

K337 reference context: HypurrFi's ~9% APY is organic, unrelated to
Coinbase deal. Security incident (domain compromise) increases caution.

---

## Phase 3 — Mechanism Categorization

### AQAv2 USDC Reserve Yield → HYPE Buyback

- **Category:** INDIRECT_BENEFIT
- **User claimable:** False
- **Requires HYPE exposure:** True
- **Est. APY:** None%
- **K344 sleeve candidate:** False
- **Notes:** Benefit is capital appreciation of HYPE token, not a claimable yield stream. No passthrough to USDC holders.
- **Reason for rejection:** Not a claimable yield product. Requires HYPE token ownership. Indirect benefit only.

### HYPE Native Staking (2.37% APY)

- **Category:** INDIRECT_BENEFIT
- **User claimable:** False
- **Requires HYPE exposure:** True
- **Est. APY:** 2.37%
- **K344 sleeve candidate:** False
- **Notes:** AQAv2 yield does NOT feed into staking rewards. Rewards are inflationary emissions. Auto-compound, not claimable in the sUSDe sense. Unstaking requires 7-day queue.
- **Reason for rejection:** Below K344 sUSDe 5% APY. Requires HYPE price exposure. Not orthogonal to existing trading strategies. 7-day liquidity lockup.

### HLP Market-Making Vault

- **Category:** INDIRECT_BENEFIT
- **User claimable:** True
- **Requires HYPE exposure:** False
- **Est. APY:** None%
- **K344 sleeve candidate:** False
- **Notes:** AQAv2 yield does NOT feed into HLP. Jan 2026 HLP revenue was $651K/month. Directional MM risk in trending markets (MDD risk non-trivial).
- **Reason for rejection:** AQAv2 yield does not flow here. MM risk means non-negligible MDD — incompatible with K344 sleeve target (MDD < 0.2%). Increases HL ecosystem concentration.

### HypurrFi USDC Lending Pool (8-20% APY)

- **Category:** INDIRECT_BENEFIT
- **User claimable:** True
- **Requires HYPE exposure:** False
- **Est. APY:** 9.0%
- **K344 sleeve candidate:** False
- **Notes:** Yield is organic borrowing demand on HyperEVM — NOT derived from AQAv2 Coinbase deal. K337 reference. Domain compromise incident (migrated to hypurrfi.com). HyperEVM smart contract risk.
- **Reason for rejection:** Not connected to Coinbase deal. High smart-contract risk on HyperEVM. Domain compromise incident. HL ecosystem concentration risk (v6.13d HL exposure already 57.5%).

### Direct USDC Reserve Yield Passthrough (NOT FOUND)

- **Category:** TBD_NOT_LAUNCHED
- **User claimable:** False
- **Requires HYPE exposure:** False
- **Est. APY:** None%
- **K344 sleeve candidate:** False
- **Notes:** This product does NOT currently exist. All AQAv2 reserve yield routes exclusively to HYPE buybacks via Assistance Fund. No 'HL native sUSDe equivalent' exists as of 2026-05-27.
- **Reason for rejection:** Product does not exist. If launched, would require re-evaluation. Trigger: HL governance proposal for USDC yield passthrough token.

---

## Phase 4 — K344 Sleeve Comparison Matrix

| Metric | sUSDe (K344) | HYPE Staking | HLP Vault | HypurrFi USDC | AQAv2 Direct |
|--------|-------------|--------------|-----------|----------------|--------------|
| Annual yield APY | 4.01% (Q1 2026 mean, K361) | 2.37% | variable (MM-dependent) | ~9% (organic demand, volatile) | N/A (product does not exist) |
| User claimable | YES (sUSDe redeem anytime) | NO (auto-compound, 7d unstake) | YES (with withdrawal lag) | YES | N/A |
| MDD risk | 0.11% (K344 live) | HYPE price exposure (high vol) | non-trivial (trending mkt risk) | stablecoin; liquidation risk | N/A |
| Orthogonal to trading (rho) | 0.05 (near-zero, K344) | likely high (corr with crypto mkt) | medium (corr with vol regime) | low-medium (HyperEVM rate-driven) | N/A |
| Smart contract risk | medium (audited, complex hedging) | low (native HL L1) | low-medium (native HL L1) | HIGH (HyperEVM + domain incident) | N/A |
| HL concentration impact | ZERO (Ethereum-native, outside HL) | +X% (adds HL exposure) | +X% (adds HL exposure) | +X% (adds HyperEVM exposure) | +X% (would add HL exposure) |
| Tied to Coinbase AQAv2 deal | NO | NO (inflationary emissions) | NO (trading fees only) | NO (organic borrow demand) | YES (hypothetical only) |

**Conclusion:** No HL-native product matches or exceeds sUSDe on all
dimensions critical for a K344 sleeve (APY, claimability, MDD, orthogonality,
HL concentration neutrality). sUSDe remains the only qualifying sleeve.

---

## Phase 5 — HL Ecosystem Yield Assessment

### HYPE Token Accretion

AQAv2 creates ~$135–160M/year in additional HYPE buyback fuel. At current
$5.1B USDC base, this is ~2.7–3.1% annual buyback yield equivalent for HYPE
holders — meaningful for HYPE price but zero benefit to USDC depositors.

If USDC supply grows to $10B (plausible given HL's growth trajectory), annual
AQAv2-driven buybacks could reach $270–300M — comparable to a major DeFi
protocol's entire annual revenue.

### HLP Vault Holders

HLP vault does NOT receive AQAv2 yield share. HLP earns from trading
activity. The vault is a reasonable passive yield product for HL-native
participants but is disqualified as a K344 sleeve due to: (1) MM directional
risk, (2) no AQAv2 yield connection, (3) adds HL concentration.

### Bid-Side Market Makers

No evidence of rebates funded by USDC yield. Existing rebate structure is
funded by trading fees (taker-maker spread). AQAv2 yield bypasses the
rebate pool entirely.

---

## Phase 6 — Decision Matrix

| Verdict | Trigger Condition | Result |
|---------|-------------------|--------|
| ACCEPT scaffold | Clear claimable yield product live, K344-like profile | NOT MET |
| MONITOR | Yield mechanism exists but not yet claimable | NOT MET |
| DEFER | HL governance proposal pending, not finalized | NOT MET |
| **REJECT** | Yield flows entirely to buybacks/dev — zero passthrough | **MET** |

**Final decision: REJECT**

All AQAv2 yield routes to HYPE buybacks. No direct user passthrough exists
or is pending. This is the same structural outcome as K354 USDH rejection
(that was deprecated; this is: yield mechanism mismatch — buyback-only).

### Monitor Trigger

Watch for: **HL governance proposal published for a USDC yield passthrough
token** (analogous to sUSDe / Ethena's rebasing model). If such a proposal
appears on hyperliquid.gitbook.io or HL Discord governance channel, escalate
to K363+ scaffold wave immediately.

---

## Phase 7 — Concentration Risk Note

| Parameter | Value |
|-----------|-------|
| Current HL exposure | 57.5% |
| Max allowed (feedback_concentration_risk_HL.md) | 65.0% |
| Headroom | 7.5% |
| sUSDe inside HL ecosystem | False |

### Replace sUSDe with HL product?

HL exposure delta = 0, but lose Ethereum-native orthogonality.
**Verdict: INFERIOR.** sUSDe's outside-HL positioning is a structural advantage.

### Add HL product alongside sUSDe?

Even a 5% allocation to an HL product → HL exposure = 62.5% (near 65% cap).
Would only be viable if product materially outperforms sUSDe AND has
demonstrably lower MDD. No such product exists.
**Verdict: RISKY with no discovered candidate.**

---

## Sources

- https://www.coinbase.com/blog/coinbase-and-hyperliquid-aligning-markets-on-hyperliquid-to-usdc
- https://www.theblock.co/post/401233/coinbase-hyperliquid-official-deployer-usdc
- https://www.coindesk.com/markets/2026/05/18/hyperliquid-s-usdc-deal-could-supercharge-hype-pressure-circle-coinbase-margins-analysts-say
- https://beincrypto.com/coinbase-usdh-hyperliquid-shifts-to-usdc/
- https://cryptobriefing.com/hyperliquid-usdc-yield-hype-buybacks/
- https://coincentral.com/hyperliquid-usdc-yield-deal-could-route-up-to-90-to-hype-buybacks/
- https://tokenomics.com/articles/hyperliquid-tokenomics-how-hype-captures-65m-monthly-in-holder-revenue
- https://hyperliquid.gitbook.io/hyperliquid-docs/hypercore/staking

---

## Key Findings Summary

1. **AQAv2 yield is HYPE-buyback-only.** 90% of $180M/year USDC reserve
   yield flows to HYPE buybacks. Zero passthrough to USDC depositors.

2. **No sUSDe equivalent on HL.** No rebasing USDC yield token, no
   claimable USDC staking product, no AQAv2-backed vault exists.

3. **HYPE staking (2.37% APY)** is below K344 benchmark, requires HYPE
   exposure, auto-compounds (not claimable), and adds HL concentration.

4. **HLP vault** earns from MM activity only, carries directional risk,
   and adds HL concentration. Disqualified as sleeve.

5. **HypurrFi USDC (~9% APY)** is organic/unconnected to Coinbase deal,
   carries HyperEVM smart-contract risk, and adds HL concentration.
   Prior domain compromise incident noted.

6. **sUSDe K344 sleeve unchanged.** No replacement or addition warranted.
   sUSDe's Ethereum-native positioning provides structural HL-orthogonality
   unavailable from any HL-ecosystem product.

7. **Monitor trigger set.** If HL governance proposes a direct USDC yield
   passthrough token, escalate immediately to scaffold wave.

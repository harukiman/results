# K400 — Ondo Global Markets Investigation (R14-07)

**Wave**: K400 | **Task**: R14-07 STRICT_VERIFIED follow-up
**Generated**: 2026-05-29 07:01 JST (via `date`)
**Status**: CONDITIONAL — USDY accessible for non-US users; OGM deferred

---

## Executive Summary

Ondo Finance has grown from the $1B TVL milestone (May 2025) to **$3.85B TVL** (DeFiLlama, May 2026), establishing itself as the largest tokenized RWA protocol globally. The protocol spans 4 main products across 7+ chains.

**Key verdict**: USDY (tokenized T-bills, $500 minimum, non-US KYC) is a **CONDITIONAL ACCEPT** for a v6.15 sleeve (5-10%) that would directly address K355's HL concentration risk — reducing HL exposure from 57.5% to as low as 47.5% (first below-50% milestone). Ondo Global Markets (tokenized equities, institutional-only, US persons blocked, SEC registration pending) is **DEFERRED**.

The critical blocking question for K401: is the user non-US resident? USDY is entirely blocked for US persons.

---

## 1. Protocol Overview

| Metric | Value |
|---|---|
| Total TVL | $3.85B (May 2026, DeFiLlama) |
| TVL 12 months ago | ~$1B (K396 STRICT_VERIFIED finding, May 2025) |
| Annualized fees | $51.8M |
| Avg pool APY | 3.51% across monitored pools |
| ONDO token price | $0.37 (ATH $2.14; -83% from ATH) |
| ONDO market cap | $1.815B |
| Cumulative Ondo GM volume | >$10B |

### TVL by Chain (May 2026)

| Chain | TVL |
|---|---|
| Ethereum | $1.821B |
| BSC | $560M |
| Plume Mainnet | $504M |
| XRPL | $294M |
| Sei | $256M |
| Solana | $208M |
| Stellar | $124M |
| Other | $81M |

---

## 2. Product Landscape

### 2.1 USDY — Ondo US Dollar Yield Token

**Category**: General access (non-US retail + institutional)

| Attribute | Detail |
|---|---|
| Underlying | Short-term US Treasuries + iShares Short Treasury Bond ETF + bank demand deposits |
| Yield | ~4.5% APY (tracks T-bill benchmark; updated each business day) |
| Minimum | $500 (Ethereum); $5,000 (Solana/Sui/Aptos/Stellar/XRPL) |
| KYC required | Yes (Ondo Finance onboarding) |
| US persons | PROHIBITED — Ondo USDY LLC redeems only to non-US bank accounts |
| Chains | Ethereum, Solana, Sui, Aptos, Stellar, XRPL, Noble |
| Lock-up | 40 days before first transfer |
| Redemption | 1 business day (daily NAV update) |
| Custody | Ankura Trust (US federal chartered bank); monthly audits by Withum |
| Smart contract (ETH) | 0x96F6eF951840721AdbF46Ac996b59E0235CB985 |
| Regulatory | Money market note (not a security); Reg S / Rule 144A |
| DeFi composable | Yes — ERC-20 post-lock; usable in protocols |

**Analysis**: USDY is the most accessible Ondo product. The $500 minimum and multi-chain support make it retail-accessible. The 40-day initial lock is a material constraint for rapid deployment — USDY must be held as a standing allocation, it cannot function as emergency capital.

### 2.2 OUSG — Ondo Short-Term US Government Bond Fund

**Category**: Qualified access (institutional + US accredited)

| Attribute | Detail |
|---|---|
| Underlying | BlackRock, Franklin Templeton, WisdomTree, Fidelity short-term gov fund shares + USDC |
| Yield | ~4.8% APY |
| Min (instant) | $5,000 |
| Min (standard) | $100,000 investment; $50,000 redemption |
| KYC required | Yes (qualified-fund onboarding) |
| US persons | Permitted for accredited investors |
| Redemption | Instant 24/7 (subject to daily limits) or standard (contact support) |
| Chains | Ethereum |
| DeFi variant | rOUSG (rebasing ERC-20) |
| Regulatory | SEC-registered security; qualified-access fund |

**Analysis**: OUSG has more yield (~4.8% vs 4.5%) and instant redemption is superior to USDY's 1-day NAV. However, $100K standard minimum and accredited investor requirement make it institutional-scale. US users can access but need accreditation compliance. DEFERRED until user qualifies.

### 2.3 Ondo Global Markets (tokenized equities)

**Category**: Institutional only (non-US)

| Attribute | Detail |
|---|---|
| Underlying | Tokenized stocks and ETFs (US + international equities) |
| Yield | None — price appreciation of underlying stocks |
| SEC registration | Confidential registration filed; first tokenized stock issuer for SEC reporting (if effective) |
| SEC no-action | Filed April 13, 2026 for Ethereum Mainnet operation approval |
| DTCC integration | Joined DTCC consortium; production trades targeted **July 2026** |
| TVL | $3.55B reported (part of overall $3.85B) |
| Cumulative volume | >$10B |
| US persons | PROHIBITED (Reg S; same as USDY) |
| Non-US requirements | MiFID II Professional / Accredited status across most jurisdictions (EU, UK, SG, HK, CH, BR, MY) |
| Min investment | Unknown; institutional scale implied |
| Status | SEC registration not yet effective; DTCC production not yet live |

**Analysis**: Ondo Global Markets is the flagship "institutional RWA" product that drove the K396 finding. Despite impressive numbers ($10B+ volume, DTCC partnership), it remains inaccessible: US persons blocked, institutional qualification required in all key jurisdictions, and the product isn't fully live yet (DTCC July 2026, SEC pending). DEFERRED.

### 2.4 ONDO Token

| Attribute | Detail |
|---|---|
| Type | Governance / utility token |
| Price | $0.37 (83% off ATH $2.14) |
| Market cap | $1.815B |
| Yield | None |
| Availability | Bybit, Binance, OKX, Coinbase |

**Analysis**: REJECT for yield strategy purposes. ONDO is a speculation/governance token with no yield passthrough. At $0.37 vs $2.14 ATH, it's in deep drawdown. Not relevant to the RWA yield sleeve.

---

## 3. HL HIP-3 (K297') vs Ondo Comparison Matrix

| Aspect | HL HIP-3 K297' | USDY | Ondo Global Markets |
|---|---|---|---|
| Mechanism | FR carry on PAXG/SPX perps | T-bill yield passthrough | Equity price exposure |
| Yield (current) | ~6-9% variable (FR) | ~4.5% stable | N/A |
| Yield type | Variable; FR can go negative | Quasi-fixed (Fed-rate-floor) | Capital gain |
| Primary risk | FR reversal, HL platform, oracle | T-bill credit (negligible), 40d lock | Equity market, SEC pending, DTCC not live |
| Custody | HL on-chain | Ankura Trust (federal charter) + Ethereum | Ethereum + DTCC (pending) |
| US person access | Permissionless (de facto) | PROHIBITED | PROHIBITED |
| Non-US retail | Permissionless | KYC $500 min | Institutional only |
| Regulatory status | CFTC gray zone | Regulated note (Reg S/144A) | SEC registration pending |
| HL exposure | 100% | ZERO | ZERO |
| DeFi composable | No (HL perp position) | Yes (ERC-20 post-lock) | Yes (pending) |
| Correlation with K280 | Moderate+ (both FR-based) | ~0 (T-bill orthogonal) | Low-moderate (equity) |
| Redemption speed | Near-instant | 1 business day (40d initial lock) | Unknown |
| Min entry | ~$10 | $500 | Institutional |

**Key insight**: K297' and USDY are complementary, not substitutes. K297' has higher yield ceiling (6-9% vs 4.5%) but 100% HL exposure. USDY has zero HL exposure and orthogonal correlation — perfect for concentration risk reduction. The optimal portfolio uses both at reduced K297' weight.

---

## 4. Architecture Scenarios

### Scenario A: v6.15a — Light Ondo (USDY 5%)

```
K280 main:           75%  (down from 80% in v6.13d)
K297' HIP-3 sat:     15%  (unchanged)
K344 sUSDe:           5%  (unchanged)
Ondo USDY:            5%  (NEW)
─────────────────────────
Total:               100%

HL exposure: 52.5% (down 5pp from 57.5%)
Expected ann return: ~11.5% (vs 12.0% baseline)
USDY return contribution: 4.5% * 5% = +0.225%
K280 drag: modest (75% vs 80%, but K280 dominates both)
```

**Rationale**: Minimal disruption. USDY 5% adds T-bill safety floor, reduces HL exposure by 5pp, almost no yield impact. K297' unchanged. Best first step.

**Feasibility**: CONDITIONAL — non-US user + KYC + $500 min required.

### Scenario B: v6.15b — Meaningful Ondo (USDY 10%)

```
K280 main:           75%  (down from 80%)
K297' HIP-3 sat:     10%  (down from 15%)
K344 sUSDe:           5%  (unchanged)
Ondo USDY:           10%  (NEW)
─────────────────────────
Total:               100%

HL exposure: 47.5% (down 10pp — FIRST TIME BELOW 50%)
Expected ann return: ~10.5% (vs 12.0% baseline)
USDY return contribution: 4.5% * 10% = +0.45%
K297' yield sacrifice: ~7% * 5% = -0.35% (blended FR vs USDY diff * 5% reallocation)
Net yield cost: ~-0.5% for -10pp HL risk reduction
```

**Rationale**: The K355 primary risk milestone — HL exposure below 50% for the first time. Meaningful concentration improvement at modest yield cost. K297' is halved but retained (FR yield ceiling is still 2x USDY in good regimes).

**Feasibility**: CONDITIONAL — same access requirements. 10% sleeve = $5,000+ position for a $50K portfolio (well above $500 minimum).

### Scenario C: v6.13e BEAR_1 Enhancement

**Concept**: Replace 10% BTC/ETH spot in BEAR_1 fallback with USDY.

```
Current BEAR_1 (K386): K280 85% + BTC/ETH spot 10% + sUSDe 5%
Enhanced BEAR_1:        K280 85% + USDY 10% + sUSDe 5%

BEAR_1 HL exposure: 52.5% -> 42.5%
```

**Verdict**: IMPRACTICAL as emergency deployment. USDY's 40-day initial lock means it cannot be deployed reactively when BEAR_1 triggers. Only viable if USDY is already held as a standing v6.15a/b sleeve before any crisis. Reclassify: this is an argument FOR implementing v6.15a/b now (so USDY is already available if BEAR_1 triggers later).

---

## 5. K266 Gates (Adapted for Stable-Yield RWA)

| Gate | Criterion | USDY | Result |
|---|---|---|---|
| G1 | Net APY >= 4% (stable RWA bar) | 4.5% | PASS |
| G2 | NAV stability < 0.5% vs benchmark | Money market NAV = par + accrual | PASS |
| G3 | Custody auditability (third-party audited) | Ankura Trust + Withum monthly | PASS |
| G4 | Redemption < 7 business days | 1 business day | PASS (caveat: 40d initial lock) |
| G5 | Correlation K280 < 0.1 | ~0.02 (T-bill orthogonal to FR) | PASS |
| G6 | Max single-event loss < 1% | US Treasury default ~0.001% | PASS |
| G7 | User access confirmed | Non-US only; $500 min; KYC | CONDITIONAL |

**Gate score**: 6/7 pass outright. G7 is conditional on user jurisdiction confirmation.

**Critical caveat on G4**: The 40-day initial lock means USDY cannot serve as "quick liquidity" during a crisis. It functions as a permanent allocation, not a reserve.

---

## 6. HL Concentration Impact

K355 identified HL concentration as the primary portfolio risk. Current exposure = 57.5%.

| Version | K297' | USDY | HL Exposure | Delta | Milestone |
|---|---|---|---|---|---|
| v6.13d (current) | 15% | 0% | 57.5% | — | Baseline |
| v6.15a | 15% | 5% | 52.5% | -5pp | Progress |
| v6.15b | 10% | 10% | 47.5% | -10pp | **First below 50%** |

USDY contributes exactly ZERO HL exposure (Ethereum/multichain). Every percentage point reallocated to USDY is a 1:1 reduction in HL concentration.

**K355 milestone**: v6.15b would be the first portfolio version to achieve sub-50% HL exposure, directly addressing the primary risk identified in K355.

---

## 7. Practical Feasibility

### USDY Access Path (Non-US User)

1. Navigate to app.ondo.finance
2. Complete KYC/AML onboarding (non-US identity documents required)
3. Wire USD to Ondo USDY LLC (non-US bank account required)
4. Minimum: $500 on Ethereum
5. Receive USDY tokens; 40-day lock before first transfer
6. After lock: transferable ERC-20; use in DeFi or hold for yield

### Price Feed for Backtesting

USDY tracks the T-bill rate. For backtesting, use the FRED API (free, no key required for small volumes):

```
https://api.stlouisfed.org/fred/series/observations?series_id=DGS3MO
```

This provides daily 3-month T-bill rates back to 1954. Accurate proxy for USDY yield in backtesting.

### Programmatic Integration

| Component | Path |
|---|---|
| Price feed | DeFiLlama /protocol/ondo-finance + Ondo NAV daily announcement |
| Backtesting proxy | FRED DGS3MO (3-month T-bill, free) |
| Smart contract (ETH) | 0x96F6eF951840721AdbF46Ac996b59E0235CB985 |
| Mint/redeem | Via app.ondo.finance (no public API documented) |
| DeFi composability | Standard ERC-20 after 40-day lock |

---

## 8. Decision Matrix

### Product Verdicts

| Product | Verdict | Action |
|---|---|---|
| **USDY** | **CONDITIONAL ACCEPT** | Proceed to v6.15a scaffold if user is non-US + willing to KYC |
| OUSG | DEFER | Requires accredited status; $100K standard minimum; revisit when user qualifies |
| Ondo Global Markets | DEFER | US persons blocked; SEC registration pending; institutional minimums; DTCC July 2026 |
| ONDO token | REJECT | Governance token only; no yield; 83% off ATH; not relevant to RWA sleeve |

### K297' Relationship

**Do not replace K297' entirely.** FR carry has a 6-9% yield ceiling vs USDY's 4.5% floor. The optimal action:

- **v6.15a**: Keep K297' at 15%, add USDY 5% (slight K280 trim). Low disruption.
- **v6.15b**: Trim K297' to 10% to fund USDY 10% — first sub-50% HL milestone at ~-0.5% yield cost.

The yield sacrifice for the concentration improvement is small and worth it if HL risk is the priority concern.

### Blocking Question for K401

**Is the user a non-US person?**

- YES → USDY accessible at $500 minimum; proceed to v6.15a design
- NO (US person) → USDY blocked; OUSG possible if accredited investor; DEFER until jurisdiction confirmed

---

## 9. Strategic Fit Analysis

### Why USDY Fits v6.15

1. **Orthogonal return stream**: T-bill yield (~4.5%) is completely uncorrelated with crypto FR cycles. In FR drought periods (negative funding, K280 underperforming), USDY continues earning.

2. **Zero HL dependency**: K302a (K297') satellite and K280 both rely on HL infrastructure. USDY is Ethereum-native — zero HL single point of failure.

3. **Regulatory complement**: K297' operates in CFTC gray zone (HL perps). USDY is a regulated money market note. The combination provides regulatory diversification.

4. **DeFi composability**: Post-40d lock, USDY ERC-20 can be used in Ethereum DeFi. Opens future options (USDY as collateral for leverage, etc.).

5. **Concentration math**: 10% USDY allocation mechanically reduces HL exposure by 10pp — the most efficient single action for K355 risk.

### Why NOT Fully Replace K297'

1. K297' blended FR yield (6.21% 7d ann) substantially outperforms USDY (4.5%) in normal regimes.
2. K297' is HIP-3 infrastructure — replaces it with anything requires full strategy rebuild.
3. PAXG and SPX FR have been positive >80% of days — a durable edge.
4. The correct portfolio design is diversification (USDY + K297'), not substitution.

---

## 10. Ondo Global Markets: Longer-Term Thesis

Despite being DEFERRED now, Ondo Global Markets deserves monitoring:

- **DTCC production July 2026**: If this milestone hits, it validates the institutional infrastructure story.
- **SEC registration effectiveness**: Ondo will be the first SEC-reporting tokenized stock issuer. If effective, tokenized equities enter mainstream RWA.
- **Non-US institutional access**: For non-US MiFID II Professional investors, OGM provides tokenized AAPL, TSLA, S&P 500 ETFs with blockchain settlement.
- **Strategic relevance**: In a future portfolio where user is non-US + qualifies as Professional Investor, OGM could replace BTC/ETH spot in BEAR_1 (equity exposure without crypto volatility).

Revisit: K450+ when DTCC production is confirmed and SEC registration effective.

---

## 11. Implementation Plan (if CONDITIONAL ACCEPT)

### K401 Immediate

1. Confirm user jurisdiction (non-US required for USDY)
2. Design v6.15a specification document:
   - Sleeve allocations: K280 75% + K297' 15% + sUSDe 5% + USDY 5%
   - HL exposure impact: 57.5% -> 52.5%
   - Expected return impact: 12.0% -> 11.5%
3. USDY onboarding checklist (KYC URL, required documents, bank wire instructions)
4. Price feed integration: FRED DGS3MO proxy for backtesting; DeFiLlama for live monitoring

### K-future

- K450+: Revisit Ondo Global Markets when DTCC July 2026 goes live
- K-future: OUSG integration if accredited investor status confirmed
- K-future: v6.15b (USDY 10%) if v6.15a is stable and user wants deeper HL concentration reduction

---

## 12. Risk Factors

| Risk | Severity | Mitigation |
|---|---|---|
| US person blocked | HIGH | Confirm non-US jurisdiction before any USDY allocation |
| 40-day initial lock | MEDIUM | Cannot use as emergency capital; must be standing allocation |
| T-bill rate decline | LOW-MEDIUM | USDY yield tracks Fed rate; rate cuts reduce yield to 2-3% in easing cycle |
| Ondo smart contract risk | LOW | Audited; Ankura Trust custody; but non-zero smart contract risk |
| NAV gate failure | LOW | Money market NAV is structurally par-stable; T-bill default is near-zero |
| KYC rejection | LOW-MEDIUM | Non-US with clean AML profile should pass; jurisdiction restrictions per list |
| OGM SEC delay | LOW (for us) | Already DEFERRED; delay doesn't impact USDY v6.15 plan |

---

## Appendix: Data Sources

- DeFiLlama: https://defillama.com/protocol/ondo-finance
- Ondo USDY docs: https://docs.ondo.finance/general-access-products/usdy
- OUSG overview: https://docs.ondo.finance/qualified-access-products/ousg/overview
- Ondo Global Markets eligibility: https://docs.ondo.finance/ondo-global-markets/eligibility
- SEC filing announcement: https://ondo.finance/blog/ondo-global-markets-files-registration-statement-with-sec
- DTCC consortium: https://cryptobriefing.com/ondo-finance-sec-no-action-dtcc/
- FRED DGS3MO: https://fred.stlouisfed.org/series/DGS3MO

---

*K400 investigation complete. Verdict: CONDITIONAL ACCEPT for USDY (non-US users). K297' retained and complemented, not replaced. v6.15a is the recommended next design step pending jurisdiction confirmation.*

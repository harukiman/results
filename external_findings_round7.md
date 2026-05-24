# External Findings Round 7 — Summary
**Generated:** 2026-05-25 JST  
**Total Findings:** 20  
**Actionable (Y):** 16 | **Informational (N):** 4  
**Cumulative total (R1-R7):** ~162 entries  

---

## Executive Summary

Round 7 uncovered a critical theme: **Hyperliquid's structural dominance is accompanied by structural risk accumulation**. The JELLY (March 2025) and FARTCOIN (April 2026) attacks confirm a repeating attack pattern against HLP/ADL. Meanwhile, BitMEX's definitive data shows passive FR arb has compressed to sub-Treasury Bill yields for major pairs — reinforcing K196's REVERSE carry differentiation as the right strategic direction. The academic literature (5 new papers) converges on OU+Jump models for FR dynamics, GARCH regime filters, and CEX→DEX information flow dominance.

---

## Top 3 Actionable Findings for K198+

### #1 — FARTCOIN/JELLY Attack Pattern: HLP Health Monitoring (R7-05, R7-06, R7-07)
**Urgency: HIGH**

Two confirmed attacks (JELLY Mar 2025, FARTCOIN Apr 2026) exploit the same vector: oversized positions on illiquid HL tokens → forced self-liquidation → HLP absorbs bad position → ADL forces profitable opposing positions closed. K196's HL-short delta-neutral positions are NOT directly at risk of ADL (they are not the "winning long" side), but HLP fund depletion increases ADL trigger probability, which can force-close K196's profitable positions.

**Immediate actions for K197+:**
- Add HLP balance + Assistance Fund balance as weekly monitoring KPIs
- If HLP balance drops >20% in 7 days, auto-reduce HL exposure by 50%
- Add OI/MarketCap ratio filter to exclude potential manipulation targets (reject if HL OI > 5% of token's spot market cap)

### #2 — OU+Jump FR Predictor: Replace Pure OU in K196 Model (R7-02, R7-13)
**Urgency: HIGH**

Two independent papers (arXiv 2605.06405, SSRN 5290137) confirm that OU+Jump models substantially outperform pure Gaussian OU for HL funding rates. Empirically measured mean-reversion half-life: **2–6 hours** on Hyperliquid. Jump events create asymmetric entry opportunities: post-jump the rate overshoots and reverts rapidly, enabling high-conviction short-window entries.

**Immediate actions for K197:**
- Implement Euler-Maruyama jump detection layer on top of existing OU parameter estimation
- Use rolling 72h window for OU+Jump parameter updates (captures regime shifts quickly)
- Add jump-event trigger: when FR > μ + 3σ (OU baseline), enter opposing position within 30 min

### #3 — BitMEX/Q3 2025 Data: Reconfirm HL ETH as Core Pair, Reduce BTC Weight (R7-09, R7-10)
**Urgency: MEDIUM-HIGH**

BitMEX Q3 2025 report definitively quantifies: HL ETH FR std dev = 0.0131% vs BitMEX 0.0045% (2.9x). HL ETH max FR = 0.0752% vs BitMEX 0.0276% (2.7x). ETH shows 35% higher beta than BTC on HL. For K197 universe design: ETH captures more FR volatility premium on HL than BTC, while major pair arb has compressed to ~4% APR (sub-T-bill). Long-tail perps retain 20-60% APR.

**Immediate actions for K197:**
- Increase ETH weight relative to BTC in HL-side positions (suggested ratio: ETH 35%, BTC 20%, mid-cap 45%)
- Add Ethena TVL monitoring: TVL rapid decline → FR spike signal → early entry trigger
- Implement 20bps minimum spread filter (per MDPI study: only 40% of 20bps+ opportunities profitable after costs; below 20bps is near-zero EV)

---

## Full Findings Index

| ID | Title (short) | Source | Actionable |
|----|--------------|--------|------------|
| R7-01 | Designing FR for Perps — BSDE Framework | arXiv q-fin.MF | Y |
| R7-02 | Funding-Aware MM for Perp DEXs — OU+Jump | arXiv q-fin.TR | Y |
| R7-03 | HL vs CEX Perp Arb: True Cost Analysis 2026 | Neural Arb Blog | Y |
| R7-04 | HLP Vault Anatomy: Structure + Counterparty Risk | 0xian Substack | Y |
| R7-05 | Hyperliquid ADL First Activation (Oct 2025) | WuBlockchain Substack | Y |
| R7-06 | JELLY Attack: Oracle Manipulation Full Anatomy | OAK Research | Y |
| R7-07 | FARTCOIN Suicide-Liquidation Attack (Apr 2026) | Exmon Academy | Y |
| R7-08 | HL Reverse Engineering: Oracle Key/Broadcaster Risk | can.ac Blog | N |
| R7-09 | BitMEX State of Crypto Perps 2025: Post-Yield Era | BitMEX Blog | Y |
| R7-10 | BitMEX Q3 2025: HL vs CEX FR Structure Data | BitMEX Blog | Y |
| R7-11 | Two-Tiered FR Markets Structure (MDPI, 2026) | MDPI Mathematics | Y |
| R7-12 | Temporal Dynamics: CEX-DEX GARCH/Granger (MDPI, 2026) | MDPI IJFS | Y |
| R7-13 | Stochastic FR Modeling with Jumps (SSRN 2025) | SSRN | Y |
| R7-14 | Pendle Boros: Fixed-Yield Cross-Exchange FR Swap | Pendle/Boros Medium | N |
| R7-15 | HL Portfolio Margin: Spot-Perp Offset (Dec 2025) | Hyperliquid Docs | Y |
| R7-16 | Explainable Microstructure Patterns: CatBoost+SHAP | arXiv q-fin.TR | Y |
| R7-17 | Crypto Quant Index X (Feb 2026): FYpGE Metric | 1Token Blog | Y |
| R7-18 | Hyperliquid S1 2025: 73% DEX Share, $7.5B OI | OAK Research | Y |
| R7-19 | Ethena $7.83B Liquidity Sets FR Spike Ceiling | Ethena Docs | Y |
| R7-20 | CryptoFundingArb: 6-Exchange FR Scanner (OSS) | GitHub | N |

---

## Regime-Conditional Weakness of K196: Findings Relevance

K196's known weakness is regime-conditional drawdowns (bear/low-FR environments). Key findings addressing this:

- **R7-09 (BitMEX Post-Yield):** Confirms that 2025 saw first sustained sub-floor FR environment during a bull cycle — K196 needs a regime OFF-switch when Ethena TVL rapidly increases (crowded arb)
- **R7-10 (Q3 BitMEX):** 92% of K196 periods are positive FR — but the 8% negative-rate periods are when drawdowns concentrate. GARCH filter (R7-12) can help identify and reduce exposure in these windows
- **R7-13 (OU+Jump):** Jump detection enables proactive position reduction before cascading FR reversals

## Arb Saturation Status

Confirmed: major pair (BTC/ETH) passive FR arb compressed to 3-12% net APR. HL mid-cap/long-tail perps retain 20-60% APR. The "saturation ceiling" is enforced by Ethena's $7.83B deployable capital (R7-19). K196's differentiation (REVERSE carry on opposite-sign venues) is correctly positioned outside the crowded trade.

---

*Files: external_findings_round7.json · external_findings_round7.html · external_findings_round7.md*  
*Previous rounds: R1-R6 (142 entries), R7 (+20) = 162 cumulative*

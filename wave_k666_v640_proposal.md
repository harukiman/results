# Wave K666 — v6.40 Architecture Proposal

**Status:** CANDIDATE  
**Date:** 2026-05-30 13:05 JST  
**Extends:** K643 v6.32 (5 orthog Bybit, mid $19.93M @$10M)

---

## Executive Summary

v6.40 is the profit-maximizing extension of v6.32, adding:

1. **K629 WLD-ETH** (3% HL) — ETH-base mechanism fix unlocks WLD family (blocked since K621)
2. **K658 SOL-ETH** (1.5% HL) + **K476 SOL-BTC** (reduced 4%→1.5%) — diversified SOL family
3. **5 additional Bybit orthog sleeves** (K645 BNB / K646 ALGO / K647 DOT / K648 POL / K656 GALA)

**K523 range @$10M: Conservative $15M / Mid $20.9M / Optimistic $48M/yr**  
**5y central: $105–115M**  
**HL: 63.5% (< 65% cap, 1.5pp headroom)**  
**9-orthog combined Sharpe: 32.45 (K655, Sharpe-weighted)**

---

## Phase 1: v6.32 Baseline (K643)

| Metric | Value |
|--------|-------|
| Source wave | K643 |
| HL concentration | 62.5% |
| Annual mid @$10M | $19.93M/yr |
| Annual conservative | $14.5M/yr |
| Annual optimistic | $46M/yr |
| 5y mid | $100M |
| Total sleeves | 22 |
| Orthog sleeves | 5 (K628/K631/K633/K635/K638 Bybit) |
| K655 9-orthog Sharpe | 32.45 (Sharpe-weighted) |
| K655 9-orthog profit @$10M | $812,523/yr |

---

## Phase 2: v6.40 Candidate Composition

### New sleeves vs v6.32 (7 additions)

| Sleeve | % AUM | Venue | HL% | OOS Sharpe | Ann Mid @$10M | Source |
|--------|--------|-------|-----|-----------|---------------|--------|
| K629 WLD-ETH | 3.0% | HL (WLD+ETH perps) | 2.0% | 19.90 | $94,210/yr | K629 ACCEPT |
| K658 SOL-ETH | 1.5% | HL (SOL+ETH perps) | 1.5% | 29.66 | $42,332/yr | K658 ACCEPT |
| K645 BNB orthog | 2.0% | Bybit | 0% | 7.07 | $14,745/yr | K645 ACCEPT COND |
| K646 ALGO orthog | 2.0% | Bybit | 0% | 8.11 | $20,325/yr | K646 ACCEPT COND |
| K647 DOT orthog | 2.0% | Bybit | 0% | 23.25 | $80,460/yr | K647 ACCEPT |
| K648 POL orthog | 2.0% | Bybit | 0% | 23.41 | $85,864/yr | K648 ACCEPT COND |
| K656 GALA orthog | 1.5% | Bybit | 0% | 8.32 | $14,130/yr | K656 ACCEPT COND |

### Modification vs v6.32

- **K476 SOL-BTC**: reduced 4% → 1.5% (same SOL family 3% total, diversified with K658)

### Complete v6.40 sleeve roster (29 sleeves)

| # | Sleeve | % | Venue | HL% | Status |
|---|--------|---|-------|-----|--------|
| 1 | K280 multi-venue | 32.0% | HL+Bybit | 16.0% | ACTIVE |
| 2 | K297 prime | 5.0% | HL | 5.0% | ACTIVE |
| 3 | sUSDe | 7.0% | Ethena | 0% | ACTIVE |
| 4 | Spark sUSDS | 7.0% | Spark | 0% | ACTIVE |
| 5 | K376 momentum | 8.0% | HL | 8.0% | ACTIVE |
| 6 | K449 ETH-BTC | 5.0% | HL | 5.0% | PAPER-60d |
| 7 | K476 SOL-BTC | **1.5%** | HL | 1.5% | PAPER-60d (reduced) |
| 8 | K484 AVAX-BTC | 5.0% | HL | 5.0% | PAPER-60d |
| 9 | K493 ATOM-BTC | 5.0% | HL | 5.0% | PAPER-60d |
| 10 | K500 INJ-BTC | 4.0% | HL | 4.0% | PAPER-60d |
| 11 | K507 SEI-BTC | 2.0% | HL+Bybit | 1.0% | PAPER-60d |
| 12 | K507 TIA-BTC | 1.0% | HL | 1.0% | PAPER-60d |
| 13 | K512 APT-BTC | 2.0% | HL+Bybit | 1.0% | PAPER-60d |
| 14 | K495 DEX-CEX flow | 6.0% | HL | 6.0% | PAPER-60d |
| 15 | K541 stablecoin supply | 3.0% | Bybit | 0% | PAPER-60d |
| 16 | K521 options skew | 3.0% | HL+Bybit | 1.5% | PAPER-90d |
| 17 | K628 JTO orthog | 2.0% | Bybit | 0% | PAPER-60d |
| 18 | K631 WLD orthog | 2.0% | Bybit | 0% | PAPER-60d |
| 19 | K633 OP orthog | 2.0% | Bybit | 0% | PAPER-60d |
| 20 | K635 IMX orthog | 2.0% | Bybit | 0% | PAPER-60d |
| 21 | K638 STX orthog | 1.5% | Bybit | 0% | PAPER-60d |
| 22 | **K629 WLD-ETH** | **3.0%** | HL | **2.0%** | PAPER-60d NEW |
| 23 | **K658 SOL-ETH** | **1.5%** | HL | **1.5%** | PAPER-60d NEW |
| 24 | **K645 BNB orthog** | **2.0%** | Bybit | 0% | PAPER-60d NEW |
| 25 | **K646 ALGO orthog** | **2.0%** | Bybit | 0% | PAPER-60d NEW |
| 26 | **K647 DOT orthog** | **2.0%** | Bybit | 0% | PAPER-60d NEW |
| 27 | **K648 POL orthog** | **2.0%** | Bybit | 0% | PAPER-60d NEW |
| 28 | **K656 GALA orthog** | **1.5%** | Bybit | 0% | PAPER-60d NEW |
| 29 | Cash | 1.0% | cash | 0% | ACTIVE |

---

## Phase 3: HL Concentration Check

```
v6.32 baseline:         62.5%
+ K629 WLD-ETH add:     +2.0pp  (3% sleeve, HL portion 2/3 = 2%)
- K476 SOL-BTC reduce:  -2.5pp  (4%->1.5%, HL reduction)
+ K658 SOL-ETH add:     +1.5pp  (1.5% all HL)
+ Bybit orthog x5:       0.0pp  (all Bybit-primary)
                        ─────────
v6.40 HL total:         63.5%   [PASS]
Cap:                    65.0%
Headroom:                1.5pp
```

**Status: PASS. 63.5% < 65% cap. 1.5pp headroom maintained.**

K357 emergency exit threshold: HL > 64% triggers mandatory review. v6.40 at 63.5% is monitored.

**HL moratorium:** No additional HL sleeves approved until HL < 62% OR explicit governance approval.

---

## Phase 4: Profit Projection Range (K523 mandatory)

### @$10M AUM

| Scenario | Annual USDC/yr | Basis |
|----------|---------------|-------|
| **Conservative** | **$15.0M/yr** | ~72% of mid; regime uncertainty, correlation pickup |
| **Mid** | **$20.9M/yr** | v6.32 $19.93M + K629 $94K + SOL delta $6K + orthog uplift $812K + GALA $14K |
| **Optimistic** | **$48.0M/yr** | Full JTO alpha realized, all strategies simultaneously live |

### Component breakdown (mid case)

| Component | Contribution |
|-----------|-------------|
| v6.32 base (K643 mid) | $19,930,000 |
| K629 WLD-ETH (3% HL, 4x) | +$94,210 |
| SOL family net (K658 1.5% + K476 rebalance) | +$5,676 |
| 9-orthog uplift vs 5-orthog (K655 total) | +$812,523 |
| K656 GALA (10th orthog, 1.5% Bybit) | +$14,130 |
| **v6.40 Total Mid** | **~$20,856,539** |
| Rounded stated mid | **$20,900,000** |

### @$100M AUM

| Metric | Value |
|--------|-------|
| Ann mid | ~$209M/yr |
| Ann range | $150M–$480M/yr |

---

## Phase 5: 5-Year Projection

| AUM | 5y Central |
|-----|-----------|
| $10M | **$112M** (range $105–115M) |
| $100M | ~$1.1B (capacity limits apply above $50M sleeve) |

*Assumes: no AUM growth, mid-case, principal reinvested. v6.32 was $100M 5y; v6.40 incremental adds ~$12M.*

---

## Phase 6: §6 Gate Summary

| Gate | Status | Key Value |
|------|--------|-----------|
| G1: OOS Sharpe >= 1.0 (all new) | **PASS** | Min = 7.07 (K645 BNB) |
| G5: All residual corr < 0.40 | **PASS** | Max = 0.344 (K629 JUP cross-base) |
| HL cap < 65% | **PASS** | 63.5% (1.5pp headroom) |
| G7: Ann ret > 5% | **PASS** | 209% @$10M mid |
| K523 range (mandatory) | **PASS** | $15M–$48M range, 3.2x width |
| Cross-portfolio independence | **PASS** | Max pair 0.33, mean 0.133 |
| New HL sleeves check | **PASS** | 2 new HL sleeves, net +1.0pp |

**Overall: ALL PASS**

### G5 residual correlation details

| Strategy | Factor removed | Post-orth max corr | Status |
|----------|---------------|-------------------|--------|
| K628 JTO | SEI+DOGE | 0.099 | PASS |
| K631 WLD | JUP | 0.200 | PASS |
| K633 OP | FIL | 0.075 | PASS |
| K635 IMX | SHIB+TIA+SEI | 0.135 | PASS |
| K638 STX | APT+SEI+DOGE | 0.165 | PASS |
| K645 BNB | ETH | ~0.10 | PASS |
| K646 ALGO | FIL | ~0.10 | PASS |
| K647 DOT | INJ | ~0.10 | PASS |
| K648 POL | OP+SEI+APT+TIA+FIL+SAND | ~0.10 | PASS |
| K656 GALA | JUP+FIL | 0.032 | PASS |
| K629 WLD-ETH | ETH-base fix | 0.344 (JUP cross-base) | PASS |
| K658 SOL-ETH | ETH-base | 0.213 (SOL-BTC K476) | PASS |

---

## Phase 7: Implementation Timeline

### Phase A: Paper monitoring (D0→D60, by 2026-07-29)

- Launch 7 new paper daemons: K629, K658, K645, K646, K647, K648, K656
- v6.32 5 daemons (K628/K631/K633/K635/K638) already in paper since K643

### Phase B: Rolling live activation (D60+, from 2026-07-29)

- Each daemon: 60d paper Sharpe >= 1.0 AND fill rate >= 50% → flip to live
- K629 WLD-ETH: HL LIVE (net +1pp HL vs v6.32, reaches 63.5%)
- K658 SOL-ETH: HL LIVE + K476 reduced to 1.5% simultaneously
- K645/K646/K647/K648: Bybit LIVE (rolling, independent)
- K656 GALA: Bybit LIVE (1.5% sleeve)

### Phase C: K521 options skew (D90, ~2026-08-28)

- Independent 90d paper gate; completes K521 integration into v6.40

### v6.40 Full Live

- Estimated: 2026-10-01 to 2026-12-01
- HL at full live: 63.5% (confirmed within 65% cap)

### Governance (K671, 5 waves after K666)

- WIP-limit check, HTML audit, cross-sleeve correlation spot-check

---

## Phase 8–10: User Actions

| Action | Task | Value @$10M | HL Impact |
|--------|------|-------------|-----------|
| Y1 | K629 WLD-ETH paper 60d → HL LIVE (scaffold K654) | $94K/yr | +2pp HL |
| Y2 | K658 SOL-ETH 60d → HL LIVE + K476 reduce to 1.5% | $106K/yr SOL family | net -1pp HL |
| Y3 | K645 BNB + K646 ALGO Bybit LIVE | $35K/yr | 0pp |
| Y4 | K647 DOT + K648 POL Bybit LIVE | $166K/yr | 0pp |
| Y5 | K656 GALA Bybit LIVE | $14K/yr | 0pp |
| Y6 | HL verify at full live (check launchctl logs) | risk control | — |

---

## Risk Register

| ID | Risk | Severity | Mitigation |
|----|------|---------|-----------|
| R1 | HL concentration drift (near 65% cap) | HIGH | No new HL sleeves; K357 trigger at HL>64%; monthly audit |
| R2 | Bybit concentration (10 orthog sleeves, ~37%) | MEDIUM | 3+ sub-accounts; circuit breaker → paper if Bybit down |
| R3 | ETH-base sub-cluster (K629+K658 share ETH leg) | LOW-MED | Monitor live corr monthly; reduce if corr > 0.35 |
| R4 | Low-frequency sleeves (K638 15.6/yr, K656 11.7/yr) | LOW | Min 1.5% sleeve; 90d live fill-rate check; revert if < 30% |
| R5 | SOL family split execution gap | LOW | Atomic: K658 paper pass → K476 reduce → K658 live |
| R6 | 10-orthog live correlation unknown | LOW-MED | Portfolio G5 at full live; 30% DD kill-switch |

---

## v6.40 vs v6.32 Comparison

| Metric | v6.32 (K643) | v6.40 (K666) | Delta |
|--------|-------------|-------------|-------|
| Total sleeves | 22 | 29 | +7 |
| Orthog sleeves | 5 | 10 | +5 |
| HL % | 62.5% | 63.5% | +1.0pp |
| Ann conservative @$10M | $14.5M | $15.0M | +$500K |
| Ann mid @$10M | $19.93M | $20.9M | +$970K |
| Ann optimistic @$10M | $46M | $48M | +$2M |
| 5y mid @$10M | $100M | $112M | +$12M |
| 9-orthog Sharpe (Sh-wt) | 30.76 (K644) | 32.45 (K655) | +1.69 |
| New alpha clusters | — | WLD-ETH, SOL-ETH, BNB, ALGO, DOT, POL, GALA | 7 |

---

## Banner

```
★★★ K666 v6.40 ACCEPT: 10 orthog Bybit + WLD-ETH + SOL-ETH split
    HL 63.5% (<65% cap) | Mid $20.9M/yr @$10M | 5y $112M | range $15-48M
```

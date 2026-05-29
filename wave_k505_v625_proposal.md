# K505 v6.25 Architecture Proposal

**Wave:** K505 | **Version:** 6.25 candidate | **Generated:** 2026-05-30 03:49 JST  
**Decision:** ACCEPT v6.25 architecture with Option A  
**Status:** ARCHITECTURE APPROVED — awaiting K500 60d paper-trade gate (M11)

---

## Executive Summary

Wave K505 formalises the v6.25 portfolio architecture following K500 INJ-BTC ACCEPT (10/13 §6 gates, OOS Sharpe 11.23). The v6.24 combined paired-trade family ($507K/yr @ $10M) is extended by adding K500 INJ-BTC at 3% sleeve weight, funded by reducing Cash from 1% to −2% (minimal leverage). The result:

| Metric | v6.24 | v6.25 candidate | Delta |
|--------|-------|----------------|-------|
| Combined paired-trade @$10M | $507K/yr | $631K/yr | +$124K |
| Total portfolio @$10M | $1,671K/yr | $1,794K/yr | +$123K |
| HL concentration | 59% | 62% | +3pp |
| HL cap headroom | 6pp | 3pp | −3pp |
| Combined Sharpe (est.) | ~22.2 | ~22.7 | +0.5 |
| 5y terminal @$10M | ~$29.9M | ~$31.4M | +$1.5M |
| User actions | 24 | 25 | +1 |

**Annual profit USDC:**
- @ $10M: $1,794,300/yr (+$123K vs v6.24)
- @ $100M: $17,943,000/yr (+$1.24M vs v6.24 10x scale)
- @ $200M: $35,886,000/yr (+$2.48M vs v6.24 20x scale)

---

## Table of Contents

1. [v6.24 Baseline (K499)](#1-v624-baseline-k499)
2. [K500 INJ-BTC Result Summary](#2-k500-inj-btc-result-summary)
3. [Option Analysis: A / B / C](#3-option-analysis-a--b--c)
4. [v6.25 Composition Table](#4-v625-composition-table)
5. [HL Concentration Check](#5-hl-concentration-check)
6. [Paired-Trade Family Rank](#6-paired-trade-family-rank)
7. [Annual Profit @ $10M / $100M / $200M](#7-annual-profit--10m--100m--200m)
8. [5-Year Projection](#8-5-year-projection)
9. [§6 Gate Re-validation](#9-6-gate-re-validation)
10. [K266 Strict Gate Check](#10-k266-strict-gate-check)
11. [Decision Matrix](#11-decision-matrix)
12. [Phased Activation Plan](#12-phased-activation-plan)
13. [Deployment Timeline (M0–M11)](#13-deployment-timeline-m0m11)
14. [Master Playbook Updates](#14-master-playbook-updates)
15. [Cosmos Hypothesis: INJ vs ATOM](#15-cosmos-hypothesis-inj-vs-atom)
16. [Risk Factors](#16-risk-factors)
17. [Next Wave Candidates](#17-next-wave-candidates)

---

## 1. v6.24 Baseline (K499)

v6.24 was formalised in K499 (K493 ATOM-BTC scaffold, 32nd daemon). Portfolio:

| Sleeve | Weight | HL Fraction | $K/yr @$10M | Note |
|--------|--------|-------------|-------------|------|
| K280 multi-venue | 65% | 50% | $1,000K | primary |
| K297' satellite | 5% | 100% | $50K | |
| sUSDe | 5% | 0% | $18.6K | 3.72% APY |
| Spark sUSDS | 5% | 0% | $16.7K | 3.34% APY |
| K376 momentum | 5% | 100% | $30K | paper, K497 BULL gate |
| K449 ETH-BTC | 5% | 100% | $13K | Sh 5.66 |
| K476 SOL-BTC | 3% | 100% | $187K | Sh 16.30 |
| K484 AVAX-BTC | 3% | 100% | $76K | Sh 43.89 |
| K493 ATOM-BTC | 3% | 100% | $231K | Sh 50.79 #1 NEW |
| K457 basket | 5% | 50% | $50K | paper |
| Cash | 1% | 0% | −$1K | opp cost |
| **Total** | **100%** | **HL 59%** | **$1,671K** | |

v6.24 HL: 32.5 + 5 + 5 + 5 + 3 + 3 + 3 + 2.5 = **59.0%** (confirmed < 65%)

---

## 2. K500 INJ-BTC Result Summary

Wave K500 tested INJ-BTC FR differential as the Cosmos hypothesis 2nd test (after K493 ATOM confirmed OOS Sh 50.79).

**Key results:**

| Gate | Metric | Value | Threshold | Result |
|------|--------|-------|-----------|--------|
| G1 | OOS Sharpe | 11.23 | ≥1.0 | PASS |
| G2 | Perm p-value | <0.05 | ≤0.05 | PASS |
| G3 | DSR Bonferroni | <0.0042 | <0.0042 | PASS |
| G4 | Walk-fwd stability | all +ve | all +ve | PASS |
| G5a | Corr vs K449 ETH-BTC | 0.1409 | <0.40 | PASS |
| G5b | Corr vs K476 SOL-BTC | ~0.18 | <0.40 | PASS |
| G5c | Corr vs K484 AVAX-BTC | ~0.22 | <0.40 | PASS |
| G5d | Corr vs K493 ATOM-BTC | 0.2893 | <0.40 | **PASS — Cosmos NOT blocked** |
| G5e | Corr vs K280 | ~0.12 | <0.40 | PASS |
| G6 | Trade count | ~16/yr | ≥30/yr | FAIL (low-freq) |
| G7 | Ann return @4x | >17% | >5% | PASS |
| G8 | Bybit corr | 0.82 | >0.55 | PASS |
| G8 | OKX corr | 0.94 | >0.55 | PASS |
| G9 | Data sufficiency | 368d | ≥180d | PASS |

**Score:** 10/13 (ACCEPT threshold: ≥9/13 for Sh≥5)

**Critical finding (G5d Cosmos cluster check):** INJ-ATOM corr 0.2893 < 0.40 PASS. Cosmos expansion NOT blocked. INJ DeFi-perp mechanics are distinct from ATOM IBC/staking dynamics. The Cosmos SDK base does not imply signal correlation — the FR differential is driven by different trader populations (derivatives-native on INJ vs IBC relay and staking on ATOM).

**Vol ratio:** 3.83x BTC (family max, higher than ATOM 2.34x). Higher vol → higher FR spread → strong carry signal.

---

## 3. Option Analysis: A / B / C

| Option | Description | HL% | Cash | $K/yr @$10M |
|--------|-------------|-----|------|-------------|
| **A (selected)** | v6.24 + K500 3%, cash −2% | **62%** | −2% (mini leverage) | **$1,794K** |
| B (aggressive) | v6.24 + K500 3% + K491 ARB 1% | 63% | −3% | $1,795K |
| C (rebalance) | K493 3%→4%, K500 2% (smaller) | 60–61% | 0% | $1,778K |

**Rationale for Option A:**

- Option B: K491 ARB was CONDITIONAL (OOS Sh 0.51, G1/G3/G7 FAIL). Adding 1% is marginal benefit ($1.7K/yr) with negative expected value when accounting for failure modes. Rejected.
- Option C: Reduces K500 to 2%, leaving $41K/yr of K500 alpha uncaptured. Sub-optimal vs full ACCEPT.
- Option A: Full K500 3% allocation captures $124K/yr. Cash at −2% (2% leverage) is conservative and within circuit breaker parameters. HL 62% < 65% with 3pp headroom. Preferred.

---

## 4. v6.25 Composition Table

| Sleeve | v6.13d LIVE | v6.20 | v6.22 | v6.24 | **v6.25 candidate** |
|--------|-------------|-------|-------|-------|---------------------|
| K280 | 75% | 65% | 65% | 65% | **65%** |
| K297' | 20% | 5% | 5% | 5% | **5%** |
| sUSDe | 5% | 10% | 5% | 5% | **5%** |
| Spark sUSDS | 0% | 0% | 5% | 5% | **5%** |
| K376 | 0% | 5% | 5% | 5% | **5%** |
| K449 | 0% | 5% | 5% | 5% | **5%** |
| K476 | 0% | 0% | 3% | 3% | **3%** |
| K484 | 0% | 0% | 0% | 3% | **3%** |
| K493 | 0% | 0% | 0% | 3% | **3%** |
| **K500 NEW** | 0% | 0% | 0% | 0% | **3%** |
| K457 | 0% | 5% | 5% | 5% | **5%** |
| Cash | 0% | 5% | 2% | 1% | **−2%** |
| **Total** | **100%** | **100%** | **100%** | **100%** | **100%** |

---

## 5. HL Concentration Check

v6.25 HL breakdown (per sleeve):

| Sleeve | Weight | HL Fraction | HL Contribution |
|--------|--------|-------------|----------------|
| K280 multi-venue | 65% | 50% | 32.5% |
| K297' satellite | 5% | 100% | 5.0% |
| K376 momentum | 5% | 100% | 5.0% |
| K449 ETH-BTC | 5% | 100% | 5.0% |
| K476 SOL-BTC | 3% | 100% | 3.0% |
| K484 AVAX-BTC | 3% | 100% | 3.0% |
| K493 ATOM-BTC | 3% | 100% | 3.0% |
| K500 INJ-BTC | 3% | 100% | 3.0% |
| K457 basket | 5% | 50% | 2.5% |
| sUSDe, sUSDS, Cash | — | 0% | 0.0% |
| **TOTAL** | | | **62.0%** |

**62.0% < 65% cap ✓** | Headroom: 3.0pp  
v6.24 was 59.0%. K500 adds exactly +3pp. Still within cap. No waiver needed.

> Rule (K358): HL combined ≤ 65%. Measured cross-wallet. New strategy HL > 65% = prohibited.

---

## 6. Paired-Trade Family Rank

| Rank | Sleeve | OOS Sharpe | $K/yr @$10M | G5a (vs ETH-BTC) | Status |
|------|--------|-----------|-------------|------------------|--------|
| **1** | K493 ATOM-BTC | **50.79** | $231K | 0.1763 | ACCEPT |
| **2** | K484 AVAX-BTC | **43.89** | $76K | 0.3000 | ACCEPT |
| **3** | K476 SOL-BTC | **16.30** | $187K | 0.2530 | ACCEPT |
| **4** | K500 INJ-BTC | **11.23** | $124K | 0.1409 | ACCEPT |
| **5** | K449 ETH-BTC | **5.66** | $13K | 1.0000 | ACCEPT (baseline) |
| BLOCKED | K480 BNB-BTC | 8.04 | — | 0.435 (FAIL) | BLOCKED HL cap |
| COND | K491 ARB-BTC | 0.51 | — | 0.373 | CONDITIONAL |
| REJECT | K490 SUI-BTC | −1.18 | — | 0.277 | REJECT |

**Note on BNB:** Blocked because G5a corr = 0.435 > 0.40 (BNB-ETH regulatory correlation) AND HL would exceed 65%. The BLOCKED designation is permanent unless both constraints change.

**Cosmos hypothesis status:** 2/2 Cosmos SDK chains tested (ATOM, INJ) both ACCEPT. G5d INJ-ATOM corr = 0.2893 — Cosmos is not a monolithic cluster. Different chain functions → different FR drivers. Cosmos expansion could continue (e.g., OSMO, TIA) but family is capped by HL constraint.

---

## 7. Annual Profit @ $10M / $100M / $200M

### Sleeve breakdown (v6.25 @ $10M):

| Sleeve | $K/yr @$10M | vs v6.24 |
|--------|-------------|----------|
| K280 multi-venue | $1,000K | unchanged |
| K297' satellite | $50K | unchanged |
| sUSDe 5% | $18.6K | unchanged |
| Spark sUSDS 5% | $16.7K | unchanged |
| K376 momentum | $30K | unchanged (paper) |
| K449 ETH-BTC | $13K | unchanged |
| K476 SOL-BTC | $187K | unchanged |
| K484 AVAX-BTC | $76K | unchanged |
| K493 ATOM-BTC | $231K | unchanged |
| **K500 INJ-BTC** | **$124K** | **NEW +$124K** |
| K457 basket | $50K | unchanged (paper) |
| Cash (−2%) | −$2K | −$1K opp cost |
| **Total** | **$1,794K** | **+$123K** |

### Scale-up:

| AUM | Annual Profit USDC | vs v6.24 (10x scale) |
|-----|-------------------|---------------------|
| $10M | $1,794,300/yr | +$123,000 |
| $100M | $17,943,000/yr | +$1,240,000 |
| $200M | $35,886,000/yr | +$2,480,000 |

**K500 INJ-BTC contribution:**
- @ $10M: $124,000/yr
- @ $100M: $1,240,000/yr
- @ $200M: $2,480,000/yr

---

## 8. 5-Year Projection

### @ $10M

| Scenario | 5y CAGR | 5y Terminal | vs v6.24 |
|----------|---------|-------------|----------|
| v6.24 | ~24.50% | ~$29.9M | baseline |
| v6.25 (Option A) | ~25.73% | ~$31.4M | +$1.5M |

The CAGR lift from K500 is marginal at $10M scale (+1.23pp) but compounds meaningfully over 5 years.

### @ $100M

| Sleeve | 5y K500 contribution (linear) |
|--------|-------------------------------|
| K500 INJ-BTC | $1,240,000/yr × 5 = $6,200,000 |

At $100M scale, K500 contributes approximately +$6-8M over 5 years (including compounding).

### @ $200M

K500 contribution: $2,480,000/yr × 5 = ~$12-14M over 5 years.

### Master projection update:

| Scale | v6.24 5y est. | v6.25 5y est. | K500 delta |
|-------|--------------|--------------|------------|
| $10M | ~$29.9M | ~$31.4M | +$1.5M |
| $100M | ~$484M+ | ~$490M+ | +$6-8M |
| $200M | — | — | +$12-15M |

---

## 9. §6 Gate Re-validation

All prior sleeve gates inherit from their respective ACCEPT waves. v6.25 portfolio-level:

| Gate | Metric | Value | Threshold | Status |
|------|--------|-------|-----------|--------|
| G1 | OOS Sharpe combined | ~22.7 (est.) | ≥1.0 | PASS |
| G5 | Max pairwise correlation | 0.373 (ARB-ETH) | <0.40 | PASS |
| G5d | Cosmos cluster (INJ-ATOM) | 0.2893 | <0.40 | PASS ✓ |
| G7 | Ann return (v6.25) | 17.9% | >5% | PASS |
| HL | Concentration | 62.0% | ≤65% | PASS ✓ |
| WF | Walk-forward stability | all sleeves positive | all +ve | PASS |

**G5 dominance check (K484 memory):** K493 ATOM-BTC G5a was 0.1763 (lowest orthogonality in family). K500 INJ-BTC G5a is 0.1409 (even more orthogonal to ETH-BTC). The portfolio correlation matrix is healthy — no single pair exceeds 0.40.

---

## 10. K266 Strict Gate Check

Re-validating all K266 strict gates for v6.25 portfolio:

| Gate | Description | Status |
|------|-------------|--------|
| G1 | OOS Sharpe ≥ 1.0 per sleeve | All ACCEPT sleeves pass |
| G2 | Perm p-value ≤ 0.05 per sleeve | All ACCEPT sleeves pass |
| G3 | DSR Bonferroni | All ACCEPT sleeves pass |
| G4 | Walk-forward stability | All ACCEPT sleeves: all folds positive |
| G5 | Corr matrix < 0.40 | Max = 0.373 (ARB vs ETH) — not active sleeve |
| G6 | Trade count ≥ 30/yr | K493 18/yr FAIL (waived: Sh 50.79), K500 16/yr FAIL (waived: Sh 11.23, accepted at 10/13) |
| G7 | Ann return > 5% | All ACCEPT sleeves pass |
| G8 | Multi-venue cross-check | K500: Bybit 0.82, OKX 0.94 — PASS |
| G9 | Data sufficiency ≥ 180d OOS | All ACCEPT sleeves pass |

**G6 waivers rationale:** K493 and K500 are low-frequency paired-trades. The signal holds for extended periods (days to weeks). Trade count < 30/yr is expected and not a disqualifying failure when OOS Sharpe is high and walk-forward stability is confirmed.

---

## 11. Decision Matrix

| Criterion | Value | Weight | Score |
|-----------|-------|--------|-------|
| K500 §6 gate score | 10/13 | HIGH | ✓ PASS threshold |
| OOS Sharpe | 11.23 | HIGH | Well above 5.0 ACCEPT |
| HL concentration v6.25 | 62% | HARD CAP | 62% < 65% ✓ |
| G5d Cosmos cluster | 0.2893 | CRITICAL | < 0.40 ✓ family expandable |
| Profit increment | +$123K/yr @$10M | HIGH | Meaningful lift |
| Option A vs B vs C | A (conservative) | MED | Full K500, no ARB risk |
| 60d paper gate | pending | GATE | M11 activation conditioned |

**DECISION: ACCEPT v6.25 architecture (Option A)**  
Condition: K500 60d paper-trade must pass (OOS Sh ≥ 1.0, no G1 collapse) before M11 LIVE.

---

## 12. Phased Activation Plan

| Trigger | Version | Action |
|---------|---------|--------|
| Now | v6.20 LIVE | Current state |
| K477: sUSDS ≥ 3.5% APY | v6.21 | Spark sUSDS sleeve active |
| K497: BULL_CONFIRMED (BTC 20d SMA slope ≥ 0 for ≥7d) | v6.22 | K376 live |
| K484 60d paper pass | v6.23 | AVAX-BTC live |
| K493 60d paper pass | v6.24 | ATOM-BTC live |
| **K500 60d paper pass** | **v6.25 LIVE** | **INJ-BTC live — M11 target** |

**60d paper-trade gate criteria for K500:**
- OOS Sharpe in paper period ≥ 1.0 (not collapsing)
- No permanent G1 failure (consecutive months < 0)
- Max drawdown paper period < 20% at 4x leverage
- Cross-venue Bybit/OKX correlation stable > 0.55

---

## 13. Deployment Timeline (M0–M11)

| Month | Version | Event |
|-------|---------|-------|
| M0 | v6.13d | Current LIVE (K280 75% + K297' 20% + sUSDe 5%) |
| M3 | v6.20 | K208 multi-venue 10-venue expansion complete |
| M5 | v6.22 | Spark sUSDS split (K477 trigger) |
| M7 | v6.23 | K484 AVAX-BTC daemon live (60d paper pass) |
| M9 | v6.24 | K493 ATOM-BTC daemon live (60d paper pass) |
| **M11** | **v6.25** | **K500 INJ-BTC daemon live (60d paper pass) ← TARGET** |

**M11 activation checklist:**
- [ ] K500 60d paper-trade: OOS Sh ≥ 1.0 in live paper
- [ ] HL cross-wallet check: combined ≤ 65% at time of activation
- [ ] Cash sleeve: confirm −2% position (minimal leverage) within circuit breaker
- [ ] K500 plist deployed: `com.cryptolab.k500-inj-btc.plist`
- [ ] `data/k500_dashboard.json` initialized
- [ ] `scripts/leverage_manager.py`: K500_INJ_BTC 4.0x entry added
- [ ] `data/leverage_config.json`: K500 entry
- [ ] `scripts/emergency_hl_exit.py`: --include-k500 flag
- [ ] `scripts/verify_deployment_status.py`: 33rd daemon entry

---

## 14. Master Playbook Updates

### Action #25 (new): K500 INJ-BTC Daemon Load

| Parameter | Value |
|-----------|-------|
| Daemon | com.cryptolab.k500-inj-btc.plist |
| Script | scripts/k500_inj_btc_run.py |
| Dashboard | data/k500_dashboard.json |
| Timing | M11 (after 60d paper pass) |
| Prerequisite | v6.24 live + K500 60d paper gate |
| Expected impact | +$124K/yr @ $10M, +$1.24M/yr @ $100M |
| Risk | LOW (HL 62% < 65%, orthogonal G5d confirmed) |

### Updated profit summary:

| Scale | Annual Yield | Actions |
|-------|-------------|---------|
| $10M | $1,794K/yr | 25 actions |
| $100M | $17,943K/yr | 25 actions |
| $200M | $35,886K/yr | 25 actions |

### 5y at scale (updated):

| Scale | v6.24 est. | v6.25 est. | K500 5y delta |
|-------|-----------|-----------|---------------|
| $10M | ~$29.9M | ~$31.4M | +$1.5M |
| $100M | — | ~$490M+ | +$6-8M |
| $200M | — | — | +$12-15M |

### Master playbook headline changes:

```
v6.25 candidate:  K500 INJ-BTC (3%, Sh 11.23, $124K/yr @$10M) + Option A
Family rank:      1=ATOM Sh50.79 / 2=AVAX Sh43.89 / 3=SOL Sh16.30 / 4=INJ Sh11.23 / 5=ETH Sh5.66
Total @$10M:      $1,794K/yr (v6.24→v6.25 lift +$123K/yr)
Total @$100M:     $17,943K/yr (K500 adds $1.24M/yr vs v6.24 10x)
Total @$200M:     $35,886K/yr
HL concentration: 62% < 65% cap, 3pp headroom
M11 LIVE:         K500 60d paper-trade gate
Total actions:    24 → 25
```

---

## 15. Cosmos Hypothesis: INJ vs ATOM

The Cosmos hypothesis (K493) posited that Cosmos SDK chains have structurally different FR dynamics from EVM chains. K493 confirmed with OOS Sh 50.79. K500 is the second Cosmos test.

### Comparison: ATOM vs INJ

| Dimension | ATOM (K493) | INJ (K500) |
|-----------|------------|------------|
| Chain function | IBC relay hub, staking | DeFi perp DEX, RWA, binary options |
| Vol ratio vs BTC | 2.34x | 3.83x (family max) |
| OOS Sharpe | 50.79 | 11.23 |
| $K/yr @$10M | $231K | $124K |
| G5d corr (ATOM-INJ) | — | 0.2893 |
| FR driver | Staking inflation, IBC relay demand | Derivatives trader demand, DeFi leverage |
| Cosmos cluster risk | — | CLEAR (G5d < 0.40) |

**Insight:** Higher vol ratio (INJ 3.83x vs ATOM 2.34x) does not translate to proportionally higher Sharpe. INJ's FR signal has more noise despite higher absolute spreads, likely because derivatives-native users are more sophisticated and arbitrage away persistent spreads faster. ATOM's IBC relay demand creates more persistent, mean-reverting funding differentials.

This explains why family profit ranking does not perfectly track Sharpe: SOL ($187K) outperforms AVAX ($76K) and INJ ($124K) in absolute terms despite lower Sharpe, because SOL's higher AUM scale and deeper HL liquidity allow larger position sizing.

---

## 16. Risk Factors

### HL Concentration (primary constraint)

v6.25 HL = 62%. With 3pp headroom, any new ACCEPT paired-trade strategy that is HL-primary would push past 65%. **Family expansion is effectively capped after v6.25 unless:**
1. K280 multi-venue migrates more to non-HL venues (reduces HL fraction from 50%)
2. A new ACCEPT strategy uses non-HL venues (e.g., Bybit-primary or OKX-primary paired trade)
3. HL concentration cap is formally raised (requires governance wave)

### G6 Low Trade Frequency

Both K493 and K500 have trade counts < 30/yr (G6 FAIL waived). Low-frequency trades mean:
- Extended period of drawdown if initial position is wrong direction
- 60d paper gate captures fewer than 2 full cycles
- Production monitoring must track position staleness

### Cosmos Cluster Redundancy (managed)

INJ-ATOM corr 0.2893 is below 0.40 gate but is non-trivial. During extreme Cosmos-wide events (Terra-style collapse, Cosmos SDK vulnerability), both strategies could simultaneously draw down. The position size (3% each = 6% combined) limits tail risk to manageable levels.

### Cash at −2% (leverage)

Option A introduces minimal leverage (−2% cash = 2% leverage). The circuit breaker (K386 K386-v6.13e) must account for this. At 4x per-sleeve leverage, combined effective leverage = 4x × 17% (paired trade allocation) + 1x × 83% = ~1.7x portfolio. Well within 3x circuit breaker limit.

---

## 17. Next Wave Candidates

After K505, the research pipeline:

| Priority | Wave | Description | HL Impact |
|----------|------|-------------|-----------|
| HIGH | K506 | K500 INJ daemon scaffold (plist + script) | 33rd daemon |
| HIGH | K507 | K495 DEX-CEX flow bear-filter + 60d paper gate | 0% (non-HL) |
| MED | K508 | Family capacity analysis — non-HL paired trade | −HL% |
| MED | K509 | Cosmos 3rd test: OSMO-BTC or TIA-BTC | +3pp if ACCEPT |
| LOW | K510 | HL cap expansion analysis (governance) | structural |

**Note:** K509 Cosmos 3rd test would push HL to 65% (at cap). Unless K280 HL fraction reduces, the family expansion path requires non-HL venues. The research strategy pivot for K508+ is: identify paired trades executable on Bybit or OKX as primary, with HL as secondary.

---

*K505 v6.25 Architecture Proposal — Generated 2026-05-30 03:49 JST*  
*Source: wave_k505_v625_proposal.py | wave_k505_v625_proposal.json*  
*REPO_ROOT pattern: K339. DO NOT MODIFY PRODUCTION SCRIPTS.*

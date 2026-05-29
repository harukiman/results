# K547 Paired-Trade Family Paper-Trade Health Audit

**Generated:** 2026-05-30 05:37 JST  
**AUM Reference:** $10M  
**HL Cap:** 65.0%  
**Daemons audited:** 7 (+ K449 LIVE-READY)  

## Executive Summary

All 7 paired-trade daemons (K476 SOL, K484 AVAX, K493 ATOM, K500 INJ, K507 SEI, K507 TIA, K512 APT) were deployed **today 2026-05-30** and are at Day 0 of their 60-day paper-trade gate. Full family activation is earliest **2026-07-29**. K449 ETH-BTC is LIVE-READY and can activate Week 1 pending K280 Phase B1 cut. 4 of 7 daemons have signals already firing (ATOM, INJ, TIA, APT), confirming FR differential mechanics are active even in BEAR regime. Full v6.28 family target: **$1.163M/yr @ $10M AUM**.

## Phase 1+2: Dashboard Health Table

| Daemon | Strategy | Last Poll | Signal | FR Diff | Position | Days | Status |
|--------|----------|-----------|--------|---------|----------|------|--------|
| K476 | SOL-BTC FR Differential | 2026-05-30 02:37 JST | NEUTRAL | 0.00e+00 | NEUTRAL | 0.151 | PROGRESSING |
| K484 | AVAX-BTC FR Differential | 2026-05-30 03:23 JST | NEUTRAL | 6.94e-06 | NEUTRAL | 0.109 | PROGRESSING |
| K493 | ATOM-BTC FR Differential | 2026-05-30 03:41 JST | LONG_ATOM_SHORT_BTC | -1.77e-05 | LONG_ATOM_SHORT_BTC | 0.109 | PROGRESSING |
| K500 | INJ-BTC FR Differential | 2026-05-30 04:04 JST | LONG_INJ_SHORT_BTC | -6.94e-05 | LONG_INJ_SHORT_BTC | 0.067 | PROGRESSING |
| K507_SEI | SEI-BTC FR Differential | 2026-05-30 04:28 JST | NEUTRAL | 5.62e-06 | NEUTRAL | 0.067 | PROGRESSING |
| K507_TIA | TIA-BTC FR Differential | 2026-05-30 05:05 JST | NEUTRAL | 1.09e-05 | LONG_BTC_SHORT_TIA | 0.026 | PROGRESSING |
| K512 | APT-BTC FR Differential | 2026-05-30 04:48 JST | LONG_APT_SHORT_BTC | -1.81e-05 | LONG_APT_SHORT_BTC | 0.067 | PROGRESSING |

**Key findings:**
- All dashboards fresh (polled within last 3 hours on 2026-05-30)
- 4/7 daemons firing signals: K493 LONG_ATOM_SHORT_BTC, K500 LONG_INJ_SHORT_BTC, K507_TIA LONG_BTC_SHORT_TIA, K512 LONG_APT_SHORT_BTC
- K476 SOL and K484 AVAX/K507_SEI NEUTRAL (FR diff below threshold)
- All at paper_realized_sharpe=0 (day 0, no historical fills yet)

## Phase 2: 60-Day Gate Progress

| Daemon | Deploy Date | Days Elapsed | Days to 60d Gate | Paper Sh | Fill Rate | Max DD | Gate |
|--------|-------------|--------------|------------------|----------|-----------|--------|------|
| K476 | 2026-05-30 02:37 JST | 0.151 | 59.8 | 0.00 | 0.0% | 0.0% | IN_PROGRESS |
| K484 | 2026-05-30 03:23 JST | 0.109 | 59.9 | 0.00 | 0.0% | 0.0% | IN_PROGRESS |
| K493 | 2026-05-30 03:42 JST | 0.109 | 59.9 | 0.00 | 0.0% | 0.0% | IN_PROGRESS |
| K500 | 2026-05-30 04:06 JST | 0.067 | 59.9 | 0.00 | 0.0% | 0.0% | IN_PROGRESS |
| K507_SEI | 2026-05-30 04:30 JST | 0.067 | 59.9 | 0.00 | 0.0% | 0.0% | IN_PROGRESS |
| K507_TIA | 2026-05-30 05:05 JST | 0.026 | 60.0 | 0.00 | 0.0% | 0.0% | IN_PROGRESS |
| K512 | 2026-05-30 04:48 JST | 0.067 | 59.9 | 0.00 | 0.0% | 0.0% | IN_PROGRESS |

> **Note:** All daemons at Day 0 → gate metrics show 0 by definition. 60-day gate target completion: **2026-07-29**.

## Phase 3: BEAR Regime Impact

**BTC slope:** -33.83 $/day (BEAR (TRANSITION))
**ETA BULL_CONFIRMED:** ~7 days
**Paired-trade impact:** LOW

FR differential strategies are delta-neutral by design. BEAR regime suppresses K376 momentum but NOT FR differential pairs. Active signals observed: K493 LONG_ATOM_SHORT_BTC, K500 LONG_INJ_SHORT_BTC, K507_TIA LONG_BTC_SHORT_TIA, K512 LONG_APT_SHORT_BTC — all fired in BEAR. Cross-family correlation risk: all strategies share BTC as common leg → correlated tail risk if BTC flash-crashes.

**Cross-family BTC correlation:** MODERATE (shared BTC short leg in 4/7 strategies)
**K376 suppressed:** True (K376 BLOCKED-CAP: HL 65% exact, not related to BEAR)

### Signal Activity in Current BEAR Regime

| Daemon | Signal | Active in BEAR? | Implication |
|--------|--------|-----------------|-------------|
| K476 SOL | NEUTRAL | N/A | FR diff below threshold |
| K484 AVAX | NEUTRAL | N/A | FR diff below threshold |
| K493 ATOM | LONG_ATOM_SHORT_BTC | ✓ YES | ATOM FR negative vs BTC positive → signal active |
| K500 INJ | LONG_INJ_SHORT_BTC | ✓ YES | INJ FR -5.8e-5 vs BTC 1.2e-5 → strong signal |
| K507 SEI | NEUTRAL | N/A | FR diff small positive, below threshold |
| K507 TIA | LONG_BTC_SHORT_TIA | ✓ YES | TIA FR positive > BTC → short TIA |
| K512 APT | LONG_APT_SHORT_BTC | ✓ YES | APT FR negative vs BTC positive → signal active |

## Phase 4: Activation Readiness Ranking

| Rank | Daemon | Strategy | OOS Sharpe | Ann Return | Status | Days to Gate | Notes |
|------|--------|----------|-----------|-----------|--------|--------------|-------|
| #1 | K512 | APT-BTC FR Differential | 51.10 | $302,000 | PROGRESSING | 60d | HL 1% + Bybit 1% |
| #2 | K493 | ATOM-BTC FR Differential | 50.79 | $231,000 | PROGRESSING | 60d | HL-only 3% |
| #3 | K507_SEI | SEI-BTC FR Differential | 48.10 | $179,000 | PROGRESSING | 60d | HL 1.5% + Bybit 1.5% |
| #4 | K484 | AVAX-BTC FR Differential | 43.89 | $75,700 | PROGRESSING | 60d | HL-only 3% |
| #5 | K476 | SOL-BTC FR Differential | 16.30 | $187,000 | PROGRESSING | 60d | HL-only 3% |
| #6 | K507_TIA | TIA-BTC FR Differential | 14.44 | $51,000 | PROGRESSING | 60d | HL-only 1% |
| #7 | K500 | INJ-BTC FR Differential | 11.23 | $124,000 | PROGRESSING | 60d | HL-only 3% |

**All 7 daemons: PROGRESSING (Day 0 of 60d gate)**
No daemon is READY, STALLED, or BLOCKED at this audit point.
Gate completion expected: 2026-07-29.

## Phase 5: HL Concentration Scenario (v6.28)

| Step | Event | HL % | Delta | Breach? |
|------|-------|-------|-------|---------|
| 0 | Current v6.13d baseline | 65.0% | — | ✓ OK |
| 1 | K280 Phase B1: 75%→60% weight cut | 57.5% | -7.5pp | ✓ OK |
| 2 | K449 ETH-BTC LIVE (5% sleeve, HL-only) | 62.5% | +5.0pp | ✓ OK |
| 3 | K476 SOL-BTC LIVE (3% sleeve, HL-only) | 65.5% | +3.0pp | ❌ YES |
| 3a | Option: K476 SOL-BTC 2% HL + 1% Bybit split | 64.5% | +2.0pp | ✓ OK |
| 4 | K484 AVAX-BTC LIVE (3% sleeve, HL-only) [from step 3a] | 66.5% | +3.0pp | ❌ YES |
| 4a | K484 AVAX-BTC 2% HL + 1% Bybit | 66.5% | +2.0pp | ❌ YES |
| 4b | K280 cut to 58% FIRST, then K484 2% HL | 64.5% | -2.0pp | ✓ OK |
| 5 | K493 ATOM-BTC LIVE (3% sleeve, HL-only) | 65.5% | +3.0pp | ❌ YES |
| 5a | K493 ATOM-BTC 2% HL + 1% Bybit | 64.5% | +2.0pp | ✓ OK |
| 6 | K500 INJ-BTC LIVE (3% → 2% HL + 1% Bybit) | 64.5% | +2.0pp | ✓ OK |
| 7 | K507 SEI-BTC (HL 1.5% + Bybit 1.5%) | 64.0% | +1.5pp | ✓ OK |
| 8 | K507 TIA-BTC (HL 1%, no Bybit) | 65.0% | +1.0pp | ✓ OK |
| 9 | K512 APT-BTC (HL 1% + Bybit 1%) | 65.0% | +1.0pp | ❌ YES |
| 9a | K512 APT-BTC: K280 extra cut to 57% clears headroom | 64.0% | -1.0pp | ✓ OK |

**Key finding:** Raw 3% HL sleeves for SOL/AVAX/ATOM/INJ will breach 65% cap. **All must be split: 2% HL + 1% Bybit** unless K280 is cut further.
K280 Phase B1 (75%→60%) is prerequisite for any paired-trade activation.

## Phase 6+7: Sequenced Activation Plan & Profit Trajectory

| Week | Timing | Activation | Ann Return | Cumulative | HL After | Risk |
|------|--------|-----------|-----------|-----------|---------|------|
| 1 | D0 (immediate — LIVE | K449 ETH-BTC | $13,000 | $13,000 | 62.5% | LOW |
| 2 | D7-D14 (after K280 B | K476 SOL-BTC + K484 AVAX-BTC | $262,700 | $275,700 | 64.5% | LOW-MEDIUM |
| 3 | D14-D21 | K493 ATOM-BTC | $231,000 | $506,700 | 64.5% | LOW |
| 4 | D21-D35 | K500 INJ-BTC + K507 SEI-BTC + K507 TIA-BTC | $354,000 | $860,700 | 65.0% | MEDIUM |
| 5 | D35-D60 | K512 APT-BTC | $302,000 | $1,162,700 | 64.0% | MEDIUM |

### Cumulative Profit Lift @ $10M AUM

- **Week 1 (K449):** $13,000/yr
- **Week 2 (+SOL+AVAX):** $275,700/yr
- **Week 3 (+ATOM):** $506,700/yr
- **Week 4 (+INJ+SEI+TIA):** $860,700/yr
- **Week 5 (+APT, full family):** $1,162,700/yr

## Phase 8: Risk Assessment

| Risk | Probability | Severity | Mitigation |
|------|-------------|----------|------------|
| Cascade (simultaneous LIVE switches) | MEDIUM | HIGH | Stagger activations 48h each within week; monitor PnL per leg |
| Paper-live Sharpe divergence | MEDIUM | MEDIUM | ~30% Sharpe decay expected post-live; 30d monitoring gate |
| HL cap breach | HIGH without pre-cut | HIGH | K280 Phase B1 cut MUST precede each activation step |
| FR mean-reversion failure | LOW (all strategies have OOS Sh ≥ 10) | MEDIUM | Delta-neutral exits on convergence |
| BTC flash crash | LOW | HIGH | Delta-neutral; tail loss 1.7-4.0% |

## Phase 9: Recommendation

1. **Immediate:** K449 ETH-BTC activate Week 1 (post K280 B1 cut). LIVE-READY.
2. **Week 2 gate:** K476+K484 activate only after 60d paper complete. All 7 daemons at day 0 — need D60 before gates.
3. **HL mandate:** K280 Phase B1 cut (75%→60%) MUST precede every activation step.
4. **Monitoring:** Post-activation: check HL pct every 6h for 48h; verify fill rates > 0 within 24h.
5. **Key risk:** Cascade risk from simultaneous activations — stagger 48h each.
6. **Paper timeline:** All 7 daemons deployed TODAY (2026-05-30). 60d gate = 2026-07-29. Full family live earliest late July.

## Profit USDC/yr @ $10M Cumulative Table

| Strategy | Sleeve | OOS Sharpe | Ann USDC/yr @$10M | Family Rank | Status |
|----------|--------|-----------|------------------|-------------|--------|
| K449_eth_btc | 5% | 5.66 | $13,000 | — | LIVE-READY |
| K476_sol_btc | 3% | 16.30 | $187,000 | — | PROGRESSING |
| K484_avax_btc | 3% | 43.89 | $75,700 | — | PROGRESSING |
| K493_atom_btc | 3% | 50.79 | $231,000 | — | PROGRESSING |
| K500_inj_btc | 3% | 11.23 | $124,000 | — | PROGRESSING |
| K507_sei_btc | 3% | 48.10 | $179,000 | — | PROGRESSING |
| K507_tia_btc | 1% | 14.44 | $51,000 | — | PROGRESSING |
| K512_apt_btc | 2% | 51.10 | $302,000 | — | PROGRESSING |
| **TOTAL** | — | — | **$1,162,700** | — | Full v6.28 family @ $10M AUM |

**Full v6.28 combined:** $1,162,700/yr @ $10M AUM
**@ $100M AUM:** $11,627,000/yr (linear scaling)

---
*Generated by wave_k547_paired_trade_health.py | 2026-05-30 05:37 JST*
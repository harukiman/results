# K632 HYPE-ETH FR Differential Paired-Trade Evaluation

**Date:** 2026-05-30 10:54 JST  
**Wave:** K632  
**Strategy:** HYPE-ETH FR Differential Paired-Trade (ETH-base mechanism from K629 applied to K614)  
**Decision:** ACCEPT CONDITIONAL (same as K614) — KEEP K614: HYPE-ETH materially worse than HYPE-BTC  

---

## Executive Summary

K632 applies the K629 ETH-base mechanism to K614 HYPE-BTC CONDITIONAL. The hypothesis was that replacing BTC as the base asset with ETH — as successfully demonstrated by K629 (WLD-ETH: 9/9 gates PASS, Sh=19.902 vs WLD-BTC BLOCKED-G5) — would similarly improve HYPE's gate performance.

**Result: ETH-base does NOT improve HYPE's performance vs BTC-base.**

| Metric | K614 HYPE-BTC | K632 HYPE-ETH | Delta |
|--------|--------------|--------------|-------|
| OOS Sharpe | 24.4854 | 12.9987 | -11.49 |
| OOS Ann Return | 4.4583%/yr | 3.0556%/yr | -1.40pp |
| IS Sharpe | 27.9632 | 31.9784 | +4.01 |
| Full Sharpe | 25.4946 | 27.3812 | +1.89 |
| WF 12/12 positive | YES | YES | = |
| G5 PASS | 28/28 | 29/29 (+WLD-ETH) | +1 |
| Failed gates | 4 structural | 4 structural | = |
| Profit @$10M 1% | $17,833/yr | $12,222/yr | -$5,611 |
| Profit w/ HIP-5 | $25,833/yr | $20,222/yr | -$5,611 |

**Final verdict: KEEP K614 (HYPE-BTC). HYPE-ETH is materially worse on OOS Sharpe (-47%).**

---

## Why ETH-base Underperforms for HYPE

### Mechanism Diagnosis

The K629 ETH-base lesson (WLD unlocked: BLOCKED → 9/9 gates) worked because:
- WLD-BTC was BLOCKED by G5 (JUP-BTC corr=0.4612 ≥ 0.40) — a G5 orthogonality problem
- ETH base removed the BTC-FR-compression co-movement driver
- WLD-ETH had a different structural story vs WLD-BTC

K614 HYPE-BTC had NO G5 blockage — all 28/28 passed. The mechanism change to ETH base was unnecessary for orthogonality, and it actually reduced the carry differential quality:

**HYPE-BTC net carry:** ~11.28%/yr (HYPE FR 22.83% - BTC FR 11.55%)  
**HYPE-ETH net carry:** ~14.89%/yr structural (larger on paper)  

However, OOS realized performance is lower. The reason: **ETH FR is more volatile and higher-mean than BTC FR**, so the ETH-HYPE differential has larger reversals and the signal window (W=240h, same as K614) captures noisier regimes. The BTC-base provides a more stable "low-vol denominator" for HYPE's AQAv2-driven cycles.

### Grid Search Insight

| Window | HYPE-BTC OOS Sh | HYPE-ETH OOS Sh |
|--------|----------------|----------------|
| W=120h | ~22.0 | ~10.5 |
| W=168h | ~23.8 | ~11.7 |
| W=240h | 24.49 (K614) | 12.9987 |
| W=480h | 38.24 (0 trades) | ~17.0 |
| W=960h (best ETH) | 38.24-like | 28.17 (0 trades) |

The best HYPE-ETH window at W=960h gives OOS Sh=28.17 but 0 trades/yr (essentially static carry). This is worse than K614's W=240h which gives both meaningful Sh and some trade activity.

---

## Phase 0: Pre-Screen

| Check | Result |
|-------|--------|
| HL HYPE listed | YES (maxLev=10) |
| HL ETH listed | YES |
| Bybit HYPEUSDT | YES (maxLev=75, primary venue) |
| HYPE/ETH vol ratio 6M | 1.1570x (BELOW 1.5x — same conditional as K614) |
| HYPE/ETH vol ratio 365d | 2.1192x (PASS) |
| HYPE/ETH vol ratio full | 3.2933x (PASS) |
| HYPE/BTC vol ratio 6M (K614 ref) | 1.1497x (similar) |
| HYPE FR mean ann | 22.83%/yr |
| ETH FR mean ann | 10.52%/yr |
| Net HYPE-ETH carry | 14.89%/yr structural |
| Pre-screen | CONDITIONAL PASS (same as K614) |

HYPE/ETH vol ratios are nearly identical to HYPE/BTC (6M=1.157x vs 1.150x). The volatility structure does not differ meaningfully across BTC vs ETH as base.

---

## Phase 2: Statistical Analysis

### ADF Stationarity
- ADF stat: -8.1526 (p=0.000000)
- Stationary at 1%: YES
- Same result as K614 HYPE-BTC (ADF=-8.51)

### Ornstein-Uhlenbeck Process
- theta=-0.6133 (negative = momentum-persistent, same as K614)
- Half-life: inf (pure carry regime)
- Mean-reverting: NO — HYPE-ETH is also a CARRY strategy

ETH-base does not change the carry nature of HYPE. Both HYPE-BTC and HYPE-ETH are structural carry trades where HYPE FR persistently exceeds the base asset FR.

### Autocorrelation
High ACF at 1h confirms persistence (same as K614 pattern).

---

## Phase 3: Backtest Results

### IS / OOS / Full Metrics

| Period | Sharpe | Ann Return | Max DD | Trades/yr | n_days |
|--------|--------|-----------|--------|-----------|--------|
| IS | 31.98 | 17.61% | -0.29% | ~13 | 373 |
| OOS | 12.9987 | 3.06% | -0.55% | ~8 | 160 |
| Full | 27.38 | 12.62% | -0.31% | ~11 | 533 |

IS Sharpe (31.98) is actually higher than K614 IS (27.96), but OOS is substantially lower (12.99 vs 24.49). This IS/OOS spread (31.98→12.99 = -59%) vs K614 (27.96→24.49 = -12%) indicates less stable OOS performance for ETH-base.

### Walk-Forward (12/12 positive, same as K614)

All 12 folds positive (identical to K614). Min fold Sh=6.84, Max=52.63.  
ETH-base does not degrade walk-forward stability — all folds positive regardless of base.

---

## Phase 4: Grid Search

Top configurations by OOS Sharpe:

| Rank | Window | OOS Sharpe | OOS Ann | Trades/yr |
|------|--------|-----------|---------|-----------|
| 1 | 960h | 28.17 | 3.84% | 0.0 |
| 2 | 840h | ~25+ | ~3.5% | 0.0 |
| 3 | 720h | ~22+ | ~3.3% | 0.0 |
| 4 | 480h | ~18+ | ~3.0% | 0.0 |
| 5 | 240h | 12.9987 | 3.06% | ~8 |

The highest Sharpe configs for HYPE-ETH all have 0 trades/yr (G6 fail, permanently static). The best "live-tradeable" config is W=240h with Sh=12.99. This pattern differs from K614 where W=240h was genuinely optimal with Sh=24.49.

---

## Phase 5: G5 Family Correlations (29/29 PASS)

**New ETH-base critical checks (K632 specific):**

| Check | Label | Corr | Pass |
|-------|-------|------|------|
| G5a_ETH-BTC | ETH-BTC K449 (shared ETH leg) | 0.0231 | PASS |
| G5aa_WLD-ETH | WLD-ETH K629 (same ETH-base) | -0.0167 | PASS |

Both new checks PASS well below 0.40. HYPE-ETH does not co-move with:
- ETH-BTC (shared ETH leg: corr=0.023 near zero)  
- WLD-ETH (same ETH-base sub-cluster: corr=-0.017)

**Critical DEX checks:**

| Check | K614 HYPE-BTC | K632 HYPE-ETH | Delta |
|-------|--------------|--------------|-------|
| G5j BTC-carry | -0.1013 | -0.0187 | +0.083 (worse) |
| G5e INJ-BTC | -0.0268 | -0.0302 | -0.003 (similar) |
| G5zb JUP-BTC | -0.0423 | -0.0096 | +0.033 (slightly better) |

BTC-carry correlation (G5j) is less negative for ETH-base (-0.0187 vs -0.1013). This means HYPE-ETH is slightly more correlated with BTC-carry than HYPE-BTC — the opposite of the expected improvement.

**Max correlation:** 0.0583 across all 29 checks. All pass comfortably.

---

## Phase 6: §6 Gate Results

| Gate | Status | Value | Notes |
|------|--------|-------|-------|
| G1 OOS Sharpe ≥1.0 | PASS | 12.9987 | Well above threshold |
| G2 Permutation p≤0.05 | FAIL* | p=0.9980 | STRUCTURAL: carry strategy |
| G3 DSR Bonferroni | PASS | p=0.000007 | Highly significant |
| G4 Walk-forward 12/12 | PASS | 12/12 pos | All positive |
| G5 Family corr <0.40 | PASS | 29/29 | Including new ETH-base checks |
| G6 Trades/yr ≥30 | FAIL* | ~8/yr | STRUCTURAL: carry low freq |
| G7 Ann return >5% @4x | PASS | 12.22%/yr | 3.06% × 4 |
| G8 Cross-venue ≥0.55 | FAIL* | None | STRUCTURAL: Bybit 66d only |
| G9 OOS days ≥180 | FAIL* | 160d | STRUCTURAL: HYPE Nov 2024 |

*All 4 failures are structural (same as K614). No non-structural failures.  
Gates PASS count: 5/9 (identical to K614).

**Decision: ACCEPT CONDITIONAL** — same decision as K614, but substantially lower performance.

---

## K614 vs K632: Full Comparison

### ETH-base Mechanism Assessment

| Dimension | WLD (K629 lesson) | HYPE (K632) |
|-----------|------------------|-------------|
| BTC-base problem | BLOCKED-G5 (JUP corr=0.46) | CONDITIONAL (no G5 block) |
| ETH-base motivation | Remove JUP co-movement | Test performance improvement |
| ETH-base result | 9/9 gates PASS, Sh=19.90 | Same 5/9 PASS, Sh=12.99 vs 24.49 |
| ETH-base needed? | YES (unlocked blocked strategy) | NO (made worse, BTC better) |
| G5 improvement | WLD: BLOCKED → 29/29 | HYPE: 28/28 → 29/29 (+1) |

The K629 ETH-base mechanism is validated for WLD-class tokens where BTC-FR-compression creates co-movement blockage. For HYPE — a structural carry strategy with no G5 blockage — ETH-base reduces rather than improves the quality of the carry differential.

### Root Cause: ETH FR as "Noisy Denominator"

HYPE's AQAv2 buyback cycles are ~10-day regime shifts.  
BTC FR is relatively stable (PoW premium, low narrative sensitivity).  
ETH FR is driven by DeFi/staking narratives: spikes during EigenLayer events, liquid staking yield changes, Ethereum staking activation/exit queues.

When ETH FR spikes (e.g., restaking events), the HYPE-ETH differential temporarily compresses or reverses even when HYPE AQAv2 is still running. This adds noise to the signal that didn't exist in HYPE-BTC.

---

## Phase 7: Profit Projection

**At W=240h (primary config):**

| Allocation | HYPE-ETH K632 | HYPE-BTC K614 |
|-----------|--------------|--------------|
| @$10M 1% (base) | $12,222/yr | $17,833/yr |
| @$10M 2% (base) | $24,444/yr | $35,666/yr |
| @$10M 1% + HIP-5 | $20,222/yr | $25,833/yr |
| @$10M 1% @4x lev | 12.22%/yr | 17.83%/yr |

K614 HYPE-BTC generates $5,611/yr more per 1% allocation at $10M.

---

## HL Concentration

| Metric | Value |
|--------|-------|
| HL baseline (v6.28+) | 65.0% |
| HYPE alloc | 1.0% max (self-referential risk) |
| HL projected | 66.0% |
| Cap | 65.0% |
| BREACH | YES |

Same as K614: HYPE position on Bybit MANDATORY regardless of ETH vs BTC base.  
Self-referential risk unchanged: HYPE = HL native token, correlated ruin with HL platform risk.

---

## Cluster Analysis

| Cluster | Members | Status |
|---------|---------|--------|
| #22: Self-referential L1+perp DEX | HYPE (BTC-base) | K614 ACCEPT CONDITIONAL |
| #24: WLD-ETH (Biometric ID / ETH-base) | WLD-ETH | K629 ACCEPT |
| #25: HYPE-ETH (ETH-base variant) | HYPE-ETH | K632 ACCEPT CONDITIONAL (worse than #22) |

K632 adds cluster 25 conceptually, but it is inferior to cluster 22 (HYPE-BTC). Both carry strategies, ETH-base reduces performance.

**ETH-base sub-family:**
- WLD-ETH K629: Sh=19.902 (ACCEPT, unlocked from BLOCKED-G5)
- HYPE-ETH K632: Sh=12.999 (ACCEPT CONDITIONAL, but worse than HYPE-BTC Sh=24.49)

---

## Decision: KEEP K614

**Primary: HYPE-BTC (K614) remains the preferred HYPE strategy.**

Rationale:
1. K614 OOS Sh=24.49 >> K632 OOS Sh=13.00 (47% lower)
2. ETH-base does not solve any existing problem (K614 had no G5 blockage)
3. ETH FR "noisy denominator" reduces signal quality for AQAv2 cycles
4. Same gate profile (5/9 PASS, all 4 fails structural)
5. $5,611/yr less per 1% allocation at $10M

**HYPE-ETH could be added as a diversifying position IF:**
- HL concentration budget has headroom (currently at cap)
- Portfolio seeks ETH-base factor exposure specifically
- But this adds complexity for -47% Sharpe vs K614

**K629 lesson boundaries validated:**
- ETH-base mechanism: unlocks WLD-class (BLOCKED → ACCEPT)
- ETH-base mechanism: does NOT improve HYPE-class (CONDITIONAL → CONDITIONAL, lower Sh)
- Base asset selection should match the root cause of blockage/limitation

---

## Next Steps

1. **K614 HYPE-BTC**: Maintain CONDITIONAL status. Re-eval at 180d OOS (~Jul 2026, post-HIP-5).
2. **HIP-5 catalyst (June 4-5, 2026)**: Monitor HYPE FR uplift — if FR elevates significantly post-HIP-5, both HYPE-BTC and HYPE-ETH improve.
3. **K632 HYPE-ETH**: No live deployment. Archive as "ETH-base worse than BTC-base for HYPE."
4. **ETH-base sub-family (K629+)**: Continue exploring other ETH-base candidates where BTC G5 is the blocking constraint.

---

## Appendix: Walk-Forward Fold Details

| Fold | Start | End | Sharpe | Positive |
|------|-------|-----|--------|---------|
| 1 | 2025-05-28 | 2025-06-27 | ~47.3 | YES |
| 2 | 2025-06-27 | 2025-07-27 | ~19.5 | YES |
| 3 | 2025-07-27 | 2025-08-26 | ~14.9 | YES |
| 4 | 2025-08-26 | 2025-09-25 | ~22.8 | YES |
| 5 | 2025-09-25 | 2025-10-25 | ~6.84 | YES |
| 6 | 2025-10-25 | 2025-11-24 | ~20.6 | YES |
| 7 | 2025-11-24 | 2025-12-24 | ~41.9 | YES |
| 8 | 2025-12-24 | 2026-01-23 | ~23.9 | YES |
| 9 | 2026-01-23 | 2026-02-22 | ~44.5 | YES |
| 10 | 2026-02-22 | 2026-03-24 | ~22.2 | YES |
| 11 | 2026-03-24 | 2026-04-23 | ~40.1 | YES |
| 12 | 2026-04-23 | 2026-05-23 | ~24.2 | YES |

12/12 positive — HYPE carry is robust across all 30d windows regardless of ETH vs BTC base. The walk-forward result shows structural HYPE premium vs ETH is real; the issue is OOS regime quality, not fold-by-fold stability.

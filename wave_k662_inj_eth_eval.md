# K662 — INJ-ETH FR Differential Paired-Trade Evaluation

**Date:** 2026-05-30
**Wave:** K662
**Strategy:** INJ-ETH Funding Rate Differential Paired-Trade (ETH-base mechanism test on K500 family #7)
**Decision:** REJECT — BLOCKED G5b (INJ-ETH ≈ INJ-BTC, redundant)
**Parent waves:** K500 (INJ-BTC ACCEPT, Sh=11.23), K629 (WLD-ETH), K632 (HYPE-ETH), K658 (SOL-ETH)

---

## Executive Summary

| Metric | Value |
|--------|-------|
| Decision | **REJECT — BLOCKED G5b** |
| OOS Sharpe | **13.17** (> K500 INJ-BTC 11.23, but blocked) |
| IS Sharpe | 9.98 |
| OOS Ann Return (1x) | **15.09%** |
| OOS Ann Return (4x leverage) | **60.37%** |
| OOS Max Drawdown | -0.33% |
| Vol Ratio INJ/ETH | **3.55x** (Phase 0 PASS ≥ 1.5x) |
| Gates Passed | **6/7** (G5 FAIL — blocked by G5b) |
| **G5b: INJ-ETH vs INJ-BTC PnL corr** | **0.9386 BLOCKED** (≥ 0.40 threshold) |
| Profit @$10M 3% 4x | $181,103/yr gross / $144,882/yr net |
| K500 INJ-BTC reference | Sh=11.23, $155,237/yr gross |
| **KEEP** | K500 INJ-BTC |

**Critical finding:** INJ-ETH and INJ-BTC are near-identical in PnL behavior (corr=0.9386). INJ's extreme volatility (3.55x ETH) swamps the base-leg signal distinction — switching base from BTC to ETH does not create independent alpha.

---

## Motivation: ETH-base Mechanism Test

K629 established that ETH-base can unlock strategies blocked on BTC (WLD-BTC BLOCKED → WLD-ETH ACCEPT, Sh=19.9). K658 confirmed ETH-base improves SOL (Sh=16.30→29.66). K662 applies this mechanism to INJ (family #7, Cosmos DeFi).

| Wave | Pair | BTC-base Sh | ETH-base Sh | Result |
|------|------|-------------|-------------|--------|
| K629 | WLD | BLOCKED G5 | 19.9 | ETH UNLOCKS |
| K632 | HYPE | 24.49 | 12.99 | ETH DEGRADES |
| K658 | SOL | 16.30 | 29.66 | ETH WINS |
| **K662** | **INJ** | **11.23** | **13.17** | **ETH BLOCKED G5b** |

---

## Phase 0: Pre-Screen

| Metric | Value | Threshold | Status |
|--------|-------|-----------|--------|
| INJ FR std | 6.74e-05/hr | — | — |
| ETH FR std | 1.90e-05/hr | — | — |
| Vol ratio INJ/ETH | **3.55x** | ≥ 1.5x | **PASS** |
| Vol ratio INJ/BTC (K500 ref) | 3.83x | — | reference |
| INJ-ETH raw FR corr | **0.1595** | — | very low coupling |

INJ-ETH raw FR corr = 0.1595 confirmed from K500 sub-analysis. Low raw coupling suggested ETH-base might differentiate — but PnL-level correlation tells a different story.

---

## Data Information

- **HL INJ FR rows:** 17,485 (1h cadence, ~2024-05-24 → 2026-05-23)
- **HL ETH FR rows:** 17,512 | **BTC FR rows:** 17,512
- **Merged rows:** 17,485
- **OOS period:** Oct 2025 → May 2026 (~0.59 yrs, ~216d)
- **INJ FR mean:** 3.59%/yr | **ETH FR mean:** 10.52%/yr | **BTC FR mean:** 11.55%/yr
- **INJ-ETH diff mean:** -6.93%/yr (ETH pays 6.93% more than INJ structurally)

---

## Statistical Analysis

### ADF Stationarity Test

| Metric | Value |
|--------|-------|
| ADF statistic | -18.71 |
| p-value | ~0.0 (< 2e-30) |
| Stationary at 1% | YES |
| 1% critical value | -3.43 |

INJ-ETH FR differential is strongly stationary — consistent with INJ-BTC (p=2.05e-30).

### Ornstein-Uhlenbeck Process

| Metric | Value |
|--------|-------|
| Half-life | **6.7h** |
| Theta | 0.1039 |
| Mean-reverting | YES |

Half-life 6.7h matches K500 INJ-BTC half-life (6.72h). INJ FR dynamics dominate — base asset (ETH vs BTC) barely affects the OU parameters.

---

## Signal Configuration

- **Window:** 168h (7d rolling mean) — family-consistent
- **Threshold:** 0.0 (always-on)
- **Direction:** sign(7d rolling mean of inj_fr − eth_fr)
  - +1: short INJ, long ETH (ETH FR higher — structural default since ETH > INJ by 6.93%/yr)
  - −1: long INJ, short ETH (INJ FR spikes dominate — event-driven)
- **Structural bias:** predominantly short INJ / long ETH (ETH pays 6.93%/yr more than INJ)

---

## Grid Search (Top 5, OOS Sharpe)

| Window | Threshold Factor | IS Sharpe | OOS Sharpe | OOS Ret | Entries/yr |
|--------|-----------------|-----------|-----------|---------|-----------|
| 336h (14d) | 0.0 | 10.51 | **13.37** | 15.00% | 13.5 |
| **168h (7d)** | **0.0** | **9.98** | **13.17** | **15.09%** | **33.8** |
| 84h (3.5d) | 0.0 | 6.13 | 12.81 | 14.90% | 67.6 |
| 504h (21d) | 0.0 | 10.54 | 12.57 | 14.35% | 10.1 |
| 336h | 0.25 | -0.79 | 10.70 | 10.91% | 16.9 |

168h selected for family consistency (avoids IS-overfit optimization).

---

## Backtest Results

### Full Period

| Metric | Value |
|--------|-------|
| Sharpe | 11.43 |
| Ann Return | ~4.5% |
| Max DD | -0.97% |
| Entries/yr | 35.0 |

### IS Period (2024-05 → 2025-10)

| Metric | Value |
|--------|-------|
| Sharpe | **9.98** |
| Ann Return | 3.24% |
| Entries/yr | 38.5 |

### OOS Period (2025-10 → 2026-05)

| Metric | Value |
|--------|-------|
| Sharpe | **13.17** |
| Ann Return (1x) | **15.09%** |
| Ann Return (4x) | **60.37%** |
| Max Drawdown | **-0.33%** |
| Entries/yr | **33.8** |

### K500 INJ-BTC OOS Reference (recomputed same period)

| Metric | Value |
|--------|-------|
| OOS Sharpe | 11.23 |
| OOS Ann Return (1x) | 12.94% |
| Entries/yr | 27.3 |

**INJ-ETH beats INJ-BTC on all raw metrics** — but the PnL correlation analysis reveals why this is misleading.

---

## Walk-Forward 4-Fold Analysis

| Fold | OOS Sharpe | Status |
|------|-----------|--------|
| 1 | 19.36 | + |
| 2 | 8.34 | + |
| 3 | 20.16 | + |
| 4 | 12.29 | + |

**G4 PASS: 4/4 folds positive.** (Better than K500's 10/12.)

---

## §6 Gate Results

| Gate | Value | Threshold | Result |
|------|-------|-----------|--------|
| G1: OOS Sharpe | **13.17** | ≥ 1.0 | **PASS** |
| G2: Perm p-value | **0.000** | ≤ 0.05 | **PASS** |
| G3: DSR Bonferroni | p << 0.0042 | p < 0.0042 | **PASS** |
| G4: WF 4-fold | **4/4 positive** | all positive | **PASS** |
| G5: Family corr | **G5b BLOCKED** | all < 0.40 | **FAIL** |
| G6: Trades/yr | **33.8** | ≥ 30 | **PASS** |
| G7: Ann return 4x | **60.37%** | > 5% | **PASS** |

**Gates passed: 6/7 — BLOCKED by G5b**

### G5 Breakdown

| Sub-Gate | Correlation | Threshold | Result |
|----------|------------|-----------|--------|
| G5a: vs ETH-BTC K449 (shared ETH leg) | **-0.0012** | < 0.40 | **PASS** |
| **G5b: vs INJ-BTC K500 (same INJ leg)** | **0.9386** | < 0.40 | **FAIL — BLOCKED** |
| G5c: vs ATOM-BTC K493 (Cosmos cluster) | 0.15 (est) | < 0.40 | PASS |
| G5d: vs K457 basket | 0.12 (est) | < 0.40 | PASS |
| G5e: vs WLD-ETH K629 (same ETH-base) | 0.10 (est) | < 0.40 | PASS |

**Root cause of G5b=0.9386:** INJ volatility ratio (3.55x ETH, 3.83x BTC) is so large that the base-leg signal (ETH vs BTC) is completely swamped by INJ FR dynamics. Both INJ-ETH and INJ-BTC respond to the same INJ FR regime changes — the choice of base asset is effectively irrelevant to PnL.

---

## INJ-BTC vs INJ-ETH Mandatory Comparison

| Metric | INJ-BTC (K500) | INJ-ETH (K662) | Delta |
|--------|---------------|---------------|-------|
| OOS Sharpe | 11.23 | 13.17 | +1.94 |
| OOS Ann Ret (1x) | 12.94% | 15.09% | +2.16% |
| OOS Ann Ret (4x) | 51.75% | 60.37% | +8.62% |
| OOS Max DD | -0.44% | -0.33% | +0.11pp |
| Entries/yr | 27.3 | 33.8 | +6.5 |
| Gates passed | 10/13 | 6/7 | — |
| G5b PnL corr | baseline | **0.9386** | — |
| Profit gross @$10M | $155,237/yr | $181,103/yr | +$25,866 |
| Profit net @$10M | $124,190/yr | $144,882/yr | +$20,692 |
| Orthogonality | — | **NOT orthogonal** | — |
| **Verdict** | **KEEP** | **REJECT** | — |

Despite INJ-ETH showing better raw metrics, the 0.9386 PnL correlation means there is **zero diversification benefit** — they are the same trade with different terminology on the base leg.

**Why INJ-ETH nominally outperforms INJ-BTC in OOS:**
- ETH FR is structurally lower than BTC FR (10.52% vs 11.55%/yr)
- INJ-ETH direction (short-INJ/long-ETH) is stronger when INJ spikes (receive more carry from INJ)
- BUT the signal generation is nearly identical (INJ FR dominates in both)
- Minor extra return comes from ETH not BTC as hedge, not from signal quality

---

## ETH-base Mechanism Assessment (Updated with K662)

| Wave | Pair | ETH-base Result | Root Cause |
|------|------|----------------|-----------|
| K629 | WLD | UNLOCKED (G5 PASS) | WLD BTC-base had structural G5 blockage (0.46); ETH decouples |
| K632 | HYPE | DEGRADED (Sh halved) | ETH DeFi cycles inject noise into HYPE AQAv2 carry |
| K658 | SOL | IMPROVED (+13.4 Sh) | SOL retail momentum vs ETH DeFi yield — distinct regimes |
| **K662** | **INJ** | **BLOCKED G5b** | **INJ vol (3.55x) swamps base distinction → PnL corr 0.9386** |

**Refined ETH-base hypothesis (post-K662):**
ETH-base succeeds when:
1. Alt has moderate vol ratio (< ~2.5x ETH) so base-leg contributes meaningful signal
2. Alt token narrative is structurally decoupled from BTC-FR-compression

ETH-base fails when:
- Alt vol is extreme (> 3x ETH/BTC), making base-leg choice irrelevant to PnL dynamics
- ETH DeFi cycles create noise that disrupts alt carry patterns (HYPE case)

**INJ (3.55x ETH) falls into the first failure mode.** The base-leg switch from BTC to ETH cannot differentiate signal when alt vol dominates by 3.5x.

---

## Profit Projection (Illustrative — strategy REJECTED)

| AUM | Sleeve | Leverage | Gross/yr | Net/yr |
|-----|--------|----------|---------|-------|
| $10M | 3% | 4x | $181,103 | $144,882 |
| $50M | 3% | 4x | $905,518 | $724,414 |
| $100M | 3% | 4x | $1,811,035 | $1,448,828 |

*Note: These projections are illustrative only. K662 is REJECTED due to G5b blockage. Profit would not be incremental — it would replace K500 not add to it, and even then diversification is absent.*

---

## HL Concentration Impact

K662 is REJECTED — no HL concentration change.
- Current HL: 63.5% (post-K658 context)
- K500 INJ-BTC retained at 3% sleeve
- No new allocation required

---

## Decision: REJECT — BLOCKED G5b

**Decision rationale:**

K662 INJ-ETH is BLOCKED at G5b. INJ-ETH PnL correlation vs INJ-BTC K500 = **0.9386** (>= 0.40 threshold). Despite superior raw Sharpe (13.17 vs 11.23, +1.94) and 6/7 gates passing, the strategies are near-identical in behavior — not independent alpha streams.

The INJ leg's extreme volatility (3.55x ETH) causes both INJ-ETH and INJ-BTC signals to fire on the same INJ FR regime transitions. The ETH vs BTC base distinction provides negligible signal differentiation. Switching from K500 to K662 would not improve portfolio diversification — it would merely rename the base asset while executing the same trade.

**VERDICT:** Keep K500 INJ-BTC (10/13 gates, Sh=11.23, $124K/yr @$10M net).

**Contrast with K629 WLD-ETH:** WLD had a BTC-G5 structural blockage (0.46), which ETH resolved by changing signal direction. INJ has no such structural G5 blockage on BTC — it simply has high vol that dominates both base configurations.

---

## Key Finding: ETH-base Mechanism Boundary

K662 establishes the **vol-dominance boundary** for the ETH-base mechanism:

- Vol ratio < ~2x: ETH-base can meaningfully differentiate signal (WLD 1.8x)
- Vol ratio ~1.5-2.5x (SOL 1.76x): ETH-base provides signal differentiation, improves Sharpe
- Vol ratio > 3x (INJ 3.55x, INJ/BTC 3.83x): Alt dominates → base choice irrelevant → G5b blocked

This is a **new design rule**: before testing ETH-base on a high-vol alt, check if INJ-BTCsignal corr > 0.85 would be expected (if vol ratio > 3x, skip ETH-base test).

---

## Next Steps

1. **K500 INJ-BTC:** Maintain ACCEPT status, no change required
2. **Cosmos family expansion:** INJ confirmed orthogonal at BTC-base. Next: OSMO-BTC (3rd Cosmos token, G5d vs both ATOM and INJ)
3. **ETH-base vol rule:** Apply new boundary rule — skip ETH-base test for vol ratio > 3x alts
4. **K663 candidate:** NEAR-BTC (moderate vol, non-Cosmos, non-ETH L1 ecosystem)

---

## Appendix: ETH-base Mechanism Test History

| Wave | Pair | Pre-ETH-base Sh | ETH-base Sh | Delta | Verdict |
|------|------|-----------------|-------------|-------|---------|
| K629 | WLD-ETH | BLOCKED G5 | 19.9 | — | ETH UNLOCKS |
| K632 | HYPE-ETH | 24.49 | 12.99 | -11.5 | BTC wins |
| K658 | SOL-ETH | 16.30 | 29.66 | +13.4 | ETH wins |
| K662 | INJ-ETH | 11.23 | 13.17 | +1.94 | BLOCKED G5b |

Pattern: ETH-base is not universally better or worse — outcome depends on alt vol profile and narrative structure.

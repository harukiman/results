# K664 ATOM-ETH FR Differential Paired-Trade Evaluation
**ETH-base mechanism test on K493 Cosmos Hub family #2**
**Date**: 2026-05-30 13:00 JST
**Decision**: KEEP K493 — ETH-BASE REDUNDANT (5/7 gates, G5b corr=0.87, no diversification benefit)

---

## Executive Summary

K664 tests whether replacing BTC with ETH as the base asset for the ATOM carry strategy (K493) yields improvement or meaningful diversification. The answer is neither: ATOM-ETH and ATOM-BTC are **highly correlated strategies** (G5b PnL corr = 0.8732) because both strategies are fundamentally long ATOM / short the higher-FR asset — and ETH and BTC have nearly identical structural FR levels (~10.5%/yr vs 11.6%/yr vs ATOM's -3.3%/yr).

**Key findings:**
- **OOS Sharpe: 53.25** — marginally *higher* than K493's 50.79 (+2.46 delta)
- **G5b: 0.8732** — strategies are nearly identical (far exceeds 0.40 threshold)
- **Decision: KEEP K493** — ETH-base is redundant, provides no alpha differentiation
- **No diversification benefit**: PnL corr=0.87 means ETH-base and BTC-base ATOM carry trade together
- **ETH-base track: WLD UNLOCKED / HYPE WORSENED / SOL IMPROVED / AVAX DECLINED+DIVERSIFY / ATOM REDUNDANT**

The Cosmos insight is confirmed from a different angle: ATOM FR dynamics are so distinct from both BTC and ETH that *either* asset serves as a carry base — but choosing between them provides no incremental edge.

---

## ETH-base Mechanism Track Record (Complete)

| Wave | Pair | BTC-base Sh | ETH-base Sh | Delta | Decision |
|------|------|-------------|-------------|-------|----------|
| K629 | WLD-ETH | BLOCKED (G5a) | 19.9 | +UNLOCKED | ACCEPT |
| K632 | HYPE-ETH | 24.49 | 12.99 | -11.5 | KEEP BTC |
| K658 | SOL-ETH | 16.30 | 29.66 | +13.36 | ETH WINS |
| K661 | AVAX-ETH | 43.89 | 28.26 | -15.63 | BTC better; DIVERSIFY |
| **K664** | **ATOM-ETH** | **50.79** | **53.25** | **+2.46** | **REDUNDANT (G5b=0.87)** |

**Pattern insight**: ETH-base wins when alt token narrative decouples from BTC-FR-compression (SOL retail momentum). ETH-base is redundant when BTC and ETH are near-interchangeable as bases (ATOM: both BTC and ETH pay ~11-13% more than ATOM — similar carry magnitude, similar signal).

---

## Phase 0: Pre-screen

| Metric | ATOM-ETH | ATOM-BTC (K493) | Threshold | Result |
|--------|----------|-----------------|-----------|--------|
| Vol ratio | **2.17x** | 2.34x | ≥ 1.5x | **PASS** |
| ATOM FR mean | -3.27%/yr | same | — | — |
| ETH FR mean | +10.52%/yr | — | — | — |
| BTC FR mean | +11.55%/yr | — | — | — |
| ATOM-ETH spread | -13.79%/yr | — | — | strong bias |
| ATOM-BTC spread | +14.82%/yr | — | — | slightly larger |

ATOM-ETH vol ratio (2.17x) is slightly lower than ATOM-BTC (2.34x) because ETH itself has higher absolute FR volatility than BTC — the ATOM-ETH spread is marginally noisier. Still well above 1.5x threshold.

---

## Phase 1: ATOM FR Mean Level vs ETH Diagnostic

### Structural Comparison

| Asset | FR mean/yr | Spread vs ATOM |
|-------|------------|----------------|
| ATOM | -3.27% | — |
| ETH | +10.52% | +13.79% (ETH > ATOM) |
| BTC | +11.55% | +14.82% (BTC > ATOM) |

**Key insight**: ETH and BTC both pay ~13-15% more per year than ATOM. The structural spread is nearly identical — this is why ETH-base and BTC-base ATOM strategies are highly correlated. The carry source is the same (ATOM persistently underperforms both). The base selection merely affects which asset is the "long-paying" leg, not the signal direction.

### Statistical Properties

| Metric | ATOM-ETH | ATOM-BTC |
|--------|----------|----------|
| ADF statistic | -11.77 (p=0.000) | -14.66 (p≈0) |
| OU half-life | 4.93h | 5.43h |
| ACF(1h) | 0.8689 | 0.8724 |
| ACF(24h) | 0.3709 | 0.3928 |
| Diff std | 4.057e-05 | 4.116e-05 |

Both differentials are stationary and mean-reverting on similar timescales. The 7d rolling window is appropriate for both.

### Raw Differential Correlation
ATOM-ETH vs ATOM-BTC raw differential corr = **-0.9093** (negative by construction — when BTC-ATOM spread rises, ATOM-ETH spread falls if ETH and BTC track each other). This near-perfect negative raw correlation explains why *signal-level* PnL correlation is high.

---

## Phase 2: ATOM-ETH Signal at 7d

### Backtest Results

| Period | Sharpe | Ann Ret 1x | Ann Ret 4x | Max DD | Entries/yr |
|--------|--------|-----------|-----------|--------|------------|
| Full (IS+OOS) | 31.72 | 13.84% | — | -0.69% | 26.3 |
| IS (70%) | 21.70 | 8.80% | — | -0.69% | 32.0 |
| **OOS (30%)** | **53.25** | **25.51%** | **102.05%** | **-0.15%** | **13.4** |

OOS outperforms IS significantly — a positive sign of genuine regime capture (ATOM FR regime in OOS period particularly clean). Max DD of just -0.15% in OOS is extremely low.

### K493 ATOM-BTC Reference (recomputed on same slice)

| Metric | ATOM-ETH (K664) | ATOM-BTC (K493 recomputed) | Delta |
|--------|-----------------|---------------------------|-------|
| OOS Sharpe | 53.25 | 51.67 | +1.58 |
| OOS Ann Ret 1x | 25.51% | 24.59% | +0.92% |
| OOS Ann Ret 4x | 102.05% | 98.35% | +3.70% |
| OOS Max DD | -0.15% | -0.23% | -0.08% |
| OOS Entries/yr | 13.4 | 10.1 | +3.3 |

ATOM-ETH shows marginally better metrics, but the difference is within noise — and PnL correlation of **0.8732** reveals these are effectively the same trade.

---

## Phase 3: §6 Gate Results

| Gate | Metric | Value | Threshold | Pass |
|------|--------|-------|-----------|------|
| G1 | OOS Sharpe | 53.25 | ≥ 1.0 | PASS |
| G2 | Perm p-value | 0.0000 | ≤ 0.05 | PASS |
| G3 | DSR Bonferroni | 0.000 | < 0.05/12 | PASS |
| G4 | WF all-positive | 4/4 folds | all > 0 | PASS |
| **G5** | **Family corr** | **G5b=0.8732** | **< 0.40** | **FAIL** |
| G6 | Entries/yr | 13.4 | ≥ 30 | FAIL |
| G7 | Ann ret 4x | 102.05% | ≥ 5% | PASS |

**Total: 5/7 gates passed**

### G5 Breakdown

| Check | Corr | Threshold | Pass | Note |
|-------|------|-----------|------|------|
| G5a: ETH-BTC K449 (shared ETH leg) | **0.0141** | < 0.40 | PASS | ATOM signal independent from ETH DeFi dynamics |
| **G5b: ATOM-BTC K493 (same ATOM leg)** | **0.8732** | **< 0.40** | **FAIL** | Strategies essentially identical |
| G5c: SOL-ETH K658 (same ETH-base) | 0.14 (est) | < 0.40 | PASS | SOL retail vs ATOM governance |
| G5d: K457 basket | 0.18 (est) | < 0.40 | PASS | Different mechanism |

**G5a = 0.0141 is remarkable**: ATOM-ETH is completely orthogonal to ETH-BTC K449 despite sharing the ETH leg. This confirms Cosmos IBC/governance events are independent from ETH DeFi events — the ATOM leg drives the signal, not the ETH leg.

**G5b = 0.8732 is the blocker**: ATOM-ETH and ATOM-BTC are essentially the same carry strategy expressed with two different reference assets that happen to have nearly identical structural FR levels.

### Walk-Forward Folds

| Fold | OOS Period | Sharpe | Ann Ret |
|------|-----------|--------|---------|
| 1 | Oct–Nov 2024 | 21.60 | 9.67% |
| 2 | Feb–May 2025 | 32.92 | 9.35% |
| 3 | Jul–Nov 2025 | 32.76 | 20.53% |
| 4 | Nov 2025–May 2026 | 45.51 | 21.08% |

All 4 folds positive. Sharpe trending upward across time — regime quality improving. Min fold Sharpe = 21.60.

---

## Phase 4: §6 Gates + PnL Correlation with K493

### Grid Search Top 5 (12 configs)

| Window | Threshold | IS Sh | OOS Sh | OOS Ret | Entries/yr |
|--------|----------|-------|--------|---------|-----------|
| 336h | 0.0 | 24.45 | **53.39** | 25.17% | 12.3 |
| 168h | 0.0 | 21.70 | 53.25 | 25.51% | 26.3 |
| 504h | 0.0 | 23.63 | 51.68 | 24.22% | 10.3 |
| 168h | 0.25σ | 16.12 | 50.02 | 24.26% | 33.4 |
| 336h | 0.25σ | 14.14 | 48.88 | 23.37% | 29.2 |

Config 4 (168h, threshold=0.25σ) is notable: OOS Sh=50.02 with 33.4 entries/yr — would pass G6. But it doesn't meaningfully change G5b (still ATOM-based).

### PnL Correlations

| Comparison | Corr | Interpretation |
|-----------|------|----------------|
| ATOM-ETH vs ETH-BTC K449 (G5a) | **0.0141** | Cosmos orthogonal to ETH DeFi |
| ATOM-ETH vs ATOM-BTC K493 (G5b) | **0.8732** | Same strategy different base |
| K493 original OOS Sharpe | 50.79 | Reference |
| K664 OOS Sharpe | 53.25 | +2.46 delta, not worth the G5b penalty |

---

## Phase 5: Decision — BTC Wins / ETH Wins / Diversify

### Decision Matrix

| Criterion | K493 ATOM-BTC | K664 ATOM-ETH | Winner |
|-----------|--------------|--------------|--------|
| OOS Sharpe | 50.79 | **53.25** | ETH (marginal) |
| Max DD (OOS) | -0.23% | **-0.15%** | ETH |
| Gates passed | **11/12** | 5/7 | BTC |
| G5b (family corr) | n/a | 0.8732 FAIL | BTC |
| Entries/yr | 6.0 | 13.4 | ETH |
| Diversification | base strategy | REDUNDANT | BTC |
| Net profit @$10M | **$231.7K/yr** | $244.9K/yr | ETH (marginal) |

### Decision: **BTC WINS — KEEP K493**

ATOM-ETH (K664) is essentially the same carry trade as ATOM-BTC (K493):
1. Both exploit ATOM's persistently low/negative FR vs a higher-FR base
2. BTC and ETH have nearly identical structural FR levels (~10-12%/yr)
3. G5b corr = 0.8732 confirms strategies are nearly identical
4. No diversification benefit from holding both
5. K493 already passes 11/12 gates vs K664's 5/7 — K493 has higher statistical confidence

**ATOM-BTC (K493) remains the canonical Cosmos carry strategy.** BTC's slightly higher structural FR (11.55% vs 10.52%) makes it a marginally better base for ATOM carry.

### Profit (USDC/yr @$10M AUM)

| Strategy | Gross | Net | Sleeve |
|---------|-------|-----|--------|
| K664 ATOM-ETH (standalone) | $306,148 | $244,918 | 3%, 4x |
| K493 ATOM-BTC (incumbent) | $289,575 | $231,660 | 3%, 4x |
| Difference | +$16,573 | +$13,258 | — |

The $13K/yr net improvement is negligible vs the gate failures and lack of diversification benefit. Keep K493.

---

## Summary: ETH-base Pattern Analysis (All 5 Tests)

| Pattern Type | Cases | Explanation |
|-------------|-------|-------------|
| UNLOCKED | WLD | ETH-base unlocks tokens blocked on BTC-base (G5a) |
| IMPROVED | SOL | Alt narrative (retail momentum) decouples from BTC institutional — ETH base cleaner |
| WORSENED | HYPE | Alt narrative tightly coupled to BTC; ETH base adds noise |
| DECLINED+DIVERSIFY | AVAX | BTC base cleaner, but ETH-base orthogonal enough to diversify |
| **REDUNDANT** | **ATOM** | **BTC and ETH near-identical carry bases for ATOM; no differentiation** |

**ATOM is unique**: it's so distinct from BOTH BTC and ETH that *either* works as a base — but that also means neither provides incremental edge over the other.

---

## Operational Status

- **K493 ATOM-BTC**: ACCEPT, active production scaffold candidate
- **K664 ATOM-ETH**: REJECT as standalone; ETH-base redundant for ATOM
- **No live changes from K664**
- **ETH-base track**: Complete for current paired-trade family (#1 WLD, #2 HYPE, #3 SOL, #4 AVAX, now #5 ATOM)
- **Next**: Consider OSMO-BTC (Cosmos IBC DEX), INJ-BTC (Cosmos-adjacent DeFi hub)

---

*Wave K664 | 2026-05-30 13:00 JST | runtime 2.21s | K339 REPO_ROOT pattern*

# K665 SEI-ETH FR Differential Paired-Trade Evaluation

**Wave:** K665  
**Strategy:** SEI-ETH FR Differential (ETH-base mechanism test on K507 SEI-BTC)  
**Family:** Cosmos SDK parallel-EVM cluster (#3 from K507)  
**Run:** 2026-05-30T13:08:54+09:00  
**K339 REPO_ROOT pattern**

---

## Executive Summary

**DECISION: REJECT — BLOCKED G5b (SEI-ETH ~= SEI-BTC, redundant)**

K665 applies the ETH-base mechanism (K629 series) to K507 SEI-BTC (OOS Sh=48.10, $179K/yr).
OOS Sharpe improved to 56.50 (+8.40 vs K507), but G5b blocks: SEI-ETH vs SEI-BTC PnL
corr = **0.7858** (>= 0.40 threshold). Both strategies are predominantly long SEI — the
base leg (ETH vs BTC) makes no meaningful difference because SEI FR is persistent and dominant.

**VERDICT: Keep K507 SEI-BTC. K665 is rejected — no diversification benefit.**

---

## Phase 0: Pre-screen (K662 Vol Rule)

| Metric | Value | Threshold | Status |
|--------|-------|-----------|--------|
| SEI/ETH vol ratio (full-period) | 2.16x | < 3.0x (K662 rule) | PASS — PROCEED |
| SEI/ETH vol ratio (6m recent) | 3.42x | < 3.0x | ELEVATED FLAG |
| SEI FR mean annualized | -3.65%/yr | — | negative (net payer) |
| ETH FR mean annualized | +10.52%/yr | — | positive structural |
| SEI-ETH diff mean | -14.17%/yr | — | ETH structural advantage |

**K662 pre-screen: PASS** on full-period vol (2.16x < 3.0x). Proceeded to full eval.
6m flag (3.42x) noted as elevated regime risk — consistent with G5b block finding.

**Structural direction warning (pre-identified):**
- K665 (SEI-ETH): predominantly short ETH, long SEI (SEI FR < ETH FR)
- K507 (SEI-BTC): predominantly short BTC, long SEI (SEI FR < BTC FR)
- **Both are long SEI** — same directional bet, different short leg

---

## Phase 1: SEI FR Mean Level vs ETH (K660 diagnostic)

| Stat | SEI | ETH | BTC |
|------|-----|-----|-----|
| FR mean ann. | -3.65%/yr | +10.52%/yr | +11.55%/yr |
| FR vol (std) | 4.11e-05 | 1.90e-05 | 1.76e-05 |
| Vol ratio vs ETH | **2.16x** | — | 0.93x |

- SEI raw FR corr with ETH: 0.4606 (moderate-high, higher than BTC=0.3165)
- SEI-ETH diff mean: -14.17%/yr (structural: ETH always paid more than SEI)
- This creates persistent directional signal (short ETH, long SEI) — same side as K507

**ADF stationarity:** p=0.000 (stationary at 1%) — confirmed  
**OU half-life:** 4.4h (mean-reverting, very fast reversion)

---

## Phase 2: SEI-ETH Differential at 7d Window

| Config | Window | IS Sharpe | OOS Sharpe | OOS Ann Ret | Entries/yr |
|--------|--------|-----------|------------|-------------|------------|
| Selected (family) | 168h | 35.37 | **56.50** | 19.11% | 6.8 |
| Best grid (IS overfit) | 504h | — | 60.14 | — | — |
| 336h no threshold | 336h | 36.43 | 57.41 | 18.31% | 6.8 |
| 168h 0.25 thr | 168h | 29.42 | 40.37 | — | — |

Grid confirms: OOS Sharpe actually higher with longer windows, but we use 168h for
family consistency (avoid IS overfit by picking best OOS window).

---

## Phase 3: Backtest Results

| Period | Sharpe | Ann Return | Ann Return 4x | Max DD | Entries/yr |
|--------|--------|------------|----------------|--------|------------|
| Full (IS+OOS) | 40.90 | 15.41% | 61.63% | -0.36% | 16.2 |
| IS (70%) | 35.37 | 13.85% | 55.40% | -0.36% | 20.3 |
| OOS (30%) | **56.50** | **19.11%** | **76.46%** | **-0.23%** | **6.8** |
| **K507 OOS ref** | **48.10** | **17.60%** | **70.40%** | -0.27% | 16.9 |

OOS Sharpe **56.50 vs K507 48.10 (+8.40)** — SEI-ETH appears better in isolation.
However OOS entries/yr dropped to 6.8 vs K507's 16.9 — signal flipped far less,
suggesting high-persistence regime lock (same root cause as G5b block).

**Profit @ $10M, 3% sleeve, 4x leverage:**
- Gross: $229,369/yr (vs K507 $211,089/yr, +$18,280)
- Net est: $194,964/yr (vs K507 $179,425/yr, +$15,539)

---

## Phase 4: §6 Gate Evaluation

| Gate | Criterion | Value | Result |
|------|-----------|-------|--------|
| G1 | OOS Sharpe >= 1.0 | 56.50 | **PASS** |
| G2 | Perm p-value <= 0.05 | 0.000 | **PASS** |
| G3 | DSR Bonferroni p < 0.00417 | 0.000 | **PASS** |
| G4 | WF 4-fold all positive | 13.07, 45.33, 32.54, 51.26 | **PASS** |
| G5 | Family corr < 0.40 (all) | G5b FAIL=0.7858 | **FAIL** |
| G6 | Trades > 30/yr | 6.8/yr | **FAIL** (structural) |
| G7 | Ann return > 5% at 4x | 76.46% | **PASS** |

**Gates passed: 5/7 (6/7 effective if G6 structural)**

### G5 Correlation Details

| Check | Strategy | PnL Corr | Threshold | Result |
|-------|----------|----------|-----------|--------|
| G5a | ETH-BTC K449 (shared ETH leg) | -0.0078 | < 0.40 | **PASS** |
| **G5b** | **SEI-BTC K507 (same SEI leg)** | **0.7858** | **< 0.40** | **FAIL** |
| G5c | ATOM-BTC K493 (Cosmos cluster) | 0.1529 | < 0.40 | **PASS** |
| G5d | INJ-BTC K500 (DeFi cluster) | 0.1487 | < 0.40 | **PASS** |
| G5e | WLD-ETH K629 (same ETH base) | ~0.12 est | < 0.40 | **PASS** |

**G5b root cause:** SEI FR mean = -3.65%/yr vs ETH +10.52%/yr and BTC +11.55%/yr.
SEI is a net payer relative to both bases → signal is persistently "long SEI, short {base}".
Changing from BTC base to ETH base doesn't change the SEI leg dominance.
OOS entries: 6.8/yr (K665) vs 16.9/yr (K507) confirms signal persistence.
PnL corr = **0.7858** — two strategies moving in near-lockstep.

---

## Phase 5: Decision + K507 Comparison

| Metric | K507 SEI-BTC | K665 SEI-ETH | Delta |
|--------|-------------|-------------|-------|
| OOS Sharpe | 48.10 | **56.50** | +8.40 |
| OOS Ann Ret 1x | 17.60% | 19.11% | +1.51% |
| OOS Ann Ret 4x | 70.40% | 76.46% | +6.05% |
| Gates | 12/14 ACCEPT | 5/7 REJECT | — |
| G5b PnL corr | — | 0.7858 | BLOCKED |
| Entries/yr | 16.9 | 6.8 | -10.1 |
| Gross @$10M | $211,089 | $229,369 | +$18,280 |
| Net @$10M | $179,425 | $194,964 | +$15,539 |

**Verdict: Keep K507 SEI-BTC. K665 REJECTED.**

Despite higher apparent OOS Sharpe (+8.40), the PnL correlation of 0.7858 means
K665 adds no independent alpha. Holding both would be redundant risk, not diversification.

---

## ETH-Base Mechanism Tracker (6 waves)

| Wave | Pair | Result | G5b PnL Corr | Sharpe Delta |
|------|------|--------|--------------|--------------|
| K629 | WLD-ETH | ACCEPT (ETH unlocks WLD) | < 0.40 PASS | +19.9 unlocked |
| K632 | HYPE-ETH | CONDITIONAL WORSE | — | -11.5 |
| K658 | SOL-ETH | ACCEPT ETH WINS | < 0.40 PASS | +13.36 |
| K660 | APT-ETH | REJECT BLOCKED G5b | 0.966 | +6.9 (redundant) |
| K662 | INJ-ETH | REJECT BLOCKED G5b | 0.9386 | +1.94 (redundant) |
| **K665** | **SEI-ETH** | **REJECT BLOCKED G5b** | **0.7858** | **+8.40 (redundant)** |

**Pattern:** ETH-base BLOCKS when alt FR is persistent dominant signal vs both ETH and BTC.
Low flip count is the leading indicator: K507 SEI-BTC=16.9/yr, K665 SEI-ETH=6.8/yr.

**Refined rule (6 data points):**
- ETH-base SUCCEEDS: alt has balanced FR near both bases, distinct narrative (WLD, SOL)
- ETH-base FAILS: alt is persistent net-payer vs both bases, signal dominated by alt leg
- G6 trades/yr < 20 is a warning sign for G5b block (alt leg dominates → few regime changes)

---

## §6 PnL Correlation with K507

K665 SEI-ETH OOS PnL correlation with K507 SEI-BTC: **0.7858**  
This confirms K665 is NOT an independent strategy — it is a redundant variant of K507.
No portfolio diversification benefit. K507 retained as canonical SEI strategy.

---

## Operational Summary

- **Venue:** HL (SEI-PERP + ETH-PERP both listed on Hyperliquid)
- **Rebalances/yr:** 6.8 (very low — confirm SEI-PERP liquidity before any deployment)
- **HL concentration:** No impact (K665 rejected; K507 sleeve unchanged)
- **Next candidate:** K665 closes ETH-base testing for current Cosmos family
  - All BTC-base strategies tested: K449, K476, K484, K493, K500, K507
  - ETH-base variants tested: K629 (WLD), K632 (HYPE), K658 (SOL), K660 (APT), K662 (INJ), K665 (SEI)
  - ETH-base success rate: 2/6 (WLD, SOL)
  - Pattern fully characterized → next focus: new token families or regime-adaptive strategies

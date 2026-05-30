# K799 ETH-COMP FR Differential Evaluation

**Strategy:** ETH-COMP FR Differential (cross-base non-SOL, ETH L1 vs COMP DeFi governance)  
**Wave:** K799 | **Generated:** 2026-05-31 02:26 JST | **K339 REPO_ROOT pattern**  
**Verdict:** REJECT — G5v CLUSTER FAIL (COMP-SOL K778 corr = -0.9754)

---

## Executive Summary

ETH-COMP was proposed as the **first cross-base non-SOL direction** after 22-vertex SOL-pivot saturation. The strategy shows strong quantitative metrics (OOS Sharpe 25.09, WF 12/12 positive), but **fails G5 cluster screening** due to near-perfect anti-correlation with K778 (COMP-SOL): the existing ACCEPT pair.

**Primary rejection reason:** ETH-COMP is functionally the inverse of COMP-SOL because the COMP FR dominates both signals. The COMP FR standard deviation is 5.97x that of ETH FR — meaning the ETH vs SOL base difference is secondary noise.

---

## Phase 0: Pre-screens

### MR9: Algebraic Independence Check

| Comparison | Signal Corr | Algebraically Identical? | MR9 Status |
|------------|------------|--------------------------|------------|
| ETH-COMP vs K449 (ETH-BTC) | 0.0823 | No (COMP ≠ BTC) | CLEAR |
| ETH-COMP vs K778 (COMP-SOL) | -0.9754 | No (ETH ≠ SOL) | CLEAR algebraically |
| ETH-COMP vs K449-K778 combo | — | No (BTC, SOL terms remain) | CLEAR |

**MR9 Verdict: ALGEBRAICALLY CLEAR** — no linear combination of existing pairs exactly reproduces ETH-COMP.

**Critical distinction:** MR9 checks algebraic identity (floating-point equality). G5 checks execution-level cluster overlap. ETH-COMP passes MR9 but fails G5v because functional substitutability (ETH ≈ SOL as base leg when COMP FR dominates) creates near-perfect anti-correlation at signal level.

### L003/L004/L004_DIFF/L007/L010 Pre-screens

| Check | Value | Threshold | Status |
|-------|-------|-----------|--------|
| L003 AVAX: ETH×AVAX | — | <0.45 | PASS |
| L003 AVAX: diff×AVAX | — | <0.45 | PASS |
| L004 ETH carry (full/OOS) | — | Both <80% | PASS |
| L004 COMP carry (full/OOS) | — | Both <80% | PASS (K778 confirmed OOS=50.1%) |
| **L004_DIFF full** | **0.4702** | [0.30, 0.70] | **PASS** |
| **L004_DIFF OOS** | **0.5504** | [0.30, 0.70] | **PASS** |
| L007 FIL-SOL overlap | — | <0.40 | PASS |
| L010 HBAR contamination | — | <0.45 | PASS |

**L004_DIFF Note:** Pure carry IS Sharpe = -13.19 (shorting COMP has negative carry). Signal IS Sharpe = 14.49. Timing adds **+27.68 Sharpe points** — genuine timing alpha, NOT carry-contaminated.

---

## Phase 1: Vol Pre-screen + Cycle Analysis

| Metric | Value | Status |
|--------|-------|--------|
| vol_ratio(COMP/ETH) | **5.97x** | PASS (≥1.5x) |
| ETH FR std | 0.30 bps | — |
| COMP FR std | 1.79 bps | — |
| ETH-COMP diff std | — | — |
| ETH-COMP mean | — | — |
| raw_corr(ETH, COMP) | ~0.09 | Low (independent) |

### ETH Narrative Cycles
- ETH ETF approval (Jan-May 2024) → institutional perpetual demand spikes
- Dencun upgrade / EIP-4844 (Mar 2024) → L2 cost reduction, ETH demand shift
- ETH staking yield vs leverage premium oscillation (Lido APY cycles)
- ETH spot ETF launch (US SEC, July 2024) → institutional FR pressure

### COMP Narrative Cycles
- Compound v3 (Comet) migration governance votes
- COMP reward distribution epoch changes (biweekly)
- Protocol competition: Aave v3 vs Compound III TVL battles
- COMP fee switch governance discussions → token repricing events

**Cross-ecosystem independence:** ETH L1 base layer vs COMP DeFi application governance — distinct FR mechanisms confirmed by low raw_corr(ETH, COMP) ≈ 0.09.

---

## Phase 2: IS/OOS Backtest (W=84h canonical)

| Period | Sharpe | Ann Ret (1x) | Ann Ret (4x) | Max DD | Entries/yr |
|--------|--------|-------------|-------------|--------|------------|
| IS | 14.49 | — | — | — | 22.9 |
| **OOS** | **25.09** | **33.10%** | **132.4%** | **-0.13%** | **31.2** |
| Full | — | — | — | — | 21.3 |

| Window | IS Sh | OOS Sh | OOS entries/yr |
|--------|-------|--------|----------------|
| W=48h | 14.34 | 25.01 | 59.0 |
| **W=84h (canonical)** | **14.49** | **25.09** | **31.2** |
| W=168h | 13.79 | 24.84 | 17.3 (fails G6) |

---

## Phase 3: Grid Search + DSR Bonferroni

- **Best config:** W=84h, T=0 → OOS Sh=25.09, 31.2/yr
- **DSR Bonferroni:** t=19.05, p_bonf≈0.0 (12 configs) → PASS
- All grid configs show OOS Sh > 20 — consistent signal

---

## Phase 4: Walk-Forward (12 folds)

**Result: 12/12 positive folds** — min Sh = 14.21, mean Sh = 38.23

All walk-forward folds positive across the full 2-year IS period. Strong temporal stability of the underlying COMP FR dynamics.

---

## Phase 5: §6 Gate Results

| Gate | Metric | Value | Pass? |
|------|--------|-------|-------|
| G1 OOS Sharpe | OOS Sh | 25.09 | ✓ |
| G2 Permutation | p-value | 0.002 | ✓ |
| G3 DSR Bonferroni | p_bonf | ≈0.0 | ✓ |
| G4 Walk-Forward | 12/12 positive | min Sh=14.21 | ✓ |
| **G5 Family Corr** | **G5v = -0.9754** | **>>0.40** | **✗ FAIL** |
| G6 Trade Count | 31.2/yr | ≥30 | ✓ |
| G7 Ann Return | 132.4% @4x | ≥5% | ✓ |
| G8 Cross-venue | ETH+COMP on HL/OKX/Bybit | confirmed | ✓ |
| G9 Data | OOS days | ~216d | ✓ |

**Gate summary: 8/9 PASS, 1 FAIL (G5)**

### G5 Critical Pairs

| Gate | Pair | Full Corr | Status |
|------|------|-----------|--------|
| G5a | K449 ETH-BTC | 0.0823 | PASS |
| G5q | K721 LDO-SOL (ETH-DeFi cluster) | -0.0313 | PASS |
| **G5v** | **K778 COMP-SOL** | **-0.9754** | **FAIL** |
| G5ac | K698 LINK-ETH | -0.0723 | PASS |

**All 29 other G5 gates: PASS** (max = 0.0823). The G5v failure is COMP-specific and severe.

---

## Phase 6: Decision

### REJECT — G5v CLUSTER FAIL

**Primary reason:** ETH-COMP vs K778 (COMP-SOL) signal correlation = -0.9754 (IS = -0.9604, OOS = -0.9940).

This is not a borderline case — it's a near-perfect anti-correlation indicating **functional equivalence** between ETH-COMP and the inverse of COMP-SOL.

**Mechanistic explanation:**
- COMP FR std = 5.97x ETH FR std
- COMP FR dominates the differential in both ETH-COMP = ETH_FR - COMP_FR and COMP-SOL = COMP_FR - SOL_FR
- When COMP FR spikes → both strategies fire simultaneously (in opposite notional directions but same P&L direction)
- ETH vs SOL FR difference is secondary noise overwhelmed by COMP volatility

**MR9 lesson:** Algebraic independence (MR9 CLEAR) is necessary but NOT sufficient. G5 cluster screening catches functional substitutability that MR9 misses. This is distinct from K698 (LINK-ETH vs K449 ETH-BTC) where MR9 CLEAR + G5 PASS both hold — K698 passed because LINK FR ≠ BTC FR in magnitude.

### K523 3-point ROI (for record — NOT viable due to G5v)

| Scenario | USD/yr @$10M (1% sleeve, 4x) |
|----------|------------------------------|
| Conservative (×0.38) | $50,304 |
| Mid (×0.60) | $79,428 |
| Optimistic (×0.85) | $112,524 |
| Upper bound (raw OOS) | $132,381 |

*These numbers are academic — the strategy cannot be traded independently of K778 COMP-SOL.*

### Vertex count: **22 unchanged**

---

## K799 Lesson: COMP Leg Dominance Rule

> **When a proposed pair shares a leg with an existing accepted pair, and that shared leg has FR volatility ≫ the new base leg, the G5 cluster corr will approach ±1 regardless of algebraic independence.**

**COMP FR std (1.79 bps) ≫ ETH FR std (0.30 bps) → COMP dominates → ETH-COMP ≈ inverse(COMP-SOL)**

### Future cross-base non-SOL candidates

The concept of cross-base non-SOL pairs is valid, but the base must be a token NOT already in the vertex set with high FR volatility. Viable candidates:

1. **ETH-LDO**: LDO not in vertex set as standalone. But G5q (LDO-SOL) exists — check vol_ratio(ETH/LDO).
2. **ETH-AAVE**: AAVE blocked by L004 (carry-stable 86%). K748 lesson applies.
3. **BTC-ETH** (reversed): Covered by K449 (ETH-BTC). Inverse = same trade.
4. **ATOM-ETH**: ATOM is in vertex set. G5d/G5i overlap likely.
5. **New non-vertex base tokens**: Tokens with high FR vol NOT yet in the 22-vertex family.

**Key screening criterion for cross-base pairs:**
- BOTH legs must have comparable FR volatility (vol_ratio ≤ 5x for independence)
- OR: the lower-vol leg must be a BASE token (BTC/SOL/ETH) with strong narrative independence

---

## Files

- `wave_k799_eth_comp_eval.py` — Full evaluation script (~500 LOC, K339)
- `wave_k799_eth_comp_eval.json` — Machine-readable results
- `wave_k799_eth_comp_eval.md` — This document
- `report.html` — Badge added (REJECT)

**K339 compliance:** REPO_ROOT = `/Users/nekonaomichi/crypto-lab` (redacted in public commits)

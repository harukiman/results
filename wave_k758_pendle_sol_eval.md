# K758 PENDLE-SOL FR Differential Eval — Wave Report

**Wave:** K758
**Pair:** PENDLE-SOL (yield-trading DeFi vs Solana SVM)
**Date:** 2026-05-30
**Decision:** BLOCKED-L004-G5q

---

## Executive Summary

K758 evaluates PENDLE (Ethereum yield-trading DeFi protocol — PT/YT tokens, sUSDe/ENA yield wars) vs SOL (Solana SVM) as a new alt-alt vertex candidate. PENDLE ranked highly in the K744 saturation map (vol_ratio_SOL=1.106x, cycle_indep=0.807, score 1.519 — 15th vertex candidate).

**BLOCKED** on two independent structural grounds:

1. **L004 carry-stable (hard block):** PENDLE FR > 0 in 90.2% (full) and 86.9% (OOS) — BOTH exceed 80% threshold. Yield-trading protocol identical carry mechanism to AAVE (K748 L004 BLOCKED). Fixed-yield demand (PT buyers) creates structural positive FR bias → carry trade, not genuine FR differential alpha.

2. **G5 family cluster (3 fails):** G5q LDO-SOL (full=0.4166), G5s HBAR-SOL (full=0.5071), G5u FIL-SOL (full=0.4232) — all exceed 0.40 threshold at canonical W=48h. ETH DeFi yield cluster collinearity confirmed.

OOS Sharpe = 58.55 (W=48h, for record) and all 12 walk-forward folds positive — but results are structurally invalid given carry contamination.

---

## Pre-Screen Results (Phase 0)

| Check | Value | Threshold | Result |
|-------|-------|-----------|--------|
| MR9 algebraic (PENDLE ∉ V) | max_err=2.332e-03 (APT) | > 1e-8 | CLEAR |
| L003 AVAX corr (K746) | 0.3307 | < 0.45 | PASS |
| **L004 carry-stability full** | **90.2% positive** | **< 80%** | **WARN** |
| **L004 carry-stability OOS** | **86.9% positive** | **< 80%** | **WARN → HARD BLOCK** |
| L007 FIL-SOL pre-screen (K749) | 0.3773 | < 0.40 | PASS (marginal) |
| L010 HBAR corr (K752) | 0.3966 | < 0.45 | PASS |

**L004 hard block (K748 rule):** BOTH full-period AND OOS fraction exceed 80% threshold. This is the structural BLOCK condition. PENDLE yield-trading protocol extracts carry from DeFi capital flows — identical mechanism to AAVE lending. Fixed-yield demand (PT buyers purchase at discount vs par) creates persistent long positioning → structural positive FR regardless of market phase.

**L007 marginal:** FIL-SOL pre-screen corr=0.3773 passes at W=168h. G5u (FIL-SOL) fails at canonical W=48h (0.4232) due to increased signal sensitivity at shorter window.

---

## Phase 1: Vol Pre-Screen + Cycle Analysis

- **Vol ratio PENDLE/SOL:** 1.1061x (K744 stated 1.106x — CONFIRMED)
- **K744 cycle_indep:** 0.807 — high (yield-trading cycles vs SVM cycles diverge on paper)
- **PENDLE FR mean:** 0.1441 bps/hr (vs SOL 0.0882 bps/hr) — structural carry premium

### Quarterly FR Comparison (PENDLE vs SOL mean bps/hr)

| Quarter | PENDLE mean (bps) | SOL mean (bps) | Differential |
|---------|-------------------|-----------------|--------------|
| Q2 2024 | +0.107 | +0.215 | -0.108 (SOL leads — SVM season) |
| Q3 2024 | -0.005 | +0.109 | -0.114 (SOL leads) |
| Q4 2024 | +0.427 | +0.341 | +0.086 (PENDLE leads — DeFi yield season) |
| Q1 2025 | +0.127 | +0.041 | +0.086 |
| Q2 2025 | +0.111 | +0.044 | +0.068 |
| Q3 2025 | +0.231 | +0.163 | +0.068 |
| Q4 2025 | +0.093 | -0.007 | +0.101 |
| Q1 2026 | +0.071 | -0.089 | +0.160 |
| Q2 2026 | +0.092 | +0.017 | +0.075 |

**Carry-stable pattern visible:** PENDLE leads SOL in almost every recent quarter. The pattern reflects PENDLE's structural positive FR bias (yield-trading carry), not genuine mean-reversion signal. SOL bears the negative FR (cascade events), while PENDLE remains positive.

### FR Tail Risk

| Metric | PENDLE | SOL |
|--------|--------|-----|
| Min (bps) | -23.44 | -20.51 |
| Max (bps) | +6.29 | +1.84 |
| P1 (bps) | -0.476 | -0.510 |
| P99 (bps) | +1.243 | +0.932 |
| Mean (bps) | +0.144 | +0.088 |
| Std (bps) | +0.344 | +0.311 |

---

## Phase 2: Backtest (IS/OOS split, W=168h → W=48h)

| Window | IS Sh | OOS Sh | entries/yr | G6 |
|--------|-------|--------|------------|----|
| W=168h | 19.51 | 56.65 | 6.9 | FAIL |
| W=84h | 19.81 | 57.63 | 27.8 | FAIL |
| **W=48h** | **21.92** | **58.55** | **48.6** | **PASS** |

Canonical window: **W=48h** (first G6-compliant window). OOS period: 2025-10-26 to 2026-05-23 (210 days).

Note: High OOS Sharpe (58.55) is structurally inflated by carry contamination — PENDLE perpetually positive FR creates asymmetric signal vs SOL's variable/negative FR.

---

## Phase 3: Grid Search (4×3=12 configs)

- Best OOS config: W=48h T=2e-6, Sh=58.94
- Best G6-compliant: W=48h, Sh=58.55-58.94
- DSR Bonferroni: t=25.93, p_bonf≈0.000 — PASS (IS period robust)

Grid search shows consistent high OOS Sharpe across all tested windows — further evidence the signal captures structural carry premium, not cycle-based alpha.

---

## Phase 4: Walk-Forward 12-Fold (G4)

All 12 folds positive (min Sh=25.89, max Sh=62.41, W=48h):

| Fold | Period | Sharpe | Ann Ret |
|------|--------|--------|---------|
| 1 | 2024-08-30 to 2024-09-29 | 26.53 | 7.88% |
| 2 | 2024-09-29 to 2024-10-29 | 35.50 | 4.73% |
| 3 | 2024-10-29 to 2024-11-28 | 25.89 | 8.65% |
| 4 | 2024-11-28 to 2024-12-28 | 54.42 | 22.38% |
| 5 | 2024-12-28 to 2025-01-27 | 35.79 | 8.32% |
| 6 | 2025-01-27 to 2025-02-26 | 50.70 | 10.42% |
| 7 | 2025-02-26 to 2025-03-28 | 47.98 | 8.05% |
| 8 | 2025-03-28 to 2025-04-27 | 42.88 | 10.25% |
| 9 | 2025-04-27 to 2025-05-27 | 38.70 | 5.45% |
| 10 | 2025-05-27 to 2025-06-26 | 62.41 | 7.31% |
| 11 | 2025-06-26 to 2025-07-26 | 40.03 | 9.34% |
| 12 | 2025-07-26 to 2025-08-25 | 31.61 | 5.34% |

G4 technically PASS — but 12/12 folds consistently positive is itself a flag for carry-stable strategies (the signal is always "long PENDLE-short SOL" which profits from PENDLE's structural positive carry).

---

## Phase 5: §6 Gates Summary

| Gate | Value | Threshold | Result |
|------|-------|-----------|--------|
| G1 OOS Sharpe | 58.55 | ≥ 1.0 | PASS |
| G2 Perm p-value | 0.000 | ≤ 0.05 | PASS |
| G3 DSR Bonferroni | p≈0.000 | < 0.0042 | PASS |
| G4 Walk-forward | 12/12 positive | all positive | PASS |
| **G5 Family corr** | **max=0.5071 (G5s)** | **< 0.40** | **FAIL (3 gates)** |
| G6 Trade count | 48.6/yr | ≥ 30 | PASS |
| G7 4x Ann Return | 41.15% | > 5% | PASS |
| G8 Cross-venue | HL only | conditional | COND PASS |
| G9 OOS days | 210 | ≥ 180 | PASS |

### G5 Failed Gates Detail

| Gate | Full corr | IS corr | OOS corr | Verdict |
|------|-----------|---------|----------|---------|
| G5q — LDO-SOL | **0.4166** | 0.3669 | 0.5346 | FAIL |
| G5s — HBAR-SOL | **0.5071** | 0.5222 | 0.3621 | FAIL |
| G5u — FIL-SOL | **0.4232** | 0.4357 | 0.3438 | FAIL |

**G5q (LDO-SOL) interpretation:** PENDLE (yield-trading) and LDO (liquid staking) are both ETH DeFi yield protocols — they share the same capital flow source (ETH yield seekers). Signal overlap at all windows (W=48: 0.4166, W=84: 0.4637, W=168: 0.4486). Per `feedback_meta_narrative_cluster_rule`: meta-narrative overlap (ETH DeFi yield cluster) is a stronger reject signal than G5 alone.

**G5s (HBAR-SOL) / G5u (FIL-SOL):** Additional SOL-beta cluster contamination — PENDLE-SOL signal at W=48h overlaps with both HBAR-SOL and FIL-SOL reference signals. Multiple cluster failures reinforce BLOCKED verdict.

---

## Phase 6: Decision

### Final Decision: BLOCKED-L004-G5q

**Two independent hard-block conditions:**

**Block 1 — L004 (yield-protocol carry-stable):**
- PENDLE_FR > 0: 90.2% (full) and 86.9% (OOS) — both exceed 80% threshold
- Yield-trading protocol category: PENDLE extracts carry from DeFi capital via PT/YT mechanics
- Identical mechanism to AAVE lending (K748 L004 BLOCKED): lending vs yield-trading both extract carry
- Structural positive FR regardless of market regime → carry trade, not genuine alpha

**Block 2 — G5 cluster overlap (3 gates failed):**
- G5q LDO-SOL: 0.4166 full (ETH DeFi yield cluster)
- G5s HBAR-SOL: 0.5071 full (SOL-beta cluster)
- G5u FIL-SOL: 0.4232 full (SOL-beta cluster)
- Meta-narrative overlap (ETH yield cluster) confirmed per K748/K749 lessons

### K523 3-Point ROI (for record — BLOCKED, not actionable)

| Scenario | Haircut | Annual P&L |
|----------|---------|-----------|
| Conservative | ×0.38 | $39,053/yr |
| Mid | ×0.65 | $66,820/yr |
| Optimistic | ×0.90 | $92,504/yr |

Base: OOS ret=10.28% @ 4x leverage × $250K notional. Figures are THEORETICAL — L004 carry contamination means actual live performance structurally lower.

---

## New Lessons Recorded (K758)

1. **Yield-trading protocol category (L004):** PENDLE is the second DeFi yield protocol blocked by L004 (after AAVE K748). Category rule: any DeFi protocol whose primary mechanism is yield extraction (lending, borrowing, fixed-yield trading, yield optimization) will fail L004 due to structural positive FR bias. Future candidates: CURVE, CONVEX, BALANCER — all expected to fail.

2. **ETH DeFi yield cluster (G5q):** PENDLE (yield-trading) + LDO (liquid staking) confirmed collinear at all windows. Both protocols capture ETH yield capital flows. The cluster is: PENDLE/CURVE/CONVEX + LDO/RPL/FXS → same source capital.

3. **Carry contamination inflates metrics:** OOS Sh=58.55, 12/12 WF folds positive, DSR p≈0 — all indicators suggest strong alpha. But this is carry contamination: the "signal" is really "PENDLE is almost always long (positive carry) vs SOL which oscillates." This passes quantitative screens but fails structural analysis. L004 pre-screen correctly identifies this before §6 computation.

4. **Future yield-protocol screening:** Screen yield-related protocols with L004 FIRST. If L004 blocks → skip §6 entirely (save computation). Add category rule to backlog: "yield-extraction protocols fail L004 systematically."

---

## HL Cap Impact

- HL 66.8% (K751) — paper-gate strict regardless
- PENDLE: HL listing confirmed (17519 rows), Bybit/OKX parquet not found
- No cap impact: BLOCKED wave, no deployment

---

## Governance Update

- Vertex set unchanged: 14 vertices (APT, ATOM, AVAX, BNB, ENA, FIL, HBAR, INJ, LDO, PEPE, SEI, SOL, TIA, TAO)
- PENDLE: BLOCKED-L004-G5q — NOT added to vertex set
- K758 lessons added to screening protocol
- Next candidates per K744 map: review remaining candidates excluding ETH DeFi yield category

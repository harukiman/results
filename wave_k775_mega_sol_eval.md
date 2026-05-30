# K775 — MEGA-SOL FR Differential Eval (MegaETH L2 vs SVM)

**Wave:** K775  
**Date:** 2026-05-30  
**Pair:** MEGA-SOL (MegaETH Ethereum L2 vs Solana SVM)  
**Source:** K773 #2 queue (fresh long-tail HIP-3)  
**K339 REPO_ROOT:** /Users/nekonaomichi/crypto-lab  
**LIVE 自動変更禁止**

---

## Verdict: REJECT

**Primary block:** L004 HARD BLOCK (structural carry 93.8% full / 91.0% OOS)  
**Additional blocks:** G5y AXS-SOL family contamination, G8 no Bybit, G6 entries, G9 OOS days

---

## Phase 0 — Identity + Pre-screens

### MEGA Identity
| Field | Value |
|-------|-------|
| Token | MEGA (Unit MegaETH) |
| Platform | MegaETH L2 — Ethereum L2, ultra-low latency, EVM-compatible |
| Listing | HIP-3 non-canonical perp on HyperLiquid |
| Listing Date | 2025-10-22 |
| Cluster | ETH L2 / EVM DeFi infrastructure |
| HL OI | ~$8M USD |
| Day Vol | ~$1M/day |
| maxLeverage | 3x |

### Pre-screen Results

| Gate | Value | Threshold | Result |
|------|-------|-----------|--------|
| L003 AVAX | corr=-0.0077 | < 0.45 | **PASS** |
| **L004 carry (FULL)** | **93.84%** | **< 80%** | **FAIL (HARD BLOCK)** |
| **L004 carry (OOS)** | **91.04%** | **< 80%** | **FAIL (HARD BLOCK)** |
| L007 FIL | corr=-0.0176 | < 0.45 | **PASS** |
| L010 HBAR | corr=-0.0128 | < 0.45 | **PASS** |
| L011 SOL | corr=-0.0205 | < 0.50 | **PASS** |
| G5q LDO-SOL (W168) | sig_corr=0.3641 | < 0.40 | PASS (marginal) |

**L004 is DISQUALIFYING.** Both full (93.8%) and OOS (91.0%) carry exceed the 80% hard block threshold. Strategy captures structural one-sided carry, NOT FR differential mean-reversion.

---

## Phase 1 — Vol Pre-screen

**K773 claimed vol_ratio=9.53x was a MEASUREMENT ARTIFACT.**

| Window | vol_ratio |
|--------|-----------|
| K773 30d (Apr30–May21 2026) | 9.53x (reported) / 9.80x (computed) |
| Full 220d | **1.86x** |
| 2025-11-21 (rolling 30d) | 1.24x |
| 2025-12-21 | 1.27x |
| 2026-01-20 | 0.35x |
| 2026-02-19 | 0.65x |
| **2026-03-21** | **0.00x (FLAT — HL floor rate for full month)** |
| 2026-04-20 | 0.67x |
| 2026-05-20 | 7.69x |

**Root cause:** K773 used a 30d window (Apr30–May21) where SOL FR compressed to near-zero while MEGA FR spiked. March 2026: MEGA FR = constant 0.000013 (HL minimum tick) for all 744 hours → zero variance → vol_ratio = 0.

---

## Phase 2 — Cycle Analysis

### MEGA Monthly FR Profile

| Month | FR Mean Ann | Carry % | Unique Values | Note |
|-------|------------|---------|---------------|------|
| 2025-10 | +3.26% | 87.9% | 34 | Fresh listing |
| 2025-11 | +11.5% | 98.8% | 41 | Structural floor carry |
| 2025-12 | +9.39% | 97.0% | 31 | Near-floor |
| 2026-01 | +9.77% | 98.4% | 21 | Near-floor |
| 2026-02 | +10.9% | 98.7% | 34 | Near-floor |
| **2026-03** | **+10.9%** | **100.0%** | **1 (CONSTANT)** | **★ HL FLOOR FOR FULL MONTH** |
| 2026-04 | +13.8% | 97.6% | 59 | Near-floor with spikes |
| 2026-05 | -8.07% | 67.7% | 330 | Regime shift / K773 spike window |

### Key Finding
MEGA FR is dominated by the HL floor rate (0.000013/hr = 11.4%/yr). The near-zero correlations with all anchors (SOL: -0.02, AVAX: -0.01, LDO: +0.01) are artifacts of near-constant FR, NOT genuine cycle independence.

---

## Phase 3 — Backtest Results

| Window | Full Sh | IS Sh | OOS Sh | OOS entries/yr |
|--------|---------|-------|--------|----------------|
| W=168h | 38.67 | 37.82 | 43.05 | 16.4 |
| W=84h | 38.49 | 41.81 | 41.42 | 29.5 |
| W=48h | 41.51 | 42.53 | 45.91 | 29.5 |

**CRITICAL NOTE:** High Sharpe values are NOT genuine alpha. They reflect structural carry capture: MEGA FR nearly always positive, SOL FR near-zero or negative → strategy = always long MEGA, short SOL = carry harvesting, not mean-reversion. **These are L004 contaminated backtests.**

---

## Phase 4 — Grid Search

Best config: W=48h, T=0.000000 → OOS Sh=45.91 (Bonferroni adj = 15.30)

Grid confirms: all 9 configs show elevated OOS Sharpe — systematic carry contamination, not signal selection.

---

## Phase 5 — Walk-Forward

| Fold | OOS Start | OOS Sh |
|------|-----------|--------|
| 1 | 2026-01-20 | +91.99 |
| 2 | 2026-02-19 | +148.86 |
| 3 | 2026-03-21 | +88.08 |
| 4 | 2026-04-20 | +11.29 |

WF stability: 4/4 = 1.00. **Entirely from carry capture. Fold 3 (Mar 2026) includes the zero-variance HL floor month — strategy trivially wins because FR differential is mechanically non-zero.**

---

## Phase 6 — §6 Gate Summary

| Gate | Value | Pass? | Note |
|------|-------|-------|------|
| G1 OOS Sharpe | 43.05 | ✓* | *Void — carry contaminated |
| G2 Perm p-value | 0.000 | ✓* | *Void — carry contaminated |
| G3 DSR Bonferroni | 14.18 | ✓* | *Void — carry contaminated |
| G4 WF stability | 1.00 | ✓* | *Void — carry contaminated |
| **G5y AXS-SOL** | **-0.652** | **✗** | |\|corr\|| = 0.652 > 0.40 |
| G6 Entries/yr | 16.4 | ✗ | < 20 threshold (long-tail) |
| G7 Ann ret @4x | 282% | ✓* | *Void |
| **G8 Cross-venue** | HL only | **✗** | No Bybit listing |
| **G9 OOS days** | 111d | **✗** | < 120d (long-tail) |
| **L004 HARD BLOCK** | **93.8%** | **✗✗** | **Primary disqualification** |

Standard gates: 5/9 pass (numerically) — all 5 passes are void due to L004 contamination.  
Total fails: L004 (primary), G5y, G6, G8, G9.

---

## Phase 7 — Decision + K523 3-Point ROI

### Decision: REJECT

**Primary rejection: L004 structural carry hard block (93.8%/91.0%)**

Additional rejections:
- G5y: AXS-SOL |sig_corr|=0.652 → anti-correlated with AXS-SOL strategy (family contamination)
- G8: MEGA HIP-3 HL-only, no Bybit listing → single-venue concentration risk
- G6: 16.4 entries/yr < 20 (W=168h OOS)
- G9: 111d OOS < 120d long-tail requirement

### K523 3-Point ROI (Mandatory — HYPOTHETICAL only, strategy is void)

| Scenario | USD/yr | Assumption |
|----------|--------|------------|
| Conservative | $80,478 | 38% realized × 25% OOS haircut |
| Mid | $107,305 | 38% realized, no OOS haircut |
| Optimistic | $282,380 | No haircut |

Sleeve: $100K (@1.0% of $10M), Leverage: 4.0x.  
**These numbers are meaningless** — the strategy is structural carry, not persistent alpha. Carry from HIP-3 listing epoch is NOT durable.

### Cluster Ruling
- MEGA = MegaETH L2 (ETH-adjacent)
- G5q (K772 lesson): LDO-SOL sig_corr=0.364 (W168) → PASS but marginal (IS=0.575)
- K772 ETH-DeFi-adjacent contamination check: applied and passed numerically
- Primary block remains L004 — cluster contamination is a secondary concern

---

## Key Insights (Learnings from K775)

### 1. K773 vol_ratio measurement artifact
30d window vol_ratio (9.53x) was a tail event where SOL FR compressed + MEGA FR spiked simultaneously. Full 220d structural vol_ratio = 1.86x with high instability (0x in March). **Lesson: pre-screen vol_ratio should be computed on full available history, not trailing 30d.**

### 2. HIP-3 tokens with HL floor-rate domination
MEGA FR spent the entire March 2026 at the HL minimum tick (0.000013). This produces:
- Near-zero correlation with all anchors (artifact, not genuine independence)
- Zero signal variance for full month
- High apparent carry (93.8%) → L004 hard block
- **Lesson: HIP-3 fresh listings are high-risk for structural carry contamination.**

### 3. G5y AXS-SOL anti-correlation
MEGA-SOL signal shows |corr|=0.652 with AXS-SOL (anti-correlated). This is noteworthy — MEGA and AXS are both gaming/entertainment-adjacent tokens and both on HL HIP-3. The anti-correlation suggests MEGA-SOL signal mimics the inverse of AXS-SOL. **Lesson: HIP-3 tokens may share systematic listing dynamics that correlate their FR differentials.**

### 4. Structural carry captures pass all backtest gates
G1-G4 all pass numerically despite L004 block. This validates why L004 hard block must be checked FIRST before running any backtest. OOS Sharpe of 43 and WF stability of 1.00 are both artifacts of structural carry domination, not genuine FR differential edge.

---

## Constraints & Risks

- **L004 HARD BLOCK:** Primary disqualification — structural carry 93.8%
- **G5y AXS-SOL failure:** Anti-correlated signal with existing strategy
- **G8 single-venue:** HL-only listing (HIP-3 non-canonical)
- **G9 short history:** 220d total, only 111d OOS
- **Vol instability:** vol_ratio ranges from 0x to 9.8x — not tradeable
- **K523:** 3-point ROI computed but void — strategy disqualified

---

## Deliverables

| File | Description |
|------|-------------|
| `wave_k775_mega_sol_eval.py` | Main script (~600 LOC, K339) |
| `wave_k775_mega_sol_eval.json` | Full output JSON |
| `wave_k775_mega_sol_eval.md` | This summary |
| `report.html` | K775 REJECT badge injected after K773 badge |

---

## Next Wave

- **K776:** EIGEN (EigenLayer restaking) — K773 queue #3
  - K773 metrics: vol_ratio=3.97x, max_corr=0.031, carry=0.622
  - EigenLayer restaking: distinct cluster (Ethereum restaking yield)
  - Concern: carry=0.622 → borderline (below 80% threshold → should pass L004)
  - Need: full history fetch + IS/OOS full eval

---

*K339 REPO_ROOT | LIVE 自動変更禁止 | 2026-05-30 22:58 JST*

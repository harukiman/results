# K760 DOGE-SOL FR Differential Eval — PoW Meme vs SVM

**Wave:** K760  
**Pair:** DOGE-SOL (Dogecoin PoW meme vs Solana SVM)  
**Decision:** REJECTED-PRE-SCREEN-L003-AVAX_L010-HBAR_L011-SOL-DIRECT_VOL-RATIO-BELOW-1x  
**Date:** 2026-05-30 JST  
**Exploration vector:** Separate from K744 top-10 (PoW meme cluster)

---

## Executive Summary

DOGE-SOL FR differential is **blocked at pre-screen stage** by 4 simultaneous failures:

| Gate | Value | Threshold | Result |
|------|-------|-----------|--------|
| L003 AVAX raw_corr | 0.5521 | < 0.45 | **FAIL** |
| L010 HBAR raw_corr | 0.5142 | < 0.45 | **FAIL** |
| L011 SOL raw_corr | 0.5768 | < 0.50 | **FAIL** |
| Vol ratio DOGE/SOL | 0.896x | ≥ 1.5x target | **FAIL** |
| L004 carry OOS | 71.6% | < 80% | PASS |
| L007 FIL raw_corr | 0.3871 | < 0.45 | PASS |
| MR9 DOGE ∉ V | CLEAR | - | PASS |

Vertex set unchanged: 15 vertices (PEPE K754, WIF K759 remain latest).

---

## Phase 0: Pre-screens

### MR9 — CLEAR
DOGE (PoW meme, Dogecoin Litecoin-fork 2013) is structurally distinct from all 15 existing alt-alt vertices. DOGE-SOL signal algebraically ≠ X-SOL for all X ∈ V.

### L003 AVAX — FAIL (0.5521 >> 0.45)
- Full: 0.5521, IS: 0.5706, OOS: 0.2615
- PoW meme thesis: DOGE mining economics co-move with broad alt cycle (AVAX = broad L1 beta). IS-period 2024 crypto bull drove DOGE and AVAX FR simultaneously.
- OOS decorrelation (0.2615) suggests regime-dependency — but full-period governs per policy.

### L010 HBAR — FAIL (0.5142 >> 0.45)
- HBAR data found in cache (unexpected from prior waves). DOGE-HBAR corr = 0.5142.
- Triple cluster contamination: AVAX + HBAR + SOL all contaminate DOGE FR.

### L011 SOL-direct — FAIL (0.5768 >> 0.50)
- Full: 0.5768, IS: 0.5742, OOS: 0.3178
- During IS bull period (2024 H1/H2): both DOGE (Musk election narrative) and SOL (ETF narrative) surged simultaneously, creating high FR co-movement.
- OOS 0.3178 shows meaningful divergence — but not enough for reconsideration yet.

### L004 carry — PASS
- Full=83.2% (WARN), OOS=71.6% (PASS). Hard block requires BOTH > 80%.

### L007 FIL — PASS
- raw_corr(DOGE_fr, FIL_fr) = 0.3871 < 0.45.

### Meme cluster overlap (Phase 0g)
- DOGE-SOL vs PEPE-SOL signal corr: 0.2937 (full), 0.3825 (OOS) — PASS
- DOGE-SOL vs WIF-SOL signal corr: 0.3450 (full), 0.5003 (OOS) — PASS (marginal OOS)
- DOGE-SOL WOULD add marginal signal above existing meme vertices — moot given pre-screen block.

---

## Phase 1: Vol Pre-screen

| Metric | DOGE | SOL |
|--------|------|-----|
| std (bps/hr) | 0.2785 | 0.3110 |
| Vol ratio | **0.896x** | — |
| mean (bps) | 0.1387 | 0.1129 (approx) |
| min (bps) | -12.14 | -20.51 |
| max (bps) | +3.45 | +1.84 |
| P99 (bps) | +1.27 | +0.93 |

Vol ratio = 0.896x — BELOW 1.0x minimum. SOL FR is MORE volatile than DOGE FR, driven by SOL liquidation cascade events (min=-20.51bps). DOGE min=-12.14bps is less extreme.

### Quarterly Differential Analysis

| Period | DOGE (bps) | SOL (bps) | Diff (bps) |
|--------|-----------|-----------|-----------|
| Q2 2024 | +0.208 | +0.215 | -0.008 |
| Q3 2024 | +0.118 | +0.109 | +0.009 |
| Q4 2024 | +0.434 | +0.341 | **+0.094** |
| Q1 2025 | +0.076 | +0.041 | +0.035 |
| Q2 2025 | +0.100 | +0.044 | +0.057 |
| Q3 2025 | +0.193 | +0.163 | +0.030 |
| Q4 2025 | +0.036 | -0.008 | **+0.044** |
| Q1 2026 | +0.014 | -0.089 | **+0.103** |
| Q2 2026 | +0.091 | +0.017 | +0.074 |

Differential positive in nearly all periods (Q4 2024 election cycle peak: +0.094bps).

---

## Phase 2: Backtest (FOR RECORD — deployment blocked)

| Window | OOS Sharpe | IS Sharpe | Entries/yr | G6 |
|--------|-----------|----------|-----------|-----|
| W=168h | 49.35 | 16.04 | 15.6/yr | FAIL |
| W=84h | **59.27** | 22.08 | **31.2/yr** | PASS |
| W=48h | 62.98 | 24.69 | 50.3/yr | PASS |

Canonical W=84h: OOS Sh=59.27, OOS AnnRet=8.58%/yr, OOS AnnRet@4x=34.30%, MaxDD=-0.057%.

---

## Phase 3: Grid Search

Best OOS: 64.26 (W=48h, T=2e-6). DSR Bonferroni: t=26.25, p_bonf=0.000 → G3 PASS.

---

## Phase 4: Walk-forward 12-fold (W=84h)

| Fold | OOS Period | Sharpe |
|------|-----------|--------|
| 1 | 2025-05-28 – 2025-06-27 | 23.76 |
| 2 | 2025-06-27 – 2025-07-27 | 33.03 |
| 3 | 2025-07-27 – 2025-08-26 | 23.50 |
| 4 | 2025-08-26 – 2025-09-25 | 25.34 |
| 5 | 2025-09-25 – 2025-10-25 | 15.05 |
| 6 | 2025-10-25 – 2025-11-24 | 77.06 |
| 7 | 2025-11-24 – 2025-12-24 | 62.77 |
| 8 | 2025-12-24 – 2026-01-23 | 43.36 |
| 9 | 2026-01-23 – 2026-02-22 | 69.01 |
| 10 | 2026-02-22 – 2026-03-24 | 56.35 |
| 11 | 2026-03-24 – 2026-04-23 | 74.68 |
| 12 | 2026-04-23 – 2026-05-23 | 55.66 |

**12/12 positive, mean Sh=46.63, min=15.05.**

---

## Phase 5: §6 Gates (FOR RECORD)

All G5 gates PASS at W=84h. Max corr: 0.3722 (G5m TIA-SOL). All G1-G9 would pass IF pre-screens were waived.

---

## K523 3-Point ROI (FOR RECORD — deployment blocked)

@$10M 2.5% sleeve 4x leverage, 25% OOS haircut:
- Conservative ($×0.38): **$24,440/yr**
- Mid ($×0.60): **$38,590/yr**
- Optimistic ($×0.85): **$54,669/yr**

---

## Key Finding: PoW Meme Category Rule (K760 Lesson)

DOGE (PoW) exhibits **triple cluster contamination**: AVAX + HBAR + SOL raw FR corr all exceed threshold. This is explained by PoW mining economics:

1. PoW miners react to broad BTC/alt price (not ecosystem-specific narratives)
2. DOGE has no staking yield → FR purely speculative, driven by market beta
3. Musk/X narrative fires during broad crypto bull phases (co-movement with all alts)
4. No validator rewards or DeFi composability to create idiosyncratic FR

**K760 Category Rule:** Future PoW candidates (LTC, BCH, DOGE variants) should pre-screen L003 (AVAX) + L011 (SOL) first before deeper evaluation. Expected triple cluster failure.

---

## Future Revisit Criteria

Re-open K760 DOGE-SOL if ALL:
1. 12-month rolling raw_corr(DOGE_fr, AVAX_fr) < 0.40 (OOS=0.2615 trending — possible in extended OOS)
2. 12-month rolling raw_corr(DOGE_fr, SOL_fr) < 0.45 (OOS=0.3178 trending — borderline)
3. Vol ratio DOGE/SOL approaches 1.0x+ in sustained period
4. Musk/X payment narrative creates new cycle desynchronization from SVM

---

## Deliverables

- `wave_k760_doge_sol_eval.py` (~600 LOC, K339 REPO_ROOT)
- `wave_k760_doge_sol_eval.json` (full results)
- `wave_k760_doge_sol_eval.md` (this file)
- `report.html` (badge added)

**K339 REPO_ROOT | LIVE自動変更禁止 | HL 66.8% cap (K751) | Vertex set 15 unchanged**

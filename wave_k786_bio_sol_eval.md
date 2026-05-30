# K786 BIO-SOL FR Differential Eval — ACCEPT (DeSci + SVM)

**Date:** 2026-05-31 00:30 JST  
**Wave:** K786  
**Pair:** BIO-SOL (Bio Protocol DeSci vs Solana SVM)  
**Verdict:** **ACCEPT** (8/9 gates, G5 all PASS)  
**Vertex count:** 21st vertex (1st DeSci cluster)

---

## Executive Summary

BIO-SOL passes all pre-screens and all §6 gates except G8 (cross-venue — HIP-3 HL-only). OOS Sharpe 23.10 across 205 days is exceptional. All 24 G5 family correlations below 0.40. L004_DIFF borderline (full=0.303, just 0.003 above threshold), but OOS=0.461 confirms timing alpha exists. G2 permutation p=0.000 confirms edge is not random.

BIO is the first DeSci vertex — distinct cluster from all 20 existing members.

---

## Pre-Screen Results (Phase 0) — ALL PASS

| Check | Value | Threshold | Result |
|-------|-------|-----------|--------|
| MR9 (not in vertex set) | BIO absent | — | PASS |
| K775 vol_ratio full | 9.833x | >= 1.5x | PASS |
| L003 corr(BIO,AVAX) | 0.0192 | < 0.45 | PASS |
| L007 corr(BIO,FIL) | 0.0314 | < 0.45 | PASS |
| L010 corr(BIO,HBAR) | 0.0503 | < 0.45 | PASS |
| L011 corr(BIO,SOL) | 0.0028 | < 0.50 | PASS |
| L004 carry full | 0.5590 | [0.30, 0.80] | PASS |
| L004 carry OOS | 0.5983 | [0.30, 0.80] | PASS |
| **L004_DIFF full** | **0.3030** | **[0.30, 0.70]** | **PASS (BORDERLINE)** |
| L004_DIFF OOS | 0.4611 | [0.30, 0.70] | PASS |
| G5u pre-check (FIL-SOL) | 0.3308 | < 0.40 | PASS |
| G5j pre-check (SOL-INJ) | -0.2987 | < 0.40 | PASS |

**L004_DIFF borderline note:** full=0.303 is 0.003 above the 0.30 threshold. OOS=0.461 confirms this is genuine timing alpha (not structural one-sidedness). G2 p=0.000 confirms.

**K775 note:** K781 used 500-row (20d) cache giving vol_ratio=5.33x. Full 12,290-record fetch gives 9.833x — actual vol is even higher than estimated.

---

## Cycle Analysis (Phase 1)

- **History:** 2025-01-03 to 2026-05-30, 512 days, 12,289 aligned hourly rows
- **IS/OOS split:** IS end 2025-11-06 (60/40), OOS = 205 days
- **vol_ratio_full:** 9.833x (SOL baseline)
- **raw_corr(BIO,SOL):** 0.0028 (essentially uncorrelated)
- **OU half-life:** 7.16h (mean-reversion fast enough for 84h window)

**BIO FR drivers:** DeSci narrative cycles, BioDAO deal flow (IP-NFT acquisitions, VitaDAO longevity milestones), biotech bull/bear cycles, regulatory DeSci news  
**SOL FR drivers:** SVM meme season, SOL ETF narratives, Firedancer cycles, Raydium/Jupiter DEX volume

**DeSci structural independence:** Biotech research funding cycles are orthogonal to Solana consumer DeFi/meme dynamics. BIO-SOL corr=0.003 confirms this.

---

## Backtest Grid (Phase 2)

| Window | IS Sharpe | OOS Sharpe | OOS Ann Ret |
|--------|-----------|------------|-------------|
| W=48h  | 23.38     | 23.89      | 144.1%      |
| W=84h  | 23.24     | 23.10      | 139.6%      |
| W=168h | 23.34     | 20.83      | 126.6%      |

**Canonical window:** 84h (W=84, T=0.0)

All windows show IS/OOS Sharpe consistency with OOS > 20 — no degradation signal.

---

## §6 Gate Results (Phase 3)

| Gate | Value | Threshold | Result |
|------|-------|-----------|--------|
| G1 OOS Sharpe | 23.10 | >= 1.0 | PASS |
| G2 Perm p | 0.0000 | <= 0.05 | PASS |
| G3 DSR Bonferroni | t=1619.5, p≈0 | < 0.0056 | PASS |
| G4 Walk-forward | 5 folds, 0 neg | all positive | PASS |
| G5 Family (24 checks) | max_corr=0.331 | all < 0.40 | PASS |
| G6 Entries/yr | 7,479 | >= 30 | PASS |
| G7 OOS ret @4x | 558.4% | > 5% | PASS |
| G8 Cross-venue | HL only | need Bybit/OKX | **FAIL** |
| G9 OOS days | 204.8d | >= 180d | PASS |

**G8 note:** BIO is HIP-3 on HL (Jan 2025). No confirmed Bybit/OKX perpetual. Paper-gate mandatory until cross-venue verified.

### G4 Walk-Forward Folds

| Fold | OOS Period | Sharpe | Ann Ret |
|------|-----------|--------|---------|
| 1 | 2025-04-03 → 2025-05-03 | 37.44 | 177.6% |
| 2 | 2025-07-02 → 2025-08-01 | 69.92 | 85.9% |
| 3 | 2025-09-30 → 2025-10-30 | 33.03 | 1227.0% |
| 4 | 2025-12-29 → 2026-01-28 | 29.89 | 21.2% |
| 5 | 2026-03-29 → 2026-04-28 | 20.95 | 183.9% |

All 5 folds positive. Sharpe consistently > 20 (except fold 5 at 20.95).

### G5 Family Correlation (selected)

All 24 checks PASS (max_corr = 0.3308, G5u FIL-SOL):

- G5u FIL-SOL: 0.3308 (highest, below 0.40 threshold)
- G5j SOL-INJ: -0.2987 (PASS — K784 lesson validated)
- G5i ATOM-SOL: 0.1772 (PASS)
- G5q LDO-SOL: 0.2497 (PASS)
- G5o BNB-SOL: 0.2017 (PASS)

---

## K523 3-Point ROI Projection

**Sleeve:** 0.4% of $10M = $40,000 notional  
**Leverage:** 4.0x  
**OOS Ann Ret (raw):** 139.6%

| Scenario | Annual USD |
|----------|------------|
| Conservative (×0.38 realized ×OOS-haircut ×fee) | $54,105/yr |
| **Mid/Central (×0.38 realized ×OOS-haircut)** | **$63,652/yr** |
| Optimistic (raw OOS, upper bound) | $167,506/yr |

K523 compliance: single-number $167K is upper bound, not central. Central estimate $63.7K/yr at 0.4% sleeve.

---

## Cluster Analysis

**BIO cluster:** DeSci / Biotech DAO coordination (BioDAO ecosystem)
- VitaDAO (longevity), AthenaDAO (women's health), HairDAO, GenomesDAO
- IP-NFT tokenization of biotech intellectual property
- Decentralized patient capital for drug discovery DAOs

**Distinction from existing vertices:**
- vs TAO: TAO = AI model weight tokenization (neural networks), BIO = biotech IP/DAO capital (biology). Distinct.
- vs AAVE: AAVE = DeFi lending governance, BIO = decentralized science funding. Distinct.
- vs SOL: structural independence confirmed (corr=0.003).

**DeSci is a new category** — first vertex to represent academic/research capital tokenization.

---

## Operational Notes

- HL cap at 65.0% — paper-gate mandatory regardless
- Sleeve 0.4% ($40K @$10M) — liquidity-limited
- BIO listing: HIP-3 HL (Jan 2025), 512 days history
- G8 FAIL: cross-venue perp not confirmed. Verify Bybit/OKX before live.
- Paper-gate: all new paired-trades paper-only until HL% reduces below cap

---

## Lesson Summary

| Lesson | Applied | Result |
|--------|---------|--------|
| K782 L004_DIFF mandatory | Yes — full=0.303 BORDERLINE | PASS (OOS=0.461 confirms) |
| K784 G5u pre-check | Yes — 0.331 < 0.40 | PASS |
| K784 G5j pre-check | Yes — -0.299 | PASS |
| K775 full vol verify | Yes — 9.83x vs K781 5.33x | PASS (vol higher than cached) |

K782 lesson validated: L004_DIFF full=0.303 borderline but OOS=0.461 confirms timing alpha. G2 p=0.000 confirms. PROVE-SOL (diff=0.277) would have failed here too if borderline.

---

## Decision

**VERDICT: ACCEPT**  
**Code:** ACCEPT  
**21st vertex (1st DeSci cluster)**  
**Paper-gate mandatory (HL cap + G8 cross-venue unconfirmed)**

Next wave: K787 (next backlog or HIP-3 round 2e screen)

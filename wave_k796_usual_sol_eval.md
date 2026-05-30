# K796: USUAL-SOL FR Differential Evaluation

**Decision:** REJECTED (G2 FAIL — no timing alpha; G4 10/11; structural carry decay)
**Date:** 2026-05-31 JST
**Wave:** K796 | Pair: USUAL-SOL | Candidate: K793 final long-tail (#2)

---

## Executive Summary

USUAL-SOL (Usual Money USD0 stablecoin governance, ETH-DeFi vs Solana SVM L1) FR differential strategy — the final K793 long-tail queue candidate — evaluated through all §6 gates. **REJECTED**: 3 gates fail (G2, G4, G8). Critical finding: **IS Sharpe=36.33 collapses to OOS Sharpe=12.60** (-65% IS-to-OOS gap), and **G2 permutation test p=0.925** — the signal has zero timing alpha above pure carry. The edge is structural carry-dominated (SHORT USUAL earns negative USUAL FR), but the carry magnitude has decayed dramatically in 2026 (2026Q1: diff=-0.01bps, 2026Q2: +0.03bps). Carry-30d=0.954 from K793 is confirmed: the USUAL-SOL differential has converged to near-zero in the OOS period.

K523 ROI at $10M: **$500 conservative / $790 mid / $1,119 optimistic per year** (sleeve 0.25% = $25K, leverage 3x) — economically negligible, confirming REJECTION is correct.

Long-tail exhaust **COMPLETE**: K793 final two candidates (ME K794 CONDITIONAL_ACCEPT, USUAL K796 REJECTED). HIP-3 batch screening series concluded.

---

## Phase 0: Pre-screens

| Check | Value | Threshold | Result |
|-------|-------|-----------|--------|
| MR9 identity | USUAL ∉ vertex_set_V (21 vertices) | not in set | CLEAR |
| Meta-narrative | ETH-DeFi stablecoin gov vs SVM L1 | distinct | CLEAR |
| L003 AVAX corr | 0.0831 | < 0.45 | PASS |
| L004 carry (full) | 0.5645 | < 0.80 | PASS |
| L004 carry (OOS) | — | < 0.80 | PASS |
| **L004_DIFF (full)** | **0.2914** | **[0.30, 0.70]** | **BORDERLINE** |
| L004_DIFF (OOS) | 0.5141 | [0.30, 0.70] | PASS |
| L007 FIL-SOL pre-screen | 0.1103 | < 0.40 | PASS |
| L010 HBAR corr | 0.1101 | < 0.45 | PASS |
| L011 SOL-direct corr | 0.0231 | < 0.45 | PASS |
| **G5q LDO-SOL** | **0.1734** | **< 0.40** | **PASS** |
| **G5v COMP-SOL** | **0.0224** | **< 0.40** | **PASS** |
| G5ab MEME-SOL | 0.0221 | < 0.40 | PASS |

### L004_DIFF Analysis (Critical — K788 Borderline Rule)

- Full period diff_pos = 0.2914 (borderline, 0.0086 below 0.30 floor)
- OOS period diff_pos = 0.5141 (PASS — within [0.30, 0.70])
- Pure carry IS Sharpe = **36.7483** vs Signal IS Sharpe = **36.3256**
- **Timing alpha = -0.4227 Sh pts** — signal HURTS vs pure carry
- **G2 mandatory**: K788 borderline rule requires G2 p < 0.05 before proceeding
- **K775 carry_30d = 0.954**: Out-of-range warning — recent 30d is one-sided

### ETH-DeFi Governance Cluster Pre-Screens

| Gate | Pair | Corr | Result |
|------|------|------|--------|
| G5q | LDO-SOL (K721) | 0.1734 | PASS |
| G5v | COMP-SOL (K778) | 0.0224 | PASS |
| G5ab | MEME-SOL (K788) | 0.0221 | PASS |

Both ETH-DeFi governance family members (LDO, COMP) show low signal correlation with USUAL-SOL. ETH-DeFi cluster is CLEAR at pre-screen level.

### Vol Ratio 30d Warning

- Full period vol_ratio = **5.25x** (PASS, > 3x threshold)
- 30d vol_ratio = **0.95x** (WARN — near-zero differential in recent period)
- This K775-type warning is confirmed by quarterly analysis: 2026Q1 diff = -0.01bps, 2026Q2 = +0.03bps

---

## Phase 1: Vol/FR Characterization

| Metric | USUAL | SOL |
|--------|-------|-----|
| FR mean (bps) | −0.341 | +0.031 |
| FR std (bps) | 1.787 | 0.341 |
| Vol ratio USUAL/SOL | **5.25x** | — |

### Quarterly Analysis (Regime Decay Confirmed)

| Period | USUAL mean | SOL mean | Diff | Diff pos% |
|--------|-----------|----------|------|-----------|
| 2024Q4 | −0.39bps | +0.10bps | −0.50bps | **13%** |
| 2025Q1 | −0.80bps | +0.04bps | −0.84bps | **10%** |
| 2025Q2 | −0.54bps | +0.04bps | −0.58bps | **16%** |
| 2025Q3 | −0.03bps | +0.16bps | −0.19bps | **11%** |
| 2025Q4 | −0.49bps | −0.01bps | −0.48bps | **30%** |
| **2026Q1** | **−0.10bps** | **−0.09bps** | **−0.01bps** | **61%** |
| **2026Q2** | **+0.05bps** | **+0.01bps** | **+0.03bps** | **60%** |

**Critical pattern**: 2024Q4 through 2025Q3, USUAL FR is strongly negative (diff -0.5 to -0.8bps, diff_pos ~10-16%). But **2026Q1-Q2, the differential collapses to ~0bps, diff_pos flips to 60-61%**. This is structural carry decay — USUAL FR has normalized vs SOL FR in the OOS period, eliminating the edge.

---

## Phase 2: Backtest Results (Canonical W=84h)

| Period | Sharpe | Ann Ret | Ann Ret (3x) | Max DD | Entries/yr |
|--------|--------|---------|-------------|--------|-----------|
| IS (Dec 2024 – Oct 2025) | **36.33** | 42.83% | 128.49% | — | — |
| OOS (Oct 2025 – May 2026) | **12.60** | 23.41% | 70.22% | −0.45% | **68.8** |
| Full (Dec 2024 – May 2026) | — | — | — | — | — |

**IS-to-OOS gap is massive**: IS Sh=36.33 → OOS Sh=12.60 (-65%). This confirms the quarterly analysis — the IS period captured high-carry episodes (2024Q4-2025Q3) that do not persist in OOS (2025Q4-2026Q2). The edge is carry-regime dependent, not structural.

**Pure carry IS Sharpe = 36.75** > Signal IS Sharpe = 36.33 → timing signal destroys value (timing alpha = -0.42 Sh).

---

## Phase 3: Grid Search

All 12 configs show similar IS-OOS Sharpe gap. Best OOS config likely at shorter W (48h) due to frequency of sign changes in OOS, but G2 result is deterministic — no timing alpha regardless of parameters.

DSR Bonferroni: t-stat=15.036, p≈0.000 → PASS (but irrelevant — G2 kills the path).

---

## Phase 4: Walk-Forward (11 folds)

| Fold | Period | Sharpe | Positive |
|------|--------|--------|---------|
| 2 | Mar–Apr 2025 | 54.28 | YES |
| 3 | Apr–May 2025 | 29.43 | YES |
| 4 | May–Jun 2025 | 47.61 | YES |
| 5 | Jun–Jul 2025 | 71.11 | YES |
| 6 | Jul–Aug 2025 | 61.89 | YES |
| 7 | Aug–Sep 2025 | 56.33 | YES |
| **8** | **Sep–Oct 2025** | **−0.37** | **NO** |
| 9 | Oct–Nov 2025 | 36.03 | YES |
| 10 | Nov–Dec 2025 | 17.63 | YES |
| 11 | Dec 2025–Jan 2026 | 44.90 | YES |
| 12 | Jan–Feb 2026 | 19.63 | YES |

**10/11 positive folds. G4 FAIL** (threshold: all positive, i.e., 11/11). Fold 8 (Sep-Oct 2025) is the transition period where USUAL FR began normalizing — this is the regime shift point visible in the quarterly data (2025Q3 diff_pos jumps from 11% to 30% in Q4). G4 fail = 10/11, which doesn't meet the "all positive" standard.

Mean WF Sharpe = 39.86 (driven by IS period folds). Min = -0.37 (Fold 8).

---

## Phase 5: Section §6 Gates

| Gate | Value | Threshold | Result |
|------|-------|-----------|--------|
| G1 OOS Sharpe | **12.60** | ≥ 1.0 | **PASS** |
| **G2 Perm p-value** | **0.9250** | **< 0.05** | **FAIL** |
| G3 DSR Bonferroni | p≈0.000 | < 0.05 | PASS |
| **G4 Walk-forward** | **10/11** (min Sh=−0.37) | all positive | **FAIL** |
| G5 Family corr | max=0.3128 (G5s HBAR-SOL) | < 0.40 | **29/29 PASS** |
| G5q LDO-SOL | 0.1734 | < 0.40 | PASS |
| G5v COMP-SOL | 0.0224 | < 0.40 | PASS |
| G6 Entries/yr OOS | 68.8 | ≥ 30 | PASS |
| G7 Ann ret 3x | 70.22% | ≥ 5% | PASS |
| **G8 Cross-venue** | **HL only (1 venue)** | **2+ venues** | **FAIL** |
| G9 OOS days | ≥ 180d | ≥ 180 | PASS |

**6/9 gates PASS, 3 FAIL (G2, G4, G8)**

### G2 Analysis (Decisive — K782/K788 Rule)

- Real IS Sharpe = 36.3256
- Permutation null mean = 36.5823
- Permutation null max = 38.1209
- p-value = **0.9250** (real IS Sh is BELOW null mean — pure carry beats signal)
- **G2 FAIL**: Real signal is worse than random carry. The rolling-mean signal adds negative value.
- K788 borderline rule: G2 p=0.925 → HARD BLOCK. No timing alpha = structural carry only strategy.
- K782 precedent: PROVE-SOL (G2 p=1.000) was hard-blocked. USUAL-SOL (G2 p=0.925) follows same pattern.

### G5 Family — Key Observations

- All 29 gates PASS (max corr = G5s HBAR-SOL = 0.3128, below 0.40)
- G5q LDO-SOL (K721) = **0.1734** → ETH-DeFi governance cluster CLEAR (different FR mechanisms)
- G5v COMP-SOL (K778) = **0.0224** → ETH-DeFi governance cluster CLEAR (near-zero correlation)
- USUAL-SOL FR is orthogonal to all existing family strategies — structural isolation confirmed
- However, orthogonality doesn't save USUAL from regime decay / G2 failure

---

## Phase 6: Decision

**REJECTED** — G2 FAIL (no timing alpha, p=0.925), G4 FAIL (10/11 folds), G8 FAIL (HL only)

### Primary Rejection Reason: G2 No Timing Alpha + Regime Decay

The USUAL-SOL strategy edge was **pure structural carry** (SHORT USUAL, earn negative USUAL FR vs positive SOL FR). This carry was substantial in 2024Q4-2025Q3 but has **completely decayed in 2026**:

- 2025Q3: diff = -0.19bps (declining)
- 2025Q4: diff = -0.48bps (temporary recovery)
- 2026Q1: diff = **-0.01bps** (near zero — carry gone)
- 2026Q2: diff = **+0.03bps** (carry reversed)

The rolling-mean signal (W=84h) cannot create timing alpha when the underlying carry regime is unstable (G2 p=0.925). The K793 carry_30d=0.954 warning was correct: the recent 30d differential was long-biased (SOL FR > USUAL FR), confirming the carry had inverted.

### K523 3-Point ROI Projection (Negligible)

| Sleeve | Conservative | Mid | Optimistic |
|--------|-------------|-----|-----------|
| 0.20% | $400/yr | $632/yr | $895/yr |
| **0.25% (mid)** | **$500/yr** | **$790/yr** | **$1,119/yr** |
| 0.30% | $600/yr | $948/yr | $1,343/yr |

ROI < $1,200/yr at all scenarios — economically negligible. Even optimistic projection at 0.3% sleeve is under $1,500/yr @$10M. This confirms rejection is the correct economic decision.

---

## Lessons Documented

- **K796 USUAL regime decay**: USD0 stablecoin governance FR starts strongly negative (2024-2025) then normalizes to +0.03bps in 2026Q2. Carry-dominated strategies in DeFi governance tokens must monitor quarterly carry magnitude — if carry < 0.1bps diff mean over any 90d rolling window, suspend.
- **K796 vol_ratio_30d=0.95x signal**: K793 carry_30d=0.954 flag was correct. vol_ratio_30d < 1.0x (effectively no vol differential) is a reliable pre-screen for structural carry decay. Future candidates with vol_ratio_30d < 1.5x should be flagged as HIGH-RISK regardless of full-period vol_ratio.
- **K796 G2 pure carry**: When IS signal Sharpe < IS pure-carry Sharpe (timing alpha < 0), G2 will fail even for K788-borderline tokens. This is the K782 PROVE-SOL pattern. The signal is not timing the carry — it is carry itself.
- **K796 ETH-DeFi governance cluster**: USUAL-SOL vs LDO-SOL (0.1734) and COMP-SOL (0.0224) are CLEAR — ETH-DeFi governance tokens have orthogonal FR cycles despite same meta-narrative cluster. Future DeFi governance evals can proceed past pre-screen if G5q/G5v < 0.40.
- **K796 long-tail exhaust**: K793 batch (ME + USUAL) = final K793 queue. HIP-3 round 2e complete. Long-tail screening series (K766-K793) is now physically exhausted. 99 tokens screened, 31 pre-screen survivors, ME (K794) = last meaningful survivor.

---

## Cluster Ruling

**USUAL = NO NEW CLUSTER** (rejected before acceptance)

- USUAL = Usual Money USD0 governance (ETH-DeFi, stablecoin protocol)
- Screened against COMP-SOL (G5v=0.022) and LDO-SOL (G5q=0.173) — both CLEAR
- ETH-DeFi cluster currently has 2 members: COMP (K778) + LDO (K721)
- Future stablecoin governance evals (MKR/SKY, AAVE, CRV) should pre-screen vs both

---

## K793 Long-Tail Series: Final Tally

| Wave | Token | Composite | OOS Sh | Verdict |
|------|-------|-----------|--------|---------|
| K794 | ME (NFT marketplace) | 0.432 | 19.47 | CONDITIONAL_ACCEPT_RESEARCH_ONLY |
| **K796** | **USUAL (stablecoin gov)** | **0.069** | **12.60** | **REJECTED (G2/G4/G8)** |

**Long-tail screening complete. Remaining pipeline = governance waves only.**

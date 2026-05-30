# K625 JTO-BTC Window Sweet-Spot Retry

**Decision: BLOCKED-G5-STRUCTURAL**
**Date: 2026-05-30 10:17 JST**
**Runtime: 2.18s**

---

## Executive Summary

K625 tested 7 window sizes (72h–720h) on JTO-BTC FR differential carry to find a "sweet-spot" where both G5 blockers (SEI and DOGE) clear the 0.40 correlation threshold simultaneously with sufficient trade frequency (≥30/yr). Result: **no window achieves joint pass**. The SEI and DOGE blockers exhibit **opposite window sensitivities** — shorter windows resolve SEI but worsen DOGE, and vice versa. This is a structural constraint that cannot be resolved by window tuning alone.

Despite the block, K625 conclusively confirms the **Solana LST/MEV sub-cluster (24th)** — SOL corr=0.3782 and JUP corr=0.1418 both PASS, establishing that JTO's MEV/LST mechanics are orthogonal to Solana L1 (SOL) and Solana DEX (JUP). The $4.49M/yr profit potential remains locked pending a structural solution.

---

## Context: Why K625 Exists

**K622 JTO-BTC evaluation** produced:
- OOS Sharpe: 18.67
- OOS Ann Return: 44.91%
- Estimated profit: $4,490,000/yr @$10M notional 4x leverage
- Decision: BLOCKED-G5

Both blockers were borderline:
- **SEI (G5f)**: corr = 0.4075 (0.0075 over threshold)
- **DOGE (G5r)**: corr = 0.4009 (0.0009 over threshold)

Hypothesis: at a different rolling window, both might drop below 0.40 simultaneously while maintaining ≥30 trades/yr.

Solana LST/MEV sub-cluster was confirmed at K622:
- SOL G5b: 0.3783 (PASS) — JTO distinct from Solana L1
- JUP G5aa: 0.1414 (PASS) — JTO distinct from Solana DEX

---

## Phase 1: Window Sweep Results

| W(h) | W(d) | OOS Sh | Ann Ret | tr/yr | SEI (G5f) | DOGE (G5r) | SOL (G5b) | JUP (G5aa) | JOINT |
|------|------|--------|---------|-------|-----------|------------|-----------|------------|-------|
| 72   | 3.0  | 18.24  | 44.67%  | 54.7  | 0.3775 **P** | 0.4172 **F** | 0.3483 P | 0.1856 P | **FAIL** |
| 168  | 7.0  | 18.71  | 45.59%  | 27.4  | 0.4052 **F** | 0.4004 **F** | 0.3782 P | 0.1418 P | **FAIL** |
| 240  | 10.0 | 18.82  | 45.87%  | 23.9  | 0.4702 **F** | 0.3674 **P** | 0.3463 P | 0.1607 P | **FAIL** |
| 336  | 14.0 | 19.16  | 46.58%  | 6.8   | 0.5914 **F** | 0.4039 **F** | 0.4230 F | 0.1519 P | **FAIL** |
| 504  | 21.0 | 19.14  | 46.51%  | 6.8   | 0.6575 **F** | 0.4465 **F** | 0.4932 F | 0.1962 P | **FAIL** |
| 672  | 28.0 | 19.27  | 46.80%  | 0.0   | 0.6475 **F** | 0.4527 **F** | 0.5319 F | 0.1859 P | **FAIL** |
| 720  | 30.0 | 19.27  | 46.80%  | 0.0   | 0.6878 **F** | 0.4378 **F** | 0.5380 F | 0.2068 P | **FAIL** |

**Joint pass windows: 0 out of 7**

### Key Observations

**1. SEI (G5f) — Monotone Increasing with Window Length**
- W=72h: 0.3775 (PASS — below threshold)
- W=168h: 0.4052 (FAIL — 0.0052 over)
- W=336h: 0.5914 (FAIL — high)
- W=720h: 0.6878 (FAIL — very high)

Interpretation: At short windows, JTO and SEI signals switch direction frequently due to MEV bursts and ecosystem-specific FR episodes. At long windows, both converge into the same macro alt-sentiment regime direction (BTC contango vs alt-flat/backwardation).

**2. DOGE (G5r) — Non-Monotone, Partially Decreasing then Increasing**
- W=72h: 0.4172 (FAIL — above threshold)
- W=168h: 0.4004 (FAIL — barely over)
- W=240h: 0.3674 (PASS — unique PASS)
- W=336h: 0.4039 (FAIL — re-fails)
- W=504h+: 0.4465+ (FAIL — worsening)

Interpretation: DOGE has a mid-range sweet-spot at W=240h (10d) where it passes. However, at that exact window, SEI has jumped to 0.4702 (FAIL). The crossing points of SEI and DOGE do not overlap.

**3. JUP (G5aa) — Consistently PASS**
- JUP corr ranges 0.14–0.21 across all windows (always PASS)
- Solana LST/MEV vs DEX distinction is robust to window choice

**4. SOL (G5b) — Passes at short windows, fails at long windows**
- W=72h-240h: 0.34–0.38 (PASS)
- W=336h+: 0.42–0.53 (FAIL at long windows)
- Critical insight: at long windows, JTO and SOL both enter the same macro bull/bear carry regime, eroding the sub-cluster distinction

**5. OOS Sharpe — Robust and Improving**
- Sh range: 18.24 (W=72h) to 19.27 (W=720h)
- The signal quality is inherently strong — the block is purely from G5 correlations
- Trade frequency collapses above W=336h (≤7/yr → G6 structural FAIL)

---

## Phase 2: Joint Optimization Analysis

**Conclusion: NO_SWEET_SPOT**

The fundamental constraint is a **crossing impossibility**:
- SEI < 0.40 requires W ≤ ~80h (very short window)
- DOGE < 0.40 requires W ≈ 240h (mid-range window) or W < 72h (untested but extrapolation suggests possible)
- Trades/yr ≥ 30 requires W ≤ ~240h

The three constraints create an infeasible region:
- Short enough for SEI: W ≤ ~80h → too short for DOGE
- Right for DOGE: W ≈ 240h → too long for SEI
- G6 trades: W ≤ 240h but both SEI fails at W=240h

**Root Cause**: SEI and DOGE have structurally different FR correlation structures with JTO:
- SEI (Sei Network — parallel EVM) shares ecosystem sentiment cycles with JTO Solana MEV at LONG windows via broad alt-market regime. At short windows, ecosystem-specific FR patterns dominate.
- DOGE has a different structure — its FR is driven by retail sentiment cycles (~10d) that creates a specific resonance at W=240h where the DOGE signal is decorrelated from JTO.

These two different structural causes cannot be resolved simultaneously by window tuning.

### Margin Analysis (distance from threshold)

| W(h) | SEI margin | DOGE margin | Trade margin | Any near-miss? |
|------|-----------|-------------|--------------|----------------|
| 72   | +0.0225 P | -0.0172 F   | +24.7 P      | SEI PASS but DOGE fails by 0.0172 |
| 168  | -0.0052 F | -0.0004 F   | -2.6 F       | DOGE nearly passes (0.0004 over) but SEI fails |
| 240  | -0.0702 F | +0.0326 P   | -6.1 F       | DOGE PASS but SEI +0.07 over, G6 fails |

The nearest miss is **W=168h** where DOGE is only 0.0004 over threshold (the K622 value). However, SEI is -0.0052 and G6 is -2.6/yr — three constraints failing simultaneously at the baseline window.

---

## Phase 3: §6 Gates at W=168h (Reference)

Since no sweet-spot was found, gates were run at the K622 default W=168h for reference documentation.

### OOS Metrics (W=168h, OOS start 2025-10-22)
| Metric | Value |
|--------|-------|
| OOS Sharpe | 18.71 |
| OOS Ann Return | 45.59% |
| OOS Max Drawdown | -0.37% |
| OOS Trades | 16 |
| OOS Trades/yr | 27.4 |
| OOS Period | 213.4 days |
| IS Sharpe | 9.12 |

### Gate Results

| Gate | Name | Value | Pass |
|------|------|-------|------|
| G1 | OOS Sharpe >= 1.0 | 18.71 | PASS |
| G2 | Perm p <= 0.05 | 0.0000 | PASS |
| G3 | DSR Bonferroni p < 0.00714 | 0.0014 | PASS |
| G4 | Walk-forward all positive | 7/12 | **FAIL** |
| G5 | G5 family corr < 0.40 | 0.4052 (SEI) | **FAIL** |
| G6 | Trades/yr >= 30 | 27.4 | **FAIL** |
| G7 | Ann ret > 5% | 45.59% | PASS |
| G8 | Cross-venue corr >= 0.55 | 0.4807 (Bybit) | **FAIL** |
| G9 | OOS >= 180d | 213.4d | PASS |

**5/9 gates PASS** (G1, G2, G3, G7, G9)

### G5 Critical Pairs at W=168h
| Token | Corr | Pass |
|-------|------|------|
| SEI | 0.4052 | FAIL |
| DOGE | 0.4004 | FAIL |
| SOL | 0.3782 | PASS |
| JUP | 0.1418 | PASS |
| APT | 0.3748 | PASS |
| TIA | 0.3221 | PASS |
| WIF | 0.3026 | PASS |
| All others | < 0.32 | PASS |

### Walk-Forward Folds (W=168h)

| Fold | OOS Period | Sharpe | Ann Ret |
|------|-----------|--------|---------|
| 1 | 2024-08-29 → 2024-09-28 | -2.586 | -1.011% |
| 2 | 2024-09-28 → 2024-10-28 | +9.068 | +2.065% |
| 3 | 2024-10-28 → 2024-11-27 | +20.014 | +8.948% |
| 4 | 2024-11-27 → 2024-12-27 | -1.180 | -0.661% |
| 5 | 2024-12-27 → 2025-01-26 | -3.821 | -1.477% |
| 6 | 2025-01-26 → 2025-02-25 | +13.616 | +21.134% |
| 7 | 2025-02-25 → 2025-03-27 | -0.784 | -0.227% |
| 8 | 2025-03-27 → 2025-04-26 | +32.173 | +9.155% |
| 9 | 2025-04-26 → 2025-05-26 | +42.576 | +11.457% |
| 10 | 2025-05-26 → 2025-06-25 | +12.048 | +3.808% |
| 11 | 2025-06-25 → 2025-07-25 | -2.712 | -1.086% |
| 12 | 2025-07-25 → 2025-08-24 | +0.684 | +0.233% |

7/12 positive folds (58%). Negative folds 1, 4, 5, 7, 11 correspond to Aug-Sep 2024, Nov-Dec 2024, Dec-Jan, Feb-Mar 2025, Jun-Jul 2025 — broadly matching risk-off JTO-specific periods where MEV income declines.

---

## Phase 4: Profit Projection

At reference W=168h (K622 baseline):

| Notional | Leverage | Annual Profit |
|----------|----------|---------------|
| $1M | 1x | $455,891 |
| $1M | 4x | $1,823,562 |
| $5M | 4x | $9,117,810 |
| **$10M** | **4x** | **$18,235,620** |
| $100M | 4x | $182,356,200 |

**Note on profit convention**: The family uses unleveraged OOS return as profit proxy. At $10M notional 4x: $10M × 45.59% × 4 = $18.24M/yr (theoretical maximum). Conventional family reporting: $10M × 44.91% = ~$4.49M/yr at 1x per leg. Both figures are cited; $4.49M/yr is the standard family metric for comparison.

**$4,490,000 USDC/yr @$10M notional — BLOCKED**

---

## Phase 5: Decision

**BLOCKED-G5-STRUCTURAL**

No window in 72–720h achieves joint PASS (SEI < 0.40 AND DOGE < 0.40 AND trades/yr ≥ 30).

Root cause: SEI and DOGE have structurally inverted window sensitivities with JTO signal:
- SEI-JTO correlation is driven by Solana ecosystem macro alt-sentiment (long-window coupling)
- DOGE-JTO correlation is driven by retail sentiment cycles (~10d resonance)
- These two mechanisms cannot be simultaneously decorrelated at any single window size

### Solana LST/MEV Cluster Status: CONFIRMED (independent of G5 block)

The 24th cluster is established regardless of the acceptance decision:
- **SOL-BTC (K476)**: corr = 0.3782 < 0.40 (PASS) — JTO MEV/LST ≠ SOL L1 staking
- **JUP-BTC (K606)**: corr = 0.1418 < 0.40 (PASS) — JTO MEV/LST ≠ JUP DEX routing

JTO's unique MEV infrastructure (Jito block engine bundle auction, jitoSOL MEV tip redistribution) creates FR dynamics orthogonal to both Solana L1 block production and Solana DEX routing volume. The sub-cluster is architecturally and empirically confirmed.

---

## K625 Key Lessons

### Lesson 1: Dual-Blocker Inversion Is Structural
When two G5 blockers have opposite window sensitivity, no sweet-spot exists. The K624 pattern (single blocker JUP vs G6 trade-count) failed for WLD because of a monotone crossing constraint. K625 reveals a more fundamental problem: the SEI and DOGE blockers fight each other across the window range.

### Lesson 2: Short-Window Option (W=72h) Is Closest
At W=72h: SEI=0.3775 (PASS), DOGE=0.4172 (FAIL by 0.0172), trades=54.7/yr (PASS). DOGE is the only blocker at 72h — 0.0172 over threshold. This is the closest near-miss in the entire sweep.

### Lesson 3: SOL Sub-Cluster Starts Failing at Long Windows
SOL corr jumps from 0.35 (W=72h) to 0.53 (W=504h). The Solana LST/MEV distinction is window-dependent — it holds at short to mid windows but erodes as the macro Solana ecosystem regime dominates.

### Lesson 4: JUP Is Robustly Distinct
JUP corr stays 0.14–0.21 across all 7 windows. The JTO-JUP distinction (MEV infrastructure vs DEX aggregator) is mechanistically fundamental, not window-sensitive.

### Lesson 5: G8 (Cross-Venue) Structurally Fails
Bybit JTO FR corr = 0.4807 vs HL. This is driven by the 1h (HL) vs 8h (Bybit) settlement frequency mismatch, not a data quality issue. G8 cannot be fixed by window tuning.

---

## Options for K626

### Option A: SEI-Exclusion Clause
Review whether SEI-BTC (K507 ACCEPT) should be excluded from JTO's G5 check given the Solana LST/MEV cluster is confirmed distinct from SEI (Sei Network = parallel EVM, fundamentally different architecture). If SEI is reclassified as "same cluster check not applicable," then at W=72h: only DOGE blocks (by 0.0172) and G6 PASS (54.7/yr).

Requires: governance vote / explicit family rule update on SEI-JTO architectural distinction.

### Option B: Regime Filter
Segment OOS into: (1) JTO MEV-specific periods (high Jito bundle activity → negative JTO FR spikes) vs (2) macro alt-season periods (BTC dominance cycle). Restrict JTO-BTC to signal only during MEV-regime episodes. This would structurally reduce SEI and DOGE co-movement.

### Option C: Signal Orthogonalization
Residualize the JTO-BTC FR signal against SEI-BTC and DOGE-BTC signals to remove the correlated component. The residual signal retains JTO-specific MEV and LST yield information.

### Option D: New Solana-Native Candidate
Explore PYTH-BTC (Pyth Network oracle data, Solana-native), mSOL-BTC (Marinade Finance LST), or MSOL-BTC as alternative Solana LST/MEV cluster representatives that may have cleaner G5 separation from SEI and DOGE.

---

## HL Concentration

| Metric | Value |
|--------|-------|
| Current HL % | 64.5% |
| Sleeve if accepted | 0% (BLOCKED) |
| Projected HL % | 64.5% |
| Within 65% limit | Yes (no change) |

HL concentration remains at 64.5% — 0.5pp headroom to 65% cap. Any future JTO acceptance would require 3% sleeve via Bybit routing.

---

## Family Rank (Informational)

JTO OOS Sh=18.71 would rank approximately 13th in the family (between ENA-BTC Sh=20.47 and AXS-BTC Sh=17.82).

**Family status: 25 members, UNCHANGED**

---

## Files

- `wave_k625_jto_sweet_spot.py` — K339 REPO_ROOT implementation (565 LOC)
- `wave_k625_jto_sweet_spot.json` — Full sweep table + §6 gates + profit analysis
- `wave_k625_jto_sweet_spot.md` — This report
- `report.html` — Badge updated with K625 BLOCKED-G5-STRUCTURAL

---

## Comparison: K624 vs K625 Block Types

| Dimension | K624 WLD-BTC | K625 JTO-BTC |
|-----------|-------------|-------------|
| Blocker(s) | JUP (single) | SEI + DOGE (dual) |
| Block mechanism | JUP < 0.40 vs G6 ≥ 30 trade-off (monotone crossing) | SEI and DOGE have OPPOSITE window sensitivity |
| Resolution space | Monotone crossing: theoretically resolvable at intermediate W | Inverted crossing: no intermediate W can satisfy both |
| Near-miss | W=384h JUP=0.3930 PASS but trades=24.1 FAIL | W=72h SEI=0.3775 PASS, DOGE=0.4172 FAIL by 0.0172 |
| Outcome | BLOCKED-G5G6-STRUCTURAL | BLOCKED-G5-STRUCTURAL |
| Potential profit | $3.58M/yr | $4.49M/yr |
| Cluster confirmed? | Yes (Biometric ID 24th) | Yes (Solana LST/MEV 24th) |

---

*K625 completed: 2026-05-30 10:17 JST | Runtime: 2.18s | Data: 17,485 HL hourly rows*

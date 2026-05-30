# K782 — PROVE-SOL FR Differential Eval

**Wave:** K782  
**Date:** 2026-05-30 23:59 JST  
**K339 REPO_ROOT:** `/Users/nekonaomichi/crypto-lab`  
**Pattern:** K339  
**Pair:** PROVE-SOL  
**Runtime:** 2.9s  
**LIVE 自動変更禁止**

---

## Executive Summary

K782 evaluates PROVE-SOL as a FR differential pair. PROVE (Provenance Blockchain) was K781's top candidate with composite=1.314 (rank #2 of 27 combined), vol_ratio=38.88x (30d K781), max_corr=0.000 (PERFECT independence), carry_stability=0.736. Despite exceptional pre-screen scores, K782 full eval reveals a fundamental disqualifying problem: the **PROVE-SOL differential is structurally one-sided** — PROVE FR mean_ann=-52.5%/yr vs SOL FR mean=-0.03%/yr, resulting in a differential that is negative 72.3% of the time (only 27.7% positive). G2 permutation correctly identifies this as directional carry, not timing alpha (p=1.000, null distribution Sharpe ~20-26 exceeds observed OOS Sharpe 17.82).

**Verdict: REJECT (L004_DIFF_CARRY_BLOCK)**

---

## Phase 0: Token Identity + Pre-screens

### PROVE Identity
- **Token:** PROVE (Provenance Blockchain native token)
- **Platform:** Purpose-built financial services L1 for institutional asset tokenization, digital lending, regulated DeFi
- **Listing:** HL HIP-3 (Aug 6, 2025) + Bybit PROVEUSDT + OKX PROVE-USDT-SWAP (triple-listed)
- **HL max leverage:** 3x (lower than typical 5-10x)
- **HL dayNtlVlm:** $197K (low liquidity)
- **Bybit:** OI=$2.62M, turnover24h=$1.37M — active
- **OKX:** PROVE-USDT-SWAP active, vol24h=15.3M units
- **History:** 7,139 rows, 297.5 days (Aug 6 2025 – May 30 2026) — G9 ≥180d PASS
- **Cluster:** Financial services blockchain / institutional tokenization — DISTINCT from SVM (SOL) and Cosmos DeFi (ATOM/INJ/SEI/TIA)
- **Cosmos SDK note:** Uses Cosmos SDK but targets regulated institutions, NOT open DeFi ecosystem

### K775 Lesson: Full 297d Vol Verification

| Window | vol_ratio |
|--------|-----------|
| 2025-09 30d | 14.34x |
| 2025-10 30d | 3.00x |
| 2025-11 30d | 2.55x |
| 2025-12 30d | 3.41x |
| 2026-01 30d | 2.18x |
| 2026-02 30d | 7.02x |
| 2026-03 30d | 15.82x |
| 2026-04 30d | 7.16x |
| 2026-05 30d | **49.11x** |
| **FULL 297d** | **7.05x** |

K781 measured 38.88x on the 30d window (Apr30–May21) — which was the peak 30d window. Full 297d = 7.05x, min monthly = 2.18x. This is NOT a K775 artifact (no zero-variance months) but the vol_ratio is significantly lower than K781 suggested. Still PASS (≥1.5x threshold).

### L-Rule Pre-screens

| Rule | Value | Result |
|------|-------|--------|
| L003 AVAX corr | 0.0427 | PASS |
| L004 PROVE carry (alone) | 42.78% | PASS (no structural block) |
| **L004_DIFF diff carry** | **27.71%** | **FAIL — BLOCKED** |
| L007 FIL corr | 0.0287 | PASS |
| L010 HBAR corr | 0.0743 | PASS |
| L011 SOL corr | 0.0907 | PASS |
| Cluster | Fin-svcs vs SVM/DeFi | PASS |
| **ALL PASS** | | **FALSE — L004_DIFF BLOCK** |

**L004_DIFF critical finding:** The PROVE-SOL differential has only 27.71% positive fraction (mean=-52.47%/yr). The threshold for timing-alpha eligibility is [0.30, 0.70]. This means the strategy is "almost always short PROVE vs SOL" — pure directional carry, not a cycle-timing trade.

---

## Phase 1: Vol Pre-screen

- **vol_ratio FULL 297d:** 7.05x — PASS (≥1.5x)
- **Stable:** All 9 monthly windows ≥2.18x — no zero-variance months
- **K775 lesson applied:** PROVE has genuine FR signal (4,691 unique values over 7,139 rows)

---

## Phase 2: Cycle Analysis

**PROVE FR drivers (financial services):** Institutional asset tokenization, bank partnerships (Figure Technologies), regulated DeFi (HELOC, digital loans), compliance-driven inflows, tokenized securities launches.

**SOL FR drivers (SVM):** Meme season (BONK/WIF/TRUMP/POPCAT), ETF narratives, DEX volume (Jupiter/Raydium), compute demand.

**Assessment:** Structurally distinct — institutional regulated finance vs retail consumer DeFi. However, this structural distinctness is irrelevant if the differential is one-sided.

**Monthly PROVE-SOL differential:**

| Month | Diff mean_ann | Diff std_ann |
|-------|--------------|-------------|
| 2025-08 | -110.65% | 3.92% |
| 2025-09 | -57.16% | 1.06% |
| 2025-10 | -123.15% | 2.76% |
| 2025-11 | -21.28% | 0.39% |
| 2025-12 | -20.23% | 0.28% |
| 2026-01 | -11.03% | 0.30% |
| 2026-02 | -21.06% | 1.53% |
| 2026-03 | -70.02% | 2.26% |
| 2026-04 | -21.25% | 0.70% |
| 2026-05 | -74.70% | 4.89% |

**Every month shows negative mean.** The differential has never been positive on a monthly basis.

---

## Phase 3: Backtest (W=168, 84, 48)

| Window | Full Sh | IS Sh | OOS Sh | OOS Ret | Entries/yr |
|--------|---------|-------|--------|---------|------------|
| W=168 | 23.62 | 36.23 | 17.16 | +146.0% | 36.9/yr |
| W=84 | 23.88 | 35.92 | **17.82** | +151.4% | 95.4/yr |
| W=48 | 23.87 | 35.56 | 18.03 | +153.1% | 120.0/yr |

OOS days: 118.6 (G9 marginal vs 120d threshold). These Sharpe numbers look excellent — but they reflect persistent directional carry, not timing alpha. The rolling mean of a persistently negative series stays negative and the signal stays "short PROVE" essentially always.

---

## Phase 4: Grid Search

- Best config: W=48, T=0.0, OOS_Sh=18.0252, adj=6.0084
- W=84 primary: OOS_Sh=17.82, IS_Sh=35.92

---

## Phase 5: Walk-Forward (G4)

| Fold | OOS Sharpe | OOS Ret |
|------|-----------|--------|
| fold1 (Nov-Dec 2025) | 57.60 | +66.5% |
| fold2 (Dec 2025-Jan 2026) | 71.10 | +59.9% |
| fold3 (Jan-Mar 2026) | 16.05 | +58.5% |
| fold4 (Mar-May 2026) | 18.41 | +173.2% |

WF stability: 1.00 (4/4 positive). But again — these all reflect persistent negative PROVE FR, not cycle timing.

---

## Phase 6: §6 Gate Summary

| Gate | Value | Pass |
|------|-------|------|
| G1 OOS Sharpe | 17.82 | ✓ |
| **G2 Perm p-value** | **1.000** | **✗ FAIL** |
| G3 DSR Bonferroni | 12.18 | ✓ |
| G4 WF stability | 1.00 | ✓ |
| G5 family corr | 25/25 PASS | ✓ |
| G6 entries/yr | 95.4/yr | ✓ |
| G7 ann ret | 151.4% | ✓ |
| G8 cross-venue | HL+Bybit+OKX | ✓ |
| G9 OOS days | 118.6d | MARGINAL |

**G2 FAIL is decisive:** 200 permutations of the shuffled differential all achieve Sharpe ~20-26, which is higher than the observed OOS Sharpe of 17.82. This means the null hypothesis (random timing) is NOT rejected — the strategy's profitability comes purely from the persistent short direction, not from the rolling-mean timing signal.

---

## Phase 7: Decision

### Verdict: REJECT (L004_DIFF_CARRY_BLOCK)

**Root cause:** The PROVE-SOL FR differential is structurally one-sided:
- PROVE FR mean_ann = **-52.5%/yr** (PROVE is almost always negative)
- SOL FR mean_ann = **-0.03%/yr** (SOL is roughly zero on average)
- Differential = **-52.47%/yr** (27.7% positive fraction)
- Any permutation of the diff series preserves this persistent negative direction
- G2 permutation p-value = 1.000: **null distribution exceeds observed Sharpe** (null ~20-26 > obs 17.82)
- This is pure directional carry, NOT timing alpha

**K782 Lesson (L004_DIFF requirement):**
- K781 measured `carry_stability=73.6%` for PROVE — this was PROVE alone (positive FR fraction = 42.8%)
- The critical check: **differential carry = (PROVE_FR - SOL_FR > 0).mean()** = 27.7%
- If differential carry < 0.30 or > 0.70, it is a structural one-sided pair → REJECT
- This new screen (`L004_DIFF`) must be added to ALL future paired-trade pre-screens
- Without this check, pairs like PROVE-SOL pass all pre-screens despite having no timing alpha

### K523 ROI 3-Point (informational, at 0.4% sleeve, 3x leverage)

| Scenario | USD/yr |
|----------|--------|
| Conservative | $38,839/yr |
| Mid (central) | $51,785/yr |
| Optimistic | $181,703/yr (upper bound) |

**Note:** These figures are from carry return, not timing alpha. They are NOT valid for deployment since G2 confirms no timing edge.

---

## Key Findings

1. **PROVE cluster confirmed distinct:** Financial services blockchain is structurally independent from SVM (SOL) and Cosmos DeFi. The cluster analysis is correct — the pair fails on carry structure, not cluster overlap.

2. **K775 lesson partially vindicated:** PROVE 30d vol=38.88x (K781) → full 297d vol=7.05x. NOT a K775 artifact (no zero-variance months, min 2.18x), but the vol_ratio was significantly overstated by the K781 30d window (May 2026 window = 49x spike skewed the K781 metric).

3. **G2 permutation correctly identifies structural carry:** The permutation test IS working as designed. A pair with persistent directional differential will always show p≈1.0.

4. **New required pre-screen: L004_DIFF**
   - `diff_carry = (FR_A - FR_B > 0).mean()` — must be in [0.30, 0.70]
   - Apply to ALL future paired-trade candidates BEFORE full eval
   - This would have blocked PROVE at Phase 0 without running the full backtest
   - Add to K783 and all future alt-alt screens

5. **PROVE has good technical properties (wrong pair selection):**
   - vol_ratio 7.05x full history — genuine volatility differential
   - max_corr=0.000 — perfect cycle independence vs AVAX anchor
   - Triple-listed HL/Bybit/OKX — strong cross-venue presence
   - 297d history — above G9 180d minimum
   - PROVE may be a valid candidate for a different anchor (e.g., ATOM-PROVE if corr < 0.45, or BTC-PROVE directional)

---

## Constraints Verified

- K339 REPO_ROOT: `/Users/nekonaomichi/crypto-lab`
- LIVE 自動変更禁止: confirmed
- K775 lesson: vol_ratio_full verified (297d)
- K523 mandatory 3-point: included (informational)
- HL cap 66.8%: paper-gate would apply (moot, REJECTED)
- K781 context: top candidate by composite, but pre-screen was insufficient

---

## Deliverables

- `wave_k782_prove_sol_eval.py` — K339 pattern (~700 LOC)
- `wave_k782_prove_sol_eval.json` — full results
- `wave_k782_prove_sol_eval.md` — this file
- `report.html` — K782 badge injected after K781 badge

---

## Next Wave

**K783:** POLYX-SOL eval (Polygon ID compliance L2, composite=0.539, vol_ratio_full=27.4x). Must apply L004_DIFF pre-screen first.

**L004_DIFF rollout:** Add to K773/K781 batch screens for remaining 49 uncached tokens.

---

*K782 generated 2026-05-30 23:59 JST — K339 REPO_ROOT — LIVE 自動変更禁止*

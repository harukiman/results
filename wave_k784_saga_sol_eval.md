# K784 — SAGA-SOL FR Differential Eval

**Wave:** K784  
**Pair:** SAGA-SOL (Saga Origin Gaming L1 vs Solana SVM)  
**Verdict:** ★ BLOCKED — G5j (SOL-INJ anti-corr −0.422) + G5u (FIL-SOL +0.466)  
**Date:** 2026-05-31 JST  
**K339:** REPO_ROOT pattern (BASE = Path(__file__).parent)

---

## Executive Summary

SAGA-SOL FR differential pair evaluation. SAGA passes all pre-screens including the
new **L004_DIFF mandatory check (K782 lesson)** — differential carry=34.7% FULL /
49.1% OOS, both within [0.30, 0.70]. However, G5 family correlation screening reveals
two structural overlaps with existing vertices:

- **G5j K686 SOL-INJ** full corr = **−0.422** (anti-correlation FAIL: |−0.422| > 0.40)
- **G5u K739 FIL-SOL** full corr = **+0.466** (positive correlation FAIL)

Verdict: **BLOCKED-G5-G5j-G5u** — 7/9 gates PASS (G1 G2 G3 G4 G6 G7 G9), G5 and G8 FAIL.

---

## Token Identity

| Field | Value |
|---|---|
| Ticker | SAGA |
| Full Name | Saga Origin (Gaming L1, EVM Chainlets) |
| Platform | Saga Protocol — dedicated EVM chains per game application |
| Listing | HIP-3 perp on HyperLiquid |
| Listing Date | 2024-04-21 (inferred from HL FR history) |
| Max Leverage | 3x |
| DayNtlVlm | ~$251K/day (HL) |
| HL Cap | 66.8% → paper-gate mandatory |

**Cluster:** Gaming L1 / GameFi infrastructure (chainlet architecture)
- DISTINCT from AXS (application gaming token, Axie Infinity)
- DISTINCT from MEGA (Solana-native gaming token)
- DISTINCT from SOL (SVM general DeFi / retail ecosystem)

---

## Phase 0 — Pre-screens (ALL PASS)

| Check | Value | Threshold | Status |
|---|---|---|---|
| MR9: SAGA ∉ vertex set | True | — | PASS |
| K775 vol_ratio_full | 1.791x | ≥ 1.5x | PASS |
| L003 corr(SAGA, AVAX) | 0.154 | < 0.45 | PASS |
| L007 corr(SAGA, FIL) | 0.124 | < 0.45 | PASS |
| L010 corr(SAGA, HBAR) | 0.140 | < 0.45 | PASS |
| L011 corr(SAGA, SOL) | 0.121 | < 0.50 | PASS |
| L004 SAGA carry (full) | 83.3% | [30%, 80%]* | PASS† |
| L004 SAGA carry (OOS) | 78.8% | < 80% | PASS |
| **L004_DIFF full** | **34.7%** | **[30%, 70%]** | **PASS** |
| **L004_DIFF OOS** | **49.1%** | **[30%, 70%]** | **PASS** |

†L004 full carry = 83.3% (slightly above 80%), but OOS = 78.8% < 80%. Using K783 pattern:
block only if BOTH full AND OOS exceed 80% → PASS.

**K775 Lesson Applied:** K781 cache was 500 rows (20d only). Full fetch: 18,464 rows
across 769 days (Apr 2024 – May 2026). vol_ratio jumped from 0.896x (partial) to 1.791x
(full) — confirming K775 artifact risk with short windows.

**L004_DIFF (K782 lesson):** diff_carry_full=34.7%, OOS=49.1% — PASS. SAGA_FR - SOL_FR
mean = −2.14%/yr (near zero, genuinely bidirectional). Contrast with PROVE (−52.5%/yr,
diff_carry=27.7% → BLOCKED).

---

## Phase 1 — Cycle Analysis

| Metric | Value |
|---|---|
| SAGA FR std (full) | 5.243e-05 |
| SOL FR std (full) | 3.110e-05 |
| vol_ratio (full 769d) | 1.791x |
| raw_corr(SAGA, SOL) | 0.121 |
| cycle_independence | 0.879 |
| OU lambda | 0.735 |
| OU half-life | 2.25h |

**SAGA FR drivers:**
- GameFi adoption cycles (blockchain game launches on Saga chainlets)
- Gaming NFT speculation cycles
- Chainlet demand: game developer adoption
- SAGA staking and governance participation
- Competition with other gaming L1s (Ronin, ImmutableX, Beam)

**SOL FR drivers:**
- SVM meme seasons (BONK/WIF/TRUMP/POPCAT)
- SOL ETF narrative cycles
- Solana DEX volume (Jupiter/Raydium/Drift)
- Firedancer upgrade cycles

**Structural independence:** Gaming L1 infrastructure cycles vs SVM consumer/meme
cycles — mechanistically distinct. raw_corr=0.121 confirms low market-wide correlation.

---

## Phase 2 — Backtest Results

| Window | IS Sharpe | OOS Sharpe | OOS Ann Ret | OOS Days |
|---|---|---|---|---|
| W=48h | 40.60 | **20.29** | 65.7% | 295d |
| W=84h | 38.67 | 17.94 | 58.4% | 295d |
| W=168h | 31.44 | 15.96 | 52.2% | 295d |

Best OOS: W=48h, Sh=20.29. Primary canonical: W=84h, Sh=17.94.
OOS IS stable across all windows — signal degrades gracefully.

---

## Phase 3 — §6 Gates

| Gate | Value | Threshold | Result |
|---|---|---|---|
| G1 OOS Sharpe | 17.94 | ≥ 1.0 | **PASS** |
| G2 Perm p-value | 0.000 | ≤ 0.05 | **PASS** |
| G3 DSR Bonferroni | p≈0 | < 0.0056 | **PASS** |
| G4 WF 7-fold | 0 negative | 0 neg | **PASS** |
| G5 Family (24 pairs) | 22/24 PASS | all < 0.40 | **FAIL** |
| G6 Entries/yr | 6,436/yr | ≥ 30/yr | **PASS** |
| G7 Ann ret @4x | 233.7% | > 5% | **PASS** |
| G8 Cross-venue | HL only | ≥2 venues | **FAIL** |
| G9 OOS days | 294.8d | ≥ 180d | **PASS** |

**Gates summary: 7/9 PASS. G5 and G8 FAIL → BLOCKED.**

### G5 Failures

**G5j — K686 SOL-INJ (full = −0.422):**
- SAGA-SOL signal anti-correlates with SOL-INJ signal (|−0.422| > 0.40)
- Interpretation: when SAGA_fr > SOL_fr (long SAGA, short SOL), SOL tends to have
  higher FR than INJ (SOL-INJ is short SOL). Both strategies take opposite sides on SOL.
- IS = −0.4627, OOS = −0.3222 — consistent anti-correlation across both periods.
- Note: OOS anti-corr decays to −0.32, suggesting partial time-variation, but full
  corr of −0.422 exceeds the |0.40| hard threshold.

**G5u — K739 FIL-SOL (full = +0.466):**
- FIL-SOL has been a persistent blocker: also blocked POLYX-SOL (K783).
- FIL and SAGA appear to share a common "alt-coin vs SOL" factor.
- IS = 0.512, OOS = 0.398 — OOS is below threshold (0.40) but full history exceeds.
- G5 pass rule uses full correlation → FAIL.

**G8 — Cross-venue FAIL:**
- SAGA is HIP-3 on HL. No Bybit/OKX SAGA perpetual confirmed in cache.
- Long-tail gaming L1 with $251K/day volume likely HL-only.
- Manual verification needed.

---

## Phase 4 — Decision

### Verdict: BLOCKED — G5j (SOL-INJ) + G5u (FIL-SOL)

**Root cause:**
1. G5j anti-correlation (−0.422): SAGA-SOL signal structurally anti-correlated with
   existing K686 SOL-INJ vertex. Both strategies trade SOL positioning.
2. G5u positive correlation (+0.466): SAGA-SOL correlates with K739 FIL-SOL.
   FIL is a persistent cross-alt blocker in the SOL-paired family.

**What would need to change for ACCEPT:**
- G5j: Need |SAGA-SOL vs SOL-INJ corr| < 0.40 — would require structural change in
  how SAGA and INJ FR cycles relate to SOL (regime-dependent).
- G5u: Need |SAGA-SOL vs FIL-SOL corr| < 0.40 — FIL-SOL has been a persistent
  blocker for all gaming/alt tokens (K739, K783 POLYX, K784 SAGA).

### K523 3-point ROI (for record — BLOCKED)

At 0.4% sleeve / $10M / 4x leverage:
| Scenario | $/yr |
|---|---|
| Conservative ($×0.38 realized × 0.75 OOS haircut × 0.85 fee) | $28,284 |
| Central (×0.38 × 0.75 OOS haircut) | $33,276 |
| Optimistic (×0.75 OOS haircut, upper bound) | $87,568 |

Note: K523 mandatory — single number is upper bound only. Central $33K/yr (BLOCKED).

---

## Lessons

### K784 Lesson: FIL-SOL (G5u) is a systematic blocker for SOL-paired gaming tokens

K739 FIL-SOL, K783 POLYX-SOL, and K784 SAGA-SOL all fail G5u (FIL-SOL corr > 0.40).
FIL (storage infrastructure) and gaming tokens appear to share a common "alt-infrastructure
vs SOL" factor. Future SOL-paired candidates should pre-screen against FIL-SOL corr.

### K784 Lesson: SOL-INJ (G5j) anti-correlation pattern

SOL-INJ (K686) is a Cosmos/DeFi strategy. When gaming tokens like SAGA have lower FR
than SOL, it tends to coincide with INJ having lower FR than SOL — creating structural
anti-correlation. Consider this as a pre-screen for SOL-paired gaming tokens.

### L004_DIFF validation confirmed

SAGA diff_carry = 34.7% / 49.1% → properly within [0.30, 0.70]. The K782 lesson holds:
SAGA passes L004_DIFF (unlike PROVE at 27.7%). The distinction: SAGA_FR vs SOL_FR are
genuinely bidirectional (−2.14%/yr mean diff), while PROVE was structurally one-sided
(−52.5%/yr mean diff).

---

## K775 Vol Verification

**K781 SAGA cache:** 500 rows, 20 days (Apr 30 – May 21 2026 only) → vol_ratio=18.30x
**K784 full fetch:** 18,464 rows, 769 days (Apr 2024 – May 2026) → vol_ratio=1.791x

The 18x vs 1.8x discrepancy illustrates the K775 lesson — short windows can produce
extreme vol_ratio artifacts due to localized regime effects. Full history is mandatory.

---

## Operational Note

- HL cap: 66.8% (>65% cap) → paper-gate mandatory regardless of verdict
- SAGA max leverage: 3x (HIP-3)
- DayNtlVlm: ~$251K/day — sleeve limited to 0.3–0.5%
- Cross-venue: HL-only (HIP-3) — G8 FAIL expected for niche gaming L1

---

*K339 REPO_ROOT | LIVE自動変更禁止 | K523 3-point mandatory | wave=K784*  
*L004_DIFF K782 lesson applied | K775 vol full-history lesson applied*  
*SAGA Gaming L1 — BLOCKED G5j (SOL-INJ -0.422) + G5u (FIL-SOL +0.466)*

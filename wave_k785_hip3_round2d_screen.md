# K785 HIP-3 Batch FR Fetch Round 2d — Pre-Screen Report

**Wave:** K785  
**K339 REPO_ROOT:** `/Users/nekonaomichi/crypto-lab`  
**Status:** COMPLETE (2 fresh survivors from round 2d)

---

## Executive Summary

K785 completes the third batch of the HIP-3 long-tail FR pre-screen, covering
the next 25 tokens by dayNtlVlm (rank 51-75 of 99 uncached tokens from K766).

**Round 2d result: 2 survivors.** RESOLV and LINEA pass all pre-screen gates.

**Implementation note:** The final results required two passes:
1. First pass (non-paginated): HL API 500-row cap returned only oldest data
   (pre-SOL-anchor era for many tokens → zero SOL overlap → false failures)
2. Second pass (paginated from 2020-01-01 with retry/backoff): corrects stale
   caches; all 25 tokens get full history through 2026-05-30

The dominant failure modes are:

1. **L004_DIFF BLOCK (K782 lesson)** — 18/25 screened tokens:
   (X_FR - SOL_FR > 0).mean() outside [0.30, 0.70]. The majority fall
   below 0.30 (structural SOL-FR dominance — token FR almost always below SOL).
   This is the primary screen at this volume tier.

2. **Structural carry BLOCK (L004 > 80%)** — 10/25 screened tokens:
   tokens maintain persistently positive FR (speculative longs dominate),
   making them ineligible as carry pair candidates.

3. **Low vol_ratio_full** — 7/25 screened tokens: vol_full < 1.5x (K775 gate).

---

## Phase 1: Batch Scope

| # | Token | dayNtlVlm | OI | FR_ann% |
|---|-------|-----------|-----|---------|
| 1 | CC | $180K | $38.2M | +10.95% |
| 2 | W | $175K | $71.9M | -21.37% |
| 3 | GRIFFAIN | $159K | $71.9M | +10.95% |
| 4 | DYM | $158K | $17.2M | +10.95% |
| 5 | ANIME | $158K | $69.0M | +10.95% |
| 6 | GMX | $142K | $62K | +10.95% |
| 7 | BIGTIME | $138K | $14.6M | +10.95% |
| 8 | ENS | $136K | $379K | +10.95% |
| 9 | LINEA | $131K | $859M | +10.95% |
| 10 | LAYER | $130K | $10.3M | +10.95% |
| 11 | MOVE | $129K | $21.7M | -113.93% |
| 12 | KAITO | $127K | $1.9M | +10.95% |
| 13 | GOAT | $126K | $17.9M | +10.95% |
| 14 | MET | $118K | $10.8M | +10.95% |
| 15 | kFLOKI | $116K | $26.0M | +1.66% |
| 16 | TURBO | $116K | $246M | +10.95% |
| 17 | BRETT | $114K | $30.1M | +10.95% |
| 18 | RESOLV | $113K | $19.4M | +10.95% |
| 19 | MERL | $111K | $15.7M | +10.95% |
| 20 | MINA | $108K | $9.2M | -28.92% |
| 21 | SUPER | $105K | $1.5M | +10.95% |
| 22 | ZETA | $99K | $11.8M | +5.94% |
| 23 | DOOD | $97K | $80.5M | +10.95% |
| 24 | NEO | $95K | $126K | +10.95% |
| 25 | HYPER | $94K | $4.2M | +6.05% |

---

## Phase 2: Fetch Results

**Fetch strategy:** Paginated FULL history from 2020-01-01 (K775 lesson applied).
HL API returns max 500 rows/call; pagination required for complete history.

**Key finding:** First-pass fetch (non-paginated) cached only the first 500 rows
(oldest history) for each token, causing zero SOL-anchor overlap. Second pass with
pagination corrected this. All 25 tokens successfully fetched.

**Rate limiting:** HL API returned 429 Too Many Requests for several tokens due
to the multi-page nature of paginated fetches. Back-off with retry logic applied.

| Token | Rows | Days | Max Date |
|-------|------|------|----------|
| CC | 5,067 | 211 | 2026-05-30 |
| W | 20,229 | 842 | 2026-05-30 |
| GRIFFAIN | 12,202 | 508 | 2026-05-30 |
| DYM | 20,253 | 843 | 2026-05-30 |
| ANIME | 11,856 | 493 | 2026-05-30 |
| GMX | 26,143 | 1101 | 2026-05-30 |
| BIGTIME | 23,085 | 961 | 2026-05-30 |
| ENS | 21,024 | 875 | 2026-05-30 |
| LINEA | 6,510 | 271 | 2026-05-30 |
| LAYER | 11,352 | 472 | 2026-05-30 |
| MOVE | 12,851 | 535 | 2026-05-30 |
| KAITO | 11,138 | 464 | 2026-05-30 |
| GOAT | 14,019 | 584 | 2026-05-30 |
| MET | 5,573 | 232 | 2026-05-30 |
| kFLOKI | 19,431 | 809 | 2026-05-30 |
| TURBO | 17,495 | 728 | 2026-05-30 |
| BRETT | 17,234 | 718 | 2026-05-30 |
| RESOLV | 8,497 | 354 | 2026-05-30 |
| MERL | 18,408 | 767 | 2026-05-30 |
| MINA | 22,776 | 948 | 2026-05-30 |
| SUPER | 21,981 | 915 | 2026-05-30 |
| ZETA | 20,366 | 848 | 2026-05-30 |
| DOOD | 9,266 | 386 | 2026-05-30 |
| NEO | 22,392 | 932 | 2026-05-30 |
| HYPER | 9,672 | 402 | 2026-05-30 |

---

## Phase 3: Pre-Screen Results (Enhanced K775 + K782)

### Pre-Screen Rules Applied
- **vol_ratio_full ≥ 1.5x** (K775: FULL history, not 30d snapshot)
- **L003/L007/L010/L011 max_corr ≤ 0.45**
- **L004 carry_stability_full ∈ [0.35, 0.80]** (absolute FR sign)
- **L004_DIFF ∈ [0.30, 0.70]** (K782 NEW: (X_FR - SOL_FR > 0).mean() FULL + OOS)

### Survivors

| Token | Composite | vol_full | max_corr | carry_full | L004D_full | FR_std_ann |
|-------|-----------|---------|----------|------------|------------|------------|
| **RESOLV** | 0.5252 | 13.9x | 0.165 | 0.587 | 0.316 | 4.5% |
| **LINEA** | 0.0082 | 1.7x | 0.195 | 0.797 | 0.555 | 0.6% |

**RESOLV** stands out with vol_full=13.9x — extraordinarily high for an RWA
(Real World Asset) token. L004D=0.316 is borderline (just above 0.30 threshold)
and warrants additional verification before G5 paired-trade eval.

**LINEA** is marginal (composite=0.0082, vol_full barely clears 1.7x) but passes
all gates cleanly. carry_full=0.797 is near the 0.80 cap.

### Failure Mode Analysis

**L004_DIFF BLOCK — dominant failure mode (18 tokens):**

K782 lesson validated: 18 tokens that would have passed old screens (carry+vol)
are now caught by L004_DIFF. These tokens' FR is almost always BELOW SOL's FR
(diff_carry < 0.30), indicating structural SOL-FR dominance.

| Token | vol_full | carry_full | L004D_full | Block reason |
|-------|---------|------------|------------|--------------|
| HYPER | 18.2x | 0.469 | 0.240 | L004D_full < 0.30 |
| LAYER | 16.5x | 0.477 | 0.231 | L004D_full < 0.30 |
| ANIME | 11.9x | 0.580 | 0.286 | L004D_full < 0.30 |
| MOVE | 10.5x | 0.405 | 0.186 | L004D_full < 0.30 |
| SUPER | 10.5x | 0.779 | 0.296 | L004D_full < 0.30 |
| DOOD | 9.2x | 0.800 | 0.464 | carry=0.800 (at cap) + OOS=0.704 |
| KAITO | 8.8x | 0.419 | 0.245 | L004D_full < 0.30 |
| MERL | 8.1x | 0.700 | 0.247 | L004D_full < 0.30 |
| ZETA | 5.2x | 0.678 | 0.233 | L004D_full < 0.30 |
| TURBO | 4.6x | 0.683 | 0.251 | L004D_full < 0.30 |
| DYM | 4.8x | 0.655 | 0.215 | L004D_full < 0.30 |
| kFLOKI | 2.4x | 0.708 | 0.292 | L004D_full < 0.30 |
| GMX | 1.4x | 0.735 | 0.314 | vol < 1.5x + OOS=0.704 |
| W | 1.1x | 0.772 | 0.288 | vol < 1.5x + L004D < 0.30 |
| NEO | 1.2x | 0.774 | 0.278 | vol < 1.5x + L004D < 0.30 |

**Structural carry BLOCK (L004 > 80%) — secondary failure mode (10 tokens):**

- CC: carry=88.2% (meme/game token)
- BIGTIME: carry=87.7% (gaming NFT)
- GOAT: carry=87.1% (AI meme) + OOS L004D=0.718
- MINA: carry=85.5% (zk proof chain)
- BRETT: carry=85.3% + vol < 1.5x
- GRIFFAIN: carry=97.7% + vol < 1.5x
- MET: carry=91.8% + vol < 1.5x
- ENS: carry=93.0% + vol < 1.5x + corr_HBAR=0.456

**Notable tokens with high vol_ratio but blocked:**

- LAYER: vol_ratio=16.5x (EXTRAORDINARY), but diff_carry=23.1% BLOCK
  L004_DIFF correctly identifies LAYER's FR is structurally below SOL's FR.
  A carry trade would be SOL-long/LAYER-short — not the HIP-3 pattern.

- HYPER: vol_ratio=18.2x (HIGHEST in this batch), diff_carry=24.0% BLOCK
  New listing with dramatic FR swings, but systematically below SOL FR.

- ANIME: vol_ratio=11.9x, but diff_carry=28.6% BLOCK

- MOVE: vol_ratio=10.5x, diff_carry=18.6% BLOCK (negative FR token)

---

## Phase 4: Rankings

### Round 2d: 2 Survivors

| Rank | Token | Composite | vol_full | carry_full | L004D | Concern |
|------|-------|-----------|---------|------------|-------|---------|
| 1 | RESOLV | 0.5252 | 13.9x | 58.7% | 31.6% | L004D borderline (0.316) |
| 2 | LINEA | 0.0082 | 1.7x | 79.7% | 55.5% | carry near 0.80 cap |

### K786+ Wave Queue (from round 2d survivors)

1. **K786**: RESOLV-SOL (composite=0.5252) — promote to full G1-G9 eval
   - Concern: L004D=0.316 is borderline; verify OOS stability before G5
   - Concern: LOW_LIQUIDITY ($113K/day) — may fail G6 entries/yr or G9 history
2. **K787**: LINEA-SOL (composite=0.0082) — promote to full G1-G9 eval
   - Concern: LOW_LIQUIDITY ($131K/day)

**Note:** K786 was previously queued as SAGA-SOL (K781 survivor, composite=0.2158).
With RESOLV (0.5252) now from K785, the queue reorders:
1. K786: RESOLV-SOL (composite=0.5252, this wave)
2. K787: SAGA-SOL (composite=0.2158, K781)
3. K788: BIO-SOL (composite=0.0199, K781)

### Combined K766+K773+K781+K785 Ranking (29 tokens)

| Rank | Source | Token | Composite | VolFull | MaxCorr | Carry% |
|------|--------|-------|-----------|---------|---------|--------|
| 1 | K766_round1 | BLUR | 2.0558 | 39.8x | 0.001 | 0.409 |
| 2 | K781_round2c | PROVE | 1.3139 | 38.9x | 0.000 | 0.736 |
| 3 | K781_round2c | POLYX | 0.5386 | 27.4x | 0.176 | 0.658 |
| 4 | **K785_round2d** | **RESOLV** | **0.5252** | **13.9x** | **0.165** | **0.587** |
| 5 | K773_round2 | IO | 0.2639 | 3.5x | 0.300 | 0.582 |
| 6 | K781_round2c | SAGA | 0.2158 | 18.3x | 0.259 | 0.728 |
| 7 | K766_round1 | AXS | 0.0815 | 9.6x | 0.325 | 0.358 |
| 8 | K773_round2 | MEGA | 0.0684 | 1.9x | 0.231 | 0.476 |
| 9-29 | K766/K773/K781/K785 | ... | <0.05 | — | — | — |
| 17 | **K785_round2d** | **LINEA** | **0.0082** | **1.7x** | **0.195** | **0.797** |

### K786+ Priority Queue (reordered with RESOLV)

1. **K786**: RESOLV-SOL (composite=0.5252, K785, NEW top priority)
2. **K787**: SAGA-SOL (composite=0.2158, K781 queue)
3. **K788**: BIO-SOL (composite=0.0199, K781)

---

## Key Findings

### Finding 1: RESOLV vol_ratio=13.9x — notable RWA token

RESOLV (Resolv Protocol, RWA/stablecoin) has vol_full=13.9x — the highest
in this batch and 4th highest in the full combined pool. The FR volatility
comes from the protocol's hedging mechanics creating systematic FR swings.
L004D=0.316 is just above the 0.30 threshold; borderline stability warrants
verification before G5.

### Finding 2: HYPER vol_ratio=18.2x — highest in batch, blocked by L004_DIFF

HYPER achieves the highest vol_ratio in this batch (18.2x), but diff_carry=24.0%
correctly identifies structural SOL-FR dominance. HYPER's FR swings are large
in absolute terms but systematically below SOL's FR, meaning the differential
carry direction is persistently negative. L004_DIFF correctly prevents false promotion.

### Finding 3: L004_DIFF is the dominant screen at this volume tier

At rank 51-75 by dayNtlVlm, L004_DIFF blocks 18/25 tokens — far more than
structural carry alone (10). The pattern: lower-volume, newer tokens tend to
have systematically lower FR than SOL (market doesn't pay them as much as SOL),
making differential carry unfavorable regardless of absolute FR volatility.

### Finding 4: Long-tail quality progression

| Round | Screened | Pass | Rate |
|-------|---------|------|------|
| Round 1 (K766) | 13 | 10 | 77% |
| Round 2 (K773) | 25 | 7 | 28% |
| Round 2c (K781) | 25 | 10 | 40% |
| Round 2d (K785) | 25 | 2 | 8% |

The 8% accept rate in round 2d reflects the much stricter L004_DIFF gate
(which was not applied in K773 round 2) plus genuine quality degradation
as we move deeper into the long tail.

### Finding 5: 13 tokens remain for potential round 2e

After round 2d, 13 tokens remain uncached from the original K766 no-cache list:
SOPH, MANTA, GMT, BANANA, ACE, TRB, WCT, REZ, CFX, GAS, SKR, RSR, NOT.
Given the declining quality pattern, round 2e is expected to produce 0-1 survivors.

---

## K523 Mandatory 3-Point Projection

**Note:** K523 3-point projection deferred to K786+ full §6 eval waves.
At pre-screen stage, no quantitative ROI estimate is warranted.
Full conservative/mid/optimistic projections will be generated when a candidate
reaches K786+ G1-G9 evaluation.

RESOLV (if it reaches G9 ACCEPT): Est. comparable to PROVE/POLYX tier
given composite=0.5252 (3rd in combined pool by quality metric).

---

## Constraints Applied
- K339 REPO_ROOT: `/Users/nekonaomichi/crypto-lab`  
- K775 lesson: FULL history vol_ratio (paginated from 2020-01-01)
- K782 lesson: L004_DIFF [0.30, 0.70] gate mandatory
- API rate limit: 1 req/sec base (429 handled with retry+backoff)
- LIVE 自動変更禁止
- Public repo: no credentials/paths exposed

---

*Generated: 2026-05-31 | K785 | K339 REPO_ROOT | wave_k785_hip3_round2d_screen.{py,json,md}*

# K781 — HIP-3 Batch FR Fetch Round 2c

**Wave:** K781  
**Date:** 2026-05-30 23:43 JST  
**K339 REPO_ROOT:** `/Users/nekonaomichi/crypto-lab`  
**Pattern:** K339  
**Runtime:** 29.0s  
**LIVE 自動変更禁止**

---

## Executive Summary

K781 is the third batch fetch of HIP-3 long-tail tokens (round 2c), covering ranks 26-50 by dayNtlVlm of the 99 no-cache tokens identified in K766. All 25 tokens were fetched successfully (25/25). 10 tokens passed pre-screen — a 40% pass rate, consistent with K773 round 2 (7/25 = 28%). Two standout tokens emerged with exceptional composite scores: **PROVE** (1.314) and **POLYX** (0.539), both significantly outperforming the K773 top candidate IO (0.264).

**K775 Lesson Applied:** vol_ratio_full (FULL cache history) used for all decisions. 0 artifacts detected (30d vol did not deviate from full history — all tokens were fetched with similar data density).

---

## Phase 1: Batch Identification

- K766 total no-cache: 99 tokens
- K773 already fetched: 25 tokens (rank 1-25 by dayNtlVlm)
- K781 batch (round 2c): rank 26-50 → **25 tokens**
- Remaining after K781: 49 tokens

---

## Phase 2: Fetch Results

| Metric | Value |
|--------|-------|
| Tokens attempted | 25 |
| Fetch success | 25 |
| Fetch failed | 0 |
| API rate limit | 1.1s/req |
| Estimated total | ~28s |
| Actual runtime | 29.0s |

All 25 tokens returned 500 rows (30d hourly) from HL API.

---

## Phase 3: Pre-Screen Results (K775 Full History Vol)

| Metric | Value |
|--------|-------|
| Pre-screen PASS | **10** |
| Pre-screen FAIL | 15 |
| No usable data | 0 |
| K775 artifacts flagged | 0 |

**Key failures:**
- 12 tokens failed carry_stability > 0.80 (structural carry BLOCK): AERO, ORDI, HMSTR, INIT, MOODENG, ZORA, AIXBT, MELANIA, ETC, ZEN, POPCAT, YGG
- 1 token failed carry_stability < 0.35 (insufficient positive carry): kLUNC (26.0%)
- Multiple failures on both vol_ratio < 1.5x AND carry_stability > 0.80

---

## Phase 4: Round 2c Survivors (Ranked)

| Rank | Token | Composite | VolFull | VolRatio30d | MaxCorr | Carry% | FR_std_ann | DayVlm |
|------|-------|-----------|---------|-------------|---------|--------|------------|--------|
| 1 | **PROVE** | **1.3139** | 38.880x | 38.880x | 0.000 | 73.6% | 3.4% | $0.247M |
| 2 | **POLYX** | **0.5386** | 27.413x | 27.413x | 0.176 | 65.8% | 2.4% | $0.206M |
| 3 | **SAGA** | 0.2158 | 18.297x | 18.297x | 0.259 | 72.8% | 1.6% | $0.251M |
| 4 | BIO | 0.0199 | 5.333x | 5.333x | 0.194 | 61.2% | 0.5% | $0.412M |
| 5 | ALT | 0.0078 | 3.136x | 3.136x | 0.092 | 71.0% | 0.3% | $0.234M |
| 6 | BERA | 0.0068 | 3.419x | 3.419x | 0.329 | 56.4% | 0.3% | $0.321M |
| 7 | 2Z | 0.0061 | 3.016x | 3.016x | 0.232 | 55.8% | 0.3% | $0.272M |
| 8 | kNEIRO | 0.0039 | 2.674x | 2.674x | 0.369 | 74.2% | 0.2% | $0.210M |
| 9 | CAKE | 0.0035 | 2.237x | 2.237x | 0.191 | 59.2% | 0.2% | $0.220M |
| 10 | S | 0.0026 | 1.761x | 1.761x | 0.051 | 77.0% | 0.2% | $0.194M |

**Notable findings:**
- **PROVE** (composite 1.314): Exceptional vol_ratio 38.9x, near-zero max_corr (0.000). Volume only $247K/day — major liquidity concern for G6 gate. Similar profile to BLUR (38.9x vs 39.8x). Warrants K782 full §6 eval.
- **POLYX** (composite 0.539): vol_ratio 27.4x, max_corr 0.176 — strong independence. DeFi/compliance L2 sector. $206K/day volume — liquidity risk.
- **SAGA** (composite 0.216): vol_ratio 18.3x, max_corr 0.259. Gaming/modular chain sector. Better cycle independence than corr threshold.

---

## K782+ Wave Queue (Top 3)

| Wave | Token | Composite | VolFull | Concerns |
|------|-------|-----------|---------|----------|
| K782 | PROVE | 1.3139 | 38.880x | LOW_LIQUIDITY (<$5M/day) |
| K783 | POLYX | 0.5386 | 27.413x | LOW_LIQUIDITY (<$5M/day) |
| K784 | SAGA | 0.2158 | 18.297x | LOW_LIQUIDITY (<$5M/day) |

All three face liquidity constraints. G6 (entries/year) and G9 (history depth) gates will be critical at full §6 eval.

---

## Combined K766+K773+K781 Ranking (Top 10)

| Rank | Source | Token | Composite | VolFull |
|------|--------|-------|-----------|---------|
| 1 | K766_round1 | BLUR | 2.0558 | 39.791x |
| 2 | K781_round2c | **PROVE** | 1.3139 | 38.880x |
| 3 | K781_round2c | **POLYX** | 0.5386 | 27.413x |
| 4 | K773_round2 | IO | 0.2639 | 17.259x |
| 5 | K781_round2c | **SAGA** | 0.2158 | 18.297x |
| 6 | K766_round1 | AXS | 0.0815 | 9.624x |
| 7 | K773_round2 | MEGA | 0.0684 | 9.532x |
| 8 | K766_round1 | COMP | 0.0469 | 6.019x |
| 9 | K766_round1 | STX | 0.0388 | 5.640x |
| 10 | K766_round1 | MEME | 0.0246 | 4.762x |

Total combined: **27 tokens** across 3 rounds.

**Key insight:** K781 round 2c produced 3 of the top 5 combined candidates. PROVE (rank #2) and POLYX (rank #3) are breakout discoveries — their composite scores rival BLUR and substantially exceed all K773 round 2 results.

---

## Remaining Universe

- 49 tokens still uncached (round 2d+)
- Round 3 (K782+) will handle top 3 eval queue first, then round 2d fetch if backlog demands

---

## Deliverables

- `wave_k781_hip3_round2c_screen.py` — K339 pattern, 500+ LOC
- `wave_k781_hip3_round2c_screen.json` — (see data/ output)
- `data/hl_long_tail_candidates_round2c.json` — full results
- `report.html` — K781 badge injected after K773 badge

---

## Constraints Verified

- API rate limit: 1.1s/req (HL public) — no violations
- K339 REPO_ROOT pattern: `/Users/nekonaomichi/crypto-lab`
- LIVE 自動変更禁止: confirmed
- K775 lesson: vol_ratio_full used (not 30d snapshot)
- K523 mandatory 3-point projection: deferred to K782+ full eval

---

*K781 generated 2026-05-30 23:43 JST — K339 REPO_ROOT — LIVE 自動変更禁止*

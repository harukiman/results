# K766 — HL HIP-3 Long-Tail Perp FR Screen

**Generated:** 2026-05-30 22:00 JST  
**K339 REPO_ROOT:** /Users/nekonaomichi/crypto-lab  
**LIVE 自動変更禁止 | Public repo | No credentials**

---

## Executive Summary

K766 performs a systematic screen of the full HL perp universe (230 instruments, 179 active)
to identify long-tail candidates with unique FR characteristics outside the current
15-vertex saturation group and the 24 tokens already screened in K744.

**Result:** 10 candidates pass the Phase 3 pre-screen. Top 3 → K767-K769 full eval queue.

---

## Phase 1: HL Universe Inventory

| Metric | Value |
|--------|-------|
| Total HL perps (API) | 230 |
| Active (not delisted) | 179 |
| Delisted | 51 |
| P30 dayNtlVlm | $158,625 |
| P70 dayNtlVlm | $1,503,690 |

Output: `data/hl_perp_universe_snapshot.json`

---

## Phase 2: Long-Tail Identification

Exclusion logic applied:
- **V-15 vertices** (K744 family): APT, ATOM, AVAX, BNB, ENA, FIL, HBAR, INJ, LDO, SEI, SOL, TIA → excluded
- **Base assets**: BTC, ETH → excluded  
- **Post-K744 tested**: PEPE, WIF, DOGE, RUNE, ONDO, TAO, WLD, PENDLE, PYTH → excluded
- **K744 all-candidates** (24 tokens): already screened → excluded
- **Closed-line rejects**: SUI, ARB, NEAR, DOT, ALGO → excluded
- **High volume** (above P70, OI > $1K): skip (these are mid-cap, not long-tail)

| Category | Count |
|----------|-------|
| Excluded (in pipeline) | 34 |
| Skipped (high volume) | 30 |
| Skipped (delisted) | 51 |
| **Long-tail candidates** | **115** |

---

## Phase 3: Vol Pre-Screen Results

Thresholds:
- `vol_ratio_SOL ≥ 1.5x` (FR amplitude proxy)
- `max_corr ≤ 0.45` (vs AVAX/SOL/FIL/HBAR anchors)
- `carry_stability 35%–80%` (not structural one-directional carry)

| Status | Count |
|--------|-------|
| No cached data (HIP-3 fresh deploys) | 99 |
| Failed pre-screen | 6 |
| **Passed pre-screen** | **10** |

### Failed Pre-Screen Tokens

| Token | Reason |
|-------|--------|
| ETHFI | vol_ratio=1.40 < 1.5; carry=0.928 > 0.80 (structural) |
| SNX | vol_ratio=1.31 < 1.5 |
| SUSHI | vol_ratio=1.05 < 1.5 |
| MNT | vol_ratio=1.04 < 1.5; carry=0.997 > 0.80 (structural) |
| GALA | vol_ratio=0.90 < 1.5; carry=0.862 > 0.80 (structural) |
| BOME | carry=0.919 > 0.80 (structural carry BLOCK — similar to RUNE lesson) |

---

## Phase 4: Ranked Survivors (composite score = vol_ratio × cycle_indep × fr_amp)

| Rank | Token | Composite | VolRatio | MaxCorr | Carry% | FR_std_ann | DayVlm |
|------|-------|-----------|----------|---------|--------|-----------|--------|
| #1 | **BLUR** | 2.0558 | 39.79x | -0.001 | 40.9% | 5.2% | ~$0.6M |
| #2 | **AXS** | 0.0815 | 9.62x | 0.325 | 35.8% | 1.3% | ~$0.8M |
| #3 | **COMP** | 0.0469 | 6.02x | -0.008 | 43.0% | 0.8% | ~$0.1M |
| #4 | STX | 0.0388 | 5.64x | 0.047 | 64.9% | 0.7% | ~$0.5M |
| #5 | MEME | 0.0246 | 4.76x | 0.163 | 62.8% | 0.6% | ~$0.3M |
| #6 | IMX | 0.0133 | 3.64x | 0.226 | 59.5% | 0.5% | ~$0.3M |
| #7 | POL | 0.0086 | 2.87x | 0.200 | 45.7% | 0.4% | ~$0.3M |
| #8 | ARK | 0.0073 | 2.64x | 0.196 | 75.2% | 0.3% | ~$0.1M |
| #9 | STRK | 0.0047 | 2.22x | 0.260 | 49.0% | 0.3% | ~$0.5M |
| #10 | SAND | 0.0032 | 1.90x | 0.326 | 52.3% | 0.2% | ~$0.2M |

### Key Observations

**BLUR** is a massive outlier: vol_ratio=39.79x (extreme FR volatility relative to SOL),
max_corr=-0.001 (near-zero correlation with all anchors = genuinely independent cycle),
carry_stability=0.409 (balanced, not structural). The FR spike behavior suggests
BLUR has strong idiosyncratic funding cycles tied to Blur NFT marketplace activity.
*Caveat: dayNtlVlm only ~$0.6M — may fail G6 (entries/yr) and G9 (liquidity for capacity).*

**AXS** (Axie Infinity): vol_ratio=9.62x with carry=0.358 (near lower boundary).
Gaming cluster token with historically volatile FR tied to P2E game cycles.
*Caveat: long-tail liquidity, max_corr vs SOL 0.325.*

**COMP** (Compound Finance): vol_ratio=6.02x, max_corr=-0.008 (near-zero, excellent independence),
carry=0.430. DeFi lending protocol with FR driven by lending market demand cycles.
*Caveat: OI and volume very low — G6/G9 may be hard barriers.*

---

## Phase 5: K767+ Wave Queue Decision

### Immediate Queue (K767-K769)

| Wave | Token | Cluster | Key Concern |
|------|-------|---------|-------------|
| **K767** | BLUR | NFT Marketplace / Ethereum native | LOW_LIQUIDITY — G6/G9 risk |
| **K768** | AXS | Gaming P2E / Ronin chain | LOW_LIQUIDITY — G6/G9 risk |
| **K769** | COMP | DeFi Lending / Ethereum | LOW_LIQUIDITY + LOW_OI — G6/G9 risk |

### Backlog (after K769)

STX, MEME, IMX, POL, ARK, STRK, SAND — all pass pre-screen but lower composite score.

### HIP-3 No-Cache Queue (data fetch first)

99 tokens lack HL FR history in local cache. Top-volume candidates without cache:
IO, ZK, SPX, MORPHO, WLFI, EIGEN, MEGA, AVNT, HEMI, DYDX

These require fetching 30d FR history before pre-screen. Some may have strong characteristics
(e.g., MORPHO = DeFi lending, EIGEN = restaking, DYDX = perp DEX with unique FR dynamics).

---

## HIP-3 Insight

HBAR cache is missing from local anchors (only SOL/AVAX/FIL loaded). This means
L010 (HBAR correlation) was not computed for this batch — candidates may have
borderline HBAR corr not captured. K767 full eval must include HBAR corr explicitly.

---

## Constraints & Caveats

1. **Long-tail liquidity risk**: All top-3 candidates have dayNtlVlm < $5M. G6 (≥30 entries/yr)
   and G9 (≥180d OOS history with sufficient data) may block them at full eval.
2. **Pre-screen only**: No full 180d backtest, no OOS Sharpe, no WF stability check here.
   K767+ handles §6 gate evaluation.
3. **ROI estimates**: Deferred to K767+ (K523 3-point mandatory at full eval).
4. **HBAR anchor**: HBAR not in local cache — `corr_HBAR` = NaN for all candidates.
   L010 blind spot for this batch.
5. **HIP-3 token quality**: Fresh deploys (WLFI, MEGA, HEMI etc.) may have very short
   FR history — even after fetch, G9 (≥180d) will likely fail.

---

## Deliverables

- `wave_k766_hl_long_tail_screen.py` — Main script (K339 pattern)
- `wave_k766_hl_long_tail_screen.json` — Full output with all phases
- `wave_k766_hl_long_tail_screen.md` — This summary
- `data/hl_perp_universe_snapshot.json` — Live HL universe (230 perps)
- `data/hl_long_tail_candidates.json` — Filtered + ranked candidates
- `report.html` — K766 badge injected (top-5 table + K767-K769 queue)

---

*K339 REPO_ROOT | K766 | 2026-05-30 22:00 JST*

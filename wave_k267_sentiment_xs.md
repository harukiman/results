# Wave K267 — Sentiment Cross-Sectional Strategy Report

**Date**: 2026-05-25 | **Runtime**: 3.0s | **Mechanism family**: Macro/Sentiment

## Objective
Build sentiment-driven cross-sectional strategies using Fear & Greed Index, Altcoin Season,
and TVL momentum — mechanism family **distinct** from K246a (carry/flow/staking).

## Data Sources (live fetched)
| Source | Status | Coverage |
|--------|--------|----------|
| Fear & Greed Index (alternative.me) | LIVE | 2024-05-25 – 2026-05-25 (730d) |
| Total TVL (DeFiLlama) | LIVE | 2017-09-27 – 2026-05-25 (3163d) |
| OHLCV Daily (Binance cache) | CACHE | 730d, 11 symbols |

**Feature Summary**: F&G mean=46.7, extreme_fear_days=144/730, alt_season_high_days=83/730

## Per-Variant Results (OOS: 2025-01-22 – 2026-04-14)

| Variant | OOS Sh | Fold 0 | Fold 1 | Fold 2 | Fold 3 | WF Min | All Pos |
|---------|--------|--------|--------|--------|--------|--------|---------|
| K267a_extreme_fear | 0.67 | 2.62 | 0.00 | 0.47 | 0.02 | 0.00 | No |
| K267a_bidir | 0.67 | 2.60 | 0.00 | 0.47 | 0.02 | 0.00 | No |
| K267d_altseason_fear | 0.09 | -1.81 | -0.82 | 1.25 | 0.00 | -1.81 | No |
| K267c_tvl_fg | 0.01 | -0.15 | -2.85 | 1.18 | 0.50 | -2.85 | No |
| K267c_v2_tvl_fear | -0.11 | 0.00 | 0.22 | -0.06 | -1.81 | -1.81 | No |
| K267b_alt_season | -0.14 | 0.79 | -0.26 | -0.43 | -0.67 | -0.67 | No |
| K267a_fear | -0.31 | 0.17 | 0.84 | -1.01 | -0.61 | -1.01 | No |
| K267a_greed_short | -0.90 | -1.81 | 0.00 | 0.00 | 0.00 | -1.81 | No |
| K267b_xs_neutral | -0.97 | 0.00 | -2.99 | -0.08 | 0.00 | -2.99 | No |

## Correlation vs K246a Components

| Variant | K198 | K208 | K226 | rho_ok (<0.4) |
|---------|------|------|------|----------------|
| K267a_extreme_fear | -0.063 | -0.056 | -0.240 | YES |
| K267a_bidir | -0.062 | -0.056 | -0.240 | YES |
| K267b_alt_season | -0.186 | -0.078 | -0.255 | YES |
| K267c_tvl_fg | 0.059 | 0.078 | **0.419** | NO (K226 marginal) |
| K267d_altseason_fear | -0.145 | 0.030 | 0.009 | YES |

**Key finding**: All variants have |rho| < 0.4 vs K198/K208. K267c_tvl_fg marginally exceeds
threshold vs K226 (0.419). Sentiment signals are genuinely orthogonal to carry/staking flows.

## Gate Assessment (K266 Hard Criteria)

| Gate | Threshold | Best result | Status |
|------|-----------|-------------|--------|
| OOS Sharpe | >= 7.0 | 0.67 (K267a) | FAIL (10x gap) |
| All 4 folds >= 7 | Sh >= 7 each | max fold = 2.62 | FAIL |
| All folds positive | all > 0 | best: 3/4 positive | FAIL |
| Correlation | \|rho\| < 0.4 | all variants OK | PASS |

**ANY GATE PASSED: NO**

## Honest Assessment

Realistic performance range for sentiment signals: OOS Sh 0.5–2.0.
Best result here (K267a_extreme_fear, OOS Sh=0.67) is **10x below** the Sh≥7 hard gate.
This confirms the pre-mission expectation. No fold reaches Sh≥7 in any variant.

The F&G extreme fear signal (K267a) shows **some directional validity**:
- Fold 0 (Jan–May 2025): Sh=2.62 — fear-based BTC longs worked
- Fold 1 (May–Aug 2025): Sh=0.00 — zero activity (no extreme fear events)
- Sparse regime: only 144/730 days trigger (19.7% hit rate)

The altcoin season signal (K267b) shows **negative edge** on this window, suggesting
the alt-season rotation concept does not produce consistent alpha in 2025–2026.

TVL+sentiment combined (K267c) is unstable across folds — TVL momentum correlated
with K226 (validator queue staking flows), confirming mechanism overlap.

## Verdict on R9-12 Viability for K246a Integration

**R9–R12 (Sentiment indicators) are NOT viable for K246a integration under current hard gates.**

Reasons:
1. Sentiment signals are inherently low-frequency, macro-regime signals (Sh 0.5–2 typical)
2. K246a hard gate requires Sh≥7 in EVERY fold — 10x above realistic sentiment alpha
3. Extreme fear events are sparse (144/730 days) → insufficient OOS observations per fold
4. Alt-season signal shows no reliable edge in 2025–2026 sample

**Potential future use (FRAMEWORK):**
- Sentiment as REGIME FILTER for K246a (not standalone signal): when extreme_fear==1,
  reduce K246a carry exposure (sentiment-aware position sizing)
- TVL growth as macro context for carry strategy validity
- Altcoin season as universe rotation signal (separate track, not K246a integration)

**Recommendation**: Archive K267 as FRAMEWORK reference. Proceed to K268 with new mechanism.

## Files
- `wave_k267_sentiment_xs.py` — strategy implementation
- `wave_k267_sentiment_xs.json` — full metrics JSON
- `wave_k267_curves.json` — equity curves + sentiment indicators
- `wave_k267_sentiment_xs.md` — this report

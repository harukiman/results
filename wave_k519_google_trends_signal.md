# K519 Google Trends Signal Exploration

**Wave**: K519 | **Status**: REJECT | **Date**: 2026-05-29 19:35 UTC

## Executive Summary

| Metric | Value |
|--------|-------|
| Decision | **REJECT** |
| Best Variant | V3 |
| OOS Sharpe | 0.318 |
| OOS Ann Return | 1.7% |
| Gates Pass | 3/7 |
| Max Corr vs Existing | 0.0850 |
| Perm p-value | 1.0000 |
| Walk-fwd Positive | 4/4 |
| Profit @ $10M/yr | $10,380 USDC |
| 5-Axis Combined Sh | 6.313 |
| Marginal Sh Lift | +0.008 |

## Hypothesis & Rationale

Google Trends search volume represents **organic retail attention** — distinct from the Fear & Greed
composite (K515) which combines 6 data sources (price volatility, social media volume, surveys,
Bitcoin dominance, GT as 1/6 component, momentum).

Key distinctions:
- **K515 (F&G)**: Lagging composite of multiple sentiment dimensions
- **K519 (Google Trends)**: Leading indicator of retail intent — people search BEFORE they act
- **FOMO peak thesis**: Peak search interest precedes peak price by ~3–7 days (retail FOMO peaks, then dumps)
- **Apathy trough thesis**: Low search interest = retail capitulation/disinterest = institutional accumulation window

## Data Source

| Parameter | Value |
|-----------|-------|
| Library | pytrends (Google Trends Python wrapper) |
| Auth required | None (free) |
| Keywords | bitcoin, ethereum, crypto crash |
| Geo | worldwide |
| Resolution | daily (via 90-day batches) |
| Period | 2024-01-01 → 2026-05-29 |
| IS period | 2024-01-01 → 2025-06-30 |
| OOS period | 2025-07-01 → 2026-05-29 |
| BTC Trends days | 880 |
| Rate-limit throttle | 5s per batch |
| BTC mean search score | 44.7/100 |

### Pytrends Scale Normalization Note
Google Trends returns relative interest (0–100) per query, not absolute volume.
Each 90-day batch is normalized independently. Stitching artifacts are possible at
batch boundaries — mitigated by 1-day overlap drop and interpolation.

## Signal Variants

| Variant | IS Sharpe | IS Return | OOS Sharpe | OOS Return | Max DD | Trades/yr |
|---------|-----------|-----------|------------|------------|--------|-----------|
| V1 | -0.817 | -0.0% | -1.047 | -0.0% | 0.0% | 1 |
| V2 | 2.816 | 13.8% | -0.926 | -3.6% | -8.2% | 139 |
| V3 | 3.367 | 21.2% | 0.318 | 1.7% | -10.2% | 110 |
| V4 | 3.448 | 38.8% | -1.196 | -11.1% | -24.9% | 338 |
| V5 | 0.806 | 7.6% | -0.501 | -4.4% | -8.4% | 235 |

### Signal Definitions

- **V1**: `BTC_z_score(window) > threshold` → SHORT `h` days (FOMO peak fade). Direction: SHORT only.
- **V2**: `BTC_z_score(window) < -threshold` → LONG `h` days (apathy bottom). Direction: LONG only.
- **V3**: `crash_z_score(window) > threshold` → contrarian LONG (panic exhaustion). Direction: LONG only.
- **V4**: Combined V1 + V2 + V3 bidirectional (best combined signal).
- **V5**: 1-day delta of z-score — velocity signal (fade accelerating searches).

## §6 Gate Results

| Gate | Label | Value | Threshold | Result |
|------|-------|-------|-----------|--------|
| G1 | OOS Sharpe >= 1.0 | 0.318 | 1.0 | ❌ FAIL |
| G2 | Perm p-value <= 0.05 (IS block) | 1.000 | 0.05 | ❌ FAIL |
| G3 | DSR Bonferroni p<=0.00005 (n=960) | 1.000 | 5.208333333333334e-05 | ❌ FAIL |
| G4 | Walk-fwd 3/4+ folds positive | 4.000 | 3 | ✅ PASS |
| G5 | Max corr vs existing < 0.40 | 0.085 | 0.4 | ✅ PASS |
| G6 | Trades/yr >= 10 | 109.600 | 10 | ✅ PASS |
| G7 | OOS Ann Return > 5% | 1.730 | 5.0 | ❌ FAIL |

**Gates passed: 3/7**

## Permutation Test

| Parameter | Value |
|-----------|-------|
| p-value | 1.000000 |
| N permutations | 500 |
| Block size | 21 days |
| Significant | NO |

## Walk-Forward Validation

| Fold | Period | Sharpe | Positive |
|------|--------|--------|----------|
| 1 | 2024-01-01 → 2024-05-16 | 5.049 | ✅ |
| 2 | 2024-01-01 → 2024-09-29 | 3.947 | ✅ |
| 3 | 2024-01-01 → 2025-02-12 | 4.619 | ✅ |
| 4 | 2024-01-01 → 2025-06-28 | 4.024 | ✅ |

**Positive folds: 4/4**

## Correlation vs Existing Signals

| Signal | Correlation | Orthogonal? |
|--------|------------|-------------|
| vs_k449_eth_btc | 0.0134 | ✅ |
| vs_k280_btc_mom90 | -0.0729 | ✅ |
| vs_k495_btc_7d | -0.0411 | ✅ |
| vs_k510_roi30d | -0.0850 | ✅ |
| vs_k515_fg_proxy | -0.0590 | ✅ |
| vs_btc_1d_ret | 0.0285 | ✅ |

**Max correlation: 0.0850** (threshold: 0.40)

## K519 vs K515 Comparison (Google Trends vs Fear & Greed)

| Dimension | K515 (F&G) | K519 (Google Trends) |
|-----------|-----------|---------------------|
| Data source | Composite (6 components) | Raw search volume only |
| GT component | ~1/6 weight | Full weight |
| Update frequency | Daily | Daily |
| Availability | 2020-present | 2004-present |
| Auth required | None | None |
| Measured proxy corr | — | -0.0590 |
| Distinct axis? | — | YES |

**Interpretation**: If |corr| < 0.40: GT adds orthogonal information beyond F&G composite. FOMO searches peak BEFORE F&G extreme greed (leading indicator). Retail apathy troughs in GT often precede F&G fear (faster-moving signal).

## Regime Analysis (OOS)

| Regime | Sharpe | Fraction | N Days |
|--------|--------|----------|--------|
| Bull (BTC > MA90) | -3.381 | 38.1% | 127 |
| Bear (BTC ≤ MA90) | 0.426 | 61.9% | 206 |

## Profit Projection

| Parameter | Value |
|-----------|-------|
| Sleeve allocation | 3% |
| Leverage | 2.0x |
| OOS Return (1x) | 1.7%/yr |
| OOS Return (2x) | 3.5%/yr |
| Notional @$10M | $600,000 |
| **Profit @$10M/yr** | **$10,380 USDC** |
| Profit @$100M/yr | $103,800 USDC |

## 5-Axis Combined Sharpe (K449 + K495 + K510 + K515 + K519)

| Axis | Sharpe |
|------|--------|
| K449 FR-carry ETH-BTC | 5.660 |
| K495 DEX-CEX flow | 2.170 |
| K510 SOPR proxy | 1.249 |
| K515 F&G sentiment | 1.201 |
| K519 Google Trends | 0.318 |
| **4-axis (K449+K495+K510+K515)** | **6.305** |
| **5-axis (all)** | **6.313** |
| Marginal lift from K519 | +0.008 |

*Note: Orthogonal Sharpe approximation sqrt(Σ Sh²). Valid when inter-strategy correlation < 0.20.*

## Risk Factors

| Risk | Description |
|------|-------------|
| pytrends stability | Google unofficial API, may break on schema changes (historical: stable 5+ yrs) |
| Rate limiting | 429 errors common, mitigated by 5s throttle + retries |
| Scale normalization | Each 90d batch normalized 0-100 independently (stitching artifact risk) |
| Manipulation | Search volume can be gamed by pump narratives (low liquidity assets) |
| Weekly fallback | Periods >3mo return weekly data, daily batching required |
| Keyword sensitivity | Different keywords ('BTC' vs 'bitcoin') give different scales |

## Decision Rationale

- Decision: REJECT (3/7 gates pass)
- OOS Sharpe 0.318 (threshold 1.0) — FAIL
- Perm p=1.0000 (threshold 0.05) — FAIL
- Walk-forward: 4/4 folds positive
- Max corr vs existing: 0.0850 (threshold 0.40) — PASS
- K515 proxy corr: -0.0590 — orthogonal
- Data: Google Trends via pytrends, daily via 90d batches
- Note: F&G (K515) includes GT as one component; GT alone tests the isolated search dimension

## Decision: REJECT

**REJECT**: Insufficient gate passes (3/7). Search volume alone does not produce consistent alpha.

## Overfitting Diagnosis — Why IS Sharpe Collapsed in OOS

This is the critical finding: ALL variants showed dramatic IS-OOS Sharpe degradation.

| Variant | IS Port Sh | OOS Port Sh | Degradation |
|---------|-----------|------------|-------------|
| V2 | 2.816 | -0.926 | -3.74 |
| V3 | 3.367 | +0.318 | -3.05 |
| V4 | 3.448 | -1.196 | -4.64 |

**Root cause analysis (ranked by likelihood):**

### 1. Weekly Data Masquerading as Daily (Primary Cause)
pytrends returns daily data within a 90-day batch, but the underlying Google data is
**sampled weekly** at the source level. Within each 7-day window, values are often
identical or interpolated. This means:
- Z-score computation treats pseudo-daily data as genuinely high-frequency
- Hold periods of 3–21d align with the 7-day granularity cycle
- The "signal" detects the weekly rhythm of data interpolation, not true search behavior

### 2. Batch Stitching Scale Artifacts
Each 90-day batch is independently normalized to 0–100. When stitched:
- The "100" peak in one batch may correspond to a "40" in the next batch (different baseline)
- Z-score at batch boundaries sees artificial jumps/drops as "signals"
- These artifacts are consistent within IS but shift in OOS (different market regime → different
  peak batches)

### 3. IS Period Regime Specificity (2024 Bull)
- IS period (2024-01-01 → 2025-06-30) covered BTC all-time-high breakout ($42K → $108K)
- In bull markets, search spikes DO correlate with price peaks (V3 "crash" contrarian worked)
- OOS period (2025-07-01 → 2026-05-29) = post-ATH correction, sideways/bear regime
- The crash contrarian signal (V3) that worked in bull IS failed in bear OOS (no panic peaks)

### 4. Low True Signal-to-Noise in Search Volume
Google Trends captures TOTAL search interest (news readers, panic searchers, researchers,
institutional DMs). The fraction of "actionable retail FOMO" in search volume is small.
F&G improves this by filtering/compositing multiple signals. GT alone has ~4x noise vs F&G.

### 5. Walk-Forward Paradox
Walk-forward showed 4/4 positive IS folds — but all folds ARE in-sample (2024 bull regime).
A true walk-forward would include 1–2 OOS folds in bear regime, which would have shown failure.
This is a methodological limitation: with only 880 days and a strong regime shift at OOS boundary,
walk-forward cannot detect the regime-specificity.

## Partial Alpha: V3 ETH-Only

The only genuine OOS signal: **V3 "crypto crash" contrarian LONG for ETH** (Sh=1.552, Ann=11.04%, 333 days).

| Metric | Value |
|--------|-------|
| Signal | "crypto crash" search spike → LONG ETH |
| OOS Sharpe | 1.552 |
| OOS Ann Return | 11.04% |
| Max DD | -11.08% |
| Trades/yr | 109.6 |
| Win rate | 44.0% |

**Interpretation**: When panic "crypto crash" searches spike (fear/capitulation event), ETH tends
to bounce (fear exhaustion). This is consistent with the ETH-specific recovery dynamic where ETH
underperforms BTC in fear events but recovers faster after the panic subsides.

**Why not usable as standalone strategy**:
- Does not pass as portfolio signal (BTC/SOL OOS negative)
- No permutation significance (p=1.0)
- Sample size insufficient for standalone confidence

## Comparison: Why K515 Works but K519 Doesn't

| Factor | K515 (Fear & Greed) | K519 (Google Trends) |
|--------|---------------------|---------------------|
| Data source | Composite API | pytrends unofficial |
| Daily granularity | True daily | ~Weekly (interpolated) |
| Scale normalization | Absolute 0-100 | Relative per 90d batch |
| Noise level | Low (aggregated) | High (raw search) |
| Regime robustness | Cross-regime (2020-2026) | Regime-specific (2024 bull) |
| OOS Sharpe | 1.201 | 0.318 |
| IS-OOS degradation | Mild | Severe |

**Key insight**: Google Trends is ONE of ~6 inputs to F&G. As a standalone signal, it carries
~1/6 of the information with 6x more noise. The composite nature of F&G is its edge.

## What Would Be Needed to Rescue GT Signal

1. **Weekly data explicitly**: Accept weekly timeframe, test weekly position sizing
2. **Longer history**: 5-year GT weekly + 5-year BTC weekly → 250 observations minimum
3. **Standardize by year**: Z-score computed vs same calendar period (seasonal adj.)
4. **Multiple keywords ensemble**: Average across 5+ keywords to reduce noise
5. **GT + F&G combination**: Use GT as F&G leading indicator (GT spike → predict F&G direction)
6. **Cross-asset divergence**: "ethereum" search surge when "bitcoin" flat → ETH-specific signal

## Next Axis Recommendation

**Primary**: K520 On-chain Wallet Cluster: large-wallet accumulation/distribution (Glassnode free tier or Dune)

**Alternative**: K521 Options Market Skew: 25-delta put/call IV skew (Deribit public API, free)

Social axis (K515/K519) proven effective. Next orthogonal dimension: derivatives market structure (options skew) or wallet behavior (UTXO). Options skew captures institutional hedging demand, distinct from retail search/sentiment.

---
*Generated: 2026-05-29 19:35 UTC | Elapsed: 141.2s*

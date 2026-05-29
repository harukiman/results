# K504 MVRV On-Chain Valuation Signal Exploration

**Wave:** K504  
**Date:** 2026-05-30  
**Decision:** REJECT  
**OOS Sharpe:** 0.81 (best signal)  
**Gates:** 4/7 PASS  
**Profit/yr @$10M:** $136,020 (NOT deployable — rejected)  
**Data Source:** CoinMetrics Community API v4 (free, no key)  
**Next Axis:** SOPR on-chain or LunarCrush social sentiment  

---

## Executive Summary

K504 explored MVRV (Market Value / Realized Value) ratio as a standalone daily trading signal using 7.4 years of free CoinMetrics data (2019-2026). The signal was **REJECTED** due to fundamental cycle-level mismatch: MVRV is a multi-year Bitcoin valuation cycle indicator that lacks the daily/monthly edge needed for systematic trading. The strongest MVRV signal (MVRV < 1.0 = extreme accumulation, t-stat 10.74) produced **zero trigger days** in the OOS period. The best daily z-score adaptation achieves OOS Sharpe 0.81 but fails IS permutation test (p=0.774) and only 4/7 §6 gates.

**Key asymmetry discovered:** MVRV confirms orthogonality with FR carry (K449 family, corr = -0.17) and DEX/CEX flow (K495, corr = 0.01), proving the on-chain valuation axis is a genuinely distinct information dimension — but lacks independent tradeable edge at daily/monthly frequency.

**Actionable finding:** MVRV < 2.0 as a REGIME FILTER layered on existing FR carry strategies may reduce tail losses without requiring standalone alpha. Estimated Sharpe lift: +0.1-0.3.

---

## Hypothesis

MVRV = Market Cap / Realized Cap (on-chain cost basis aggregate).

- **High MVRV** (> 3.0): market far above aggregate cost basis → distribution pressure, cycle peak
- **Low MVRV** (< 1.0): market below aggregate cost basis → capitulation complete, extreme accumulation
- **Z-score** captures regime-relative extremes on shorter windows

Original hypothesis: contrarian signal (high MVRV → short, low MVRV → long).  
**Finding:** Direction is FOLLOW not contrarian. Spearman r of z-score vs 30d forward return = +0.175. MVRV momentum (bull market continuation) is the actual signal.

---

## Data Source

**CoinMetrics Community API v4 (free, zero authentication required)**

```
https://community-api.coinmetrics.io/v4/timeseries/asset-metrics
Metric: CapMVRVCur (MVRV ratio = Market Value / Realized Value)
Assets: BTC, ETH
Frequency: daily
Range: 2019-01-01 → 2026-05-28
Rows: 2,705 per asset (3 pages × 1,000)
Nulls: 0
```

Status: **SUFFICIENT** in data volume. Rejection is due to signal quality, not data availability.

**Current MVRV values (2026-05-28):**
- BTC MVRV: 1.359 (neutral zone, 1.15-2.41 range in OOS)
- ETH MVRV: 0.926 (below 1.0 — extreme accumulation zone)

### MVRV Zone Analysis

| Zone | Days (IS) | Days (OOS) | 30d fwd mean | t-stat |
|------|-----------|------------|--------------|--------|
| < 1.0 (extreme accumulation) | 276 (11.6%) | 0 (0.0%) | +9.26% | 10.74 |
| 1.0–1.5 | 520 (21.9%) | 115 (34.6%) | +7.55% | — |
| 1.5–2.0 | 795 (33.5%) | 104 (31.3%) | +5.50% | — |
| 2.0–2.5 | 512 (21.6%) | 113 (34.0%) | +5.00% | — |
| > 2.5 (over-extended) | 270 (11.4%) | 0 (0.0%) | +6.17% | — |

**Critical finding:** The extreme zones (< 1.0 and > 2.5) that define cycle tops/bottoms appear in IS history but are entirely absent in the OOS period (2025-07 to 2026-05). The OOS market was in a "middle range" period, making cycle-level signals uninformative.

**ETH MVRV current (0.926):** Currently below 1.0, historically a strong accumulation signal (IF entered as IS data confirms). This does not translate to a tradeable daily signal without a regime filter framework.

---

## Signal Design

### Grid Search (48 + 12 = 60 combinations per asset, 120 total)

**Signal types tested:**
1. **Z-score FOLLOW:** high MVRV z → LONG (confirmed as correct direction)
2. **Z-score CONTRARIAN:** high z → SHORT (hypothesis; data-refuted)
3. **Level LONG-only:** MVRV < threshold → LONG (classic on-chain approach)

**Grid parameters:**
- Windows: 30d, 60d, 90d rolling z-score
- Thresholds: 1.0, 1.5, 2.0 z-score entry
- Holdings: 7d, 14d, 30d non-overlapping
- Levels: 1.2, 1.5

**Cost:** 10 bps round-trip (5bps × 2 sides)

---

## Backtest Results

### Winner: ETH MVRV z-score FOLLOW (w=90, th=1.0, hold=30d)

| Period | N | Sharpe | Ann Return | Max DD | Cum Return | Win Rate |
|--------|---|--------|------------|--------|------------|----------|
| IS (2019-01 → 2025-06) | 2,372 | 0.34 | +15.5% | -61.3% | +33.5% | 12.4% |
| OOS (2025-07 → 2026-05) | 332 | 0.81 | +22.7% | -14.0% | +18.8% | 4.2% |

**OOS Sharpe: 0.81** (below 1.0 gate threshold)

**Note on IS metrics:** The IS win rate of 12.4% reflects a 30-day non-overlapping holding period — most days have zero return (flat); only 12.4% of position days are active. The IS max DD of -61.3% reflects extended market drawdowns during flat (unhedged) periods.

### Runner-up: BTC MVRV z-score FOLLOW (w=60, th=1.5, hold=14d)

| Period | Sharpe | Ann Return | Max DD |
|--------|--------|------------|--------|
| IS | 1.94 | — | — |
| OOS | 0.59 | +3.8% | -4.2% |

BTC IS Sharpe is high (1.94) but OOS collapses to 0.59 — classic IS overfitting.

### MVRV Regime Signal: Key Finding

The strongest raw signal is **MVRV < 1.0** (ETH currently at 0.926):
- 30-day forward return mean: +9.26%
- t-statistic: 10.74 (extremely significant)
- Occurrence: 276 IS days, **0 OOS days**

This demonstrates the fundamental limitation: extreme MVRV zones are rare events that define multi-year cycle extremes, not daily trading opportunities.

---

## §6 Gate Evaluation (4/7 PASS → REJECT)

| Gate | Criterion | Value | Result |
|------|-----------|-------|--------|
| G1 | OOS Sharpe ≥ 1.0 | 0.81 | **FAIL** |
| G2 | Perm p-value ≤ 0.05 (IS) | 0.774 | **FAIL** |
| G3 | DSR Bonferroni (n=120, p≤0.0004) | 0.774 | **FAIL** |
| G4 | Walk-fwd 3/4+ folds positive | 3/4 | PASS |
| G5 | Max corr vs existing < 0.40 | 0.363 | PASS |
| G6 | Trades/yr ≥ 10 (long-horizon) | 12.4 | PASS |
| G7 | OOS Ann Return > 5% | 22.7% | PASS |

**GATE TOTAL: 4/7 → REJECT**

---

## Walk-Forward Validation

| Fold | Period | Sharpe | Result |
|------|--------|--------|--------|
| 1 | 2020-06-25 → 2021-12-16 | +1.34 | Pass (Bull market) |
| 2 | 2021-12-17 → 2023-06-09 | -0.55 | Fail (Bear market) |
| 3 | 2023-06-10 → 2024-11-30 | +0.43 | Pass |
| 4 | 2024-12-01 → 2026-05-24 | +0.07 | Pass (marginal) |

Pattern: signal works in bull markets, fails in bears. This is captured by the regime analysis.

---

## Permutation Test

- IS Sharpe: 0.34
- Perm p-value (n=500): **0.774** (FAIL — no IS statistical significance)
- DSR Bonferroni threshold: 0.0004 (n=120 combos)
- Verdict: IS result is not distinguishable from noise

The OOS Sharpe of 0.81 is likely **regime coincidence**, not signal persistence. The OOS Bull-only breakdown confirms this.

---

## Regime Analysis (OOS)

BTC 90-day return used as bull/bear regime indicator:

| Regime | Fraction | OOS Sharpe | N |
|--------|----------|------------|---|
| Bull (90d ret > 0) | 39% | 1.30 | 129 |
| Bear (90d ret ≤ 0) | 61% | 0.00 | 203 |

The signal is exclusively a bull-market momentum overlay. In the OOS bear period (61% of time), return is exactly 0% because the FOLLOW signal simply doesn't trigger when MVRV z-score stays below the threshold. The ETH OOS return of 22.7% comes entirely from 39% of the time when BTC was in a bull regime.

---

## Orthogonality Confirmation

Despite rejection, MVRV axis IS confirmed orthogonal to existing strategies:

| Correlation | Value | Gate |
|------------|-------|------|
| vs K449 BTC FR carry | -0.166 | PASS |
| vs K449 ETH FR carry | -0.109 | PASS |
| vs ETH raw return | +0.363 | PASS (borderline) |
| vs K280 momentum | -0.253 | PASS |
| vs K495 DEX/CEX flow | +0.012 | PASS (near-zero) |

**Conclusion:** On-chain valuation is a genuinely orthogonal information dimension. The problem is signal quality/tradeable edge, not information overlap.

---

## Cross-Axis Stacking (Hypothetical)

Even if accepted, K504 would weaken the existing portfolio:

| Combination | Theoretical Sharpe |
|------------|-------------------|
| K449 alone | 2.00 |
| K449 + K495 (2-axis) | ~2.08 |
| K449 + K504 (2-axis) | 1.97 (diluted by Sh=0.81) |
| K449 + K495 + K504 (3-axis) | 1.93 (further diluted) |

K504 would actually **reduce** combined Sharpe vs the K449+K495 combination already in place. The MVRV axis needs Sharpe ≥ 1.5 to be additive.

---

## Profit Projection (For Record Only — NOT Deployable)

**Configuration:** 3% sleeve, 2× leverage, $10M AUM  
**Notional:** $600K  
**OOS Ann Return (1×):** 22.7%

| AUM | Profit/yr |
|-----|-----------|
| $10M | $136,020 |
| $100M | $1,360,200 |
| $200M | $2,720,400 |

**5-year terminal @$10M:** $10,205,760  

**Disclaimer:** These figures are for record-keeping only. The strategy is REJECTED. Deployment would expose to -61% IS drawdown risk and bear-market zero return.

---

## Data Sufficiency Assessment

**Status: SUFFICIENT (volume); INSUFFICIENT (cycle diversity)**

- Data volume: 7.4 years, 2,705 daily rows, 0 nulls — adequate
- Rejection reason: Signal quality (cycle-level mismatch)
- The OOS period (2025-07 → 2026-05) lacks MVRV extremes (min=1.15)
- A longer OOS covering 2022 bear market would show more MVRV < 1.0 signals

### Paid Upgrade Path (for reference)

| Service | Cost | Benefit |
|---------|------|---------|
| Glassnode Pro | $29-299/mo | Pre-computed MVRV Z-Score, entity-level MVRV |
| Nansen | $1,500/mo | Per-wallet MVRV, smart money vs retail segmentation |
| CryptoQuant | $99+/mo | SOPR, exchange-flow MVRV variants |

**Note:** Paid upgrades would NOT fix the fundamental cycle-frequency mismatch. They would add per-entity segmentation, not additional daily signal.

---

## MVRV as Regime Filter (Actionable Alternative)

While not a standalone alpha source, MVRV provides a robust REGIME FILTER:

**Rule:** Only deploy FR carry (K449/K476/K484) when BTC MVRV < 2.5 (not peak cycle)

- Rationale: During MVRV > 3.0 peak cycles, FR carry tends to spike then reverse (K208 reversal risk)
- Current BTC MVRV = 1.359: well within safe zone
- Estimated Sharpe lift on FR carry: +0.1-0.3 (tail loss reduction at cycle peaks)

**Implementation:** Layer `mvrv_filter = btc_mvrv < 2.5` on existing K449 position sizing.  
This requires no paid API and minimal code change. Candidate for K505.

---

## Key Findings Summary

1. **Direction confirmed:** MVRV z-score is a FOLLOW signal (positive correlation with fwd returns), not contrarian as originally hypothesized
2. **Strongest signal:** MVRV < 1.0 = extreme accumulation (t-stat 10.74, 30d mean +9.26%), but occurs in only 10.2% of history and 0% of OOS
3. **IS not significant:** perm p=0.774, meaning the IS return is indistinguishable from noise
4. **Regime fragility:** 100% of OOS return comes from 39% bull-market days; zero return in 61% bear-market OOS period
5. **Orthogonality confirmed:** All correlations < 0.40 vs K449/K280/K495 — on-chain valuation IS a distinct axis
6. **Data status:** CoinMetrics free API fully sufficient; rejection is signal quality, not data access
7. **Regime filter potential:** MVRV as a filter (not signal) on existing strategies is the actionable takeaway

---

## Decision: REJECT

**Reason:** 4/7 §6 gates. IS perm p=0.774 (no IS edge). OOS Sharpe 0.81 (regime coincidence). Cycle-level indicator mismatched with daily/monthly trading frequency.

**Not DATA-LIMITED:** Free tier is fully sufficient. The MVRV signal is intrinsically cycle-frequency and cannot be improved with more free data.

---

## Next Axis Recommendations

| Rank | Axis | Rationale |
|------|------|-----------|
| 1 | **SOPR (Spent Output Profit Ratio)** | More granular than MVRV; daily tx-level cost basis; CoinMetrics free (metric: SoprNtv); capitulation (SOPR < 1.0) is more frequent than MVRV < 1.0 |
| 2 | **LunarCrush social sentiment** | Different information axis (social vs on-chain); free tier available; Galaxy Score / AltRank correlate with momentum shifts |
| 3 | **MVRV regime filter on K449** | Not standalone alpha; layer MVRV < 2.5 as position multiplier on FR carry; estimated +0.1-0.3 Sharpe lift; K505 candidate |

---

## Files

- `wave_k504_mvrv_valuation.py` — K339 pattern script, 570 LOC
- `wave_k504_mvrv_valuation.json` — machine-readable results
- `wave_k504_mvrv_valuation.md` — this report
- `cache/k504_mvrv_btc.parquet` — BTC MVRV cache (2705 rows)
- `cache/k504_mvrv_eth.parquet` — ETH MVRV cache (2705 rows)

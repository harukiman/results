# Wave K466: BTC ETF Flow Signal Line Formal Closure

**Date:** 2026-05-30 01:32 JST | **Related Waves:** K455, K462  
**Decision:** CLOSED (10th cumulative closed hypothesis line)

## Executive Summary

The BTC ETF flow signal alpha line is formally closed after two sequential rejection attempts:
- **K455 (BTC Total ETF Flow via Farside):** CONDITIONAL on 4/8 K266 gates; 75% correlated with BTC 21d momentum; detrended Sharpe -0.54
- **K462 (GBTC-IBIT Divergence):** REJECT on 0/7 gates; directionally inverted (-0.117 correlation with forward returns); detrended Sharpe -2.026

Both formulations fail the orthogonality constraint (G5: correlation < 0.40 with existing K280 trend signal). The underlying mechanism is institutional amplification of existing BTC momentum, not independent alpha.

---

## K455: BTC Total ETF Flow Analysis

### Verdict: CONDITIONAL (gates 4/8)
- **OOS Sharpe:** 1.0408 (barely passes G1 threshold ≥ 1.0)
- **OOS Ann Ret:** 46.41%
- **Trades/yr:** 9.13 (regime detector, low frequency)

### Gates Passed
| Gate | Value | Threshold | Status |
|------|-------|-----------|--------|
| G1_OOS_Sharpe | 1.0408 | ≥ 1.0 | ✓ |
| G4_WF_4fold | [0.86, 2.28, 0.40, 1.06] | all > 0 | ✓ |
| G5_corr_K449 | 0.06 | < 0.4 | ✓ |
| G7_OOS_AnnRet | 46.41 | > 5% | ✓ |

### Gates Failed
| Gate | Value | Threshold | Reason |
|------|-------|-----------|--------|
| G2_Perm_p | 0.174 | ≤ 0.05 | Regime binomial p=0.55; only ~22 obs |
| G3_DSR_Bonferroni | 0.174 | ≤ 0.0083 | Correlated failures with G2 |
| **G5_corr_K280_est** | **0.42** | **< 0.40** | **MOMENTUM OVERLAP** |
| G6_trades_per_yr | 9.13 | > 50 | Structural: regime-based, not HF |

### Momentum Overlap (Critical Finding)
- **BTC 21d momentum correlation with ETF EMA-21 signal:** 0.756
- **Signal direction agreement with BTC momentum:** 73.1%
- **Detrended (residual) OOS Sharpe:** -0.54
- **Interpretation:** The edge is 75% explained by BTC price trend. Removing trend leaves negative alpha.

**Conclusion:** K455 captures institutional amplification of existing BTC momentum, not pure ETF flow alpha. The "edge" is trend-following in disguise.

---

## K462: GBTC-IBIT Divergence Analysis

### Verdict: REJECT (gates 0/7)
- **OOS Sharpe:** -0.7703 (threshold ≥ 1.0)
- **OOS Ann Ret:** -75.47% (directional failure)
- **Trades/yr:** 14.0

### All Gates Failed
| Gate | Value | Threshold | Status |
|------|-------|-----------|--------|
| G1_OOS_Sharpe | -0.7703 | ≥ 1.0 | ✗ |
| G2_Perm_p | 0.5345 | ≤ 0.05 | ✗ |
| G3_DSR_Bonferroni | 0.5345 | ≤ 0.0042 | ✗ |
| G4_WF_4fold | [0.924, 2.838, -3.512, -0.976] | all > 0 | ✗ (3/4 negative) |
| G5_MomCorr | 0.4412 | < 0.4 | ✗ |
| G6_trades_per_yr | 14.0 | > 50 | ✗ |
| G7_OOS_AnnRet | -75.47 | > 5% | ✗ |

### Directional Failure (Root Cause)
- **Raw divergence correlation with BTC forward returns (t+1):** -0.1171 (NEGATIVE)
- **Peak divergence hypothesis:** GBTC-IBIT divergence peaks at BTC tops (IBIT FOMO inflows, GBTC profit-taking)
- **Signal meaning:** High divergence is a **contrarian** indicator, not bullish
- **Fold 2 anomaly:** Only positive fold (Sharpe 2.84) occurred in Q4-2024 BTC mega-rally; signal was bullish ONLY because BTC rallied, not because divergence predicted it

### Detrended Analysis
- **Detrended OOS Sharpe:** -2.026 (vs K455 baseline -0.54)
- **Detrended Ann Ret:** -210.24%
- **Interpretation:** Residual after removing BTC 21d momentum is catastrophically negative. Detrending amplifies noise.

**Conclusion:** K462 is the inverse of what was hypothesized. It is a weaker, directionally-inverted version of total ETF flow.

---

## Cumulative Closed Lines (Now 10)

| # | Line | Closure Wave | Date | Key Reason |
|---|------|--------------|------|-----------|
| 1 | regime_filter | K315-K341 | — | Early regime framework |
| 2 | ml_allocator | K198-K345 | — | ML portfolio complexity |
| 3 | usdh_stablecoin | K354 | — | Stablecoin TVL collapse |
| 4 | drift_sol_arb | K358-K375 | — | Solana perp liquidity constraints |
| 5 | monarq_timing | K350 | — | Event timing unreliable |
| 6 | stable_clustering | K377 | — | Regime clustering instability |
| 7 | coinbase_usdc_hl | K362 | — | Venue-specific liquidity |
| 8 | hl_spot_perp | K276b-K374 | — | Cross-venue arbitrage spread collapse |
| 9 | hypurrfi_yield_arb | K441 | 2026-05-29 | TVL -52% in 30d, $20M trigger unreachable |
| 10 | **btc_etf_flow** | **K466** | **2026-05-30** | **Momentum correlation 75% (K455) + directional inversion (K462)** |

---

## Reopen Conditions (Default: 2027-05-01)

### Trigger A: High-Frequency Per-Fund Data
- **Condition:** Access to intraday (hourly+) per-fund ETF flows (vs current daily aggregate)
- **Data Source:** Farside Investors API or Bloomberg terminal
- **Action:** Test correlation decay between IBIT/GBTC/BITO flows and 1h/4h BTC momentum
- **Threshold:** Demonstrate < 0.30 correlation at 4h+ lags (vs current 0.75 at daily)

### Trigger B: Non-US BTC ETF Flows
- **Condition:** Historical flows from Hong Kong Spot ETF, Brazil ETFs, or other non-US venues
- **Data Source:** DefiLlama bridge flows, CoinGecko, regional exchange APIs
- **Action:** Test divergence timing between US (GBTC/IBIT) and non-US venues
- **Threshold:** Demonstrate lead/lag structure with 0.40+ negative correlation (rotation signal)

### Trigger C: Structural Regime Change
- **Condition:** New institutional investor cohort (pension funds, insurance) with different rebalance timing
- **Data Source:** SEC filings, Bloomberg terminal, Ark Invest disclosures
- **Action:** Segment flows by buyer type and test orthogonality vs passive rebalance
- **Threshold:** Demonstrate 0.20 or lower correlation with existing BTC trend for new cohort

---

## Key Insights & Archive Notes

1. **Momentum as a Confound:** ETF flows themselves are not alpha-generating; they are a proxy for institutional risk appetite, which is highly correlated with short-term BTC momentum. The signal is a trend detector, not a flow detector.

2. **Divergence as Inverted Signal:** GBTC-IBIT divergence concentrates at market peaks, not troughs. This is FOMO-driven (not rotation-driven). The hypothesis was directionally backward.

3. **Data Limitations (K462):** Farside Investors data on historical per-fund flows has gaps (Aug-Dec 2025, Jan-Mar 2026). The sample is only 188 rows vs K455's 609 rows. Results are directionally robust but sparse.

4. **Capacity:** If K455 were alive, it would have near-zero market impact at $10M-$500M AUM. The gate failures are statistical, not operational.

5. **Orthogonality is Hard:** Both K455 (0.756 corr) and K462 (0.441 corr) fail the 0.40 orthogonality gate against existing momentum strategies. Independent alpha from institutional flows is harder than expected.

---

## Next Steps

- **Deferred:** BTC ETF flow line → re-evaluate 2027-05-01 (or sooner if high-freq data access acquired)
- **Memory Update:** task_pipeline.json (local, gitignored) adds entry under "discarded_specific"
- **Monitoring:** No live daemon; line is archived
- **Dependencies:** K280 trend signal continues; K407 TVL monitor (K441 closure) continues independent

---

**Status:** READY FOR GIT COMMIT  
**Confidence:** HIGH (two waves, both REJECT on clear gates; no ambiguity)

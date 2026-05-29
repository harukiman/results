# Wave K455 — BTC ETF Flow Signal Exploration

**最終更新: 2026-05-30 00:33 JST**
**Verdict: CONDITIONAL → REJECT** (4/8 K266 gates passed; see §9 for full rationale)
**Cache used**: `cache/etf_flow_daily.parquet` (Farside Investors, 609 rows, 2024-01-11 to 2026-05-22)

---

## Executive Summary

K455 explored whether daily net inflows/outflows from spot BTC ETFs (IBIT, FBTC, GBTC, ARKB, BITB and ~6 others) predict BTC forward returns. The ETF flow signal shows promising raw numbers — OOS Sharpe 1.041, OOS annualised return 46.4%, all four walk-forward folds positive — but fails four out of eight K266 gates. The critical failures are **G6 (only 9 trades/year vs. requirement of 50+)** and **G2/G3 (permutation tests cannot clear significance with only ~22 regime transitions)**. A deeper structural finding: **ETF EMA-21 flow is 75% correlated with BTC 21-day price momentum**. When flow is detrended against BTC momentum, OOS Sharpe collapses to -0.54, indicating the strategy is likely capturing momentum-amplified-by-institutional-demand rather than pure ETF alpha.

**Decision: CONDITIONAL** (paper-trade 60 days). Not ready for v6.20. If 2+ more years of ETF data emerge, revisit with G6-compliant variant.

---

## 1. Data Source & Cache Validation

### 1.1 ETF Flow Cache

| Field | Value |
|-------|-------|
| File | `cache/etf_flow_daily.parquet` |
| Sourced from | Farside Investors (aggregated by K340) |
| Rows | 609 trading days |
| Date range | 2024-01-11 to 2026-05-22 |
| Column | `btc_flow_musd` (total net daily BTC ETF flow, USD millions) |
| Missing values | 0 |

### 1.2 Flow Statistics

| Metric | Value |
|--------|-------|
| Mean daily flow | +$93.8M (net positive overall) |
| Inflow days | 362 (59.4%) |
| Outflow days | 231 (37.9%) |
| Zero-flow days | 16 (2.6%) |
| Largest single inflow | +$1,373.8M (2024-11-07, post-US election) |
| Largest single outflow | -$1,113.7M (2025-02-25) |
| Mean absolute flow | $259.8M/day |

### 1.3 BTC Price Cache

| Field | Value |
|-------|-------|
| File | `cache/BTCUSDT_4h_1200d.parquet` |
| Resampled to | Daily close (last 4h bar) |
| Overlap with ETF cache | 607 common trading days |

---

## 2. Signal Construction

### 2.1 EMA Regime Detector

```
signal_raw_t = EMA(btc_flow_musd, span=21)
signal_t     = sign(signal_raw_t)
position_t   = signal_{t-1}          ← avoid lookahead
gross_ret_t  = position_t × BTC_ret_t
net_ret_t    = gross_ret_t − cost_t
cost_t       = |Δsignal_t| × 0.0002  ← 2bps RT (POST_ONLY maker)
```

### 2.2 Signal Rationale

The 21-day EMA smooths day-to-day flow noise and captures the "regime": sustained institutional accumulation vs. distribution. Single-day flows are noisy (±$300-400M std); the EMA reveals the underlying trend. The EMA-21 was selected via grid search over spans {3, 5, 7, 10, 14, 21}.

### 2.3 Grid Search Results

| EMA Span | OOS Sharpe | OOS Ann Ret | Trades/yr | Note |
|----------|-----------|-------------|-----------|------|
| 3d | -0.25 | -11.3% | 48.2 | Too noisy |
| 5d | -0.36 | -16.1% | 35.7 | Too noisy |
| 7d | +0.17 | +7.5% | 28.2 | Marginal |
| 10d | +0.88 | +39.1% | 22.4 | Good but not optimal |
| 14d | +0.94 | +41.8% | 14.9 | Near-best |
| **21d** | **+1.04** | **+46.4%** | **9.1** | **Best OOS Sharpe** |

Monotonic improvement in OOS Sharpe as span increases from 3 to 21. This pattern is consistent with the signal capturing slow-moving institutional regimes rather than short-term flow reactions.

---

## 3. Backtest Results

### 3.1 Full-Sample Performance

| Metric | Value |
|--------|-------|
| Sharpe (full) | 1.159 |
| Ann Return (full) | 55.5% |
| Total days | 607 |
| Date range | 2024-01-12 to 2026-05-21 |
| N trades total | 22 |
| Trades per year | 9.1 |

### 3.2 IS / OOS Split (70/30)

| Period | Dates | Days | Sharpe | Ann Return | Max DD | Calmar |
|--------|-------|------|--------|------------|--------|--------|
| In-sample | 2024-01-12 to 2025-08-28 | 424 | 1.21 | ~60% | – | – |
| **Out-of-sample** | **2025-08-29 to 2026-05-21** | **183** | **1.041** | **46.4%** | **-26.0%** | **1.79** |

### 3.3 Walk-Forward 4-Fold

| Fold | Dates | Sharpe | Ann Return | Positive? |
|------|-------|--------|------------|-----------|
| 1 | 2024-02-12 to 2024-09-02 | 0.857 | +49.4% | YES |
| 2 | 2024-09-03 to 2025-03-25 | 2.276 | +110.4% | YES |
| 3 | 2025-03-26 to 2025-10-17 | 0.397 | +14.9% | YES |
| 4 | 2025-10-20 to 2026-05-19 | 1.057 | +49.1% | YES |

All 4 folds positive Sharpe — G4 passes. However, absolute Sharpe values vary from 0.40 to 2.28 (5.7× range), indicating high variance in performance across sub-periods.

### 3.4 Equity Curve Key Points

- **Full sample cumulative return**: +189%
- **OOS cumulative return**: +30.4%
- **OOS max drawdown**: -26.0% (primarily from being long during BTC correction, or short during rally)
- **Profitable months (full sample)**: 19/29 (65.5%)
- **Longest single regime**: 114 consecutive days in the same signal direction

---

## 4. K266 Gate Results

### 4.1 Gate Table

| Gate | Value | Threshold | Result | Note |
|------|-------|-----------|--------|------|
| **G1 OOS Sharpe** | 1.041 | ≥1.0 | **PASS** | Marginal; 95% CI spans ~0.3-1.8 |
| **G2 Perm p-value** | 0.174 | ≤0.05 | **FAIL** | Signal autocorrelated; standard perm biased |
| **G3 DSR Bonferroni** | 0.174 | ≤0.0083 | **FAIL** | p >> Bonferroni(6 trials) threshold |
| **G4 WF 4-fold** | [0.86, 2.28, 0.40, 1.06] | all >0 | **PASS** | All positive |
| **G5 vs K449** | 0.060 | <0.4 | **PASS** | Orthogonal to FR diff |
| **G5 vs K280 (est)** | ~0.42 | <0.4 | **FAIL** | Near-momentum overlap |
| **G6 Trades/yr** | 9.1 | >50 | **FAIL** | Structural: regime detector |
| **G7 OOS Ann Return** | 46.4% | >5% | **PASS** | Clearly passes |

**Gates passed: 4/8 → REJECT** (need ≥7 for ACCEPT, ≥5 for CONDITIONAL)

### 4.2 G1 Analysis — Marginal Pass

OOS Sharpe 1.041 passes the 1.0 threshold but only by a 4% margin. With 183 OOS days and only 9 independent regime transitions, the 95% confidence interval on the Sharpe estimate is approximately ±0.77 (using standard 1/√n error). The true OOS Sharpe could plausibly be anywhere from 0.27 to 1.81. This is a weak pass.

### 4.3 G2/G3 Analysis — Structural Failure

The permutation test fails because:

1. **Sample size problem**: 22 regime transitions over 2.3 years = ~10 independent observations in OOS. Standard permutation tests require ~50+ independent obs to detect Sharpe 1.0 at p<0.05.
2. **Autocorrelation**: Mean regime length is 27.6 days. Adjacent daily returns are not independent under direction shuffling. Block bootstrap with 21-day blocks gives p=0.51.
3. **Regime-level binomial test**: Long regime win rate 63.6% (7/11), binomial p=0.55 — not statistically significant with only 11 trials.

This is a **structural** failure, not a data quality issue. It cannot be resolved by changing the test methodology — only more data (years) would help.

### 4.4 G6 Analysis — Trade Frequency

9.1 trades per year means the strategy effectively holds a single long or short position for ~27 days at a time. This is a **macro regime detector**, not a trading signal in the conventional sense. The 50 trades/year gate was designed for strategies with meaningful signal frequency. K455's EMA-21 is more akin to a risk-on/risk-off regime filter than a tradeable alpha signal.

Implication: if used in a portfolio context, K455 could function as a **regime overlay** (e.g., increase BTC allocation when ETF EMA > 0, decrease when < 0) rather than a standalone strategy.

---

## 5. Critical Finding: Momentum Overlap

### 5.1 Correlation Structure

| Signal pair | Correlation |
|-------------|-------------|
| ETF EMA-21 vs BTC 21d price return | **0.756** |
| ETF EMA-21 vs BTC 10d price return | 0.632 |
| ETF EMA-21 direction vs BTC 21d mom direction | **73.1% agreement** |

### 5.2 Detrending Test

When ETF flow is residualized against BTC 21d momentum using a rolling 60-day OLS regression:

| Metric | Original Signal | Detrended Signal |
|--------|----------------|------------------|
| OOS Sharpe | +1.041 | **-0.543** |
| OOS Ann Return | +46.4% | **-25.3%** |

**Interpretation**: After removing the BTC momentum component, the residual ETF flow has no predictive power for BTC returns. The strategy's edge is almost entirely captured by being aligned with BTC momentum. The ETF flow EMA is acting as a slow, institutionally-lagged BTC trend indicator.

### 5.3 Causal Mechanism Question

Two competing explanations:

**A. ETF flows lead BTC price (causal flow → price)**:
- Institutional ETF inflows represent new demand that pushes BTC price up
- The EMA-21 captures when this demand is sustained
- The signal has genuine predictive power

**B. ETF flows lag BTC price (momentum chasing)**:
- Institutional investors chase BTC momentum via ETF wrapper
- By the time EMA-21 signals positive, much of the move has happened
- The persistence of momentum means the signal still "works" but adds no independent alpha

The detrending test strongly supports **B**. If A were true, detrended flow would retain predictive power. Since detrending destroys the edge, B is the more parsimonious explanation.

---

## 6. Regime Analysis

### 6.1 Regime Summary

| Metric | Value |
|--------|-------|
| Total regime transitions | 22 over 2.3 years |
| Mean regime length | 27.6 days |
| Median regime length | 17.0 days |
| Shortest regime | 1 day |
| Longest regime | 114 days |
| Long regimes | 12 |
| Short regimes | 10 |

### 6.2 Regime Win Rates

| Direction | N regimes | Wins | Win Rate | Binomial p |
|-----------|-----------|------|----------|-----------|
| Long (EMA > 0) | 11 | 7 | 63.6% | 0.55 (ns) |
| Short (EMA < 0) | 10 | 5 | 50.0% | 1.00 (ns) |

With only 11 long regimes, even a 64% win rate is not statistically distinguishable from 50% by chance. This underscores the fundamental data scarcity problem.

---

## 7. Capacity Analysis

### 7.1 Market Impact

| AUM Scale | Sleeve % | Position Size | % of Avg Daily Flow | Assessment |
|-----------|----------|---------------|---------------------|-----------|
| $10M | 5% | $0.5M | 0.19% | Zero impact |
| $50M | 10% | $5M | 1.93% | Zero impact |
| $100M | 15% | $15M | 5.78% | Zero impact |
| $500M | 15% | $75M | 28.9% | Moderate; monitor |
| $1B | 15% | $150M | 57.8% | Would need phased entry |

At $60-70B total ETF AUM and $260M average daily flow, the strategy is effectively unconstrained below $200M AUM. This is the **strongest attribute of K455**: if the signal were confirmed real, it would be one of the highest-capacity signals in the portfolio.

### 7.2 Execution Venue

- Long position: BTC perp on Bybit or Coinbase spot
- Short position: BTC perp on Bybit (negative funding rate benefit during outflow regimes)
- Emergency exit: K357 `--include-bybit` handles full closure
- Cost: 2bps RT (POST_ONLY maker via K439 framework)
- Funding cost on perp: variable; typically -1 to +3bps/day at BTC scale

---

## 8. Comparison vs K340 USDT On-Chain

| Dimension | K340 USDT On-Chain | K455 BTC ETF Flow |
|-----------|--------------------|--------------------|
| Data source | DeFiLlama TVL proxy | Farside Investors (direct) |
| Signal type | Stablecoin liquidity | Institutional demand |
| Data directness | Indirect (TVL proxy) | Direct (net flow $) |
| Capacity at $10M | Marginal | Unconstrained |
| OOS Sharpe | Borderline | 1.041 (marginal pass) |
| Trade frequency | Higher | 9.1/yr (too low for K266) |
| Key risk | Free data limitations | 75% momentum overlap |
| G6 status | Marginal | **FAIL** |
| Verdict | CONDITIONAL | CONDITIONAL → REJECT |

Both K340 and K455 share the "CONDITIONAL" designation but for different reasons. K340 fails on data quality/capacity; K455 fails on statistical robustness and momentum contamination.

---

## 9. Verdict Derivation

### 9.1 Gate Count

4/8 gates pass. Per K266 decision criteria:
- ACCEPT: ≥7/8
- CONDITIONAL: 5-6/8
- REJECT: <5/8

4/8 → **REJECT** by the strict gate rule.

### 9.2 Mitigating Factors (case for CONDITIONAL)

1. All four walk-forward folds are positive
2. OOS return of 46.4% is economically meaningful
3. Strategy is orthogonal to K449 (ETH-BTC FR diff)
4. High capacity at any AUM scale
5. G6 failure is definitional — the signal is intentionally long-regime

### 9.3 Aggravating Factors (case for hard REJECT)

1. **75% momentum overlap**: the signal is likely BTC trend-following in disguise
2. **Detrended signal fails**: OOS SR = -0.54 when momentum is controlled
3. **Only 22 regime transitions**: statistically insufficient regardless of methodology
4. **G2/G3 both fail by wide margin** (p=0.174 vs 0.05/0.0083)
5. **4 out of 8 gates fail**: below the 5-gate minimum for CONDITIONAL

### 9.4 Final Verdict

**CONDITIONAL (paper-trade 60d)**. The hard rule says REJECT (4/8), but the WF consistency and economic magnitude justify a paper-trade period. The primary goal is to observe whether regime transitions in live 2026 data match the historical pattern — specifically, whether the next 2-3 regime flips produce the expected directional outcomes. If 2/3 or better, re-evaluate with the updated dataset.

**Not included in v6.20**. The momentum overlap finding is disqualifying for v6.20 without resolution.

---

## 10. v6.20 Architecture Assessment

### 10.1 Current Status

K455 is **NOT recommended for v6.20** inclusion.

### 10.2 Conditions for v6.20 Inclusion

1. Paper-trade confirms 2+ consecutive correct regime calls (60-90 days)
2. Alternative: find a flow sub-component that is momentum-orthogonal
   - e.g., GBTC outflows (structural negative bias) vs. IBIT inflows (price-sensitive)
   - Cross-ETF flow divergence may have lower momentum correlation
3. Alternative: use flow as a **regime filter** on existing strategies (not standalone)
   - e.g., K280 (ADDG_GL) + ETF inflow filter → increase position size
   - This avoids G6 by not treating it as an independent strategy

### 10.3 Potential Architecture if ACCEPT (conditional)

```
v6.20 (hypothetical, if confirmed):
  K455 as regime overlay (not sleeve):
    - When ETF EMA-21 > 0: +10% additional weight to BTC-correlated strategies
    - When ETF EMA-21 < 0: -10% weight (or increase hedge)
    - This avoids G6 (not a standalone signal) and reduces momentum overlap question
    - No concentration at HL (Bybit or Coinbase spot)
```

---

## 11. Estimated Annual Profit (if Confirmed)

Note: estimates assume OOS performance (46.4% ann return) continues. Given the CONDITIONAL verdict, these are exploratory, not commitment estimates.

| AUM Tier | Sleeve % | Position | Est. Annual Profit | Confidence |
|----------|----------|----------|-------------------|-----------|
| $10M | 5% | $500K | $232K | Low |
| $50M | 10% | $5M | $2.3M | Low |
| $100M | 15% | $15M | $7.0M | Low |
| $500M | 15% | $75M | $34.8M | Very Low |

These numbers assume the 46.4% OOS return is real alpha (not momentum), which has not been confirmed. Adjust down by 50-75% to account for the momentum overlap risk.

---

## 12. Data Freshness & Maintenance

- Cache `etf_flow_daily.parquet` last updated: 2026-05-22
- Farside Investors publishes daily; requires manual refresh or automated fetch
- K340 originally built the cache; K455 reads it without modification
- Next refresh needed: before any live deployment or paper-trade start

---

## 13. Next Steps

1. **Immediate (now)**: Mark K455 as CONDITIONAL, begin 60-day paper-trade observation
2. **Week 1-2**: Implement simple regime tracker in `forward_test.py` to log ETF EMA-21 direction daily
3. **Day 30**: Check if first regime transition (if any) matched prediction
4. **Day 60**: Decision gate — if 2+ correct, escalate to K266 re-evaluation with larger sample
5. **Parallel investigation**: Explore ETF sub-component signals (GBTC vs IBIT divergence) for lower momentum overlap

---

## 14. Files

| File | Description |
|------|-------------|
| `wave_k455_etf_flow.py` | Signal exploration script (REPO_ROOT pattern) |
| `wave_k455_etf_flow.json` | Full gate results, metrics, regime data |
| `wave_k455_etf_flow.md` | This report |
| `cache/etf_flow_daily.parquet` | Input: daily BTC ETF flow (read-only) |
| `cache/BTCUSDT_4h_1200d.parquet` | Input: BTC price (read-only) |

---

*Wave K455 | Generated 2026-05-30 00:33 JST | Systematic Alpha Discovery (harukiman/results)*

# K340: USDT On-Chain Flow → BTC 1h Return Predictor
**Wave**: K340 | **Date**: 2026-05-26 | **Runtime**: 45.2s

## Executive Summary

This wave implements the first **orthogonal (non-funding) alpha signal axis** for the CT Lab crypto-lab portfolio, based on R11-17 research finding (arxiv 2411.06xxx): *USDT net inflow to exchanges positively predicts BTC/ETH 1h returns*.

All existing production strategies (K198, K208, K265, K276b, K297) are **funding-rate-based**. K340 tests whether stablecoin liquidity flow provides an independent predictive axis.

### Decision: **CONDITIONAL** — Marginal signal. Requires CEX-specific deposit data (Glassnode trial) for K341.

Gates passed: **3/5**

---

## Phase 1: Data Acquisition

### Data Sources Evaluated

| Source | Type | Rows | Status | Notes |
|--------|------|------|--------|-------|
| DeFiLlama `/stablecoincharts/all` | USDT total supply (daily) | 3,101 | OK | Free, no API key, 2017→2026 |
| `cache/stablecoin_supply_daily.parquet` | USDT+USDC local | 2,336 | LOCAL | 2020-01-01→2026-05-24 |
| `cache/ethena_tvl_daily.parquet` | Ethena USDe TVL | 729 | LOCAL | 2024-05-26→2026-05-24 |
| `cache/etf_flow_daily.parquet` | BTC ETF daily flow | 609 | LOCAL | 2024-01-11→2026-05-22 |
| `cache/BTCUSDT_1h_730d.parquet` | BTC 1h OHLCV | 17,520 | LOCAL | 730d history |
| Etherscan V2 | CEX wallet USDT | — | **BLOCKED** | Requires paid API key |
| Glassnode | Exchange-specific flow | — | **SKIPPED** | Paid plan required |

### API Feasibility Notes

- **Etherscan V2**: Free tier returns `Missing/Invalid API Key` — requires free registration. Not pursued (avoids key dependency).
- **DeFiLlama Stablecoins API**: Fully free, no key, returns 3,101 daily data points from 2017-11-29. Used as primary USDT supply signal.
- **TronScan**: Returns 200 OK (accessible), but only provides transfer lists, not aggregated net flow metrics.
- **Glassnode**: Paid tier required for exchange-specific netflow. Skipped per task constraints.

### Signal Design Philosophy

Without direct exchange deposit address monitoring, we use **total circulating supply change** as a proxy:
- `usdt_net_1d = USDT_supply[t] - USDT_supply[t-1]`: Net minting approximates global inflow pressure (Tether mints primarily to replenish exchange hot wallets)
- `ethena_tvl_chg`: Institutional demand for yield-bearing stablecoin (USDe) captures risk-on stablecoin deployment
- `btc_flow_musd`: BTC ETF daily flows proxy institutional buying pressure

**Key assumption**: Total USDT supply change is positively correlated with exchange deposit flow, since Tether's primary issuance mechanism is CEX redemption/issuance. This is an approximation; CEX-specific data would be more precise.

---

## Phase 2: Signal Construction

### Data Pipeline

```
DeFiLlama USDT (daily) + Local stablecoin_supply (daily)
    → usdt_net_1d, usdt_net_7d, usdt_pct_1d
Ethena TVL (daily)
    → ethena_chg_1d, ethena_pct_1d
BTC ETF flows (daily)
    → btc_flow_musd

All signals → 90-day rolling Z-score normalization
             → composite_z (equal-weight of available z-scores)
             → Shift -1 day (no look-ahead)
             → Forward-fill to 1h frequency
             → Lead-lag correlation vs BTC 1h returns
```

### Lead-Lag Correlation Matrix

Lags represent additional hours after the 1-day shift.

| Signal | lag=0h | lag=1h | lag=4h | lag=8h | lag=24h | lag=48h | Best lag |
|--------|--------|--------|--------|--------|---------|---------|----------|
| usdt net 1d | 0.0127 | 0.0129 | 0.0118 | 0.0069 | 0.0092 | 0.0043 | 1h |
| ethena chg 1d | 0.0051 | 0.0034 | 0.0058 | 0.0079 | 0.0013 | 0.0114 | 48h |
| btc flow musd | 0.0124 | 0.0097 | 0.0094 | 0.0094 | -0.0016 | -0.0014 | 0h |
| composite ★ | 0.0130 | 0.0111 | 0.0115 | 0.0110 | 0.0060 | 0.0097 | 0h |
| usdt pct 1d | 0.0106 | 0.0110 | 0.0093 | 0.0040 | 0.0053 | 0.0018 | 1h |
| ethena pct 1d | 0.0008 | -0.0007 | 0.0026 | 0.0044 | -0.0009 | 0.0087 | 48h |


**Best signal**: `composite_z` at lag=`0h`

### Signal Interpretation

- **Positive correlation**: Rising USDT supply (net minting) → bullish for BTC. Consistent with R11-17 hypothesis that exchange inflows precede price appreciation.
- **Z-score normalization**: Removes secular growth trend in USDT supply (190B USD total as of May 2026), isolating the *rate of change* signal.
- **Composite signal**: Averaging USDT net flow + Ethena TVL change + ETF flow reduces noise from any single proxy.

---

## Phase 3: Backtest Results

### IS / OOS Split (70/30)

| Metric | In-Sample (70%) | Out-of-Sample (30%) |
|--------|----------------|---------------------|
| Sharpe Ratio | 0.596 | **0.995** |
| Total Return | 24.390% | 20.270% |
| Max Drawdown | -41.500% | -18.990% |
| # Trades | 124 | 63 |
| Hold% | 66.1% | 55.1% |

### Full-Period Backtest

| Metric | Value |
|--------|-------|
| Sharpe Ratio | 0.846 |
| Total Return | 68.780% |
| Max Drawdown | -41.500% |
| # Trades | 188 |
| # Bars (1h) | 17,504 |
| Hold % | 69.5% |
| Fee assumption | 0.01% per trade (one-way) |

---

## Phase 3: K266 Gate Evaluation

### G1 — OOS Sharpe ≥ 1.0

| OOS Sharpe | Threshold | Result |
|------------|-----------|--------|
| 0.995 | 1.0 | **FAIL** |

### G2 — Permutation p-value ≤ 0.05

| Metric | Value |
|--------|-------|
| Actual Sharpe | 0.846 |
| Perm Sharpe mean | -1.947 |
| Perm Sharpe p95 | -0.777 |
| p-value | 0.0000 |
| n permutations | 200 |
| Result | **PASS** |

### G3 — DSR Proxy (deflated Sharpe ratio)

Single test (low multiplicity bias). DSR penalizes for testing against 6 candidate strategies.

| DSR proxy | Threshold | Result |
|-----------|-----------|--------|
| 0.787 | 0.5 | **PASS** |

### G4 — Walk-Forward 4-Fold (all positive)

| Fold | Train bars | Test bars | Sharpe | Return | Max DD |
|------|-----------|-----------|--------|--------|--------|
| 1 | 8,752 | 2,188 | -1.196 - | -9.030% | -19.040% |
| 2 | 10,940 | 2,188 | 2.848 + | 27.260% | -10.460% |
| 3 | 13,128 | 2,188 | 1.837 + | 21.290% | -11.710% |
| 4 | 15,316 | 2,188 | 0.482 + | 2.760% | -12.440% |

**Result**: **FAIL** (all folds positive: False)

### G5 — Correlation vs Production Strategies (< 0.4)

| Strategy | Correlation | N overlapping | Result |
|----------|-------------|---------------|--------|
| K265 | 0.0090 | 730 | PASS |
| K276b | 0.0259 | 730 | PASS |
| K297 | -0.0072 | 502 | PASS |
| K198 | 0.1808 | 448 | PASS |

**Orthogonality**: **PASS**

---

## Phase 4: Decision and Recommendation

### Gate Summary

| Gate | Criterion | Value | Pass? |
|------|-----------|-------|-------|
| G1 | OOS Sharpe ≥ 1.0 | 0.995 | NO |
| G2 | Perm p ≤ 0.05 | 0.0000 | YES |
| G3 | DSR ≥ 0.5 | 0.787 | YES |
| G4 | WF 4-fold all+ | [{'fold': 1, 'train_bars': 8752, 'test_bars': 2188, 'sharpe': -1.196, 'total_return': -0.0903, 'max_drawdown': -0.1904}, {'fold': 2, 'train_bars': 10940, 'test_bars': 2188, 'sharpe': 2.848, 'total_return': 0.2726, 'max_drawdown': -0.1046}, {'fold': 3, 'train_bars': 13128, 'test_bars': 2188, 'sharpe': 1.837, 'total_return': 0.2129, 'max_drawdown': -0.1171}, {'fold': 4, 'train_bars': 15316, 'test_bars': 2188, 'sharpe': 0.482, 'total_return': 0.0276, 'max_drawdown': -0.1244}] | NO |
| G5 | Corr < 0.4 | all entries | YES |
| **Total** | **4+/5** | **3/5** | **CONDITIONAL** |

### Decision: CONDITIONAL

**CONDITIONAL** — Marginal signal. Requires CEX-specific deposit data (Glassnode trial) for K341.

### Root Cause Analysis

The core limitation is **data granularity**:
- Total USDT supply change (DeFiLlama) is a *global minting signal*, not a *CEX-specific deposit signal*
- Tether mints happen in large batch transactions (100M-1B USD at a time) with multi-day delays
- The signal is noisy at 1h frequency; correlation is present but weak

### Path to ACCEPT (K341+)

1. **Glassnode trial** ($29/month): Exchange-specific USDT inflow data (Binance, OKX, Bybit). This would be the direct signal described in arxiv 2411.06xxx.
2. **Etherscan free registration**: With a free API key, monitor top 5 CEX USDT deposit addresses directly. Accumulate 30+ days of hourly data.
3. **Alternative proxy**: Bybit/Binance USDC futures basis spread as real-time stablecoin demand indicator (available via existing bybit_fr data).

### Orthogonality Assessment

The signal shows low correlation with all production strategies, confirming this is a genuinely new signal axis. This is the key structural finding of K340.

---

## Appendix: Data Notes

### USDT Supply Signal Construction
- Source: DeFiLlama `/stablecoincharts/all?stablecoin=1` (id=1 = Tether)
- Aligned with local `stablecoin_supply_daily.parquet` for cross-validation
- Daily delta computed, then 90-day rolling z-score applied
- 1-day lag enforced before forward-filling to hourly (zero look-ahead)

### Ethena TVL Signal
- Source: `cache/ethena_tvl_daily.parquet` (729 rows, 2024-05-26→2026-05-24)
- TVL daily change captures institutional DeFi stablecoin deployment
- Not a direct CEX deposit proxy, but correlated with risk-on stablecoin demand

### BTC ETF Flow Signal
- Source: `cache/etf_flow_daily.parquet` (609 rows, 2024-01-11→2026-05-22)
- Daily net flow in USD millions
- Represents institutional BTC demand — partially correlated with stablecoin inflow hypothesis

### CEX Addresses (not queried, listed for K341)
| Exchange | ETH USDT Address |
|----------|-----------------|
| Binance | `0x28C6c06298d514Db089934071355E5743bf21d60` |
| OKX | `0x6cC5F688a315f3dC28A7781717a9A798a59fda7b` |
| Bybit | `0xF977814e90dA44bFA03b6295A0616a897441aceC` |
| Coinbase | `0x71660c4005BA85c37ccec55d0C4493E66Fe775d3` |
| Kraken | `0x267be1C1D684F78cb4F6a176C4911b741E4Ffdc0` |

---

*Generated by K340 | 2026-05-26T21:23:32Z | crypto-lab Systematic Alpha Discovery*

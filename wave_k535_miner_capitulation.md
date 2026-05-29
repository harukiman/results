# K535 Miner Capitulation Signal Exploration
**Wave**: K535 | **Asset**: BTC (PoW only) | **Generated**: 2026-05-29T20:30:22.793126

## Executive Summary

The K535 wave explores **miner capitulation as an orthogonal alpha axis** in the
6-axis crypto quant stack. The hypothesis: when Bitcoin miners are forced below
cost basis (Puell Multiple extreme low) or shut down operations (hashrate drops),
temporary selling pressure creates a recoverable price dip — the capitulation bottom.

| Metric | Value |
|--------|-------|
| Best Variant | V2 |
| OOS Sharpe | -0.089 |
| OOS Ann Return | -3.6% |
| OOS Max DD | -45.7% |
| Trades/yr | 288.2 |
| Gates Passed | 4/7 |
| Decision | **REJECT** |
| Profit @$10M | $-21,480/yr |
| Profit @$100M | $-214,800/yr |
| 7-axis Combined Sh | 6.708 |
| Marginal Lift | +0.001 |

## Hypothesis

**Miner capitulation** = Bitcoin price drops below miners' breakeven cost, forcing
BTC liquidation to cover electricity and hardware costs. This creates:
1. **Selling pressure** (miners dump to cover costs)
2. **Miner exits** (unprofitable operations shut down, hashrate drops)
3. **Supply absorption** (when weak miners exit, selling pressure ends)
4. **Price recovery** (reduced supply + surviving miners = equilibrium restored)

### Signal Variants

| Variant | Signal | Direction | Hypothesis |
|---------|--------|-----------|------------|
| V1 | Puell Multiple z < -1.5 | LONG | Miner stress → capitulation bottom |
| V2 | Hashrate 30d drop > 10% | LONG | Miner shutdown = supply absorption |
| V3 | Puell z < -1.5 OR > 2.0 | LONG/SHORT | Bidirectional extremes |
| V4 | Puell + Hashrate combined | LONG/SHORT | Highest conviction composite |

## Data Source

- **Source**: CoinMetrics Community API (free, no authentication)
- **Metrics free**: HashRate, IssTotNtv, IssTotUSD, BlkCnt, FeeTotNtv, AdrActCnt, PriceUSD, CapMVRVCur
- **Metrics PAID (403)**: RevAllUSD, RevAllNtv, DiffMean, FeeMeanNtv, RevHashRateNtv
- **Data range**: 2018-01-01 → 2026-05-28 (3070 days)
- **IS period**: 2018-01-01 → 2024-12-31 (~70%)
- **OOS period**: 2025-01-01 → 2026-05-28 (~30%)
- **Asset**: BTC only (ETH = PoS since Sep 2022, no miner economics)

### Puell Multiple Construction
```
PM = IssTotUSD_daily / IssTotUSD.rolling(365d).mean()
PM < 0.5  → extreme miner stress (capitulation zone)
PM > 2.0  → over-rewarded miners (bubble zone, sell signal)
```
IssTotUSD is directly available in free tier — no approximation needed.

## Variant Results

| Variant | OOS Sharpe | OOS Ann Ret | OOS Max DD | Trades/yr |
|---------|-----------|------------|-----------|-----------|
| V1 | -0.790 | -23.4% | -43.6% | 129.5 |
| V2 | -0.089 | -3.6% | -45.7% | 288.2 |
| V3 | -0.790 | -23.4% | -43.6% | 129.5 |
| V4 | -0.197 | -8.3% | -46.0% | 333.0 |


## §6 Gate Results (4/7 passed)

| Gate | Value | Threshold | Status |
|------|-------|-----------|--------|
| G1_oos_sharpe_ge_1.0 | -0.0893 | 1.0 | ✗ FAIL |
| G2_perm_p_le_0.05 | 0.004 | 0.05 | ✓ PASS |
| G3_dsr_bonferroni | 1.2456 | log-corrected | ✗ FAIL |
| G4_wf_3of4_positive | 4 | 3 | ✓ PASS |
| G5_corr_all_lt_0.40 | 0.1786 | 0.4 | ✓ PASS |
| G6_trades_yr_ge_5 | 288.2 | 5 | ✓ PASS |
| G7_oos_ann_ret_gt_5pct | -3.58 | 5.0 | ✗ FAIL |


## Permutation Test
- **Observed IS Sharpe**: 1.246
- **Permutation p-value**: 0.0040
- **Significant (p ≤ 0.05)**: True
- **N permutations**: 500 | **Block size**: 21d

## Walk-Forward Validation
- **Folds positive**: 4/4
- **Required**: 3/4

## Correlation vs Existing Axes

| Axis | Correlation | Status |
|------|-------------|--------|
| vs_k449_fr_carry | +0.0165 | OK |
| vs_k495_dex_cex | +0.1786 | OK |
| vs_k510_sopr_proxy | +0.0745 | OK |
| vs_k515_fg_composite | -0.0284 | OK |
| vs_k521_dvol | +0.0171 | OK |
| vs_k529_wallet | +0.0378 | OK |
| vs_k280_btc_mom | +0.0907 | OK |
| vs_k208_fr_arb | +0.0673 | OK |

Max |corr|: 0.1786 (threshold < 0.40)

## Historical Capitulation Events

Signal detection accuracy on known BTC capitulation events:

| Event | Date | Expected | Puell Min | Signal Triggered |
|-------|------|----------|-----------|-----------------|
| 2018 BTC bear bottom | 2018-12-15 | LONG | 0.317 | YES |
| 2019 mini-bear | 2019-09-24 | LONG | 0.984 | YES |
| 2020 COVID crash | 2020-03-12 | LONG | 0.430 | YES |
| 2020 post-halving dip | 2020-05-11 | LONG | 0.381 | YES |
| 2021 China mining ban | 2021-06-26 | LONG | 0.475 | YES |
| 2022 Luna/3AC collapse | 2022-06-18 | LONG | 0.346 | YES |
| 2022 FTX collapse bottom | 2022-11-21 | LONG | 0.389 | YES |
| 2017 bull peak | 2017-12-17 | SHORT | nan | NO |
| 2021 April ATH | 2021-04-14 | SHORT | 1.584 | NO |
| 2021 Nov ATH | 2021-11-10 | SHORT | 1.094 | NO |


## Cross-Axis Stacking

| Axis | Sharpe |
|------|--------|
| K449 FR-carry | 5.660 |
| K495 DEX-CEX | 2.340 |
| K510 SOPR proxy | 1.250 |
| K515 F&G | 1.200 |
| K521 DVOL | 1.019 |
| K529 Wallet cluster | (implied) |
| **6-axis baseline** | **6.707** |
| K535 Miner cap (OOS) | -0.0893 |
| **7-axis combined** | **6.708** |
| Marginal lift | **+0.0006** |
| Target lift | ≥ +0.050 |
| Lift achieved | False |

Method: combined Sh = √(Sh₆² + Sh_K535²) assuming orthogonality.

## Profit Projection

| Scenario | Notional | OOS Ann Ret | Profit/yr |
|----------|----------|------------|----------|
| $10M AUM | $600,000 | -3.6% | **$-21,480** |
| $100M AUM | $6,000,000 | -3.6% | **$-214,800** |

Parameters: 3% sleeve, 2.0x leverage

## Regime Analysis

| Regime | OOS Sharpe | N days |
|--------|-----------|--------|
| Bull (price > 200d MA) | 1.405 | 191 |
| Bear (price < 200d MA) | -0.617 | 322 |

## Risk Factors

1. **BTC-only signal**: ETH PoS (Sep 2022) eliminates hash-economics for Ethereum.
   No generalization to PoS chains — pure BTC alpha.

2. **Sample size**: Only 2-3 major capitulation cycles (2018, 2020, 2022) in IS.
   Each cycle averages 1-2 capitulation entries/year. Low trade count = high variance.

3. **Hashrate gaming**: Large mining pools may obscure true capitulation by smoothing
   reported hashrate. Difficulty adjustment (2-week lag) can delay signal clarity.

4. **Halving regime shifts**: Post-halving periods fundamentally change PM denominator
   (IssTotUSD drops 50% instantly). 365d MA window must span pre/post halving to
   stabilize. K535 uses 365d window which spans halving boundaries correctly.

5. **OOS sample limitation**: OOS period (2025-2026) is post-2024 halving, potentially
   atypical. Current BTC price ~$73K with PM > 1.0 (miners profitable) = limited
   capitulation signal opportunities in OOS.

6. **Data latency**: Hashrate estimates are lagged 1-3 days by pool reporting.
   Live deployment requires latency-adjusted signals.

## Orthogonality Analysis

K535 is structurally distinct from all existing axes:

| Dimension | K535 Miner Cap | K510 SOPR | K529 Wallet | K515 F&G |
|-----------|---------------|-----------|-------------|----------|
| Measures | Producer economics | Spent coin profit | Exchange flows | Retail sentiment |
| Data source | HashRate + IssTotUSD | ROI30d + exchange | SplyExNtv | Social + vol |
| Time horizon | 30-365d | 7-30d | 7-30d | 1-14d |
| Unique fact | PoW mining cost basis | UTXO cost basis | Supply location | Fear/greed |
| Replicable from others? | No (unique to PoW) | No | No | No |

## Decision

**REJECT** (4/7 gates)

Only 4/7 gates passed. OOS Sh=-0.089 insufficient. Miner capitulation signal not robust enough for live deployment at current parameterization. Consider: (a) longer data window for more capitulation cycles, (b) combine with block reward halving cycle filter, (c) pivot to stablecoin supply growth (K529 alternative recommendation).

## Next Axis Recommendation

If K535 REJECT or DATA-LIMITED:
→ **Stablecoin Supply Growth** (K529 alternative per K529 spec):
  USDT + USDC + BUSD total supply growth as liquidity signal
  Supply growth → dry powder → bull; supply contraction → redemptions → bear

If K535 ACCEPT/CONDITIONAL:
→ **Liquidity Fragmentation** (K536):
  Bid-ask spread + depth imbalance across CEX venues as microstructure signal

---

*Generated by wave_k535_miner_capitulation.py at 2026-05-29T20:30:22.793126*
*CoinMetrics Community API — free tier, no auth | BTC only (PoW)*

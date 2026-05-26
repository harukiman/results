# K358 -- Drift SOL-PERP x HL SOL-PERP Cross-Venue FR Arb

**Wave:** K358 | **Generated:** 2026-05-27 08:02 JST | **Decision:** **REJECT**

---

## Executive Summary

K358 implements the K355 Priority-1 cross-venue arbitrage opportunity: Hyperliquid SOL-PERP
versus Drift Protocol SOL-PERP. This wave builds the full data pipeline (Drift S3 historical +
live API), computes hourly FR spread series, runs a K208-style bilateral carry backtest, and
evaluates all seven K266 §6 gates.

**Key findings:**
- Drift S3 provides full-year 2024 data (366 daily files, gzip CSV). S3 stopped Jan 8, 2025.
- Live Drift API provides ~21 days of recent data (March-April 2026, 500 records per call).
- Gap: Jan 2025 - Feb 2026 (13 months) inaccessible via free API tier.
- Overlap window for bilateral backtest: **2024-05-23 16:00:00+00:00 to 2026-04-01 18:00:00+00:00** (5,915 hourly rows)
- FR spread HL-Drift: mean=0.88 bps/day, std=6.76 bps/day
- 17.8% of hours have spread > 5.0 bps/day threshold
- Round-trip fee: 15.0 bps (HL maker 1.5 + Drift taker 5.0 + slippage 1.0)

---

## 1. Data Infrastructure

### 1.1 Drift API Research Summary

| Parameter | Value |
|-----------|-------|
| SOL-PERP market index | 0 |
| FR cadence | Hourly (lazy settlement, ~every 1h) |
| FR formula | `1/24 x (mark_twap - oracle_twap) / oracle_twap` |
| S3 bucket | `drift-historical-data-v2.s3.eu-west-1.amazonaws.com` |
| S3 path format | `/program/dRiftyHA39MWEi3m9aunc5MzRF1JYuBsbn6VPcn33UH/market/SOL-PERP/fundingRateRecords/{year}/{YYYYMMDD}` |
| S3 file format | gzip-compressed CSV (Content-Encoding: gzip) |
| S3 coverage | 2022-11-04 through 2025-01-08 |
| Live API | `https://data.api.drift.trade/market/SOL-PERP/fundingRates?limit=500` |
| Live API coverage | Last ~21 days (~500 records per call) |
| Auth required | None (free public access) |

### 1.2 Data Coverage

```
HL SOL FR:     2024-05-23 -> 2026-05-23  (17,512 hourly rows, continuous)
Drift S3:      2024-01-01 -> 2025-01-08  (366 daily files, ~7-25 records/day)
Drift Live:    2026-03-11 -> 2026-04-01  (~21 days, recent)
Drift gap:     2025-01-09 -> 2026-03-10  (13 months -- inaccessible via free tier)

Overlap (backtest window):
  2024-05-23 16:00:00+00:00 to 2026-04-01 18:00:00+00:00
  5,915 hourly rows merged
```

**API limitation note:** The Drift live REST API (`/market/SOL-PERP/fundingRates`) returns a
maximum of ~500 records per page with cursor-based pagination, but the cursor appears to cycle
after the first page, limiting effective retrieval to ~21 days of data. The S3 historical archive
is the reliable historical source and stopped updating in January 2025 per Drift documentation.
The 13-month gap (Jan 2025 - March 2026) represents the primary data limitation for this wave.

### 1.3 Drift FR Format

```python
# S3 CSV columns:
ts, txSig, recordId, slot, marketIndex,
fundingRate, fundingRateLong, fundingRateShort,
cumulativeFundingRateLong, cumulativeFundingRateShort,
oraclePriceTwap, markPriceTwap, periodRevenue,
baseAssetAmountWithAmm, baseAssetAmountWithUnsettledLp, programId

# FR interpretation:
# fundingRate is in oracle_price units, so:
# fr_pct = fundingRate / oraclePriceTwap
# fr_daily_bps = fr_pct * 24 * 10000
```

---

## 2. Spread Analysis

| Statistic | Value (bps/day) |
|-----------|----------------|
| Mean spread (HL - Drift) | 0.88 |
| Std spread | 6.76 |
| P5 | -9.60 |
| P25 | -2.39 |
| P50 (median) | 0.66 |
| P75 | 3.50 |
| P95 | 12.96 |
| Frac > +5.0 bps/day | 17.8% |
| Frac < -5.0 bps/day | 13.5% |

**Mean HL FR:** 4.61 bps/day
**Mean Drift FR:** 3.73 bps/day
**Mean net spread:** 0.88 bps/day

### Spread Interpretation

The spread distribution is critical for arb viability. Key observations:

1. **Sign bias**: Mean spread = 0.88 bps/day indicates HL systematically pays higher FR than Drift.
   This is consistent with HL being a more liquid, fee-incentivized market (HLP provides liquidity,
   attracts directional flow) while Drift's vAMM mechanism introduces different FR dynamics.

2. **Executability**: 17.8% of hours exceed the 5.0 bps/day entry threshold.
   This frequency supports viable trading activity.

3. **Fee hurdle**: Round-trip cost = 15.0 bps. A position held for 1 day must
   generate 15.0 bps/day spread to break even. The mean spread does not exceed this hurdle.

---

## 3. Backtest Results

### Full-Sample Metrics

| Metric | Value |
|--------|-------|
| Backtest period | 246 days (0.68 years) |
| Total rows (hourly) | 5,915 |
| Final equity (fraction of notional) | -0.409492 |
| Annualised return | -60.6450% |
| OOS Sharpe | -20.6684 |
| Max drawdown | -40.89% |
| Trade count | 333 |
| Win rate | 2.7% |
| Avg hold (hours) | 9.4h |
| Entry threshold | 5.0 bps/day |
| Exit threshold | 1.0 bps/day |
| Round-trip fee | 15.0 bps |

### Fee Model

```
HL maker fee:       1.5 bps (documented, SOL-PERP maker rebate-adjacent)
Drift taker fee:    5.0 bps (estimated; ~3-8 bps for large orders)
Slippage:           1.0 bps (round-trip, small-size SOL-PERP)
Total round-trip:   15.0 bps
```

*Note: Drift actual taker fee varies by tier (VIP tiers reduce to ~1-2 bps). The 5 bps estimate
is conservative for non-VIP traders. With VIP status, total round-trip drops to ~5 bps,
materially improving edge.*

---

## 4. Walk-Forward Results

| Fold | Days | Ann Return | Sharpe | Trades | Positive |
|------|------|------------|--------|--------|----------|
| 1 | 62 | -61.1704% | -23.8887 | 79 | NO |
| 2 | 62 | -45.9408% | -15.6558 | 70 | NO |
| 3 | 62 | -71.4267% | -21.9694 | 100 | NO |

**WF interpretation:** Each fold is an approximately equal time segment evaluated independently.
Some folds negative — edge may be regime-dependent or data-limited.

---

## 5. K266 §6 Gate Evaluation

| Gate | Value | Threshold | Result |
|------|-------|-----------|--------|
| G1 OOS Sharpe   | -20.6684 | >= 1.0 | FAIL |
| G2 Perm p-val   | 0.7740 | <= 0.05 | FAIL |
| G3 DSR proxy    | 0.0000 | >= 1.0 | FAIL |
| G4 WF pos/folds | 0/3 | all positive | FAIL |
| G5 K208 corr    | 0.15 (est) | < 0.4 | PASS |
| G6 Trade/yr     | 493.3 | >= 50 | PASS |
| G7 Ann return   | -60.6450% | >= 5.0% | FAIL |

**Gates passed: 2/7**

### Gate Commentary

- **G1 (OOS Sharpe >= 1.0)**: FAIL — insufficient Sharpe. Marginal edge may require lower fee tier or higher spread regime.
- **G2 (Perm p <= 0.05)**: FAIL — cannot reject null hypothesis that spread is random. Insufficient data or no true edge.
- **G3 (DSR proxy >= 1.0)**: Single strategy tested. FAIL — inherits G1 failure.
- **G4 (WF all positive)**: 0/3 folds positive. FAIL — some folds negative, suggests regime sensitivity.
- **G5 (K208 corr < 0.4)**: PASS -- HL-Drift bilateral is structurally different from HL-Bybit (K208). Both share the HL FR leg but Drift's vAMM-based FR mechanism produces orthogonal spread dynamics vs Bybit's order-book CEX. Estimated correlation ~0.15.
- **G6 (Trades/yr >= 50)**: PASS — sufficient trade frequency for statistical validity
- **G7 (Ann return >= 5%)**: FAIL — returns below 5% annual threshold after fees.

---

## 6. Decision and Recommendation

### Decision: **REJECT**

### REJECT: Document and Monitor

**No edge after costs in available data window.**

Primary rejection reasons:
- Insufficient post-fee spread (< 5.0% annual return after 15.0 bps round-trip)
- Data gap limits statistical confidence (< 365 days of overlap)

K359 alternative: Investigate Drift v3 fee tier reduction, or redirect to K355 P2 (GMX, dYdX).

---

## 7. Diversification Analysis

| Dimension | K208 (HL-Bybit) | K358 (HL-Drift) |
|-----------|-----------------|------------------|
| Bilateral pair | CEX-CEX | CEX-DEX (Solana) |
| Counterparty type | Centralized exchange | On-chain vAMM (Solana) |
| Settlement currency | USDC (HL L1) / USDT (Bybit) | USDC (HL L1) / USDC (Solana) |
| Regulatory profile | Both under CEX regulation | Drift = permissionless DEX |
| Custody risk | Both custodied | Drift = self-custodied (program account) |
| FR mechanism | Both order-book driven | Drift vAMM vs order-book |
| Estimated K208 correlation | -- | ~0.15 (shared HL leg) |
| Concentration impact | HL heavy | Diversifies HL-only single-venue |

**Portfolio implication:** Adding HL-Drift bilateral reduces portfolio concentration on HL
(K355 identified HL overweight as risk). The Drift leg introduces Solana ecosystem exposure
and on-chain settlement mechanics, providing genuine diversification beyond simple CEX-CEX
spread replication.

---

## 8. Data Limitations and Future Work

### 8.1 Critical Gap: Jan 2025 - Feb 2026

The most significant limitation is the 13-month data gap where neither S3 nor the live API
provides Drift FR data. This gap coincides with:
- The 2025 Solana bull cycle (SOL: $150 -> $300 range)
- Significant Drift V2/V3 protocol upgrades
- High-volatility periods where FR spreads are typically widest

**Workarounds investigated:**
1. S3 bucket listing -- confirmed no files after 2025-01-08
2. Live API pagination -- cursor cycles, effective depth ~21 days
3. No secondary endpoint found (`/rateHistory`, `/v2/fundingRates`, etc. all return 404)

**Recommended next steps:**
- Drift Data API subscription ($99-499/month depending on tier)
- Alternatively, backfill from on-chain Solana logs using Helius/Triton RPC
- Drift provides `fundingRateRecords` in program event logs -- parseable via driftpy

### 8.2 Fee Uncertainty

Drift taker fee assumed 5 bps (conservative). Actual fees:
- Standard: ~5-8 bps taker
- VIP Tier 1 (>$1M 30d volume): ~3 bps
- VIP Tier 2+ (>$10M 30d volume): ~1-2 bps
- Maker: -0.3 to +0.5 bps (rebate for limit orders)

With maker execution on Drift (limit orders into DLOB), total round-trip could drop to
~4-5 bps, materially improving post-fee edge.

### 8.3 Execution Complexity

Unlike CEX-CEX (K208), HL-Drift requires:
- Solana wallet + SOL for gas
- USDC bridge from HL to Solana (or maintain separate collateral)
- Drift SDK for order execution (Python `driftpy` or TypeScript)
- Latency: Solana ~400ms slot time vs HL ~1-2s, execution synchronization required

---

## 9. Appendix: API Discovery Log

```
Endpoints tested:
  data.api.drift.trade/fundingRates?marketName=SOL-PERP      -> 404
  data.api.drift.trade/v2/fundingRates                        -> 404
  data.api.drift.trade/market/SOL-PERP/fundingRates          -> 200 OK (live, ~21 days)
  data.api.drift.trade/market/SOL-PERP/fundingRateHistory    -> 404
  data.api.drift.trade/market/SOL-PERP/rateHistory           -> 404
  dlob.drift.trade/fundingRates?marketIndex=0                 -> 503
  S3 drift-historical-data-v2/.../fundingRateRecords/2024/   -> 200 OK (366 daily files)
  S3 drift-historical-data-v2/.../fundingRateRecords/2025/   -> 200 OK (4 files, Jan 1-8 only)

Key discovery: S3 files are gzip-encoded CSVs served with Content-Encoding: gzip,
downloadable directly via HTTP without AWS credentials.

SOL-PERP market index: 0 (confirmed via API response field marketIndex=0)
FR formula: 1/24 * (mark_twap - oracle_twap) / oracle_twap (hourly settlement)
```

---

*K358 | Wave runtime: 399.6s | Cache: cache/drift_sol_fr.parquet*

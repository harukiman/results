# Wave K319: K208 actual sources CLEAR — K280 production unaffected

**Generated**: 2026-05-25 14:32 JST
**Status**: ★ K208 PRODUCTION DATA CLEAN — K280 NOT DEGRADED ★

## Verification

Tested K208's actual data sources (per `scripts/k280_live_fetch.py`):
- `cache/bybit_fr_<SYM>USDT_730d.parquet` (column `funding_rate`, indexed by `timestamp`)
- `cache/k163_hl/hl_fr_<SYM>.parquet`

For the K208 candidate universe (ARB, ADA, DOGE, SOL, AAVE, BNB, BTC, ETH, AVAX):

| Symbol | Bybit rows | Bybit 30d zero% | Last Bybit ts | HL 30d zero% |
|---|---:|---:|---|---:|
| ARB  | 2190 | **0.0%** | 2026-05-24 08:00 | 0.0% |
| ADA  | 2190 | **0.0%** | 2026-05-23 08:00 | 0.0% |
| DOGE | 2190 | **0.0%** | 2026-05-24 08:00 | 0.0% |
| SOL  | 2190 | **0.0%** | 2026-05-24 08:00 | 0.0% |
| AAVE | 2190 | **0.0%** | 2026-05-24 16:00 | 0.0% |
| BNB  | 2190 | **0.0%** | 2026-05-23 08:00 | 0.0% |
| BTC  | 2190 | **0.0%** | 2026-05-23 08:00 | 0.0% |
| ETH  | 2190 | **0.0%** | 2026-05-23 08:00 | 0.0% |
| AVAX | 2190 | **0.0%** | 2026-05-24 08:00 | 0.0% |

All clean. No silent-zero bug in K208's actual data path.

(2190 rows = 730d × 3 FR events/day = correct Bybit 8h cadence)

## Conclusion

- **K208 production signal is HEALTHY**
- **K280 live Sharpe is NOT overstated** (K317 claim retracted)
- **K302a v6.12 deployment plan is UNAFFECTED**
- HTML banner needs NO correction beyond what K310 already did

## What was actually broken (K316/K317 finding still valid)

`cache/alt_exchange_fr_daily.parquet` (K270 dYdX v4 source):
- ARB 14/14 days zero, ADA 9/14, DOGE 2/14 in last 14 days
- Bug is real but **affects K270 (deprecated satellite)** only
- K270 not in current K302a v6.12 production allocation
- Fix is **non-urgent**; tracked as K321 (was K318 in K317 plan)

## Cross-references

- K316: first symptom (60% zeros in alt_exchange_fr_daily) — symptom real
- K317: bug confirmation but WRONG production attribution to K208/K280
- K318: corrected attribution to K270 (deprecated)
- K319 (this wave): K208 actual sources verified CLEAN

## Discovery chain quality assessment

Pattern recognition: ✓ K312 → K316 → K317 found the zero-density bug correctly
Impact attribution: ✗ K317 mis-mapped strategy to data source
Self-correction: ✓ K318 caught the error, K319 verified the right path

**Net lesson**: keep the discovery chain but separate "pattern detection" from
"production impact analysis." Always verify strategy ↔ data source mapping via
`grep parquet scripts/<strategy>.py` before claiming production impact.

## Action items

- ✓ K319 closed: K208/K280 clean
- → K321 (low priority): patch K270 aggregator silent-zero (deferred, K270 deprecated)
- → Optional K322: enhance scripts/audit_cache_integrity.py with:
   * `zero_fraction_recent_30d` per parquet
   * `STALE_OR_INTERMITTENT` status when >30%
   * `consumer_strategies` field (which scripts read this parquet) for future impact analysis

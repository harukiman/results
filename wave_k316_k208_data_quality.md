# Wave K316: K208 source data quality audit — zero-value pattern

**Generated**: 2026-05-25 14:25 JST
**Source**: `cache/alt_exchange_fr_daily.parquet` (K208 production input)
**Trigger**: K312 cache audit passed sanity but tail values mostly zero — needed deeper look

## Key findings

### Data shape
- 731 rows × 30 symbol columns (date index, single exchange?)
- Range: 2024-05-25 → 2026-05-25
- Symbols: AAVE, ADA, APT, ARB, ATOM, AVAX, AXS, BLUR, BONK, CRV, DOGE, DOT, ENA, INJ, JUP, LDO, NEAR, OP, PEPE, PYTH, SEI, SOL, SUI, TAO, TIA, UNI, WIF, WLD, XRP, BNB

### Zero-value spread (alarming trajectory)
| Date | % cols == 0 |
|---|---:|
| 2026-05-11 | 13% |
| 2026-05-13 | **53%** ← cross-over |
| 2026-05-25 | **60%** ← today |

**First date with >50% zeros: 2025-02-21** (3+ months ago).

### Bottom 10 symbols by nonzero count (over 731-day history)
| Symbol | Nonzero days | Coverage % |
|---|---:|---:|
| ARB  | 181 | 25% |
| TIA  | 261 | 36% |
| WIF  | 378 | 52% |
| PEPE | 413 | 57% |
| CRV  | 414 | 57% |
| SUI  | 424 | 58% |
| NEAR | 429 | 59% |
| ADA  | 438 | 60% |
| DOT  | 459 | 63% |
| WLD  | 464 | 64% |

### Recency check
All 30 symbols have at least one nonzero value in 2026-05 → data isn't dead, just intermittent.

## Interpretation

Two competing hypotheses:

**H1 — Genuine zero-FR**: Perpetual contracts with low volume can have FR = 0 (no premium/discount). If true, K208 signal is correctly null and the strategy correctly skips. Not a bug.

**H2 — Fetch failure**: The aggregator silently writes 0 when source API returns empty/None. Then K208 sees fake "zero FR" and may falsely classify symbols as "no carry opportunity" when in reality data is missing.

Can't distinguish from inside this parquet alone. Need cross-check against:
- Original source CSVs / API logs (where did this come from?)
- Compare with `cache/funding_<SYMBOL>_29d.parquet` (separately maintained, per-symbol)

## Risk to K208 production

If H2 is true:
- K208 signal is degraded for ~60% of today's universe
- K208 backtest Sharpe likely overstated (used full data, live runs into zeros)
- K280 main 80% allocation includes K208 → 30-40% potential signal degradation

## Recommendations

- **K317** (proposed): cross-check `cache/funding_<SYMBOL>_29d.parquet` vs `alt_exchange_fr_daily.parquet` for overlapping date+symbol. If 29d files show nonzero but daily aggregator shows 0 → H2 confirmed → fetch bug.
- **K318** (proposed, after K317): if H2 confirmed, patch the upstream fetch to distinguish None/missing from 0.0 and re-aggregate.
- Until resolved: K208's contribution to K280 should be treated as **point estimate with high data-quality risk**, not a robust signal.

## Status

DATA QUALITY CONCERN flagged, no decisions changed yet. K208 remains in production pending K317 cross-check.

## Cross-references

- K293 (post-fix scaffold audit) — did not catch this because the symptom emerged after K293
- K310 (HTML reconciliation) — focus was on daemon state, not data
- K312 (cache integrity audit) — passed sanity (|values| < 1.0) but didn't measure zero-density trajectory

**K312 follow-up**: enhance `scripts/audit_cache_integrity.py` to add `zero_fraction_recent_30d` per parquet. Add `STALE_OR_INTERMITTENT` status when >30%.

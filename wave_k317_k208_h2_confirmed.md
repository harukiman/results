# Wave K317: K208 H2 CONFIRMED — silent fetch-failure bug in daily aggregator

**Generated**: 2026-05-25 14:27 JST
**Status**: ★★★ PRODUCTION BUG IDENTIFIED ★★★

## Test design

For each symbol in `cache/alt_exchange_fr_daily.parquet`, compare last 14 days against
`cache/funding_<SYMBOL>USDT_29d.parquet` (separately maintained per-symbol fetch).

If daily aggregator shows 0 on date D, but per-symbol 29d file shows nonzero on date D
→ H2 (silent fetch failure) confirmed, not H1 (genuine zero-FR).

## Results

| Symbol | Days daily=0 (last 14d) | Days 29d=0 (last 14d) | Days 29d nonzero when daily=0 |
|---|---:|---:|---:|
| **ARB**  | 14 | 0 | **14 (100%)** |
| **ADA**  |  9 | 0 | **9 (100%)** |
| **DOGE** |  2 | 0 | **2 (100%)** |
| SOL  | 0 | 0 | 0 |
| AAVE | 0 | 0 | 0 |
| TIA, WIF, CRV, LINK | — | — | NO 29D FILE (test inconclusive) |

## Conclusion: H2 CONFIRMED

The daily aggregator (`cache/alt_exchange_fr_daily.parquet`) is **silently writing 0**
when the source API returns empty/None, while the parallel per-symbol fetcher
(`cache/funding_<SYMBOL>_29d.parquet`) correctly stores real values for the same dates.

K208 production signal has been degraded for affected symbols (at least ARB, ADA, DOGE).

## Magnitude

ARB last 14d: 0/14 nonzero in daily aggregator (100% failure rate)
This is the most extreme case. ARB's K208 contribution has been ZERO for at least 2 weeks
even though FR carry opportunity existed on every day.

## Root cause hypothesis

Either:
1. The daily aggregator's source API endpoint returns null for some symbols and the
   aggregator code falls back to `value = 0.0` instead of `value = NaN` or skip
2. A scheduled fetch failed silently and a default-zero row was written
3. Symbol mapping bug: aggregator uses an outdated venue+symbol mapping

The per-symbol 29d fetcher uses a different code path that handles missing gracefully.

## Impact on K280 production

K280 = K198 + K208 + K276b_top20.
K208 weight in K280 ≈ 33%.
If K208 ARB/ADA/DOGE signals are dead → K280 effective allocation reduced.
Live K280 Sh (currently claimed in HTML) may be **overstated by 10-20%** because
backtest used historical (pre-bug) data while live uses degraded post-bug data.

## Immediate next steps

### K318 (URGENT): Patch upstream fetch
- Locate the script that writes `cache/alt_exchange_fr_daily.parquet`
  (likely `scripts/k280_live_fetch.py` or an older `scripts/alt_exchange_*.py`)
- Add NaN/skip handling for null returns instead of writing 0
- Re-aggregate from `cache/funding_<SYMBOL>_29d.parquet` files where available
- Backfill ARB/ADA/DOGE history

### K319 (after K318): K280 backtest re-run with corrected data
- Compare K280 Sh before/after correction
- If material delta (>10%), revise K302a v6.12 deployment plan

### K320 (also urgent): HTML banner correction
- Add warning badge: "K280 signal under data-quality investigation (K317)"
- Reduce "98.7% K287d retention" claim to provisional pending K319

## Cross-references

- K316 first flagged the symptom (60% zeros today)
- K312 missed it because sanity check only verified |value| < threshold, not zero-density
- K293 was a "post-fix scaffold audit" but ran before this symptom emerged

## Severity: HIGH

This is the kind of silent production degradation that motivated the
`feedback_agent_groundtruth_verify` rule. The K312 cache audit "passed" because we
checked the wrong thing. The discovery chain K312 → K316 → K317 shows that even
ground-truth verification needs the right invariants.

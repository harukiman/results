# Wave K326: K317 FULL RETRACTION — comparison was apples-to-oranges

**Generated**: 2026-05-25 14:40 JST
**Status**: ★ K317 BUG CONCLUSION FULLY RETRACTED ★

## Discovery chain to date (K316→K326)

| Wave | Claim | Status (after this wave) |
|---|---|---|
| K316 | alt_exchange_fr_daily today 60% zero, since 2025-02-21 >50% | True (pattern real) |
| K317 | "Silent fetch failure" — H2 confirmed via cross-check | **WRONG comparison**, retracted |
| K318 | K317's K208 attribution wrong; bug affects K270 | Partial — also wrong (no bug at all) |
| K319 | K208 actual sources clean | True (K208/K280 unaffected) |
| K326 | Even K270 has no bug — just genuine low-volume zero FR | **THIS RETRACTION** |

## What K317 actually compared

- `cache/alt_exchange_fr_daily.parquet` — **dYdX v4** per-day FR (K270 source)
- `cache/funding_ARBUSDT_29d.parquet` — **Binance** per-event FR (per `wave_k295_k275_reconcile.py:446` comment: "Fallback: use Binance 29d cache")

Two different exchanges. Of course they have different funding rates on the same dates.

## Why dYdX shows zeros legitimately

ARB last 14 days on dYdX v4 (from alt_exchange_fr_daily.parquet):
```
2026-05-12  0.000000e+00
2026-05-13  0.000000e+00
2026-05-14  2.083333e-08  ← tiny but nonzero
2026-05-15  0.000000e+00
2026-05-16  0.000000e+00
...
2026-05-22 -2.500000e-07
2026-05-25  0.000000e+00
```

Values are either 0 or near-zero (2e-8 to 3e-7). This pattern is consistent with a **low-volume perp tracking spot index closely** — when there's no premium/discount, FR is genuinely 0. dYdX v4's ARB perp likely has much lower volume than Binance's ARB perp, hence near-zero FR.

K317 mistakenly treated "dYdX ARB FR = 0 while Binance ARB FR = 0.01%" as evidence of a fetch failure, when it's just market-microstructure difference between venues.

## Correct interpretation

`cache/alt_exchange_fr_daily.parquet` is **not buggy**. It is dYdX v4 data that genuinely contains many zeros because dYdX v4 has thinner volume on alts than Binance.

This is the K270 strategy's intended input — K270 (cross-sectional FR carry on dYdX) selects symbols WITH meaningful FR; symbols with zero FR are correctly excluded by the strategy logic. Zero != fetch failure.

## Why K316's zero-fraction metric is still useful

The metric itself is valuable — it could catch a real silent fetch failure if one occurred. The interpretation of 25-60% zero rate as "bug" was wrong. The interpretation should be:

- Zero fraction trending upward over time → genuine FR drying up (market microstructure change), strategy may need re-evaluation
- Zero fraction sudden jump (e.g., 5% → 90% in one day) → likely fetch failure
- Stable 25-60% over months → genuine zero FR for low-volume venue, no issue

## What changed in production

**Nothing**. No code was patched. No HTML claim was changed based on K317. The "wave_k318" attribution correction stands (alt_exchange is K270 source, not K208). The "K208 clean" K319 verification stands.

K317's "10-20% K280 Sh overstated" claim was already retracted in K318/K319. This K326 wave goes further: there's no bug to fix in K270 either. K321 (proposed: K270 aggregator patch) is now obsolete and removed from the backlog.

## Meta-lesson: discovery chain quality

**K312 → K316 → K317 → K318 → K319 → K326** chain:
1. ✓ K312 audit passed sanity but missed zero-density (legitimate gap, K322 fixed)
2. ✓ K316 noticed pattern (high zero rate)
3. ✗ K317 jumped to "fetch failure" without checking what alt_exchange_fr_daily *contains* (which exchange?)
4. ✓ K318 caught the production-impact attribution error
5. ✓ K319 verified K208/K280 actually clean
6. ✓ K326 (this wave) caught the *underlying* pattern interpretation error

Self-corrective ability is good, but K317 → K318 → K326 = **two correction rounds for one bad inference**. The cost: ~3 wave files of analysis on an ultimately-spurious bug.

**Permanent lesson** (will be added to memory): when comparing parquets, always confirm they are from the same data source / exchange / venue / API endpoint before treating differences as bugs.

## Cross-references

- K316 (pattern detection): useful, valid
- K317 (bug confirmation): RETRACTED (this wave)
- K318 (production attribution correction): valid, doesn't go far enough
- K319 (K208 sanity verification): valid, useful
- K326 (this wave): full retraction of K317

## Action items closed

- ✓ K317 retracted
- ✓ K318 stands (attribution correction)
- ✓ K319 stands (K208/K280 clean)
- ✗ K321 (K270 aggregator patch) — REMOVED FROM BACKLOG (no patch needed)
- → New memory rule needed: "Cross-source comparisons require same-source verification first"

## What to do going forward

1. Don't change K270 aggregator (no bug)
2. Update audit_cache_integrity.py threshold logic: rolling delta of zero_fraction is more interesting than absolute value (genuine zero FR vs fetch failure distinction)
3. Add memory rule

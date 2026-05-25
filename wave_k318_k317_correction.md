# Wave K318: K317 misattribution correction — bug affects K270 (deprecated), not K208

**Generated**: 2026-05-25 14:30 JST
**Status**: ★ K317 ATTRIBUTION ERROR CORRECTED ★

## What K317 claimed (incorrect)

K317 reported `cache/alt_exchange_fr_daily.parquet` zero-density bug affects K208 production,
implying K280 main signal degradation.

## Ground truth (this wave)

`cache/alt_exchange_fr_daily.parquet` is written by `wave_k270_alt_exchange_fr.py` (line 86, 542).
It is **dYdX v4 daily FR data** — the source for the **K270 strategy**, not K208.

K280's K208 component reads from:
- `cache/bybit_fr_<SYMBOL>USDT_<tag>.parquet` (Bybit per-symbol)
- `cache/k163_hl/hl_fr_<SYMBOL>.parquet` (HyperLiquid per-symbol)
(verified via `grep parquet scripts/k280_live_fetch.py` lines 129–262)

`scripts/k280_live_fetch.py` does NOT read `alt_exchange_fr_daily.parquet`.

## So what is the actual impact?

**Bug remains real**: `cache/alt_exchange_fr_daily.parquet` does have the silent-zero issue
documented in K316/K317. ARB/ADA/DOGE 14d nonzero-coverage degraded.

**But the strategy impacted is K270 (dYdX v4 cross-sectional)**, which is:
- A **DEPRECATED satellite component** (K287d satellite was K289 daemon → K302a v6.12 switch)
- Currently **NOT in any active production allocation** (K302a v6.12 = K280 main 80% + K297 RWA 20%; K270 not included)

→ Live production K302a v6.12 is **NOT affected** by this bug.

## K208 verification status

K208 component (Bybit + HL per-symbol) is **NOT confirmed bug-free** — we just haven't tested it.
Bybit and HL per-symbol parquets need their own zero-density audit before declaring K280 healthy.

## Revised plan

**K319** (revised): Audit K208's actual data sources:
- `cache/bybit_fr_<SYM>USDT_<tag>.parquet` (last 30d zero-density per symbol)
- `cache/k163_hl/hl_fr_<SYM>.parquet` (same)
If these are clean → K280 production is fine.
If degraded → K280 truly affected and HTML correction needed.

**K320** (revised): Only after K319 results, decide HTML banner action.

**K321** (existing K318 scope but reframed): Fix the K270 aggregator silent-zero bug
- Even though K270 is deprecated, the bug should be fixed so future K270-revival waves work
- Lower priority than K319

## Lessons

1. **Strategy → data source mapping must be explicit** before claiming production impact.
   K317 conflated "alt_exchange" naming with "K208 component" without verification.
2. **K312 cache audit registry needs strategy attribution column**: which strategies depend on
   each parquet. Then a flag on parquet X auto-shows which strategies are affected.
3. **Discovery chain accuracy**: K312 → K316 → K317 was great pattern-finding but K317
   conclusion was wrong on impact. The pattern (silent zeros) is real; the production attribution wasn't.

## Cross-references
- K316: original symptom (60% zeros)
- K317: bug confirmation + INCORRECT production attribution
- This wave (K318): attribution correction

## What I'm NOT doing in this wave
- Not patching the K270 aggregator (lower priority since K270 deprecated)
- Not updating HTML banner (K280 may or may not be affected; awaiting K319)
- Not panicking about K280 live Sh (the K317 "10-20% overstated" claim is premature)

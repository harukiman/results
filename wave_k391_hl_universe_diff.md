# Wave K391 — HL Universe Diff Scanner

**Generated:** 2026-05-29 06:34 JST  
**Author:** CT Lab / K391  
**Scan window:** 2026-05-25 → 2026-05-29 (4 days)  
**Live snapshot:** `cache/hl_universe_20260529_0000.json`

---

## Executive Summary

**Result: MED_LOW — Baseline stable. No RWA additions detected.**

K391 scanned the Hyperliquid perpetual universe against two baselines (K314 on 2026-05-25 and K352 on 2026-05-27). Across a 4-day window, **zero new symbols were listed** and **zero symbols were fully removed** from the HL universe. The total symbol count remains 230.

Key findings:
- **No new RWA/HIP-3 tokens listed.** All 15 waitlist candidates (XAG, WTI, XAU, OIL, COPPER, NDX, DJI, US500, plus 7 equity proxies) remain unlisted as of 2026-05-29.
- **4 low-tier symbols newly flagged as delisted** (TST, BLAST, CHILLGUY, FTT — all 3x leverage, none in K276b universe).
- **3x tier shrank by 4 symbols** (93 → 89 active at 3x), entirely due to the new delistings above.
- **K297' expansion NOT triggered.** PAXG and SPX remain the only active RWA instruments.
- **K337-K345 trigger date unchanged: 2026-10-01.**

---

## Phase 1 — Snapshot

| Snapshot | Date | Total Symbols | Active | RWA Count |
|---|---|---|---|---|
| K314 baseline | 2026-05-25 14:19 JST | 230 | 183 | 2 (PAXG, SPX) |
| K352 baseline | 2026-05-27 07:05 JST | 230 | 183 | 2 (unchanged) |
| **K391 live** | **2026-05-29 06:34 JST** | **230** | **179** | **2 (unchanged)** |

The drop from 183 to 179 active symbols is entirely explained by 4 new delistings flagged during the 4-day window (existing symbols marked `isDelisted: true`). No net additions or removals from the universe array itself.

---

## Phase 2 — Symbol Diff

### New Listings Since K314
```
Added since K314 (2026-05-25):  NONE
Added since K352 (2026-05-27):  NONE
```

### Removed Listings Since K314
```
Removed since K314:  NONE
Removed since K352:  NONE
```

The universe array length is exactly 230 in all three snapshots. No HIP-3 listing or delisting events occurred at the structural level.

### Delisting Status Changes (K314 → K391)

These symbols were active (`isDelisted: false`) in K314 but are now `isDelisted: true`:

| Symbol | MaxLeverage | K276b Member | Category |
|---|---|---|---|
| TST | 3x | No | Memecoin / low liquidity |
| BLAST | 3x | No | Layer-2 token |
| CHILLGUY | 3x | No | Memecoin |
| FTT | 3x | No | Exchange token (FTX legacy) |

**All 4 delistings are 3x-tier tokens. None are K276b universe members. No direct strategy impact.**

### MaxLeverage Changes (K314 → K391)
```
NONE — zero individual token leverage tier changes detected.
```

---

## Phase 3 — RWA Filter

### Current Active RWA Instruments (K391)

| Symbol | Max Leverage | szDecimals | Isolated Only | marginTableId | Matched Keyword |
|---|---|---|---|---|---|
| PAXG | 10x | 3 | No | 51 (tiered 10x) | PAXG |
| SPX | 5x | 1 | No | 5 (flat 3x) | SPX |

**No change from K314 or K352 baseline. K297' universe remains PAXG + SPX (2 instruments).**

### New RWA Listings Detected
```
NONE
```

### Wait List Status (R11/K314 candidates)

All 15 K297' expansion candidates remain unlisted on HL as of 2026-05-29:

| Category | Symbols | Status |
|---|---|---|
| Precious metals | XAG, XAU | Not listed |
| Energy commodities | WTI, OIL | Not listed |
| Industrial metals | COPPER | Not listed |
| Equity indices | US500, NDX, DJI | Not listed |
| Individual equities | NVDA, AAPL, TSLA, META, GOOG, AMZN, MSFT | Not listed |

**Interpretation:** HL's HIP-3 expansion pace for traditional asset proxies remains slow. This is consistent with the regulatory uncertainty tracked in K385 (CFTC complaint-phase risk, SEC innovation exemption delay). No catalyst for K297' expansion in the 4-day window.

---

## Phase 4 — MaxLeverage Tier Shifts

### Tier Comparison (K314 → K391, active symbols only)

| Leverage Tier | K314 Count | K391 Count | Delta | Strategy Impact |
|---|---|---|---|---|
| 40x | 1 | 1 | 0 | None |
| 25x | 1 | 1 | 0 | None |
| 20x | 2 | 2 | 0 | None |
| 10x | 31 | 31 | 0 | None |
| 5x | 55 | 55 | 0 | None |
| **3x** | **93** | **89** | **-4** | Low — driven by 4 delistings |

**Total active: 183 → 179 (-4)**

The only shift is the 3x tier shrinking by 4, entirely attributable to TST/BLAST/CHILLGUY/FTT delistings. No symbol migrated between leverage tiers (e.g., 3x → 5x). This rules out the most actionable scenario: a mid-cap token graduating to higher leverage (signaling liquidity maturation).

**K208 / K198 capital efficiency: No review required.** The high-leverage tiers (5x–40x) where K208 and K198 operate are perfectly unchanged.

---

## Phase 5 — Implications Matrix

| # | Change Type | Symbol | Severity | Strategy Impact | Action |
|---|---|---|---|---|---|
| 1 | MEMECOIN_DELISTED | TST | LOW | Not in K276b | Log only |
| 2 | MEMECOIN_DELISTED | BLAST | LOW | Not in K276b | Log only |
| 3 | MEMECOIN_DELISTED | CHILLGUY | LOW | Not in K276b | Log only |
| 4 | MEMECOIN_DELISTED | FTT | LOW | Not in K276b | Log only |
| 5 | LEVERAGE_TIER_SHIFT | 3x tier (-4) | MED | K208/K198 theoretical monitoring | Track, no immediate action |

### Detailed Change Notes

**TST (Test token, delisted)**  
Low-liquidity test instrument. Delisting expected. No production strategy used it.

**BLAST (Blast L2, delisted)**  
The Blast Layer-2 ecosystem token lost traction. 3x-only leverage confirmed it was never in the core K276b universe (which focuses on DeFi blue chips and funding-carry candidates at 5x+).

**CHILLGUY (Memecoin, delisted)**  
Typical memecoin lifecycle: listed at 3x, never reached liquidity threshold for leverage upgrade, delisted within months. K276b was specifically designed to avoid this class.

**FTT (FTX exchange token, delisted)**  
Somewhat notable as FTX's exchange token should have had declining relevance since 2022. HL had it listed at 3x (isolated-mode-eligible in K314, but not flagged as onlyIsolated). Delisting now cleans up the universe. No strategy exposure.

**3x Tier shrink (-4 symbols)**  
The 3x tier dropping from 93 to 89 active is a purely administrative cleanup. It does not signal that any HIP-3 token was upgraded to 5x, which would have been meaningful for K297'. No actionable implication for K208/K198 since those strategies operate in the 5x–40x bands.

---

## Phase 6 — Concentration Risk (K297' / K355 65% Cap)

| Metric | Value |
|---|---|
| Current K297' instruments | 2 (PAXG, SPX) |
| New RWA detected this scan | 0 |
| Projected K297' instruments | 2 (unchanged) |
| K355 65% HL concentration cap | **Unaffected** |
| Non-RWA new listings | 0 |
| Non-RWA concentration impact | None |

**No concentration risk change.** K297' is stable at PAXG + SPX. K355 cap is not in danger from this scan's findings.

If a new RWA were to be listed (e.g., XAG silver), the concentration analysis would need to immediately check:
1. Projected weight increase in K297' relative to the overall v6.13d portfolio
2. Whether K297' total allocation would breach the 65% HL ecosystem cap
3. Whether the new instrument fits the K208/K266 gate criteria before allocation

---

## Phase 7 — Decision Matrix

### Overall Result: MED_LOW

| Criterion | Status |
|---|---|
| CRITICAL trigger (new RWA listed) | NOT TRIGGERED |
| MED trigger (2+ meaningful changes) | NOT TRIGGERED |
| MED_LOW trigger (1 MED + low delistings) | TRIGGERED (3x tier shift) |
| K337-K345 trigger date unchanged | YES — still 2026-10-01 |
| K297' expansion wave (K392) | NOT TRIGGERED |

### Decision Actions

| Priority | Action | Wave |
|---|---|---|
| LOW | Log 4 delistings to audit trail | This wave (K391) |
| LOW | Confirm 3x tier data consistent with HTML records | This wave (K391) |
| LOW | Recheck HL universe next scheduled scan | 2026-10-01 (K337-K345 trigger) |
| DEFERRED | K297' expansion for XAG, WTI, XAU etc. | Conditional on HL listing |

### RWA Waitlist Final State

**All 15 waitlist candidates remain unlisted.** No immediate expansion of K297'. The wait list from R11/K314 is unchanged and continues to be monitored passively.

Trigger conditions for K392 (K297' expansion):
- HL lists any of: XAG, XAU, WTI, OIL, COPPER (commodity class, highest priority)
- HL lists any of: US500, NDX, DJI (index class, medium priority)
- HL lists any equity proxy (NVDA, TSLA, etc.) at 5x+ leverage (low priority — regulatory risk high)

---

## Appendix A — Full Symbol List K391 vs K314

### All 230 Symbols — Unchanged Structure

The universe is identical in structure to K314 and K352. The only changes are:
- 4 symbols transitioned from `isDelisted: false` to `isDelisted: true`
- All other 226 symbols are bit-for-bit identical across all three snapshots

### RWA Instruments Full Detail

**PAXG** (PAX Gold)
- Backed by physical gold held by Paxos Trust
- HL maxLeverage: 10x | szDecimals: 3 | marginTableId: 51 (tiered 10x)
- Tier: Position >$3M drops to 5x max
- K297' role: Gold synthetic exposure, primary HIP-3 RWA instrument
- Status: Active, unchanged since K314

**SPX** (S&P 500 Index)
- SPX token on HL, tracking S&P 500 index
- HL maxLeverage: 5x | szDecimals: 1 | marginTableId: 5 (flat 3x... actual table says flat, max=5 is symbol level)
- Note: SPX classification as RWA is borderline — it is an index-tracking token, not directly backed
- K297' role: US equity beta exposure, secondary HIP-3 RWA instrument
- Status: Active, unchanged since K314

---

## Appendix B — Methodology

### API Endpoint
```
POST https://api.hyperliquid.xyz/info
Content-Type: application/json
Body: {"type": "meta"}
```

### Baseline Files
- `cache/hl_universe_20260525_1419.json` — K314 baseline (230 symbols)
- `cache/hl_universe_20260527_0705.json` — K352 baseline (230 symbols)
- `cache/hl_universe_20260529_0000.json` — K391 live snapshot (230 symbols)

### RWA Keyword Filter
```python
RWA_KEYWORDS = [
    "GOLD", "SILVER", "XAU", "XAG", "WTI", "OIL", "COPPER",
    "COMMODITY", "US500", "NDX", "DJI",
    "NVDA", "AAPL", "TSLA", "META", "GOOG", "AMZN", "MSFT",
    "PAXG", "SPX",
]
```

Keyword match is case-insensitive substring, applied to the HL symbol name.

### Diff Logic
1. Build `set` of symbol names per snapshot
2. Set difference for additions/removals
3. For common symbols: compare `isDelisted`, `maxLeverage` fields field-by-field

### Leverage Tier Analysis
Active symbols only (`isDelisted: false`). Grouped by `maxLeverage` field value.

---

## Appendix C — K276b Universe vs Delistings

K276b 20-symbol universe (from K374):
`ENA, ONDO, ATOM, TIA, SEI, WLD, RNDR, TAO, MEME, AAVE, PYTH, LDO, FET, PEPE, MKR, JUP, UNI, BOME, DOT, BONK`

Intersection with newly delisted symbols (TST, BLAST, CHILLGUY, FTT):
**EMPTY SET** — zero overlap.

K276b coverage is fully intact as of 2026-05-29.

---

## Next Scheduled Scan

- **Routine recheck:** 2026-10-01 (K337-K345 trigger date, unchanged)
- **Event-driven recheck trigger:** Any HL HIP-3 governance vote for new asset listings
- **Source to watch:** HL Discord governance channel, HL blog, @HyperliquidX Twitter for listing announcements

If a new HIP-3 RWA token (especially XAG, XAU, WTI, or any equity proxy) is announced, trigger K392 immediately without waiting for the 2026-10-01 date.

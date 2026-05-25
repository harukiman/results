# Wave K314: HL Universe snapshot — RWA expansion baseline

**Generated**: 2026-05-25 14:19 JST
**Source**: `https://api.hyperliquid.xyz/info` `{type:"meta"}`
**Snapshot**: `cache/hl_universe_20260525_1419.json` (gitignored, local-only)

## Why

After R11 finding #1 (XAG silver, WTI crude OI $100M+/$200M+ via Ripple Prime), establish a HL universe baseline so future K297 RWA expansion candidates can be tracked diff-style.

## Findings

### Active universe: 183 perps (230 raw, 47 delisted)

### Leverage tier distribution

| maxLeverage | Symbols | % | Notes |
|---:|---:|---:|---|
|  3x | 93 | 51% | K276 long-tail territory |
|  5x | 55 | 30% | Mid-cap alts |
| 10x | 31 | 17% | Major alts **+ RWA (SPX, PAXG)** |
| 20x |  2 |  1% | Top liquidity |
| 25x |  1 |  0.5% | Likely ETH |
| 40x |  1 |  0.5% | Likely BTC |

### RWA tokens currently listed: 2 of target ~8

| Token | maxLev | szDecimals | Status |
|---|---:|---:|---|
| **PAXG** | 10x | 3 | LIVE (K297 component) |
| **SPX** | 10x | 1 | LIVE (K297 component) |
| XAG (silver) | — | — | NOT on HL (per R11: Ripple Prime only) |
| XAU (gold) | — | — | NOT on HL |
| WTI (crude) | — | — | NOT on HL (per R11) |
| OIL | — | — | NOT on HL |
| US500 | — | — | NOT on HL |
| TSLA/AAPL/NVDA/META/GOOG | — | — | NOT on HL |

## K297 Universe Expansion Decision

**Status**: Expansion blocked — HL has not yet added the R11 candidates via HIP-3.

**Trigger for K297 expansion**: When HL announces or lists XAG/XAU/WTI as HIP-3 perpetuals.

**Monitoring path**: Rerun this snapshot daily (or weekly), diff against `cache/hl_universe_20260525_1419.json`, alert on new RWA-like names.

## Sample 3x leverage tokens (K276 long-tail relevant)

GMX, SNX, YGG, BANANA, TRB, FTT, ARK, BIGTIME, KAS, BLUR, BSV, MINA, POLYX, GAS, MEME, ORDI, SUSHI, GMT, SUPER, kLUNC, RSR, GALA, ACE, CAKE, PEOPLE, XAI, MANTA, UMA, ALT, ZETA, ...

Compare to **K276b_top20** (current production K265 component): drops include ARK, BLUR, STRK, ARB, SUSHI (which appear in 3x bucket here — consistent with K276 noise removal logic targeting low-leverage low-liquidity names).

## Cross-reference K313 finding

K313 K208 carry candidate `SUPER` (67.2 bps spread BYBIT-BIN) appears in HL 3x bucket → low liquidity → high spread plausible but high execution risk. Flag as "tradeable but tight size limit".

## Next steps

1. K297 expansion = pending HL listings (no action without HL roadmap signal)
2. Cron `verify_deployment_status.py` daily; diff cache snapshots
3. K276c (top10) sensitivity test if any K276b_top20 member newly added/removed from HL universe

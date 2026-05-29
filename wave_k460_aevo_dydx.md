# Wave K460: Aevo + dYdX v4 Venue Integration Scaffold

**Date:** 2026-05-25  
**v6.20 Progress:** 6/7 waves complete  
**Daemons:** 24 (23rd = Aevo, 24th = dYdX v4)

---

## Executive Summary

K460 completes waves 5 and 6 of the K454 v6.20 7-wave plan by scaffolding two new
funding-rate venues: Aevo (4th venue) and dYdX v4 (5th venue). Both use 1h funding cycles
(vs 8h HL/Bybit/OKX) and support read-only public REST endpoints without API keys.
Full trading integration (Aevo API auth + dYdX Cosmos signing) is scoped post-K460.

After K460: K208 spans 5 venues with cross-venue FR arbitrage opportunity set expanded.

---

## Phase 1: API Research

### Aevo
- **Base URL:** `https://api.aevo.xyz`
- **FR endpoint:** `GET /funding?instrument_name=BTC-PERP`
- **Response:** `{"funding_rate": "0.000008", "next_epoch": "1780070400000000000"}`
- **next_epoch:** nanosecond Unix timestamp
- **Funding period:** 1h (24 settlements/day)
- **Public API:** No auth required for read-only endpoints
- **Symbol format:** `{BASE}-PERP`
- **Annualized:** `FR × 24 × 365 × 100`

### dYdX v4 (Cosmos Chain)
- **Indexer base:** `https://indexer.dydx.trade/v4`
- **All markets:** `GET /v4/perpetualMarkets`
- **Single market:** `GET /v4/perpetualMarkets?ticker=BTC-USD`
- **Historical:** `GET /v4/historicalFunding/BTC-USD?limit=100`
- **Orderbook:** `GET /v4/orderbooks/perpetualMarket/BTC-USD`
- **FR field:** `nextFundingRate` (per-1h fractional string)
- **Timestamps:** ISO 8601 UTC (Cosmos chain time, e.g. `"2026-05-25T12:00:00.000Z"`)
- **Public API:** No auth required for Indexer REST
- **Symbol format:** `{BASE}-USD`
- **Chain:** Cosmos (NOT EVM) — trading requires `MsgPlaceOrder` protobuf
- **Annualized:** `FR × 24 × 365 × 100`

---

## New Files

| File | Type | Description |
|------|------|-------------|
| `scripts/aevo_fr_fetcher.py` | NEW | Aevo FR fetcher, 14 K208 symbols, 1h daemon |
| `scripts/dydx_v4_fr_fetcher.py` | NEW | dYdX v4 FR fetcher, 18 K208 symbols, 1h daemon |
| `com.cryptolab.aevo-fr-monitor.plist` | NEW | 23rd daemon plist (1h, gitignored) |
| `com.cryptolab.dydx-v4-fr-monitor.plist` | NEW | 24th daemon plist (1h, gitignored) |
| `data/aevo_dashboard.json` | NEW | Initial Aevo dashboard scaffold |
| `data/dydx_v4_dashboard.json` | NEW | Initial dYdX v4 dashboard scaffold |
| `wave_k460_aevo_dydx.md` | NEW | This file |
| `wave_k460_aevo_dydx.json` | NEW | Machine-readable wave summary |

---

## Updated Files

| File | Change |
|------|--------|
| `scripts/verify_deployment_status.py` | 23rd + 24th daemons added to REGISTRY |
| `scripts/emergency_hl_exit.py` | `close_aevo_positions()` + `close_dydx_positions()` stubs added; `--include-aevo` + `--include-dydx` flags |
| `scripts/depth_aware_allocator.py` | Aevo + dYdX_v4 enabled=True; live API fetch with fallback; FALLBACK_OI_USD extended |
| `data/smart_router_config.json` | Aevo + dYdX_v4 venues added (enabled=true, 1h funding, normalization factor 8) |
| `data/leverage_config.json` | `K280_K208_Aevo: 3.0` + `K280_K208_dYdX: 3.0` caps added |
| `docs/k302a_runbook.md` | §33 added (Aevo + dYdX v4 integration overview) |
| `report.html` | 2 new Live Monitoring rows (23rd + 24th); v6.20 progress badge → 6/7; 24 daemons confirmed |

---

## Key Technical Notes

### Funding Rate Normalization
Aevo and dYdX v4 use 1h cycles; HL/Bybit/OKX use 8h cycles.
Cross-venue comparison requires normalization:
```
Aevo_8h_equiv   = Aevo_1h_FR   × 8
dYdX_8h_equiv   = dYdX_1h_FR   × 8
```
Both fetchers include `annualized_pct = FR × 24 × 365 × 100`.

### dYdX v4 Cosmos Chain
- dYdX v4 is a standalone Cosmos appchain (NOT EVM).
- Indexer REST is public (no auth) — covers all read-only use cases at K460.
- Trading requires Cosmos SDK (`MsgPlaceOrder` protobuf) — NOT compatible with HL/Bybit/OKX EVM signing.
- Python client: https://github.com/dydxprotocol/v4-clients (TODO post-K460).
- Emergency exit: STUB (manual close at dydx.trade until Cosmos signing implemented).

### Emergency Exit Stubs
Both venues added as STUB functions in `emergency_hl_exit.py`:
- `close_aevo_positions()` — dry-run safe, live returns guidance
- `close_dydx_positions()` — dry-run safe, live returns guidance
- Flags: `--include-aevo`, `--include-dydx` (both default OFF)

---

## Verification

```bash
# Run fetchers (read-only, no auth needed)
python3 scripts/aevo_fr_fetcher.py --all
python3 scripts/dydx_v4_fr_fetcher.py --all

# Verify 24 daemons (0 mismatches)
python3 scripts/verify_deployment_status.py

# Check dashboards
python3 scripts/aevo_fr_fetcher.py --dashboard
python3 scripts/dydx_v4_fr_fetcher.py --dashboard
```

---

## v6.20 Progress

| Wave | Content | Status |
|------|---------|--------|
| K456 | OKX (3rd venue) | DONE |
| K457 | BTC+ETH+SOL basket | DONE |
| K458 | Depth allocator | DONE |
| K459 | K457 scaffold | DONE |
| K460 | Aevo (4th) + dYdX v4 (5th) | DONE (this wave) |
| K46x | 7th wave (TBD) | TODO |

**6/7 v6.20 waves complete. 24 daemons confirmed.**

---

*K460 chronicle — 2026-05-25*

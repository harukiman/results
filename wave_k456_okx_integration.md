# K456 OKX Integration Scaffold — Wave Summary

**Date:** 2026-05-30 00:32 JST
**Status:** SCAFFOLD-READY
**Context:** K454 v6.20 Wave 1/7 — K208 venue expansion (3→10), maximize live profit

---

## Executive Summary

K456 adds OKX as the 3rd major trading venue for the K208 funding rate carry strategy.
This is wave 1/7 toward the v6.20 capacity expansion architecture (K454 plan).

Key outcomes:
- **20th daemon** scaffolded: `com.cryptolab.okx-fr-monitor` (8h cycle, 18-symbol FR poll)
- **3rd K208 venue**: HL + Bybit + OKX = triangle arb potential (5bps threshold)
- **0 API keys required** for read-only fetch (public OKX endpoints)
- **Emergency exit** updated: `--include-okx` flag added to `emergency_hl_exit.py`
- **Leverage cap**: `K280_K208_OKX: 3.0` added (conservative, matching HL/Bybit)
- **Runbook §30**: 10 subsections covering API, VIP, keys, emergency, activation, orders

---

## Deliverables

| File | Status | Notes |
|------|--------|-------|
| `scripts/okx_fr_fetcher.py` | NEW | ~300 LOC, 18 symbols, 30d cache, triangle arb helper |
| `com.cryptolab.okx-fr-monitor.plist` | NEW | 20th daemon, StartInterval 28800, gitignored |
| `scripts/verify_deployment_status.py` | UPDATED | 20th daemon DaemonSpec added |
| `data/okx_dashboard.json` | NEW | Initial state (last_poll: null, SCAFFOLD-READY) |
| `scripts/emergency_hl_exit.py` | UPDATED | `--include-okx` flag + `close_okx_positions()` |
| `scripts/leverage_manager.py` | UPDATED | `K280_K208_OKX: 3.0` in DEFAULT_EXCHANGE_CAPS |
| `data/leverage_config.json` | UPDATED | `K280_K208_OKX: 3.0` + `k456_okx_notes` |
| `docs/k302a_runbook.md` | UPDATED | §30 (10 subsections, OKX integration overview) |
| `report.html` | UPDATED | K456 Live Monitoring row + v6.20 1/7 badge + 20 daemons |
| `wave_k456_okx_integration.json` | NEW | Structured wave summary |

---

## OKX API Reference

| Endpoint | Auth | Purpose |
|----------|------|---------|
| `GET /api/v5/public/funding-rate?instId=BTC-USDT-SWAP` | None | Current FR |
| `GET /api/v5/public/funding-rate-history?instId=...` | None | Historical FR |
| `GET /api/v5/market/ticker?instId=BTC-USDT-SWAP` | None | Mark price |
| `GET /api/v5/market/books?instId=...&sz=5` | None | Order book depth |
| `GET /api/v5/account/positions?instType=SWAP` | Yes | Open positions |
| `POST /api/v5/trade/close-position` | Yes | Close position |

**Auth method:** HMAC-SHA256 (similar to Bybit, but with passphrase)

---

## K208 Triangle Arbitrage Logic

```
3 venues: HL, Bybit, OKX
For each symbol:
  max_venue = venue with highest FR → SHORT here
  min_venue = venue with lowest FR  → LONG here
  spread_bps = (max_FR - min_FR) × 10,000
  if spread_bps >= 5.0: OPPORTUNITY

Example (BTC):
  HL FR: +0.01% per 8h
  Bybit FR: +0.008% per 8h
  OKX FR: +0.015% per 8h
  → short OKX (+0.015%), long Bybit (+0.008%)
  → spread = 0.007% = 7bps > 5bps threshold
```

---

## Daemon Configuration

```
Label:         com.cryptolab.okx-fr-monitor
Script:        scripts/okx_fr_fetcher.py --daemon
StartInterval: 28800 (8 hours — matches OKX funding cycle)
RunAtLoad:     false
Log:           logs/okx_fr_monitor.log
Dashboard:     data/okx_dashboard.json
Cache:         cache/okx_fr_BTC_USDT_SWAP.parquet
               cache/okx_fr_ETH_USDT_SWAP.parquet
```

**Activation (when OKX trading ready):**
```bash
cp com.cryptolab.okx-fr-monitor.plist ~/Library/LaunchAgents/
launchctl load ~/Library/LaunchAgents/com.cryptolab.okx-fr-monitor.plist
python3 scripts/verify_deployment_status.py   # expect 0 mismatches, 20 daemons
```

---

## Constraints

- Scaffold only — no actual trading
- OKX API key NOT required for read-only fetch
- K280 production logic NOT modified
- K339 security pattern enforced throughout

---

## v6.20 Progress

| Wave | Content | Status |
|------|---------|--------|
| K456 (1/7) | OKX 3rd venue scaffold | DONE |
| K457 (2/7) | TBD next venue | PENDING |
| … | … | … |
| K??? (7/7) | venues 3→10 complete | TARGET |

*K456 -- OKX integration scaffold (20th daemon, K454 v6.20 wave 1/7) -- 2026-05-30 00:32 JST*

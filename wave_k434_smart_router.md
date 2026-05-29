# Wave K434 — Smart Router Daemon (Cross-Venue HL/Bybit/OKX Routing)

**Date:** 2026-05-29 22:59 JST
**Status:** SCAFFOLD-READY (16th daemon)
**Profit lever:** $175K/yr @ $10M AUM | $877K/yr @ $50M AUM

---

## Summary

Implemented the K208 Smart Router daemon — the single largest identified execution optimization lever ($175K/yr @ $10M per K432 analysis). The router selects the optimal execution venue for each K208 trade by scoring HL, Bybit, and OKX on live FR spread + maker rebate + slippage, subject to concentration caps.

---

## Deliverables

| File | Status | Description |
|------|--------|-------------|
| `scripts/smart_router.py` | NEW | ~330 LOC cross-venue router (stdlib urllib, no new deps) |
| `data/smart_router_config.json` | NEW | Venue settings (tiers, rebates, caps) |
| `com.cryptolab.smart-router.plist` | NEW | launchd plist (gitignored, 1h StartInterval) |
| `scripts/verify_deployment_status.py` | UPDATED | 16th daemon entry added |
| `scripts/k280_live_fetch.py` | UPDATED | K434 call site scaffold + `get_k208_venue()` |
| `docs/k302a_runbook.md` | UPDATED | §24 added (Smart Router playbook) |
| `report.html` | UPDATED | K434 banner badge + daemon row + status card |
| `wave_k434_smart_router.md` | NEW | This file |
| `wave_k434_smart_router.json` | NEW | Machine-readable summary |

---

## Architecture

```
K208 trade signal
    │
    ▼
select_best_venue(symbol, side, size_usd)
    │
    ├── fetch_hl_state()      → POST /info metaAndAssetCtxs (bulk, 1 call)
    ├── fetch_bybit_state()   → GET  /v5/market/tickers?category=linear (bulk, 1 call)
    └── fetch_okx_state()     → GET  /api/v5/public/funding-rate (per symbol)
    │
    ▼
score_venue() = fr_capture + maker_rebate − slippage
    │
    ▼
filter_by_concentration_caps()  (HL≤65%, Bybit≤50%, OKX≤30%)
    │
    ▼
→ {venue, score, fallback_order, details}
```

---

## Scoring Formula

```
net_per_8h = fr_capture + maker_rebate - slippage

fr_capture   = fr × (+1 short / −1 long)
maker_rebate = tier_rebate_bps / 10000
slippage     = (size_usd / depth_usd) × 100 × 0.5 / 10000
```

**Venue tiers:**
- HL GOLD: +0.3 bps rebate, 4.5 bps taker
- Bybit VIP5: +1.0 bps rebate, 3.2 bps taker
- OKX VIP1: +0.5 bps rebate, 4.0 bps taker

Bybit VIP5 has the highest maker rebate (+1.0 bps), so when FR spreads are similar across venues, Bybit tends to score highest.

---

## K339 Compliance

- REPO_ROOT = `Path(__file__).resolve().parent.parent` in smart_router.py
- No new packages (stdlib urllib + json + time only)
- Config at `data/smart_router_config.json` (not hardcoded)

---

## Activation Checklist

- [ ] `python3 scripts/smart_router.py --symbol BTC --side short --size 100000` → verify FR fetched from 3 venues
- [ ] `python3 scripts/smart_router.py --all-symbols` → verify all K208 symbols scored
- [ ] Check `data/smart_router_dashboard.json` written
- [ ] Set `SMART_ROUTER_ENABLED = True` in `scripts/k280_live_fetch.py`
- [ ] `cp com.cryptolab.smart-router.plist ~/Library/LaunchAgents/ && launchctl load ...`
- [ ] See `docs/k302a_runbook.md §24` for full playbook

---

## Phase Status

| Phase | Description | Status |
|-------|-------------|--------|
| 1 | `scripts/smart_router.py` (~330 LOC) | DONE |
| 2 | `data/smart_router_config.json` | DONE |
| 3 | Per-venue state fetchers (HL/Bybit/OKX) | DONE |
| 4 | Score function | DONE |
| 5 | Decision algorithm + concentration caps | DONE |
| 6 | Dashboard JSON (`data/smart_router_dashboard.json`) | DONE |
| 7 | `com.cryptolab.smart-router.plist` | DONE |
| 8 | K208 call site scaffold in `k280_live_fetch.py` | SCAFFOLD |
| 9 | `verify_deployment_status.py` updated (16th daemon) | DONE |
| 10 | HTML banner badge + status card | DONE |
| 11 | Manual test | PENDING (user) |

---

*K434 Smart Router SCAFFOLD — 2026-05-29 22:59 JST*

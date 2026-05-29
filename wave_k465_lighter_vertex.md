# Wave K465: Lighter + Vertex Integration Scaffold

**Date:** 2026-05-30  
**Status:** COMPLETE — 7-venue K208 mesh SCAFFOLD-READY  
**Daemon count:** 26 (25th = Lighter, 26th = Vertex)

---

## Summary

Wave K465 completes the v6.20 7-venue K208 mesh by adding:
- **Lighter** (6th venue): zkEVM perpetual exchange, ZK proof settlement
- **Vertex** (7th venue): spot+perp AMM hybrid, USDC margin

Both venues integrated as read-only scaffolds following the K456/K460 OKX/Aevo pattern. No production K280 logic modified.

### 7-Venue K208 Mesh (COMPLETE)

| # | Venue | Chain | FR Cycle | Status |
|---|-------|-------|----------|--------|
| 1 | HyperLiquid | HL L1 | 8h | ACTIVE |
| 2 | Bybit | CEX | 8h | ACTIVE |
| 3 | OKX | CEX | 8h | SCAFFOLD-READY (K456) |
| 4 | Aevo | Ethereum | 1h | SCAFFOLD-READY (K460) |
| 5 | dYdX v4 | Cosmos | 1h | SCAFFOLD-READY (K460) |
| 6 | Lighter | zkEVM | 8h | SCAFFOLD-READY (K465) |
| 7 | Vertex | Arbitrum | 8h | SCAFFOLD-READY (K465) |

---

## Phase 1: API Research

### Lighter API
- **Base URL:** `https://mainnet.zklighter.elliot.ai`
- **FR endpoint:** `GET /api/v1/funding-rates` (all markets bulk)
- **Markets:** `GET /api/v1/markets` (mark price, OI, leverage)
- **Order books:** `GET /api/v1/orderBooks?market={SYMBOL}`
- **Metrics:** `GET /api/v1/exchangeMetrics?market={SYMBOL}`
- **Auth:** NOT required for public read-only endpoints
- **Funding cycle:** 8h (conservative default — verify via /api/v1/markets)
- **Colocation:** AWS Tokyo ap-northeast-1a (apne1-az4)

### Vertex API
- **Gateway:** `https://gateway.prod.vertexprotocol.com/v1`
- **Archive:** `https://archive.prod.vertexprotocol.com/v1`
- **FR endpoint:** `POST /query {"type": "funding_rates", "product_ids": [2, 4, ...]}`
- **Historical FR:** `POST /indexer {"funding_rates": {"product_id": N, "limit": L}}`
- **All products:** `POST /query {"type": "all_products"}`
- **Auth:** NOT required for public read-only query endpoints
- **Funding cycle:** 8h
- **Product IDs:** BTC=2, ETH=4, ARB=6, SOL=12 (verify via --products)
- **Margin:** USDC

---

## Deliverables

### New Scripts
- `scripts/lighter_fr_fetcher.py` (~340 LOC) — K456/Aevo pattern, zkEVM
- `scripts/vertex_fr_fetcher.py` (~420 LOC) — Gateway POST + Archive historical

### New Plists (gitignored)
- `com.cryptolab.lighter-fr-monitor.plist` — 25th daemon, StartInterval 28800 (8h)
- `com.cryptolab.vertex-fr-monitor.plist` — 26th daemon, StartInterval 28800 (8h)

### New Dashboard JSONs
- `data/lighter_dashboard.json` — initial scaffold
- `data/vertex_dashboard.json` — initial scaffold (includes product_id_map)

### Updated Scripts
- `scripts/verify_deployment_status.py` — Lighter (25th) + Vertex (26th) added to REGISTRY
- `scripts/emergency_hl_exit.py` — `--include-lighter` + `--include-vertex` stub flags
- `scripts/depth_aware_allocator.py` — VENUE_CONFIG + FALLBACK_OI_USD extended

### Updated Config
- `data/smart_router_config.json` — Lighter + Vertex venues (7 total)
- `data/leverage_config.json` — K280_K208_Lighter=3.0, K280_K208_Vertex=3.0

### Documentation
- `docs/k302a_runbook.md §35` — Full Lighter + Vertex integration overview

### HTML
- `report.html` — K465 banner added, 2 new daemon rows (25th/26th)

---

## Conservative Tier Configuration

Both new venues start at conservative allocation:

| Setting | Lighter | Vertex | Established |
|---------|---------|--------|-------------|
| max_pct_of_oi | 0.03 | 0.03 | 0.05 |
| min_depth_usd | 25,000 | 25,000 | 50K–100K |
| leverage_cap | 3.0x | 3.0x | 3.0x |
| concentration_cap | 10% | 10% | 15–65% |

**Upgrade path:** Standard tier after 30d data accumulation + live API validation.

---

## TODO Post-K465

1. **Lighter auth:** Obtain API key via lighter.xyz → implement authenticated orders
2. **Vertex auth:** USDC deposit → implement wallet-signed `/execute` calls
3. Verify Vertex product IDs via `python3 scripts/vertex_fr_fetcher.py --products`
4. Activate plists after API connectivity confirmed (see §35.10 activation playbook)
5. Upgrade conservative tier caps after 30d of live data

---

## K339 Security

- `REPO_ROOT = Path(__file__).resolve().parent.parent` — no `/Users/` literals
- Plists gitignored (contain REPO_ROOT placeholder)
- API keys: env var only, never logged
- Read-only public endpoints: no auth required for K465 scaffold scope

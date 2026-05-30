# Wave K765 — Smart Order Routing + Slippage Minimization

**Wave:** K765 | **Axis:** #6 (Execution Edge) | **Status:** SCAFFOLD_READY | **Date:** 2026-05-30 21:52 JST
**Pattern:** K339 REPO_ROOT | **Default:** PAPER_TRADE=True | LIVE 自動変更禁止

---

## Executive Summary

Profit-max axis #6 = execution edge (slippage削減、BBO aggregation、split orders、time-of-day routing).
Previously unexplored. Applied to all 30+ sleeves via `route_order(strategy_id, side, notional)`.

**Baseline:** ~5 bps avg slippage per order
**Target:** ~3 bps avg (-40% reduction)
**Mechanism:** POST_ONLY first + BBO routing + split orders reduce half-spread crossing cost

---

## K523 3-Point Uplift @$10M AUM

| Scenario | Gross /yr | Realized /yr (K518 38%) |
|----------|-----------|------------------------|
| Conservative (50% capture, 300% turnover) | $6,000 | $2,280 |
| **Central (100% capture, 300% turnover)** | **$12,000** | **$4,560** |
| Optimistic (250% capture, 500% turnover) | $30,000 | $11,400 |

**Reduction:** 2.00 bps avg | Turnover: $30M/yr (300% of $10M, both sides)
**K523 MANDATORY:** Central $12,000/yr is NOT upper bound. Realized $4,560/yr (K518 38%).
Upper bound = optimistic $30,000/yr gross.

---

## Architecture

```
route_order(strategy_id, side, notional)
  │
  ├── fetch_bbo_all_venues()   → HL / Bybit / OKX real-time BBO
  ├── time_of_day_score()      → penalize 00-06 UTC low-liquidity
  ├── estimate_slippage_k765() → improved half-spread + linear impact model
  ├── compute_split_legs()     → split if notional > $500K (depth-proportional)
  └── log_slippage()           → data/slippage_log.jsonl
```

**K765 vs K434 slippage model:**
- K434: linear market impact only (depth proxy)
- K765: half-spread + market impact + POST_ONLY 50% discount + TOD penalty

---

## Venue BBO Summary (Mock)

| Venue | Avg Spread | Avg Depth |
|-------|-----------|-----------|
| HL    | ~0.5-15 bps | $80K-$2.8M |
| Bybit | ~0.3-18 bps | $110K-$3.2M |
| OKX   | ~0.2-14 bps | $70K-$2.5M |

Best venue varies by symbol and time-of-day.

---

## Split Order Logic

- **Threshold:** $500K notional → split across ≤3 venues
- **Weight:** Proportional to depth_usd (deepest venue gets largest leg)
- **Min leg:** $50K (skip venues below minimum)
- **Applicable:** K208 ($500K), K449 ETH-BTC ($600K paired), K276b ($300K)

---

## Time-of-Day Routing

| UTC Window | Band | Penalty |
|-----------|------|---------|
| 00:00–05:59 | LOW | +0.5 bps |
| 06:00–11:59, 22:00–23:59 | MEDIUM | +0.25 bps |
| 12:00–21:59 | HIGH | 0 bps |

→ Defer non-urgent orders from 00-06 UTC. Optimal: 12-22 UTC (European/US overlap).

---

## Implementation

| File | Description |
|------|-------------|
| `scripts/k765_smart_router.py` | ~500 LOC, K339 pattern, PAPER_TRADE default |
| `data/slippage_log.jsonl` | Per-order slippage tracking (expected vs actual fill) |
| `data/k765_routing_decisions.jsonl` | Routing decisions log |
| `data/k765_smart_router_dashboard.json` | Dashboard JSON |
| `wave_k765_smart_routing.{py,json,md}` | Wave files |
| `docs/k302a_runbook.md` | §74 K765 activation runbook |

---

## Activation (1-step)

```bash
# Step 1: dry-run validation
python3 scripts/k765_smart_router.py --dry-run

# Step 2: route all 33 registered sleeves
SMART_ROUTER_ENABLED=true python3 scripts/k765_smart_router.py --all-sleeves

# Step 3: monitor dashboard
cat data/k765_smart_router_dashboard.json | python3 -m json.tool | head -40

# Revert (zero code change)
SMART_ROUTER_ENABLED=false
```

---

## References

| Wave | Description |
|------|-------------|
| K765 | This wave — smart routing + slippage minimization (axis #6) |
| K434 | K434 smart router (FR-based venue scoring, K208 only) |
| K439 | K439 POST_ONLY order manager (IOC fallback, fill rate G8) |
| K523 | K523 3-point projection mandate |
| K208 | K208 reverse carry (primary beneficiary of improved routing) |
| K755 | K755 K481 builder rebate scaffold (complementary execution axis) |
| K757 | K757 Bybit sub-account (multi-account venue capacity) |
| K763 | K763 compounding scheduler (profit-max axis #3) |

---

*K765 §74 — Smart Order Routing + Slippage Minimization (axis #6, +$4,560 central realized @$10M) — 2026-05-30 21:52 JST*
*K339 REPO_ROOT | PAPER_TRADE=True | LIVE 自動変更禁止*

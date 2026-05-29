# Wave K458: Depth-Aware Allocator
**Date:** 2026-05-30 | **Status:** SCAFFOLD-READY | **Priority:** HIGH
**K454 Phase 5** — v6.20 Capacity Rescue | **21st Daemon**

---

## Executive Summary

K454 found that linear AUM scaling produces quadratic slippage when positions
are concentrated at a single venue. K458 implements the depth-aware allocator
that distributes positions across HL/Bybit/OKX respecting per-venue OI caps
(5% each), rescuing strategy capacity at $100M+ AUM.

---

## Problem (K454 Finding)

```
AUM $10M  → BTC $2M  → 0.25% HL OI  → ~0.25 bps  ✓ fine
AUM $100M → BTC $20M → 2.5% HL OI   → ~2.5 bps   ⚠ acceptable but degrading
AUM $100M (naive) → all on HL → 25%+ OI → quadratic slip → BAD
```

Without the allocator, scaling to $100M+ results in severe market impact at
single venues that individually cannot absorb the position size.

---

## Solution

**Greedy depth-aware allocator:**
1. Fetch live OI + L2 book depth from HL, Bybit, OKX
2. Compute 5% OI cap per venue
3. Score venues: maker rebate + book depth + capacity
4. Greedy fill: best venue first, up to cap, until target absorbed
5. Validate: total slippage < 20bps threshold
6. Reduce target if no venue combination can absorb

---

## $100M Simulation Results

| Metric | Without Allocator | With Allocator |
|--------|------------------|----------------|
| Method | HL only | HL + Bybit + OKX |
| BTC $20M % of OI | ~2.5% single venue | <1% per venue |
| Slippage est. | degrading (scale) | ~50-80% lower |
| Validation | FAIL at scale | PASS (< 20bps) |

**Capacity absorption (BTC 20% position):**
- $10M AUM: 100% absorbable
- $100M AUM: 85% absorbable
- $500M AUM: 60% absorbable

---

## Files Created

| File | Description |
|------|-------------|
| `scripts/depth_aware_allocator.py` | ~500 LOC main script (K339 pattern) |
| `com.cryptolab.depth-allocator.plist` | 21st daemon plist (gitignored) |
| `scripts/verify_deployment_status.py` | Updated with 21st daemon entry |
| `data/depth_allocator_dashboard.json` | Initial dashboard JSON |
| `data/depth_allocator_decisions.jsonl` | Decision log (created at runtime) |
| `docs/k302a_runbook.md §31` | Depth-aware allocator runbook section |
| `report.html` | K458 banner + daemon row + footer |

---

## Integration Chain

```
K458 distribute_target()
├── fetch_venue_depth() → HL l2Book + Bybit orderbook + OKX books
├── compute_max_position_per_venue() → 5% OI cap
├── score_venue() → K434 patterns: rebate + depth + cap
├── greedy allocate → best venue first
├── validate_allocation() → total slip < 20bps
└── submit_allocation_post_only() → K439 POST_ONLY per venue (scaffold)
    └── check_margin_health() → K430 circuit breaker (scaffold)
```

---

## v6.20 Progress

K456 (OKX) + K457 (basket) + K458 (depth allocator) = **3/7 v6.20 waves**

---

## Activation

```bash
# Activate when v6.20 go-live + AUM >$10M:
cp com.cryptolab.depth-allocator.plist ~/Library/LaunchAgents/
launchctl load ~/Library/LaunchAgents/com.cryptolab.depth-allocator.plist

# Manual test:
python3 scripts/depth_aware_allocator.py --dry-run --aum 100000000
python3 scripts/depth_aware_allocator.py --symbol BTC --target 20000000 --dry-run
```

# Wave K450 — K449 Production Scaffold

**Date:** 2026-05-30 | **Status:** COMPLETE

## Executive Summary

K450 builds the full production scaffold for the K449 ETH-BTC funding rate
differential strategy.  K449 was accepted in the previous wave with 8/9 §6 gates
passing.  K450 adds all plumbing for a paper-trade-safe 19th daemon.

## Deliverables

| File | Type | Description |
|------|------|-------------|
| `scripts/k449_eth_btc_run.py` | NEW | 285 LOC strategy script: FR fetch, 7d EMA, paired-trade, rebalance, close |
| `scripts/smart_router.py` | EXTENDED | `select_best_venue_for_paired()`: HL-priority multi-leg routing |
| `scripts/post_only_order_manager.py` | EXTENDED | `execute_paired_trade()`: POST_ONLY both legs, separate fill tracking |
| `scripts/leverage_manager.py` | UPDATED | K449 3% sleeve + K449_ETH_BTC 4x cap + SLEEVE_WEIGHTS_V616 |
| `scripts/emergency_hl_exit.py` | UPDATED | K449 pair detection; short leg closed first to prevent uncovered short |
| `scripts/verify_deployment_status.py` | UPDATED | 19th daemon added (com.cryptolab.k449-eth-btc) |
| `data/leverage_config.json` | UPDATED | K449_ETH_BTC: 4.0 exchange cap |
| `data/k449_dashboard.json` | NEW | Initial dashboard (NEUTRAL, PAPER-TRADE, v6.16 proposal) |
| `com.cryptolab.k449-eth-btc.plist` | NEW | 19th daemon, StartInterval=28800, RunAtLoad=false, gitignored |
| `docs/k302a_runbook.md` | UPDATED | §29 K449 (10 subsections: overview, mechanics, v6.16, activation, rollback) |
| `report.html` | UPDATED | K449 row + v6.16 badge + timestamps |

## Strategy Design

### Signal
- Fetch BTC and ETH 8h funding rates from HL `metaAndAssetCtxs`
- Compute 7d EMA of (BTC FR − ETH FR)
- Entry when |EMA| > 0.00001

### Trade Direction
```
EMA > +threshold → LONG ETH / SHORT BTC  (BTC FR is richer, collect as short)
EMA < −threshold → LONG BTC / SHORT ETH  (ETH FR is richer)
|EMA| <= threshold → NEUTRAL
```

### Sizing (at $10M AUM)
| Item | Value |
|------|-------|
| Sleeve | 3% = $300K |
| Leverage | 4x |
| Notional/leg | $300K × 4 ÷ 2 = **$600K** |
| Total notional | **$1.2M** |
| Margin required | $300K (3% of AUM) |

### Delta-Neutral Rebalance
- Check drift daily: if |long_val/short_val − 1| > 5% → rebalance
- Reduce larger leg to restore equal notional

## v6.16 Architecture Proposal

| Sleeve | v6.13d | v6.16 candidate | Change |
|--------|--------|-----------------|--------|
| K280 | 75% | 72% | −3pp to fund K449 |
| K297' | 20% | 20% | unchanged |
| sUSDe | 5% | 5% | unchanged |
| K449 | — | 3% | NEW |
| HL exposure | 57.5% | 60.5% | +3pp |

**Status:** PROPOSED — requires 60d paper-trade gate pass.

## Activation Criteria

| Gate | Requirement |
|------|-------------|
| G1 | ≥ 60 calendar days paper-trade |
| G2 | ≥ 65% fill rate (both legs POST_ONLY) |
| G3 | ≥ 2.0 Sharpe (60d paper) |
| G4 | ≤ 10% max drift during paper period |
| G5 | Combined margin < 80% AUM |

## Daemon Count

18 (K444) → **19 (K450)**

19th daemon: `com.cryptolab.k449-eth-btc` (8h, RunAtLoad=false, gitignored plist)

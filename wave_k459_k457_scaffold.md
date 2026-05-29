# Wave K459: K457 Multi-Asset Basket Production Scaffold

**Date:** 2026-05-25  
**Status:** SCAFFOLD-READY  
**Wave:** K459 (22nd daemon)

---

## Executive Summary

K457 (BTC+ETH+SOL simultaneous FR carry basket) received CONDITIONAL ACCEPT with OOS Sharpe **19.58** — the highest standalone single-strategy result in the crypto-lab backtest history. K459 scaffolds the full production infrastructure for 60d paper-trade evaluation before v6.20 activation at 5% sleeve.

---

## K457 Strategy Result

| Metric | Value |
|--------|-------|
| OOS Sharpe | **19.58** (highest standalone!) |
| Decision | **CONDITIONAL ACCEPT** |
| Gate | 60d paper-trade + OOS Sh ≥15 + fill_rate ≥65% |
| v6.20 sleeve target | **5% AUM** |
| Backtest Sharpe vs K449 | 19.58 vs 8.9 (K457 +10.68 alpha) |

---

## Implementation Summary

### Phase 1: `scripts/k457_basket_run.py` (NEW, ~300 LOC)
- K339 REPO_ROOT pattern (no /Users/ literals)
- Single-shot 8h cron (FR cycle)
- `fetch_per_asset_fr(symbols) -> dict`: HL + Bybit per asset
- `compute_inv_vol_weights(symbols) -> dict`: 30d realized vol normalization
- `apply_dar_filter(fr_series, p=2, q=1) -> bool`: DAR(2,1) signal gate
- `decide_basket_position(weights, dar_signals) -> dict`: per-asset position direction
- `submit_basket_trade(positions) -> dict`: 6-leg execution (3 longs + 3 shorts)
- `close_basket_position(reason) -> dict`: 6-leg unwind (shorts first)

### Phase 2: Position Management
For each asset: compute FR spread (HL - Bybit), apply DAR(2,1), if signal: long lower-FR venue, short higher-FR venue. Size = total_sleeve × inv_vol_weight × leverage.

### Phase 3: K434 Smart Router Multi-Asset Extension
Per-asset venue decision with smart router scoring. K355 HL concentration cap ≤65%.

### Phase 4: K439 POST_ONLY Triple-Leg Extended to 6 Legs
All 6 legs POST_ONLY first, 5-min wait, IOC fallback per leg, per-asset fill rate tracked.

### Phase 5: K430 Leverage 4x
K457 leverage cap = 4x. `data/leverage_config.json` updated: `K457_basket: 4.0`.

### Phase 6: K357 Emergency Exit Basket Close
`--include-k457` flag in `emergency_hl_exit.py`. Sequential close: short legs first, then longs. `_detect_k457_basket_positions()` auto-detects BTC/ETH/SOL pairs.

### Phase 7: Inv-Vol Weight Rebalancing
Updated each 8h cycle from FR history JSONL (30d lookback).

### Phase 8: Data Structures
`data/k457_basket_dashboard.json` created with initial scaffold state.

### Phase 9: Plist `com.cryptolab.k457-basket.plist`
StartInterval: 28800 (8h), gitignored, 22nd daemon.

### Phase 10: `verify_deployment_status.py`
K457 basket added as 22nd daemon, expected SCAFFOLD-READY.

### Phase 11: 60d Paper-Trade Gate
- OOS Sharpe ≥ 15 (paper, 60d)
- Fill rate ≥ 65% (G8 gate)
- Pass → activate v6.20 K457 sleeve at 5%
- Fail → extend or reject

### Phase 12: `docs/k302a_runbook.md §32`
Full K457 basket runbook including inv-vol mechanics, DAR filter, multi-asset execution playbook, emergency exit protocol, daemon config, and 60d activation criteria.

### Phase 13: HTML Banner Update
- K457 row in Live Monitoring (SCAFFOLD-READY, 22nd daemon)
- v6.20 progress badge updated: "K456-K458 + K459 = 4/7 v6.20 waves"
- Timestamp updated: 2026-05-25 00:53 JST

---

## Daemon Registry (Post-K459)

| # | Label | Status |
|---|-------|--------|
| 21st | com.cryptolab.depth-allocator | SCAFFOLD-READY |
| **22nd** | **com.cryptolab.k457-basket** | **SCAFFOLD-READY** |

Total daemons: **22**

---

## 60d Paper-Trade Activation Criteria

| Gate | Threshold | Current |
|------|-----------|---------|
| G1: OOS Sharpe | ≥ 15.0 (paper, 60d) | PENDING (day 0/60) |
| G8: Fill rate | ≥ 65% (all 6 legs) | PENDING |
| Backtest OOS Sharpe | — | 19.58 (confirmed) |

**On pass:** activate v6.20 K457 sleeve at 5% AUM  
**On fail:** extend paper-trade 30d or reject

---

## v6.20 Progress

| Wave | Description | Status |
|------|-------------|--------|
| K456 | OKX FR Monitor (3rd K208 venue, 20th daemon) | SCAFFOLD-READY |
| K457 | BTC+ETH+SOL basket FR carry (OOS Sh 19.58) | CONDITIONAL ACCEPT |
| K458 | Depth-Aware Allocator ($100M+ slippage rescue, 21st daemon) | SCAFFOLD-READY |
| **K459** | **K457 basket production scaffold (22nd daemon)** | **SCAFFOLD-READY** |
| K460-K462 | Remaining 3/7 v6.20 waves | TBD |

Progress: **4/7 v6.20 waves complete**

---

## Files Changed

```
scripts/k457_basket_run.py          NEW   (~300 LOC, 8h cron, 6-leg basket)
com.cryptolab.k457-basket.plist     NEW   (gitignored, 22nd daemon, StartInterval 28800)
scripts/verify_deployment_status.py UPDATED (22nd daemon K457 basket in REGISTRY)
data/k457_basket_dashboard.json     NEW   (initial scaffold state)
scripts/emergency_hl_exit.py        UPDATED (--include-k457, _detect_k457_basket_positions)
scripts/leverage_manager.py         UPDATED (K457_basket 4x cap, SLEEVE_WEIGHTS, margins)
data/leverage_config.json           UPDATED (K457_basket: 4.0 + k457_basket_notes)
docs/k302a_runbook.md               UPDATED (§32 K457 basket runbook, ~200 lines)
report.html                         UPDATED (K457 Live Monitoring row, v6.20 4/7 progress)
wave_k459_k457_scaffold.md          NEW   (this file)
wave_k459_k457_scaffold.json        NEW   (formal record)
```

---

*K459 Wave — 2026-05-25 00:53 JST — 22 daemons confirmed — 0 mismatches expected*

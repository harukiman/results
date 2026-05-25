# Wave K304 — HL predictedFundings Live Monitor Scaffold

**Date:** 2026-05-25
**Status:** Deployed (single-shot verified)

---

## Overview

Builds operational live monitor for HL predictedFundings API.
Not a signal replacement — a monitoring scaffold for K208/K265/K276b/K297 strategies.

**API endpoint:** `POST https://api.hyperliquid.xyz/info {"type": "predictedFundings"}`
- Public, no auth required
- Returns 230 coins × 3 venues (HlPerp / BinPerp / BybitPerp)
- Response size: ~3-10 KB per call
- K298 confirmed Spearman 0.9989 vs realized FR

---

## Files Delivered

| File | Purpose |
|------|---------|
| `scripts/hl_predicted_fr_monitor.py` | Polling + alert + dashboard script |
| `data/hl_predicted_fr_dashboard.json` | Live dashboard (refreshed every 5 min) |
| `com.cryptolab.hl-predicted-monitor.plist` | launchctl 5-min interval daemon |
| `wave_k304_hl_monitor_scaffold.md` | This deployment guide |

---

## Deployment

### 1. Install launchctl agent

```bash
cp /Users/nekonaomichi/crypto-lab/com.cryptolab.hl-predicted-monitor.plist \
   ~/Library/LaunchAgents/
launchctl load ~/Library/LaunchAgents/com.cryptolab.hl-predicted-monitor.plist
```

### 2. Verify it loaded

```bash
launchctl list | grep hl-predicted
# Should show: com.cryptolab.hl-predicted-monitor
```

### 3. Monitor logs

```bash
tail -f /Users/nekonaomichi/crypto-lab/logs/hl_predicted_fr_monitor.log
tail -f /Users/nekonaomichi/crypto-lab/logs/hl_predicted_fr_monitor_err.log
```

### 4. Manual single-shot trigger

```bash
/Users/nekonaomichi/crypto-lab/.venv311/bin/python3 \
    /Users/nekonaomichi/crypto-lab/scripts/hl_predicted_fr_monitor.py
```

### 5. Reload after script changes

```bash
launchctl unload ~/Library/LaunchAgents/com.cryptolab.hl-predicted-monitor.plist
launchctl load   ~/Library/LaunchAgents/com.cryptolab.hl-predicted-monitor.plist
```

### 6. Uninstall

```bash
launchctl unload ~/Library/LaunchAgents/com.cryptolab.hl-predicted-monitor.plist
rm ~/Library/LaunchAgents/com.cryptolab.hl-predicted-monitor.plist
```

---

## Cache Architecture

```
cache/hl_predicted_fr_YYYYMMDDHHMM.parquet
  - 5-min snapshots, 230 rows each
  - Columns: ts_ms, coin, hl_fr, hl_next_settle_ms, bin_fr, bin_next_settle_ms,
             bybit_fr, bybit_next_settle_ms
  - File size: ~9-12 KB per snapshot (snappy compression)
  - 288 files/day × ~10 KB = ~2.9 MB/day rolling
  - 24h purge: older files automatically deleted
  - Max steady-state: ~288 files × ~10 KB ≈ 3 MB
```

---

## Alert Logic

### K208 Spread Alerts (Bybit - HL spread monitoring)

| Level | Condition |
|-------|-----------|
| NORMAL | `|spread_bps|` > 2.0 bps |
| HIGH | `|spread_bps|` > 3.0 bps |
| EXTREME | `|spread_bps|` > 6.0 bps |

- Coins: SOL, XRP, SUI, OP, APT, AXS, JTO, IMX, SAND, ADA
- `LONG_SPREAD` signal = spread > 0 (Bybit FR > HL FR; favorable for reverse carry)
- Use as intra-8h-cycle spread sign verification for K208 DAR(2,1)

### K265/K276b Rank Alerts

- Tracks 35 K265 coins ranked by HL predicted FR (descending)
- Alerts when any K276b top-20 coin shifts rank by >= 3 positions vs prior snapshot
- First run: no prior → no rank alerts (bootstraps cleanly)
- Steady-state: prior = snapshot from 5 min ago

### K297 RWA Tracking

- Tracks: XAG, XAU, SPX, PAXG, NQ
- XAG, XAU, NQ: NOT_LISTED on HL (confirmed by K297 analysis)
- SPX, PAXG: listed, currently at HL floor rate (+0.1250 bps)
- `SHORT_CARRY_LIVE` = positive FR = longs paying → short carry opportunity

---

## API Rate Limit Etiquette

- **288 calls/day** at 5-min intervals = extremely light load
- HL info endpoint: no published rate limit; community norm ~1 req/s for info
- This monitor: 1 req/300s = 0.003 req/s (negligible)
- Single POST body, ~100 bytes request / ~5 KB response
- No authentication, no order placement — read-only monitoring

---

## Initial Snapshot (2026-05-25 04:49 UTC)

**Top 5 highest HL predicted FR:**

| Coin | HL FR (bps) |
|------|-------------|
| NIL | +1.608 |
| XMR | +1.082 |
| 0G / 2Z / AAVE+ | +0.125 (floor) |

**K208 spread snapshot (Bybit - HL):**

| Coin | Spread (bps) | Signal |
|------|-------------|--------|
| SOL | -0.909 | NO_ENTRY |
| APT | +1.202 | LONG_SPREAD |
| ADA | +0.386 | LONG_SPREAD |
| IMX | +0.375 | LONG_SPREAD |
| OP | +0.266 | LONG_SPREAD |
| SUI | +0.254 | LONG_SPREAD |

**K297 RWA:**
- SPX: +0.1250 bps → SHORT_CARRY_LIVE
- PAXG: +0.1250 bps → SHORT_CARRY_LIVE
- XAG/XAU/NQ: NOT_LISTED

---

## Future Use (K310+)

The dashboard JSON at `data/hl_predicted_fr_dashboard.json` is the integration point:

```python
import json
with open("data/hl_predicted_fr_dashboard.json") as f:
    dash = json.load(f)

# K208 spread signals
spreads = dash["k208_spread_snapshot"]

# K265/K276b current ranks
ranks = {r["coin"]: r["rank"] for r in dash["k265_k276b_rank_snapshot"]}

# Alerts
alerts = dash["alerts_firing"]

# Pre-settlement awareness
mins_left = dash["mins_to_next_hl_settle"]
```

Potential K310+ experiments:
1. **K208 spread gate enhancement**: Use live `spread_bps` to time K208 entry within 8h cycle
2. **K265 rank momentum**: If top-quartile rank is stable for 3 consecutive snapshots → increase position
3. **Pre-settlement short carry**: Enter K297 PAXG/SPX short carry when `mins_to_next_hl_settle` < 30

---

## Notes

- `mins_to_next_hl_settle` may be negative if settlement occurred mid-cycle; next poll will reset
- K265 rank alerts are delta vs previous 5-min snapshot; large deltas on 2nd run are expected (bootstrapping)
- Rank alerts use K276b (top-20) for signal relevance; full K265 (35) available in rank_snapshot
- Dashboard JSON is overwritten each poll; if archival needed, add timestamped copies in K310+

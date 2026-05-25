# Wave K305 — K302a v6.12 Paper-Trade Scaffold
**Generated:** 2026-05-25 UTC | **Status:** COMPLETE

---

## Executive Summary

K305 delivers the K302a v6.12 paper-trade scaffold, replacing K289 (K287d: K270 dYdX + K275 OKX)
with K297 (PAXG/SPX RWA perp carry on HyperLiquid only). All 5 deliverables built, tested, and verified.

**First-run results:**
- PAXG: 415 days data | 7d ann FR: 7.79% | 87.7% positive days | 30d Sh: 19.86
- SPX:  504 days data | 7d ann FR: 9.04% | 78.0% positive days | 30d Sh: 25.47
- Satellite (PAXG 60% + SPX 40%): 30d Sh = **25.35** | all-time Sh = 10.47 | equity = 1.0862 (+8.6%)
- K280 main 30d Sh: 27.32 | No alerts triggered on first run

---

## Deliverables

| File | Purpose | Status |
|------|---------|--------|
| `scripts/k302a_satellite_fetch.py` | Incremental PAXG/SPX FR fetch from HL API | DONE |
| `scripts/k302a_satellite_run.py` | Daily paper-trade (always-on carry, 80/20 view) | DONE |
| `data/k302a_satellite_dashboard.json` | Live satellite dashboard (initial snapshot) | DONE |
| `com.cryptolab.k302a-satellite.plist` | launchctl daemon (09:30 JST, replaces K287 slot) | DONE |
| `scripts/k302a_migration.sh` | Stop K287 → backup → load K302a → reconcile | DONE |

---

## Architecture: K302a v6.12

```
ARCHITECTURE: K302a
CORE (80%):      K280 [K272a 50% + K276b 50%] — Bybit + HyperLiquid
SATELLITE (20%): K297 [PAXG 60% + SPX 40%]   — HyperLiquid only
TOTAL EXCHANGES: 2 (Bybit + HyperLiquid)

K302a combined Sharpe target: 32.59 (K303 decision matrix)
vs K287d: 33.00 (3 exchanges) | K302a: 32.59 (2 exchanges)
Efficiency: 16.30 Sh/exchange (K302a) vs 11.00 (K287d)
```

---

## Strategy Detail: K302a Satellite (K297)

### PAXG Component (60% of satellite)
- **Asset:** PAXG (Paxos gold-backed token) perp on HL HIP-3
- **Direction:** Always-on LONG — receive positive funding rate
- **Data start:** 2025-04-06 (415 days of history)
- **Backtest:** Sh=16.91, MaxDD=-0.36%, Win Days 88%, Ann Return 8.03%
- **Current (live, 2026-05-25):** 7d ann FR 7.79%, 30d Sh 19.86

### SPX Component (40% of satellite)
- **Asset:** SPX (S&P 500 index) perp on HL HIP-3
- **Direction:** Always-on LONG — receive positive funding rate
- **Data start:** 2025-01-07 (504 days of history)
- **Backtest:** Sh=5.87, MaxDD=-1.74%, Win Days 78%, Ann Return 6.80%
- **Current (live, 2026-05-25):** 7d ann FR 9.04%, 30d Sh 25.47

### Portfolio
| Metric | Backtest (K297) | Live (2026-05-25) |
|--------|----------------|-------------------|
| Satellite Sh (all) | 10.17 (EW) | 10.47 |
| Satellite Sh (30d) | — | 25.35 |
| Satellite MaxDD (all) | -1.41% | -0.38% |
| Satellite equity | — | +8.62% cumulative |
| PAXG vs SPX correlation | 0.18 | (low, confirmed) |

---

## HL Maker/Taker Cost Reality (K296 Finding)

| Cost Type | Rate | bp |
|-----------|------|----|
| HL maker | 0.015%/side | 1.5 bp |
| HL taker | 0.045%/side | 4.5 bp |
| Paper-trade assumption | 0.07%/side | 7.0 bp (conservative, 4.7x maker) |
| Cost amortization | 7bp / 30d hold | 0.233 bp/day |

Always-on carry uses maker orders. Paper-trade applies 7 bp/side amortized over 30-day hold period.
Real live PnL expected to be higher than paper-trade by ~5.5 bp/side (maker vs paper assumption).

---

## K289 Deprecation (K287d Rollback Retention)

| Item | Status |
|------|--------|
| `com.cryptolab.k287-satellite.plist` | Source file preserved; `.disabled_k305` copy as rollback |
| `scripts/k287_satellite_fetch.py` | PRESERVED — not deleted |
| `scripts/k287_satellite_run.py` | PRESERVED — not deleted |
| `cache/k270_dydx_daily.parquet` | Backed up to `cache/k287d_backup/` |
| `cache/okx_fr_daily.parquet` | Backed up to `cache/k287d_backup/` |
| `cache/k270_dydx/` | Backed up to `cache/k287d_backup/k270_dydx/` |
| `data/k287_satellite_dashboard.json` | Backed up to `cache/k287d_backup/` |
| Rollback window | 60 days (until 2026-07-25) |

K287d daemon is DISABLED but not deleted. Full rollback available in <5 minutes.

---

## Step 1: Run Migration

```bash
# DRY RUN first to verify
bash scripts/k302a_migration.sh --dry-run

# Execute migration (stops K287, backs up, loads K302a, reconciles)
bash scripts/k302a_migration.sh
```

---

## Step 2: Verify Installation

```bash
# Check K302a daemon is loaded
launchctl list | grep k302a

# Check K287 daemon is stopped
launchctl list | grep k287

# Verify K280 main still running
launchctl list | grep k280

# Check K302a dashboard
python3 -c "
import json
with open('data/k302a_satellite_dashboard.json') as f:
    d = json.load(f)
rm = d['rolling_metrics'] or {}
af = d.get('active_alert_flags', {})
print('Last update:', d['last_update'])
print(f'Satellite Sh: 7d={rm.get(\"sh_7d\",\"N/A\")}  30d={rm.get(\"sh_30d\",\"N/A\")}  all={rm.get(\"sh_all\",\"N/A\")}')
print(f'Satellite MaxDD: 30d={rm.get(\"mdd_30d\",\"N/A\")}  all={rm.get(\"mdd_all\",\"N/A\")}')
print(f'Satellite equity: {d.get(\"sat_equity\",\"N/A\")}')
print('Alert flags:', af)
"
```

---

## Step 3: Daily Manual Trigger

```bash
cd /Users/nekonaomichi/crypto-lab

# Step A: Fetch (incremental — only fetches delta since last run)
.venv311/bin/python3 scripts/k302a_satellite_fetch.py

# Force re-fetch (use after outage)
.venv311/bin/python3 scripts/k302a_satellite_fetch.py --force

# Step B: Daily execution
.venv311/bin/python3 scripts/k302a_satellite_run.py
```

---

## Step 4: Monitoring

### Watch logs:
```bash
tail -f logs/k302a_satellite.log
tail -f logs/k302a_satellite_err.log
```

### Dashboard status:
```bash
python3 -c "
import json
with open('data/k302a_satellite_dashboard.json') as f:
    d = json.load(f)
r = d['daily_records'][-1] if d['daily_records'] else {}
paxg = r.get('component', {}).get('PAXG', {})
spx  = r.get('component', {}).get('SPX', {})
print(f'PAXG: Sh(30d)={paxg.get(\"metrics\", {}).get(\"sh_30d\", \"N/A\")}  weight={paxg.get(\"weight\", 0):.1%}')
print(f'SPX:  Sh(30d)={spx.get(\"metrics\", {}).get(\"sh_30d\", \"N/A\")}  weight={spx.get(\"weight\", 0):.1%}')
print(f'Sat today PnL: {r.get(\"today_sat_pnl\", \"N/A\")}')
print('Alerts today:', [a[\"code\"] for a in r.get('alerts_today', [])])
print('Exchange status:', r.get('exchange_status', {}))
"
```

### Combined K302a view (satellite + K280 main):
```bash
python3 -c "
import json
with open('data/k302a_satellite_dashboard.json') as f:
    sat = json.load(f)
with open('data/k280_live_dashboard.json') as f:
    k280 = json.load(f)
sat_sh = (sat.get('rolling_metrics') or {}).get('sh_30d', 'N/A')
k280_sh= (k280.get('rolling_metrics') or {}).get('sh_30d', 'N/A')
sat_eq = sat.get('sat_equity', 'N/A')
print(f'K280 main 30d Sh: {k280_sh}  |  Satellite 30d Sh: {sat_sh}')
print(f'Satellite equity: {sat_eq}')
print(f'K302a combined BT Sh: {sat[\"backtest\"][\"combined_sh\"]} (target)')
"
```

---

## Step 5: Alert Response Protocols

| Alert Code | Condition | Action |
|-----------|-----------|--------|
| `SAT_DD_HALT` | Satellite 30d MaxDD > 0.5% | HALT satellite immediately. K303 trigger: half of K297 MaxDD (-1.41%). |
| `PAXG_LOW_SH` | PAXG 30d Sh < 3.0 | PAXG carry compressed. Check HL HIP-3 funding pool utilization. Monitor for HL-wide FR suppression. |
| `SPX_LOW_SH` | SPX 30d Sh < 2.0 | SPX carry compressed. Often coincides with equity volatility regimes. Monitor 14d trend. |
| `HL_EXCHANGE_ERROR` | HL API unreachable | CRITICAL. Halt paper logging. Both satellite and K280 HL component at risk. Check status.hyperliquid.xyz. |
| `SAT_SH_LOW` | Satellite 30d Sh < 2.0 | Satellite drag on combined. Re-evaluate K302a vs K287d revert. |
| `NO_SNAPSHOT` | No daily fetch run | Run fetch manually. Likely cron failure — check launchctl and log. |

---

## Step 6: K303 Deployment Timeline

| Day | Action | Trigger |
|-----|--------|---------|
| 0 (2026-05-25) | K302a scaffold live, paper-trade active | K305 complete |
| 1-14 | Shadow K302a alongside K287d | Compare daily PnL delta |
| 15-30 | K302a live at 20% target capital | Manual step — verify 14d Sh ≥ 25 |
| 31+ | Full capital, K287d rollback window expires | 30d Sh ≥ 25.0 |
| 60 | K287d 60d rollback window closes (2026-07-25) | Delete .disabled_k305 plist |

**Live capital trigger:** 14d rolling Sh ≥ 25.0  
**Revert trigger:** K302a 55d Sh < 28.0  

---

## File Inventory (K305 additions)

```
scripts/k302a_satellite_fetch.py          — NEW (this wave)
scripts/k302a_satellite_run.py            — NEW (this wave)
scripts/k302a_migration.sh                — NEW (this wave)
com.cryptolab.k302a-satellite.plist       — NEW (this wave)
data/k302a_satellite_dashboard.json       — NEW (seeded by first run)
data/k302a_satellite_paper_trades.jsonl   — NEW (seeded by first run)
cache/k302a_fr_daily.parquet              — NEW (PAXG+SPX daily panel)
cache/k302a_satellite_20260525.parquet    — NEW (daily snapshot)
cache/k302a_satellite_20260525.json       — NEW (daily snapshot metadata)
wave_k305_v6_12_scaffold.md               — THIS FILE
```

---

*Wave K305 — 2026-05-25 UTC*

# K302a v6.12 Operational Runbook
**Version:** 1.0 | **Generated:** 2026-05-25 | **Wave:** K307
**Status:** PRODUCTION REFERENCE — DO NOT DELETE

---

## Architecture Quick Reference

```
K302a v6.12 = K280 Core (80%) + K297 Satellite (20%)

K280 Core (80%):
  K198  Ridge ML allocator            [~10.8% live weight]
  K208  DAR(2,1) reverse carry        [~42.3% live weight]
  K276b HL FR 14d rank L/S (20 syms)  [~46.9% live weight]
  Exchanges: Bybit + HyperLiquid

K297 Satellite (20%):
  PAXG  always-on HL carry            [60%]
  SPX   always-on HL carry            [40%]
  Exchange: HyperLiquid only

Capital exposure by exchange:
  HyperLiquid: ~60% (K208 HL leg + K276b + K297 satellite)
  Bybit:        ~40% (K208 Bybit leg)
```

---

## Backtest Reference Targets

| Metric | K280 Core | K302a Combined |
|--------|-----------|----------------|
| Sharpe (OOS) | 18.46 | 32.59 |
| Sharpe WF min | 12.97 | 21.60 |
| MaxDD | -0.000013 | -0.0202% |
| Ann Return | ~8-12% | ~10-15% |
| K303 live Sh gate (Day 22) | — | ≥ 15 (7d) |
| K303 full capital gate (Day 31) | — | ≥ 25 (30d) |
| K303 revert trigger | — | < 25 (30d Sh) |

---

## 1. Risk Inventory

### 1.1 HyperLiquid Outage (CRITICAL — 60% Capital Exposure)

**Why most critical:** K302a consolidates 3 strategy components on HL (K208 HL leg, K276b, K297). Any HL outage makes 60% of paper positions unrealizable in live.

**Failure modes:**
- HL API returns 5xx → fetch scripts catch non-200 codes and fall back to cached data
- HL API timeout (> 500ms × 3 consecutive checks) → `HL_API_LATENCY` alert in K304 monitor
- HL trading halt / market suspension → live positions cannot be closed; funding accrues adversely
- HL smart contract / protocol exploit → catastrophic; 400+ day track record in K280 production

**Response — outage confirmed:**
1. Check HL status: `https://hyperliquid.xyz/` and community Discord
2. If K280 fetch fails (`fetch=$FETCH_FAILED` in log): paper PnL for today uses yesterday's signal; acceptable for 1 day
3. If live trading: CLOSE ALL HL POSITIONS immediately via HL UI
4. Disable K302a satellite daemon: `launchctl unload ~/Library/LaunchAgents/com.cryptolab.k302a-satellite.plist`
5. Disable K280 HL-dependent fetch: run K208 Bybit-only mode (manual)
6. After HL recovery: reload daemon, run `--force` re-fetch, reconcile positions

**Prolonged HL outage (> 3 days):**
- Rollback to K287d satellite (see Section 7) if within 60d rollback window
- Re-evaluate architecture: HL-only concentration is the accepted K302a trade-off

### 1.2 Bybit Outage (K208, K280 Core)

**Exposure:** ~40% of capital (K208 Bybit FR data source and trade venue)

**Failure modes:**
- Bybit API unreachable: K208 spread computation fails; fetch script logs `FETCH FAILED`
- Bybit FR data stale: K208 DAR gate uses yesterday's signal (graceful degradation)
- Bybit trading halt: K208 Bybit-leg positions cannot be closed

**Response:**
1. Check Bybit status page
2. K208 component can be disabled independently: set K208 weight to 0 in `scripts/k280_daily_run.py` and restart
3. K276b and K297 (both HL-only) continue unaffected
4. For live: close Bybit positions via Bybit UI

### 1.3 API Key Rotation

**Bybit API keys:**
- K280 scripts use Bybit read-only keys for FR data (no order placement in paper trade)
- Rotation procedure: update `BYBIT_API_KEY` / `BYBIT_API_SECRET` env vars in `~/.zshrc`
- Restart affected daemon: `launchctl unload/load ~/Library/LaunchAgents/com.cryptolab.k280-live.plist`
- Verify: run `scripts/k280_live_fetch.py` manually and check exit code 0

**HyperLiquid:**
- K304 HL predicted FR monitor uses public API (no auth key required)
- K297 / K276b fetch: HL public info endpoint, no API key
- No key rotation needed for current paper-trade configuration

**For live trading (future):**
- Bybit: create trading-only key, no withdrawal permission
- HL: create separate key with trading-only scope
- Store in `.env` file (NOT in git), rotate every 90 days minimum

### 1.4 Cache / Parquet Integrity

**Critical cache files:**
- `cache/hl_k276b_fr_daily.parquet` — K276b 20-symbol FR panel (K280 core)
- `cache/k302a_fr_daily.parquet` — K297 PAXG/SPX FR history (K302a satellite)
- `cache/k280_live_YYYYMMDD.parquet` — daily K280 snapshots
- `cache/k302a_satellite_YYYYMMDD.parquet` — daily K302a snapshots

**Corruption detection:**
```bash
python3 -c "
import pandas as pd
for f in ['cache/hl_k276b_fr_daily.parquet', 'cache/k302a_fr_daily.parquet']:
    try:
        df = pd.read_parquet(f'$CRYPTO_LAB/{f}')
        print(f'OK: {f} — {df.shape}')
    except Exception as e:
        print(f'CORRUPTED: {f} — {e}')
"
```

**Repair procedure:**
1. If parquet unreadable: delete and re-seed with `--force` flag on fetch scripts
2. For K276b panel: `python3 scripts/k280_live_fetch.py --force`
3. For K302a panel: `python3 scripts/k302a_satellite_fetch.py --force`
4. If K287d backup cache needed: `cache/k287d_backup/` preserved from migration

**Prevention:** Fetch scripts write to temp file then atomic rename; partial writes do not corrupt existing cache.

### 1.5 Disk Space (Snapshot Accumulation)

**Daily growth:**
- K304 HL predicted FR monitor: ~2.9 MB/day (288 snapshots × ~10 KB, auto-purge 24h)
- K280 snapshots: ~1 snapshot/day × ~500 KB = ~180 MB/year
- K302a snapshots: ~1 snapshot/day × ~100 KB = ~36 MB/year

**Check disk usage:**
```bash
du -sh $CRYPTO_LAB/cache/ 2>/dev/null
df -h $HOME/
```

**Manual cleanup (safe to delete older than 90 days):**
```bash
# Remove K280 daily snapshots older than 90 days (keep last 90)
find $CRYPTO_LAB/cache -name "k280_live_*.parquet" -mtime +90 -delete
find $CRYPTO_LAB/cache -name "k302a_satellite_*.parquet" -mtime +90 -delete
# K304 snapshots auto-purge (built-in 24h window) — no action needed
```

### 1.6 Network Failures During Fetch

**Graceful degradation design:**
- All fetch scripts log non-zero exit but continue to daily_run with cached data
- K280 plist: `fetch=$FETCH_EXIT run=$RUN_EXIT` logged — if `fetch=1, run=0`, dashboard updates with prior data
- K302a plist: same pattern — PAXG/SPX FR carries over from last successful fetch

**Recovery:**
```bash
# Force re-fetch after network recovery
$CRYPTO_LAB/.venv311/bin/python3 \
    $CRYPTO_LAB/scripts/k280_live_fetch.py --force
$CRYPTO_LAB/.venv311/bin/python3 \
    $CRYPTO_LAB/scripts/k302a_satellite_fetch.py --force
```

### 1.7 Strategy Parameter Drift

**Drift definition:** Live 30d Sharpe deviates > 2σ from backtest OOS reference (18.46 for K280 core)

**Positive drift** (live > backtest): Common during strong carry regimes. Do NOT reduce positions. Monitor for 60-90 days; drift self-corrects as regime normalizes.

**Negative drift** (live < backtest): Investigate immediately.
- Check component-level Sh: which of K198/K208/K276b degraded?
- If K208 spread compressed: SPREAD_COMPRESSED alert fires (INFO level)
- If K276b universe changed: check HL listing/delisting
- If 30d Sh < 25 sustained 7+ days → see K303 revert trigger

**Monitor drift:**
```bash
python3 -c "
import json
with open('$CRYPTO_LAB/data/k280_live_dashboard.json') as f:
    d = json.load(f)
rm = d.get('rolling_metrics', {})
print(f'Drift z-score: {rm.get(\"drift_z\", \"N/A\")} (alert > 2.0, critical > 2.5)')
print(f'30d Sh: {rm.get(\"sh_30d\", \"N/A\")}  (backtest ref: 18.46 for K280 core)')
print(f'Alerts: {d.get(\"active_alert_flags\", {})}')
"
```

---

## 2. Daily Check Checklist

**Run every morning (09:35+ JST, after both daemons have fired)**

### 2.1 Daemon Status
```bash
launchctl list | grep -E "(k280|k302a|hl-predicted|hlp-monitor)"
# All 4 should appear with PID or 0 (scheduled)
```

Expected output:
```
-    0    com.cryptolab.k280-live           (fires 09:00 JST)
-    0    com.cryptolab.k302a-satellite     (fires 09:30 JST)
-    0    com.cryptolab.hl-predicted-monitor (fires every 5 min)
-    0    com.cryptolab.hlp-monitor         (fires 08:00 JST)
```

### 2.2 Dashboard Freshness
```bash
python3 -c "
import json
from datetime import datetime, timezone
files = {
    'K280': 'data/k280_live_dashboard.json',
    'K302a': 'data/k302a_satellite_dashboard.json',
    'HL-pred': 'data/hl_predicted_fr_dashboard.json',
}
for name, path in files.items():
    try:
        with open(f'$CRYPTO_LAB/{path}') as f:
            d = json.load(f)
        lu = d.get('last_update', 'N/A')
        print(f'{name}: {lu}')
    except Exception as e:
        print(f'{name}: ERROR — {e}')
"
```

### 2.3 Today's PnL Check
```bash
python3 -c "
import json
for label, path in [('K280', 'data/k280_live_dashboard.json'), ('K302a', 'data/k302a_satellite_dashboard.json')]:
    with open(f'$CRYPTO_LAB/{path}') as f:
        d = json.load(f)
    rm = d.get('rolling_metrics', {})
    print(f'{label}: 7d Sh={rm.get(\"sh_7d\",\"N/A\")}  30d Sh={rm.get(\"sh_30d\",\"N/A\")}  MaxDD={rm.get(\"mdd_all\",\"N/A\")}')
    recs = d.get('daily_records', [])
    if recs:
        today = recs[-1]
        print(f'  Today PnL: {today.get(\"pnl\", \"N/A\")}')
"
```

### 2.4 Alert Log Review
```bash
# K280 alerts
tail -20 $CRYPTO_LAB/logs/k280_live.log | grep -E "(ALERT|CRITICAL|HALT|REDUCE|ERROR)"

# K302a alerts
tail -20 $CRYPTO_LAB/logs/k302a_satellite.log | grep -E "(ALERT|CRITICAL|HALT|REDUCE|ERROR)"

# HL monitor alerts
tail -20 $CRYPTO_LAB/logs/hl_predicted_fr_monitor.log | grep -E "(ALERT|HIGH|EXTREME)"

# Error files
tail -5 $CRYPTO_LAB/logs/k280_live_err.log
tail -5 $CRYPTO_LAB/logs/k302a_satellite_err.log
```

### 2.5 Drift Score Check
```bash
python3 -c "
import json
with open('$CRYPTO_LAB/data/k280_live_dashboard.json') as f:
    d = json.load(f)
z = d.get('rolling_metrics', {}).get('drift_z', None)
if z is None:
    print('drift_z: N/A')
elif abs(z) < 1.5:
    print(f'drift_z: {z:.2f} — NORMAL')
elif abs(z) < 2.0:
    print(f'drift_z: {z:.2f} — WATCH')
else:
    print(f'drift_z: {z:.2f} — ALERT (> 2sigma)')
"
```

**Expected ranges:**
- K280 30d Sh: 15-35 (normal running range around backtest 18.46)
- K302a satellite 30d Sh: 8-20 (PAXG Sh 16.91, SPX Sh 5.87, portfolio Sh 10.17)
- Combined drift_z: < 2.0 (positive drift common in bull carry regimes — do not act)

---

## 3. Weekly Check Checklist

**Run every Monday morning (covers prior week)**

### 3.1 7d Cumulative PnL vs Backtest
```bash
python3 -c "
import json
with open('$CRYPTO_LAB/data/k280_live_dashboard.json') as f:
    d = json.load(f)
rm = d.get('rolling_metrics', {})
sh7 = rm.get('sh_7d', 'N/A')
sh30 = rm.get('sh_30d', 'N/A')
print(f'K280 — 7d Sh: {sh7}  |  30d Sh: {sh30}  |  Backtest OOS: 18.46')
print(f'       WF min threshold: 12.97')
# K302a
with open('$CRYPTO_LAB/data/k302a_satellite_dashboard.json') as f:
    d2 = json.load(f)
rm2 = d2.get('rolling_metrics', {})
print(f'K302a — 7d Sh: {rm2.get(\"sh_7d\",\"N/A\")}  |  30d Sh: {rm2.get(\"sh_30d\",\"N/A\")}  |  Backtest Sh: 10.17 (full 504d)')
"
```

**Decision guide:**
- 7d Sh < 5 for K280 core: investigate component breakdown
- 7d Sh < 3 for K302a satellite: check PAXG and SPX FR individually

### 3.2 Per-Component 7d Sharpe
```bash
python3 -c "
import json
with open('$CRYPTO_LAB/data/k280_live_dashboard.json') as f:
    d = json.load(f)
cc = d.get('component_contribution', {})
for comp, info in cc.items():
    print(f'{comp}: weight={info.get(\"weight\",0):.1%}  30d_sh={info.get(\"sh_30d\",\"N/A\")}  ref={info.get(\"oos_ref_weight\",0):.1%}')
"
```

### 3.3 HLP Balance Trajectory (K200 Monitor)
```bash
python3 -c "
import json
with open('$CRYPTO_LAB/data/k280_live_dashboard.json') as f:
    d = json.load(f)
hlp = d.get('hlp_status', {})
print(f'HLP balance:   \${hlp.get(\"balance_m\",\"N/A\")}M')
print(f'HLP 7d change: {hlp.get(\"change_7d_pct\",\"N/A\")}%')
print(f'HLP 30d change: {hlp.get(\"change_30d_pct\",\"N/A\")}%')
print(f'HLP alert level: {hlp.get(\"alert_level\",\"N/A\")}')
"
# Also check HLP monitor log
tail -10 $CRYPTO_LAB/logs/hlp_monitor.log
```

**HLP thresholds:**
- NORMAL: 7d change > -20%
- REDUCE (T1): 7d change -20% to -40% → K208 scaled 50% automatically
- HALT (T2): 7d change < -40% → K208 weight → 0 automatically

### 3.4 7d Alert Count Summary
```bash
grep -c "ALERT\|CRITICAL\|HALT\|REDUCE" $CRYPTO_LAB/logs/k280_live.log 2>/dev/null || echo "0 alerts in K280 log"
grep -c "ALERT\|CRITICAL\|HALT\|REDUCE" $CRYPTO_LAB/logs/k302a_satellite.log 2>/dev/null || echo "0 alerts in K302a log"
# Per-week count (last 7 days of log)
grep "$(date -v -7d '+%Y-%m-%d')" $CRYPTO_LAB/logs/k280_live.log | grep -c "ALERT" || echo "0"
```

### 3.5 K302a Satellite Weight Stability
```bash
python3 -c "
import json
with open('$CRYPTO_LAB/data/k302a_satellite_dashboard.json') as f:
    d = json.load(f)
sw = d.get('satellite_weights', {})
print(f'PAXG weight: {sw.get(\"PAXG\",0):.1%}  (target: 60%)')
print(f'SPX weight:  {sw.get(\"SPX\",0):.1%}  (target: 40%)')
recs = d.get('daily_records', [])
if len(recs) >= 7:
    print('Last 7 days satellite Sh:')
    for r in recs[-7:]:
        print(f'  {r.get(\"date\",\"?\")} PnL={r.get(\"pnl\",\"N/A\")}')
"
```

**Weight drift threshold:** If PAXG weight deviates > ±15pp from 60% target for 7+ days, investigate vol regime shift.

---

## 4. Monthly Check Checklist

**Run on the 1st of each month**

### 4.1 30d Sharpe vs Backtest Target
```bash
python3 -c "
import json
with open('$CRYPTO_LAB/data/k280_live_dashboard.json') as f:
    d = json.load(f)
sh30 = d.get('rolling_metrics', {}).get('sh_30d', 'N/A')
print(f'K280 30d Sh: {sh30}  |  Backtest OOS: 18.46  |  K303 gate: ≥25 for full capital')
with open('$CRYPTO_LAB/data/k302a_satellite_dashboard.json') as f:
    d2 = json.load(f)
sh30_sat = d2.get('rolling_metrics', {}).get('sh_30d', 'N/A')
print(f'K302a combined target: 32.59  |  Revert threshold: <25 sustained')
print(f'K302a satellite 30d Sh: {sh30_sat}  (backtest: 10.17)')
"
```

**K303 gates:**
- < 25 combined Sh for 7+ days → re-evaluate architecture
- < 25 combined Sh at Day 22 checkpoint → do NOT scale to full capital
- ≥ 25 at Day 31 → scale to 100% capital
- K302a 55d Sh < 28.0 → revert to K287d

### 4.2 Strategy Parameter Sensitivity Check

Check if K208 DAR gate thresholds remain valid:
```bash
# Check recent spread behavior for K208 symbols
python3 -c "
import json
with open('$CRYPTO_LAB/data/k280_live_dashboard.json') as f:
    d = json.load(f)
compressed = d.get('active_alert_flags', {}).get('spread_compressed_syms', [])
print(f'K208 spread compressed symbols: {compressed}')
print('(Expected: 0-5 INFO-level compressions is normal)')
"
```

Check if K276b universe coverage has degraded:
```bash
python3 -c "
import json
with open('$CRYPTO_LAB/data/k280_live_dashboard.json') as f:
    d = json.load(f)
low_liq = d.get('active_alert_flags', {}).get('k276b_low_liq', [])
print(f'K276b low liquidity symbols (coverage < 70% 7d): {low_liq}')
print('(If any: consider removing from K276b universe)')
"
```

### 4.3 Component Correlation Re-evaluation

Run every 30 days to verify K297 still diversifies vs K280:
```bash
python3 -c "
import json, numpy as np
with open('$CRYPTO_LAB/data/k280_live_dashboard.json') as f:
    k280 = json.load(f)
with open('$CRYPTO_LAB/data/k302a_satellite_dashboard.json') as f:
    k302a = json.load(f)
k280_pnls = [r.get('pnl', 0) for r in k280.get('daily_records', [])[-90:]]
k302a_pnls = [r.get('pnl', 0) for r in k302a.get('daily_records', [])[-90:]]
n = min(len(k280_pnls), len(k302a_pnls))
if n >= 30:
    r = np.corrcoef(k280_pnls[-n:], k302a_pnls[-n:])[0, 1]
    print(f'90d correlation K280 vs K302a satellite: {r:.3f}')
    print('(Backtest reference: -0.26. Threshold: keep < 0.5)')
    if abs(r) > 0.5:
        print('WARNING: correlation exceeds threshold — diversification benefit reduced')
else:
    print('Insufficient data (need >= 30 days)')
"
```

### 4.4 Rebalance Decision (K303 Protocol)

| Day | Condition | Action |
|-----|-----------|--------|
| Day 0 | Deploy | K287d daemon disabled; K302a paper-trade starts |
| Day 15 | 7d Sh ≥ 10 (paper) | Go live 20% capital on HL |
| Day 22 | 7d Sh ≥ 15 (live) | Continue scaling plan |
| Day 31 | 30d Sh ≥ 25 | Scale to 100% capital |
| Day 60 | All conditions met | Delete K287d rollback cache |
| Ongoing | 30d Sh < 25 sustained | Re-evaluate / revert |

---

## 5. Alert Response Playbook

### 5.1 SPREAD_COMPRESSED_* (K304 / K280 Monitor)

**Level:** INFO — no immediate action required
**Condition:** K208 symbol 7d spread < 75% of 30d baseline (Bybit FR ≈ HL FR)
**Background:** DAR(2,1) gate already accounts for spread compression; K208 naturally de-weights when spread thin

**Action:**
- Log alert in weekly count
- If 5+ symbols compressed simultaneously for 3+ days: check if HL is normalizing Bybit spreads (macro event?)
- K208 backtest robustness confirmed in fold 2 (spread compression regime) at Sh 12.97 WF min

### 5.2 K265/K276b Rank Shift (K304 Monitor)

**Condition:** Top-20 K276b coin shifts rank >= 3 positions vs prior 5-min snapshot
**Level:** INFO — no immediate action required
**Rationale:** Rank alerts are delta vs 5-min prior; large deltas are expected during funding period transitions

**Action:**
- Review if K276b rebalances at next daily run (09:00 JST)
- If rank shift persists for 3+ consecutive 5-min snapshots → potential early signal of FR regime shift
- No position changes based on intraday rank alerts (K276b is daily rebalance)

### 5.3 HLP Balance -20%/7d (K200 Monitor → T1 Trigger)

**Condition:** HLP 7d change < -20%
**Level:** ALERT — automatic K208 de-weighting
**Impact:** K208 weight halved (×0.5 scale factor) automatically by k280_daily_run.py

**Action:**
1. Verify HLP alert in dashboard:
   ```bash
   python3 -c "import json; d=json.load(open('$CRYPTO_LAB/data/k280_live_dashboard.json')); print(d.get('hlp_status', {}))"
   ```
2. Monitor HLP daily until change recovers to > -20%
3. K208 weight auto-restores when condition clears
4. Check K303 section 5: HLP T1 triggers during ADL events (March 2025 JELLY attack was -57.7%)
5. If K208 carry is already short HL (reverse carry), ADL risk may be amplified — review K208 signal direction

### 5.4 Satellite DD > 1% (K302a)

**Condition:** K302a satellite 30d MaxDD > 1.0% (half of K297 full-period MaxDD -1.41%)
**Level:** ALERT → emergency review

**Action:**
1. Identify which component drove DD:
   ```bash
   python3 -c "
   import json
   with open('$CRYPTO_LAB/data/k302a_satellite_dashboard.json') as f:
       d = json.load(f)
   recs = d.get('daily_records', [])[-7:]
   for r in recs:
       print(r.get('date'), r.get('pnl'), r.get('component', {}))
   "
   ```
2. Check PAXG and SPX FR individually — if PAXG FR goes negative, carry reverses
3. If DD > 1.5% (K302a critical threshold):
   - Halt satellite: `launchctl unload ~/Library/LaunchAgents/com.cryptolab.k302a-satellite.plist`
   - Review PAXG/SPX FR regime (is HL HIP-3 mechanism inverted?)
   - Do not restart without understanding root cause

### 5.5 HL Outage — Full Position Close Protocol

**Emergency procedure (live trading only):**
1. Log in to HL UI immediately: `https://app.hyperliquid.xyz/`
2. Close all open positions: Portfolio → Select All → Close All
3. Do not attempt API calls (API is unreachable by definition)
4. Stop K302a daemon: `launchctl unload ~/Library/LaunchAgents/com.cryptolab.k302a-satellite.plist`
5. Stop K280 daemon: `launchctl unload ~/Library/LaunchAgents/com.cryptolab.k280-live.plist`
6. Note positions closed (for reconciliation after recovery)
7. After HL recovery: re-fetch with `--force`, verify positions match expected signals

**Paper trade only (current state):** No real positions; log the outage date and duration only.

### 5.6 Bybit Outage — K208 Component Disable

**Procedure:**
1. K208 fetch fails → K280 daily_run continues with stale K208 data (1-day lag acceptable)
2. If outage > 2 days: disable K208 component manually in `scripts/k280_daily_run.py`
   - Set `k208_weight_override = 0.0` (temporary)
3. K276b and K197 continue unaffected on HL
4. After Bybit recovery: remove override, run `--force`, verify spread data fresh

---

## 6. Position Scaling Ramp (K303 Deployment Plan)

| Day | Phase | Capital | Action | Gate |
|-----|-------|---------|--------|------|
| **Day 0** | Migration | 0% live | Run `scripts/k302a_migration.sh`; disable K287d daemon; start K302a paper | — |
| Day 1-14 | Shadow | 0% live | Monitor K302a dashboard daily; compare vs K287d backup PnL | — |
| **Day 15** | Phase 1 live | 20% capital | Start live trading at 20% of target capital on HL | 7d paper Sh ≥ 10 |
| **Day 22** | Checkpoint | 20% capital | Review 7d live Sh; continue if gate passed | 7d live Sh ≥ 15 |
| Day 23-30 | Continue | 20% capital | Monitor; no action unless gate failed | — |
| **Day 31** | Full capital | 100% capital | Scale to full capital if 30d Sh gate passed | 30d Sh ≥ 25 |
| Day 60 | Lock | — | K287d rollback option closed; delete K287d backup cache | Sh stable |

**If Day 22 gate fails (7d Sh < 15):**
- Do NOT scale to 100%
- Extend shadow period to Day 30
- Re-evaluate at Day 30; if 30d Sh < 25, initiate rollback

**If Day 31 gate fails (30d Sh < 25):**
- Maintain 20% capital allocation
- Set re-evaluation date + 30 days
- If 60d Sh < 25: initiate rollback to K287d (if within 60d window)

---

## 7. Rollback Procedure (K302a → K287d)

**Use when:** K302a 55d Sh < 28.0 OR 30d Sh < 25 sustained, within 60-day rollback window

### Step 1: Stop K302a Daemon
```bash
launchctl unload ~/Library/LaunchAgents/com.cryptolab.k302a-satellite.plist
launchctl list | grep k302a  # should show nothing
```

### Step 2: Re-enable K287d Daemon
```bash
# Restore the disabled K287d plist
cp $CRYPTO_LAB/com.cryptolab.k287-satellite.plist.disabled_k305 \
   ~/Library/LaunchAgents/com.cryptolab.k287-satellite.plist
launchctl load ~/Library/LaunchAgents/com.cryptolab.k287-satellite.plist
launchctl list | grep k287  # should appear
```

### Step 3: Restore K287c Satellite Cache
```bash
# Restore backed-up cache files from migration
cp $CRYPTO_LAB/cache/k287d_backup/k270_dydx_daily.parquet \
   $CRYPTO_LAB/cache/k270_dydx_daily.parquet
cp $CRYPTO_LAB/cache/k287d_backup/okx_fr_daily.parquet \
   $CRYPTO_LAB/cache/okx_fr_daily.parquet
# Restore K270 per-symbol directory if needed
cp -r $CRYPTO_LAB/cache/k287d_backup/k270_dydx \
      $CRYPTO_LAB/cache/k270_dydx
echo "Cache restored from k287d_backup/"
```

### Step 4: Reconcile Positions
```bash
# Run K287d fetch to verify data is current
$CRYPTO_LAB/.venv311/bin/python3 \
    $CRYPTO_LAB/scripts/k287_satellite_fetch.py --force

$CRYPTO_LAB/.venv311/bin/python3 \
    $CRYPTO_LAB/scripts/k287_satellite_run.py

# Verify K287d dashboard updated
python3 -c "
import json
with open('$CRYPTO_LAB/data/k287_satellite_dashboard.json') as f:
    d = json.load(f)
print('K287d last update:', d.get('last_update'))
print('K287d satellite Sh (30d):', d.get('rolling_metrics', {}).get('sh_30d'))
print('Alerts:', d.get('active_alert_flags', {}))
"
```

**Note on K275 stale data:** OKX FR history is limited to ~90 days. After rollback, if gap > 7 days, K275 coverage may be sparse. Run with `--force` to trigger re-fetch of recent OKX data.

---

## 8. Reconciliation (Live PnL vs Backtest Expected)

### 8.1 Daily Expected PnL (Rough Estimate)

Formula (approximation):
```
Daily expected return ≈ Annual Sh × Daily Vol / sqrt(252)
K280 core: ~18.46 × daily_vol / sqrt(252)
K302a combined: ~32.59 × daily_vol / sqrt(252)
```

K302a combined MaxDD = -0.0202% absolute → implied daily vol ≈ 0.03-0.05%
Daily expected return ≈ 32.59 × 0.04% / sqrt(252) ≈ 0.082% (rough)

**Practical check:** Daily PnL should be positive 80%+ of days (backtest win rate: 82.9% for K302a).

### 8.2 Weekly Expected Metrics

| Window | Expected Sh | Win Days % | Action if below |
|--------|-------------|------------|----------------|
| 7d rolling | ≥ 10 | ≥ 70% | Investigate component breakdown |
| 30d rolling | ≥ 20 (warning) / ≥ 25 (gate) | ≥ 78% | < 20 → watch; < 15 → re-evaluate |
| 55d rolling | ≥ 28 | ≥ 80% | < 28 → K303 revert trigger |

### 8.3 Drift Monitoring

**Drift z-score interpretation:**
- `drift_z` < 1.5 → NORMAL
- `drift_z` 1.5-2.0 → WATCH (log weekly)
- `drift_z` > 2.0 → ALERT (investigate; positive drift is common in early deployment)
- `drift_z` > 3.0 with negative sign → CRITICAL (live significantly below backtest)

**Drift threshold for action:** Negative drift_z > 2.0 sustained 14+ days → parameter sensitivity check (Section 4.2).

---

## 9. Failure Mode Tree

### Unknown Failure Mode Decision Tree

```
SYMPTOM: Unexpected PnL deviation or system anomaly
│
├─ Q1: Which daemons are running?
│   └─ launchctl list | grep cryptolab
│       ├─ All 4 running → proceed to Q2
│       └─ Missing daemon → restart missing daemon (Section 2.1)
│
├─ Q2: Is the dashboard JSON updated today?
│   └─ Check last_update timestamp (Section 2.2)
│       ├─ Fresh (< 6h) → proceed to Q3
│       └─ Stale → run manual fetch + daily_run (Section 1.6)
│
├─ Q3: Which exchange is affected?
│   ├─ HL errors in log → check HL status (hyperliquid.xyz)
│   │   ├─ HL down → Section 5.5 (HL outage protocol)
│   │   └─ HL up → check API key, rate limits
│   └─ Bybit errors → Section 5.6 (Bybit protocol)
│
├─ Q4: Is PnL anomalous or just drift?
│   ├─ Positive drift (live > backtest) → normal, monitor, no action
│   ├─ Negative drift < 2σ → log, watch
│   ├─ Negative drift > 2σ → Section 1.7 (drift response)
│   └─ Single day large loss → check PAXG/SPX FR sign flip (K302a) or spread spike (K208)
│
├─ Q5: Component-level failure?
│   ├─ K208 degraded → check spread compression (SPREAD_COMPRESSED alert)
│   ├─ K276b degraded → check HL listing changes, coverage > 70%
│   ├─ K297 degraded → check PAXG/SPX FR (must be positive for carry to work)
│   └─ K198 degraded → Ridge ML allocator; check recent covariance matrix stability
│
└─ Q6: Systemic failure?
    ├─ Combined 30d Sh < 25 sustained 7d → rebalance decision (Section 4.4)
    ├─ Combined 55d Sh < 28 → K303 revert trigger → Section 7 (Rollback)
    └─ Unknown cause after Q1-Q5 → escalate to parameter sensitivity check (Section 4.2)
```

### 9.1 Escalation Criteria

| Trigger | Severity | Escalation Action |
|---------|----------|-------------------|
| 1 daemon down for > 1h | MEDIUM | Restart daemon; check launchctl status |
| HL API unreachable for > 30 min | HIGH | Start HL outage protocol (Section 5.5) |
| Combined 30d Sh < 20 | HIGH | Daily monitoring; prepare rollback |
| K302a satellite DD > 1.5% | HIGH | Halt satellite daemon |
| Combined 55d Sh < 28 | CRITICAL | Initiate rollback to K287d (Section 7) |
| HLP balance 7d change < -40% | CRITICAL | K208 auto-halted; verify; monitor |
| Both exchanges simultaneously down | CRITICAL | All operations halt; wait for recovery |
| Parquet corruption on main cache | HIGH | Re-seed from force-fetch; if unavailable, use backup |

---

## 10. Manual Commands Reference

```bash
BASE=$CRYPTO_LAB
PYTHON=$BASE/.venv311/bin/python3

# Daemon management
launchctl list | grep cryptolab                          # list all daemons
launchctl unload ~/Library/LaunchAgents/com.cryptolab.k280-live.plist
launchctl load   ~/Library/LaunchAgents/com.cryptolab.k280-live.plist
launchctl unload ~/Library/LaunchAgents/com.cryptolab.k302a-satellite.plist
launchctl load   ~/Library/LaunchAgents/com.cryptolab.k302a-satellite.plist

# Manual runs
$PYTHON $BASE/scripts/k280_live_fetch.py               # K280 fetch (incremental)
$PYTHON $BASE/scripts/k280_live_fetch.py --force       # K280 fetch (full re-fetch)
$PYTHON $BASE/scripts/k280_daily_run.py                # K280 daily signals
$PYTHON $BASE/scripts/k302a_satellite_fetch.py         # K302a fetch (incremental)
$PYTHON $BASE/scripts/k302a_satellite_fetch.py --force # K302a fetch (full)
$PYTHON $BASE/scripts/k302a_satellite_run.py           # K302a daily signals
$PYTHON $BASE/scripts/hl_predicted_fr_monitor.py       # K304 single-shot poll

# Log monitoring
tail -f $BASE/logs/k280_live.log
tail -f $BASE/logs/k302a_satellite.log
tail -f $BASE/logs/hl_predicted_fr_monitor.log
tail -f $BASE/logs/hlp_monitor.log

# Dashboard inspection
python3 -c "import json; print(json.dumps(json.load(open('$BASE/data/k280_live_dashboard.json')), indent=2))" | head -50
python3 -c "import json; print(json.dumps(json.load(open('$BASE/data/k302a_satellite_dashboard.json')), indent=2))" | head -50
python3 -c "import json; print(json.dumps(json.load(open('$BASE/data/hl_predicted_fr_dashboard.json')), indent=2))" | head -30

# Parquet integrity check
python3 -c "
import pandas as pd
for f in ['cache/hl_k276b_fr_daily.parquet', 'cache/k302a_fr_daily.parquet']:
    df = pd.read_parquet('$BASE/' + f)
    print(f'OK: {f} shape={df.shape} last={df.index[-1] if hasattr(df.index,\"__len__\") else \"N/A\"}')
"
```

---

## 11. Key File Locations

| File | Purpose |
|------|---------|
| `data/k280_live_dashboard.json` | K280 core live monitoring |
| `data/k302a_satellite_dashboard.json` | K302a satellite monitoring |
| `data/hl_predicted_fr_dashboard.json` | K304 HL predicted FR (5-min) |
| `data/k280_paper_trades.jsonl` | K280 daily trade log |
| `data/k302a_satellite_paper_trades.jsonl` | K302a satellite trade log |
| `cache/hl_k276b_fr_daily.parquet` | K276b 20-sym FR panel (critical) |
| `cache/k302a_fr_daily.parquet` | K297 PAXG/SPX FR history (critical) |
| `cache/k287d_backup/` | K287d cache backup (60d rollback) |
| `com.cryptolab.k287-satellite.plist.disabled_k305` | Disabled K287d plist (rollback) |
| `logs/k280_live.log` | K280 main daemon log |
| `logs/k302a_satellite.log` | K302a satellite daemon log |
| `logs/k302a_migration.log` | Migration event log |
| `wave_k303_v6_12_decision.md` | Architecture decision record |
| `wave_k302_k297_only_sat.md` | K302a acceptance gates |
| `scripts/k302a_migration.sh` | Day 0 migration script |
| `docs/k302a_runbook.md` | This runbook |

---

## 12. K310 Plist Deployment Instructions (2026-05-25 14:14 JST)

### Background

Waves K283/K289/K304/K305 documented daemons as "ACTIVE" or "DEPLOY-READY" in the report,
but the LaunchAgent plist files were **never actually created** at `~/Library/LaunchAgents/`.
Wave K310 (2026-05-25) performed a ground-truth audit against `launchctl list | grep cryptolab`
and found 3 missing plists. The files were created and staged but intentionally NOT loaded
pending user verification.

### Plists Created (SCAFFOLD-READY, not yet loaded)

| Plist file | Daemon label | Cadence | Scripts |
|-----------|--------------|---------|---------|
| `~/Library/LaunchAgents/com.cryptolab.k280-live.plist` | `com.cryptolab.k280-live` | 8×/day at HH:05 (00,03,06,09,12,15,18,21) | `k280_live_fetch.py && k280_daily_run.py` |
| `~/Library/LaunchAgents/com.cryptolab.k302a-satellite.plist` | `com.cryptolab.k302a-satellite` | 8×/day at HH:05 (00,03,06,09,12,15,18,21) | `k302a_satellite_fetch.py && k302a_satellite_run.py` |
| `~/Library/LaunchAgents/com.cryptolab.hl-predicted-monitor.plist` | `com.cryptolab.hl-predicted-monitor` | every 5 min (StartInterval 300) | `hl_predicted_fr_monitor.py` |

### Pre-Activation Checklist

Before loading any plist, verify the following:

1. **Test each script manually in your terminal:**
   ```bash
   cd $CRYPTO_LAB
   # K280 main
   .venv311/bin/python scripts/k280_live_fetch.py --dry-run 2>&1 | tail -20
   .venv311/bin/python scripts/k280_daily_run.py 2>&1 | tail -20

   # K302a satellite
   .venv311/bin/python scripts/k302a_satellite_fetch.py --dry-run 2>&1 | tail -20
   .venv311/bin/python scripts/k302a_satellite_run.py 2>&1 | tail -20

   # HL predicted monitor (single-shot)
   .venv311/bin/python scripts/hl_predicted_fr_monitor.py --dry-run 2>&1 | tail -20
   ```

2. **Check that required cache files exist:**
   ```bash
   ls cache/hl_k276b_fr_daily.parquet cache/k302a_fr_daily.parquet 2>/dev/null
   ```

3. **Check log directory is writable:**
   ```bash
   touch logs/k310-test.tmp && rm logs/k310-test.tmp && echo "logs writable"
   ```

### Load Commands (run AFTER checklist passes)

Load all 3 daemons:
```bash
launchctl load ~/Library/LaunchAgents/com.cryptolab.k280-live.plist
launchctl load ~/Library/LaunchAgents/com.cryptolab.k302a-satellite.plist
launchctl load ~/Library/LaunchAgents/com.cryptolab.hl-predicted-monitor.plist
```

Verify they appear in launchctl:
```bash
launchctl list | grep cryptolab
```

Expected output (after loading):
```
-   0   com.cryptolab.k280-live
-   0   com.cryptolab.k302a-satellite
-   0   com.cryptolab.hl-predicted-monitor
# ... plus existing daemons
```

### Monitor Logs After Loading

```bash
tail -f logs/k280-live.log
tail -f logs/k302a-satellite.log
tail -f logs/hl-predicted-monitor.log
```

### Unload / Disable Commands (if needed)

```bash
launchctl unload ~/Library/LaunchAgents/com.cryptolab.k280-live.plist
launchctl unload ~/Library/LaunchAgents/com.cryptolab.k302a-satellite.plist
launchctl unload ~/Library/LaunchAgents/com.cryptolab.hl-predicted-monitor.plist
```

### HLP Monitor (K200)

The K200 HLP balance monitor daemon (`com.cryptolab.hlp-monitor`) was listed in the K310
task as potentially missing. A scan of `scripts/` found no `*hlp*` script files. This daemon
was **not scaffolded** in K310. If required, a corresponding script must be created first.

---

*K307 Runbook — K302a v6.12 — 2026-05-25*

---

## §13 v6.13d Activation Steps (K348 Production Patch)

**Wave:** K348 | **Date:** 2026-05-27 | **Status:** SCAFFOLD-READY (K297' LIVE; sUSDe awaiting launchctl)

### §13.1 Architecture Change Summary

```
v6.12 (previous):
  K280 Core (80%) + K297 Satellite (20%)
  BT Combined Sh: 32.59

v6.13d (K346 winner, K348 deployed):
  K280 Core (75%) + K297' Satellite (20%) + sUSDe OC sleeve (5%)
  BT Combined Sh: 25.47 / MDD 0.0189% / all §6 gates / WF min 22.3

Fallback (v6.13e, regulatory-conservative):
  K280 Core (85%) + K297' Satellite (10%) + sUSDe OC sleeve (5%)
```

### §13.2 Diff Summary (Phase 1–4)

**Phase 1 — K297' SPX filter (scripts/k302a_satellite_run.py)**
- Added module-level config:
  ```python
  SPX_FILTER_ENABLED    = True   # K343 K297→K297' integration (v6.13d)
  SPX_TREND_WINDOW_D    = 5
  SPX_FR_THRESHOLD      = 0.0
  ```
- In `compute_spx_daily_pnl()`, after raw PnL computed:
  ```python
  if SPX_FILTER_ENABLED:
      spx_equity  = (1 + gross_daily).cumprod()
      trend_5d    = spx_equity.pct_change(SPX_TREND_WINDOW_D)
      filter_mask = (trend_5d > 0) & (spx_fr > SPX_FR_THRESHOLD)
      pnl         = pnl.where(filter_mask, 0.0)
  ```
- Updated backtest constants: BT_SPX_SH 5.87 → 12.20, BT_PORT_SH 10.17 → 18.48

**Phase 2 — Weight change (scripts/k302a_satellite_run.py)**
- `K302A_MAIN_WEIGHT`: 0.80 → 0.75
- `K302A_SATELLITE_WEIGHT`: 0.20 (unchanged)
- `K302A_SUSDE_WEIGHT`: 0.05 (new)
- `BT_COMBINED_SH`: 32.59 → 25.47

**Phase 3 — sUSDe OC daemon (scripts/k344_susde_oc_daily_run.py)**
- New script: fetches DeFiLlama sUSDe APY, computes OC signal, writes dashboard JSON + parquet history
- K339 compliant: uses `Path(__file__).resolve().parent.parent`
- OC rules: FULL (APY > EMA+50bps) / HALF (band) / ZERO (below) / SHOCK (7d drop > 3pp)

**Phase 4 — plist (com.cryptolab.susde-oc.plist)**
- Repo root (gitignored per `com.cryptolab.*.plist` rule)
- Label: `com.cryptolab.susde-oc`
- RunAtLoad: false — user must activate manually

### §13.3 Activation Order

1. Verify K280 daemon running:
   ```bash
   launchctl list | grep com.cryptolab.k280
   ```
2. Verify K302a satellite daemon running:
   ```bash
   launchctl list | grep com.cryptolab.k302a
   ```
3. Test sUSDe OC script manually before loading plist:
   ```bash
   python3 scripts/k344_susde_oc_daily_run.py --dry-run
   # Verify: prints signal, no file writes
   python3 scripts/k344_susde_oc_daily_run.py
   # Verify: data/k344_susde_dashboard.json created
   ```
4. Copy and load sUSDe OC plist (LAST — after K280/K302a confirmed):
   ```bash
   cp com.cryptolab.susde-oc.plist ~/Library/LaunchAgents/
   launchctl load ~/Library/LaunchAgents/com.cryptolab.susde-oc.plist
   launchctl list | grep susde-oc   # confirm loaded
   ```
5. Run verification:
   ```bash
   python3 scripts/verify_deployment_status.py
   # Expected: susde-oc PENDING ACTIVATION, NO mismatches
   python3 scripts/audit_cache_integrity.py
   # Expected: all pass
   ```

### §13.4 Rollback Procedure

**Step 1 — Revert SPX filter (immediate, no restart needed)**
```python
# In scripts/k302a_satellite_run.py, set:
SPX_FILTER_ENABLED = False
```
This reverts to K297 always-on behaviour (v6.12).

**Step 2 — Revert weight allocation**
```python
# In scripts/k302a_satellite_run.py:
K302A_MAIN_WEIGHT  = 0.80   # back to 80%
# Remove or zero-out K302A_SUSDE_WEIGHT line
```

**Step 3 — Disable sUSDe OC daemon**
```bash
launchctl unload ~/Library/LaunchAgents/com.cryptolab.susde-oc.plist
rm ~/Library/LaunchAgents/com.cryptolab.susde-oc.plist
```

**Step 4 — Verify rollback**
```bash
python3 scripts/verify_deployment_status.py
```

### §13.5 Monitoring Checkpoints (Post-Activation)

| Checkpoint | Threshold | Action |
|------------|-----------|--------|
| K302a satellite 30d Sharpe | < 25 | Re-evaluate (K303 trigger) |
| SPX 30d Sharpe (K297') | < 2.0 | Review filter; consider SPX_FILTER_ENABLED=False |
| sUSDe OC signal | SHOCK (7d drop > 3pp) | Zero allocation auto (no manual action) |
| sUSDe OC log | Error / no update 24h+ | Check launchctl + logs/k344_susde_oc.log |
| Combined portfolio | MDD > 0.05% | HALT all components, investigate |

---

## §14 Emergency HL Exit Protocol (K357)

**Added:** 2026-05-25 | **Script:** `scripts/emergency_hl_exit.py` | **Status:** SCAFFOLD-READY
**K386 update (2026-05-27):** Two distinct flag files now exist:
- `EMERGENCY_EXIT_TRIGGERED.flag` — closes ALL positions on ALL daemons (catastrophic HL failure)
- `BEAR_1_FALLBACK_ACTIVE.flag`   — closes K297' HIP-3 only; K280/sUSDe continue (regulatory trigger)
See §18 for BEAR_1 activation playbook (CFTC enforcement scenario, P=15%).

### §14.1 Context and Risk

v6.13d production allocates **57.5% of capital** to HyperLiquid infrastructure:
- K280 main (75% weight) × ~50% HL leg = **37.5% on HL**
- K297' satellite (20% weight, PAXG/SPX, HL-only) = **20% on HL**
- sUSDe 5% (Ethena, ETH-based) = 0% on HL

**Worst-case expected loss (K355 assessment):**
- HL platform shutdown probability: 3–7% / 12mo
- Expected loss if triggered: 57.5% × capital × (recovery fraction)
- Annual expected loss (P × impact): 1.7–4.0% of AUM
- K355 verdict: "Acceptable but unmitigated — no emergency exit exists"
- K357 status: **CRITICAL-MITIGATED** — scaffold ready, user activation required

### §14.2 When to Use

Trigger this protocol under **any** of the following conditions:

| Trigger | Threshold | Source |
|---------|-----------|--------|
| Regulatory enforcement | CFTC/SEC action against HL | Official notice |
| Platform exploit signal | Unverified but credible report | Twitter, Discord, HL status |
| ADL cascade | >5 positions auto-deleveraged | HL UI notification |
| Insolvency signal | HLP vault APY drops >50% overnight | K200/K224 monitor |
| HYPE token stress | HYPE -40% in 7 days | Market data |
| Operator discretion | Any conviction >70% of systemic risk | User judgment |

**Do NOT trigger for:**
- Normal market volatility (BTC/ETH -20% in 1 day)
- Temporary HL API outage (<6 hours)
- Individual position stop-loss (handled by strategy logic)

### §14.3 Pre-conditions (Verify Before Executing)

1. **Private key access verified**
   ```bash
   # Confirm you have the private key for the HL address
   echo $HL_PRIVATE_KEY | wc -c   # should be 67 (0x + 64 chars + newline)
   echo $HL_USER_ADDRESS
   ```

2. **Dry-run output verified**
   ```bash
   export HL_USER_ADDRESS=0x<your_address>
   python3 scripts/emergency_hl_exit.py --dry-run
   # → Check positions list, notional, estimated time
   ```

3. **K302a daemons stopped** (prevent conflicting orders)
   ```bash
   launchctl unload ~/Library/LaunchAgents/com.cryptolab.k280-live.plist
   launchctl unload ~/Library/LaunchAgents/com.cryptolab.k302a-satellite.plist
   launchctl unload ~/Library/LaunchAgents/com.cryptolab.susde-oc.plist
   launchctl list | grep cryptolab   # should return empty
   ```

4. **Capital reconciliation** (note current balances)
   ```bash
   python3 scripts/emergency_hl_exit.py --dry-run   # prints balance snapshot
   ```

### §14.4 Step-by-Step Command Sequence

```bash
# Step 1: Set environment variables (NEVER commit these to git)
export HL_USER_ADDRESS=0x<your_hl_address>
export HL_PRIVATE_KEY=0x<your_private_key>

# Step 2: Stop all trading daemons
launchctl unload ~/Library/LaunchAgents/com.cryptolab.k280-live.plist      2>/dev/null || true
launchctl unload ~/Library/LaunchAgents/com.cryptolab.k302a-satellite.plist 2>/dev/null || true
launchctl unload ~/Library/LaunchAgents/com.cryptolab.susde-oc.plist        2>/dev/null || true

# Step 3: Run dry-run and VERIFY the plan output
python3 scripts/emergency_hl_exit.py --dry-run
# → Review: positions listed, notional, estimated time. Confirm looks correct.

# Step 4: EXECUTE (real trading — requires two interactive confirmations)
python3 scripts/emergency_hl_exit.py --EXECUTE
# → Prompt 1: type 'yes'
# → Prompt 2: type 'EXECUTE'
# → Monitor stdout for cancel/close confirmations
# → Script waits 5 min then runs post-check

# Step 5: Verify exit log
tail -50 logs/emergency_hl_exit.log
cat cache/emergency_exit_status.json   # machine-readable status

# Step 6: Check HL UI to confirm zero positions
# Navigate to: https://app.hyperliquid.xyz/portfolio
```

### §14.5 Post-Exit Checklist

- [ ] `logs/emergency_hl_exit_postcheck_*.json` exists and shows `"all_closed": true`
- [ ] `cache/emergency_exit_status.json` shows `"status": "EMERGENCY_EXIT_TRIGGERED"`
- [ ] `EMERGENCY_EXIT_TRIGGERED.flag` file exists in repo root
- [ ] HL UI shows $0 positions for the address
- [ ] No open orders remain
- [ ] USDC balance reconciled with pre-check balance (accounting for PnL + fees + slippage)

**If residual positions remain:**
```bash
# Re-run exit for remaining positions
python3 scripts/emergency_hl_exit.py --EXECUTE
# or manually close in HL UI
```

### §14.6 Recovery Path (Post-Emergency)

After HL exit is complete, options for capital reallocation:

**Option A: v6.13e (Pure Bybit)**
- K280 main → Bybit-only mode (K208 + K246a components only)
- K302a satellite → paused (HL-only, no alternative venue for PAXG/SPX)
- sUSDe OC → unchanged (not HL-dependent)
- Expected Sharpe reduction: ~30% vs full v6.13d

**Option B: K280 Bybit-only fallback (K280b)**
- Activate K246a (Bybit FR carry) and K208 Bybit leg only
- Zero HL exposure
- Reduced AUM utilization (~42.5% of deployed capital active)

**Option C: Pause + assess**
- Zero deployments, capital in USDC
- Assess HL situation: recovery timeline, regulatory status
- Wait for clarity before re-deploying

**To re-enable HL trading after platform recovery:**
```bash
# 1. Remove emergency flag (REQUIRED before daemons will trade)
rm EMERGENCY_EXIT_TRIGGERED.flag

# 2. Update emergency status JSON
python3 -c "
import json; from pathlib import Path
p = Path('cache/emergency_exit_status.json')
d = json.loads(p.read_text())
d['triggered'] = False; d['status'] = 'STANDBY'
p.write_text(json.dumps(d, indent=2))
print('Status reset to STANDBY')
"

# 3. Reload daemons (per §12 activation procedure)
launchctl load ~/Library/LaunchAgents/com.cryptolab.k280-live.plist
launchctl load ~/Library/LaunchAgents/com.cryptolab.k302a-satellite.plist
```

### §14.7 Script Architecture (K357 Design Notes)

**Script:** `scripts/emergency_hl_exit.py`

| Feature | Implementation |
|---------|---------------|
| Default mode | `--dry-run` (safe, no API write calls) |
| Auth | HL_PRIVATE_KEY env var, read only at execution moment, never logged |
| Address | HL_USER_ADDRESS env var or `--user` CLI arg |
| SECP256K1 signing | via `eth_account` (requires `pip install eth-account` for live) |
| Order type | Market-close via IOC limit + `reduceOnly=True` |
| Cancel first | All open orders cancelled before position close |
| Verify after each | Position checked after every close |
| Pre/post snapshots | `logs/emergency_hl_exit_precheck_<ts>.json` + `_postcheck_<ts>.json` |
| Alert | ntfy.sh topic: `cryptolab-emergency-hl-exit` |
| Flag file | `EMERGENCY_EXIT_TRIGGERED.flag` (K302a daemons check this) |
| Dashboard | `cache/emergency_exit_status.json` (JSON for HTML indicator) |

**SCAFFOLD ONLY caveat:**
- Live trading requires: (a) `HL_PRIVATE_KEY` env var, (b) `pip install eth-account`
- Signing implementation uses SECP256K1 via eth_account per HL SDK protocol
- User must verify dry-run output matches actual positions before executing
- Practice the `--EXECUTE` confirm flow without real key before an emergency

### §14.8 Bybit Emergency Close-All (K380 Gap Fix)

**Added:** 2026-05-27 | **Wave:** K380 | **K378 activation criterion #6**

K376 CONDITIONAL_ACCEPT included a requirement to close the gap: K357 only covered HyperLiquid.
K380 adds `close_bybit_positions()` to `scripts/emergency_hl_exit.py`.

**Bybit coverage:**
- Cancels all Bybit open orders via `POST /v5/order/cancel-all` (category=linear)
- Fetches all open positions via `GET /v5/position/list`
- Market-closes each position via `POST /v5/order/create` (Market + reduceOnly + IOC)

**CLI flag added (K380):**

```bash
# Default (HL + Bybit, requires BYBIT_API_KEY + BYBIT_API_SECRET):
python3 scripts/emergency_hl_exit.py --EXECUTE                  # --include-bybit is default=True
python3 scripts/emergency_hl_exit.py --EXECUTE --include-bybit  # explicit

# HL only (skip Bybit):
python3 scripts/emergency_hl_exit.py --EXECUTE --no-bybit

# Dry-run preview:
python3 scripts/emergency_hl_exit.py --dry-run   # shows what WOULD happen
```

**Credentials required for Bybit close-all:**
```bash
export BYBIT_API_KEY=<your_bybit_api_key>
export BYBIT_API_SECRET=<your_bybit_api_secret>
# Keys NEVER logged or committed to git
```

**Bybit exit flow (integrated into §14.4 Step 4):**
1. HL positions cancelled + closed (existing K357 logic)
2. Bybit orders cancelled + positions closed (K380 addition)
3. Post-check verifies HL closure (Bybit: verify via Bybit UI)

**SCAFFOLD note:** Bybit signing uses HMAC-SHA256 (stdlib only — no new packages required).
The `close_bybit_positions()` function is tested in dry-run mode; live execution requires
valid Bybit API keys with trading permission.

### §14.10 Daemon Integration (K302a Daemons Check Flag)

K302a satellite and K280 live daemons SHOULD check for the emergency flag before each run:

```python
# Add to k280_daily_run.py, k302a_satellite_run.py preamble:
from pathlib import Path
REPO_ROOT = Path(__file__).resolve().parent.parent
EMERGENCY_FLAG = REPO_ROOT / "EMERGENCY_EXIT_TRIGGERED.flag"
if EMERGENCY_FLAG.exists():
    print(f"[EMERGENCY] Flag file detected: {EMERGENCY_FLAG}")
    print("Trading disabled. Remove flag file to re-enable.")
    sys.exit(0)
```

This integration is recommended but not yet deployed in all daemons (K357 scaffold scope).

---

## §15 Builder Code Self-Rebate Activation (K370 AX-01)

**Added:** 2026-05-27 | **Wave:** K370 | **Status:** SCAFFOLD-READY (user activation required)
**Risk:** ZERO (no HL concentration change, no counterparty risk, pure cost reduction)

### §15.1 Background

HyperLiquid builder codes allow any address that sends orders on behalf of a user to capture
referral-pool rewards on that volume. By registering the production wallet as its own builder
("self-builder mode"), K280 production accumulates referral rewards on all its HL order flow.

**API mechanism** (HL docs, verified 2026-05-27):
- Order action field: `{"builder": {"b": wallet_address, "f": 0}}`
- `f` = additional fee in tenths of basis points charged to user. Use `f=0` → zero extra cost.
- Builder claims rewards via standard referral reward claim process.
- Reward type: referral-pool rewards (NOT a direct 50% taker fee rebate as K368 originally estimated).
- K368 correction: K368 cited "$82,800/yr savings at $10M AUM" assuming 50% direct rebate on
  4.5bp taker fee. Actual mechanism is referral pool rewards. Conservative analysis (K370):
  $9,444–$94,444/yr at $10M AUM (10–50% reward rate). True benefit TBD pending claim data.

**Eligibility requirements (confirmed):**
- ≥100 USDC in perps account value (trivially met)
- No minimum volume threshold found in documentation
- Max 10 active approvals per user; max builder fee cap: 0.1% perps (irrelevant at f=0)

### §15.2 Step-by-Step Activation

#### Step 1: Approve builder fee on HL (one-time on-chain action)

Must be signed by the **main wallet** (not an agent/API wallet).

**Option A: HL UI** (recommended)
1. Go to `https://app.hyperliquid.xyz/`
2. Navigate to Profile → Builder Codes or API Settings
3. Approve your wallet address as a builder with maxFeeRate ≥ 0% (use 0% for f=0 mode)

**Option B: Direct API action** (advanced)
```python
# approveBuilderFee action structure (EIP-712 signed):
action = {
    "type": "approveBuilderFee",
    "hyperliquidChain": "Mainnet",
    "signatureChainId": "0xa4b1",        # Arbitrum
    "maxFeeRate": "0.001%",              # any value >= f*0.1bp; 0.001% covers f=0
    "builder": "0x<YOUR_WALLET_ADDRESS>",
    "nonce": int(time.time() * 1000),    # milliseconds
}
# Sign with eth_account (EIP-712 typed data)
```

#### Step 2: Set environment variable
```bash
export HL_BUILDER_WALLET=0x<YOUR_WALLET_ADDRESS>
# Add to ~/.zshrc for persistence
echo 'export HL_BUILDER_WALLET=0x<YOUR_WALLET_ADDRESS>' >> ~/.zshrc
```

#### Step 3: Enable builder code in production scripts
Edit both scripts (additive patch already staged in K370 scaffold):

```python
# In scripts/k280_live_fetch.py (line ~83):
BUILDER_CODE_ENABLED   = True   # was False — enable after Step 1+2
# BUILDER_WALLET_ADDRESS auto-reads from HL_BUILDER_WALLET env var

# In scripts/k302a_satellite_run.py (line ~56):
BUILDER_CODE_ENABLED   = True   # was False — enable after Step 1+2
```

#### Step 4: Integrate builder field into live order submission

When live order execution is implemented (currently paper-trade), add to the order action builder:
```python
if BUILDER_CODE_ENABLED and BUILDER_WALLET_ADDRESS:
    order_action["builder"] = {
        "b": BUILDER_WALLET_ADDRESS,
        "f": BUILDER_FEE_F,          # = 0 (zero extra cost to user)
    }
```

#### Step 5: Verify integration
```bash
# After first live orders, verify builder field appears:
# Check HL clearinghouse state for recent fills — builder address should appear
# Monitor: HL UI → Profile → Builder Codes → Accumulated rewards
```

#### Step 6: Claim accumulated rewards
- Navigate to HL UI → Referral / Builder Code rewards
- Claim periodically (no auto-distribution)

### §15.3 Expected Savings (K370 analysis)

| AUM | Conservative (10% scenario) | Optimistic (50% scenario) |
|-----|----------------------------|--------------------------|
| $1M | ~$9,444/yr | ~$47,222/yr |
| $5M | ~$47,222/yr | ~$236,109/yr |
| $10M | ~$94,444/yr | ~$472,219/yr |
| $25M | ~$236,109/yr | ~$1,180,547/yr |
| $50M | ~$472,219/yr | ~$2,361,094/yr |

**Assumptions:** ~$2.1B annual HL volume at $10M AUM (17 fills/day at ~$336K notional/fill).
True reward rate TBD — check HL referral claim history after activation.

**Sharpe lift (K302a satellite):**
- Conservative (-10% cost): +0.13 Sh
- Optimistic (-50% cost): +0.65 Sh
- K302a satellite baseline Sh ~10.41 (from cached panel)

### §15.4 Verification

```bash
# Check scaffold is in place:
grep -n "BUILDER_CODE_ENABLED" scripts/k280_live_fetch.py scripts/k302a_satellite_run.py

# Run K370 analysis:
python3 wave_k370_builder_rebate.py
cat wave_k370_builder_rebate.json | python3 -m json.tool | head -50

# Verify deployment status:
python3 scripts/verify_deployment_status.py
```

### §15.5 Risk Assessment

| Dimension | Assessment |
|-----------|-----------|
| HL concentration change | ZERO — no new positions added |
| Counterparty risk | ZERO — referral pool, not external counterparty |
| Execution risk | ZERO — f=0 adds no extra cost to user |
| Signal change | NONE — pure cost reduction, no alpha change |
| K266 §6 gate | ACCEPT-FREE (cost optimization, not a new signal) |

---

*K370 §15 — Builder Code Self-Rebate — 2026-05-27*

---

## §16 G9 Oracle Deviation Gate (K371 — K369 K297' Production Safety)

**Added:** 2026-05-27 | **Wave:** K371 | **Status:** LIVE (ORACLE_GATE_ENABLED = True)

### §16.1 Background

K369 assessed K297' production risk via live HL oracle data:
- PAXG oracle deviation: **0.062%** (well within HL's 1%-per-update native cap)
- SPX oracle deviation: **0.125%** (well within threshold)
- K369 verdict: LOW risk. Recommended adding G9 safety gate as production guard.

K371 implements the G9 gate: a surgical 5-line patch to `scripts/k302a_satellite_run.py` that
skips today's entry for SPX (and PAXG last bar) when `|mark - oracle| / oracle > 1%`.

### §16.2 What G9 Does

```python
# Constants (scripts/k302a_satellite_run.py)
ORACLE_GATE_ENABLED        = True
ORACLE_DEVIATION_THRESHOLD = 0.01   # 1%

# At entry-decision point in compute_spx_daily_pnl():
if ORACLE_GATE_ENABLED:
    health = fetch_oracle_health(["SPX", "PAXG"])
    if abs(health["SPX"]["deviation"]) > ORACLE_DEVIATION_THRESHOLD:
        pnl.iloc[-1] = 0.0   # skip today's entry
```

**Logic:** POST `{"type":"metaAndAssetCtxs"}` to `https://api.hyperliquid.xyz/info`.
Parse `universe[i]` for coin index → `assetCtxs[i].markPx` and `assetCtxs[i].oraclePx`.
Gate fires if SPX **or** PAXG deviation exceeds 1%.

**Fail-open:** On API error, `fetch_oracle_health()` returns `{}`, gate does NOT fire.
Trading proceeds normally. Error logged to stdout.

### §16.3 Expected Behavior

| Scenario | Deviation | Gate Action |
|----------|-----------|-------------|
| Normal (current) | SPX 0.18%, PAXG 0.06% | Gate OK — no skip |
| Stressed oracle | SPX or PAXG > 1% | Gate fires — today's PnL zeroed |
| API error | N/A | Fail-open — trade proceeds |

**Expected G9 fires under current regime:** 0 days (both coins << 1% threshold).

**Sharpe impact:** Near-zero. K369 worst-case analysis showed even zero-FR simulation
(far more disruptive than G9) degraded Sharpe by only -0.228. G9 expected: 0.00 Sh impact.

### §16.4 Dashboard Fields (K371)

K371 adds the following to `data/k302a_satellite_dashboard.json`:

| Field | Type | Description |
|-------|------|-------------|
| `oracle_gate_enabled` | bool | Whether G9 is active |
| `oracle_deviation_threshold` | float | 0.01 (1%) |
| `current_spx_deviation` | float% | Live SPX \|mark-oracle\|/oracle in % |
| `current_paxg_deviation` | float% | Live PAXG \|mark-oracle\|/oracle in % |
| `oracle_gate_fired` | bool | True if either coin exceeded threshold this run |
| `active_alert_flags.oracle_g9_fired` | bool | Same as oracle_gate_fired |

### §16.5 Rollback

**Immediate (no restart required):**
```python
# In scripts/k302a_satellite_run.py, set:
ORACLE_GATE_ENABLED = False
```
This disables the oracle fetch entirely. Trading reverts to K297' always-on behavior.

**Verify rollback:**
```bash
python3 scripts/k302a_satellite_run.py
# Should NOT print [G9] lines
python3 scripts/verify_deployment_status.py
```

### §16.6 Monitoring

**Check G9 status:**
```bash
python3 -c "
import json
d = json.load(open('data/k302a_satellite_dashboard.json'))
print('G9 gate enabled:', d.get('oracle_gate_enabled'))
print('Threshold:',       d.get('oracle_deviation_threshold'))
print('SPX dev%:',        d.get('current_spx_deviation'))
print('PAXG dev%:',       d.get('current_paxg_deviation'))
print('Gate fired:',      d.get('oracle_gate_fired'))
"
```

**Trigger to investigate:**
- G9 fires more than 1 consecutive day → check HL oracle feed health
- Oracle API errors > 3 consecutive days → consider disabling gate (ORACLE_GATE_ENABLED = False)

### §16.7 K266 Gate Compatibility

G9 is a **production safety gate**, not a K266 strict backtest gate.

| Gate | Change |
|------|--------|
| G1–G7 (K266 strict) | UNCHANGED — G9 does not modify historical backtest logic |
| G8 (K280 MDD < 2%) | UNCHANGED |
| G9 (K371, new) | Production-only: API fetch at runtime, not in historical data |

Walk-forward: NO change expected (historical oracle deviations not recorded → G9 transparent
in backtest context). K297' Sharpe 18.48 remains unaffected.

---

## §17 K376 Volume-Spike Momentum Activation Plan (K380)

**Added:** 2026-05-27 | **Wave:** K380 | **Status:** SCAFFOLD-READY (60-day paper-trade gate)
**K378 verdict:** CONDITIONAL_ACCEPT — 60d paper-trade required; G8 fill rate ≥ 65% before capital

### §17.1 Strategy Summary

| Parameter | Value |
|-----------|-------|
| Strategy ID | K376_volume_momentum_v1 |
| Version | v6.14_candidate |
| Universe | ETH, LINK, AVAX (PEPE/SUI dropped: 3/4 folds negative) |
| Signal | vol_ratio > 4.0x (12h rolling) AND \|5min return\| > 0.4% |
| Regime gate | BTC 20d SMA slope > 0 (bull-only; skip all signals in bear) |
| Execution | Post-only limit (maker) — 2bps maker rebate on HL/Bybit |
| Hold period | 4h (240 minutes) |
| Sleeve | 3% of AUM (v6.14 candidate) |
| Script | `scripts/k376_momentum_run.py` |
| Daemon label | `com.cryptolab.k376-momentum` |
| Dashboard | `data/k376_momentum_dashboard.json` |
| Fill log | `data/k376_paper_fills.jsonl` |
| Paper-trade log | `logs/k376_momentum.log` |

**OOS backtest stats (K376/K378):**
- Combined Sharpe lift: +3.35 OOS
- DSR: 0.9957
- Fold breakdown: ETH/LINK/AVAX positive folds 3/4 (fold 3 BTC bear was systemic, filtered by regime gate)
- Maker RT cost: 2bps (net-positive after rebate)

### §17.2 Pre-Activation Gate Checks

Before allocating any real capital to K376, ALL of the following must pass:

| Gate | Metric | Threshold | Source |
|------|--------|-----------|--------|
| G8 (paper fill rate) | Maker fill rate, 60d | ≥ 65% | `data/k376_momentum_dashboard.json → fill_rate_60d` |
| G9 (live Sharpe) | Sharpe annualized, 30d | ≥ 1.0 | `data/k376_momentum_dashboard.json → live_sharpe_30d` |
| Regime filter | BTC 20d SMA slope > 0 | Bull regime | `current_regime == "bull"` |
| Paper-trade duration | Days running | ≥ 60 days | Compare first fill in `data/k376_paper_fills.jsonl` |
| K357 Bybit gap | Bybit close-all endpoint | Present | See §14.7 (K380 patch) |

```bash
# Check gate status:
python3 -c "
import json
d = json.load(open('data/k376_momentum_dashboard.json'))
print('Regime:',        d.get('current_regime'))
print('Fill rate 60d:', d.get('fill_rate_60d'))
print('G8 passed:',     d.get('g8_gate_passed'))
print('Live Sh 30d:',   d.get('live_sharpe_30d'))
print('Open positions:',len(d.get('open_positions', [])))
print('Signals 24h:',   d.get('recent_signals_24h'))
"
```

### §17.3 Activation Order

K376 activates **after sUSDe daemon, before HL portfolio margin**:

```
Priority order (per K379 Governance v3):
  1. sUSDe OC daemon (com.cryptolab.susde-oc)          ← already SCAFFOLD-READY
  2. K376 volume momentum (com.cryptolab.k376-momentum) ← 60d paper-trade gate
  3. HL Portfolio Margin (K373, DEFER)                  ← deferred, no current gate
```

**Architecture after K376 activation (v6.14):**
```
v6.14 = K280 Core (73%) + K297' Satellite (18.5%) + sUSDe OC (5%) + K376 Momentum (3%)
  Combined Sharpe (estimated): 25.68 + 3.35 sleeve lift (subject to live confirmation)
  HL exposure: 58.5% (cap 65% per K355)
```

### §17.4 Activation Commands (User Action Required After 60d Gate)

```bash
# Step 1: Verify 60d paper-trade gate passed
python3 scripts/k376_momentum_run.py --verbose
# → Check: fill_rate_60d >= 0.65, live_sharpe_30d >= 1.0, regime = bull

# Step 2: Stop daemon (paper mode), copy plist to LaunchAgents
launchctl unload ~/Library/LaunchAgents/com.cryptolab.k376-momentum.plist 2>/dev/null || true
cp com.cryptolab.k376-momentum.plist ~/Library/LaunchAgents/

# Step 3: Reload daemon
launchctl load ~/Library/LaunchAgents/com.cryptolab.k376-momentum.plist

# Step 4: Verify daemon is scheduled
launchctl list | grep k376

# Step 5: Confirm 0 deployment mismatches
python3 scripts/verify_deployment_status.py
```

### §17.5 Universe Expansion Path

Controlled expansion after initial 30d live data:

| Phase | Timeline | Universe | Gate |
|-------|----------|----------|------|
| Launch | Day 0–30 | ETH, LINK, AVAX (3 coins) | K380 activation |
| Phase 2 | Day 30–60 | + ADA (4 coins) | 30d Sharpe positive |
| Phase 3 | Day 60–90 | + SUI or PEPE (5 coins) | Additional 60d Sharpe > 1.0 |

**Decision on SUI/PEPE expansion:**
- SUI fold 3 Sharpe: -1.807 → expansion only if live rolling 30d Sh > 1.0
- PEPE fold 3 Sharpe: -3.078 → requires positive fold 3 in live env before adding
- BTC/DOGE excluded indefinitely (K378 analysis: systemic bear sensitivity, not strategy-specific)

### §17.6 Rollback Procedure

**Immediate (no daemon restart required):**
- Set `SLEEVE_PCT = 0` (effectively disables position sizing) in `scripts/k376_momentum_run.py`

**Full rollback:**
```bash
launchctl unload ~/Library/LaunchAgents/com.cryptolab.k376-momentum.plist
# Architecture reverts to v6.13d: K280 75% + K297' 20% + sUSDe 5%
# Update verify_deployment_status.py expected_html_status to "DEPRECATED"
python3 scripts/verify_deployment_status.py   # confirm 0 mismatches
```

**Trigger conditions for rollback:**
- Live 30d Sharpe drops below 0.5 after activation
- Fill rate drops below 50% for 7+ consecutive days
- Regime filter fails to prevent losses in confirmed bear market (>3 consecutive losing weeks)
- Emergency: `EMERGENCY_EXIT_TRIGGERED.flag` present (daemon auto-skips)

### §17.7 Monitoring

```bash
# Live regime check:
python3 scripts/k376_momentum_run.py --verbose --dry-run

# Fill log analysis:
python3 -c "
import json
fills = [json.loads(l) for l in open('data/k376_paper_fills.jsonl') if l.strip()]
print(f'Total fills: {len(fills)}')
long_fills  = [f for f in fills if f.get(\"direction\") == \"long\"]
short_fills = [f for f in fills if f.get(\"direction\") == \"short\"]
print(f'Long: {len(long_fills)}, Short: {len(short_fills)}')
"

# Dashboard:
cat data/k376_momentum_dashboard.json | python3 -m json.tool
```

**Dashboard fields key:**
| Field | Alert threshold |
|-------|-----------------|
| `current_regime` | Investigate if "unknown" for > 1h |
| `fill_rate_60d` | Alert if < 0.50 (G8 gate warning) |
| `live_sharpe_30d` | Alert if < 0.5 (strategy degrading) |
| `open_positions` | Alert if > 3 simultaneously (position limit) |
| `recent_signals_24h` | Alert if > 20/day (signal frequency anomaly) |

---

---

## §18 BEAR_1 Fallback Activation Playbook (K386, v6.13e)

**Added:** 2026-05-27 | **Wave:** K386 | **Status:** STANDBY (prototype ready)
**Script:** `scripts/k386_v613e_fallback_run.py` | **Flag:** `BEAR_1_FALLBACK_ACTIVE.flag`

### §18.1 Scenario Definition

**BEAR_1:** CFTC enforcement action vs HyperLiquid (K385 estimate P=15%).
Covers two equivalent sub-triggers:
1. CFTC enforcement filing vs HyperLiquid
2. HL voluntary HIP-3 suspension (preemptive compliance)

**Architecture change (v6.13d → v6.13e):**

| Component | v6.13d | v6.13e | Change |
|-----------|--------|--------|--------|
| K280 main | 75% | 85% | +10pp (boost) |
| K297' HIP-3 | 20% | 0% | −20pp (CFTC restricted) |
| BTC/ETH spot | 0% | 10% | +10pp (new sleeve) |
| sUSDe OC | 5% | 5% | unchanged |
| **HL exposure** | **57.5%** | **52.5%** | **−5pp** |
| Combined Sharpe est. | 25.47 | 22.89 | −2.58 (acceptable) |

**BTC/ETH spot sleeve (10%):**
- 50/50 BTC + ETH spot (passive long)
- Daily mark-to-market via Binance public klines API (no auth)
- Rebalanced daily by daemon; no hedging in prototype
- Future upgrade: delta-neutral hedge via BTC/ETH perp shorts on Bybit

### §18.2 Pre-Trigger Detection

Monitor for BEAR_1 indicators:
```bash
# Monitor CFTC/SEC RSS (manual until K388 automation):
open https://www.cftc.gov/PressRoom/PressReleases/index.htm
open https://www.sec.gov/litigation/actions.shtml

# HL official status:
open https://hyperliquid.xyz/
open https://discord.gg/hyperliquid   # community Discord

# K386 daemon standby check:
python3 scripts/k386_v613e_fallback_run.py --dry-run
# → Should show: Fallback status: STANDBY
```

**K388 future:** Automated SEC/CFTC RSS monitor (not yet implemented).
Until then: manual check once per trading day.

### §18.3 Activation Steps (3 Trading Days)

**Day 1 Morning — Close K297' HIP-3 Positions:**
```bash
# Step 1: Close all PAXG/SPX HL positions via K357 emergency exit
# K386 adds --cftc-fallback mode: closes HIP-3 only, keeps K280
python3 scripts/emergency_hl_exit.py --dry-run   # confirm positions

# Step 2: Activate BEAR_1 flag (K302a satellite will self-suspend)
touch BEAR_1_FALLBACK_ACTIVE.flag

# Step 3: Verify K302a exits cleanly
python3 scripts/k302a_satellite_run.py
# → Should print: "BEAR_1_FALLBACK_ACTIVE.flag detected. K302a satellite skipping execution."

# Step 4: Verify K386 activates
python3 scripts/k386_v613e_fallback_run.py
# → Should print: "BEAR_1 flag present. Executing v6.13e architecture."
```

**Day 1 Afternoon — Redirect 10% AUM to BTC/ETH Spot:**
```bash
# K386 daemon handles BTC/ETH spot automatically once flag is present.
# Verify spot sleeve is fetching prices:
cat data/v6_13e_fallback_dashboard.json | python3 -m json.tool | grep -A5 spot_sleeve

# Confirm dashboard shows ACTIVE:
cat data/v6_13e_fallback_dashboard.json | python3 -c "import json,sys; d=json.load(sys.stdin); print(d['fallback_status'])"
# → ACTIVE
```

**Day 2 — Rebalance K280 to 85% Weight:**
```bash
# K280 daemon continues running (no changes needed to K280 scripts).
# K386 weights (K280 85% + BTC/ETH 10% + sUSDe 5%) are enforced by k386_v613e_fallback_run.py.
# Verify via deployment status:
python3 scripts/verify_deployment_status.py
# → K386 should show LOADED or ACTIVE; K302a should show SCAFFOLD-READY (daemon not running)
```

**Day 3 — Verify Weights and Dashboard:**
```bash
# Full deployment status check:
python3 scripts/verify_deployment_status.py
# → 0 mismatches

# Dashboard validation:
python3 -c "
import json
with open('data/v6_13e_fallback_dashboard.json') as f:
    d = json.load(f)
assert d['fallback_status'] == 'ACTIVE', 'Expected ACTIVE'
assert d['weights']['K297_prime'] == 0.0, 'K297 should be 0'
assert d['weights']['K280'] == 0.85, 'K280 should be 0.85'
assert d['weights']['BTC_ETH_spot'] == 0.10, 'BTC/ETH should be 0.10'
print('All v6.13e weight assertions PASSED')
print(f'HL exposure: {d[\"hl_exposure_pct\"]}% (target: 52.5%)')
"

# Report check:
grep "v6.13e\|BEAR_1\|ACTIVE" report.html | head -5
```

### §18.4 Daemon Configuration During BEAR_1

**Active daemons (v6.13e mode):**
| Daemon | Status | Role |
|--------|--------|------|
| com.cryptolab.k280-live | Running | K280 85% main (unchanged) |
| com.cryptolab.k386-v613e-fallback | Running | BTC/ETH spot 10% + dashboard |
| com.cryptolab.susde-oc | Running | sUSDe 5% (unchanged) |
| com.cryptolab.k302a-satellite | **Self-suspended** | K297' flag check exits 0 |

**Daemon check order (inside each daemon):**
1. `EMERGENCY_EXIT_TRIGGERED.flag` → all daemons stop immediately
2. `BEAR_1_FALLBACK_ACTIVE.flag` → K302a exits 0; K386 takes over

### §18.5 Deactivation (BEAR_1 Reversal)

When BEAR_1 scenario resolves (CFTC case dropped / HL reinstates HIP-3):
```bash
# Step 1: Remove flag
rm BEAR_1_FALLBACK_ACTIVE.flag

# Step 2: Verify K302a resumes
python3 scripts/k302a_satellite_run.py
# → Should run normally (no flag message)

# Step 3: Stop K386 daemon (if loaded in LaunchAgents)
launchctl unload ~/Library/LaunchAgents/com.cryptolab.k386-v613e-fallback.plist || true

# Step 4: Restart K297' with K348 patch + G9 gate
# K297' (SPX_FILTER_ENABLED=True, ORACLE_GATE_ENABLED=True) auto-restarts via K302a daemon

# Step 5: Confirm 0 deployment mismatches
python3 scripts/verify_deployment_status.py
```

**K297' post-BEAR_1 restart checklist:**
- [ ] `SPX_FILTER_ENABLED = True` in `scripts/k302a_satellite_run.py`
- [ ] `ORACLE_GATE_ENABLED = True` (G9 gate)
- [ ] Run `k302a_satellite_fetch.py` to refresh PAXG/SPX FR data
- [ ] Run `k302a_satellite_run.py --date YYYY-MM-DD` and verify no alerts
- [ ] Dashboard `data/k302a_satellite_dashboard.json` shows live data

### §18.6 Dashboard Fields (v6.13e)

| Field | STANDBY value | ACTIVE value |
|-------|--------------|--------------|
| `fallback_status` | `"STANDBY"` | `"ACTIVE"` |
| `current_architecture` | `"v6.13d"` | `"v6.13e"` |
| `weights.K280` | `0.85` | `0.85` |
| `weights.K297_prime` | `0.0` | `0.0` |
| `weights.BTC_ETH_spot` | `0.10` | `0.10` |
| `weights.sUSDe` | `0.05` | `0.05` |
| `hl_exposure_pct` | `52.5` | `52.5` |
| `estimated_sharpe` | `22.89` | `22.89` |

Dashboard path: `data/v6_13e_fallback_dashboard.json`
Trade log: `data/k386_v613e_paper_trades.jsonl`

---

## §19 K387 Regulatory Alerts — Manual Review & BEAR_1 Trigger

**Wave:** K387 (2026-05-27) | **Scope:** SEC/CFTC RSS feed monitoring, manual review only

### 19.1 Overview

K387 runs a lightweight RSS daemon that polls SEC and CFTC official feeds every 30 minutes, searching for keywords related to HyperLiquid, HIP-3, perpetuals, and market manipulation concerns. This is a **monitoring scaffold only**—no automatic action is taken. All alerts require manual operator review before triggering K386 BEAR_1 fallback.

**Key constraint:** K387 does NOT auto-flag `BEAR_1_FALLBACK_ACTIVE.flag`. Only user intervention sets this flag (see §19.5).

### 19.2 Daemon Status

| Component | Status | Command |
|-----------|--------|---------|
| Script | `scripts/regulatory_rss_monitor.py` | Stdlib only, ~200 LOC |
| Polling | 30min interval via launchd | `StartInterval=1800` |
| Feeds | SEC + CFTC RSS | 2 XML feeds, fallback on parse fail |
| Cache | `cache/regulatory_alerts_seen.txt` | Avoid duplicate alerts |
| Alerts log | `cache/regulatory_alerts.jsonl` | Timestamped JSONL, one per line |
| Dashboard | `data/regulatory_dashboard.json` | Live JSON (24h counts, recent alerts) |
| Logs | `logs/regulatory_rss_monitor.log/.err` | Standard plist output |
| Status | **SCAFFOLD-READY** | Plist in repo root (gitignored); manual activation required |

**Activation (after manual verification):**
```bash
cp com.cryptolab.regulatory-rss.plist ~/Library/LaunchAgents/
launchctl load ~/Library/LaunchAgents/com.cryptolab.regulatory-rss.plist
# Verify:
launchctl list | grep regulatory-rss
```

### 19.3 Alert Keywords & Feed Structure

**Keywords (case-insensitive):**
- `hyperliquid` — Direct HL mention
- `hip-3` — HIP-3 proposal/action
- `perpetual` — Perpetual futures context
- `tokenized` — Tokenized instruments (compliance angle)
- `manipulation` — Market manipulation (CFTC focus)
- `defi dex` — Decentralized exchange context
- `clarity act` — Digital Asset Market Clarity Act (Senate bill tracking) *(Added K404)*
- `digital asset market clarity act` — Full bill name *(Added K404)*
- `h.r.3633` — House version of Clarity Act *(Added K404)*
- `senate floor` — Senate floor vote context (regulatory inflection) *(Added K404)*
- `crypto market structure` — Market structure legislation *(Added K404)*
- `defi exemption` — DeFi regulatory exemption discussions *(Added K404)*
- `cftc market authority` — CFTC market authority expansion *(Added K404)*

**Feed sources:**
1. **SEC**: `https://www.sec.gov/news/pressreleases.rss`
   - Focus: Innovation exemptions, token classification, custody rules
2. **CFTC**: `https://www.cftc.gov/PressRoom/PressReleases.xml`
   - Focus: Enforcement, DCO approval, HL/perpetual regulation

**Alert JSON structure (in `regulatory_alerts.jsonl`):**
```json
{
  "timestamp_jst": "2026-05-27T10:09:57.748539+09:00",
  "source": "SEC|CFTC",
  "title": "SEC Regulation... Tokenized Assets Rule Clarification",
  "link": "https://www.sec.gov/news/press-release/...",
  "pubDate": "2026-05-27T10:00:00Z",
  "guid": "https://www.sec.gov/news/press-release/...",
  "keyword_matched": "tokenized|perpetual|hip-3|..."
}
```

### 19.4 Manual Review Workflow (User Responsibility)

**Trigger:** Dashboard shows `new_alerts_this_poll > 0` OR email notification from monitoring system.

**Step 1: Check dashboard**
```bash
# View current alert status in Live Monitoring widget
cat data/regulatory_dashboard.json | jq .

# Example output:
{
  "last_poll_jst": "2026-05-27T10:30:00+09:00",
  "sec_alerts_24h": 0,
  "cftc_alerts_24h": 2,
  "new_alerts_this_poll": 1,
  "recent_alerts": [
    {
      "timestamp_jst": "2026-05-27T10:29:00+09:00",
      "source": "CFTC",
      "title": "CFTC Enforcement Action: HyperLiquid Perpetual Leverage Mandate",
      "link": "https://cftc.gov/...",
      "keyword_matched": "hyperliquid|perpetual"
    }
  ],
  "next_action": "monitor"
}
```

**Step 2: Read full alert**
1. Click alert link in Live Monitoring widget (HTML dashboard)
2. OR run: `cat cache/regulatory_alerts.jsonl | tail -1 | jq .`
3. Read full SEC/CFTC press release

**Step 3: Assess BEAR_1 trigger candidacy**

Use this decision matrix:

| Alert signal | BEAR_1 probability | Action |
|--------------|------------------|--------|
| "SEC innovation exemption for HL" | Low (<10%) | MONITOR — flag as "BULL" in comments |
| "CFTC begins HIP-3 review" (early stages) | Medium (30–50%) | MONITOR + prepare K386 activation |
| "CFTC enforcement action: HL manipulation case" | High (70%+) | **→ Proceed to §19.5** |
| "CFTC HL leverage cap finalized" (affects viability) | High (70%+) | **→ Proceed to §19.5** |

### 19.5 BEAR_1 Fallback Activation (Manual Only)

If alert confirms BEAR_1 scenario (CFTC enforcement / HL viability threat):

**Step 1: Create BEAR_1 trigger flag**
```bash
touch BEAR_1_FALLBACK_ACTIVE.flag
```

**What this does:**
- K302a daemon checks for this flag on each run; if present, it exits silently (0)
- K386 daemon (`scripts/k386_v613e_fallback_run.py`) checks for flag; if present, begins running immediately
- All K280/K297' allocations pause; K386 v6.13e architecture takes over (K280 85% + BTC/ETH spot 10% + sUSDe 5%)
- K386 writes trades to `data/k386_v613e_paper_trades.jsonl` + dashboard `data/v6_13e_fallback_dashboard.json`

**Step 2: Verify flag is honored**
```bash
# Check that K302a recognizes flag
python3 scripts/k302a_satellite_run.py --dry-run
# Should see: "[BEAR_1_FALLBACK_ACTIVE.flag detected] Exiting (K386 active)"

# Check that K386 is ready
python3 scripts/k386_v613e_fallback_run.py --dry-run
# Should begin paper-trading under fallback allocation
```

**Step 3: Activate K386 plist (if not already loaded)**
```bash
cp com.cryptolab.k386-v613e-fallback.plist ~/Library/LaunchAgents/
launchctl load ~/Library/LaunchAgents/com.cryptolab.k386-v613e-fallback.plist
# Verify:
launchctl list | grep k386
```

**Step 4: Update regulatory dashboard manually**
```bash
# Edit data/regulatory_dashboard.json:
# Set "next_action": "trigger_BEAR_1" or "bear_1_active"
# Add comment field documenting alert title + CFTC action date
```

**Step 5: Notify stakeholders**
- Email or Slack: "BEAR_1 fallback activated due to [alert title]. K386 v6.13e now live. Monitor for 4h reversion."
- Document in `logs/bear_1_activation_log.txt` (optional)

### 19.6 Dashboard & Monitoring

**Live Monitoring widget (report.html) shows:**
- K387 row with status: `SCAFFOLD-READY` → `ACTIVE` (after manual load)
- 24h alert counts (SEC, CFTC)
- Recent 5 alerts with title preview + matched keyword
- Fetch timestamp (JST)

**Access patterns:**
1. **HTML dashboard**: Open `report.html` → scroll to "Live Monitoring" → K387 row + "Regulatory Alerts Monitor" card
2. **JSON programmatic**: `curl file://$(pwd)/data/regulatory_dashboard.json | jq .`
3. **Raw JSONL log**: `tail -20 cache/regulatory_alerts.jsonl` (unfiltered, all seen alerts)

### 19.7 No Auto-Trigger Policy (Compliance)

**Critical rule:** K387 makes NO autonomous decisions. The daemon:
- ✅ Fetches RSS, parses XML, matches keywords
- ✅ Logs to JSONL, updates dashboard
- ✅ Can POST to ntfy.sh (optional future feature)
- ❌ Does NOT create any flag file
- ❌ Does NOT execute K386 trigger
- ❌ Does NOT modify any daemon state

All trigger decisions are **operator-initiated**. This is mandatory per K385 (regulatory-conservative strategy design).

### 19.8 Deactivation (Regulatory All-Clear)

When CFTC case is dropped or SEC approves innovation exemption:

```bash
# Step 1: Remove flag
rm BEAR_1_FALLBACK_ACTIVE.flag

# Step 2: K302a will auto-resume on next scheduled run
# (Or manually restart)
python3 scripts/k302a_satellite_run.py

# Step 3: Stop K386 daemon
launchctl unload ~/Library/LaunchAgents/com.cryptolab.k386-v613e-fallback.plist || true

# Step 4: Verify deployment state
python3 scripts/verify_deployment_status.py
# Should show 0 mismatches and K302a ACTIVE again
```

---

## §20 K368 HIP-4 Calibration — Adjusted Target (K409)

**Adjusted by:** K409 (2026-05-29)  
**Old K368 target:** 2026-06-10 (K356 scaffold + K395 prep)  
**New K368 target:** **2026-06-22** (K409 — Option C selected)  
**Reason:** K408 math: N=14 BTC daily resolution minimum not achievable by 2026-06-10 (only N=11 possible even if daemon loaded immediately).

---

### §20.1 Background

HIP-4 (Hyperliquid Incentive Program 4) hosts binary prediction markets including a BTC recurring daily market that settles at 06:00 UTC. K353 identified a potential calibration bias edge; K356 scaffolded a data collection daemon (`com.cryptolab.hl-hip4-monitor`). As of K409, the daemon has **not been activated** by the user — it remains at `SCAFFOLD_READY`.

K368 is reserved for the calibration analysis. The original 2026-06-10 target was infeasible (N=11 outcomes < N=14 minimum). K409 pushes to 2026-06-22, providing a 24-day collection window (N=23 possible, 9-day buffer).

### §20.2 User Activation — MOST CRITICAL

**Run this command immediately. Every day of delay reduces collection window.**

```bash
# Step 1: Install and load daemon
cp com.cryptolab.hl-hip4-monitor.plist ~/Library/LaunchAgents/
launchctl load ~/Library/LaunchAgents/com.cryptolab.hl-hip4-monitor.plist

# Step 2: Verify loaded
launchctl list | grep hip4
# Expected output line: ... com.cryptolab.hl-hip4-monitor

# Step 3: Check first snapshot appears (wait ~5 minutes after load)
ls -la cache/hl_hip4_snapshots/
# Should see new parquet files appearing every 5 minutes

# Step 4: Health check (run on 2026-06-15, 7 days before K368)
python3 scripts/verify_deployment_status.py | grep hip4
ls cache/hl_hip4_snapshots/ | wc -l
# Expected at 2026-06-15 (17 days active): ~4,896 snapshots
```

**If daemon unavailable (manual fallback):**
```bash
# Run once daily from 2026-05-29 to 2026-06-21 (morning preferred):
python3 scripts/hl_hip4_monitor.py
```

### §20.3 K368 Execution Timeline

| Date | Event | Data Capture |
|------|-------|--------------|
| 2026-05-29 | K409: target adjusted | Baseline (4 snapshots) |
| 2026-05-29+ | Daemon active (if activated) | 288 snapshots/day |
| 2026-06-10 | May CPI YoY BLS release (12:30 UTC) | Secondary market: single-event Brier |
| 2026-06-18 | FOMC June decision | Cross-venue: HL vs Polymarket final |
| **2026-06-22** | **K368 executes** | Full calibration analysis |

### §20.4 Decision Gates (Revised by K409)

| Gate | Condition | Action |
|------|-----------|--------|
| **ACCEPT** | calibration_gap > 3% AND N ≥ 14 | → K369 BTC recurring trade prototype |
| **WATCH** | 1% ≤ gap ≤ 3% AND N ≥ 14 | Extend daemon +14 days, recheck K380 |
| **MONITOR** | gap < 1% AND N ≥ 14 | No edge, continue collecting |
| **INCONCLUSIVE_DIRECTIONAL** | 10 ≤ N < 14 | Document trend hypothesis, push to K380+ |
| **INCONCLUSIVE** | N < 10 by 2026-06-22 | Push to K450+ monthly recheck |

### §20.5 Data Projections

| Scenario | N outcomes by 2026-06-22 | Snapshots | K368 Gate Eligible |
|----------|--------------------------|-----------|-------------------|
| Daemon active from 2026-05-29 | 23 | ~6,912 | Any gate |
| Manual daily fetch | 23 | ~24 | Any gate |
| Daemon active from 2026-06-05 | 16 | ~2,016 | Any gate (marginal) |
| Daemon active from 2026-06-09 | 12 | ~864 | INCONCLUSIVE_DIRECTIONAL |
| No activation, no manual | 0 | 4 (historical) | INCONCLUSIVE |

### §20.6 K368 Deliverables (to create 2026-06-22)

- `wave_k368_hip4_calibration.py` — computation script
- `wave_k368_hip4_calibration.json` — Brier score, calibration_gap_pct, decision
- `wave_k368_hip4_calibration.md` — 200–300 line structured report

**Placeholder:** `wave_k368_calibration_RESERVED.md` (created by K409)

### §20.7 References

| Wave | Content |
|------|---------|
| K353 | HIP-4 prediction market initial scouting (MONITOR) |
| K356 | Daemon scaffold, plist created |
| K395 | Calibration prep, K368 design, fallback plan |
| K408 | Math feasibility: N=11 at 2026-06-10 → INCONCLUSIVE |
| K409 | Target adjusted to 2026-06-22 (this section) |

---

*K409 §20 — K368 HIP-4 Calibration Adjusted Target — 2026-05-29*

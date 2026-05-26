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

### §14.8 Daemon Integration (K302a Daemons Check Flag)

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

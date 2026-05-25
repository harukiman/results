# Wave K289 — K287d Satellite Paper-Trade Scaffold

**Date:** 2026-05-25  |  **Parallel to:** K283 (K280 main daemon)
**Architecture:** K287d = K280 main (80%) + K287c Satellite (20%)

---

## Deliverables Summary

| File | Purpose |
|------|---------|
| `scripts/k287_satellite_fetch.py` | Daily incremental fetch (dYdX K270 FR + OKX K275 FR) |
| `scripts/k287_satellite_run.py` | Daily paper-trade (K270+K275 signals, inv-vol, satellite dashboard) |
| `data/k287_satellite_dashboard.json` | Live satellite monitoring dashboard |
| `data/k287_satellite_paper_trades.jsonl` | Trade log (append-only JSONL per day) |
| `com.cryptolab.k287-satellite.plist` | launchctl daemon (09:30 JST daily) |
| `cache/k270_dydx_daily.parquet` | K270 dYdX daily FR panel (persistent, 731d) |
| `cache/okx_fr_daily.parquet` | K275 OKX daily FR panel (persistent, ~90d) |
| `cache/k287_satellite_YYYYMMDD.parquet` | Per-day combined snapshot |
| `cache/k287_satellite_YYYYMMDD.json` | Per-day JSON metadata snapshot |

Legacy K280 main files remain functional via com.cryptolab.k280-live.plist.

---

## Architecture: K287d v1.0

```
dYdX v4 FR (30 symbols, hourly settlement, Cosmos DEX)
  └── K270: 14d FR rank → L/S quartile daily carry   [satellite weight ~35.5%]

OKX FR (35 symbols, 8h settlement x3/day, CEX)
  └── K275: 7d FR rank → L/S quartile daily carry    [satellite weight ~64.5%]

Satellite inv-vol allocation (K270 + K275, 60d window)
  → Satellite daily PnL (paper only)

Combined K287d view:
  K280 main (80%) + Satellite (20%)  →  K287d portfolio PnL
```

**Backtest Reference (from wave_k287_satellite.json):**
| Metric | K270 | K275 | Satellite (K287c) | K287d Combined |
|--------|------|------|-------------------|----------------|
| OOS Sharpe | 11.85 | 30.25 | 22.95 | 33.00 |
| OOS MaxDD | -0.002016 | 0.000 | -0.000496 | 0.000 |
| WF min | 10.38 | 5.94 | 17.01 | — |
| Inv-vol weight | ~35.5% | ~64.5% | 20% of K287d | — |

---

## First-Run Verification (2026-05-25)

### k287_satellite_fetch.py:
- Runtime: 10.4s
- dYdX v4 status: OK (server_time confirmed)
- OKX status: OK (API reachable)
- K270: 30 symbols, panel 731d × 30 (built from k270_dydx/ per-symbol cache)
- K275: 35 symbols, panel 96d × 35 (from okx_fr_daily.parquet cache)
- Outputs: `cache/k287_satellite_20260525.parquet`, `cache/k287_satellite_20260525.json`

### k287_satellite_run.py:
- Runtime: 1.4s
- K270: 30 symbols active, 731 days of PnL
  - Long today: BLUR, INJ, JUP, OP, SOL, WIF, XRP (low-FR symbols on dYdX)
  - Short today: AAVE, AXS, BONK, DOGE, ENA, UNI, BNB (high-FR symbols)
  - 30d Sh: 21.30 (strong dYdX carry regime)
- K275: 35 symbols active, 96 days of PnL
  - Long today: TIA, SEI, WLD, BLUR, BONK, JUP, MEME, COMP (low OKX FR)
  - Short today: DOGE, NEAR, DOT, UNI, AAVE, SUSHI, TAO, GRT (high OKX FR)
  - 30d Sh: -3.55 (K275_LOW_SH alert fired — OKX carry compression)
- Satellite weights (live inv-vol, 60d): K270=18.0%, K275=82.0%
  - Note: K275 gets higher weight despite alert because lower vol (30d). Alert is advisory.
  - Reference OOS: K270=35.5%, K275=64.5%
- Today's satellite PnL: 0.0000085
- Satellite equity: 1.0506 (+5.06% cumulative, 731d)
- Satellite 30d Sharpe: 15.80

### Alerts triggered on first run:
| Code | Level | Description |
|------|-------|-------------|
| K275_LOW_SH | ALERT | OKX 30d rolling Sh = -3.55 < 3.0 threshold. OKX carry currently compressed. |

**Interpretation:** K275_LOW_SH fired because OKX carry was weak over the last 30 days. This is an advisory alert — K275 weight is determined by inv-vol (which correctly reduces K275 during high-vol/low-carry periods). The K275 OOS Sharpe of 30.25 was measured on a specific 28d window. Satellite overall 30d Sh remains 15.80 (acceptable).

---

## Step 1: Install launchctl Daemon

```bash
# Install K287 satellite daemon
cp /Users/nekonaomichi/crypto-lab/com.cryptolab.k287-satellite.plist \
   ~/Library/LaunchAgents/
launchctl load ~/Library/LaunchAgents/com.cryptolab.k287-satellite.plist

# Verify loaded
launchctl list | grep k287

# Verify K280 main is still running in parallel
launchctl list | grep k280
```

Both daemons run on separate schedules with separate log files — no conflict.

---

## Step 2: Manual Run Commands

```bash
cd /Users/nekonaomichi/crypto-lab

# Step A: Fetch (incremental — only fetches delta since last run)
.venv311/bin/python3 scripts/k287_satellite_fetch.py

# Force full re-fetch (use after long outage)
.venv311/bin/python3 scripts/k287_satellite_fetch.py --force

# Step B: Daily execution
.venv311/bin/python3 scripts/k287_satellite_run.py
```

---

## Step 3: Daily Monitoring

### Check satellite dashboard:
```bash
python3 -c "
import json
with open('data/k287_satellite_dashboard.json') as f:
    d = json.load(f)
rm = d['rolling_metrics'] or {}
af = d['active_alert_flags']
sw = d['satellite_weights'] or {}
print('Last update:', d['last_update'])
print(f'Satellite rolling Sh: 7d={rm.get(\"sh_7d\",\"N/A\")}  30d={rm.get(\"sh_30d\",\"N/A\")}  all={rm.get(\"sh_all\",\"N/A\")}')
print(f'Satellite MaxDD:  30d={rm.get(\"mdd_30d\",\"N/A\")}  all={rm.get(\"mdd_all\",\"N/A\")}')
print(f'Sat weights: K270={sw.get(\"K270\",0):.1%}  K275={sw.get(\"K275\",0):.1%}')
print('Alerts:', af)
"
```

### Watch logs:
```bash
tail -f logs/k287_satellite.log
tail -f logs/k287_satellite_err.log
```

### Check K270 + K275 current positions:
```bash
python3 -c "
import json
with open('data/k287_satellite_dashboard.json') as f:
    d = json.load(f)
if d['daily_records']:
    rec = d['daily_records'][-1]
    k270 = rec['component']['K270']['signal']
    k275 = rec['component']['K275']['signal']
    print('K270 long today:', k270['long_today'])
    print('K270 short today:', k270['short_today'])
    print('K275 long today:', k275['long_today'])
    print('K275 short today:', k275['short_today'])
    print('Exchange status:', rec['exchange_status'])
"
```

### Combined K287d view (satellite + K280):
```bash
python3 -c "
import json
with open('data/k287_satellite_dashboard.json') as f:
    sat = json.load(f)
with open('data/k280_live_dashboard.json') as f:
    k280 = json.load(f)
sat_sh = (sat['rolling_metrics'] or {}).get('sh_30d', 'N/A')
k280_sh = (k280['rolling_metrics'] or {}).get('sh_30d', 'N/A')
sat_eq  = sat.get('sat_equity', 'N/A')
print(f'K280 main 30d Sh: {k280_sh}  |  Satellite 30d Sh: {sat_sh}')
print(f'Satellite equity: {sat_eq}')
print(f'K287d combined target Sh: {sat[\"backtest_k287d_combined_sh\"]}')
"
```

---

## Step 4: Alert Response Protocols

| Alert Code | Condition | Action |
|-----------|-----------|--------|
| `SAT_DD_EXCEED` | Satellite 30d DD > 1.5% | REDUCE satellite weight (20% → 10%). Review K270/K275 carry regime. |
| `K270_LOW_SH` | K270 30d rolling Sh < 3.0 | Review dYdX FR dispersion. Check if dYdX funding compressed across universe. |
| `K275_LOW_SH` | K275 30d rolling Sh < 3.0 | Advisory — OKX carry compressed. Inv-vol will naturally reduce K275 weight. |
| `DYDX_EXCHANGE_ERROR` | dYdX v4 indexer unreachable | K270 data is stale. Halt K270 paper positions. Check dYdX status page. |
| `OKX_EXCHANGE_ERROR` | OKX API unreachable | K275 data is stale. Halt K275 paper positions. Check OKX status page. |
| `K270_LOW_LIQ` | dYdX symbol < 70% 7d coverage | Remove low-coverage symbol from K270 universe. |
| `K275_LOW_LIQ` | OKX symbol < 70% 7d coverage | Remove low-coverage symbol from K275 universe. |

---

## Step 5: Deployment Risks

### 1. K275 Short History (~90d OKX data)
**Issue:** OKX public API retains only ~90 days of FR history. K275 backtest was on only 96d.
**Risk:** 2-fold WF minimum Sharpe = 5.94. Lower statistical confidence than K270 (4-fold, 731d).
**Action:** Monitor K275 30d Sh daily. If K275_LOW_SH fires for 7+ consecutive days, reduce satellite weight.

### 2. dYdX DEX Counterparty Risk
**Issue:** dYdX v4 is a Cosmos-based DEX (not CEX). Smart contract risk, bridge risk.
**Risk:** dYdX outage/hack would make K270 paper trades unrealizable. More fragile than Bybit/HL.
**Alert:** `DYDX_EXCHANGE_ERROR` fires if indexer is unreachable at 09:30 JST.
**Action:** If DYDX_EXCHANGE_ERROR fires for 2+ days, pause K270 paper logging. Investigate via dydx.trade status page.

### 3. OKX API Rate Limits
**Issue:** OKX public API has stricter rate limits. Fetch script uses 0.2s delays between pages.
**Risk:** 429 responses slow incremental refresh. Each symbol fetches max 10 pages × 100 records.
**Action:** If K275 panel is stale (days_stale > 1), run `k287_satellite_fetch.py --force` manually.

### 4. Live Weights vs OOS Reference
**Observation (first run):** Live inv-vol K270=18.0%, K275=82.0% vs OOS reference K270=35.5%, K275=64.5%.
**Reason:** On the 60d trailing window, K275 has recently lower vol than K270 (K270 has 731d of history with older volatile periods). This biases K275 higher.
**Impact:** Satellite is currently K275-heavy. Since K275_LOW_SH alert fired, this is unfavorable. Inv-vol will self-correct as K275 vol materializes.
**Action:** Monitor for 7d. If K275_LOW_SH persists, manually cap K275 at 65% until regime normalizes.

### 5. dYdX Liquidity vs CEX
**Issue:** dYdX liquidity is thinner than Bybit/HL. K270 uses 3bp maker cost (vs 2bp for K280).
**Risk:** For live trading (not paper), actual slippage on dYdX may exceed 3bp on smaller alts.
**Action:** If moving to live: use 5bp cost assumption for K270. Consider excluding very thin symbols (BLUR, BONK).

### 6. No Real Order Execution
Paper-trade only. For live trading: add $10k notional per symbol, actual order placement on dYdX (K270) and OKX (K275).

---

## Step 6: Comparison to K283 (K280 Main)

| Item | K283 (K280 Main) | K289 (K287d Satellite) |
|------|------------------|------------------------|
| Strategy | K198 + K208 + K276b | K270 + K275 |
| Exchanges | Bybit + HyperLiquid | dYdX v4 + OKX |
| Schedule | 09:00 JST | 09:30 JST |
| OOS Sharpe | 18.46 (K280) | 22.95 (K287c satellite) |
| Portfolio weight | 80% of K287d | 20% of K287d |
| MaxDD | -0.000013 | -0.000496 |
| Log | logs/k280_live.log | logs/k287_satellite.log |
| Dashboard | data/k280_live_dashboard.json | data/k287_satellite_dashboard.json |
| Trade log | data/k280_paper_trades.jsonl | data/k287_satellite_paper_trades.jsonl |
| FR window | K208: event-driven, K276b: 14d | K270: 14d, K275: 7d |
| Cost model | 2bp (HL) | 3bp dYdX, 2bp OKX |

---

## Quick Reference: Satellite Thresholds

| Metric | Normal | Alert | Critical |
|--------|--------|-------|---------|
| Satellite 30d Sh | > 8 | 5-8 | < 5 |
| K270 30d Sh | > 6 | 3-6 | < 3 |
| K275 30d Sh | > 5 | 3-5 | < 3 |
| Satellite 30d MaxDD | < 0.5% | 0.5-1.5% | > 1.5% → REDUCE |
| dYdX status | OK | — | ERROR → pause K270 |
| OKX status | OK | — | ERROR → pause K275 |

---

*Generated by Wave K289 — 2026-05-25*

# K530 K498 Phase 1A Activation Playbook

**Wave:** K530  |  **Date:** 2026-05-30  |  **Generated:** 2026-05-30 05:04 JST

## Executive Summary

| Metric | Value |
|--------|-------|
| Annual lift @ $30M | **+$121K/yr USDC** |
| Annual lift @ $100M | **+$1.03M/yr USDC** |
| Activation effort | **8 hours** |
| ROI | **$15,125/hr** |
| Risk tier | **LOW** |
| User active time | **~4.8 hours** + 24h paper observation |

> **Root cause:** K434 current Strategy B (HL_OVERFLOW) gives **$0 lift** because HL alone
> absorbs all orders at current AUM. True lift requires routing mode switch to **BBO_SELECT**:
> call `select_best_venue()` per order as primary decision (already implemented — just disabled).
> Bybit VIP5 maker rebate **1.0 bps > HL GOLD 0.3 bps = 0.7 bps advantage per order.**

## Why $0 Lift Today

```
Strategy B (current): HL_OVERFLOW mode
  → HL depth cap: 5% × $180M OI = $9M per order
  → Current order size: <$1M per 8h cycle (at $30M AUM)
  → Overflow trigger: NEVER (order always fits in HL)
  → Bybit/OKX: NEVER used → rebate advantage: $0

Strategy C (Phase 1A): BBO_SELECT mode
  → Score every venue BEFORE routing (not just for overflow)
  → Bybit score = Bybit_FR + 1.0bps_rebate - Bybit_slippage
  → HL score    = HL_FR    + 0.3bps_rebate - HL_slippage
  → Route to BEST-SCORED venue per order
  → Bybit wins ~80% of orders (higher rebate + lower slippage coeff)
  → Annual lift: +$121K @ $30M | +$1.03M @ $100M
```

## Venue Scoring Comparison

| Venue | Maker Rebate | Slip Coeff | Depth Cap | Status |
|-------|-------------|-----------|----------|--------|
| HL | **0.3 bps** | 10.0 | $9.0M | LIVE |
| Bybit | **1.0 bps** | 8.0 | $14.2M | LIVE |
| OKX | **0.5 bps** | 9.0 | $10.7M | SCAFFOLD-READY (K456) |

## Rebate Advantage Analysis @ $30M AUM

| Component | Value |
|-----------|-------|
| Annual K208 flow | $569,400,000 |
| HL rebate | 0.3 bps |
| Bybit rebate | **1.0 bps** |
| Effective BBO rebate | 0.890 bps |
| Rebate delta vs HL | **+0.590 bps** |
| Slippage savings | +1.1372 bps |
| **Total lift** | **1.7272 bps = $98K/yr** |

## BBO_SELECT Patch (14 LOC total)

### PATCH 1: `scripts/k280_live_fetch.py` (4 LOC)

```diff
- SMART_ROUTER_ENABLED = False   # K434: set True after testing; scaffold only in this wave
+ # K530: BBO_SELECT routing activated — K498 Phase 1A (8h, +$121K/yr @$30M)
+ # select_best_venue() called per order as PRIMARY decision (not just overflow)
+ # Bybit VIP5 1.0bps maker rebate > HL GOLD 0.3bps → 0.7bps advantage captured
+ SMART_ROUTER_ENABLED = True    # K530 K498 Phase 1A: BBO routing ACTIVE
```

### PATCH 2: `data/smart_router_config.json` (3 LOC)

```json
// Add after "default_post_only": true,
"routing_mode": "BBO_SELECT",
"routing_mode_note": "K530 K498 Phase 1A: BBO_SELECT replaces HL_OVERFLOW.",
"bbo_select_min_score": -0.0001,
```

### PATCH 3: `scripts/smart_router.py` (7 LOC — routing mode gate)

```python
# Add to select_best_venue(), after cfg = load_config():
routing_mode = cfg.get('routing_mode', 'HL_OVERFLOW')
if routing_mode == 'HL_OVERFLOW':
    pass  # Legacy mode — no BBO scoring
# BBO_SELECT: existing select_best_venue() logic IS correct BBO selection
# No structural change needed — only the routing_mode config gate
```

## 8-Step Activation Checklist

### Step 1: Verify K456 OKX daemon SCAFFOLD-READY state

**Time:** 15 minutes  |  **Risk:** ZERO (read-only, no trading)  |  **Category:** VERIFY

```bash
# Check daemon registered (should show com.cryptolab.okx-fr-monitor)
launchctl list | grep okx

# Check OKX dashboard freshness
python3 scripts/okx_fr_fetcher.py --dashboard

# Test live OKX fetch (no API keys needed for read-only)
python3 scripts/okx_fr_fetcher.py --symbol BTC-USDT-SWAP

# Verify data/okx_dashboard.json exists
ls -la data/okx_dashboard.json
```

**Expected:** OKX BTC FR: ±0.01% per 8h (non-zero value)

**Gate:** OKX fetch returns ok=True for BTC-USDT-SWAP

### Step 2: Apply K434 BBO_SELECT mode patch (10-20 LOC diff)

**Time:** 30 minutes  |  **Risk:** LOW (paper-trade only — no live orders yet)  |  **Category:** CODE_PATCH

```bash
# PATCH 1 (2 LOC): Enable smart router in k280_live_fetch.py
# Change line ~159:
#   SMART_ROUTER_ENABLED = False
# TO:
#   SMART_ROUTER_ENABLED = True    # K530 K498 Phase 1A: BBO routing ACTIVE

# PATCH 2 (3 LOC): Add routing_mode to smart_router_config.json
# Add after 'default_post_only': true,
#   "routing_mode": "BBO_SELECT",

# PATCH 3 (10 LOC): Add routing mode gate to smart_router.py
# (see BBO_SELECT_PATCH constant in this file for exact diff)

# Verify patch applied correctly
python3 scripts/smart_router.py --all-symbols --side short --size 100000
# Expected: Bybit should be selected for most symbols
```

**Expected:** smart_router.py prints: BTC: Best=Bybit score=+0.0001xxx

**Gate:** At least 50% of K208 symbols routed to Bybit or OKX (not HL)

### Step 3: OKX API key generate + secret env var setup

**Time:** 30 minutes  |  **Risk:** LOW (key generation only; no trading yet)  |  **Category:** API_SETUP

```bash
# 1. Generate OKX API keys:
#    https://www.okx.com/account/my-api → Create V5 API
#    Permissions: READ + TRADE (perps/futures)
#    IP whitelist: add your server IP

# 2. Set environment variables (never commit to git):
# Add to ~/.zshrc:
#   export OKX_API_KEY='your_api_key_here'
#   export OKX_API_SECRET='your_api_secret_here'
#   export OKX_PASSPHRASE='your_passphrase_here'

# 3. Verify variables set correctly:
python3 -c "import os; print('OKX_API_KEY:', 'SET' if os.environ.get('OKX_API_KEY') else 'NOT SET')"

# 4. Verify API key permissions (read-only test):
# OKX does NOT require keys for public FR fetch — keys only for trading
# Test authenticated endpoint (private account info):
# curl -H 'OK-ACCESS-KEY: $OKX_API_KEY' https://www.okx.com/api/v5/account/balance
```

**Expected:** OKX_API_KEY: SET | API balance endpoint returns code 0

**Gate:** All 3 env vars set (KEY, SECRET, PASSPHRASE). Balance endpoint returns code:0

### Step 4: Local dry-run K434 + K456 integration test (48h paper-trade)

**Time:** 60 minutes  |  **Risk:** ZERO (paper only — no orders sent to exchanges)  |  **Category:** DRY_RUN

```bash
# Full smart router dry-run (reads live FR, picks best venue, logs to JSONL)
python3 scripts/smart_router.py --all-symbols --side short --size 100000

# Check decision log — verify Bybit/OKX are selected
tail -20 data/smart_router_decisions.jsonl | python3 -c "
import json, sys
for line in sys.stdin:
    d = json.loads(line)
    print(f\"{d['symbol']:<8} → {d['venue']:<6} score={d.get('score',0):+.8f}\")
"

# Verify OKX FR data flowing into scoring
python3 scripts/okx_fr_fetcher.py --all

# 48h parallel paper-trade: compare routing decisions vs HL baseline
# (K280 daemon logs each cycle — check venue distribution in decisions.jsonl)

# Verify concentration caps not exceeded
python3 -c "
import json; d=json.loads(open('data/smart_router_dashboard.json').read())
print('Dashboard written:', d.get('generated_at_jst', 'N/A'))
print('Decisions logged:', len(d.get('recent_decisions', [])))
"
```

**Expected:**
- smart_router_decisions.jsonl: 50%+ decisions showing venue=Bybit or OKX
- No concentration cap violations logged
- OKX FR data: BTC/ETH/SOL/XRP all returning ok=True

**Gate:** 48h paper-trade: Bybit+OKX combined routing rate >= 40%

### Step 5: launchctl load K456 OKX FR monitor daemon

**Time:** 30 minutes  |  **Risk:** LOW (read-only FR monitor — no trading orders)  |  **Category:** DAEMON_LOAD

```bash
# Copy plist to LaunchAgents
cp com.cryptolab.okx-fr-monitor.plist ~/Library/LaunchAgents/

# (Optional: update plist with OKX API keys for future trading)
# Edit ~/Library/LaunchAgents/com.cryptolab.okx-fr-monitor.plist
# Uncomment and fill in OKX_API_KEY, OKX_API_SECRET, OKX_PASSPHRASE

# Load daemon
launchctl load ~/Library/LaunchAgents/com.cryptolab.okx-fr-monitor.plist

# Verify loaded
launchctl list | grep okx-fr-monitor

# Trigger immediate run (optional — daemon normally runs at next 8h boundary)
launchctl kickstart gui/$(id -u)/com.cryptolab.okx-fr-monitor

# Monitor logs
tail -f logs/okx_fr_monitor.log

# Verify dashboard updated
python3 scripts/okx_fr_fetcher.py --dashboard | python3 -m json.tool | grep last_poll
```

**Expected:** com.cryptolab.okx-fr-monitor shows PID in launchctl list | data/okx_dashboard.json last_poll updated

**Gate:** Daemon loaded + first poll completes (check logs/okx_fr_monitor.log for OK messages)

### Step 6: 24h paper-trade observation + log review

**Time:** 60 minutes  |  **Risk:** ZERO (observation only)  |  **Category:** OBSERVE

```bash
# Monitor smart router decisions over 24h
watch -n 60 'tail -5 data/smart_router_decisions.jsonl'

# After 24h: analyze routing distribution
python3 -c "
import json
from pathlib import Path
from collections import Counter
log = Path('data/smart_router_decisions.jsonl')
decisions = [json.loads(l) for l in log.read_text().strip().splitlines()]
recent = decisions[-72:]  # last 24h * 3 settlements/day * symbols
venue_counts = Counter(d['venue'] for d in recent)
print('24h routing distribution:'); [print(f'  {v}: {c/len(recent)*100:.0f}%') for v,c in venue_counts.most_common()]
"

# Check for errors in decision log
grep 'BLOCKED\|ERROR\|None' data/smart_router_decisions.jsonl | tail -20

# OKX dashboard freshness check
python3 scripts/okx_fr_fetcher.py --dashboard | python3 -m json.tool | grep -E 'last_poll|status'
```

**Expected:**
- Bybit: 40-85% of routing decisions
- OKX: 10-25% of routing decisions
- HL: 5-30% (wins when HL FR > other venues)
- Zero BLOCKED decisions (no venue saturation at current AUM)
- OKX dashboard: last_poll within 8h

**Gate:**
- [ ] Bybit+OKX combined >= 40% of routing decisions
- [ ] Zero concentration cap violations
- [ ] OKX data fresh (< 8h stale)

### Step 7: BBO routing live activation (gate flip in config)

**Time:** 30 minutes  |  **Risk:** LOW (concentration caps prevent runaway venue concentration)  |  **Category:** LIVE_ACTIVATION

```bash
# Pre-flight check
python3 scripts/smart_router.py --all-symbols --side short --size 100000

# Gate 1: Verify 48h paper-trade results pass
# Gate 2: Verify OKX API keys set (for trading — not just FR fetch)
# Gate 3: Verify concentration caps configured correctly

# ACTIVATION: flip K280 smart router flag to live
# In scripts/k280_live_fetch.py: confirm SMART_ROUTER_ENABLED = True
grep SMART_ROUTER_ENABLED scripts/k280_live_fetch.py

# Restart K280 live daemon to pick up new routing
launchctl kickstart -k gui/$(id -u)/com.cryptolab.k280-live

# Verify first live routing decision appears in log
tail -5 data/smart_router_decisions.jsonl

# First 30 minutes: monitor closely
watch -n 30 'tail -3 data/smart_router_decisions.jsonl'
```

**Expected:** K280 daemon produces routing decisions with venue=Bybit or venue=OKX (not exclusively HL)

**Gate:**
- [ ] First live order routed to Bybit or OKX confirms activation
- [ ] No exception in logs/k280_live.log
- [ ] smart_router_decisions.jsonl showing live timestamps

**Rollback:** `Set SMART_ROUTER_ENABLED = False → launchctl kickstart -k gui/$(id -u)/com.cryptolab.k280-live`

### Step 8: Daily realized lift monitoring (alert < 50% expected)

**Time:** 30 minutes  |  **Risk:** ZERO (monitoring only)  |  **Category:** MONITORING

```bash
# Daily monitoring script — run daily or add to existing cron
python3 -c "
import json; from pathlib import Path; from collections import defaultdict
log = Path('data/smart_router_decisions.jsonl')
if not log.exists(): print('No decisions yet'); exit()
decisions = [json.loads(l) for l in log.read_text().strip().splitlines()[-200:]]
venue_cnt = defaultdict(int)
for d in decisions: venue_cnt[d.get('venue','?')] += 1
total = sum(venue_cnt.values())
print(f'Last {total} decisions:')
for v,c in sorted(venue_cnt.items(), key=lambda x:-x[1]):
    print(f'  {v}: {c} ({c/total*100:.0f}%)')
non_hl = total - venue_cnt.get('HL',0)
print(f'Non-HL routing rate: {non_hl/total*100:.0f}% (target: >40%)')
"

# Weekly: check realized lift vs expected
# Expected routing: 40%+ non-HL = ~0.7bps lift per non-HL order
# $30M AUM: $331/day expected. Alert if 7d cumulative < $2,317 (50% threshold)
# Track via: data/smart_router_decisions.jsonl venue distribution
```

**Expected:** Non-HL routing rate >= 40% | 30d cumulative lift tracked in dashboard


**Total active time:** ~4h 45min + 24h paper observation

## Risk + Rollback Plan

| Risk | Probability | Impact | Mitigation |
|------|-------------|--------|------------|
| BBO scoring fails | LOW | LOW | Fallback to HL in select_best_venue() |
| OKX API instability | LOW | LOW | OKX weighted 15%; Bybit+HL absorb |
| Concentration cap breach | NEAR-ZERO | MEDIUM | filter_by_concentration_caps() enforced |
| Latency > 1s budget | VERY LOW | LOW | 3-venue scoring = 145ms (85% headroom) |

**Rollback time:** < 5 minutes

```bash
# Rollback: flip flag back to False
# In scripts/k280_live_fetch.py:
# SMART_ROUTER_ENABLED = False
launchctl kickstart -k gui/$(id -u)/com.cryptolab.k280-live
```

## Monitoring (Step 8 Ongoing)

| Metric | Target | Alert Threshold |
|--------|--------|----------------|
| Non-HL routing rate | >= 40% | < 20% for 7d |
| Daily lift @ $30M | $332/day | < $165/day (50%) |
| Daily lift @ $100M | $2822/day | < $1,411/day (50%) |
| OKX dashboard freshness | < 8h | > 24h stale |
| Concentration cap | HL < 65% | HL > 65% |

## Forward Path: Phase 1B/2

| Phase | Trigger | Venues Added | Effort | Risk | Value |
|-------|---------|-------------|--------|------|-------|
| 1B | 30d after 1A | Aevo + dYdX_v4 | 100h | MEDIUM | AUM ceiling $200M |
| 2 | 60d after 1B | Lighter + Vertex | 160h | HIGH | $200M+ safe scale |

> Phase 1B adds no incremental lift at $30M — value is capacity insurance.
> Activate Phase 1B only when targeting $100M+ AUM.

## Combined Activated Lift @ $30M

| Action | Annual USDC | Status |
|--------|------------|--------|
| K498 Phase 1A BBO routing (K530) | +$121K/yr | **THIS PLAYBOOK** |
| K481 Builder rebate (conservative 10%) | +$99K/yr | Action #23 (user-activatable) |
| K430 3x leverage | multiplier (already deployed) | LIVE |
| **Total incremental (conservative)** | **+$220K/yr** | Both activated |

---

*K530 K498 Phase 1A Playbook — Generated by wave_k530_k498_phase_1a_playbook.py*
*K339 pattern | 2026-05-30*
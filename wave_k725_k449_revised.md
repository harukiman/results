# K725 — K449 Week 1 LIVE Revised Playbook

**Wave:** K725  
**Context:** K723 escalation — K376 indefinitely deferred, K449 priority elevated to PRIMARY  
**Date:** 2026-05-30 17:32 JST  
**Pattern:** K339 REPO_ROOT  
**Profit:** K449 $13K/yr | K481+K449 $260K/yr Week 1 | Pipeline $1.16M/yr W1-W5

---

## Executive Summary

K723 deferred K376 indefinitely (BTC BULL regime uncertain). This elevates K449 ETH-BTC Week 1 LIVE from secondary to **PRIMARY** validation path. K449 is a strategic proof-of-concept: it demonstrates the execution infrastructure (plist + 8h cron + POST_ONLY paired trade + K357 emergency exit) that will scale to **$1.16M/yr** across W2-W5 family strategies (K476→K484→K493→K500/K507→K512).

**Key change:** K280 75→60% cut (K539 Phase B1) is now the **mandatory prerequisite** for K449 activation. This frees 7.5pp HL headroom and $1.5M capital.

| Item | Value |
|------|-------|
| K449 standalone profit | $13,000/yr @$10M |
| K481 builder rebate (Phase A) | $247,000/yr |
| **Week 1 combined** | **$260,000/yr** |
| Pipeline multiplier (W1-W5) | **89x** ($1.16M/yr unlocked by K449 PASS) |
| Prerequisite | K280 75→60% patch (1-LOC change) |
| Prerequisite file | `scripts/leverage_manager.py` |

---

## Phase 1: Prerequisites (Completion Check)

### K280 Sleeve 75→60% (K539 Phase B1)

**Status:** PENDING (K723 elevated this to mandatory)

**Single change:**

File: `scripts/leverage_manager.py`  
Section: `SLEEVE_WEIGHTS` dict  
Field: `"K280"`

```python
# BEFORE (current):
"K280":   0.75,   # K280 main — v6.13d

# AFTER (K725 activation):
"K280":   0.60,   # K280 main (K539 Phase B1: 75→60, frees 7.5pp HL for K449)
```

**Verify current state:**
```bash
grep '"K280"' scripts/leverage_manager.py
# Expected output: "K280":   0.75,
```

**Apply change:**
```bash
sed -i '' 's/"K280":   0.75,   # K280 main (K198 + K208 + K276b) — v6.13d; v6.16 reduces to 0.72/"K280":   0.60,   # K280 main (K539 Phase B1: 75→60, frees 7.5pp HL, 2026-05-30)/' scripts/leverage_manager.py

# Verify:
grep '"K280":   0.60' scripts/leverage_manager.py || echo "ERROR: change failed"
```

**Commit:**
```bash
git add scripts/leverage_manager.py
git commit -m "K725 K280 sleeve 75→60% (K539 Phase B1, mandatory K449 prereq)"
git push origin main
```

### HL Exposure Post-Cut

```
Baseline (v6.13d):           57.5%
After K280 60% × 70%:        42.0%
+ K449 5%:                    5.0%
+ HLP / residual:             ~5.0%
Post-activation estimate:    ~52.0%  ← WELL BELOW 65% hard cap
```

**Assessment:** SAFE for activation.

---

## Phase 2: Day 0 Activation Steps (MANUAL EXECUTION)

### [D0-PREREQ]

**Step 1:** Confirm K280 sleeve config
```bash
grep '"K280"' scripts/leverage_manager.py
# Expected: "K280":   0.60,
```

**Step 2:** Confirm git push completed
```bash
git log --oneline -1 scripts/leverage_manager.py
# Expected: commit message includes "K280" or "K539"
```

### [D0-LIVE]

**Step 3:** Edit K449 plist — remove `--dry-run`
```bash
sed -i '' '/<string>--dry-run<\/string>/d' com.cryptolab.k449-eth-btc.plist

# Verify CLEAN (no --dry-run remaining):
grep 'dry-run' com.cryptolab.k449-eth-btc.plist && echo "ERROR: --dry-run still present" || echo "CLEAN"
```

**Step 4:** Copy plist to LaunchAgents
```bash
cp com.cryptolab.k449-eth-btc.plist ~/Library/LaunchAgents/com.cryptolab.k449-eth-btc.plist

# Verify:
ls -la ~/Library/LaunchAgents/com.cryptolab.k449-eth-btc.plist
```

**Step 5:** Load daemon
```bash
launchctl load ~/Library/LaunchAgents/com.cryptolab.k449-eth-btc.plist

# Verify loaded:
launchctl list | grep k449-eth-btc
# Expected: com.cryptolab.k449-eth-btc present (PID will be 0 until next 8h interval)
```

### [D0-VERIFY]

**Step 6:** HL margin health check
```bash
python3 scripts/emergency_hl_exit.py --dry-run --status

# Pass criteria: margin utilisation < 70%
```

**Step 7:** K449 status check
```bash
python3 scripts/k449_eth_btc_run.py --status

# Pass criteria: dashboard refreshed, paper_trade_mode=false, position_state visible
```

---

## Phase 3: Days 1-7 Monitoring

### Daily Cadence (09:00 JST)

```bash
python3 scripts/k449_eth_btc_run.py --status

cat data/k449_dashboard.json | python3 -c "
import json, sys
d = json.load(sys.stdin)
print(f'Position:  {d[\"position_state\"]}')
print(f'FR diff:   {d[\"fr_raw_diff\"]:.6f}')
print(f'Daily PnL: \${d[\"daily_pnl_usdc\"]:.2f}')
print(f'Drift %:   {d[\"delta_neutral_drift_pct\"]:.3%}')
print(f'60d Sh:    {d[\"60d_sharpe\"]:.2f}')
"
```

### Per-8h Cycle Check

```bash
# HL margin
python3 scripts/emergency_hl_exit.py --dry-run --status

# FR differential + position
cat data/k449_dashboard.json | python3 -c "
import json, sys
d = json.load(sys.stdin)
print(f'Cycle #:    {d.get(\"cycle_count\", \"N/A\")}')
print(f'FR diff:    {d[\"fr_raw_diff\"]:.6f} (7d EMA: BTC FR - ETH FR)')
print(f'Position:   {d[\"position_state\"]} (LONG_ETH_SHORT_BTC or reverse)')
print(f'Drift:      {d[\"delta_neutral_drift_pct\"]:.3%}')
print(f'Margin:     {d.get(\"hl_margin_util_pct\", \"N/A\"):.1f}%')
"
```

### Monitoring Metrics (Pass/Alert)

| Metric | Pass | Alert | Source |
|--------|------|-------|--------|
| `60d_sharpe` | ≥ 9.0 | < 5.0 | k449_dashboard.json |
| `fill_rate_pct` | ≥ 65% | < 50% | k449_dashboard.json |
| `delta_neutral_drift_pct` | < 5% | > 8% | k449_dashboard.json |
| `daily_pnl_usdc` | ≥ $0 | < -$5 | k449_dashboard.json |
| HL margin utilisation | < 70% | > 80% | emergency_hl_exit.py |

---

## Phase 4: Day 7 Go/No-Go Decision

### Decision Logic

| Decision | Criteria | Action | Profit Unlock |
|----------|----------|--------|---------------|
| **PASS** | `60d_sharpe ≥ 9.0` AND `fill_rate ≥ 65%` | Expand sleeve 5%→8% | K476+K484 Week 2 ready ($263K/yr) |
| **HOLD** | `60d_sharpe 5-9` OR `fill_rate 50-65%` | Maintain 5%, re-evaluate D14 | Pause W2 activation |
| **ROLLBACK** | `60d_sharpe < 5` OR `fill < 50%` OR `margin > 80%` | Close both legs, reload plist | Return to paper mode |

### PASS Protocol

If `60d_sharpe ≥ 9.0` and `fill_rate ≥ 65%`:

```bash
# 1. Approve sleeve expansion in leverage_manager.py
sed -i '' 's/"K449":   0.05,/"K449":   0.08,/' scripts/leverage_manager.py

# 2. Commit
git add scripts/leverage_manager.py
git commit -m "K725 K449 sleeve 5%→8% (D7 PASS: Sharpe ≥ 9.0, fill ≥ 65%)"

# 3. Document in master deployment log
# See: docs/k302a_master_deployment.md (User Action #31, appendix)

# 4. Wait for K476 plist (Week 2 activation ready)
```

### ROLLBACK Protocol

If `60d_sharpe < 5.0` or `fill_rate < 50%` or margin > 80%:

```bash
# 1. Close both legs immediately
python3 scripts/k449_eth_btc_run.py --close "D7 ROLLBACK: Sharpe/fill below threshold"

# 2. Unload daemon
launchctl unload ~/Library/LaunchAgents/com.cryptolab.k449-eth-btc.plist

# 3. Restore --dry-run to plist
# Edit com.cryptolab.k449-eth-btc.plist and re-add: <string>--dry-run</string>

# 4. Re-copy to LaunchAgents
cp com.cryptolab.k449-eth-btc.plist ~/Library/LaunchAgents/

# 5. Document decision in master deployment log
```

---

## Phase 5: K449 Strategic Value (89x Validation Multiplier)

### Week 1: K449 ETH-BTC ($13K/yr)

Standalone profit is modest, but strategic role is **critical**:
- Validates execution path: plist + 8h cron + POST_ONLY paired trade + K357 emergency exit
- Demonstrates HL paired-position handling at scale ($500K margin committed)
- Proves filling dynamics (65% target) in real FR environment
- **Unlocks entire W2-W5 family if PASS**

### Pipeline W1-W5 (89x Multiplier)

| Week | Strategy | Sleeve | Profit/yr | Cumulative |
|------|----------|--------|-----------|-----------|
| 1 | K449 ETH-BTC | 5% | $13K | $13K |
| 2 | K476 SOL-BTC + K484 AVAX-BTC | 3%+3% | $263K | $276K |
| 3 | K493 ATOM-BTC | 3% | $231K | $507K |
| 4 | K500 INJ + K507 SEI/TIA | 3%+3% | $354K | $861K |
| 5 | K512 APT-BTC | 3% | $302K | **$1,163K** |
| + | K481 builder rebate (Phase A) | — | $247K | **$1,410K/yr** |

**89x validation multiplier:** K449 PASS gates $1.16M/yr family activation. A single 7-day validation unlocks a 5-week cascade.

---

## Phase 6: Risk Register

| Risk | Severity | Trigger | Mitigation |
|------|----------|---------|-----------|
| Paper vs LIVE Sharpe divergence | MEDIUM | 60d_sharpe < 5 OR fill < 50% | D7 rollback protocol |
| **HL concentration breach >65%** | **HIGH** | HL exposure > 60% post-K449 | **Daily verify post-activation; hold K476/K484 if HL > 60%** |
| FR differential collapse (ETH=BTC) | LOW | NEUTRAL > 14 days | No action; auto-resume when FR re-opens |
| K280 sleeve cut loss | MEDIUM | K280 30d Sharpe < 8 | Accept: $1.16M pipeline >> $247K K280 delta |
| Week 2 cascade concentration | MEDIUM | HL > 65% after K476 | 48h gap between K476/K484; hold K484 if needed |

### Critical Risk: HL Concentration

**Trajectory post-K280 cut:**

```
Baseline (K280 60%):     ~47%
+ K449 5%:                ~52%   (Week 1, D+0)
+ K476 3%:                ~55%   (Week 2, D+7)
+ K484 3%:                ~58%   (Week 2, D+9)
Hard cap:                 65%
Headroom after W2:        7pp     ← SAFE
```

**Daily verification (each 09:00 JST):**

```bash
python3 scripts/emergency_hl_exit.py --dry-run --status | grep -E "concentration|exposure|margin"
```

If HL > 60% at any point, **hold next activation** until prior week completes.

---

## Phase 7: Week 2 Prep (If K449 PASS)

### K476 SOL-BTC (D+7) + K484 AVAX-BTC (D+9)

**Prerequisites (all must PASS):**
1. K449 Day 7 PASS (60d_sharpe ≥ 9.0, fill_rate ≥ 65%)
2. HL margin utilisation < 65% post-K449 Week 1
3. K476 plist edited (remove --dry-run, same 5-step procedure as K449)
4. K484 plist edited (same procedure, 48h after K476)
5. Combined HL exposure < 65% after both loaded

### 48-Hour Cascade Gap

- **D+7:** Load K476 (gain +3pp HL)
- **D+8:** Verify K476 stability (margin < 70%, position fills)
- **D+9:** Load K484 (gain +3pp HL)
- **Rationale:** Prevents simultaneous HL margin pressure from two new paired positions

---

## Phase 8: User Action Checklist

### Day 0 — Activation

- [ ] **Prerequisites complete:**
  - [ ] K280 75→60% applied to `scripts/leverage_manager.py`
  - [ ] Commit pushed: `git push origin main`
  - [ ] Verify: `grep '"K280":   0.60' scripts/leverage_manager.py`

- [ ] **LIVE switch:**
  - [ ] Step 3: `sed -i '' '/<string>--dry-run<\/string>/d' com.cryptolab.k449-eth-btc.plist`
  - [ ] Verify: `grep 'dry-run' com.cryptolab.k449-eth-btc.plist || echo CLEAN`
  - [ ] Step 4: `cp com.cryptolab.k449-eth-btc.plist ~/Library/LaunchAgents/`
  - [ ] Step 5: `launchctl load ~/Library/LaunchAgents/com.cryptolab.k449-eth-btc.plist`
  - [ ] Verify: `launchctl list | grep k449`

- [ ] **Verification:**
  - [ ] Step 6: `python3 scripts/emergency_hl_exit.py --dry-run --status` → margin < 70%
  - [ ] Step 7: `python3 scripts/k449_eth_btc_run.py --status` → dashboard refreshed

### Days 1-3 — Monitor

- [ ] **Daily 09:00 JST:** `python3 scripts/k449_eth_btc_run.py --status`
- [ ] **Daily:** Check `data/k449_dashboard.json` → position_state, daily_pnl_usdc, drift_pct
- [ ] **Daily:** HL margin utilisation < 70% (via `emergency_hl_exit.py`)
- [ ] **Per 8h cycle:** Log FR differential, position direction, fill rate

### Days 4-6 — Monitor + Prepare Decision

- [ ] **Daily:** Continue monitoring (same as Days 1-3)
- [ ] **By D6 evening:** Prepare D7 decision document:
  - Final 60d_sharpe reading
  - Fill rate (% filled orders / total orders)
  - Any margin exceedances or position drift issues

### Day 7 — Decision + Action

- [ ] **Review metrics:**
  - [ ] Read `data/k449_dashboard.json` → `60d_sharpe` field
  - [ ] Read fill_rate (check logs or dashboard)
  - [ ] Check HL margin < 65%

- [ ] **Decision:**
  - [ ] **PASS:** 60d_sharpe ≥ 9.0 AND fill_rate ≥ 65%
    - Approve K449 sleeve 5%→8%
    - Commit + push
    - Document in `docs/k302a_master_deployment.md`
  - [ ] **HOLD:** 60d_sharpe 5-9 OR fill_rate 50-65%
    - Maintain 5%, re-evaluate D14
    - Document rationale
  - [ ] **ROLLBACK:** 60d_sharpe < 5 OR fill < 50% OR margin > 80%
    - Execute rollback steps (close, unload, restore --dry-run)
    - Document failure mode

---

## Files & References

| File | Purpose | Status |
|------|---------|--------|
| `scripts/leverage_manager.py` | K280 0.75→0.60 (1-LOC change, prerequisite) | PENDING |
| `com.cryptolab.k449-eth-btc.plist` | LaunchAgent (edit, remove --dry-run) | READY |
| `scripts/k449_eth_btc_run.py` | K449 strategy daemon | DEPLOYED (paper) |
| `scripts/emergency_hl_exit.py` | K357 emergency exit (K449 registered) | ACTIVE |
| `data/k449_dashboard.json` | Live monitoring dashboard | ACTIVE |
| `data/k280_live_dashboard.json` | K280 live metrics | MONITORING |
| `docs/k302a_master_deployment.md` | Master deployment doc | UPDATE POST-D7 |
| `wave_k725_k449_revised.py` | K725 playbook (this wave) | DELIVERABLE |
| `wave_k725_k449_revised.json` | K725 structured summary | DELIVERABLE |
| `wave_k725_k449_revised.md` | K725 user playbook (this file) | DELIVERABLE |

---

## Key Insights

### Why K449 Is Critical Now (Post-K723)

1. **K376 indefinitely deferred** → Lost $247K/yr profit in pipeline
2. **K449 non-BTC alpha** → Fills regime gap with ETH-BTC FR carry (uncorrelated to BTC momentum)
3. **Infrastructure proof** → Same plist/8h/POST_ONLY pattern scales to W2-W5 family
4. **89x validation multiplier** → K449 PASS unlocks $1.16M/yr family cascade

### K280 75→60% Is Now Mandatory (Not Optional)

1. **HL headroom** → Frees 7.5pp for K449 (5%) + K449 family (6pp W2-W5)
2. **Capital efficiency** → $1.5M freed, redeployed to higher-margin strategies
3. **Risk management** → Keeps HL concentration < 65% throughout W1-W5 cascade
4. **Irreversible once K449 loads** → Must apply before Step 3 (plist edit)

### Daily Verification Is Not Optional

HL concentration is the **critical path risk**. Daily 09:00 JST check:

```bash
python3 scripts/emergency_hl_exit.py --dry-run --status | grep -i "concentration\|exposure"
```

If HL > 60%, escalate to risk team immediately. K376 deferral means K449 family is the primary profit source — concentration breach threatens the entire $1.16M/yr pipeline.

---

*K725 — 2026-05-30 17:32 JST*  
*K449 Week 1 LIVE priority elevated (K376 deferred); $260K/yr Week 1 | $1.16M/yr W1-W5 pipeline*

# K552: K280 Sleeve 75→60% Concrete Production Patch

**Generated:** 2026-05-30 05:56 JST  
**Wave:** K552  
**Status:** PATCH NOT YET APPLIED — awaiting user action  
**Priority:** CRITICAL BLOCKER for K376 ($247K/yr), K449 LIVE ($13K+), Phase B1

---

## Executive Summary

K551 confirmed that K280 sleeve weight = **0.75** is the sole blocker for:
- K376 BULL unlock ($247K/yr — ETA 14d)
- K449 Week 1 LIVE activation ($13K/yr + pipeline to $1.163M/yr)
- v6.26 Phase B1 transition

K552 delivers the **exact 3-file patch** (concrete file paths + line numbers) to reduce K280 from 75% → 60%, freeing **7.5pp HL headroom** and unlocking the cascade.

**Net 30-day value: +$260K+/yr immediately, +$1.163M/yr pipeline.**

---

## Phase 1: Authoritative File Discovery

K280 weight 0.75 appears in **5 files**, but only **3 require patching**:

### File 1: `scripts/leverage_manager.py` — PRIMARY (MUST PATCH)
- **Line 74**
- `SLEEVE_WEIGHTS` dict — the **runtime authoritative source** for all position sizing
- Every sleeve's `compute_position_size()` call reads from this dict
- **K280 daily run, K302a satellite, and all paired-trade scripts** use this

```python
# Line 74 — BEFORE:
    "K280":   0.75,   # K280 main (K198 + K208 + K276b) — v6.13d; v6.16 reduces to 0.72

# Line 74 — AFTER:
    "K280":   0.60,   # K280 main (K539 Phase B1: 75→60%, frees 7.5pp HL, 2026-05-30)
```

### File 2: `data/portfolio_aum_state.json` — JSON STATE (MUST PATCH)
- **Line 18**
- `sleeve_weights.K280` — persisted state read by `portfolio_aum_manager.load_state()`
- `k280_daily_run.py` reads this via K429 AUM tracking
- Without this update, `load_state()` returns 0.75 and overwrites leverage_manager at runtime

```json
// Line 18 — BEFORE:
    "K280": 0.75,

// Line 18 — AFTER:
    "K280": 0.60,
```

### File 3: `scripts/portfolio_aum_manager.py` — DEFAULT FALLBACK (PATCH FOR CONSISTENCY)
- **Line 86**
- `DEFAULT_SLEEVE_WEIGHTS` — used only when `portfolio_aum_state.json` does not exist (fresh install / state reset)
- Also update **line 17** docstring for consistency

```python
# Line 86 — BEFORE:
    "K280":       0.75,

# Line 86 — AFTER:
    "K280":       0.60,
```

### Files to NOT Change

| File | Line | Value | Reason |
|------|------|-------|--------|
| `scripts/k302a_satellite_run.py` | 151 | `K302A_MAIN_WEIGHT = 0.75` | Display-only combined dashboard math. Does NOT drive position sizing. |
| `scripts/k386_v613e_fallback_run.py` | 66 | `"K280": 0.85` | v6.13e BEAR_1 fallback — intentionally boosted. Leave unchanged. |
| `scripts/k386_v613e_fallback_run.py` | 74 | `"K280": 0.75` | Snapshot/reference weight inside the fallback script. Not runtime. |

---

## Phase 2: Complete 1-LOC Diff

### Primary patch diff (leverage_manager.py)
```diff
--- a/scripts/leverage_manager.py
+++ b/scripts/leverage_manager.py
@@ line 74 @@
 SLEEVE_WEIGHTS: Dict[str, float] = {
-    "K280":   0.75,   # K280 main (K198 + K208 + K276b) — v6.13d; v6.16 reduces to 0.72
+    "K280":   0.60,   # K280 main (K539 Phase B1: 75→60%, frees 7.5pp HL, 2026-05-30)
     "K297":   0.20,   # K302a satellite (PAXG 60% + SPX 40%)
     "sUSDe":  0.05,   # sUSDe OC sleeve
```

### JSON state diff (portfolio_aum_state.json)
```diff
--- a/data/portfolio_aum_state.json
+++ b/data/portfolio_aum_state.json
@@ line 18 @@
   "sleeve_weights": {
-    "K280": 0.75,
+    "K280": 0.60,
     "K297_prime": 0.2,
```

---

## Phase 3: User Action Sequence

### Pre-flight: Backup
```bash
cp scripts/leverage_manager.py scripts/leverage_manager.py.bak
cp data/portfolio_aum_state.json data/portfolio_aum_state.json.bak
cp scripts/portfolio_aum_manager.py scripts/portfolio_aum_manager.py.bak
```

### Step 1: Apply PRIMARY patch (leverage_manager.py)
```bash
sed -i '' 's/"K280":   0\.75,   # K280 main (K198 + K208 + K276b) — v6\.13d; v6\.16 reduces to 0\.72/"K280":   0.60,   # K280 main (K539 Phase B1: 75→60%, frees 7.5pp HL, 2026-05-30)/' scripts/leverage_manager.py
```

Verify:
```bash
grep -n '"K280"' scripts/leverage_manager.py | head -5
# Expected: L74 shows 0.60
```

### Step 2: Apply JSON STATE patch (portfolio_aum_state.json)
```bash
python3 -c "
import json
f = 'data/portfolio_aum_state.json'
d = json.load(open(f))
d['sleeve_weights']['K280'] = 0.60
d['last_updated_jst'] = '2026-05-30 K552 Phase B1 patch'
json.dump(d, open(f, 'w'), indent=2)
print('Updated K280 to', d['sleeve_weights']['K280'])
"
```

### Step 3: Apply AUM MANAGER patch (portfolio_aum_manager.py)
```bash
sed -i '' 's/"K280":       0\.75,/"K280":       0.60,/' scripts/portfolio_aum_manager.py
```

### Step 4: Verify all three files
```bash
grep -n '"K280".*0\.' scripts/leverage_manager.py data/portfolio_aum_state.json scripts/portfolio_aum_manager.py
```
**Expected output:**
```
scripts/leverage_manager.py:74:    "K280":   0.60,   # K280 main (K539 Phase B1:...
data/portfolio_aum_state.json:18:    "K280": 0.6,
scripts/portfolio_aum_manager.py:86:    "K280":       0.60,
```

### Step 5: Deployment status check
```bash
python3 scripts/verify_deployment_status.py 2>&1 | head -40
```
Expected: No MISMATCH errors. State consistent.

### Step 6: K297_prime unchanged check
```bash
python3 -c "import json; d=json.load(open('data/portfolio_aum_state.json')); print('K297_prime:', d['sleeve_weights']['K297_prime'])"
# Expected: K297_prime: 0.2
```

### Step 7: Sleeve weights sum check
```bash
python3 -c "
import json
d = json.load(open('data/portfolio_aum_state.json'))
w = d['sleeve_weights']
print('Weights:', w)
print('Sum:', sum(w.values()))
print('Note: sum < 1.0 is valid — K376 is sub-slice of K280')
"
```
Expected: K280=0.60, K297_prime=0.20, sUSDe=0.05, K376=0.03, sum=0.88 (valid — K376 sub-slice of K280)

### Step 8: Restart k280-live daemon
```bash
launchctl unload ~/Library/LaunchAgents/com.cryptolab.k280-live.plist
launchctl load  ~/Library/LaunchAgents/com.cryptolab.k280-live.plist
```

### Step 9: Restart k302a-satellite daemon
```bash
launchctl unload ~/Library/LaunchAgents/com.cryptolab.k302a-satellite.plist
launchctl load  ~/Library/LaunchAgents/com.cryptolab.k302a-satellite.plist
```

### Step 10: Confirm daemons running
```bash
launchctl list | grep cryptolab
# Expected: k280-live and k302a-satellite show PIDs (not -)
```

### Step 11: Monitor 24h post-patch
```bash
# Check k280 dashboard next morning:
python3 -c "import json; d=json.load(open('data/k280_live_dashboard.json')); print(d.get('today_pnl', 'no pnl yet'))"
```

### Step 12: Unlock K449 LIVE (D+1 per K549 playbook)
After 24h clean monitoring, activate K449:
```bash
cp com.cryptolab.k449-eth-btc.plist ~/Library/LaunchAgents/
launchctl load ~/Library/LaunchAgents/com.cryptolab.k449-eth-btc.plist
```

---

## Phase 4: HL Exposure Recompute

### Before patch (K280 = 0.75)
| Component | HL % | Notes |
|-----------|------|-------|
| K280 HL portion | ~30.0% | 75% sleeve × 50% on HL (HL+Bybit split) |
| K449 (5% HL-only) | ~2.5% | Pre-patch with K449 inactive |
| K297' PAXG+SPX | ~2.0% | Partial HL |
| **Total HL** | **~34.5%** | (v6.13d observed ~57.5% — accounting for leverage; 3x on K280) |
| **Headroom** | **7.5pp** | v6.13d: 57.5% → 65% cap = 7.5pp |

**Note:** v6.13d observed 57.5% at 0.75 (K280 leveraged 3x notional on HL). With 3x leverage, K280 HL = 0.75 × 0.92 × 0.50 × 3 = 103% notional but margin-basis 57.5% — per existing measurements.

### After patch (K280 = 0.60)
| Component | HL % | Change |
|-----------|------|--------|
| K280 HL reduction | -7.5pp | 60% sleeve vs 75% = -15pp × 50% HL fraction |
| K449 LIVE activated | +2.5pp | 5% sleeve HL-only (net new) |
| Net change | **-5.0pp** | 57.5% → ~52.5% |
| HL cap headroom | **+12.5pp** | vs 65% cap |

**K376 + K449 family can add up to 12.5pp more HL before hitting the 65% cap.**

---

## Phase 5: Daemon Impact

| Daemon | Status | Weight Source | Restart? |
|--------|--------|---------------|----------|
| `com.cryptolab.k280-live` | LOADED | `portfolio_aum_state.json` via load_state() | YES |
| `com.cryptolab.k302a-satellite` | LOADED | `leverage_manager.SLEEVE_WEIGHTS` (module import) | YES |
| `com.cryptolab.paper-trade` | LOADED | Independent weight config | No |
| `com.cryptolab.forward-test` | LOADED | Read-only monitoring | No |
| `com.cryptolab.inbox-poll` | LOADED | No position sizing | No |
| `com.cryptolab.hl-predicted-monitor` | LOADED | Monitoring only | No |

**Stale cache risk:** `leverage_manager.py` is imported at daemon startup. If k280-live or k302a-satellite are running as long-lived processes, they cache the old `SLEEVE_WEIGHTS` in memory. **Restart is required** for the new weight to take effect.

---

## Phase 6: Rollback Path

### Trigger rollback if:
1. HL exposure rises unexpectedly > 65% after K449 activation
2. Margin health circuit breaker fires (> 80% margin used)
3. K280 daily PnL anomaly > 3-sigma (check `data/k280_live_dashboard.json`)
4. Any daemon error in first 24h post-patch

### Rollback commands:
```bash
# Step 1: Restore from backup (safest)
cp scripts/leverage_manager.py.bak scripts/leverage_manager.py
cp data/portfolio_aum_state.json.bak data/portfolio_aum_state.json
cp scripts/portfolio_aum_manager.py.bak scripts/portfolio_aum_manager.py

# Step 2: Or manual revert (if no backup)
sed -i '' 's/"K280":   0\.60,   # K280 main (K539 Phase B1.*/"K280":   0.75,   # K280 main (K198 + K208 + K276b) — v6.13d; v6.16 reduces to 0.72/' scripts/leverage_manager.py
python3 -c "import json; f='data/portfolio_aum_state.json'; d=json.load(open(f)); d['sleeve_weights']['K280']=0.75; json.dump(d, open(f,'w'), indent=2)"
sed -i '' 's/"K280":       0\.60,/"K280":       0.75,/' scripts/portfolio_aum_manager.py

# Step 3: Restart daemons
launchctl unload ~/Library/LaunchAgents/com.cryptolab.k280-live.plist
launchctl load  ~/Library/LaunchAgents/com.cryptolab.k280-live.plist
launchctl unload ~/Library/LaunchAgents/com.cryptolab.k302a-satellite.plist
launchctl load  ~/Library/LaunchAgents/com.cryptolab.k302a-satellite.plist

# Step 4: Verify rollback
grep -n '"K280".*0\.' scripts/leverage_manager.py data/portfolio_aum_state.json
# Expected: both show 0.75
```

---

## Phase 7: Risk Analysis

| Risk | Severity | Mitigation |
|------|----------|------------|
| Production state mismatch (JSON vs py file) | HIGH | Patch both atomically (steps 1+2 within 60s) |
| Daemon using stale cached weight | HIGH | Restart both daemons immediately after patch |
| HL exposure mis-computed after K449 activation | MEDIUM | Verify HL pct in k280_live_dashboard.json before activating K449 |
| K302a satellite dashboard showing wrong combined return | LOW | K302A_MAIN_WEIGHT unchanged — display only, not position-sized |
| Unintended reduction in K280 profitability | LOW | K280 is FR-carry (rate-of-return per dollar); sleeve cut reduces notional, not per-dollar return |
| Rollback triggers unexpected regime state | LOW | Rollback restores exact prior state; no regime dependency |

---

## Phase 8: Profit Unlock Pathway

```
K552 PATCH APPLIED
      |
      +-- K280 sleeve: $10M × 0.75 → 0.60 = -$1.5M notional
      |   (capital recycled into paired trades)
      |
      +-- HL headroom freed: 57.5% → ~50% = 7.5pp
      |
      v
K449 Week 1 LIVE (D+1 after patch)
  - 5% sleeve × 4x × $9.2M = $1.84M notional
  - HL-only (K439 POST_ONLY, 8h cron)
  - $13K+/yr immediate
  - Pipeline validation trigger: K449 pass → K476(W2) → K484 → K493 → K500/K507 → K512
      |
      v
K376 BULL trigger (ETA D+14, K551 analysis)
  - K280 Sh>8 sustained 15d → K376 reopen
  - $247K/yr
      |
      v
NET 30-DAY UNLOCK
  $247K (K376) + $13K+ (K449) = $260K+ immediate
  Full pipeline: $1,163,000/yr @ $10M (W1-W5 cascade)
  Multiplier vs K449 alone: ×89
```

---

## Validation Script

```bash
# Run K552 discovery (READ-ONLY, no auto-patch)
python3 wave_k552_k280_patch.py

# Check-only mode (no output files)
python3 wave_k552_k280_patch.py --check

# After patch: re-run to confirm
python3 wave_k552_k280_patch.py
# Expected: "STATUS: PATCH APPEARS APPLIED"
```

---

## Appendix: File Reference

| File | Role | Line of Interest |
|------|------|-----------------|
| `scripts/leverage_manager.py` | AUTHORITATIVE runtime weight | L74: `SLEEVE_WEIGHTS["K280"] = 0.75` |
| `data/portfolio_aum_state.json` | Persisted AUM state | L18: `"K280": 0.75` |
| `scripts/portfolio_aum_manager.py` | Default fallback weight | L86: `DEFAULT_SLEEVE_WEIGHTS["K280"] = 0.75` |
| `scripts/k280_daily_run.py` | Reads via `compute_position_size("K280")` | No direct weight constant |
| `scripts/k302a_satellite_run.py` | Display-only `K302A_MAIN_WEIGHT = 0.75` | L151 — DO NOT CHANGE |
| `scripts/verify_deployment_status.py` | Deployment state checker | Run post-patch for validation |

---

*K552 — concrete production patch — K339 REPO_ROOT pattern — READ-ONLY discovery — 2026-05-30 JST*

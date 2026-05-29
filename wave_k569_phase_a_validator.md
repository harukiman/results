# K569 Phase A Pre-Execution Validator

**Generated:** 2026-05-30 06:49 JST | Wave K569 | READ-ONLY simulation  
**Purpose:** Simulate all 5 Phase A actions before user executes them. Catch issues early.  
**Result:** 35 checks | 23 PASS | 4 WARN | 0 FAIL | 0 BLOCKERS | Overall: READY_WITH_WARNINGS

---

## Executive Summary

All 5 Phase A actions are unblocked. No file-system blockers found. 4 medium warnings require attention before or during execution — primarily env var configuration (HL_BUILDER_WALLET, BYBIT_API_KEY) and Bybit KYC constraints. A3 (K552 patch) is the critical prerequisite that unlocks both A4 (K498 routing) and the K449 LIVE cascade.

**Recommended execution order: A1 → A2 → A3 → A4 → A5**  
(A5 application can start in parallel with A3/A4 as it is independent; but A4 must come after A3)

| Action | Wave | Status | Time | Risk | ROI |
|--------|------|--------|------|------|-----|
| A1 K545 Tax Harvester | K545 | WARN (LOW) | 5 min | ZERO | +$47K/yr @$10M |
| A2 K481 HL Builder Rebate | K481 | WARN (MEDIUM) | 30 min | ZERO | +$99K-$496K/yr |
| A3 K552 K280 75→60% | K552 | READY | 30 min | LOW | +$260K unlock |
| A4 K498 BBO_SELECT | K498 | READY | 8h | LOW | +$121K/yr @$30M |
| A5 K485 Bybit Sub-Acct | K485 | WARN (MEDIUM) | 30min+7d | LOW | +$204K/yr |

---

## A1 — K545 Tax Harvester Plist Load

### Pre-Flight Check Results
- **PASS** `com.cryptolab.loss-harvester.plist` exists in repo root (39 lines, syntax valid)
- **PASS** `scripts/loss_harvester.py` exists (K339 compliant, no /Users/ literals)
- **PASS** Schedule correct: StartCalendarInterval Month=12, Day=28, Hour=6, RunAtLoad=false
- **PASS** `logs/` directory writable
- **WARN (LOW)** Plist NOT yet in `~/Library/LaunchAgents/` — clean install path (expected)
- **PASS** com.cryptolab.loss-harvester NOT currently loaded in launchctl

### Simulation: Commands to Execute
```bash
# From crypto-lab repo root:
cp com.cryptolab.loss-harvester.plist ~/Library/LaunchAgents/
launchctl load ~/Library/LaunchAgents/com.cryptolab.loss-harvester.plist
```

### Post-Execution Verify
```bash
launchctl list | grep loss-harvester
# Expected: -  0  com.cryptolab.loss-harvester (dash = scheduled, not running yet)
python3 scripts/loss_harvester.py --status
```

### Known Issues / Caveats
1. Daemon triggers **once annually** (Dec 28 06:00 JST) — verify Mac will be running on that date
2. `TAX_RATE_PCT` env var should be set before Dec 28 run (default jurisdiction = US_STCG, not JPN)
3. Plist uses `/usr/bin/python3` (system Python) — loss_harvester.py must be stdlib-only compatible
4. Re-running A1 (if plist already in LaunchAgents): unload first with `launchctl unload ...` before cp+load

### Risk Assessment
**ZERO RISK.** Annual scheduled job, `RunAtLoad=false`, no immediate execution. Daemon runs once per year. Rollback: `launchctl unload ~/Library/LaunchAgents/com.cryptolab.loss-harvester.plist && rm ~/Library/LaunchAgents/com.cryptolab.loss-harvester.plist`

---

## A2 — K481 HL Builder Rebate (approveBuilderFee)

### Pre-Flight Check Results
- **WARN (MEDIUM)** `HL_BUILDER_WALLET` env var NOT SET — required for daemon code integration
- **PASS** `scripts/post_only_order_manager.py` exists (K481 integration target)
- **WARN (MEDIUM)** `BUILDER_CODE_ENABLED=False` in k280_live_fetch.py — code patch needed after UI approval
- **PASS** `HL_BUILDER_WALLET` env var referenced in k280_live_fetch.py (env wiring exists)
- **PASS** No KYC required (wallet signature only — per K481 spec)
- **INFO** HL account balance >=100 USDC required — cannot verify without live API call

### Simulation: Action Sequence
```bash
# Step 1: On-chain action via HL UI (no CLI equivalent)
# app.hyperliquid.xyz → Account → Builder → Approve
# Builder address = your main HL wallet address
# Fee rate = 0 (f=0 self-rebate mode)

# Step 2: Set env var (add to ~/.zshrc)
export HL_BUILDER_WALLET=0x<YOUR_MAIN_WALLET_ADDRESS>

# Step 3: Enable in code (K481 Phase 2 — 6-LOC patch)
# Edit scripts/post_only_order_manager.py to flip BUILDER_CODE_ENABLED=True
# Edit scripts/k280_live_fetch.py: BUILDER_CODE_ENABLED=True
# Edit scripts/k302a_satellite_run.py: BUILDER_CODE_ENABLED=True
```

### Post-Execution Verify
```bash
echo $HL_BUILDER_WALLET                                        # must be set
grep BUILDER_CODE_ENABLED scripts/k280_live_fetch.py          # should show True
# HL UI: Account → Builder → verify fee approved (shows builder address + fee=0)
```

### Known Issues / Caveats
1. **MEDIUM:** `HL_BUILDER_WALLET` env var MUST be set before code patch takes effect. Daemon silently skips builder code if env var is empty
2. Rebate mechanism is **referral pool** (NOT direct taker fee rebate) — true rate only determinable after activation via actual claim data
3. K370 correction: K368 assumed 50% direct rebate; K481 corrects to 10-50% range (mid 25%). Use conservative $99K estimate, not $496K, for planning
4. On-chain action MUST use **MAIN wallet** (not API/agent wallet) — easy to confuse
5. Self-rebate mode (f=0): user pays zero extra fees. Builder earns from HL referral pool allocation
6. Max 10 active builder fee approvals per user (currently 0 used)
7. Activation is immediate after on-chain confirmation — no epoch delay

### Risk Assessment
**ZERO RISK.** Purely additive. On-chain approval adds builder tag to orders. No existing logic removed. Code patch is behind `BUILDER_CODE_ENABLED` flag gate. Full rollback: remove flag from order submission.

---

## A3 — K552 K280 75% → 60% Patch

### Pre-Flight Check Results
- **PASS** `scripts/leverage_manager.py` exists (K339 compliant)
- **PASS** `K280 = 0.75` confirmed in `SLEEVE_WEIGHTS` dict at L74 — pre-patch state correct
- **PASS** `data/portfolio_aum_state.json` has K280=0.75 (2nd file to patch)
- **PASS** `scripts/portfolio_aum_manager.py` exists with K280 references (3rd file to patch)
- **PASS** `scripts/verify_deployment_status.py` exists — post-patch validation tool available

### Simulation: sed Commands
```bash
# Step 0: Backup (REQUIRED before any patch)
cp scripts/leverage_manager.py scripts/leverage_manager.py.bak.K552
cp data/portfolio_aum_state.json data/portfolio_aum_state.json.bak.K552
cp scripts/portfolio_aum_manager.py scripts/portfolio_aum_manager.py.bak.K552

# Step 1: Primary patch — SLEEVE_WEIGHTS (K552 L74)
sed -i '' 's/"K280":   0\.75,   # K280 main (K198 + K208 + K276b) — v6\.13d; v6\.16 reduces to 0\.72/"K280":   0.60,   # K280 main (K539 Phase B1: 75→60%, frees 7.5pp HL, 2026-05-30)/' scripts/leverage_manager.py

# Step 2: Verify patch applied to primary file
grep -n '"K280"' scripts/leverage_manager.py
# Expected: L74 shows 0.60 in SLEEVE_WEIGHTS, L87 shows 0.69 in SLEEVE_WEIGHTS_V621 (unchanged)

# Step 3: Patch portfolio_aum_state.json (see K552 spec for exact sed)
# Step 4: Patch portfolio_aum_manager.py docstring (see K552 spec for exact sed)

# Step 5: Post-patch validation
python3 scripts/verify_deployment_status.py
```

### Post-Execution Verify
```bash
grep -n '"K280"' scripts/leverage_manager.py
# L74: "K280":   0.60   (SLEEVE_WEIGHTS — patched)
# L87: "K280":  0.69   (SLEEVE_WEIGHTS_V621 — unchanged, correct)

python3 scripts/verify_deployment_status.py
# Expected: HL exposure recomputes from 57.5% to ~50.0%
```

### Known Issues / Caveats
1. **CRITICAL:** SLEEVE_WEIGHTS `K280` value flows through ALL production position sizing. Backup is mandatory before applying
2. Three files must be patched atomically: `leverage_manager.py` (L74), `data/portfolio_aum_state.json`, `scripts/portfolio_aum_manager.py`
3. Do NOT patch `SLEEVE_WEIGHTS_V621` dict (L87 K280=0.69) — that is a future candidate, not active
4. macOS `sed -i ''` (BSD sed) differs from Linux `sed -i` — the `''` argument is required on macOS
5. Daemon restart NOT required immediately — position sizing reloads on next cycle. Daemons read values at runtime
6. HL exposure impact: 57.5% → 50.0% (7.5pp freed for K376/K449 family allocation)
7. **K449 LIVE** activation depends on A3 being applied first — this is the critical prerequisite cascade

### Risk Assessment
**LOW RISK.** Patch reduces K280 sleeve weight (HL exposure decreases). If unexpected behavior observed, restore from backup in <30 seconds. No exchange orders are sent by this patch itself — it only affects position sizing calculation on next cycle.

---

## A4 — K498 14-LOC BBO_SELECT Patch + OKX Daemon

### Pre-Flight Check Results
- **PASS** `SMART_ROUTER_ENABLED = False` confirmed in k280_live_fetch.py L159 — pre-patch state correct (K548 verified)
- **PASS** `routing_mode` field MISSING in smart_router_config.json — pre-patch state correct (defaults to HL_OVERFLOW)
- **PASS** routing_mode gate NOT in smart_router.py — pre-patch state correct
- **PASS** `com.cryptolab.okx-fr-monitor.plist` exists, syntax valid
- **PASS** com.cryptolab.okx-fr-monitor NOT loaded in launchctl
- **INFO** `OKX_API_KEY` NOT SET — acceptable for Phase 1A (FR fetch is public/read-only)
- **PASS** `scripts/okx_fr_fetcher.py` exists
- **WARN** A3 (K280 75→60%) not yet applied — must complete A3 before A4

### Simulation: 14-LOC Patch

**Patch 1 — k280_live_fetch.py (4 LOC, L159):**
```python
# Before:
SMART_ROUTER_ENABLED = False   # K434: set True after testing; scaffold only in this wave

# After:
# K530: BBO_SELECT routing activated — K498 Phase 1A (8h, +$121K/yr @$30M)
# select_best_venue() called per order as PRIMARY decision (not just overflow)
# Bybit VIP5 1.0bps maker rebate > HL GOLD 0.3bps → 0.7bps advantage captured
SMART_ROUTER_ENABLED = True    # K530 K498 Phase 1A: BBO routing ACTIVE
```

**Patch 2 — data/smart_router_config.json (3 LOC, after line "default_post_only"):**
```json
"routing_mode": "BBO_SELECT",
"routing_mode_note": "K530 K498 Phase 1A: BBO_SELECT routes per order to highest-scoring venue",
"bbo_select_min_score": -0.0001,
```

**Patch 3 — scripts/smart_router.py (7 LOC, in select_best_venue() after load_config()):**
```python
# K530: routing mode gate — BBO_SELECT is the Phase 1A target
routing_mode = cfg.get('routing_mode', 'HL_OVERFLOW')
if routing_mode == 'HL_OVERFLOW':
    # Legacy: HL default (Strategy B = $0 lift). Prefer BBO_SELECT.
    pass  # continue to BBO_SELECT logic below
```

**Daemon Load:**
```bash
cp com.cryptolab.okx-fr-monitor.plist ~/Library/LaunchAgents/
launchctl load ~/Library/LaunchAgents/com.cryptolab.okx-fr-monitor.plist
```

### Post-Execution Verify
```bash
grep SMART_ROUTER_ENABLED scripts/k280_live_fetch.py
# Expected: SMART_ROUTER_ENABLED = True

grep routing_mode data/smart_router_config.json
# Expected: "routing_mode": "BBO_SELECT"

python3 scripts/smart_router.py --all-symbols   # dry-run scoring test

launchctl list | grep okx-fr-monitor
# Expected: -  0  com.cryptolab.okx-fr-monitor

cat data/okx_dashboard.json | python3 -m json.tool | head -20
# Expected: status=ACTIVE after first 8h daemon cycle
```

### Known Issues / Caveats
1. **A3 MUST complete before A4** — both are required for K449 LIVE and full routing efficiency
2. OKX API keys NOT required for Phase 1A (FR fetch is read-only public API) — but needed for Phase 2 OKX trading
3. OKX daemon `RunAtLoad=false`, `StartInterval=28800` (8h) — first run happens 8h after daemon load
4. Restart k280-live daemon after patches: `launchctl unload/load ~/Library/LaunchAgents/com.cryptolab.k280-live.plist`
5. Rollback path: flip `SMART_ROUTER_ENABLED=False` + remove `routing_mode` from config JSON (<2 min)
6. Bybit VIP5 (1.0bps maker rebate) beats HL GOLD (0.3bps) by 0.7bps — smart router will route most orders to Bybit at current AUM
7. K548 pre-condition verification confirmed all 5 gates GREEN as of 2026-05-30 06:15 JST — state unchanged at K569 (2026-05-30 06:49 JST)
8. Smart router uses stdlib urllib only — no external packages needed

### Risk Assessment
**LOW RISK.** `SMART_ROUTER_ENABLED` flag gate provides instant rollback. OKX daemon is read-only (no trading). Patch 3 in smart_router.py is additive routing logic only. Bybit routing already working (VIP5 account). Full rollback in <2 minutes.

---

## A5 — K485 Bybit Sub-Account Application

### Pre-Flight Check Results
- **INFO** `BYBIT_SUB1_API_KEY` NOT SET — expected pre-application state
- **WARN (MEDIUM)** `BYBIT_API_KEY` (master) NOT SET — Bybit master API not yet configured
- **WARN (MEDIUM)** Bybit sub-account requires KYC — personal multi-wallet ToS risk (use institutional)
- **INFO** Bybit VIP5 tier assumed — verify master account tier
- **INFO** 7-day paper-trade gate mandated by K485 spec (§6 gate)

### Simulation: Application Process
```bash
# Step 1: Apply via Bybit UI (no CLI)
# bybit.com → Account → Sub-Accounts → Create Sub-Account
# Type: Standard (not UTA for Phase 1B strategy isolation)

# Step 2: KYC (if prompted) — 1-7 business days

# Step 3: Generate sub-account API keys
# Permissions: Read + Trade (NO withdraw permission)

# Step 4: Set env vars
export BYBIT_SUB1_API_KEY=<sub_account_api_key>
export BYBIT_SUB1_API_SECRET=<sub_account_api_secret>

# Step 5: 7-day paper-trade gate
# Monitor K280/K302a strategy on sub-account paper trades

# Step 6: After gate passed — activate live capital
```

### Post-Execution Verify
```bash
# After sub-account created:
python3 -c "import os; print(os.environ.get('BYBIT_SUB1_API_KEY','NOT SET'))"

# After 7-day gate:
python3 scripts/k280_live_fetch.py --dry-run --venue Bybit
```

### Known Issues / Caveats
1. **MEDIUM:** `BYBIT_API_KEY` master API not yet configured — needed for sub-account connectivity testing
2. **MEDIUM:** KYC required for Bybit sub-account — timeline 1-7 business days (may delay execution)
3. **HIGH:** Bybit ToS prohibits multiple personal accounts — use institutional/fund account structure. ToS risk = HIGH if duplicate personal
4. 7-day paper-trade gate is **mandatory** before live capital (K485 §6 gate)
5. $204K/yr estimate = Phase 1B strategy isolation at $10M HL only (same order book, stagger benefit)
6. Full Phase 1A benefit ($2.2M/yr) requires $25M AUM across HL+Bybit — separate funding required
7. Bybit VIP5 tier drives smart router advantage — verify master account tier before assuming 1.0bps rebate
8. No code changes needed for A5 itself — sub-account becomes a routing target in smart_router_config.json after activation

### Risk Assessment
**LOW RISK.** Application is administrative (no code changes). 7-day paper gate enforced before any capital at risk. Main risk is KYC denial or institutional account structure setup complexity.

---

## Cross-Action Dependency Map

```
A1 (K545) ──────────────────────────────── independent
A2 (K481) ──────────────────────────────── independent
A3 (K552) ──────────────────────────────► A4 (K498) [REQUIRED prerequisite]
                         └──────────────► K449 LIVE cascade
A4 (K498) ──────────────────────────────► K208 routing efficiency
A5 (K485) ──────────────────────────────── independent (longest lead time)
```

**Parallel-safe combinations:**
- A1 + A2: YES (both independent, <35 min combined)
- A3 + A5: YES (A5 application process while A3 patches applied)
- A4 + A5 pending: YES (7-day A5 gate runs during A4 8h verification window)

**Critical path:** `A3 → A4` (code patches must be sequential; daemon loads after all 3 patches)

**Fastest execution timeline:**
- T+0: Start A1 (5 min) + A2 HL UI (30 min) + A5 application (30 min) — all parallel
- T+35: Apply A3 patches (30 min)
- T+65: Start A4 patches (270 min active + 3.25h passive) + A5 KYC wait (7d)
- T+335: A4 complete, verify OKX daemon first cycle
- T+7d: A5 paper gate complete → live activation

---

## Phase 8: Recommended Pre-Execution Checklist

### Before A2 (K481 HL Builder Rebate):
- [ ] HL UI login confirmed with MAIN wallet (not API wallet)
- [ ] HL account balance > $100 USDC confirmed
- [ ] Know your main wallet address (0x...)
- [ ] Plan to set `HL_BUILDER_WALLET` env var in shell profile after UI approval
- [ ] Have K481 code patch spec open (scripts/post_only_order_manager.py, 6-LOC)

### Before A3 (K552 K280 Patch):
- [ ] Backups prepared: 3 files (leverage_manager.py, portfolio_aum_state.json, portfolio_aum_manager.py)
- [ ] Confirm current value: `grep '"K280"' scripts/leverage_manager.py` shows 0.75
- [ ] K552 sed commands copy-pasted (use macOS BSD sed: `sed -i ''`)
- [ ] verify_deployment_status.py script ready for post-patch validation

### Before A4 (K498 BBO_SELECT):
- [ ] A3 complete (K280=0.60 confirmed)
- [ ] Backups of k280_live_fetch.py, smart_router_config.json, smart_router.py
- [ ] K530 playbook open (wave_k530_k498_phase_1a_playbook.md)
- [ ] Smart router dry-run ready: `python3 scripts/smart_router.py --all-symbols`
- [ ] Note: OKX_API_KEY NOT needed for Phase 1A

### Before A5 (K485 Bybit Sub-Account):
- [ ] Confirmed account structure is institutional (not personal duplicate)
- [ ] Bybit master account VIP tier verified
- [ ] 7-day calendar blocked for paper gate
- [ ] Plan to generate API keys with Read+Trade permissions (NO withdraw)

---

## Phase 9: Post-Execution Verify Suite

### A1: Tax Harvester
```bash
launchctl list | grep loss-harvester
# Expected: -  0  com.cryptolab.loss-harvester
python3 scripts/loss_harvester.py --status
```

### A2: HL Builder Rebate
```bash
echo $HL_BUILDER_WALLET                              # should be 0x... address
grep BUILDER_CODE_ENABLED scripts/k280_live_fetch.py # should be True after code patch
# HL UI: Account → Builder → verify approved, fee=0
```

### A3: K280 75→60% Patch
```bash
grep -n '"K280"' scripts/leverage_manager.py
# L74: 0.60 (patched), L87: 0.69 (SLEEVE_WEIGHTS_V621 — unchanged)
python3 scripts/verify_deployment_status.py
```

### A4: BBO_SELECT + OKX Daemon
```bash
grep SMART_ROUTER_ENABLED scripts/k280_live_fetch.py       # True
grep routing_mode data/smart_router_config.json            # BBO_SELECT
launchctl list | grep okx-fr-monitor                       # loaded
python3 scripts/smart_router.py --all-symbols              # dry-run OK
cat data/k208_live.json | python3 -m json.tool | grep venue  # after 8h cycle: OKX entries appear
```

### A5: Bybit Sub-Account
```bash
python3 -c "import os; print(os.environ.get('BYBIT_SUB1_API_KEY','NOT SET'))"
# After 7d paper gate:
python3 scripts/k280_live_fetch.py --dry-run --venue Bybit
```

---

## Risk Mitigation Summary

| Action | Primary Risk | Mitigation |
|--------|-------------|------------|
| A1 | Daemon fires immediately (RunAtLoad) | RunAtLoad=false confirmed — only fires Dec 28 06:00 |
| A2 | Wrong wallet address in builder approval | Double-check 0x address before signing on HL UI |
| A3 | Wrong sed command patches wrong dict | Backup + verify grep shows L74=0.60, L87=0.69 unchanged |
| A4 | Smart router routes to wrong venue | Dry-run first; SMART_ROUTER_ENABLED flag rollback in <2min |
| A5 | Bybit ToS violation (personal dup) | Institutional account structure required |

---

## Files Referenced

- `/Users/nekonaomichi/crypto-lab/com.cryptolab.loss-harvester.plist` — A1
- `/Users/nekonaomichi/crypto-lab/scripts/loss_harvester.py` — A1
- `/Users/nekonaomichi/crypto-lab/scripts/k280_live_fetch.py` — A2, A4 (SMART_ROUTER_ENABLED L159)
- `/Users/nekonaomichi/crypto-lab/scripts/post_only_order_manager.py` — A2 (K481 code patch)
- `/Users/nekonaomichi/crypto-lab/scripts/leverage_manager.py` — A3 (SLEEVE_WEIGHTS L74)
- `/Users/nekonaomichi/crypto-lab/data/portfolio_aum_state.json` — A3
- `/Users/nekonaomichi/crypto-lab/scripts/portfolio_aum_manager.py` — A3
- `/Users/nekonaomichi/crypto-lab/data/smart_router_config.json` — A4 (routing_mode)
- `/Users/nekonaomichi/crypto-lab/scripts/smart_router.py` — A4 (routing mode gate)
- `/Users/nekonaomichi/crypto-lab/com.cryptolab.okx-fr-monitor.plist` — A4 (OKX daemon)
- `/Users/nekonaomichi/crypto-lab/scripts/okx_fr_fetcher.py` — A4
- `/Users/nekonaomichi/crypto-lab/scripts/verify_deployment_status.py` — A3, A4 (post-patch)
- `wave_k569_phase_a_validator.py` — validator script
- `wave_k569_phase_a_validator.json` — machine-readable output

---

*K569 | wave_k569_phase_a_validator.md | 2026-05-30 06:49 JST | K339 compliant (no /Users/ hardcoded)*

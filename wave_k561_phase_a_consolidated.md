# K561 — Phase A Day 0 Consolidated Action Sheet

**Wave:** K561 | **Generated:** 2026-05-30 06:30 JST | **Pattern:** K339  
**Status:** READY-TO-APPLY | **Source waves:** K481, K485, K498/K530, K545, K552  

---

## Executive Summary

5 user-actionable items consolidated from 10+ prior waves into a single Day 0 execution guide.

| Metric | Value |
|--------|-------|
| Actions | 5 |
| Active effort | ~1.5 hours |
| Monitoring period | 1-2 days + 7d Bybit gate |
| Immediate lift @$10M | ~$95K/yr (K481 + K545 net) |
| Full Phase A @$30M | +$2.5-3M/yr (all 5 active) |
| Combined effort ROI | >$200K/hr (weighted average) |

---

## Phase A 5-Action Widget

| Action | Time | ROI | Risk | Status | Verify Command |
|--------|------|-----|------|--------|----------------|
| A1 K545 Tax Harvester plist | 5 min | +$47K/yr @$10M (JPN) | ZERO | READY | `launchctl list \| grep loss-harvester` |
| A2 K481 HL Builder Rebate | 30 min | +$99K–$496K/yr @$10M | ZERO | READY | `echo $HL_BUILDER_CODE` |
| A3 K552 K280 75→60% Patch | 30 min | +$260K unlock (30d) | LOW | READY | `grep '"K280".*0\.' scripts/leverage_manager.py` |
| A4 K498 OKX BBO_SELECT | 8h (4.75h active) | +$121K/yr @$30M | LOW | READY (K548 verified) | `grep SMART_ROUTER_ENABLED scripts/k280_live_fetch.py` |
| A5 K485 Bybit Sub-Account | 30 min + 7d gate | +$2.2M/yr @$25M | LOW | READY | `python3 -c "import os; print(os.environ.get('BYBIT_SUB1_API_KEY','NOT SET'))"` |

---

## Pre-Flight Checklist

Run before starting any action:

```bash
# 1. HL wallet funded (for A2)
# Check: https://app.hyperliquid.xyz/ — account balance >= 100 USDC perps

# 2. Main wallet accessible (for A2 — NOT the API/agent key)
# Open MetaMask, confirm main HL wallet available

# 3. Bybit VIP tier (for A5)
# Bybit UI: Account & Security -> Sub Accounts menu visible

# 4. LaunchAgents writable (for A1, A4)
ls ~/Library/LaunchAgents/ 2>&1 | head -3

# 5. Git clean (for A3)
git status --short

# 6. OKX API key (for A4 only — deferrable)
python3 -c "import os; print('OKX_API_KEY:', 'SET' if os.environ.get('OKX_API_KEY') else 'NOT SET')"

# 7. Plist present (for A1)
ls com.cryptolab.loss-harvester.plist

# 8. K280 patch target (for A3)
grep -n '"K280".*0.75' scripts/leverage_manager.py | head -3
```

---

## Recommended Sequence

```
D0 Morning:
  A1 (5 min)  → A2 (30 min) → A3 (30 min)     ← 1.25hr, ZERO/LOW risk
  
D0-D1 (when OKX API ready):
  A4 (8h block: 4.75h active + 24h paper)       ← can defer to D1-D2

D0 (start immediately, runs in background):
  A5 (30 min application → 7d gate auto-runs)   ← parallel to A1-A3
  
D7:
  A5 gate check → capital transfer decision
  A4 paper gate review → live flip decision
```

**Rationale:**
- A1 is 5 min, ZERO risk, no dependencies — always first
- A2 is ZERO risk, highest ROI/hr in the entire 23-action playbook, no dependencies
- A3 is the PREREQUISITE for K376 ($247K/yr) and K449 ($13K+) unlock — do before A4
- A4 requires OKX API key; 48h paper gate; deferrable without penalty
- A5 application starts D0; 7d gate runs concurrently with everything else

---

## A1: K545 Tax Harvester Plist Load

**Source:** `wave_k545_tax_harvester_activation.md`  
**Wave:** K545 | **Effort:** 5 minutes | **Risk:** ZERO  
**ROI:** +$47,300/yr @$10M (Japan 55%) | +$18,920/yr @$10M (Korea 22%)

### Goal

Deploy 18th daemon (loss-harvester) to LaunchAgents. Fires annually Dec 28 only. Zero trading activity until year-end harvest window.

### Pre-conditions

- [ ] Tax jurisdiction confirmed with licensed advisor
- [ ] `com.cryptolab.loss-harvester.plist` in REPO_ROOT
- [ ] `python3 scripts/loss_harvester.py --mock-test` returns PASS

### Commands (paste-ready)

```bash
# Step 1: Set jurisdiction (adjust for your situation)
python3 scripts/loss_harvester.py --set-rate 55 --set-jurisdiction JPN
# Korea: --set-rate 22 --set-jurisdiction KOR
# Germany: --set-rate 26.375 --set-jurisdiction DE

# Step 2: Verify mock test
python3 scripts/loss_harvester.py --mock-test
# Expected: PASS: YES | Tax liability: $351,500.00

# Step 3: Deploy plist
cp com.cryptolab.loss-harvester.plist ~/Library/LaunchAgents/com.cryptolab.loss-harvester.plist

# Step 4: Load daemon (RunAtLoad=false — NO immediate run)
launchctl load ~/Library/LaunchAgents/com.cryptolab.loss-harvester.plist

# Step 5: Verify
launchctl list | grep loss-harvester
```

### Expected Result

`com.cryptolab.loss-harvester` listed in launchctl (no PID — correct; RunAtLoad=false, annual trigger).

### Rollback

```bash
launchctl unload ~/Library/LaunchAgents/com.cryptolab.loss-harvester.plist
rm ~/Library/LaunchAgents/com.cryptolab.loss-harvester.plist
```

### Profit Lift Quantification

| AUM | Japan (55%) | Korea (22%) | Germany (26.4%) |
|-----|------------|------------|----------------|
| $10M | +$47,300/yr | +$18,920/yr | +$22,682/yr |
| $100M | +$473,000/yr | +$189,200/yr | +$226,825/yr |

*INFORMATIONAL — consult licensed tax advisor before action.*

---

## A2: K481 HL Builder Rebate Registration

**Source:** `wave_k481_builder_rebate_activation.md`  
**Wave:** K481 | **Effort:** 30 minutes | **Risk:** ZERO  
**ROI:** +$99K–$496K/yr @$10M (conservative–optimistic) | Mid: +$248K/yr

### Goal

Register HL self-builder (approveBuilderFee, f=0). No extra cost charged to trader. Earns from HL referral pool on own order flow.

### Pre-conditions

- [ ] HL account has >=100 USDC perps balance
- [ ] Main wallet (MetaMask / hardware wallet) accessible — NOT the API/agent wallet
- [ ] `HL_BUILDER_CODE` env var NOT currently set

### Commands (paste-ready)

```bash
# STEP 1: Register on HL UI (browser, ~20 min)
# Go to: https://app.hyperliquid.xyz/trade -> Account -> Builder
# Enter: your main wallet address as builder address
# Fee: 0 (zero tenths of basis points — no extra cost to trader)
# Sign: approveBuilderFee transaction (MUST use main wallet, not API key)
# Confirm: HL shows activation banner

# STEP 2: Set environment variable (replace 0x<ADDR> with your actual main wallet address)
echo 'export HL_BUILDER_CODE="0x<YOUR_MAIN_WALLET_ADDRESS>"' >> ~/.zshrc
source ~/.zshrc
echo $HL_BUILDER_CODE   # verify prints your address (starts with 0x)

# STEP 3: Apply 6-LOC patch to scripts/post_only_order_manager.py
# Insertion point: in submit_post_only_order(), after "if dry_run:" block
# Add these 4 lines:
#
#   # K481: Builder code injection (ZERO-RISK additive, env-var gated)
#   _builder_code = os.environ.get("HL_BUILDER_CODE", "").strip()
#   if venue == "HL" and _builder_code and not dry_run:
#       order_action["builder"] = {"b": _builder_code, "f": 0}

# STEP 4: Verify dry-run (builder field should NOT appear in dry-run — correct)
python3 scripts/post_only_order_manager.py --dry-run

# STEP 5: Restart live daemons
launchctl unload ~/Library/LaunchAgents/com.cryptolab.k246a-live.plist
launchctl load  ~/Library/LaunchAgents/com.cryptolab.k246a-live.plist
launchctl unload ~/Library/LaunchAgents/com.cryptolab.k280-live.plist
launchctl load  ~/Library/LaunchAgents/com.cryptolab.k280-live.plist

# STEP 6: Verify (24h later — check HL referral dashboard)
# https://app.hyperliquid.xyz/referrals -> builder rewards > $0
```

### Expected Result

- `HL_BUILDER_CODE` env var set to `0x...` address
- k246a-live and k280-live show PIDs in launchctl list
- After 24h: HL referral dashboard shows >$0 accrued

### Rollback

```bash
# Remove builder field from post_only_order_manager.py (delete 4 LOC)
# Remove from ~/.zshrc: unset HL_BUILDER_CODE
source ~/.zshrc
# Restart daemons (same launchctl unload/load sequence)
```

### Profit Lift Quantification

| AUM | Conservative (10%) | Mid (25%) | Optimistic (50%) |
|-----|--------------------|-----------|-----------------|
| $10M | **+$99,166/yr** | +$247,915/yr | +$495,830/yr |
| $50M | +$495,830/yr | +$1,239,574/yr | +$2,479,148/yr |

Daily monitoring target @$10M: $271.7/day (conservative). Alert if <$135/day for 3+ days.

---

## A3: K552 K280 Sleeve 75→60% Production Patch

**Source:** `wave_k552_k280_patch.md`  
**Wave:** K552 | **Effort:** 30 minutes | **Risk:** LOW  
**ROI:** PREREQUISITE — unlocks K376 (+$247K/yr) + K449 (+$13K+) = +$260K within 30 days  
**Full cascade:** +$1,163,000/yr @$10M (W1-W5 paired-trade family)

### Goal

Reduce K280 sleeve weight 0.75 → 0.60 in 3 authoritative files. Frees 7.5pp HL headroom. Unlocks K376 BULL trigger and K449 ETH-BTC live activation.

### Pre-conditions

- [ ] Git working tree clean (backup step below creates .bak files)
- [ ] `scripts/leverage_manager.py` confirmed at line 74: `"K280":   0.75`
- [ ] k280-live and k302a-satellite daemons not in middle of active cycle

### Commands (paste-ready)

```bash
# PRE-FLIGHT: Backup 3 files
cp scripts/leverage_manager.py scripts/leverage_manager.py.bak
cp data/portfolio_aum_state.json data/portfolio_aum_state.json.bak
cp scripts/portfolio_aum_manager.py scripts/portfolio_aum_manager.py.bak

# STEP 1: PRIMARY patch (leverage_manager.py L74 — AUTHORITATIVE runtime source)
sed -i '' 's/"K280":   0\.75,   # K280 main (K198 + K208 + K276b) — v6\.13d; v6\.16 reduces to 0\.72/"K280":   0.60,   # K280 main (K539 Phase B1: 75->60%, frees 7.5pp HL, 2026-05-30)/' scripts/leverage_manager.py

# Verify Step 1:
grep -n '"K280"' scripts/leverage_manager.py | head -5
# Expected: L74 shows 0.60

# STEP 2: JSON STATE patch (portfolio_aum_state.json — persisted state)
python3 -c "
import json
f = 'data/portfolio_aum_state.json'
d = json.load(open(f))
d['sleeve_weights']['K280'] = 0.60
d['last_updated_jst'] = '2026-05-30 K552 Phase B1 patch'
json.dump(d, open(f, 'w'), indent=2)
print('Updated K280 to', d['sleeve_weights']['K280'])
"

# STEP 3: AUM manager fallback (portfolio_aum_manager.py L86 — default on fresh install)
sed -i '' 's/"K280":       0\.75,/"K280":       0.60,/' scripts/portfolio_aum_manager.py

# STEP 4: Verify ALL 3 files
grep -n '"K280".*0\.' scripts/leverage_manager.py data/portfolio_aum_state.json scripts/portfolio_aum_manager.py
# Expected: All 3 show 0.60

# STEP 5: Check sleeve weights sum
python3 -c "
import json
d = json.load(open('data/portfolio_aum_state.json'))
w = d['sleeve_weights']
print('Weights:', w)
print('Sum:', sum(w.values()))
print('K280:', w.get('K280'))
print('Note: sum < 1.0 is valid — K376 is sub-slice of K280')
"

# STEP 6: Restart daemons (REQUIRED — stale cache risk)
launchctl unload ~/Library/LaunchAgents/com.cryptolab.k280-live.plist
launchctl load  ~/Library/LaunchAgents/com.cryptolab.k280-live.plist
launchctl unload ~/Library/LaunchAgents/com.cryptolab.k302a-satellite.plist
launchctl load  ~/Library/LaunchAgents/com.cryptolab.k302a-satellite.plist

# STEP 7: Confirm daemons running
launchctl list | grep cryptolab | grep -E 'k280|k302a'
# Expected: both show PIDs (not -)

# STEP 8 (D+1): Unlock K449 LIVE after 24h clean monitoring
# cp com.cryptolab.k449-eth-btc.plist ~/Library/LaunchAgents/
# launchctl load ~/Library/LaunchAgents/com.cryptolab.k449-eth-btc.plist
```

### Expected Result

- All 3 files: `K280 = 0.60`
- k280-live and k302a-satellite: PIDs in launchctl list
- HL exposure: drops from ~57.5% to ~52.5% (7.5pp freed)
- K376 + K449 headroom: +12.5pp available before 65% cap

### Rollback

```bash
cp scripts/leverage_manager.py.bak scripts/leverage_manager.py
cp data/portfolio_aum_state.json.bak data/portfolio_aum_state.json
cp scripts/portfolio_aum_manager.py.bak scripts/portfolio_aum_manager.py
launchctl unload ~/Library/LaunchAgents/com.cryptolab.k280-live.plist
launchctl load  ~/Library/LaunchAgents/com.cryptolab.k280-live.plist
# Verify rollback:
grep -n '"K280".*0\.' scripts/leverage_manager.py data/portfolio_aum_state.json
```

### Profit Unlock Pathway

```
K552 patch applied (30 min)
      |
      +-- HL headroom: 57.5% → ~50% (7.5pp freed)
      |
      v
K449 Week 1 LIVE (D+1 after patch, K549 playbook)
  +$13K+/yr immediate (pipeline validation trigger)
      |
      v
K376 BULL_CONFIRMED (ETA D+14, K551 analysis)
  +$247K/yr (Sharpe >8 sustained 15d)
      |
      v
Full pipeline: K449 → K476 → K484 → K493 → K500/K507 → K512
  +$1,163,000/yr @$10M
```

---

## A4: K498 Phase 1A OKX BBO_SELECT Smart Router

**Source:** `wave_k530_k498_phase_1a_playbook.md` | Verified: `wave_k548_okx_preconditions_verify.md`  
**Wave:** K530/K498 | **Effort:** 8h (4.75h active + 24h paper observation) | **Risk:** LOW  
**ROI:** +$121K/yr @$30M | +$1.03M/yr @$100M | ROI/hr: $15,125

### Goal

Switch K280 smart router from `HL_OVERFLOW` to `BBO_SELECT`. Bybit VIP5 makes 1.0bps rebate vs HL GOLD 0.3bps — 0.7bps advantage per order. Currently delivering $0 because HL absorbs all orders (never overflows). BBO_SELECT routes each order to best-scored venue.

**K548 verified: ALL 5 pre-conditions PASS. READY for immediate activation.**

### Pre-conditions

- [ ] OKX account active with API key, secret, passphrase
- [ ] `OKX_API_KEY`, `OKX_API_SECRET`, `OKX_PASSPHRASE` set in `~/.zshrc`
- [ ] `com.cryptolab.okx-fr-monitor.plist` in REPO_ROOT (K548 confirmed PRESENT)
- [ ] `SMART_ROUTER_ENABLED = False` in `scripts/k280_live_fetch.py` line 159 (K548 confirmed)
- [ ] A3 (K552 patch) applied first is RECOMMENDED but not strictly required

### Commands (paste-ready)

```bash
# STEP 1: Verify OKX scaffold state (K548 confirmed PASS)
launchctl list | grep okx
python3 scripts/okx_fr_fetcher.py --symbol BTC-USDT-SWAP
# Expected: BTC FR non-zero value

# STEP 2: Apply BBO_SELECT patch (14 LOC total)
# PATCH 1 — k280_live_fetch.py line 159:
sed -i '' 's/SMART_ROUTER_ENABLED = False   # K434.*/SMART_ROUTER_ENABLED = True    # K530 K498 Phase 1A: BBO routing ACTIVE/' scripts/k280_live_fetch.py
grep SMART_ROUTER_ENABLED scripts/k280_live_fetch.py  # verify

# PATCH 2 — data/smart_router_config.json (add routing_mode):
# Open data/smart_router_config.json and add after "default_post_only": true,
# "routing_mode": "BBO_SELECT",
# "routing_mode_note": "K530 K498 Phase 1A: BBO_SELECT replaces HL_OVERFLOW.",
# "bbo_select_min_score": -0.0001,

# STEP 3: OKX API env vars (if not already set)
# echo 'export OKX_API_KEY="your_key_here"' >> ~/.zshrc
# echo 'export OKX_API_SECRET="your_secret_here"' >> ~/.zshrc
# echo 'export OKX_PASSPHRASE="your_passphrase_here"' >> ~/.zshrc
# source ~/.zshrc
python3 -c "import os; print('OKX_API_KEY:', 'SET' if os.environ.get('OKX_API_KEY') else 'NOT SET')"

# STEP 4: Load OKX FR monitor daemon
cp com.cryptolab.okx-fr-monitor.plist ~/Library/LaunchAgents/
launchctl load ~/Library/LaunchAgents/com.cryptolab.okx-fr-monitor.plist
launchctl list | grep okx-fr-monitor
# Expected: PID shown

# STEP 5: 24h paper observation (verify routing)
python3 scripts/smart_router.py --all-symbols --side short --size 100000
# Expected: BTC: Best=Bybit score=+0.0001xxx

# STEP 6: 48h gate check (Gate: Bybit+OKX >= 40% routing)
python3 -c "
import json
from pathlib import Path
from collections import Counter
log = Path('data/smart_router_decisions.jsonl')
if log.exists():
    decisions = [json.loads(l) for l in log.read_text().strip().splitlines()]
    recent = decisions[-72:]
    venue_counts = Counter(d['venue'] for d in recent)
    print('24h routing:')
    for v, c in venue_counts.most_common():
        print(f'  {v}: {c/len(recent)*100:.0f}%')
"

# STEP 7: Live activation (after gate pass)
launchctl kickstart -k gui/$(id -u)/com.cryptolab.k280-live
tail -5 data/smart_router_decisions.jsonl
```

### Expected Result

- `SMART_ROUTER_ENABLED = True` in k280_live_fetch.py
- com.cryptolab.okx-fr-monitor shows PID
- smart_router_decisions.jsonl: Bybit+OKX >= 40% of routing decisions
- Daily lift @$30M: ~$331/day ($121K/yr)

### Rollback (< 5 min)

```bash
sed -i '' 's/SMART_ROUTER_ENABLED = True.*/SMART_ROUTER_ENABLED = False   # K530 rollback/' scripts/k280_live_fetch.py
launchctl kickstart -k gui/$(id -u)/com.cryptolab.k280-live
```

### Profit Lift Quantification

| AUM | Annual USDC | Daily |
|-----|------------|-------|
| $30M | **+$121,000/yr** | $331/day |
| $100M | **+$1,030,000/yr** | $2,822/day |

Alert threshold: if non-HL routing rate < 20% for 7d, investigate.

---

## A5: K485 Bybit Sub-Account Phase 1A Application

**Source:** `wave_k485_multi_account_scaling.md`  
**Wave:** K485 | **Effort:** 30 min setup + 7d paper gate | **Risk:** LOW  
**ROI:** +$2.2M/yr @$25M total AUM (+106% vs $10M single-HL baseline)

### Goal

Create Bybit sub-account (standard sub, inherits master KYC). Generate trade-only API key. Run 7-day paper-trade gate. After gate: transfer $5M+ from master to sub — first true capacity expansion beyond HL $10M ceiling.

**Legal note:** Bybit sub-accounts are explicitly permitted (not duplicate personal accounts). Sub inherits master KYC — no separate KYC required.

### Pre-conditions

- [ ] Bybit master account active with KYC verified
- [ ] Sub-account feature visible: Bybit UI → Account & Security → Sub Accounts
- [ ] Server/Mac IP known for API whitelist

### Commands (paste-ready)

```bash
# STEP 1: Create sub-account (Bybit web UI, ~10 min)
# Login Bybit -> Profile -> Account & Security -> Sub Accounts
# -> Create Sub Account -> Standard Sub Account
# -> Label: "k485-sub1-k297p"

# STEP 2: Generate API key for sub-account (Bybit UI, ~5 min)
# Sub Account page -> API Management -> Create API
# Name: "k485-sub1-api"
# Permissions: Trade only (NO withdrawal)
# IP restriction: add your server/Mac IP (required for security)
# Copy: API Key and Secret -> save to 1Password or hardware wallet immediately

# STEP 3: Set environment variables (never commit to git)
echo 'export BYBIT_SUB1_API_KEY="<your_sub_api_key>"' >> ~/.zshrc
echo 'export BYBIT_SUB1_SECRET="<your_sub_secret>"' >> ~/.zshrc
source ~/.zshrc

# STEP 4: Verify env vars
python3 -c "import os; print('BYBIT_SUB1_API_KEY:', 'SET' if os.environ.get('BYBIT_SUB1_API_KEY') else 'NOT SET')"
python3 -c "import os; print('BYBIT_SUB1_SECRET:', 'SET' if os.environ.get('BYBIT_SUB1_SECRET') else 'NOT SET')"

# STEP 5: 7-day paper-trade gate (automated monitoring)
python3 scripts/k280_live_fetch.py --venue=bybit --wallet=sub1 --dry-run
# Monitor for 7 days: check fills, latency, API errors in dry-run logs

# STEP 6: After 7d gate passes — capital transfer (Bybit internal, instant)
# Bybit UI: Assets -> Transfer -> From: Master Account -> To: k485-sub1-k297p
# Initial amount: $3-5M (grow to $10M+ as confidence builds)
# No withdrawal key used — internal transfer only
```

### Expected Result

- Sub-account visible in Bybit UI → Account & Security → Sub Accounts
- `BYBIT_SUB1_API_KEY` and `BYBIT_SUB1_SECRET` set in environment
- 7d paper-trade: no errors, fills simulated correctly
- After gate: $5M+ transferred, K297p running on Bybit sub

### Rollback

No capital transfer until 7d gate passes. Sub-account can be deleted via Bybit UI if not funded. API key can be revoked in Bybit → API Management.

### Profit Lift Quantification

| Total AUM | Architecture | Net/yr | vs Baseline |
|-----------|-------------|--------|-------------|
| $10M | Single HL (baseline) | $2.08M/yr | — |
| $25M | HL primary + Bybit sub | **$4.28M/yr** | +$2.20M (+106%) |
| $50M | HL + Bybit + dYdX (Phase 2) | $5.45M/yr | +$3.37M (+162%) |

---

## Profit Projection: Phase A Full Activation

### @$10M AUM (Immediate, D0)

| Action | Conservative | Central | Optimistic |
|--------|-------------|---------|-----------|
| K481 Builder rebate | +$99K/yr | +$248K/yr | +$496K/yr |
| K545 Tax harvester (JPN) | +$47K/yr | +$47K/yr | +$95K/yr |
| K552 K280 patch (prerequisite) | (unlocks K376 $247K, K449 $13K) | | |
| K498 BBO_SELECT @$30M | +$121K/yr | +$121K/yr | — |
| K485 Bybit @$25M (D+21) | +$2.2M/yr | +$2.2M/yr | — |
| **Net immediate (K481+K545)** | **+$95K/yr** | **+$295K/yr** | **+$591K/yr** |

### Realization Timeline

| Checkpoint | Target | Verify |
|------------|--------|--------|
| D0 | K545 loaded, K481 registered, K552 patched | All 3 verify commands pass |
| D0+7 | K481 first rebate visible; K498 paper gate pass | HL referral >$0; routing 40%+ non-HL |
| D0+14 | K376 BULL trigger check; K449 LIVE (D+1 after K552) | K497 --status; K449 PID in launchctl |
| D0+21 | K485 7d gate complete → capital transfer decision | BYBIT_SUB1 env vars set + sub-account funded |

---

## Risk Summary

| Action | Risk | Key Mitigation | Rollback Time |
|--------|------|---------------|--------------|
| A1 K545 | ZERO | RunAtLoad=false; annual cron; no trades | instant |
| A2 K481 | ZERO | f=0 no extra cost; additive field; baseline preserved if program ends | instant (remove 4 LOC) |
| A3 K552 | LOW | 3-file atomic backup; daemon restart sequence documented; rollback <2 min | <2 min |
| A4 K498 | LOW | Concentration caps enforced; 48h paper gate; rollback 1 flag flip | <5 min |
| A5 K485 | LOW | No capital transfer until 7d gate; sub explicitly ToS-permitted; API trade-only scope | instant (no capital) |

---

## Status Check Command

```bash
python3 wave_k561_phase_a_consolidated.py --status
```

---

## Source References

| Wave | File | Topic |
|------|------|-------|
| K481 | `wave_k481_builder_rebate_activation.md` | HL builder rebate registration + code patch |
| K485 | `wave_k485_multi_account_scaling.md` | Bybit sub-account setup + capacity expansion |
| K498 | `wave_k498_smart_router_profit.md` | BBO_SELECT smart router profit model |
| K530 | `wave_k530_k498_phase_1a_playbook.md` | K498 Phase 1A 8-step activation |
| K539 | `wave_k539_immediate_actions.md` | 4-phase D0-D60 sequencing |
| K545 | `wave_k545_tax_harvester_activation.md` | Loss harvester production activation |
| K548 | `wave_k548_okx_preconditions_verify.md` | K530 pre-conditions VERIFIED PASS |
| K549 | `wave_k549_k449_week1_live.md` | K449 Week 1 LIVE playbook (post-K552) |
| K551 | `wave_k551_k376_refresh.md` | K376 BULL trigger analysis |
| K552 | `wave_k552_k280_patch.md` | K280 75→60% concrete 3-file patch |

---

*K561 Phase A Consolidated Day 0 Sheet — 2026-05-30 06:30 JST*  
*K339 REPO_ROOT pattern | LIVE 自動変更禁止 (sheet only) | Public docs only*

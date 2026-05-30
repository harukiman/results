# K709 — Day 0 Unified Execution Single-Page Sheet

**Wave:** K709 | **Generated:** 2026-05-30 16:20 JST | **Pattern:** K339  
**Status:** READY-TO-EXECUTE | **Source waves:** K674/K702/K706/K705/K700/K561/K539  
**Constraint:** LIVE 自動変更禁止 — manual execution only

---

## Profit Summary

| Scope | USD/yr | Notes |
|-------|--------|-------|
| Phase A immediate | **+$146,300/yr @$10M** | K481 $99K + K545 $47K (conservative) |
| Phase A full mid | **+$2,863,000/yr @$30M** | All 5 actions activated |
| D60 cascade (Jul 29) | **+$1,642,745/yr @$10M** | 14 scaffolds, 5 days |
| **Grand total mid** | **$4,505,745/yr** | Phase A + D60 on top |
| Active effort today | **~3.5 hours** | 5 actions, ZERO/LOW risk |

---

## Pre-Flight Checklist

Run `python3 wave_k709_day0_sheet.py --preflight` or manually verify:

```bash
# 1. HL wallet funded (for A2)
# Check: https://app.hyperliquid.xyz/ — account >= 100 USDC perps

# 2. Main wallet (MetaMask/hardware) accessible — NOT the API/agent key (for A2)

# 3. Bybit VIP/KYC (for A5)
# Bybit UI: Account & Security -> Sub Accounts menu visible

# 4. OKX API key (for A4 — deferrable)
python3 -c "import os; print('OKX_API_KEY:', 'SET' if os.environ.get('OKX_API_KEY') else 'NOT SET')"

# 5. LaunchAgents writable (for A1, A4)
ls ~/Library/LaunchAgents/ 2>&1 | head -3

# 6. Git clean (for A3 audit trail)
git status --short

# 7. Plist present (for A1)
ls com.cryptolab.loss-harvester.plist
```

### Required Environment Variables

| Var | Required For | Set Command |
|-----|-------------|-------------|
| `HL_BUILDER_CODE` | A2 K481 | `echo 'export HL_BUILDER_CODE="0x<ADDR>"' >> ~/.zshrc` |
| `OKX_API_KEY` / `OKX_API_SECRET` / `OKX_PASSPHRASE` | A4 K498 | `echo 'export OKX_API_KEY="..."' >> ~/.zshrc` |
| `BYBIT_SUB1_API_KEY` / `BYBIT_SUB1_SECRET` | A5 K485 | `echo 'export BYBIT_SUB1_API_KEY="..."' >> ~/.zshrc` |

---

## Phase A: Day 0 Actions (~3-4 hours)

### Execution Timeline

```
T+0:00 ── A1 K545 (5 min)  Tax Harvester plist           [ZERO risk]  +$47K/yr
T+0:05 ── A2 K481 (30 min) HL Builder Rebate              [ZERO risk]  +$99-248K/yr
T+0:35 ── A3 K552 (30 min) K280 75→60% patch [PREREQ]    [LOW risk]   +$260K unlock
T+1:05 ── MORNING BLOCK COMPLETE

T+0:00 ── A5 K485 (30 min) Bybit sub-account START       [LOW risk]   +$2.2M/yr @$25M
          → parallel to A1-A3, 7d gate runs in background

T+1:30 ── A4 K498 (8h)     OKX BBO_SELECT router         [LOW risk]   +$121K/yr @$30M
          → when OKX API key ready; deferrable to D1-D2
```

---

### A1: K545 Tax Harvester Plist (5 min, ZERO risk, +$47,300/yr @$10M Japan)

**Source:** K545 | **Pre-conditions:** tax jurisdiction confirmed with advisor

```bash
# Step 1: Set jurisdiction (adjust for your country)
python3 scripts/loss_harvester.py --set-rate 55 --set-jurisdiction JPN
# Korea: --set-rate 22 --set-jurisdiction KOR | Germany: --set-rate 26.375 --set-jurisdiction DE

# Step 2: Verify mock test
python3 scripts/loss_harvester.py --mock-test
# Expected: PASS: YES | Tax liability: $351,500.00

# Step 3: Deploy plist
cp com.cryptolab.loss-harvester.plist ~/Library/LaunchAgents/com.cryptolab.loss-harvester.plist

# Step 4: Load daemon (RunAtLoad=false — NO immediate run, annual Dec 28 trigger)
launchctl load ~/Library/LaunchAgents/com.cryptolab.loss-harvester.plist

# Step 5: Verify
launchctl list | grep loss-harvester
# Expected: com.cryptolab.loss-harvester listed (no PID — correct)
```

**Rollback:** `launchctl unload ~/Library/LaunchAgents/com.cryptolab.loss-harvester.plist && rm ~/Library/LaunchAgents/com.cryptolab.loss-harvester.plist`

| AUM | Japan (55%) | Korea (22%) |
|-----|-------------|-------------|
| $10M | **+$47,300/yr** | +$18,920/yr |
| $100M | +$473,000/yr | +$189,200/yr |

*INFORMATIONAL — consult licensed tax advisor before action.*

---

### A2: K481 HL Builder Rebate Registration (30 min, ZERO risk, +$99K–$248K/yr @$10M)

**Source:** K481 | **Pre-conditions:** HL >= 100 USDC perps; main wallet accessible; `HL_BUILDER_CODE` unset

```bash
# STEP 1: Register on HL UI (browser, ~20 min)
# https://app.hyperliquid.xyz/trade -> Account -> Builder
# Enter: your main wallet address | Fee: 0 | Sign: approveBuilderFee (MAIN wallet, not API key)
# Confirm: HL shows activation banner

# STEP 2: Set env var (replace 0x<ADDR> with your main wallet)
echo 'export HL_BUILDER_CODE="0x<YOUR_MAIN_WALLET>"' >> ~/.zshrc
source ~/.zshrc
echo $HL_BUILDER_CODE   # verify prints 0x address

# STEP 3: Apply 4-LOC patch to scripts/post_only_order_manager.py
# In submit_post_only_order(), AFTER the "if dry_run:" block, add:
#   _builder_code = os.environ.get("HL_BUILDER_CODE", "").strip()
#   if venue == "HL" and _builder_code and not dry_run:
#       order_action["builder"] = {"b": _builder_code, "f": 0}

# STEP 4: Verify dry-run (builder field should NOT appear — correct)
python3 scripts/post_only_order_manager.py --dry-run

# STEP 5: Restart live daemons
launchctl unload ~/Library/LaunchAgents/com.cryptolab.k246a-live.plist && launchctl load ~/Library/LaunchAgents/com.cryptolab.k246a-live.plist
launchctl unload ~/Library/LaunchAgents/com.cryptolab.k280-live.plist && launchctl load ~/Library/LaunchAgents/com.cryptolab.k280-live.plist

# STEP 6: Verify (24h later)
# https://app.hyperliquid.xyz/referrals -> builder rewards > $0
```

**Rollback:** Remove 4 LOC builder block; `unset HL_BUILDER_CODE` from ~/.zshrc; restart daemons.

| AUM | Conservative | Mid | Optimistic |
|-----|-------------|-----|-----------|
| $10M | **+$99,166/yr** | +$247,915/yr | +$495,830/yr |
| $50M | +$495,830/yr | +$1,239,574/yr | +$2,479,148/yr |

Daily monitoring target @$10M: $271/day. Alert if <$135/day for 3+ days.

---

### A3: K552 K280 75→60% Patch (30 min, LOW risk, +$260K unlock within 30d) [PREREQ]

**Source:** K552 | **Pre-conditions:** git clean; line 74 of leverage_manager.py shows 0.75; daemons not in active cycle  
**CRITICAL:** This is a prerequisite for K376 (+$247K/yr), K449 ($13K+), and D60 K629 WLD-ETH eligibility.

```bash
# PRE-FLIGHT: Backup 3 files
cp scripts/leverage_manager.py scripts/leverage_manager.py.bak
cp data/portfolio_aum_state.json data/portfolio_aum_state.json.bak
cp scripts/portfolio_aum_manager.py scripts/portfolio_aum_manager.py.bak

# STEP 1: PRIMARY patch (leverage_manager.py L74 — authoritative runtime)
sed -i '' 's/"K280":   0\.75,   # K280 main (K198 + K208 + K276b) — v6\.13d; v6\.16 reduces to 0\.72/"K280":   0.60,   # K280 main (K539 Phase B1: 75->60%, frees 7.5pp HL, 2026-05-30)/' scripts/leverage_manager.py

# Verify Step 1:
grep -n '"K280"' scripts/leverage_manager.py | head -5
# Expected: L74 shows 0.60

# STEP 2: JSON STATE patch
python3 -c "
import json
f = 'data/portfolio_aum_state.json'
d = json.load(open(f))
d['sleeve_weights']['K280'] = 0.60
d['last_updated_jst'] = '2026-05-30 K552/K709 Phase B1 patch'
json.dump(d, open(f, 'w'), indent=2)
print('Updated K280 to', d['sleeve_weights']['K280'])
"

# STEP 3: AUM manager fallback
sed -i '' 's/"K280":       0\.75,/"K280":       0.60,/' scripts/portfolio_aum_manager.py

# STEP 4: Verify ALL 3 files
grep -n '"K280".*0\.' scripts/leverage_manager.py data/portfolio_aum_state.json scripts/portfolio_aum_manager.py
# Expected: all 3 show 0.60

# STEP 5: Restart daemons
launchctl unload ~/Library/LaunchAgents/com.cryptolab.k280-live.plist && launchctl load ~/Library/LaunchAgents/com.cryptolab.k280-live.plist
launchctl unload ~/Library/LaunchAgents/com.cryptolab.k302a-satellite.plist && launchctl load ~/Library/LaunchAgents/com.cryptolab.k302a-satellite.plist

# STEP 6: Confirm daemons
launchctl list | grep cryptolab | grep -E 'k280|k302a'
# Expected: both show PIDs
```

**Rollback (< 2 min):**
```bash
cp scripts/leverage_manager.py.bak scripts/leverage_manager.py
cp data/portfolio_aum_state.json.bak data/portfolio_aum_state.json
cp scripts/portfolio_aum_manager.py.bak scripts/portfolio_aum_manager.py
launchctl unload ~/Library/LaunchAgents/com.cryptolab.k280-live.plist && launchctl load ~/Library/LaunchAgents/com.cryptolab.k280-live.plist
```

**Unlock cascade after A3:**
```
A3 applied (30 min)
  └── HL: 57.5% → ~50% (7.5pp freed)
      ├── K449 ETH-BTC: LIVE D+1  (+$13K+/yr)
      ├── K376 BULL_CONFIRMED: D+14  (+$247K/yr if triggered)
      └── D60 K629 WLD-ETH: eligible Jul29  (+$94K/yr conditional)
```

---

### A4: K498 Phase 1A OKX BBO_SELECT Smart Router (8h, LOW risk, +$121K/yr @$30M)

**Source:** K530/K498 | **Status:** K548 pre-conditions VERIFIED PASS  
**Pre-conditions:** OKX API key; `OKX_API_KEY`/`OKX_API_SECRET`/`OKX_PASSPHRASE` in ~/.zshrc; A3 applied first

```bash
# STEP 1: Verify OKX scaffold
launchctl list | grep okx
python3 scripts/okx_fr_fetcher.py --symbol BTC-USDT-SWAP

# STEP 2: Apply BBO_SELECT flag
sed -i '' 's/SMART_ROUTER_ENABLED = False   # K434.*/SMART_ROUTER_ENABLED = True    # K530 K498 Phase 1A: BBO routing ACTIVE/' scripts/k280_live_fetch.py
grep SMART_ROUTER_ENABLED scripts/k280_live_fetch.py  # verify

# STEP 3: Add to data/smart_router_config.json (after "default_post_only": true)
# "routing_mode": "BBO_SELECT",
# "bbo_select_min_score": -0.0001,

# STEP 4: Load OKX FR monitor daemon
cp com.cryptolab.okx-fr-monitor.plist ~/Library/LaunchAgents/
launchctl load ~/Library/LaunchAgents/com.cryptolab.okx-fr-monitor.plist
launchctl list | grep okx-fr-monitor

# STEP 5: 24h paper observation
python3 scripts/smart_router.py --all-symbols --side short --size 100000

# STEP 6: 48h gate check (target: Bybit+OKX >= 40%)
tail -20 data/smart_router_decisions.jsonl

# STEP 7: Live activation (after gate pass)
launchctl kickstart -k gui/$(id -u)/com.cryptolab.k280-live
```

**Rollback (< 5 min, 1 flag flip):**
```bash
sed -i '' 's/SMART_ROUTER_ENABLED = True.*/SMART_ROUTER_ENABLED = False   # K709 rollback/' scripts/k280_live_fetch.py
launchctl kickstart -k gui/$(id -u)/com.cryptolab.k280-live
```

| AUM | Annual | Daily |
|-----|--------|-------|
| $30M | **+$121,000/yr** | $331/day |
| $100M | +$1,030,000/yr | $2,822/day |

Alert: if non-HL routing < 20% for 7d, investigate.

---

### A5: K485 Bybit Sub-Account Phase 1A (30 min + 7d gate, LOW risk, +$2.2M/yr @$25M)

**Source:** K485 | **Pre-conditions:** Bybit KYC; Sub Accounts menu visible; server IP known  
**Note:** Start in parallel with A1-A3. No capital transfer until 7d gate passes.

```bash
# STEP 1: Create sub-account (Bybit UI, ~10 min)
# Login Bybit -> Profile -> Account & Security -> Sub Accounts
# -> Create Sub Account -> Standard Sub Account -> Label: k485-sub1-k297p

# STEP 2: Generate API key (Bybit UI, ~5 min)
# Sub Account -> API Management -> Create API
# Permissions: Trade only (NO withdrawal)
# IP restriction: add your Mac/server IP
# Save API Key + Secret to password manager immediately

# STEP 3: Set env vars (never commit to git)
echo 'export BYBIT_SUB1_API_KEY="<sub_api_key>"' >> ~/.zshrc
echo 'export BYBIT_SUB1_SECRET="<sub_secret>"' >> ~/.zshrc
source ~/.zshrc

# STEP 4: Verify
python3 -c "import os; print('BYBIT_SUB1_API_KEY:', 'SET' if os.environ.get('BYBIT_SUB1_API_KEY') else 'NOT SET')"

# STEP 5: 7-day paper-trade gate
python3 scripts/k280_live_fetch.py --venue=bybit --wallet=sub1 --dry-run
# Monitor 7 days: check fills, latency, API errors in dry-run logs

# STEP 6: After 7d gate (D+21) — capital transfer (Bybit internal, instant)
# Bybit UI: Assets -> Transfer -> From: Master -> To: k485-sub1-k297p
# Initial: $3-5M (no withdrawal key used — internal transfer only)
```

**Rollback:** No capital at risk until 7d gate. Sub-account deletable via Bybit UI. API key revocable.

| Total AUM | Architecture | Net/yr | vs Baseline |
|-----------|-------------|--------|-------------|
| $10M | Single HL (baseline) | $2.08M/yr | — |
| $25M | HL primary + Bybit sub | **$4.28M/yr** | +$2.20M (+106%) |
| $50M | HL + Bybit + dYdX (Phase 2) | $5.45M/yr | +$3.37M (+162%) |

---

## Risk Matrix

| Action | Risk | Rollback Time | Key Mitigation |
|--------|------|---------------|---------------|
| A1 K545 | **ZERO** | instant | RunAtLoad=false; annual cron; no trades |
| A2 K481 | **ZERO** | instant (remove 4 LOC) | f=0 no extra cost; additive field; env-var gated |
| A3 K552 | LOW | < 2 min | 3-file atomic backup; daemon restart documented |
| A4 K498 | LOW | < 5 min (1 flag flip) | 48h paper gate; concentration caps; rollback = 1 line |
| A5 K485 | LOW | instant (no capital) | No transfer until 7d gate; ToS-permitted; trade-only API |

---

## Phase B: D7–D14 — K376 BULL Activation Watch

**Trigger:** K497 daemon monitors slope > 0, Sharpe > 8 sustained 15d  
**Profit:** +$247K/yr max | $126K/yr regime-weighted  
**Auto-check:** K497 daemon already running — check status D+7 and D+14

```bash
# Check K376 regime status
python3 scripts/k376_regime_trigger_monitor.py --status

# If BULL_CONFIRMED:
launchctl load ~/Library/LaunchAgents/com.cryptolab.k376-momentum.plist
launchctl list | grep k376  # verify PID
```

Note: Regime-filter line CLOSED (K315-K341: 5 consecutive REJECT). K376 reopen condition: K280 Sharpe > 8 sustained 15d+. Monitor passively — K497 daemon alerts automatically.

---

## Phase C: D60 Cascade (2026-07-29 — Aug 2)

**D30 audit first:** 2026-06-29 (mandatory paper health check)  
**14 scaffolds | $1,642,745/yr unlock @$10M | $4,501/day post-cascade**  
**CONSTRAINT:** Max 3/day, Sharpe-descending order, 24h monitoring between batches  
**CRITICAL PREREQ:** A3 K552 patch MUST be applied BEFORE cascade for K629 WLD-ETH eligibility

| Day | Date | Strategies | Cumulative/yr | HL% |
|-----|------|-----------|---------------|-----|
| D+0 | 2026-07-29 | K686 AVAX-SOL (Sh=50.27), K682 ATOM-SOL (Sh=43.43), K628 JTO-orthog (Sh=44.63) | $673,817 | 63.5% |
| D+1 | 2026-07-30 | K679 APT-SOL (Sh=39.29), K658 SOL-ETH +1.5pp (Sh=29.66), K696 ENA-SOL (Sh=26.93) | $1,044,117 | **65.0% AT CAP** |
| D+2 | 2026-07-31 | K690 SEI-SOL (Sh=25.11), K648 POL-orthog (Sh=23.41), K647 DOT-orthog (Sh=23.25) | $1,315,215 | 65.0% |
| D+3 | 2026-08-01 | K663 TIA-ETH (Sh=22.0), K629 WLD-ETH COND (Sh=19.9, +2.0pp HL), K694 TIA-SOL (Sh=19.09) | $1,503,779 | 65.0% |
| D+4 | 2026-08-02 | K698 LINK-ETH (Sh=12.07), K684 SOL-INJ (Sh=9.65) | **$1,642,745** | 65.0% |

**K629 HARD STOP:** DO NOT load if HL >= 63.0%. Requires K552 headroom.

**Gate conditions per scaffold (all 14):**
- Realized Sharpe >= gate threshold (Sh >= 5 general, Sh >= 8 orthog, Sh >= 12 POL/DOT)
- Fill rate >= 60%
- Max drawdown < 20%
- PnL correlation vs nearest neighbor < 0.40

**Activation command template:**
```bash
python3 scripts/verify_deployment_status.py --check <strategy_wave>
launchctl load ~/Library/LaunchAgents/<plist_name>.plist
launchctl list | grep <daemon_name>  # verify PID non-zero
# Log rollback trigger:
# launchctl unload ~/Library/LaunchAgents/<plist_name>.plist
# echo "ROLLED BACK: <strategy> $(date)" >> data/rollback_log.txt
```

---

## Checkpoints

| Checkpoint | Date | Verify |
|------------|------|--------|
| D+7 | 2026-06-06 | K481 HL referral >$0; K545 daemon in launchctl; K552 all 3 files=0.60 |
| D+14 | 2026-06-13 | K498 routing Bybit+OKX >= 40%; K376 BULL check; K449 LIVE if applicable |
| D+21 | 2026-06-20 | K485 7d gate complete; capital transfer decision; sub-account active |
| D+30 | 2026-06-29 | D30 paper audit: all 14 scaffolds — Sharpe, fill rate, maxDD |
| D+60 | 2026-07-29 | D60 cascade execute: 14 scaffolds, Sharpe order, max 3/day |

---

## Constraints

1. **LIVE 自動変更禁止** — all changes are MANUAL EXECUTION ONLY
2. **K339 REPO_ROOT** — `/Users/nekonaomichi/crypto-lab`
3. **HL cap 65% hard ceiling** — K552 (A3) MUST precede any HL-adding strategy
4. **D60 cascade: max 3/day** — 24h monitoring between batches
5. **K629 CONDITIONAL** — DO NOT load if HL >= 63.0%
6. **API credentials** — NEVER commit to git; ~/.zshrc only

---

## Quick Reference Commands

```bash
# Full Day 0 sheet (colour terminal)
python3 wave_k709_day0_sheet.py

# Pre-flight checks
python3 wave_k709_day0_sheet.py --preflight

# Status check (all actions + daemons)
python3 wave_k709_day0_sheet.py --status

# Rollback instructions
python3 wave_k709_day0_sheet.py --rollback A3

# D60 cascade reference
cat wave_k705_d60_cascade.md | head -100

# K376 BULL regime check (Phase B)
python3 scripts/k376_regime_trigger_monitor.py --status
```

---

## Source References

| Wave | File | Topic |
|------|------|-------|
| K481 | `wave_k481_builder_rebate_activation.md` | HL builder rebate |
| K485 | `wave_k485_multi_account_scaling.md` | Bybit sub-account |
| K497 | `wave_k497_k376_regime_trigger.py` | K376 BULL auto-trigger |
| K498 | `wave_k498_smart_router_profit.md` | BBO_SELECT smart router |
| K539 | `wave_k539_immediate_actions.md` | D0–D60 sequencing |
| K545 | `wave_k545_tax_harvester_activation.md` | Tax harvester activation |
| K552 | `wave_k552_k280_patch.md` | K280 75→60% concrete patch |
| K561 | `wave_k561_phase_a_consolidated.md` | Phase A full consolidation |
| K674 | `wave_k674_executive_summary.md` | 225-wave session summary |
| K700 | `wave_k700_v650_mega.md` | v6.50 MEGA architecture |
| K702 | `wave_k702_defensive_verify.md` | Pre-execution defensive verify |
| K705 | `wave_k705_d60_cascade.md` | D60 cascade playbook |
| K706 | `wave_k706_production_audit.md` | Production audit |

---

*K709 Day 0 Unified Execution Sheet — 2026-05-30 16:20 JST*  
*K339 REPO_ROOT pattern | LIVE 自動変更禁止 | 1-page user-actionable*

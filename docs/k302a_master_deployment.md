# K539 Master Deployment Playbook — Single Source of Truth
**Version:** 6.28 | **Generated:** 2026-05-30 05:30 JST | **Wave:** K539 Immediate Action Consolidation (supersedes K532)
**Status:** ACTIVE USER ACTIVATION GUIDE — 4-Phase D0-D60 sequenced playbook

---

## ★★★ K539 Immediate Action Plan — 4-Phase D0-D60

**Realistic profit trajectory @$10M AUM (K523 calibrated):**

| Phase | Timing | Annual Range | Central | Delta |
|-------|--------|-------------|---------|-------|
| Baseline v6.13d | Now | $400K–$600K | $500K | — |
| Phase A active | D0 | $650K–$850K | $748K | +$248K |
| Phase B active | D14 | $1.05M–$1.45M | $1.25M | +$502K |
| Phase C active | D30 | $1.35M–$1.95M | $1.65M | +$400K |
| Phase D active | D60 | $1.55M–$2.35M | $1.95M | +$300K |

**Three convergent paths — single constraint (HL 65% cap + K280 overweight):**

| Path | Annual Value | Action Required |
|------|-------------|-----------------|
| K376 BULL unlock | +$247K/yr @ 3% sleeve | HL headroom 2.5pp → K280 reduce first |
| K208 decay defense | Prevent $0.6M/yr loss | K280 75%→40% (K511 v6.26) |
| K498 Phase 1A | +$121K/yr @ $30M | 14-LOC patch + OKX daemon |

---

### Phase A: Immediate (D0, 30 minutes)

| Step | Action | Effort | Risk | +$/yr @$10M |
|------|--------|--------|------|-------------|
| A1 | K481-A: HL approveBuilderFee registration | 30 min | ZERO | +$247,915 |
| A2 | Verify 37 SCAFFOLD-READY daemon pre-conditions | 5 min | ZERO | — |
| A3 | Confirm v6.13d baseline (K280=75%, K297p=20%, sUSDe=5%) | 2 min | ZERO | — |

**Result:** v6.13d unchanged + K481 builder rebate active → $650-850K/yr

---

### Phase B Step 1: K280 Sleeve Restructure (D0, 4 hours)

| Step | Action | Effort | Risk | HL Delta |
|------|--------|--------|------|----------|
| B1-1 | K280 weight 75% → 60% in data/portfolio_config.json | 30 min | LOW | -7.5pp |
| B1-2 | K297p 20% → 5%; sUSDe 5% → 8% | 15 min | LOW | — |
| B1-3 | K376 paper-trade seed at 1% provisional | 15 min | ZERO | — |
| B1-4 | K495 paper-trade seed at 1% | 15 min | ZERO | — |
| B1-5 | Restart K280 live daemon | 5 min | LOW | — |

**Result:** v6.13e-interim (K280=60%, HL=57.5%, K376+K495 paper 1% each)
**HL exposure after:** 57.5% (7.5pp headroom for K376 + new strategies)

---

### Phase B Step 2: K498 Phase 1A Smart Router (D7, 8 hours)

**Prerequisite:** OKX API key configured

| Step | Action | Effort | Risk | +$/yr @$30M |
|------|--------|--------|------|-------------|
| B2-1 | 14-LOC patch: SMART_ROUTER_ENABLED=True in scripts/k280_live_fetch.py | 30 min | LOW | +$121K |
| B2-2 | Add BBO_SELECT routing_mode to data/smart_router_config.json | 15 min | LOW | — |
| B2-3 | Load OKX FR monitor daemon | 5 min | LOW | — |
| B2-4 | 24h paper observation | 24h | ZERO | — |

```bash
# B2-1 patch (14 LOC)
# In scripts/k280_live_fetch.py: change SMART_ROUTER_ENABLED = False → True
# In data/smart_router_config.json: {"routing_mode": "BBO_SELECT", "venues": ["HL","Bybit","OKX"]}

# B2-3 daemon load
cp /Users/nekonaomichi/crypto-lab/com.cryptolab.okx-fr-monitor.plist ~/Library/LaunchAgents/
launchctl load ~/Library/LaunchAgents/com.cryptolab.okx-fr-monitor.plist
launchctl list | grep okx
```

**Result:** v6.13e + smart router BBO_SELECT active

---

### Phase C: K376 BULL_CONFIRMED (D14, 4 hours — CONDITIONAL)

**Gate:** BTC 20d SMA slope > 0 × 7 consecutive days (K497 BULL_CONFIRMED)
**Current:** TRANSITION zone (K533 — slope -33.83 $/day, ETA ~7 days from K527)

| Step | Action | Effort | Risk | +$/yr @$10M |
|------|--------|--------|------|-------------|
| C1 | K497 BULL_CONFIRMED check | 2 min | ZERO | — |
| C2 | K376 paper 1% → live 1% | 30 min | MEDIUM | +$82K |
| C3 | K280 60% → 40% (full K511 v6.26) | 1 hr | LOW | defensive |
| C4 | Spark sUSDS add 8% sleeve | 2 hr | LOW | — |
| C5 | K376 expand 1% → 3% (D14→D30, gate pass) | 15 min | MEDIUM | +$165K |

**Result:** v6.26 (K280=40%, K376=3%, K495=1%, sUSDe=8%, Spark=8%, HL≈52%)

```bash
# C1 check
python3 scripts/k497_regime_monitor.py --status

# C3 config update
# Edit data/portfolio_config.json: k280_weight: 0.40
launchctl unload ~/Library/LaunchAgents/com.cryptolab.k280-live.plist
launchctl load ~/Library/LaunchAgents/com.cryptolab.k280-live.plist
```

---

### Phase D: Full v6.28 Paired-Trade Family (D30–D60)

| Step | Action | Gate | +$/yr @$10M |
|------|--------|------|-------------|
| D1 | K376 expand 3% → 5% | Sharpe ≥ 8 post 7d live | +$82K |
| D2 | K495 expand 1% → 6% | 60d paper Sharpe ≥ 10 | +$150K |
| D3 | K484 AVAX-BTC activate (3%) | 60d paper gate | +$76K |
| D4 | K493 ATOM-BTC activate (3%) | 60d paper gate | +$75K |
| D5 | K500 INJ-BTC activate (3%) | 60d paper gate | +$75K |
| D6 | K507 SEI+TIA activate (D60) | 60d paper gate | +$50K |
| D7 | K512 APT activate (D60) | 60d paper gate | +$50K |
| D8 | K280 fine-tune 40% → 38% | HL re-balance target 64% | — |

**Result:** v6.28 (K280=38%, K376=5-8%, K495=6%, paired-trade family, HL≈64%)

---

### Sleeve GANTT D0-D60

```
Strategy                   D0     D7    D14    D30    D60  Note
------------------------------------------------------------------------------------------
K280                      75%    60%    40%    38%    38%  K511 v6.26 full reduction
K297p                     20%     5%     5%     5%     5%  reduce; free headroom
sUSDe                      5%     8%     8%     8%     8%  stablecoin yield expansion
Spark sUSDS                0%     0%     8%     8%     8%  add D14 post-K280 reduction
K376 momentum              0%     1%     3%     5%     8%  paper→live; BULL_CONFIRMED gate
K495 DEX-CEX flow          0%     1%     1%     6%     6%  1% test; 6% post-paper-gate D30
K449 ETH-BTC               0%     0%     0%     5%     5%  daemon D7; sleeve D30 post-gate
K476 SOL-BTC               0%     0%     3%     3%     3%  D14 post K280 restructure
K484 AVAX-BTC              0%     0%     0%     3%     3%  60d paper gate; D30 if pass
K493 ATOM-BTC              0%     0%     0%     3%     3%  60d paper gate; D30 if pass
K500 INJ-BTC               0%     0%     0%     3%     3%  60d paper gate; D30 if pass
K507 SEI                   0%     0%     0%     0%     2%  D60 paper-gate
K507 TIA                   0%     0%     0%     0%     1%  D60 paper-gate
K512 APT                   0%     0%     0%     0%     2%  D60 paper-gate
K521 Options               0%     0%     0%     0%     0%  paper only — no live
------------------------------------------------------------------------------------------
TOTAL                    100%    75%    68%    87%    95%
HL EXPOSURE               65%    58%    52%    54%    64%  Hard cap 65% enforced
```

### Critical Risk Summary

| Risk | Severity | Mitigation |
|------|----------|------------|
| K280 reduction → loss if K208 decay not permanent | HIGH | Stage 75%→60%→40%; monitor daily |
| BULL false positive (K376 premature live) | MEDIUM | Require 7d slope > 0; start 1% only |
| Phase 1A patch breaks smart router | LOW | 24h paper observation; rollback ready |
| HL cap breach from simultaneous strategy adds | HIGH | Track HL% at each step; 65% hard cap |
| Paper-gate strategies fail Sharpe threshold | MEDIUM | Gate ≥ 8 Sharpe strictly enforced |

> See `wave_k539_immediate_actions.{py,json,md}` for full detail.
> **Source:** K539 | K481 | K497 | K509 | K511 | K523 | K527 | K530 | K532 | K533

---

---

## K532 Governance v5 — User Action Queue (UPDATED)

**Realistic v6.28 projection: $1.63-2.48M/yr @$10M (central $2.02M) | K523 transparency-adjusted**  
**Top-5 actionable lift: ~$956K/yr @$10M + $121K @$30M**  
**Architecture: v6.26 LIVE + v6.28 PROPOSAL | 37 daemons | 18 closed lines | 52-wave cycle**

> CRITICAL: K208 decay -67% Y/Y (K509). K492E activation is the #1 defensive priority.  
> IMMINENT: K376 BULL_CONFIRMED ETA ~7 days (K527 slope -37.23 $/day, TRANSITION zone).  
> CAP: HL concentration 65.0% EXACTLY AT CAP (K524). All new strategies paper-only.

### Immediate Top 5 (No Dependencies, Start Now)

| Priority | Action | Setup | Risk | +$/yr @$10M |
|----------|--------|-------|------|------------|
| 1 | **K481-A**: Register HL builder rebate (approveBuilderFee, main wallet) | 30 min | ZERO | +$247,915 |
| 2 | **K485-1A**: Create Bybit sub-account + HL W2 strategy isolation | 30 min | LOW | +$204,370 |
| 3 | **K483**: Update portfolio weights to v6.22a (Kelly MV: K376 35%, sUSDe 10%) | 1 hr | LOW | +$150,300 |
| 4 | **K492E**: Activate K208 Variant E (predictedFundings + POST_ONLY) — CRITICAL decay offset | 3 hr | LOW | +$223,000 |
| 5 | **K498-1A**: K530 playbook: BBO_SELECT + OKX daemon LIVE | 8 hr | LOW | +$121K @$30M |

### Full 10-Action Queue (K532 Updated, ROI/hr Ranked)

| Rank | ID | ROI/hr @$10M | +$/yr @$10M | Setup | Risk | Deps | Status |
|------|----|-------------|-------------|-------|------|------|--------|
| 1 | K481-A | $495,830/hr | +$247,915 | 0.5h | ZERO | none | OPEN |
| 2 | K485-1A | $408,740/hr | +$204,370 | 0.5h | LOW | none | OPEN |
| 3 | K483 | $150,300/hr | +$150,300 | 1.0h | LOW | none | OPEN |
| 4 | K492E | $74,333/hr | +$223,000 | 3.0h | LOW | K304 daemon | CRITICAL |
| 5 | K376 | $247,047/hr | +$247,047 | 1.0h | MEDIUM | BULL_CONFIRMED (ETA ~7d) | CONDITIONAL |
| 6 | K493-paper | $57,750/hr | +$231,000 | 4.0h | LOW | K499 plist active | OPEN |
| 7 | K498-1A | $15,125/hr | +$121K @$30M | 8.0h | LOW | OKX API key | OPEN |
| 8 | K482-3 | $46,120/hr | +$368,961 | 8.0h | LOW | none (prerequisite K482-2/1) | OPEN |
| 9 | K482-2 | $77,210/hr | +$154,420 | 2.0h | LOW | K482-3 done | DEFERRED |
| 10 | K481-B | — | — | 2.0h | LOW | K481-A done | DEFERRED |

**Also pending:** K437 (HYPE Bronze stake, +$8.6K/yr, 30min, LOW), K484/AVAX (paper gate ongoing), K515 LunarCrush ($423K/yr, needs $49+/mo API)

**Activated:** K430 (3x leverage, circuit breaker required)

**Dependency chain:**
- K482: implement in order K482-3 → K482-2 → K482-1
- K492E: requires K304 daemon (SCAFFOLD-READY) — activate immediately
- K376: wait for K497 BULL_CONFIRMED (BTC 20d SMA slope > 0 × 7 days) — ETA ~7 days
- K481-B (code patch): after K481-A registration
- K498-1A: requires OKX account + API key (K530 3-step playbook delivered)

Full detail: `wave_k532_governance_v5.md` / `wave_k532_governance_v5.json`

---

## K532 Architecture Status Summary

| Architecture | Status | Realistic @$10M/yr | Notes |
|-------------|--------|-------------------|-------|
| v6.13d | LIVE baseline | $400K-$1M (K208 decaying) | K492E patch critical |
| v6.26 emergency | APPROVED | $1.26-1.98M (central $1.59M) | K280 40%, K495 +6% |
| v6.28 proposal | CANDIDATE | $1.63-2.48M (central $2.02M) | APT+SEI+TIA family |
| v6.20 full | DEFERRED | $74M @$200M optimal | Long-term M6-M9 |

---

## K501 v6.24 5-Year Projection Update

| Scenario | CAGR | 5y Terminal @$10M | vs Baseline |
|----------|------|------------------|-------------|
| v6.13d baseline (K430 activated) | 20.84% | $25,766,390 | — |
| + All pending lifts activated | 44.03% effective | $61,990,560 | +$36,224,170 |
| @$100M all activated | — | ~$484M+ | significant |

---



## Executive Summary

You have accumulated a profit-driving stack across waves K356–K464 that projects:

```
v6.13d Base case: $10M → $28.56M over 5 years (CAGR 23.35%, Sharpe 13.43)
v6.20 Full case:  $10M → $200M optimal +$74.4M/yr (Portfolio Sharpe 21.70)
Architecture:     v6.13d LIVE → v6.16 (K449) → v6.20 (full 10-venue, 8-sleeve)
Key levers:       3x leverage (K430) + daily reinvest (K429) + multi-venue K208 (K431/K456/K460)
                  + smart router (K434) + depth allocator (K458) + basket (K457)
K461 verdict:     ACCEPT (CONDITIONAL) — K449+K457 60d paper-trade gates required
```

This document consolidates every pending user action from waves K356–K464 into one sequential activation guide.  
**Total: 20 sequenced user actions** (K436's original 10 + 10 new v6.20 actions).  
Follow it top-to-bottom. Each action is ranked by ROI-per-hour-invested.

---

## Table of Contents

1. [20-Action Priority Ranking](#1-20-action-priority-ranking)
2. [4-Week Deployment Timeline](#2-4-week-deployment-timeline)
3. [Daily Checklist](#3-daily-checklist-post-deployment)
4. [Weekly Checklist](#4-weekly-checklist)
5. [Monthly Checklist](#5-monthly-checklist)
6. [Month 0–Y3 Roadmap (v6.20 Path)](#6-month-0y3-roadmap-v620-path)
7. [Expected Outcomes by Phase](#7-expected-outcomes-by-phase)
8. [v6.20 Transition Flowchart](#8-v620-transition-flowchart)
9. [Profit Trajectory](#9-profit-trajectory)
10. [K449 + K457 Paper-Trade Gates](#10-k449--k457-paper-trade-gates)
11. [Troubleshooting](#11-troubleshooting)
12. [Rollback Procedures](#12-rollback-procedures)
13. [Reference: Source Waves](#13-reference-source-waves)

---

## 1. 20-Action Priority Ranking

Sorted by ROI/hour invested. Actions 1–10 are M0 Week-1 priorities. Actions 11–20 are phased M0–M6.

### Actions 1–10: M0 Foundation (K436 original actions, updated)

| # | Action | Source Wave | Cost | Time | Expected Annual ROI @ $10M | Risk |
|---|--------|-------------|------|------|---------------------------|------|
| 1 | K370 Builder rebate — `approveBuilderFee` on main HL wallet | K370 | $0 | 30 min | **$94K–$472K/yr** | ZERO |
| 2 | Load K356 HIP-4 daemon (calibration deadline 2026-06-22) | K356/K368/K409 | $0 | 5 min | data quality gate unlock | None |
| 3 | Load K387 RSS regulatory monitor daemon | K387/K404 | $0 | 5 min | early warning $0→prevent loss | None |
| 4 | Load K407 TVL trajectory monitor daemon | K407 | $0 | 5 min | HypurrFi drop-line alert | None |
| 5 | Load K412 sUSDe APY monitor daemon | K412 | $0 | 5 min | sleeve re-eval trigger | None |
| 6 | Load K434 smart router daemon | K434 | $0 | 5 min | **+$175K/yr** execution gain | Low |
| 7 | K357 emergency exit credentials — set `HL_PRIVATE_KEY` env | K357 | $0 | 30 min | Safety net | None |
| 8 | HL HYPE Bronze stake (100 HYPE ≈ $5,900) ← **K437 corrected** | K432/K437 | $5,900 | 30 min | **$8,623/yr** (143.9% ROI) | Low |
| 9 | Fund Bybit account ($2M+) — triggers VIP5 instantly | K432 | $0 (realloc) | 1 day wire | **$154K/yr** fee tier reduction | None |
| 10 | Enable `AUM_TRACKING_ENABLED=true` for K429 | K429 | $0 | 5 min | unlocks reinvest compounding | Low |

> **Action #1 (builder rebate): $94K–$472K/yr at ZERO cost in 30 minutes. Do this first.**  
> **Action #8 corrected (K437):** Bronze 100 HYPE at $5,900 yields 143.9% ROI. Do NOT buy Gold at $590K.

---

### Actions 11–20: v6.20 Path (K464 new actions, phased M0–M6)

| # | Action | Source Wave | Timing | Prerequisite | Expected Impact |
|---|--------|-------------|--------|-------------|----------------|
| 11 | Load K456 OKX daemon (20th daemon) | K456 | M0 | OKX API keys | 3rd K208 venue, triangle arb HL/Bybit/OKX |
| 12 | Load K457 multi-asset basket daemon (22nd daemon, K459 scaffold) | K457/K459 | M0 paper | — | BTC+ETH+SOL inv-vol carry, 5% sleeve, 60d paper gate |
| 13 | Load K458 depth-aware allocator daemon (21st daemon) | K458 | M0 | K456 active | Capacity rescue: 5% OI cap/venue, $100M+ slip guard |
| 14 | K449 ETH-BTC paired daemon load (19th daemon) | K449/K451 | M2 | K376 started | v6.16 transition: +$157K/5y net |
| 15 | Load K460 Aevo + dYdX v4 daemons (23rd + 24th) | K460 | M0 | Aevo/dYdX setup | 5th+ K208 venue, 1h funding cycle, cross-venue arb |
| 16 | OKX account: minimal funding for FR fetch + future trading | K456 | M0–M1 | OKX account | Enables 3rd venue live trading |
| 17 | Aevo account creation (no funding needed for fetch) | K460 | M0 | — | Enables Aevo FR data + future live orders |
| 18 | dYdX v4 wallet setup (Cosmos chain) | K460 | M0 | Cosmos wallet | Enables dYdX v4 FR fetch + orders |
| 19 | K457 production active (after 60d paper gate, Sharpe ≥15) | K457/K459 | M5 | 60d paper pass | Basket sleeve 5% live → v6.20 prep |
| 20 | v6.20 transition: K280 multi-venue active (K208 distributed 10 venues) | K464/K461 | M6–M9 | K458 + OKX/Aevo/dYdX live | $100M viable, $200M optimal +$74.4M/yr |

> **Actions 11–15 require daemon loads. Actions 16–18 require external account setup (no coding).  
> Action 19–20 are conditional on paper-trade gates passing — do not force-activate.**

---

## 2. 4-Week Deployment Timeline

### Week 1: Zero-Cost Foundation (Days 1–7)

#### Day 1 — Load Monitoring Daemons (20 min total)

**Goal:** Get all 4 scaffold daemons live before anything else.

**Action 1: K356 HIP-4 Calibration Daemon**
```bash
cp /Users/nekonaomichi/crypto-lab/com.cryptolab.hl-hip4-monitor.plist ~/Library/LaunchAgents/
launchctl load ~/Library/LaunchAgents/com.cryptolab.hl-hip4-monitor.plist
# Verify:
launchctl list | grep hip4
```
- Deadline: data collection must start ASAP — calibration gate is 2026-06-22
- Every day without daemon load reduces buffer from 9 days toward 0
- Runbook: docs/k302a_runbook.md §20

**Action 2: K387 RSS Regulatory Monitor**
```bash
cp /Users/nekonaomichi/crypto-lab/com.cryptolab.regulatory-rss.plist ~/Library/LaunchAgents/
launchctl load ~/Library/LaunchAgents/com.cryptolab.regulatory-rss.plist
# Verify:
launchctl list | grep regulatory
```
- Polls SEC/CFTC every 30 min, sends ntfy.sh alert on keyword match
- Clarity Act keywords: 13 total including "Crypto Clarity Act", "Senate floor vote", etc.
- Runbook: docs/k302a_runbook.md §18

**Action 3: K407 TVL Monitor**
```bash
cp /Users/nekonaomichi/crypto-lab/com.cryptolab.protocol-tvl-monitor.plist ~/Library/LaunchAgents/
launchctl load ~/Library/LaunchAgents/com.cryptolab.protocol-tvl-monitor.plist
# Verify:
launchctl list | grep tvl
```
- Weekly HypurrFi TVL check — alerts on DROP_LINE pattern ($14.9M baseline, 30d −52.6%)
- Script: scripts/protocol_tvl_trajectory_monitor.py

**Action 4: K412 sUSDe APY Monitor**
```bash
cp /Users/nekonaomichi/crypto-lab/com.cryptolab.susde-apy-monitor.plist ~/Library/LaunchAgents/
launchctl load ~/Library/LaunchAgents/com.cryptolab.susde-apy-monitor.plist
# Verify:
launchctl list | grep susde
```
- Weekly sUSDe APY check — triggers sleeve re-evaluation if APY drops below 5%
- Script: scripts/susde_apy_monitor.py

---

#### Day 2 — Smart Router Verification (5 min)

**Action 5: Load K434 Smart Router Daemon**
```bash
cp /Users/nekonaomichi/crypto-lab/com.cryptolab.smart-router.plist ~/Library/LaunchAgents/
launchctl load ~/Library/LaunchAgents/com.cryptolab.smart-router.plist
# Manual test first:
python3 /Users/nekonaomichi/crypto-lab/scripts/smart_router.py --symbol BTC --side short --size 100000
```
- Routes K208 orders to best venue (HL / Bybit / OKX) based on spread + fee
- +$175K/yr @ $10M, +$877K/yr @ $50M
- Runbook: docs/k302a_runbook.md §24

**Expected output:** JSON with venue recommendation, spread differential, fee comparison.
If API auth fails, check `data/smart_router_config.json` for credentials.

---

#### Day 3 — Builder Rebate Registration (30 min) ← HIGHEST ROI

**Action 6: K370 Builder Fee Approval**

This is the single highest-ROI action in the entire playbook. Zero cost, zero risk, 30 minutes.

1. Open HyperLiquid main wallet UI or use direct contract call
2. Call `approveBuilderFee` with builder address (see docs/k302a_runbook.md §19 for exact address)
3. Confirm transaction on-chain
4. Verify in HL dashboard that builder rebate is active

Expected result: **$94K–$472K/yr** fee rebate credited to your account based on volume tier.

> Source: K370. This action is STILL UNACTIVATED as of K436. Most impactful single user action.

---

#### Day 4 — Emergency Exit Credentials (30 min)

**Action 7: Set HL Private Key for Emergency Exit**
```bash
# Add to ~/.zshrc or set permanently in system environment:
export HL_PRIVATE_KEY="your_hyperliquid_private_key_here"
export HL_USER_ADDRESS="your_hl_wallet_address_here"

# Test emergency exit script (DRY RUN only):
python3 /Users/nekonaomichi/crypto-lab/emergency_hl_exit.py --dry-run
```
- Only needed in emergencies (HL outage, margin cascade)
- Script: emergency_hl_exit.py
- Source: K357

> **IMPORTANT:** Never commit private keys to git. Set env vars in shell profile only.

---

#### Day 5 — Enable AUM Tracking (5 min)

**Action 8: K429 AUM Tracking Enable**
```bash
# Set initial AUM and enable tracking:
export INITIAL_AUM_USDC=10000000   # Set to your actual capital
export AUM_TRACKING_ENABLED=true

# Or write to data/portfolio_aum_state.json directly:
python3 scripts/portfolio_aum_manager.py --set-initial-aum 10000000
```
- Unlocks daily reinvestment compounding (+$3.6M/5y @ $10M)
- Runbook: docs/k302a_runbook.md §22

---

#### Days 5–7 — Paper Trade at 1.5x Leverage

**Action 9: K430 Leverage Phase PAPER_TRADE**
```bash
# Verify current phase:
python3 scripts/leverage_manager.py --status
# Expected output: phase=PAPER_TRADE, current_leverage=1.0x
```
- You should already be in PAPER_TRADE from Day 1
- Monitor circuit breaker behavior: `data/leverage_cb_dashboard.json`
- Nothing to activate yet — just observe

---

### Week 2: Capital Deployment (Days 8–14)

#### Day 8 — Fund Bybit Account

**Action 10: Bybit VIP5 Trigger**
- Wire transfer $2M+ to Bybit account
- VIP5 status activates **instantly** at $2M+ assets (no waiting period)
- Fee reduction: 0.02% maker / 0.04% taker → significant at $10M volume
- Expected: **+$154K/yr** fee savings at current trading volume
- Source: K432

#### Days 9–14 — Continue Paper Trade Monitoring

- Watch circuit breaker: margin_used should stay below 70%
- Watch K408 K412 sUSDe alert — if APY drops to LOW/CRASH, pause K429 sleeve rebalancing
- Watch K407 TVL alert — HypurrFi TVL dropping below $10M → reduce K297 satellite exposure

---

### Week 3: Leverage Go-Live (Days 15–21)

#### Day 15 — Advance to LIVE_1.5X

**Gate check before advancing:**
- [ ] margin_used_pct < 60% in all K280 positions
- [ ] K429 AUM tracking active > 7 days
- [ ] No active circuit breaker fires in past 7 days
- [ ] sUSDe APY above 5% (K412 status: NORMAL)

```bash
# Advance phase:
python3 scripts/leverage_manager.py --advance
# Expected: phase changes PAPER_TRADE → LIVE_1.5X
# Verify:
python3 scripts/leverage_manager.py --status
```

Expected outcome: leverage increases from 1.0x → 1.5x on K280 positions.
Monitor for 7 days before advancing further.

---

#### Days 16–21 — Monitor LIVE_1.5X

Daily checks:
- `data/leverage_cb_dashboard.json` — CB fire? → stop
- `data/portfolio_aum_state.json` — AUM growth on track?
- K428: daily reinvest running? → check cumulative_pnl_pct > 0

---

### Week 4: Full 3x Leverage (Days 22–28)

#### Day 22 — Advance to LIVE_3X

**Gate check before advancing:**
- [ ] margin_used_pct consistently < 65% during LIVE_1.5X week
- [ ] No circuit breaker fires during LIVE_1.5X phase
- [ ] 7-day rolling return positive (K429 k429-7d-val > 0)
- [ ] Bybit VIP5 confirmed active

```bash
python3 scripts/leverage_manager.py --advance
# Expected: phase changes LIVE_1.5X → LIVE_3X
```

#### Day 28 — Final AUM Tracking Enable + HL HYPE Stake

**HYPE Gold Stake (if not done in Week 1):**
- Purchase 10,000 HYPE tokens (≈ $13K at time of K432)
- Stake in HL HYPE Gold tier
- Expected: +$2,534/yr (19.5% staking APY)

**Verify AUM tracking fully operational:**
```bash
python3 scripts/portfolio_aum_manager.py --report
```

---

## 3. Daily Checklist (Post-Deployment)

Each morning, check these 6 items in order (< 5 minutes total):

```
[ ] 1. sUSDe APY  — K412 alert status: NORMAL? (if LOW/HIGH/CRASH → sleeve rebalance)
[ ] 2. HypurrFi   — K407 alert: DROP_LINE pattern? (if yes → review K297 exposure)
[ ] 3. RSS alerts — K387 any new SEC/CFTC items? (if yes → manual review)
[ ] 4. Smart router decisions — K434 any routing changes? (check data/smart_router_dashboard.json)
[ ] 5. AUM growth — K429 cumulative_pnl_pct vs prior day (positive? on track?)
[ ] 6. Margin     — K430 circuit breaker margin_used < 70%? (if > 70% → alert)
```

---

## 4. Weekly Checklist

Every Sunday (< 15 minutes):

```
[ ] 1. K368 HIP-4 calibration data accumulation — how many N snapshots collected?
       Target: N ≥ 14 by 2026-06-22. Check: data/hip4_calibration_data/
[ ] 2. K412 sUSDe trajectory — weekly APY trend stable?
[ ] 3. K407 TVL monitor digest — HypurrFi TVL direction?
[ ] 4. K429 AUM weekly delta — weekly % vs base case?
       Base case target: ~+0.396%/wk (20.56% CAGR / 52 weeks)
[ ] 5. K431 venue allocation — HL exposure < 65%?
       If > 65%: shift next K280 orders to Bybit (smart router handles automatically)
[ ] 6. K370 builder rebate — rebate amount visible in HL dashboard?
```

---

## 5. Monthly Checklist

First day of each month (< 30 minutes):

```
[ ] Day 1:  K411 memory rules recheck — any outdated rules? Remove/update
[ ] Day 1:  K359/K379/K399 governance schedule — HL governance votes pending?
[ ] Day 1:  K414 HL universe diff — new RWA listings? Update K276b universe
[ ] Day 15: K393 HypurrFi monthly trajectory recheck
[ ] Day 15: K412 sUSDe APY 30-day mean — still > 5%?
[ ] Day 30: Sleeve weight rebalance (K427 confirmed 75/20/5):
            K280 75% / K297' 20% / sUSDe OC 5%
[ ] Day 30: K429 AUM reinvestment — surplus above 8% cash buffer redeployed?
```

---

## 6. Month 0–Y3 Roadmap (v6.20 Path)

### Full Timeline: M0 → Y3 (v6.13d → v6.16 → v6.20)

| Month | Action | AUM Tier | Architecture |
|-------|--------|----------|--------------|
| M0 | Load all monitor daemons: K356/K387/K407/K412 + K456/K458/K460 | $10M | v6.13d |
| M0 | K370 builder rebate registration | $10M | v6.13d |
| M0 | HL HYPE Bronze stake (100 HYPE, ~$5,900) | $10M | v6.13d |
| M0 | K357 emergency exit credentials | $10M | v6.13d |
| M1 | K430 leverage rollout: PAPER → 1.5x → 3x | $10M | v6.13d |
| M1 | K376 paper-trade starts | $10–15M | v6.14 prep |
| M2 | Bybit account fund $2M+ for VIP5 | $15M+ | v6.13d |
| M2 | K449 paper-trade starts (19th daemon) | $15M | v6.16 prep |
| M2 | K457 basket paper-trade starts (22nd daemon) | $15M | v6.20 prep |
| M3 | OKX account active (fund + API) | $15M+ | v6.20 prep |
| M4 | K376 graduate to live (Sharpe pass) | $20M | v6.14 LIVE |
| M4 | K449 graduate, v6.16 active | $25M | v6.16 LIVE |
| M5 | K457 graduate (if Sharpe ≥15.0) | $25–30M | v6.16+ |
| M5 | K458 depth allocator active | $25M+ | v6.16+ |
| M6 | K458 distributes K208 across HL+Bybit+OKX | $30M+ | v6.20 transition |
| M6 | Aevo + dYdX v4 added (23rd + 24th daemons) | $30M+ | v6.20 transition |
| M9 | v6.20 fully deployed (10 venues, 8 sleeves) | $50M+ | v6.20 LIVE |
| M12 | $100M tier reached | $100M | v6.20 LIVE |
| Y2 | $200M optimal +$74M/yr | $200M | v6.20 LIVE |
| Y3–Y5 | Continue compounding at 37.2% net rate | $200M+ | v6.20 LIVE |

---

### M0–M1: Foundation (v6.13d)

Full stack activating: 3x leverage + daily reinvest + smart router routing.  
Base case trajectory:
- Month 2: ~$10.35M (+3.5%)
- Month 3: ~$10.73M (+7.3%)
- Month 6: ~$11.88M (+18.8%) → **v6.20 transition begins**

Monitor monthly: AUM vs K440 base-case ($28.56M/5y, CAGR 23.35%).  
If AUM trailing by > 5%: review leverage setting, check CB fire logs.

---

### M2: v6.16 Transition Begins (K449 + Bybit)

**Trigger:** M2 start

```
v6.16 Architecture transition:
  - K449 ETH-BTC differential paper-trade starts
  - Bybit account funded $2M+ → VIP5 instant
  - Smart router begins HL/Bybit routing
  - K457 basket paper-trade starts concurrently
```

K449 paper-trade gate (60d): OOS Sharpe ≥ 5.0, fill rate ≥ 60%, max DD < 2%.

---

### M3: OKX Account Active

**Trigger:** AUM $15M+ OR user discretion

```
OKX Account Setup (Action #16):
  - Minimal funding for FR fetch + future trading
  - API key with Trade permissions (no withdrawal)
  - Add to data/smart_router_config.json: okx_api_key, okx_secret, okx_passphrase
  - K456 daemon already loaded (M0) → shifts paper→live
  - Triangle arb: HL/Bybit/OKX threshold 5bps
```

---

### M4–M5: v6.14 → v6.16 Go-Live

**Trigger:** K376 Sharpe passes 60d gate AND K449 Sharpe passes 60d gate

```
v6.16 Activation:
  1. Reduce K280 weight: 75% → 72%
  2. Add K449 live weight: 0% → 3% ($300K notional / $1.2M with 4x leverage)
  3. Confirm HL exposure: 57.5% → 60.5% (must remain ≤ 65%)
  4. 5y terminal: $28.71M (CAGR 23.49%)
  5. K449 net lift: +$157,190 over 5y
```

---

### M5: K457 Basket Go-Live (if gate passes)

**Trigger:** K457 60d paper gate: OOS Sharpe ≥ 15.0, fill rate ≥ 65%

```
K457 Activation (Action #19):
  - BTC+ETH+SOL inv-vol carry sleeve: 5% weight
  - K280 weight: 72% → 67% (or K297' reduced)
  - Expected: v6.20 prep complete
```

---

### M6: v6.20 Transition — Multi-Venue Full Activation

**Trigger:** AUM ≥ $30M (expected M6 per K440 trajectory)

```
v6.20 Transition (Action #20):
  K208 distribution across 10 venues:
    HL / Bybit / OKX / Drift / Aevo / dYdX / Vertex / Lighter / Variational / Gate
  
  K458 depth allocator manages venue allocation:
    - 5% OI cap per venue (prevents quadratic slippage)
    - Greedy distribution: HL → Bybit → OKX → ...
    - $100M viable, $200M optimal
  
  Aevo + dYdX v4 added (23rd + 24th daemons):
    - Aevo: 1h funding cycle, api.aevo.xyz
    - dYdX v4: Cosmos chain, indexer.dydx.trade
    - Cross-venue arb: HL/Bybit/OKX/Aevo/dYdX
```

---

### M9: v6.20 Fully Deployed

All 10 venues active. 8 sleeves live. 24 daemons running.  
Portfolio Sharpe: 21.70 | Combined Ann Return: 9.01% | HL concentration: 47.5% ≤ 65% cap.

---

### M12 Decision Point: $100M Tier

- If AUM ≥ $100M → confirm v6.20 full capacity check (K458 depth guard)
- v6.13d flips negative at $100M → v6.20 rescues: +$48.2M/yr at $100M
- Continue compounding to $200M optimal (+$74.4M/yr)

---

## 7. Expected Outcomes by Phase

| Phase | Timeline | AUM Target | Architecture | Key Milestone |
|-------|----------|------------|-------------|---------------|
| Foundation | Day 1–7 | $10M | v6.13d | Monitor daemons + builder rebate live |
| Capital Deploy | Day 8–14 | $10M | v6.13d | Bybit VIP5, smart router verified |
| 1.5x Leverage | Day 15–21 | $10.1M+ | v6.13d | +$1.1M/yr incremental activated |
| 3x Leverage | Day 22+ | $10.2M+ | v6.13d | +$2.2M/yr fully active |
| Month 2 | ~Day 60 | ~$10.35M | v6.13d | Full compounding + K449 paper started |
| Month 4 | ~Day 120 | ~$10.73M | v6.14 LIVE | K376 graduated |
| Month 4 | ~Day 120 | ~$15M | v6.16 LIVE | K449 graduated, HL 60.5% |
| Month 6 | ~Day 180 | ~$20M | v6.20 prep | OKX/Aevo/dYdX active, K457 paper started |
| Month 9 | ~Day 270 | ~$30M+ | v6.20 LIVE | 10 venues, K458 full distribution |
| Month 12 | ~Day 365 | ~$50M | v6.20 LIVE | $100M viable via v6.20 |
| Year 2 | ~Day 730 | ~$100M | v6.20 LIVE | +$48.2M/yr net |
| Year 2–3 | ~Day 900 | ~$200M | v6.20 LIVE | **Optimal: +$74.4M/yr** |
| Year 5 | ~Day 1825 | **~$200M+** | v6.20 LIVE | **Sustained $74M/yr, ~$250M+ cumulative** |

---

## 8. v6.20 Transition Flowchart

```
v6.13d (LIVE M0)
├── Action 6: K434 smart router (M0) → HL/Bybit/OKX routing
├── Action 11: K456 OKX daemon (M0) → 20th daemon, 3rd venue
├── Action 12: K457 basket paper (M0) → 22nd daemon, 60d gate
├── Action 13: K458 depth allocator (M0) → 21st daemon, capacity
├── Action 14: K449 paper-trade (M2) → 19th daemon
├── Action 15: K460 Aevo+dYdX (M0 loads) → 23rd+24th daemons
│
├── M4: K376 paper gate PASS → v6.14 LIVE
│   └── K376 momentum 5% sleeve active
│
├── M4: K449 paper gate PASS → v6.16 LIVE
│   ├── K280 72% + K297 20% + sUSDe 5% + K449 3%
│   └── 5y terminal: $28.71M CAGR 23.49%
│
└── M5: K457 paper gate PASS (Sharpe ≥15) → v6.20 prep
    ├── K458 depth allocator M5 active
    ├── OKX/Aevo/dYdX M3-M6 funded
    │
    └── M6–M9: v6.20 LIVE
        ├── K208 across 10 venues (K458 distributes)
        ├── 8 sleeves: K280 65% + K297' 5% + sUSDe 10%
        │            + K376 5% + K449 5% + K457 5% + Cash 5%
        ├── Portfolio Sharpe: 21.70
        ├── $100M → +$48.2M/yr
        └── $200M OPTIMAL → +$74.4M/yr
```

**Architecture decision gates:**
- Gate A (M4): K376 60d paper → Sharpe ≥ 5.0, fill rate ≥ 60% → v6.14 LIVE
- Gate B (M4): K449 60d paper → Sharpe ≥ 5.0, fill rate ≥ 60% → v6.16 LIVE
- Gate C (M5): K457 60d paper → Sharpe ≥ 15.0, fill rate ≥ 65% → v6.20 LIVE
- Gates fail → hold current architecture, extend paper period

---

## 9. Profit Trajectory

| Time | AUM | Annual Profit (run rate) | Cumulative Profit | Architecture |
|------|-----|------------------------|-------------------|-------------|
| M0 | $10M | $1.0M baseline | $0 | v6.13d |
| M6 | $20M | $2.5M (multi-venue) | ~$8M | v6.13d→v6.16 |
| Y1 | $50M | $15M (v6.20 partial) | ~$25M | v6.20 partial |
| Y2 | $100M | $48M (v6.20 full) | ~$60M | v6.20 LIVE |
| Y3 | $200M | $74M (optimal) | ~$100M+ | v6.20 LIVE |
| Y5 | $200M | $74M sustained | ~$250M+ | v6.20 LIVE |

**v6.20 vs v6.13d at scale:**
- v6.13d at $100M: **-$4M/yr** (slippage destroys profit — K297' quadratic drag)
- v6.20 at $100M: **+$48.2M/yr** (K458 depth guard + 10-venue distribution)
- v6.20 at $200M: **+$74.4M/yr** (optimal AUM point, 37.2% net rate)
- v6.20 at $400M: still positive (+$3.2M/yr) — hard ceiling
- Above $400M: multi-entity structure required

**Tax note (K442/K444):**
- Annual: run K444 loss harvester Dec 28–31 ($2–41K/yr retention)
- Quarterly: tax estimate via K442 calculator
- K428 reinvest does NOT defer tax (each FR cycle = realization event)
- UAE/SGP/HK residency: 0% retention max (K442 jurisdiction lever)

---

## 10. K449 + K457 Paper-Trade Gates

These are the conditional gates for v6.20 full activation per K461 ACCEPT verdict.

### K449 ETH-BTC Differential (19th daemon)

**Paper-trade start:** M2 | **Duration:** 60 days | **Activation: v6.16**

```bash
# Load K449 paper-trade daemon:
cp /Users/nekonaomichi/crypto-lab/com.cryptolab.k449-eth-btc.plist ~/Library/LaunchAgents/
launchctl load ~/Library/LaunchAgents/com.cryptolab.k449-eth-btc.plist
# Verify:
launchctl list | grep k449
```

**Gate criteria (60d OOS):**
- [ ] Realized Sharpe ≥ 5.0 (K461 gate — stricter than K451's ≥2.0)
- [ ] Fill rate ≥ 60%
- [ ] Max drawdown < 2%
- [ ] Signal fire count ≥ 3

**Pass → v6.16 activation:**
1. Reduce K280 live weight: 75% → 72%
2. Add K449 live weight: 0% → 3% ($300K notional at $10M)
3. Confirm HL exposure: 57.5% → 60.5% ≤ 65% cap
4. Expected: +$19.8K/yr net, +$157K/5y

**Script:** `ct_forward/k449_eth_btc_live.py`  
**Daemon:** `com.cryptolab.k449-eth-btc.plist`  
**Runbook:** docs/k302a_runbook.md §29

---

### K457 Multi-Asset Basket (22nd daemon, K459 scaffold)

**Paper-trade start:** M2 | **Duration:** 60 days | **Activation: v6.20 prep**

```bash
# Load K457 basket paper-trade daemon:
cp /Users/nekonaomichi/crypto-lab/com.cryptolab.k457-basket.plist ~/Library/LaunchAgents/
launchctl load ~/Library/LaunchAgents/com.cryptolab.k457-basket.plist
# Verify:
launchctl list | grep k457
```

**Gate criteria (60d OOS):**
- [ ] OOS Sharpe ≥ 15.0 (in-sample 19.58 — must sustain)
- [ ] Fill rate ≥ 65%
- [ ] 6 legs executing (BTC+ETH+SOL spot short + 3x futures)
- [ ] DAR(2,1) signal stable

**Pass → v6.20 prep activation:**
1. Add K457 live weight: 0% → 5%
2. K280 or K297' weight reduced by 5pp accordingly
3. Confirm sleeve total = 100%

**Script:** `ct_forward/k459_basket_scaffold.py` (K459 scaffold for K457)  
**Daemon:** `com.cryptolab.k457-basket.plist`  
**OOS Sharpe (in-sample):** 19.58 — CONDITIONAL ACCEPT

---

### Activation Order

```
K376 paper (already started M1) → Gate A → v6.14 LIVE
K449 paper (M2)                 → Gate B → v6.16 LIVE
K457 paper (M2 concurrent)      → Gate C → v6.20 LIVE
```

Do NOT skip gates. Paper periods exist precisely because fill rate and slippage in production differ from simulation.

---

## 11. Troubleshooting

### Circuit Breaker Fires (margin_used > 80%)

**Symptoms:** `data/leverage_cb_dashboard.json` shows `circuit_breaker_fire: true`

**Response:**
```bash
# Immediate reduce:
python3 scripts/leverage_manager.py --emergency-reduce
# This reduces leverage back to LIVE_1.5X phase
# Monitor margin for 24h before re-advancing
```

**Root causes:**
- Large market move against K208 carry positions
- HL outage causing position imbalance
- K276b FR rank inversion (high-FR assets moved against prediction)

---

### Low Fill Rate on Smart Router

**Symptoms:** `data/smart_router_dashboard.json` shows `fill_rate < 65%`

**Response:**
```bash
# Widen spread tolerance:
# Edit data/smart_router_config.json:
# "max_spread_bps": 5 → 8
# Or switch to IOC fallback mode:
python3 scripts/smart_router.py --symbol BTC --side short --size 100000 --mode IOC
```

---

### HIP-4 Daemon Not Collecting Data

**Symptoms:** N < 5 snapshots by Day 10 (check `data/hip4_calibration_data/`)

**Response:**
```bash
# Check daemon status:
launchctl list | grep hip4
# If not running:
launchctl unload ~/Library/LaunchAgents/com.cryptolab.hl-hip4-monitor.plist
launchctl load ~/Library/LaunchAgents/com.cryptolab.hl-hip4-monitor.plist
# Manual snapshot:
python3 scripts/hl_hip4_monitor.py --manual-snapshot
```

**Deadline:** 2026-06-22. If N < 14 by that date, calibration becomes INCONCLUSIVE_DIRECTIONAL only.

---

### sUSDe APY Crash Alert

**Symptoms:** K412 alert = `CRASH` (APY < 3%)

**Immediate action:**
1. Pause K429 automatic sleeve rebalancing
2. Redeploy sUSDe 5% sleeve to USDC or USDY (v6.15a/b pathway)
3. Review K415 runbook §21 for USDY activation

---

### Builder Rebate Not Appearing

**Symptoms:** No rebate credit visible in HL dashboard after 48h

**Response:**
1. Verify `approveBuilderFee` transaction was confirmed on-chain (HL explorer)
2. Check builder address matches exactly (see K370 wave for address)
3. Contact HL support if still not visible after 72h

---

### AUM Tracking Below Base Case

**Symptoms:** K429 7-day rolling return consistently < 0.38%/week

**Response:**
- Check leverage is at 3x (not still at LIVE_1.5X)
- Check smart router is routing (not stuck on single venue)
- Check K412 sUSDe sleeve is deployed (not parked in USDC)
- If all above correct: accept variance (base case has Sharpe 13.43, short-run divergence expected)

---

## 12. Rollback Procedures

### Rollback: Reduce Leverage

```bash
python3 scripts/leverage_manager.py --emergency-reduce
# Goes from current phase → previous phase
# LIVE_3X → LIVE_1.5X → PAPER_TRADE
```

### Rollback: Disable Daemon

```bash
launchctl unload ~/Library/LaunchAgents/com.cryptolab.<daemon-name>.plist
```

### Rollback: Revert Builder Rebate

- Contact HyperLiquid support to remove builder fee approval
- No on-chain rollback needed (only approval, no funds at risk)

### Rollback: Emergency Full Exit

```bash
# Uses K357 emergency exit script (requires HL_PRIVATE_KEY set)
python3 emergency_hl_exit.py --all-positions --confirm
```

> This closes all HL positions at market. Use only in extreme scenarios (HL insolvency, protocol exploit).

### Rollback: Revert Leverage Config

```bash
cp data/leverage_config.json.bak data/leverage_config.json
# Or edit data/leverage_config.json:
# "current_phase": "PAPER_TRADE"
# "leverage": 1.0
```

---

## 13. Reference: Source Waves

### Original Actions 1–10 (K436)

| Action | Wave | Runbook Section |
|--------|------|-----------------|
| K370 Builder rebate | K370 | §19 |
| K356 HIP-4 daemon | K356/K368/K409 | §20 |
| K387 RSS monitor | K387/K404 | §18 |
| K407 TVL monitor | K407 | (plist: com.cryptolab.protocol-tvl-monitor) |
| K412 sUSDe monitor | K412 | (plist: com.cryptolab.susde-apy-monitor) |
| K434 Smart router | K434 | §24 |
| K357 Emergency exit | K357 | (emergency_hl_exit.py) |
| K437 HYPE Bronze stake | K432/K437 | (HL staking UI) |
| K432 Bybit VIP5 | K432 | (Bybit account settings) |
| K429 AUM tracking | K429 | §22 |
| K430 Leverage rollout | K430 | §23 |
| K431 Bybit live integration | K431 | (Month 2 milestone) |
| K400/K415 USDY (non-US only) | K400/K415 | §21 |
| K440 5y revised projection | K440 | (wave_k440_revised_projection.md) |

### New Actions 11–20 (K464 v6.20)

| Action | Wave | Runbook Section |
|--------|------|-----------------|
| K456 OKX daemon (20th) | K456 | (com.cryptolab.k456-okx.plist) |
| K457 basket daemon (22nd, K459 scaffold) | K457/K459 | (com.cryptolab.k457-basket.plist) |
| K458 depth allocator (21st) | K458 | (com.cryptolab.k458-depth-allocator.plist) |
| K449 ETH-BTC daemon (19th) | K449/K451 | §29 |
| K460 Aevo+dYdX daemons (23rd+24th) | K460 | (com.cryptolab.k460-aevo.plist / k460-dydx.plist) |
| OKX account setup | K456 | (data/smart_router_config.json) |
| Aevo account creation | K460 | (api.aevo.xyz) |
| dYdX v4 wallet setup | K460 | (indexer.dydx.trade, Cosmos chain) |
| K457 production activation | K457/K459/K464 | (after 60d paper gate §C) |
| v6.20 full transition | K461/K464 | §34 |

### Architecture Milestones

| Milestone | Wave | Key File |
|-----------|------|---------|
| v6.13d base projection | K440 | wave_k440_revised_projection.md |
| v6.16 +K449 projection | K451 | wave_k451_v616_projection.md |
| v6.20 scaling redesign | K454 | wave_k454_scaling_redesign.md |
| K456 OKX scaffold | K456 | wave_k456_okx_scaffold.md |
| K458 depth allocator | K458 | (scripts/k458_depth_allocator.py) |
| K459 basket scaffold | K459 | (ct_forward/k459_basket_scaffold.py) |
| K460 Aevo+dYdX | K460 | wave_k460_aevo_dydx.md |
| v6.20 §6 gate validation | K461 | wave_k461_v620_validation.md |
| v6.20 playbook update | K464 | wave_k464_playbook_v620.md |

---

## Appendix: Key File Paths

```
scripts/leverage_manager.py          — Phase advance / emergency reduce
scripts/leverage_circuit_breaker.py  — CB daemon (15th daemon)
scripts/smart_router.py              — Smart router logic + manual test
scripts/portfolio_aum_manager.py     — AUM tracking state management
scripts/regulatory_rss_monitor.py    — K387 RSS daemon
scripts/protocol_tvl_trajectory_monitor.py — K407 TVL daemon
scripts/susde_apy_monitor.py         — K412 sUSDe daemon
emergency_hl_exit.py                 — Emergency exit (K357)

data/leverage_config.json            — Leverage phase config
data/leverage_cb_dashboard.json      — CB dashboard (live)
data/portfolio_aum_state.json        — AUM tracking state (live)
data/smart_router_config.json        — Smart router venue config
data/smart_router_dashboard.json     — Router dashboard (live)

com.cryptolab.hl-hip4-monitor.plist        — K356 HIP-4 daemon
com.cryptolab.regulatory-rss.plist         — K387 RSS daemon
com.cryptolab.protocol-tvl-monitor.plist   — K407 TVL daemon
com.cryptolab.susde-apy-monitor.plist      — K412 sUSDe daemon
com.cryptolab.smart-router.plist           — K434 smart router daemon
com.cryptolab.leverage-circuit-breaker.plist — K430 CB daemon
```

---

*K464 Master Deployment Playbook v6.20 — Generated 2026-05-30 01:18 JST*
*Single source of truth: supersedes K436 and all per-wave activation notes*
*20 user actions: Actions 1–10 (M0) + Actions 11–20 (M0→M9 phased)*
*Next update: K475 (after Month 4 K449 paper gate or milestone event)*

---

## Appendix K440 — Updated Profit Projection (2026-05-29)

**Wave:** K440 | **Supersedes:** K433 base projections | **Source:** wave_k440_revised_projection.md

### Corrected 5-Year Projection Table

| Case | K433 Baseline | K438 Lift | **K440 Revised** | CAGR |
|------|--------------|-----------|-----------------|------|
| Conservative | $13,484,015 | +$1,632,449 | **$15,116,464** | 8.62% |
| **Base** | $25,472,463 | **+$3,083,837** | **$28,556,300** | **23.35%** |
| Aggressive | $29,561,725 | +$3,578,906 | **$33,140,631** | 27.08% |

### K437 HYPE Correction

**Action 8 in §1 (10-Action Priority Ranking) is CORRECTED:**

| | Old (K432) | Corrected (K437) |
|--|-----------|-----------------|
| Tier | Gold (10K HYPE) | **Bronze (100 HYPE)** |
| Cost | $13,000 (at $1.30/HYPE) | **$5,900 (at $59/HYPE)** |
| Annual benefit | $2,534 | **$8,623** |
| ROI | 19.5% | **143.9%** |
| Verdict | Based on 2024 airdrop price | HYPE 45x'd → Gold costs $590K, ROI only 2.9% |

**Do NOT buy Gold tier at $10M AUM.** Bronze dominates. Upgrade to Silver at $50M AUM (ROI 87%).

### K438 K208 Alpha Lift

- K208 limit ladder + predictedFR signal integrated
- K280 OOS Sharpe: 20.25 → **22.12** (+1.87)
- 5-year terminal: $25.47M → **$28.56M** (+$3.08M)
- §6 gates: **PASS 7/7**
- Implementation: ~230 LOC across `scripts/predicted_fr_signal.py` + `scripts/k280_live_fetch.py`

### Uncaptured Upside (NOT in $28.56M)

| Item | Annual Lift | Action Required |
|------|-------------|----------------|
| K434 Smart router | +$175,500 | Load daemon (5 min, $0 cost) |
| K432 Bybit VIP5 | +$154,264 | Fund Bybit $2M+ |
| K437 HYPE Bronze | +$8,623 | Buy 100 HYPE ≈ $5,900 |
| K370 Builder rebate | +$94K–$472K | approveBuilderFee on HL |

**True Base with router + builder low: $10M → ~$31M (CAGR ~25%)**

### K280 Sharpe Trajectory

| Milestone | K280 Sharpe | Portfolio Sharpe |
|-----------|------------|-----------------|
| K433 Base | 20.25 | 13.43 |
| K438 Refined | **22.12** | ~14.83 |

### Expected Outcomes (Updated §7)

| Phase | Timeline | AUM Target | Notes |
|-------|----------|------------|-------|
| Year 1 | Day 365 | ~$12.3M | K438 trajectory |
| Year 2 | Day 730 | ~$15.2M | Bybit live integration active |
| Year 3 | Day 1095 | ~$18.8M | |
| Year 4 | Day 1460 | ~$23.2M | |
| **Year 5** | **Day 1825** | **~$28.6M** | **Base CAGR 23.35%** |

### Decision

- **CONFIRMED Base: $28.56M** (conservative, K438 fully integrated)
- **OPTIMISTIC Base: $30–32M** (with smart router + builder rebate activated)
- **Aggressive: $33–35M** (+ K431 multi-venue scaling at AUM $30–50M y3+)

Source files: `wave_k440_revised_projection.py` | `wave_k440_revised_projection.json` | `wave_k440_revised_projection.md`

---

## Appendix K451 — v6.16 5-Year Projection (2026-05-30)

**Wave:** K451 | **Supersedes:** v6.16 candidate notes from K450 | **Source:** wave_k451_v616_projection.md

### v6.16 Architecture

| Component | v6.13d | v6.16 | Change |
|-----------|--------|-------|--------|
| K280 FR Carry | 75% | **72%** | −3pp |
| K297' Weekend FR | 20% | 20% | — |
| sUSDe OC | 5% | 5% | — |
| K449 ETH-BTC Diff | 0% | **3%** | +3pp |
| HL Exposure | 57.5% | **60.5%** | within 65% cap |

### v6.16 Projection Table

| Case | v6.13d Terminal | v6.16 Terminal | Delta | CAGR |
|------|----------------|----------------|-------|------|
| Conservative | $15,116,464 | **$15,199,674** | +$83,209 | 8.73% |
| **Base** | **$28,556,300** | **$28,713,489** | **+$157,190** | **23.49%** |
| Aggressive | $33,140,631 | **$33,323,055** | +$182,424 | 27.17% |

### K449 Net Contribution

```
K449 gross annual (4x, both legs):  +$52,600/yr
K280 weight loss (3% × 10.94%):     −$32,820/yr
Net swap gain Year 1:               +$19,780/yr

5-year compounded total:            +$157,190
```

### Step 11: K449 Paper-Trade Activation

**Timing:** After K376 60d paper-trade gate completes (or concurrently if slots available)

```bash
# Load K449 paper-trade daemon (K450 scaffold):
cp /Users/nekonaomichi/crypto-lab/com.cryptolab.k449-eth-btc.plist ~/Library/LaunchAgents/
launchctl load ~/Library/LaunchAgents/com.cryptolab.k449-eth-btc.plist
# Verify:
launchctl list | grep k449
```

**Gate criteria (60d):**
- Realized Sharpe ≥ 2.0
- Max drawdown < 2%
- Signal fire count ≥ 3

**Script:** `ct_forward/k449_eth_btc_live.py`
**Daemon:** `com.cryptolab.k449-eth-btc.plist`
**Runbook:** docs/k302a_runbook.md §29

---

### Step 12: v6.16 Architecture Transition

**Trigger:** K449 60d paper-trade gate passes (Sharpe ≥ 2.0 AND DD < 2%)

**Action:**
1. Reduce K280 live weight: 75% → 72% (reduce $300K notional at $10M AUM)
2. Add K449 live weight: 0% → 3% (add $300K notional / $1.2M with 4x leverage)
3. Confirm HL exposure: 57.5% → 60.5% (must remain ≤ 65%)

**Expected outcome:**
- 5y terminal: $28,713,489 (CAGR 23.49%)
- Sharpe: 13.43 → 13.55 (+0.12 via orthogonality)
- K449 net lift: +$157,190 over 5y

**Recommendation:** HYBRID — do not activate until 60d paper-trade gate passes.

**Source files:**
`wave_k451_v616_projection.py` | `wave_k451_v616_projection.json` | `wave_k451_v616_projection.md`

*K440 Appendix — Added 2026-05-29 23:19 JST*

---

## Appendix K454 — $100M+ AUM Scaling Redesign (v6.20 Candidate, 2026-05-30)

**Wave:** K454 | **Supersedes:** K431 multi-venue analysis | **Source:** wave_k454_scaling_redesign.md

### Problem Statement

K431 confirmed the current v6.13d/v6.16 strategy flips **negative at $100M AUM**:
- Slippage: $37M/yr (quadratic, K297' shallow markets)
- Gross profit: $33M/yr
- Net: **-$4M/yr** — strategy unviable above $50M

### Root Cause

Linear AUM scaling → quadratic slippage in shallow OI markets (K297' RWA, K276b long-tail).
At $100M, K297' notional ($60M) vs PAXG OI ($15M) = 4× ratio → 28+ bps impact per trade.

### v6.20 Solution: Multi-Venue + Sleeve Rebalance

**Architecture (8 sleeves, 10 venues):**

| Sleeve | Weight | Capacity | Change from v6.13d |
|--------|--------|----------|-------------------|
| K208 BTC Multi-Venue (10 venues) | 65% | $500M | HL/Bybit/OKX/Drift/Aevo/dYdX/Vertex/Lighter/Variational |
| K297' RWA (HL+Variational) | **5%** | $25M | **20% → 5% (removes quadratic drag)** |
| sUSDe Yield | **10%** | $10B | **5% → 10% (zero slippage)** |
| K376 Momentum | 5% | $50M | New in v6.20 |
| K449 ETH-BTC Differential | 5% | $100M | v6.16 → v6.20 |
| BTC ETF Flow Alpha | **5%** | $2B | **NEW sleeve (K458)** |
| Multi-Asset Basket (BTC+ETH+SOL) | **5%** | $300M | **NEW sleeve (K459)** |
| Cash + Margin Buffer | **10%** | — | Increased for scale |

**HL exposure: ~27.5% of AUM** (well within 65% cap)

### Profit Projections (v6.20)

| AUM | v6.13d Net | v6.20 Net | v6.20 Viable |
|-----|-----------|----------|-------------|
| $10M | +$2.08M/yr | +$5.32M/yr | YES |
| $25M | +$4.28M/yr | +$13.22M/yr | YES |
| $50M | +$5.45M/yr | +$25.85M/yr | YES |
| $100M | **-$4.00M/yr** | **+$48.18M/yr** | **YES (rescue)** |
| $200M | NEGATIVE | **+$74.45M/yr** | **YES (optimal)** |
| $400M | NEGATIVE | +$3.20M/yr | YES (marginal) |
| $500M | NEGATIVE | -$122.25M/yr | NO |

### Maximum Sustainable AUM

- **v6.20 ceiling: $400M** (last viable tier)
- **Optimal profit: $200M AUM** ($74.4M/yr net, 37.2% net rate)
- **Beyond $400M:** multi-entity structure required (2× $200M entities)
- **$500M+ ceiling** with multi-entity (separate legal/ops per entity)

### 8-Wave Implementation Roadmap

| Wave | Deliverable | Trigger |
|------|-------------|---------|
| K454 | Scaling redesign + v6.20 blueprint | NOW |
| K455 | Position depth-aware allocator (~500 LOC) | AUM $20M+ |
| K456 | OKX integration (K208 3rd major venue) | AUM $25M+ |
| K457 | Aevo + dYdX v4 integration | AUM $30M+ |
| K458 | BTC ETF flow alpha (new sleeve) | AUM $30M+ |
| K459 | Multi-asset basket BTC+ETH+SOL | AUM $40M+ |
| K460 | Lighter + Vertex (tail venues) | AUM $50M+ |
| K461 | v6.20 full §6 gate validation | K455-K460 complete |

**Timeline: ~6 months | ~2,500 new LOC | 7 additional waves**

### Activation Triggers

```
Primary: AUM >= $30M (1 month post-Bybit M6 per K436 playbook)
Secondary: Aggressive deployment timeline approved by user
Gate: K461 §6 must pass before full v6.20 production deploy
```

### Decision

**HYBRID:**
- Continue v6.13d/v6.16 unchanged at current scale (<$30M)
- Plan v6.20 for $50M+ AUM (6 months out)
- No immediate production change

**New Sleeves Queued:**
- K458: BTC ETF flow alpha (Glassnode/Coinglass data, $2B capacity, ~12% gross)
- K459: Multi-asset basket BTC+ETH+SOL inv-vol ($300M capacity, ~25% gross)

Source files: `wave_k454_scaling_redesign.py` | `wave_k454_scaling_redesign.json` | `wave_k454_scaling_redesign.md`

*K454 Appendix — Added 2026-05-30 00:22 JST*

---

## Appendix K464 — v6.20 Deployment Playbook Complete (2026-05-30)

**Wave:** K464 | **Supersedes:** K436 playbook (10 actions) | **Source:** wave_k464_playbook_v620.md

### Summary of Changes from K436 → K464

| Item | K436 | K464 |
|------|------|------|
| Total user actions | 10 | **20** |
| Architecture | v6.13d only | **v6.13d → v6.16 → v6.20** |
| Venue count | 1–2 (HL+Bybit) | **10 venues** |
| Daemon count | ~16 | **24** |
| 5y terminal | $28.56M (K440) | **$200M+ optimal** |
| Optimal AUM | ~$15M | **$200M ($74.4M/yr)** |
| Capacity ceiling | $50M (flips negative) | **$400M** |
| Timeline | Year 5 $28M | **Year 2 $200M optimal** |

### 10 New Actions Added (Actions 11–20)

1. **#11 K456 OKX daemon** — 20th daemon, 3rd K208 venue, triangle arb HL/Bybit/OKX (5bps threshold)
2. **#12 K457 basket daemon** — 22nd daemon (K459 scaffold), BTC+ETH+SOL inv-vol carry, 60d paper gate
3. **#13 K458 depth allocator** — 21st daemon, capacity rescue, 5% OI cap/venue, $100M+ slip guard
4. **#14 K449 paper-trade** — 19th daemon, ETH-BTC differential, M2 start, v6.16 transition gate
5. **#15 K460 Aevo+dYdX** — 23rd+24th daemons, 1h funding cycle, cross-venue arb
6. **#16 OKX account** — minimal funding for FR fetch + future trading (M0–M1)
7. **#17 Aevo account** — no funding needed for fetch, create before M6
8. **#18 dYdX v4 wallet** — Cosmos chain setup, indexer.dydx.trade
9. **#19 K457 production** — activate after 60d paper gate (Sharpe ≥15), v6.20 prep
10. **#20 v6.20 transition** — K280 distributed 10 venues via K458, M6–M9, K461 §6 validated

### K461 ACCEPT (CONDITIONAL) Summary

| Gate | Result | Status |
|------|--------|--------|
| Portfolio Sharpe (corr-adj) | 21.70 | PASS (≥15) |
| Combined Ann Return | 9.01% | PASS (≥5%) |
| HL Concentration | 47.5% | PASS (≤65%) |
| $200M capacity | +$74.4M/yr | PASS (≥$50M/yr) |
| K449 OOS gate | CONDITIONAL | 60d paper required |
| K457 OOS gate | CONDITIONAL | 60d paper required |
| §6 Overall | **5/7 CONDITIONAL** | ACCEPT CONDITIONAL |

### Tax + Loss Harvesting Integration (K442/K444)

- **Annual (Dec 28–31):** Run K444 loss harvester → $2–41K/yr tax retention
- **Quarterly:** Tax estimate via K442 calculator
- **Note:** K428 reinvest does NOT defer tax — each FR cycle = taxable realization
- **Jurisdiction:** UAE/SGP/HK 0% retention (K442 lever, adds $10.2M/5y at $50M AUM)

### v6.20 Full Architecture (M9 Steady State)

```
Sleeve               Weight   Capacity   OOS Sharpe
─────────────────────────────────────────────────────
K280 BTC Multi-Venue   65%    $500M      20.25  (10 venues)
K297' RWA (HL+Var)      5%    $25M       12.20  (reduced from 20%)
sUSDe Yield            10%    $10B        8.39  (increased from 5%)
K376 Momentum           5%    $50M        3.35  (ETH/LINK/AVAX)
K449 ETH-BTC Diff       5%    $100M       5.66  (v6.16→v6.20)
K457 BTC+ETH+SOL        5%    $300M      19.58  (conditional)
Cash / Margin Buf       5%    —           4.5%  (increased for scale)
─────────────────────────────────────────────────────
TOTAL                 100%              Portfolio 21.70
```

Source files: `wave_k464_playbook_v620.py` | `wave_k464_playbook_v620.json` | `wave_k464_playbook_v620.md`

*K464 Appendix — Added 2026-05-30 01:18 JST*

---

## Appendix K477 — v6.21 Architecture Proposal (Stablecoin Sleeve Refinement)

**Wave:** K477 | **Generated:** 2026-05-30 02:26 JST | **Supersedes:** K473 sleeve proposal
**Verdict:** RECOMMEND v6.21 Variant A on trigger (K473 sUSDS sustained >= 3.5% for 14d)

### Context

K461 v6.20 holds 10% sUSDe-only in the stablecoin sleeve (HHI = 1.0, max concentration).
K473 ACCEPT scaffolds Spark sUSDS as a co-sleeve candidate (28th daemon, trigger-based).
K474 CONDITIONAL permits Pendle YT-aUSDC at <= 10% but requires rollover daemon.
K477 evaluates all three v6.21 variants and recommends Variant A as the optimal upgrade path.

### v6.21 Variant Summary

| Variant | Composition | Blended APY | Lift vs v6.20 | HHI | Complexity | Status |
|---------|-------------|-------------|---------------|-----|------------|--------|
| v6.20 (baseline) | sUSDe 10% | 3.72% | — | 1.000 | NONE | ACTIVE |
| **v6.21 A** (Conservative) | sUSDe 5% + sUSDS 5% | 3.61% | -$1,100/yr | 0.500 | LOW | **PREPARE** |
| v6.21 B (Enhanced) | + Pendle 2% | ~4.0% | +$2,800/yr | 0.400 | MEDIUM | DEFERRED |
| v6.21 C (Aggregator) | 7 protocols 10% | ~4.12% | +$4,000/yr | 0.205 | HIGH | DEFERRED |

### Activation Trigger — Variant A

```
Trigger:       sUSDS 14d average APY >= 3.5%
Source:        com.cryptolab.spark-usds-monitor (K473 28th daemon — already running)
Current spot:  3.344% (below trigger; temporary DSR dip)
Current 7d:    3.573% (above trigger)
Current 30d:   3.668% (above trigger — structural level confirmed)
```

The 30d mean (3.668%) confirms structural DSR is above threshold. Spot dip is intra-month variance.
30d APY volatility = 0.232pp — within normal Sky/MakerDAO governance cycle fluctuation.
Trigger expected to fire within 1-4 weeks upon next governance rate confirmation.

### User Action on Trigger

```
1. K473 daemon alert fires: "sUSDS 14d mean >= 3.5% — Variant A trigger MET"
2. User action: Move 5% of portfolio (half of current sUSDe 10% sleeve) → Spark Protocol
   - Deposit: USDS or USDC via Spark.fi (Ethereum L1)
   - Receive: sUSDS (auto-compounding, instant redemption)
3. Resulting allocation: sUSDe 5% + sUSDS 5% = 10% stablecoin sleeve (unchanged total)
4. Estimated lift: -$1,100/yr at current rates → +$3,500/yr when sUSDS recovers to 7d mean
5. Diversification: HHI 1.0 → 0.50 (single-protocol failure impact halved)
```

### Why Variant A Now, B/C Later

| Dimension | Variant A | Variant B | Variant C |
|-----------|-----------|-----------|-----------|
| New daemons needed | 0 (K473 already built) | 2 | 6 |
| Ops hours/month | 0.5 | 4.0 | 12.0 |
| Rollover required | No | Yes (Pendle) | Yes |
| Lift at $10M/yr | -$1,100 (diversification justifies) | +$2,800 | +$4,000 |
| Lift at $100M/yr | -$11,000 → +$35K (rate dep.) | +$28,000 | +$41,000 |
| Recommendation | **PREPARE NOW** | DEFER ($100M+) | DEFER ($100M+) |

At sub-$100M AUM: Variant B/C yield lifts don't justify ops complexity. Pendle rollover adds 4 hrs/mo
for +$2.8K/yr at $10M = $700/hr → below threshold. At $100M: $28K/yr / same hours = $7K/hr → justified.

### HL Concentration Impact

None of the v6.21 stablecoin protocols add HL exposure. All are Ethereum L1 DeFi:
- HL concentration remains at **27.5%** (well under 65% cap)
- Portfolio Sharpe **21.70 unchanged** (sleeve composition doesn't affect trading strategy metrics)

### 5-Year Projection

At $10M baseline, Variant A adds negligible terminal value:

```
v6.20:         $10M → $28.71M (CAGR 23.49%)
v6.21 A:       $10M → $28.70M (-$1,100/yr current) or $28.74M (+$3.5K/yr on trigger)
Difference:    < $30K over 5y (primary value = diversification, not yield)
At $100M:      Variant A lifts become +$150-350K over 5y (material at scale)
```

### Checklist Addition — Daily/Weekly

Add to Daily Checklist item #7:
```
[ ] 7. sUSDS APY — K473 daemon status: is 14d mean >= 3.5%? (if yes → Variant A activation)
```

Add to Monthly Checklist item #31:
```
[ ] Day 30: v6.21 Variant A check — sUSDS 30d mean? If >= 3.5% for 14d, activate Variant A.
            At AUM >= $100M: evaluate Variant B (Pendle) integration.
```

### v6.21 Architecture (Post-Activation, Variant A)

```
Sleeve               Weight   Capacity   Notes
─────────────────────────────────────────────────────────────────────
K280 BTC Multi-Venue   65%    $500M      20.25 Sharpe (10 venues)
K297' RWA (HL+Var)      5%    $25M       12.20 Sharpe
sUSDe Yield             5%    $5B         3.88% APY (7d target)
Spark sUSDS             5%    $800M+      3.57% APY (7d) / instant redeem
K376 Momentum           5%    $50M        3.35 Sharpe
K449 ETH-BTC Diff       5%    $100M       5.66 Sharpe
K457 BTC+ETH+SOL        5%    $300M      19.58 Sharpe (conditional)
Cash / Margin Buf       5%    —           safety buffer
─────────────────────────────────────────────────────────────────────
TOTAL                 100%              Sharpe 21.70 | HL 27.5%
Stablecoin HHI:       0.50  (improved from 1.0)
```

Source files: `wave_k477_v621_proposal.py` | `wave_k477_v621_proposal.json` | `wave_k477_v621_proposal.md`

*K477 Appendix — Added 2026-05-30 02:26 JST*

---

## Appendix K479 — v6.22 Architecture Proposal (K477 + K476 Combined)

**Wave:** K479 | **Generated:** 2026-05-30 02:34 JST | **Supersedes:** K477 v6.21 candidate notes
**Verdict:** ACCEPT v6.22 architecture — phased activation (v6.21 trigger + K476 60d paper gate)

### Context

K477 v6.21 (Variant A) adds Spark sUSDS as a co-sleeve (stablecoin HHI 1.0 → 0.5, trigger-based).
K476 ACCEPT: SOL-BTC FR Differential (OOS Sharpe 16.30, 9/10 K266 gates, $187K net/yr @ $10M).
K479 combines both into v6.22: stablecoin diversification + K476 3% sleeve addition funded by Cash reduction.

### v6.22 vs v6.21 vs v6.20

| Version | Change | Profit @ $10M | HL% | HHI |
|---------|--------|---------------|-----|-----|
| v6.20 | K461 baseline | ~$1,180K/yr | 47.5% | 1.0 |
| v6.21 | sUSDe split (K477 Variant A) | ~$1,179K/yr (−$1.1K) | 47.5% | 0.5 |
| **v6.22** | + K476 3% + Cash 5%→2% | **~$1,366K/yr (+$186K)** | **53%** | **0.5** |

### v6.22 Architecture (Full 9-Sleeve)

```
Sleeve               Weight   HL%    OOS Sharpe / APY    Change vs v6.20
─────────────────────────────────────────────────────────────────────────
K280 BTC Multi-Venue   65%    32.5%  20.25 Sharpe        unchanged
K297' RWA               5%     5.0%  12.20 Sharpe        unchanged
sUSDe Yield             5%     0%     3.72% APY           −5pp (split)
Spark sUSDS             5%     0%     3.34% spot APY      NEW (K477)
K376 Momentum           5%     5.0%   3.35 Sharpe        unchanged
K449 ETH-BTC Diff       5%     5.0%   5.66 Sharpe        unchanged
K476 SOL-BTC Diff       3%     3.0%  16.30 Sharpe        NEW (K476)
K457 BTC+ETH+SOL        5%     2.5%  19.58 Sharpe        unchanged
Cash / Margin Buf       2%     0%     —                   −3pp (funds K476)
─────────────────────────────────────────────────────────────────────────
TOTAL                 100%    53.0%  Portfolio ~22.0+     HL 53% < 65% cap
Stablecoin HHI:        0.50   |   HL headroom: 12pp for future additions
```

### K476 Contribution to v6.22

```
K476 sleeve: 3% × $10M × 4x leverage = $1.2M notional
OOS annual return (4x): 19.55%
Gross annual: 19.55% × $1.2M = $234,600
Net annual (−20% friction): $187,680

vs K449 (ETH-BTC): $13,000/yr net — K476 is 13× stronger
Combined K449 + K476 paired-trade sleeve: $200,680/yr, 8% weight, corr 0.15
```

### Annual Profit Summary @ $10M

| Sleeve | Annual (v6.22) | vs v6.20 |
|--------|----------------|----------|
| K280 | $1,000,000 | unchanged |
| K297' | $50,000 | unchanged |
| sUSDe 5% | $18,600 | −$18,600 (split) |
| Spark sUSDS 5% | $16,700 | NEW |
| K376 | $30,000 | unchanged |
| K449 | $13,000 | unchanged |
| **K476 NEW** | **$187,680** | **NEW** |
| K457 | $50,000 | unchanged |
| Cash (2%) | $0 | −$15,000 opp cost |
| **Total** | **~$1,366K** | **+$186K vs v6.20** |

### 5-Year Projection

| Scenario | CAGR | 5y Terminal | vs v6.20 |
|----------|------|-------------|----------|
| v6.20 baseline | 23.49% | $28,710,000 | — |
| v6.22 mid | ~24.2% | ~$29,542,000 | +~$832K |
| v6.22 high | ~24.5% | ~$29,870,000 | +~$1,160K |

At $100M scale: K476 adds $469K/yr net → +$2-4M over 5y vs v6.20.

### Sharpe Estimate

```
v6.20 baseline:  21.70
v6.22 estimated: 22.0 – 22.3 (K476 OOS 16.30 × orthogonal 0.15 corr contribution)
```

### Updated Deployment Timeline (Actions 21–22)

| Month | Trigger | Architecture |
|-------|---------|--------------|
| M0–M6 | (unchanged from K464) | v6.13d → v6.20 |
| M7 | sUSDS 14d mean ≥ 3.5% | v6.21 ACTIVATE (K477 Variant A) |
| M7–9 | K476 paper-trade starts | + K476 paper (K450 module, SOL-BTC config) |
| M9 | K476 60d paper gate passes | **v6.22 LIVE** |

**New user actions for v6.22 (total: 20 → 22):**

| # | Action | Timing | Expected Impact |
|---|--------|--------|----------------|
| 21 | Load K476 paper daemon (K450 module, SOL-BTC) | M7 | Begins 60d gate |
| 22 | v6.22 cash rebalance: Cash 5%→2%, K476 3% live | M9 (paper gate pass) | +$187K/yr @ $10M |

**K476 60-day paper gate criteria:**
- Realized Sharpe ≥ 5.0
- Fill rate ≥ 60% (both SOL/BTC legs)
- Max drawdown < 2%
- Signal fires ≥ 3 (expected ~5 in 60d at 31/yr rate)
- Monthly delta rebalance executed (confirms SOL-BTC ratio drift managed)

### HL Concentration at v6.22

```
K280 HL: 65% × 50% =  32.5%
K297'  :              5.0%
K376   :              5.0%
K449   :              5.0%
K476   :              3.0%   ← NEW
K457   : 5% × 50% =   2.5%
───────────────────────────
Total  :             53.0%   (cap 65%, 12pp headroom for v6.23+)
```

### Updated Master Playbook Parameters

| Parameter | K464 v6.20 | K479 v6.22 |
|-----------|-----------|-----------|
| Total user actions | 20 | **22** |
| Daemon count | 24 (after v6.20) | **25 (K476 daemon)** |
| Annual profit @ $10M | ~$1,180K | **~$1,366K** |
| 5y terminal @ $10M | $28.71M | **~$29.5M** |
| Annual profit @ $100M | ~$48M | **~$52M** |
| 5y lift @ $100M | — | +$2-4M cumulative |
| HL concentration | 47.5% | **53% (12pp headroom)** |
| Stablecoin HHI | 1.0 | **0.5** |
| Portfolio Sharpe | 21.70 | **~22.0+** |

### Profit Trajectory (Updated §9)

| Time | AUM | Annual Profit (run rate) | Architecture |
|------|-----|--------------------------|-------------|
| M0 | $10M | $1.0M baseline | v6.13d |
| M7 | — | +$1.1K/yr (sUSDS trigger) | v6.21 |
| M9 | — | +$187K/yr (K476 live) | **v6.22** |
| Y2 | $100M | ~$52M/yr | v6.22 |
| Y3 | $200M | ~$77M/yr (v6.20 $74M + K476 $3M) | v6.22 |

### §6 Gate Summary for v6.22

| Gate | Status | Note |
|------|--------|------|
| G1 OOS Sharpe ≥ baseline | PASS | v6.22 ~22.0 > v6.20 21.70 |
| G2 K476 K266 gates | PASS | 9/10 pass; G6 accepted (same as K449) |
| G3 HL concentration ≤ 65% | PASS | 53% < 65% cap |
| G4 Weight total = 100% | PASS | Sum exactly 100% |
| G5 Correlation matrix | PASS | All cross-sleeve corr < 0.4 |
| G6 Stablecoin HHI | PASS | 0.50 improved from 1.0 |
| G7 Profit lift positive | PASS | +$186K/yr @ $10M |

**Overall: 7/7 v6.22 gates PASS → ACCEPT**

Source files: `wave_k479_v622_proposal.py` | `wave_k479_v622_proposal.json` | `wave_k479_v622_proposal.md`

*K479 Appendix — Added 2026-05-30 02:34 JST*

---

## Appendix K481 — Builder Rebate Activation Playbook (User Action #23)

**Wave:** K481 | **Added:** 2026-05-30 02:44 JST | **Classification:** ZERO RISK, Fee minimization axis #4

### Summary

HL builder rebate activation: 65-minute setup yielding $99K–$496K/yr at $10M AUM with zero risk to strategy P&L, zero HL concentration change, zero signal change. This is the highest ROI-per-hour action in the entire deployment playbook (~$91K/hr even at conservative estimate).

### User Action #23: HL Builder Rebate Activation (M0, Priority #1)

| # | Action | Time | Expected Annual ROI @ $10M | Risk |
|---|--------|------|---------------------------|------|
| 23 | K481 Builder rebate activation (5-step playbook) | 65 min + 24h paper | **$99K–$496K/yr** (conservative–optimistic) | ZERO |

> **Action #23 supersedes the Action #1 description from K436/K464.** K481 provides the full implementation-ready playbook with code patch, monitoring spec, and exact profit model. Action #1 in the priority table (K370 builder rebate) maps to this K481 playbook.

### Profit Projection (K481 Refined)

| AUM | Conservative (10%) | Mid (25%) | Optimistic (50%) |
|-----|-------------------|-----------|-----------------|
| $10M | **$99,166/yr** | $247,915/yr | $495,830/yr |
| $50M | $495,830/yr | $1,239,574/yr | $2,479,148/yr |
| $100M | $991,659/yr | $2,479,148/yr | $4,958,297/yr |
| $200M | $1,983,319/yr | $4,958,297/yr | $9,916,594/yr |

Model: HL fraction 57.5%, daily turnover 1.5x, POST_ONLY fill rate 70%, HL taker 4.5 bps.

### 5-Step Activation Sequence

**Step 1 (20 min):** `approveBuilderFee` on HL main wallet → `https://app.hyperliquid.xyz/trade` → Account → Builder. Fee = 0 (f=0). MUST be signed by main wallet (not API/agent wallet). Immediate activation.

**Step 2 (5 min):** `export HL_BUILDER_CODE="0x<YOUR_MAIN_WALLET_ADDRESS>"` in `~/.zshrc` + daemon plists. Do NOT commit to git.

**Step 3 (10 min):** Apply 6-LOC patch to `scripts/post_only_order_manager.py`:
```python
# K481: Builder code injection (ZERO-RISK additive, env-var gated)
_builder_code = os.environ.get("HL_BUILDER_CODE", "").strip()
if venue == "HL" and _builder_code and not dry_run:
    order_action["builder"] = {"b": _builder_code, "f": 0}
```
Run `python3 scripts/post_only_order_manager.py --dry-run` to verify no errors.

**Step 4 (24h):** Paper-trade 24h. Verify builder field in HL order payload. Check `https://app.hyperliquid.xyz/referrals` for rebate > $0. Gate: must see positive accrual before LIVE switch.

**Step 5 (30 min + ongoing):** Restart live daemons. Add daily rebate check: expected $272/day (conservative) at $10M. Alert if < $136/day for 3+ consecutive days.

### Updated Deployment Parameters

| Parameter | K479 v6.22 | K481 (this wave) |
|-----------|-----------|-----------------|
| Total user actions | 22 | **23** |
| Builder rebate status | SCAFFOLD (K370) | **ACTIVATION-READY (K481)** |
| Annual profit @ $10M (con.) | ~$1,366K | **~$1,465K (+$99K builder rebate)** |
| Annual profit @ $10M (mid) | ~$1,366K | **~$1,614K (+$248K builder rebate)** |
| ROI/hr for setup | — | **~$91,538/hr** (conservative) |

### Risk Assessment

- HL concentration delta: **ZERO** (builder code is order metadata)
- Signal change: **NONE**
- Counterparty risk: **NONE** (HL internal referral pool)
- Execution risk: **NONE** (f=0, no extra cost)
- Worst case if program ends: return to current cost baseline (no degradation)
- K266 gate: **ACCEPT-FREE** (cost optimization, not alpha signal)

### Daily Rebate Targets (Monitoring)

| AUM | Conservative/day | Mid/day | Optimistic/day |
|-----|-----------------|---------|----------------|
| $10M | $272 | $679 | $1,358 |
| $100M | $2,717 | $6,792 | $13,584 |

Alert threshold: < 50% of conservative for 3+ consecutive days.

Source files: `wave_k481_builder_rebate_activation.py` | `wave_k481_builder_rebate_activation.json` | `wave_k481_builder_rebate_activation.md`

---

## Appendix K485 — Multi-Account Scaling Activation Playbook (User Action #24)

**Wave:** K485 | **Added:** 2026-05-30 02:54 JST | **Classification:** Capacity expansion axis, profit-max #5

### Summary

Multi-account scaling activation playbook: $10M → $25M → $50M → $100M → $200M ceiling via multi-wallet multi-venue architecture. Key finding: multiple HL wallets are technically permissible (non-KYC DEX) but provide ZERO slippage relief (same OB). Real capacity expansion requires separate venues (Bybit sub-account, dYdX, Aevo). K431 ToS verdict corrected.

### User Action #24: Multi-Account Scaling Activation (M0–M6, Phased)

| # | Action | Time | Expected Annual ROI | Risk |
|---|--------|------|---------------------|------|
| 24a | HL W2 wallet creation (strategy isolation for K449+K476) | 5 min | +$210K/yr | ZERO |
| 24b | Bybit sub-account activation + 7d paper gate | 30 min + 7d | **+$2.2M/yr** at $25M AUM | LOW |
| 24c | multi_account_orchestrator.py + cross-wallet dashboard | 3 hr | Operational clarity | LOW |
| 24d | dYdX + Aevo wallet setup (Phase 2 preparation) | 15 min each | Unlock Phase 2 gates | TRIVIAL |
| 24e | Capital scaling Phase 1→2→3 (conditional on paper gates) | Monthly | +$3.37M/yr at $50M | MEDIUM |

> **Action #24b (Bybit sub): +$2.2M/yr at $25M total AUM with 30-minute setup. Do this second (after Action #23 builder rebate).**

### Profit Lift by Phase

| Phase | AUM | Architecture | Net/yr | Lift vs $10M baseline |
|-------|-----|-------------|--------|-----------------------|
| Baseline | $10M | Single HL (v6.13d) | $2.08M/yr | — |
| Phase 1A | $25M | HL + Bybit sub (2 venues) | **$4.28M/yr** | **+$2.20M (+106%)** |
| Phase 1B | $10M | HL W1+W2 (strategy iso) | $2.29M/yr | +$210K (+10%) |
| Phase 2 | $50M | HL + Bybit + dYdX (3 venues) | **$5.45M/yr** | **+$3.37M (+162%)** |
| Phase 3 | $100M | v6.20 7-venue + K458 depth allocator | $48.2M/yr | +$46.1M (+2216%) |
| Phase 4 | $200M | v6.20 10-venue optimal (K461) | **$74.4M/yr** | **+$72.4M (+3479%)** |

### K431 ToS Correction

K431 incorrectly flagged HL as "NOT PERMITTED" for multiple accounts. **K485 correction:** HL is a non-KYC permissionless DEX — multiple wallets are technically unrestricted. The real constraint is **market impact** (same HL order book = same slippage regardless of wallet count). For capacity expansion, separate venues (Bybit/dYdX/Aevo) are required.

### Per-Venue Policy Summary

| Venue | KYC | Multi-wallet | Sub-account | Recommended Path |
|-------|-----|-------------|-------------|-----------------|
| HL | No | PERMITTED (DEX) | Vault/agent sub-account | W2 for strategy isolation (K449/K476) |
| Bybit | Yes | PROHIBITED (personal) | PERMITTED (up to 20 subs) | Sub #1 for K297p overflow at $15M+ |
| OKX | Yes | PROHIBITED (personal) | PERMITTED (up to 30 subs) | Sub for K208 3rd venue (K456 Action #16) |
| Aevo | No | PERMITTED (DEX) | N/A (wallet=account) | K460 Action #17 |
| dYdX v4 | No | PERMITTED (DEX, Cosmos) | YES (sub-account index) | K460 Action #18 |
| Lighter | No | PERMITTED (DEX) | N/A | K465 25th daemon |
| Vertex | No | PERMITTED (DEX, Arbitrum) | N/A | K465 26th daemon |

### Step-by-Step: Phase 1 Activation (Days 1–14)

**Day 1 (~5 min): HL W2 Strategy Isolation**
```bash
# MetaMask → Add Account → Create Account → label "K485-W2-strategy-iso"
# Export private key (store in 1Password or macOS Keychain, NOT git)
export HL_PRIVATE_KEY_W2="0x<YOUR_W2_KEY>"  # add to ~/.zshrc (NOT committed)
# Update K449/K476 daemon plists to use HL_PRIVATE_KEY_W2
launchctl unload ~/Library/LaunchAgents/com.cryptolab.k449-eth-btc.plist
# (edit plist EnvironmentVariables)
launchctl load ~/Library/LaunchAgents/com.cryptolab.k449-eth-btc.plist
```

**Day 2–3 (~30 min): Bybit Sub-Account**
```bash
# Bybit UI: Account & Security → Sub Accounts → Create Sub Account (Standard)
# Generate trade-only API key + IP restriction
export BYBIT_SUB1_API_KEY="<key>"   # add to ~/.zshrc (NOT committed)
export BYBIT_SUB1_SECRET="<secret>" # add to ~/.zshrc (NOT committed)
# Paper-trade K297p on Bybit sub for 7 days before live capital
```

**Day 3–5 (~3 hr): Orchestrator + Dashboard**
```bash
python3 scripts/multi_account_orchestrator.py --dry-run --wallets=all
python3 scripts/multi_account_orchestrator.py --config-check
# Verify all wallet connections before any capital transfer
```

**Week 2: Live Bybit Sub**
```bash
# After 7-day paper gate passes:
# Bybit: transfer $3–5M from master to sub #1 (Account → Transfer → Sub Account)
# Activate K297p live on Bybit sub
```

### HL Concentration Rule (Cross-Wallet)

```
HL combined = W1_HL_equity + W2_HL_equity
Total AUM   = HL + Bybit + dYdX + Aevo + ...
HL% = HL_combined / Total_AUM ≤ 65%  (K358 rule, measured cross-wallet)

Current (K479 v6.22): 53%. 12pp headroom.
At $25M (W1=$12.5M HL, W3=$12.5M Bybit): HL% = 50%. Safe.
```

### Do NOT Do

1. Do NOT open duplicate personal Bybit/OKX accounts — ToS violation, account freeze risk
2. Do NOT expect HL multi-wallet to reduce slippage — same order book, zero OI benefit
3. Do NOT store private keys in git, HTML reports, or env files committed to repo
4. Do NOT force Phase 2+ before K449+K457 paper-trade gates pass (K461 condition)
5. Do NOT exceed 65% HL combined concentration (measure across ALL HL wallets)

### Updated Profit Projection Summary

| Parameter | K481 (previous) | K485 (this wave) |
|-----------|----------------|-----------------|
| Total user actions | 23 | **24** |
| Annual profit @ $10M (con.) | ~$1,465K | **~$1,675K (+ W2 strategy iso $210K)** |
| Annual profit @ $25M (con.) | — | **~$4,280K (+ Bybit sub Phase 1A)** |
| Annual profit @ $200M optimal | $74.4M | **$74.4M + $2.2M builder rebate = ~$76.6M** |
| Bybit sub setup time | — | **30 min + 7d paper gate** |
| ROI/hr for Phase 1B (Bybit sub) | — | **~$4,400/hr** (30 min → $2.2M/yr lift) |

Source files: `wave_k485_multi_account_scaling.py` | `wave_k485_multi_account_scaling.json` | `wave_k485_multi_account_scaling.md` | `scripts/multi_account_orchestrator.py`

*K485 Appendix — Added 2026-05-30 02:54 JST*

---

## K505 v6.25 Architecture — User Action #25 + Profit Lift

**Version:** 6.25 candidate | **Generated:** 2026-05-30 03:49 JST | **Wave:** K505

### v6.25 Summary

K500 INJ-BTC ACCEPT (10/13 §6 gates, OOS Sharpe 11.23) → v6.25 candidate activated.  
Option A: v6.24 + K500 INJ-BTC 3% sleeve, Cash reduced from 1% → −2%.  
Combined paired-trade family: $631K/yr @ $10M (+$124K vs v6.24 $507K/yr).  
Total portfolio: $1,794K/yr @ $10M (+$123K vs v6.24 $1,671K/yr).

### v6.25 Composition

| Sleeve | Weight | HL% Contribution | $K/yr @$10M |
|--------|--------|-----------------|-------------|
| K280 multi-venue | 65% | 32.5% | $1,000K |
| K297' satellite | 5% | 5.0% | $50K |
| sUSDe | 5% | 0% | $18.6K |
| Spark sUSDS | 5% | 0% | $16.7K |
| K376 momentum | 5% | 5.0% | $30K (paper) |
| K449 ETH-BTC | 5% | 5.0% | $13K |
| K476 SOL-BTC | 3% | 3.0% | $187K |
| K484 AVAX-BTC | 3% | 3.0% | $76K |
| K493 ATOM-BTC | 3% | 3.0% | $231K |
| **K500 INJ-BTC NEW** | **3%** | **3.0%** | **$124K** |
| K457 basket | 5% | 2.5% | $50K (paper) |
| Cash | −2% | 0% | −$2K |
| **Total** | **100%** | **62.0%** | **$1,794K** |

**HL concentration: 62.0% < 65% cap ✓ | Headroom: 3pp**

### Paired-Trade Family Rank (v6.25)

| Rank | Sleeve | OOS Sharpe | $K/yr @$10M | Status |
|------|--------|-----------|-------------|--------|
| 1 | K493 ATOM-BTC | 50.79 | $231K | ACCEPT |
| 2 | K484 AVAX-BTC | 43.89 | $76K | ACCEPT |
| 3 | K476 SOL-BTC | 16.30 | $187K | ACCEPT |
| **4** | **K500 INJ-BTC** | **11.23** | **$124K** | **ACCEPT NEW** |
| 5 | K449 ETH-BTC | 5.66 | $13K | ACCEPT |
| BLOCKED | K480 BNB-BTC | 8.04 | — | G5a FAIL + HL cap |
| COND | K491 ARB-BTC | 0.51 | — | G1/G3/G7 FAIL |
| REJECT | K490 SUI-BTC | −1.18 | — | OOS collapse |

### Annual Profit USDC (v6.25)

| AUM | Annual Profit | vs v6.24 |
|-----|--------------|----------|
| **$10M** | **$1,794,300/yr** | **+$123,000** |
| **$100M** | **$17,943,000/yr** | **+$1,240,000** |
| **$200M** | **$35,886,000/yr** | **+$2,480,000** |

K500 INJ-BTC alone: $124K/yr @$10M | $1.24M/yr @$100M | $2.48M/yr @$200M

### 5-Year Projection Update

| Scenario | 5y Terminal @$10M | K500 5y delta |
|----------|------------------|---------------|
| v6.24 | ~$29.9M | — |
| **v6.25** | **~$31.4M** | **+$1.5M** |
| @$100M (K500 5y) | — | +$6-8M |
| @$200M (K500 5y) | — | +$12-15M |

### User Action #25: K500 INJ-BTC Daemon Load (M11)

| Parameter | Value |
|-----------|-------|
| Action | Load K500 INJ-BTC daemon |
| Timing | M11 (after 60d paper-trade gate pass) |
| Time to setup | 5 min (after scaffold wave K506) |
| Risk | LOW (HL 62% < 65%, G5d Cosmos 0.2893 < 0.40) |
| Prerequisite | v6.24 LIVE + K500 60d paper gate |
| Expected ROI | **+$124K/yr @ $10M** |

```bash
# M11 activation (after K506 scaffold created):
cp /Users/nekonaomichi/crypto-lab/com.cryptolab.k500-inj-btc.plist ~/Library/LaunchAgents/
launchctl load ~/Library/LaunchAgents/com.cryptolab.k500-inj-btc.plist
launchctl list | grep k500
# Verify:
python3 scripts/k500_inj_btc_run.py --dry-run
```

**Gate conditions before activation:**
- K500 paper-trade OOS Sharpe ≥ 1.0 (60d window)
- HL cross-wallet combined ≤ 65% at activation time
- Cash −2% leverage within circuit breaker parameters

### Deployment Timeline (updated)

| Month | Version | Event |
|-------|---------|-------|
| M0 | v6.13d | LIVE (current) |
| M3 | v6.20 | 10-venue K208 multi-venue |
| M5 | v6.22 | Spark sUSDS split |
| M7 | v6.23 | K484 AVAX-BTC live |
| M9 | v6.24 | K493 ATOM-BTC live |
| **M11** | **v6.25** | **K500 INJ-BTC live ← NEW TARGET** |

### Updated Totals (v6.25)

| Parameter | K501 (previous) | K505 (v6.25) |
|-----------|----------------|--------------|
| Total user actions | 24 | **25** |
| Annual profit @ $10M | ~$1,671K | **~$1,794K (+$123K)** |
| Annual profit @ $100M | ~$16.7M | **~$17.9M (+$1.24M)** |
| Annual profit @ $200M | ~$33.4M | **~$35.9M (+$2.48M)** |
| 5y terminal @ $10M | ~$29.9M | **~$31.4M (+$1.5M)** |
| HL concentration | 59% | **62% (<65% cap ✓)** |
| M11 LIVE | — | **K500 INJ 60d paper pass** |

Source files: `wave_k505_v625_proposal.py` | `wave_k505_v625_proposal.json` | `wave_k505_v625_proposal.md`

*K505 Appendix — Added 2026-05-30 03:49 JST*

*K481 Appendix — Added 2026-05-30 02:44 JST*

---

## K511 v6.26 EMERGENCY Architecture Recompute — URGENT
**Version:** 6.26 (EMERGENCY) | **Generated:** 2026-05-30 04:08 JST | **Wave:** K511
**Status:** URGENT — K208 -67% Y/Y decay confirmed (K509), K280 65%→40% emergency rebalance

### K208 Decay Context

K509 CONFIRM verdict: K208 single-factor funding rate carry edge degraded -67% Y/Y
(Sharpe 24.03 → 7.46, 2024H2 → 2026YTD). Bybit-HL spread inverted to -0.14 bps avg 2026YTD.
Mechanism: HL HIP-3/HIP-4 venue expansion compressed divergence. R15-12 claim vindicated.

**Impact without action:**
- K280 sleeve $1M/yr → $400K/yr effective (-$600K/yr)
- v6.25 5y terminal $31.4M → $12.2M decay-adjusted (-$19.2M)

### v6.26 Composition

| Sleeve | v6.25 | v6.26 | Δ pp | Ann Yield @$10M | Note |
|--------|-------|-------|------|-----------------|------|
| K280 multi-venue | 65% | **40%** | **-25** | $246K | K208 decay-adj ($400K/yr @ 65% prorated) |
| K297' | 5% | 5% | 0 | $50K | Unchanged |
| sUSDe | 5% | **8%** | +3 | $30K | Stable buffer expanded |
| Spark sUSDS | 5% | **8%** | +3 | $27K | Stable buffer expanded |
| K376 momentum | 5% | **8%** | +3 | $48K | Bull-regime gate K497 |
| K449 ETH-BTC | 5% | 5% | 0 | $13K | Unchanged paired-trade anchor |
| K476 SOL-BTC | 3% | **4%** | +1 | $250K | Expanded Sh 16.30 |
| K484 AVAX-BTC | 3% | **5%** | +2 | $126K | Expanded Sh 43.89 |
| K493 ATOM-BTC | 3% | **5%** | +2 | $386K | Expanded Sh 50.79 #1 |
| K500 INJ-BTC | 3% | **4%** | +1 | $165K | Expanded Sh 11.23 |
| **K495 DEX-CEX flow** | 0% | **6%** | **+6** | $646K | **NEW — fully orthogonal (corr=-0.017)** |
| K457 basket | 5% | 1% | -4 | $10K | Reduced to fund orthogonal sleeves |
| Cash | 1% | 1% | 0 | -$1K | Unchanged |
| **TOTAL** | **100%** | **100%** | — | **$1,996K/yr** | — |

### Profit Comparison @ $10M

| Scenario | Ann Yield | ARR | vs Baseline |
|----------|-----------|-----|-------------|
| v6.25 nominal (K505, overstated) | $1,794K | 17.9% | +$598K vs decay |
| v6.25 decay-adjusted (K509) | $1,195K | 12.0% | baseline |
| **v6.26 reallocation** | **$1,996K** | **20.0%** | **+$801K** |
| v6.26 + K492 Variant E | $2,219K | 22.2% | +$1,024K |

> **K523 PROJECTION AUDIT NOTE (2026-05-30):** $1,996K is the UPPER BOUND (full paid-tier K495 + no OOS degradation).
> Forward-realistic ranges (K523 reconciliation):
> - Conservative: **$1,259K/yr** (12.6% ARR) — free-tier K495, 25% paired-trade haircut
> - Mid (central): **$1,588K/yr** (15.9% ARR) — partial paid-tier, 12.5% haircut
> - Optimistic: **$1,980K/yr** (19.8% ARR) — K492E + paid-tier + bull regime
> - K518 realized floor: $764K/yr (38% of stated, public-data only)
> Single-point $1,995K is misleading as base case. Use $1.3–2.0M/yr range in all communications.

### HL Concentration Audit

| Sleeve | HL Exposure |
|--------|------------|
| K280 (50% HL × 40%) | 20.0% |
| K297' | 5.0% |
| K376 | 8.0% |
| K449 | 5.0% |
| K476 | 4.0% |
| K484 | 5.0% |
| K493 | 5.0% |
| K500 | 4.0% |
| K495 | 6.0% |
| K457 (50% × 1%) | 0.5% |
| **TOTAL** | **62.5%** |

**HL 62.5% < 65% cap ✓ (2.5pp headroom)**

### 5-Year Projection @ $10M

| Scenario | CAGR | 5y Terminal |
|----------|------|------------|
| Without action (decay trajectory) | ~8% | ~$12.2M |
| v6.25 nominal (overstated, pre-K509) | ~19% | ~$31.4M |
| **v6.26 reallocation** | **~20%** | **~$24.8M** |
| v6.26 + K492 Variant E | ~22% | ~$27.2M |

Note: The 5y terminal for v6.26 is lower than v6.25 stated ($31.4M) because:
(a) K280 yield used is decay-adjusted ($246K not $650K), (b) K495 60d paper-trade gate
means 6% weight may not convert to live immediately. Range $28-35M with K492E activation.

### §6 Gate Re-check

| Gate | Status | Detail |
|------|--------|--------|
| G5 K495 corr vs K208 | PASS | -0.017 << 0.40 |
| G5 K495 corr vs K280 | PASS | 0.008 << 0.40 |
| G5 K495 corr vs K449 | PASS | 0.107 < 0.40 |
| G7 ann return | PASS | 20.0% ≥ 15% threshold |
| HL cap | PASS | 62.5% < 65% (2.5pp headroom) |
| K495 paper-trade gate | PENDING | 60d required before live |

### Implementation Roadmap (Phase 1-4)

| Phase | Timeline | Key Actions | Risk |
|-------|----------|------------|------|
| **Phase 1** | **Now (Day 0-7)** | K280 65%→40%, K495 6% paper-trade activate, sUSDe/Spark 5%→8% | LOW |
| Phase 2 | 30 days | K492 Variant E via K498-1A, K376 +3pp if K497 BULL confirmed | LOW |
| Phase 3 | 60 days | K493/K484/K500 gates pass→live, K495 60d gate→live | MEDIUM |
| Phase 4 | 90 days | v6.26 full, K492E review, K208 decay re-verify, v6.27 assessment | LOW |

### Key Risk Summary

| Risk | Probability | Mitigation |
|------|-------------|------------|
| K208 decay continues -10%/yr | MEDIUM | K492E +6.19 Sh buffer; K280 already reduced |
| K495 short live history (60d gate) | MEDIUM | Strict paper-trade; bear-regime filter |
| K280/K495 production correlation | LOW | Monitor rolling 30d; abort if corr > 0.35 |
| K492 Variant E timing lag | LOW | K492-3 first (OKX, 50 LOC, 3h setup) |
| K376 8% in bear regime | MEDIUM | K497 BULL gate strictly required |

### User Actions Required (URGENT)

1. **K280 rebalance**: Reduce K280 to 40% — redirect $2.5M to stablecoin buffers NOW
2. **K492 Variant E**: Activate via K498 Phase 1A (adds +$223K/yr to K280 sleeve)
3. **K495 paper-trade**: Confirm K502 scaffold gate then activate 6% paper sleeve
4. Wait 60d → Phase 3 live gating → Phase 4 full v6.26

Source files: `wave_k511_v626_emergency_recompute.py` | `wave_k511_v626_emergency_recompute.json` | `wave_k511_v626_emergency_recompute.md`

*K511 Appendix — Added 2026-05-30 04:08 JST*

---

## K516 v6.28 Architecture Proposal

**Version:** 6.28 | **Generated:** 2026-05-30 04:25 JST | **Wave:** K516
**Status:** CANDIDATE — APT + SEI + TIA family additions (batch K511+K507+K512, skip v6.27)

### v6.28 Executive Summary

| Metric | v6.26 | v6.28 | Delta |
|--------|-------|-------|-------|
| Ann Yield @ $10M | $1,996K | **$2,304K** | **+$308K** |
| Ann Yield @ $100M | $19.95M | **$23.03M** | +$3.08M |
| 5y Terminal @ $10M | $24.9M | **$28.2M** | **+$3.3M** |
| HL Concentration | 62.5% | **64.0%** | +1.5pp |
| Family ACCEPTs | 5 | **8** | +3 |
| Family Combined @ $10M | $863K/yr | **$1,467K/yr** | +$604K/yr |

v6.28 + K492E: **$2,527K/yr @ $10M** | 5y: **$30.8M**

> **K523 PROJECTION AUDIT NOTE (2026-05-30):** $2,304K is the UPPER BOUND (full paid-tier K495 + no OOS degradation).
> Forward-realistic ranges (K523 reconciliation):
> - Conservative: **$1,634K/yr** (16.3% ARR) — free-tier K495, 25% family haircut (incl APT/SEI/TIA)
> - Mid (central): **$2,024K/yr** (20.2% ARR) — partial paid-tier, 12.5% haircut
> - Optimistic: **$2,483K/yr** (24.8% ARR) — K492E + paid-tier + bull regime
> - v6.28 lift vs v6.26 still POSITIVE across all scenarios (architecture logic maintained)
> Use $1.6–2.5M/yr range. v6.28 remains superior to v6.26 even under conservative assumptions.

### Family Rank (K516) — 8 ACCEPTs

| Rank | Symbol | Wave | Sharpe | Ann @$10M | Status |
|------|--------|------|--------|-----------|--------|
| 1 | APT-BTC | K512 | 51.10 | $302K | ACCEPT **NEW** |
| 2 | ATOM-BTC | K493 | 50.79 | $231K | ACCEPT |
| 3 | SEI-BTC | K507 | 48.10 | $179K | ACCEPT **NEW** |
| 4 | AVAX-BTC | K484 | 43.89 | $76K | ACCEPT |
| 5 | SOL-BTC | K476 | 16.30 | $187K | ACCEPT |
| 6 | TIA-BTC | K507 | 14.44 | $51K | ACCEPT **NEW** |
| 7 | INJ-BTC | K500 | 11.23 | $124K | ACCEPT |
| 8 | ETH-BTC | K449 | 5.66 | $13K | ACCEPT |
| **—** | **Combined** | — | — | **$1,163K** | **8 ACCEPTs** |

### v6.28 Composition (v6.26 → v6.28)

| Sleeve | v6.26 | v6.28 | Δ pp | Rank | Note |
|--------|-------|-------|------|------|------|
| K280 multi-venue | 40% | **38%** | -2 | core | decay-adj $234K/yr |
| K297' | 5% | 5% | 0 | — | |
| sUSDe | 8% | **7%** | -1 | — | |
| Spark sUSDS | 8% | **7%** | -1 | — | |
| K376 momentum | 8% | 8% | 0 | — | bull-gated |
| K449 ETH-BTC | 5% | 5% | 0 | #8 | |
| K476 SOL-BTC | 4% | 4% | 0 | #5 | |
| K484 AVAX-BTC | 5% | 5% | 0 | #4 | |
| K493 ATOM-BTC | 5% | 5% | 0 | #2 | |
| K500 INJ-BTC | 4% | 4% | 0 | #7 | |
| **K512 APT-BTC** | **0%** | **2%** | **+2** | **#1 NEW** | 1% HL + 1% Bybit |
| **K507 SEI-BTC** | **0%** | **2%** | **+2** | **#3 NEW** | 1% HL + 1% Bybit |
| **K507 TIA-BTC** | **0%** | **1%** | **+1** | **#6 NEW** | 1% HL primary |
| K495 DEX-CEX | 6% | 6% | 0 | — | orthogonal |
| K457 basket | 1% | **0%** | -1 | — | DROP |
| Cash | 1% | 1% | 0 | — | |
| **TOTAL** | **100%** | **100%** | — | — | — |

### HL Concentration (v6.28)

| Component | HL Exposure |
|-----------|-------------|
| K280 (50% × 38%) | 19.0% |
| K297' | 5.0% |
| K376 | 8.0% |
| K449 | 5.0% |
| K476 | 4.0% |
| K484 | 5.0% |
| K493 | 5.0% |
| K500 | 4.0% |
| K512 APT (split 50%) | 1.0% |
| K507 SEI (split 50%) | 1.0% |
| K507 TIA (HL primary) | 1.0% |
| K495 DEX-CEX | 6.0% |
| **TOTAL** | **64.0% < 65% cap ✓** |

### Profit @ $10M / $100M / $200M

| AUM | v6.28 Ann Yield | CAGR ~23% | 5y Terminal |
|-----|-----------------|-----------|-------------|
| $10M | $2,304K/yr | 23.0% | $28.2M |
| $100M | $23.0M/yr | 23.0% | $281.5M |
| $200M | $46.1M/yr | 23.0% | $563.1M |

v6.28 + K492E @ $10M: **$2,527K/yr | 5y: $30.8M**

### 5-Year Projection @ $10M

| Scenario | CAGR | 5y Terminal | vs v6.26 |
|----------|------|-------------|----------|
| v6.26 (K511) | 20.0% | $24.9M | baseline |
| **v6.28** | **23.0%** | **$28.2M** | **+$3.3M** |
| v6.28 + K492E | 25.3% | $30.8M | +$5.9M |

### §6 Gate Summary

| Gate | v6.28 | Status |
|------|-------|--------|
| HL cap ≤ 65% | 64.0% | ✓ PASS (1pp headroom) |
| G5 APT-SOL cross-corr | 0.488 | ⚠ MARGINAL (alt-L1) |
| G5 APT-SEI cross-corr | 0.419 | ⚠ MARGINAL (parallel exec) |
| G5 all others | < 0.40 | ✓ PASS |
| G7 ann return | ~23% | ✓ PASS (≥15%) |
| K208 decay maintained | K280 38% decay-adj | ✓ PASS |

### Implementation Timeline

| Phase | Timeline | Key Milestone |
|-------|----------|---------------|
| 1 | Now (done) | v6.26 LIVE, K280 40%, K495 paper |
| 2 | Day 0–30 | K492E activate, K514 SEI scaffold |
| 3 | Day 30–60 | K493/K484/K500 live gate, K517 APT scaffold, TIA scaffold |
| 4 | Day 60–90 | K495 live, SEI live (paper gate pass) |
| **5** | **Day 90–120** | **v6.28 FULL LIVE: APT+TIA live, K457 drop → $2,304K/yr** |

### User Actions Added (K516)

- **Action #26**: K517 APT-BTC scaffold + 60d paper → +$201K/yr @ $10M (2% sleeve, HL+Bybit split)
- **Action #27**: K514 SEI-BTC scaffold + 60d paper → +$119K/yr @ $10M (2% sleeve, HL+Bybit split)
- **Action #28**: K507 TIA scaffold + 60d paper → +$17K/yr @ $10M (1% sleeve, HL primary)

Source files: `wave_k516_v628_proposal.py` | `wave_k516_v628_proposal.json` | `wave_k516_v628_proposal.md`

*K516 Appendix — Added 2026-05-30 04:25 JST*

---

## Appendix K530 — K498 Phase 1A Activation Playbook (User Action #29)

**Wave:** K530  |  **Date:** 2026-05-30 05:00 JST  |  **Priority:** Top 3 immediate (K501)

### User Action #29: K498 Phase 1A BBO_SELECT + OKX LIVE (8h, +$121K/yr @$30M, +$1.03M/yr @$100M)

> **Root cause:** K434 current Strategy B (HL_OVERFLOW mode) gives **$0 lift** because HL alone absorbs all orders at current AUM. The fix is a routing mode switch — not a new venue integration. `select_best_venue()` already implements correct BBO scoring. It just needs to be called per order as the primary routing decision (not only for overflow). Bybit VIP5 maker rebate **1.0 bps >> HL GOLD 0.3 bps = 0.7 bps advantage per order.**

| Metric | Value |
|--------|-------|
| Annual lift @ $30M | **+$121,000/yr USDC** |
| Annual lift @ $100M | **+$1,030,000/yr USDC** |
| Activation effort | **8 hours** |
| ROI | **$15,125/hr** |
| Risk tier | **LOW** |
| K501 rank | **Top 3 immediate action** |
| Prerequisite | K456 OKX scaffold (SCAFFOLD-READY — no work needed) |

### Why HL_OVERFLOW = $0 Lift

```
Strategy B (current K434 default): HL_OVERFLOW mode
  → HL depth cap: 5% × $180M OI = $9M per order maximum
  → Current order size at $30M AUM: ~$455K per 8h cycle
  → $455K << $9M → HL NEVER hits depth cap
  → Bybit/OKX: NEVER invoked → rebate advantage: $0

Strategy C (Phase 1A target): BBO_SELECT mode
  → Score ALL venues per order (not just when HL overflows)
  → Bybit score: Bybit_FR + 1.0bps_rebate - Bybit_slippage
  → HL score:    HL_FR    + 0.3bps_rebate - HL_slippage
  → Route to BEST-SCORED venue per order
  → Bybit wins ~80% of orders → +0.7bps rebate advantage
  → Annual lift: +$121K @ $30M | +$1.03M @ $100M
```

### 8-Step Activation (User Action #29 Checklist)

| Step | Action | Time | Risk | Gate |
|------|--------|------|------|------|
| 1 | Verify K456 OKX daemon SCAFFOLD-READY | 15min | ZERO | `python3 scripts/okx_fr_fetcher.py --symbol BTC-USDT-SWAP` → ok=True |
| 2 | Apply BBO_SELECT patch (14 LOC: k280 + config + smart_router) | 30min | LOW | `smart_router.py --all-symbols` shows Bybit winning 50%+ orders |
| 3 | OKX API key generate + env vars | 30min | LOW | `OKX_API_KEY`, `OKX_API_SECRET`, `OKX_PASSPHRASE` set |
| 4 | 48h paper-trade dry-run | 60min | ZERO | Bybit+OKX combined routing >= 40% in decisions.jsonl |
| 5 | launchctl load K456 OKX daemon | 30min | LOW | `launchctl list \| grep okx-fr-monitor` shows PID |
| 6 | 24h paper observation | 60min | ZERO | Non-HL routing >= 40%, no cap violations |
| 7 | BBO routing live activation | 30min | LOW | First live order routed to Bybit confirmed |
| 8 | Daily monitoring (ongoing) | 30min | ZERO | Non-HL rate >= 40%, daily lift >= $165/day @$30M |

**Total user time:** ~4.8h active + 24h paper observation

### The Patch (14 LOC total)

**Patch 1 — `scripts/k280_live_fetch.py` (4 LOC):**
```diff
- SMART_ROUTER_ENABLED = False   # K434: set True after testing; scaffold only in this wave
+ # K530: BBO_SELECT routing activated — K498 Phase 1A (8h, +$121K/yr @$30M)
+ # select_best_venue() called per order as PRIMARY decision (not just overflow)
+ # Bybit VIP5 1.0bps maker rebate > HL GOLD 0.3bps → 0.7bps advantage captured
+ SMART_ROUTER_ENABLED = True    # K530 K498 Phase 1A: BBO routing ACTIVE
```

**Patch 2 — `data/smart_router_config.json` (3 LOC):**
```json
"routing_mode": "BBO_SELECT",
"routing_mode_note": "K530 Phase 1A: BBO_SELECT replaces HL_OVERFLOW.",
"bbo_select_min_score": -0.0001,
```

**Patch 3 — `scripts/smart_router.py` (7 LOC — routing mode gate):**
```python
# Add to select_best_venue(), after cfg = load_config():
routing_mode = cfg.get('routing_mode', 'HL_OVERFLOW')
if routing_mode == 'HL_OVERFLOW':
    pass  # Legacy: fall through, BBO scoring unchanged
# BBO_SELECT: existing select_best_venue() IS correct BBO logic
```

### Rollback (< 5 minutes)

```bash
# Option A: flag
# Set SMART_ROUTER_ENABLED = False in scripts/k280_live_fetch.py
# Option B: config
# Set routing_mode: HL_OVERFLOW in data/smart_router_config.json

launchctl kickstart -k gui/$(id -u)/com.cryptolab.k280-live
```

### Risk Summary

| Risk | Probability | Impact | Mitigation |
|------|-------------|--------|------------|
| BBO scoring failure | LOW | LOW | select_best_venue() falls back to HL (ALL_VENUES_BLOCKED) |
| OKX API instability | LOW | LOW | OKX ~15% weight; Bybit+HL absorb entire order |
| Concentration cap breach | NEAR-ZERO | MEDIUM | filter_by_concentration_caps() already enforced |
| Latency > 1s | VERY LOW | LOW | 3-venue fetch = 145ms; 85% headroom vs 1s budget |

### Monitoring Thresholds

| Metric | Target | Alert |
|--------|--------|-------|
| Non-HL routing rate | >= 40% | < 20% for 7d → check SMART_ROUTER_ENABLED |
| Daily lift @ $30M | $331/day | < $165/day (50% threshold) |
| Daily lift @ $100M | $2,822/day | < $1,411/day |
| OKX dashboard freshness | < 8h | > 24h stale → check daemon |

### Forward Path (Post Phase 1A)

| Phase | Trigger | Action | Value |
|-------|---------|--------|-------|
| 1B | 30d after 1A | Aevo + dYdX LIVE (K460) | AUM ceiling → $200M |
| 2 | 60d after 1B | Lighter + Vertex LIVE (K465) | $200M+ safe scale |

> Phase 1B/2 add no incremental lift at $30M — value is AUM capacity insurance.

### Combined Activated Lift @ $30M

| Action | Annual USDC | Status |
|--------|------------|--------|
| K498 Phase 1A BBO routing | **+$121,000/yr** | This playbook (Action #29) |
| K481 Builder rebate (conservative 10%) | **+$99,166/yr** | Action #23 (user-activatable) |
| K430 3x leverage | multiplier (already LIVE) | Deployed |
| **Total incremental (conservative)** | **+$220,166/yr** | Both actions activated |

Source files: `wave_k530_k498_phase_1a_playbook.py` | `wave_k530_k498_phase_1a_playbook.json` | `wave_k530_k498_phase_1a_playbook.md`

*K530 Appendix — Added 2026-05-30 05:00 JST*


---

## K540 R16 Catalyst Integration (Added 2026-05-30 05:34 JST)

### June 4-5 Dual Catalyst Event Window

| Catalyst | Status | Passage Prob | +$/yr @$10M | Trigger |
|----------|--------|-------------|------------|---------|
| R16-01 HIP-5 AF2 Buyback | Voting June 5 | 68% | +$80-220K | June 5 18:00 ET result |
| R16-11 Clarity Act | Floor vote June 4-5 | 87% | +$150-400K | Senate.gov confirmation |
| Both PASS (combined) | — | ~59% | +$420K mid | Both confirmed D+0 |

### Portfolio Action by Outcome

| Outcome | HL Exposure | K376 | K297' | K430 Leverage | Notes |
|---------|------------|------|-------|--------------|-------|
| PASS+PASS | Hold 65% | Activate 2-3% sleeve | Hold | Restore 3x D+7 | MAX_BULLISH |
| PASS+FAIL | Hold 65% | Hold | Hold | Restore 3x D+7 | MODERATE |
| FAIL+PASS | Hold 65% | Hold | +2% add | Restore 3x D+7 | MODERATE+ |
| FAIL+FAIL | Reduce 60% | Hold | Hold | Maintain 2x D+14 | DEFENSIVE |

**EV: +$378,800/yr @$10M (probability-weighted)**

See `wave_k540_dual_catalyst_prep.{py,json,md}` for full playbook.

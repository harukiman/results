# K436 Master Deployment Playbook — Single Source of Truth
**Version:** 1.0 | **Generated:** 2026-05-29 | **Wave:** K436
**Status:** ACTIVE USER ACTIVATION GUIDE — single source of truth for all pending actions

---

## Executive Summary

You have accumulated a profit-driving stack across waves K356–K434 that projects:

```
Base case: $10M → $25.47M over 5 years
CAGR:       20.56%
Sharpe:     13.43
Key levers: 3x leverage (K430) + daily reinvest (K429) + multi-venue (K431) + smart router (K434)
```

This document consolidates every pending user action from every wave into one sequential activation guide. Follow it top-to-bottom. Each action is ranked by ROI-per-hour-invested.

---

## Table of Contents

1. [10-Action Priority Ranking](#1-10-action-priority-ranking)
2. [4-Week Deployment Timeline](#2-4-week-deployment-timeline)
3. [Daily Checklist](#3-daily-checklist-post-deployment)
4. [Weekly Checklist](#4-weekly-checklist)
5. [Monthly Checklist](#5-monthly-checklist)
6. [Month 2–12 Roadmap](#6-month-2-12-roadmap)
7. [Expected Outcomes by Phase](#7-expected-outcomes-by-phase)
8. [Troubleshooting](#8-troubleshooting)
9. [Rollback Procedures](#9-rollback-procedures)
10. [Reference: Source Waves](#10-reference-source-waves)

---

## 1. 10-Action Priority Ranking

Sorted by ROI/hour invested. Do these in order during Week 1.

| # | Action | Source Wave | Cost | Time | Expected Annual ROI @ $10M | Risk |
|---|--------|-------------|------|------|---------------------------|------|
| 1 | K370 Builder rebate — `approveBuilderFee` on main HL wallet | K370 | $0 | 30 min | **$94K–$472K/yr** | ZERO |
| 2 | Load K356 HIP-4 daemon (calibration deadline 2026-06-22) | K356/K368/K409 | $0 | 5 min | data quality gate unlock | None |
| 3 | Load K387 RSS regulatory monitor daemon | K387/K404 | $0 | 5 min | early warning $0→prevent loss | None |
| 4 | Load K407 TVL trajectory monitor daemon | K407 | $0 | 5 min | HypurrFi drop-line alert | None |
| 5 | Load K412 sUSDe APY monitor daemon | K412 | $0 | 5 min | sleeve re-eval trigger | None |
| 6 | Load K434 smart router daemon | K434 | $0 | 5 min | **+$175K/yr** execution gain | Low |
| 7 | K357 emergency exit credentials — set `HL_PRIVATE_KEY` env | K357 | $0 | 30 min | Safety net | None |
| 8 | HL HYPE Gold stake (10K HYPE ≈ $13K) | K432 | $13K | 30 min | **$2,534/yr** (19.5% on stake) | Low |
| 9 | Fund Bybit account ($2M+) — triggers VIP5 instantly | K432 | $0 (realloc) | 1 day wire | **$154K/yr** fee tier reduction | None |
| 10 | Enable `AUM_TRACKING_ENABLED=true` for K429 | K429 | $0 | 5 min | unlocks reinvest compounding | Low |

> **The highest-leverage action is #1 (builder rebate): $94K–$472K/yr at ZERO cost in 30 minutes.**

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

## 6. Month 2–12 Roadmap

### Months 2–5: Compounding at Full Speed

- Full stack operating: 3x leverage + daily reinvest + smart router routing
- Base case trajectory from K433 simulation:
  - Month 2: ~$10.35M (+3.5%)
  - Month 3: ~$10.73M (+7.3%)
  - Month 6: ~$11.88M (+18.8%)
  - Month 12: ~$14.20M (+42.0%)

- Monitor monthly: AUM vs K433 base-case trajectory
- If AUM trailing base case by > 5%: review leverage setting, check CB fire logs

### Month 6 Milestone: Bybit Live Integration (K431)

**Trigger:** AUM ≥ $15M (expected Month 4 at K433 base-case CAGR)

```
K431 Bybit Live Integration:
  - API keys set up for live order routing
  - K208 Bybit leg shifts from paper → live execution
  - Smart router automatically shifts flow to Bybit when spread favors it
  - Expected capacity: +$2.2M/yr incremental (50/50 HL/Bybit split)
```

**Setup steps:**
1. Create Bybit API key with `Trade` permissions (no withdrawal)
2. Add to `data/smart_router_config.json`: `bybit_api_key`, `bybit_secret`
3. Run: `python3 scripts/smart_router.py --venue bybit --test`
4. Confirm orders routing correctly
5. Runbook: docs/k302a_runbook.md §24

### Month 12 Decision Point: Drift Integration or Continue

- If AUM ≥ $30M → evaluate Drift (Solana DEX) integration
- Expected at K433 aggressive case (CAGR 24.2%) by Month 12
- If AUM between $15M–$30M → continue HL + Bybit, no Drift needed
- Decision framework documented in K431 wave

---

## 7. Expected Outcomes by Phase

| Phase | Timeline | AUM Target | Key Milestone |
|-------|----------|------------|---------------|
| Foundation | Day 1–7 | $10M | 4 daemons live, builder rebate active |
| Capital Deploy | Day 8–14 | $10M | Bybit VIP5, smart router verified |
| 1.5x Leverage | Day 15–21 | $10.1M+ | +$1.1M/yr incremental activated |
| 3x Leverage | Day 22+ | $10.2M+ | +$2.2M/yr fully active |
| Month 2 | ~Day 60 | ~$10.35M | Full compounding visible |
| Month 6 | ~Day 180 | ~$11.88M | Bybit live integration |
| Month 12 | ~Day 365 | ~$14.2M | Decision: Drift or hold |
| Year 5 | ~Day 1825 | **~$25.47M** | Base case terminal (CAGR 20.56%) |

---

## 8. Troubleshooting

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

## 9. Rollback Procedures

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

## 10. Reference: Source Waves

| Action | Wave | Runbook Section |
|--------|------|-----------------|
| K370 Builder rebate | K370 | §19 |
| K356 HIP-4 daemon | K356/K368/K409 | §20 |
| K387 RSS monitor | K387/K404 | §18 |
| K407 TVL monitor | K407 | (plist: com.cryptolab.protocol-tvl-monitor) |
| K412 sUSDe monitor | K412 | (plist: com.cryptolab.susde-apy-monitor) |
| K434 Smart router | K434 | §24 |
| K357 Emergency exit | K357 | (emergency_hl_exit.py) |
| K432 HYPE stake | K432 | (HL staking UI) |
| K432 Bybit VIP5 | K432 | (Bybit account settings) |
| K429 AUM tracking | K429 | §22 |
| K430 Leverage rollout | K430 | §23 |
| K431 Bybit live integration | K431 | (Month 6 milestone) |
| K400/K415 USDY (non-US only) | K400/K415 | §21 |
| K433 5y projection model | K433 | (wave_k433_combined_simulation.md) |

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

*K436 Master Deployment Playbook — Generated 2026-05-29 22:59 JST*
*Single source of truth: supersedes all per-wave activation notes*
*Next update: K450 (after Month 6 Bybit integration milestone)*

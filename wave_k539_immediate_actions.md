# K539 Immediate Action Consolidation — 4-Phase D0-D60
**Wave:** K539 | **Generated:** 2026-05-30 05:30 JST | **Supersedes:** K532 Governance v5
**Status:** USER ACTION REQUIRED — 4 phases sequenced, D0 start today

---

## Executive Summary

Three converging profit paths resolved into a single coordinated playbook.
All blocked by the same constraint: **HL 65% cap + K280 overweight**.

| Path | Value | Constraint | ETA |
|------|-------|------------|-----|
| K376 BULL unlock | +$247K/yr @ 3% sleeve | HL exactly at 65% cap | 7 days (K527) |
| K208 decay defense | Prevent $0.6M/yr loss | K280 75% → 40% needed | D0 action |
| K498 Phase 1A | +$121K/yr @ $30M | SMART_ROUTER_ENABLED=False | D7 (8hr) |

**Realistic profit trajectory @$10M AUM:**

| Phase | Timing | Annual Range | Central |
|-------|--------|-------------|---------|
| Baseline (no action) | Now | $400K–$600K | $500K |
| Phase A active | D0 | $650K–$850K | $748K |
| Phase B active | D14 | $1.05M–$1.45M | $1.25M |
| Phase C active | D30 | $1.35M–$1.95M | $1.65M |
| Phase D active | D60 | $1.55M–$2.35M | $1.95M |

---

## Production State Baseline (v6.13d LIVE)

```
Composition: K280 75% + K297' 20% + sUSDe 5%
HL exposure:  65.0% (EXACTLY at cap — K524)
Daemons:      37 total, all SCAFFOLD-READY, 0 mismatches
K208 decay:   -67% Y/Y (K509) — CRITICAL defensive urgency
Baseline:     ~$400-600K/yr declining
```

---

## Sleeve GANTT Chart D0-D60

```
Strategy                   D0     D7    D14    D30    D60  Note
------------------------------------------------------------------------------------------
K280                      75%    60%    40%    38%    38%  K511 v6.26 full reduction; K208 decay mitigat
K297p                     20%     5%     5%     5%     5%  reduce; headroom freed for new strategies
sUSDe                      5%     8%     8%     8%     8%  stablecoin yield expansion
Spark sUSDS                0%     0%     8%     8%     8%  add D14 post-K280 reduction
K376 momentum              0%     1%     3%     5%     8%  paper D0→live D7 (1%) → BULL_CONFIRMED D14 (3
K495 DEX-CEX flow          0%     1%     1%     6%     6%  1% test D7, 6% post-paper-gate D30
K449 ETH-BTC               0%     0%     0%     5%     5%  activate D7 daemon; sleeve D30 post-gate
K476 SOL-BTC               0%     0%     3%     3%     3%  D14 post K280 restructure
K484 AVAX-BTC              0%     0%     0%     3%     3%  60d paper gate; activate D30 if pass
K493 ATOM-BTC              0%     0%     0%     3%     3%  60d paper gate; activate D30 if pass
K500 INJ-BTC               0%     0%     0%     3%     3%  60d paper gate; activate D30 if pass
K507 SEI                   0%     0%     0%     0%     2%  D60 paper-gate complete
K507 TIA                   0%     0%     0%     0%     1%  D60 paper-gate complete
K512 APT                   0%     0%     0%     0%     2%  D60 paper-gate complete
K521 Options               0%     0%     0%     0%     0%  paper only — no live allocation yet
------------------------------------------------------------------------------------------
TOTAL                    100%    75%    68%    87%    95%
HL EXPOSURE               65%    57%    52%    54%    64%
```

> HL hard cap 65% — enforced at each milestone.
> All new strategies paper-only until gate pass.

---

## Phase A: Immediate Actions
**Timing:** D0 — 30 minutes | **Priority:** CRITICAL
**Profit uplift:** +$247,915/yr (K481 builder rebate)
**Result version:** v6.13d (unchanged, K481 rebate added)

### User Action Checklist

| Step | Action | Effort | Risk | +$/yr |
|------|--------|--------|------|-------|
| A1 | K481-A: HL approveBuilderFee registration | 30 min | ZERO | $247,915 |
| A2 | Verify all 37 SCAFFOLD-READY daemons pre-conditions | 5 min | ZERO | — |
| A3 | Confirm v6.13d composition baseline in data/portfolio_config.json | 2 min | ZERO | — |


### Commands

#### A1: K481-A: HL approveBuilderFee registration
```bash
# On HL main wallet — execute approveBuilderFee transaction per K481 playbook
```
Verify: Builder rebate visible in HL account settings within 24h

#### A2: Verify all 37 SCAFFOLD-READY daemons pre-conditions
```bash
launchctl list | grep cryptolab | wc -l
```
Verify: Count matches expected loaded daemons

#### A3: Confirm v6.13d composition baseline in data/portfolio_config.json
```bash
python3 wave_k539_immediate_actions.py --verify
```
Verify: K280=75%, K297p=20%, sUSDe=5% confirmed

---

## Phase B1: K280 Sleeve Restructure (Step 1)
**Timing:** D0 — 4 hours | **Priority:** HIGH
**Profit uplift:** +$400K/yr defensive (K208 decay mitigation)
**Result version:** v6.13e-interim (K280=60%, K297p=5%, sUSDe=8%; K376+K495 paper 1% each)

### User Action Checklist

| Step | Action | Effort | Risk | +$/yr |
|------|--------|--------|------|-------|
| B1-1 | K280 weight config reduce 75% → 60% (v6.13e-interim) | 30 min | LOW | — |
| B1-2 | K297p reduce 20% → 5%, sUSDe increase 5% → 8% | 15 min | LOW | — |
| B1-3 | K376 paper-trade seed allocation 1% provisional | 15 min | ZERO (paper only) | — |
| B1-4 | K495 paper-trade seed allocation 1% | 15 min | ZERO (paper only) | — |
| B1-5 | Restart K280 live daemon with new config | 5 min | LOW | — |

**HL exposure after:** 57.5%

### Commands

#### B1-1: K280 weight config reduce 75% → 60% (v6.13e-interim)
```bash
# Edit data/portfolio_config.json: k280_weight: 0.60
```
Verify: HL exposure drops from 65% → 57.5%; K376 + K495 headroom freed

#### B1-2: K297p reduce 20% → 5%, sUSDe increase 5% → 8%
```bash
# Edit data/portfolio_config.json: k297p_weight: 0.05, susde_weight: 0.08
```
Verify: Total allocation sums to 100%; HL cap not breached

#### B1-3: K376 paper-trade seed allocation 1% provisional
```bash
# Edit data/portfolio_config.json: k376_paper_weight: 0.01
```
Verify: K376 daemon logging paper-trade at 1% notional

#### B1-4: K495 paper-trade seed allocation 1%
```bash
# Edit data/portfolio_config.json: k495_paper_weight: 0.01
```
Verify: K495 daemon logging paper-trade at 1% notional

#### B1-5: Restart K280 live daemon with new config
```bash
launchctl unload ~/Library/LaunchAgents/com.cryptolab.k280-live.plist && launchctl load ~/Library/LaunchAgents/com.cryptolab.k280-live.plist
```
Verify: launchctl list | grep k280-live shows PID

---

## Phase B2: K498 Phase 1A Smart Router + OKX
**Timing:** D7 — 8 hours | **Priority:** HIGH
**Profit uplift:** +$121K/yr @ $30M (BBO_SELECT routing)
**Result version:** v6.13e + smart router Phase 1A active

### User Action Checklist

| Step | Action | Effort | Risk | +$/yr |
|------|--------|--------|------|-------|
| B2-1 | Apply 14-LOC patch: SMART_ROUTER_ENABLED = True in scripts/k280_live_fetch.py | 30 min | LOW | $121,000 |
| B2-2 | Load OKX FR monitor daemon | 5 min | LOW | — |
| B2-3 | 24h paper observation period | 24h watch | ZERO | — |
| B2-4 | Confirm K449 daemon load (ETH-BTC paired trade) | 5 min | LOW | — |

**Prerequisite:** OKX API key set in environment

### Commands

#### B2-1: Apply 14-LOC patch: SMART_ROUTER_ENABLED = True in scripts/k280_live_fetch.py
```bash
# In scripts/k280_live_fetch.py:
# Change: SMART_ROUTER_ENABLED = False
# To:     SMART_ROUTER_ENABLED = True
# And update routing_mode in data/smart_router_config.json:
# {"routing_mode": "BBO_SELECT", "venues": ["HL", "Bybit", "OKX"]}
```
Verify: grep SMART_ROUTER_ENABLED scripts/k280_live_fetch.py shows True

#### B2-2: Load OKX FR monitor daemon
```bash
cp /Users/nekonaomichi/crypto-lab/com.cryptolab.okx-fr-monitor.plist ~/Library/LaunchAgents/ && launchctl load ~/Library/LaunchAgents/com.cryptolab.okx-fr-monitor.plist
```
Verify: launchctl list | grep okx-fr-monitor shows PID

#### B2-3: 24h paper observation period
```bash
# Monitor logs/okx_fr_monitor.log and data/smart_router_dashboard.json
```
Verify: BBO_SELECT routing decisions appearing in logs; no error spikes

#### B2-4: Confirm K449 daemon load (ETH-BTC paired trade)
```bash
launchctl load ~/Library/LaunchAgents/com.cryptolab.k449-eth-btc.plist
```
Verify: launchctl list | grep k449 shows PID

---

## Phase C: K376 BULL_CONFIRMED Activation
**Timing:** D14 — 4 hours (conditional on BULL_CONFIRMED) | **Priority:** CONDITIONAL
**Profit uplift:** +$247K/yr @ 3% sleeve (K376 momentum)
**Result version:** v6.26 (K280=40%, K376=3%, K495=1%, sUSDe=8%, Spark=8%)

### User Action Checklist

| Step | Action | Effort | Risk | +$/yr |
|------|--------|--------|------|-------|
| C1 | K376 BULL_CONFIRMED check (K497 trigger) | 2 min | ZERO | — |
| C2 | K376 sleeve increase paper 1% → live 1% | 30 min | MEDIUM (regime false positive) | $82,349 |
| C3 | K280 reduce 60% → 40% (full K511 v6.26) | 1 hr | LOW | — |
| C4 | Spark sUSDS add 8% sleeve | 2 hr | LOW | — |
| C5 | K376 sleeve expand 1% → 3% (D14 → D30) | 15 min | MEDIUM | $164,698 |

**HL exposure after:** ~52%
**Conditional on:** K497 BULL_CONFIRMED (ETA D7–D14 from K533 TRANSITION status)

### Commands

#### C1: K376 BULL_CONFIRMED check (K497 trigger)
```bash
python3 scripts/k497_regime_monitor.py --status
```
Verify: days_slope_positive >= 7; BTC 20d SMA slope > 0

#### C2: K376 sleeve increase paper 1% → live 1%
```bash
# Edit data/portfolio_config.json: k376_live_weight: 0.01
```
Verify: K376 fills appearing in fills.jsonl

#### C3: K280 reduce 60% → 40% (full K511 v6.26)
```bash
# Edit data/portfolio_config.json: k280_weight: 0.40
```
Verify: HL exposure < 55%; K376 3% + K495 1% within headroom

#### C4: Spark sUSDS add 8% sleeve
```bash
# Bridge 8% allocation to Spark protocol; update config
```
Verify: Spark sUSDS position visible; APY > 4%

#### C5: K376 sleeve expand 1% → 3% (D14 → D30)
```bash
# Edit data/portfolio_config.json: k376_live_weight: 0.03 (D14 gate pass)
```
Verify: Sharpe > 8 post 7d live; no drawdown > 5%

---

## Phase D: Full v6.28 Paired-Trade Family
**Timing:** D30–D60 | **Priority:** MEDIUM
**Profit uplift:** +$300-500K/yr (paired-trade family)
**Result version:** v6.28 (K280=38%, K376=5-8%, K495=6%, paired-trade family active)

### User Action Checklist

| Step | Action | Effort | Risk | +$/yr |
|------|--------|--------|------|-------|
| D1 | K376 expand 3% → 5% | 15 min | MEDIUM | $82,349 |
| D2 | K495 expand 1% → 6% (post-paper-gate D30) | 30 min | MEDIUM | $150,000 |
| D3 | K484 AVAX-BTC activate (paper gate complete) | 30 min | LOW | $75,683 |
| D4 | K493 ATOM-BTC activate (paper gate complete) | 30 min | LOW | $75,000 |
| D5 | K500 INJ-BTC activate (paper gate complete) | 30 min | LOW | $75,000 |
| D6 | K507 SEI+TIA activate (D60 paper gate) | 1 hr | MEDIUM | $50,000 |
| D7 | K512 APT activate (D60 paper gate) | 30 min | MEDIUM | $50,000 |
| D8 | K280 fine-tune 40% → 38% (HL re-balance target 64%) | 15 min | LOW | — |

**HL exposure after:** ~64%

### Commands

#### D1: K376 expand 3% → 5%
```bash
# Edit data/portfolio_config.json: k376_live_weight: 0.05
```
Verify: 60d paper Sharpe ≥ 8; BULL_CONFIRMED still active

#### D2: K495 expand 1% → 6% (post-paper-gate D30)
```bash
# Edit data/portfolio_config.json: k495_live_weight: 0.06
```
Verify: K495 paper 60d Sharpe ≥ 10; fill rate > 70%

#### D3: K484 AVAX-BTC activate (paper gate complete)
```bash
# launchctl load com.cryptolab.k484-avax-btc.plist; set weight 3%
```
Verify: Paper Sharpe ≥ 8; HL exposure < 65%

#### D4: K493 ATOM-BTC activate (paper gate complete)
```bash
# launchctl load com.cryptolab.k493-atom-btc.plist; set weight 3%
```
Verify: Paper Sharpe ≥ 8; HL exposure < 65%

#### D5: K500 INJ-BTC activate (paper gate complete)
```bash
# launchctl load com.cryptolab.k500-inj-btc.plist; set weight 3%
```
Verify: Paper Sharpe ≥ 8; HL exposure < 65%

#### D6: K507 SEI+TIA activate (D60 paper gate)
```bash
# launchctl load com.cryptolab.k507-sei-btc.plist; weight 2%+1%
```
Verify: Paper Sharpe ≥ 8; total HL < 65%

#### D7: K512 APT activate (D60 paper gate)
```bash
# launchctl load plist; weight 2%
```
Verify: Paper Sharpe ≥ 8; HL < 65%

#### D8: K280 fine-tune 40% → 38% (HL re-balance target 64%)
```bash
# Edit data/portfolio_config.json: k280_weight: 0.38
```
Verify: HL exposure ≈ 64%; total allocation = 100%

---

## Risk Summary

| ID | Risk | Severity | Phase | Mitigation |
|----|------|----------|-------|------------|
| R1 | K280 weight reduction → realized loss if K208 not permanentl | HIGH | B1 | Stage reduction 75%→60%→40% over D0→D14; monitor K208 daily  |
| R2 | BULL false positive at D14 (K376 premature live activation) | MEDIUM | C | Require 7 consecutive positive-slope days (K497); start at 1 |
| R3 | Phase 1A patch breaks smart router behavior unexpectedly | LOW | B2 | 24h paper observation post-patch; rollback flag ready |
| R4 | HL daemon restart user dependency (manual launchctl step req | LOW | B1 | Pre-write exact commands; test in staging first |
| R5 | Paper-gate strategies (K484/K493/K500) fail 60d Sharpe thres | MEDIUM | D | Gate ≥ 8 Sharpe strictly enforced; no live activation withou |
| R6 | HL concentration exceeds 65% cap if multiple strategies add  | HIGH | All | HL exposure tracking enforced at each step; 65% hard cap rul |

---

## Reference

| Source Wave | Topic |
|-------------|-------|
| K481 | HL builder rebate playbook |
| K497 | K376 BULL/BEAR regime monitor |
| K509 | K208 decay -67% Y/Y confirmation |
| K511 | v6.26 K280 65%→40% proposal |
| K523 | Realistic profit range calibration |
| K527 | K376 BULL_CONFIRMED ETA estimate |
| K530 | K498 Phase 1A activation playbook |
| K532 | Governance v5 — master action queue |
| K533 | K376 readiness check (TRANSITION zone) |

---

*Generated by wave_k539_immediate_actions.py | 2026-05-30 05:30 JST*
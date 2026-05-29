# K559 Week 4 Triple LIVE Activation Playbook

**Wave:** K559  
**Date:** 2026-05-30 06:25 JST  
**Strategies:** K500 INJ-BTC (D+21) · K507 SEI-BTC (D+23) · K507 TIA-BTC (D+25)  
**Week 4 combined:** +$354K/yr incremental  
**Cumulative W1-W4:** $861K/yr @ $10M | $2.58M @ $30M | $8.61M @ $100M  
**HL post-W4:** 64.5% (cap 65%, TIA Bybit-only contingency activated)

---

## Executive Summary

K559 is the Week 4 activation wave of the K547 Cosmos paired-trade cascade. Three strategies activate in cascade over 96 hours:

| Strategy | Day | OOS Sharpe | Ann. Return | Venue | HL Delta |
|----------|-----|-----------|-------------|-------|----------|
| K500 INJ-BTC | D+21 | 11.23 | $124K/yr | HL primary 3% | +3.0pp |
| K507 SEI-BTC | D+23 | 48.10 | $179K/yr | 1% HL + 1% Bybit | +1.0pp |
| K507 TIA-BTC | D+25 | 14.44 | $51K/yr | Bybit-only 1% | +0.0pp |
| **TOTAL** | — | — | **$354K/yr** | — | **+4.0pp** |

**Critical HL cap decision:** K507 TIA activates Bybit-only (not HL-primary) to hold HL at 64.5% vs 65% cap. If TIA used HL-primary: 65.5% → breach by 0.5pp.

---

## Cumulative Deployment Roadmap (W1-W5)

| Week | Strategy | Delta/yr | Cumulative @$10M | @$30M | @$100M |
|------|----------|---------|-----------------|-------|--------|
| W1 | K449 ETH-BTC | $13K | $13K | $39K | $130K |
| W2 | K476 SOL + K484 AVAX | $263K | $276K | $828K | $2.76M |
| W3 | K493 ATOM-BTC | $231K | $507K | $1.52M | $5.07M |
| **W4** | **K500 INJ + SEI + TIA** | **$354K** | **$861K** | **$2.58M** | **$8.61M** |
| W5 | K512 APT-BTC | $302K | $1,163K | $3.49M | $11.63M |

---

## Phase 1: Pre-Requisite Checklist

Before any Week 4 activation:

- **K449 W1 LIVE PASS** — K549 playbook, paper_trade_mode=false
- **K476+K484 W2 LIVE PASS** — per K558 playbook
- **K493 W3 LIVE PASS** — per K556 playbook, Sharpe ≥ 25 at D+21 gate
- **K280 sleeve 60%** — K552 Phase B1 applied (leverage_manager.py)
- **HL exposure verified** — scripts/verify_deployment_status.py → hl_exposure_pct ≈ 60.5%

```bash
# Quick prerequisite check
python3 wave_k559_week4_triple_live.py --phase1
```

---

## Phase 2-4: Scaffold State Audit

```bash
python3 wave_k559_week4_triple_live.py --phase2   # K500 INJ audit
python3 wave_k559_week4_triple_live.py --phase3   # K507 SEI audit
python3 wave_k559_week4_triple_live.py --phase4   # K507 TIA audit
```

### K500 INJ-BTC (k500_dashboard.json — K506 scaffold)

- OOS Sharpe: 11.23 | Ann return: $124K/yr @ $10M
- Position at scaffold: `LONG_INJ_SHORT_BTC` (signal firing)
- FR diff: INJ FR (-5.78e-05) − BTC FR (1.16e-05) = -6.94e-05 (negative = long INJ)
- Sleeve: 3% HL-primary → $300K margin, $1.2M notional @ 4x
- Gate: IN_PROGRESS (0/60 paper days — activated D+21 after W3 pass)

### K507 SEI-BTC (k507_dashboard.json — K514 scaffold)

- OOS Sharpe: 48.10 | Ann return: $179K/yr @ $10M
- Position at scaffold: `NEUTRAL` (signal not firing at scaffold time)
- Cosmos 3rd hypothesis: SEI EVM-compat + Cosmos SDK distinct from ATOM/INJ
- Split: HL 1.5% + Bybit 1.5% at scaffold; K559 uses 1% HL + 1% Bybit (2% total)
- Gate: IN_PROGRESS

### K507 TIA-BTC (k507_tia_dashboard.json — K524 scaffold)

- OOS Sharpe: 14.44 | Ann return: $51K/yr @ $10M
- Position at scaffold: `LONG_BTC_SHORT_TIA` (signal active)
- Celestia DA hypothesis: modular DA layer, rollup blob fees → orthogonal FR
- G5d corr vs ATOM: 0.05 (LOWEST in family — fully orthogonal)
- **K559 decision:** Bybit-only (0pp HL) to maintain 64.5% vs 65% cap

---

## Phase 5: D+21 K500 INJ-BTC LIVE Activation

**Trigger:** K493 realized 7d Sharpe ≥ 25 at D+21 gate

```bash
# Step 1: Verify K493 PASS
python3 -c "import json; d=json.load(open('data/k493_dashboard.json')); print(d['60d_sharpe'])"

# Step 2: HL margin pre-check
python3 scripts/emergency_hl_exit.py --dry-run --status

# Step 3: K500 plist LIVE edit
sed -i '' '/<string>--dry-run<\/string>/d' com.cryptolab.k500-inj-btc.plist
# Edit: PAPER_TRADE=False

# Step 4: Load daemon
cp com.cryptolab.k500-inj-btc.plist ~/Library/LaunchAgents/
launchctl load ~/Library/LaunchAgents/com.cryptolab.k500-inj-btc.plist

# Step 5: Verify
launchctl list | grep k500-inj-btc
python3 scripts/verify_deployment_status.py | grep hl_exposure
# Expected: HL ≈ 63.5%

# Step 6: Commit
git add com.cryptolab.k500-inj-btc.plist
git commit -m "K559 K500 plist: D+21 INJ-BTC LIVE activation"
git push origin main
```

**Sizing:**
- Sleeve capital: 3% × $10M = $300K
- Leverage: 4x → $1.2M notional
- HL leg: $1.2M (long INJ + short BTC on HL)
- HL delta: +3.0pp → 63.5% total
- K357 emergency exit: K500/INJ detection registered (per K506)

**Monitor:** 48h before D+23 SEI activation

---

## Phase 6: D+23 K507 SEI-BTC LIVE Activation

**Trigger:** K500 48h health check PASS (activity + no margin breach)

```bash
# Step 1: K500 48h check
python3 -c "import json; d=json.load(open('data/k500_dashboard.json')); print(d['position_state'], d['daily_pnl_usdc'])"

# Step 2: HL margin check
python3 scripts/emergency_hl_exit.py --dry-run --status  # < 75% utilisation

# Step 3: K507 SEI plist LIVE edit
sed -i '' '/<string>--dry-run<\/string>/d' com.cryptolab.k507-sei-btc.plist
# Edit: PAPER_TRADE=False; HL_SLEEVE=0.01; BYBIT_SLEEVE=0.01

# Step 4: Load daemon
cp com.cryptolab.k507-sei-btc.plist ~/Library/LaunchAgents/
launchctl load ~/Library/LaunchAgents/com.cryptolab.k507-sei-btc.plist

# Step 5: Verify HL ≈ 64.5%
python3 scripts/verify_deployment_status.py | grep hl_exposure

# Step 6: Commit
git add com.cryptolab.k507-sei-btc.plist
git commit -m "K559 K507 SEI plist: D+23 SEI-BTC LIVE (1% HL + 1% Bybit)"
git push origin main
```

**Sizing:**
- Total sleeve: 2% → $200K margin, $800K notional @ 4x
- HL leg: 1% = $400K notional (+1.0pp HL → 64.5%)
- Bybit leg: 1% = $400K notional (no HL contribution)
- Post-SEI HL: 64.5% (cap 65% → 0.5pp headroom)

---

## Phase 7: D+25 K507 TIA-BTC LIVE Activation (Bybit-only)

**Trigger:** K507 SEI 48h health check PASS  
**Critical:** TIA activates BYBIT-ONLY to hold HL ≤ 64.5%

```bash
# Step 1: SEI 48h check
python3 -c "import json; d=json.load(open('data/k507_dashboard.json')); print(d['position_state'], d['daily_pnl_usdc'])"

# Step 2: HL cap confirm (must be ≤ 64.5% before TIA loads)
python3 scripts/verify_deployment_status.py | grep hl_exposure

# Step 3: TIA plist — Bybit-only config
# Edit plist: PAPER_TRADE=False; SMART_ROUTER=BYBIT_ONLY; HL_SLEEVE=0; BYBIT_SLEEVE=0.01
sed -i '' '/<string>--dry-run<\/string>/d' com.cryptolab.k507-tia-btc.plist

# Step 4: Load TIA daemon
cp com.cryptolab.k507-tia-btc.plist ~/Library/LaunchAgents/
launchctl load ~/Library/LaunchAgents/com.cryptolab.k507-tia-btc.plist

# Step 5: Final cap verify (all 3 LIVE)
python3 scripts/verify_deployment_status.py | grep hl_exposure
# Expected: HL = 64.5% (unchanged — TIA Bybit-only = 0pp)

# Step 6: Commit
git add com.cryptolab.k507-tia-btc.plist
git commit -m "K559 K507 TIA plist: D+25 TIA-BTC LIVE (Bybit-only 1%, HL=64.5%)"
git push origin main
```

**Sizing:**
- Sleeve: 1% → $100K margin, $400K notional @ 4x
- Bybit-only: $400K on Bybit (0pp HL contribution)
- HL post-TIA: 64.5% (cap 65% → 0.5pp headroom preserved)
- Expected yield: $51K/yr @ $10M (Bybit liquidity adequate for 1% sleeve)

---

## Phase 8: HL Exposure Post-Week 4 Trajectory

| Step | HL% | Delta | Status |
|------|-----|-------|--------|
| v6.13d baseline | 65.0% | — | AT CAP |
| K280 Phase B1 cut (K552) | 57.5% | −7.5pp | SAFE |
| + K449 ETH-BTC W1 (5% HL) | 62.5% | +5.0pp | SAFE |
| + K476 SOL W2 (2% HL) | 64.5% | +2.0pp | SAFE |
| + K484 AVAX W2 (adj. −4pp + 2pp) | 60.5% | −2.0pp | SAFE |
| + K493 ATOM W3 (2.5% HL+2.5% Bybit) | 60.5% | +0.0pp | SAFE |
| + K500 INJ W4-D21 (3% HL-primary) | **63.5%** | +3.0pp | SAFE |
| + K507 SEI W4-D23 (1% HL+1% Bybit) | **64.5%** | +1.0pp | SAFE |
| + K507 TIA W4-D25 (1% Bybit-ONLY) | **64.5%** | +0.0pp | **0.5pp headroom** |

### Contingency Analysis

| Scenario | HL% | Status | Note |
|----------|-----|--------|------|
| RECOMMENDED: TIA Bybit-only | 64.5% | SAFE | 0.5pp headroom |
| ALT A: K500 HL+Bybit split (1.5/1.5) | 63.0% | SAFE | More headroom but less HL yield |
| ALT B: TIA HL-primary (original) | 65.5% | **BREACH** | +0.5pp over 65% cap |

**Decision: RECOMMENDED selected.** TIA Bybit-only, HL locked at 64.5%.

**Week 5 (K512 APT, 1% HL portion of 2% sleeve):** 64.5% + 1.0pp = 65.5% → will need cap review before APT activation. Options: expand headroom via K280 further cut or K449 Bybit migration.

---

## Phase 9: Day 28-35 Monitoring (All 3 Strategies)

Monitor window: D+25 (all 3 active) → D+35 (decision matrix)

### Daily Combined PnL Targets

| Strategy | Daily PnL | Venue | Signal direction |
|----------|-----------|-------|-----------------|
| K500 INJ-BTC | $340/day | HL | INJ FR < BTC FR → long INJ |
| K507 SEI-BTC | $490/day | HL+Bybit | SEI FR > BTC FR → long SEI |
| K507 TIA-BTC | $140/day | Bybit | BTC FR > TIA FR → long BTC short TIA |
| **Combined** | **$970/day** | — | — |

### Daily Monitoring Checklist

```bash
# All 3 in one pass
for f in data/k500_dashboard.json data/k507_dashboard.json data/k507_tia_dashboard.json; do
  python3 -c "
import json, sys
d = json.load(open('$f'))
g = d.get('gate_metrics', {})
print(f\"{d.get('strategy','?')}: state={d.get('position_state','?')} pnl=\${d.get('daily_pnl_usdc',0):.2f} sh={d.get('60d_sharpe',0):.2f} fill={g.get('current_fill_rate',0):.1%} gate={g.get('gate_status','?')}\")"
done

# HL margin check
python3 scripts/emergency_hl_exit.py --dry-run --status

# Cross-correlation (all 3 positions should be independent)
python3 -c "import json; [print(json.load(open(f))['position_state']) for f in ['data/k500_dashboard.json','data/k507_dashboard.json','data/k507_tia_dashboard.json']]"
```

### Alert Thresholds

| Metric | Warning | Alert |
|--------|---------|-------|
| Delta neutral drift | > 5% per strategy | > 10% → rebalance |
| HL margin utilisation | > 75% | > 80% → K386 fallback |
| Daily PnL (combined) | < 0 for 3 days | < 0 for 7 days → review |
| Fill rate | < 40% | < 20% → check router |
| Cross-strategy correlation | Positions identical for 7d | All same direction → diversification failure |

---

## Phase 10: Decision Matrix D+35

| Strategy | OOS Sharpe | PASS (≥50% OOS) | HOLD | ROLLBACK | PASS action |
|----------|-----------|----------------|------|----------|-------------|
| K500 INJ | 11.23 | Sh ≥ 5.6 | 3.4–5.6 | < 3.4 | Expand to 4% sleeve |
| K507 SEI | 48.10 | Sh ≥ 24 | 14–24 | < 14 | Expand to 3% sleeve |
| K507 TIA | 14.44 | Sh ≥ 7 | 4–7 | < 4 | Maintain 1% Bybit |

### Rollback Procedure (per strategy)

```bash
# Replace XX with strategy identifier
launchctl unload ~/Library/LaunchAgents/com.cryptolab.k5XX-YYY.plist
python3 scripts/k5XX_yyy_run.py --close "Week 4 D35 rollback"
python3 scripts/emergency_hl_exit.py --status
# Restore --dry-run in plist; reload paper mode
```

### HL Impact of Rollbacks

| Scenario | HL after | Note |
|----------|----------|------|
| All 3 PASS | 64.5% | Week 5 APT needs cap review |
| TIA rollback only | 64.5% | Unchanged (Bybit-only = 0pp) |
| K500 rollback | 61.5% | −3pp reclaimed |
| K500 + SEI rollback | 60.5% | Return to W3 state |
| All 3 rollback | 60.5% | K493 ATOM only |

---

## Phase 11: Profit Projection

### Week 4 Breakdown

| Strategy | @$10M | @$30M | @$100M |
|----------|-------|-------|--------|
| K500 INJ-BTC | $124K/yr | $372K/yr | $1.24M/yr |
| K507 SEI-BTC | $179K/yr | $537K/yr | $1.79M/yr |
| K507 TIA-BTC | $51K/yr | $153K/yr | $0.51M/yr |
| **W4 combined** | **$354K/yr** | **$1.06M/yr** | **$3.54M/yr** |

### Cumulative W1-W4

| AUM | /yr | Ann% (at $10M basis) |
|-----|-----|---------------------|
| $10M | **$861K/yr** | 8.61% |
| $30M | **$2.58M/yr** | — |
| $100M | **$8.61M/yr** | — |

### Full Family W1-W5 (inc. K512 APT)

| AUM | /yr |
|-----|-----|
| $10M | **$1,163K/yr** |
| $30M | **$3.49M/yr** |
| $100M | **$11.63M/yr** |

---

## Phase 12: Week 5 Prep — K512 APT-BTC (D+32)

| Attribute | Value |
|-----------|-------|
| OOS Sharpe | 51.10 (family #1 overall: APT > ATOM 50.79) |
| Ann return | $302K/yr @ $10M |
| Sleeve | 2% total (1% HL + 1% Bybit) |
| HL contribution | +1.0pp → 65.5% |
| **HL issue** | **Would breach 65% cap by 0.5pp** |

**K512 APT HL solutions (evaluate at D+32):**
1. K500 INJ at PASS → expand to 4% but migrate 0.5% from HL to Bybit (net 0pp HL change)
2. K280 further sleeve cut (micro-trim) to reclaim 1pp HL
3. K449 ETH-BTC: migrate 1% from HL to Bybit (reclaim 1pp)
4. Defer K512 until HL headroom created by organic rollback

**Prerequisite:** All 3 W4 strategies PASS/HOLD at D+35 gate before K512 scheduling.

```bash
# Week 5 prep review
python3 wave_k559_week4_triple_live.py --phase12
```

---

## Phase 13: User Checklist (D+21/23/25/28/35)

### D+21 (K500 INJ-BTC LIVE)

- [ ] Verify K493 W3 Sharpe ≥ 25 (PASS gate)
- [ ] K500 dashboard pre-flight — signal LONG_INJ_SHORT_BTC
- [ ] HL margin < 70% (headroom for +$300K margin)
- [ ] Edit K500 plist: remove `--dry-run`, set `PAPER_TRADE=False`
- [ ] `launchctl load ~/Library/LaunchAgents/com.cryptolab.k500-inj-btc.plist`
- [ ] Verify HL ≈ 63.5% (< 65% cap)
- [ ] Commit + push K500 plist

### D+23 (K507 SEI-BTC LIVE — 48h after K500)

- [ ] K500 48h health check: position_state != NEUTRAL, daily_pnl > 0
- [ ] HL margin < 75% (headroom for +$100K margin)
- [ ] Edit K507 SEI plist: `PAPER_TRADE=False`, `HL_SLEEVE=0.01`, `BYBIT_SLEEVE=0.01`
- [ ] `launchctl load ~/Library/LaunchAgents/com.cryptolab.k507-sei-btc.plist`
- [ ] Verify HL ≈ 64.5% (< 65% cap, 0.5pp headroom)
- [ ] Commit + push K507 SEI plist

### D+25 (K507 TIA-BTC LIVE — 48h after SEI)

- [ ] K507 SEI 48h health check: activity confirmed
- [ ] HL cap verify: must be ≤ 64.5% before TIA loads
- [ ] Edit TIA plist: `PAPER_TRADE=False`, `SMART_ROUTER=BYBIT_ONLY`, `HL_SLEEVE=0`, `BYBIT_SLEEVE=0.01`
- [ ] `launchctl load ~/Library/LaunchAgents/com.cryptolab.k507-tia-btc.plist`
- [ ] Final HL verify: still 64.5% (TIA adds 0pp HL)
- [ ] Commit + push TIA plist

### D+28 (First 7d Cross-Strategy Review)

- [ ] All 3 strategies showing daily_pnl > 0 (at least 1 fill cycle each)
- [ ] No margin breach on HL account
- [ ] Delta drift < 5% per strategy
- [ ] Cross-correlation check: positions not all identical direction
- [ ] Fill rate > 20% (early 7d window, signal-frequency dependent)

### D+35 (Decision Matrix)

- [ ] Per-strategy Sharpe evaluation: `python3 wave_k559_week4_triple_live.py --phase10`
- [ ] K500 INJ: ≥ 5.6 PASS / 3.4–5.6 HOLD / < 3.4 ROLLBACK
- [ ] K507 SEI: ≥ 24 PASS / 14–24 HOLD / < 14 ROLLBACK
- [ ] K507 TIA: ≥ 7 PASS / 4–7 HOLD / < 4 ROLLBACK
- [ ] Week 5 K512 APT go/no-go: HL cap review
- [ ] Commit D+35 status + push

---

## Risk Inventory

| ID | Risk | Severity | Mitigation |
|----|------|----------|-----------|
| R1 | Paper→LIVE Sharpe decay (20-30%) | HIGH | Post-only fill opt; 7d rolling gate; rollback thresholds set at 50% of OOS |
| R2 | HL cap breach if TIA goes HL-primary | HIGH | K559 resolution: TIA Bybit-only (0pp). Enforce via plist `SMART_ROUTER=BYBIT_ONLY` |
| R3 | SEI NEUTRAL signal at scaffold | MEDIUM | Signal is FR-dependent; activates when SEI FR > BTC FR. Monitor FR diff daily. |
| R4 | K507 TIA Bybit-only fill rate risk | MEDIUM | 1% sleeve × 4x = $400K notional. Bybit TIA perp ADV >$50M/d. Adequate. |
| R5 | Three-way correlation spike | MEDIUM | INJ DeFi-perp, SEI EVM, TIA modular DA — empirically orthogonal (G5d ATOM-TIA = 0.05) |
| R6 | HL margin cascade (K500 adds $300K) | HIGH | Emergency exit K500/INJ registered (K506). Margin utilisation checked at each step. |
| R7 | Bybit API rate limits (SEI+TIA) | LOW | 1% sleeve each. Bybit API limits > $10M notional/day. Not a constraint at this scale. |

---

## Architecture Summary (v6.28 after Week 4)

| Strategy | Sleeve | Venue | Sharpe | Ann. Return |
|----------|--------|-------|--------|-------------|
| K449 ETH-BTC | 5% | HL | 5.66 | $13K |
| K476 SOL-BTC | 4% | HL | 16.30 | $187K |
| K484 AVAX-BTC | 5% | HL | 43.89 | $76K |
| K493 ATOM-BTC | 5% | HL+Bybit | 50.79 | $231K |
| **K500 INJ-BTC** | **3%** | **HL** | **11.23** | **$124K** |
| **K507 SEI-BTC** | **2%** | **HL+Bybit** | **48.10** | **$179K** |
| **K507 TIA-BTC** | **1%** | **Bybit-only** | **14.44** | **$51K** |
| *K512 APT-BTC* | *2%* | *HL+Bybit* | *51.10* | *$302K* |
| K376 momentum | 8% | HL | — | $48K |
| K495 DEX-CEX | 6% | HL | — | $646K |
| K280 sleeve | 60% | HL | — | — |

**Post-W4 HL exposure:** 64.5% (cap 65%, 0.5pp headroom)  
**W1-W4 paired-trade family combined:** $861K/yr @ $10M

---

## Files

| File | Purpose |
|------|---------|
| `wave_k559_week4_triple_live.py` | Playbook script (13 phases, 600+ LOC, K339) |
| `wave_k559_week4_triple_live.json` | Machine-readable state export |
| `wave_k559_week4_triple_live.md` | This document |
| `docs/k302a_master_deployment.md` | Week 4 section appended |
| `report.html` | Badge prepended |
| `data/k500_dashboard.json` | K500 INJ scaffold state (K506) |
| `data/k507_dashboard.json` | K507 SEI scaffold state (K514) |
| `data/k507_tia_dashboard.json` | K507 TIA scaffold state (K524) |

---

*K559 Playbook — Generated 2026-05-30 06:25 JST*  
*K339 pattern: REPO_ROOT from __file__, no absolute paths, stdlib only*  
*LIVE 自動変更禁止 — manual activation required per checklist*

# K556 — K493 ATOM-BTC Week 3 LIVE Activation Playbook

**Wave:** K556 | **Generated:** 2026-05-30 06:07 JST | **Strategy:** K493 ATOM-BTC FR Differential (Family #1)

---

## Executive Summary

K493 ATOM-BTC is the **highest-Sharpe strategy** in the paired-trade family (OOS Sh 50.79), delivering **$231K/yr @ $10M AUM** with the Cosmos hypothesis fully confirmed (G5a = 0.1763, most orthogonal alt in family).

This wave delivers the **Week 3 LIVE activation playbook** in the K547 sequenced cascade:

| Cumulative | AUM Scale | Annual Profit |
|------------|-----------|--------------|
| Week 3 (K449+K476+K484+K493) | **$10M** | **$507K/yr** |
| Week 3 cumulative | **$30M** | **$1.52M/yr** |
| Week 3 cumulative | **$100M** | **$5.07M/yr** |

Post-activation HL exposure: **~60.5%** (cap 65%, 4.5pp headroom for Week 4).

---

## Sequenced Activation Context

```
Week 1: K449 ETH-BTC    ($13K/yr)           D0     ← K549 playbook
Week 2: K476 SOL-BTC    ($187K/yr)          D7-D14
        K484 AVAX-BTC   ($76K/yr)           D9-D14 (48h gap)
Week 3: K493 ATOM-BTC   ($231K/yr)          D14-D21 ← THIS WAVE
Week 4: K500 INJ-BTC    ($124K/yr)          D21-D35
        K507 SEI-BTC    ($179K/yr)          D23-D35
        K507 TIA-BTC    ($51K/yr)           D25-D35
Week 5: K512 APT-BTC    ($302K/yr)          D35-D60
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Full family (D60): $1,163K/yr @$10M | $3.49M @$30M | $11.63M @$100M
```

---

## Phase 1: K493 Scaffold State (as of K556)

| Parameter | Value |
|-----------|-------|
| Dashboard | `data/k493_dashboard.json` PRESENT |
| Daemon | `com.cryptolab.k493-atom-btc.plist` PRESENT (32nd daemon) |
| Script | `scripts/k493_atom_btc_run.py` PRESENT (~280 LOC) |
| Paper mode | `PAPER_TRADE=True` (default, flip at Week 3) |
| Current signal | `LONG_ATOM_SHORT_BTC` (already firing) |
| FR raw diff | -1.77e-5 (ATOM FR more negative than BTC FR → positive carry) |
| OOS Sharpe | 50.79 (#1 in family: ATOM > AVAX 43.89 > SOL 16.30 > ETH 5.66) |
| Paper days | 0.1/60 (D0 = 2026-05-30, paper gate ongoing) |
| Gate status | IN_PROGRESS |
| K499 deliverables | ALL COMPLETE (scaffold, plist, emergency exit, leverage manager) |

**Note:** Per K547, Week 3 activation assumes K449+K476+K484 (Weeks 1+2) PASS. The paper-trade gate is ongoing — K547 profit-max mandate authorizes activation when W1+W2 gates pass, not requiring the full 60d paper gate for K493 itself (same rationale as K449 Week 1).

---

## Phase 2: Pre-Requisite Checklist

Before Week 3 D0, verify all of the following:

### Required (Block activation if FAIL)

- [ ] **Week 1 K449 LIVE PASS** — 7d realized Sharpe ≥ 5, fill_rate ≥ 50%
  ```bash
  python3 scripts/k449_eth_btc_run.py --status
  cat data/k449_dashboard.json | python3 -c "import json,sys; d=json.load(sys.stdin); print(f'State={d[\"position_state\"]}, Paper={d[\"paper_trade_mode\"]}')"
  ```

- [ ] **Week 2 K476 SOL-BTC LIVE PASS** — positive PnL + fills confirmed
  ```bash
  cat data/k476_dashboard.json | python3 -c "import json,sys; d=json.load(sys.stdin); print(f'State={d.get(\"position_state\",\"?\")}, Paper={d.get(\"paper_trade_mode\",True)}')"
  ```

- [ ] **Week 2 K484 AVAX-BTC LIVE PASS** — positive PnL + fills confirmed
  ```bash
  cat data/k484_dashboard.json | python3 -c "import json,sys; d=json.load(sys.stdin); print(f'State={d.get(\"position_state\",\"?\")}, Paper={d.get(\"paper_trade_mode\",True)}')"
  ```

- [ ] **HL exposure < 65%** before K493 addition
  ```bash
  python3 scripts/verify_deployment_status.py
  # Check hl_exposure_pct — must be < 62.5% to safely add K493 (+2.5pp)
  ```

- [ ] **K280 sleeve at 60%** (K539 Phase B1 / K552)
  ```bash
  grep '"K280"' scripts/leverage_manager.py
  # Expected: "K280":   0.60,
  ```

### Check (Non-blocking, monitor)

- [ ] **K498 Phase 1A active** (BBO_SELECT smart router + OKX daemon)
  ```bash
  launchctl list | grep okx
  ```

---

## Phase 3: LIVE Switch Concrete Steps (Week 3 D0 — ~20 min)

### Sizing

```
Sleeve:      5% × $10M AUM = $500K capital
Leverage:    4x → $2M total notional
HL leg:      60% = $1.2M notional ($300K margin) — ATOM long + BTC short primary
Bybit leg:   40% = $0.8M notional ($200K margin) — secondary for cap management
HL delta:    +2.5pp (5% × 50% HL fraction)
Post-K493:   ~60.5% HL vs 65% cap (4.5pp headroom)
```

### Step-by-Step

**Step 1 (2 min): Verify K280 @ 60%**
```bash
grep '"K280"' scripts/leverage_manager.py
# Expected: "K280":   0.60,
```

**Step 2 (2 min): Verify W1+W2 LIVE**
```bash
python3 scripts/k449_eth_btc_run.py --status
# paper_trade_mode must be false
```

**Step 3 (2 min): HL margin health check**
```bash
python3 scripts/emergency_hl_exit.py --dry-run --status
# Margin utilisation must be < 70%
```

**Step 4 (2 min): Remove --dry-run from K493 plist**
```bash
sed -i '' '/<string>--dry-run<\/string>/d' com.cryptolab.k493-atom-btc.plist
grep 'dry-run' com.cryptolab.k493-atom-btc.plist || echo 'CLEAN'
```

**Step 5 (1 min): Set PAPER_TRADE=False in plist env**
```bash
# Edit com.cryptolab.k493-atom-btc.plist:
# Change: <string>True</string>  (under PAPER_TRADE key)
# To:     <string>False</string>
grep PAPER_TRADE com.cryptolab.k493-atom-btc.plist
```

**Step 6 (1 min): Copy to LaunchAgents**
```bash
cp com.cryptolab.k493-atom-btc.plist \
   ~/Library/LaunchAgents/com.cryptolab.k493-atom-btc.plist
```

**Step 7 (1 min): USER ACTION #34 — Load K493 daemon**
```bash
launchctl load ~/Library/LaunchAgents/com.cryptolab.k493-atom-btc.plist
launchctl list | grep k493-atom-btc
# Expected: PID entry visible
```

**Step 8 (1 min): Confirm K357 emergency exit includes K493**
```bash
grep -c 'K493\|ATOM' scripts/emergency_hl_exit.py
# Expected: >= 3 (K499 scaffold already implemented)
```

**Step 9 (2 min): K493 status check**
```bash
python3 scripts/k493_atom_btc_run.py --status
# Expected: position_state=LONG_ATOM_SHORT_BTC (signal already firing)
```

**Step 10 (3 min): Commit + push**
```bash
git add com.cryptolab.k493-atom-btc.plist
git commit -m "K556 K493 ATOM-BTC Week 3 LIVE activation (Sh50.79, $231K/yr, HL 60.5%)"
git push origin main
```

---

## Phase 4: Day 21-28 Monitoring (Week 3)

### Daily check (run every day after activation)

```bash
python3 scripts/k493_atom_btc_run.py --status && \
cat data/k493_dashboard.json | python3 -c "
import json, sys; d = json.load(sys.stdin)
g = d.get('gate_metrics', {})
print(f'State:    {d[\"position_state\"]}')
print(f'PnL/day:  \${d[\"daily_pnl_usdc\"]:.2f}  (target: \$633/day)')
print(f'Sharpe:   {d[\"60d_sharpe\"]:.2f}  (D28 target: ≥25)')
print(f'Fill:     {g.get(\"current_fill_rate\",0):.1%}  (target: ≥65%)')
print(f'Drift:    {d[\"delta_neutral_drift_pct\"]:.3%}  (alert: >5%)')
print(f'FR diff:  {d[\"fr_raw_diff\"]:.6f}  (positive = ATOM carry)')
print(f'Gate:     {g.get(\"gate_status\",\"UNKNOWN\")}')
"
```

### Daily targets

| Metric | Target | Alert | Kill |
|--------|--------|-------|------|
| Daily PnL | $633/day | <$0 3 days straight | <-$2K/day |
| Realized Sharpe | ≥ 25 by D28 | 15-25 | < 15 |
| Fill rate (paired) | ≥ 65% | 50-65% | < 50% |
| HL margin util | < 70% | 70-80% | > 80% |
| Delta drift | < 5% | 5-10% | > 10% |
| FR diff (ATOM-BTC) | < 0 (ATOM pay less) | approach 0 | > 0 (reverse signal) |

### Funding rate carry check

```bash
cat data/k493_dashboard.json | python3 -c "
import json, sys; d = json.load(sys.stdin)
atom_fr = d.get('fr_atom_current', 0)
btc_fr  = d.get('fr_btc_current', 0)
diff    = d.get('fr_raw_diff', 0)
print(f'ATOM FR:  {atom_fr:.6f}  (\"+\" = longs pay shorts)')
print(f'BTC FR:   {btc_fr:.6f}')
print(f'Diff:     {diff:.6f}  (\"-\" = ATOM cheaper to hold long vs BTC short)')
print(f'Signal:   {\"LONG_ATOM_SHORT_BTC\" if diff < -1e-5 else \"NEUTRAL\" if abs(diff) < 1e-5 else \"LONG_BTC_SHORT_ATOM\"}')"
```

### Cross-venue sync check (if Bybit split active)

```bash
# Verify both legs open (no uncovered position)
python3 scripts/k493_atom_btc_run.py --status
launchctl list | grep k493

# If Bybit leg not synced:
# python3 scripts/k493_atom_btc_run.py --close "cross-venue desync"
# Then reload and re-enter after investigation
```

---

## Phase 5: Decision Matrix — Week 3 + 7 Days (D28)

| Decision | Realized Sharpe | Fill Rate | Additional Criteria | Action |
|----------|----------------|-----------|---------------------|--------|
| **PASS** | ≥ 25 | ≥ 65% | No margin alert | Expand to 8% sleeve → Week 4 |
| **HOLD** | 15-25 | 50-65% | No kill criteria | Maintain 5%; re-evaluate D35 |
| **ROLLBACK** | < 15 | < 50% or margin > 80% | Any | Close legs; reload paper |

**Important context:** OOS Sharpe 50.79 → live est ~35.55 (20-30% decay). The D28 PASS threshold of ≥25 is set at 50% of OOS to account for slippage + fee drag. Even at realized Sh 25, K493 remains the highest live Sharpe in the paired-trade family.

### PASS scenario: Expand to 8%

```bash
# 1. Edit plist: increase sleeve_pct to 0.08
# 2. Reload daemon
launchctl unload ~/Library/LaunchAgents/com.cryptolab.k493-atom-btc.plist
launchctl load ~/Library/LaunchAgents/com.cryptolab.k493-atom-btc.plist
# 3. Verify new notional: 8% × $10M × 4x = $3.2M (vs $2M initial)
```

### ROLLBACK procedure

```bash
# Step 1: Unload daemon
launchctl unload ~/Library/LaunchAgents/com.cryptolab.k493-atom-btc.plist

# Step 2: Close all positions
python3 scripts/k493_atom_btc_run.py --close "Week 3 rollback — Sharpe below threshold"

# Step 3: Verify positions closed
python3 scripts/emergency_hl_exit.py --status

# Step 4: Restore paper mode in plist
sed -i '' 's/<string>False<\/string>/<string>True<\/string>/' com.cryptolab.k493-atom-btc.plist
# Add --dry-run back to ProgramArguments

# Step 5: Reload in paper mode
cp com.cryptolab.k493-atom-btc.plist ~/Library/LaunchAgents/
launchctl load ~/Library/LaunchAgents/com.cryptolab.k493-atom-btc.plist
```

---

## Phase 6: HL Exposure Post-Week 3

### Trajectory

| Event | HL% | Delta | Status |
|-------|-----|-------|--------|
| v6.13d baseline | 65.0% | — | AT CAP |
| K280 Phase B1 (75→60%) | 57.5% | −7.5pp | SAFE |
| + K449 ETH-BTC (5%, HL-only) | 62.5% | +5.0pp | SAFE |
| + K476 SOL-BTC (2% HL + 1% Bybit) | 64.5% | +2.0pp | SAFE |
| + K484 AVAX-BTC (K280 micro-trim + 2% HL) | 60.5% | −4.0pp/+2.0pp | SAFE |
| **+ K493 ATOM-BTC (2.5% HL + 2.5% Bybit)** | **60.5%** | **+2.5pp** | **SAFE** |
| Week 4 headroom | — | 4.5pp remaining | — |

### Split protocol (K493)

K493 uses a **HL-primary + Bybit-secondary split** to stay under the 65% HL cap:
- HyperLiquid: 60% of notional ($1.2M of $2M) → primary execution (ATOM + BTC perps)
- Bybit: 40% of notional ($0.8M of $2M) → secondary for overflow
- Net HL addition: +2.5pp (vs +5pp if pure HL)

This split gives Week 4 (K500+K507) the 4.5pp headroom they need to activate at full sizing.

---

## Phase 7: Profit Projection

### K493 standalone

| AUM Scale | Annual Profit | Notes |
|-----------|--------------|-------|
| **$10M** | **$231,000/yr** | 3% sleeve (K499 spec); 5% initial Week 3 |
| **$30M** | **$693,000/yr** | Linear scaling; HL liquidity ceiling ~$30M effective |
| **$100M** | **$2,310,000/yr** | Subject to HL perp depth for ATOM-BTC at large size |

### Cumulative W1-W3 combined

| Strategy | W1-W3 Contribution | @ $10M | @ $30M | @ $100M |
|----------|-------------------|--------|--------|---------|
| K449 ETH-BTC | Week 1 | $13K | $39K | $130K |
| K476 SOL-BTC | Week 2 | $187K | $561K | $1.87M |
| K484 AVAX-BTC | Week 2 | $76K | $228K | $760K |
| **K493 ATOM-BTC** | **Week 3** | **$231K** | **$693K** | **$2.31M** |
| **TOTAL W3** | | **$507K/yr** | **$1.52M/yr** | **$5.07M/yr** |

### Full family pipeline (W1-W5)

| Week | Cumulative |  @ $10M | @ $30M | @ $100M |
|------|------------|---------|--------|---------|
| W3 (this wave) | K449+K476+K484+K493 | $507K | $1.52M | $5.07M |
| W4 | +K500+K507 SEI+K507 TIA | $861K | $2.58M | $8.61M |
| W5 | +K512 APT | $1,163K | $3.49M | $11.63M |

---

## Phase 8: Risk Inventory

| Risk | Severity | Probability | Mitigation |
|------|----------|-------------|------------|
| Paper→LIVE Sharpe divergence | HIGH | MEDIUM | 20-30% decay expected; D28 gate @ Sh≥25 (50% of OOS) |
| HL+Bybit cross-venue desync | MEDIUM | LOW | K439 5s rollback; daily sync check |
| Cosmos hypothesis decay | MEDIUM | LOW | Monitor ATOM staking yield vs BTC FR monthly |
| BTC flash crash correlated tail | HIGH | LOW | K357 registered; delta-neutral absorbs price; tail 1.7-4.0% |
| HL cap breach during W3 | HIGH | LOW | Pre-check HL%; use Bybit split; 65% hard cap enforced |
| G6 low frequency (18.2/yr) | LOW | CERTAIN | Accepted at 5% sleeve; monitor signal count vs 18.2 expected |

### Cosmos hypothesis (ATOM-specific)

ATOM FR differential is driven by:
1. **IBC network flows** — interchain transfers affect perp funding rates
2. **Staking yield competition** — ATOM ~15-20% APY vs BTC ~0% → perp longs pay premium
3. **Governance cycles** — voting lockups create temporary supply pressure

The G5a correlation of 0.1763 (vs AVAX 0.300, SOL 0.253) confirms ATOM is the most orthogonal paired-trade asset — key to portfolio-level Sharpe enhancement.

---

## Phase 9: User Action #34 Checklist (Week 3 D0 — ~20 min)

```
[ ] 1. K547 Week 2 PASS verification (2 min)
       cat data/k476_dashboard.json && cat data/k484_dashboard.json
       → Both paper_trade_mode=false

[ ] 2. K493 dashboard health check (2 min)
       python3 scripts/k493_atom_btc_run.py --status
       → gate_status=IN_PROGRESS, signal=LONG_ATOM_SHORT_BTC

[ ] 3. HL margin pre-check (2 min)
       python3 scripts/emergency_hl_exit.py --dry-run --status
       → margin utilisation < 70%

[ ] 4. Edit plist: remove --dry-run, PAPER_TRADE=False (3 min)
       sed -i '' '/<string>--dry-run<\/string>/d' com.cryptolab.k493-atom-btc.plist

[ ] 5. Copy plist + launchctl load (2 min)
       cp com.cryptolab.k493-atom-btc.plist ~/Library/LaunchAgents/
       launchctl load ~/Library/LaunchAgents/com.cryptolab.k493-atom-btc.plist
       launchctl list | grep k493-atom-btc   ← must show PID

[ ] 6. Confirm K357 K493 registered (1 min)
       grep -c 'K493\|ATOM' scripts/emergency_hl_exit.py   ← >= 3

[ ] 7. Schedule D28 decision review (calendar: 2026-06-27)

[ ] 8. Commit + push (3 min)
       git add com.cryptolab.k493-atom-btc.plist
       git commit -m "K556 K493 ATOM-BTC Week 3 LIVE (Sh50.79, $231K/yr, HL 60.5%)"
       git push origin main

[ ] 9. Begin Week 4 prep (K500 INJ, 5 min)
       python3 wave_k556_k493_week3_live.py --phase10
```

---

## Phase 10: Week 4 Prep (K500 INJ + K507 SEI + K507 TIA)

Activate only after K493 D28 PASS (Sharpe ≥ 25).

### Activation sequence (stagger 48h each)

| Strategy | Timing | Sleeve | HL Add | Ann. Return |
|----------|--------|--------|--------|-------------|
| K500 INJ-BTC | D21 (K493 PASS) | 2% HL + 1% Bybit | +2.0pp | $124K/yr |
| K507 SEI-BTC | D23 (+48h) | 1.5% HL + 1.5% Bybit | +1.5pp | $179K/yr |
| K507 TIA-BTC | D25 (+48h) | 1% HL | +1.0pp | $51K/yr |

```bash
# K500 INJ-BTC activation (D21)
# 1. Remove --dry-run from com.cryptolab.k500-inj-btc.plist
# 2. Set PAPER_TRADE=False
# 3. Copy + load:
cp com.cryptolab.k500-inj-btc.plist ~/Library/LaunchAgents/
launchctl load ~/Library/LaunchAgents/com.cryptolab.k500-inj-btc.plist
launchctl list | grep k500
```

### Week 4 HL trajectory

```
Post-W3:   60.5%   (K493 activated)
+ K500:    62.5%   (+2pp INJ HL fraction)
+ K507 SEI:64.0%   (+1.5pp SEI HL fraction)
+ K507 TIA:65.0%   (+1.0pp TIA HL) ← AT CAP — no more room
```

**Week 4 adds $354K/yr → cumulative $861K/yr @ $10M.**

### Decision tree

```
K493 D28 PASS (Sh ≥ 25) ──→ K500 activate D21 → SEI D23 → TIA D25
K493 D28 HOLD (Sh 15-25) ─→ K500 deferred to D35; re-evaluate
K493 D28 ROLLBACK (Sh<15) → Week 4 cascade PAUSED; K493 returns to paper
```

---

## Quick Reference

```bash
# Full playbook
python3 wave_k556_k493_week3_live.py --all

# Status only
python3 wave_k556_k493_week3_live.py --status

# D0 checklist only
python3 wave_k556_k493_week3_live.py --checklist

# Decision matrix
python3 wave_k556_k493_week3_live.py --phase5

# Week 4 prep
python3 wave_k556_k493_week3_live.py --phase10

# Export machine-readable JSON
python3 wave_k556_k493_week3_live.py --export-json
```

---

## Key Files

| File | Purpose |
|------|---------|
| `wave_k556_k493_week3_live.py` | Playbook executor (this wave) |
| `wave_k556_k493_week3_live.json` | Machine-readable output |
| `wave_k556_k493_week3_live.md` | This document |
| `scripts/k493_atom_btc_run.py` | Production strategy script (32nd daemon) |
| `com.cryptolab.k493-atom-btc.plist` | Daemon plist (edit for LIVE) |
| `data/k493_dashboard.json` | Live paper/live state dashboard |
| `docs/k302a_master_deployment.md` | User Action #34 (this appendix) |
| `scripts/emergency_hl_exit.py` | K357 exit (K493 registered) |

---

## Reference

| Wave | Purpose |
|------|---------|
| K493 | ATOM-BTC FR differential strategy (§6 evaluation) |
| K499 | K493 production scaffold |
| K547 | Paired-trade family health audit + activation sequence |
| K549 | Week 1 K449 LIVE activation playbook |
| K556 | **This wave** — Week 3 K493 LIVE activation playbook |
| K339 | REPO_ROOT from `__file__` security pattern |
| K357 | Emergency HL exit (K493 registered) |
| K434 | HL smart router Phase 2 |
| K439 | POST_ONLY parallel execution pattern |

---

*K556 | 2026-05-30 06:07 JST | K493 ATOM-BTC Week 3 LIVE Prep | Family #1 $231K/yr | Cumulative $507K/yr @$10M*

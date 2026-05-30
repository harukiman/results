# K705 — D60 Cascade Activation Playbook

**Wave:** K705 | **Parent:** K700 v6.50 MEGA | **Updated:** 2026-05-30 16:00 JST
**Gate Date:** 2026-07-29 | **Scaffolds:** 14 | **Cumulative Unlock:** +$1,642,745/yr @$10M AUM
**Constraint:** LIVE 自動変更禁止 — manual execution only | **K339 pattern**

---

## Executive Summary

K700 confirmed 14 scaffolds entering 60d paper gate on 2026-05-30. All 14 pass §6 gates with OOS Sharpe ranging from 9.65 (K684 SOL-INJ) to 50.27 (K686 AVAX-SOL). Cascade activates 2026-07-29, spread over 5 days (max 3/day) in descending Sharpe order. Cumulative unlock is $1,642,745/yr on top of the $288K/yr already active baseline, totaling $1,930,745/yr @$10M AUM.

**Critical HL gate:** Only K658 SOL-ETH (+1.5pp) and K629 WLD-ETH (+2.0pp) add HL exposure. K629 is **conditional** on K552 prereq (HL 75%→60% baseline reduction) being applied first. Without K552, K629 would push HL to 67% — over the 65% cap.

---

## Phase 1 — Scaffold Inventory (Sharpe DESC)

| Rank | Scaffold | Strategy | Pair | Family | OOS Sh | Gate Sh | Ann $10M | HL Δ | Day |
|------|----------|----------|------|--------|--------|---------|----------|------|-----|
| 1 | K689 | K686 | AVAX-SOL | alt-alt | 50.27 | 5.0 | $102,153 | 0.0pp | D+0 |
| 2 | K685 | K682 | ATOM-SOL | alt-alt | 43.43 | 5.0 | $214,638 | 0.0pp | D+0 |
| 3 | K637 | K628 | JTO-BTC (orthog) | orthog | 44.63 | 8.0 | $357,026 | 0.0pp | D+0 |
| 4 | K683 | K679 | APT-SOL | alt-alt | 39.29 | 5.0 | $234,781 | 0.0pp | D+1 |
| 5 | K669 | K658 | SOL-ETH | eth-base | 29.66 | 5.0 | $42,332 | +1.5pp | D+1 |
| 6 | K699 | K696 | ENA-SOL | alt-alt | 26.93 | 5.0 | $93,187 | 0.0pp | D+1 |
| 7 | K693 | K690 | SEI-SOL | alt-alt | 25.11 | 5.0 | $104,774 | 0.0pp | D+2 |
| 8 | K652 | K648 | POL-BTC (orthog) | orthog | 23.41 | 12.0 | $85,864 | 0.0pp | D+2 |
| 9 | K653 | K647 | DOT-BTC (orthog) | orthog | 23.25 | 12.0 | $80,460 | 0.0pp | D+2 |
| 10 | K668 | K663 | TIA-ETH | eth-base | 22.0 | 5.0 | $36,000 | 0.0pp | D+3 |
| 11 | K654 | K629 | WLD-ETH | eth-base | 19.9 | 5.0 | $94,210 | +2.0pp | D+3 **COND** |
| 12 | K697 | K694 | TIA-SOL | alt-alt | 19.09 | 5.0 | $58,354 | 0.0pp | D+3 |
| 13 | K701 | K698 | LINK-ETH | oracle | 12.07 | 5.0 | $24,650 | 0.0pp | D+4 |
| 14 | K687 | K684 | SOL-INJ | alt-alt | 9.65 | 5.0 | $114,316 | 0.0pp | D+4 |
| **TOTAL** | | | | | | | **$1,642,745** | **+3.5pp** | |

Paper start: 2026-05-30 | Gate date: 2026-07-29 | Duration: 60 days

---

## Phase 2 — Per-Scaffold Activation Checklist

**Gate conditions (all strategies):**
- Realized Sharpe >= gate threshold (see table) over 60d paper period
- Fill rate >= 60%
- Max drawdown < 20%
- PnL correlation vs nearest neighbor < 0.40

**Activation steps (per scaffold):**
1. `VERIFY`: `python3 scripts/verify_deployment_status.py --check <strategy_wave>`
2. `GATE CHECK`: Confirm realized Sh >= threshold, fill >= 60%, maxDD < 20%
3. `HL CHECK`: For K658/K629 only — verify HL% <= (65% - delta_pp) before load
4. `LIVE SWITCH`: `launchctl load ~/Library/LaunchAgents/<plist>`
5. `CONFIRM`: `launchctl list | grep <daemon_name>` (expect PID non-zero)
6. `MONITOR`: Check dashboard JSON + logs for 7 days
7. `ROLLBACK TRIGGER`: Realized Sh < 50% of gate OR maxDD > 15% within 7d

**Sleeve weight init:**
- Bybit-only: full sleeve from day 1 (paper weights = live weights)
- HL strategies (K658, K629): 50% sleeve for first 7d, then full sleeve

**Rollback command template:**
```bash
launchctl unload ~/Library/LaunchAgents/<plist>
echo "ROLLED BACK: <strategy> $(date)" >> /Users/nekonaomichi/crypto-lab/data/rollback_log.txt
```

---

## Phase 3 — Sequential Activation Timing

14 scaffolds spread over **5 days** (Jul 29 – Aug 2). Max 3/day. Sharpe-descending order.

| Day | Date | Activations | Ann $10M/day | Cum $10M | HL% |
|-----|------|-------------|-------------|----------|-----|
| D+0 | 2026-07-29 | K686 AVAX-SOL, K682 ATOM-SOL, K628 JTO | $673,817 | $673,817 | 63.5% |
| D+1 | 2026-07-30 | K679 APT-SOL, K658 SOL-ETH, K696 ENA-SOL | $370,300 | $1,044,117 | 65.0% AT CAP |
| D+2 | 2026-07-31 | K690 SEI-SOL, K648 POL, K647 DOT | $271,098 | $1,315,215 | 65.0% |
| D+3 | 2026-08-01 | K663 TIA-ETH, K629 WLD-ETH (COND), K694 TIA-SOL | $188,564 | $1,503,779 | 65.0% (if K629 deferred) |
| D+4 | 2026-08-02 | K698 LINK-ETH, K684 SOL-INJ | $138,966 | $1,642,745 | 65.0% |

**Rule:** 24h monitoring window between daily batches. Stop cascade if any rollback triggers within 24h of activation.

---

## Phase 4 — HL Trajectory Check

**Baseline:** 63.5% (K700 v6.50) | **Cap:** 65.0% | **K552 effect:** -2.0pp

| Step | Strategy | Pair | HL Delta | HL After | Headroom | Status |
|------|----------|------|----------|----------|----------|--------|
| 0 | BASELINE | K700 v6.50 | — | 63.5% | +1.5pp | OK |
| 1-3 | K686/K682/K628 | Bybit-only | +0.0pp | 63.5% | +1.5pp | OK |
| 4 | K679 | APT-SOL Bybit | +0.0pp | 63.5% | +1.5pp | OK |
| 5 | K658 | SOL-ETH HL | **+1.5pp** | 65.0% | 0.0pp | **AT CAP** |
| 6-10 | K696/K690/K648/K647/K663 | Bybit-only | +0.0pp | 65.0% | 0.0pp | AT CAP |
| 11 | K629 | WLD-ETH HL | **+2.0pp** | **67.0%** | -2.0pp | **FAIL — OVER CAP** |

**Resolution:**
- K552 (K280 75%→60%) reduces HL baseline from 63.5% to **61.5%** (-2pp)
- With K552 applied: K658 pushes to 63.0%, K629 pushes to 65.0% = exactly at cap, PASS
- **Hard stop: Do NOT load K629 WLD-ETH if HL >= 63.0% at activation time**

**HL-zero strategies (12 of 14):** All 10 orthog + 7 alt-alt = zero HL impact. Activate freely.

---

## Phase 5 — Cumulative Profit Unlock

**Baseline (already active):** $288,000/yr (K280 $210K + K297 $50K + stables $28K)

| Day | Date | Strategies | New $/yr | Cumulative | $/day |
|-----|------|------------|----------|------------|-------|
| D+0 | Jul 29 | K686+K682+K628 | +$673,817 | $673,817 | $1,846 |
| D+1 | Jul 30 | K679+K658+K696 | +$370,300 | $1,044,117 | $2,861 |
| D+2 | Jul 31 | K690+K648+K647 | +$271,098 | $1,315,215 | $3,603 |
| D+3 | Aug 1 | K663+K629+K694 | +$188,564 | $1,503,779 | $4,120 |
| D+4 | Aug 2 | K698+K684 | +$138,966 | $1,642,745 | $4,501 |

**Total cascade unlock:** $1,642,745/yr  
**Total incl. baseline:** $1,930,745/yr @$10M AUM  
**If K629 deferred:** $1,548,535/yr (excl. $94K WLD-ETH)

**Top contributors:**
1. K628 JTO orthog: $357,026/yr (21.7%)
2. K679 APT-SOL: $234,781/yr (14.3%)
3. K682 ATOM-SOL: $214,638/yr (13.1%)
4. K684 SOL-INJ: $114,316/yr (7.0%)
5. K690 SEI-SOL: $104,774/yr (6.4%)

---

## Phase 6 — Risk + Rollback Playbook

### Individual Rollback Triggers
Any strategy meeting ANY condition within 7d of activation:
1. Realized Sharpe < 50% of OOS gate threshold
2. Max drawdown > 15% in any 7d window
3. Fill rate < 40%
4. PnL correlation vs nearest neighbor > 0.70
5. HL% breach > 65% (immediate unload)

### Cascade Failure Prevention
- Max 3 activations/day
- 24h monitoring window between batches
- **STOP cascade** if any rollback triggers within 24h of activation
- Resume only after root-cause analysis
- Governance wave within 14d of completion

### Emergency Exit (Portfolio-level)
**Trigger:** HL margin util > 80% OR combined maxDD > 25% in 48h
```bash
python3 scripts/emergency_hl_exit.py \
  --include-k628 --include-alt-alts --include-eth-base
```

### Rollback Commands
```bash
launchctl unload ~/Library/LaunchAgents/com.cryptolab.k686-avax-sol.plist   # K686 AVAX-SOL
launchctl unload ~/Library/LaunchAgents/com.cryptolab.k682-atom-sol.plist   # K682 ATOM-SOL
launchctl unload ~/Library/LaunchAgents/com.cryptolab.k628-jto-orthog.plist # K628 JTO
launchctl unload ~/Library/LaunchAgents/com.cryptolab.k679-apt-sol.plist    # K679 APT-SOL
launchctl unload ~/Library/LaunchAgents/com.cryptolab.k658-sol-eth.plist    # K658 SOL-ETH
launchctl unload ~/Library/LaunchAgents/com.cryptolab.k696-ena-sol.plist    # K696 ENA-SOL
launchctl unload ~/Library/LaunchAgents/com.cryptolab.k690-sei-sol.plist    # K690 SEI-SOL
launchctl unload ~/Library/LaunchAgents/com.cryptolab.k648-pol-orthog.plist # K648 POL
launchctl unload ~/Library/LaunchAgents/com.cryptolab.k647-dot-orthog.plist # K647 DOT
launchctl unload ~/Library/LaunchAgents/com.cryptolab.k663-tia-eth.plist    # K663 TIA-ETH
launchctl unload ~/Library/LaunchAgents/com.cryptolab.k629-wld-eth.plist    # K629 WLD-ETH
launchctl unload ~/Library/LaunchAgents/com.cryptolab.k694-tia-sol.plist    # K694 TIA-SOL
launchctl unload ~/Library/LaunchAgents/com.cryptolab.k698-link-eth.plist   # K698 LINK-ETH
launchctl unload ~/Library/LaunchAgents/com.cryptolab.k684-sol-inj.plist    # K684 SOL-INJ
```

---

## Phase 7 — User Action Timeline

### D-7 (2026-07-22): Pre-Flight Check
```bash
python3 scripts/verify_deployment_status.py --full-audit
# Pull 60d paper performance for all 14 scaffolds
# Verify HL% baseline (target <= 61.5% post-K552)
# Confirm K552 applied (PREREQ for K658 SOL-ETH, K629 WLD-ETH)
# Confirm K485 Bybit sub-account isolation complete
# Confirm no open incidents in prior 7d
# USER GO/NO-GO DECISION
```

### D-1 (2026-07-28): Final Review
```bash
# Final realized Sh check — all 14 must pass gate threshold
# Snapshot HL% baseline
# ls ~/Library/LaunchAgents/com.cryptolab.k6*.plist  # confirm 14 plist files
# Confirm cascade day schedule
```

### D+0 (2026-07-29): CASCADE BEGIN
```bash
# Highest Sharpe first — all Bybit, zero HL impact
launchctl load ~/Library/LaunchAgents/com.cryptolab.k686-avax-sol.plist    # Sh=50.27 $102K/yr FIRST
launchctl load ~/Library/LaunchAgents/com.cryptolab.k682-atom-sol.plist    # Sh=43.43 $215K/yr
launchctl load ~/Library/LaunchAgents/com.cryptolab.k628-jto-orthog.plist  # Sh=44.63 $357K/yr
# Verify: launchctl list | grep 'k686\|k682\|k628'
# Expected: $1,846/day new unlock
```

### D+1 (2026-07-30): HL check before K658
```bash
# PREREQ: verify HL% <= 63.5% before loading k658-sol-eth
launchctl load ~/Library/LaunchAgents/com.cryptolab.k679-apt-sol.plist     # Sh=39.29 $235K/yr
launchctl load ~/Library/LaunchAgents/com.cryptolab.k658-sol-eth.plist     # Sh=29.66 +1.5pp HL
launchctl load ~/Library/LaunchAgents/com.cryptolab.k696-ena-sol.plist     # Sh=26.93 $93K/yr
# HL check after K658: HL% should be <= 65.0%
# Expected: $2,861/day cumulative
```

### D+2 (2026-07-31): Bybit-only batch
```bash
launchctl load ~/Library/LaunchAgents/com.cryptolab.k690-sei-sol.plist     # Sh=25.11 $105K/yr
launchctl load ~/Library/LaunchAgents/com.cryptolab.k648-pol-orthog.plist  # Sh=23.41 $86K/yr
launchctl load ~/Library/LaunchAgents/com.cryptolab.k647-dot-orthog.plist  # Sh=23.25 $80K/yr
# Expected: $3,603/day cumulative
```

### D+3 (2026-08-01): K629 CONDITIONAL
```bash
launchctl load ~/Library/LaunchAgents/com.cryptolab.k663-tia-eth.plist     # Sh=22.0 (Bybit)
# K629 CONDITIONAL: DO NOT load if HL >= 63.0%
# launchctl load ~/Library/LaunchAgents/com.cryptolab.k629-wld-eth.plist   # +2.0pp HL VERIFY FIRST
launchctl load ~/Library/LaunchAgents/com.cryptolab.k694-tia-sol.plist     # Sh=19.09 (Bybit)
# Expected: $4,120/day cumulative
```

### D+4 (2026-08-02): Final batch
```bash
launchctl load ~/Library/LaunchAgents/com.cryptolab.k698-link-eth.plist    # Sh=12.07 (Bybit)
launchctl load ~/Library/LaunchAgents/com.cryptolab.k684-sol-inj.plist     # Sh=9.65 (Bybit) LAST
# CASCADE COMPLETE
# Total daily rate: $4,501/day (14 strategies live)
```

### D+5 to D+14: Post-Activation Monitor
```bash
# Daily: check all dashboard JSONs
# Daily: verify HL% snapshot
# Day 7: governance wave — correlation drift audit
# Day 14: file K706 post-activation monitoring report
```

---

## Phase 8 — Memory + Summary

**K705 Key Lessons:**
1. K629 WLD-ETH (+2pp HL) is the critical bottleneck — defer until K552 confirmed
2. Bybit-only strategies (12 of 14) = zero HL impact, activate freely
3. D60 gate threshold varies: Sh>=8 (K628), Sh>=12 (K648/K647), Sh>=5 (alt-alts)
4. Cascade order = Sharpe DESC for maximum early alpha capture
5. K552 prereq MUST precede D+1 K658 SOL-ETH activation

**Next Waves:**
- K706: 7-day post-activation monitoring report
- K707: WLD-SOL eval (K703 result) — potential 8th alt-alt candidate
- K708: D30 audit (2026-06-29) — paired-trade BTC-base rollout check

---

*K705 | K339 REPO_ROOT | 2026-05-30 | v1.0*

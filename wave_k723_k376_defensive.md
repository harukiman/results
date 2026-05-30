# K723 — K376 INDETERMINATE Defensive Update Playbook

**Wave:** K723  
**Mission:** K376 BULL ETA INDETERMINATE — defensive priority shift, K722 reconciliation follow-up  
**Timestamp:** 2026-05-30 17:26 JST  
**Pattern:** K339 REPO_ROOT  
**Files:** `wave_k723_k376_defensive.{py,json,md}`

---

## Executive Summary

K722 established that K376 BULL ETA is **INDETERMINATE** (not 14d, not 622d):
- K497 authoritative slope: **-72.36 USD/day** (worsening at -28.1/day)
- BULL_CONFIRMED requires slope >= 0 for 7 consecutive calendar days
- At current trajectory, no ETA projection is meaningful until BTC recovers above ~$78K

**Defensive posture shift (K723):**
- K552 + K492-C elevated to **PRIMARY** (was secondary to K376)
- K498 Phase 1A and K449 LIVE prioritized
- K376 Phase B: **INDEFINITELY DEFERRED** — K497 daemon auto-monitors
- $4.3M activation available without K376 (vs $4.5M with), delta = **-$200K**

---

## Phase 1: Profit Impact Reassessment

### v6.50 Mid Context

| Metric | With K376 | Without K376 | Delta |
|--------|-----------|--------------|-------|
| Portfolio mid/yr @$10M | $21.1M | $20.85M | -$247K |
| Phase A immediate | $566K/yr | $566K/yr | 0 (unchanged) |
| D60 cascade | $1.643M/yr | $1.643M/yr | 0 (unaffected) |
| K376 contribution | $247K/yr (3%) | $0 | -$247K |
| Combined activation @$10M | $4.5M/yr | $4.3M/yr | **-$200K** |

### K376 Delay Cost

- **$677/day** in foregone K376 profit during INDETERMINATE period
- Phase A ($566K) and D60 cascade ($1.643M) are **fully independent** of K376 regime
- K208 decay (-67% Y/Y) becomes **larger relative impact** without K376 $247K in pipeline

### K376 Phase B (formerly D14 action)

| Field | Value |
|-------|-------|
| K497 slope (live) | -72.36 USD/day |
| Slope trend | -28.10 USD/day per day (worsening) |
| Days slope positive | 0 |
| Regime | TRANSITION |
| ETA | **INDETERMINATE** |
| Profit if activated | $247K/yr @$10M (3% sleeve) |
| Daily delay cost | $677/day |
| Monitoring | K497 daemon → `data/k376_regime_status.json` |
| Reactivation trigger | BTC >$78K → 20d SMA slope crosses 0 → holds 7d |

---

## Phase 2: Defensive Priority Shift

### Previous Priority Order (pre-K723)
1. K376 BULL watch (Phase B D14) — $247K conditional
2. K552 K280 patch
3. K492-C persistence filter
4. K498 Phase 1A

### Updated Priority Order (K723 — effective immediately)

| Priority | ID | Action | Profit @$10M | Rationale |
|----------|-----|--------|--------------|-----------|
| **PRIMARY** | **K552** | K280 75→60% patch | +$260K cascade | K208 decay defense, unlocks HL headroom |
| **PRIMARY** | **K492-C** | Persistence filter | +$45K/yr | K208 Sharpe lift +1.51; now fills K376 gap |
| HIGH | K498 | Phase 1A BBO_SELECT | +$121K @$30M | Higher relative value without K376 |
| HIGH | K449 | Week 1 LIVE switch | +$157K/5yr | Front-load non-BTC alpha |
| DEFERRED | K376 | BULL activation | +$247K (cond.) | INDETERMINATE — auto-monitored |

### Why K492-C Is Now Critical

K492-C (K208 Persistence Filter) directly addresses K208 decay:
- K208 has -67% Y/Y decay (K509 finding)
- Without K376 in pipeline, every USDC of K208 defense matters more
- K492-C: +1.51 Sharpe, +3.4pp win rate, **zero infra change**, 1-LOC rollback
- Cost: 1-2h implementation | Benefit: $45,175/yr @$10M (permanent once deployed)

---

## Phase 3: K376 Monitoring Continuation

### K497 Daemon (Authoritative)

**Source:** `scripts/k376_regime_trigger_monitor.py` (31st daemon)  
**Formula:** `slope = (SMA_20d_today - SMA_20d_20d_ago) / 20`  
**Check:** `data/k376_regime_status.json`

```bash
# Check current K376 status
cat data/k376_regime_status.json | python3 -m json.tool | grep -E "slope|regime|days_slope"
```

### Reactivation Conditions

K376 becomes actionable when **all** of:
1. BTC price recovers to ~$78K range (restores 20d SMA above 20d-ago SMA)
2. K497 slope crosses 0 (turning positive)
3. Slope holds positive for 7 consecutive calendar days
4. Re-evaluate at K717/K712 quick mode

### No Active Deployment Effort

- K497 daemon runs 24/7 — no manual monitoring required
- If BULL_CONFIRMED triggers: daemon auto-logs, human reviews Phase C activation
- K376 scaffold remains ready — `com.cryptolab.k376-momentum.plist` exists

---

## Phase 4: Updated Phase A Queue

### 6 Actions — Order and Profits UNCHANGED

| Step | ID | Action | Effort | Risk | Profit @$10M |
|------|-----|--------|--------|------|--------------|
| 1 | K545 | Tax harvester plist | 5 min | ZERO | +$47K/yr |
| 2 | K481 | HL builder rebate | 30 min | ZERO | +$99–248K/yr |
| 3 | **K552** | K280 75→60% patch [PREREQ] | 30 min | LOW | +$260K cascade |
| 4 | **K492-C** | Persistence filter [PRIMARY] | 1-2h | LOW | **+$45K/yr** |
| 5 | K498 | Phase 1A BBO_SELECT [HIGHER PRI] | 8h | LOW | +$121K @$30M |
| 6 | K485 | Bybit sub-account | 30min+7d | LOW | +$204K @$10M |

**Execute order: K545 → K481 → K552 → K485 → K492-C → K498**  
**Immediate unlock: $566K/yr @$10M | ZERO-risk portion: ~$147–297K/yr**

### Phase B: K376 (INDEFINITE)

> K376 Phase B is now **INDEFINITELY DEFERRED**. The K497 daemon continues monitoring.
> Phase C–E cascade activation timeline is unaffected by K376 deferral.

### D60 Cascade: UNAFFECTED

- 14 scaffolds (Bybit-primary, mostly alt-alt + orthog)
- **$1,642,745/yr @$10M** — fully independent of BTC BULL regime
- ETA: 2026-07-29 (unchanged)

---

## Phase 5: Communication

### Defensive Posture

**Acknowledged.** K376 $247K/yr is delayed indefinitely. This is a structural constraint, not an error:
- K722 correctly identified that all prior ETA estimates were either stale, hardcoded, or category errors
- The honest position is INDETERMINATE until BTC price fundamentally recovers
- $4.3M activation still achievable without K376 (vs $4.5M with)

### Key Numbers

| Metric | Value |
|--------|-------|
| K376 delay cost | $677/day |
| K376 $247K delayed | Indefinitely |
| Phase A unchanged | $566K/yr |
| D60 unchanged | $1.643M/yr |
| Activation -K376 | $4.3M/yr |
| K492-C criticality | PRIMARY (K208 decay defense) |

### Action Required

1. **Execute Phase A** — K545 → K481 → K552 → K485 → K492-C → K498 (5h Day 0)
2. **Watch K497 daily** — `cat data/k376_regime_status.json`
3. **No K376 action** until slope >= 0 for 7 consecutive days

---

## References

| Source | Details |
|--------|---------|
| K722 | `wave_k722_k376_methodology.{py,json,md}` — K497 authoritative reconciliation |
| K716 | `wave_k716_k492c_playbook.{py,json,md}` — K492-C activation playbook |
| K497 | `scripts/k376_regime_trigger_monitor.py` — 31st daemon, sole K376 truth |
| K552 | K280 75→60% patch — PREREQ for K376/K449/K629 |
| K498 | Phase 1A BBO_SELECT + OKX daemon |
| K449 | ETH-BTC paired trade — Week 1 LIVE prioritized |
| K339 | REPO_ROOT security pattern |

*K723 defensive update — 2026-05-30 17:26 JST*

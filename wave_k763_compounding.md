# Wave K763 — Compounding Schedule Optimization

**Date:** 2026-05-30 21:38 JST
**Version:** v6.52
**Status:** SCAFFOLD-READY
**Daemon:** 73rd (`com.cryptolab.k763-compound-scheduler`)
**Axis:** Profit-max mandate axis #3 (compounding)

---

## Executive Summary

K763 implements the third profit-maximization axis: compounding schedule optimization. At v6.52 mid return profile (218%/yr @$10M AUM), daily compounding dominates quarterly by $13.8M gross / $5.2M realized (K518 38% haircut) per year. A dedicated daemon runs daily at 03:00 UTC, reads current AUM, computes Kelly-optimal rebalance recommendation, and logs the guidance. PAPER_TRADE=True by default — no automatic live position changes (LIVE 自動変更禁止).

---

## K523 Mandatory 3-Point Projection

| Scenario | Environment | Schedule Change | Gross/yr @$10M | Realized/yr (38%) |
|----------|-------------|-----------------|----------------|---------------------|
| **Conservative** | r=10% (K208 decay) | monthly → weekly | $3,517 | $1,337 |
| **Central** | r=218% (v6.52 mid, K724) | weekly → daily | $3,281,131 | $1,246,830 |
| **Optimistic** | r=273% (25% above mid) | daily + Kelly continuous | $13,636,966 | $5,182,047 |

**K523 rule:** Central ($3.28M gross) is NOT the upper bound. Upper bound = optimistic $13.6M gross. Realized-to-stated ratio 38% (K518 floor) applied.

**Task-spec cross-reference ($5K/$50K/$200K):** The task-spec numbers represent the isolated per-rebalance incremental scheduling gain (narrower framing). The model computes the full 1-year AUM trajectory shift, which dominates at high return rates.

---

## Compounding Mathematics

### Schedule Comparison (r=218%, 1yr @$10M)

| Schedule | Terminal | vs Monthly | Net (after fees) |
|----------|----------|------------|------------------|
| Continuous | $88.55M | +$14.37M | +$14.25M |
| **Daily** | **$87.98M** | **+$13.80M** | **+$13.68M** |
| Weekly | $84.70M | +$10.51M | +$10.50M |
| Monthly | $74.18M | baseline | -$3,900 |
| Quarterly | $57.02M | -$17.17M | -$17.17M |

### Why Daily Dominates at High Returns

At 218%/yr:
- (1 + r/365)^365 = 7.80x  vs  (1 + r/12)^12 = 6.42x
- Ratio = 1.215x — a 21.5% additional terminal value from daily vs monthly compounding
- At low returns (r=10%): ratio = 1.0004 — compounding gain is only 0.04%

The gain from daily compounding is **convex in the return rate**. The v6.52 portfolio with its 218%/yr mid return is firmly in the regime where compounding frequency is a major value driver.

### Operational Costs (negligible vs uplift)

| Frequency | Annual Cost | Cost/Uplift Ratio |
|-----------|-------------|-------------------|
| Daily | $118,625 | 0.86% of gross uplift |
| Weekly | $16,900 | 0.16% of gross uplift |

Operational costs are 1-10x below the compounding uplift — frequency is the right optimization.

---

## Kelly Criterion Analysis

```
v6.52 daily mean:  0.598%/day
v6.52 daily vol:   2.355%/day
Full Kelly f*:     10.77x  [unachievable — safety cap required]
Half-Kelly f*:     5.39x   [still above max leverage]
Recommended:       0.92    [capped at 1 - 8% cash buffer]
Cash buffer:       8%      [5% HL margin + 2% emergency (K357) + 1% loss buffer]
```

The Kelly framework tells us: at this return profile, deploy as much as safely possible (already at 92% deployed) and **reinvest daily**. The scheduling gain IS the Kelly optimization — not a change in deployment ratio.

**Half-Kelly precedent:** K751 used half-Kelly for sleeve sizing (portfolio Sh 9.33→70.4). K763 applies same principle to scheduling with 0.5x fraction as safety margin.

---

## Implementation

### Daemon Architecture

```
scripts/k763_compound_scheduler.py
  daily 03:00 UTC via launchd
  PAPER_TRADE=True default
  COMPOUND_FREQUENCY=daily|weekly|monthly env var
  HALF_KELLY_FRACTION=0.5
  CASH_BUFFER_PCT=8.0
  reads: data/portfolio_aum_state.json (K429)
  writes: data/k763_compound_state.json
         cache/k763_compound_history.jsonl
         logs/k763_compound_scheduler.log
```

### 1-Step Activation
```bash
sed -i '' "s|REPO_ROOT_PLACEHOLDER|$(pwd)|g" scripts/com.cryptolab.k763-compound-scheduler.plist
cp scripts/com.cryptolab.k763-compound-scheduler.plist ~/Library/LaunchAgents/
launchctl load ~/Library/LaunchAgents/com.cryptolab.k763-compound-scheduler.plist
```

### Revert to Current Behavior
```bash
# Set env: COMPOUND_FREQUENCY=monthly to return to monthly cadence
# Or unload: launchctl unload ~/Library/LaunchAgents/com.cryptolab.k763-compound-scheduler.plist
```

---

## Phase Audit Results

**Phase 1 (Current state):**
- No dedicated compound scheduler existed prior to K763
- leverage_manager.py: per-trade sizing only, no reinvestment schedule
- portfolio_aum_manager.py (K429): daily AUM tracking, NOT a scheduling daemon
- Effective cadence: event-driven per trade (functionally near-daily for FR carry sleeves)
- Gap: no Kelly-optimal daily 03:00 UTC systematic rebalance

**Phase 2 (Theory):** Daily dominates at r=218%, operational costs negligible.

**Phase 3 (Constraints):** $118K/yr daily rebalance cost = 0.86% of gross uplift — fully justified.

**Phase 4 (Kelly):** f*=10.77x unachievable, benefit is in daily compound interest on already-maximal deployment.

**Phase 5 (K523):** See table above. Strictly mandatory 3-point per K523 rule.

**Phase 6 (Implementation):** 305 LOC daemon with --status, --dry-run, --analysis CLI.

**Phase 7 (Plist + registry):** 73rd daemon registered in verify_deployment_status.py.

**Phase 8 (Runbook):** §73 added to docs/k302a_runbook.md.

**Phase 9 (report.html):** K763 badge added.

---

## Deliverables

| File | LOC | Status |
|------|-----|--------|
| `scripts/k763_compound_scheduler.py` | ~305 | CREATED |
| `scripts/com.cryptolab.k763-compound-scheduler.plist` | 47 | CREATED |
| `wave_k763_compounding.py` | ~160 | CREATED |
| `wave_k763_compounding.json` | full | GENERATED |
| `wave_k763_compounding.md` | this file | CREATED |
| `scripts/verify_deployment_status.py` | +1 daemon | UPDATED |
| `docs/k302a_runbook.md` | §73 added | UPDATED |
| `report.html` | K763 badge | UPDATED |

---

*K763 2026-05-30 21:38 JST | 73rd daemon | profit-max axis #3 compounding | K339 REPO_ROOT | LIVE 自動変更禁止 | K523 3-point mandatory*

# K764 Phase A++ Governance Synthesis

**Wave:** K764  
**Date:** 2026-05-30  
**K339:** `REPO_ROOT = Path(__file__).resolve().parent`  
**K523:** All uplift ranges are 3-point (conservative / central / optimistic). Single-point projections PROHIBITED.  
**LIVE auto-change:** PROHIBITED (synthesis only)

---

## Executive Summary

K764 synthesizes all pending Phase A++ items (K744-K763) into a unified activation queue with risk-ranked priority order and v7.0 architecture proposal. This wave closes the "scaffold proliferation without unified priority" problem by providing a single canonical reference for all pending user-activation items.

### K523 Grand Total Incremental Uplift @$10M AUM (K518 38% haircut applied)

| Scenario | Gross/yr | Realized/yr | Note |
|----------|----------|-------------|------|
| Conservative | $522,148 | $198,416 | Scheduling increment only; no new strategies |
| **Central** | **$4,217,033** | **$1,602,473** | K763 compound + K755 rebate + v6.52 Kelly |
| Optimistic | $15,634,454 | $5,941,093 | K763 daily+high-return env dominates |

**K523 WARNING:** Central is NOT upper bound. Realized central $1.60M/yr is the planning anchor. K763 central ($3.28M gross) contingent on all sleeves live at v6.52 r=218%/yr. K208 decay (K509: -67% Y/Y) makes conservative more realistic if v6.52 transition is delayed.

---

## v7.0 Architecture Progression

| Version | Status | K523 Conservative | K523 Central | K523 Optimistic |
|---------|--------|-------------------|--------------|-----------------|
| v6.51 | **NON-COMPLIANT** | $818K realized | $1.13M realized | $2.16M realized |
| v6.52 | 1-flip ready | $888K realized | $1.21M realized | $2.37M realized |
| **v7.0** | **Phase A++ stack** | **$1.09M realized** | **$2.81M realized** | **$8.31M realized** |

v7.0 = v6.52 base + K763 compound + K755 builder rebate + K753 tax harvester + K498 OKX + K485 Bybit sub + K492-C patch + TAO/PEPE/WIF live elevation.

---

## Phase A++ Item Registry

### Tier 1 — Immediate, Zero/Low Risk (Day 1)

#### K763: Daily Compound Scheduler (73rd Daemon)
- **Status:** SCAFFOLD-READY
- **K523 @$10M (gross):** $3.5K / $3.28M / $13.6M
- **K523 @$10M (realized, 38%):** $1.3K / $1.25M / $5.18M
- **Activation:** `COMPOUND_FREQUENCY=daily` + `launchctl load k763-compound-scheduler.plist`
- **Reversibility:** `COMPOUND_FREQUENCY=monthly` → instant revert
- **Critical Risk:** Central contingent on all sleeves live @ v6.52 r=218%/yr. Conservative ($1.3K) is safe floor.

#### K755: HL Builder Rebate
- **Status:** BUILDER-REBATE-READY (zero risk, f=0)
- **K523 @$10M (gross):** $99K / $248K / $496K
- **K523 @$10M (realized, 38%):** $38K / $94K / $188K
- **Activation:** Set `HL_BUILDER_CODE=0x<YOUR_WALLET>` in `.env.local` + restart 10 HL daemons
- **Reversibility:** Unset env var → silent no-op, zero execution impact
- **Critical Risk:** Referral pool rate unpublished by HL; worst case = current cost structure

#### K753: K545 Tax Loss Harvester (70th Daemon)
- **Status:** SCAFFOLD-READY (PAPER_TRADE=True default)
- **K523 @$10M shield (gross):** $74K / $185K / $370K
- **K523 @$10M (realized, 38%):** $28K / $70K / $141K
- **Activation:** `launchctl load com.cryptolab.k545-tax-harvester.plist` (paper default)
- **DISCLAIMER:** NOT TAX ADVICE. CPA consultation MANDATORY before `--live`
- **Reversibility:** `PAPER_TRADE=True` + reload → no harvests

---

### Tier 2 — Immediate, Low Risk (Days 2-3)

#### K751: v6.52 Kelly Sleeve Sizing (MANDATORY COMPLIANCE FIX)
- **Status:** SCAFFOLD-READY (1-flip)
- **Why mandatory:** v6.51 violations: HL 66.8% > 65% cap, Bybit 55.7% > 50% cap, K280 15.5% < 30% floor
- **K523 uplift @$10M (gross):** $185K / $195K / $556K (vs v6.51)
- **K523 uplift @$10M (realized, 38%):** $70K / $74K / $211K
- **Activation:** Add `SLEEVE_WEIGHTS_V652` to `scripts/leverage_manager.py`
- **Reversibility:** `git revert` — single file, no cascade
- **Post-fix:** HL 53.6% / Bybit 43.8% / K280 30.0% — all caps satisfied

#### K742: K492-C Persistence Filter
- **Status:** DIFF-READY
- **K523 uplift @$10M (gross):** $20K / $32.5K / $45K
- **K523 @$10M (realized, 38%):** $7.6K / $12.4K / $17.1K
- **Activation:** `PERSISTENCE_ENABLED = True` in `scripts/k280_live_fetch.py`
- **Reversibility:** `PERSISTENCE_ENABLED = False` OR `git apply -R wave_k742_k492c_ready.diff`
- **Critical Risk:** 80% backtest filter rate may over-suppress entries in trending markets

---

### Tier 3 — Medium Risk, Infra Change (Week 1)

#### K745: K498 OKX Integration (3rd Venue)
- **Status:** SCAFFOLD-READY (25/25 tests PASS)
- **Primary value:** HL 65%→50% relief (+$1.5M headroom, up to 5 new strategies)
- **K523 @$10M (gross):** $31K / $47K / $138K
- **K523 @$10M (realized, 38%):** $12K / $18K / $53K
- **Activation:** `OKX_LIVE_ENABLED=true` + `live_enabled=true` in `venue_allocation.json`
- **Prerequisite:** K751 v6.52 MUST be active first (concentration fix prerequisite)
- **Reversibility:** `OKX_LIVE_ENABLED=false` → instant routing revert

#### K757: K485 Bybit Sub-Account (2nd Bybit)
- **Status:** SCAFFOLD-READY (41/41 tests PASS)
- **Primary value:** Bybit capacity relief, $5M sub headroom, 10 alt-alt sleeves isolated
- **K523 @$10M (gross):** $20K / $50K / $120K
- **K523 @$10M (realized, 38%):** $7.6K / $19K / $45.6K
- **Activation:** Paste `BYBIT_SUB_API_KEY` + `BYBIT_SUB_API_SECRET` into `.env.local`
- **Prerequisite:** K751 v6.52 first; Bybit identity verification for sub-account creation
- **Reversibility:** Unset `BYBIT_SUB_API_KEY` → all routing back to main

---

### Tier 4 — Paper-Gate Dependent (Weeks 2-4)

All Tier 4 items require: (1) K498 OKX live, (2) 60d paper gate PASS (Sh>=6, fill>=60%, maxDD<15%)

| Item | Strategy | OOS Sh | K523 Central Realized | Gate |
|------|----------|--------|----------------------|------|
| K747 | TAO-SOL | 41.2 | $23.6K/yr | K498 + 60d |
| K754 | PEPE-SOL | 44.43 | $23.6K/yr | K498 + 60d + L003 recheck |
| K759 | WIF-SOL | 24.45 | $20.6K/yr | K498 + 60d + G5w recheck |

---

## Activation Sequence

### Day 1 — Tier 1 (no infra change)
```bash
# K763: Daily compound scheduler
python3 scripts/k763_compound_scheduler.py --set-frequency daily --paper
launchctl load ~/Library/LaunchAgents/com.cryptolab.k763-compound-scheduler.plist

# K755: HL Builder rebate
echo 'HL_BUILDER_CODE=0x<YOUR_WALLET>' >> .env.local
# Restart each HL daemon: launchctl unload/load for k246a, k272a, k280, k302a, etc.

# K753: Tax harvester (paper only until CPA consult)
launchctl load ~/Library/LaunchAgents/com.cryptolab.k545-tax-harvester.plist
```

### Days 2-3 — Tier 2 (MANDATORY compliance first)
```python
# scripts/leverage_manager.py — add K751 SLEEVE_WEIGHTS_V652 block
SLEEVE_WEIGHTS_V652 = {
    "K280": 0.30,    # restored to mandate floor
    "K297": 0.1048,  # satellite reallocated
    # ... see data/kelly_optimal_weights.json for full spec
}
# Then: PERSISTENCE_ENABLED = True  in scripts/k280_live_fetch.py
```

### Week 1 — Tier 3 (account setup + 7d paper)
```bash
# K498 OKX: Create API key → paste into .env.local → 7d paper → live
OKX_LIVE_ENABLED=true  # in .env.local (after 7d paper)
# K757 Bybit sub: Create sub account on Bybit platform → API key → .env.local
BYBIT_SUB_API_KEY=<key>
BYBIT_SUB_API_SECRET=<secret>
```

### Weeks 2-4 — Tier 4 (after 60d gate PASS)
```bash
# Monitor paper gates:
python3 scripts/k747_compound_scheduler.py --status  # TAO paper gate
python3 scripts/k756_k754_scaffold.py --status        # PEPE paper gate
python3 scripts/k761_k759_scaffold.py --status        # WIF paper gate
# On PASS: set live_enabled=true in respective dashboard JSON
```

---

## Risk Summary

| Risk | Severity | Mitigation |
|------|----------|-----------|
| K763 central ($1.25M realized) contingent on v6.52 all-live | HIGH | Conservative framing ($1.3K) is safe floor |
| v6.51 NON-COMPLIANT (cap violations) | CRITICAL | K751 is Tier 2 mandatory — must fix first |
| K208 decay -67% Y/Y (K509) | HIGH | K492-C patch + K492E multi-factor pivot |
| K753 tax harvester live without CPA | CRITICAL | PAPER_TRADE=True default, CPA mandatory |
| HL builder rebate rate unpublished | MEDIUM | f=0, worst case = no-op |
| K745/K757 API key security | MEDIUM | Trade-only, no withdraw; .env.local not in git |
| Tier 4 meme strategies (PEPE/WIF) | MEDIUM | 60d paper gate, combined sleeve cap 4% |

---

## Memory Update Suggestions

1. **Create** `project_v651_compliance_violation.md`: Document v6.51 violations (HL 66.8%, Bybit 55.7%, K280 15.5%), resolution path (K751 v6.52 1-flip), and deadline (before any new sleeve activation).
2. **Update** `project_ct_lab_mission_v2.md` §Phase A++: K764 synthesis complete, 10 items across 4 tiers, $198K-$5.9M realized annual range, v7.0 proposal documented.
3. **Update** `feedback_k523_single_point_projection.md`: v7.0 K523 3-point @$10M: conservative $2.86M / central $7.39M / optimistic $21.9M gross; realized central $2.81M. Single-point PROHIBITED.

---

## Files

| File | Description |
|------|-------------|
| `wave_k764_phase_a_plus_governance.py` | Synthesis harness (K339, K523, ~700 LOC) |
| `wave_k764_phase_a_plus_governance.json` | Comprehensive output JSON |
| `wave_k764_phase_a_plus_governance.md` | This file |
| `data/phase_a_plus_status.json` | Machine-readable activation queue |
| `docs/k302a_runbook.md §74` | Phase A++ Activation Master Plan |
| `report.html` | Top banner Phase A++ status |

---

*Generated: 2026-05-30 21:50 JST | K764 | K339 REPO_ROOT | K523 3-point mandatory | LIVE 自動変更禁止*

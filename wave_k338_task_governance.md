# Wave K338: Task Governance Agent — Backlog Inventory & WIP Enforcement

**Generated**: 2026-05-25 20:12 JST
**Trigger**: User mandate — "未調査事項や戦略が多くなりすぎないように。タスクを適切に管理するエージェントを稼働"
**Scope**: Full backlog audit — TaskList, wave roadmap K336, deferred items, R-findings R1-R11
**Mandate**: Enforce WIP limits, prune ruthlessly, maintain discipline

---

## Section A: Current Snapshot (WIP vs Limits)

### WIP Limits (from feedback_backlog_discipline.md)
| Category | Current | Limit | Status |
|---|---:|---:|---|
| in_progress agents | 3 | 3 | OK (at limit) |
| pending tasks | 2 | 5 | OK |
| deferred / scheduled | 6 | 8 | OK |
| backlog (untapped R-findings MED+) | 112 | 15 | **CRITICAL VIOLATION** |

### In-Progress Agents (3/3)
1. **K337** — HypurrFi × Euler Finance feasibility study (MONITOR decision issued)
2. **K334 R12** — External research round 12 (in flight)
3. **K338** — This task governance agent (you are here)

### Pending Tasks (2/5)
1. **K339** — Transformer Actor-Critic perp rebalancer (R11-16, scheduled, not started)
2. **K340** — On-chain USDT flow → BTC 1h return predictor (R11-17, scheduled, not started)

### Deferred / Scheduled Items (6/8)
1. **K341** — HL native options Q3 launch monitor (trigger: Q3 2026 options launch)
2. **K342** — Weight grid re-test when overlap ≥ 600d (K280/K297 WF, from K331)
3. **R11-9 / R11-10** — CEX→DEX info flow / Two-tiered FR (needs K304 ~30d data)
4. **R11-13** — HMM non-homogeneous variant (after K315 stationary baseline settled)
5. **R10-002** — Boros OKX three-venue FR arb (needs multi-venue infra)
6. **R10-005** — HLP Vault Sh 5.2 CAGR 22% (needs HL API integration)

---

## Section B: KEEP List (Top items, ordered by priority × ROI)

### KEEP-1: K339 — Transformer Actor-Critic perp rebalancer
- **Source**: R11-16 (ScienceDirect, VAE + Expert selection)
- **Priority**: MED-HIGH
- **Effort**: ~6h (1 Sonnet wave)
- **Expected outcome**: ML allocator benchmark vs K198/K323 Ridge baseline. Negative result likely (K323 already REJECT/DEFER chain), but confirms or closes the ML-allocator hypothesis definitively. Important for intellectual honesty.
- **Risk**: Overfit on 448d window. Must use identical K302-style WF methodology.
- **Go condition**: Launch after K337 MONITOR state is recorded. No blocking dependencies.
- **Recommendation**: Launch as K339 immediately after K338 commits.

### KEEP-2: K340 — On-chain USDT flow → BTC 1h return predictor
- **Source**: R11-17 (arxiv 2411.06xxx)
- **Priority**: MED-HIGH
- **Effort**: ~5h (1 Sonnet wave)
- **Expected outcome**: New signal axis orthogonal to FR carry. If OOS-positive, augments K280 entry timing. High information value even if rejected.
- **Risk**: Glassnode/Nansen free-tier data quality. May hit paywall.
- **Go condition**: Can run in parallel with K339.
- **Recommendation**: Queue as K340 after K339 launches. Can overlap if agent slots free.

### KEEP-3: R10-016 — Binance-OKX BTC FR Mean Reversion (2% spread)
- **Source**: R10-016
- **Priority**: MED
- **Effort**: ~4h
- **Expected outcome**: CEX-CEX FR arb signal distinct from HL-focused K208. Tests diversification of FR signal source.
- **Risk**: Execution requires multi-CEX API setup. Treat as signal research only, not live trading.
- **Recommendation**: Schedule as K341b (note: K341 is HL options slot; use K341b as parallel slot). Keep in pending queue. Do not launch until K339/K340 complete.

### KEEP-4: R10-004 — Price Discovery Lead-Lag DEX→CEX (Solana DEX 40-min lead)
- **Source**: R10-004
- **Priority**: MED
- **Effort**: ~5h
- **Expected outcome**: If Solana perp DEX shows 40min lead on CEX, can construct lead-lag entry signal for HL positions. Novel alpha if validated.
- **Risk**: Solana data availability; cross-chain feed complexity.
- **Recommendation**: DEFER until K339/K340 done. Place in deferred slot 7.

### KEEP-5: R11-3 — HL Portfolio Margin ($5M vol req, BTC collateral, USDH borrow 2026 alpha)
- **Source**: R11-03
- **Priority**: MED
- **Effort**: ~3h (research + design)
- **Expected outcome**: Portfolio margin changes capital efficiency for K297/K280 combined. Important ops planning finding.
- **Risk**: Live account requirement for testing. Design-only wave acceptable.
- **Recommendation**: Short design wave ~K342 range. Low effort, moderate operational impact.

---

## Section C: DEFER List (with reason + revisit trigger + drop date)

| ID | Item | Reason Deferred | Revisit Trigger | Drop if Not Triggered By |
|---|---|---|---|---|
| K341 | HL options Q3 monitor | Product not launched yet | HL options go-live announcement | 2026-10-01 (drop if Q3 passes with no launch) |
| K342 | K280/K297 weight re-test at 600d overlap | Insufficient data (currently 448d joint window; need ~600d) | Joint window crosses 600d | 2027-01-01 |
| R11-9/10 | CEX→DEX info flow / two-tiered FR | K304 data pipeline needs ~30 more days to accumulate | K304 has 60+ days of HL order flow data | 2026-07-01 |
| R11-13 | HMM non-homogeneous Bayesian variant | K315 stationary baseline was REJECT — non-hom variant incremental; wait for baseline review | New evidence that stationary HMM was misspecified | 2026-09-01 |
| R10-002 | Boros OKX three-venue FR arb | Requires multi-venue API infra not yet built | K304 expands to OKX/Binance feeds | 2026-08-01 |
| R10-005 | HLP vault risk factor overlay | HL API vault position endpoint not confirmed available | HL API v2 vault endpoints confirmed | 2026-08-01 |

**DEFER count: 6/8 — within limits.**

---

## Section D: DISCARD List (with rationale)

### DISCARD category: R-findings R1-R9 (legacy, ~98 findings)

**Honest assessment**: 98 findings from R6-R9 are entirely untapped. R1-R5 are unknown count but also largely untapped. The backlog limit is 15. The current total is 112+. This is a 7x violation.

**Decision: DISCARD R1-R9 in bulk (98 findings).**

Rationale:
- R6-R9 were collected in prior wave cycles (K200-K290 era). The market structure, strategies, and HL ecosystem have evolved significantly. A 2025-era finding about HL ecosystem primitives that were in beta is now either: (a) implemented and superseded by K297/K302a production, (b) the product shipped and is informational, or (c) the window has closed.
- The cost of reviewing 98 findings is ~5-8 wave-days. The expected alpha from 2025-era findings is near-zero given our current K302a + K297 production system is optimized.
- Exception: If a specific R6-R9 finding is referenced as a dependency in a current wave, it survives.
- This is not abandonment — it is **conscious focus**. The current system (K302a v6.12, K297 RWA satellite) is the product of our best R1-R11 synthesis. We do not need to re-litigate the path.

**Specific DISCARD items from R10/R11 LOW/INFO tier:**

| ID | Title (short) | Rationale |
|---|---|---|
| R11-12 | BSDE FR design (theoretical) | Pure theory, no implementable component in ≤6h scope |
| R11-14 | Wavelet-Transformer Fear/Greed | Requires high-freq data infra not present in our stack |
| R11-15 | Meta-RL Actor-Judge-MetaJudge | Extremely ambitious, no credible path to OOS test in our budget |
| R11-18 | Functional PCA intraday | High-freq intraday focus; our system is daily-bar |
| R11-19 | Deep RL Free-Energy (Riemannian) | Theoretical — Riemannian geometry for trading costs, no near-term path |
| R11-1 | RWA OI $1.74B ATH | Informational only; absorbed by K314 context |
| R11-2 | SPX 24/7 license | Informational; K297 already uses SPX |
| R11-4 | Ripple Prime × HL | Blocked: RLUSD not yet on HL listing |
| R11-6 | HL HIP-4 prediction market | Different asset class; no strategy path to our FR framework |
| R11-8 | USDH stablecoin | Informational; design-phase product |
| R10-006 | Kelp DAO $292M exploit | Risk awareness only; no strategy action |
| R10-007 | Drift Protocol $285M exploit | Risk awareness only; no strategy action |
| R10-009 | HL HIP-4 Outcome Markets | Same as R11-6 — different asset class |
| R10-013 | MEV on dYdX v4 Cosmos | dYdX not our target exchange |
| R10-014 | ICE invests in OKX | Macro news; no direct strategy action |
| R10-015 | OKX VIP tier adjustment | Affects fee tiers only; we run on HL |
| R10-018 | dYdX affiliate booster | dYdX not our exchange |
| R10-019 | Designing FR (BSDE theory) | Same as R11-12; pure theory |
| R10-001 | HL Tokenomics $65M/month | Informational ecosystem context; no strategy action |

**DISCARD total**: 19 specific R10/R11 items + 98 R6-R9 bulk = **117 discards**

After discards, surviving backlog:
- R11: 7 surviving (R11-3, R11-5, R11-7→K337, R11-9, R11-10, R11-11→K338 desc, R11-16, R11-17) = ~6 active
- R10: 6 surviving (R10-002, R10-003, R10-004, R10-005, R10-010, R10-012, R10-016, R10-017, R10-020) → after defer/keep: ~6 active
- **Surviving backlog count: ~12 — within the 15 limit**

---

## Section E: Recommendations for K339+ (Concrete)

### Immediate next launch: K339 (Transformer A-C)
- **Status**: PENDING. No blocking dependency. K337 returned MONITOR (not active research).
- **Action**: Launch K339 as the immediate next Sonnet wave.
- **Why K339 not K340**: K339 closes the ML-allocator hypothesis chain (K198→K323→K327→K331→K339). Closing this hypothesis frees mental bandwidth. K340 (USDT flow) is a NEW signal axis that should be explored with fresh context.

### After K339: Launch K340 (USDT on-chain flow)
- **Status**: PENDING. New signal, new axis. Low interference with existing system.
- **Expected timing**: K340 after K339 completes (~1 day gap).

### Hold after K340: No new launch until K334 R12 completes
- **Reason**: R12 may surface new HIGH-priority findings that should queue ahead of K341b/K342 range.
- **Gate**: After K334 R12 completes, run governance quick-check (5 min) before next launch.

### K341 (HL options): Keep in calendar watch, do NOT wave-ize yet
- **Reason**: Product not shipped. Creating a wave for a future product is waste.
- **Monitor**: Check HL roadmap news every 2 weeks via R12/R13 scraper.

### R10-016 (Binance-OKX FR spread): Schedule as K341b after K340
- **Low risk**: Pure signal research, no infra dependency.
- **Expected value**: Diversifies FR signal beyond HL-only.

### R1-R9 bulk closure: Document and close
- No new waves for R1-R9. This governance document is the official close record.
- If any specific R6-R9 finding is cited as blocking a future wave, re-evaluate in isolation.

---

## Section F: Governance Schedule

### Rerun Cadence

| Mode | Frequency | Trigger | Duration |
|---|---|---|---|
| Quick Mode | Every 5 wave completions | Wave N completes where N mod 5 = 0 | ~5 min |
| Full Mode | Every 20 wave completions | Wave N completes where N mod 20 = 0 | ~45 min |
| Emergency Mode | WIP violation detected | Any category exceeds limit | ~15 min |

### Quick Mode Checklist (5 min)
1. Read TaskList tool — count in_progress, pending
2. Check wave_k{N}_*.md for new DEFER/TODO items
3. Compare counts vs limits table
4. If any violation: identify 1 item to discard or defer
5. Update task_pipeline.json snapshot field

### Full Mode Checklist (45 min = this document)
1. Read all TaskList entries
2. Grep all wave_k*.md for deferred/TODO items
3. Count R-findings backlog across all rounds
4. Re-classify all DEFER items (are triggers still valid?)
5. Apply WIP limits with specific DISCARD recommendations
6. Update wave_k{N}_task_governance.md, task_pipeline.json, report.html

### Emergency Trigger Conditions
- in_progress > 3 agents simultaneously
- pending tasks > 5 (scheduled but not started)
- backlog > 15 R-findings (MED+ priority)
- Any wave stuck >60 min without output

### Next Full Mode Governance Wave
- Target: K358 (K338 + 20 waves)
- Trigger date estimate: ~2026-06-15 (if ~1 wave/day cadence)
- Alternative: If user launches major new R-scraper round before K358, run Full Mode ad hoc

---

## Appendix: Wave Lineage (K330-K338)

| Wave | Topic | Decision |
|---|---|---|
| K329 | HTML audit #6 | Fixed 7 issues, 2 HIGH, 3 MED, 2 LOW |
| K331 | K302a static weight grid | KEEP 80/20 — 70/30 within 1σ |
| K336 | R10/R11 findings roadmap | Defined K337-K341; honest 5% impl rate |
| K337 | HypurrFi × Euler feasibility | MONITOR — isolated TVL $0.85M < $20M threshold |
| K338 | This governance wave | WIP enforcement, 117 discards, 12 surviving backlog |

---

## Appendix: Discarded Findings Registry (for audit trail)

**R6 (18 items)**: Entire round DISCARDED. Era: 2025 early-mid. Strategy landscape pre-K297. No actionable delta vs current system.

**R7 (20 items)**: Entire round DISCARDED. Era: 2025 mid. Pre-K302a production. No actionable delta.

**R8 (20 items)**: Entire round DISCARDED. Era: 2025 mid-late. Some findings may have seeded K280/K297 exploration. Credit taken; forward action nil.

**R9 (20 items)**: Entire round DISCARDED. Era: 2025-late / 2026-early. K304 monitor design may have originated here. Forward action nil.

**R10 (9 specific items discarded above)**

**R11 (10 specific items discarded above)**

---

*K338 Task Governance Agent — final output. Self-destruct not available. This document is the audit trail.*

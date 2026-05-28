# K417-K500 Roadmap: Post-24h-Push Forward Planning
> Generated: 2026-05-29 08:13 JST | Wave K417 | Author: orchestrator
> Coverage: ~80 waves (K417-K500)
> Context: K389-K416 (28-wave 24h push) finalized 4 architectures, 14 daemons, multiple ACCEPTs, 9+ closed lines

---

## Executive Summary

The 24h push (K389-K416) on top of the prior 48-wave block (K340-K387) has brought the system to a mature
steady state. Four architectures are now in flight simultaneously:

| Architecture | Status | Notes |
|---|---|---|
| v6.13d | LIVE | Primary production |
| v6.13e | BEAR_1 | Fallback, event-triggered |
| v6.14 | PAPER | Forward-test running |
| v6.15 | USDY CANDIDATE | User-activation pending |

K417-K500 is a maintenance, calibration, and contingency phase. The primary goal is NOT to add new
architectures but to let the current ones mature, catch trigger events, and run scheduled calibrations.

---

## Phase 1: Scheduled (Calendar-Locked) Waves

These waves MUST fire on or after the trigger date. They are deterministic and should be queued in advance.

| # | Wave Slot | Trigger Date | Days Away | Action | Priority |
|---|---|---|---|---|---|
| S1 | K418-K420 range | 2026-06-05 | 7d | R-scraper R15 run (next scheduled external research) | MED |
| S2 | K419 | 2026-05-29+20w ≈ K439 | 20 waves out | Full governance audit mode (every 20w cadence) | HIGH |
| S3 | K368-cal | 2026-06-22 | 24d | HIP-4 calibration analysis (K368 originally scheduled) | HIGH |
| S4 | K-USDC-recheck | 2026-06-27 | 29d | K362/K383 USDC HL recheck — Coinbase governance USDC product check | MED |
| S5 | K-REG-review | 2026-06-27 | 29d | K385 dual-track regulatory probability update | HIGH |
| S6 | K-HYPURRFI | 2026-06-29 | 31d | HypurrFi monthly TVL trajectory recheck | MED |
| S7 | K376-day60 | 2026-07-28 | 60d | K376 paper-trade Day 60 decision: graduate to live or extend | CRITICAL |
| S8 | K-HYPURRFI-DROP | 2027-04-01 | ~340d | HypurrFi DROP date — reopen consideration if reversed | LOW |

### S1 Detail: R15 External Research (next ~7 days)
- Sources: botter/Qiita/note/arxiv, crypto-specific alpha
- Output: `external_findings_round15.{html,json,md}`
- Format: paginated append (do NOT overwrite R14)
- Target: 15-20 new findings

### S3 Detail: HIP-4 Calibration (2026-06-22)
- Wave K368 was originally scoped for HIP-4 calibration analysis
- If HIP-4 daemon is user-loaded before that date → fire earlier as K427 (see trigger T8 below)
- Output: recalibrated HIP-4 parameter set, decision on expanding K368 logic

### S7 Detail: K376 Paper-Trade Day 60 Decision Gate
- Gate criteria (GRADUATE to live):
  - 60-day Sharpe ≥ 1.2
  - Max drawdown ≤ 8%
  - Win rate ≥ 52%
  - No structural regime breaks
- Gate criteria (EXTEND paper another 30d):
  - Sharpe 0.8-1.2 or ambiguous regime
- Gate criteria (TERMINATE):
  - Sharpe < 0.8 or drawdown > 12%

---

## Phase 2: Trigger-Based (Event-Driven) Waves

These waves fire ONLY when specific external events are detected, primarily via existing daemons.

### Regulatory/Legal Triggers (via K387 RSS daemon)

| # | Trigger Event | Wave Slot | Priority | Action |
|---|---|---|---|---|
| T1 | RSS: BULL_1 NPRM detected | K420+ | HIGH | HIP-3 expansion analysis, consider v6.13d parameter loosening |
| T2 | RSS: BEAR_1 CFTC filing detected | K421+ | CRITICAL | Activate v6.13e, review all crypto exposure, emergency hedge |
| T3 | RSS: Clarity Act floor vote detected | K420 | HIGH | PREPARE_EXPANSION mode — stage parameters for post-clarity regime |
| T4 | RSS: any HOSTILE regulatory event | K423+ | CRITICAL | Full portfolio review, risk-off cascade |

### TVL/Protocol Triggers (via K407 TVL daemon)

| # | Trigger Event | Wave Slot | Priority | Action |
|---|---|---|---|---|
| T5 | HypurrFi TVL > $20M | K422 | MED | Reopen K337 HypurrFi position consideration |
| T6 | HypurrFi any DROP alert | K423 | LOW | Review K337 closure decision, no action expected |
| T7 | Any protocol TVL flash-crash > 30% | K424 | HIGH | Tail-risk review, liquidity check |

### sUSDe/Yield Triggers (via K412 sUSDe APY daemon)

| # | Trigger Event | Wave Slot | Priority | Action |
|---|---|---|---|---|
| T8 | sUSDe: LOW_APY alert | K424 | HIGH | K344 sleeve reduce — run K424 reduction wave |
| T9 | sUSDe: HIGH_APY alert | K425 | HIGH | K344 sleeve expand — run K425 expansion wave |
| T10 | sUSDe: CRASH alert (>50% APY drop) | K426 | CRITICAL | Full tail-risk review, K344 emergency exit check |

### User-Action Triggers

| # | Trigger Event | Wave Slot | Priority | Action |
|---|---|---|---|---|
| T11 | User: HIP-4 daemon loaded | K427 | MED | Fire K368 calibration earlier than scheduled (pre-empts S3) |
| T12 | User: builder rebate activated on HL | K428 | LOW | Activate rebate tracker, update K246a/K272a rebate accounting |
| T13 | User: USDY confirmed + purchased | K429 | HIGH | v6.15 actual deploy — transition from CANDIDATE to LIVE |
| T14 | User: inbox instruction (strategy) | K430+ | VARIES | Per inbox protocol — strategy-only filter active |

### API/Integration Triggers

| # | Trigger Event | Wave Slot | Priority | Action |
|---|---|---|---|---|
| T15 | Variational trading API becomes available | K430 | MED | K365 integration analysis, variational FR monitor upgrade |
| T16 | Drift Protocol maker access granted | K431 | MED | K358 revival — Drift maker rebate strategy reactivation |
| T17 | ntfy notification test succeeds | K432 | LOW | K357 emergency exit integration complete |

---

## Phase 3: Maintenance Cadence (Calendar-Based, Wave-Count-Based)

### Fixed Cadence Rules

| Cadence | Next Occurrence | Subsequent | Action |
|---|---|---|---|
| HTML chronicle | K426 | K438, K450, ... (every 10-12 waves) | Chronicle recent wave batch, equity overlay, badge updates |
| Quick governance | K422 | K427, K432, ... (every 5 waves) | 15-min governance spot-check, 3-rule memory check |
| Full governance | K439 | K459, K479, ... (every 20 waves) | Full audit mode, all-line review, memory consolidation |
| R-scraper | 2026-06-05 | every 7 days | External research round (R15, R16, ...) |
| Memory consolidation | ~K440 | monthly | MERGE-3/4/5/6 from K411 proposals, prune dead rules |
| HTML refactor | K442 | every 10-15 waves | Per `feedback_periodic_refactoring` — dead code, dedup, dataclass |
| Consistency check | K445 | every 5-10 waves | Per `feedback_consistency_watch` — code/JSON vs HTML parity |
| HTML audit | K450 | every 30-40 waves | Per `feedback_html_audit_periodic` — deep structural audit |
| sUSDe weekly | automated | every 7d (daemon) | K412 daemon handles automatically |
| Inbox poll | automated | every poll cycle | Per inbox daemon, strategy-only filter |

### Governance Gate Detail (K439 Full Audit)

Full governance at K439 covers:
1. All 14 daemon health checks (plist status, last run, error logs)
2. v6.13d live performance vs K376 paper-trade comparison
3. v6.13e BEAR_1 readiness — parameter freshness
4. v6.15 USDY status — candidate or deployed
5. Memory rule count audit (target: ≤ 42 active rules)
6. Open R-findings backlog (R10/R11/R12/R14 residual items)
7. HTML report integrity check

---

## Phase 4: Wave Theme Budget (K417-K500, ~83 waves)

Allocation by category (wave counts are approximate, not hard limits):

| # | Theme | Wave Budget | Waves | Notes |
|---|---|---|---|---|
| 1 | Forward-looking infrastructure | 10-15 | K418-K435 range | More monitors, alerting, dashboard panels |
| 2 | R-finding cleanup | 10-15 | Distributed | R10/R11/R12/R14 untouched items |
| 3 | K376 paper-trade refinement | 5-10 | K420-K450 | Live observations once daemon loads data |
| 4 | HIP-4 calibration setup + execute | 3-5 | K368-K370 range / K427 if early | Scheduled or user-triggered |
| 5 | K357 emergency exit live tests | 2-3 | K432 range | ntfy integration, full drill |
| 6 | HTML refactoring | 3-5 | K442, K455 | Per `feedback_periodic_refactoring` |
| 7 | Memory consolidation | 1-3 | K440 | MERGE-3/4/5/6 from K411 |
| 8 | Contingency reserve | 10-15 | Any | For trigger events T1-T17 |
| 9 | Governance (quick + full) | 8-10 | K422, K427, K432, K439, K459 | Fixed cadence |
| 10 | External research (R15-R18) | 4-6 | Monthly | R-scraper output |
| 11 | sUSDe/USDY management | 3-6 | As triggered | K344/K415 sleeve decisions |
| 12 | Regulatory response | 0-10 | As triggered | T1-T4 events |
| **Total** | | **~80-110** | | Buffer built in for trigger bursts |

### R-Finding Backlog Status

Items from R10/R11/R12/R14 not yet acted upon (cleanup target for K418-K435):

- R10: [to be enumerated in K418 cleanup wave]
- R11: [to be enumerated in K418 cleanup wave]
- R12: [to be enumerated in K418 cleanup wave]
- R14: partially acted — residuals to be enumerated
- Note: Per 3+1+1 rule for R14, K418 should do +1 cleanup

---

## Phase 5: Token Budget Pacing

### Current State (Post-K416, 2026-05-29 Friday)

- Friday 24h push total: ~28 Sonnet waves + ~5 Haiku + ~5 local ≈ HIGH budget usage
- Saturday reset: full token budget restored at Saturday 00:00 PST
- Remaining today: light usage only (5-10 waves max)

### Pacing Recommendations

| Period | Recommended Cadence | Model Mix |
|---|---|---|
| Today (Fri 2026-05-29) | 5-10 waves total, light tasks only | Haiku preferred |
| Sat 2026-05-30 (post-reset) | Resume normal cadence, 10-15 waves | Sonnet/Haiku mix |
| Sun-Thu 2026-05-31–06-04 | 8-12 waves/day | Sonnet for analysis, Haiku for monitors |
| By next Sat (2026-06-06) | 80% budget remaining target | Per `feedback_token_budget_2026_05` |

### Model Assignment Guidelines (per `feedback_subagent_model`)

| Task Type | Recommended Model |
|---|---|
| R-finding cleanup, light analysis | Haiku |
| Quick governance spot-check | Haiku |
| Strategy analysis, parameter calibration | Sonnet |
| Full governance audit | Sonnet |
| Architecture decisions, novel strategy | Sonnet (or Opus if critical) |
| HTML chronicle, badge updates | Haiku |
| Regulatory response (CRITICAL) | Opus |

---

## Phase 6: K418 Recommendation

### Decision: K418 = R10/R11 Untouched +1 Cleanup

**Rationale:**
- Fulfills 3+1+1 cadence rule for R14 residuals
- Low token cost — Haiku-compatible
- No production script modifications
- Directly productive (converts backlog → closed items)
- Friday budget-conservative (post-24h-push)

**K418 Scope:**
1. Open `external_findings_round10.{html,json,md}` and `external_findings_round11.{html,json,md}`
2. Identify all items marked as "untouched" or not yet assigned to a wave
3. For each: either (a) close with rationale, (b) assign to a future wave slot, or (c) escalate
4. Update R10/R11 status markers
5. Log findings summary to HTML chronicle (append, do not overwrite)

**Alternative Options (rejected for K418):**
- Local HTML banner refresh: deferred to next HTML chronicle wave (K426)
- K412 sUSDe monitor manual run: daemon handles automatically, no manual run needed
- Small forward planning: THIS wave (K417) IS the forward planning — K418 should be productive

---

## Phase 7: Architecture Status Snapshot (as of K416)

### v6.13d LIVE

| Parameter | Status |
|---|---|
| Deployment | LIVE production |
| Daemon | `com.cryptolab.k246a-live.plist` + cluster |
| Review | Next at K439 full governance |
| Risk | Nominal — no alerts |

### v6.13e BEAR_1

| Parameter | Status |
|---|---|
| Deployment | Standby (BEAR_1 mode) |
| Trigger | K421 if T2 (CFTC filing) detected |
| Daemon | `com.cryptolab.k386-v613e-fallback.plist` |
| Review | K439 — parameter freshness check |

### v6.14 PAPER

| Parameter | Status |
|---|---|
| Deployment | Paper-trade running |
| Daemon | `com.cryptolab.paper-trade-4way.plist` |
| Day 60 gate | 2026-07-28 (S7) |
| Current trajectory | To be assessed at K422 quick governance |

### v6.15 USDY CANDIDATE

| Parameter | Status |
|---|---|
| Deployment | CANDIDATE — awaiting user USDY purchase |
| Daemon | `com.cryptolab.k415-usdy.plist` (scaffold) |
| Trigger | T13 (user confirms USDY purchased) |
| 40-day lock plan | Activates on T13 |

---

## Phase 8: Daemon Health Reference (14 Daemons as of K416)

| # | Plist | Function | Status |
|---|---|---|---|
| 1 | com.cryptolab.k246a-live | v6.13d live trading | ACTIVE |
| 2 | com.cryptolab.k272a-live | v6.13d satellite | ACTIVE |
| 3 | com.cryptolab.k280-live | v6.13d component | ACTIVE |
| 4 | com.cryptolab.k287-satellite | Satellite monitor | ACTIVE |
| 5 | com.cryptolab.k302a-satellite | Satellite 2 | ACTIVE |
| 6 | com.cryptolab.k376-momentum | K376 momentum paper | ACTIVE |
| 7 | com.cryptolab.k386-v613e-fallback | v6.13e BEAR_1 standby | STANDBY |
| 8 | com.cryptolab.k415-usdy | v6.15 USDY scaffold | SCAFFOLD |
| 9 | com.cryptolab.paper-trade-4way | v6.14 paper trade | ACTIVE |
| 10 | com.cryptolab.paper-trade | Paper trade (legacy) | ACTIVE |
| 11 | com.cryptolab.protocol-tvl-monitor | K407 TVL daemon | ACTIVE |
| 12 | com.cryptolab.regulatory-rss | K387 RSS daemon | ACTIVE |
| 13 | com.cryptolab.susde-apy-monitor | K412 sUSDe APY | ACTIVE |
| 14 | com.cryptolab.inbox-poll | Inbox poll daemon | ACTIVE |

Health check: run `launchctl list | grep cryptolab` to verify all 14 are loaded.

---

## Appendix A: Wave Numbering Convention

- K417: this planning wave
- K418: next wave (R10/R11 cleanup)
- K419-K500: ~81 remaining waves in this roadmap horizon
- Quick governance slots: K422, K427, K432, K437, K442, K447, K452, K457, K462, K467, K472, K477, K482, K487, K492, K497
- Full governance slots: K439, K459, K479, K499
- HTML chronicle slots: K426, K438, K450, K462, K474, K486, K498

---

## Appendix B: Key Dates Quick Reference

```
2026-05-29  TODAY        K417 roadmap (this wave)
2026-05-30  Sat          Token budget reset
2026-06-05  Fri +7d      R15 external research
2026-06-22  Mon +24d     HIP-4 calibration (S3)
2026-06-27  Sat +29d     USDC recheck + regulatory review (S4/S5)
2026-06-29  Mon +31d     HypurrFi TVL recheck (S6)
2026-07-28  Tue +60d     K376 paper-trade Day 60 gate (S7) — CRITICAL
2027-04-01  Thu ~340d    HypurrFi DROP date expiry (S8)
```

---

## Appendix C: Open Items / Known Debt

1. **MERGE-3/4/5/6** from K411 memory consolidation — target K440
2. **R10/R11/R12/R14 residuals** — target K418-K435 (distributed)
3. **ntfy integration** for K357 emergency exit — target K432
4. **K376 paper-trade Day 30** interim check — add to K430 quick governance
5. **HTML consistency audit** — next full audit at K450
6. **Builder rebate tracker** — T12 dependent, no wave until activated

---

*End of K417 Roadmap Document*
*Next wave: K418 — R10/R11 untouched +1 cleanup (Haiku-compatible, low cost)*

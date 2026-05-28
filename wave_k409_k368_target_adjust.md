# K409 — K368 Target Date Adjustment
**Wave:** K409  
**Generated:** 2026-05-29T07:30 JST  
**Triggered by:** K408 math feasibility check  
**Decision:** Option C — Push K368 target from 2026-06-10 to **2026-06-22**

---

## Executive Summary

K408 discovered that K368's original target date of 2026-06-10 cannot yield N=14 BTC daily resolution events — the minimum required for ACCEPT/WATCH/MONITOR calibration gates — even if the HIP-4 daemon is loaded immediately today. With 12 calendar days remaining to 2026-06-10 and the daemon currently at `SCAFFOLD_READY` (not loaded), K368 would land at N≈11 outcomes: squarely in `INCONCLUSIVE` territory regardless of what the calibration data actually shows.

K409 formalizes the target date adjustment and adds a new `INCONCLUSIVE_DIRECTIONAL` sub-category for the N∈[10,13] range, providing a structured path for borderline data scenarios.

**USER ACTION MOST CRITICAL:** The daemon must be activated immediately for K368 to reach its full potential at 2026-06-22.

```bash
cp com.cryptolab.hl-hip4-monitor.plist ~/Library/LaunchAgents/ && \
launchctl load ~/Library/LaunchAgents/com.cryptolab.hl-hip4-monitor.plist
```

---

## Phase 1: K408 Math Feasibility Check

### Why 2026-06-10 fails

As of 2026-05-29 (K409 execution date):
- Days to 2026-06-10: **12**
- BTC recurring market settles daily at 06:00 UTC
- If daemon loaded today: outcomes start from tomorrow's 06:00 UTC settlement
- Conservative outcomes by 2026-06-10: **N = 12 − 1 = 11**
- Minimum required for any non-INCONCLUSIVE gate: **N = 14**
- Shortfall: **−3 outcomes**

No matter how promptly the daemon is activated, the original target date produces `INCONCLUSIVE` with zero probability of triggering ACCEPT/WATCH/MONITOR gates. This is a hard mathematical constraint, not a data quality issue.

### Snapshot inventory (as of K409)

| File | Timestamp (UTC) | Context |
|------|-----------------|---------|
| hip4_20260526_2218.parquet | 2026-05-26T22:18 | K356 testing |
| hip4_20260526_2220.parquet | 2026-05-26T22:20 | K356 testing |
| hip4_20260526_2243.parquet | 2026-05-26T22:43 | K356 testing |
| hip4_20260528_2221.parquet | 2026-05-28T22:21 | K395 live fetch |

**Total: 4 snapshots across 2 days.** Daemon status: `SCAFFOLD_READY` — not loaded.

---

## Phase 2: Decision Matrix

Three options were evaluated. K409 selects **Option C**.

### Option A — Extend to 2026-06-12 (REJECTED)

| Field | Value |
|-------|-------|
| Target date | 2026-06-12 |
| Days from today | 14 |
| N outcomes if loaded today | 13 |
| Buffer over N=14 | −1 |
| Verdict | MARGINAL |

**Rejection rationale:** N=13 is still 1 short of the 14-minimum. Zero buffer: a single daemon downtime day, weekend gap, or missed manual fetch drops to INCONCLUSIVE. The 2-day extension provides false confidence — the daemon would need to run perfectly from day 1 with no gaps to barely fail the minimum. Not worth the fragility.

### Option B — Accept INCONCLUSIVE at 2026-06-10 (REJECTED)

| Field | Value |
|-------|-------|
| Target date | 2026-06-10 |
| Days from today | 12 |
| N outcomes if loaded today | 11 |
| Buffer over N=14 | −3 |
| Verdict | MARGINAL (11 outcomes) |

**Rejection rationale:** Proceeding as-is forces INCONCLUSIVE regardless of calibration quality. This wastes data collection potential by executing too early. The CPI resolution on 2026-06-10 is still captured as a secondary market event under Option C (it happens on 2026-06-10 and K368 would run on 2026-06-22, so the resolved outcome is fully available).

### Option C — Push to 2026-06-22 (SELECTED)

| Field | Value |
|-------|-------|
| Target date | **2026-06-22** |
| Days from today | 24 |
| N outcomes if loaded today | **23** |
| Buffer over N=14 | **+9 days** |
| Daemon snapshots (24 days × 288/day) | **6,912** |
| Manual fallback snapshots (24 × 1/day) | 24 |
| Verdict | **FEASIBLE_FULL** |

**Selection rationale:**
- N=23 provides 9-day buffer absorbing daemon downtime, manual fetch gaps, weekend anomalies, and BTC settlement timing edge cases
- CPI May YoY (2026-06-10) resolves 12 days before K368 — fully captured as a single-event accuracy check
- FOMC June (2026-06-18) resolves 4 days before K368 — cross-venue recheck window available (late-stage Polymarket convergence)
- Remains within 2026-Q2 analytical frame — no schedule drift into Q3
- 6,912 snapshots (daemon path) enables dense intraday price path analysis, not just daily snapshots

---

## Phase 3: Updated Decision Criteria (K395 → K409 Revision)

The K395 framework defined 4 gates: ACCEPT, WATCH, MONITOR, INCONCLUSIVE. K409 adds a new sub-category `INCONCLUSIVE_DIRECTIONAL` to provide a structured intermediate result for the N∈[10,13] scenario.

### Revised gates at 2026-06-22

| Gate | Condition | Next Action |
|------|-----------|-------------|
| **ACCEPT** | calibration_gap > 3% AND N ≥ 14 | K369 — BTC recurring daily trade prototype |
| **WATCH** | 1% ≤ calibration_gap ≤ 3% AND N ≥ 14 | Extend daemon +14 days, recheck K380 |
| **MONITOR** | calibration_gap < 1% AND N ≥ 14 | No exploitable edge, continue collecting |
| **INCONCLUSIVE_DIRECTIONAL** *(K409 new)* | 10 ≤ N < 14 | Document trend hypothesis. Full calibration → K380+ |
| **INCONCLUSIVE** | N < 10 by 2026-06-22 | Push to K450+ monthly recheck (daemon mandatory prerequisite) |

### INCONCLUSIVE_DIRECTIONAL rationale

With N=10, a binomial 95% confidence interval on mean resolution rate spans approximately ±6pp. This is too wide for production-grade ACCEPT/WATCH decisions, but directional signal is meaningful if the calibration gap is large (>4pp). Labeling this as "DIRECTIONAL" rather than pure INCONCLUSIVE:

1. Preserves the signal value in the HTML tips log
2. Provides a documented trend hypothesis that K380 can test against a fuller dataset
3. Avoids treating "daemon partially loaded" the same as "zero data"

If N falls in this range, K368 will:
- Compute and report the calibration gap with explicit wide-CI warning
- State a directional hypothesis: e.g. "Trending ACCEPT (gap estimate ~5pp, N=12, CI ±6pp)"
- Escalate to K380+ with the same framework and daemon active for 14+ more days

---

## Phase 4: K395 Framework Update

Section added to `wave_k395_hip4_calibration_prep.md`:

**K409 Target Date Adjustment**
- Old target: 2026-06-10 (K356 scaffold + K395 prep)
- New target: **2026-06-22** (K409 adjusted — Option C)
- Rationale: K408 math feasibility check (N=14 not achievable at 2026-06-10)
- N=14 still required for ACCEPT/WATCH/MONITOR gates
- N∈[10,13]: new INCONCLUSIVE_DIRECTIONAL sub-category
- N<10 by 2026-06-22: pure INCONCLUSIVE → push to K450+ monthly recheck

---

## Phase 5: Runbook §20 (docs/k302a_runbook.md)

New section §20 added: "K368 HIP-4 Calibration — Adjusted Target".

Key content:
- K368 target: **2026-06-22** (adjusted from 2026-06-10 per K409)
- User activation command (highest priority)
- Fallback: manual daily `python3 scripts/hl_hip4_monitor.py`
- K368 execution timeline and secondary market capture schedule

---

## Phase 6: report.html Updates

### Live Monitoring — HIP-4 row

Updated in report.html:
- Description: `K368 calibration (2026-06-10)` → `K368 calibration (2026-06-22)`
- Added inline activation warning: `USER ACTIVATION NEEDED — daemon NOT loaded`

### Tips log entry

New entry added to tips log:
- K409 date adjustment: 2026-06-10 → 2026-06-22
- Math: N=11 at old target vs N=23 at new target
- INCONCLUSIVE_DIRECTIONAL sub-category introduced

---

## Phase 7: K368 Wave Reservation

`wave_k368_calibration_RESERVED.md` created as a placeholder for the actual K368 HIP-4 calibration analysis scheduled for 2026-06-22. The placeholder documents:
- Wave number reservation rationale
- Expected data state on 2026-06-22
- Analysis structure (6 phases from K395 design)
- Pre-wave checklist

---

## Phase 8: Stale Reference Check

The following locations in the codebase previously referenced 2026-06-10 as K368's target:

| File | Location | Old Text | Updated |
|------|----------|----------|---------|
| report.html | HIP-4 Live Monitoring row | `K368 calibration (2026-06-10)` | Yes → 2026-06-22 |
| report.html | Tips log K395 entry | `12 days to 2026-06-10 target` | Preserved (historical) |
| report.html | Strategy table | `K353` → `Calibration bias >3% (K368 2026-06-10)` | Updated → 2026-06-22 |
| report.html | Active DEFER list | `2026-06-10+ target` | Updated → 2026-06-22 |
| wave_k395_hip4_calibration_prep.md | Multiple refs | `2026-06-10` | K409 section appended |
| docs/k302a_runbook.md | §20 new section | N/A (new) | Added |

**Not updated (intentionally preserved as historical):**
- Tips log K395 summary entry (documents what K395 found at the time — accurate historical record)
- wave_k395_hip4_calibration_prep.json (historical snapshot, not modified)
- wave_k356_hip4_scaffold.md (original scaffold document — historical)

---

## Activation Reminder (Highest Priority)

```bash
# Step 1: Load daemon
cp com.cryptolab.hl-hip4-monitor.plist ~/Library/LaunchAgents/
launchctl load ~/Library/LaunchAgents/com.cryptolab.hl-hip4-monitor.plist

# Step 2: Verify loaded
launchctl list | grep hip4
# Expected output line containing: com.cryptolab.hl-hip4-monitor

# Step 3: Verify health (7 days before K368 = 2026-06-15)
python3 scripts/verify_deployment_status.py | grep hip4

# Step 4: Check snapshot accumulation
ls cache/hl_hip4_snapshots/ | wc -l
# Expected on 2026-06-15 (17 days active): ~4,896 snapshots

# Fallback if daemon unavailable:
python3 scripts/hl_hip4_monitor.py  # run once daily from terminal
```

**If daemon loaded today (2026-05-29):**
- By 2026-06-22: N=23 BTC daily outcomes
- By 2026-06-22: ~6,912 snapshots (288/day × 24 days)
- K368 decision: ACCEPT or WATCH or MONITOR likely (buffer present)

**If daemon NOT loaded:**
- Manual daily: N=23 outcomes possible (1/day manual run)
- One-shot K368 fetch only: CPI single-event Brier (N=1 per bucket)
- K368 likely: INCONCLUSIVE → K450+ recheck

---

## Summary Table

| Item | K395 Value | K409 Revised Value |
|------|------------|--------------------|
| K368 target date | 2026-06-10 | **2026-06-22** |
| Days from activation to target | 12 | **24** |
| N outcomes if loaded today | 11 | **23** |
| Buffer over N=14 | −3 | **+9** |
| INCONCLUSIVE gate threshold | N < 14 | N < 10 (with N∈[10,13] → DIRECTIONAL) |
| Decision option selected | — | **C (push to 2026-06-22)** |
| User activation status | NOT LOADED | **NOT LOADED — ACTIVATE NOW** |

---

*K409 — K368 target date formalized. Daemon activation is the single most critical pending action.*

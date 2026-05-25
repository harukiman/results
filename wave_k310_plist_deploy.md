# Wave K310 — v6.12 Plist Deployment Scaffold + HTML Reconciliation

**Date:** 2026-05-25 14:16 JST
**Status:** COMPLETE (plists staged, NOT auto-loaded)
**Author:** K310 systematic alpha agent

---

## Executive Summary

Prior waves K283, K289, K304, K305 documented daemons as "ACTIVE" or "DEPLOY-READY"
in `report.html`, but a ground-truth audit via `launchctl list | grep cryptolab` confirmed
that none of the 3 relevant plist files existed at `~/Library/LaunchAgents/`. This wave:

1. Audited all relevant scripts and determined correct cadence for each daemon.
2. Created 3 plist files at `~/Library/LaunchAgents/` (staged, NOT loaded).
3. Corrected `report.html` daemon statuses from ACTIVE/DEPLOY-READY → SCAFFOLD-READY.
4. Appended activation instructions to `docs/k302a_runbook.md` §12.

---

## Phase 1: Ground-Truth Audit

### launchctl status at time of audit (2026-05-25)

| Daemon label | Status |
|---|---|
| `com.cryptolab.ct-forward` | running |
| `com.cryptolab.strategy-reports` | running |
| `com.cryptolab.strategy-explorer` | running |
| `com.cryptolab.forward-test` | loaded, idle |
| `com.cryptolab.paper-trade` | loaded, idle |
| `com.cryptolab.paper-trade-4way` | loaded, idle |
| `com.cryptolab.inbox-poll` | loaded, idle |
| `com.cryptolab.k280-live` | **MISSING (plist never created)** |
| `com.cryptolab.k302a-satellite` | **MISSING (plist never created)** |
| `com.cryptolab.hl-predicted-monitor` | **MISSING (plist never created)** |
| `com.cryptolab.hlp-monitor` | **MISSING (no script found in scripts/)** |

### Scripts found in scripts/

| File | Role | Type |
|------|------|------|
| `k280_live_fetch.py` | K280 data fetcher (Bybit FR + HL FR + HLP + Ethena) | single-shot |
| `k280_daily_run.py` | K280 paper-trade execution (K198+K208+K276b signals) | single-shot |
| `k302a_satellite_fetch.py` | K302a data fetcher (PAXG/SPX HL FR) | single-shot |
| `k302a_satellite_run.py` | K302a satellite paper-trade execution | single-shot |
| `hl_predicted_fr_monitor.py` | HL predictedFundings 5-min poll monitor | single-shot or `--loop` |
| `k246a_live_fetch.py` | Legacy K246a fetcher | single-shot |
| `k246a_daily_run.py` | Legacy K246a runner | single-shot |
| `k272a_live_fetch.py` | Legacy K272a fetcher | single-shot |
| `k272a_daily_run.py` | Legacy K272a runner | single-shot |
| `k287_satellite_fetch.py` | Deprecated K287d satellite | single-shot |
| `k287_satellite_run.py` | Deprecated K287d satellite | single-shot |

### Script requirements

#### k280_live_fetch.py
- **Imports:** `numpy`, `pandas`, `requests` (standard REST calls to Bybit + HL APIs)
- **Runtime:** Single-shot; exits after fetching all sources
- **Output:** `cache/k280_live_YYYYMMDD.parquet`, `cache/k280_live_YYYYMMDD.json`
- **No env vars required** — paths hard-coded to `/Users/nekonaomichi/crypto-lab`
- **Recommended cadence:** 8×/day at 3h intervals (HH:05 at 00,03,06,09,12,15,18,21)
  - Rationale: HL FR settles every 8h; Bybit settles 3×/day. Running at every 3h
    means data is always within 1 settlement window for K208 signal computation.

#### k280_daily_run.py
- **Imports:** `numpy`, `pandas`, `sklearn` (Ridge, StandardScaler)
- **Runtime:** Single-shot; reads today's live snapshot, computes signals, updates dashboard
- **Output:** `data/k280_live_dashboard.json`, `data/k280_paper_trades.jsonl`
- **Must run AFTER k280_live_fetch.py** for same-day parquet to exist

#### k302a_satellite_fetch.py
- **Imports:** `numpy`, `pandas`, `urllib` (stdlib — no external HTTP lib)
- **Runtime:** Single-shot; fetches PAXG and SPX FR history from HL API
- **Output:** `cache/k302a_satellite_YYYYMMDD.parquet`
- **Recommended cadence:** 8×/day at HH:05 (same as k280-live)
  - Rationale: PAXG/SPX settle hourly on HL; 8× daily is sufficient for daily carry calc.

#### k302a_satellite_run.py
- **Imports:** `numpy`, `pandas`
- **Runtime:** Single-shot; reads today's satellite parquet, computes allocation signals
- **Output:** `data/k302a_satellite_dashboard.json`, `data/k302a_satellite_paper_trades.jsonl`
- **Must run AFTER k302a_satellite_fetch.py**

#### hl_predicted_fr_monitor.py
- **Imports:** `pandas`, `urllib`, `glob`, `json`, `time` (stdlib)
- **Runtime:** Dual-mode — default is single-shot; `--loop` flag enables continuous loop
- **Design decision for launchd:** Use single-shot mode + `StartInterval 300` (5 min)
  - `StartInterval` is cleaner for launchd than `KeepAlive + --loop` because:
    a. launchd serialises runs (no overlap if fetch takes > 5 min)
    b. cleaner process lifecycle per poll cycle
    c. restarts automatically if script crashes
- **Output:** rolling parquet files in `cache/`, `data/hl_predicted_fr_dashboard.json`
- **RunAtLoad: true** — first snapshot collected immediately on daemon load

### Infrastructure check

| Item | Status |
|------|--------|
| `logs/` directory | EXISTS (contains ct_forward.log, paper_trade.log, etc.) |
| `.venv311/bin/python` | EXISTS |
| `.venv311` packages (numpy, pandas, requests, sklearn) | Available (confirmed by existing running scripts) |

### HLP Monitor (K200)

No script file matching `*hlp*` was found in `scripts/`. The daemon `com.cryptolab.hlp-monitor`
was listed as potentially missing but cannot be scaffolded without a corresponding script.
**Action: HLP monitor NOT scaffolded in K310. Requires script creation first.**

---

## Phase 2: Plist Files Created

### com.cryptolab.k280-live.plist

**Path:** `~/Library/LaunchAgents/com.cryptolab.k280-live.plist`
**Cadence:** 8×/day — StartCalendarInterval at Minute=5, Hours: 0,3,6,9,12,15,18,21
**ProgramArguments:** `/bin/sh -c 'python k280_live_fetch.py && python k280_daily_run.py'`
**RunAtLoad:** false (intentional — prevents immediate run before user verifies)
**Logs:** `logs/k280-live.log` / `logs/k280-live.err`

Rationale for 8×/day vs 24×/day:
- HL FR 8h settlement: only 3 true data points/day. Running 8× catches each
  settlement with 2.67h margin and allows intraday signal refresh.
- 24×/day would be redundant (same data after settlement, wasted API calls).
- K283 spec said "8h granularity" — 8 invocations aligns with 3h intervals.

### com.cryptolab.k302a-satellite.plist

**Path:** `~/Library/LaunchAgents/com.cryptolab.k302a-satellite.plist`
**Cadence:** 8×/day — same as k280-live (HH:05 at 0,3,6,9,12,15,18,21)
**ProgramArguments:** `/bin/sh -c 'python k302a_satellite_fetch.py && python k302a_satellite_run.py'`
**RunAtLoad:** false
**Logs:** `logs/k302a-satellite.log` / `logs/k302a-satellite.err`

Rationale: PAXG/SPX settle hourly, so any 3h-interval cadence is sufficient.
Aligning with k280-live ensures both dashboards are synchronized.

### com.cryptolab.hl-predicted-monitor.plist

**Path:** `~/Library/LaunchAgents/com.cryptolab.hl-predicted-monitor.plist`
**Cadence:** StartInterval 300 (every 5 minutes = 288 polls/day)
**ProgramArguments:** direct python invocation (no --loop flag)
**RunAtLoad:** true (collects first snapshot immediately on load)
**Logs:** `logs/hl-predicted-monitor.log` / `logs/hl-predicted-monitor.err`

Rationale for StartInterval vs KeepAlive:
- Script says "Usage: python3 hl_predicted_fr_monitor.py" (single-shot default)
- Script comment on --loop says "use launchctl instead" — explicit guidance
- StartInterval 300 is the standard macOS launchd pattern for periodic jobs
- If script crashes, launchd restarts it after 300s (self-healing)

---

## Phase 3: HTML and Runbook Corrections

### report.html changes (Live Monitoring section only)

| Element | Before | After |
|---------|--------|-------|
| `K280 main` badge | `lm-badge-active` / "ACTIVE" | `lm-badge-scaffold` / "SCAFFOLD-READY" |
| `K302a satellite` badge | `lm-badge-ready` / "DEPLOY-READY" | `lm-badge-scaffold` / "SCAFFOLD-READY" |
| `K304 HL mon` badge | `lm-badge-ready` / "DEPLOY-READY" | `lm-badge-scaffold` / "SCAFFOLD-READY" |
| `K200 HLP` badge | `lm-badge-active` / "ACTIVE" | `lm-badge-deprecated` / "NO SCRIPT" |
| CSS | no `.lm-badge-scaffold` class | Added `.lm-badge-scaffold` (blue/info color) |
| New block | none | K310 activation notice card with load commands |

The banner timestamp was NOT modified (per task instructions).

### docs/k302a_runbook.md changes

Appended **§12 K310 Plist Deployment Instructions** covering:
- Background context (why prior waves were inaccurate)
- Table of plist files created
- Pre-activation checklist (manual script test commands)
- Load commands block
- Log monitoring commands
- Unload/disable commands
- HLP monitor gap note

---

## Phase 4: Lessons Learned

### Why prior waves marked daemons "ACTIVE" without verification

1. **No verification step in prior wave templates.** Waves K283/K289/K304/K305 created
   scripts and documented them as "ACTIVE" / "DEPLOY-READY" in HTML summaries without
   running `launchctl list` to confirm actual daemon loading.

2. **Confusing plist creation with plist loading.** A plist file at `~/Library/LaunchAgents/`
   is NOT active until explicitly `launchctl load`ed. Prior waves may have intended to
   create the files but the creation step was skipped or not verified.

3. **Self-referential HTML as source of truth.** Subsequent waves read the HTML status
   badges as ground truth rather than querying `launchctl`. Once an incorrect "ACTIVE"
   label appeared, later waves preserved it.

4. **Absent launchctl verification in CI/commit step.** No existing workflow checks
   `launchctl list` after claiming daemon status changes. This should be added as a
   standard step in any future wave that touches daemon infrastructure.

### Recommended practice going forward

- Any wave that claims a daemon is "ACTIVE" MUST run `launchctl list | grep <label>`
  and include the output in its deliverables.
- HTML badge values should map to a defined vocabulary:
  - `ACTIVE` = verified by launchctl (must show PID > 0 or status 0)
  - `SCAFFOLD-READY` = plist staged at ~/Library/LaunchAgents, NOT yet loaded
  - `DEPLOY-READY` = code/scripts verified, plist NOT yet written
  - `DEPRECATED` = intentionally disabled

---

## Deliverables Summary

| Deliverable | Path | Status |
|------------|------|--------|
| K280 plist | `~/Library/LaunchAgents/com.cryptolab.k280-live.plist` | Created |
| K302a plist | `~/Library/LaunchAgents/com.cryptolab.k302a-satellite.plist` | Created |
| HL monitor plist | `~/Library/LaunchAgents/com.cryptolab.hl-predicted-monitor.plist` | Created |
| Wave report | `wave_k310_plist_deploy.md` | This file |
| JSON metadata | `wave_k310_plist_deploy.json` | Created |
| HTML corrections | `report.html` Live Monitoring section | Corrected |
| Runbook update | `docs/k302a_runbook.md` §12 | Appended |
| launchctl load | — | NOT executed (awaiting user) |

---

*Wave K310 complete — 2026-05-25 14:16 JST*

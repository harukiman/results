# Wave K415 — v6.15a/b Activation Pathway Scaffold

**Date:** 2026-05-29 08:06 JST  
**Status:** COMPLETE  
**K400 Decision:** CONDITIONAL_ACCEPT (Ondo USDY 5-10% sleeve, non-US residency required)

---

## Executive Summary

K415 prepares the complete v6.15a/b activation pathway so the user can act immediately upon confirming non-US residency status. All scaffolding is in place; no on-chain action is taken.

**Default recommendation: v6.15b** (10% USDY, HL exposure 47.5% — first time below 50%).

---

## Deliverables

### 1. `scripts/k415_usdy_sleeve_run.py` (NEW)
Paper-trade scaffold for USDY virtual sleeve:
- EMERGENCY flag check at startup (exits safely, notes USDY hold guidance)
- APY fetch from DefiLlama yields API (USDY pool), fallback to 4.5% constant
- Price fetch from Ondo public API, fallback to computed NAV from APY
- Daily PnL: `sleeve_pct × AUM × daily_apy / 365`
- Lock status tracking: NOT_PURCHASED / LOCKED / LIQUID
- v6.15a vs v6.15b variant comparison table
- Opportunity cost analysis (yield cost vs HL exposure reduction)
- Dashboard: `data/k415_usdy_dashboard.json`
- K339 REPO_ROOT pattern, stdlib only, no new packages

### 2. `com.cryptolab.k415-usdy.plist` (NEW, gitignored)
launchd plist for daily execution:
- StartCalendarInterval: 06:00 JST (21:00 UTC)
- RunAtLoad: false (per K310 lesson)
- Gitignored per `com.cryptolab.*.plist` pattern in .gitignore

### 3. `scripts/verify_deployment_status.py` (UPDATED)
14th daemon added to REGISTRY:
- Label: `com.cryptolab.k415-usdy`
- expected_html_status: `SCAFFOLD-READY`
- Scripts: `scripts/k415_usdy_sleeve_run.py`

### 4. `scripts/emergency_hl_exit.py` (UPDATED)
K415 `--include-usdy` flag added:
- Prints USDY hold guidance during emergency exit
- Documents 1-business-day redemption limitation
- Explains T-bill safe-harbor rationale
- Does NOT submit redemption to Ondo (intentional — hold is recommended)
- Epilog and dry-run section both include USDY note

### 5. `docs/k302a_runbook.md` (UPDATED)

**§14.9 added** — USDY Sleeve Emergency Guidance (K415):
- Comparison table: USDY vs HL/Bybit emergency properties
- Recommended sequence: exit HL+Bybit, HOLD USDY
- CLI usage for --include-usdy flag

**§21 added** (8 subsections):
- §21.1 v6.15a vs v6.15b selection guide (table + recommendation)
- §21.2 USDY procurement steps (5 steps: non-US confirm → Ondo KYC → fund → purchase)
- §21.3 40-day lock bridge plan (DO/DO NOT during lock)
- §21.4 3-day activation playbook (Day 0/1/2/3-40/41+)
- §21.5 K415 daemon configuration (activation commands, dashboard update)
- §21.6 USDY redemption procedure (normal + emergency guidance + limitation)
- §21.7 Rollback to v6.13d (steps + triggers)
- §21.8 References table (K355, K357, K400, K415)

### 6. `report.html` (UPDATED)
- Live Monitoring: K415 USDY row added (14th daemon, SCAFFOLD-READY badge)
- Ticker banner: updated to "K415 activation pathway documented"
- Footer: timestamp updated, 14 daemons total

---

## v6.15a vs v6.15b Selection

| Criterion | v6.15a | v6.15b (DEFAULT) |
|---|---|---|
| USDY sleeve | 5% | **10%** |
| K297' weight | 15% | **10%** |
| HL exposure | 52.5% | **47.5%** |
| Yield cost | ~−0.28pp/yr | ~−0.55pp/yr |
| HL < 50% milestone | No | **YES (first time)** |

Recommendation: **v6.15b** — concentration risk reduction (10pp HL reduction) outweighs yield cost (0.55pp/yr).

---

## Activation Timeline

Once user confirms non-US residency:

```
Day 0:  Non-US confirm → Ondo register → USDY purchase
Day 1:  Receive USDY → K297' weight reduction → K415 daemon active
Day 2:  Verification → HL exposure confirmed
Day 3-40: v6.15 LIVE, USDY locked (earning ~4.5% APY)
Day 41+: USDY liquid → v6.15 fully operational
```

---

## Daemon Registry

Total daemons after K415: **14**
- K415 USDY: SCAFFOLD-READY (14th daemon)
- 0 mismatches with HTML expected

---

## Constraints Respected

- No on-chain USDY purchase (user action only)
- K280/K344 production scripts untouched
- No new packages (stdlib + requests already present)
- K339 security pattern throughout
- Paper-trade scaffold only

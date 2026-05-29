# Wave K444 — Loss Harvesting Automation + Tax-Aware Tracking (18th Daemon)

**Date:** 2026-05-29 JST
**Status:** SCAFFOLD-READY
**Daemon:** 18th (annual Dec 28 06:00 JST cron)
**INFORMATIONAL ONLY — consult licensed tax advisor before acting**

---

## Executive Summary

K444 implements the infrastructure identified in K442 to retain $2–41K/yr in after-tax
profit through systematic loss harvesting at year-end. This is a pure infrastructure
wave — no strategy changes, no trade execution.

**K442 finding:** crypto derivatives generate extremely high realization event counts
(K376 alone: ~10,733/yr), making tax-loss harvesting material even at moderate AUM.

---

## Deliverables

| File | Purpose |
|------|---------|
| `scripts/loss_harvester.py` | Main script (~250 LOC, K339 REPO_ROOT) |
| `com.cryptolab.loss-harvester.plist` | Annual cron plist (gitignored) |
| `scripts/verify_deployment_status.py` | 18th daemon entry added to REGISTRY |
| `data/portfolio_aum_state.json` | Tax fields extended (7 new fields) |
| `data/loss_harvester_dashboard.json` | HTML widget data (initial) |
| `docs/k302a_runbook.md` | §28 added (loss harvesting playbook) |
| `report.html` | K444 daemon row + YTD tax widget + banners |

---

## Phase 11 Test Results

| Input | Value |
|-------|-------|
| Realized gains YTD | $1,000,000 |
| Realized losses YTD | $50,000 |
| Net taxable | $950,000 |
| Tax rate | 37% |
| Expected liability | $351,500 |
| Actual (computed) | $351,500 |
| **PASS** | YES |

---

## Estimated Tax Savings (INFORMATIONAL ONLY)

Based on K440 profit projections and K442 framework. Harvestable loss = ~5% of gross gains.

### $10M AUM (~$1.72M/yr gross gains)
- Harvestable loss estimate: ~$86,000
- US (37% STCG): **~$32K/yr saved**
- Japan (55%): **~$47K/yr saved**
- Singapore (0% CGT): **$0** (no CGT on investment gains)

### $50M AUM (~$6.0M/yr gross gains)
- Harvestable loss estimate: ~$300,000
- US (37% STCG): **~$111K/yr saved**
- Japan (55%): **~$165K/yr saved**
- Singapore (0% CGT): **$0**

---

## Event Taxonomy (K442)

| Strategy | Events/yr | Tax category |
|----------|-----------|-------------|
| K208 8h FR cycle | ~1,095 | Short-term capital (most jurisdictions) |
| K297' SPX filter | ~26/coin | Short-term capital |
| K376 momentum 4h | ~10,733 | Short-term capital |
| sUSDe yield | Continuous | Ordinary income (separate) |

---

## Architecture

```
scripts/loss_harvester.py
  load_taxable_events_ytd()      -> list[dict]
  compute_realized_gains_ytd()   -> float
  compute_realized_losses_ytd()  -> float
  identify_harvest_candidates()  -> list[dict]
  estimate_tax_liability(rate)   -> float
  generate_annual_report()       -> dict
  record_realization_event(pnl, strategy, coin)  [K429 integration hook]
  write_dashboard()              -> None
  set_user_tax_rate(rate, juris) -> None
```

**AUM state tax fields (Phase 4):**
- `taxable_events_ytd` — running event count
- `estimated_realized_gain_ytd_usd` — running YTD gains
- `estimated_realized_loss_ytd_usd` — running YTD losses
- `user_tax_rate_pct` — user-set via `--set-rate` or TAX_RATE_PCT env
- `estimated_tax_liability_usd` — recomputed on each update
- `loss_harvesting_opportunities` — list of currently losing positions
- `jurisdiction` — user-set (US_STCG / JP / SG / DE / UNKNOWN)
- `tax_year_start` — resets each Jan 1

---

## Activation

```bash
# Step 1: Set tax rate (consult advisor first)
python3 scripts/loss_harvester.py --set-rate 37 --set-jurisdiction US_STCG

# Step 2: Check status
python3 scripts/loss_harvester.py --status

# Step 3 (optional): Load annual cron
cp com.cryptolab.loss-harvester.plist ~/Library/LaunchAgents/
launchctl load ~/Library/LaunchAgents/com.cryptolab.loss-harvester.plist
```

---

## References

- K442: Loss harvesting analysis ($2–41K/yr estimate, jurisdiction table)
- K376: Momentum strategy (highest event count)
- K429: AUM tracking infrastructure
- K340/K339: Security rule (REPO_ROOT pattern)
- §28: This wave's runbook section

---

*INFORMATIONAL ONLY — 2026-05-29 — Wave K444*

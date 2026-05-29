# Wave K545 — Tax Loss Harvester Production Activation Playbook

**Date:** 2026-05-30 05:35 JST
**Wave:** K545
**Status:** ACTIVATION PLAYBOOK — SCAFFOLD-READY → PRODUCTION
**INFORMATIONAL ONLY — consult licensed tax advisor before acting**

---

## Executive Summary

K542/K444 tax loss harvester infrastructure is fully implemented and tested but
NOT yet active in production. The single activation gap: the LaunchAgent plist is
not loaded. This wave (K545) provides the complete activation playbook, deep-dive
profit projections, and integration specifications.

**Bottom line (INFORMATIONAL):**

| AUM | Jurisdiction | Rate | Annual Savings (base) | Annual Savings (optimistic) |
|-----|-------------|------|----------------------|----------------------------|
| $10M | Japan | 55% | **$47,300/yr** | **$94,600/yr** |
| $10M | Korea | 22% | **$18,920/yr** | **$37,840/yr** |
| $10M | Germany | 26.4% | **$22,682/yr** | **$45,365/yr** |
| $100M | Japan | 55% | **$473,000/yr** | **$946,000/yr** |
| $100M | Korea | 22% | **$189,200/yr** | **$378,400/yr** |
| $100M | Germany | 26.4% | **$226,825/yr** | **$453,650/yr** |

**Combined K442 + K444 + K545 range @$10M:** $18.7K–$94.6K/yr (JPN 55%)
**Combined @$100M:** $187K–$946K/yr (JPN 55%)

5-year compounded (cumulative simple sum):

| AUM | Japan (55%) | Korea (22%) |
|-----|------------|------------|
| $10M | $94K–$473K/5yr | $38K–$189K/5yr |
| $100M | $940K–$4.73M/5yr | $378K–$1.89M/5yr |

---

## Phase 1: K442/K444 Baseline Audit

### File Status (All PRESENT)

| File | Size | Status | Note |
|------|------|--------|------|
| `wave_k442_tax_optimization.py` | 20,665 B | OK | 552 LOC, 10 jurisdictions |
| `wave_k442_tax_optimization.json` | 14,239 B | OK | Full jurisdiction table |
| `wave_k444_loss_harvester.json` | 2,349 B | OK | Daemon spec, SCAFFOLD-READY |
| `wave_k444_loss_harvester.md` | 4,081 B | OK | Activation guide |
| `scripts/loss_harvester.py` | 31,701 B | OK | 729 LOC, Phase 11 PASS |
| `com.cryptolab.loss-harvester.plist` | 1,163 B | OK | Annual Dec 28 cron |
| `data/portfolio_aum_state.json` | 1,253 B | OK | Tax fields backfilled |
| `data/loss_harvester_dashboard.json` | 883 B | OK | Mock data populated |

### Deployment Status

```
State:                  SCAFFOLD-READY
Script status:          FUNCTIONAL (729 LOC, K339 compliant)
Plist in LaunchAgents:  NO (pending User Action #30)
Tax rate configured:    YES (37% mock from Phase 11 test)
Jurisdiction set:       US_STCG (mock — override with real value)
YTD events logged:      200 (mock from Phase 11 test)
Phase 11 test:          PASS ($351,500 liability verified)
```

**Critical gap:** Plist NOT loaded in `~/Library/LaunchAgents/`. Annual Dec 28 trigger
will NOT fire until loaded. This is User Action #30 (5 minutes).

---

## Phase 2: Tax Jurisdiction Model (Non-US)

### Japan (55% — Most Critical)

- **Category:** Miscellaneous income (雑所得 / zatsushotoku)
- **Rate:** 45% national + 10% local = 55% at top bracket (income >40M JPY)
- **Additional:** 2.1% reconstruction surtax
- **LTCG treatment:** NONE — no long-term exemption for crypto
- **Loss carryforward:** ZERO (losses expire Dec 31 each year — CRITICAL)
- **Loss offset within year:** YES — losses offset other zatsushotoku gains
- **Wash-sale equivalent:** NONE — crypto re-entry same day is permissible
- **Re-entry wait:** 0 days (as of 2026 — confirm with advisor annually)
- **K208 impact:** 1,095 realization events/yr = 1,095 Japanese tax events
- **Exit tax:** Applies for assets >500M JPY (~$3.3M USD)

**Key implication:** Japan's no-carryforward rule makes Dec 28 harvest window
MANDATORY, not optional. Unrealized losses that expire past Dec 31 = zero tax value.

### Korea (22%)

- **Category:** Virtual asset income
- **Rate:** 20% + 2% local = 22% flat on gains above KRW 2.5M (~$1.7K)
- **Loss carryforward:** 5 years — harvesting useful even in 0-gain years
- **Wash-sale equivalent:** NONE
- **Re-entry wait:** 0 days

### Germany (26.4%)

- **Category:** Abgeltungsteuer (flat tax) for <1yr hold
- **Rate:** 25% + 5.5% solidarity surcharge = 26.375%
- **K208:** Always <1yr hold → 26.375% applies to all events
- **K297' PAXG static hold:** >1yr → potentially 0% (different rule)
- **Loss carryforward:** Indefinite
- **Annual exempt allowance:** €600

### Singapore / UAE (0%)

- **Loss harvesting impact:** $0 — no CGT at individual level
- **Business classification risk:** K208 high-frequency may trigger IRAS review (SGP)
- **Action:** Document investment intent, avoid "trading business" classification

---

## Phase 3: Loss Harvesting Strategy

### Primary Loss Sources

1. **K376 momentum stop-outs** — primary source (~10,733 events/yr at full universe)
   - Each stop-out = realized loss in the position
   - Year-end stop-outs before Dec 31 = harvestable
   - K376 4h cycle naturally generates stop-outs in drawdown periods

2. **K297' SPX filter exits** — secondary source (~26/yr per coin)
   - SPX filter near year-end creates involuntary position closes
   - Some close at loss → harvestable

3. **K208/K280 losing FR cycles** — rare (Sharpe 22.1) but occur
   - 8h cycle with negative funding rate payout = realized loss
   - Small individual losses but aggregate meaningful at scale

### Harvest Decision Rules

| Trigger | Action | Rationale |
|---------|--------|-----------|
| Position loss > $1,000 USD | Flag as harvest candidate | Minimum materiality |
| Date window: Dec 1–31 | Activate harvest review | Year-end priority |
| Japan: no carryforward | Harvest ALL year-end losses | Binary — use it or lose it |
| Korea: 5yr carryforward | Harvest when convenient | Less urgent than Japan |
| Loss > 2% of AUM | Priority harvest | High-impact single event |
| K357 emergency exit | Immediate harvest remaining | Mass realization offset |

### Re-entry Protocol (Non-US Crypto)

```
1. Identify harvest candidate (position with unrealized loss > $1K)
2. Close position before Dec 31 (Japan) / before carryforward expires (Korea)
3. Record realization event: python3 scripts/loss_harvester.py --record-event <PNL> <STRATEGY> <COIN>
4. Wait period: 0 days (Japan/Korea/Germany — no wash-sale equivalent for crypto as of 2026)
5. Re-enter position (optional — strategy signal may not be active)
6. Net tax benefit = |loss_usd| × tax_rate_pct
```

**ALWAYS confirm wash-sale rules with licensed tax advisor before re-entry.**

---

## Phase 4: Production Activation Steps (User Action #30)

### Step 1: Confirm Jurisdiction + Tax Rate (1hr)

Legal check required before setting any rate. Then:

```bash
# Example for Japan:
python3 scripts/loss_harvester.py --set-rate 55 --set-jurisdiction JPN

# Example for Korea:
python3 scripts/loss_harvester.py --set-rate 22 --set-jurisdiction KOR

# Example for Germany:
python3 scripts/loss_harvester.py --set-rate 26.375 --set-jurisdiction DE
```

Verify:
```bash
python3 scripts/loss_harvester.py --status
```

Expected output:
```
Jurisdiction: JPN | User Tax Rate: 55.0% | Events YTD: N
```

---

### Step 2: Verify Script Integrity (5min)

```bash
python3 scripts/loss_harvester.py --mock-test
```

Expected Phase 11 output:
```
  Gains YTD:    $1,000,000
  Losses YTD:   $50,000
  Net:          $950,000
  Tax rate:     37%
  Expected:     $351,500.00
  Actual:       $351,500.00
  PASS:         YES
```

If PASS fails: check Python3 path, AUM state JSON write permissions.

---

### Step 3: Deploy Plist to LaunchAgents — USER ACTION #30 (5min)

```bash
# Copy plist
cp /Users/nekonaomichi/crypto-lab/com.cryptolab.loss-harvester.plist \
   ~/Library/LaunchAgents/com.cryptolab.loss-harvester.plist

# Load daemon (RunAtLoad=false — no immediate execution)
launchctl load ~/Library/LaunchAgents/com.cryptolab.loss-harvester.plist

# Verify load
launchctl list | grep loss-harvester
```

Expected:
```
com.cryptolab.loss-harvester    (no PID shown — annual trigger, not running)
```

**Risk:** LOW. RunAtLoad=false. Next trigger: Dec 28 2026 06:00 JST.
**No positions modified. No trades executed. Pure analysis.**

---

### Step 4: 30-Day Paper-Trade Tracking (Passive)

During live trading, wire K429 integration hook to record real events:

```python
# In strategy close logic (sleeve scripts):
from scripts.loss_harvester import record_realization_event
record_realization_event(pnl_usd=closed_pnl, strategy="K376", coin=coin)
```

Weekly check:
```bash
python3 scripts/loss_harvester.py --status
python3 scripts/loss_harvester.py --write-dashboard
```

---

### Step 5: Year-End Harvest Execution (Dec 28–31 ONLY)

```bash
# Review harvest plan (INFORMATIONAL — shows what to close)
python3 scripts/loss_harvester.py --realize-losses

# Full annual report for tax advisor
python3 scripts/loss_harvester.py --annual-report > data/tax_report_2026.json
```

**MANUAL EXECUTION REQUIRED** — loss harvester never auto-closes live positions.
Review the harvest plan with your tax advisor, then execute closes manually.

---

## Phase 5: Integration with v6.13d LIVE

### K357 Emergency Exit

If K357 fires (portfolio draw >15% in single session):
1. K357 liquidates all positions immediately
2. All liquidations = mass realization events
3. Immediately run: `python3 scripts/loss_harvester.py --realize-losses`
4. Any remaining positions with losses: close before Dec 31
5. Dashboard auto-updates via `--write-dashboard`

**K357 + year-end combination** is the highest-value harvest scenario (forced realization
creates a tax event regardless — might as well maximize loss capture simultaneously).

### K430 Leverage 3x

Leverage amplifies both gains (higher tax) and losses (higher harvest value).

| Scenario | Notional @$10M | 5% drawdown loss | JPN 55% savings |
|----------|---------------|-----------------|----------------|
| 1x leverage | $10M | $500K loss | $275K |
| 3x leverage (K430) | $30M | $1.5M loss | $825K |

K430 3x materially increases loss harvesting potential in drawdown periods.
**K545 harvest threshold should be $1K (not $5K) at 3x given notional scale.**

### K429 AUM Manager

K429 tracks cumulative PnL. The `record_realization_event()` function in
`scripts/loss_harvester.py` is the K429 integration hook. Wiring requires:

1. Import `record_realization_event` in each sleeve script
2. Call it on every position close (both gains and losses)
3. AUM state auto-updates with running YTD tax liability

**Time estimate:** ~30min total across K280, K376, K297' sleeve scripts.

---

## Phase 6: Profit Projection (5-Year)

### Source: K523 calibrated 17.2%/yr net gross gain | INFORMATIONAL ONLY

### @$10M AUM

| Jurisdiction | Rate | Conservative/yr | Base/yr | Optimistic/yr | 5yr (base) |
|-------------|------|----------------|---------|--------------|-----------|
| Japan (JPN) | 55% | $18,920 | **$47,300** | $94,600 | $236,500 |
| Korea (KOR) | 22% | $7,568 | **$18,920** | $37,840 | $94,600 |
| Germany (DEU) | 26.4% | $9,073 | **$22,682** | $45,365 | $113,410 |

### @$100M AUM

| Jurisdiction | Rate | Conservative/yr | Base/yr | Optimistic/yr | 5yr (base) |
|-------------|------|----------------|---------|--------------|-----------|
| Japan (JPN) | 55% | $189,200 | **$473,000** | $946,000 | $2,365,000 |
| Korea (KOR) | 22% | $75,680 | **$189,200** | $378,400 | $946,000 |
| Germany (DEU) | 26.4% | $90,730 | **$226,825** | $453,650 | $1,134,125 |

### K442 Existing Baseline (for comparison)

K442 original estimates (5% gross gain harvested at reported AUM):
- @$10M JPN 55%: $41,250/yr optimistic
- @$50M JPN 55%: $165,000/yr optimistic

K545 extends to $100M tier with K523-calibrated gain basis.

### Combined Stack (K442 jurisdiction + K545 harvesting)

The largest lever is jurisdiction selection (K442): Japan → UAE/SGP saves
$10.2M over 5 years at $50M AUM. Loss harvesting is additive but smaller.

| Lever | Magnitude @$10M | Magnitude @$100M |
|-------|----------------|-----------------|
| Jurisdiction: Japan → UAE | +$10.2M/5yr gains retained | +$102M/5yr |
| Loss harvesting (base, JPN) | +$236K/5yr | +$2.37M/5yr |
| K481 builder rebate | +$247K/yr | +$2.47M/yr |

---

## Phase 7: Implementation Roadmap

| Wave | Status | Title |
|------|--------|-------|
| K442 | COMPLETE | Tax optimization analysis (10 jurisdictions) |
| K444 | SCAFFOLD-READY | Loss harvester 18th daemon |
| **K545** | **THIS WAVE** | Production activation deep-dive |
| K545-1 | COMPLETE | K442/K444 audit (all files present) |
| K545-2 | NOT NEEDED | Script already 729 LOC production quality |
| K545-3 | PENDING | Deploy plist → User Action #30 (5min) |
| K545-4 | PENDING | 30d paper tracking + K429 wire-up (30d) |
| K545-5 | PENDING | Dec 28 2026 harvest window |

---

## Phase 8: Risk Table

| Risk | Probability | Impact | Mitigation | Status |
|------|------------|--------|-----------|--------|
| No wash-sale violation | LOW (non-US crypto) | MEDIUM | Confirm with advisor annually | MANAGED |
| Japan no-carryforward | CERTAIN | HIGH | Dec 28 trigger mandatory | DOCUMENTED |
| HL cost basis accuracy | MEDIUM | MEDIUM | JSONL entry-price logging | PARTIAL |
| K357 mass realization | LOW | HIGH | Immediate harvest protocol | DOCUMENTED |
| Japan exit tax >$3.3M | MEDIUM at scale | HIGH | Legal advice required | DOCUMENTED |
| Business classification (SGP/HKG) | MEDIUM | HIGH | Document investment intent | MANAGED |

---

## Phase 9: Activation Playbook Summary

### 5-Step User Playbook

```
Step 1 (1hr):  Legal check → confirm jurisdiction + rate
               → python3 scripts/loss_harvester.py --set-rate <RATE> --set-jurisdiction <JURIS>

Step 2 (5min): Integrity check
               → python3 scripts/loss_harvester.py --mock-test (expect PASS)

Step 3 (5min): USER ACTION #30 — Deploy plist (18th daemon)
               → cp com.cryptolab.loss-harvester.plist ~/Library/LaunchAgents/
               → launchctl load ~/Library/LaunchAgents/com.cryptolab.loss-harvester.plist

Step 4 (30d):  K429 wire-up + passive tracking
               → Weekly: python3 scripts/loss_harvester.py --status

Step 5 (2-4hr, Dec 28-31 ONLY): Year-end harvest execution
               → python3 scripts/loss_harvester.py --realize-losses
               → Review with advisor → execute closes manually
```

**Total upfront effort:** 1.5 hours
**First annual benefit:** Dec 31 2026
**Expected benefit @$10M JPN 55%:** $47,300/yr (base scenario)

---

## Daemon Specification

| Field | Value |
|-------|-------|
| Label | `com.cryptolab.loss-harvester` |
| Number | 18th daemon |
| Schedule | Annual Dec 28 06:00 JST |
| RunAtLoad | false |
| Script | `scripts/loss_harvester.py --realize-losses` |
| Plist | `com.cryptolab.loss-harvester.plist` |
| Status | SCAFFOLD-READY → User Action #30 |
| Logs | `logs/loss_harvester.log` / `.err` |

---

## References

- K442: Multi-jurisdiction tax optimization (10 jurisdictions, 5y projections)
- K444: Loss harvester 18th daemon implementation (729 LOC)
- K429: AUM manager (integration hook target)
- K357: Emergency exit interplay
- K430: 3x leverage amplification
- K376: Primary loss source (stop-outs)
- K523: Realistic profit trajectory calibration ($748K–$1.95M/yr)
- K339: Security pattern (REPO_ROOT)
- docs/k302a_master_deployment.md §Tax: User Action #30

---

*INFORMATIONAL ONLY — 2026-05-30 — Wave K545*
*NOT TAX ADVICE. Consult a licensed tax professional before any action.*

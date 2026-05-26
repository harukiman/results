# Wave K356 — HL HIP-4 Prediction Market Polling Daemon Scaffold

**Date:** 2026-05-27
**Status:** SCAFFOLD-READY
**K353 verdict:** MONITOR — calibration data collection required
**K368 target:** 2026-06-10 (2-week collection window)

---

## Context

K353 found HL HIP-4 prediction markets live and accessible (no auth). Key findings:
- 22 active outcomes across 11 markets (CPI, FOMC, BTC daily binary, UCL final, etc.)
- Endpoints functional: `outcomeMeta`, `allMids` (`#XXXX` keys), `l2Book`
- MONITOR verdict: calibration bias >3% or cross-venue >2% would trigger trade prototype

K356 scaffolds the polling daemon for 2-week data collection feeding K368 calibration analysis.

---

## Deliverables

| File | Status | Description |
|---|---|---|
| `scripts/hl_hip4_monitor.py` | NEW | Single-shot polling daemon (launchd scheduled) |
| `com.cryptolab.hl-hip4-monitor.plist` | NEW | launchd plist (repo root, gitignored) |
| `scripts/verify_deployment_status.py` | UPDATED | Registry entry added |
| `report.html` | UPDATED | Live Monitoring daemon row added |
| `wave_k356_hip4_scaffold.md` | NEW | This file |
| `wave_k356_hip4_scaffold.json` | NEW | Machine-readable metadata |

---

## Activation (manual, after user verification)

```bash
# Step 1: verify script works
python3 scripts/hl_hip4_monitor.py --dry-run

# Step 2: copy plist to LaunchAgents
cp /Users/nekonaomichi/crypto-lab/com.cryptolab.hl-hip4-monitor.plist ~/Library/LaunchAgents/

# Step 3: load daemon
launchctl load ~/Library/LaunchAgents/com.cryptolab.hl-hip4-monitor.plist

# Step 4: verify
launchctl list | grep hip4
```

**Deactivation:**
```bash
launchctl unload ~/Library/LaunchAgents/com.cryptolab.hl-hip4-monitor.plist
```

---

## Script Technical Notes

- **REPO_ROOT pattern (K339):** `Path(__file__).resolve().parent.parent` — no `/Users/` literals
- **Single-shot:** no while-loop; launchd StartInterval=300 (5 min) manages cadence
- **Error handling:** all exceptions caught, written to `logs/hl_hip4_monitor.err`, `exit 0` to prevent launchd throttling
- **Parquet schema (18 cols):**
  - `ts_ms` int64, `coin` object (e.g. `#1010`), `outcome_id` int64, `side` int64 (0=Yes/1=No)
  - `side_name` object, `outcome_name` object, `question_name` object, `description` object
  - `mid_price` float64 (binary probability), `resolved` bool, `resolved_outcome` float64
  - `best_bid`, `best_ask`, `spread`, `spread_pct`, `bid_depth_1pct`, `ask_depth_1pct` float64
  - `btc_mark` float64 (BTC mark price for daily-binary calibration)
- **Coin key mapping:** `#(outcome_id * 10 + side_index)` e.g. outcome 101 Yes → `#1010`, No → `#1011`
- **l2Book:** fetches top-3 markets by |price - 0.5| (most uncertain = most active); depth within 1% of mid
- **Snapshot dir:** `cache/hl_hip4_snapshots/hip4_<YYYYMMDD_HHMM>.parquet`

---

## K368 Trigger (Calibration Analysis — target 2026-06-10)

After 2 weeks of data collection (~2026 snapshots at 5-min cadence), run K368 calibration analysis:

### BTC Daily Binary Calibration

The `Recurring` outcomes (questions 20+) track BTC price vs thresholds daily.
- Load all snapshots from `cache/hl_hip4_snapshots/`
- For each resolved BTC binary outcome:
  - Extract predicted P (mid_price at resolution_time - 1h) vs realized outcome (Yes=1/No=0)
  - Compute **Brier score**: `BS = mean((P - Y)^2)` (lower = better, perfect = 0)
  - Compute **log loss**: `LL = -mean(Y*log(P) + (1-Y)*log(1-P))`
  - Bin predictions by decile → plot calibration curve (predicted vs realized frequency)

### Decision Gates

| Finding | Threshold | Action |
|---|---|---|
| Systematic bias | \|predicted - realized\| > 3% on average | CALIBRATION BIAS → K369 trade prototype |
| Well-calibrated | Brier score near theoretical minimum, no bias | MONITOR continues, no edge |
| Cross-venue spread | \|HL_price - other_venue\| > 2% for same outcome | ARBITRAGE EDGE → K369 |
| Thin books | Total depth within 1% of mid < $1000 | NOTE: capacity constrained |

### CPI / FOMC Calibration (categorical)

- For question "May CPI year-over-year": 3 outcomes (Below/Exactly/Above 4.3%)
- Predicted probabilities must sum to ~1.0 (check for consistency)
- Compare predicted distribution at T-24h, T-6h, T-1h vs resolution
- If market underweights tail outcomes systematically → potential edge

### Brier Score Reference

- Perfect calibration: BS = 0
- Always predict 0.5: BS = 0.25
- Random coin flip market: BS ≈ 0.25
- Any score < 0.25 suggests some signal; score > 0.20 suggests market is near-uninformative

---

## Plist Notes

launchd does NOT expand `$HOME` in `<string>` tags. Absolute paths `/Users/nekonaomichi/crypto-lab/...`
are used in the plist. The file is gitignored via `com.cryptolab.*.plist` rule (line 42 of `.gitignore`).

---

## Market Snapshot (2026-05-27 07:20 JST)

Active markets at scaffold time:
- **May CPI y/y:** Below 4.3% = 36.8%, Exactly 4.3% = 43.7%, Above 4.3% = 22.9%
- **June FOMC:** Rate change = 3.2%, No Change = 96.9%
- **BTC daily (Recurring, expiry 2026-05-27):** Yes = 4.9%, No = 95.1%
- **UCL Final:** PSG = 57.8%, Arsenal = 42.2%
- **BTC mark at snapshot:** $75,757.5

*CPI resolution date: 2026-06-10 08:30 ET — aligns with K368 calibration target.*

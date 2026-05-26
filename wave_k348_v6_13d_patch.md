# Wave K348 — v6.13d Production Patch

**Date:** 2026-05-27 06:49 JST
**Type:** PRODUCTION PATCH
**Decision Wave:** K346 (v6.13d winner)

## Executive Summary

K346 confirmed v6.13d = K280 75% + K297' 20% + sUSDe OC 5% as the winner
(Sh 25.47, MDD 0.0189%, all §6 gates pass, WF min 22.3). K348 applies the
production patch to all relevant files.

## Status

| Component | Status |
|-----------|--------|
| K297' SPX filter | **LIVE** (SPX_FILTER_ENABLED=True) |
| Weight allocation 75/20/5 | **LIVE** |
| sUSDe OC daemon script | **SCAFFOLD-READY** |
| sUSDe OC plist | **SCAFFOLD-READY** (awaiting launchctl) |
| HTML banner | **UPDATED** (v6.12 → v6.13d) |
| Runbook §13 | **APPENDED** |
| verify_deployment_status.py | **UPDATED** |

## What's LIVE (Script Changes)

1. **scripts/k302a_satellite_run.py** — K297' SPX filter integrated:
   - `SPX_FILTER_ENABLED = True` at module level
   - 5d trend + FR>0 filter in `compute_spx_daily_pnl()`
   - BT_SPX_SH: 5.87 → 12.20, BT_PORT_SH: 10.17 → 18.48
   - K302A_MAIN_WEIGHT: 0.80 → 0.75
   - K302A_SUSDE_WEIGHT = 0.05 (new)
   - BT_COMBINED_SH: 32.59 → 25.47

2. **report.html** — Banner updated to PRODUCTION v6.13d K302a

3. **docs/k302a_runbook.md** — §13 v6.13d Activation Steps appended

4. **scripts/verify_deployment_status.py** — sUSDe OC daemon added to REGISTRY

## What's SCAFFOLD-READY (Awaiting Manual Activation)

5. **scripts/k344_susde_oc_daily_run.py** — sUSDe OC daemon:
   - Fetches DeFiLlama sUSDe APY history
   - OC signal: FULL/HALF/ZERO/SHOCK (30d EMA ±50bps, 7d shock guard)
   - Writes data/k344_susde_dashboard.json + cache/k344_susde_oc_state.parquet
   - K339 compliant (Path(__file__).resolve().parent.parent)

6. **com.cryptolab.susde-oc.plist** — LaunchAgent plist:
   - Gitignored (com.cryptolab.*.plist pattern)
   - RunAtLoad=false — user activates manually
   - Schedule: 00:30 JST daily

### Activation Command
```bash
# Test first
python3 scripts/k344_susde_oc_daily_run.py --dry-run
python3 scripts/k344_susde_oc_daily_run.py

# Then load daemon
cp com.cryptolab.susde-oc.plist ~/Library/LaunchAgents/
launchctl load ~/Library/LaunchAgents/com.cryptolab.susde-oc.plist
```

## Rollback Procedure

1. `SPX_FILTER_ENABLED = False` in scripts/k302a_satellite_run.py
2. Revert `K302A_MAIN_WEIGHT = 0.80`, remove `K302A_SUSDE_WEIGHT`
3. `launchctl unload ~/Library/LaunchAgents/com.cryptolab.susde-oc.plist`
4. `rm ~/Library/LaunchAgents/com.cryptolab.susde-oc.plist`
5. Run `python3 scripts/verify_deployment_status.py` to confirm

## v6.13d vs v6.12 Comparison

| Metric | v6.12 | v6.13d |
|--------|-------|--------|
| K280 weight | 80% | 75% |
| Satellite | K297 (always-on) | K297' (SPX filtered) |
| sUSDe sleeve | — | 5% OC |
| Combined Sh | 32.59 | 25.47 |
| SPX component Sh | 5.87 | 12.20 (+108%) |
| Portfolio Sh | 10.17 | 18.48 (+81.7%) |
| MDD | 0.0202% | 0.0189% |

*K348 Production Patch — 2026-05-27*

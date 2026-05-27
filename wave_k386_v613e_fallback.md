# Wave K386: v6.13e BEAR_1 Fallback Prototype

**Date:** 2026-05-27 | **Status:** COMPLETE | **Wave:** K386

## Executive Summary

K385 identified BEAR_1 scenario (CFTC enforcement vs HyperLiquid, P=15%) requiring a ready fallback deployment. K386 builds the complete prototype: script, plist, dashboard, runbook §18, K357 integration, and HTML monitoring card.

## Architecture Change: v6.13d → v6.13e

| Component | v6.13d | v6.13e | Delta |
|-----------|--------|--------|-------|
| K280 main | 75% | **85%** | +10pp |
| K297' HIP-3 | 20% | **0%** | −20pp (CFTC restricted) |
| BTC/ETH spot | 0% | **10%** | +10pp (new) |
| sUSDe OC | 5% | 5% | unchanged |
| **HL exposure** | **57.5%** | **52.5%** | **−5pp** |
| Combined Sharpe | 25.47 | **22.89** | −2.58 (accepted) |

Interpretation B applied: K297' → 0%, spare 10% → BTC/ETH spot (50/50), K280 boosted to 85%. Total = 100%.

## Deliverables

### Phase 1: `scripts/k386_v613e_fallback_run.py` (NEW)
- Single-shot daemon, K339-compliant (`REPO_ROOT = Path(__file__).resolve().parent.parent`)
- Flag priority: `EMERGENCY_EXIT_TRIGGERED` > `BEAR_1_FALLBACK_ACTIVE` > STANDBY
- STANDBY mode: writes status to `data/v6_13e_fallback_dashboard.json`, exits 0
- ACTIVE mode: fetches BTC/ETH daily prices (Binance public API), computes weighted portfolio PnL, writes ACTIVE dashboard + trade log

### Phase 2: BTC/ETH Spot Signal
- 50/50 BTC + ETH, daily mark-to-market from Binance free klines API
- `urllib.request` (stdlib only) — no new packages
- Fail-open: on API error, sleeve contributes 0 PnL (continues gracefully)

### Phase 3: `data/v6_13e_fallback_dashboard.json` (NEW)
- `fallback_status`: `"STANDBY"` | `"ACTIVE"`
- Full weight spec, HL exposure, trigger conditions, activation/deactivation commands

### Phase 4: `docs/k302a_runbook.md` §18 (NEW)
- Pre-trigger detection (RSS + Discord + manual)
- Day 1/2/3 activation steps with exact commands
- Daemon table during BEAR_1 mode
- Deactivation checklist (K297' restart with K348+G9)
- Dashboard field reference

### Phase 5: K357 Integration — `docs/k302a_runbook.md` §14 update
- §14 now documents two distinct flag files:
  - `EMERGENCY_EXIT_TRIGGERED.flag` → closes ALL positions (catastrophic failure)
  - `BEAR_1_FALLBACK_ACTIVE.flag` → closes K297' only; K280/sUSDe continue

### Phase 6: `scripts/k302a_satellite_run.py` (MODIFIED)
- Added K386 BEAR_1 gate at module top (after imports, before any execution)
- Checks `EMERGENCY_EXIT_TRIGGERED.flag` → exit 0 (highest priority)
- Checks `BEAR_1_FALLBACK_ACTIVE.flag` → prints suspension message, exit 0
- K280 and sUSDe daemons unaffected

### Phase 7: `com.cryptolab.k386-v613e-fallback.plist` (NEW)
- `StartInterval: 14400` (4h, same as K302a)
- `RunAtLoad: false` (K310 convention)
- gitignored; cp to LaunchAgents to activate

### Phase 8: `report.html` (MODIFIED)
- Daemon table: new K386 row with STANDBY badge (turns ACTIVE/red if flag present)
- New widget: BEAR_1 fallback status card
  - Architecture tab (v6.13d vs v6.13e weights)
  - BTC/ETH spot sleeve live prices
  - Activation steps quick-ref
  - Deactivation command
  - JSON-driven: reads `data/v6_13e_fallback_dashboard.json`
- Ticker line: K386 STANDBY announcement

### Phase 9: `scripts/verify_deployment_status.py` (MODIFIED)
- K386 entry added to `REGISTRY`
- `expected_html_status: "SCAFFOLD-READY"` (plist in repo root, not loaded)

## Dry-Run Test

```bash
# Test 1: STANDBY mode
python3 scripts/k386_v613e_fallback_run.py --dry-run
# → Should print: "STANDBY — BEAR_1 flag absent"
# → Should print: "[DRY-RUN] Would write: data/v6_13e_fallback_dashboard.json"

# Test 2: ACTIVE mode (flag, then cleanup)
touch BEAR_1_FALLBACK_ACTIVE.flag
python3 scripts/k386_v613e_fallback_run.py --dry-run
rm BEAR_1_FALLBACK_ACTIVE.flag
# → Should print: "BEAR_1 flag present. Executing v6.13e architecture."

# Test 3: K302a flag gate
touch BEAR_1_FALLBACK_ACTIVE.flag
python3 scripts/k302a_satellite_run.py
rm BEAR_1_FALLBACK_ACTIVE.flag
# → Should print: "K302a satellite skipping execution"

# Test 4: Deployment status
python3 scripts/verify_deployment_status.py
# → K386 entry: SCAFFOLD-READY (0 mismatches if HTML matches)
```

## Constraints Respected

- NO BEAR_1 flag committed (accidental activation prevented)
- K280/K302a/K344 production logic unchanged (only flag-check gates added)
- NO new packages (stdlib `urllib.request` only)
- K339 security rule: `REPO_ROOT = Path(__file__).resolve().parent.parent`

## Next Steps

- **K387/K388 (future):** Automated CFTC/SEC RSS monitor for pre-trigger detection
- **K389 (future):** Delta-neutral hedge for BTC/ETH spot sleeve (Bybit perp short)
- **K357 `--cftc-fallback` flag (future):** Close HIP-3 only (not K280) in emergency_hl_exit.py

---

*K386 Wave complete — 2026-05-27 10:00 JST*

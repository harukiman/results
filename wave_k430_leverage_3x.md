# Wave K430 — K426 3x Leverage IMPLEMENTATION

**Date:** 2026-05-25 | **Status:** SCAFFOLD-READY (PAPER_TRADE, leverage=1.0x safe default)
**Source:** K426 (+$2.2M/yr @ $10M AUM at 3x leverage)

---

## Summary

K430 implements production-grade 3x leverage management for the v6.13d portfolio architecture:
- `scripts/leverage_manager.py` — core leverage API (NEW)
- `scripts/leverage_circuit_breaker.py` — 5-min margin health daemon (NEW, 15th daemon)
- `data/leverage_config.json` — single source of truth for rollout state
- `com.cryptolab.leverage-circuit-breaker.plist` — launchd daemon
- Additive patches to `k280_live_fetch.py`, `k302a_satellite_run.py`, `k376_momentum_run.py`
- `docs/k302a_runbook.md §23` — full rollout + emergency playbook
- `report.html` — banner badge + leverage status card + 15th daemon row

## Expected Impact

| Scenario | Annual P&L |
|----------|-----------|
| Baseline 1x (current) | ~$0.8-1.2M/yr (FR carry only) |
| 3x leverage (K426 target) | +$2.2M/yr incremental |
| Combined | ~$3.0-3.4M/yr @ $10M AUM |

## Rollout Phases

### Phase A: PAPER_TRADE (current, safe default)
- All scripts at `LEVERAGE=1.0` — zero behaviour change
- Verify dashboards show `k430_leverage` field
- Circuit breaker dry-run: `python3 scripts/leverage_circuit_breaker.py --dry-run`
- **Pass criteria:** 7d, no CB alerts

### Phase B: LIVE_1.5X (user advances when ready)
```bash
python3 scripts/leverage_manager.py --advance
cp com.cryptolab.leverage-circuit-breaker.plist ~/Library/LaunchAgents/
export HL_WALLET_ADDRESS=0x<your_wallet>
launchctl load ~/Library/LaunchAgents/com.cryptolab.leverage-circuit-breaker.plist
```
- **Pass criteria:** 7d live, margin < 70%, Sharpe > 20

### Phase C: LIVE_3X (user advances after B passes)
```bash
# Optional: reduce deployment_pct to 0.75 in data/leverage_config.json for headroom
python3 scripts/leverage_manager.py --advance
```

## Circuit Breaker

| Event | Action |
|-------|--------|
| `margin > 80%` | `emergency_reduce_leverage()` → all scripts 1x immediately |
| `margin > 70%` | WARNING in `data/leverage_cb_dashboard.json` |
| `margin ≤ 70%` | OK |

Emergency reduce: `python3 scripts/leverage_manager.py --emergency-reduce`
Restore: `python3 scripts/leverage_manager.py --restore PAPER_TRADE`

## Files Modified

- `scripts/leverage_manager.py` (NEW, ~280 LOC)
- `scripts/leverage_circuit_breaker.py` (NEW, ~180 LOC)
- `data/leverage_config.json` (NEW)
- `com.cryptolab.leverage-circuit-breaker.plist` (NEW, gitignored)
- `scripts/k280_live_fetch.py` — K430 leverage import block (additive)
- `scripts/k302a_satellite_run.py` — K430 leverage import block (additive)
- `scripts/k376_momentum_run.py` — K430 leverage import + SLEEVE_PCT_LEVERAGED (additive)
- `scripts/verify_deployment_status.py` — 15th daemon registry entry
- `docs/k302a_runbook.md` — §23 (3-step rollout, circuit breaker, emergency procedure)
- `report.html` — banner badge, leverage status card, daemon row

## Safety Guarantees

1. **Additive:** Default `LEVERAGE=1.0` at `PAPER_TRADE` — all existing behaviour unchanged
2. **K266 gates:** K426 confirmed all §6 gates pass at 3x
3. **Circuit breaker:** Automatic 1x revert if margin > 80% AUM
4. **No auto-advance:** User must explicitly run `--advance` command for each phase
5. **Rollout history:** All phase transitions recorded in `data/leverage_config.json::rollout_history`

*K430 — 2026-05-25*

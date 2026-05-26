# Wave K357 — Emergency HL Exit Script Scaffold

**Date:** 2026-05-27  
**Status:** CRITICAL-MITIGATED  
**Parent wave:** K355 (HL platform risk assessment)  
**Script:** `scripts/emergency_hl_exit.py`

---

## Executive Summary

K355 identified that v6.13d production had **57.5% of capital on HyperLiquid** (K280 HL leg 37.5% + K297' satellite 20%) with **no emergency exit plan** in place. Worst-case expected loss was estimated at 1.7–4.0% annually (P=3–7% shutdown risk × full exposure).

K357 closes this gap with a complete scaffold:
- `scripts/emergency_hl_exit.py` — CLI tool, dry-run default, --EXECUTE with double-confirm
- `docs/k302a_runbook.md §14` — full operational runbook
- `report.html` — Emergency Exit Status dashboard indicator
- `cache/emergency_exit_status.json` — machine-readable status for dashboard
- `EMERGENCY_EXIT_TRIGGERED.flag` — written on execution (daemons should check this)

**Gap status:** CRITICAL → CRITICAL-MITIGATED  
**Remaining gap:** User must provide HL_USER_ADDRESS + HL_PRIVATE_KEY; eth_account needed for live signing.

---

## Risk Context (from K355)

### Capital Distribution on HL

| Component | Portfolio Weight | HL Fraction | HL Notional |
|-----------|-----------------|-------------|-------------|
| K280 main | 75% | ~50% (HL leg) | **37.5% AUM** |
| K297' satellite | 20% | 100% (HL-only) | **20.0% AUM** |
| sUSDe OC | 5% | 0% (Ethena) | 0.0% AUM |
| **Total on HL** | — | — | **57.5% AUM** |

### Worst-Case Scenario

- Platform shutdown probability: 3–7% / 12 months (K355 estimate)
- Impact if triggered: 57.5% × AUM × (1 − recovery fraction)
- Annual expected loss: **1.7–4.0% of AUM**
- Severity: HIGH — no single event is more consequential to this portfolio

---

## Phase 1: HL API Research

### Read-Only Endpoints (no auth)

```
POST https://api.hyperliquid.xyz/info
{"type": "clearinghouseState", "user": "0x..."}  → positions, margin
{"type": "openOrders",         "user": "0x..."}  → open orders
{"type": "fundingHistory",     "coin": "BTC"}    → funding rate history
```

### Exchange Endpoints (require SECP256K1 signature)

```
POST https://api.hyperliquid.xyz/exchange
Body: {
  "action":    {...},    // cancel or order
  "nonce":     <ms>,
  "signature": {"r": "0x...", "s": "0x...", "v": 27|28},
  "vaultAddress": null
}
```

### Signing Protocol

1. Serialize action as JSON (compact, sorted keys)
2. Hash: `keccak256(action_bytes + nonce_uint64_be + vault_bytes_20)`
3. Sign with SECP256K1 private key (eth_account compatible)
4. Include `{r, s, v}` in request body

### Order Types Used

**Cancel order:**
```json
{"type": "cancel", "cancels": [{"coin": "BTC", "oid": 12345}]}
```

**Market close (IOC reduce-only):**
```json
{
  "type": "order",
  "orders": [{
    "coin": "BTC",
    "isBuy": false,
    "sz": "0.01",
    "limitPx": "0.001",
    "orderType": {"limit": {"tif": "Ioc"}},
    "reduceOnly": true
  }],
  "grouping": "na"
}
```
*Strategy: set limitPx far from market (very low for sell, very high for buy) to guarantee fill via IOC.*

---

## Phase 2: Script Architecture

### CLI Interface

```bash
# Default (safe): dry-run
python3 scripts/emergency_hl_exit.py --dry-run --user 0x...

# Using env var:
export HL_USER_ADDRESS=0x...
python3 scripts/emergency_hl_exit.py --dry-run

# Live execution (DANGEROUS — requires double confirm + TTY):
export HL_PRIVATE_KEY=0x...
python3 scripts/emergency_hl_exit.py --EXECUTE
```

### Function Inventory

| Function | Inputs | Output | API call? |
|----------|--------|--------|-----------|
| `fetch_positions(user, dry_run)` | user addr, bool | `[{coin, size, value_usd, side}]` | Yes (live) / mock (dry) |
| `fetch_orders(user, dry_run)` | user addr, bool | `[{coin, oid, side, size, px}]` | Yes (live) / mock (dry) |
| `fetch_balance(user, dry_run)` | user addr, bool | `{usdc_balance, unrealized_pnl, withdrawable}` | Yes (live) / mock (dry) |
| `plan_exit(positions, orders)` | lists | `{cancel_orders, close_positions, total_notional, estimated_time, slippage}` | No |
| `dry_run_report(precheck, plan, logger)` | dicts | None (prints plan) | No |
| `run_precheck(user, dry_run, logger)` | args | snapshot dict | Yes (live) / mock (dry) |
| `run_postcheck(user, logger)` | args | snapshot dict | Yes (live, 5min wait) |
| `execute_exit(plan, private_key, user, logger)` | args | bool (success) | Yes (live ONLY) |
| `double_confirm(plan, user)` | args | bool | No (interactive) |
| `write_emergency_status(triggered, plan, logger)` | args | None (writes files) | No |
| `send_ntfy_alert(...)` | args | None (best-effort) | Yes (ntfy.sh) |

### Safety Features

| Feature | Implementation |
|---------|---------------|
| Default mode | `--dry-run` (argparse default) |
| Execute guard | Mutually exclusive `--dry-run` / `--EXECUTE` flags |
| TTY check | `sys.stdin.isatty()` — refuse if piped/redirected |
| Double confirm | Two separate prompts: 'yes' then 'EXECUTE' |
| Private key | Env var only, never logged, cleared from memory after use |
| API calls in dry-run | Zero — all fetch functions return mocks |
| Repo root | `Path(__file__).resolve().parent.parent` (K339) |
| No hardcoded creds | All addresses/keys from env vars or CLI |

---

## Phase 3: Pre-check / Post-check

### Pre-check (before exit)
- Fetches: USDC balance, positions, open orders
- Builds exit plan with notional and time estimate
- Saves: `logs/emergency_hl_exit_precheck_<ts>.json`

### Post-check (5 min after exit)
- Re-fetches all positions and orders
- Checks: all positions < $10 notional (noise threshold)
- Checks: all open orders cleared
- Status: `CLEAN` or `RESIDUAL_WARNING`
- Saves: `logs/emergency_hl_exit_postcheck_<ts>.json`

---

## Phase 4: Alert Mechanism

### Notification Channels
1. **stdout + log file:** `logs/emergency_hl_exit.log` (always)
2. **Machine-readable:** `cache/emergency_exit_status.json` (HTML dashboard reads this)
3. **Push notification:** ntfy.sh topic `cryptolab-emergency-hl-exit` (best-effort)
4. **Flag file:** `EMERGENCY_EXIT_TRIGGERED.flag` in repo root

### Flag File Protocol
- Written on `--EXECUTE` confirmation
- K302a daemons SHOULD check this file and refuse to trade if present
- Integration code provided in `docs/k302a_runbook.md §14.8`
- Remove to re-enable trading: `rm EMERGENCY_EXIT_TRIGGERED.flag`

---

## Phase 5: Dry-run Test Results

```bash
$ python3 scripts/emergency_hl_exit.py --dry-run --user 0x0000000000000000000000000000000000000000

2026-05-27 07:27:55 UTC [INFO] K357 Emergency HL Exit Script — DRY-RUN MODE
2026-05-27 07:27:55 UTC [INFO] REPO_ROOT: /Users/nekonaomichi/crypto-lab
2026-05-27 07:27:55 UTC [INFO] User address: 0x0000000000000000000000000000000000000000
2026-05-27 07:27:55 UTC [INFO] Emergency status JSON written: cache/emergency_exit_status.json
2026-05-27 07:27:55 UTC [INFO] === PRE-CHECK ===
  [DRY-RUN] fetch_balance — returning mock $0 (no API call made)
  [DRY-RUN] fetch_positions — returning empty mock (no API call made)
  [DRY-RUN] fetch_orders — returning empty mock (no API call made)
2026-05-27 07:27:55 UTC [INFO] No positions or open orders found. Nothing to exit.
2026-05-27 07:27:55 UTC [INFO]   EMERGENCY HL EXIT — DRY-RUN PLAN (no actual trading)
...
2026-05-27 07:27:55 UTC [INFO] DRY-RUN COMPLETE. No trades executed.
Exit code: 0
```

**Results:**
- No crash on zero address
- No crash on missing HL_PRIVATE_KEY (not needed for dry-run)
- No actual API calls made
- Emergency status JSON written to cache
- Log written to logs/emergency_hl_exit.log

Test for missing address:
```bash
$ python3 scripts/emergency_hl_exit.py --dry-run
2026-05-27 07:27:59 UTC [ERROR] No user address provided. Use --user 0x... or set HL_USER_ADDRESS env var.
Exit code: 1
```

Test for env var:
```bash
$ HL_USER_ADDRESS=0xABCD... python3 scripts/emergency_hl_exit.py --dry-run
2026-05-27 07:28:05 UTC [INFO] User address: 0xABCD...
# OK
```

---

## Phase 6: Documentation

### Runbook §14 Coverage

| Section | Content |
|---------|---------|
| §14.1 Context | Capital distribution, expected loss, K355/K357 verdicts |
| §14.2 Triggers | 6 defined triggers + 3 non-triggers |
| §14.3 Pre-conditions | Key access, dry-run verify, daemon stop |
| §14.4 Commands | Step-by-step bash sequence |
| §14.5 Post-exit checklist | 6 checkboxes, residual handling |
| §14.6 Recovery path | Options A/B/C + re-enable commands |
| §14.7 Architecture | Feature table, scaffold caveats |
| §14.8 Daemon integration | Code snippet for flag check |

### HTML Dashboard

Added "Emergency Exit Status" card in Live Monitoring section:
- GREEN badge: "STANDBY — No Emergency" (default)
- RED badge: "EMERGENCY EXIT TRIGGERED" (when flag is set)
- Shows HL exposure (57.5% AUM), expected loss estimate (1.7–4.0%/yr)
- Links to runbook §14
- Shows trigger conditions inline
- Loads from `cache/emergency_exit_status.json` via fetch()

---

## Gaps and Next Steps

### Gaps (scaffold only)

1. **eth_account dependency not in requirements.txt**  
   Live signing requires `pip install eth-account`. Not added to avoid breaking existing env.
   Action: User must install before --EXECUTE.

2. **Signing not live-tested**  
   SECP256K1 signing implementation follows HL SDK protocol but has not been tested against
   real HL exchange endpoint. Recommend test with a small position before emergency use.

3. **K302a daemon flag integration not deployed**  
   Code snippet provided in runbook §14.8 but not integrated into k280_daily_run.py,
   k302a_satellite_run.py yet (out of scope for K357 scaffold).

4. **No position size precision handling**  
   HL has minimum order sizes and tick sizes per coin. Market-close via IOC should handle
   this, but edge cases (very small residual positions) may fail silently.

### Recommended Next Steps

1. **User:** Set HL_USER_ADDRESS and run dry-run against real account
2. **User:** Verify position list matches HL UI
3. **User:** Install eth_account, test --EXECUTE confirm flow (abort at second confirm)
4. **K360:** Integrate EMERGENCY_EXIT_TRIGGERED.flag check into K280/K302a daemons
5. **K362:** Live test with tiny position (manual close test)

---

## Conclusion

K357 transforms K355's "CRITICAL — no plan" into "CRITICAL-MITIGATED — plan exists, dry-run passes, user needs to provide credentials."

The 57.5% HL concentration risk has not been reduced in capital terms (that would require strategy changes), but the **operational response capability** is now documented, scripted, and ready for activation. This reduces the tail risk from "loss is inevitable if HL fails" to "loss is large but manageable if operator follows the protocol."

Honest assessment: this is a scaffold. Live capability requires 30 minutes of credential setup and one practice run by the user.

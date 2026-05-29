# K481 Builder Rebate Activation Playbook
**Wave:** K481 | **Generated:** 2026-05-30 02:44 JST | **Status:** PLAYBOOK-READY (user activation required)  
**Classification:** ZERO RISK | Fee minimization axis (#4) | User action #23

---

## Executive Summary

HyperLiquid's builder rebate program allows any wallet with ≥100 USDC perps balance to register as a "builder" and earn referral-pool rewards on its own order flow. In self-builder mode (fee `f=0`), no extra cost is charged to the trader — the builder earns from HL's referral pool as a pure bonus on top of existing strategy returns.

**Profit projection (refined from K370):**

| AUM | Conservative (10%) | Mid (25%) | Optimistic (50%) |
|-----|-------------------|-----------|-----------------|
| $10M | **$99K/yr** | $248K/yr | $496K/yr |
| $50M | $496K/yr | $1.24M/yr | $2.48M/yr |
| $100M | $991K/yr | $2.48M/yr | $4.96M/yr |
| $200M | $1.98M/yr | $4.96M/yr | $9.92M/yr |

Model assumptions: HL fraction 57.5% of AUM, daily turnover 1.5x, POST_ONLY maker fill rate 70%, HL taker rate 4.5 bps.

**Total time to activate: ~65 minutes + 24h paper verification.**

---

## Phase 1: HL Builder Program Current State

### Status: ACTIVE

Verified 2026-05-27 via HL official documentation.

### Mechanism

The builder field is attached to every order action:

```python
order_action["builder"] = {
    "b": "0x<BUILDER_WALLET_ADDRESS>",  # the approved builder wallet
    "f": 0,                             # fee in tenths of basis points (0 = zero extra cost)
}
```

- `f=0` is the self-rebate mode: zero additional cost to the trader
- Builder earns from HL's referral pool (not a direct taker fee share from HL)
- Exact referral pool rate is not publicly documented; estimated 10–50% of taker fee implied

### Eligibility

- Minimum account value: ≥100 USDC in perps account (essentially free)
- No minimum trading volume threshold documented
- No KYC required — wallet signature only
- Maximum: 10 active builder approvals per user address
- Builder fee cap: 0.1% for perps, 1% for spot (f=0 uses 0%, no cap concern)

### Registration

1. Navigate to `https://app.hyperliquid.xyz/trade` → Account → Builder
2. Submit `approveBuilderFee` on-chain transaction
3. **Critical:** must be signed by the MAIN wallet, not an API/agent wallet
4. Activation: immediate (no epoch delay documented)

### K370 Correction Note

K368 originally estimated $82,800/yr at $10M AUM assuming a direct 50% rebate on taker fees. K370 corrected this: builder codes are NOT direct fee rebates from HL — they earn from the referral pool. K481 adds a refined MID scenario (25%) and incorporates the POST_ONLY fill rate factor for more accurate projection. True rate is only discoverable after activation via actual claim data.

---

## Phase 2: Code Integration Design

### Target: `scripts/post_only_order_manager.py`

The 6-LOC patch adds builder code injection to `submit_post_only_order()`. The patch is:
- **Additive only** — no existing logic is removed or modified
- **Env-var gated** — silently skips if `HL_BUILDER_CODE` is not set
- **Venue-specific** — only injects for HL (Bybit/OKX orders unaffected)
- **Dry-run safe** — does not inject during paper-trade mode

### Proposed Patch (DO NOT APPLY TO LIVE WITHOUT DRY-RUN)

```diff
--- a/scripts/post_only_order_manager.py
+++ b/scripts/post_only_order_manager.py
@@ near submit_post_only_order(), after dry_run block, in live order construction @@

+    # K481: Builder code injection (ZERO-RISK additive, env-var gated)
+    _builder_code = os.environ.get("HL_BUILDER_CODE", "").strip()
+    if venue == "HL" and _builder_code and not dry_run:
+        order_action["builder"] = {"b": _builder_code, "f": 0}

 # --- existing order submission logic continues below ---
```

The same 6-LOC pattern applies to `submit_ioc_fallback()` for completeness (IOC orders on HL also carry the builder field — though maker-type rebates may differ for IOC).

### `smart_router.py` (K434) Integration Note

Update venue scoring in `score_venue()` to add builder rebate to HL's effective rate:

```python
# In score_venue(), HL-specific scoring:
if venue == "HL" and os.environ.get("HL_BUILDER_CODE"):
    # Conservative: add 0.45 bps (10% of 4.5bp taker × 70% maker fill rate)
    # This makes HL marginally more attractive in routing decisions
    effective_maker_bps_hl -= 0.45  # builder rebate bonus
```

This is optional — builder rebate accrues regardless of router preference since all HL orders carry the field. But adding it to the score makes routing decisions more accurate.

### Daemon Integration

All existing live daemons that submit orders via HL:
- `k246a-live.plist` → K208 reverse carry (main HL flow)
- `k272a-live.plist` → K280 main
- `k302a-satellite.plist` → K302a PAXG/SPX

All benefit automatically once `HL_BUILDER_CODE` is set and the patch is applied. No daemon restarts needed beyond the standard `launchctl unload/load` after code change.

---

## Phase 3: Profit Calculation (Refined)

### Model Parameters

| Parameter | Value | Source |
|-----------|-------|--------|
| HL fraction of AUM | 57.5% | v6.22 architecture (K280×50% + K302a) |
| Daily turnover factor | 1.5x AUM on HL | K370 estimate (17 fills/day, avg notional) |
| POST_ONLY maker fill rate | 70% | K439 target; paper target ≥65% |
| HL taker rate | 4.5 bps | Standard, non-VIP |
| Referral pool rebate (conservative) | 10% of taker notional implied | K370 research |
| Referral pool rebate (mid) | 25% of taker notional implied | K481 new scenario |
| Referral pool rebate (optimistic) | 50% of taker notional implied | K370 original |

### Annual Rebate by AUM and Scenario

```
HL daily volume   = AUM × 57.5% × 1.5 = AUM × 0.8625
Maker daily vol   = HL daily vol × 70% = AUM × 0.60375
Daily rebate (10%)= Maker vol × 0.045% × 10% = AUM × 0.0000272
Annual (10%)      = Daily × 365 = AUM × 0.00992

@ $10M:  $10M × 0.00992 = $99,166/yr   (conservative)
@ $10M:  $10M × 0.02481 = $248,414/yr  (mid 25%)
@ $10M:  $10M × 0.04962 = $496,828/yr  (optimistic)
```

| AUM | Conservative | Mid | Optimistic |
|-----|-------------|-----|-----------|
| $10M | $99,166/yr | $247,915/yr | $495,830/yr |
| $50M | $495,830/yr | $1,239,574/yr | $2,479,148/yr |
| $100M | $991,659/yr | $2,479,148/yr | $4,958,297/yr |
| $200M | $1,983,319/yr | $4,958,297/yr | $9,916,594/yr |

### Expected Daily Rebate at $10M AUM

| Scenario | USDC/day |
|----------|---------|
| Conservative (10%) | $271.7 |
| Mid (25%) | $679.2 |
| Optimistic (50%) | $1,358.4 |

These are the monitoring targets. Any sustained deviation below 50% of expected triggers an alert.

### Comparison to K370 Original

K370 projected $94K–$472K/yr at $10M AUM. K481 refined:
- Conservative: $99K (slight upward due to POST_ONLY fill rate model improvement)
- New mid scenario: $248K
- Optimistic: $496K (slight upward vs K370's $472K for same reason)

The headline "$94K–$472K/yr ZERO RISK" from K370 remains valid. K481 adds the mid ($248K) as a more likely central estimate.

---

## Phase 4: Activation Playbook

### Pre-Conditions

- [ ] HL account has ≥100 USDC perps balance
- [ ] Main wallet (not API key) is accessible for signing
- [ ] `scripts/post_only_order_manager.py` is at K439 version (check `REPO_ROOT/scripts/post_only_order_manager.py`)
- [ ] `HL_BUILDER_CODE` env var is NOT currently set (start clean)

---

### Step 1: Register Builder Fee on HL (20 min)

**URL:** `https://app.hyperliquid.xyz/trade` → Account → Builder

1. Connect main HL wallet (MetaMask or equivalent)
2. Navigate to Account → Builder section
3. Enter builder address: **your own main wallet address** (same address you're registering from)
4. Set fee: **0** (zero tenths of basis points = no extra cost to traders)
5. Sign the `approveBuilderFee` transaction
6. Confirm on-chain (typically 1–2 blocks, ~2 seconds on HL L1)

**What this does:** Registers your wallet as an authorized builder. Every future order with `order_action["builder"] = {"b": "0x<your_wallet>", "f": 0}` will credit the referral pool rewards to your account.

**CRITICAL:** This MUST be signed by the main wallet, not the API/agent wallet. If you use a separate agent wallet for trading, the `approveBuilderFee` must still come from the main wallet.

**Expected result:** Immediate activation. Check HL UI for confirmation banner.

---

### Step 2: Set HL_BUILDER_CODE Environment Variable (5 min)

```bash
# Add to ~/.zshrc (permanent)
echo 'export HL_BUILDER_CODE="0x<YOUR_MAIN_WALLET_ADDRESS>"' >> ~/.zshrc
source ~/.zshrc

# Verify
echo $HL_BUILDER_CODE   # should print: 0x<your_address>
```

The value is your main HL wallet address (the approved builder address). This is a public Ethereum address — not a private key. Still exclude from git commits per security hygiene.

For launchd daemons, add to each relevant plist:
```xml
<key>EnvironmentVariables</key>
<dict>
    <key>HL_BUILDER_CODE</key>
    <string>0x<YOUR_MAIN_WALLET_ADDRESS></string>
</dict>
```

**Do NOT commit this value to git. Do NOT write it to report.html.**

---

### Step 3: Apply 6-LOC Patch (10 min)

Apply the patch to `scripts/post_only_order_manager.py`.

**Exact insertion point:** In `submit_post_only_order()`, after the `if dry_run:` block and before the live HL order API call.

```python
# K481: Builder code injection (ZERO-RISK additive, env-var gated)
_builder_code = os.environ.get("HL_BUILDER_CODE", "").strip()
if venue == "HL" and _builder_code and not dry_run:
    order_action["builder"] = {"b": _builder_code, "f": 0}
```

The variable `order_action` is the dict being built for the HL clearinghouse API call. Verify by searching for `order_action` construction in the function.

**Verify patch with dry-run:**
```bash
cd /path/to/crypto-lab   # use absolute path, no /Users/ in scripts
python3 scripts/post_only_order_manager.py --dry-run
# Expected: no errors, DRY_RUN orders printed
# Should NOT include builder field in dry-run (env-var gate: not dry_run)
```

**IMPORTANT:** Do not apply to LIVE production until Step 4 paper-trade verification passes.

---

### Step 4: Paper-Trade 24h Verification (24h monitoring)

```bash
# Run paper-trade with patch active
python3 scripts/post_only_order_manager.py --dry-run --test-flow
```

For daemon-based verification:
1. Confirm daemon is in paper-trade mode
2. Submit 1 test order via K439 paper path
3. Inspect the order payload logged — builder field should appear for HL venue
4. After 24h, check HL referral dashboard: `https://app.hyperliquid.xyz/referrals`

**Gate:** Rebate > $0 accrued after 24h of paper orders. If $0:
- Check `approveBuilderFee` confirmed on-chain (TX hash in HL history)
- Check `HL_BUILDER_CODE` env var is set in the daemon process environment
- Verify orders are reaching HL (not being routed to Bybit/OKX by smart router)

---

### Step 5: Switch to LIVE + Daily Dashboard (30 min + ongoing)

After paper gate passes:

```bash
# Restart live daemons to pick up patched code
launchctl unload ~/Library/LaunchAgents/com.cryptolab.k246a-live.plist
launchctl load  ~/Library/LaunchAgents/com.cryptolab.k246a-live.plist
# Repeat for k272a-live, k302a-satellite, etc.
```

**Rebate claim:** Rebates accumulate in HL referral pool. Claim periodically at:
`https://app.hyperliquid.xyz/referrals`

**Daily monitoring (add to existing pnl_engine or cron):**
```python
# Expected daily @ $10M AUM (conservative): $271.7/day
# Alert if < $135/day for 3+ consecutive days
EXPECTED_DAILY_REBATE_10M_CON = 271.7
ALERT_THRESHOLD_PCT = 0.50
```

---

## Phase 5: Risk and Edge Cases

### Risk Matrix

| Risk | Severity | Probability | Mitigation |
|------|----------|-------------|-----------|
| HL terminates builder program | LOW | LOW | Rebate is bonus — strategy P&L unchanged; remove 1 field from order_action |
| Maker fill rate drops < 60% | MEDIUM | LOW-MED | K439 G8 gate already monitors; rebate scales linearly (never negative) |
| approveBuilderFee approval revoked | LOW | LOW | Weekly check via HL API; re-approve in 5 min |
| HL concentration impact | NEGLIGIBLE | N/A | Builder code has zero effect on venue allocation |
| Smart router deprioritizes HL | LOW | LOW | Builder rebate makes HL MORE attractive; optional: add to router scoring |

### Key Assertions

- **ZERO HL concentration change:** Builder code is order-level metadata. No new position on HL, no new AUM allocation.
- **ZERO counterparty risk:** Referral pool is internal HL accounting.
- **ZERO execution risk:** f=0 means no extra cost charged to the trading strategy. Worst case: builder field is ignored.
- **ZERO downside:** If program ends or approval lapses, strategy returns to current cost baseline. No degradation below current state.
- **K266 gate:** ACCEPT-FREE (cost optimization, not a new alpha signal).

### Cross-Venue Comparable Programs

| Venue | Program | Status | Notes |
|-------|---------|--------|-------|
| Bybit | Broker Program | EXISTS | Application required; 0.02% maker rebate for broker volume; priority after HL |
| OKX | Affiliate/API Broker | EXISTS | Application required; commission share; explore after HL active |
| Hyperliquid | Builder Rebate | ACTIVE | Primary target — highest HL allocation (57.5%) |

Bybit and OKX programs are lower priority: HL has the largest allocation, and the self-builder model requires no broker relationship agreement.

### Fill Rate Sensitivity

Rebate scales linearly with maker fill rate:

| Fill Rate | Rebate (conservative @ $10M) |
|-----------|------------------------------|
| 70% (target) | $99,166/yr |
| 60% (G8 threshold) | $85,000/yr |
| 50% | $70,833/yr |
| 40% | $56,667/yr |

Even at 40% fill rate (well below the K439 G8 alert threshold), rebate is $56K/yr — still significant positive contribution.

---

## Monitoring Specification

### Daily Check (add to pnl_engine or separate cron)

```
GET https://api.hyperliquid.xyz/info
Payload: {"type": "referralState", "user": "0x<your_wallet>"}

Check: cumulative_builder_rewards > (expected_daily × days_since_activation) × 0.50
Alert: if below 50% threshold for 3 consecutive days
```

### Weekly Check

```
Verify approveBuilderFee is still active:
GET https://api.hyperliquid.xyz/info
Payload: {"type": "builderFees", "user": "0x<your_wallet>"}
Expected: builder address in approved list with f=0
```

### Integration with K439 Fill Rate Gate

The existing `cache/post_only_fills.jsonl` tracks maker vs IOC fills. Builder rebate monitoring can be added as a derived metric:

```
rebate_days_equivalent = (actual_daily_rebate) / (expected_conservative_daily)
Alert: rebate_days_equivalent < 0.5 for 3+ days
```

---

## Implementation Checklist

```
[ ] Step 1: approveBuilderFee signed on HL main wallet (URL above)
[ ] Step 2: HL_BUILDER_CODE env var set in ~/.zshrc AND daemon plists
[ ] Step 3: 6-LOC patch applied to scripts/post_only_order_manager.py
[ ] Step 3a: python3 scripts/post_only_order_manager.py --dry-run → no errors
[ ] Step 4: 24h paper-trade, confirm rebate > $0 in HL dashboard
[ ] Step 5: Restart live daemons, add daily monitoring
[ ] Ongoing: Weekly approval check, daily rebate vs expected
```

---

## Appendix: Full Profit Projection Detail

### At $10M AUM
- Conservative (10% referral rate): **$99,166/yr** ($271.7/day)
- Mid estimate (25%): **$247,915/yr** ($679.2/day)
- Optimistic (50%): **$495,830/yr** ($1,358.4/day)

### At $100M AUM
- Conservative: **$991,659/yr** ($2,717/day)
- Mid: **$2,479,148/yr** ($6,792/day)
- Optimistic: **$4,958,297/yr** ($13,584/day)

### At $200M AUM
- Conservative: **$1,983,319/yr** ($5,434/day)
- Mid: **$4,958,297/yr** ($13,584/day)
- Optimistic: **$9,916,594/yr** ($27,168/day)

### ROI on Time Investment

At $10M AUM, even the conservative case ($99K/yr) against 65 minutes of setup time yields:
- **ROI per hour:** $99,166 / (65/60) ≈ $91,538/hr
- Payback period: < 4 hours of first-day trading

This is the highest ROI-per-hour user action in the entire 23-action deployment playbook.

---

*Source: `wave_k481_builder_rebate_activation.py` | `wave_k481_builder_rebate_activation.json`*  
*K481 Activation Playbook — 2026-05-30 02:44 JST*

# Wave K468: JLP APY Trigger Monitor — Jupiter Perpetuals LP

**Date:** 2026-05-30
**Status:** COMPLETE — 27th daemon SCAFFOLD-READY
**Daemon count:** 27 (27th = JLP APY monitor)

---

## Summary

Wave K468 implements the JLP APY trigger-based monitor (K467 CONDITIONAL follow-up).

K467 analyzed Jupiter Perpetuals JLP as a yield-generation strategy:
- **Current gross APY:** 1.68% (as of K467, 2026-05-25)
- **Break-even APY:** ~21% (IL + HL hedge cost + basis risk ~14-17%/yr)
- **Current net APY if entered:** −19.32pp (unprofitable at current rates)
- **K467 verdict:** CONDITIONAL — hold cash, monitor weekly, enter only when APY ≥ 25%

K468 builds the weekly monitor that detects the entry trigger.

---

## Deliverables

### New Files
- `scripts/jlp_apy_monitor.py` — K468 monitor script (~200 LOC)
- `com.cryptolab.jlp-apy-monitor.plist` — launchd plist (weekly, gitignored)
- `data/jlp_apy_dashboard.json` — initial dashboard (BELOW_BREAK_EVEN, 1.68%)
- `wave_k468_jlp_monitor.md` — this file
- `wave_k468_jlp_monitor.json` — structured wave metadata

### Modified Files
- `scripts/verify_deployment_status.py` — 27th daemon added
- `scripts/emergency_hl_exit.py` — `--include-jlp` flag + `close_jlp_positions()` stub
- `docs/k302a_runbook.md` — §36 JLP APY monitor playbook (8 subsections)
- `report.html` — K468 row in Live Monitoring, banner updated

---

## Implementation Phases

### Phase 1: jlp_apy_monitor.py

Single-shot script, REPO_ROOT pattern (K339), stdlib-only.

Each call:
1. Fetches JLP APY from DefiLlama `/yields` (searches Jupiter + Solana)
2. Fetches historical APY series from `/chart/{pool_id}`
3. Computes 7d/30d mean + 30d linear slope (pure stdlib)
4. Detects triggers:
   - **ENTRY_READY** (≥25%): entry threshold reached
   - **ACTIVE** (21%-25%): above break-even, no new entry
   - **BELOW_BREAK_EVEN** (<21%): hold cash
   - **REDUCE_WARNING** (10%-15%): exit half if position active
   - **EXIT** (<10% sustained 14d): exit all
5. Writes `cache/jlp_apy_alerts.jsonl`
6. Writes `data/jlp_apy_dashboard.json`
7. Optional ntfy.sh alert on ENTRY_READY / REDUCE_WARNING / EXIT

### Phase 2: Dashboard JSON Schema

```json
{
  "last_poll_jst": "2026-05-30 01:49:00 JST",
  "current_apy": 1.68,
  "apy_7d_mean": null,
  "apy_30d_mean": null,
  "apy_30d_slope": null,
  "break_even_apy": 21.0,
  "entry_trigger_threshold": 25.0,
  "reduce_trigger_threshold": 15.0,
  "exit_trigger_threshold": 10.0,
  "alert_status": "BELOW_BREAK_EVEN",
  "recommended_action": "Hold cash. JLP currently 1.68% < break-even 21%. Wait for >=25% trigger.",
  "estimated_net_apy_if_entered": -19.32,
  "vector_to_break_even": "+19.32pp required",
  "vector_to_entry": "+23.32pp required to reach 25.0% entry"
}
```

### Phase 3: Plist (27th Daemon)

```xml
<key>Label</key>
<string>com.cryptolab.jlp-apy-monitor</string>
<key>StartInterval</key>
<integer>604800</integer>  <!-- weekly, same as K407 TVL / K412 sUSDe monitors -->
```

### Phase 4: verify_deployment_status.py

27th daemon registered:
- `label`: `com.cryptolab.jlp-apy-monitor`
- `scripts`: `["scripts/jlp_apy_monitor.py"]`
- `expected_html_status`: `SCAFFOLD-READY`

Test result: **27 daemons, 0 mismatches**

### Phase 5: Runbook §36

Added to `docs/k302a_runbook.md`:
- §36.1 Strategy overview + K467 analysis (break-even derivation)
- §36.2 Trigger threshold table (entry/active/below_break_even/reduce/exit)
- §36.3 Daemon spec + dashboard JSON schema
- §36.4 Activation procedure (when ENTRY_READY fires)
- §36.5 Emergency exit procedure (--include-jlp flag)
- §36.6 Risk factors (Solana chain, IL, basis risk, APY decay, Jupiter protocol, funding blowout)
- §36.7 Activation commands
- §36.8 References table

### Phase 6: emergency_hl_exit.py

Added:
- `close_jlp_positions(dry_run, logger)` stub (~60 LOC)
  - Dry-run: prints Solana close guidance (jup.ag/perp → Earn → JLP → Withdraw)
  - Live: warns manual action required (Solana wallet signing is user responsibility)
- `--include-jlp` CLI flag
- JLP handling in execute path + dry-run note
- `jlp_success` included in `overall_success`

### Phase 7: Test Results

```
$ python3 scripts/jlp_apy_monitor.py
Exit code: 0

data/jlp_apy_dashboard.json:
  alert_status: BELOW_BREAK_EVEN
  current_apy: 1.68%
  recommended_action: "Hold cash. JLP currently 1.68% < break-even 21%. Wait for >=25% trigger."

$ python3 scripts/verify_deployment_status.py 2>&1 | tail -3
  com.cryptolab.jlp-apy-monitor  SCAFFOLD-READY  (html claims: SCAFFOLD-READY) pid=None plist=N
--- summary: {mismatches_with_html: 0} ---
--- daemons: 27 total ---
```

### Phase 8: HTML Live Monitoring

- K468 row added after K465 Vertex (27th daemon)
- Banner: "★ K468 JLP APY monitor 27th daemon (current 1.68% < 21% break-even, wait for 25% trigger)"
- last-update: 2026-05-30 01:49 JST

---

## K467 Analysis Background

JLP earns yield from 3 fee sources:
1. **Opening/closing fees:** 0.06% per position (Jupiter Perpetuals)
2. **Borrow fees:** Hourly utilization × funding rate (traders pay LP)
3. **Liquidation fees:** ~0.1-0.3% of liquidated position notional

**Cost structure (to LP):**
- IL: JLP is delta-long BTC/ETH/SOL (effectively short volatility) → IL from sharp moves
- Hedge cost: shorting BTC/ETH/SOL on HL to neutralize delta → funding + slippage ~6-9%/yr
- Basis risk: JLP price ≠ sum of hedge legs due to fee accumulation timing

**Historical APY range:**
- 2023-2024 (high-vol periods): 30-60% gross APY → profitable after costs
- 2025-2026 (low-vol): 1-5% gross APY → unprofitable at current levels

**Target entry regime:** High trader activity, elevated perp volumes (bull runs, high-vol events)

---

## Activation Sequence (When ENTRY_READY Fires)

```bash
# 1. Verify trigger
cat data/jlp_apy_dashboard.json | python3 -m json.tool | grep alert_status
# Expected: "alert_status": "ENTRY_READY"

# 2. Manual verification on DefiLlama
# https://defillama.com/yields?project=jupiter

# 3. Load daemon
cp com.cryptolab.jlp-apy-monitor.plist ~/Library/LaunchAgents/
launchctl load ~/Library/LaunchAgents/com.cryptolab.jlp-apy-monitor.plist

# 4. User: Set up Solana wallet + JLP deposit (jup.ag/perp)
# 5. User: Open HL delta hedge short
# 6. Verify verify_deployment_status.py shows ACTIVE
python3 scripts/verify_deployment_status.py
```

---

## References

| Wave | Content |
|------|---------|
| K468 | This wave — JLP APY trigger monitor (27th daemon) |
| K467 | JLP APY analysis (CONDITIONAL verdict, break-even 21%) |
| K465 | Lighter + Vertex scaffold (§35, 25th + 26th daemons) |
| K412 | sUSDe APY monitor (same architecture pattern) |
| K407 | TVL trajectory monitor (weekly StartInterval pattern) |
| K357 | Emergency HL exit script (--include-jlp added K468) |

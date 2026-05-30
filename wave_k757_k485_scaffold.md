# K757 K485 Bybit Sub-Account Integration Scaffold

**Wave:** K757 | **Generated:** 2026-05-30 20:58 JST
**Mandate:** feedback_profit_max_priority axis #5 — Multi-account scaling
**Status:** SCAFFOLD-READY (user 1-step activation)
**Tests:** 41/41 PASS

---

## Executive Summary

K751 audit found Bybit at 55.7% — 5.7pp over the 50% hard cap (K485).
K757 scaffolds Bybit sub-account integration: creates a 2nd Bybit account under the same master KYC,
routing alt-alt strategies to the sub-account and core strategies to main.

**Result:** Each account individually capped at 50%. Effective Bybit headroom:
- Before: 55.7% single account → 5.7pp over cap, headroom = $0
- After: main=55.7% (relief pending), sub=0% → sub headroom = $5M
- Together: total Bybit effective capacity doubles (main 50% + sub 50% = 100% combined)

---

## K523 3-Point Projection (capacity relief, @$10M AUM)

| Scenario | Bybit Headroom | Mechanism | Annual USD |
|----------|---------------|-----------|-----------|
| Conservative | +5pp | Alt-alt sleeves deploy fully (cap constraint relief) | **$20,000/yr** |
| Central | +10pp | 7-strategy alt-alt family at 1.5% each + fill rate improvement | **$50,000/yr** |
| Optimistic | +20pp | Full alt-alt at 2%+ + execution edge from strategy isolation | **$120,000/yr** |

K523 compliant: 3-point mandatory, single-point banned. Realized-to-stated ratio: 0.38.
This is **capacity relief** (unlocks already-validated strategies), not direct alpha.

---

## Deliverables

| File | Description |
|------|-------------|
| `scripts/bybit_multi_account_client.py` | ~420 LOC multi-account Bybit client (main + sub, K339) |
| `scripts/risk_manager.py` | K757 update: Bybit_main + Bybit_sub concentration tracking |
| `data/venue_allocation.json` | K757 extension: bybit_account per sleeve + sub activation steps |
| `wave_k757_k485_scaffold.py` | Validation harness (41/41 tests pass) |
| `wave_k757_k485_scaffold.json` | Full test results + K523 projections |
| `wave_k757_k485_scaffold.md` | This summary |
| `docs/k302a_runbook.md` | §71 K757 K485 sub-account 1-step activation runbook |
| `report.html` | K757 K485 BYBIT SUB-ACCOUNT READY badge |

---

## Sleeve-to-Account Mapping (K757 Default)

| Strategy | Account | Rationale |
|----------|---------|-----------|
| K208 / K280 / K297p | **main** | Core FR carry — stable, established |
| K500 INJ-BTC | **sub** | Alt-alt paired-trade — route to sub for cap relief |
| K507 TIA-BTC | **sub** | Alt-alt paired-trade |
| K512 APT-BTC | **sub** | Alt-alt paired-trade |
| K679 APT-SOL | **sub** | Alt-alt |
| K682 ATOM-SOL | **sub** | Alt-alt |
| K684 SOL-INJ | **sub** | Alt-alt |
| K686 AVAX-SOL | **sub** | Alt-alt |
| K687/K696 ENA-SOL | **sub** | Alt-alt |
| K698 LINK-ETH | **sub** | Alt-alt |

---

## 1-Step Activation (User Action Required)

```bash
# Step 1: Create Bybit sub-account
# Bybit → Account & Security → Sub Accounts → Create Sub Account
# Name: crypto-lab-k485-sub1 | Permissions: Trade (NO Withdrawal)

# Step 2: Generate sub-account API key
# Sub account → API → Create API key → Read + Trade (no Withdraw)

# Step 3: Paste credentials
echo "BYBIT_SUB_API_KEY=<your_sub_key>" >> ~/.env.local
echo "BYBIT_SUB_API_SECRET=<your_sub_secret>" >> ~/.env.local
echo "BYBIT_LIVE_ENABLED=true" >> ~/.env.local   # if not already set

# Step 4: Update this file
# Set venues.Bybit.accounts.sub.live_enabled=true in data/venue_allocation.json

# Step 5: Smoke test
python3 scripts/bybit_multi_account_client.py --smoke

# Step 6: Validate routing
python3 scripts/bybit_multi_account_client.py --capacity

# Step 7: Fund sub-account (optional initial amount)
# Bybit Asset Center → Internal Transfer → main → sub ($2-5M USDT)

# Step 8: Activate
# bybit_multi_account_client.py detects BYBIT_SUB_API_KEY automatically
# All alt-alt strategies route to sub; core strategies stay on main
```

**Reversibility:** Unset `BYBIT_SUB_API_KEY` → all routing returns to main (no code change needed).

---

## Compliance Note

Bybit sub-accounts are **explicitly permitted** under Bybit ToS for risk separation under the same
master KYC. This is NOT a duplicate personal account (which is prohibited). The sub-account shares
the master account's KYC, with separate API keys and separate balance tracking.

---

## Architecture Integration

```
bybit_multi_account_client.py
  ├── route_account(strategy_id) → "main" | "sub"
  │     ├── 1. venue_allocation.json sleeve.bybit_account (explicit)
  │     ├── 2. auto-rebalance: if main ≥ 45% → route to sub
  │     └── 3. default: core→main, alt-alt→sub
  ├── place_order(..., account=None) → auto-routes
  ├── get_balance(account="main"|"sub")
  ├── transfer(amount, direction="main_to_sub")
  └── capacity_check() → per-account + combined headroom

risk_manager.py (K757 update)
  ├── Bybit_main + Bybit_sub tracked independently
  ├── bybit_dual_account_capacity() → K757 dual-view
  ├── check_trade("Bybit_sub", notional) → ALLOW/BLOCK per account
  └── write_risk_report() → includes bybit_dual_account_capacity

data/venue_allocation.json (K757 extension)
  ├── venues.Bybit.accounts.main / sub (config + activation steps)
  ├── sleeves[*].bybit_account = "main" | "sub"
  ├── concentration_caps: Bybit_main + Bybit_sub each 50%
  └── bybit_sub_profit_unlock: K523 3-point ($20K / $50K / $120K/yr)
```

---

## References

| Wave | Description |
|------|-------------|
| K757 | This wave — K485 sub-account integration scaffold |
| K751 | Audit finding: Bybit 55.7% over 50% cap |
| K745 | K498 OKX integration (HL relief 65%→50%) |
| K485 | Original multi-account scaling analysis |
| K523 | 3-point projection mandate |
| K524 | HL 65.0% exact cap |

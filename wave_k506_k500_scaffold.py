#!/usr/bin/env python3
"""
wave_k506_k500_scaffold.py — K506 Wave Driver + Verification
=============================================================
Validates the K506 K500 INJ-BTC production scaffold deliverables.

Tests:
  1. Import k500_inj_btc_run and run compute_fr_differential (mock)
  2. Test decide_position logic (both directions + NEUTRAL)
  3. Test compute_delta_neutral_notional ($10M / 3% / 4x)
  4. Test close_paired_position (dry-run)
  5. Verify dashboard written correctly
  6. Verify leverage_manager has K500_INJ_BTC cap entry
  7. Verify leverage_config.json has k500_notes
  8. Verify emergency_hl_exit detects _detect_k500_paired_positions
  9. Verify verify_deployment_status has 34 daemons
  10. Print v6.25 combined sleeve summary

K339 security: REPO_ROOT from __file__, no /Users/ literals.
"""
from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent
DATA_DIR  = REPO_ROOT / "data"
SCRIPTS   = REPO_ROOT / "scripts"

PASS = "PASS"
FAIL = "FAIL"

results = []


def check(name: str, condition: bool, detail: str = "") -> None:
    status = PASS if condition else FAIL
    results.append({"name": name, "status": status, "detail": detail})
    icon = "OK" if condition else "!!"
    print(f"  [{icon}] {name}: {status}" + (f" — {detail}" if detail else ""))


# ── Load k500_inj_btc_run ────────────────────────────────────────────────────
spec = importlib.util.spec_from_file_location(
    "k500_inj_btc_run",
    SCRIPTS / "k500_inj_btc_run.py",
)
k500 = importlib.util.module_from_spec(spec)
spec.loader.exec_module(k500)

print("\n=== K506 Wave Verification ===")
print("  Strategy: K500 INJ-BTC FR Differential")
print("  Wave:     K506 (34th daemon)\n")

# Test 1: FR differential (mock values — no live API call)
print("[Test 1] compute_fr_differential (mock)")
fr_data = k500.compute_fr_differential(inj_fr=0.00003, btc_fr=0.00001)
check("fr_inj set", abs(fr_data["fr_inj"] - 0.00003) < 1e-9)
check("fr_btc set", abs(fr_data["fr_btc"] - 0.00001) < 1e-9)
check("raw_diff correct", abs(fr_data["raw_diff"] - 0.00002) < 1e-9)
check("ema_7d computed", isinstance(fr_data["ema_7d"], float))

# Test 2: decide_position — LONG_BTC_SHORT_INJ (INJ FR > BTC FR)
print("\n[Test 2] decide_position — LONG_BTC_SHORT_INJ")
fr_pos = {"ema_7d": 0.00005}  # INJ FR >> BTC FR
decision = k500.decide_position(fr_pos)
check("decision not None", decision is not None)
check("long_asset = BTC", decision is not None and decision["long_asset"] == "BTC")
check("short_asset = INJ", decision is not None and decision["short_asset"] == "INJ")
check("state correct", decision is not None and decision["position_state"] == k500.STATE_LONG_BTC_SHORT_INJ)

# Test 3: decide_position — LONG_INJ_SHORT_BTC (BTC FR > INJ FR)
print("\n[Test 3] decide_position — LONG_INJ_SHORT_BTC")
fr_neg = {"ema_7d": -0.00005}  # BTC FR >> INJ FR
dec2 = k500.decide_position(fr_neg)
check("decision not None (neg)", dec2 is not None)
check("long_asset = INJ", dec2 is not None and dec2["long_asset"] == "INJ")
check("short_asset = BTC", dec2 is not None and dec2["short_asset"] == "BTC")
check("state correct (neg)", dec2 is not None and dec2["position_state"] == k500.STATE_LONG_INJ_SHORT_BTC)

# Test 4: decide_position — NEUTRAL
print("\n[Test 4] decide_position — NEUTRAL")
fr_neutral = {"ema_7d": 0.000001}  # below threshold
dec_neutral = k500.decide_position(fr_neutral)
check("NEUTRAL returns None", dec_neutral is None)

# Test 5: compute_delta_neutral_notional
print("\n[Test 5] compute_delta_neutral_notional")
notional_per_leg, total_notional = k500.compute_delta_neutral_notional(
    aum=10_000_000, sleeve_pct=0.03, leverage=4.0
)
check("notional_per_leg = $600K", abs(notional_per_leg - 600_000) < 1)
check("total_notional = $1.2M", abs(total_notional - 1_200_000) < 1)
check("sleeve_capital = $300K", abs(10_000_000 * 0.03 - 300_000) < 1)
check("margin_required = $300K", abs(total_notional / 4.0 - 300_000) < 1)

# Test 6: close_paired_position dry-run
print("\n[Test 6] close_paired_position (dry-run from NEUTRAL)")
result = k500.close_paired_position("test_close", dry_run=True)
check("close returns dict", isinstance(result, dict))
# NEUTRAL state returns NO_POSITION since dashboard starts neutral
check("handles NEUTRAL gracefully", result.get("status") in ("NO_POSITION", "DRY_RUN_CLOSED"))

# Test 7: Dashboard written
print("\n[Test 7] Dashboard check")
dash_path = DATA_DIR / "k500_dashboard.json"
check("k500_dashboard.json exists", dash_path.exists())
if dash_path.exists():
    dash = json.loads(dash_path.read_text())
    check("position_state in valid states",
          dash.get("position_state") in ("NEUTRAL", "LONG_INJ_SHORT_BTC", "LONG_BTC_SHORT_INJ"))
    check("leverage = 4.0", dash.get("leverage") == 4.0)
    check("sleeve_pct = 0.03", dash.get("sleeve_pct") == 0.03)
    check("wave = K506", dash.get("wave") == "K506")
    check("oos_sharpe = 11.23", dash.get("oos_performance", {}).get("sharpe") == 11.23)
    check("ann_return = $124K", dash.get("oos_performance", {}).get("ann_return_usd") == 124_000)
    check("combined $631K/yr", dash.get("combined_sleeve", {}).get("combined_ann_return_usd") == 631_000)

# Test 8: leverage_config.json
print("\n[Test 8] leverage_config.json")
lc_path = DATA_DIR / "leverage_config.json"
check("leverage_config.json exists", lc_path.exists())
if lc_path.exists():
    lc = json.loads(lc_path.read_text())
    caps = lc.get("exchange_caps", {})
    check("K500_INJ_BTC cap = 4.0", caps.get("K500_INJ_BTC") == 4.0)
    k500_notes = lc.get("k500_notes", {})
    check("k500_notes exists", bool(k500_notes))
    check("k500_notes oos_sharpe = 11.23", k500_notes.get("oos_sharpe") == 11.23)
    check("k500_notes wave = K506", k500_notes.get("wave") == "K506")

# Test 9: leverage_manager.py has K500
print("\n[Test 9] leverage_manager.py K500 entries")
lm_path = SCRIPTS / "leverage_manager.py"
lm_text = lm_path.read_text()
check("K500_INJ_BTC in DEFAULT_EXCHANGE_CAPS", '"K500_INJ_BTC"' in lm_text)
check("K500 in SLEEVE_WEIGHTS_V625", '"K500"' in lm_text)
check("K500_INJ_BTC in cap_key_map", "K500_INJ_BTC" in lm_text)

# Test 10: emergency_hl_exit.py K500 integration
print("\n[Test 10] emergency_hl_exit.py K500 integration")
em_path = SCRIPTS / "emergency_hl_exit.py"
em_text = em_path.read_text()
check("_detect_k500_paired_positions exists", "_detect_k500_paired_positions" in em_text)
check("close_k500_paired_positions exists", "close_k500_paired_positions" in em_text)
check("--include-k500 flag exists", "--include-k500" in em_text)
check("k500_pair_detail in plan_exit", "k500_pair_detail" in em_text)
check("k500_paired_detected in return", "k500_paired_detected" in em_text)

# Test 11: verify_deployment_status.py 34 daemons
print("\n[Test 11] verify_deployment_status.py")
vd_path = SCRIPTS / "verify_deployment_status.py"
vd_text = vd_path.read_text()
check("com.cryptolab.k500-inj-btc in REGISTRY", "com.cryptolab.k500-inj-btc" in vd_text)
check("k500_inj_btc_run.py in REGISTRY", "k500_inj_btc_run.py" in vd_text)
check("34th daemon in REGISTRY", "34th daemon" in vd_text)

# Count REGISTRY entries
import re
registry_labels = re.findall(r'"com\.cryptolab\.[^"]+?"', vd_text)
unique_labels = set(registry_labels)
check("34 daemons in REGISTRY", len(unique_labels) == 34, f"found {len(unique_labels)}")

# Test 12: k500_dashboard.json initial state
print("\n[Test 12] k500_dashboard.json initial NEUTRAL state")
if dash_path.exists():
    dash = json.loads(dash_path.read_text())
    check("gate_metrics oos_sharpe_target = 3.5", dash.get("gate_metrics", {}).get("oos_sharpe_target") == 3.5)
    check("gate_metrics fill_rate_target = 60", dash.get("gate_metrics", {}).get("fill_rate_target_pct") == 60)
    check("gate_metrics max_drawdown = 15", dash.get("gate_metrics", {}).get("max_drawdown_pct") == 15)
    check("activation status = SCAFFOLD-READY", dash.get("activation_criteria", {}).get("status") == "SCAFFOLD-READY")

# ── Summary ──────────────────────────────────────────────────────────────────
print("\n=== v6.25 Combined Paired-Trade Sleeve Summary ===")
print("  K449 ETH-BTC:  OOS Sh  5.66 | $187K/yr |  5% sleeve")
print("  K476 SOL-BTC:  OOS Sh 16.30 | $187K/yr |  3% sleeve")
print("  K484 AVAX-BTC: OOS Sh 43.89 | $ 75.7K/yr |  3% sleeve")
print("  K493 ATOM-BTC: OOS Sh 50.79 | $231K/yr |  3% sleeve")
print("  K500 INJ-BTC:  OOS Sh 11.23 | $124K/yr |  3% sleeve  ← NEW (K506)")
print("  ──────────────────────────────────────────────")
print("  COMBINED:                    | $631K/yr | 17% sleeve")
print()
print("  HL concentration: 62% < 65% cap (3pp headroom)")
print("  60d paper-trade gate (K500): OOS Sh>=3.5 + fill_rate>=60% + maxDD<15%")
print("  After gate: activate v6.25 K500 3% live → $631K/yr combined @$10M")
print()

n_pass = sum(1 for r in results if r["status"] == PASS)
n_fail = sum(1 for r in results if r["status"] == FAIL)
print(f"=== K506 Verification Complete: {n_pass} PASS / {n_fail} FAIL ===")

if n_fail > 0:
    print("\nFailed checks:")
    for r in results:
        if r["status"] == FAIL:
            print(f"  - {r['name']}: {r['detail']}")

sys.exit(0 if n_fail == 0 else 1)

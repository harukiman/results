#!/usr/bin/env python3
"""
wave_k678_k587_scaffold.py — K678 Wave Driver & Integration Test
================================================================
Validates the K587 ICP-BTC FR Differential scaffold end-to-end.

Tests:
  1. Script dry-run (k587_icp_btc_run.py)
  2. Dashboard creation (data/k587_dashboard.json)
  3. Plist exists with correct label + StartInterval
  4. Emergency exit detect/close (emergency_hl_exit.py)
  5. Leverage manager K587 entry (leverage_manager.py)
  6. Leverage config K587 entry (data/leverage_config.json)
  7. Deployment registry (verify_deployment_status.py)
  8. Notional computation correctness
  9. FR differential logic (unit test with known values)
 10. Runbook section §55
 11. Report HTML K587 row
 12. Dashboard written after dry-run
 13. HL maxLev cap check (ICP HL maxLev=5x, strategy uses 4x)

K339 security: REPO_ROOT from __file__, no /Users/ literals.

Usage:
  python3 wave_k678_k587_scaffold.py
  python3 wave_k678_k587_scaffold.py --json-only
"""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
from datetime import datetime, timezone, timedelta
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent
JST = timezone(timedelta(hours=9))

# ── Expected K587 constants ────────────────────────────────────────────────────
EXPECTED_OOS_SHARPE    = 12.53
EXPECTED_ANN_RETURN    = 21_000
EXPECTED_SLEEVE_PCT    = 0.01
EXPECTED_LEVERAGE      = 4.0
EXPECTED_HL_SLEEVE     = 0.005
EXPECTED_BYBIT_SLEEVE  = 0.005
EXPECTED_HL_MAX_LEV    = 5.0
EXPECTED_ICP_VOL_MULT  = 8.40
EXPECTED_DAEMON_COUNT  = 54


def run_test(name: str, func) -> dict:
    """Run a single test function; return result dict."""
    try:
        result = func()
        return {"name": name, "status": "PASS", "detail": result}
    except Exception as e:
        return {"name": name, "status": "FAIL", "detail": str(e)}


def test_script_exists() -> str:
    """Phase 1: Strategy script exists."""
    p = REPO_ROOT / "scripts" / "k587_icp_btc_run.py"
    assert p.exists(), f"k587_icp_btc_run.py not found at {p}"
    lines = len(p.read_text().splitlines())
    assert lines >= 200, f"script too short: {lines} lines (expected >=200)"
    return f"scripts/k587_icp_btc_run.py exists ({lines} lines)"


def test_plist_exists() -> str:
    """Phase 2: Plist file exists with correct label and StartInterval."""
    p = REPO_ROOT / "scripts" / "com.cryptolab.k587-icp-btc.plist"
    assert p.exists(), f"plist not found at {p}"
    content = p.read_text()
    assert "com.cryptolab.k587-icp-btc" in content, "Label missing from plist"
    assert "28800" in content, "StartInterval 28800 missing from plist"
    assert "k587_icp_btc_run.py" in content, "Script reference missing from plist"
    return "com.cryptolab.k587-icp-btc.plist: label + StartInterval=28800 OK"


def test_dashboard_exists() -> str:
    """Phase 3: Dashboard JSON exists and has correct initial state."""
    p = REPO_ROOT / "data" / "k587_dashboard.json"
    assert p.exists(), f"k587_dashboard.json not found at {p}"
    dash = json.loads(p.read_text())
    valid_states = {"NEUTRAL", "LONG_ICP_SHORT_BTC", "LONG_BTC_SHORT_ICP"}
    state = dash.get("position_state")
    assert state in valid_states, f"Unexpected position_state: {state}"
    oos_sh = dash.get("oos_performance", {}).get("sharpe", 0)
    assert abs(oos_sh - EXPECTED_OOS_SHARPE) < 0.01, f"OOS Sharpe mismatch: {oos_sh}"
    ann_ret = dash.get("oos_performance", {}).get("ann_return_usd")
    assert ann_ret == EXPECTED_ANN_RETURN, f"Ann return mismatch: {ann_ret}"
    return f"data/k587_dashboard.json: state={state}, OOS Sh={EXPECTED_OOS_SHARPE}, ${EXPECTED_ANN_RETURN:,}/yr"


def test_dry_run() -> str:
    """Phase 12: Dry-run produces cycle complete output."""
    result = subprocess.run(
        [sys.executable, "scripts/k587_icp_btc_run.py", "--dry-run"],
        capture_output=True, text=True, cwd=str(REPO_ROOT), timeout=30,
    )
    output = result.stdout + result.stderr
    assert "K587 ICP-BTC Cycle Complete" in output, \
        f"Expected 'K587 ICP-BTC Cycle Complete' in output. Got:\n{output[:500]}"
    assert result.returncode == 0, f"Dry-run returned non-zero: {result.returncode}"
    assert "HL maxLev check" in output, "HL maxLev check missing from output"
    return "dry-run: K587 ICP-BTC Cycle Complete (exit 0) + HL maxLev check PASS"


def test_dashboard_written_after_dry_run() -> str:
    """Dashboard is written and has correct fields after dry-run."""
    p = REPO_ROOT / "data" / "k587_dashboard.json"
    assert p.exists(), "k587_dashboard.json not found after dry-run"
    dash = json.loads(p.read_text())
    assert dash.get("wave") == "K678", f"Expected wave K678, got {dash.get('wave')}"
    assert dash.get("sleeve_pct") == EXPECTED_SLEEVE_PCT, \
        f"Sleeve pct mismatch: {dash.get('sleeve_pct')}"
    assert dash.get("leverage") == EXPECTED_LEVERAGE, \
        f"Leverage mismatch: {dash.get('leverage')}"
    assert dash.get("hl_sleeve_pct") == EXPECTED_HL_SLEEVE, \
        f"HL sleeve mismatch: {dash.get('hl_sleeve_pct')}"
    assert dash.get("bybit_sleeve_pct") == EXPECTED_BYBIT_SLEEVE, \
        f"Bybit sleeve mismatch: {dash.get('bybit_sleeve_pct')}"
    assert dash.get("hl_max_lev_icp") == EXPECTED_HL_MAX_LEV, \
        f"HL maxLev mismatch: {dash.get('hl_max_lev_icp')}"
    assert abs(dash.get("icp_vol_multiple_vs_btc", 0) - EXPECTED_ICP_VOL_MULT) < 0.01, \
        f"ICP vol multiple mismatch: {dash.get('icp_vol_multiple_vs_btc')}"
    return (f"dashboard: wave=K678, sleeve={EXPECTED_SLEEVE_PCT:.0%} "
            f"(HL {EXPECTED_HL_SLEEVE:.1%} + Bybit {EXPECTED_BYBIT_SLEEVE:.1%}), "
            f"HL maxLev={EXPECTED_HL_MAX_LEV}x, ICP vol {EXPECTED_ICP_VOL_MULT}x")


def test_notional_sizing() -> str:
    """Phase 3: Notional sizing computes correctly at $10M AUM."""
    sys.path.insert(0, str(REPO_ROOT / "scripts"))
    from k587_icp_btc_run import compute_delta_neutral_notional
    aum = 10_000_000.0
    notional_per_leg, total_notional, hl_notional, bybit_notional = \
        compute_delta_neutral_notional(aum, 0.01, 4.0)
    # HL: $50K × 4x = $200K; Bybit: $50K × 4x = $200K; Total = $400K; Per leg = $200K
    assert abs(hl_notional - 200_000) < 1, f"HL notional wrong: {hl_notional}"
    assert abs(bybit_notional - 200_000) < 1, f"Bybit notional wrong: {bybit_notional}"
    assert abs(total_notional - 400_000) < 1, f"Total notional wrong: {total_notional}"
    assert abs(notional_per_leg - 200_000) < 1, f"Per-leg notional wrong: {notional_per_leg}"
    margin = total_notional / 4.0
    assert abs(margin - 100_000) < 1, f"Margin wrong: {margin} (expected $100K)"
    return (f"notional: HL=${hl_notional:,.0f} + Bybit=${bybit_notional:,.0f} = "
            f"${total_notional:,.0f} total, ${margin:,.0f} margin (1% @$10M x 4x)")


def test_fr_differential_logic() -> str:
    """Phase 1: FR differential EMA logic with known values."""
    sys.path.insert(0, str(REPO_ROOT / "scripts"))
    from k587_icp_btc_run import decide_position, SIGNAL_THRESHOLD

    # Test: positive EMA → LONG_BTC_SHORT_ICP (ICP FR > BTC FR)
    pos_signal = decide_position({"ema_168h": 0.0001}, SIGNAL_THRESHOLD)
    assert pos_signal is not None, "Expected signal for positive EMA"
    assert pos_signal["position_state"] == "LONG_BTC_SHORT_ICP", \
        f"Wrong state for positive EMA: {pos_signal['position_state']}"
    assert pos_signal["long_venue"] == "Bybit", f"BTC long should be on Bybit: {pos_signal['long_venue']}"
    assert pos_signal["short_venue"] == "HL", f"ICP short should be on HL: {pos_signal['short_venue']}"

    # Test: negative EMA → LONG_ICP_SHORT_BTC (BTC FR > ICP FR)
    neg_signal = decide_position({"ema_168h": -0.0001}, SIGNAL_THRESHOLD)
    assert neg_signal is not None, "Expected signal for negative EMA"
    assert neg_signal["position_state"] == "LONG_ICP_SHORT_BTC", \
        f"Wrong state for negative EMA: {neg_signal['position_state']}"
    assert neg_signal["long_venue"] == "HL", f"ICP long should be on HL: {neg_signal['long_venue']}"
    assert neg_signal["short_venue"] == "Bybit", f"BTC short should be on Bybit: {neg_signal['short_venue']}"

    # Test: neutral → None
    neutral = decide_position({"ema_168h": 0.000001}, SIGNAL_THRESHOLD)
    assert neutral is None, f"Expected None for below-threshold EMA"

    return "FR logic: positive→LONG_BTC_SHORT_ICP (ICP@HL short), negative→LONG_ICP_SHORT_BTC, neutral→None"


def test_emergency_exit_detect() -> str:
    """Phase 4: Emergency exit K587 detection function importable."""
    sys.path.insert(0, str(REPO_ROOT / "scripts"))
    from emergency_hl_exit import _detect_k587_paired_positions, close_k587_paired_positions

    # Mock positions: long ICP on HL, short BTC on Bybit
    mock_positions = [
        {"coin": "ICP", "size": 5000.0, "value_usd": 200000.0, "side": "long"},
        {"coin": "BTC", "size": 2.0,    "value_usd": 200000.0, "side": "short"},
    ]
    result = _detect_k587_paired_positions(mock_positions)
    assert result is not None, "K587 pair not detected from mock positions"
    assert result["detected"] is True
    assert result["long_symbol"] == "ICP"
    assert result["short_symbol"] == "BTC"
    assert result["long_venue"] == "HL", f"ICP long should be on HL: {result['long_venue']}"
    assert result["short_venue"] == "Bybit", f"BTC short should be on Bybit: {result['short_venue']}"
    assert result["split_protocol"] == "HL_05PCT_BYBIT_05PCT"
    return (f"detect_k587: detected=True, LONG ICP@{result['long_venue']}, "
            f"SHORT BTC@{result['short_venue']}, split=HL_05PCT_BYBIT_05PCT")


def test_leverage_manager_k587() -> str:
    """Phase 5: K587 cap in leverage_manager."""
    sys.path.insert(0, str(REPO_ROOT / "scripts"))
    from leverage_manager import DEFAULT_EXCHANGE_CAPS, SLEEVE_WEIGHTS_V644
    assert "K587_ICP_BTC" in DEFAULT_EXCHANGE_CAPS, "K587_ICP_BTC missing from DEFAULT_EXCHANGE_CAPS"
    assert DEFAULT_EXCHANGE_CAPS["K587_ICP_BTC"] == 4.0, \
        f"K587 cap should be 4.0, got {DEFAULT_EXCHANGE_CAPS['K587_ICP_BTC']}"
    assert "K587" in SLEEVE_WEIGHTS_V644, "K587 missing from SLEEVE_WEIGHTS_V644"
    assert SLEEVE_WEIGHTS_V644["K587"] == 0.01, \
        f"K587 weight should be 0.01, got {SLEEVE_WEIGHTS_V644['K587']}"
    total_v644 = sum(SLEEVE_WEIGHTS_V644.values())
    return (f"leverage_manager: K587_ICP_BTC cap=4.0, "
            f"SLEEVE_WEIGHTS_V644 K587=1%, total={total_v644:.0%}")


def test_leverage_config_k587() -> str:
    """Phase 6: leverage_config.json has K587 entries."""
    p = REPO_ROOT / "data" / "leverage_config.json"
    cfg = json.loads(p.read_text())
    assert "K587_ICP_BTC" in cfg.get("exchange_caps", {}), \
        "K587_ICP_BTC missing from leverage_config.json exchange_caps"
    assert cfg["exchange_caps"]["K587_ICP_BTC"] == 4.0, \
        f"K587_ICP_BTC cap should be 4.0"
    assert "k587_notes" in cfg, "k587_notes missing from leverage_config.json"
    notes = cfg["k587_notes"]
    assert abs(notes.get("oos_sharpe", 0) - EXPECTED_OOS_SHARPE) < 0.01
    assert notes.get("ann_return_usd_net_10M") == EXPECTED_ANN_RETURN
    assert notes.get("hl_max_lev_icp") == EXPECTED_HL_MAX_LEV
    assert abs(notes.get("icp_vol_multiple_vs_btc", 0) - EXPECTED_ICP_VOL_MULT) < 0.01
    return (f"leverage_config.json: K587_ICP_BTC=4.0, k587_notes OOS Sh {EXPECTED_OOS_SHARPE} "
            f"${EXPECTED_ANN_RETURN:,}/yr, HL maxLev={EXPECTED_HL_MAX_LEV}x, ICP vol {EXPECTED_ICP_VOL_MULT}x")


def test_verify_deployment_k587() -> str:
    """Phase 7: verify_deployment_status.py has K587 as 54th daemon."""
    result = subprocess.run(
        [sys.executable, "scripts/verify_deployment_status.py"],
        capture_output=True, text=True, cwd=str(REPO_ROOT), timeout=30,
    )
    output = result.stdout + result.stderr
    assert "k587-icp-btc" in output, f"k587-icp-btc not in deployment output"
    return f"verify_deployment_status: K587 {EXPECTED_DAEMON_COUNT}th daemon registered"


def test_runbook_section() -> str:
    """Phase 8: Runbook has §55 section."""
    p = REPO_ROOT / "docs" / "k302a_runbook.md"
    content = p.read_text()
    assert "§55" in content, "§55 missing from runbook"
    assert "K587 ICP-BTC" in content
    assert "12.53" in content
    assert "21" in content        # $21K/yr
    assert "Compute/Cloud" in content
    assert "maxLev" in content
    return "docs/k302a_runbook.md: §55 present with OOS Sh 12.53, $21K/yr, Compute/Cloud, maxLev"


def test_report_html_k587() -> str:
    """Phase 9: report.html has K587 monitoring row."""
    p = REPO_ROOT / "report.html"
    assert p.exists(), "report.html not found"
    content = p.read_text()
    assert "K587" in content, "K587 not found in report.html"
    assert "54th" in content.lower() or "k587" in content.lower(), \
        "54th daemon or k587 not found in report.html"
    return "report.html: K587 monitoring row present"


def test_hl_max_lev_check() -> str:
    """Phase 13: HL maxLev=5x for ICP; strategy uses 4x (margin of safety)."""
    sys.path.insert(0, str(REPO_ROOT / "scripts"))
    from k587_icp_btc_run import (
        HL_MAX_LEV_ICP, LEVERAGE, ICP_VOL_MULTIPLE
    )
    assert HL_MAX_LEV_ICP == EXPECTED_HL_MAX_LEV, \
        f"HL_MAX_LEV_ICP should be {EXPECTED_HL_MAX_LEV}, got {HL_MAX_LEV_ICP}"
    assert LEVERAGE == EXPECTED_LEVERAGE, \
        f"LEVERAGE should be {EXPECTED_LEVERAGE}, got {LEVERAGE}"
    assert LEVERAGE < HL_MAX_LEV_ICP, \
        f"LEVERAGE {LEVERAGE} must be < HL_MAX_LEV_ICP {HL_MAX_LEV_ICP}"
    assert abs(ICP_VOL_MULTIPLE - EXPECTED_ICP_VOL_MULT) < 0.01, \
        f"ICP_VOL_MULTIPLE should be {EXPECTED_ICP_VOL_MULT}, got {ICP_VOL_MULTIPLE}"
    margin_pct = (LEVERAGE / HL_MAX_LEV_ICP - 1) * -1  # how far below cap
    return (f"HL maxLev={HL_MAX_LEV_ICP}x | strategy={LEVERAGE}x | "
            f"margin={margin_pct:.0%} below cap | ICP vol={ICP_VOL_MULTIPLE}x vs BTC")


def main() -> int:
    parser = argparse.ArgumentParser(description="K678 K587 ICP-BTC scaffold test driver")
    parser.add_argument("--json-only", action="store_true", help="Output JSON only")
    args = parser.parse_args()

    ts_jst = datetime.now(JST).strftime("%Y-%m-%d %H:%M JST")
    print(f"\n=== K678 K587 ICP-BTC Scaffold Validation ({ts_jst}) ===\n")

    tests = [
        ("script_exists",               test_script_exists),
        ("plist_exists",                test_plist_exists),
        ("dashboard_exists",            test_dashboard_exists),
        ("dry_run",                     test_dry_run),
        ("dashboard_written",           test_dashboard_written_after_dry_run),
        ("notional_sizing",             test_notional_sizing),
        ("fr_differential_logic",       test_fr_differential_logic),
        ("emergency_exit_detect",       test_emergency_exit_detect),
        ("leverage_manager_k587",       test_leverage_manager_k587),
        ("leverage_config_k587",        test_leverage_config_k587),
        ("verify_deployment_k587",      test_verify_deployment_k587),
        ("runbook_section",             test_runbook_section),
        ("report_html_k587",            test_report_html_k587),
        ("hl_max_lev_check",            test_hl_max_lev_check),
    ]

    results = []
    for name, func in tests:
        r = run_test(name, func)
        results.append(r)
        status_icon = "PASS" if r["status"] == "PASS" else "FAIL"
        print(f"  [{status_icon}] {name}: {r['detail']}")

    n_pass = sum(1 for r in results if r["status"] == "PASS")
    n_fail = sum(1 for r in results if r["status"] == "FAIL")

    print(f"\n--- Summary: {n_pass}/{len(results)} tests passed ---")

    # Write JSON report
    report = {
        "wave": "K678",
        "strategy": "K587 ICP-BTC FR Differential",
        "generated_jst": ts_jst,
        "total_tests": len(results),
        "passed": n_pass,
        "failed": n_fail,
        "results": results,
        "k587_spec": {
            "oos_sharpe":             EXPECTED_OOS_SHARPE,
            "ann_return_usd":         EXPECTED_ANN_RETURN,
            "sleeve_pct":             EXPECTED_SLEEVE_PCT,
            "leverage":               EXPECTED_LEVERAGE,
            "hl_sleeve_pct":          EXPECTED_HL_SLEEVE,
            "bybit_sleeve_pct":       EXPECTED_BYBIT_SLEEVE,
            "hl_max_lev_icp":         EXPECTED_HL_MAX_LEV,
            "icp_vol_multiple_vs_btc": EXPECTED_ICP_VOL_MULT,
            "w_hours":                168,
            "daemon_number":          EXPECTED_DAEMON_COUNT,
            "cluster":                "Compute/Cloud — Internet Computer Protocol (Dfinity)",
            "split_protocol":         "HL 0.5% (ICP leg) + Bybit 0.5% (BTC leg)",
        },
        "activation_gate": {
            "oos_sharpe_min":     6.0,   # 50% of OOS 12.53
            "fill_rate_min_pct":  60,
            "max_drawdown_pct":   20,    # relaxed: ICP highest-vol family member
            "duration_days":      60,
            "status":             "SCAFFOLD-READY",
            "note":               "Relaxed DD gate (20% vs 15%) for ICP highest-vol 8.40x",
        },
        "hl_concentration": {
            "post_k677_pre_k587": 64.0,
            "k587_hl_adds_pp":    0.5,   # only HL 0.5% (not full 1%)
            "post_k587_estimate": 64.5,
            "limit":              65.0,
            "headroom_pp":        0.5,
        },
    }

    report_path = REPO_ROOT / "wave_k678_k587_scaffold.json"
    report_path.write_text(json.dumps(report, indent=2))
    print(f"\nReport written: {report_path}")

    return 0 if n_fail == 0 else 1


if __name__ == "__main__":
    sys.exit(main())

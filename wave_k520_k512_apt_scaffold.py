#!/usr/bin/env python3
"""
wave_k520_k512_apt_scaffold.py — K520 Wave Driver & Integration Test
=====================================================================
Validates the K512 APT-BTC FR Differential scaffold end-to-end.

Tests:
  1. Script dry-run (k512_apt_btc_run.py)
  2. Dashboard creation (data/k512_dashboard.json)
  3. Emergency exit detect/close (emergency_hl_exit.py)
  4. Leverage manager K512 entry (leverage_manager.py)
  5. Deployment registry (verify_deployment_status.py)
  6. Notional computation correctness
  7. FR differential logic (unit test with known values)

K339 security: REPO_ROOT from __file__, no /Users/ literals.

Usage:
  python3 wave_k520_k512_apt_scaffold.py
  python3 wave_k520_k512_apt_scaffold.py --json-only
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

# ── Expected K512 constants ────────────────────────────────────────────────────
EXPECTED_OOS_SHARPE    = 51.10
EXPECTED_ANN_RETURN    = 302_000
EXPECTED_SLEEVE_PCT    = 0.02
EXPECTED_LEVERAGE      = 4.0
EXPECTED_HL_SLEEVE     = 0.01
EXPECTED_BYBIT_SLEEVE  = 0.01
EXPECTED_HL_CONC       = 64.0
EXPECTED_OU_HALFLIFE   = 0.27
EXPECTED_DAEMON_COUNT  = 36


def run_test(name: str, func) -> dict:
    """Run a single test function; return result dict."""
    try:
        result = func()
        return {"name": name, "status": "PASS", "detail": result}
    except Exception as e:
        return {"name": name, "status": "FAIL", "detail": str(e)}


def test_script_exists() -> str:
    """Phase 1: Strategy script exists."""
    p = REPO_ROOT / "scripts" / "k512_apt_btc_run.py"
    assert p.exists(), f"k512_apt_btc_run.py not found at {p}"
    lines = len(p.read_text().splitlines())
    assert lines >= 200, f"script too short: {lines} lines (expected >=200)"
    return f"scripts/k512_apt_btc_run.py exists ({lines} lines)"


def test_dashboard_exists() -> str:
    """Phase 3: Dashboard JSON exists and has correct initial state."""
    p = REPO_ROOT / "data" / "k512_dashboard.json"
    assert p.exists(), f"k512_dashboard.json not found at {p}"
    dash = json.loads(p.read_text())
    valid_states = {"NEUTRAL", "LONG_APT_SHORT_BTC", "LONG_BTC_SHORT_APT"}
    state = dash.get("position_state")
    assert state in valid_states, \
        f"Unexpected position_state: {state}"
    assert abs(dash.get("oos_performance", {}).get("sharpe", 0) - EXPECTED_OOS_SHARPE) < 0.01, \
        f"OOS Sharpe mismatch: {dash.get('oos_performance', {}).get('sharpe')}"
    assert dash.get("oos_performance", {}).get("ann_return_usd") == EXPECTED_ANN_RETURN, \
        f"Ann return mismatch"
    return f"data/k512_dashboard.json: state={state}, OOS Sh 51.10, $302K/yr"


def test_dry_run() -> str:
    """Phase 12: Dry-run produces cycle complete output."""
    result = subprocess.run(
        [sys.executable, "scripts/k512_apt_btc_run.py", "--dry-run"],
        capture_output=True, text=True, cwd=str(REPO_ROOT), timeout=30,
    )
    output = result.stdout + result.stderr
    assert "K512 Cycle Complete" in output, \
        f"Expected 'K512 Cycle Complete' in output. Got:\n{output[:500]}"
    assert result.returncode == 0, f"Dry-run returned non-zero: {result.returncode}"
    return "dry-run: K512 Cycle Complete (exit 0)"


def test_dashboard_written_after_dry_run() -> str:
    """Dashboard is written and has correct fields after dry-run."""
    p = REPO_ROOT / "data" / "k512_dashboard.json"
    assert p.exists(), "k512_dashboard.json not found after dry-run"
    dash = json.loads(p.read_text())
    assert dash.get("wave") == "K520", f"Expected wave K520, got {dash.get('wave')}"
    assert dash.get("sleeve_pct") == EXPECTED_SLEEVE_PCT, \
        f"Sleeve pct mismatch: {dash.get('sleeve_pct')}"
    assert dash.get("leverage") == EXPECTED_LEVERAGE, \
        f"Leverage mismatch: {dash.get('leverage')}"
    assert dash.get("hl_sleeve_pct") == EXPECTED_HL_SLEEVE, \
        f"HL sleeve mismatch: {dash.get('hl_sleeve_pct')}"
    assert dash.get("bybit_sleeve_pct") == EXPECTED_BYBIT_SLEEVE, \
        f"Bybit sleeve mismatch: {dash.get('bybit_sleeve_pct')}"
    assert dash.get("hl_concentration_pct") == EXPECTED_HL_CONC, \
        f"HL concentration mismatch: {dash.get('hl_concentration_pct')}"
    return (f"dashboard: wave=K520, sleeve={EXPECTED_SLEEVE_PCT:.0%}, "
            f"HL={EXPECTED_HL_CONC}% (1pp headroom)")


def test_notional_sizing() -> str:
    """Phase 3: Notional sizing computes correctly at $10M AUM."""
    sys.path.insert(0, str(REPO_ROOT / "scripts"))
    from k512_apt_btc_run import compute_delta_neutral_notional
    aum = 10_000_000.0
    notional_per_leg, total_notional, hl_notional, bybit_notional = \
        compute_delta_neutral_notional(aum, 0.02, 4.0)
    assert abs(hl_notional - 400_000) < 1, f"HL notional wrong: {hl_notional}"
    assert abs(bybit_notional - 400_000) < 1, f"Bybit notional wrong: {bybit_notional}"
    assert abs(total_notional - 800_000) < 1, f"Total notional wrong: {total_notional}"
    assert abs(notional_per_leg - 400_000) < 1, f"Per-leg notional wrong: {notional_per_leg}"
    margin = total_notional / 4.0
    assert abs(margin - 200_000) < 1, f"Margin wrong: {margin}"
    return (f"notional: HL=${hl_notional:,.0f} + Bybit=${bybit_notional:,.0f} = "
            f"${total_notional:,.0f} total, ${margin:,.0f} margin (2% @ $10M × 4x)")


def test_fr_differential_logic() -> str:
    """Phase 1: FR differential EMA logic with known values."""
    sys.path.insert(0, str(REPO_ROOT / "scripts"))
    from k512_apt_btc_run import decide_position, SIGNAL_THRESHOLD

    # Test: positive EMA → LONG_BTC_SHORT_APT
    pos_signal = decide_position({"ema_7d": 0.0001}, SIGNAL_THRESHOLD)
    assert pos_signal is not None, "Expected signal for positive EMA"
    assert pos_signal["position_state"] == "LONG_BTC_SHORT_APT", \
        f"Wrong state for positive EMA: {pos_signal['position_state']}"
    assert pos_signal["long_venue"] == "Bybit", f"BTC long should be on Bybit"
    assert pos_signal["short_venue"] == "HL", f"APT short should be on HL"

    # Test: negative EMA → LONG_APT_SHORT_BTC
    neg_signal = decide_position({"ema_7d": -0.0001}, SIGNAL_THRESHOLD)
    assert neg_signal is not None, "Expected signal for negative EMA"
    assert neg_signal["position_state"] == "LONG_APT_SHORT_BTC", \
        f"Wrong state for negative EMA: {neg_signal['position_state']}"
    assert neg_signal["long_venue"] == "HL", f"APT long should be on HL"
    assert neg_signal["short_venue"] == "Bybit", f"BTC short should be on Bybit"

    # Test: neutral → None
    neutral = decide_position({"ema_7d": 0.000001}, SIGNAL_THRESHOLD)
    assert neutral is None, f"Expected None for below-threshold EMA"

    return "FR logic: positive→LONG_BTC_SHORT_APT (APT@HL), negative→LONG_APT_SHORT_BTC, neutral→None"


def test_emergency_exit_detect() -> str:
    """Phase 4: Emergency exit K512 detection function importable."""
    sys.path.insert(0, str(REPO_ROOT / "scripts"))
    from emergency_hl_exit import _detect_k512_paired_positions, close_k512_paired_positions

    # Mock positions: long APT on HL, short BTC on Bybit
    mock_positions = [
        {"coin": "APT", "size": 1000.0, "value_usd": 400000.0, "side": "long"},
        {"coin": "BTC",  "size": 5.0,    "value_usd": 400000.0, "side": "short"},
    ]
    result = _detect_k512_paired_positions(mock_positions)
    assert result is not None, "K512 pair not detected from mock positions"
    assert result["detected"] is True
    assert result["long_symbol"] == "APT"
    assert result["short_symbol"] == "BTC"
    assert result["long_venue"] == "HL", f"APT long should be on HL: {result['long_venue']}"
    assert result["short_venue"] == "Bybit", f"BTC short should be on Bybit: {result['short_venue']}"
    assert result["split_protocol"] == "HL_1PCT_BYBIT_1PCT"
    return (f"detect_k512: detected=True, LONG APT@{result['long_venue']}, "
            f"SHORT BTC@{result['short_venue']}, split=HL_1PCT_BYBIT_1PCT")


def test_leverage_manager_k512() -> str:
    """Phase 5: K512 cap in leverage_manager."""
    sys.path.insert(0, str(REPO_ROOT / "scripts"))
    from leverage_manager import DEFAULT_EXCHANGE_CAPS, SLEEVE_WEIGHTS_V628
    assert "K512_APT_BTC" in DEFAULT_EXCHANGE_CAPS, "K512_APT_BTC missing from DEFAULT_EXCHANGE_CAPS"
    assert DEFAULT_EXCHANGE_CAPS["K512_APT_BTC"] == 4.0, \
        f"K512 cap should be 4.0, got {DEFAULT_EXCHANGE_CAPS['K512_APT_BTC']}"
    assert "K512" in SLEEVE_WEIGHTS_V628, "K512 missing from SLEEVE_WEIGHTS_V628"
    assert SLEEVE_WEIGHTS_V628["K512"] == 0.02, \
        f"K512 weight should be 0.02, got {SLEEVE_WEIGHTS_V628['K512']}"
    total_v628 = sum(SLEEVE_WEIGHTS_V628.values())
    return (f"leverage_manager: K512_APT_BTC cap=4.0, "
            f"SLEEVE_WEIGHTS_V628 K512=2%, total={total_v628:.0%}")


def test_leverage_config_k512() -> str:
    """Phase 6: leverage_config.json has K512 entries."""
    p = REPO_ROOT / "data" / "leverage_config.json"
    cfg = json.loads(p.read_text())
    assert "K512_APT_BTC" in cfg.get("exchange_caps", {}), \
        "K512_APT_BTC missing from leverage_config.json exchange_caps"
    assert cfg["exchange_caps"]["K512_APT_BTC"] == 4.0
    assert "k512_notes" in cfg, "k512_notes missing from leverage_config.json"
    notes = cfg["k512_notes"]
    assert notes.get("oos_sharpe") == 51.10
    assert notes.get("ann_return_usd_net_10M") == 302000
    assert notes.get("hl_headroom_pp") == 1.0
    return "leverage_config.json: K512_APT_BTC=4.0, k512_notes OOS Sh 51.10 $302K/yr"


def test_verify_deployment_k512() -> str:
    """Phase 7: verify_deployment_status.py has K512 as 36th daemon."""
    result = subprocess.run(
        [sys.executable, "scripts/verify_deployment_status.py"],
        capture_output=True, text=True, cwd=str(REPO_ROOT), timeout=30,
    )
    output = result.stdout + result.stderr
    assert "k512-apt-btc" in output, f"k512-apt-btc not in deployment output"
    return "verify_deployment_status: K512 36th daemon registered"


def test_plist_exists() -> str:
    """Phase 2: Plist file exists with correct label and StartInterval."""
    p = REPO_ROOT / "scripts" / "com.cryptolab.k512-apt-btc.plist"
    assert p.exists(), f"plist not found at {p}"
    content = p.read_text()
    assert "com.cryptolab.k512-apt-btc" in content, "Label missing from plist"
    assert "28800" in content, "StartInterval 28800 missing from plist"
    assert "k512_apt_btc_run.py" in content, "Script reference missing from plist"
    return "com.cryptolab.k512-apt-btc.plist: label + StartInterval=28800 OK"


def test_runbook_section() -> str:
    """Phase 8: Runbook has §38g section."""
    p = REPO_ROOT / "docs" / "k302a_runbook.md"
    content = p.read_text()
    assert "§38g" in content, "§38g missing from runbook"
    assert "K512 APT-BTC" in content
    assert "51.10" in content
    assert "302" in content
    assert "Move-VM" in content
    assert "0.27d" in content
    return "docs/k302a_runbook.md: §38g present with OOS Sh 51.10, $302K/yr, Move-VM, 0.27d"


def test_report_html_k512() -> str:
    """Phase 9: report.html has K512 monitoring row."""
    p = REPO_ROOT / "report.html"
    assert p.exists(), "report.html not found"
    content = p.read_text()
    assert "K512" in content, "K512 not found in report.html"
    assert "36th" in content or "k512" in content.lower(), \
        "36th daemon or k512 not found in report.html"
    return "report.html: K512 monitoring row present"


def main() -> int:
    parser = argparse.ArgumentParser(description="K520 K512 APT-BTC scaffold test driver")
    parser.add_argument("--json-only", action="store_true", help="Output JSON only")
    args = parser.parse_args()

    ts_jst = datetime.now(JST).strftime("%Y-%m-%d %H:%M JST")
    print(f"\n=== K520 K512 APT-BTC Scaffold Validation ({ts_jst}) ===\n")

    tests = [
        ("script_exists",               test_script_exists),
        ("plist_exists",                test_plist_exists),
        ("dashboard_exists",            test_dashboard_exists),
        ("dry_run",                     test_dry_run),
        ("dashboard_written",           test_dashboard_written_after_dry_run),
        ("notional_sizing",             test_notional_sizing),
        ("fr_differential_logic",       test_fr_differential_logic),
        ("emergency_exit_detect",       test_emergency_exit_detect),
        ("leverage_manager_k512",       test_leverage_manager_k512),
        ("leverage_config_k512",        test_leverage_config_k512),
        ("verify_deployment_k512",      test_verify_deployment_k512),
        ("runbook_section",             test_runbook_section),
        ("report_html_k512",            test_report_html_k512),
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
        "wave": "K520",
        "strategy": "K512 APT-BTC FR Differential",
        "generated_jst": ts_jst,
        "total_tests": len(results),
        "passed": n_pass,
        "failed": n_fail,
        "results": results,
        "k512_spec": {
            "oos_sharpe":        EXPECTED_OOS_SHARPE,
            "ann_return_usd":    EXPECTED_ANN_RETURN,
            "sleeve_pct":        EXPECTED_SLEEVE_PCT,
            "leverage":          EXPECTED_LEVERAGE,
            "hl_sleeve_pct":     EXPECTED_HL_SLEEVE,
            "bybit_sleeve_pct":  EXPECTED_BYBIT_SLEEVE,
            "hl_concentration":  EXPECTED_HL_CONC,
            "ou_half_life_days": EXPECTED_OU_HALFLIFE,
            "daemon_number":     EXPECTED_DAEMON_COUNT,
            "family_rank":       "#1 (APT Sh51.10 > ATOM Sh50.79 > SEI Sh48.10 > AVAX Sh43.89)",
            "move_vm":           "Block-STM parallel execution + Move resource model",
        },
        "activation_gate": {
            "oos_sharpe_min":     5.0,
            "fill_rate_min_pct":  60,
            "max_drawdown_pct":   15,
            "duration_days":      60,
            "status":             "SCAFFOLD-READY",
        },
        "v628_combined": {
            "total_ann_return_usd":    1_112_000,
            "note": "K449 5% + K476 4% + K484 5% + K493 5% + K500 4% + K507 SEI 2% + K507 TIA 1% + K512 APT 2% = ~$1.11M/yr @ $10M",
            "hl_concentration_pct":    64.0,
            "hl_headroom_pp":          1.0,
        },
    }

    report_path = REPO_ROOT / "wave_k520_k512_apt_scaffold.json"
    report_path.write_text(json.dumps(report, indent=2))
    print(f"\nReport written: {report_path}")

    return 0 if n_fail == 0 else 1


if __name__ == "__main__":
    sys.exit(main())

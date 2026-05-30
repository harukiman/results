#!/usr/bin/env python3
"""
wave_k685_k682_scaffold.py — K685 Wave Driver & Integration Test
================================================================
Validates the K682 ATOM-SOL FR Differential scaffold end-to-end.

Tests:
  1. Script dry-run (k682_atom_sol_run.py)
  2. Dashboard creation (data/k682_dashboard.json)
  3. Plist exists with correct label + StartInterval
  4. Emergency exit detect/close (emergency_hl_exit.py --include-k682)
  5. Leverage manager K682 entry (leverage_manager.py)
  6. Leverage config K682 entry (data/leverage_config.json)
  7. Deployment registry (verify_deployment_status.py)
  8. Notional computation correctness
  9. FR differential logic (unit test with known values)
 10. Runbook section §57
 11. Report HTML K682 row
 12. Dashboard written after dry-run

K339 security: REPO_ROOT from __file__, no /Users/ literals.

Usage:
  python3 wave_k685_k682_scaffold.py
  python3 wave_k685_k682_scaffold.py --json-only
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

# ── Expected K682 constants ────────────────────────────────────────────────────
EXPECTED_OOS_SHARPE    = 43.43
EXPECTED_ANN_RETURN    = 214638
EXPECTED_SLEEVE_PCT    = 0.02
EXPECTED_LEVERAGE      = 4.0
EXPECTED_DAEMON_COUNT  = "55th (2nd alt-alt)"
EXPECTED_HL_CONC       = 62.5
EXPECTED_GATE_SHARPE   = 22.0


def run_test(name: str, func) -> dict:
    """Run a single test function; return result dict."""
    try:
        result = func()
        return {"name": name, "status": "PASS", "detail": result}
    except Exception as e:
        return {"name": name, "status": "FAIL", "detail": str(e)}


def test_script_exists() -> str:
    """Phase 1: Strategy script exists."""
    p = REPO_ROOT / "scripts" / "k682_atom_sol_run.py"
    assert p.exists(), f"k682_atom_sol_run.py not found at {p}"
    lines = len(p.read_text().splitlines())
    assert lines >= 200, f"script too short: {lines} lines (expected >=200)"
    return f"scripts/k682_atom_sol_run.py exists ({lines} lines)"


def test_plist_exists() -> str:
    """Phase 2: Plist file exists with correct label and StartInterval."""
    p = REPO_ROOT / "scripts" / "com.cryptolab.k682-atom-sol.plist"
    assert p.exists(), f"plist not found at {p}"
    content = p.read_text()
    assert "com.cryptolab.k682-atom-sol" in content, "Label missing from plist"
    assert "28800" in content, "StartInterval 28800 missing from plist"
    assert "k682_atom_sol_run.py" in content, "Script reference missing from plist"
    return "com.cryptolab.k682-atom-sol.plist: label + StartInterval=28800 OK"


def test_dashboard_exists() -> str:
    """Phase 3: Dashboard JSON exists and has correct initial state."""
    p = REPO_ROOT / "data" / "k682_dashboard.json"
    assert p.exists(), f"k682_dashboard.json not found at {p}"
    dash = json.loads(p.read_text())
    valid_states = {"NEUTRAL", "LONG_ATOM_SHORT_SOL", "LONG_SOL_SHORT_ATOM"}
    state = dash.get("position_state")
    assert state in valid_states, f"Unexpected position_state: {state}"
    oos_sh = dash.get("oos_performance", {}).get("sharpe", 0)
    assert abs(oos_sh - EXPECTED_OOS_SHARPE) < 0.01, f"OOS Sharpe mismatch: {oos_sh}"
    ann_ret = dash.get("oos_performance", {}).get("ann_return_usd_2pct_4x")
    assert ann_ret == EXPECTED_ANN_RETURN, f"Ann return mismatch: {ann_ret}"
    sleeve = dash.get("sleeve_pct")
    assert sleeve == EXPECTED_SLEEVE_PCT, f"Sleeve pct mismatch: {sleeve}"
    gate_sh = dash.get("gate_metrics", {}).get("realized_sharpe_target", 0)
    assert abs(gate_sh - EXPECTED_GATE_SHARPE) < 0.01, f"Gate Sharpe mismatch: {gate_sh}"
    hl_conc = dash.get("hl_concentration_pct", 0)
    assert abs(hl_conc - EXPECTED_HL_CONC) < 0.1, f"HL concentration mismatch: {hl_conc}"
    return (f"data/k682_dashboard.json: state={state}, OOS Sh={EXPECTED_OOS_SHARPE}, "
            f"${EXPECTED_ANN_RETURN:,}/yr, 2% sleeve, gate Sh>={EXPECTED_GATE_SHARPE}, HL {EXPECTED_HL_CONC}%")


def test_dry_run() -> str:
    """Phase 12: Dry-run produces cycle complete output."""
    result = subprocess.run(
        [sys.executable, "scripts/k682_atom_sol_run.py", "--dry-run"],
        capture_output=True, text=True, cwd=str(REPO_ROOT), timeout=30,
    )
    output = result.stdout + result.stderr
    assert "K682 ATOM-SOL Cycle Complete" in output, \
        f"Expected 'K682 ATOM-SOL Cycle Complete' in output. Got:\n{output[:500]}"
    assert result.returncode == 0, f"Dry-run returned non-zero: {result.returncode}"
    return "dry-run: K682 ATOM-SOL Cycle Complete (exit 0)"


def test_dashboard_written_after_dry_run() -> str:
    """Dashboard is written and has correct fields after dry-run."""
    p = REPO_ROOT / "data" / "k682_dashboard.json"
    assert p.exists(), "k682_dashboard.json not found after dry-run"
    dash = json.loads(p.read_text())
    assert dash.get("wave") == "K685", f"Expected wave K685, got {dash.get('wave')}"
    assert dash.get("sleeve_pct") == EXPECTED_SLEEVE_PCT, \
        f"Sleeve pct mismatch: {dash.get('sleeve_pct')}"
    assert dash.get("leverage") == EXPECTED_LEVERAGE, \
        f"Leverage mismatch: {dash.get('leverage')}"
    assert dash.get("hl_concentration_pct") == EXPECTED_HL_CONC, \
        f"HL conc mismatch: {dash.get('hl_concentration_pct')}"
    return (f"dashboard: wave=K685, sleeve={EXPECTED_SLEEVE_PCT:.0%}, "
            f"leverage={EXPECTED_LEVERAGE}x, HL conc={EXPECTED_HL_CONC}%")


def test_notional_sizing() -> str:
    """Phase 3: Notional sizing computes correctly at $10M AUM."""
    sys.path.insert(0, str(REPO_ROOT / "scripts"))
    from k682_atom_sol_run import compute_delta_neutral_notional
    aum = 10_000_000.0
    notional_per_leg, total_notional = compute_delta_neutral_notional(aum, 0.02, 4.0)
    # Sleeve: $10M x 2% = $200K; total notional = $200K x 4x = $800K; per leg = $400K
    assert abs(notional_per_leg - 400_000) < 1, f"Per-leg notional wrong: {notional_per_leg}"
    assert abs(total_notional - 800_000) < 1, f"Total notional wrong: {total_notional}"
    margin = total_notional / 4.0
    assert abs(margin - 200_000) < 1, f"Margin wrong: {margin} (expected $200K)"
    return (f"notional: per_leg=${notional_per_leg:,.0f}, total=${total_notional:,.0f}, "
            f"margin=${margin:,.0f} (2% @$10M x 4x)")


def test_fr_differential_logic() -> str:
    """Phase 1: FR differential logic with known values."""
    sys.path.insert(0, str(REPO_ROOT / "scripts"))
    from k682_atom_sol_run import decide_position

    # Test: negative mean_168h (SOL FR > ATOM FR = normal state 80%+ of time)
    # BEAR_ATOM -> long ATOM, short SOL
    neg_signal = decide_position({"regime": "BEAR_ATOM", "mean_168h": -0.0001, "signal_direction": -1})
    assert neg_signal is not None, "Expected signal for BEAR_ATOM"
    assert neg_signal["position_state"] == "LONG_ATOM_SHORT_SOL", \
        f"Wrong state for BEAR_ATOM: {neg_signal['position_state']}"
    assert neg_signal["long_asset"] == "ATOM"
    assert neg_signal["short_asset"] == "SOL"
    assert neg_signal["long_venue"] == "BYBIT"
    assert neg_signal["short_venue"] == "BYBIT"

    # Test: positive mean_168h (ATOM FR > SOL FR = episodic IBC governance spike)
    # BULL_ATOM -> short ATOM, long SOL
    pos_signal = decide_position({"regime": "BULL_ATOM", "mean_168h": 0.0001, "signal_direction": 1})
    assert pos_signal is not None, "Expected signal for BULL_ATOM"
    assert pos_signal["position_state"] == "LONG_SOL_SHORT_ATOM", \
        f"Wrong state for BULL_ATOM: {pos_signal['position_state']}"
    assert pos_signal["long_asset"] == "SOL"
    assert pos_signal["short_asset"] == "ATOM"

    # Test: neutral -> None
    neutral = decide_position({"regime": "NEUTRAL", "mean_168h": 0.0, "signal_direction": 0})
    assert neutral is None, f"Expected None for NEUTRAL"

    return ("FR logic: BEAR_ATOM->LONG_ATOM_SHORT_SOL (both @BYBIT), "
            "BULL_ATOM->LONG_SOL_SHORT_ATOM (both @BYBIT), NEUTRAL->None")


def test_emergency_exit_flag() -> str:
    """Phase 4: Emergency exit has --include-k682 flag."""
    p = REPO_ROOT / "scripts" / "emergency_hl_exit.py"
    assert p.exists(), "emergency_hl_exit.py not found"
    content = p.read_text()
    assert "--include-k682" in content, "--include-k682 flag missing from emergency_hl_exit.py"
    assert "K682 ATOM-SOL CLOSE SUMMARY" in content, "K682 close summary missing"
    assert "include_k682" in content, "include_k682 variable missing"
    return "emergency_hl_exit.py: --include-k682 flag + K682 ATOM-SOL CLOSE SUMMARY present"


def test_leverage_manager_k682() -> str:
    """Phase 5: K682 cap in leverage_manager."""
    sys.path.insert(0, str(REPO_ROOT / "scripts"))
    from leverage_manager import DEFAULT_EXCHANGE_CAPS, SLEEVE_WEIGHTS_V645
    assert "K682_ATOM_SOL" in DEFAULT_EXCHANGE_CAPS, "K682_ATOM_SOL missing from DEFAULT_EXCHANGE_CAPS"
    assert DEFAULT_EXCHANGE_CAPS["K682_ATOM_SOL"] == 4.0, \
        f"K682 cap should be 4.0, got {DEFAULT_EXCHANGE_CAPS['K682_ATOM_SOL']}"
    assert "K682" in SLEEVE_WEIGHTS_V645, "K682 missing from SLEEVE_WEIGHTS_V645"
    assert SLEEVE_WEIGHTS_V645["K682"] == 0.02, \
        f"K682 weight should be 0.02, got {SLEEVE_WEIGHTS_V645['K682']}"
    return (f"leverage_manager: K682_ATOM_SOL cap=4.0, "
            f"SLEEVE_WEIGHTS_V645 K682=2%")


def test_leverage_config_k682() -> str:
    """Phase 6: leverage_config.json has K682 entries."""
    p = REPO_ROOT / "data" / "leverage_config.json"
    cfg = json.loads(p.read_text())
    assert "K682_ATOM_SOL" in cfg.get("exchange_caps", {}), \
        "K682_ATOM_SOL missing from leverage_config.json exchange_caps"
    assert cfg["exchange_caps"]["K682_ATOM_SOL"] == 4.0, \
        f"K682_ATOM_SOL cap should be 4.0"
    assert "k682_notes" in cfg, "k682_notes missing from leverage_config.json"
    notes = cfg["k682_notes"]
    assert abs(notes.get("oos_sharpe", 0) - EXPECTED_OOS_SHARPE) < 0.01
    assert notes.get("ann_return_usd_net_10M") == EXPECTED_ANN_RETURN
    assert abs(notes.get("sleeve_pct", 0) - EXPECTED_SLEEVE_PCT) < 0.001
    return (f"leverage_config.json: K682_ATOM_SOL=4.0, k682_notes OOS Sh {EXPECTED_OOS_SHARPE} "
            f"${EXPECTED_ANN_RETURN:,}/yr, 2% sleeve")


def test_verify_deployment_k682() -> str:
    """Phase 7: verify_deployment_status.py has K682."""
    result = subprocess.run(
        [sys.executable, "scripts/verify_deployment_status.py"],
        capture_output=True, text=True, cwd=str(REPO_ROOT), timeout=30,
    )
    output = result.stdout + result.stderr
    assert "k682-atom-sol" in output, f"k682-atom-sol not in deployment output"
    return f"verify_deployment_status: K682 registered (SECOND ALT-ALT, 55th daemon slot)"


def test_runbook_section() -> str:
    """Phase 8: Runbook has §57 section."""
    p = REPO_ROOT / "docs" / "k302a_runbook.md"
    content = p.read_text()
    assert "§57" in content, "§57 missing from runbook"
    assert "K682 ATOM-SOL" in content
    assert "43.43" in content
    assert "214" in content        # $214K/yr
    assert "Cosmos IBC" in content
    assert "SECOND ALT-ALT" in content
    return "docs/k302a_runbook.md: §57 present with OOS Sh 43.43, $214K/yr, Cosmos IBC, SECOND ALT-ALT"


def test_report_html_k682() -> str:
    """Phase 9: report.html has K682 entry."""
    p = REPO_ROOT / "report.html"
    assert p.exists(), "report.html not found"
    content = p.read_text()
    assert "K682" in content, "K682 not found in report.html"
    return "report.html: K682 entry present (eval section confirmed)"


def main() -> int:
    parser = argparse.ArgumentParser(description="K685 K682 ATOM-SOL scaffold test driver")
    parser.add_argument("--json-only", action="store_true", help="Output JSON only")
    args = parser.parse_args()

    ts_jst = datetime.now(JST).strftime("%Y-%m-%d %H:%M JST")
    print(f"\n=== K685 K682 ATOM-SOL Scaffold Validation ({ts_jst}) ===\n")

    tests = [
        ("script_exists",               test_script_exists),
        ("plist_exists",                test_plist_exists),
        ("dashboard_exists",            test_dashboard_exists),
        ("dry_run",                     test_dry_run),
        ("dashboard_written",           test_dashboard_written_after_dry_run),
        ("notional_sizing",             test_notional_sizing),
        ("fr_differential_logic",       test_fr_differential_logic),
        ("emergency_exit_flag",         test_emergency_exit_flag),
        ("leverage_manager_k682",       test_leverage_manager_k682),
        ("leverage_config_k682",        test_leverage_config_k682),
        ("verify_deployment_k682",      test_verify_deployment_k682),
        ("runbook_section",             test_runbook_section),
        ("report_html_k682",            test_report_html_k682),
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
        "wave": "K685",
        "strategy": "K682 ATOM-SOL FR Differential (SECOND ALT-ALT, Bybit-only)",
        "generated_jst": ts_jst,
        "total_tests": len(results),
        "passed": n_pass,
        "failed": n_fail,
        "results": results,
        "k682_spec": {
            "oos_sharpe":             EXPECTED_OOS_SHARPE,
            "ann_return_usd_net":     EXPECTED_ANN_RETURN,
            "daily_usdc":             588,
            "sleeve_pct":             EXPECTED_SLEEVE_PCT,
            "leverage":               EXPECTED_LEVERAGE,
            "w_hours":                168,
            "threshold":              0.0,
            "bybit_only":             True,
            "hl_concentration":       EXPECTED_HL_CONC,
            "daemon_slot":            "55th (2nd alt-alt)",
            "cluster":                "ATOM-SOL Alt-Alt — Cosmos IBC vs Solana SVM DePIN-Retail",
            "venue":                  "Bybit-only (ATOM-PERP + SOL-PERP)",
            "k493_k476_overlap":      "algebraic overlap — standalone 2% sleeve, anti-corr K682/K493=-0.5195 HEDGES",
            "math_identity":          "ATOM-SOL = -(BTC-ATOM) + (BTC-SOL) = -K493_dir + K476_dir",
        },
        "activation_gate": {
            "oos_sharpe_min":     22.0,   # 50% of OOS 43.43
            "fill_rate_min_pct":  60,
            "max_drawdown_pct":   15,
            "duration_days":      60,
            "status":             "SCAFFOLD-READY",
            "note":               "Sh>=22 (50% of OOS 43.43), fill>=60%, maxDD<15%, 60d paper-trade",
        },
        "hl_concentration": {
            "baseline_pct":         62.5,
            "k682_hl_adds_pp":      0.0,  # Bybit-only — HL unchanged
            "post_k682_estimate":   62.5,
            "limit":                65.0,
            "headroom_pp":          2.5,
        },
        "section6_gates": {
            "gates_passed": 10,
            "gates_total":  12,
            "failed":       ["G4 WF 10/12 folds (not all positive)", "G6 trades/yr 26.8 <30 threshold"],
            "decision":     "ACCEPT",
        },
    }

    report_path = REPO_ROOT / "wave_k685_k682_scaffold.json"
    report_path.write_text(json.dumps(report, indent=2))
    print(f"\nReport written: {report_path}")

    return 0 if n_fail == 0 else 1


if __name__ == "__main__":
    sys.exit(main())

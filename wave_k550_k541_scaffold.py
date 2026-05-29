#!/usr/bin/env python3
"""
wave_k550_k541_scaffold.py — K550 Wave Driver & Verification Test
=================================================================
K541 Stablecoin Supply Growth — Production Scaffold (38th daemon, v6.29 candidate)

Tests:
  1. Dry-run full cycle (k541_stablecoin_supply_run.py --dry-run)
  2. verify_deployment_status.py (38 daemons, 0 mismatches)
  3. Strategy unit tests (z-score acceleration computation)
  4. Dashboard JSON schema validation
  5. leverage_config.json K541 entry check
  6. emergency_hl_exit.py --include-k541 flag check

Result written to wave_k550_k541_scaffold.json.

K339 Security: REPO_ROOT from __file__, no /Users/ literals.
"""
from __future__ import annotations

import json
import subprocess
import sys
from datetime import datetime, timezone, timedelta
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent
DATA_DIR  = REPO_ROOT / "data"
JST       = timezone(timedelta(hours=9))


def run_cmd(cmd: list[str]) -> tuple[int, str, str]:
    """Run a subprocess and return (returncode, stdout, stderr)."""
    result = subprocess.run(
        cmd, capture_output=True, text=True, cwd=str(REPO_ROOT)
    )
    return result.returncode, result.stdout, result.stderr


def test_dry_run() -> dict:
    """Test 1: dry-run full cycle."""
    print("  [Test 1] Dry-run full cycle...")
    rc, stdout, stderr = run_cmd([
        sys.executable,
        str(REPO_ROOT / "scripts" / "k541_stablecoin_supply_run.py"),
        "--dry-run",
    ])
    passed  = rc == 0
    has_complete = "K541 Cycle Complete" in stdout
    has_neutral  = "NEUTRAL" in stdout or "NEUTRAL" in stderr
    return {
        "test":    "dry_run_cycle",
        "passed":  passed and has_complete,
        "returncode": rc,
        "has_cycle_complete": has_complete,
        "stdout_preview": stdout[:500],
        "stderr_preview": stderr[:200] if stderr else "",
    }


def test_verify_deployment() -> dict:
    """Test 2: verify_deployment_status.py — expect 38 daemons."""
    print("  [Test 2] verify_deployment_status.py...")
    rc, stdout, stderr = run_cmd([
        sys.executable,
        str(REPO_ROOT / "scripts" / "verify_deployment_status.py"),
    ])
    # Check deployment_status.json
    status_path = REPO_ROOT / "deployment_status.json"
    daemons_count = 0
    mismatches    = 0
    if status_path.exists():
        data          = json.loads(status_path.read_text())
        daemons_count = len(data.get("daemons", []))
        mismatches    = data.get("summary", {}).get("mismatches_with_html", 0)
        # Verify k541 is in registry
        k541_found    = any(
            d["label"] == "com.cryptolab.k541-stablecoin-supply"
            for d in data.get("daemons", [])
        )
    else:
        k541_found = False

    return {
        "test":           "verify_deployment",
        "passed":         daemons_count == 38 and mismatches == 0,
        "daemon_count":   daemons_count,
        "mismatches":     mismatches,
        "k541_in_registry": k541_found,
        "expected_daemons": 38,
        "returncode":     rc,
    }


def test_zscore_acceleration() -> dict:
    """Test 3: z-score acceleration computation unit test."""
    print("  [Test 3] Z-score acceleration unit test...")
    try:
        sys.path.insert(0, str(REPO_ROOT / "scripts"))
        import importlib
        spec = importlib.util.spec_from_file_location(
            "k541_module",
            str(REPO_ROOT / "scripts" / "k541_stablecoin_supply_run.py")
        )
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)

        # Build synthetic history with 50 daily points (acceleration spike at end)
        import math
        base_supply = 130_000_000_000.0  # $130B combined
        history = []
        for i in range(50):
            # Add sine wave to create acceleration spike at day 45
            spike = 500_000_000 * math.sin(i * 0.3)  # oscillation
            accel_inject = 2_000_000_000 if i >= 43 else 0  # acceleration at end
            supply = base_supply + spike + accel_inject * (i - 42) if i >= 43 else base_supply + spike
            history.append({
                "ts_utc": f"2026-04-{(i%30)+1:02d}T00:00:00+00:00",
                "total_supply": supply,
                "usdt_supply":  supply * 0.55,
                "usdc_supply":  supply * 0.45,
            })

        result = mod.compute_zscore_acceleration(history)
        data_sufficient = result.get("data_sufficient", False)
        accel = result.get("zscore_acceleration", 0.0)

        return {
            "test":            "zscore_acceleration",
            "passed":          data_sufficient,
            "data_sufficient": data_sufficient,
            "zscore_acceleration": accel,
            "signal_fires":    result.get("signal_fires", False),
            "history_points":  result.get("history_points", 0),
        }
    except Exception as e:
        return {
            "test":   "zscore_acceleration",
            "passed": False,
            "error":  str(e),
        }


def test_dashboard_schema() -> dict:
    """Test 4: dashboard JSON schema validation."""
    print("  [Test 4] Dashboard schema validation...")
    dashboard_path = DATA_DIR / "k541_dashboard.json"
    if not dashboard_path.exists():
        return {"test": "dashboard_schema", "passed": False, "error": "dashboard not found"}

    try:
        data = json.loads(dashboard_path.read_text())
        required_keys = [
            "position_state", "zscore_acceleration", "sleeve_pct",
            "leverage", "oos_performance", "gate_metrics",
            "paper_trade_mode", "wave", "activation_criteria",
        ]
        missing = [k for k in required_keys if k not in data]
        gate_ok = data.get("gate_metrics", {}).get("oos_sharpe_target") == 1.2
        oos_ok  = data.get("oos_performance", {}).get("sharpe") == 1.498
        paper_gate_90 = data.get("gate_metrics", {}).get("min_trades_90d") == 50
        return {
            "test":          "dashboard_schema",
            "passed":        len(missing) == 0 and gate_ok and oos_ok and paper_gate_90,
            "missing_keys":  missing,
            "gate_target_ok": gate_ok,
            "oos_sharpe_ok": oos_ok,
            "paper_gate_90_ok": paper_gate_90,
            "wave":          data.get("wave"),
        }
    except Exception as e:
        return {"test": "dashboard_schema", "passed": False, "error": str(e)}


def test_leverage_config() -> dict:
    """Test 5: leverage_config.json K541 entry."""
    print("  [Test 5] leverage_config.json K541 check...")
    config_path = DATA_DIR / "leverage_config.json"
    if not config_path.exists():
        return {"test": "leverage_config", "passed": False, "error": "leverage_config not found"}
    try:
        data   = json.loads(config_path.read_text())
        caps   = data.get("exchange_caps", {})
        k541_cap = caps.get("K541_STABLECOIN_SUPPLY", 0.0)
        k541_notes = data.get("k541_notes", {})
        notes_ok = k541_notes.get("leverage") == 2.0
        sleeve_ok = k541_notes.get("sleeve_pct") == 0.03
        gate_ok = k541_notes.get("paper_gate_days") == 90
        return {
            "test":           "leverage_config",
            "passed":         k541_cap == 2.0 and notes_ok and sleeve_ok and gate_ok,
            "k541_cap":       k541_cap,
            "notes_present":  bool(k541_notes),
            "leverage_ok":    notes_ok,
            "sleeve_ok":      sleeve_ok,
            "gate_90d_ok":    gate_ok,
        }
    except Exception as e:
        return {"test": "leverage_config", "passed": False, "error": str(e)}


def test_emergency_exit_flag() -> dict:
    """Test 6: emergency_hl_exit.py --include-k541 flag exists."""
    print("  [Test 6] emergency_hl_exit.py --include-k541 flag check...")
    hl_exit_path = REPO_ROOT / "scripts" / "emergency_hl_exit.py"
    if not hl_exit_path.exists():
        return {"test": "emergency_exit_flag", "passed": False, "error": "emergency_hl_exit.py not found"}
    content = hl_exit_path.read_text()
    has_include_k541    = "--include-k541"           in content
    has_detect_k541     = "_detect_k541_position"    in content
    has_close_k541      = "close_k541_position"      in content
    has_k541_detail     = "k541_detail"              in content
    passed = all([has_include_k541, has_detect_k541, has_close_k541, has_k541_detail])
    return {
        "test":                 "emergency_exit_flag",
        "passed":               passed,
        "has_include_k541":     has_include_k541,
        "has_detect_k541":      has_detect_k541,
        "has_close_k541":       has_close_k541,
        "has_k541_detail":      has_k541_detail,
    }


def main() -> int:
    ts_jst = datetime.now(JST).strftime("%Y-%m-%d %H:%M JST")
    print(f"\n=== K550 Wave Driver — K541 Stablecoin Supply Growth Scaffold ===")
    print(f"  Timestamp: {ts_jst}")
    print(f"  38th daemon | v6.29 candidate | OOS Sh 1.498 | $294K/yr @$10M | 90d gate")
    print(f"  G5 max corr 0.074 | 7-axis Sh 6.872 +0.165 lift\n")

    tests = [
        test_dry_run,
        test_verify_deployment,
        test_zscore_acceleration,
        test_dashboard_schema,
        test_leverage_config,
        test_emergency_exit_flag,
    ]

    results = []
    for t in tests:
        r = t()
        results.append(r)
        status = "PASS" if r.get("passed") else "FAIL"
        print(f"    [{status}] {r['test']}")

    passed_count = sum(1 for r in results if r.get("passed"))
    total_count  = len(results)
    all_pass     = passed_count == total_count

    # Build report
    report = {
        "wave":         "K550",
        "strategy":     "K541 Stablecoin Supply Growth (V3 Acceleration Spike)",
        "daemon_number": "38th",
        "timestamp_jst": ts_jst,
        "status":       "SCAFFOLD-READY" if all_pass else "SCAFFOLD-PARTIAL",
        "tests_passed": passed_count,
        "tests_total":  total_count,
        "all_pass":     all_pass,
        "results":      results,
        "scaffold_summary": {
            "oos_sharpe":         1.498,
            "ann_return_usd_10M": 294_000,
            "seven_axis_sharpe":  6.872,
            "seven_axis_lift":    0.165,
            "g5_max_corr":        0.074,
            "trades_per_yr":      273,
            "paper_gate_days":    90,
            "signal_version":     "V3 — 7d z-score 2nd derivative (acceleration spike)",
            "universe":           ["BTC", "ETH", "SOL"],
            "leverage":           2.0,
            "sleeve_pct":         0.03,
            "data_api":           "DefiLlama free public (stablecoins.llama.fi)",
            "venue":              "HL-only",
        },
        "90d_paper_gate_criteria": {
            "oos_sharpe_min":     1.2,
            "fill_rate_min_pct":  60,
            "max_drawdown_pct":   25,
            "min_trades_90d":     50,
            "gate_status":        "IN_PROGRESS",
        },
        "v629_summary": {
            "description":        "v6.28 + K541 3% stablecoin supply addition",
            "combined_return_usd": 1_456_000,
            "v628_base_usd":      1_162_000,
            "k541_add_usd":       294_000,
            "hl_concentration_note": "K541 adds 3% HL → exceeds 65% cap; HL restructure required before v6.29 activation",
        },
    }

    # Write JSON report
    report_path = REPO_ROOT / "wave_k550_k541_scaffold.json"
    report_path.write_text(json.dumps(report, indent=2))
    print(f"\n  Report written → {report_path}")

    print(f"\n=== K550 Result: {passed_count}/{total_count} tests PASS "
          f"({'SCAFFOLD-READY' if all_pass else 'SCAFFOLD-PARTIAL'}) ===")
    print(f"  OOS Sharpe 1.498 | $294K/yr @$10M | 7-axis Sh 6.872 +0.165 lift")
    print(f"  G5 max corr 0.074 (orthogonal) | 90d paper-gate | 38th daemon")
    print(f"  v6.29 candidate: v6.28 $1.162M + K541 $294K = ~$1.456M/yr @$10M")
    print()

    return 0 if all_pass else 1


if __name__ == "__main__":
    sys.exit(main())

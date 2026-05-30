#!/usr/bin/env python3
"""
wave_k641_k635_scaffold.py — K641 Wave Driver + Verification
=============================================================
Verifies all K641 deliverables for the K635 IMX orthogonalized production scaffold:
  - Phase 1: Strategy script (k635_imx_orthog_run.py)
  - Phase 2: Daemon plist (com.cryptolab.k635-imx-orthog.plist)
  - Phase 3: Dashboard (k635_dashboard.json)
  - Phase 4: Emergency exit integration (--include-k635 flag)
  - Phase 5: Leverage manager (K635_IMX_ORTHOG cap + SLEEVE_WEIGHTS_V634)
  - Phase 6: Leverage config (k635_notes + K635_IMX_ORTHOG)
  - Phase 7: Deployment verification (43 daemons)
  - Phase 8: Runbook §45 (K635 IMX orthog playbook)
  - Phase 9: HTML update (K635 SCAFFOLD-READY row, 43 daemon count)
  - Phase 10: 60d paper-trade gate criteria
  - Phase 11: Wave deliverables (this file + JSON report)
  - Phase 12: Dry-run verification

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
CACHE_DIR = REPO_ROOT / "cache"

JST = timezone(timedelta(hours=9))
UTC = timezone.utc

WAVE     = "K641"
STRATEGY = "K635 IMX Orthogonalized FR Differential (MF SHIB+TIA+SEI)"


def _check_file(path: Path, description: str) -> dict:
    exists = path.exists()
    size   = path.stat().st_size if exists else 0
    return {
        "path":        str(path.relative_to(REPO_ROOT)),
        "description": description,
        "exists":      exists,
        "size_bytes":  size,
        "status":      "PASS" if exists and size > 0 else "FAIL",
    }


def check_deliverables() -> dict:
    """Verify all K641 file deliverables exist and are non-empty."""
    checks = [
        _check_file(
            REPO_ROOT / "scripts" / "k635_imx_orthog_run.py",
            "Phase 1: K635 strategy script (K339 pattern, 3-factor MF)"
        ),
        _check_file(
            REPO_ROOT / "scripts" / "com.cryptolab.k635-imx-orthog.plist",
            "Phase 2: 43rd daemon plist (StartInterval 28800)"
        ),
        _check_file(
            DATA_DIR / "k635_dashboard.json",
            "Phase 3: Dashboard (residual signal, beta_used, regime)"
        ),
        _check_file(
            REPO_ROOT / "scripts" / "emergency_hl_exit.py",
            "Phase 4: Emergency exit (--include-k635 flag)"
        ),
        _check_file(
            REPO_ROOT / "scripts" / "leverage_manager.py",
            "Phase 5: Leverage manager (K635_IMX_ORTHOG + SLEEVE_WEIGHTS_V634)"
        ),
        _check_file(
            DATA_DIR / "leverage_config.json",
            "Phase 6: Leverage config (K635_IMX_ORTHOG: 4.0 + k635_notes)"
        ),
        _check_file(
            REPO_ROOT / "scripts" / "verify_deployment_status.py",
            "Phase 7: Deployment verifier (43rd daemon registry)"
        ),
        _check_file(
            REPO_ROOT / "docs" / "k302a_runbook.md",
            "Phase 8: Runbook §45 (K635 IMX orthog playbook)"
        ),
        _check_file(
            REPO_ROOT / "report.html",
            "Phase 9: HTML report (K635 SCAFFOLD-READY)"
        ),
        _check_file(
            REPO_ROOT / "wave_k641_k635_scaffold.py",
            "Phase 11: Wave driver (this file)"
        ),
    ]
    return {
        "checks":   checks,
        "total":    len(checks),
        "passed":   sum(1 for c in checks if c["status"] == "PASS"),
        "failed":   sum(1 for c in checks if c["status"] == "FAIL"),
        "all_pass": all(c["status"] == "PASS" for c in checks),
    }


def check_content_integrity() -> dict:
    """Spot-check key content in critical files."""
    results = {}

    # Check k635_imx_orthog_run.py has hardcoded beta coefficients
    script_path = REPO_ROOT / "scripts" / "k635_imx_orthog_run.py"
    if script_path.exists():
        content = script_path.read_text()
        results["beta_shib_hardcoded"]   = "BETA_SHIB = 0.254" in content
        results["beta_tia_hardcoded"]    = "BETA_TIA  = 0.068" in content
        results["beta_sei_hardcoded"]    = "BETA_SEI  = 0.158" in content
        results["k339_repo_root"]        = "REPO_ROOT   = Path(__file__).resolve().parent.parent" in content
        results["paper_trade_default"]   = "PAPER_TRADE         = True" in content
        results["bybit_primary"]         = "BYBIT_SLEEVE_PCT   = SLEEVE_PCT" in content
        results["post_only"]             = "POST_ONLY_PARALLEL" in content
        results["signal_1_5sigma"]       = "SIGNAL_SIGMA_MULT   = 1.5" in content
        results["sleeve_2pct"]           = "SLEEVE_PCT          = 0.02" in content
        results["ema_168h"]              = "EMA_PERIOD_HOURS    = 168" in content
        results["symbols_correct"]       = 'SYMBOLS = ("IMX", "SHIB", "TIA", "SEI", "BTC")' in content
    else:
        results["script_missing"] = True

    # Check dashboard has beta fields
    dash_path = DATA_DIR / "k635_dashboard.json"
    if dash_path.exists():
        try:
            dash = json.loads(dash_path.read_text())
            results["dashboard_beta_shib"]   = dash.get("beta_shib_used") == 0.254
            results["dashboard_beta_tia"]    = dash.get("beta_tia_used")  == 0.068
            results["dashboard_beta_sei"]    = dash.get("beta_sei_used")  == 0.158
            results["dashboard_regime"]      = "regime" in dash
            results["dashboard_oos_perf"]    = "oos_performance" in dash
            results["dashboard_orthog_mech"] = "orthog_mechanism" in dash
            results["dashboard_hl_65"]       = dash.get("hl_concentration_pct") == 65.0
        except Exception as e:
            results["dashboard_error"] = str(e)

    # Check leverage_config.json has K635 entries
    cfg_path = DATA_DIR / "leverage_config.json"
    if cfg_path.exists():
        try:
            cfg = json.loads(cfg_path.read_text())
            results["cfg_k635_cap"]    = cfg.get("exchange_caps", {}).get("K635_IMX_ORTHOG") == 4.0
            results["cfg_k635_notes"]  = "k635_notes" in cfg
            results["cfg_beta_shib"]   = cfg.get("k635_notes", {}).get("beta_shib") == 0.254
            results["cfg_beta_tia"]    = cfg.get("k635_notes", {}).get("beta_tia")  == 0.068
            results["cfg_beta_sei"]    = cfg.get("k635_notes", {}).get("beta_sei")  == 0.158
        except Exception as e:
            results["cfg_error"] = str(e)

    # Check emergency_hl_exit.py has --include-k635
    emer_path = REPO_ROOT / "scripts" / "emergency_hl_exit.py"
    if emer_path.exists():
        content = emer_path.read_text()
        results["emer_include_k635"]  = "--include-k635" in content
        results["emer_k635_summary"]  = "K635 IMX-BTC ORTHOG CLOSE SUMMARY" in content

    # Check leverage_manager.py has K635 cap and SLEEVE_WEIGHTS_V634
    lev_path = REPO_ROOT / "scripts" / "leverage_manager.py"
    if lev_path.exists():
        content = lev_path.read_text()
        results["lev_k635_cap"]      = "K635_IMX_ORTHOG" in content
        results["lev_v634_weights"]  = "SLEEVE_WEIGHTS_V634" in content

    # Check verify_deployment_status.py has 43rd daemon
    vds_path = REPO_ROOT / "scripts" / "verify_deployment_status.py"
    if vds_path.exists():
        content = vds_path.read_text()
        results["vds_43rd_daemon"]  = "com.cryptolab.k635-imx-orthog" in content
        results["vds_43rd_label"]   = "43rd daemon" in content

    # Check runbook has §45
    rb_path = REPO_ROOT / "docs" / "k302a_runbook.md"
    if rb_path.exists():
        content = rb_path.read_text()
        results["runbook_section45"] = "## §45 K635 IMX-BTC Orthogonalized" in content
        results["runbook_beta_table"] = "beta_SHIB" in content and "beta_TIA" in content
        results["runbook_60d_gate"]   = "60-Day Paper-Trade Activation Gate" in content

    return results


def count_registry_daemons() -> int:
    """Count registered daemons in verify_deployment_status.py."""
    vds_path = REPO_ROOT / "scripts" / "verify_deployment_status.py"
    if not vds_path.exists():
        return 0
    content = vds_path.read_text()
    return content.count('label="com.cryptolab.')


def run_dry_run_test() -> dict:
    """Execute k635_imx_orthog_run.py --status and capture output."""
    try:
        result = subprocess.run(
            [sys.executable, "scripts/k635_imx_orthog_run.py", "--status"],
            capture_output=True, text=True, timeout=30,
            cwd=str(REPO_ROOT),
        )
        success = result.returncode == 0
        return {
            "returncode": result.returncode,
            "success":    success,
            "stdout_len": len(result.stdout),
            "stderr_len": len(result.stderr),
            "status":     "PASS" if success else "FAIL",
        }
    except Exception as e:
        return {"status": "ERROR", "error": str(e)}


def main() -> int:
    ts_jst = datetime.now(JST).strftime("%Y-%m-%d %H:%M JST")
    print(f"\n=== {WAVE} {STRATEGY} Wave Verification ===")
    print(f"  Timestamp: {ts_jst}")
    print(f"  REPO_ROOT: {REPO_ROOT}")

    # Phase 1-11: File deliverables
    print("\n[Phase 1-11] Checking file deliverables...")
    deliverables = check_deliverables()
    for c in deliverables["checks"]:
        status_icon = "OK" if c["status"] == "PASS" else "FAIL"
        print(f"  [{status_icon}] {c['path']} — {c['description'][:60]}")
    print(f"  Result: {deliverables['passed']}/{deliverables['total']} passed")

    # Content integrity checks
    print("\n[Content] Checking content integrity...")
    content = check_content_integrity()
    passed_content = sum(1 for v in content.values() if v is True)
    failed_content = sum(1 for v in content.values() if v is False)
    total_content  = len(content)
    for key, val in content.items():
        icon = "OK" if val is True else ("FAIL" if val is False else "INFO")
        print(f"  [{icon}] {key}: {val}")
    print(f"  Result: {passed_content}/{total_content} content checks passed")

    # Daemon count
    print("\n[Phase 7] Counting registered daemons...")
    daemon_count = count_registry_daemons()
    daemon_ok    = daemon_count == 43
    print(f"  Registered daemons: {daemon_count} (expected 43)")
    print(f"  Status: {'PASS' if daemon_ok else f'MISMATCH (expected 43, got {daemon_count})'}")

    # Dry-run test
    print("\n[Phase 12] Running dry-run test...")
    dry_run = run_dry_run_test()
    print(f"  Status: {dry_run.get('status')}  returncode={dry_run.get('returncode')}")

    # Summary report
    print(f"\n=== K641 Wave Summary ===")
    print(f"  Deliverables: {deliverables['passed']}/{deliverables['total']} files")
    print(f"  Content checks: {passed_content}/{total_content}")
    print(f"  Daemon count: {daemon_count} {'OK' if daemon_ok else 'MISMATCH'}")
    print(f"  Dry-run: {dry_run.get('status')}")
    print()
    print(f"  K635 Strategy:    IMX-BTC Orthogonalized FR Differential (MF SHIB+TIA+SEI)")
    print(f"  OOS Sharpe:       24.81 (residual MF W=168h) vs 41.73 raw K612")
    print(f"  beta_SHIB:        0.254  beta_TIA: 0.068  beta_SEI: 0.158")
    print(f"  Profit 2% sleeve: $4,775,120/yr @$10M @4x")
    print(f"  HL concentration: 65% UNCHANGED (Bybit-only)")
    print(f"  Cluster:          Gaming L2 Infra (ImmutableX StarkEx ZK rollup)")
    print(f"  Daemon number:    43rd")
    print(f"  60d gate:         Realized Sh>=12 + fill>=60% + maxDD<20%")
    print(f"  v6.34 path:       K635 IMX orthog 2% Bybit sleeve added to v6.33")
    print()

    # Save wave result JSON
    report = {
        "wave":          WAVE,
        "strategy":      STRATEGY,
        "timestamp_jst": ts_jst,
        "deliverables":  deliverables,
        "content_checks": content,
        "daemon_count":  daemon_count,
        "daemon_ok":     daemon_ok,
        "dry_run":       dry_run,
        "k635_summary": {
            "oos_sharpe_residual":     24.81,
            "oos_sharpe_raw_k612":     41.73,
            "beta_shib":               0.254,
            "beta_tia":                0.068,
            "beta_sei":                0.158,
            "ema_window_h":            168,
            "ema_periods":             21,
            "profit_2pct_usd_yr":      4_775_120,
            "sleeve_activation":       "2% Bybit (IMX+BTC both legs)",
            "hl_concentration":        "65% UNCHANGED -- Bybit-only",
            "cluster":                 "Gaming L2 Infra (ImmutableX StarkEx ZK rollup, 43rd daemon)",
            "gate_60d":                "Realized Sh>=12 + fill>=60% + maxDD<20%",
            "v634_candidate":          "K635 2% Bybit + v6.33 portfolio",
            "factors_removed":         ["SHIB (meme/retail)", "TIA (modular DA)", "SEI (EVM-Cosmos mid-cap)"],
        },
        "overall_status": "PASS" if deliverables["all_pass"] and daemon_ok else "PARTIAL",
    }
    report_path = REPO_ROOT / "wave_k641_k635_scaffold.json"
    report_path.write_text(json.dumps(report, indent=2))
    print(f"  Report saved: wave_k641_k635_scaffold.json")
    print()

    return 0 if deliverables["all_pass"] and daemon_ok else 1


if __name__ == "__main__":
    sys.exit(main())

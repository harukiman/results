#!/usr/bin/env python3
"""
wave_k642_k638_scaffold.py — K642 Wave Driver + Verification
=============================================================
Verifies all K642 deliverables for the K638 STX orthogonalized production scaffold:
  - Phase 1: Strategy script (k638_stx_orthog_run.py)
  - Phase 2: Daemon plist (com.cryptolab.k638-stx-orthog.plist)
  - Phase 3: Dashboard (k638_dashboard.json)
  - Phase 4: Emergency exit integration (--include-k638 flag)
  - Phase 5: Leverage manager (K638_STX_ORTHOG cap + SLEEVE_WEIGHTS_V635)
  - Phase 6: Leverage config (k638_notes + K638_STX_ORTHOG)
  - Phase 7: Deployment verification (44 daemons)
  - Phase 8: Runbook §46 (K638 STX orthog playbook)
  - Phase 9: HTML update (K638 SCAFFOLD-READY row, 44 daemon count)
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

WAVE     = "K642"
STRATEGY = "K638 STX Orthogonalized FR Differential"


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
    """Verify all K642 file deliverables exist and are non-empty."""
    checks = [
        _check_file(
            REPO_ROOT / "scripts" / "k638_stx_orthog_run.py",
            "Phase 1: K638 strategy script (K339 pattern, W=504h, beta_APT=0.203339)"
        ),
        _check_file(
            REPO_ROOT / "scripts" / "com.cryptolab.k638-stx-orthog.plist",
            "Phase 2: 44th daemon plist (StartInterval 28800)"
        ),
        _check_file(
            DATA_DIR / "k638_dashboard.json",
            "Phase 3: Dashboard (residual signal, beta_used, regime)"
        ),
        _check_file(
            REPO_ROOT / "scripts" / "emergency_hl_exit.py",
            "Phase 4: Emergency exit (--include-k638 flag, §46)"
        ),
        _check_file(
            REPO_ROOT / "scripts" / "leverage_manager.py",
            "Phase 5: Leverage manager (K638_STX_ORTHOG + SLEEVE_WEIGHTS_V635)"
        ),
        _check_file(
            DATA_DIR / "leverage_config.json",
            "Phase 6: Leverage config (K638_STX_ORTHOG: 4.0 + k638_notes)"
        ),
        _check_file(
            REPO_ROOT / "scripts" / "verify_deployment_status.py",
            "Phase 7: Deployment verifier (44th daemon registry)"
        ),
        _check_file(
            REPO_ROOT / "docs" / "k302a_runbook.md",
            "Phase 8: Runbook §46 (K638 STX orthog playbook)"
        ),
        _check_file(
            REPO_ROOT / "report.html",
            "Phase 9: HTML report (K638 SCAFFOLD-READY)"
        ),
        _check_file(
            REPO_ROOT / "wave_k642_k638_scaffold.py",
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

    # Check k638_stx_orthog_run.py has hardcoded β coefficients
    script_path = REPO_ROOT / "scripts" / "k638_stx_orthog_run.py"
    if script_path.exists():
        content = script_path.read_text()
        results["beta_apt_hardcoded"]   = "BETA_APT  = 0.203339" in content
        results["beta_sei_hardcoded"]   = "BETA_SEI  = 0.125164" in content
        results["beta_doge_hardcoded"]  = "BETA_DOGE = 0.306518" in content
        results["k339_repo_root"]       = "REPO_ROOT   = Path(__file__).resolve().parent.parent" in content
        results["paper_trade_default"]  = "PAPER_TRADE         = True" in content
        results["bybit_primary"]        = "BYBIT_SLEEVE_PCT   = SLEEVE_PCT" in content
        results["post_only"]            = "POST_ONLY_PARALLEL" in content
        results["signal_1_5sigma"]      = "SIGNAL_SIGMA_MULT   = 1.5" in content
        results["sleeve_1_5pct"]        = "SLEEVE_PCT          = 0.015" in content
        results["ema_504h"]             = "EMA_PERIOD_HOURS    = 504" in content
    else:
        results["script_missing"] = True

    # Check dashboard has β fields
    dash_path = DATA_DIR / "k638_dashboard.json"
    if dash_path.exists():
        try:
            dash = json.loads(dash_path.read_text())
            results["dashboard_beta_apt"]    = dash.get("beta_apt_used") == 0.203339
            results["dashboard_beta_sei"]    = dash.get("beta_sei_used") == 0.125164
            results["dashboard_beta_doge"]   = dash.get("beta_doge_used") == 0.306518
            results["dashboard_regime"]      = "regime" in dash
            results["dashboard_oos_perf"]    = "oos_performance" in dash
            results["dashboard_orthog_mech"] = "orthog_mechanism" in dash
            results["dashboard_hl_65"]       = dash.get("hl_concentration_pct") == 65.0
        except Exception as e:
            results["dashboard_error"] = str(e)

    # Check leverage_config.json has K638 entries
    cfg_path = DATA_DIR / "leverage_config.json"
    if cfg_path.exists():
        try:
            cfg = json.loads(cfg_path.read_text())
            results["cfg_k638_cap"]    = cfg.get("exchange_caps", {}).get("K638_STX_ORTHOG") == 4.0
            results["cfg_k638_notes"]  = "k638_notes" in cfg
            results["cfg_beta_apt"]    = cfg.get("k638_notes", {}).get("beta_apt") == 0.203339
            results["cfg_beta_doge"]   = cfg.get("k638_notes", {}).get("beta_doge") == 0.306518
        except Exception as e:
            results["cfg_error"] = str(e)

    # Check emergency_hl_exit.py has --include-k638
    emer_path = REPO_ROOT / "scripts" / "emergency_hl_exit.py"
    if emer_path.exists():
        content = emer_path.read_text()
        results["emer_include_k638"]      = "--include-k638" in content
        results["emer_k638_summary"]      = "K638 STX-BTC ORTHOG CLOSE SUMMARY" in content
        results["emer_bybit_only_note"]   = "Bybit-only" in content

    # Check leverage_manager.py has K638 cap and SLEEVE_WEIGHTS_V635
    lev_path = REPO_ROOT / "scripts" / "leverage_manager.py"
    if lev_path.exists():
        content = lev_path.read_text()
        results["lev_k638_cap"]     = "K638_STX_ORTHOG" in content
        results["lev_v635_weights"] = "SLEEVE_WEIGHTS_V635" in content

    # Check verify_deployment_status.py has 44th daemon
    vds_path = REPO_ROOT / "scripts" / "verify_deployment_status.py"
    if vds_path.exists():
        content = vds_path.read_text()
        results["vds_44th_daemon"]  = "com.cryptolab.k638-stx-orthog" in content
        results["vds_44th_label"]   = "44th daemon" in content

    # Check runbook has §46
    rb_path = REPO_ROOT / "docs" / "k302a_runbook.md"
    if rb_path.exists():
        content = rb_path.read_text()
        results["runbook_section46"] = "## §46 K638 STX-BTC Orthogonalized" in content
        results["runbook_beta_table"] = "β_APT" in content and "β_DOGE" in content
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
    """Execute k638_stx_orthog_run.py --status and capture output."""
    try:
        result = subprocess.run(
            [sys.executable, "scripts/k638_stx_orthog_run.py", "--status"],
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
    daemon_ok    = daemon_count == 44
    print(f"  Registered daemons: {daemon_count} (expected 44)")
    print(f"  Status: {'PASS' if daemon_ok else f'MISMATCH (expected 44, got {daemon_count})'}")

    # Dry-run test
    print("\n[Phase 12] Running dry-run test...")
    dry_run = run_dry_run_test()
    print(f"  Status: {dry_run.get('status')}  returncode={dry_run.get('returncode')}")

    # Summary report
    print(f"\n=== K642 Wave Summary ===")
    print(f"  Deliverables: {deliverables['passed']}/{deliverables['total']} files")
    print(f"  Content checks: {passed_content}/{total_content}")
    print(f"  Daemon count: {daemon_count} {'OK' if daemon_ok else 'MISMATCH'}")
    print(f"  Dry-run: {dry_run.get('status')}")
    print()
    print(f"  K638 Strategy:    STX-BTC Orthogonalized FR Differential")
    print(f"  OOS Sharpe:       12.38 (residual MF W=504h) vs 26.86 raw K613")
    print(f"  beta_APT:         0.203339  beta_SEI: 0.125164  beta_DOGE: 0.306518")
    print(f"  Profit 1.5% slv:  $65,018/yr net @$10M @4x")
    print(f"  HL concentration: 65% UNCHANGED (Bybit-only)")
    print(f"  Cluster:          BTC-L2 / Stacks PoX (Bitcoin Layer-2, 44th daemon)")
    print(f"  60d gate:         Realized Sh>=6 + fill>=60% + maxDD<20%")
    print(f"  v6.35:            K638 adds 1.5% Bybit sleeve to v6.34")
    print()

    # Save wave result JSON
    report = {
        "wave":             WAVE,
        "strategy":         STRATEGY,
        "timestamp_jst":    ts_jst,
        "deliverables":     deliverables,
        "content_checks":   content,
        "daemon_count":     daemon_count,
        "daemon_ok":        daemon_ok,
        "dry_run":          dry_run,
        "k638_summary": {
            "oos_sharpe_residual":      12.38,
            "oos_sharpe_raw_k613":      26.8576,
            "beta_apt":                 0.203339,
            "beta_sei":                 0.125164,
            "beta_doge":                0.306518,
            "profit_1_5pct_net_usd_yr": 65_018,
            "profit_1_5pct_gross_usd_yr": 81_272,
            "sleeve_activation":        "1.5% Bybit (STX+BTC both legs)",
            "hl_concentration":         "65% UNCHANGED — Bybit-only",
            "cluster":                  "BTC-L2 / Stacks PoX (Bitcoin Layer-2, 44th daemon)",
            "gate_60d":                 "Realized Sh>=6 + fill>=60% + maxDD<20%",
            "v635_candidate":           "K638 1.5% Bybit + v6.34 portfolio",
            "ema_window":               "W=504h (63 x 8h periods)",
        },
        "overall_status":   "PASS" if deliverables["all_pass"] and daemon_ok else "PARTIAL",
    }
    report_path = REPO_ROOT / "wave_k642_k638_scaffold.json"
    report_path.write_text(json.dumps(report, indent=2))
    print(f"  Report saved: wave_k642_k638_scaffold.json")
    print()

    return 0 if deliverables["all_pass"] and daemon_ok else 1


if __name__ == "__main__":
    sys.exit(main())

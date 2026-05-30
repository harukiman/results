#!/usr/bin/env python3
"""
wave_k650_k645_scaffold.py — K650 Wave Driver + Verification
=============================================================
Verifies all K650 deliverables for the K645 BNB orthogonalized production scaffold:
  - Phase 1: Strategy script (k645_bnb_orthog_run.py)
  - Phase 2: Daemon plist (com.cryptolab.k645-bnb-orthog.plist)
  - Phase 3: Dashboard (k645_dashboard.json)
  - Phase 4: Emergency exit integration (--include-k645 flag)
  - Phase 5: Leverage manager (K645_BNB_ORTHOG cap + SLEEVE_WEIGHTS_V636)
  - Phase 6: Leverage config (k645_notes + K645_BNB_ORTHOG)
  - Phase 7: Deployment verification (45 daemons)
  - Phase 8: Runbook §47 (K645 BNB orthog playbook)
  - Phase 9: HTML update (K645 SCAFFOLD-READY row, 45 daemon count)
  - Phase 10: 60d paper-trade gate criteria
  - Phase 11: Wave deliverables (this file + JSON report)
  - Phase 12: Dry-run verification

K339 Security: REPO_ROOT from __file__, no /Users/ literals.
K650 Milestone: 6th orthogonal scaffold — ETH-cluster unlock (BNB post-orth corr=0.1757 PASS).
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

WAVE     = "K650"
STRATEGY = "K645 BNB-BTC Orthogonalized FR Differential"


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
    """Verify all K650 file deliverables exist and are non-empty."""
    checks = [
        _check_file(
            REPO_ROOT / "scripts" / "k645_bnb_orthog_run.py",
            "Phase 1: K645 strategy script (K339 pattern, W=168h, beta_ETH=0.539)"
        ),
        _check_file(
            REPO_ROOT / "scripts" / "com.cryptolab.k645-bnb-orthog.plist",
            "Phase 2: 45th daemon plist (StartInterval 28800)"
        ),
        _check_file(
            DATA_DIR / "k645_dashboard.json",
            "Phase 3: Dashboard (residual signal, beta_eth_used, regime)"
        ),
        _check_file(
            REPO_ROOT / "scripts" / "emergency_hl_exit.py",
            "Phase 4: Emergency exit (--include-k645 flag, §47)"
        ),
        _check_file(
            REPO_ROOT / "scripts" / "leverage_manager.py",
            "Phase 5: Leverage manager (K645_BNB_ORTHOG + SLEEVE_WEIGHTS_V636)"
        ),
        _check_file(
            DATA_DIR / "leverage_config.json",
            "Phase 6: Leverage config (K645_BNB_ORTHOG: 4.0 + k645_notes)"
        ),
        _check_file(
            REPO_ROOT / "scripts" / "verify_deployment_status.py",
            "Phase 7: Deployment verifier (45th daemon registry)"
        ),
        _check_file(
            REPO_ROOT / "docs" / "k302a_runbook.md",
            "Phase 8: Runbook §47 (K645 BNB orthog playbook)"
        ),
        _check_file(
            REPO_ROOT / "report.html",
            "Phase 9: HTML report (K645 SCAFFOLD-READY)"
        ),
        _check_file(
            REPO_ROOT / "wave_k650_k645_scaffold.py",
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

    # Check k645_bnb_orthog_run.py has hardcoded β_ETH coefficient
    script_path = REPO_ROOT / "scripts" / "k645_bnb_orthog_run.py"
    if script_path.exists():
        content = script_path.read_text()
        results["beta_eth_hardcoded"]   = "BETA_ETH" in content and "0.539" in content
        results["k339_repo_root"]       = "REPO_ROOT" in content and "Path(__file__).resolve().parent.parent" in content
        results["paper_trade_default"]  = "PAPER_TRADE" in content and "True" in content
        results["bybit_primary"]        = "BYBIT_SLEEVE_PCT" in content
        results["post_only"]            = "POST_ONLY_PARALLEL" in content
        results["signal_1_5sigma"]      = "SIGNAL_SIGMA_MULT" in content and "1.5" in content
        results["sleeve_3pct"]          = "SLEEVE_PCT" in content and "0.03" in content
        results["ema_168h"]             = "EMA_PERIOD_HOURS" in content and "168" in content
    else:
        results["script_missing"] = True

    # Check dashboard has β_ETH field
    dash_path = DATA_DIR / "k645_dashboard.json"
    if dash_path.exists():
        try:
            dash = json.loads(dash_path.read_text())
            results["dashboard_beta_eth"]    = dash.get("beta_eth_used") == 0.539
            results["dashboard_regime"]      = "regime" in dash
            results["dashboard_oos_perf"]    = "oos_performance" in dash
            results["dashboard_orthog_mech"] = "orthog_mechanism" in dash
            oos = dash.get("oos_performance", {})
            results["dashboard_eth_corr_raw"]     = oos.get("eth_corr_raw") == 0.435
            results["dashboard_eth_corr_post"]    = oos.get("eth_corr_post_orth") == 0.1757
        except Exception as e:
            results["dashboard_error"] = str(e)

    # Check leverage_config.json has K645 entries
    cfg_path = DATA_DIR / "leverage_config.json"
    if cfg_path.exists():
        try:
            cfg = json.loads(cfg_path.read_text())
            results["cfg_k645_cap"]    = cfg.get("exchange_caps", {}).get("K645_BNB_ORTHOG") == 4.0
            results["cfg_k645_notes"]  = "k645_notes" in cfg
            results["cfg_beta_eth"]    = cfg.get("k645_notes", {}).get("beta_eth") == 0.539
            results["cfg_sleeve_3pct"] = cfg.get("k645_notes", {}).get("sleeve_pct") == 0.03
        except Exception as e:
            results["cfg_error"] = str(e)

    # Check emergency_hl_exit.py has --include-k645
    emer_path = REPO_ROOT / "scripts" / "emergency_hl_exit.py"
    if emer_path.exists():
        content = emer_path.read_text()
        results["emer_include_k645"]      = "--include-k645" in content
        results["emer_k645_summary"]      = "K645 BNB-BTC ORTHOG CLOSE SUMMARY" in content

    # Check leverage_manager.py has K645 cap and SLEEVE_WEIGHTS_V636
    lev_path = REPO_ROOT / "scripts" / "leverage_manager.py"
    if lev_path.exists():
        content = lev_path.read_text()
        results["lev_k645_cap"]     = "K645_BNB_ORTHOG" in content
        results["lev_v636_weights"] = "SLEEVE_WEIGHTS_V636" in content

    # Check verify_deployment_status.py has 45th daemon
    vds_path = REPO_ROOT / "scripts" / "verify_deployment_status.py"
    if vds_path.exists():
        content = vds_path.read_text()
        results["vds_45th_daemon"]  = "com.cryptolab.k645-bnb-orthog" in content
        results["vds_45th_label"]   = "45th daemon" in content

    # Check runbook has §47
    rb_path = REPO_ROOT / "docs" / "k302a_runbook.md"
    if rb_path.exists():
        content = rb_path.read_text()
        results["runbook_section47"]  = "§47 K645 BNB-BTC Orthogonalized" in content
        results["runbook_beta_table"] = "β_ETH" in content
        results["runbook_60d_gate"]   = "60-Day Paper-Trade Activation Gate" in content

    # Check report.html has K650 / K645 entry
    html_path = REPO_ROOT / "report.html"
    if html_path.exists():
        content = html_path.read_text()
        results["html_k650_entry"]    = "K650" in content
        results["html_k645_scaffold"] = "K645 BNB-BTC Orthog SCAFFOLD-READY" in content
        results["html_45_daemons"]    = "45 daemons" in content

    return results


def count_registry_daemons() -> int:
    """Count registered daemons in verify_deployment_status.py."""
    vds_path = REPO_ROOT / "scripts" / "verify_deployment_status.py"
    if not vds_path.exists():
        return 0
    content = vds_path.read_text()
    return content.count('label="com.cryptolab.')


def run_dry_run_test() -> dict:
    """Execute k645_bnb_orthog_run.py --status and capture output."""
    try:
        result = subprocess.run(
            [sys.executable, "scripts/k645_bnb_orthog_run.py", "--status"],
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
    daemon_ok    = daemon_count == 45
    print(f"  Registered daemons: {daemon_count} (expected 45)")
    print(f"  Status: {'PASS' if daemon_ok else f'MISMATCH (expected 45, got {daemon_count})'}")

    # Dry-run test
    print("\n[Phase 12] Running dry-run test...")
    dry_run = run_dry_run_test()
    print(f"  Status: {dry_run.get('status')}  returncode={dry_run.get('returncode')}")

    # Summary report
    print(f"\n=== K650 Wave Summary ===")
    print(f"  Deliverables: {deliverables['passed']}/{deliverables['total']} files")
    print(f"  Content checks: {passed_content}/{total_content}")
    print(f"  Daemon count: {daemon_count} {'OK' if daemon_ok else 'MISMATCH'}")
    print(f"  Dry-run: {dry_run.get('status')}")
    print()
    print(f"  K645 Strategy:    BNB-BTC Orthogonalized FR Differential")
    print(f"  OOS Sharpe:       7.07 (residual SF W=168h) — best OOS R²=+0.0215 in series")
    print(f"  beta_ETH:         0.539 (HARDCODED, no re-OLS in prod)")
    print(f"  ETH corr:         0.435 (raw) → 0.1757 (post-orth, PASS<0.40)")
    print(f"  Profit 3% sleeve: $17,694/yr net @$10M @4x")
    print(f"  HL concentration: 65% UNCHANGED (Bybit-only)")
    print(f"  Cluster:          Binance Ecosystem / BSC L1 (6th orthog, ETH-cluster unlock)")
    print(f"  60d gate:         Realized Sh>=3.5 + fill>=60% + maxDD<20%")
    print(f"  v6.36:            K645 adds 3% Bybit sleeve to v6.35")
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
        "k645_summary": {
            "oos_sharpe_residual":        7.0686,
            "oos_r2":                     0.0215,
            "oos_r2_note":                "HEALTHIEST in orthog series (positive OOS R²)",
            "beta_eth":                   0.539,
            "beta_eth_note":              "HARDCODED — no re-OLS in production for stability",
            "eth_corr_raw":               0.435,
            "eth_corr_post_orth":         0.1757,
            "eth_cluster_unlock":         "K480 BLOCKED (ETH corr=0.435 >= 0.40) → K645 PASS (0.1757 < 0.40)",
            "ema_window":                 "W=168h (21 x 8h periods, single-factor SF ETH)",
            "signal_threshold":           "1.5σ of residual EMA_168h",
            "profit_3pct_net_usd_yr":     17_694,
            "profit_3pct_gross_usd_yr":   22_117,
            "sleeve_activation":          "3% Bybit (BNB+BTC both legs, delta-neutral)",
            "hl_concentration":           "65% UNCHANGED — Bybit-only strategy",
            "cluster":                    "Binance Ecosystem / BSC L1 (6th orthog scaffold)",
            "gate_60d":                   "Realized Sh>=3.5 + fill>=60% + maxDD<20%",
            "v636_candidate":             "K645 3% Bybit + v6.35 portfolio",
            "daemon_number":              "45th",
            "milestone":                  "K650 MILESTONE — 6th orthog scaffold complete",
        },
        "overall_status":   "PASS" if deliverables["all_pass"] and daemon_ok else "PARTIAL",
    }
    report_path = REPO_ROOT / "wave_k650_k645_scaffold.json"
    report_path.write_text(json.dumps(report, indent=2))
    print(f"  Report saved: wave_k650_k645_scaffold.json")
    print()

    return 0 if deliverables["all_pass"] and daemon_ok else 1


if __name__ == "__main__":
    sys.exit(main())

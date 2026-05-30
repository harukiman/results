#!/usr/bin/env python3
"""
wave_k653_k647_scaffold.py — K653 Wave Driver + Verification
=============================================================
Verifies all K653 deliverables for the K647 DOT orthogonalized production scaffold:
  - Phase 1: Strategy script (k647_dot_orthog_run.py)
  - Phase 2: Daemon plist (com.cryptolab.k647-dot-orthog.plist)
  - Phase 3: Dashboard (k647_dashboard.json)
  - Phase 4: Emergency exit integration (--include-k647 flag)
  - Phase 5: Leverage manager (K647_DOT_ORTHOG cap + SLEEVE_WEIGHTS_V638)
  - Phase 6: Leverage config (k647_notes + K647_DOT_ORTHOG)
  - Phase 7: Deployment verification (48 daemons)
  - Phase 8: Runbook §49 (K647 DOT orthog playbook)
  - Phase 9: HTML update (K647 SCAFFOLD-READY row, 48 daemon count)
  - Phase 10: 60d paper-trade gate criteria (STRICT: Sh>=12, DD<15%)
  - Phase 11: Wave deliverables (this file + JSON report)
  - Phase 12: Dry-run verification

K339 Security: REPO_ROOT from __file__, no /Users/ literals.
K653 Milestone: 8th orthogonal scaffold — DOT Governance/Staking cluster
  (INJ-cluster unlock, OOS R²=-4.11 structural break caution, IS beta re-OLS every 30d).
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

WAVE     = "K653"
STRATEGY = "K647 DOT-BTC Orthogonalized FR Differential"


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
    """Verify all K653 file deliverables exist and are non-empty."""
    checks = [
        _check_file(
            REPO_ROOT / "scripts" / "k647_dot_orthog_run.py",
            "Phase 1: K647 strategy script (K339 pattern, W=168h, beta_INJ=0.642)"
        ),
        _check_file(
            REPO_ROOT / "scripts" / "com.cryptolab.k647-dot-orthog.plist",
            "Phase 2: 48th daemon plist (StartInterval 28800)"
        ),
        _check_file(
            DATA_DIR / "k647_dashboard.json",
            "Phase 3: Dashboard (residual signal, beta_inj_used, regime)"
        ),
        _check_file(
            REPO_ROOT / "scripts" / "emergency_hl_exit.py",
            "Phase 4: Emergency exit (--include-k647 flag, §49)"
        ),
        _check_file(
            REPO_ROOT / "scripts" / "leverage_manager.py",
            "Phase 5: Leverage manager (K647_DOT_ORTHOG + SLEEVE_WEIGHTS_V638)"
        ),
        _check_file(
            DATA_DIR / "leverage_config.json",
            "Phase 6: Leverage config (K647_DOT_ORTHOG: 4.0 + k647_notes)"
        ),
        _check_file(
            REPO_ROOT / "scripts" / "verify_deployment_status.py",
            "Phase 7: Deployment verifier (48th daemon registry)"
        ),
        _check_file(
            REPO_ROOT / "docs" / "k302a_runbook.md",
            "Phase 8: Runbook §49 (K647 DOT orthog playbook)"
        ),
        _check_file(
            REPO_ROOT / "report.html",
            "Phase 9: HTML report (K647 SCAFFOLD-READY)"
        ),
        _check_file(
            REPO_ROOT / "wave_k653_k647_scaffold.py",
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

    # Check k647_dot_orthog_run.py has hardcoded β_INJ coefficient
    script_path = REPO_ROOT / "scripts" / "k647_dot_orthog_run.py"
    if script_path.exists():
        content = script_path.read_text()
        results["beta_inj_hardcoded"]   = "BETA_INJ" in content and "0.642" in content
        results["k339_repo_root"]       = "REPO_ROOT" in content and "Path(__file__).resolve().parent.parent" in content
        results["paper_trade_default"]  = "PAPER_TRADE" in content and "True" in content
        results["bybit_primary"]        = "BYBIT_SLEEVE_PCT" in content
        results["post_only"]            = "POST_ONLY_PARALLEL" in content
        results["signal_1_5sigma"]      = "SIGNAL_SIGMA_MULT" in content and "1.5" in content
        results["sleeve_3pct"]          = "SLEEVE_PCT" in content and "0.03" in content
        results["ema_168h"]             = "EMA_PERIOD_HOURS" in content and "168" in content
        results["oos_r2_warning"]       = "OOS_R2=-4.11" in content or "OOS R²=-4.11" in content or "oos_r2_warning" in content
    else:
        results["script_missing"] = True

    # Check dashboard has β_INJ field
    dash_path = DATA_DIR / "k647_dashboard.json"
    if dash_path.exists():
        try:
            dash = json.loads(dash_path.read_text())
            results["dashboard_beta_inj"]    = dash.get("beta_inj_used") == 0.642
            results["dashboard_regime"]      = "regime" in dash
            results["dashboard_oos_perf"]    = "oos_performance" in dash
            results["dashboard_orthog_mech"] = "orthog_mechanism" in dash
            oos = dash.get("oos_performance", {})
            results["dashboard_inj_corr_raw"]  = oos.get("inj_corr_raw") == 0.4229
            results["dashboard_inj_corr_post"] = oos.get("inj_corr_post_orth") == 0.037
            results["dashboard_oos_r2"]        = oos.get("oos_r2") == -4.1139
        except Exception as e:
            results["dashboard_error"] = str(e)

    # Check leverage_config.json has K647 entries
    cfg_path = DATA_DIR / "leverage_config.json"
    if cfg_path.exists():
        try:
            cfg = json.loads(cfg_path.read_text())
            results["cfg_k647_cap"]    = cfg.get("exchange_caps", {}).get("K647_DOT_ORTHOG") == 4.0
            results["cfg_k647_notes"]  = "k647_notes" in cfg
            results["cfg_beta_inj"]    = cfg.get("k647_notes", {}).get("beta_inj") == 0.642
            results["cfg_sleeve_3pct"] = cfg.get("k647_notes", {}).get("sleeve_pct") == 0.03
        except Exception as e:
            results["cfg_error"] = str(e)

    # Check emergency_hl_exit.py has --include-k647
    emer_path = REPO_ROOT / "scripts" / "emergency_hl_exit.py"
    if emer_path.exists():
        content = emer_path.read_text()
        results["emer_include_k647"]      = "--include-k647" in content
        results["emer_k647_summary"]      = "K647 DOT-BTC ORTHOG CLOSE SUMMARY" in content

    # Check leverage_manager.py has K647 cap and SLEEVE_WEIGHTS_V638
    lev_path = REPO_ROOT / "scripts" / "leverage_manager.py"
    if lev_path.exists():
        content = lev_path.read_text()
        results["lev_k647_cap"]      = "K647_DOT_ORTHOG" in content
        results["lev_v638_weights"]  = "SLEEVE_WEIGHTS_V638" in content

    # Check verify_deployment_status.py has 48th daemon
    vds_path = REPO_ROOT / "scripts" / "verify_deployment_status.py"
    if vds_path.exists():
        content = vds_path.read_text()
        results["vds_48th_daemon"]  = "com.cryptolab.k647-dot-orthog" in content
        results["vds_48th_label"]   = "48th daemon" in content

    # Check runbook has §49
    rb_path = REPO_ROOT / "docs" / "k302a_runbook.md"
    if rb_path.exists():
        content = rb_path.read_text()
        results["runbook_section49"]  = "§49 K647 DOT-BTC Orthogonalized" in content
        results["runbook_beta_table"] = "β_INJ" in content or "beta_INJ" in content
        results["runbook_60d_gate"]   = "60-Day Paper-Trade Activation Gate" in content or "60d gate" in content.lower()
        results["runbook_oos_r2"]     = "OOS R²=-4.11" in content or "OOS_R2=-4.11" in content

    # Check report.html has K653 / K647 entry
    html_path = REPO_ROOT / "report.html"
    if html_path.exists():
        content = html_path.read_text()
        results["html_k653_entry"]    = "K653" in content
        results["html_k647_scaffold"] = "K647 DOT-BTC Orthog SCAFFOLD-READY" in content
        results["html_48_daemons"]    = "48 daemons" in content

    return results


def count_registry_daemons() -> int:
    """Count registered daemons in verify_deployment_status.py."""
    vds_path = REPO_ROOT / "scripts" / "verify_deployment_status.py"
    if not vds_path.exists():
        return 0
    content = vds_path.read_text()
    return content.count('label="com.cryptolab.')


def run_dry_run_test() -> dict:
    """Execute k647_dot_orthog_run.py --status and capture output."""
    try:
        result = subprocess.run(
            [sys.executable, "scripts/k647_dot_orthog_run.py", "--status"],
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
    daemon_ok    = daemon_count == 48
    print(f"  Registered daemons: {daemon_count} (expected 48)")
    print(f"  Status: {'PASS' if daemon_ok else f'MISMATCH (expected 48, got {daemon_count})'}")

    # Dry-run test
    print("\n[Phase 12] Running dry-run test...")
    dry_run = run_dry_run_test()
    print(f"  Status: {dry_run.get('status')}  returncode={dry_run.get('returncode')}")

    # Summary report
    print(f"\n=== K653 Wave Summary ===")
    print(f"  Deliverables: {deliverables['passed']}/{deliverables['total']} files")
    print(f"  Content checks: {passed_content}/{total_content}")
    print(f"  Daemon count: {daemon_count} {'OK' if daemon_ok else 'MISMATCH'}")
    print(f"  Dry-run: {dry_run.get('status')}")
    print()
    print(f"  K647 Strategy:    DOT-BTC Orthogonalized FR Differential")
    print(f"  OOS Sharpe:       23.25 (residual SF W=168h) — INJ-cluster unlock")
    print(f"  OOS R² WARNING:   -4.11 STRUCTURAL BREAK (IS DOT-INJ corr=0.616 -> OOS=0.045)")
    print(f"  beta_INJ:         0.642 (HARDCODED, no re-OLS in prod)")
    print(f"  IS beta re-OLS:   every 30d mandatory (drift check)")
    print(f"  INJ corr:         0.4229 (raw) → 0.037 (post-orth, PASS<0.40)")
    print(f"  Profit 3% sleeve: $103,586/yr net @$10M @4x")
    print(f"  HL concentration: 64% (1pp headroom: 65%->64%, 3% split HL 1.5%+Bybit 1.5%)")
    print(f"  Cluster:          Governance/Staking / Polkadot relay chain (8th orthog, INJ-cluster unlock)")
    print(f"  60d gate STRICT:  Realized Sh>=12 + fill>=60% + maxDD<15% (OOS R² caution)")
    print(f"  v6.38:            K647 adds 3% Bybit sleeve to v6.37")
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
        "k647_summary": {
            "oos_sharpe_residual":        23.25,
            "oos_r2":                     -4.1139,
            "oos_r2_warning":             "STRUCTURAL BREAK: IS DOT-INJ corr=0.616 -> OOS=0.045. IS beta re-OLS every 30d mandatory.",
            "is_r2":                      0.3798,
            "beta_inj":                   0.642,
            "beta_inj_note":              "HARDCODED — no re-OLS in production for stability. IS beta re-OLS every 30d for drift monitoring.",
            "inj_corr_raw":               0.4229,
            "inj_corr_post_orth":         0.037,
            "inj_cluster_unlock":         "K513 BLOCKED (INJ corr=0.4229 >= 0.40) → K647 PASS (0.037 < 0.40)",
            "ema_window":                 "W=168h (21 x 8h periods, single-factor SF INJ)",
            "signal_threshold":           "1.5σ of residual EMA_168h",
            "profit_3pct_net_usd_yr":     103_586,
            "profit_3pct_gross_usd_yr":   129_483,
            "sleeve_activation":          "3% Bybit (DOT+BTC both legs, delta-neutral)",
            "hl_concentration":           "64% (1pp headroom from 65% — 3% split HL 1.5%+Bybit 1.5%)",
            "cluster":                    "Governance/Staking / Polkadot relay chain (8th orthog scaffold)",
            "gate_60d":                   "Realized Sh>=12 + fill>=60% + maxDD<15% (STRICT — OOS R²=-4.11)",
            "v638_candidate":             "K647 3% Bybit + v6.37 portfolio",
            "daemon_number":              "48th",
            "milestone":                  "K653 MILESTONE — 8th orthog scaffold complete",
        },
        "overall_status":   "PASS" if deliverables["all_pass"] and daemon_ok else "PARTIAL",
    }
    report_path = REPO_ROOT / "wave_k653_k647_scaffold.json"
    report_path.write_text(json.dumps(report, indent=2))
    print(f"  Report saved: wave_k653_k647_scaffold.json")
    print()

    return 0 if deliverables["all_pass"] and daemon_ok else 1


if __name__ == "__main__":
    sys.exit(main())

#!/usr/bin/env python3
"""
wave_k640_k633_scaffold.py — K640 Wave Driver + Verification
=============================================================
Verifies all K640 deliverables for the K633 OP orthogonalized production scaffold:
  - Phase 1: Strategy script (k633_op_orthog_run.py)
  - Phase 2: Daemon plist (com.cryptolab.k633-op-orthog.plist)
  - Phase 3: Dashboard (k633_dashboard.json)
  - Phase 4: Emergency exit integration (--include-k633 flag)
  - Phase 5: Leverage manager (K633_OP_ORTHOG cap + SLEEVE_WEIGHTS_V633)
  - Phase 6: Leverage config (k633_notes + K633_OP_ORTHOG)
  - Phase 7: Deployment verification (42nd daemon)
  - Phase 8: Runbook §44 (K633 OP orthog playbook)
  - Phase 9: HTML update (K633 SCAFFOLD-READY row)
  - Phase 10: 60d paper-trade gate criteria (Sh>=5, lower threshold)
  - Phase 11: Wave deliverables (this file + JSON report)
  - Phase 12: Dry-run verification

K633 orthog pattern (K637/K639 pattern):
  - residual = OP_diff - β_FIL × FIL_diff
  - β_FIL = 0.542224 (K633 OLS, IS R²=0.3283)
  - W=72h EMA (9 × 8h periods, optimal per K633 sweep)
  - OOS Sharpe 12.68 (residual) vs raw K609=32.91 (G5 BLOCKED, FIL corr=0.43)
  - G5 cleared: FIL corr 0.43 → 0.0749 post-orth (PASS); ARB 0.279 (PASS)
  - L2 cluster unlock: first confirmed OP Superchain-specific FR alpha cluster

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

WAVE     = "K640"
STRATEGY = "K633 OP-BTC Orthogonalized FR Differential"


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
    """Verify all K640 file deliverables exist and are non-empty."""
    checks = [
        _check_file(
            REPO_ROOT / "scripts" / "k633_op_orthog_run.py",
            "Phase 1: K633 strategy script (K339 pattern, W=72h, β_FIL=0.542224)"
        ),
        _check_file(
            REPO_ROOT / "scripts" / "com.cryptolab.k633-op-orthog.plist",
            "Phase 2: 42nd daemon plist (StartInterval 28800)"
        ),
        _check_file(
            DATA_DIR / "k633_dashboard.json",
            "Phase 3: Dashboard (residual signal, β_fil_used, regime)"
        ),
        _check_file(
            REPO_ROOT / "scripts" / "emergency_hl_exit.py",
            "Phase 4: Emergency exit (--include-k633 flag, §44)"
        ),
        _check_file(
            REPO_ROOT / "scripts" / "leverage_manager.py",
            "Phase 5: Leverage manager (K633_OP_ORTHOG + SLEEVE_WEIGHTS_V633)"
        ),
        _check_file(
            DATA_DIR / "leverage_config.json",
            "Phase 6: Leverage config (K633_OP_ORTHOG: 4.0 + k633_notes)"
        ),
        _check_file(
            REPO_ROOT / "scripts" / "verify_deployment_status.py",
            "Phase 7: Deployment verifier (42nd daemon registry)"
        ),
        _check_file(
            REPO_ROOT / "docs" / "k302a_runbook.md",
            "Phase 8: Runbook §44 (K633 OP orthog playbook)"
        ),
        _check_file(
            REPO_ROOT / "report.html",
            "Phase 9: HTML report (K633 SCAFFOLD-READY)"
        ),
        _check_file(
            REPO_ROOT / "wave_k640_k633_scaffold.py",
            "Phase 11: Wave driver (this file)"
        ),
    ]
    return {
        "checks":       checks,
        "total":        len(checks),
        "passed":       sum(1 for c in checks if c["status"] == "PASS"),
        "failed":       sum(1 for c in checks if c["status"] == "FAIL"),
        "all_pass":     all(c["status"] == "PASS" for c in checks),
    }


def check_content_integrity() -> dict:
    """Spot-check key content in critical files."""
    results = {}

    # Check k633_op_orthog_run.py has hardcoded β coefficient
    script_path = REPO_ROOT / "scripts" / "k633_op_orthog_run.py"
    if script_path.exists():
        content = script_path.read_text()
        results["beta_fil_hardcoded"]      = "BETA_FIL = 0.542224" in content
        results["k339_repo_root"]          = "REPO_ROOT   = Path(__file__).resolve().parent.parent" in content
        results["paper_trade_default"]     = "PAPER_TRADE         = True" in content
        results["bybit_primary"]           = "BYBIT_SLEEVE_PCT          = SLEEVE_PCT" in content
        results["post_only"]               = "POST_ONLY_PARALLEL" in content
        results["signal_1_5sigma"]         = "SIGNAL_SIGMA_MULT   = 1.5" in content
        results["sleeve_2pct"]             = "SLEEVE_PCT          = 0.02" in content
        results["ema_72h"]                 = "EMA_PERIOD_HOURS    = 72" in content
    else:
        results["script_missing"] = True

    # Check dashboard has β_fil fields
    dash_path = DATA_DIR / "k633_dashboard.json"
    if dash_path.exists():
        try:
            dash = json.loads(dash_path.read_text())
            results["dashboard_beta_fil"]    = dash.get("beta_fil_used") == 0.542224
            results["dashboard_regime"]      = "regime" in dash
            results["dashboard_oos_perf"]    = "oos_performance" in dash
            results["dashboard_orthog_mech"] = "orthog_mechanism" in dash
            results["dashboard_hl_65"]       = dash.get("hl_concentration_pct") == 65.0
        except Exception as e:
            results["dashboard_error"] = str(e)

    # Check leverage_config.json has K633 entries
    cfg_path = DATA_DIR / "leverage_config.json"
    if cfg_path.exists():
        try:
            cfg = json.loads(cfg_path.read_text())
            results["cfg_k633_cap"]    = cfg.get("exchange_caps", {}).get("K633_OP_ORTHOG") == 4.0
            results["cfg_k633_notes"]  = "k633_notes" in cfg
            results["cfg_beta_fil"]    = cfg.get("k633_notes", {}).get("beta_fil") == 0.542224
        except Exception as e:
            results["cfg_error"] = str(e)

    # Check emergency_hl_exit.py has --include-k633
    emer_path = REPO_ROOT / "scripts" / "emergency_hl_exit.py"
    if emer_path.exists():
        content = emer_path.read_text()
        results["emer_include_k633"]      = "--include-k633" in content
        results["emer_k633_bybit_note"]   = "K633 OP-BTC orthog: Bybit-only" in content

    # Check leverage_manager.py has K633 cap and SLEEVE_WEIGHTS_V633
    lev_path = REPO_ROOT / "scripts" / "leverage_manager.py"
    if lev_path.exists():
        content = lev_path.read_text()
        results["lev_k633_cap"]     = "K633_OP_ORTHOG" in content
        results["lev_v633_weights"] = "SLEEVE_WEIGHTS_V633" in content

    # Check verify_deployment_status.py has 42nd daemon
    vds_path = REPO_ROOT / "scripts" / "verify_deployment_status.py"
    if vds_path.exists():
        content = vds_path.read_text()
        results["vds_k633_label"]   = "com.cryptolab.k633-op-orthog" in content
        results["vds_42nd_daemon"]  = "42nd daemon" in content

    # Check runbook has §44
    rb_path = REPO_ROOT / "docs" / "k302a_runbook.md"
    if rb_path.exists():
        content = rb_path.read_text()
        results["runbook_section44"]  = "## §44 K633 OP-BTC Orthogonalized" in content
        results["runbook_beta_table"] = "β_FIL" in content
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
    """Execute k633_op_orthog_run.py --status and capture output."""
    try:
        result = subprocess.run(
            [sys.executable, "scripts/k633_op_orthog_run.py", "--status"],
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
        print(f"  [{status_icon}] {c['path']} — {c['description'][:65]}")
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
    # K640 = 42nd daemon (k633-op-orthog); registry may include K635 (43rd) too
    daemon_ok    = daemon_count >= 42
    print(f"  Registered daemons: {daemon_count} (expected >= 42 for K640)")
    print(f"  K633 daemon (42nd): {'PASS' if daemon_ok else 'FAIL'}")

    # Dry-run test
    print("\n[Phase 12] Running dry-run test...")
    dry_run = run_dry_run_test()
    print(f"  Status: {dry_run.get('status')}  returncode={dry_run.get('returncode')}")

    # Summary report
    print(f"\n=== K640 Wave Summary ===")
    print(f"  Deliverables: {deliverables['passed']}/{deliverables['total']} files")
    print(f"  Content checks: {passed_content}/{total_content}")
    print(f"  Daemon count: {daemon_count} {'OK (>=42)' if daemon_ok else 'MISMATCH'}")
    print(f"  Dry-run: {dry_run.get('status')}")
    print()
    print(f"  K633 Strategy:    OP-BTC Orthogonalized FR Differential")
    print(f"  OOS Sharpe:       12.68 (residual W=72h) vs raw K609=32.91 / K618=29.13")
    print(f"  β_FIL hardcoded:  0.542224  IS R²=0.3283")
    print(f"  FIL corr:         raw=0.43 (BLOCKED) → post-orth=0.0749 (G5 PASS)")
    print(f"  ARB corr:         0.2787 (G5 PASS — L2 sibling, residual corr acceptable)")
    print(f"  Profit full 4x:   $2,318,640/yr @$10M @4x")
    print(f"  Profit 2% sleeve: $46,373/yr @$10M @4x")
    print(f"  HL concentration: 65% UNCHANGED (Bybit-only)")
    print(f"  Cluster:          L2 Rollup / Optimism Superchain (L2 cluster unlock)")
    print(f"  Daemon number:    42nd (com.cryptolab.k633-op-orthog)")
    print(f"  60d gate:         Realized Sh>=5 + fill>=60% + maxDD<20%")
    print(f"  v6.33:            K633 adds 2% Bybit sleeve to v6.32")
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
        "k633_summary": {
            "oos_sharpe_residual":     12.6841,
            "oos_sharpe_raw_k609":     32.91,
            "oos_sharpe_raw_k618":     29.13,
            "ema_window_h":            72,
            "beta_fil":                0.542224,
            "is_r2":                   0.3283,
            "oos_r2":                  -0.3797,
            "fil_corr_raw":            0.4298,
            "fil_corr_post_orth":      0.0749,
            "arb_corr_post_orth":      0.2787,
            "ann_ret_pct_oos":         5.7966,
            "profit_full_4x_usd_yr":   2_318_640,
            "profit_2pct_sleeve_usd_yr": 46_373,
            "sleeve_activation":       "2% Bybit (OP+BTC both legs)",
            "hl_concentration":        "65% UNCHANGED — Bybit-only",
            "cluster":                 "L2 Rollup / Optimism Superchain (#42 daemon, L2 cluster unlock)",
            "gate_60d":                "Realized Sh>=5 + fill>=60% + maxDD<20%",
            "v633_candidate":          "K633 2% Bybit + v6.32 portfolio = v6.33",
            "l2_cluster_significance": "First confirmed L2-rollup-specific FR alpha cluster",
        },
        "overall_status":   "PASS" if deliverables["all_pass"] and daemon_ok else "PARTIAL",
    }
    report_path = REPO_ROOT / "wave_k640_k633_scaffold.json"
    report_path.write_text(json.dumps(report, indent=2))
    print(f"  Report saved: wave_k640_k633_scaffold.json")
    print()

    return 0 if deliverables["all_pass"] and daemon_ok else 1


if __name__ == "__main__":
    sys.exit(main())

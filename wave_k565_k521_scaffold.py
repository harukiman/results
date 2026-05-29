#!/usr/bin/env python3
"""
wave_k565_k521_scaffold.py — K565 Wave Driver & Test
======================================================
Drives and validates the K521 Options 25d Skew production scaffold (39th daemon).

K521 CONDITIONAL ACCEPT (6/7 gates):
  - OOS Sharpe 1.019, $494K/yr @ $10M
  - 5-axis Sh 6.386 (+0.082 lift)
  - Max corr 0.199 (G5 orthogonal confirmed — institutional axis)
  - Deribit free public API: DVOL index + 25d skew (no auth)
  - 90d paper-trade gate (G3 DSR CONDITIONAL)

K339 Security: REPO_ROOT from __file__, no /Users/ literals.
"""
from __future__ import annotations

import json
import subprocess
import sys
import time
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Dict, List

# ── K339 canonical paths ──────────────────────────────────────────────────────
REPO_ROOT = Path(__file__).resolve().parent
DATA_DIR  = REPO_ROOT / "data"
LOGS_DIR  = REPO_ROOT / "logs"
CACHE_DIR = REPO_ROOT / "cache"

JST = timezone(timedelta(hours=9))
UTC = timezone.utc

WAVE         = "K565"
STRATEGY     = "K521 Options 25d Skew"
DAEMON_N     = 39
OOS_SHARPE   = 1.019
ANN_RETURN   = 494_000
FIVE_AXIS_SH = 6.386
LIFT         = 0.082
MAX_CORR     = 0.199
GATES_PASS   = 6
GATES_TOTAL  = 7


def ts_jst() -> str:
    return datetime.now(JST).strftime("%Y-%m-%d %H:%M JST")


def check_file_exists(path: Path, label: str) -> bool:
    exists = path.exists()
    status = "OK" if exists else "MISSING"
    print(f"  [{status}] {label}: {path.relative_to(REPO_ROOT)}")
    return exists


def run_dry_run() -> Dict:
    """Run k521_options_skew_run.py --dry-run and capture result."""
    script = REPO_ROOT / "scripts" / "k521_options_skew_run.py"
    if not script.exists():
        return {"success": False, "error": "script not found"}

    print(f"\n  Running: python3 {script.relative_to(REPO_ROOT)} --dry-run")
    t0 = time.time()
    result = subprocess.run(
        [sys.executable, str(script), "--dry-run"],
        capture_output=True, text=True, timeout=60,
    )
    elapsed = time.time() - t0

    success = result.returncode == 0
    status  = "PASS" if success else "FAIL"
    print(f"  [{status}] dry-run exit={result.returncode} in {elapsed:.1f}s")

    if result.stdout:
        for line in result.stdout.splitlines()[-10:]:  # last 10 lines
            print(f"    stdout: {line}")
    if result.stderr and not success:
        for line in result.stderr.splitlines()[-5:]:
            print(f"    stderr: {line}")

    return {
        "success":     success,
        "returncode":  result.returncode,
        "elapsed_s":   round(elapsed, 2),
        "stdout_tail": result.stdout.splitlines()[-5:] if result.stdout else [],
    }


def run_verify() -> Dict:
    """Run verify_deployment_status.py and check 39 daemons, 0 mismatches."""
    script = REPO_ROOT / "scripts" / "verify_deployment_status.py"
    if not script.exists():
        return {"success": False, "error": "verify script not found"}

    print(f"\n  Running: python3 {script.relative_to(REPO_ROOT)}")
    result = subprocess.run(
        [sys.executable, str(script)],
        capture_output=True, text=True, timeout=30,
    )

    # Read output JSON
    status_json = REPO_ROOT / "deployment_status.json"
    daemon_count     = 0
    mismatch_count   = 0
    k521_status      = "UNKNOWN"
    k521_found       = False

    if status_json.exists():
        try:
            data   = json.loads(status_json.read_text())
            summ   = data.get("summary", {})
            daemon_count   = len(data.get("daemons", []))
            mismatch_count = summ.get("mismatches_with_html", 0)
            for d in data.get("daemons", []):
                if "k521" in d.get("label", "").lower():
                    k521_status = d.get("actual_status", "UNKNOWN")
                    k521_found  = True
        except Exception as e:
            print(f"  [WARN] Could not parse deployment_status.json: {e}")

    success = (daemon_count >= 39 and mismatch_count == 0 and k521_found)
    status  = "PASS" if success else "PARTIAL"

    print(f"  [{'PASS' if daemon_count >= 39 else 'FAIL'}] Daemon count: {daemon_count} (expected ≥39)")
    print(f"  [{'PASS' if mismatch_count == 0 else 'FAIL'}] Mismatches: {mismatch_count} (expected 0)")
    print(f"  [{'PASS' if k521_found else 'FAIL'}] K521 daemon found: {k521_found} status={k521_status}")

    return {
        "success":       success,
        "daemon_count":  daemon_count,
        "mismatches":    mismatch_count,
        "k521_found":    k521_found,
        "k521_status":   k521_status,
    }


def check_all_deliverables() -> Dict:
    """Verify all K565 wave deliverables exist."""
    print(f"\n{'='*60}")
    print(f"  K565 Deliverable Check — {STRATEGY} (39th daemon)")
    print(f"{'='*60}")

    checks = {
        "strategy_script":   REPO_ROOT / "scripts" / "k521_options_skew_run.py",
        "daemon_plist":      REPO_ROOT / "scripts" / "com.cryptolab.k521-options-skew.plist",
        "dashboard_json":    DATA_DIR / "k521_dashboard.json",
        "emergency_exit":    REPO_ROOT / "scripts" / "emergency_hl_exit.py",
        "leverage_manager":  REPO_ROOT / "scripts" / "leverage_manager.py",
        "leverage_config":   DATA_DIR / "leverage_config.json",
        "verify_deploy":     REPO_ROOT / "scripts" / "verify_deployment_status.py",
        "runbook":           REPO_ROOT / "docs" / "k302a_runbook.md",
        "report_html":       REPO_ROOT / "report.html",
        "wave_driver":       REPO_ROOT / "wave_k565_k521_scaffold.py",
        "wave_json":         REPO_ROOT / "wave_k565_k521_scaffold.json",
    }

    results = {}
    all_ok  = True
    for label, path in checks.items():
        ok = check_file_exists(path, label)
        results[label] = ok
        if not ok:
            all_ok = False

    # Check key content in files
    print("\n  Content checks:")

    # K521_OPTIONS_SKEW in leverage_config.json
    lev_cfg = DATA_DIR / "leverage_config.json"
    if lev_cfg.exists():
        cfg_text = lev_cfg.read_text()
        has_k521_cap = "K521_OPTIONS_SKEW" in cfg_text
        has_k521_notes = "k521_notes" in cfg_text
        print(f"  [{'OK' if has_k521_cap else 'MISS'}] leverage_config.json: K521_OPTIONS_SKEW cap")
        print(f"  [{'OK' if has_k521_notes else 'MISS'}] leverage_config.json: k521_notes section")
        results["leverage_config_k521_cap"] = has_k521_cap
        results["leverage_config_k521_notes"] = has_k521_notes
        if not (has_k521_cap and has_k521_notes):
            all_ok = False

    # SLEEVE_WEIGHTS_V630 in leverage_manager.py
    lm_py = REPO_ROOT / "scripts" / "leverage_manager.py"
    if lm_py.exists():
        lm_text = lm_py.read_text()
        has_v630 = "SLEEVE_WEIGHTS_V630" in lm_text
        has_k521_cap_lm = "K521_OPTIONS_SKEW" in lm_text
        print(f"  [{'OK' if has_v630 else 'MISS'}] leverage_manager.py: SLEEVE_WEIGHTS_V630")
        print(f"  [{'OK' if has_k521_cap_lm else 'MISS'}] leverage_manager.py: K521_OPTIONS_SKEW cap")
        results["leverage_manager_v630"] = has_v630
        results["leverage_manager_k521_cap"] = has_k521_cap_lm
        if not (has_v630 and has_k521_cap_lm):
            all_ok = False

    # --include-k521 in emergency_hl_exit.py
    emrg_py = REPO_ROOT / "scripts" / "emergency_hl_exit.py"
    if emrg_py.exists():
        emrg_text = emrg_py.read_text()
        has_include_k521 = "--include-k521" in emrg_text
        has_detect_k521  = "_detect_k521_position" in emrg_text
        has_close_k521   = "close_k521_position" in emrg_text
        print(f"  [{'OK' if has_include_k521 else 'MISS'}] emergency_hl_exit.py: --include-k521 flag")
        print(f"  [{'OK' if has_detect_k521 else 'MISS'}] emergency_hl_exit.py: _detect_k521_position()")
        print(f"  [{'OK' if has_close_k521 else 'MISS'}] emergency_hl_exit.py: close_k521_position()")
        results["emergency_exit_k521_flag"] = has_include_k521
        results["emergency_exit_detect"] = has_detect_k521
        results["emergency_exit_close"] = has_close_k521
        if not (has_include_k521 and has_detect_k521 and has_close_k521):
            all_ok = False

    # K521 in verify_deployment_status.py
    vds_py = REPO_ROOT / "scripts" / "verify_deployment_status.py"
    if vds_py.exists():
        vds_text = vds_py.read_text()
        has_k521_registry = "k521-options-skew" in vds_text
        print(f"  [{'OK' if has_k521_registry else 'MISS'}] verify_deployment_status.py: K521 registry entry")
        results["verify_k521_registry"] = has_k521_registry
        if not has_k521_registry:
            all_ok = False

    # §41 in runbook
    runbook_path = REPO_ROOT / "docs" / "k302a_runbook.md"
    if runbook_path.exists():
        rb_text = runbook_path.read_text()
        has_s41 = "§41 K521 Options 25d Skew Playbook" in rb_text
        print(f"  [{'OK' if has_s41 else 'MISS'}] k302a_runbook.md: §41 K521 Options 25d Skew Playbook")
        results["runbook_s41"] = has_s41
        if not has_s41:
            all_ok = False

    # K521 Live Monitoring row in report.html
    rpt_path = REPO_ROOT / "report.html"
    if rpt_path.exists():
        rpt_text = rpt_path.read_text()
        has_lm_k521 = "lm-k521-row" in rpt_text
        has_k565_banner = "K565 K521 OPTIONS 25d SKEW SCAFFOLD" in rpt_text
        print(f"  [{'OK' if has_lm_k521 else 'MISS'}] report.html: K521 Live Monitoring row")
        print(f"  [{'OK' if has_k565_banner else 'MISS'}] report.html: K565 scaffold banner")
        results["report_html_lm_k521"] = has_lm_k521
        results["report_html_k565_banner"] = has_k565_banner
        if not (has_lm_k521 and has_k565_banner):
            all_ok = False

    print(f"\n  Overall: {'ALL DELIVERABLES OK' if all_ok else 'SOME MISSING (see above)'}")
    return {"all_ok": all_ok, "checks": results}


def main() -> int:
    print(f"\n{'='*70}")
    print(f"  Wave {WAVE}: {STRATEGY} Production Scaffold")
    print(f"  39th daemon | OOS Sh {OOS_SHARPE} | ${ANN_RETURN:,.0f}/yr @$10M")
    print(f"  5-axis Sh {FIVE_AXIS_SH} (+{LIFT} lift) | Max corr {MAX_CORR} orthogonal")
    print(f"  {GATES_PASS}/{GATES_TOTAL} gates | 90d paper gate | v6.30 candidate")
    print(f"  {ts_jst()}")
    print(f"{'='*70}")

    # Phase 1: Deliverable checks
    print(f"\n[Phase 1] Deliverable checks...")
    deliverables = check_all_deliverables()

    # Phase 2: Dry-run
    print(f"\n[Phase 2] Dry-run verification...")
    dry_run_result = run_dry_run()

    # Phase 3: Deployment verification
    print(f"\n[Phase 3] Deployment status verification...")
    verify_result = run_verify()

    # Phase 4: Summary
    print(f"\n{'='*70}")
    print(f"  K565 WAVE SUMMARY — {ts_jst()}")
    print(f"{'='*70}")

    items = [
        ("Deliverables",     deliverables.get("all_ok", False)),
        ("Dry-run",          dry_run_result.get("success", False)),
        ("Deployment verify", verify_result.get("success", False)),
    ]

    all_pass = all(v for _, v in items)
    for label, ok in items:
        print(f"  [{'PASS' if ok else 'FAIL'}] {label}")

    print(f"\n  Strategy:      {STRATEGY}")
    print(f"  Daemon:        {DAEMON_N}th daemon")
    print(f"  OOS Sharpe:    {OOS_SHARPE}")
    print(f"  Ann Return:    ${ANN_RETURN:,.0f}/yr @$10M")
    print(f"  5-axis Sh:     {FIVE_AXIS_SH} (+{LIFT} lift)")
    print(f"  Max corr:      {MAX_CORR} (G5 orthogonal)")
    print(f"  Gates:         {GATES_PASS}/{GATES_TOTAL} (G3 DSR CONDITIONAL)")
    print(f"  Paper gate:    90d")
    print(f"  v6.30 target:  ~$1.950M/yr @$10M (v6.29 $1.456M + K521 $494K)")
    print(f"\n  Status: {'SCAFFOLD-READY' if all_pass else 'SCAFFOLD-PARTIAL (check above)'}")

    print(f"\n  90d Paper-Trade Activation Criteria:")
    print(f"    OOS Sharpe (paper) >= 0.8")
    print(f"    Fill rate >= 60%")
    print(f"    Max drawdown < 20%")
    print(f"    Trades count >= 100 in 90d")
    print(f"    After gate: activate v6.30 K521 3% live")

    # Write result JSON
    result = {
        "wave":          WAVE,
        "strategy":      STRATEGY,
        "daemon_number": DAEMON_N,
        "ts_jst":        ts_jst(),
        "oos_sharpe":    OOS_SHARPE,
        "ann_return_usd_10m": ANN_RETURN,
        "five_axis_sharpe":  FIVE_AXIS_SH,
        "five_axis_lift":    LIFT,
        "max_corr_g5":       MAX_CORR,
        "gates_passed":      GATES_PASS,
        "gates_total":       GATES_TOTAL,
        "paper_gate_days":   90,
        "v630_candidate":    True,
        "v630_combined_yr":  1_950_000,
        "deliverables_ok":   deliverables.get("all_ok", False),
        "dry_run_ok":        dry_run_result.get("success", False),
        "verify_ok":         verify_result.get("success", False),
        "daemon_count":      verify_result.get("daemon_count", 0),
        "mismatches":        verify_result.get("mismatches", -1),
        "k521_status":       verify_result.get("k521_status", "UNKNOWN"),
        "status":            "SCAFFOLD-READY" if all_pass else "SCAFFOLD-PARTIAL",
        "activation_criteria": {
            "oos_sharpe_paper_min": 0.8,
            "fill_rate_min":        0.60,
            "max_dd_max":           0.20,
            "trades_min_90d":       100,
            "days_required":        90,
        },
    }

    output_path = REPO_ROOT / "wave_k565_k521_scaffold.json"
    output_path.write_text(json.dumps(result, indent=2))
    print(f"\n  Result written: {output_path.relative_to(REPO_ROOT)}")

    return 0 if all_pass else 1


if __name__ == "__main__":
    sys.exit(main())

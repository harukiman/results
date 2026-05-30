#!/usr/bin/env python3
"""
wave_k639_k631_scaffold.py — K639 Wave Driver / Verification Script
======================================================================
Verifies all K639 K631 WLD-BTC Orthog scaffold deliverables.

K639 = K631 WLD Orthogonalized FR Differential production scaffold:
  - 41st daemon (com.cryptolab.k631-wld-orthog)
  - OOS Sh=18.04 (residual W=72h), $2.9M/yr @$10M @4x (2% sleeve)
  - Biometric ID cluster (WLD World ID + AI-bot resistance)
  - β_JUP=0.458795 HARDCODED
  - Bybit-only (WLD+BTC paired), HL concentration UNCHANGED 65%
  - 60d paper-trade gate: Realized Sh>=8 + fill>=60% + maxDD<20%
  - v6.32 candidate

K339 security: REPO_ROOT from __file__, no /Users/ literals.

Usage:
  python3 wave_k639_k631_scaffold.py
"""
from __future__ import annotations

import json
import subprocess
import sys
from datetime import datetime, timezone, timedelta
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent
DATA_DIR  = REPO_ROOT / "data"
SCRIPTS   = REPO_ROOT / "scripts"
JST = timezone(timedelta(hours=9))

CHECKS = [
    ("scripts/k631_wld_orthog_run.py",         "Phase 1: K631 strategy script (β_JUP=0.458795 hardcoded, W=72h EMA, K339)"),
    ("scripts/com.cryptolab.k631-wld-orthog.plist", "Phase 2: 41st daemon plist (StartInterval 28800)"),
    ("data/k631_dashboard.json",               "Phase 3: Dashboard (residual signal, β_JUP, regime, live data)"),
    ("scripts/emergency_hl_exit.py",           "Phase 4: Emergency exit (--include-k631 flag)"),
    ("scripts/leverage_manager.py",            "Phase 5: Leverage manager (K631_WLD_ORTHOG=4.0 + SLEEVE_WEIGHTS_V632)"),
    ("data/leverage_config.json",              "Phase 6: Leverage config (K631_WLD_ORTHOG: 4.0 + k631_notes)"),
    ("scripts/verify_deployment_status.py",    "Phase 7: Deployment verifier (41st daemon registry)"),
    ("docs/k302a_runbook.md",                  "Phase 8: Runbook §43 (K631 WLD orthog playbook)"),
    ("report.html",                            "Phase 9: HTML report (K639 SCAFFOLD-READY + 41st daemon)"),
    ("wave_k639_k631_scaffold.py",             "Phase 11: Wave driver (this file)"),
]

CONTENT_CHECKS = [
    ("scripts/k631_wld_orthog_run.py",  "BETA_JUP = 0.458795",        "beta_jup_hardcoded"),
    ("scripts/k631_wld_orthog_run.py",  "REPO_ROOT   = Path(__file__)", "k339_repo_root"),
    ("scripts/k631_wld_orthog_run.py",  "PAPER_TRADE         = True",   "paper_trade_default"),
    ("scripts/k631_wld_orthog_run.py",  "BYBIT_SLEEVE_PCT",             "bybit_primary"),
    ("scripts/k631_wld_orthog_run.py",  "POST_ONLY_PARALLEL",           "post_only"),
    ("scripts/k631_wld_orthog_run.py",  "SIGNAL_SIGMA_MULT   = 1.5",    "signal_1_5sigma"),
    ("scripts/k631_wld_orthog_run.py",  "EMA_PERIOD_HOURS    = 72",     "ema_72h_window"),
    ("scripts/k631_wld_orthog_run.py",  "SLEEVE_PCT          = 0.02",   "sleeve_2pct"),
    ("data/k631_dashboard.json",        "beta_jup_used",                "dashboard_beta_jup"),
    ("data/k631_dashboard.json",        "regime",                       "dashboard_regime"),
    ("data/k631_dashboard.json",        "oos_performance",              "dashboard_oos_perf"),
    ("data/k631_dashboard.json",        "orthog_mechanism",             "dashboard_orthog_mech"),
    ("data/k631_dashboard.json",        "65.0",                         "dashboard_hl_65"),
    ("data/leverage_config.json",       "K631_WLD_ORTHOG",              "cfg_k631_cap"),
    ("data/leverage_config.json",       "k631_notes",                   "cfg_k631_notes"),
    ("data/leverage_config.json",       "0.458795",                     "cfg_beta_jup"),
    ("scripts/emergency_hl_exit.py",    "--include-k631",               "emer_include_k631"),
    ("scripts/leverage_manager.py",     "K631_WLD_ORTHOG",              "lev_k631_cap"),
    ("scripts/leverage_manager.py",     "SLEEVE_WEIGHTS_V632",          "lev_v632_weights"),
    ("scripts/verify_deployment_status.py", "k631-wld-orthog",          "vds_41st_daemon"),
    ("scripts/verify_deployment_status.py", "41st daemon",              "vds_41st_label"),
    ("docs/k302a_runbook.md",           "§43",                          "runbook_section43"),
    ("docs/k302a_runbook.md",           "0.458795",                     "runbook_beta_table"),
    ("docs/k302a_runbook.md",           "60-Day Paper-Trade",           "runbook_60d_gate"),
]


def main() -> int:
    ts_jst = datetime.now(JST).strftime("%Y-%m-%d %H:%M JST")
    print(f"\n=== K639 K631 WLD Orthog Scaffold Verification — {ts_jst} ===")
    print(f"  Strategy: K631 WLD-BTC Orthogonalized FR Differential")
    print(f"  Daemon:   41st (com.cryptolab.k631-wld-orthog)")
    print(f"  OOS Sh:   18.04 (residual W=72h)")
    print(f"  Profit:   $2,900,000/yr @$10M @4x (2% sleeve)")
    print(f"  Cluster:  Biometric ID / World ID")
    print(f"  β_JUP:    0.458795 (HARDCODED)")
    print(f"  Venue:    Bybit-only (HL 65% UNCHANGED)")
    print(f"  Gate:     60d paper-trade: Sh>=8 + fill>=60% + maxDD<20%")

    # Phase 1: File existence checks
    print(f"\n--- File Checks ---")
    file_results = []
    for rel_path, desc in CHECKS:
        p = REPO_ROOT / rel_path
        exists = p.is_file()
        size   = p.stat().st_size if exists else 0
        status = "PASS" if exists else "FAIL"
        file_results.append({"path": rel_path, "exists": exists, "size_bytes": size, "status": status})
        icon = "✓" if exists else "✗"
        print(f"  {icon} {rel_path} ({size:,} bytes) — {status}")

    passed_files = sum(1 for r in file_results if r["status"] == "PASS")
    print(f"\n  Files: {passed_files}/{len(CHECKS)} PASS")

    # Phase 2: Content checks
    print(f"\n--- Content Checks ---")
    content_results = {}
    for rel_path, needle, key in CONTENT_CHECKS:
        p = REPO_ROOT / rel_path
        if p.is_file():
            found = needle in p.read_text()
        else:
            found = False
        content_results[key] = found
        icon = "✓" if found else "✗"
        print(f"  {icon} {key}: {'PASS' if found else 'FAIL'} ({needle[:50]})")

    passed_content = sum(1 for v in content_results.values() if v)
    print(f"\n  Content: {passed_content}/{len(CONTENT_CHECKS)} PASS")

    # Phase 3: Daemon count
    print(f"\n--- Daemon Count ---")
    vds_path = REPO_ROOT / "scripts" / "verify_deployment_status.py"
    daemon_count = 0
    if vds_path.is_file():
        text = vds_path.read_text()
        daemon_count = text.count("DaemonSpec(")
    daemon_ok = daemon_count == 41
    print(f"  Daemon count: {daemon_count} ({'PASS — 41 daemons' if daemon_ok else 'FAIL — expected 41'})")

    # Phase 4: Dry-run
    print(f"\n--- Dry-Run ---")
    try:
        result = subprocess.run(
            ["python3", "scripts/k631_wld_orthog_run.py", "--dry-run"],
            capture_output=True, text=True, timeout=30, cwd=str(REPO_ROOT)
        )
        dry_ok = result.returncode == 0
        print(f"  Dry-run: {'PASS' if dry_ok else 'FAIL'} (returncode={result.returncode})")
        if not dry_ok:
            print(f"  stderr: {result.stderr[:200]}")
    except Exception as e:
        dry_ok = False
        print(f"  Dry-run: FAIL ({e})")

    # Summary
    all_pass = (passed_files == len(CHECKS) and
                passed_content == len(CONTENT_CHECKS) and
                daemon_ok and dry_ok)

    print(f"\n=== K639 Summary ===")
    print(f"  Files:     {passed_files}/{len(CHECKS)}")
    print(f"  Content:   {passed_content}/{len(CONTENT_CHECKS)}")
    print(f"  Daemons:   {daemon_count} (target: 41)")
    print(f"  Dry-run:   {'PASS' if dry_ok else 'FAIL'}")
    print(f"  Overall:   {'ALL PASS' if all_pass else 'SOME FAILURES'}")
    print(f"\n  K631 WLD orthog: SCAFFOLD-READY (41st daemon)")
    print(f"  v6.32 candidate: K631 2% Bybit + v6.31 portfolio")
    print(f"  Next: 60d paper-trade gate (Sh>=8 + fill>=60% + maxDD<20%)")
    print()

    return 0 if all_pass else 1


if __name__ == "__main__":
    sys.exit(main())

#!/usr/bin/env python3
"""
wave_k790_k789_scaffold.py — K790 K789 RESOLV-SOL Alt-Alt Scaffold
=================================================================
Wave K790: Production scaffold for K789 RESOLV-SOL FR Differential (CONDITIONAL ACCEPT 7/9).
81st daemon, 24th alt-alt scaffold (23rd alt-alt pair evaluated), 22nd vertex candidate RESOLV.

Scaffold tasks:
  Phase 1:  Verify scripts/k789_resolv_sol_run.py exists and is runnable
  Phase 2:  Verify scripts/com.cryptolab.k789-resolv-sol.plist (81st daemon, 8h/28800s)
  Phase 3:  Add K789 entry to data/leverage_config.json
  Phase 4:  Add K789 DaemonSpec to scripts/verify_deployment_status.py
  Phase 5:  Add --include-k789 flag to scripts/emergency_hl_exit.py
  Phase 6:  Add §82 section to docs/k302a_runbook.md
  Phase 7:  Initialize data/k789_dashboard.json
  Phase 8:  Validate all scaffold files exist
  Phase 9:  Update report.html (K790 K789 RESOLV-SOL scaffold entry)
  Phase 10: Generate wave_k790_k789_scaffold.json

K789 CONDITIONAL ACCEPT parameters:
  OOS Sharpe:      23.91 (W=84h, zero threshold, 141d OOS — G9 FAIL < 180d; re-gate ~Aug 2026)
  IS Sharpe:       26.05 (W=84h) — IS>OOS typical (OOS conservative)
  G4 Walk-Forward: 8/8 ALL POSITIVE (min_fold_sh=27.72 — all folds strong)
  G5 25/25:        ALL PASS (max_corr=0.1269 G5k AVAX-SOL, below 0.40)
  G6:              1,228 entries/yr OOS PASS (W=84h vs 30/yr threshold)
  G7:              OOS ann ret 4x=273.3% PASS
  G8:              FAIL — RESOLV HL-only HIP-3 (no cross-venue perp confirmed)
  G9:              FAIL — OOS=141d < 180d. Re-gate ~Aug 18 2026 (39 more days).
  L004:            PASS — RESOLV bidirectional (carry_full=0.5867 carry_oos=0.6955)
  L004_DIFF:       BORDERLINE PASS full=0.3159 (IS=0.1597 WARN; OOS=0.5502 governs). Monthly recheck.
  Sleeve:          0.4% (@$10M = $40K margin, $160K notional at 4x)
  K523 central:    $41,539/yr @$10M @4x @0.4%
  Vertex:          RESOLV = 22nd vertex candidate (2nd RWA/synth-dollar cluster after ENA)
  HL cap:          66.8% AT CAP -> paper-gate strict
  G8 gate:         Cross-venue RESOLV perp verify required before live
  G9 gate:         Re-gate ~Aug 18 2026 (OOS reaches 180d; re-run K789 eval)
  60d gate:        Sh >= 15, fill >= 60%, maxDD < 15% + K498/v6.52 + G9 re-gate + G8 resolve

K339 security: REPO_ROOT from __file__, no /Users/ literals.
"""
from __future__ import annotations

import json
import subprocess
import sys
from datetime import datetime, timezone, timedelta
from pathlib import Path

# ── K339 canonical paths ──────────────────────────────────────────────────────
REPO_ROOT   = Path(__file__).resolve().parent
DATA_DIR    = REPO_ROOT / "data"
DOCS_DIR    = REPO_ROOT / "docs"
SCRIPTS_DIR = REPO_ROOT / "scripts"

JST = timezone(timedelta(hours=9))
UTC = timezone.utc

WAVE         = "K790"
STRATEGY     = "K789"
PAIR         = "RESOLV-SOL"
DAEMON_NUM   = "81st"
ALT_ALT_N    = "twenty-fourth"   # scaffold count (evaluated)
ALT_ALT_PAIR = "twenty-third"    # actual pair number in family
VERTEX_N     = "22nd"
CLUSTER      = "RWA Synthetic Dollar × Solana SVM"
OOS_SHARPE   = 23.91
IS_SHARPE    = 26.05
SLEEVE_PCT   = 0.004
LEVERAGE     = 4.0
CENTRAL_YR   = 41539
K523_CONS    = 26481
K523_OPT     = 109312
HL_CAP_PCT   = 66.8


def ts_jst() -> str:
    return datetime.now(JST).strftime("%Y-%m-%d %H:%M JST")


def check(condition: bool, msg: str) -> bool:
    tag = "PASS" if condition else "FAIL"
    print(f"  [{tag}] {msg}")
    return condition


# ─────────────────────────────────────────────────────────────────────────────
# Phase 1 — Verify run script
# ─────────────────────────────────────────────────────────────────────────────

def phase1_run_script() -> bool:
    path = SCRIPTS_DIR / "k789_resolv_sol_run.py"
    exists = path.exists()
    check(exists, "scripts/k789_resolv_sol_run.py exists")
    if not exists:
        return False

    result = subprocess.run(
        [sys.executable, "-c", f"import ast; ast.parse(open('{path}').read())"],
        capture_output=True, text=True
    )
    syntax_ok = result.returncode == 0
    check(syntax_ok, "scripts/k789_resolv_sol_run.py syntax OK")
    return syntax_ok


# ─────────────────────────────────────────────────────────────────────────────
# Phase 2 — Verify plist
# ─────────────────────────────────────────────────────────────────────────────

def phase2_plist() -> bool:
    path = SCRIPTS_DIR / "com.cryptolab.k789-resolv-sol.plist"
    exists = path.exists()
    check(exists, "scripts/com.cryptolab.k789-resolv-sol.plist exists")
    if not exists:
        return False

    content = path.read_text()
    interval_ok = "<integer>28800</integer>" in content
    label_ok    = "com.cryptolab.k789-resolv-sol" in content
    paper_ok    = "<string>True</string>" in content
    check(interval_ok, "plist StartInterval=28800 (8h)")
    check(label_ok,    "plist Label=com.cryptolab.k789-resolv-sol")
    check(paper_ok,    "plist PAPER_TRADE=True default")
    return interval_ok and label_ok and paper_ok


# ─────────────────────────────────────────────────────────────────────────────
# Phase 3 — leverage_config.json
# ─────────────────────────────────────────────────────────────────────────────

def phase3_leverage_config() -> bool:
    path = DATA_DIR / "leverage_config.json"
    if not path.exists():
        check(False, "data/leverage_config.json exists")
        return False

    config = json.loads(path.read_text())
    k789_key = "K789_RESOLV_SOL"

    if k789_key in config:
        check(True, f"data/leverage_config.json: {k789_key} entry already present")
    else:
        check(False, f"data/leverage_config.json: {k789_key} entry MISSING")
        return False
    return True


# ─────────────────────────────────────────────────────────────────────────────
# Phase 4 — verify_deployment_status.py
# ─────────────────────────────────────────────────────────────────────────────

def phase4_verify_deployment() -> bool:
    path = SCRIPTS_DIR / "verify_deployment_status.py"
    if not path.exists():
        check(False, "scripts/verify_deployment_status.py exists")
        return False

    content = path.read_text()
    present = "k789-resolv-sol" in content
    check(present, "verify_deployment_status.py: K789 DaemonSpec present")
    return present


# ─────────────────────────────────────────────────────────────────────────────
# Phase 5 — emergency_hl_exit.py
# ─────────────────────────────────────────────────────────────────────────────

def phase5_emergency_exit() -> bool:
    path = SCRIPTS_DIR / "emergency_hl_exit.py"
    if not path.exists():
        check(False, "scripts/emergency_hl_exit.py exists")
        return False

    content = path.read_text()
    present = "include-k789" in content
    check(present, "emergency_hl_exit.py: --include-k789 flag present")
    return present


# ─────────────────────────────────────────────────────────────────────────────
# Phase 6 — k302a_runbook.md §82
# ─────────────────────────────────────────────────────────────────────────────

def phase6_runbook() -> bool:
    path = DOCS_DIR / "k302a_runbook.md"
    if not path.exists():
        check(False, "docs/k302a_runbook.md exists")
        return False

    content = path.read_text()
    present = "§82" in content and "K789 RESOLV-SOL" in content
    check(present, "docs/k302a_runbook.md: §82 K789 RESOLV-SOL present")
    return present


# ─────────────────────────────────────────────────────────────────────────────
# Phase 7 — data/k789_dashboard.json
# ─────────────────────────────────────────────────────────────────────────────

def phase7_dashboard() -> bool:
    path = DATA_DIR / "k789_dashboard.json"
    exists = path.exists()
    check(exists, "data/k789_dashboard.json exists")
    if not exists:
        return False

    try:
        dash = json.loads(path.read_text())
        wave_ok  = dash.get("wave") == "K790"
        strat_ok = "K789" in dash.get("strategy", "")
        check(wave_ok,  "data/k789_dashboard.json: wave=K790")
        check(strat_ok, "data/k789_dashboard.json: strategy contains K789")
        return wave_ok and strat_ok
    except Exception as e:
        check(False, f"data/k789_dashboard.json: JSON parse error: {e}")
        return False


# ─────────────────────────────────────────────────────────────────────────────
# Phase 8 — Full validation
# ─────────────────────────────────────────────────────────────────────────────

def phase8_validate() -> dict:
    results = {
        "run_script":         phase1_run_script(),
        "plist":              phase2_plist(),
        "leverage_config":    phase3_leverage_config(),
        "verify_deployment":  phase4_verify_deployment(),
        "emergency_exit":     phase5_emergency_exit(),
        "runbook_s82":        phase6_runbook(),
        "dashboard":          phase7_dashboard(),
    }
    all_pass = all(results.values())
    passed   = sum(results.values())
    total    = len(results)
    print(f"\n  Scaffold validation: {passed}/{total} PASS  (all_pass={all_pass})")
    return results


# ─────────────────────────────────────────────────────────────────────────────
# Phase 9 — Update report.html
# ─────────────────────────────────────────────────────────────────────────────

def phase9_report_html(checks: dict) -> bool:
    path = REPO_ROOT / "report.html"
    if not path.exists():
        check(False, "report.html exists")
        return False

    content = path.read_text()
    if "K790" in content and "K789" in content and "RESOLV-SOL" in content:
        check(True, "report.html: K790 K789 RESOLV-SOL entry already present")
        return True

    check(False, "report.html: K790 K789 RESOLV-SOL entry MISSING -- add manually")
    return False


# ─────────────────────────────────────────────────────────────────────────────
# Phase 10 — Generate wave_k790_k789_scaffold.json
# ─────────────────────────────────────────────────────────────────────────────

def phase10_json(checks: dict) -> dict:
    out_path = REPO_ROOT / "wave_k790_k789_scaffold.json"
    if out_path.exists():
        try:
            result = json.loads(out_path.read_text())
            check(True, "wave_k790_k789_scaffold.json exists and valid JSON")
            return result
        except Exception as e:
            check(False, f"wave_k790_k789_scaffold.json: JSON parse error: {e}")

    # Fallback: write minimal result
    all_pass = all(checks.values())
    result = {
        "wave": WAVE,
        "strategy": f"K789 RESOLV-SOL FR Differential Alt-Alt (RWA Synthetic Dollar × Solana SVM — 22nd vertex candidate RESOLV)",
        "run_time_jst": ts_jst(),
        "scaffold_verification": {
            "all_pass": all_pass,
            "gates_passed": sum(checks.values()),
            "gates_total": len(checks),
            "checks": checks,
            "ts_jst": ts_jst(),
        },
    }
    out_path.write_text(json.dumps(result, indent=2))
    return result


# ─────────────────────────────────────────────────────────────────────────────
# Main
# ─────────────────────────────────────────────────────────────────────────────

def main() -> int:
    print("=" * 70)
    print(f"K790 K789 RESOLV-SOL Scaffold Verification — {ts_jst()}")
    print(f"  Strategy: K789 RESOLV-SOL FR Differential")
    print(f"  Daemon:   {DAEMON_NUM} ({ALT_ALT_N} alt-alt scaffold)")
    print(f"  Verdict:  CONDITIONAL ACCEPT 7/9 (G8 FAIL + G9 FAIL OOS=141d re-gate Aug 2026)")
    print(f"  OOS Sh:   {OOS_SHARPE} | IS Sh: {IS_SHARPE} | W=84h")
    print(f"  Central:  ${CENTRAL_YR:,}/yr @$10M @{LEVERAGE}x @{SLEEVE_PCT:.1%}")
    print(f"  HL cap:   {HL_CAP_PCT}% AT CAP — paper-gate strict")
    print(f"  G9:       Re-gate ~Aug 18 2026 (OOS reaches 180d)")
    print("=" * 70)

    checks = phase8_validate()

    print("\n--- Phase 9: report.html ---")
    phase9_report_html(checks)

    print("\n--- Phase 10: JSON output ---")
    result = phase10_json(checks)

    print("\n" + "=" * 70)
    all_pass = all(checks.values())
    print(f"K790 Scaffold Complete: {'ALL PASS' if all_pass else 'PARTIAL'}")
    print(f"  Daemon:  com.cryptolab.k789-resolv-sol (81st)")
    print(f"  Script:  scripts/k789_resolv_sol_run.py")
    print(f"  Gate:    Sh>=15 fill>=60% maxDD<15% + K498/v6.52 + G9 Aug 2026 + cross-venue")
    print(f"  MR9:     RESOLV = 22nd vertex candidate. All RESOLV-X pairs blocked if confirmed.")
    print("=" * 70)
    return 0 if all_pass else 1


if __name__ == "__main__":
    sys.exit(main())

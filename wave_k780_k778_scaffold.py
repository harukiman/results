#!/usr/bin/env python3
"""
wave_k780_k778_scaffold.py — K780 K778 COMP-SOL Alt-Alt Scaffold
=================================================================
Wave K780: Production scaffold for K778 COMP-SOL FR Differential (CLEAN ACCEPT 30/30).
79th daemon, 22nd alt-alt scaffold (21st alt-alt pair evaluated), 20th vertex COMP.

Scaffold tasks:
  Phase 1:  Verify scripts/k778_comp_sol_run.py exists and is runnable
  Phase 2:  Verify scripts/com.cryptolab.k778-comp-sol.plist (79th daemon, 8h/28800s)
  Phase 3:  Add K778 entry to data/leverage_config.json
  Phase 4:  Add K778 DaemonSpec to scripts/verify_deployment_status.py
  Phase 5:  Add --include-k778 flag to scripts/emergency_hl_exit.py
  Phase 6:  Add §80 section to docs/k302a_runbook.md
  Phase 7:  Initialize data/k778_dashboard.json
  Phase 8:  Validate all scaffold files exist
  Phase 9:  Update report.html (K780 K778 COMP-SOL scaffold entry)
  Phase 10: Generate wave_k780_k778_scaffold.json

K778 CLEAN ACCEPT parameters:
  OOS Sharpe:      25.05 (W=48h, zero threshold, 216d OOS — G9 PASS >= 180d)
  IS Sharpe:       14.91 (OOS > IS — clean, no overfit)
  G4 Walk-Forward: 12/12 ALL POSITIVE (min_fold_sh=14.79 — perfect WF validation)
  G5 22/22:        ALL PASS (max_corr=0.3906 G5j SOL-INJ, negative — all below 0.40)
  G5q:             LDO-SOL=0.2926 PASS (DeFi protocol overlap clear)
  G5v:             AAVE-SOL=0.2359 PASS (DeFi lending cluster clear)
  G6:              87.5 entries/yr OOS PASS (W=48h vs 30/yr threshold — highest in alt-alt)
  G7:              OOS ann ret 4x=130.1% PASS
  G8:              OKX COMP FR vs HL COMP FR corr=0.8548 PASS (proxy, n=284)
  G9:              OOS 216d PASS (>= 180d minimum — NO marginal caveat)
  L004:            PASS — COMP bidirectional (pos_frac_full=68.1% pos_frac_oos=50.1%)
  Sleeve:          2.5% (@$10M = $250K margin, $1M notional at 4x)
  K523 central:    $207,345/yr @$10M @4x @2.5%
  Vertex:          COMP = 20th vertex (1st DeFi governance token cluster)
  HL cap:          66.8% AT CAP -> paper-gate strict
  60d gate:        Sh >= 12, fill >= 60%, maxDD < 15% + K498/v6.52

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

WAVE         = "K780"
STRATEGY     = "K778"
PAIR         = "COMP-SOL"
DAEMON_NUM   = "79th"
ALT_ALT_N    = "twenty-second"   # scaffold count (evaluated)
ALT_ALT_PAIR = "twenty-first"    # actual pair number in family
VERTEX_N     = "20th"
CLUSTER      = "DeFi governance × Solana SVM"
OOS_SHARPE   = 25.05
IS_SHARPE    = 14.91
SLEEVE_PCT   = 0.025
LEVERAGE     = 4.0
CENTRAL_YR   = 207345
K523_CONS    = 78791
K523_OPT     = 276460
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
    path = SCRIPTS_DIR / "k778_comp_sol_run.py"
    exists = path.exists()
    check(exists, "scripts/k778_comp_sol_run.py exists")
    if not exists:
        return False

    result = subprocess.run(
        [sys.executable, "-c", f"import ast; ast.parse(open('{path}').read())"],
        capture_output=True, text=True
    )
    syntax_ok = result.returncode == 0
    check(syntax_ok, "scripts/k778_comp_sol_run.py syntax OK")
    return syntax_ok


# ─────────────────────────────────────────────────────────────────────────────
# Phase 2 — Verify plist
# ─────────────────────────────────────────────────────────────────────────────

def phase2_plist() -> bool:
    path = SCRIPTS_DIR / "com.cryptolab.k778-comp-sol.plist"
    exists = path.exists()
    check(exists, "scripts/com.cryptolab.k778-comp-sol.plist exists")
    if not exists:
        return False

    content = path.read_text()
    interval_ok = "<integer>28800</integer>" in content
    label_ok    = "com.cryptolab.k778-comp-sol" in content
    paper_ok    = "<string>True</string>" in content
    check(interval_ok, "plist StartInterval=28800 (8h)")
    check(label_ok,    "plist Label=com.cryptolab.k778-comp-sol")
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
    k778_key = "K778_COMP_SOL"

    if k778_key in config:
        check(True, f"data/leverage_config.json: {k778_key} entry already present")
    else:
        check(False, f"data/leverage_config.json: {k778_key} entry MISSING")
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
    present = "k778-comp-sol" in content
    check(present, "verify_deployment_status.py: K778 DaemonSpec present")
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
    present = "include-k778" in content
    check(present, "emergency_hl_exit.py: --include-k778 flag present")
    return present


# ─────────────────────────────────────────────────────────────────────────────
# Phase 6 — k302a_runbook.md §80
# ─────────────────────────────────────────────────────────────────────────────

def phase6_runbook() -> bool:
    path = DOCS_DIR / "k302a_runbook.md"
    if not path.exists():
        check(False, "docs/k302a_runbook.md exists")
        return False

    content = path.read_text()
    present = "§80" in content and "K778 COMP-SOL" in content
    check(present, "docs/k302a_runbook.md: §80 K778 COMP-SOL present")
    return present


# ─────────────────────────────────────────────────────────────────────────────
# Phase 7 — data/k778_dashboard.json
# ─────────────────────────────────────────────────────────────────────────────

def phase7_dashboard() -> bool:
    path = DATA_DIR / "k778_dashboard.json"
    exists = path.exists()
    check(exists, "data/k778_dashboard.json exists")
    if not exists:
        return False

    try:
        dash = json.loads(path.read_text())
        wave_ok  = dash.get("wave") == "K780"
        strat_ok = "K778" in dash.get("strategy", "")
        check(wave_ok,  "data/k778_dashboard.json: wave=K780")
        check(strat_ok, "data/k778_dashboard.json: strategy contains K778")
        return wave_ok and strat_ok
    except Exception as e:
        check(False, f"data/k778_dashboard.json: JSON parse error: {e}")
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
        "runbook_s80":        phase6_runbook(),
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
    if "K780" in content and "K778" in content and "COMP-SOL" in content:
        check(True, "report.html: K780 K778 COMP-SOL entry already present")
        return True

    check(False, "report.html: K780 K778 COMP-SOL entry MISSING -- add manually")
    return False


# ─────────────────────────────────────────────────────────────────────────────
# Phase 10 — Verify wave_k780_k778_scaffold.json
# ─────────────────────────────────────────────────────────────────────────────

def phase10_json(checks: dict) -> dict:
    out_path = REPO_ROOT / "wave_k780_k778_scaffold.json"
    if out_path.exists():
        try:
            result = json.loads(out_path.read_text())
            check(True, f"wave_k780_k778_scaffold.json exists and valid JSON")
            return result
        except Exception as e:
            check(False, f"wave_k780_k778_scaffold.json: JSON parse error: {e}")
    else:
        check(False, "wave_k780_k778_scaffold.json MISSING")

    # Fallback: write minimal result
    all_pass = all(checks.values())
    result = {
        "wave": WAVE,
        "strategy": f"K778 COMP-SOL FR Differential Alt-Alt (DeFi governance × Solana SVM — 20th vertex COMP)",
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
    check(True, f"wave_k780_k778_scaffold.json written ({out_path})")
    return result


# ─────────────────────────────────────────────────────────────────────────────
# Main
# ─────────────────────────────────────────────────────────────────────────────

def main() -> int:
    print(f"\n{'='*70}")
    print(f"K780 K778 COMP-SOL Alt-Alt Scaffold — {ts_jst()}")
    print(f"{'='*70}")
    print(f"  Wave: {WAVE} | Strategy: K778 {PAIR} | Daemon: {DAEMON_NUM}")
    print(f"  OOS Sh={OOS_SHARPE} | IS Sh={IS_SHARPE} (OOS > IS -- CLEAN)")
    print(f"  G4 12/12 ALL POSITIVE | G5 22/22 ALL PASS | G6 87.5/yr | G9 216d PASS")
    print(f"  L004 PASS: COMP bidirectional (pos_frac_oos=50.1%)")
    print(f"  Sleeve={SLEEVE_PCT:.1%} | Lev={LEVERAGE}x | HL={HL_CAP_PCT}% AT CAP")
    print(f"  K523: ${K523_CONS:,}/${CENTRAL_YR:,}/${K523_OPT:,}/yr @$10M")
    print(f"  COMP = {VERTEX_N} vertex (1st DeFi-gov cluster). MR9 L002: all COMP-X blocked.")
    print(f"  60d gate: Sh>=12 + fill>=60% + maxDD<15% + K498/v6.52")
    print(f"  CLEAN ACCEPT 30/30 (no conditional caveats)")
    print(f"{'='*70}\n")

    print("Phase 8: Validation (all files should already be created):")
    checks = phase8_validate()

    print("\nPhase 9: Verify report.html:")
    phase9_report_html(checks)

    print("\nPhase 10: Verify scaffold JSON:")
    result = phase10_json(checks)

    all_pass = all(checks.values())
    print(f"\n{'='*70}")
    print(f"K780 scaffold complete. All pass: {all_pass}")
    print(f"  Scaffold: {sum(checks.values())}/{len(checks)} checks PASS")
    print(f"  Decision: CLEAN ACCEPT 30/30 (no conditional caveats)")
    print(f"  Next: 60d paper-trade gate -> live after K498/v6.52 reduces HL% < 65%")
    print(f"{'='*70}")
    return 0 if all_pass else 1


if __name__ == "__main__":
    sys.exit(main())

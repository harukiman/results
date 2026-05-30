#!/usr/bin/env python3
"""
wave_k787_k786_scaffold.py — K787 K786 BIO-SOL Alt-Alt Scaffold
=================================================================
Wave K787: Production scaffold for K786 BIO-SOL FR Differential (ACCEPT 8/9).
80th daemon, 23rd alt-alt scaffold (22nd alt-alt pair evaluated), 21st vertex BIO.

Scaffold tasks:
  Phase 1:  Verify scripts/k786_bio_sol_run.py exists and is runnable
  Phase 2:  Verify scripts/com.cryptolab.k786-bio-sol.plist (80th daemon, 8h/28800s)
  Phase 3:  Add K786 entry to data/leverage_config.json
  Phase 4:  Add K786 DaemonSpec to scripts/verify_deployment_status.py
  Phase 5:  Add --include-k786 flag to scripts/emergency_hl_exit.py
  Phase 6:  Add §81 section to docs/k302a_runbook.md
  Phase 7:  Initialize data/k786_dashboard.json
  Phase 8:  Validate all scaffold files exist
  Phase 9:  Update report.html (K787 K786 BIO-SOL scaffold entry)
  Phase 10: Generate wave_k787_k786_scaffold.json

K786 ACCEPT parameters:
  OOS Sharpe:      23.10 (W=84h, zero threshold, 205d OOS — G9 PASS >= 180d)
  IS Sharpe:       23.24 (W=84h) — IS~OOS (consistent, no directional overfit)
  G4 Walk-Forward: 5/5 ALL POSITIVE (min_fold_sh=20.95 — all folds strong)
  G5 24/24:        ALL PASS (max_corr=0.3308 G5u FIL-SOL, below 0.40)
  G6:              7,479 entries/yr OOS PASS (W=84h vs 30/yr threshold — ultra-high)
  G7:              OOS ann ret 4x=558.4% PASS
  G8:              FAIL — BIO HL-only HIP-3 (no cross-venue perp confirmed)
  G9:              OOS 204.8d PASS (>= 180d minimum)
  L004:            PASS — BIO bidirectional (pos_frac_full=0.5590 pos_frac_oos=0.5983)
  L004_DIFF:       BORDERLINE full=0.303 (OOS=0.461 PASS). Monthly recheck.
  Sleeve:          0.4% (@$10M = $40K margin, $160K notional at 4x)
  K523 central:    $63,652/yr @$10M @4x @0.4%
  Vertex:          BIO = 21st vertex (1st DeSci cluster)
  HL cap:          66.8% AT CAP -> paper-gate strict
  G8 gate:         Cross-venue Bybit BIO verify required before live
  60d gate:        Sh >= 15, fill >= 60%, maxDD < 15% + K498/v6.52 + G8 resolve

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

WAVE         = "K787"
STRATEGY     = "K786"
PAIR         = "BIO-SOL"
DAEMON_NUM   = "80th"
ALT_ALT_N    = "twenty-third"    # scaffold count (evaluated)
ALT_ALT_PAIR = "twenty-second"   # actual pair number in family
VERTEX_N     = "21st"
CLUSTER      = "DeSci Biotech-DAO × Solana SVM"
OOS_SHARPE   = 23.10
IS_SHARPE    = 23.24
SLEEVE_PCT   = 0.004
LEVERAGE     = 4.0
CENTRAL_YR   = 63652
K523_CONS    = 54105
K523_OPT     = 167506
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
    path = SCRIPTS_DIR / "k786_bio_sol_run.py"
    exists = path.exists()
    check(exists, "scripts/k786_bio_sol_run.py exists")
    if not exists:
        return False

    result = subprocess.run(
        [sys.executable, "-c", f"import ast; ast.parse(open('{path}').read())"],
        capture_output=True, text=True
    )
    syntax_ok = result.returncode == 0
    check(syntax_ok, "scripts/k786_bio_sol_run.py syntax OK")
    return syntax_ok


# ─────────────────────────────────────────────────────────────────────────────
# Phase 2 — Verify plist
# ─────────────────────────────────────────────────────────────────────────────

def phase2_plist() -> bool:
    path = SCRIPTS_DIR / "com.cryptolab.k786-bio-sol.plist"
    exists = path.exists()
    check(exists, "scripts/com.cryptolab.k786-bio-sol.plist exists")
    if not exists:
        return False

    content = path.read_text()
    interval_ok = "<integer>28800</integer>" in content
    label_ok    = "com.cryptolab.k786-bio-sol" in content
    paper_ok    = "<string>True</string>" in content
    check(interval_ok, "plist StartInterval=28800 (8h)")
    check(label_ok,    "plist Label=com.cryptolab.k786-bio-sol")
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
    k786_key = "K786_BIO_SOL"

    if k786_key in config:
        check(True, f"data/leverage_config.json: {k786_key} entry already present")
    else:
        check(False, f"data/leverage_config.json: {k786_key} entry MISSING")
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
    present = "k786-bio-sol" in content
    check(present, "verify_deployment_status.py: K786 DaemonSpec present")
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
    present = "include-k786" in content
    check(present, "emergency_hl_exit.py: --include-k786 flag present")
    return present


# ─────────────────────────────────────────────────────────────────────────────
# Phase 6 — k302a_runbook.md §81
# ─────────────────────────────────────────────────────────────────────────────

def phase6_runbook() -> bool:
    path = DOCS_DIR / "k302a_runbook.md"
    if not path.exists():
        check(False, "docs/k302a_runbook.md exists")
        return False

    content = path.read_text()
    present = "§81" in content and "K786 BIO-SOL" in content
    check(present, "docs/k302a_runbook.md: §81 K786 BIO-SOL present")
    return present


# ─────────────────────────────────────────────────────────────────────────────
# Phase 7 — data/k786_dashboard.json
# ─────────────────────────────────────────────────────────────────────────────

def phase7_dashboard() -> bool:
    path = DATA_DIR / "k786_dashboard.json"
    exists = path.exists()
    check(exists, "data/k786_dashboard.json exists")
    if not exists:
        return False

    try:
        dash = json.loads(path.read_text())
        wave_ok  = dash.get("wave") == "K787"
        strat_ok = "K786" in dash.get("strategy", "")
        check(wave_ok,  "data/k786_dashboard.json: wave=K787")
        check(strat_ok, "data/k786_dashboard.json: strategy contains K786")
        return wave_ok and strat_ok
    except Exception as e:
        check(False, f"data/k786_dashboard.json: JSON parse error: {e}")
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
        "runbook_s81":        phase6_runbook(),
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
    if "K787" in content and "K786" in content and "BIO-SOL" in content:
        check(True, "report.html: K787 K786 BIO-SOL entry already present")
        return True

    check(False, "report.html: K787 K786 BIO-SOL entry MISSING -- add manually")
    return False


# ─────────────────────────────────────────────────────────────────────────────
# Phase 10 — Verify wave_k787_k786_scaffold.json
# ─────────────────────────────────────────────────────────────────────────────

def phase10_json(checks: dict) -> dict:
    out_path = REPO_ROOT / "wave_k787_k786_scaffold.json"
    if out_path.exists():
        try:
            result = json.loads(out_path.read_text())
            check(True, f"wave_k787_k786_scaffold.json exists and valid JSON")
            return result
        except Exception as e:
            check(False, f"wave_k787_k786_scaffold.json: JSON parse error: {e}")

    # Fallback: write minimal result
    all_pass = all(checks.values())
    result = {
        "wave": WAVE,
        "strategy": f"K786 BIO-SOL FR Differential Alt-Alt (DeSci Biotech-DAO × Solana SVM — 21st vertex BIO)",
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
    check(True, f"wave_k787_k786_scaffold.json written ({out_path})")
    return result


# ─────────────────────────────────────────────────────────────────────────────
# Main
# ─────────────────────────────────────────────────────────────────────────────

def main() -> int:
    print(f"\n{'='*70}")
    print(f"K787 K786 BIO-SOL Alt-Alt Scaffold — {ts_jst()}")
    print(f"{'='*70}")
    print(f"  Wave: {WAVE} | Strategy: K786 {PAIR} | Daemon: {DAEMON_NUM}")
    print(f"  OOS Sh={OOS_SHARPE} | IS Sh={IS_SHARPE} (IS~OOS -- consistent, no directional overfit)")
    print(f"  G4 5/5 ALL POSITIVE (min_sh=20.95) | G5 24/24 ALL PASS | G6 7,479/yr | G9 204.8d PASS")
    print(f"  G8 FAIL: BIO HL-only HIP-3 (no cross-venue perp confirmed)")
    print(f"  L004 PASS: BIO bidirectional (pos_frac_oos=0.5983)")
    print(f"  L004_DIFF BORDERLINE: full=0.303, OOS=0.461 PASS. Monthly recheck required.")
    print(f"  Sleeve={SLEEVE_PCT:.1%} | Lev={LEVERAGE}x | HL={HL_CAP_PCT}% AT CAP")
    print(f"  K523: ${K523_CONS:,}/${CENTRAL_YR:,}/${K523_OPT:,}/yr @$10M")
    print(f"  BIO = {VERTEX_N} vertex (1st DeSci cluster). MR9 L002: all BIO-X blocked.")
    print(f"  60d gate: Sh>=15 + fill>=60% + maxDD<15% + K498/v6.52 + cross-venue Bybit verify")
    print(f"  ACCEPT 8/9 (G8 FAIL HL-only HIP-3 — cross-venue verify required)")
    print(f"{'='*70}\n")

    print("Phase 8: Validation (all files should already be created):")
    checks = phase8_validate()

    print("\nPhase 9: Verify report.html:")
    phase9_report_html(checks)

    print("\nPhase 10: Verify scaffold JSON:")
    result = phase10_json(checks)

    all_pass = all(checks.values())
    print(f"\n{'='*70}")
    print(f"K787 scaffold complete. All pass: {all_pass}")
    print(f"  Scaffold: {sum(checks.values())}/{len(checks)} checks PASS")
    print(f"  Decision: ACCEPT 8/9 (G8 FAIL HL-only HIP-3)")
    print(f"  Next: 60d paper-trade gate -> live after K498/v6.52 + G8 resolve (Bybit BIO verify)")
    print(f"{'='*70}")
    return 0 if all_pass else 1


if __name__ == "__main__":
    sys.exit(main())

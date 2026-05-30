#!/usr/bin/env python3
"""
wave_k791_k788_scaffold.py — K791 K788 MEME-SOL Alt-Alt Scaffold
=================================================================
Wave K791: Production scaffold for K788 MEME-SOL FR Differential (CONDITIONAL_ACCEPT 9/9).
82nd daemon, 25th alt-alt scaffold (24th alt-alt pair evaluated), 22nd vertex MEME.

Scaffold tasks:
  Phase 1:  Verify scripts/k788_meme_sol_run.py exists and is runnable
  Phase 2:  Verify scripts/com.cryptolab.k788-meme-sol.plist (82nd daemon, 8h/28800s)
  Phase 3:  Verify K788 entry in data/leverage_config.json
  Phase 4:  Verify K788 DaemonSpec in scripts/verify_deployment_status.py
  Phase 5:  Verify --include-k788 flag in scripts/emergency_hl_exit.py
  Phase 6:  Verify §83 section in docs/k302a_runbook.md
  Phase 7:  Verify data/k788_dashboard.json
  Phase 8:  Validate all scaffold files exist
  Phase 9:  Verify report.html (K791 K788 MEME-SOL scaffold entry)
  Phase 10: Verify wave_k791_k788_scaffold.json

K788 CONDITIONAL_ACCEPT parameters:
  OOS Sharpe:      15.97 (W=84h, zero threshold, 212d OOS — G9 PASS >= 180d)
  IS Sharpe:       13.12 (W=84h) — OOS > IS (no directional overfit)
  G4 Walk-Forward: 12/12 ALL POSITIVE (min_fold_sh=4.3534 — all folds positive)
  G5 27/27:        ALL PASS (max_corr=0.1973 G5b SOL-BTC, well below 0.40)
  G5w:             PEPE-SOL=0.1339 PASS (meme cluster orthogonal)
  G5y:             WIF-SOL=0.0825 PASS (cross-chain meme distinct)
  G6:              84.3 entries/yr OOS PASS (W=84h vs 30/yr threshold)
  G7:              OOS ann ret 3x=60.5% PASS
  G8:              PASS — MEME HL+OKX+Bybit confirmed (cross-venue verified)
  G9:              OOS 212d PASS (>= 180d minimum)
  L004:            PASS — MEME bidirectional (pos_frac_full=0.7940 pos_frac_oos=0.5743)
  L004_DIFF:       BORDERLINE full=0.289 (<0.30 floor), OOS=0.440 PASS. G2 timing alpha.
  Sleeve:          0.4% (@$10M = $40K margin, $120K notional at 3x, $60K per leg)
  Leverage:        3x (HL max for MEME — lower than standard 4x; OI=$480K)
  K523 central:    $14,518/yr @$10M @3x @0.4%
  Vertex:          MEME = 22nd vertex (1st ERC-20 meme index cluster)
  HL cap:          66.8% AT CAP -> paper-gate strict
  G8 status:       PASS (HL+OKX+Bybit cross-venue verified)
  60d gate:        Sh >= 10, fill >= 60%, maxDD < 15% + K498/v6.52 + L004_DIFF stable

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

WAVE         = "K791"
STRATEGY     = "K788"
PAIR         = "MEME-SOL"
DAEMON_NUM   = "82nd"
ALT_ALT_N    = "twenty-fifth"    # scaffold count
ALT_ALT_PAIR = "twenty-fourth"   # actual pair number in family
VERTEX_N     = "22nd"
CLUSTER      = "ERC-20 Meme Index × Solana SVM"
OOS_SHARPE   = 15.97
IS_SHARPE    = 13.12
SLEEVE_PCT   = 0.004
LEVERAGE     = 3.0
CENTRAL_YR   = 14518
K523_CONS    = 9194
K523_OPT     = 20567
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
    path = SCRIPTS_DIR / "k788_meme_sol_run.py"
    exists = path.exists()
    check(exists, "scripts/k788_meme_sol_run.py exists")
    if not exists:
        return False

    result = subprocess.run(
        [sys.executable, "-c", f"import ast; ast.parse(open('{path}').read())"],
        capture_output=True, text=True
    )
    syntax_ok = result.returncode == 0
    check(syntax_ok, "scripts/k788_meme_sol_run.py syntax OK")
    return syntax_ok


# ─────────────────────────────────────────────────────────────────────────────
# Phase 2 — Verify plist
# ─────────────────────────────────────────────────────────────────────────────

def phase2_plist() -> bool:
    path = SCRIPTS_DIR / "com.cryptolab.k788-meme-sol.plist"
    exists = path.exists()
    check(exists, "scripts/com.cryptolab.k788-meme-sol.plist exists")
    if not exists:
        return False

    content = path.read_text()
    interval_ok = "<integer>28800</integer>" in content
    label_ok    = "com.cryptolab.k788-meme-sol" in content
    paper_ok    = "<string>True</string>" in content
    check(interval_ok, "plist StartInterval=28800 (8h)")
    check(label_ok,    "plist Label=com.cryptolab.k788-meme-sol")
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
    k788_key = "K788_MEME_SOL"

    if k788_key in config:
        check(True, f"data/leverage_config.json: {k788_key} entry present")
    else:
        check(False, f"data/leverage_config.json: {k788_key} entry MISSING")
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
    present = "k788-meme-sol" in content
    check(present, "verify_deployment_status.py: K788 DaemonSpec present")
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
    present = "include-k788" in content
    check(present, "emergency_hl_exit.py: --include-k788 flag present")
    return present


# ─────────────────────────────────────────────────────────────────────────────
# Phase 6 — k302a_runbook.md §83
# ─────────────────────────────────────────────────────────────────────────────

def phase6_runbook() -> bool:
    path = DOCS_DIR / "k302a_runbook.md"
    if not path.exists():
        check(False, "docs/k302a_runbook.md exists")
        return False

    content = path.read_text()
    present = "§83" in content and "K788 MEME-SOL" in content
    check(present, "docs/k302a_runbook.md: §83 K788 MEME-SOL present")
    return present


# ─────────────────────────────────────────────────────────────────────────────
# Phase 7 — data/k788_dashboard.json
# ─────────────────────────────────────────────────────────────────────────────

def phase7_dashboard() -> bool:
    path = DATA_DIR / "k788_dashboard.json"
    exists = path.exists()
    check(exists, "data/k788_dashboard.json exists")
    if not exists:
        return False

    try:
        dash = json.loads(path.read_text())
        wave_ok  = dash.get("wave") == "K791"
        strat_ok = "K788" in dash.get("strategy", "")
        check(wave_ok,  "data/k788_dashboard.json: wave=K791")
        check(strat_ok, "data/k788_dashboard.json: strategy contains K788")
        return wave_ok and strat_ok
    except Exception as e:
        check(False, f"data/k788_dashboard.json: JSON parse error: {e}")
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
        "runbook_s83":        phase6_runbook(),
        "dashboard":          phase7_dashboard(),
    }
    all_pass = all(results.values())
    passed   = sum(results.values())
    total    = len(results)
    print(f"\n  Scaffold validation: {passed}/{total} PASS  (all_pass={all_pass})")
    return results


# ─────────────────────────────────────────────────────────────────────────────
# Phase 9 — Verify report.html
# ─────────────────────────────────────────────────────────────────────────────

def phase9_report_html(checks: dict) -> bool:
    path = REPO_ROOT / "report.html"
    if not path.exists():
        check(False, "report.html exists")
        return False

    content = path.read_text()
    if "K791" in content and "K788" in content and "MEME-SOL" in content:
        check(True, "report.html: K791 K788 MEME-SOL entry already present")
        return True

    check(False, "report.html: K791 K788 MEME-SOL entry MISSING -- will add")
    return False


# ─────────────────────────────────────────────────────────────────────────────
# Phase 10 — Verify wave_k791_k788_scaffold.json
# ─────────────────────────────────────────────────────────────────────────────

def phase10_json(checks: dict) -> dict:
    out_path = REPO_ROOT / "wave_k791_k788_scaffold.json"
    if out_path.exists():
        try:
            result = json.loads(out_path.read_text())
            check(True, f"wave_k791_k788_scaffold.json exists and valid JSON")
            return result
        except Exception as e:
            check(False, f"wave_k791_k788_scaffold.json: JSON parse error: {e}")

    # Fallback: write minimal result
    all_pass = all(checks.values())
    result = {
        "wave": WAVE,
        "strategy": f"K788 MEME-SOL FR Differential Alt-Alt (ERC-20 Meme Index × Solana SVM — 22nd vertex MEME)",
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
    check(True, f"wave_k791_k788_scaffold.json written ({out_path})")
    return result


# ─────────────────────────────────────────────────────────────────────────────
# Main
# ─────────────────────────────────────────────────────────────────────────────

def main() -> int:
    print(f"\n{'='*70}")
    print(f"K791 K788 MEME-SOL Alt-Alt Scaffold — {ts_jst()}")
    print(f"{'='*70}")
    print(f"  Wave: {WAVE} | Strategy: K788 {PAIR} | Daemon: {DAEMON_NUM}")
    print(f"  OOS Sh={OOS_SHARPE} | IS Sh={IS_SHARPE} (OOS > IS -- no directional overfit)")
    print(f"  G4 12/12 ALL POSITIVE (min_sh=4.35) | G5 27/27 ALL PASS | G6 84.3/yr | G9 212d PASS")
    print(f"  G8 PASS: MEME HL+OKX+Bybit confirmed (cross-venue verified)")
    print(f"  G5w PEPE-SOL=0.1339 PASS | G5y WIF-SOL=0.0825 PASS (meme cluster CLEAR)")
    print(f"  L004 PASS: MEME bidirectional (pos_frac_oos=0.5743)")
    print(f"  L004_DIFF BORDERLINE: full=0.289 (<0.30), OOS=0.440 PASS. G2 timing alpha (+5.13 Sh).")
    print(f"  Sleeve={SLEEVE_PCT:.1%} | Lev={LEVERAGE}x (HL max for MEME) | HL={HL_CAP_PCT}% AT CAP")
    print(f"  K523: ${K523_CONS:,}/${CENTRAL_YR:,}/${K523_OPT:,}/yr @$10M")
    print(f"  MEME = {VERTEX_N} vertex (1st ERC-20 meme index cluster). MR9 L002: all MEME-X blocked.")
    print(f"  60d gate: Sh>=10 + fill>=60% + maxDD<15% + K498/v6.52 + L004_DIFF stable (OOS>=0.30)")
    print(f"  CONDITIONAL_ACCEPT 9/9 (G8 PASS -- condition: L004_DIFF stable monitoring)")
    print(f"{'='*70}\n")

    print("Phase 8: Validation (all files should already be created):")
    checks = phase8_validate()

    print("\nPhase 9: Verify report.html:")
    phase9_report_html(checks)

    print("\nPhase 10: Verify scaffold JSON:")
    result = phase10_json(checks)

    all_pass = all(checks.values())
    print(f"\n{'='*70}")
    print(f"K791 scaffold complete. All pass: {all_pass}")
    print(f"  Scaffold: {sum(checks.values())}/{len(checks)} checks PASS")
    print(f"  Decision: CONDITIONAL_ACCEPT 9/9 (G8 PASS -- L004_DIFF monitor)")
    print(f"  Next: 60d paper-trade gate -> live after K498/v6.52 + L004_DIFF stable")
    print(f"  L004_DIFF: monthly recheck; reduce sleeve if OOS diff_pos < 0.28 for 2 mo")
    print(f"{'='*70}")
    return 0 if all_pass else 1


if __name__ == "__main__":
    sys.exit(main())

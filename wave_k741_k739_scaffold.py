#!/usr/bin/env python3
"""
wave_k741_k739_scaffold.py — K741 K739 FIL-SOL Alt-Alt Scaffold Verification
==============================================================================
Verifies K739 FIL-SOL scaffold readiness: script importability, plist structure,
dashboard initialization, and dry-run cycle.

K339 security: REPO_ROOT from __file__, no /Users/ literals.
"""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

# ── K339 canonical paths ──────────────────────────────────────────────────────
REPO_ROOT = Path(__file__).resolve().parent
SCRIPTS   = REPO_ROOT / "scripts"
DATA      = REPO_ROOT / "data"


def check_file(path: Path, label: str) -> bool:
    exists = path.exists()
    status = "OK" if exists else "MISSING"
    print(f"  [{status}] {label}: {path.relative_to(REPO_ROOT)}")
    return exists


def run_dry_run() -> bool:
    """Run k739_fil_sol_run.py --dry-run and check exit code."""
    script = SCRIPTS / "k739_fil_sol_run.py"
    result = subprocess.run(
        [sys.executable, str(script), "--dry-run"],
        capture_output=True, text=True, timeout=30
    )
    print(f"\n  --- k739_fil_sol_run.py --dry-run stdout (first 20 lines) ---")
    for line in result.stdout.splitlines()[:20]:
        print(f"    {line}")
    if result.returncode != 0:
        print(f"  [FAIL] exit code={result.returncode}")
        print(f"  stderr: {result.stderr[:500]}")
        return False
    print(f"  [OK] exit code=0")
    return True


def check_dashboard() -> bool:
    """Verify k739_dashboard.json was written and has required keys."""
    dash_path = DATA / "k739_dashboard.json"
    if not dash_path.exists():
        print(f"  [MISSING] k739_dashboard.json not found")
        return False
    try:
        dash = json.loads(dash_path.read_text())
    except Exception as e:
        print(f"  [FAIL] dashboard parse error: {e}")
        return False

    required_keys = [
        "last_poll_jst", "regime", "mean_168h", "position_state",
        "sleeve_pct", "leverage", "hl_concentration_pct",
        "wave", "strategy", "gate_metrics", "oos_performance",
    ]
    missing = [k for k in required_keys if k not in dash]
    if missing:
        print(f"  [FAIL] dashboard missing keys: {missing}")
        return False

    sleeve = dash.get("sleeve_pct", 0)
    hl_conc = dash.get("hl_concentration_pct", 0)
    wave    = dash.get("wave", "")
    print(f"  [OK] dashboard: wave={wave} sleeve={sleeve:.1%} hl_conc={hl_conc:.1f}% "
          f"regime={dash.get('regime')} position={dash.get('position_state')}")
    return True


def check_plist() -> bool:
    """Verify plist has required keys."""
    plist_path = SCRIPTS / "com.cryptolab.k739-fil-sol.plist"
    if not plist_path.exists():
        print(f"  [MISSING] com.cryptolab.k739-fil-sol.plist")
        return False
    content = plist_path.read_text()
    checks = [
        ("com.cryptolab.k739-fil-sol", "label"),
        ("k739_fil_sol_run.py", "script ref"),
        ("28800", "8h interval (28800s)"),
        ("PAPER_TRADE", "paper trade env"),
        ("True", "paper trade=True"),
        ("logs/k739_fil_sol.log", "stdout log"),
    ]
    all_ok = True
    for needle, label in checks:
        ok = needle in content
        status = "OK" if ok else "MISSING"
        print(f"    [{status}] plist {label}: '{needle}'")
        if not ok:
            all_ok = False
    return all_ok


def main() -> int:
    print("\n=== K741 K739 FIL-SOL Scaffold Verification ===")
    print(f"  REPO_ROOT: {REPO_ROOT}")
    print(f"  Wave:      K741 (68th daemon, 14th alt-alt, Storage L1 × SVM)")
    print(f"  Strategy:  K739 FIL-SOL FR Differential")
    print(f"  Sleeve:    1.5% (HL-cap-aware: 64% + 1.5% = 65.0%)")
    print(f"  OOS Sh:    23.378 (W=168h, zero threshold)")
    print(f"  Profit:    ~$122K/yr @$10M @4x @1.5% sleeve")
    print(f"  Gates:     17/18 PASS (G6 below threshold 26.9/yr vs 30)")

    print("\n[Phase 1] File existence checks")
    files_ok = all([
        check_file(SCRIPTS / "k739_fil_sol_run.py",           "run script"),
        check_file(SCRIPTS / "com.cryptolab.k739-fil-sol.plist", "plist"),
        check_file(REPO_ROOT / "wave_k741_k739_scaffold.json", "scaffold JSON"),
        check_file(REPO_ROOT / "wave_k739_fil_sol_eval.json",  "eval JSON"),
    ])

    print("\n[Phase 2] Plist structure check")
    plist_ok = check_plist()

    print("\n[Phase 3] Dry-run cycle")
    run_ok = run_dry_run()

    print("\n[Phase 4] Dashboard verification")
    dash_ok = check_dashboard()

    print("\n=== Scaffold Verification Summary ===")
    results = {
        "files_ok":  files_ok,
        "plist_ok":  plist_ok,
        "run_ok":    run_ok,
        "dash_ok":   dash_ok,
    }
    all_pass = all(results.values())
    for k, v in results.items():
        print(f"  {'PASS' if v else 'FAIL'} {k}")

    print(f"\n  Overall: {'ALL PASS — scaffold ready for paper-trade' if all_pass else 'SOME CHECKS FAILED'}")
    print(f"\n  Deploy instructions:")
    print(f"    cp scripts/com.cryptolab.k739-fil-sol.plist ~/Library/LaunchAgents/")
    print(f"    # Edit REPO_ROOT_PLACEHOLDER in copied plist to actual path")
    print(f"    launchctl load ~/Library/LaunchAgents/com.cryptolab.k739-fil-sol.plist")
    print(f"    launchctl list | grep k739")
    print(f"\n  60d gate: Realized Sh>=10 + fill>=60% + maxDD<15%")
    print(f"  Expand: 2.5% sleeve ($81K/yr eval) after K517 cap resolution")
    print()

    return 0 if all_pass else 1


if __name__ == "__main__":
    sys.exit(main())

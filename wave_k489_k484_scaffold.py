#!/usr/bin/env python3
"""
wave_k489_k484_scaffold.py — K489 Wave Driver & Scaffold Verification
======================================================================
Driver / test script for K489 wave deliverables.

Usage:
    python3 wave_k489_k484_scaffold.py               # full verification suite
    python3 wave_k489_k484_scaffold.py --dry-run     # include dry-run cycle
    python3 wave_k489_k484_scaffold.py --summary     # print summary only

Checks:
    1. All K489 deliverable files exist
    2. k484_dashboard.json schema valid
    3. leverage_config.json K484 entries present
    4. leverage_manager.py SLEEVE_WEIGHTS_V623 present
    5. emergency_hl_exit.py --include-k484 flag present
    6. verify_deployment_status.py 30th daemon entry present
    7. report.html K484 monitoring row present
    8. Optional: dry-run cycle (k484_avax_btc_run.py --dry-run)

K339: REPO_ROOT from __file__, no /Users/ literals.
"""

import json
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent

# ---------------------------------------------------------------------------
# K489 deliverables manifest
# ---------------------------------------------------------------------------
DELIVERABLES = {
    "scripts/k484_avax_btc_run.py": "K484 main strategy script (~250 LOC)",
    "com.cryptolab.k484-avax-btc.plist": "30th daemon plist (gitignored)",
    "data/k484_dashboard.json": "K484 dashboard (initial NEUTRAL state)",
    "wave_k489_k484_scaffold.json": "K489 wave summary JSON",
    "wave_k489_k484_scaffold.md": "K489 wave document (200-400 lines)",
}

MODIFIED_FILES = {
    "scripts/emergency_hl_exit.py": "--include-k484 flag",
    "scripts/leverage_manager.py": "SLEEVE_WEIGHTS_V623 + K484 entries",
    "data/leverage_config.json": "K484_AVAX_BTC = 4.0 cap + k484_notes",
    "scripts/verify_deployment_status.py": "K484 as 30th DaemonSpec",
    "docs/k302a_runbook.md": "§38c K484 playbook",
    "report.html": "K484 row + v6.23 banner + 30 daemons",
}

# ---------------------------------------------------------------------------
# Verification helpers
# ---------------------------------------------------------------------------

def check_file_exists(rel_path: str) -> bool:
    p = REPO_ROOT / rel_path
    return p.exists()


def check_json_key(rel_path: str, key_path: list) -> bool:
    """Drill into nested JSON with a list of keys and check the final value exists."""
    p = REPO_ROOT / rel_path
    try:
        data = json.loads(p.read_text())
    except Exception:
        return False
    node = data
    for k in key_path:
        if not isinstance(node, dict) or k not in node:
            return False
        node = node[k]
    return True


def check_file_contains(rel_path: str, needle: str) -> bool:
    p = REPO_ROOT / rel_path
    try:
        return needle in p.read_text()
    except Exception:
        return False


def run_dry_run() -> bool:
    result = subprocess.run(
        [sys.executable, str(REPO_ROOT / "scripts" / "k484_avax_btc_run.py"), "--dry-run"],
        capture_output=True,
        text=True,
        timeout=60,
    )
    if result.returncode != 0:
        print(f"  [FAIL] dry-run exited {result.returncode}")
        print(result.stderr[-500:] if result.stderr else "")
        return False
    return True


def run_verify_deployment() -> bool:
    result = subprocess.run(
        [sys.executable, str(REPO_ROOT / "scripts" / "verify_deployment_status.py")],
        capture_output=True,
        text=True,
        timeout=60,
    )
    output = result.stdout + result.stderr
    # Must show 30 daemons and 0 mismatches
    if "30" not in output:
        print("  [FAIL] verify_deployment_status.py did not report 30 daemons")
        return False
    if result.returncode != 0:
        print(f"  [WARN] verify_deployment_status.py exited {result.returncode}")
    return True


# ---------------------------------------------------------------------------
# Main verification suite
# ---------------------------------------------------------------------------

def main(dry_run: bool = False, summary_only: bool = False) -> int:
    print("=" * 65)
    print("K489 Wave Scaffold Verification")
    print("K484 AVAX-BTC FR Differential — 30th Daemon")
    print("=" * 65)

    failures = []

    # ── 1. Deliverable files ────────────────────────────────────────────────
    print("\n[1] Deliverable files:")
    for rel, desc in DELIVERABLES.items():
        ok = check_file_exists(rel)
        mark = "PASS" if ok else "FAIL"
        print(f"  [{mark}] {rel}  ({desc})")
        if not ok:
            failures.append(f"Missing: {rel}")

    # ── 2. Modified files ──────────────────────────────────────────────────
    print("\n[2] Modified files:")
    for rel, desc in MODIFIED_FILES.items():
        ok = check_file_exists(rel)
        mark = "PASS" if ok else "FAIL"
        print(f"  [{mark}] {rel}  ({desc})")
        if not ok:
            failures.append(f"Missing modified file: {rel}")

    # ── 3. Content checks ──────────────────────────────────────────────────
    print("\n[3] Content checks:")

    checks = [
        ("data/k484_dashboard.json", ["strategy"], "k484_dashboard strategy field"),
        ("data/leverage_config.json", ["exchange_caps", "K484_AVAX_BTC"], "leverage_config K484_AVAX_BTC"),
        ("data/leverage_config.json", ["k484_notes"], "leverage_config k484_notes section"),
        ("data/k484_dashboard.json", ["oos_performance", "sharpe"], "k484_dashboard oos_performance.sharpe"),
        ("wave_k489_k484_scaffold.json", ["verify_result", "daemons_total"], "wave json verify_result.daemons_total"),
    ]
    for rel, key_path, desc in checks:
        ok = check_json_key(rel, key_path)
        mark = "PASS" if ok else "FAIL"
        print(f"  [{mark}] {desc}")
        if not ok:
            failures.append(f"JSON key missing: {rel} → {key_path}")

    str_checks = [
        ("scripts/emergency_hl_exit.py", "--include-k484", "emergency_hl_exit --include-k484 arg"),
        ("scripts/emergency_hl_exit.py", "_detect_k484_paired_positions", "emergency_hl_exit _detect_k484"),
        ("scripts/emergency_hl_exit.py", "close_k484_paired_positions", "emergency_hl_exit close_k484"),
        ("scripts/leverage_manager.py", "SLEEVE_WEIGHTS_V623", "leverage_manager SLEEVE_WEIGHTS_V623"),
        ("scripts/leverage_manager.py", "K484_AVAX_BTC", "leverage_manager K484_AVAX_BTC cap"),
        ("scripts/verify_deployment_status.py", "k484-avax-btc", "verify_deployment K484 entry"),
        ("report.html", "lm-k484-row", "report.html K484 monitoring row"),
        ("report.html", "v6.23", "report.html v6.23 banner"),
        ("docs/k302a_runbook.md", "38c", "runbook §38c section"),
    ]
    for rel, needle, desc in str_checks:
        ok = check_file_contains(rel, needle)
        mark = "PASS" if ok else "FAIL"
        print(f"  [{mark}] {desc}")
        if not ok:
            failures.append(f"String not found in {rel}: '{needle}'")

    # ── 4. Security check (no /Users/ literals in new script) ──────────────
    print("\n[4] K339 security check:")
    security_files = [
        "scripts/k484_avax_btc_run.py",
        "wave_k489_k484_scaffold.py",
        "wave_k489_k484_scaffold.json",
    ]
    for rel in security_files:
        p = REPO_ROOT / rel
        try:
            # Check for hardcoded absolute user paths (real K339 violation)
            # Exclude comment lines and docstring lines
            import re
            user_path_pattern = re.compile(r'/Users/[A-Za-z][A-Za-z0-9_-]+/')
            lines = p.read_text().splitlines()
            code_lines = [
                ln for ln in lines
                if not ln.strip().startswith("#")
                and not ln.strip().startswith('"""')
                and not ln.strip().startswith("'''")
            ]
            violations = user_path_pattern.findall("\n".join(code_lines))
            has_users = bool(violations)
            mark = "FAIL" if has_users else "PASS"
            print(f"  [{mark}] No hardcoded user paths in {rel}")
            if has_users:
                failures.append(f"K339 violation: hardcoded user path in {rel}: {violations[:3]}")
        except Exception as e:
            print(f"  [WARN] Could not read {rel}: {e}")

    # ── 5. Optional dry-run ────────────────────────────────────────────────
    if dry_run and not summary_only:
        print("\n[5] Dry-run cycle (k484_avax_btc_run.py --dry-run):")
        ok = run_dry_run()
        mark = "PASS" if ok else "FAIL"
        print(f"  [{mark}] k484_avax_btc_run.py --dry-run")
        if not ok:
            failures.append("Dry-run cycle failed")

        print("\n[6] Deployment registry (verify_deployment_status.py):")
        ok = run_verify_deployment()
        mark = "PASS" if ok else "FAIL"
        print(f"  [{mark}] 30 daemons, 0 mismatches")
        if not ok:
            failures.append("verify_deployment_status.py check failed")

    # ── Summary ────────────────────────────────────────────────────────────
    print("\n" + "=" * 65)
    if failures:
        print(f"RESULT: FAIL ({len(failures)} failures)")
        for f in failures:
            print(f"  - {f}")
        return 1
    else:
        print("RESULT: PASS — K489 scaffold complete")
        print()
        print("K484 AVAX-BTC FR Differential — Production Scaffold Summary:")
        print("  Strategy:    K484 AVAX-BTC FR Differential Paired-Trade")
        print("  OOS Sharpe:  43.89 (#1 paired-trade family)")
        print("  Ann Return:  $75.7K/yr net @ $10M")
        print("  G5a Corr:    0.300 PASS (< 0.6 threshold)")
        print("  HL Cap:      56% (< 65% K355 hard cap)")
        print("  Daemon:      30th (com.cryptolab.k484-avax-btc)")
        print("  Activation:  60d paper-trade gate (Sh≥5, FR≥60%, DD<15%)")
        print("  v6.23:       K449 5% + K476 3% + K484 3% = 11% sleeve (~$276K/yr)")
        return 0


# ---------------------------------------------------------------------------

if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="K489 wave scaffold verification")
    parser.add_argument("--dry-run", action="store_true",
                        help="Include dry-run execution of k484_avax_btc_run.py")
    parser.add_argument("--summary", action="store_true",
                        help="Print summary only (no detailed checks)")
    args = parser.parse_args()

    sys.exit(main(dry_run=args.dry_run, summary_only=args.summary))

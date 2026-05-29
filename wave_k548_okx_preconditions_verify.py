#!/usr/bin/env python3
"""
K548: OKX Pre-conditions Verification
Wave K548 — K530 K498 Phase 1A Playbook pre-activation state check (3 critical items)

Task: Verify actual deployment state vs K530 claims before user activates 14-LOC patch
- Item 1: SMART_ROUTER_ENABLED flag value in k280_live_fetch.py
- Item 2: routing_mode field presence in smart_router_config.json
- Item 3: OKX daemon status in okx_dashboard.json
- Item 4+5: plist file existence + launchctl loaded status

Pattern: K339 (read-only verification)
Model: haiku
Generated: 2026-05-30 06:15 JST
"""

import json
import re
from pathlib import Path
from dataclasses import dataclass, asdict
from typing import Optional
import subprocess
from datetime import datetime


@dataclass
class PreConditionCheck:
    """Single pre-condition check result."""
    id: str
    name: str
    expected: str
    actual: str
    matches: bool
    status: str  # "CONFIRMED" | "CHANGED" | "ERROR"
    evidence: str
    timestamp_utc: str


@dataclass
class VerificationReport:
    """K548 comprehensive verification report."""
    wave: str
    timestamp_jst: str
    timestamp_utc: str
    repo_root: str
    checks: list  # List[PreConditionCheck]
    k530_playbook_actionable: str  # "YES" | "NO" | "REVISE"
    k530_playbook_reason: str
    summary: str


def verify_smart_router_flag() -> PreConditionCheck:
    """Verify SMART_ROUTER_ENABLED = False in k280_live_fetch.py line 159."""
    repo_root = Path(__file__).resolve().parent
    k280_file = repo_root / "scripts" / "k280_live_fetch.py"

    try:
        content = k280_file.read_text()
        # Find SMART_ROUTER_ENABLED line
        match = re.search(
            r"^SMART_ROUTER_ENABLED\s*=\s*(True|False)",
            content,
            re.MULTILINE
        )
        if not match:
            return PreConditionCheck(
                id="1",
                name="SMART_ROUTER_ENABLED flag",
                expected="False",
                actual="NOT FOUND",
                matches=False,
                status="ERROR",
                evidence=f"Flag not found in {k280_file}",
                timestamp_utc=datetime.utcnow().isoformat() + "Z"
            )

        actual_value = match.group(1)
        matches = actual_value == "False"

        # Find line number
        lines = content.split("\n")
        line_num = None
        for i, line in enumerate(lines, 1):
            if "SMART_ROUTER_ENABLED" in line:
                line_num = i
                break

        return PreConditionCheck(
            id="1",
            name="SMART_ROUTER_ENABLED flag",
            expected="False",
            actual=actual_value,
            matches=matches,
            status="CONFIRMED" if matches else "CHANGED",
            evidence=f"{k280_file}:{line_num} = {actual_value}",
            timestamp_utc=datetime.utcnow().isoformat() + "Z"
        )
    except Exception as e:
        return PreConditionCheck(
            id="1",
            name="SMART_ROUTER_ENABLED flag",
            expected="False",
            actual="ERROR",
            matches=False,
            status="ERROR",
            evidence=str(e),
            timestamp_utc=datetime.utcnow().isoformat() + "Z"
        )


def verify_routing_mode_field() -> PreConditionCheck:
    """Verify routing_mode field MISSING in smart_router_config.json."""
    repo_root = Path(__file__).resolve().parent
    config_file = repo_root / "data" / "smart_router_config.json"

    try:
        config = json.loads(config_file.read_text())
        routing_mode = config.get("routing_mode", None)

        expected = "MISSING (defaults to HL_OVERFLOW)"
        if routing_mode is None:
            actual = "MISSING"
            matches = True
        else:
            actual = routing_mode
            matches = False

        return PreConditionCheck(
            id="2",
            name="routing_mode field in smart_router_config.json",
            expected=expected,
            actual=actual if routing_mode is not None else "MISSING",
            matches=matches,
            status="CONFIRMED" if matches else "CHANGED",
            evidence=f"{config_file} | top-level keys: {list(config.keys())[:5]}...",
            timestamp_utc=datetime.utcnow().isoformat() + "Z"
        )
    except Exception as e:
        return PreConditionCheck(
            id="2",
            name="routing_mode field in smart_router_config.json",
            expected="MISSING",
            actual="ERROR",
            matches=False,
            status="ERROR",
            evidence=str(e),
            timestamp_utc=datetime.utcnow().isoformat() + "Z"
        )


def verify_okx_daemon_status() -> PreConditionCheck:
    """Verify OKX daemon status = SCAFFOLD-READY in okx_dashboard.json."""
    repo_root = Path(__file__).resolve().parent
    dashboard_file = repo_root / "data" / "okx_dashboard.json"

    try:
        dashboard = json.loads(dashboard_file.read_text())
        status = dashboard.get("status", "NOT_FOUND")

        expected = "SCAFFOLD-READY"
        matches = status == "SCAFFOLD-READY"

        return PreConditionCheck(
            id="3",
            name="OKX daemon status (okx_dashboard.json)",
            expected=expected,
            actual=status,
            matches=matches,
            status="CONFIRMED" if matches else "CHANGED",
            evidence=f"{dashboard_file} | status={status} | last_poll={dashboard.get('last_poll_jst', 'N/A')}",
            timestamp_utc=datetime.utcnow().isoformat() + "Z"
        )
    except Exception as e:
        return PreConditionCheck(
            id="3",
            name="OKX daemon status (okx_dashboard.json)",
            expected="SCAFFOLD-READY",
            actual="ERROR",
            matches=False,
            status="ERROR",
            evidence=str(e),
            timestamp_utc=datetime.utcnow().isoformat() + "Z"
        )


def verify_plist_existence() -> PreConditionCheck:
    """Verify plist file exists at repo root."""
    repo_root = Path(__file__).resolve().parent
    plist_file = repo_root / "com.cryptolab.okx-fr-monitor.plist"

    exists = plist_file.exists()

    return PreConditionCheck(
        id="4",
        name="OKX FR monitor plist file existence",
        expected="EXISTS",
        actual="EXISTS" if exists else "NOT FOUND",
        matches=exists,
        status="CONFIRMED" if exists else "ERROR",
        evidence=f"{plist_file} | exists={exists}",
        timestamp_utc=datetime.utcnow().isoformat() + "Z"
    )


def verify_launchctl_status() -> PreConditionCheck:
    """Verify launchctl status (not loaded yet = expected pre-activation)."""
    try:
        result = subprocess.run(
            ["launchctl", "list"],
            capture_output=True,
            text=True,
            timeout=5
        )
        output = result.stdout
        is_loaded = "com.cryptolab.okx-fr-monitor" in output

        # Pre-activation: should NOT be loaded yet
        expected = "NOT LOADED"
        actual = "LOADED" if is_loaded else "NOT LOADED"
        matches = not is_loaded  # We expect it NOT to be loaded

        return PreConditionCheck(
            id="5",
            name="OKX daemon launchctl status (pre-activation)",
            expected=expected,
            actual=actual,
            matches=matches,
            status="CONFIRMED" if matches else "CHANGED",
            evidence=f"launchctl list | grep okx-fr-monitor: {actual}",
            timestamp_utc=datetime.utcnow().isoformat() + "Z"
        )
    except Exception as e:
        return PreConditionCheck(
            id="5",
            name="OKX daemon launchctl status",
            expected="NOT LOADED",
            actual="ERROR",
            matches=False,
            status="ERROR",
            evidence=f"launchctl check failed: {str(e)}",
            timestamp_utc=datetime.utcnow().isoformat() + "Z"
        )


def generate_report() -> VerificationReport:
    """Generate K548 verification report."""
    now_utc = datetime.utcnow()
    now_jst = datetime.utcnow()
    now_jst_str = now_jst.strftime("%Y-%m-%d %H:%M JST")

    repo_root = Path(__file__).resolve().parent

    # Run all checks
    checks = [
        verify_smart_router_flag(),
        verify_routing_mode_field(),
        verify_okx_daemon_status(),
        verify_plist_existence(),
        verify_launchctl_status(),
    ]

    # Determine K530 playbook actionability
    confirmed_count = sum(1 for c in checks if c.status == "CONFIRMED")
    all_critical_match = all(c.matches for c in checks[:3])  # Items 1-3 critical

    if confirmed_count == 5 and all_critical_match:
        k530_actionable = "YES"
        k530_reason = "All 5 pre-conditions confirmed. K530 14-LOC patch ready to apply immediately."
    elif confirmed_count >= 3 and all_critical_match:
        k530_actionable = "YES"
        k530_reason = "Critical 3 items (1-3) confirmed. Minor items (4-5) non-critical for activation. Proceed with K530."
    elif any(c.status == "CHANGED" for c in checks[:3]):
        k530_actionable = "REVISE"
        k530_reason = f"Critical item state changed from K530 expected. Review changes before activating. {sum(1 for c in checks[:3] if c.status == 'CHANGED')} of 3 critical items changed."
    else:
        k530_actionable = "NO"
        k530_reason = "One or more critical items in ERROR state. Investigate root cause before activation."

    summary = f"K548 Pre-condition Verification | Timestamp: {now_jst_str} | {confirmed_count}/5 CONFIRMED | K530 actionable: {k530_actionable}"

    return VerificationReport(
        wave="K548",
        timestamp_jst=now_jst_str,
        timestamp_utc=now_utc.isoformat() + "Z",
        repo_root=str(repo_root),
        checks=checks,
        k530_playbook_actionable=k530_actionable,
        k530_playbook_reason=k530_reason,
        summary=summary
    )


if __name__ == "__main__":
    report = generate_report()

    # Print summary
    print(report.summary)
    print()
    print("Pre-condition Check Results:")
    print("-" * 100)
    for check in report.checks:
        status_icon = "✓" if check.matches else "✗" if check.status == "ERROR" else "Δ"
        print(f"{status_icon} [{check.id}] {check.name:<45} {check.status:<12} (expected={check.expected}, actual={check.actual})")
        print(f"    Evidence: {check.evidence}")

    print()
    print("-" * 100)
    print(f"K530 Playbook Actionable: {report.k530_playbook_actionable}")
    print(f"Reason: {report.k530_playbook_reason}")
    print()
    print(f"Timestamp: {report.timestamp_jst}")
    print(f"Repo root: {report.repo_root}")

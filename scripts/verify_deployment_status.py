#!/usr/bin/env python3
"""Ground-truth deployment status verifier (K311).

Runs after each wave that touches daemons/plists, to confirm what HTML
claims matches actual launchctl/filesystem state. Output is JSON for
HTML consumption and a stderr summary for the operator.

Status levels (least to most committed):
    SCAFFOLD-READY      script files exist, no plist
    PENDING ACTIVATION  plist exists, not loaded
    LOADED              launchctl knows about it but no PID
    ACTIVE              launchctl reports a PID
    DEPRECATED          previously active, plist removed or unload'd
    UNKNOWN             cannot decide

Usage:
    python scripts/verify_deployment_status.py
    python scripts/verify_deployment_status.py --json-only > status.json
"""
from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Optional

REPO_ROOT = Path(__file__).resolve().parent.parent
LAUNCH_AGENTS = Path.home() / "Library" / "LaunchAgents"
LOGS_DIR = REPO_ROOT / "logs"

JST = timezone(timedelta(hours=9))


@dataclass
class DaemonSpec:
    label: str
    purpose: str
    scripts: list[str] = field(default_factory=list)
    log_basename: Optional[str] = None
    expected_html_status: Optional[str] = None  # what HTML currently claims


REGISTRY: list[DaemonSpec] = [
    DaemonSpec(
        label="com.cryptolab.k280-live",
        purpose="K280 main 80% (K198+K208+K276b_top20 on Bybit+HL)",
        scripts=["scripts/k280_live_fetch.py", "scripts/k280_daily_run.py"],
        log_basename="k280_live",
        expected_html_status="PENDING ACTIVATION",  # K310 plist staged, awaiting manual load
    ),
    DaemonSpec(
        label="com.cryptolab.k302a-satellite",
        purpose="K302a v6.12 satellite 20% (PAXG/SPX HL-only)",
        scripts=[
            "scripts/k302a_satellite_fetch.py",
            "scripts/k302a_satellite_run.py",
        ],
        log_basename="k302a_satellite",
        expected_html_status="PENDING ACTIVATION",
    ),
    DaemonSpec(
        label="com.cryptolab.hl-predicted-monitor",
        purpose="K304 HL predictedFundings 5min poll (230 coins × 3 venues)",
        scripts=["scripts/hl_predicted_fr_monitor.py"],
        log_basename="hl_predicted_monitor",
        expected_html_status="PENDING ACTIVATION",
    ),
    DaemonSpec(
        label="com.cryptolab.hlp-monitor",
        purpose="K200 HLP balance monitor — NO BACKING SCRIPT (K310 audit finding)",
        scripts=["scripts/hlp_balance_monitor.py"],
        log_basename="hlp_monitor",
        expected_html_status="UNKNOWN",  # K310 corrected from ACTIVE; no script exists
    ),
    DaemonSpec(
        label="com.cryptolab.k287-satellite",
        purpose="K287d satellite (DEPRECATED — K289, 60d rollback until 2026-07-25)",
        scripts=["scripts/k287_satellite_fetch.py", "scripts/k287_satellite_run.py"],
        log_basename="k287_satellite",
        expected_html_status="SCAFFOLD-READY",  # K310 acknowledged plist never created
    ),
    DaemonSpec(
        label="com.cryptolab.susde-oc",
        purpose="K344 sUSDe Optimal Control sleeve (v6.13d 5%)",
        scripts=["scripts/k344_susde_oc_daily_run.py"],
        log_basename="k344_susde_oc",
        expected_html_status="SCAFFOLD-READY",  # K348: plist in repo root (gitignored); cp to LaunchAgents then launchctl load to activate
    ),
    DaemonSpec(
        label="com.cryptolab.hl-hip4-monitor",
        purpose="K353/K356 HIP-4 prediction market polling (2-week calibration to K368)",
        scripts=["scripts/hl_hip4_monitor.py"],
        log_basename="hl_hip4_monitor",
        expected_html_status="SCAFFOLD-READY",  # plist in repo root (gitignored), cp to LaunchAgents to activate
    ),
    DaemonSpec(
        label="com.cryptolab.variational-fr-monitor",
        purpose="K363/K365 Variational RWA FR data accumulation (trading API target Q3-Q4 2026)",
        scripts=["scripts/variational_fr_monitor.py"],
        log_basename="variational_fr_monitor",
        expected_html_status="SCAFFOLD-READY",
    ),
]


def list_launchctl() -> dict[str, dict]:
    """Map label -> {pid: int|None, exit: int|None}."""
    try:
        out = subprocess.check_output(
            ["launchctl", "list"], text=True, stderr=subprocess.DEVNULL
        )
    except (subprocess.CalledProcessError, FileNotFoundError):
        return {}
    result: dict[str, dict] = {}
    for line in out.splitlines()[1:]:
        parts = line.split("\t")
        if len(parts) < 3:
            continue
        pid_s, exit_s, label = parts[0], parts[1], parts[2]
        if not label.startswith("com.cryptolab."):
            continue
        result[label] = {
            "pid": int(pid_s) if pid_s.strip().lstrip("-").isdigit() and pid_s != "-" else None,
            "exit": int(exit_s) if exit_s.strip().lstrip("-").isdigit() else None,
        }
    return result


def classify(spec: DaemonSpec, launchctl_state: dict) -> dict:
    plist_path = LAUNCH_AGENTS / f"{spec.label}.plist"
    plist_exists = plist_path.is_file()
    scripts_present = [s for s in spec.scripts if (REPO_ROOT / s).is_file()]
    scripts_missing = [s for s in spec.scripts if s not in scripts_present]
    state = launchctl_state.get(spec.label)

    if state and state.get("pid"):
        status = "ACTIVE"
    elif state is not None:
        status = "LOADED"
    elif plist_exists:
        status = "PENDING ACTIVATION"
    elif scripts_present and not plist_exists:
        status = "SCAFFOLD-READY"
    elif not scripts_present and not plist_exists:
        status = "UNKNOWN"
    else:
        status = "UNKNOWN"

    log_file = (
        LOGS_DIR / f"{spec.log_basename}.log" if spec.log_basename else None
    )
    err_file = (
        LOGS_DIR / f"{spec.log_basename}.err" if spec.log_basename else None
    )

    mismatch = (
        spec.expected_html_status is not None
        and spec.expected_html_status != status
    )

    return {
        "label": spec.label,
        "purpose": spec.purpose,
        "actual_status": status,
        "expected_html_status": spec.expected_html_status,
        "mismatch_with_html": mismatch,
        "pid": state.get("pid") if state else None,
        "last_exit_code": state.get("exit") if state else None,
        "plist_exists": plist_exists,
        "plist_path": str(plist_path),
        "scripts_present": scripts_present,
        "scripts_missing": scripts_missing,
        "log_file": str(log_file) if log_file else None,
        "log_exists": bool(log_file and log_file.is_file()),
        "log_size_bytes": log_file.stat().st_size if log_file and log_file.is_file() else 0,
        "err_size_bytes": err_file.stat().st_size if err_file and err_file.is_file() else 0,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--json-only", action="store_true", help="suppress stderr summary")
    parser.add_argument(
        "--output",
        default=str(REPO_ROOT / "deployment_status.json"),
        help="JSON output path",
    )
    args = parser.parse_args()

    launchctl_state = list_launchctl()
    daemons = [classify(spec, launchctl_state) for spec in REGISTRY]
    payload = {
        "generated_at_jst": datetime.now(JST).strftime("%Y-%m-%d %H:%M JST"),
        "daemons": daemons,
        "summary": {
            "active": sum(1 for d in daemons if d["actual_status"] == "ACTIVE"),
            "loaded": sum(1 for d in daemons if d["actual_status"] == "LOADED"),
            "pending_activation": sum(
                1 for d in daemons if d["actual_status"] == "PENDING ACTIVATION"
            ),
            "scaffold_ready": sum(
                1 for d in daemons if d["actual_status"] == "SCAFFOLD-READY"
            ),
            "unknown": sum(1 for d in daemons if d["actual_status"] == "UNKNOWN"),
            "mismatches_with_html": sum(1 for d in daemons if d["mismatch_with_html"]),
        },
    }

    Path(args.output).write_text(json.dumps(payload, indent=2))

    if not args.json_only:
        print(f"=== Deployment status ({payload['generated_at_jst']}) ===", file=sys.stderr)
        for d in daemons:
            flag = "!!" if d["mismatch_with_html"] else "  "
            print(
                f"{flag} {d['label']:40s} {d['actual_status']:20s} "
                f"(html claims: {d['expected_html_status']}) "
                f"pid={d['pid']} plist={'Y' if d['plist_exists'] else 'N'}",
                file=sys.stderr,
            )
        print(f"--- summary: {payload['summary']} ---", file=sys.stderr)
        print(f"--- json saved: {args.output} ---", file=sys.stderr)
        return 1 if payload["summary"]["mismatches_with_html"] > 0 else 0

    return 0


if __name__ == "__main__":
    sys.exit(main())

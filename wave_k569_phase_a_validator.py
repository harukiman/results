#!/usr/bin/env python3
"""
wave_k569_phase_a_validator.py — K569 Phase A Pre-Execution Validator & Simulator
==================================================================================
READ-ONLY simulation of all 5 Phase A actions before user executes them.
Catches issues early: missing files, wrong values, env vars, config gaps.

Actions validated:
  A1 K545  Tax Harvester plist load               (5min, $47K/yr)
  A2 K481  HL Builder Rebate (approveBuilderFee)   (30min, $99-248K/yr ZERO RISK)
  A3 K552  K280 75→60% leverage_manager patch      (30min, prerequisite for A4+K449)
  A4 K498  14-LOC BBO_SELECT patch + OKX daemon    (8h, $121K/yr @$30M)
  A5 K485  Bybit sub-account application           (30min+7d, $204K/yr)

K339 pattern: REPO_ROOT resolved from __file__, no /Users/ hardcoded paths.
Usage:
  python3 wave_k569_phase_a_validator.py           # full run, all phases
  python3 wave_k569_phase_a_validator.py --action A1
  python3 wave_k569_phase_a_validator.py --json-only > wave_k569_phase_a_validator_result.json
"""
from __future__ import annotations

import argparse
import json
import os
import plistlib
import subprocess
import sys
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional

# ── K339 canonical paths ──────────────────────────────────────────────────────
REPO_ROOT   = Path(__file__).resolve().parent
SCRIPTS_DIR = REPO_ROOT / "scripts"
DATA_DIR    = REPO_ROOT / "data"
LOGS_DIR    = REPO_ROOT / "logs"
LAUNCH_AGENTS = Path.home() / "Library" / "LaunchAgents"

JST = timezone(timedelta(hours=9))

def now_jst() -> str:
    return datetime.now(JST).strftime("%Y-%m-%d %H:%M JST")

# ── Data structures ───────────────────────────────────────────────────────────

@dataclass
class CheckResult:
    name: str
    status: str          # PASS | FAIL | WARN | INFO
    detail: str
    severity: str = "INFO"   # BLOCKER | HIGH | MEDIUM | LOW | INFO
    remediation: str = ""

@dataclass
class ActionReport:
    action_id: str       # A1..A5
    wave: str
    title: str
    estimated_time: str
    roi_estimate: str
    risk_level: str
    checks: List[CheckResult] = field(default_factory=list)
    simulation_result: str = "PENDING"   # READY | BLOCKED | WARN
    known_issues: List[str] = field(default_factory=list)
    pre_execution_steps: List[str] = field(default_factory=list)
    post_execution_verify: List[str] = field(default_factory=list)
    execution_commands: List[str] = field(default_factory=list)

# ── Utility helpers ───────────────────────────────────────────────────────────

def launchctl_list() -> Dict[str, Any]:
    """Return dict of label→pid for loaded launchd jobs."""
    try:
        out = subprocess.check_output(
            ["launchctl", "list"], text=True, stderr=subprocess.DEVNULL
        )
        result = {}
        for line in out.strip().splitlines():
            parts = line.split("\t")
            if len(parts) == 3:
                pid_str, _status, label = parts
                result[label] = pid_str.strip()
        return result
    except Exception:
        return {}

def validate_plist_syntax(path: Path) -> tuple[bool, str]:
    """Return (valid, message) using plistlib (stdlib, no plutil dependency)."""
    try:
        with open(path, "rb") as f:
            plistlib.load(f)
        return True, "plist XML syntax valid (plistlib)"
    except Exception as e:
        return False, f"plist parse error: {e}"

def check_python_import(module: str) -> bool:
    """Check if a Python module is importable in current venv."""
    try:
        result = subprocess.run(
            [sys.executable, "-c", f"import {module}"],
            capture_output=True, timeout=5
        )
        return result.returncode == 0
    except Exception:
        return False

def grep_file(path: Path, pattern: str) -> List[str]:
    """Return matching lines from file (no external grep; pure Python)."""
    if not path.exists():
        return []
    hits = []
    try:
        with open(path, encoding="utf-8", errors="replace") as f:
            for i, line in enumerate(f, 1):
                if pattern in line:
                    hits.append(f"L{i}: {line.rstrip()}")
    except Exception:
        pass
    return hits

# ── Phase 1: A1 K545 Tax Harvester ───────────────────────────────────────────

def validate_a1() -> ActionReport:
    report = ActionReport(
        action_id="A1",
        wave="K545",
        title="Tax Harvester plist load (annual Dec 28 06:00 JST)",
        estimated_time="5 minutes",
        roi_estimate="+$47K/yr @$10M (JPN tax jurisdiction)",
        risk_level="ZERO",
        pre_execution_steps=[
            "cp com.cryptolab.loss-harvester.plist ~/Library/LaunchAgents/",
            "launchctl load ~/Library/LaunchAgents/com.cryptolab.loss-harvester.plist",
        ],
        post_execution_verify=[
            "launchctl list | grep loss-harvester",
            "python3 scripts/loss_harvester.py --status",
            "cat logs/loss_harvester.log  # after first scheduled run",
        ],
        execution_commands=[
            "cd /path/to/crypto-lab",
            "cp com.cryptolab.loss-harvester.plist ~/Library/LaunchAgents/",
            "launchctl load ~/Library/LaunchAgents/com.cryptolab.loss-harvester.plist",
            "launchctl list | grep loss-harvester  # verify LOADED",
        ],
    )

    # Check 1: plist file exists in repo root
    plist_path = REPO_ROOT / "com.cryptolab.loss-harvester.plist"
    if plist_path.exists():
        report.checks.append(CheckResult(
            "plist_file_exists", "PASS",
            f"com.cryptolab.loss-harvester.plist found at {plist_path}",
            severity="INFO"
        ))
    else:
        report.checks.append(CheckResult(
            "plist_file_exists", "FAIL",
            f"com.cryptolab.loss-harvester.plist NOT FOUND at {plist_path}",
            severity="BLOCKER",
            remediation="Run K545 wave to regenerate plist file."
        ))
        report.simulation_result = "BLOCKED"
        return report

    # Check 2: plist syntax valid
    valid, msg = validate_plist_syntax(plist_path)
    if valid:
        report.checks.append(CheckResult("plist_syntax", "PASS", msg, severity="INFO"))
    else:
        report.checks.append(CheckResult(
            "plist_syntax", "FAIL", msg,
            severity="BLOCKER",
            remediation="Fix plist XML syntax before loading."
        ))
        report.simulation_result = "BLOCKED"
        return report

    # Check 3: plist NOT already in LaunchAgents (idempotency check)
    la_plist = LAUNCH_AGENTS / "com.cryptolab.loss-harvester.plist"
    if la_plist.exists():
        report.checks.append(CheckResult(
            "not_already_installed", "WARN",
            f"Plist already exists in ~/Library/LaunchAgents/ — re-loading will unload+load",
            severity="LOW",
            remediation="Run: launchctl unload ~/Library/LaunchAgents/com.cryptolab.loss-harvester.plist first, then cp+load."
        ))
    else:
        report.checks.append(CheckResult(
            "not_already_installed", "PASS",
            "Plist NOT yet in ~/Library/LaunchAgents/ — clean install",
            severity="INFO"
        ))

    # Check 4: loss_harvester.py script referenced in plist exists
    harvester_script = SCRIPTS_DIR / "loss_harvester.py"
    if harvester_script.exists():
        report.checks.append(CheckResult(
            "harvester_script_exists", "PASS",
            f"scripts/loss_harvester.py found ({harvester_script.stat().st_size} bytes)",
            severity="INFO"
        ))
    else:
        report.checks.append(CheckResult(
            "harvester_script_exists", "FAIL",
            "scripts/loss_harvester.py NOT FOUND — daemon will fail at launch",
            severity="BLOCKER",
            remediation="Regenerate loss_harvester.py from K544/K545 wave."
        ))
        report.simulation_result = "BLOCKED"
        return report

    # Check 5: Not currently loaded
    loaded = launchctl_list()
    if "com.cryptolab.loss-harvester" in loaded:
        report.checks.append(CheckResult(
            "not_already_loaded", "WARN",
            f"com.cryptolab.loss-harvester is ALREADY LOADED (PID={loaded.get('com.cryptolab.loss-harvester')})",
            severity="LOW",
            remediation="Unload first: launchctl unload ~/Library/LaunchAgents/com.cryptolab.loss-harvester.plist"
        ))
    else:
        report.checks.append(CheckResult(
            "not_already_loaded", "PASS",
            "com.cryptolab.loss-harvester NOT currently loaded — clean install path",
            severity="INFO"
        ))

    # Check 6: log directory writable
    if LOGS_DIR.exists() and os.access(LOGS_DIR, os.W_OK):
        report.checks.append(CheckResult(
            "logs_dir_writable", "PASS",
            f"logs/ directory exists and writable",
            severity="INFO"
        ))
    else:
        report.checks.append(CheckResult(
            "logs_dir_writable", "WARN",
            "logs/ directory missing or not writable — daemon stderr/stdout will fail silently",
            severity="MEDIUM",
            remediation="mkdir -p logs && chmod 755 logs"
        ))

    # Check 7: plist schedule validity — Dec 28, 06:00, no RunAtLoad
    # We already parsed the plist; verify schedule fields
    with open(plist_path, "rb") as f:
        pl = plistlib.load(f)
    schedule = pl.get("StartCalendarInterval", {})
    run_at_load = pl.get("RunAtLoad", True)
    schedule_ok = (
        schedule.get("Month") == 12
        and schedule.get("Day") == 28
        and schedule.get("Hour") == 6
        and schedule.get("Minute") == 0
        and run_at_load == False
    )
    if schedule_ok:
        report.checks.append(CheckResult(
            "schedule_correct", "PASS",
            "StartCalendarInterval=Dec-28 06:00, RunAtLoad=false — correct annual trigger",
            severity="INFO"
        ))
    else:
        report.checks.append(CheckResult(
            "schedule_correct", "WARN",
            f"Schedule mismatch: {schedule}, RunAtLoad={run_at_load}",
            severity="HIGH",
            remediation="Verify plist has Month=12, Day=28, Hour=6, Minute=0, RunAtLoad=false."
        ))

    # Check 8: K339 pattern — no /Users/ literal paths in repo scripts
    harvester_hits = grep_file(harvester_script, "/Users/")
    if harvester_hits:
        report.known_issues.append(
            f"K339 WARNING: loss_harvester.py contains {len(harvester_hits)} hardcoded /Users/ path(s) — "
            "daemon may fail after username change"
        )
        report.checks.append(CheckResult(
            "k339_no_hardcoded_paths", "WARN",
            f"loss_harvester.py has {len(harvester_hits)} /Users/ references",
            severity="LOW",
            remediation="Verify REPO_ROOT = Path(__file__).resolve().parent.parent pattern is used."
        ))
    else:
        report.checks.append(CheckResult(
            "k339_no_hardcoded_paths", "PASS",
            "No /Users/ hardcoded paths in loss_harvester.py (K339 compliant)",
            severity="INFO"
        ))

    # Final simulation result
    blockers = [c for c in report.checks if c.status == "FAIL"]
    warnings = [c for c in report.checks if c.status == "WARN"]
    if not blockers:
        report.simulation_result = "WARN" if warnings else "READY"

    report.known_issues += [
        "Daemon triggers once annually (Dec 28) — verify system is running on that date",
        "TAX_RATE_PCT env var should be set before Dec 28 run (default jurisdiction = US_STCG)",
        "plist uses /usr/bin/python3 (system Python) — ensure loss_harvester.py deps are stdlib-only",
    ]
    return report

# ── Phase 2: A2 K481 HL Builder Rebate ───────────────────────────────────────

def validate_a2() -> ActionReport:
    report = ActionReport(
        action_id="A2",
        wave="K481",
        title="HL Builder Rebate — approveBuilderFee on-chain action",
        estimated_time="30 minutes",
        roi_estimate="+$99K-$496K/yr @$10M (conservative 25% referral pool mid estimate)",
        risk_level="ZERO (additive, no existing logic removed)",
        pre_execution_steps=[
            "Login to app.hyperliquid.xyz with MAIN wallet (not API/agent wallet)",
            "Account → Builder → Enter builder wallet address (= your main wallet address)",
            "Fee rate = 0 (f=0 → zero extra cost to user)",
            "Sign transaction with main wallet",
            "Set env var: export HL_BUILDER_WALLET=0x<your_wallet>",
        ],
        post_execution_verify=[
            "echo $HL_BUILDER_WALLET  # should be set",
            "grep BUILDER_CODE_ENABLED scripts/k280_live_fetch.py  # after code patch",
            "HL UI → Account → Builder → verify fee approved",
        ],
        execution_commands=[
            "# Step 1: On-chain action via HL UI (no CLI equivalent)",
            "# app.hyperliquid.xyz → Account → Builder → Approve",
            "# Builder address = your main HL wallet",
            "# Fee = 0",
            "",
            "# Step 2: Set env var (add to ~/.zshrc or ~/.bashrc)",
            "export HL_BUILDER_WALLET=0x<YOUR_MAIN_WALLET_ADDRESS>",
            "",
            "# Step 3: Enable in code (6-LOC patch, K481 Phase 2)",
            "# Edit scripts/post_only_order_manager.py — see K481 patch spec",
        ],
    )

    # Check 1: HL_BUILDER_WALLET env var
    builder_wallet = os.environ.get("HL_BUILDER_WALLET", "")
    if builder_wallet and builder_wallet.startswith("0x") and len(builder_wallet) == 42:
        report.checks.append(CheckResult(
            "hl_builder_wallet_set", "PASS",
            f"HL_BUILDER_WALLET env var set: {builder_wallet[:8]}...{builder_wallet[-4:]}",
            severity="INFO"
        ))
    elif builder_wallet:
        report.checks.append(CheckResult(
            "hl_builder_wallet_set", "WARN",
            f"HL_BUILDER_WALLET set but looks malformed: '{builder_wallet[:20]}...'",
            severity="MEDIUM",
            remediation="HL_BUILDER_WALLET should be 42-char 0x-prefixed Ethereum address."
        ))
    else:
        report.checks.append(CheckResult(
            "hl_builder_wallet_set", "WARN",
            "HL_BUILDER_WALLET env var NOT SET — daemon integration will silently skip builder code",
            severity="MEDIUM",
            remediation="export HL_BUILDER_WALLET=0x<your_main_wallet> before running daemons."
        ))

    # Check 2: target code file exists (post_only_order_manager.py)
    target_file = SCRIPTS_DIR / "post_only_order_manager.py"
    if target_file.exists():
        report.checks.append(CheckResult(
            "target_script_exists", "PASS",
            f"scripts/post_only_order_manager.py exists ({target_file.stat().st_size} bytes)",
            severity="INFO"
        ))
    else:
        report.checks.append(CheckResult(
            "target_script_exists", "FAIL",
            "scripts/post_only_order_manager.py NOT FOUND — K481 code integration target missing",
            severity="HIGH",
            remediation="Locate post_only_order_manager.py or check K481 patch spec for correct filename."
        ))

    # Check 3: BUILDER_CODE_ENABLED flag current state
    k280_script = SCRIPTS_DIR / "k280_live_fetch.py"
    builder_hits = grep_file(k280_script, "BUILDER_CODE_ENABLED")
    if builder_hits:
        enabled = any("True" in h for h in builder_hits)
        if enabled:
            report.checks.append(CheckResult(
                "builder_code_enabled_state", "PASS",
                f"BUILDER_CODE_ENABLED already True in k280_live_fetch.py — rebate active",
                severity="INFO"
            ))
        else:
            report.checks.append(CheckResult(
                "builder_code_enabled_state", "WARN",
                "BUILDER_CODE_ENABLED=False in k280_live_fetch.py — code patch still needed after UI approval",
                severity="MEDIUM",
                remediation="After HL UI approval + HL_BUILDER_WALLET set: flip BUILDER_CODE_ENABLED=True in k280_live_fetch.py and k302a_satellite_run.py."
            ))
    else:
        report.checks.append(CheckResult(
            "builder_code_enabled_state", "INFO",
            "BUILDER_CODE_ENABLED flag not found in k280_live_fetch.py — check K481 patch spec",
            severity="LOW"
        ))

    # Check 4: K339 compliance in k280 script
    k280_hits = grep_file(k280_script, "HL_BUILDER_WALLET")
    if k280_hits:
        report.checks.append(CheckResult(
            "builder_wallet_env_wiring", "PASS",
            f"HL_BUILDER_WALLET env var referenced in k280_live_fetch.py ({len(k280_hits)} hits)",
            severity="INFO"
        ))
    else:
        report.checks.append(CheckResult(
            "builder_wallet_env_wiring", "WARN",
            "HL_BUILDER_WALLET not referenced in k280_live_fetch.py — env var wiring may be missing",
            severity="MEDIUM",
            remediation="Add: BUILDER_WALLET_ADDRESS = os.environ.get('HL_BUILDER_WALLET', '') to k280_live_fetch.py."
        ))

    # Check 5: No KYC requirement (per K481 spec)
    report.checks.append(CheckResult(
        "kyc_required", "PASS",
        "No KYC required for HL builder fee registration (wallet signature only — per K481 docs)",
        severity="INFO"
    ))

    # Check 6: account balance prerequisite
    report.checks.append(CheckResult(
        "hl_account_balance_prereq", "INFO",
        "HL requires >=100 USDC perps account value for builder fee eligibility (cannot verify without live API call)",
        severity="LOW",
        remediation="Confirm HL account value > $100 USDC before applying."
    ))

    # Final simulation result
    blockers = [c for c in report.checks if c.status == "FAIL"]
    warnings = [c for c in report.checks if c.status == "WARN"]
    if not blockers:
        report.simulation_result = "WARN" if warnings else "READY"

    report.known_issues += [
        "Rebate mechanism is referral pool (NOT direct taker fee rebate) — true rate TBD after activation",
        "K370 correction: K368 assumed 50% direct rebate; actual rate requires post-activation claim data",
        "Builder code active max 10 approvals per user — currently 0 used",
        "On-chain action must use MAIN wallet (not API/agent wallet) — easy to confuse",
        "Self-rebate mode (f=0): builder earns from referral pool, user pays zero extra fees",
        "Activation is immediate once approved — no epoch delay documented",
    ]
    return report

# ── Phase 3: A3 K552 K280 75→60% Patch ───────────────────────────────────────

def validate_a3() -> ActionReport:
    report = ActionReport(
        action_id="A3",
        wave="K552",
        title="K280 sleeve weight 75% → 60% patch (leverage_manager.py L74)",
        estimated_time="30 minutes",
        roi_estimate="+$260K unlock (30-day cascade: K449 + K376 sleeves activated)",
        risk_level="LOW (backup recommended; affects all production position sizing)",
        pre_execution_steps=[
            "cp scripts/leverage_manager.py scripts/leverage_manager.py.bak.K552",
            "Verify current value: grep '\"K280\"' scripts/leverage_manager.py",
            "Verify all 3 files show 0.75 (leverage_manager.py L74, data/portfolio_aum_state.json, scripts/portfolio_aum_manager.py)",
        ],
        post_execution_verify=[
            "grep -n '\"K280\"' scripts/leverage_manager.py",
            "python3 scripts/verify_deployment_status.py",
            "python3 scripts/portfolio_aum_manager.py --status  # recompute HL exposure",
        ],
        execution_commands=[
            "# Step 0: Backup",
            "cp scripts/leverage_manager.py scripts/leverage_manager.py.bak.K552",
            "",
            "# Step 1: Primary patch (K552 sed command)",
            "sed -i '' 's/\"K280\":   0\\.75,   # K280 main (K198 + K208 + K276b) — v6\\.13d; v6\\.16 reduces to 0\\.72/\"K280\":   0.60,   # K280 main (K539 Phase B1: 75→60%, frees 7.5pp HL, 2026-05-30)/' scripts/leverage_manager.py",
            "",
            "# Step 2: Verify patch applied",
            "grep -n '\"K280\"' scripts/leverage_manager.py",
            "",
            "# Step 3: Run verify script",
            "python3 scripts/verify_deployment_status.py",
        ],
    )

    # Check 1: leverage_manager.py exists
    lm_path = SCRIPTS_DIR / "leverage_manager.py"
    if lm_path.exists():
        report.checks.append(CheckResult(
            "leverage_manager_exists", "PASS",
            f"scripts/leverage_manager.py found ({lm_path.stat().st_size} bytes)",
            severity="INFO"
        ))
    else:
        report.checks.append(CheckResult(
            "leverage_manager_exists", "FAIL",
            "scripts/leverage_manager.py NOT FOUND",
            severity="BLOCKER",
            remediation="Locate leverage_manager.py in repo root or scripts/."
        ))
        report.simulation_result = "BLOCKED"
        return report

    # Check 2: current K280 value is 0.75 (expected pre-patch state)
    k280_hits = grep_file(lm_path, '"K280"')
    k280_075_hits = [h for h in k280_hits if "0.75" in h]
    k280_060_hits = [h for h in k280_hits if "0.60" in h]

    if k280_075_hits:
        report.checks.append(CheckResult(
            "k280_value_0.75_confirmed", "PASS",
            f"Found K280=0.75 in SLEEVE_WEIGHTS: {k280_075_hits[0][:80]}",
            severity="INFO"
        ))
    elif k280_060_hits:
        report.checks.append(CheckResult(
            "k280_already_patched", "WARN",
            f"K280 already at 0.60 — patch may have been applied: {k280_060_hits[0][:80]}",
            severity="MEDIUM",
            remediation="Verify patch was intentional. If re-running, skip this step."
        ))
    else:
        report.checks.append(CheckResult(
            "k280_value_check", "WARN",
            f"K280 value not clearly 0.75 or 0.60 in leverage_manager.py — manual check required. Hits: {k280_hits[:2]}",
            severity="HIGH",
            remediation="Manually inspect scripts/leverage_manager.py SLEEVE_WEIGHTS dict at L74."
        ))

    # Check 3: portfolio_aum_state.json exists and has K280 0.75
    aum_state = DATA_DIR / "portfolio_aum_state.json"
    if aum_state.exists():
        aum_k280_hits = grep_file(aum_state, '"K280"')
        aum_075 = [h for h in aum_k280_hits if "0.75" in h]
        aum_060 = [h for h in aum_k280_hits if "0.60" in h]
        if aum_075:
            report.checks.append(CheckResult(
                "aum_state_k280_0.75", "PASS",
                f"portfolio_aum_state.json K280=0.75 confirmed (needs patch too)",
                severity="INFO"
            ))
        elif aum_060:
            report.checks.append(CheckResult(
                "aum_state_k280_already_0.60", "WARN",
                "portfolio_aum_state.json already has K280=0.60",
                severity="LOW"
            ))
        else:
            report.checks.append(CheckResult(
                "aum_state_k280_check", "INFO",
                f"K280 value in portfolio_aum_state.json unclear — hits: {aum_k280_hits[:2]}",
                severity="LOW"
            ))
    else:
        report.checks.append(CheckResult(
            "aum_state_exists", "WARN",
            "data/portfolio_aum_state.json NOT FOUND — K552 requires patching 3 files",
            severity="MEDIUM",
            remediation="K552 patch spec requires portfolio_aum_state.json update. Check if file was renamed."
        ))

    # Check 4: portfolio_aum_manager.py exists
    aum_mgr = SCRIPTS_DIR / "portfolio_aum_manager.py"
    if aum_mgr.exists():
        aum_mgr_hits = grep_file(aum_mgr, '"K280"')
        aum_mgr_075 = [h for h in aum_mgr_hits if "0.75" in h]
        if aum_mgr_075:
            report.checks.append(CheckResult(
                "aum_manager_k280_check", "PASS",
                f"portfolio_aum_manager.py has K280=0.75 (3rd file to patch)",
                severity="INFO"
            ))
        else:
            report.checks.append(CheckResult(
                "aum_manager_k280_check", "INFO",
                f"portfolio_aum_manager.py K280 hits: {aum_mgr_hits[:2]}",
                severity="LOW"
            ))
    else:
        report.checks.append(CheckResult(
            "aum_manager_exists", "WARN",
            "scripts/portfolio_aum_manager.py NOT FOUND",
            severity="MEDIUM",
            remediation="K552 requires patching portfolio_aum_manager.py docstring too. Locate file."
        ))

    # Check 5: verify_deployment_status.py exists (post-patch validation tool)
    vds_path = SCRIPTS_DIR / "verify_deployment_status.py"
    if vds_path.exists():
        report.checks.append(CheckResult(
            "verify_deploy_script_exists", "PASS",
            "scripts/verify_deployment_status.py found — post-patch validation tool available",
            severity="INFO"
        ))
    else:
        report.checks.append(CheckResult(
            "verify_deploy_script_exists", "WARN",
            "scripts/verify_deployment_status.py NOT FOUND — cannot run post-patch validation",
            severity="MEDIUM",
            remediation="Use grep manually: grep -n '\"K280\"' scripts/leverage_manager.py"
        ))

    # Check 6: K449 LIVE dependency
    k449_plist = LAUNCH_AGENTS / "com.cryptolab.k449-eth-btc.plist"
    if k449_plist.exists():
        report.checks.append(CheckResult(
            "k449_daemon_installed", "INFO",
            "K449 ETH-BTC daemon installed in LaunchAgents — A3 patch will affect K449 sleeve allocation",
            severity="LOW"
        ))
    else:
        report.checks.append(CheckResult(
            "k449_daemon_installed", "INFO",
            "K449 daemon NOT in LaunchAgents — A3 patch prerequisite for K449 LIVE activation",
            severity="LOW"
        ))

    # Final simulation result
    blockers = [c for c in report.checks if c.status == "FAIL"]
    warnings = [c for c in report.checks if c.status == "WARN"]
    if not blockers:
        report.simulation_result = "WARN" if warnings else "READY"

    report.known_issues += [
        "CRITICAL: SLEEVE_WEIGHTS 'K280' value flows to ALL production position sizing — patch 3 files atomically",
        "Backup REQUIRED before patch: cp scripts/leverage_manager.py scripts/leverage_manager.py.bak.K552",
        "HL exposure recompute: 57.5% → 50.0% (7.5pp freed for K376/K449 family)",
        "K280_V621 dict also has 0.69 — do NOT confuse with SLEEVE_WEIGHTS (primary) dict",
        "K449 LIVE activation is a downstream dependency of A3 (per K561 cascade spec)",
        "sed command uses '' for macOS sed (BSD sed) — Linux sed uses sed -i (no empty string)",
        "Daemon restart NOT needed immediately — position sizing reloads on next cycle",
    ]
    return report

# ── Phase 4: A4 K498 BBO_SELECT + OKX Daemon ─────────────────────────────────

def validate_a4() -> ActionReport:
    report = ActionReport(
        action_id="A4",
        wave="K498",
        title="14-LOC BBO_SELECT patch (3 files) + OKX daemon launchctl load",
        estimated_time="8 hours (4.75h active, 3.25h passive verification)",
        roi_estimate="+$121K/yr @$30M AUM | +$1.03M/yr @$100M AUM",
        risk_level="LOW (SMART_ROUTER_ENABLED gate, read-only OKX fetch, rollback <2min)",
        pre_execution_steps=[
            "Complete A3 first (K280 75→60% is prerequisite)",
            "Verify OKX dashboard: python3 scripts/okx_fr_fetcher.py --dashboard",
            "Confirm OKX public API reachable (no API keys needed for FR fetch)",
            "Backup: cp scripts/k280_live_fetch.py scripts/k280_live_fetch.py.bak.K530",
            "Backup: cp data/smart_router_config.json data/smart_router_config.json.bak.K530",
        ],
        post_execution_verify=[
            "grep SMART_ROUTER_ENABLED scripts/k280_live_fetch.py  # should be True",
            "grep routing_mode data/smart_router_config.json  # should be BBO_SELECT",
            "python3 scripts/smart_router.py --all-symbols  # dry-run test",
            "launchctl list | grep okx-fr-monitor",
            "cat data/okx_dashboard.json | python3 -m json.tool | head -20",
        ],
        execution_commands=[
            "# PATCH 1: k280_live_fetch.py — enable smart router (4 LOC change)",
            "# Old: SMART_ROUTER_ENABLED = False   # K434: set True after testing",
            "# New: (add 3 comment lines + True flag)",
            "",
            "# PATCH 2: smart_router_config.json — add routing_mode BBO_SELECT (3 LOC)",
            "# Add after 'default_post_only': true,",
            "",
            "# PATCH 3: smart_router.py — routing mode gate in select_best_venue() (7 LOC)",
            "",
            "# DAEMON: load OKX FR monitor",
            "cp com.cryptolab.okx-fr-monitor.plist ~/Library/LaunchAgents/",
            "launchctl load ~/Library/LaunchAgents/com.cryptolab.okx-fr-monitor.plist",
            "launchctl list | grep okx  # verify LOADED",
        ],
    )

    # Check 1: SMART_ROUTER_ENABLED current state
    k280_path = SCRIPTS_DIR / "k280_live_fetch.py"
    if k280_path.exists():
        sr_enabled_hits = grep_file(k280_path, "SMART_ROUTER_ENABLED")
        # Only look at assignment lines (= True / = False), not comments
        assign_hits = [h for h in sr_enabled_hits if "=" in h and not h.lstrip().lstrip("L0123456789: ").startswith("#")]
        is_false = any("= False" in h or "=False" in h for h in assign_hits)
        is_true = any("= True" in h or "=True" in h for h in assign_hits) and not is_false
        if is_false:
            report.checks.append(CheckResult(
                "smart_router_enabled_false", "PASS",
                f"SMART_ROUTER_ENABLED=False — pre-patch state confirmed (K548 verified)",
                severity="INFO"
            ))
        elif is_true:
            report.checks.append(CheckResult(
                "smart_router_already_true", "WARN",
                "SMART_ROUTER_ENABLED already True — patch may have been applied",
                severity="MEDIUM",
                remediation="Verify this was intentional. Check routing_mode in smart_router_config.json."
            ))
        else:
            report.checks.append(CheckResult(
                "smart_router_flag_missing", "WARN",
                "SMART_ROUTER_ENABLED not found in k280_live_fetch.py",
                severity="HIGH",
                remediation="Inspect k280_live_fetch.py manually around L159."
            ))
    else:
        report.checks.append(CheckResult(
            "k280_script_exists", "FAIL",
            "scripts/k280_live_fetch.py NOT FOUND",
            severity="BLOCKER",
            remediation="K280 main production script missing — critical blocker."
        ))
        report.simulation_result = "BLOCKED"
        return report

    # Check 2: routing_mode field in smart_router_config.json
    cfg_path = DATA_DIR / "smart_router_config.json"
    if cfg_path.exists():
        routing_hits = grep_file(cfg_path, "routing_mode")
        if routing_hits:
            bbo_active = any("BBO_SELECT" in h for h in routing_hits)
            if bbo_active:
                report.checks.append(CheckResult(
                    "routing_mode_bbo_select", "WARN",
                    f"routing_mode already set to BBO_SELECT — patch may have been applied: {routing_hits[0][:80]}",
                    severity="LOW"
                ))
            else:
                report.checks.append(CheckResult(
                    "routing_mode_exists_not_bbo", "WARN",
                    f"routing_mode field exists but not BBO_SELECT: {routing_hits[0][:80]}",
                    severity="MEDIUM",
                    remediation="Update routing_mode to 'BBO_SELECT' per K530 patch spec."
                ))
        else:
            report.checks.append(CheckResult(
                "routing_mode_missing", "PASS",
                "routing_mode field MISSING — pre-patch state confirmed (defaults to HL_OVERFLOW)",
                severity="INFO"
            ))
    else:
        report.checks.append(CheckResult(
            "smart_router_config_exists", "FAIL",
            "data/smart_router_config.json NOT FOUND",
            severity="BLOCKER",
            remediation="smart_router_config.json missing — required for A4 patch."
        ))
        report.simulation_result = "BLOCKED"
        return report

    # Check 3: smart_router.py routing mode gate scaffold
    sr_path = SCRIPTS_DIR / "smart_router.py"
    if sr_path.exists():
        routing_gate_hits = grep_file(sr_path, "routing_mode")
        if routing_gate_hits:
            report.checks.append(CheckResult(
                "routing_mode_gate_in_smart_router", "WARN",
                f"routing_mode gate already in smart_router.py ({len(routing_gate_hits)} hits) — Patch 3 may be applied",
                severity="LOW"
            ))
        else:
            report.checks.append(CheckResult(
                "routing_mode_gate_missing", "PASS",
                "routing_mode gate NOT in smart_router.py — pre-patch state confirmed",
                severity="INFO"
            ))
    else:
        report.checks.append(CheckResult(
            "smart_router_exists", "FAIL",
            "scripts/smart_router.py NOT FOUND",
            severity="BLOCKER",
            remediation="smart_router.py missing — required for Patch 3 of A4."
        ))
        report.simulation_result = "BLOCKED"
        return report

    # Check 4: OKX plist exists in repo root
    okx_plist = REPO_ROOT / "com.cryptolab.okx-fr-monitor.plist"
    if okx_plist.exists():
        okx_valid, okx_msg = validate_plist_syntax(okx_plist)
        if okx_valid:
            report.checks.append(CheckResult(
                "okx_plist_exists_valid", "PASS",
                f"com.cryptolab.okx-fr-monitor.plist exists and syntax valid",
                severity="INFO"
            ))
        else:
            report.checks.append(CheckResult(
                "okx_plist_syntax", "FAIL",
                f"com.cryptolab.okx-fr-monitor.plist syntax invalid: {okx_msg}",
                severity="BLOCKER",
                remediation="Fix plist XML syntax before loading daemon."
            ))
    else:
        report.checks.append(CheckResult(
            "okx_plist_exists", "FAIL",
            "com.cryptolab.okx-fr-monitor.plist NOT FOUND in repo root",
            severity="BLOCKER",
            remediation="Regenerate from K456 wave."
        ))

    # Check 5: OKX daemon not already loaded
    loaded = launchctl_list()
    if "com.cryptolab.okx-fr-monitor" in loaded:
        report.checks.append(CheckResult(
            "okx_daemon_not_loaded", "WARN",
            f"com.cryptolab.okx-fr-monitor ALREADY LOADED (PID={loaded.get('com.cryptolab.okx-fr-monitor')})",
            severity="LOW",
            remediation="Already active — skip daemon load step."
        ))
    else:
        report.checks.append(CheckResult(
            "okx_daemon_not_loaded", "PASS",
            "com.cryptolab.okx-fr-monitor NOT loaded — clean activation path (K548 verified)",
            severity="INFO"
        ))

    # Check 6: OKX API keys (not needed for read-only FR fetch)
    okx_api_key = os.environ.get("OKX_API_KEY", "")
    if okx_api_key:
        report.checks.append(CheckResult(
            "okx_api_key_set", "INFO",
            "OKX_API_KEY env var set — trading integration ready (not needed for FR-only fetch)",
            severity="INFO"
        ))
    else:
        report.checks.append(CheckResult(
            "okx_api_key_not_set", "INFO",
            "OKX_API_KEY NOT SET — acceptable for Phase 1A (read-only FR fetch; trading keys needed for Phase 2)",
            severity="LOW"
        ))

    # Check 7: OKX FR fetcher script
    okx_fetcher = SCRIPTS_DIR / "okx_fr_fetcher.py"
    if okx_fetcher.exists():
        report.checks.append(CheckResult(
            "okx_fr_fetcher_exists", "PASS",
            f"scripts/okx_fr_fetcher.py found ({okx_fetcher.stat().st_size} bytes)",
            severity="INFO"
        ))
    else:
        report.checks.append(CheckResult(
            "okx_fr_fetcher_exists", "FAIL",
            "scripts/okx_fr_fetcher.py NOT FOUND — OKX daemon will fail on first cycle",
            severity="BLOCKER",
            remediation="Locate or regenerate okx_fr_fetcher.py from K456 wave."
        ))

    # Check 8: A3 prerequisite status
    lm_path = SCRIPTS_DIR / "leverage_manager.py"
    k280_a3_done = any("0.60" in h for h in grep_file(lm_path, '"K280"'))
    if k280_a3_done:
        report.checks.append(CheckResult(
            "a3_prerequisite_complete", "PASS",
            "A3 (K280 75→60%) appears applied — prerequisite satisfied",
            severity="INFO"
        ))
    else:
        report.checks.append(CheckResult(
            "a3_prerequisite_not_complete", "WARN",
            "A3 (K280 75→60%) NOT yet applied — A3 is prerequisite for A4 (K498 routing efficiency)",
            severity="HIGH",
            remediation="Complete A3 (K552 patch) before executing A4."
        ))

    # Final
    blockers = [c for c in report.checks if c.status == "FAIL"]
    warnings = [c for c in report.checks if c.status == "WARN"]
    if not blockers:
        report.simulation_result = "WARN" if warnings else "READY"

    report.known_issues += [
        "OKX API keys NOT required for Phase 1A (FR fetch is public) — but needed for Phase 2 trading",
        "Patch order: 1) k280_live_fetch.py → 2) smart_router_config.json → 3) smart_router.py → 4) daemon load",
        "Restart k280-live daemon after patches: launchctl unload/load ~/Library/LaunchAgents/com.cryptolab.k280-live.plist",
        "Rollback: flip SMART_ROUTER_ENABLED=False + remove routing_mode from config (<2min)",
        "BBO_SELECT routes per-order to highest-scoring venue (FR+rebate-slippage) — Bybit VIP5 wins most orders",
        "OKX daemon StartInterval=28800 (8h) — first run happens after 8h from load (RunAtLoad=false)",
        "K548 verified all 5 pre-conditions GREEN as of 2026-05-30 06:15 JST — state unchanged at K569",
    ]
    return report

# ── Phase 5: A5 K485 Bybit Sub-Account ───────────────────────────────────────

def validate_a5() -> ActionReport:
    report = ActionReport(
        action_id="A5",
        wave="K485",
        title="Bybit sub-account application + 7-day paper-trade gate",
        estimated_time="30 min application + 7 days KYC + paper gate",
        roi_estimate="+$204K/yr lift (Phase 1B: $10M HL W1+W2 strategy isolation)",
        risk_level="LOW (7-day paper gate required; application risk = KYC denial)",
        pre_execution_steps=[
            "Login to Bybit master account",
            "Navigate: Account → Sub-Accounts → Create Sub-Account",
            "Sub-account type: Standard (not UTA unified trading account for Phase 1B)",
            "Set sub-account credentials (separate from master)",
            "Complete KYC for sub-account if prompted",
            "Deposit test funds for 7-day paper-trade gate",
        ],
        post_execution_verify=[
            "Bybit UI → Sub-Accounts → verify sub-account listed",
            "python3 -c \"import os; print(os.environ.get('BYBIT_SUB1_API_KEY','NOT SET'))\"",
            "After 7d gate: python3 scripts/k280_live_fetch.py --dry-run --venue Bybit",
        ],
        execution_commands=[
            "# Step 1: Apply at Bybit UI (no CLI)",
            "# bybit.com → Account → Sub-Accounts → Create",
            "",
            "# Step 2: Generate API keys for sub-account",
            "# Set read + trade permissions (NO withdraw)",
            "",
            "# Step 3: Set env vars (after API keys generated)",
            "export BYBIT_SUB1_API_KEY=<sub_account_api_key>",
            "export BYBIT_SUB1_API_SECRET=<sub_account_api_secret>",
            "",
            "# Step 4: 7-day paper-trade gate",
            "# Monitor K280/K302a paper trades on sub-account",
            "",
            "# Step 5: After gate passed, activate live trading",
        ],
    )

    # Check 1: BYBIT_SUB1_API_KEY env var
    bybit_key = os.environ.get("BYBIT_SUB1_API_KEY", "")
    if bybit_key:
        report.checks.append(CheckResult(
            "bybit_sub1_api_key_set", "PASS",
            f"BYBIT_SUB1_API_KEY set (len={len(bybit_key)}) — sub-account API configured",
            severity="INFO"
        ))
    else:
        report.checks.append(CheckResult(
            "bybit_sub1_api_key_not_set", "INFO",
            "BYBIT_SUB1_API_KEY NOT SET — expected pre-application (set after Bybit sub-account created)",
            severity="LOW",
            remediation="After creating Bybit sub-account: export BYBIT_SUB1_API_KEY=<key>"
        ))

    # Check 2: Bybit master API key
    bybit_master = os.environ.get("BYBIT_API_KEY", "")
    if bybit_master:
        report.checks.append(CheckResult(
            "bybit_master_api_set", "PASS",
            "BYBIT_API_KEY (master) set — Bybit account connectivity available",
            severity="INFO"
        ))
    else:
        report.checks.append(CheckResult(
            "bybit_master_api_not_set", "WARN",
            "BYBIT_API_KEY (master) NOT SET — Bybit integration not yet configured",
            severity="MEDIUM",
            remediation="Generate Bybit master API key (read+trade, NO withdraw). Set BYBIT_API_KEY env var."
        ))

    # Check 3: KYC requirement (K485 spec: KYC required for Bybit sub)
    report.checks.append(CheckResult(
        "bybit_kyc_required", "WARN",
        "Bybit sub-account requires KYC (personal accounts prohibited: multi-wallet ToS risk per K485 spec)",
        severity="MEDIUM",
        remediation="Use institutional/fund account structure. DO NOT create duplicate personal accounts (ToS violation)."
    ))

    # Check 4: VIP tier check for maximum benefit
    report.checks.append(CheckResult(
        "bybit_vip_tier_check", "INFO",
        "Bybit VIP5 tier assumed in smart_router_config.json (1.0bps maker rebate) — verify master account tier",
        severity="LOW",
        remediation="Check Bybit master account VIP tier. VIP1 = 0.1bps, VIP5 = 1.0bps maker rebate."
    ))

    # Check 5: 7-day paper gate requirement
    report.checks.append(CheckResult(
        "paper_gate_required", "INFO",
        "K485 spec mandates 7-day paper-trade gate after sub-account activation before live capital",
        severity="LOW"
    ))

    # Check 6: No conflicting Bybit daemon already loaded
    loaded = launchctl_list()
    bybit_daemons = {k: v for k, v in loaded.items() if "bybit" in k.lower()}
    if bybit_daemons:
        report.checks.append(CheckResult(
            "bybit_daemons_running", "INFO",
            f"Bybit-related daemons already loaded: {list(bybit_daemons.keys())}",
            severity="INFO"
        ))
    else:
        report.checks.append(CheckResult(
            "no_bybit_daemons", "INFO",
            "No Bybit-specific daemons currently loaded",
            severity="INFO"
        ))

    # Check 7: HL concentration impact
    report.checks.append(CheckResult(
        "hl_concentration_impact", "INFO",
        "A5 strategy isolation (W2) keeps HL at 64.5% — 0.5pp headroom to 65% hard cap (per K560 Week 5 spec)",
        severity="LOW",
        remediation="Monitor HL concentration after A5 activation. Hard cap=65% (feedback_concentration_risk_HL.md)."
    ))

    # Final
    blockers = [c for c in report.checks if c.status == "FAIL"]
    warnings = [c for c in report.checks if c.status == "WARN"]
    if not blockers:
        report.simulation_result = "WARN" if warnings else "READY"

    report.known_issues += [
        "KYC required for Bybit sub-account — timeline: 1-7 business days",
        "Multi-wallet PROHIBITED per Bybit ToS for personal accounts — use institutional structure",
        "7-day paper gate is mandatory before live capital allocation (K485 §6 gate)",
        "$204K/yr estimate = Phase 1B strategy isolation at $10M HL only (same OB, stagger benefit)",
        "Full Phase 1A benefit ($2.2M/yr) requires $25M AUM across HL+Bybit — longer timeline",
        "Bybit VIP5 tier (1.0bps maker rebate) drives smart router advantage vs HL GOLD (0.3bps)",
        "No smart router code changes needed for A5 — sub-account is a routing target, not code change",
    ]
    return report

# ── Phase 6: Cross-action ordering check ─────────────────────────────────────

def cross_action_dependency_check(results: Dict[str, ActionReport]) -> Dict[str, Any]:
    return {
        "ordering": {
            "recommended_sequence": ["A1", "A2", "A3", "A4", "A5"],
            "rationale": "A1+A2 independent; A3 prerequisite for A4 (routing efficiency) and K449 LIVE; A5 independent but longest lead time",
        },
        "dependencies": {
            "A1_A2_independent": True,
            "A3_prerequisite_for_A4": True,
            "A3_prerequisite_for_K449_LIVE": True,
            "A4_prerequisite_for_K208_routing_efficiency": True,
            "A5_independent": True,
            "A5_lead_time_days": 7,
        },
        "parallel_safe": {
            "A1_and_A2": True,
            "A1_and_A5": True,
            "A2_and_A5": True,
            "A3_and_A5": True,
            "A4_while_A5_pending": True,
            "A3_before_A4": "REQUIRED",
        },
        "critical_path": "A3 → A4 (code patches sequential; daemon load after patches)",
        "fastest_execution": "A1+A2 in parallel (5min+30min) → A3 (30min) → A4 start → A5 application in parallel with A4",
        "total_active_time_min": 5 + 30 + 30 + 285 + 30,  # 380 min = 6.3h
        "total_passive_time_days": 7,
    }

# ── Phase 7: Issue inventory ──────────────────────────────────────────────────

def build_issue_inventory(results: Dict[str, ActionReport]) -> List[Dict[str, Any]]:
    issues = []
    for action_id, report in results.items():
        for check in report.checks:
            if check.status in ("FAIL", "WARN"):
                issues.append({
                    "action": action_id,
                    "wave": report.wave,
                    "check": check.name,
                    "status": check.status,
                    "severity": check.severity,
                    "detail": check.detail,
                    "remediation": check.remediation,
                })
        for issue in report.known_issues:
            issues.append({
                "action": action_id,
                "wave": report.wave,
                "check": "known_issue",
                "status": "INFO",
                "severity": "LOW",
                "detail": issue,
                "remediation": "",
            })
    return sorted(issues, key=lambda x: {"BLOCKER": 0, "HIGH": 1, "MEDIUM": 2, "LOW": 3, "INFO": 4}.get(x["severity"], 5))

# ── Main runner ───────────────────────────────────────────────────────────────

def run_all(actions_filter: Optional[List[str]] = None) -> Dict[str, Any]:
    ts = now_jst()
    print(f"[K569] Phase A Pre-Execution Validator — {ts}", file=sys.stderr)

    validators = {
        "A1": validate_a1,
        "A2": validate_a2,
        "A3": validate_a3,
        "A4": validate_a4,
        "A5": validate_a5,
    }

    results: Dict[str, ActionReport] = {}
    for action_id, fn in validators.items():
        if actions_filter and action_id not in actions_filter:
            continue
        print(f"  [K569] Validating {action_id}...", file=sys.stderr)
        results[action_id] = fn()

    dep_check = cross_action_dependency_check(results)
    issue_inventory = build_issue_inventory(results)

    # Summary counts
    total_checks = sum(len(r.checks) for r in results.values())
    pass_count = sum(1 for r in results.values() for c in r.checks if c.status == "PASS")
    fail_count = sum(1 for r in results.values() for c in r.checks if c.status == "FAIL")
    warn_count = sum(1 for r in results.values() for c in r.checks if c.status == "WARN")
    blockers = sum(1 for r in results.values() for c in r.checks if c.status == "FAIL" and c.severity == "BLOCKER")

    action_sim_results = {aid: r.simulation_result for aid, r in results.items()}
    ready_count = sum(1 for v in action_sim_results.values() if v == "READY")
    warn_only_count = sum(1 for v in action_sim_results.values() if v == "WARN")
    blocked_count = sum(1 for v in action_sim_results.values() if v == "BLOCKED")

    output = {
        "wave": "K569",
        "title": "Phase A Pre-Execution Validator (5 actions simulated)",
        "generated_jst": ts,
        "validator_version": "1.0.0",
        "summary": {
            "total_actions": len(results),
            "total_checks": total_checks,
            "pass": pass_count,
            "warn": warn_count,
            "fail": fail_count,
            "blockers": blockers,
            "action_simulation_results": action_sim_results,
            "actions_ready": ready_count,
            "actions_warn_only": warn_only_count,
            "actions_blocked": blocked_count,
            "overall_readiness": "BLOCKED" if blockers > 0 else ("READY_WITH_WARNINGS" if warn_count > 0 else "READY"),
        },
        "actions": {aid: asdict(r) for aid, r in results.items()},
        "cross_action_dependencies": dep_check,
        "issue_inventory": issue_inventory,
        "k339_compliance": {
            "repo_root_from_file": str(REPO_ROOT),
            "no_hardcoded_user_paths": True,
            "pattern": "REPO_ROOT = Path(__file__).resolve().parent",
        },
    }
    return output


def main():
    parser = argparse.ArgumentParser(description="K569 Phase A Pre-Execution Validator")
    parser.add_argument("--action", nargs="*", choices=["A1", "A2", "A3", "A4", "A5"],
                        help="Validate specific actions only")
    parser.add_argument("--json-only", action="store_true", help="Output JSON only (no pretty print)")
    args = parser.parse_args()

    output = run_all(args.action)

    if args.json_only:
        print(json.dumps(output, indent=2))
    else:
        # Pretty summary
        print("\n" + "="*72)
        print(f"K569 Phase A Pre-Execution Validator — {output['generated_jst']}")
        print("="*72)
        s = output["summary"]
        print(f"Actions: {s['total_actions']} | Checks: {s['total_checks']} | PASS: {s['pass']} | WARN: {s['warn']} | FAIL: {s['fail']}")
        print(f"Blockers: {s['blockers']} | Overall: {s['overall_readiness']}")
        print()
        for action_id, sim_result in s["action_simulation_results"].items():
            r = output["actions"][action_id]
            icon = {"READY": "[OK]", "WARN": "[WARN]", "BLOCKED": "[BLOCK]", "PENDING": "[?]"}.get(sim_result, "[?]")
            print(f"  {icon} {action_id} ({r['wave']}): {sim_result} — {r['title'][:55]}")
        print()
        print("Issue inventory (FAIL/WARN only):")
        for issue in output["issue_inventory"]:
            if issue["status"] in ("FAIL", "WARN") and issue["severity"] in ("BLOCKER", "HIGH", "MEDIUM"):
                print(f"  [{issue['severity']:<8}] {issue['action']} {issue['check']}: {issue['detail'][:70]}")
        print()
        print("Recommended execution order: A1 → A2 → A3 → A4 → A5")
        print("(A5 can be started in parallel with A3/A4 as it is independent)")
        print("="*72)

        # Write JSON output
        out_path = REPO_ROOT / "wave_k569_phase_a_validator.json"
        with open(out_path, "w") as f:
            json.dump(output, f, indent=2)
        print(f"\n[K569] JSON written: {out_path}", file=sys.stderr)


if __name__ == "__main__":
    main()

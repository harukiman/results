#!/usr/bin/env python3
"""
wave_k561_phase_a_consolidated.py — Phase A Day 0 Consolidated Action Sheet
=============================================================================
K561: Consolidates 5 immediately-executable user actions from K481, K485, K530,
K545, K552 into a single structured sheet.

Mission: User-readable Day 0 execution guide with paste-ready commands,
         ROI quantification, sequencing logic, and realization tracking.

K339 Security: REPO_ROOT from __file__, no /Users/ literals.

Usage:
  python3 wave_k561_phase_a_consolidated.py             # full report
  python3 wave_k561_phase_a_consolidated.py --status    # current status check
  python3 wave_k561_phase_a_consolidated.py --preflight # pre-flight checks only
  python3 wave_k561_phase_a_consolidated.py --summary   # concise 5-row table

Deliverables:
  wave_k561_phase_a_consolidated.py   — this script (K339 pattern)
  wave_k561_phase_a_consolidated.json — 5 actions structured
  wave_k561_phase_a_consolidated.md   — Day 0 user-actionable sheet
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Tuple

# ── K339 Security: REPO_ROOT from __file__, no /Users/ literals ──────────────
REPO_ROOT   = Path(__file__).resolve().parent
SCRIPTS     = REPO_ROOT / "scripts"
DATA        = REPO_ROOT / "data"
DOCS        = REPO_ROOT / "docs"
LAUNCH      = Path.home() / "Library" / "LaunchAgents"

# Output files
OUT_JSON    = REPO_ROOT / "wave_k561_phase_a_consolidated.json"
OUT_MD      = REPO_ROOT / "wave_k561_phase_a_consolidated.md"
REPORT_HTML = REPO_ROOT / "report.html"

JST = timezone(timedelta(hours=9))
WAVE = "K561"


# ─────────────────────────────────────────────────────────────────────────────
# Action Definitions
# ─────────────────────────────────────────────────────────────────────────────

ACTIONS: List[Dict] = [
    {
        "id": "A1",
        "seq": 1,
        "wave_ref": "K545",
        "label": "Tax Harvester Plist Load",
        "goal": "Load loss-harvester daemon (18th daemon) — annual Dec 28 trigger, zero trading risk",
        "effort": "5 min",
        "effort_minutes": 5,
        "risk": "ZERO",
        "roi_label": "+$47,300/yr @$10M (Japan 55%) | +$18,920/yr (Korea 22%)",
        "roi_10m_jpn": 47300,
        "roi_10m_kor": 18920,
        "status": "READY-TO-APPLY",
        "source_file": "wave_k545_tax_harvester_activation.md",
        "verify_cmd": "launchctl list | grep loss-harvester",
        "notes": "RunAtLoad=false — NO immediate execution. Fires Dec 28 annually only.",
    },
    {
        "id": "A2",
        "seq": 2,
        "wave_ref": "K481",
        "label": "HL Builder Rebate Registration",
        "goal": "Register HL self-builder (approveBuilderFee, f=0) — referral pool bonus, ZERO extra cost",
        "effort": "30 min",
        "effort_minutes": 30,
        "risk": "ZERO",
        "roi_label": "+$99K–$496K/yr @$10M | Mid: +$248K/yr @$10M",
        "roi_10m_conservative": 99166,
        "roi_10m_mid": 247915,
        "roi_10m_optimistic": 495830,
        "roi_per_hour": 495830,
        "status": "READY-TO-APPLY",
        "source_file": "wave_k481_builder_rebate_activation.md",
        "verify_cmd": "echo $HL_BUILDER_CODE",
        "notes": "Must sign approveBuilderFee with MAIN wallet (not API/agent wallet). 6-LOC code patch required.",
    },
    {
        "id": "A3",
        "seq": 3,
        "wave_ref": "K552",
        "label": "K280 Sleeve 75→60% Production Patch",
        "goal": "Reduce K280 weight 0.75→0.60 in 3 files — unlocks K376 ($247K/yr) + K449 ($13K+) cascade",
        "effort": "30 min",
        "effort_minutes": 30,
        "risk": "LOW",
        "roi_label": "+$260K+/yr unlock via K376+K449 (30-day pipeline) | Full cascade: +$1.163M/yr",
        "roi_30d_unlock": 260000,
        "roi_full_cascade": 1163000,
        "status": "READY-TO-APPLY",
        "source_file": "wave_k552_k280_patch.md",
        "verify_cmd": "grep -n '\"K280\".*0\\.' scripts/leverage_manager.py data/portfolio_aum_state.json scripts/portfolio_aum_manager.py",
        "notes": "PREREQUISITE for K376 + K449. Patch 3 files atomically. Daemon restart required. Backup first.",
    },
    {
        "id": "A4",
        "seq": 4,
        "wave_ref": "K498/K530",
        "label": "K498 Phase 1A OKX BBO_SELECT Routing",
        "goal": "Switch smart router from HL_OVERFLOW to BBO_SELECT — Bybit 1.0bps > HL 0.3bps rebate captured",
        "effort": "8h (4.75h active + 24h paper observation)",
        "effort_active_hours": 4.75,
        "risk": "LOW",
        "roi_label": "+$121K/yr @$30M | +$1.03M/yr @$100M | Rollback < 5 min",
        "roi_30m": 121000,
        "roi_100m": 1030000,
        "roi_per_hour": 15125,
        "status": "READY-TO-APPLY (K548 verified all pre-conditions PASS)",
        "source_file": "wave_k530_k498_phase_1a_playbook.md",
        "verify_cmd": "grep SMART_ROUTER_ENABLED scripts/k280_live_fetch.py && launchctl list | grep okx-fr-monitor",
        "notes": "Requires OKX API key. Can defer 1-2 days. 48h paper gate before live flip.",
    },
    {
        "id": "A5",
        "seq": 5,
        "wave_ref": "K485",
        "label": "Bybit Sub-Account Phase 1A Application",
        "goal": "Create Bybit sub-account + API — 7d paper gate then +$2.2M/yr @$25M capacity unlock",
        "effort": "30 min setup + 7d paper gate",
        "effort_minutes": 30,
        "gate_days": 7,
        "risk": "LOW",
        "roi_label": "+$2.2M/yr @$25M total AUM (+106% vs $10M single-HL baseline)",
        "roi_25m": 2200000,
        "status": "READY-TO-APPLY",
        "source_file": "wave_k485_multi_account_scaling.md",
        "verify_cmd": "python3 -c \"import os; print('BYBIT_SUB1_API_KEY:', 'SET' if os.environ.get('BYBIT_SUB1_API_KEY') else 'NOT SET')\"",
        "notes": "Bybit sub-accounts explicitly permitted by ToS (not duplicate personal account). No capital transfer until 7d gate passes.",
    },
]

PHASE_A_SUMMARY = {
    "total_actions": 5,
    "active_effort": "1.5 hours",
    "monitoring": "1-2 days + 7d Bybit gate",
    "immediate_lift_10m": "$95K/yr (K481 $99K + K545 $47K net; K552 defensive prerequisite)",
    "full_activation_30m": "$2.5-3M/yr (all 5 activated, Bybit Phase 1A live)",
    "profit_realization": {
        "D0": "K545 daemon loaded, K481 registered, K552 patch applied",
        "D7": "K498 routing live (paper gate passed), K481 first rebate visible",
        "D14": "K485 Bybit 7d gate complete → capital transfer decision",
        "D21+": "K485 Bybit sub live → +$2.2M/yr unlock begins",
    },
}

PREFLIGHT_CHECKS = [
    {
        "label": "HL wallet funded",
        "check": "HL account has >=100 USDC perps balance",
        "required_for": ["A2"],
        "command": "# Check at https://app.hyperliquid.xyz/ — account balance section",
    },
    {
        "label": "Main wallet accessible",
        "check": "MetaMask or hardware wallet accessible (NOT the API/agent key)",
        "required_for": ["A2"],
        "command": "# Open MetaMask — ensure main HL wallet (not API wallet) is available",
    },
    {
        "label": "Bybit VIP tier",
        "check": "Bybit master account KYC verified + sub-account feature enabled",
        "required_for": ["A5"],
        "command": "# Check Bybit: Account & Security -> Sub Accounts menu visible",
    },
    {
        "label": "LaunchAgents writable",
        "check": "~/Library/LaunchAgents/ directory writable",
        "required_for": ["A1", "A4"],
        "command": "ls ~/Library/LaunchAgents/ 2>&1 | head -3",
    },
    {
        "label": "Git working tree clean",
        "check": "No uncommitted changes in REPO_ROOT (for K552 patch audit trail)",
        "required_for": ["A3"],
        "command": "git -C $(python3 -c \"from pathlib import Path; print(Path('wave_k561_phase_a_consolidated.py').resolve().parent)\") status --short",
    },
    {
        "label": "OKX API key",
        "check": "OKX_API_KEY, OKX_API_SECRET, OKX_PASSPHRASE set (A4 only, deferrable)",
        "required_for": ["A4"],
        "command": "python3 -c \"import os; print('OKX_API_KEY:', 'SET' if os.environ.get('OKX_API_KEY') else 'NOT SET — defer A4 until configured')\"",
    },
    {
        "label": "Loss harvester plist present",
        "check": "com.cryptolab.loss-harvester.plist in REPO_ROOT",
        "required_for": ["A1"],
        "command": "ls com.cryptolab.loss-harvester.plist",
    },
    {
        "label": "Leverage manager target line",
        "check": "K280 weight 0.75 present in leverage_manager.py (not yet patched)",
        "required_for": ["A3"],
        "command": "grep -n '\"K280\".*0.75' scripts/leverage_manager.py | head -3",
    },
]


# ─────────────────────────────────────────────────────────────────────────────
# Status Checks
# ─────────────────────────────────────────────────────────────────────────────

def check_a1_status() -> Tuple[str, str]:
    """Check K545 tax harvester deployment status."""
    plist_repo = REPO_ROOT / "com.cryptolab.loss-harvester.plist"
    plist_la = LAUNCH / "com.cryptolab.loss-harvester.plist"
    if not plist_repo.exists():
        return "MISSING", "com.cryptolab.loss-harvester.plist not in REPO_ROOT"
    if plist_la.exists():
        return "DEPLOYED", "Plist in ~/Library/LaunchAgents/ (launchctl load status unknown from script)"
    return "READY", "Plist in REPO_ROOT, not yet loaded into LaunchAgents"


def check_a2_status() -> Tuple[str, str]:
    """Check K481 builder rebate env var status."""
    builder_code = os.environ.get("HL_BUILDER_CODE", "").strip()
    if builder_code and builder_code.startswith("0x"):
        return "ACTIVE", f"HL_BUILDER_CODE set ({builder_code[:6]}...{builder_code[-4:]})"
    if builder_code:
        return "PARTIAL", f"HL_BUILDER_CODE set but unexpected format: {builder_code[:10]}..."
    return "PENDING", "HL_BUILDER_CODE not set — registration required"


def check_a3_status() -> Tuple[str, str]:
    """Check K552 K280 patch status across 3 files."""
    results = []
    targets = [
        SCRIPTS / "leverage_manager.py",
        DATA / "portfolio_aum_state.json",
        SCRIPTS / "portfolio_aum_manager.py",
    ]
    for f in targets:
        if not f.exists():
            results.append(f"MISSING:{f.name}")
            continue
        text = f.read_text(errors="replace")
        if '"K280":   0.60' in text or '"K280": 0.6' in text or '"K280":       0.60' in text:
            results.append(f"PATCHED:{f.name}")
        elif '"K280":   0.75' in text or '"K280": 0.75' in text or '"K280":       0.75' in text:
            results.append(f"UNPATCHED:{f.name}")
        else:
            results.append(f"UNKNOWN:{f.name}")

    patched = sum(1 for r in results if r.startswith("PATCHED"))
    if patched == 3:
        return "APPLIED", "All 3 files show K280=0.60"
    if patched > 0:
        return "PARTIAL", f"Partially applied ({patched}/3): {results}"
    return "PENDING", f"Not yet applied — all files still at 0.75"


def check_a4_status() -> Tuple[str, str]:
    """Check K498 smart router flag status."""
    fetch_script = SCRIPTS / "k280_live_fetch.py"
    config_file = DATA / "smart_router_config.json"

    if not fetch_script.exists():
        return "MISSING", "scripts/k280_live_fetch.py not found"

    text = fetch_script.read_text(errors="replace")
    if "SMART_ROUTER_ENABLED = True" in text:
        return "ACTIVE", "SMART_ROUTER_ENABLED = True in k280_live_fetch.py"

    okx_key = os.environ.get("OKX_API_KEY", "").strip()
    if not okx_key:
        return "BLOCKED", "OKX_API_KEY not set — required before activation"

    if not config_file.exists():
        return "READY", "SMART_ROUTER_ENABLED = False (pre-patch); OKX key set; config missing"

    return "READY", "SMART_ROUTER_ENABLED = False (pre-patch); apply K530 14-LOC patch"


def check_a5_status() -> Tuple[str, str]:
    """Check K485 Bybit sub-account env var status."""
    key = os.environ.get("BYBIT_SUB1_API_KEY", "").strip()
    secret = os.environ.get("BYBIT_SUB1_SECRET", "").strip()
    if key and secret:
        return "CONFIGURED", "BYBIT_SUB1_API_KEY and BYBIT_SUB1_SECRET set"
    if key:
        return "PARTIAL", "BYBIT_SUB1_API_KEY set but BYBIT_SUB1_SECRET missing"
    return "PENDING", "BYBIT_SUB1_API_KEY not set — sub-account application required"


STATUS_CHECKS = {
    "A1": check_a1_status,
    "A2": check_a2_status,
    "A3": check_a3_status,
    "A4": check_a4_status,
    "A5": check_a5_status,
}


# ─────────────────────────────────────────────────────────────────────────────
# CLI Modes
# ─────────────────────────────────────────────────────────────────────────────

def print_summary_table() -> None:
    """Print concise 5-row action table."""
    now_jst = datetime.now(JST).strftime("%Y-%m-%d %H:%M JST")
    print(f"\n{'='*90}")
    print(f"  K561 Phase A — Day 0 Consolidated Actions  |  {now_jst}")
    print(f"{'='*90}")
    print(f"  {'ID':<4} {'Label':<38} {'Time':<16} {'ROI @$10M':<22} {'Risk':<8} {'Status'}")
    print(f"  {'-'*4} {'-'*38} {'-'*16} {'-'*22} {'-'*8} {'-'*12}")

    for a in ACTIONS:
        status_fn = STATUS_CHECKS.get(a["id"])
        status_str = "?"
        if status_fn:
            state, _ = status_fn()
            status_str = state

        roi = a.get("roi_label", "").split("|")[0].strip()[:22]
        print(f"  {a['id']:<4} {a['label']:<38} {a['effort']:<16} {roi:<22} {a['risk']:<8} {status_str}")

    print(f"\n  Phase A Total: 5 actions | 1.5h active | +$95K immediate | +$2.5-3M/yr full activation")
    print(f"{'='*90}\n")


def print_status_check() -> None:
    """Print current status of all 5 actions."""
    now_jst = datetime.now(JST).strftime("%Y-%m-%d %H:%M JST")
    print(f"\n[K561 STATUS CHECK — {now_jst}]")
    all_ready = True
    for a in ACTIONS:
        fn = STATUS_CHECKS.get(a["id"])
        if fn:
            state, detail = fn()
        else:
            state, detail = "UNKNOWN", "No check defined"
        icon = "✓" if state in ("ACTIVE", "DEPLOYED", "APPLIED", "CONFIGURED") else \
               "~" if state in ("PARTIAL", "READY", "CONFIGURED") else "✗"
        print(f"  {icon} {a['id']} [{state:<12}] {a['label']}: {detail}")
        if state not in ("ACTIVE", "DEPLOYED", "APPLIED", "CONFIGURED"):
            all_ready = False

    if all_ready:
        print("\n  ALL 5 ACTIONS COMPLETE — Phase A fully deployed.")
    else:
        print("\n  Phase A has pending actions. Run with --summary for next steps.")
    print()


def print_preflight() -> None:
    """Print pre-flight checklist."""
    now_jst = datetime.now(JST).strftime("%Y-%m-%d %H:%M JST")
    print(f"\n[K561 PRE-FLIGHT CHECKS — {now_jst}]")
    print(f"{'─'*70}")
    for chk in PREFLIGHT_CHECKS:
        actions_str = "+".join(chk["required_for"])
        print(f"\n  [{actions_str}] {chk['label']}")
        print(f"  Condition: {chk['check']}")
        print(f"  Command:   {chk['command']}")
    print(f"\n{'─'*70}\n")


def print_full_report() -> None:
    """Print full Phase A action report."""
    now_jst = datetime.now(JST).strftime("%Y-%m-%d %H:%M JST")
    print(f"\n{'='*90}")
    print(f"  K561 — PHASE A DAY 0 CONSOLIDATED SHEET")
    print(f"  Generated: {now_jst} | Pattern: K339 | Status: READY-TO-APPLY")
    print(f"{'='*90}")

    print(f"\n  SUMMARY")
    print(f"  Actions: 5 | Active effort: ~1.5 hours | Monitoring: 1-2 days + 7d gate")
    print(f"  Immediate lift @$10M: ~$95K/yr (K481 + K545)")
    print(f"  Full Phase A @$30M (all 5 active): +$2.5-3M/yr")

    print(f"\n  RECOMMENDED SEQUENCE")
    print(f"  1. A1 K545 (5 min, ZERO risk) — then")
    print(f"  2. A2 K481 (30 min, ZERO risk) — then")
    print(f"  3. A3 K552 (30 min, LOW risk)  — then")
    print(f"  4. A4 K498 (8h block, LOW risk; defer 1-2d if OKX key not ready)")
    print(f"  5. A5 K485 (30 min application; 7d gate runs concurrently)")
    print(f"  Total D0 active: ~1.5 hours | A4 can be deferred to D1-D2")

    print(f"\n  PROFIT PROJECTION")
    print(f"  @$10M D0:  K481 $99K-$496K/yr (conservative-optimistic)")
    print(f"             K545 $47K/yr (Japan 55%) — first Dec 28")
    print(f"             K552 prerequisite (unlocks $260K cascade within 30d)")
    print(f"  @$30M D14: K498 +$121K/yr (after 48h paper gate)")
    print(f"  @$25M D21+: K485 +$2.2M/yr (after Bybit 7d gate)")
    print(f"  Full Phase A net: +$2.5-3M/yr at full activation")

    print(f"\n  ACTIONS DETAIL")
    print(f"  {'─'*86}")
    for a in ACTIONS:
        print(f"\n  [{a['id']}] {a['label']}  |  {a['effort']}  |  Risk: {a['risk']}")
        print(f"  Goal: {a['goal']}")
        print(f"  ROI:  {a['roi_label']}")
        print(f"  Verify: {a['verify_cmd']}")
        print(f"  Source: {a['source_file']}")
        if a.get("notes"):
            print(f"  Note:  {a['notes']}")

    print(f"\n  REALIZATION TRACKING")
    for milestone, details in PHASE_A_SUMMARY["profit_realization"].items():
        print(f"  {milestone}: {details}")

    print(f"\n  RISK SUMMARY")
    risks = {
        "A1 K545": "ZERO — annual cron only, no trades",
        "A2 K481": "ZERO — additive field, no extra cost, baseline preserved if program ends",
        "A3 K552": "LOW — backup first; rollback <2 min; daemon restart required",
        "A4 K498": "LOW — concentration caps enforced; rollback <5 min (1 flag flip)",
        "A5 K485": "LOW — Bybit sub explicitly permitted; no capital until 7d gate",
    }
    for k, v in risks.items():
        print(f"  {k}: {v}")

    print(f"\n{'='*90}")
    print(f"  Source waves: K481 | K485 | K498 | K530 | K539 | K545 | K548 | K552")
    print(f"  K561 Phase A Consolidated | {now_jst}")
    print(f"{'='*90}\n")


# ─────────────────────────────────────────────────────────────────────────────
# Main
# ─────────────────────────────────────────────────────────────────────────────

def main() -> int:
    parser = argparse.ArgumentParser(
        description="K561 Phase A Consolidated Day 0 Sheet"
    )
    parser.add_argument("--status", action="store_true", help="Show current status of all 5 actions")
    parser.add_argument("--preflight", action="store_true", help="Print pre-flight checklist")
    parser.add_argument("--summary", action="store_true", help="Concise 5-row table")
    parser.add_argument("--check", action="store_true", help="Alias for --status")
    args = parser.parse_args()

    if args.summary:
        print_summary_table()
    elif args.status or args.check:
        print_status_check()
    elif args.preflight:
        print_preflight()
    else:
        # Default: full report
        print_full_report()
        print_status_check()

    return 0


if __name__ == "__main__":
    sys.exit(main())

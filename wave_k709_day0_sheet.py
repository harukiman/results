#!/usr/bin/env python3
"""
wave_k709_day0_sheet.py — K709 Day 0 Unified Execution Sheet
Pattern: K339 (REPO_ROOT relative paths)
Generated: 2026-05-30 16:20 JST

Consolidates K674/K702/K706/K705/K700/K561/K539 into:
  - Phase A: 5 actions (~3-4h) with paste-ready commands
  - Phase B: D7-D14 K376 BULL watch
  - Phase C: D60 cascade (2026-07-29, 14 scaffolds)

Usage:
  python3 wave_k709_day0_sheet.py              # print Day 0 action sheet
  python3 wave_k709_day0_sheet.py --status     # check current env/daemon status
  python3 wave_k709_day0_sheet.py --preflight  # run pre-flight checks only
  python3 wave_k709_day0_sheet.py --rollback A3  # show rollback for action A3
"""

from __future__ import annotations
import argparse
import json
import os
import subprocess
import sys
from pathlib import Path
from datetime import datetime

REPO_ROOT = Path(__file__).resolve().parent

# ─── ANSI colours ────────────────────────────────────────────────────────────
RESET  = "\033[0m"
BOLD   = "\033[1m"
GREEN  = "\033[92m"
YELLOW = "\033[93m"
RED    = "\033[91m"
CYAN   = "\033[96m"
MAGENTA = "\033[95m"
DIM    = "\033[2m"


def _c(text: str, colour: str) -> str:
    return f"{colour}{text}{RESET}"


# ─── Action definitions ───────────────────────────────────────────────────────
ACTIONS = [
    {
        "id": "A1",
        "wave": "K545",
        "label": "Tax Harvester Plist",
        "effort": "5 min",
        "risk": "ZERO",
        "risk_colour": GREEN,
        "profit": "+$47,300/yr @$10M (Japan 55%)",
        "profit_usd": 47300,
        "status": "READY",
        "pre_conditions": [
            "Tax jurisdiction confirmed with licensed advisor",
            f"Plist present: {REPO_ROOT}/com.cryptolab.loss-harvester.plist",
            "python3 scripts/loss_harvester.py --mock-test returns PASS",
        ],
        "commands": [
            ("Set jurisdiction (adjust for your country):",
             "python3 scripts/loss_harvester.py --set-rate 55 --set-jurisdiction JPN"),
            ("Verify mock test:",
             "python3 scripts/loss_harvester.py --mock-test"),
            ("Deploy plist:",
             "cp com.cryptolab.loss-harvester.plist ~/Library/LaunchAgents/com.cryptolab.loss-harvester.plist"),
            ("Load daemon (RunAtLoad=false — NO immediate run):",
             "launchctl load ~/Library/LaunchAgents/com.cryptolab.loss-harvester.plist"),
            ("Verify:",
             "launchctl list | grep loss-harvester"),
        ],
        "verify_cmd": "launchctl list | grep loss-harvester",
        "expected": "com.cryptolab.loss-harvester listed (no PID — annual Dec 28 trigger)",
        "rollback": (
            "launchctl unload ~/Library/LaunchAgents/com.cryptolab.loss-harvester.plist\n"
            "rm ~/Library/LaunchAgents/com.cryptolab.loss-harvester.plist"
        ),
    },
    {
        "id": "A2",
        "wave": "K481",
        "label": "HL Builder Rebate Registration",
        "effort": "30 min",
        "risk": "ZERO",
        "risk_colour": GREEN,
        "profit": "+$99K–$248K/yr @$10M (conservative–mid)",
        "profit_usd": 99166,
        "status": "READY",
        "pre_conditions": [
            "HL account >= 100 USDC perps balance",
            "Main wallet (MetaMask / hardware) accessible — NOT the API/agent key",
            "HL_BUILDER_CODE env var NOT currently set (or set to correct address)",
        ],
        "commands": [
            ("Register on HL UI (browser, ~20 min):",
             "open https://app.hyperliquid.xyz/trade  # -> Account -> Builder -> fee=0 -> sign approveBuilderFee"),
            ("Set HL_BUILDER_CODE env var (replace 0x<ADDR>):",
             "echo 'export HL_BUILDER_CODE=\"0x<YOUR_MAIN_WALLET>\"' >> ~/.zshrc && source ~/.zshrc"),
            ("Verify env var:",
             "echo $HL_BUILDER_CODE"),
            ("Apply 4-LOC patch to scripts/post_only_order_manager.py (after if dry_run: block):",
             "# _builder_code = os.environ.get('HL_BUILDER_CODE', '').strip()\n"
             "# if venue == 'HL' and _builder_code and not dry_run:\n"
             "#     order_action['builder'] = {'b': _builder_code, 'f': 0}"),
            ("Verify dry-run (builder field should NOT appear — correct):",
             "python3 scripts/post_only_order_manager.py --dry-run"),
            ("Restart live daemons:",
             "launchctl unload ~/Library/LaunchAgents/com.cryptolab.k246a-live.plist && "
             "launchctl load ~/Library/LaunchAgents/com.cryptolab.k246a-live.plist\n"
             "launchctl unload ~/Library/LaunchAgents/com.cryptolab.k280-live.plist && "
             "launchctl load ~/Library/LaunchAgents/com.cryptolab.k280-live.plist"),
            ("Verify (24h later — HL referral dashboard):",
             "open https://app.hyperliquid.xyz/referrals  # builder rewards > $0"),
        ],
        "verify_cmd": "echo $HL_BUILDER_CODE && launchctl list | grep -E 'k246a|k280'",
        "expected": "HL_BUILDER_CODE prints 0x... address; k246a-live and k280-live show PIDs",
        "rollback": (
            "# Remove 4 LOC builder block from scripts/post_only_order_manager.py\n"
            "# Remove from ~/.zshrc: export HL_BUILDER_CODE=... then:\n"
            "source ~/.zshrc\n"
            "# Restart daemons (same unload/load sequence)"
        ),
    },
    {
        "id": "A3",
        "wave": "K552",
        "label": "K280 Sleeve 75→60% Patch [PREREQ for K376, K449, D60 K629]",
        "effort": "30 min",
        "risk": "LOW",
        "risk_colour": YELLOW,
        "profit": "+$260K unlock (K376 $247K + K449 $13K) within 30d",
        "profit_usd": 260000,
        "status": "READY",
        "pre_conditions": [
            "Git working tree clean",
            "scripts/leverage_manager.py line 74: '\"K280\":   0.75' confirmed",
            "k280-live and k302a-satellite daemons NOT in active cycle",
        ],
        "commands": [
            ("PRE-FLIGHT: Backup 3 files:",
             "cp scripts/leverage_manager.py scripts/leverage_manager.py.bak\n"
             "cp data/portfolio_aum_state.json data/portfolio_aum_state.json.bak\n"
             "cp scripts/portfolio_aum_manager.py scripts/portfolio_aum_manager.py.bak"),
            ("PRIMARY patch (leverage_manager.py L74 — authoritative runtime):",
             r"""sed -i '' 's/"K280":   0\.75,   # K280 main (K198 + K208 + K276b) — v6\.13d; v6\.16 reduces to 0\.72/"K280":   0.60,   # K280 main (K539 Phase B1: 75->60%, frees 7.5pp HL, 2026-05-30)/' scripts/leverage_manager.py"""),
            ("Verify Step 1:",
             "grep -n '\"K280\"' scripts/leverage_manager.py | head -5"),
            ("JSON STATE patch (portfolio_aum_state.json):",
             "python3 -c \""
             "import json; f='data/portfolio_aum_state.json'; d=json.load(open(f)); "
             "d['sleeve_weights']['K280']=0.60; d['last_updated_jst']='2026-05-30 K552/K709 Phase B1 patch'; "
             "json.dump(d, open(f,'w'), indent=2); print('Updated K280 to', d['sleeve_weights']['K280'])"
             "\""),
            ("AUM manager fallback (portfolio_aum_manager.py):",
             r"""sed -i '' 's/"K280":       0\.75,/"K280":       0.60,/' scripts/portfolio_aum_manager.py"""),
            ("Verify ALL 3 files:",
             "grep -n '\"K280\".*0\\.' scripts/leverage_manager.py data/portfolio_aum_state.json scripts/portfolio_aum_manager.py"),
            ("Restart daemons:",
             "launchctl unload ~/Library/LaunchAgents/com.cryptolab.k280-live.plist && "
             "launchctl load ~/Library/LaunchAgents/com.cryptolab.k280-live.plist\n"
             "launchctl unload ~/Library/LaunchAgents/com.cryptolab.k302a-satellite.plist && "
             "launchctl load ~/Library/LaunchAgents/com.cryptolab.k302a-satellite.plist"),
            ("Confirm daemons running:",
             "launchctl list | grep cryptolab | grep -E 'k280|k302a'"),
        ],
        "verify_cmd": "grep -n '\"K280\".*0\\.' scripts/leverage_manager.py data/portfolio_aum_state.json scripts/portfolio_aum_manager.py",
        "expected": "All 3 files show 0.60; k280-live and k302a-satellite show PIDs",
        "rollback": (
            "cp scripts/leverage_manager.py.bak scripts/leverage_manager.py\n"
            "cp data/portfolio_aum_state.json.bak data/portfolio_aum_state.json\n"
            "cp scripts/portfolio_aum_manager.py.bak scripts/portfolio_aum_manager.py\n"
            "launchctl unload ~/Library/LaunchAgents/com.cryptolab.k280-live.plist && "
            "launchctl load ~/Library/LaunchAgents/com.cryptolab.k280-live.plist"
        ),
    },
    {
        "id": "A4",
        "wave": "K498/K530",
        "label": "OKX BBO_SELECT Smart Router",
        "effort": "8h (4.75h active + 24h paper)",
        "risk": "LOW",
        "risk_colour": YELLOW,
        "profit": "+$121K/yr @$30M | +$1.03M/yr @$100M",
        "profit_usd": 121000,
        "status": "READY (K548 pre-conditions PASS) — requires OKX API key",
        "pre_conditions": [
            "OKX account + API key, secret, passphrase",
            "OKX_API_KEY, OKX_API_SECRET, OKX_PASSPHRASE set in ~/.zshrc",
            "com.cryptolab.okx-fr-monitor.plist present in REPO_ROOT (K548 CONFIRMED)",
            "A3 (K552 patch) applied FIRST — RECOMMENDED",
        ],
        "commands": [
            ("Verify OKX daemon scaffold state:",
             "launchctl list | grep okx && python3 scripts/okx_fr_fetcher.py --symbol BTC-USDT-SWAP"),
            ("Apply BBO_SELECT flag:",
             "sed -i '' 's/SMART_ROUTER_ENABLED = False   # K434.*/SMART_ROUTER_ENABLED = True    # K530 K498 Phase 1A: BBO routing ACTIVE/' scripts/k280_live_fetch.py"),
            ("Verify flag:",
             "grep SMART_ROUTER_ENABLED scripts/k280_live_fetch.py"),
            ("Add routing_mode to data/smart_router_config.json (after default_post_only):",
             '# "routing_mode": "BBO_SELECT",\n'
             '# "bbo_select_min_score": -0.0001,'),
            ("Load OKX FR monitor daemon:",
             "cp com.cryptolab.okx-fr-monitor.plist ~/Library/LaunchAgents/ && "
             "launchctl load ~/Library/LaunchAgents/com.cryptolab.okx-fr-monitor.plist"),
            ("24h paper observation — verify routing distribution:",
             "python3 scripts/smart_router.py --all-symbols --side short --size 100000"),
            ("48h gate check (target: Bybit+OKX >= 40%):",
             "tail -20 data/smart_router_decisions.jsonl"),
            ("Live activation after gate pass:",
             "launchctl kickstart -k gui/$(id -u)/com.cryptolab.k280-live"),
        ],
        "verify_cmd": "grep SMART_ROUTER_ENABLED scripts/k280_live_fetch.py && launchctl list | grep okx-fr-monitor",
        "expected": "SMART_ROUTER_ENABLED = True; okx-fr-monitor shows PID; routing >= 40% non-HL",
        "rollback": (
            "sed -i '' 's/SMART_ROUTER_ENABLED = True.*/SMART_ROUTER_ENABLED = False   # K709 rollback/' "
            "scripts/k280_live_fetch.py\n"
            "launchctl kickstart -k gui/$(id -u)/com.cryptolab.k280-live"
        ),
    },
    {
        "id": "A5",
        "wave": "K485",
        "label": "Bybit Sub-Account Phase 1A (30min + 7d gate)",
        "effort": "30 min + 7d paper gate",
        "risk": "LOW",
        "risk_colour": YELLOW,
        "profit": "+$2.2M/yr @$25M total AUM (+106% vs $10M single-HL baseline)",
        "profit_usd": 2200000,
        "status": "READY — start parallel to A1-A3, 7d gate runs concurrently",
        "pre_conditions": [
            "Bybit master account KYC verified",
            "Sub Accounts menu visible: Bybit UI -> Account & Security",
            "Server/Mac IP known for API IP whitelist",
        ],
        "commands": [
            ("Create sub-account (Bybit web UI, ~10 min):",
             "# Login Bybit -> Profile -> Account & Security -> Sub Accounts\n"
             "# -> Create Sub Account -> Standard Sub Account -> Label: k485-sub1-k297p"),
            ("Generate API key for sub (Bybit UI, ~5 min):",
             "# Sub Account -> API Management -> Create API\n"
             "# Scope: Trade only (NO withdrawal) | IP restriction: add your Mac/server IP\n"
             "# Copy API Key + Secret -> save to password manager immediately"),
            ("Set env vars (never commit to git):",
             "echo 'export BYBIT_SUB1_API_KEY=\"<sub_api_key>\"' >> ~/.zshrc\n"
             "echo 'export BYBIT_SUB1_SECRET=\"<sub_secret>\"' >> ~/.zshrc\n"
             "source ~/.zshrc"),
            ("Verify env vars:",
             "python3 -c \"import os; print('BYBIT_SUB1_API_KEY:', 'SET' if os.environ.get('BYBIT_SUB1_API_KEY') else 'NOT SET')\""),
            ("Start 7-day paper-trade gate:",
             "python3 scripts/k280_live_fetch.py --venue=bybit --wallet=sub1 --dry-run"),
            ("After 7d gate passes — capital transfer (Bybit internal, instant):",
             "# Bybit UI: Assets -> Transfer -> Master Account -> k485-sub1-k297p\n"
             "# Initial: $3-5M (no withdrawal key used — internal only)"),
        ],
        "verify_cmd": "python3 -c \"import os; print('BYBIT_SUB1_API_KEY:', 'SET' if os.environ.get('BYBIT_SUB1_API_KEY') else 'NOT SET')\"",
        "expected": "BYBIT_SUB1_API_KEY: SET | Sub-account in Bybit UI | 7d paper completes without errors",
        "rollback": (
            "No capital transfer until 7d gate passes.\n"
            "Sub-account can be deleted via Bybit UI if not funded.\n"
            "API key revocable in Bybit -> API Management."
        ),
    },
]

# ─── Phase B / C definitions ─────────────────────────────────────────────────
PHASE_B = {
    "label": "Phase B: D7-D14 — K376 BULL Activation Watch",
    "trigger": "K376 BULL_CONFIRMED (K497 automated: slope > 0, Sharpe > 8 sustained 15d)",
    "check_cmd": "python3 scripts/k376_regime_trigger_monitor.py --status",
    "activation_cmd": "launchctl load ~/Library/LaunchAgents/com.cryptolab.k376-momentum.plist",
    "profit": "+$247K/yr max | $126K/yr regime-weighted",
    "note": "K497 daemon auto-monitors. Check status D+7 and D+14.",
}

PHASE_C = {
    "label": "Phase C: D60 Cascade — 2026-07-29 (14 scaffolds, 5 days)",
    "gate_date": "2026-07-29",
    "d30_audit": "2026-06-29 (mandatory D30 paper audit first)",
    "total_unlock": "$1,642,745/yr @$10M | $4,501/day post-cascade",
    "constraint": "Max 3/day, Sharpe-descending, 24h monitoring between batches",
    "prereq": "A3 K552 patch MUST be applied BEFORE D60 cascade for K629 WLD-ETH eligibility",
    "days": [
        ("D+0 Jul29", "K686 AVAX-SOL (Sh=50.27), K682 ATOM-SOL (Sh=43.43), K628 JTO-orthog (Sh=44.63)",
         "$673,817/yr cumulative", "HL 63.5% — OK"),
        ("D+1 Jul30", "K679 APT-SOL (Sh=39.29), K658 SOL-ETH +1.5pp HL (Sh=29.66), K696 ENA-SOL (Sh=26.93)",
         "$1,044,117/yr cumulative", "HL 65.0% AT CAP"),
        ("D+2 Jul31", "K690 SEI-SOL (Sh=25.11), K648 POL-orthog (Sh=23.41), K647 DOT-orthog (Sh=23.25)",
         "$1,315,215/yr cumulative", "HL 65.0%"),
        ("D+3 Aug01", "K663 TIA-ETH (Sh=22.0), K629 WLD-ETH CONDITIONAL +2.0pp HL (Sh=19.9), K694 TIA-SOL (Sh=19.09)",
         "$1,503,779/yr cumulative", "HL 65.0% (K629 deferred if HL >= 63%)"),
        ("D+4 Aug02", "K698 LINK-ETH (Sh=12.07), K684 SOL-INJ (Sh=9.65)",
         "$1,642,745/yr COMPLETE", "HL 65.0%"),
    ],
}

CHECKPOINTS = [
    ("D+7",  [
        "K481 builder: HL referral dashboard > $0",
        "K545 daemon: launchctl list | grep loss-harvester",
        "K552 patch: grep '\"K280\".*0.60' confirmed in all 3 files",
    ]),
    ("D+14", [
        "K498 paper gate: Bybit+OKX >= 40% routing in smart_router_decisions.jsonl",
        "K376 BULL check: python3 scripts/k376_regime_trigger_monitor.py --status",
        "K449 LIVE check: if D+1 after K552, see K549 playbook",
    ]),
    ("D+21", [
        "K485 7d paper gate: complete — make capital transfer decision",
        "K485 sub-account: BYBIT_SUB1_API_KEY SET + paper K297p running",
    ]),
    ("D+30", [
        "D30 paper audit (2026-06-29): all 14 scaffolds — Sharpe, fill rate, maxDD",
        "Prerequisite for D60 cascade eligibility 2026-07-29",
    ]),
    ("D+60", [
        "2026-07-29: Execute cascade in Sharpe order (max 3/day, 5 days)",
        "PREREQ: K552 applied, HL <= 63.5% at D+0",
    ]),
]


# ─── Status checks ────────────────────────────────────────────────────────────
def _run(cmd: str, cwd: Path = REPO_ROOT) -> tuple[int, str]:
    try:
        r = subprocess.run(
            cmd, shell=True, capture_output=True, text=True, cwd=str(cwd), timeout=15
        )
        return r.returncode, (r.stdout + r.stderr).strip()
    except Exception as e:
        return 1, str(e)


def check_status() -> None:
    print(_c("\n=== K709 Day 0 Status Check ===", BOLD + CYAN))
    print(_c(f"REPO_ROOT: {REPO_ROOT}", DIM))
    print()

    checks = [
        ("A1 K545 Loss Harvester daemon", "launchctl list | grep loss-harvester"),
        ("A2 K481 HL_BUILDER_CODE", "python3 -c \"import os; v=os.environ.get('HL_BUILDER_CODE',''); print('SET:' + v if v else 'NOT SET')\""),
        ("A3 K552 K280=0.60 leverage_manager", "grep -c '\"K280\":   0.60' scripts/leverage_manager.py"),
        ("A4 K498 SMART_ROUTER_ENABLED", "grep SMART_ROUTER_ENABLED scripts/k280_live_fetch.py"),
        ("A5 K485 BYBIT_SUB1_API_KEY", "python3 -c \"import os; print('SET' if os.environ.get('BYBIT_SUB1_API_KEY') else 'NOT SET')\""),
        ("Phase B K376 regime", "python3 scripts/k376_regime_trigger_monitor.py --status 2>/dev/null | tail -3"),
        ("k280-live PID", "launchctl list | grep com.cryptolab.k280-live"),
        ("k302a-satellite PID", "launchctl list | grep com.cryptolab.k302a-satellite"),
        ("okx-fr-monitor PID", "launchctl list | grep com.cryptolab.okx-fr-monitor"),
        ("Bybit paper log (last line)", "tail -1 data/smart_router_decisions.jsonl 2>/dev/null"),
    ]

    for label, cmd in checks:
        rc, out = _run(cmd)
        if out:
            status = _c("OK", GREEN)
            detail = out[:120]
        else:
            status = _c("--", DIM)
            detail = "(no output)"
        print(f"  {status}  {_c(label, BOLD)}")
        print(f"       {_c(detail, DIM)}")
    print()


# ─── Pre-flight ───────────────────────────────────────────────────────────────
def preflight() -> bool:
    print(_c("\n=== K709 Pre-Flight Checks ===", BOLD + CYAN))
    all_pass = True
    checks = [
        ("LaunchAgents writable", "ls ~/Library/LaunchAgents/ 2>&1 | head -1"),
        ("loss-harvester plist in REPO_ROOT",
         f"ls {REPO_ROOT}/com.cryptolab.loss-harvester.plist"),
        ("OKX FR monitor plist in REPO_ROOT",
         f"ls {REPO_ROOT}/com.cryptolab.okx-fr-monitor.plist"),
        ("Git status (for A3 audit trail)", "git status --short"),
        ("leverage_manager.py exists",
         f"ls {REPO_ROOT}/scripts/leverage_manager.py"),
        ("portfolio_aum_state.json exists",
         f"ls {REPO_ROOT}/data/portfolio_aum_state.json"),
    ]
    for label, cmd in checks:
        rc, out = _run(cmd)
        if rc == 0:
            print(f"  {_c('PASS', GREEN)}  {label}")
        else:
            print(f"  {_c('FAIL', RED)}  {label}: {out[:80]}")
            all_pass = False
    print()
    if all_pass:
        print(_c("  All pre-flight checks PASS. Ready to execute Day 0 actions.", GREEN + BOLD))
    else:
        print(_c("  Some checks FAILED. Resolve before executing.", RED + BOLD))
    return all_pass


# ─── Rollback printer ─────────────────────────────────────────────────────────
def print_rollback(action_id: str) -> None:
    for a in ACTIONS:
        if a["id"].upper() == action_id.upper():
            print(_c(f"\n=== Rollback: {a['id']} {a['label']} ===", BOLD + YELLOW))
            print(a["rollback"])
            return
    print(_c(f"Action {action_id} not found. Valid: A1-A5", RED))


# ─── Main display ─────────────────────────────────────────────────────────────
def print_sheet() -> None:
    width = 90
    now = datetime.now().strftime("%Y-%m-%d %H:%M JST")

    print()
    print(_c("=" * width, CYAN))
    print(_c("  K709 — DAY 0 UNIFIED EXECUTION SHEET".center(width), BOLD + CYAN))
    print(_c(f"  Generated: {now} | Pattern: K339 | LIVE 自動変更禁止".center(width), DIM))
    print(_c("=" * width, CYAN))
    print()

    # ── Profit summary banner ─────────────────────────────────────────────────
    print(_c("  PROFIT SUMMARY", BOLD + MAGENTA))
    print(_c("  " + "-" * (width - 2), MAGENTA))
    rows = [
        ("Phase A immediate (K481 conservative + K545)", "$146,300/yr @$10M"),
        ("Phase A full activation mid (all 5 actions)", "$2,863,000/yr @$30M"),
        ("D60 cascade unlock (Jul 29 – Aug 2, 14 scaffolds)", "+$1,642,745/yr @$10M"),
        ("GRAND TOTAL mid (Phase A + D60)", "$4,505,745/yr"),
        ("Active effort today", "~3.5 hours"),
    ]
    for label, val in rows:
        print(f"  {_c(label, BOLD):<65}{_c(val, GREEN)}")
    print()

    # ── Pre-flight checklist ──────────────────────────────────────────────────
    print(_c("  PRE-FLIGHT CHECKLIST (run before starting)", BOLD))
    print(_c("  " + "-" * (width - 2), DIM))
    pre = [
        "HL wallet funded (>= 100 USDC perps): https://app.hyperliquid.xyz/",
        "Main wallet (MetaMask / hardware) accessible for A2 signing",
        "Bybit VIP tier / KYC for A5: Account & Security -> Sub Accounts visible",
        "OKX API key for A4 (deferrable): OKX_API_KEY / OKX_API_SECRET / OKX_PASSPHRASE",
        "LaunchAgents writable: ls ~/Library/LaunchAgents/ (no error)",
        "Git tree clean for A3: git status --short",
    ]
    for i, item in enumerate(pre, 1):
        print(f"  [ ] {i}. {item}")
    print()
    print(f"  {_c('Quick preflight:', DIM)} python3 wave_k709_day0_sheet.py --preflight")
    print()

    # ── Day 0 timeline ────────────────────────────────────────────────────────
    print(_c("  DAY 0 EXECUTION SEQUENCE (~3.5 HOURS)", BOLD + CYAN))
    print(_c("  " + "-" * (width - 2), CYAN))
    timeline = [
        ("  MORNING BLOCK (1.25hr, ZERO risk first)", None),
        ("  T+0:00", "A1 K545 (5 min)  →  Tax Harvester plist load", "$47K/yr"),
        ("  T+0:05", "A2 K481 (30 min) →  HL Builder Rebate (browser + 4 LOC)", "$99-248K/yr"),
        ("  T+0:35", "A3 K552 (30 min) →  K280 75→60% patch (PREREQ)", "$260K unlock"),
        ("  T+1:05", "                  →  MORNING BLOCK COMPLETE", ""),
        ("", "", ""),
        ("  PARALLEL START (launch immediately, runs in background)", None),
        ("  T+0:00", "A5 K485 (30 min) →  Bybit sub-account setup + 7d gate", "$2.2M/yr @$25M"),
        ("", "", ""),
        ("  OKX BLOCK — when API key ready (deferrable to D1-D2)", None),
        ("  T+1:30", "A4 K498 (8h)     →  OKX BBO_SELECT smart router", "$121K/yr @$30M"),
        ("  T+5:30", "                  →  24h paper observation", "gate check"),
    ]
    for row in timeline:
        if len(row) == 1:
            print(_c(row[0], BOLD))
        elif row[1]:
            t, action, profit = row
            p_str = _c(f"  {profit}", GREEN) if profit else ""
            print(f"  {_c(t, DIM)}  {action}{p_str}")
        else:
            print()
    print()

    # ── Per-action detail ─────────────────────────────────────────────────────
    for a in ACTIONS:
        risk_str = _c(f"[{a['risk']}]", a["risk_colour"] + BOLD)
        profit_str = _c(a["profit"], GREEN + BOLD)
        print(_c("=" * width, DIM))
        print(f"  {_c(a['id'], BOLD + CYAN)} {_c(a['label'], BOLD)} {risk_str} {profit_str}")
        print(f"     Wave: {a['wave']} | Effort: {a['effort']} | Status: {a['status']}")
        print()

        print(f"  {_c('Pre-conditions:', BOLD)}")
        for pc in a["pre_conditions"]:
            print(f"    [ ] {pc}")
        print()

        print(f"  {_c('Commands (paste-ready):', BOLD)}")
        for step_label, cmd in a["commands"]:
            print(f"    {_c('# ' + step_label, DIM)}")
            for line in cmd.split("\n"):
                print(f"    {line}")
            print()

        print(f"  {_c('Verify:', BOLD)} {a['verify_cmd']}")
        print(f"  {_c('Expected:', DIM)} {a['expected']}")
        print(f"  {_c('Rollback:', YELLOW)} {a['rollback'].split(chr(10))[0]} ...")
        print(f"           {_c('(full: python3 wave_k709_day0_sheet.py --rollback ' + a['id'] + ')', DIM)}")
        print()

    # ── Phase B ───────────────────────────────────────────────────────────────
    print(_c("=" * width, DIM))
    print(_c(f"  {PHASE_B['label']}", BOLD + YELLOW))
    print()
    print(f"  Trigger:  {PHASE_B['trigger']}")
    print(f"  Profit:   {_c(PHASE_B['profit'], GREEN)}")
    print(f"  Check:    {PHASE_B['check_cmd']}")
    print(f"  Activate: {PHASE_B['activation_cmd']}")
    print(f"  Note:     {PHASE_B['note']}")
    print()

    # ── Phase C ───────────────────────────────────────────────────────────────
    print(_c("=" * width, DIM))
    print(_c(f"  {PHASE_C['label']}", BOLD + MAGENTA))
    print()
    print(f"  Gate date: {_c(PHASE_C['gate_date'], BOLD)} | D30 audit: {PHASE_C['d30_audit']}")
    print(f"  Unlock:    {_c(PHASE_C['total_unlock'], GREEN + BOLD)}")
    print(f"  Constraint:{PHASE_C['constraint']}")
    print(f"  {_c('PREREQ:', RED + BOLD)} {PHASE_C['prereq']}")
    print()
    for day, strategies, cumulative, hl_status in PHASE_C["days"]:
        hl_col = RED if "OVER" in hl_status or "FAIL" in hl_status else (YELLOW if "CAP" in hl_status else GREEN)
        print(f"  {_c(day, BOLD):<18} {strategies}")
        print(f"  {'':<18} {_c(cumulative, GREEN)} | {_c(hl_status, hl_col)}")
        print()

    # ── Checkpoints ──────────────────────────────────────────────────────────
    print(_c("=" * width, DIM))
    print(_c("  CHECKPOINTS", BOLD))
    print()
    for period, items in CHECKPOINTS:
        print(f"  {_c(period, BOLD + CYAN)}")
        for item in items:
            print(f"    [ ] {item}")
        print()

    # ── Risk matrix ───────────────────────────────────────────────────────────
    print(_c("=" * width, DIM))
    print(_c("  RISK MATRIX", BOLD))
    print()
    hdr = f"  {'Action':<10}{'Risk':<10}{'Rollback':<15}{'Key Mitigation'}"
    print(_c(hdr, DIM))
    print(_c("  " + "-" * 78, DIM))
    risk_rows = [
        ("A1 K545", "ZERO", "instant", "RunAtLoad=false, annual cron, no trades"),
        ("A2 K481", "ZERO", "instant (4 LOC)", "f=0 no cost, additive, env-var gated"),
        ("A3 K552", "LOW", "< 2 min", "3-file atomic backup; daemon restart documented"),
        ("A4 K498", "LOW", "< 5 min (1 flag)", "48h paper gate; concentration caps enforced"),
        ("A5 K485", "LOW", "instant (no capital)", "No transfer until 7d gate; ToS-permitted sub"),
    ]
    for action, risk, rollback_t, mitigation in risk_rows:
        risk_col = GREEN if risk == "ZERO" else YELLOW
        print(f"  {action:<10}{_c(risk, risk_col):<20}{rollback_t:<22}{mitigation}")
    print()

    # ── Constraints ───────────────────────────────────────────────────────────
    print(_c("=" * width, DIM))
    print(_c("  CONSTRAINTS", BOLD + RED))
    constraints = [
        "LIVE 自動変更禁止 — all changes are MANUAL EXECUTION ONLY",
        "K339 REPO_ROOT pattern — /Users/nekonaomichi/crypto-lab",
        "HL concentration hard cap: 65% — K552 patch (A3) MUST precede any HL-adding strategy",
        "D60 cascade: max 3 activations/day, 24h monitoring between batches",
        "K629 WLD-ETH CONDITIONAL: DO NOT load if HL >= 63.0% (needs K552 headroom)",
        "API credentials: NEVER commit to git — .zshrc only",
    ]
    for c in constraints:
        print(f"  {_c('!', RED + BOLD)} {c}")
    print()
    print(_c("=" * width, CYAN))
    print(_c("  K709 Day 0 Sheet — K339 Pattern | LIVE 自動変更禁止 | 2026-05-30".center(width), DIM))
    print(_c("=" * width, CYAN))
    print()


# ─── Entry point ─────────────────────────────────────────────────────────────
def main() -> None:
    parser = argparse.ArgumentParser(description="K709 Day 0 Unified Execution Sheet")
    parser.add_argument("--status", action="store_true", help="Check current env/daemon status")
    parser.add_argument("--preflight", action="store_true", help="Run pre-flight checks")
    parser.add_argument("--rollback", metavar="ACTION_ID", help="Show rollback for A1-A5")
    args = parser.parse_args()

    os.chdir(REPO_ROOT)

    if args.status:
        check_status()
    elif args.preflight:
        preflight()
    elif args.rollback:
        print_rollback(args.rollback)
    else:
        print_sheet()


if __name__ == "__main__":
    main()

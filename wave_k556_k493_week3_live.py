#!/usr/bin/env python3
"""
wave_k556_k493_week3_live.py — K556 K493 ATOM-BTC Week 3 LIVE Activation Playbook
===================================================================================
Week 3 LIVE switch playbook for K493 ATOM-BTC FR Differential strategy.

K547 sequenced activation:
  Week 1: K449 ETH-BTC  ($13K/yr)          ← K549 playbook  (D0)
  Week 2: K476 SOL + K484 AVAX (+$263K/yr) ← D7-D14
  Week 3: K493 ATOM-BTC ($231K/yr)         ← THIS WAVE (D14-D21)
  Week 4: K500 INJ + K507 SEI + K507 TIA (+$354K/yr) ← D21-D35
  Week 5: K512 APT-BTC (+$302K/yr)         ← D35-D60

Family rank: K493 = #1 by OOS Sharpe (50.79).
Cosmos hypothesis: ATOM FR driven by IBC flows, staking yield competition,
governance cycles — most orthogonal alt in paired-trade family (G5a=0.1763).

LIVE 自動変更禁止 — this script is PLAYBOOK ONLY.
No orders submitted. No config files written.
All LIVE changes must be executed manually per printed checklist.

K339 security: REPO_ROOT from __file__, no /Users/ literals.
No new packages — stdlib only.

Usage:
  python3 wave_k556_k493_week3_live.py --status
  python3 wave_k556_k493_week3_live.py --phase1
  python3 wave_k556_k493_week3_live.py --phase2
  python3 wave_k556_k493_week3_live.py --phase3
  python3 wave_k556_k493_week3_live.py --phase4
  python3 wave_k556_k493_week3_live.py --phase5
  python3 wave_k556_k493_week3_live.py --all
  python3 wave_k556_k493_week3_live.py --checklist
  python3 wave_k556_k493_week3_live.py --export-json
"""
from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

# ── K339 canonical paths ──────────────────────────────────────────────────────
REPO_ROOT   = Path(__file__).resolve().parent
DATA_DIR    = REPO_ROOT / "data"
SCRIPTS_DIR = REPO_ROOT / "scripts"
LOGS_DIR    = REPO_ROOT / "logs"
DOCS_DIR    = REPO_ROOT / "docs"

# ── Wave constant ─────────────────────────────────────────────────────────────
WAVE = "K556"

# ── Key file paths (relative via REPO_ROOT) ───────────────────────────────────
K493_DASHBOARD_JSON    = DATA_DIR / "k493_dashboard.json"
K449_DASHBOARD_JSON    = DATA_DIR / "k449_dashboard.json"
K476_DASHBOARD_JSON    = DATA_DIR / "k476_dashboard.json"
K484_DASHBOARD_JSON    = DATA_DIR / "k484_dashboard.json"
K280_DASHBOARD_JSON    = DATA_DIR / "k280_live_dashboard.json"
LEVERAGE_MANAGER_PY    = SCRIPTS_DIR / "leverage_manager.py"
K493_RUN_PY            = SCRIPTS_DIR / "k493_atom_btc_run.py"
K493_PLIST             = REPO_ROOT / "com.cryptolab.k493-atom-btc.plist"
EMERGENCY_EXIT_PY      = SCRIPTS_DIR / "emergency_hl_exit.py"
SMART_ROUTER_PY        = SCRIPTS_DIR / "smart_router.py"
OUTPUT_JSON            = REPO_ROOT / "wave_k556_k493_week3_live.json"

# ── Financial constants ───────────────────────────────────────────────────────
AUM_REF_USD            = 10_000_000    # $10M reference AUM
AUM_30M_USD            = 30_000_000    # $30M scale
AUM_100M_USD           = 100_000_000   # $100M scale
K493_SLEEVE_PCT        = 0.05          # 5% initial sleeve (Week 3 D0)
K493_LEVERAGE          = 4.0           # 4x (HL-only, delta-neutral)
K493_ANN_RETURN_USD    = 231_000       # $231K/yr @ $10M OOS
K493_OOS_SHARPE        = 50.79         # OOS Sharpe (highest in family)
K493_LIVE_SHARPE_EST   = 35.55         # ~70% of OOS (slippage/fee decay)
HL_SPLIT_PCT           = 0.60          # 60% of notional on HL (3pp of sleeve)
BYBIT_SPLIT_PCT        = 0.40          # 40% on Bybit (2pp of sleeve)
HL_EXPOSURE_PRE        = 0.58          # ~58% pre-K493 (after Week 1+2)
HL_EXPOSURE_CAP        = 0.65          # 65% hard cap
HL_K493_ADD_PP         = 2.5           # +2.5pp HL (5% sleeve × 50% HL split)
HL_EXPOSURE_POST       = 0.605         # ~60.5% post-K493

# ── Cumulative profit constants ───────────────────────────────────────────────
WEEK1_K449_USD         = 13_000        # K449 ETH-BTC
WEEK2_K476_USD         = 187_000       # K476 SOL-BTC
WEEK2_K484_USD         = 76_000        # K484 AVAX-BTC
WEEK3_K493_USD         = 231_000       # K493 ATOM-BTC
CUMULATIVE_W3_USD      = 507_000       # W1+W2+W3 combined

# ── Decision thresholds ───────────────────────────────────────────────────────
PASS_SHARPE            = 25.0          # PASS → expand to 8%
HOLD_SHARPE_LOW        = 15.0          # HOLD lower bound
ROLLBACK_SHARPE        = 15.0          # < 15 → rollback to paper
PASS_FILL_RATE         = 0.65          # 65% fill rate threshold
HOLD_FILL_RATE_LOW     = 0.50          # 50% fill rate lower bound

# ── Colour helpers (ANSI, safe fallback) ─────────────────────────────────────
def _c(code: str, text: str) -> str:
    if sys.stdout.isatty():
        return f"\033[{code}m{text}\033[0m"
    return text

def bold(t: str) -> str:   return _c("1", t)
def green(t: str) -> str:  return _c("32", t)
def yellow(t: str) -> str: return _c("33", t)
def red(t: str) -> str:    return _c("31", t)
def cyan(t: str) -> str:   return _c("36", t)
def grey(t: str) -> str:   return _c("90", t)
def magenta(t: str) -> str: return _c("35", t)


# ─────────────────────────────────────────────────────────────────────────────
# Phase 1: K493 scaffold state verify + 60d paper progress
# ─────────────────────────────────────────────────────────────────────────────

def phase1_scaffold_verify() -> Dict[str, Any]:
    """Verify K493 scaffold state and 60d paper-trade progress."""
    print(bold(f"\n{'='*70}"))
    print(bold("Phase 1: K493 Scaffold State Verification"))
    print(bold(f"{'='*70}"))

    results: Dict[str, Any] = {
        "phase": 1,
        "name": "scaffold_verify",
        "checks": [],
        "all_pass": True,
    }

    def check(name: str, ok: bool, detail: str, warn_only: bool = False) -> None:
        status = "PASS" if ok else ("WARN" if warn_only else "FAIL")
        colour = green if ok else (yellow if warn_only else red)
        print(f"  {colour(f'[{status}]')} {name}: {detail}")
        results["checks"].append({"name": name, "status": status, "detail": detail})
        if not ok and not warn_only:
            results["all_pass"] = False

    # 1a. K493 dashboard JSON
    if K493_DASHBOARD_JSON.exists():
        with open(K493_DASHBOARD_JSON) as f:
            dash = json.load(f)
        paper_mode   = dash.get("paper_trade_mode", True)
        pos_state    = dash.get("position_state", "UNKNOWN")
        sleeve_pct   = dash.get("sleeve_pct", 0.0)
        sharpe_60d   = dash.get("60d_sharpe", 0.0)
        days_elapsed = dash.get("paper_trade_status", {}).get("days_elapsed", 0)
        oos_sharpe   = dash.get("oos_performance", {}).get("sharpe", 0.0)
        gate_status  = dash.get("gate_metrics", {}).get("gate_status", "UNKNOWN")
        check("k493_dashboard_json", True,
              f"EXISTS — state={pos_state}, paper={paper_mode}, sleeve={sleeve_pct:.0%}, gate={gate_status}")
        check("k493_paper_mode", paper_mode,
              "PAPER_TRADE=True (current) — must flip to False at Week 3 activation", warn_only=True)
        check("k493_oos_sharpe", oos_sharpe >= 25.0,
              f"OOS Sharpe={oos_sharpe:.2f} (target ≥25 for family #1 confidence)")
        check("k493_paper_days", days_elapsed >= 0,
              f"Paper days elapsed: {days_elapsed:.1f}/60 (D21 target = Week 3 activation)")
        check("k493_signal_firing", pos_state == "LONG_ATOM_SHORT_BTC",
              f"Signal firing: {pos_state} (LONG_ATOM_SHORT_BTC expected in current regime)", warn_only=True)
    else:
        check("k493_dashboard_json", False, "MISSING — run k493_atom_btc_run.py --status")

    # 1b. K493 run script
    check("k493_run_script", K493_RUN_PY.exists(),
          str(K493_RUN_PY.relative_to(REPO_ROOT)) if K493_RUN_PY.exists() else "MISSING")

    # 1c. K493 plist
    if K493_PLIST.exists():
        plist_text = K493_PLIST.read_text()
        has_dry_run = "--dry-run" in plist_text
        has_paper   = "PAPER_TRADE" in plist_text
        check("k493_plist_exists", True, str(K493_PLIST.relative_to(REPO_ROOT)))
        check("k493_plist_dry_run", has_dry_run,
              "--dry-run flag PRESENT (must remove for Week 3 LIVE)", warn_only=True)
        la_path = Path.home() / "Library" / "LaunchAgents" / "com.cryptolab.k493-atom-btc.plist"
        check("k493_plist_launchagent", la_path.exists(),
              "LOADED in ~/Library/LaunchAgents/" if la_path.exists()
              else "NOT loaded — required for Week 3 activation", warn_only=not la_path.exists())
    else:
        check("k493_plist_exists", False, "com.cryptolab.k493-atom-btc.plist MISSING")

    # 1d. Emergency exit K493 registration (K357 + K499)
    if EMERGENCY_EXIT_PY.exists():
        exit_text = EMERGENCY_EXIT_PY.read_text()
        k493_registered = "K493" in exit_text or "ATOM" in exit_text
        check("k357_k493_registered", k493_registered,
              "K493 ATOM/BTC pair detection PRESENT in emergency_hl_exit.py")
    else:
        check("k357_emergency_exit", False, "emergency_hl_exit.py MISSING")

    # 1e. K493 HL+Bybit split status
    split_proto = "HL-only 3%"
    check("k493_split_protocol", True,
          f"Split design: {split_proto} (K547 plan: 2.5pp HL + 2.5pp Bybit for cap management)",
          warn_only=True)

    # 1f. Week 1+2 prerequisite dashboards
    for dash_path, label in [(K449_DASHBOARD_JSON, "K449"), (K476_DASHBOARD_JSON, "K476"),
                              (K484_DASHBOARD_JSON, "K484")]:
        if dash_path.exists():
            with open(dash_path) as f:
                d2 = json.load(f)
            paper2 = d2.get("paper_trade_mode", True)
            check(f"{label}_dashboard", True,
                  f"EXISTS — paper={paper2} ({'LIVE' if not paper2 else 'still PAPER'})",
                  warn_only=paper2)
        else:
            check(f"{label}_dashboard", False, f"{dash_path.name} MISSING", warn_only=True)

    # Summary
    n_pass = sum(1 for c in results["checks"] if c["status"] == "PASS")
    n_warn = sum(1 for c in results["checks"] if c["status"] == "WARN")
    n_fail = sum(1 for c in results["checks"] if c["status"] == "FAIL")
    print(f"\n  Summary: {green(str(n_pass))} PASS | {yellow(str(n_warn))} WARN | {red(str(n_fail))} FAIL")
    results["summary"] = {"pass": n_pass, "warn": n_warn, "fail": n_fail}
    return results


# ─────────────────────────────────────────────────────────────────────────────
# Phase 2: Pre-requisite checklist (Week 1+2 PASS + HL trajectory)
# ─────────────────────────────────────────────────────────────────────────────

def phase2_prerequisites() -> Dict[str, Any]:
    """Verify Week 1+2 PASS, HL exposure trajectory, K280 cut, K498 activation."""
    print(bold(f"\n{'='*70}"))
    print(bold("Phase 2: Pre-Requisite Checklist for Week 3 Activation"))
    print(bold(f"{'='*70}"))

    results: Dict[str, Any] = {
        "phase": 2,
        "name": "prerequisites",
        "items": [],
    }

    def item(name: str, status: str, detail: str, action: str = "") -> None:
        colour = green if status == "REQUIRED" else (yellow if status == "CHECK" else cyan)
        marker = {"REQUIRED": "[PREREQ]", "CHECK": "[CHECK]", "DONE": "[DONE]"}.get(status, "[INFO]")
        print(f"  {colour(marker)} {bold(name)}")
        print(f"    {detail}")
        if action:
            print(f"    {cyan('Action:')} {action}")
        results["items"].append({"name": name, "status": status, "detail": detail, "action": action})

    print()
    item("Week 1 K449 LIVE PASS (K549 Day 7)",
         "REQUIRED",
         "K449 ETH-BTC must show 7d realized Sharpe ≥ 5 and fill_rate ≥ 50%",
         "python3 scripts/k449_eth_btc_run.py --status  → check 60d_sharpe > 0 and fills > 0")

    item("Week 2 K476 SOL-BTC LIVE PASS",
         "REQUIRED",
         "K476 must show 7d positive PnL and fill_rate > 0% in live mode",
         "python3 scripts/k476_sol_btc_run.py --status  (if script exists)")

    item("Week 2 K484 AVAX-BTC LIVE PASS",
         "REQUIRED",
         "K484 must show 7d positive PnL and fill_rate > 0% in live mode",
         "python3 scripts/k484_avax_btc_run.py --status  (if script exists)")

    item("HL exposure trajectory check",
         "REQUIRED",
         f"Pre-K493: ~{HL_EXPOSURE_PRE:.0%} HL (after W1+W2)\n"
         f"    K493 adds +{HL_K493_ADD_PP:.1f}pp HL (5% sleeve × 50% HL split)\n"
         f"    Post-K493: ~{HL_EXPOSURE_POST:.1%} HL vs {HL_EXPOSURE_CAP:.0%} hard cap → SAFE (+{(HL_EXPOSURE_CAP-HL_EXPOSURE_POST)*100:.1f}pp headroom)",
         "python3 scripts/verify_deployment_status.py  → check hl_exposure_pct")

    item("K280 sleeve 75→60% applied (K552 / K539 Phase B1)",
         "REQUIRED",
         "K280 must be at 60% or lower in scripts/leverage_manager.py",
         "grep '\"K280\"' scripts/leverage_manager.py  → expect 0.60")

    item("K498 Phase 1A activated (K530)",
         "CHECK",
         "BBO_SELECT smart router + OKX daemon should be active (per K530 playbook)",
         "launchctl list | grep okx  → confirm running")

    # HL split calculation detail
    print()
    print(bold("  HL Exposure Trajectory (Week 3):"))
    print(grey("  ─"*35))
    steps = [
        ("Pre-Week 3 baseline",        0.580,  0.0,   "After K280 cut + K449 + K476 + K484"),
        ("+ K493 5% sleeve ×50% HL",   0.605, +2.5,   "2.5pp HL + 2.5pp Bybit split"),
        ("Post-K493 LIVE",             0.605,  0.0,   f"vs {HL_EXPOSURE_CAP:.0%} cap → {(HL_EXPOSURE_CAP-0.605)*100:.1f}pp headroom"),
        ("Week 4 headroom remaining",  0.605,  0.0,   "Room for K500+K507+K507 (+5pp target)"),
    ]
    for label, hl, delta, note in steps:
        delta_str = f" ({'+' if delta >= 0 else ''}{delta:.1f}pp)" if delta != 0.0 else ""
        breach = hl > HL_EXPOSURE_CAP
        status_str = red("BREACH") if breach else green("SAFE")
        print(f"    {label:<40} {hl:.1%}{delta_str:<10} {status_str} — {note}")

    results["hl_trajectory"] = {
        "pre_week3_pct":   HL_EXPOSURE_PRE,
        "k493_add_pp":     HL_K493_ADD_PP,
        "post_k493_pct":   HL_EXPOSURE_POST,
        "cap_pct":         HL_EXPOSURE_CAP,
        "headroom_pp":     round((HL_EXPOSURE_CAP - HL_EXPOSURE_POST) * 100, 1),
        "week4_headroom_pp": round((HL_EXPOSURE_CAP - HL_EXPOSURE_POST) * 100, 1),
    }
    return results


# ─────────────────────────────────────────────────────────────────────────────
# Phase 3: K493 LIVE switch concrete steps
# ─────────────────────────────────────────────────────────────────────────────

def phase3_live_switch_steps() -> Dict[str, Any]:
    """Concrete steps for K493 Week 3 LIVE activation."""
    print(bold(f"\n{'='*70}"))
    print(bold("Phase 3: K493 LIVE Switch Concrete Steps (Week 3 D0)"))
    print(bold(f"{'='*70}"))

    aum                = AUM_REF_USD
    sleeve_capital     = aum * K493_SLEEVE_PCT          # $500K
    total_notional     = sleeve_capital * K493_LEVERAGE  # $2M
    hl_notional        = total_notional * HL_SPLIT_PCT   # $1.2M on HL
    bybit_notional     = total_notional * BYBIT_SPLIT_PCT # $0.8M on Bybit
    hl_margin          = hl_notional / K493_LEVERAGE      # $300K
    bybit_margin       = bybit_notional / K493_LEVERAGE   # $200K

    print(f"\n  Sizing:")
    print(f"    Sleeve:         {K493_SLEEVE_PCT:.0%} × ${aum/1e6:.0f}M = ${sleeve_capital/1e3:.0f}K capital")
    print(f"    Leverage:       {K493_LEVERAGE:.0f}x → ${total_notional/1e6:.1f}M notional")
    print(f"    HL leg:         ${hl_notional/1e6:.2f}M notional (${hl_margin/1e3:.0f}K margin) → ATOM long + BTC short")
    print(f"    Bybit leg:      ${bybit_notional/1e6:.2f}M notional (${bybit_margin/1e3:.0f}K margin) → secondary")
    print(f"    HL exposure:    +{HL_K493_ADD_PP:.1f}pp → {HL_EXPOSURE_POST:.1%} total (< {HL_EXPOSURE_CAP:.0%} cap)")
    print()

    steps = [
        {
            "step": 1,
            "phase": "D0_prereq",
            "name": "Verify K280 sleeve at 60%",
            "command": 'grep \'"K280"\' scripts/leverage_manager.py',
            "verify": "Expected: \"K280\":   0.60,",
            "notes": "If still 0.75, apply K539 Phase B1 cut first (1-LOC sed command)"
        },
        {
            "step": 2,
            "phase": "D0_prereq",
            "name": "Verify Week 1+2 LIVE status",
            "command": "python3 scripts/k449_eth_btc_run.py --status",
            "verify": "paper_trade_mode=false, position_state != NEUTRAL",
            "notes": "K449+K476+K484 must be LIVE and showing non-zero fills before K493 activates"
        },
        {
            "step": 3,
            "phase": "D0_prereq",
            "name": "Check HL margin health",
            "command": "python3 scripts/emergency_hl_exit.py --dry-run --status",
            "verify": "Margin utilisation < 70% on HL account",
            "notes": "K493 adds $300K HL margin. Ensure sufficient headroom."
        },
        {
            "step": 4,
            "phase": "D0_config",
            "name": "Remove --dry-run from K493 plist",
            "command": "sed -i '' '/<string>--dry-run<\\/string>/d' com.cryptolab.k493-atom-btc.plist",
            "verify": "grep 'dry-run' com.cryptolab.k493-atom-btc.plist || echo 'CLEAN'",
            "notes": "Remove --dry-run from ProgramArguments to enable live execution"
        },
        {
            "step": 5,
            "phase": "D0_config",
            "name": "Set PAPER_TRADE=False in plist env",
            "command": "# Edit plist EnvironmentVariables: set PAPER_TRADE to False",
            "verify": "grep PAPER_TRADE com.cryptolab.k493-atom-btc.plist",
            "notes": "k493_atom_btc_run.py reads PAPER_TRADE env var — must be 'False' or absent for live"
        },
        {
            "step": 6,
            "phase": "D0_load",
            "name": "Copy plist to LaunchAgents",
            "command": "cp com.cryptolab.k493-atom-btc.plist ~/Library/LaunchAgents/com.cryptolab.k493-atom-btc.plist",
            "verify": "ls -la ~/Library/LaunchAgents/com.cryptolab.k493-atom-btc.plist",
            "notes": "Copy modified (LIVE mode) plist to system LaunchAgents directory"
        },
        {
            "step": 7,
            "phase": "D0_load",
            "name": "launchctl load K493 daemon",
            "command": "launchctl load ~/Library/LaunchAgents/com.cryptolab.k493-atom-btc.plist",
            "verify": "launchctl list | grep k493-atom-btc",
            "notes": "Loads daemon; first execution at next 8h cron interval"
        },
        {
            "step": 8,
            "phase": "D0_verify",
            "name": "Confirm K357 emergency exit includes K493",
            "command": "grep -c 'K493\\|ATOM' scripts/emergency_hl_exit.py",
            "verify": "Expected: >=3 matches (K499 already implemented K493 detection)",
            "notes": "K493 paired-position detection present per K499 scaffold"
        },
        {
            "step": 9,
            "phase": "D0_verify",
            "name": "K434 smart router routing check",
            "command": "python3 scripts/k493_atom_btc_run.py --status",
            "verify": "Dashboard refreshed, venue=HL or HL+Bybit split confirmed",
            "notes": "K493 uses HL-primary + Bybit-secondary split for cap management"
        },
        {
            "step": 10,
            "phase": "D0_verify",
            "name": "K493 initial position status",
            "command": "python3 scripts/k493_atom_btc_run.py --status",
            "verify": "position_state=LONG_ATOM_SHORT_BTC (signal already firing per K547)",
            "notes": "ATOM FR diff was -1.77e-5 at scaffold time — signal likely still active"
        },
        {
            "step": 11,
            "phase": "D0_commit",
            "name": "Commit plist LIVE change + push",
            "command": 'git add com.cryptolab.k493-atom-btc.plist && git commit -m "K556 K493 plist: remove --dry-run for Week 3 LIVE activation" && git push origin main',
            "verify": "git log --oneline -1",
            "notes": "Commit the LIVE plist to repo for audit trail"
        },
    ]

    print(bold("  Activation steps:"))
    for s in steps:
        tag = yellow(f"[D0 {s['phase'].upper()}]")
        print(f"  {tag} Step {s['step']}: {bold(s['name'])}")
        print(f"    {cyan('CMD:')} {s['command']}")
        print(f"    {green('VFY:')} {s['verify']}")
        print(f"    {grey('NOTE:')} {s['notes']}")
        print()

    # POST_ONLY K439 execution note
    print(bold("  K439 POST_ONLY execution path (K493):"))
    print(f"  k493_atom_btc_run.py → submit_paired_trade() → POST_ONLY both legs in parallel")
    print(f"  Long leg:   ATOM perp post-only limit at mid (positive FR diff → long ATOM)")
    print(f"  Short leg:  BTC perp post-only limit at mid")
    print(f"  Rollback:   if ATOM fills but BTC fails → cancel ATOM within 5s (K439 pattern)")
    print(f"  HL-primary: up to ${hl_notional/1e6:.2f}M notional; Bybit-secondary: up to ${bybit_notional/1e6:.2f}M")
    print()

    results = {
        "phase": 3,
        "name": "live_switch_steps",
        "sizing": {
            "aum_ref_usd":       aum,
            "sleeve_pct":        K493_SLEEVE_PCT,
            "sleeve_capital_usd": sleeve_capital,
            "leverage":          K493_LEVERAGE,
            "total_notional_usd": total_notional,
            "hl_notional_usd":   hl_notional,
            "bybit_notional_usd": bybit_notional,
            "hl_margin_usd":     hl_margin,
            "bybit_margin_usd":  bybit_margin,
        },
        "steps": steps,
        "execution": {
            "order_type":   "POST_ONLY (maker)",
            "submission":   "Parallel (K439 pattern)",
            "close_order":  "Sequential: BTC short first, then ATOM long",
            "fallback":     "IOC on timeout (>5s)",
            "cadence_h":    8,
        }
    }
    return results


# ─────────────────────────────────────────────────────────────────────────────
# Phase 4: Day 21-28 monitoring specification
# ─────────────────────────────────────────────────────────────────────────────

def phase4_monitoring_spec() -> Dict[str, Any]:
    """Day 21-28 monitoring specification for K493 Week 3."""
    print(bold(f"\n{'='*70}"))
    print(bold("Phase 4: Day 21-28 Monitoring Specification (Week 3)"))
    print(bold(f"{'='*70}"))

    print(f"\n  Reference date: D0 = 2026-05-30 (K547), D21 = Week 3 activation target")
    print(f"  Monitoring window: D21 (activation) → D28 (Week 3 + 7d decision)")
    print()

    metrics = [
        ("Daily Sharpe realized",      "60d_sharpe in k493_dashboard.json",
         "Daily P&L / rolling vol → target ≥ 25 at D28 for PASS",
         "python3 scripts/k493_atom_btc_run.py --status | grep sharpe"),
        ("Fill rate (paired legs)",    "paper_fill_rate_pct in gate_metrics",
         "Both ATOM + BTC legs must fill > 65% of signals; POST_ONLY maker fill",
         "cat data/k493_dashboard.json | python3 -c \"import json,sys; d=json.load(sys.stdin); print(d.get('gate_metrics',{}).get('current_fill_rate',0))\""),
        ("HL margin health",           "Via emergency_hl_exit.py --status",
         "Margin utilisation < 75%; alert if > 80% (K386 fallback trigger)",
         "python3 scripts/emergency_hl_exit.py --dry-run --status"),
        ("Funding rate carry/leg",     "fr_atom_current + fr_btc_current in dashboard",
         "ATOM FR − BTC FR > 0 confirms positive carry; monitor 7d EMA stability",
         "cat data/k493_dashboard.json | python3 -c \"import json,sys; d=json.load(sys.stdin); print(f'ATOM FR: {d.get(\\\"fr_atom_current\\\",0):.6f}, BTC FR: {d.get(\\\"fr_btc_current\\\",0):.6f}, Diff: {d.get(\\\"fr_raw_diff\\\",0):.6f}')\""),
        ("Delta neutral drift",        "delta_neutral_drift_pct in dashboard",
         "Drift > 5% triggers rebalance; > 10% triggers alert",
         "cat data/k493_dashboard.json | python3 -c \"import json,sys; d=json.load(sys.stdin); print(f'Drift: {d.get(\\\"delta_neutral_drift_pct\\\",0):.3%}')\""),
        ("Cross-venue sync (HL+Bybit)","Via k493_atom_btc_run.py --status",
         "If Bybit leg split active: confirm both legs in sync; no uncovered position",
         "launchctl list | grep k493 && python3 scripts/k493_atom_btc_run.py --status"),
        ("Realized daily PnL",         "daily_pnl_usdc in dashboard",
         f"Expected: ${K493_ANN_RETURN_USD/365:.0f}/day @ $10M (${K493_ANN_RETURN_USD}/yr ÷ 365)",
         "cat data/k493_dashboard.json | python3 -c \"import json,sys; d=json.load(sys.stdin); print(f'Daily PnL: ${d.get(\\\"daily_pnl_usdc\\\",0):.2f}')\""),
    ]

    print(bold("  Daily monitoring checklist:"))
    for name, source, detail, command in metrics:
        print(f"\n  {bold(name)}")
        print(f"    Source:  {grey(source)}")
        print(f"    Criteria:{detail}")
        print(f"    Command: {cyan(command)}")

    print()
    print(bold("  Quick daily one-liner:"))
    print(cyan("""  python3 scripts/k493_atom_btc_run.py --status && \\
    cat data/k493_dashboard.json | python3 -c "
  import json, sys; d = json.load(sys.stdin)
  g = d.get('gate_metrics', {})
  print(f'State:    {d[\"position_state\"]}')
  print(f'PnL/day:  \${d[\"daily_pnl_usdc\"]:.2f}')
  print(f'Sharpe:   {d[\"60d_sharpe\"]:.2f}')
  print(f'Fill:     {g.get(\"current_fill_rate\",0):.1%}')
  print(f'Drift:    {d[\"delta_neutral_drift_pct\"]:.3%}')
  print(f'FR diff:  {d[\"fr_raw_diff\"]:.6f}')
  print(f'Gate:     {g.get(\"gate_status\",\"UNKNOWN\")}')
  " """))

    results = {
        "phase": 4,
        "name": "monitoring_spec",
        "d0": "2026-05-30",
        "d21_target": "2026-06-20",
        "d28_decision": "2026-06-27",
        "daily_pnl_target_usd": round(K493_ANN_RETURN_USD / 365, 2),
        "metrics": [{"name": m[0], "source": m[1], "detail": m[2]} for m in metrics],
    }
    return results


# ─────────────────────────────────────────────────────────────────────────────
# Phase 5: Decision matrix at Week 3 + 7 days (D28)
# ─────────────────────────────────────────────────────────────────────────────

def phase5_decision_matrix() -> Dict[str, Any]:
    """Decision matrix for Week 3 Day 28 evaluation."""
    print(bold(f"\n{'='*70}"))
    print(bold("Phase 5: Decision Matrix at Week 3 + 7 Days (D28)"))
    print(bold(f"{'='*70}"))

    print()
    print(bold("  K493 D28 Decision Matrix:"))
    print(grey("  ─"*60))
    print(f"  {'Decision':<12} {'Realized Sharpe':<22} {'Fill Rate':<18} {'Action'}")
    print(grey("  " + "─"*58))

    decisions = [
        ("PASS",     f"≥ {PASS_SHARPE:.0f}",   f"≥ {PASS_FILL_RATE:.0%}",  "Expand to 8% sleeve → Week 4 prep begins"),
        ("HOLD",     f"{HOLD_SHARPE_LOW:.0f}–{PASS_SHARPE:.0f}",
                                               f"{HOLD_FILL_RATE_LOW:.0%}–{PASS_FILL_RATE:.0%}",
                                                                "Maintain 5% sleeve; re-evaluate at D35"),
        ("ROLLBACK", f"< {ROLLBACK_SHARPE:.0f}", f"< {HOLD_FILL_RATE_LOW:.0%} OR margin > 80%",
                                                "Close legs; reload --dry-run; return to paper"),
    ]
    colours = [green, yellow, red]
    for (dec, sh, fill, action), colour in zip(decisions, colours):
        print(f"  {colour(f'[{dec}]'):<20} {sh:<22} {fill:<18} {action}")

    print()
    print(bold("  Expansion sizing (PASS scenario):"))
    for sleeve_pct in [0.05, 0.08, 0.10]:
        notional = AUM_REF_USD * sleeve_pct * K493_LEVERAGE
        ann_scaled = K493_ANN_RETURN_USD * (sleeve_pct / 0.03)
        print(f"    {sleeve_pct:.0%} sleeve → ${notional/1e6:.1f}M notional → ${ann_scaled/1e3:.0f}K/yr @ $10M")

    print()
    print(bold("  ROLLBACK procedure:"))
    rollback_steps = [
        "1. launchctl unload ~/Library/LaunchAgents/com.cryptolab.k493-atom-btc.plist",
        "2. python3 scripts/k493_atom_btc_run.py --close 'Week 3 rollback'",
        "3. Verify positions closed: python3 scripts/emergency_hl_exit.py --status",
        "4. Restore --dry-run in plist; reload in paper mode",
        "5. Update data/k493_dashboard.json paper_trade_mode=true",
    ]
    for step in rollback_steps:
        print(f"    {cyan(step)}")

    results = {
        "phase": 5,
        "name": "decision_matrix",
        "evaluation_date": "D28 (2026-06-27 target)",
        "decisions": [
            {"outcome": "PASS",     "sharpe_min": PASS_SHARPE,     "fill_min": PASS_FILL_RATE,  "action": "expand_to_8pct"},
            {"outcome": "HOLD",     "sharpe_range": [HOLD_SHARPE_LOW, PASS_SHARPE], "action": "maintain_5pct"},
            {"outcome": "ROLLBACK", "sharpe_max": ROLLBACK_SHARPE, "action": "close_reload_paper"},
        ],
        "oos_paper_sharpe_decay_est": {
            "oos_paper": K493_OOS_SHARPE,
            "live_est":  K493_LIVE_SHARPE_EST,
            "decay_pct": round((K493_OOS_SHARPE - K493_LIVE_SHARPE_EST) / K493_OOS_SHARPE * 100, 1),
            "note": "20-30% Sharpe decay from slippage + fee drag expected post-live"
        },
    }
    return results


# ─────────────────────────────────────────────────────────────────────────────
# Phase 6: HL exposure post-Week 3
# ─────────────────────────────────────────────────────────────────────────────

def phase6_hl_exposure() -> Dict[str, Any]:
    """HL exposure trajectory post-Week 3 + Week 4 headroom."""
    print(bold(f"\n{'='*70}"))
    print(bold("Phase 6: HL Exposure Post-Week 3 + Week 4 Headroom"))
    print(bold(f"{'='*70}"))

    print()
    scenario = [
        ("v6.13d baseline",                   0.650, "Before K280 cut — at hard cap"),
        ("K280 Phase B1 cut (75→60%)",         0.575, "−7.5pp HL"),
        ("+ K449 ETH-BTC LIVE (5%, HL-only)", 0.625, "+5pp (5% × 100%)"),
        ("+ K476 SOL-BTC (2% HL + 1% Bybit)", 0.645, "+2pp (split to stay under cap)"),
        ("+ K484 AVAX-BTC (2% HL + 1% Bybit)",0.605, "K280 micro-trim −4pp; +2pp AVAX"),
        ("+ K493 ATOM-BTC (2.5% HL + 2.5% Bybit)", 0.605, "+2.5pp HL; net ~60.5%"),
        ("Week 4 headroom (K500+K507+K507)",   0.605, f"4.5pp remaining vs {HL_EXPOSURE_CAP:.0%} cap"),
    ]

    print(f"  {'Step':<50} {'HL%':<8} Note")
    print(grey("  " + "─"*80))
    for label, hl_pct, note in scenario:
        breach = hl_pct > HL_EXPOSURE_CAP
        status = f" {red('BREACH')}" if breach else ""
        bar = int(hl_pct * 30)
        bar_str = "#" * bar + " " * (20 - bar)
        print(f"  {label:<50} {hl_pct:.1%}{status}")

    print()
    print(f"  {bold('Post-Week 3 HL:')} {HL_EXPOSURE_POST:.1%} (cap: {HL_EXPOSURE_CAP:.0%})")
    headroom = (HL_EXPOSURE_CAP - HL_EXPOSURE_POST) * 100
    print(f"  {bold('Headroom for Week 4:')} {headroom:.1f}pp")
    print(f"  {bold('Week 4 target:')} K500 INJ(2pp) + K507 SEI(1.5pp) + K507 TIA(1pp) = 4.5pp → {HL_EXPOSURE_POST + 0.045:.1%}")
    print()

    print(bold("  Split protocol for K493 (cap management):"))
    print(f"  Primary:   HyperLiquid {HL_SPLIT_PCT:.0%} → {AUM_REF_USD * K493_SLEEVE_PCT * K493_LEVERAGE * HL_SPLIT_PCT / 1e6:.2f}M notional")
    print(f"  Secondary: Bybit       {BYBIT_SPLIT_PCT:.0%} → ${AUM_REF_USD * K493_SLEEVE_PCT * K493_LEVERAGE * BYBIT_SPLIT_PCT / 1e6:.2f}M notional")
    print(f"  HL delta:  +{HL_K493_ADD_PP:.1f}pp ({K493_SLEEVE_PCT:.0%} × {HL_SPLIT_PCT:.0%} = {K493_SLEEVE_PCT * HL_SPLIT_PCT:.1%} AUM)")

    results = {
        "phase": 6,
        "name": "hl_exposure",
        "pre_k493_pct":   HL_EXPOSURE_PRE,
        "k493_hl_add_pp": HL_K493_ADD_PP,
        "post_k493_pct":  HL_EXPOSURE_POST,
        "cap_pct":        HL_EXPOSURE_CAP,
        "headroom_pp":    headroom,
        "week4_planned_pp": 4.5,
        "week4_post_pct": HL_EXPOSURE_POST + 0.045,
        "split": {
            "hl_fraction":    HL_SPLIT_PCT,
            "bybit_fraction": BYBIT_SPLIT_PCT,
        }
    }
    return results


# ─────────────────────────────────────────────────────────────────────────────
# Phase 7: Profit projection
# ─────────────────────────────────────────────────────────────────────────────

def phase7_profit_projection() -> Dict[str, Any]:
    """Profit projection realized at multiple AUM scales."""
    print(bold(f"\n{'='*70}"))
    print(bold("Phase 7: Profit Projection (Realized) — Multiple AUM Scales"))
    print(bold(f"{'='*70}"))

    def scale(base_10m: int, aum: int) -> str:
        return f"${base_10m * (aum / AUM_REF_USD) / 1e6:.2f}M"

    table = [
        ("Week 1",  "K449 ETH-BTC",            WEEK1_K449_USD,  WEEK1_K449_USD),
        ("Week 2",  "K476 SOL + K484 AVAX",    WEEK2_K476_USD + WEEK2_K484_USD,
                                                WEEK1_K449_USD + WEEK2_K476_USD + WEEK2_K484_USD),
        ("Week 3",  "K493 ATOM-BTC (THIS WAVE)",WEEK3_K493_USD, CUMULATIVE_W3_USD),
        ("Week 4",  "K500+K507 SEI+K507 TIA",  354_000,         CUMULATIVE_W3_USD + 354_000),
        ("Week 5",  "K512 APT-BTC",            302_000,         CUMULATIVE_W3_USD + 354_000 + 302_000),
    ]

    print(f"\n  {'Week':<10} {'Strategy':<30} {'Delta/yr':<14} {'Cumulative/yr':<16} @$30M       @$100M")
    print(grey("  " + "─"*90))
    for week, strat, delta, cumul in table:
        is_this = "← THIS" if week == "Week 3" else ""
        print(f"  {week:<10} {strat:<30} ${delta/1e3:.0f}K{'':<8} ${cumul/1e3:.0f}K/yr{'':<9}"
              f"${cumul * 3 / 1e6:.2f}M     ${cumul * 10 / 1e6:.2f}M   {yellow(is_this)}")

    print()
    print(bold(f"  Week 3 Cumulative @ $10M:   ${CUMULATIVE_W3_USD/1e3:.0f}K/yr"))
    print(bold(f"  Week 3 Cumulative @ $30M:   ${CUMULATIVE_W3_USD * 3 / 1e6:.2f}M/yr"))
    print(bold(f"  Week 3 Cumulative @ $100M:  ${CUMULATIVE_W3_USD * 10 / 1e6:.2f}M/yr"))

    print()
    print(bold("  K493 standalone:"))
    print(f"    $10M:  ${K493_ANN_RETURN_USD/1e3:.0f}K/yr ({K493_OOS_SHARPE:.2f} OOS Sharpe → ~{K493_LIVE_SHARPE_EST:.1f} live est)")
    print(f"    $30M:  ${K493_ANN_RETURN_USD * 3 / 1e6:.2f}M/yr")
    print(f"    $100M: ${K493_ANN_RETURN_USD * 10 / 1e6:.2f}M/yr (subject to HL liquidity ceiling ~$30M effective)")

    results = {
        "phase": 7,
        "name": "profit_projection",
        "k493_standalone": {
            "at_10m_usd": K493_ANN_RETURN_USD,
            "at_30m_usd": K493_ANN_RETURN_USD * 3,
            "at_100m_usd": K493_ANN_RETURN_USD * 10,
        },
        "week3_cumulative": {
            "at_10m_usd": CUMULATIVE_W3_USD,
            "at_30m_usd": CUMULATIVE_W3_USD * 3,
            "at_100m_usd": CUMULATIVE_W3_USD * 10,
            "breakdown": {
                "k449_eth_btc": WEEK1_K449_USD,
                "k476_sol_btc": WEEK2_K476_USD,
                "k484_avax_btc": WEEK2_K484_USD,
                "k493_atom_btc": WEEK3_K493_USD,
            }
        },
        "full_family_projection": {
            "at_10m_usd":  CUMULATIVE_W3_USD + 354_000 + 302_000,
            "at_30m_usd": (CUMULATIVE_W3_USD + 354_000 + 302_000) * 3,
            "at_100m_usd":(CUMULATIVE_W3_USD + 354_000 + 302_000) * 10,
        }
    }
    return results


# ─────────────────────────────────────────────────────────────────────────────
# Phase 8: Risk inventory
# ─────────────────────────────────────────────────────────────────────────────

def phase8_risk_inventory() -> Dict[str, Any]:
    """K493 Week 3 risk inventory."""
    print(bold(f"\n{'='*70}"))
    print(bold("Phase 8: Risk Inventory (K493 Week 3)"))
    print(bold(f"{'='*70}"))

    risks = [
        {
            "id": "R1",
            "name": "Paper vs LIVE Sharpe divergence",
            "severity": "HIGH",
            "probability": "MEDIUM",
            "detail": f"OOS Sh {K493_OOS_SHARPE:.2f} → live est {K493_LIVE_SHARPE_EST:.1f} (20-30% decay). "
                      f"High OOS Sharpe = more decay risk (overfitting to historical FR cycles).",
            "mitigation": "Post-only fill optimization; 7d live monitoring gate; rollback < Sh 15"
        },
        {
            "id": "R2",
            "name": "HL + Bybit cross-venue sync failure",
            "severity": "MEDIUM",
            "probability": "LOW",
            "detail": "If Bybit leg fails to fill while HL ATOM leg fills → uncovered directional exposure",
            "mitigation": "K439 rollback: cancel HL leg within 5s if Bybit fails. Monitor cross-venue sync daily."
        },
        {
            "id": "R3",
            "name": "Cosmos hypothesis maintenance",
            "severity": "MEDIUM",
            "probability": "LOW",
            "detail": "ATOM FR differential driven by IBC flows + staking yield competition + governance cycles. "
                      "If IBC network effect weakens or staking APY converges with market, signal degrades.",
            "mitigation": "Monitor ATOM staking yield vs BTC funding. Check G5a correlation monthly."
        },
        {
            "id": "R4",
            "name": "BTC flash crash (correlated leg risk)",
            "severity": "HIGH",
            "probability": "LOW",
            "detail": "BTC -20% flash crash: all BTC-short legs gain, ATOM-long leg loses. "
                      "Delta-neutral design absorbs price move. Tail loss est 1.7-4.0%.",
            "mitigation": "K357 emergency exit registered. HL margin monitored. Delta drift alert > 10%."
        },
        {
            "id": "R5",
            "name": "HL cap breach during Week 3 activation",
            "severity": "HIGH",
            "probability": "LOW",
            "detail": f"K493 adds {HL_K493_ADD_PP:.1f}pp HL → {HL_EXPOSURE_POST:.1%} (cap {HL_EXPOSURE_CAP:.0%}). "
                      f"If Week 1+2 used more HL than planned, breach risk increases.",
            "mitigation": "Verify HL pct via verify_deployment_status.py before activation. Use Bybit split."
        },
        {
            "id": "R6",
            "name": "G6 low-frequency gate (18.2/yr)",
            "severity": "LOW",
            "probability": "CERTAIN",
            "detail": "K493 only fires ~18 trades/yr (confirmed G6 FAIL). Long holding periods "
                      "mean slippage per trade is amortized but signal is slow to adapt.",
            "mitigation": "Accepted at reduced sizing (3% sleeve). Monitor signal count vs expected 18.2/yr."
        },
    ]

    for r in risks:
        sev_colour = red if r["severity"] == "HIGH" else (yellow if r["severity"] == "MEDIUM" else green)
        print(f"\n  {r['id']}: {bold(r['name'])} [{sev_colour(r['severity'])} / {r['probability']}]")
        print(f"    {r['detail']}")
        print(f"    {green('Mitigation:')} {r['mitigation']}")

    return {"phase": 8, "name": "risk_inventory", "risks": risks}


# ─────────────────────────────────────────────────────────────────────────────
# Phase 9: User action checklist (Week 3 D0)
# ─────────────────────────────────────────────────────────────────────────────

def phase9_user_checklist() -> Dict[str, Any]:
    """Week 3 D0 user action checklist (printed and machine-readable)."""
    print(bold(f"\n{'='*70}"))
    print(bold("Phase 9: User Action Checklist — Week 3 D0"))
    print(bold(f"{'='*70}"))

    checklist = [
        {
            "id": 1,
            "action": "K547 Week 2 PASS verification",
            "command": "cat data/k476_dashboard.json && cat data/k484_dashboard.json",
            "criteria": "Both paper_trade_mode=false AND position_state != NEUTRAL in recent poll",
            "time_min": 2,
        },
        {
            "id": 2,
            "action": "K493 dashboard health check",
            "command": "python3 scripts/k493_atom_btc_run.py --status",
            "criteria": "Dashboard up-to-date; gate_status=IN_PROGRESS; signal LONG_ATOM_SHORT_BTC",
            "time_min": 2,
        },
        {
            "id": 3,
            "action": "HL margin pre-check",
            "command": "python3 scripts/emergency_hl_exit.py --dry-run --status",
            "criteria": "Margin utilisation < 70%; sufficient headroom for +$300K margin",
            "time_min": 2,
        },
        {
            "id": 4,
            "action": "Edit K493 plist — remove --dry-run, set PAPER_TRADE=False",
            "command": "sed -i '' '/<string>--dry-run<\\/string>/d' com.cryptolab.k493-atom-btc.plist",
            "criteria": "grep 'dry-run' com.cryptolab.k493-atom-btc.plist returns nothing (CLEAN)",
            "time_min": 3,
        },
        {
            "id": 5,
            "action": "Copy plist to LaunchAgents + launchctl load",
            "command": "cp com.cryptolab.k493-atom-btc.plist ~/Library/LaunchAgents/ && launchctl load ~/Library/LaunchAgents/com.cryptolab.k493-atom-btc.plist",
            "criteria": "launchctl list | grep k493-atom-btc returns PID > 0",
            "time_min": 2,
        },
        {
            "id": 6,
            "action": "Confirm K357 emergency exit includes K493",
            "command": "grep -c 'K493\\|ATOM' scripts/emergency_hl_exit.py",
            "criteria": "Count >= 3 (K499 scaffold already added K493 detection)",
            "time_min": 1,
        },
        {
            "id": 7,
            "action": "7d Sharpe verification (D28 gate)",
            "command": "python3 wave_k556_k493_week3_live.py --phase5",
            "criteria": "Review decision matrix; schedule D28 calendar reminder",
            "time_min": 2,
        },
        {
            "id": 8,
            "action": "Commit LIVE plist + push",
            "command": 'git add com.cryptolab.k493-atom-btc.plist && git commit -m "K556 K493 ATOM-BTC Week 3 LIVE activation" && git push origin main',
            "criteria": "git log --oneline -1 shows K556 commit",
            "time_min": 3,
        },
        {
            "id": 9,
            "action": "Week 4 prep initiation (K500+K507)",
            "command": "python3 wave_k556_k493_week3_live.py --phase10",
            "criteria": "Review K500/K507 paper gate status; schedule Week 4 activation",
            "time_min": 5,
        },
    ]

    total_min = sum(c["time_min"] for c in checklist)
    print(f"\n  Total estimated time: {total_min} minutes")
    print()
    for c in checklist:
        print(f"  [ ] #{c['id']} — {bold(c['action'])} ({c['time_min']} min)")
        print(f"       {cyan('CMD:')} {c['command']}")
        print(f"       {green('OK?')} {c['criteria']}")
        print()

    return {
        "phase": 9,
        "name": "user_checklist",
        "total_time_min": total_min,
        "items": checklist
    }


# ─────────────────────────────────────────────────────────────────────────────
# Phase 10: Week 4 prep
# ─────────────────────────────────────────────────────────────────────────────

def phase10_week4_prep() -> Dict[str, Any]:
    """Week 4 cascade prep: K500 INJ + K507 SEI + K507 TIA."""
    print(bold(f"\n{'='*70}"))
    print(bold("Phase 10: Week 4 Prep (K500 INJ + K507 SEI + K507 TIA)"))
    print(bold(f"{'='*70}"))

    print()
    print(bold("  Week 4 activation plan (D21-D35 after K493 PASS):"))
    week4 = [
        {
            "daemon": "K500 INJ-BTC",
            "oos_sharpe": 11.23,
            "ann_return_usd": 124_000,
            "sleeve": "2% HL + 1% Bybit",
            "hl_add_pp": 2.0,
            "timing": "D21 (K493 gate pass)",
            "plist": "com.cryptolab.k500-inj-btc.plist",
            "signal_status": "LONG_INJ_SHORT_BTC (firing at scaffold)",
        },
        {
            "daemon": "K507 SEI-BTC",
            "oos_sharpe": 48.1,
            "ann_return_usd": 179_000,
            "sleeve": "1.5% HL + 1.5% Bybit",
            "hl_add_pp": 1.5,
            "timing": "D23 (+48h after K500)",
            "plist": "com.cryptolab.k507-sei-btc.plist",
            "signal_status": "NEUTRAL at scaffold",
        },
        {
            "daemon": "K507 TIA-BTC",
            "oos_sharpe": 14.44,
            "ann_return_usd": 51_000,
            "sleeve": "1% HL",
            "hl_add_pp": 1.0,
            "timing": "D25 (+48h after SEI)",
            "plist": "com.cryptolab.k507-sei-btc.plist",
            "signal_status": "LONG_BTC_SHORT_TIA at scaffold",
        },
    ]

    hl_running = HL_EXPOSURE_POST
    for w in week4:
        hl_after = hl_running + w["hl_add_pp"] / 100
        breach = hl_after > HL_EXPOSURE_CAP
        status = red("BREACH") if breach else green(f"{hl_after:.1%}")
        print(f"\n  {bold(w['daemon'])} ({w['timing']})")
        print(f"    OOS Sharpe:   {w['oos_sharpe']:.2f}  |  Ann. return: ${w['ann_return_usd']/1e3:.0f}K/yr @ $10M")
        print(f"    Sleeve:       {w['sleeve']}  (+{w['hl_add_pp']:.1f}pp HL)")
        print(f"    HL after:     {status}")
        print(f"    Signal:       {w['signal_status']}")
        plist_name = w["plist"]
        print(f"    Load cmd:     {cyan(f'launchctl load ~/Library/LaunchAgents/{plist_name}')}")
        hl_running = hl_after

    print()
    print(bold("  Week 4 combined profit:"))
    print(f"    INJ ($124K) + SEI ($179K) + TIA ($51K) = $354K/yr incremental")
    print(f"    Cumulative W1-W4: ${(CUMULATIVE_W3_USD + 354_000)/1e3:.0f}K/yr @ $10M")
    print(f"    HL exposure after W4: ~{hl_running:.1%} vs {HL_EXPOSURE_CAP:.0%} cap")

    print()
    print(bold("  Decision tree for Week 4:"))
    print(f"  K493 PASS (Sh ≥ {PASS_SHARPE:.0f}) → {green('K500 activate D21')}")
    print(f"  K493 HOLD (Sh {HOLD_SHARPE_LOW:.0f}-{PASS_SHARPE:.0f}) → {yellow('Wait for K493 D35 re-eval; K500 deferred')}")
    print(f"  K493 ROLLBACK (Sh < {ROLLBACK_SHARPE:.0f}) → {red('No Week 4; re-evaluate entire cascade')}")

    return {
        "phase": 10,
        "name": "week4_prep",
        "strategies": week4,
        "cumulative_w1_w4_usd": CUMULATIVE_W3_USD + 354_000,
        "hl_after_w4_pct": hl_running,
        "decision_tree": {
            "pass": "K500 activate D21",
            "hold": "K500 deferred to D35",
            "rollback": "Week 4 cascade paused",
        }
    }


# ─────────────────────────────────────────────────────────────────────────────
# Status overview
# ─────────────────────────────────────────────────────────────────────────────

def print_status() -> None:
    """Print concise status of K493 Week 3 readiness."""
    JST = timezone(timedelta(hours=9))
    now = datetime.now(JST).strftime("%Y-%m-%d %H:%M JST")

    print(bold(f"\n{'='*70}"))
    print(bold("K556 K493 ATOM-BTC Week 3 LIVE Activation — Status"))
    print(bold(f"{'='*70}"))
    print(f"  Wave:      {WAVE}")
    print(f"  Strategy:  K493 ATOM-BTC FR Differential (family #1, Sh {K493_OOS_SHARPE:.2f})")
    print(f"  Profit:    ${K493_ANN_RETURN_USD/1e3:.0f}K/yr @$10M | ${K493_ANN_RETURN_USD*3/1e6:.2f}M @$30M | ${K493_ANN_RETURN_USD*10/1e6:.2f}M @$100M")
    print(f"  Cumul W3:  ${CUMULATIVE_W3_USD/1e3:.0f}K/yr @$10M (W1+W2+W3)")
    print(f"  HL post:   {HL_EXPOSURE_POST:.1%} (cap {HL_EXPOSURE_CAP:.0%}, +{HL_K493_ADD_PP:.1f}pp)")
    print(f"  As of:     {now}")
    print()

    # Live dashboard check
    if K493_DASHBOARD_JSON.exists():
        with open(K493_DASHBOARD_JSON) as f:
            dash = json.load(f)
        print(f"  Dashboard: {green('FOUND')}")
        print(f"    State:    {dash.get('position_state', 'UNKNOWN')}")
        print(f"    Paper:    {dash.get('paper_trade_mode', True)}")
        print(f"    Sharpe:   {dash.get('60d_sharpe', 0.0):.2f}")
        print(f"    Days:     {dash.get('paper_trade_status', {}).get('days_elapsed', 0):.1f}/60")
        print(f"    Signal:   {dash.get('fr_raw_diff', 0.0):.6f} (raw diff)")
        gate = dash.get("gate_metrics", {})
        print(f"    Gate:     {gate.get('gate_status', 'UNKNOWN')}")
    else:
        print(f"  Dashboard: {red('MISSING')}")

    # Plist loaded check
    la_path = Path.home() / "Library" / "LaunchAgents" / "com.cryptolab.k493-atom-btc.plist"
    loaded = la_path.exists()
    print(f"\n  Daemon:   {'LOADED' if loaded else red('NOT LOADED')} in ~/Library/LaunchAgents/")
    print()
    print(f"  Usage:    python3 {Path(__file__).name} --all   (full playbook)")
    print(f"            python3 {Path(__file__).name} --checklist  (D0 user actions)")
    print(f"            python3 {Path(__file__).name} --export-json  (write JSON output)")


# ─────────────────────────────────────────────────────────────────────────────
# Export JSON
# ─────────────────────────────────────────────────────────────────────────────

def export_json(phases: Dict[str, Any]) -> None:
    """Write consolidated JSON output to wave_k556_k493_week3_live.json."""
    JST = timezone(timedelta(hours=9))
    now_str = datetime.now(JST).strftime("%Y-%m-%d %H:%M JST")

    output = {
        "wave":           WAVE,
        "strategy":       "K493_ATOM_BTC",
        "title":          "K493 ATOM-BTC Week 3 LIVE Activation Playbook",
        "generated_jst":  now_str,
        "aum_ref_usd":    AUM_REF_USD,
        "k493_oos_sharpe": K493_OOS_SHARPE,
        "k493_ann_return_usd": K493_ANN_RETURN_USD,
        "cumulative_w3_usd": CUMULATIVE_W3_USD,
        "hl_post_k493_pct": HL_EXPOSURE_POST,
        "hl_cap_pct":     HL_EXPOSURE_CAP,
        "profit_table": {
            "k493_at_10m": K493_ANN_RETURN_USD,
            "k493_at_30m": K493_ANN_RETURN_USD * 3,
            "k493_at_100m": K493_ANN_RETURN_USD * 10,
            "cumulative_w3_at_10m": CUMULATIVE_W3_USD,
            "cumulative_w3_at_30m": CUMULATIVE_W3_USD * 3,
            "cumulative_w3_at_100m": CUMULATIVE_W3_USD * 10,
        },
        "phases": phases,
    }

    with open(OUTPUT_JSON, "w") as f:
        json.dump(output, f, indent=2)
    print(f"\n  {green('[WRITTEN]')} {OUTPUT_JSON.relative_to(REPO_ROOT)}")


# ─────────────────────────────────────────────────────────────────────────────
# Main
# ─────────────────────────────────────────────────────────────────────────────

def main() -> None:
    parser = argparse.ArgumentParser(
        description="K556 K493 ATOM-BTC Week 3 LIVE Activation Playbook"
    )
    parser.add_argument("--status",      action="store_true", help="Print concise status")
    parser.add_argument("--phase1",      action="store_true", help="Scaffold state verify")
    parser.add_argument("--phase2",      action="store_true", help="Pre-requisite checklist")
    parser.add_argument("--phase3",      action="store_true", help="LIVE switch concrete steps")
    parser.add_argument("--phase4",      action="store_true", help="D21-D28 monitoring spec")
    parser.add_argument("--phase5",      action="store_true", help="Decision matrix D28")
    parser.add_argument("--phase6",      action="store_true", help="HL exposure post-Week 3")
    parser.add_argument("--phase7",      action="store_true", help="Profit projection")
    parser.add_argument("--phase8",      action="store_true", help="Risk inventory")
    parser.add_argument("--phase9",      action="store_true", help="User action checklist D0")
    parser.add_argument("--phase10",     action="store_true", help="Week 4 prep")
    parser.add_argument("--checklist",   action="store_true", help="Print D0 checklist only")
    parser.add_argument("--all",         action="store_true", help="Run all phases + export")
    parser.add_argument("--export-json", action="store_true", help="Export JSON output file")
    args = parser.parse_args()

    if args.status or not any(vars(args).values()):
        print_status()
        return

    phases: Dict[str, Any] = {}

    if args.phase1 or args.all:
        phases["phase1"] = phase1_scaffold_verify()
    if args.phase2 or args.all:
        phases["phase2"] = phase2_prerequisites()
    if args.phase3 or args.all:
        phases["phase3"] = phase3_live_switch_steps()
    if args.phase4 or args.all:
        phases["phase4"] = phase4_monitoring_spec()
    if args.phase5 or args.all:
        phases["phase5"] = phase5_decision_matrix()
    if args.phase6 or args.all:
        phases["phase6"] = phase6_hl_exposure()
    if args.phase7 or args.all:
        phases["phase7"] = phase7_profit_projection()
    if args.phase8 or args.all:
        phases["phase8"] = phase8_risk_inventory()
    if args.phase9 or args.checklist or args.all:
        phases["phase9"] = phase9_user_checklist()
    if args.phase10 or args.all:
        phases["phase10"] = phase10_week4_prep()

    if args.export_json or args.all:
        export_json(phases)

    print(bold(f"\n{'='*70}"))
    print(bold(f"K556 Wave Complete — K493 ATOM-BTC Week 3 LIVE Prep"))
    print(bold(f"{'='*70}"))
    print(f"  Strategy:   K493 ATOM-BTC FR Differential (family #1)")
    print(f"  Profit:     ${K493_ANN_RETURN_USD/1e3:.0f}K/yr @$10M | ${K493_ANN_RETURN_USD*3/1e6:.2f}M @$30M | ${K493_ANN_RETURN_USD*10/1e6:.2f}M @$100M")
    print(f"  Cumul W3:   ${CUMULATIVE_W3_USD/1e3:.0f}K/yr @$10M (W1+W2+W3)")
    print(f"  HL post:    {HL_EXPOSURE_POST:.1%} vs {HL_EXPOSURE_CAP:.0%} cap")
    print(f"  Files:      wave_k556_k493_week3_live.{{py,json,md}}")
    print(f"              docs/k302a_master_deployment.md #34")


if __name__ == "__main__":
    main()

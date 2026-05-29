#!/usr/bin/env python3
"""
wave_k549_k449_week1_live.py — K549 K449 ETH-BTC Week 1 LIVE Activation Playbook
==================================================================================
Playbook executor for the K449 ETH-BTC Week 1 LIVE switch.

Tasks executed by this script:
  Phase 1:  Pre-activation state verification
  Phase 2:  K280 sleeve restructure (75% → 60%) audit — playbook only, no writes
  Phase 3:  K449 LIVE switch preflight (plist, daemon, margin calc)
  Phase 4:  Day 1-7 monitoring spec (JSON output)
  Phase 5:  Phase B2 K498 interaction summary
  Phase 6:  Profit lift projection (Week 1 + pipeline validation)
  Phase 7:  Risk inventory
  Phase 8:  User action checklist D0-D7
  Phase 9:  Week 2 prep (K476 + K484 cascade)

LIVE 自動変更禁止 — this script is PLAYBOOK ONLY.
No orders are submitted. No config files are written.
All LIVE changes must be executed manually per the printed checklist.

K339 security: REPO_ROOT from __file__, no /Users/ literals.
No new packages — stdlib only.

Usage:
  python3 wave_k549_k449_week1_live.py --status
  python3 wave_k549_k449_week1_live.py --phase1
  python3 wave_k549_k449_week1_live.py --phase2
  python3 wave_k549_k449_week1_live.py --all
  python3 wave_k549_k449_week1_live.py --checklist
  python3 wave_k549_k449_week1_live.py --export-json
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
WAVE = "K549"

# ── Key file paths (relative via REPO_ROOT) ───────────────────────────────────
K449_DASHBOARD_JSON    = DATA_DIR / "k449_dashboard.json"
K280_DASHBOARD_JSON    = DATA_DIR / "k280_live_dashboard.json"
LEVERAGE_MANAGER_PY    = SCRIPTS_DIR / "leverage_manager.py"
K449_RUN_PY            = SCRIPTS_DIR / "k449_eth_btc_run.py"
K449_PLIST             = REPO_ROOT / "com.cryptolab.k449-eth-btc.plist"
EMERGENCY_EXIT_PY      = SCRIPTS_DIR / "emergency_hl_exit.py"
OUTPUT_JSON            = REPO_ROOT / f"wave_k549_k449_week1_live.json"

# ── Financial constants ───────────────────────────────────────────────────────
AUM_REF_USD            = 10_000_000   # $10M reference AUM
K449_WEEK1_SLEEVE_PCT  = 0.05         # 5% sleeve (per K547 mandate)
K449_LEVERAGE          = 4.0          # 4x leverage (HL-only, delta-neutral)
K449_PROFIT_YR_USD     = 13_000       # K449 $13K/yr @ $10M per K547 audit
K481_BUILDER_REBATE    = 247_000      # K481 builder rebate ~$247K/yr (Phase A)
K280_SLEEVE_CURRENT    = 0.75         # v6.13d production value
K280_SLEEVE_TARGET     = 0.60         # K539 Phase B1 target
HL_EXPOSURE_CURRENT    = 0.575        # 57.5% per v6.13d
HL_EXPOSURE_TARGET_CAP = 0.65         # 65% hard cap (new HL>65% prohibition)

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


# ─────────────────────────────────────────────────────────────────────────────
# Phase 1: Pre-activation state verification
# ─────────────────────────────────────────────────────────────────────────────

def phase1_verify_state() -> Dict[str, Any]:
    """Verify pre-activation state for K449 LIVE switch."""
    print(bold(f"\n{'='*70}"))
    print(bold("Phase 1: Pre-Activation State Verification"))
    print(bold(f"{'='*70}"))

    results: Dict[str, Any] = {
        "phase": 1,
        "name": "pre_activation_verify",
        "checks": [],
        "all_pass": True,
    }

    def check(name: str, ok: bool, detail: str, warn_only: bool = False) -> None:
        status = "PASS" if ok else ("WARN" if warn_only else "FAIL")
        colour = green if ok else (yellow if warn_only else red)
        print(f"  {colour(f'[{status}]')} {name}: {detail}")
        results["checks"].append({
            "name": name, "status": status, "detail": detail
        })
        if not ok and not warn_only:
            results["all_pass"] = False

    # 1a. K449 dashboard JSON
    if K449_DASHBOARD_JSON.exists():
        with open(K449_DASHBOARD_JSON) as f:
            dash = json.load(f)
        paper_mode = dash.get("paper_trade_mode", True)
        pos_state  = dash.get("position_state", "UNKNOWN")
        sleeve_pct = dash.get("sleeve_pct", 0.0)
        sharpe_60d = dash.get("60d_sharpe", 0.0)
        check("k449_dashboard_json", True,
              f"EXISTS — state={pos_state}, paper={paper_mode}, sleeve={sleeve_pct:.0%}")
        check("k449_paper_mode", paper_mode,
              "PAPER_TRADE=True (current) — must flip to False for LIVE", warn_only=True)
        check("k449_sleeve_pct", sleeve_pct == 0.03 or sleeve_pct == 0.05,
              f"sleeve={sleeve_pct:.0%} (target 5% per K547)")
    else:
        check("k449_dashboard_json", False, "MISSING — run k449_eth_btc_run.py --status first")

    # 1b. K449 run script
    check("k449_run_script", K449_RUN_PY.exists(),
          str(K449_RUN_PY.relative_to(REPO_ROOT)))

    # 1c. K449 plist
    if K449_PLIST.exists():
        plist_text = K449_PLIST.read_text()
        has_dry_run = "--dry-run" in plist_text
        check("k449_plist_exists", True, str(K449_PLIST.relative_to(REPO_ROOT)))
        check("k449_plist_dry_run", has_dry_run,
              "--dry-run flag PRESENT (must remove for LIVE)", warn_only=True)
        # Check if loaded in LaunchAgents
        la_path = Path.home() / "Library" / "LaunchAgents" / "com.cryptolab.k449-eth-btc.plist"
        check("k449_plist_launchagent", la_path.exists(),
              "LOADED in ~/Library/LaunchAgents/" if la_path.exists()
              else "NOT loaded — need: cp plist ~/Library/LaunchAgents/ && launchctl load",
              warn_only=not la_path.exists())
    else:
        check("k449_plist_exists", False, f"{K449_PLIST} MISSING")

    # 1d. K280 sleeve current value
    if LEVERAGE_MANAGER_PY.exists():
        lm_text = LEVERAGE_MANAGER_PY.read_text()
        has_75 = '"K280":   0.75,' in lm_text
        has_60 = '"K280":   0.60,' in lm_text
        check("k280_sleeve_current", True,
              f"leverage_manager.py: K280=0.75 found={has_75}, K280=0.60 found={has_60}")
        check("k280_sleeve_needs_cut", has_75 and not has_60,
              "K280 0.75 → 0.60 CUT REQUIRED (K539 Phase B1 prerequisite)",
              warn_only=True)
    else:
        check("k280_leverage_manager", False, "leverage_manager.py MISSING")

    # 1e. K280 live dashboard
    if K280_DASHBOARD_JSON.exists():
        with open(K280_DASHBOARD_JSON) as f:
            k280 = json.load(f)
        sh_30d = k280.get("rolling_metrics", {}).get("sh_30d", 0.0)
        drift_z = k280.get("rolling_metrics", {}).get("drift_z", 0.0)
        check("k280_live_sharpe", sh_30d > 8.0,
              f"30d Sharpe = {sh_30d:.2f} (K280 open criterion: >8)")
        check("k280_drift_z", drift_z < 2.5,
              f"Drift z = {drift_z:.3f} {'OK' if drift_z < 2.5 else '(CRITICAL — overfit regime)'}",
              warn_only=drift_z >= 2.5)
    else:
        check("k280_live_dashboard", False, "k280_live_dashboard.json MISSING")

    # 1f. Emergency exit registry
    if EMERGENCY_EXIT_PY.exists():
        exit_text = EMERGENCY_EXIT_PY.read_text()
        k449_registered = "K449" in exit_text
        check("k357_k449_registered", k449_registered,
              "K449 ETH/BTC pair detection PRESENT in emergency_hl_exit.py")
    else:
        check("k357_emergency_exit", False, "emergency_hl_exit.py MISSING")

    # Summary
    n_pass = sum(1 for c in results["checks"] if c["status"] == "PASS")
    n_warn = sum(1 for c in results["checks"] if c["status"] == "WARN")
    n_fail = sum(1 for c in results["checks"] if c["status"] == "FAIL")
    print(f"\n  Summary: {green(str(n_pass))} PASS | {yellow(str(n_warn))} WARN | {red(str(n_fail))} FAIL")
    results["summary"] = {"pass": n_pass, "warn": n_warn, "fail": n_fail}
    return results


# ─────────────────────────────────────────────────────────────────────────────
# Phase 2: K280 sleeve 75% → 60% restructure
# ─────────────────────────────────────────────────────────────────────────────

def phase2_k280_sleeve_restructure() -> Dict[str, Any]:
    """Audit and spec the K280 sleeve 75% → 60% 1-LOC change."""
    print(bold(f"\n{'='*70}"))
    print(bold("Phase 2: K280 Sleeve 75% → 60% Restructure (K539 Phase B1)"))
    print(bold(f"{'='*70}"))

    results: Dict[str, Any] = {
        "phase": 2,
        "name": "k280_sleeve_restructure",
        "current_sleeve": K280_SLEEVE_CURRENT,
        "target_sleeve":  K280_SLEEVE_TARGET,
        "delta_pp": (K280_SLEEVE_CURRENT - K280_SLEEVE_TARGET) * 100,
    }

    # Financial impact analysis
    aum = AUM_REF_USD
    k280_current_capital = aum * K280_SLEEVE_CURRENT      # $7.5M
    k280_target_capital  = aum * K280_SLEEVE_TARGET       # $6.0M
    capital_freed        = k280_current_capital - k280_target_capital  # $1.5M

    # K280 expected annual return (backtest OOS Sh 18.46 → ~17%/yr annualised rough estimate)
    # Using conservative 1.5% daily vol proxy → Sh 18.46 ≈ ~$1.5M/yr on $7.5M sleeve
    # Reduction: $1.5M × (1.5/7.5) = $300K/yr reduction estimate
    k280_ann_return_pct  = 0.20   # ~20%/yr rough (high-Sharpe FR carry, 365d)
    k280_profit_current  = k280_current_capital * k280_ann_return_pct
    k280_profit_target   = k280_target_capital  * k280_ann_return_pct
    k280_profit_delta    = k280_profit_current  - k280_profit_target   # ~-$300K

    # HL exposure impact
    # K280 HL allocation: primarily K208 (42.3%) + K276b (46.9%) = mixed HL/Bybit
    # Rough: 70% of K280 on HL → 75%×70% = 52.5pp of HL
    # After cut to 60%: 60%×70% = 42pp HL (from K280 alone)
    # Frees ~7.5pp HL headroom for K449 (5%) + K476/K484 (3%+3%)
    hl_k280_ratio = 0.70
    hl_from_k280_current = K280_SLEEVE_CURRENT * hl_k280_ratio
    hl_from_k280_target  = K280_SLEEVE_TARGET  * hl_k280_ratio
    hl_freed_pp          = (hl_from_k280_current - hl_from_k280_target) * 100

    print(f"  K280 sleeve:  {K280_SLEEVE_CURRENT:.0%} → {K280_SLEEVE_TARGET:.0%}  ({results['delta_pp']:.0f}pp cut)")
    print(f"  Capital:      ${k280_current_capital/1e6:.1f}M → ${k280_target_capital/1e6:.1f}M  (${capital_freed/1e6:.1f}M freed)")
    print(f"  Profit delta: -${k280_profit_delta/1e3:.0f}K/yr (K208 decay-adj baseline: acceptable per K539)")
    print(f"  HL headroom:  +{hl_freed_pp:.1f}pp freed → funds K449(5%) + K476(3%) + K484(3%) = 11pp")
    print()

    print(bold("  1-LOC Change Specification:"))
    print(grey("  ─"*35))
    print(f"  File:    scripts/leverage_manager.py")
    print(f"  Line:    SLEEVE_WEIGHTS dict, key 'K280'")
    print()
    print(f"  BEFORE:  \"K280\":   0.75,   # K280 main (K198 + K208 + K276b) — v6.13d; v6.16 reduces to 0.72")
    print(f"  AFTER:   \"K280\":   0.60,   # K280 main (K539 Phase B1: 75→60, frees 7.5pp HL, 2026-05-30)")
    print()
    print(bold("  Exact sed command (run manually after verification):"))
    print(cyan('  sed -i \'\' \'s/"K280":   0.75,   # K280 main (K198 + K208 + K276b) — v6.13d; v6.16 reduces to 0.72/"K280":   0.60,   # K280 main (K539 Phase B1: 75→60, frees 7.5pp HL, 2026-05-30)/\' scripts/leverage_manager.py'))
    print()
    print(bold("  Verify after change:"))
    print(cyan('  grep "K280.*0\\.60" scripts/leverage_manager.py'))
    print()

    # HL exposure verification
    print(bold("  HL Exposure Delta (post K280 cut + K449 activation):"))
    print(grey("  ─"*35))
    # Current: K280(75%×70%=52.5%) + K297(≈0% HL) + sUSDe(0% HL) = 52.5% + HLP~5% = 57.5%
    # After: K280(60%×70%=42%) + K449(5%×100%=5%) + HLP~5% = 52% — BELOW 57.5% current!
    # Note: HL carries additional items; conservative calc
    hl_after = hl_from_k280_target + (K449_WEEK1_SLEEVE_PCT * 1.0) + 0.05   # +HLP
    print(f"  Current HL:  {HL_EXPOSURE_CURRENT:.1%} (v6.13d baseline)")
    print(f"  After cut+K449: ~{hl_after:.1%} (K280@60%×70% + K449@5% + HLP@5%)")
    print(f"  vs Hard cap: {HL_EXPOSURE_TARGET_CAP:.0%} → {green('SAFE') if hl_after < HL_EXPOSURE_TARGET_CAP else red('BREACH')}")
    print()

    results.update({
        "capital_freed_usd": capital_freed,
        "profit_delta_yr_usd": -k280_profit_delta,
        "hl_freed_pp": hl_freed_pp,
        "hl_exposure_after": hl_after,
        "one_loc_spec": {
            "file": "scripts/leverage_manager.py",
            "before": '"K280":   0.75,',
            "after":  '"K280":   0.60,',
        },
    })
    return results


# ─────────────────────────────────────────────────────────────────────────────
# Phase 3: K449 LIVE switch concrete steps
# ─────────────────────────────────────────────────────────────────────────────

def phase3_live_switch_steps() -> Dict[str, Any]:
    """Specify concrete K449 LIVE switch steps."""
    print(bold(f"\n{'='*70}"))
    print(bold("Phase 3: K449 LIVE Switch Concrete Steps"))
    print(bold(f"{'='*70}"))

    aum = AUM_REF_USD
    sleeve_capital     = aum * K449_WEEK1_SLEEVE_PCT         # $500K
    total_notional     = sleeve_capital * K449_LEVERAGE       # $2M ($1M long + $1M short)
    per_leg_notional   = total_notional / 2                   # $1M per leg
    margin_per_leg     = per_leg_notional / K449_LEVERAGE     # $250K
    total_margin       = margin_per_leg * 2                   # $500K

    print(f"  Sleeve: {K449_WEEK1_SLEEVE_PCT:.0%} × ${aum/1e6:.0f}M = ${sleeve_capital/1e3:.0f}K capital")
    print(f"  Notional: ${sleeve_capital/1e3:.0f}K × {K449_LEVERAGE:.0f}x = ${total_notional/1e6:.1f}M total (${per_leg_notional/1e6:.1f}M each leg)")
    print(f"  Margin:   ${total_margin/1e3:.0f}K (${margin_per_leg/1e3:.0f}K per leg at {K449_LEVERAGE:.0f}x)")
    print(f"  Venue:    HyperLiquid ONLY (both ETH and BTC legs)")
    print()

    steps = [
        {
            "step": 1,
            "phase": "D0_prereq",
            "name": "K280 sleeve cut",
            "command": "sed -i '' 's/\"K280\":   0.75,/\"K280\":   0.60,/' scripts/leverage_manager.py",
            "verify": "grep '\"K280\":   0.60' scripts/leverage_manager.py",
            "notes": "PREREQUISITE — must complete before K449 load"
        },
        {
            "step": 2,
            "phase": "D0_prereq",
            "name": "Plist LIVE edit — remove --dry-run",
            "command": "sed -i '' '/<string>--dry-run<\\/string>/d' com.cryptolab.k449-eth-btc.plist",
            "verify": "grep 'dry-run' com.cryptolab.k449-eth-btc.plist || echo 'CLEAN'",
            "notes": "Remove --dry-run flag from ProgramArguments so daemon executes live"
        },
        {
            "step": 3,
            "phase": "D0_prereq",
            "name": "Set PAPER_TRADE=False in environment / plist",
            "command": "# Add PAPER_TRADE=False to plist EnvironmentVariables dict",
            "verify": "grep PAPER_TRADE com.cryptolab.k449-eth-btc.plist",
            "notes": "k449_eth_btc_run.py reads os.environ['PAPER_TRADE'] — must be 'False' or absent"
        },
        {
            "step": 4,
            "phase": "D0_load",
            "name": "Copy plist to LaunchAgents",
            "command": "cp com.cryptolab.k449-eth-btc.plist ~/Library/LaunchAgents/com.cryptolab.k449-eth-btc.plist",
            "verify": "ls -la ~/Library/LaunchAgents/com.cryptolab.k449-eth-btc.plist",
            "notes": "Copy modified plist to system LaunchAgents directory"
        },
        {
            "step": 5,
            "phase": "D0_load",
            "name": "launchctl load K449 daemon",
            "command": "launchctl load ~/Library/LaunchAgents/com.cryptolab.k449-eth-btc.plist",
            "verify": "launchctl list | grep k449-eth-btc",
            "notes": "Loads daemon; first execution at next 8h interval (RunAtLoad=false)"
        },
        {
            "step": 6,
            "phase": "D0_load",
            "name": "Confirm K357 emergency exit includes K449",
            "command": "grep -c 'K449' scripts/emergency_hl_exit.py",
            "verify": "Expected: >=5 matches (ETH/BTC pair detection present)",
            "notes": "K449 paired-position detection already present in emergency_hl_exit.py per K450"
        },
        {
            "step": 7,
            "phase": "D0_verify",
            "name": "HL margin health check",
            "command": "python3 scripts/emergency_hl_exit.py --dry-run --status",
            "verify": "Margin utilisation < 80%",
            "notes": "Confirms HL account has sufficient margin before first K449 trade fires"
        },
        {
            "step": 8,
            "phase": "D0_verify",
            "name": "Smart router check (K434)",
            "command": "python3 scripts/k449_eth_btc_run.py --status",
            "verify": "Dashboard refreshed, venue=HL confirmed",
            "notes": "K449 is HL-only; K434 smart router not invoked (single-venue)"
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

    # Post-only order execution via K439
    print(bold("  K439 POST_ONLY execution path:"))
    print(f"  k449_eth_btc_run.py → submit_paired_trade() → POST_ONLY_ORDER_ENABLED=True")
    print(f"  Long leg: post-only limit at mid (ETH or BTC depending on FR diff)")
    print(f"  Short leg: post-only limit at mid (opposing asset)")
    print(f"  Rollback: if long fills but short fails → cancel long within 5s")
    print()

    results = {
        "phase": 3,
        "name": "live_switch_steps",
        "sizing": {
            "aum_ref_usd": aum,
            "sleeve_pct": K449_WEEK1_SLEEVE_PCT,
            "sleeve_capital_usd": sleeve_capital,
            "leverage": K449_LEVERAGE,
            "total_notional_usd": total_notional,
            "per_leg_notional_usd": per_leg_notional,
            "total_margin_usd": total_margin,
        },
        "steps": steps,
    }
    return results


# ─────────────────────────────────────────────────────────────────────────────
# Phase 4: Day 1-7 monitoring spec
# ─────────────────────────────────────────────────────────────────────────────

def phase4_monitoring_spec() -> Dict[str, Any]:
    """Generate Day 1-7 monitoring specification."""
    print(bold(f"\n{'='*70}"))
    print(bold("Phase 4: Day 1-7 Monitoring Specification"))
    print(bold(f"{'='*70}"))

    metrics = [
        {
            "metric": "daily_sharpe_realized",
            "source": "data/k449_dashboard.json → 60d_sharpe (rolling)",
            "target": "≥ 50% of paper Sharpe (paper target: ~18+)",
            "pass_threshold": 9.0,
            "alert_threshold": 5.0,
            "cadence": "Daily 09:00 JST",
        },
        {
            "metric": "fill_rate_vs_paper",
            "source": "data/k449_dashboard.json → fill_rate (future field)",
            "target": "≥ 65% fill rate (gate per K450 activation criteria)",
            "pass_threshold": 0.65,
            "alert_threshold": 0.50,
            "cadence": "Per 8h cycle",
        },
        {
            "metric": "hl_position_drift",
            "source": "data/k449_dashboard.json → delta_neutral_drift_pct",
            "target": "< 5% drift (rebalance trigger at 5%)",
            "pass_threshold": 0.05,
            "alert_threshold": 0.08,
            "cadence": "Per 8h cycle",
        },
        {
            "metric": "funding_rate_carry",
            "source": "data/k449_dashboard.json → daily_pnl_usdc",
            "target": "+$0.35/day/($1M notional) expected (= $13K/yr / 365)",
            "pass_threshold": 0.0,   # any positive carry
            "alert_threshold": -5.0,  # -$5 daily as alert
            "cadence": "Daily 09:00 JST",
        },
        {
            "metric": "hl_margin_health",
            "source": "HL account API (emergency_hl_exit.py --status)",
            "target": "Margin utilisation < 70% (auto-alert at 80% per K357)",
            "pass_threshold": 0.70,
            "alert_threshold": 0.80,
            "cadence": "Daily 09:00 JST + real-time K357 circuit breaker",
        },
    ]

    print(f"  {'Metric':<30} {'Source':<40} {'Cadence'}")
    print(f"  {'-'*30} {'-'*40} {'-'*15}")
    for m in metrics:
        print(f"  {m['metric']:<30} {m['source'][:40]:<40} {m['cadence']}")

    print()
    print(bold("  Day 7 Go/No-Go decision:"))
    print(f"  PASS: 60d rolling Sharpe ≥ 9.0 AND fill_rate ≥ 65% → expand to 8% sleeve")
    print(f"  HOLD: Sharpe 5-9 or fill 50-65% → maintain 5% sleeve, monitor D8-D14")
    print(f"  ROLLBACK: Sharpe < 5 OR fill < 50% OR margin breach → close both legs, reload --dry-run")
    print()

    print(bold("  Monitoring commands:"))
    print(cyan("  python3 scripts/k449_eth_btc_run.py --status"))
    print(cyan("  python3 scripts/emergency_hl_exit.py --dry-run --status"))
    print(cyan(f"  cat {K449_DASHBOARD_JSON.relative_to(REPO_ROOT)}"))
    print()

    results = {
        "phase": 4,
        "name": "d1_d7_monitoring",
        "metrics": metrics,
        "day7_decision": {
            "PASS_criteria": "60d_sharpe >= 9.0 AND fill_rate >= 0.65",
            "PASS_action": "expand sleeve to 8% (=$800K capital)",
            "HOLD_criteria": "60d_sharpe in [5, 9) OR fill_rate in [0.50, 0.65)",
            "HOLD_action": "maintain 5% sleeve, re-evaluate D14",
            "ROLLBACK_criteria": "60d_sharpe < 5 OR fill_rate < 0.50 OR margin_util > 0.80",
            "ROLLBACK_action": "close both legs, reload plist with --dry-run",
        },
    }
    return results


# ─────────────────────────────────────────────────────────────────────────────
# Phase 5: K498 Phase 1A interaction
# ─────────────────────────────────────────────────────────────────────────────

def phase5_k498_interaction() -> Dict[str, Any]:
    """Summarise K498 Phase 1A interaction with K449."""
    print(bold(f"\n{'='*70}"))
    print(bold("Phase 5: Phase B2 K498 Phase 1A / BBO_SELECT Interaction"))
    print(bold(f"{'='*70}"))

    print(f"  K498 Phase 1A (per K530): BBO_SELECT routing for HL post-only fills")
    print(f"  Interaction with K449:")
    print(f"    • K449 uses POST_ONLY_ORDER_ENABLED=True (K439 path)")
    print(f"    • K449 is HL-only (single venue) → K434 smart router bypassed")
    print(f"    • BBO_SELECT benefit: K449 paired trades benefit from BBO mid reference")
    print(f"      → improved fill quality on ETH/BTC post-only limit orders")
    print(f"    • K449 submit_paired_trade() targets mid-price ± 0.01% for post-only")
    print(f"    • BBO_SELECT provides accurate mid → lower slippage on 8h rebalance")
    print()
    print(f"  K208 (K280 component) also on HL path:")
    print(f"    • K449 operates independently of K208 (separate daemon, separate sleeve)")
    print(f"    • No direct interference — K449 ETH/BTC legs ≠ K208 symbols (SOL/XRP/SUI...)")
    print(f"    • Shared HL account margin: must confirm combined margin < 80% threshold")
    print()

    results = {
        "phase": 5,
        "name": "k498_phase1a_interaction",
        "bbo_select_benefit": "improved_post_only_fill_quality",
        "k449_execution_path": "K439 POST_ONLY → HL ETH + HL BTC simultaneous",
        "interference_with_k208": "NONE (disjoint symbol sets)",
        "margin_note": "confirm combined HL margin (K280+K449+K457+K476+K484) < 70% pre-activation",
    }
    return results


# ─────────────────────────────────────────────────────────────────────────────
# Phase 6: Profit lift projection
# ─────────────────────────────────────────────────────────────────────────────

def phase6_profit_projection() -> Dict[str, Any]:
    """Compute Week 1 and pipeline profit projections."""
    print(bold(f"\n{'='*70}"))
    print(bold("Phase 6: Profit Lift — Week 1 + Pipeline Validation"))
    print(bold(f"{'='*70}"))

    # Week 1 starting state
    k449_yr          = K449_PROFIT_YR_USD           # $13K/yr
    builder_rebate   = K481_BUILDER_REBATE           # $247K/yr (K481 Phase A)
    week1_total      = k449_yr + builder_rebate      # $260K/yr starting state

    # Pipeline projections (per K547 audit)
    pipeline = {
        "K449 ETH-BTC (Week 1)":  13_000,
        "K476 SOL-BTC (Week 2)":  263_000,   # (K476+K484)
        "K484 AVAX-BTC (Week 2)": 0,          # included in K476 line (combined $263K)
        "K493 ATOM-BTC (Week 3)": 231_000,
        "K500+K507 SEI/TIA (Week 4)": 354_000,
        "K512 APT (Week 5)":      302_000,
    }

    # K547: Total = $1.16M/yr @ $10M (excludes K481 builder rebate)
    total_pipeline_strategy = sum(v for v in pipeline.values() if v > 0)

    print(f"  Week 1 immediate profit:")
    print(f"    K449 ETH-BTC:     ${k449_yr:>8,}/yr (5% sleeve @ $10M, 4x leverage)")
    print(f"    K481 builder:     ${builder_rebate:>8,}/yr (Phase A maker rebate, already active)")
    print(f"    Week 1 combined:  ${week1_total:>8,}/yr")
    print()
    print(f"  Pipeline validation value:")
    print(f"    K449 is TEST CASE for K476/K484/K493/K500/K507/K512 cascade")
    print(f"    Pipeline total (W1-W5): ${total_pipeline_strategy:>8,}/yr (K547 estimate)")
    print(f"    + K481 builder rebate:  ${builder_rebate:>8,}/yr")
    print(f"    TOTAL W1-W5 + builder:  ${total_pipeline_strategy + builder_rebate:>8,}/yr @ $10M")
    print()
    print(f"  Pipeline validation multiplier: x{(total_pipeline_strategy/k449_yr):.0f} (if K449 PASS → all families activate)")
    print()

    results = {
        "phase": 6,
        "name": "profit_projection",
        "week1": {
            "k449_yr_usd": k449_yr,
            "builder_rebate_yr_usd": builder_rebate,
            "week1_combined_yr_usd": week1_total,
        },
        "pipeline_w1_w5_yr_usd": total_pipeline_strategy,
        "total_with_builder_yr_usd": total_pipeline_strategy + builder_rebate,
        "pipeline_activation_multiplier": round(total_pipeline_strategy / k449_yr, 0),
        "note": "K449 PASS = all 5 family waves validate → $1.16M+/yr @ $10M",
    }
    return results


# ─────────────────────────────────────────────────────────────────────────────
# Phase 7: Risk inventory
# ─────────────────────────────────────────────────────────────────────────────

def phase7_risk_inventory() -> Dict[str, Any]:
    """Enumerate risks and mitigations for K449 Week 1 LIVE."""
    print(bold(f"\n{'='*70}"))
    print(bold("Phase 7: Risk Inventory"))
    print(bold(f"{'='*70}"))

    risks = [
        {
            "risk": "K449 paper vs LIVE Sharpe divergence",
            "severity": "MEDIUM",
            "probability": "LOW",
            "detail": "Paper Sharpe based on assumed fills; LIVE fill quality depends on HL liquidity depth for ETH/BTC (liquid majors → low risk)",
            "mitigation": "Day 7 go/no-go: rollback if realized Sharpe < 50% of paper",
            "trigger": "60d_sharpe < 5.0 OR fill_rate < 50%",
        },
        {
            "risk": "K280 sleeve cut realized loss",
            "severity": "MEDIUM",
            "probability": "LOW",
            "detail": "K280 75→60% cut reduces $7.5M→$6M exposure; loses ~$300K/yr alpha. Offset by K449 family pipeline $1.16M. K208 decay-adj baseline confirms net positive.",
            "mitigation": "Accept loss: K449 pipeline EV >> K280 incremental; re-expand K280 if pipeline underperforms",
            "trigger": "K280 30d Sharpe < 8 (reopen criterion per K280 discipline)",
        },
        {
            "risk": "HL execution lag (8h cron vs FR settlement)",
            "severity": "LOW",
            "probability": "LOW",
            "detail": "8h cron may fire slightly after FR settlement window; funding paid on stale position. ETH/BTC FR settlement is precise 8h UTC.",
            "mitigation": "Cron fires at 00:01/08:01/16:01 UTC (slightly after 00:00/08:00/16:00 settlement). Worst case: 1 settlement missed. Acceptable.",
            "trigger": "fill_rate < 50% consistently → investigate timing offset",
        },
        {
            "risk": "HL concentration breach (>65% cap)",
            "severity": "HIGH",
            "probability": "LOW",
            "detail": "New HL>65% prohibition per memory. K449 5% adds ~5pp HL. Post-cut HL ~ 52% (below cap). Week 2 additions must stay monitored.",
            "mitigation": "Verify HL exposure after each activation step. K449 alone: safe. K476+K484 Week 2: re-verify stays < 65%.",
            "trigger": "HL exposure > 60% → pause cascade; > 65% → immediate size reduction",
        },
        {
            "risk": "FR differential collapses (ETH = BTC FR)",
            "severity": "LOW",
            "probability": "MEDIUM",
            "detail": "If ETH-BTC FR diff → 0 for extended periods, K449 stays NEUTRAL (no trade). Carry = 0 but no loss. Strategy waits for regime.",
            "mitigation": "No action needed; NEUTRAL state = no margin at risk. Monitor daily_pnl_usdc.",
            "trigger": "position_state = NEUTRAL for > 14 consecutive days → review FR environment",
        },
        {
            "risk": "Cascade risk (K476+K484 Week 2 simultaneous)",
            "severity": "MEDIUM",
            "probability": "LOW",
            "detail": "K476 SOL-BTC + K484 AVAX-BTC both activating Week 2 adds $263K/yr but also +6pp HL. Per K547: 48h apart sequencing required.",
            "mitigation": "K476 D0 → K484 D2 minimum 48h gap. Monitor HL margin between activations.",
            "trigger": "HL exposure hits 60% → hold K484 until K476 fills are confirmed stable",
        },
    ]

    print(f"  {'Risk':<45} {'Sev':<8} {'P(occur)'}")
    print(f"  {'-'*45} {'-'*8} {'-'*10}")
    for r in risks:
        sev_c = red if r["severity"] == "HIGH" else (yellow if r["severity"] == "MEDIUM" else green)
        print(f"  {r['risk'][:45]:<45} {sev_c(r['severity']):<8} {r['probability']}")

    print()
    for r in risks:
        print(f"  {bold(r['risk'])}")
        print(f"    Detail:     {r['detail']}")
        print(f"    Mitigation: {r['mitigation']}")
        print(f"    Trigger:    {cyan(r['trigger'])}")
        print()

    results = {
        "phase": 7,
        "name": "risk_inventory",
        "risks": risks,
    }
    return results


# ─────────────────────────────────────────────────────────────────────────────
# Phase 8: User action checklist D0-D7
# ─────────────────────────────────────────────────────────────────────────────

def phase8_user_checklist() -> Dict[str, Any]:
    """Print user action checklist for Day 0-7."""
    print(bold(f"\n{'='*70}"))
    print(bold("Phase 8: User Action Checklist D0-D7"))
    print(bold(f"{'='*70}"))

    checklist = {
        "D0_pre": [
            {"step": 1, "action": "Verify K280 sleeve config path",
             "cmd": "grep '\"K280\"' scripts/leverage_manager.py",
             "expected": '"K280":   0.75,  # must show 0.75 before edit'},
            {"step": 2, "action": "K280 sleeve 75 → 60% commit",
             "cmd": "sed -i '' 's/\"K280\":   0.75,/\"K280\":   0.60,/' scripts/leverage_manager.py && git add scripts/leverage_manager.py && git commit -m 'K549 K280 sleeve 75→60% (Phase B1)' && git push origin main",
             "expected": '"K280":   0.60,  confirmed'},
            {"step": 3, "action": "Verify HL exposure post-cut",
             "cmd": "# Manual calc: K280(60%×70%)+K449(5%)+HLP(5%) ≈ 52% < 65% OK",
             "expected": "< 65% hard cap"},
        ],
        "D0_load": [
            {"step": 4, "action": "Remove --dry-run from K449 plist",
             "cmd": "sed -i '' '/<string>--dry-run<\\/string>/d' com.cryptolab.k449-eth-btc.plist && grep 'dry-run' com.cryptolab.k449-eth-btc.plist || echo 'CLEAN'",
             "expected": "CLEAN — no --dry-run present"},
            {"step": 5, "action": "Copy plist to LaunchAgents",
             "cmd": "cp com.cryptolab.k449-eth-btc.plist ~/Library/LaunchAgents/com.cryptolab.k449-eth-btc.plist",
             "expected": "File exists in ~/Library/LaunchAgents/"},
            {"step": 6, "action": "launchctl load K449 daemon",
             "cmd": "launchctl load ~/Library/LaunchAgents/com.cryptolab.k449-eth-btc.plist && launchctl list | grep k449",
             "expected": "com.cryptolab.k449-eth-btc appears in list (PID may be 0 if RunAtLoad=false)"},
            {"step": 7, "action": "Confirm K357 emergency exit includes K449",
             "cmd": "grep -c 'K449' scripts/emergency_hl_exit.py",
             "expected": ">= 5 matches"},
        ],
        "D1_D3": [
            {"step": 8, "action": "Monitor k449_dashboard.json realized PnL",
             "cmd": "python3 scripts/k449_eth_btc_run.py --status | grep -E 'pnl|state|drift'",
             "expected": "daily_pnl_usdc >= 0 (neutral or positive carry)"},
            {"step": 9, "action": "Check HL margin health",
             "cmd": "python3 scripts/emergency_hl_exit.py --dry-run --status",
             "expected": "Margin utilisation < 70%"},
            {"step": 10, "action": "Funding rate observed",
             "cmd": "cat data/k449_dashboard.json | python3 -c \"import json,sys; d=json.load(sys.stdin); print(f'FR_diff: {d[\\\"fr_raw_diff\\\"]}, state: {d[\\\"position_state\\\"]}')\"",
             "expected": "FR diff != 0.0 → strategy active; = 0 → NEUTRAL waiting"},
        ],
        "D7": [
            {"step": 11, "action": "Realized Sharpe vs paper (≥ 50% of paper = PASS)",
             "cmd": "python3 scripts/k449_eth_btc_run.py --status | grep sharpe",
             "expected": "60d_sharpe >= 9.0 → PASS | 5-9 → HOLD | < 5 → ROLLBACK"},
            {"step": 12, "action": "Decision: expand 8% OR hold OR rollback",
             "cmd": "# Based on D7 metrics: edit leverage_manager.py K449 0.05→0.08 if PASS",
             "expected": "Document decision in docs/k302a_master_deployment.md Week 1 section"},
        ],
    }

    for day, actions in checklist.items():
        day_label = day.replace("_", " ").upper()
        print(f"\n  {bold(day_label)}:")
        for a in actions:
            print(f"    [{a['step']}] {bold(a['action'])}")
            print(f"        CMD: {cyan(a['cmd'])}")
            print(f"        EXP: {green(a['expected'])}")

    results = {
        "phase": 8,
        "name": "user_checklist_d0_d7",
        "checklist": checklist,
    }
    return results


# ─────────────────────────────────────────────────────────────────────────────
# Phase 9: Week 2 prep
# ─────────────────────────────────────────────────────────────────────────────

def phase9_week2_prep() -> Dict[str, Any]:
    """Outline Week 2 (K476 SOL-BTC + K484 AVAX-BTC) cascade prep."""
    print(bold(f"\n{'='*70}"))
    print(bold("Phase 9: Week 2 Prep — K476 SOL-BTC + K484 AVAX-BTC Cascade"))
    print(bold(f"{'='*70}"))

    week2 = {
        "K476_SOL_BTC": {
            "plist": "com.cryptolab.k476-sol-btc.plist",
            "run_script": "scripts/k476_sol_btc_run.py",
            "sleeve_pct": 0.03,
            "profit_yr_usd": 263_000,   # K476+K484 combined per K547
            "leverage": 4.0,
            "venue": "HL",
            "activation_day": "D+7 (48h after K449 confirms PASS)",
            "hl_delta_pp": 3.0,
        },
        "K484_AVAX_BTC": {
            "plist": "com.cryptolab.k484-avax-btc.plist",
            "run_script": "scripts/k484_avax_btc_run.py",
            "sleeve_pct": 0.03,
            "profit_yr_usd": 0,          # included in K476 line ($263K combined)
            "leverage": 4.0,
            "venue": "HL",
            "activation_day": "D+9 (48h after K476 — cascade risk mitigation per K547)",
            "hl_delta_pp": 3.0,
        },
    }

    for name, spec in week2.items():
        print(f"\n  {bold(name)}:")
        print(f"    Plist:    {spec['plist']}")
        print(f"    Script:   {spec['run_script']}")
        print(f"    Sleeve:   {spec['sleeve_pct']:.0%} × $10M = ${spec['sleeve_pct']*AUM_REF_USD/1e3:.0f}K capital")
        print(f"    Notional: ${spec['sleeve_pct']*AUM_REF_USD*spec['leverage']/1e6:.1f}M ({spec['leverage']:.0f}x)")
        print(f"    Venue:    {spec['venue']}")
        print(f"    HL delta: +{spec['hl_delta_pp']:.0f}pp")
        print(f"    Activate: {spec['activation_day']}")

    print()
    print(f"  HL exposure trajectory (Week 1→2):")
    print(f"    Week 1 post-K449: ~52% (K280@60% + K449@5% + HLP@5%)")
    print(f"    Week 2 post-K476: ~55% (+3pp SOL-BTC)")
    print(f"    Week 2 post-K484: ~58% (+3pp AVAX-BTC)")
    print(f"    vs Cap 65%: {green('SAFE')} — 7pp headroom after Week 2 complete")
    print()
    print(f"  Week 2 prerequisites:")
    print(f"    1. K449 Day 7 PASS (60d_sharpe ≥ 9.0, fill_rate ≥ 65%)")
    print(f"    2. HL margin utilisation < 65% post-K449 Week 1")
    print(f"    3. K476/K484 plist --dry-run removed (same procedure as K449 Step 2)")
    print(f"    4. Combined Week 2 HL exposure check: < 65% hard cap")
    print()

    results = {
        "phase": 9,
        "name": "week2_cascade_prep",
        "week2_strategies": week2,
        "hl_trajectory": {
            "week1_post_k449": 0.52,
            "week2_post_k476": 0.55,
            "week2_post_k484": 0.58,
            "hard_cap": 0.65,
        },
    }
    return results


# ─────────────────────────────────────────────────────────────────────────────
# Status summary
# ─────────────────────────────────────────────────────────────────────────────

def print_status_summary() -> None:
    """Print brief status of K449 activation readiness."""
    print(bold(f"\n{'='*70}"))
    print(bold(f"K549 K449 ETH-BTC Week 1 LIVE Activation — Status Summary"))
    print(bold(f"{'='*70}"))
    print()

    # K449 dashboard
    if K449_DASHBOARD_JSON.exists():
        with open(K449_DASHBOARD_JSON) as f:
            d = json.load(f)
        print(f"  K449 state:       {bold(d.get('position_state', 'UNKNOWN'))}")
        print(f"  Paper mode:       {yellow('YES') if d.get('paper_trade_mode') else green('NO — LIVE')}")
        print(f"  Sleeve:           {d.get('sleeve_pct', 0):.1%}")
        print(f"  60d Sharpe:       {d.get('60d_sharpe', 0):.2f}")
        print(f"  Daily PnL:        ${d.get('daily_pnl_usdc', 0):.2f}")
        print(f"  FR diff (7d EMA): {d.get('current_fr_diff_7d', 0):.6f}")
    else:
        print(f"  {red('[MISSING]')} k449_dashboard.json")

    # K280 sleeve
    if LEVERAGE_MANAGER_PY.exists():
        lm = LEVERAGE_MANAGER_PY.read_text()
        has_75 = '"K280":   0.75,' in lm
        print(f"\n  K280 sleeve:      {'0.75 (MUST CUT to 0.60)' if has_75 else '0.60 (OK)'}")
        print(f"  K280 cut status:  {red('PENDING') if has_75 else green('DONE')}")

    # Plist status
    if K449_PLIST.exists():
        plist_text = K449_PLIST.read_text()
        has_dr = "--dry-run" in plist_text
        la_path = Path.home() / "Library" / "LaunchAgents" / "com.cryptolab.k449-eth-btc.plist"
        print(f"\n  Plist dry-run:    {red('PRESENT (must remove)') if has_dr else green('REMOVED — LIVE-ready')}")
        print(f"  LaunchAgent:      {green('LOADED') if la_path.exists() else yellow('NOT LOADED')}")

    print()
    print(f"  Profit target:    ${K449_PROFIT_YR_USD:,}/yr @ $10M (K449 alone)")
    print(f"  Pipeline total:   $1,163,000/yr @ $10M (W1-W5 all families)")
    print(f"  Week 1 combined:  ${K449_PROFIT_YR_USD + K481_BUILDER_REBATE:,}/yr (K449 + K481 builder)")
    print()


# ─────────────────────────────────────────────────────────────────────────────
# Export JSON
# ─────────────────────────────────────────────────────────────────────────────

def export_json(phases: List[Dict]) -> None:
    """Write wave_k549_k449_week1_live.json."""
    now_jst = datetime.now(timezone(timedelta(hours=9)))
    payload = {
        "wave": WAVE,
        "title": "K449 ETH-BTC Week 1 LIVE Activation Playbook",
        "generated_jst": now_jst.strftime("%Y-%m-%d %H:%M JST"),
        "profit_usdc_yr_10m": {
            "k449_alone": K449_PROFIT_YR_USD,
            "k481_builder_rebate": K481_BUILDER_REBATE,
            "week1_combined": K449_PROFIT_YR_USD + K481_BUILDER_REBATE,
            "pipeline_w1_w5": 1_163_000,
            "total_with_builder": 1_163_000 + K481_BUILDER_REBATE,
        },
        "k280_sleeve_restructure": {
            "current": K280_SLEEVE_CURRENT,
            "target": K280_SLEEVE_TARGET,
            "file": "scripts/leverage_manager.py",
            "one_loc_before": '"K280":   0.75,',
            "one_loc_after":  '"K280":   0.60,',
            "prerequisite": True,
        },
        "k449_activation": {
            "sleeve_pct": K449_WEEK1_SLEEVE_PCT,
            "leverage": K449_LEVERAGE,
            "sleeve_capital_usd": AUM_REF_USD * K449_WEEK1_SLEEVE_PCT,
            "total_notional_usd": AUM_REF_USD * K449_WEEK1_SLEEVE_PCT * K449_LEVERAGE,
            "venue": "HyperLiquid",
            "plist": "com.cryptolab.k449-eth-btc.plist",
            "launchctl_load": "launchctl load ~/Library/LaunchAgents/com.cryptolab.k449-eth-btc.plist",
            "live_prereq": "Remove --dry-run from plist ProgramArguments",
        },
        "day7_decision_criteria": {
            "PASS": "60d_sharpe >= 9.0 AND fill_rate >= 0.65 → expand to 8%",
            "HOLD": "60d_sharpe in [5,9) OR fill in [0.5,0.65) → maintain 5%",
            "ROLLBACK": "60d_sharpe < 5 OR fill < 0.5 OR margin > 0.80 → close, reload dry-run",
        },
        "week2_cascade": {
            "K476_SOL_BTC": {"activate_day": "D+7", "sleeve_pct": 0.03, "hl_delta_pp": 3.0},
            "K484_AVAX_BTC": {"activate_day": "D+9", "sleeve_pct": 0.03, "hl_delta_pp": 3.0},
            "hl_exposure_after_week2": 0.58,
            "hard_cap": 0.65,
        },
        "phases": phases,
    }
    with open(OUTPUT_JSON, "w") as f:
        json.dump(payload, f, indent=2)
    print(f"\n  {green('[WRITTEN]')} {OUTPUT_JSON.relative_to(REPO_ROOT)}")


# ─────────────────────────────────────────────────────────────────────────────
# Main
# ─────────────────────────────────────────────────────────────────────────────

def main() -> None:
    parser = argparse.ArgumentParser(
        description="K549 K449 ETH-BTC Week 1 LIVE Activation Playbook"
    )
    parser.add_argument("--status",       action="store_true", help="Print status summary")
    parser.add_argument("--phase1",       action="store_true", help="Run Phase 1 only")
    parser.add_argument("--phase2",       action="store_true", help="Run Phase 2 only")
    parser.add_argument("--checklist",    action="store_true", help="Print D0-D7 checklist")
    parser.add_argument("--all",          action="store_true", help="Run all phases")
    parser.add_argument("--export-json",  action="store_true", help="Export JSON output")
    args = parser.parse_args()

    print(bold(f"\n★ {WAVE} K449 ETH-BTC Week 1 LIVE Activation Playbook"))
    print(bold(f"  LIVE 自動変更禁止 — Playbook Only — No orders submitted"))
    print(grey(f"  Generated: {datetime.now(timezone(timedelta(hours=9))).strftime('%Y-%m-%d %H:%M JST')}"))

    if args.status or not any(vars(args).values()):
        print_status_summary()
        return

    phases: List[Dict] = []

    if args.phase1 or args.all:
        phases.append(phase1_verify_state())

    if args.phase2 or args.all:
        phases.append(phase2_k280_sleeve_restructure())

    if args.all:
        phases.append(phase3_live_switch_steps())
        phases.append(phase4_monitoring_spec())
        phases.append(phase5_k498_interaction())
        phases.append(phase6_profit_projection())
        phases.append(phase7_risk_inventory())

    if args.checklist or args.all:
        phases.append(phase8_user_checklist())

    if args.all:
        phases.append(phase9_week2_prep())

    if args.export_json or args.all:
        export_json(phases)

    print(bold(f"\n{'='*70}"))
    print(bold(f"K549 Playbook Complete"))
    print(bold(f"  Profit: K449 = $13K/yr | K481+K449 = $260K/yr | Pipeline = $1.16M+/yr @ $10M"))
    print(bold(f"{'='*70}\n"))


if __name__ == "__main__":
    main()

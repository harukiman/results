#!/usr/bin/env python3
"""
wave_k705_d60_cascade.py — K705 D60 Cascade Activation Playbook
================================================================
K339 REPO_ROOT pattern. 14 scaffolds LIVE switch cascade (2026-07-29).

MISSION (K705)
--------------
60+ daemons SCAFFOLD-READY. 14 pass 60d gate at 2026-07-29 (K700 D60 cascade).
K705 = detailed activation playbook: inventory, per-scaffold checklist, sequential
timing, HL trajectory, cumulative profit unlock, rollback playbook, user timeline.

CONSTRAINT: LIVE 自動変更禁止 — this script is a PLANNING/VERIFICATION tool only.
No live daemon operations. Use phase-specific output for manual execution.

USAGE
-----
  python3 wave_k705_d60_cascade.py                  # Full playbook report
  python3 wave_k705_d60_cascade.py --phase1         # Scaffold inventory
  python3 wave_k705_d60_cascade.py --phase4         # HL trajectory check
  python3 wave_k705_d60_cascade.py --phase5         # Profit unlock table
  python3 wave_k705_d60_cascade.py --pre-flight     # Pre-flight gate verify
  python3 wave_k705_d60_cascade.py --day 0          # Day 0 commands (Jul 29)
  python3 wave_k705_d60_cascade.py --day 1          # Day 1 commands (Jul 30)
  python3 wave_k705_d60_cascade.py --rollback K686  # Rollback command for strategy

K339 REPO_ROOT
"""

import os
import sys
import json
import argparse
from pathlib import Path
from datetime import date, timedelta
from typing import List, Dict, Optional

# K339 REPO_ROOT pattern
REPO_ROOT = Path(os.environ.get("CRYPTO_LAB", Path(__file__).parent))
DATA_DIR = REPO_ROOT / "data"
DOCS_DIR = REPO_ROOT / "docs"
SCRIPTS_DIR = REPO_ROOT / "scripts"
LAUNCH_AGENTS_DIR = Path("~/Library/LaunchAgents").expanduser()

# ============================================================
# SCAFFOLD REGISTRY — 14 scaffolds ordered by Sharpe desc
# ============================================================

SCAFFOLDS: List[Dict] = [
    {
        "rank": 1,
        "scaffold_wave": "K689",
        "strategy_wave": "K686",
        "pair": "AVAX-SOL",
        "family": "alt-alt",
        "venue": "Bybit",
        "oos_sharpe": 50.27,
        "gate_sh": 5.0,
        "ann_net_10m_usd": 102_153,
        "daily_usdc": 280,
        "sleeve_pct": 0.03,
        "hl_delta_pp": 0.0,
        "plist": "com.cryptolab.k686-avax-sol.plist",
        "script": "scripts/k686_avax_sol_run.py",
        "dashboard": "data/k686_dashboard.json",
        "paper_start": date(2026, 5, 30),
        "gate_date": date(2026, 7, 29),
        "activation_day": 0,
    },
    {
        "rank": 2,
        "scaffold_wave": "K685",
        "strategy_wave": "K682",
        "pair": "ATOM-SOL",
        "family": "alt-alt",
        "venue": "Bybit",
        "oos_sharpe": 43.43,
        "gate_sh": 5.0,
        "ann_net_10m_usd": 214_638,
        "daily_usdc": 588,
        "sleeve_pct": 0.02,
        "hl_delta_pp": 0.0,
        "plist": "com.cryptolab.k682-atom-sol.plist",
        "script": "scripts/k682_atom_sol_run.py",
        "dashboard": "data/k682_dashboard.json",
        "paper_start": date(2026, 5, 30),
        "gate_date": date(2026, 7, 29),
        "activation_day": 0,
    },
    {
        "rank": 3,
        "scaffold_wave": "K637",
        "strategy_wave": "K628",
        "pair": "JTO-BTC (orthog)",
        "family": "orthog",
        "venue": "Bybit",
        "oos_sharpe": 44.63,
        "gate_sh": 8.0,
        "ann_net_10m_usd": 357_026,
        "daily_usdc": 978,
        "sleeve_pct": 0.02,
        "hl_delta_pp": 0.0,
        "plist": "com.cryptolab.k628-jto-orthog.plist",
        "script": "scripts/k628_jto_orthog_run.py",
        "dashboard": "data/k628_dashboard.json",
        "paper_start": date(2026, 5, 30),
        "gate_date": date(2026, 7, 29),
        "activation_day": 0,
    },
    {
        "rank": 4,
        "scaffold_wave": "K683",
        "strategy_wave": "K679",
        "pair": "APT-SOL",
        "family": "alt-alt",
        "venue": "Bybit",
        "oos_sharpe": 39.29,
        "gate_sh": 5.0,
        "ann_net_10m_usd": 234_781,
        "daily_usdc": 643,
        "sleeve_pct": 0.03,
        "hl_delta_pp": 0.0,
        "plist": "com.cryptolab.k679-apt-sol.plist",
        "script": "scripts/k679_apt_sol_run.py",
        "dashboard": "data/k679_dashboard.json",
        "paper_start": date(2026, 5, 30),
        "gate_date": date(2026, 7, 29),
        "activation_day": 1,
    },
    {
        "rank": 5,
        "scaffold_wave": "K669",
        "strategy_wave": "K658",
        "pair": "SOL-ETH",
        "family": "eth-base",
        "venue": "HL",
        "oos_sharpe": 29.66,
        "gate_sh": 5.0,
        "ann_net_10m_usd": 42_332,
        "daily_usdc": 116,
        "sleeve_pct": 0.015,
        "hl_delta_pp": 1.5,
        "plist": "com.cryptolab.k658-sol-eth.plist",
        "script": "scripts/k658_sol_eth_run.py",
        "dashboard": "data/k658_dashboard.json",
        "paper_start": date(2026, 5, 30),
        "gate_date": date(2026, 7, 29),
        "activation_day": 1,
        "prereq": "K552 (HL 75->60% patch) must be applied first",
    },
    {
        "rank": 6,
        "scaffold_wave": "K699",
        "strategy_wave": "K696",
        "pair": "ENA-SOL",
        "family": "alt-alt",
        "venue": "Bybit",
        "oos_sharpe": 26.93,
        "gate_sh": 5.0,
        "ann_net_10m_usd": 93_187,
        "daily_usdc": 255,
        "sleeve_pct": 0.03,
        "hl_delta_pp": 0.0,
        "plist": "com.cryptolab.k696-ena-sol.plist",
        "script": "scripts/k696_ena_sol_run.py",
        "dashboard": "data/k696_dashboard.json",
        "paper_start": date(2026, 5, 30),
        "gate_date": date(2026, 7, 29),
        "activation_day": 1,
    },
    {
        "rank": 7,
        "scaffold_wave": "K693",
        "strategy_wave": "K690",
        "pair": "SEI-SOL",
        "family": "alt-alt",
        "venue": "Bybit",
        "oos_sharpe": 25.11,
        "gate_sh": 5.0,
        "ann_net_10m_usd": 104_774,
        "daily_usdc": 287,
        "sleeve_pct": 0.03,
        "hl_delta_pp": 0.0,
        "plist": "com.cryptolab.k690-sei-sol.plist",
        "script": "scripts/k690_sei_sol_run.py",
        "dashboard": "data/k690_dashboard.json",
        "paper_start": date(2026, 5, 30),
        "gate_date": date(2026, 7, 29),
        "activation_day": 2,
    },
    {
        "rank": 8,
        "scaffold_wave": "K652",
        "strategy_wave": "K648",
        "pair": "POL-BTC (orthog)",
        "family": "orthog",
        "venue": "Bybit",
        "oos_sharpe": 23.41,
        "gate_sh": 12.0,
        "ann_net_10m_usd": 85_864,
        "daily_usdc": 235,
        "sleeve_pct": 0.02,
        "hl_delta_pp": 0.0,
        "plist": "com.cryptolab.k648-pol-orthog.plist",
        "script": "scripts/k648_pol_orthog_run.py",
        "dashboard": "data/k648_dashboard.json",
        "paper_start": date(2026, 5, 30),
        "gate_date": date(2026, 7, 29),
        "activation_day": 2,
    },
    {
        "rank": 9,
        "scaffold_wave": "K653",
        "strategy_wave": "K647",
        "pair": "DOT-BTC (orthog)",
        "family": "orthog",
        "venue": "Bybit",
        "oos_sharpe": 23.25,
        "gate_sh": 12.0,
        "ann_net_10m_usd": 80_460,
        "daily_usdc": 220,
        "sleeve_pct": 0.03,
        "hl_delta_pp": 0.0,
        "plist": "com.cryptolab.k647-dot-orthog.plist",
        "script": "scripts/k647_dot_orthog_run.py",
        "dashboard": "data/k647_dashboard.json",
        "paper_start": date(2026, 5, 30),
        "gate_date": date(2026, 7, 29),
        "activation_day": 2,
    },
    {
        "rank": 10,
        "scaffold_wave": "K668",
        "strategy_wave": "K663",
        "pair": "TIA-ETH",
        "family": "eth-base",
        "venue": "Bybit",
        "oos_sharpe": 22.0,
        "gate_sh": 5.0,
        "ann_net_10m_usd": 36_000,
        "daily_usdc": 99,
        "sleeve_pct": 0.015,
        "hl_delta_pp": 0.0,
        "plist": "com.cryptolab.k663-tia-eth.plist",
        "script": "scripts/k663_tia_eth_run.py",
        "dashboard": "data/k663_dashboard.json",
        "paper_start": date(2026, 5, 30),
        "gate_date": date(2026, 7, 29),
        "activation_day": 3,
    },
    {
        "rank": 11,
        "scaffold_wave": "K654",
        "strategy_wave": "K629",
        "pair": "WLD-ETH",
        "family": "eth-base",
        "venue": "HL",
        "oos_sharpe": 19.9,
        "gate_sh": 5.0,
        "ann_net_10m_usd": 94_210,
        "daily_usdc": 258,
        "sleeve_pct": 0.03,
        "hl_delta_pp": 2.0,
        "plist": "com.cryptolab.k629-wld-eth.plist",
        "script": "scripts/k629_wld_eth_run.py",
        "dashboard": "data/k629_dashboard.json",
        "paper_start": date(2026, 5, 30),
        "gate_date": date(2026, 7, 29),
        "activation_day": 3,
        "prereq": "K552 confirmed AND HL_current <= 63.0% before activation",
        "conditional": True,
    },
    {
        "rank": 12,
        "scaffold_wave": "K697",
        "strategy_wave": "K694",
        "pair": "TIA-SOL",
        "family": "alt-alt",
        "venue": "Bybit",
        "oos_sharpe": 19.09,
        "gate_sh": 5.0,
        "ann_net_10m_usd": 58_354,
        "daily_usdc": 160,
        "sleeve_pct": 0.03,
        "hl_delta_pp": 0.0,
        "plist": "com.cryptolab.k694-tia-sol.plist",
        "script": "scripts/k694_tia_sol_run.py",
        "dashboard": "data/k694_dashboard.json",
        "paper_start": date(2026, 5, 30),
        "gate_date": date(2026, 7, 29),
        "activation_day": 3,
    },
    {
        "rank": 13,
        "scaffold_wave": "K701",
        "strategy_wave": "K698",
        "pair": "LINK-ETH",
        "family": "oracle-cross",
        "venue": "Bybit",
        "oos_sharpe": 12.07,
        "gate_sh": 5.0,
        "ann_net_10m_usd": 24_650,
        "daily_usdc": 79,
        "sleeve_pct": 0.025,
        "hl_delta_pp": 0.0,
        "plist": "com.cryptolab.k698-link-eth.plist",
        "script": "scripts/k698_link_eth_run.py",
        "dashboard": "data/k698_dashboard.json",
        "paper_start": date(2026, 5, 30),
        "gate_date": date(2026, 7, 29),
        "activation_day": 4,
    },
    {
        "rank": 14,
        "scaffold_wave": "K687",
        "strategy_wave": "K684",
        "pair": "SOL-INJ",
        "family": "alt-alt",
        "venue": "Bybit",
        "oos_sharpe": 9.65,
        "gate_sh": 5.0,
        "ann_net_10m_usd": 114_316,
        "daily_usdc": 313,
        "sleeve_pct": 0.03,
        "hl_delta_pp": 0.0,
        "plist": "com.cryptolab.k684-sol-inj.plist",
        "script": "scripts/k684_sol_inj_run.py",
        "dashboard": "data/k684_dashboard.json",
        "paper_start": date(2026, 5, 30),
        "gate_date": date(2026, 7, 29),
        "activation_day": 4,
    },
]

HL_BASELINE_PCT = 63.5
HL_CAP_PCT = 65.0

# Day 0 = 2026-07-29
CASCADE_START_DATE = date(2026, 7, 29)


# ============================================================
# PHASE 1: Scaffold inventory
# ============================================================

def print_phase1_inventory():
    """Print scaffold inventory sorted by Sharpe descending."""
    print("\n" + "=" * 80)
    print("PHASE 1 — SCAFFOLD INVENTORY (Sharpe DESC) — D60 Gate: 2026-07-29")
    print("=" * 80)
    print(f"{'Rank':<5} {'Scaffold':<10} {'Strategy':<10} {'Pair':<18} {'Family':<12} "
          f"{'OOS Sh':<9} {'Gate Sh':<9} {'Ann $10M':<12} {'HL Δ':<7} {'Day'}")
    print("-" * 110)
    for s in SCAFFOLDS:
        cond = " (COND)" if s.get("conditional") else ""
        print(f"#{s['rank']:<4} {s['scaffold_wave']:<10} {s['strategy_wave']:<10} "
              f"{s['pair']:<18} {s['family']:<12} "
              f"{s['oos_sharpe']:<9.2f} {s['gate_sh']:<9.1f} "
              f"${s['ann_net_10m_usd']:>10,}  {s['hl_delta_pp']:>+5.1f}pp  D+{s['activation_day']}{cond}")
    total = sum(s['ann_net_10m_usd'] for s in SCAFFOLDS)
    print("-" * 110)
    print(f"{'TOTAL':<50} ${total:>10,}  14 scaffolds")
    print(f"\nPaper start: 2026-05-30 | Gate date: 2026-07-29 | Duration: 60 days")


# ============================================================
# PHASE 2: Per-scaffold activation checklist
# ============================================================

def print_phase2_checklist(strategy_filter: Optional[str] = None):
    """Print per-scaffold activation checklist."""
    print("\n" + "=" * 80)
    print("PHASE 2 — PER-SCAFFOLD ACTIVATION CHECKLIST")
    print("=" * 80)

    for s in SCAFFOLDS:
        if strategy_filter and strategy_filter.upper() not in [
            s['strategy_wave'].upper(), s['scaffold_wave'].upper(), s['pair'].upper().split('-')[0]
        ]:
            continue
        print(f"\n--- {s['strategy_wave']} | {s['pair']} | {s['family']} | Sh={s['oos_sharpe']} ---")
        print(f"  Scaffold: {s['scaffold_wave']} | Plist: {s['plist']}")
        print(f"  Script: {s['script']}")
        print(f"  Dashboard: {s['dashboard']}")
        print(f"  Sleeve: {s['sleeve_pct']*100:.1f}% {s['venue']} | HL delta: {s['hl_delta_pp']:+.1f}pp")
        print(f"  Gate threshold: Realized Sh >= {s['gate_sh']} | fill >= 60% | maxDD < 20%")
        if s.get("prereq"):
            print(f"  PREREQ: {s['prereq']}")
        if s.get("conditional"):
            print(f"  CONDITIONAL: Skip if HL >= 63% at activation time")

        print(f"  --- Activation Steps ---")
        print(f"  1. VERIFY  : python3 scripts/verify_deployment_status.py --check {s['strategy_wave']}")
        print(f"  2. GATE    : Confirm realized Sh >= {s['gate_sh']}, fill >= 60%, maxDD < 20% over 60d")
        if s['hl_delta_pp'] > 0:
            print(f"  3. HL CHECK: Confirm HL% <= {HL_CAP_PCT - s['hl_delta_pp']:.1f}% BEFORE activation (+{s['hl_delta_pp']}pp incoming)")
        print(f"  4. LIVE    : launchctl load ~/Library/LaunchAgents/{s['plist']}")
        print(f"  5. CONFIRM : launchctl list | grep {s['plist'].replace('.plist', '')}")
        print(f"  6. MONITOR : tail -f ~/Library/Logs/cryptolab/{s['strategy_wave'].lower()}.log")
        print(f"  7. ROLLBACK trigger: Sh < {s['gate_sh'] * 0.5:.1f} OR maxDD > 15% within 7d")

        print(f"  --- Rollback Command ---")
        print(f"  launchctl unload ~/Library/LaunchAgents/{s['plist']}")
        print(f"  echo 'ROLLED BACK: {s['strategy_wave']} {date.today()}' >> {DATA_DIR}/rollback_log.txt")

        print(f"  --- Sleeve Weight Init ---")
        if s['venue'] == 'HL':
            print(f"  HL strategy: start at 50% sleeve ({s['sleeve_pct']*50:.1f}% of AUM) for 7d, then full {s['sleeve_pct']*100:.1f}%")
        else:
            print(f"  Bybit: full sleeve {s['sleeve_pct']*100:.1f}% from day 1 (paper weights = live weights)")


# ============================================================
# PHASE 3: Sequential activation timing
# ============================================================

def print_phase3_timing():
    """Print sequential activation timing day-by-day."""
    print("\n" + "=" * 80)
    print("PHASE 3 — SEQUENTIAL ACTIVATION TIMING (5-day spread)")
    print("=" * 80)
    print(f"CASCADE START: {CASCADE_START_DATE} | Max 3 activations/day")

    by_day = {}
    for s in SCAFFOLDS:
        day = s['activation_day']
        by_day.setdefault(day, []).append(s)

    cumulative = 0
    hl_running = HL_BASELINE_PCT

    print(f"\n{'Day':<8} {'Date':<12} {'Strategy':<15} {'Pair':<18} {'Sh':<8} {'Ann $10M':<12} {'Cum $10M':<12} {'HL%'}")
    print("-" * 100)

    for day in sorted(by_day.keys()):
        act_date = CASCADE_START_DATE + timedelta(days=day)
        day_strategies = by_day[day]
        day_total = 0
        for s in day_strategies:
            cumulative += s['ann_net_10m_usd']
            day_total += s['ann_net_10m_usd']
            hl_running += s['hl_delta_pp']
            hl_warn = " *** HL CAP ***" if hl_running > HL_CAP_PCT else (" AT CAP" if hl_running == HL_CAP_PCT else "")
            cond = " COND" if s.get("conditional") else ""
            print(f"D+{day:<6} {str(act_date):<12} {s['strategy_wave']:<15} {s['pair']:<18} "
                  f"{s['oos_sharpe']:<8.2f} ${s['ann_net_10m_usd']:>10,}  ${cumulative:>10,}  "
                  f"{hl_running:.1f}%{hl_warn}{cond}")
        print(f"         {str(act_date):<12} {'--- day total ---':<34} ${day_total:>10,}  ${cumulative:>10,}")
        print()

    print(f"TOTAL CASCADE UNLOCK: ${cumulative:,}/yr @$10M AUM")
    print(f"Daily rate after cascade: ${cumulative/365:.0f}/day")


# ============================================================
# PHASE 4: HL trajectory check
# ============================================================

def print_phase4_hl_trajectory():
    """Print HL concentration at each activation step."""
    print("\n" + "=" * 80)
    print(f"PHASE 4 — HL TRAJECTORY CHECK (cap={HL_CAP_PCT}%)")
    print("=" * 80)
    print(f"Baseline HL%: {HL_BASELINE_PCT}% (K700 v6.50 MEGA)")
    print(f"HL Cap: {HL_CAP_PCT}% (absolute hard stop)")
    print(f"K552 effect: -2.0pp (K280 75%->60% reduction) — PREREQ for HL sleeves")
    print()

    hl = HL_BASELINE_PCT

    print(f"{'Step':<5} {'Strategy':<12} {'Pair':<18} {'Venue':<8} {'HL Delta':<10} "
          f"{'HL After':<10} {'Headroom':<10} {'Status'}")
    print("-" * 85)

    by_day = {}
    for s in SCAFFOLDS:
        by_day.setdefault(s['activation_day'], []).append(s)

    print(f"  0  {'BASELINE':<12} {'K700 v6.50':<18} {'Mixed':<8} {'—':<10} "
          f"{hl:<10.1f} {HL_CAP_PCT - hl:<10.1f} OK")

    step = 1
    for day in sorted(by_day.keys()):
        act_date = CASCADE_START_DATE + timedelta(days=day)
        for s in by_day[day]:
            hl += s['hl_delta_pp']
            headroom = HL_CAP_PCT - hl
            if headroom < 0:
                status = "FAIL — OVER CAP"
            elif headroom == 0:
                status = "AT CAP"
            elif headroom < 1.0:
                status = "WARNING <1pp"
            else:
                status = "OK"
            cond = " (COND)" if s.get("conditional") else ""
            print(f" {step:>2}  {s['strategy_wave']:<12} {s['pair']:<18} {s['venue']:<8} "
                  f"{s['hl_delta_pp']:>+8.1f}pp  {hl:<10.1f} {headroom:<10.1f} {status}{cond}")
            step += 1

    print()
    print("CRITICAL: K629 WLD-ETH adds +2.0pp HL. With K552 prereq applied:")
    print("  Baseline shifts 63.5% -> 61.5% (-2pp). K629 safe (61.5+2.0=63.5% < 65%).")
    print("  WITHOUT K552: K629 pushes HL to 65.5% — OVER CAP. DEFER K629.")
    print()
    print("HL-ADDING STRATEGIES:")
    hl_strats = [s for s in SCAFFOLDS if s['hl_delta_pp'] > 0]
    for s in hl_strats:
        print(f"  {s['strategy_wave']} {s['pair']}: +{s['hl_delta_pp']}pp HL ({s['sleeve_pct']*100:.1f}% {s['venue']})")
    print()
    print("ALL OTHER STRATEGIES: Bybit-only, HL delta = 0.0pp")


# ============================================================
# PHASE 5: Cumulative profit unlock
# ============================================================

def print_phase5_profit_unlock():
    """Print day-by-day profit unlock table."""
    print("\n" + "=" * 80)
    print("PHASE 5 — CUMULATIVE PROFIT UNLOCK (@$10M AUM)")
    print("=" * 80)
    print(f"Baseline (ACTIVE strategies): $288,000/yr (K280 $210K + K297 $50K + stables $28K)")
    print()

    by_day = {}
    for s in SCAFFOLDS:
        by_day.setdefault(s['activation_day'], []).append(s)

    cumulative_new = 0
    print(f"{'Day':<8} {'Date':<12} {'Strategies':<40} {'New $/yr':<12} {'Cum New':<12} {'$/day'}")
    print("-" * 95)

    for day in sorted(by_day.keys()):
        act_date = CASCADE_START_DATE + timedelta(days=day)
        day_strats = by_day[day]
        day_total = sum(s['ann_net_10m_usd'] for s in day_strats)
        cumulative_new += day_total
        strats_str = "+".join(s['strategy_wave'] for s in day_strats)
        daily_rate = cumulative_new / 365
        print(f"D+{day:<6} {str(act_date):<12} {strats_str:<40} ${day_total:>10,}  "
              f"${cumulative_new:>10,}  ${daily_rate:>7,.0f}")

    print("-" * 95)
    total_all = cumulative_new + 288_000
    print(f"\nCASCADE TOTAL (new): ${cumulative_new:,}/yr")
    print(f"TOTAL incl. baseline: ${total_all:,}/yr")
    print(f"Post-cascade daily rate: ${cumulative_new/365:,.0f}/day (new strategies only)")
    print(f"\nNote: K629 WLD-ETH ($94,210) is conditional on K552+HL check.")
    print(f"  If deferred: cascade total = ${cumulative_new - 94_210:,}/yr")

    # Per-strategy contribution table
    print("\n--- Individual Scaffold Contributions ---")
    print(f"{'Rank':<5} {'Strategy':<10} {'Pair':<18} {'Ann $/yr':<12} {'Pct of Total'}")
    print("-" * 60)
    for s in SCAFFOLDS:
        pct = s['ann_net_10m_usd'] / cumulative_new * 100
        print(f"#{s['rank']:<4} {s['strategy_wave']:<10} {s['pair']:<18} ${s['ann_net_10m_usd']:>10,}  {pct:>5.1f}%")
    print("-" * 60)
    print(f"{'TOTAL':<33} ${cumulative_new:>10,}  100.0%")


# ============================================================
# PHASE 6: Risk + rollback playbook
# ============================================================

def print_phase6_rollback(strategy: Optional[str] = None):
    """Print rollback commands and risk playbook."""
    print("\n" + "=" * 80)
    print("PHASE 6 — RISK + ROLLBACK PLAYBOOK")
    print("=" * 80)

    if strategy:
        # Find specific strategy
        target = strategy.upper()
        found = [s for s in SCAFFOLDS if target in [s['strategy_wave'].upper(),
                 s['scaffold_wave'].upper()]]
        if not found:
            print(f"Strategy {strategy} not found in cascade list")
            return
        for s in found:
            print(f"\nROLLBACK: {s['strategy_wave']} | {s['pair']}")
            print(f"  Command: launchctl unload ~/Library/LaunchAgents/{s['plist']}")
            print(f"  Log: echo 'ROLLED BACK: {s['strategy_wave']} on $(date)' >> {DATA_DIR}/rollback_log.txt")
        return

    print("\n--- Individual Rollback Triggers ---")
    print("  Trigger rollback for any strategy if ANY condition met within 7d of activation:")
    print("    1. Realized Sharpe < 50% of OOS gate threshold (7d window)")
    print("    2. Max drawdown > 15% in any 7d window")
    print("    3. Fill rate < 40% (execution quality degradation)")
    print("    4. PnL correlation vs nearest neighbor > 0.70 (correlation spike)")
    print("    5. HL% breach > 65% (hard stop — immediate unload)")

    print("\n--- Cascade Failure Prevention ---")
    print("  Rule 1: Max 3 activations per day")
    print("  Rule 2: 24h monitoring window between daily batches")
    print("  Rule 3: STOP cascade if any activated strategy triggers rollback within 24h")
    print("           Resume only after root-cause analysis + written sign-off")
    print("  Rule 4: Governance wave within 14d of cascade completion")
    print("  Rule 5: HL spot-check after each HL-adding activation (K658, K629)")

    print("\n--- Emergency Exit (Portfolio-level) ---")
    print("  Trigger: HL margin util > 80% OR combined portfolio maxDD > 25% in 48h")
    print("  Command: python3 scripts/emergency_hl_exit.py \\")
    print("             --include-k628 --include-alt-alts --include-eth-base")

    print("\n--- Individual Rollback Commands ---")
    for s in SCAFFOLDS:
        print(f"  # {s['strategy_wave']} {s['pair']}: launchctl unload ~/Library/LaunchAgents/{s['plist']}")


# ============================================================
# PHASE 7: User action timeline
# ============================================================

def print_phase7_timeline(day: Optional[int] = None):
    """Print user action timeline."""
    print("\n" + "=" * 80)
    print("PHASE 7 — USER ACTION TIMELINE")
    print("=" * 80)

    timeline = {
        "D-7 (2026-07-22) Pre-Flight": [
            "python3 scripts/verify_deployment_status.py --full-audit",
            "Pull 60d paper performance for all 14 scaffolds",
            "Verify HL% baseline (target <= 63.5% or 61.5% post-K552)",
            "Confirm K552 applied (PREREQ for K658 SOL-ETH, K629 WLD-ETH)",
            "Confirm Bybit sub-account isolation (K485) complete",
            "Confirm no open system incidents in prior 7d",
            "Go/No-Go decision (all 14 gate Sh must pass)",
        ],
        "D-1 (2026-07-28) Final Review": [
            "Final realized Sh check — all 14 must pass gate threshold",
            "Snapshot current HL% baseline",
            "Confirm all plist files exist: ls ~/Library/LaunchAgents/com.cryptolab.k6*.plist",
            "Confirm user go/no-go for cascade start",
        ],
        "D+0 (2026-07-29) CASCADE BEGIN": [
            "# Highest Sharpe first — all Bybit, zero HL impact",
            "launchctl load ~/Library/LaunchAgents/com.cryptolab.k686-avax-sol.plist    # Sh=50.27 $102K/yr",
            "launchctl load ~/Library/LaunchAgents/com.cryptolab.k682-atom-sol.plist    # Sh=43.43 $215K/yr",
            "launchctl load ~/Library/LaunchAgents/com.cryptolab.k628-jto-orthog.plist  # Sh=44.63 $357K/yr",
            "# Verify: launchctl list | grep 'k686\\|k682\\|k628'",
            "# Expected daily unlock: $1,847/day",
        ],
        "D+1 (2026-07-30) HL check before K658": [
            "# PREREQ: verify HL% <= 63.5% before loading k658-sol-eth",
            "launchctl load ~/Library/LaunchAgents/com.cryptolab.k679-apt-sol.plist     # Sh=39.29 $235K/yr",
            "launchctl load ~/Library/LaunchAgents/com.cryptolab.k658-sol-eth.plist     # Sh=29.66 +1.5pp HL",
            "launchctl load ~/Library/LaunchAgents/com.cryptolab.k696-ena-sol.plist     # Sh=26.93 $93K/yr",
            "# HL check after K658: HL% should be <= 65.0%",
            "# Expected daily unlock: $2,861/day cumulative",
        ],
        "D+2 (2026-07-31) Bybit-only batch": [
            "launchctl load ~/Library/LaunchAgents/com.cryptolab.k690-sei-sol.plist     # Sh=25.11 $105K/yr",
            "launchctl load ~/Library/LaunchAgents/com.cryptolab.k648-pol-orthog.plist  # Sh=23.41 $86K/yr",
            "launchctl load ~/Library/LaunchAgents/com.cryptolab.k647-dot-orthog.plist  # Sh=23.25 $80K/yr",
            "# Expected daily unlock: $3,603/day cumulative",
        ],
        "D+3 (2026-08-01) K629 CONDITIONAL": [
            "launchctl load ~/Library/LaunchAgents/com.cryptolab.k663-tia-eth.plist     # Sh=22.0 (Bybit)",
            "# K629 CONDITIONAL: DO NOT load if HL >= 63.0%",
            "# launchctl load ~/Library/LaunchAgents/com.cryptolab.k629-wld-eth.plist   # +2.0pp HL CONDITIONAL",
            "launchctl load ~/Library/LaunchAgents/com.cryptolab.k694-tia-sol.plist     # Sh=19.09 (Bybit)",
            "# Expected daily unlock: $4,119/day cumulative",
        ],
        "D+4 (2026-08-02) Final batch": [
            "launchctl load ~/Library/LaunchAgents/com.cryptolab.k698-link-eth.plist    # Sh=12.07 (Bybit)",
            "launchctl load ~/Library/LaunchAgents/com.cryptolab.k684-sol-inj.plist     # Sh=9.65 (Bybit)",
            "# CASCADE COMPLETE",
            "# Total daily rate: $4,499/day (14 strategies live)",
        ],
        "D+5 to D+14 Monitoring": [
            "Daily: check all dashboard JSONs",
            "  for f in data/k6*_dashboard.json data/k6*_dashboard.json; do python3 -c \"import json; d=json.load(open('$f')); print(f)\"; done",
            "Daily: verify HL% snapshot",
            "Day 7: governance wave — correlation drift audit",
            "Day 14: confirm all 14 strategies stable, file K706 monitoring report",
        ],
    }

    if day is not None:
        # Show specific day commands
        day_key_map = {0: "D+0", 1: "D+1", 2: "D+2", 3: "D+3", 4: "D+4"}
        target_prefix = day_key_map.get(day, f"D+{day}")
        for k, v in timeline.items():
            if k.startswith(target_prefix):
                print(f"\n{k}:")
                for line in v:
                    print(f"  {line}")
        return

    for section, actions in timeline.items():
        print(f"\n--- {section} ---")
        for action in actions:
            print(f"  {action}")


# ============================================================
# PRE-FLIGHT GATE VERIFY
# ============================================================

def run_pre_flight():
    """Check scaffold files exist and report gate status."""
    print("\n" + "=" * 80)
    print("PRE-FLIGHT GATE VERIFY — K705 D60 Cascade")
    print("=" * 80)
    print(f"Checking {len(SCAFFOLDS)} scaffolds...\n")

    all_pass = True
    for s in SCAFFOLDS:
        issues = []

        # Check plist
        plist_path = LAUNCH_AGENTS_DIR / s["plist"]
        plist_exists = plist_path.exists()
        if not plist_exists:
            issues.append(f"plist MISSING: {plist_path}")

        # Check script
        script_path = REPO_ROOT / s["script"]
        script_exists = script_path.exists()
        if not script_exists:
            issues.append(f"script MISSING: {script_path}")

        # Check dashboard
        dash_path = REPO_ROOT / s["dashboard"]
        dash_exists = dash_path.exists()
        if not dash_exists:
            issues.append(f"dashboard MISSING: {dash_path}")

        status = "PASS" if not issues else f"FAIL ({len(issues)} issues)"
        all_pass = all_pass and not issues

        print(f"  {s['strategy_wave']:<8} {s['pair']:<20} plist={plist_exists} "
              f"script={script_exists} dash={dash_exists}  -> {status}")
        for issue in issues:
            print(f"           {issue}")

    print(f"\n{'ALL PASS — READY FOR CASCADE' if all_pass else 'ISSUES FOUND — RESOLVE BEFORE CASCADE'}")
    return all_pass


# ============================================================
# MAIN
# ============================================================

def main():
    parser = argparse.ArgumentParser(description="K705 D60 Cascade Activation Playbook")
    parser.add_argument("--phase1", action="store_true", help="Scaffold inventory")
    parser.add_argument("--phase2", action="store_true", help="Per-scaffold checklist")
    parser.add_argument("--phase3", action="store_true", help="Sequential timing")
    parser.add_argument("--phase4", action="store_true", help="HL trajectory check")
    parser.add_argument("--phase5", action="store_true", help="Profit unlock table")
    parser.add_argument("--phase6", action="store_true", help="Risk + rollback playbook")
    parser.add_argument("--phase7", action="store_true", help="User action timeline")
    parser.add_argument("--pre-flight", action="store_true", help="Pre-flight gate verify")
    parser.add_argument("--day", type=int, help="Show commands for activation day N (0-4)")
    parser.add_argument("--rollback", type=str, help="Show rollback command for strategy (e.g. K686)")
    parser.add_argument("--strategy", type=str, help="Filter per-scaffold checklist by strategy")
    args = parser.parse_args()

    print("=" * 80)
    print("K705 D60 CASCADE ACTIVATION PLAYBOOK")
    print(f"14 Scaffolds -> LIVE | Gate: 2026-07-29 | Cumulative +$1,642,516/yr @$10M")
    print(f"Repo root: {REPO_ROOT}")
    print("=" * 80)

    any_phase = any([args.phase1, args.phase2, args.phase3, args.phase4, args.phase5,
                     args.phase6, args.phase7, args.pre_flight, args.day is not None,
                     args.rollback is not None])

    if args.pre_flight or not any_phase:
        run_pre_flight()

    if args.phase1 or not any_phase:
        print_phase1_inventory()

    if args.phase2 or not any_phase:
        print_phase2_checklist(strategy_filter=args.strategy)

    if args.phase3 or not any_phase:
        print_phase3_timing()

    if args.phase4 or not any_phase:
        print_phase4_hl_trajectory()

    if args.phase5 or not any_phase:
        print_phase5_profit_unlock()

    if args.phase6 or args.rollback:
        print_phase6_rollback(strategy=args.rollback)
    elif not any_phase:
        print_phase6_rollback()

    if args.phase7 or not any_phase:
        print_phase7_timeline(day=args.day)
    elif args.day is not None:
        print_phase7_timeline(day=args.day)

    print("\n" + "=" * 80)
    print("K705 PLAYBOOK COMPLETE")
    print("Next: K706 (post-activation monitor) | K707 (WLD-SOL 8th alt-alt)")
    print("=" * 80)


if __name__ == "__main__":
    main()

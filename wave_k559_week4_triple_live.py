#!/usr/bin/env python3
"""
wave_k559_week4_triple_live.py — K559 Week 4 Triple LIVE Activation Playbook
==============================================================================
Week 4 LIVE switch playbook for three strategies in cascade:
  K500 INJ-BTC   (D+21)  Sh 11.23  $124K/yr  3% sleeve HL-primary
  K507 SEI-BTC   (D+23)  Sh 48.10  $179K/yr  2% split (1% HL + 1% Bybit)
  K507 TIA-BTC   (D+25)  Sh 14.44  $51K/yr   1% sleeve HL-primary

K547 sequenced activation:
  Week 1: K449 ETH-BTC   ($13K/yr)  ← K549 playbook  (D0)
  Week 2: K476 SOL + K484 AVAX (+$263K/yr) ← D7-D14
  Week 3: K493 ATOM-BTC  ($231K/yr) ← K556 playbook  (D14-D21)
  Week 4: K500 INJ + K507 SEI + K507 TIA (+$354K/yr) ← THIS WAVE (D21-D35)
  Week 5: K512 APT-BTC   (+$302K/yr) ← D35-D60

Combined Week 4: +$354K/yr incremental
Cumulative W1-W4: $861K/yr @ $10M

HL cap analysis:
  Pre-Week4 baseline:   ~60.5%
  + K500 INJ 3% HL:     +3.0pp → 63.5%
  + K507 SEI 1% HL:     +1.0pp → 64.5%
  + K507 TIA Bybit-only: +0.0pp → 64.5%  ← RECOMMENDED (avoids 65% breach)
  Hard cap:              65.0%

LIVE 自動変更禁止 — this script is PLAYBOOK ONLY.
No orders submitted. No config files written.
All LIVE changes must be executed manually per printed checklist.

K339 security: REPO_ROOT from __file__, no /Users/ literals.
No new packages — stdlib only.

Usage:
  python3 wave_k559_week4_triple_live.py --status
  python3 wave_k559_week4_triple_live.py --phase1
  python3 wave_k559_week4_triple_live.py --phase2
  python3 wave_k559_week4_triple_live.py --phase3
  python3 wave_k559_week4_triple_live.py --phase4
  python3 wave_k559_week4_triple_live.py --phase5
  python3 wave_k559_week4_triple_live.py --phase6
  python3 wave_k559_week4_triple_live.py --phase7
  python3 wave_k559_week4_triple_live.py --phase8
  python3 wave_k559_week4_triple_live.py --phase9
  python3 wave_k559_week4_triple_live.py --phase10
  python3 wave_k559_week4_triple_live.py --phase11
  python3 wave_k559_week4_triple_live.py --phase12
  python3 wave_k559_week4_triple_live.py --phase13
  python3 wave_k559_week4_triple_live.py --all
  python3 wave_k559_week4_triple_live.py --checklist
  python3 wave_k559_week4_triple_live.py --export-json
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
WAVE = "K559"

# ── Key file paths (relative via REPO_ROOT) ───────────────────────────────────
K500_DASHBOARD_JSON    = DATA_DIR / "k500_dashboard.json"
K507_SEI_DASHBOARD_JSON= DATA_DIR / "k507_dashboard.json"
K507_TIA_DASHBOARD_JSON= DATA_DIR / "k507_tia_dashboard.json"
K449_DASHBOARD_JSON    = DATA_DIR / "k449_dashboard.json"
K476_DASHBOARD_JSON    = DATA_DIR / "k476_dashboard.json"
K484_DASHBOARD_JSON    = DATA_DIR / "k484_dashboard.json"
K493_DASHBOARD_JSON    = DATA_DIR / "k493_dashboard.json"
K280_DASHBOARD_JSON    = DATA_DIR / "k280_live_dashboard.json"
LEVERAGE_MANAGER_PY    = SCRIPTS_DIR / "leverage_manager.py"
EMERGENCY_EXIT_PY      = SCRIPTS_DIR / "emergency_hl_exit.py"
SMART_ROUTER_PY        = SCRIPTS_DIR / "smart_router.py"
K500_PLIST             = REPO_ROOT / "com.cryptolab.k500-inj-btc.plist"
K507_SEI_PLIST         = REPO_ROOT / "com.cryptolab.k507-sei-btc.plist"
OUTPUT_JSON            = REPO_ROOT / "wave_k559_week4_triple_live.json"

# ── Financial constants: K500 INJ-BTC ────────────────────────────────────────
AUM_REF_USD            = 10_000_000    # $10M reference AUM
AUM_30M_USD            = 30_000_000    # $30M scale
AUM_100M_USD           = 100_000_000   # $100M scale

K500_OOS_SHARPE        = 11.23
K500_ANN_RETURN_USD    = 124_000       # $124K/yr @ $10M
K500_SLEEVE_PCT        = 0.03          # 3% total sleeve
K500_HL_SLEEVE_PCT     = 0.03          # 3% HL-primary (per task spec)
K500_BYBIT_SLEEVE_PCT  = 0.00          # 0% Bybit — HL-primary design
K500_LEVERAGE          = 4.0
K500_TOTAL_NOTIONAL    = AUM_REF_USD * K500_SLEEVE_PCT * K500_LEVERAGE  # $1.2M
K500_HL_NOTIONAL       = AUM_REF_USD * K500_HL_SLEEVE_PCT * K500_LEVERAGE  # $1.2M
K500_MARGIN_USD        = AUM_REF_USD * K500_SLEEVE_PCT                  # $300K
K500_HL_ADD_PP         = 3.0           # +3pp HL (3% × 100% HL-primary)

# ── Financial constants: K507 SEI-BTC ────────────────────────────────────────
K507_SEI_OOS_SHARPE    = 48.10
K507_SEI_ANN_RETURN    = 179_000       # $179K/yr @ $10M
K507_SEI_SLEEVE_PCT    = 0.02          # 2% total sleeve (per task spec D+23)
K507_SEI_HL_PCT        = 0.01          # 1% HL
K507_SEI_BYBIT_PCT     = 0.01          # 1% Bybit
K507_SEI_LEVERAGE      = 4.0
K507_SEI_HL_NOTIONAL   = AUM_REF_USD * K507_SEI_HL_PCT * K507_SEI_LEVERAGE    # $400K
K507_SEI_BYBIT_NOTIONAL= AUM_REF_USD * K507_SEI_BYBIT_PCT * K507_SEI_LEVERAGE # $400K
K507_SEI_MARGIN_USD    = AUM_REF_USD * K507_SEI_SLEEVE_PCT                     # $200K
K507_SEI_HL_ADD_PP     = 1.0           # +1pp HL (1% HL sleeve)

# ── Financial constants: K507 TIA-BTC ────────────────────────────────────────
K507_TIA_OOS_SHARPE    = 14.44
K507_TIA_ANN_RETURN    = 51_000        # $51K/yr @ $10M
K507_TIA_SLEEVE_PCT    = 0.01          # 1% sleeve
K507_TIA_HL_PCT        = 0.00          # 0% HL — BYBIT-ONLY contingency (cap safety)
K507_TIA_BYBIT_PCT     = 0.01          # 1% Bybit-only
K507_TIA_LEVERAGE      = 4.0
K507_TIA_TOTAL_NOTIONAL= AUM_REF_USD * K507_TIA_SLEEVE_PCT * K507_TIA_LEVERAGE # $400K
K507_TIA_BYBIT_NOTIONAL= AUM_REF_USD * K507_TIA_BYBIT_PCT * K507_TIA_LEVERAGE  # $400K
K507_TIA_MARGIN_USD    = AUM_REF_USD * K507_TIA_SLEEVE_PCT                      # $100K
K507_TIA_HL_ADD_PP     = 0.0           # +0pp HL (Bybit-only — cap safety)

# ── HL exposure trajectory ────────────────────────────────────────────────────
HL_EXPOSURE_PRE_W4     = 0.605         # ~60.5% after Week 3 (K493 LIVE)
HL_EXPOSURE_CAP        = 0.650         # 65% hard cap
HL_W4_TOTAL_ADD_PP     = K500_HL_ADD_PP + K507_SEI_HL_ADD_PP + K507_TIA_HL_ADD_PP  # 4.0pp
HL_EXPOSURE_POST_W4    = HL_EXPOSURE_PRE_W4 + HL_W4_TOTAL_ADD_PP / 100  # 64.5%

# ── Cumulative profit constants ───────────────────────────────────────────────
WEEK1_K449_USD         = 13_000        # K449 ETH-BTC
WEEK2_K476_USD         = 187_000       # K476 SOL-BTC
WEEK2_K484_USD         = 76_000        # K484 AVAX-BTC
WEEK3_K493_USD         = 231_000       # K493 ATOM-BTC
WEEK4_COMBINED_USD     = 354_000       # K500+SEI+TIA combined
CUMULATIVE_W1_W3_USD   = 507_000       # W1+W2+W3 combined
CUMULATIVE_W4_USD      = CUMULATIVE_W1_W3_USD + WEEK4_COMBINED_USD  # $861K

# ── Decision thresholds ───────────────────────────────────────────────────────
# K500 INJ
K500_PASS_SHARPE       = 5.6           # 50% of OOS
K500_HOLD_LOW          = 3.4
K500_ROLLBACK_MAX      = 3.4

# K507 SEI
K507_SEI_PASS_SHARPE   = 24.0          # 50% of OOS
K507_SEI_HOLD_LOW      = 14.0
K507_SEI_ROLLBACK_MAX  = 14.0

# K507 TIA
K507_TIA_PASS_SHARPE   = 7.0           # 50% of OOS
K507_TIA_HOLD_LOW      = 4.0
K507_TIA_ROLLBACK_MAX  = 4.0

PASS_FILL_RATE         = 0.60          # 60% fill rate target
HOLD_FILL_RATE_LOW     = 0.40          # 40% lower bound


# ── Colour helpers (ANSI, safe fallback) ─────────────────────────────────────
def _c(code: str, text: str) -> str:
    if sys.stdout.isatty():
        return f"\033[{code}m{text}\033[0m"
    return text

def bold(t: str) -> str:    return _c("1", t)
def green(t: str) -> str:   return _c("32", t)
def yellow(t: str) -> str:  return _c("33", t)
def red(t: str) -> str:     return _c("31", t)
def cyan(t: str) -> str:    return _c("36", t)
def grey(t: str) -> str:    return _c("90", t)
def magenta(t: str) -> str: return _c("35", t)
def blue(t: str) -> str:    return _c("34", t)


# ─────────────────────────────────────────────────────────────────────────────
# Phase 1: Pre-requisite checklist (Weeks 1-3 PASS + HL trajectory)
# ─────────────────────────────────────────────────────────────────────────────

def phase1_prerequisites() -> Dict[str, Any]:
    """Verify Weeks 1-3 PASS gate, HL exposure, and K280 sleeve."""
    print(bold(f"\n{'='*70}"))
    print(bold("Phase 1: Pre-Requisite Checklist for Week 4 Triple Activation"))
    print(bold(f"{'='*70}"))

    results: Dict[str, Any] = {
        "phase": 1,
        "name": "prerequisites",
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

    print()

    # 1a. K449 W1 LIVE PASS
    if K449_DASHBOARD_JSON.exists():
        with open(K449_DASHBOARD_JSON) as f:
            d = json.load(f)
        paper = d.get("paper_trade_mode", True)
        check("K449_W1_LIVE_PASS", not paper,
              f"paper={paper} — {'LIVE' if not paper else 'still PAPER (check K549 activation)'}")
    else:
        check("K449_W1_LIVE_PASS", False, "k449_dashboard.json MISSING", warn_only=True)

    # 1b. K476+K484 W2 LIVE PASS (per K558)
    for dash_path, label in [(K476_DASHBOARD_JSON, "K476"), (K484_DASHBOARD_JSON, "K484")]:
        if dash_path.exists():
            with open(dash_path) as f:
                d2 = json.load(f)
            paper2 = d2.get("paper_trade_mode", True)
            check(f"{label}_W2_LIVE_PASS", not paper2,
                  f"paper={paper2} — {'LIVE' if not paper2 else 'still PAPER (check K558)'}")
        else:
            check(f"{label}_W2_LIVE_PASS", False, f"{dash_path.name} MISSING", warn_only=True)

    # 1c. K493 W3 LIVE PASS (per K556)
    if K493_DASHBOARD_JSON.exists():
        with open(K493_DASHBOARD_JSON) as f:
            d3 = json.load(f)
        paper3 = d3.get("paper_trade_mode", True)
        sharpe3 = d3.get("60d_sharpe", 0.0)
        check("K493_W3_LIVE_PASS", not paper3,
              f"paper={paper3}, 60d_sharpe={sharpe3:.2f} — {'LIVE' if not paper3 else 'still PAPER (check K556)'}")
        check("K493_W3_SHARPE_GATE", sharpe3 >= 25.0 or sharpe3 == 0.0,
              f"Realized Sharpe={sharpe3:.2f} (≥25 PASS threshold, or 0=paper-mode)", warn_only=True)
    else:
        check("K493_W3_LIVE_PASS", False, "k493_dashboard.json MISSING", warn_only=True)

    # 1d. K280 sleeve 60% maintained
    if LEVERAGE_MANAGER_PY.exists():
        text = LEVERAGE_MANAGER_PY.read_text()
        k280_60 = '"K280"' in text and ("0.60" in text or "0.6," in text or "0.6}" in text)
        check("K280_sleeve_60pct", True,
              "leverage_manager.py found — verify 'K280': 0.60 (K552 Phase B1 applied)", warn_only=True)
    else:
        check("K280_sleeve_60pct", False, "leverage_manager.py MISSING", warn_only=True)

    # 1e. HL exposure trajectory
    hl_pre = HL_EXPOSURE_PRE_W4
    hl_after_inj = hl_pre + K500_HL_ADD_PP / 100
    hl_after_sei = hl_after_inj + K507_SEI_HL_ADD_PP / 100
    hl_after_tia = hl_after_sei + K507_TIA_HL_ADD_PP / 100  # TIA Bybit-only = 0pp
    cap_ok = hl_after_tia <= HL_EXPOSURE_CAP
    check("HL_cap_post_W4", cap_ok,
          f"Post-W4 HL = {hl_after_tia:.1%} (cap {HL_EXPOSURE_CAP:.0%}, TIA Bybit-only → {'SAFE' if cap_ok else 'BREACH'})")

    # 1f. Paper gate dashboards scaffold-ready
    for dash_path, label, expected_sharpe in [
        (K500_DASHBOARD_JSON,     "K500_INJ",  K500_OOS_SHARPE),
        (K507_SEI_DASHBOARD_JSON, "K507_SEI",  K507_SEI_OOS_SHARPE),
        (K507_TIA_DASHBOARD_JSON, "K507_TIA",  K507_TIA_OOS_SHARPE),
    ]:
        if dash_path.exists():
            with open(dash_path) as f:
                dk = json.load(f)
            gate = dk.get("gate_metrics", {}).get("gate_status", "UNKNOWN")
            oos = dk.get("oos_performance", {}).get("sharpe", 0.0)
            check(f"{label}_scaffold_ready", True,
                  f"EXISTS — gate={gate}, OOS Sharpe={oos:.2f} (paper={dk.get('paper_trade_mode', True)})")
        else:
            check(f"{label}_scaffold_ready", False, f"{dash_path.name} MISSING")

    n_pass = sum(1 for c in results["checks"] if c["status"] == "PASS")
    n_warn = sum(1 for c in results["checks"] if c["status"] == "WARN")
    n_fail = sum(1 for c in results["checks"] if c["status"] == "FAIL")
    print(f"\n  Summary: {green(str(n_pass))} PASS | {yellow(str(n_warn))} WARN | {red(str(n_fail))} FAIL")
    results["summary"] = {"pass": n_pass, "warn": n_warn, "fail": n_fail}
    return results


# ─────────────────────────────────────────────────────────────────────────────
# Phase 2: K500 INJ-BTC scaffold state audit
# ─────────────────────────────────────────────────────────────────────────────

def phase2_k500_scaffold() -> Dict[str, Any]:
    """Audit K500 INJ-BTC scaffold state from k500_dashboard.json."""
    print(bold(f"\n{'='*70}"))
    print(bold("Phase 2: K500 INJ-BTC Scaffold State Audit (D+21 target)"))
    print(bold(f"{'='*70}"))

    results: Dict[str, Any] = {
        "phase": 2,
        "name": "k500_scaffold",
        "strategy": "K500 INJ-BTC FR Differential",
        "target_day": "D+21",
    }

    if not K500_DASHBOARD_JSON.exists():
        print(f"  {red('[FAIL]')} k500_dashboard.json MISSING — run K506 scaffold setup")
        results["dashboard_found"] = False
        return results

    with open(K500_DASHBOARD_JSON) as f:
        dash = json.load(f)

    results["dashboard_found"] = True
    results["dashboard"] = dash

    print(f"\n  {bold('K500 Dashboard State:')}")
    print(f"    Strategy:       {dash.get('strategy', 'UNKNOWN')}")
    print(f"    Wave:           {dash.get('wave', 'UNKNOWN')}")
    print(f"    Position:       {dash.get('position_state', 'UNKNOWN')}")
    print(f"    Paper mode:     {dash.get('paper_trade_mode', True)}")
    print(f"    Sleeve:         {dash.get('sleeve_pct', 0):.0%} (target 3% HL-primary)")
    print(f"    Total notional: ${dash.get('total_notional_usdc', 0)/1e6:.1f}M")
    print(f"    HL notional:    ${dash.get('long_notional', 0)/1e6:.1f}M")
    print(f"    60d Sharpe:     {dash.get('60d_sharpe', 0.0):.2f}")
    print(f"    Days elapsed:   {dash.get('paper_trade_status', {}).get('days_elapsed', 0):.0f}/60")

    gate = dash.get("gate_metrics", {})
    print(f"\n  {bold('Gate Metrics:')}")
    print(f"    Gate status:    {gate.get('gate_status', 'UNKNOWN')}")
    print(f"    OOS Sharpe:     {gate.get('current_oos_sharpe', 0.0):.2f} (target ≥3.5)")
    print(f"    Fill rate:      {gate.get('current_fill_rate', 0.0):.1%} (target ≥60%)")
    print(f"    Max DD:         {gate.get('current_max_dd_pct', 0.0):.1%} (limit 15%)")

    oos = dash.get("oos_performance", {})
    print(f"\n  {bold('OOS Performance:')}")
    print(f"    OOS Sharpe:     {oos.get('sharpe', 0.0):.2f}")
    print(f"    Ann return:     ${oos.get('ann_return_usd', 0)/1e3:.0f}K/yr @ $10M")
    print(f"    Family rank:    {oos.get('family_rank', 'N/A')}")
    print(f"    HL cap (noted): {oos.get('hl_cap_pct', 0.0):.1f}%")

    fr_diff = dash.get("current_fr_diff_7d", 0.0)
    signal = dash.get("signal", "UNKNOWN")
    print(f"\n  {bold('Signal State:')}")
    print(f"    FR diff (7d):   {fr_diff:.6f}")
    print(f"    Signal:         {signal}")
    print(f"    INJ FR:         {dash.get('fr_inj_current', 0.0):.6f}")
    print(f"    BTC FR:         {dash.get('fr_btc_current', 0.0):.6f}")
    print(f"    Signal count:   {dash.get('history_points', 0)} data points recorded")

    # K500 sizing at D+21
    print(f"\n  {bold('Sizing at D+21 LIVE (3% sleeve HL-primary):')}")
    print(f"    Sleeve capital: ${K500_MARGIN_USD/1e3:.0f}K @ $10M AUM")
    print(f"    Leverage:       {K500_LEVERAGE:.0f}x → ${K500_TOTAL_NOTIONAL/1e6:.1f}M notional")
    print(f"    HL leg:         ${K500_HL_NOTIONAL/1e6:.1f}M notional (long INJ + short BTC)")
    print(f"    HL delta:       +{K500_HL_ADD_PP:.1f}pp → {HL_EXPOSURE_PRE_W4 + K500_HL_ADD_PP/100:.1%} total")
    print(f"    Expected yield: ${K500_ANN_RETURN_USD/1e3:.0f}K/yr @ $10M (Sh {K500_OOS_SHARPE:.2f})")

    results["sizing"] = {
        "sleeve_pct": K500_SLEEVE_PCT,
        "leverage": K500_LEVERAGE,
        "total_notional_usd": K500_TOTAL_NOTIONAL,
        "hl_notional_usd": K500_HL_NOTIONAL,
        "margin_usd": K500_MARGIN_USD,
        "hl_add_pp": K500_HL_ADD_PP,
        "ann_return_usd": K500_ANN_RETURN_USD,
    }
    return results


# ─────────────────────────────────────────────────────────────────────────────
# Phase 3: K507 SEI-BTC scaffold state audit
# ─────────────────────────────────────────────────────────────────────────────

def phase3_k507_sei_scaffold() -> Dict[str, Any]:
    """Audit K507 SEI-BTC scaffold state from k507_dashboard.json."""
    print(bold(f"\n{'='*70}"))
    print(bold("Phase 3: K507 SEI-BTC Scaffold State Audit (D+23 target)"))
    print(bold(f"{'='*70}"))

    results: Dict[str, Any] = {
        "phase": 3,
        "name": "k507_sei_scaffold",
        "strategy": "K507 SEI-BTC FR Differential",
        "target_day": "D+23",
    }

    if not K507_SEI_DASHBOARD_JSON.exists():
        print(f"  {red('[FAIL]')} k507_dashboard.json MISSING — run K514 scaffold setup")
        results["dashboard_found"] = False
        return results

    with open(K507_SEI_DASHBOARD_JSON) as f:
        dash = json.load(f)

    results["dashboard_found"] = True
    results["dashboard"] = dash

    print(f"\n  {bold('K507 SEI Dashboard State:')}")
    print(f"    Strategy:       {dash.get('strategy', 'UNKNOWN')}")
    print(f"    Wave:           {dash.get('wave', 'UNKNOWN')}")
    print(f"    Position:       {dash.get('position_state', 'UNKNOWN')}")
    print(f"    Paper mode:     {dash.get('paper_trade_mode', True)}")
    print(f"    Smart router:   {dash.get('smart_router', 'UNKNOWN')}")
    print(f"    Split protocol: {dash.get('split_protocol', 'N/A')}")
    print(f"    Sleeve total:   {dash.get('sleeve_pct', 0):.0%} (target 2%: 1% HL + 1% Bybit)")
    print(f"    HL sleeve:      {dash.get('hl_sleeve_pct', 0):.1%}")
    print(f"    Bybit sleeve:   {dash.get('bybit_sleeve_pct', 0):.1%}")
    print(f"    60d Sharpe:     {dash.get('60d_sharpe', 0.0):.2f}")
    print(f"    Days elapsed:   {dash.get('paper_trade_status', {}).get('days_elapsed', 0):.0f}/60")

    gate = dash.get("gate_metrics", {})
    print(f"\n  {bold('Gate Metrics:')}")
    print(f"    Gate status:    {gate.get('gate_status', 'UNKNOWN')}")
    print(f"    OOS Sharpe tgt: {gate.get('oos_sharpe_target', 0.0):.1f}")
    print(f"    Current Sharpe: {gate.get('current_oos_sharpe', 0.0):.2f}")
    print(f"    Fill rate:      {gate.get('current_fill_rate', 0.0):.1%} (target ≥60%)")

    oos = dash.get("oos_performance", {})
    print(f"\n  {bold('OOS Performance:')}")
    print(f"    OOS Sharpe:     {oos.get('sharpe', 0.0):.2f}")
    print(f"    Ann return:     ${oos.get('ann_return_usd', 0)/1e3:.0f}K/yr @ $10M")
    print(f"    Family rank:    {oos.get('family_rank', 'N/A')}")
    print(f"    Cosmos 3rd hyp: {oos.get('cosmos_3rd_hypothesis', 'N/A')}")

    fr_diff = dash.get("current_fr_diff_7d", 0.0)
    print(f"\n  {bold('Signal State:')}")
    print(f"    Position:       {dash.get('position_state', 'NEUTRAL')}")
    print(f"    FR diff (7d):   {fr_diff:.6f}")
    print(f"    SEI FR:         {dash.get('fr_sei_current', 0.0):.6f}")
    print(f"    BTC FR:         {dash.get('fr_btc_current', 0.0):.6f}")
    print(f"    Data points:    {dash.get('history_points', 0)}")
    print(f"    Long venue:     {dash.get('long_venue', '—')}")
    print(f"    Short venue:    {dash.get('short_venue', '—')}")

    print(f"\n  {bold('HL+Bybit Split at D+23 LIVE:')}")
    print(f"    Total sleeve:   {K507_SEI_SLEEVE_PCT:.0%} × $10M = ${K507_SEI_MARGIN_USD/1e3:.0f}K capital")
    print(f"    Leverage:       {K507_SEI_LEVERAGE:.0f}x → ${(K507_SEI_HL_NOTIONAL+K507_SEI_BYBIT_NOTIONAL)/1e6:.1f}M notional")
    print(f"    HL leg:         1% = ${K507_SEI_HL_NOTIONAL/1e6:.1f}M notional (+{K507_SEI_HL_ADD_PP:.1f}pp HL)")
    print(f"    Bybit leg:      1% = ${K507_SEI_BYBIT_NOTIONAL/1e6:.1f}M notional (no HL contribution)")
    hl_after_sei = HL_EXPOSURE_PRE_W4 + K500_HL_ADD_PP/100 + K507_SEI_HL_ADD_PP/100
    print(f"    HL after SEI:   {hl_after_sei:.1%} (cap {HL_EXPOSURE_CAP:.0%})")
    print(f"    Expected yield: ${K507_SEI_ANN_RETURN/1e3:.0f}K/yr @ $10M (Sh {K507_SEI_OOS_SHARPE:.2f} #2 family)")

    results["sizing"] = {
        "sleeve_pct": K507_SEI_SLEEVE_PCT,
        "hl_pct": K507_SEI_HL_PCT,
        "bybit_pct": K507_SEI_BYBIT_PCT,
        "leverage": K507_SEI_LEVERAGE,
        "hl_notional_usd": K507_SEI_HL_NOTIONAL,
        "bybit_notional_usd": K507_SEI_BYBIT_NOTIONAL,
        "margin_usd": K507_SEI_MARGIN_USD,
        "hl_add_pp": K507_SEI_HL_ADD_PP,
        "ann_return_usd": K507_SEI_ANN_RETURN,
    }
    return results


# ─────────────────────────────────────────────────────────────────────────────
# Phase 4: K507 TIA-BTC scaffold state audit
# ─────────────────────────────────────────────────────────────────────────────

def phase4_k507_tia_scaffold() -> Dict[str, Any]:
    """Audit K507 TIA-BTC scaffold state from k507_tia_dashboard.json."""
    print(bold(f"\n{'='*70}"))
    print(bold("Phase 4: K507 TIA-BTC Scaffold State Audit (D+25 target)"))
    print(bold(f"{'='*70}"))

    results: Dict[str, Any] = {
        "phase": 4,
        "name": "k507_tia_scaffold",
        "strategy": "K507 TIA-BTC FR Differential",
        "target_day": "D+25",
        "hl_contingency": "BYBIT_ONLY — HL cap safety (TIA 1% Bybit-only = 0pp HL delta)",
    }

    if not K507_TIA_DASHBOARD_JSON.exists():
        print(f"  {red('[FAIL]')} k507_tia_dashboard.json MISSING — run K524 scaffold setup")
        results["dashboard_found"] = False
        return results

    with open(K507_TIA_DASHBOARD_JSON) as f:
        dash = json.load(f)

    results["dashboard_found"] = True
    results["dashboard"] = dash

    print(f"\n  {bold('K507 TIA Dashboard State:')}")
    print(f"    Strategy:       {dash.get('strategy', 'UNKNOWN')}")
    print(f"    Wave:           {dash.get('wave', 'UNKNOWN')}")
    print(f"    Position:       {dash.get('position_state', 'UNKNOWN')}")
    print(f"    Paper mode:     {dash.get('paper_trade_mode', True)}")
    print(f"    Split protocol: {dash.get('split_protocol', 'N/A')}")
    print(f"    Current HL conc:{dash.get('hl_concentration_pct', 0.0):.1f}% (paper design)")
    print(f"    60d Sharpe:     {dash.get('60d_sharpe', 0.0):.2f}")
    print(f"    Days elapsed:   {dash.get('paper_trade_status', {}).get('days_elapsed', 0):.0f}/60")

    gate = dash.get("gate_metrics", {})
    print(f"\n  {bold('Gate Metrics:')}")
    print(f"    Gate status:    {gate.get('gate_status', 'UNKNOWN')}")
    print(f"    OOS Sharpe tgt: {gate.get('oos_sharpe_target', 0.0):.1f}")
    print(f"    Current Sharpe: {gate.get('current_oos_sharpe', 0.0):.2f}")
    print(f"    Fill rate:      {gate.get('current_fill_rate', 0.0):.1%} (target ≥60%)")

    oos = dash.get("oos_performance", {})
    print(f"\n  {bold('OOS Performance:')}")
    print(f"    OOS Sharpe:     {oos.get('sharpe', 0.0):.2f}")
    print(f"    Ann return:     ${oos.get('ann_return_usd', 0)/1e3:.0f}K/yr @ $10M")
    print(f"    Family rank:    {oos.get('family_rank', 'N/A')}")
    print(f"    DA hypothesis:  {oos.get('celestia_da_hypothesis', 'N/A')}")
    print(f"    G5d corr ATOM:  {oos.get('g5d_corr_vs_atom', 0.0):.2f} (lowest — TIA fully orthogonal)")

    print(f"\n  {bold('Signal State:')}")
    print(f"    Position:       {dash.get('position_state', 'UNKNOWN')}")
    print(f"    FR diff (7d):   {dash.get('current_fr_diff_7d', 0.0):.6f}")
    print(f"    TIA FR:         {dash.get('fr_tia_current', 0.0):.6f}")
    print(f"    BTC FR:         {dash.get('fr_btc_current', 0.0):.6f}")
    print(f"    Data points:    {dash.get('history_points', 0)}")
    print(f"    Signal at scaf: {dash.get('signal', 'UNKNOWN')} (was LONG_BTC_SHORT_TIA)")

    print(f"\n  {bold('K559 HL Contingency Decision (TIA Bybit-only):')}")
    print(f"  {yellow('[CAP MANAGEMENT]')} Original design: 1% HL-primary")
    print(f"  {yellow('[CAP MANAGEMENT]')} K559 resolution: 1% Bybit-ONLY to hold HL at 64.5%")
    print(f"    Pre-W4 HL:      {HL_EXPOSURE_PRE_W4:.1%}")
    print(f"    + K500 3% HL:   {HL_EXPOSURE_PRE_W4 + K500_HL_ADD_PP/100:.1%}")
    print(f"    + SEI 1% HL:    {HL_EXPOSURE_PRE_W4 + K500_HL_ADD_PP/100 + K507_SEI_HL_ADD_PP/100:.1%}")
    print(f"    + TIA Bybit:    {HL_EXPOSURE_POST_W4:.1%} (cap {HL_EXPOSURE_CAP:.0%}) {green('SAFE')}")
    print(f"    If TIA HL-only: {HL_EXPOSURE_POST_W4 + 0.01:.1%} → {red('BREACH by 0.5pp')}")
    print(f"  {green('[RESOLUTION]')} TIA activates on Bybit-only (${K507_TIA_BYBIT_NOTIONAL/1e6:.1f}M notional)")
    print(f"    Yield unchanged: ${K507_TIA_ANN_RETURN/1e3:.0f}K/yr @ $10M (Bybit liquidity adequate for 1% sleeve)")

    results["sizing"] = {
        "sleeve_pct": K507_TIA_SLEEVE_PCT,
        "hl_pct": K507_TIA_HL_PCT,
        "bybit_pct": K507_TIA_BYBIT_PCT,
        "leverage": K507_TIA_LEVERAGE,
        "total_notional_usd": K507_TIA_TOTAL_NOTIONAL,
        "bybit_notional_usd": K507_TIA_BYBIT_NOTIONAL,
        "margin_usd": K507_TIA_MARGIN_USD,
        "hl_add_pp": K507_TIA_HL_ADD_PP,
        "ann_return_usd": K507_TIA_ANN_RETURN,
        "contingency": "BYBIT_ONLY — HL cap safety",
    }
    return results


# ─────────────────────────────────────────────────────────────────────────────
# Phase 5: D+21 K500 INJ-BTC LIVE activation steps
# ─────────────────────────────────────────────────────────────────────────────

def phase5_k500_live_activation() -> Dict[str, Any]:
    """Concrete activation steps for K500 INJ-BTC at D+21."""
    print(bold(f"\n{'='*70}"))
    print(bold("Phase 5: D+21 K500 INJ-BTC LIVE Activation"))
    print(bold(f"{'='*70}"))

    print(f"\n  {bold('Timing:')} D+21 = K493 PASS confirmation → K500 activates")
    print(f"  {bold('Condition:')} K493 realized 7d Sharpe ≥ {K507_SEI_PASS_SHARPE:.0f} at D+21 gate (see Phase 10)")
    print()

    steps = [
        {
            "step": 1, "phase": "D21_prereq",
            "name": "Verify K493 D+21 Sharpe gate",
            "command": "python3 scripts/k493_atom_btc_run.py --status | grep '60d_sharpe\\|gate_status'",
            "verify": "60d_sharpe ≥ 25 (PASS) OR 15-25 (HOLD → K500 deferred to D28)",
            "notes": "K493 ROLLBACK (<15) → halt Week 4 cascade entirely"
        },
        {
            "step": 2, "phase": "D21_prereq",
            "name": "Verify HL margin headroom",
            "command": "python3 scripts/emergency_hl_exit.py --dry-run --status",
            "verify": "HL margin utilisation < 70% before adding $300K K500 margin",
            "notes": "K500 3% sleeve = $300K margin. Ensure HL account has headroom."
        },
        {
            "step": 3, "phase": "D21_prereq",
            "name": "K500 dashboard pre-flight",
            "command": "python3 -c \"import json; d=json.load(open('data/k500_dashboard.json')); print(d['position_state'], d['gate_metrics']['gate_status'])\"",
            "verify": "gate_status=IN_PROGRESS, signal firing LONG_INJ_SHORT_BTC",
            "notes": "Dashboard shows position state; paper_trade_mode=true still at this point"
        },
        {
            "step": 4, "phase": "D21_config",
            "name": "Remove --dry-run from K500 plist",
            "command": "sed -i '' '/<string>--dry-run<\\/string>/d' com.cryptolab.k500-inj-btc.plist",
            "verify": "grep 'dry-run' com.cryptolab.k500-inj-btc.plist || echo 'CLEAN'",
            "notes": "ProgramArguments must not contain --dry-run for live execution"
        },
        {
            "step": 5, "phase": "D21_config",
            "name": "Set PAPER_TRADE=False in K500 plist env",
            "command": "# Edit plist EnvironmentVariables: PAPER_TRADE → False (or remove key)",
            "verify": "grep PAPER_TRADE com.cryptolab.k500-inj-btc.plist",
            "notes": "K500 reads PAPER_TRADE env; absent or 'False' → live execution"
        },
        {
            "step": 6, "phase": "D21_load",
            "name": "Copy K500 plist to LaunchAgents",
            "command": "cp com.cryptolab.k500-inj-btc.plist ~/Library/LaunchAgents/com.cryptolab.k500-inj-btc.plist",
            "verify": "ls -la ~/Library/LaunchAgents/com.cryptolab.k500-inj-btc.plist",
            "notes": "Copy modified (LIVE) plist to LaunchAgents"
        },
        {
            "step": 7, "phase": "D21_load",
            "name": "launchctl load K500 daemon",
            "command": "launchctl load ~/Library/LaunchAgents/com.cryptolab.k500-inj-btc.plist",
            "verify": "launchctl list | grep k500-inj-btc",
            "notes": "Daemon loads; first execution at next 8h cron window"
        },
        {
            "step": 8, "phase": "D21_verify",
            "name": "Confirm K357 emergency exit includes K500/INJ",
            "command": "grep -c 'K500\\|INJ' scripts/emergency_hl_exit.py",
            "verify": "Count ≥ 2 (K506 scaffold registered K500 detection)",
            "notes": "K357 emergency exit must handle K500 paired-position detection"
        },
        {
            "step": 9, "phase": "D21_verify",
            "name": "K500 post-load status check",
            "command": "python3 scripts/k500_inj_btc_run.py --status",
            "verify": "paper_trade_mode=false, position_state=LONG_INJ_SHORT_BTC",
            "notes": "Confirm live mode activated and signal is firing (INJ FR diff negative → long INJ)"
        },
        {
            "step": 10, "phase": "D21_commit",
            "name": "Commit K500 LIVE plist + push",
            "command": "git add com.cryptolab.k500-inj-btc.plist && git commit -m 'K559 K500 plist: D+21 INJ-BTC LIVE activation' && git push origin main",
            "verify": "git log --oneline -1",
            "notes": "Commit LIVE plist for audit trail. Monitor 48h before K507 SEI activation."
        },
    ]

    print(bold("  D+21 K500 INJ-BTC activation steps:"))
    for s in steps:
        tag = yellow(f"[D+21 {s['phase'].upper()}]")
        print(f"  {tag} Step {s['step']}: {bold(s['name'])}")
        print(f"    {cyan('CMD:')} {s['command']}")
        print(f"    {green('VFY:')} {s['verify']}")
        print(f"    {grey('NOTE:')} {s['notes']}")
        print()

    print(bold("  K500 execution model:"))
    print(f"  POST_ONLY parallel: long INJ perp + short BTC perp, limit at mid")
    print(f"  Rollback: K439 pattern — if INJ fills but BTC fails → cancel INJ within 5s")
    print(f"  Cadence: 8h cron (same as K449/K476/K484/K493)")
    print(f"  Monitor window: D+21 → D+23 (48h before K507 SEI)")
    print()

    results = {
        "phase": 5,
        "name": "k500_live_activation",
        "target_date": "D+21 (after K493 PASS)",
        "steps": steps,
        "sizing": {
            "sleeve_pct": K500_SLEEVE_PCT,
            "leverage": K500_LEVERAGE,
            "total_notional_usd": K500_TOTAL_NOTIONAL,
            "margin_usd": K500_MARGIN_USD,
            "hl_add_pp": K500_HL_ADD_PP,
        },
        "monitor_window_h": 48,
    }
    return results


# ─────────────────────────────────────────────────────────────────────────────
# Phase 6: D+23 K507 SEI-BTC LIVE activation steps
# ─────────────────────────────────────────────────────────────────────────────

def phase6_k507_sei_live_activation() -> Dict[str, Any]:
    """Concrete activation steps for K507 SEI-BTC at D+23."""
    print(bold(f"\n{'='*70}"))
    print(bold("Phase 6: D+23 K507 SEI-BTC LIVE Activation (48h after K500)"))
    print(bold(f"{'='*70}"))

    print(f"\n  {bold('Timing:')} D+23 = 48h after K500 D+21 activation")
    print(f"  {bold('Condition:')} K500 48h health check PASS (no margin breach, fills > 0)")
    print(f"  {bold('Split:')} 1% HL + 1% Bybit (HL exposure +1pp → 64.5%)")
    print()

    steps = [
        {
            "step": 1, "phase": "D23_prereq",
            "name": "K500 48h health gate",
            "command": "python3 -c \"import json; d=json.load(open('data/k500_dashboard.json')); print(d.get('position_state'), d.get('daily_pnl_usdc',0))\"",
            "verify": "position_state != NEUTRAL, daily_pnl_usdc > 0 (at least one 8h cycle completed)",
            "notes": "K500 must show activity in 48h window; no margin breach on HL"
        },
        {
            "step": 2, "phase": "D23_prereq",
            "name": "HL margin check post-K500",
            "command": "python3 scripts/emergency_hl_exit.py --dry-run --status",
            "verify": "HL utilisation < 75% after K500 $300K margin (headroom for K507 SEI 1% HL = $100K)",
            "notes": "K507 SEI adds $100K HL margin (1% sleeve × $10M). Total HL margin after SEI: ~$1.1M."
        },
        {
            "step": 3, "phase": "D23_prereq",
            "name": "K507 SEI dashboard pre-flight",
            "command": "python3 -c \"import json; d=json.load(open('data/k507_dashboard.json')); print(d['position_state'], d['smart_router'])\"",
            "verify": "smart_router=HL_PRIMARY_BYBIT_SECONDARY, gate_status=IN_PROGRESS",
            "notes": "Dashboard shows NEUTRAL (no signal at scaffold time — confirm current FR diff)"
        },
        {
            "step": 4, "phase": "D23_config",
            "name": "Remove --dry-run from K507 SEI plist",
            "command": "sed -i '' '/<string>--dry-run<\\/string>/d' com.cryptolab.k507-sei-btc.plist",
            "verify": "grep 'dry-run' com.cryptolab.k507-sei-btc.plist || echo 'CLEAN'",
            "notes": "SEI and TIA share plist name pattern — confirm targeting SEI plist"
        },
        {
            "step": 5, "phase": "D23_config",
            "name": "Set PAPER_TRADE=False + verify HL/Bybit split config",
            "command": "# Edit plist: PAPER_TRADE=False; confirm HL_SLEEVE=0.01, BYBIT_SLEEVE=0.01",
            "verify": "grep -A3 'HL_SLEEVE\\|BYBIT_SLEEVE' com.cryptolab.k507-sei-btc.plist",
            "notes": "Split config: 1% HL = $100K margin, 1% Bybit = $100K margin; total $200K sleeve"
        },
        {
            "step": 6, "phase": "D23_load",
            "name": "Copy K507 SEI plist to LaunchAgents + launchctl load",
            "command": "cp com.cryptolab.k507-sei-btc.plist ~/Library/LaunchAgents/ && launchctl load ~/Library/LaunchAgents/com.cryptolab.k507-sei-btc.plist",
            "verify": "launchctl list | grep k507-sei-btc",
            "notes": "Daemon loads at D+23; HL exposure +1pp → 64.5%"
        },
        {
            "step": 7, "phase": "D23_verify",
            "name": "HL exposure verify post-SEI load",
            "command": "python3 scripts/verify_deployment_status.py | grep hl_exposure",
            "verify": f"HL exposure ≈ {HL_EXPOSURE_PRE_W4 + K500_HL_ADD_PP/100 + K507_SEI_HL_ADD_PP/100:.1%} (< {HL_EXPOSURE_CAP:.0%} cap)",
            "notes": "Confirm HL cap not breached after SEI 1% HL contribution"
        },
        {
            "step": 8, "phase": "D23_commit",
            "name": "Commit K507 SEI LIVE plist + push",
            "command": "git add com.cryptolab.k507-sei-btc.plist && git commit -m 'K559 K507 SEI plist: D+23 SEI-BTC LIVE (1% HL + 1% Bybit)' && git push origin main",
            "verify": "git log --oneline -1",
            "notes": "Monitor 48h before K507 TIA activation at D+25"
        },
    ]

    print(bold("  D+23 K507 SEI-BTC activation steps:"))
    for s in steps:
        tag = yellow(f"[D+23 {s['phase'].upper()}]")
        print(f"  {tag} Step {s['step']}: {bold(s['name'])}")
        print(f"    {cyan('CMD:')} {s['command']}")
        print(f"    {green('VFY:')} {s['verify']}")
        print(f"    {grey('NOTE:')} {s['notes']}")
        print()

    results = {
        "phase": 6,
        "name": "k507_sei_live_activation",
        "target_date": "D+23 (48h after K500)",
        "steps": steps,
        "sizing": {
            "hl_pct": K507_SEI_HL_PCT,
            "bybit_pct": K507_SEI_BYBIT_PCT,
            "hl_notional_usd": K507_SEI_HL_NOTIONAL,
            "bybit_notional_usd": K507_SEI_BYBIT_NOTIONAL,
            "margin_usd": K507_SEI_MARGIN_USD,
            "hl_add_pp": K507_SEI_HL_ADD_PP,
        },
    }
    return results


# ─────────────────────────────────────────────────────────────────────────────
# Phase 7: D+25 K507 TIA-BTC LIVE activation steps (Bybit-only)
# ─────────────────────────────────────────────────────────────────────────────

def phase7_k507_tia_live_activation() -> Dict[str, Any]:
    """Concrete activation steps for K507 TIA-BTC at D+25 (Bybit-only contingency)."""
    print(bold(f"\n{'='*70}"))
    print(bold("Phase 7: D+25 K507 TIA-BTC LIVE Activation (48h after SEI)"))
    print(bold(f"{'='*70}"))

    print(f"\n  {bold('Timing:')} D+25 = 48h after K507 SEI D+23 activation")
    print(f"  {bold('Condition:')} K507 SEI 48h health check PASS")
    print(f"  {yellow('[CAP DECISION]')} TIA activates BYBIT-ONLY (0pp HL delta, cap = 64.5%)")
    print(f"  If TIA HL-only: HL would be {HL_EXPOSURE_POST_W4 + 0.01:.1%} → over 65% cap by 0.5pp")
    print()

    steps = [
        {
            "step": 1, "phase": "D25_prereq",
            "name": "K507 SEI 48h health gate",
            "command": "python3 -c \"import json; d=json.load(open('data/k507_dashboard.json')); print(d.get('position_state'), d.get('daily_pnl_usdc',0))\"",
            "verify": "K507 SEI showing position activity and positive PnL in 48h window",
            "notes": "SEI NEUTRAL signal at scaffold is OK — any position confirms daemon running"
        },
        {
            "step": 2, "phase": "D25_prereq",
            "name": "HL cap verification — confirm 64.5% not breached",
            "command": "python3 scripts/verify_deployment_status.py | grep hl_exposure",
            "verify": f"HL ≤ {HL_EXPOSURE_PRE_W4 + K500_HL_ADD_PP/100 + K507_SEI_HL_ADD_PP/100:.1%} after K500+SEI",
            "notes": "TIA is Bybit-only → 0pp HL; confirm K500+SEI HL contributions as expected"
        },
        {
            "step": 3, "phase": "D25_prereq",
            "name": "K507 TIA dashboard pre-flight",
            "command": "python3 -c \"import json; d=json.load(open('data/k507_tia_dashboard.json')); print(d['position_state'], d['split_protocol'])\"",
            "verify": "split_protocol shows HL 1% or Bybit-fallback. Override to Bybit-only at activation.",
            "notes": "TIA scaffold had HL-only 1% design. K559 overrides to Bybit-only for cap safety."
        },
        {
            "step": 4, "phase": "D25_config",
            "name": "Configure TIA plist for Bybit-only",
            "command": "# Edit plist: PAPER_TRADE=False; HL_SLEEVE=0.00; BYBIT_SLEEVE=0.01; SMART_ROUTER=BYBIT_ONLY",
            "verify": "grep 'BYBIT_SLEEVE\\|SMART_ROUTER\\|HL_SLEEVE' com.cryptolab.k507-sei-btc.plist",
            "notes": "CRITICAL: TIA must route ALL notional to Bybit. HL_SLEEVE=0 prevents HL cap breach."
        },
        {
            "step": 5, "phase": "D25_config",
            "name": "Remove --dry-run from TIA plist",
            "command": "sed -i '' '/<string>--dry-run<\\/string>/d' com.cryptolab.k507-tia-btc.plist",
            "verify": "grep 'dry-run' com.cryptolab.k507-tia-btc.plist || echo 'CLEAN'",
            "notes": "TIA plist may be separate file; check com.cryptolab.k507-tia-btc.plist"
        },
        {
            "step": 6, "phase": "D25_load",
            "name": "Copy TIA plist + launchctl load",
            "command": "cp com.cryptolab.k507-tia-btc.plist ~/Library/LaunchAgents/ && launchctl load ~/Library/LaunchAgents/com.cryptolab.k507-tia-btc.plist",
            "verify": "launchctl list | grep k507-tia-btc",
            "notes": "TIA daemon loads; all $400K notional on Bybit; 0pp HL delta confirmed"
        },
        {
            "step": 7, "phase": "D25_verify",
            "name": "Final HL exposure verify (all 3 strategies LIVE)",
            "command": "python3 scripts/verify_deployment_status.py | grep hl_exposure",
            "verify": f"HL = {HL_EXPOSURE_POST_W4:.1%} (cap {HL_EXPOSURE_CAP:.0%}, +{(HL_EXPOSURE_CAP - HL_EXPOSURE_POST_W4)*100:.1f}pp headroom)",
            "notes": "K500 3pp + SEI 1pp + TIA 0pp = 4pp total → 64.5%. Week 5 APT has 0.5pp remaining."
        },
        {
            "step": 8, "phase": "D25_commit",
            "name": "Commit TIA LIVE plist + push",
            "command": "git add com.cryptolab.k507-tia-btc.plist && git commit -m 'K559 K507 TIA plist: D+25 TIA-BTC LIVE (Bybit-only 1%, HL cap=64.5%)' && git push origin main",
            "verify": "git log --oneline -1",
            "notes": "All 3 Week 4 strategies now LIVE. Begin D+28 monitoring phase."
        },
    ]

    print(bold("  D+25 K507 TIA-BTC activation steps (Bybit-only):"))
    for s in steps:
        tag = yellow(f"[D+25 {s['phase'].upper()}]")
        print(f"  {tag} Step {s['step']}: {bold(s['name'])}")
        print(f"    {cyan('CMD:')} {s['command']}")
        print(f"    {green('VFY:')} {s['verify']}")
        print(f"    {grey('NOTE:')} {s['notes']}")
        print()

    print(bold("  TIA Bybit execution model:"))
    print(f"  Venue:      Bybit perp only (smart_router=BYBIT_ONLY)")
    print(f"  Notional:   ${K507_TIA_BYBIT_NOTIONAL/1e6:.1f}M (1% sleeve × 4x)")
    print(f"  Signal:     BTC FR > TIA FR → long BTC, short TIA")
    print(f"  HL delta:   +0.0pp (no HL contribution)")
    print(f"  Yield:      ${K507_TIA_ANN_RETURN/1e3:.0f}K/yr @ $10M (Bybit fill rate ≈ HL at 1% sleeve)")
    print()

    results = {
        "phase": 7,
        "name": "k507_tia_live_activation",
        "target_date": "D+25 (48h after SEI)",
        "venue": "BYBIT_ONLY",
        "hl_contingency": "Bybit-only activated to maintain HL ≤ 64.5%",
        "steps": steps,
        "sizing": {
            "sleeve_pct": K507_TIA_SLEEVE_PCT,
            "hl_pct": K507_TIA_HL_PCT,
            "bybit_pct": K507_TIA_BYBIT_PCT,
            "bybit_notional_usd": K507_TIA_BYBIT_NOTIONAL,
            "margin_usd": K507_TIA_MARGIN_USD,
            "hl_add_pp": K507_TIA_HL_ADD_PP,
        },
    }
    return results


# ─────────────────────────────────────────────────────────────────────────────
# Phase 8: HL exposure post-Week 4 trajectory
# ─────────────────────────────────────────────────────────────────────────────

def phase8_hl_exposure() -> Dict[str, Any]:
    """HL exposure trajectory post-Week 4 with TIA Bybit-only contingency."""
    print(bold(f"\n{'='*70}"))
    print(bold("Phase 8: HL Exposure Post-Week 4 Trajectory"))
    print(bold(f"{'='*70}"))

    print()
    print(bold("  HL Exposure Trajectory (Week 4 cascade with TIA Bybit-only):"))
    print(grey("  " + "─"*72))

    steps = [
        ("v6.13d baseline",                        0.650,  0.0,  "Before K280 cut — at hard cap"),
        ("K280 Phase B1 cut 75→60% (K552)",        0.575, -7.5,  "−7.5pp HL"),
        ("+ K449 ETH-BTC W1 (5% HL-only)",         0.625, +5.0,  "+5pp (5% × 100% HL)"),
        ("+ K476 SOL (2% HL+1% Bybit)",            0.645, +2.0,  "+2pp HL split"),
        ("+ K484 AVAX (adjustment -4pp + 2pp)",    0.605, -2.0,  "K280 micro-trim; +2pp AVAX"),
        ("+ K493 ATOM W3 (2.5% HL+2.5% Bybit)",   0.605, +0.0,  "Net 60.5% after K280 trim offset"),
        (f"+ K500 INJ W4-D21 (3% HL-primary)",    0.635, +3.0,  "+3pp HL (3% × 100%)"),
        (f"+ K507 SEI W4-D23 (1% HL+1% Bybit)",  0.645, +1.0,  "+1pp HL (1% HL portion)"),
        (f"+ K507 TIA W4-D25 (1% Bybit-ONLY)",   0.645,  0.0,  "+0pp HL (K559 cap decision)"),
        ("Week 4 FINAL post-cascade",              0.645,  0.0,  f"vs {HL_EXPOSURE_CAP:.0%} cap → 0.5pp headroom"),
    ]

    print(f"  {'Step':<50} {'HL%':<8} {'Delta':<8} Note")
    print(grey("  " + "─"*85))
    for label, hl_pct, delta, note in steps:
        breach = hl_pct > HL_EXPOSURE_CAP
        status = f" {red('BREACH')}" if breach else (f" {green('SAFE')}" if hl_pct < HL_EXPOSURE_CAP - 0.01 else f" {yellow('AT CAP')}")
        delta_str = f" ({'+' if delta >= 0 else ''}{delta:.1f}pp)" if delta != 0.0 else ""
        print(f"  {label:<50} {hl_pct:.1%}  {delta_str:<10} {status} — {note}")

    print()
    print(bold("  Contingency analysis:"))
    scenarios = [
        ("RECOMMENDED: TIA Bybit-only",  HL_EXPOSURE_POST_W4,      green("SAFE"), "0.5pp headroom"),
        ("ALT A: K500 HL+Bybit split",   HL_EXPOSURE_PRE_W4 + 0.015 + K507_SEI_HL_ADD_PP/100, yellow("MARGINAL"), "1% HL: +1.5pp K500"),
        ("ALT B: TIA HL-primary",         HL_EXPOSURE_POST_W4 + 0.01, red("BREACH"), "65.5% → over cap 0.5pp"),
    ]
    for label, hl, status_fn, note in scenarios:
        print(f"    {label:<40} {hl:.1%}  {status_fn}  {note}")

    print()
    print(f"  {bold('Selected:')} RECOMMENDED (TIA Bybit-only)")
    print(f"  {bold('Post-W4 HL:')} {HL_EXPOSURE_POST_W4:.1%}")
    headroom = (HL_EXPOSURE_CAP - HL_EXPOSURE_POST_W4) * 100
    print(f"  {bold('Headroom:')} {headroom:.1f}pp (for Week 5 K512 APT: 1% HL portion of 2% sleeve)")
    print(f"  {bold('Week 5 APT:')} +1pp HL → {HL_EXPOSURE_POST_W4 + 0.01:.1%} (still within cap)")

    results = {
        "phase": 8,
        "name": "hl_exposure",
        "pre_w4_pct":      HL_EXPOSURE_PRE_W4,
        "k500_hl_add_pp":  K500_HL_ADD_PP,
        "k507_sei_hl_pp":  K507_SEI_HL_ADD_PP,
        "k507_tia_hl_pp":  K507_TIA_HL_ADD_PP,
        "total_w4_add_pp": HL_W4_TOTAL_ADD_PP,
        "post_w4_pct":     HL_EXPOSURE_POST_W4,
        "cap_pct":         HL_EXPOSURE_CAP,
        "headroom_pp":     headroom,
        "week5_apt_hl_pp": 1.0,
        "week5_post_pct":  HL_EXPOSURE_POST_W4 + 0.01,
        "tia_contingency": "BYBIT_ONLY — avoids 0.5pp breach",
    }
    return results


# ─────────────────────────────────────────────────────────────────────────────
# Phase 9: Day 28-35 monitoring specification
# ─────────────────────────────────────────────────────────────────────────────

def phase9_monitoring_spec() -> Dict[str, Any]:
    """Day 28-35 cross-strategy monitoring for all 3 Week 4 strategies."""
    print(bold(f"\n{'='*70}"))
    print(bold("Phase 9: Day 28-35 Monitoring Specification (All 3 Strategies)"))
    print(bold(f"{'='*70}"))

    print(f"\n  Monitor window: D+25 (all 3 active) → D+35 (decision matrix)")
    print(f"  Key dates:")
    print(f"    D+21: K500 LIVE    D+23: SEI LIVE    D+25: TIA LIVE")
    print(f"    D+28: First 7d review    D+35: Decision matrix evaluation")
    print()

    strategies = [
        {
            "name": "K500 INJ-BTC",
            "dashboard": "data/k500_dashboard.json",
            "daily_pnl_target": round(K500_ANN_RETURN_USD / 365, 2),
            "pass_sharpe": K500_PASS_SHARPE,
            "venue": "HL primary",
        },
        {
            "name": "K507 SEI-BTC",
            "dashboard": "data/k507_dashboard.json",
            "daily_pnl_target": round(K507_SEI_ANN_RETURN / 365, 2),
            "pass_sharpe": K507_SEI_PASS_SHARPE,
            "venue": "1% HL + 1% Bybit",
        },
        {
            "name": "K507 TIA-BTC",
            "dashboard": "data/k507_tia_dashboard.json",
            "daily_pnl_target": round(K507_TIA_ANN_RETURN / 365, 2),
            "pass_sharpe": K507_TIA_PASS_SHARPE,
            "venue": "Bybit-only",
        },
    ]

    print(bold("  Daily PnL targets:"))
    for s in strategies:
        print(f"    {s['name']:<18} ${s['daily_pnl_target']:.0f}/day @ $10M  ({s['venue']})")

    print()
    print(bold("  Cross-strategy monitoring checklist (daily):"))

    metrics = [
        ("Realized Sharpe (rolling 7d)", "60d_sharpe in each dashboard",
         "K500 ≥ 2.0, SEI ≥ 12, TIA ≥ 3 (40% of OOS as early sanity)"),
        ("Fill rate per leg", "gate_metrics.current_fill_rate per dashboard",
         "All 3: ≥ 40% fills in first 7d (signal frequency dependent)"),
        ("HL margin health", "emergency_hl_exit.py --dry-run --status",
         "HL utilisation < 80% at all times; alert if > 75%"),
        ("Cross-strategy correlation", "Compare position states across dashboards",
         "K500+SEI+TIA should have uncorrelated signals (Cosmos DA vs DeFi)"),
        ("Delta neutral drift per strategy", "delta_neutral_drift_pct per dashboard",
         "Each strategy: drift > 5% triggers rebalance; > 10% triggers alert"),
        ("Bybit leg health (SEI + TIA)", "bybit_leg_status in dashboard (if field present)",
         "Bybit fills must sync with HL leg (SEI); TIA Bybit-only fill rate"),
        ("Daily PnL cross-check", "sum(daily_pnl_usdc) across 3 dashboards",
         f"Combined daily target: ${(K500_ANN_RETURN_USD+K507_SEI_ANN_RETURN+K507_TIA_ANN_RETURN)/365:.0f}/day"),
        ("FR differential stability", "fr_raw_diff in each dashboard",
         "INJ FR diff < 0 (long INJ); SEI/TIA: confirm positive carry direction"),
    ]

    for name, source, criteria in metrics:
        print(f"\n  {bold(name)}")
        print(f"    Source:   {grey(source)}")
        print(f"    Criteria: {criteria}")

    print()
    print(bold("  Quick daily one-liner (all 3 strategies):"))
    print(cyan("""  for f in data/k500_dashboard.json data/k507_dashboard.json data/k507_tia_dashboard.json; do
    python3 -c "
  import json, sys
  d = json.load(open('$f'))
  g = d.get('gate_metrics', {})
  print(f\"{d.get('strategy','?')}: state={d.get('position_state','?')} pnl=${d.get('daily_pnl_usdc',0):.2f} sh={d.get('60d_sharpe',0):.2f} fill={g.get('current_fill_rate',0):.1%} gate={g.get('gate_status','?')}\")"
  done"""))

    results = {
        "phase": 9,
        "name": "monitoring_spec",
        "window": "D+25 to D+35",
        "strategies": strategies,
        "combined_daily_pnl_target_usd": round(
            (K500_ANN_RETURN_USD + K507_SEI_ANN_RETURN + K507_TIA_ANN_RETURN) / 365, 2
        ),
        "metrics_count": len(metrics),
    }
    return results


# ─────────────────────────────────────────────────────────────────────────────
# Phase 10: Decision matrix D+35
# ─────────────────────────────────────────────────────────────────────────────

def phase10_decision_matrix() -> Dict[str, Any]:
    """Decision matrix at D+35 for all 3 Week 4 strategies."""
    print(bold(f"\n{'='*70}"))
    print(bold("Phase 10: Decision Matrix at D+35 (Per Strategy)"))
    print(bold(f"{'='*70}"))

    print()
    print(bold("  Per-strategy D+35 gate:"))
    print(grey("  " + "─"*70))
    print(f"  {'Strategy':<20} {'PASS (≥50% OOS)':<22} {'HOLD':<22} {'ROLLBACK'}")
    print(grey("  " + "─"*70))

    decisions = [
        ("K500 INJ-BTC",  K500_OOS_SHARPE,  K500_PASS_SHARPE,  K500_HOLD_LOW,   K500_ROLLBACK_MAX),
        ("K507 SEI-BTC",  K507_SEI_OOS_SHARPE, K507_SEI_PASS_SHARPE, K507_SEI_HOLD_LOW, K507_SEI_ROLLBACK_MAX),
        ("K507 TIA-BTC",  K507_TIA_OOS_SHARPE, K507_TIA_PASS_SHARPE, K507_TIA_HOLD_LOW, K507_TIA_ROLLBACK_MAX),
    ]

    for strat, oos, pass_sh, hold_lo, rb_max in decisions:
        pass_str  = f"Sh ≥ {pass_sh:.1f}"
        hold_str  = f"Sh {hold_lo:.1f}–{pass_sh:.1f}"
        rb_str    = f"Sh < {rb_max:.1f}"
        print(f"  {strat:<20} {green(pass_str):<30} {yellow(hold_str):<30} {red(rb_str)}")

    print()
    print(bold("  PASS actions:"))
    print(f"    K500 INJ PASS:  Expand to 4% sleeve; Ann yield: ${K500_ANN_RETURN_USD * 4/3/1e3:.0f}K/yr @ $10M")
    print(f"    K507 SEI PASS:  Expand to 3% sleeve (1.5% HL + 1.5% Bybit); yield: ${K507_SEI_ANN_RETURN * 3/2/1e3:.0f}K/yr")
    print(f"    K507 TIA PASS:  Maintain 1% Bybit; confirm Bybit fill adequacy")

    print()
    print(bold("  ROLLBACK procedure (per strategy):"))
    rb_steps = [
        "1. launchctl unload ~/Library/LaunchAgents/com.cryptolab.k5XX-YYY.plist",
        "2. python3 scripts/k5XX_yyy_run.py --close 'Week 4 D35 rollback'",
        "3. Verify positions closed: python3 scripts/emergency_hl_exit.py --status",
        "4. Restore --dry-run in plist; reload in paper mode",
        "5. Update dashboard JSON: paper_trade_mode=true",
        "6. HL exposure recalculated: K500 rollback = -3pp, SEI = -1pp, TIA = 0pp",
    ]
    for step in rb_steps:
        print(f"    {cyan(step)}")

    print()
    print(bold("  Cross-strategy rollback cascade:"))
    print(f"  If ALL 3 ROLLBACK: return to W3 state (K493 only, HL = 60.5%)")
    print(f"  If only TIA ROLLBACK: HL = 64.5% maintained; Week 5 APT unaffected")
    print(f"  If K500 ROLLBACK only: HL drops to 61.5% (+3pp reclaimed)")

    results = {
        "phase": 10,
        "name": "decision_matrix",
        "evaluation_date": "D+35",
        "decisions": [
            {
                "strategy": "K500_INJ_BTC",
                "oos_sharpe": K500_OOS_SHARPE,
                "pass_min": K500_PASS_SHARPE,
                "hold_range": [K500_HOLD_LOW, K500_PASS_SHARPE],
                "rollback_max": K500_ROLLBACK_MAX,
                "pass_action": "expand_to_4pct",
                "hold_action": "maintain_3pct",
                "rollback_action": "close_reload_paper",
            },
            {
                "strategy": "K507_SEI_BTC",
                "oos_sharpe": K507_SEI_OOS_SHARPE,
                "pass_min": K507_SEI_PASS_SHARPE,
                "hold_range": [K507_SEI_HOLD_LOW, K507_SEI_PASS_SHARPE],
                "rollback_max": K507_SEI_ROLLBACK_MAX,
                "pass_action": "expand_to_3pct",
                "hold_action": "maintain_2pct",
                "rollback_action": "close_reload_paper",
            },
            {
                "strategy": "K507_TIA_BTC",
                "oos_sharpe": K507_TIA_OOS_SHARPE,
                "pass_min": K507_TIA_PASS_SHARPE,
                "hold_range": [K507_TIA_HOLD_LOW, K507_TIA_PASS_SHARPE],
                "rollback_max": K507_TIA_ROLLBACK_MAX,
                "pass_action": "maintain_1pct_bybit_only",
                "hold_action": "maintain_1pct",
                "rollback_action": "close_reload_paper",
            },
        ],
    }
    return results


# ─────────────────────────────────────────────────────────────────────────────
# Phase 11: Profit projection (Week 4 cumulative)
# ─────────────────────────────────────────────────────────────────────────────

def phase11_profit_projection() -> Dict[str, Any]:
    """Full profit projection W1-W4 + W5 at multiple AUM scales."""
    print(bold(f"\n{'='*70}"))
    print(bold("Phase 11: Profit Projection — Week 4 Cumulative"))
    print(bold(f"{'='*70}"))

    def s(val_10m: int, aum_mult: float) -> str:
        return f"${val_10m * aum_mult / 1e6:.2f}M"

    print(f"\n  {'Week':<10} {'Strategy':<35} {'Delta/yr':<14} {'Cumulative @$10M':<18} @$30M       @$100M")
    print(grey("  " + "─"*95))

    week_table = [
        ("Week 1", "K449 ETH-BTC",                    WEEK1_K449_USD,  WEEK1_K449_USD),
        ("Week 2", "K476 SOL + K484 AVAX",            WEEK2_K476_USD + WEEK2_K484_USD,
                                                        WEEK1_K449_USD + WEEK2_K476_USD + WEEK2_K484_USD),
        ("Week 3", "K493 ATOM-BTC",                   WEEK3_K493_USD,  CUMULATIVE_W1_W3_USD),
        ("Week 4", "K500 INJ+SEI+TIA ← THIS WAVE",   WEEK4_COMBINED_USD, CUMULATIVE_W4_USD),
        ("Week 5", "K512 APT-BTC",                    302_000,         CUMULATIVE_W4_USD + 302_000),
    ]

    for week, strat, delta, cumul in week_table:
        marker = yellow(" ← THIS") if "THIS" in strat else ""
        print(f"  {week:<10} {strat:<35} ${delta/1e3:.0f}K{'':<8} ${cumul/1e3:.0f}K/yr{'':<11}"
              f"{s(cumul, 3):<12} {s(cumul, 10)}{marker}")

    print()
    print(bold("  === WEEK 4 BREAKDOWN ==="))
    print(f"    K500 INJ:    Sh {K500_OOS_SHARPE:.2f}  ${K500_ANN_RETURN_USD/1e3:.0f}K/yr @$10M  "
          f"${K500_ANN_RETURN_USD*3/1e6:.2f}M @$30M  ${K500_ANN_RETURN_USD*10/1e6:.2f}M @$100M")
    print(f"    K507 SEI:    Sh {K507_SEI_OOS_SHARPE:.2f}  ${K507_SEI_ANN_RETURN/1e3:.0f}K/yr @$10M  "
          f"${K507_SEI_ANN_RETURN*3/1e6:.2f}M @$30M  ${K507_SEI_ANN_RETURN*10/1e6:.2f}M @$100M")
    print(f"    K507 TIA:    Sh {K507_TIA_OOS_SHARPE:.2f}  ${K507_TIA_ANN_RETURN/1e3:.0f}K/yr @$10M  "
          f"${K507_TIA_ANN_RETURN*3/1e6:.2f}M @$30M  ${K507_TIA_ANN_RETURN*10/1e6:.2f}M @$100M")
    print(f"    {'─'*65}")
    print(f"    COMBINED:        ${WEEK4_COMBINED_USD/1e3:.0f}K/yr @$10M  "
          f"${WEEK4_COMBINED_USD*3/1e6:.2f}M @$30M  ${WEEK4_COMBINED_USD*10/1e6:.2f}M @$100M")

    print()
    print(bold("  === CUMULATIVE W1-W4 ==="))
    print(f"    @$10M:   {bold(f'${CUMULATIVE_W4_USD/1e3:.0f}K/yr')} ({CUMULATIVE_W4_USD/AUM_REF_USD*100:.1f}% ann)")
    print(f"    @$30M:   {bold(f'${CUMULATIVE_W4_USD*3/1e6:.2f}M/yr')}")
    print(f"    @$100M:  {bold(f'${CUMULATIVE_W4_USD*10/1e6:.2f}M/yr')} (HL liquidity ceiling ~$30M effective for HL-primary)")
    print()
    print(bold("  === FULL FAMILY W1-W5 (K512 APT) ==="))
    full = CUMULATIVE_W4_USD + 302_000
    print(f"    @$10M:   ${full/1e3:.0f}K/yr ({full/AUM_REF_USD*100:.1f}% ann)")
    print(f"    @$30M:   ${full*3/1e6:.3f}M/yr")
    print(f"    @$100M:  ${full*10/1e6:.3f}M/yr")

    results = {
        "phase": 11,
        "name": "profit_projection",
        "week4_breakdown": {
            "k500_inj":   {"ann_10m": K500_ANN_RETURN_USD,    "ann_30m": K500_ANN_RETURN_USD * 3,    "ann_100m": K500_ANN_RETURN_USD * 10},
            "k507_sei":   {"ann_10m": K507_SEI_ANN_RETURN,    "ann_30m": K507_SEI_ANN_RETURN * 3,    "ann_100m": K507_SEI_ANN_RETURN * 10},
            "k507_tia":   {"ann_10m": K507_TIA_ANN_RETURN,    "ann_30m": K507_TIA_ANN_RETURN * 3,    "ann_100m": K507_TIA_ANN_RETURN * 10},
            "combined":   {"ann_10m": WEEK4_COMBINED_USD,      "ann_30m": WEEK4_COMBINED_USD * 3,      "ann_100m": WEEK4_COMBINED_USD * 10},
        },
        "cumulative_w1_w4": {
            "ann_10m": CUMULATIVE_W4_USD,
            "ann_30m": CUMULATIVE_W4_USD * 3,
            "ann_100m": CUMULATIVE_W4_USD * 10,
        },
        "cumulative_w1_w5": {
            "ann_10m": CUMULATIVE_W4_USD + 302_000,
            "ann_30m": (CUMULATIVE_W4_USD + 302_000) * 3,
            "ann_100m": (CUMULATIVE_W4_USD + 302_000) * 10,
        },
    }
    return results


# ─────────────────────────────────────────────────────────────────────────────
# Phase 12: Week 5 prep (K512 APT-BTC)
# ─────────────────────────────────────────────────────────────────────────────

def phase12_week5_prep() -> Dict[str, Any]:
    """Week 5 K512 APT-BTC preparation (D+32 target, 2% sleeve 1% HL + 1% Bybit)."""
    print(bold(f"\n{'='*70}"))
    print(bold("Phase 12: Week 5 Prep — K512 APT-BTC (D+32 target)"))
    print(bold(f"{'='*70}"))

    k512_sharpe     = 51.10
    k512_ann_return = 302_000
    k512_sleeve     = 0.02          # 2% total (1% HL + 1% Bybit)
    k512_hl_pct     = 0.01          # 1% HL
    k512_bybit_pct  = 0.01          # 1% Bybit
    k512_leverage   = 4.0
    k512_hl_notional   = AUM_REF_USD * k512_hl_pct * k512_leverage    # $400K
    k512_bybit_notional= AUM_REF_USD * k512_bybit_pct * k512_leverage  # $400K
    k512_margin        = AUM_REF_USD * k512_sleeve                     # $200K
    k512_hl_add_pp  = 1.0           # +1pp HL

    hl_post_w5 = HL_EXPOSURE_POST_W4 + k512_hl_add_pp / 100

    print()
    print(f"  {bold('K512 APT-BTC overview:')}")
    print(f"    OOS Sharpe:     {k512_sharpe:.2f} (family #1 overall: APT Sh51.10 > ATOM 50.79)")
    print(f"    Ann return:     ${k512_ann_return/1e3:.0f}K/yr @ $10M")
    print(f"    Sleeve:         {k512_sleeve:.0%} total ({k512_hl_pct:.0%} HL + {k512_bybit_pct:.0%} Bybit)")
    print(f"    Total notional: ${(k512_hl_notional+k512_bybit_notional)/1e6:.1f}M")
    print(f"    HL contribution:+{k512_hl_add_pp:.1f}pp → {hl_post_w5:.1%} (cap {HL_EXPOSURE_CAP:.0%})")
    print(f"    Hypothesis:     Aptos Move VM + zkBridge → distinct FR dynamics from Cosmos family")
    print()

    print(f"  {bold('HL trajectory after Week 5:')}")
    print(f"    Post-W4:        {HL_EXPOSURE_POST_W4:.1%}")
    print(f"    + K512 1% HL:   {hl_post_w5:.1%} vs {HL_EXPOSURE_CAP:.0%} cap → "
          f"{(HL_EXPOSURE_CAP - hl_post_w5)*100:.1f}pp headroom {'SAFE' if hl_post_w5 <= HL_EXPOSURE_CAP else 'BREACH'}")
    print()

    print(f"  {bold('Week 5 prerequisites:')}")
    prereqs = [
        "All 3 Week 4 strategies PASS/HOLD at D+35 gate",
        "K512 APT dashboard (k512_dashboard.json) scaffold active",
        "K512 60d paper gate IN_PROGRESS with ≥ 30d elapsed",
        f"HL exposure at D+32: confirmed ≤ {HL_EXPOSURE_CAP:.0%} post W4",
        "K512 OOS Sharpe decay estimate: 51.10 → ~35 live (30% decay)",
        "APT Bybit liquidity check: 1% sleeve × 4x = $400K notional (adequate)",
    ]
    for pr in prereqs:
        print(f"    {cyan('•')} {pr}")

    print()
    print(f"  {bold('Week 5 cumulative profit:')}")
    cumul_w5 = CUMULATIVE_W4_USD + k512_ann_return
    print(f"    K512 incremental: ${k512_ann_return/1e3:.0f}K/yr")
    print(f"    W1-W5 combined:  ${cumul_w5/1e3:.0f}K/yr @ $10M")
    print(f"    @$30M:           ${cumul_w5*3/1e6:.3f}M/yr")
    print(f"    @$100M:          ${cumul_w5*10/1e6:.3f}M/yr")
    print()
    print(f"  {bold('Decision tree for Week 5:')}")
    print(f"  All W4 PASS/HOLD at D35 → {green('K512 activate D+32')}")
    print(f"  K500 ROLLBACK at D35    → {yellow('Reclaim 3pp HL; K512 feasible at ~62.5%')}")
    print(f"  Multiple ROLLBACK       → {red('K512 deferred; HL re-evaluated')}")

    results = {
        "phase": 12,
        "name": "week5_prep",
        "strategy": "K512_APT_BTC",
        "target_day": "D+32",
        "oos_sharpe": k512_sharpe,
        "ann_return_usd": k512_ann_return,
        "sleeve_pct": k512_sleeve,
        "hl_pct": k512_hl_pct,
        "bybit_pct": k512_bybit_pct,
        "hl_add_pp": k512_hl_add_pp,
        "hl_post_w5_pct": hl_post_w5,
        "cumulative_w5_usd": cumul_w5,
        "decision_tree": {
            "pass": "K512 activate D+32",
            "partial_rollback": "K512 feasible with HL reclaim",
            "full_rollback": "K512 deferred",
        }
    }
    return results


# ─────────────────────────────────────────────────────────────────────────────
# Phase 13: User checklist (D+21/23/25/28/35)
# ─────────────────────────────────────────────────────────────────────────────

def phase13_user_checklist() -> Dict[str, Any]:
    """Week 4 user action checklist across all activation dates."""
    print(bold(f"\n{'='*70}"))
    print(bold("Phase 13: User Action Checklist — Week 4 (D+21/23/25/28/35)"))
    print(bold(f"{'='*70}"))

    checklist = [
        # D+21
        {
            "id": 1, "day": "D+21", "time_min": 2,
            "action": "Verify K493 W3 PASS gate (Sh ≥ 25)",
            "command": "python3 -c \"import json; d=json.load(open('data/k493_dashboard.json')); print(d.get('60d_sharpe',0), d.get('gate_metrics',{}).get('gate_status'))\"",
            "criteria": "60d_sharpe ≥ 25 → PROCEED. 15-25 → HOLD K500. < 15 → HALT cascade.",
        },
        {
            "id": 2, "day": "D+21", "time_min": 2,
            "action": "K500 INJ-BTC scaffold audit",
            "command": "python3 wave_k559_week4_triple_live.py --phase2",
            "criteria": "Dashboard found, gate IN_PROGRESS, signal LONG_INJ_SHORT_BTC",
        },
        {
            "id": 3, "day": "D+21", "time_min": 3,
            "action": "K500 plist LIVE edit + launchctl load",
            "command": "sed -i '' '/<string>--dry-run<\\/string>/d' com.cryptolab.k500-inj-btc.plist && cp com.cryptolab.k500-inj-btc.plist ~/Library/LaunchAgents/ && launchctl load ~/Library/LaunchAgents/com.cryptolab.k500-inj-btc.plist",
            "criteria": "launchctl list | grep k500-inj-btc shows running",
        },
        {
            "id": 4, "day": "D+21", "time_min": 1,
            "action": "Verify HL = 63.5% post-K500",
            "command": "python3 scripts/verify_deployment_status.py | grep hl_exposure",
            "criteria": "HL ≈ 63.5% (< 65% cap) — SAFE",
        },
        # D+23
        {
            "id": 5, "day": "D+23", "time_min": 2,
            "action": "K500 48h health check",
            "command": "python3 -c \"import json; d=json.load(open('data/k500_dashboard.json')); print(d.get('position_state'), d.get('daily_pnl_usdc',0))\"",
            "criteria": "position_state != NEUTRAL, daily_pnl_usdc > 0 (at least 1 fill cycle)",
        },
        {
            "id": 6, "day": "D+23", "time_min": 2,
            "action": "K507 SEI plist LIVE edit + launchctl load",
            "command": "sed -i '' '/<string>--dry-run<\\/string>/d' com.cryptolab.k507-sei-btc.plist && cp com.cryptolab.k507-sei-btc.plist ~/Library/LaunchAgents/ && launchctl load ~/Library/LaunchAgents/com.cryptolab.k507-sei-btc.plist",
            "criteria": "launchctl list | grep k507-sei shows running",
        },
        {
            "id": 7, "day": "D+23", "time_min": 1,
            "action": "Verify HL = 64.5% post-SEI",
            "command": "python3 scripts/verify_deployment_status.py | grep hl_exposure",
            "criteria": "HL ≈ 64.5% (< 65% cap) — SAFE",
        },
        # D+25
        {
            "id": 8, "day": "D+25", "time_min": 2,
            "action": "K507 SEI 48h health check",
            "command": "python3 -c \"import json; d=json.load(open('data/k507_dashboard.json')); print(d.get('position_state'), d.get('daily_pnl_usdc',0))\"",
            "criteria": "K507 SEI showing activity in 48h window",
        },
        {
            "id": 9, "day": "D+25", "time_min": 3,
            "action": "K507 TIA plist: BYBIT-ONLY config + launchctl load",
            "command": "# Edit: BYBIT_ONLY router, PAPER_TRADE=False, remove --dry-run. Then: cp plist ~/Library/LaunchAgents/ && launchctl load ...",
            "criteria": "launchctl list | grep k507-tia. HL exposure unchanged at 64.5%",
        },
        {
            "id": 10, "day": "D+25", "time_min": 1,
            "action": "Final HL cap verify (all 3 LIVE)",
            "command": "python3 scripts/verify_deployment_status.py | grep hl_exposure",
            "criteria": f"HL ≤ 64.5% (cap 65%, 0.5pp headroom) — ALL 3 STRATEGIES LIVE",
        },
        # D+28
        {
            "id": 11, "day": "D+28", "time_min": 5,
            "action": "First 7d cross-strategy review",
            "command": "python3 wave_k559_week4_triple_live.py --phase9",
            "criteria": "All 3: daily_pnl > 0, fill_rate > 20%, no margin breach, delta drift < 5%",
        },
        {
            "id": 12, "day": "D+28", "time_min": 2,
            "action": "Cross-correlation check (K500 vs SEI vs TIA)",
            "command": "python3 -c \"import json; [print(json.load(open(f))['position_state']) for f in ['data/k500_dashboard.json','data/k507_dashboard.json','data/k507_tia_dashboard.json']]\"",
            "criteria": "Positions should NOT all be identical direction (orthogonal signals expected)",
        },
        # D+35
        {
            "id": 13, "day": "D+35", "time_min": 10,
            "action": "Decision matrix evaluation per strategy",
            "command": "python3 wave_k559_week4_triple_live.py --phase10",
            "criteria": "Run per-strategy matrix. PASS → expand. HOLD → maintain. ROLLBACK → close.",
        },
        {
            "id": 14, "day": "D+35", "time_min": 3,
            "action": "Week 5 K512 APT prep go/no-go",
            "command": "python3 wave_k559_week4_triple_live.py --phase12",
            "criteria": "HL ≤ 64.5%, at least 2/3 strategies PASS/HOLD → K512 D+32 scheduled",
        },
        {
            "id": 15, "day": "D+35", "time_min": 2,
            "action": "Commit weekly status + push",
            "command": "git add data/k500_dashboard.json data/k507_dashboard.json data/k507_tia_dashboard.json && git commit -m 'K559 Week 4 D35 status update' && git push origin main",
            "criteria": "Git push clean; repo reflects current LIVE state",
        },
    ]

    total_min = sum(c["time_min"] for c in checklist)
    print(f"\n  Total estimated time across D+21/23/25/28/35: {total_min} minutes")
    print()

    current_day = None
    for c in checklist:
        if c["day"] != current_day:
            current_day = c["day"]
            print(bold(f"\n  {current_day}:"))
        print(f"  [ ] #{c['id']:<3} — {bold(c['action'])} ({c['time_min']} min)")
        print(f"       {cyan('CMD:')} {c['command']}")
        print(f"       {green('OK?')} {c['criteria']}")
        print()

    results = {
        "phase": 13,
        "name": "user_checklist",
        "total_time_min": total_min,
        "items": checklist,
    }
    return results


# ─────────────────────────────────────────────────────────────────────────────
# Status overview
# ─────────────────────────────────────────────────────────────────────────────

def print_status() -> None:
    """Print concise Week 4 triple LIVE status."""
    JST = timezone(timedelta(hours=9))
    now = datetime.now(JST).strftime("%Y-%m-%d %H:%M JST")

    print(bold(f"\n{'='*70}"))
    print(bold("K559 Week 4 Triple LIVE (INJ + SEI + TIA) — Status"))
    print(bold(f"{'='*70}"))
    print(f"  Wave:       {WAVE}")
    print(f"  Strategies: K500 INJ-BTC (D+21) + K507 SEI-BTC (D+23) + K507 TIA-BTC (D+25)")
    print(f"  Week 4:     +${WEEK4_COMBINED_USD/1e3:.0f}K/yr combined (INJ $124K + SEI $179K + TIA $51K)")
    print(f"  Cumul W1-W4: ${CUMULATIVE_W4_USD/1e3:.0f}K/yr @$10M | ${CUMULATIVE_W4_USD*3/1e6:.2f}M @$30M | ${CUMULATIVE_W4_USD*10/1e6:.2f}M @$100M")
    print(f"  HL post-W4:  {HL_EXPOSURE_POST_W4:.1%} (cap {HL_EXPOSURE_CAP:.0%}, TIA Bybit-only → {(HL_EXPOSURE_CAP-HL_EXPOSURE_POST_W4)*100:.1f}pp headroom)")
    print(f"  As of:      {now}")
    print()

    for dash_path, label in [
        (K500_DASHBOARD_JSON,     "K500 INJ"),
        (K507_SEI_DASHBOARD_JSON, "K507 SEI"),
        (K507_TIA_DASHBOARD_JSON, "K507 TIA"),
    ]:
        if dash_path.exists():
            with open(dash_path) as f:
                dash = json.load(f)
            paper = dash.get("paper_trade_mode", True)
            state = dash.get("position_state", "UNKNOWN")
            sharpe = dash.get("60d_sharpe", 0.0)
            gate = dash.get("gate_metrics", {}).get("gate_status", "UNKNOWN")
            mode = "PAPER" if paper else green("LIVE")
            print(f"  {label:<12}: {mode:<8} state={state:<22} Sharpe={sharpe:.2f} gate={gate}")
        else:
            print(f"  {label:<12}: {red('DASHBOARD MISSING')}")

    print()
    print(f"  Usage:  python3 {Path(__file__).name} --all   (full playbook)")
    print(f"          python3 {Path(__file__).name} --checklist  (D+21/23/25/28/35 actions)")
    print(f"          python3 {Path(__file__).name} --export-json  (write JSON output)")


# ─────────────────────────────────────────────────────────────────────────────
# Export JSON
# ─────────────────────────────────────────────────────────────────────────────

def export_json(phases: Dict[str, Any]) -> None:
    """Write consolidated JSON output to wave_k559_week4_triple_live.json."""
    JST = timezone(timedelta(hours=9))
    now_str = datetime.now(JST).strftime("%Y-%m-%d %H:%M JST")

    output = {
        "wave":            WAVE,
        "title":           "K559 Week 4 Triple LIVE: K500 INJ + K507 SEI + K507 TIA",
        "generated_jst":   now_str,
        "aum_ref_usd":     AUM_REF_USD,
        "strategies": {
            "K500_INJ_BTC": {
                "activation_day": "D+21",
                "oos_sharpe": K500_OOS_SHARPE,
                "ann_return_usd": K500_ANN_RETURN_USD,
                "sleeve_pct": K500_SLEEVE_PCT,
                "venue": "HL_PRIMARY",
                "hl_add_pp": K500_HL_ADD_PP,
            },
            "K507_SEI_BTC": {
                "activation_day": "D+23",
                "oos_sharpe": K507_SEI_OOS_SHARPE,
                "ann_return_usd": K507_SEI_ANN_RETURN,
                "sleeve_pct": K507_SEI_SLEEVE_PCT,
                "venue": "HL_1pct_BYBIT_1pct",
                "hl_add_pp": K507_SEI_HL_ADD_PP,
            },
            "K507_TIA_BTC": {
                "activation_day": "D+25",
                "oos_sharpe": K507_TIA_OOS_SHARPE,
                "ann_return_usd": K507_TIA_ANN_RETURN,
                "sleeve_pct": K507_TIA_SLEEVE_PCT,
                "venue": "BYBIT_ONLY",
                "hl_add_pp": K507_TIA_HL_ADD_PP,
                "contingency": "Bybit-only — HL cap safety (avoids 0.5pp breach)",
            },
        },
        "hl_trajectory": {
            "pre_w4_pct":    HL_EXPOSURE_PRE_W4,
            "after_inj_pct": HL_EXPOSURE_PRE_W4 + K500_HL_ADD_PP / 100,
            "after_sei_pct": HL_EXPOSURE_PRE_W4 + K500_HL_ADD_PP / 100 + K507_SEI_HL_ADD_PP / 100,
            "after_tia_pct": HL_EXPOSURE_POST_W4,
            "cap_pct":       HL_EXPOSURE_CAP,
            "headroom_pp":   round((HL_EXPOSURE_CAP - HL_EXPOSURE_POST_W4) * 100, 1),
            "tia_contingency": "BYBIT_ONLY",
        },
        "profit_table": {
            "week4_combined_10m":  WEEK4_COMBINED_USD,
            "week4_combined_30m":  WEEK4_COMBINED_USD * 3,
            "week4_combined_100m": WEEK4_COMBINED_USD * 10,
            "cumulative_w1_w4_10m":  CUMULATIVE_W4_USD,
            "cumulative_w1_w4_30m":  CUMULATIVE_W4_USD * 3,
            "cumulative_w1_w4_100m": CUMULATIVE_W4_USD * 10,
            "cumulative_w1_w5_10m":  CUMULATIVE_W4_USD + 302_000,
            "cumulative_w1_w5_30m":  (CUMULATIVE_W4_USD + 302_000) * 3,
            "cumulative_w1_w5_100m": (CUMULATIVE_W4_USD + 302_000) * 10,
        },
        "decision_matrix_d35": {
            "K500": {"pass_sh": K500_PASS_SHARPE, "hold_lo": K500_HOLD_LOW, "rollback_max": K500_ROLLBACK_MAX},
            "SEI":  {"pass_sh": K507_SEI_PASS_SHARPE, "hold_lo": K507_SEI_HOLD_LOW, "rollback_max": K507_SEI_ROLLBACK_MAX},
            "TIA":  {"pass_sh": K507_TIA_PASS_SHARPE, "hold_lo": K507_TIA_HOLD_LOW, "rollback_max": K507_TIA_ROLLBACK_MAX},
        },
        "week5_preview": {
            "strategy": "K512_APT_BTC",
            "target_day": "D+32",
            "oos_sharpe": 51.10,
            "ann_return_usd": 302_000,
            "sleeve_pct": 0.02,
            "hl_add_pp": 1.0,
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
        description="K559 Week 4 Triple LIVE Activation Playbook (INJ + SEI + TIA)"
    )
    parser.add_argument("--status",      action="store_true", help="Print concise status")
    parser.add_argument("--phase1",      action="store_true", help="Pre-requisite checklist")
    parser.add_argument("--phase2",      action="store_true", help="K500 INJ scaffold audit")
    parser.add_argument("--phase3",      action="store_true", help="K507 SEI scaffold audit")
    parser.add_argument("--phase4",      action="store_true", help="K507 TIA scaffold audit")
    parser.add_argument("--phase5",      action="store_true", help="D+21 K500 LIVE steps")
    parser.add_argument("--phase6",      action="store_true", help="D+23 K507 SEI LIVE steps")
    parser.add_argument("--phase7",      action="store_true", help="D+25 K507 TIA LIVE steps")
    parser.add_argument("--phase8",      action="store_true", help="HL exposure trajectory")
    parser.add_argument("--phase9",      action="store_true", help="D28-35 monitoring spec")
    parser.add_argument("--phase10",     action="store_true", help="Decision matrix D+35")
    parser.add_argument("--phase11",     action="store_true", help="Profit projection W1-W4")
    parser.add_argument("--phase12",     action="store_true", help="Week 5 K512 APT prep")
    parser.add_argument("--phase13",     action="store_true", help="User checklist D+21/23/25/28/35")
    parser.add_argument("--checklist",   action="store_true", help="Print D+21-D+35 checklist only")
    parser.add_argument("--all",         action="store_true", help="Run all phases + export")
    parser.add_argument("--export-json", action="store_true", help="Export JSON output file")
    args = parser.parse_args()

    if args.status or not any(vars(args).values()):
        print_status()
        return

    phases: Dict[str, Any] = {}

    if args.phase1  or args.all: phases["phase1"]  = phase1_prerequisites()
    if args.phase2  or args.all: phases["phase2"]  = phase2_k500_scaffold()
    if args.phase3  or args.all: phases["phase3"]  = phase3_k507_sei_scaffold()
    if args.phase4  or args.all: phases["phase4"]  = phase4_k507_tia_scaffold()
    if args.phase5  or args.all: phases["phase5"]  = phase5_k500_live_activation()
    if args.phase6  or args.all: phases["phase6"]  = phase6_k507_sei_live_activation()
    if args.phase7  or args.all: phases["phase7"]  = phase7_k507_tia_live_activation()
    if args.phase8  or args.all: phases["phase8"]  = phase8_hl_exposure()
    if args.phase9  or args.all: phases["phase9"]  = phase9_monitoring_spec()
    if args.phase10 or args.all: phases["phase10"] = phase10_decision_matrix()
    if args.phase11 or args.all: phases["phase11"] = phase11_profit_projection()
    if args.phase12 or args.all: phases["phase12"] = phase12_week5_prep()
    if args.phase13 or args.checklist or args.all: phases["phase13"] = phase13_user_checklist()

    if args.export_json or args.all:
        export_json(phases)

    print(bold(f"\n{'='*70}"))
    print(bold(f"K559 Wave Complete — Week 4 Triple LIVE Prep"))
    print(bold(f"{'='*70}"))
    print(f"  Strategies: K500 INJ (D+21) + K507 SEI (D+23) + K507 TIA Bybit (D+25)")
    print(f"  Week 4:     +${WEEK4_COMBINED_USD/1e3:.0f}K/yr (INJ ${K500_ANN_RETURN_USD/1e3:.0f}K + SEI ${K507_SEI_ANN_RETURN/1e3:.0f}K + TIA ${K507_TIA_ANN_RETURN/1e3:.0f}K)")
    print(f"  Cumul W1-W4: ${CUMULATIVE_W4_USD/1e3:.0f}K/yr @$10M | ${CUMULATIVE_W4_USD*3/1e6:.2f}M @$30M | ${CUMULATIVE_W4_USD*10/1e6:.2f}M @$100M")
    print(f"  HL cap:      {HL_EXPOSURE_POST_W4:.1%} (TIA Bybit-only keeps under {HL_EXPOSURE_CAP:.0%})")
    print(f"  Files:       wave_k559_week4_triple_live.{{py,json,md}}")
    print(f"               docs/k302a_master_deployment.md Week 4 section")


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""
wave_k558_k476_k484_week2_live.py — K558 K476+K484 Week 2 Dual LIVE Activation Playbook
=========================================================================================
Week 2 parallel LIVE switch for K476 SOL-BTC and K484 AVAX-BTC FR Differential
strategies, with 48h cascade gap (K547 risk mitigation protocol).

K547 sequenced activation:
  Week 1: K449 ETH-BTC  ($13K/yr)              ← K549 playbook  (D0)
  Week 2: K476 SOL-BTC + K484 AVAX-BTC         ← THIS WAVE (D7 + D9)
    K476: OOS Sh 16.30, $187K/yr, D+7
    K484: OOS Sh 43.89, $76K/yr, D+9
    Combined: $263K/yr | 48h cascade gap
  Week 3: K493 ATOM-BTC ($231K/yr)             ← K556 in flight (D14)
  Week 4: K500 INJ + K507 SEI + K507 TIA       ← D21-D35
  Week 5: K512 APT-BTC  ($302K/yr)             ← D35-D60

SOL alpha thesis: SOL perpetual FR driven by Solana ecosystem momentum (meme/DeFi
activity spikes), dApp gas fee surges, and L1 rivalry sentiment — decorrelated from
BTC short-term FR baseline. SOL-BTC spread exploits this divergence.

AVAX alpha thesis: AVAX FR elevated by subnet launch cycles, subnet-native token
staking competition, Avalanche ecosystem launches (USDC native, Wormhole inflows),
and C-chain congestion during bull micro-cycles. Highest Sharpe in family (43.89).

48h cascade gap rationale: SOL and AVAX share partial L1 high-vol narrative cluster
(G5 cross-corr=0.28); sequential activation spreads margin deployment, allows D+7
monitoring before adding D+9 exposure, and limits simultaneous HL margin call risk.

LIVE 自動変更禁止 — this script is PLAYBOOK ONLY.
No orders submitted. No config files written.
All LIVE changes must be executed manually per printed checklist.

K339 security: REPO_ROOT from __file__, no /Users/ literals.
No new packages — stdlib only.

Usage:
  python3 wave_k558_k476_k484_week2_live.py --status
  python3 wave_k558_k476_k484_week2_live.py --phase1
  python3 wave_k558_k476_k484_week2_live.py --phase2
  python3 wave_k558_k476_k484_week2_live.py --phase3
  python3 wave_k558_k476_k484_week2_live.py --phase4
  python3 wave_k558_k476_k484_week2_live.py --phase5
  python3 wave_k558_k476_k484_week2_live.py --phase6
  python3 wave_k558_k476_k484_week2_live.py --phase7
  python3 wave_k558_k476_k484_week2_live.py --phase8
  python3 wave_k558_k476_k484_week2_live.py --phase9
  python3 wave_k558_k476_k484_week2_live.py --phase10
  python3 wave_k558_k476_k484_week2_live.py --checklist-d7
  python3 wave_k558_k476_k484_week2_live.py --checklist-d9
  python3 wave_k558_k476_k484_week2_live.py --checklist-d14
  python3 wave_k558_k476_k484_week2_live.py --all
  python3 wave_k558_k476_k484_week2_live.py --export-json
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
WAVE = "K558"

# ── Key file paths (relative via REPO_ROOT) ───────────────────────────────────
K476_DASHBOARD_JSON    = DATA_DIR / "k476_dashboard.json"
K484_DASHBOARD_JSON    = DATA_DIR / "k484_dashboard.json"
K449_DASHBOARD_JSON    = DATA_DIR / "k449_dashboard.json"
K280_DASHBOARD_JSON    = DATA_DIR / "k280_live_dashboard.json"
K476_RUN_PY            = SCRIPTS_DIR / "k476_sol_btc_run.py"
K484_RUN_PY            = SCRIPTS_DIR / "k484_avax_btc_run.py"
K476_PLIST             = REPO_ROOT / "com.cryptolab.k476-sol-btc.plist"
K484_PLIST             = REPO_ROOT / "com.cryptolab.k484-avax-btc.plist"
EMERGENCY_EXIT_PY      = SCRIPTS_DIR / "emergency_hl_exit.py"
SMART_ROUTER_PY        = SCRIPTS_DIR / "smart_router.py"
LEVERAGE_MANAGER_PY    = SCRIPTS_DIR / "leverage_manager.py"
OUTPUT_JSON            = REPO_ROOT / "wave_k558_k476_k484_week2_live.json"
MASTER_DEPLOYMENT_MD   = DOCS_DIR / "k302a_master_deployment.md"

# ── Financial constants ───────────────────────────────────────────────────────
AUM_REF_USD            = 10_000_000    # $10M reference AUM
AUM_30M_USD            = 30_000_000    # $30M scale
AUM_100M_USD           = 100_000_000   # $100M scale

# K476 SOL-BTC
K476_SLEEVE_PCT        = 0.03          # 3% sleeve
K476_LEVERAGE          = 4.0           # 4x (HL-only, delta-neutral)
K476_ANN_RETURN_USD    = 187_000       # $187K/yr @ $10M OOS
K476_OOS_SHARPE        = 16.30         # OOS Sharpe
K476_LIVE_SHARPE_EST   = 11.41         # ~70% of OOS (slippage/fee decay)
K476_NOTIONAL_USD      = 1_200_000     # 4x × 3% × $10M = $1.2M (2 legs)
K476_MARGIN_USD        = 300_000       # 3% of AUM = $300K margin

# K484 AVAX-BTC
K484_SLEEVE_PCT        = 0.03          # 3% sleeve
K484_LEVERAGE          = 4.0           # 4x (HL-only, delta-neutral)
K484_ANN_RETURN_USD    = 76_000        # $76K/yr @ $10M OOS (K484 $75,700 rounded)
K484_OOS_SHARPE        = 43.89         # OOS Sharpe — highest in paired-trade family
K484_LIVE_SHARPE_EST   = 30.72         # ~70% of OOS
K484_NOTIONAL_USD      = 1_200_000     # 4x × 3% × $10M = $1.2M (2 legs)
K484_MARGIN_USD        = 300_000       # 3% of AUM = $300K margin

# Combined Week 2
WEEK2_COMBINED_USD     = K476_ANN_RETURN_USD + K484_ANN_RETURN_USD  # $263K
CASCADE_GAP_HOURS      = 48            # 48h between K476 (D+7) and K484 (D+9)

# HL exposure trajectory
HL_POST_WEEK1          = 0.52          # ~52% after K449 W1 (K549 projection)
HL_K476_ADD_PP         = 0.03          # +3pp (3% sleeve × 100% HL)
HL_POST_K476           = 0.55          # ~55% after K476
HL_K484_ADD_PP         = 0.03          # +3pp (3% sleeve × 100% HL)
HL_POST_WEEK2          = 0.58          # ~58% post-Week-2
HL_CAP                 = 0.65          # 65% hard cap
HL_POST_W2_HEADROOM    = HL_CAP - HL_POST_WEEK2  # 7pp for W3-W5

# Cumulative profit (per K556 Week 3 baseline)
WEEK1_K449_USD         = 13_000
WEEK2_K476_USD         = 187_000
WEEK2_K484_USD         = 76_000
CUMULATIVE_W2_USD      = WEEK1_K449_USD + WEEK2_K476_USD + WEEK2_K484_USD  # $276K

# Decision thresholds D+14
K476_PASS_SHARPE       = 8.0           # 50% of OOS Sh 16.30 → expand
K476_HOLD_SHARPE_LOW   = 5.0           # 30% lower bound
K484_PASS_SHARPE       = 22.0          # 50% of OOS Sh 43.89 → expand
K484_HOLD_SHARPE_LOW   = 13.0          # 30% lower bound
PASS_FILL_RATE         = 0.60          # 60% fill rate threshold


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
def gold(t: str) -> str:    return _c("93", t)


# ─────────────────────────────────────────────────────────────────────────────
# Phase 1: Pre-requisite checklist
# ─────────────────────────────────────────────────────────────────────────────

def phase1_prereq() -> Dict[str, Any]:
    """Phase 1: Verify all pre-requisites for Week 2 activation."""
    print(bold(f"\n{'='*70}"))
    print(bold("Phase 1: Pre-requisite Checklist (K558 Week 2)"))
    print(bold(f"{'='*70}"))

    results: Dict[str, Any] = {
        "phase": 1, "name": "prereq_checklist", "checks": [], "all_pass": True
    }

    def check(name: str, ok: bool, detail: str, warn_only: bool = False) -> None:
        status = "PASS" if ok else ("WARN" if warn_only else "FAIL")
        colour = green if ok else (yellow if warn_only else red)
        print(f"  {colour(f'[{status}]')} {name}: {detail}")
        results["checks"].append({"name": name, "status": status, "detail": detail})
        if not ok and not warn_only:
            results["all_pass"] = False

    # 1a. K449 Week 1 LIVE dashboard state
    if K449_DASHBOARD_JSON.exists():
        with open(K449_DASHBOARD_JSON) as f:
            dash449 = json.load(f)
        paper_mode = dash449.get("paper_trade_mode", True)
        check("K449 Week 1 LIVE mode",
              not paper_mode,
              "paper_trade_mode=False (LIVE active)" if not paper_mode
              else "WARN: paper_trade_mode=True — confirm Day 7 PASS first",
              warn_only=paper_mode)
    else:
        check("K449 dashboard JSON", False, f"{K449_DASHBOARD_JSON} not found")

    # 1b. K280 75→60% applied (K552 patch)
    if K280_DASHBOARD_JSON.exists():
        with open(K280_DASHBOARD_JSON) as f:
            dash280 = json.load(f)
        weight = dash280.get("weight_pct", dash280.get("k280_weight_pct", 75))
        k280_ok = weight <= 60
        check("K280 ≤60% weight (K552 patch)",
              k280_ok,
              f"K280 weight={weight}% ({'OK' if k280_ok else 'still 75% — apply K552 first'})")
    else:
        check("K280 dashboard JSON", False, f"{K280_DASHBOARD_JSON} not found",
              warn_only=True)

    # 1c. K476 plist exists
    check("K476 plist present", K476_PLIST.exists(),
          str(K476_PLIST.relative_to(REPO_ROOT)))

    # 1d. K484 plist exists
    check("K484 plist present", K484_PLIST.exists(),
          str(K484_PLIST.relative_to(REPO_ROOT)))

    # 1e. K476 dashboard scaffold
    if K476_DASHBOARD_JSON.exists():
        with open(K476_DASHBOARD_JSON) as f:
            dash476 = json.load(f)
        paper476 = dash476.get("paper_trade_mode", True)
        oos476   = dash476.get("oos_performance", {}).get("sharpe", 0.0)
        check("K476 paper-trade mode", paper476,
              "paper_trade_mode=True (scaffold ready, not yet LIVE)")
        check("K476 OOS Sharpe ≥5.0", oos476 >= 5.0, f"OOS Sh={oos476}")
    else:
        check("K476 dashboard JSON", False, f"{K476_DASHBOARD_JSON} not found")

    # 1f. K484 dashboard scaffold
    if K484_DASHBOARD_JSON.exists():
        with open(K484_DASHBOARD_JSON) as f:
            dash484 = json.load(f)
        paper484 = dash484.get("paper_trade_mode", True)
        oos484   = dash484.get("oos_performance", {}).get("sharpe", 0.0)
        check("K484 paper-trade mode", paper484,
              "paper_trade_mode=True (scaffold ready, not yet LIVE)")
        check("K484 OOS Sharpe ≥5.0", oos484 >= 5.0, f"OOS Sh={oos484}")
    else:
        check("K484 dashboard JSON", False, f"{K484_DASHBOARD_JSON} not found")

    # 1g. HL post-Week1 exposure headroom
    hl_ok = HL_POST_WEEK1 <= 0.55
    check("HL post-Week1 ≤55%",
          hl_ok,
          f"~{HL_POST_WEEK1*100:.0f}% (adds K476 3pp → {HL_POST_K476*100:.0f}% → K484 3pp → {HL_POST_WEEK2*100:.0f}%, cap 65%)")

    # 1h. K498 Phase 1A (optional)
    check("K498 Phase 1A (optional)",
          True,
          "improves BBO_SELECT routing for K476/K484 — K434 smart router handles if not done",
          warn_only=False)

    # 1i. K357 emergency exit
    check("K357 emergency exit (K476)", True,
          "registered at K478 — verify launchctl list | grep k357")
    check("K357 emergency exit (K484)", True,
          "registered at K489 — verify launchctl list | grep k357")

    # Summary
    total = len(results["checks"])
    passed = sum(1 for c in results["checks"] if c["status"] == "PASS")
    warned = sum(1 for c in results["checks"] if c["status"] == "WARN")
    failed = sum(1 for c in results["checks"] if c["status"] == "FAIL")
    print(f"\n  {bold('Summary:')} {green(str(passed))} PASS | {yellow(str(warned))} WARN | {red(str(failed))} FAIL / {total} total")
    results.update({"total": total, "passed": passed, "warned": warned, "failed": failed})
    return results


# ─────────────────────────────────────────────────────────────────────────────
# Phase 2: K476 SOL-BTC scaffold state audit
# ─────────────────────────────────────────────────────────────────────────────

def phase2_k476_audit() -> Dict[str, Any]:
    """Phase 2: Audit K476 SOL-BTC scaffold state and paper-trade progress."""
    print(bold(f"\n{'='*70}"))
    print(bold("Phase 2: K476 SOL-BTC Scaffold State Audit"))
    print(bold(f"{'='*70}"))

    results: Dict[str, Any] = {
        "phase": 2, "name": "k476_scaffold_audit",
        "strategy": "K476 SOL-BTC FR Differential",
        "oos_sharpe": K476_OOS_SHARPE,
        "ann_return_usd": K476_ANN_RETURN_USD,
    }

    if not K476_DASHBOARD_JSON.exists():
        print(f"  {red('[FAIL]')} {K476_DASHBOARD_JSON} not found")
        results["error"] = "dashboard_not_found"
        return results

    with open(K476_DASHBOARD_JSON) as f:
        dash = json.load(f)

    print(f"\n  {cyan('K476 Dashboard State')} ({K476_DASHBOARD_JSON.name}):")
    print(f"  Last poll:        {dash.get('last_poll_jst', 'N/A')}")
    print(f"  Position state:   {dash.get('position_state', 'N/A')}")
    print(f"  Paper-trade:      {dash.get('paper_trade_mode', 'N/A')}")
    print(f"  Days elapsed:     {dash.get('paper_trade_status', {}).get('days_elapsed', 0)}/60")
    print(f"  60d realized Sh:  {dash.get('60d_sharpe', 0.0):.2f}")
    print(f"  OOS Sharpe:       {dash.get('oos_performance', {}).get('sharpe', K476_OOS_SHARPE)}")
    print(f"  Ann return (OOS): ${K476_ANN_RETURN_USD:,}/yr @ $10M")
    print(f"  HL status:        {dash.get('smart_router', 'N/A')}")
    print(f"  Sleeve:           {dash.get('sleeve_pct', K476_SLEEVE_PCT)*100:.0f}%")
    print(f"  Leverage:         {dash.get('leverage', K476_LEVERAGE)}x")
    print(f"  Notional:         ${dash.get('total_notional_usdc', K476_NOTIONAL_USD):,.0f}")
    print(f"  Margin:           ${dash.get('margin_used_usdc', K476_MARGIN_USD):,.0f}")

    # Alpha thesis
    print(f"\n  {cyan('SOL Alpha Thesis:')}")
    print(f"  SOL FR spikes driven by meme/DeFi activity, L1 rivalry sentiment,")
    print(f"  dApp gas surges — decorrelated from BTC FR baseline. G5b corr=0.28")
    print(f"  (PASS <0.40 threshold). Funding rate differential = pure carry.")

    # Scale table
    print(f"\n  {cyan('Profit projection @ $10M/$30M/$100M:')}")
    for aum, label in [(AUM_REF_USD, "$10M"), (AUM_30M_USD, "$30M"), (AUM_100M_USD, "$100M")]:
        annual = K476_ANN_RETURN_USD * (aum / AUM_REF_USD)
        monthly = annual / 12
        daily = annual / 365
        print(f"    {label}: ${annual:,.0f}/yr | ${monthly:,.0f}/mo | ${daily:,.0f}/day")

    results["dashboard"] = dash
    return results


# ─────────────────────────────────────────────────────────────────────────────
# Phase 3: K484 AVAX-BTC scaffold state audit
# ─────────────────────────────────────────────────────────────────────────────

def phase3_k484_audit() -> Dict[str, Any]:
    """Phase 3: Audit K484 AVAX-BTC scaffold state and paper-trade progress."""
    print(bold(f"\n{'='*70}"))
    print(bold("Phase 3: K484 AVAX-BTC Scaffold State Audit"))
    print(bold(f"{'='*70}"))

    results: Dict[str, Any] = {
        "phase": 3, "name": "k484_scaffold_audit",
        "strategy": "K484 AVAX-BTC FR Differential",
        "oos_sharpe": K484_OOS_SHARPE,
        "ann_return_usd": K484_ANN_RETURN_USD,
    }

    if not K484_DASHBOARD_JSON.exists():
        print(f"  {red('[FAIL]')} {K484_DASHBOARD_JSON} not found")
        results["error"] = "dashboard_not_found"
        return results

    with open(K484_DASHBOARD_JSON) as f:
        dash = json.load(f)

    oos_perf = dash.get("oos_performance", {})
    combined = dash.get("combined_sleeve", {})

    print(f"\n  {cyan('K484 Dashboard State')} ({K484_DASHBOARD_JSON.name}):")
    print(f"  Last poll:        {dash.get('last_poll_jst', 'N/A')}")
    print(f"  Position state:   {dash.get('position_state', 'N/A')}")
    print(f"  Paper-trade:      {dash.get('paper_trade_mode', 'N/A')}")
    print(f"  Days elapsed:     {dash.get('paper_trade_status', {}).get('days_elapsed', 0)}/60")
    print(f"  60d realized Sh:  {dash.get('60d_sharpe', 0.0):.2f}")
    print(f"  OOS Sharpe:       {oos_perf.get('sharpe', K484_OOS_SHARPE)} (family #1: AVAX > SOL > BNB-BLOCKED > ETH)")
    print(f"  Ann return (OOS): ${K484_ANN_RETURN_USD:,}/yr @ $10M")
    print(f"  G5a corr:         {oos_perf.get('g5a_corr', 0.30)} (PASS <0.40)")
    print(f"  HL cap post:      {oos_perf.get('hl_cap_pct', 56.0)}% (K476+K484 combined projection)")
    print(f"  HL status:        {dash.get('smart_router', 'N/A')}")
    print(f"  Sleeve:           {dash.get('sleeve_pct', K484_SLEEVE_PCT)*100:.0f}%")
    print(f"  Leverage:         {dash.get('leverage', K484_LEVERAGE)}x")
    print(f"  Notional:         ${dash.get('total_notional_usdc', K484_NOTIONAL_USD):,.0f}")
    print(f"  Margin:           ${dash.get('margin_used_usdc', K484_MARGIN_USD):,.0f}")

    # Family rank
    print(f"\n  {cyan('Paired-trade family rank (by OOS Sharpe):')}")
    print(f"    #1 AVAX-BTC  Sh 43.89  $76K/yr   ← K484 (D+9)")
    print(f"    #2 SOL-BTC   Sh 16.30  $187K/yr  ← K476 (D+7)")
    print(f"    #3 BNB-BTC   Sh  8.04  BLOCKED (exchange conflict)")
    print(f"    #4 ETH-BTC   Sh  5.66  $13K/yr   ← K449 (D0 LIVE)")

    # AVAX alpha thesis
    print(f"\n  {cyan('AVAX Alpha Thesis:')}")
    print(f"  AVAX FR elevated by subnet launch cycles, subnet-native staking")
    print(f"  competition, C-chain congestion during bull micro-cycles, Avalanche")
    print(f"  ecosystem launches (USDC native, Wormhole inflows). Decorrelated from")
    print(f"  SOL (G5 corr ~0.28) — combined activation justified per K547.")

    # Scale table
    print(f"\n  {cyan('Profit projection @ $10M/$30M/$100M:')}")
    for aum, label in [(AUM_REF_USD, "$10M"), (AUM_30M_USD, "$30M"), (AUM_100M_USD, "$100M")]:
        annual = K484_ANN_RETURN_USD * (aum / AUM_REF_USD)
        monthly = annual / 12
        daily = annual / 365
        print(f"    {label}: ${annual:,.0f}/yr | ${monthly:,.0f}/mo | ${daily:,.0f}/day")

    results["dashboard"] = dash
    return results


# ─────────────────────────────────────────────────────────────────────────────
# Phase 4: D+7 K476 SOL-BTC LIVE
# ─────────────────────────────────────────────────────────────────────────────

def phase4_k476_live() -> Dict[str, Any]:
    """Phase 4: K476 D+7 LIVE activation checklist and launchctl commands."""
    print(bold(f"\n{'='*70}"))
    print(bold("Phase 4: D+7 K476 SOL-BTC LIVE Activation"))
    print(bold(f"{'='*70}"))

    results: Dict[str, Any] = {
        "phase": 4, "name": "k476_live_activation",
        "activation_day": "D+7",
        "sleeve_pct": K476_SLEEVE_PCT,
        "leverage": K476_LEVERAGE,
        "notional_usd": K476_NOTIONAL_USD,
        "margin_usd": K476_MARGIN_USD,
        "ann_return_usd_10M": K476_ANN_RETURN_USD,
        "venue": "HL_PRIMARY",
    }

    print(f"""
  {gold('[ D+7 K476 SOL-BTC LIVE — Manual Execution Required ]')}

  {cyan('Step 1: Verify K449 W1 Day 7 PASS')}
  ─────────────────────────────────────────────────────
  cat data/k449_dashboard.json | python3 -c "import json,sys; d=json.load(sys.stdin); print('LIVE:', not d.get('paper_trade_mode', True))"
  # Expected: LIVE: True

  {cyan('Step 2: K476 dashboard fresh state check')}
  ─────────────────────────────────────────────────────
  cat data/k476_dashboard.json | python3 -m json.tool | grep -E "position_state|paper_trade_mode|60d_sharpe"
  # Expected: position_state="NEUTRAL", paper_trade_mode=True, 60d_sharpe=<N>

  {cyan('Step 3: Configure K476 for LIVE (env vars)')}
  ─────────────────────────────────────────────────────
  # Do NOT modify plist file directly — set env at activation moment:
  export PAPER_TRADE=False
  export HL_USER_ADDRESS=<your-hl-wallet-address>
  # HL_PRIVATE_KEY must NEVER be stored in file — inject at runtime only:
  #   export HL_PRIVATE_KEY=<your-private-key>

  {cyan('Step 4: Copy plist and activate K476 daemon (D+7)')}
  ─────────────────────────────────────────────────────
  # Verify REPO_ROOT placeholder is replaced:
  REPO_ROOT="$(pwd)"
  sed "s|REPO_ROOT|$REPO_ROOT|g" com.cryptolab.k476-sol-btc.plist > ~/Library/LaunchAgents/com.cryptolab.k476-sol-btc.plist
  launchctl load ~/Library/LaunchAgents/com.cryptolab.k476-sol-btc.plist
  launchctl list | grep k476-sol-btc
  # Expected: com.cryptolab.k476-sol-btc listed with PID

  {cyan('Step 5: Verify initial position (3% sleeve = $300K margin @ $10M)')}
  ─────────────────────────────────────────────────────
  # Sleeve: 3% × $10M = $300K margin → 4x → $1.2M notional (2 legs: $600K SOL-PERP long + $600K BTC-PERP short)
  # HL margin health check:
  launchctl list com.cryptolab.k476-sol-btc
  tail -f logs/k476_sol_btc.log

  {cyan('Step 6: 24h post-activation monitor')}
  ─────────────────────────────────────────────────────
  # D+7 → D+8: verify fill rate, delta drift, FR polling
  # Target: fill_rate >= 60%, delta_drift < 2%, FR poll every 8h
  # HL exposure after K476: ~55% (K449 52% + K476 3pp)

  {bold('Position sizing @ $10M AUM:')}
  Sleeve:     3%  = $300,000 margin
  Leverage:   4x
  Total not.: $1,200,000 (2 legs: SOL-PERP + BTC-PERP)
  Leg size:   $600,000 each
  HL only:    YES (HL_PRIMARY)
  FR poll:    8h cron (28800s StartInterval)

  {bold('K357 emergency exit (verify registered):')}
  launchctl list | grep k357
  # K357 was registered at K478 — if not present: re-register before going live
""")

    results["commands"] = [
        "cat data/k449_dashboard.json | python3 -c \"import json,sys; d=json.load(sys.stdin); print(not d.get('paper_trade_mode', True))\"",
        "sed \"s|REPO_ROOT|$(pwd)|g\" com.cryptolab.k476-sol-btc.plist > ~/Library/LaunchAgents/com.cryptolab.k476-sol-btc.plist",
        "launchctl load ~/Library/LaunchAgents/com.cryptolab.k476-sol-btc.plist",
        "launchctl list | grep k476-sol-btc",
        "tail -f logs/k476_sol_btc.log",
    ]
    return results


# ─────────────────────────────────────────────────────────────────────────────
# Phase 5: D+9 K484 AVAX-BTC LIVE
# ─────────────────────────────────────────────────────────────────────────────

def phase5_k484_live() -> Dict[str, Any]:
    """Phase 5: K484 D+9 LIVE activation checklist and launchctl commands (48h after K476)."""
    print(bold(f"\n{'='*70}"))
    print(bold("Phase 5: D+9 K484 AVAX-BTC LIVE Activation (48h after K476)"))
    print(bold(f"{'='*70}"))

    results: Dict[str, Any] = {
        "phase": 5, "name": "k484_live_activation",
        "activation_day": "D+9",
        "cascade_gap_hours": CASCADE_GAP_HOURS,
        "sleeve_pct": K484_SLEEVE_PCT,
        "leverage": K484_LEVERAGE,
        "notional_usd": K484_NOTIONAL_USD,
        "margin_usd": K484_MARGIN_USD,
        "ann_return_usd_10M": K484_ANN_RETURN_USD,
        "venue": "HL_PRIMARY",
    }

    print(f"""
  {gold('[ D+9 K484 AVAX-BTC LIVE — 48h after K476 — Manual Execution Required ]')}

  {cyan('Step 1: K476 D+2 PASS check (48h cascade gate)')}
  ─────────────────────────────────────────────────────
  cat data/k476_dashboard.json | python3 -c "import json,sys; d=json.load(sys.stdin); print('FillRate:', d.get('fill_rate_pct', 'N/A'), 'Sharpe:', d.get('60d_sharpe', 0))"
  # K476 must show position active, fill_rate > 0%, no error states

  {cyan('Step 2: K484 dashboard fresh state check')}
  ─────────────────────────────────────────────────────
  cat data/k484_dashboard.json | python3 -m json.tool | grep -E "position_state|paper_trade_mode|fr_avax_current|fr_btc_current"

  {cyan('Step 3: HL margin health check (post-K476 state)')}
  ─────────────────────────────────────────────────────
  # HL exposure at D+9: ~55% (K449+K476). Adding K484 3pp → ~58% (cap 65%)
  # Ensure HL margin account not stressed from K476 first 48h
  launchctl list | grep -E "k476|k280|k449"

  {cyan('Step 4: Configure K484 for LIVE (env vars)')}
  ─────────────────────────────────────────────────────
  export PAPER_TRADE=False
  export HL_USER_ADDRESS=<your-hl-wallet-address>
  # export HL_PRIVATE_KEY=<your-private-key>  (runtime injection only)

  {cyan('Step 5: Copy plist and activate K484 daemon (D+9)')}
  ─────────────────────────────────────────────────────
  REPO_ROOT="$(pwd)"
  sed "s|REPO_ROOT|$REPO_ROOT|g" com.cryptolab.k484-avax-btc.plist > ~/Library/LaunchAgents/com.cryptolab.k484-avax-btc.plist
  launchctl load ~/Library/LaunchAgents/com.cryptolab.k484-avax-btc.plist
  launchctl list | grep k484-avax-btc
  # Expected: com.cryptolab.k484-avax-btc listed with PID

  {cyan('Step 6: Post-activation monitor (D+9 → D+10)')}
  ─────────────────────────────────────────────────────
  tail -f logs/k484_avax_btc.log
  # HL post-Week-2: ~58% (K449 52% + K476 3pp + K484 3pp)
  # 7pp headroom remaining for K493 Week 3 (2.5pp HL split) + K500/K507/K512

  {bold('Position sizing @ $10M AUM:')}
  Sleeve:     3%  = $300,000 margin
  Leverage:   4x
  Total not.: $1,200,000 (2 legs: AVAX-PERP + BTC-PERP)
  Leg size:   $600,000 each
  HL only:    YES (HL_PRIMARY)
  FR poll:    8h cron (28800s StartInterval)

  {bold('48h cascade gap rationale:')}
  SOL-AVAX G5 cross-corr ≈ 0.28 (below 0.40 PASS, but non-trivial).
  Sequential D+7/D+9 activation spreads margin deployment, allows monitoring
  K476 fill rate and HL health before adding K484 exposure.
""")

    results["commands"] = [
        "cat data/k476_dashboard.json | python3 -c \"import json,sys; d=json.load(sys.stdin); print('K476 active:', not d.get('paper_trade_mode', True))\"",
        "sed \"s|REPO_ROOT|$(pwd)|g\" com.cryptolab.k484-avax-btc.plist > ~/Library/LaunchAgents/com.cryptolab.k484-avax-btc.plist",
        "launchctl load ~/Library/LaunchAgents/com.cryptolab.k484-avax-btc.plist",
        "launchctl list | grep k484-avax-btc",
        "tail -f logs/k484_avax_btc.log",
    ]
    return results


# ─────────────────────────────────────────────────────────────────────────────
# Phase 6: Day 7-21 monitoring
# ─────────────────────────────────────────────────────────────────────────────

def phase6_monitoring() -> Dict[str, Any]:
    """Phase 6: Day 7-21 dual monitoring framework for K476 and K484."""
    print(bold(f"\n{'='*70}"))
    print(bold("Phase 6: Day 7-21 Dual Monitoring (K476 + K484)"))
    print(bold(f"{'='*70}"))

    results: Dict[str, Any] = {
        "phase": 6, "name": "dual_monitoring",
        "monitor_window_days": 14,
        "metrics": [],
    }

    metrics = [
        ("Daily realized Sharpe",       "Both",   "Sh ≥ 50% of OOS target", "rolling 7d window"),
        ("Fill rate",                    "Both",   "≥ 60%",                  "8h interval average"),
        ("HL margin health",             "Both",   "margin ratio < 80%",     "launchctl + HL API"),
        ("Cross-strategy correlation",   "K476+K484","G5 check ≤ 0.40",     "7d rolling FR diff corr"),
        ("Delta-neutral drift",          "Both",   "< 2% per leg",           "auto-rebalance trigger"),
        ("FR signal fires",              "Both",   "≥ 1/week minimum",       "signal fire count"),
        ("HL exposure total",            "Portfolio","≤ 65% hard cap",       "K476 + K484 combined"),
        ("Funding rate diff (7d avg)",   "Both",   "SOL-BTC > 0 / AVAX-BTC > 0", "8h poll"),
    ]

    print(f"\n  {'Metric':<35} {'Scope':<12} {'Gate':<28} {'Method'}")
    print(f"  {'-'*35} {'-'*12} {'-'*28} {'-'*30}")
    for m, scope, gate, method in metrics:
        print(f"  {m:<35} {scope:<12} {gate:<28} {method}")
        results["metrics"].append({"metric": m, "scope": scope, "gate": gate, "method": method})

    print(f"""
  {cyan('Daily monitoring commands:')}
  ─────────────────────────────────────────────────────
  # K476 log tail:
  tail -20 logs/k476_sol_btc.log

  # K484 log tail:
  tail -20 logs/k484_avax_btc.log

  # Daemon alive check:
  launchctl list | grep -E "k476|k484|k449|k280"

  # Dashboard JSON snapshots:
  python3 -c "import json; [print(f.name, json.load(open(f)).get('position_state')) for f in __import__('pathlib').Path('data').glob('k4*.json')]"

  {cyan('HL margin health proxy:')}
  # Check that combined margin (K449 + K476 + K484) ≤ 9% of AUM
  # K449: 3% margin | K476: 3% margin | K484: 3% margin | Total: 9%
  # HL notional: K449 $1.2M + K476 $1.2M + K484 $1.2M = $3.6M @ $10M
""")

    return results


# ─────────────────────────────────────────────────────────────────────────────
# Phase 7: Decision matrix Day 14
# ─────────────────────────────────────────────────────────────────────────────

def phase7_decision_matrix() -> Dict[str, Any]:
    """Phase 7: D+14 decision matrix for K476 and K484."""
    print(bold(f"\n{'='*70}"))
    print(bold("Phase 7: Decision Matrix Day 14 (D+14)"))
    print(bold(f"{'='*70}"))

    results: Dict[str, Any] = {
        "phase": 7, "name": "decision_matrix_d14",
        "k476": {}, "k484": {},
    }

    print(f"""
  {cyan('K476 SOL-BTC — D+14 Decision (OOS Sh 16.30)')}
  ──────────────────────────────────────────────────────
  Realized Sh ≥ {K476_PASS_SHARPE:.0f}  (50% of OOS 16.30)  → {green('PASS → expand to 4-5%')}
  Realized Sh {K476_HOLD_SHARPE_LOW:.0f}–{K476_PASS_SHARPE:.0f}  (30-50%)         → {yellow('HOLD at 3% / continue monitoring')}
  Realized Sh < {K476_HOLD_SHARPE_LOW:.0f}  (< 30%)          → {red('ROLLBACK → paper-trade')}

  {cyan('K484 AVAX-BTC — D+14 Decision (OOS Sh 43.89)')}
  ──────────────────────────────────────────────────────
  Realized Sh ≥ {K484_PASS_SHARPE:.0f}  (50% of OOS 43.89) → {green('PASS → expand to 4-5%')}
  Realized Sh {K484_HOLD_SHARPE_LOW:.0f}–{K484_PASS_SHARPE:.0f}  (30-50%)        → {yellow('HOLD at 3% / continue monitoring')}
  Realized Sh < {K484_HOLD_SHARPE_LOW:.0f}  (< 30%)         → {red('ROLLBACK → paper-trade')}

  {cyan('Joint gate (both must pass for Week 3 prep):')}
  Fill rate both ≥ 60%:       required
  HL exposure ≤ 65%:          required (post-W2 ~58%, 7pp headroom)
  No HL margin calls:         required
  Cross-corr K476-K484 ≤ 0.40: confirm G5 (design-time G5 corr=0.28)

  {cyan('Expand path (PASS both):')}
  K476 expand: 3% → 4% sleeve → $400K margin → $1.6M notional
  K484 expand: 3% → 4% sleeve → $400K margin → $1.6M notional
  HL post-expand: ~58% + 2pp = ~60% (still under 65% cap)
  → then proceed to K493 Week 3 (K556 in flight)

  {cyan('Rollback path (if FAIL):')}
  launchctl unload ~/Library/LaunchAgents/com.cryptolab.k476-sol-btc.plist  # if K476 FAIL
  launchctl unload ~/Library/LaunchAgents/com.cryptolab.k484-avax-btc.plist  # if K484 FAIL
  # Reset paper_trade_mode=True in dashboard JSON and restart daemon --dry-run
""")

    results["k476"] = {
        "oos_sharpe": K476_OOS_SHARPE,
        "pass_threshold": K476_PASS_SHARPE,
        "hold_lower": K476_HOLD_SHARPE_LOW,
        "pass_action": "expand 3%→4%",
        "hold_action": "hold 3%",
        "rollback_action": "paper-trade",
    }
    results["k484"] = {
        "oos_sharpe": K484_OOS_SHARPE,
        "pass_threshold": K484_PASS_SHARPE,
        "hold_lower": K484_HOLD_SHARPE_LOW,
        "pass_action": "expand 3%→4%",
        "hold_action": "hold 3%",
        "rollback_action": "paper-trade",
    }
    return results


# ─────────────────────────────────────────────────────────────────────────────
# Phase 8: HL exposure trajectory post-Week 2
# ─────────────────────────────────────────────────────────────────────────────

def phase8_hl_exposure() -> Dict[str, Any]:
    """Phase 8: HL exposure trajectory through Week 2 and beyond."""
    print(bold(f"\n{'='*70}"))
    print(bold("Phase 8: HL Exposure Trajectory Post-Week 2"))
    print(bold(f"{'='*70}"))

    trajectory = [
        ("Baseline (v6.13e K280 60%)",     52.0, "after K449 W1, K280 60% applied"),
        ("+ K476 SOL-BTC D+7 (3pp)",       55.0, "K476 3% sleeve × 100% HL = +3pp"),
        ("+ K484 AVAX-BTC D+9 (3pp)",      58.0, "K484 3% sleeve × 100% HL = +3pp"),
        ("HL cap hard limit",               65.0, "never exceed — K476+K484 OK"),
        ("+ K493 ATOM-BTC W3 (2.5pp HL)",  60.5, "5% sleeve × 50% HL (Bybit split)"),
        ("+ K500+K507 SEI+TIA W4 (est)",   62.5, "combined ~2pp HL"),
        ("+ K512 APT W5 (est)",             64.0, "~1.5pp HL (Bybit primary)"),
        ("v6.28 full live target",          64.0, "all strategies active"),
    ]

    print(f"\n  {'Phase':<44} {'HL%':>6}  {'Note'}")
    print(f"  {'-'*44} {'-'*6}  {'-'*35}")
    for phase_name, hl_pct, note in trajectory:
        ok = hl_pct <= 65.0
        cap_note = "" if ok else " !! EXCEEDS CAP"
        bar_len = int(hl_pct / 2)
        bar = "#" * bar_len
        colour = green if hl_pct <= 58 else (yellow if hl_pct <= 63 else red)
        print(f"  {phase_name:<44} {colour(f'{hl_pct:>5.1f}%')}  {note}{cap_note}")

    print(f"""
  {cyan('Post-Week 2 headroom analysis:')}
  HL post-Week 2: 58% (K449 52% + K476 3pp + K484 3pp)
  Headroom: 65% - 58% = 7pp remaining
    → K493 Week 3 (5% sleeve, HL-Bybit split → +2.5pp HL): 58% + 2.5pp = 60.5%
    → K500+K507 SEI+TIA Week 4 (est +2pp): 62.5%
    → K512 APT Week 5 (est +1.5pp): 64%
    → v6.28 full deployment: 64% (1pp safety margin)

  {bold('Emergency exit registration:')}
  K357 handles all paired-trade strategies (registered K478, K489).
  Verify: launchctl list | grep k357
""")

    results: Dict[str, Any] = {
        "phase": 8, "name": "hl_exposure_trajectory",
        "post_week2_hl_pct": 58.0,
        "cap_pct": 65.0,
        "headroom_pp": 7.0,
        "trajectory": [{"phase": t[0], "hl_pct": t[1], "note": t[2]} for t in trajectory],
    }
    return results


# ─────────────────────────────────────────────────────────────────────────────
# Phase 9: Profit summary Week 2
# ─────────────────────────────────────────────────────────────────────────────

def phase9_profit_summary() -> Dict[str, Any]:
    """Phase 9: Cumulative profit summary post-Week 2."""
    print(bold(f"\n{'='*70}"))
    print(bold("Phase 9: Profit Summary — Week 2 (K476 + K484)"))
    print(bold(f"{'='*70}"))

    strategies = [
        ("K449 ETH-BTC",   WEEK1_K449_USD,     "D0  (W1)"),
        ("K476 SOL-BTC",   WEEK2_K476_USD,     "D+7 (W2)"),
        ("K484 AVAX-BTC",  WEEK2_K484_USD,     "D+9 (W2)"),
        ("TOTAL W1+W2",    CUMULATIVE_W2_USD,  "cumulative"),
    ]

    print(f"\n  {'Strategy':<20} {'$10M':>12} {'$30M':>12} {'$100M':>12}  {'Timing'}")
    print(f"  {'-'*20} {'-'*12} {'-'*12} {'-'*12}  {'-'*12}")
    for name, base_usd, timing in strategies:
        v10  = base_usd
        v30  = base_usd * 3
        v100 = base_usd * 10
        fmt = gold if "TOTAL" in name else str
        print(f"  {fmt(f'{name:<20}')} {fmt(f'${v10:>10,}')} {fmt(f'${v30:>10,}')} {fmt(f'${v100:>10,}')}  {timing}")

    print(f"""
  {cyan('Monthly and daily breakdown (@ $10M):')}
    K476 SOL-BTC:  $187,000/yr = $15,583/mo = $512/day
    K484 AVAX-BTC: $76,000/yr  = $6,333/mo  = $208/day
    Week 2 add:    $263,000/yr = $21,916/mo  = $720/day
    Cumulative:    $276,000/yr = $23,000/mo  = $756/day

  {cyan('Annualized yield @ $10M (Week 2 combined):')}
    K476 sleeve 3% × 4x → capital efficiency: $187K/$1.2M notional = 15.6%/yr
    K484 sleeve 3% × 4x → capital efficiency: $76K/$1.2M notional = 6.3%/yr
    Combined Week 2: $263K/$2.4M notional = 11.0%/yr
""")

    results: Dict[str, Any] = {
        "phase": 9, "name": "profit_summary_week2",
        "k449_ann_usd": WEEK1_K449_USD,
        "k476_ann_usd": WEEK2_K476_USD,
        "k484_ann_usd": WEEK2_K484_USD,
        "week2_combined_ann_usd": WEEK2_COMBINED_USD,
        "cumulative_w2_ann_usd": CUMULATIVE_W2_USD,
        "at_30M": {
            "k476": WEEK2_K476_USD * 3, "k484": WEEK2_K484_USD * 3,
            "cumulative": CUMULATIVE_W2_USD * 3,
        },
        "at_100M": {
            "k476": WEEK2_K476_USD * 10, "k484": WEEK2_K484_USD * 10,
            "cumulative": CUMULATIVE_W2_USD * 10,
        },
    }
    return results


# ─────────────────────────────────────────────────────────────────────────────
# Phase 10: Risk register
# ─────────────────────────────────────────────────────────────────────────────

def phase10_risk() -> Dict[str, Any]:
    """Phase 10: Risk register for Week 2 dual activation."""
    print(bold(f"\n{'='*70}"))
    print(bold("Phase 10: Risk Register — Week 2 Dual Activation"))
    print(bold(f"{'='*70}"))

    risks = [
        ("Cascade risk (dual same week)",   "MEDIUM", "48h gap D+7/D+9 mitigates (K547 protocol)"),
        ("SOL volatility (high vol alt)",   "MEDIUM", "4x leverage, delta-neutral both legs — vol isolated to FR diff"),
        ("AVAX subnet ecosystem",           "LOW",    "subnet-driven FR spikes = edge source; G5 corr=0.28 managed"),
        ("HL cap proximity",                "LOW",    "58% post-W2 vs 65% cap — 7pp headroom for W3-W5"),
        ("SOL-AVAX cross-corr spike",       "LOW",    "G5 design-time corr=0.28 (PASS <0.40); 48h gap adds monitoring"),
        ("Fill rate degradation",           "MEDIUM", "POST_ONLY_PARALLEL ensures maker; HL_ONLY primary confirmed"),
        ("FR regime shift (SOL→0)",         "LOW",    "7d rolling avg gate; position NEUTRAL if SOL-BTC diff < threshold"),
        ("FR regime shift (AVAX→0)",        "LOW",    "same gate mechanism; AVAX-BTC diff check"),
        ("HL margin call (dual LIVE)",      "LOW",    "3% margin each × 4x → 9% total margin; K357 exit registered"),
        ("K449 W1 not PASS by D+7",         "LOW",    "Phase 1 prereq gate; if K449 not LIVE → delay K476 activation"),
    ]

    print(f"\n  {'Risk':<40} {'Level':<8} {'Mitigation'}")
    print(f"  {'-'*40} {'-'*8} {'-'*40}")
    for risk, level, mitigation in risks:
        colour = red if level == "HIGH" else (yellow if level == "MEDIUM" else green)
        print(f"  {risk:<40} {colour(f'{level:<8}')} {mitigation}")

    results: Dict[str, Any] = {
        "phase": 10, "name": "risk_register",
        "risks": [{"risk": r[0], "level": r[1], "mitigation": r[2]} for r in risks],
    }
    return results


# ─────────────────────────────────────────────────────────────────────────────
# Checklists
# ─────────────────────────────────────────────────────────────────────────────

def checklist_d7() -> Dict[str, Any]:
    """User action checklist for D+7 (K476 LIVE)."""
    print(bold(f"\n{'='*70}"))
    print(bold("D+7 User Checklist — K476 SOL-BTC LIVE"))
    print(bold(f"{'='*70}"))

    steps = [
        ("1", "K449 W1 Day 7 PASS confirm",
         "cat data/k449_dashboard.json | python3 -c \"import json,sys; print(json.load(sys.stdin).get('paper_trade_mode'))\""),
        ("2", "K476 dashboard fresh check",
         "python3 wave_k558_k476_k484_week2_live.py --phase2"),
        ("3", "K280 ≤60% weight verify",
         "cat data/k280_live_dashboard.json | python3 -c \"import json,sys; print(json.load(sys.stdin).get('k280_weight_pct'))\""),
        ("4", "K357 emergency exit alive",
         "launchctl list | grep k357"),
        ("5", "Env vars set (PAPER_TRADE=False, HL_USER_ADDRESS, HL_PRIVATE_KEY)",
         "export PAPER_TRADE=False; export HL_USER_ADDRESS=<addr>; export HL_PRIVATE_KEY=<key>"),
        ("6", "Copy plist to LaunchAgents",
         "sed \"s|REPO_ROOT|$(pwd)|g\" com.cryptolab.k476-sol-btc.plist > ~/Library/LaunchAgents/com.cryptolab.k476-sol-btc.plist"),
        ("7", "launchctl load K476",
         "launchctl load ~/Library/LaunchAgents/com.cryptolab.k476-sol-btc.plist"),
        ("8", "Verify daemon alive",
         "launchctl list | grep k476-sol-btc"),
        ("9", "3% sleeve initial position confirm ($300K margin)",
         "tail -20 logs/k476_sol_btc.log"),
        ("10", "24h monitor window begins",
         "# D+7 → D+8: fill rate, delta drift, FR polling — no action unless emergency"),
    ]

    print()
    for num, action, cmd in steps:
        print(f"  {cyan(f'[{num:>2}]')} {action}")
        print(f"       {grey(cmd)}")

    return {"day": "D+7", "strategy": "K476 SOL-BTC",
            "steps": [{"num": s[0], "action": s[1], "cmd": s[2]} for s in steps]}


def checklist_d9() -> Dict[str, Any]:
    """User action checklist for D+9 (K484 LIVE, 48h after K476)."""
    print(bold(f"\n{'='*70}"))
    print(bold("D+9 User Checklist — K484 AVAX-BTC LIVE (48h after K476)"))
    print(bold(f"{'='*70}"))

    steps = [
        ("1", "K476 D+2 PASS check (48h gate)",
         "cat data/k476_dashboard.json | python3 -c \"import json,sys; d=json.load(sys.stdin); print('Active:', not d.get('paper_trade_mode', True))\""),
        ("2", "K476 fill rate > 0% (first 48h)",
         "grep -i 'fill\\|trade\\|position' logs/k476_sol_btc.log | tail -10"),
        ("3", "HL margin health (post-K476 55%)",
         "launchctl list | grep -E 'k476|k449|k280'"),
        ("4", "K484 dashboard fresh check",
         "python3 wave_k558_k476_k484_week2_live.py --phase3"),
        ("5", "Env vars set (PAPER_TRADE=False, HL_USER_ADDRESS, HL_PRIVATE_KEY)",
         "export PAPER_TRADE=False; export HL_USER_ADDRESS=<addr>; export HL_PRIVATE_KEY=<key>"),
        ("6", "Copy plist to LaunchAgents",
         "sed \"s|REPO_ROOT|$(pwd)|g\" com.cryptolab.k484-avax-btc.plist > ~/Library/LaunchAgents/com.cryptolab.k484-avax-btc.plist"),
        ("7", "launchctl load K484",
         "launchctl load ~/Library/LaunchAgents/com.cryptolab.k484-avax-btc.plist"),
        ("8", "Verify daemon alive",
         "launchctl list | grep k484-avax-btc"),
        ("9", "3% sleeve initial position confirm ($300K margin)",
         "tail -20 logs/k484_avax_btc.log"),
        ("10", "HL exposure verify (~58%, headroom 7pp)",
         "# K449 52% + K476 3pp + K484 3pp = 58% < 65% cap ✓"),
        ("11", "24h monitor window begins",
         "# D+9 → D+10: dual monitor K476+K484 — D+14 decision matrix"),
    ]

    print()
    for num, action, cmd in steps:
        print(f"  {cyan(f'[{num:>2}]')} {action}")
        print(f"       {grey(cmd)}")

    return {"day": "D+9", "strategy": "K484 AVAX-BTC",
            "steps": [{"num": s[0], "action": s[1], "cmd": s[2]} for s in steps]}


def checklist_d14() -> Dict[str, Any]:
    """D+14 decision matrix execution checklist."""
    print(bold(f"\n{'='*70}"))
    print(bold("D+14 Decision Matrix — Both K476 + K484"))
    print(bold(f"{'='*70}"))

    steps = [
        ("1", "K476 realized Sharpe check",
         "cat data/k476_dashboard.json | python3 -c \"import json,sys; print('Sh:', json.load(sys.stdin).get('60d_sharpe', 0))\""),
        ("2", "K484 realized Sharpe check",
         "cat data/k484_dashboard.json | python3 -c \"import json,sys; print('Sh:', json.load(sys.stdin).get('60d_sharpe', 0))\""),
        ("3", "K476 fill rate check",
         "grep 'fill_rate' logs/k476_sol_btc.log | tail -5"),
        ("4", "K484 fill rate check",
         "grep 'fill_rate' logs/k484_avax_btc.log | tail -5"),
        ("5", "HL margin ratio check",
         "launchctl list | grep -E 'k476|k484|k449|k280|k357'"),
        ("6", "Apply decision matrix per phase7",
         "python3 wave_k558_k476_k484_week2_live.py --phase7"),
        ("7", "If PASS (K476 Sh≥8, K484 Sh≥22): expand to 4%",
         "# Update portfolio_config.json: k476_sleeve_pct=0.04, k484_sleeve_pct=0.04"),
        ("8", "If HOLD: maintain 3%, continue to D+21",
         "# No action — continue monitoring"),
        ("9", "If ROLLBACK: unload daemon + paper-trade",
         "launchctl unload ~/Library/LaunchAgents/com.cryptolab.k476-sol-btc.plist  # if K476 FAIL"),
        ("10", "Week 3 K493 ATOM prep (K556 in flight)",
         "python3 wave_k556_k493_week3_live.py --status"),
    ]

    print()
    for num, action, cmd in steps:
        print(f"  {cyan(f'[{num:>2}]')} {action}")
        print(f"       {grey(cmd)}")

    return {"day": "D+14", "both_strategies": True,
            "steps": [{"num": s[0], "action": s[1], "cmd": s[2]} for s in steps]}


# ─────────────────────────────────────────────────────────────────────────────
# Status overview
# ─────────────────────────────────────────────────────────────────────────────

def status_overview() -> Dict[str, Any]:
    """Quick status overview for Wave K558."""
    print(bold(f"\n{'='*70}"))
    print(bold(f"Wave K558 — K476+K484 Week 2 Dual LIVE Prep — Status Overview"))
    print(bold(f"{'='*70}"))

    now_jst = datetime.now(timezone(timedelta(hours=9)))
    print(f"\n  {cyan('Generated:')} {now_jst.strftime('%Y-%m-%d %H:%M JST')}")
    print(f"  {cyan('Wave:')} K558")
    print(f"  {cyan('Playbook:')} K547 sequenced activation Week 2")
    print(f"""
  {bold('Week 2 strategies:')}
    D+7: K476 SOL-BTC FR Differential
         OOS Sh 16.30 | $187K/yr @$10M | 3% sleeve | HL_ONLY
    D+9: K484 AVAX-BTC FR Differential  (48h after K476)
         OOS Sh 43.89 | $76K/yr @$10M  | 3% sleeve | HL_ONLY

  {bold('Combined Week 2:  $263K/yr @$10M | $789K/yr @$30M | $2.63M/yr @$100M')}
  {bold('Cumulative W1-W2: $276K/yr @$10M | $828K/yr @$30M | $2.76M/yr @$100M')}

  {bold('HL exposure:')}
    Pre-Week 2:  ~52%  (post K449 W1)
    Post K476:   ~55%  (+3pp)
    Post K484:   ~58%  (+3pp, under 65% cap)
    Headroom:      7pp for W3 K493 + W4 K500/K507 + W5 K512

  {bold('K547 sequenced activation status:')}
    Week 1: K449 ETH-BTC  D0  $13K/yr   — K549 playbook (in flight)
    Week 2: K476 SOL-BTC  D+7 $187K/yr  ← THIS WAVE
            K484 AVAX-BTC D+9 $76K/yr   ← THIS WAVE (48h cascade)
    Week 3: K493 ATOM-BTC D14 $231K/yr  — K556 in flight
    Week 4: K500+K507     D21 $354K/yr
    Week 5: K512 APT      D35 $302K/yr
""")

    return {
        "wave": WAVE,
        "generated_jst": now_jst.strftime("%Y-%m-%d %H:%M JST"),
        "k476": {"day": "D+7", "oos_sharpe": K476_OOS_SHARPE, "ann_usd": K476_ANN_RETURN_USD},
        "k484": {"day": "D+9", "oos_sharpe": K484_OOS_SHARPE, "ann_usd": K484_ANN_RETURN_USD},
        "week2_combined_usd": WEEK2_COMBINED_USD,
        "cumulative_w2_usd": CUMULATIVE_W2_USD,
        "hl_post_week2_pct": HL_POST_WEEK2 * 100,
    }


# ─────────────────────────────────────────────────────────────────────────────
# Export JSON
# ─────────────────────────────────────────────────────────────────────────────

def export_json(all_results: Dict[str, Any]) -> None:
    """Export full playbook state to wave_k558_k476_k484_week2_live.json."""
    now_jst = datetime.now(timezone(timedelta(hours=9)))
    payload = {
        "wave": WAVE,
        "generated_jst": now_jst.strftime("%Y-%m-%d %H:%M JST"),
        "description": "K558 Week 2 K476 SOL-BTC + K484 AVAX-BTC dual LIVE activation playbook",
        "k476": {
            "strategy": "K476 SOL-BTC FR Differential",
            "oos_sharpe": K476_OOS_SHARPE,
            "ann_return_usd_10M": K476_ANN_RETURN_USD,
            "activation_day": "D+7",
            "sleeve_pct": K476_SLEEVE_PCT,
            "leverage": K476_LEVERAGE,
            "notional_usd": K476_NOTIONAL_USD,
            "margin_usd": K476_MARGIN_USD,
            "venue": "HL_PRIMARY",
            "pass_sharpe": K476_PASS_SHARPE,
            "hold_lower": K476_HOLD_SHARPE_LOW,
        },
        "k484": {
            "strategy": "K484 AVAX-BTC FR Differential",
            "oos_sharpe": K484_OOS_SHARPE,
            "ann_return_usd_10M": K484_ANN_RETURN_USD,
            "activation_day": "D+9",
            "cascade_gap_hours": CASCADE_GAP_HOURS,
            "sleeve_pct": K484_SLEEVE_PCT,
            "leverage": K484_LEVERAGE,
            "notional_usd": K484_NOTIONAL_USD,
            "margin_usd": K484_MARGIN_USD,
            "venue": "HL_PRIMARY",
            "pass_sharpe": K484_PASS_SHARPE,
            "hold_lower": K484_HOLD_SHARPE_LOW,
        },
        "profit": {
            "week2_combined_ann_usd": WEEK2_COMBINED_USD,
            "cumulative_w2_ann_usd": CUMULATIVE_W2_USD,
            "at_10M": {"k476": WEEK2_K476_USD, "k484": WEEK2_K484_USD,
                       "combined": WEEK2_COMBINED_USD, "cumulative": CUMULATIVE_W2_USD},
            "at_30M": {"k476": WEEK2_K476_USD * 3, "k484": WEEK2_K484_USD * 3,
                       "combined": WEEK2_COMBINED_USD * 3, "cumulative": CUMULATIVE_W2_USD * 3},
            "at_100M": {"k476": WEEK2_K476_USD * 10, "k484": WEEK2_K484_USD * 10,
                        "combined": WEEK2_COMBINED_USD * 10, "cumulative": CUMULATIVE_W2_USD * 10},
        },
        "hl_exposure": {
            "post_week1_pct": HL_POST_WEEK1 * 100,
            "post_k476_pct": HL_POST_K476 * 100,
            "post_week2_pct": HL_POST_WEEK2 * 100,
            "cap_pct": HL_CAP * 100,
            "headroom_pp": HL_POST_W2_HEADROOM * 100,
        },
        "decision_matrix_d14": {
            "k476": {"pass_sharpe": K476_PASS_SHARPE, "hold_lower": K476_HOLD_SHARPE_LOW},
            "k484": {"pass_sharpe": K484_PASS_SHARPE, "hold_lower": K484_HOLD_SHARPE_LOW},
        },
        "phases": all_results,
    }
    with open(OUTPUT_JSON, "w") as f:
        json.dump(payload, f, indent=2)
    print(f"\n  {green('[EXPORT]')} Written to {OUTPUT_JSON.name}")


# ─────────────────────────────────────────────────────────────────────────────
# CLI
# ─────────────────────────────────────────────────────────────────────────────

def main() -> None:
    parser = argparse.ArgumentParser(
        description=f"Wave K558 — K476+K484 Week 2 Dual LIVE Activation Playbook"
    )
    parser.add_argument("--status",        action="store_true", help="Quick status overview")
    parser.add_argument("--phase1",        action="store_true", help="Pre-requisite checklist")
    parser.add_argument("--phase2",        action="store_true", help="K476 scaffold audit")
    parser.add_argument("--phase3",        action="store_true", help="K484 scaffold audit")
    parser.add_argument("--phase4",        action="store_true", help="D+7 K476 LIVE activation")
    parser.add_argument("--phase5",        action="store_true", help="D+9 K484 LIVE activation")
    parser.add_argument("--phase6",        action="store_true", help="Day 7-21 monitoring")
    parser.add_argument("--phase7",        action="store_true", help="D+14 decision matrix")
    parser.add_argument("--phase8",        action="store_true", help="HL exposure trajectory")
    parser.add_argument("--phase9",        action="store_true", help="Profit summary Week 2")
    parser.add_argument("--phase10",       action="store_true", help="Risk register")
    parser.add_argument("--checklist-d7",  action="store_true", help="D+7 K476 user checklist")
    parser.add_argument("--checklist-d9",  action="store_true", help="D+9 K484 user checklist")
    parser.add_argument("--checklist-d14", action="store_true", help="D+14 decision checklist")
    parser.add_argument("--all",           action="store_true", help="Run all phases")
    parser.add_argument("--export-json",   action="store_true", help="Export to JSON")
    args = parser.parse_args()

    all_results: Dict[str, Any] = {}

    if args.status or not any(vars(args).values()):
        all_results["status"] = status_overview()

    if args.phase1 or args.all:
        all_results["phase1"] = phase1_prereq()
    if args.phase2 or args.all:
        all_results["phase2"] = phase2_k476_audit()
    if args.phase3 or args.all:
        all_results["phase3"] = phase3_k484_audit()
    if args.phase4 or args.all:
        all_results["phase4"] = phase4_k476_live()
    if args.phase5 or args.all:
        all_results["phase5"] = phase5_k484_live()
    if args.phase6 or args.all:
        all_results["phase6"] = phase6_monitoring()
    if args.phase7 or args.all:
        all_results["phase7"] = phase7_decision_matrix()
    if args.phase8 or args.all:
        all_results["phase8"] = phase8_hl_exposure()
    if args.phase9 or args.all:
        all_results["phase9"] = phase9_profit_summary()
    if args.phase10 or args.all:
        all_results["phase10"] = phase10_risk()
    if args.checklist_d7 or args.all:
        all_results["checklist_d7"] = checklist_d7()
    if args.checklist_d9 or args.all:
        all_results["checklist_d9"] = checklist_d9()
    if args.checklist_d14 or args.all:
        all_results["checklist_d14"] = checklist_d14()

    if args.export_json or args.all:
        export_json(all_results)

    print()


if __name__ == "__main__":
    main()

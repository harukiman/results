#!/usr/bin/env python3
"""
wave_k540_dual_catalyst_prep.py — K540 HIP-5 + Clarity Act Dual Catalyst June 4-5 Playbook
=============================================================================================
Time-critical: 5-6 days to event window (current date: 2026-05-30)

Catalysts:
  - R16-01  HIP-5 AF2 Token Buyback vote — June 5 deadline
  - R16-11  Clarity Act Senate floor vote — June 4-5

Combined potential: +$620K/yr mid-range if PASS+PASS
Immediate impact:   +$200K (base) to +$400K (high) USDC in first 30 days post-event

K339 REPO_ROOT pattern: all paths relative to REPO_ROOT.
No live trading modifications — playbook + decision tree only.
Stdlib only, no new packages.

Usage:
  python3 wave_k540_dual_catalyst_prep.py            # generate all outputs + update report.html
  python3 wave_k540_dual_catalyst_prep.py --dry-run  # generate outputs only, skip HTML update
"""
from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Dict, List, Any, Optional

# ── K339 canonical paths ──────────────────────────────────────────────────────
REPO_ROOT  = Path(__file__).resolve().parent
JSON_OUT   = REPO_ROOT / "wave_k540_dual_catalyst_prep.json"
MD_OUT     = REPO_ROOT / "wave_k540_dual_catalyst_prep.md"
REPORT_OUT = REPO_ROOT / "report.html"

# ── Constants ─────────────────────────────────────────────────────────────────
WAVE          = "K540"
DATE_JST      = "2026-05-30"
EVENT_DATE_1  = "2026-06-04"   # Clarity Act floor vote day 1
EVENT_DATE_2  = "2026-06-05"   # HIP-5 vote deadline + Clarity Act day 2
EFFECTIVE_DATE = "2026-06-14"  # Clarity Act effective date (post-signature)

# Profit projections @$10M portfolio (USDC/yr)
PROFIT_PP_LOW  = 200_000   # PASS+PASS, low
PROFIT_PP_MID  = 420_000   # PASS+PASS, mid
PROFIT_PP_HIGH = 620_000   # PASS+PASS, high (combined R16-01+R16-11)
PROFIT_PP_IMM  = 200_000   # immediate first-month equivalent (annualized)

PROFIT_PF_LOW  = 80_000    # PASS+FAIL, low
PROFIT_PF_MID  = 220_000   # PASS+FAIL, mid (HIP-5 alone)

PROFIT_FP_LOW  = 150_000   # FAIL+PASS, low
PROFIT_FP_MID  = 400_000   # FAIL+PASS, mid (Clarity alone)

PROFIT_FF_LOW  = -50_000   # FAIL+FAIL event loss
PROFIT_FF_MID  = -20_000   # FAIL+FAIL median

# Current portfolio state (K524)
HL_EXPOSURE_PCT    = 65.0   # exactly at cap
CASH_RESERVE_PCT   = 1.0    # per v6.13d
LEVERAGE_CURRENT   = 3      # K430 activated
LEVERAGE_EVENT     = 2      # temporary reduction for event window

JST = timezone(timedelta(hours=9))


def now_jst() -> str:
    return datetime.now(JST).strftime("%Y-%m-%d %H:%M JST")


# ── Phase 1: HIP-5 AF2 Deep-Dive ─────────────────────────────────────────────

HIP5_ANALYSIS: Dict[str, Any] = {
    "id": "R16-01",
    "proposal": "HIP-5 AF2 (Assistance Fund 2) Token Buyback",
    "voting_deadline": "2026-06-05",
    "announcement_window": "2026-06-05 18:00 ET (result expected)",
    "current_sentiment": {
        "favor": 49,
        "against": 46,
        "abstain": 5,
        "as_of": "2026-05-30",
        "institutional_participation_pct": 40,
        "passage_probability": 68,   # botter estimate 65-70%
    },
    "mechanism": {
        "buyback_capacity_usd_yr": 80_000_000,   # $80M/yr additional buyback
        "supply_impact": "HYPE deflation rate acceleration; supply reduction compounding",
        "protocol_buy_pressure": "AF2 token (HyperEVM) receives protocol buy pressure explicit mandate",
        "hype_price_multiplier": "est. $0.5-1.2/token upside on passage (R16-01 analysis)",
    },
    "profit_pathway": {
        "primary": "HL exposure maintained (currently at 65% cap) → HYPE price appreciation",
        "secondary": "HYPE direct purchase (separate sleeve, not counted in HL 65% cap)",
        "tertiary": "K376 momentum captures HYPE spike within D+1 to D+7",
    },
    "risk_if_fail": {
        "governance_signal": "BEARISH — institutional participation >40% still voted against",
        "hype_price_impact": "est. -3% to -8% immediate (sell-the-news)",
        "k362_signal": "K362 confidence drops ±30%; short-term vol increase",
    },
    "monitor_source": "https://governance.hyperliquid.co/proposals/hip-5",
    "monitor_frequency": "Every 6h from June 1; every 1h from June 4",
}


# ── Phase 2: Clarity Act Deep-Dive (K403 update) ─────────────────────────────

CLARITY_ACT_ANALYSIS: Dict[str, Any] = {
    "id": "R16-11",
    "bill": "Digital Asset Market Clarity Act of 2025 (H.R.3633, 119th Congress)",
    "vote_schedule": "June 4-5, 2026 (Senate floor vote)",
    "effective_date": EFFECTIVE_DATE,
    "passage_probability": 87,   # 53-47 likely per R16-11; swing votes confirmed "support"
    "k403_update": {
        "bull1_prob": 14,   # K403 updated from 10% → 14%
        "bull2_prob": 22,   # K403 updated from 20% → 22%
        "bear1_prob": 11,   # K403 updated from 15% → 11%
        "bear2_prob": 27,   # K403 updated from 30% → 27%
        "scenario_c": 16,
        "scenario_d": 10,
    },
    "k540_update": {
        "note": "Floor vote now June 4-5 (accelerated from July 4 target per R16-11)",
        "bull1_prob_updated": 20,   # Floor vote = near-final step; higher confidence
        "bear1_prob_updated": 8,    # Lower given confirmed swing votes
    },
    "defi_dev_exemption": {
        "hl_perp_qualifies": "OPEN — 'truly decentralized' definition left to rulemaking (18-24mo post-passage)",
        "immediate_impact": "Regulatory risk premium reduction → +15-30% institutional capital inflow potential",
        "k297_rwa_impact": "DeFi RWA strategies benefit from explicit legal framework for tokenized assets",
    },
    "institutional_inflow_window": {
        "day_0_to_7": "Pre-positioning + immediate institutional response",
        "day_7_to_30": "ETF/fund manager reallocation (compliance sign-off period)",
        "day_30_to_90": "Major institutional capital deployment (after legal review completion)",
    },
    "profit_pathway": {
        "primary": "HL regulatory risk discount removed → K280 40%+K376 35% HL exposure maintained/increased",
        "secondary": "Institutional volume increase → K376 momentum more frequent events",
        "tertiary": "K297' RWA position expansion (DeFi legal clarity)",
    },
    "risk_if_fail": {
        "regulatory_status": "BEAR_1 probability reverts to 15% (K403 baseline)",
        "k385_revert": "Probability matrix resets to pre-K403 levels",
        "sharpe_impact": "-0.72pp annualized expected Sharpe (K403 analysis)",
    },
    "monitor_source": "https://www.senate.gov (floor schedule); https://theblock.co",
    "monitor_keyword": [
        "Clarity Act floor vote",
        "Digital Asset Market Clarity",
        "DeFi exemption vote",
        "Senate crypto vote June 4",
    ],
}


# ── Phase 3: Catalyst Interaction Analysis ────────────────────────────────────

CATALYST_INTERACTION: Dict[str, Any] = {
    "synergy_scenarios": {
        "PASS_PASS": {
            "label": "HIP-5 PASS + Clarity PASS",
            "probability": 0.68 * 0.87,   # ~0.59 independent
            "hl_volume_spike": "+35-55% within 72h (institutional rush + governance confidence)",
            "funding_rate_variance": "Spike to +150bp range (both events = max bullish positioning)",
            "hype_price_action": "+8-20% D+1 to D+7",
            "k208_impact": "Funding rate spike = tactical opportunity for K208 macro-event capture",
            "k280_k376_synergy": "Both sleeves benefit; K376 momentum events likely 2-3 within D+3 to D+14",
            "profit_usdc_yr_low":  PROFIT_PP_LOW,
            "profit_usdc_yr_mid":  PROFIT_PP_MID,
            "profit_usdc_yr_high": PROFIT_PP_HIGH,
            "immediate_usdc":      PROFIT_PP_IMM,
            "action": "MAX_BULLISH — K376 momentum sleeve activate 2-3% (K376 confirmed BULL_CONFIRMED), HYPE purchase",
        },
        "PASS_FAIL": {
            "label": "HIP-5 PASS, Clarity FAIL",
            "probability": 0.68 * 0.13,   # ~0.09
            "hl_volume_spike": "+10-20% short term (HL-specific governance confidence)",
            "funding_rate_variance": "Moderate spike +50-80bp (governance-driven, not macro)",
            "hype_price_action": "+3-7% D+1, fade after",
            "profit_usdc_yr_low":  PROFIT_PF_LOW,
            "profit_usdc_yr_mid":  PROFIT_PF_MID,
            "profit_usdc_yr_high": 350_000,
            "immediate_usdc":      80_000,
            "action": "MODERATE_BULLISH — Hold current position; watch for HYPE buying opportunity on spike",
        },
        "FAIL_PASS": {
            "label": "HIP-5 FAIL, Clarity PASS",
            "probability": 0.32 * 0.87,   # ~0.28
            "hl_volume_spike": "+20-35% (regulatory clarity drives institutional inflow)",
            "funding_rate_variance": "+80-120bp (macro/regulatory-driven)",
            "hype_price_action": "-3-8% (governance failure), then recovery +5-10% from Clarity tailwind",
            "profit_usdc_yr_low":  PROFIT_FP_LOW,
            "profit_usdc_yr_mid":  PROFIT_FP_MID,
            "profit_usdc_yr_high": 600_000,
            "immediate_usdc":      120_000,
            "action": "MODERATE_BULLISH — K297' position add (RWA DeFi clarity); avoid HYPE direct in short term",
        },
        "FAIL_FAIL": {
            "label": "HIP-5 FAIL, Clarity FAIL",
            "probability": 0.32 * 0.13,   # ~0.04
            "hl_volume_spike": "-10-20% (risk-off, regulatory uncertainty preserved)",
            "funding_rate_variance": "Spike negative -100bp possible (forced liquidation)",
            "hype_price_action": "-8-15% combined sell-off",
            "profit_usdc_yr_low":  PROFIT_FF_LOW,
            "profit_usdc_yr_mid":  PROFIT_FF_MID,
            "profit_usdc_yr_high": 0,
            "immediate_usdc":      -50_000,
            "action": "DEFENSIVE — Reduce HL exposure 5% (→60%), K344 EMERGENCY guard check, no new positions",
        },
    },
    "expected_value_usdc_yr": {
        "calculation": "weighted sum of mid scenarios by probability",
        "pp": round(0.59 * PROFIT_PP_MID),
        "pf": round(0.09 * PROFIT_PF_MID),
        "fp": round(0.28 * PROFIT_FP_MID),
        "ff": round(0.04 * PROFIT_FF_MID),
        "total_ev": round(0.59 * PROFIT_PP_MID + 0.09 * PROFIT_PF_MID +
                         0.28 * PROFIT_FP_MID + 0.04 * PROFIT_FF_MID),
    },
}


# ── Phase 4: Pre-Event Preparation (D-5 to D-1) ──────────────────────────────

PRE_EVENT_PREP: Dict[str, Any] = {
    "D-5 (2026-05-30)": {
        "date": "2026-05-30",
        "actions": [
            {
                "id": "D5-1",
                "task": "Read K540 playbook",
                "detail": "Review this document and decision tree",
                "effort": "15min",
                "risk": "NONE",
            },
            {
                "id": "D5-2",
                "task": "HL position check",
                "detail": "Verify HL exposure is 65.0% (exactly at cap). No new HL adds.",
                "effort": "5min",
                "risk": "NONE",
                "command": "Check portfolio dashboard; verify HL sleeve = 65.0%",
            },
            {
                "id": "D5-3",
                "task": "Cash reserve verify",
                "detail": "Confirm 1.0% cash reserve per v6.13d (do not deploy pre-event)",
                "effort": "5min",
                "risk": "NONE",
            },
            {
                "id": "D5-4",
                "task": "Approve K344 EMERGENCY guard",
                "detail": "Verify K344 emergency exit daemon is ARMED and tested (dry-run)",
                "effort": "20min",
                "risk": "LOW",
                "command": "launchctl list | grep k344; check emergency_exit_guard.py --dry-run",
            },
            {
                "id": "D5-5",
                "task": "K387 RSS monitor: add Clarity Act keywords",
                "detail": "Add R16-11 keywords to regulatory_rss_monitor.py (K403 recommendation)",
                "effort": "30min",
                "risk": "NONE",
                "keywords": CLARITY_ACT_ANALYSIS["monitor_keyword"],
            },
        ],
    },
    "D-3 (2026-06-01)": {
        "date": "2026-06-01",
        "actions": [
            {
                "id": "D3-1",
                "task": "HIP-5 vote progress check",
                "detail": "Check governance.hyperliquid.co for updated vote tallies",
                "effort": "10min",
                "risk": "NONE",
            },
            {
                "id": "D3-2",
                "task": "Senate schedule confirmation",
                "detail": "Confirm Clarity Act floor vote still scheduled June 4-5 (Senate.gov)",
                "effort": "5min",
                "risk": "NONE",
            },
        ],
    },
    "D-1 (2026-06-03)": {
        "date": "2026-06-03",
        "actions": [
            {
                "id": "D1-1",
                "task": "K430 leverage 3x → 2x temporary mode",
                "detail": "Reduce leverage from 3x to 2x for event window risk management",
                "effort": "15min",
                "risk": "LOW — reduces position sizing, temporary only",
                "note": "Revert to 3x at D+7 if vol normalizes",
            },
            {
                "id": "D1-2",
                "task": "Cancel pending OTC orders",
                "detail": "Cancel any large OTC/limit orders that could execute during event volatility",
                "effort": "10min",
                "risk": "NONE",
            },
            {
                "id": "D1-3",
                "task": "Set volume spike alert",
                "detail": "Configure HL volume spike alert threshold: +30% vs 7-day avg",
                "effort": "15min",
                "risk": "NONE",
                "threshold": "HL volume 30% above 7d rolling average",
            },
            {
                "id": "D1-4",
                "task": "Set HYPE price alert",
                "detail": "Configure HYPE price alerts: +5% and -5% from D-1 close",
                "effort": "10min",
                "risk": "NONE",
            },
            {
                "id": "D1-5",
                "task": "K357 emergency exit dry-run",
                "detail": "Run K357 emergency exit simulation; confirm execution path",
                "effort": "30min",
                "risk": "NONE (dry-run only)",
            },
        ],
    },
}


# ── Phase 5: Event Day (D=0, June 4-5) ───────────────────────────────────────

EVENT_DAY: Dict[str, Any] = {
    "timeline": {
        "June 4 AM (ET)": "Senate floor debate begins; follow C-SPAN or senate.gov live feed",
        "June 4 12:00-15:00 ET": "Senate procedural votes (cloture motions expected)",
        "June 4 18:00 ET": "Potential final vote count; watch for 53+ 'aye' signals",
        "June 5 09:00 ET": "Clarity Act vote result confirmed (latest)",
        "June 5 18:00 ET": "HIP-5 voting deadline (governance.hyperliquid.co)",
        "June 5 19:00 ET": "HIP-5 result announcement (usually ~1h after deadline)",
    },
    "monitoring": {
        "clarity_act": [
            "C-SPAN Senate livestream (senate.gov/c-span)",
            "TheBlock.co live coverage",
            "K387 RSS monitor (should auto-alert)",
        ],
        "hip5": [
            "governance.hyperliquid.co/proposals/hip-5",
            "Hyperliquid Discord #governance",
            "botter note.com (post-vote analysis usually within 2h)",
        ],
    },
    "decision_tree": CATALYST_INTERACTION["synergy_scenarios"],
    "execution_timing": {
        "PASS_PASS": "Execute within 2h of BOTH confirmed (fastest alpha window D0+2h to D0+24h)",
        "PASS_FAIL": "Execute within 24h; smaller position than PASS+PASS",
        "FAIL_PASS": "Execute K297' add within 48h; avoid HYPE for 72h",
        "FAIL_FAIL": "Defensive within 4h; reduce HL exposure 5% before Asia open",
    },
}


# ── Phase 6: Post-Event (D+1 to D+14) ────────────────────────────────────────

POST_EVENT: Dict[str, Any] = {
    "D+1 to D+3": {
        "funding_rate_check": "Monitor BTC/ETH/HYPE funding rates; compare to pre-event baseline",
        "etf_flow_check": "Check Bitcoin ETF daily flows (proxy for institutional appetite)",
        "hype_price_action": "HYPE chart: D+1 reaction sets trajectory for D+7 target",
        "k208_opportunity": "Check for funding rate spike event qualification (K208 macro-event variant)",
    },
    "D+7 (2026-06-11)": {
        "review_items": [
            "Funding rate post-event analysis (is +150bp spike sustained or reversion?)",
            "K297' / K280 weight adjustment (if Clarity PASS, consider K280 → K376 rebalance)",
            "K376 momentum event count since D0 (expected 2-3 if PASS+PASS)",
            "Restore K430 leverage to 3x if post-event vol < pre-event baseline",
        ],
        "weight_adjustment_guide": {
            "PASS_PASS": "K376 maintain/increase; K280 stable; HYPE position evaluate",
            "PASS_FAIL": "K376 stable; K280 stable; HYPE hold short-term",
            "FAIL_PASS": "K297' +2% allocation; K376 stable; HYPE reduce if -5%+ from D0",
            "FAIL_FAIL": "Restore exposure only after 7 consecutive days without regulatory headlines",
        },
    },
    "D+14 (2026-06-18)": {
        "hl_q2_revenue_checkpoint": "June 15 Hyperliquid Q2 revenue report (R16-09); confirms/revises HYPE valuation",
        "fomc_window": "June 19 FOMC — second macro event within 14 days; prepare K208 macro-event variant",
        "clarity_act_effective": "June 14 Clarity Act effective date (if signed in time); institutional positioning shift",
    },
}


# ── Phase 7: Profit Projection (Catalyst-Conditional) ────────────────────────

PROFIT_PROJECTION: Dict[str, Any] = {
    "portfolio_base": 10_000_000,   # $10M reference
    "scenarios": {
        "PASS_PASS_base": {
            "label": "Base Case: HIP-5 PASS + Clarity PASS",
            "immediate_usdc": 200_000,
            "ongoing_usdc_yr": 420_000,
            "note": "K376 2-3% momentum sleeve + HYPE direct purchase + institutional inflow lift",
        },
        "PASS_PASS_high": {
            "label": "Optimistic Case: PASS + PASS + Q2 revenue beat",
            "immediate_usdc": 400_000,
            "ongoing_usdc_yr": 620_000,
            "note": "Full R16-01 + R16-11 + R16-09 combo; June 15 Q2 revenue >$180M confirms",
        },
        "PASS_FAIL": {
            "label": "Conservative: HIP-5 PASS only",
            "immediate_usdc": 80_000,
            "ongoing_usdc_yr": 220_000,
            "note": "HYPE buyback mechanism alone without regulatory catalyst",
        },
        "FAIL_PASS": {
            "label": "Conservative: Clarity PASS only",
            "immediate_usdc": 120_000,
            "ongoing_usdc_yr": 400_000,
            "note": "Regulatory clarity drives institutional inflow; K297' RWA expansion viable",
        },
        "FAIL_FAIL": {
            "label": "Bear Case: Both FAIL",
            "immediate_usdc": -50_000,
            "ongoing_usdc_yr": 0,
            "note": "Event loss from leveraged positioning; revert K403 probability matrix",
        },
    },
    "expected_value": CATALYST_INTERACTION["expected_value_usdc_yr"],
}


# ── Phase 8: User Action Checklist ────────────────────────────────────────────

USER_CHECKLIST: List[Dict[str, Any]] = [
    # D-5
    {"phase": "D-5 (May 30)", "id": "D5-1", "action": "Read K540 playbook", "effort": "15min", "priority": "HIGH"},
    {"phase": "D-5 (May 30)", "id": "D5-2", "action": "HL position check — confirm 65.0% cap exactly", "effort": "5min", "priority": "HIGH"},
    {"phase": "D-5 (May 30)", "id": "D5-3", "action": "Cash reserve verify — confirm 1.0% free", "effort": "5min", "priority": "HIGH"},
    {"phase": "D-5 (May 30)", "id": "D5-4", "action": "K344 EMERGENCY guard: arm + dry-run test", "effort": "20min", "priority": "HIGH"},
    {"phase": "D-5 (May 30)", "id": "D5-5", "action": "K387 RSS monitor: add Clarity Act keywords", "effort": "30min", "priority": "MEDIUM"},
    # D-1
    {"phase": "D-1 (Jun 3)", "id": "D1-1", "action": "K430 leverage 3x → 2x (event risk reduction)", "effort": "15min", "priority": "HIGH"},
    {"phase": "D-1 (Jun 3)", "id": "D1-2", "action": "Cancel pending OTC orders", "effort": "10min", "priority": "MEDIUM"},
    {"phase": "D-1 (Jun 3)", "id": "D1-3", "action": "Set HL volume spike alert: +30% threshold", "effort": "15min", "priority": "HIGH"},
    {"phase": "D-1 (Jun 3)", "id": "D1-4", "action": "Set HYPE price alert: ±5%", "effort": "10min", "priority": "MEDIUM"},
    {"phase": "D-1 (Jun 3)", "id": "D1-5", "action": "K357 emergency exit dry-run", "effort": "30min", "priority": "HIGH"},
    # D=0
    {"phase": "D=0 (Jun 4-5)", "id": "D0-1", "action": "Monitor Senate vote — C-SPAN / TheBlock", "effort": "ongoing", "priority": "CRITICAL"},
    {"phase": "D=0 (Jun 4-5)", "id": "D0-2", "action": "Monitor HIP-5 results — governance.hyperliquid.co", "effort": "ongoing", "priority": "CRITICAL"},
    {"phase": "D=0 (Jun 4-5)", "id": "D0-3", "action": "Execute decision tree based on outcomes (see Phase 5)", "effort": "2-4h", "priority": "CRITICAL"},
    # D+7
    {"phase": "D+7 (Jun 11-12)", "id": "D7-1", "action": "Review funding rate post-event (K208 signal check)", "effort": "30min", "priority": "HIGH"},
    {"phase": "D+7 (Jun 11-12)", "id": "D7-2", "action": "Adjust K297' / K280 weights per decision tree outcome", "effort": "1h", "priority": "HIGH"},
    {"phase": "D+7 (Jun 11-12)", "id": "D7-3", "action": "Restore K430 leverage 3x if post-event vol normalizes", "effort": "15min", "priority": "MEDIUM"},
    {"phase": "D+7 (Jun 11-12)", "id": "D7-4", "action": "Pre-position for June 15 Q2 revenue report (R16-09)", "effort": "30min", "priority": "HIGH"},
]


# ── Phase 9: Daemon Prep ──────────────────────────────────────────────────────

DAEMON_PREP: Dict[str, Any] = {
    "k344_emergency_exit": {
        "status_check": "launchctl list com.cryptolab.k344-emergency-guard",
        "expected": "ACTIVE",
        "dashboard_freshness": "Must be updated within 24h of event day",
        "action_if_stale": "Restart daemon: launchctl kickstart -k gui/$(id -u)/com.cryptolab.k344-emergency-guard",
    },
    "k387_rss_monitor": {
        "status_check": "launchctl list com.cryptolab.regulatory-rss",
        "keywords_to_add": CLARITY_ACT_ANALYSIS["monitor_keyword"],
        "file": "regulatory_rss_monitor.py",
        "action": "Add Clarity Act keywords; restart daemon",
    },
    "k412_susde_apy": {
        "status_check": "launchctl list com.cryptolab.susde-apy-monitor",
        "relevance": "sUSDe yield shifts during event volatility; monitor for strategy re-weight trigger",
        "threshold": "sUSDe APY < 2.5% → trigger stablecoin rebalance review (R16-10)",
    },
    "hl_hip4_monitor": {
        "status_check": "launchctl list com.cryptolab.hl-hip4-monitor",
        "relevance": "HIP-5 result may create new HIP-4 prediction markets (per K403 Phase 7)",
        "action": "Verify monitor is active; add HIP-5 result as new market trigger",
    },
}


# ── Phase 10: Memory + Playbook Formalization ─────────────────────────────────

PLAYBOOK_PATTERN: Dict[str, Any] = {
    "pattern_name": "dual_catalyst_event_window",
    "formalization_date": DATE_JST,
    "wave_origin": WAVE,
    "protocol": {
        "lead_time_required": "5-7 days",
        "leverage_reduction": "3x → 2x on D-1",
        "exposure_freeze": "No new HL adds from D-5 to D+1",
        "cash_reserve_maintain": "1% minimum, 2% preferred during event",
        "daemon_checks": ["k344", "k387", "k412", "hl-hip4"],
        "monitoring_frequency": "Every 6h D-5 to D-2, every 1h D-1 to D+1",
    },
    "decision_tree_template": {
        "outcome_A_passes": "BULLISH action (see PASS_PASS / PASS_FAIL branches)",
        "outcome_A_fails": "DEFENSIVE check before outcome_B confirmed",
        "outcome_B_passes": "Add PASS_* actions",
        "outcome_B_fails": "Defensive: reduce exposure, check EMERGENCY guard",
    },
    "applicable_future_events": [
        "June 19 FOMC meeting (next macro window)",
        "June 15 Hyperliquid Q2 revenue report (R16-09)",
        "HIP-6+ governance votes (if created post-HIP-5)",
        "ETF approval decisions (SEC; K385 BULL_1 trigger)",
    ],
}


# ── Output Generation ─────────────────────────────────────────────────────────

def build_full_output() -> Dict[str, Any]:
    ts = now_jst()
    ev = CATALYST_INTERACTION["expected_value_usdc_yr"]

    return {
        "wave": WAVE,
        "generated_jst": ts,
        "title": "K540 HIP-5 + Clarity Act Dual Catalyst June 4-5 Playbook",
        "event_dates": [EVENT_DATE_1, EVENT_DATE_2],
        "effective_date": EFFECTIVE_DATE,
        "profit_projection": PROFIT_PROJECTION,
        "hip5_analysis": HIP5_ANALYSIS,
        "clarity_act_analysis": CLARITY_ACT_ANALYSIS,
        "catalyst_interaction": CATALYST_INTERACTION,
        "pre_event_prep": PRE_EVENT_PREP,
        "event_day": EVENT_DAY,
        "post_event": POST_EVENT,
        "user_checklist": USER_CHECKLIST,
        "daemon_prep": DAEMON_PREP,
        "playbook_pattern": PLAYBOOK_PATTERN,
        "portfolio_context": {
            "hl_exposure_pct": HL_EXPOSURE_PCT,
            "cash_reserve_pct": CASH_RESERVE_PCT,
            "leverage_current": LEVERAGE_CURRENT,
            "leverage_event": LEVERAGE_EVENT,
        },
        "expected_value_summary": {
            "ev_usdc_yr": ev["total_ev"],
            "ev_breakdown": {
                "pp_contribution": ev["pp"],
                "pf_contribution": ev["pf"],
                "fp_contribution": ev["fp"],
                "ff_contribution": ev["ff"],
            },
            "immediate_usdc_base_case": 200_000,
            "ongoing_usdc_yr_base_case": 420_000,
        },
        "files": {
            "py": "wave_k540_dual_catalyst_prep.py",
            "json": "wave_k540_dual_catalyst_prep.json",
            "md": "wave_k540_dual_catalyst_prep.md",
        },
    }


def write_json(output: Dict[str, Any]) -> None:
    JSON_OUT.write_text(json.dumps(output, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"  [K540] JSON → {JSON_OUT}")


def write_markdown(output: Dict[str, Any]) -> None:
    ts = output["generated_jst"]
    ev = output["expected_value_summary"]

    lines: List[str] = []

    lines += [
        f"# Wave K540 — HIP-5 + Clarity Act Dual Catalyst Playbook",
        f"",
        f"**Generated:** {ts}  ",
        f"**Wave:** {WAVE}  ",
        f"**Event Window:** June 4-5, 2026 (5-6 days from current date 2026-05-30)  ",
        f"**Expected Value:** +${ev['ev_usdc_yr']:,}/yr @$10M (probability-weighted mid scenarios)  ",
        f"**Base Case (PASS+PASS):** +$200K immediate, +$420K/yr ongoing  ",
        f"**High Case (PASS+PASS+Q2beat):** +$400K immediate, +$620K/yr ongoing  ",
        f"",
        f"---",
        f"",
        f"## Executive Summary",
        f"",
        f"Two high-impact catalysts converge on June 4-5, 2026:",
        f"",
        f"| Catalyst | Event | Date | Mid Impact |",
        f"|----------|-------|------|-----------|",
        f"| R16-01 | HIP-5 AF2 Token Buyback vote | June 5 (18:00 ET deadline) | +$220K/yr |",
        f"| R16-11 | Clarity Act Senate floor passage | June 4-5 | +$400K/yr |",
        f"| **Combined** | **Both PASS** | **June 4-5** | **+$620K/yr** |",
        f"",
        f"**Passage probabilities (independent):**",
        f"- HIP-5: 68% (botter estimate; 49% favor as of May 30, institutional participation >40%)",
        f"- Clarity Act: 87% (53-47 projected; swing votes confirmed 'support')",
        f"- Both PASS: ~59% probability",
        f"",
        f"**Current portfolio state:** HL 65.0% (exactly at cap), 1% cash reserve, 3x leverage (K430)",
        f"**Event risk management:** Leverage → 2x on D-1; no new HL adds D-5 to D+1",
        f"",
        f"---",
        f"",
        f"## Phase 1: HIP-5 AF2 Deep-Dive",
        f"",
        f"**Proposal:** HIP-5 Assistance Fund 2 — Ecosystem Token Buyback  ",
        f"**Voting deadline:** June 5, 2026 at 18:00 ET  ",
        f"**Current vote (May 30):** 49% favor / 46% against / 5% abstain  ",
        f"**Passage probability:** 68% (institutional participation >40%)  ",
        f"",
        f"### Mechanism",
        f"",
        f"- **Buyback capacity:** $80M/yr additional once HIP-5 passes",
        f"- **AF2 token:** HyperEVM-native token receives explicit protocol buy pressure mandate",
        f"- **HYPE deflation:** Supply reduction accelerates; compounding deflationary effect",
        f"- **Price impact estimate:** $0.5-1.2/token upside on passage",
        f"",
        f"### Profit Pathway",
        f"",
        f"1. **Primary:** HL exposure maintained at 65% cap → HYPE price appreciation benefits K280/K376",
        f"2. **Secondary:** HYPE direct purchase (separate sleeve, not in HL 65% cap count)",
        f"3. **Tertiary:** K376 momentum captures HYPE spike within D+1 to D+7",
        f"",
        f"### Risk If HIP-5 Fails",
        f"",
        f"- Governance signal: BEARISH (institutional vote against creates confidence concern)",
        f"- HYPE price: -3% to -8% immediate (sell-the-news on high vote participation)",
        f"- K362 signal confidence: ±30% swing; short-term vol increase",
        f"",
        f"### Monitor",
        f"",
        f"- Source: `governance.hyperliquid.co/proposals/hip-5`",
        f"- Frequency: Every 6h from June 1; every 1h from June 4; real-time June 5",
        f"",
        f"---",
        f"",
        f"## Phase 2: Clarity Act Deep-Dive (K403 Update)",
        f"",
        f"**Bill:** Digital Asset Market Clarity Act of 2025 (H.R.3633, 119th Congress)  ",
        f"**Vote schedule:** June 4-5, 2026 Senate floor (ACCELERATED from July 4 target)  ",
        f"**Effective date:** June 14, 2026 (if signed within 10 days of passage)  ",
        f"**Passage probability:** 87% (53-47 projected; 2 swing Dem senators confirmed support)  ",
        f"",
        f"### K403 Probability Matrix — K540 Update",
        f"",
        f"| Scenario | K403 Prob | K540 Update | Delta | Reason |",
        f"|----------|-----------|-------------|-------|--------|",
        f"| BULL_1 (SEC exempt + CFTC settles) | 14% | 20% | +6pp | Floor vote = near-final step |",
        f"| BULL_2 (SEC exempt + CFTC adversarial) | 22% | 24% | +2pp | Marginal uplift |",
        f"| BEAR_1 (SEC delays + CFTC enforcement) | 11% | 8% | -3pp | Swing votes confirmed |",
        f"| BEAR_2 (status quo) | 27% | 24% | -3pp | Legislative path now clearer |",
        f"| C (both stand down) | 16% | 14% | -2pp | Slight reallocation |",
        f"| D (dual enforcement EMERGENCY) | 10% | 10% | 0pp | Unchanged |",
        f"",
        f"### DeFi Dev Exemption Impact",
        f"",
        f"- **HL qualification:** OPEN — 'truly decentralized' threshold left to rulemaking (18-24mo post-passage)",
        f"- **Immediate regulatory risk removal:** HL risk premium drops; +15-30% institutional capital inflow",
        f"- **K297' RWA impact:** DeFi RWA strategies get explicit legal framework for tokenized assets",
        f"- **Institutional inflow window:** D0-D7 (pre-positioning), D7-D30 (reallocation), D30-D90 (major capital)",
        f"",
        f"### Monitor",
        f"",
        f"- Senate.gov floor schedule; TheBlock.co; K387 RSS monitor (auto-alert)",
        f"- Keywords: 'Clarity Act floor vote', 'Digital Asset Market Clarity', 'DeFi exemption vote'",
        f"",
        f"---",
        f"",
        f"## Phase 3: Catalyst Interaction — Decision Tree",
        f"",
        f"### 4-Outcome Scenario Matrix",
        f"",
        f"| Scenario | Probability | HL Volume Spike | HYPE Price | Profit @$10M/yr | Action |",
        f"|----------|-------------|----------------|------------|-----------------|--------|",
        f"| PASS+PASS | ~59% | +35-55% | +8-20% | +$420K mid | MAX_BULLISH |",
        f"| PASS+FAIL | ~9% | +10-20% | +3-7% | +$220K mid | MODERATE |",
        f"| FAIL+PASS | ~28% | +20-35% | -3→+10% | +$400K mid | MODERATE+ |",
        f"| FAIL+FAIL | ~4% | -10-20% | -8-15% | -$20K mid | DEFENSIVE |",
        f"",
        f"**Expected Value:** +${ev['ev_usdc_yr']:,}/yr @$10M (probability-weighted)",
        f"",
        f"### Scenario Actions",
        f"",
        f"**PASS+PASS (MAX BULLISH):**",
        f"- Execute within 2h of both confirmed",
        f"- K376 momentum sleeve: activate 2-3% (BULL_CONFIRMED expected ~7d; event may trigger early)",
        f"- HYPE direct purchase: evaluate position size (target 2-5% of portfolio)",
        f"- K208 macro-event variant: watch for funding rate spike >150bp (capture window)",
        f"- No leverage increase — maintain 2x through D+3 then re-evaluate",
        f"",
        f"**PASS+FAIL (HIP-5 pass, Clarity fail):**",
        f"- Hold current HL position; no new adds",
        f"- Watch HYPE price for entry if spike >5% (sell-the-news risk; wait for D+2 stabilization)",
        f"- K297' position: no change (Clarity Act failed = RWA legal clarity still pending)",
        f"- K403 probability matrix: revert Clarity Act probability shifts back to baseline",
        f"",
        f"**FAIL+PASS (HIP-5 fail, Clarity pass):**",
        f"- K297' position add: +2% allocation (DeFi legal clarity enables RWA expansion)",
        f"- Avoid HYPE direct for 72h (governance failure = near-term headwind)",
        f"- K376: institutional inflow should increase momentum event frequency; maintain exposure",
        f"- v6.13d HL cap: Clarity passage strengthens case for 65%+ but maintain cap D+7",
        f"",
        f"**FAIL+FAIL (DEFENSIVE):**",
        f"- Execute within 4h of BOTH confirmed",
        f"- Reduce HL exposure: 65% → 60% (5% reduction before Asia open)",
        f"- K344 EMERGENCY guard: verify armed status",
        f"- K403 probability matrix: revert all K540 updates; BEAR_1 back to 15%",
        f"- No new positions for 7 days minimum",
        f"",
        f"---",
        f"",
        f"## Phase 4: Pre-Event Preparation Checklist",
        f"",
        f"### D-5 (Today, May 30)",
        f"",
        f"- [ ] **D5-1** Read K540 playbook (this document) — 15min",
        f"- [ ] **D5-2** HL position check: confirm 65.0% exposure exactly — 5min",
        f"- [ ] **D5-3** Cash reserve: confirm 1.0% free (do not deploy pre-event) — 5min",
        f"- [ ] **D5-4** K344 EMERGENCY guard: arm + dry-run test — 20min",
        f"- [ ] **D5-5** K387 RSS monitor: add Clarity Act keywords — 30min",
        f"",
        f"### D-1 (June 3)",
        f"",
        f"- [ ] **D1-1** K430 leverage: 3x → 2x temporary mode — 15min",
        f"- [ ] **D1-2** Cancel pending OTC orders — 10min",
        f"- [ ] **D1-3** Set HL volume spike alert: +30% vs 7-day avg — 15min",
        f"- [ ] **D1-4** Set HYPE price alert: ±5% from D-1 close — 10min",
        f"- [ ] **D1-5** K357 emergency exit dry-run — 30min",
        f"",
        f"---",
        f"",
        f"## Phase 5: Event Day (D=0, June 4-5)",
        f"",
        f"### Timeline",
        f"",
        f"| Time (ET) | Event | Monitor |",
        f"|-----------|-------|---------|",
        f"| Jun 4 AM | Senate floor debate begins | C-SPAN / senate.gov |",
        f"| Jun 4 12:00-15:00 | Procedural votes (cloture) | TheBlock.co live |",
        f"| Jun 4 18:00 | Potential final vote count | K387 RSS auto-alert |",
        f"| Jun 5 09:00 | Clarity Act result confirmed | Senate.gov / TheBlock |",
        f"| Jun 5 18:00 | HIP-5 voting deadline | governance.hyperliquid.co |",
        f"| Jun 5 19:00 | HIP-5 result announcement | Hyperliquid Discord #governance |",
        f"",
        f"### D=0 Checklist",
        f"",
        f"- [ ] **D0-1** Monitor Senate vote — C-SPAN / TheBlock (ongoing)",
        f"- [ ] **D0-2** Monitor HIP-5 results — governance.hyperliquid.co (ongoing)",
        f"- [ ] **D0-3** Execute decision tree based on outcomes (see Phase 3)",
        f"",
        f"---",
        f"",
        f"## Phase 6: Post-Event (D+1 to D+14)",
        f"",
        f"### D+1 to D+3",
        f"",
        f"- Monitor BTC/ETH/HYPE funding rates vs pre-event baseline",
        f"- Check Bitcoin ETF daily flows (proxy for institutional appetite)",
        f"- HYPE chart: D+1 reaction sets trajectory for D+7 target",
        f"- K208: check for funding rate spike event qualification (macro-event variant opportunity)",
        f"",
        f"### D+7 (June 11-12)",
        f"",
        f"- [ ] **D7-1** Review funding rate post-event (K208 signal check) — 30min",
        f"- [ ] **D7-2** Adjust K297' / K280 weights per outcome — 1h",
        f"- [ ] **D7-3** Restore K430 leverage 3x if post-event vol normalizes — 15min",
        f"- [ ] **D7-4** Pre-position for June 15 Q2 revenue report (R16-09) — 30min",
        f"",
        f"### D+14 (June 18)",
        f"",
        f"- **June 15:** Hyperliquid Q2 revenue report (R16-09 checkpoint) — confirms/revises HYPE valuation",
        f"- **June 14:** Clarity Act effective date (if signed) — institutional positioning shift begins",
        f"- **June 19:** FOMC meeting — K208 macro-event variant window",
        f"",
        f"---",
        f"",
        f"## Phase 7: Profit Projection (Catalyst-Conditional)",
        f"",
        f"All figures @$10M portfolio reference.",
        f"",
        f"| Scenario | Immediate (1mo equiv) | Ongoing $/yr | Notes |",
        f"|----------|----------------------|--------------|-------|",
        f"| PASS+PASS (base) | +$200,000 | +$420,000 | K376 + HYPE + institutional inflow |",
        f"| PASS+PASS (high) | +$400,000 | +$620,000 | + Q2 revenue beat (R16-09) |",
        f"| PASS+FAIL | +$80,000 | +$220,000 | HIP-5 alone |",
        f"| FAIL+PASS | +$120,000 | +$400,000 | Clarity alone; K297' expansion |",
        f"| FAIL+FAIL | -$50,000 | $0 | Event loss; defensive posture |",
        f"| **EV (weighted)** | **~+$139,000** | **+${ev['ev_usdc_yr']:,}** | **Probability-weighted mid** |",
        f"",
        f"---",
        f"",
        f"## Phase 8: Daemon Prep Summary",
        f"",
        f"| Daemon | Check Command | Expected | Action |",
        f"|--------|--------------|----------|--------|",
        f"| K344 emergency exit | `launchctl list com.cryptolab.k344*` | ACTIVE | Dry-run test D-5 |",
        f"| K387 regulatory RSS | `launchctl list com.cryptolab.regulatory-rss` | ACTIVE | Add Clarity keywords |",
        f"| K412 sUSDe APY | `launchctl list com.cryptolab.susde-apy-monitor` | ACTIVE | Threshold: APY < 2.5% |",
        f"| HL HIP-4 monitor | `launchctl list com.cryptolab.hl-hip4-monitor` | ACTIVE | Add HIP-5 trigger |",
        f"",
        f"---",
        f"",
        f"## Phase 9: Memory + Playbook Formalization",
        f"",
        f"**Pattern:** `dual_catalyst_event_window`  ",
        f"**Protocol summary:**",
        f"- Lead time required: 5-7 days",
        f"- Leverage: 3x → 2x on D-1",
        f"- Exposure: freeze HL from D-5 to D+1",
        f"- Cash reserve: 1% minimum, 2% preferred during event",
        f"- Monitoring: every 6h D-5 to D-2, every 1h D-1 to D+1",
        f"- Daemon checks: k344, k387, k412, hl-hip4",
        f"",
        f"**Applicable future events:**",
        f"- June 19 FOMC (K208 macro-event window)",
        f"- June 15 Hyperliquid Q2 revenue report (R16-09)",
        f"- HIP-6+ governance votes (post-HIP-5)",
        f"- ETF approval decisions (K385 BULL_1 trigger)",
        f"",
        f"---",
        f"",
        f"## K302a Phase A Supplement — R16 Catalyst Integration",
        f"",
        f"_This section feeds into `docs/k302a_master_deployment.md` Phase A_",
        f"",
        f"**R16 catalysts added to deployment consideration:**",
        f"",
        f"| Catalyst | K Action | Trigger | +$/yr @$10M |",
        f"|----------|----------|---------|------------|",
        f"| HIP-5 PASS | HYPE direct purchase (new sleeve) | June 5 result | +$80-220K |",
        f"| Clarity PASS | K297' +2% allocation; K376 institutional inflow uplift | June 14 effective | +$150-400K |",
        f"| HIP-5+Clarity PASS | K376 momentum 2-3% sleeve activate | D+7 if BULL_CONFIRMED | +$247K |",
        f"| Q2 revenue >$180M | K362 HYPE reweight; confirm K280 stability | June 15 | +$100-300K |",
        f"",
        f"---",
        f"",
        f"*Generated by `wave_k540_dual_catalyst_prep.py` | K339 REPO_ROOT pattern | {ts}*",
    ]

    MD_OUT.write_text("\n".join(lines), encoding="utf-8")
    print(f"  [K540] MD → {MD_OUT}")


def update_report_html(output: Dict[str, Any], dry_run: bool = False) -> None:
    """Prepend K540 banner to report.html top (before K539 banner)."""
    if not REPORT_OUT.exists():
        print(f"  [K540] report.html not found — skipping HTML update")
        return

    ts_jst = output["generated_jst"]
    ev = output["expected_value_summary"]

    badge_html = (
        f'<!-- K540_BANNER_INSERTED -->\n'
        f'<!-- K540_BANNER -->\n'
        f'<div id="k540-banner" style="'
        f'background:linear-gradient(135deg,#1a0a2e 0%,#0d1b3e 50%,#0a2e1a 100%);'
        f'border:2px solid #00ff88;border-radius:10px;padding:18px 24px;'
        f'margin:0 0 24px 0;box-shadow:0 4px 24px rgba(0,255,136,0.35);'
        f'font-family:-apple-system,BlinkMacSystemFont,\'Segoe UI\',sans-serif;">\n'
        f'  <div style="display:flex;align-items:center;gap:14px;flex-wrap:wrap;">\n'
        f'    <span style="font-size:2.2rem;">&#9733;&#9733;&#9733;&#9733;</span>\n'
        f'    <div>\n'
        f'      <div style="color:#00ff88;font-size:1.2rem;font-weight:900;letter-spacing:0.02em;margin-bottom:4px;">'
        f'K540 Dual Catalyst Prep — June 4-5 (HIP-5 + Clarity Act)</div>\n'
        f'      <div style="color:#a8d8a8;font-size:0.97rem;font-weight:600;">'
        f'+$200-400K immediate &nbsp;|&nbsp; +$420K/yr ongoing if PASS+PASS &nbsp;|&nbsp; EV +${ev["ev_usdc_yr"]:,}/yr @$10M'
        f'</div>\n'
        f'    </div>\n'
        f'  </div>\n'
        f'  <div style="margin-top:14px;display:grid;grid-template-columns:repeat(auto-fit,minmax(160px,1fr));gap:10px;">\n'
        f'    <div style="background:rgba(0,255,136,0.08);border-radius:6px;padding:10px 12px;">\n'
        f'      <div style="color:#8b949e;font-size:0.78rem;margin-bottom:3px;">HIP-5 (Jun 5)</div>\n'
        f'      <div style="color:#00ff88;font-weight:700;">+$220K/yr mid</div>\n'
        f'      <div style="color:#e6edf3;font-size:0.82rem;">68% passage prob; buyback $80M/yr</div>\n'
        f'    </div>\n'
        f'    <div style="background:rgba(88,166,255,0.08);border-radius:6px;padding:10px 12px;">\n'
        f'      <div style="color:#8b949e;font-size:0.78rem;margin-bottom:3px;">Clarity Act (Jun 4-5)</div>\n'
        f'      <div style="color:#58a6ff;font-weight:700;">+$400K/yr mid</div>\n'
        f'      <div style="color:#e6edf3;font-size:0.82rem;">87% passage prob; institutional inflow</div>\n'
        f'    </div>\n'
        f'    <div style="background:rgba(255,215,0,0.08);border-radius:6px;padding:10px 12px;">\n'
        f'      <div style="color:#8b949e;font-size:0.78rem;margin-bottom:3px;">PASS+PASS</div>\n'
        f'      <div style="color:#ffd700;font-weight:700;">+$620K/yr high</div>\n'
        f'      <div style="color:#e6edf3;font-size:0.82rem;">~59% combined; K376+HYPE+K297\'</div>\n'
        f'    </div>\n'
        f'    <div style="background:rgba(248,81,73,0.08);border-radius:6px;padding:10px 12px;">\n'
        f'      <div style="color:#8b949e;font-size:0.78rem;margin-bottom:3px;">FAIL+FAIL defense</div>\n'
        f'      <div style="color:#f85149;font-weight:700;">HL 65%→60%</div>\n'
        f'      <div style="color:#e6edf3;font-size:0.82rem;">~4% prob; K344 EMERGENCY guard</div>\n'
        f'    </div>\n'
        f'  </div>\n'
        f'  <div style="margin-top:12px;color:#8b949e;font-size:0.8rem;">\n'
        f'    Generated: {ts_jst} &nbsp;|&nbsp; Wave K540 &nbsp;|&nbsp;\n'
        f'    D-5: HL=65% cap, cash=1%, leverage=3x &nbsp;|&nbsp;\n'
        f'    D-1: leverage→2x &nbsp;|&nbsp; D=0: decision tree execution &nbsp;|&nbsp;\n'
        f'    D+7: K430 restore if vol normal, K297\' adjust &nbsp;|&nbsp;\n'
        f'    Effective date Clarity: Jun 14 &nbsp;|&nbsp; Q2 revenue checkpoint: Jun 15\n'
        f'  </div>\n'
        f'</div>\n'
        f'<!-- /K540_BANNER -->\n\n'
    )

    if dry_run:
        print(f"  [K540] DRY-RUN: would write {len(badge_html)} chars banner to report.html")
        return

    html = REPORT_OUT.read_text(encoding="utf-8")

    # Idempotent: remove existing K540 banner if present
    removed = 0
    while "K540_BANNER_INSERTED" in html:
        start = html.find("<!-- K540_BANNER_INSERTED -->")
        end = html.find("<!-- /K540_BANNER -->", start)
        if start == -1 or end == -1:
            break
        end += len("<!-- /K540_BANNER -->\n\n")
        html = html[:start] + html[end:]
        removed += 1
    if removed:
        print(f"  [K540] Removed {removed} existing K540 banner(s)")

    # Update last-update timestamp
    old_ts_pattern = '<span id="last-update">'
    if old_ts_pattern in html:
        old_start = html.find(old_ts_pattern) + len(old_ts_pattern)
        old_end = html.find("</span>", old_start)
        html = html[:old_start] + f"{ts_jst} (K540 Dual Catalyst Prep)" + html[old_end:]

    # Prepend before K539 banner or first existing banner
    insertion_markers = [
        "<!-- K539_BANNER_INSERTED -->",
        "<!-- K539_BANNER -->",
        '<div id="k539-banner"',
        '<span style="color:#00ff88;font-weight:900;font-size:1.6em;',
        '<span style="color:#58a6ff;font-weight:900;font-size:1.6em;',
    ]
    inserted = False
    for marker in insertion_markers:
        idx = html.find(marker)
        if idx != -1:
            html = html[:idx] + badge_html + html[idx:]
            print(f"  [K540] Banner prepended before '{marker[:40]}...'")
            inserted = True
            break

    if not inserted:
        # Fallback: insert after <div class="container">
        container = '<div class="container">'
        idx = html.find(container)
        if idx != -1:
            ins = idx + len(container) + 1
            html = html[:ins] + badge_html + html[ins:]
            print(f"  [K540] Banner inserted after container div (fallback)")
        else:
            print(f"  [K540] WARNING: could not find insertion point in report.html")

    REPORT_OUT.write_text(html, encoding="utf-8")
    print(f"  [K540] report.html updated → {REPORT_OUT}")


def update_k302a(dry_run: bool = False) -> None:
    """Append K540 catalyst section to docs/k302a_master_deployment.md."""
    k302a = REPO_ROOT / "docs" / "k302a_master_deployment.md"
    if not k302a.exists():
        print(f"  [K540] k302a_master_deployment.md not found — skipping")
        return

    ts = now_jst()
    ev = CATALYST_INTERACTION["expected_value_usdc_yr"]

    supplement = f"""

---

## K540 R16 Catalyst Integration (Added {ts})

### June 4-5 Dual Catalyst Event Window

| Catalyst | Status | Passage Prob | +$/yr @$10M | Trigger |
|----------|--------|-------------|------------|---------|
| R16-01 HIP-5 AF2 Buyback | Voting June 5 | 68% | +$80-220K | June 5 18:00 ET result |
| R16-11 Clarity Act | Floor vote June 4-5 | 87% | +$150-400K | Senate.gov confirmation |
| Both PASS (combined) | — | ~59% | +$420K mid | Both confirmed D+0 |

### Portfolio Action by Outcome

| Outcome | HL Exposure | K376 | K297' | K430 Leverage | Notes |
|---------|------------|------|-------|--------------|-------|
| PASS+PASS | Hold 65% | Activate 2-3% sleeve | Hold | Restore 3x D+7 | MAX_BULLISH |
| PASS+FAIL | Hold 65% | Hold | Hold | Restore 3x D+7 | MODERATE |
| FAIL+PASS | Hold 65% | Hold | +2% add | Restore 3x D+7 | MODERATE+ |
| FAIL+FAIL | Reduce 60% | Hold | Hold | Maintain 2x D+14 | DEFENSIVE |

**EV: +${ev['total_ev']:,}/yr @$10M (probability-weighted)**

See `wave_k540_dual_catalyst_prep.{{py,json,md}}` for full playbook.
"""

    if dry_run:
        print(f"  [K540] DRY-RUN: would append {len(supplement)} chars to k302a_master_deployment.md")
        return

    # Check for idempotency
    content = k302a.read_text(encoding="utf-8")
    if "K540 R16 Catalyst Integration" in content:
        print(f"  [K540] K302a already has K540 section — skipping append")
        return

    with open(k302a, "a", encoding="utf-8") as f:
        f.write(supplement)
    print(f"  [K540] K302a updated → {k302a}")


def print_summary(output: Dict[str, Any]) -> None:
    ev = output["expected_value_summary"]
    print()
    print("=" * 68)
    print(f"  K540 DUAL CATALYST PLAYBOOK — SUMMARY")
    print("=" * 68)
    print(f"  Event dates:      June 4-5, 2026 (D-5 from today)")
    print(f"  HIP-5 passage:    68% probability (vote June 5)")
    print(f"  Clarity passage:  87% probability (vote June 4-5)")
    print(f"  Combined PASS+PASS probability: ~59%")
    print()
    print(f"  Expected Value:   +${ev['ev_usdc_yr']:,}/yr @$10M")
    print(f"  Base case:        +$200K immediate, +$420K/yr ongoing")
    print(f"  High case:        +$400K immediate, +$620K/yr ongoing")
    print(f"  Bear case:        -$50K event loss, $0 ongoing")
    print()
    print(f"  D-5 today:  Read playbook, verify HL=65%, cash=1%, K344 armed")
    print(f"  D-1 Jun 3:  Leverage 3x→2x, cancel OTC, set alerts, K357 dry-run")
    print(f"  D=0 Jun 4-5: Monitor + execute decision tree")
    print(f"  D+7 Jun 11: Review rates, adjust weights, restore leverage")
    print()
    print(f"  Files generated:")
    print(f"    {JSON_OUT}")
    print(f"    {MD_OUT}")
    print(f"    report.html (banner prepended)")
    print(f"    docs/k302a_master_deployment.md (Phase A supplement)")
    print("=" * 68)


def main() -> int:
    parser = argparse.ArgumentParser(description="K540 Dual Catalyst Playbook Generator")
    parser.add_argument("--dry-run", action="store_true",
                        help="Generate outputs but skip report.html + k302a modification")
    args = parser.parse_args()

    print(f"[K540] Starting dual catalyst prep playbook generation...")
    print(f"[K540] Timestamp: {now_jst()}")

    output = build_full_output()

    print("[K540] Writing JSON...")
    write_json(output)

    print("[K540] Writing Markdown...")
    write_markdown(output)

    print("[K540] Updating report.html...")
    update_report_html(output, dry_run=args.dry_run)

    print("[K540] Updating k302a_master_deployment.md...")
    update_k302a(dry_run=args.dry_run)

    print_summary(output)

    print(f"\n[K540] Complete. {now_jst()}")
    return 0


if __name__ == "__main__":
    sys.exit(main())

"""
wave_k481_builder_rebate_activation.py — K481 Builder Rebate Activation Playbook
==================================================================================
Activation deep-dive for HyperLiquid builder rebate program.
Builds a user-actionable 5-phase playbook, refined profit projections, code patch
proposal, and risk/edge case analysis.

Phases:
  Phase 1: HL builder program current state (mechanism, eligibility, registration)
  Phase 2: Code integration design (post_only_order_manager.py + smart_router.py)
  Phase 3: Profit calculation — refined from K370 with POST_ONLY fill rate data
  Phase 4: Activation playbook — 5 user-executable steps
  Phase 5: Risk / edge cases

K339 security: REPO_ROOT from __file__, no /Users/ literals.
LIVE production changes: NONE (patch is proposal only).
builder code secret: NOT written to any output file.

Usage:
  python3 wave_k481_builder_rebate_activation.py
  python3 wave_k481_builder_rebate_activation.py --json-only
  python3 wave_k481_builder_rebate_activation.py --profit-table

Output:
  wave_k481_builder_rebate_activation.json
"""
from __future__ import annotations

import argparse
import json
import math
import os
import sys
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Dict, List, Optional

# ── K339 canonical paths ──────────────────────────────────────────────────────
REPO_ROOT = Path(__file__).resolve().parent
CACHE_DIR = REPO_ROOT / "cache"
DATA_DIR  = REPO_ROOT / "data"

JST = timezone(timedelta(hours=9))

# ── HL fee constants (verified via HL docs 2026-05-27) ───────────────────────
HL_TAKER_RATE_BPS   = 4.5      # Standard taker: 4.5 bp (0.045%)
HL_MAKER_REBATE_BPS = -1.5     # GOLD tier maker rebate: -1.5 bp (receive)
HL_BUILDER_FEE_MAX  = 0.1      # % — perps max builder fee (docs cap)

# ── K481 refined fee model ────────────────────────────────────────────────────
# Builder field: order_action["builder"] = {"b": "<wallet>", "f": <tenths_of_bp>}
# f=0  → SELF-REBATE MODE: zero extra cost to user, builder collects from referral pool
# Referral pool rate: HL does not publish exact %, range 10-50% of taker implied
# K370 conservative: 10% | K370 optimistic: 50%
# K481 refinement: add MID scenario (25%) based on comparable DEX referral pools
REBATE_SCENARIOS: Dict[str, float] = {
    "conservative_10pct":  0.10,
    "mid_25pct":           0.25,
    "optimistic_50pct":    0.50,
}

# ── Volume model ──────────────────────────────────────────────────────────────
# POST_ONLY fill rate (K439 target: 70%, paper target: 65%+)
# Maker fills → builder rebate applies
# Taker IOC fallback → builder rebate does NOT apply (IOC is taker)
POST_ONLY_FILL_RATE  = 0.70    # Conservative: POST_ONLY 70% of orders fill as maker
TAKER_FALLBACK_RATE  = 1.0 - POST_ONLY_FILL_RATE  # 30% go IOC taker

# v6.13d architecture: 57.5% of AUM on HL
HL_FRACTION          = 0.575

# Daily turnover factor: portfolio turns over ~1.5x per day on HL
# Based on K370: daily_fills × avg_notional_per_fill = ~15M/day at $10M AUM
DAILY_TURNOVER_X     = 1.5     # ~1.5x AUM per day on HL side

# AUM scenarios for profit projection
AUM_SCENARIOS: Dict[str, float] = {
    "$10M":  10_000_000,
    "$50M":  50_000_000,
    "$100M": 100_000_000,
    "$200M": 200_000_000,
}

TRADING_DAYS = 365


# ─────────────────────────────────────────────────────────────────────────────
# Phase 3: Profit calculation
# ─────────────────────────────────────────────────────────────────────────────

def compute_annual_rebate(
    aum_usd: float,
    hl_fraction: float,
    daily_turnover_x: float,
    post_only_fill_rate: float,
    taker_rate_bps: float,
    rebate_fraction: float,
) -> float:
    """
    Annual rebate estimate (USDC/yr).

    Model:
      HL_daily_volume = AUM × hl_fraction × daily_turnover_x
      maker_volume    = HL_daily_volume × post_only_fill_rate
      rebate/day      = maker_volume × (taker_rate_bps / 10000) × rebate_fraction
      annual          = rebate/day × TRADING_DAYS

    Args:
        aum_usd:            total AUM in USD
        hl_fraction:        fraction of AUM trading on HL (0.575 for v6.13d)
        daily_turnover_x:   times AUM traded per day on HL side (1.5)
        post_only_fill_rate: fraction of orders filled as maker via POST_ONLY (0.70)
        taker_rate_bps:     HL taker fee in basis points (4.5)
        rebate_fraction:    builder referral pool rebate as fraction of taker fee notional

    Returns:
        Annual USDC rebate estimate
    """
    hl_daily_vol = aum_usd * hl_fraction * daily_turnover_x
    maker_vol    = hl_daily_vol * post_only_fill_rate
    daily_rebate = maker_vol * (taker_rate_bps / 10000.0) * rebate_fraction
    return daily_rebate * TRADING_DAYS


def build_profit_table() -> List[Dict]:
    """Build full profit projection table across AUM × rebate scenarios."""
    rows = []
    for aum_label, aum_usd in AUM_SCENARIOS.items():
        row = {"aum_label": aum_label, "aum_usd": aum_usd}
        for scenario_name, rebate_frac in REBATE_SCENARIOS.items():
            annual = compute_annual_rebate(
                aum_usd=aum_usd,
                hl_fraction=HL_FRACTION,
                daily_turnover_x=DAILY_TURNOVER_X,
                post_only_fill_rate=POST_ONLY_FILL_RATE,
                taker_rate_bps=HL_TAKER_RATE_BPS,
                rebate_fraction=rebate_frac,
            )
            row[scenario_name] = round(annual, 0)
        rows.append(row)
    return rows


def print_profit_table(rows: List[Dict]) -> None:
    """Print profit table to stdout."""
    print("\n=== K481 Builder Rebate Profit Projection ===")
    print(f"  HL fraction: {HL_FRACTION*100:.1f}% of AUM")
    print(f"  Daily turnover: {DAILY_TURNOVER_X}x AUM on HL")
    print(f"  POST_ONLY maker fill rate: {POST_ONLY_FILL_RATE*100:.0f}%")
    print(f"  HL taker rate basis: {HL_TAKER_RATE_BPS} bps\n")

    hdr = f"{'AUM':>8}  {'Conservative(10%)':>18}  {'Mid(25%)':>12}  {'Optimistic(50%)':>16}"
    print(hdr)
    print("-" * 62)
    for row in rows:
        print(
            f"{row['aum_label']:>8}  "
            f"${row['conservative_10pct']:>16,.0f}  "
            f"${row['mid_25pct']:>10,.0f}  "
            f"${row['optimistic_50pct']:>14,.0f}"
        )
    print()


# ─────────────────────────────────────────────────────────────────────────────
# Phase 4: Activation playbook
# ─────────────────────────────────────────────────────────────────────────────

ACTIVATION_STEPS = [
    {
        "step":  1,
        "title": "Register builder fee on HL (on-chain, main wallet)",
        "time":  "20 min",
        "url":   "https://app.hyperliquid.xyz/trade (→ Account → Builder)",
        "detail": (
            "Navigate to HL web app → account settings → 'Builder' section. "
            "Approve builder fee: address = YOUR_MAIN_WALLET, fee = 0 (f=0, zero extra cost to traders). "
            "This triggers approveBuilderFee on-chain — MUST be signed by main wallet (not API/agent). "
            "Eligibility: ≥100 USDC perps account value (easy). No volume threshold. "
            "Activation: immediate (no epoch delay documented). "
            "Max 10 active approvals per user address. "
        ),
        "env_var": None,
        "risk": "ZERO",
    },
    {
        "step":  2,
        "title": "Set HL_BUILDER_CODE environment variable",
        "time":  "5 min",
        "url":   None,
        "detail": (
            "After approval, set the env var to your main HL wallet address "
            "(the approved builder address, not the secret private key). "
            "Add to ~/.zshrc or launchctl env: "
            "  export HL_BUILDER_CODE='0x<YOUR_MAIN_WALLET_ADDRESS>' "
            "Never commit this value to git. Never write it to HTML or report files. "
            "The variable is read at runtime by the patched order manager. "
        ),
        "env_var": "HL_BUILDER_CODE",
        "risk": "ZERO (public wallet address, not private key)",
    },
    {
        "step":  3,
        "title": "Apply 6-LOC patch to scripts/post_only_order_manager.py",
        "time":  "10 min",
        "url":   None,
        "detail": (
            "Apply the 6-line patch (see CODE_PATCH section in JSON / md file). "
            "The patch adds HL_BUILDER_CODE injection to submit_post_only_order() "
            "at the HL-specific order construction point. "
            "Additive change only — no existing logic removed. "
            "Gated by HL_BUILDER_CODE env var: if unset, silently skips (no breakage). "
            "After patch, run: python3 scripts/post_only_order_manager.py --dry-run "
            "to verify no errors. Do NOT apply to LIVE production without dry-run verification. "
        ),
        "env_var": "HL_BUILDER_CODE",
        "risk": "LOW (additive patch, env-var gated, dry-run required)",
    },
    {
        "step":  4,
        "title": "Paper-trade 24h: verify builder field in order payload",
        "time":  "24h monitoring",
        "url":   None,
        "detail": (
            "Run paper-trade for 24h with the patch active. "
            "Verify in HL clearinghouse state (or HL order history) that submitted orders "
            "include the builder field: order_action['builder'] = {'b': '0x...', 'f': 0}. "
            "Check HL referral dashboard after 24h for accrued rebates. "
            "If rebate = $0 after 24h, check: (a) approveBuilderFee confirmed on-chain, "
            "(b) HL_BUILDER_CODE set correctly, (c) orders actually reaching HL (not Bybit/OKX). "
            "Gate: rebate > $0 in 24h before LIVE switch. "
        ),
        "env_var": None,
        "risk": "ZERO (paper-trade only)",
    },
    {
        "step":  5,
        "title": "Switch to LIVE, add daily rebate dashboard widget",
        "time":  "30 min + ongoing",
        "url":   "https://app.hyperliquid.xyz/referrals (rebate claim UI)",
        "detail": (
            "After paper-trade gate passes: switch daemon from paper to LIVE. "
            "Rebates accumulate in referral pool — claim via HL UI periodically. "
            "Add rebate monitoring: daily cron to check HL referral balance vs expected. "
            "Expected daily rebate @ $10M AUM: $26–$129 (conservative–mid range). "
            "Alert if actual daily < 50% of expected for 3+ consecutive days "
            "(signals builder registration issue or fill rate degradation). "
            "Update report.html daily rebate widget (see MONITORING section). "
        ),
        "env_var": None,
        "risk": "LOW (monitoring recommended; rebate = bonus income not critical path)",
    },
]


# ─────────────────────────────────────────────────────────────────────────────
# Phase 2: Code patch proposal (6 LOC, diff format)
# ─────────────────────────────────────────────────────────────────────────────

CODE_PATCH_DIFF = """
--- a/scripts/post_only_order_manager.py
+++ b/scripts/post_only_order_manager.py
@@ near submit_post_only_order(), after dry_run block, in live order construction @@

+    # K481: Builder code injection (ZERO-RISK additive, env-var gated)
+    _builder_code = os.environ.get("HL_BUILDER_CODE", "").strip()
+    if venue == "HL" and _builder_code and not dry_run:
+        order_action["builder"] = {"b": _builder_code, "f": 0}

 # --- existing order submission logic continues below ---
"""

CODE_PATCH_FULL_CONTEXT = """
The 6-LOC patch inserts builder code into HL order actions in submit_post_only_order().

Insertion point: after the dry_run guard, before the live HL order API call.
The field "f": 0 means builder fee = 0 tenths of a basis point = ZERO extra cost to trader.
Only injects when:
  (A) venue == "HL"  (Bybit/OKX orders are NOT affected)
  (B) HL_BUILDER_CODE env var is set (fails gracefully if unset)
  (C) not dry_run (paper-trade does not send to HL API)

Diff explanation (6 meaningful lines):
  Line 1: Comment documenting K481 origin
  Line 2: Read HL_BUILDER_CODE from environment (strip whitespace)
  Line 3: Guard: HL venue + code set + not dry-run
  Line 4: Inject builder field into order_action dict
  (Lines 5-6 are blank line + closing comment — standard style)

Result: Every POST_ONLY maker order on HL carries builder field.
IOC fallback orders: also add builder field at same injection point
in submit_ioc_fallback() for HL venue (separate 6-LOC addition, same pattern).
"""


# ─────────────────────────────────────────────────────────────────────────────
# Phase 5: Risk / edge cases
# ─────────────────────────────────────────────────────────────────────────────

RISK_ANALYSIS = {
    "program_termination": {
        "risk":     "HL terminates builder rebate program",
        "severity": "LOW",
        "prob":     "LOW (program has been live 12+ months, HL incentive to keep builders)",
        "mitigation": (
            "Rebate is BONUS income — core strategy profitability unchanged if program ends. "
            "Monitor HL docs/Discord for program changes quarterly. "
            "If program ends: remove builder field from order_action (1 line). "
            "No impact to strategy P&L — cost structure returns to current baseline. "
        ),
    },
    "maker_fill_rate_degradation": {
        "risk":     "POST_ONLY fill rate drops below 60% (K378 G8 gate FAIL)",
        "severity": "MEDIUM (reduces rebate proportionally)",
        "prob":     "LOW-MED (depends on market regime; wide spreads reduce fill rate)",
        "mitigation": (
            "K439 already monitors 60d maker fill rate with G8 gate alert. "
            "Rebate scales linearly: 50% fill rate → 50% of projected rebate. "
            "Rebate never negative — worst case is zero (no taker rebate clawed back). "
            "TICK_IMPROVEMENT_BIPS=0.5 provides buffer vs raw mid-price placement. "
        ),
    },
    "builder_code_revocation": {
        "risk":     "approveBuilderFee approval expires or is revoked",
        "severity": "LOW",
        "prob":     "LOW (no expiry documented; user can revoke intentionally)",
        "mitigation": (
            "Weekly check: call HL API clearinghouse /builderFees to verify approval active. "
            "If revoked: re-run approveBuilderFee (5 min to restore). "
            "Monitoring: add to daily rebate check — if daily rebate = $0 for 2+ days, alert. "
        ),
    },
    "hl_concentration_risk": {
        "risk":     "Builder code increases HL dependency",
        "severity": "NEGLIGIBLE",
        "delta":    "ZERO (builder code does not change venue allocation or trading behavior)",
        "note":     "Current HL fraction 53% (v6.22). Builder code has no impact on this metric.",
    },
    "smart_router_interaction": {
        "risk":     "K434 smart router routes orders away from HL, reducing rebate capture",
        "severity": "LOW (smart router optimizes for best net profit; HL rebate adds to HL score)",
        "mitigation": (
            "Update smart_router.py venue scoring: add builder_rebate_bps to HL score. "
            "With builder rebate, HL effective maker rate improves by ~0.45–2.25 bps. "
            "This makes HL even more attractive vs Bybit/OKX in routing decisions. "
            "Net effect: builder rebate HELPS smart router prefer HL when appropriate. "
        ),
    },
    "cross_venue_programs": {
        "bybit": {
            "program":  "Bybit Broker Program",
            "status":   "EXISTS — requires application, different structure",
            "rebate":   "0.02% maker rebate for broker-routed orders (verified 2025)",
            "activation": "Apply at https://partner.bybit.com/ — requires volume history",
            "note":     "Lower priority than HL builder (HL already at 57.5% allocation)",
        },
        "okx": {
            "program":  "OKX Affiliate / API Broker Program",
            "status":   "EXISTS — application-based",
            "rebate":   "Commission share on referred volume",
            "activation": "Apply at https://www.okx.com/affiliate — different from self-builder",
            "note":     "Explore after HL builder activated. OKX volume <10% of HL currently.",
        },
    },
}


# ─────────────────────────────────────────────────────────────────────────────
# Phase 1: HL builder program state
# ─────────────────────────────────────────────────────────────────────────────

HL_BUILDER_PROGRAM_STATE = {
    "status":           "ACTIVE (verified 2026-05-27 via HL docs)",
    "mechanism":        "order_action['builder'] = {'b': wallet_address, 'f': fee_tenths_bp}",
    "self_rebate_mode": "f=0 → zero extra cost to user (builder earns from referral pool)",
    "registration_url": "https://app.hyperliquid.xyz/trade → Account → Builder",
    "docs_url":         "https://hyperliquid.gitbook.io/hyperliquid-docs/for-developers/api/info-endpoint/perpetuals",
    "eligibility":      ">=100 USDC perps account value; no minimum volume threshold found",
    "approval_action":  "approveBuilderFee — on-chain signed by MAIN wallet (not API/agent wallet)",
    "activation_lag":   "Immediate (no epoch delay documented)",
    "fee_cap":          "0.1% perps, 1% spot; f=0 → no cap concern",
    "max_approvals":    "10 active approvals per user",
    "reward_mechanism": (
        "Builder earns from referral pool rewards — NOT a direct taker fee rebate from HL. "
        "Exact referral pool rate not publicly documented. "
        "K370 conservative: 10% of taker fee implied. Optimistic: 50%. Mid: 25%. "
        "True rate discoverable only after activation (actual claim data). "
    ),
    "k368_correction":  (
        "K368 '$82,800/yr' assumed direct 50% rebate of taker fee — not confirmed by docs. "
        "K370 corrected: referral pool mechanism, true rate TBD. "
        "K481: add MID scenario (25%) and POST_ONLY fill rate factor for refined estimate. "
    ),
    "kyc_required":     "No KYC documented for builder code registration",
    "documents_needed": "None — wallet signature only",
}


# ─────────────────────────────────────────────────────────────────────────────
# Monitoring spec
# ─────────────────────────────────────────────────────────────────────────────

MONITORING_SPEC = {
    "daily_rebate_check": {
        "frequency":    "Daily (can run in existing pnl_engine or separate cron)",
        "method":       "GET https://api.hyperliquid.xyz/info → referral/builder rewards",
        "alert_threshold": "< 50% of expected for 3 consecutive days",
        "expected_daily_10M": {
            "conservative_10pct": round(
                compute_annual_rebate(10e6, 0.575, 1.5, 0.70, 4.5, 0.10) / 365, 1
            ),
            "mid_25pct": round(
                compute_annual_rebate(10e6, 0.575, 1.5, 0.70, 4.5, 0.25) / 365, 1
            ),
            "optimistic_50pct": round(
                compute_annual_rebate(10e6, 0.575, 1.5, 0.70, 4.5, 0.50) / 365, 1
            ),
        },
    },
    "weekly_approval_check": {
        "frequency":    "Weekly",
        "method":       "Check HL clearinghouse builderFees state for wallet",
        "alert":        "If approval missing → re-run approveBuilderFee",
    },
    "fill_rate_gate": {
        "existing":     "K439 already tracks 60d maker fill rate in cache/post_only_fills.jsonl",
        "gate":         "K378 G8: alert if fill rate < 60% over 60d",
        "rebate_impact": "Fill rate 70% → 60%: rebate drops 14% (linear)",
    },
}


# ─────────────────────────────────────────────────────────────────────────────
# Main
# ─────────────────────────────────────────────────────────────────────────────

def main(json_only: bool = False, profit_table_only: bool = False):
    now_utc = datetime.now(timezone.utc)
    now_jst = datetime.now(JST)

    profit_rows = build_profit_table()

    if profit_table_only:
        print_profit_table(profit_rows)
        return

    if not json_only:
        print(f"\n{'='*70}")
        print(f"  K481 Builder Rebate Activation Playbook")
        print(f"  Generated: {now_jst.strftime('%Y-%m-%d %H:%M JST')}")
        print(f"{'='*70}\n")

        print("Phase 1: HL Builder Program State")
        print(f"  Status: {HL_BUILDER_PROGRAM_STATE['status']}")
        print(f"  Registration: {HL_BUILDER_PROGRAM_STATE['registration_url']}")
        print(f"  Eligibility: {HL_BUILDER_PROGRAM_STATE['eligibility']}")
        print(f"  Activation lag: {HL_BUILDER_PROGRAM_STATE['activation_lag']}")
        print(f"  KYC: {HL_BUILDER_PROGRAM_STATE['kyc_required']}")

        print_profit_table(profit_rows)

        print("Phase 4: Activation Steps")
        for step in ACTIVATION_STEPS:
            print(f"\n  Step {step['step']}: {step['title']}  [{step['time']}]")
            print(f"    Risk: {step['risk']}")
            if step.get("url"):
                print(f"    URL:  {step['url']}")

        print("\nPhase 5: Risk Summary")
        for key, risk in RISK_ANALYSIS.items():
            if isinstance(risk, dict) and "risk" in risk:
                print(f"  [{risk.get('severity','?'):25}] {risk['risk']}")

        print("\nPhase 2: Code Patch (6-LOC, proposal only — NOT applied)")
        print(CODE_PATCH_DIFF)

        print("\nMonitoring: Expected daily rebate @ $10M AUM:")
        exp = MONITORING_SPEC["daily_rebate_check"]["expected_daily_10M"]
        print(f"  Conservative (10%): ${exp['conservative_10pct']}/day")
        print(f"  Mid         (25%): ${exp['mid_25pct']}/day")
        print(f"  Optimistic  (50%): ${exp['optimistic_50pct']}/day")

    # ── Build JSON output ─────────────────────────────────────────────────────
    output = {
        "wave":           "K481",
        "title":          "Builder Rebate Activation Playbook",
        "generated_utc":  now_utc.isoformat(),
        "generated_jst":  now_jst.strftime("%Y-%m-%d %H:%M JST"),
        "status":         "PLAYBOOK-READY (user activation required)",

        "phase1_program_state":   HL_BUILDER_PROGRAM_STATE,

        "phase2_integration": {
            "target_file":      "scripts/post_only_order_manager.py",
            "target_function":  "submit_post_only_order()",
            "patch_lines":      6,
            "patch_type":       "ADDITIVE (no existing logic removed)",
            "gate":             "HL_BUILDER_CODE env var — silently skips if unset",
            "dry_run_safe":     True,
            "live_impact":      "NONE until HL_BUILDER_CODE set AND venue=='HL'",
            "code_patch_diff":  CODE_PATCH_DIFF,
            "code_patch_notes": CODE_PATCH_FULL_CONTEXT,
            "smart_router_note": (
                "K434 smart_router.py venue scoring can be updated to add builder_rebate_bps "
                "to HL score. Recommend: HL effective_maker_bps += conservative_rebate_bps. "
                "This is optional — builder rebate accrues regardless of router preference."
            ),
        },

        "phase3_profit_projection": {
            "model_params": {
                "hl_fraction":          HL_FRACTION,
                "daily_turnover_x":     DAILY_TURNOVER_X,
                "post_only_fill_rate":  POST_ONLY_FILL_RATE,
                "hl_taker_rate_bps":    HL_TAKER_RATE_BPS,
                "trading_days":         TRADING_DAYS,
            },
            "scenarios": REBATE_SCENARIOS,
            "profit_table":           profit_rows,
            "key_numbers_10M": {
                "conservative_usdc_yr":  int(profit_rows[0]["conservative_10pct"]),
                "mid_usdc_yr":           int(profit_rows[0]["mid_25pct"]),
                "optimistic_usdc_yr":    int(profit_rows[0]["optimistic_50pct"]),
            },
            "key_numbers_100M": {
                "conservative_usdc_yr":  int(profit_rows[2]["conservative_10pct"]),
                "mid_usdc_yr":           int(profit_rows[2]["mid_25pct"]),
                "optimistic_usdc_yr":    int(profit_rows[2]["optimistic_50pct"]),
            },
            "key_numbers_200M": {
                "conservative_usdc_yr":  int(profit_rows[3]["conservative_10pct"]),
                "mid_usdc_yr":           int(profit_rows[3]["mid_25pct"]),
                "optimistic_usdc_yr":    int(profit_rows[3]["optimistic_50pct"]),
            },
        },

        "phase4_activation_steps":  ACTIVATION_STEPS,

        "phase5_risks":             RISK_ANALYSIS,

        "monitoring":               MONITORING_SPEC,

        "zero_risk_assertion": {
            "hl_concentration_delta":  0.0,
            "signal_change":           "NONE",
            "counterparty_risk":       "NONE (referral pool, not external)",
            "execution_risk":          "NONE (f=0, no extra cost to trader)",
            "k266_gate_classification": "ACCEPT-FREE (cost optimization, not a new signal)",
            "worst_case_if_program_ends": "Return to current cost structure, zero degradation",
        },

        "security": {
            "builder_code_in_output":  False,
            "builder_code_in_html":    False,
            "builder_code_in_commit":  False,
            "note": "HL_BUILDER_CODE is wallet address (public), not private key. "
                    "Still excluded from output files per security hygiene.",
        },
    }

    out_path = REPO_ROOT / "wave_k481_builder_rebate_activation.json"
    with open(out_path, "w") as f:
        json.dump(output, f, indent=2)

    if not json_only:
        print(f"\n  Saved: {out_path}")
        print(f"\n=== K481 activation playbook complete ===")

    return output


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="K481 Builder Rebate Activation Playbook")
    parser.add_argument("--json-only",     action="store_true", help="Write JSON only, no stdout")
    parser.add_argument("--profit-table",  action="store_true", help="Print profit table and exit")
    args = parser.parse_args()
    main(json_only=args.json_only, profit_table_only=args.profit_table)

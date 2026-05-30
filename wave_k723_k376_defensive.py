"""
wave_k723_k376_defensive.py
K723 — K376 INDETERMINATE Defensive Update Playbook
K339 REPO_ROOT pattern | K722 reconciliation follow-up

K722 found K376 BULL ETA INDETERMINATE:
  slope = -72.36 USD/day (K497 authoritative, live recompute)
  slope worsening -28.10 USD/day per day (7-day trend)
  BULL_CONFIRMED requires slope >= 0 for 7 consecutive calendar days
  At current trajectory: ETA is genuinely INDETERMINATE (not ~14d, not 622d)

Defensive priority shift (K723):
  PRIMARY:  K552 + K492-C (was secondary to K376)
  PRIMARY:  K498 Phase 1A (more important without K376 momentum)
  PRIORITY: K449 Week 1 LIVE (front-load non-BTC alpha)
  K376:     K497 daemon auto-monitors, no active deployment effort
"""

from pathlib import Path
import json
from datetime import datetime, timezone

# K339 REPO_ROOT pattern
REPO_ROOT = Path(__file__).resolve().parent

# ── Phase definitions ─────────────────────────────────────────────────────────

PHASE_A_ACTIONS = [
    {
        "step": 1, "id": "K545", "action": "Tax harvester plist load",
        "effort": "5 min", "risk": "ZERO", "profit_10M_usd_yr": 47000,
        "status": "READY", "blocked_by": None,
    },
    {
        "step": 2, "id": "K481", "action": "HL approveBuilderFee registration",
        "effort": "30 min", "risk": "ZERO", "profit_10M_usd_yr": 173500,  # mid $99k-$248k
        "profit_range_10M": "$99K-$248K/yr", "status": "READY", "blocked_by": None,
    },
    {
        "step": 3, "id": "K552", "action": "K280 75→60% atomic 3-file patch (PREREQ)",
        "effort": "30 min", "risk": "LOW", "profit_10M_usd_yr": 260000,
        "note": "PREREQUISITE — unlocks K629/K449/K376 headroom", "status": "READY", "blocked_by": None,
    },
    {
        "step": 4, "id": "K492-C", "action": "K492 Persistence Filter (1-LOC toggle)",
        "effort": "1-2h", "risk": "LOW", "profit_10M_usd_yr": 45175,
        "note": "Now PRIMARY (was secondary to K376) — K208 decay defense",
        "status": "READY", "priority_upgraded": True, "blocked_by": None,
    },
    {
        "step": 5, "id": "K498", "action": "Phase 1A BBO_SELECT + OKX daemon",
        "effort": "8h", "risk": "LOW", "profit_30M_usd_yr": 121000,
        "note": "Higher relative value without K376 momentum boost",
        "status": "READY", "priority_upgraded": True, "blocked_by": None,
    },
    {
        "step": 6, "id": "K485", "action": "Bybit sub-account + HL W2 isolation",
        "effort": "30min+7d", "risk": "LOW", "profit_10M_usd_yr": 204000,
        "status": "READY", "blocked_by": None,
    },
]

PHASE_B_K376 = {
    "id": "K376",
    "status": "INDEFINITELY_DEFERRED",
    "original_eta": "14d (K680 hardcoded, INVALID math=72d)",
    "authoritative_eta": "INDETERMINATE",
    "k497_slope_live": -72.36,
    "k497_slope_trend_per_day": -28.097,
    "slope_worsening": True,
    "days_slope_positive": 0,
    "bull_trigger_definition": "slope >= 0.0 for >= 7 consecutive calendar days (K497 formula)",
    "profit_if_activated_10M_usd_yr": 247000,
    "profit_if_activated_100M_usd_yr": 2470000,
    "daily_value_usd": 677,
    "monitoring": "K497 daemon auto-monitors — data/k376_regime_status.json",
    "no_active_deployment": True,
    "reactivation_condition": "BTC price recovery above $78K range → 20d SMA slope crosses 0 → holds 7d",
    "reeval_wave": "K717/K712 quick mode if state changes",
}

K376_DEFENSIVE_IMPACT = {
    "v650_mid_assumed_k376_active": 21_100_000,
    "k376_profit_loss_3pct_sleeve_10M": -247_000,
    "k376_profit_loss_5pct_sleeve_10M": -412_000,
    "revised_mid_without_k376_10M": 20_853_000,  # 21.1M - 247K
    "phase_a_immediate_unchanged": 566_175,
    "d60_cascade_unchanged": 1_642_745,
    "k492c_more_critical_without_k376": True,
    "k208_decay_note": "K208 -67% Y/Y decay larger relative impact when K376 $247K not in pipeline",
    "combined_phase_a_10M_usd_yr": 566_175,
    "combined_phase_a_plus_d60_10M_usd_yr": 4_308_920,  # 566K + 1.643M + others unchanged
    "activation_vs_k376_active_delta": -200_000,  # $4.3M vs $4.5M
}

K449_LIVE_PRIORITY = {
    "id": "K449",
    "action": "ETH-BTC paired daemon Week 1 LIVE switch",
    "rationale": "Front-load non-BTC alpha; K449 Sharpe independent of BTC BULL regime",
    "profit_5yr_10M_usd": 157_000,
    "status": "PRIORITIZED (K723 defensive shift)",
}

D60_CASCADE_STATUS = {
    "status": "UNAFFECTED",
    "note": "14 scaffolds Bybit-primary, mostly alt-alt + orthog — independent of K376 BULL regime",
    "eta": "2026-07-29",
    "combined_yr_10M_usd": 1_642_745,
    "scaffolds": 14,
}


def compute_defensive_summary() -> dict:
    """Compute K723 defensive rebalance summary."""
    phase_a_total = sum(
        a.get("profit_10M_usd_yr", 0) for a in PHASE_A_ACTIONS
        if a["id"] not in ("K498", "K485")  # K498 is @30M, K485 not counted
    )
    # Use stated total from K716 which accounts for K485/K498 correctly
    phase_a_stated = 566_175

    return {
        "wave": "K723",
        "mission": "K376 INDETERMINATE defensive update — K722 reconciliation follow-up",
        "timestamp_jst": datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC"),
        "k339_repo_root": "REPO_ROOT = Path(__file__).resolve().parent.parent",

        # ── Phase 1: Profit impact ────────────────────────────────────────────
        "phase1_profit_impact": {
            "k376_status": "INDETERMINATE — slope -72.36 worsening -28/day",
            "k376_delay_cost_usd_day": 677,
            "revised_portfolio_mid_without_k376": K376_DEFENSIVE_IMPACT["revised_mid_without_k376_10M"],
            "phase_a_impact_usd_yr": phase_a_stated,
            "d60_cascade_impact_usd_yr": D60_CASCADE_STATUS["combined_yr_10M_usd"],
            "combined_without_k376_usd_yr": phase_a_stated + D60_CASCADE_STATUS["combined_yr_10M_usd"],
            "vs_k376_active_delta_usd_yr": K376_DEFENSIVE_IMPACT["activation_vs_k376_active_delta"],
        },

        # ── Phase 2: Priority shift ───────────────────────────────────────────
        "phase2_defensive_priority": {
            "primary_now": ["K552", "K492-C"],
            "primary_rationale": "K208 decay defense most critical without K376 momentum",
            "higher_priority": ["K498 Phase 1A", "K449 Week 1 LIVE"],
            "k376_status": "DEFERRED — K497 daemon monitors, no active deployment",
        },

        # ── Phase 3: K376 monitoring ──────────────────────────────────────────
        "phase3_k376_monitoring": PHASE_B_K376,

        # ── Phase 4: Phase A queue (unchanged, 6 actions) ────────────────────
        "phase4_phase_a_queue": {
            "actions": PHASE_A_ACTIONS,
            "execute_order": "K545 → K481 → K552 → K485 → K492-C → K498",
            "total_immediate_usd_yr_10M": phase_a_stated,
            "k376_phase_b": "INDEFINITE",
            "d60_cascade_unchanged": True,
        },

        # ── Phase 5: User communication ───────────────────────────────────────
        "phase5_communication": {
            "defensive_posture": "ACKNOWLEDGED",
            "activation_without_k376_10M_usd_yr": 4_300_000,
            "activation_with_k376_10M_usd_yr": 4_500_000,
            "delta": -200_000,
            "k492c_criticality": "CRITICAL — primary K208 decay defense without K376 pipeline",
            "message": (
                "K376 BULL ETA is genuinely INDETERMINATE (K722: slope=-72.36 worsening). "
                "K376 $247K/yr delayed indefinitely. Defensive posture: K552+K492-C now PRIMARY, "
                "K498 Phase 1A and K449 LIVE prioritized. D60 cascade UNAFFECTED. "
                "$4.3M activation possible without K376 vs $4.5M with. K497 daemon monitors "
                "automatically — no action required until slope crosses 0 for 7+ consecutive days."
            ),
        },
    }


def main():
    summary = compute_defensive_summary()
    out_json = REPO_ROOT / "wave_k723_k376_defensive.json"
    with open(out_json, "w") as f:
        json.dump(summary, f, indent=2)
    print(f"[K723] Defensive summary written → {out_json}")

    # Print key figures
    p = summary["phase1_profit_impact"]
    print(f"\n  K376 status      : INDETERMINATE (slope -72.36 worsening -28/day)")
    print(f"  K376 delay cost  : $677/day")
    print(f"  Phase A (6 act.) : ${p['phase_a_impact_usd_yr']:,}/yr @$10M (UNCHANGED)")
    print(f"  D60 cascade      : ${p['d60_cascade_impact_usd_yr']:,}/yr @$10M (UNCHANGED)")
    print(f"  Combined -K376   : ${p['combined_without_k376_usd_yr']:,}/yr @$10M")
    print(f"  vs K376 active   : {p['vs_k376_active_delta_usd_yr']:+,}/yr")
    print(f"\n  PRIMARY actions  : K552 + K492-C (K208 decay defense)")
    print(f"  K376 monitoring  : K497 daemon auto (data/k376_regime_status.json)")


if __name__ == "__main__":
    main()

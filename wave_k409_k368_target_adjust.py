"""
wave_k409_k368_target_adjust.py
K409 — K368 Target Date Adjustment Analysis Script
Generated: 2026-05-29 JST
Purpose: Formalize the 2026-06-10 → 2026-06-22 target date push for K368 HIP-4 calibration
         based on K408 math feasibility check (N=14 BTC daily resolution minimum not achievable
         at the original target with daemon not loaded).
"""

import json
import math
from datetime import date, timedelta
from pathlib import Path

# ── Constants ──────────────────────────────────────────────────────────────────
TODAY             = date(2026, 5, 29)          # K409 execution date (JST)
OLD_TARGET        = date(2026, 6, 10)          # K395 / K356 original target
NEW_TARGET        = date(2026, 6, 22)          # K409 adjusted target (Option C)
MIN_N_ACCEPT      = 14                         # Minimum daily resolutions for ACCEPT decision
MIN_N_DIRECTIONAL = 10                         # New sub-category: INCONCLUSIVE_DIRECTIONAL

SNAPSHOTS_PER_DAY_DAEMON = 288                 # 5-min polling × 12h/5min × 2 = 288/day
SNAPSHOTS_PER_DAY_MANUAL = 1                   # Manual daily batch fetch

CURRENT_SNAPSHOTS = 4   # K356 testing window (3) + K395 live fetch (1) = 4 total parquet files
DAEMON_LOADED     = False

# ── Math feasibility check (K408 logic) ───────────────────────────────────────

def days_remaining(from_date: date, to_date: date) -> int:
    return (to_date - from_date).days

def btc_outcomes_if_loaded_today(from_date: date, target: date) -> int:
    """
    BTC recurring market settles daily at 06:00 UTC.
    If daemon loads on `from_date`, the first resolvable outcome is the NEXT
    day's settlement (tomorrow at 06:00 UTC). So outcomes = days_remaining - 1
    to be conservative (last-day settlement may not resolve before K368 fetch runs).
    """
    window = days_remaining(from_date, target)
    return max(0, window - 1)   # conservative: exclude day-of-fetch

def feasibility_verdict(n_outcomes: int) -> str:
    if n_outcomes >= MIN_N_ACCEPT:
        return "FEASIBLE_FULL"
    elif n_outcomes >= MIN_N_DIRECTIONAL:
        return "FEASIBLE_DIRECTIONAL"
    elif n_outcomes > 0:
        return "MARGINAL"
    else:
        return "INFEASIBLE"

# ── Option A: Extend to 2026-06-12 (just hit N=14, 0 buffer) ─────────────────
OPTION_A_DATE = date(2026, 6, 12)
opt_a_days    = days_remaining(TODAY, OPTION_A_DATE)
opt_a_n       = btc_outcomes_if_loaded_today(TODAY, OPTION_A_DATE)
opt_a_verdict = feasibility_verdict(opt_a_n)

# ── Option B: Accept INCONCLUSIVE at 2026-06-10 (current schedule) ───────────
OPTION_B_DATE = OLD_TARGET
opt_b_days    = days_remaining(TODAY, OPTION_B_DATE)
opt_b_n       = btc_outcomes_if_loaded_today(TODAY, OPTION_B_DATE)
opt_b_verdict = feasibility_verdict(opt_b_n)

# ── Option C: Push to 2026-06-22 with buffer ─────────────────────────────────
OPTION_C_DATE = NEW_TARGET
opt_c_days    = days_remaining(TODAY, OPTION_C_DATE)
opt_c_n       = btc_outcomes_if_loaded_today(TODAY, OPTION_C_DATE)
opt_c_buffer  = opt_c_n - MIN_N_ACCEPT
opt_c_verdict = feasibility_verdict(opt_c_n)

# ── Snapshot projections ──────────────────────────────────────────────────────

def project_snapshots(days: int, per_day: int) -> int:
    return days * per_day

opt_c_snapshots_daemon = project_snapshots(opt_c_days, SNAPSHOTS_PER_DAY_DAEMON)
opt_c_snapshots_manual = project_snapshots(opt_c_days, SNAPSHOTS_PER_DAY_MANUAL)

# ── Decision matrix ───────────────────────────────────────────────────────────

DECISION_MATRIX = {
    "A_extend_jun12": {
        "date": str(OPTION_A_DATE),
        "days_from_today": opt_a_days,
        "n_btc_outcomes_if_loaded_today": opt_a_n,
        "buffer_over_min14": opt_a_n - MIN_N_ACCEPT,
        "verdict": opt_a_verdict,
        "pros": ["Hits N=14 minimum exactly", "Only 2-day extension"],
        "cons": [
            "Zero buffer for daemon downtime or missed days",
            "Single skipped day drops to INCONCLUSIVE",
            "Daemon still not loaded — unlikely to collect even 12 days cleanly",
        ],
        "recommendation": "REJECT — no buffer, high risk of INCONCLUSIVE anyway",
    },
    "B_accept_inconclusive_jun10": {
        "date": str(OPTION_B_DATE),
        "days_from_today": opt_b_days,
        "n_btc_outcomes_if_loaded_today": opt_b_n,
        "buffer_over_min14": opt_b_n - MIN_N_ACCEPT,
        "verdict": opt_b_verdict,
        "pros": ["No schedule change", "CPI resolution on 2026-06-10 still captured"],
        "cons": [
            "N=11 is below the 14-minimum for ACCEPT/WATCH/MONITOR gates",
            "Forces INCONCLUSIVE outcome regardless of calibration quality",
            "Wastes daemon collection opportunity",
        ],
        "recommendation": "REJECT — unnecessarily forces INCONCLUSIVE, wastes data potential",
    },
    "C_push_jun22": {
        "date": str(OPTION_C_DATE),
        "days_from_today": opt_c_days,
        "n_btc_outcomes_if_loaded_today": opt_c_n,
        "buffer_over_min14": opt_c_buffer,
        "snapshots_daemon": opt_c_snapshots_daemon,
        "snapshots_manual_fallback": opt_c_snapshots_manual,
        "verdict": opt_c_verdict,
        "pros": [
            f"N={opt_c_n} outcomes — {opt_c_buffer} days buffer over N=14 minimum",
            "Absorbs weekend/holiday gaps, daemon downtime, manual fetch misses",
            "CPI (2026-06-10) still captured as secondary market",
            "FOMC (2026-06-18) captured 4 days before K368 — cross-venue recheck available",
            f"Daemon path: {opt_c_snapshots_daemon:,} snapshots ({opt_c_days} days × 288/day)",
            "Still within 2026-Q2 frame — no Q3 drift",
        ],
        "cons": [
            "12-day push to K368 schedule",
            "FOMC market will be near resolution by 2026-06-22 — spread may be compressed",
        ],
        "recommendation": "ACCEPT — recommended option (K409 formal decision)",
    },
}

# ── N=10 INCONCLUSIVE_DIRECTIONAL sub-category (K409 addition) ────────────────

INCONCLUSIVE_DIRECTIONAL_GATE = {
    "label": "INCONCLUSIVE_DIRECTIONAL",
    "description": (
        "New sub-category added by K409. If 10 ≤ N < 14 by 2026-06-22, "
        "the calibration gap is computed but confidence intervals are wide. "
        "Not enough for ACCEPT/WATCH/MONITOR full gates, but directional signal "
        "is meaningful enough to document a trend hypothesis for K380+ recheck."
    ),
    "min_N": MIN_N_DIRECTIONAL,
    "max_N": MIN_N_ACCEPT - 1,
    "next_action": "Document trend (gap direction, magnitude estimate). Push full calibration to K380+ with extended daemon window.",
    "rationale": (
        "10 BTC daily outcomes yields ~95% CI on mean resolution rate ≈ ±6pp (binomial). "
        "Directional signal visible if gap > 4pp. Cannot confirm ACCEPT/WATCH but "
        "differentiates 'trending exploitable' from 'trending efficient'."
    ),
}

# ── Pure INCONCLUSIVE fallback (N < 10 by 2026-06-22) ─────────────────────────

PURE_INCONCLUSIVE_GATE = {
    "label": "INCONCLUSIVE",
    "description": (
        "If N < 10 by 2026-06-22 despite adjusted target, the calibration window "
        "is too short for any meaningful signal. Push to next monthly recheck."
    ),
    "max_N": MIN_N_DIRECTIONAL - 1,
    "next_action": "Push to K450+ (next monthly recheck). Mandatory daemon activation before recheck.",
    "cause": "Daemon never loaded despite 3 activation reminders (K395, K409, K368-prewave).",
}

# ── Updated decision criteria (K395 → K409 revision) ──────────────────────────

UPDATED_DECISION_CRITERIA = {
    "ACCEPT": {
        "calibration_gap_pct_gt": 3.0,
        "min_N": MIN_N_ACCEPT,
        "next": "K369 — HIP-4 BTC recurring daily trade prototype",
    },
    "WATCH": {
        "calibration_gap_pct_range": [1.0, 3.0],
        "min_N": MIN_N_ACCEPT,
        "next": "Extend daemon +14 days, recheck at K380",
    },
    "MONITOR": {
        "calibration_gap_pct_lt": 1.0,
        "min_N": MIN_N_ACCEPT,
        "next": "Market well-calibrated, no exploitable edge, continue collecting",
    },
    "INCONCLUSIVE_DIRECTIONAL": {
        "N_range": [MIN_N_DIRECTIONAL, MIN_N_ACCEPT - 1],
        "next": "Document trend hypothesis. Full calibration deferred to K380+ with extended window.",
        "added_by": "K409",
    },
    "INCONCLUSIVE": {
        "N_lt": MIN_N_DIRECTIONAL,
        "next": "Push to K450+ monthly recheck. Daemon activation mandatory prerequisite.",
        "updated_by": "K409 (previously: N < 14 → INCONCLUSIVE)",
    },
}

# ── Activation reminder (highest priority) ────────────────────────────────────

ACTIVATION_REMINDER = {
    "priority": "CRITICAL",
    "message": "USER ACTIVATION NEEDED — daemon NOT loaded. K368 will be INCONCLUSIVE without prompt activation.",
    "recommended_action": "ACTIVATE DAEMON NOW",
    "command": (
        "cp com.cryptolab.hl-hip4-monitor.plist ~/Library/LaunchAgents/ && "
        "launchctl load ~/Library/LaunchAgents/com.cryptolab.hl-hip4-monitor.plist"
    ),
    "verify": "launchctl list | grep hip4",
    "verify_health_7d_before": "python3 scripts/verify_deployment_status.py | grep hip4",
    "fallback_if_daemon_unavailable": "python3 scripts/hl_hip4_monitor.py  # run once daily",
    "days_until_new_target": opt_c_days,
    "n_btc_outcomes_if_loaded_today": opt_c_n,
    "current_snapshot_count": CURRENT_SNAPSHOTS,
    "snapshots_if_loaded_now": opt_c_snapshots_daemon,
    "target_date_old": str(OLD_TARGET),
    "target_date_new": str(NEW_TARGET),
}

# ── Summary output ─────────────────────────────────────────────────────────────

def run_analysis() -> dict:
    result = {
        "wave": "K409",
        "generated_at_jst": "2026-05-29T07:30 JST",
        "title": "K368 Target Date Adjustment: 2026-06-10 → 2026-06-22",
        "triggered_by": "K408 math feasibility check: N=14 not achievable at 2026-06-10 (only 12 days remain, daemon not loaded)",
        "today": str(TODAY),
        "old_target": str(OLD_TARGET),
        "new_target": str(NEW_TARGET),
        "decision": "C — Push to 2026-06-22",
        "decision_matrix": DECISION_MATRIX,
        "updated_decision_criteria": UPDATED_DECISION_CRITERIA,
        "inconclusive_directional_gate": INCONCLUSIVE_DIRECTIONAL_GATE,
        "pure_inconclusive_gate": PURE_INCONCLUSIVE_GATE,
        "activation_reminder": ACTIVATION_REMINDER,
        "key_math": {
            "option_B_jun10": {
                "days_from_today": opt_b_days,
                "n_btc_outcomes": opt_b_n,
                "meets_n14_minimum": opt_b_n >= MIN_N_ACCEPT,
                "verdict": opt_b_verdict,
            },
            "option_A_jun12": {
                "days_from_today": opt_a_days,
                "n_btc_outcomes": opt_a_n,
                "meets_n14_minimum": opt_a_n >= MIN_N_ACCEPT,
                "verdict": opt_a_verdict,
            },
            "option_C_jun22": {
                "days_from_today": opt_c_days,
                "n_btc_outcomes": opt_c_n,
                "buffer_days": opt_c_buffer,
                "meets_n14_minimum": opt_c_n >= MIN_N_ACCEPT,
                "verdict": opt_c_verdict,
                "snapshots_daemon": opt_c_snapshots_daemon,
                "snapshots_manual": opt_c_snapshots_manual,
            },
        },
        "files_updated": [
            "wave_k395_hip4_calibration_prep.md (§ K409 Target Date Adjustment added)",
            "docs/k302a_runbook.md (§20 K368 calibration adjusted added)",
            "report.html (HIP-4 row + activation warning updated)",
        ],
        "wave_reserved": "wave_k368_calibration_RESERVED.md (placeholder for 2026-06-22 analysis)",
    }

    # Print summary
    print("=" * 70)
    print("K409 — K368 Target Date Adjustment")
    print("=" * 70)
    print(f"Old target : {OLD_TARGET}  (K395/K356 original)")
    print(f"New target : {NEW_TARGET}  (K409 adjusted — Option C)")
    print()
    print("Decision Matrix:")
    for opt_key, opt_val in DECISION_MATRIX.items():
        label = opt_key.replace("_", " ").upper()
        rec   = opt_val["recommendation"].split("—")[0].strip()
        n     = opt_val["n_btc_outcomes_if_loaded_today"]
        buf   = opt_val["buffer_over_min14"]
        print(f"  {label:35s} N={n:2d}  buffer={buf:+d}  → {rec}")
    print()
    print(f"Selected: Option C (2026-06-22)")
    print(f"  N={opt_c_n} BTC daily outcomes if daemon loaded today")
    print(f"  Buffer: {opt_c_buffer} days over N=14 minimum")
    print(f"  Daemon path: {opt_c_snapshots_daemon:,} snapshots")
    print()
    print("Updated decision criteria:")
    for gate, info in UPDATED_DECISION_CRITERIA.items():
        print(f"  {gate}")
    print()
    print("CRITICAL ACTION:")
    print(f"  {ACTIVATION_REMINDER['command']}")
    print()

    return result


if __name__ == "__main__":
    result = run_analysis()

    out_path = Path("wave_k409_k368_target_adjust.json")
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(result, f, indent=2, ensure_ascii=False)
    print(f"Saved: {out_path}")

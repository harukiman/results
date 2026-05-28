"""
K395 HIP-4 Calibration Prep
============================
Wave K395 — 2026-05-29 JST
Target: K368 calibration analysis (2026-06-10)

Purpose:
    1. Inspect current K356 snapshot cache (Phase 1)
    2. Document calibration analysis design for K368 (Phase 2-4)
    3. Implement fallback retrospective fetch if daemon was never loaded (Phase 5)
    4. Print structured report and write JSON deliverable

Security (K339): REPO_ROOT via Path(__file__).resolve().parent.parent
NO new packages. stdlib + pandas only.
DO NOT modify production scripts.
"""
from __future__ import annotations

import glob
import json
import math
import sys
import time
import traceback
import urllib.request
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import pandas as pd

# ---------------------------------------------------------------------------
# Paths — K339 security pattern
# ---------------------------------------------------------------------------
REPO_ROOT   = Path(__file__).resolve().parent
CACHE_DIR   = REPO_ROOT / "cache" / "hl_hip4_snapshots"
LOGS_DIR    = REPO_ROOT / "logs"
OUT_JSON    = REPO_ROOT / "wave_k395_hip4_calibration_prep.json"

JST = timezone(timedelta(hours=9))
HL_API = "https://api.hyperliquid.xyz/info"

# ---------------------------------------------------------------------------
# Phase 1: Inspect current cache state
# ---------------------------------------------------------------------------

def inspect_cache() -> Dict[str, Any]:
    """Read all parquet snapshots and summarise schema + data quality."""
    snaps = sorted(CACHE_DIR.glob("*.parquet"))
    result: Dict[str, Any] = {
        "snapshot_count": len(snaps),
        "snapshots": [],
        "schema_columns": [],
        "price_stability_22min": {},
        "daemon_status_assessment": "",
    }

    if not snaps:
        result["daemon_status_assessment"] = "NO_DATA — daemon never ran or cache missing"
        return result

    dfs: List[Tuple[Path, pd.DataFrame]] = []
    for p in snaps:
        try:
            df = pd.read_parquet(p)
            dfs.append((p, df))
        except Exception as exc:
            print(f"  [WARN] Failed to read {p}: {exc}", file=sys.stderr)

    for p, df in dfs:
        ts_ms = int(df["ts_ms"].iloc[0]) if "ts_ms" in df.columns else 0
        dt_utc = datetime.fromtimestamp(ts_ms / 1000, tz=timezone.utc)
        result["snapshots"].append({
            "file": p.name,
            "rows": len(df),
            "cols": len(df.columns),
            "ts_utc": dt_utc.strftime("%Y-%m-%dT%H:%M UTC"),
            "ts_jst": dt_utc.astimezone(JST).strftime("%Y-%m-%dT%H:%M JST"),
        })

    # Use the richest schema snapshot (most columns)
    best = max(dfs, key=lambda x: len(x[1].columns))
    result["schema_columns"] = list(best[1].columns)
    result["rows_per_snapshot_expected"] = 22  # 11 outcomes × 2 sides

    # Price stability: diff between first and last full schema snapshot
    full_schema = [(p, df) for p, df in dfs if len(df.columns) >= 18]
    if len(full_schema) >= 2:
        df_first = full_schema[0][1]
        df_last  = full_schema[-1][1]
        t_first  = int(df_first["ts_ms"].iloc[0])
        t_last   = int(df_last["ts_ms"].iloc[0])
        delta_min = (t_last - t_first) / 60000

        merged = df_first[["coin", "outcome_name", "side_name", "mid_price"]].merge(
            df_last[["coin", "mid_price"]], on="coin", suffixes=("_first", "_last")
        )
        merged["delta"] = merged["mid_price_last"] - merged["mid_price_first"]
        movers = merged[merged["delta"].abs() > 0].copy()

        result["price_stability_22min"] = {
            "delta_minutes": round(delta_min, 1),
            "coins_with_price_change": len(movers),
            "total_coins": len(merged),
            "max_abs_delta": round(float(movers["delta"].abs().max()), 6) if len(movers) else 0.0,
            "movers": [
                {
                    "coin": row.coin,
                    "outcome": row.outcome_name,
                    "side": row.side_name,
                    "p_first": round(row.mid_price_first, 6),
                    "p_last": round(row.mid_price_last, 6),
                    "delta": round(row.delta, 6),
                }
                for _, row in movers.iterrows()
            ],
        }

    # Daemon status assessment
    if len(snaps) <= 2:
        result["daemon_status_assessment"] = (
            "DAEMON_NOT_LOADED — only manual test snapshots found. "
            "K356 plist was scaffolded but user did not activate launchd daemon. "
            "Calibration requires 14+ daily outcomes; current data insufficient."
        )
    elif len(snaps) <= 10:
        result["daemon_status_assessment"] = (
            f"PARTIAL_DATA — {len(snaps)} snapshots found. "
            "Daemon may have been briefly active. Calibration window still short."
        )
    else:
        result["daemon_status_assessment"] = (
            f"DATA_SUFFICIENT — {len(snaps)} snapshots. Calibration analysis feasible."
        )

    return result


# ---------------------------------------------------------------------------
# Phase 5: Retrospective fetch fallback
# ---------------------------------------------------------------------------

def hl_post(payload: dict, retries: int = 3, delay: float = 3.0) -> Any:
    """POST to HL info API with retry."""
    for attempt in range(retries):
        try:
            body = json.dumps(payload).encode()
            req  = urllib.request.Request(
                HL_API, data=body,
                headers={"Content-Type": "application/json", "User-Agent": "ct-k395-prep/1.0"}
            )
            with urllib.request.urlopen(req, timeout=20) as resp:
                return json.loads(resp.read())
        except Exception as exc:
            if attempt < retries - 1:
                wait = delay * (2 ** attempt)
                print(f"  [WARN] hl_post attempt {attempt+1} failed: {exc} — retry in {wait:.0f}s",
                      flush=True)
                time.sleep(wait)
            else:
                raise


def fetch_current_snapshot() -> Optional[Dict[str, Any]]:
    """
    Fetch one live snapshot from HL API.
    Used as fallback when daemon was not loaded — provides at least a single
    calibration reference point for K368.

    Returns dict with outcome prices and BTC mark, or None on error.
    """
    try:
        print("  [FALLBACK] Fetching live outcomeMeta from HL...", flush=True)
        meta_raw = hl_post({"type": "outcomeMeta"})
        outcomes  = meta_raw.get("outcomes", []) if isinstance(meta_raw, dict) else []
        questions = meta_raw.get("questions", []) if isinstance(meta_raw, dict) else []

        print("  [FALLBACK] Fetching live allMids from HL...", flush=True)
        mids_raw = hl_post({"type": "allMids"})
        all_mids: Dict[str, float] = {}
        if isinstance(mids_raw, dict):
            for k, v in mids_raw.items():
                try:
                    all_mids[k] = float(v)
                except (TypeError, ValueError):
                    pass

        hip4_mids = {k: v for k, v in all_mids.items() if k.startswith("#")}
        btc_mark  = all_mids.get("BTC")
        ts_ms     = int(time.time() * 1000)
        dt_str    = datetime.fromtimestamp(ts_ms / 1000, tz=JST).strftime("%Y-%m-%dT%H:%M JST")

        print(f"  [FALLBACK] {len(outcomes)} outcomes, {len(hip4_mids)} HIP-4 mids, BTC={btc_mark}",
              flush=True)

        return {
            "ts_ms":       ts_ms,
            "ts_jst":      dt_str,
            "btc_mark":    btc_mark,
            "n_outcomes":  len(outcomes),
            "n_questions": len(questions),
            "hip4_mids":   hip4_mids,
            "n_hip4_mids": len(hip4_mids),
        }
    except Exception as exc:
        print(f"  [WARN] Live fetch failed: {exc}", file=sys.stderr)
        traceback.print_exc()
        return None


# ---------------------------------------------------------------------------
# Phase 2-3: Calibration analysis design (documented as code + comments)
# ---------------------------------------------------------------------------

def design_calibration_framework() -> Dict[str, Any]:
    """
    Return the full K368 calibration analysis design spec.

    For the BTC recurring daily binary market (#1050 Yes / #1051 No):
      - Each day at settlement (06:00 UTC), outcome resolves Yes or No
      - Predicted P = last observed mid_price before 06:00 UTC for Yes side
      - Realized outcome = 1 if BTC mark >= targetPrice, else 0
      - Calibration: do N-day collections of (P, outcome) show E[outcome|P] ≈ P?

    Brier score: mean((P - outcome)^2); perfect = 0, random = 0.25
    Log loss:    mean(-outcome*log(P) - (1-outcome)*log(1-P)); perfect = 0
    Calibration gap: max over 10 probability bins of |bin_mean_P - bin_mean_outcome|

    Decision rule (K353/K356 gate):
      gap > 3%  → ACCEPT (bias exploitable, proceed to K369 trade prototype)
      gap 1-3%  → WATCH  (marginal, extend collection window)
      gap < 1%  → MONITOR (well-calibrated, no exploitable edge)
      N < 14    → INCONCLUSIVE (insufficient data)
    """
    return {
        "target_market": {
            "coin_yes": "#1050",
            "coin_no":  "#1051",
            "description": "BTC recurring daily binary — settles 06:00 UTC vs BTC mark price",
            "target_price_at_k356": 76877.0,
            "btc_mark_at_k356":     75757.5,
            "implied_prob_yes_at_k356": 0.048565,
            "note": "Target price resets daily. K356 snapshot shows 4.9% prob of BTC reaching 76877 by next 06:00 UTC.",
        },
        "metrics": {
            "brier_score": {
                "formula": "mean((P_predicted - outcome_binary)^2)",
                "perfect": 0.0,
                "random_baseline": 0.25,
                "interpretation": "Lower = better calibration. HL well-calibrated ≈ 0.02-0.05 for near-tail events.",
            },
            "log_loss": {
                "formula": "mean(-outcome * log(P) - (1-outcome) * log(1-P))",
                "perfect": 0.0,
                "binary_entropy_baseline": "depends on base rate",
                "clipping": "P clipped to [0.001, 0.999] to avoid -inf",
            },
            "calibration_bins": {
                "n_bins": 10,
                "bin_edges": [0.0, 0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9, 1.0],
                "per_bin": "mean(P_predicted) vs mean(outcome) within bin",
                "calibration_gap": "max(|bin_mean_P - bin_mean_outcome|) * 100  [in percentage points]",
            },
        },
        "decision_criteria": {
            "ACCEPT":       {"calibration_gap_pct_gt": 3.0, "min_N": 14,
                             "next": "K369 trade prototype on BTC recurring daily"},
            "WATCH":        {"calibration_gap_pct_range": [1.0, 3.0], "min_N": 14,
                             "next": "Extend daemon collection window +14 days"},
            "MONITOR":      {"calibration_gap_pct_lt": 1.0, "min_N": 14,
                             "next": "No exploitable edge, continue MONITOR status"},
            "INCONCLUSIVE": {"N_lt": 14,
                             "next": "Fallback to one-shot analysis or extend window"},
        },
        "minimum_data_requirements": {
            "daily_outcomes_needed": 14,
            "snapshots_per_day_daemon": 288,  # every 5min = 288/day
            "snapshots_per_day_manual": 1,     # one-shot fallback
            "resolution_events_at_06UTC": "One per calendar day",
        },
        "secondary_markets": {
            "May_CPI_yoy": {
                "coins": ["#1010", "#1011", "#1020", "#1021", "#1030", "#1031"],
                "resolution_date": "2026-06-10T12:30:00Z",
                "metric": "single-event Brier (N=1, directional check only)",
                "k356_prices": {
                    "Below_4.3pct_Yes": 0.368,
                    "Exactly_4.3pct_Yes": 0.437,
                    "Above_4.3pct_Yes": 0.229,
                },
                "note": "Single resolution event. Not enough for calibration curve; useful for directional accuracy check.",
            },
            "FOMC_June": {
                "coins": ["#1040", "#1041"],
                "resolution_date": "2026-06-18T18:00:00Z",
                "metric": "single-event Brier",
                "k356_prices": {"Change": 0.0315, "No_Change": 0.9685},
            },
            "UCL_Final": {
                "coins": ["#1100", "#1101"],
                "resolution_date": "2026-05-31",
                "metric": "single-event Brier",
                "k356_prices": {"PSG": 0.578, "Arsenal": 0.422},
                "note": "Already resolved by K368 target date. Historical check only.",
            },
        },
    }


# ---------------------------------------------------------------------------
# Phase 4: Cross-venue spread analysis design
# ---------------------------------------------------------------------------

def design_cross_venue_analysis() -> Dict[str, Any]:
    """
    Design spec for HL vs Polymarket spread monitoring.
    K353 baseline: spreads were 0.35–0.83pp absolute (all < 2% threshold).
    K368 will test whether this changed over the 2-week window.
    """
    return {
        "overlapping_markets": [
            {
                "name": "FOMC June 2026 — No Change",
                "hl_coin": "#1041",
                "polymarket_slug": "fomc-june-2026-no-rate-change",
                "k353_hl": 0.9685,
                "k353_poly": 0.972,
                "k353_abs_spread": 0.0035,
                "arb_threshold_abs": 0.02,
                "status": "BELOW_THRESHOLD",
            },
            {
                "name": "UCL 2026 — PSG",
                "hl_coin": "#1100",
                "polymarket_slug": "ucl-2026-winner-psg",
                "k353_hl": 0.5783,
                "k353_poly": 0.570,
                "k353_abs_spread": 0.0083,
                "arb_threshold_abs": 0.02,
                "status": "BELOW_THRESHOLD",
            },
            {
                "name": "UCL 2026 — Arsenal",
                "hl_coin": "#1101",
                "polymarket_slug": "ucl-2026-winner-arsenal",
                "k353_hl": 0.4217,
                "k353_poly": 0.430,
                "k353_abs_spread": 0.0083,
                "arb_threshold_abs": 0.02,
                "status": "BELOW_THRESHOLD",
            },
        ],
        "persistence_criteria": {
            "min_spread_pct_abs": 0.02,
            "min_persistence_minutes": 30,
            "arb_candidate_trigger": "spread > 2% for > 30min in >= 3 separate windows",
            "k208_arb_comparison": "K208-style: detect regime, size Kelly, hold until convergence",
        },
        "k353_conclusion": "No >2% absolute spread on any liquid HL vs Polymarket market. UCL resolved by K368 date.",
        "k368_retest": "Recheck FOMC (#1041) vs Polymarket on 2026-06-10 (8 days before FOMC decision).",
        "structural_barriers": [
            "Polymarket geo-restricted (US accounts blocked)",
            "USDC bridge friction between HL and Polymarket",
            "Same underlying data sources → pre-resolution convergence",
            "Settlement timing: both use BLS/FOMC official releases",
        ],
    }


# ---------------------------------------------------------------------------
# Phase 5: Fallback plan
# ---------------------------------------------------------------------------

def design_fallback_plan(n_snapshots: int) -> Dict[str, Any]:
    """
    If daemon was not loaded, what can K368 still accomplish?
    """
    daemon_loaded = n_snapshots > 10
    return {
        "daemon_was_loaded": daemon_loaded,
        "current_snapshot_count": n_snapshots,
        "calibration_feasibility": "LIKELY_INCONCLUSIVE" if not daemon_loaded else "FEASIBLE",
        "fallback_options": [
            {
                "option": "A — Manual batch fetch (recommended if daemon not loaded)",
                "description": (
                    "Run scripts/hl_hip4_monitor.py once daily from 2026-05-29 to 2026-06-09 "
                    "(12 days). Each run captures one snapshot per day. "
                    "At K368 (2026-06-10) CPI resolves → 1 resolution event (May CPI YoY). "
                    "BTC recurring: 12 daily settlements from 2026-05-28 to 2026-06-09."
                ),
                "data_yield": "12 BTC daily outcomes, 1 CPI outcome — marginal but usable",
                "command": "python3 scripts/hl_hip4_monitor.py",
                "effort": "LOW — one command per day",
            },
            {
                "option": "B — One-shot live fetch at K368",
                "description": (
                    "Fetch a single live snapshot on 2026-06-10. Compare CPI implied prob "
                    "against BLS release. N=1: directional accuracy only, no calibration curve."
                ),
                "data_yield": "1 CPI outcome — directional accuracy check, not calibration",
                "effort": "ZERO — auto-runs in K368 wave script",
            },
            {
                "option": "C — Daemon activation NOW (most valuable)",
                "description": (
                    "User activates launchd daemon immediately. 12 days × 288 snapshots/day "
                    "= 3456 snapshots, 12 BTC daily outcomes. Full calibration curve feasible."
                ),
                "data_yield": "12 BTC daily outcomes, dense intraday price path, 1 CPI outcome",
                "command": (
                    "cp com.cryptolab.hl-hip4-monitor.plist ~/Library/LaunchAgents/ && "
                    "launchctl load ~/Library/LaunchAgents/com.cryptolab.hl-hip4-monitor.plist"
                ),
                "verify": (
                    "python3 scripts/verify_deployment_status.py | grep hip4"
                ),
                "effort": "ONE-TIME — 30 seconds",
            },
        ],
        "k368_alternative_if_no_daemon": {
            "title": "K368 One-Shot Calibration (Fallback Mode)",
            "steps": [
                "Load all cache/hl_hip4_snapshots/*.parquet (3 manual snapshots)",
                "Fetch live snapshot on 2026-06-10 at CPI release time (08:30 EDT / 12:30 UTC)",
                "Compare P_predicted vs resolved outcome for CPI outcomes (N=1 per bucket)",
                "Compute single-event Brier for CPI: below/above/exactly 4.3%",
                "Document as 'directional accuracy check' — not full calibration",
                "BTC recurring: if no daemon, rely on K356 baseline P ≈ 4.9% (1 reference point)",
                "Decision: INCONCLUSIVE → extend to K380+ with daemon activated",
            ],
            "value": "Even 1 CPI resolution event provides directional accuracy data. Not waste.",
        },
        "activation_reminder": {
            "plist": "com.cryptolab.hl-hip4-monitor.plist",
            "load_command": (
                "cp com.cryptolab.hl-hip4-monitor.plist ~/Library/LaunchAgents/ && "
                "launchctl load ~/Library/LaunchAgents/com.cryptolab.hl-hip4-monitor.plist"
            ),
            "verify_loaded": "launchctl list | grep hip4",
            "verify_health": "python3 scripts/verify_deployment_status.py | grep hip4",
            "days_remaining_to_k368": 12,
            "snapshots_if_loaded_now": 12 * 288,  # = 3456
        },
    }


# ---------------------------------------------------------------------------
# Phase 6: K368 wave structure preview
# ---------------------------------------------------------------------------

def preview_k368_structure() -> Dict[str, Any]:
    return {
        "wave": "K368",
        "target_date": "2026-06-10",
        "trigger": "CPI May YoY resolution at 08:30 EDT (12:30 UTC)",
        "phases": [
            {
                "phase": 1,
                "name": "Data load",
                "action": "glob cache/hl_hip4_snapshots/*.parquet → concat → sort by ts_ms",
                "output": "Single DataFrame with all snapshots",
            },
            {
                "phase": 2,
                "name": "BTC recurring calibration",
                "action": (
                    "For each 06:00 UTC window: extract last mid_price (#1050 Yes) before settlement. "
                    "Mark resolved_outcome=1/0. Compute Brier, log loss, 10-bin calibration curve."
                ),
                "output": "brier_score, log_loss, calibration_bins, calibration_gap_pct",
                "decision_gate": "gap > 3% → ACCEPT | 1-3% → WATCH | <1% → MONITOR | N<14 → INCONCLUSIVE",
            },
            {
                "phase": 3,
                "name": "CPI single-event accuracy",
                "action": (
                    "Fetch BLS CPI release (web scrape or manual input). "
                    "Compare K356 implied probs (Below 0.368, Exactly 0.437, Above 0.229) "
                    "against actual May 2026 CPI YoY value."
                ),
                "output": "Single-event Brier per CPI bucket, directional accuracy",
            },
            {
                "phase": 4,
                "name": "FOMC cross-venue check",
                "action": "Fetch live #1041 price, compare to Polymarket FOMC. Spread vs K353 baseline.",
                "output": "Current HL/Poly spread, trend since K353",
            },
            {
                "phase": 5,
                "name": "Decision",
                "action": "Apply decision criteria from Phase 2",
                "outputs": {
                    "ACCEPT":       "Proceed to K369 — HIP-4 BTC recurring trade prototype",
                    "WATCH":        "Extend daemon +14 days, recheck at K380",
                    "MONITOR":      "Keep daemon running, no active trading",
                    "INCONCLUSIVE": "Fallback one-shot mode, evaluate with N=1 CPI data",
                },
            },
        ],
        "deliverables": [
            "wave_k368_hip4_calibration.py",
            "wave_k368_hip4_calibration.json (metrics + decision)",
            "wave_k368_hip4_calibration.md (200-300 lines)",
        ],
    }


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> None:
    ts_now_jst = datetime.now(JST).strftime("%Y-%m-%dT%H:%M JST")
    print(f"\n{'='*60}", flush=True)
    print(f"K395 HIP-4 Calibration Prep — {ts_now_jst}", flush=True)
    print(f"{'='*60}\n", flush=True)

    # Phase 1: Cache inspection
    print("[Phase 1] Inspecting K356 snapshot cache...", flush=True)
    cache_state = inspect_cache()
    n_snaps = cache_state["snapshot_count"]
    print(f"  Snapshots found: {n_snaps}", flush=True)
    print(f"  Assessment: {cache_state['daemon_status_assessment']}", flush=True)
    if cache_state.get("price_stability_22min"):
        ps = cache_state["price_stability_22min"]
        print(f"  Price stability ({ps['delta_minutes']}min): "
              f"{ps['coins_with_price_change']}/{ps['total_coins']} coins moved, "
              f"max_delta={ps['max_abs_delta']}", flush=True)

    # Phase 5: Live fallback fetch (lightweight — fetch current snapshot for reference)
    print("\n[Phase 5] Attempting live HL fallback fetch...", flush=True)
    live_snapshot = fetch_current_snapshot()
    if live_snapshot:
        print(f"  Live fetch OK: {live_snapshot['n_hip4_mids']} HIP-4 mids, BTC={live_snapshot['btc_mark']}",
              flush=True)
    else:
        print("  Live fetch failed — network unavailable or HL API down", flush=True)

    # Phases 2-4: Design frameworks
    print("\n[Phase 2-3] Building calibration analysis design...", flush=True)
    calib_framework = design_calibration_framework()
    print("  Calibration framework designed (BTC recurring + CPI + FOMC)", flush=True)

    print("\n[Phase 4] Building cross-venue spread analysis design...", flush=True)
    cross_venue = design_cross_venue_analysis()
    print(f"  {len(cross_venue['overlapping_markets'])} overlapping HL/Polymarket markets documented",
          flush=True)

    print("\n[Phase 5] Designing fallback plan...", flush=True)
    fallback = design_fallback_plan(n_snaps)
    print(f"  Daemon loaded: {fallback['daemon_was_loaded']}", flush=True)
    print(f"  Calibration feasibility: {fallback['calibration_feasibility']}", flush=True)
    print(f"  Fallback options: {len(fallback['fallback_options'])}", flush=True)

    print("\n[Phase 6] Previewing K368 wave structure...", flush=True)
    k368_preview = preview_k368_structure()
    print(f"  K368 phases: {len(k368_preview['phases'])}", flush=True)

    # Assemble output JSON
    output = {
        "wave": "K395",
        "generated_at_jst": ts_now_jst,
        "k368_target_date": "2026-06-10",
        "days_to_k368": 12,
        "phase1_cache_state": cache_state,
        "phase2_calibration_framework": calib_framework,
        "phase3_decision_criteria": calib_framework["decision_criteria"],
        "phase4_cross_venue_design": cross_venue,
        "phase5_fallback_plan": fallback,
        "phase5_live_snapshot": live_snapshot,
        "phase6_k368_preview": k368_preview,
        "user_action_required": {
            "priority": "HIGH" if not fallback["daemon_was_loaded"] else "NONE",
            "action": (
                "Activate launchd daemon NOW to collect 12 days of BTC recurring daily data "
                "before 2026-06-10 K368 calibration target."
                if not fallback["daemon_was_loaded"] else
                "Daemon active — verify health in 7 days."
            ),
            "command": fallback["activation_reminder"]["load_command"],
            "verify": fallback["activation_reminder"]["verify_loaded"],
        },
    }

    # Write JSON
    REPO_ROOT.mkdir(parents=True, exist_ok=True)
    with open(OUT_JSON, "w") as fh:
        json.dump(output, fh, indent=2, default=str)
    print(f"\n  Written: {OUT_JSON}", flush=True)

    print(f"\n{'='*60}", flush=True)
    print("K395 COMPLETE", flush=True)
    print(f"  Snapshots: {n_snaps} (daemon {'NOT ' if not fallback['daemon_was_loaded'] else ''}loaded)", flush=True)
    print(f"  Calibration feasibility: {fallback['calibration_feasibility']}", flush=True)
    if not fallback["daemon_was_loaded"]:
        print("  ACTION REQUIRED: Load daemon → 12 days of data before K368", flush=True)
        print(f"  CMD: {fallback['activation_reminder']['load_command']}", flush=True)
    print(f"{'='*60}\n", flush=True)


if __name__ == "__main__":
    main()

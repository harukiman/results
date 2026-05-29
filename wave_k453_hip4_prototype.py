#!/usr/bin/env python3
"""
wave_k453_hip4_prototype.py — K453 HL HIP-4 Prediction Market Trading Prototype
==================================================================================
Builds on K353 (MONITOR verdict, 22 outcomes) and K356 (polling daemon scaffold).
Purpose: characterize the 5 cached snapshots, assess strategy feasibility per K266
gates, and produce a structured JSON/MD report for the paper-trade scaffold decision.

NO production orders are placed. This is analysis + prototype scaffolding only.

K453 mandate: maximize live profit — but calibration data is insufficient until
K368 (target 2026-06-22). This wave builds the scaffold and documents the gate
pass/fail status with the current evidence.

Security: K339 — REPO_ROOT relative paths, no /Users/ literals.
"""
from __future__ import annotations

import json
import sys
import time
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import pandas as pd
import numpy as np

# ---------------------------------------------------------------------------
# Paths — K339 security pattern
# ---------------------------------------------------------------------------
REPO_ROOT  = Path(__file__).resolve().parent
CACHE_DIR  = REPO_ROOT / "cache" / "hl_hip4_snapshots"
LOGS_DIR   = REPO_ROOT / "logs"
JST        = timezone(timedelta(hours=9))


# ---------------------------------------------------------------------------
# 1. Load all K356 snapshots
# ---------------------------------------------------------------------------

def load_snapshots() -> pd.DataFrame:
    """
    Load all parquet files from cache/hl_hip4_snapshots/.
    Returns concatenated DataFrame, filtering to full-schema snapshots only
    (those with question_name column — earliest partial snapshot excluded).
    """
    files = sorted(CACHE_DIR.glob("hip4_*.parquet"))
    if not files:
        raise FileNotFoundError(f"No snapshots in {CACHE_DIR}")

    dfs = []
    for f in files:
        df = pd.read_parquet(f)
        if "question_name" in df.columns:      # full-schema only
            df["source_file"] = f.name
            dfs.append(df)

    if not dfs:
        raise ValueError("No full-schema snapshots found")

    combined = pd.concat(dfs, ignore_index=True)
    combined["dt_utc"] = pd.to_datetime(combined["ts_ms"], unit="ms", utc=True)
    return combined


# ---------------------------------------------------------------------------
# 2. Market inventory
# ---------------------------------------------------------------------------

MARKET_CATEGORIES = {
    "May CPI year-over-year": "macro_one-off",
    "": "macro_fomc_recurring_unknown",  # June Fed rate change / Champions League / Recurring
    "Recurring": "btc_daily_binary",
}

def build_market_inventory(df: pd.DataFrame) -> Dict[str, Any]:
    """
    Enumerate all markets, outcomes, resolution status, and category.
    Returns structured dict for JSON output.
    """
    latest_ts = df["ts_ms"].max()
    latest = df[df["ts_ms"] == latest_ts].copy()

    markets: List[Dict] = []

    # Group by question_name + special grouping for empty question_name
    # The empty-question_name group contains: June Fed rate change, Champions League, Recurring
    for q_name in latest["question_name"].dropna().unique():
        q_rows = latest[latest["question_name"] == q_name]
        # Only Yes side for price display
        yes_rows = q_rows[q_rows["side"] == 0]

        outcomes_list = []
        for _, row in yes_rows.iterrows():
            outcomes_list.append({
                "outcome_name": row["outcome_name"],
                "outcome_id":   int(row["outcome_id"]) if pd.notna(row["outcome_id"]) else None,
                "coin_key":     row["coin"],
                "mid_price_yes": float(row["mid_price"]) if pd.notna(row["mid_price"]) else None,
                "resolved":     bool(row["resolved"]) if pd.notna(row["resolved"]) else False,
                "description":  str(row["description"]) if pd.notna(row["description"]) else "",
            })

        # Categorize
        if q_name == "May CPI year-over-year":
            cat = "macro_one-off"
            resolution_target = "2026-06-11"  # BLS CPI release date
            strategy_applicability = ["calibration_arb", "event_trading"]
        elif q_name == "Recurring":
            cat = "btc_daily_binary"
            resolution_target = "daily (06:00 UTC expiry)"
            strategy_applicability = ["event_trading", "kelly_binary", "mean_reversion"]
        else:
            cat = "unknown"
            resolution_target = "TBD"
            strategy_applicability = ["event_trading"]

        markets.append({
            "question_name":          q_name,
            "category":               cat,
            "n_outcomes":             len(outcomes_list),
            "resolution_target":      resolution_target,
            "outcomes":               outcomes_list,
            "strategy_applicability": strategy_applicability,
        })

    # Special: empty question_name (June FOMC, Champions League, Recurring Named Outcomes)
    unnamed = latest[latest["question_name"].fillna("") == ""]
    if len(unnamed) > 0:
        yes_unnamed = unnamed[unnamed["side"] == 0]
        for _, row in yes_unnamed.iterrows():
            name = str(row["outcome_name"])
            if "June Fed" in name or "rate change" in name.lower():
                cat = "macro_fomc"
                res_target = "2026-06-17 (FOMC decision)"
                strat = ["event_trading", "calibration_arb"]
            elif "Champions" in name or "PSG" in name or "Arsenal" in name:
                cat = "sports_one-off"
                res_target = "2026-05-31 (UCL Final)"
                strat = ["event_trading"]
            elif "Recurring" in name:
                cat = "btc_daily_binary"
                res_target = "daily (06:00 UTC expiry)"
                strat = ["event_trading", "kelly_binary"]
            else:
                cat = "unknown"
                res_target = "unknown"
                strat = []

            markets.append({
                "question_name":          name,
                "category":               cat,
                "n_outcomes":             1,
                "resolution_target":      res_target,
                "outcomes": [{
                    "outcome_name":   name,
                    "outcome_id":     int(row["outcome_id"]) if pd.notna(row["outcome_id"]) else None,
                    "coin_key":       row["coin"],
                    "mid_price_yes":  float(row["mid_price"]) if pd.notna(row["mid_price"]) else None,
                    "resolved":       bool(row["resolved"]) if pd.notna(row["resolved"]) else False,
                    "description":    str(row["description"]) if pd.notna(row["description"]) else "",
                }],
                "strategy_applicability": strat,
            })

    return {
        "snapshot_count":    int(df["source_file"].nunique()),
        "latest_ts_utc":     datetime.fromtimestamp(latest_ts / 1000, tz=timezone.utc).isoformat(),
        "n_markets":         len(markets),
        "n_outcomes_total":  len(latest),
        "markets":           markets,
    }


# ---------------------------------------------------------------------------
# 3. Price evolution analysis
# ---------------------------------------------------------------------------

def analyze_price_evolution(df: pd.DataFrame) -> Dict[str, Any]:
    """
    For each outcome (Yes side), track price across all snapshots.
    Key metrics: total drift, max single-period move, volatility.
    """
    yes_side = df[df["side"] == 0].copy()
    yes_side = yes_side.sort_values("ts_ms")

    snapshots = sorted(yes_side["ts_ms"].unique())
    n_snaps = len(snapshots)

    evolution: List[Dict] = []
    for outcome_id in yes_side["outcome_id"].dropna().unique():
        rows = yes_side[yes_side["outcome_id"] == outcome_id].sort_values("ts_ms")
        if len(rows) < 2:
            continue

        prices = rows["mid_price"].dropna().tolist()
        if not prices:
            continue

        first_p = prices[0]
        last_p  = prices[-1]
        diffs   = [prices[i+1] - prices[i] for i in range(len(prices)-1)]

        evolution.append({
            "outcome_id":      int(outcome_id),
            "outcome_name":    rows["outcome_name"].iloc[0],
            "question_name":   rows["question_name"].iloc[0],
            "n_snapshots":     len(rows),
            "price_first":     round(first_p, 4),
            "price_last":      round(last_p, 4),
            "total_drift":     round(last_p - first_p, 4),
            "max_move":        round(max(abs(d) for d in diffs), 4) if diffs else 0.0,
            "std_moves":       round(float(np.std(diffs)), 4) if len(diffs) > 1 else 0.0,
            "prices_series":   [round(p, 4) for p in prices],
        })

    return {
        "n_snapshots": n_snaps,
        "span_days":   round((max(snapshots) - min(snapshots)) / 86400_000, 2),
        "outcomes":    evolution,
    }


# ---------------------------------------------------------------------------
# 4. BTC daily binary structure decode
# ---------------------------------------------------------------------------

def decode_btc_daily_binary(df: pd.DataFrame) -> Dict[str, Any]:
    """
    Decode the Recurring (BTC daily binary) market structure from descriptions.
    Format: class:priceBinary|underlying:BTC|expiry:YYYYMMDD-HHMM|targetPrice:XXXXX|period:1d
    """
    btc_markets = df[
        df["description"].fillna("").str.startswith("class:priceBinary")
    ].copy()

    decoded = []
    for _, row in btc_markets.drop_duplicates("outcome_id").iterrows():
        desc = str(row["description"])
        parts = dict(kv.split(":", 1) for kv in desc.split("|") if ":" in kv)
        expiry_str = parts.get("expiry", "")
        target     = parts.get("targetPrice", "N/A")

        try:
            expiry_dt = datetime.strptime(expiry_str, "%Y%m%d-%H%M").replace(
                tzinfo=timezone.utc
            )
        except ValueError:
            expiry_dt = None

        decoded.append({
            "outcome_id":    int(row["outcome_id"]) if pd.notna(row["outcome_id"]) else None,
            "coin_key":      row["coin"],
            "target_price":  float(target) if target != "N/A" else None,
            "expiry_utc":    expiry_dt.isoformat() if expiry_dt else expiry_str,
            "period":        parts.get("period", "1d"),
            "description":   desc,
        })

    # BTC snapshot prices at relevant times
    btc_prices = (
        df[["ts_ms", "btc_mark"]].drop_duplicates("ts_ms")
        .sort_values("ts_ms")
        .assign(dt_utc=lambda x: pd.to_datetime(x["ts_ms"], unit="ms", utc=True))
    )

    btc_series = [
        {"dt_utc": str(r["dt_utc"]), "btc_mark": float(r["btc_mark"])}
        for _, r in btc_prices.iterrows()
        if pd.notna(r["btc_mark"])
    ]

    # Cross-check: for each daily binary, is BTC above/below target at closest snapshot?
    calibration_hints: List[Dict] = []
    for mkt in decoded:
        tp = mkt.get("target_price")
        if tp is None:
            continue
        # Use last snapshot price
        last_btc = btc_series[-1]["btc_mark"] if btc_series else None
        if last_btc is not None:
            implied_yes = "BTC > target" if last_btc > tp else "BTC < target"
            calibration_hints.append({
                "outcome_id":   mkt["outcome_id"],
                "target_price": tp,
                "last_btc_mark": last_btc,
                "implied_direction": implied_yes,
            })

    return {
        "n_btc_binary_outcomes": len(decoded),
        "decoded_markets":       decoded,
        "btc_price_series":      btc_series,
        "calibration_hints":     calibration_hints,
        "note": (
            "BTC daily binary: expiry at 06:00 UTC daily. "
            "3 active outcomes per cycle (index:0,1,2) + fallback. "
            "index:0 = imminent-expiry outcome. index:1 = next day. index:2 = day after."
        ),
    }


# ---------------------------------------------------------------------------
# 5. Strategy feasibility per K266 gates
# ---------------------------------------------------------------------------

def assess_strategy_feasibility(
    inventory: Dict[str, Any],
    price_evo: Dict[str, Any],
    btc_daily: Dict[str, Any],
) -> Dict[str, Any]:
    """
    Assess each of the 5 proposed strategies against K266 gates.
    Returns pass/fail/pending with rationale.
    """
    n_snapshots = price_evo["n_snapshots"]
    span_days   = price_evo["span_days"]

    strategies = {

        "S1_calibration_arb": {
            "name":        "Calibration Arbitrage",
            "description": "Bet on undervalued side when HL pricing is systematically mis-calibrated",
            "requires":    ["K368 calibration data (min N=30 resolution events)", "2+ weeks of snapshots"],
            "current_data_n": n_snapshots,
            "current_span_days": span_days,
            "gates": {
                "G1_oos_sharpe": {
                    "status": "PENDING",
                    "reason": f"Needs N≥30 resolved events. Have {n_snapshots} snapshots, 0 resolutions confirmed.",
                    "target": "K368 calibration 2026-06-22",
                },
                "G2_perm_pvalue": {"status": "PENDING", "reason": "No resolutions yet"},
                "G3_dsr":         {"status": "PENDING", "reason": "No resolutions yet"},
                "G4_walk_forward":{"status": "PENDING", "reason": "Need 4-fold temporal split → min 120 events"},
                "G5_corr_check":  {"status": "LIKELY_PASS", "reason": "Event-driven, orthogonal to all FR/momentum strategies"},
                "G6_trade_count": {"status": "CONDITIONAL_PASS", "reason": "BTC daily = 365 bets/yr. Macro = ~10/yr."},
                "G7_ann_return":  {"status": "SPECULATIVE", "reason": "Edge unknown without calibration: assume 2-5%"},
            },
            "verdict":     "PENDING — wait for K368 calibration (2026-06-22)",
            "action":      "SCAFFOLD + MONITOR",
        },

        "S2_cross_venue_arb": {
            "name":        "Cross-Venue Arbitrage (HL vs Polymarket/Kalshi)",
            "description": "Bet on spread when HL vs external venue diverges >2%",
            "requires":    ["Real-time Polymarket/Kalshi API integration", "Spread monitoring daemon"],
            "current_data_n": n_snapshots,
            "gates": {
                "G1_oos_sharpe":  {"status": "PENDING", "reason": "Need live spread monitoring"},
                "G2_perm_pvalue": {"status": "PENDING", "reason": "Need N≥30 arb events"},
                "G3_dsr":         {"status": "PENDING", "reason": "Single strategy, but unproven"},
                "G4_walk_forward":{"status": "PENDING", "reason": "Need time-series of spread data"},
                "G5_corr_check":  {"status": "LIKELY_PASS", "reason": "Arb is event-driven, low correlation"},
                "G6_trade_count": {"status": "CONDITIONAL", "reason": "Depends on spread frequency >2%"},
                "G7_ann_return":  {"status": "SPECULATIVE", "reason": "Spread <2% currently; arb edge unknown"},
            },
            "k353_finding": "K353 found spreads <2% currently — below actionable threshold",
            "verdict":      "MONITOR — deploy only when spread >2% events detected",
            "action":       "MONITOR",
        },

        "S3_market_making": {
            "name":        "Market-Making (Liquidity Provision)",
            "description": "Post bids/asks on both sides, capture spread passively",
            "requires":    ["HL HIP-4 market maker API access", "Inventory risk model", "Adverse selection filter"],
            "gates": {
                "G1_oos_sharpe":  {"status": "PENDING", "reason": "No MM backtest data"},
                "G6_trade_count": {"status": "LIKELY_PASS", "reason": "MM fills continuously"},
            },
            "key_risks": ["Adverse selection from informed traders", "Inventory limits", "API access unclear"],
            "verdict":   "DEFER — requires dedicated MM infrastructure not in K356",
            "action":    "DEFER",
        },

        "S4_event_trading": {
            "name":        "Event Trading (Near-Resolution Markets)",
            "description": "Bet on near-expiry markets where outcome uncertainty is low",
            "requires":    ["Pricing accuracy at T-1h", "Sufficient liquidity"],
            "observations": {
                "june_fomc_rate_change": {
                    "market": "June Fed rate change",
                    "mid_price": 0.02698,
                    "interpretation": "97.3% probability NO CHANGE — consensus trade",
                    "edge_assessment": "Very low edge if market is correctly pricing consensus",
                },
                "ucl_final": {
                    "market": "Champions League Winner (PSG vs Arsenal)",
                    "mid_price_psg": 0.5853,
                    "resolution_date": "2026-05-31",
                    "edge_assessment": "Sports prediction — depends on model advantage over market",
                },
                "btc_daily_binary": {
                    "description": "index:1 (next day) pricing at 0.937 YES on 2026-05-28",
                    "interpretation": "Market predicts BTC stays above target on 2026-05-29",
                    "edge_assessment": "High confidence pricing → low edge unless model disagrees",
                },
            },
            "gates": {
                "G1_oos_sharpe":  {"status": "PENDING", "reason": "No backtestable historical resolutions"},
                "G6_trade_count": {"status": "CONDITIONAL_PASS", "reason": "BTC daily = 365/yr satisfies G6"},
            },
            "verdict": "CONDITIONAL — BTC daily binary is the best candidate; macro events too infrequent",
            "action":  "SCAFFOLD + MONITOR",
        },

        "S5_btc_daily_kelly": {
            "name":        "BTC Daily Binary — Kelly-Sized Bets",
            "description": "Use HL predicted P vs actual BTC outcome; size position via Kelly criterion",
            "requires":    ["Minimum 14+ daily resolutions for calibration", "Brier score analysis"],
            "kelly_framework": {
                "formula":           "f* = |P_HL - 0.5| × 2   (binary Kelly)",
                "fractional_kelly":  "f/4 recommended (safety factor)",
                "edge_per_bet":      "unknown until calibration",
                "example_at_p=0.6":  {
                    "kelly_full":     "0.20 (20% of bankroll)",
                    "kelly_quarter":  "0.05 (5% of bankroll)",
                    "note":           "Even quarter-Kelly is aggressive for unproven market",
                },
            },
            "btc_binary_structure": {
                "n_active_per_cycle": 3,
                "index_0_meaning":    "imminent expiry (≤24h)",
                "index_1_meaning":    "next day (~24-48h)",
                "index_2_meaning":    "day-after (~48-72h)",
                "observed_prices": {
                    "2026-05-28_index0": 0.002505,  # near-certain NO (BTC far from target)
                    "2026-05-28_index1": 0.937295,  # near-certain YES (BTC above target)
                    "2026-05-28_index2": 0.073680,  # near-certain NO (BTC below target)
                },
                "btc_mark_at_observation": 73633.5,
            },
            "gates": {
                "G1_oos_sharpe":  {"status": "PENDING", "reason": "Need N≥30 daily resolutions"},
                "G2_perm_pvalue": {"status": "PENDING", "reason": "Need resolutions for shuffle test"},
                "G6_trade_count": {"status": "PASS", "reason": "365 bets/yr >> 50 threshold"},
                "G7_ann_return":  {"status": "SPECULATIVE",
                                   "reason": "If edge = 2% per bet × 365 bets × $400K notional = $2.92M/yr potential; HIGHLY SPECULATIVE"},
            },
            "verdict": "HIGHEST PRIORITY CANDIDATE — but requires calibration evidence",
            "action":  "SCAFFOLD + MONITOR → DEPLOY post-K368",
        },
    }

    # Summary counts
    scaffold_count = sum(1 for s in strategies.values() if "SCAFFOLD" in s.get("action",""))
    defer_count    = sum(1 for s in strategies.values() if s.get("action") == "DEFER")
    monitor_count  = sum(1 for s in strategies.values() if s.get("action") == "MONITOR")

    return {
        "strategies":        strategies,
        "summary": {
            "scaffold_count": scaffold_count,
            "defer_count":    defer_count,
            "monitor_count":  monitor_count,
            "top_priority":   "S5_btc_daily_kelly",
            "data_gap":       f"Only {n_snapshots} snapshots over {span_days} days. Need 14+ daily resolutions for G1/G2.",
        },
    }


# ---------------------------------------------------------------------------
# 6. K266 gate status (aggregate)
# ---------------------------------------------------------------------------

def build_k266_gate_status(n_snapshots: int, span_days: float) -> Dict[str, Any]:
    """Overall K266 gate evaluation for HIP-4 as a strategy family."""
    return {
        "wave":      "K453",
        "strategy":  "HL HIP-4 Prediction Market Trading",
        "data_as_of": datetime.now(JST).strftime("%Y-%m-%dT%H:%M JST"),
        "gates": {
            "G1_oos_sharpe": {
                "value":     None,
                "threshold": 1.0,
                "status":    "PENDING",
                "reason":    f"0 resolved events. Need N≥30. {n_snapshots} snapshots over {span_days}d.",
            },
            "G2_perm_pvalue": {
                "value":     None,
                "threshold": 0.05,
                "status":    "PENDING",
                "reason":    "Requires resolved outcome series for permutation test.",
            },
            "G3_dsr": {
                "value":     None,
                "threshold": 0.05,
                "status":    "PENDING",
                "reason":    "5 strategies explored; Bonferroni correction needed once data available.",
                "n_trials":  5,
            },
            "G4_walk_forward": {
                "value":     None,
                "threshold": "all 4 folds positive",
                "status":    "PENDING",
                "reason":    "Need ~120 resolved events for 4-fold split.",
            },
            "G5_corr_check": {
                "vs_K280":   "~0.0 (event-driven vs momentum)",
                "vs_K297":   "~0.0 (event-driven vs weekend FR)",
                "vs_K376":   "~0.0 (event-driven vs volume spike)",
                "vs_K449":   "~0.0 (event-driven vs FR differential carry)",
                "status":    "STRUCTURAL_PASS",
                "reason":    "Event-driven prediction markets are orthogonal to all current strategies.",
            },
            "G6_trade_count": {
                "btc_daily_bets_per_yr": 365,
                "macro_bets_per_yr":     "~10-20 (CPI, FOMC, sports)",
                "threshold":             50,
                "status":               "PASS_FOR_BTC_DAILY",
                "reason":               "BTC daily binary alone satisfies G6 (365 >> 50/yr).",
            },
            "G7_ann_return": {
                "value_estimate":  "2-5% per bet × 365 bets (highly speculative)",
                "threshold_pct":   5.0,
                "status":          "SPECULATIVE",
                "reason":          "Edge unknown without calibration. K368 will determine this.",
            },
        },
        "overall_verdict": "PENDING_CALIBRATION",
        "gates_passed_now": 2,  # G5 structural + G6 BTC daily
        "gates_total":      7,
        "calibration_target": "K368 — 2026-06-22",
        "decision":          "MONITOR / SCAFFOLD",
    }


# ---------------------------------------------------------------------------
# 7. Sleeve & profit estimate
# ---------------------------------------------------------------------------

def build_profit_estimate() -> Dict[str, Any]:
    """
    Conservative and optimistic annual profit estimates given assumptions.
    Highly speculative until K368 calibration.
    """
    aum = 10_000_000
    sleeve_pct = 0.01          # 1% initial sleeve
    leverage   = 4.0
    notional   = aum * sleeve_pct * leverage  # $400K

    # Scenarios
    scenarios = []
    for edge_pct, win_rate, label in [
        (0.01, 0.51, "bear_case: 1% edge, barely above chance"),
        (0.02, 0.52, "base_case: 2% edge, mild calibration bias"),
        (0.05, 0.55, "bull_case: 5% edge, significant mis-calibration"),
    ]:
        bets_per_yr = 365 + 20  # BTC daily + ~20 macro events
        gross_per_yr = notional * edge_pct * bets_per_yr * win_rate
        scenarios.append({
            "label":         label,
            "edge_pct":      edge_pct,
            "win_rate":      win_rate,
            "bets_per_yr":   bets_per_yr,
            "notional_usd":  notional,
            "gross_ann_usd": round(gross_per_yr, 0),
        })

    return {
        "aum_usd":       aum,
        "sleeve_pct":    sleeve_pct,
        "leverage":      leverage,
        "notional_usd":  notional,
        "scenarios":     scenarios,
        "hl_concentration_impact": {
            "current_hl_pct":    60.5,
            "hip4_sleeve_pct":   1.0,
            "new_hl_pct":        61.5,
            "hl_cap_pct":        65.0,
            "within_cap":        True,
        },
        "critical_caveat": (
            "ALL profit estimates are HIGHLY SPECULATIVE. Edge depends entirely on "
            "HL pricing calibration quality, which is unknown until K368 (2026-06-22). "
            "Do NOT deploy capital before K368 calibration confirmation."
        ),
    }


# ---------------------------------------------------------------------------
# 8. Recommendation
# ---------------------------------------------------------------------------

def build_recommendation(gates: Dict, profit: Dict) -> Dict[str, Any]:
    return {
        "wave":          "K453",
        "verdict":       "MONITOR",
        "sub_verdict":   "SCAFFOLD_READY",
        "rationale": [
            "5 snapshots over 2 days — insufficient for G1/G2/G4 empirical gates.",
            "BTC daily binary (Recurring market) is highest-priority candidate: 365 bets/yr satisfies G6.",
            "Structural correlation vs K280/K297/K376/K449 is near-zero (orthogonal alpha source).",
            "K356 polling daemon already running — snapshot accumulation ongoing.",
            "paper-trade scaffold (scripts/hip4_prediction_prototype.py) built in K453.",
            "Calibration bias analysis blocked until K368 (2026-06-22, min 28 daily resolutions).",
            "HL concentration: 60.5% → 61.5% at 1% sleeve — within 65% cap.",
        ],
        "gates_blocking_deploy": ["G1_oos_sharpe", "G2_perm_pvalue", "G3_dsr", "G4_walk_forward", "G7_ann_return"],
        "gates_passing_now":     ["G5_corr_check (structural)", "G6_trade_count (BTC daily)"],
        "next_milestone": {
            "wave":        "K368",
            "target_date": "2026-06-22",
            "trigger":     "28+ daily BTC binary resolutions accumulated",
            "deliverable": "Brier score analysis, calibration plot, G1/G2 empirical gates",
        },
        "action_items": [
            "Continue K356 polling (no change needed)",
            "Deploy scripts/hip4_prediction_prototype.py as paper-trade observer",
            "Accumulate resolution events: first UCL final (2026-05-31), then daily BTC binary",
            "At K368: compute Brier score, calibration plot, OOS Sharpe",
        ],
        "do_not": [
            "Do NOT deploy capital before K368 calibration evidence",
            "Do NOT size positions based on speculative edge estimates",
            "Do NOT open new daemon (K356 already covers this)",
        ],
        "proposed_v617": "NOT YET — waiting for K368 calibration",
    }


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> None:
    ts_start = time.time()
    print("[K453] HL HIP-4 Prediction Market Trading Prototype", flush=True)
    print(f"  Run time: {datetime.now(JST).strftime('%Y-%m-%dT%H:%M JST')}", flush=True)

    # Load data
    print("\n[1] Loading K356 snapshots...", flush=True)
    df = load_snapshots()
    n_snaps = df["source_file"].nunique()
    span_days = round((df["ts_ms"].max() - df["ts_ms"].min()) / 86400_000, 2)
    print(f"    {n_snaps} full-schema snapshots, {len(df)} rows, span {span_days} days", flush=True)

    # Market inventory
    print("\n[2] Building market inventory...", flush=True)
    inventory = build_market_inventory(df)
    print(f"    {inventory['n_markets']} markets, {inventory['n_outcomes_total']} outcome-sides", flush=True)

    # Price evolution
    print("\n[3] Analyzing price evolution...", flush=True)
    price_evo = analyze_price_evolution(df)
    print(f"    {len(price_evo['outcomes'])} outcomes tracked over {price_evo['span_days']} days", flush=True)

    # BTC daily binary decode
    print("\n[4] Decoding BTC daily binary structure...", flush=True)
    btc_daily = decode_btc_daily_binary(df)
    print(f"    {btc_daily['n_btc_binary_outcomes']} BTC binary outcomes decoded", flush=True)

    # Strategy feasibility
    print("\n[5] Assessing strategy feasibility...", flush=True)
    strategies = assess_strategy_feasibility(inventory, price_evo, btc_daily)
    print(f"    {strategies['summary']['scaffold_count']} strategies → SCAFFOLD, "
          f"{strategies['summary']['defer_count']} → DEFER, "
          f"{strategies['summary']['monitor_count']} → MONITOR", flush=True)

    # K266 gates
    print("\n[6] Building K266 gate status...", flush=True)
    gates = build_k266_gate_status(n_snaps, span_days)
    print(f"    Gates passed now: {gates['gates_passed_now']}/{gates['gates_total']}", flush=True)

    # Profit estimate
    print("\n[7] Building profit estimate...", flush=True)
    profit = build_profit_estimate()

    # Recommendation
    print("\n[8] Building recommendation...", flush=True)
    rec = build_recommendation(gates, profit)
    print(f"    Verdict: {rec['verdict']} / {rec['sub_verdict']}", flush=True)

    # Assemble output JSON
    output = {
        "wave":          "K453",
        "strategy":      "HL HIP-4 Prediction Market Trading Prototype",
        "run_time_jst":  datetime.now(JST).strftime("%Y-%m-%dT%H:%M JST"),
        "runtime_s":     round(time.time() - ts_start, 2),
        "data_summary": {
            "n_snapshots":      n_snaps,
            "span_days":        span_days,
            "total_rows":       len(df),
            "first_snapshot":   df["source_file"].iloc[0],
            "last_snapshot":    df["source_file"].iloc[-1],
        },
        "market_inventory":     inventory,
        "price_evolution":      price_evo,
        "btc_daily_binary":     btc_daily,
        "strategy_feasibility": strategies,
        "k266_gates":           gates,
        "profit_estimate":      profit,
        "recommendation":       rec,
    }

    # Save JSON
    out_json = REPO_ROOT / "wave_k453_hip4_prototype.json"
    with open(out_json, "w") as f:
        json.dump(output, f, indent=2, default=str)
    print(f"\n[OUTPUT] JSON saved: {out_json}", flush=True)

    # Print summary
    print("\n" + "=" * 72, flush=True)
    print("K453 SUMMARY", flush=True)
    print("=" * 72, flush=True)
    print(f"  Markets found:    {inventory['n_markets']}", flush=True)
    print(f"  Outcomes tracked: {len(price_evo['outcomes'])}", flush=True)
    print(f"  Strategies:       {len(strategies['strategies'])}", flush=True)
    print(f"  Gates passed now: {gates['gates_passed_now']}/{gates['gates_total']}", flush=True)
    print(f"  Verdict:          {rec['verdict']} / {rec['sub_verdict']}", flush=True)
    print(f"  Next milestone:   {rec['next_milestone']['wave']} ({rec['next_milestone']['target_date']})", flush=True)
    print("=" * 72, flush=True)

    return output


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""
scripts/hip4_prediction_prototype.py — HL HIP-4 Paper-Trade Scaffold
======================================================================
K453 deliverable: paper-trade observer for HL HIP-4 prediction markets.

PURPOSE
-------
This script is a PAPER-TRADE observer only. It does NOT place real orders.
It reads cached K356 snapshots, applies strategy logic, and outputs
paper-trade signals with Kelly-sized positions for post-K368 validation.

STRATEGIES IMPLEMENTED (paper only)
------------------------------------
  S4: Event trading — bet on near-expiry outcomes where P < 0.1 or P > 0.9
  S5: BTC daily binary — Kelly-sized paper bets based on distance from 0.5

PREREQUISITES
-------------
  - K356 polling daemon must be running (launchd plist)
  - At least 1 snapshot in cache/hl_hip4_snapshots/

OUTPUT
------
  - Stdout: paper-trade signal table
  - JSON: cache/hip4_paper_trades_<YYYYMMDD>.json  (accumulated)

USAGE
-----
  python3 scripts/hip4_prediction_prototype.py           # observe latest snapshot
  python3 scripts/hip4_prediction_prototype.py --all     # replay all snapshots
  python3 scripts/hip4_prediction_prototype.py --dry-run # print only, no JSON write

POST-K368 UPGRADE
-----------------
  After K368 calibration (target: 2026-06-22):
    1. Replace paper-bet flags with real order calls
    2. Add calibration-adjusted Kelly: f* = (P_true - P_HL) / (1 - P_HL) for Yes bets
    3. Add Brier score tracker per market type

Security (K339): REPO_ROOT pattern, no /Users/ literals.
"""
from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional

import pandas as pd
import numpy as np

# ---------------------------------------------------------------------------
# Paths — K339 security pattern
# ---------------------------------------------------------------------------
REPO_ROOT  = Path(__file__).resolve().parent.parent
CACHE_DIR  = REPO_ROOT / "cache" / "hl_hip4_snapshots"
PAPER_DIR  = REPO_ROOT / "cache" / "hip4_paper_trades"
LOGS_DIR   = REPO_ROOT / "logs"
JST        = timezone(timedelta(hours=9))

# ---------------------------------------------------------------------------
# Strategy parameters (conservative paper-trade defaults)
# ---------------------------------------------------------------------------

# S4: Event trading — bet when market is near-resolution with high confidence
S4_CONFIDENCE_THRESHOLD = 0.85   # P > 0.85 → implied YES; P < 0.15 → implied NO
S4_MAX_DAYS_TO_EXPIRY   = 2.0    # only bet on outcomes expiring within 2 days

# S5: BTC daily binary Kelly
S5_BANKROLL_USD         = 10_000.0  # paper bankroll per cycle
S5_KELLY_FRACTION       = 0.25      # 1/4 Kelly for safety
S5_MAX_BET_PCT          = 0.05      # max 5% of bankroll per single bet
S5_MIN_EDGE             = 0.10      # minimum |P - 0.5| to consider a bet

# Paper-trade metadata
PAPER_TRADE_VERSION     = "K453_scaffold_v1"
CALIBRATION_PENDING     = True      # flip to False after K368 confirms edge


# ---------------------------------------------------------------------------
# Load snapshot(s)
# ---------------------------------------------------------------------------

def load_latest_snapshot() -> pd.DataFrame:
    """Load the most recent full-schema parquet snapshot."""
    files = sorted(CACHE_DIR.glob("hip4_*.parquet"))
    if not files:
        raise FileNotFoundError(f"No snapshots in {CACHE_DIR}")

    # Find most recent full-schema snapshot
    for f in reversed(files):
        df = pd.read_parquet(f)
        if "question_name" in df.columns:
            return df

    raise ValueError("No full-schema snapshots found")


def load_all_snapshots() -> pd.DataFrame:
    """Load and concatenate all full-schema parquet snapshots."""
    files = sorted(CACHE_DIR.glob("hip4_*.parquet"))
    dfs = []
    for f in files:
        df = pd.read_parquet(f)
        if "question_name" in df.columns:
            df["source_file"] = f.name
            dfs.append(df)
    if not dfs:
        raise ValueError("No full-schema snapshots found")
    return pd.concat(dfs, ignore_index=True)


# ---------------------------------------------------------------------------
# BTC daily binary decoder
# ---------------------------------------------------------------------------

def decode_btc_binary_outcomes(df: pd.DataFrame) -> List[Dict]:
    """
    Extract all priceBinary|underlying:BTC outcomes with decoded expiry.
    Returns list sorted by expiry time (nearest first).
    """
    btc_rows = df[
        df["description"].fillna("").str.startswith("class:priceBinary|underlying:BTC")
    ].copy()

    decoded = []
    for _, row in btc_rows.iterrows():
        if row["side"] != 0:  # only Yes side
            continue
        desc = str(row["description"])
        parts = dict(kv.split(":", 1) for kv in desc.split("|") if ":" in kv)
        expiry_str = parts.get("expiry", "")
        try:
            expiry_dt = datetime.strptime(expiry_str, "%Y%m%d-%H%M").replace(tzinfo=timezone.utc)
        except ValueError:
            continue

        target_price = float(parts.get("targetPrice", 0))
        mid_price    = float(row["mid_price"]) if pd.notna(row["mid_price"]) else 0.5
        btc_mark     = float(row["btc_mark"])  if pd.notna(row["btc_mark"])  else None
        ts_utc       = datetime.fromtimestamp(row["ts_ms"] / 1000, tz=timezone.utc)
        hours_to_exp = (expiry_dt - ts_utc).total_seconds() / 3600

        decoded.append({
            "outcome_id":    int(row["outcome_id"]) if pd.notna(row["outcome_id"]) else None,
            "coin_key":      row["coin"],
            "expiry_dt":     expiry_dt,
            "expiry_str":    expiry_str,
            "target_price":  target_price,
            "mid_price_yes": mid_price,
            "btc_mark":      btc_mark,
            "hours_to_exp":  round(hours_to_exp, 2),
            "btc_vs_target": ("ABOVE" if btc_mark and btc_mark > target_price else "BELOW") if btc_mark else "UNKNOWN",
        })

    return sorted(decoded, key=lambda x: x["hours_to_exp"])


# ---------------------------------------------------------------------------
# Strategy S4: Event trading on near-resolution markets
# ---------------------------------------------------------------------------

def run_s4_event_trading(df: pd.DataFrame, snapshot_ts_ms: int) -> List[Dict]:
    """
    S4: identify near-expiry outcomes with high market confidence.
    Returns list of paper-trade signals.
    """
    snap_utc = datetime.fromtimestamp(snapshot_ts_ms / 1000, tz=timezone.utc)
    signals  = []

    for _, row in df.iterrows():
        if row["side"] != 0:  # Yes side only
            continue
        mid = float(row["mid_price"]) if pd.notna(row["mid_price"]) else 0.5
        resolved = bool(row["resolved"]) if pd.notna(row["resolved"]) else False

        if resolved:
            continue

        desc = str(row["description"]) if pd.notna(row["description"]) else ""

        # Decode expiry for priceBinary outcomes
        hours_to_exp = None
        if "expiry:" in desc:
            parts = dict(kv.split(":", 1) for kv in desc.split("|") if ":" in kv)
            expiry_str = parts.get("expiry", "")
            try:
                expiry_dt  = datetime.strptime(expiry_str, "%Y%m%d-%H%M").replace(tzinfo=timezone.utc)
                hours_to_exp = (expiry_dt - snap_utc).total_seconds() / 3600
            except ValueError:
                pass

        # S4 trigger: high confidence AND near expiry (if expiry known)
        if mid >= S4_CONFIDENCE_THRESHOLD:
            if hours_to_exp is None or hours_to_exp <= S4_MAX_DAYS_TO_EXPIRY * 24:
                signals.append({
                    "strategy":      "S4_event_trading",
                    "outcome_name":  row["outcome_name"],
                    "question_name": row["question_name"],
                    "coin_key":      row["coin"],
                    "mid_price":     round(mid, 4),
                    "signal":        "BET_YES",
                    "hours_to_exp":  round(hours_to_exp, 1) if hours_to_exp else None,
                    "confidence":    round(mid, 4),
                    "edge_est":      "UNKNOWN (pre-K368)",
                    "paper_notional_usd": 0.0,  # no sizing pre-K368
                    "reason":        f"P(Yes)={mid:.3f} >= {S4_CONFIDENCE_THRESHOLD}",
                    "status":        "PAPER_ONLY",
                })

        elif mid <= (1.0 - S4_CONFIDENCE_THRESHOLD):
            if hours_to_exp is None or hours_to_exp <= S4_MAX_DAYS_TO_EXPIRY * 24:
                signals.append({
                    "strategy":      "S4_event_trading",
                    "outcome_name":  row["outcome_name"],
                    "question_name": row["question_name"],
                    "coin_key":      row["coin"],
                    "mid_price":     round(mid, 4),
                    "signal":        "BET_NO",
                    "hours_to_exp":  round(hours_to_exp, 1) if hours_to_exp else None,
                    "confidence":    round(1.0 - mid, 4),
                    "edge_est":      "UNKNOWN (pre-K368)",
                    "paper_notional_usd": 0.0,
                    "reason":        f"P(Yes)={mid:.3f} <= {1-S4_CONFIDENCE_THRESHOLD:.3f}",
                    "status":        "PAPER_ONLY",
                })

    return signals


# ---------------------------------------------------------------------------
# Strategy S5: BTC daily binary — Kelly-sized paper bets
# ---------------------------------------------------------------------------

def run_s5_btc_kelly(btc_markets: List[Dict]) -> List[Dict]:
    """
    S5: Kelly-sized paper bets on BTC daily binary outcomes.
    Edge is assumed UNKNOWN pre-K368 — paper sizing only for tracking.

    Kelly formula (binary, calibrated):
      f* = (p_win - p_lose) / 1 = 2*p - 1  (for equal payoff)
    Pre-calibration: treat |mid - 0.5| as naive edge proxy.
    """
    signals = []

    for mkt in btc_markets:
        mid   = mkt["mid_price_yes"]
        edge  = abs(mid - 0.5)

        if edge < S5_MIN_EDGE:
            continue  # insufficient edge proxy

        # Naive Kelly fraction
        kelly_f       = min(edge * 2, 1.0)          # |2p - 1| = Kelly for equal-odds binary
        quarter_kelly = kelly_f * S5_KELLY_FRACTION
        bet_fraction  = min(quarter_kelly, S5_MAX_BET_PCT)
        paper_bet_usd = round(S5_BANKROLL_USD * bet_fraction, 2)

        direction = "BET_YES" if mid > 0.5 else "BET_NO"

        signals.append({
            "strategy":         "S5_btc_daily_kelly",
            "outcome_id":       mkt["outcome_id"],
            "coin_key":         mkt["coin_key"],
            "expiry_str":       mkt["expiry_str"],
            "hours_to_exp":     mkt["hours_to_exp"],
            "target_price":     mkt["target_price"],
            "btc_mark":         mkt["btc_mark"],
            "btc_vs_target":    mkt["btc_vs_target"],
            "mid_price_yes":    round(mid, 4),
            "edge_naive":       round(edge, 4),
            "kelly_full":       round(kelly_f, 4),
            "kelly_quarter":    round(quarter_kelly, 4),
            "bet_fraction":     round(bet_fraction, 4),
            "paper_bet_usd":    paper_bet_usd,
            "bankroll_usd":     S5_BANKROLL_USD,
            "signal":           direction,
            "edge_est":         "NAIVE (pre-K368: no calibration correction)",
            "calibration_flag": "PENDING_K368",
            "status":           "PAPER_ONLY",
            "note": (
                "Pre-calibration: edge is naive |P-0.5|. "
                "Post-K368: replace with (P_true - P_HL) calibration adjustment."
            ),
        })

    return signals


# ---------------------------------------------------------------------------
# Brier score accumulator (for resolved outcomes only)
# ---------------------------------------------------------------------------

def compute_brier_scores(df: pd.DataFrame) -> List[Dict]:
    """
    Compute Brier scores for any resolved outcomes in the snapshot history.
    Brier score = (P_predicted - O_realized)^2 where O = 1 if Yes resolved, 0 if No.
    Lower is better (perfect = 0, random = 0.25).
    """
    yes_side = df[df["side"] == 0].copy()
    resolved = yes_side[yes_side["resolved_outcome"].notna()].copy()

    if len(resolved) == 0:
        return []

    scores = []
    for _, row in resolved.iterrows():
        p_pred  = float(row["mid_price"]) if pd.notna(row["mid_price"]) else 0.5
        o_real  = float(row["resolved_outcome"]) if pd.notna(row["resolved_outcome"]) else None
        if o_real is None:
            continue

        brier = (p_pred - o_real) ** 2
        scores.append({
            "outcome_id":       int(row["outcome_id"]) if pd.notna(row["outcome_id"]) else None,
            "outcome_name":     row["outcome_name"],
            "question_name":    row["question_name"],
            "predicted_p_yes":  round(p_pred, 4),
            "resolved_yes":     int(o_real),
            "brier_score":      round(brier, 4),
            "ts_ms":            int(row["ts_ms"]),
        })

    return scores


# ---------------------------------------------------------------------------
# Main output builder
# ---------------------------------------------------------------------------

def build_paper_trade_report(
    df: pd.DataFrame,
    signals_s4: List[Dict],
    signals_s5: List[Dict],
    brier_scores: List[Dict],
    snap_ts_ms: int,
) -> Dict[str, Any]:
    """Assemble full paper-trade report dict."""
    snap_dt = datetime.fromtimestamp(snap_ts_ms / 1000, tz=JST)

    total_paper_notional = sum(s.get("paper_bet_usd", 0) for s in signals_s5)

    return {
        "version":           PAPER_TRADE_VERSION,
        "snapshot_ts_jst":   snap_dt.strftime("%Y-%m-%dT%H:%M JST"),
        "snapshot_ts_ms":    snap_ts_ms,
        "calibration_pending": CALIBRATION_PENDING,
        "calibration_target":  "K368 — 2026-06-22",
        "n_outcome_sides":     len(df),
        "s4_signals":          signals_s4,
        "s5_signals":          signals_s5,
        "brier_scores":        brier_scores,
        "paper_summary": {
            "n_s4_signals":          len(signals_s4),
            "n_s5_signals":          len(signals_s5),
            "s5_total_paper_bet_usd": round(total_paper_notional, 2),
            "n_brier_scores":        len(brier_scores),
            "mean_brier":            round(float(np.mean([b["brier_score"] for b in brier_scores])), 4) if brier_scores else None,
        },
        "warnings": [
            "ALL positions are PAPER ONLY — no real orders placed.",
            "Edge estimates are NAIVE (|P-0.5|) — not calibration-adjusted.",
            "Do NOT use for live trading until K368 calibration confirmed.",
        ] + (
            ["CALIBRATION PENDING: deploy after K368 (2026-06-22)"] if CALIBRATION_PENDING else []
        ),
    }


# ---------------------------------------------------------------------------
# Save paper trade log
# ---------------------------------------------------------------------------

def save_paper_trade_log(report: Dict, dry_run: bool = False) -> Optional[Path]:
    """Append paper trade report to daily JSON log."""
    date_str = datetime.now(JST).strftime("%Y%m%d")
    out_file = PAPER_DIR / f"hip4_paper_trades_{date_str}.json"

    if dry_run:
        print(f"  [DRY-RUN] Would append to {out_file}", flush=True)
        return None

    PAPER_DIR.mkdir(parents=True, exist_ok=True)

    # Load existing or start fresh
    if out_file.exists():
        with open(out_file) as f:
            existing = json.load(f)
    else:
        existing = {"date": date_str, "records": []}

    existing["records"].append(report)
    existing["last_updated"] = datetime.now(JST).strftime("%Y-%m-%dT%H:%M JST")
    existing["n_records"] = len(existing["records"])

    with open(out_file, "w") as f:
        json.dump(existing, f, indent=2, default=str)

    return out_file


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def main() -> None:
    parser = argparse.ArgumentParser(
        description="HL HIP-4 paper-trade scaffold (K453)"
    )
    parser.add_argument("--all", action="store_true",
                        help="Replay all cached snapshots (not just latest)")
    parser.add_argument("--dry-run", action="store_true",
                        help="Print signals only, do not write files")
    args = parser.parse_args()

    now_jst = datetime.now(JST).strftime("%Y-%m-%dT%H:%M JST")
    print(f"[{now_jst}] HL HIP-4 Paper-Trade Prototype ({PAPER_TRADE_VERSION})", flush=True)

    if CALIBRATION_PENDING:
        print("  [!] CALIBRATION PENDING — paper mode only (K368 target: 2026-06-22)", flush=True)

    # Load data
    if args.all:
        df = load_all_snapshots()
        snapshot_times = sorted(df["ts_ms"].unique())
        print(f"  Loaded {df['source_file'].nunique()} snapshots, {len(snapshot_times)} time points", flush=True)
    else:
        df = load_latest_snapshot()
        snapshot_times = [df["ts_ms"].max()]
        print(f"  Loaded latest snapshot: {snapshot_times[0]}", flush=True)

    # Process each snapshot time
    all_reports = []
    for snap_ts_ms in snapshot_times:
        snap_df = df[df["ts_ms"] == snap_ts_ms] if args.all else df

        # Decode BTC binary outcomes for this snapshot
        btc_markets = decode_btc_binary_outcomes(snap_df)

        # Run strategies
        signals_s4 = run_s4_event_trading(snap_df, snap_ts_ms)
        signals_s5 = run_s5_btc_kelly(btc_markets)

        # Brier scores (on resolved outcomes)
        brier_scores = compute_brier_scores(snap_df)

        # Build report
        report = build_paper_trade_report(
            snap_df, signals_s4, signals_s5, brier_scores, snap_ts_ms
        )
        all_reports.append(report)

        # Print signals
        snap_dt = datetime.fromtimestamp(snap_ts_ms / 1000, tz=JST)
        print(f"\n  === {snap_dt.strftime('%Y-%m-%dT%H:%M JST')} ===", flush=True)

        if signals_s4:
            print(f"  S4 Event Signals ({len(signals_s4)}):", flush=True)
            for s in signals_s4:
                exp_str = f" (exp {s['hours_to_exp']}h)" if s.get("hours_to_exp") else ""
                print(f"    {s['signal']:8} {s['outcome_name'][:30]:30} P={s['mid_price']:.3f}{exp_str}", flush=True)

        if signals_s5:
            print(f"  S5 BTC Binary Kelly ({len(signals_s5)}):", flush=True)
            for s in signals_s5:
                print(
                    f"    {s['signal']:8} target={s['target_price']:7.0f} "
                    f"P={s['mid_price_yes']:.3f} edge={s['edge_naive']:.3f} "
                    f"bet=${s['paper_bet_usd']:.0f} (paper)",
                    flush=True,
                )

        if brier_scores:
            mean_b = float(np.mean([b["brier_score"] for b in brier_scores]))
            print(f"  Brier scores: {len(brier_scores)} resolved, mean={mean_b:.4f}", flush=True)
        else:
            print(f"  Brier scores: 0 resolved outcomes yet", flush=True)

    # Save logs
    if not args.all:
        out = save_paper_trade_log(all_reports[-1], dry_run=args.dry_run)
        if out:
            print(f"\n  [SAVED] {out}", flush=True)

    print(f"\n[DONE] {len(all_reports)} snapshot(s) processed", flush=True)
    if CALIBRATION_PENDING:
        print(
            "\n[NOTE] Edge estimates are NAIVE. Deploy only after K368 calibration (2026-06-22).",
            flush=True,
        )


if __name__ == "__main__":
    main()

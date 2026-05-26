"""
HL HIP-4 Prediction Market Monitor — K353/K356 Scaffold
=========================================================
Purpose:
    Poll https://api.hyperliquid.xyz/info HIP-4 prediction market endpoints
    every 5 minutes (scheduled by launchd). Single-shot execution model.

    Each call:
      1. POST {"type":"outcomeMeta"} — get outcome list + resolution status
         Returns {"outcomes": [...], "questions": [...]}
         Outcome ID mapping: allMids key "#XXXX" where XXXX = outcome_id * 10 + side
         side 0 = Yes, side 1 = No
      2. POST {"type":"allMids"}     — get all prices (filter keys starting with '#')
      3. Top-3 markets by depth      — fetch l2Book for spread/depth metrics
      4. BTC mark price from allMids ('BTC' key) for daily-binary calibration
      5. Save snapshot to cache/hl_hip4_snapshots/hip4_<YYYYMMDD_HHMM>.parquet

On error: write to logs/hl_hip4_monitor.err, exit 0 (don't break launchd schedule)
Stdout: brief summary (timestamp, # markets, sample price)

K353 context: MONITOR verdict. 22 active outcomes, 11 markets.
K356 scaffold: 2-week data collection → K368 calibration analysis (target 2026-06-10).

Parquet schema (one row per outcome-side per snapshot):
  ts_ms            int64   — Unix milliseconds UTC
  coin             object  — '#XXXX' allMids key (e.g. '#1010')
  outcome_id       int64   — HL outcome integer id (e.g. 101)
  side             int64   — 0=Yes, 1=No
  outcome_name     object  — human label from outcomeMeta (e.g. 'Below 4.3%')
  question_name    object  — parent question (e.g. 'May CPI year-over-year')
  description      object  — full outcome description text
  mid_price        float64 — binary probability from allMids [0,1]
  resolved         bool    — whether outcome is resolved
  resolved_outcome int64   — 0/1 (Yes/No) if resolved, else NaN
  best_bid         float64 — top bid from l2Book (if fetched)
  best_ask         float64 — top ask from l2Book (if fetched)
  spread           float64 — ask - bid
  spread_pct       float64 — spread / best_bid * 100
  bid_depth_1pct   float64 — total bid qty within 1% of mid
  ask_depth_1pct   float64 — total ask qty within 1% of mid
  btc_mark         float64 — BTC mark price (for daily-binary calibration)

Usage:
    python3 scripts/hl_hip4_monitor.py            # single-shot (default)
    python3 scripts/hl_hip4_monitor.py --dry-run  # fetch + print, skip writes

Security (K339):
    REPO_ROOT = Path(__file__).resolve().parent.parent — no /Users/ literals in paths
"""
from __future__ import annotations

import argparse
import json
import sys
import time
import traceback
import urllib.request
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import pandas as pd

# ---------------------------------------------------------------------------
# Paths — K339 security: relative to REPO_ROOT, no hardcoded /Users/ literals
# ---------------------------------------------------------------------------
REPO_ROOT      = Path(__file__).resolve().parent.parent
CACHE_DIR      = REPO_ROOT / "cache" / "hl_hip4_snapshots"
LOGS_DIR       = REPO_ROOT / "logs"
ERR_FILE       = LOGS_DIR / "hl_hip4_monitor.err"

JST = timezone(timedelta(hours=9))

# ---------------------------------------------------------------------------
# HL API
# ---------------------------------------------------------------------------
HL_API = "https://api.hyperliquid.xyz/info"

# Top-N markets to fetch l2Book for depth/spread metrics
L2BOOK_TOP_N = 3


def hl_post(payload: dict, retries: int = 3, delay: float = 5.0) -> Any:
    """POST to HL info API with retry and exponential back-off."""
    for attempt in range(retries):
        try:
            body = json.dumps(payload).encode()
            req  = urllib.request.Request(
                HL_API, data=body,
                headers={
                    "Content-Type": "application/json",
                    "User-Agent": "ct-hip4-monitor/1.0",
                }
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


# ---------------------------------------------------------------------------
# Step 1: outcomeMeta — outcome list + resolution status
# ---------------------------------------------------------------------------

def fetch_outcome_meta() -> Tuple[List[Dict], List[Dict]]:
    """
    POST {"type":"outcomeMeta"} to HL.
    Returns (outcomes_list, questions_list).

    Response structure:
        {
          "outcomes": [
            {"outcome": 100, "name": "Fallback", "description": "", "sideSpecs": [...], ...},
            {"outcome": 101, "name": "Below 4.3%", ...},
            ...
          ],
          "questions": [
            {"question": 19, "name": "May CPI year-over-year", "fallbackOutcome": 100,
             "namedOutcomes": [101, 102, 103], "settledNamedOutcomes": []},
            ...
          ]
        }

    allMids key mapping:
        '#XXXX' where XXXX = outcome_id * 10 + side_index
        side_index 0 = sideSpecs[0] = "Yes"
        side_index 1 = sideSpecs[1] = "No"
    """
    raw = hl_post({"type": "outcomeMeta"})
    if isinstance(raw, dict):
        outcomes  = raw.get("outcomes", [])
        questions = raw.get("questions", [])
    elif isinstance(raw, list):
        outcomes  = raw
        questions = []
    else:
        outcomes, questions = [], []
    return outcomes, questions


def build_outcome_index(outcomes: List[Dict], questions: List[Dict]) -> Dict[str, Dict]:
    """
    Build a lookup dict: '#XXXX' coin key → enriched outcome metadata.
    Covers both sides (Yes=0, No=1) for each outcome.

    Returns dict keyed by coin e.g. '#1010': {
        'outcome_id': 101, 'side': 0, 'outcome_name': 'Below 4.3%',
        'question_name': 'May CPI year-over-year', 'description': '...',
        'resolved': False, 'resolved_outcome': None
    }
    """
    # Build question name lookup: fallback/named outcome_id -> question name
    question_of: Dict[int, str] = {}
    for q in questions:
        q_name = q.get("name", "")
        for oid in q.get("namedOutcomes", []):
            question_of[oid] = q_name
        fb = q.get("fallbackOutcome")
        if fb is not None:
            question_of[fb] = q_name

    index: Dict[str, Dict] = {}
    for o in outcomes:
        oid       = o.get("outcome")
        if oid is None:
            continue
        name      = o.get("name", "")
        desc      = o.get("description", "")
        resolved  = o.get("resolved") or o.get("isResolved") or False
        res_out   = o.get("resolvedOutcome")
        side_specs = o.get("sideSpecs", [{"name": "Yes"}, {"name": "No"}])
        q_name    = question_of.get(oid, "")

        # Map each side to allMids coin key
        for side_idx, side_spec in enumerate(side_specs):
            coin_key = f"#{oid * 10 + side_idx}"
            index[coin_key] = {
                "outcome_id":       oid,
                "side":             side_idx,
                "side_name":        side_spec.get("name", str(side_idx)),
                "outcome_name":     name,
                "question_name":    q_name,
                "description":      desc,
                "resolved":         bool(resolved),
                "resolved_outcome": int(res_out) if res_out is not None else None,
            }

    return index


# ---------------------------------------------------------------------------
# Step 2: allMids — prices for '#' keys + BTC mark
# ---------------------------------------------------------------------------

def fetch_all_mids() -> Dict[str, float]:
    """
    POST {"type":"allMids"} and return dict of coin -> mid_price.
    Keeps ALL keys (including '#'-prefixed HIP-4 outcomes and 'BTC').
    """
    raw = hl_post({"type": "allMids"})
    result: Dict[str, float] = {}
    if isinstance(raw, dict):
        for k, v in raw.items():
            try:
                result[k] = float(v)
            except (TypeError, ValueError):
                pass
    return result


def extract_hip4_mids(all_mids: Dict[str, float]) -> Dict[str, float]:
    """Filter allMids to only HIP-4 prediction market outcomes (keys starting with '#')."""
    return {k: v for k, v in all_mids.items() if k.startswith("#")}


# ---------------------------------------------------------------------------
# Step 3: l2Book — spread / depth for top-N markets
# ---------------------------------------------------------------------------

def fetch_l2_book(coin: str) -> Optional[Dict]:
    """
    POST {"type":"l2Book","coin": coin} and return parsed book summary.
    Returns dict with: best_bid, best_ask, spread, bid_depth_1pct, ask_depth_1pct
    or None on failure.
    """
    try:
        raw = hl_post({"type": "l2Book", "coin": coin})
        # raw expected: {"levels": [[bids], [asks]]} where each level is [price, size, ...]
        levels = raw.get("levels") if isinstance(raw, dict) else None
        if not levels or len(levels) < 2:
            return None

        bids = levels[0]  # [[price, size], ...]
        asks = levels[1]

        if not bids or not asks:
            return None

        best_bid = float(bids[0][0]) if bids else None
        best_ask = float(asks[0][0]) if asks else None
        spread   = (best_ask - best_bid) if (best_bid and best_ask) else None
        spread_pct = (spread / best_bid * 100) if (spread and best_bid) else None

        # Depth within 1% of mid
        mid = (best_bid + best_ask) / 2 if (best_bid and best_ask) else None
        bid_depth_1pct = None
        ask_depth_1pct = None
        if mid:
            bid_cutoff = mid * 0.99
            ask_cutoff = mid * 1.01
            bid_depth_1pct = sum(
                float(lvl[1]) for lvl in bids if float(lvl[0]) >= bid_cutoff
            )
            ask_depth_1pct = sum(
                float(lvl[1]) for lvl in asks if float(lvl[0]) <= ask_cutoff
            )

        return {
            "coin":            coin,
            "best_bid":        best_bid,
            "best_ask":        best_ask,
            "spread":          round(spread, 6) if spread else None,
            "spread_pct":      round(spread_pct, 4) if spread_pct else None,
            "bid_depth_1pct":  round(bid_depth_1pct, 4) if bid_depth_1pct else None,
            "ask_depth_1pct":  round(ask_depth_1pct, 4) if ask_depth_1pct else None,
        }
    except Exception as exc:
        print(f"  [WARN] l2Book fetch failed for {coin}: {exc}", flush=True)
        return None


# ---------------------------------------------------------------------------
# Snapshot construction
# ---------------------------------------------------------------------------

def build_snapshot_rows(
    outcome_index: Dict[str, Dict],
    hip4_mids:    Dict[str, float],
    btc_price:    Optional[float],
    l2_books:     List[Dict],
    ts_ms:        int,
) -> List[Dict]:
    """
    Merge outcomeMeta index + allMids (HIP-4) + l2Book depth data into tabular rows.
    One row per outcome-side (coin key).
    """
    # Index l2book by coin for fast lookup
    l2_idx: Dict[str, Dict] = {b["coin"]: b for b in l2_books if b}

    # Union of all known coin keys
    all_coins = set(outcome_index.keys()) | set(hip4_mids.keys())

    rows = []
    for coin_key in sorted(all_coins):
        meta      = outcome_index.get(coin_key, {})
        mid_price = hip4_mids.get(coin_key)
        l2        = l2_idx.get(coin_key, {})

        rows.append({
            "ts_ms":            ts_ms,
            "coin":             coin_key,
            "outcome_id":       meta.get("outcome_id"),
            "side":             meta.get("side"),
            "side_name":        meta.get("side_name"),
            "outcome_name":     meta.get("outcome_name"),
            "question_name":    meta.get("question_name"),
            "description":      meta.get("description"),
            "mid_price":        mid_price,
            "resolved":         meta.get("resolved"),
            "resolved_outcome": meta.get("resolved_outcome"),
            "best_bid":         l2.get("best_bid"),
            "best_ask":         l2.get("best_ask"),
            "spread":           l2.get("spread"),
            "spread_pct":       l2.get("spread_pct"),
            "bid_depth_1pct":   l2.get("bid_depth_1pct"),
            "ask_depth_1pct":   l2.get("ask_depth_1pct"),
            "btc_mark":         btc_price,
        })

    return rows


def save_snapshot(rows: List[Dict], ts_ms: int, dry_run: bool = False) -> Optional[Path]:
    """
    Save rows to parquet at cache/hl_hip4_snapshots/hip4_<YYYYMMDD_HHMM>.parquet.
    Returns path or None if dry_run.
    """
    dt  = datetime.fromtimestamp(ts_ms / 1000, tz=timezone.utc)
    fn  = f"hip4_{dt.strftime('%Y%m%d_%H%M')}.parquet"
    out = CACHE_DIR / fn

    if dry_run:
        print(f"  [DRY-RUN] Would write {len(rows)} rows → {out}", flush=True)
        return None

    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    df = pd.DataFrame(rows)

    # Enforce dtypes for stable parquet schema
    if "ts_ms" in df.columns:
        df["ts_ms"] = df["ts_ms"].astype("int64")
    for float_col in ["mid_price", "best_bid", "best_ask", "spread",
                       "spread_pct", "bid_depth_1pct", "ask_depth_1pct", "btc_mark"]:
        if float_col in df.columns:
            df[float_col] = pd.to_numeric(df[float_col], errors="coerce").astype("float64")
    for int_col in ["outcome_id", "side", "resolved_outcome"]:
        if int_col in df.columns:
            df[int_col] = pd.to_numeric(df[int_col], errors="coerce")

    df.to_parquet(out, index=False, compression="snappy")
    return out


# ---------------------------------------------------------------------------
# Main single-shot run
# ---------------------------------------------------------------------------

def run_once(dry_run: bool = False) -> None:
    ts_ms  = int(time.time() * 1000)
    dt_str = datetime.fromtimestamp(ts_ms / 1000, tz=JST).strftime("%Y-%m-%dT%H:%M JST")

    print(f"[{dt_str}] HL HIP-4 Monitor — poll cycle start", flush=True)

    # Step 1: outcomeMeta
    print("  [1] Fetching outcomeMeta...", flush=True)
    outcomes, questions = fetch_outcome_meta()
    outcome_index = build_outcome_index(outcomes, questions)
    n_active = sum(1 for o in outcomes if not o.get("resolved"))
    print(f"      {len(outcomes)} outcomes, {len(questions)} questions, "
          f"{n_active} unresolved, {len(outcome_index)} coin-side pairs mapped", flush=True)

    # Step 2: allMids
    print("  [2] Fetching allMids...", flush=True)
    all_mids  = fetch_all_mids()
    hip4_mids = extract_hip4_mids(all_mids)
    btc_price = all_mids.get("BTC")
    print(f"      {len(hip4_mids)} HIP-4 mid prices, BTC mark={btc_price}", flush=True)

    # Step 3: l2Book for top-N markets closest to p=0.5 (most uncertain / most liquid)
    top_coins: List[str] = []
    if hip4_mids:
        sorted_coins = sorted(
            hip4_mids.keys(),
            key=lambda c: abs(hip4_mids[c] - 0.5)  # closest to 0.5 = most uncertain
        )
        top_coins = sorted_coins[:L2BOOK_TOP_N]

    l2_books: List[Dict] = []
    if top_coins:
        print(f"  [3] Fetching l2Book for top {len(top_coins)} markets: {top_coins}", flush=True)
        for coin in top_coins:
            book = fetch_l2_book(coin)
            if book:
                l2_books.append(book)
                print(f"      {coin}: bid={book['best_bid']} ask={book['best_ask']} "
                      f"spread_pct={book['spread_pct']}%", flush=True)
            else:
                print(f"      {coin}: no l2Book data", flush=True)
    else:
        print("  [3] No HIP-4 mids available — skipping l2Book", flush=True)

    # Step 4: Build rows and save
    print("  [4] Building snapshot rows...", flush=True)
    rows = build_snapshot_rows(outcome_index, hip4_mids, btc_price, l2_books, ts_ms)
    print(f"      {len(rows)} rows constructed", flush=True)

    print("  [5] Saving parquet snapshot...", flush=True)
    out = save_snapshot(rows, ts_ms, dry_run=dry_run)
    if out:
        size_kb = out.stat().st_size // 1024
        print(f"      Saved: {out} ({size_kb}KB, {len(rows)} rows)", flush=True)

    # Brief summary line — log a few sample probabilities for a sanity check
    sample_prices: List[str] = []
    for coin_key, price in list(hip4_mids.items())[:3]:
        meta = outcome_index.get(coin_key, {})
        label = meta.get("outcome_name", coin_key)
        sample_prices.append(f"{label}({coin_key})={price:.3f}")

    print(
        f"[SUMMARY] {dt_str} | outcomes={len(outcomes)} | hip4_mids={len(hip4_mids)} "
        f"| btc_mark={btc_price} | samples: {', '.join(sample_prices)}",
        flush=True,
    )


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def main() -> None:
    parser = argparse.ArgumentParser(
        description="HL HIP-4 prediction market monitor (K353/K356 scaffold)"
    )
    parser.add_argument(
        "--dry-run", action="store_true",
        help="Fetch and log but do not write any files"
    )
    args = parser.parse_args()

    # Ensure directories exist
    LOGS_DIR.mkdir(parents=True, exist_ok=True)
    if not args.dry_run:
        CACHE_DIR.mkdir(parents=True, exist_ok=True)

    try:
        run_once(dry_run=args.dry_run)
    except Exception:
        # On any unhandled error: write to err file and exit 0 (don't break launchd)
        err_msg  = traceback.format_exc()
        ts_str   = datetime.now(JST).strftime("%Y-%m-%dT%H:%M JST")
        err_line = f"[{ts_str}] FATAL ERROR:\n{err_msg}\n"
        print(err_line, file=sys.stderr, flush=True)
        try:
            LOGS_DIR.mkdir(parents=True, exist_ok=True)
            with open(ERR_FILE, "a") as fh:
                fh.write(err_line)
        except Exception:
            pass
        sys.exit(0)  # exit 0 to avoid launchd throttling


if __name__ == "__main__":
    main()

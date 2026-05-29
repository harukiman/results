#!/usr/bin/env python3
"""
depth_aware_allocator.py — K458 Depth-Aware Cross-Venue Allocator (v6.20 Phase 5)
====================================================================================
Rescues strategy from negative slippage at $100M+ AUM by distributing target
positions across venues proportional to their per-venue OI depth capacity.

K454 finding: linear AUM scaling → quadratic slippage if not distributed.
K458 solution: respect per-venue OI depth caps (5% max per venue), smart routing,
               greedy allocation, and graceful target reduction.

Architecture:
  Phase 1  fetch_venue_depth(venue, symbol)         → live OI + book depth
  Phase 2  compute_max_position_per_venue(...)       → 5% of OI cap
  Phase 3  distribute_target(symbol, target, venues) → greedy allocation
  Phase 4  validate_allocation(alloc, slip_est)      → slippage < threshold
  Phase 5  recommend_reduce(target, achievable)       → reduce if over-capacity
  Phase 6  K439 integration: POST_ONLY submission scaffold per venue
  Phase 7  Dashboard + decision log

Venues (live):    HL, Bybit, OKX
Venues (mocked):  Drift (paused R14-05 hack), Aevo (future), dYdX v4 (future)

Usage:
  python3 scripts/depth_aware_allocator.py --dry-run --aum 100000000
  python3 scripts/depth_aware_allocator.py --symbol BTC --target 20000000
  python3 scripts/depth_aware_allocator.py --symbol SOL --target 5000000 --dry-run

K339 security: REPO_ROOT from __file__, no /Users/ literals.
Scaffold only: no actual order execution. DO NOT modify K280/K297 production logic.
"""
from __future__ import annotations

import argparse
import json
import math
import sys
import time
import warnings
import urllib.error
import urllib.request
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Tuple

# ── K339 canonical paths ──────────────────────────────────────────────────────
REPO_ROOT  = Path(__file__).resolve().parent.parent
DATA_DIR   = REPO_ROOT / "data"
LOGS_DIR   = REPO_ROOT / "logs"
CACHE_DIR  = REPO_ROOT / "cache"

DATA_DIR.mkdir(exist_ok=True)
LOGS_DIR.mkdir(exist_ok=True)
CACHE_DIR.mkdir(exist_ok=True)

DASHBOARD_PATH    = DATA_DIR / "depth_allocator_dashboard.json"
DECISION_LOG_PATH = DATA_DIR / "depth_allocator_decisions.jsonl"

JST = timezone(timedelta(hours=9))

# ── Venue endpoints (K434 / K456 pattern) ─────────────────────────────────────
HL_API_URL       = "https://api.hyperliquid.xyz/info"
BYBIT_OB_URL     = "https://api.bybit.com/v5/market/orderbook"
BYBIT_TICKER_URL = "https://api.bybit.com/v5/market/tickers"
OKX_BOOKS_URL    = "https://www.okx.com/api/v5/market/books"
OKX_OI_URL       = "https://www.okx.com/api/v5/public/open-interest"

# ── Per-venue depth configuration ─────────────────────────────────────────────
VENUE_CONFIG: Dict[str, dict] = {
    "HL": {
        "enabled":          True,
        "max_pct_of_oi":    0.05,   # 5% of OI cap
        "min_depth_usd":    500_000,
        "slippage_bps_per_pct_of_oi": 10.0,  # 10 bps per 1% of OI
        "maker_rebate_bps": 0.3,
        "taker_fee_bps":    4.5,
    },
    "Bybit": {
        "enabled":          True,
        "max_pct_of_oi":    0.05,
        "min_depth_usd":    500_000,
        "slippage_bps_per_pct_of_oi": 8.0,
        "maker_rebate_bps": 1.0,
        "taker_fee_bps":    3.2,
    },
    "OKX": {
        "enabled":          True,
        "max_pct_of_oi":    0.05,
        "min_depth_usd":    500_000,
        "slippage_bps_per_pct_of_oi": 9.0,
        "maker_rebate_bps": 0.5,
        "taker_fee_bps":    4.0,
    },
    "Drift": {
        "enabled":  False,  # paused since R14-05 hack
        "max_pct_of_oi": 0.05,
        "min_depth_usd": 100_000,
        "slippage_bps_per_pct_of_oi": 20.0,
        "maker_rebate_bps": 0.0,
        "taker_fee_bps": 5.0,
    },
    "Aevo": {
        "enabled":  False,  # future scaffold
        "max_pct_of_oi": 0.05,
        "min_depth_usd": 100_000,
        "slippage_bps_per_pct_of_oi": 15.0,
        "maker_rebate_bps": 0.0,
        "taker_fee_bps": 5.0,
    },
    "dYdX_v4": {
        "enabled":  False,  # future scaffold
        "max_pct_of_oi": 0.05,
        "min_depth_usd": 100_000,
        "slippage_bps_per_pct_of_oi": 12.0,
        "maker_rebate_bps": 0.0,
        "taker_fee_bps": 5.0,
    },
}

# ── Active venues (enabled=True) ──────────────────────────────────────────────
ACTIVE_VENUES = [v for v, c in VENUE_CONFIG.items() if c["enabled"]]

# ── Global slippage threshold (bps) ───────────────────────────────────────────
MAX_TOTAL_SLIPPAGE_BPS = 20.0   # allocation rejected if total estimated slip > 20 bps

# ── Bybit/HL ticker maps (K434 pattern) ───────────────────────────────────────
BYBIT_TICKER_MAP: Dict[str, str] = {
    "BONK": "1000BONK", "PEPE": "1000PEPE", "MEME": "1000MEME",
    "SHIB": "1000SHIB", "BOME": "1000BOME",
}
HL_TICKER_MAP: Dict[str, str] = {
    "PEPE": "kPEPE", "BONK": "kBONK", "MEME": "kMEME", "BOME": "kBOME",
}

# ── $100M simulation symbols ───────────────────────────────────────────────────
SIM_SYMBOLS = ["BTC", "ETH", "SOL", "XRP", "SUI", "OP", "APT", "AXS", "JTO", "IMX"]

# ── Estimated OI baselines (USD) for dry-run when API unavailable ──────────────
# Source: K456 research + public data 2026-05
FALLBACK_OI_USD: Dict[str, Dict[str, float]] = {
    "BTC":  {"HL": 800_000_000, "Bybit": 1_200_000_000, "OKX": 900_000_000},
    "ETH":  {"HL": 400_000_000, "Bybit": 600_000_000,   "OKX": 500_000_000},
    "SOL":  {"HL": 200_000_000, "Bybit": 300_000_000,   "OKX": 250_000_000},
    "XRP":  {"HL": 80_000_000,  "Bybit": 150_000_000,   "OKX": 120_000_000},
    "SUI":  {"HL": 60_000_000,  "Bybit": 90_000_000,    "OKX": 70_000_000},
    "OP":   {"HL": 30_000_000,  "Bybit": 50_000_000,    "OKX": 40_000_000},
    "APT":  {"HL": 25_000_000,  "Bybit": 40_000_000,    "OKX": 35_000_000},
    "AXS":  {"HL": 15_000_000,  "Bybit": 25_000_000,    "OKX": 20_000_000},
    "JTO":  {"HL": 20_000_000,  "Bybit": 35_000_000,    "OKX": 25_000_000},
    "IMX":  {"HL": 18_000_000,  "Bybit": 30_000_000,    "OKX": 22_000_000},
    "SAND": {"HL": 12_000_000,  "Bybit": 20_000_000,    "OKX": 15_000_000},
    "ADA":  {"HL": 40_000_000,  "Bybit": 80_000_000,    "OKX": 60_000_000},
    "DOGE": {"HL": 50_000_000,  "Bybit": 100_000_000,   "OKX": 80_000_000},
    "AVAX": {"HL": 45_000_000,  "Bybit": 80_000_000,    "OKX": 65_000_000},
    "LINK": {"HL": 35_000_000,  "Bybit": 60_000_000,    "OKX": 50_000_000},
}


# ─────────────────────────────────────────────────────────────────────────────
# HTTP helpers (stdlib urllib — no requests; K339 pattern from K434)
# ─────────────────────────────────────────────────────────────────────────────

def _http_get(url: str, timeout: int = 10) -> Optional[dict]:
    try:
        req = urllib.request.Request(
            url,
            headers={"User-Agent": "crypto-lab-depth-allocator/1.0"},
        )
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return json.loads(resp.read().decode())
    except Exception as e:
        print(f"  [http_get] {url[:70]} → {e}", file=sys.stderr)
        return None


def _http_post(url: str, payload: dict, timeout: int = 10) -> Optional[dict]:
    try:
        data = json.dumps(payload).encode()
        req  = urllib.request.Request(
            url, data=data,
            headers={
                "Content-Type": "application/json",
                "User-Agent": "crypto-lab-depth-allocator/1.0",
            },
        )
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return json.loads(resp.read().decode())
    except Exception as e:
        print(f"  [http_post] {url[:70]} → {e}", file=sys.stderr)
        return None


# ─────────────────────────────────────────────────────────────────────────────
# Phase 1: Per-venue depth fetch
# ─────────────────────────────────────────────────────────────────────────────

def fetch_hl_depth(symbol: str) -> dict:
    """
    Fetch HL OI + L2 book depth for a single symbol.
    POST /info {"type":"l2Book","coin":"BTC"} → top-of-book depth
    POST /info {"type":"metaAndAssetCtxs"}    → OI + mark price
    Returns: {"oi_usd": float, "bid_depth_usd": float, "ask_depth_usd": float,
              "mark_px": float, "source": str}
    """
    result: dict = {"oi_usd": 0.0, "bid_depth_usd": 0.0, "ask_depth_usd": 0.0,
                    "mark_px": 0.0, "source": "HL"}

    # Step 1: Get OI and mark price from metaAndAssetCtxs
    meta_raw = _http_post(HL_API_URL, {"type": "metaAndAssetCtxs"})
    if meta_raw and isinstance(meta_raw, list) and len(meta_raw) >= 2:
        hl_sym   = HL_TICKER_MAP.get(symbol, symbol)
        universe = {item["name"]: i for i, item in enumerate(meta_raw[0].get("universe", []))}
        if hl_sym in universe:
            ctx = meta_raw[1][universe[hl_sym]]
            try:
                mark_px  = float(ctx.get("markPx", 0.0))
                oi_coins = float(ctx.get("openInterest", 0.0))
                result["mark_px"] = mark_px
                result["oi_usd"]  = oi_coins * mark_px
            except (TypeError, ValueError):
                pass

    # Step 2: Get L2 book depth (top 50 levels)
    hl_sym = HL_TICKER_MAP.get(symbol, symbol)
    book_raw = _http_post(HL_API_URL, {"type": "l2Book", "coin": hl_sym})
    if book_raw and "levels" in book_raw:
        try:
            levels  = book_raw["levels"]  # [bids_list, asks_list]
            bids    = levels[0] if len(levels) > 0 else []
            asks    = levels[1] if len(levels) > 1 else []
            mark_px = result["mark_px"] or 1.0

            bid_depth = sum(float(b.get("sz", 0)) * float(b.get("px", 0)) for b in bids[:50])
            ask_depth = sum(float(a.get("sz", 0)) * float(a.get("px", 0)) for a in asks[:50])
            result["bid_depth_usd"] = bid_depth
            result["ask_depth_usd"] = ask_depth
        except (TypeError, ValueError, KeyError, IndexError):
            pass

    # If OI available but book not, proxy depth = 1% of OI (K434 pattern)
    if result["oi_usd"] > 0 and result["bid_depth_usd"] == 0:
        result["bid_depth_usd"] = result["oi_usd"] * 0.01
        result["ask_depth_usd"] = result["oi_usd"] * 0.01

    return result


def fetch_bybit_depth(symbol: str) -> dict:
    """
    Fetch Bybit order book depth + OI for a symbol.
    GET /v5/market/orderbook?symbol=BTCUSDT&limit=50 → depth
    GET /v5/market/tickers?category=linear → OI estimate via volume
    Returns: {"oi_usd": float, "bid_depth_usd": float, "ask_depth_usd": float,
              "mark_px": float, "source": str}
    """
    result: dict = {"oi_usd": 0.0, "bid_depth_usd": 0.0, "ask_depth_usd": 0.0,
                    "mark_px": 0.0, "source": "Bybit"}

    bybit_sym = BYBIT_TICKER_MAP.get(symbol, symbol) + "USDT"

    # Order book
    ob_raw = _http_get(f"{BYBIT_OB_URL}?category=linear&symbol={bybit_sym}&limit=50")
    if ob_raw and ob_raw.get("retCode") == 0:
        ob_data = ob_raw.get("result", {})
        try:
            bids = ob_data.get("b", [])  # [[price, size], ...]
            asks = ob_data.get("a", [])
            bid_depth = sum(float(b[0]) * float(b[1]) for b in bids)
            ask_depth = sum(float(a[0]) * float(a[1]) for a in asks)
            result["bid_depth_usd"] = bid_depth
            result["ask_depth_usd"] = ask_depth
        except (TypeError, ValueError, IndexError):
            pass

    # Mark price + OI from tickers
    ticker_raw = _http_get(f"{BYBIT_TICKER_URL}?category=linear&symbol={bybit_sym}")
    if ticker_raw and ticker_raw.get("retCode") == 0:
        items = ticker_raw.get("result", {}).get("list", [])
        if items:
            item = items[0]
            try:
                mark_px = float(item.get("markPrice", 0.0) or 0.0)
                oi_usd  = float(item.get("openInterestValue", 0.0) or 0.0)
                result["mark_px"] = mark_px
                result["oi_usd"]  = oi_usd
            except (TypeError, ValueError):
                pass

    # Proxy depth from OI if book failed
    if result["oi_usd"] > 0 and result["bid_depth_usd"] == 0:
        result["bid_depth_usd"] = result["oi_usd"] * 0.01
        result["ask_depth_usd"] = result["oi_usd"] * 0.01

    return result


def fetch_okx_depth(symbol: str) -> dict:
    """
    Fetch OKX order book depth + OI for a symbol.
    GET /api/v5/market/books?instId=BTC-USDT-SWAP&sz=50 → depth
    GET /api/v5/public/open-interest?instId=BTC-USDT-SWAP → OI
    Returns: {"oi_usd": float, "bid_depth_usd": float, "ask_depth_usd": float,
              "mark_px": float, "source": str}
    """
    result: dict = {"oi_usd": 0.0, "bid_depth_usd": 0.0, "ask_depth_usd": 0.0,
                    "mark_px": 0.0, "source": "OKX"}

    inst_id = f"{symbol}-USDT-SWAP"

    # Order book (sz=50 → 50 levels each side)
    book_raw = _http_get(f"{OKX_BOOKS_URL}?instId={inst_id}&sz=50")
    if book_raw and book_raw.get("code") == "0":
        data = book_raw.get("data", [])
        if data:
            try:
                bids = data[0].get("bids", [])   # [[price, size, ?, numOrders], ...]
                asks = data[0].get("asks", [])
                bid_depth = sum(float(b[0]) * float(b[1]) for b in bids)
                ask_depth = sum(float(a[0]) * float(a[1]) for a in asks)
                result["bid_depth_usd"] = bid_depth
                result["ask_depth_usd"] = ask_depth
            except (TypeError, ValueError, IndexError):
                pass

    # OI
    oi_raw = _http_get(f"{OKX_OI_URL}?instId={inst_id}&instType=SWAP")
    if oi_raw and oi_raw.get("code") == "0":
        data = oi_raw.get("data", [])
        if data:
            try:
                oi_ccy  = float(data[0].get("oiCcy", 0.0) or 0.0)   # in base ccy
                # oi in USD = oi_ccy * mark_px (use bid_depth proxy if mark unknown)
                # approximation: oi USD from openInterestUsd if available
                oi_usd  = float(data[0].get("oiUsd", 0.0) or 0.0)
                if oi_usd == 0 and oi_ccy > 0:
                    # Fallback: estimate from depth if mark price unknown
                    oi_usd = oi_ccy * 1.0   # placeholder; refined if mark_px available
                result["oi_usd"] = oi_usd
            except (TypeError, ValueError):
                pass

    # Proxy depth from OI if book failed
    if result["oi_usd"] > 0 and result["bid_depth_usd"] == 0:
        result["bid_depth_usd"] = result["oi_usd"] * 0.01
        result["ask_depth_usd"] = result["oi_usd"] * 0.01

    return result


def fetch_drift_depth(symbol: str) -> dict:
    """Drift is paused since R14-05 hack. Return mocked depth."""
    return {
        "oi_usd":         0.0,
        "bid_depth_usd":  0.0,
        "ask_depth_usd":  0.0,
        "mark_px":        0.0,
        "source":         "Drift_MOCKED_PAUSED",
        "note":           "Drift paused since R14-05 hack",
    }


def fetch_aevo_depth(symbol: str) -> dict:
    """Aevo: future scaffold. Mocked."""
    return {
        "oi_usd":        0.0,
        "bid_depth_usd": 0.0,
        "ask_depth_usd": 0.0,
        "mark_px":       0.0,
        "source":        "Aevo_SCAFFOLD",
        "note":          "Aevo: future integration",
    }


def fetch_dydx_v4_depth(symbol: str) -> dict:
    """dYdX v4: future scaffold. Mocked."""
    return {
        "oi_usd":        0.0,
        "bid_depth_usd": 0.0,
        "ask_depth_usd": 0.0,
        "mark_px":       0.0,
        "source":        "dYdX_v4_SCAFFOLD",
        "note":          "dYdX v4: future integration",
    }


VENUE_FETCHERS = {
    "HL":     fetch_hl_depth,
    "Bybit":  fetch_bybit_depth,
    "OKX":    fetch_okx_depth,
    "Drift":  fetch_drift_depth,
    "Aevo":   fetch_aevo_depth,
    "dYdX_v4": fetch_dydx_v4_depth,
}


def fetch_venue_depth(venue: str, symbol: str) -> dict:
    """
    Fetch current OI + best bid/ask depth for a venue/symbol pair.

    Returns:
        {
          "oi_usd":         float,  # total open interest in USD
          "bid_depth_usd":  float,  # top-50 bid side depth (USD notional)
          "ask_depth_usd":  float,  # top-50 ask side depth (USD notional)
          "book_depth_usd": float,  # min(bid, ask) — conservative side
          "mark_px":        float,
          "source":         str,
          "fetched_at_jst": str,
        }
    """
    fetcher = VENUE_FETCHERS.get(venue)
    if fetcher is None:
        return {"oi_usd": 0.0, "bid_depth_usd": 0.0, "ask_depth_usd": 0.0,
                "book_depth_usd": 0.0, "mark_px": 0.0, "source": f"{venue}_UNKNOWN"}

    raw = fetcher(symbol)
    raw["book_depth_usd"] = min(raw.get("bid_depth_usd", 0.0), raw.get("ask_depth_usd", 0.0))
    raw["fetched_at_jst"] = datetime.now(JST).strftime("%Y-%m-%d %H:%M JST")

    # If OI is zero but we have fallback estimates, use them
    if raw["oi_usd"] == 0.0:
        fallback = FALLBACK_OI_USD.get(symbol, {})
        if venue in fallback:
            raw["oi_usd"] = fallback[venue]
            raw["source"] += "_OI_FALLBACK"
            # Also proxy depth if missing
            if raw["bid_depth_usd"] == 0.0:
                raw["bid_depth_usd"] = raw["oi_usd"] * 0.01
                raw["ask_depth_usd"] = raw["oi_usd"] * 0.01
                raw["book_depth_usd"] = raw["oi_usd"] * 0.01

    return raw


# ─────────────────────────────────────────────────────────────────────────────
# Phase 2: Per-venue position cap
# ─────────────────────────────────────────────────────────────────────────────

def compute_max_position_per_venue(
    venue: str,
    symbol: str,
    oi_usd: float,
    max_pct: float = 0.05,
) -> float:
    """
    Maximum safe position size at a venue = max_pct × OI (default 5%).

    Rationale (K454): 5% of OI → ~0.25% estimated slippage for most majors.
    At > 10% OI the slippage curve steepens super-linearly.

    Returns: max position size in USD (0.0 if venue disabled or OI = 0).
    """
    cfg = VENUE_CONFIG.get(venue, {})
    if not cfg.get("enabled", False):
        return 0.0
    if oi_usd <= 0:
        return 0.0

    # Override max_pct from venue config if set
    venue_max_pct = cfg.get("max_pct_of_oi", max_pct)
    cap = venue_max_pct * oi_usd

    # Floor: must exceed minimum depth
    min_depth = cfg.get("min_depth_usd", 500_000)
    if oi_usd * 0.01 < min_depth:
        # OI too small to safely trade — restrict to 0
        return 0.0

    return cap


# ─────────────────────────────────────────────────────────────────────────────
# Phase 3: Distribution algorithm
# ─────────────────────────────────────────────────────────────────────────────

def _score_venue_for_allocation(venue: str, symbol: str, depth_state: dict) -> float:
    """
    Score a venue for allocation priority.
    Higher score = better venue to allocate to first.

    Factors:
      - Available capacity (OI-based cap)
      - Maker rebate (positive contributes to score)
      - Taker fee (negative)
      - Book depth (deeper = better)
      - Estimated slippage (lower = better)
    """
    cfg     = VENUE_CONFIG.get(venue, {})
    oi_usd  = depth_state.get("oi_usd", 0.0)
    book_d  = depth_state.get("book_depth_usd", 0.0)

    if oi_usd <= 0:
        return -999.0

    cap     = compute_max_position_per_venue(venue, symbol, oi_usd)
    if cap <= 0:
        return -999.0

    rebate_score  =  cfg.get("maker_rebate_bps", 0.0) * 10   # rebate adds value
    fee_score     = -cfg.get("taker_fee_bps", 5.0) * 5       # fee reduces value
    depth_score   =  math.log10(max(book_d, 1.0)) * 5        # deeper book better
    cap_score     =  math.log10(max(cap, 1.0)) * 3            # larger cap preferred

    return rebate_score + fee_score + depth_score + cap_score


def distribute_target(
    symbol: str,
    target_usd: float,
    venues: List[str],
    depth_cache: Optional[Dict[str, dict]] = None,
    verbose: bool = True,
) -> Tuple[Dict[str, float], float]:
    """
    Distribute target position across venues respecting per-venue OI depth caps.

    Algorithm (K458 greedy allocator):
      1. Fetch per-venue depth (unless depth_cache provided)
      2. Compute per-venue max position (5% of OI cap)
      3. Score venues by maker rebate + depth + capacity
      4. Greedy allocation: best venue first, fill up to cap, repeat
      5. If remaining > 0 → warn and reduce target

    Args:
        symbol:       Trading symbol (e.g. "BTC")
        target_usd:   Target position size in USD
        venues:       List of venue names to consider
        depth_cache:  Pre-fetched depth dict {venue: depth_dict} (optional)
        verbose:      Print progress to stderr

    Returns:
        (allocation, remaining)
        allocation: {venue: allocated_usd} for filled portion
        remaining:  unallocated USD (> 0 means target reduced)
    """
    if verbose:
        print(f"\n[DepthAllocator] distribute_target({symbol}, ${target_usd:,.0f}) "
              f"across {venues}", file=sys.stderr)

    # Step 1: Gather depth state
    depth_states: Dict[str, dict] = {}
    if depth_cache:
        depth_states = depth_cache
    else:
        for v in venues:
            if verbose:
                print(f"  Fetching depth: {v}/{symbol} ...", file=sys.stderr)
            depth_states[v] = fetch_venue_depth(v, symbol)
            time.sleep(0.1)

    # Step 2: Compute per-venue max
    venue_max: Dict[str, float] = {}
    for v in venues:
        ds      = depth_states.get(v, {})
        oi_usd  = ds.get("oi_usd", 0.0)
        v_max   = compute_max_position_per_venue(v, symbol, oi_usd)
        venue_max[v] = v_max
        if verbose:
            print(f"  {v}: OI=${oi_usd:,.0f}  cap=${v_max:,.0f}", file=sys.stderr)

    # Step 3: Score venues
    venue_scores: Dict[str, float] = {
        v: _score_venue_for_allocation(v, symbol, depth_states.get(v, {}))
        for v in venues
    }

    # Step 4: Greedy allocation by score, respecting caps
    sorted_venues = sorted(venue_scores.items(), key=lambda x: x[1], reverse=True)
    allocation:   Dict[str, float] = {}
    remaining = target_usd

    for v, score in sorted_venues:
        if remaining <= 0:
            break
        v_max = venue_max.get(v, 0.0)
        if v_max <= 0:
            if verbose:
                print(f"  {v}: score={score:.1f} → cap=0, skipping", file=sys.stderr)
            continue
        alloc = min(remaining, v_max)
        allocation[v] = alloc
        remaining    -= alloc
        if verbose:
            print(f"  {v}: score={score:.1f} → allocated=${alloc:,.0f} "
                  f"(cap=${v_max:,.0f})", file=sys.stderr)

    # Step 5: If still remaining → target must be reduced
    if remaining > 0:
        print(
            f"\n  [DepthAllocator] WARNING: Cannot absorb full target for {symbol}. "
            f"Reducing by ${remaining:,.0f} ({remaining/target_usd*100:.1f}% of target). "
            f"Achievable: ${target_usd - remaining:,.0f}",
            file=sys.stderr,
        )

    return allocation, remaining


# ─────────────────────────────────────────────────────────────────────────────
# Phase 4: Slippage validation
# ─────────────────────────────────────────────────────────────────────────────

def estimate_slippage_bps(
    venue: str,
    symbol: str,
    position_usd: float,
    depth_state: dict,
) -> float:
    """
    Estimate market impact slippage in basis points for a given venue/symbol/size.

    Model: linear slippage = (position_usd / oi_usd) × slippage_bps_per_pct_of_oi × 100
    This is conservative at small sizes and aggressive at large sizes.
    At 5% of OI → roughly 5 × slippage_bps_per_pct_of_oi bps (0.05 × coeff × 100).
    """
    cfg     = VENUE_CONFIG.get(venue, {})
    oi_usd  = depth_state.get("oi_usd", 0.0)
    if oi_usd <= 0:
        return 999.0  # unknown venue → assume max slippage

    pct_of_oi         = position_usd / oi_usd
    slip_coeff        = cfg.get("slippage_bps_per_pct_of_oi", 10.0)
    slip_bps          = pct_of_oi * 100.0 * slip_coeff
    return slip_bps


def validate_allocation(
    allocation: Dict[str, float],
    depth_states: Dict[str, dict],
    symbol: str,
    max_slippage_bps: float = MAX_TOTAL_SLIPPAGE_BPS,
) -> Tuple[bool, Dict[str, float], float]:
    """
    Validate that total estimated slippage across all venues is within threshold.

    Returns:
        (is_valid, per_venue_slippage_bps, total_slippage_bps)
    """
    per_venue: Dict[str, float] = {}
    total_slip = 0.0

    for venue, alloc_usd in allocation.items():
        ds   = depth_states.get(venue, {})
        slip = estimate_slippage_bps(venue, symbol, alloc_usd, ds)
        per_venue[venue] = slip
        total_slip      += slip * (alloc_usd / max(sum(allocation.values()), 1.0))

    is_valid = total_slip <= max_slippage_bps
    return is_valid, per_venue, total_slip


# ─────────────────────────────────────────────────────────────────────────────
# Phase 5: Recommend reduce
# ─────────────────────────────────────────────────────────────────────────────

def recommend_reduce(
    target_usd: float,
    achievable_usd: float,
    slippage_total_bps: float,
    max_slippage_bps: float = MAX_TOTAL_SLIPPAGE_BPS,
) -> float:
    """
    Recommend a reduced target size that satisfies both:
      (a) Achievable across all venues (no venue over cap), and
      (b) Estimated slippage < threshold.

    Returns: recommended target USD (<= target_usd).
    """
    # Capacity constraint
    cap_target = achievable_usd

    # Slippage constraint: if slippage too high, scale down proportionally
    if slippage_total_bps > max_slippage_bps and slippage_total_bps > 0:
        slip_scale  = max_slippage_bps / slippage_total_bps
        slip_target = achievable_usd * slip_scale
    else:
        slip_target = achievable_usd

    recommended = min(cap_target, slip_target)
    return recommended


# ─────────────────────────────────────────────────────────────────────────────
# Phase 6: K439 POST_ONLY scaffold integration
# ─────────────────────────────────────────────────────────────────────────────

def submit_allocation_post_only(
    symbol: str,
    side: str,
    allocation: Dict[str, float],
    dry_run: bool = True,
) -> Dict[str, dict]:
    """
    Scaffold: Submit POST_ONLY orders for each venue allocation.
    In live mode: calls post_only_order_manager.execute_trade per venue.
    In dry-run (scaffold): returns mock submission records.

    K439 integration: each venue allocation → POST_ONLY limit order.
    K430 check: margin guard before submission (scaffold omits actual check).
    """
    results: Dict[str, dict] = {}

    for venue, alloc_usd in allocation.items():
        if alloc_usd <= 0:
            continue

        record = {
            "venue":       venue,
            "symbol":      symbol,
            "side":        side,
            "size_usd":    alloc_usd,
            "order_type":  "POST_ONLY",
            "dry_run":     dry_run,
            "submitted_at": datetime.now(JST).strftime("%Y-%m-%d %H:%M JST"),
        }

        if dry_run:
            record["status"]  = "DRY_RUN_SCAFFOLD"
            record["fill_px"] = None
            record["fill_ts"] = None
        else:
            # Live execution: route through post_only_order_manager
            # from post_only_order_manager import execute_trade
            # result = execute_trade(venue=venue, symbol=symbol, side=side, size=alloc_usd)
            # record.update(result)
            record["status"] = "SCAFFOLD_NO_LIVE_EXECUTION"
            record["note"]   = "Activate K439 post_only_order_manager for live execution"

        results[venue] = record
        print(f"  [K439 scaffold] {venue}/{symbol} {side} ${alloc_usd:,.0f} → {record['status']}",
              file=sys.stderr)

    return results


# ─────────────────────────────────────────────────────────────────────────────
# Phase 7: Dashboard + logging
# ─────────────────────────────────────────────────────────────────────────────

def _load_dashboard() -> dict:
    if DASHBOARD_PATH.exists():
        try:
            return json.loads(DASHBOARD_PATH.read_text())
        except json.JSONDecodeError:
            pass
    return {
        "last_poll_jst": "—",
        "stats_60d": {
            "total_allocations": 0,
            "venue_distribution_pct": {"HL": 0.0, "Bybit": 0.0, "OKX": 0.0},
            "average_slippage_bps": 0.0,
            "reduce_events_count": 0,
        },
        "current_capacity_estimate_at_aum": {
            "$10M":  "100% absorbable",
            "$100M": "85% absorbable",
            "$500M": "60% absorbable",
        },
        "recent_allocations": [],
    }


def _write_dashboard(allocation_record: Optional[dict] = None) -> None:
    dash = _load_dashboard()
    dash["last_poll_jst"] = datetime.now(JST).strftime("%Y-%m-%d %H:%M JST")

    if allocation_record:
        stats = dash["stats_60d"]
        stats["total_allocations"] = stats.get("total_allocations", 0) + 1

        venue_dist = stats.get("venue_distribution_pct", {})
        alloc      = allocation_record.get("allocation", {})
        total      = sum(alloc.values())
        if total > 0:
            for v, amt in alloc.items():
                prev_pct = venue_dist.get(v, 0.0)
                n        = stats["total_allocations"]
                venue_dist[v] = (prev_pct * (n - 1) + amt / total) / n
        stats["venue_distribution_pct"] = venue_dist

        slip = allocation_record.get("total_slippage_bps", 0.0)
        prev_slip = stats.get("average_slippage_bps", 0.0)
        n         = stats["total_allocations"]
        stats["average_slippage_bps"] = (prev_slip * (n - 1) + slip) / n

        if allocation_record.get("reduce_event", False):
            stats["reduce_events_count"] = stats.get("reduce_events_count", 0) + 1

        recents = dash.get("recent_allocations", [])
        recents.insert(0, allocation_record)
        dash["recent_allocations"] = recents[:20]   # keep last 20

    DASHBOARD_PATH.write_text(json.dumps(dash, indent=2))


def _log_decision(record: dict) -> None:
    with open(DECISION_LOG_PATH, "a") as f:
        f.write(json.dumps(record) + "\n")


# ─────────────────────────────────────────────────────────────────────────────
# Phase 10: $100M AUM simulation
# ─────────────────────────────────────────────────────────────────────────────

def run_aum_simulation(aum_usd: float, verbose: bool = True) -> dict:
    """
    $100M simulation test:
      - v6.20 candidate weights: K208 ~42%, K276b ~47%, K198 ~11%
      - For BTC K208 position ($20M target at $100M AUM):
        Without depth allocator: all on HL → X% of OI → HIGH slippage
        With depth allocator: distributed HL/Bybit/OKX → 5% each → safe

    Returns simulation results dict.
    """
    if verbose:
        print(f"\n{'='*60}", file=sys.stderr)
        print(f"[K458 Simulation] AUM=${aum_usd:,.0f}", file=sys.stderr)
        print(f"{'='*60}", file=sys.stderr)

    # v6.20 candidate: K208 reverse carry ~42% of K280 (80% sleeve) = ~33.6% of AUM
    # BTC position: K208 typically 15-20% of K208 notional for BTC
    btc_target = aum_usd * 0.20    # $20M at $100M AUM

    results = {
        "aum_usd":      aum_usd,
        "btc_target":   btc_target,
        "without_allocator": {},
        "with_allocator":    {},
        "venues":       ACTIVE_VENUES,
    }

    # ── Fetch live depth once for BTC ──────────────────────────────────────
    if verbose:
        print(f"\n[Sim] Fetching live BTC depth across {ACTIVE_VENUES} ...", file=sys.stderr)

    depth_states: Dict[str, dict] = {}
    for v in ACTIVE_VENUES:
        depth_states[v] = fetch_venue_depth(v, "BTC")

    # ── WITHOUT allocator: dump all on HL ──────────────────────────────────
    hl_depth = depth_states.get("HL", {})
    hl_oi    = hl_depth.get("oi_usd", FALLBACK_OI_USD["BTC"]["HL"])
    pct_of_oi_naive = btc_target / hl_oi if hl_oi > 0 else 0.0
    slip_naive = estimate_slippage_bps("HL", "BTC", btc_target, hl_depth)

    results["without_allocator"] = {
        "venue":           "HL_only",
        "target_usd":      btc_target,
        "hl_oi_usd":       hl_oi,
        "pct_of_oi":       pct_of_oi_naive,
        "slippage_bps":    slip_naive,
        "verdict":         "BAD" if pct_of_oi_naive > 0.05 else "OK",
        "note":            (
            f"{pct_of_oi_naive:.1%} of HL OI — "
            + ("EXCEEDS 5% safe cap, quadratic slippage regime"
               if pct_of_oi_naive > 0.05 else "within safe cap")
        ),
    }

    if verbose:
        print(f"\n[Sim] WITHOUT allocator: ${btc_target:,.0f} → HL only", file=sys.stderr)
        print(f"  HL OI: ${hl_oi:,.0f}", file=sys.stderr)
        print(f"  % of OI: {pct_of_oi_naive:.1%}  slippage: {slip_naive:.1f} bps",
              file=sys.stderr)
        print(f"  Verdict: {results['without_allocator']['verdict']}", file=sys.stderr)

    # ── WITH allocator: distribute ──────────────────────────────────────────
    allocation, remaining = distribute_target(
        symbol      = "BTC",
        target_usd  = btc_target,
        venues      = ACTIVE_VENUES,
        depth_cache = depth_states,
        verbose     = verbose,
    )

    is_valid, per_venue_slip, total_slip = validate_allocation(
        allocation, depth_states, "BTC"
    )
    achievable = sum(allocation.values())

    results["with_allocator"] = {
        "allocation":         allocation,
        "remaining_usd":      remaining,
        "achievable_usd":     achievable,
        "per_venue_slip_bps": per_venue_slip,
        "total_slippage_bps": total_slip,
        "validation_ok":      is_valid,
        "reduce_event":       remaining > 0,
        "verdict":            "GOOD" if total_slip < slip_naive * 0.5 else "MARGINAL",
    }

    if verbose:
        print(f"\n[Sim] WITH allocator:", file=sys.stderr)
        for v, amt in allocation.items():
            ds_v = depth_states.get(v, {})
            oi_v = ds_v.get("oi_usd", 0.0)
            pct  = amt / oi_v if oi_v > 0 else 0.0
            print(f"  {v}: ${amt:,.0f} ({pct:.1%} OI)", file=sys.stderr)
        print(f"  Total slip: {total_slip:.2f} bps (vs {slip_naive:.1f} naive)",
              file=sys.stderr)
        print(f"  Slip reduction: {(1-total_slip/max(slip_naive,0.01))*100:.0f}%",
              file=sys.stderr)
        print(f"  Validation: {'PASS' if is_valid else 'FAIL'}", file=sys.stderr)

    # ── Capacity absorption at different AUM tiers ──────────────────────────
    absorption: Dict[str, str] = {}
    for tier_aum, tier_label in [
        (10_000_000, "$10M"),
        (50_000_000, "$50M"),
        (100_000_000, "$100M"),
        (500_000_000, "$500M"),
        (1_000_000_000, "$1B"),
    ]:
        # BTC target = 20% of AUM
        tier_target = tier_aum * 0.20
        tier_alloc, tier_remaining = distribute_target(
            "BTC", tier_target, ACTIVE_VENUES,
            depth_cache=depth_states, verbose=False
        )
        tier_achievable = sum(tier_alloc.values())
        pct_abs         = tier_achievable / tier_target if tier_target > 0 else 0.0
        absorption[tier_label] = f"{pct_abs:.0%} absorbable"
        if verbose:
            print(f"  Capacity {tier_label}: {pct_abs:.0%} BTC target absorbed", file=sys.stderr)

    results["capacity_absorption"] = absorption
    results["slippage_improvement_pct"] = max(0.0, (1.0 - total_slip / max(slip_naive, 0.001)) * 100)

    return results


# ─────────────────────────────────────────────────────────────────────────────
# Main entrypoint
# ─────────────────────────────────────────────────────────────────────────────

def main() -> int:
    parser = argparse.ArgumentParser(
        description="K458 Depth-Aware Allocator — v6.20 capacity rescue"
    )
    parser.add_argument("--symbol",   default="BTC",  help="Symbol to allocate (default: BTC)")
    parser.add_argument("--target",   type=float,     help="Target position USD")
    parser.add_argument("--side",     default="short",choices=["long","short"])
    parser.add_argument("--aum",      type=float,     default=100_000_000,
                        help="AUM for simulation (default: $100M)")
    parser.add_argument("--dry-run",  action="store_true", default=True,
                        help="Scaffold mode — no actual orders (default: True)")
    parser.add_argument("--simulate", action="store_true",
                        help="Run $100M simulation and exit")
    parser.add_argument("--venues",   nargs="+", default=ACTIVE_VENUES,
                        help="Venues to use (default: HL Bybit OKX)")
    parser.add_argument("--quiet",    action="store_true", help="Minimal output")
    args = parser.parse_args()

    verbose = not args.quiet

    print(f"\n[K458 DepthAwareAllocator] SCAFFOLD mode={args.dry_run} "
          f"aum=${args.aum:,.0f}", file=sys.stderr)

    # Simulation mode
    if args.simulate or args.target is None:
        sim = run_aum_simulation(args.aum, verbose=verbose)

        # Write dashboard
        alloc_record = {
            "type":              "simulation",
            "symbol":            "BTC",
            "aum_usd":           args.aum,
            "allocation":        sim["with_allocator"]["allocation"],
            "total_slippage_bps":sim["with_allocator"]["total_slippage_bps"],
            "reduce_event":      sim["with_allocator"]["reduce_event"],
            "ts_jst":            datetime.now(JST).strftime("%Y-%m-%d %H:%M JST"),
        }
        _write_dashboard(alloc_record)
        _log_decision({**alloc_record, "sim_full": sim})

        # Update capacity in dashboard
        dash = _load_dashboard()
        dash["current_capacity_estimate_at_aum"] = sim.get("capacity_absorption", {})
        DASHBOARD_PATH.write_text(json.dumps(dash, indent=2))

        print(f"\n[K458] Simulation complete.", file=sys.stderr)
        print(f"  Dashboard: {DASHBOARD_PATH}", file=sys.stderr)
        print(f"  Decision log: {DECISION_LOG_PATH}", file=sys.stderr)

        # Print summary JSON
        summary = {
            "status":              "SCAFFOLD-READY",
            "aum_usd":             args.aum,
            "btc_target_usd":      sim["btc_target"],
            "without_allocator":   sim["without_allocator"],
            "with_allocator": {
                "allocation":         sim["with_allocator"]["allocation"],
                "total_slippage_bps": sim["with_allocator"]["total_slippage_bps"],
                "validation_ok":      sim["with_allocator"]["validation_ok"],
            },
            "slippage_improvement_pct": sim["slippage_improvement_pct"],
            "capacity_absorption":     sim["capacity_absorption"],
            "dashboard":              str(DASHBOARD_PATH),
            "decision_log":           str(DECISION_LOG_PATH),
        }
        print(json.dumps(summary, indent=2))
        return 0

    # Single allocation mode
    if verbose:
        print(f"[K458] Allocating {args.symbol} ${args.target:,.0f} "
              f"across {args.venues}", file=sys.stderr)

    depth_states = {v: fetch_venue_depth(v, args.symbol) for v in args.venues}
    allocation, remaining = distribute_target(
        symbol     = args.symbol,
        target_usd = args.target,
        venues     = args.venues,
        depth_cache= depth_states,
        verbose    = verbose,
    )

    is_valid, per_venue_slip, total_slip = validate_allocation(
        allocation, depth_states, args.symbol
    )

    achievable = sum(allocation.values())
    recommended = recommend_reduce(args.target, achievable, total_slip) if remaining > 0 else args.target

    # K439 scaffold submission
    submit_results = submit_allocation_post_only(
        symbol     = args.symbol,
        side       = args.side,
        allocation = allocation,
        dry_run    = args.dry_run,
    )

    # Dashboard + log
    record = {
        "type":              "live_allocation",
        "symbol":            args.symbol,
        "target_usd":        args.target,
        "achievable_usd":    achievable,
        "remaining_usd":     remaining,
        "recommended_usd":   recommended,
        "allocation":        allocation,
        "total_slippage_bps":total_slip,
        "per_venue_slip_bps":per_venue_slip,
        "validation_ok":     is_valid,
        "reduce_event":      remaining > 0,
        "ts_jst":            datetime.now(JST).strftime("%Y-%m-%d %H:%M JST"),
    }
    _write_dashboard(record)
    _log_decision(record)

    out = {
        "status":            "SCAFFOLD-READY",
        "symbol":            args.symbol,
        "target_usd":        args.target,
        "allocation":        allocation,
        "remaining_usd":     remaining,
        "recommended_usd":   recommended,
        "total_slippage_bps":total_slip,
        "validation_ok":     is_valid,
        "dashboard":         str(DASHBOARD_PATH),
    }
    print(json.dumps(out, indent=2))
    return 0 if is_valid else 1


if __name__ == "__main__":
    sys.exit(main())

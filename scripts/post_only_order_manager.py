"""
post_only_order_manager.py — K439 POST_ONLY Order Manager + IOC Fallback
=========================================================================
Maximizes maker rebates by attempting POST_ONLY orders first, falling back
to IOC taker orders after 5-minute timeout. Tracks fill rate per venue and
alerts when 60d maker fill rate drops below 60% (K378 G8 gate).

Expected value: +$23K/yr at $10M AUM (K432 lever analysis).

Architecture:
  1. submit_post_only_order()   → attempt maker at mid-price (or 1-tick better)
  2. wait_for_fill()            → poll up to POST_ONLY_TIMEOUT_SEC (300s)
  3. cancel_unfilled_order()    → cancel if timeout
  4. submit_ioc_fallback()      → taker IOC at mid-price (small slip)
  5. track_fill_rate()          → append to cache/post_only_fills.jsonl
  6. get_daily_fill_stats()     → rolling 60d fill rate + G8 gate
  7. execute_trade()            → full decision flow

K434 / K430 integration:
  - K434 smart router chooses venue → K439 chooses order type
  - K430 circuit breaker: refuse if margin > 80% AUM

K339 security: REPO_ROOT from __file__, no /Users/ literals.

Usage:
  python3 scripts/post_only_order_manager.py --dry-run
  python3 scripts/post_only_order_manager.py --stats
  python3 scripts/post_only_order_manager.py --dashboard

Production integration (scaffold — not active; POST_ONLY_ENABLED=True by default):
  from post_only_order_manager import execute_trade
  result = execute_trade(venue="HL", symbol="SOL", side="short", size=1000.0)
"""
from __future__ import annotations

import argparse
import json
import math
import time
import os
import sys
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Tuple

# ── K339 Security: REPO_ROOT from __file__, no /Users/ literals ───────────────
REPO_ROOT = Path(__file__).resolve().parent.parent
CACHE_DIR = REPO_ROOT / "cache"
DATA_DIR  = REPO_ROOT / "data"
CACHE_DIR.mkdir(exist_ok=True)
DATA_DIR.mkdir(exist_ok=True)

# ── Config ────────────────────────────────────────────────────────────────────
POST_ONLY_ENABLED       = True      # Master switch; set False to bypass all POST_ONLY logic
POST_ONLY_TIMEOUT_SEC   = 300       # 5 minutes wait for POST_ONLY fill before IOC fallback
TICK_IMPROVEMENT_BIPS   = 0.5       # Place POST_ONLY 0.5 bps better than mid to increase fill chance
FILL_RATE_ALERT_THRESH  = 0.60      # Alert if 60d maker fill rate < 60% (K378 G8 gate)
FILL_RATE_WINDOW_DAYS   = 60        # Rolling window for fill rate calculation
MAX_MARGIN_PCT          = 0.80      # Refuse trade if portfolio margin > 80% AUM (K430 circuit breaker)
IOC_LIMIT_SLIP_BIPS     = 3.0       # IOC fallback: allow up to 3 bps slip from mid-price

# ── File paths ────────────────────────────────────────────────────────────────
FILLS_JSONL         = CACHE_DIR / "post_only_fills.jsonl"
DASHBOARD_JSON      = DATA_DIR  / "post_only_dashboard.json"

# ── Venue-specific constants ──────────────────────────────────────────────────
SUPPORTED_VENUES    = ["HL", "Bybit", "OKX"]
MAKER_REBATE_BPS: Dict[str, float] = {
    "HL":    -1.5,   # HL GOLD tier maker rebate (negative = rebate)
    "Bybit": -1.0,   # Bybit VIP5 maker rebate
    "OKX":   -0.5,   # OKX VIP1 maker rebate
}
TAKER_FEE_BPS: Dict[str, float] = {
    "HL":    4.5,
    "Bybit": 2.5,
    "OKX":   2.0,
}

# ── K430 Leverage Manager integration ─────────────────────────────────────────
try:
    sys.path.insert(0, str(REPO_ROOT / "scripts"))
    from leverage_manager import check_margin_health as _check_margin_health
    _LEVERAGE_MANAGER_AVAILABLE = True
except Exception as _lev_err:
    _LEVERAGE_MANAGER_AVAILABLE = False


# ─────────────────────────────────────────────────────────────────────────────
# Price utilities (dry-run: returns mock mid; live: call venue REST)
# ─────────────────────────────────────────────────────────────────────────────

def get_mid_price(venue: str, symbol: str) -> float:
    """
    Get mid-price for symbol at venue.
    In dry-run / scaffold mode: returns a plausible mock price.
    In live mode: call venue REST orderbook API (not implemented — scaffold).

    Returns:
        float: mid-price in USD
    """
    # Scaffold: realistic mock prices per symbol
    _MOCK_PRICES: Dict[str, float] = {
        "BTC": 108000.0, "ETH": 4000.0, "SOL": 230.0,  "XRP": 2.80,
        "SUI": 5.80,     "OP":  3.20,   "APT": 14.50,  "AXS": 6.00,
        "JTO": 4.10,     "IMX": 2.30,   "SAND": 0.60,  "ADA": 1.20,
        "LINK": 25.50,   "AVAX": 45.00, "PAXG": 3850.0, "SPX": 5800.0,
        "ENA": 0.85,     "PEPE": 0.00002, "BONK": 0.00005,
    }
    price = _MOCK_PRICES.get(symbol.upper(), 100.0)
    return price


def _tick_adjusted_price(mid: float, side: str, venue: str) -> float:
    """
    Compute POST_ONLY limit price: 1 tick better than mid to improve fill odds.
    Buy: place slightly below mid (better than aggressor).
    Sell: place slightly above mid.

    TICK_IMPROVEMENT_BIPS = 0.5 bps default.
    """
    delta = mid * (TICK_IMPROVEMENT_BIPS / 10000.0)
    if side.lower() in ("buy", "long"):
        return round(mid - delta, 8)   # bid side: just inside mid
    else:
        return round(mid + delta, 8)   # ask side: just inside mid


def _ioc_limit_price(mid: float, side: str) -> float:
    """
    IOC fallback limit price: allow up to IOC_LIMIT_SLIP_BIPS slip from mid.
    Buy IOC: willing to pay up to mid + slip.
    Sell IOC: willing to accept down to mid - slip.
    """
    slip = mid * (IOC_LIMIT_SLIP_BIPS / 10000.0)
    if side.lower() in ("buy", "long"):
        return round(mid + slip, 8)
    else:
        return round(mid - slip, 8)


# ─────────────────────────────────────────────────────────────────────────────
# Phase 1 core functions
# ─────────────────────────────────────────────────────────────────────────────

def submit_post_only_order(
    venue: str,
    symbol: str,
    side: str,
    size: float,
    price: float,
    dry_run: bool = False,
) -> Dict:
    """
    Submit a POST_ONLY limit order at the given price.
    POST_ONLY means the order is rejected (not filled as taker) if it would
    immediately match — ensuring we pay maker rebate, not taker fee.

    Args:
        venue:   "HL" | "Bybit" | "OKX"
        symbol:  e.g. "SOL", "BTC"
        side:    "buy" | "sell" (or "long" | "short")
        size:    order size in USD notional
        price:   limit price (should be 1 tick better than mid)
        dry_run: if True, simulate only (no real API call)

    Returns:
        {
            "order_id": str,
            "status":   "PENDING" | "FAILED" | "DRY_RUN",
            "venue":    str,
            "symbol":   str,
            "side":     str,
            "size":     float,
            "price":    float,
            "ts_utc":   str,
            "post_only": True,
        }
    """
    ts = datetime.now(timezone.utc).isoformat()

    if dry_run:
        order_id = f"DRY_{venue}_{symbol}_{int(time.time())}"
        print(f"  [POST_ONLY DRY-RUN] {venue} {symbol} {side} ${size:,.0f} @ {price:.6f}")
        return {
            "order_id": order_id,
            "status":   "DRY_RUN",
            "venue":    venue,
            "symbol":   symbol,
            "side":     side,
            "size":     size,
            "price":    price,
            "ts_utc":   ts,
            "post_only": True,
        }

    # Live scaffold: venue-specific POST_ONLY submission not implemented
    # K439 Phase 1 — wiring point for HL / Bybit / OKX exchange adapters
    # HL: order_type="limit", post_only=True in order action
    # Bybit: timeInForce="PostOnly"
    # OKX: ordType="post_only"
    order_id = f"SCAFFOLD_{venue}_{symbol}_{int(time.time())}"
    print(f"  [POST_ONLY] SCAFFOLD: {venue} {symbol} {side} ${size:,.0f} @ {price:.6f}  [POST_ONLY_ENABLED={POST_ONLY_ENABLED}]")
    return {
        "order_id": order_id,
        "status":   "PENDING",
        "venue":    venue,
        "symbol":   symbol,
        "side":     side,
        "size":     size,
        "price":    price,
        "ts_utc":   ts,
        "post_only": True,
    }


def wait_for_fill(order_id: str, timeout_sec: int = POST_ONLY_TIMEOUT_SEC, dry_run: bool = False) -> bool:
    """
    Poll for order fill status until timeout.
    In dry-run mode: simulate 70% fill rate (optimistic).
    In scaffold: always returns False after 0-second mock delay.

    Args:
        order_id:    order identifier from submit_post_only_order
        timeout_sec: maximum wait time (default 300s = 5 min)
        dry_run:     if True, simulate fill without waiting

    Returns:
        True if filled, False if timeout/unfilled
    """
    if dry_run:
        # Simulate realistic ~70% maker fill rate for dry-run
        import hashlib
        seed = int(hashlib.md5(order_id.encode()).hexdigest()[:8], 16)
        filled = (seed % 100) < 70   # deterministic 70% rate
        result = "FILLED" if filled else "TIMEOUT"
        print(f"  [WAIT_FILL DRY-RUN] order={order_id[:30]}...  → {result} (simulated)")
        return filled

    # Scaffold: poll logic placeholder
    # Live implementation: poll venue REST /orders/{order_id} every 5s
    # until status == "FILLED" or timeout reached
    print(f"  [WAIT_FILL] SCAFFOLD: order={order_id[:30]}...  timeout={timeout_sec}s  → TIMEOUT (no live API)")
    return False


def cancel_unfilled_order(order_id: str, venue: str = "HL", dry_run: bool = False) -> bool:
    """
    Cancel an unfilled POST_ONLY order before placing IOC fallback.

    Args:
        order_id: order identifier
        venue:    venue where order was placed
        dry_run:  if True, simulate without real API call

    Returns:
        True if cancelled successfully, False otherwise
    """
    if dry_run:
        print(f"  [CANCEL DRY-RUN] {venue} order={order_id[:30]}...  → OK")
        return True

    # Scaffold: venue-specific cancel API call
    # HL: {"type": "cancel", "cancels": [{"a": asset_id, "o": order_id}]}
    # Bybit: DELETE /v5/order/cancel
    # OKX:  POST /api/v5/trade/cancel-order
    print(f"  [CANCEL] SCAFFOLD: {venue} order={order_id[:30]}...  → OK (scaffold)")
    return True


def submit_ioc_fallback(
    venue: str,
    symbol: str,
    side: str,
    size: float,
    dry_run: bool = False,
) -> Dict:
    """
    Submit IOC (Immediate Or Cancel) taker order at mid-price + small slip.
    IOC ensures the order fills immediately or not at all (no resting).
    Accepts taker fee, but avoids prolonged exposure.

    Args:
        venue:   "HL" | "Bybit" | "OKX"
        symbol:  e.g. "SOL"
        side:    "buy" | "sell"
        size:    order size in USD notional
        dry_run: if True, simulate fill without real API call

    Returns:
        {
            "order_id": str,
            "status":   "FILLED" | "PARTIAL" | "FAILED" | "DRY_RUN",
            "filled":   bool,
            "fill_price": float,
            "taker_fee_bps": float,
            "ts_utc":   str,
        }
    """
    mid   = get_mid_price(venue, symbol)
    limit = _ioc_limit_price(mid, side)
    ts    = datetime.now(timezone.utc).isoformat()
    taker_fee = TAKER_FEE_BPS.get(venue, 4.5)

    if dry_run:
        order_id = f"IOC_DRY_{venue}_{symbol}_{int(time.time())}"
        print(f"  [IOC DRY-RUN] {venue} {symbol} {side} ${size:,.0f} @ {limit:.6f}  (taker {taker_fee:.1f}bps)")
        return {
            "order_id":     order_id,
            "status":       "DRY_RUN",
            "filled":       True,
            "fill_price":   limit,
            "mid_price":    mid,
            "slip_bps":     IOC_LIMIT_SLIP_BIPS,
            "taker_fee_bps": taker_fee,
            "ts_utc":       ts,
        }

    order_id = f"IOC_{venue}_{symbol}_{int(time.time())}"
    print(f"  [IOC FALLBACK] SCAFFOLD: {venue} {symbol} {side} ${size:,.0f} @ {limit:.6f}  (taker {taker_fee:.1f}bps)")
    return {
        "order_id":     order_id,
        "status":       "SCAFFOLD",
        "filled":       False,   # scaffold: treat as unfilled until live wiring
        "fill_price":   limit,
        "mid_price":    mid,
        "slip_bps":     IOC_LIMIT_SLIP_BIPS,
        "taker_fee_bps": taker_fee,
        "ts_utc":       ts,
    }


# ─────────────────────────────────────────────────────────────────────────────
# Phase 3: Fill rate tracking
# ─────────────────────────────────────────────────────────────────────────────

def track_fill_rate(
    venue: str,
    symbol: str,
    side: str,
    size: float,
    was_post_only_filled: bool,
    ioc_used: bool,
    fill_price: Optional[float] = None,
) -> None:
    """
    Append a fill attempt record to cache/post_only_fills.jsonl.
    Called after every trade attempt (POST_ONLY success or IOC fallback).

    Args:
        venue:                "HL" | "Bybit" | "OKX"
        symbol:               e.g. "SOL"
        side:                 "buy" | "sell"
        size:                 USD notional
        was_post_only_filled: True if POST_ONLY filled before timeout
        ioc_used:             True if IOC fallback was triggered
        fill_price:           actual fill price (None if scaffold)
    """
    record = {
        "timestamp":           datetime.now(timezone.utc).isoformat(),
        "venue":               venue,
        "symbol":              symbol,
        "side":                side,
        "size":                size,
        "post_only_filled":    was_post_only_filled,
        "ioc_used":            ioc_used,
        "fill_price":          fill_price,
    }
    with open(FILLS_JSONL, "a") as f:
        f.write(json.dumps(record) + "\n")


def _load_fills(window_days: int = FILL_RATE_WINDOW_DAYS) -> List[Dict]:
    """Load fill records from JSONL within the rolling window."""
    if not FILLS_JSONL.exists():
        return []
    cutoff = datetime.now(timezone.utc) - timedelta(days=window_days)
    records: List[Dict] = []
    try:
        with open(FILLS_JSONL) as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    rec = json.loads(line)
                    ts_str = rec.get("timestamp", "")
                    if ts_str:
                        ts = datetime.fromisoformat(ts_str.replace("Z", "+00:00"))
                        if ts >= cutoff:
                            records.append(rec)
                except (json.JSONDecodeError, ValueError):
                    continue
    except Exception as e:
        print(f"  [fills] Error loading fills: {e}")
    return records


def get_daily_fill_stats(window_days: int = FILL_RATE_WINDOW_DAYS) -> Dict:
    """
    Compute rolling fill rate statistics.
    Returns overall stats and per-venue breakdown.

    Returns:
        {
            "total_orders":       int,
            "post_only_filled":   int,
            "post_only_fill_rate": float,
            "ioc_used":           int,
            "G8_gate_status":     "PASS" | "FAIL" | "NO_DATA",
            "by_venue": {
                "HL": {...},
                "Bybit": {...},
                "OKX": {...},
            },
            "window_days": int,
            "computed_at_utc": str,
        }
    """
    records = _load_fills(window_days)
    ts_now  = datetime.now(timezone.utc).isoformat()

    if not records:
        return {
            "total_orders":        0,
            "post_only_filled":    0,
            "post_only_fill_rate": 0.0,
            "ioc_used":            0,
            "G8_gate_status":      "NO_DATA",
            "by_venue":            {v: {"total": 0, "post_only_filled": 0, "fill_rate": 0.0} for v in SUPPORTED_VENUES},
            "window_days":         window_days,
            "computed_at_utc":     ts_now,
        }

    total         = len(records)
    po_filled     = sum(1 for r in records if r.get("post_only_filled"))
    ioc_used      = sum(1 for r in records if r.get("ioc_used"))
    fill_rate     = po_filled / total if total > 0 else 0.0
    g8_status     = "PASS" if fill_rate >= FILL_RATE_ALERT_THRESH else "FAIL"

    # Per-venue breakdown
    by_venue: Dict[str, Dict] = {}
    for venue in SUPPORTED_VENUES:
        v_recs  = [r for r in records if r.get("venue") == venue]
        v_total = len(v_recs)
        v_po    = sum(1 for r in v_recs if r.get("post_only_filled"))
        v_rate  = round(v_po / v_total, 4) if v_total > 0 else 0.0
        if v_total == 0:
            v_g8 = "NO_DATA"
        elif v_rate >= FILL_RATE_ALERT_THRESH:
            v_g8 = "PASS"
        else:
            v_g8 = "FAIL"
        by_venue[venue] = {
            "total":            v_total,
            "post_only_filled": v_po,
            "ioc_used":         sum(1 for r in v_recs if r.get("ioc_used")),
            "fill_rate":        v_rate,
            "g8_status":        v_g8,
        }

    return {
        "total_orders":        total,
        "post_only_filled":    po_filled,
        "post_only_fill_rate": round(fill_rate, 4),
        "ioc_used":            ioc_used,
        "G8_gate_status":      g8_status,
        "by_venue":            by_venue,
        "window_days":         window_days,
        "computed_at_utc":     ts_now,
    }


# ─────────────────────────────────────────────────────────────────────────────
# Phase 4: Dashboard JSON
# ─────────────────────────────────────────────────────────────────────────────

def write_dashboard() -> Dict:
    """
    Write data/post_only_dashboard.json with current fill rate stats.
    Called after each trade or by fill-rate-monitor plist (hourly).

    Returns the written dashboard dict.
    """
    stats    = get_daily_fill_stats()
    g8_pass  = stats["G8_gate_status"] == "PASS"
    g8_no_data = stats["G8_gate_status"] == "NO_DATA"

    # JST timestamp
    jst_offset = timezone(timedelta(hours=9))
    ts_jst = datetime.now(jst_offset).strftime("%Y-%m-%d %H:%M JST")

    dashboard = {
        "last_poll_jst":   ts_jst,
        "stats_60d":       {
            "total_orders":        stats["total_orders"],
            "post_only_filled":    stats["post_only_filled"],
            "post_only_fill_rate": stats["post_only_fill_rate"],
            "ioc_used":            stats["ioc_used"],
            "G8_gate_status":      stats["G8_gate_status"],
            "alert":               (not g8_pass and not g8_no_data),
            "threshold":           FILL_RATE_ALERT_THRESH,
        },
        "stats_by_venue":  stats["by_venue"],
        "config": {
            "post_only_enabled":       POST_ONLY_ENABLED,
            "timeout_sec":             POST_ONLY_TIMEOUT_SEC,
            "tick_improvement_bips":   TICK_IMPROVEMENT_BIPS,
            "fill_rate_alert_thresh":  FILL_RATE_ALERT_THRESH,
            "ioc_limit_slip_bips":     IOC_LIMIT_SLIP_BIPS,
            "max_margin_pct":          MAX_MARGIN_PCT,
            "fill_rate_window_days":   FILL_RATE_WINDOW_DAYS,
        },
        "edge_estimate": {
            "description":     "POST_ONLY vs taker fee savings per $10M AUM/yr",
            "maker_vs_taker_bps_HL":    abs(MAKER_REBATE_BPS["HL"] - TAKER_FEE_BPS["HL"]),
            "maker_vs_taker_bps_Bybit": abs(MAKER_REBATE_BPS["Bybit"] - TAKER_FEE_BPS["Bybit"]),
            "annual_savings_10M_usd":   23000,   # K432 lever estimate
        },
        "wave":    "K439",
        "version": "v1.0",
    }

    with open(DASHBOARD_JSON, "w") as f:
        json.dump(dashboard, f, indent=2)
    print(f"  [POST_ONLY] Dashboard written: {DASHBOARD_JSON}")
    return dashboard


# ─────────────────────────────────────────────────────────────────────────────
# Phase 7: K430 margin check guard
# ─────────────────────────────────────────────────────────────────────────────

def _check_margin_guard(venue: str, current_aum: float = 10_000_000.0) -> bool:
    """
    Before any order submission: check K430 circuit breaker margin health.
    If margin used > MAX_MARGIN_PCT (80%), refuse the trade.

    Args:
        venue:       exchange venue (informational)
        current_aum: current AUM in USD (default $10M for paper-trade mode)

    Returns True if trade is allowed, False if refused.
    """
    if not _LEVERAGE_MANAGER_AVAILABLE:
        return True   # fail-open: allow trade if CB not available

    try:
        health = _check_margin_health(current_aum=current_aum)
        margin_pct = health.get("margin_used_pct", 0.0)
        fire = health.get("circuit_breaker_fire", False)
        if fire or margin_pct > MAX_MARGIN_PCT:
            print(f"  [K430 CB] Trade REFUSED: margin={margin_pct:.1%} > {MAX_MARGIN_PCT:.0%}  fire={fire}")
            return False
        return True
    except Exception as e:
        print(f"  [K430 CB] Margin check error ({e}) — allowing trade (fail-open)")
        return True


# ─────────────────────────────────────────────────────────────────────────────
# Phase 2: Main decision flow
# ─────────────────────────────────────────────────────────────────────────────

def execute_trade(
    venue:   str,
    symbol:  str,
    side:    str,
    size:    float,
    urgency: str = "LOW",
    dry_run: bool = False,
) -> Dict:
    """
    Full POST_ONLY → IOC fallback decision flow.

    urgency:
      "LOW"       → POST_ONLY first, IOC fallback after 5 min (default)
      "MEDIUM"    → POST_ONLY with 60s timeout, then IOC
      "EMERGENCY" → bypass POST_ONLY, submit IOC immediately

    Args:
        venue:   "HL" | "Bybit" | "OKX"
        symbol:  e.g. "SOL", "BTC"
        side:    "buy" | "sell" (or "long" | "short")
        size:    USD notional
        urgency: "LOW" | "MEDIUM" | "EMERGENCY"
        dry_run: if True, simulate without real API calls

    Returns:
        {
            "venue":      str,
            "symbol":     str,
            "side":       str,
            "size":       float,
            "type":       "POST_ONLY" | "IOC_FALLBACK" | "EMERGENCY_IOC" | "REFUSED",
            "filled":     bool,
            "fill_price": float | None,
            "post_only_attempted": bool,
            "margin_check_passed": bool,
            "ts_utc":     str,
        }
    """
    ts = datetime.now(timezone.utc).isoformat()
    urgency = urgency.upper()

    # ── Master switch ─────────────────────────────────────────────────────────
    if not POST_ONLY_ENABLED:
        print(f"  [POST_ONLY] Disabled (POST_ONLY_ENABLED=False) → routing directly to IOC")
        ioc = submit_ioc_fallback(venue, symbol, side, size, dry_run=dry_run)
        track_fill_rate(venue, symbol, side, size,
                        was_post_only_filled=False, ioc_used=True,
                        fill_price=ioc.get("fill_price"))
        return {"venue": venue, "symbol": symbol, "side": side, "size": size,
                "type": "IOC_DIRECT", "filled": ioc.get("filled", False),
                "fill_price": ioc.get("fill_price"), "post_only_attempted": False,
                "margin_check_passed": True, "ts_utc": ts}

    # ── K430 Margin guard ─────────────────────────────────────────────────────
    margin_ok = _check_margin_guard(venue)
    if not margin_ok:
        return {"venue": venue, "symbol": symbol, "side": side, "size": size,
                "type": "REFUSED", "filled": False, "fill_price": None,
                "post_only_attempted": False, "margin_check_passed": False,
                "reason": "K430_MARGIN_EXCEEDED", "ts_utc": ts}

    # ── EMERGENCY bypass ─────────────────────────────────────────────────────
    if urgency == "EMERGENCY":
        print(f"  [POST_ONLY] EMERGENCY urgency → bypassing POST_ONLY, submitting IOC directly")
        ioc = submit_ioc_fallback(venue, symbol, side, size, dry_run=dry_run)
        track_fill_rate(venue, symbol, side, size,
                        was_post_only_filled=False, ioc_used=True,
                        fill_price=ioc.get("fill_price"))
        return {"venue": venue, "symbol": symbol, "side": side, "size": size,
                "type": "EMERGENCY_IOC", "filled": ioc.get("filled", False),
                "fill_price": ioc.get("fill_price"), "post_only_attempted": False,
                "margin_check_passed": True, "ts_utc": ts}

    # ── Set timeout by urgency ────────────────────────────────────────────────
    timeout = 60 if urgency == "MEDIUM" else POST_ONLY_TIMEOUT_SEC

    # ── Step 1: POST_ONLY attempt ─────────────────────────────────────────────
    mid_price = get_mid_price(venue, symbol)
    po_price  = _tick_adjusted_price(mid_price, side, venue)

    print(f"\n  [K439] execute_trade: {venue} {symbol} {side} ${size:,.0f}  urgency={urgency}  mid={mid_price:.4f}")
    print(f"  [K439] Step 1: POST_ONLY @ {po_price:.6f}  timeout={timeout}s")

    order = submit_post_only_order(venue, symbol, side, size, po_price, dry_run=dry_run)
    filled = wait_for_fill(order["id"] if "id" in order else order.get("order_id", ""), timeout_sec=timeout, dry_run=dry_run)

    if filled:
        track_fill_rate(venue, symbol, side, size,
                        was_post_only_filled=True, ioc_used=False,
                        fill_price=po_price)
        print(f"  [K439] POST_ONLY FILLED  maker_rebate={MAKER_REBATE_BPS.get(venue, -1.0):.1f}bps")
        write_dashboard()
        return {
            "venue":               venue,
            "symbol":              symbol,
            "side":                side,
            "size":                size,
            "type":                "POST_ONLY",
            "filled":              True,
            "fill_price":          po_price,
            "post_only_attempted": True,
            "margin_check_passed": True,
            "maker_rebate_bps":    MAKER_REBATE_BPS.get(venue, -1.0),
            "ts_utc":              ts,
        }

    # ── Step 2: Cancel + IOC fallback ────────────────────────────────────────
    print(f"  [K439] POST_ONLY timeout → cancelling, submitting IOC fallback")
    order_id = order.get("order_id", order.get("id", ""))
    cancel_unfilled_order(order_id, venue=venue, dry_run=dry_run)
    ioc = submit_ioc_fallback(venue, symbol, side, size, dry_run=dry_run)

    track_fill_rate(venue, symbol, side, size,
                    was_post_only_filled=False, ioc_used=True,
                    fill_price=ioc.get("fill_price"))

    # Check fill rate and alert if G8 below threshold
    stats = get_daily_fill_stats()
    if stats["G8_gate_status"] == "FAIL":
        print(f"  [K439] ALERT: 60d maker fill rate = {stats['post_only_fill_rate']:.1%} < "
              f"{FILL_RATE_ALERT_THRESH:.0%} (K378 G8 gate FAIL)  venue={venue}")

    write_dashboard()
    return {
        "venue":               venue,
        "symbol":              symbol,
        "side":                side,
        "size":                size,
        "type":                "IOC_FALLBACK",
        "filled":              ioc.get("filled", False),
        "fill_price":          ioc.get("fill_price"),
        "post_only_attempted": True,
        "margin_check_passed": True,
        "taker_fee_bps":       TAKER_FEE_BPS.get(venue, 4.5),
        "ts_utc":              ts,
    }


# ─────────────────────────────────────────────────────────────────────────────
# K450 Phase 6 — Paired-trade POST_ONLY execution (K449 multi-leg)
# ─────────────────────────────────────────────────────────────────────────────

# Separate fill-rate tracking for paired trades
PAIRED_FILLS_JSONL = CACHE_DIR / "k449_paired_fills.jsonl"


def _track_paired_fill_rate(
    venue: str,
    long_symbol: str,
    short_symbol: str,
    size: float,
    long_post_only_filled: bool,
    short_post_only_filled: bool,
    long_ioc_used: bool,
    short_ioc_used: bool,
) -> None:
    """Track fill rate for K449 paired trades separately from single-leg K208."""
    record = {
        "timestamp":              datetime.now(timezone.utc).isoformat(),
        "venue":                  venue,
        "long_symbol":            long_symbol,
        "short_symbol":           short_symbol,
        "size_per_leg":           size,
        "long_post_only_filled":  long_post_only_filled,
        "short_post_only_filled": short_post_only_filled,
        "long_ioc_used":          long_ioc_used,
        "short_ioc_used":         short_ioc_used,
        "both_post_only":         long_post_only_filled and short_post_only_filled,
    }
    with open(PAIRED_FILLS_JSONL, "a") as f:
        f.write(json.dumps(record) + "\n")


def get_paired_fill_stats(window_days: int = FILL_RATE_WINDOW_DAYS) -> Dict:
    """
    Compute fill rate statistics for K449 paired trades.
    Separate from single-leg K208 stats.

    Returns:
      {
        "total_paired_trades":  int,
        "both_post_only":       int,
        "both_post_only_rate":  float,
        "G8_paired_status":     "PASS" | "FAIL" | "NO_DATA",
        "window_days":          int,
      }
    """
    if not PAIRED_FILLS_JSONL.exists():
        return {
            "total_paired_trades": 0,
            "both_post_only":      0,
            "both_post_only_rate": 0.0,
            "G8_paired_status":    "NO_DATA",
            "window_days":         window_days,
        }
    cutoff  = datetime.now(timezone.utc) - timedelta(days=window_days)
    records = []
    for line in PAIRED_FILLS_JSONL.read_text().splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            rec = json.loads(line)
            ts_str = rec.get("timestamp", "")
            if ts_str:
                ts = datetime.fromisoformat(ts_str.replace("Z", "+00:00"))
                if ts >= cutoff:
                    records.append(rec)
        except (json.JSONDecodeError, ValueError):
            continue

    total  = len(records)
    both   = sum(1 for r in records if r.get("both_post_only"))
    rate   = both / total if total > 0 else 0.0
    g8     = "PASS" if rate >= FILL_RATE_ALERT_THRESH else ("NO_DATA" if total == 0 else "FAIL")

    return {
        "total_paired_trades": total,
        "both_post_only":      both,
        "both_post_only_rate": round(rate, 4),
        "G8_paired_status":    g8,
        "window_days":         window_days,
    }


def execute_paired_trade(
    long_leg: Dict,
    short_leg: Dict,
    urgency: str = "LOW",
    dry_run: bool = False,
) -> Dict:
    """
    K449 paired-trade POST_ONLY execution (K450 Phase 6).

    Submits both legs using POST_ONLY maker orders.
    Protocol:
      1. POST_ONLY long leg
      2. On long fill: POST_ONLY short leg simultaneously
      3. If short POST_ONLY times out: cancel + IOC short fallback
      4. If long POST_ONLY times out: cancel long, abort (retry next 8h cycle)

    Fill rate tracked separately in k449_paired_fills.jsonl (not mixed with K208).

    Args:
      long_leg:  {"venue": "HL", "symbol": "ETH", "size": 600000.0}
      short_leg: {"venue": "HL", "symbol": "BTC", "size": 600000.0}
      urgency:   "LOW" (default) | "MEDIUM" | "EMERGENCY"
      dry_run:   if True, simulate without API calls

    Returns:
      {
        "status":             "BOTH_POST_ONLY" | "SHORT_IOC" | "ABORTED" | "DRY_RUN",
        "long_filled":        bool,
        "short_filled":       bool,
        "long_order":         dict,
        "short_order":        dict,
        "paired_fill_rate":   float,  # running 60d rate
        "ts_utc":             str,
      }
    """
    ts = datetime.now(timezone.utc).isoformat()
    urgency = urgency.upper()

    venue      = long_leg.get("venue", "HL")
    long_sym   = long_leg.get("symbol", "ETH")
    short_sym  = short_leg.get("symbol", "BTC")
    long_size  = float(long_leg.get("size", 0.0))
    short_size = float(short_leg.get("size", 0.0))

    # K430 margin guard
    margin_ok = _check_margin_guard(venue)
    if not margin_ok:
        return {
            "status":       "REFUSED",
            "reason":       "K430_MARGIN_EXCEEDED",
            "long_filled":  False,
            "short_filled": False,
            "ts_utc":       ts,
        }

    # Timeout based on urgency
    timeout = (
        0    if urgency == "EMERGENCY"  else
        60   if urgency == "MEDIUM"     else
        POST_ONLY_TIMEOUT_SEC
    )

    print(f"\n  [K449 PAIRED] execute_paired_trade: {venue}  "
          f"LONG {long_sym} ${long_size:,.0f} / SHORT {short_sym} ${short_size:,.0f}  "
          f"urgency={urgency}")

    # ── EMERGENCY: bypass POST_ONLY for both legs ─────────────────────────────
    if urgency == "EMERGENCY":
        print(f"  [K449 PAIRED] EMERGENCY: IOC direct for both legs")
        long_ioc  = submit_ioc_fallback(venue, long_sym,  "buy",  long_size,  dry_run=dry_run)
        short_ioc = submit_ioc_fallback(venue, short_sym, "sell", short_size, dry_run=dry_run)
        _track_paired_fill_rate(venue, long_sym, short_sym, long_size,
                                False, False, True, True)
        return {
            "status":       "EMERGENCY_IOC",
            "long_filled":  long_ioc.get("filled", False),
            "short_filled": short_ioc.get("filled", False),
            "long_order":   long_ioc,
            "short_order":  short_ioc,
            "ts_utc":       ts,
        }

    # ── Step 1: POST_ONLY long leg ─────────────────────────────────────────────
    long_mid   = get_mid_price(venue, long_sym)
    long_price = _tick_adjusted_price(long_mid, "buy", venue)
    print(f"  [K449 PAIRED] Step 1: POST_ONLY LONG {long_sym} @ {long_price:.6f}  timeout={timeout}s")

    long_order = submit_post_only_order(venue, long_sym, "buy", long_size, long_price, dry_run=dry_run)
    long_oid   = long_order.get("order_id", long_order.get("id", ""))
    long_filled = wait_for_fill(long_oid, timeout_sec=timeout, dry_run=dry_run)

    if not long_filled:
        # Long didn't fill — cancel and abort
        cancel_unfilled_order(long_oid, venue=venue, dry_run=dry_run)
        print(f"  [K449 PAIRED] Long timeout — aborting, retry next 8h cycle")
        _track_paired_fill_rate(venue, long_sym, short_sym, long_size,
                                False, False, False, False)
        return {
            "status":       "ABORTED",
            "reason":       "LONG_TIMEOUT",
            "long_filled":  False,
            "short_filled": False,
            "long_order":   long_order,
            "short_order":  None,
            "ts_utc":       ts,
        }

    # ── Step 2: POST_ONLY short leg (long filled) ──────────────────────────────
    short_mid   = get_mid_price(venue, short_sym)
    short_price = _tick_adjusted_price(short_mid, "sell", venue)
    print(f"  [K449 PAIRED] Step 2: POST_ONLY SHORT {short_sym} @ {short_price:.6f}  timeout={timeout}s")

    short_order = submit_post_only_order(venue, short_sym, "sell", short_size, short_price, dry_run=dry_run)
    short_oid   = short_order.get("order_id", short_order.get("id", ""))
    short_filled = wait_for_fill(short_oid, timeout_sec=timeout, dry_run=dry_run)

    if short_filled:
        # Both legs filled as POST_ONLY
        print(f"  [K449 PAIRED] Both legs POST_ONLY filled")
        _track_paired_fill_rate(venue, long_sym, short_sym, long_size,
                                True, True, False, False)
        _check_paired_fill_rate_alert()
        return {
            "status":       "BOTH_POST_ONLY",
            "long_filled":  True,
            "short_filled": True,
            "long_order":   long_order,
            "short_order":  short_order,
            "ts_utc":       ts,
        }

    # Short POST_ONLY timed out — IOC fallback for short only
    print(f"  [K449 PAIRED] Short POST_ONLY timeout → IOC fallback (avoid uncovered long)")
    cancel_unfilled_order(short_oid, venue=venue, dry_run=dry_run)
    short_ioc = submit_ioc_fallback(venue, short_sym, "sell", short_size, dry_run=dry_run)

    _track_paired_fill_rate(venue, long_sym, short_sym, long_size,
                            True, False, False, True)
    _check_paired_fill_rate_alert()

    return {
        "status":       "SHORT_IOC",
        "long_filled":  True,
        "short_filled": short_ioc.get("filled", False),
        "long_order":   long_order,
        "short_order":  short_ioc,
        "ts_utc":       ts,
    }


def _check_paired_fill_rate_alert() -> None:
    """Alert if paired trade fill rate drops below G8 threshold."""
    stats = get_paired_fill_stats()
    if stats["G8_paired_status"] == "FAIL":
        print(f"  [K449 PAIRED] ALERT: 60d paired fill rate = "
              f"{stats['both_post_only_rate']:.1%} < {FILL_RATE_ALERT_THRESH:.0%} "
              f"(K378 G8 gate FAIL)")


# ─────────────────────────────────────────────────────────────────────────────
# CLI Entry Point
# ─────────────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="K439 POST_ONLY Order Manager")
    parser.add_argument("--dry-run",   action="store_true", help="Simulate without real API calls")
    parser.add_argument("--stats",     action="store_true", help="Print 60d fill rate stats")
    parser.add_argument("--dashboard", action="store_true", help="Write dashboard JSON and exit")
    parser.add_argument("--test-flow", action="store_true", help="Run mock execute_trade() test")
    args = parser.parse_args()

    if args.stats:
        stats = get_daily_fill_stats()
        print(f"\n=== POST_ONLY Fill Rate Stats ({stats['window_days']}d window) ===")
        print(f"  Total orders:          {stats['total_orders']}")
        print(f"  POST_ONLY filled:      {stats['post_only_filled']}")
        print(f"  Fill rate:             {stats['post_only_fill_rate']:.1%}")
        print(f"  IOC fallbacks used:    {stats['ioc_used']}")
        print(f"  G8 gate status:        {stats['G8_gate_status']} (threshold ≥ {FILL_RATE_ALERT_THRESH:.0%})")
        print(f"\nPer-venue breakdown:")
        for venue, v in stats["by_venue"].items():
            if v["total"] > 0:
                print(f"  {venue}: {v['total']} orders  fill_rate={v['fill_rate']:.1%}  G8={v['g8_status']}")
        return

    if args.dashboard:
        dash = write_dashboard()
        print(f"\nDashboard: {DASHBOARD_JSON}")
        print(f"  G8 gate: {dash['stats_60d']['G8_gate_status']}")
        return

    if args.dry_run or args.test_flow:
        print("\n=== K439 POST_ONLY Order Manager — Dry-Run Test ===")
        print(f"  REPO_ROOT: {REPO_ROOT}")
        print(f"  FILLS_JSONL: {FILLS_JSONL}")
        print(f"  DASHBOARD: {DASHBOARD_JSON}")
        print(f"  POST_ONLY_ENABLED: {POST_ONLY_ENABLED}")
        print(f"  TIMEOUT: {POST_ONLY_TIMEOUT_SEC}s")
        print(f"  G8 THRESHOLD: {FILL_RATE_ALERT_THRESH:.0%}")

        # Test 1: POST_ONLY fills
        print("\n--- Test 1: LOW urgency (POST_ONLY → fill expected ~70%) ---")
        r1 = execute_trade("HL", "SOL", "short", 10000.0, urgency="LOW", dry_run=True)
        print(f"  Result: type={r1['type']}  filled={r1['filled']}  price={r1.get('fill_price')}")

        # Test 2: EMERGENCY bypass
        print("\n--- Test 2: EMERGENCY urgency (bypass POST_ONLY) ---")
        r2 = execute_trade("Bybit", "ETH", "sell", 5000.0, urgency="EMERGENCY", dry_run=True)
        print(f"  Result: type={r2['type']}  filled={r2['filled']}")

        # Test 3: MEDIUM urgency
        print("\n--- Test 3: MEDIUM urgency (60s timeout) ---")
        r3 = execute_trade("OKX", "BTC", "sell", 50000.0, urgency="MEDIUM", dry_run=True)
        print(f"  Result: type={r3['type']}  filled={r3['filled']}")

        # Write dashboard
        print("\n--- Writing dashboard JSON ---")
        dash = write_dashboard()
        print(f"  G8 gate: {dash['stats_60d']['G8_gate_status']}")
        print(f"  Total orders tracked: {dash['stats_60d']['total_orders']}")

        # Stats summary
        print("\n--- Fill rate stats ---")
        stats = get_daily_fill_stats()
        print(f"  60d total:    {stats['total_orders']} orders")
        print(f"  Fill rate:    {stats['post_only_fill_rate']:.1%}")
        print(f"  G8 status:    {stats['G8_gate_status']}")

        print(f"\n=== Dry-run complete. No real orders placed. ===")
        print(f"  Fills log: {FILLS_JSONL}")
        print(f"  Dashboard: {DASHBOARD_JSON}")
        return

    # Default: print help
    parser.print_help()


if __name__ == "__main__":
    main()

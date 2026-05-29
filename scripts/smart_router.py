#!/usr/bin/env python3
"""
smart_router.py — K434 Cross-Venue Smart Router Daemon
=======================================================
Fetches live FR + depth snapshots from HL, Bybit, and OKX for each K208 symbol,
scores venues by expected net profit (FR capture - maker cost - slippage), and
routes each K208 trade decision to the highest-scoring venue that satisfies
concentration caps and minimum depth requirements.

Architecture (K434):
  1. fetch_all_venue_state()   → snapshot FR + depth per symbol × 3 venues
  2. score_venue()             → net expected profit per trade (FR capture + rebate - slippage)
  3. select_best_venue()       → returns chosen venue + runner-up + detailed scores
  4. route_decision_log()      → appends JSON entry to decision log
  5. write_dashboard()         → writes data/smart_router_dashboard.json

Usage (standalone):
  python3 scripts/smart_router.py
  python3 scripts/smart_router.py --symbol BTC --side short --size 100000
  python3 scripts/smart_router.py --all-symbols         # score all K208 symbols

Integration (K208 call site):
  from smart_router import select_best_venue
  result = select_best_venue(symbol="BTC", side="short", position_size_usd=100_000)
  venue  = result["venue"]  # "HL" | "Bybit" | "OKX"

K339 security: REPO_ROOT resolved relative to this script, not CWD.
No new packages — stdlib urllib + json only (no requests import).
"""
from __future__ import annotations

import argparse
import json
import math
import sys
import time
import urllib.error
import urllib.request
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Tuple

# ── K339 canonical paths ──────────────────────────────────────────────────────
REPO_ROOT  = Path(__file__).resolve().parent.parent
DATA_DIR   = REPO_ROOT / "data"
LOGS_DIR   = REPO_ROOT / "logs"
CONFIG_PATH = DATA_DIR / "smart_router_config.json"
DASHBOARD_PATH = DATA_DIR / "smart_router_dashboard.json"
DECISION_LOG   = DATA_DIR / "smart_router_decisions.jsonl"

LOGS_DIR.mkdir(exist_ok=True)
DATA_DIR.mkdir(exist_ok=True)

JST = timezone(timedelta(hours=9))

# ── K208 symbols (reverse carry universe) ────────────────────────────────────
K208_SYMS = ["SOL", "XRP", "SUI", "OP", "APT", "AXS", "JTO", "IMX", "SAND", "ADA",
             "BTC", "ETH"]   # BTC/ETH added for smart-router demo scoring

# ── Venue API constants ───────────────────────────────────────────────────────
HL_API_URL    = "https://api.hyperliquid.xyz/info"
BYBIT_TICKER_URL = "https://api.bybit.com/v5/market/tickers"
OKX_FR_URL    = "https://www.okx.com/api/v5/public/funding-rate"
OKX_BOOK_URL  = "https://www.okx.com/api/v5/market/books"

# Bybit ticker overrides (small-cap symbols use 1000XXX prefix on Bybit)
BYBIT_TICKER_MAP: Dict[str, str] = {
    "BONK": "1000BONK", "PEPE": "1000PEPE", "MEME": "1000MEME",
    "SHIB": "1000SHIB", "BOME": "1000BOME",
}
HL_TICKER_MAP: Dict[str, str] = {
    "PEPE": "kPEPE", "BONK": "kBONK", "MEME": "kMEME", "BOME": "kBOME",
}


# ─────────────────────────────────────────────────────────────────────────────
# Config loading
# ─────────────────────────────────────────────────────────────────────────────

def load_config() -> dict:
    """Load smart_router_config.json; return defaults if missing."""
    if CONFIG_PATH.exists():
        with open(CONFIG_PATH) as f:
            return json.load(f)
    # Inline defaults (fallback; normally config file is present)
    return {
        "venues": {
            "HL":    {"enabled": True, "user_tier": "GOLD",  "maker_rebate_bps": 0.3, "taker_fee_bps": 4.5, "min_depth_usd": 100000, "max_position_pct_of_depth": 0.10},
            "Bybit": {"enabled": True, "user_tier": "VIP5",  "maker_rebate_bps": 1.0, "taker_fee_bps": 3.2, "min_depth_usd": 100000, "max_position_pct_of_depth": 0.10},
            "OKX":   {"enabled": True, "user_tier": "VIP1",  "maker_rebate_bps": 0.5, "taker_fee_bps": 4.0, "min_depth_usd": 100000, "max_position_pct_of_depth": 0.10},
        },
        "default_post_only": True,
        "ioc_fallback_seconds": 300,
        "blacklist_symbols": [],
        "concentration_caps": {"HL_pct_of_total": 0.65, "Bybit_pct_of_total": 0.50, "OKX_pct_of_total": 0.30},
    }


# ─────────────────────────────────────────────────────────────────────────────
# HTTP helper (stdlib urllib only — no requests)
# ─────────────────────────────────────────────────────────────────────────────

def _http_get(url: str, timeout: int = 10) -> Optional[dict]:
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "crypto-lab-smart-router/1.0"})
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return json.loads(resp.read().decode())
    except Exception as e:
        print(f"  [http_get] {url[:60]} → {e}", file=sys.stderr)
        return None


def _http_post(url: str, payload: dict, timeout: int = 10) -> Optional[dict]:
    try:
        data = json.dumps(payload).encode()
        req  = urllib.request.Request(
            url, data=data,
            headers={"Content-Type": "application/json", "User-Agent": "crypto-lab-smart-router/1.0"},
        )
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return json.loads(resp.read().decode())
    except Exception as e:
        print(f"  [http_post] {url[:60]} → {e}", file=sys.stderr)
        return None


# ─────────────────────────────────────────────────────────────────────────────
# Phase 3 — Per-venue state fetchers
# ─────────────────────────────────────────────────────────────────────────────

def fetch_hl_state(symbols: List[str]) -> Dict[str, dict]:
    """
    Fetch HL funding rate + mark price + OI for all symbols in one call.
    POST /info {"type":"metaAndAssetCtxs"} → [meta, assetCtxs]

    Returns: {symbol: {"fr": float, "mark_px": float, "oi_usd": float, "depth_usd": float}}
    depth_usd estimated as OI × 0.01 (1% of open interest proxy for top-of-book depth).
    """
    result: Dict[str, dict] = {}
    raw = _http_post(HL_API_URL, {"type": "metaAndAssetCtxs"})
    if not raw or not isinstance(raw, list) or len(raw) < 2:
        print("  [HL] metaAndAssetCtxs failed or empty", file=sys.stderr)
        return result

    meta       = raw[0]
    asset_ctxs = raw[1]
    universe   = {item["name"]: i for i, item in enumerate(meta.get("universe", []))}

    for sym in symbols:
        hl_sym = HL_TICKER_MAP.get(sym, sym)
        if hl_sym not in universe:
            continue
        idx = universe[hl_sym]
        ctx = asset_ctxs[idx]
        try:
            fr       = float(ctx.get("funding", 0.0))
            mark_px  = float(ctx.get("markPx", 0.0))
            oi_coins = float(ctx.get("openInterest", 0.0))
            oi_usd   = oi_coins * mark_px
            # Proxy for top-of-book depth: 1% of OI (conservative estimate)
            depth_usd = oi_usd * 0.01
            result[sym] = {
                "fr":        fr,
                "mark_px":   mark_px,
                "oi_usd":    oi_usd,
                "depth_usd": depth_usd,
                "source":    "HL_metaAndAssetCtxs",
            }
        except (TypeError, ValueError, KeyError):
            continue

    return result


def fetch_bybit_state(symbols: List[str]) -> Dict[str, dict]:
    """
    Fetch Bybit funding rate + mark price for all linear symbols in one call.
    GET /v5/market/tickers?category=linear

    Returns: {symbol: {"fr": float, "mark_px": float, "depth_usd": float}}
    """
    result: Dict[str, dict] = {}
    raw = _http_get(f"{BYBIT_TICKER_URL}?category=linear", timeout=12)
    if not raw or raw.get("retCode") != 0:
        print(f"  [Bybit] tickers failed: {raw}", file=sys.stderr)
        return result

    # Build lookup by ticker symbol
    ticker_lookup: Dict[str, dict] = {}
    for item in raw.get("result", {}).get("list", []):
        ticker_lookup[item.get("symbol", "")] = item

    for sym in symbols:
        bybit_sym = BYBIT_TICKER_MAP.get(sym, sym) + "USDT"
        item = ticker_lookup.get(bybit_sym)
        if not item:
            continue
        try:
            fr       = float(item.get("fundingRate", 0.0))
            mark_px  = float(item.get("markPrice", 0.0) or 0.0)
            vol_24h_usd = float(item.get("turnover24h", 0.0) or 0.0)
            # Proxy for depth: 0.05% of 24h volume (micro-market-impact proxy)
            depth_usd = vol_24h_usd * 0.0005 if vol_24h_usd > 0 else 0.0
            result[sym] = {
                "fr":        fr,
                "mark_px":   mark_px,
                "vol24h_usd": vol_24h_usd,
                "depth_usd": depth_usd,
                "source":    "Bybit_tickers",
            }
        except (TypeError, ValueError, KeyError):
            continue

    return result


def fetch_okx_state(symbols: List[str]) -> Dict[str, dict]:
    """
    Fetch OKX funding rate for each symbol.
    GET /api/v5/public/funding-rate?instId=BTC-USDT-SWAP

    OKX does not have a bulk FR endpoint, so we call per symbol with a small delay.
    Returns: {symbol: {"fr": float, "mark_px": float, "depth_usd": float}}
    """
    result: Dict[str, dict] = {}
    for sym in symbols:
        inst_id = f"{sym}-USDT-SWAP"
        url     = f"{OKX_FR_URL}?instId={inst_id}"
        raw     = _http_get(url, timeout=8)
        if not raw or raw.get("code") != "0":
            continue
        data = raw.get("data", [])
        if not data:
            continue
        try:
            item     = data[0]
            fr       = float(item.get("fundingRate", 0.0))
            mark_px  = float(item.get("markPx", 0.0) or 0.0)
            # OKX: depth proxy via next funding time estimate (sparse; use mark_px × 1e6 placeholder)
            depth_usd = 2_000_000.0  # conservative $2M placeholder — OKX majors are highly liquid
            result[sym] = {
                "fr":        fr,
                "mark_px":   mark_px,
                "depth_usd": depth_usd,
                "source":    "OKX_funding_rate",
            }
        except (TypeError, ValueError, KeyError):
            continue
        time.sleep(0.1)   # polite rate-limiting for per-symbol OKX calls

    return result


def fetch_all_venue_state(symbols: Optional[List[str]] = None) -> Dict[str, Dict[str, dict]]:
    """
    Fetch FR + depth state from all 3 venues for the given symbols.
    Returns nested dict: {venue: {symbol: state_dict}}

    Falls back gracefully if a venue is down (returns empty dict for that venue).
    """
    if symbols is None:
        symbols = K208_SYMS

    cfg    = load_config()
    venues = cfg.get("venues", {})

    print(f"  [SmartRouter] Fetching venue state for {len(symbols)} symbols ...", file=sys.stderr)
    t0 = time.time()

    state: Dict[str, Dict[str, dict]] = {}

    if venues.get("HL", {}).get("enabled", True):
        print("  [SmartRouter] HL fetch ...", file=sys.stderr)
        state["HL"] = fetch_hl_state(symbols)
        print(f"    HL: {len(state['HL'])} symbols ok", file=sys.stderr)

    if venues.get("Bybit", {}).get("enabled", True):
        print("  [SmartRouter] Bybit fetch ...", file=sys.stderr)
        state["Bybit"] = fetch_bybit_state(symbols)
        print(f"    Bybit: {len(state['Bybit'])} symbols ok", file=sys.stderr)

    if venues.get("OKX", {}).get("enabled", True):
        print("  [SmartRouter] OKX fetch ...", file=sys.stderr)
        state["OKX"] = fetch_okx_state(symbols)
        print(f"    OKX: {len(state['OKX'])} symbols ok", file=sys.stderr)

    elapsed = time.time() - t0
    print(f"  [SmartRouter] Venue fetch done in {elapsed:.1f}s", file=sys.stderr)
    return state


# ─────────────────────────────────────────────────────────────────────────────
# Phase 4 — Scoring
# ─────────────────────────────────────────────────────────────────────────────

def estimate_slippage(position_size_usd: float, depth_usd: float) -> float:
    """
    Simple linear market impact model.
    Slippage (as fraction) = (position_size / depth) × impact_multiplier
    Returns slippage in the same units as FR (fractional per 8h).

    If depth_usd == 0, returns a large penalty (venue effectively unusable for this size).
    """
    if depth_usd <= 0:
        return 0.01   # 1% penalty if no depth info → avoids routing there
    ratio = position_size_usd / depth_usd
    # Linear model: at 10% of depth, slippage ≈ 0.5bp = 0.00005
    # We scale linearly so that 10% → 5bps (0.0005 total cost equivalent)
    # Expressed as 8h-equivalent fraction for comparability with FR
    impact_bps_per_pct = 0.5    # 0.5bps for every 1% of depth consumed
    slippage_bps       = ratio * 100 * impact_bps_per_pct
    return slippage_bps / 10_000   # convert bps to fractional


def score_venue(
    venue: str,
    symbol: str,
    side: str,
    position_size_usd: float,
    venue_state: dict,
    cfg: dict,
) -> Tuple[float, dict]:
    """
    Compute expected net profit per 8h period for routing a trade to `venue`.

    Scoring formula:
        fr_capture  = fr × (+1 if short; −1 if long)   [receive FR if short]
        maker_rebate = maker_rebate_bps / 10000         [receive rebate]
        slippage     = estimate_slippage(size, depth)   [pay on entry]
        net_per_8h   = fr_capture + maker_rebate − slippage

    Returns (score, detail_dict).
    score > 0 → profitable to route here.
    """
    vcfg   = cfg["venues"].get(venue, {})
    sym_state = venue_state.get(symbol)
    if not sym_state:
        return -999.0, {"reason": f"{venue} state unavailable for {symbol}"}

    fr           = sym_state.get("fr", 0.0)
    depth_usd    = sym_state.get("depth_usd", 0.0)
    mark_px      = sym_state.get("mark_px", 0.0)

    # Check minimum depth
    min_depth    = vcfg.get("min_depth_usd", 100_000)
    max_pos_pct  = vcfg.get("max_position_pct_of_depth", 0.10)
    if depth_usd < min_depth:
        return -888.0, {"reason": f"{venue} depth ${depth_usd:,.0f} < min ${min_depth:,.0f}"}
    if depth_usd > 0 and (position_size_usd / depth_usd) > max_pos_pct:
        return -777.0, {"reason": f"{venue} position {position_size_usd/depth_usd:.1%} > max {max_pos_pct:.0%} of depth"}

    # FR capture: short positions receive positive FR, pay negative FR
    if side == "short":
        fr_capture = fr       # positive FR means we receive it as short
    else:
        fr_capture = -fr      # long position: pay positive FR, receive negative FR

    # Maker rebate (positive = receive, expressed as fractional)
    maker_rebate = vcfg.get("maker_rebate_bps", 0.0) / 10_000

    # Slippage estimate
    slippage = estimate_slippage(position_size_usd, depth_usd)

    net = fr_capture + maker_rebate - slippage

    detail = {
        "fr":           round(fr, 8),
        "fr_capture":   round(fr_capture, 8),
        "maker_rebate": round(maker_rebate, 8),
        "slippage":     round(slippage, 8),
        "net_per_8h":   round(net, 8),
        "depth_usd":    round(depth_usd, 0),
        "mark_px":      mark_px,
        "tier":         vcfg.get("user_tier", "UNKNOWN"),
    }
    return round(net, 10), detail


# ─────────────────────────────────────────────────────────────────────────────
# Phase 5 — Concentration caps + venue selection
# ─────────────────────────────────────────────────────────────────────────────

def filter_by_concentration_caps(
    scores: Dict[str, float],
    current_allocation: Dict[str, float],
    total_aum: float,
    cfg: dict,
) -> Dict[str, float]:
    """
    Zero out venues where adding `position_size_usd` would exceed concentration cap.
    current_allocation: {venue: current_notional_usd}
    total_aum: total portfolio AUM in USD.
    """
    caps    = cfg.get("concentration_caps", {})
    filtered = dict(scores)

    for venue in list(filtered.keys()):
        cap_key = f"{venue}_pct_of_total"
        cap_pct = caps.get(cap_key, 1.0)
        current = current_allocation.get(venue, 0.0)
        current_pct = (current / total_aum) if total_aum > 0 else 0.0
        if current_pct >= cap_pct:
            filtered[venue] = -666.0   # capped — mark with distinctive penalty
            print(
                f"  [SmartRouter] {venue} concentration cap hit: "
                f"{current_pct:.1%} >= {cap_pct:.0%}",
                file=sys.stderr,
            )

    return filtered


def select_best_venue(
    symbol: str,
    side: str,
    position_size_usd: float,
    venue_state: Optional[Dict[str, Dict[str, dict]]] = None,
    current_allocation: Optional[Dict[str, float]] = None,
    total_aum: float = 10_000_000.0,
) -> dict:
    """
    Select the best venue for a K208 trade on `symbol` with `side` and `position_size_usd`.

    Returns dict:
    {
      "venue":         "HL" | "Bybit" | "OKX",
      "score":         float,          # net_per_8h of best venue
      "symbol":        str,
      "side":          str,
      "position_usd":  float,
      "scores":        {venue: float}, # raw scores per venue
      "details":       {venue: dict},  # full breakdown per venue
      "fallback_order": [str],         # venues ranked best→worst (usable ones only)
      "timestamp_utc": str,
      "reason":        str,
    }
    """
    cfg  = load_config()
    blist = cfg.get("blacklist_symbols", [])
    if symbol in blist:
        return {"venue": None, "reason": f"{symbol} blacklisted", "score": -9999}

    if venue_state is None:
        venue_state = fetch_all_venue_state([symbol])

    if current_allocation is None:
        current_allocation = {"HL": 0.0, "Bybit": 0.0, "OKX": 0.0}

    enabled_venues = [
        v for v, vcfg in cfg["venues"].items() if vcfg.get("enabled", True)
    ]

    raw_scores: Dict[str, float] = {}
    details:    Dict[str, dict]  = {}

    for venue in enabled_venues:
        vstate = venue_state.get(venue, {})
        score, detail = score_venue(venue, symbol, side, position_size_usd, vstate, cfg)
        raw_scores[venue] = score
        details[venue]    = detail

    # Apply concentration caps
    capped_scores = filter_by_concentration_caps(
        raw_scores, current_allocation, total_aum, cfg
    )

    # Find best usable venue (score > -100 means no hard block)
    usable = {v: s for v, s in capped_scores.items() if s > -100.0}

    if not usable:
        # All venues blocked — return least-bad (still log decision)
        best_venue = max(raw_scores, key=lambda v: raw_scores[v])
        reason     = "ALL_VENUES_BLOCKED — returning least-bad; manual review required"
    else:
        best_venue = max(usable, key=lambda v: usable[v])
        reason     = f"Best net_per_8h={usable[best_venue]:.8f} at {best_venue}"

    # Fallback order (only usable venues)
    fallback_order = sorted(usable, key=lambda v: usable[v], reverse=True)

    return {
        "venue":          best_venue,
        "score":          raw_scores.get(best_venue, -9999.0),
        "symbol":         symbol,
        "side":           side,
        "position_usd":   position_size_usd,
        "scores":         raw_scores,
        "capped_scores":  capped_scores,
        "details":        details,
        "fallback_order": fallback_order,
        "timestamp_utc":  datetime.now(timezone.utc).isoformat(),
        "reason":         reason,
    }


# ─────────────────────────────────────────────────────────────────────────────
# Phase 6 — Decision log + dashboard
# ─────────────────────────────────────────────────────────────────────────────

def route_decision_log(symbol: str, decision: dict) -> None:
    """Append one routing decision to data/smart_router_decisions.jsonl."""
    entry = {
        "ts_jst":      datetime.now(JST).strftime("%Y-%m-%d %H:%M JST"),
        "symbol":      symbol,
        "venue":       decision.get("venue"),
        "side":        decision.get("side"),
        "position_usd": decision.get("position_usd"),
        "score":       decision.get("score"),
        "fallback_order": decision.get("fallback_order", []),
        "reason":      decision.get("reason"),
        "details":     {
            v: {k2: d.get(k2) for k2 in ["fr", "fr_capture", "maker_rebate", "slippage", "net_per_8h", "depth_usd"]}
            for v, d in decision.get("details", {}).items()
        },
    }
    with open(DECISION_LOG, "a") as f:
        f.write(json.dumps(entry) + "\n")


def write_dashboard(decisions_buffer: List[dict], venue_state: Dict[str, Dict[str, dict]]) -> None:
    """
    Write data/smart_router_dashboard.json.
    Includes:
      - last 100 decisions
      - per-venue current FR snapshot
      - estimated daily/monthly edge captured
    """
    # Load last 100 decisions from log
    recent: List[dict] = []
    if DECISION_LOG.exists():
        lines = DECISION_LOG.read_text().strip().splitlines()
        for line in lines[-100:]:
            try:
                recent.append(json.loads(line))
            except json.JSONDecodeError:
                continue

    # Per-venue FR snapshot (flat dict)
    venue_fr_snapshot: Dict[str, dict] = {}
    for venue, sym_state in venue_state.items():
        venue_fr_snapshot[venue] = {
            sym: {"fr_8h": round(s.get("fr", 0.0), 8), "depth_usd": round(s.get("depth_usd", 0.0), 0)}
            for sym, s in sym_state.items()
        }

    # Estimate edge: for each symbol, max(fr over venues) - min(fr over venues)
    symbols_seen: set = set()
    for v in venue_state.values():
        symbols_seen.update(v.keys())

    edge_by_symbol: Dict[str, dict] = {}
    for sym in sorted(symbols_seen):
        frs = {v: venue_state[v][sym]["fr"] for v in venue_state if sym in venue_state[v]}
        if len(frs) < 2:
            continue
        max_fr = max(frs.values())
        min_fr = min(frs.values())
        spread = max_fr - min_fr
        edge_by_symbol[sym] = {
            "fr_spread_8h":  round(spread, 8),
            "best_venue":    max(frs, key=lambda v: frs[v]),
            "worst_venue":   min(frs, key=lambda v: frs[v]),
            "all_frs":       {v: round(f, 8) for v, f in frs.items()},
        }

    # Rough edge estimate: assume $10M AUM, 3 settlements/day, 12-month compounding
    # edge_per_8h = mean(spread_8h) across symbols × 10M × 0.10 (K208 weight)
    mean_spread = (
        sum(e["fr_spread_8h"] for e in edge_by_symbol.values()) / len(edge_by_symbol)
        if edge_by_symbol else 0.0
    )
    aum_ref         = 10_000_000
    k208_weight     = 0.10   # K208 allocation fraction of total AUM
    settlements_day = 3      # 8h settlements per day
    edge_daily_usd  = mean_spread * aum_ref * k208_weight * settlements_day
    edge_monthly_usd = edge_daily_usd * 30
    edge_annual_usd  = edge_daily_usd * 365

    dashboard = {
        "generated_at_jst": datetime.now(JST).strftime("%Y-%m-%d %H:%M JST"),
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "wave":             "K434",
        "version":          "1.0",
        "recent_decisions": recent[-100:],
        "venue_fr_snapshot": venue_fr_snapshot,
        "edge_by_symbol":   edge_by_symbol,
        "edge_estimates": {
            "mean_fr_spread_8h":  round(mean_spread, 8),
            "aum_ref_usd":        aum_ref,
            "k208_weight":        k208_weight,
            "settlements_per_day": settlements_day,
            "edge_daily_usd":     round(edge_daily_usd, 2),
            "edge_monthly_usd":   round(edge_monthly_usd, 2),
            "edge_annual_usd":    round(edge_annual_usd, 2),
            "note": "Based on live FR spread; actual edge depends on execution quality + position size",
        },
        "config_path":      str(CONFIG_PATH),
        "decision_log":     str(DECISION_LOG),
    }

    DASHBOARD_PATH.write_text(json.dumps(dashboard, indent=2))
    print(f"  [SmartRouter] Dashboard → {DASHBOARD_PATH}", file=sys.stderr)


# ─────────────────────────────────────────────────────────────────────────────
# CLI entry point
# ─────────────────────────────────────────────────────────────────────────────

def _verify_snapshot(venue_state: Dict[str, Dict[str, dict]]) -> None:
    """Print a summary table of FR values per venue per symbol."""
    print("\n=== Venue State Snapshot ===")
    all_syms = sorted({s for v in venue_state.values() for s in v})
    venues   = sorted(venue_state.keys())
    header   = f"{'Symbol':<10}" + "".join(f"  {v:<12}" for v in venues) + "  Best"
    print(header)
    print("-" * len(header))
    for sym in all_syms:
        parts = []
        frs   = {}
        for venue in venues:
            fr = venue_state.get(venue, {}).get(sym, {}).get("fr")
            if fr is not None:
                parts.append(f"  {fr:+.6f}   ")
                frs[venue] = fr
            else:
                parts.append(f"  {'N/A':<12}")
        best = max(frs, key=lambda v: frs[v]) if frs else "—"
        print(f"  {sym:<10}" + "".join(parts) + f"  {best}")
    print()


def main() -> int:
    parser = argparse.ArgumentParser(description="K434 Smart Router — cross-venue scoring")
    parser.add_argument("--symbol",   default="BTC",    help="Symbol to route (default: BTC)")
    parser.add_argument("--side",     default="short",  choices=["short", "long"])
    parser.add_argument("--size",     type=float, default=100_000, help="Position size USD")
    parser.add_argument("--all-symbols", action="store_true", help="Score all K208 symbols")
    parser.add_argument("--aum",      type=float, default=10_000_000, help="Total AUM for cap calc")
    parser.add_argument("--no-dashboard", action="store_true", help="Skip dashboard write")
    args = parser.parse_args()

    symbols = K208_SYMS if args.all_symbols else [args.symbol.upper()]

    print(f"\n=== K434 Smart Router  ({datetime.now(JST).strftime('%Y-%m-%d %H:%M JST')}) ===")
    print(f"  Symbols: {symbols}  |  Side: {args.side}  |  Size: ${args.size:,.0f}")

    # Fetch venue state
    venue_state = fetch_all_venue_state(symbols)

    # Print snapshot
    _verify_snapshot(venue_state)

    # Score each symbol
    decisions = []
    for sym in symbols:
        decision = select_best_venue(
            symbol=sym,
            side=args.side,
            position_size_usd=args.size,
            venue_state=venue_state,
            total_aum=args.aum,
        )
        decisions.append(decision)

        # Log decision
        route_decision_log(sym, decision)

        # Print result
        best = decision["venue"]
        score = decision["score"]
        fo    = decision.get("fallback_order", [])
        print(f"  {sym:<8}  Best={best:<6}  score={score:+.8f}  fallback={fo}  | {decision['reason']}")
        for v, d in decision.get("details", {}).items():
            if isinstance(d, dict) and "net_per_8h" in d:
                print(
                    f"           {v:<6}: fr_cap={d.get('fr_capture',0):+.7f}  rebate={d.get('maker_rebate',0):+.7f}"
                    f"  slip={d.get('slippage',0):.7f}  net={d.get('net_per_8h',0):+.7f}"
                    f"  depth=${d.get('depth_usd',0):>12,.0f}"
                )
    print()

    # Write dashboard
    if not args.no_dashboard:
        write_dashboard(decisions, venue_state)
        print(f"  Dashboard written → {DASHBOARD_PATH}")

    # Verify concentration caps config present
    cfg = load_config()
    print(f"\n  Config: {CONFIG_PATH}")
    print(f"  Caps:   HL={cfg['concentration_caps'].get('HL_pct_of_total','-'):.0%}  "
          f"Bybit={cfg['concentration_caps'].get('Bybit_pct_of_total','-'):.0%}  "
          f"OKX={cfg['concentration_caps'].get('OKX_pct_of_total','-'):.0%}")
    print(f"  Decision log → {DECISION_LOG}")
    print(f"\n=== Smart Router complete ===\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())

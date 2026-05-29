#!/usr/bin/env python3
"""
aevo_fr_fetcher.py — K460 Aevo Funding Rate Fetcher (K454 v6.20 4th venue)
============================================================================
Fetches Aevo perpetual funding rates and caches them as Parquet for
downstream use by K208 strategy adapter and K434 smart router.

Architecture:
  - fetch_aevo_funding_rate(symbol)       → live current FR dict
  - fetch_aevo_history(symbol, days=30)   → 30d historical FR DataFrame
  - save_aevo_fr_cache(symbol, df)        → cache/aevo_fr_{symbol}.parquet
  - fetch_and_cache_all(symbols)          → run all symbols in sequence
  - write_aevo_dashboard()               → data/aevo_dashboard.json

Aevo REST API base: https://api.aevo.xyz
  - GET /funding?instrument_name=BTC-PERP   (current FR + next epoch)
  - GET /markets                            (active perp markets + mark price)
  - GET /orderbook?instrument_name=BTC-PERP (L2 depth)

Auth: NOT required for public endpoints (read-only data).

Note on Aevo FR format:
  - funding_rate: fractional (e.g. 0.000008 = 0.0008%)
  - next_epoch: nanosecond Unix timestamp
  - Settlement: 1h intervals (vs 8h on HL/Bybit/OKX)
  - Annualized: FR × 24 × 365 × 100 (24 periods/day for 1h cycle)

K208 Integration (4th venue — K454 v6.20 expansion):
  - K208 short-highest-FR / long-lowest-FR now spans HL + Bybit + OKX + Aevo.
  - Aevo specializes in structured products + smaller altcoin perps.
  - K434 smart router uses this fetcher's output as Aevo venue score input.

K460 context:
  - Wave 5/7 toward v6.20 architecture (K454 plan: venues 3→10).
  - Aevo is 4th major venue (HL=1st, Bybit=2nd, OKX=3rd).
  - StartInterval: 3600 (1h — matches Aevo 1h funding cycle).
  - Daemon: com.cryptolab.aevo-fr-monitor (23rd daemon, SCAFFOLD-READY).

K339 Security:
  REPO_ROOT = Path(__file__).resolve().parent.parent — no /Users/ literals.
  Aevo API keys NOT required for read-only fetch endpoints.

Usage:
  python3 scripts/aevo_fr_fetcher.py                     # BTC-PERP
  python3 scripts/aevo_fr_fetcher.py --symbol ETH-PERP
  python3 scripts/aevo_fr_fetcher.py --all               # all K208 symbols
  python3 scripts/aevo_fr_fetcher.py --history --days 30
  python3 scripts/aevo_fr_fetcher.py --dashboard          # print dashboard JSON

Dependencies: stdlib only (urllib, json, pathlib) + pandas (for parquet cache)
"""
from __future__ import annotations

import argparse
import json
import sys
import time
import urllib.error
import urllib.request
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Dict, List, Optional

# ── K339: REPO_ROOT from __file__, no /Users/ literals ───────────────────────
REPO_ROOT = Path(__file__).resolve().parent.parent
CACHE_DIR = REPO_ROOT / "cache"
DATA_DIR  = REPO_ROOT / "data"
LOGS_DIR  = REPO_ROOT / "logs"

CACHE_DIR.mkdir(exist_ok=True)
DATA_DIR.mkdir(exist_ok=True)
LOGS_DIR.mkdir(exist_ok=True)

JST = timezone(timedelta(hours=9))

# ── Aevo REST API constants ──────────────────────────────────────────────────
AEVO_BASE_URL        = "https://api.aevo.xyz"
AEVO_FUNDING_EP      = "/funding"           # ?instrument_name=BTC-PERP
AEVO_MARKETS_EP      = "/markets"
AEVO_ORDERBOOK_EP    = "/orderbook"         # ?instrument_name=BTC-PERP

# Aevo 1h funding cycle (vs 8h on OKX/Bybit/HL)
AEVO_PERIODS_PER_DAY = 24
AEVO_FUNDING_INTERVAL_SEC = 3600

# ── K208 universe symbols (Aevo perp format: {BASE}-PERP) ────────────────────
# Aevo specializes in: BTC, ETH, SOL + structured products
# Subset of 50+ universe available on Aevo perps
K208_SYMBOLS_AEVO: List[str] = [
    "BTC-PERP",
    "ETH-PERP",
    "SOL-PERP",
    "ARB-PERP",
    "OP-PERP",
    "AEVO-PERP",
    "SUI-PERP",
    "ATOM-PERP",
    "APE-PERP",
    "DOGE-PERP",
    "AVAX-PERP",
    "LINK-PERP",
    "BNB-PERP",
    "XRP-PERP",
]

DASHBOARD_PATH = DATA_DIR / "aevo_dashboard.json"
DECISION_LOG   = DATA_DIR / "aevo_fr_decisions.jsonl"


# ─────────────────────────────────────────────────────────────────────────────
# HTTP helpers (stdlib urllib only — no requests dependency)
# ─────────────────────────────────────────────────────────────────────────────

def _http_get(url: str, timeout: int = 10) -> Optional[dict]:
    """
    Lightweight GET request using stdlib urllib.
    Returns parsed JSON dict, or None on any error.
    K339: user-agent identifies this as crypto-lab tooling.
    """
    try:
        req = urllib.request.Request(
            url,
            headers={
                "User-Agent": "crypto-lab-aevo-fr-fetcher/1.0",
                "Accept":     "application/json",
            },
        )
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            body = resp.read().decode("utf-8")
            return json.loads(body)
    except urllib.error.HTTPError as exc:
        print(f"  [aevo_fr_fetcher] HTTP {exc.code}: {url}", file=sys.stderr)
        return None
    except urllib.error.URLError as exc:
        print(f"  [aevo_fr_fetcher] URL error: {exc.reason} — {url}", file=sys.stderr)
        return None
    except Exception as exc:
        print(f"  [aevo_fr_fetcher] Error: {exc} — {url}", file=sys.stderr)
        return None


# ─────────────────────────────────────────────────────────────────────────────
# Core fetch functions
# ─────────────────────────────────────────────────────────────────────────────

def fetch_aevo_funding_rate(symbol: str = "BTC-PERP") -> dict:
    """
    Fetch live current funding rate for a single Aevo perpetual.

    Aevo endpoint: GET /funding?instrument_name={symbol}
    Response fields:
      funding_rate — current rate (fractional, 1h period)
      next_epoch   — next settlement timestamp (nanoseconds)

    Aevo FR note: 1h settlement cycle (24 periods/day).
    Annualized = FR × 24 × 365 × 100

    Returns:
        {
            "symbol":           "BTC-PERP",
            "funding_rate":     float,   # e.g. 0.000008 per 1h
            "next_epoch_ns":    int,     # next settlement (nanoseconds)
            "next_epoch_sec":   int,     # human-readable (seconds)
            "annualized_pct":   float,   # FR × 24 × 365 × 100
            "mark_px":          float,   # from markets endpoint (may be None)
            "fetched_at_utc":   str,
            "source":           "Aevo_public_api",
            "ok":               bool,
            "settlement_period_h": 1,    # 1h Aevo cycle
        }

    On failure: returns dict with ok=False and error message.
    """
    url = f"{AEVO_BASE_URL}{AEVO_FUNDING_EP}?instrument_name={symbol}"
    raw = _http_get(url, timeout=10)

    base = {
        "symbol":               symbol,
        "fetched_at_utc":       datetime.now(timezone.utc).isoformat(),
        "source":               "Aevo_public_api",
        "settlement_period_h":  1,
    }

    if raw is None:
        return {**base, "ok": False, "error": "HTTP request failed"}

    # Aevo returns: {"funding_rate": "0.000008", "next_epoch": "1780070400000000000"}
    try:
        fr_raw       = raw.get("funding_rate", "0")
        epoch_ns_raw = raw.get("next_epoch", "0")

        fr         = float(fr_raw) if fr_raw else 0.0
        epoch_ns   = int(epoch_ns_raw) if epoch_ns_raw else 0
        epoch_sec  = epoch_ns // 1_000_000_000 if epoch_ns else 0
        # Annualized: FR per 1h × 24 periods/day × 365 days × 100 = %
        annualized = fr * AEVO_PERIODS_PER_DAY * 365 * 100

        return {
            **base,
            "funding_rate":     fr,
            "next_epoch_ns":    epoch_ns,
            "next_epoch_sec":   epoch_sec,
            "annualized_pct":   round(annualized, 4),
            "mark_px":          None,   # fetched separately via /markets
            "ok":               True,
        }
    except (TypeError, ValueError, KeyError) as exc:
        return {**base, "ok": False, "error": f"Parse error: {exc}"}


def fetch_aevo_markets() -> Dict[str, dict]:
    """
    Fetch all active Aevo perpetual markets (mark price, index price, OI).

    GET /markets
    Returns: {symbol: {mark_price, index_price, open_interest, ...}}
    Falls back to empty dict on failure.
    """
    url = f"{AEVO_BASE_URL}{AEVO_MARKETS_EP}"
    raw = _http_get(url, timeout=15)
    if raw is None:
        return {}

    # Response is a list of market objects
    markets: Dict[str, dict] = {}
    data = raw if isinstance(raw, list) else raw.get("markets", [])
    for item in data:
        name = item.get("instrument_name", "")
        if not name.endswith("-PERP"):
            continue
        markets[name] = {
            "mark_price":     _safe_float(item.get("mark_price")),
            "index_price":    _safe_float(item.get("index_price")),
            "open_interest":  _safe_float(item.get("open_interest")),
            "max_leverage":   _safe_float(item.get("max_leverage")),
            "is_active":      item.get("is_active", True),
        }
    return markets


def _safe_float(val) -> Optional[float]:
    """Convert str/float/None to float safely."""
    if val is None:
        return None
    try:
        return float(val)
    except (TypeError, ValueError):
        return None


def fetch_aevo_history(
    symbol: str = "BTC-PERP",
    days:   int = 30,
) -> "pd.DataFrame":  # type: ignore[name-defined]
    """
    Synthesize funding rate history from repeated snapshots or return empty.

    NOTE: Aevo public API does not expose a historical funding rate endpoint
    in the documented public REST. This function fetches the current rate
    and, if a cached Parquet exists, appends to it. Full backfill requires
    authenticated access or websocket accumulation.

    Returns:
        pd.DataFrame with columns:
          fundingTime   (datetime, UTC)
          fundingRate   (float)
          symbol        (str)

    Returns empty DataFrame if no data available.
    """
    try:
        import pandas as pd
    except ImportError:
        print("  [aevo_fr_fetcher] pandas not available", file=sys.stderr)
        import types
        empty_df = types.SimpleNamespace()
        empty_df.empty = True
        return empty_df  # type: ignore

    # Load existing cache if present
    safe_sym = symbol.replace("/", "_").replace("-", "_")
    cache_path = CACHE_DIR / f"aevo_fr_{safe_sym}.parquet"
    existing_records = []

    if cache_path.is_file():
        try:
            existing_df = pd.read_parquet(cache_path)
            existing_records = existing_df.to_dict("records")
            print(
                f"  [aevo_fr_fetcher] Loaded {len(existing_records)} cached rows for {symbol}",
                file=sys.stderr,
            )
        except Exception as exc:
            print(f"  [aevo_fr_fetcher] Cache load error: {exc}", file=sys.stderr)

    # Append current snapshot
    current = fetch_aevo_funding_rate(symbol)
    if current.get("ok"):
        existing_records.append({
            "fundingTime": pd.Timestamp.now(tz="UTC"),
            "fundingRate": current["funding_rate"],
            "symbol":      symbol,
        })

    if not existing_records:
        return pd.DataFrame()

    df = pd.DataFrame(existing_records)
    # Filter to requested days window
    cutoff = pd.Timestamp.now(tz="UTC") - pd.Timedelta(days=days)
    if "fundingTime" in df.columns:
        # Ensure datetime type
        df["fundingTime"] = pd.to_datetime(df["fundingTime"], utc=True)
        df = df[df["fundingTime"] >= cutoff]

    df = df.sort_values("fundingTime").reset_index(drop=True)
    print(
        f"  [aevo_fr_fetcher] History: {symbol} — {len(df)} records ({days}d window)",
        file=sys.stderr,
    )
    return df


def fetch_aevo_orderbook_depth(symbol: str = "BTC-PERP") -> float:
    """
    Estimate top-of-book depth (USD) from Aevo order book.
    GET /orderbook?instrument_name={symbol}

    Returns depth_usd estimate. Falls back to 500_000.0 (conservative for Aevo).
    """
    url = f"{AEVO_BASE_URL}{AEVO_ORDERBOOK_EP}?instrument_name={symbol}"
    raw = _http_get(url, timeout=8)
    if raw is None:
        return 500_000.0

    try:
        bids = raw.get("bids", [])
        asks = raw.get("asks", [])
        # Aevo format: [[price, size], ...] (strings)
        bid_depth = sum(float(b[0]) * float(b[1]) for b in bids[:5] if len(b) >= 2)
        ask_depth = sum(float(a[0]) * float(a[1]) for a in asks[:5] if len(a) >= 2)
        return bid_depth + ask_depth
    except (TypeError, ValueError, IndexError):
        return 500_000.0


# ─────────────────────────────────────────────────────────────────────────────
# Cache management
# ─────────────────────────────────────────────────────────────────────────────

def save_aevo_fr_cache(symbol: str, df: "pd.DataFrame") -> Path:  # type: ignore[name-defined]
    """
    Write funding rate history DataFrame to cache/aevo_fr_{symbol}.parquet.

    symbol: e.g. "BTC-PERP" (Aevo format)
    df:     DataFrame from fetch_aevo_history()

    Returns: Path to written file.
    K339: uses REPO_ROOT-relative path, no absolute /Users/ literal.
    """
    safe_sym = symbol.replace("/", "_").replace("-", "_")
    path = CACHE_DIR / f"aevo_fr_{safe_sym}.parquet"
    try:
        df.to_parquet(path, index=False)
        print(
            f"  [aevo_fr_fetcher] Cache written: {path.name} ({len(df)} rows)",
            file=sys.stderr,
        )
    except Exception as exc:
        print(f"  [aevo_fr_fetcher] Cache write error: {exc}", file=sys.stderr)
    return path


def load_aevo_fr_cache(symbol: str) -> Optional["pd.DataFrame"]:  # type: ignore[name-defined]
    """Load cached FR history. Returns DataFrame or None if cache missing."""
    try:
        import pandas as pd
    except ImportError:
        return None

    safe_sym = symbol.replace("/", "_").replace("-", "_")
    path = CACHE_DIR / f"aevo_fr_{safe_sym}.parquet"
    if not path.is_file():
        return None
    try:
        return pd.read_parquet(path)
    except Exception as exc:
        print(f"  [aevo_fr_fetcher] Cache load error: {exc}", file=sys.stderr)
        return None


# ─────────────────────────────────────────────────────────────────────────────
# Dashboard I/O
# ─────────────────────────────────────────────────────────────────────────────

def write_aevo_dashboard(
    fr_results: Dict[str, dict],
    markets:    Optional[Dict[str, dict]] = None,
    depth_map:  Optional[Dict[str, float]] = None,
) -> None:
    """
    Write data/aevo_dashboard.json with latest FR snapshot.

    Schema:
      last_poll_utc     — ISO timestamp of this poll
      last_poll_jst     — JST-formatted string
      btc_fr            — BTC funding rate (fractional, 1h period)
      eth_fr            — ETH funding rate (fractional, 1h period)
      symbols           — list of per-symbol dicts
      daemon_label      — com.cryptolab.aevo-fr-monitor
      wave              — K460
      status            — SCAFFOLD-READY
      venue             — Aevo
    """
    now_utc = datetime.now(timezone.utc)
    now_jst = now_utc.astimezone(JST)

    markets = markets or {}
    symbol_rows = []
    for sym, d in fr_results.items():
        mkt = markets.get(sym, {})
        symbol_rows.append({
            "symbol":         sym,
            "funding_rate":   d.get("funding_rate", 0.0),
            "mark_px":        mkt.get("mark_price") or d.get("mark_px"),
            "annualized_pct": d.get("annualized_pct", 0.0),
            "next_epoch_sec": d.get("next_epoch_sec", 0),
            "open_interest":  mkt.get("open_interest"),
            "ok":             d.get("ok", False),
        })

    btc_d = fr_results.get("BTC-PERP", {})
    eth_d = fr_results.get("ETH-PERP", {})
    btc_m = markets.get("BTC-PERP", {})
    eth_m = markets.get("ETH-PERP", {})

    payload = {
        "_comment": (
            "K460 Aevo FR Monitor dashboard "
            "(K454 v6.20 4th venue, 23rd daemon, 1h funding cycle)"
        ),
        "_wave":           "K460",
        "last_poll_utc":   now_utc.isoformat(),
        "last_poll_jst":   now_jst.strftime("%Y-%m-%d %H:%M JST"),
        "btc_fr":          btc_d.get("funding_rate", None),
        "btc_mark_px":     btc_m.get("mark_price"),
        "btc_annualized":  btc_d.get("annualized_pct", None),
        "eth_fr":          eth_d.get("funding_rate", None),
        "eth_mark_px":     eth_m.get("mark_price"),
        "eth_annualized":  eth_d.get("annualized_pct", None),
        "symbols":         symbol_rows,
        "depth_map_usd":   depth_map or {},
        "daemon_label":    "com.cryptolab.aevo-fr-monitor",
        "daemon_number":   23,
        "start_interval":  AEVO_FUNDING_INTERVAL_SEC,   # 3600 = 1h
        "settlement_period_h": 1,
        "status":          "SCAFFOLD-READY",
        "venue":           "Aevo",
        "api_base":        AEVO_BASE_URL,
        "version_target":  "v6.20",
        "k208_venues":     ["HL", "Bybit", "OKX", "Aevo"],
        "notes": (
            "Aevo uses 1h funding cycle (vs 8h HL/Bybit/OKX). "
            "Annualized = FR × 24 × 365 × 100. "
            "No historical endpoint on public REST; cache accumulates via polling."
        ),
    }

    tmp = DASHBOARD_PATH.with_suffix(".tmp")
    with open(tmp, "w") as f:
        json.dump(payload, f, indent=2)
    tmp.replace(DASHBOARD_PATH)
    print(
        f"  [aevo_fr_fetcher] Dashboard written: {DASHBOARD_PATH.name}",
        file=sys.stderr,
    )


# ─────────────────────────────────────────────────────────────────────────────
# Bulk fetch (daemon entry point)
# ─────────────────────────────────────────────────────────────────────────────

def fetch_and_cache_all(
    symbols:      Optional[List[str]] = None,
    history_days: int = 30,
    fetch_depth:  bool = False,
) -> Dict[str, dict]:
    """
    Main daemon loop: fetch live FR for all symbols, update cache,
    and write dashboard.

    Called by com.cryptolab.aevo-fr-monitor daemon every 1h.

    Args:
        symbols:       Aevo symbol list (default: K208_SYMBOLS_AEVO)
        history_days:  Days of history window for cache (default 30)
        fetch_depth:   Whether to fetch order book depth (slower)

    Returns:
        fr_results dict {symbol: result_dict}
    """
    if symbols is None:
        symbols = K208_SYMBOLS_AEVO

    print(
        f"  [aevo_fr_fetcher] Starting bulk fetch: {len(symbols)} symbols",
        file=sys.stderr,
    )
    t0 = time.time()

    # Fetch markets once (mark prices, OI)
    markets = fetch_aevo_markets()
    print(
        f"  [aevo_fr_fetcher] Markets fetched: {len(markets)} perps",
        file=sys.stderr,
    )

    fr_results: Dict[str, dict] = {}
    depth_map:  Dict[str, float] = {}

    for sym in symbols:
        result = fetch_aevo_funding_rate(sym)
        # Enrich with mark price from markets
        if sym in markets:
            result["mark_px"] = markets[sym].get("mark_price")
        fr_results[sym] = result

        if result.get("ok"):
            fr  = result["funding_rate"]
            ann = result.get("annualized_pct", fr * AEVO_PERIODS_PER_DAY * 365 * 100)
            mk  = result.get("mark_px") or 0.0
            print(
                f"    {sym:<16s}  FR={fr*100:+.6f}%/1h  "
                f"ann={ann:+.2f}%/yr  mark={mk if mk else 'n/a'}",
                file=sys.stderr,
            )
        else:
            print(
                f"    {sym:<16s}  FAILED: {result.get('error', '?')}",
                file=sys.stderr,
            )
        time.sleep(0.2)  # conservative rate limit for public API

    # Depth fetch (optional)
    if fetch_depth:
        for sym in ["BTC-PERP", "ETH-PERP"]:
            depth_map[sym] = fetch_aevo_orderbook_depth(sym)
            time.sleep(0.2)

    # History cache: append BTC and ETH snapshots
    for hist_sym in ["BTC-PERP", "ETH-PERP"]:
        try:
            import pandas as pd
            df = fetch_aevo_history(hist_sym, days=history_days)
            if not getattr(df, "empty", True) and len(df) > 0:
                save_aevo_fr_cache(hist_sym, df)
        except Exception as exc:
            print(
                f"  [aevo_fr_fetcher] Cache error for {hist_sym}: {exc}",
                file=sys.stderr,
            )
        time.sleep(0.2)

    # Write dashboard
    write_aevo_dashboard(fr_results, markets, depth_map)

    elapsed  = time.time() - t0
    ok_count = sum(1 for r in fr_results.values() if r.get("ok"))
    print(
        f"  [aevo_fr_fetcher] Done: {ok_count}/{len(symbols)} OK in {elapsed:.1f}s",
        file=sys.stderr,
    )

    return fr_results


# ─────────────────────────────────────────────────────────────────────────────
# K208 Cross-Venue Arbitrage Helper
# ─────────────────────────────────────────────────────────────────────────────

def compute_cross_venue_opportunities(
    aevo_results:  Dict[str, dict],
    hl_fr_map:     Optional[Dict[str, float]] = None,
    bybit_fr_map:  Optional[Dict[str, float]] = None,
    okx_fr_map:    Optional[Dict[str, float]] = None,
    threshold_bps: float = 5.0,
) -> List[dict]:
    """
    Compare Aevo FR against HL/Bybit/OKX to find cross-venue carry opportunities.

    NOTE: Aevo uses 1h cycles. For comparison with 8h venues, normalize:
      Aevo_8h_equiv = Aevo_1h_FR × 8
    K208 short-highest-FR / long-lowest-FR — use normalized rates.

    Returns list of opportunity dicts sorted by spread_bps desc.
    """
    opportunities = []

    for sym, aevo_d in aevo_results.items():
        if not aevo_d.get("ok"):
            continue

        aevo_fr_1h = aevo_d["funding_rate"]
        aevo_fr_8h = aevo_fr_1h * 8   # normalize to 8h basis for comparison

        # Convert Aevo format (BTC-PERP) to base symbol (BTC)
        base_sym = sym.replace("-PERP", "")

        fr_map: Dict[str, float] = {"Aevo_8h": aevo_fr_8h}
        if hl_fr_map and base_sym in hl_fr_map:
            fr_map["HL"] = hl_fr_map[base_sym]
        if bybit_fr_map and base_sym in bybit_fr_map:
            fr_map["Bybit"] = bybit_fr_map[base_sym]
        if okx_fr_map and base_sym in okx_fr_map:
            fr_map["OKX"] = okx_fr_map[base_sym]

        if len(fr_map) < 2:
            continue

        max_venue = max(fr_map, key=fr_map.get)  # type: ignore[arg-type]
        min_venue = min(fr_map, key=fr_map.get)  # type: ignore[arg-type]
        spread_bps = (fr_map[max_venue] - fr_map[min_venue]) * 10_000

        if spread_bps >= threshold_bps:
            opportunities.append({
                "symbol":      base_sym,
                "short_venue": max_venue,
                "long_venue":  min_venue,
                "spread_bps":  round(spread_bps, 2),
                "fr_map_8h_basis": {
                    v: round(f * 10_000, 2) for v, f in fr_map.items()
                },
                "aevo_1h_fr":  aevo_fr_1h,
                "note": (
                    f"short {max_venue} ({fr_map[max_venue]*100:.4f}% per 8h basis) "
                    f"/ long {min_venue} ({fr_map[min_venue]*100:.4f}% per 8h basis)"
                ),
            })

    return sorted(opportunities, key=lambda x: x["spread_bps"], reverse=True)


# ─────────────────────────────────────────────────────────────────────────────
# CLI
# ─────────────────────────────────────────────────────────────────────────────

def _parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(
        description=(
            "K460 Aevo Funding Rate Fetcher "
            "(K454 v6.20 4th venue, 23rd daemon, 1h funding cycle)"
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Live BTC FR (default):
  python3 scripts/aevo_fr_fetcher.py

  # Specific symbol:
  python3 scripts/aevo_fr_fetcher.py --symbol ETH-PERP

  # Fetch all K208 symbols + write dashboard:
  python3 scripts/aevo_fr_fetcher.py --all

  # Fetch history + cache (accumulates from polling):
  python3 scripts/aevo_fr_fetcher.py --history --symbol BTC-PERP --days 30

  # Full daemon run (all symbols + history + dashboard):
  python3 scripts/aevo_fr_fetcher.py --daemon

  # Print dashboard JSON:
  python3 scripts/aevo_fr_fetcher.py --dashboard

K460 context: Aevo is 4th K208 venue (HL+Bybit+OKX+Aevo = v6.20 expansion).
23rd daemon: com.cryptolab.aevo-fr-monitor (StartInterval 3600, 1h cycle).
NOTE: Aevo uses 1h funding period (vs 8h HL/Bybit/OKX). Normalize for comparison.
        """,
    )
    p.add_argument("--symbol",    default="BTC-PERP",
                   help="Aevo instrument_name (default: BTC-PERP)")
    p.add_argument("--all",       action="store_true",
                   help="Fetch all K208 symbols")
    p.add_argument("--history",   action="store_true",
                   help="Fetch/accumulate historical FR data for the symbol")
    p.add_argument("--days",      type=int, default=30,
                   help="Days of history window (default: 30)")
    p.add_argument("--daemon",    action="store_true",
                   help="Full daemon run: all symbols + history + dashboard")
    p.add_argument("--dashboard", action="store_true",
                   help="Print current dashboard JSON (no fetch)")
    p.add_argument("--depth",     action="store_true",
                   help="Also fetch order book depth (slower)")
    p.add_argument("--json",      action="store_true",
                   help="Output result as JSON")
    return p.parse_args()


def main() -> int:
    args = _parse_args()

    # --dashboard: print current state
    if args.dashboard:
        if DASHBOARD_PATH.is_file():
            with open(DASHBOARD_PATH) as f:
                print(json.dumps(json.load(f), indent=2))
        else:
            print(json.dumps({
                "status": "no dashboard found — run --all or --daemon first"
            }))
        return 0

    # --daemon: full cycle
    if args.daemon:
        print("=== K460 Aevo FR Monitor — Daemon Run ===", file=sys.stderr)
        fr_results = fetch_and_cache_all(
            history_days=args.days,
            fetch_depth=args.depth,
        )
        ok_count = sum(1 for r in fr_results.values() if r.get("ok"))
        print(
            f"\n=== Daemon run complete: {ok_count}/{len(fr_results)} symbols OK ===",
            file=sys.stderr,
        )
        if args.json:
            print(json.dumps(fr_results, indent=2))
        return 0

    # --all: fetch all symbols, write dashboard
    if args.all:
        fr_results = fetch_and_cache_all(
            symbols=K208_SYMBOLS_AEVO,
            history_days=args.days,
            fetch_depth=args.depth,
        )
        if args.json:
            print(json.dumps(fr_results, indent=2))
        else:
            print(
                f"\n=== Aevo FR Snapshot "
                f"({datetime.now(JST).strftime('%Y-%m-%d %H:%M JST')}) ==="
            )
            for sym, d in fr_results.items():
                if d.get("ok"):
                    print(
                        f"  {sym:<16s}  FR={d['funding_rate']*100:+.6f}%/1h  "
                        f"ann={d.get('annualized_pct', 0):+.2f}%/yr"
                    )
                else:
                    print(f"  {sym:<16s}  FAILED: {d.get('error', '?')}")
        return 0

    # --history: accumulate historical data
    if args.history:
        print(f"=== Accumulating {args.days}d history for {args.symbol} ===", file=sys.stderr)
        try:
            df = fetch_aevo_history(args.symbol, days=args.days)
            if not getattr(df, "empty", True) and len(df) > 0:
                save_aevo_fr_cache(args.symbol, df)
                if args.json:
                    print(df.to_json(orient="records", date_format="iso"))
                else:
                    print(df.to_string())
            else:
                print("No data — cache empty and API returned no history.")
        except Exception as exc:
            print(f"Error: {exc}")
        return 0

    # Default: single symbol live fetch
    result = fetch_aevo_funding_rate(args.symbol)
    if args.json:
        print(json.dumps(result, indent=2))
    else:
        if result.get("ok"):
            fr     = result["funding_rate"]
            ann    = result.get("annualized_pct", 0.0)
            ns     = result.get("next_epoch_ns", 0)
            sec    = result.get("next_epoch_sec", 0)
            print(f"\n=== Aevo Funding Rate: {args.symbol} ===")
            print(f"  Current FR:    {fr*100:+.6f}% per 1h (Aevo 1h cycle)")
            print(f"  8h equivalent: {fr*8*100:+.6f}% per 8h (for HL/Bybit/OKX comparison)")
            print(f"  Annualized:    {ann:+.2f}% per year")
            print(f"  Next epoch:    {ns} ns (Unix {sec}s)")
            print(f"  Fetched at:    {result['fetched_at_utc']}")
            print(f"  Source:        {result['source']}")
            print(f"\n  K460 Aevo → 4th venue for K208 cross-venue FR arb")
            print(f"  Dashboard:     data/aevo_dashboard.json")
            print(f"  NOTE: Aevo 1h period — annualized = FR × 24 × 365 × 100")
        else:
            print(f"FAILED: {result.get('error', 'unknown')}", file=sys.stderr)
            return 1

    return 0


if __name__ == "__main__":
    sys.exit(main())

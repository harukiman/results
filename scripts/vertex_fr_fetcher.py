#!/usr/bin/env python3
"""
vertex_fr_fetcher.py — K465 Vertex Protocol Funding Rate Fetcher (K454 v6.20 7th venue)
=========================================================================================
Fetches Vertex Protocol perpetual funding rates via the Vertex Gateway REST API
and caches them as Parquet for downstream use by K208 and K434 smart router.

Architecture:
  - fetch_vertex_funding_rate(product_id)    → live current FR dict
  - fetch_vertex_all_products()              → all active perp products
  - fetch_vertex_history(product_id, days)   → 30d historical FR DataFrame
  - save_vertex_fr_cache(symbol, df)         → cache/vertex_fr_{symbol}.parquet
  - fetch_and_cache_all(product_ids)         → run all products in sequence
  - write_vertex_dashboard()                → data/vertex_dashboard.json

Vertex Protocol REST API:
  Gateway base URL:  https://gateway.prod.vertexprotocol.com/v1
  Archive base URL:  https://archive.prod.vertexprotocol.com/v1

  Key endpoints:
  - POST /query  {"type": "all_products"}          → all products (spot + perp)
  - POST /query  {"type": "market_snapshots", "interval": {...}}  → market data
  - POST /query  {"type": "funding_rates", "product_ids": [...]}  → FR data
  - POST /query  {"type": "candlesticks", ...}     → OHLCV
  - GET  /status                                   → gateway health

  Archive endpoints (historical):
  - POST /indexer  {"funding_rates": {"product_id": N, "limit": L}}  → historical FR
  - POST /indexer  {"market_snapshots": {...}}                         → historical OI

Auth: NOT required for public read-only query endpoints.

Vertex funding rate notes:
  - Product IDs: BTC-PERP = 2, ETH-PERP = 4 (verify via all_products)
  - Funding rate: per 8h period (long pays short when rate > 0)
  - Settlement: 8h intervals (aligns with HL/Bybit/OKX)
  - Annualized: FR × 3 × 365 × 100
  - Vertex uses USDC as margin

K208 Integration (7th venue — K454 v6.20 expansion, K465):
  - K208 short-highest-FR / long-lowest-FR now spans all 7 venues.
  - Vertex specializes in spot + perp AMM hybrid (deep on-chain liquidity).
  - K434 smart router uses this fetcher's output as Vertex venue score input.
  - Conservative tier: max_pct_of_oi=0.03, min_depth_usd=25_000 (new venue).

K465 context:
  - Wave K465: completes 7-venue K208 mesh (HL + Bybit + OKX + Aevo + dYdX + Lighter + Vertex).
  - Vertex is 7th major venue (K465 K454 v6.20 redundancy — final venue).
  - StartInterval: 28800 (8h — aligns with Vertex 8h funding cycle).
  - Daemon: com.cryptolab.vertex-fr-monitor (26th daemon, SCAFFOLD-READY).

K339 Security:
  REPO_ROOT = Path(__file__).resolve().parent.parent — no /Users/ literals.
  Vertex API keys NOT required for read-only query endpoints.

API source: https://docs.vertexprotocol.com/ (Vertex Edge / Gateway / Archive)

Usage:
  python3 scripts/vertex_fr_fetcher.py                        # BTC-PERP (product_id=2)
  python3 scripts/vertex_fr_fetcher.py --symbol ETH           # ETH-PERP
  python3 scripts/vertex_fr_fetcher.py --all                  # all K208 products
  python3 scripts/vertex_fr_fetcher.py --history --days 30
  python3 scripts/vertex_fr_fetcher.py --dashboard             # print dashboard JSON
  python3 scripts/vertex_fr_fetcher.py --daemon                # full daemon run

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
from typing import Dict, List, Optional, Tuple

# ── K339: REPO_ROOT from __file__, no /Users/ literals ───────────────────────
REPO_ROOT = Path(__file__).resolve().parent.parent
CACHE_DIR = REPO_ROOT / "cache"
DATA_DIR  = REPO_ROOT / "data"
LOGS_DIR  = REPO_ROOT / "logs"

CACHE_DIR.mkdir(exist_ok=True)
DATA_DIR.mkdir(exist_ok=True)
LOGS_DIR.mkdir(exist_ok=True)

JST = timezone(timedelta(hours=9))

# ── Vertex Protocol REST API constants ────────────────────────────────────────
VERTEX_GATEWAY_BASE   = "https://gateway.prod.vertexprotocol.com/v1"
VERTEX_ARCHIVE_BASE   = "https://archive.prod.vertexprotocol.com/v1"
VERTEX_QUERY_EP       = "/query"      # POST: all_products, funding_rates, market_snapshots
VERTEX_INDEXER_EP     = "/indexer"    # POST: historical funding_rates, market_snapshots
VERTEX_STATUS_EP      = "/status"     # GET: gateway health

# Vertex 8h funding cycle (aligns with HL/Bybit/OKX)
VERTEX_PERIODS_PER_DAY   = 3          # 8h cycle = 3 periods/day
VERTEX_FUNDING_INTERVAL_SEC = 28800   # 8h in seconds

# ── Vertex product ID mapping ─────────────────────────────────────────────────
# Vertex uses integer product_ids. Perp IDs follow pattern: spot_id+1 (even=spot, odd=perp)
# Key product IDs (verify via all_products query):
#   1 = BTC spot, 2 = BTC-PERP
#   3 = ETH spot, 4 = ETH-PERP
#   5 = ARB spot, 6 = ARB-PERP  (and so on...)
# NOTE: actual IDs may differ — always verify via fetch_vertex_all_products()
VERTEX_PRODUCT_ID_MAP: Dict[str, int] = {
    "BTC":  2,
    "ETH":  4,
    "ARB":  6,
    "BNB":  8,
    "XRP":  10,
    "SOL":  12,
    "OP":   14,
    "MATIC": 16,
    "AVAX": 18,
    "LINK": 20,
    "SUI":  22,
    "APT":  24,
    "ATOM": 26,
    "DOGE": 28,
    "TIA":  30,
}

# Reverse map: product_id -> symbol
VERTEX_ID_TO_SYMBOL: Dict[int, str] = {v: k for k, v in VERTEX_PRODUCT_ID_MAP.items()}

# ── K208 universe symbols for Vertex ─────────────────────────────────────────
K208_SYMBOLS_VERTEX: List[str] = [
    "BTC",
    "ETH",
    "SOL",
    "ARB",
    "OP",
    "AVAX",
    "LINK",
    "XRP",
    "DOGE",
    "BNB",
    "SUI",
    "APT",
    "ATOM",
    "TIA",
]

DASHBOARD_PATH = DATA_DIR / "vertex_dashboard.json"
DECISION_LOG   = DATA_DIR / "vertex_fr_decisions.jsonl"


# ─────────────────────────────────────────────────────────────────────────────
# HTTP helpers (stdlib urllib only — no requests dependency)
# ─────────────────────────────────────────────────────────────────────────────

def _http_get(url: str, timeout: int = 10) -> Optional[dict]:
    """Lightweight GET request using stdlib urllib. Returns JSON or None."""
    try:
        req = urllib.request.Request(
            url,
            headers={
                "User-Agent": "crypto-lab-vertex-fr-fetcher/1.0",
                "Accept":     "application/json",
            },
        )
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        print(f"  [vertex_fr_fetcher] HTTP {exc.code}: {url}", file=sys.stderr)
        return None
    except urllib.error.URLError as exc:
        print(f"  [vertex_fr_fetcher] URL error: {exc.reason} — {url}", file=sys.stderr)
        return None
    except Exception as exc:
        print(f"  [vertex_fr_fetcher] Error: {exc} — {url}", file=sys.stderr)
        return None


def _http_post(url: str, payload: dict, timeout: int = 12) -> Optional[dict]:
    """
    POST JSON to Vertex Gateway/Archive. Returns parsed JSON or None.
    K339: user-agent identifies this as crypto-lab tooling.
    """
    try:
        data = json.dumps(payload).encode("utf-8")
        req  = urllib.request.Request(
            url,
            data=data,
            headers={
                "Content-Type": "application/json",
                "User-Agent":   "crypto-lab-vertex-fr-fetcher/1.0",
                "Accept":       "application/json",
            },
        )
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        try:
            body = exc.read().decode("utf-8")
            print(f"  [vertex_fr_fetcher] HTTP {exc.code} POST {url}: {body[:200]}", file=sys.stderr)
        except Exception:
            print(f"  [vertex_fr_fetcher] HTTP {exc.code} POST {url}", file=sys.stderr)
        return None
    except urllib.error.URLError as exc:
        print(f"  [vertex_fr_fetcher] URL error POST: {exc.reason} — {url}", file=sys.stderr)
        return None
    except Exception as exc:
        print(f"  [vertex_fr_fetcher] Error POST: {exc} — {url}", file=sys.stderr)
        return None


def _safe_float(val) -> Optional[float]:
    """Convert str/float/int/None to float safely."""
    if val is None:
        return None
    try:
        return float(val)
    except (TypeError, ValueError):
        return None


# ─────────────────────────────────────────────────────────────────────────────
# Core fetch functions
# ─────────────────────────────────────────────────────────────────────────────

def fetch_vertex_all_products() -> Dict[str, dict]:
    """
    Fetch all Vertex products via the Gateway query endpoint.

    POST /query {"type": "all_products"}

    Returns dict: {symbol: {product_id, type, mark_price, open_interest, ...}}
    Falls back to empty dict on failure.
    """
    url = f"{VERTEX_GATEWAY_BASE}{VERTEX_QUERY_EP}"
    raw = _http_post(url, {"type": "all_products"}, timeout=15)
    if raw is None:
        return {}

    products: Dict[str, dict] = {}

    # Response structure: {"data": {"spot_products": [...], "perp_products": [...], ...}}
    data = raw.get("data", raw)
    perp_list = (
        data.get("perp_products", [])
        if isinstance(data, dict) else []
    )
    if not perp_list and isinstance(data, list):
        perp_list = [item for item in data if item.get("type") == "perp"]

    for item in perp_list:
        product_id = item.get("product_id", item.get("id"))
        # Try to get symbol from product_id reverse map or metadata
        sym = VERTEX_ID_TO_SYMBOL.get(product_id)
        if not sym:
            # Try market name fields
            name = item.get("market_name", item.get("name", item.get("ticker", "")))
            if name:
                sym = name.replace("-PERP", "").replace("-USD", "").upper()
        if not sym or not product_id:
            continue

        # Mark price may be nested in oracle_price or product.state
        state   = item.get("state", item.get("product", {}))
        mark_px = None
        oi_usd  = None
        if isinstance(state, dict):
            mark_px = _safe_float(
                state.get("mark_price", state.get("oracle_price", state.get("markPrice")))
            )
            oi_usd = _safe_float(
                state.get("open_interest", state.get("openInterest"))
            )

        products[sym] = {
            "product_id":    product_id,
            "type":          "perp",
            "mark_price":    mark_px,
            "open_interest": oi_usd,
        }

    print(
        f"  [vertex_fr_fetcher] all_products: {len(products)} perps found",
        file=sys.stderr,
    )
    return products


def fetch_vertex_funding_rates_bulk(
    product_ids: Optional[List[int]] = None,
) -> Dict[int, dict]:
    """
    Fetch funding rates for multiple Vertex products in one call.

    POST /query {"type": "funding_rates", "product_ids": [2, 4, ...]}

    Returns dict: {product_id: {funding_rate, period_h, ...}}
    """
    if product_ids is None:
        product_ids = list(VERTEX_PRODUCT_ID_MAP.values())

    url = f"{VERTEX_GATEWAY_BASE}{VERTEX_QUERY_EP}"
    raw = _http_post(
        url,
        {"type": "funding_rates", "product_ids": product_ids},
        timeout=12,
    )
    if raw is None:
        return {}

    results: Dict[int, dict] = {}
    now_utc = datetime.now(timezone.utc).isoformat()

    data = raw.get("data", raw)
    # Response may be dict of product_id -> rate, or list
    if isinstance(data, dict):
        for pid_str, rate_info in data.items():
            try:
                pid = int(pid_str)
            except (TypeError, ValueError):
                continue
            fr = _safe_float(rate_info) if not isinstance(rate_info, dict) else \
                 _safe_float(rate_info.get("funding_rate", rate_info.get("rate")))
            if fr is not None:
                annualized = fr * VERTEX_PERIODS_PER_DAY * 365 * 100
                results[pid] = {
                    "product_id":     pid,
                    "funding_rate":   fr,
                    "annualized_pct": round(annualized, 4),
                    "fetched_at_utc": now_utc,
                    "source":         "Vertex_public_api",
                    "settlement_period_h": 8,
                    "ok":             True,
                }
    elif isinstance(data, list):
        for item in data:
            pid = item.get("product_id", item.get("id"))
            fr  = _safe_float(item.get("funding_rate", item.get("rate")))
            if pid is not None and fr is not None:
                annualized = fr * VERTEX_PERIODS_PER_DAY * 365 * 100
                results[int(pid)] = {
                    "product_id":     int(pid),
                    "funding_rate":   fr,
                    "annualized_pct": round(annualized, 4),
                    "fetched_at_utc": now_utc,
                    "source":         "Vertex_public_api",
                    "settlement_period_h": 8,
                    "ok":             True,
                }

    return results


def fetch_vertex_funding_rate(symbol: str = "BTC") -> dict:
    """
    Fetch live current funding rate for a single Vertex perpetual.

    Attempts bulk funding_rates query first, then falls back to
    market_snapshots query for the specific product.

    Returns:
        {
            "symbol":               str,
            "product_id":           int,
            "funding_rate":         float,   # per 8h period
            "annualized_pct":       float,   # FR × 3 × 365 × 100
            "mark_px":              float or None,
            "open_interest":        float or None,
            "fetched_at_utc":       str,
            "source":               "Vertex_public_api",
            "settlement_period_h":  8,
            "ok":                   bool,
        }
    On failure: returns dict with ok=False and error message.
    """
    product_id = VERTEX_PRODUCT_ID_MAP.get(symbol)
    base = {
        "symbol":               symbol,
        "product_id":           product_id,
        "fetched_at_utc":       datetime.now(timezone.utc).isoformat(),
        "source":               "Vertex_public_api",
        "settlement_period_h":  8,
    }

    if product_id is None:
        return {**base, "ok": False, "error": f"Unknown symbol: {symbol} (not in VERTEX_PRODUCT_ID_MAP)"}

    # Try bulk endpoint
    bulk_rates = fetch_vertex_funding_rates_bulk([product_id])
    if product_id in bulk_rates:
        result = bulk_rates[product_id]
        result["symbol"] = symbol
        return result

    # Fallback: market_snapshots query
    url = f"{VERTEX_GATEWAY_BASE}{VERTEX_QUERY_EP}"
    raw = _http_post(
        url,
        {"type": "market_snapshots", "product_id": product_id},
        timeout=12,
    )

    if raw is None:
        return {**base, "ok": False, "error": "HTTP request failed — check Vertex Gateway connectivity"}

    try:
        data = raw.get("data", raw)
        if isinstance(data, list) and data:
            data = data[-1]  # most recent snapshot

        fr_raw  = data.get("funding_rate", data.get("fundingRate"))
        mark_px = _safe_float(data.get("mark_price", data.get("markPrice")))
        oi      = _safe_float(data.get("open_interest", data.get("openInterest")))

        if fr_raw is None:
            return {**base, "ok": False, "error": f"No funding_rate in response: {list(data.keys()) if isinstance(data, dict) else type(data)}"}

        fr         = float(fr_raw)
        annualized = fr * VERTEX_PERIODS_PER_DAY * 365 * 100

        return {
            **base,
            "funding_rate":   fr,
            "annualized_pct": round(annualized, 4),
            "mark_px":        mark_px,
            "open_interest":  oi,
            "ok":             True,
        }
    except (TypeError, ValueError, KeyError) as exc:
        return {**base, "ok": False, "error": f"Parse error: {exc}"}


def fetch_vertex_market_snapshots(
    product_ids: Optional[List[int]] = None,
) -> Dict[int, dict]:
    """
    Fetch market snapshots (mark price, OI) for multiple Vertex products.

    POST /query {"type": "market_snapshots", "product_ids": [...]}

    Returns dict: {product_id: {mark_price, open_interest, funding_rate}}
    """
    if product_ids is None:
        product_ids = list(VERTEX_PRODUCT_ID_MAP.values())

    url = f"{VERTEX_GATEWAY_BASE}{VERTEX_QUERY_EP}"
    raw = _http_post(
        url,
        {"type": "market_snapshots", "product_ids": product_ids},
        timeout=15,
    )
    if raw is None:
        return {}

    snapshots: Dict[int, dict] = {}
    data = raw.get("data", raw)

    if isinstance(data, list):
        for item in data:
            pid = item.get("product_id", item.get("id"))
            if pid is None:
                continue
            snapshots[int(pid)] = {
                "mark_price":    _safe_float(item.get("mark_price", item.get("markPrice"))),
                "open_interest": _safe_float(item.get("open_interest", item.get("openInterest"))),
                "funding_rate":  _safe_float(item.get("funding_rate", item.get("fundingRate"))),
            }
    elif isinstance(data, dict):
        for pid_str, item in data.items():
            try:
                pid = int(pid_str)
            except (TypeError, ValueError):
                continue
            if isinstance(item, dict):
                snapshots[pid] = {
                    "mark_price":    _safe_float(item.get("mark_price", item.get("markPrice"))),
                    "open_interest": _safe_float(item.get("open_interest", item.get("openInterest"))),
                    "funding_rate":  _safe_float(item.get("funding_rate", item.get("fundingRate"))),
                }

    return snapshots


def fetch_vertex_historical_funding(
    product_id: int,
    limit: int = 100,
) -> List[dict]:
    """
    Fetch historical funding rates from Vertex Archive.

    POST /indexer {"funding_rates": {"product_id": N, "limit": L}}

    Returns list of {timestamp, rate, product_id} dicts.
    Falls back to empty list on failure.
    """
    url = f"{VERTEX_ARCHIVE_BASE}{VERTEX_INDEXER_EP}"
    raw = _http_post(
        url,
        {"funding_rates": {"product_id": product_id, "limit": limit}},
        timeout=15,
    )
    if raw is None:
        return []

    data = raw.get("data", raw.get("funding_rates", []))
    if isinstance(data, list):
        return data
    if isinstance(data, dict):
        return data.get("funding_rates", data.get("rates", []))
    return []


# ─────────────────────────────────────────────────────────────────────────────
# Cache management
# ─────────────────────────────────────────────────────────────────────────────

def fetch_vertex_history(
    symbol: str = "BTC",
    days:   int = 30,
) -> "pd.DataFrame":  # type: ignore[name-defined]
    """
    Build funding rate history for a Vertex symbol from archive + cached data.

    Uses Archive /indexer endpoint for historical data, then appends current.
    Falls back to snapshot-only accumulation if archive unavailable.

    Returns pd.DataFrame with columns: fundingTime, fundingRate, symbol
    """
    try:
        import pandas as pd
    except ImportError:
        print("  [vertex_fr_fetcher] pandas not available", file=sys.stderr)
        import types
        empty_df = types.SimpleNamespace()
        empty_df.empty = True
        return empty_df  # type: ignore

    safe_sym   = symbol.replace("/", "_").replace("-", "_")
    cache_path = CACHE_DIR / f"vertex_fr_{safe_sym}.parquet"
    existing_records = []

    if cache_path.is_file():
        try:
            existing_df = pd.read_parquet(cache_path)
            existing_records = existing_df.to_dict("records")
            print(
                f"  [vertex_fr_fetcher] Loaded {len(existing_records)} cached rows for {symbol}",
                file=sys.stderr,
            )
        except Exception as exc:
            print(f"  [vertex_fr_fetcher] Cache load error: {exc}", file=sys.stderr)

    # Fetch from archive
    product_id = VERTEX_PRODUCT_ID_MAP.get(symbol)
    if product_id:
        hist = fetch_vertex_historical_funding(product_id, limit=100)
        for entry in hist:
            ts_raw = entry.get("timestamp", entry.get("ts", entry.get("time")))
            rate   = _safe_float(entry.get("rate", entry.get("funding_rate")))
            if ts_raw is not None and rate is not None:
                try:
                    ts = pd.Timestamp(int(ts_raw), unit="s", tz="UTC") if str(ts_raw).isdigit() else pd.Timestamp(ts_raw, tz="UTC")
                    existing_records.append({
                        "fundingTime": ts,
                        "fundingRate": rate,
                        "symbol":      symbol,
                    })
                except Exception:
                    pass

    # Append current snapshot
    current = fetch_vertex_funding_rate(symbol)
    if current.get("ok"):
        existing_records.append({
            "fundingTime": pd.Timestamp.now(tz="UTC"),
            "fundingRate": current["funding_rate"],
            "symbol":      symbol,
        })

    if not existing_records:
        return pd.DataFrame()

    df = pd.DataFrame(existing_records)
    # Deduplicate and filter to window
    cutoff = pd.Timestamp.now(tz="UTC") - pd.Timedelta(days=days)
    if "fundingTime" in df.columns:
        df["fundingTime"] = pd.to_datetime(df["fundingTime"], utc=True)
        df = df[df["fundingTime"] >= cutoff]
        df = df.drop_duplicates(subset=["fundingTime"]).sort_values("fundingTime").reset_index(drop=True)

    print(
        f"  [vertex_fr_fetcher] History: {symbol} — {len(df)} records ({days}d window)",
        file=sys.stderr,
    )
    return df


def save_vertex_fr_cache(symbol: str, df: "pd.DataFrame") -> Path:  # type: ignore[name-defined]
    """
    Write funding rate history DataFrame to cache/vertex_fr_{symbol}.parquet.
    K339: uses REPO_ROOT-relative path, no absolute /Users/ literal.
    """
    safe_sym = symbol.replace("/", "_").replace("-", "_")
    path = CACHE_DIR / f"vertex_fr_{safe_sym}.parquet"
    try:
        df.to_parquet(path, index=False)
        print(
            f"  [vertex_fr_fetcher] Cache written: {path.name} ({len(df)} rows)",
            file=sys.stderr,
        )
    except Exception as exc:
        print(f"  [vertex_fr_fetcher] Cache write error: {exc}", file=sys.stderr)
    return path


def load_vertex_fr_cache(symbol: str) -> Optional["pd.DataFrame"]:  # type: ignore[name-defined]
    """Load cached FR history. Returns DataFrame or None if cache missing."""
    try:
        import pandas as pd
    except ImportError:
        return None

    safe_sym = symbol.replace("/", "_").replace("-", "_")
    path = CACHE_DIR / f"vertex_fr_{safe_sym}.parquet"
    if not path.is_file():
        return None
    try:
        return pd.read_parquet(path)
    except Exception as exc:
        print(f"  [vertex_fr_fetcher] Cache load error: {exc}", file=sys.stderr)
        return None


# ─────────────────────────────────────────────────────────────────────────────
# Dashboard I/O
# ─────────────────────────────────────────────────────────────────────────────

def write_vertex_dashboard(
    fr_results:  Dict[str, dict],
    snapshots:   Optional[Dict[int, dict]] = None,
    depth_map:   Optional[Dict[str, float]] = None,
) -> None:
    """
    Write data/vertex_dashboard.json with latest FR snapshot.

    Schema:
      last_poll_utc     — ISO timestamp of this poll
      last_poll_jst     — JST-formatted string
      btc_fr            — BTC funding rate (fractional, 8h period)
      eth_fr            — ETH funding rate (fractional, 8h period)
      symbols           — list of per-symbol dicts
      daemon_label      — com.cryptolab.vertex-fr-monitor
      wave              — K465
      status            — SCAFFOLD-READY
      venue             — Vertex
    """
    now_utc = datetime.now(timezone.utc)
    now_jst = now_utc.astimezone(JST)

    snapshots = snapshots or {}
    symbol_rows = []
    for sym, d in fr_results.items():
        pid      = VERTEX_PRODUCT_ID_MAP.get(sym)
        snap     = snapshots.get(pid, {}) if pid else {}
        symbol_rows.append({
            "symbol":         sym,
            "product_id":     pid,
            "funding_rate":   d.get("funding_rate", 0.0),
            "mark_px":        snap.get("mark_price") or d.get("mark_px"),
            "annualized_pct": d.get("annualized_pct", 0.0),
            "open_interest":  snap.get("open_interest") or d.get("open_interest"),
            "ok":             d.get("ok", False),
        })

    btc_d  = fr_results.get("BTC", {})
    eth_d  = fr_results.get("ETH", {})
    btc_s  = snapshots.get(VERTEX_PRODUCT_ID_MAP.get("BTC", 2), {})
    eth_s  = snapshots.get(VERTEX_PRODUCT_ID_MAP.get("ETH", 4), {})

    payload = {
        "_comment": (
            "K465 Vertex Protocol FR Monitor dashboard "
            "(K454 v6.20 7th venue, 26th daemon, 8h funding cycle, USDC margin)"
        ),
        "_wave":           "K465",
        "last_poll_utc":   now_utc.isoformat(),
        "last_poll_jst":   now_jst.strftime("%Y-%m-%d %H:%M JST"),
        "btc_fr":          btc_d.get("funding_rate", None),
        "btc_product_id":  VERTEX_PRODUCT_ID_MAP.get("BTC", 2),
        "btc_mark_px":     btc_s.get("mark_price"),
        "btc_annualized":  btc_d.get("annualized_pct", None),
        "eth_fr":          eth_d.get("funding_rate", None),
        "eth_product_id":  VERTEX_PRODUCT_ID_MAP.get("ETH", 4),
        "eth_mark_px":     eth_s.get("mark_price"),
        "eth_annualized":  eth_d.get("annualized_pct", None),
        "symbols":         symbol_rows,
        "depth_map_usd":   depth_map or {},
        "daemon_label":    "com.cryptolab.vertex-fr-monitor",
        "daemon_number":   26,
        "start_interval":  VERTEX_FUNDING_INTERVAL_SEC,  # 28800 = 8h
        "settlement_period_h": 8,
        "status":          "SCAFFOLD-READY",
        "venue":           "Vertex",
        "api_gateway":     VERTEX_GATEWAY_BASE,
        "api_archive":     VERTEX_ARCHIVE_BASE,
        "version_target":  "v6.20",
        "k208_venues":     ["HL", "Bybit", "OKX", "Aevo", "dYdX_v4", "Lighter", "Vertex"],
        "conservative_tier": True,
        "notes": (
            "Vertex Protocol: spot+perp AMM hybrid, USDC margin. "
            "Gateway: gateway.prod.vertexprotocol.com/v1. "
            "Archive (historical): archive.prod.vertexprotocol.com/v1. "
            "8h funding cycle (aligns with HL/Bybit/OKX). "
            "Product IDs: BTC=2, ETH=4. Conservative tier: max_pct_of_oi=0.03. "
            "Historical FR available via Archive /indexer endpoint. "
            "Auth NOT required for read-only query endpoints. "
            "Trading keys needed for K208 execution (TODO post-K465 auth phase)."
        ),
    }

    tmp = DASHBOARD_PATH.with_suffix(".tmp")
    with open(tmp, "w") as f:
        json.dump(payload, f, indent=2)
    tmp.replace(DASHBOARD_PATH)
    print(
        f"  [vertex_fr_fetcher] Dashboard written: {DASHBOARD_PATH.name}",
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

    Called by com.cryptolab.vertex-fr-monitor daemon every 8h.

    Args:
        symbols:       Vertex symbol list (default: K208_SYMBOLS_VERTEX)
        history_days:  Days of history window for cache (default 30)
        fetch_depth:   Whether to fetch OI snapshots for depth (slightly slower)

    Returns:
        fr_results dict {symbol: result_dict}
    """
    if symbols is None:
        symbols = K208_SYMBOLS_VERTEX

    print(
        f"  [vertex_fr_fetcher] Starting bulk fetch: {len(symbols)} symbols",
        file=sys.stderr,
    )
    t0 = time.time()

    # Bulk funding rates
    product_ids = [VERTEX_PRODUCT_ID_MAP[s] for s in symbols if s in VERTEX_PRODUCT_ID_MAP]
    bulk_rates  = fetch_vertex_funding_rates_bulk(product_ids)
    print(
        f"  [vertex_fr_fetcher] Bulk funding rates: {len(bulk_rates)} products",
        file=sys.stderr,
    )

    # Market snapshots (mark price + OI)
    snapshots: Dict[int, dict] = {}
    if fetch_depth:
        snapshots = fetch_vertex_market_snapshots(product_ids)
        print(
            f"  [vertex_fr_fetcher] Market snapshots: {len(snapshots)} products",
            file=sys.stderr,
        )

    fr_results: Dict[str, dict] = {}

    for sym in symbols:
        pid = VERTEX_PRODUCT_ID_MAP.get(sym)
        if pid and pid in bulk_rates:
            result = bulk_rates[pid]
            result["symbol"] = sym
        else:
            result = fetch_vertex_funding_rate(sym)

        # Enrich with mark price from snapshots
        if pid and pid in snapshots:
            result["mark_px"]       = snapshots[pid].get("mark_price")
            result["open_interest"] = snapshots[pid].get("open_interest")

        fr_results[sym] = result

        if result.get("ok"):
            fr  = result["funding_rate"]
            ann = result.get("annualized_pct", fr * VERTEX_PERIODS_PER_DAY * 365 * 100)
            mk  = result.get("mark_px") or 0.0
            print(
                f"    {sym:<12s}  FR={fr*100:+.6f}%/8h  "
                f"ann={ann:+.2f}%/yr  pid={pid}  mark={mk if mk else 'n/a'}",
                file=sys.stderr,
            )
        else:
            print(
                f"    {sym:<12s}  FAILED: {result.get('error', '?')}",
                file=sys.stderr,
            )
        time.sleep(0.2)

    # History cache: append BTC and ETH snapshots
    for hist_sym in ["BTC", "ETH"]:
        try:
            import pandas as pd
            df = fetch_vertex_history(hist_sym, days=history_days)
            if not getattr(df, "empty", True) and len(df) > 0:
                save_vertex_fr_cache(hist_sym, df)
        except Exception as exc:
            print(
                f"  [vertex_fr_fetcher] Cache error for {hist_sym}: {exc}",
                file=sys.stderr,
            )
        time.sleep(0.2)

    # Write dashboard
    write_vertex_dashboard(fr_results, snapshots)

    elapsed  = time.time() - t0
    ok_count = sum(1 for r in fr_results.values() if r.get("ok"))
    print(
        f"  [vertex_fr_fetcher] Done: {ok_count}/{len(symbols)} OK in {elapsed:.1f}s",
        file=sys.stderr,
    )

    return fr_results


# ─────────────────────────────────────────────────────────────────────────────
# K208 Cross-Venue Arbitrage Helper
# ─────────────────────────────────────────────────────────────────────────────

def compute_cross_venue_opportunities(
    vertex_results: Dict[str, dict],
    hl_fr_map:      Optional[Dict[str, float]] = None,
    bybit_fr_map:   Optional[Dict[str, float]] = None,
    okx_fr_map:     Optional[Dict[str, float]] = None,
    threshold_bps:  float = 5.0,
) -> List[dict]:
    """
    Compare Vertex FR against HL/Bybit/OKX to find cross-venue carry opportunities.

    Vertex uses 8h cycles — same period as HL/Bybit/OKX, direct comparison.
    K208 short-highest-FR / long-lowest-FR across all 7 venues.

    Returns list of opportunity dicts sorted by spread_bps desc.
    """
    opportunities = []

    for sym, vtx_d in vertex_results.items():
        if not vtx_d.get("ok"):
            continue

        vtx_fr_8h = vtx_d["funding_rate"]  # already 8h period

        fr_map: Dict[str, float] = {"Vertex": vtx_fr_8h}
        if hl_fr_map and sym in hl_fr_map:
            fr_map["HL"] = hl_fr_map[sym]
        if bybit_fr_map and sym in bybit_fr_map:
            fr_map["Bybit"] = bybit_fr_map[sym]
        if okx_fr_map and sym in okx_fr_map:
            fr_map["OKX"] = okx_fr_map[sym]

        if len(fr_map) < 2:
            continue

        max_venue  = max(fr_map, key=fr_map.get)  # type: ignore[arg-type]
        min_venue  = min(fr_map, key=fr_map.get)  # type: ignore[arg-type]
        spread_bps = (fr_map[max_venue] - fr_map[min_venue]) * 10_000

        if spread_bps >= threshold_bps:
            opportunities.append({
                "symbol":      sym,
                "short_venue": max_venue,
                "long_venue":  min_venue,
                "spread_bps":  round(spread_bps, 2),
                "fr_map_8h_basis": {
                    v: round(f * 10_000, 2) for v, f in fr_map.items()
                },
                "vertex_fr_8h":    vtx_fr_8h,
                "vertex_product_id": VERTEX_PRODUCT_ID_MAP.get(sym),
                "note": (
                    f"short {max_venue} ({fr_map[max_venue]*100:.4f}% per 8h) "
                    f"/ long {min_venue} ({fr_map[min_venue]*100:.4f}% per 8h)"
                ),
            })

    return sorted(opportunities, key=lambda x: x["spread_bps"], reverse=True)


# ─────────────────────────────────────────────────────────────────────────────
# CLI
# ─────────────────────────────────────────────────────────────────────────────

def _parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(
        description=(
            "K465 Vertex Protocol Funding Rate Fetcher "
            "(K454 v6.20 7th venue, 26th daemon, 8h funding cycle, USDC margin)"
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Live BTC FR (default, product_id=2):
  python3 scripts/vertex_fr_fetcher.py

  # Specific symbol:
  python3 scripts/vertex_fr_fetcher.py --symbol ETH

  # Fetch all K208 symbols + write dashboard:
  python3 scripts/vertex_fr_fetcher.py --all

  # Fetch history + cache (from Archive + polling accumulation):
  python3 scripts/vertex_fr_fetcher.py --history --symbol BTC --days 30

  # Full daemon run (all symbols + history + dashboard):
  python3 scripts/vertex_fr_fetcher.py --daemon

  # Print dashboard JSON:
  python3 scripts/vertex_fr_fetcher.py --dashboard

  # List all Vertex perp products:
  python3 scripts/vertex_fr_fetcher.py --products

K465 context: Vertex is 7th K208 venue (7-venue mesh COMPLETE at K465).
26th daemon: com.cryptolab.vertex-fr-monitor (StartInterval 28800, 8h cycle).
Gateway: gateway.prod.vertexprotocol.com/v1 (POST /query).
Archive: archive.prod.vertexprotocol.com/v1 (POST /indexer for historical FR).
USDC margin, spot+perp AMM hybrid.
        """,
    )
    p.add_argument("--symbol",    default="BTC",
                   help="Vertex symbol (default: BTC)")
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
                   help="Also fetch market snapshots (OI + mark price)")
    p.add_argument("--json",      action="store_true",
                   help="Output result as JSON")
    p.add_argument("--products",  action="store_true",
                   help="List all Vertex perp products via all_products query")
    p.add_argument("--status",    action="store_true",
                   help="Check Vertex Gateway status endpoint")
    return p.parse_args()


def main() -> int:
    args = _parse_args()

    # --status: check gateway health
    if args.status:
        url = f"{VERTEX_GATEWAY_BASE}{VERTEX_STATUS_EP}"
        raw = _http_get(url, timeout=8)
        if raw:
            print(json.dumps(raw, indent=2))
            return 0
        else:
            print(f"FAILED: Could not reach {url}", file=sys.stderr)
            return 1

    # --products: list all Vertex perp products
    if args.products:
        products = fetch_vertex_all_products()
        if args.json:
            print(json.dumps(products, indent=2))
        else:
            print(f"\n=== Vertex Perp Products ({len(products)}) ===")
            for sym, info in sorted(products.items()):
                print(f"  {sym:<12s}  product_id={info['product_id']}  mark={info.get('mark_price', 'n/a')}")
        return 0

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
        print("=== K465 Vertex FR Monitor — Daemon Run ===", file=sys.stderr)
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
            symbols=K208_SYMBOLS_VERTEX,
            history_days=args.days,
            fetch_depth=args.depth,
        )
        if args.json:
            print(json.dumps(fr_results, indent=2))
        else:
            print(
                f"\n=== Vertex FR Snapshot "
                f"({datetime.now(JST).strftime('%Y-%m-%d %H:%M JST')}) ==="
            )
            for sym, d in fr_results.items():
                pid = VERTEX_PRODUCT_ID_MAP.get(sym, "?")
                if d.get("ok"):
                    print(
                        f"  {sym:<12s}  pid={pid}  FR={d['funding_rate']*100:+.6f}%/8h  "
                        f"ann={d.get('annualized_pct', 0):+.2f}%/yr"
                    )
                else:
                    print(f"  {sym:<12s}  FAILED: {d.get('error', '?')}")
        return 0

    # --history: accumulate historical data
    if args.history:
        print(f"=== Accumulating {args.days}d history for {args.symbol} ===", file=sys.stderr)
        try:
            df = fetch_vertex_history(args.symbol, days=args.days)
            if not getattr(df, "empty", True) and len(df) > 0:
                save_vertex_fr_cache(args.symbol, df)
                if args.json:
                    print(df.to_json(orient="records", date_format="iso"))
                else:
                    print(df.to_string())
            else:
                print("No data — cache empty and archive returned no history.")
        except Exception as exc:
            print(f"Error: {exc}")
        return 0

    # Default: single symbol live fetch
    result = fetch_vertex_funding_rate(args.symbol)
    if args.json:
        print(json.dumps(result, indent=2))
    else:
        if result.get("ok"):
            fr   = result["funding_rate"]
            ann  = result.get("annualized_pct", 0.0)
            pid  = result.get("product_id")
            mk   = result.get("mark_px")
            oi   = result.get("open_interest")
            print(f"\n=== Vertex Funding Rate: {args.symbol} (product_id={pid}) ===")
            print(f"  Current FR:     {fr*100:+.6f}% per 8h")
            print(f"  Annualized:     {ann:+.2f}% per year")
            print(f"  Mark price:     {mk if mk else 'n/a'}")
            print(f"  Open interest:  {oi if oi else 'n/a'}")
            print(f"  Fetched at:     {result['fetched_at_utc']}")
            print(f"  Source:         {result['source']}")
            print(f"\n  K465 Vertex → 7th venue — K208 7-venue mesh COMPLETE (v6.20)")
            print(f"  Dashboard:      data/vertex_dashboard.json")
            print(f"  Gateway:        {VERTEX_GATEWAY_BASE}")
            print(f"  Archive:        {VERTEX_ARCHIVE_BASE}")
        else:
            print(f"FAILED: {result.get('error', 'unknown')}", file=sys.stderr)
            print(f"  NOTE: Vertex Gateway ({VERTEX_GATEWAY_BASE}) may require connectivity check.", file=sys.stderr)
            print(f"  Product IDs: BTC=2, ETH=4. POST /query {{\"type\": \"funding_rates\", \"product_ids\": [2]}}", file=sys.stderr)
            return 1

    return 0


if __name__ == "__main__":
    sys.exit(main())

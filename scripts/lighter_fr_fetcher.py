#!/usr/bin/env python3
"""
lighter_fr_fetcher.py — K465 Lighter Funding Rate Fetcher (K454 v6.20 6th venue)
==================================================================================
Fetches Lighter perpetual funding rates via the Lighter REST API and caches
them as Parquet for downstream use by K208 strategy adapter and K434 smart router.

Architecture:
  - fetch_lighter_funding_rate(symbol)       → live current FR dict
  - fetch_lighter_markets()                  → all perp markets + mark price, OI
  - fetch_lighter_history(symbol, days=30)   → 30d historical FR DataFrame
  - save_lighter_fr_cache(symbol, df)        → cache/lighter_fr_{symbol}.parquet
  - fetch_and_cache_all(symbols)             → run all symbols in sequence
  - write_lighter_dashboard()               → data/lighter_dashboard.json

Lighter REST API base: https://mainnet.zklighter.elliot.ai
  - GET /api/v1/funding-rates              (current funding rates, all markets)
  - GET /api/v1/markets                    (all active markets + mark price)
  - GET /api/v1/orderBooks                 (order book metadata with fee structure)
  - GET /api/v1/orderBookDetails           (per-market OI + details)
  - GET /api/v1/exchangeMetrics            (exchange-wide metrics by market)
  - GET /api/v1/exchangeStats              (overall exchange statistics)
  - GET /api/v1/status                     (system health)

Auth: NOT required for public read-only endpoints.
Lighter is a zkEVM-based perpetuals exchange (ZK proofs for settlement).

Note on Lighter FR format:
  - funding_rate: per 8h period (typical) — verify via /api/v1/markets response
  - Settlement: typically 8h (may vary per market)
  - Annualized: FR × (365 × 24 / period_h) × 100
  - Base URL: mainnet.zklighter.elliot.ai (AWS Tokyo ap-northeast-1a recommended)

K208 Integration (6th venue — K454 v6.20 expansion, K465):
  - K208 short-highest-FR / long-lowest-FR now spans HL + Bybit + OKX + Aevo + dYdX + Lighter.
  - Lighter specializes in zkEVM perps (lower latency via ZK proof settlement).
  - K434 smart router uses this fetcher's output as Lighter venue score input.
  - Conservative tier: max_pct_of_oi=0.03, min_depth_usd=25_000 (new venue).

K465 context:
  - Wave K465: 7-venue K208 mesh (HL + Bybit + OKX + Aevo + dYdX + Lighter + Vertex).
  - Lighter is 6th major venue (K465 K454 v6.20 redundancy).
  - StartInterval: 28800 (8h — conservative; verify actual FR cycle with live API).
  - Daemon: com.cryptolab.lighter-fr-monitor (25th daemon, SCAFFOLD-READY).

K339 Security:
  REPO_ROOT = Path(__file__).resolve().parent.parent — no /Users/ literals.
  Lighter API keys NOT required for read-only fetch endpoints.

API source: https://apidocs.lighter.xyz/docs/get-started
  Lighter colocation recommendation: AWS Tokyo ap-northeast-1a (apne1-az4)

Usage:
  python3 scripts/lighter_fr_fetcher.py                     # BTC default
  python3 scripts/lighter_fr_fetcher.py --symbol ETH
  python3 scripts/lighter_fr_fetcher.py --all               # all K208 symbols
  python3 scripts/lighter_fr_fetcher.py --history --days 30
  python3 scripts/lighter_fr_fetcher.py --dashboard          # print dashboard JSON
  python3 scripts/lighter_fr_fetcher.py --daemon             # full daemon run

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

# ── Lighter REST API constants ────────────────────────────────────────────────
# Base: https://mainnet.zklighter.elliot.ai (zkEVM, AWS Tokyo recommended)
LIGHTER_BASE_URL          = "https://mainnet.zklighter.elliot.ai"
LIGHTER_FUNDING_EP        = "/api/v1/funding-rates"    # current FR for all markets
LIGHTER_MARKETS_EP        = "/api/v1/markets"           # all active markets + mark price
LIGHTER_ORDER_BOOKS_EP    = "/api/v1/orderBooks"        # order book metadata + fee structure
LIGHTER_OB_DETAILS_EP     = "/api/v1/orderBookDetails"  # per-market OI + details
LIGHTER_EXCHANGE_METRICS_EP = "/api/v1/exchangeMetrics" # exchange-wide metrics by market
LIGHTER_EXCHANGE_STATS_EP = "/api/v1/exchangeStats"     # overall exchange stats
LIGHTER_STATUS_EP         = "/api/v1/status"            # system health check

# Lighter funding cycle (typically 8h — conservative default)
# NOTE: verify actual settlement period from /api/v1/markets response per market
LIGHTER_PERIODS_PER_DAY   = 3         # 8h cycle = 3 periods/day
LIGHTER_FUNDING_INTERVAL_SEC = 28800  # 8h in seconds (conservative default)

# ── K208 universe symbols (Lighter perp format) ───────────────────────────────
# Lighter is zkEVM-based; focus on major liquid perps available on-chain
# Symbol format: typically "BTC", "ETH", etc. (verify via /api/v1/markets)
K208_SYMBOLS_LIGHTER: List[str] = [
    "BTC",
    "ETH",
    "SOL",
    "ARB",
    "OP",
    "SUI",
    "AVAX",
    "LINK",
    "XRP",
    "DOGE",
    "BNB",
    "ATOM",
    "APT",
    "TIA",
]

DASHBOARD_PATH = DATA_DIR / "lighter_dashboard.json"
DECISION_LOG   = DATA_DIR / "lighter_fr_decisions.jsonl"


# ─────────────────────────────────────────────────────────────────────────────
# HTTP helpers (stdlib urllib only — no requests dependency)
# ─────────────────────────────────────────────────────────────────────────────

def _http_get(url: str, timeout: int = 10) -> Optional[dict]:
    """
    Lightweight GET request using stdlib urllib.
    Returns parsed JSON dict/list, or None on any error.
    K339: user-agent identifies this as crypto-lab tooling.
    """
    try:
        req = urllib.request.Request(
            url,
            headers={
                "User-Agent": "crypto-lab-lighter-fr-fetcher/1.0",
                "Accept":     "application/json",
            },
        )
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            body = resp.read().decode("utf-8")
            return json.loads(body)
    except urllib.error.HTTPError as exc:
        print(f"  [lighter_fr_fetcher] HTTP {exc.code}: {url}", file=sys.stderr)
        return None
    except urllib.error.URLError as exc:
        print(f"  [lighter_fr_fetcher] URL error: {exc.reason} — {url}", file=sys.stderr)
        return None
    except Exception as exc:
        print(f"  [lighter_fr_fetcher] Error: {exc} — {url}", file=sys.stderr)
        return None


def _safe_float(val) -> Optional[float]:
    """Convert str/float/None to float safely."""
    if val is None:
        return None
    try:
        return float(val)
    except (TypeError, ValueError):
        return None


# ─────────────────────────────────────────────────────────────────────────────
# Core fetch functions
# ─────────────────────────────────────────────────────────────────────────────

def fetch_lighter_all_funding_rates() -> Dict[str, dict]:
    """
    Fetch live current funding rates for all Lighter perpetual markets.

    Lighter endpoint: GET /api/v1/funding-rates
    Returns dict: {symbol: {funding_rate, settlement_time, ...}}

    Falls back to empty dict on failure.
    """
    url = f"{LIGHTER_BASE_URL}{LIGHTER_FUNDING_EP}"
    raw = _http_get(url, timeout=12)
    if raw is None:
        return {}

    results: Dict[str, dict] = {}
    now_utc = datetime.now(timezone.utc).isoformat()

    # Response may be list or dict — handle both
    data = raw if isinstance(raw, list) else raw.get("funding_rates", raw.get("data", []))
    if isinstance(data, dict):
        # Might be {symbol: rate} directly
        for sym, rate_info in data.items():
            fr = _safe_float(rate_info) if not isinstance(rate_info, dict) else _safe_float(rate_info.get("rate", rate_info.get("funding_rate")))
            if fr is not None:
                annualized = fr * LIGHTER_PERIODS_PER_DAY * 365 * 100
                results[sym] = {
                    "symbol":           sym,
                    "funding_rate":     fr,
                    "annualized_pct":   round(annualized, 4),
                    "fetched_at_utc":   now_utc,
                    "source":           "Lighter_public_api",
                    "settlement_period_h": 8,
                    "ok":               True,
                }
    elif isinstance(data, list):
        for item in data:
            sym = item.get("symbol", item.get("market", item.get("ticker", "")))
            fr  = _safe_float(item.get("funding_rate", item.get("rate", item.get("fundingRate"))))
            if sym and fr is not None:
                annualized = fr * LIGHTER_PERIODS_PER_DAY * 365 * 100
                results[sym] = {
                    "symbol":           sym,
                    "funding_rate":     fr,
                    "annualized_pct":   round(annualized, 4),
                    "next_epoch_sec":   item.get("next_epoch", item.get("settlement_time", 0)),
                    "fetched_at_utc":   now_utc,
                    "source":           "Lighter_public_api",
                    "settlement_period_h": 8,
                    "ok":               True,
                }

    return results


def fetch_lighter_funding_rate(symbol: str = "BTC") -> dict:
    """
    Fetch live current funding rate for a single Lighter perpetual.

    Attempts bulk /funding-rates endpoint first, then falls back to
    per-market fetch via /exchangeMetrics?market={symbol}.

    Returns:
        {
            "symbol":               str,
            "funding_rate":         float,   # e.g. 0.0001 per 8h
            "annualized_pct":       float,   # FR × 3 × 365 × 100
            "mark_px":              float or None,
            "fetched_at_utc":       str,
            "source":               "Lighter_public_api",
            "settlement_period_h":  8,
            "ok":                   bool,
        }
    On failure: returns dict with ok=False and error message.
    """
    base = {
        "symbol":               symbol,
        "fetched_at_utc":       datetime.now(timezone.utc).isoformat(),
        "source":               "Lighter_public_api",
        "settlement_period_h":  8,
    }

    # Try bulk endpoint first
    all_rates = fetch_lighter_all_funding_rates()
    if symbol in all_rates:
        return all_rates[symbol]

    # Try exchangeMetrics with market filter
    url = f"{LIGHTER_BASE_URL}{LIGHTER_EXCHANGE_METRICS_EP}?market={symbol}"
    raw = _http_get(url, timeout=10)

    if raw is None:
        return {**base, "ok": False, "error": "HTTP request failed — check Lighter API availability"}

    try:
        # Response fields may include fundingRate, openInterest, markPrice
        data = raw if not isinstance(raw, list) else (raw[0] if raw else {})
        if isinstance(data, list):
            # Find matching market
            for item in raw:
                if item.get("symbol", item.get("market", "")) == symbol:
                    data = item
                    break
            else:
                data = {}

        fr_raw = data.get("fundingRate", data.get("funding_rate", data.get("rate")))
        mark   = data.get("markPrice", data.get("mark_price"))

        if fr_raw is None:
            return {**base, "ok": False, "error": f"No funding rate field in response: {list(data.keys()) if data else '[]'}"}

        fr         = float(fr_raw)
        annualized = fr * LIGHTER_PERIODS_PER_DAY * 365 * 100

        return {
            **base,
            "funding_rate":    fr,
            "annualized_pct":  round(annualized, 4),
            "mark_px":         _safe_float(mark),
            "ok":              True,
        }
    except (TypeError, ValueError, KeyError) as exc:
        return {**base, "ok": False, "error": f"Parse error: {exc}"}


def fetch_lighter_markets() -> Dict[str, dict]:
    """
    Fetch all active Lighter perpetual markets (mark price, OI, etc.).

    GET /api/v1/markets
    Returns: {symbol: {mark_price, open_interest, max_leverage, ...}}
    Falls back to empty dict on failure.
    """
    url = f"{LIGHTER_BASE_URL}{LIGHTER_MARKETS_EP}"
    raw = _http_get(url, timeout=15)
    if raw is None:
        return {}

    markets: Dict[str, dict] = {}
    data = raw if isinstance(raw, list) else raw.get("markets", raw.get("data", []))
    if isinstance(data, list):
        for item in data:
            sym = item.get("symbol", item.get("ticker", item.get("name", "")))
            if not sym:
                continue
            markets[sym] = {
                "mark_price":    _safe_float(item.get("mark_price", item.get("markPrice"))),
                "index_price":   _safe_float(item.get("index_price", item.get("indexPrice"))),
                "open_interest": _safe_float(item.get("open_interest", item.get("openInterest"))),
                "max_leverage":  _safe_float(item.get("max_leverage", item.get("maxLeverage"))),
                "is_active":     item.get("is_active", item.get("status", "active")),
            }
    elif isinstance(data, dict):
        for sym, item in data.items():
            markets[sym] = {
                "mark_price":    _safe_float(item.get("mark_price", item.get("markPrice"))) if isinstance(item, dict) else None,
                "open_interest": _safe_float(item.get("open_interest", item.get("openInterest"))) if isinstance(item, dict) else None,
                "is_active":     True,
            }
    return markets


def fetch_lighter_ob_depth(symbol: str = "BTC") -> float:
    """
    Estimate top-of-book depth (USD) from Lighter order book metadata.
    GET /api/v1/orderBooks?market={symbol}

    Returns depth_usd estimate. Falls back to 250_000.0 (conservative for new venue).
    """
    url = f"{LIGHTER_BASE_URL}{LIGHTER_ORDER_BOOKS_EP}?market={symbol}"
    raw = _http_get(url, timeout=8)
    if raw is None:
        return 250_000.0

    try:
        data = raw if not isinstance(raw, list) else (raw[0] if raw else {})
        # Try to extract bid/ask depth from order book metadata
        bids = data.get("bids", data.get("bid_depth", []))
        asks = data.get("asks", data.get("ask_depth", []))
        if bids and asks:
            bid_depth = sum(float(b[0]) * float(b[1]) for b in bids[:5] if len(b) >= 2)
            ask_depth = sum(float(a[0]) * float(a[1]) for a in asks[:5] if len(a) >= 2)
            return bid_depth + ask_depth
        # Fallback: use size fields if available
        total_depth = _safe_float(data.get("total_depth_usd", data.get("liquidity_usd")))
        if total_depth:
            return total_depth
    except (TypeError, ValueError, IndexError):
        pass
    return 250_000.0


# ─────────────────────────────────────────────────────────────────────────────
# Cache management
# ─────────────────────────────────────────────────────────────────────────────

def fetch_lighter_history(
    symbol: str = "BTC",
    days:   int = 30,
) -> "pd.DataFrame":  # type: ignore[name-defined]
    """
    Synthesize funding rate history from repeated snapshots or return empty.

    NOTE: Lighter public API may not expose a historical funding endpoint.
    This function fetches the current rate and, if a cached Parquet exists,
    appends to it. Full backfill requires authenticated access or accumulation.

    Returns:
        pd.DataFrame with columns: fundingTime, fundingRate, symbol
    Returns empty DataFrame if no data available.
    """
    try:
        import pandas as pd
    except ImportError:
        print("  [lighter_fr_fetcher] pandas not available", file=sys.stderr)
        import types
        empty_df = types.SimpleNamespace()
        empty_df.empty = True
        return empty_df  # type: ignore

    safe_sym = symbol.replace("/", "_").replace("-", "_")
    cache_path = CACHE_DIR / f"lighter_fr_{safe_sym}.parquet"
    existing_records = []

    if cache_path.is_file():
        try:
            existing_df = pd.read_parquet(cache_path)
            existing_records = existing_df.to_dict("records")
            print(
                f"  [lighter_fr_fetcher] Loaded {len(existing_records)} cached rows for {symbol}",
                file=sys.stderr,
            )
        except Exception as exc:
            print(f"  [lighter_fr_fetcher] Cache load error: {exc}", file=sys.stderr)

    current = fetch_lighter_funding_rate(symbol)
    if current.get("ok"):
        existing_records.append({
            "fundingTime": pd.Timestamp.now(tz="UTC"),
            "fundingRate": current["funding_rate"],
            "symbol":      symbol,
        })

    if not existing_records:
        return pd.DataFrame()

    df = pd.DataFrame(existing_records)
    cutoff = pd.Timestamp.now(tz="UTC") - pd.Timedelta(days=days)
    if "fundingTime" in df.columns:
        df["fundingTime"] = pd.to_datetime(df["fundingTime"], utc=True)
        df = df[df["fundingTime"] >= cutoff]

    df = df.sort_values("fundingTime").reset_index(drop=True)
    print(
        f"  [lighter_fr_fetcher] History: {symbol} — {len(df)} records ({days}d window)",
        file=sys.stderr,
    )
    return df


def save_lighter_fr_cache(symbol: str, df: "pd.DataFrame") -> Path:  # type: ignore[name-defined]
    """
    Write funding rate history DataFrame to cache/lighter_fr_{symbol}.parquet.
    K339: uses REPO_ROOT-relative path, no absolute /Users/ literal.
    """
    safe_sym = symbol.replace("/", "_").replace("-", "_")
    path = CACHE_DIR / f"lighter_fr_{safe_sym}.parquet"
    try:
        df.to_parquet(path, index=False)
        print(
            f"  [lighter_fr_fetcher] Cache written: {path.name} ({len(df)} rows)",
            file=sys.stderr,
        )
    except Exception as exc:
        print(f"  [lighter_fr_fetcher] Cache write error: {exc}", file=sys.stderr)
    return path


def load_lighter_fr_cache(symbol: str) -> Optional["pd.DataFrame"]:  # type: ignore[name-defined]
    """Load cached FR history. Returns DataFrame or None if cache missing."""
    try:
        import pandas as pd
    except ImportError:
        return None

    safe_sym = symbol.replace("/", "_").replace("-", "_")
    path = CACHE_DIR / f"lighter_fr_{safe_sym}.parquet"
    if not path.is_file():
        return None
    try:
        return pd.read_parquet(path)
    except Exception as exc:
        print(f"  [lighter_fr_fetcher] Cache load error: {exc}", file=sys.stderr)
        return None


# ─────────────────────────────────────────────────────────────────────────────
# Dashboard I/O
# ─────────────────────────────────────────────────────────────────────────────

def write_lighter_dashboard(
    fr_results: Dict[str, dict],
    markets:    Optional[Dict[str, dict]] = None,
    depth_map:  Optional[Dict[str, float]] = None,
) -> None:
    """
    Write data/lighter_dashboard.json with latest FR snapshot.

    Schema:
      last_poll_utc     — ISO timestamp of this poll
      last_poll_jst     — JST-formatted string
      btc_fr            — BTC funding rate (fractional, 8h period)
      eth_fr            — ETH funding rate (fractional, 8h period)
      symbols           — list of per-symbol dicts
      daemon_label      — com.cryptolab.lighter-fr-monitor
      wave              — K465
      status            — SCAFFOLD-READY
      venue             — Lighter
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
            "open_interest":  mkt.get("open_interest"),
            "ok":             d.get("ok", False),
        })

    btc_d = fr_results.get("BTC", {})
    eth_d = fr_results.get("ETH", {})
    btc_m = markets.get("BTC", {})
    eth_m = markets.get("ETH", {})

    payload = {
        "_comment": (
            "K465 Lighter FR Monitor dashboard "
            "(K454 v6.20 6th venue, 25th daemon, 8h funding cycle, zkEVM)"
        ),
        "_wave":           "K465",
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
        "daemon_label":    "com.cryptolab.lighter-fr-monitor",
        "daemon_number":   25,
        "start_interval":  LIGHTER_FUNDING_INTERVAL_SEC,  # 28800 = 8h
        "settlement_period_h": 8,
        "status":          "SCAFFOLD-READY",
        "venue":           "Lighter",
        "api_base":        LIGHTER_BASE_URL,
        "version_target":  "v6.20",
        "k208_venues":     ["HL", "Bybit", "OKX", "Aevo", "dYdX_v4", "Lighter"],
        "conservative_tier": True,
        "notes": (
            "Lighter uses zkEVM for settlement (ZK proofs). "
            "Base URL: mainnet.zklighter.elliot.ai. "
            "8h funding cycle (same as HL/Bybit/OKX). "
            "Conservative tier: max_pct_of_oi=0.03, min_depth_usd=25_000. "
            "No historical endpoint on public REST; cache accumulates via polling. "
            "Auth NOT required for read-only endpoints. "
            "Trading keys needed for K208 execution (TODO post-K465 auth phase)."
        ),
    }

    tmp = DASHBOARD_PATH.with_suffix(".tmp")
    with open(tmp, "w") as f:
        json.dump(payload, f, indent=2)
    tmp.replace(DASHBOARD_PATH)
    print(
        f"  [lighter_fr_fetcher] Dashboard written: {DASHBOARD_PATH.name}",
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

    Called by com.cryptolab.lighter-fr-monitor daemon every 8h.

    Args:
        symbols:       Lighter symbol list (default: K208_SYMBOLS_LIGHTER)
        history_days:  Days of history window for cache (default 30)
        fetch_depth:   Whether to fetch order book depth (slower)

    Returns:
        fr_results dict {symbol: result_dict}
    """
    if symbols is None:
        symbols = K208_SYMBOLS_LIGHTER

    print(
        f"  [lighter_fr_fetcher] Starting bulk fetch: {len(symbols)} symbols",
        file=sys.stderr,
    )
    t0 = time.time()

    # Fetch markets once (mark prices, OI)
    markets = fetch_lighter_markets()
    print(
        f"  [lighter_fr_fetcher] Markets fetched: {len(markets)} markets",
        file=sys.stderr,
    )

    # Try bulk funding rates first (more efficient)
    all_rates = fetch_lighter_all_funding_rates()
    print(
        f"  [lighter_fr_fetcher] Bulk funding rates: {len(all_rates)} markets",
        file=sys.stderr,
    )

    fr_results: Dict[str, dict] = {}
    depth_map:  Dict[str, float] = {}

    for sym in symbols:
        # Use bulk result if available, else fetch individually
        if sym in all_rates:
            result = all_rates[sym]
        else:
            result = fetch_lighter_funding_rate(sym)

        # Enrich with mark price from markets
        if sym in markets:
            result["mark_px"] = markets[sym].get("mark_price")
        fr_results[sym] = result

        if result.get("ok"):
            fr  = result["funding_rate"]
            ann = result.get("annualized_pct", fr * LIGHTER_PERIODS_PER_DAY * 365 * 100)
            mk  = result.get("mark_px") or 0.0
            print(
                f"    {sym:<12s}  FR={fr*100:+.6f}%/8h  "
                f"ann={ann:+.2f}%/yr  mark={mk if mk else 'n/a'}",
                file=sys.stderr,
            )
        else:
            print(
                f"    {sym:<12s}  FAILED: {result.get('error', '?')}",
                file=sys.stderr,
            )
        time.sleep(0.3)  # conservative rate limit

    # Depth fetch (optional — BTC, ETH only for speed)
    if fetch_depth:
        for depth_sym in ["BTC", "ETH"]:
            depth_map[depth_sym] = fetch_lighter_ob_depth(depth_sym)
            time.sleep(0.3)

    # History cache: append BTC and ETH snapshots
    for hist_sym in ["BTC", "ETH"]:
        try:
            import pandas as pd
            df = fetch_lighter_history(hist_sym, days=history_days)
            if not getattr(df, "empty", True) and len(df) > 0:
                save_lighter_fr_cache(hist_sym, df)
        except Exception as exc:
            print(
                f"  [lighter_fr_fetcher] Cache error for {hist_sym}: {exc}",
                file=sys.stderr,
            )
        time.sleep(0.2)

    # Write dashboard
    write_lighter_dashboard(fr_results, markets, depth_map)

    elapsed  = time.time() - t0
    ok_count = sum(1 for r in fr_results.values() if r.get("ok"))
    print(
        f"  [lighter_fr_fetcher] Done: {ok_count}/{len(symbols)} OK in {elapsed:.1f}s",
        file=sys.stderr,
    )

    return fr_results


# ─────────────────────────────────────────────────────────────────────────────
# K208 Cross-Venue Arbitrage Helper
# ─────────────────────────────────────────────────────────────────────────────

def compute_cross_venue_opportunities(
    lighter_results: Dict[str, dict],
    hl_fr_map:       Optional[Dict[str, float]] = None,
    bybit_fr_map:    Optional[Dict[str, float]] = None,
    okx_fr_map:      Optional[Dict[str, float]] = None,
    threshold_bps:   float = 5.0,
) -> List[dict]:
    """
    Compare Lighter FR against HL/Bybit/OKX to find cross-venue carry opportunities.

    Lighter uses 8h cycles — same period as HL/Bybit/OKX, direct comparison.
    K208 short-highest-FR / long-lowest-FR — use normalized rates.

    Returns list of opportunity dicts sorted by spread_bps desc.
    """
    opportunities = []

    for sym, lighter_d in lighter_results.items():
        if not lighter_d.get("ok"):
            continue

        lighter_fr_8h = lighter_d["funding_rate"]  # already 8h period

        fr_map: Dict[str, float] = {"Lighter": lighter_fr_8h}
        if hl_fr_map and sym in hl_fr_map:
            fr_map["HL"] = hl_fr_map[sym]
        if bybit_fr_map and sym in bybit_fr_map:
            fr_map["Bybit"] = bybit_fr_map[sym]
        if okx_fr_map and sym in okx_fr_map:
            fr_map["OKX"] = okx_fr_map[sym]

        if len(fr_map) < 2:
            continue

        max_venue = max(fr_map, key=fr_map.get)  # type: ignore[arg-type]
        min_venue = min(fr_map, key=fr_map.get)  # type: ignore[arg-type]
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
                "lighter_fr_8h": lighter_fr_8h,
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
            "K465 Lighter Funding Rate Fetcher "
            "(K454 v6.20 6th venue, 25th daemon, zkEVM, 8h funding cycle)"
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Live BTC FR (default):
  python3 scripts/lighter_fr_fetcher.py

  # Specific symbol:
  python3 scripts/lighter_fr_fetcher.py --symbol ETH

  # Fetch all K208 symbols + write dashboard:
  python3 scripts/lighter_fr_fetcher.py --all

  # Fetch history + cache (accumulates from polling):
  python3 scripts/lighter_fr_fetcher.py --history --symbol BTC --days 30

  # Full daemon run (all symbols + history + dashboard):
  python3 scripts/lighter_fr_fetcher.py --daemon

  # Print dashboard JSON:
  python3 scripts/lighter_fr_fetcher.py --dashboard

K465 context: Lighter is 6th K208 venue (HL+Bybit+OKX+Aevo+dYdX+Lighter = v6.20 7-venue mesh).
25th daemon: com.cryptolab.lighter-fr-monitor (StartInterval 28800, 8h cycle).
zkEVM: ZK proof settlement, base URL: mainnet.zklighter.elliot.ai.
Conservative tier: max_pct_of_oi=0.03, min_depth_usd=25_000 (new venue).
        """,
    )
    p.add_argument("--symbol",    default="BTC",
                   help="Lighter symbol (default: BTC)")
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
    p.add_argument("--status",    action="store_true",
                   help="Check Lighter API status endpoint")
    return p.parse_args()


def main() -> int:
    args = _parse_args()

    # --status: check API health
    if args.status:
        url = f"{LIGHTER_BASE_URL}{LIGHTER_STATUS_EP}"
        raw = _http_get(url, timeout=8)
        if raw:
            print(json.dumps(raw, indent=2))
            return 0
        else:
            print(f"FAILED: Could not reach {url}", file=sys.stderr)
            return 1

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
        print("=== K465 Lighter FR Monitor — Daemon Run ===", file=sys.stderr)
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
            symbols=K208_SYMBOLS_LIGHTER,
            history_days=args.days,
            fetch_depth=args.depth,
        )
        if args.json:
            print(json.dumps(fr_results, indent=2))
        else:
            print(
                f"\n=== Lighter FR Snapshot "
                f"({datetime.now(JST).strftime('%Y-%m-%d %H:%M JST')}) ==="
            )
            for sym, d in fr_results.items():
                if d.get("ok"):
                    print(
                        f"  {sym:<12s}  FR={d['funding_rate']*100:+.6f}%/8h  "
                        f"ann={d.get('annualized_pct', 0):+.2f}%/yr"
                    )
                else:
                    print(f"  {sym:<12s}  FAILED: {d.get('error', '?')}")
        return 0

    # --history: accumulate historical data
    if args.history:
        print(f"=== Accumulating {args.days}d history for {args.symbol} ===", file=sys.stderr)
        try:
            df = fetch_lighter_history(args.symbol, days=args.days)
            if not getattr(df, "empty", True) and len(df) > 0:
                save_lighter_fr_cache(args.symbol, df)
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
    result = fetch_lighter_funding_rate(args.symbol)
    if args.json:
        print(json.dumps(result, indent=2))
    else:
        if result.get("ok"):
            fr  = result["funding_rate"]
            ann = result.get("annualized_pct", 0.0)
            mk  = result.get("mark_px")
            print(f"\n=== Lighter Funding Rate: {args.symbol} ===")
            print(f"  Current FR:    {fr*100:+.6f}% per 8h")
            print(f"  Annualized:    {ann:+.2f}% per year")
            print(f"  Mark price:    {mk if mk else 'n/a'}")
            print(f"  Fetched at:    {result['fetched_at_utc']}")
            print(f"  Source:        {result['source']}")
            print(f"\n  K465 Lighter → 6th venue for K208 7-venue mesh (v6.20)")
            print(f"  Dashboard:     data/lighter_dashboard.json")
            print(f"  zkEVM base:    {LIGHTER_BASE_URL}")
        else:
            print(f"FAILED: {result.get('error', 'unknown')}", file=sys.stderr)
            print(f"  NOTE: Lighter API ({LIGHTER_BASE_URL}) may require connectivity check.", file=sys.stderr)
            return 1

    return 0


if __name__ == "__main__":
    sys.exit(main())

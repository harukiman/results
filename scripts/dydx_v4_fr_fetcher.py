#!/usr/bin/env python3
"""
dydx_v4_fr_fetcher.py — K460 dYdX v4 Funding Rate Fetcher (K454 v6.20 5th venue)
==================================================================================
Fetches dYdX v4 perpetual funding rates via the dYdX Indexer REST API
and caches them as Parquet for downstream use by K208 and K434 smart router.

Architecture:
  - fetch_dydx_funding_rate(symbol)      → live current FR dict
  - fetch_dydx_history(symbol, days=30)  → 30d historical FR DataFrame
  - save_dydx_fr_cache(symbol, df)       → cache/dydx_v4_fr_{symbol}.parquet
  - fetch_and_cache_all(symbols)         → run all symbols in sequence
  - write_dydx_dashboard()              → data/dydx_v4_dashboard.json

dYdX v4 Indexer REST API base: https://indexer.dydx.trade/v4
  - GET /v4/perpetualMarkets             (all markets: nextFundingRate, OI, price)
  - GET /v4/perpetualMarkets?ticker=BTC-USD  (single market)
  - GET /v4/historicalFunding/{ticker}   (historical funding rates)
  - GET /v4/markets/perpetual/{ticker}   (per-market detail)

Auth: NOT required for Indexer REST endpoints (public read-only).

dYdX v4 Chain context:
  - dYdX v4 is a Cosmos-based appchain (not EVM)
  - Indexer is an off-chain REST service mirroring on-chain state
  - Timestamps: ISO 8601 UTC (e.g. "2026-05-25T12:00:00.000Z")
  - Funding rate: per 1h (nextFundingRate) — annualized = FR × 24 × 365 × 100
  - Market status: ACTIVE | PAUSED | OFFLINE | POST_ONLY | CANCEL_ONLY
  - Historical endpoint: returns list of {ticker, rate, effectiveAt}

K208 Integration (5th venue — K454 v6.20 expansion):
  - dYdX v4 Cosmos-native perps, deep BTC/ETH liquidity
  - nextFundingRate field available on all market objects
  - K434 smart router uses this fetcher's output as dYdX venue score
  - Full trading requires Cosmos signing (dYdX SDK) — TODO for auth phase

K460 context:
  - Wave 6/7 toward v6.20 architecture (K454 plan: venues 3→10).
  - dYdX v4 is 5th major venue (HL=1st, Bybit=2nd, OKX=3rd, Aevo=4th).
  - StartInterval: 3600 (1h — matches dYdX 1h funding cycle).
  - Daemon: com.cryptolab.dydx-v4-fr-monitor (24th daemon, SCAFFOLD-READY).

K339 Security:
  REPO_ROOT = Path(__file__).resolve().parent.parent — no /Users/ literals.
  dYdX v4 Indexer API keys NOT required for read-only fetch.

Usage:
  python3 scripts/dydx_v4_fr_fetcher.py                     # BTC-USD
  python3 scripts/dydx_v4_fr_fetcher.py --symbol ETH-USD
  python3 scripts/dydx_v4_fr_fetcher.py --all               # all K208 symbols
  python3 scripts/dydx_v4_fr_fetcher.py --history --days 30
  python3 scripts/dydx_v4_fr_fetcher.py --dashboard          # print dashboard JSON

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

# ── dYdX v4 Indexer REST API constants ───────────────────────────────────────
# Mainnet indexer (Cosmos-based, read-only, no auth)
DYDX_INDEXER_BASE       = "https://indexer.dydx.trade"
DYDX_MARKETS_EP         = "/v4/perpetualMarkets"     # all markets
DYDX_HISTORICAL_FR_EP   = "/v4/historicalFunding"    # /{ticker}?limit=N
DYDX_ORDERBOOK_EP       = "/v4/orderbooks/perpetualMarket"  # /{ticker}

# dYdX v4 funding: 1h intervals
DYDX_PERIODS_PER_DAY    = 24
DYDX_FUNDING_INTERVAL_S = 3600

# Acceptable market statuses
DYDX_ACTIVE_STATUSES = {"ACTIVE", "POST_ONLY"}

# ── K208 universe symbols (dYdX v4 ticker format: {BASE}-USD) ────────────────
K208_SYMBOLS_DYDX: List[str] = [
    "BTC-USD",
    "ETH-USD",
    "SOL-USD",
    "XRP-USD",
    "DOGE-USD",
    "AVAX-USD",
    "LINK-USD",
    "MATIC-USD",
    "ADA-USD",
    "APT-USD",
    "SUI-USD",
    "OP-USD",
    "ARB-USD",
    "ATOM-USD",
    "NEAR-USD",
    "LTC-USD",
    "UNI-USD",
    "DOT-USD",
]

DASHBOARD_PATH = DATA_DIR / "dydx_v4_dashboard.json"
DECISION_LOG   = DATA_DIR / "dydx_v4_fr_decisions.jsonl"


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
                "User-Agent": "crypto-lab-dydx-v4-fr-fetcher/1.0",
                "Accept":     "application/json",
            },
        )
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            body = resp.read().decode("utf-8")
            return json.loads(body)
    except urllib.error.HTTPError as exc:
        print(f"  [dydx_v4_fr_fetcher] HTTP {exc.code}: {url}", file=sys.stderr)
        return None
    except urllib.error.URLError as exc:
        print(f"  [dydx_v4_fr_fetcher] URL error: {exc.reason} — {url}", file=sys.stderr)
        return None
    except Exception as exc:
        print(f"  [dydx_v4_fr_fetcher] Error: {exc} — {url}", file=sys.stderr)
        return None


def _parse_dydx_timestamp(ts_str: Optional[str]) -> Optional[datetime]:
    """
    Parse dYdX v4 Cosmos-style ISO 8601 timestamp to datetime.

    Formats seen from indexer:
      "2026-05-25T12:00:00.000Z"
      "2026-05-25T12:00:00Z"

    Returns UTC-aware datetime or None on failure.
    """
    if not ts_str:
        return None
    try:
        # Normalize: replace trailing Z with +00:00 for fromisoformat()
        normalized = ts_str.rstrip("Z").split(".")[0] + "+00:00"
        return datetime.fromisoformat(normalized)
    except (ValueError, AttributeError):
        try:
            # Fallback: strptime
            return datetime.strptime(
                ts_str[:19], "%Y-%m-%dT%H:%M:%S"
            ).replace(tzinfo=timezone.utc)
        except ValueError:
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

def fetch_dydx_all_markets() -> Dict[str, dict]:
    """
    Fetch all active dYdX v4 perpetual markets from Indexer.

    GET /v4/perpetualMarkets
    Returns parsed dict {ticker: market_data}.

    Key fields per market:
      nextFundingRate     — next 1h funding rate (fractional string)
      oraclePrice         — oracle/mark price
      status              — ACTIVE | PAUSED | etc.
      openInterest        — open interest (in base asset units)
      volume24H           — 24h volume USD
      priceChange24H      — 24h price change USD
      initialMarginFraction
      maintenanceMarginFraction
    """
    url = f"{DYDX_INDEXER_BASE}{DYDX_MARKETS_EP}"
    raw = _http_get(url, timeout=15)
    if raw is None:
        return {}

    # Response: {"markets": {"BTC-USD": {...}, "ETH-USD": {...}, ...}}
    return raw.get("markets", {})


def fetch_dydx_funding_rate(symbol: str = "BTC-USD") -> dict:
    """
    Fetch live current funding rate for a single dYdX v4 perpetual.

    Uses GET /v4/perpetualMarkets?ticker={symbol} to fetch market state.
    Key field: nextFundingRate (per-1h rate, fractional string).

    dYdX v4 funding rate note:
      - 1h settlement cycle
      - nextFundingRate: approximate rate for next 1h period
      - No separate funding endpoint; embedded in market object
      - Historical: GET /v4/historicalFunding/{ticker}

    Returns:
        {
            "symbol":           "BTC-USD",
            "funding_rate":     float,   # e.g. 0.0000052 per 1h
            "annualized_pct":   float,   # FR × 24 × 365 × 100
            "oracle_price":     float,   # oracle price USD
            "open_interest":    float,   # in base asset (e.g. BTC)
            "volume_24h":       float,   # USD
            "market_status":    str,     # ACTIVE | PAUSED | etc.
            "settlement_period_h": 1,
            "fetched_at_utc":   str,
            "source":           "dYdX_v4_indexer_public",
            "ok":               bool,
        }

    On failure: returns dict with ok=False and error message.
    """
    url = f"{DYDX_INDEXER_BASE}{DYDX_MARKETS_EP}?ticker={symbol}"
    raw = _http_get(url, timeout=10)

    base = {
        "symbol":               symbol,
        "fetched_at_utc":       datetime.now(timezone.utc).isoformat(),
        "source":               "dYdX_v4_indexer_public",
        "settlement_period_h":  1,
        "chain":                "Cosmos (dYdX v4 appchain)",
    }

    if raw is None:
        return {**base, "ok": False, "error": "HTTP request failed"}

    markets = raw.get("markets", {})
    market  = markets.get(symbol)

    if not market:
        return {
            **base,
            "ok": False,
            "error": f"Symbol '{symbol}' not found in markets response",
        }

    try:
        fr_raw      = market.get("nextFundingRate", "0")
        oracle_raw  = market.get("oraclePrice", "0")
        oi_raw      = market.get("openInterest", "0")
        vol_raw     = market.get("volume24H", "0")
        status      = market.get("status", "UNKNOWN")

        fr         = _safe_float(fr_raw) or 0.0
        oracle_px  = _safe_float(oracle_raw) or 0.0
        oi         = _safe_float(oi_raw) or 0.0
        vol_24h    = _safe_float(vol_raw) or 0.0

        # Annualized: FR per 1h × 24/day × 365 days × 100 = %
        annualized = fr * DYDX_PERIODS_PER_DAY * 365 * 100

        return {
            **base,
            "funding_rate":     fr,
            "annualized_pct":   round(annualized, 6),
            "oracle_price":     oracle_px,
            "open_interest":    oi,
            "volume_24h":       vol_24h,
            "market_status":    status,
            "ok":               True,
        }
    except (TypeError, ValueError, KeyError) as exc:
        return {**base, "ok": False, "error": f"Parse error: {exc}"}


def fetch_dydx_history(
    symbol: str = "BTC-USD",
    days:   int = 30,
    limit:  int = 100,
) -> "pd.DataFrame":  # type: ignore[name-defined]
    """
    Fetch historical funding rates from dYdX v4 Indexer.

    GET /v4/historicalFunding/{ticker}?limit={limit}
    Returns funding records with ISO 8601 timestamps (Cosmos format).

    dYdX historical record fields:
      ticker      — e.g. "BTC-USD"
      rate        — fractional rate per 1h
      price       — oracle price at settlement
      effectiveAt — ISO 8601 UTC timestamp (Cosmos chain time)

    Returns:
        pd.DataFrame with columns:
          fundingTime   (datetime, UTC)
          fundingRate   (float)
          oracle_price  (float)
          symbol        (str)

    Returns empty DataFrame on failure.
    """
    try:
        import pandas as pd
    except ImportError:
        print("  [dydx_v4_fr_fetcher] pandas not available", file=sys.stderr)
        import types
        empty_df = types.SimpleNamespace()
        empty_df.empty = True
        return empty_df  # type: ignore

    # dYdX historical funding endpoint
    url = (
        f"{DYDX_INDEXER_BASE}{DYDX_HISTORICAL_FR_EP}/{symbol}"
        f"?limit={limit}"
    )
    raw = _http_get(url, timeout=15)

    if raw is None:
        print(
            f"  [dydx_v4_fr_fetcher] Historical fetch failed for {symbol}",
            file=sys.stderr,
        )
        return pd.DataFrame()

    # Response: {"historicalFunding": [{ticker, rate, price, effectiveAt}, ...]}
    funding_list = raw.get("historicalFunding", [])
    if not funding_list:
        # Some versions return list directly
        if isinstance(raw, list):
            funding_list = raw
        else:
            print(
                f"  [dydx_v4_fr_fetcher] No historical data returned for {symbol}",
                file=sys.stderr,
            )
            return pd.DataFrame()

    cutoff_utc = datetime.now(timezone.utc) - timedelta(days=days)
    records = []

    for item in funding_list:
        try:
            ts_str  = item.get("effectiveAt", "")
            dt      = _parse_dydx_timestamp(ts_str)
            if dt is None or dt.replace(tzinfo=timezone.utc) < cutoff_utc:
                # Make dt timezone-aware for comparison
                if dt and dt.tzinfo is None:
                    dt = dt.replace(tzinfo=timezone.utc)
                if dt is None or dt < cutoff_utc:
                    continue

            rate     = _safe_float(item.get("rate")) or 0.0
            oracle   = _safe_float(item.get("price")) or 0.0
            records.append({
                "fundingTime":  pd.Timestamp(dt),
                "fundingRate":  rate,
                "oracle_price": oracle,
                "symbol":       symbol,
            })
        except (TypeError, ValueError, KeyError):
            continue

    if not records:
        print(
            f"  [dydx_v4_fr_fetcher] No records in {days}d window for {symbol}",
            file=sys.stderr,
        )
        return pd.DataFrame()

    df = pd.DataFrame(records).sort_values("fundingTime").reset_index(drop=True)
    print(
        f"  [dydx_v4_fr_fetcher] History: {symbol} — {len(df)} records ({days}d window)",
        file=sys.stderr,
    )
    return df


def fetch_dydx_orderbook_depth(symbol: str = "BTC-USD") -> float:
    """
    Estimate top-of-book depth (USD) from dYdX v4 Indexer order book.
    GET /v4/orderbooks/perpetualMarket/{ticker}

    Returns depth_usd estimate. Falls back to 1_000_000.0 (conservative).
    """
    url = f"{DYDX_INDEXER_BASE}{DYDX_ORDERBOOK_EP}/{symbol}"
    raw = _http_get(url, timeout=8)
    if raw is None:
        return 1_000_000.0

    try:
        bids = raw.get("bids", [])
        asks = raw.get("asks", [])
        # dYdX format: [{price, size}, ...] (strings)
        bid_depth = sum(
            float(b["price"]) * float(b["size"]) for b in bids[:5]
            if "price" in b and "size" in b
        )
        ask_depth = sum(
            float(a["price"]) * float(a["size"]) for a in asks[:5]
            if "price" in a and "size" in a
        )
        return bid_depth + ask_depth
    except (TypeError, ValueError, KeyError):
        return 1_000_000.0


# ─────────────────────────────────────────────────────────────────────────────
# Cache management
# ─────────────────────────────────────────────────────────────────────────────

def save_dydx_fr_cache(symbol: str, df: "pd.DataFrame") -> Path:  # type: ignore[name-defined]
    """
    Write funding rate history DataFrame to cache/dydx_v4_fr_{symbol}.parquet.

    symbol: e.g. "BTC-USD" (dYdX v4 ticker format)
    df:     DataFrame from fetch_dydx_history()

    Returns: Path to written file.
    K339: uses REPO_ROOT-relative path, no absolute /Users/ literal.
    """
    safe_sym = symbol.replace("/", "_").replace("-", "_")
    path = CACHE_DIR / f"dydx_v4_fr_{safe_sym}.parquet"
    try:
        df.to_parquet(path, index=False)
        print(
            f"  [dydx_v4_fr_fetcher] Cache written: {path.name} ({len(df)} rows)",
            file=sys.stderr,
        )
    except Exception as exc:
        print(f"  [dydx_v4_fr_fetcher] Cache write error: {exc}", file=sys.stderr)
    return path


def load_dydx_fr_cache(symbol: str) -> Optional["pd.DataFrame"]:  # type: ignore[name-defined]
    """Load cached FR history. Returns DataFrame or None if cache missing."""
    try:
        import pandas as pd
    except ImportError:
        return None

    safe_sym = symbol.replace("/", "_").replace("-", "_")
    path = CACHE_DIR / f"dydx_v4_fr_{safe_sym}.parquet"
    if not path.is_file():
        return None
    try:
        return pd.read_parquet(path)
    except Exception as exc:
        print(f"  [dydx_v4_fr_fetcher] Cache load error: {exc}", file=sys.stderr)
        return None


# ─────────────────────────────────────────────────────────────────────────────
# Dashboard I/O
# ─────────────────────────────────────────────────────────────────────────────

def write_dydx_dashboard(
    fr_results: Dict[str, dict],
    depth_map:  Optional[Dict[str, float]] = None,
) -> None:
    """
    Write data/dydx_v4_dashboard.json with latest FR snapshot.

    Schema:
      last_poll_utc     — ISO timestamp of this poll
      last_poll_jst     — JST-formatted string
      btc_fr            — BTC funding rate (fractional, 1h period)
      eth_fr            — ETH funding rate (fractional, 1h period)
      symbols           — list of per-symbol dicts
      daemon_label      — com.cryptolab.dydx-v4-fr-monitor
      wave              — K460
      status            — SCAFFOLD-READY
      venue             — dYdX v4
      chain             — Cosmos (dYdX v4 appchain)
    """
    now_utc = datetime.now(timezone.utc)
    now_jst = now_utc.astimezone(JST)

    symbol_rows = []
    for sym, d in fr_results.items():
        symbol_rows.append({
            "symbol":         sym,
            "funding_rate":   d.get("funding_rate", 0.0),
            "oracle_price":   d.get("oracle_price", 0.0),
            "annualized_pct": d.get("annualized_pct", 0.0),
            "open_interest":  d.get("open_interest", 0.0),
            "volume_24h":     d.get("volume_24h", 0.0),
            "market_status":  d.get("market_status", "UNKNOWN"),
            "ok":             d.get("ok", False),
        })

    btc_d = fr_results.get("BTC-USD", {})
    eth_d = fr_results.get("ETH-USD", {})

    payload = {
        "_comment": (
            "K460 dYdX v4 FR Monitor dashboard "
            "(K454 v6.20 5th venue, 24th daemon, 1h funding cycle, Cosmos chain)"
        ),
        "_wave":             "K460",
        "last_poll_utc":     now_utc.isoformat(),
        "last_poll_jst":     now_jst.strftime("%Y-%m-%d %H:%M JST"),
        "btc_fr":            btc_d.get("funding_rate", None),
        "btc_oracle_price":  btc_d.get("oracle_price", None),
        "btc_annualized":    btc_d.get("annualized_pct", None),
        "eth_fr":            eth_d.get("funding_rate", None),
        "eth_oracle_price":  eth_d.get("oracle_price", None),
        "eth_annualized":    eth_d.get("annualized_pct", None),
        "symbols":           symbol_rows,
        "depth_map_usd":     depth_map or {},
        "daemon_label":      "com.cryptolab.dydx-v4-fr-monitor",
        "daemon_number":     24,
        "start_interval":    DYDX_FUNDING_INTERVAL_S,   # 3600 = 1h
        "settlement_period_h": 1,
        "status":            "SCAFFOLD-READY",
        "venue":             "dYdX v4",
        "chain":             "Cosmos (dYdX v4 appchain)",
        "api_base":          DYDX_INDEXER_BASE,
        "indexer_note":      "Public Indexer REST — no auth required for read-only data",
        "trading_auth_note": "Full trading requires Cosmos tx signing via dYdX SDK (TODO K460+)",
        "version_target":    "v6.20",
        "k208_venues":       ["HL", "Bybit", "OKX", "Aevo", "dYdX_v4"],
        "notes": (
            "dYdX v4 is Cosmos-based (not EVM). "
            "Indexer at indexer.dydx.trade — no API key for read-only. "
            "Timestamps: ISO 8601 UTC (Cosmos chain time). "
            "nextFundingRate: per-1h fractional rate. "
            "Annualized = FR × 24 × 365 × 100. "
            "Historical: GET /v4/historicalFunding/{ticker}."
        ),
    }

    tmp = DASHBOARD_PATH.with_suffix(".tmp")
    with open(tmp, "w") as f:
        json.dump(payload, f, indent=2)
    tmp.replace(DASHBOARD_PATH)
    print(
        f"  [dydx_v4_fr_fetcher] Dashboard written: {DASHBOARD_PATH.name}",
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
    Main daemon loop: fetch live FR for all symbols, cache history,
    and write dashboard.

    Called by com.cryptolab.dydx-v4-fr-monitor daemon every 1h.

    Optimization: fetches ALL markets in a single API call, then parses
    per-symbol. This is more efficient than N per-symbol calls.

    Args:
        symbols:       dYdX ticker list (default: K208_SYMBOLS_DYDX)
        history_days:  Days of history to cache for BTC/ETH (default 30)
        fetch_depth:   Whether to fetch order book depth (slower)

    Returns:
        fr_results dict {symbol: result_dict}
    """
    if symbols is None:
        symbols = K208_SYMBOLS_DYDX

    print(
        f"  [dydx_v4_fr_fetcher] Starting bulk fetch: {len(symbols)} symbols",
        file=sys.stderr,
    )
    t0 = time.time()

    # Fetch all markets in a single call (efficient)
    all_markets = fetch_dydx_all_markets()
    print(
        f"  [dydx_v4_fr_fetcher] Markets fetched: {len(all_markets)} total",
        file=sys.stderr,
    )

    fr_results: Dict[str, dict] = {}
    depth_map:  Dict[str, float] = {}
    now_utc = datetime.now(timezone.utc).isoformat()

    for sym in symbols:
        base = {
            "symbol":              sym,
            "fetched_at_utc":      now_utc,
            "source":              "dYdX_v4_indexer_public",
            "settlement_period_h": 1,
            "chain":               "Cosmos (dYdX v4 appchain)",
        }

        market = all_markets.get(sym)
        if not market:
            result = {**base, "ok": False, "error": f"Not found in markets: {sym}"}
        else:
            try:
                fr         = _safe_float(market.get("nextFundingRate")) or 0.0
                oracle_px  = _safe_float(market.get("oraclePrice")) or 0.0
                oi         = _safe_float(market.get("openInterest")) or 0.0
                vol_24h    = _safe_float(market.get("volume24H")) or 0.0
                status     = market.get("status", "UNKNOWN")
                annualized = fr * DYDX_PERIODS_PER_DAY * 365 * 100

                result = {
                    **base,
                    "funding_rate":   fr,
                    "annualized_pct": round(annualized, 6),
                    "oracle_price":   oracle_px,
                    "open_interest":  oi,
                    "volume_24h":     vol_24h,
                    "market_status":  status,
                    "ok":             True,
                }
            except (TypeError, ValueError, KeyError) as exc:
                result = {**base, "ok": False, "error": f"Parse error: {exc}"}

        fr_results[sym] = result

        if result.get("ok"):
            fr  = result["funding_rate"]
            ann = result.get("annualized_pct", 0.0)
            px  = result.get("oracle_price", 0.0)
            st  = result.get("market_status", "?")
            print(
                f"    {sym:<12s}  FR={fr*100:+.6f}%/1h  "
                f"ann={ann:+.2f}%/yr  oracle={px:,.2f}  [{st}]",
                file=sys.stderr,
            )
        else:
            print(
                f"    {sym:<12s}  FAILED: {result.get('error', '?')}",
                file=sys.stderr,
            )

    # Depth fetch (optional)
    if fetch_depth:
        for sym in ["BTC-USD", "ETH-USD"]:
            depth_map[sym] = fetch_dydx_orderbook_depth(sym)
            time.sleep(0.2)

    # History cache for BTC and ETH
    for hist_sym in ["BTC-USD", "ETH-USD"]:
        try:
            import pandas as pd
            df = fetch_dydx_history(hist_sym, days=history_days)
            if not getattr(df, "empty", True) and len(df) > 0:
                save_dydx_fr_cache(hist_sym, df)
        except Exception as exc:
            print(
                f"  [dydx_v4_fr_fetcher] Cache error for {hist_sym}: {exc}",
                file=sys.stderr,
            )
        time.sleep(0.3)

    # Write dashboard
    write_dydx_dashboard(fr_results, depth_map)

    elapsed  = time.time() - t0
    ok_count = sum(1 for r in fr_results.values() if r.get("ok"))
    print(
        f"  [dydx_v4_fr_fetcher] Done: {ok_count}/{len(symbols)} OK in {elapsed:.1f}s",
        file=sys.stderr,
    )

    return fr_results


# ─────────────────────────────────────────────────────────────────────────────
# K208 Cross-Venue Arbitrage Helper
# ─────────────────────────────────────────────────────────────────────────────

def compute_cross_venue_opportunities(
    dydx_results:  Dict[str, dict],
    hl_fr_map:     Optional[Dict[str, float]] = None,
    bybit_fr_map:  Optional[Dict[str, float]] = None,
    okx_fr_map:    Optional[Dict[str, float]] = None,
    aevo_fr_map:   Optional[Dict[str, float]] = None,
    threshold_bps: float = 5.0,
) -> List[dict]:
    """
    Compare dYdX v4 FR against HL/Bybit/OKX/Aevo for cross-venue carry opportunities.

    NOTE: All rates should be on the same time basis.
    dYdX nextFundingRate is per 1h; normalize to 8h for comparison with HL/Bybit/OKX:
      dYdX_8h_equiv = dYdX_1h_FR × 8

    Returns list of opportunity dicts sorted by spread_bps desc.
    """
    opportunities = []

    for sym, dydx_d in dydx_results.items():
        if not dydx_d.get("ok"):
            continue

        dydx_fr_1h = dydx_d["funding_rate"]
        dydx_fr_8h = dydx_fr_1h * 8   # normalize to 8h basis

        # Convert dYdX format (BTC-USD) to base symbol (BTC)
        base_sym = sym.replace("-USD", "")

        fr_map: Dict[str, float] = {"dYdX_8h": dydx_fr_8h}
        if hl_fr_map and base_sym in hl_fr_map:
            fr_map["HL"] = hl_fr_map[base_sym]
        if bybit_fr_map and base_sym in bybit_fr_map:
            fr_map["Bybit"] = bybit_fr_map[base_sym]
        if okx_fr_map and base_sym in okx_fr_map:
            fr_map["OKX"] = okx_fr_map[base_sym]
        if aevo_fr_map and base_sym in aevo_fr_map:
            fr_map["Aevo_8h"] = aevo_fr_map[base_sym] * 8

        if len(fr_map) < 2:
            continue

        max_venue  = max(fr_map, key=fr_map.get)  # type: ignore[arg-type]
        min_venue  = min(fr_map, key=fr_map.get)  # type: ignore[arg-type]
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
                "dydx_1h_fr":  dydx_fr_1h,
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
            "K460 dYdX v4 Funding Rate Fetcher "
            "(K454 v6.20 5th venue, 24th daemon, Cosmos chain, 1h cycle)"
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Live BTC FR (default):
  python3 scripts/dydx_v4_fr_fetcher.py

  # Specific symbol:
  python3 scripts/dydx_v4_fr_fetcher.py --symbol ETH-USD

  # Fetch all K208 symbols + write dashboard:
  python3 scripts/dydx_v4_fr_fetcher.py --all

  # Fetch 30d BTC history + cache:
  python3 scripts/dydx_v4_fr_fetcher.py --history --symbol BTC-USD --days 30

  # Full daemon run (all symbols + history + dashboard):
  python3 scripts/dydx_v4_fr_fetcher.py --daemon

  # Print dashboard JSON:
  python3 scripts/dydx_v4_fr_fetcher.py --dashboard

K460 context: dYdX v4 is 5th K208 venue (HL+Bybit+OKX+Aevo+dYdX_v4 = v6.20).
24th daemon: com.cryptolab.dydx-v4-fr-monitor (StartInterval 3600, 1h cycle).
Chain: Cosmos (dYdX v4 appchain). Indexer: indexer.dydx.trade (no auth needed).
Full trading requires Cosmos SDK signing — scaffold read-only only (K460 scope).
        """,
    )
    p.add_argument("--symbol",    default="BTC-USD",
                   help="dYdX ticker (default: BTC-USD)")
    p.add_argument("--all",       action="store_true",
                   help="Fetch all K208 symbols")
    p.add_argument("--history",   action="store_true",
                   help="Fetch historical FR data for the symbol")
    p.add_argument("--days",      type=int, default=30,
                   help="Days of history to fetch (default: 30)")
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
        print("=== K460 dYdX v4 FR Monitor — Daemon Run ===", file=sys.stderr)
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
            symbols=K208_SYMBOLS_DYDX,
            history_days=args.days,
            fetch_depth=args.depth,
        )
        if args.json:
            print(json.dumps(fr_results, indent=2))
        else:
            print(
                f"\n=== dYdX v4 FR Snapshot "
                f"({datetime.now(JST).strftime('%Y-%m-%d %H:%M JST')}) ==="
            )
            for sym, d in fr_results.items():
                if d.get("ok"):
                    print(
                        f"  {sym:<12s}  FR={d['funding_rate']*100:+.6f}%/1h  "
                        f"ann={d.get('annualized_pct', 0):+.2f}%/yr  "
                        f"oracle={d.get('oracle_price', 0):,.2f}"
                    )
                else:
                    print(f"  {sym:<12s}  FAILED: {d.get('error', '?')}")
        return 0

    # --history: historical data
    if args.history:
        print(f"=== Fetching {args.days}d history for {args.symbol} ===", file=sys.stderr)
        try:
            df = fetch_dydx_history(args.symbol, days=args.days)
            if not getattr(df, "empty", True) and len(df) > 0:
                save_dydx_fr_cache(args.symbol, df)
                if args.json:
                    print(df.to_json(orient="records", date_format="iso"))
                else:
                    print(df.to_string())
            else:
                print("No data returned.")
        except Exception as exc:
            print(f"Error: {exc}")
        return 0

    # Default: single symbol live fetch
    result = fetch_dydx_funding_rate(args.symbol)
    if args.json:
        print(json.dumps(result, indent=2))
    else:
        if result.get("ok"):
            fr  = result["funding_rate"]
            ann = result.get("annualized_pct", 0.0)
            px  = result.get("oracle_price", 0.0)
            oi  = result.get("open_interest", 0.0)
            st  = result.get("market_status", "?")
            print(f"\n=== dYdX v4 Funding Rate: {args.symbol} ===")
            print(f"  Current FR:    {fr*100:+.6f}% per 1h (dYdX v4 Cosmos)")
            print(f"  8h equivalent: {fr*8*100:+.6f}% per 8h (for HL/Bybit/OKX comparison)")
            print(f"  Annualized:    {ann:+.2f}% per year")
            print(f"  Oracle price:  ${px:,.2f}")
            print(f"  Open interest: {oi:,.4f} {args.symbol.replace('-USD', '')}")
            print(f"  Market status: {st}")
            print(f"  Fetched at:    {result['fetched_at_utc']}")
            print(f"  Chain:         {result['chain']}")
            print(f"\n  K460 dYdX v4 → 5th venue for K208 cross-venue FR arb")
            print(f"  Indexer:       {DYDX_INDEXER_BASE} (public, no auth)")
            print(f"  Dashboard:     data/dydx_v4_dashboard.json")
            print(f"  NOTE: 1h period — trading requires Cosmos signing (TODO post-K460)")
        else:
            print(f"FAILED: {result.get('error', 'unknown')}", file=sys.stderr)
            return 1

    return 0


if __name__ == "__main__":
    sys.exit(main())

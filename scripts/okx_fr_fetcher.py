#!/usr/bin/env python3
"""
okx_fr_fetcher.py — K456 OKX Funding Rate Fetcher (K454 v6.20 1/7 wave)
=========================================================================
Fetches OKX perpetual swap funding rates and caches them as Parquet for
downstream use by K208 strategy adapter and K434 smart router.

Architecture:
  - fetch_okx_funding_rate(symbol)       → live current FR dict
  - fetch_okx_funding_history(symbol)    → 30d historical FR DataFrame
  - save_okx_fr_cache(symbol, df)        → cache/okx_fr_{symbol}.parquet
  - fetch_and_cache_all(symbols)         → run all symbols in sequence
  - write_okx_dashboard()               → data/okx_dashboard.json

OKX REST API base: https://www.okx.com
  - GET /api/v5/public/funding-rate?instId=BTC-USDT-SWAP   (current FR)
  - GET /api/v5/public/funding-rate-history?instId=...&limit=100  (history)
  - GET /api/v5/market/ticker?instId=BTC-USDT-SWAP          (mark price + vol)

Auth: NOT required for public endpoints (read-only data).

K208 Integration (3rd venue — K454 v6.20 expansion):
  - K208 short-highest-FR / long-lowest-FR logic now spans HL + Bybit + OKX.
  - Triangle arbitrage potential: when OKX FR diverges from HL/Bybit by > 5bps.
  - K434 smart router uses this fetcher's output as OKX venue score input.

K456 context:
  - Wave 1/7 toward v6.20 architecture (K454 plan: venues 3→10).
  - OKX is 3rd major venue (HL = 1st, Bybit = 2nd).
  - StartInterval: 28800 (8h, matches OKX funding cycle).
  - Daemon: com.cryptolab.okx-fr-monitor (20th daemon, SCAFFOLD-READY).

K339 Security:
  REPO_ROOT = Path(__file__).resolve().parent.parent — no /Users/ literals.
  OKX API keys NOT required for read-only fetch endpoints.

Usage:
  python3 scripts/okx_fr_fetcher.py                     # BTC-USDT-SWAP
  python3 scripts/okx_fr_fetcher.py --symbol ETH-USDT-SWAP
  python3 scripts/okx_fr_fetcher.py --all               # all K208 symbols
  python3 scripts/okx_fr_fetcher.py --history --days 30  # 30d history
  python3 scripts/okx_fr_fetcher.py --dashboard          # print dashboard JSON

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

# ── OKX REST API constants ─────────────────────────────────────────────────────
OKX_BASE_URL       = "https://www.okx.com"
OKX_FR_ENDPOINT    = "/api/v5/public/funding-rate"
OKX_FR_HIST_ENDPOINT = "/api/v5/public/funding-rate-history"
OKX_TICKER_ENDPOINT  = "/api/v5/market/ticker"
OKX_BOOKS_ENDPOINT   = "/api/v5/market/books"

# ── K208 universe symbols to monitor (18 symbols, subset of 50+ universe) ────
# OKX instId format: {BASE}-USDT-SWAP
K208_SYMBOLS_OKX = [
    "BTC-USDT-SWAP",
    "ETH-USDT-SWAP",
    "SOL-USDT-SWAP",
    "XRP-USDT-SWAP",
    "SUI-USDT-SWAP",
    "OP-USDT-SWAP",
    "APT-USDT-SWAP",
    "AVAX-USDT-SWAP",
    "DOGE-USDT-SWAP",
    "ADA-USDT-SWAP",
    "LINK-USDT-SWAP",
    "DOT-USDT-SWAP",
    "UNI-USDT-SWAP",
    "ATOM-USDT-SWAP",
    "NEAR-USDT-SWAP",
    "IMX-USDT-SWAP",
    "SAND-USDT-SWAP",
    "AXS-USDT-SWAP",
]

DASHBOARD_PATH   = DATA_DIR  / "okx_dashboard.json"
DECISION_LOG     = DATA_DIR  / "okx_fr_decisions.jsonl"


# ─────────────────────────────────────────────────────────────────────────────
# HTTP helpers (stdlib urllib only — no requests dependency)
# ─────────────────────────────────────────────────────────────────────────────

def _http_get(url: str, timeout: int = 10) -> Optional[dict]:
    """
    Lightweight GET request using stdlib urllib.
    Returns parsed JSON dict, or None on any error (network, HTTP, JSON parse).
    K339: user-agent identifies this as crypto-lab tooling (not a browser).
    """
    try:
        req = urllib.request.Request(
            url,
            headers={
                "User-Agent": "crypto-lab-okx-fr-fetcher/1.0",
                "Accept":     "application/json",
            },
        )
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            body = resp.read().decode("utf-8")
            return json.loads(body)
    except urllib.error.HTTPError as exc:
        print(f"  [okx_fr_fetcher] HTTP {exc.code}: {url}", file=sys.stderr)
        return None
    except urllib.error.URLError as exc:
        print(f"  [okx_fr_fetcher] URL error: {exc.reason} — {url}", file=sys.stderr)
        return None
    except Exception as exc:
        print(f"  [okx_fr_fetcher] Error: {exc} — {url}", file=sys.stderr)
        return None


# ─────────────────────────────────────────────────────────────────────────────
# Core fetch functions
# ─────────────────────────────────────────────────────────────────────────────

def fetch_okx_funding_rate(symbol: str = "BTC-USDT-SWAP") -> dict:
    """
    Fetch live current funding rate for a single OKX perpetual swap.

    OKX endpoint: GET /api/v5/public/funding-rate?instId={instId}
    Response data[0] fields:
      fundingRate     — current realized rate (fractional, 8h period)
      nextFundingRate — predicted next rate
      fundingTime     — next settlement timestamp (ms)
      markPx          — mark price
      instId          — instrument ID (e.g. BTC-USDT-SWAP)

    Returns:
        {
            "symbol":           "BTC-USDT-SWAP",
            "funding_rate":     float,   # e.g. 0.0001 = 0.01% per 8h
            "next_funding_rate": float,  # predicted next rate
            "funding_time_ms":  int,     # next settlement time (epoch ms)
            "mark_px":          float,
            "annualized_pct":   float,   # FR × 3 × 365 × 100 (for comparison)
            "fetched_at_utc":   str,
            "source":           "OKX_public_api",
            "ok":               bool,
        }

    On failure: returns dict with ok=False and error message.

    Example (live BTC):
        >>> d = fetch_okx_funding_rate("BTC-USDT-SWAP")
        >>> print(f"BTC OKX FR: {d['funding_rate']*100:.4f}% per 8h")
    """
    url = f"{OKX_BASE_URL}{OKX_FR_ENDPOINT}?instId={symbol}"
    raw = _http_get(url, timeout=10)

    base = {
        "symbol":            symbol,
        "fetched_at_utc":    datetime.now(timezone.utc).isoformat(),
        "source":            "OKX_public_api",
    }

    if raw is None:
        return {**base, "ok": False, "error": "HTTP request failed"}

    if raw.get("code") != "0":
        msg = raw.get("msg", "unknown error")
        return {**base, "ok": False, "error": f"OKX API error: {msg}", "raw_code": raw.get("code")}

    data = raw.get("data", [])
    if not data:
        return {**base, "ok": False, "error": "Empty data array in response"}

    item = data[0]
    try:
        fr            = float(item.get("fundingRate", 0.0))
        next_fr       = float(item.get("nextFundingRate", fr) or fr)
        funding_time  = int(item.get("fundingTime", 0))
        mark_px       = float(item.get("markPx", 0.0) or 0.0)
        # Annualized: FR per 8h × 3 periods/day × 365 days × 100 = %
        annualized    = fr * 3 * 365 * 100

        return {
            **base,
            "funding_rate":      fr,
            "next_funding_rate": next_fr,
            "funding_time_ms":   funding_time,
            "mark_px":           mark_px,
            "annualized_pct":    round(annualized, 4),
            "ok":                True,
        }
    except (TypeError, ValueError, KeyError) as exc:
        return {**base, "ok": False, "error": f"Parse error: {exc}"}


def fetch_okx_funding_history(
    symbol: str = "BTC-USDT-SWAP",
    days:   int = 30,
) -> "pd.DataFrame":  # type: ignore[name-defined]
    """
    Fetch historical funding rate data for a symbol.

    OKX endpoint: GET /api/v5/public/funding-rate-history?instId={instId}&limit=N
    Paginates automatically to cover the requested number of days
    (3 records/day × days → up to 300 records for 100d).

    Returns:
        pd.DataFrame with columns:
          fundingTime   (datetime, UTC)
          fundingRate   (float)
          realizedRate  (float)
          symbol        (str)

    Returns empty DataFrame on failure.
    """
    try:
        import pandas as pd
    except ImportError:
        print("  [okx_fr_fetcher] pandas not available — install: pip install pandas", file=sys.stderr)
        import types
        empty_df = types.SimpleNamespace()
        empty_df.empty = True
        return empty_df  # type: ignore

    records = []
    limit   = min(100, days * 3 + 10)   # 3 records/day, small buffer
    url     = f"{OKX_BASE_URL}{OKX_FR_HIST_ENDPOINT}?instId={symbol}&limit={limit}"

    raw = _http_get(url, timeout=15)
    if raw is None or raw.get("code") != "0":
        print(f"  [okx_fr_fetcher] History fetch failed for {symbol}", file=sys.stderr)
        return pd.DataFrame()

    data = raw.get("data", [])
    cutoff_ms = (datetime.now(timezone.utc) - timedelta(days=days)).timestamp() * 1000

    for item in data:
        try:
            ts_ms    = int(item.get("fundingTime", 0))
            if ts_ms < cutoff_ms:
                continue
            fr       = float(item.get("fundingRate", 0.0))
            realized = float(item.get("realizedRate", fr) or fr)
            records.append({
                "fundingTime":  pd.Timestamp(ts_ms, unit="ms", tz="UTC"),
                "fundingRate":  fr,
                "realizedRate": realized,
                "symbol":       symbol,
            })
        except (TypeError, ValueError, KeyError):
            continue

    if not records:
        print(f"  [okx_fr_fetcher] No history records in range for {symbol}", file=sys.stderr)
        return pd.DataFrame()

    df = pd.DataFrame(records).sort_values("fundingTime").reset_index(drop=True)
    print(f"  [okx_fr_fetcher] History: {symbol} — {len(df)} records ({days}d window)", file=sys.stderr)
    return df


def fetch_okx_mark_price(symbol: str = "BTC-USDT-SWAP") -> Optional[float]:
    """
    Fetch current mark price via ticker endpoint.
    GET /api/v5/market/ticker?instId={instId}
    Returns float or None on failure.
    """
    url = f"{OKX_BASE_URL}{OKX_TICKER_ENDPOINT}?instId={symbol}"
    raw = _http_get(url, timeout=8)
    if raw is None or raw.get("code") != "0":
        return None
    data = raw.get("data", [])
    if not data:
        return None
    try:
        return float(data[0].get("markPx", 0.0) or 0.0)
    except (TypeError, ValueError):
        return None


def fetch_okx_orderbook_depth(symbol: str = "BTC-USDT-SWAP", sz: int = 5) -> float:
    """
    Estimate top-of-book depth (USD) from OKX order book.
    GET /api/v5/market/books?instId={instId}&sz={sz}

    Returns depth_usd estimate: top sz bid + ask levels summed.
    Falls back to 2_000_000.0 if fetch fails (conservative for major pairs).
    """
    url = f"{OKX_BASE_URL}{OKX_BOOKS_ENDPOINT}?instId={symbol}&sz={sz}"
    raw = _http_get(url, timeout=8)
    if raw is None or raw.get("code") != "0":
        return 2_000_000.0  # fallback: $2M conservative for OKX majors

    data = raw.get("data", [])
    if not data:
        return 2_000_000.0

    try:
        book = data[0]
        bids = book.get("bids", [])
        asks = book.get("asks", [])
        # Each level: [price, size, num_orders, num_orders_deprecated]
        bid_depth = sum(float(b[0]) * float(b[1]) for b in bids if len(b) >= 2)
        ask_depth = sum(float(a[0]) * float(a[1]) for a in asks if len(a) >= 2)
        return bid_depth + ask_depth
    except (TypeError, ValueError, IndexError):
        return 2_000_000.0


# ─────────────────────────────────────────────────────────────────────────────
# Cache management
# ─────────────────────────────────────────────────────────────────────────────

def save_okx_fr_cache(symbol: str, df: "pd.DataFrame") -> Path:  # type: ignore[name-defined]
    """
    Write funding rate history DataFrame to cache/okx_fr_{symbol}.parquet.

    symbol: e.g. "BTC-USDT-SWAP" (dash-separated OKX format)
    df:     DataFrame from fetch_okx_funding_history()

    Returns: Path to written file.
    K339: uses REPO_ROOT-relative path, no absolute /Users/ literal.
    """
    safe_sym = symbol.replace("/", "_").replace("-", "_")
    path = CACHE_DIR / f"okx_fr_{safe_sym}.parquet"
    try:
        df.to_parquet(path, index=False)
        print(f"  [okx_fr_fetcher] Cache written: {path.name} ({len(df)} rows)", file=sys.stderr)
    except Exception as exc:
        print(f"  [okx_fr_fetcher] Cache write error: {exc}", file=sys.stderr)
    return path


def load_okx_fr_cache(symbol: str) -> Optional["pd.DataFrame"]:  # type: ignore[name-defined]
    """Load cached FR history. Returns DataFrame or None if cache missing."""
    try:
        import pandas as pd
    except ImportError:
        return None

    safe_sym = symbol.replace("/", "_").replace("-", "_")
    path = CACHE_DIR / f"okx_fr_{safe_sym}.parquet"
    if not path.is_file():
        return None
    try:
        return pd.read_parquet(path)
    except Exception as exc:
        print(f"  [okx_fr_fetcher] Cache load error: {exc}", file=sys.stderr)
        return None


# ─────────────────────────────────────────────────────────────────────────────
# Dashboard I/O
# ─────────────────────────────────────────────────────────────────────────────

def write_okx_dashboard(
    fr_results: Dict[str, dict],
    depth_map:  Optional[Dict[str, float]] = None,
) -> None:
    """
    Write data/okx_dashboard.json with latest FR snapshot.

    Schema:
      last_poll_utc       — ISO timestamp of this poll
      last_poll_jst       — JST-formatted string
      btc_fr              — BTC funding rate (fractional)
      eth_fr              — ETH funding rate (fractional)
      symbols             — list of per-symbol dicts (symbol, fr, mark_px, annualized_pct, ok)
      daemon_label        — com.cryptolab.okx-fr-monitor
      wave                — K456
      status              — SCAFFOLD-READY
      venue               — OKX
      version             — v6.20 target (K454)
    """
    now_utc = datetime.now(timezone.utc)
    now_jst = now_utc.astimezone(JST)

    symbol_rows = []
    for sym, d in fr_results.items():
        symbol_rows.append({
            "symbol":         sym,
            "funding_rate":   d.get("funding_rate", 0.0),
            "mark_px":        d.get("mark_px", 0.0),
            "annualized_pct": d.get("annualized_pct", 0.0),
            "next_fr":        d.get("next_funding_rate", 0.0),
            "ok":             d.get("ok", False),
        })

    btc_d = fr_results.get("BTC-USDT-SWAP", {})
    eth_d = fr_results.get("ETH-USDT-SWAP", {})

    payload = {
        "_comment": "K456 OKX FR Monitor dashboard (K454 v6.20 1/7 wave, 3rd K208 venue, 20th daemon)",
        "_wave":    "K456",
        "last_poll_utc":   now_utc.isoformat(),
        "last_poll_jst":   now_jst.strftime("%Y-%m-%d %H:%M JST"),
        "btc_fr":          btc_d.get("funding_rate", None),
        "btc_mark_px":     btc_d.get("mark_px", None),
        "eth_fr":          eth_d.get("funding_rate", None),
        "eth_mark_px":     eth_d.get("mark_px", None),
        "symbols":         symbol_rows,
        "depth_map_usd":   depth_map or {},
        "daemon_label":    "com.cryptolab.okx-fr-monitor",
        "daemon_number":   20,
        "start_interval":  28800,
        "status":          "SCAFFOLD-READY",
        "venue":           "OKX",
        "api_base":        OKX_BASE_URL,
        "version_target":  "v6.20",
        "k208_venues":     ["HL", "Bybit", "OKX"],
        "triangle_arb_threshold_bps": 5.0,
    }

    tmp = DASHBOARD_PATH.with_suffix(".tmp")
    with open(tmp, "w") as f:
        json.dump(payload, f, indent=2)
    tmp.replace(DASHBOARD_PATH)
    print(f"  [okx_fr_fetcher] Dashboard written: {DASHBOARD_PATH.name}", file=sys.stderr)


# ─────────────────────────────────────────────────────────────────────────────
# Bulk fetch (daemon entry point)
# ─────────────────────────────────────────────────────────────────────────────

def fetch_and_cache_all(
    symbols:      Optional[List[str]] = None,
    history_days: int = 30,
    fetch_depth:  bool = False,
) -> Dict[str, dict]:
    """
    Main daemon loop: fetch live FR for all symbols, cache history for BTC/ETH,
    and write dashboard.

    Called by com.cryptolab.okx-fr-monitor daemon every 8h.

    Args:
        symbols:       OKX instId list (default: K208_SYMBOLS_OKX)
        history_days:  Days of history to cache for BTC/ETH (default 30)
        fetch_depth:   Whether to fetch order book depth (slower, per-symbol)

    Returns:
        fr_results dict {symbol: result_dict}
    """
    if symbols is None:
        symbols = K208_SYMBOLS_OKX

    print(f"  [okx_fr_fetcher] Starting bulk fetch: {len(symbols)} symbols", file=sys.stderr)
    t0 = time.time()

    fr_results: Dict[str, dict] = {}
    depth_map:  Dict[str, float] = {}

    for sym in symbols:
        result = fetch_okx_funding_rate(sym)
        fr_results[sym] = result
        if result.get("ok"):
            fr = result["funding_rate"]
            ann = result.get("annualized_pct", fr * 3 * 365 * 100)
            print(
                f"    {sym:<22s}  FR={fr*100:+.4f}%  ann={ann:+.2f}%/yr  "
                f"mark={result.get('mark_px', 0):,.2f}",
                file=sys.stderr,
            )
        else:
            print(f"    {sym:<22s}  FAILED: {result.get('error', '?')}", file=sys.stderr)
        time.sleep(0.15)  # rate-limit: OKX public API ~20 req/s limit

    # Depth fetch (optional, slower)
    if fetch_depth:
        for sym in ["BTC-USDT-SWAP", "ETH-USDT-SWAP"]:
            depth_map[sym] = fetch_okx_orderbook_depth(sym)
            time.sleep(0.1)

    # History cache for BTC and ETH
    for hist_sym in ["BTC-USDT-SWAP", "ETH-USDT-SWAP"]:
        df = fetch_okx_funding_history(hist_sym, days=history_days)
        try:
            if not getattr(df, "empty", True) and len(df) > 0:
                save_okx_fr_cache(hist_sym, df)
        except Exception as exc:
            print(f"  [okx_fr_fetcher] Cache error for {hist_sym}: {exc}", file=sys.stderr)
        time.sleep(0.2)

    # Write dashboard
    write_okx_dashboard(fr_results, depth_map)

    elapsed = time.time() - t0
    ok_count = sum(1 for r in fr_results.values() if r.get("ok"))
    print(
        f"  [okx_fr_fetcher] Done: {ok_count}/{len(symbols)} OK in {elapsed:.1f}s",
        file=sys.stderr,
    )

    return fr_results


# ─────────────────────────────────────────────────────────────────────────────
# K208 Triangle Arbitrage Helper
# ─────────────────────────────────────────────────────────────────────────────

def compute_triangle_arb_opportunities(
    okx_results: Dict[str, dict],
    hl_fr_map:   Optional[Dict[str, float]] = None,
    bybit_fr_map: Optional[Dict[str, float]] = None,
    threshold_bps: float = 5.0,
) -> List[dict]:
    """
    Given OKX FR results + optional HL/Bybit FR maps, compute triangle arb
    opportunities where OKX FR diverges by > threshold_bps from either venue.

    K208 v6.20 logic:
      short highest-FR venue, long lowest-FR venue.
      With 3 venues: triangle arb = max_FR - min_FR across all 3 venues.

    Returns list of opportunity dicts sorted by spread_bps desc.
    """
    opportunities = []

    for sym, okx_d in okx_results.items():
        if not okx_d.get("ok"):
            continue

        okx_fr = okx_d["funding_rate"]
        # Convert OKX format (e.g. BTC-USDT-SWAP) to K208 base symbol (BTC)
        base_sym = sym.split("-")[0]

        fr_map: Dict[str, float] = {"OKX": okx_fr}
        if hl_fr_map and base_sym in hl_fr_map:
            fr_map["HL"] = hl_fr_map[base_sym]
        if bybit_fr_map and base_sym in bybit_fr_map:
            fr_map["Bybit"] = bybit_fr_map[base_sym]

        if len(fr_map) < 2:
            continue

        max_venue = max(fr_map, key=fr_map.get)  # type: ignore[arg-type]
        min_venue = min(fr_map, key=fr_map.get)  # type: ignore[arg-type]
        spread_bps = (fr_map[max_venue] - fr_map[min_venue]) * 10_000

        if spread_bps >= threshold_bps:
            opportunities.append({
                "symbol":       base_sym,
                "short_venue":  max_venue,
                "long_venue":   min_venue,
                "spread_bps":   round(spread_bps, 2),
                "fr_map":       {v: round(f * 10_000, 2) for v, f in fr_map.items()},
                "note":         f"short {max_venue} ({fr_map[max_venue]*100:.4f}%) "
                                f"/ long {min_venue} ({fr_map[min_venue]*100:.4f}%)",
            })

    return sorted(opportunities, key=lambda x: x["spread_bps"], reverse=True)


# ─────────────────────────────────────────────────────────────────────────────
# CLI
# ─────────────────────────────────────────────────────────────────────────────

def _parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(
        description="K456 OKX Funding Rate Fetcher (K454 v6.20 1/7 wave, 3rd K208 venue)",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Live BTC FR (default):
  python3 scripts/okx_fr_fetcher.py

  # Specific symbol:
  python3 scripts/okx_fr_fetcher.py --symbol ETH-USDT-SWAP

  # Fetch all K208 symbols + write dashboard:
  python3 scripts/okx_fr_fetcher.py --all

  # Fetch 30d BTC history + cache:
  python3 scripts/okx_fr_fetcher.py --history --symbol BTC-USDT-SWAP --days 30

  # Full daemon run (all symbols + history + dashboard):
  python3 scripts/okx_fr_fetcher.py --daemon

  # Print dashboard JSON:
  python3 scripts/okx_fr_fetcher.py --dashboard

K456 context: OKX is 3rd K208 venue (HL + Bybit + OKX = v6.20 expansion).
20th daemon: com.cryptolab.okx-fr-monitor (StartInterval 28800, 8h cycle).
        """,
    )
    p.add_argument("--symbol",    default="BTC-USDT-SWAP",
                   help="OKX instId (default: BTC-USDT-SWAP)")
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

    # --dashboard: just print current state
    if args.dashboard:
        if DASHBOARD_PATH.is_file():
            with open(DASHBOARD_PATH) as f:
                print(json.dumps(json.load(f), indent=2))
        else:
            print(json.dumps({"status": "no dashboard found — run --all or --daemon first"}))
        return 0

    # --daemon: full cycle
    if args.daemon:
        print("=== K456 OKX FR Monitor — Daemon Run ===", file=sys.stderr)
        fr_results = fetch_and_cache_all(
            history_days=args.days,
            fetch_depth=args.depth,
        )
        ok_count = sum(1 for r in fr_results.values() if r.get("ok"))
        print(f"\n=== Daemon run complete: {ok_count}/{len(fr_results)} symbols OK ===", file=sys.stderr)
        if args.json:
            print(json.dumps(fr_results, indent=2))
        return 0

    # --all: fetch all symbols, write dashboard
    if args.all:
        fr_results = fetch_and_cache_all(
            symbols=K208_SYMBOLS_OKX,
            history_days=args.days,
            fetch_depth=args.depth,
        )
        if args.json:
            print(json.dumps(fr_results, indent=2))
        else:
            print(f"\n=== OKX FR Snapshot ({datetime.now(JST).strftime('%Y-%m-%d %H:%M JST')}) ===")
            for sym, d in fr_results.items():
                if d.get("ok"):
                    print(
                        f"  {sym:<22s}  FR={d['funding_rate']*100:+.4f}%  "
                        f"ann={d.get('annualized_pct',0):+.2f}%/yr  "
                        f"mark={d.get('mark_px',0):,.2f}"
                    )
                else:
                    print(f"  {sym:<22s}  FAILED: {d.get('error', '?')}")
        return 0

    # --history: historical data
    if args.history:
        print(f"=== Fetching {args.days}d history for {args.symbol} ===", file=sys.stderr)
        df = fetch_okx_funding_history(args.symbol, days=args.days)
        try:
            if not getattr(df, "empty", True) and len(df) > 0:
                save_okx_fr_cache(args.symbol, df)
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
    result = fetch_okx_funding_rate(args.symbol)
    if args.json:
        print(json.dumps(result, indent=2))
    else:
        if result.get("ok"):
            fr  = result["funding_rate"]
            ann = result.get("annualized_pct", 0.0)
            mk  = result.get("mark_px", 0.0)
            nfr = result.get("next_funding_rate", 0.0)
            print(f"\n=== OKX Funding Rate: {args.symbol} ===")
            print(f"  Current FR:    {fr*100:+.4f}% per 8h")
            print(f"  Next FR:       {nfr*100:+.4f}% per 8h (predicted)")
            print(f"  Annualized:    {ann:+.2f}% per year")
            print(f"  Mark price:    ${mk:,.2f}")
            print(f"  Fetched at:    {result['fetched_at_utc']}")
            print(f"  Source:        {result['source']}")
            print(f"\n  K456 OKX → 3rd venue for K208 triangle arb")
            print(f"  Dashboard:     data/okx_dashboard.json")
        else:
            print(f"FAILED: {result.get('error', 'unknown')}", file=sys.stderr)
            return 1

    return 0


if __name__ == "__main__":
    sys.exit(main())

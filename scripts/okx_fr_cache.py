#!/usr/bin/env python3
"""
okx_fr_cache.py — K745 OKX Funding Rate Cache Layer
=====================================================
Manages OKX FR data as Parquet files matching the k208_*.parquet schema used by
HL and Bybit cache files. Provides uniform venue interface for downstream strategies.

Architecture:
  OKXFRCache     — main cache manager class
  backfill()     — fetch last N days of history and write Parquet
  update()       — incremental update (last settlement window)
  load()         — read cached data as DataFrame
  venue_snapshot() — uniform dict {symbol: fr_float} for smart_router.py integration
  write_venue_state() — write data/okx_venue_state.json (smart_router compatible)

Parquet schema (matches k208_*.parquet / HL / Bybit cache schema):
  fundingTime   (datetime64[ns, UTC]) — settlement timestamp
  fundingRate   (float64)             — realized rate, fractional per 8h
  realizedRate  (float64)             — alias for fundingRate (OKX returns both)
  symbol        (str)                 — OKX instId format: "BTC-USDT-SWAP"
  venue         (str)                 — always "OKX"
  annualized_pct (float64)           — FR × 3 × 365 × 100

Cache files:
  cache/okx_fr_{BASE}_USDT_SWAP.parquet — e.g. cache/okx_fr_BTC_USDT_SWAP.parquet
  data/okx_venue_state.json             — current live FR snapshot (smart_router format)
  data/okx_fr_cache_manifest.json       — cache metadata (last update, rows, coverage)

K339 Security: REPO_ROOT from __file__, no /Users/ literals.
K745 context: cache layer feeds into multi_venue_router.py OKX registration.

Usage:
  python3 scripts/okx_fr_cache.py --backfill --days 30           # initial 30d backfill
  python3 scripts/okx_fr_cache.py --update                       # incremental update
  python3 scripts/okx_fr_cache.py --symbol BTC-USDT-SWAP --load  # read cached data
  python3 scripts/okx_fr_cache.py --venue-state                  # write venue state JSON
  python3 scripts/okx_fr_cache.py --manifest                     # show cache manifest
"""
from __future__ import annotations

import argparse
import json
import sys
import time
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Tuple

# ── K339 canonical paths ──────────────────────────────────────────────────────
REPO_ROOT = Path(__file__).resolve().parent.parent
CACHE_DIR = REPO_ROOT / "cache"
DATA_DIR  = REPO_ROOT / "data"
LOGS_DIR  = REPO_ROOT / "logs"

CACHE_DIR.mkdir(exist_ok=True)
DATA_DIR.mkdir(exist_ok=True)
LOGS_DIR.mkdir(exist_ok=True)

JST = timezone(timedelta(hours=9))

# ── OKX K208 symbol universe ──────────────────────────────────────────────────
K208_OKX_SYMBOLS = [
    "BTC-USDT-SWAP", "ETH-USDT-SWAP", "SOL-USDT-SWAP", "XRP-USDT-SWAP",
    "SUI-USDT-SWAP",  "OP-USDT-SWAP",  "APT-USDT-SWAP", "AXS-USDT-SWAP",
    "JTO-USDT-SWAP",  "IMX-USDT-SWAP", "ATOM-USDT-SWAP","INJ-USDT-SWAP",
    "AVAX-USDT-SWAP", "SEI-USDT-SWAP", "TIA-USDT-SWAP", "LINK-USDT-SWAP",
    "DOT-USDT-SWAP",  "NEAR-USDT-SWAP","ENA-USDT-SWAP", "HBAR-USDT-SWAP",
]

# Priority symbols for initial backfill (K208 main + paired-trade family)
PRIORITY_SYMBOLS = [
    "BTC-USDT-SWAP", "ETH-USDT-SWAP", "SOL-USDT-SWAP", "INJ-USDT-SWAP",
    "ATOM-USDT-SWAP", "TIA-USDT-SWAP", "APT-USDT-SWAP", "SEI-USDT-SWAP",
    "AVAX-USDT-SWAP", "ENA-USDT-SWAP",
]

# Cache file naming
MANIFEST_PATH    = DATA_DIR / "okx_fr_cache_manifest.json"
VENUE_STATE_PATH = DATA_DIR / "okx_venue_state.json"

# OKX FR cycle: 8h (3 settlements per day)
FR_PERIOD_HOURS = 8
FR_PER_DAY      = 24 // FR_PERIOD_HOURS   # = 3


def _sym_to_filename(symbol: str) -> str:
    """Convert OKX instId to safe filename: BTC-USDT-SWAP → okx_fr_BTC_USDT_SWAP"""
    return "okx_fr_" + symbol.replace("-", "_")


def _cache_path(symbol: str) -> Path:
    return CACHE_DIR / (_sym_to_filename(symbol) + ".parquet")


# ─────────────────────────────────────────────────────────────────────────────
# OKX History fetcher (uses okx_client.py)
# ─────────────────────────────────────────────────────────────────────────────

def _fetch_history_records(
    symbol: str,
    days:   int = 30,
    client=None,
) -> List[dict]:
    """
    Fetch historical FR records from OKX API.
    Paginates to cover the requested number of days.
    Returns list of raw OKX record dicts.
    """
    try:
        if client is None:
            from scripts.okx_client import OKXClient
            client = OKXClient()
    except ImportError:
        # Fallback: direct urllib call (if running standalone without package install)
        import urllib.request
        client = _SimpleOKXFetcher()

    records: List[dict] = []
    cutoff_ms = int((datetime.now(timezone.utc) - timedelta(days=days)).timestamp() * 1000)
    limit     = 100
    after_ms: Optional[int] = None   # pagination cursor
    max_pages = (days * FR_PER_DAY // limit) + 2   # safety ceiling

    for page in range(max_pages):
        page_records = client.get_funding_rate_history(
            symbol, limit=limit,
            after=after_ms,
        )
        if not page_records:
            break

        for rec in page_records:
            try:
                ts_ms = int(rec.get("fundingTime", 0))
                if ts_ms < cutoff_ms:
                    continue
                records.append(rec)
            except (TypeError, ValueError):
                continue

        # Pagination: after = oldest fundingTime in this page
        if page_records:
            oldest_ts = min(int(r.get("fundingTime", 0)) for r in page_records)
            if oldest_ts <= cutoff_ms:
                break   # covered the full window
            after_ms = oldest_ts
            time.sleep(0.15)
        else:
            break

    print(f"  [okx_fr_cache] {symbol}: fetched {len(records)} records ({days}d window)", file=sys.stderr)
    return records


def _records_to_dataframe(records: List[dict], symbol: str):
    """Convert raw OKX FR history records to DataFrame with k208 schema."""
    try:
        import pandas as pd
    except ImportError:
        print("  [okx_fr_cache] pandas required: pip install pandas pyarrow", file=sys.stderr)
        return None

    rows = []
    for rec in records:
        try:
            ts_ms    = int(rec.get("fundingTime", 0))
            fr       = float(rec.get("fundingRate", 0.0) or 0.0)
            realized = float(rec.get("realizedRate", fr) or fr)
            rows.append({
                "fundingTime":  pd.Timestamp(ts_ms, unit="ms", tz="UTC"),
                "fundingRate":  fr,
                "realizedRate": realized,
                "symbol":       symbol,
                "venue":        "OKX",
                "annualized_pct": round(fr * 3 * 365 * 100, 4),
            })
        except (TypeError, ValueError, KeyError):
            continue

    if not rows:
        return pd.DataFrame()

    df = pd.DataFrame(rows).sort_values("fundingTime").reset_index(drop=True)
    return df


class _SimpleOKXFetcher:
    """
    Fallback FR history fetcher using only stdlib urllib.
    Used when scripts.okx_client is not importable (standalone execution).
    """
    BASE = "https://www.okx.com"
    EP   = "/api/v5/public/funding-rate-history"

    def get_funding_rate_history(
        self,
        symbol: str,
        limit:  int = 100,
        after:  Optional[int] = None,
        before: Optional[int] = None,
    ) -> List[dict]:
        import urllib.request, urllib.parse, json as _json
        params = {"instId": symbol, "limit": str(min(limit, 100))}
        if after  is not None: params["after"]  = str(after)
        if before is not None: params["before"] = str(before)
        url = self.BASE + self.EP + "?" + urllib.parse.urlencode(params)
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "crypto-lab-okx-fr-cache/1.0"})
            with urllib.request.urlopen(req, timeout=15) as resp:
                raw = _json.loads(resp.read())
                if raw.get("code") == "0":
                    return raw.get("data", [])
        except Exception as exc:
            print(f"  [_SimpleOKXFetcher] {exc}", file=sys.stderr)
        return []


# ─────────────────────────────────────────────────────────────────────────────
# OKX FR Cache Manager
# ─────────────────────────────────────────────────────────────────────────────

class OKXFRCache:
    """
    Manages OKX funding rate cache as Parquet files.

    Schema matches HL/Bybit Parquet convention used in k208_*.parquet files:
      fundingTime    datetime64[ns, UTC]
      fundingRate    float64
      realizedRate   float64
      symbol         str (OKX instId format)
      venue          str ("OKX")
      annualized_pct float64

    This enables uniform multi-venue DataFrame operations in downstream analysis.
    """

    def __init__(self, client=None):
        self._client = client   # OKXClient or None (will lazy-create)

    def _get_client(self):
        if self._client is None:
            try:
                from scripts.okx_client import OKXClient
                self._client = OKXClient()
            except ImportError:
                self._client = _SimpleOKXFetcher()
        return self._client

    # ── Backfill ──────────────────────────────────────────────────────────────

    def backfill(
        self,
        symbol: str,
        days:   int = 30,
    ) -> Tuple[int, Path]:
        """
        Fetch last `days` days of FR history for `symbol` and write to Parquet.
        Returns (rows_written, cache_path).

        Safe to call on existing cache: will merge (dedup by fundingTime).
        """
        try:
            import pandas as pd
        except ImportError:
            print("  [OKXFRCache] pandas/pyarrow required for Parquet I/O", file=sys.stderr)
            return 0, _cache_path(symbol)

        client  = self._get_client()
        records = _fetch_history_records(symbol, days, client)
        if not records:
            print(f"  [OKXFRCache] No records for {symbol}", file=sys.stderr)
            return 0, _cache_path(symbol)

        df_new = _records_to_dataframe(records, symbol)
        if df_new is None or df_new.empty:
            return 0, _cache_path(symbol)

        # Merge with existing cache (dedup by fundingTime)
        path = _cache_path(symbol)
        if path.exists():
            try:
                df_old = pd.read_parquet(path)
                df = pd.concat([df_old, df_new], ignore_index=True)
                df = df.drop_duplicates(subset=["fundingTime"]).sort_values("fundingTime").reset_index(drop=True)
            except Exception as exc:
                print(f"  [OKXFRCache] Cache merge failed ({exc}), overwriting", file=sys.stderr)
                df = df_new
        else:
            df = df_new

        _write_parquet(df, path)
        self._update_manifest(symbol, len(df), df["fundingTime"].min(), df["fundingTime"].max())
        return len(df), path

    def backfill_all(
        self,
        symbols: Optional[List[str]] = None,
        days:    int = 30,
    ) -> Dict[str, Tuple[int, Path]]:
        """Backfill all symbols (default: PRIORITY_SYMBOLS for speed)."""
        if symbols is None:
            symbols = PRIORITY_SYMBOLS
        results = {}
        for sym in symbols:
            rows, path = self.backfill(sym, days)
            results[sym] = (rows, path)
            time.sleep(0.5)   # conservative rate limiting
        return results

    # ── Incremental update ────────────────────────────────────────────────────

    def update(self, symbol: str) -> Tuple[int, int]:
        """
        Incremental update: fetch settlements since last cached record.
        Returns (new_rows_added, total_rows).

        Logic: reads last fundingTime from cache → fetches history since that time.
        Safe to run every 8h (matches OKX settlement cycle).
        """
        try:
            import pandas as pd
        except ImportError:
            return 0, 0

        path = _cache_path(symbol)
        last_ts_ms: Optional[int] = None

        if path.exists():
            try:
                df_old = pd.read_parquet(path)
                if not df_old.empty:
                    last_ts_ms = int(df_old["fundingTime"].max().timestamp() * 1000)
            except Exception:
                pass

        if last_ts_ms is None:
            # No cache exists — run full 30d backfill
            rows, _ = self.backfill(symbol, days=30)
            return rows, rows

        # Fetch only new records (fundingTime > last_ts_ms)
        client  = self._get_client()
        records = _fetch_history_records(symbol, days=2, client=client)  # last 2 days to catch any missed

        new_records = [
            r for r in records
            if int(r.get("fundingTime", 0)) > last_ts_ms
        ]

        if not new_records:
            print(f"  [OKXFRCache] {symbol}: no new records since last update", file=sys.stderr)
            df_old = pd.read_parquet(path)
            return 0, len(df_old)

        df_new = _records_to_dataframe(new_records, symbol)
        df_old = pd.read_parquet(path) if path.exists() else pd.DataFrame()

        df = pd.concat([df_old, df_new], ignore_index=True)
        df = df.drop_duplicates(subset=["fundingTime"]).sort_values("fundingTime").reset_index(drop=True)
        _write_parquet(df, path)

        self._update_manifest(symbol, len(df), df["fundingTime"].min(), df["fundingTime"].max())
        print(f"  [OKXFRCache] {symbol}: +{len(new_records)} new records → {len(df)} total", file=sys.stderr)
        return len(new_records), len(df)

    # ── Load ──────────────────────────────────────────────────────────────────

    def load(self, symbol: str, days: Optional[int] = None):
        """
        Load cached FR history for a symbol. Returns pandas DataFrame or None.
        If days is specified, returns only the last N days.
        """
        try:
            import pandas as pd
        except ImportError:
            print("  [OKXFRCache] pandas required", file=sys.stderr)
            return None

        path = _cache_path(symbol)
        if not path.exists():
            print(f"  [OKXFRCache] Cache not found: {path.name}", file=sys.stderr)
            return None

        try:
            df = pd.read_parquet(path)
            if days is not None:
                cutoff = datetime.now(timezone.utc) - timedelta(days=days)
                cutoff_ts = pd.Timestamp(cutoff)
                df = df[df["fundingTime"] >= cutoff_ts].reset_index(drop=True)
            return df
        except Exception as exc:
            print(f"  [OKXFRCache] Load error: {exc}", file=sys.stderr)
            return None

    def load_multi(
        self,
        symbols: Optional[List[str]] = None,
        days:    Optional[int] = None,
    ):
        """
        Load cached data for multiple symbols. Returns combined DataFrame with all venues
        for multi-venue analysis. Compatible with k208_*.parquet schema.
        """
        try:
            import pandas as pd
        except ImportError:
            return None

        if symbols is None:
            symbols = PRIORITY_SYMBOLS

        dfs = []
        for sym in symbols:
            df = self.load(sym, days=days)
            if df is not None and not df.empty:
                dfs.append(df)

        if not dfs:
            return pd.DataFrame()

        combined = pd.concat(dfs, ignore_index=True).sort_values(
            ["symbol", "fundingTime"]
        ).reset_index(drop=True)
        return combined

    # ── Venue state snapshot ──────────────────────────────────────────────────

    def live_venue_state(
        self,
        symbols: Optional[List[str]] = None,
        include_depth: bool = False,
    ) -> Dict[str, dict]:
        """
        Fetch live FR snapshot for all symbols.
        Returns dict in smart_router.py compatible format:
          {base_symbol: {"fr": float, "mark_px": float, "depth_usd": float, "source": str}}

        base_symbol is extracted from OKX instId: "BTC-USDT-SWAP" → "BTC"
        """
        if symbols is None:
            symbols = K208_OKX_SYMBOLS

        try:
            from scripts.okx_client import OKXClient
            client = OKXClient()
        except ImportError:
            client = _SimpleOKXFetcher()
            # Minimal live state using simple fetcher
            return {}

        result: Dict[str, dict] = {}
        for sym in symbols:
            try:
                snap = client.get_funding_rate(sym)
                if snap.ok:
                    base = sym.split("-")[0]
                    depth = client.get_orderbook_depth_usd(sym) if include_depth else 2_000_000.0
                    result[base] = {
                        "fr":        snap.funding_rate,
                        "mark_px":   snap.mark_px,
                        "depth_usd": depth,
                        "source":    "OKX_v5_live",
                        "inst_id":   sym,
                        "annualized_pct": snap.annualized_pct,
                    }
                time.sleep(0.15)
            except Exception as exc:
                print(f"  [OKXFRCache] live_venue_state error for {sym}: {exc}", file=sys.stderr)

        return result

    def write_venue_state(
        self,
        symbols:       Optional[List[str]] = None,
        include_depth: bool = False,
    ) -> Path:
        """
        Fetch live FR snapshot and write to data/okx_venue_state.json.
        Compatible with smart_router.py venue_state format.
        Returns path to written file.
        """
        now_utc = datetime.now(timezone.utc)
        now_jst = now_utc.astimezone(JST)

        state = self.live_venue_state(symbols, include_depth)

        payload = {
            "_wave":          "K745",
            "_source":        "okx_fr_cache.py",
            "last_poll_utc":  now_utc.isoformat(),
            "last_poll_jst":  now_jst.strftime("%Y-%m-%d %H:%M JST"),
            "venue":          "OKX",
            "symbols_fetched": len(state),
            "state":          state,
        }

        tmp = VENUE_STATE_PATH.with_suffix(".tmp")
        with open(tmp, "w") as f:
            json.dump(payload, f, indent=2)
        tmp.replace(VENUE_STATE_PATH)
        print(f"  [OKXFRCache] Venue state written: {VENUE_STATE_PATH.name} ({len(state)} symbols)", file=sys.stderr)
        return VENUE_STATE_PATH

    # ── Manifest ──────────────────────────────────────────────────────────────

    def _update_manifest(self, symbol: str, rows: int, min_ts, max_ts) -> None:
        """Update cache manifest with latest stats for symbol."""
        manifest = {}
        if MANIFEST_PATH.exists():
            try:
                with open(MANIFEST_PATH) as f:
                    manifest = json.load(f)
            except Exception:
                pass

        manifest[symbol] = {
            "rows":        rows,
            "min_ts":      str(min_ts),
            "max_ts":      str(max_ts),
            "updated_jst": datetime.now(JST).strftime("%Y-%m-%d %H:%M JST"),
            "path":        _sym_to_filename(symbol) + ".parquet",
        }

        tmp = MANIFEST_PATH.with_suffix(".tmp")
        with open(tmp, "w") as f:
            json.dump(manifest, f, indent=2)
        tmp.replace(MANIFEST_PATH)

    def show_manifest(self) -> dict:
        """Load and display cache manifest."""
        if not MANIFEST_PATH.exists():
            print("  [OKXFRCache] No manifest found — run --backfill first", file=sys.stderr)
            return {}
        with open(MANIFEST_PATH) as f:
            manifest = json.load(f)
        print(f"\n=== OKX FR Cache Manifest ({MANIFEST_PATH.name}) ===")
        for sym, info in sorted(manifest.items()):
            print(f"  {sym:<22}  rows={info['rows']:<6}  {info['min_ts'][:10]} → {info['max_ts'][:10]}  updated={info['updated_jst']}")
        return manifest

    # ── Comparison helpers ────────────────────────────────────────────────────

    def compare_with_hl(
        self,
        symbol: str,
        hl_cache_pattern: str = "hl_fr_{base}.parquet",
        days:   int = 30,
    ):
        """
        Load OKX + HL cached FR data for a symbol and return merged DataFrame.
        Enables cross-venue FR spread analysis.

        hl_cache_pattern: pattern for HL Parquet file in cache/ (base = e.g. "BTC")
        Returns merged DataFrame with columns: fundingTime, fr_okx, fr_hl, spread_bps
        """
        try:
            import pandas as pd
        except ImportError:
            return None

        base = symbol.split("-")[0]
        hl_path = CACHE_DIR / hl_cache_pattern.format(base=base)

        df_okx = self.load(symbol, days=days)
        if df_okx is None or df_okx.empty:
            print(f"  [compare] No OKX cache for {symbol}", file=sys.stderr)
            return None

        if not hl_path.exists():
            print(f"  [compare] No HL cache at {hl_path.name}", file=sys.stderr)
            return df_okx.rename(columns={"fundingRate": "fr_okx"})

        try:
            df_hl = pd.read_parquet(hl_path)
        except Exception as exc:
            print(f"  [compare] HL cache load error: {exc}", file=sys.stderr)
            return None

        # Merge on fundingTime (nearest match ±1h tolerance for 8h cycle alignment)
        df_okx_s = df_okx[["fundingTime", "fundingRate"]].rename(columns={"fundingRate": "fr_okx"})
        df_hl_s  = df_hl[["fundingTime", "fundingRate"]].rename(columns={"fundingRate": "fr_hl"})

        merged = pd.merge_asof(
            df_okx_s.sort_values("fundingTime"),
            df_hl_s.sort_values("fundingTime"),
            on="fundingTime",
            tolerance=pd.Timedelta("1h"),
            direction="nearest",
        ).dropna()

        merged["spread_bps"] = (merged["fr_okx"] - merged["fr_hl"]) * 10_000
        return merged


# ── Parquet I/O helper ─────────────────────────────────────────────────────────

def _write_parquet(df, path: Path) -> None:
    """Write DataFrame to Parquet with atomic rename."""
    try:
        tmp = path.with_suffix(".tmp.parquet")
        df.to_parquet(tmp, index=False)
        tmp.replace(path)
        print(f"  [okx_fr_cache] Written: {path.name} ({len(df)} rows)", file=sys.stderr)
    except Exception as exc:
        print(f"  [okx_fr_cache] Write error: {exc}", file=sys.stderr)


# ── CLI ───────────────────────────────────────────────────────────────────────

def main() -> int:
    p = argparse.ArgumentParser(
        description="K745 OKX FR Cache — Parquet cache management for K208 venue integration",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Initial 30d backfill (priority symbols: BTC,ETH,SOL,INJ,ATOM,TIA,APT,SEI,AVAX,ENA)
  python3 scripts/okx_fr_cache.py --backfill

  # Backfill specific symbol:
  python3 scripts/okx_fr_cache.py --backfill --symbol INJ-USDT-SWAP --days 60

  # Incremental update (run every 8h via daemon):
  python3 scripts/okx_fr_cache.py --update

  # Load and inspect cache:
  python3 scripts/okx_fr_cache.py --load --symbol BTC-USDT-SWAP

  # Write live venue state (for smart_router.py integration):
  python3 scripts/okx_fr_cache.py --venue-state

  # Show cache manifest:
  python3 scripts/okx_fr_cache.py --manifest

  # Compare OKX vs HL FR spread:
  python3 scripts/okx_fr_cache.py --compare --symbol BTC-USDT-SWAP

K745: OKX cache feeds multi_venue_router.py for HL cap relief ($4.5M unlock).
        """,
    )
    p.add_argument("--backfill",    action="store_true", help="Fetch historical data (30d default)")
    p.add_argument("--update",      action="store_true", help="Incremental update (new settlements only)")
    p.add_argument("--load",        action="store_true", help="Load and display cached data")
    p.add_argument("--venue-state", action="store_true", help="Fetch live FR + write okx_venue_state.json")
    p.add_argument("--manifest",    action="store_true", help="Show cache manifest")
    p.add_argument("--compare",     action="store_true", help="Compare OKX vs HL FR spread")
    p.add_argument("--symbol",      default=None,        help="OKX instId (default: all priority symbols)")
    p.add_argument("--days",        type=int, default=30, help="Days of history (backfill only)")
    p.add_argument("--all",         action="store_true", help="Use all K208_OKX_SYMBOLS (not just priority)")
    p.add_argument("--json",        action="store_true", help="Output JSON")
    args = p.parse_args()

    cache = OKXFRCache()

    if args.manifest:
        manifest = cache.show_manifest()
        if args.json:
            print(json.dumps(manifest, indent=2))
        return 0

    if args.venue_state:
        syms = K208_OKX_SYMBOLS if args.all else ([args.symbol] if args.symbol else None)
        path = cache.write_venue_state(symbols=syms)
        if args.json:
            with open(path) as f:
                print(f.read())
        return 0

    if args.backfill:
        if args.symbol:
            rows, path = cache.backfill(args.symbol, days=args.days)
            print(f"  Backfill {args.symbol}: {rows} rows → {path.name}")
        else:
            syms = K208_OKX_SYMBOLS if args.all else PRIORITY_SYMBOLS
            print(f"  Backfilling {len(syms)} symbols ({args.days}d) ...")
            results = cache.backfill_all(syms, days=args.days)
            total_rows = sum(r[0] for r in results.values())
            print(f"\n  Done: {total_rows} total rows across {len(results)} symbols")
            if args.json:
                print(json.dumps({s: {"rows": r[0], "path": str(r[1].name)} for s, r in results.items()}, indent=2))
        return 0

    if args.update:
        syms = [args.symbol] if args.symbol else PRIORITY_SYMBOLS
        total_new, total_rows = 0, 0
        for sym in syms:
            new, tot = cache.update(sym)
            total_new  += new
            total_rows += tot
        print(f"  Update complete: +{total_new} new rows, {total_rows} total rows")
        return 0

    if args.load:
        sym = args.symbol or "BTC-USDT-SWAP"
        df  = cache.load(sym, days=args.days if args.days else None)
        if df is None or df.empty:
            print(f"  No data for {sym}")
            return 1
        if args.json:
            print(df.to_json(orient="records", date_format="iso"))
        else:
            print(f"\n=== OKX FR Cache: {sym} ({len(df)} records) ===")
            print(df.tail(10).to_string())
            print(f"\n  Time range: {df['fundingTime'].min()} → {df['fundingTime'].max()}")
            print(f"  Mean FR: {df['fundingRate'].mean()*100:.4f}% / std: {df['fundingRate'].std()*100:.4f}%")
            print(f"  Annualized mean: {df['annualized_pct'].mean():.2f}%/yr")
        return 0

    if args.compare:
        sym = args.symbol or "BTC-USDT-SWAP"
        merged = cache.compare_with_hl(sym, days=args.days)
        if merged is None or merged.empty:
            print(f"  No comparison data for {sym}")
            return 1
        if args.json:
            print(merged.to_json(orient="records", date_format="iso"))
        else:
            print(f"\n=== OKX vs HL FR Spread: {sym} ===")
            print(merged[["fundingTime", "fr_okx", "fr_hl", "spread_bps"]].tail(20).to_string())
            if "spread_bps" in merged.columns:
                print(f"\n  Mean spread OKX-HL: {merged['spread_bps'].mean():.2f} bps")
                print(f"  Std spread:         {merged['spread_bps'].std():.2f} bps")
        return 0

    # Default: show manifest + hint
    print("K745 OKX FR Cache — run with --help for usage")
    cache.show_manifest()
    return 0


if __name__ == "__main__":
    sys.exit(main())

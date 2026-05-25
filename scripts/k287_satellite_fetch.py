"""
k287_satellite_fetch.py — K287d Satellite Live Data Fetcher
============================================================
Fetches all data required for the K287d satellite paper-trade daemon.

K287d Satellite = K270 (35.5% / 7.1% portfolio) + K275 (64.5% / 12.9% portfolio)
  K270: dYdX v4 Cosmos perp DEX — 14d FR rank, 30 symbols
  K275: OKX perp exchange      — 7d FR rank,  35 symbols

Compared to K280 (main daemon):
  - K280 uses Bybit/HL (K208 majors) + HL 20-symbol longtail (K276b)
  - K287d Satellite uses dYdX v4 and OKX — entirely different exchanges
  - Run at 09:30 JST (30 min after K280 at 09:00 JST) to avoid API conflicts

Data flow:
  K270: incremental refresh of cache/k270_dydx/dydx_fr_{SYM}.parquet
        → aggregate to daily panel → cache/k270_dydx_daily.parquet
  K275: incremental refresh of cache/okx_fr_{SYM}.parquet
        → aggregate/update cache/okx_fr_daily.parquet
  Snapshot: cache/k287_satellite_{YYYYMMDD}.parquet

Usage:
  python3 scripts/k287_satellite_fetch.py
  python3 scripts/k287_satellite_fetch.py --date 2026-05-25
  python3 scripts/k287_satellite_fetch.py --force   # re-fetch even if cached today
"""
from __future__ import annotations

import argparse
import json
import math
import time
import urllib.request
import urllib.error
import warnings
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Optional

import numpy as np
import pandas as pd

warnings.filterwarnings("ignore")

# ── Paths ──────────────────────────────────────────────────────────────────────
BASE       = Path("/Users/nekonaomichi/crypto-lab")
CACHE      = BASE / "cache"
DYDX_CACHE = CACHE / "k270_dydx"
LOGS       = BASE / "logs"
DYDX_CACHE.mkdir(parents=True, exist_ok=True)
LOGS.mkdir(exist_ok=True)

# ── K270 dYdX v4 universe (30 symbols per K270 spec) ───────────────────────────
K270_SYMBOLS = [
    "AAVE", "ADA",  "APT",  "ARB",  "ATOM",
    "AVAX", "AXS",  "BLUR", "BONK", "CRV",
    "DOGE", "DOT",  "ENA",  "INJ",  "JUP",
    "LDO",  "NEAR", "OP",   "PEPE", "PYTH",
    "SEI",  "SOL",  "SUI",  "TAO",  "TIA",
    "UNI",  "WIF",  "WLD",  "XRP",  "BNB",
]

# ── K275 OKX universe (35 symbols per K275 spec, K208 majors excluded) ─────────
K275_SYMBOLS = [
    "DOGE", "AVAX", "LINK", "ARB",  "NEAR", "DOT",  "ATOM",
    "BNB",  "LTC",  "UNI",  "AAVE", "INJ",  "TIA",  "SEI",
    "STRK", "WLD",  "ENA",  "BLUR", "BONK", "PEPE", "WIF",
    "PYTH", "JUP",  "BOME", "ONDO", "CRV",  "SUSHI","MEME",
    "SHIB", "TAO",  "DYDX", "FIL",  "GRT",  "SNX",  "COMP",
]

# ── dYdX v4 API ───────────────────────────────────────────────────────────────
DYDX_API_BASE = "https://indexer.dydx.trade/v4/historicalFunding"

# ── OKX API ───────────────────────────────────────────────────────────────────
OKX_FR_URL = "https://www.okx.com/api/v5/public/funding-rate-history"


# ─────────────────────────────────────────────────────────────────────────────
# 1. dYdX v4 Helpers (K270)
# ─────────────────────────────────────────────────────────────────────────────

def sym_to_dydx_market(sym: str) -> str:
    """Convert symbol to dYdX v4 market format: SYM-USD."""
    return f"{sym}-USD"


def fetch_dydx_fr_page(market: str, before_ts: Optional[str] = None) -> List[Dict]:
    """
    Fetch one page of dYdX v4 historical funding rates.
    dYdX API: GET /v4/historicalFunding/{market}?limit=100&effectiveBeforeOrAt={iso_ts}
    Returns list of records (newest first).
    """
    url = f"{DYDX_API_BASE}/{market}?limit=100"
    if before_ts:
        url += f"&effectiveBeforeOrAt={before_ts}"
    req = urllib.request.Request(
        url, headers={"User-Agent": "Mozilla/5.0", "Accept": "application/json"}
    )
    for attempt in range(3):
        try:
            with urllib.request.urlopen(req, timeout=20) as resp:
                data = json.loads(resp.read().decode())
                return data.get("historicalFunding", [])
        except urllib.error.HTTPError as e:
            if e.code == 429:
                wait = 15 * (attempt + 1)
                print(f"    429 rate-limit {market}, waiting {wait}s...")
                time.sleep(wait)
                continue
            print(f"    HTTP {e.code} {market}")
            return []
        except Exception as ex:
            print(f"    err {market}: {ex}")
            if attempt < 2:
                time.sleep(5)
    return []


def fetch_dydx_fr_incremental(sym: str, lookback_hours: int = 72) -> pd.DataFrame:
    """
    Incrementally fetch recent dYdX FR for one symbol.
    Uses existing cache to determine how far back to fetch (max lookback_hours).
    Returns DataFrame with columns [timestamp, dydx_fr] indexed 0..N.
    """
    market     = sym_to_dydx_market(sym)
    cache_path = DYDX_CACHE / f"dydx_fr_{sym}.parquet"

    # Determine starting point
    if cache_path.exists():
        existing = pd.read_parquet(cache_path)
        if "timestamp" not in existing.columns and existing.index.name != "timestamp":
            existing = existing.reset_index()
        last_ts = pd.to_datetime(existing["timestamp"]).max()
        # Fetch from last_ts back to fill gap (add buffer)
        before_ts = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.000Z")
        cutoff_ts = last_ts
        print(f"    {sym}: cache exists up to {last_ts.date()}, fetching incrementally")
    else:
        existing  = pd.DataFrame()
        before_ts = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.000Z")
        cutoff_ts = pd.Timestamp("2020-01-01")
        print(f"    {sym}: no cache, fetching full history")

    # Paginate backwards
    all_records: List[Dict] = []
    done = False

    for page in range(50):  # max 50 pages = 5000 events (~200d at hourly)
        records = fetch_dydx_fr_page(market, before_ts=before_ts)
        if not records:
            break

        for r in records:
            ts_str = r.get("effectiveAt", r.get("createdAt", ""))
            try:
                ts = pd.Timestamp(ts_str).tz_localize(None) if "+" not in ts_str \
                     else pd.Timestamp(ts_str).tz_convert(None)
            except Exception:
                continue
            if ts <= cutoff_ts:
                done = True
                break
            fr = float(r.get("rate", 0.0))
            all_records.append({"timestamp": ts, "dydx_fr": fr})

        if done or len(records) < 100:
            break

        # Move pointer to oldest record in this page
        oldest_str = records[-1].get("effectiveAt", records[-1].get("createdAt", ""))
        before_ts  = oldest_str
        time.sleep(0.2)

    if not all_records:
        return existing

    new_df = pd.DataFrame(all_records).sort_values("timestamp").reset_index(drop=True)

    # Merge with existing
    if not existing.empty:
        combined = pd.concat([existing, new_df], ignore_index=True)
        combined = combined.drop_duplicates("timestamp").sort_values("timestamp").reset_index(drop=True)
    else:
        combined = new_df

    # Save back
    combined.to_parquet(cache_path, index=False)
    return combined


def load_dydx_fr_cached(sym: str) -> pd.DataFrame:
    """Load dYdX FR from cache/k270_dydx/ parquet."""
    cache_path = DYDX_CACHE / f"dydx_fr_{sym}.parquet"
    if not cache_path.exists():
        return pd.DataFrame(columns=["timestamp", "dydx_fr"])
    df = pd.read_parquet(cache_path)
    if "timestamp" not in df.columns:
        df = df.reset_index()
    df["timestamp"] = pd.to_datetime(df["timestamp"])
    return df.sort_values("timestamp").reset_index(drop=True)


def build_dydx_daily_panel(incremental: bool = True) -> pd.DataFrame:
    """
    Refresh K270 dYdX FR panel.
    - If incremental: fetch last 3 days from API for each symbol to top-up cache
    - Aggregate hourly FR to daily mean
    - Returns daily panel DataFrame (index=date, columns=symbols)
    """
    print(f"\n  [K270 dYdX] Building daily FR panel ({len(K270_SYMBOLS)} symbols)...")

    # Check existing daily panel
    daily_path = CACHE / "k270_dydx_daily.parquet"
    if daily_path.exists() and incremental:
        existing_daily = pd.read_parquet(daily_path)
        existing_daily.index = pd.to_datetime(existing_daily.index)
        last_date = existing_daily.index.max()
        today = pd.Timestamp.utcnow().normalize().tz_localize(None)
        days_stale = (today - last_date).days
        print(f"  [K270] Existing daily panel: {existing_daily.shape}, "
              f"last={last_date.date()}, stale={days_stale}d")
        if days_stale == 0:
            print("  [K270] Panel up-to-date. Loading from cache.")
            return existing_daily
        # Fetch only recent data (lookback covers staleness + 1d buffer)
        lookback_hours = max(72, (days_stale + 2) * 24)
    else:
        existing_daily = pd.DataFrame()
        lookback_hours = 24 * 365 * 2  # fresh build = 2yr lookback

    # Incremental fetch per symbol
    sym_daily: Dict[str, pd.Series] = {}
    for sym in K270_SYMBOLS:
        try:
            if incremental and (DYDX_CACHE / f"dydx_fr_{sym}.parquet").exists():
                raw = fetch_dydx_fr_incremental(sym, lookback_hours=lookback_hours)
            else:
                raw = fetch_dydx_fr_incremental(sym, lookback_hours=lookback_hours)

            if raw.empty or "timestamp" not in raw.columns:
                print(f"    {sym}: no data")
                continue
            raw["timestamp"] = pd.to_datetime(raw["timestamp"])
            raw = raw.set_index("timestamp").sort_index()
            # Aggregate to daily mean (24 hourly events → 1 daily)
            daily = raw["dydx_fr"].resample("D").mean().dropna()
            daily.index = daily.index.normalize()
            sym_daily[sym] = daily
            time.sleep(0.15)  # polite rate-limiting
        except Exception as e:
            print(f"    {sym}: error {e}")
            continue

    if not sym_daily:
        print("  [K270] No symbols fetched. Returning cached panel if available.")
        return existing_daily if not existing_daily.empty else pd.DataFrame()

    new_panel = pd.DataFrame(sym_daily)

    # Merge with existing daily panel
    if not existing_daily.empty:
        merged = pd.concat([existing_daily, new_panel])
        merged = merged.groupby(merged.index).last().sort_index()
    else:
        merged = new_panel.sort_index()

    # Save
    merged.to_parquet(daily_path)
    print(f"  [K270] Daily panel saved: {merged.shape} → {daily_path}")
    return merged


# ─────────────────────────────────────────────────────────────────────────────
# 2. OKX Helpers (K275)
# ─────────────────────────────────────────────────────────────────────────────

def fetch_okx_fr_page(inst_id: str, after: Optional[str] = None) -> List[Dict]:
    """
    Fetch one page of OKX FR history (newest first).
    Paginate backwards via 'after' (fundingTime of oldest record).
    """
    url = f"{OKX_FR_URL}?instId={inst_id}&limit=100"
    if after:
        url += f"&after={after}"
    req = urllib.request.Request(
        url, headers={"User-Agent": "Mozilla/5.0", "Accept": "application/json"}
    )
    for attempt in range(3):
        try:
            with urllib.request.urlopen(req, timeout=20) as resp:
                data = json.loads(resp.read().decode())
                if data.get("code") != "0":
                    return []
                return data.get("data", [])
        except urllib.error.HTTPError as e:
            if e.code == 429:
                wait = 20 * (attempt + 1)
                print(f"    429 {inst_id}, wait {wait}s...")
                time.sleep(wait)
                continue
            print(f"    HTTP {e.code} for {inst_id}")
            return []
        except Exception as ex:
            print(f"    err {inst_id}: {ex}")
            if attempt < 2:
                time.sleep(5)
    return []


def fetch_okx_fr_incremental(sym: str) -> pd.DataFrame:
    """
    Incrementally fetch OKX FR for one symbol.
    OKX public API retains only ~90 days — always fetch all available.
    Returns DataFrame with [timestamp, okx_fr].
    """
    inst_id    = f"{sym}-USDT-SWAP"
    cache_path = CACHE / f"okx_fr_{sym}.parquet"

    print(f"    {sym}: fetching OKX (incremental)...")
    all_records: List[Dict] = []
    after: Optional[str] = None

    # Determine cutoff from cache
    cutoff_ts = pd.Timestamp("2020-01-01")
    existing = pd.DataFrame()
    if cache_path.exists():
        try:
            existing = pd.read_parquet(cache_path)
            if "timestamp" not in existing.columns:
                existing = existing.reset_index()
            existing["timestamp"] = pd.to_datetime(existing["timestamp"])
            cutoff_ts = existing["timestamp"].max()
        except Exception:
            existing = pd.DataFrame()

    for page in range(10):  # max 10 pages × 100 records = 1000 events ~333d at 8h
        records = fetch_okx_fr_page(inst_id, after=after)
        if not records:
            break

        done = False
        for r in records:
            ts_ms = int(r.get("fundingTime", 0))
            if ts_ms == 0:
                continue
            ts = pd.Timestamp(ts_ms, unit="ms").tz_localize(None)
            if ts <= cutoff_ts:
                done = True
                break
            fr = float(r.get("fundingRate", 0.0))
            all_records.append({"timestamp": ts, "okx_fr": fr})

        if done or len(records) < 100:
            break

        after = records[-1].get("fundingTime", None)
        time.sleep(0.2)

    if not all_records:
        return existing

    new_df = pd.DataFrame(all_records).sort_values("timestamp").reset_index(drop=True)

    if not existing.empty:
        combined = pd.concat([existing[["timestamp", "okx_fr"]], new_df], ignore_index=True)
        combined = combined.drop_duplicates("timestamp").sort_values("timestamp").reset_index(drop=True)
    else:
        combined = new_df

    combined.to_parquet(cache_path, index=False)
    return combined


def build_okx_daily_panel(incremental: bool = True) -> pd.DataFrame:
    """
    Refresh K275 OKX FR panel.
    OKX settles 3x/day (8h): panel stores the daily MEAN of 8h events.
    k287_satellite_run.py multiplies by K275_EVENTS_DAY=3 to get daily total.
    Convention: panel = mean(8h_events), run applies *3 = daily_total.
    Returns daily panel DataFrame (index=date, columns=symbols).
    """
    print(f"\n  [K275 OKX] Building daily FR panel ({len(K275_SYMBOLS)} symbols)...")

    daily_path = CACHE / "okx_fr_daily.parquet"

    # Check existing daily panel
    if daily_path.exists() and incremental:
        existing_daily = pd.read_parquet(daily_path)
        existing_daily.index = pd.to_datetime(existing_daily.index)
        last_date = existing_daily.index.max()
        today = pd.Timestamp.utcnow().normalize().tz_localize(None)
        days_stale = (today - last_date).days
        print(f"  [K275] Existing daily panel: {existing_daily.shape}, "
              f"last={last_date.date()}, stale={days_stale}d")
        if days_stale == 0:
            print("  [K275] Panel up-to-date. Loading from cache.")
            return existing_daily
    else:
        existing_daily = pd.DataFrame()

    sym_daily: Dict[str, pd.Series] = {}
    for sym in K275_SYMBOLS:
        try:
            raw = fetch_okx_fr_incremental(sym)
            if raw.empty or "okx_fr" not in raw.columns:
                # Try loading from cache only
                cache_path = CACHE / f"okx_fr_{sym}.parquet"
                if cache_path.exists():
                    raw = pd.read_parquet(cache_path)
                    if "timestamp" not in raw.columns:
                        raw = raw.reset_index()
                if raw.empty:
                    print(f"    {sym}: no data available")
                    continue

            raw["timestamp"] = pd.to_datetime(raw["timestamp"])
            raw = raw.set_index("timestamp").sort_index()
            # OKX 8h events: store daily MEAN of 8h rate (not sum).
            # k287_satellite_run.py compute_k275_daily_pnl() multiplies by K275_EVENTS_DAY=3
            # to reconstruct the daily total. Panel must store MEAN to avoid 3× double-count.
            # BUG FIX (K293): was .sum() which would cause 3× overcounting when run script
            # applies *3. Changed to .mean() to match backtest (wave_k275_okx_fr.py line 217).
            daily = raw["okx_fr"].resample("D").mean().dropna()
            daily.index = daily.index.normalize()
            # Filter out days with < 2 events (incomplete)
            event_count = raw["okx_fr"].resample("D").count()
            daily = daily[event_count >= 2]
            sym_daily[sym] = daily
            time.sleep(0.1)
        except Exception as e:
            print(f"    {sym}: error {e}")
            continue

    if not sym_daily:
        print("  [K275] No symbols fetched. Returning cached panel.")
        return existing_daily if not existing_daily.empty else pd.DataFrame()

    new_panel = pd.DataFrame(sym_daily)

    if not existing_daily.empty:
        # Reindex both to same columns
        all_cols = sorted(set(existing_daily.columns) | set(new_panel.columns))
        merged = pd.concat([
            existing_daily.reindex(columns=all_cols),
            new_panel.reindex(columns=all_cols),
        ])
        merged = merged.groupby(merged.index).last().sort_index()
    else:
        merged = new_panel.sort_index()

    # Keep only K275 universe
    merged = merged[[c for c in K275_SYMBOLS if c in merged.columns]]
    merged.to_parquet(daily_path)
    print(f"  [K275] Daily panel saved: {merged.shape} → {daily_path}")
    return merged


# ─────────────────────────────────────────────────────────────────────────────
# 3. Exchange Status Check
# ─────────────────────────────────────────────────────────────────────────────

def check_dydx_status() -> Dict:
    """Check dYdX v4 indexer availability."""
    try:
        url = "https://indexer.dydx.trade/v4/time"
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=10) as resp:
            data = json.loads(resp.read().decode())
            iso_ts = data.get("iso", "unknown")
            return {"status": "OK", "server_time": iso_ts}
    except Exception as e:
        return {"status": "ERROR", "error": str(e)}


def check_okx_status() -> Dict:
    """Check OKX API availability via system time endpoint."""
    try:
        url = "https://www.okx.com/api/v5/public/time"
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=10) as resp:
            data = json.loads(resp.read().decode())
            if data.get("code") == "0":
                ts_ms = data["data"][0].get("ts", "0")
                return {"status": "OK", "server_ts_ms": ts_ms}
            return {"status": "ERROR", "code": data.get("code")}
    except Exception as e:
        return {"status": "ERROR", "error": str(e)}


# ─────────────────────────────────────────────────────────────────────────────
# 4. Snapshot Assembly
# ─────────────────────────────────────────────────────────────────────────────

def build_snapshot(date_str: str, incremental: bool = True) -> Dict:
    """
    Assemble all K287 Satellite live data into a daily snapshot.
    Returns metadata dict; saves parquet snapshot.
    """
    print(f"\n=== K287 Satellite Fetch — {date_str} ===\n")
    t0 = time.time()

    # Exchange status checks
    print("Checking exchange availability...")
    dydx_status = check_dydx_status()
    okx_status  = check_okx_status()
    print(f"  dYdX: {dydx_status['status']}  OKX: {okx_status['status']}")

    # K270 dYdX panel
    print("\nFetching K270 dYdX v4 FR panel...")
    k270_panel = build_dydx_daily_panel(incremental=incremental)

    # K275 OKX panel
    print("\nFetching K275 OKX FR panel...")
    k275_panel = build_okx_daily_panel(incremental=incremental)

    elapsed = time.time() - t0

    # Compute today's signal preview
    k270_stats = _compute_panel_stats(k270_panel, window=14, label="K270")
    k275_stats = _compute_panel_stats(k275_panel, window=7,  label="K275")

    snapshot = {
        "fetch_date":     date_str,
        "fetch_ts_utc":   datetime.now(timezone.utc).isoformat(),
        "elapsed_sec":    round(elapsed, 1),
        "architecture":   "K287d Satellite (K270 dYdX 35.5% + K275 OKX 64.5%)",
        "exchange_status": {
            "dydx": dydx_status,
            "okx":  okx_status,
        },
        "k270": {
            "exchange":       "dYdX v4 (Cosmos DEX)",
            "n_symbols":      len(k270_panel.columns) if not k270_panel.empty else 0,
            "universe":       K270_SYMBOLS,
            "panel_shape":    list(k270_panel.shape) if not k270_panel.empty else [0, 0],
            "panel_last_date": str(k270_panel.index[-1].date()) if not k270_panel.empty else None,
            "signal_window":  14,
            **k270_stats,
        },
        "k275": {
            "exchange":       "OKX (CEX, 8h settlement)",
            "n_symbols":      len(k275_panel.columns) if not k275_panel.empty else 0,
            "universe":       K275_SYMBOLS,
            "panel_shape":    list(k275_panel.shape) if not k275_panel.empty else [0, 0],
            "panel_last_date": str(k275_panel.index[-1].date()) if not k275_panel.empty else None,
            "signal_window":  7,
            **k275_stats,
        },
        "dydx_status":    dydx_status["status"],
        "okx_status":     okx_status["status"],
    }

    # Save combined snapshot parquet
    # Stack K270 and K275 panels side by side with prefix columns
    if not k270_panel.empty or not k275_panel.empty:
        frames = []
        if not k270_panel.empty:
            k270_prefixed = k270_panel.copy()
            k270_prefixed.columns = [f"K270_{c}" for c in k270_panel.columns]
            frames.append(k270_prefixed)
        if not k275_panel.empty:
            k275_prefixed = k275_panel.copy()
            k275_prefixed.columns = [f"K275_{c}" for c in k275_panel.columns]
            frames.append(k275_prefixed)

        if frames:
            combined = pd.concat(frames, axis=1).sort_index()
            snapshot_path = CACHE / f"k287_satellite_{date_str.replace('-', '')}.parquet"
            combined.to_parquet(snapshot_path)
            snapshot["parquet_path"] = str(snapshot_path)
            print(f"\n  Snapshot saved: {snapshot_path}")
    else:
        snapshot["parquet_path"] = None

    # Save JSON snapshot
    json_path = CACHE / f"k287_satellite_{date_str.replace('-', '')}.json"
    with open(json_path, "w") as f:
        def _sanitize(v):
            if isinstance(v, float) and math.isnan(v):
                return None
            if isinstance(v, dict):
                return {kk: _sanitize(vv) for kk, vv in v.items()}
            if isinstance(v, list):
                return [_sanitize(x) for x in v]
            return v
        f.write(json.dumps(_sanitize(snapshot), indent=2))
    print(f"  JSON snapshot: {json_path}")

    return snapshot


def _compute_panel_stats(panel: pd.DataFrame, window: int, label: str) -> Dict:
    """Compute current signal state (long/short quartiles) from daily FR panel."""
    if panel.empty or len(panel.columns) < 4:
        return {"error": f"{label} panel empty or too narrow"}
    recent = panel.tail(window)
    if len(recent) < max(3, window // 2):
        return {"error": f"{label} panel too short ({len(recent)} rows)"}
    sig = recent.mean()
    valid = sig.dropna()
    n = len(valid)
    if n < 4:
        return {"error": f"{label} too few valid symbols ({n})"}
    n_q    = max(1, int(n * 0.25))
    ranked = valid.rank(ascending=True)
    long_syms  = ranked[ranked <= n_q].index.tolist()
    short_syms = ranked[ranked > n - n_q].index.tolist()
    daily_cov  = panel.tail(7).notna().mean()
    low_liq    = daily_cov[daily_cov < 0.7].index.tolist()
    return {
        "signal_long_sleeve":  long_syms,
        "signal_short_sleeve": short_syms,
        "low_liquidity":       low_liq,
        "n_valid_symbols":     int(n),
    }


# ─────────────────────────────────────────────────────────────────────────────
# CLI Entry Point
# ─────────────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="K287d Satellite Live Data Fetcher")
    parser.add_argument("--date",  default=None, help="Date override YYYY-MM-DD")
    parser.add_argument("--force", action="store_true", help="Force re-fetch even if cached today")
    parser.add_argument("--no-incremental", action="store_true",
                        help="Full panel rebuild (slow; ignore existing cache for logic)")
    args = parser.parse_args()

    date_str = args.date or datetime.now(timezone.utc).strftime("%Y-%m-%d")

    # Skip if already fetched today (unless --force)
    json_path = CACHE / f"k287_satellite_{date_str.replace('-', '')}.json"
    if json_path.exists() and not args.force:
        print(f"Already fetched for {date_str}. Use --force to re-fetch.")
        return

    incremental = not args.no_incremental
    snapshot = build_snapshot(date_str, incremental=incremental)

    print(f"\n=== Fetch complete in {snapshot['elapsed_sec']}s ===")
    print(f"  dYdX status: {snapshot['dydx_status']}")
    print(f"  OKX status:  {snapshot['okx_status']}")
    print(f"  K270 symbols: {snapshot['k270'].get('n_symbols', 'N/A')}")
    print(f"  K275 symbols: {snapshot['k275'].get('n_symbols', 'N/A')}")
    print(f"  K270 long:    {snapshot['k270'].get('signal_long_sleeve', [])}")
    print(f"  K275 long:    {snapshot['k275'].get('signal_long_sleeve', [])}")


if __name__ == "__main__":
    main()

"""
k302a_satellite_fetch.py — K302a Satellite Live Data Fetcher
=============================================================
Fetches HL funding rates for PAXG and SPX (HIP-3 RWA perps).

K302a Satellite = K297 [PAXG 60% + SPX 40%] — HyperLiquid only
  - PAXG: Gold-backed RWA perp, always-on long carry. HL data from 2025-04-06.
  - SPX:  S&P 500 equity-index RWA perp, always-on long carry. HL data from 2025-01-07.

Replaces K289 (K287d satellite: K270 dYdX + K275 OKX).

Data flow:
  Incremental refresh from existing cache/hl_hip3_fr_daily.parquet
  → filter for PAXG and SPX
  → aggregate to daily mean FR
  → save cache/k302a_satellite_YYYYMMDD.parquet

HL public API:
  POST https://api.hyperliquid.xyz/info
  Body: {"type": "fundingHistory", "coin": "PAXG"|"SPX"}
  Returns: list of {coin, fundingRate, premium, time} (newest first, up to 500 records)

Maker/taker cost reality (K296 finding):
  HL maker: 0.015%/side (1.5 bp)
  HL taker: 0.045%/side (4.5 bp)
  → always-on carry uses maker orders; apply 1.5 bp/side (3 bp round-trip)
  → Paper-trade uses 7 bp/side (conservative per K297 spec for safety margin)

Usage:
  python3 scripts/k302a_satellite_fetch.py
  python3 scripts/k302a_satellite_fetch.py --date 2026-05-25
  python3 scripts/k302a_satellite_fetch.py --force   # re-fetch even if cached today
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
BASE  = Path("/Users/nekonaomichi/crypto-lab")
CACHE = BASE / "cache"
LOGS  = BASE / "logs"
CACHE.mkdir(exist_ok=True)
LOGS.mkdir(exist_ok=True)

# ── K302a Satellite Universe (K297 HIP-3 RWA perps on HL) ─────────────────────
K302A_COINS  = ["PAXG", "SPX"]
PAXG_WEIGHT  = 0.60    # 60% of satellite (per K297 recommendation)
SPX_WEIGHT   = 0.40    # 40% of satellite

# ── Source cache (from K297 research wave) ─────────────────────────────────────
HL_HIP3_PARQUET = CACHE / "hl_hip3_fr_daily.parquet"

# ── HL public API ─────────────────────────────────────────────────────────────
HL_INFO_URL = "https://api.hyperliquid.xyz/info"

# ── Maker/taker cost (K296 finding) ───────────────────────────────────────────
HL_MAKER_COST = 0.00015   # 0.015%/side = 1.5 bp (actual HL maker)
HL_TAKER_COST = 0.00045   # 0.045%/side = 4.5 bp (actual HL taker)
PAPER_COST    = 0.0007    # 7 bp/side (conservative paper-trade assumption per K297)


# ─────────────────────────────────────────────────────────────────────────────
# 1. HL Funding Rate Fetch (PAXG / SPX)
# ─────────────────────────────────────────────────────────────────────────────

def fetch_hl_funding_history(coin: str, start_time_ms: Optional[int] = None) -> List[Dict]:
    """
    Fetch HL FR history for a single coin.
    HL API: POST /info {"type": "fundingHistory", "coin": COIN}
    Optional startTime (ms epoch) to limit response to recent records.
    Returns list of records (newest first): {coin, fundingRate, premium, time}.
    """
    payload: Dict = {"type": "fundingHistory", "coin": coin}
    if start_time_ms is not None:
        payload["startTime"] = start_time_ms

    body = json.dumps(payload).encode()
    req  = urllib.request.Request(
        HL_INFO_URL,
        data=body,
        headers={"Content-Type": "application/json", "User-Agent": "Mozilla/5.0"},
        method="POST",
    )

    for attempt in range(3):
        try:
            with urllib.request.urlopen(req, timeout=30) as resp:
                return json.loads(resp.read().decode())
        except urllib.error.HTTPError as e:
            if e.code == 429:
                wait = 15 * (attempt + 1)
                print(f"    429 rate-limit {coin}, waiting {wait}s...")
                time.sleep(wait)
                req = urllib.request.Request(
                    HL_INFO_URL, data=body,
                    headers={"Content-Type": "application/json", "User-Agent": "Mozilla/5.0"},
                    method="POST",
                )
                continue
            print(f"    HTTP {e.code} for {coin}")
            return []
        except Exception as ex:
            print(f"    err fetching {coin}: {ex}")
            if attempt < 2:
                time.sleep(5)
    return []


def load_existing_hl_hip3() -> pd.DataFrame:
    """Load existing hl_hip3_fr_daily.parquet if present."""
    if not HL_HIP3_PARQUET.exists():
        return pd.DataFrame(columns=["timestamp", "funding_rate", "coin", "is_weekend"])
    df = pd.read_parquet(HL_HIP3_PARQUET)
    if "timestamp" not in df.columns:
        df = df.reset_index()
    df["timestamp"] = pd.to_datetime(df["timestamp"], utc=True)
    return df


def fetch_coin_incremental(coin: str, existing_df: pd.DataFrame) -> pd.DataFrame:
    """
    Incrementally fetch HL FR for one coin.
    Determines last timestamp in existing data and fetches only newer records.
    Returns combined DataFrame with columns [timestamp, funding_rate, coin, is_weekend].
    """
    # Determine cutoff from existing data
    coin_existing = existing_df[existing_df["coin"] == coin].copy() if not existing_df.empty else pd.DataFrame()
    if not coin_existing.empty:
        last_ts = pd.to_datetime(coin_existing["timestamp"]).max()
        # startTime = last_ts + 1ms to avoid re-fetching the last known record
        start_ms = int(last_ts.timestamp() * 1000) + 1
        print(f"    {coin}: existing up to {last_ts.strftime('%Y-%m-%d %H:%M')} UTC, fetching incremental")
    else:
        start_ms = None
        print(f"    {coin}: no cache, fetching full history")

    records = fetch_hl_funding_history(coin, start_time_ms=start_ms)

    if not records:
        print(f"    {coin}: no new records from API")
        return coin_existing

    # Parse API response: each record has {coin, fundingRate, premium, time}
    rows = []
    for r in records:
        ts_ms = r.get("time", 0)
        if ts_ms == 0:
            continue
        ts = pd.Timestamp(ts_ms, unit="ms", tz="UTC")
        fr = float(r.get("fundingRate", 0.0))
        # Compute is_weekend: Saturday (5) or Sunday (6) in UTC
        dow = ts.weekday()  # Monday=0 … Sunday=6
        is_weekend = dow >= 5
        rows.append({
            "timestamp":    ts,
            "funding_rate": fr,
            "coin":         coin,
            "is_weekend":   is_weekend,
        })

    if not rows:
        return coin_existing

    new_df = pd.DataFrame(rows)
    new_df["timestamp"] = pd.to_datetime(new_df["timestamp"], utc=True)

    if not coin_existing.empty:
        coin_existing["timestamp"] = pd.to_datetime(coin_existing["timestamp"], utc=True)
        combined = pd.concat([coin_existing, new_df], ignore_index=True)
        combined = combined.drop_duplicates("timestamp").sort_values("timestamp").reset_index(drop=True)
    else:
        combined = new_df.sort_values("timestamp").reset_index(drop=True)

    print(f"    {coin}: {len(new_df)} new records → total {len(combined)} records")
    return combined


def build_k302a_fr_panel(incremental: bool = True) -> pd.DataFrame:
    """
    Refresh K302a (PAXG + SPX) HL FR panel.
    - Loads existing hl_hip3_fr_daily.parquet
    - Incrementally fetches new records from HL API
    - Aggregates hourly FR to daily mean (hourly HL settlement)
    - Returns daily panel: index=date, columns=[PAXG, SPX]
    """
    print(f"\n  [K302a Fetch] Building PAXG/SPX daily FR panel...")

    # Check if today's data already in cache (fast path)
    daily_path = CACHE / "k302a_fr_daily.parquet"
    today = pd.Timestamp.utcnow().normalize().tz_localize(None)

    if daily_path.exists() and incremental:
        existing_daily = pd.read_parquet(daily_path)
        existing_daily.index = pd.to_datetime(existing_daily.index)
        if existing_daily.index.tz is not None:
            existing_daily.index = existing_daily.index.tz_localize(None)
        last_date = existing_daily.index.max()
        days_stale = (today - last_date.normalize()).days
        if days_stale == 0:
            print(f"  [K302a] Daily panel up-to-date (last={last_date.date()}). Loading from cache.")
            return existing_daily
        print(f"  [K302a] Daily panel stale by {days_stale}d, refreshing...")
    else:
        existing_daily = pd.DataFrame()

    # Load hourly raw cache
    existing_raw = load_existing_hl_hip3()

    # Incremental fetch per coin
    all_coin_dfs = []
    for coin in K302A_COINS:
        try:
            coin_df = fetch_coin_incremental(coin, existing_raw)
            if not coin_df.empty:
                all_coin_dfs.append(coin_df)
            time.sleep(0.3)
        except Exception as e:
            print(f"    {coin}: error — {e}")
            # Fall back to existing cache for this coin
            if not existing_raw.empty:
                fallback = existing_raw[existing_raw["coin"] == coin]
                if not fallback.empty:
                    all_coin_dfs.append(fallback)

    if not all_coin_dfs:
        print("  [K302a] No data fetched! Returning cached daily panel.")
        return existing_daily

    # Combine all coin hourly data and save back to hl_hip3_fr_daily.parquet
    combined_hourly = pd.concat(all_coin_dfs, ignore_index=True)
    combined_hourly["timestamp"] = pd.to_datetime(combined_hourly["timestamp"], utc=True)
    combined_hourly = combined_hourly.drop_duplicates(["timestamp", "coin"]).sort_values(
        ["coin", "timestamp"]
    ).reset_index(drop=True)

    # Merge with other coins in existing hl_hip3_fr_daily.parquet (don't lose them)
    other_coins = existing_raw[~existing_raw["coin"].isin(K302A_COINS)] if not existing_raw.empty else pd.DataFrame()
    if not other_coins.empty:
        full_hourly = pd.concat([other_coins, combined_hourly], ignore_index=True)
        full_hourly = full_hourly.drop_duplicates(["timestamp", "coin"]).sort_values(
            ["coin", "timestamp"]
        ).reset_index(drop=True)
        full_hourly.to_parquet(HL_HIP3_PARQUET, index=False)
    else:
        combined_hourly.to_parquet(HL_HIP3_PARQUET, index=False)

    print(f"  [K302a] Updated hl_hip3_fr_daily.parquet: {len(combined_hourly)} K302a records")

    # Aggregate hourly → daily mean for PAXG and SPX
    sym_daily: Dict[str, pd.Series] = {}
    for coin in K302A_COINS:
        coin_df = combined_hourly[combined_hourly["coin"] == coin].copy()
        if coin_df.empty:
            print(f"    {coin}: no data for daily aggregation")
            continue
        coin_df["timestamp"] = pd.to_datetime(coin_df["timestamp"], utc=True)
        coin_df = coin_df.set_index("timestamp").sort_index()
        # Daily mean of hourly FR (HL settles every hour)
        daily = coin_df["funding_rate"].resample("D").mean().dropna()
        daily.index = daily.index.normalize().tz_localize(None)
        sym_daily[coin] = daily
        print(f"    {coin}: {len(daily)} daily records "
              f"({daily.index[0].date()} → {daily.index[-1].date()})")

    if not sym_daily:
        print("  [K302a] No daily series built.")
        return existing_daily

    new_panel = pd.DataFrame(sym_daily)

    # Merge with existing daily panel
    if not existing_daily.empty:
        merged = pd.concat([existing_daily, new_panel])
        merged = merged.groupby(merged.index).last().sort_index()
    else:
        merged = new_panel.sort_index()

    # Save K302a-specific daily panel
    merged.to_parquet(daily_path)
    print(f"  [K302a] Daily panel saved: {merged.shape} → {daily_path}")
    return merged


# ─────────────────────────────────────────────────────────────────────────────
# 2. HL Status Check
# ─────────────────────────────────────────────────────────────────────────────

def check_hl_status() -> Dict:
    """Check HL API availability via meta endpoint."""
    try:
        payload = json.dumps({"type": "meta"}).encode()
        req = urllib.request.Request(
            HL_INFO_URL, data=payload,
            headers={"Content-Type": "application/json", "User-Agent": "Mozilla/5.0"},
            method="POST",
        )
        with urllib.request.urlopen(req, timeout=10) as resp:
            data = json.loads(resp.read().decode())
            universe = data.get("universe", [])
            return {
                "status":       "OK",
                "n_markets":    len(universe),
                "check_ts_utc": datetime.now(timezone.utc).isoformat(),
            }
    except Exception as e:
        return {"status": "ERROR", "error": str(e)}


# ─────────────────────────────────────────────────────────────────────────────
# 3. Snapshot Assembly
# ─────────────────────────────────────────────────────────────────────────────

def _panel_stats(panel: pd.DataFrame, label: str) -> Dict:
    """Compute latest FR levels and annualized carry estimate per coin."""
    stats: Dict = {}
    for coin in K302A_COINS:
        if coin not in panel.columns:
            stats[coin] = {"error": "no data"}
            continue
        series = panel[coin].dropna()
        if len(series) < 7:
            stats[coin] = {"error": f"only {len(series)} days"}
            continue
        # HL settles hourly: daily_mean_fr × 8760 = annualized FR (continuous)
        last7  = series.tail(7).mean()
        last30 = series.tail(30).mean() if len(series) >= 30 else series.mean()
        ann_7d = last7  * 24 * 365   # hourly compounding
        ann_30d= last30 * 24 * 365
        pct_pos= float((series > 0).mean() * 100)
        stats[coin] = {
            "last_daily_mean_fr": round(float(series.iloc[-1]), 8),
            "7d_mean_fr":         round(float(last7),  8),
            "30d_mean_fr":        round(float(last30), 8),
            "7d_ann_pct":         round(float(ann_7d  * 100), 2),
            "30d_ann_pct":        round(float(ann_30d * 100), 2),
            "pct_positive":       round(pct_pos, 1),
            "n_days":             int(len(series)),
            "last_date":          str(series.index[-1].date()),
        }
    return stats


def build_snapshot(date_str: str, incremental: bool = True) -> Dict:
    """
    Assemble K302a Satellite daily snapshot.
    Returns metadata dict; saves parquet + JSON.
    """
    print(f"\n=== K302a Satellite Fetch — {date_str} ===\n")
    t0 = time.time()

    # HL status check
    print("Checking HL API availability...")
    hl_status = check_hl_status()
    print(f"  HL: {hl_status['status']}  "
          f"(markets: {hl_status.get('n_markets','?')})")

    # Build daily FR panel
    panel = build_k302a_fr_panel(incremental=incremental)

    elapsed = time.time() - t0
    stats   = _panel_stats(panel, "K302a")

    snapshot = {
        "fetch_date":     date_str,
        "fetch_ts_utc":   datetime.now(timezone.utc).isoformat(),
        "elapsed_sec":    round(elapsed, 1),
        "architecture":   "K302a Satellite (PAXG 60% + SPX 40%) — HyperLiquid only",
        "version":        "v6.12",
        "replaces":       "K289 (K287d: K270 dYdX + K275 OKX)",
        "exchange_status": {"hl": hl_status},
        "satellite_weights": {"PAXG": PAXG_WEIGHT, "SPX": SPX_WEIGHT},
        "cost_reality": {
            "hl_maker_bp":  round(HL_MAKER_COST * 1e4, 2),
            "hl_taker_bp":  round(HL_TAKER_COST * 1e4, 2),
            "paper_cost_bp": round(PAPER_COST  * 1e4, 2),
            "source":        "K296 liminal research finding",
        },
        "panel_shape":    list(panel.shape) if not panel.empty else [0, 0],
        "panel_last_date": str(panel.index[-1].date()) if not panel.empty else None,
        "coin_stats":     stats,
        "hl_status":      hl_status["status"],
    }

    # Save snapshot parquet
    if not panel.empty:
        snap_path = CACHE / f"k302a_satellite_{date_str.replace('-', '')}.parquet"
        panel.to_parquet(snap_path)
        snapshot["parquet_path"] = str(snap_path)
        print(f"\n  Snapshot parquet: {snap_path}")

    # Save snapshot JSON
    def _san(v):
        if isinstance(v, float) and math.isnan(v):
            return None
        if isinstance(v, dict):
            return {kk: _san(vv) for kk, vv in v.items()}
        if isinstance(v, list):
            return [_san(x) for x in v]
        return v

    json_path = CACHE / f"k302a_satellite_{date_str.replace('-', '')}.json"
    with open(json_path, "w") as f:
        f.write(json.dumps(_san(snapshot), indent=2))
    print(f"  Snapshot JSON:   {json_path}")

    return snapshot


# ─────────────────────────────────────────────────────────────────────────────
# CLI Entry Point
# ─────────────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="K302a Satellite Live Data Fetcher (PAXG+SPX on HL)")
    parser.add_argument("--date",           default=None, help="Date override YYYY-MM-DD")
    parser.add_argument("--force",          action="store_true", help="Force re-fetch even if cached today")
    parser.add_argument("--no-incremental", action="store_true",
                        help="Full panel rebuild (slow; ignore daily cache)")
    args = parser.parse_args()

    date_str = args.date or datetime.now(timezone.utc).strftime("%Y-%m-%d")

    # Skip if already fetched today (unless --force)
    json_path = CACHE / f"k302a_satellite_{date_str.replace('-', '')}.json"
    if json_path.exists() and not args.force:
        print(f"Already fetched for {date_str}. Use --force to re-fetch.")
        return

    incremental = not args.no_incremental
    snapshot = build_snapshot(date_str, incremental=incremental)

    print(f"\n=== K302a Fetch complete in {snapshot['elapsed_sec']}s ===")
    print(f"  HL status:     {snapshot['hl_status']}")
    print(f"  Panel shape:   {snapshot['panel_shape']}")
    print(f"  PAXG stats:    {snapshot['coin_stats'].get('PAXG', {})}")
    print(f"  SPX stats:     {snapshot['coin_stats'].get('SPX', {})}")
    print(f"  Cost reality:  HL maker={snapshot['cost_reality']['hl_maker_bp']}bp  "
          f"paper={snapshot['cost_reality']['paper_cost_bp']}bp")


if __name__ == "__main__":
    main()

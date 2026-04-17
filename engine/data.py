"""Data fetcher — MEXC klines + Binance Futures derivatives data."""

import asyncio
import logging
import time
import httpx
import numpy as np
import pandas as pd
from pathlib import Path

log = logging.getLogger(__name__)

CACHE_DIR = Path(__file__).parent.parent / "cache"
CACHE_DIR.mkdir(exist_ok=True)

MEXC_BASE = "https://api.mexc.com/api/v3"
BINANCE_FAPI = "https://fapi.binance.com"


async def _sleep(secs: float):
    await asyncio.sleep(secs)


# ── MEXC Klines ──────────────────────────────────────────

async def fetch_klines(symbol="BTCUSDT", interval="5m", days=30, limit_per_req=500):
    """Fetch kline data from MEXC API, with local cache."""
    cache_file = CACHE_DIR / f"{symbol}_{interval}_{days}d.parquet"
    if cache_file.exists() and (time.time() - cache_file.stat().st_mtime) < 3600:
        return pd.read_parquet(cache_file)

    end_ms = int(time.time() * 1000)
    start_ms = end_ms - days * 86400 * 1000
    all_rows = []

    async with httpx.AsyncClient(timeout=30) as client:
        cursor = start_ms
        while cursor < end_ms:
            params = {
                "symbol": symbol, "interval": interval,
                "startTime": cursor, "endTime": end_ms, "limit": limit_per_req,
            }
            resp = await client.get(f"{MEXC_BASE}/klines", params=params)
            resp.raise_for_status()
            rows = resp.json()
            if not rows:
                break
            all_rows.extend(rows)
            cursor = rows[-1][0] + 1
            if len(rows) < limit_per_req:
                break
            await _sleep(0.15)

    if not all_rows:
        return pd.DataFrame()

    df = pd.DataFrame(all_rows, columns=[
        "open_time", "open", "high", "low", "close", "volume",
        "close_time", "quote_volume",
    ])
    for c in ["open", "high", "low", "close", "volume", "quote_volume"]:
        df[c] = df[c].astype(float)
    df["open_time"] = pd.to_datetime(df["open_time"], unit="ms")
    df["close_time"] = pd.to_datetime(df["close_time"], unit="ms")
    df = df.drop_duplicates(subset="open_time").sort_values("open_time").reset_index(drop=True)
    df.to_parquet(cache_file, index=False)
    return df


# ── Binance Futures — paginated helper ───────────────────

async def _fetch_paginated(client, url, symbol, period, start_ms, end_ms,
                           limit=500, ts_key="timestamp"):
    all_data = []
    cursor = start_ms
    retries = 0
    while cursor < end_ms:
        params = {"symbol": symbol, "period": period,
                  "startTime": cursor, "endTime": end_ms, "limit": limit}
        try:
            resp = await client.get(url, params=params)
            if resp.status_code == 429:
                await _sleep(2)
                retries += 1
                if retries > 3:
                    break
                continue
            resp.raise_for_status()
            rows = resp.json()
        except Exception as e:
            log.warning(f"Binance API error {url}: {e}")
            break
        if not rows:
            break
        all_data.extend(rows)
        last_ts = rows[-1].get(ts_key, 0)
        if isinstance(last_ts, str):
            last_ts = int(last_ts)
        cursor = int(last_ts) + 1
        if len(rows) < limit:
            break
        await _sleep(0.15)
        retries = 0
    return all_data


# ── Open Interest ────────────────────────────────────────

async def fetch_open_interest(symbol="BTCUSDT", period="5m", days=30):
    cache_file = CACHE_DIR / f"oi_{symbol}_{period}_{days}d.parquet"
    if cache_file.exists() and (time.time() - cache_file.stat().st_mtime) < 3600:
        return pd.read_parquet(cache_file)

    end_ms = int(time.time() * 1000)
    start_ms = end_ms - days * 86400 * 1000

    async with httpx.AsyncClient(timeout=30) as client:
        data = await _fetch_paginated(
            client, f"{BINANCE_FAPI}/futures/data/openInterestHist",
            symbol, period, start_ms, end_ms,
        )
    if not data:
        log.warning("No OI data fetched")
        return pd.DataFrame()

    df = pd.DataFrame(data)
    df["timestamp"] = pd.to_datetime(pd.to_numeric(df["timestamp"]), unit="ms")
    df["oi"] = pd.to_numeric(df["sumOpenInterest"], errors="coerce")
    df["oi_value"] = pd.to_numeric(df["sumOpenInterestValue"], errors="coerce")
    df = df[["timestamp", "oi", "oi_value"]].drop_duplicates("timestamp").sort_values("timestamp").reset_index(drop=True)
    try:
        df.to_parquet(cache_file, index=False)
    except Exception:
        pass
    return df


# ── Funding Rate ─────────────────────────────────────────

async def fetch_funding_rate(symbol="BTCUSDT", days=30):
    cache_file = CACHE_DIR / f"funding_{symbol}_{days}d.parquet"
    if cache_file.exists() and (time.time() - cache_file.stat().st_mtime) < 3600:
        return pd.read_parquet(cache_file)

    end_ms = int(time.time() * 1000)
    start_ms = end_ms - days * 86400 * 1000

    async with httpx.AsyncClient(timeout=30) as client:
        try:
            params = {"symbol": symbol, "startTime": start_ms, "endTime": end_ms, "limit": 1000}
            resp = await client.get(f"{BINANCE_FAPI}/fapi/v1/fundingRate", params=params)
            resp.raise_for_status()
            data = resp.json()
        except Exception as e:
            log.warning(f"Funding rate fetch error: {e}")
            return pd.DataFrame()

    if not data:
        return pd.DataFrame()

    df = pd.DataFrame(data)
    df["timestamp"] = pd.to_datetime(pd.to_numeric(df["fundingTime"]), unit="ms")
    df["funding_rate"] = pd.to_numeric(df["fundingRate"], errors="coerce")
    df = df[["timestamp", "funding_rate"]].drop_duplicates("timestamp").sort_values("timestamp").reset_index(drop=True)
    try:
        df.to_parquet(cache_file, index=False)
    except Exception:
        pass
    return df


# ── Global Long/Short Ratio ─────────────────────────────

async def fetch_long_short_ratio(symbol="BTCUSDT", period="5m", days=30):
    cache_file = CACHE_DIR / f"ls_{symbol}_{period}_{days}d.parquet"
    if cache_file.exists() and (time.time() - cache_file.stat().st_mtime) < 3600:
        return pd.read_parquet(cache_file)

    end_ms = int(time.time() * 1000)
    start_ms = end_ms - days * 86400 * 1000

    async with httpx.AsyncClient(timeout=30) as client:
        data = await _fetch_paginated(
            client, f"{BINANCE_FAPI}/futures/data/globalLongShortAccountRatio",
            symbol, period, start_ms, end_ms,
        )
    if not data:
        log.warning("No L/S ratio data fetched")
        return pd.DataFrame()

    df = pd.DataFrame(data)
    df["timestamp"] = pd.to_datetime(pd.to_numeric(df["timestamp"]), unit="ms")
    df["ls_ratio"] = pd.to_numeric(df["longShortRatio"], errors="coerce")
    df["long_account"] = pd.to_numeric(df["longAccount"], errors="coerce")
    df["short_account"] = pd.to_numeric(df["shortAccount"], errors="coerce")
    df = df[["timestamp", "ls_ratio", "long_account", "short_account"]].drop_duplicates("timestamp").sort_values("timestamp").reset_index(drop=True)
    try:
        df.to_parquet(cache_file, index=False)
    except Exception:
        pass
    return df


# ── Taker Buy/Sell Volume ────────────────────────────────

async def fetch_taker_volume(symbol="BTCUSDT", period="5m", days=30):
    cache_file = CACHE_DIR / f"taker_{symbol}_{period}_{days}d.parquet"
    if cache_file.exists() and (time.time() - cache_file.stat().st_mtime) < 3600:
        return pd.read_parquet(cache_file)

    end_ms = int(time.time() * 1000)
    start_ms = end_ms - days * 86400 * 1000

    async with httpx.AsyncClient(timeout=30) as client:
        data = await _fetch_paginated(
            client, f"{BINANCE_FAPI}/futures/data/takerlongshortRatio",
            symbol, period, start_ms, end_ms,
        )
    if not data:
        log.warning("No taker volume data fetched")
        return pd.DataFrame()

    df = pd.DataFrame(data)
    df["timestamp"] = pd.to_datetime(pd.to_numeric(df["timestamp"]), unit="ms")
    df["taker_buy_sell_ratio"] = pd.to_numeric(df["buySellRatio"], errors="coerce")
    df["taker_buy_vol"] = pd.to_numeric(df["buyVol"], errors="coerce")
    df["taker_sell_vol"] = pd.to_numeric(df["sellVol"], errors="coerce")
    df = df[["timestamp", "taker_buy_sell_ratio", "taker_buy_vol", "taker_sell_vol"]].drop_duplicates("timestamp").sort_values("timestamp").reset_index(drop=True)
    try:
        df.to_parquet(cache_file, index=False)
    except Exception:
        pass
    return df


# ── Top Trader Long/Short Position Ratio ─────────────────

async def fetch_top_ls_ratio(symbol="BTCUSDT", period="5m", days=30):
    cache_file = CACHE_DIR / f"topls_{symbol}_{period}_{days}d.parquet"
    if cache_file.exists() and (time.time() - cache_file.stat().st_mtime) < 3600:
        return pd.read_parquet(cache_file)

    end_ms = int(time.time() * 1000)
    start_ms = end_ms - days * 86400 * 1000

    async with httpx.AsyncClient(timeout=30) as client:
        data = await _fetch_paginated(
            client, f"{BINANCE_FAPI}/futures/data/topLongShortPositionRatio",
            symbol, period, start_ms, end_ms,
        )
    if not data:
        log.warning("No top L/S ratio data fetched")
        return pd.DataFrame()

    df = pd.DataFrame(data)
    df["timestamp"] = pd.to_datetime(pd.to_numeric(df["timestamp"]), unit="ms")
    df["top_ls_ratio"] = pd.to_numeric(df["longShortRatio"], errors="coerce")
    df["top_long_account"] = pd.to_numeric(df["longAccount"], errors="coerce")
    df["top_short_account"] = pd.to_numeric(df["shortAccount"], errors="coerce")
    df = df[["timestamp", "top_ls_ratio", "top_long_account", "top_short_account"]].drop_duplicates("timestamp").sort_values("timestamp").reset_index(drop=True)
    try:
        df.to_parquet(cache_file, index=False)
    except Exception:
        pass
    return df


# ── Combined Dataset ─────────────────────────────────────

async def fetch_full_dataset(symbol="BTCUSDT", interval="15m", days=180):
    """Fetch klines + all available derivatives data, merge into one DataFrame."""
    # Binance derivatives: max ~30 days history regardless of period.
    # Fetch derivatives for last 30 days, use 1h period, then ffill/bfill older klines.
    deriv_days = min(days, 29)
    deriv_period = "1h"
    # Floor resolution for merge
    floor_map = {"5m": "5min", "15m": "15min", "30m": "30min", "60m": "1h", "1h": "1h", "4h": "4h"}
    floor_freq = floor_map.get(interval, "15min")

    results = await asyncio.gather(
        fetch_klines(symbol, interval, days),
        fetch_open_interest(symbol, deriv_period, deriv_days),
        fetch_funding_rate(symbol, deriv_days),
        fetch_long_short_ratio(symbol, deriv_period, deriv_days),
        fetch_taker_volume(symbol, deriv_period, deriv_days),
        fetch_top_ls_ratio(symbol, deriv_period, deriv_days),
        return_exceptions=True,
    )

    df = results[0] if not isinstance(results[0], (Exception, BaseException)) else pd.DataFrame()
    if df.empty:
        return df

    df["_merge_ts"] = df["open_time"].dt.floor(floor_freq)

    labels = ["oi", "funding", "ls", "taker", "topls"]
    for i, (label, extra) in enumerate(zip(labels, results[1:]), 1):
        if isinstance(extra, (Exception, BaseException)) or not isinstance(extra, pd.DataFrame) or extra.empty:
            log.info(f"Skipping {label} data (not available)")
            continue

        extra = extra.copy()
        if "timestamp" not in extra.columns:
            continue

        extra["_merge_ts"] = extra["timestamp"].dt.floor(floor_freq)
        extra = extra.drop(columns=["timestamp"]).drop_duplicates("_merge_ts", keep="last")

        if label == "funding":
            extra = extra.sort_values("_merge_ts")
            df = df.sort_values("_merge_ts")
            df = pd.merge_asof(df, extra, on="_merge_ts", direction="backward")
        else:
            df = df.merge(extra, on="_merge_ts", how="left")

    df = df.drop(columns=["_merge_ts"])

    # Forward-fill sparse derivatives columns
    deriv_cols = [
        "oi", "oi_value", "funding_rate",
        "ls_ratio", "long_account", "short_account",
        "taker_buy_sell_ratio", "taker_buy_vol", "taker_sell_vol",
        "top_ls_ratio", "top_long_account", "top_short_account",
    ]
    for col in deriv_cols:
        if col in df.columns:
            df[col] = df[col].ffill().bfill()

    df = df.sort_values("open_time").reset_index(drop=True)
    avail = [c for c in deriv_cols if c in df.columns and df[c].notna().any()]
    log.info(f"Full dataset: {len(df)} rows, derivatives columns: {avail}")
    return df


# ── Symbol Info ──────────────────────────────────────────

async def fetch_symbols_info():
    async with httpx.AsyncClient(timeout=15) as client:
        resp = await client.get(f"{MEXC_BASE}/ticker/24hr")
        resp.raise_for_status()
        data = resp.json()
    usdt = [d for d in data if d["symbol"].endswith("USDT")]
    usdt.sort(key=lambda d: float(d.get("quoteVolume", 0)), reverse=True)
    return usdt[:50]

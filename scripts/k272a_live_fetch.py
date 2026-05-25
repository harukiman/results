"""
k272a_live_fetch.py — K272a v6.10.1 Live Data Fetcher
=======================================================
Fetches all data sources required for the K272a paper-trade scaffold.
K272a = K198 + K208 + K265 (3-way, K226 DROPPED per K272 validation).

  Component   Data Source
  ──────────  ──────────────────────────────────────────────────────
  K208        Bybit FR (8h settlements) — public REST v5
  K208        HL FR (8h)               — cache/k163_hl/ + HL API live
  K265        HL FR for 35 long-tail symbols — cache/hl_longtail_fr_daily.parquet + HL API
  K265        Bybit FR for K265 symbols (where listed; some HL-only)
  K200        HLP vault balance         — Hyperliquid public API (continued monitor)
  K206        Ethena TVL                — DeFiLlama (for drift context)

  NOT FETCHED (K226 dropped per K272 validation):
  K226        ETH LST staking flows     — removed from production

Output: cache/k272a_live_YYYYMMDD.parquet  (spread panel)
        cache/k272a_live_YYYYMMDD.json     (snapshot metadata)

Usage:
  python3 scripts/k272a_live_fetch.py
  python3 scripts/k272a_live_fetch.py --date 2026-05-25   # specific date
  python3 scripts/k272a_live_fetch.py --force              # re-fetch even if cached today
"""
from __future__ import annotations

import argparse
import json
import math
import time
import warnings
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Optional

import numpy as np
import pandas as pd
import requests

warnings.filterwarnings("ignore")

# ── Paths ──────────────────────────────────────────────────────────────────────
BASE     = Path("/Users/nekonaomichi/crypto-lab")
CACHE    = BASE / "cache"
HL_CACHE = CACHE / "k163_hl"
LOGS     = BASE / "logs"
LOGS.mkdir(exist_ok=True)

# ── K208 reverse carry symbols (10 majors from K196) ──────────────────────────
K208_SYMS = ["SOL", "XRP", "SUI", "OP", "APT", "AXS", "JTO", "IMX", "SAND", "ADA"]

# ── K265 long-tail symbols (35, from cache/hl_longtail_fr_daily.parquet) ──────
# These are ALL symbols present in the hl_longtail_fr_daily.parquet cache.
# K208 majors are excluded by design (K265 is orthogonal).
K265_SYMS = [
    "AAVE", "ARB", "ATOM", "AVAX", "BNB", "BONK", "BTC", "CRV", "DOGE",
    "DOT", "ETH", "FET", "INJ", "LDO", "MKR", "NEAR", "PEPE", "RNDR",
    "SHIB", "SUSHI", "TAO", "UNI", "WIF", "TIA", "JUP", "BOME", "ENA",
    "STRK", "PYTH", "MEME", "WLD", "SEI", "ONDO", "ARK", "BLUR",
]

# Bybit ticker overrides (HL uses kXXX names; Bybit uses 1000XXX)
# These map K265 symbol → Bybit USDT symbol prefix
BYBIT_TICKER_OVERRIDES: Dict[str, str] = {
    "BONK":  "1000BONK",
    "PEPE":  "1000PEPE",
    "SHIB":  "1000SHIB",  # may not be listed; handled gracefully
}

# K265 symbols that exist on HL but NOT on Bybit (HL-only)
# SHIB, PYTH, MEME, ARK, BLUR are HL-only based on cache survey
HL_ONLY_K265 = {"SHIB", "PYTH", "MEME", "ARK", "BLUR"}

# HL API
HL_API_URL  = "https://api.hyperliquid.xyz/info"
# Bybit public REST v5 — no auth needed
BYBIT_FR_URL = "https://api.bybit.com/v5/market/funding/history"
# Ethena TVL
ETHENA_URL  = "https://api.llama.fi/protocol/ethena"
# HLP vault
HLP_ADDRESS = "0xdfc24b077bc1425ad1dea75bcb6f8158e10df303"


# ─────────────────────────────────────────────────────────────────────────────
# 1. Bybit FR helpers
# ─────────────────────────────────────────────────────────────────────────────

def fetch_bybit_fr_recent(sym: str, limit: int = 200) -> pd.Series:
    """Fetch recent Bybit funding rate history for one symbol. Free endpoint."""
    ticker_sym = BYBIT_TICKER_OVERRIDES.get(sym, sym)
    params = {
        "category": "linear",
        "symbol": f"{ticker_sym}USDT",
        "limit": limit,
    }
    try:
        resp = requests.get(BYBIT_FR_URL, params=params, timeout=15)
        resp.raise_for_status()
        data = resp.json()
        if data.get("retCode") != 0:
            print(f"  [bybit] {sym}: API error {data.get('retMsg')}")
            return pd.Series(dtype=float, name=sym)
        rows = data["result"]["list"]
        records = []
        for r in rows:
            ts = pd.Timestamp(int(r["fundingRateTimestamp"]), unit="ms", tz="UTC")
            records.append({"timestamp": ts, "bybit_fr": float(r["fundingRate"])})
        if not records:
            return pd.Series(dtype=float, name=sym)
        df = pd.DataFrame(records).set_index("timestamp").sort_index()
        s = df["bybit_fr"]
        s.name = sym
        return s
    except Exception as e:
        print(f"  [bybit] {sym}: FAILED → {e}")
        return pd.Series(dtype=float, name=sym)


def load_bybit_fr_cached(sym: str) -> pd.Series:
    """Load Bybit FR from local parquet cache. Tries multiple tag suffixes."""
    ticker_sym = BYBIT_TICKER_OVERRIDES.get(sym, sym)
    for tag in ("730d", "1200d", "365d", "135d", "180d"):
        f = CACHE / f"bybit_fr_{ticker_sym}USDT_{tag}.parquet"
        if f.exists():
            df = pd.read_parquet(f)
            col = "funding_rate" if "funding_rate" in df.columns else df.columns[0]
            if "timestamp" in df.columns:
                df = df.set_index("timestamp")
            s = df[col].astype(float).sort_index()
            s = s[~s.index.duplicated(keep="last")]
            s.name = sym
            return s
    return pd.Series(dtype=float, name=sym)


def _normalize_tz(s: pd.Series) -> pd.Series:
    """Ensure Series index is tz-aware UTC."""
    if s.empty:
        return s
    if s.index.tz is None:
        return s.tz_localize("UTC")
    return s.tz_convert("UTC")


def get_bybit_fr(sym: str) -> pd.Series:
    """Merge cached historical + fresh live Bybit FR for a symbol."""
    hist = _normalize_tz(load_bybit_fr_cached(sym))
    live = _normalize_tz(fetch_bybit_fr_recent(sym, limit=200))
    if hist.empty and live.empty:
        return pd.Series(dtype=float, name=sym)
    combined = pd.concat([hist, live])
    combined = combined[~combined.index.duplicated(keep="last")].sort_index()
    combined.name = sym
    return combined


# ─────────────────────────────────────────────────────────────────────────────
# 2. Hyperliquid FR helpers
# ─────────────────────────────────────────────────────────────────────────────

# HL name overrides (HL uses kXXX for small-cap meme tokens)
HL_TICKER_MAP: Dict[str, str] = {
    "PEPE":  "kPEPE",
    "BONK":  "kBONK",
    "SHIB":  "kSHIB",
    "FLOKI": "kFLOKI",
}


def fetch_hl_fr_live_point(sym: str) -> pd.Series:
    """
    Fetch the current HL funding rate (single live point) via metaAndAssetCtxs.
    This supplements the historical cache with the latest 8h event.
    """
    hl_sym = HL_TICKER_MAP.get(sym, sym)
    try:
        payload = {"type": "metaAndAssetCtxs"}
        resp = requests.post(HL_API_URL, json=payload, timeout=15)
        resp.raise_for_status()
        data = resp.json()
        meta      = data[0]
        assetCtxs = data[1]
        universe = {item["name"]: i for i, item in enumerate(meta["universe"])}
        if hl_sym not in universe:
            return pd.Series(dtype=float, name=sym)
        idx = universe[hl_sym]
        ctx = assetCtxs[idx]
        fr_8h = float(ctx.get("funding", 0.0))
        ts = pd.Timestamp.now(tz="UTC").floor("8h")
        s = pd.Series({ts: fr_8h}, name=sym)
        s.index.name = "timestamp"
        return s
    except Exception as e:
        print(f"  [hl_live] {sym}: FAILED → {e}")
        return pd.Series(dtype=float, name=sym)


def fetch_hl_fr_history_page(coin: str, start_ms: int, end_ms: int) -> List[Dict]:
    """Fetch one page of HL funding history via fundingHistory endpoint."""
    payload = {"type": "fundingHistory", "coin": coin,
               "startTime": start_ms, "endTime": end_ms}
    try:
        resp = requests.post(HL_API_URL, json=payload, timeout=30)
        resp.raise_for_status()
        data = resp.json()
        return data if isinstance(data, list) else []
    except Exception as e:
        print(f"    [hl_hist_page] {coin}: {e}")
        return []


def fetch_hl_fr_history(sym: str, days: int = 30) -> pd.Series:
    """
    Fetch recent HL FR history (last `days` days) via paged fundingHistory.
    Used to refresh longtail cache without a full re-download.
    Returns hourly FR series.
    """
    hl_sym = HL_TICKER_MAP.get(sym, sym)
    now_ms   = int(time.time() * 1000)
    start_ms = now_ms - days * 86400 * 1000
    all_events: List[Dict] = []
    page_start = start_ms

    while page_start < now_ms:
        events = fetch_hl_fr_history_page(hl_sym, page_start, now_ms)
        if not events:
            break
        all_events.extend(events)
        last_t = max(e.get("time", 0) for e in events)
        if last_t <= page_start or len(events) < 500:
            break
        page_start = last_t + 1
        time.sleep(0.5)  # be polite

    if not all_events:
        return pd.Series(dtype=float, name=sym)

    df = pd.DataFrame(all_events)
    df["timestamp"] = pd.to_datetime(df["time"], unit="ms", utc=True)
    df["hl_fr"]     = df["fundingRate"].astype(float)
    df = df[["timestamp", "hl_fr"]].drop_duplicates("timestamp").sort_values("timestamp")
    s = df.set_index("timestamp")["hl_fr"]
    s.index = s.index.tz_localize(None)  # match cache format
    s.name = sym
    return s


def load_hl_fr_cached(sym: str) -> pd.Series:
    """Load HL FR from cache/k163_hl/ parquet (hourly events)."""
    f = HL_CACHE / f"hl_fr_{sym}.parquet"
    if not f.exists():
        return pd.Series(dtype=float, name=sym)
    df = pd.read_parquet(f)
    col = "hl_fr" if "hl_fr" in df.columns else df.columns[0]
    if "timestamp" in df.columns:
        df = df.set_index("timestamp")
    s = df[col].astype(float).sort_index()
    s = s[~s.index.duplicated(keep="last")]
    s.name = sym
    return s


def get_hl_fr(sym: str) -> pd.Series:
    """
    Get HL FR for a symbol: cached historical + live single point.
    Result is hourly-resolution, tz-naive (UTC).
    """
    hist = load_hl_fr_cached(sym)
    live = fetch_hl_fr_live_point(sym)
    live_tz_naive = live.copy()
    if not live_tz_naive.empty and live_tz_naive.index.tz is not None:
        live_tz_naive.index = live_tz_naive.index.tz_localize(None)

    if hist.empty and live_tz_naive.empty:
        return pd.Series(dtype=float, name=sym)
    combined = pd.concat([hist, live_tz_naive])
    combined = combined[~combined.index.duplicated(keep="last")].sort_index()
    combined.name = sym
    return combined


# ─────────────────────────────────────────────────────────────────────────────
# 3. K265 Long-Tail HL FR panel refresh
# ─────────────────────────────────────────────────────────────────────────────

def refresh_k265_longtail_panel(force_days: int = 7) -> pd.DataFrame:
    """
    Refresh hl_longtail_fr_daily.parquet with recent data.

    Strategy:
      1. Load existing parquet cache (733 rows × 35 columns)
      2. For each K265 symbol: fetch last `force_days` days from HL API
      3. Aggregate new hourly events to daily mean
      4. Append to existing panel, dedup, save back to parquet
      5. Return merged panel
    """
    parquet_path = CACHE / "hl_longtail_fr_daily.parquet"
    print(f"\n  [K265] Refreshing longtail panel ({len(K265_SYMS)} symbols)...")

    # Load existing cache
    if parquet_path.exists():
        panel = pd.read_parquet(parquet_path)
        panel.index = pd.to_datetime(panel.index)
        last_date = panel.index.max()
        today = pd.Timestamp.utcnow().normalize().tz_localize(None)
        days_stale = (today - last_date).days
        print(f"  [K265] Existing panel: {panel.shape}, last date: {last_date.date()}, "
              f"staleness: {days_stale}d")
        # Only re-fetch if stale
        refresh_days = max(force_days, days_stale + 1)
    else:
        print("  [K265] No existing longtail parquet. Building fresh.")
        panel = pd.DataFrame()
        refresh_days = 60  # fetch 60d if starting fresh

    updates: Dict[str, pd.Series] = {}
    for sym in K265_SYMS:
        try:
            # Fetch recent history from HL API
            raw_hourly = fetch_hl_fr_history(sym, days=refresh_days)
            if raw_hourly.empty:
                print(f"    {sym}: no new data from API, using cache only")
                continue
            # Aggregate to daily mean
            daily_new = (raw_hourly
                         .groupby(pd.Grouper(freq="D"))
                         .mean()
                         .rename(sym))
            daily_new.index = daily_new.index.normalize()
            updates[sym] = daily_new
            time.sleep(0.3)  # rate-limit HL API
        except Exception as e:
            print(f"    {sym}: error {e}")
            continue

    if not updates:
        print("  [K265] No updates fetched. Using existing panel.")
        return panel

    # Merge updates into existing panel
    new_df = pd.DataFrame(updates)
    if panel.empty:
        merged = new_df.sort_index()
    else:
        merged = pd.concat([panel, new_df])
        merged = merged.groupby(merged.index).last()  # take latest per date
        merged = merged.sort_index()

    merged.to_parquet(parquet_path)
    print(f"  [K265] Panel refreshed → {merged.shape}  ({parquet_path})")
    return merged


def get_k265_daily_panel(refresh: bool = True) -> pd.DataFrame:
    """Load K265 longtail daily FR panel, optionally refreshing from HL API."""
    if refresh:
        return refresh_k265_longtail_panel(force_days=3)
    parquet_path = CACHE / "hl_longtail_fr_daily.parquet"
    if parquet_path.exists():
        df = pd.read_parquet(parquet_path)
        df.index = pd.to_datetime(df.index)
        return df
    return pd.DataFrame()


# ─────────────────────────────────────────────────────────────────────────────
# 4. K208 spread computation
# ─────────────────────────────────────────────────────────────────────────────

def compute_k208_spreads() -> Dict:
    """
    For each K208 symbol compute:
      - latest bybit_fr, hl_fr_8h
      - spread = bybit_fr - hl_fr_8h
      - 7d and 30d rolling mean of spread
    Returns dict of per-symbol live stats.
    """
    bybit_latest:    Dict[str, float] = {}
    hl_latest:       Dict[str, float] = {}
    spread_latest:   Dict[str, float] = {}
    spread_7d_mean:  Dict[str, float] = {}
    spread_30d_mean: Dict[str, float] = {}
    compression:     Dict[str, str]   = {}

    print("  [K208] Fetching per-symbol FR data...")
    for sym in K208_SYMS:
        by = get_bybit_fr(sym)
        hl = get_hl_fr(sym)
        bybit_latest[sym] = float(by.iloc[-1]) if not by.empty else np.nan
        hl_latest[sym]    = float(hl.iloc[-1]) if not hl.empty else np.nan

        # Resample HL to 8h sums aligned to Bybit timestamps
        if not by.empty and not hl.empty:
            by_tz = _normalize_tz(by)
            hl_8h = _normalize_tz(hl).resample("8h", label="right", closed="right").sum(min_count=1)
            sp = by_tz - hl_8h.reindex(by_tz.index)
            sp = sp.dropna()
            spread_latest[sym]   = float(sp.iloc[-1])   if not sp.empty else np.nan
            spread_7d_mean[sym]  = float(sp.tail(21).mean()) if not sp.empty else np.nan   # 3×7d
            spread_30d_mean[sym] = float(sp.tail(90).mean()) if not sp.empty else np.nan   # 3×30d
            # Compression flag
            m7, m30 = spread_7d_mean[sym], spread_30d_mean[sym]
            if not math.isnan(m7) and not math.isnan(m30) and abs(m30) > 1e-9:
                ratio = m7 / (m30 + 1e-12)
                compression[sym] = "COMPRESSED" if ratio < 0.75 else "NORMAL"
            else:
                compression[sym] = "UNKNOWN"
        else:
            spread_latest[sym]   = np.nan
            spread_7d_mean[sym]  = np.nan
            spread_30d_mean[sym] = np.nan
            compression[sym]     = "UNKNOWN"

    return {
        "bybit_fr_latest":     bybit_latest,
        "hl_fr_latest":        hl_latest,
        "spread_latest":       spread_latest,
        "spread_7d_mean":      spread_7d_mean,
        "spread_30d_mean":     spread_30d_mean,
        "spread_compression":  compression,
    }


# ─────────────────────────────────────────────────────────────────────────────
# 5. K265 live stats (universe liquidity check)
# ─────────────────────────────────────────────────────────────────────────────

def compute_k265_stats(panel: pd.DataFrame) -> Dict:
    """
    Compute current K265 signal state from the daily FR panel.
    Returns per-symbol FR statistics and current quartile assignments.
    """
    if panel.empty:
        return {"error": "K265 panel empty"}

    # Use last 14d mean as the current signal (K265 logic: 14d rolling)
    recent = panel.tail(14)
    if len(recent) < 7:
        return {"error": f"K265 panel too short ({len(recent)} days)"}

    sig_today = recent.mean()  # 14d mean per symbol
    n_sym = sig_today.dropna().shape[0]
    n_q   = max(1, int(n_sym * 0.25))
    ranked = sig_today.rank(ascending=True)

    long_syms  = ranked[ranked <= n_q].index.tolist()
    short_syms = ranked[ranked > n_sym - n_q].index.tolist()

    # Liquidity check: flag symbols where last 7d daily data is NaN-heavy
    daily_coverage = panel.tail(7).notna().mean()
    low_liq = daily_coverage[daily_coverage < 0.7].index.tolist()

    return {
        "n_symbols":      n_sym,
        "signal_14d_mean":  {sym: round(float(v), 8) for sym, v in sig_today.dropna().items()},
        "long_sleeve":    long_syms,
        "short_sleeve":   short_syms,
        "low_liquidity":  low_liq,
        "panel_last_date": str(panel.index[-1].date()),
        "panel_n_days":   len(panel),
    }


# ─────────────────────────────────────────────────────────────────────────────
# 6. HLP Balance (K200 monitor continued)
# ─────────────────────────────────────────────────────────────────────────────

def get_hlp_balance() -> Dict:
    """Fetch HLP vault balance; return dict with latest value and 7d change."""
    cache_path = CACHE / "hlp_balance_daily.parquet"

    if cache_path.exists():
        age = time.time() - cache_path.stat().st_mtime
        if age < 23 * 3600:
            print("  [hlp] Loading cached HLP balance")
            df = pd.read_parquet(cache_path)
            col = [c for c in df.columns if "balance" in c.lower()]
            col = col[0] if col else df.columns[0]
            s = df[col].squeeze()
            return _hlp_to_dict(s)

    print("  [hlp] Fetching HLP vault balance from HL API...")
    try:
        payload = {"type": "vaultDetails", "vaultAddress": HLP_ADDRESS}
        resp = requests.post(HL_API_URL, json=payload, timeout=20)
        resp.raise_for_status()
        raw = resp.json()
        portfolio = {entry[0]: entry[1] for entry in raw.get("portfolio", [])}
        hist = portfolio.get("allTime", {}).get("accountValueHistory", [])
        records = {}
        for ts_ms, val in hist:
            dt = pd.Timestamp(ts_ms, unit="ms", tz="UTC").normalize().tz_localize(None)
            records[dt] = float(val)
        if not records:
            return {"error": "no HLP data"}
        s = pd.Series(records, name="total_balance_usd").sort_index()
        s = s[~s.index.duplicated(keep="last")]
        # Update cache
        if cache_path.exists():
            existing = pd.read_parquet(cache_path)
            col = [c for c in existing.columns if "balance" in c.lower()]
            col = col[0] if col else existing.columns[0]
            combined = pd.concat([existing[col].squeeze(), s])
            combined = combined[~combined.index.duplicated(keep="last")].sort_index()
            combined.to_frame(name="total_balance_usd").to_parquet(cache_path)
        else:
            s.to_frame().to_parquet(cache_path)
        return _hlp_to_dict(s)
    except Exception as e:
        print(f"  [hlp] FAILED → {e}")
        if cache_path.exists():
            df = pd.read_parquet(cache_path)
            col = [c for c in df.columns if "balance" in c.lower()]
            col = col[0] if col else df.columns[0]
            return _hlp_to_dict(df[col].squeeze())
        return {"error": str(e)}


def _hlp_to_dict(s: pd.Series) -> Dict:
    out = {}
    if s.empty:
        return out
    out["balance_usd"] = float(s.iloc[-1])
    if len(s) >= 7:
        out["7d_change_pct"] = float((s.iloc[-1] / s.iloc[-7] - 1) * 100)
    if len(s) >= 30:
        out["30d_change_pct"] = float((s.iloc[-1] / s.iloc[-30] - 1) * 100)
    # Alert flag
    pct7 = out.get("7d_change_pct", 0.0)
    if pct7 < -40.0:
        out["alert"] = "HALT"
    elif pct7 < -20.0:
        out["alert"] = "REDUCE"
    else:
        out["alert"] = "OK"
    return out


# ─────────────────────────────────────────────────────────────────────────────
# 7. Ethena TVL (context monitor)
# ─────────────────────────────────────────────────────────────────────────────

def get_ethena_tvl() -> Dict:
    """Fetch Ethena TVL from DeFiLlama for drift context."""
    cache_path = CACHE / "ethena_tvl_daily.parquet"
    if cache_path.exists():
        age = time.time() - cache_path.stat().st_mtime
        if age < 23 * 3600:
            print("  [ethena] Loading cached TVL")
            df = pd.read_parquet(cache_path)
            col = "tvl" if "tvl" in df.columns else df.columns[0]
            return _tvl_series_to_dict(df[col].squeeze())

    print("  [ethena] Fetching TVL from DeFiLlama...")
    try:
        resp = requests.get(ETHENA_URL, headers={"User-Agent": "Mozilla/5.0"}, timeout=20)
        resp.raise_for_status()
        data = resp.json()
        tvl_hist = data.get("tvl", [])
        records = {}
        for entry in tvl_hist:
            ts = pd.Timestamp(int(entry["date"]), unit="s", tz="UTC").normalize().tz_localize(None)
            records[ts] = float(entry["totalLiquidityUSD"])
        s = pd.Series(records, name="tvl").sort_index()
        s.to_frame().to_parquet(cache_path)
        return _tvl_series_to_dict(s)
    except Exception as e:
        print(f"  [ethena] FAILED → {e}")
        if cache_path.exists():
            df = pd.read_parquet(cache_path)
            col = "tvl" if "tvl" in df.columns else df.columns[0]
            return _tvl_series_to_dict(df[col].squeeze())
        return {"error": str(e)}


def _tvl_series_to_dict(s: pd.Series) -> Dict:
    out = {}
    if s.empty:
        return out
    out["tvl_usd"] = float(s.iloc[-1])
    if len(s) >= 7:
        out["7d_change_pct"]  = float((s.iloc[-1] / s.iloc[-7]  - 1) * 100)
    if len(s) >= 30:
        out["30d_change_pct"] = float((s.iloc[-1] / s.iloc[-30] - 1) * 100)
    return out


# ─────────────────────────────────────────────────────────────────────────────
# 8. Build and save snapshot
# ─────────────────────────────────────────────────────────────────────────────

def build_snapshot(date_str: str, refresh_k265: bool = True) -> Dict:
    """Assemble all K272a live data into a snapshot. Returns metadata dict."""
    print(f"\n=== K272a Live Fetch — {date_str} ===\n")
    t0 = time.time()

    # ── K208 spreads ──────────────────────────────────────────────────────────
    print("Fetching K208 (major CEX-DEX spread) data...")
    k208_data = compute_k208_spreads()

    # ── K265 longtail panel ───────────────────────────────────────────────────
    print("\nFetching K265 (HL longtail FR) panel...")
    k265_panel = get_k265_daily_panel(refresh=refresh_k265)
    k265_stats = compute_k265_stats(k265_panel)

    # ── HLP balance (K200 monitor) ────────────────────────────────────────────
    print("\nFetching HLP balance...")
    hlp_data = get_hlp_balance()

    # ── Ethena TVL ────────────────────────────────────────────────────────────
    print("\nFetching Ethena TVL...")
    ethena_data = get_ethena_tvl()

    elapsed = time.time() - t0

    # ── Assemble snapshot ────────────────────────────────────────────────────
    snapshot = {
        "fetch_date":     date_str,
        "fetch_ts_utc":   datetime.now(timezone.utc).isoformat(),
        "elapsed_sec":    round(elapsed, 1),
        "architecture":   "K272a v6.10.1 (K198+K208+K265 3-way, K226 dropped)",
        "k208":           k208_data,
        "k265":           k265_stats,
        "hlp_balance":    hlp_data,
        "hlp_alert":      hlp_data.get("alert", "OK"),
        "ethena_tvl":     ethena_data,
    }

    # ── Save JSON snapshot ────────────────────────────────────────────────────
    json_path = CACHE / f"k272a_live_{date_str.replace('-', '')}.json"
    with open(json_path, "w") as f:
        class NaNSafe(json.JSONEncoder):
            def default(self, obj):
                if isinstance(obj, float) and math.isnan(obj):
                    return None
                if isinstance(obj, np.floating):
                    return None if math.isnan(float(obj)) else float(obj)
                if isinstance(obj, np.integer):
                    return int(obj)
                return super().default(obj)
        # Pre-sanitize nested floats
        import copy
        def sanitize(v):
            if isinstance(v, float) and math.isnan(v):
                return None
            if isinstance(v, dict):
                return {kk: sanitize(vv) for kk, vv in v.items()}
            if isinstance(v, list):
                return [sanitize(x) for x in v]
            return v
        f.write(json.dumps(sanitize(snapshot), indent=2, cls=NaNSafe))
    print(f"\n  Saved snapshot JSON: {json_path}")

    # ── Save K265 spread panel parquet ────────────────────────────────────────
    if not k265_panel.empty:
        parquet_path = CACHE / f"k272a_live_{date_str.replace('-', '')}.parquet"
        k265_panel.to_parquet(parquet_path)
        print(f"  Saved K265 panel: {parquet_path}")
        snapshot["parquet_path"] = str(parquet_path)
    else:
        print("  WARNING: K265 panel empty, parquet not saved")
        snapshot["parquet_path"] = None

    return snapshot


# ─────────────────────────────────────────────────────────────────────────────
# CLI Entry Point
# ─────────────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="K272a v6.10.1 Live Data Fetcher")
    parser.add_argument("--date",        default=None,  help="Date override YYYY-MM-DD")
    parser.add_argument("--force",       action="store_true", help="Force re-fetch even if cached today")
    parser.add_argument("--no-refresh",  action="store_true", help="Skip HL API refresh for K265 panel")
    args = parser.parse_args()

    date_str = args.date or datetime.now(timezone.utc).strftime("%Y-%m-%d")

    # Skip if already fetched today (unless --force)
    json_path = CACHE / f"k272a_live_{date_str.replace('-', '')}.json"
    if json_path.exists() and not args.force:
        print(f"Already fetched for {date_str}. Use --force to re-fetch.")
        return

    snapshot = build_snapshot(date_str, refresh_k265=not args.no_refresh)
    print(f"\n=== Fetch complete in {snapshot['elapsed_sec']}s ===")
    print(f"  HLP alert:      {snapshot.get('hlp_alert', 'N/A')}")
    print(f"  K265 symbols:   {snapshot['k265'].get('n_symbols', 'N/A')}")
    print(f"  K265 long:      {snapshot['k265'].get('long_sleeve', [])}")
    print(f"  K265 short:     {snapshot['k265'].get('short_sleeve', [])}")
    if snapshot['k265'].get('low_liquidity'):
        print(f"  K265 low-liq:   {snapshot['k265']['low_liquidity']}")


if __name__ == "__main__":
    main()

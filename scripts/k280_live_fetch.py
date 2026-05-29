"""
k280_live_fetch.py — K280 v6.10.2 Live Data Fetcher
=====================================================
Fetches all data sources required for the K280 paper-trade scaffold.
K280 = K198 + K208 + K276b_top20 (3-way, K265 → K276b_top20 upgrade per K280 validation).

  Component   Data Source
  ──────────  ──────────────────────────────────────────────────────
  K208        Bybit FR (8h settlements) — public REST v5
  K208        HL FR (8h)               — cache/k163_hl/ + HL API live
  K276b       HL FR for 20 top-selected symbols — cache/hl_k276b_fr_daily.parquet + HL API
  K276b       Bybit FR for K276b symbols (where listed; MEME, PYTH are HL-only)
  K200        HLP vault balance         — Hyperliquid public API (continued monitor)
  K206        Ethena TVL                — DeFiLlama (for drift context)

  NOT FETCHED vs K272a (K274 scaffold):
  K265        35-symbol longtail       — replaced by K276b_top20 (better Sharpe +8.78)
  ARK, BLUR, STRK, ARB, SUSHI         — dropped (not in K276b_top20)
  + 10 other minor K265 symbols       — dropped (AVAX, BNB, CRV, DOGE, INJ, NEAR, SHIB, WIF, BTC, ETH)

  Added vs K272a (K274 scaffold):
  JUP, UNI, BOME, DOT, BONK           — new K276b symbols (HL public API)

K276b_top20 symbols (20): ENA, ONDO, ATOM, TIA, SEI, WLD, RNDR, TAO, MEME, AAVE,
                           PYTH, LDO, FET, PEPE, MKR, JUP, UNI, BOME, DOT, BONK

Output: cache/k280_live_YYYYMMDD.parquet  (spread panel)
        cache/k280_live_YYYYMMDD.json     (snapshot metadata)

Usage:
  python3 scripts/k280_live_fetch.py
  python3 scripts/k280_live_fetch.py --date 2026-05-25   # specific date
  python3 scripts/k280_live_fetch.py --force              # re-fetch even if cached today
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
BASE     = Path(__file__).resolve().parent.parent
CACHE    = BASE / "cache"
HL_CACHE = CACHE / "k163_hl"
LOGS     = BASE / "logs"
LOGS.mkdir(exist_ok=True)

# ── K208 reverse carry symbols (10 majors from K196) — UNCHANGED ──────────────
K208_SYMS = ["SOL", "XRP", "SUI", "OP", "APT", "AXS", "JTO", "IMX", "SAND", "ADA"]

# ── K276b_top20 symbols (20, upgraded from K265's 35 longtail) ────────────────
# Selected via K276/K280 optimization: higher Sharpe (+8.78 vs K265 on same window)
# Removed vs K265: ARK, BLUR, STRK, ARB, SUSHI, AVAX, BNB, CRV, DOGE, INJ, NEAR, SHIB, WIF, BTC, ETH
# Added vs K265: JUP, UNI, BOME, DOT, BONK
K276B_SYMS = [
    "ENA", "ONDO", "ATOM", "TIA", "SEI", "WLD", "RNDR", "TAO", "MEME",
    "AAVE", "PYTH", "LDO", "FET", "PEPE", "MKR", "JUP", "UNI", "BOME",
    "DOT", "BONK",
]

# Bybit ticker overrides (HL uses kXXX names; Bybit uses 1000XXX)
BYBIT_TICKER_OVERRIDES: Dict[str, str] = {
    "BONK":  "1000BONK",
    "PEPE":  "1000PEPE",
    "MEME":  "1000MEME",  # if listed on Bybit
}

# K276b symbols that exist on HL but NOT on Bybit (HL-only)
# MEME and PYTH are HL-only based on K272a cache survey
HL_ONLY_K276B = {"MEME", "PYTH"}

# ── K370: Builder Code Self-Rebate (AX-01 from K368) ─────────────────────────
# HyperLiquid allows builders to receive a fee on fills they send on behalf of
# a user. By registering as a self-builder, the trading wallet captures
# referral-style rewards on its own order volume.
#
# MECHANISM (from HL docs, verified 2026-05-27):
#   1. User approves max fee rate for a builder via approveBuilderFee on-chain action
#      (signed by main wallet, NOT agent/API wallet; max 10 active approvals).
#   2. Builder includes {"b": address, "f": fee_tenths_of_bp} in every order.
#      "f" is an ADDITIONAL fee charged to the user, not deducted from HL taker fee.
#   3. Builder claims accumulated fees via the referral reward claim process.
#   4. SELF-REBATE MODE: set f=0 (zero extra cost to user). Builder still
#      accumulates referral pool rewards on own volume.
#   5. Builder eligibility: ≥100 USDC in perps account. No volume threshold found.
#   6. Max builder fee caps: 0.1% perps, 1% spot. Activation: immediate (no epoch delay).
#
# IMPORTANT CLARIFICATION vs K368 "$82,800/yr" estimate:
#   K368 assumed 50% direct rebate on taker fee (4.5bp × 50% = 2.25bp savings).
#   Actual mechanism: builder earns referral-pool rewards, not direct fee reduction.
#   Revised estimate: ~$5,000–$40,000/yr at $10M AUM (TBD; claim data needed).
#   Net benefit is still FREE MONEY with ZERO execution risk if f=0.
#
# ACTIVATION (user action required — this wave does NOT execute on-chain):
#   Step 1: Register builder wallet on HL (docs/k302a_runbook.md §15)
#   Step 2: export HL_BUILDER_WALLET=0x<your_wallet>
#   Step 3: Set BUILDER_CODE_ENABLED = True below
#   Step 4: Verify live orders include builder field via HL clearinghouse
#
# ORDER API FORMAT (when integrating into live order submission):
#   order_action["builder"] = {"b": BUILDER_WALLET_ADDRESS, "f": BUILDER_FEE_F}
import os as _os
BUILDER_CODE_ENABLED   = False                           # K370 AX-01: True after user registers
BUILDER_WALLET_ADDRESS = _os.environ.get("HL_BUILDER_WALLET", "")   # registered HL wallet
BUILDER_FEE_F          = 0             # tenths of bp extra cost to user (0 = self-rebate, free)

# ── K430: Leverage application (additive — LEVERAGE=1.0 at default PAPER_TRADE) ─
# Import leverage_manager from same scripts/ directory.
# At default phase (PAPER_TRADE), LEVERAGE=1.0 → behaviour UNCHANGED.
# User advances phase via: python3 scripts/leverage_manager.py --advance
try:
    import sys as _sys_lev
    _sys_lev.path.insert(0, str(Path(__file__).resolve().parent))
    from leverage_manager import (
        get_current_leverage   as _get_leverage,
        compute_margin_required as _compute_margin,
        check_margin_health    as _check_margin_health,
    )
    LEVERAGE = _get_leverage()
    _LEVERAGE_ENABLED = True
except Exception as _lev_err:
    print(f"  [K430] leverage_manager import failed ({_lev_err}) — defaulting to 1x")
    LEVERAGE = 1.0
    _LEVERAGE_ENABLED = False

MAX_MARGIN_PCT = 0.80   # refuse trade if portfolio margin > 80% AUM (K430 circuit breaker)

# ── K434: Smart Router (cross-venue HL/Bybit/OKX routing for K208 trades) ────
# select_best_venue() returns the optimal venue for each K208 trade based on:
#   - current FR spread across venues
#   - maker rebate tier (HL GOLD, Bybit VIP5, OKX VIP1)
#   - slippage estimate from top-of-book depth
#   - concentration caps (K355 risk limits)
#
# CALL SITE SCAFFOLD (K434 Phase 8 — production wiring not yet active):
#   from smart_router import select_best_venue
#   chosen = select_best_venue(
#       symbol="BTC", side="short", position_size_usd=position_usd
#   )
#   venue = chosen["venue"]   # "HL" | "Bybit" | "OKX"
#   # → use venue-specific order submission (HL or Bybit API)
#
# ACTIVATION: set SMART_ROUTER_ENABLED = True after live testing confirms
#   1. FR snapshots fetch correctly from all 3 venues
#   2. Scoring produces expected rankings for known symbols
#   3. Concentration caps enforced correctly
#   4. Dashboard JSON written to data/smart_router_dashboard.json
SMART_ROUTER_ENABLED = False   # K434: set True after testing; scaffold only in this wave
try:
    import sys as _sys_sr
    _sys_sr.path.insert(0, str(Path(__file__).resolve().parent))
    from smart_router import select_best_venue as _select_best_venue
    _SMART_ROUTER_AVAILABLE = True
except Exception as _sr_err:
    _SMART_ROUTER_AVAILABLE = False
    print(f"  [K434] smart_router import failed ({_sr_err}) — K208 routing unchanged")

# ── K439: POST_ONLY Order Manager (K208 trade submission hook) ────────────────
# K434 chooses venue → K439 chooses order type (POST_ONLY first, IOC fallback).
# Default: POST_ONLY_ENABLED=True; daemons currently paper-trade so no actual orders.
# CALL SITE SCAFFOLD (K439 Phase 5 — production wiring not yet active):
#   from post_only_order_manager import execute_trade as _post_only_execute
#   result = _post_only_execute(venue=venue, symbol=symbol, side=side,
#                               size=position_usd, urgency="LOW")
#   venue = result["venue"]  # "HL" | "Bybit" | "OKX"
# ACTIVATION: POST_ONLY_ENABLED is True by default in post_only_order_manager.py.
#   Live wiring requires exchange adapter implementation (K439 Phase 1 scaffolded).
POST_ONLY_ORDER_ENABLED = True   # K439: set False to bypass POST_ONLY for K208 trades
try:
    import sys as _sys_po
    _sys_po.path.insert(0, str(Path(__file__).resolve().parent))
    from post_only_order_manager import execute_trade as _post_only_execute
    _POST_ONLY_AVAILABLE = True
except Exception as _po_err:
    _POST_ONLY_AVAILABLE = False
    print(f"  [K439] post_only_order_manager import failed ({_po_err}) — K208 orders unchanged")


def get_k208_venue(symbol: str, side: str, position_usd: float) -> str:
    """
    K434 Phase 8 call site: returns best venue for a K208 trade.
    Falls back to "HL" if smart router is disabled or unavailable.

    Args:
        symbol:        K208 symbol (e.g. "SOL", "BTC")
        side:          "short" or "long"
        position_usd:  notional position size in USD

    Returns:
        venue string: "HL" | "Bybit" | "OKX"
    """
    if SMART_ROUTER_ENABLED and _SMART_ROUTER_AVAILABLE:
        try:
            result = _select_best_venue(symbol=symbol, side=side, position_size_usd=position_usd)
            venue  = result.get("venue", "HL")
            score  = result.get("score", 0.0)
            print(f"  [K434] SmartRouter → {symbol} {side}: venue={venue} score={score:+.8f}")
            return venue
        except Exception as _sr_exc:
            print(f"  [K434] SmartRouter error ({_sr_exc}) — defaulting to HL")
    return "HL"   # default: HL (unchanged K208 behavior)


# HL API
HL_API_URL   = "https://api.hyperliquid.xyz/info"
# Bybit public REST v5 — no auth needed
BYBIT_FR_URL = "https://api.bybit.com/v5/market/funding/history"
# Ethena TVL
ETHENA_URL   = "https://api.llama.fi/protocol/ethena"
# HLP vault
HLP_ADDRESS  = "0xdfc24b077bc1425ad1dea75bcb6f8158e10df303"


# ─────────────────────────────────────────────────────────────────────────────
# 1. Bybit FR helpers (unchanged from K272a)
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
# 2. Hyperliquid FR helpers (unchanged from K272a)
# ─────────────────────────────────────────────────────────────────────────────

# HL name overrides (HL uses kXXX for small-cap meme tokens)
HL_TICKER_MAP: Dict[str, str] = {
    "PEPE":  "kPEPE",
    "BONK":  "kBONK",
    "MEME":  "kMEME",
    "BOME":  "kBOME",
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
    Used to refresh K276b cache without a full re-download.
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
# 3. K276b HL FR panel refresh (replaces K265 longtail panel from K272a)
# ─────────────────────────────────────────────────────────────────────────────

def refresh_k276b_panel(force_days: int = 7) -> pd.DataFrame:
    """
    Refresh hl_k276b_fr_daily.parquet with recent data.
    Uses K276b_top20 (20 symbols) instead of K265's 35-symbol longtail.

    Strategy:
      1. Load existing parquet cache
      2. For each K276b symbol: fetch last `force_days` days from HL API
      3. Aggregate new hourly events to daily mean
      4. Append to existing panel, dedup, save back to parquet
      5. Return merged panel

    Note: Also checks hl_longtail_fr_daily.parquet (K265 cache) for overlapping
    symbols to minimize redundant API calls.
    """
    parquet_path      = CACHE / "hl_k276b_fr_daily.parquet"
    k265_parquet_path = CACHE / "hl_longtail_fr_daily.parquet"
    print(f"\n  [K276b] Refreshing K276b_top20 panel ({len(K276B_SYMS)} symbols)...")

    # Load existing K276b cache
    if parquet_path.exists():
        panel = pd.read_parquet(parquet_path)
        panel.index = pd.to_datetime(panel.index)
        last_date = panel.index.max()
        today = pd.Timestamp.utcnow().normalize().tz_localize(None)
        days_stale = (today - last_date).days
        print(f"  [K276b] Existing panel: {panel.shape}, last date: {last_date.date()}, "
              f"staleness: {days_stale}d")
        refresh_days = max(force_days, days_stale + 1)
    else:
        print("  [K276b] No existing K276b parquet. Building fresh (seeding from K265 cache).")
        panel = pd.DataFrame()
        refresh_days = 60  # fetch 60d if starting fresh

    # Seed from K265 longtail cache for overlapping symbols (avoid redundant API calls)
    k265_seed: pd.DataFrame = pd.DataFrame()
    if k265_parquet_path.exists():
        try:
            k265_df = pd.read_parquet(k265_parquet_path)
            k265_df.index = pd.to_datetime(k265_df.index)
            overlap = [s for s in K276B_SYMS if s in k265_df.columns]
            if overlap:
                k265_seed = k265_df[overlap]
                print(f"  [K276b] Seeding {len(overlap)} symbols from K265 cache: {overlap}")
        except Exception as e:
            print(f"  [K276b] K265 cache seed failed: {e}")

    updates: Dict[str, pd.Series] = {}
    for sym in K276B_SYMS:
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

    if not updates and panel.empty and k265_seed.empty:
        print("  [K276b] No updates fetched and no seed data. Panel empty.")
        return pd.DataFrame()

    # Build new data frame from updates
    new_df = pd.DataFrame(updates) if updates else pd.DataFrame()

    # Merge: K265 seed → existing K276b panel → fresh API updates (priority: API > cached)
    frames = []
    if not k265_seed.empty:
        frames.append(k265_seed)
    if not panel.empty:
        frames.append(panel)
    if not new_df.empty:
        frames.append(new_df)

    if len(frames) == 1:
        merged = frames[0].sort_index()
    else:
        merged = pd.concat(frames)
        merged = merged.groupby(merged.index).last()
        merged = merged.sort_index()

    # Keep only K276b symbols
    available_cols = [s for s in K276B_SYMS if s in merged.columns]
    merged = merged[available_cols]

    merged.to_parquet(parquet_path)
    print(f"  [K276b] Panel refreshed → {merged.shape}  ({parquet_path})")
    return merged


def get_k276b_daily_panel(refresh: bool = True) -> pd.DataFrame:
    """Load K276b daily FR panel, optionally refreshing from HL API."""
    if refresh:
        return refresh_k276b_panel(force_days=3)
    parquet_path = CACHE / "hl_k276b_fr_daily.parquet"
    if parquet_path.exists():
        df = pd.read_parquet(parquet_path)
        df.index = pd.to_datetime(df.index)
        return df
    return pd.DataFrame()


# ─────────────────────────────────────────────────────────────────────────────
# 4. K208 spread computation (unchanged from K272a)
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
# 5. K276b live stats (universe liquidity check)
# ─────────────────────────────────────────────────────────────────────────────

def compute_k276b_stats(panel: pd.DataFrame) -> Dict:
    """
    Compute current K276b signal state from the daily FR panel.
    Returns per-symbol FR statistics and current quartile assignments.
    K276b uses same 14d rolling mean signal logic as K265, but on 20-symbol universe.
    """
    if panel.empty:
        return {"error": "K276b panel empty"}

    # Use last 14d mean as the current signal (K276b logic: 14d rolling, same as K265)
    recent = panel.tail(14)
    if len(recent) < 7:
        return {"error": f"K276b panel too short ({len(recent)} days)"}

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
        "n_symbols":       n_sym,
        "signal_14d_mean": {sym: round(float(v), 8) for sym, v in sig_today.dropna().items()},
        "long_sleeve":     long_syms,
        "short_sleeve":    short_syms,
        "low_liquidity":   low_liq,
        "panel_last_date": str(panel.index[-1].date()),
        "panel_n_days":    len(panel),
        "hl_only_syms":    list(HL_ONLY_K276B),
    }


# ─────────────────────────────────────────────────────────────────────────────
# 6. HLP Balance (K200 monitor continued — unchanged from K272a)
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
# 7. Ethena TVL (context monitor — unchanged from K272a)
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

def build_snapshot(date_str: str, refresh_k276b: bool = True) -> Dict:
    """Assemble all K280 live data into a snapshot. Returns metadata dict."""
    print(f"\n=== K280 Live Fetch — {date_str} ===\n")
    t0 = time.time()

    # ── K208 spreads ──────────────────────────────────────────────────────────
    print("Fetching K208 (major CEX-DEX spread) data...")
    k208_data = compute_k208_spreads()

    # ── K276b panel ───────────────────────────────────────────────────────────
    print("\nFetching K276b_top20 (HL 20-symbol FR) panel...")
    k276b_panel = get_k276b_daily_panel(refresh=refresh_k276b)
    k276b_stats = compute_k276b_stats(k276b_panel)

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
        "architecture":   "K280 v6.10.2 (K198+K208+K276b_top20 3-way)",
        "k276b_symbols":  K276B_SYMS,
        "k208":           k208_data,
        "k276b":          k276b_stats,
        "hlp_balance":    hlp_data,
        "hlp_alert":      hlp_data.get("alert", "OK"),
        "ethena_tvl":     ethena_data,
        # K430 leverage metadata (additive; LEVERAGE=1.0 at default PAPER_TRADE)
        "k430_leverage":  LEVERAGE,
        "k430_leverage_enabled": _LEVERAGE_ENABLED,
    }

    # ── Save JSON snapshot ────────────────────────────────────────────────────
    json_path = CACHE / f"k280_live_{date_str.replace('-', '')}.json"
    with open(json_path, "w") as f:
        def sanitize(v):
            if isinstance(v, float) and math.isnan(v):
                return None
            if isinstance(v, dict):
                return {kk: sanitize(vv) for kk, vv in v.items()}
            if isinstance(v, list):
                return [sanitize(x) for x in v]
            return v
        f.write(json.dumps(sanitize(snapshot), indent=2))
    print(f"\n  Saved snapshot JSON: {json_path}")

    # ── Save K276b spread panel parquet ───────────────────────────────────────
    if not k276b_panel.empty:
        parquet_path = CACHE / f"k280_live_{date_str.replace('-', '')}.parquet"
        k276b_panel.to_parquet(parquet_path)
        print(f"  Saved K276b panel: {parquet_path}")
        snapshot["parquet_path"] = str(parquet_path)
    else:
        print("  WARNING: K276b panel empty, parquet not saved")
        snapshot["parquet_path"] = None

    return snapshot


# ─────────────────────────────────────────────────────────────────────────────
# CLI Entry Point
# ─────────────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="K280 v6.10.2 Live Data Fetcher")
    parser.add_argument("--date",        default=None,  help="Date override YYYY-MM-DD")
    parser.add_argument("--force",       action="store_true", help="Force re-fetch even if cached today")
    parser.add_argument("--no-refresh",  action="store_true", help="Skip HL API refresh for K276b panel")
    args = parser.parse_args()

    date_str = args.date or datetime.now(timezone.utc).strftime("%Y-%m-%d")

    # Skip if already fetched today (unless --force)
    json_path = CACHE / f"k280_live_{date_str.replace('-', '')}.json"
    if json_path.exists() and not args.force:
        print(f"Already fetched for {date_str}. Use --force to re-fetch.")
        return

    snapshot = build_snapshot(date_str, refresh_k276b=not args.no_refresh)
    print(f"\n=== Fetch complete in {snapshot['elapsed_sec']}s ===")
    print(f"  HLP alert:       {snapshot.get('hlp_alert', 'N/A')}")
    print(f"  K276b symbols:   {snapshot['k276b'].get('n_symbols', 'N/A')}")
    print(f"  K276b long:      {snapshot['k276b'].get('long_sleeve', [])}")
    print(f"  K276b short:     {snapshot['k276b'].get('short_sleeve', [])}")
    if snapshot['k276b'].get('low_liquidity'):
        print(f"  K276b low-liq:   {snapshot['k276b']['low_liquidity']}")


if __name__ == "__main__":
    main()

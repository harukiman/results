"""
k246a_live_fetch.py — K246a v6.9 Live Data Fetcher
===================================================
Fetches all data sources required for the K246a paper-trade scaffold:

  Component   Data Source
  ──────────  ──────────────────────────────────────────────────────
  K208        Bybit FR (8h settlements) — public REST v5
  K208        HL FR (8h)               — cache/k163_hl/ or HL API
  K226        ETH LST staking flows    — DeFiLlama (free)
  K200        HLP vault balance        — Hyperliquid public API
  K206        Ethena TVL               — DeFiLlama (free)

Output: cache/k246a_live_YYYYMMDD.parquet  (snapshot keyed by today's date)

Usage:
  python3 scripts/k246a_live_fetch.py
  python3 scripts/k246a_live_fetch.py --date 2026-05-25   # specific date
  python3 scripts/k246a_live_fetch.py --force              # re-fetch even if cached today
"""
from __future__ import annotations

import argparse
import json
import time
import warnings
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Dict, Optional

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

# ── Strategy constants ─────────────────────────────────────────────────────────
# K208 reverse carry symbols (10 symbols from K196)
REVERSE_SYMS = ["SOL", "XRP", "SUI", "OP", "APT", "AXS", "JTO", "IMX", "SAND", "ADA"]

# DeFiLlama LST protocol endpoints (for K226)
LST_PROTOCOLS = {
    "lido":       "https://api.llama.fi/protocol/lido",
    "rocket_pool":"https://api.llama.fi/protocol/rocket-pool",
    "stakewise":  "https://api.llama.fi/protocol/stakewise",
    "frax_ether": "https://api.llama.fi/protocol/frax-ether",
}
ETHENA_URL  = "https://api.llama.fi/protocol/ethena"
HLP_ADDRESS = "0xdfc24b077bc1425ad1dea75bcb6f8158e10df303"
HL_API_URL  = "https://api.hyperliquid.xyz/info"

# Bybit public REST v5 — no auth needed
BYBIT_FR_URL = "https://api.bybit.com/v5/market/funding/history"

# ─────────────────────────────────────────────────────────────────────────────
# 1. Bybit FR (last 200 events per symbol, ~66 days at 8h)
# ─────────────────────────────────────────────────────────────────────────────

def fetch_bybit_fr_recent(sym: str, limit: int = 200) -> pd.Series:
    """Fetch recent Bybit funding rate history for one symbol. Free endpoint."""
    params = {
        "category": "linear",
        "symbol": f"{sym}USDT",
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
    """Load Bybit FR from local parquet cache (fallback / historical)."""
    for tag in ("730d", "1200d", "365d"):
        f = CACHE / f"bybit_fr_{sym}USDT_{tag}.parquet"
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
# 2. Hyperliquid FR (from local cache)
# ─────────────────────────────────────────────────────────────────────────────

def fetch_hl_fr_recent(sym: str) -> pd.Series:
    """
    Fetch recent HL funding via Hyperliquid public meta endpoint.
    Returns the current funding rate (single-point; cache will be stale until K163 re-runs).
    """
    try:
        payload = {"type": "metaAndAssetCtxs"}
        resp = requests.post(HL_API_URL, json=payload, timeout=15)
        resp.raise_for_status()
        data = resp.json()
        meta    = data[0]  # universe metadata
        assetCtxs = data[1]  # per-asset current stats
        # Build name→index map
        universe = {item["name"]: i for i, item in enumerate(meta["universe"])}
        if sym not in universe:
            return pd.Series(dtype=float, name=sym)
        idx = universe[sym]
        ctx = assetCtxs[idx]
        fr_8h = float(ctx.get("funding", 0.0))  # 8h rate
        ts = pd.Timestamp.now(tz="UTC").floor("8h")
        s = pd.Series({ts: fr_8h}, name=sym)
        s.index.name = "timestamp"
        return s
    except Exception as e:
        print(f"  [hl_fr live] {sym}: FAILED → {e}")
        return pd.Series(dtype=float, name=sym)


def load_hl_fr_cached(sym: str) -> pd.Series:
    """Load HL FR from cache/k163_hl/ parquet."""
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
    """Merge cached HL FR + latest live point."""
    hist = _normalize_tz(load_hl_fr_cached(sym))
    live = _normalize_tz(fetch_hl_fr_recent(sym))
    if hist.empty and live.empty:
        return pd.Series(dtype=float, name=sym)
    combined = pd.concat([hist, live])
    combined = combined[~combined.index.duplicated(keep="last")].sort_index()
    combined.name = sym
    return combined


# ─────────────────────────────────────────────────────────────────────────────
# 3. K226 — ETH LST Staking Flow (DeFiLlama)
# ─────────────────────────────────────────────────────────────────────────────

def fetch_lst_protocol_eth(name: str, url: str, days_back: int = 90) -> pd.Series:
    """Fetch daily ETH staked for one LST protocol from DeFiLlama."""
    cutoff = time.time() - days_back * 86400
    try:
        req_headers = {"User-Agent": "Mozilla/5.0"}
        resp = requests.get(url, headers=req_headers, timeout=20)
        resp.raise_for_status()
        data = resp.json()
        tokens = data.get("tokens", [])
        records = {}
        for entry in tokens:
            if entry["date"] >= cutoff:
                eth = (
                    (entry["tokens"].get("WETH", 0) or 0)
                    + (entry["tokens"].get("stETH", 0) or 0)
                    + (entry["tokens"].get("ETH", 0) or 0)
                )
                ts = pd.Timestamp(int(entry["date"]), unit="s", tz="UTC").normalize()
                records[ts] = float(eth)
        return pd.Series(records, name=name)
    except Exception as e:
        print(f"  [lst] {name}: FAILED → {e}")
        return pd.Series(dtype=float, name=name)


def get_k226_staking_data() -> pd.DataFrame:
    """
    Fetch or load ETH LST staking data.
    Returns DataFrame with columns: [lido, rocket_pool, stakewise, frax_ether, total_eth_staked]
    """
    cache_path = CACHE / "eth_validator_queue_daily.parquet"
    # Use local cache if fresh (<24h)
    if cache_path.exists():
        age = time.time() - cache_path.stat().st_mtime
        if age < 24 * 3600:
            print("  [k226] Loading cached LST data")
            return pd.read_parquet(cache_path)

    print("  [k226] Fetching LST staking data from DeFiLlama...")
    series_list = []
    for name, url in LST_PROTOCOLS.items():
        s = fetch_lst_protocol_eth(name, url, days_back=90)
        series_list.append(s)

    df = pd.concat(series_list, axis=1).sort_index()
    df = df.ffill()
    protocol_cols = list(LST_PROTOCOLS.keys())
    df["total_eth_staked"] = df[protocol_cols].sum(axis=1, min_count=1)

    df.to_parquet(cache_path)
    print(f"  [k226] Saved to {cache_path}")
    return df


# ─────────────────────────────────────────────────────────────────────────────
# 4. Ethena TVL (DeFiLlama) — K206
# ─────────────────────────────────────────────────────────────────────────────

def get_ethena_tvl() -> pd.Series:
    """Fetch or load Ethena TVL from DeFiLlama. Returns daily USD TVL series."""
    cache_path = CACHE / "ethena_tvl_daily.parquet"
    if cache_path.exists():
        age = time.time() - cache_path.stat().st_mtime
        if age < 24 * 3600:
            print("  [ethena] Loading cached TVL")
            df = pd.read_parquet(cache_path)
            col = "tvl" if "tvl" in df.columns else df.columns[0]
            return df[col].squeeze()

    print("  [ethena] Fetching TVL from DeFiLlama...")
    try:
        resp = requests.get(ETHENA_URL, headers={"User-Agent": "Mozilla/5.0"}, timeout=20)
        resp.raise_for_status()
        data = resp.json()
        tvl_hist = data.get("tvl", [])
        records = {}
        for entry in tvl_hist:
            ts = pd.Timestamp(int(entry["date"]), unit="s", tz="UTC").normalize()
            records[ts] = float(entry["totalLiquidityUSD"])
        s = pd.Series(records, name="tvl").sort_index()
        df = s.to_frame()
        df.index.name = "date"
        df.to_parquet(cache_path)
        print(f"  [ethena] Saved to {cache_path}")
        return s
    except Exception as e:
        print(f"  [ethena] FAILED → {e}")
        # Return cached even if stale
        if cache_path.exists():
            df = pd.read_parquet(cache_path)
            col = "tvl" if "tvl" in df.columns else df.columns[0]
            return df[col].squeeze()
        return pd.Series(dtype=float, name="tvl")


# ─────────────────────────────────────────────────────────────────────────────
# 5. HLP Balance — K200
# ─────────────────────────────────────────────────────────────────────────────

def get_hlp_balance() -> pd.Series:
    """
    Load HLP vault balance series.
    Uses existing cache/hlp_balance_daily.parquet (maintained by K200 daemon).
    Falls back to live API fetch if cache stale.
    """
    cache_path = CACHE / "hlp_balance_daily.parquet"

    if cache_path.exists():
        age = time.time() - cache_path.stat().st_mtime
        if age < 24 * 3600:
            print("  [hlp] Loading cached HLP balance")
            df = pd.read_parquet(cache_path)
            col = [c for c in df.columns if "balance" in c.lower()]
            col = col[0] if col else df.columns[0]
            return df[col].squeeze()

    # Live fetch from Hyperliquid API
    print("  [hlp] Fetching HLP vault balance from Hyperliquid API...")
    try:
        payload = {"type": "vaultDetails", "vaultAddress": HLP_ADDRESS}
        resp = requests.post(HL_API_URL, json=payload, timeout=20)
        resp.raise_for_status()
        raw = resp.json()
        portfolio = {entry[0]: entry[1] for entry in raw.get("portfolio", [])}
        hist = portfolio.get("allTime", {}).get("accountValueHistory", [])
        records = {}
        for ts_ms, val in hist:
            dt = pd.Timestamp(ts_ms, unit="ms", tz="UTC").normalize()
            records[dt] = float(val)
        if not records:
            print("  [hlp] No data returned from API")
            return pd.Series(dtype=float, name="total_balance_usd")
        s = pd.Series(records, name="total_balance_usd").sort_index()
        s = s[~s.index.duplicated(keep="last")]
        # Append to existing cache
        if cache_path.exists():
            existing = pd.read_parquet(cache_path)
            col = [c for c in existing.columns if "balance" in c.lower()]
            col = col[0] if col else existing.columns[0]
            existing_s = existing[col].squeeze()
            combined = pd.concat([existing_s, s])
            combined = combined[~combined.index.duplicated(keep="last")].sort_index()
            combined.to_frame(name="total_balance_usd").to_parquet(cache_path)
            return combined
        else:
            s.to_frame().to_parquet(cache_path)
            return s
    except Exception as e:
        print(f"  [hlp] FAILED → {e}")
        if cache_path.exists():
            df = pd.read_parquet(cache_path)
            col = [c for c in df.columns if "balance" in c.lower()]
            col = col[0] if col else df.columns[0]
            return df[col].squeeze()
        return pd.Series(dtype=float, name="total_balance_usd")


# ─────────────────────────────────────────────────────────────────────────────
# 6. Spread Computation (K208 input)
# ─────────────────────────────────────────────────────────────────────────────

def compute_spreads_panel() -> pd.DataFrame:
    """
    For each of the 10 K208 symbols, compute:
      spread = bybit_fr - hl_fr_8h  (at aligned 8h timestamps)
    Returns DataFrame of per-symbol spreads, indexed by timestamp.
    """
    spread_frames: Dict[str, pd.Series] = {}
    for sym in REVERSE_SYMS:
        bybit = get_bybit_fr(sym)
        hl    = get_hl_fr(sym)
        if bybit.empty or hl.empty:
            print(f"  [spread] {sym}: missing data, skipping")
            continue
        # Resample HL to 8h sums
        hl_8h = hl.resample("8h", label="right", closed="right").sum(min_count=1)
        # Align on Bybit index
        aligned = bybit.to_frame("bybit_fr")
        aligned["hl_fr_8h"] = hl_8h.reindex(aligned.index)
        aligned = aligned.dropna()
        if aligned.empty:
            print(f"  [spread] {sym}: no overlap after alignment")
            continue
        spread_frames[sym] = aligned["bybit_fr"] - aligned["hl_fr_8h"]
        spread_frames[sym].name = sym

    if not spread_frames:
        return pd.DataFrame()
    panel = pd.concat(spread_frames, axis=1)
    panel.index.name = "timestamp"
    return panel


# ─────────────────────────────────────────────────────────────────────────────
# 7. Snapshot Assembly & Save
# ─────────────────────────────────────────────────────────────────────────────

def build_snapshot(date_str: str) -> Dict:
    """Assemble all live data into a snapshot dict. Returns metadata."""
    print(f"\n=== K246a Live Fetch — {date_str} ===\n")
    t0 = time.time()

    # 5a. Bybit + HL FR per symbol (individual)
    bybit_latest: Dict[str, float] = {}
    hl_latest:    Dict[str, float] = {}
    spread_latest: Dict[str, float] = {}
    spread_7d_mean: Dict[str, float] = {}
    spread_30d_mean: Dict[str, float] = {}

    print("Fetching per-symbol FR data...")
    for sym in REVERSE_SYMS:
        by = get_bybit_fr(sym)
        hl = get_hl_fr(sym)
        bybit_latest[sym] = float(by.iloc[-1]) if not by.empty else np.nan
        hl_latest[sym]    = float(hl.iloc[-1]) if not hl.empty else np.nan
        sp = by - hl.resample("8h", label="right", closed="right").sum(min_count=1).reindex(by.index)
        sp = sp.dropna()
        spread_latest[sym]   = float(sp.iloc[-1]) if not sp.empty else np.nan
        spread_7d_mean[sym]  = float(sp.tail(3*7).mean())  if not sp.empty else np.nan   # 3 events/day×7d
        spread_30d_mean[sym] = float(sp.tail(3*30).mean()) if not sp.empty else np.nan

    # 5b. K226 LST staking data
    print("\nFetching K226 LST staking data...")
    lst_df = get_k226_staking_data()
    lst_latest = {}
    lst_7d_change = {}
    lst_30d_change = {}
    if not lst_df.empty and "total_eth_staked" in lst_df.columns:
        s = lst_df["total_eth_staked"].dropna()
        if len(s) > 0:
            lst_latest["total_eth_staked"] = float(s.iloc[-1])
            if len(s) >= 7:
                lst_7d_change["pct"] = float((s.iloc[-1] / s.iloc[-7] - 1) * 100)
            if len(s) >= 30:
                lst_30d_change["pct"] = float((s.iloc[-1] / s.iloc[-30] - 1) * 100)

    # 5c. Ethena TVL
    print("\nFetching Ethena TVL...")
    ethena_tvl = get_ethena_tvl()
    ethena_latest = {}
    if not ethena_tvl.empty:
        ethena_latest["tvl_usd"] = float(ethena_tvl.iloc[-1])
        if len(ethena_tvl) >= 7:
            ethena_latest["7d_change_pct"] = float(
                (ethena_tvl.iloc[-1] / ethena_tvl.iloc[-7] - 1) * 100
            )
        if len(ethena_tvl) >= 30:
            ethena_latest["30d_change_pct"] = float(
                (ethena_tvl.iloc[-1] / ethena_tvl.iloc[-30] - 1) * 100
            )

    # 5d. HLP Balance
    print("\nFetching HLP balance...")
    hlp_series = get_hlp_balance()
    hlp_latest = {}
    if not hlp_series.empty:
        hlp_latest["balance_usd"] = float(hlp_series.iloc[-1])
        if len(hlp_series) >= 7:
            hlp_latest["7d_change_pct"] = float(
                (hlp_series.iloc[-1] / hlp_series.iloc[-7] - 1) * 100
            )

    # 5e. Build spread panel and save to parquet
    print("\nBuilding spread panel...")
    spread_panel = compute_spreads_panel()

    # ── K226 z-score (30d rolling) ────────────────────────────────────────────
    k226_zscore = np.nan
    if not lst_df.empty and "total_eth_staked" in lst_df.columns:
        flow = lst_df["total_eth_staked"].diff().dropna()
        if len(flow) >= 30:
            roll_mean = flow.rolling(30).mean()
            roll_std  = flow.rolling(30).std(ddof=1)
            z = (flow - roll_mean) / (roll_std + 1e-9)
            k226_zscore = float(z.iloc[-1]) if not z.empty else np.nan

    # ── HLP 7d alert flag ────────────────────────────────────────────────────
    hlp_7d_pct = hlp_latest.get("7d_change_pct", np.nan)
    hlp_alert  = "OK"
    if not np.isnan(hlp_7d_pct):
        if hlp_7d_pct < -40.0:
            hlp_alert = "HALT"
        elif hlp_7d_pct < -20.0:
            hlp_alert = "REDUCE"

    # ── Spread compression check ─────────────────────────────────────────────
    spread_compression_flags: Dict[str, str] = {}
    for sym in REVERSE_SYMS:
        m7  = spread_7d_mean.get(sym, np.nan)
        m30 = spread_30d_mean.get(sym, np.nan)
        if not np.isnan(m7) and not np.isnan(m30) and m30 > 0:
            # Flag if 7d mean < 25th pctile approximation (< 75% of 30d mean)
            ratio = m7 / (m30 + 1e-12)
            spread_compression_flags[sym] = "COMPRESSED" if ratio < 0.75 else "NORMAL"
        else:
            spread_compression_flags[sym] = "UNKNOWN"

    elapsed = time.time() - t0

    snapshot = {
        "fetch_date":          date_str,
        "fetch_ts_utc":        datetime.now(timezone.utc).isoformat(),
        "elapsed_sec":         round(elapsed, 1),
        "bybit_fr_latest":     bybit_latest,
        "hl_fr_latest":        hl_latest,
        "spread_latest":       spread_latest,
        "spread_7d_mean":      spread_7d_mean,
        "spread_30d_mean":     spread_30d_mean,
        "k226_lst_latest":     lst_latest,
        "k226_lst_7d_change":  lst_7d_change,
        "k226_lst_30d_change": lst_30d_change,
        "k226_zscore_today":   k226_zscore,
        "ethena_tvl":          ethena_latest,
        "hlp_balance":         hlp_latest,
        "hlp_alert":           hlp_alert,
        "spread_compression":  spread_compression_flags,
    }

    # Save summary JSON
    json_path = CACHE / f"k246a_live_{date_str.replace('-', '')}.json"
    with open(json_path, "w") as f:
        def _safe(v):
            if isinstance(v, float) and np.isnan(v): return None
            return v
        # Custom serializer for NaN
        import math
        class NaNSafe(json.JSONEncoder):
            def default(self, obj):
                if isinstance(obj, float) and math.isnan(obj):
                    return None
                return super().default(obj)
        f.write(json.dumps(snapshot, indent=2, cls=NaNSafe))
    print(f"\n  Saved snapshot JSON: {json_path}")

    # Save spread panel parquet
    if not spread_panel.empty:
        parquet_path = CACHE / f"k246a_live_{date_str.replace('-', '')}.parquet"
        spread_panel.to_parquet(parquet_path)
        print(f"  Saved spread panel: {parquet_path}")
        snapshot["parquet_path"] = str(parquet_path)
    else:
        print("  WARNING: spread panel empty, parquet not saved")
        snapshot["parquet_path"] = None

    return snapshot


# ─────────────────────────────────────────────────────────────────────────────
# CLI Entry Point
# ─────────────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="K246a Live Data Fetcher")
    parser.add_argument("--date",  default=None,  help="Date override YYYY-MM-DD")
    parser.add_argument("--force", action="store_true", help="Force re-fetch")
    args = parser.parse_args()

    date_str = args.date or datetime.now(timezone.utc).strftime("%Y-%m-%d")

    # Skip if already fetched today (unless --force)
    json_path = CACHE / f"k246a_live_{date_str.replace('-', '')}.json"
    if json_path.exists() and not args.force:
        print(f"Already fetched for {date_str}. Use --force to re-fetch.")
        return

    snapshot = build_snapshot(date_str)
    print(f"\n=== Fetch complete in {snapshot['elapsed_sec']}s ===")
    print(f"  HLP alert: {snapshot['hlp_alert']}")
    print(f"  K226 z-score: {snapshot.get('k226_zscore_today', 'N/A'):.3f}"
          if isinstance(snapshot.get('k226_zscore_today'), float) and
             not np.isnan(snapshot['k226_zscore_today']) else
          f"  K226 z-score: N/A")


if __name__ == "__main__":
    main()

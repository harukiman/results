"""Wave K18 — Stablecoin supply meta-filter (S3I 再定義).

仮説:
  S3I (Wave J17) は signal として 4Hで機能しなかった (slow signal)。
  しかし<strong>レジームフィルター</strong>として活用すれば価値?
  stablecoin supply が縮小局面 (z_score < threshold) は「資金引き上げ局面」
  → ポジションサイズ縮小 (DD回避) 検証
"""
import asyncio
import json
import sys
import numpy as np
import pandas as pd
import httpx
from pathlib import Path
from datetime import datetime, timezone, timedelta

sys.path.insert(0, "/Users/nekonaomichi/crypto-lab")
from audit_4way_mix import compute_4way_daily, sharpe, aggregate_4h_to_8h
from engine.data import fetch_klines, fetch_bybit_funding_rate, fetch_historical_metrics

ATR_SYMBOLS = ["OPUSDT", "WIFUSDT", "INJUSDT", "BONKUSDT",
               "DOGEUSDT", "SHIBUSDT", "ARBUSDT", "LINKUSDT"]
FOPD_SYMS = ['BNBUSDT', 'AVAXUSDT', 'ETHUSDT', 'ADAUSDT', 'LINKUSDT', 'DOTUSDT']
VOL_MR_SYMS = ['BTCUSDT', 'ETHUSDT', 'SOLUSDT', 'BNBUSDT']
ALL = set(ATR_SYMBOLS + FOPD_SYMS + VOL_MR_SYMS)
DAYS = 730
CACHE_PATH = Path("/Users/nekonaomichi/crypto-lab/cache/stablecoin_supply.parquet")


async def fetch_stablecoin_supply():
    if CACHE_PATH.exists():
        return pd.read_parquet(CACHE_PATH)
    url = "https://stablecoins.llama.fi/stablecoincharts/all"
    async with httpx.AsyncClient(timeout=60) as client:
        resp = await client.get(url); resp.raise_for_status()
        data = resp.json()
    records = []
    for d in data:
        ts = int(d["date"])
        tc = d.get("totalCirculating") or d.get("totalCirculatingUSD") or {}
        if isinstance(tc, dict):
            usd = tc.get("peggedUSD", 0) or 0
        else:
            usd = float(tc) if tc else 0
        records.append({"timestamp": pd.to_datetime(ts, unit='s'), "supply_usd": float(usd)})
    df = pd.DataFrame(records).sort_values("timestamp").drop_duplicates("timestamp").reset_index(drop=True)
    return df


async def main():
    print("=== Wave K18: Stablecoin Supply Meta-Filter on 4-way mix ===\n")

    # Get stablecoin supply data
    ss = await fetch_stablecoin_supply()
    # Existing cache uses column 'stablecoin_supply_usd', new fetch uses 'supply_usd'
    supply_col = 'stablecoin_supply_usd' if 'stablecoin_supply_usd' in ss.columns else 'supply_usd'
    ss['supply_change_7d'] = ss[supply_col].pct_change(7)
    ss['change_mean_60d'] = ss['supply_change_7d'].rolling(60).mean()
    ss['change_std_60d'] = ss['supply_change_7d'].rolling(60).std()
    ss['supply_z'] = (ss['supply_change_7d'] - ss['change_mean_60d']) / (ss['change_std_60d'] + 1e-10)
    ss['supply_z'] = ss['supply_z'].fillna(0)
    print(f"Stablecoin supply: {len(ss)} days, range {ss['timestamp'].min().date()} → {ss['timestamp'].max().date()}")
    print(f"supply_z stats: min={ss['supply_z'].min():.2f}, max={ss['supply_z'].max():.2f}, mean={ss['supply_z'].mean():.2f}")

    # Compute 4-way mix daily returns
    cache = {}
    for s in ALL:
        cache[s] = await fetch_klines(s, "4h", DAYS)
    for s in FOPD_SYMS:
        try: fr = await fetch_bybit_funding_rate(s, DAYS)
        except: fr = None
        try: oi = await fetch_historical_metrics(s, DAYS)
        except: oi = None
        cache[s] = {'ohlcv': cache[s], 'fr': fr, 'oi': oi}
    btc = cache['BTCUSDT'] if not isinstance(cache['BTCUSDT'], dict) else cache['BTCUSDT']['ohlcv']
    btc = btc.copy()
    btc['ret'] = btc['close'].pct_change()
    btc['rv'] = btc['ret'].rolling(60).std() * np.sqrt(2190) * 100
    btc['rvm'] = btc['rv'].rolling(360).mean()
    btc['rvs'] = btc['rv'].rolling(360).std()
    btc['volz'] = (btc['rv'] - btc['rvm']) / (btc['rvs'] + 1e-10)
    btc_idx_4h = btc.set_index('open_time')
    btc_8h = aggregate_4h_to_8h(btc)
    btc_8h['ret'] = btc_8h['close'].pct_change()
    btc_8h['rv'] = btc_8h['ret'].rolling(30).std() * np.sqrt(1095) * 100
    btc_8h['rvm'] = btc_8h['rv'].rolling(180).mean()
    btc_8h['rvs'] = btc_8h['rv'].rolling(180).std()
    btc_8h['volz'] = (btc_8h['rv'] - btc_8h['rvm']) / (btc_8h['rvs'] + 1e-10)
    btc_idx_8h = btc_8h.set_index('open_time')

    print("\nComputing 4-way mix baseline ...")
    four_way = await compute_4way_daily(cache, btc_idx_4h, btc_idx_8h)
    n_days = len(four_way)

    # Align supply data to 4-way mix days
    dates_4w = pd.date_range(end=pd.Timestamp.now().normalize(), periods=n_days, freq='D')
    dates_4w_df = pd.DataFrame({'timestamp': pd.to_datetime(dates_4w).astype('datetime64[ns]')})
    ss_normalized = ss[['timestamp', 'supply_z']].copy()
    ss_normalized['timestamp'] = pd.to_datetime(ss_normalized['timestamp']).astype('datetime64[ns]')
    ss_aligned = pd.merge_asof(dates_4w_df, ss_normalized, on='timestamp', direction='backward')
    supply_z_aligned = ss_aligned['supply_z'].fillna(0).values

    # Variants
    variants = {}
    variants['Baseline (no filter)'] = four_way

    # Filter A: When supply_z < -1, reduce position to 50%
    for thr in [-2.0, -1.5, -1.0, -0.5]:
        scale = np.where(supply_z_aligned < thr, 0.5, 1.0)
        variants[f"50% scale when supply_z < {thr}"] = four_way * scale

    # Filter B: When supply_z < -1, full off
    for thr in [-2.0, -1.5, -1.0]:
        scale = np.where(supply_z_aligned < thr, 0.0, 1.0)
        variants[f"OFF when supply_z < {thr}"] = four_way * scale

    print(f"\n{'Variant':<45} {'Sharpe':>8} {'Return':>9} {'DD':>8} {'Calmar':>8}")
    print("-" * 80)
    results = []
    for name, p in variants.items():
        sh = sharpe(p)
        eq = np.cumprod(1 + p)
        ret = (eq[-1] - 1) * 100
        dd = (eq / np.maximum.accumulate(eq) - 1).min() * 100
        cal = abs(ret / dd) if dd != 0 else 0
        print(f"  {name:<45} {sh:>+8.2f} {ret:>+8.1f}% {dd:>+7.1f}% {cal:>8.2f}")
        results.append({"variant": name, "sharpe": round(sh, 3), "return_pct": round(float(ret), 2),
                        "max_dd_pct": round(float(dd), 2), "calmar": round(cal, 2)})

    out = {
        "wave": "K18", "name": "Stablecoin supply meta-filter on 4-way mix",
        "generated_at": datetime.now(timezone(timedelta(hours=9))).strftime("%Y-%m-%d %H:%M JST"),
        "results": results,
    }
    Path("/Users/nekonaomichi/crypto-lab/wave_k18_stable_filter.json").write_text(json.dumps(out, indent=2, default=str))
    print("\nSaved.")


if __name__ == "__main__":
    asyncio.run(main())

"""Expand symbol cache to 50+ MEXC perpetual symbols.

Uses Bybit klines (proxy for MEXC perp data quality — Bybit USDT-perp
prices track MEXC closely for top symbols, and our existing 4h_730d cache
is Bybit-sourced as well).

Usage: python3 build_universe_50.py
Output: cache/{SYM}_4h_730d.parquet (skip if exists & fresh)
"""
import asyncio
import sys
import time
from pathlib import Path

sys.path.insert(0, "/Users/nekonaomichi/crypto-lab")
from engine.data import fetch_klines, CACHE_DIR

# Target: 50+ MEXC liquid perpetual symbols
# Selected from coingecko top-100 + MEXC perp listings (manually filtered for liquidity > 1M$/day)
SYMBOLS_60 = [
    # Tier 1 - majors
    "BTCUSDT", "ETHUSDT", "SOLUSDT", "BNBUSDT", "XRPUSDT", "DOGEUSDT",
    # Tier 2 - large alts
    "ADAUSDT", "AVAXUSDT", "LINKUSDT", "DOTUSDT", "MATICUSDT", "LTCUSDT",
    "TRXUSDT", "ATOMUSDT", "NEARUSDT", "FILUSDT", "ICPUSDT", "ETCUSDT",
    # Tier 3 - mid caps
    "INJUSDT", "APTUSDT", "OPUSDT", "ARBUSDT", "SUIUSDT", "SEIUSDT",
    "TIAUSDT", "AAVEUSDT", "MKRUSDT", "RUNEUSDT", "FETUSDT", "RENDERUSDT",
    "RNDRUSDT", "GRTUSDT", "STXUSDT", "IMXUSDT", "PYTHUSDT", "JUPUSDT",
    # Meme / high vol
    "WIFUSDT", "BONKUSDT", "SHIBUSDT", "PEPEUSDT", "FLOKIUSDT", "BOMEUSDT",
    # DeFi
    "UNIUSDT", "LDOUSDT", "CRVUSDT", "SUSHIUSDT", "DYDXUSDT", "GMXUSDT",
    "COMPUSDT", "SNXUSDT",
    # AI / gaming / L1-L2
    "WLDUSDT", "AIUSDT", "TAOUSDT", "ARKMUSDT", "ONDOUSDT", "JTOUSDT",
    "MANTAUSDT", "STRKUSDT", "ALTUSDT", "ENAUSDT",
]


async def fetch_one(sym, days=730):
    """Fetch klines if not cached. Returns (sym, status, bars)."""
    cache_file = CACHE_DIR / f"{sym}_4h_{days}d.parquet"
    if cache_file.exists():
        try:
            import pandas as pd
            df = pd.read_parquet(cache_file)
            return (sym, "cached", len(df))
        except Exception:
            pass
    try:
        t0 = time.time()
        df = await fetch_klines(sym, "4h", days)
        elapsed = time.time() - t0
        return (sym, f"new ({elapsed:.1f}s)", len(df))
    except Exception as e:
        return (sym, f"FAIL: {str(e)[:60]}", 0)


async def main():
    print(f"Target universe: {len(SYMBOLS_60)} symbols")
    sem = asyncio.Semaphore(4)
    results = []
    async def worker(s):
        async with sem:
            r = await fetch_one(s)
            print(f"  {r[0]:14s} {r[1]:30s} bars={r[2]}", flush=True)
            results.append(r)
    await asyncio.gather(*[worker(s) for s in SYMBOLS_60])
    ok = [r for r in results if r[2] > 100]
    fail = [r for r in results if r[2] <= 100]
    print(f"\nSUMMARY: {len(ok)}/{len(SYMBOLS_60)} OK, {len(fail)} missing/short")
    print(f"Universe size for future Waves: {len(ok)}")
    return ok


if __name__ == "__main__":
    asyncio.run(main())

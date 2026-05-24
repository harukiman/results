"""Build 730d OI + funding cache for symbols used by v4.1 mix.

Solves the K109 caveat (OI/funding 730d cache missing → proxies used).
Output: cache/bybit_fr_{SYM}_730d.parquet, cache/bybit_oi_{SYM}_730d.parquet
"""
import asyncio
import sys
import time
import pandas as pd
from pathlib import Path

sys.path.insert(0, "/Users/nekonaomichi/crypto-lab")
from engine.data import fetch_bybit_funding_rate, fetch_open_interest, fetch_historical_metrics

CACHE = Path("/Users/nekonaomichi/crypto-lab/cache")
SYMBOLS = ["BTCUSDT", "ETHUSDT", "SOLUSDT", "BNBUSDT", "DOGEUSDT",
           "AVAXUSDT", "LINKUSDT", "ADAUSDT", "XRPUSDT", "INJUSDT",
           "OPUSDT", "WIFUSDT", "BONKUSDT", "SHIBUSDT", "ARBUSDT"]
DAYS = 730


async def fetch_one(sym):
    rows = []
    try:
        t0 = time.time()
        fr = await fetch_bybit_funding_rate(sym, days=DAYS)
        rows.append(f"  {sym} FR: rows={len(fr)} {time.time()-t0:.1f}s")
    except Exception as e:
        rows.append(f"  {sym} FR FAIL: {e}")
    try:
        t0 = time.time()
        oi = await fetch_open_interest(sym, period="4h", days=DAYS)
        rows.append(f"  {sym} OI: rows={len(oi)} {time.time()-t0:.1f}s")
    except Exception as e:
        rows.append(f"  {sym} OI FAIL: {e}")
    return "\n".join(rows)


async def main():
    print(f"Building OI+FR 730d cache for {len(SYMBOLS)} symbols...")
    sem = asyncio.Semaphore(3)  # limit concurrency to avoid rate-limit
    async def worker(s):
        async with sem:
            r = await fetch_one(s)
            print(r, flush=True)
    await asyncio.gather(*[worker(s) for s in SYMBOLS])
    print("done.")


if __name__ == "__main__":
    asyncio.run(main())

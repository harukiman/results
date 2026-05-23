"""Fetch missing symbols for Wave G broad universe scan.

Targets 27-symbol universe across Major/LargeCap/MidCap/SmallCap/L2/DeFi/Meme tiers.
"""
import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from engine.data import fetch_klines

MISSING = ['ATOMUSDT', 'LTCUSDT', 'INJUSDT', 'TIAUSDT', 'ARBUSDT',
           'OPUSDT', 'MATICUSDT', 'UNIUSDT', 'AAVEUSDT', 'SHIBUSDT']


async def fetch_one(sym):
    try:
        df = await fetch_klines(symbol=sym, interval="4h", days=730)
        if df is None or df.empty:
            print(f"{sym}: EMPTY")
            return sym, 0
        print(f"{sym}: {len(df)} bars, range {df['open_time'].min()} → {df['open_time'].max()}")
        return sym, len(df)
    except Exception as e:
        print(f"{sym}: ERROR {e}")
        return sym, -1


async def main():
    results = []
    # serial to be nice to MEXC
    for s in MISSING:
        results.append(await fetch_one(s))
    print("\n=== Summary ===")
    for s, n in results:
        flag = "OK" if n > 1000 else ("THIN" if n > 0 else "FAIL")
        print(f"  {s:<12} {n:>5} bars  [{flag}]")


if __name__ == "__main__":
    asyncio.run(main())

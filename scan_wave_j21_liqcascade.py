"""Wave J21 — LiqCascadeFade (Tip-scraper TOP1) validation.

Hypothesis (Curupira blog, Tip TOP1):
  清算カスケード「climax」後の v字回復 mean reversion。
  「売りvolume急増 + 価格が下げ止まる」=passive bid 介入 検知シグナル。

Entry (4H bar):
  vol_ratio = volume / mean(volume, 20)
  range_low_break = low < min(low, 20)  # 直近20バー新安値ブレイク
  range_high_break = high > max(high, 20)  # 直近20バー新高値ブレイク
  body_above_mid = close > (high + low) / 2  # close が中点より上 (反転示唆)
  body_below_mid = close < (high + low) / 2

  long_signal: range_low_break & (vol_ratio > N) & body_above_mid (sold off, then closed near top)
  short_signal: range_high_break & (vol_ratio > N) & body_below_mid (bought up, then closed near bottom)

Exit: TP=1.5 ATR, SL=1.0 ATR, MaxHold=6 bars (24h)
Universe: ALL 26 (broad test)
"""
import asyncio
import json
import sys
import numpy as np
import pandas as pd
from pathlib import Path
from datetime import datetime, timezone, timedelta

sys.path.insert(0, "/Users/nekonaomichi/crypto-lab")
from engine.data import fetch_klines
from engine.backtest import run_backtest
from engine.cost_config import get_cost_params

UNIVERSE = ["BTCUSDT", "ETHUSDT", "SOLUSDT", "BNBUSDT", "XRPUSDT",
            "ADAUSDT", "DOTUSDT", "LINKUSDT", "AVAXUSDT", "ATOMUSDT", "LTCUSDT",
            "SUIUSDT", "APTUSDT", "NEARUSDT", "INJUSDT", "TIAUSDT", "SEIUSDT",
            "ARBUSDT", "OPUSDT", "UNIUSDT", "AAVEUSDT",
            "DOGEUSDT", "PEPEUSDT", "SHIBUSDT", "BONKUSDT", "WIFUSDT"]
DAYS = 730
BARS_PER_YEAR = 2190


def liqcascade_signal(df, vol_lookback=20, vol_thresh=3.0, range_lookback=20):
    """LiqCascadeFade signal — v字回復 candidate detection."""
    o = df['open'].values
    h = df['high'].values
    l = df['low'].values
    c = df['close'].values
    v = df['volume'].values

    vol_ma = pd.Series(v).rolling(vol_lookback).mean().values
    vol_ratio = v / (vol_ma + 1e-12)

    # New range break (extreme)
    low_break = pd.Series(l).rolling(range_lookback).min().shift(1).values
    high_break = pd.Series(h).rolling(range_lookback).max().shift(1).values
    is_new_low = l < low_break
    is_new_high = h > high_break

    midpoint = (h + l) / 2.0
    body_above_mid = c > midpoint  # rejection of low - bullish
    body_below_mid = c < midpoint  # rejection of high - bearish

    long_sig = is_new_low & (vol_ratio > vol_thresh) & body_above_mid
    short_sig = is_new_high & (vol_ratio > vol_thresh) & body_below_mid

    sig = np.zeros(len(df), dtype=int)
    sig[long_sig] = +1
    sig[short_sig] = -1
    sig[:max(vol_lookback, range_lookback) + 2] = 0
    return pd.Series(sig, index=df.index)


def run_bt(df, sig, sym, sl=0.04, tp=0.06, mhb=6):
    cost = get_cost_params(sym, "4h")
    return run_backtest(df, sig, strategy_name="LCF", bars_per_year=BARS_PER_YEAR,
                        leverage=1.0, stop_loss_pct=sl, take_profit_pct=tp,
                        max_hold_bars=mhb, **cost)


async def main():
    print("=== Wave J21: LiqCascadeFade (Tip TOP1) ===\n")

    cache = {}
    print("Loading data ...")
    for s in UNIVERSE:
        df = await fetch_klines(s, "4h", DAYS)
        cache[s] = df

    vol_threshs = [2.0, 2.5, 3.0, 4.0, 5.0]
    range_lbs = [15, 20, 30]
    sls = [0.03, 0.04, 0.05]
    tps = [0.04, 0.06, 0.08]
    mhbs = [3, 6, 12]

    n_grid = len(vol_threshs) * len(range_lbs) * len(sls) * len(tps) * len(mhbs)
    print(f"Grid: {n_grid} params × {len(UNIVERSE)} = {n_grid * len(UNIVERSE)} backtests\n")

    results = []
    best_per_symbol = {}
    for s in UNIVERSE:
        df = cache[s]
        best = None
        for vt in vol_threshs:
            for rl in range_lbs:
                sig = liqcascade_signal(df, vol_thresh=vt, range_lookback=rl)
                n_sig = (sig != 0).sum()
                if n_sig < 10:
                    continue
                for sl in sls:
                    for tp in tps:
                        for mhb in mhbs:
                            try:
                                r = run_bt(df, sig, s, sl, tp, mhb)
                                m = r['metrics']
                                sh = float(m.get('sharpe_ratio') or 0)
                                ret = float(m.get('total_return_pct') or 0)
                                dd = float(m.get('max_drawdown_pct') or 0)
                                trades = int(m.get('total_trades') or 0)
                                if trades < 15:
                                    continue
                                row = {
                                    'symbol': s, 'vt': vt, 'rl': rl,
                                    'sl': sl, 'tp': tp, 'mhb': mhb,
                                    'sharpe': round(sh, 3), 'return_pct': round(ret, 2),
                                    'dd_pct': round(dd, 2), 'trades': trades,
                                }
                                results.append(row)
                                if best is None or sh > best['sharpe']:
                                    best = row
                            except Exception:
                                pass
        if best:
            best_per_symbol[s] = best

    print("=== Best per symbol ===")
    for s in UNIVERSE:
        if s in best_per_symbol:
            b = best_per_symbol[s]
            print(f"  {s:<10} Sh={b['sharpe']:+5.2f} ret={b['return_pct']:+6.1f}% dd={b['dd_pct']:+6.1f}% tr={b['trades']:>3} (vt={b['vt']}, rl={b['rl']})")
        else:
            print(f"  {s:<10} no valid result")

    results.sort(key=lambda x: x['sharpe'], reverse=True)
    print(f"\n=== Top 10 ===")
    for r in results[:10]:
        print(f"  {r['symbol']:<10} Sh={r['sharpe']:+.2f} ret={r['return_pct']:+.1f}% dd={r['dd_pct']:+.1f}% tr={r['trades']}")

    sh_pos = sum(1 for r in results if r['sharpe'] > 0)
    sh_ge_1 = sum(1 for r in results if r['sharpe'] >= 1.0)
    sh_ge_1_5 = sum(1 for r in results if r['sharpe'] >= 1.5)
    sh_ge_2 = sum(1 for r in results if r['sharpe'] >= 2.0)
    print(f"\nTotals: Sh>0 {sh_pos}/{len(results)} ({sh_pos/max(len(results),1)*100:.0f}%), ≥1.0: {sh_ge_1}, ≥1.5: {sh_ge_1_5}, ≥2.0: {sh_ge_2}")

    out = {
        "wave": "J21", "name": "LiqCascadeFade (OHLCV proxy)",
        "generated_at": datetime.now(timezone(timedelta(hours=9))).strftime("%Y-%m-%d %H:%M JST"),
        "n_trials": len(results),
        "summary_counts": {"sh_pos": sh_pos, "sh_ge_1": sh_ge_1, "sh_ge_1_5": sh_ge_1_5, "sh_ge_2": sh_ge_2},
        "best_per_symbol": best_per_symbol, "top10": results[:10],
    }
    Path("/Users/nekonaomichi/crypto-lab/wave_j21_liqcascade.json").write_text(json.dumps(out, indent=2, default=str))
    print("\nSaved.")


if __name__ == "__main__":
    asyncio.run(main())

"""Wave J11 — HLWI (HL Wick Imbalance) validation.

Hypothesis (Researcher R6):
  4Hローソク足の上ヒゲ/下ヒゲ比率はテイク主体の board depth 非対称性を間接推定。
  極端な非対称ヒゲ後の continuation が短期エッジ。
  Body Ratio (棄却) と異なり、ヒゲ非対称×ボラ条件付き で 「continuation 地形」に絞る。

Entry:
  upper_wick = high - max(open, close)
  lower_wick = min(open, close) - low
  wick_asym = (upper_wick - lower_wick) / (high - low)
  range_ratio = (high - low) / ATR20
  short_signal: wick_asym > +0.6 & range_ratio > 1.5 & close < open (陰線)
  long_signal:  wick_asym < -0.6 & range_ratio > 1.5 & close > open (陽線)

Exit: TP=1.5 ATR / SL=1.0 ATR / MaxHold=4 bars

26-symbol broad universe scan (既存のWave Gと同じ).
"""
import asyncio
import json
import sys
import time
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


def hlwi_signal(df, wick_thresh=0.6, range_thresh=1.5, atr_window=20):
    """HLWI signal."""
    o = df['open'].values
    h = df['high'].values
    l = df['low'].values
    c = df['close'].values
    body_top = np.maximum(o, c)
    body_bot = np.minimum(o, c)
    upper_wick = h - body_top
    lower_wick = body_bot - l
    rng = h - l
    rng_safe = np.where(rng > 0, rng, 1e-10)
    wick_asym = (upper_wick - lower_wick) / rng_safe
    atr = pd.Series(rng, index=df.index).rolling(atr_window).mean().values
    atr_safe = np.where(atr > 0, atr, 1e-10)
    range_ratio = rng / atr_safe
    is_bearish = c < o
    is_bullish = c > o
    # Continuation: large upper wick + bearish bar → short (price was rejected up)
    short_sig = (wick_asym > wick_thresh) & (range_ratio > range_thresh) & is_bearish
    long_sig = (wick_asym < -wick_thresh) & (range_ratio > range_thresh) & is_bullish
    sig = np.zeros(len(df), dtype=int)
    sig[short_sig] = -1
    sig[long_sig] = +1
    # warmup
    sig[:atr_window + 2] = 0
    return pd.Series(sig, index=df.index)


def sharpe(r, ppy=365):
    r = np.asarray(r); r = r[np.isfinite(r)]
    if len(r) < 5 or np.std(r, ddof=1) == 0: return 0.0
    return float(np.mean(r) / np.std(r, ddof=1) * np.sqrt(ppy))


def run_bt(df, sig, sym, sl=0.04, tp=0.06, mhb=4):
    cost = get_cost_params(sym, "4h")
    return run_backtest(df, sig, strategy_name="HLWI",
                        bars_per_year=BARS_PER_YEAR, leverage=1.0,
                        stop_loss_pct=sl, take_profit_pct=tp, max_hold_bars=mhb,
                        **cost)


async def main():
    t0 = time.time()
    print("=== Wave J11: HLWI (HL Wick Imbalance) validation ===\n")

    print("Loading data ...")
    cache = {}
    for s in UNIVERSE:
        df = await fetch_klines(s, "4h", DAYS)
        cache[s] = df
    print(f"Loaded {len(cache)} symbols\n")

    # ── Parameter scan ──
    wick_thresholds = [0.4, 0.5, 0.6, 0.7]
    range_thresholds = [1.2, 1.5, 1.8]
    sls = [0.03, 0.04, 0.05]
    tps = [0.04, 0.06, 0.08]
    mhbs = [2, 4, 6]

    n_grid = len(wick_thresholds) * len(range_thresholds) * len(sls) * len(tps) * len(mhbs)
    print(f"Grid: {n_grid} params × {len(UNIVERSE)} symbols = {n_grid * len(UNIVERSE)} backtests")

    results = []
    best_per_symbol = {}
    for s in UNIVERSE:
        df = cache[s]
        best = None
        for wt in wick_thresholds:
            for rt in range_thresholds:
                sig = hlwi_signal(df, wt, rt)
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
                                if trades < 20:
                                    continue
                                row = {
                                    'symbol': s, 'wt': wt, 'rt': rt,
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

    # Print best per symbol
    print("\n=== Best per symbol ===")
    for s in UNIVERSE:
        if s in best_per_symbol:
            b = best_per_symbol[s]
            print(f"  {s:<10} Sh={b['sharpe']:+5.2f} ret={b['return_pct']:+6.1f}% "
                  f"dd={b['dd_pct']:+5.1f}% tr={b['trades']:>3} (wt={b['wt']}, rt={b['rt']}, sl={b['sl']}, tp={b['tp']}, mhb={b['mhb']})")
        else:
            print(f"  {s:<10} no valid result")

    # Top global
    results.sort(key=lambda x: x['sharpe'], reverse=True)
    print(f"\n=== Top 10 (all symbols) ===")
    for r in results[:10]:
        print(f"  {r['symbol']:<10} Sh={r['sharpe']:+.2f} ret={r['return_pct']:+.1f}% dd={r['dd_pct']:+.1f}% tr={r['trades']}")

    sh_pos = sum(1 for r in results if r['sharpe'] > 0)
    sh_ge_1 = sum(1 for r in results if r['sharpe'] >= 1.0)
    sh_ge_1_5 = sum(1 for r in results if r['sharpe'] >= 1.5)
    sh_ge_2 = sum(1 for r in results if r['sharpe'] >= 2.0)
    print(f"\nTotals: Sh>0 {sh_pos}/{len(results)} ({sh_pos/max(len(results),1)*100:.0f}%), ≥1.0: {sh_ge_1}, ≥1.5: {sh_ge_1_5}, ≥2.0: {sh_ge_2}")

    out = {
        "wave": "J11", "name": "HLWI (HL Wick Imbalance)",
        "generated_at": datetime.now(timezone(timedelta(hours=9))).strftime("%Y-%m-%d %H:%M JST"),
        "hypothesis": "ヒゲ非対称×レンジ×陰陽AND で OB depth proxy", "universe": UNIVERSE,
        "n_trials": len(results),
        "summary_counts": {"sh_pos": sh_pos, "sh_ge_1": sh_ge_1, "sh_ge_1_5": sh_ge_1_5, "sh_ge_2": sh_ge_2},
        "best_per_symbol": best_per_symbol, "top10": results[:10],
        "runtime_sec": round(time.time() - t0, 1),
    }
    Path("/Users/nekonaomichi/crypto-lab/wave_j11_hlwi.json").write_text(json.dumps(out, indent=2, default=str))
    print(f"\nSaved (runtime {out['runtime_sec']}s)")


if __name__ == "__main__":
    asyncio.run(main())

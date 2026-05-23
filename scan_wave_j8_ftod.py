"""Wave J8 — FToD (Funding Time-of-Day Tail Reversal) validation.

Hypothesis (Researcher TOP1):
  ファンディング決済時刻 (UTC 0/8/16) の直後の4Hバーで、その直前12hで
  「FRが極端な側」のポジション保有者が支払コストに耐えきれず利確/損切りする
  現象を捕捉する逆張り戦略。Funding Timing単独 (棄却) と異なり、FR水準条件を
  必須にすることで行動経済学的トリガーポイントに限定。

Entry:
  is_post_funding = bar_hour in {0, 8, 16}  # UTC
  fr_extreme_long_pay = FR > +0.03%/8h  (ロング過剰)
  fr_extreme_short_pay = FR < -0.03%/8h
  short_signal: is_post_funding & fr_long_pay & price_24h_ret > +5%
  long_signal:  is_post_funding & fr_short_pay & price_24h_ret < -5%

Exit: TP=1ATR / SL=0.8ATR / MaxHold=2 bars (8h)
Symbols: Meme + SmallCap (FR極値発生頻度高)
TF: 4H

Test:
  - 730d backtest on multi-symbol
  - Walk-Forward 4-fold
  - Correlation with existing 5 survivors
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
from engine.data import fetch_klines, fetch_bybit_funding_rate
from engine.backtest import run_backtest
from engine.cost_config import get_cost_params

# Symbols: Meme + SmallCap (high FR volatility expected)
SYMBOLS = ["BONKUSDT", "WIFUSDT", "DOGEUSDT", "SHIBUSDT", "PEPEUSDT",
           "SUIUSDT", "INJUSDT", "NEARUSDT", "APTUSDT", "TIAUSDT", "SEIUSDT"]

DAYS = 730
BARS_PER_YEAR = 2190


def ftod_signal(df, funding_series, fr_extreme=0.0003, price_stretch=0.05):
    """FToD entry signal.

    Args:
        df: OHLCV 4H DataFrame with 'open_time' (datetime)
        funding_series: funding rates aligned to df index (8h rates as fraction)
        fr_extreme: FR magnitude threshold (e.g. 0.0003 = 0.03% per 8h)
        price_stretch: 24h return threshold (e.g. 0.05 = 5%)
    Returns:
        Signal series in {-1, 0, +1}
    """
    # Hour of bar open (in UTC; df['open_time'] is UTC tz-naive)
    hours = df['open_time'].dt.hour
    is_post_funding = hours.isin([0, 8, 16]).values

    # Forward-fill funding to df index
    fr = funding_series.reindex(df.index, method='ffill').fillna(0).values

    # 24h return ≈ 6 4H-bars
    ret_24h = df['close'].pct_change(6).fillna(0).values

    fr_long_pay = fr > fr_extreme       # longs pay (over-crowded longs)
    fr_short_pay = fr < -fr_extreme     # shorts pay (over-crowded shorts)
    stretched_up = ret_24h > price_stretch
    stretched_down = ret_24h < -price_stretch

    sig = np.zeros(len(df), dtype=int)
    sig[is_post_funding & fr_long_pay & stretched_up] = -1   # short over-crowded longs
    sig[is_post_funding & fr_short_pay & stretched_down] = +1  # long over-crowded shorts
    return pd.Series(sig, index=df.index)


def sharpe(r, ppy=365):
    r = np.asarray(r); r = r[np.isfinite(r)]
    if len(r) < 5 or np.std(r, ddof=1) == 0: return 0.0
    return float(np.mean(r) / np.std(r, ddof=1) * np.sqrt(ppy))


def eq_to_daily(eq):
    eq = np.asarray(eq, dtype=float)
    d = eq[5::6]
    if len(d) < 2: d = eq[::6]
    return np.diff(d) / np.where(d[:-1] != 0, d[:-1], 1.0)


def run_bt(df, sig, sym, sl=0.04, tp=0.04, mhb=2):
    cost = get_cost_params(sym, "4h")
    return run_backtest(df, sig, strategy_name="FToD",
                        bars_per_year=BARS_PER_YEAR, leverage=1.0,
                        stop_loss_pct=sl, take_profit_pct=tp, max_hold_bars=mhb,
                        **cost)


async def main():
    t0 = time.time()
    print("=== Wave J8: FToD (Funding Time-of-Day Tail Reversal) validation ===\n")

    # Load data
    print("Loading OHLCV + funding data ...")
    ohlcv_cache = {}
    funding_cache = {}
    for s in SYMBOLS:
        df = await fetch_klines(s, "4h", DAYS)
        ohlcv_cache[s] = df
        try:
            fr_df = await fetch_bybit_funding_rate(s, DAYS)
        except Exception as e:
            print(f"  {s:<10} funding FAIL: {e}")
            funding_cache[s] = None
            continue
        if fr_df is None or fr_df.empty:
            print(f"  {s:<10} {len(df)} bars, no funding")
            funding_cache[s] = None
            continue
        # Align: turn fr_df into a Series indexed by df row index via merge_asof
        fr_df = fr_df.sort_values('timestamp').reset_index(drop=True)
        df_w = df.copy().sort_values('open_time').reset_index(drop=True)
        # Normalize dtypes to ns (pandas merge_asof requires matching datetime resolution)
        df_w['open_time'] = pd.to_datetime(df_w['open_time']).astype('datetime64[ns]')
        fr_df['timestamp'] = pd.to_datetime(fr_df['timestamp']).astype('datetime64[ns]')
        merged = pd.merge_asof(df_w[['open_time']],
                                fr_df.rename(columns={'timestamp':'open_time'}),
                                on='open_time', direction='backward')
        funding_cache[s] = merged['funding_rate'].fillna(0)
        print(f"  {s:<10} {len(df)} bars, {len(fr_df)} funding records")

    # ── Scan parameters ──
    print("\n=== Parameter scan ===")
    # Wider grid for proper search
    fr_thresholds = [0.0002, 0.0003, 0.0005, 0.001]    # 0.02%, 0.03%, 0.05%, 0.10%
    price_stretches = [0.03, 0.05, 0.08, 0.12]
    sl_vals = [0.03, 0.04, 0.06]
    tp_vals = [0.03, 0.04, 0.06, 0.08]
    mhb_vals = [2, 4, 6]

    n_trials = len(fr_thresholds) * len(price_stretches) * len(sl_vals) * len(tp_vals) * len(mhb_vals)
    print(f"Grid size: {n_trials} configurations × {len(SYMBOLS)} symbols")

    results = []
    best_per_symbol = {}
    for s in SYMBOLS:
        df = ohlcv_cache[s]
        fr_ser = funding_cache[s]
        if fr_ser is None:
            print(f"  {s} SKIP (no funding)")
            continue
        best = None
        for fr_t in fr_thresholds:
            for ps in price_stretches:
                sig = ftod_signal(df, fr_ser, fr_t, ps)
                n_sig = (sig != 0).sum()
                if n_sig < 10:
                    continue
                for sl in sl_vals:
                    for tp in tp_vals:
                        for mhb in mhb_vals:
                            try:
                                r = run_bt(df, sig, s, sl, tp, mhb)
                                m = r['metrics']
                                sh = float(m.get('sharpe_ratio') or 0)
                                ret = float(m.get('total_return_pct') or 0)
                                dd = float(m.get('max_drawdown_pct') or 0)
                                trades = int(m.get('total_trades') or 0)
                                if trades < 10:
                                    continue
                                results.append({
                                    'symbol': s, 'fr_t': fr_t, 'price_stretch': ps,
                                    'sl': sl, 'tp': tp, 'mhb': mhb,
                                    'sharpe': round(sh, 3), 'return_pct': round(ret, 2),
                                    'dd_pct': round(dd, 2), 'trades': trades,
                                    'n_sig': int(n_sig),
                                })
                                if best is None or sh > best['sharpe']:
                                    best = results[-1]
                            except Exception as e:
                                pass
        if best:
            best_per_symbol[s] = best
            print(f"  {s:<10} best: Sh={best['sharpe']:+.2f} ret={best['return_pct']:+.1f}% "
                  f"dd={best['dd_pct']:+.1f}% trades={best['trades']} "
                  f"params=(fr={best['fr_t']}, ps={best['price_stretch']}, sl={best['sl']}, tp={best['tp']}, mhb={best['mhb']})")
        else:
            print(f"  {s:<10} no valid result")

    # Summary across symbols
    print(f"\n=== Summary ===")
    print(f"Total trials: {len(results)}")
    sh_positive = sum(1 for r in results if r['sharpe'] > 0)
    sh_ge_1 = sum(1 for r in results if r['sharpe'] >= 1.0)
    sh_ge_1_5 = sum(1 for r in results if r['sharpe'] >= 1.5)
    sh_ge_2 = sum(1 for r in results if r['sharpe'] >= 2.0)
    print(f"  Sharpe > 0: {sh_positive}/{len(results)} ({sh_positive/max(len(results),1)*100:.0f}%)")
    print(f"  Sharpe ≥ 1.0: {sh_ge_1}")
    print(f"  Sharpe ≥ 1.5: {sh_ge_1_5}")
    print(f"  Sharpe ≥ 2.0: {sh_ge_2}")

    # Top 10
    results_sorted = sorted(results, key=lambda x: x['sharpe'], reverse=True)
    print(f"\nTop 10 (sym, params, Sh):")
    for r in results_sorted[:10]:
        print(f"  {r['symbol']:<10} Sh={r['sharpe']:+.2f} ret={r['return_pct']:+.1f}% "
              f"dd={r['dd_pct']:+.1f}% trades={r['trades']} "
              f"(fr={r['fr_t']}, ps={r['price_stretch']}, sl={r['sl']}, tp={r['tp']}, mhb={r['mhb']})")

    out = {
        "wave": "J8",
        "name": "FToD (Funding Time-of-Day Tail Reversal) — Researcher TOP1 hypothesis",
        "generated_at": datetime.now(timezone(timedelta(hours=9))).strftime("%Y-%m-%d %H:%M JST"),
        "hypothesis": "ファンディング決済直後の4Hバーで、FR極値 × 価格ストレッチを条件に逆張り",
        "n_symbols": len(SYMBOLS),
        "n_trials": len(results),
        "summary_counts": {
            "sh_positive": sh_positive, "sh_ge_1": sh_ge_1,
            "sh_ge_1_5": sh_ge_1_5, "sh_ge_2": sh_ge_2,
        },
        "best_per_symbol": best_per_symbol,
        "top10": results_sorted[:10],
        "runtime_sec": round(time.time() - t0, 1),
    }
    Path("/Users/nekonaomichi/crypto-lab/wave_j8_ftod.json").write_text(json.dumps(out, indent=2, default=str))
    print(f"\nSaved to wave_j8_ftod.json (runtime {out['runtime_sec']}s)")


if __name__ == "__main__":
    asyncio.run(main())

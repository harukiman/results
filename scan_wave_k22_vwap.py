"""Wave K22 — VWAP deviation mean-reversion.

仮説:
  4H bars で rolling VWAP からの乖離が極端な時 → 一時的な過剰反応 → mean-reversion

  VWAP = Σ(price × volume) / Σ(volume) over rolling window
  deviation = (close - VWAP) / VWAP

Entry:
  deviation < -threshold → long (買い戻し期待)
  deviation > +threshold → short
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

SYMBOLS = ["BTCUSDT", "ETHUSDT", "SOLUSDT", "BNBUSDT", "DOGEUSDT",
           "ADAUSDT", "AVAXUSDT", "LINKUSDT", "INJUSDT", "ARBUSDT"]
DAYS = 730


def vwap_signal(df, vwap_window=24, dev_threshold=0.03):
    """VWAP deviation signal."""
    typical_price = (df['high'] + df['low'] + df['close']) / 3
    pv = typical_price * df['volume']
    pv_sum = pv.rolling(vwap_window).sum()
    vol_sum = df['volume'].rolling(vwap_window).sum()
    vwap = pv_sum / (vol_sum + 1e-10)
    deviation = (df['close'] - vwap) / (vwap + 1e-10)

    sig = pd.Series(0, index=df.index)
    sig[deviation < -dev_threshold] = +1
    sig[deviation > dev_threshold] = -1
    sig.iloc[:vwap_window + 5] = 0
    return sig


def run_bt(df, sig, sym, sl=0.03, tp=0.04, mhb=12):
    cost = get_cost_params(sym, "4h")
    return run_backtest(df, sig, strategy_name="K22", bars_per_year=2190,
                        leverage=1.0, stop_loss_pct=sl, take_profit_pct=tp,
                        max_hold_bars=mhb, **cost)


def sharpe(r, ppy=365):
    r = np.asarray(r); r = r[np.isfinite(r)]
    if len(r) < 5 or np.std(r, ddof=1) == 0: return 0.0
    return float(np.mean(r) / np.std(r, ddof=1) * np.sqrt(ppy))


async def main():
    print("=== Wave K22: VWAP deviation MR ===\n")

    cache = {}
    for s in SYMBOLS:
        cache[s] = await fetch_klines(s, "4h", DAYS)

    vwap_windows = [12, 24, 48, 96]
    dev_thresholds = [0.02, 0.03, 0.05, 0.08]
    sls = [0.02, 0.03, 0.05]
    tps = [0.03, 0.04, 0.06]
    mhbs = [6, 12, 24]

    n_grid = len(vwap_windows) * len(dev_thresholds) * len(sls) * len(tps) * len(mhbs)
    print(f"Grid: {n_grid} configs × {len(SYMBOLS)} = {n_grid * len(SYMBOLS)} backtests\n")

    results = []
    best_per_symbol = {}
    for s in SYMBOLS:
        df = cache[s]
        best = None
        for vw in vwap_windows:
            for dt in dev_thresholds:
                sig = vwap_signal(df, vwap_window=vw, dev_threshold=dt)
                n_sig = (sig != 0).sum()
                if n_sig < 15:
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
                                    'symbol': s, 'vw': vw, 'dt': dt, 'sl': sl, 'tp': tp, 'mhb': mhb,
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
            print(f"  {s:<10} Sh={best['sharpe']:+5.2f} ret={best['return_pct']:+6.1f}% dd={best['dd_pct']:+6.1f}% tr={best['trades']:>3} (vw={best['vw']}, dt={best['dt']})")
        else:
            print(f"  {s:<10} no valid")

    results.sort(key=lambda x: x['sharpe'], reverse=True)
    print(f"\n=== Top 10 ===")
    for r in results[:10]:
        print(f"  {r['symbol']:<10} Sh={r['sharpe']:+.2f} ret={r['return_pct']:+.1f}% dd={r['dd_pct']:+.1f}% tr={r['trades']}")

    sh_pos = sum(1 for r in results if r['sharpe'] > 0)
    sh_ge_1 = sum(1 for r in results if r['sharpe'] >= 1.0)
    sh_ge_1_5 = sum(1 for r in results if r['sharpe'] >= 1.5)
    sh_ge_2 = sum(1 for r in results if r['sharpe'] >= 2.0)
    print(f"\nTotals: Sh>0 {sh_pos}/{len(results)} ({sh_pos/max(len(results),1)*100:.0f}%), ≥1: {sh_ge_1}, ≥1.5: {sh_ge_1_5}, ≥2: {sh_ge_2}")

    Path("/Users/nekonaomichi/crypto-lab/wave_k22_vwap.json").write_text(json.dumps({
        "wave": "K22", "name": "VWAP deviation MR",
        "n_trials": len(results),
        "summary_counts": {"sh_pos": sh_pos, "sh_ge_1": sh_ge_1, "sh_ge_1_5": sh_ge_1_5, "sh_ge_2": sh_ge_2},
        "best_per_symbol": best_per_symbol, "top10": results[:10],
    }, indent=2, default=str))
    print("Saved.")


if __name__ == "__main__":
    asyncio.run(main())

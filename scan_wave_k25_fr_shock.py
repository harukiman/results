"""Wave K25 — BTC funding rate shock contrarian.

仮説:
  Funding Rate が直近30日比で 3σ以上極端な瞬間 (z >= +3 or <= -3) →
  market は過熱、即時 contrarian short / long

  FOPD (J12) は FR+OI+Price の3項一致 condition だったが、本案は<strong>FR shock 単独</strong>。
  発火頻度が稀なので exposed period 短く、エッジ取りやすいか。
"""
import asyncio
import json
import sys
import numpy as np
import pandas as pd
from pathlib import Path
from datetime import datetime, timezone, timedelta

sys.path.insert(0, "/Users/nekonaomichi/crypto-lab")
from engine.data import fetch_klines, fetch_bybit_funding_rate
from engine.backtest import run_backtest
from engine.cost_config import get_cost_params

SYMBOLS = ["BTCUSDT", "ETHUSDT", "SOLUSDT", "BNBUSDT", "DOGEUSDT", "AVAXUSDT", "ADAUSDT", "LINKUSDT", "DOTUSDT"]
DAYS = 730


def fr_shock_signal(df, fr_series, z_threshold=3.0, window=180):
    """FR shock contrarian: z >= +threshold → short, <= -threshold → long."""
    df_w = df.copy().sort_values('open_time').reset_index(drop=True)
    df_w['open_time'] = pd.to_datetime(df_w['open_time']).astype('datetime64[ns]')
    if fr_series is None or fr_series.empty:
        return pd.Series(0, index=df_w.index)
    fr_df = fr_series.copy()
    fr_df['timestamp'] = pd.to_datetime(fr_df['timestamp']).astype('datetime64[ns]')
    fr_df = fr_df.sort_values('timestamp').reset_index(drop=True)
    m = pd.merge_asof(df_w[['open_time']], fr_df.rename(columns={'timestamp':'open_time'}),
                      on='open_time', direction='backward')
    fr = m['funding_rate'].fillna(0).values
    fr_s = pd.Series(fr)
    mean = fr_s.rolling(window).mean()
    std = fr_s.rolling(window).std()
    z = (fr_s - mean) / (std + 1e-10)
    z = z.fillna(0).values
    sig = np.zeros(len(df_w), dtype=int)
    sig[z >= z_threshold] = -1   # FR shock high → longs over-paying → short
    sig[z <= -z_threshold] = +1  # FR shock low → shorts over-paying → long
    sig[:window + 5] = 0
    return pd.Series(sig, index=df_w.index)


def run_bt(df, sig, sym, sl=0.04, tp=0.06, mhb=12):
    cost = get_cost_params(sym, "4h")
    return run_backtest(df, sig, strategy_name="K25", bars_per_year=2190,
                        leverage=1.0, stop_loss_pct=sl, take_profit_pct=tp,
                        max_hold_bars=mhb, **cost)


def sharpe(r, ppy=365):
    r = np.asarray(r); r = r[np.isfinite(r)]
    if len(r) < 5 or np.std(r, ddof=1) == 0: return 0.0
    return float(np.mean(r) / np.std(r, ddof=1) * np.sqrt(ppy))


async def main():
    print("=== Wave K25: FR shock contrarian ===\n")

    z_thresholds = [2.0, 2.5, 3.0, 3.5]
    windows = [90, 180, 360]
    sls = [0.03, 0.04, 0.06]
    tps = [0.04, 0.06, 0.08]
    mhbs = [6, 12, 24]
    n_grid = len(z_thresholds) * len(windows) * len(sls) * len(tps) * len(mhbs)
    print(f"Grid: {n_grid} configs × {len(SYMBOLS)} = {n_grid * len(SYMBOLS)} backtests\n")

    results = []
    best_per_symbol = {}
    for sym in SYMBOLS:
        df = await fetch_klines(sym, "4h", DAYS)
        try:
            fr = await fetch_bybit_funding_rate(sym, DAYS)
        except Exception:
            print(f"  {sym} FR fetch failed"); continue
        if fr is None or fr.empty:
            print(f"  {sym} no FR data"); continue
        best = None
        for zt in z_thresholds:
            for w in windows:
                sig = fr_shock_signal(df, fr, z_threshold=zt, window=w)
                n_sig = (sig != 0).sum()
                if n_sig < 10:
                    continue
                for sl in sls:
                    for tp in tps:
                        for mhb in mhbs:
                            try:
                                r = run_bt(df, sig, sym, sl, tp, mhb)
                                m = r['metrics']
                                sh = float(m.get('sharpe_ratio') or 0)
                                ret = float(m.get('total_return_pct') or 0)
                                dd = float(m.get('max_drawdown_pct') or 0)
                                trades = int(m.get('total_trades') or 0)
                                if trades < 10:
                                    continue
                                row = {
                                    'symbol': sym, 'zt': zt, 'w': w, 'sl': sl, 'tp': tp, 'mhb': mhb,
                                    'sharpe': round(sh, 3), 'return_pct': round(ret, 2),
                                    'dd_pct': round(dd, 2), 'trades': trades,
                                }
                                results.append(row)
                                if best is None or sh > best['sharpe']:
                                    best = row
                            except Exception:
                                pass
        if best:
            best_per_symbol[sym] = best
            print(f"  {sym:<10} Sh={best['sharpe']:+5.2f} ret={best['return_pct']:+6.1f}% dd={best['dd_pct']:+6.1f}% tr={best['trades']:>3}")
        else:
            print(f"  {sym:<10} no valid")

    results.sort(key=lambda x: x['sharpe'], reverse=True)
    print(f"\n=== Top 10 ===")
    for r in results[:10]:
        print(f"  {r['symbol']:<10} Sh={r['sharpe']:+.2f} ret={r['return_pct']:+.1f}% dd={r['dd_pct']:+.1f}% tr={r['trades']}")
    sh_pos = sum(1 for r in results if r['sharpe'] > 0)
    sh_ge_1 = sum(1 for r in results if r['sharpe'] >= 1.0)
    sh_ge_1_5 = sum(1 for r in results if r['sharpe'] >= 1.5)
    sh_ge_2 = sum(1 for r in results if r['sharpe'] >= 2.0)
    print(f"\nTotals: Sh>0 {sh_pos}/{len(results)} ({sh_pos/max(len(results),1)*100:.0f}%), ≥1: {sh_ge_1}, ≥1.5: {sh_ge_1_5}, ≥2: {sh_ge_2}")

    Path("/Users/nekonaomichi/crypto-lab/wave_k25_fr_shock.json").write_text(json.dumps({
        "wave": "K25", "name": "FR shock contrarian",
        "n_trials": len(results),
        "summary_counts": {"sh_pos": sh_pos, "sh_ge_1": sh_ge_1, "sh_ge_1_5": sh_ge_1_5, "sh_ge_2": sh_ge_2},
        "best_per_symbol": best_per_symbol, "top10": results[:10],
    }, indent=2, default=str))
    print("Saved.")


if __name__ == "__main__":
    asyncio.run(main())

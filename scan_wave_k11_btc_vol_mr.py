"""Wave K11 — BTC vol_z mean-reversion strategy.

仮説:
  BTC vol_z (60バー実現ボラの360バー Z-score) が極端値の時:
    - vol_z << -1 (極端な低ボラ): 圧縮後ブレイク準備、ロング/ショートのトレンド bias
    - vol_z >> +2 (極端な高ボラ): vol spike 後 mean-revert → カウンタートレード

  単純な vol_z 閾値だけでなく、direction bias 加えて検証:
    - 低 vol_z + 上昇トレンド → long (圧縮後上抜けを期待)
    - 低 vol_z + 下降トレンド → short
    - 高 vol_z (vol spike) + 直前下落 → long (反転狙い)
    - 高 vol_z + 直前上昇 → short (利確売り)
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

SYMBOLS = ["BTCUSDT", "ETHUSDT", "SOLUSDT", "BNBUSDT"]
DAYS = 730
BARS_PER_YEAR = 2190


def btc_vol_mr_signal(df, vol_z_low=-1.0, vol_z_high=2.0, trend_window=20):
    """vol_z extreme + direction bias signal."""
    close = df['close'].values
    ret = np.zeros_like(close)
    ret[1:] = (close[1:] - close[:-1]) / close[:-1]
    rv = pd.Series(ret).rolling(60).std() * np.sqrt(BARS_PER_YEAR) * 100
    rvm = rv.rolling(360).mean()
    rvs = rv.rolling(360).std()
    vol_z = (rv - rvm) / (rvs + 1e-10)
    vol_z = vol_z.fillna(0).values

    # Trend (EMA-based)
    ema_fast = pd.Series(close).ewm(span=trend_window).mean().values
    ema_slow = pd.Series(close).ewm(span=trend_window * 3).mean().values
    bullish = ema_fast > ema_slow
    bearish = ema_fast < ema_slow

    # Recent return for vol spike reversal
    recent_ret = pd.Series(close).pct_change(6).fillna(0).values

    sig = np.zeros(len(df), dtype=int)
    # Low vol + bullish → long (compression breakout)
    sig[(vol_z < vol_z_low) & bullish] = +1
    sig[(vol_z < vol_z_low) & bearish] = -1
    # High vol + recent down → long (reversal)
    sig[(vol_z > vol_z_high) & (recent_ret < -0.05)] = +1
    sig[(vol_z > vol_z_high) & (recent_ret > 0.05)] = -1
    sig[:380] = 0
    return pd.Series(sig, index=df.index)


def run_bt(df, sig, sym, sl=0.04, tp=0.06, mhb=12):
    cost = get_cost_params(sym, "4h")
    return run_backtest(df, sig, strategy_name="K11", bars_per_year=BARS_PER_YEAR,
                        leverage=1.0, stop_loss_pct=sl, take_profit_pct=tp,
                        max_hold_bars=mhb, **cost)


def sharpe(r, ppy=365):
    r = np.asarray(r); r = r[np.isfinite(r)]
    if len(r) < 5 or np.std(r, ddof=1) == 0: return 0.0
    return float(np.mean(r) / np.std(r, ddof=1) * np.sqrt(ppy))


async def main():
    print("=== Wave K11: BTC vol_z mean-reversion ===\n")

    cache = {}
    for s in SYMBOLS:
        cache[s] = await fetch_klines(s, "4h", DAYS)

    vol_z_lows = [-2.0, -1.5, -1.0, -0.5]
    vol_z_highs = [1.0, 1.5, 2.0, 2.5]
    trend_windows = [10, 20, 40]
    sls = [0.03, 0.04, 0.06]
    tps = [0.04, 0.06, 0.08]
    mhbs = [6, 12, 24]

    n_grid = len(vol_z_lows) * len(vol_z_highs) * len(trend_windows) * len(sls) * len(tps) * len(mhbs)
    print(f"Grid: {n_grid} configs × {len(SYMBOLS)} = {n_grid * len(SYMBOLS)} backtests\n")

    results = []
    best_per_symbol = {}
    for s in SYMBOLS:
        df = cache[s]
        best = None
        for vzl in vol_z_lows:
            for vzh in vol_z_highs:
                for tw in trend_windows:
                    sig = btc_vol_mr_signal(df, vol_z_low=vzl, vol_z_high=vzh, trend_window=tw)
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
                                        'symbol': s, 'vzl': vzl, 'vzh': vzh, 'tw': tw,
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
    for s in SYMBOLS:
        if s in best_per_symbol:
            b = best_per_symbol[s]
            print(f"  {s:<10} Sh={b['sharpe']:+5.2f} ret={b['return_pct']:+6.1f}% dd={b['dd_pct']:+6.1f}% tr={b['trades']:>3} (vzl={b['vzl']}, vzh={b['vzh']}, tw={b['tw']})")
        else:
            print(f"  {s:<10} no result")

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
        "wave": "K11", "name": "BTC vol_z mean-reversion",
        "generated_at": datetime.now(timezone(timedelta(hours=9))).strftime("%Y-%m-%d %H:%M JST"),
        "n_trials": len(results),
        "summary_counts": {"sh_pos": sh_pos, "sh_ge_1": sh_ge_1, "sh_ge_1_5": sh_ge_1_5, "sh_ge_2": sh_ge_2},
        "best_per_symbol": best_per_symbol, "top10": results[:10],
    }
    Path("/Users/nekonaomichi/crypto-lab/wave_k11_btc_vol_mr.json").write_text(json.dumps(out, indent=2, default=str))
    print("\nSaved.")


if __name__ == "__main__":
    asyncio.run(main())

"""Wave K6 — Pure Funding Carry strategy.

仮説:
  Funding Rate (FR) が極端に高い (longs pay) → short position で carry 受取
  FR が極端に低い (shorts pay) → long position で carry 受取

  純粋にキャリー収益狙い、価格方向予測なし。
  FOPD と異なる:
    - FOPD: FR + OI + Price 3項一致で反転狙い (directional)
    - Pure Funding Carry: FR一項のみで持続的キャリー (non-directional, hedge的)

エントリー: FR_smooth (EMA 10 cycles ≈ 80h) が閾値超え
エグジット: FR が反対側 or 中立に戻る、または timeout

Test: Major+LargeCap (FRが信頼できる流動性のある銘柄)
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

SYMBOLS = ["BTCUSDT", "ETHUSDT", "SOLUSDT", "BNBUSDT", "XRPUSDT",
           "ADAUSDT", "AVAXUSDT", "LINKUSDT", "DOTUSDT"]
DAYS = 730
BARS_PER_YEAR = 2190


def funding_carry_signal(df, fr_series, smooth_span=10, threshold_pct=0.001):
    """Pure funding carry: smooth FR, take counter-position when extreme."""
    df_w = df.copy().sort_values('open_time').reset_index(drop=True)
    df_w['open_time'] = pd.to_datetime(df_w['open_time']).astype('datetime64[ns]')
    if fr_series is None or fr_series.empty:
        return pd.Series(0, index=df_w.index)
    fr_df = fr_series.copy()
    fr_df['timestamp'] = pd.to_datetime(fr_df['timestamp']).astype('datetime64[ns]')
    fr_df = fr_df.sort_values('timestamp').reset_index(drop=True)
    m = pd.merge_asof(df_w[['open_time']], fr_df.rename(columns={'timestamp':'open_time'}), on='open_time', direction='backward')
    fr = m['funding_rate'].fillna(0).values

    # Smooth FR with EMA
    fr_smooth = pd.Series(fr).ewm(span=smooth_span).mean().values

    sig = np.zeros(len(df_w), dtype=int)
    # Long when FR very negative (shorts pay): we long to receive
    sig[fr_smooth < -threshold_pct] = +1
    # Short when FR very positive (longs pay): we short to receive
    sig[fr_smooth > threshold_pct] = -1
    sig[:smooth_span + 5] = 0
    return pd.Series(sig, index=df_w.index)


def eq_to_daily(eq):
    eq = np.asarray(eq, dtype=float)
    d = eq[5::6]
    if len(d) < 2: d = eq[::6]
    return np.diff(d) / np.where(d[:-1] != 0, d[:-1], 1.0)


def sharpe(r, ppy=365):
    r = np.asarray(r); r = r[np.isfinite(r)]
    if len(r) < 5 or np.std(r, ddof=1) == 0: return 0.0
    return float(np.mean(r) / np.std(r, ddof=1) * np.sqrt(ppy))


def run_bt(df, sig, sym, sl=0.05, tp=0.05, mhb=18):
    cost = get_cost_params(sym, "4h")
    return run_backtest(df, sig, strategy_name="K6", bars_per_year=BARS_PER_YEAR,
                        leverage=1.0, stop_loss_pct=sl, take_profit_pct=tp,
                        max_hold_bars=mhb, **cost)


async def main():
    print("=== Wave K6: Pure Funding Carry ===\n")

    # Param grid
    smooth_spans = [5, 10, 20]
    thresholds = [0.0005, 0.001, 0.002, 0.005]  # 0.05%, 0.1%, 0.2%, 0.5% per 8h
    sls = [0.03, 0.05, 0.08]
    tps = [0.03, 0.05, 0.08]
    mhbs = [6, 12, 18, 24]

    n_grid = len(smooth_spans) * len(thresholds) * len(sls) * len(tps) * len(mhbs)
    print(f"Grid: {n_grid} configs × {len(SYMBOLS)} = {n_grid * len(SYMBOLS)} backtests\n")

    results = []
    best_per_symbol = {}
    for s in SYMBOLS:
        df = await fetch_klines(s, "4h", DAYS)
        try:
            fr_df = await fetch_bybit_funding_rate(s, DAYS)
        except Exception:
            print(f"  {s} FR fetch failed"); continue
        if fr_df is None or fr_df.empty:
            print(f"  {s} no FR data"); continue
        best = None
        for span in smooth_spans:
            for thr in thresholds:
                sig = funding_carry_signal(df, fr_df, smooth_span=span, threshold_pct=thr)
                n_sig = (sig != 0).sum()
                if n_sig < 20:
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
                                    'symbol': s, 'span': span, 'thr': thr,
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
            print(f"  {s:<10} best Sh={best['sharpe']:+.2f} ret={best['return_pct']:+.1f}% dd={best['dd_pct']:+.1f}% tr={best['trades']}")
        else:
            print(f"  {s:<10} no valid result")

    results.sort(key=lambda x: x['sharpe'], reverse=True)
    print(f"\n=== Top 10 ===")
    for r in results[:10]:
        print(f"  {r['symbol']:<10} Sh={r['sharpe']:+.2f} ret={r['return_pct']:+.1f}% dd={r['dd_pct']:+.1f}% tr={r['trades']} (span={r['span']}, thr={r['thr']})")

    sh_pos = sum(1 for r in results if r['sharpe'] > 0)
    sh_ge_1 = sum(1 for r in results if r['sharpe'] >= 1.0)
    sh_ge_1_5 = sum(1 for r in results if r['sharpe'] >= 1.5)
    sh_ge_2 = sum(1 for r in results if r['sharpe'] >= 2.0)
    print(f"\nTotals: Sh>0 {sh_pos}/{len(results)} ({sh_pos/max(len(results),1)*100:.0f}%), ≥1.0: {sh_ge_1}, ≥1.5: {sh_ge_1_5}, ≥2.0: {sh_ge_2}")

    out = {
        "wave": "K6", "name": "Pure Funding Carry",
        "generated_at": datetime.now(timezone(timedelta(hours=9))).strftime("%Y-%m-%d %H:%M JST"),
        "n_trials": len(results),
        "summary_counts": {"sh_pos": sh_pos, "sh_ge_1": sh_ge_1, "sh_ge_1_5": sh_ge_1_5, "sh_ge_2": sh_ge_2},
        "best_per_symbol": best_per_symbol, "top10": results[:10],
    }
    Path("/Users/nekonaomichi/crypto-lab/wave_k6_funding_carry.json").write_text(json.dumps(out, indent=2, default=str))
    print("\nSaved.")


if __name__ == "__main__":
    asyncio.run(main())

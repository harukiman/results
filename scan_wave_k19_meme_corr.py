"""Wave K19 — Meme correlation breakdown trade.

仮説:
  DOGE-SHIB は通常 +0.7 相関 (Meme共通要因)。
  この相関が急減した時 → ローカルダイバージェンス → 回帰トレード。

実装 (simple):
  rolling_corr_30 = corr(DOGE returns, SHIB returns, 30 bars)
  When rolling_corr_30 < threshold:
    - check which is leading down → long the laggard (回帰期待)
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

PAIRS = [
    ("DOGEUSDT", "SHIBUSDT"),
    ("BONKUSDT", "WIFUSDT"),
    ("PEPEUSDT", "DOGEUSDT"),
]
DAYS = 730


def meme_corr_signal_pair(df1, df2, corr_window=30, corr_threshold=0.2, lookback_ret=6):
    """Signal for first asset, based on its lag to second when corr drops."""
    df1 = df1.copy().reset_index(drop=True)
    df2 = df2.copy().reset_index(drop=True)
    # Align
    df1['open_time'] = pd.to_datetime(df1['open_time'])
    df2['open_time'] = pd.to_datetime(df2['open_time'])
    merged = pd.merge_asof(df1[['open_time', 'close']].rename(columns={'close': 'c1'}),
                            df2[['open_time', 'close']].rename(columns={'close': 'c2'}),
                            on='open_time', direction='backward')
    r1 = merged['c1'].pct_change()
    r2 = merged['c2'].pct_change()
    rolling_corr = r1.rolling(corr_window).corr(r2)
    # Recent returns
    ret1_recent = merged['c1'].pct_change(lookback_ret)
    ret2_recent = merged['c2'].pct_change(lookback_ret)
    # If correlation drops below threshold AND asset 1 down while asset 2 up → long asset 1 (回帰)
    sig = pd.Series(0, index=merged.index)
    low_corr = rolling_corr < corr_threshold
    # asset 1 lagging down
    cond_long = low_corr & (ret1_recent < -0.02) & (ret2_recent > 0.01)
    cond_short = low_corr & (ret1_recent > 0.02) & (ret2_recent < -0.01)
    sig[cond_long] = +1
    sig[cond_short] = -1
    sig.iloc[:corr_window + 10] = 0
    return sig


def run_bt(df, sig, sym, sl=0.04, tp=0.06, mhb=12):
    cost = get_cost_params(sym, "4h")
    return run_backtest(df, sig, strategy_name="K19", bars_per_year=2190,
                        leverage=1.0, stop_loss_pct=sl, take_profit_pct=tp,
                        max_hold_bars=mhb, **cost)


def sharpe(r, ppy=365):
    r = np.asarray(r); r = r[np.isfinite(r)]
    if len(r) < 5 or np.std(r, ddof=1) == 0: return 0.0
    return float(np.mean(r) / np.std(r, ddof=1) * np.sqrt(ppy))


async def main():
    print("=== Wave K19: Meme correlation breakdown ===\n")

    results = []
    for sym1, sym2 in PAIRS:
        df1 = await fetch_klines(sym1, "4h", DAYS)
        df2 = await fetch_klines(sym2, "4h", DAYS)
        print(f"\n{sym1} vs {sym2}:")

        best = None
        for cw in [20, 30, 60]:
            for ct in [-0.2, 0.0, 0.2, 0.4]:
                sig = meme_corr_signal_pair(df1, df2, corr_window=cw, corr_threshold=ct)
                n_sig = (sig != 0).sum()
                if n_sig < 15:
                    continue
                for sl in [0.03, 0.04, 0.06]:
                    for tp in [0.04, 0.06, 0.08]:
                        try:
                            r = run_bt(df1, sig, sym1, sl, tp, 12)
                            m = r['metrics']
                            sh = float(m.get('sharpe_ratio') or 0)
                            ret = float(m.get('total_return_pct') or 0)
                            dd = float(m.get('max_drawdown_pct') or 0)
                            trades = int(m.get('total_trades') or 0)
                            if trades < 15:
                                continue
                            row = {
                                'pair': f"{sym1}/{sym2}", 'cw': cw, 'ct': ct, 'sl': sl, 'tp': tp,
                                'sharpe': round(sh, 3), 'return_pct': round(ret, 2),
                                'dd_pct': round(dd, 2), 'trades': trades,
                            }
                            results.append(row)
                            if best is None or sh > best['sharpe']:
                                best = row
                        except Exception:
                            pass
        if best:
            print(f"  Best Sh={best['sharpe']:+.2f} ret={best['return_pct']:+.1f}% dd={best['dd_pct']:+.1f}% tr={best['trades']}")
        else:
            print(f"  No valid result")

    results.sort(key=lambda x: x['sharpe'], reverse=True)
    print(f"\n=== Top 10 ===")
    for r in results[:10]:
        print(f"  {r['pair']:<20} Sh={r['sharpe']:+.2f} ret={r['return_pct']:+.1f}% dd={r['dd_pct']:+.1f}% tr={r['trades']}")
    sh_pos = sum(1 for r in results if r['sharpe'] > 0)
    sh_ge_1 = sum(1 for r in results if r['sharpe'] >= 1.0)
    sh_ge_1_5 = sum(1 for r in results if r['sharpe'] >= 1.5)
    sh_ge_2 = sum(1 for r in results if r['sharpe'] >= 2.0)
    print(f"\nTotals: Sh>0 {sh_pos}/{len(results)} ({sh_pos/max(len(results),1)*100:.0f}%), ≥1: {sh_ge_1}, ≥1.5: {sh_ge_1_5}, ≥2.0: {sh_ge_2}")

    Path("/Users/nekonaomichi/crypto-lab/wave_k19_meme_corr.json").write_text(json.dumps({
        "wave": "K19", "name": "Meme correlation breakdown",
        "n_trials": len(results),
        "summary_counts": {"sh_pos": sh_pos, "sh_ge_1": sh_ge_1, "sh_ge_1_5": sh_ge_1_5, "sh_ge_2": sh_ge_2},
        "top10": results[:10],
    }, indent=2, default=str))
    print("Saved.")


if __name__ == "__main__":
    asyncio.run(main())

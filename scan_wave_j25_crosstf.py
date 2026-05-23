"""Wave J25 — Cross-timeframe robustness for ATR_Ratio_Compression.

仮説検証:
  ATR_Ratio (4H で Sh+2.78) が他の時間軸でも機能するか?
  parameters は時間単位を保つ ( = TF ratio に応じてバー数調整 ):
    4H: atr_short=7, atr_long=56, ema_fast=20, ema_slow=80
    1H: atr_short=28, atr_long=224, ema_fast=80, ema_slow=320 (4x)
    8H: atr_short=4, atr_long=28, ema_fast=10, ema_slow=40 (0.5x)
  ※ MEXC API は 8H 直接取得不可、4H aggregateで近似

期待:
  本物のエッジ → 他TFでも残存
  時間軸固有の overfit → 他TFで消える
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

# Symbols with both 4H and 1H cached
SYMBOLS = ["BTCUSDT", "ETHUSDT", "DOGEUSDT", "AVAXUSDT", "ADAUSDT", "LINKUSDT"]
PARAMS_4H = {"atr_short": 7, "atr_long": 56, "threshold": 0.6, "ema_fast": 20, "ema_slow": 80}
PARAMS_1H = {"atr_short": 28, "atr_long": 224, "threshold": 0.6, "ema_fast": 80, "ema_slow": 320}
# 8H aggregation from 4H by sum/last
PARAMS_8H = {"atr_short": 4, "atr_long": 28, "threshold": 0.6, "ema_fast": 10, "ema_slow": 40}
EXIT_4H = {"stop_loss_pct": 0.04, "take_profit_pct": 0.08, "max_hold_bars": 24}
EXIT_1H = {"stop_loss_pct": 0.04, "take_profit_pct": 0.08, "max_hold_bars": 96}  # 4x
EXIT_8H = {"stop_loss_pct": 0.04, "take_profit_pct": 0.08, "max_hold_bars": 12}  # 0.5x
DAYS = 365  # only 365d for 1h cache


def atr_ratio_signal(df, **k):
    atr_s = (df['high'] - df['low']).rolling(k['atr_short']).mean()
    atr_l = (df['high'] - df['low']).rolling(k['atr_long']).mean()
    comp = atr_s < atr_l * k['threshold']
    ef = df['close'].ewm(span=k['ema_fast']).mean()
    es = df['close'].ewm(span=k['ema_slow']).mean()
    sig = pd.Series(0, index=df.index)
    sig[comp & (ef > es)] = 1
    sig[comp & (ef < es)] = -1
    warmup = max(k['atr_long'], k['ema_slow']) + 5
    sig.iloc[:warmup] = 0
    return sig


def aggregate_4h_to_8h(df_4h):
    """Aggregate 4h bars to 8h by pairs."""
    df = df_4h.copy().sort_values('open_time').reset_index(drop=True)
    # Pair odd/even (each 2 4h bars = 1 8h bar)
    df['pair_idx'] = df.index // 2
    agg = df.groupby('pair_idx').agg({
        'open_time': 'first', 'open': 'first',
        'high': 'max', 'low': 'min', 'close': 'last',
        'volume': 'sum'
    }).reset_index(drop=True)
    return agg


def run_bt(df, sig, sym, interval, exit_kw):
    cost = get_cost_params(sym, interval)
    # Adjust bars_per_year per interval
    bars_per_year = 2190 if interval == "4h" else (8760 if interval == "1h" else 1095)
    return run_backtest(df, sig, strategy_name="cTF", bars_per_year=bars_per_year,
                        leverage=1.0, **exit_kw, **cost)


def sharpe(r, ppy=365):
    r = np.asarray(r); r = r[np.isfinite(r)]
    if len(r) < 5 or np.std(r, ddof=1) == 0: return 0.0
    return float(np.mean(r) / np.std(r, ddof=1) * np.sqrt(ppy))


async def main():
    print("=== Wave J25: Cross-timeframe robustness (4H baseline) ===\n")

    results = {}
    for s in SYMBOLS:
        results[s] = {}
        # 4H baseline
        df_4h = await fetch_klines(s, "4h", DAYS)
        sig_4h = atr_ratio_signal(df_4h, **PARAMS_4H)
        if (sig_4h != 0).sum() < 5:
            results[s]["4h"] = {"note": "no signals"}
        else:
            r = run_bt(df_4h, sig_4h, s, "4h", EXIT_4H)
            m = r['metrics']
            results[s]["4h"] = {
                "sharpe": round(float(m.get('sharpe_ratio') or 0), 3),
                "return_pct": round(float(m.get('total_return_pct') or 0), 2),
                "dd_pct": round(float(m.get('max_drawdown_pct') or 0), 2),
                "trades": int(m.get('total_trades') or 0),
                "n_signal_bars": int((sig_4h != 0).sum()),
            }

        # 1H (scaled params)
        try:
            df_1h = await fetch_klines(s, "1h", DAYS)
        except Exception:
            df_1h = None
        if df_1h is not None and len(df_1h) > 200:
            sig_1h = atr_ratio_signal(df_1h, **PARAMS_1H)
            if (sig_1h != 0).sum() < 5:
                results[s]["1h"] = {"note": "no signals"}
            else:
                r = run_bt(df_1h, sig_1h, s, "1h", EXIT_1H)
                m = r['metrics']
                results[s]["1h"] = {
                    "sharpe": round(float(m.get('sharpe_ratio') or 0), 3),
                    "return_pct": round(float(m.get('total_return_pct') or 0), 2),
                    "dd_pct": round(float(m.get('max_drawdown_pct') or 0), 2),
                    "trades": int(m.get('total_trades') or 0),
                    "n_signal_bars": int((sig_1h != 0).sum()),
                }
        else:
            results[s]["1h"] = {"note": "no data"}

        # 8H (aggregated from 4H)
        df_8h = aggregate_4h_to_8h(df_4h)
        sig_8h = atr_ratio_signal(df_8h, **PARAMS_8H)
        if (sig_8h != 0).sum() < 5:
            results[s]["8h"] = {"note": "no signals"}
        else:
            r = run_bt(df_8h, sig_8h, s, "8h", EXIT_8H)
            m = r['metrics']
            results[s]["8h"] = {
                "sharpe": round(float(m.get('sharpe_ratio') or 0), 3),
                "return_pct": round(float(m.get('total_return_pct') or 0), 2),
                "dd_pct": round(float(m.get('max_drawdown_pct') or 0), 2),
                "trades": int(m.get('total_trades') or 0),
                "n_signal_bars": int((sig_8h != 0).sum()),
            }

        print(f"  {s:<10}: ", end="")
        for tf in ["1h", "4h", "8h"]:
            r = results[s][tf]
            if "sharpe" in r:
                print(f"{tf}=Sh{r['sharpe']:+.2f}({r['trades']}tr) ", end="")
            else:
                print(f"{tf}=N/A ", end="")
        print()

    # Aggregate stats
    print("\n=== Summary ===")
    for tf in ["1h", "4h", "8h"]:
        valid = [results[s][tf]['sharpe'] for s in SYMBOLS
                 if 'sharpe' in results[s].get(tf, {})]
        if valid:
            pos = sum(1 for sh in valid if sh > 0)
            print(f"  {tf}: {pos}/{len(valid)} symbols with Sh>0, mean Sh = {np.mean(valid):+.2f}, max = {max(valid):+.2f}")

    out = {
        "wave": "J25", "name": "Cross-timeframe robustness",
        "generated_at": datetime.now(timezone(timedelta(hours=9))).strftime("%Y-%m-%d %H:%M JST"),
        "symbols": SYMBOLS,
        "per_symbol": results,
    }
    Path("/Users/nekonaomichi/crypto-lab/wave_j25_crosstf.json").write_text(json.dumps(out, indent=2, default=str))
    print("\nSaved.")


if __name__ == "__main__":
    asyncio.run(main())

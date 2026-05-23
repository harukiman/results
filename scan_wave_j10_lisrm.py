"""Wave J10 — LISRM (L1 Intra-Sector Rotation Momentum) validation.

Hypothesis (Researcher TOP3):
  L1セクター内 (SOL/AVAX/ATOM/INJ/NEAR/APT/SUI/TIA/SEI) でセクター内ランキング
  上位↔下位のクロスセクション・モメンタムが4Hで存在する。CrossMomentum (棄却)
  は2銘柄ペア相関で失敗したが、本案はセクター内9銘柄のランキング rotation 戦略。
  市場中立 L/S でBTCベータを除去 → 既存生存者と独立な"narrative alpha"を抽出。

Entry:
  rank = sort(universe by return_72h)  # 過去3日リターンランキング
  top3 = ranks[:3]   ← long
  bot3 = ranks[-3:]  ← short
  rebalance every 4 bars (16h)

Symbols: L1 9個
TF: 4H
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

# L1 sector (no AVAX in pre-2024 sense, but treating as L1 alternative)
UNIVERSE = ["SOLUSDT", "AVAXUSDT", "ATOMUSDT", "INJUSDT",
            "NEARUSDT", "APTUSDT", "SUIUSDT", "TIAUSDT", "SEIUSDT"]

DAYS = 730
BARS_PER_YEAR = 2190


def sharpe(r, ppy=365):
    r = np.asarray(r); r = r[np.isfinite(r)]
    if len(r) < 5 or np.std(r, ddof=1) == 0: return 0.0
    return float(np.mean(r) / np.std(r, ddof=1) * np.sqrt(ppy))


async def main():
    t0 = time.time()
    print("=== Wave J10: LISRM (L1 Cross-Section Rotation) validation ===\n")

    # Load all symbols
    print("Loading data ...")
    data = {}
    for s in UNIVERSE:
        df = await fetch_klines(s, "4h", DAYS)
        data[s] = df.set_index('open_time')['close']
        print(f"  {s:<10} {len(df)} bars")

    # Align all on common index
    prices_df = pd.DataFrame(data).sort_index()
    # Drop NaN rows (early period before all symbols listed)
    prices_df = prices_df.dropna()
    print(f"\nCommon period: {prices_df.index[0]} → {prices_df.index[-1]}, {len(prices_df)} bars")

    # ── Parameter scan ──
    # lookback bars (rolling return window): 18 bars (3 days), 36 bars (6d), 72 (12d), 120 (20d)
    # rebalance interval (bars): 4 (16h), 6 (24h), 12 (48h), 24 (96h)
    # top_n / bot_n: 2, 3
    lookbacks = [18, 36, 72, 120]
    rebal_intervals = [4, 6, 12, 24]
    pick_ns = [2, 3]

    n_trials = len(lookbacks) * len(rebal_intervals) * len(pick_ns)
    print(f"\nGrid: {n_trials} configurations")

    results = []
    eq_curves = {}  # store best curves for inspection

    for lookback in lookbacks:
        rets_n = prices_df.pct_change(lookback)
        for rebal in rebal_intervals:
            # At each rebalance bar, rank cross-section, build L/S basket weights
            for top_n in pick_ns:
                bot_n = top_n
                # Build position weights per bar
                weights = pd.DataFrame(0.0, index=prices_df.index, columns=UNIVERSE)
                rebal_bars = list(range(lookback, len(prices_df), rebal))
                cur_w = None
                for i in range(lookback, len(prices_df)):
                    if i in rebal_bars or cur_w is None:
                        # Compute current ranking
                        r_now = rets_n.iloc[i]
                        if r_now.isna().any():
                            cur_w = pd.Series(0.0, index=UNIVERSE)
                        else:
                            ranked = r_now.sort_values()
                            longs = ranked.index[-top_n:]
                            shorts = ranked.index[:bot_n]
                            cur_w = pd.Series(0.0, index=UNIVERSE)
                            for s in longs:
                                cur_w[s] = 1.0 / top_n
                            for s in shorts:
                                cur_w[s] = -1.0 / bot_n
                    weights.iloc[i] = cur_w.values

                # Compute portfolio returns (bar-by-bar)
                bar_rets = prices_df.pct_change().fillna(0)
                # Use weights at start of period (lag by 1 to avoid lookahead)
                lagged_w = weights.shift(1).fillna(0)
                port_rets_per_bar = (lagged_w * bar_rets).sum(axis=1)

                # Apply costs at rebalance
                # Trade volume = sum of |weight changes| per rebalance
                w_change = lagged_w.diff().abs().sum(axis=1)
                # Cost per unit traded: 0.04% taker + 0.03% slippage (alt avg) = ~0.07% per side
                # For L/S basket the gross trade is ~|w_change|, but each side trades separately
                cost_per_trade = 0.0007  # 0.07% taker+slip avg
                port_rets_after_cost = port_rets_per_bar - w_change * cost_per_trade

                # Funding cost: ~0.01%/8h average per side; L/S nets close to 0, ignore for now
                # (Approximation; actual depends on which side has higher FR)

                # Daily returns: aggregate every 6 4H bars
                eq = (1 + port_rets_after_cost).cumprod()
                # Sample daily
                daily_eq = eq.values[5::6]
                daily_rets = np.diff(daily_eq) / daily_eq[:-1]

                sh = sharpe(daily_rets, ppy=365)
                eq_final = eq.iloc[-1]
                ret_total = (eq_final - 1) * 100
                run_max = eq.cummax()
                dd = ((eq / run_max) - 1).min() * 100
                # Approximate trade count
                n_rebal = len(rebal_bars)

                result = {
                    "lookback": lookback, "rebal_interval": rebal, "top_n": top_n,
                    "sharpe": round(sh, 3),
                    "return_pct": round(float(ret_total), 2),
                    "dd_pct": round(float(dd), 2),
                    "n_rebalances": n_rebal,
                    "calmar": round(abs(ret_total / dd) if dd != 0 else 0, 2),
                }
                results.append(result)

                # Save best equity curve
                key = f"L{lookback}_R{rebal}_T{top_n}"
                eq_curves[key] = eq.values.tolist()[::6][:200]  # sample for size

    # ── Summary ──
    results.sort(key=lambda x: x["sharpe"], reverse=True)
    print(f"\n=== Summary (sorted by Sharpe) ===")
    print(f"{'Lookback':>9} {'Rebal':>6} {'top_n':>6} {'Sharpe':>8} {'Ret%':>7} {'DD%':>7} {'Calmar':>7}")
    for r in results[:15]:
        print(f"  {r['lookback']:>7} {r['rebal_interval']:>6} {r['top_n']:>6} "
              f"{r['sharpe']:>+8.2f} {r['return_pct']:>+7.1f} {r['dd_pct']:>+7.1f} {r['calmar']:>7.2f}")

    sh_pos = sum(1 for r in results if r['sharpe'] > 0)
    sh_ge_1 = sum(1 for r in results if r['sharpe'] >= 1.0)
    sh_ge_1_5 = sum(1 for r in results if r['sharpe'] >= 1.5)
    sh_ge_2 = sum(1 for r in results if r['sharpe'] >= 2.0)

    print(f"\nTotals: Sh>0: {sh_pos}/{len(results)} ({sh_pos/len(results)*100:.0f}%), "
          f"≥1.0: {sh_ge_1}, ≥1.5: {sh_ge_1_5}, ≥2.0: {sh_ge_2}")

    out = {
        "wave": "J10",
        "name": "LISRM (L1 Cross-Section Rotation Momentum)",
        "generated_at": datetime.now(timezone(timedelta(hours=9))).strftime("%Y-%m-%d %H:%M JST"),
        "hypothesis": "L1セクター9銘柄のクロスセクション・ランキングL/S。市場中立",
        "universe": UNIVERSE,
        "n_trials": len(results),
        "summary_counts": {
            "sh_positive": sh_pos, "sh_ge_1": sh_ge_1,
            "sh_ge_1_5": sh_ge_1_5, "sh_ge_2": sh_ge_2,
        },
        "top15": results[:15],
        "all_results": results,
        "runtime_sec": round(time.time() - t0, 1),
    }
    Path("/Users/nekonaomichi/crypto-lab/wave_j10_lisrm.json").write_text(json.dumps(out, indent=2, default=str))
    print(f"\nSaved to wave_j10_lisrm.json (runtime {out['runtime_sec']}s)")


if __name__ == "__main__":
    asyncio.run(main())

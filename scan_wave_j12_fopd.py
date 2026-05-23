"""Wave J12 — FOPD (Funding-OI-Price Triple Decoupling) validation.

Hypothesis (Researcher TOP2):
  FR・OI・価格が3つ揃って同方向 (=過剰ポジション圧) になる稀な瞬間に逆張り。
  単一の Funding Contrarian (棄却) と違い、3項一致条件を必須にする。
  ロング過剰 (fr>>0 + oi↑ + price↑) → ショート
  ショート過剰 (fr<<0 + oi↑ + price↓) → ロング

Entry (4H bar):
  fr_z = zscore(funding_rate, 30d)
  oi_z = zscore(OI_change_24h, 30d)
  ret_z = zscore(price_return_24h, 30d)
  trigger_long  = (fr_z < -1.5) & (oi_z < -1.0) & (ret_z < -1.0)
  trigger_short = (fr_z >  1.5) & (oi_z >  1.0) & (ret_z >  1.0)

Exit: TP=1.5 ATR / SL=1.0 ATR / MaxHold=3 bars (12h)
Symbols: Major + LargeCap (FR/OI流動性必要)
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
from engine.data import fetch_klines, fetch_bybit_funding_rate, fetch_historical_metrics
from engine.backtest import run_backtest
from engine.cost_config import get_cost_params

SYMBOLS = ["BTCUSDT", "ETHUSDT", "SOLUSDT", "BNBUSDT", "XRPUSDT",
           "ADAUSDT", "DOTUSDT", "LINKUSDT", "AVAXUSDT"]

DAYS = 730
BARS_PER_YEAR = 2190


def fopd_signal(df, fr_series, oi_series,
                fr_z_thresh=1.5, oi_z_thresh=1.0, ret_z_thresh=1.0,
                zscore_window=180):  # 30 days × 6 4h = 180 bars
    """FOPD signal."""
    # Align fr / oi to df via merge
    df_w = df.copy().sort_values('open_time').reset_index(drop=True)
    df_w['open_time'] = pd.to_datetime(df_w['open_time']).astype('datetime64[ns]')

    # FR
    if fr_series is not None and not fr_series.empty:
        fr_df = fr_series.copy()
        fr_df['timestamp'] = pd.to_datetime(fr_df['timestamp']).astype('datetime64[ns]')
        fr_df = fr_df.sort_values('timestamp').reset_index(drop=True)
        merged_fr = pd.merge_asof(df_w[['open_time']],
                                   fr_df.rename(columns={'timestamp':'open_time'}),
                                   on='open_time', direction='backward')
        fr_vals = merged_fr['funding_rate'].fillna(0).values
    else:
        fr_vals = np.zeros(len(df_w))

    # OI
    if oi_series is not None and not oi_series.empty and 'oi' in oi_series.columns:
        oi_df = oi_series.copy()
        oi_df['timestamp'] = pd.to_datetime(oi_df['timestamp']).astype('datetime64[ns]')
        oi_df = oi_df.sort_values('timestamp').reset_index(drop=True)
        merged_oi = pd.merge_asof(df_w[['open_time']],
                                   oi_df[['timestamp','oi']].rename(columns={'timestamp':'open_time'}),
                                   on='open_time', direction='backward')
        oi_vals = merged_oi['oi'].ffill().bfill().values
    else:
        oi_vals = np.full(len(df_w), np.nan)

    # OI change 24h (6 bars)
    oi_series_pd = pd.Series(oi_vals, index=df_w.index)
    oi_change_24h = oi_series_pd.pct_change(6).fillna(0).values

    # Price return 24h
    close = df_w['close'].values
    ret_24h = pd.Series(close, index=df_w.index).pct_change(6).fillna(0).values

    # Z-scores (rolling)
    fr_s = pd.Series(fr_vals)
    oi_s = pd.Series(oi_change_24h)
    ret_s = pd.Series(ret_24h)

    fr_z = (fr_s - fr_s.rolling(zscore_window).mean()) / (fr_s.rolling(zscore_window).std() + 1e-12)
    oi_z = (oi_s - oi_s.rolling(zscore_window).mean()) / (oi_s.rolling(zscore_window).std() + 1e-12)
    ret_z = (ret_s - ret_s.rolling(zscore_window).mean()) / (ret_s.rolling(zscore_window).std() + 1e-12)

    fr_z_v = fr_z.fillna(0).values
    oi_z_v = oi_z.fillna(0).values
    ret_z_v = ret_z.fillna(0).values

    # Long signal: all 3 extremely negative (over-crowded shorts capitulating)
    # Short signal: all 3 extremely positive (over-crowded longs at peak)
    long_sig = (fr_z_v < -fr_z_thresh) & (oi_z_v < -oi_z_thresh) & (ret_z_v < -ret_z_thresh)
    short_sig = (fr_z_v > fr_z_thresh) & (oi_z_v > oi_z_thresh) & (ret_z_v > ret_z_thresh)

    sig = np.zeros(len(df_w), dtype=int)
    sig[long_sig] = +1
    sig[short_sig] = -1
    sig[:zscore_window + 10] = 0  # warmup
    return pd.Series(sig, index=df_w.index)


def run_bt(df, sig, sym, sl=0.04, tp=0.06, mhb=3):
    cost = get_cost_params(sym, "4h")
    return run_backtest(df, sig, strategy_name="FOPD",
                        bars_per_year=BARS_PER_YEAR, leverage=1.0,
                        stop_loss_pct=sl, take_profit_pct=tp, max_hold_bars=mhb,
                        **cost)


async def main():
    t0 = time.time()
    print("=== Wave J12: FOPD (Funding-OI-Price Triple Decoupling) ===\n")

    print("Loading OHLCV + funding + OI data ...")
    cache = {}
    for s in SYMBOLS:
        df = await fetch_klines(s, "4h", DAYS)
        try:
            fr_df = await fetch_bybit_funding_rate(s, DAYS)
        except Exception:
            fr_df = None
        try:
            oi_df = await fetch_historical_metrics(s, DAYS)
        except Exception:
            oi_df = None
        cache[s] = {"ohlcv": df, "fr": fr_df, "oi": oi_df}
        fr_n = len(fr_df) if (fr_df is not None and not fr_df.empty) else 0
        oi_n = len(oi_df) if (oi_df is not None and not oi_df.empty) else 0
        print(f"  {s:<10} OHLCV={len(df)}, FR={fr_n}, OI={oi_n}")

    # ── Scan ──
    fr_z_thresholds = [1.0, 1.5, 2.0]
    oi_z_thresholds = [0.5, 1.0, 1.5]
    ret_z_thresholds = [0.5, 1.0, 1.5]
    sls = [0.03, 0.04, 0.06]
    tps = [0.04, 0.06, 0.08]
    mhbs = [3, 6, 12]

    n_grid = len(fr_z_thresholds) * len(oi_z_thresholds) * len(ret_z_thresholds) * len(sls) * len(tps) * len(mhbs)
    print(f"\nGrid: {n_grid} params × {len(SYMBOLS)} symbols = {n_grid * len(SYMBOLS)} backtests\n")

    results = []
    best_per_symbol = {}
    for s in SYMBOLS:
        d = cache[s]
        if d["fr"] is None or d["fr"].empty:
            print(f"  {s} SKIP (no FR)")
            continue
        if d["oi"] is None or d["oi"].empty:
            print(f"  {s} SKIP (no OI)")
            continue
        df = d["ohlcv"]
        best = None
        for fr_t in fr_z_thresholds:
            for oi_t in oi_z_thresholds:
                for ret_t in ret_z_thresholds:
                    sig = fopd_signal(df, d["fr"], d["oi"], fr_t, oi_t, ret_t)
                    n_sig = (sig != 0).sum()
                    if n_sig < 5:
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
                                    if trades < 10:
                                        continue
                                    row = {
                                        'symbol': s, 'fr_t': fr_t, 'oi_t': oi_t, 'ret_t': ret_t,
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
            print(f"  {s:<10} best Sh={best['sharpe']:+.2f} ret={best['return_pct']:+.1f}% "
                  f"dd={best['dd_pct']:+.1f}% tr={best['trades']} "
                  f"(fr={best['fr_t']}, oi={best['oi_t']}, ret={best['ret_t']})")

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
        "wave": "J12", "name": "FOPD (Funding-OI-Price Triple Decoupling)",
        "generated_at": datetime.now(timezone(timedelta(hours=9))).strftime("%Y-%m-%d %H:%M JST"),
        "hypothesis": "3項一致 (FR×OI×Price z-score) で過剰ポジション逆張り",
        "symbols": SYMBOLS, "n_trials": len(results),
        "summary_counts": {"sh_pos": sh_pos, "sh_ge_1": sh_ge_1, "sh_ge_1_5": sh_ge_1_5, "sh_ge_2": sh_ge_2},
        "best_per_symbol": best_per_symbol, "top10": results[:10],
        "runtime_sec": round(time.time() - t0, 1),
    }
    Path("/Users/nekonaomichi/crypto-lab/wave_j12_fopd.json").write_text(json.dumps(out, indent=2, default=str))
    print(f"\nSaved (runtime {out['runtime_sec']}s)")


if __name__ == "__main__":
    asyncio.run(main())

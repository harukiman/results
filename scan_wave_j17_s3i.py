"""Wave J17 — S3I (Stablecoin Supply Surge Inflow) — first on-chain strategy.

仮説 (Researcher R5):
  USDT + USDC 合計の日次供給量増加率は「乾燥粉」流入の先行指標。
  供給急増後 6-24h 以内に BTC/ETH のロング側エッジが発生する。

データソース: DefiLlama API (無料、認証不要)
  https://stablecoins.llama.fi/stablecoincharts/all
  返り値: {date, totalCirculating: {peggedUSD: <USD value>}}

Entry:
  stable_supply = USDT_supply + USDC_supply
  supply_change_24h = (supply[t] - supply[t-1d]) / supply[t-1d]
  supply_z = zscore(supply_change_24h, 60d)
  trigger_long = (supply_z > +K) and (BTC_return_24h > 0)  # 確証フィルタ

Exit: 12 bars MaxHold (48h) / SL=1.5 ATR / TP=trailing 3 ATR
Symbols: BTC, ETH
TF: 4H (オンチェーンは日次だが、4Hで判定)
"""
import asyncio
import json
import sys
import time
import numpy as np
import pandas as pd
import httpx
from pathlib import Path
from datetime import datetime, timezone, timedelta

sys.path.insert(0, "/Users/nekonaomichi/crypto-lab")
from engine.data import fetch_klines
from engine.backtest import run_backtest
from engine.cost_config import get_cost_params

SYMBOLS = ["BTCUSDT", "ETHUSDT", "SOLUSDT", "BNBUSDT"]
DAYS = 730
BARS_PER_YEAR = 2190
CACHE_PATH = Path("/Users/nekonaomichi/crypto-lab/cache/stablecoin_supply.parquet")


async def fetch_stablecoin_supply():
    """Fetch total stablecoin supply from DefiLlama API."""
    if CACHE_PATH.exists() and (time.time() - CACHE_PATH.stat().st_mtime) < 86400:
        return pd.read_parquet(CACHE_PATH)

    url = "https://stablecoins.llama.fi/stablecoincharts/all"
    async with httpx.AsyncClient(timeout=60) as client:
        resp = await client.get(url)
        resp.raise_for_status()
        data = resp.json()

    # Parse
    records = []
    for d in data:
        ts = int(d["date"])
        # totalCirculating may be a dict or float
        tc = d.get("totalCirculating") or d.get("totalCirculatingUSD") or {}
        if isinstance(tc, dict):
            usd = tc.get("peggedUSD", 0) or 0
        else:
            usd = float(tc) if tc else 0
        records.append({"timestamp": pd.to_datetime(ts, unit='s'), "stablecoin_supply_usd": float(usd)})

    df = pd.DataFrame(records).sort_values("timestamp").drop_duplicates("timestamp").reset_index(drop=True)
    CACHE_PATH.parent.mkdir(exist_ok=True)
    df.to_parquet(CACHE_PATH, index=False)
    return df


def s3i_signal(df, stable_supply_df, z_threshold=1.5, ret_confirm=0.0, w=60):
    """S3I signal: supply z-score above threshold + BTC return confirmation."""
    df_w = df.copy().sort_values('open_time').reset_index(drop=True)
    df_w['open_time'] = pd.to_datetime(df_w['open_time']).astype('datetime64[ns]')

    # Align supply (daily) to 4H bars via merge_asof
    ss = stable_supply_df.copy().sort_values("timestamp").reset_index(drop=True)
    ss['timestamp'] = pd.to_datetime(ss['timestamp']).astype('datetime64[ns]')
    merged = pd.merge_asof(df_w[['open_time']], ss.rename(columns={'timestamp':'open_time'}),
                            on='open_time', direction='backward')
    supply = merged['stablecoin_supply_usd'].ffill().bfill().values

    # 24h supply change (= 6 4h bars)
    supply_s = pd.Series(supply)
    supply_change_24h = supply_s.pct_change(6).fillna(0)

    # 60-day rolling Z-score (= 360 4h bars)
    win_bars = w * 6
    rmean = supply_change_24h.rolling(win_bars).mean()
    rstd = supply_change_24h.rolling(win_bars).std()
    supply_z = (supply_change_24h - rmean) / (rstd + 1e-12)
    supply_z = supply_z.fillna(0).values

    # BTC 24h return for confirmation
    close = df_w['close'].values
    ret_24h = pd.Series(close).pct_change(6).fillna(0).values

    long_signal = (supply_z > z_threshold) & (ret_24h > ret_confirm)
    short_signal = (supply_z < -z_threshold) & (ret_24h < -ret_confirm)  # also test inverse

    sig = np.zeros(len(df_w), dtype=int)
    sig[long_signal] = +1
    sig[short_signal] = -1
    sig[:win_bars + 10] = 0
    return pd.Series(sig, index=df_w.index)


def sharpe(r, ppy=365):
    r = np.asarray(r); r = r[np.isfinite(r)]
    if len(r) < 5 or np.std(r, ddof=1) == 0: return 0.0
    return float(np.mean(r) / np.std(r, ddof=1) * np.sqrt(ppy))


def run_bt(df, sig, sym, sl=0.04, tp=0.08, mhb=12):
    cost = get_cost_params(sym, "4h")
    return run_backtest(df, sig, strategy_name="S3I",
                        bars_per_year=BARS_PER_YEAR, leverage=1.0,
                        stop_loss_pct=sl, take_profit_pct=tp, max_hold_bars=mhb,
                        **cost)


async def main():
    t0 = time.time()
    print("=== Wave J17: S3I (Stablecoin Supply Surge Inflow) — first on-chain strategy ===\n")

    # ── Fetch stablecoin supply ──
    print("Fetching DefiLlama stablecoin supply ...")
    try:
        ss = await fetch_stablecoin_supply()
        print(f"  Loaded {len(ss)} daily records, range {ss['timestamp'].min()} → {ss['timestamp'].max()}")
        # Verify recent data
        recent = ss['stablecoin_supply_usd'].iloc[-5:].values
        print(f"  Recent 5 days: {[f'${v/1e9:.1f}B' for v in recent]}")
    except Exception as e:
        print(f"  ERROR fetching DefiLlama: {e}")
        return

    print("\nLoading OHLCV ...")
    cache = {}
    for s in SYMBOLS:
        cache[s] = await fetch_klines(s, "4h", DAYS)
        print(f"  {s:<10} {len(cache[s])} bars")

    # ── Param scan ──
    z_thresholds = [1.0, 1.5, 2.0, 2.5]
    ret_confirms = [0.0, 0.01, 0.02]  # 0%, 1%, 2% confirmation
    sls = [0.03, 0.04, 0.06]
    tps = [0.04, 0.06, 0.10]
    mhbs = [6, 12, 18]

    n_grid = len(z_thresholds) * len(ret_confirms) * len(sls) * len(tps) * len(mhbs)
    print(f"\nGrid: {n_grid} configs × {len(SYMBOLS)} symbols = {n_grid * len(SYMBOLS)} backtests\n")

    results = []
    best_per_symbol = {}
    for s in SYMBOLS:
        df = cache[s]
        best = None
        for zt in z_thresholds:
            for rc in ret_confirms:
                sig = s3i_signal(df, ss, zt, rc)
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
                                if trades < 10:
                                    continue
                                row = {
                                    'symbol': s, 'z_t': zt, 'ret_conf': rc,
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
                  f"dd={best['dd_pct']:+.1f}% tr={best['trades']} (zt={best['z_t']}, rc={best['ret_conf']})")
        else:
            print(f"  {s:<10} no valid result")

    results.sort(key=lambda x: x['sharpe'], reverse=True)
    print(f"\n=== Top 10 ===")
    for r in results[:10]:
        print(f"  {r['symbol']:<10} Sh={r['sharpe']:+.2f} ret={r['return_pct']:+.1f}% dd={r['dd_pct']:+.1f}% tr={r['trades']} (zt={r['z_t']})")

    sh_pos = sum(1 for r in results if r['sharpe'] > 0)
    sh_ge_1 = sum(1 for r in results if r['sharpe'] >= 1.0)
    sh_ge_1_5 = sum(1 for r in results if r['sharpe'] >= 1.5)
    sh_ge_2 = sum(1 for r in results if r['sharpe'] >= 2.0)
    print(f"\nTotals: Sh>0 {sh_pos}/{len(results)} ({sh_pos/max(len(results),1)*100:.0f}%), ≥1.0: {sh_ge_1}, ≥1.5: {sh_ge_1_5}, ≥2.0: {sh_ge_2}")

    out = {
        "wave": "J17", "name": "S3I (Stablecoin Supply Surge Inflow)",
        "generated_at": datetime.now(timezone(timedelta(hours=9))).strftime("%Y-%m-%d %H:%M JST"),
        "hypothesis": "USDT+USDC供給急増は乾燥粉流入先行指標、BTC/ETHロングエッジ",
        "data_source": "DefiLlama stablecoincharts/all",
        "symbols": SYMBOLS, "n_trials": len(results),
        "summary_counts": {"sh_pos": sh_pos, "sh_ge_1": sh_ge_1, "sh_ge_1_5": sh_ge_1_5, "sh_ge_2": sh_ge_2},
        "best_per_symbol": best_per_symbol, "top10": results[:10],
        "runtime_sec": round(time.time() - t0, 1),
    }
    Path("/Users/nekonaomichi/crypto-lab/wave_j17_s3i.json").write_text(json.dumps(out, indent=2, default=str))
    print(f"\nSaved (runtime {out['runtime_sec']}s)")


if __name__ == "__main__":
    asyncio.run(main())

"""Wave K8 — Worst rolling windows stress test for 80/10/10.

730日 (約 2年) の中で最悪の連続日数窓を抽出:
  - 30日 (1ヶ月)
  - 60日 (2ヶ月)
  - 90日 (3ヶ月)

各窓で:
  - 80/10/10 のリターン
  - 最大 DD
  - Recovery time (peak回復までの日数)

実運用での「最悪のシナリオ」を可視化。
"""
import asyncio
import json
import sys
import numpy as np
import pandas as pd
from pathlib import Path
from datetime import datetime, timezone, timedelta

sys.path.insert(0, "/Users/nekonaomichi/crypto-lab")
from engine.data import fetch_klines, fetch_bybit_funding_rate, fetch_historical_metrics
from engine.backtest import run_backtest
from engine.cost_config import get_cost_params

ATR_SYMBOLS = ["OPUSDT", "WIFUSDT", "INJUSDT", "BONKUSDT",
               "DOGEUSDT", "SHIBUSDT", "ARBUSDT", "LINKUSDT"]
FOPD_BEST = {
    "BNBUSDT":  {"fr": 1.0, "oi": 0.5, "ret": 1.5, "sl": 0.04, "tp": 0.06, "mhb": 6},
    "AVAXUSDT": {"fr": 2.0, "oi": 1.0, "ret": 1.5, "sl": 0.04, "tp": 0.06, "mhb": 6},
    "ETHUSDT":  {"fr": 1.5, "oi": 1.5, "ret": 0.5, "sl": 0.04, "tp": 0.06, "mhb": 6},
    "ADAUSDT":  {"fr": 2.0, "oi": 0.5, "ret": 0.5, "sl": 0.04, "tp": 0.06, "mhb": 6},
    "LINKUSDT": {"fr": 1.0, "oi": 0.5, "ret": 1.0, "sl": 0.04, "tp": 0.06, "mhb": 6},
    "DOTUSDT":  {"fr": 2.0, "oi": 1.0, "ret": 1.0, "sl": 0.04, "tp": 0.06, "mhb": 6},
}
ATR_PARAMS_4H = {"atr_short": 7, "atr_long": 56, "threshold": 0.6, "ema_fast": 20, "ema_slow": 80}
ATR_PARAMS_8H = {"atr_short": 4, "atr_long": 28, "threshold": 0.6, "ema_fast": 10, "ema_slow": 40}
EXIT_4H = {"stop_loss_pct": 0.04, "take_profit_pct": 0.08, "max_hold_bars": 24}
EXIT_8H = {"stop_loss_pct": 0.04, "take_profit_pct": 0.08, "max_hold_bars": 12}
VOL_Z = 1.5
DAYS = 730


def aggregate_4h_to_8h(df_4h):
    df = df_4h.copy().sort_values('open_time').reset_index(drop=True)
    df['pair_idx'] = df.index // 2
    return df.groupby('pair_idx').agg({
        'open_time': 'first', 'open': 'first', 'high': 'max', 'low': 'min',
        'close': 'last', 'volume': 'sum'
    }).reset_index(drop=True)


def atr_ratio_signal(df, **k):
    atr_s = (df['high'] - df['low']).rolling(k['atr_short']).mean()
    atr_l = (df['high'] - df['low']).rolling(k['atr_long']).mean()
    comp = atr_s < atr_l * k['threshold']
    ef = df['close'].ewm(span=k['ema_fast']).mean()
    es = df['close'].ewm(span=k['ema_slow']).mean()
    sig = pd.Series(0, index=df.index)
    sig[comp & (ef > es)] = 1
    sig[comp & (ef < es)] = -1
    return sig


def fopd_signal(df, fr_series, oi_series, fr_z, oi_z, ret_z, w=180):
    df_w = df.copy().sort_values('open_time').reset_index(drop=True)
    df_w['open_time'] = pd.to_datetime(df_w['open_time']).astype('datetime64[ns]')
    if fr_series is not None and not fr_series.empty:
        fr_df = fr_series.copy()
        fr_df['timestamp'] = pd.to_datetime(fr_df['timestamp']).astype('datetime64[ns]')
        fr_df = fr_df.sort_values('timestamp').reset_index(drop=True)
        m = pd.merge_asof(df_w[['open_time']], fr_df.rename(columns={'timestamp':'open_time'}), on='open_time', direction='backward')
        fr = m['funding_rate'].fillna(0).values
    else:
        fr = np.zeros(len(df_w))
    if oi_series is not None and not oi_series.empty and 'oi' in oi_series.columns:
        oi_df = oi_series.copy()
        oi_df['timestamp'] = pd.to_datetime(oi_df['timestamp']).astype('datetime64[ns]')
        oi_df = oi_df.sort_values('timestamp').reset_index(drop=True)
        mo = pd.merge_asof(df_w[['open_time']], oi_df[['timestamp','oi']].rename(columns={'timestamp':'open_time'}), on='open_time', direction='backward')
        oi_vals = mo['oi'].ffill().bfill().values
    else:
        oi_vals = np.full(len(df_w), np.nan)
    oi_chg = pd.Series(oi_vals, index=df_w.index).pct_change(6).fillna(0).values
    ret = pd.Series(df_w['close'].values, index=df_w.index).pct_change(6).fillna(0).values
    def zscore(s, win=w):
        return ((s - s.rolling(win).mean()) / (s.rolling(win).std() + 1e-12)).fillna(0).values
    fr_z_v = zscore(pd.Series(fr))
    oi_z_v = zscore(pd.Series(oi_chg))
    ret_z_v = zscore(pd.Series(ret))
    long_s = (fr_z_v < -fr_z) & (oi_z_v < -oi_z) & (ret_z_v < -ret_z)
    short_s = (fr_z_v > fr_z) & (oi_z_v > oi_z) & (ret_z_v > ret_z)
    sig = np.zeros(len(df_w), dtype=int)
    sig[long_s] = +1; sig[short_s] = -1; sig[:w + 10] = 0
    return pd.Series(sig, index=df_w.index)


def eq_to_daily(eq, bpd):
    eq = np.asarray(eq, dtype=float)
    d = eq[bpd-1::bpd]
    if len(d) < 2: d = eq[::bpd]
    return np.diff(d) / np.where(d[:-1] != 0, d[:-1], 1.0)


def sharpe(r, ppy=365):
    r = np.asarray(r); r = r[np.isfinite(r)]
    if len(r) < 5 or np.std(r, ddof=1) == 0: return 0.0
    return float(np.mean(r) / np.std(r, ddof=1) * np.sqrt(ppy))


def run_bt(df, sig, sym, interval, exit_kw):
    cost = get_cost_params(sym, interval)
    bars_per_year = 2190 if interval == "4h" else 1095
    return run_backtest(df, sig, strategy_name="K8", bars_per_year=bars_per_year,
                        leverage=1.0, **exit_kw, **cost)


def rolling_window_metrics(returns, window_size):
    """Compute return/DD/Sharpe for every rolling window of size W."""
    n = len(returns)
    out = []
    for i in range(n - window_size + 1):
        w = returns[i:i+window_size]
        eq = np.cumprod(1 + w)
        ret = (eq[-1] - 1) * 100
        dd = (eq / np.maximum.accumulate(eq) - 1).min() * 100
        sh = sharpe(w)
        out.append({"start_day": i, "end_day": i + window_size, "return_pct": float(ret), "max_dd_pct": float(dd), "sharpe": float(sh)})
    return out


async def main():
    print("=== Wave K8: Worst Rolling Windows Stress Test ===\n")

    # Compute 80/10/10 daily returns
    atr_cache = {s: await fetch_klines(s, "4h", DAYS) for s in ATR_SYMBOLS}
    fopd_cache = {}
    for s in FOPD_BEST:
        df = await fetch_klines(s, "4h", DAYS)
        try: fr = await fetch_bybit_funding_rate(s, DAYS)
        except: fr = None
        try: oi = await fetch_historical_metrics(s, DAYS)
        except: oi = None
        fopd_cache[s] = {"ohlcv": df, "fr": fr, "oi": oi}
    btc = await fetch_klines("BTCUSDT", "4h", DAYS)
    btc['ret'] = btc['close'].pct_change()
    btc['rv'] = btc['ret'].rolling(60).std() * np.sqrt(2190) * 100
    btc['rvm'] = btc['rv'].rolling(360).mean()
    btc['rvs'] = btc['rv'].rolling(360).std()
    btc['volz'] = (btc['rv'] - btc['rvm']) / (btc['rvs'] + 1e-10)
    btc_idx_4h = btc.set_index('open_time')
    btc_8h = aggregate_4h_to_8h(btc)
    btc_8h['ret'] = btc_8h['close'].pct_change()
    btc_8h['rv'] = btc_8h['ret'].rolling(30).std() * np.sqrt(1095) * 100
    btc_8h['rvm'] = btc_8h['rv'].rolling(180).mean()
    btc_8h['rvs'] = btc_8h['rv'].rolling(180).std()
    btc_8h['volz'] = (btc_8h['rv'] - btc_8h['rvm']) / (btc_8h['rvs'] + 1e-10)
    btc_idx_8h = btc_8h.set_index('open_time')

    daily_atr = {}
    for s in ATR_SYMBOLS:
        df = atr_cache[s]
        sig = atr_ratio_signal(df, **ATR_PARAMS_4H)
        aligned = btc_idx_4h.reindex(df['open_time'], method='ffill')['volz'].values
        sig[pd.Series(aligned, index=sig.index).fillna(False) >= VOL_Z] = 0
        r = run_bt(df, sig, s, "4h", EXIT_4H)
        daily_atr[s] = eq_to_daily(r['equity_curve'], 6)
    ma = min(len(v) for v in daily_atr.values())
    atr_d = pd.DataFrame({k: v[:ma] for k, v in daily_atr.items()}).mean(axis=1).values

    daily_fopd = {}
    for s, p in FOPD_BEST.items():
        d = fopd_cache[s]
        sig = fopd_signal(d["ohlcv"], d["fr"], d["oi"], p["fr"], p["oi"], p["ret"])
        r = run_bt(d["ohlcv"], sig, s, "4h", {"stop_loss_pct": p["sl"], "take_profit_pct": p["tp"], "max_hold_bars": p["mhb"]})
        daily_fopd[s] = eq_to_daily(r['equity_curve'], 6)
    mf = min(len(v) for v in daily_fopd.values())
    fopd_d = pd.DataFrame({k: v[:mf] for k, v in daily_fopd.items()}).mean(axis=1).values

    bonk_8h_df = aggregate_4h_to_8h(atr_cache["BONKUSDT"])
    shib_8h_df = aggregate_4h_to_8h(atr_cache["SHIBUSDT"])
    def compute_8h(df_8h, sym):
        sig = atr_ratio_signal(df_8h, **ATR_PARAMS_8H)
        aligned = btc_idx_8h.reindex(df_8h['open_time'], method='ffill')['volz'].values
        sig[pd.Series(aligned, index=sig.index).fillna(False) >= VOL_Z] = 0
        r = run_bt(df_8h, sig, sym, "8h", EXIT_8H)
        return eq_to_daily(r['equity_curve'], 3)
    bonk_d = compute_8h(bonk_8h_df, "BONKUSDT")
    shib_d = compute_8h(shib_8h_df, "SHIBUSDT")

    common = min(len(atr_d), len(fopd_d), len(bonk_d), len(shib_d))
    atr_d = atr_d[:common]; fopd_d = fopd_d[:common]; bonk_d = bonk_d[:common]; shib_d = shib_d[:common]
    combined = 0.5 * atr_d + 0.5 * fopd_d
    triple = 0.80 * combined + 0.10 * bonk_d + 0.10 * shib_d

    # BTC daily returns for reference
    btc_daily_4h = aggregate_4h_to_8h.__wrapped__ if hasattr(aggregate_4h_to_8h, '__wrapped__') else None
    # Get BTC daily returns the same way
    btc_eq = (1 + btc['ret'].fillna(0)).cumprod().values
    btc_daily = eq_to_daily(btc_eq, 6)[:common]

    for window_size in [30, 60, 90]:
        print(f"\n=== Rolling {window_size}-day windows ===")
        windows = rolling_window_metrics(triple, window_size)
        btc_windows = rolling_window_metrics(btc_daily, window_size)

        # Sort by return ascending (worst first)
        worst_by_ret = sorted(windows, key=lambda x: x["return_pct"])[:5]
        worst_by_dd = sorted(windows, key=lambda x: x["max_dd_pct"])[:5]

        print(f"\nWorst {window_size}-day windows by RETURN (80/10/10):")
        print(f"{'Start day':<10} {'End day':<10} {'Return':<10} {'Max DD':<10} {'Sharpe':<8} {'BTC Ret':<10}")
        for w in worst_by_ret:
            btc_w = btc_windows[w["start_day"]] if w["start_day"] < len(btc_windows) else {"return_pct": 0}
            print(f"  {w['start_day']:<8} {w['end_day']:<8} {w['return_pct']:>+7.2f}%  {w['max_dd_pct']:>+7.2f}%  {w['sharpe']:>+6.2f}  {btc_w['return_pct']:>+7.2f}%")

        print(f"\nWorst {window_size}-day windows by MAX DD (80/10/10):")
        print(f"{'Start day':<10} {'End day':<10} {'Return':<10} {'Max DD':<10} {'Sharpe':<8} {'BTC Ret':<10}")
        for w in worst_by_dd:
            btc_w = btc_windows[w["start_day"]] if w["start_day"] < len(btc_windows) else {"return_pct": 0}
            print(f"  {w['start_day']:<8} {w['end_day']:<8} {w['return_pct']:>+7.2f}%  {w['max_dd_pct']:>+7.2f}%  {w['sharpe']:>+6.2f}  {btc_w['return_pct']:>+7.2f}%")

        # Aggregate stats
        all_returns = [w["return_pct"] for w in windows]
        all_dds = [w["max_dd_pct"] for w in windows]
        print(f"\nAggregate over {len(windows)} rolling windows:")
        print(f"  Returns: p5={np.percentile(all_returns, 5):+.2f}%, median={np.median(all_returns):+.2f}%, p95={np.percentile(all_returns, 95):+.2f}%")
        print(f"  DDs:     p5={np.percentile(all_dds, 5):+.2f}%, median={np.median(all_dds):+.2f}%, p95={np.percentile(all_dds, 95):+.2f}%")
        print(f"  % of windows with positive return: {sum(1 for r in all_returns if r > 0) / len(all_returns) * 100:.1f}%")

    out_data = {}
    for window_size in [30, 60, 90]:
        windows = rolling_window_metrics(triple, window_size)
        btc_windows = rolling_window_metrics(btc_daily, window_size)
        out_data[f"window_{window_size}d"] = {
            "all_windows": windows,
            "btc_for_comparison": btc_windows,
            "summary": {
                "n_windows": len(windows),
                "median_return": float(np.median([w["return_pct"] for w in windows])),
                "p5_return": float(np.percentile([w["return_pct"] for w in windows], 5)),
                "p95_return": float(np.percentile([w["return_pct"] for w in windows], 95)),
                "median_dd": float(np.median([w["max_dd_pct"] for w in windows])),
                "p5_dd": float(np.percentile([w["max_dd_pct"] for w in windows], 5)),
                "positive_ret_pct": float(sum(1 for w in windows if w["return_pct"] > 0) / len(windows) * 100),
            },
        }

    out = {
        "wave": "K8", "name": "Worst Rolling Windows Stress Test for 80/10/10",
        "generated_at": datetime.now(timezone(timedelta(hours=9))).strftime("%Y-%m-%d %H:%M JST"),
        "T_days": common,
        "windows": out_data,
    }
    Path("/Users/nekonaomichi/crypto-lab/wave_k8_worst_windows.json").write_text(json.dumps(out, indent=2, default=str))
    print("\nSaved.")


if __name__ == "__main__":
    asyncio.run(main())

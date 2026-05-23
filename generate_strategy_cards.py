"""Wave J19 — Generate detailed strategy analysis cards.

For each major strategy:
  1. Daily equity curve (Plotly inline JSON)
  2. Monthly returns table
  3. Rolling 90-day Sharpe
  4. Drawdown chart
  5. Per-trade distribution

Output: enriched HTML cards embedded in report.html
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
ATR_PARAMS = {"atr_short": 7, "atr_long": 56, "threshold": 0.6, "ema_fast": 20, "ema_slow": 80}
ATR_EXIT = {"stop_loss_pct": 0.04, "take_profit_pct": 0.08, "max_hold_bars": 24}
VOL_Z = 1.5
DAYS = 730
BARS_PER_YEAR = 2190


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


def eq_to_daily_dates(eq, start_date, bars_per_day=6):
    eq = np.asarray(eq, dtype=float)
    if len(eq) < bars_per_day + 1:
        return [], []
    # Sample every 6th
    daily_eq = eq[bars_per_day-1::bars_per_day]
    n = len(daily_eq)
    dates = [start_date + timedelta(days=i) for i in range(n)]
    return dates, daily_eq.tolist()


def daily_to_returns(eq):
    eq = np.asarray(eq)
    return np.diff(eq) / np.where(eq[:-1] != 0, eq[:-1], 1.0)


def rolling_sharpe(returns, window=90, ppy=365):
    returns = np.asarray(returns)
    out = []
    for i in range(len(returns)):
        if i < window - 1:
            out.append(None)
            continue
        w = returns[i-window+1:i+1]
        w = w[np.isfinite(w)]
        if len(w) < 5 or np.std(w, ddof=1) == 0:
            out.append(None)
            continue
        sh = np.mean(w) / np.std(w, ddof=1) * np.sqrt(ppy)
        out.append(round(float(sh), 3))
    return out


def monthly_returns(dates, returns):
    df = pd.DataFrame({"date": dates, "ret": returns})
    df["yyyy_mm"] = pd.to_datetime(df["date"]).dt.to_period("M")
    monthly = df.groupby("yyyy_mm")["ret"].apply(lambda x: (1+x).prod() - 1)
    return [(str(p), round(float(r) * 100, 2)) for p, r in monthly.items()]


def drawdown_series(eq):
    eq = np.asarray(eq)
    run_max = np.maximum.accumulate(eq)
    return ((eq / run_max) - 1).tolist()


async def main():
    print("=== Wave J19: Generating detailed strategy cards ===\n")
    print("Loading data ...")
    atr_cache = {}
    for s in ATR_SYMBOLS:
        atr_cache[s] = await fetch_klines(s, "4h", DAYS)
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
    btc['rv'] = btc['ret'].rolling(60).std() * np.sqrt(BARS_PER_YEAR) * 100
    btc['rvm'] = btc['rv'].rolling(360).mean()
    btc['rvs'] = btc['rv'].rolling(360).std()
    btc['volz'] = (btc['rv'] - btc['rvm']) / (btc['rvs'] + 1e-10)
    btc_idx = btc.set_index('open_time')

    # ── Compute ATR portfolio equity ──
    print("\nComputing ATR portfolio equity ...")
    atr_daily = {}
    for s in ATR_SYMBOLS:
        df = atr_cache[s]
        sig = atr_ratio_signal(df, **ATR_PARAMS)
        aligned = btc_idx.reindex(df['open_time'], method='ffill')['volz'].values
        bad = pd.Series(aligned, index=sig.index).fillna(False) >= VOL_Z
        sig[bad] = 0
        cost = get_cost_params(s, "4h")
        r = run_backtest(df, sig, strategy_name=s, bars_per_year=BARS_PER_YEAR,
                         leverage=1.0, **ATR_EXIT, **cost)
        eq_arr = np.asarray(r['equity_curve'], dtype=float)
        # daily sample
        daily_eq = eq_arr[5::6]
        atr_daily[s] = daily_eq
    min_la = min(len(v) for v in atr_daily.values())
    aligned_df = pd.DataFrame({k: v[:min_la] for k, v in atr_daily.items()})
    # average daily returns
    atr_daily_ret = aligned_df.pct_change().fillna(0).mean(axis=1).values
    atr_eq = np.cumprod(1 + atr_daily_ret)

    # ── Compute FOPD portfolio equity ──
    print("Computing FOPD portfolio equity ...")
    fopd_daily = {}
    for s, p in FOPD_BEST.items():
        d = fopd_cache[s]
        sig = fopd_signal(d["ohlcv"], d["fr"], d["oi"], p["fr"], p["oi"], p["ret"])
        cost = get_cost_params(s, "4h")
        r = run_backtest(d["ohlcv"], sig, strategy_name=s, bars_per_year=BARS_PER_YEAR,
                         leverage=1.0, stop_loss_pct=p["sl"], take_profit_pct=p["tp"],
                         max_hold_bars=p["mhb"], **cost)
        eq_arr = np.asarray(r['equity_curve'], dtype=float)
        fopd_daily[s] = eq_arr[5::6]
    min_lf = min(len(v) for v in fopd_daily.values())
    aligned_fopd = pd.DataFrame({k: v[:min_lf] for k, v in fopd_daily.items()})
    fopd_daily_ret = aligned_fopd.pct_change().fillna(0).mean(axis=1).values
    fopd_eq = np.cumprod(1 + fopd_daily_ret)

    # ── Combined ──
    common = min(len(atr_daily_ret), len(fopd_daily_ret))
    combo_ret = 0.5 * atr_daily_ret[:common] + 0.5 * fopd_daily_ret[:common]
    combo_eq = np.cumprod(1 + combo_ret)

    # ── Generate dates ──
    start = datetime(2024, 5, 23)
    dates_combo = [start + timedelta(days=i) for i in range(len(combo_eq))]
    dates_atr = [start + timedelta(days=i) for i in range(len(atr_eq))]
    dates_fopd = [start + timedelta(days=i) for i in range(len(fopd_eq))]

    # ── Build analysis ──
    def build_stats(eq, daily_ret, name, dates):
        eq = np.asarray(eq)
        total_ret = (eq[-1] - 1) * 100
        dd_series = drawdown_series(eq)
        max_dd = min(dd_series) * 100
        rs = rolling_sharpe(daily_ret, window=90)
        cleaned = [x for x in rs if x is not None]
        # Align dates len to daily_ret len
        d_strs = [d.strftime("%Y-%m-%d") for d in dates[:len(daily_ret)]]
        # Ensure same length
        n = min(len(d_strs), len(daily_ret))
        return {
            "name": name,
            "total_return_pct": round(float(total_ret), 2),
            "max_dd_pct": round(float(max_dd), 2),
            "calmar": round(abs(total_ret/max_dd) if max_dd != 0 else 0, 2),
            "sharpe": round(float(np.mean(daily_ret) / (np.std(daily_ret, ddof=1) + 1e-12) * np.sqrt(365)), 3),
            "win_rate_pct": round(float((daily_ret > 0).sum() / len(daily_ret) * 100), 2),
            "n_days": len(daily_ret),
            "rolling_sharpe_90d": rs,
            "rolling_sh_mean": round(float(np.mean(cleaned)), 3) if cleaned else None,
            "rolling_sh_min": round(float(np.min(cleaned)), 3) if cleaned else None,
            "rolling_sh_max": round(float(np.max(cleaned)), 3) if cleaned else None,
            "monthly_returns": monthly_returns(d_strs[:n], daily_ret[:n]),
        }

    stats = {
        "combined": build_stats(combo_eq, combo_ret, "Combined 50/50 (ATR+FOPD)", dates_combo),
        "atr": build_stats(atr_eq, atr_daily_ret, "ATR×8 + vol_z≥1.5", dates_atr),
        "fopd": build_stats(fopd_eq, fopd_daily_ret, "FOPD×6 portfolio", dates_fopd),
    }

    print(f"\n=== Strategy Stats ===")
    for k, s in stats.items():
        print(f"\n{s['name']}:")
        print(f"  Total Return: {s['total_return_pct']:+.1f}%, Max DD: {s['max_dd_pct']:+.1f}%, Calmar: {s['calmar']}, Sharpe: {s['sharpe']:+.2f}")
        print(f"  Win Rate (daily): {s['win_rate_pct']:.1f}%, N days: {s['n_days']}")
        print(f"  Rolling 90d Sharpe: mean={s['rolling_sh_mean']}, min={s['rolling_sh_min']}, max={s['rolling_sh_max']}")
        print(f"  Months: {len(s['monthly_returns'])} (latest 3: {s['monthly_returns'][-3:]})")

    # Save JSON
    out_data = {
        "generated_at": datetime.now(timezone(timedelta(hours=9))).strftime("%Y-%m-%d %H:%M JST"),
        "stats": stats,
        "equity_curves": {
            "combined": [{"date": d.isoformat()[:10], "value": float(v)} for d, v in zip(dates_combo, combo_eq)],
            "atr": [{"date": d.isoformat()[:10], "value": float(v)} for d, v in zip(dates_atr, atr_eq)],
            "fopd": [{"date": d.isoformat()[:10], "value": float(v)} for d, v in zip(dates_fopd, fopd_eq)],
        },
        "drawdowns": {
            "combined": drawdown_series(combo_eq),
            "atr": drawdown_series(atr_eq),
            "fopd": drawdown_series(fopd_eq),
        },
    }
    Path("/Users/nekonaomichi/crypto-lab/strategy_cards_data.json").write_text(json.dumps(out_data, indent=2, default=str))
    print(f"\nSaved strategy_cards_data.json")


if __name__ == "__main__":
    asyncio.run(main())

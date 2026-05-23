"""Wave J29 — H1/H2 期間独立検証 for 80/10/10 三層合成.

Wave J18 で 50/50 Combined は H1/H2 両期間で Sh+3.15+ 維持を確認済。
80/10/10 三層合成も同様の期間頑健性を持つか検証。
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
    return run_backtest(df, sig, strategy_name="J29", bars_per_year=bars_per_year,
                        leverage=1.0, **exit_kw, **cost)


async def compute_triple_for_slice(atr_cache, fopd_cache, btc_idx_4h, btc_idx_8h,
                                    bar_start, bar_end):
    """Compute triple portfolio daily returns for a 4H bar slice."""
    # 4H ATR
    daily_atr = {}
    for s in ATR_SYMBOLS:
        df = atr_cache[s].iloc[bar_start:bar_end].reset_index(drop=True)
        sig = atr_ratio_signal(df, **ATR_PARAMS_4H)
        aligned = btc_idx_4h.reindex(df['open_time'], method='ffill')['volz'].values
        sig[pd.Series(aligned, index=sig.index).fillna(False) >= VOL_Z] = 0
        if (sig != 0).sum() < 3:
            daily_atr[s] = np.zeros(60); continue
        r = run_bt(df, sig, s, "4h", EXIT_4H)
        daily_atr[s] = eq_to_daily(r['equity_curve'], 6)
    ma = min(len(v) for v in daily_atr.values())
    atr_d = pd.DataFrame({k: v[:ma] for k, v in daily_atr.items()}).mean(axis=1).values

    # 4H FOPD - need full signal first then slice
    daily_fopd = {}
    for s, p in FOPD_BEST.items():
        d = fopd_cache[s]
        sig_full = fopd_signal(d["ohlcv"], d["fr"], d["oi"], p["fr"], p["oi"], p["ret"])
        df_slice = d["ohlcv"].iloc[bar_start:bar_end].reset_index(drop=True)
        sig_slice = sig_full.iloc[bar_start:bar_end].reset_index(drop=True)
        if (sig_slice != 0).sum() < 3:
            daily_fopd[s] = np.zeros(60); continue
        r = run_bt(df_slice, sig_slice, s, "4h", {"stop_loss_pct": p["sl"], "take_profit_pct": p["tp"], "max_hold_bars": p["mhb"]})
        daily_fopd[s] = eq_to_daily(r['equity_curve'], 6)
    mf = min(len(v) for v in daily_fopd.values())
    fopd_d = pd.DataFrame({k: v[:mf] for k, v in daily_fopd.items()}).mean(axis=1).values

    common_4h = min(len(atr_d), len(fopd_d))
    combined = 0.5 * atr_d[:common_4h] + 0.5 * fopd_d[:common_4h]

    # 8H Meme - aggregate first then slice (each 2 4H bars = 1 8H bar)
    bonk_8h_full = aggregate_4h_to_8h(atr_cache["BONKUSDT"])
    shib_8h_full = aggregate_4h_to_8h(atr_cache["SHIBUSDT"])
    # Slice in 8H bars
    bar_start_8h = bar_start // 2
    bar_end_8h = bar_end // 2

    def compute_8h(df_8h_full, sym):
        sig_full = atr_ratio_signal(df_8h_full, **ATR_PARAMS_8H)
        aligned = btc_idx_8h.reindex(df_8h_full['open_time'], method='ffill')['volz'].values
        sig_full[pd.Series(aligned, index=sig_full.index).fillna(False) >= VOL_Z] = 0
        df_slice = df_8h_full.iloc[bar_start_8h:bar_end_8h].reset_index(drop=True)
        sig_slice = sig_full.iloc[bar_start_8h:bar_end_8h].reset_index(drop=True)
        if (sig_slice != 0).sum() < 3:
            return np.zeros(60)
        r = run_bt(df_slice, sig_slice, sym, "8h", EXIT_8H)
        return eq_to_daily(r['equity_curve'], 3)

    bonk_d = compute_8h(bonk_8h_full, "BONKUSDT")
    shib_d = compute_8h(shib_8h_full, "SHIBUSDT")

    common = min(len(combined), len(bonk_d), len(shib_d))
    triple = 0.80 * combined[:common] + 0.10 * bonk_d[:common] + 0.10 * shib_d[:common]
    return triple


async def main():
    print("=== Wave J29: H1/H2 Period Stability for 80/10/10 ===\n")
    print("Loading ...")
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

    n_bars = len(atr_cache[ATR_SYMBOLS[0]])
    half = n_bars // 2
    periods = {
        "Full (730d)": (0, n_bars),
        "H1 (1-365d)": (0, half),
        "H2 (365-730d)": (half, n_bars),
    }

    print(f"\n{'Period':<18} {'Sharpe':>10} {'Return':>9} {'Max DD':>8} {'Calmar':>8}")
    print("-" * 60)
    results = {}
    for name, (s_idx, e_idx) in periods.items():
        triple = await compute_triple_for_slice(atr_cache, fopd_cache, btc_idx_4h, btc_idx_8h, s_idx, e_idx)
        sh = sharpe(triple)
        eq = np.cumprod(1 + triple)
        ret = (eq[-1] - 1) * 100
        dd = (eq / np.maximum.accumulate(eq) - 1).min() * 100
        cal = abs(ret / dd) if dd != 0 else 0
        print(f"  {name:<18} {sh:>+10.2f} {ret:>+8.1f}% {dd:>+7.1f}% {cal:>8.2f}")
        results[name] = {"sharpe": round(sh, 3), "return_pct": round(float(ret), 2),
                          "max_dd_pct": round(float(dd), 2), "calmar": round(cal, 2)}

    out = {
        "wave": "J29", "name": "H1/H2 Period Stability for 80/10/10 Triple",
        "generated_at": datetime.now(timezone(timedelta(hours=9))).strftime("%Y-%m-%d %H:%M JST"),
        "periods": results,
    }
    Path("/Users/nekonaomichi/crypto-lab/wave_j29_period_stability_triple.json").write_text(json.dumps(out, indent=2, default=str))
    print("\nSaved.")


if __name__ == "__main__":
    asyncio.run(main())

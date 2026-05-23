"""Wave J30 — 他8HMeme候補のsatellite価値検証.

BONK/SHIB に加えて DOGE/PEPE/WIF も 8H で価値あるか?
そして 4-way 合成 (Combined + 4 Meme 8H) は 80/10/10 を上回るか?
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

MEME_8H_CANDIDATES = ["BONKUSDT", "SHIBUSDT", "DOGEUSDT", "PEPEUSDT", "WIFUSDT"]
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


def run_bt(df, sig, sym, interval, exit_kw):
    cost = get_cost_params(sym, interval)
    bars_per_year = 2190 if interval == "4h" else 1095
    return run_backtest(df, sig, strategy_name="J30", bars_per_year=bars_per_year,
                        leverage=1.0, **exit_kw, **cost)


def eq_to_daily(eq, bpd):
    eq = np.asarray(eq, dtype=float)
    d = eq[bpd-1::bpd]
    if len(d) < 2: d = eq[::bpd]
    return np.diff(d) / np.where(d[:-1] != 0, d[:-1], 1.0)


def sharpe(r, ppy=365):
    r = np.asarray(r); r = r[np.isfinite(r)]
    if len(r) < 5 or np.std(r, ddof=1) == 0: return 0.0
    return float(np.mean(r) / np.std(r, ddof=1) * np.sqrt(ppy))


async def main():
    print("=== Wave J30: 他8H Meme satellites + 4-way mix ===\n")

    # Load BTC vol_z
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

    # Compute 8H daily for each Meme candidate
    daily_8h_per_sym = {}
    print("=== 8H Meme candidate Sharpe ===")
    for sym in MEME_8H_CANDIDATES:
        df_4h = await fetch_klines(sym, "4h", DAYS)
        df_8h = aggregate_4h_to_8h(df_4h)
        sig = atr_ratio_signal(df_8h, **ATR_PARAMS_8H)
        aligned = btc_idx_8h.reindex(df_8h['open_time'], method='ffill')['volz'].values
        sig[pd.Series(aligned, index=sig.index).fillna(False) >= VOL_Z] = 0
        if (sig != 0).sum() < 5:
            print(f"  {sym} too few signals")
            continue
        r = run_bt(df_8h, sig, sym, "8h", EXIT_8H)
        d = eq_to_daily(r['equity_curve'], 3)
        sh = sharpe(d)
        daily_8h_per_sym[sym] = d
        print(f"  {sym:<10} Sh={sh:+.2f}  trades={int(r['metrics']['total_trades'])}")

    # Compute Combined 4H
    print("\nComputing Combined 4H ...")
    atr_cache = {s: await fetch_klines(s, "4h", DAYS) for s in ATR_SYMBOLS}
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

    fopd_cache = {}
    for s in FOPD_BEST:
        df = await fetch_klines(s, "4h", DAYS)
        try: fr = await fetch_bybit_funding_rate(s, DAYS)
        except: fr = None
        try: oi = await fetch_historical_metrics(s, DAYS)
        except: oi = None
        fopd_cache[s] = {"ohlcv": df, "fr": fr, "oi": oi}
    daily_fopd = {}
    for s, p in FOPD_BEST.items():
        d = fopd_cache[s]
        sig = fopd_signal(d["ohlcv"], d["fr"], d["oi"], p["fr"], p["oi"], p["ret"])
        r = run_bt(d["ohlcv"], sig, s, "4h", {"stop_loss_pct": p["sl"], "take_profit_pct": p["tp"], "max_hold_bars": p["mhb"]})
        daily_fopd[s] = eq_to_daily(r['equity_curve'], 6)
    mf = min(len(v) for v in daily_fopd.values())
    fopd_d = pd.DataFrame({k: v[:mf] for k, v in daily_fopd.items()}).mean(axis=1).values

    common_4h = min(len(atr_d), len(fopd_d))
    combined = 0.5 * atr_d[:common_4h] + 0.5 * fopd_d[:common_4h]

    # Align all to common length
    all_series = {"Combined": combined}
    all_series.update(daily_8h_per_sym)
    n = min(len(v) for v in all_series.values())
    for k in all_series:
        all_series[k] = all_series[k][:n]

    # Correlations matrix
    print("\n=== Correlation matrix (with Combined 4H) ===")
    series_keys = list(all_series.keys())
    print(f"  {'':>10} " + " ".join([f"{k[:8]:>10}" for k in series_keys]))
    corr_data = {}
    for k1 in series_keys:
        corr_data[k1] = {}
        row = [f"{k1[:10]:>10}"]
        for k2 in series_keys:
            c = float(np.corrcoef(all_series[k1], all_series[k2])[0,1])
            corr_data[k1][k2] = round(c, 3)
            row.append(f"{c:>+10.3f}")
        print("  " + " ".join(row))

    # Try variants: 80/x/x/x/x/x with different subsets
    # Variants: keep main 80% Combined, distribute remaining 20% among 8H Memes
    print("\n=== Portfolio variants ===")
    variants = {}
    variants["80% Combined alone"] = combined
    variants["80%C + 10%BONK + 10%SHIB (current best)"] = (
        0.80 * combined + 0.10 * all_series.get("BONKUSDT", np.zeros(n)) + 0.10 * all_series.get("SHIBUSDT", np.zeros(n))
    )
    variants["80%C + 10%BONK + 10%DOGE"] = (
        0.80 * combined + 0.10 * all_series.get("BONKUSDT", np.zeros(n)) + 0.10 * all_series.get("DOGEUSDT", np.zeros(n))
    )
    variants["80%C + 10%SHIB + 10%DOGE"] = (
        0.80 * combined + 0.10 * all_series.get("SHIBUSDT", np.zeros(n)) + 0.10 * all_series.get("DOGEUSDT", np.zeros(n))
    )
    variants["80%C + 5%each (BONK/SHIB/DOGE/PEPE)"] = (
        0.80 * combined +
        0.05 * all_series.get("BONKUSDT", np.zeros(n)) +
        0.05 * all_series.get("SHIBUSDT", np.zeros(n)) +
        0.05 * all_series.get("DOGEUSDT", np.zeros(n)) +
        0.05 * all_series.get("PEPEUSDT", np.zeros(n))
    )
    variants["80%C + 5%each (5 Meme: B/S/D/P/W)"] = (
        0.80 * combined +
        0.04 * all_series.get("BONKUSDT", np.zeros(n)) +
        0.04 * all_series.get("SHIBUSDT", np.zeros(n)) +
        0.04 * all_series.get("DOGEUSDT", np.zeros(n)) +
        0.04 * all_series.get("PEPEUSDT", np.zeros(n)) +
        0.04 * all_series.get("WIFUSDT", np.zeros(n))
    )
    variants["70%C + 6%each (5 Meme)"] = (
        0.70 * combined +
        0.06 * all_series.get("BONKUSDT", np.zeros(n)) +
        0.06 * all_series.get("SHIBUSDT", np.zeros(n)) +
        0.06 * all_series.get("DOGEUSDT", np.zeros(n)) +
        0.06 * all_series.get("PEPEUSDT", np.zeros(n)) +
        0.06 * all_series.get("WIFUSDT", np.zeros(n))
    )

    print(f"\n{'Variant':<60} {'Sharpe':>8} {'Return':>8} {'Max DD':>8} {'Calmar':>8}")
    results = []
    for name, p in variants.items():
        sh = sharpe(p)
        eq = np.cumprod(1 + p)
        ret = (eq[-1] - 1) * 100
        dd = (eq / np.maximum.accumulate(eq) - 1).min() * 100
        cal = abs(ret / dd) if dd != 0 else 0
        print(f"  {name:<60} {sh:>+8.2f} {ret:>+7.1f}% {dd:>+7.1f}% {cal:>8.2f}")
        results.append({"variant": name, "sharpe": round(sh, 3),
                        "return_pct": round(float(ret), 2),
                        "max_dd_pct": round(float(dd), 2),
                        "calmar": round(cal, 2)})

    out = {
        "wave": "J30", "name": "Other 8H Meme satellites + 4/5-way mix",
        "generated_at": datetime.now(timezone(timedelta(hours=9))).strftime("%Y-%m-%d %H:%M JST"),
        "correlations": corr_data,
        "variants": results,
    }
    Path("/Users/nekonaomichi/crypto-lab/wave_j30_other_8h_meme.json").write_text(json.dumps(out, indent=2, default=str))
    print("\nSaved.")


if __name__ == "__main__":
    asyncio.run(main())

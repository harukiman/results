"""Wave J27 — 8H Meme satellites for portfolio enhancement.

Wave J26 で発見:
  8H BONK Sh+2.15 (filt), 8H SHIB Sh+2.23 (filt)
  これらは production 4H に勝らないが、別時間軸 = 独立性高い可能性。

仮説:
  4H Combined (50/50 ATR+FOPD, Sh+3.15) + 8H Meme satellites
  3-way mix で更なる diversification と Calmar 向上を狙う

実装:
  4H Combined を 50% main
  8H BONK 25%, 8H SHIB 25%
  または smaller satellites: main 70%, satellites 30% (各 15%)

数学:
  daily portfolio = w1 * combined_4h_daily + w2 * bonk_8h_daily + w3 * shib_8h_daily
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
ATR_EXIT_4H = {"stop_loss_pct": 0.04, "take_profit_pct": 0.08, "max_hold_bars": 24}
ATR_EXIT_8H = {"stop_loss_pct": 0.04, "take_profit_pct": 0.08, "max_hold_bars": 12}
VOL_Z = 1.5
DAYS = 730


def aggregate_4h_to_8h(df_4h):
    df = df_4h.copy().sort_values('open_time').reset_index(drop=True)
    df['pair_idx'] = df.index // 2
    agg = df.groupby('pair_idx').agg({
        'open_time': 'first', 'open': 'first',
        'high': 'max', 'low': 'min', 'close': 'last',
        'volume': 'sum'
    }).reset_index(drop=True)
    return agg


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
    return run_backtest(df, sig, strategy_name="J27", bars_per_year=bars_per_year,
                        leverage=1.0, **exit_kw, **cost)


def eq_to_daily(eq, bars_per_day):
    eq = np.asarray(eq, dtype=float)
    d = eq[bars_per_day-1::bars_per_day]
    if len(d) < 2: d = eq[::bars_per_day]
    return np.diff(d) / np.where(d[:-1] != 0, d[:-1], 1.0)


def sharpe(r, ppy=365):
    r = np.asarray(r); r = r[np.isfinite(r)]
    if len(r) < 5 or np.std(r, ddof=1) == 0: return 0.0
    return float(np.mean(r) / np.std(r, ddof=1) * np.sqrt(ppy))


async def main():
    print("=== Wave J27: 8H Meme satellites + 4H Combined ===\n")

    # Load
    print("Loading ...")
    atr_cache_4h = {s: await fetch_klines(s, "4h", DAYS) for s in ATR_SYMBOLS}
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

    # 4H ATR daily
    daily_atr_4h = {}
    for s in ATR_SYMBOLS:
        df = atr_cache_4h[s]
        sig = atr_ratio_signal(df, **ATR_PARAMS_4H)
        aligned = btc_idx_4h.reindex(df['open_time'], method='ffill')['volz'].values
        sig[pd.Series(aligned, index=sig.index).fillna(False) >= VOL_Z] = 0
        r = run_bt(df, sig, s, "4h", ATR_EXIT_4H)
        daily_atr_4h[s] = eq_to_daily(r['equity_curve'], 6)
    min_la = min(len(v) for v in daily_atr_4h.values())
    atr_4h = pd.DataFrame({k: v[:min_la] for k, v in daily_atr_4h.items()}).mean(axis=1).values

    # 4H FOPD daily
    daily_fopd = {}
    for s, p in FOPD_BEST.items():
        d = fopd_cache[s]
        sig = fopd_signal(d["ohlcv"], d["fr"], d["oi"], p["fr"], p["oi"], p["ret"])
        r = run_bt(d["ohlcv"], sig, s, "4h", {"stop_loss_pct": p["sl"], "take_profit_pct": p["tp"], "max_hold_bars": p["mhb"]})
        daily_fopd[s] = eq_to_daily(r['equity_curve'], 6)
    min_lf = min(len(v) for v in daily_fopd.values())
    fopd_4h = pd.DataFrame({k: v[:min_lf] for k, v in daily_fopd.items()}).mean(axis=1).values

    common = min(len(atr_4h), len(fopd_4h))
    combined_4h = 0.5 * atr_4h[:common] + 0.5 * fopd_4h[:common]

    # 8H satellites: BONK, SHIB
    df_bonk_4h = atr_cache_4h["BONKUSDT"]
    df_shib_4h = atr_cache_4h["SHIBUSDT"]
    df_bonk_8h = aggregate_4h_to_8h(df_bonk_4h)
    df_shib_8h = aggregate_4h_to_8h(df_shib_4h)

    def run_8h_with_filter(df_8h, sym):
        sig = atr_ratio_signal(df_8h, **ATR_PARAMS_8H)
        aligned = btc_idx_8h.reindex(df_8h['open_time'], method='ffill')['volz'].values
        sig[pd.Series(aligned, index=sig.index).fillna(False) >= VOL_Z] = 0
        r = run_bt(df_8h, sig, sym, "8h", ATR_EXIT_8H)
        # 8H = 3 bars per day
        return eq_to_daily(r['equity_curve'], 3)

    bonk_8h = run_8h_with_filter(df_bonk_8h, "BONKUSDT")
    shib_8h = run_8h_with_filter(df_shib_8h, "SHIBUSDT")

    # Align all to common length
    n = min(len(combined_4h), len(bonk_8h), len(shib_8h))
    combined_4h = combined_4h[:n]
    bonk_8h = bonk_8h[:n]
    shib_8h = shib_8h[:n]

    # Correlations
    print("=== Correlations ===")
    print(f"  combined_4h vs bonk_8h: {np.corrcoef(combined_4h, bonk_8h)[0,1]:+.3f}")
    print(f"  combined_4h vs shib_8h: {np.corrcoef(combined_4h, shib_8h)[0,1]:+.3f}")
    print(f"  bonk_8h vs shib_8h:     {np.corrcoef(bonk_8h, shib_8h)[0,1]:+.3f}")

    # ── Portfolio variants ──
    variants = {
        "Combined 4H (baseline)": (combined_4h),
        "Combined + 25%BONK_8H + 25%SHIB_8H": (0.5 * combined_4h + 0.25 * bonk_8h + 0.25 * shib_8h),
        "Combined 70% + 15%BONK_8H + 15%SHIB_8H": (0.7 * combined_4h + 0.15 * bonk_8h + 0.15 * shib_8h),
        "Combined 80% + 10%BONK_8H + 10%SHIB_8H": (0.8 * combined_4h + 0.1 * bonk_8h + 0.1 * shib_8h),
        "Combined 60% + 20%BONK_8H + 20%SHIB_8H": (0.6 * combined_4h + 0.2 * bonk_8h + 0.2 * shib_8h),
    }

    print("\n=== Portfolios ===")
    print(f"{'Variant':<50} {'Sharpe':>8} {'Return':>8} {'DD':>7} {'Calmar':>8}")
    results = []
    for name, p in variants.items():
        sh = sharpe(p)
        eq = np.cumprod(1 + p)
        ret = (eq[-1] - 1) * 100
        dd = (eq / np.maximum.accumulate(eq) - 1).min() * 100
        cal = abs(ret / dd) if dd != 0 else 0
        print(f"  {name:<50} {sh:>+8.2f} {ret:>+7.1f}% {dd:>+7.1f}% {cal:>8.2f}")
        results.append({"variant": name, "sharpe": round(sh, 3),
                        "return_pct": round(float(ret), 2),
                        "max_dd_pct": round(float(dd), 2),
                        "calmar": round(cal, 2)})

    out = {
        "wave": "J27", "name": "8H Meme satellites + 4H Combined",
        "generated_at": datetime.now(timezone(timedelta(hours=9))).strftime("%Y-%m-%d %H:%M JST"),
        "correlations": {
            "combined_4h_vs_bonk_8h": round(float(np.corrcoef(combined_4h, bonk_8h)[0,1]), 3),
            "combined_4h_vs_shib_8h": round(float(np.corrcoef(combined_4h, shib_8h)[0,1]), 3),
            "bonk_8h_vs_shib_8h": round(float(np.corrcoef(bonk_8h, shib_8h)[0,1]), 3),
        },
        "variants": results,
    }
    Path("/Users/nekonaomichi/crypto-lab/wave_j27_8h_satellites.json").write_text(json.dumps(out, indent=2, default=str))
    print("\nSaved.")


if __name__ == "__main__":
    asyncio.run(main())

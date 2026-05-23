"""Wave J18 — Combined 50/50 portfolio: H1/H2 period stability check.

Wave I で ATR 単独の H1/H2 検証は済み (H1 Sh+3.28, H2 Sh+2.24)。
合成も同様に前半365d / 後半365d で独立に評価し、期間頑健性を確認。

Also: vary threshold of vol_z filter to see if 50/50 stays optimal across periods.
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


def atr_ratio_signal(df, atr_short=7, atr_long=56, threshold=0.6, ema_fast=20, ema_slow=80):
    atr_s = (df['high'] - df['low']).rolling(atr_short).mean()
    atr_l = (df['high'] - df['low']).rolling(atr_long).mean()
    comp = atr_s < atr_l * threshold
    ema_f = df['close'].ewm(span=ema_fast).mean()
    ema_s = df['close'].ewm(span=ema_slow).mean()
    sig = pd.Series(0, index=df.index)
    sig[comp & (ema_f > ema_s)] = 1
    sig[comp & (ema_f < ema_s)] = -1
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


def eq_to_daily(eq):
    eq = np.asarray(eq, dtype=float)
    d = eq[5::6]
    if len(d) < 2: d = eq[::6]
    return np.diff(d) / np.where(d[:-1] != 0, d[:-1], 1.0)


def sharpe(r, ppy=365):
    r = np.asarray(r); r = r[np.isfinite(r)]
    if len(r) < 5 or np.std(r, ddof=1) == 0: return 0.0
    return float(np.mean(r) / np.std(r, ddof=1) * np.sqrt(ppy))


def run_bt(df, sig, sym, **exit_kw):
    cost = get_cost_params(sym, "4h")
    return run_backtest(df, sig, strategy_name="ck",
                        bars_per_year=BARS_PER_YEAR, leverage=1.0,
                        **exit_kw, **cost)


async def compute_atr_daily_period(atr_cache, btc_idx, start_idx, end_idx):
    """Compute ATR portfolio daily returns for a specific bar slice."""
    daily = {}
    for s in ATR_SYMBOLS:
        df = atr_cache[s].iloc[start_idx:end_idx].reset_index(drop=True)
        sig = atr_ratio_signal(df, **ATR_PARAMS)
        aligned = btc_idx.reindex(df['open_time'], method='ffill')['volz'].values
        bad = pd.Series(aligned, index=sig.index).fillna(False) >= VOL_Z
        sig[bad] = 0
        if (sig != 0).sum() < 3:
            daily[s] = np.zeros(60)
            continue
        r = run_bt(df, sig, s, **ATR_EXIT)
        daily[s] = eq_to_daily(r['equity_curve'])
    m = min(len(v) for v in daily.values())
    return pd.DataFrame({k: v[:m] for k, v in daily.items()}).mean(axis=1).values


async def compute_fopd_daily_period(fopd_cache, start_idx, end_idx):
    daily = {}
    for s, p in FOPD_BEST.items():
        d = fopd_cache[s]
        # Full signal first (z-score needs warmup), then slice
        sig_full = fopd_signal(d["ohlcv"], d["fr"], d["oi"], p["fr"], p["oi"], p["ret"])
        df_slice = d["ohlcv"].iloc[start_idx:end_idx].reset_index(drop=True)
        sig_slice = sig_full.iloc[start_idx:end_idx].reset_index(drop=True)
        if (sig_slice != 0).sum() < 3:
            daily[s] = np.zeros(60)
            continue
        r = run_bt(df_slice, sig_slice, s,
                   stop_loss_pct=p["sl"], take_profit_pct=p["tp"], max_hold_bars=p["mhb"])
        daily[s] = eq_to_daily(r['equity_curve'])
    m = min(len(v) for v in daily.values())
    return pd.DataFrame({k: v[:m] for k, v in daily.items()}).mean(axis=1).values


async def main():
    t0 = time.time()
    print("=== Wave J18: 50/50 Combined Portfolio — H1/H2 Period Stability ===\n")

    print("Loading ...")
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

    # ── Define periods ──
    n_bars = len(atr_cache[ATR_SYMBOLS[0]])
    half = n_bars // 2
    print(f"\nTotal bars: {n_bars}, half = {half}")
    print(f"H1: bars 0..{half} (first 365d)")
    print(f"H2: bars {half}..{n_bars} (second 365d)")

    periods = {
        "Full (730d)": (0, n_bars),
        "H1 (1-365d)": (0, half),
        "H2 (365-730d)": (half, n_bars),
    }

    weights = [(0.5, 0.5), (0.4, 0.6), (0.6, 0.4), (1.0, 0.0), (0.0, 1.0)]

    print("\n" + "="*90)
    print(f"{'Period':<18} {'Weight':<14} {'Sharpe':>8} {'Return':>8} {'Max DD':>8} {'Calmar':>8} {'corr':>7}")
    print("="*90)

    results = []
    for period_name, (s_idx, e_idx) in periods.items():
        atr_d = await compute_atr_daily_period(atr_cache, btc_idx, s_idx, e_idx)
        fopd_d = await compute_fopd_daily_period(fopd_cache, s_idx, e_idx)
        common = min(len(atr_d), len(fopd_d))
        a = atr_d[:common]; f = fopd_d[:common]
        corr = float(np.corrcoef(a, f)[0, 1]) if len(a) > 5 else 0.0

        for w_atr, w_fopd in weights:
            combo = w_atr * a + w_fopd * f
            sh = sharpe(combo)
            if len(combo) == 0:
                continue
            eq = np.cumprod(1 + combo)
            ret = (eq[-1] - 1) * 100
            dd = (eq / np.maximum.accumulate(eq) - 1).min() * 100
            cal = abs(ret / dd) if dd != 0 else 0
            label = f"{int(w_atr*100)}/{int(w_fopd*100)}"
            print(f"  {period_name:<18} {label:<14} {sh:>+8.2f} {ret:>+7.1f}% {dd:>+7.1f}% {cal:>8.2f} {corr:>+7.3f}")
            results.append({
                "period": period_name, "weight": label,
                "sharpe": round(sh, 3), "return_pct": round(float(ret), 2),
                "max_dd_pct": round(float(dd), 2), "calmar": round(cal, 2),
                "correlation": round(corr, 4),
            })

    out = {
        "wave": "J18", "name": "Combined 50/50 H1/H2 Period Stability",
        "generated_at": datetime.now(timezone(timedelta(hours=9))).strftime("%Y-%m-%d %H:%M JST"),
        "results": results,
        "runtime_sec": round(time.time() - t0, 1),
    }
    Path("/Users/nekonaomichi/crypto-lab/wave_j18_period_stability.json").write_text(json.dumps(out, indent=2, default=str))
    print(f"\nSaved (runtime {out['runtime_sec']}s)")


if __name__ == "__main__":
    asyncio.run(main())

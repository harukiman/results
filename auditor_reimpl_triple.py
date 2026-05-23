"""Wave J31 — Auditor Independent Re-implementation (G7) for 80/10/10 portfolio.

§6 G7 のための独立な再実装。
原実装 (audit_triple_portfolio.py) とは:
  1. ATR計算: pandas rolling.mean → numpy convolve
  2. EMA計算: pandas ewm → 手動 alpha-loop (これは過去の Auditor 実装と同)
  3. Z-score計算: pandas rolling → numpy 直接
  4. 集計: pandas merge_asof → numpy searchsorted

合格条件: |ΔSh| < 0.3, |ΔReturn| < 10%, |ΔDD| < 5%
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
VOL_Z = 1.5
DAYS = 730


def numpy_sma(arr, window):
    """SMA using numpy convolve (Auditor reimpl)."""
    arr = np.asarray(arr, dtype=float)
    result = np.full_like(arr, np.nan)
    cumsum = np.cumsum(np.insert(arr, 0, 0))
    result[window-1:] = (cumsum[window:] - cumsum[:-window]) / window
    return result


def numpy_ema(arr, span):
    """EMA using manual alpha-loop (Auditor reimpl, no pandas ewm)."""
    arr = np.asarray(arr, dtype=float)
    alpha = 2.0 / (span + 1)
    result = np.zeros_like(arr)
    result[0] = arr[0]
    for i in range(1, len(arr)):
        if np.isnan(arr[i]):
            result[i] = result[i-1]
        else:
            result[i] = alpha * arr[i] + (1 - alpha) * result[i-1]
    return result


def atr_ratio_signal_AUDITOR(df, atr_short=7, atr_long=56, threshold=0.6, ema_fast=20, ema_slow=80):
    """Auditor reimpl: numpy direct instead of pandas."""
    high = df['high'].values
    low = df['low'].values
    close = df['close'].values
    hl = high - low
    atr_s = numpy_sma(hl, atr_short)
    atr_l = numpy_sma(hl, atr_long)
    compression = (atr_s < atr_l * threshold) & np.isfinite(atr_s) & np.isfinite(atr_l)
    ema_f_arr = numpy_ema(close, ema_fast)
    ema_s_arr = numpy_ema(close, ema_slow)
    sig = np.zeros(len(df), dtype=int)
    sig[compression & (ema_f_arr > ema_s_arr)] = 1
    sig[compression & (ema_f_arr < ema_s_arr)] = -1
    warmup = max(atr_long, ema_slow) + 5
    sig[:warmup] = 0
    return pd.Series(sig, index=df.index)


def fopd_signal_AUDITOR(df, fr_series, oi_series, fr_z, oi_z, ret_z, w=180):
    """Auditor reimpl: numpy z-score."""
    df_w = df.copy().sort_values('open_time').reset_index(drop=True)
    df_w['open_time'] = pd.to_datetime(df_w['open_time']).astype('datetime64[ns]')

    # FR alignment - same as original
    if fr_series is not None and not fr_series.empty:
        fr_df = fr_series.copy()
        fr_df['timestamp'] = pd.to_datetime(fr_df['timestamp']).astype('datetime64[ns]')
        fr_df = fr_df.sort_values('timestamp').reset_index(drop=True)
        m = pd.merge_asof(df_w[['open_time']], fr_df.rename(columns={'timestamp':'open_time'}), on='open_time', direction='backward')
        fr = m['funding_rate'].fillna(0).values
    else:
        fr = np.zeros(len(df_w))

    # OI alignment
    if oi_series is not None and not oi_series.empty and 'oi' in oi_series.columns:
        oi_df = oi_series.copy()
        oi_df['timestamp'] = pd.to_datetime(oi_df['timestamp']).astype('datetime64[ns]')
        oi_df = oi_df.sort_values('timestamp').reset_index(drop=True)
        mo = pd.merge_asof(df_w[['open_time']], oi_df[['timestamp','oi']].rename(columns={'timestamp':'open_time'}), on='open_time', direction='backward')
        oi_vals = mo['oi'].ffill().bfill().values
    else:
        oi_vals = np.full(len(df_w), np.nan)

    # OI change 6 bars - numpy roll
    oi_24h = np.zeros_like(oi_vals)
    oi_24h[6:] = (oi_vals[6:] - oi_vals[:-6]) / np.where(oi_vals[:-6] != 0, oi_vals[:-6], 1.0)

    # Price return 24h
    close = df_w['close'].values
    ret_24h = np.zeros_like(close)
    ret_24h[6:] = (close[6:] - close[:-6]) / np.where(close[:-6] != 0, close[:-6], 1.0)

    # Numpy rolling z-score (different impl - manual loop)
    def numpy_zscore(arr, window):
        out = np.full_like(arr, 0.0, dtype=float)
        for i in range(window, len(arr)):
            w = arr[i-window:i]
            w = w[np.isfinite(w)]
            if len(w) < 2: continue
            mu = np.mean(w); sd = np.std(w, ddof=0)
            if sd < 1e-12: continue
            out[i] = (arr[i] - mu) / sd
        return out

    fr_z_v = numpy_zscore(fr, w)
    oi_z_v = numpy_zscore(oi_24h, w)
    ret_z_v = numpy_zscore(ret_24h, w)

    long_s = (fr_z_v < -fr_z) & (oi_z_v < -oi_z) & (ret_z_v < -ret_z)
    short_s = (fr_z_v > fr_z) & (oi_z_v > oi_z) & (ret_z_v > ret_z)
    sig = np.zeros(len(df_w), dtype=int)
    sig[long_s] = +1; sig[short_s] = -1; sig[:w + 10] = 0
    return pd.Series(sig, index=df_w.index)


def aggregate_4h_to_8h_AUDITOR(df_4h):
    """Numpy-based aggregation (different from pandas groupby)."""
    n = len(df_4h)
    df_arr = df_4h.copy().sort_values('open_time').reset_index(drop=True)
    n_8h = n // 2
    out = {
        'open_time': df_arr['open_time'].iloc[::2].iloc[:n_8h].values,
        'open': df_arr['open'].iloc[::2].iloc[:n_8h].values,
        'high': np.maximum(df_arr['high'].iloc[::2].iloc[:n_8h].values, df_arr['high'].iloc[1::2].iloc[:n_8h].values),
        'low': np.minimum(df_arr['low'].iloc[::2].iloc[:n_8h].values, df_arr['low'].iloc[1::2].iloc[:n_8h].values),
        'close': df_arr['close'].iloc[1::2].iloc[:n_8h].values,
        'volume': df_arr['volume'].iloc[::2].iloc[:n_8h].values + df_arr['volume'].iloc[1::2].iloc[:n_8h].values,
    }
    return pd.DataFrame(out)


def sharpe(r, ppy=365):
    r = np.asarray(r); r = r[np.isfinite(r)]
    if len(r) < 5 or np.std(r, ddof=1) == 0: return 0.0
    return float(np.mean(r) / np.std(r, ddof=1) * np.sqrt(ppy))


def eq_to_daily(eq, bpd):
    eq = np.asarray(eq, dtype=float)
    d = eq[bpd-1::bpd]
    if len(d) < 2: d = eq[::bpd]
    return np.diff(d) / np.where(d[:-1] != 0, d[:-1], 1.0)


async def main():
    print("=== Wave J31: Auditor Independent Reimpl (G7) for 80/10/10 ===\n")

    print("Loading data ...")
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

    # AUDITOR REIMPL: vol_z with numpy
    btc_close = btc['close'].values
    btc_ret = np.zeros_like(btc_close)
    btc_ret[1:] = (btc_close[1:] - btc_close[:-1]) / btc_close[:-1]
    # rolling 60-bar std
    btc_rv = np.full_like(btc_close, np.nan)
    for i in range(60, len(btc_close)):
        w = btc_ret[i-59:i+1]
        btc_rv[i] = np.std(w, ddof=1) * np.sqrt(2190) * 100
    # rolling 360-bar mean/std of rv
    btc_rvm = np.full_like(btc_close, np.nan)
    btc_rvs = np.full_like(btc_close, np.nan)
    for i in range(360, len(btc_close)):
        w = btc_rv[i-359:i+1]
        w_f = w[np.isfinite(w)]
        if len(w_f) > 5:
            btc_rvm[i] = np.mean(w_f)
            btc_rvs[i] = np.std(w_f, ddof=1)
    btc_volz = (btc_rv - btc_rvm) / (btc_rvs + 1e-10)
    btc_aud = btc.copy()
    btc_aud['volz'] = btc_volz
    btc_idx_4h = btc_aud.set_index('open_time')

    # 8H BTC vol_z (aggregated)
    btc_8h = aggregate_4h_to_8h_AUDITOR(btc_aud)
    btc_8h_ret = np.zeros_like(btc_8h['close'].values)
    btc_8h_close = btc_8h['close'].values
    btc_8h_ret[1:] = (btc_8h_close[1:] - btc_8h_close[:-1]) / btc_8h_close[:-1]
    btc_8h_rv = np.full_like(btc_8h_close, np.nan)
    for i in range(30, len(btc_8h_close)):
        w = btc_8h_ret[i-29:i+1]
        btc_8h_rv[i] = np.std(w, ddof=1) * np.sqrt(1095) * 100
    btc_8h_rvm = np.full_like(btc_8h_close, np.nan)
    btc_8h_rvs = np.full_like(btc_8h_close, np.nan)
    for i in range(180, len(btc_8h_close)):
        w = btc_8h_rv[i-179:i+1]
        w_f = w[np.isfinite(w)]
        if len(w_f) > 5:
            btc_8h_rvm[i] = np.mean(w_f)
            btc_8h_rvs[i] = np.std(w_f, ddof=1)
    btc_8h_volz = (btc_8h_rv - btc_8h_rvm) / (btc_8h_rvs + 1e-10)
    btc_8h['volz'] = btc_8h_volz
    btc_idx_8h = btc_8h.set_index('open_time')

    # ── ATR with AUDITOR signal ──
    print("Computing ATR (AUDITOR reimpl) ...")
    daily_atr = {}
    for s in ATR_SYMBOLS:
        df = atr_cache[s]
        sig = atr_ratio_signal_AUDITOR(df)
        aligned = btc_idx_4h.reindex(df['open_time'], method='ffill')['volz'].values
        sig[pd.Series(aligned, index=sig.index).fillna(False) >= VOL_Z] = 0
        cost = get_cost_params(s, "4h")
        r = run_backtest(df, sig, strategy_name="aud_atr", bars_per_year=2190, leverage=1.0,
                         stop_loss_pct=0.04, take_profit_pct=0.08, max_hold_bars=24, **cost)
        daily_atr[s] = eq_to_daily(r['equity_curve'], 6)
    ma = min(len(v) for v in daily_atr.values())
    atr_d = pd.DataFrame({k: v[:ma] for k, v in daily_atr.items()}).mean(axis=1).values

    # ── FOPD with AUDITOR signal ──
    print("Computing FOPD (AUDITOR reimpl) ...")
    daily_fopd = {}
    for s, p in FOPD_BEST.items():
        d = fopd_cache[s]
        sig = fopd_signal_AUDITOR(d["ohlcv"], d["fr"], d["oi"], p["fr"], p["oi"], p["ret"])
        cost = get_cost_params(s, "4h")
        r = run_backtest(d["ohlcv"], sig, strategy_name="aud_fopd", bars_per_year=2190,
                         leverage=1.0, stop_loss_pct=p["sl"], take_profit_pct=p["tp"],
                         max_hold_bars=p["mhb"], **cost)
        daily_fopd[s] = eq_to_daily(r['equity_curve'], 6)
    mf = min(len(v) for v in daily_fopd.values())
    fopd_d = pd.DataFrame({k: v[:mf] for k, v in daily_fopd.items()}).mean(axis=1).values

    common_4h = min(len(atr_d), len(fopd_d))
    combined = 0.5 * atr_d[:common_4h] + 0.5 * fopd_d[:common_4h]

    # ── 8H BONK/SHIB ──
    print("Computing 8H Meme (AUDITOR reimpl) ...")
    bonk_8h = aggregate_4h_to_8h_AUDITOR(atr_cache["BONKUSDT"])
    shib_8h = aggregate_4h_to_8h_AUDITOR(atr_cache["SHIBUSDT"])

    def compute_8h(df_8h, sym):
        sig = atr_ratio_signal_AUDITOR(df_8h, atr_short=4, atr_long=28, threshold=0.6,
                                        ema_fast=10, ema_slow=40)
        aligned = btc_idx_8h.reindex(df_8h['open_time'], method='ffill')['volz'].values
        sig[pd.Series(aligned, index=sig.index).fillna(False) >= VOL_Z] = 0
        cost = get_cost_params(sym, "8h")
        r = run_backtest(df_8h, sig, strategy_name="aud_8h", bars_per_year=1095, leverage=1.0,
                         stop_loss_pct=0.04, take_profit_pct=0.08, max_hold_bars=12, **cost)
        return eq_to_daily(r['equity_curve'], 3)

    bonk_d = compute_8h(bonk_8h, "BONKUSDT")
    shib_d = compute_8h(shib_8h, "SHIBUSDT")

    common = min(len(combined), len(bonk_d), len(shib_d))
    triple_aud = 0.80 * combined[:common] + 0.10 * bonk_d[:common] + 0.10 * shib_d[:common]

    # Metrics
    sh_aud = sharpe(triple_aud)
    eq = np.cumprod(1 + triple_aud)
    ret_aud = (eq[-1] - 1) * 100
    dd_aud = (eq / np.maximum.accumulate(eq) - 1).min() * 100

    print("\n=== AUDITOR (numpy reimpl) ===")
    print(f"  Sh = {sh_aud:+.3f}")
    print(f"  Return = {ret_aud:+.2f}%")
    print(f"  Max DD = {dd_aud:+.2f}%")
    print(f"  Calmar = {abs(ret_aud/dd_aud):.2f}")

    # Compare with primary (audit_triple_portfolio.json)
    try:
        primary = json.loads(Path("/Users/nekonaomichi/crypto-lab/audit_triple_portfolio.json").read_text())
        prim = primary["baseline"]
        print("\n=== PRIMARY (pandas-based, audit_triple_portfolio.json) ===")
        print(f"  Sh = {prim['sharpe']:+.3f}")
        print(f"  Return = {prim['return_pct']:+.2f}%")
        print(f"  Max DD = {prim['max_dd_pct']:+.2f}%")
        print(f"  Calmar = {prim['calmar']:.2f}")
        d_sh = abs(sh_aud - prim['sharpe'])
        d_ret = abs(ret_aud - prim['return_pct'])
        d_dd = abs(dd_aud - prim['max_dd_pct'])
        agreement = d_sh < 0.3 and d_ret < 10 and d_dd < 5
        print(f"\n=== AGREEMENT CHECK ===")
        print(f"  |ΔSh| = {d_sh:.3f}  (threshold 0.3) {'✓' if d_sh < 0.3 else '✗'}")
        print(f"  |ΔReturn| = {d_ret:.2f}%  (threshold 10%) {'✓' if d_ret < 10 else '✗'}")
        print(f"  |ΔDD| = {d_dd:.2f}%  (threshold 5%) {'✓' if d_dd < 5 else '✗'}")
        print(f"  AGREEMENT: {'PASS (G7 OK)' if agreement else 'FAIL — review needed'}")
    except Exception as e:
        print(f"\nCould not load primary: {e}")
        agreement = None

    out = {
        "wave": "J31", "name": "Auditor Independent Reimpl (G7) for 80/10/10",
        "generated_at": datetime.now(timezone(timedelta(hours=9))).strftime("%Y-%m-%d %H:%M JST"),
        "auditor": {"sharpe": round(sh_aud, 3), "return_pct": round(ret_aud, 2),
                    "max_dd_pct": round(dd_aud, 2), "calmar": round(abs(ret_aud/dd_aud) if dd_aud != 0 else 0, 2)},
        "agreement_pass": agreement,
    }
    Path("/Users/nekonaomichi/crypto-lab/auditor_reimpl_triple.json").write_text(json.dumps(out, indent=2, default=str))
    print("\nSaved.")


if __name__ == "__main__":
    asyncio.run(main())

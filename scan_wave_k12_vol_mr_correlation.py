"""Wave K12 — vol_z mean-reversion best (SOL/ETH) vs 80/10/10 correlation check.

K11で発見した best 4 (SOL/ETH/BTC/BNB) を 80/10/10 と相関測定。
独立性高ければ 4軸目として価値。
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

# K11 best per symbol
BEST_VOL_MR = {
    "BTCUSDT":  {"vzl": -1.0, "vzh": 1.0, "tw": 10, "sl": 0.04, "tp": 0.06, "mhb": 12},
    "ETHUSDT":  {"vzl": -2.0, "vzh": 1.0, "tw": 20, "sl": 0.04, "tp": 0.06, "mhb": 12},
    "SOLUSDT":  {"vzl": -1.5, "vzh": 2.0, "tw": 10, "sl": 0.04, "tp": 0.06, "mhb": 12},
    "BNBUSDT":  {"vzl": -1.5, "vzh": 1.0, "tw": 10, "sl": 0.04, "tp": 0.06, "mhb": 12},
}

# 80/10/10 components
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


def btc_vol_mr_signal(df, vol_z_low=-1.0, vol_z_high=2.0, trend_window=20):
    close = df['close'].values
    ret = np.zeros_like(close)
    ret[1:] = (close[1:] - close[:-1]) / close[:-1]
    rv = pd.Series(ret).rolling(60).std() * np.sqrt(2190) * 100
    rvm = rv.rolling(360).mean()
    rvs = rv.rolling(360).std()
    vol_z = ((rv - rvm) / (rvs + 1e-10)).fillna(0).values
    ema_fast = pd.Series(close).ewm(span=trend_window).mean().values
    ema_slow = pd.Series(close).ewm(span=trend_window * 3).mean().values
    bullish = ema_fast > ema_slow
    bearish = ema_fast < ema_slow
    recent_ret = pd.Series(close).pct_change(6).fillna(0).values
    sig = np.zeros(len(df), dtype=int)
    sig[(vol_z < vol_z_low) & bullish] = +1
    sig[(vol_z < vol_z_low) & bearish] = -1
    sig[(vol_z > vol_z_high) & (recent_ret < -0.05)] = +1
    sig[(vol_z > vol_z_high) & (recent_ret > 0.05)] = -1
    sig[:380] = 0
    return pd.Series(sig, index=df.index)


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
    return run_backtest(df, sig, strategy_name="K12", bars_per_year=bars_per_year,
                        leverage=1.0, **exit_kw, **cost)


async def main():
    print("=== Wave K12: vol_z MR vs 80/10/10 correlation ===\n")

    # Compute 80/10/10
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
    common_4h = min(len(atr_d), len(fopd_d))
    combined = 0.5 * atr_d[:common_4h] + 0.5 * fopd_d[:common_4h]

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

    common_triple = min(len(combined), len(bonk_d), len(shib_d))
    triple_80_10_10 = (0.80 * combined[:common_triple] +
                       0.10 * bonk_d[:common_triple] +
                       0.10 * shib_d[:common_triple])

    # Compute vol_z MR per symbol
    daily_vol_mr = {}
    for sym, p in BEST_VOL_MR.items():
        df = await fetch_klines(sym, "4h", DAYS)
        sig = btc_vol_mr_signal(df, vol_z_low=p["vzl"], vol_z_high=p["vzh"], trend_window=p["tw"])
        r = run_bt(df, sig, sym, "4h", {"stop_loss_pct": p["sl"], "take_profit_pct": p["tp"], "max_hold_bars": p["mhb"]})
        daily_vol_mr[sym] = eq_to_daily(r['equity_curve'], 6)
        m = r['metrics']
        print(f"  {sym:<10} vol_MR Sh={float(m['sharpe_ratio']):+.2f}, Return={float(m['total_return_pct']):+.1f}%, DD={float(m['max_drawdown_pct']):+.1f}%, trades={int(m['total_trades'])}")

    # 4-symbol equal-weight vol_MR portfolio
    n_vol = min(len(v) for v in daily_vol_mr.values())
    vol_mr_port = pd.DataFrame({k: v[:n_vol] for k, v in daily_vol_mr.items()}).mean(axis=1).values
    sh_vol_mr = sharpe(vol_mr_port)
    eq_v = np.cumprod(1 + vol_mr_port)
    ret_v = (eq_v[-1] - 1) * 100
    dd_v = (eq_v / np.maximum.accumulate(eq_v) - 1).min() * 100
    print(f"\nvol_MR equal-weight portfolio: Sh={sh_vol_mr:+.2f}  ret={ret_v:+.1f}%  dd={dd_v:+.1f}%  Calmar={abs(ret_v/dd_v):.2f}")

    # Compare with triple
    common = min(len(vol_mr_port), len(triple_80_10_10))
    triple_aligned = triple_80_10_10[:common]
    vol_mr_aligned = vol_mr_port[:common]

    corr = float(np.corrcoef(triple_aligned, vol_mr_aligned)[0, 1])
    print(f"\n=== Correlation: 80/10/10 vs vol_MR portfolio = {corr:+.3f} ===")
    if abs(corr) < 0.3:
        print("  → 独立性高い → 4軸目候補!")
    elif abs(corr) < 0.5:
        print("  → 中程度独立 → satellite価値あり")
    else:
        print("  → 高相関 → 既存と重複")

    # Test 4-way mix: 80/10/10 majority + vol_MR satellite
    print("\n=== 4-way mix portfolios ===")
    variants = [
        ("100% 80/10/10 (baseline)", triple_aligned),
        ("90% 80/10/10 + 10% vol_MR", 0.9 * triple_aligned + 0.1 * vol_mr_aligned),
        ("85% + 15%", 0.85 * triple_aligned + 0.15 * vol_mr_aligned),
        ("80% + 20%", 0.80 * triple_aligned + 0.20 * vol_mr_aligned),
        ("70% + 30%", 0.70 * triple_aligned + 0.30 * vol_mr_aligned),
        ("60% + 40%", 0.60 * triple_aligned + 0.40 * vol_mr_aligned),
    ]
    for name, p in variants:
        s = sharpe(p)
        eq = np.cumprod(1 + p)
        ret = (eq[-1] - 1) * 100
        dd = (eq / np.maximum.accumulate(eq) - 1).min() * 100
        cal = abs(ret / dd) if dd != 0 else 0
        print(f"  {name:<40} Sh={s:+.2f}  ret={ret:+.1f}%  dd={dd:+.1f}%  Calmar={cal:.2f}")

    out = {
        "wave": "K12", "name": "vol_MR vs 80/10/10 correlation check",
        "generated_at": datetime.now(timezone(timedelta(hours=9))).strftime("%Y-%m-%d %H:%M JST"),
        "correlation": round(corr, 3),
        "vol_mr_portfolio": {"sharpe": round(sh_vol_mr, 3), "return_pct": round(float(ret_v), 2), "dd_pct": round(float(dd_v), 2)},
    }
    Path("/Users/nekonaomichi/crypto-lab/wave_k12_vol_mr_corr.json").write_text(json.dumps(out, indent=2, default=str))
    print("\nSaved.")


if __name__ == "__main__":
    asyncio.run(main())

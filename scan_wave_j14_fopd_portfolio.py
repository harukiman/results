"""Wave J14 — FOPD multi-symbol portfolio + correlation with existing survivors.

最良候補 (Wave J12 結果から):
  BNB Sh+1.80 (best), AVAX +1.68, ETH +1.60, ADA +1.46, LINK +1.27, DOT +0.97

各銘柄の best param を使い、等加重ポートフォリオでの分散効果と
既存 ATR_Ratio × 8 + vol_z との相関を測る。
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

# Best params per symbol (from Wave J12)
FOPD_BEST = {
    "BNBUSDT":  {"fr": 1.0, "oi": 0.5, "ret": 1.5, "sl": 0.04, "tp": 0.06, "mhb": 6},
    "AVAXUSDT": {"fr": 2.0, "oi": 1.0, "ret": 1.5, "sl": 0.04, "tp": 0.06, "mhb": 6},
    "ETHUSDT":  {"fr": 1.5, "oi": 1.5, "ret": 0.5, "sl": 0.04, "tp": 0.06, "mhb": 6},
    "ADAUSDT":  {"fr": 2.0, "oi": 0.5, "ret": 0.5, "sl": 0.04, "tp": 0.06, "mhb": 6},
    "LINKUSDT": {"fr": 1.0, "oi": 0.5, "ret": 1.0, "sl": 0.04, "tp": 0.06, "mhb": 6},
    "DOTUSDT":  {"fr": 2.0, "oi": 1.0, "ret": 1.0, "sl": 0.04, "tp": 0.06, "mhb": 6},
}

DAYS = 730
BARS_PER_YEAR = 2190


def fopd_signal(df, fr_series, oi_series,
                fr_z_thresh=1.5, oi_z_thresh=1.0, ret_z_thresh=1.0,
                zscore_window=180):
    df_w = df.copy().sort_values('open_time').reset_index(drop=True)
    df_w['open_time'] = pd.to_datetime(df_w['open_time']).astype('datetime64[ns]')
    if fr_series is not None and not fr_series.empty:
        fr_df = fr_series.copy()
        fr_df['timestamp'] = pd.to_datetime(fr_df['timestamp']).astype('datetime64[ns]')
        fr_df = fr_df.sort_values('timestamp').reset_index(drop=True)
        merged_fr = pd.merge_asof(df_w[['open_time']], fr_df.rename(columns={'timestamp':'open_time'}), on='open_time', direction='backward')
        fr_vals = merged_fr['funding_rate'].fillna(0).values
    else:
        fr_vals = np.zeros(len(df_w))
    if oi_series is not None and not oi_series.empty and 'oi' in oi_series.columns:
        oi_df = oi_series.copy()
        oi_df['timestamp'] = pd.to_datetime(oi_df['timestamp']).astype('datetime64[ns]')
        oi_df = oi_df.sort_values('timestamp').reset_index(drop=True)
        merged_oi = pd.merge_asof(df_w[['open_time']], oi_df[['timestamp','oi']].rename(columns={'timestamp':'open_time'}), on='open_time', direction='backward')
        oi_vals = merged_oi['oi'].ffill().bfill().values
    else:
        oi_vals = np.full(len(df_w), np.nan)
    oi_change = pd.Series(oi_vals, index=df_w.index).pct_change(6).fillna(0).values
    close = df_w['close'].values
    ret_24h = pd.Series(close, index=df_w.index).pct_change(6).fillna(0).values
    fr_s = pd.Series(fr_vals); oi_s = pd.Series(oi_change); ret_s = pd.Series(ret_24h)
    fr_z = (fr_s - fr_s.rolling(zscore_window).mean()) / (fr_s.rolling(zscore_window).std() + 1e-12)
    oi_z = (oi_s - oi_s.rolling(zscore_window).mean()) / (oi_s.rolling(zscore_window).std() + 1e-12)
    ret_z = (ret_s - ret_s.rolling(zscore_window).mean()) / (ret_s.rolling(zscore_window).std() + 1e-12)
    fr_z_v = fr_z.fillna(0).values; oi_z_v = oi_z.fillna(0).values; ret_z_v = ret_z.fillna(0).values
    long_sig = (fr_z_v < -fr_z_thresh) & (oi_z_v < -oi_z_thresh) & (ret_z_v < -ret_z_thresh)
    short_sig = (fr_z_v > fr_z_thresh) & (oi_z_v > oi_z_thresh) & (ret_z_v > ret_z_thresh)
    sig = np.zeros(len(df_w), dtype=int)
    sig[long_sig] = +1
    sig[short_sig] = -1
    sig[:zscore_window + 10] = 0
    return pd.Series(sig, index=df_w.index)


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


def eq_to_daily(eq):
    eq = np.asarray(eq, dtype=float)
    d = eq[5::6]
    if len(d) < 2: d = eq[::6]
    return np.diff(d) / np.where(d[:-1] != 0, d[:-1], 1.0)


def sharpe(r, ppy=365):
    r = np.asarray(r); r = r[np.isfinite(r)]
    if len(r) < 5 or np.std(r, ddof=1) == 0: return 0.0
    return float(np.mean(r) / np.std(r, ddof=1) * np.sqrt(ppy))


def run_bt(df, sig, sym, sl=0.04, tp=0.06, mhb=6):
    cost = get_cost_params(sym, "4h")
    return run_backtest(df, sig, strategy_name="FOPD_PORT",
                        bars_per_year=BARS_PER_YEAR, leverage=1.0,
                        stop_loss_pct=sl, take_profit_pct=tp, max_hold_bars=mhb,
                        **cost)


async def main():
    t0 = time.time()
    print("=== Wave J14: FOPD multi-symbol portfolio ===\n")

    # Load data for all symbols
    print("Loading data ...")
    cache = {}
    syms_fopd = list(FOPD_BEST.keys())
    for s in syms_fopd:
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
        print(f"  {s:<10} OHLCV={len(df)}")

    # ATR portfolio comparison data
    atr_symbols = ["OPUSDT", "WIFUSDT", "INJUSDT", "BONKUSDT",
                   "DOGEUSDT", "SHIBUSDT", "ARBUSDT", "LINKUSDT"]
    atr_cache = {}
    for s in atr_symbols:
        atr_cache[s] = await fetch_klines(s, "4h", DAYS)

    btc_vz = await fetch_klines("BTCUSDT", "4h", DAYS)
    btc_vz['ret'] = btc_vz['close'].pct_change()
    btc_vz['rv'] = btc_vz['ret'].rolling(60).std() * np.sqrt(BARS_PER_YEAR) * 100
    btc_vz['rvm'] = btc_vz['rv'].rolling(360).mean()
    btc_vz['rvs'] = btc_vz['rv'].rolling(360).std()
    btc_vz['volz'] = (btc_vz['rv'] - btc_vz['rvm']) / (btc_vz['rvs'] + 1e-10)

    # ── FOPD portfolio ──
    print("\n--- FOPD portfolio (6 symbols, equal-weight) ---")
    daily_fopd = {}
    for s, params in FOPD_BEST.items():
        d = cache[s]
        sig = fopd_signal(d["ohlcv"], d["fr"], d["oi"],
                          fr_z_thresh=params["fr"], oi_z_thresh=params["oi"],
                          ret_z_thresh=params["ret"])
        n_sig = (sig != 0).sum()
        if n_sig < 5:
            print(f"  {s:<10} TOO FEW SIGNALS"); continue
        r = run_bt(d["ohlcv"], sig, s, params["sl"], params["tp"], params["mhb"])
        m = r['metrics']
        sh = float(m.get('sharpe_ratio') or 0); ret = float(m.get('total_return_pct') or 0)
        dd = float(m.get('max_drawdown_pct') or 0); trades = int(m.get('total_trades') or 0)
        daily_fopd[s] = eq_to_daily(r['equity_curve'])
        print(f"  {s:<10} Sh={sh:+.2f} ret={ret:+.1f}% dd={dd:+.1f}% trades={trades}")

    min_l = min(len(v) for v in daily_fopd.values())
    aligned = pd.DataFrame({k: v[:min_l] for k, v in daily_fopd.items()})
    port_ret = aligned.mean(axis=1).values
    port_sh = sharpe(port_ret)
    eq = np.cumprod(1 + port_ret)
    port_ret_total = (eq[-1] - 1) * 100
    port_dd = (eq / np.maximum.accumulate(eq) - 1).min() * 100
    individual_avg = aligned.apply(lambda x: sharpe(x.values)).mean()
    div_ratio = port_sh / individual_avg if individual_avg > 0 else 0
    print(f"\nFOPD Portfolio: Sharpe={port_sh:+.2f} Return={port_ret_total:+.1f}% DD={port_dd:+.1f}% "
          f"Calmar={abs(port_ret_total/port_dd):.2f}  分散効果={div_ratio:.2f}x")

    # ── ATR portfolio (for correlation comparison) ──
    print("\n--- ATR portfolio (8 symbols, baseline) ---")
    daily_atr = {}
    for s in atr_symbols:
        df = atr_cache[s]
        sig = atr_ratio_signal(df, atr_short=7, atr_long=56, threshold=0.6, ema_fast=20, ema_slow=80)
        # Apply vol_z filter
        btc_idx = btc_vz.set_index('open_time')
        aligned_vz = btc_idx.reindex(df['open_time'], method='ffill')['volz'].values
        bad = pd.Series(aligned_vz, index=sig.index).fillna(False) >= 1.5
        sig_f = sig.copy(); sig_f[bad] = 0
        r = run_bt(df, sig_f, s, sl=0.04, tp=0.08, mhb=24)
        daily_atr[s] = eq_to_daily(r['equity_curve'])

    min_l2 = min(len(v) for v in daily_atr.values())
    aligned_atr = pd.DataFrame({k: v[:min_l2] for k, v in daily_atr.items()})
    atr_port_ret = aligned_atr.mean(axis=1).values
    atr_sh = sharpe(atr_port_ret)
    print(f"ATR Portfolio (comparison): Sharpe={atr_sh:+.2f}")

    # ── Correlation FOPD x ATR ──
    common_len = min(len(port_ret), len(atr_port_ret))
    correlation = float(np.corrcoef(port_ret[:common_len], atr_port_ret[:common_len])[0, 1])
    print(f"\n=== Correlation FOPD vs ATR portfolio = {correlation:+.3f} ===")
    if abs(correlation) < 0.3:
        print("  → 独立性高い → サテライト候補として有望")
    else:
        print("  → 中〜高相関 → 既存と重複、サテライト価値低い")

    # ── Combined portfolio (60% ATR + 40% FOPD) ──
    combined_ret = 0.6 * atr_port_ret[:common_len] + 0.4 * port_ret[:common_len]
    comb_sh = sharpe(combined_ret)
    comb_eq = np.cumprod(1 + combined_ret)
    comb_ret_total = (comb_eq[-1] - 1) * 100
    comb_dd = (comb_eq / np.maximum.accumulate(comb_eq) - 1).min() * 100
    print(f"\n=== Combined ATR (60%) + FOPD (40%) ===")
    print(f"  Sharpe={comb_sh:+.2f} Return={comb_ret_total:+.1f}% DD={comb_dd:+.1f}% Calmar={abs(comb_ret_total/comb_dd):.2f}")

    out = {
        "wave": "J14", "name": "FOPD multi-symbol portfolio + ATR correlation",
        "generated_at": datetime.now(timezone(timedelta(hours=9))).strftime("%Y-%m-%d %H:%M JST"),
        "fopd_portfolio": {
            "symbols": list(FOPD_BEST.keys()),
            "sharpe": round(port_sh, 3), "return_pct": round(port_ret_total, 2),
            "max_dd_pct": round(port_dd, 2),
            "calmar": round(abs(port_ret_total/port_dd) if port_dd != 0 else 0, 2),
            "div_ratio": round(div_ratio, 3),
        },
        "atr_portfolio_baseline": {"sharpe": round(atr_sh, 3)},
        "correlation_FOPD_vs_ATR": round(correlation, 3),
        "combined_60ATR_40FOPD": {
            "sharpe": round(comb_sh, 3), "return_pct": round(comb_ret_total, 2),
            "max_dd_pct": round(comb_dd, 2),
            "calmar": round(abs(comb_ret_total/comb_dd) if comb_dd != 0 else 0, 2),
        },
        "runtime_sec": round(time.time() - t0, 1),
    }
    Path("/Users/nekonaomichi/crypto-lab/wave_j14_fopd_portfolio.json").write_text(json.dumps(out, indent=2, default=str))
    print(f"\nSaved (runtime {out['runtime_sec']}s)")


if __name__ == "__main__":
    asyncio.run(main())

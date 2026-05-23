"""Wave K1 — Kelly criterion for optimal leverage (80/10/10 portfolio).

実運用に向けた最重要パラメータ「レバレッジ」を最適化:

Kelly criterion (fractional):
  f* = μ / σ² ≈ Sharpe / σ_daily (in leverage units)
  ただしフルKellyは attheoretical な「破産前提込み」最大化 → 実運用は 0.25-0.5 Kelly

評価:
  1. フルKelly: f = mean / var (per-day)
  2. 半Kelly: f / 2
  3. 四分Kelly: f / 4
  4. MCで破産確率 < 1%/5% を満たすレバ
  5. Calmar最大化レバ
  6. Sortino最大化レバ
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


def sortino(r, ppy=365):
    """Sortino ratio — only downside deviation in denominator."""
    r = np.asarray(r); r = r[np.isfinite(r)]
    if len(r) < 5: return 0.0
    down = r[r < 0]
    if len(down) == 0:
        return 0.0
    down_std = np.std(down, ddof=1)
    if down_std == 0: return 0.0
    return float(np.mean(r) / down_std * np.sqrt(ppy))


def run_bt(df, sig, sym, interval, exit_kw):
    cost = get_cost_params(sym, interval)
    bars_per_year = 2190 if interval == "4h" else 1095
    return run_backtest(df, sig, strategy_name="K1", bars_per_year=bars_per_year,
                        leverage=1.0, **exit_kw, **cost)


def kelly_fraction(returns):
    """Full Kelly fraction = E[R] / Var[R]."""
    r = np.asarray(returns); r = r[np.isfinite(r)]
    if len(r) < 5 or np.var(r) == 0: return 0.0
    return float(np.mean(r) / np.var(r))


def mc_with_leverage(returns, leverage, n_sim=10000, n_days=365, ruin_thresh=-0.50, seed=42):
    """Bootstrap MC at given leverage."""
    rng = np.random.RandomState(seed)
    r = np.asarray(returns); r = r[np.isfinite(r)]
    finals = []; dds = []
    ruined = 0
    for _ in range(n_sim):
        s = rng.choice(r, size=n_days, replace=True)
        lev_r = np.clip(s * leverage, -0.99, None)
        eq = np.cumprod(1 + lev_r)
        dd = (eq / np.maximum.accumulate(eq) - 1).min()
        if dd <= ruin_thresh: ruined += 1
        finals.append(eq[-1] - 1)
        dds.append(dd)
    return {
        "ruin_prob": ruined / n_sim,
        "median_final": float(np.median(finals)),
        "p5_final": float(np.percentile(finals, 5)),
        "p50_final": float(np.percentile(finals, 50)),
        "p95_final": float(np.percentile(finals, 95)),
        "median_max_dd": float(np.median(dds)),
        "p5_max_dd": float(np.percentile(dds, 5)),
        # geometric mean of final wealth
        "geometric_mean": float(np.exp(np.mean(np.log(np.maximum(np.array(finals) + 1, 1e-10))))),
    }


async def main():
    print("=== Wave K1: Kelly Criterion for 80/10/10 ===\n")

    # Load + compute triple daily returns (same as audit_triple_portfolio.py)
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

    # ATR
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

    # FOPD
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

    # 8H
    bonk_8h = aggregate_4h_to_8h(atr_cache["BONKUSDT"])
    shib_8h = aggregate_4h_to_8h(atr_cache["SHIBUSDT"])
    def compute_8h(df_8h, sym):
        sig = atr_ratio_signal(df_8h, **ATR_PARAMS_8H)
        aligned = btc_idx_8h.reindex(df_8h['open_time'], method='ffill')['volz'].values
        sig[pd.Series(aligned, index=sig.index).fillna(False) >= VOL_Z] = 0
        r = run_bt(df_8h, sig, sym, "8h", EXIT_8H)
        return eq_to_daily(r['equity_curve'], 3)
    bonk_d = compute_8h(bonk_8h, "BONKUSDT")
    shib_d = compute_8h(shib_8h, "SHIBUSDT")

    common = min(len(combined), len(bonk_d), len(shib_d))
    triple = 0.80 * combined[:common] + 0.10 * bonk_d[:common] + 0.10 * shib_d[:common]

    # ── Kelly计算 ──
    mu = np.mean(triple); sigma2 = np.var(triple); sigma = np.std(triple)
    sh = mu / sigma * np.sqrt(365)
    f_full_kelly = mu / sigma2
    print(f"=== Stats (1x leverage) ===")
    print(f"  Mean daily return: {mu*100:+.4f}%")
    print(f"  Daily std:         {sigma*100:.4f}%")
    print(f"  Daily variance:    {sigma2:.6e}")
    print(f"  Annualized Sharpe: {sh:+.2f}")
    print(f"\n=== Kelly Fraction ===")
    print(f"  Full Kelly:    f* = μ/σ² = {f_full_kelly:.2f}x")
    print(f"  Half Kelly:    {f_full_kelly/2:.2f}x")
    print(f"  Quarter Kelly: {f_full_kelly/4:.2f}x")

    # ── Leverage sweep MC ──
    print(f"\n=== Leverage sweep MC (10000 sim × 365 days) ===")
    print(f"{'Lev':>6} {'Ruin':>8} {'p5 Ret':>10} {'Median':>10} {'p95 Ret':>10} {'Med DD':>9} {'p5 DD':>9}")
    leverages = [1, 2, 3, 5, 7, 10, 15, 20, 25, 30, f_full_kelly/4, f_full_kelly/2, f_full_kelly]
    leverages = sorted(set([round(l, 1) for l in leverages]))
    results = []
    for lev in leverages:
        mc = mc_with_leverage(triple, lev, n_sim=10000)
        results.append({"leverage": lev, **mc})
        print(f"  {lev:>5.1f}x {mc['ruin_prob']:>7.2%} {mc['p5_final']*100:>+9.0f}% {mc['median_final']*100:>+9.0f}% {mc['p95_final']*100:>+9.0f}% {mc['median_max_dd']*100:>+8.1f}% {mc['p5_max_dd']*100:>+8.1f}%")

    # Find optimal leverage subject to ruin constraint
    safe_lev_1pct = max([r for r in results if r["ruin_prob"] < 0.01], key=lambda r: r["median_final"], default=None)
    safe_lev_5pct = max([r for r in results if r["ruin_prob"] < 0.05], key=lambda r: r["median_final"], default=None)
    sortino_v = sortino(triple)
    print(f"\n=== Optima ===")
    print(f"  Safe at ruin<1%:  Lev {safe_lev_1pct['leverage']}x, median ret {safe_lev_1pct['median_final']*100:+.0f}%")
    print(f"  Safe at ruin<5%:  Lev {safe_lev_5pct['leverage']}x, median ret {safe_lev_5pct['median_final']*100:+.0f}%")
    print(f"  Sortino (1x): {sortino_v:+.2f}")

    out = {
        "wave": "K1", "name": "Kelly Criterion + Leverage Optimization for 80/10/10",
        "generated_at": datetime.now(timezone(timedelta(hours=9))).strftime("%Y-%m-%d %H:%M JST"),
        "stats_1x": {
            "mean_daily": float(mu), "std_daily": float(sigma), "var_daily": float(sigma2),
            "annualized_sharpe": float(sh), "sortino": float(sortino_v),
        },
        "kelly": {
            "full": round(f_full_kelly, 2),
            "half": round(f_full_kelly/2, 2),
            "quarter": round(f_full_kelly/4, 2),
        },
        "leverage_sweep": results,
        "safe_1pct": safe_lev_1pct,
        "safe_5pct": safe_lev_5pct,
    }
    Path("/Users/nekonaomichi/crypto-lab/wave_k1_kelly.json").write_text(json.dumps(out, indent=2, default=str))
    print("\nSaved.")


if __name__ == "__main__":
    asyncio.run(main())

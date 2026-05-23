"""Wave J15 — Allocation optimization for combined ATR + FOPD portfolio.

Grid search: ATR weight ∈ {0, 10, 20, ..., 100}%
For each weight:
  - Daily portfolio = w*ATR_daily + (1-w)*FOPD_daily
  - Compute Sharpe, Return, DD, Calmar
  - MC ruin probability at multiple leverage levels
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
ATR_PARAMS = {"atr_short": 7, "atr_long": 56, "threshold": 0.6,
              "ema_fast": 20, "ema_slow": 80}
EXIT = {"stop_loss_pct": 0.04, "take_profit_pct": 0.08, "max_hold_bars": 24}
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


def mc_ruin(daily_returns, leverage, n_sim=5000, n_days=365, ruin_thresh=-0.50, seed=42):
    rng = np.random.RandomState(seed)
    r = np.asarray(daily_returns); r = r[np.isfinite(r)]
    if len(r) < 30: return None
    ruined = 0; finals = []
    for _ in range(n_sim):
        s = rng.choice(r, size=n_days, replace=True)
        lev_r = np.clip(s * leverage, -0.99, None)
        eq = np.cumprod(1 + lev_r)
        dd = (eq / np.maximum.accumulate(eq) - 1).min()
        if dd <= ruin_thresh: ruined += 1
        finals.append(eq[-1] - 1)
    return {
        "ruin_prob": ruined / n_sim,
        "median_final": float(np.median(finals)),
        "p5_final": float(np.percentile(finals, 5)),
        "p95_final": float(np.percentile(finals, 95)),
    }


async def main():
    t0 = time.time()
    print("=== Wave J15: Allocation optimization (ATR/FOPD weight grid) ===\n")

    # ── Compute ATR daily returns ──
    print("Loading ATR data ...")
    atr_cache = {}
    for s in ATR_SYMBOLS:
        atr_cache[s] = await fetch_klines(s, "4h", DAYS)
    btc = await fetch_klines("BTCUSDT", "4h", DAYS)
    btc['ret'] = btc['close'].pct_change()
    btc['rv'] = btc['ret'].rolling(60).std() * np.sqrt(BARS_PER_YEAR) * 100
    btc['rvm'] = btc['rv'].rolling(360).mean()
    btc['rvs'] = btc['rv'].rolling(360).std()
    btc['volz'] = (btc['rv'] - btc['rvm']) / (btc['rvs'] + 1e-10)

    daily_atr = {}
    for s in ATR_SYMBOLS:
        df = atr_cache[s]
        sig = atr_ratio_signal(df, **ATR_PARAMS)
        btc_idx = btc.set_index('open_time')
        aligned = btc_idx.reindex(df['open_time'], method='ffill')['volz'].values
        bad = pd.Series(aligned, index=sig.index).fillna(False) >= VOL_Z
        sig[bad] = 0
        cost = get_cost_params(s, "4h")
        r = run_backtest(df, sig, strategy_name="ATR", bars_per_year=BARS_PER_YEAR, leverage=1.0,
                         **EXIT, **cost)
        daily_atr[s] = eq_to_daily(r['equity_curve'])
    min_la = min(len(v) for v in daily_atr.values())
    atr_port = pd.DataFrame({k: v[:min_la] for k, v in daily_atr.items()}).mean(axis=1).values

    # ── Compute FOPD daily returns ──
    print("Loading FOPD data ...")
    fopd_cache = {}
    for s in FOPD_BEST:
        df = await fetch_klines(s, "4h", DAYS)
        try: fr_df = await fetch_bybit_funding_rate(s, DAYS)
        except: fr_df = None
        try: oi_df = await fetch_historical_metrics(s, DAYS)
        except: oi_df = None
        fopd_cache[s] = {"ohlcv": df, "fr": fr_df, "oi": oi_df}

    daily_fopd = {}
    for s, p in FOPD_BEST.items():
        d = fopd_cache[s]
        sig = fopd_signal(d["ohlcv"], d["fr"], d["oi"], p["fr"], p["oi"], p["ret"])
        cost = get_cost_params(s, "4h")
        r = run_backtest(d["ohlcv"], sig, strategy_name="FOPD", bars_per_year=BARS_PER_YEAR,
                         leverage=1.0, stop_loss_pct=p["sl"], take_profit_pct=p["tp"],
                         max_hold_bars=p["mhb"], **cost)
        daily_fopd[s] = eq_to_daily(r['equity_curve'])
    min_lf = min(len(v) for v in daily_fopd.values())
    fopd_port = pd.DataFrame({k: v[:min_lf] for k, v in daily_fopd.items()}).mean(axis=1).values

    # ── Grid search ──
    common = min(len(atr_port), len(fopd_port))
    a = atr_port[:common]
    f = fopd_port[:common]
    correlation = float(np.corrcoef(a, f)[0, 1])
    print(f"\nCorrelation ATR vs FOPD: {correlation:+.4f}")
    print(f"Common period: {common} daily returns\n")

    print(f"{'ATR w':>6} {'FOPD w':>7} {'Sharpe':>8} {'Return':>7} {'Max DD':>8} {'Calmar':>7} {'Ruin1x':>7} {'Ruin3x':>7} {'Ruin5x':>7}")
    results = []
    for atr_w_pct in range(0, 101, 5):
        atr_w = atr_w_pct / 100.0
        fopd_w = 1.0 - atr_w
        combo = atr_w * a + fopd_w * f
        sh = sharpe(combo)
        eq = np.cumprod(1 + combo)
        ret = (eq[-1] - 1) * 100
        dd = (eq / np.maximum.accumulate(eq) - 1).min() * 100
        cal = abs(ret / dd) if dd != 0 else 0
        mc1 = mc_ruin(combo, 1, n_sim=3000)
        mc3 = mc_ruin(combo, 3, n_sim=3000)
        mc5 = mc_ruin(combo, 5, n_sim=3000)
        results.append({
            "atr_weight": atr_w, "fopd_weight": fopd_w,
            "sharpe": round(sh, 3),
            "return_pct": round(float(ret), 2),
            "max_dd_pct": round(float(dd), 2),
            "calmar": round(cal, 2),
            "mc_ruin_1x": round(mc1["ruin_prob"], 4),
            "mc_ruin_3x": round(mc3["ruin_prob"], 4),
            "mc_ruin_5x": round(mc5["ruin_prob"], 4),
            "mc_median_1x": round(mc1["median_final"] * 100, 2),
            "mc_median_3x": round(mc3["median_final"] * 100, 2),
            "mc_median_5x": round(mc5["median_final"] * 100, 2),
        })
        print(f"  {atr_w_pct:>3}% {fopd_w*100:>5.0f}%  "
              f"{sh:>+8.2f} {ret:>+6.1f}% {dd:>+7.1f}% {cal:>7.2f}  "
              f"{mc1['ruin_prob']:>7.2%} {mc3['ruin_prob']:>7.2%} {mc5['ruin_prob']:>7.2%}")

    # Find optima
    best_sharpe = max(results, key=lambda x: x["sharpe"])
    best_calmar = max(results, key=lambda x: x["calmar"])
    best_return_with_low_ruin = max([r for r in results if r["mc_ruin_3x"] < 0.005],
                                     key=lambda x: x["return_pct"], default=None)

    print(f"\n=== Optima ===")
    print(f"Best Sharpe:    ATR={best_sharpe['atr_weight']:.0%}, Sh={best_sharpe['sharpe']:+.2f}, "
          f"DD={best_sharpe['max_dd_pct']:+.1f}%, Calmar={best_sharpe['calmar']:.2f}")
    print(f"Best Calmar:    ATR={best_calmar['atr_weight']:.0%}, Sh={best_calmar['sharpe']:+.2f}, "
          f"DD={best_calmar['max_dd_pct']:+.1f}%, Calmar={best_calmar['calmar']:.2f}")
    if best_return_with_low_ruin:
        print(f"Best Return at 3x lev with ruin<0.5%: ATR={best_return_with_low_ruin['atr_weight']:.0%}, "
              f"3x median={best_return_with_low_ruin['mc_median_3x']:+.0f}%, ruin={best_return_with_low_ruin['mc_ruin_3x']:.2%}")

    out = {
        "wave": "J15", "name": "Combined Allocation Optimization",
        "generated_at": datetime.now(timezone(timedelta(hours=9))).strftime("%Y-%m-%d %H:%M JST"),
        "correlation": correlation,
        "n_daily_obs": common,
        "results": results,
        "best_sharpe": best_sharpe,
        "best_calmar": best_calmar,
        "best_return_with_low_ruin": best_return_with_low_ruin,
        "runtime_sec": round(time.time() - t0, 1),
    }
    Path("/Users/nekonaomichi/crypto-lab/wave_j15_allocation.json").write_text(json.dumps(out, indent=2, default=str))
    print(f"\nSaved (runtime {out['runtime_sec']}s)")


if __name__ == "__main__":
    asyncio.run(main())

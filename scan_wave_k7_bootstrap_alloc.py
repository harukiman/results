"""Wave K7 — Bootstrap-based allocation re-optimization.

Wave K5 で発見: 観測 Sharpe で 80/10/10 (+3.57) が 50/50 (+3.15) を超えるが、
Bootstrap median では 50/50 (+3.06) > 80/10/10 (+2.78)。

本Waveで「Bootstrap median Sharpe 最大化配分」を探索:
  - 3次元グリッド: w_combined ∈ {0.5..1.0}, w_bonk_8h ∈ {0..0.25}, w_shib_8h ∈ {0..0.25}
  - 各配分で 5000-bootstrap median sharpe を計算
  - 最良 honest 配分を特定
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
    return run_backtest(df, sig, strategy_name="K7", bars_per_year=bars_per_year,
                        leverage=1.0, **exit_kw, **cost)


def bootstrap_sharpe_median(returns, n_boot=2000, mean_block_size=20, seed=42):
    """Bootstrap median Sharpe (faster than full CI: only need median)."""
    rng = np.random.RandomState(seed)
    T = len(returns)
    p = 1.0 / mean_block_size
    boot_sh = np.zeros(n_boot)
    for b in range(n_boot):
        idx = np.zeros(T, dtype=int)
        i = rng.randint(0, T)
        for t in range(T):
            idx[t] = i
            i = i + 1
            if i >= T: i = rng.randint(0, T)
            if rng.random() < p: i = rng.randint(0, T)
        boot_sh[b] = sharpe(returns[idx])
    return float(np.median(boot_sh))


async def main():
    print("=== Wave K7: Bootstrap-based Allocation Re-optimization ===\n")

    # Setup
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

    common = min(len(atr_d), len(fopd_d), len(bonk_d), len(shib_d))
    atr_d = atr_d[:common]; fopd_d = fopd_d[:common]; bonk_d = bonk_d[:common]; shib_d = shib_d[:common]

    print(f"Daily returns T={common} days\n")

    # Search: w_atr_50_50 share, w_meme_total share
    # 0% Meme = pure ATR vs FOPD
    # 20% Meme = current 80/10/10
    # Sweep w_combined ∈ [0.6, 1.0] step 0.05 (combined 4H)
    #       w_meme_total ∈ [0.0, 0.4] step 0.05 (split equally BONK/SHIB)
    # also internal ATR/FOPD weight within combined: 50/50 fixed (Wave J15 best)

    print(f"{'w_4H':<6} {'w_BONK':<8} {'w_SHIB':<8} {'Obs Sh':<8} {'Boot Sh med':<13} {'Calmar':<8}")
    print("-" * 60)
    results = []
    for w_combined in np.arange(0.6, 1.01, 0.05):
        for w_meme_total in np.arange(0.0, 0.41, 0.05):
            if abs(w_combined + w_meme_total - 1.0) > 0.001:
                continue
            w_bonk = w_meme_total / 2
            w_shib = w_meme_total / 2
            # combined = 50% ATR + 50% FOPD always
            combined = 0.5 * atr_d + 0.5 * fopd_d
            triple = w_combined * combined + w_bonk * bonk_d + w_shib * shib_d
            obs_sh = sharpe(triple)
            eq = np.cumprod(1 + triple)
            ret = (eq[-1] - 1) * 100
            dd = (eq / np.maximum.accumulate(eq) - 1).min() * 100
            cal = abs(ret / dd) if dd != 0 else 0
            boot_sh_med = bootstrap_sharpe_median(triple, n_boot=2000, mean_block_size=20)
            results.append({
                "w_combined": round(w_combined, 2), "w_bonk": round(w_bonk, 3),
                "w_shib": round(w_shib, 3),
                "observed_sharpe": round(obs_sh, 3),
                "bootstrap_median_sharpe": round(boot_sh_med, 3),
                "return_pct": round(float(ret), 2),
                "max_dd_pct": round(float(dd), 2),
                "calmar": round(cal, 2),
            })
            print(f"  {w_combined:<6.2f} {w_bonk:<8.3f} {w_shib:<8.3f} {obs_sh:>+7.2f} {boot_sh_med:>+12.2f} {cal:<8.2f}")

    # Find best by bootstrap median Sharpe
    best_boot = max(results, key=lambda x: x["bootstrap_median_sharpe"])
    best_obs = max(results, key=lambda x: x["observed_sharpe"])
    best_cal = max(results, key=lambda x: x["calmar"])
    print(f"\n=== Optima ===")
    print(f"Best Bootstrap median Sh: w_C={best_boot['w_combined']}, w_B={best_boot['w_bonk']}, w_S={best_boot['w_shib']} → boot Sh={best_boot['bootstrap_median_sharpe']:+.2f}, obs Sh={best_boot['observed_sharpe']:+.2f}, Calmar={best_boot['calmar']:.2f}")
    print(f"Best Observed Sh:         w_C={best_obs['w_combined']}, w_B={best_obs['w_bonk']}, w_S={best_obs['w_shib']} → obs Sh={best_obs['observed_sharpe']:+.2f}, boot Sh={best_obs['bootstrap_median_sharpe']:+.2f}")
    print(f"Best Calmar:              w_C={best_cal['w_combined']}, w_B={best_cal['w_bonk']}, w_S={best_cal['w_shib']} → Calmar={best_cal['calmar']:.2f}, boot Sh={best_cal['bootstrap_median_sharpe']:+.2f}")

    out = {
        "wave": "K7", "name": "Bootstrap-based Allocation Re-optimization",
        "generated_at": datetime.now(timezone(timedelta(hours=9))).strftime("%Y-%m-%d %H:%M JST"),
        "config": {"T_days": common, "n_boot": 2000, "block_size": 20},
        "results": results,
        "best_bootstrap_median": best_boot,
        "best_observed": best_obs,
        "best_calmar": best_cal,
    }
    Path("/Users/nekonaomichi/crypto-lab/wave_k7_bootstrap_alloc.json").write_text(json.dumps(out, indent=2, default=str))
    print("\nSaved.")


if __name__ == "__main__":
    asyncio.run(main())

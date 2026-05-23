"""Wave J20 — Dynamic regime-switching weights based on BTC vol_z.

仮説:
  - vol_z 低 (落ち着いた市場): ATR_Ratio (圧縮検出) が活躍 → ATR weight 上げる
  - vol_z 高 (荒れた市場): FOPD (クラウディング contrarian) が活躍 → FOPD weight 上げる

  Wave I で発見した「天然ヘッジ構造」を動的配分で強化できるか?

実装:
  各バーで btc vol_z を取得 → 連続関数 (sigmoid or piecewise) で重み決定
  daily portfolio return = w_atr(t) * atr_ret(t) + w_fopd(t) * fopd_ret(t)

3つのスイッチング方式を比較:
  (a) Piecewise: vol_z<-0.5: 70/30, -0.5..+0.5: 50/50, >+0.5: 30/70
  (b) Sigmoid smooth: w_atr = sigmoid(-vol_z * k) + 0.3 normalized
  (c) Stronger piecewise: vol_z<0: 80/20, vol_z>=0: 20/80
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
ATR_PARAMS = {"atr_short": 7, "atr_long": 56, "threshold": 0.6, "ema_fast": 20, "ema_slow": 80}
ATR_EXIT = {"stop_loss_pct": 0.04, "take_profit_pct": 0.08, "max_hold_bars": 24}
VOL_Z = 1.5
DAYS = 730
BARS_PER_YEAR = 2190


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
    return run_backtest(df, sig, strategy_name="dyn", bars_per_year=BARS_PER_YEAR,
                        leverage=1.0, **exit_kw, **cost)


async def main():
    print("=== Wave J20: Dynamic Regime-Switching Portfolio ===\n")

    # Load
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

    # ATR daily returns
    atr_daily = {}
    for s in ATR_SYMBOLS:
        df = atr_cache[s]
        sig = atr_ratio_signal(df, **ATR_PARAMS)
        aligned = btc_idx.reindex(df['open_time'], method='ffill')['volz'].values
        bad = pd.Series(aligned, index=sig.index).fillna(False) >= VOL_Z
        sig[bad] = 0
        r = run_bt(df, sig, s, **ATR_EXIT)
        atr_daily[s] = eq_to_daily(r['equity_curve'])
    min_la = min(len(v) for v in atr_daily.values())
    aligned_atr = pd.DataFrame({k: v[:min_la] for k, v in atr_daily.items()})
    atr_d = aligned_atr.mean(axis=1).values

    # FOPD daily returns
    fopd_daily = {}
    for s, p in FOPD_BEST.items():
        d = fopd_cache[s]
        sig = fopd_signal(d["ohlcv"], d["fr"], d["oi"], p["fr"], p["oi"], p["ret"])
        r = run_bt(d["ohlcv"], sig, s, stop_loss_pct=p["sl"], take_profit_pct=p["tp"], max_hold_bars=p["mhb"])
        fopd_daily[s] = eq_to_daily(r['equity_curve'])
    min_lf = min(len(v) for v in fopd_daily.values())
    aligned_fopd = pd.DataFrame({k: v[:min_lf] for k, v in fopd_daily.items()})
    fopd_d = aligned_fopd.mean(axis=1).values

    common = min(len(atr_d), len(fopd_d))
    atr_d = atr_d[:common]; fopd_d = fopd_d[:common]

    # ── Get daily-sampled vol_z (for daily weight) ──
    # vol_z is per-4h-bar, sample every 6th
    bar_vz = btc['volz'].values
    daily_vz = bar_vz[5::6][:common+1]
    if len(daily_vz) < common + 1:
        daily_vz = np.concatenate([daily_vz, np.zeros(common + 1 - len(daily_vz))])
    # Use prior day's vol_z to weight today's returns (no lookahead)
    weight_vz_lag = daily_vz[:-1][:common]

    # ── Define weight schemes ──
    schemes = {}

    # Fixed baselines for reference
    schemes["Fixed 50/50"] = np.full(common, 0.5)
    schemes["Fixed 40/60"] = np.full(common, 0.4)
    schemes["Fixed 60/40"] = np.full(common, 0.6)

    # (a) Piecewise mild
    w_mild = np.where(weight_vz_lag < -0.5, 0.7,
              np.where(weight_vz_lag < 0.5, 0.5, 0.3))
    schemes["Dynamic mild (vol_z piecewise -0.5/+0.5)"] = w_mild

    # (b) Sigmoid smooth (center 0, slope k=1)
    w_sig = 1 / (1 + np.exp(weight_vz_lag))  # vol_z 高 → ATR weight 低
    # Normalize to range [0.2, 0.8]
    w_sig_scaled = 0.2 + 0.6 * w_sig
    schemes["Dynamic sigmoid (k=1, range 0.2-0.8)"] = w_sig_scaled

    # (c) Strong piecewise
    w_strong = np.where(weight_vz_lag < 0, 0.8, 0.2)
    schemes["Dynamic strong (vol_z <0: 80/20, >=0: 20/80)"] = w_strong

    # (d) Inverted - sanity check
    w_inv = np.where(weight_vz_lag < -0.5, 0.3,
              np.where(weight_vz_lag < 0.5, 0.5, 0.7))
    schemes["INVERTED (sanity check, should be worse)"] = w_inv

    # ── Evaluate ──
    print(f"{'Scheme':<55} {'Sharpe':>8} {'Return':>8} {'Max DD':>8} {'Calmar':>8} {'avg ATR w':>10}")
    results = []
    for name, w_atr_series in schemes.items():
        w_atr = np.asarray(w_atr_series)
        # Ensure length matches
        n = min(len(w_atr), common)
        port = w_atr[:n] * atr_d[:n] + (1 - w_atr[:n]) * fopd_d[:n]
        sh = sharpe(port)
        eq = np.cumprod(1 + port)
        ret = (eq[-1] - 1) * 100
        dd = (eq / np.maximum.accumulate(eq) - 1).min() * 100
        cal = abs(ret / dd) if dd != 0 else 0
        avg_w = float(np.mean(w_atr[:n]))
        results.append({
            "scheme": name, "sharpe": round(sh, 3),
            "return_pct": round(float(ret), 2), "max_dd_pct": round(float(dd), 2),
            "calmar": round(cal, 2), "avg_atr_weight": round(avg_w, 3),
        })
        print(f"  {name:<55} {sh:>+8.2f} {ret:>+7.1f}% {dd:>+7.1f}% {cal:>8.2f} {avg_w:>10.3f}")

    # Find best
    results_sorted = sorted(results, key=lambda x: x["calmar"], reverse=True)
    print(f"\n=== Best Calmar: {results_sorted[0]['scheme']} (Calmar {results_sorted[0]['calmar']}) ===")
    print(f"=== Worst Calmar: {results_sorted[-1]['scheme']} (Calmar {results_sorted[-1]['calmar']}) ===")

    # ── Conclusion check: did dynamic beat fixed 50/50? ──
    fixed_5050 = next(r for r in results if r["scheme"] == "Fixed 50/50")
    print(f"\n=== Comparison vs Fixed 50/50 (Calmar {fixed_5050['calmar']}) ===")
    for r in results:
        if r["scheme"] == "Fixed 50/50": continue
        diff_sh = r["sharpe"] - fixed_5050["sharpe"]
        diff_cal = r["calmar"] - fixed_5050["calmar"]
        verdict = "BETTER" if diff_cal > 0 else "worse"
        print(f"  {r['scheme']:<55} ΔSh={diff_sh:+.2f}, ΔCalmar={diff_cal:+.2f}  → {verdict}")

    out = {
        "wave": "J20", "name": "Dynamic Regime-Switching Portfolio",
        "generated_at": datetime.now(timezone(timedelta(hours=9))).strftime("%Y-%m-%d %H:%M JST"),
        "results": results,
        "best_calmar_scheme": results_sorted[0],
        "fixed_5050_baseline": fixed_5050,
    }
    Path("/Users/nekonaomichi/crypto-lab/wave_j20_dynamic_regime.json").write_text(json.dumps(out, indent=2, default=str))
    print(f"\nSaved.")


if __name__ == "__main__":
    asyncio.run(main())

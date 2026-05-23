"""Wave I — Robustness validation of vol_z=1.5 filter.

Tests:
  1. Threshold sensitivity: vol_z ∈ {0.5, 0.75, 1.0, 1.25, 1.5, 1.75, 2.0, 2.5, 3.0}
     If 1.5 is a smooth local maximum, it's robust. If a spike, overfit.
  2. Sub-period stability: fit threshold on first 365d, test on last 365d (and vice-versa).
     Look for: same optimum, or graceful degradation.
  3. Apply vol_z filter to satellite strategies (SampEn, MemeMom, VSS, VolReg) to test generality.
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
from engine.data import fetch_klines
from engine.backtest import run_backtest
from engine.cost_config import get_cost_params

SYMBOLS_8 = ["OPUSDT", "WIFUSDT", "INJUSDT", "BONKUSDT",
             "DOGEUSDT", "SHIBUSDT", "ARBUSDT", "LINKUSDT"]
ATR_PARAMS = {"atr_short": 7, "atr_long": 56, "threshold": 0.6,
              "ema_fast": 20, "ema_slow": 80}
EXIT = {"stop_loss_pct": 0.04, "take_profit_pct": 0.08, "max_hold_bars": 24}
DAYS = 730
BARS_PER_YEAR = 2190
THRESHOLDS = [0.5, 0.75, 1.0, 1.25, 1.5, 1.75, 2.0, 2.5, 3.0, 99.0]  # 99 = no filter


def atr_ratio_signal(df, atr_short=7, atr_long=56, threshold=0.6,
                     ema_fast=20, ema_slow=80):
    atr_s = (df['high'] - df['low']).rolling(atr_short).mean()
    atr_l = (df['high'] - df['low']).rolling(atr_long).mean()
    compression = atr_s < atr_l * threshold
    ema_f = df['close'].ewm(span=ema_fast).mean()
    ema_s = df['close'].ewm(span=ema_slow).mean()
    sig = pd.Series(0, index=df.index)
    sig[compression & (ema_f > ema_s)] = 1
    sig[compression & (ema_f < ema_s)] = -1
    warmup = max(atr_long, ema_slow) + 5
    sig.iloc[:warmup] = 0
    return sig


# Satellite signal functions (copy)
def volreg_signal(df, short_vol=10, long_vol=25, threshold=0.7, ema_fast=14, ema_slow=40):
    r = df['close'].pct_change()
    s_v, l_v = r.rolling(short_vol).std(), r.rolling(long_vol).std()
    comp = s_v < l_v * threshold
    ef, es = df['close'].ewm(span=ema_fast).mean(), df['close'].ewm(span=ema_slow).mean()
    sig = pd.Series(0, index=df.index)
    sig[comp & (ef > es)] = 1
    sig[comp & (ef < es)] = -1
    return sig


def _sampen_fast(arr, m=2, r_mult=0.2, w=50):
    n = len(arr); out = np.full(n, np.nan)
    for i in range(w, n):
        win = arr[i - w:i]
        r = r_mult * np.std(win)
        if r < 1e-12:
            out[i] = 0.0; continue
        def cnt(t):
            if len(win) - t < 2: return 0
            t_p = np.lib.stride_tricks.sliding_window_view(win, t)
            c = 0
            for j in range(len(t_p)):
                d = np.max(np.abs(t_p - t_p[j]), axis=1)
                c += np.sum(d < r) - 1
            return c
        B, A = cnt(m), cnt(m + 1)
        out[i] = -np.log(A / B) if (A > 0 and B > 0) else 0.0
    return out


def sampen_signal(df, m=2, r_mult=0.2, w=50, pct=20, ef_p=20, es_p=80):
    r = df['close'].pct_change().fillna(0).values
    vals = _sampen_fast(r, m=m, r_mult=r_mult, w=w)
    s = pd.Series(vals, index=df.index)
    thr = s.expanding(min_periods=50).quantile(pct / 100.0)
    low_e = s < thr
    ef = df['close'].ewm(span=ef_p).mean()
    es = df['close'].ewm(span=es_p).mean()
    sig = pd.Series(0, index=df.index)
    sig[low_e & (ef > es)] = 1
    sig[low_e & (ef < es)] = -1
    return sig


def vol_smile_skew_signal(df, window=24, skew_threshold=1.0, trend_window=40):
    r = df['close'].pct_change().values
    up_sq = pd.Series(np.where(r > 0, r, 0.0) ** 2, index=df.index)
    dn_sq = pd.Series(np.where(r < 0, r, 0.0) ** 2, index=df.index)
    uv = up_sq.rolling(window, min_periods=window // 2).mean().apply(np.sqrt)
    dv = dn_sq.rolling(window, min_periods=window // 2).mean().apply(np.sqrt)
    sk = (uv / (dv + 1e-10)) - 1.0
    tm = df['close'].rolling(trend_window).mean()
    ut = df['close'] > tm
    dt = df['close'] < tm
    skm = sk.rolling(window * 3).mean()
    sks = sk.rolling(window * 3).std()
    z = (sk - skm) / (sks + 1e-10)
    sig = pd.Series(0, index=df.index)
    sig[(z < -skew_threshold) & ut] = 1
    sig[(z > skew_threshold) & dt] = -1
    return sig


def meme_momentum_signal(df, ema_fast=5, ema_slow=21, rsi_period=14,
                         rsi_lower=35, rsi_upper=65, vol_mult=1.3, vol_lookback=15):
    ef = df["close"].ewm(span=ema_fast, adjust=False).mean()
    es = df["close"].ewm(span=ema_slow, adjust=False).mean()
    d = df["close"].diff()
    g = d.where(d > 0, 0).ewm(span=rsi_period, adjust=False).mean()
    l = (-d.where(d < 0, 0)).ewm(span=rsi_period, adjust=False).mean()
    rs = g / l.replace(0, np.nan); rsi = 100 - 100 / (1 + rs)
    vma = df["volume"].rolling(vol_lookback, min_periods=5).mean()
    vc = df["volume"] > vma * vol_mult
    bull = (ef > es) & (ef.shift(1) <= es.shift(1))
    bear = (ef < es) & (ef.shift(1) >= es.shift(1))
    sig = pd.Series(0, index=df.index)
    sig[bull & (rsi > rsi_lower) & (rsi < rsi_upper) & vc] = 1
    sig[bear & (rsi > rsi_lower) & (rsi < rsi_upper) & vc] = -1
    regime = sig.copy(); cur = 0
    for i in range(len(regime)):
        if sig.iloc[i] != 0: cur = sig.iloc[i]
        regime.iloc[i] = cur
    return regime


def run_bt(df, sig, sym, sl=0.04, tp=0.08, mhb=24):
    cost = get_cost_params(sym, "4h")
    return run_backtest(df, sig, strategy_name="X",
                        bars_per_year=BARS_PER_YEAR, leverage=1.0,
                        stop_loss_pct=sl, take_profit_pct=tp, max_hold_bars=mhb,
                        **cost)


def eq_to_daily(eq):
    eq = np.asarray(eq, dtype=float)
    d = eq[5::6]
    if len(d) < 2: d = eq[::6]
    return np.diff(d) / np.where(d[:-1] != 0, d[:-1], 1.0)


def sharpe(r, ppy=365):
    r = np.asarray(r); r = r[np.isfinite(r)]
    if len(r) < 5 or np.std(r, ddof=1) == 0: return 0.0
    return float(np.mean(r) / np.std(r, ddof=1) * np.sqrt(ppy))


# ── Compute BTC vol_z series ────────────────────────────────────────────────

async def get_btc_volz():
    btc = await fetch_klines("BTCUSDT", "4h", DAYS)
    btc['ret'] = btc['close'].pct_change()
    btc['rv'] = btc['ret'].rolling(60).std() * np.sqrt(2190) * 100
    btc['rvm'] = btc['rv'].rolling(360).mean()
    btc['rvs'] = btc['rv'].rolling(360).std()
    btc['volz'] = (btc['rv'] - btc['rvm']) / (btc['rvs'] + 1e-10)
    return btc[['open_time', 'volz']].copy()


def apply_filter(df, sig, btc_volz_df, threshold):
    if threshold >= 50:  # "no filter"
        return sig
    btc = btc_volz_df.set_index('open_time')
    aligned = btc.reindex(df['open_time'], method='ffill')['volz'].values
    bad = pd.Series(aligned, index=sig.index).fillna(False) >= threshold
    out = sig.copy()
    out[bad] = 0
    return out


# ── Threshold scan on ATR portfolio (full 730d + 2 halves) ─────────────────

async def threshold_sensitivity(data_cache, btc_volz_df):
    print("\n=== Threshold sensitivity (ATR_Ratio × 8銘柄 portfolio) ===")
    full_results = []
    h1_results = []
    h2_results = []

    for thr in THRESHOLDS:
        daily_full = {}
        daily_h1 = {}
        daily_h2 = {}
        for s in SYMBOLS_8:
            df = data_cache[s]
            sig = atr_ratio_signal(df, **ATR_PARAMS)
            sig_f = apply_filter(df, sig, btc_volz_df, thr)
            if (sig_f != 0).sum() < 5:
                daily_full[s] = np.zeros(180); daily_h1[s] = np.zeros(90); daily_h2[s] = np.zeros(90)
                continue
            r = run_bt(df, sig_f, s)
            dr = eq_to_daily(r['equity_curve'])
            daily_full[s] = dr

            # Halves
            half = len(df) // 2
            df1 = df.iloc[:half].reset_index(drop=True)
            df2 = df.iloc[half:].reset_index(drop=True)
            sig1 = atr_ratio_signal(df1, **ATR_PARAMS)
            sig2 = atr_ratio_signal(df2, **ATR_PARAMS)
            sig1f = apply_filter(df1, sig1, btc_volz_df, thr)
            sig2f = apply_filter(df2, sig2, btc_volz_df, thr)
            if (sig1f != 0).sum() >= 3:
                r1 = run_bt(df1, sig1f, s)
                daily_h1[s] = eq_to_daily(r1['equity_curve'])
            else:
                daily_h1[s] = np.zeros(90)
            if (sig2f != 0).sum() >= 3:
                r2 = run_bt(df2, sig2f, s)
                daily_h2[s] = eq_to_daily(r2['equity_curve'])
            else:
                daily_h2[s] = np.zeros(90)

        def port_metric(dailies):
            m = min(len(v) for v in dailies.values())
            agg = pd.DataFrame({k: v[:m] for k, v in dailies.items()})
            pr = agg.mean(axis=1)
            ps = sharpe(pr.values)
            cum = (1 + pr).cumprod()
            tr = float((cum.iloc[-1] - 1) * 100)
            dd = float((cum / cum.cummax() - 1).min() * 100)
            return ps, tr, dd

        sh_f, tr_f, dd_f = port_metric(daily_full)
        sh_1, tr_1, dd_1 = port_metric(daily_h1)
        sh_2, tr_2, dd_2 = port_metric(daily_h2)

        thr_label = "off" if thr >= 50 else f"≥{thr}"
        print(f"  vol_z {thr_label:<5}  "
              f"FULL Sh={sh_f:+.2f} ret={tr_f:+.0f}% dd={dd_f:+.1f}% Calmar={abs(tr_f/dd_f) if dd_f != 0 else 0:>5.1f}  ||  "
              f"H1 Sh={sh_1:+.2f} dd={dd_1:+.1f}%  ||  "
              f"H2 Sh={sh_2:+.2f} dd={dd_2:+.1f}%")
        full_results.append({"thr": thr, "sharpe": round(sh_f, 3), "return": round(tr_f, 2), "dd": round(dd_f, 2), "calmar": round(abs(tr_f/dd_f) if dd_f != 0 else 0, 2)})
        h1_results.append({"thr": thr, "sharpe": round(sh_1, 3), "return": round(tr_1, 2), "dd": round(dd_1, 2)})
        h2_results.append({"thr": thr, "sharpe": round(sh_2, 3), "return": round(tr_2, 2), "dd": round(dd_2, 2)})

    return full_results, h1_results, h2_results


# ── Apply vol_z filter to satellite strategies ──────────────────────────────

async def satellite_filter_test(data_cache, btc_volz_df, threshold=1.5):
    print(f"\n=== Satellite strategies + vol_z≥{threshold} filter ===")

    satellite_configs = [
        ("SampEn_DOGE", "DOGEUSDT", sampen_signal, {}, {"sl": 0.04, "tp": 0.08, "mhb": 24}),
        ("SampEn_SOL",  "SOLUSDT",  sampen_signal, {}, {"sl": 0.04, "tp": 0.08, "mhb": 24}),
        ("MemeMom_BONK", "BONKUSDT", meme_momentum_signal, {"ema_fast": 5, "ema_slow": 21, "vol_mult": 1.3, "vol_lookback": 15}, {"sl": 0.05, "tp": 0.15, "mhb": 30}),
        ("MemeMom_SUI",  "SUIUSDT",  meme_momentum_signal, {"ema_fast": 5, "ema_slow": 21, "vol_mult": 1.3, "vol_lookback": 15}, {"sl": 0.05, "tp": 0.15, "mhb": 30}),
        ("MemeMom_NEAR", "NEARUSDT", meme_momentum_signal, {"ema_fast": 5, "ema_slow": 21, "vol_mult": 1.3, "vol_lookback": 15}, {"sl": 0.05, "tp": 0.15, "mhb": 30}),
        ("VSS_SUI",      "SUIUSDT",  vol_smile_skew_signal, {"window": 24, "skew_threshold": 1.0, "trend_window": 40}, {"sl": 0.02, "tp": 0.06, "mhb": 24}),
        ("VolReg_DOGE",  "DOGEUSDT", volreg_signal, {}, {"sl": 0.04, "tp": 0.06, "mhb": 24}),
    ]

    print(f"  {'Strategy':<18} {'Baseline':<24} {'+ filter':<24} {'ΔSh':>6} {'ΔDD':>7}")
    rows = []
    for label, sym, fn, params, exit_p in satellite_configs:
        if sym not in data_cache:
            data_cache[sym] = await fetch_klines(sym, "4h", DAYS)
        df = data_cache[sym]
        sig = fn(df, **params)
        # Baseline
        if (sig != 0).sum() < 5:
            print(f"  {label} NO SIGNALS"); continue
        r0 = run_bt(df, sig, sym, **exit_p)
        m0 = r0["metrics"]
        sh0 = round(float(m0.get("sharpe_ratio") or 0), 3)
        dd0 = round(float(m0.get("max_drawdown_pct") or 0), 2)
        # Filtered
        sigf = apply_filter(df, sig, btc_volz_df, threshold)
        if (sigf != 0).sum() < 5:
            print(f"  {label} filter killed signals"); continue
        rf = run_bt(df, sigf, sym, **exit_p)
        mf = rf["metrics"]
        shf = round(float(mf.get("sharpe_ratio") or 0), 3)
        ddf = round(float(mf.get("max_drawdown_pct") or 0), 2)
        d_sh = shf - sh0; d_dd = ddf - dd0
        print(f"  {label:<18} Sh={sh0:+.2f} DD={dd0:+5.1f}%  → Sh={shf:+.2f} DD={ddf:+5.1f}%  ΔSh={d_sh:+.2f} ΔDD={d_dd:+5.1f}%")
        rows.append({
            "strategy": label, "symbol": sym,
            "baseline": {"sharpe": sh0, "dd": dd0},
            "filtered": {"sharpe": shf, "dd": ddf},
            "delta": {"sharpe": round(d_sh, 3), "dd": round(d_dd, 2)},
        })
    return rows


# ── Main ─────────────────────────────────────────────────────────────────────

async def main():
    t0 = time.time()
    print("=== Wave I: Robustness & Generality of vol_z=1.5 filter ===")

    # Load data
    cache = {}
    needed = list(set(SYMBOLS_8 + ["SOLUSDT", "SUIUSDT", "NEARUSDT"]))
    print("Loading data ...")
    for s in needed:
        df = await fetch_klines(s, "4h", DAYS)
        cache[s] = df
        print(f"  {s:<10} {len(df)} bars")

    btc_vz = await get_btc_volz()
    print(f"  BTC vol_z series: {len(btc_vz)} bars")

    full, h1, h2 = await threshold_sensitivity(cache, btc_vz)

    satellites = await satellite_filter_test(cache, btc_vz, threshold=1.5)

    # Save
    out = {
        "wave": "I",
        "name": "Robustness & Generality of vol_z filter",
        "generated_at": datetime.now(timezone(timedelta(hours=9))).strftime("%Y-%m-%d %H:%M JST"),
        "threshold_sensitivity": {
            "full_730d": full,
            "first_half_365d": h1,
            "second_half_365d": h2,
        },
        "satellite_filter_test": satellites,
        "runtime_sec": round(time.time() - t0, 1),
    }
    Path("/Users/nekonaomichi/crypto-lab/wave_i_robustness.json").write_text(json.dumps(out, indent=2, default=str))
    print(f"\nSaved to wave_i_robustness.json (runtime {out['runtime_sec']}s)")


if __name__ == "__main__":
    asyncio.run(main())

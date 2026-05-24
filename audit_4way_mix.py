"""Wave K13 — §6 audit + Bootstrap CI for 4-way mix (85/15).

4-way mix:
  85% × 80/10/10 (= 68% Combined + 8.5% BONK_8H + 8.5% SHIB_8H)
  15% × vol_MR (4-symbol BTC/ETH/SOL/BNB equal-weight)

合計 = 5戦略コンポーネント:
  ATR 4H × 8 (= 0.85 * 0.40)
  FOPD 4H × 6 (= 0.85 * 0.40)
  BONK_8H (= 0.85 * 0.10)
  SHIB_8H (= 0.85 * 0.10)
  vol_MR × 4 (= 0.15)

完全§6 audit + Bootstrap CI で新ベスト判定。
"""
import asyncio
import json
import sys
import numpy as np
import pandas as pd
from pathlib import Path
from datetime import datetime, timezone, timedelta
from itertools import combinations

sys.path.insert(0, "/Users/nekonaomichi/crypto-lab")
from engine.data import fetch_klines, fetch_bybit_funding_rate, fetch_historical_metrics
from engine.backtest import run_backtest
from engine.cost_config import get_cost_params

VOL_MR_BEST = {
    "BTCUSDT":  {"vzl": -1.0, "vzh": 1.0, "tw": 10, "sl": 0.04, "tp": 0.06, "mhb": 12},
    "ETHUSDT":  {"vzl": -2.0, "vzh": 1.0, "tw": 20, "sl": 0.04, "tp": 0.06, "mhb": 12},
    "SOLUSDT":  {"vzl": -1.5, "vzh": 2.0, "tw": 10, "sl": 0.04, "tp": 0.06, "mhb": 12},
    "BNBUSDT":  {"vzl": -1.5, "vzh": 1.0, "tw": 10, "sl": 0.04, "tp": 0.06, "mhb": 12},
}
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
W_4WAY = 0.85  # 80/10/10 portion
W_VOLMR = 0.15  # vol_MR portion


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


def run_bt(df, sig, sym, interval, fee_m=1.0, slip_m=1.0, fund_m=1.0, **exit_kw):
    cost = get_cost_params(sym, interval)
    cs = dict(cost)
    if "fee_rate" in cs: cs["fee_rate"] *= fee_m
    if "slippage_rate" in cs: cs["slippage_rate"] *= slip_m
    if "forced_exit_slippage" in cs: cs["forced_exit_slippage"] *= slip_m
    if "funding_rate_8h" in cs: cs["funding_rate_8h"] *= fund_m
    bars_per_year = 2190 if interval == "4h" else 1095
    return run_backtest(df, sig, strategy_name="K13", bars_per_year=bars_per_year,
                        leverage=1.0, **exit_kw, **cs)


def _get_df(cache_entry):
    """Extract OHLCV df from possibly-dict cache entry."""
    if isinstance(cache_entry, dict):
        return cache_entry.get("ohlcv", cache_entry)
    return cache_entry


async def compute_4way_daily(cache, btc_idx_4h, btc_idx_8h, fee_m=1.0, slip_m=1.0, fund_m=1.0):
    # ATR
    daily_atr = {}
    for s in ATR_SYMBOLS:
        df = _get_df(cache[s])
        sig = atr_ratio_signal(df, **ATR_PARAMS_4H)
        aligned = btc_idx_4h.reindex(df['open_time'], method='ffill')['volz'].values
        sig[pd.Series(aligned, index=sig.index).fillna(False) >= VOL_Z] = 0
        r = run_bt(df, sig, s, "4h", fee_m, slip_m, fund_m, **EXIT_4H)
        daily_atr[s] = eq_to_daily(r['equity_curve'], 6)
    ma = min(len(v) for v in daily_atr.values())
    atr_d = pd.DataFrame({k: v[:ma] for k, v in daily_atr.items()}).mean(axis=1).values

    # FOPD
    daily_fopd = {}
    for s, p in FOPD_BEST.items():
        d = cache[s]
        sig = fopd_signal(d["ohlcv"], d["fr"], d["oi"], p["fr"], p["oi"], p["ret"])
        r = run_bt(d["ohlcv"], sig, s, "4h", fee_m, slip_m, fund_m, stop_loss_pct=p["sl"], take_profit_pct=p["tp"], max_hold_bars=p["mhb"])
        daily_fopd[s] = eq_to_daily(r['equity_curve'], 6)
    mf = min(len(v) for v in daily_fopd.values())
    fopd_d = pd.DataFrame({k: v[:mf] for k, v in daily_fopd.items()}).mean(axis=1).values

    common_4h = min(len(atr_d), len(fopd_d))
    combined = 0.5 * atr_d[:common_4h] + 0.5 * fopd_d[:common_4h]

    # 8H Meme
    bonk_8h = aggregate_4h_to_8h(_get_df(cache["BONKUSDT"]))
    shib_8h = aggregate_4h_to_8h(_get_df(cache["SHIBUSDT"]))
    def compute_8h(df_8h, sym):
        sig = atr_ratio_signal(df_8h, **ATR_PARAMS_8H)
        aligned = btc_idx_8h.reindex(df_8h['open_time'], method='ffill')['volz'].values
        sig[pd.Series(aligned, index=sig.index).fillna(False) >= VOL_Z] = 0
        r = run_bt(df_8h, sig, sym, "8h", fee_m, slip_m, fund_m, **EXIT_8H)
        return eq_to_daily(r['equity_curve'], 3)
    bonk_d = compute_8h(bonk_8h, "BONKUSDT")
    shib_d = compute_8h(shib_8h, "SHIBUSDT")

    common_triple = min(len(combined), len(bonk_d), len(shib_d))
    triple = (0.80 * combined[:common_triple] +
              0.10 * bonk_d[:common_triple] +
              0.10 * shib_d[:common_triple])

    # vol_MR portfolio
    daily_vol_mr = {}
    for sym, p in VOL_MR_BEST.items():
        df = _get_df(cache[sym])
        sig = btc_vol_mr_signal(df, vol_z_low=p["vzl"], vol_z_high=p["vzh"], trend_window=p["tw"])
        r = run_bt(df, sig, sym, "4h", fee_m, slip_m, fund_m, stop_loss_pct=p["sl"], take_profit_pct=p["tp"], max_hold_bars=p["mhb"])
        daily_vol_mr[sym] = eq_to_daily(r['equity_curve'], 6)
    n_vol = min(len(v) for v in daily_vol_mr.values())
    vol_mr = pd.DataFrame({k: v[:n_vol] for k, v in daily_vol_mr.items()}).mean(axis=1).values

    common = min(len(triple), len(vol_mr))
    four_way = W_4WAY * triple[:common] + W_VOLMR * vol_mr[:common]
    return four_way


def compute_dsr(returns, n_trials, ppy=365):
    from scipy.stats import norm
    r = np.asarray(returns); r = r[np.isfinite(r)]
    T = len(r)
    if T < 30: return {"DSR": None}
    mu = np.mean(r); sigma = np.std(r, ddof=1)
    if sigma == 0: return {"DSR": 0}
    sh_hat = (mu / sigma) * np.sqrt(ppy)
    sh_period = mu / sigma
    g3 = float(pd.Series(r).skew())
    g4 = float(pd.Series(r).kurtosis()) + 3
    if n_trials <= 1: z_thresh = 0.0
    else:
        sqrt2lnN = np.sqrt(2 * np.log(n_trials))
        z_thresh = sqrt2lnN - (0.5772156649 + np.log(4 * np.pi)) / (2 * sqrt2lnN)
    sh_thresh = z_thresh / np.sqrt(T) * np.sqrt(ppy)
    var_term = 1 - g3 * sh_period + ((g4 - 1) / 4) * (sh_period ** 2)
    if var_term <= 0: return {"DSR": None}
    dsr_z = (sh_hat - sh_thresh) * np.sqrt(T - 1) / np.sqrt(var_term)
    return {
        "DSR": round(float(norm.cdf(dsr_z)), 4),
        "Sh_hat": round(sh_hat, 3),
        "Sh_threshold": round(sh_thresh, 3),
        "pass": float(norm.cdf(dsr_z)) > 0.95,
    }


def compute_pbo(returns, n_splits=10):
    r = np.asarray(returns); r = r[np.isfinite(r)]
    chunk = len(r) // n_splits
    chunks = [r[i*chunk:(i+1)*chunk] for i in range(n_splits)]
    if len(chunks[-1]) < 5: chunks = chunks[:-1]
    half = len(chunks) // 2
    if half < 2: return {"PBO": None}
    all_idx = list(range(len(chunks)))
    inv = 0; tot = 0
    for tr in combinations(all_idx, half):
        te = tuple(i for i in all_idx if i not in tr)
        if len(te) != half: continue
        if sharpe(np.concatenate([chunks[i] for i in tr])) > 0 and sharpe(np.concatenate([chunks[i] for i in te])) <= 0:
            inv += 1
        tot += 1
    return {"PBO": round(inv / tot, 4), "pass": (inv / tot) < 0.5}


def mc_ruin(returns, levs, n_sim=10000, n_days=365, ruin_thresh=-0.50, seed=42):
    rng = np.random.RandomState(seed)
    r = np.asarray(returns); r = r[np.isfinite(r)]
    out = {}
    for lev in levs:
        ruined = 0; finals = []
        for _ in range(n_sim):
            s = rng.choice(r, size=n_days, replace=True)
            lev_r = np.clip(s * lev, -0.99, None)
            eq = np.cumprod(1 + lev_r)
            dd = (eq / np.maximum.accumulate(eq) - 1).min()
            if dd <= ruin_thresh: ruined += 1
            finals.append(eq[-1] - 1)
        out[lev] = {"ruin_prob": round(ruined / n_sim, 4),
                    "median_final_pct": round(float(np.median(finals)) * 100, 2)}
    return out


def bootstrap_sharpe_median(returns, n_boot=2000, block=20, seed=42):
    rng = np.random.RandomState(seed)
    T = len(returns); p = 1.0 / block
    boot = np.zeros(n_boot)
    for b in range(n_boot):
        idx = np.zeros(T, dtype=int)
        i = rng.randint(0, T)
        for t in range(T):
            idx[t] = i
            i = i + 1
            if i >= T: i = rng.randint(0, T)
            if rng.random() < p: i = rng.randint(0, T)
        boot[b] = sharpe(returns[idx])
    return {
        "median": round(float(np.median(boot)), 3),
        "p2.5": round(float(np.percentile(boot, 2.5)), 3),
        "p97.5": round(float(np.percentile(boot, 97.5)), 3),
    }


async def main():
    print(f"=== §6 AUDIT — 4-way mix ({int(W_4WAY*100)}/{int(W_VOLMR*100)}) ===\n")

    # Load all data
    cache = {}
    for s in set(ATR_SYMBOLS + list(FOPD_BEST.keys()) + list(VOL_MR_BEST.keys())):
        cache[s] = await fetch_klines(s, "4h", DAYS)
    # FOPD needs FR + OI
    for s in FOPD_BEST:
        try: fr = await fetch_bybit_funding_rate(s, DAYS)
        except: fr = None
        try: oi = await fetch_historical_metrics(s, DAYS)
        except: oi = None
        cache[s] = {"ohlcv": cache[s], "fr": fr, "oi": oi}

    btc = cache["BTCUSDT"] if not isinstance(cache["BTCUSDT"], dict) else cache["BTCUSDT"]["ohlcv"]
    btc = btc.copy()
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

    # G1
    print("[G1] Baseline ...")
    four_way = await compute_4way_daily(cache, btc_idx_4h, btc_idx_8h)
    sh = sharpe(four_way); eq = np.cumprod(1 + four_way)
    ret = (eq[-1] - 1) * 100; dd = (eq / np.maximum.accumulate(eq) - 1).min() * 100
    print(f"  Sh={sh:+.2f}  Return={ret:+.1f}%  DD={dd:+.1f}%  Calmar={abs(ret/dd):.2f}")

    # G2 PBO
    print("\n[G2] PBO ...")
    pbo = compute_pbo(four_way, 10)
    print(f"  PBO={pbo['PBO']}  PASS={pbo['pass']}")

    # G3 DSR
    print("\n[G3] DSR ...")
    dsr_results = {}
    for n in [100, 1000, 10000, 100000, 730000]:
        r = compute_dsr(four_way, n)
        dsr_results[str(n)] = r
        print(f"  N={n:>7}: Sh_hat={r.get('Sh_hat')}, Sh_thresh={r.get('Sh_threshold')}, DSR={r.get('DSR')}, PASS={r.get('pass')}")

    # G4 Cost stress
    print("\n[G4] Cost stress ...")
    cost_results = {}
    for name, fm, sm, fdm in [("baseline", 1.0, 1.0, 1.0), ("all +50% worst", 1.5, 1.5, 1.5), ("all -50% best", 0.5, 0.5, 0.5)]:
        tr = await compute_4way_daily(cache, btc_idx_4h, btc_idx_8h, fm, sm, fdm)
        s = sharpe(tr); e = np.cumprod(1 + tr); r2 = (e[-1] - 1) * 100; d = (e / np.maximum.accumulate(e) - 1).min() * 100
        cost_results[name] = {"sharpe": round(s, 3), "return_pct": round(float(r2), 2), "dd_pct": round(float(d), 2)}
        print(f"  {name:<20} Sh={s:+.2f}  Return={r2:+.1f}%  DD={d:+.1f}%")

    # G5 MC ruin
    print("\n[G5] MC ruin (10K sim × 365d) ...")
    mc = mc_ruin(four_way, [1, 3, 5, 10], n_sim=10000)
    for lev, m in mc.items():
        print(f"  Lev {lev}x: ruin={m['ruin_prob']:.2%}, median={m['median_final_pct']:+.0f}%")

    # G6 Bootstrap CI
    print("\n[G6] Bootstrap CI ...")
    boot = bootstrap_sharpe_median(four_way, n_boot=2000)
    print(f"  Sharpe median = {boot['median']}, 95% CI [{boot['p2.5']}, {boot['p97.5']}]")

    # Summary
    pass_summary = {
        "G1": True,
        "G2_PBO": pbo.get("pass", False),
        "G3_N100": dsr_results["100"].get("pass", False),
        "G3_N1000": dsr_results["1000"].get("pass", False),
        "G3_N10K": dsr_results["10000"].get("pass", False),
        "G3_N730K": dsr_results["730000"].get("pass", False),
        "G4_worst": cost_results["all +50% worst"]["sharpe"] > 0,
        "G5_ruin_3x": mc[3]["ruin_prob"] < 0.05,
    }
    n_pass = sum(1 for v in pass_summary.values() if v)
    n_total = len(pass_summary)
    print(f"\n=== GATE SUMMARY: {n_pass}/{n_total} ===")
    for k, v in pass_summary.items():
        print(f"  {k:<15} {'PASS' if v else 'FAIL'}")

    out = {
        "audit_target": f"4-way mix ({int(W_4WAY*100)}/{int(W_VOLMR*100)})",
        "generated_at": datetime.now(timezone(timedelta(hours=9))).strftime("%Y-%m-%d %H:%M JST"),
        "baseline": {"sharpe": round(sh, 3), "return_pct": round(ret, 2), "max_dd_pct": round(dd, 2),
                     "calmar": round(abs(ret/dd) if dd != 0 else 0, 2)},
        "G2_PBO": pbo, "G3_DSR": dsr_results, "G4_cost": cost_results, "G5_MC_ruin": mc,
        "G6_bootstrap_CI": boot,
        "pass_summary": pass_summary, "n_pass": n_pass, "n_total": n_total,
    }
    Path("/Users/nekonaomichi/crypto-lab/audit_4way_mix.json").write_text(json.dumps(out, indent=2, default=str))
    print("\nSaved.")


if __name__ == "__main__":
    asyncio.run(main())

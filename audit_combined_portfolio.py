"""§6 Audit — Combined portfolio (50% ATR + 50% FOPD).

Apply the same §6 strict gates to the new combined best.
"""
import asyncio
import json
import sys
import time
import numpy as np
import pandas as pd
from pathlib import Path
from datetime import datetime, timezone, timedelta
from itertools import combinations

sys.path.insert(0, "/Users/nekonaomichi/crypto-lab")
from engine.data import fetch_klines, fetch_bybit_funding_rate, fetch_historical_metrics
from engine.backtest import run_backtest
from engine.cost_config import get_cost_params

# Same as audit_top_portfolio.py base
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
WEIGHT_ATR = 0.5
WEIGHT_FOPD = 0.5


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


def run_bt(df, sig, sym, fee_mult=1.0, slip_mult=1.0, funding_mult=1.0,
           stop_loss_pct=0.04, take_profit_pct=0.08, max_hold_bars=24):
    cost = get_cost_params(sym, "4h")
    cs = dict(cost)
    for k in ("fee_rate", "slippage_rate", "forced_exit_slippage"):
        if k in cs: cs[k] *= (slip_mult if "slip" in k else fee_mult)
    if "funding_rate_8h" in cs: cs["funding_rate_8h"] *= funding_mult
    return run_backtest(df, sig, strategy_name="combo",
                        bars_per_year=BARS_PER_YEAR, leverage=1.0,
                        stop_loss_pct=stop_loss_pct, take_profit_pct=take_profit_pct,
                        max_hold_bars=max_hold_bars, **cs)


def eq_to_daily(eq):
    eq = np.asarray(eq, dtype=float)
    d = eq[5::6]
    if len(d) < 2: d = eq[::6]
    return np.diff(d) / np.where(d[:-1] != 0, d[:-1], 1.0)


def sharpe(r, ppy=365):
    r = np.asarray(r); r = r[np.isfinite(r)]
    if len(r) < 5 or np.std(r, ddof=1) == 0: return 0.0
    return float(np.mean(r) / np.std(r, ddof=1) * np.sqrt(ppy))


async def get_btc_volz():
    btc = await fetch_klines("BTCUSDT", "4h", DAYS)
    btc['ret'] = btc['close'].pct_change()
    btc['rv'] = btc['ret'].rolling(60).std() * np.sqrt(BARS_PER_YEAR) * 100
    btc['rvm'] = btc['rv'].rolling(360).mean()
    btc['rvs'] = btc['rv'].rolling(360).std()
    btc['volz'] = (btc['rv'] - btc['rvm']) / (btc['rvs'] + 1e-10)
    return btc


async def compute_atr_daily(atr_cache, btc_vz, fee_mult=1.0, slip_mult=1.0, funding_mult=1.0):
    daily = {}
    btc_idx = btc_vz.set_index('open_time')
    for s in ATR_SYMBOLS:
        df = atr_cache[s]
        sig = atr_ratio_signal(df, **ATR_PARAMS)
        aligned = btc_idx.reindex(df['open_time'], method='ffill')['volz'].values
        bad = pd.Series(aligned, index=sig.index).fillna(False) >= VOL_Z
        sig[bad] = 0
        r = run_bt(df, sig, s, fee_mult, slip_mult, funding_mult, **ATR_EXIT)
        daily[s] = eq_to_daily(r['equity_curve'])
    m = min(len(v) for v in daily.values())
    return pd.DataFrame({k: v[:m] for k, v in daily.items()}).mean(axis=1).values


async def compute_fopd_daily(fopd_cache, fee_mult=1.0, slip_mult=1.0, funding_mult=1.0):
    daily = {}
    for s, p in FOPD_BEST.items():
        d = fopd_cache[s]
        sig = fopd_signal(d["ohlcv"], d["fr"], d["oi"], p["fr"], p["oi"], p["ret"])
        r = run_bt(d["ohlcv"], sig, s, fee_mult, slip_mult, funding_mult,
                   stop_loss_pct=p["sl"], take_profit_pct=p["tp"], max_hold_bars=p["mhb"])
        daily[s] = eq_to_daily(r['equity_curve'])
    m = min(len(v) for v in daily.values())
    return pd.DataFrame({k: v[:m] for k, v in daily.items()}).mean(axis=1).values


def compute_dsr(returns, n_trials, ppy=365):
    from scipy.stats import norm
    r = np.asarray(returns); r = r[np.isfinite(r)]
    T = len(r)
    if T < 30: return {"DSR": None, "T": T}
    mu = np.mean(r); sigma = np.std(r, ddof=1)
    if sigma == 0: return {"DSR": 0, "Sh_hat": 0}
    sh_hat = (mu / sigma) * np.sqrt(ppy)
    sh_period = mu / sigma
    g3 = float(pd.Series(r).skew())
    g4 = float(pd.Series(r).kurtosis()) + 3
    if n_trials <= 1:
        z_threshold = 0.0
    else:
        sqrt2lnN = np.sqrt(2 * np.log(n_trials))
        z_threshold = sqrt2lnN - (0.5772156649 + np.log(4 * np.pi)) / (2 * sqrt2lnN)
    sh_thresh = z_threshold / np.sqrt(T) * np.sqrt(ppy)
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
        tr_r = np.concatenate([chunks[i] for i in tr])
        te_r = np.concatenate([chunks[i] for i in te])
        if sharpe(tr_r) > 0 and sharpe(te_r) <= 0: inv += 1
        tot += 1
    return {"PBO": round(inv / tot, 4), "n_combs": tot, "pass": (inv / tot) < 0.5}


def mc_ruin(returns, levs, n_sim=10000, n_days=365, ruin_thresh=-0.50, seed=42):
    rng = np.random.RandomState(seed)
    r = np.asarray(returns); r = r[np.isfinite(r)]
    out = {}
    for lev in levs:
        ruined = 0; finals = []; dds = []
        for _ in range(n_sim):
            s = rng.choice(r, size=n_days, replace=True)
            lev_r = np.clip(s * lev, -0.99, None)
            eq = np.cumprod(1 + lev_r)
            dd = (eq / np.maximum.accumulate(eq) - 1).min()
            if dd <= ruin_thresh: ruined += 1
            finals.append(eq[-1] - 1); dds.append(dd)
        out[lev] = {
            "ruin_prob": round(ruined / n_sim, 4),
            "median_final_pct": round(float(np.median(finals)) * 100, 2),
            "p5_final_pct": round(float(np.percentile(finals, 5)) * 100, 2),
            "p95_final_pct": round(float(np.percentile(finals, 95)) * 100, 2),
            "median_max_dd_pct": round(float(np.median(dds)) * 100, 2),
        }
    return out


async def main():
    t0 = time.time()
    print(f"=== §6 AUDIT — Combined {int(WEIGHT_ATR*100)}% ATR + {int(WEIGHT_FOPD*100)}% FOPD ===\n")

    print("Loading data ...")
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
    btc_vz = await get_btc_volz()

    # G1: Baseline combined daily returns
    print("\n[G1] Baseline portfolio ...")
    atr_d = await compute_atr_daily(atr_cache, btc_vz)
    fopd_d = await compute_fopd_daily(fopd_cache)
    common = min(len(atr_d), len(fopd_d))
    combo_d = WEIGHT_ATR * atr_d[:common] + WEIGHT_FOPD * fopd_d[:common]
    sh = sharpe(combo_d)
    eq = np.cumprod(1 + combo_d)
    ret = (eq[-1] - 1) * 100; dd = (eq / np.maximum.accumulate(eq) - 1).min() * 100
    print(f"  Sh={sh:+.2f}  Return={ret:+.1f}%  DD={dd:+.1f}%  Calmar={abs(ret/dd):.2f}")
    print(f"  Correlation ATR vs FOPD: {np.corrcoef(atr_d[:common], fopd_d[:common])[0,1]:+.4f}")

    # G2: PBO
    print("\n[G2] PBO ...")
    pbo = compute_pbo(combo_d, n_splits=10)
    print(f"  PBO={pbo['PBO']}, n_combs={pbo['n_combs']}, PASS={pbo['pass']}")

    # G3: DSR with various N_trials
    # Combined uses ATR's 710K + FOPD's 5817 = 716K total. But independent strategies, so eff N could be much lower.
    print("\n[G3] DSR ...")
    dsr_results = {}
    for n in [50, 100, 500, 1000, 10000, 100000, 716000]:
        r = compute_dsr(combo_d, n)
        dsr_results[str(n)] = r
        print(f"  N={n:>7}: Sh_hat={r.get('Sh_hat'):>+.2f}, Sh_thresh={r.get('Sh_threshold'):>+.2f}, DSR={r.get('DSR')}, PASS={r.get('pass')}")

    # G4: Cost stress
    print("\n[G4] Cost stress ...")
    cost_results = {}
    for name, fm, sm, fdm in [
        ("baseline (1.0x)", 1.0, 1.0, 1.0),
        ("fee +50%", 1.5, 1.0, 1.0),
        ("slip +50%", 1.0, 1.5, 1.0),
        ("funding +50%", 1.0, 1.0, 1.5),
        ("all +50% (worst)", 1.5, 1.5, 1.5),
        ("all -50% (best)", 0.5, 0.5, 0.5),
    ]:
        atr_s = await compute_atr_daily(atr_cache, btc_vz, fm, sm, fdm)
        fopd_s = await compute_fopd_daily(fopd_cache, fm, sm, fdm)
        cm = min(len(atr_s), len(fopd_s))
        cc = WEIGHT_ATR * atr_s[:cm] + WEIGHT_FOPD * fopd_s[:cm]
        s = sharpe(cc); e = np.cumprod(1 + cc); r2 = (e[-1] - 1) * 100
        d = (e / np.maximum.accumulate(e) - 1).min() * 100
        cost_results[name] = {"sharpe": round(s, 3), "return_pct": round(float(r2), 2), "dd_pct": round(float(d), 2)}
        print(f"  {name:<22} Sh={s:+.2f}  Return={r2:+.1f}%  DD={d:+.1f}%")

    # G5: MC ruin
    print("\n[G5] MC ruin probability (10K sim × 365d) ...")
    mc = mc_ruin(combo_d, [1, 2, 3, 5, 10], n_sim=10000)
    for lev, m in mc.items():
        print(f"  Lev {lev}x: ruin={m['ruin_prob']:.2%}, median={m['median_final_pct']:+.0f}%, "
              f"p5={m['p5_final_pct']:+.0f}%, p95={m['p95_final_pct']:+.0f}%, medDD={m['median_max_dd_pct']:+.1f}%")

    # Verdict
    pass_summary = {
        "G1": True,
        "G2_PBO": pbo.get("pass", False),
        "G3a_N100": dsr_results["100"].get("pass", False),
        "G3b_N1000": dsr_results["1000"].get("pass", False),
        "G3c_N10K": dsr_results["10000"].get("pass", False),
        "G3d_N716K": dsr_results["716000"].get("pass", False),
        "G4_worst_cost": cost_results["all +50% (worst)"]["sharpe"] > 0,
        "G5_ruin_3x": mc[3]["ruin_prob"] < 0.05,
    }
    n_pass = sum(1 for v in pass_summary.values() if v)
    n_total = len(pass_summary)
    print(f"\n=== GATE SUMMARY: {n_pass}/{n_total} ===")
    for k, v in pass_summary.items():
        print(f"  {k:<20} {'PASS' if v else 'FAIL'}")

    out = {
        "audit_target": f"Combined {int(WEIGHT_ATR*100)}% ATR + {int(WEIGHT_FOPD*100)}% FOPD",
        "generated_at": datetime.now(timezone(timedelta(hours=9))).strftime("%Y-%m-%d %H:%M JST"),
        "baseline": {"sharpe": round(sh, 3), "return_pct": round(ret, 2),
                     "max_dd_pct": round(dd, 2),
                     "calmar": round(abs(ret/dd) if dd != 0 else 0, 2)},
        "G2_PBO": pbo, "G3_DSR": dsr_results,
        "G4_cost_stress": cost_results, "G5_MC_ruin": mc,
        "pass_summary": pass_summary, "n_pass": n_pass, "n_total": n_total,
        "runtime_sec": round(time.time() - t0, 1),
    }
    Path("/Users/nekonaomichi/crypto-lab/audit_combined_portfolio.json").write_text(json.dumps(out, indent=2, default=str))
    print(f"\nSaved (runtime {out['runtime_sec']}s)")


if __name__ == "__main__":
    asyncio.run(main())

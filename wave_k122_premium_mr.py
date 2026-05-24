#!/usr/bin/env python3
"""
Wave K122 — Premium-Index Mean Reversion
Hypothesis (arxiv 2310.11771): perp mark-vs-index premium reverts to index when |Z|>threshold.
Pre-registered grid of 6 variants × 6 symbols, IS/OOS=70/30, walk-forward 4-fold,
permutation test n=500, block-bootstrap CI n=500, DSR N_trials=6, cost stress +/-50%.
"""
from __future__ import annotations
import glob, json, math, os, sys, time
from dataclasses import dataclass, asdict
from typing import Dict, List, Tuple, Optional
import numpy as np
import pandas as pd

# -------- Config --------
CACHE_DIR = "/Users/nekonaomichi/crypto-lab/cache"
OUT_JSON = "/Users/nekonaomichi/crypto-lab/wave_k122_premium_mr.json"
OUT_CURVES = "/Users/nekonaomichi/crypto-lab/wave_k122_curves.json"
RNG = np.random.default_rng(20260524)

BARS_PER_DAY = 6        # 4H bars
BARS_PER_YEAR = 6 * 365
COST_TAKER = 0.0004
COST_SLIPPAGE = 0.0003
COST_PER_SIDE_BASE = COST_TAKER + COST_SLIPPAGE  # 0.0007 per side
VOL_TARGET_ANN = 0.10
POS_CAP = 2.0
IS_FRAC = 0.70
MAX_HOLD_DEFAULT = 12
N_PERM = 500
N_BOOT = 500
WF_FOLDS = 4

VARIANTS = [
    {"name": "V_Z2_w28",  "z_th": 2.0,  "window": 28, "max_hold": 12, "asym": False},
    {"name": "V_Z2_w56",  "z_th": 2.0,  "window": 56, "max_hold": 12, "asym": False},
    {"name": "V_Z2_w84",  "z_th": 2.0,  "window": 84, "max_hold": 12, "asym": False},
    {"name": "V_Z25_w56", "z_th": 2.5,  "window": 56, "max_hold": 12, "asym": False},
    {"name": "V_Z15_w56", "z_th": 1.5,  "window": 56, "max_hold": 12, "asym": False},
    {"name": "V_asym_w56","z_th": 2.0,  "window": 56, "max_hold": 12, "asym": True},
]
N_TRIALS_DSR = len(VARIANTS)

# -------- Helpers --------
def annualized_sharpe(rets: np.ndarray) -> float:
    rets = np.asarray(rets, dtype=float)
    rets = rets[np.isfinite(rets)]
    if len(rets) < 5 or np.std(rets) == 0:
        return 0.0
    return float(np.mean(rets) / np.std(rets) * math.sqrt(BARS_PER_YEAR))

def max_drawdown(equity: np.ndarray) -> float:
    if len(equity) == 0:
        return 0.0
    peak = np.maximum.accumulate(equity)
    dd = (equity - peak) / np.where(peak == 0, 1, peak)
    return float(dd.min())

def dsr(observed_sr: float, n_trials: int, n_obs: int) -> float:
    """Deflated Sharpe Ratio (Bailey & Lopez de Prado), simplified."""
    if n_obs < 10 or n_trials < 1:
        return 0.0
    from math import erf, sqrt, log
    # expected max SR under H0 with n_trials
    emax = (1 - np.euler_gamma) * _ppf(1 - 1.0/n_trials) + np.euler_gamma * _ppf(1 - 1.0/(n_trials*math.e))
    # variance of SR estimator (no skew/kurt correction)
    sr_std = math.sqrt((1 + 0.5*observed_sr**2) / max(n_obs-1, 1))
    z = (observed_sr - emax * sr_std)  # rough scaling
    # convert to p-value
    p = 0.5 * (1 + erf(z / math.sqrt(2)))
    return float(p)

def _ppf(p: float) -> float:
    # inverse normal cdf approx (Beasley-Springer-Moro)
    p = max(min(p, 1-1e-9), 1e-9)
    a = [-3.969683028665376e+01, 2.209460984245205e+02, -2.759285104469687e+02,
          1.383577518672690e+02, -3.066479806614716e+01, 2.506628277459239e+00]
    b = [-5.447609879822406e+01, 1.615858368580409e+02, -1.556989798598866e+02,
          6.680131188771972e+01, -1.328068155288572e+01]
    c = [-7.784894002430293e-03, -3.223964580411365e-01, -2.400758277161838e+00,
         -2.549732539343734e+00, 4.374664141464968e+00, 2.938163982698783e+00]
    d = [7.784695709041462e-03, 3.224671290700398e-01, 2.445134137142996e+00,
         3.754408661907416e+00]
    plow = 0.02425
    phigh = 1 - plow
    if p < plow:
        q = math.sqrt(-2*math.log(p))
        return (((((c[0]*q+c[1])*q+c[2])*q+c[3])*q+c[4])*q+c[5]) / \
               ((((d[0]*q+d[1])*q+d[2])*q+d[3])*q+1)
    elif p <= phigh:
        q = p - 0.5
        r = q*q
        return (((((a[0]*r+a[1])*r+a[2])*r+a[3])*r+a[4])*r+a[5])*q / \
               (((((b[0]*r+b[1])*r+b[2])*r+b[3])*r+b[4])*r+1)
    else:
        q = math.sqrt(-2*math.log(1-p))
        return -(((((c[0]*q+c[1])*q+c[2])*q+c[3])*q+c[4])*q+c[5]) / \
                ((((d[0]*q+d[1])*q+d[2])*q+d[3])*q+1)

# -------- Data --------
def load_symbol(sym: str) -> Optional[pd.DataFrame]:
    pf = f"{CACHE_DIR}/hist_premium_{sym}_4h_730d.parquet"
    qf = f"{CACHE_DIR}/{sym}_4h_730d.parquet"
    if not (os.path.exists(pf) and os.path.exists(qf)):
        return None
    pr = pd.read_parquet(pf)
    px = pd.read_parquet(qf)
    pr = pr.rename(columns={"timestamp": "ts"})
    pr["ts"] = pd.to_datetime(pr["ts"])
    pr = pr.set_index("ts").sort_index()
    px["ts"] = pd.to_datetime(px["open_time"])
    px = px.set_index("ts").sort_index()
    df = pr[["premium_close"]].join(px[["close"]], how="inner")
    df = df.dropna()
    df["ret"] = df["close"].pct_change()
    return df.dropna()

# -------- Signal --------
def build_signal(df: pd.DataFrame, window: int, z_th: float, max_hold: int, asym: bool) -> pd.Series:
    """Return position series (lagged by 1 bar)."""
    p = df["premium_close"].values
    mu = pd.Series(p).rolling(window).mean().values
    sd = pd.Series(p).rolling(window).std().values
    z = (p - mu) / np.where(sd > 1e-12, sd, np.nan)
    pos = np.zeros(len(df))
    hold = 0
    cur = 0
    entry_sign = 0
    for i in range(len(df)):
        if not np.isfinite(z[i]):
            pos[i] = 0
            cur = 0; hold = 0; entry_sign = 0
            continue
        if cur != 0:
            hold += 1
            # exit on Z reversal or max hold
            if (entry_sign > 0 and z[i] >= 0) or (entry_sign < 0 and z[i] <= 0) or hold >= max_hold:
                cur = 0; hold = 0; entry_sign = 0
        if cur == 0:
            if z[i] > z_th:
                # premium too rich -> SHORT
                cur = -1; entry_sign = +1; hold = 0
            elif (not asym) and z[i] < -z_th:
                cur = +1; entry_sign = -1; hold = 0
        pos[i] = cur
    s = pd.Series(pos, index=df.index)
    return s.shift(1).fillna(0)

def vol_target(pos: pd.Series, ret: pd.Series, target_ann: float = VOL_TARGET_ANN,
               window: int = 56, cap: float = POS_CAP) -> pd.Series:
    realized = ret.rolling(window).std() * math.sqrt(BARS_PER_YEAR)
    scale = target_ann / realized.replace(0, np.nan)
    sized = pos * scale.shift(1)
    return sized.clip(-cap, cap).fillna(0)

def pnl_series(pos: pd.Series, ret: pd.Series, cost_per_side: float = COST_PER_SIDE_BASE) -> pd.Series:
    gross = pos * ret
    turnover = pos.diff().abs().fillna(pos.abs())
    cost = turnover * cost_per_side
    return (gross - cost).fillna(0)

# -------- Backtest one variant on one symbol --------
def backtest(df: pd.DataFrame, v: dict, cost_mult: float = 1.0) -> dict:
    pos_raw = build_signal(df, v["window"], v["z_th"], v["max_hold"], v["asym"])
    pos = vol_target(pos_raw, df["ret"])
    cps = COST_PER_SIDE_BASE * cost_mult
    p = pnl_series(pos, df["ret"], cps)
    n = len(p)
    cut = int(n * IS_FRAC)
    p_is, p_oos = p.iloc[:cut].values, p.iloc[cut:].values
    eq_is = (1 + pd.Series(p_is)).cumprod().values
    eq_oos = (1 + pd.Series(p_oos)).cumprod().values
    trades = int((pos_raw.diff().abs() > 0).sum())
    return {
        "sr_is": annualized_sharpe(p_is),
        "sr_oos": annualized_sharpe(p_oos),
        "sr_full": annualized_sharpe(p.values),
        "mdd_oos": max_drawdown(eq_oos) if len(eq_oos) else 0.0,
        "n_trades": trades,
        "n_obs": n,
        "n_oos": int(n - cut),
        "pnl": p,
        "pos": pos,
        "pos_raw": pos_raw,
        "eq_oos": eq_oos.tolist() if len(eq_oos) else [],
        "eq_is": eq_is.tolist() if len(eq_is) else [],
    }

# -------- Walk-forward --------
def walk_forward(df: pd.DataFrame, v: dict, folds: int = WF_FOLDS) -> List[float]:
    n = len(df)
    fold_size = n // (folds + 1)
    srs = []
    for k in range(folds):
        train_end = fold_size * (k + 1)
        test_end = train_end + fold_size
        if test_end > n:
            break
        sub = df.iloc[:test_end].copy()
        pos_raw = build_signal(sub, v["window"], v["z_th"], v["max_hold"], v["asym"])
        pos = vol_target(pos_raw, sub["ret"])
        p = pnl_series(pos, sub["ret"])
        srs.append(annualized_sharpe(p.iloc[train_end:test_end].values))
    return srs

# -------- Permutation test --------
def perm_pvalue(df: pd.DataFrame, v: dict, observed_sr: float, n_perm: int = N_PERM) -> float:
    p_arr = df["premium_close"].values.copy()
    rng = np.random.default_rng(42)
    wins = 0
    for _ in range(n_perm):
        sh = rng.permutation(p_arr)
        sdf = df.copy(); sdf["premium_close"] = sh
        try:
            r = backtest(sdf, v)
            if r["sr_oos"] >= observed_sr:
                wins += 1
        except Exception:
            pass
    return (wins + 1) / (n_perm + 1)

# -------- Block bootstrap CI --------
def block_bootstrap_ci(pnl: np.ndarray, n_boot: int = N_BOOT, block: int = 24) -> Tuple[float, float]:
    pnl = np.asarray(pnl)
    n = len(pnl)
    if n < block * 2:
        return (0.0, 0.0)
    rng = np.random.default_rng(7)
    srs = []
    n_blocks = n // block
    for _ in range(n_boot):
        starts = rng.integers(0, n - block, size=n_blocks)
        sample = np.concatenate([pnl[s:s+block] for s in starts])
        srs.append(annualized_sharpe(sample))
    return float(np.percentile(srs, 2.5)), float(np.percentile(srs, 97.5))

# -------- Main --------
def main():
    t0 = time.time()
    files = sorted(glob.glob(f"{CACHE_DIR}/hist_premium_*_4h_730d.parquet"))
    symbols = [os.path.basename(f).replace("hist_premium_","").replace("_4h_730d.parquet","")
               for f in files]
    print(f"Symbols available: {symbols}")
    data: Dict[str, pd.DataFrame] = {}
    for s in symbols:
        d = load_symbol(s)
        if d is None or len(d) < 200:
            print(f"  SKIP {s}: insufficient")
            continue
        data[s] = d
        print(f"  {s}: n={len(d)}, premium mean={d['premium_close'].mean():.5e}, std={d['premium_close'].std():.5e}")

    results = {"per_symbol": {}, "per_variant": {}, "portfolio": {}, "config": {
        "variants": VARIANTS, "is_frac": IS_FRAC, "cost_per_side": COST_PER_SIDE_BASE,
        "vol_target_ann": VOL_TARGET_ANN, "pos_cap": POS_CAP, "n_perm": N_PERM,
        "n_boot": N_BOOT, "wf_folds": WF_FOLDS, "symbols": list(data.keys()),
    }}
    curves = {"per_symbol": {}, "portfolio": {}}

    # --- Per-symbol backtest, all variants ---
    for sym, df in data.items():
        results["per_symbol"][sym] = {}
        curves["per_symbol"][sym] = {}
        for v in VARIANTS:
            r = backtest(df, v)
            ci = block_bootstrap_ci(r["pnl"].iloc[int(len(r["pnl"])*IS_FRAC):].values)
            r["ci_oos_low"], r["ci_oos_high"] = ci
            results["per_symbol"][sym][v["name"]] = {
                k: v_ for k, v_ in r.items()
                if k not in ("pnl", "pos", "pos_raw", "eq_oos", "eq_is")
            }
            curves["per_symbol"][sym][v["name"]] = {
                "eq_is": r["eq_is"], "eq_oos": r["eq_oos"],
            }
            print(f"  {sym} {v['name']:12s} IS={r['sr_is']:+.2f} OOS={r['sr_oos']:+.2f} "
                  f"trades={r['n_trades']:4d} MDD={r['mdd_oos']:+.2%} CI=[{ci[0]:+.2f},{ci[1]:+.2f}]")

    # --- Per-variant aggregate (equal-weight portfolio) ---
    for v in VARIANTS:
        pnls_oos = []
        pnls_full = []
        for sym, df in data.items():
            # only include if IS Sharpe > 0
            is_sr = results["per_symbol"][sym][v["name"]]["sr_is"]
            if is_sr <= 0:
                continue
            r = backtest(df, v)
            pnls_oos.append(r["pnl"].iloc[int(len(r["pnl"])*IS_FRAC):].reset_index(drop=True))
            pnls_full.append(r["pnl"].reset_index(drop=True))
        if not pnls_oos:
            results["per_variant"][v["name"]] = {"sr_oos_port": 0.0, "n_syms": 0}
            continue
        port_oos = pd.concat(pnls_oos, axis=1).mean(axis=1).values
        port_full = pd.concat(pnls_full, axis=1).mean(axis=1).values
        sr_oos = annualized_sharpe(port_oos)
        sr_full = annualized_sharpe(port_full)
        ci = block_bootstrap_ci(port_oos)
        eq_oos = (1 + pd.Series(port_oos)).cumprod().values
        mdd = max_drawdown(eq_oos)
        results["per_variant"][v["name"]] = {
            "sr_oos_port": sr_oos, "sr_full_port": sr_full,
            "ci_oos_low": ci[0], "ci_oos_high": ci[1],
            "mdd_oos": mdd, "n_syms": len(pnls_oos),
        }
        curves["portfolio"][v["name"]] = {"eq_oos": eq_oos.tolist()}
        print(f"  VAR {v['name']:12s} port OOS SR={sr_oos:+.2f} CI=[{ci[0]:+.2f},{ci[1]:+.2f}] "
              f"MDD={mdd:+.2%} n_syms={len(pnls_oos)}")

    # --- Pick best variant by portfolio OOS SR ---
    best_var = max(VARIANTS, key=lambda v: results["per_variant"][v["name"]].get("sr_oos_port", -1e9))
    print(f"\nBEST VARIANT (portfolio OOS): {best_var['name']}")

    # --- For best variant: walk-forward, permutation, DSR, cost stress ---
    best_name = best_var["name"]
    wf_per_sym = {}
    perm_per_sym = {}
    cost_stress = {}
    for sym, df in data.items():
        wf = walk_forward(df, best_var)
        wf_per_sym[sym] = wf
        observed = results["per_symbol"][sym][best_name]["sr_oos"]
        perm_p = perm_pvalue(df, best_var, observed, n_perm=N_PERM)
        perm_per_sym[sym] = perm_p
        # cost stress
        rl = backtest(df, best_var, cost_mult=0.5)
        rh = backtest(df, best_var, cost_mult=1.5)
        cost_stress[sym] = {"low_cost_sr_oos": rl["sr_oos"], "high_cost_sr_oos": rh["sr_oos"]}
        print(f"  {sym} WF folds SR={['%.2f'%x for x in wf]} perm_p={perm_p:.3f} "
              f"cost-50%={rl['sr_oos']:+.2f} cost+50%={rh['sr_oos']:+.2f}")
    results["best_variant"] = best_name
    results["walk_forward"] = wf_per_sym
    results["permutation_p"] = perm_per_sym
    results["cost_stress"] = cost_stress

    # --- DSR on portfolio best ---
    port_data = results["per_variant"][best_name]
    sr_obs = port_data.get("sr_oos_port", 0.0)
    n_oos_eff = int(np.mean([data[s].shape[0]*(1-IS_FRAC) for s in data]))
    dsr_p = dsr(sr_obs, N_TRIALS_DSR, n_oos_eff)
    results["dsr_portfolio"] = {"sr_observed": sr_obs, "n_trials": N_TRIALS_DSR,
                                 "n_obs": n_oos_eff, "dsr_p": dsr_p}
    print(f"\nDSR(portfolio best): observed_SR={sr_obs:+.2f}, n_trials={N_TRIALS_DSR}, "
          f"n_obs={n_oos_eff}, p={dsr_p:.3f}")

    # save
    with open(OUT_JSON, "w") as f:
        json.dump(results, f, indent=2, default=str)
    with open(OUT_CURVES, "w") as f:
        json.dump(curves, f, indent=2, default=str)
    print(f"\nWrote {OUT_JSON} and {OUT_CURVES} in {time.time()-t0:.1f}s")

if __name__ == "__main__":
    main()

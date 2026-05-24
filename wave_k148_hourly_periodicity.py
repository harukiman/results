"""
Wave K148 — Hour-of-Day Periodicity (arxiv 2109.12142, R5-8)

Hypothesis:
  Crypto returns/vol exhibit periodic patterns by hour-of-day (UTC). On 4H
  bars there are six distinct hour buckets {0, 4, 8, 12, 16, 20}, broadly
  representing Asia open, mid-Asia, EU open, EU/US overlap, US open, US close.
  Some hour buckets may carry systematically positive (negative) excess
  returns; a strategy trades only those windows.

  K121 already established a weekend day-of-week edge (ACCEPT). K148 tests
  an *intraday* hour-of-day edge.

Method (pre-registered):
  1. Per symbol, log returns per 4H bar.
  2. Rolling 60-day window per hour bucket: compute mean return.
  3. Determine each bar's "expected hourly z-score" using rolling stats up to
     and INCLUDING t-1 (no look-ahead).
  4. Variants:
       V_long_best_hour     : long when bar's hour is the historical best
       V_short_worst_hour   : short when bar's hour is the historical worst
       V_combined           : long best, short worst
       V_long_only_z        : long when |z(hourly_expected)| > 1.5 and positive
  5. Vol-targeted position sizing (10% ann vol target, max 2x lev).
  6. Single 4H bar holding period.

Audits:
  - 730d, IS 70 / OOS 30
  - Per-symbol Sharpe + equal-weight portfolio of top-15 liquid
  - WF 4-fold on primary variant
  - One-sided permutation: shuffle hour-of-day labels within rolling windows
    (n=300)
  - Block bootstrap (n=300)
  - DSR with N_trials=4
  - Cost stress ±50%
"""

from __future__ import annotations

import json
import math
import os
import time
import warnings
from typing import Dict, List, Tuple

import numpy as np
import pandas as pd

warnings.filterwarnings("ignore")

CACHE = "/Users/nekonaomichi/crypto-lab/cache"
OUT_JSON = "/Users/nekonaomichi/crypto-lab/wave_k148_hourly_periodicity.json"
OUT_CURVES = "/Users/nekonaomichi/crypto-lab/wave_k148_curves.json"

# 4H bars per day = 6, 730d => ~4380 bars
BARS_PER_DAY = 6
HOURS_OF_DAY = [0, 4, 8, 12, 16, 20]
N_HOURS = len(HOURS_OF_DAY)

# Lookback for hourly stats: 60 days => 60 samples per hour bucket
HOURLY_LOOKBACK_DAYS = 60
HOURLY_LOOKBACK_SAMPLES = HOURLY_LOOKBACK_DAYS  # 60 samples per hour
VOL_LOOKBACK = 60  # 60 bars realized vol for sizing (~10 days)
TARGET_ANN_VOL = 0.10
MAX_LEV = 2.0
ANNUALIZER = BARS_PER_DAY * 365  # ~2190

IS_FRAC = 0.70

# Costs
TAKER_BPS = 4.0
SLIP_BPS = 3.0
COST_PER_SIDE = (TAKER_BPS + SLIP_BPS) / 1e4  # 0.07%


# --------- universe ----------
def discover_symbols() -> List[str]:
    syms = []
    for fn in sorted(os.listdir(CACHE)):
        if fn.endswith("_4h_730d.parquet") and fn.startswith(tuple("ABCDEFGHIJKLMNOPQRSTUVWXYZ")):
            sym_full = fn.replace("_4h_730d.parquet", "")
            if sym_full.endswith("USDT") and not sym_full.startswith("hist_premium"):
                syms.append(sym_full.replace("USDT", ""))
    return syms


SYMBOLS = discover_symbols()


def load_symbol(sym: str) -> pd.DataFrame:
    fp = f"{CACHE}/{sym}USDT_4h_730d.parquet"
    df = pd.read_parquet(fp)[["open_time", "close", "quote_volume"]].rename(
        columns={"open_time": "ts", "quote_volume": "qvol"}
    )
    df = df.sort_values("ts").reset_index(drop=True)
    df["close"] = df["close"].astype(float)
    df["qvol"] = df["qvol"].astype(float)
    df["ret_1"] = df["close"].pct_change()
    df["vol_60"] = df["ret_1"].rolling(VOL_LOOKBACK, min_periods=VOL_LOOKBACK).std() * math.sqrt(ANNUALIZER)
    df["hour"] = df["ts"].dt.hour.astype(int)
    df["weekday"] = df["ts"].dt.weekday.astype(int)
    return df


# --------- hourly expected return (no look-ahead) ----------
def compute_hourly_expected(df: pd.DataFrame) -> pd.DataFrame:
    """For each bar t, compute the rolling mean / std return of bars with the same
    hour, using only data up to (and including) bar t-1 within the last
    `HOURLY_LOOKBACK_SAMPLES` same-hour observations.

    Returns df with new columns:
       hour_mean   : rolling expected return for bar t's hour
       hour_std    : rolling std of returns for bar t's hour
       hour_z      : (hour_mean - cross_hour_mean) / cross_hour_std  (informational)
       best_hour   : hour whose hour_mean is currently the largest
       worst_hour  : hour whose hour_mean is currently the smallest
    """
    out = df.copy()
    out["hour_mean"] = np.nan
    out["hour_std"] = np.nan
    out["best_hour"] = -1
    out["worst_hour"] = -1

    # Pre-split bar indices per hour
    idx_by_hour = {h: np.where(df["hour"].values == h)[0] for h in HOURS_OF_DAY}
    rets = df["ret_1"].values

    # For each hour, compute rolling mean using shift (no look-ahead)
    rolling_mean_by_hour: Dict[int, np.ndarray] = {}
    rolling_std_by_hour: Dict[int, np.ndarray] = {}
    for h, idx in idx_by_hour.items():
        s = pd.Series(rets[idx])
        # shift(1) so bar at idx[k] sees only bars idx[:k]
        rm = s.shift(1).rolling(HOURLY_LOOKBACK_SAMPLES, min_periods=20).mean().values
        rs = s.shift(1).rolling(HOURLY_LOOKBACK_SAMPLES, min_periods=20).std().values
        rolling_mean_by_hour[h] = rm
        rolling_std_by_hour[h] = rs
        out.loc[idx, "hour_mean"] = rm
        out.loc[idx, "hour_std"] = rs

    # Now for each bar, compute best_hour / worst_hour from the most recent
    # rolling stats across all 6 hours (forward-fill rolling means to all bars).
    # We need: at bar t, look at rolling_mean_by_hour evaluated at the latest
    # index <= t for each hour, then pick argmax / argmin.
    hour_mean_matrix = pd.DataFrame(index=df.index, columns=HOURS_OF_DAY, dtype=float)
    for h, idx in idx_by_hour.items():
        s = pd.Series(rolling_mean_by_hour[h], index=idx)
        hour_mean_matrix[h] = s
    # Forward fill so every bar has the most-recent rolling mean for each hour
    hour_mean_matrix = hour_mean_matrix.ffill()

    # best/worst hour per bar
    best_idx = hour_mean_matrix.idxmax(axis=1).fillna(-1)
    worst_idx = hour_mean_matrix.idxmin(axis=1).fillna(-1)
    out["best_hour"] = best_idx.astype(int)
    out["worst_hour"] = worst_idx.astype(int)

    # cross-hour stats for z-score
    out["xh_mean"] = hour_mean_matrix.mean(axis=1)
    out["xh_std"] = hour_mean_matrix.std(axis=1)
    out["hour_z"] = (out["hour_mean"] - out["xh_mean"]) / out["xh_std"].replace(0, np.nan)

    return out


# --------- positions ----------
def vol_target_size(sig: pd.Series, vol_ann: pd.Series) -> pd.Series:
    raw = TARGET_ANN_VOL / vol_ann.replace(0, np.nan) * sig
    return raw.clip(lower=-MAX_LEV, upper=MAX_LEV).fillna(0.0)


def build_position(df: pd.DataFrame, variant: str) -> pd.Series:
    """All positions sized at OPEN of bar t (uses info up to t-1) and held
    through bar t. Cost = |pos_t - pos_{t-1}|.

    variants:
      long_best   : long when hour == best_hour
      short_worst : short when hour == worst_hour
      combined    : long best, short worst
      long_z      : long when hour_z > 1.5
    """
    vol_ann = df["vol_60"].shift(1)
    cur_hour = df["hour"].values
    best = df["best_hour"].shift(1).fillna(-1).values  # decision uses prev-bar best/worst
    worst = df["worst_hour"].shift(1).fillna(-1).values
    z = df["hour_z"].shift(1).fillna(0.0).values  # z-score evaluated for the CURRENT bar's hour using info up to t-1
    # NB: hour_z for bar t was computed using shift(1) rolling, so already no look-ahead;
    # the .shift(1) above is conservative but doesn't change the no-look-ahead property.
    # We keep .shift(1) on best/worst because those used forward-fill of the matrix.

    sig = np.zeros(len(df), dtype=float)
    if variant == "long_best":
        sig = np.where(cur_hour == best, 1.0, 0.0)
    elif variant == "short_worst":
        sig = np.where(cur_hour == worst, -1.0, 0.0)
    elif variant == "combined":
        sig = np.where(cur_hour == best, 1.0, 0.0) + np.where(cur_hour == worst, -1.0, 0.0)
    elif variant == "long_z":
        sig = np.where(z > 1.5, 1.0, 0.0)
    else:
        raise ValueError(variant)

    pos = vol_target_size(pd.Series(sig, index=df.index), vol_ann)
    return pos


def apply_costs(df: pd.DataFrame, pos: pd.Series, cost_mult: float = 1.0) -> pd.DataFrame:
    out = df.copy()
    pos = pos.fillna(0.0).astype(float)
    out["pos"] = pos
    out["gross_ret"] = pos * out["ret_1"]
    turns = (pos - pos.shift(1).fillna(0)).abs()
    out["cost"] = turns * COST_PER_SIDE * cost_mult
    out["net_ret"] = out["gross_ret"] - out["cost"]
    return out


# --------- metrics ----------
def sharpe(returns: np.ndarray, periods_per_year: float = ANNUALIZER) -> float:
    r = np.asarray(returns, dtype=float)
    r = r[~np.isnan(r)]
    if len(r) < 10 or r.std() == 0:
        return 0.0
    return float(r.mean() / r.std() * math.sqrt(periods_per_year))


def max_dd(returns: np.ndarray) -> float:
    r = np.asarray(returns, dtype=float)
    r = np.nan_to_num(r, nan=0.0)
    if len(r) == 0:
        return 0.0
    eq = (1 + r).cumprod()
    peak = np.maximum.accumulate(eq)
    return float(((eq - peak) / peak).min())


def win_rate(returns: np.ndarray) -> float:
    r = np.asarray(returns, dtype=float)
    r = r[~np.isnan(r) & (r != 0)]
    if len(r) == 0:
        return 0.0
    return float((r > 0).mean())


def t_stat(returns: np.ndarray) -> float:
    r = np.asarray(returns, dtype=float)
    r = r[~np.isnan(r) & (r != 0)]
    if len(r) < 5 or r.std() == 0:
        return 0.0
    return float(r.mean() / (r.std() / math.sqrt(len(r))))


# --------- audits ----------
def block_bootstrap_sharpe(ret: np.ndarray, block: int = 20, n: int = 300, seed: int = 7) -> Tuple[float, float]:
    rng = np.random.default_rng(seed)
    r = np.asarray(ret, dtype=float)
    r = r[~np.isnan(r)]
    if len(r) < block * 2:
        return (0.0, 0.0)
    n_blocks = max(1, len(r) // block)
    samples = []
    for _ in range(n):
        starts = rng.integers(0, len(r) - block, size=n_blocks)
        sample = np.concatenate([r[s:s + block] for s in starts])
        samples.append(sharpe(sample))
    samples = np.array(samples)
    return (float(np.percentile(samples, 5)), float(np.percentile(samples, 95)))


def permutation_test_hour(df: pd.DataFrame, base_sharpe_val: float, variant: str = "combined",
                          n: int = 300, seed: int = 42) -> Dict:
    """Null: hour-of-day label has no predictive content.

    Procedure: within each rolling 7-day window, permute the *hour labels* of
    bars and recompute the hourly_expected stats and resulting positions.
    Simpler implementation: shuffle the 'hour' assignment for the whole series
    in cyclic-coherent way: pick a random offset 0..5 and add to hour index.
    This preserves the *count* of bars per hour but randomizes which timestamps
    are claimed to be which hour. With 6 cyclic shifts the permutation is
    discrete; we therefore use a per-day random permutation of the 6 hour
    labels for that day (preserves within-day structure of vol but not the
    hour-of-day causal claim).
    """
    rng = np.random.default_rng(seed)
    n_bars = len(df)
    rets = df["ret_1"].values
    vol_ann_arr = df["vol_60"].shift(1).values

    null_sharpes = []

    for _ in range(n):
        # per-day permutation of hour labels
        sh_hour = df["hour"].values.copy()
        for d0 in range(0, n_bars, BARS_PER_DAY):
            d1 = min(d0 + BARS_PER_DAY, n_bars)
            slc = sh_hour[d0:d1]
            sh_hour[d0:d1] = rng.permutation(slc)
        # rebuild df with shuffled hour
        tmp = df.copy()
        tmp["hour"] = sh_hour
        tmp = compute_hourly_expected(tmp)
        pos = build_position(tmp, variant)
        # apply costs
        pos_v = pos.fillna(0.0).values
        turns = np.abs(np.diff(np.concatenate([[0.0], pos_v])))
        cost = turns * COST_PER_SIDE
        net = pos_v * np.nan_to_num(rets, nan=0.0) - cost
        null_sharpes.append(sharpe(net))

    null_sharpes = np.array(null_sharpes)
    p = float((null_sharpes >= base_sharpe_val).mean())
    return {
        "base_sharpe": float(base_sharpe_val),
        "null_mean": float(null_sharpes.mean()),
        "null_std": float(null_sharpes.std()),
        "p_value": p,
        "n": n,
    }


def dsr(sharpe_val: float, n_obs: int, n_trials: int) -> float:
    if n_obs < 30 or n_trials < 1:
        return float("nan")
    emc = 0.5772
    sn = math.sqrt(2 * math.log(max(n_trials, 2)))
    expected_max = sn - emc / sn
    sr_std = math.sqrt((1 + 0.5 * sharpe_val ** 2) / n_obs)
    if sr_std == 0:
        return float("nan")
    z = (sharpe_val - expected_max * sr_std) / sr_std
    from math import erf
    return float(0.5 * (1 + erf(z / math.sqrt(2))))


# --------- per-symbol pipeline ----------
def slice_metrics(out: pd.DataFrame, lo: int, hi: int) -> Dict:
    sub = out.iloc[lo:hi]
    r = sub["net_ret"].values
    pos_active = (sub["pos"] != 0)
    return {
        "sharpe": sharpe(r),
        "max_dd": max_dd(r),
        "win_rate": win_rate(r),
        "n_bars": int(len(r)),
        "exposure": float(pos_active.mean()),
        "total_return": float((1 + pd.Series(r).fillna(0)).prod() - 1),
        "mean_4h_ret_bps": float(np.nan_to_num(r, nan=0.0).mean() * 1e4),
    }


def hour_distribution_table(df: pd.DataFrame) -> Dict:
    """Per-hour empirical statistics over the WHOLE 730d window (descriptive)."""
    g = df.groupby("hour")["ret_1"]
    tbl = {}
    for h in HOURS_OF_DAY:
        s = g.get_group(h).dropna().values if h in g.groups else np.array([])
        if len(s) == 0:
            tbl[int(h)] = {"n": 0, "mean_bps": 0.0, "std_bps": 0.0, "win_rate": 0.0, "t_stat": 0.0}
            continue
        tbl[int(h)] = {
            "n": int(len(s)),
            "mean_bps": float(s.mean() * 1e4),
            "std_bps": float(s.std() * 1e4),
            "win_rate": float((s > 0).mean()),
            "t_stat": float(s.mean() / (s.std() / math.sqrt(len(s)))) if s.std() > 0 else 0.0,
        }
    return tbl


def run_symbol(sym: str) -> Tuple[Dict, Dict[str, pd.DataFrame]]:
    df = load_symbol(sym)
    df = compute_hourly_expected(df)
    n = len(df)
    cut = int(n * IS_FRAC)

    variants = ["long_best", "short_worst", "combined", "long_z"]
    out_per_variant: Dict[str, pd.DataFrame] = {}
    res = {
        "symbol": sym,
        "n_bars": int(n),
        "avg_qvol": float(df["qvol"].mean()),
        "hour_distribution": hour_distribution_table(df),
    }
    for v in variants:
        pos = build_position(df, v)
        out = apply_costs(df, pos)
        out_per_variant[v] = out
        res[v] = {
            "IS": slice_metrics(out, 0, cut),
            "OOS": slice_metrics(out, cut, n),
            "FULL": slice_metrics(out, 0, n),
        }

    # WF 4-fold on combined
    fold = n // 4
    wf = []
    for k in range(4):
        lo, hi = k * fold, (k + 1) * fold if k < 3 else n
        wf.append(slice_metrics(out_per_variant["combined"], lo, hi))
    res["walk_forward_combined"] = wf
    return res, out_per_variant


def build_portfolio(per_symbol_outs: Dict[str, pd.DataFrame]) -> pd.Series:
    frames = []
    for sym, out in per_symbol_outs.items():
        s = out["net_ret"].rename(sym).copy()
        s.index = out["ts"]
        frames.append(s)
    df = pd.concat(frames, axis=1).sort_index()
    df = df.fillna(0.0)
    return df.mean(axis=1)


def equity_curve(returns: pd.Series, downsample: int = 24) -> List[Dict]:
    eq = (1 + returns.fillna(0)).cumprod()
    return [{"ts": str(ts), "eq": float(v)} for ts, v in eq.iloc[::downsample].items()]


# --------- main ----------
def main():
    t0 = time.time()
    print("=" * 72)
    print(f"Wave K148 — Hour-of-Day Periodicity — {len(SYMBOLS)} symbols")
    print("=" * 72)

    all_results: Dict[str, Dict] = {}
    outs_by_variant: Dict[str, Dict[str, pd.DataFrame]] = {
        "long_best": {}, "short_worst": {}, "combined": {}, "long_z": {}
    }
    failed = []

    for sym in SYMBOLS:
        try:
            res, outs = run_symbol(sym)
            all_results[sym] = res
            for v, out in outs.items():
                outs_by_variant[v][sym] = out
            print(f"  {sym:8s} comb_OOS={res['combined']['OOS']['sharpe']:6.2f}  "
                  f"lb_OOS={res['long_best']['OOS']['sharpe']:6.2f}  "
                  f"sw_OOS={res['short_worst']['OOS']['sharpe']:6.2f}  "
                  f"lz_OOS={res['long_z']['OOS']['sharpe']:6.2f}")
        except Exception as e:
            failed.append((sym, str(e)))
            print(f"  {sym}: FAILED — {e}")

    # ---- choose top-15 liquid symbols for portfolio ----
    liquid_ranked = sorted(all_results.items(), key=lambda kv: kv[1]["avg_qvol"], reverse=True)
    top15 = [s for s, _ in liquid_ranked[:15]]
    print(f"\nTop-15 liquid symbols: {top15}")

    # ---- portfolio metrics ----
    portfolio_metrics = {}
    portfolio_arrs: Dict[str, np.ndarray] = {}
    portfolio_series: Dict[str, pd.Series] = {}
    n_full = max(len(outs_by_variant["combined"][s]) for s in outs_by_variant["combined"])
    cut = int(n_full * IS_FRAC)

    for v, outs in outs_by_variant.items():
        outs_15 = {s: outs[s] for s in top15 if s in outs}
        port = build_portfolio(outs_15)
        portfolio_series[v] = port
        arr = port.values
        portfolio_arrs[v] = arr
        portfolio_metrics[v] = {
            "n_symbols": len(outs_15),
            "IS_sharpe": sharpe(arr[:cut]),
            "OOS_sharpe": sharpe(arr[cut:]),
            "OOS_max_dd": max_dd(arr[cut:]),
            "OOS_win_rate": win_rate(arr[cut:]),
            "FULL_sharpe": sharpe(arr),
            "FULL_total_return": float((1 + pd.Series(arr).fillna(0)).prod() - 1),
        }

    primary_v = "combined"
    primary_ci = block_bootstrap_sharpe(portfolio_arrs[primary_v][cut:], block=20, n=300)
    portfolio_metrics[primary_v]["OOS_sharpe_CI95"] = primary_ci

    # Permutation test on BTC combined (heaviest single-symbol burden)
    print("\nPermutation test (BTC combined, n=300)...")
    df_btc = load_symbol("BTC")
    df_btc = compute_hourly_expected(df_btc)
    pos_btc = build_position(df_btc, "combined")
    out_btc = apply_costs(df_btc, pos_btc)
    base_sr_btc = sharpe(out_btc["net_ret"].values)
    perm_btc = permutation_test_hour(load_symbol("BTC"), base_sr_btc, "combined", n=300)
    print(f"  BTC perm: base_SR={perm_btc['base_sharpe']:.3f} null_mean={perm_btc['null_mean']:.3f} p={perm_btc['p_value']:.3f}")

    # Also DOGE
    print("Permutation test (DOGE combined, n=300)...")
    df_doge = load_symbol("DOGE")
    df_doge = compute_hourly_expected(df_doge)
    pos_doge = build_position(df_doge, "combined")
    out_doge = apply_costs(df_doge, pos_doge)
    base_sr_doge = sharpe(out_doge["net_ret"].values)
    perm_doge = permutation_test_hour(load_symbol("DOGE"), base_sr_doge, "combined", n=300)
    print(f"  DOGE perm: base_SR={perm_doge['base_sharpe']:.3f} null_mean={perm_doge['null_mean']:.3f} p={perm_doge['p_value']:.3f}")

    # DSR (N_trials=4 across variants)
    n_oos = n_full - cut
    dsr_results = {v: dsr(portfolio_metrics[v]["OOS_sharpe"], n_oos, n_trials=4) for v in portfolio_metrics}

    # Cost stress on primary
    print("Cost stress (combined)...")
    cost_stress = {}
    for mult, name in [(0.5, "low"), (1.0, "base"), (1.5, "high")]:
        outs_cs = {}
        for sym in top15:
            df = load_symbol(sym)
            df = compute_hourly_expected(df)
            pos = build_position(df, "combined")
            outs_cs[sym] = apply_costs(df, pos, cost_mult=mult)
        port_cs = build_portfolio(outs_cs)
        arr = port_cs.values
        cost_stress[name] = {
            "OOS_sharpe": sharpe(arr[cut:]),
            "OOS_max_dd": max_dd(arr[cut:]),
            "FULL_sharpe": sharpe(arr),
        }
        print(f"  {name:5s}: OOS_SR={cost_stress[name]['OOS_sharpe']:.3f}  DD={cost_stress[name]['OOS_max_dd']:.2%}")

    # ----- Hour-of-day cross-symbol summary (descriptive) -----
    # Aggregate hour-distribution across all symbols to identify systematic best/worst
    hour_agg = {h: {"mean_bps_sum": 0.0, "n_syms": 0, "n_positive_syms": 0} for h in HOURS_OF_DAY}
    for sym, res in all_results.items():
        for h, st in res["hour_distribution"].items():
            hh = int(h)
            hour_agg[hh]["mean_bps_sum"] += st["mean_bps"]
            hour_agg[hh]["n_syms"] += 1
            hour_agg[hh]["n_positive_syms"] += int(st["mean_bps"] > 0)
    hour_agg_table = []
    for h in HOURS_OF_DAY:
        a = hour_agg[h]
        avg_mean_bps = a["mean_bps_sum"] / max(a["n_syms"], 1)
        hour_agg_table.append({
            "hour_utc": h,
            "avg_mean_bps": avg_mean_bps,
            "n_positive_syms": a["n_positive_syms"],
            "n_syms": a["n_syms"],
            "pct_positive": a["n_positive_syms"] / max(a["n_syms"], 1),
        })

    # ----- §6 gates -----
    primary = portfolio_metrics[primary_v]
    gates = {
        "G1_OOS_Sharpe_gt_0.5": primary["OOS_sharpe"] > 0.5,
        "G2_OOS_MaxDD_gt_-0.30": primary["OOS_max_dd"] > -0.30,
        "G3_BlockBoot_CI95_low_gt_0": primary_ci[0] > 0,
        "G4_Perm_BTC_p_lt_0.05": perm_btc["p_value"] < 0.05,
        "G5_DSR_combined_gt_0.95": (dsr_results[primary_v] if not math.isnan(dsr_results[primary_v]) else 0) > 0.95,
        "G6_CostStress_high_OOS_sr_gt_0.3": cost_stress["high"]["OOS_sharpe"] > 0.3,
        "G7_Perm_DOGE_p_lt_0.05": perm_doge["p_value"] < 0.05,
    }
    n_pass = sum(gates.values())
    verdict = "ACCEPT" if n_pass >= 6 else "CONDITIONAL" if n_pass >= 4 else "REJECT"

    # save curves
    curves = {v: equity_curve(portfolio_series[v]) for v in portfolio_series}
    with open(OUT_CURVES, "w") as f:
        json.dump(curves, f, indent=2)

    # Replication-style table: each symbol's best/worst hour at end of sample
    best_worst_table = []
    for sym, res in all_results.items():
        outs_combined = outs_by_variant["combined"].get(sym)
        if outs_combined is None or "best_hour" not in outs_combined.columns:
            continue
        last_bh = int(outs_combined["best_hour"].dropna().iloc[-1]) if len(outs_combined["best_hour"].dropna()) else -1
        last_wh = int(outs_combined["worst_hour"].dropna().iloc[-1]) if len(outs_combined["worst_hour"].dropna()) else -1
        best_worst_table.append({"symbol": sym, "best_hour_end": last_bh, "worst_hour_end": last_wh})

    # Count consistency: how many syms had best hour in 12-20 UTC (US session)
    us_hours = {12, 16, 20}
    asia_hours = {0, 4, 8}
    n_us_best = sum(1 for r in best_worst_table if r["best_hour_end"] in us_hours)
    n_asia_best = sum(1 for r in best_worst_table if r["best_hour_end"] in asia_hours)
    n_us_worst = sum(1 for r in best_worst_table if r["worst_hour_end"] in us_hours)
    n_asia_worst = sum(1 for r in best_worst_table if r["worst_hour_end"] in asia_hours)

    result = {
        "wave": "K148",
        "title": "Hour-of-Day Periodicity",
        "as_of": pd.Timestamp.utcnow().isoformat(),
        "n_symbols": len(SYMBOLS),
        "symbols": list(all_results.keys()),
        "top15_liquid": top15,
        "failed": failed,
        "params": {
            "hourly_lookback_days": HOURLY_LOOKBACK_DAYS,
            "vol_lookback_bars": VOL_LOOKBACK,
            "target_ann_vol": TARGET_ANN_VOL,
            "max_lev": MAX_LEV,
            "taker_bps": TAKER_BPS,
            "slip_bps": SLIP_BPS,
        },
        "per_symbol": all_results,
        "portfolio": portfolio_metrics,
        "permutation_test_BTC": perm_btc,
        "permutation_test_DOGE": perm_doge,
        "DSR": dsr_results,
        "cost_stress": cost_stress,
        "hour_aggregate_table": hour_agg_table,
        "best_worst_hour_end_table": best_worst_table,
        "best_hour_session_counts": {
            "us_hours_(12,16,20)": n_us_best,
            "asia_hours_(0,4,8)": n_asia_best,
        },
        "worst_hour_session_counts": {
            "us_hours_(12,16,20)": n_us_worst,
            "asia_hours_(0,4,8)": n_asia_worst,
        },
        "gates": gates,
        "n_gates_pass": n_pass,
        "verdict": verdict,
        "elapsed_sec": time.time() - t0,
    }
    with open(OUT_JSON, "w") as f:
        json.dump(result, f, indent=2, default=str)

    print()
    print("=" * 72)
    print("PORTFOLIO METRICS (top-15 liquid)")
    for v in ["long_best", "short_worst", "combined", "long_z"]:
        m = portfolio_metrics[v]
        print(f"  {v:13s}  IS_SR={m['IS_sharpe']:6.2f}  OOS_SR={m['OOS_sharpe']:6.2f}  "
              f"OOS_DD={m['OOS_max_dd']:6.2%}  FULL_SR={m['FULL_sharpe']:6.2f}  "
              f"totRet={m['FULL_total_return']*100:6.2f}%")
    print(f"\ncombined OOS CI95: [{primary_ci[0]:.3f}, {primary_ci[1]:.3f}]")
    print(f"\nHour-of-day aggregate avg mean bps (across all syms):")
    for row in hour_agg_table:
        print(f"  H={row['hour_utc']:02d} UTC  avg_mean_bps={row['avg_mean_bps']:+6.2f}  "
              f"%positive_syms={row['pct_positive']*100:5.1f}% ({row['n_positive_syms']}/{row['n_syms']})")
    print(f"\nBest-hour bucket counts: US(12,16,20)={n_us_best}  Asia(0,4,8)={n_asia_best}")
    print(f"Worst-hour bucket counts: US(12,16,20)={n_us_worst}  Asia(0,4,8)={n_asia_worst}")
    print()
    print("GATES:")
    for k, v in gates.items():
        print(f"  {k}: {'PASS' if v else 'FAIL'}")
    print(f"\nVERDICT: {verdict} ({n_pass}/{len(gates)} gates pass)")
    print(f"Elapsed: {time.time() - t0:.1f}s")


if __name__ == "__main__":
    main()

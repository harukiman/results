"""
Wave K121 — Weekend Momentum Differential (ACR Journal 2026)

Hypothesis (tip-scraper R3 TOP2):
  "The Weekend Effect in Crypto Momentum"
  - 7-day price momentum sign → trading signal
  - BUT only trade on Saturday/Sunday (UTC weekday >= 5)
  - Paper claims: weekend daily-Sharpe ≈ 2x weekday
    (alt 0.070 vs 0.035; major 0.069 vs 0.037)
  - DOGE: weekend 0.0052 vs weekday 0.0021 (t-stat 3.78)
  - Mechanism: institutional volume drops on weekends → retail momentum dominates

Variants (pre-registered, limited to 4):
  V_weekend_long       : weekend-only, long & short by mom sign
  V_weekday_baseline   : weekday-only (negative control)
  V_full_week          : no filter
  V_weekend_long_only  : weekend-only but skip negative-mom

Hold = 1 bar (4H), re-evaluated each bar. Vol-targeted position sizing.
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
OUT_JSON = "/Users/nekonaomichi/crypto-lab/wave_k121_weekend_mom.json"
OUT_CURVES = "/Users/nekonaomichi/crypto-lab/wave_k121_curves.json"

# --------- universe (all 4h_730d parquets, excluding hist_premium and fr files) ----------
def discover_symbols() -> List[str]:
    syms = []
    for fn in sorted(os.listdir(CACHE)):
        if fn.endswith("_4h_730d.parquet") and fn.startswith(tuple("ABCDEFGHIJKLMNOPQRSTUVWXYZ")):
            sym_full = fn.replace("_4h_730d.parquet", "")
            if sym_full.endswith("USDT"):
                syms.append(sym_full.replace("USDT", ""))
    return syms


SYMBOLS = discover_symbols()

# 4H bars per day = 6 ; 7 days = 42 bars (momentum lookback)
BARS_PER_DAY = 6
MOM_LOOKBACK = 42      # 7 days
VOL_LOOKBACK = 60      # 60 bars realized vol for sizing (~10 days)
TARGET_ANN_VOL = 0.10  # 10% annualized
MAX_LEV = 2.0          # cap |position|
ANNUALIZER = BARS_PER_DAY * 365  # for Sharpe

IS_FRAC = 0.70

# Costs
TAKER_BPS = 4.0  # 0.04% per side
SLIP_BPS = 3.0   # 0.03% slippage per side
COST_PER_SIDE = (TAKER_BPS + SLIP_BPS) / 1e4  # 0.07%


# --------- data ----------
def load_symbol(sym: str) -> pd.DataFrame:
    fp = f"{CACHE}/{sym}USDT_4h_730d.parquet"
    px = pd.read_parquet(fp)[["open_time", "close"]].rename(columns={"open_time": "ts"})
    px = px.sort_values("ts").reset_index(drop=True)
    px["close"] = px["close"].astype(float)
    px["ret_1"] = px["close"].pct_change()
    # 7d log momentum
    px["mom_7d"] = np.log(px["close"] / px["close"].shift(MOM_LOOKBACK))
    # Realized vol on bar returns (annualized for sizing)
    px["vol_60"] = px["ret_1"].rolling(VOL_LOOKBACK, min_periods=VOL_LOOKBACK).std() * math.sqrt(ANNUALIZER)
    # Weekday (UTC). Pandas weekday: Mon=0 ... Sun=6
    px["weekday"] = px["ts"].dt.weekday
    px["is_weekend"] = (px["weekday"] >= 5).astype(int)
    return px


# --------- signal/positioning ----------
def vol_target_size(sig: pd.Series, vol_ann: pd.Series) -> pd.Series:
    """Vol-targeted position: TARGET_ANN_VOL / vol_ann * sign, capped at ±MAX_LEV."""
    raw = TARGET_ANN_VOL / vol_ann.replace(0, np.nan) * sig
    return raw.clip(lower=-MAX_LEV, upper=MAX_LEV).fillna(0.0)


def build_position(df: pd.DataFrame, variant: str) -> pd.Series:
    """variant ∈ {weekend_ls, weekday_ls, full_ls, weekend_long}.

    Position computed at bar t open using info up to bar t-1 (no look-ahead):
      - sig_t = sign(mom_7d_{t-1})
      - vol_t = vol_60_{t-1}
      - filter: weekend_ls/weekday_ls/weekend_long use the bar's weekday
                (weekday is known from timestamp — not look-ahead)
    """
    sig_raw = np.sign(df["mom_7d"].shift(1))  # use yesterday's momentum to avoid look-ahead
    vol_ann = df["vol_60"].shift(1)

    pos = vol_target_size(sig_raw, vol_ann)

    # Long-only variant: zero out short positions
    if variant == "weekend_long":
        pos = pos.where(pos > 0, 0.0)

    # Apply weekend filter (weekday is bar.weekday — known at bar open)
    wd = df["weekday"]
    if variant == "weekend_ls" or variant == "weekend_long":
        mask = (wd >= 5)
    elif variant == "weekday_ls":
        mask = (wd < 5)
    elif variant == "full_ls":
        mask = pd.Series(True, index=df.index)
    else:
        raise ValueError(variant)

    pos = pos.where(mask, 0.0).fillna(0.0)
    return pos


def apply_costs(df: pd.DataFrame, pos: pd.Series, cost_mult: float = 1.0) -> pd.DataFrame:
    out = df.copy()
    pos = pos.fillna(0.0).astype(float)
    # pos_t held into bar t+1; pnl_{t+1} = pos_t * ret_{t+1}
    pos_held = pos.shift(0)  # pos at bar t — we said pos uses info up to t-1 already; apply to ret_t? No — convention:
    # Cleaner convention: pos[t] is sized at OPEN of bar t (using info up to t-1). Held through bar t.
    # P&L at bar t = pos[t] * ret_1[t] where ret_1[t] = close[t]/close[t-1] - 1.
    # Cost on turnover: |pos[t] - pos[t-1]| * cost_per_side
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


def daily_sharpe(returns: np.ndarray) -> float:
    """Sharpe annualized assuming returns sampled daily."""
    r = np.asarray(returns, dtype=float)
    r = r[~np.isnan(r)]
    if len(r) < 5 or r.std() == 0:
        return 0.0
    return float(r.mean() / r.std() * math.sqrt(365))


def mean_per_day_return(ret_4h: np.ndarray) -> Tuple[float, float, int]:
    """Aggregates 4H returns into daily and reports (mean, std, n_days)."""
    r = np.asarray(ret_4h, dtype=float)
    r = np.nan_to_num(r, nan=0.0)
    if len(r) < BARS_PER_DAY:
        return 0.0, 0.0, 0
    n_full_days = (len(r) // BARS_PER_DAY) * BARS_PER_DAY
    daily = (1 + pd.Series(r[:n_full_days])).groupby(np.arange(n_full_days) // BARS_PER_DAY).prod() - 1
    return float(daily.mean()), float(daily.std()), int(len(daily))


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


def t_stat_mean(returns: np.ndarray) -> float:
    """Simple t-stat: mean / (std/sqrt(N))."""
    r = np.asarray(returns, dtype=float)
    r = r[~np.isnan(r) & (r != 0)]
    if len(r) < 5 or r.std() == 0:
        return 0.0
    return float(r.mean() / (r.std() / math.sqrt(len(r))))


# --------- bootstrap / permutation / DSR ----------
def block_bootstrap_sharpe(ret: np.ndarray, block: int = 20, n: int = 500, seed: int = 7) -> Tuple[float, float]:
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


def permutation_test_weekday(df: pd.DataFrame, base_sharpe_val: float, n: int = 500, seed: int = 42) -> Dict:
    """Null hypothesis: weekend label has no special information.

    Procedure: shuffle weekday assignment within each calendar week (preserves
    the count of weekend bars but randomizes WHICH bars are tagged as weekend).
    Compute weekend_ls Sharpe each time and compare.

    Implementation: within each block of 42 bars (~7 days), randomly permute which
    bars carry weekend status (preserving the 12 weekend bars / 42).
    """
    rng = np.random.default_rng(seed)
    n_bars = len(df)
    block = MOM_LOOKBACK  # 42 bars / 7 days
    null_sharpes = []
    base_wd = df["weekday"].values
    base_isw = (base_wd >= 5).astype(int)

    # Precompute base signal (uses only mom_7d shift(1) and vol_60 shift(1))
    sig_raw = np.sign(df["mom_7d"].shift(1)).values
    vol_ann = df["vol_60"].shift(1).values
    raw_pos = np.where(vol_ann > 0, TARGET_ANN_VOL / np.where(vol_ann > 0, vol_ann, np.nan) * sig_raw, 0.0)
    raw_pos = np.clip(raw_pos, -MAX_LEV, MAX_LEV)
    raw_pos = np.nan_to_num(raw_pos, nan=0.0)
    ret_1 = df["ret_1"].fillna(0.0).values

    for _ in range(n):
        # Build a shuffled is_weekend mask
        sh_isw = np.zeros(n_bars, dtype=int)
        for start in range(0, n_bars, block):
            end = min(start + block, n_bars)
            sub = base_isw[start:end]
            sh_isw[start:end] = rng.permutation(sub)
        pos = raw_pos * sh_isw
        # apply costs
        turns = np.abs(np.diff(np.concatenate([[0.0], pos])))
        cost = turns * COST_PER_SIDE
        net = pos * ret_1 - cost
        null_sharpes.append(sharpe(net))
    null_sharpes = np.array(null_sharpes)
    p = float((null_sharpes >= base_sharpe_val).mean())
    return {
        "base_sharpe": float(base_sharpe_val),
        "null_mean": float(null_sharpes.mean()),
        "null_std": float(null_sharpes.std()),
        "p_value": p,
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


def replication_metrics(out: pd.DataFrame, weekday: pd.Series) -> Dict:
    """Compute weekend-vs-weekday daily Sharpe and DOGE-style t-stat replication."""
    r = out["net_ret"].fillna(0.0).values
    wd = weekday.values
    is_w = (wd >= 5)
    # Per-day aggregation: group by date
    ts = out["ts"]
    daily = pd.DataFrame({"ts": ts, "r": r, "wd": wd}).copy()
    daily["date"] = daily["ts"].dt.date
    daily["is_weekend"] = daily["wd"] >= 5
    by_day = daily.groupby("date").agg(day_ret=("r", lambda x: (1 + x).prod() - 1),
                                       wd_first=("wd", "first"))
    by_day["is_weekend"] = by_day["wd_first"] >= 5

    wd_returns = by_day.loc[~by_day["is_weekend"], "day_ret"].values
    we_returns = by_day.loc[by_day["is_weekend"], "day_ret"].values

    return {
        "weekend_daily_mean": float(np.nan_to_num(we_returns.mean()) if len(we_returns) else 0.0),
        "weekday_daily_mean": float(np.nan_to_num(wd_returns.mean()) if len(wd_returns) else 0.0),
        "weekend_daily_std": float(np.nan_to_num(we_returns.std()) if len(we_returns) else 0.0),
        "weekday_daily_std": float(np.nan_to_num(wd_returns.std()) if len(wd_returns) else 0.0),
        "weekend_daily_sharpe": daily_sharpe(we_returns),
        "weekday_daily_sharpe": daily_sharpe(wd_returns),
        "weekend_t_stat": t_stat_mean(we_returns),
        "weekday_t_stat": t_stat_mean(wd_returns),
        "n_weekend_days": int(len(we_returns)),
        "n_weekday_days": int(len(wd_returns)),
    }


def run_symbol(sym: str) -> Dict:
    df = load_symbol(sym)
    n = len(df)
    cut = int(n * IS_FRAC)

    variants = ["weekend_ls", "weekday_ls", "full_ls", "weekend_long"]
    out_per_variant = {}
    res = {"symbol": sym, "n_bars": int(n)}

    for v in variants:
        pos = build_position(df, v)
        out = apply_costs(df, pos)
        out_per_variant[v] = out
        res[v] = {
            "IS": slice_metrics(out, 0, cut),
            "OOS": slice_metrics(out, cut, n),
            "FULL": slice_metrics(out, 0, n),
        }

    # Replication test on full-week variant (so all bars represented)
    repl = replication_metrics(out_per_variant["full_ls"], df["weekday"])
    res["replication"] = repl

    # Walk-forward 4-fold on weekend_ls
    fold_size = n // 4
    wf = []
    for k in range(4):
        lo, hi = k * fold_size, (k + 1) * fold_size if k < 3 else n
        wf.append(slice_metrics(out_per_variant["weekend_ls"], lo, hi))
    res["walk_forward_weekend_ls"] = wf

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
    print(f"Wave K121 — Weekend Momentum Differential — {len(SYMBOLS)} symbols")
    print("=" * 72)

    all_results = {}
    outs_by_variant: Dict[str, Dict[str, pd.DataFrame]] = {
        "weekend_ls": {}, "weekday_ls": {}, "full_ls": {}, "weekend_long": {}
    }
    failed = []
    for sym in SYMBOLS:
        try:
            res, outs = run_symbol(sym)
            all_results[sym] = res
            for v, out in outs.items():
                outs_by_variant[v][sym] = out
            repl = res["replication"]
            print(f"  {sym:8s} weekend_SR={res['weekend_ls']['OOS']['sharpe']:6.2f}  "
                  f"weekday_SR={res['weekday_ls']['OOS']['sharpe']:6.2f}  "
                  f"repl wkd={repl['weekday_daily_sharpe']:5.2f} we={repl['weekend_daily_sharpe']:5.2f}  "
                  f"means wkd={repl['weekday_daily_mean']*1e4:5.1f}bps we={repl['weekend_daily_mean']*1e4:5.1f}bps")
        except Exception as e:
            failed.append((sym, str(e)))
            print(f"  {sym}: FAILED — {e}")

    # ---- portfolio metrics ----
    portfolio_metrics = {}
    portfolio_arrs = {}
    portfolio_series = {}
    n_full = max(len(outs_by_variant["full_ls"][s]) for s in outs_by_variant["full_ls"])
    cut = int(n_full * IS_FRAC)

    for v, outs in outs_by_variant.items():
        port = build_portfolio(outs)
        portfolio_series[v] = port
        arr = port.values
        portfolio_arrs[v] = arr
        portfolio_metrics[v] = {
            "n_symbols": len(outs),
            "IS_sharpe": sharpe(arr[:cut]),
            "OOS_sharpe": sharpe(arr[cut:]),
            "OOS_max_dd": max_dd(arr[cut:]),
            "OOS_win_rate": win_rate(arr[cut:]),
            "FULL_sharpe": sharpe(arr),
            "FULL_total_return": float((1 + pd.Series(arr).fillna(0)).prod() - 1),
        }

    # Block bootstrap CI on OOS portfolio Sharpe for primary variant
    primary_ci = block_bootstrap_sharpe(portfolio_arrs["weekend_ls"][cut:], block=20, n=500)
    portfolio_metrics["weekend_ls"]["OOS_sharpe_CI95"] = primary_ci

    # Portfolio-level replication test
    print()
    print("Portfolio replication test (full_ls bars classified by weekday)...")
    # Use a synthetic 'frame' for replication on the portfolio:
    # Use the same trading variant (full_ls) and group portfolio returns by weekday.
    port_full = portfolio_series["full_ls"]
    df_port = pd.DataFrame({"ts": port_full.index, "r": port_full.values})
    df_port["wd"] = df_port["ts"].dt.weekday
    df_port["date"] = df_port["ts"].dt.date
    df_port["is_weekend"] = df_port["wd"] >= 5
    by_day_port = df_port.groupby("date").agg(day_ret=("r", lambda x: (1 + x).prod() - 1),
                                              wd_first=("wd", "first"))
    by_day_port["is_weekend"] = by_day_port["wd_first"] >= 5
    we_arr = by_day_port.loc[by_day_port["is_weekend"], "day_ret"].values
    wd_arr = by_day_port.loc[~by_day_port["is_weekend"], "day_ret"].values
    port_repl = {
        "weekend_daily_mean": float(we_arr.mean() if len(we_arr) else 0.0),
        "weekday_daily_mean": float(wd_arr.mean() if len(wd_arr) else 0.0),
        "weekend_daily_sharpe": daily_sharpe(we_arr),
        "weekday_daily_sharpe": daily_sharpe(wd_arr),
        "weekend_t_stat": t_stat_mean(we_arr),
        "weekday_t_stat": t_stat_mean(wd_arr),
        "n_weekend_days": int(len(we_arr)),
        "n_weekday_days": int(len(wd_arr)),
    }
    print(f"  portfolio weekend daily SR={port_repl['weekend_daily_sharpe']:.3f}  "
          f"weekday daily SR={port_repl['weekday_daily_sharpe']:.3f}")
    print(f"  portfolio weekend mean={port_repl['weekend_daily_mean']*1e4:.2f}bps  "
          f"weekday mean={port_repl['weekday_daily_mean']*1e4:.2f}bps")

    # Permutation test on BTC weekend_ls
    print("Permutation test (BTC weekend_ls, n=500)...")
    df_btc = load_symbol("BTC")
    pos_btc = build_position(df_btc, "weekend_ls")
    out_btc = apply_costs(df_btc, pos_btc)
    base_sr_btc = sharpe(out_btc["net_ret"].values)
    perm_btc = permutation_test_weekday(df_btc, base_sr_btc, n=500)
    print(f"  BTC perm: base SR={perm_btc['base_sharpe']:.3f} null_mean={perm_btc['null_mean']:.3f} p={perm_btc['p_value']:.3f}")

    print("Permutation test (DOGE weekend_ls, n=500)...")
    df_doge = load_symbol("DOGE")
    pos_doge = build_position(df_doge, "weekend_ls")
    out_doge = apply_costs(df_doge, pos_doge)
    base_sr_doge = sharpe(out_doge["net_ret"].values)
    perm_doge = permutation_test_weekday(df_doge, base_sr_doge, n=500)
    print(f"  DOGE perm: base SR={perm_doge['base_sharpe']:.3f} null_mean={perm_doge['null_mean']:.3f} p={perm_doge['p_value']:.3f}")

    # DSR for portfolio OOS Sharpe (N_trials=4)
    n_oos = n_full - cut
    dsr_results = {}
    for v in ["weekend_ls", "weekday_ls", "full_ls", "weekend_long"]:
        dsr_results[v] = dsr(portfolio_metrics[v]["OOS_sharpe"], n_oos, n_trials=4)

    # Cost stress ±50% on weekend_ls
    print("Cost stress (weekend_ls)...")
    cost_stress = {}
    for mult, name in [(0.5, "low"), (1.0, "base"), (1.5, "high")]:
        outs_cs = {}
        for sym in all_results.keys():
            df = load_symbol(sym)
            pos = build_position(df, "weekend_ls")
            outs_cs[sym] = apply_costs(df, pos, cost_mult=mult)
        port_cs = build_portfolio(outs_cs)
        arr = port_cs.values
        cost_stress[name] = {
            "OOS_sharpe": sharpe(arr[cut:]),
            "OOS_max_dd": max_dd(arr[cut:]),
            "FULL_sharpe": sharpe(arr),
        }
        print(f"  {name:5s}: OOS_SR={cost_stress[name]['OOS_sharpe']:.3f}  DD={cost_stress[name]['OOS_max_dd']:.2%}")

    # ----- §6 mini gates -----
    primary = portfolio_metrics["weekend_ls"]
    gates = {
        "G1_OOS_Sharpe_gt_0.5": primary["OOS_sharpe"] > 0.5,
        "G2_OOS_MaxDD_gt_-0.30": primary["OOS_max_dd"] > -0.30,
        "G3_BlockBoot_CI95_low_gt_0": primary_ci[0] > 0,
        "G4_Perm_BTC_p_lt_0.05": perm_btc["p_value"] < 0.05,
        "G5_DSR_weekend_ls_gt_0.95": (dsr_results["weekend_ls"] if not math.isnan(dsr_results["weekend_ls"]) else 0) > 0.95,
        "G6_CostStress_high_OOS_sr_gt_0.3": cost_stress["high"]["OOS_sharpe"] > 0.3,
        "G7_Weekend_beats_Weekday_replication": port_repl["weekend_daily_sharpe"] > port_repl["weekday_daily_sharpe"],
    }
    n_pass = sum(gates.values())
    verdict = "ACCEPT" if n_pass >= 6 else "CONDITIONAL" if n_pass >= 4 else "REJECT"

    # Replication summary table: per symbol, weekend vs weekday daily Sharpe
    replication_table = []
    for sym, res in all_results.items():
        r = res["replication"]
        replication_table.append({
            "symbol": sym,
            "weekend_daily_sharpe": r["weekend_daily_sharpe"],
            "weekday_daily_sharpe": r["weekday_daily_sharpe"],
            "weekend_daily_mean_bps": r["weekend_daily_mean"] * 1e4,
            "weekday_daily_mean_bps": r["weekday_daily_mean"] * 1e4,
            "weekend_t_stat": r["weekend_t_stat"],
            "weekday_t_stat": r["weekday_t_stat"],
            "n_weekend_days": r["n_weekend_days"],
            "n_weekday_days": r["n_weekday_days"],
        })
    # Count how many symbols weekend > weekday daily SR
    n_we_better = sum(1 for r in replication_table if r["weekend_daily_sharpe"] > r["weekday_daily_sharpe"])

    # Save curves
    curves = {v: equity_curve(portfolio_series[v]) for v in portfolio_series}
    with open(OUT_CURVES, "w") as f:
        json.dump(curves, f, indent=2)

    result = {
        "wave": "K121",
        "title": "Weekend Momentum Differential",
        "as_of": pd.Timestamp.utcnow().isoformat(),
        "n_symbols": len(SYMBOLS),
        "symbols": list(all_results.keys()),
        "failed": failed,
        "params": {
            "mom_lookback_bars": MOM_LOOKBACK,
            "vol_lookback_bars": VOL_LOOKBACK,
            "target_ann_vol": TARGET_ANN_VOL,
            "max_lev": MAX_LEV,
            "taker_bps": TAKER_BPS,
            "slip_bps": SLIP_BPS,
        },
        "per_symbol": all_results,
        "portfolio": portfolio_metrics,
        "portfolio_replication": port_repl,
        "replication_table": replication_table,
        "n_symbols_weekend_better": n_we_better,
        "permutation_test_BTC": perm_btc,
        "permutation_test_DOGE": perm_doge,
        "DSR": dsr_results,
        "cost_stress": cost_stress,
        "gates": gates,
        "n_gates_pass": n_pass,
        "verdict": verdict,
        "elapsed_sec": time.time() - t0,
    }
    with open(OUT_JSON, "w") as f:
        json.dump(result, f, indent=2, default=str)

    print()
    print("=" * 72)
    print("PORTFOLIO METRICS")
    for v in ["weekend_ls", "weekday_ls", "full_ls", "weekend_long"]:
        m = portfolio_metrics[v]
        print(f"  {v:14s}  IS_SR={m['IS_sharpe']:6.2f}  OOS_SR={m['OOS_sharpe']:6.2f}  "
              f"OOS_DD={m['OOS_max_dd']:6.2%}  FULL_SR={m['FULL_sharpe']:6.2f}  totRet={m['FULL_total_return']*100:6.2f}%")
    print()
    print(f"weekend_ls OOS CI95: [{primary_ci[0]:.3f}, {primary_ci[1]:.3f}]")
    print(f"Symbols where weekend > weekday daily SR: {n_we_better}/{len(replication_table)}")
    print()
    # DOGE-specific replication
    doge_repl = all_results.get("DOGE", {}).get("replication")
    if doge_repl:
        print(f"DOGE replication (paper claimed weekend mean 0.0052 vs weekday 0.0021, t-stat 3.78):")
        print(f"  weekend daily mean={doge_repl['weekend_daily_mean']:.5f}  weekday daily mean={doge_repl['weekday_daily_mean']:.5f}")
        print(f"  weekend t-stat={doge_repl['weekend_t_stat']:.2f}  weekday t-stat={doge_repl['weekday_t_stat']:.2f}")
    print()
    print("GATES:")
    for k, v in gates.items():
        print(f"  {k}: {'PASS' if v else 'FAIL'}")
    print(f"\nVERDICT: {verdict} ({n_pass}/{len(gates)} gates pass)")
    print(f"Elapsed: {time.time()-t0:.1f}s")


if __name__ == "__main__":
    main()

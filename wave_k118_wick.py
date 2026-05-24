#!/usr/bin/env python3
"""
Wave K118 — Wick Rejection Strategy (AI predictor 発見)
=========================================================

Origin
------
The AI chart predictor (chart_ai_predictor.py) tested 7 sub-rules across 200
random 4H chart cutouts at horizon +12 bars / 2 days. The `wick_rejection`
sub-rule was the only one passing 60%:
  * Overall: 61.9% accuracy on 42 fires
  * In `elevated` BTC vol_z bucket: 70.0% accuracy on 10 fires

We promote that label-level accuracy to a proper costed backtest across the
55-symbol perpetual universe and ask: does 70%/61.9% directional accuracy
actually translate into a positive-Sharpe strategy after costs?

Strategy
--------
For each symbol s and each 4H bar t (decision uses info up to bar t-1):
  1. Compute 3-bar avg wick balance using bars t-3, t-2, t-1:
        wick_score(i) = ((h[i]-max(o[i],c[i])) - (min(o[i],c[i])-l[i])) / (h[i]-l[i])
        wick_avg3     = mean(wick_score(t-1), wick_score(t-2), wick_score(t-3))
     Positive => upper wicks dominate => bearish rejection (SHORT).
     Negative => lower wicks dominate => bullish rejection (LONG).
     (Same definition as chart_ai_predictor.py; thresholds 0.25.)
  2. Compute BTC vol_z bucket using BTC realized vol (60-bar rolling std)
     standardized by 360-bar rolling mean / std of itself, with buckets:
         low      z < -0.5
         mid      -0.5 <= z < 0.5
         elevated  0.5 <= z < 1.5
         extreme   z >= 1.5
     (Same definition as build_chart_samples.py / chart_ai_predictor.py.)
  3. Variant gates:
        V_base          gate == 'elevated'
        V_no_gate       gate in {low, mid, elevated, extreme}
        V_relaxed_gate  gate in {mid, elevated, extreme}
        V_strict_gate   gate == 'extreme'
  4. Entry:
        wick_avg3 >  +0.25  AND  gate_ok  ->  SHORT
        wick_avg3 <  -0.25  AND  gate_ok  ->  LONG
        otherwise                           ->  no entry
  5. Exit: at +12 bars OR ATR-trailing stop (2x 14-bar ATR), whichever first.
  6. Position sizing: vol-targeted 10% annual per symbol; equal-weight portfolio
     with max 20 concurrent positions across symbols.
  7. Costs: 0.04% taker + 0.03% slippage per side = 0.07% one-side, applied
     to |delta_size| at each rebalance bar.

Audit (§6 mini)
---------------
  * IS 70% / OOS 30%
  * Walk-forward 4-fold anchored
  * Block bootstrap n=500 OOS Sharpe 95% CI
  * Permutation n=500: shuffle wick *sign* within bars => null Sharpe distribution
  * DSR with N_trials = 4 (the 4 variants are our trial set)
  * Cost stress: x0.5 / x1.0 / x1.5 / x2.0
"""
from __future__ import annotations

import json
import math
import os
import sys
import time
import warnings
from pathlib import Path
from typing import Dict, List, Tuple, Optional

import numpy as np
import pandas as pd

warnings.filterwarnings("ignore")

# --------------------------------------------------------------------------
# CONFIG
# --------------------------------------------------------------------------
ROOT = Path("/Users/nekonaomichi/crypto-lab")
CACHE = ROOT / "cache"
OUT_PY = ROOT / "wave_k118_wick.py"
OUT_JSON = ROOT / "wave_k118_wick.json"
OUT_CURVES = ROOT / "wave_k118_curves.json"

# Universe: all USDT 4h_730d symbols with enough history (>= 4000 bars).
# Match K116/K117-style cache filter: read everything that matches pattern,
# require enough bars, optionally cap at 55.
MIN_BARS = 4000
UNIVERSE_CAP = 55

BARS_PER_DAY = 6  # 4h bars
ANN_FACTOR = math.sqrt(365 * 6)  # ~46.79

# Costs
TAKER = 0.0004
SLIPPAGE = 0.0003
COST_PER_TURN = TAKER + SLIPPAGE  # one-side, applied to |delta size|

# Strategy params
WICK_THRESH = 0.25
HOLD_BARS = 12              # 2 days at 4H
ATR_PERIOD = 14
ATR_TRAIL_MULT = 2.0

# Sizing
TARGET_VOL_ANN = 0.10
VOL_LOOKBACK_BARS = 30
POS_CAP = 2.0
MAX_CONCURRENT = 20

# IS/OOS
IS_FRAC = 0.70

# Vol bucket (BTC)
VOL_WIN = 60           # rolling realized vol window
VOL_REF = 360          # rolling reference window for z-score

# Variants
GATE_SETS = {
    "V_base":         {"elevated"},
    "V_no_gate":      {"low", "mid", "elevated", "extreme"},
    "V_relaxed_gate": {"mid", "elevated", "extreme"},
    "V_strict_gate":  {"extreme"},
}

SEED = 42
N_BOOT = 500
N_PERM = 500


def log(msg: str):
    print(f"[K118] {msg}", flush=True)


# --------------------------------------------------------------------------
# DATA LOADING
# --------------------------------------------------------------------------
def load_one(sym: str) -> pd.DataFrame:
    fp = CACHE / f"{sym}USDT_4h_730d.parquet"
    df = pd.read_parquet(fp)
    df = df[["open_time", "open", "high", "low", "close", "volume"]].copy()
    df["open_time"] = pd.to_datetime(df["open_time"])
    df = df.sort_values("open_time").reset_index(drop=True)
    return df


def select_universe() -> List[str]:
    syms = []
    for f in sorted(os.listdir(CACHE)):
        if f.startswith("hist_"):
            continue
        if not (f.endswith("USDT_4h_730d.parquet") and "USDT_4h_730d" in f):
            continue
        sym = f.split("USDT_4h_730d.parquet")[0]
        if not sym.isalpha() or not sym.isupper():
            continue
        try:
            df = pd.read_parquet(CACHE / f, columns=["open_time"])
            if len(df) >= MIN_BARS:
                syms.append(sym)
        except Exception:
            continue
    return syms[:UNIVERSE_CAP]


# --------------------------------------------------------------------------
# CORE FEATURES
# --------------------------------------------------------------------------
def wick_score_arr(o: np.ndarray, h: np.ndarray, l: np.ndarray, c: np.ndarray) -> np.ndarray:
    """Per-bar wick asymmetry (upper - lower) / range; +ve => upper-wick dominant => bearish.
    Vectorised version of wick_score from chart_ai_predictor.py."""
    rng = h - l
    upper = h - np.maximum(o, c)
    lower = np.minimum(o, c) - l
    out = np.where(rng > 0, (upper - lower) / np.where(rng > 0, rng, 1.0), 0.0)
    return out


def wick_avg3(o: np.ndarray, h: np.ndarray, l: np.ndarray, c: np.ndarray) -> np.ndarray:
    """3-bar trailing average of wick_score using bars [t-3, t-2, t-1] for decision at t.
    Returns aligned to index t (NaN for warmup)."""
    ws = wick_score_arr(o, h, l, c)
    s = pd.Series(ws)
    # mean of t-1, t-2, t-3 == shifted by 1 then rolling 3
    return s.shift(1).rolling(3, min_periods=3).mean().to_numpy()


def compute_atr(high: np.ndarray, low: np.ndarray, close: np.ndarray, period: int = 14) -> np.ndarray:
    h = pd.Series(high); l = pd.Series(low); c = pd.Series(close)
    tr = pd.concat([(h - l).abs(),
                    (h - c.shift(1)).abs(),
                    (l - c.shift(1)).abs()], axis=1).max(axis=1)
    return tr.rolling(period, min_periods=period).mean().to_numpy()


def realized_vol_ann(close: np.ndarray, win: int = VOL_LOOKBACK_BARS) -> np.ndarray:
    r = pd.Series(close).pct_change()
    return (r.shift(1).rolling(win, min_periods=win).std() * ANN_FACTOR).to_numpy()


def btc_vol_bucket_series(btc_close: np.ndarray, win: int = VOL_WIN, ref_win: int = VOL_REF) -> np.ndarray:
    """Returns an array of strings (or 'na') aligned to bar t, using info up to t-1
    (we shift the realized vol by 1 bar so decision at t uses through t-1)."""
    r = pd.Series(btc_close).pct_change()
    rv = (r.rolling(win, min_periods=win).std() * ANN_FACTOR * 100.0).shift(1)
    rvm = rv.rolling(ref_win, min_periods=ref_win).mean()
    rvs = rv.rolling(ref_win, min_periods=ref_win).std()
    z = (rv - rvm) / rvs
    buckets = np.full(len(btc_close), "na", dtype=object)
    vals = z.to_numpy()
    for i, v in enumerate(vals):
        if np.isnan(v):
            continue
        if v < -0.5:
            buckets[i] = "low"
        elif v < 0.5:
            buckets[i] = "mid"
        elif v < 1.5:
            buckets[i] = "elevated"
        else:
            buckets[i] = "extreme"
    return buckets


# --------------------------------------------------------------------------
# BACKTEST: per-symbol position series
# --------------------------------------------------------------------------
def build_signal(
    df: pd.DataFrame,
    btc_bucket: np.ndarray,
    gate_set: set,
    wick_thresh: float = WICK_THRESH,
) -> Tuple[np.ndarray, np.ndarray, np.ndarray]:
    """
    Returns:
        pos     per-bar position in {-1, 0, +1} after applying entry/exit rules.
        entries indicator (1 at the bar an entry was opened).
        wick    the wick_avg3 series (for permutation test).
    """
    o = df["open"].to_numpy(np.float64)
    h = df["high"].to_numpy(np.float64)
    l = df["low"].to_numpy(np.float64)
    c = df["close"].to_numpy(np.float64)
    n = len(c)

    w = wick_avg3(o, h, l, c)         # decision feature at index t (NaN for first ~4 bars)
    atr = compute_atr(h, l, c, ATR_PERIOD)
    atr_lag = pd.Series(atr).shift(1).to_numpy()  # use ATR up to t-1

    # bucket is already lagged (uses through t-1)
    pos = np.zeros(n, dtype=np.float64)
    entries = np.zeros(n, dtype=np.int8)

    cur_pos = 0
    hold_left = 0
    trail = 0.0  # trailing stop level

    # entry price for trail init
    for t in range(n):
        wt = w[t]; bt = btc_bucket[t]; at = atr_lag[t]
        # close used for stop checks: previous close
        c_prev = c[t - 1] if t > 0 else c[t]
        if cur_pos != 0:
            # update trail using ATR from t-1 (do not look ahead)
            if not np.isnan(at):
                if cur_pos == 1:
                    new_trail = c_prev - ATR_TRAIL_MULT * at
                    if new_trail > trail:
                        trail = new_trail
                elif cur_pos == -1:
                    new_trail = c_prev + ATR_TRAIL_MULT * at
                    if new_trail < trail:
                        trail = new_trail
            # check exit conditions BEFORE applying position for bar t
            stop_hit = False
            if cur_pos == 1 and c_prev < trail:
                stop_hit = True
            elif cur_pos == -1 and c_prev > trail:
                stop_hit = True
            hold_left -= 1
            if stop_hit or hold_left <= 0:
                cur_pos = 0
                hold_left = 0
                trail = 0.0
        # if flat, consider new entry using info at t-1
        if cur_pos == 0:
            if not np.isnan(wt) and bt in gate_set:
                if wt > wick_thresh:
                    cur_pos = -1   # bearish rejection => SHORT
                    entries[t] = 1
                    hold_left = HOLD_BARS
                    if not np.isnan(at):
                        trail = c_prev + ATR_TRAIL_MULT * at
                    else:
                        trail = float("inf")  # never stop until time exit
                elif wt < -wick_thresh:
                    cur_pos = 1    # bullish rejection => LONG
                    entries[t] = 1
                    hold_left = HOLD_BARS
                    if not np.isnan(at):
                        trail = c_prev - ATR_TRAIL_MULT * at
                    else:
                        trail = -float("inf")
        pos[t] = float(cur_pos)
    return pos, entries, w


def vol_targeted_size(close: np.ndarray, pos: np.ndarray) -> np.ndarray:
    rv = realized_vol_ann(close)
    raw = np.where(rv > 0, TARGET_VOL_ANN / rv, 0.0)
    raw = np.where(np.isnan(raw), 0.0, raw)
    size = pos * raw
    return np.clip(size, -POS_CAP, POS_CAP)


def per_symbol_pnl(close: np.ndarray, size: np.ndarray) -> np.ndarray:
    ret = pd.Series(close).pct_change().fillna(0.0).to_numpy()
    gross = size * ret
    delta = np.abs(np.diff(size, prepend=0.0))
    cost = delta * COST_PER_TURN
    return gross - cost


# --------------------------------------------------------------------------
# PORTFOLIO with max-concurrent cap
# --------------------------------------------------------------------------
def portfolio_pnl(
    per_sym_size: Dict[str, np.ndarray],
    per_sym_close: Dict[str, np.ndarray],
    max_concurrent: int = MAX_CONCURRENT,
) -> Tuple[np.ndarray, np.ndarray]:
    """Equal-weight across symbols, capped at max_concurrent active positions
    per bar. If more than cap are active, downscale proportionally (1/k weighting
    is unfair because some symbols generated entries earlier; we use a stable
    tie-break by symbol index order ranking)."""
    syms = list(per_sym_size.keys())
    n = len(next(iter(per_sym_close.values())))
    # number of active symbols (|pos|>0) per bar
    active_mask = np.vstack([(np.abs(per_sym_size[s]) > 0).astype(np.float64)
                             for s in syms])  # (S, n)
    n_active = active_mask.sum(axis=0)
    # weight per active symbol per bar = 1 / max(n_active, max_concurrent_used)
    # if n_active <= cap, use 1/cap (so we never lever past cap=20 worth of book);
    # if n_active >  cap, accept first 'cap' (by symbol order) only.
    weight_mat = np.zeros_like(active_mask)
    # rank within each bar by symbol order
    # Use cumulative count to know which are within cap
    cum = np.cumsum(active_mask, axis=0)
    take_mask = (active_mask > 0) & (cum <= max_concurrent)
    # equal weight = 1 / cap (we always assume the maximum book size of `cap`)
    w_per = 1.0 / max_concurrent
    weight_mat = take_mask * w_per
    # build per-symbol scaled return: size[s] * close_ret[s] - cost; weight applied at bar
    port = np.zeros(n, dtype=np.float64)
    per_sym_pnl: Dict[str, np.ndarray] = {}
    for i, s in enumerate(syms):
        close = per_sym_close[s]
        ret = pd.Series(close).pct_change().fillna(0.0).to_numpy()
        size = per_sym_size[s]
        gross = size * ret
        delta = np.abs(np.diff(size, prepend=0.0))
        cost = delta * COST_PER_TURN
        full_pnl = gross - cost
        per_sym_pnl[s] = full_pnl
        # apply weight: only counted when within cap
        port += full_pnl * weight_mat[i]
    return port, n_active


# --------------------------------------------------------------------------
# METRICS
# --------------------------------------------------------------------------
def sharpe(r: np.ndarray) -> float:
    r = np.asarray(r, dtype=np.float64)
    if len(r) < 5:
        return 0.0
    sd = r.std(ddof=1)
    if sd == 0 or np.isnan(sd):
        return 0.0
    return float(r.mean() / sd * ANN_FACTOR)


def sortino(r: np.ndarray) -> float:
    r = np.asarray(r, dtype=np.float64)
    dn = r[r < 0]
    if len(dn) < 2:
        return 0.0
    sd = dn.std(ddof=1)
    if sd == 0:
        return 0.0
    return float(r.mean() / sd * ANN_FACTOR)


def max_dd(r: np.ndarray) -> float:
    eq = np.cumprod(1 + r)
    peak = np.maximum.accumulate(eq)
    dd = eq / peak - 1
    return float(dd.min()) if len(dd) else 0.0


def calmar(r: np.ndarray) -> float:
    mdd = max_dd(r)
    if mdd == 0:
        return 0.0
    ann = (1 + r.mean()) ** (365 * 6) - 1
    return float(ann / abs(mdd))


def metrics(r: np.ndarray) -> Dict[str, float]:
    if len(r) < 10:
        return dict(sharpe=0.0, sortino=0.0, max_dd=0.0, calmar=0.0, ann_ret=0.0, n=int(len(r)))
    return dict(
        sharpe=sharpe(r),
        sortino=sortino(r),
        max_dd=max_dd(r),
        calmar=calmar(r),
        ann_ret=float((1 + r.mean()) ** (365 * 6) - 1),
        n=int(len(r)),
    )


# --------------------------------------------------------------------------
# AUDIT
# --------------------------------------------------------------------------
def block_bootstrap(r: np.ndarray, n_boot: int = N_BOOT, block: int = 20, seed: int = SEED) -> Tuple[float, float, float]:
    rng = np.random.default_rng(seed)
    n = len(r)
    if n < block * 3:
        return (0.0, 0.0, 0.0)
    nblocks = max(1, n // block)
    boots = []
    for _ in range(n_boot):
        idx_starts = rng.integers(0, max(1, n - block + 1), size=nblocks)
        sample = np.concatenate([r[s:s + block] for s in idx_starts])
        boots.append(sharpe(sample))
    bs = np.array(boots)
    return float(np.percentile(bs, 2.5)), float(np.percentile(bs, 97.5)), float(np.mean(bs))


def permutation_null_sharpe(
    dfs: Dict[str, pd.DataFrame],
    btc_bucket: np.ndarray,
    gate_set: set,
    n_perm: int = N_PERM,
    seed: int = SEED,
) -> List[float]:
    """Shuffle the sign of wick_avg3 across time independently per symbol,
    re-run the backtest, collect portfolio Sharpe.
    This breaks the temporal alignment between wick sign and forward returns
    while preserving wick magnitude, sizing, ATR-trail, and the bucket gate."""
    rng = np.random.default_rng(seed)
    syms = list(dfs.keys())
    # pre-compute per-symbol arrays once
    pre = {}
    for s in syms:
        df = dfs[s]
        o = df["open"].to_numpy(np.float64); h = df["high"].to_numpy(np.float64)
        l = df["low"].to_numpy(np.float64); c = df["close"].to_numpy(np.float64)
        w = wick_avg3(o, h, l, c)
        atr_lag = pd.Series(compute_atr(h, l, c, ATR_PERIOD)).shift(1).to_numpy()
        pre[s] = dict(o=o, h=h, l=l, c=c, w=w, atr_lag=atr_lag)

    out = []
    for _ in range(n_perm):
        per_sym_size = {}
        per_sym_close = {}
        for s in syms:
            d = pre[s]
            w_perm = d["w"].copy()
            valid = ~np.isnan(w_perm)
            signs = np.where(rng.random(valid.sum()) < 0.5, -1.0, 1.0)
            w_perm[valid] = np.abs(w_perm[valid]) * signs
            pos = _signal_from_arrays(d["o"], d["h"], d["l"], d["c"], w_perm,
                                      d["atr_lag"], btc_bucket, gate_set)
            size = vol_targeted_size(d["c"], pos)
            per_sym_size[s] = size
            per_sym_close[s] = d["c"]
        port, _ = portfolio_pnl(per_sym_size, per_sym_close)
        out.append(sharpe(port))
    return out


def _signal_from_arrays(o, h, l, c, w, atr_lag, btc_bucket, gate_set,
                        wick_thresh: float = WICK_THRESH) -> np.ndarray:
    """Inline replica of build_signal but using a pre-computed (possibly shuffled) wick series."""
    n = len(c)
    pos = np.zeros(n, dtype=np.float64)
    cur_pos = 0
    hold_left = 0
    trail = 0.0
    for t in range(n):
        wt = w[t]; bt = btc_bucket[t]; at = atr_lag[t]
        c_prev = c[t - 1] if t > 0 else c[t]
        if cur_pos != 0:
            if not np.isnan(at):
                if cur_pos == 1:
                    new_trail = c_prev - ATR_TRAIL_MULT * at
                    if new_trail > trail:
                        trail = new_trail
                else:
                    new_trail = c_prev + ATR_TRAIL_MULT * at
                    if new_trail < trail:
                        trail = new_trail
            stop_hit = (cur_pos == 1 and c_prev < trail) or (cur_pos == -1 and c_prev > trail)
            hold_left -= 1
            if stop_hit or hold_left <= 0:
                cur_pos = 0
                hold_left = 0
                trail = 0.0
        if cur_pos == 0 and not np.isnan(wt) and bt in gate_set:
            if wt > wick_thresh:
                cur_pos = -1; hold_left = HOLD_BARS
                trail = c_prev + ATR_TRAIL_MULT * at if not np.isnan(at) else float("inf")
            elif wt < -wick_thresh:
                cur_pos = 1; hold_left = HOLD_BARS
                trail = c_prev - ATR_TRAIL_MULT * at if not np.isnan(at) else -float("inf")
        pos[t] = float(cur_pos)
    return pos


def deflated_sharpe(sh_obs: float, sh_trials: List[float], n_eff: int) -> float:
    """Bailey/Lopez de Prado DSR — simplified gaussian."""
    from scipy.stats import norm
    sh_trials = np.asarray(sh_trials, dtype=np.float64)
    if len(sh_trials) < 2:
        return float("nan")
    var_sh = float(np.var(sh_trials, ddof=1))
    sd_sh = math.sqrt(max(var_sh, 1e-12))
    N = len(sh_trials)
    gamma = 0.5772156649
    e_max = sh_trials.mean() + sd_sh * (
        (1 - gamma) * math.sqrt(2 * math.log(max(N, 2))) +
        gamma * (1 / math.sqrt(2 * math.log(max(N, 2))))
    )
    z = (sh_obs - e_max) * math.sqrt(max(n_eff - 1, 1))
    return float(norm.cdf(z))


# --------------------------------------------------------------------------
# WALK-FORWARD
# --------------------------------------------------------------------------
def walk_forward(per_var_port: Dict[str, np.ndarray], n_bars: int) -> List[Dict]:
    """4-fold anchored WF: pick variant with best train Sharpe, evaluate on test slice."""
    out = []
    for k in range(4):
        train_end = max(int(0.4 * n_bars), (k + 1) * (n_bars // 5))
        test_lo = train_end
        test_hi = min(n_bars, test_lo + (n_bars // 5))
        if test_hi - test_lo < 50:
            continue
        best = None
        best_sh = -1e9
        for v, p in per_var_port.items():
            sh = sharpe(p[:train_end])
            if sh > best_sh:
                best_sh = sh; best = v
        test_sh = sharpe(per_var_port[best][test_lo:test_hi])
        out.append(dict(fold=k, train_end=int(train_end),
                        test_lo=int(test_lo), test_hi=int(test_hi),
                        best_variant=best, train_sharpe=float(best_sh),
                        test_sharpe=float(test_sh)))
    return out


# --------------------------------------------------------------------------
# MAIN
# --------------------------------------------------------------------------
def main():
    t0 = time.time()
    log("loading universe ...")
    syms = select_universe()
    log(f"universe size: {len(syms)}")
    if "BTC" not in syms:
        # ensure BTC for vol bucket
        log("BTC missing from filtered universe — including explicitly")
        syms = ["BTC"] + [s for s in syms if s != "BTC"]
        syms = syms[:UNIVERSE_CAP]
    dfs: Dict[str, pd.DataFrame] = {}
    for s in syms:
        try:
            dfs[s] = load_one(s)
        except Exception as e:
            log(f"  skip {s}: {e}")
    log(f"loaded {len(dfs)} symbols")

    # Align timelines by intersection of open_time. Use BTC's index as the spine.
    btc = dfs["BTC"]
    spine = btc["open_time"].to_numpy()
    aligned: Dict[str, pd.DataFrame] = {}
    for s, df in dfs.items():
        m = df.merge(pd.DataFrame({"open_time": spine}), on="open_time", how="right")
        # forward-fill last close so vol-bucket math is stable; mark entries with NaN
        # but for trading we just drop bars where data is missing.
        m = m.sort_values("open_time").reset_index(drop=True)
        aligned[s] = m
    n_bars = len(spine)
    is_end = int(n_bars * IS_FRAC)
    log(f"aligned n_bars={n_bars}, IS[0:{is_end}] OOS[{is_end}:{n_bars}]")

    # BTC vol bucket (computed once using BTC close)
    btc_close_full = aligned["BTC"]["close"].to_numpy(np.float64)
    btc_bucket = btc_vol_bucket_series(btc_close_full)

    # Diagnostic: bucket distribution
    from collections import Counter
    bucket_dist = Counter(btc_bucket.tolist())
    log(f"BTC vol bucket distribution (full): {dict(bucket_dist)}")

    # ------------------- run each variant -----------------------
    per_variant_results = {}
    per_variant_port = {}
    per_variant_per_sym_pnl = {}
    per_variant_per_sym_size = {}
    per_variant_per_sym_entries = {}

    for vname, gset in GATE_SETS.items():
        log(f"variant {vname} (gates={sorted(gset)}) ...")
        per_sym_size = {}
        per_sym_close = {}
        per_sym_pnl_arr = {}
        per_sym_entries_arr = {}
        per_sym_n_entries = {}
        per_sym_n_bars_active = {}
        for s in syms:
            df = aligned[s]
            close = df["close"].to_numpy(np.float64)
            # if any of the trading bars have NaN in OHLC, skip those entries
            # (build_signal handles NaN via wick=NaN which gates entry)
            if df["close"].isna().all():
                continue
            pos, entries, _ = build_signal(df, btc_bucket, gset)
            size = vol_targeted_size(close, pos)
            per_sym_size[s] = size
            per_sym_close[s] = close
            per_sym_pnl_arr[s] = per_symbol_pnl(close, size)
            per_sym_entries_arr[s] = entries
            per_sym_n_entries[s] = int(entries.sum())
            per_sym_n_bars_active[s] = int((np.abs(pos) > 0).sum())

        port, n_active = portfolio_pnl(per_sym_size, per_sym_close)
        per_variant_port[vname] = port
        per_variant_per_sym_pnl[vname] = per_sym_pnl_arr
        per_variant_per_sym_size[vname] = per_sym_size
        per_variant_per_sym_entries[vname] = per_sym_entries_arr

        # per-symbol metrics for this variant
        per_sym_metrics = {}
        per_sym_summary = {}
        for s in syms:
            if s not in per_sym_pnl_arr:
                continue
            psm = metrics(per_sym_pnl_arr[s])
            psm["n_entries"] = per_sym_n_entries[s]
            psm["n_bars_active"] = per_sym_n_bars_active[s]
            per_sym_metrics[s] = psm
            # per-trade win rate / avg PnL using entry boundaries
            psp = per_sym_pnl_arr[s]
            ent = per_sym_entries_arr[s]
            # crude trade aggregation: from each entry bar to next entry or end-of-pos
            sizes = per_sym_size[s]
            in_trade = False
            wins = 0; total = 0; pnl_acc = 0.0; trade_pnls = []
            running = 0.0
            for t in range(len(psp)):
                if ent[t] and not in_trade:
                    in_trade = True
                    running = 0.0
                if in_trade:
                    running += psp[t]
                    if abs(sizes[t]) > 0 and (t == len(psp) - 1 or abs(sizes[t + 1]) == 0):
                        # trade closes at t+1 boundary or at end
                        total += 1
                        if running > 0:
                            wins += 1
                        trade_pnls.append(running)
                        in_trade = False
                        running = 0.0
            per_sym_summary[s] = dict(
                n_trades=total,
                win_rate=float(wins / total) if total else 0.0,
                avg_trade_pnl=float(np.mean(trade_pnls)) if trade_pnls else 0.0,
                avg_win=float(np.mean([x for x in trade_pnls if x > 0])) if any(x > 0 for x in trade_pnls) else 0.0,
                avg_loss=float(np.mean([x for x in trade_pnls if x < 0])) if any(x < 0 for x in trade_pnls) else 0.0,
            )

        port_is = port[:is_end]; port_oos = port[is_end:]
        m_full = metrics(port); m_is = metrics(port_is); m_oos = metrics(port_oos)
        # also concurrency stats
        per_variant_results[vname] = dict(
            gates=sorted(gset),
            portfolio_metrics=dict(full=m_full, is_=m_is, oos=m_oos),
            per_symbol_metrics=per_sym_metrics,
            per_symbol_trade_summary=per_sym_summary,
            concurrency=dict(
                mean_active_bars=float(np.mean(n_active)),
                p95_active_bars=float(np.percentile(n_active, 95)),
                max_active_bars=int(n_active.max()),
                bars_with_active=int((n_active > 0).sum()),
                pct_bars_active=float((n_active > 0).mean()),
            ),
            total_entries=int(sum(per_sym_n_entries.values())),
        )
        log(f"  {vname}: total_entries={sum(per_sym_n_entries.values())}, "
            f"port_full_sh={m_full['sharpe']:.3f}, IS_sh={m_is['sharpe']:.3f}, OOS_sh={m_oos['sharpe']:.3f}, "
            f"mean_active={np.mean(n_active):.2f}")

    # ----------------------- variant comparison & best -----------------------
    variant_sh = {v: per_variant_results[v]["portfolio_metrics"]["is_"]["sharpe"]
                  for v in GATE_SETS}
    best_variant = max(variant_sh, key=variant_sh.get)
    log(f"best by IS Sharpe: {best_variant} (IS Sh={variant_sh[best_variant]:.3f})")
    best_port = per_variant_port[best_variant]
    best_port_is = best_port[:is_end]; best_port_oos = best_port[is_end:]

    # ----------------------- walk-forward -----------------------
    log("walk-forward 4-fold ...")
    wf = walk_forward(per_variant_port, n_bars)
    for r in wf:
        log(f"  fold {r['fold']}: train_end={r['train_end']} test=[{r['test_lo']}:{r['test_hi']}] "
            f"best={r['best_variant']} train_sh={r['train_sharpe']:.3f} test_sh={r['test_sharpe']:.3f}")

    # ----------------------- block bootstrap on OOS -----------------------
    log(f"block bootstrap n={N_BOOT} (OOS, best variant) ...")
    bb_lo, bb_hi, bb_mean = block_bootstrap(best_port_oos, n_boot=N_BOOT, block=20)
    log(f"  OOS Sharpe 95% CI: [{bb_lo:.3f}, {bb_hi:.3f}] mean={bb_mean:.3f}")

    # ----------------------- permutation null -----------------------
    log(f"permutation null n={N_PERM} (sign-shuffle wick) ...")
    null_sh = permutation_null_sharpe(aligned, btc_bucket,
                                      GATE_SETS[best_variant],
                                      n_perm=N_PERM)
    obs_full = per_variant_results[best_variant]["portfolio_metrics"]["full"]["sharpe"]
    pval = float((np.sum(np.array(null_sh) >= obs_full) + 1) / (len(null_sh) + 1))
    log(f"  obs full Sh={obs_full:.3f}  null mean={np.mean(null_sh):.3f} p={pval:.3f}")

    # ----------------------- DSR -----------------------
    trial_shs = [variant_sh[v] for v in GATE_SETS]
    dsr = deflated_sharpe(per_variant_results[best_variant]["portfolio_metrics"]["is_"]["sharpe"],
                          trial_shs, n_eff=len(best_port_is))
    log(f"  DSR (IS, N_trials={len(trial_shs)}) = {dsr:.3f}")

    # ----------------------- cost stress -----------------------
    log("cost stress ...")
    def restress(mult: float) -> Dict[str, float]:
        per_sym_size_v = per_variant_per_sym_size[best_variant]
        per_sym_close_v = {s: aligned[s]["close"].to_numpy(np.float64) for s in per_sym_size_v}
        port = np.zeros(n_bars, dtype=np.float64)
        # apply same max_concurrent gating
        active_mask = np.vstack([(np.abs(per_sym_size_v[s]) > 0).astype(np.float64)
                                 for s in per_sym_size_v])
        cum = np.cumsum(active_mask, axis=0)
        take_mask = (active_mask > 0) & (cum <= MAX_CONCURRENT)
        w_per = 1.0 / MAX_CONCURRENT
        weight_mat = take_mask * w_per
        for i, s in enumerate(per_sym_size_v):
            close = per_sym_close_v[s]
            ret = pd.Series(close).pct_change().fillna(0.0).to_numpy()
            size = per_sym_size_v[s]
            gross = size * ret
            delta = np.abs(np.diff(size, prepend=0.0))
            cost = delta * COST_PER_TURN * mult
            pnl = gross - cost
            port += pnl * weight_mat[i]
        return dict(
            sharpe_full=sharpe(port),
            sharpe_is=sharpe(port[:is_end]),
            sharpe_oos=sharpe(port[is_end:]),
            mdd=max_dd(port),
            ann_ret=float((1 + port.mean()) ** (365 * 6) - 1) if len(port) else 0.0,
        )

    stress = dict(
        cost_x0_5=restress(0.5),
        cost_x1_0=restress(1.0),
        cost_x1_5=restress(1.5),
        cost_x2_0=restress(2.0),
    )
    log(f"  x1.0 OOS Sh={stress['cost_x1_0']['sharpe_oos']:.3f}  x1.5 OOS Sh={stress['cost_x1_5']['sharpe_oos']:.3f}")

    # ----------------------- §6 mini gates -----------------------
    oos_sh = per_variant_results[best_variant]["portfolio_metrics"]["oos"]["sharpe"]
    is_sh = per_variant_results[best_variant]["portfolio_metrics"]["is_"]["sharpe"]
    pbo_fracs = sum(1 for r in wf if r["test_sharpe"] < 0)
    pbo = float(pbo_fracs / max(1, len(wf)))
    gates = dict(
        G1_oos_sharpe_gt_0_5=bool(oos_sh > 0.5),
        G2_pbo_lt_0_3=bool(pbo < 0.3),
        G3_dsr_gt_0_5=bool(dsr > 0.5),
        G4_perm_p_lt_0_05=bool(pval < 0.05),
        G5_cost_x1_5_oos_gt_0=bool(stress["cost_x1_5"]["sharpe_oos"] > 0),
        is_sharpe=float(is_sh),
        oos_sharpe=float(oos_sh),
        oos_full_sharpe=float(obs_full),
        pbo=float(pbo),
        dsr=float(dsr),
        perm_p=float(pval),
        bb_oos_ci=[bb_lo, bb_hi],
    )
    passed = sum([gates["G1_oos_sharpe_gt_0_5"], gates["G2_pbo_lt_0_3"],
                  gates["G3_dsr_gt_0_5"], gates["G4_perm_p_lt_0_05"],
                  gates["G5_cost_x1_5_oos_gt_0"]])
    if passed >= 4:
        verdict = "ACCEPT"
    elif passed >= 2:
        verdict = "CONDITIONAL"
    else:
        verdict = "REJECT"
    log(f"gates passed {passed}/5  ->  {verdict}")

    # ----------------------- curves -----------------------
    def downsample(arr, max_pts=600):
        a = np.asarray(arr)
        if len(a) <= max_pts:
            return a.tolist()
        step = max(1, len(a) // max_pts)
        return a[::step].tolist()

    eq_port = np.cumprod(1 + best_port)
    eq_variants = {v: np.cumprod(1 + per_variant_port[v]).tolist()
                   for v in GATE_SETS}
    eq_variants_ds = {v: downsample(eq_variants[v]) for v in eq_variants}

    # top/bottom 5 by full sharpe in best variant
    psm_best = per_variant_results[best_variant]["per_symbol_metrics"]
    ranked = sorted(psm_best.items(), key=lambda kv: kv[1]["sharpe"], reverse=True)
    top5 = [s for s, _ in ranked[:5]]
    bot5 = [s for s, _ in ranked[-5:]]
    pnl_best = per_variant_per_sym_pnl[best_variant]
    top5_eq = {s: downsample(np.cumprod(1 + pnl_best[s])) for s in top5}
    bot5_eq = {s: downsample(np.cumprod(1 + pnl_best[s])) for s in bot5}

    curves = dict(
        wave="K118",
        best_variant=best_variant,
        n_bars=int(n_bars),
        is_end_idx=int(is_end),
        is_end_idx_downsampled=int(is_end // max(1, len(eq_port) // 600)),
        portfolio_equity=downsample(eq_port),
        variant_equities=eq_variants_ds,
        top5_symbols=top5,
        top5_equity=top5_eq,
        bot5_symbols=bot5,
        bot5_equity=bot5_eq,
    )
    with open(OUT_CURVES, "w") as f:
        json.dump(curves, f)
    log(f"curves -> {OUT_CURVES}")

    # ----------------------- assemble results -----------------------
    results = dict(
        wave="K118",
        ts_utc=pd.Timestamp.utcnow().isoformat(),
        config=dict(
            universe=syms,
            universe_size=len(syms),
            min_bars=MIN_BARS,
            n_bars_aligned=int(n_bars),
            bars_per_day=BARS_PER_DAY,
            is_frac=IS_FRAC,
            wick_thresh=WICK_THRESH,
            hold_bars=HOLD_BARS,
            atr_period=ATR_PERIOD,
            atr_trail_mult=ATR_TRAIL_MULT,
            target_vol_ann=TARGET_VOL_ANN,
            pos_cap=POS_CAP,
            max_concurrent=MAX_CONCURRENT,
            taker_fee=TAKER,
            slippage=SLIPPAGE,
            cost_per_turn=COST_PER_TURN,
            vol_window=VOL_WIN,
            vol_ref_window=VOL_REF,
            gate_sets={k: sorted(v) for k, v in GATE_SETS.items()},
        ),
        btc_vol_bucket_distribution={k: int(v) for k, v in bucket_dist.items()},
        variants=per_variant_results,
        best_variant=best_variant,
        walk_forward=wf,
        block_bootstrap_oos_sharpe_ci=dict(lo=bb_lo, hi=bb_hi, mean=bb_mean, n=N_BOOT),
        permutation=dict(
            n=len(null_sh),
            null_mean=float(np.mean(null_sh)),
            null_std=float(np.std(null_sh)),
            null_p95=float(np.percentile(null_sh, 95)),
            observed_full_sharpe=obs_full,
            p_value=pval,
        ),
        deflated_sharpe=dsr,
        cost_stress=stress,
        gates=gates,
        verdict=verdict,
        wall_time_sec=time.time() - t0,
    )
    with open(OUT_JSON, "w") as f:
        json.dump(results, f, indent=2, default=str)
    log(f"results -> {OUT_JSON}")
    log(f"DONE in {time.time() - t0:.1f}s  verdict={verdict}")
    return results


if __name__ == "__main__":
    try:
        main()
    except Exception:
        import traceback
        traceback.print_exc()
        sys.exit(1)

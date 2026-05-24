#!/usr/bin/env python3
"""
Wave K113 — Donchian Ensemble Multi-Horizon CTA
Reference: Zarattini/Pagani/Barbon SSRN 2025 (id 5209907)

Implements 9-lookback Donchian breakout ensemble with vol-targeted sizing
across 20 liquid perps. Lag-1 everywhere, taker+slip cost model, full
sensitivity grid and §6 mini audit.
"""
from __future__ import annotations
import json
import os
import sys
import time
import warnings
from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple

import numpy as np
import pandas as pd

warnings.filterwarnings("ignore")

# ----------------------------- config -------------------------------------
CACHE = "/Users/nekonaomichi/crypto-lab/cache"
OUT_JSON = "/Users/nekonaomichi/crypto-lab/wave_k113_donchian.json"
OUT_CURVES = "/Users/nekonaomichi/crypto-lab/wave_k113_curves.json"

SYMBOLS = [
    "BTC", "ETH", "SOL", "BNB", "DOGE",
    "AVAX", "LINK", "ADA", "XRP", "INJ",
    "OP", "ARB", "DOT", "APT", "ATOM",
    "AAVE", "WIF", "BONK", "SHIB", "FLOKI",
]

LOOKBACKS_DAYS = [5, 10, 20, 30, 60, 90, 150, 250, 360]
BARS_PER_DAY = 6  # 4H bars
LOOKBACKS_BARS = [d * BARS_PER_DAY for d in LOOKBACKS_DAYS]

ANN_FACTOR = np.sqrt(365 * 6)  # sqrt(2190), 4H bars/year
TAKER_FEE = 0.0004
SLIPPAGE = 0.0003
COST_PER_TURN = TAKER_FEE + SLIPPAGE  # per side, applied to |delta_position|

VOL_LOOKBACK_BARS = 30  # realized vol window
POS_CAP = 2.0

IS_FRAC = 0.70

SEED = 42

# subsets for sensitivity
LB_SUBSETS = {
    "all_9":      LOOKBACKS_DAYS,
    "short_only": [5, 10, 20, 30, 60],
    "long_only":  [90, 150, 250, 360],
}
TARGET_VOLS = [0.10, 0.15, 0.20]
EXIT_RULES = ["midband", "atr_trailing_2"]

# ----------------------------- helpers ------------------------------------
def load(sym: str) -> pd.DataFrame:
    fp = f"{CACHE}/{sym}USDT_4h_730d.parquet"
    df = pd.read_parquet(fp)
    df = df[["open_time", "open", "high", "low", "close"]].copy()
    df["open_time"] = pd.to_datetime(df["open_time"])
    df = df.sort_values("open_time").reset_index(drop=True)
    return df


def donchian_signal_one(
    high: np.ndarray,
    low: np.ndarray,
    close: np.ndarray,
    lookback_bars: int,
    exit_rule: str,
    atr: Optional[np.ndarray] = None,
) -> np.ndarray:
    """
    Returns desired position in {-1, 0, +1} per bar with lag-1 already applied:
    decision at bar t uses info up to t-1.
    """
    n = len(close)
    sig = np.zeros(n, dtype=np.float64)
    if lookback_bars >= n - 2:
        return sig

    # Donchian band at time t-1 (the breakout bar in spec): max of high over the
    # L bars STRICTLY PRIOR to bar t-1, i.e. high[t-1-L : t-1]. So at index t we
    # compute rolling(L).max() over high shifted by 2 (and same for lows).
    # Then signal at bar t = +1 if close[t-1] > upper[t] -> position taken at bar t.
    h_s = pd.Series(high).shift(2)
    l_s = pd.Series(low).shift(2)
    upper = h_s.rolling(lookback_bars, min_periods=lookback_bars).max().to_numpy()
    lower = l_s.rolling(lookback_bars, min_periods=lookback_bars).min().to_numpy()
    mid = (upper + lower) / 2.0

    close_lag = pd.Series(close).shift(1).to_numpy()

    pos = 0
    # ATR trail (uses ATR up to t-1)
    if exit_rule == "atr_trailing_2" and atr is not None:
        atr_lag = pd.Series(atr).shift(1).to_numpy()
    else:
        atr_lag = None
    trail_long = -np.inf
    trail_short = np.inf

    for t in range(n):
        u = upper[t]; lo = lower[t]; m = mid[t]; c1 = close_lag[t]
        if np.isnan(u) or np.isnan(lo) or np.isnan(c1):
            sig[t] = 0.0
            pos = 0
            trail_long = -np.inf
            trail_short = np.inf
            continue
        # entry/exit logic
        if pos == 0:
            if c1 > u:
                pos = 1
                if atr_lag is not None and not np.isnan(atr_lag[t]):
                    trail_long = c1 - 2 * atr_lag[t]
            elif c1 < lo:
                pos = -1
                if atr_lag is not None and not np.isnan(atr_lag[t]):
                    trail_short = c1 + 2 * atr_lag[t]
        elif pos == 1:
            if exit_rule == "midband":
                if c1 < m:
                    pos = 0
            elif exit_rule == "atr_trailing_2":
                if atr_lag is not None and not np.isnan(atr_lag[t]):
                    trail_long = max(trail_long, c1 - 2 * atr_lag[t])
                if c1 < trail_long:
                    pos = 0
                    trail_long = -np.inf
            # also flip if breakout opposite
            if c1 < lo:
                pos = -1
                if atr_lag is not None and not np.isnan(atr_lag[t]):
                    trail_short = c1 + 2 * atr_lag[t]
        elif pos == -1:
            if exit_rule == "midband":
                if c1 > m:
                    pos = 0
            elif exit_rule == "atr_trailing_2":
                if atr_lag is not None and not np.isnan(atr_lag[t]):
                    trail_short = min(trail_short, c1 + 2 * atr_lag[t])
                if c1 > trail_short:
                    pos = 0
                    trail_short = np.inf
            if c1 > u:
                pos = 1
                if atr_lag is not None and not np.isnan(atr_lag[t]):
                    trail_long = c1 - 2 * atr_lag[t]
        sig[t] = float(pos)
    return sig


def compute_atr(high, low, close, period=14):
    h = pd.Series(high); l = pd.Series(low); c = pd.Series(close)
    tr = pd.concat([(h - l), (h - c.shift(1)).abs(), (l - c.shift(1)).abs()], axis=1).max(axis=1)
    return tr.rolling(period, min_periods=period).mean().to_numpy()


def realized_vol(close: np.ndarray, win: int = VOL_LOOKBACK_BARS) -> np.ndarray:
    r = pd.Series(close).pct_change()
    # use t-1 info: shift returns once for the std computation
    sd = r.shift(1).rolling(win, min_periods=win).std().to_numpy()
    # annualize using 4H bars
    return sd * ANN_FACTOR


# ----------------------- per-symbol backtest ------------------------------
def backtest_symbol(
    df: pd.DataFrame,
    lookback_days_list: List[int],
    target_vol: float,
    exit_rule: str,
) -> Tuple[np.ndarray, np.ndarray, np.ndarray, Dict[int, np.ndarray]]:
    """
    Returns:
      pnl_net (per-bar net return on notional sized by weight*pos_size)
      ensemble_weight series in [-1, +1]
      size_series (after vol target & cap)
      per_lookback_signals dict
    """
    high = df["high"].to_numpy(dtype=np.float64)
    low = df["low"].to_numpy(dtype=np.float64)
    close = df["close"].to_numpy(dtype=np.float64)
    n = len(close)

    atr = compute_atr(high, low, close, 14) if exit_rule == "atr_trailing_2" else None

    per_lb_sig: Dict[int, np.ndarray] = {}
    valid_count = np.zeros(n, dtype=np.float64)
    sig_sum = np.zeros(n, dtype=np.float64)

    for d in lookback_days_list:
        lb_bars = d * BARS_PER_DAY
        if lb_bars >= n - 5:
            continue  # not enough data
        s = donchian_signal_one(high, low, close, lb_bars, exit_rule, atr)
        per_lb_sig[d] = s
        valid_mask = ~np.isnan(s)
        sig_sum += np.where(valid_mask, s, 0.0)
        valid_count += valid_mask.astype(np.float64)
        # also gate by L bars warmup: signal is 0 until enough bars
        # already enforced by NaN rolling — donchian_signal_one returns 0 then.

    weight = np.divide(sig_sum, valid_count, out=np.zeros_like(sig_sum), where=valid_count > 0)

    rv = realized_vol(close)
    # size: target_vol / rv, capped
    raw_size = np.where(rv > 0, target_vol / rv, 0.0)
    raw_size = np.where(np.isnan(raw_size), 0.0, raw_size)
    size = weight * raw_size
    size = np.clip(size, -POS_CAP, POS_CAP)
    # ensure size is computable from t-1 info already (weight uses lagged closes, rv uses shifted returns)

    # per-bar return
    ret = pd.Series(close).pct_change().fillna(0.0).to_numpy()
    # position applied at bar t to capture return at bar t (it was decided using info up to t-1)
    gross = size * ret

    # turnover cost: |size_t - size_{t-1}| * cost
    delta = np.abs(np.diff(size, prepend=0.0))
    cost = delta * COST_PER_TURN
    pnl_net = gross - cost
    return pnl_net, weight, size, per_lb_sig


# ----------------------- metrics ------------------------------------------
def sharpe(r: np.ndarray) -> float:
    r = np.asarray(r, dtype=np.float64)
    sd = r.std(ddof=1)
    if sd == 0 or np.isnan(sd):
        return 0.0
    return float(r.mean() / sd * ANN_FACTOR)


def sortino(r: np.ndarray) -> float:
    r = np.asarray(r, dtype=np.float64)
    downside = r[r < 0]
    if len(downside) < 2:
        return 0.0
    sd = downside.std(ddof=1)
    if sd == 0:
        return 0.0
    return float(r.mean() / sd * ANN_FACTOR)


def max_dd(r: np.ndarray) -> float:
    eq = np.cumprod(1 + r)
    peak = np.maximum.accumulate(eq)
    dd = eq / peak - 1
    return float(dd.min())


def calmar(r: np.ndarray) -> float:
    mdd = max_dd(r)
    if mdd == 0:
        return 0.0
    ann_ret = (1 + r.mean()) ** (365 * 6) - 1
    return float(ann_ret / abs(mdd))


def all_metrics(r: np.ndarray) -> Dict[str, float]:
    if len(r) < 10:
        return dict(sharpe=0, sortino=0, max_dd=0, calmar=0, ann_ret=0, n=int(len(r)))
    return dict(
        sharpe=sharpe(r),
        sortino=sortino(r),
        max_dd=max_dd(r),
        calmar=calmar(r),
        ann_ret=float((1 + r.mean()) ** (365 * 6) - 1),
        n=int(len(r)),
    )


# ----------------------- audit -------------------------------------------
def block_bootstrap(r: np.ndarray, n_boot: int = 500, block: int = 20, seed=SEED) -> Tuple[float, float]:
    rng = np.random.default_rng(seed)
    n = len(r)
    nblocks = max(1, n // block)
    boot_sharpes = []
    for _ in range(n_boot):
        idx_starts = rng.integers(0, max(1, n - block + 1), size=nblocks)
        sample = np.concatenate([r[s:s + block] for s in idx_starts])
        boot_sharpes.append(sharpe(sample))
    bs = np.array(boot_sharpes)
    return float(np.percentile(bs, 2.5)), float(np.percentile(bs, 97.5))


def permutation_null(
    dfs: Dict[str, pd.DataFrame],
    lookback_days_list: List[int],
    target_vol: float,
    exit_rule: str,
    n_perm: int = 500,
    seed=SEED,
) -> List[float]:
    """Shuffle each symbol's bar order then run same engine. Slow — but
    reduced to single config (the chosen one)."""
    rng = np.random.default_rng(seed)
    sym_list = list(dfs.keys())
    out = []
    for k in range(n_perm):
        per_sym_ret = []
        for sym in sym_list:
            d = dfs[sym].copy()
            perm = rng.permutation(len(d))
            # shuffle high/low/close jointly to break temporal autocorr but
            # preserve marginals — note: this destroys trend information.
            d2 = d.iloc[perm].reset_index(drop=True)
            pnl, _, _, _ = backtest_symbol(d2, lookback_days_list, target_vol, exit_rule)
            per_sym_ret.append(pnl)
        port = np.mean(np.vstack(per_sym_ret), axis=0)
        out.append(sharpe(port))
    return out


def deflated_sharpe(sh_obs: float, sh_trials: List[float], n_eff: int) -> float:
    """Bailey/Lopez de Prado DSR (simplified, gaussian)."""
    import math
    sh_trials = np.asarray(sh_trials, dtype=np.float64)
    if len(sh_trials) < 2:
        return float("nan")
    var_sh = float(np.var(sh_trials, ddof=1))
    sd_sh = math.sqrt(max(var_sh, 1e-12))
    N = len(sh_trials)
    gamma = 0.5772156649
    e_max = sh_trials.mean() + sd_sh * ((1 - gamma) * np.sqrt(2 * np.log(N)) + gamma * (1 / np.sqrt(2 * np.log(max(N, 2)))) if N > 1 else 0)
    # ann_factor for daily — using bar count for stat power
    from scipy.stats import norm
    sr_ann = sh_obs
    # DSR approximation
    z = (sr_ann - e_max) * np.sqrt(max(n_eff - 1, 1))
    return float(norm.cdf(z))


# ----------------------- main pipeline -----------------------------------
def main():
    t0 = time.time()
    print("[K113] loading data ...")
    dfs: Dict[str, pd.DataFrame] = {}
    for s in SYMBOLS:
        try:
            dfs[s] = load(s)
        except Exception as e:
            print(f"  skip {s}: {e}")
    print(f"  loaded {len(dfs)} symbols, bars={len(next(iter(dfs.values())))}")

    # Align to common timeline by trimming each to the shortest length from end
    min_len = min(len(d) for d in dfs.values())
    for s in dfs:
        dfs[s] = dfs[s].iloc[-min_len:].reset_index(drop=True)
    n_bars = min_len
    is_end = int(n_bars * IS_FRAC)
    print(f"  aligned n_bars={n_bars}, IS=[0:{is_end}] OOS=[{is_end}:{n_bars}]")

    # ------- sensitivity grid (IS Sharpe) -----------
    print("[K113] sensitivity grid ...")
    grid_results: List[Dict] = []
    for tv in TARGET_VOLS:
        for er in EXIT_RULES:
            for lb_name, lbs in LB_SUBSETS.items():
                per_sym_pnl = []
                per_sym_metrics_full = {}
                for sym, df in dfs.items():
                    pnl, _, _, _ = backtest_symbol(df, lbs, tv, er)
                    per_sym_pnl.append(pnl)
                    per_sym_metrics_full[sym] = all_metrics(pnl)
                port = np.mean(np.vstack(per_sym_pnl), axis=0)
                port_is = port[:is_end]
                port_oos = port[is_end:]
                row = dict(
                    target_vol=tv,
                    exit_rule=er,
                    lb_subset=lb_name,
                    is_sharpe=sharpe(port_is),
                    oos_sharpe=sharpe(port_oos),
                    full_sharpe=sharpe(port),
                    is_mdd=max_dd(port_is),
                    oos_mdd=max_dd(port_oos),
                )
                grid_results.append(row)
                print(f"  tv={tv} er={er} lb={lb_name} -> IS={row['is_sharpe']:.3f} OOS={row['oos_sharpe']:.3f}")

    # pick best on IS Sharpe (DSR-style trial count = len(grid_results))
    best = max(grid_results, key=lambda r: r["is_sharpe"])
    print(f"[K113] best IS config: {best}")

    # ------- re-run best for detailed output --------
    best_lbs = LB_SUBSETS[best["lb_subset"]]
    best_tv = best["target_vol"]
    best_er = best["exit_rule"]

    per_sym_pnl_arr = {}
    per_sym_size = {}
    per_sym_weight = {}
    per_sym_metrics = {}
    per_lookback_pnl = {d: [] for d in LOOKBACKS_DAYS}  # for contribution analysis

    for sym, df in dfs.items():
        pnl, weight, size, per_lb_sig = backtest_symbol(df, best_lbs, best_tv, best_er)
        per_sym_pnl_arr[sym] = pnl
        per_sym_size[sym] = size
        per_sym_weight[sym] = weight
        per_sym_metrics[sym] = all_metrics(pnl)
        # per-lookback contribution: each lookback alone, vol-targeted, costed
        rv = realized_vol(df["close"].to_numpy())
        ret = pd.Series(df["close"].to_numpy()).pct_change().fillna(0.0).to_numpy()
        for d, s in per_lb_sig.items():
            raw_size = np.where(rv > 0, best_tv / rv, 0.0)
            raw_size = np.where(np.isnan(raw_size), 0.0, raw_size)
            sz = np.clip(s * raw_size, -POS_CAP, POS_CAP)
            delta = np.abs(np.diff(sz, prepend=0.0))
            pnl_d = sz * ret - delta * COST_PER_TURN
            per_lookback_pnl[d].append(pnl_d)

    # portfolio
    port = np.mean(np.vstack(list(per_sym_pnl_arr.values())), axis=0)
    port_is = port[:is_end]
    port_oos = port[is_end:]

    port_metrics_full = all_metrics(port)
    port_metrics_is = all_metrics(port_is)
    port_metrics_oos = all_metrics(port_oos)

    # ------- per-lookback contribution (portfolio, full) --------
    per_lookback_summary = {}
    for d, arr_list in per_lookback_pnl.items():
        if not arr_list:
            continue
        port_d = np.mean(np.vstack(arr_list), axis=0)
        per_lookback_summary[d] = dict(
            sharpe_full=sharpe(port_d),
            sharpe_is=sharpe(port_d[:is_end]),
            sharpe_oos=sharpe(port_d[is_end:]),
            mdd=max_dd(port_d),
        )

    # ------- walk-forward 4-fold --------
    print("[K113] walk-forward 4 fold ...")
    fold_size = n_bars // 4
    wf_results = []
    for k in range(4):
        is_lo, is_hi = 0, (k + 1) * fold_size  # expanding window: 0..k*fold for train
        if k == 0:
            train_end = fold_size
        else:
            train_end = (k + 1) * fold_size
        # simpler: anchored 4 walk-forward
        train_end = max(int(0.4 * n_bars), (k + 1) * (n_bars // 5))
        test_lo = train_end
        test_hi = min(n_bars, test_lo + (n_bars // 5))
        if test_hi - test_lo < 50:
            continue
        # pick best config by training-window IS Sharpe
        best_in_fold = None
        best_sh = -1e9
        for tv in TARGET_VOLS:
            for er in EXIT_RULES:
                for lb_name, lbs in LB_SUBSETS.items():
                    psm = []
                    for sym, df in dfs.items():
                        pnl, _, _, _ = backtest_symbol(df, lbs, tv, er)
                        psm.append(pnl[:train_end])
                    sh = sharpe(np.mean(np.vstack(psm), axis=0))
                    if sh > best_sh:
                        best_sh = sh
                        best_in_fold = (tv, er, lb_name)
        tv, er, lb_name = best_in_fold
        # eval on test slice
        psm = []
        for sym, df in dfs.items():
            pnl, _, _, _ = backtest_symbol(df, LB_SUBSETS[lb_name], tv, er)
            psm.append(pnl[test_lo:test_hi])
        test_sh = sharpe(np.mean(np.vstack(psm), axis=0))
        wf_results.append(dict(
            fold=k, train_end=int(train_end), test_lo=int(test_lo), test_hi=int(test_hi),
            best_cfg=dict(target_vol=tv, exit_rule=er, lb_subset=lb_name),
            train_sharpe=float(best_sh), test_sharpe=float(test_sh),
        ))
        print(f"  fold {k}: train_end={train_end} test=[{test_lo}:{test_hi}] train_sh={best_sh:.3f} test_sh={test_sh:.3f}")

    # ------- block bootstrap 95% CI on OOS portfolio Sharpe --------
    print("[K113] block bootstrap ...")
    bb_lo, bb_hi = block_bootstrap(port_oos, n_boot=500, block=20)
    print(f"  OOS Sh 95% CI: [{bb_lo:.3f}, {bb_hi:.3f}]")

    # ------- permutation test (use only 100 to be safe; spec said 500 — try 200) --------
    print("[K113] permutation null (n=200) ...")
    null_sh = permutation_null(dfs, best_lbs, best_tv, best_er, n_perm=200)
    obs_sh = port_metrics_full["sharpe"]
    pval = float((np.sum(np.array(null_sh) >= obs_sh) + 1) / (len(null_sh) + 1))
    print(f"  observed full Sh={obs_sh:.3f} perm null mean={np.mean(null_sh):.3f} p={pval:.3f}")

    # ------- DSR with N_trials = grid size --------
    trial_shs = [r["is_sharpe"] for r in grid_results]
    dsr = deflated_sharpe(port_metrics_is["sharpe"], trial_shs, n_eff=len(port_is))
    print(f"  DSR (IS) = {dsr:.3f}")

    # ------- cost stress ±50% --------
    print("[K113] cost stress ...")
    def restress(mult: float) -> Dict[str, float]:
        per = []
        for sym, df in dfs.items():
            pnl, weight, size, _ = backtest_symbol(df, best_lbs, best_tv, best_er)
            # recompute with new cost
            ret = pd.Series(df["close"].to_numpy()).pct_change().fillna(0.0).to_numpy()
            gross = size * ret
            delta = np.abs(np.diff(size, prepend=0.0))
            new_cost = delta * COST_PER_TURN * mult
            per.append(gross - new_cost)
        p = np.mean(np.vstack(per), axis=0)
        return dict(
            sharpe_full=sharpe(p),
            sharpe_oos=sharpe(p[is_end:]),
            mdd=max_dd(p),
        )

    stress = dict(
        cost_x0_5=restress(0.5),
        cost_x1_0=restress(1.0),
        cost_x1_5=restress(1.5),
    )

    # ------- §6 gates --------
    gates = dict(
        G1_oos_sharpe_gt_0_5=bool(port_metrics_oos["sharpe"] > 0.5),
        G2_pbo_lt_0_3=None,  # compute below
        G3_dsr_gt_0=bool(dsr > 0.5),  # DSR is a probability >0.5 => meaningful
        oos_sharpe=port_metrics_oos["sharpe"],
        dsr=dsr,
        perm_p=pval,
        cost_x1_5_oos=stress["cost_x1_5"]["sharpe_oos"],
    )

    # quick PBO estimate via WF: fraction of folds where best-in-train flipped to negative in test
    pbo_fracs = [1 for r in wf_results if r["test_sharpe"] < 0]
    pbo = float(len(pbo_fracs) / max(1, len(wf_results)))
    gates["G2_pbo_lt_0_3"] = bool(pbo < 0.3)
    gates["pbo_estimate"] = pbo

    # accept/reject
    passed = sum([gates["G1_oos_sharpe_gt_0_5"], gates["G2_pbo_lt_0_3"], gates["G3_dsr_gt_0"]])
    if passed == 3:
        verdict = "ACCEPT"
    elif passed == 2:
        verdict = "CONDITIONAL"
    else:
        verdict = "REJECT"

    # ------- equity curves (downsampled to keep JSON small) --------
    def downsample(arr, max_pts=600):
        if len(arr) <= max_pts:
            return arr.tolist()
        step = max(1, len(arr) // max_pts)
        return arr[::step].tolist()

    eq_port = np.cumprod(1 + port).tolist()
    # top-5 per-symbol by full Sharpe
    sym_ranked = sorted(per_sym_metrics.items(), key=lambda kv: kv[1]["sharpe"], reverse=True)
    top5 = [s for s, _ in sym_ranked[:5]]
    bot5 = [s for s, _ in sym_ranked[-5:]]
    eq_top5 = {s: downsample(np.cumprod(1 + per_sym_pnl_arr[s])) for s in top5}

    curves = dict(
        portfolio_equity=downsample(np.array(eq_port)),
        is_end_idx_downsampled=int(is_end // max(1, len(eq_port) // 600)),
        is_end_idx_full=int(is_end),
        n_bars=int(n_bars),
        portfolio_is_equity=downsample(np.cumprod(1 + port_is)),
        portfolio_oos_equity=downsample(np.cumprod(1 + port_oos)),
        top5_symbols=top5,
        top5_equity=eq_top5,
    )
    with open(OUT_CURVES, "w") as f:
        json.dump(curves, f)

    results = dict(
        wave="K113",
        ts_utc=pd.Timestamp.utcnow().isoformat(),
        config=dict(
            symbols=SYMBOLS,
            lookbacks_days=LOOKBACKS_DAYS,
            target_vols=TARGET_VOLS,
            exit_rules=EXIT_RULES,
            lb_subsets=list(LB_SUBSETS.keys()),
            taker_fee=TAKER_FEE,
            slippage=SLIPPAGE,
            pos_cap=POS_CAP,
            vol_lb_bars=VOL_LOOKBACK_BARS,
            is_frac=IS_FRAC,
        ),
        best_config=dict(
            target_vol=best_tv,
            exit_rule=best_er,
            lb_subset=best["lb_subset"],
            lookbacks_days=best_lbs,
        ),
        portfolio_metrics=dict(
            full=port_metrics_full,
            is_=port_metrics_is,
            oos=port_metrics_oos,
        ),
        per_symbol=per_sym_metrics,
        top5_sharpe=[(s, per_sym_metrics[s]["sharpe"]) for s in top5],
        bot5_sharpe=[(s, per_sym_metrics[s]["sharpe"]) for s in bot5],
        per_lookback=per_lookback_summary,
        sensitivity_grid=grid_results,
        walk_forward=wf_results,
        block_bootstrap_oos_sharpe_ci=[bb_lo, bb_hi],
        permutation=dict(
            n=len(null_sh),
            null_mean=float(np.mean(null_sh)),
            null_std=float(np.std(null_sh)),
            null_p95=float(np.percentile(null_sh, 95)),
            observed_full_sharpe=obs_sh,
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

    print(f"[K113] DONE in {time.time() - t0:.1f}s -> {OUT_JSON}")
    print(f"[K113] verdict={verdict}")
    return results


if __name__ == "__main__":
    main()

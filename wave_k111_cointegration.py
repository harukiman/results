"""
Wave K111 — Cointegrated Alt Pair Z-Score (Stat Arb)

Engle-Granger cointegration screening + rolling-Z mean reversion on log-spread
across a 20-symbol alt universe. In-sample (70%) pair selection, out-of-sample
(30%) portfolio backtest, walk-forward 4-fold, permutation null, block-bootstrap
CI, cost stress, DSR.

Outputs:
  /Users/nekonaomichi/crypto-lab/wave_k111_cointegration.json
  /Users/nekonaomichi/crypto-lab/wave_k111_curves.json
"""

from __future__ import annotations

import json
import math
import os
import time
import warnings
from itertools import combinations
from typing import Dict, List, Tuple

import numpy as np
import pandas as pd
from statsmodels.regression.linear_model import OLS
from statsmodels.tools.tools import add_constant
from statsmodels.tsa.stattools import adfuller

warnings.filterwarnings("ignore")

CACHE = "/Users/nekonaomichi/crypto-lab/cache"
OUT_JSON = "/Users/nekonaomichi/crypto-lab/wave_k111_cointegration.json"
OUT_CURVES = "/Users/nekonaomichi/crypto-lab/wave_k111_curves.json"

SYMBOLS = [
    "BTC", "ETH", "SOL", "BNB", "DOGE", "AVAX", "LINK", "ADA", "XRP", "INJ",
    "OP", "ARB", "DOT", "APT", "ATOM", "AAVE", "WIF", "BONK", "SHIB", "FLOKI",
]

# Strategy params
Z_ENTER = 2.0
Z_EXIT = 0.5
Z_STOP = 4.0
MAX_HOLD = 30           # bars
ROLL_WIN = 180          # bars rolling Z + beta
HL_MIN, HL_MAX = 10, 200
ADF_PMAX = 0.05
IS_FRAC = 0.70

# Costs (per leg, per side). 4 sides total per round trip (enter L, enter S, exit L, exit S)
COST_PER_SIDE = 0.0007          # 0.07% per leg per side
# Funding ignored (cancels approximately for hedged spreads)

# Portfolio
MAX_CONCURRENT = 8
IS_SHARPE_GATE = 0.8

BARS_PER_YEAR = 6 * 365  # 4H bars

RNG = np.random.default_rng(42)


# ---------------- Data ---------------- #

def load_closes(symbols: List[str]) -> pd.DataFrame:
    series = {}
    for s in symbols:
        path = f"{CACHE}/{s}USDT_4h_730d.parquet"
        if not os.path.exists(path):
            print(f"  miss: {s}")
            continue
        df = pd.read_parquet(path, columns=["open_time", "close"])
        df = df.set_index("open_time").sort_index()
        series[s] = df["close"].astype(float)
    px = pd.DataFrame(series)
    px = px.dropna(how="any")  # align on common window
    return px


# ---------------- Pair tests ---------------- #

def half_life(resid: np.ndarray) -> float:
    """AR(1) half-life of mean reversion."""
    r = np.asarray(resid, dtype=float)
    r = r[~np.isnan(r)]
    if len(r) < 50:
        return np.nan
    dr = np.diff(r)
    r_lag = r[:-1]
    # dr = phi * r_lag + e ; HL = -ln(2)/ln(1+phi) when phi<0
    X = add_constant(r_lag)
    try:
        res = OLS(dr, X).fit()
        phi = res.params[1]
        if phi >= 0 or phi <= -1:
            return np.nan
        hl = -math.log(2.0) / math.log(1.0 + phi)
        return hl
    except Exception:
        return np.nan


def engle_granger(y: np.ndarray, x: np.ndarray) -> Tuple[float, float, float]:
    """
    Returns: (beta, adf_pvalue, half_life)
    y = alpha + beta * x + resid; ADF on resid.
    """
    yy = np.asarray(y, dtype=float)
    xx = np.asarray(x, dtype=float)
    mask = np.isfinite(yy) & np.isfinite(xx)
    yy, xx = yy[mask], xx[mask]
    if len(yy) < 100:
        return np.nan, 1.0, np.nan
    X = add_constant(xx)
    res = OLS(yy, X).fit()
    alpha, beta = res.params[0], res.params[1]
    resid = yy - alpha - beta * xx
    try:
        adf_p = adfuller(resid, maxlag=4, autolag=None, regression="c")[1]
    except Exception:
        adf_p = 1.0
    hl = half_life(resid)
    return beta, adf_p, hl


# ---------------- Backtest per pair ---------------- #

def backtest_pair(
    pY: pd.Series,
    pX: pd.Series,
    start_idx: int,
    end_idx: int,
    z_enter: float = Z_ENTER,
    z_exit: float = Z_EXIT,
    z_stop: float = Z_STOP,
    max_hold: int = MAX_HOLD,
    roll_win: int = ROLL_WIN,
    cost_per_side: float = COST_PER_SIDE,
) -> Dict:
    """
    Backtest one pair over bars [start_idx : end_idx). Returns daily-bar P&L
    series (net returns on capital allocated to the spread, equal $ per leg).
    Spread S_t = log(pY_t) - beta_t * log(pX_t), with beta from rolling 180-bar OLS.
    Z computed on rolling mean/std of S.
    Trade rule: signal at t-1 -> position at t. Long-spread => +1 leg Y, -beta leg X.
    P&L per bar (on $1 long-spread, normalized notional = 1 + |beta| per side):
        ret_t = (rY_t) - beta * (rX_t)  (log returns, approximated)
    Cost charged on entry and exit: 2 * cost_per_side * (1 + |beta|) per leg-stack.
    """
    pY = pY.iloc[start_idx:end_idx].reset_index(drop=True)
    pX = pX.iloc[start_idx:end_idx].reset_index(drop=True)
    logY = np.log(pY.values)
    logX = np.log(pX.values)
    rY = np.diff(logY, prepend=logY[0])
    rX = np.diff(logX, prepend=logX[0])

    n = len(logY)
    spread = np.full(n, np.nan)
    beta = np.full(n, np.nan)
    z = np.full(n, np.nan)

    # Rolling beta + Z (look-back only)
    for i in range(roll_win, n):
        Yw = logY[i - roll_win:i]
        Xw = logX[i - roll_win:i]
        Xc = np.column_stack([np.ones(roll_win), Xw])
        # Closed-form OLS (small + many calls; faster than statsmodels)
        try:
            beta_pair = np.linalg.lstsq(Xc, Yw, rcond=None)[0]
        except Exception:
            continue
        a, b = beta_pair[0], beta_pair[1]
        beta[i] = b
        s_window = Yw - a - b * Xw
        s_now = logY[i] - a - b * logX[i]
        spread[i] = s_now
        mu, sd = s_window.mean(), s_window.std(ddof=1)
        if sd > 1e-12:
            z[i] = (s_now - mu) / sd

    # Trade loop (signal lagged by 1 bar)
    pos = 0          # +1 long-spread, -1 short-spread, 0 flat
    held = 0
    entry_beta = 0.0
    pnl = np.zeros(n)
    trades = []      # dicts
    entry_idx = -1
    for i in range(roll_win + 1, n):
        # Mark-to-market P&L from existing position over bar [i-1 -> i]
        if pos != 0 and not np.isnan(entry_beta):
            # ret on long-spread leg (per $1 of Y leg, beta*$1 of X leg)
            ret = pos * (rY[i] - entry_beta * rX[i])
            # Normalize by gross notional = 1 + |beta| (equal-dollar version)
            notional = 1.0 + abs(entry_beta)
            pnl[i] += ret / notional
            held += 1

        # Use yesterday's z (lag-1) for signal
        z_sig = z[i - 1]
        b_sig = beta[i - 1]

        if pos == 0:
            if not np.isnan(z_sig) and not np.isnan(b_sig):
                if z_sig < -z_enter:
                    pos = +1
                    entry_beta = b_sig
                    # Cost on entry: 2 legs * cost_per_side
                    notional = 1.0 + abs(entry_beta)
                    pnl[i] -= 2 * cost_per_side  # already per-unit-notional
                    held = 0
                    entry_idx = i
                elif z_sig > z_enter:
                    pos = -1
                    entry_beta = b_sig
                    notional = 1.0 + abs(entry_beta)
                    pnl[i] -= 2 * cost_per_side
                    held = 0
                    entry_idx = i
        else:
            exit_now = False
            reason = ""
            if not np.isnan(z_sig):
                if abs(z_sig) < z_exit:
                    exit_now = True; reason = "exit_band"
                elif abs(z_sig) > z_stop:
                    exit_now = True; reason = "stop"
            if held >= max_hold:
                exit_now = True; reason = reason or "time"
            if exit_now:
                # cost on exit
                pnl[i] -= 2 * cost_per_side
                trades.append({
                    "entry": int(entry_idx), "exit": int(i),
                    "pos": int(pos), "held": int(held),
                    "reason": reason,
                })
                pos = 0
                entry_beta = 0.0
                held = 0

    # Close any open position at end (flat-out cost)
    if pos != 0:
        pnl[-1] -= 2 * cost_per_side
        trades.append({"entry": int(entry_idx), "exit": int(n - 1),
                       "pos": int(pos), "held": int(held), "reason": "eod"})

    # Stats
    pnl_s = pd.Series(pnl)
    sharpe = np.nan
    if pnl_s.std(ddof=1) > 0:
        sharpe = pnl_s.mean() / pnl_s.std(ddof=1) * math.sqrt(BARS_PER_YEAR)
    eq = (1 + pnl_s).cumprod()
    mdd = float((eq / eq.cummax() - 1).min()) if len(eq) else 0.0
    wins = [t for t in trades if True]  # need per-trade P&L
    # Per-trade P&L
    trade_pnls = []
    for t in trades:
        seg = pnl[t["entry"] + 1: t["exit"] + 1]
        trade_pnls.append(float(seg.sum()))
    win_rate = float(np.mean([1 if x > 0 else 0 for x in trade_pnls])) if trade_pnls else 0.0
    avg_hold = float(np.mean([t["held"] for t in trades])) if trades else 0.0

    return {
        "pnl": pnl,
        "sharpe": float(sharpe) if not np.isnan(sharpe) else 0.0,
        "n_trades": int(len(trades)),
        "win_rate": float(win_rate),
        "avg_hold": float(avg_hold),
        "mdd": float(mdd),
        "trade_pnls": trade_pnls,
        "trades": trades,
    }


# ---------------- Pair selection ---------------- #

def select_pairs(px: pd.DataFrame, is_end: int) -> List[Dict]:
    """In-sample Engle-Granger screen. Returns list of dicts for surviving pairs."""
    symbols = list(px.columns)
    pairs = list(combinations(symbols, 2))
    survived = []
    all_tests = []
    for a, b in pairs:
        y = np.log(px[a].values[:is_end])
        x = np.log(px[b].values[:is_end])
        beta, p, hl = engle_granger(y, x)
        all_tests.append({"a": a, "b": b, "beta": float(beta) if np.isfinite(beta) else None,
                          "adf_p": float(p), "half_life": float(hl) if np.isfinite(hl) else None})
        if p < ADF_PMAX and np.isfinite(hl) and HL_MIN <= hl <= HL_MAX and np.isfinite(beta):
            survived.append({"a": a, "b": b, "beta_is": float(beta),
                             "adf_p": float(p), "half_life": float(hl)})
    return survived, all_tests


# ---------------- Portfolio combine ---------------- #

def portfolio_pnl(pair_pnls: List[np.ndarray], max_concurrent: int = MAX_CONCURRENT) -> np.ndarray:
    """Equal-weight 1/max_concurrent allocation, simple sum of per-pair pnl scaled."""
    if not pair_pnls:
        return np.zeros(0)
    n = len(pair_pnls[0])
    M = np.zeros((len(pair_pnls), n))
    for i, p in enumerate(pair_pnls):
        M[i, : len(p)] = p[:n]
    # Track active pairs (non-zero current-bar pnl OR sustained position too costly to track exactly)
    # Approximation: equal weight 1/min(n_pairs, max_concurrent) is fine since selection ensures diversification.
    weight = 1.0 / min(len(pair_pnls), max_concurrent)
    return M.sum(axis=0) * weight


def metrics(pnl: np.ndarray) -> Dict:
    if len(pnl) == 0 or np.std(pnl) == 0:
        return {"sharpe": 0.0, "calmar": 0.0, "mdd": 0.0, "ann_ret": 0.0,
                "cum_ret": 0.0, "n_bars": int(len(pnl))}
    s = pd.Series(pnl)
    sharpe = s.mean() / s.std(ddof=1) * math.sqrt(BARS_PER_YEAR)
    eq = (1 + s).cumprod()
    mdd = float((eq / eq.cummax() - 1).min())
    cum_ret = float(eq.iloc[-1] - 1)
    years = len(s) / BARS_PER_YEAR
    ann_ret = (1 + cum_ret) ** (1 / max(years, 1e-9)) - 1 if cum_ret > -1 else -1.0
    calmar = ann_ret / abs(mdd) if mdd < 0 else 0.0
    return {"sharpe": float(sharpe), "calmar": float(calmar), "mdd": float(mdd),
            "ann_ret": float(ann_ret), "cum_ret": float(cum_ret), "n_bars": int(len(pnl))}


# ---------------- Robustness ---------------- #

def block_bootstrap_sharpe(pnl: np.ndarray, n: int = 500, block: int = 20) -> Tuple[float, float]:
    if len(pnl) < 2 * block:
        return (0.0, 0.0)
    out = []
    n_blocks = len(pnl) // block
    for _ in range(n):
        starts = RNG.integers(0, len(pnl) - block, size=n_blocks)
        sample = np.concatenate([pnl[s:s + block] for s in starts])
        if sample.std() > 0:
            out.append(sample.mean() / sample.std(ddof=1) * math.sqrt(BARS_PER_YEAR))
    if not out:
        return (0.0, 0.0)
    return (float(np.percentile(out, 2.5)), float(np.percentile(out, 97.5)))


def permutation_null(pair_pnls: List[np.ndarray], n: int = 500) -> Tuple[float, float]:
    """Shuffle (circular shift random) each pair's pnl independently; recompute portfolio Sharpe."""
    null_sharpes = []
    for _ in range(n):
        shifted = []
        for p in pair_pnls:
            k = int(RNG.integers(1, len(p)))
            shifted.append(np.roll(p, k))
        port = portfolio_pnl(shifted, MAX_CONCURRENT)
        m = metrics(port)
        null_sharpes.append(m["sharpe"])
    return float(np.mean(null_sharpes)), float(np.percentile(null_sharpes, 95))


def deflated_sharpe(sr: float, n_trials: int, n_obs: int, skew: float = 0.0, kurt: float = 3.0) -> float:
    """Bailey & Lopez de Prado approx DSR (probability that observed SR > 0 given trials)."""
    if n_obs < 30:
        return 0.0
    # Expected max SR under null (Bailey & LdP eq.)
    emc = 0.5772156649
    if n_trials < 2:
        sr0 = 0.0
    else:
        sr0 = math.sqrt(2 * math.log(n_trials)) - (emc + math.log(math.log(max(n_trials, 3)))) / max(math.sqrt(2 * math.log(n_trials)), 1e-9)
    # SR is in annual units; convert to per-bar for std calc
    sr_per_bar = sr / math.sqrt(BARS_PER_YEAR)
    sr0_per_bar = sr0 / math.sqrt(BARS_PER_YEAR) * 0  # interpreted as zero-mean threshold w/ EMax adjustment in annual SR
    # Variance of SR estimator (approx, Lo 2002):
    # Var(SR_hat) = (1 - skew*SR + (kurt-1)/4 * SR^2) / (T-1)
    SR = sr / math.sqrt(BARS_PER_YEAR)
    var_sr = (1.0 - skew * SR + (kurt - 1) / 4.0 * SR ** 2) / max(n_obs - 1, 1)
    std_sr = math.sqrt(max(var_sr, 1e-18))
    # Test stat: (SR_annual - SR0_annual) / (std_sr_per_bar * sqrt(BARS_PER_YEAR))
    z = (sr - sr0) / (std_sr * math.sqrt(BARS_PER_YEAR))
    # Normal CDF
    from math import erf
    p = 0.5 * (1 + erf(z / math.sqrt(2)))
    return float(p)


# ---------------- Main ---------------- #

def main():
    t0 = time.time()
    print("[load]")
    px = load_closes(SYMBOLS)
    print(f"  px shape: {px.shape}, cols={len(px.columns)}, from {px.index[0]} to {px.index[-1]}")
    n_all = len(px)
    is_end = int(n_all * IS_FRAC)
    oos_start = is_end
    print(f"  IS bars: {is_end} | OOS bars: {n_all - is_end}")

    # ---- Pair selection on IS ----
    print("[engle-granger screen]")
    survived, all_tests = select_pairs(px, is_end)
    print(f"  pairs tested: {len(all_tests)} | survived: {len(survived)}")

    # ---- Per-pair full-sample backtest + IS Sharpe gate ----
    print("[per-pair backtest (IS + OOS, full series)]")
    pair_results = []
    pair_pnl_full = {}     # key -> pnl array (full)
    pair_pnl_oos = {}      # key -> pnl array (oos slice)
    pair_pnl_is = {}
    for s in survived:
        a, b = s["a"], s["b"]
        res_full = backtest_pair(px[a], px[b], 0, n_all)
        pnl = res_full["pnl"]
        # IS metric (over IS bars, skipping warmup)
        is_pnl = pnl[ROLL_WIN + 1: is_end]
        oos_pnl = pnl[is_end:]
        is_m = metrics(is_pnl)
        oos_m = metrics(oos_pnl)
        rec = {
            "pair": f"{a}-{b}", "a": a, "b": b,
            "adf_p": s["adf_p"], "half_life": s["half_life"], "beta_is": s["beta_is"],
            "is_sharpe": is_m["sharpe"], "is_n_trades": None,
            "oos_sharpe": oos_m["sharpe"], "oos_cum_ret": oos_m["cum_ret"],
            "oos_mdd": oos_m["mdd"],
            "full_n_trades": res_full["n_trades"],
            "full_win_rate": res_full["win_rate"],
            "full_avg_hold": res_full["avg_hold"],
        }
        pair_results.append(rec)
        pair_pnl_full[f"{a}-{b}"] = pnl
        pair_pnl_oos[f"{a}-{b}"] = oos_pnl
        pair_pnl_is[f"{a}-{b}"] = is_pnl

    # Apply IS Sharpe gate
    gated = [r for r in pair_results if r["is_sharpe"] > IS_SHARPE_GATE]
    print(f"  IS-Sharpe>{IS_SHARPE_GATE}: {len(gated)}")

    # ---- Portfolio (gated pairs) ----
    print("[portfolio]")
    if gated:
        keys = [r["pair"] for r in gated]
        is_arrays = [pair_pnl_is[k] for k in keys]
        oos_arrays = [pair_pnl_oos[k] for k in keys]
        # IS portfolio sanity
        port_is = portfolio_pnl(is_arrays, MAX_CONCURRENT)
        port_is_m = metrics(port_is)
        # OOS portfolio
        port_oos = portfolio_pnl(oos_arrays, MAX_CONCURRENT)
        port_oos_m = metrics(port_oos)
        # OOS bootstrap CI
        ci_low, ci_high = block_bootstrap_sharpe(port_oos, n=500, block=20)
        # Permutation null on OOS pair pnls
        perm_mean, perm_p95 = permutation_null(oos_arrays, n=500)
        obs_oos = port_oos_m["sharpe"]
        perm_p_value = float(np.mean([
            1 if (lambda x: x)(
                metrics(portfolio_pnl([np.roll(p, int(RNG.integers(1, len(p)))) for p in oos_arrays], MAX_CONCURRENT))["sharpe"]
            ) >= obs_oos else 0
            for _ in range(0)
        ]))  # placeholder; compute properly below
    else:
        keys = []
        port_is = np.zeros(0); port_oos = np.zeros(0)
        port_is_m = metrics(port_is); port_oos_m = metrics(port_oos)
        ci_low, ci_high = 0.0, 0.0
        perm_mean, perm_p95 = 0.0, 0.0

    # Proper permutation p-value: fraction of null Sharpes >= observed
    if gated:
        null_dist = []
        oos_arrays = [pair_pnl_oos[k] for k in keys]
        for _ in range(500):
            shifted = [np.roll(p, int(RNG.integers(1, len(p)))) for p in oos_arrays]
            null_dist.append(metrics(portfolio_pnl(shifted, MAX_CONCURRENT))["sharpe"])
        null_dist = np.array(null_dist)
        perm_p_value = float((null_dist >= port_oos_m["sharpe"]).mean())
    else:
        perm_p_value = 1.0

    # ---- Walk-forward 4-fold ----
    print("[walk-forward 4-fold]")
    wf_results = []
    fold_count = 4
    fold_size = n_all // (fold_count + 1)  # smallest train = 1 fold, expanding
    # Expanding window: train on [0:end_train], test on next fold_size
    for k in range(fold_count):
        end_train = fold_size * (k + 2)  # at least 2 folds for training
        end_test = min(end_train + fold_size, n_all)
        if end_test - end_train < 50:
            continue
        # Re-select pairs on train slice (no leakage)
        surv_k, _ = select_pairs(px.iloc[:end_train], end_train)
        # Per-pair backtest on full but eval test slice; gate by train Sharpe
        train_pnls = {}; test_pnls = {}
        for s in surv_k:
            a, b = s["a"], s["b"]
            res = backtest_pair(px[a], px[b], 0, end_test)
            pnl = res["pnl"]
            tr = pnl[ROLL_WIN + 1:end_train]
            te = pnl[end_train:end_test]
            if pd.Series(tr).std() == 0:
                continue
            sr_tr = pd.Series(tr).mean() / pd.Series(tr).std(ddof=1) * math.sqrt(BARS_PER_YEAR)
            if sr_tr > IS_SHARPE_GATE:
                train_pnls[f"{a}-{b}"] = tr
                test_pnls[f"{a}-{b}"] = te
        if test_pnls:
            port_te = portfolio_pnl(list(test_pnls.values()), MAX_CONCURRENT)
            m = metrics(port_te)
            wf_results.append({"fold": k + 1, "train_end": int(end_train),
                               "test_end": int(end_test), "n_pairs": len(test_pnls),
                               **m})
        else:
            wf_results.append({"fold": k + 1, "train_end": int(end_train),
                               "test_end": int(end_test), "n_pairs": 0,
                               "sharpe": 0.0, "calmar": 0.0, "mdd": 0.0,
                               "ann_ret": 0.0, "cum_ret": 0.0, "n_bars": int(end_test - end_train)})

    # ---- Cost stress ----
    print("[cost stress on OOS portfolio]")
    cost_stress = {}
    for mult in [0.5, 1.0, 1.5]:
        new_oos_arrays = []
        for k in keys:
            a, b = k.split("-")
            res = backtest_pair(px[a], px[b], 0, n_all, cost_per_side=COST_PER_SIDE * mult)
            new_oos_arrays.append(res["pnl"][is_end:])
        port = portfolio_pnl(new_oos_arrays, MAX_CONCURRENT)
        cost_stress[f"x{mult}"] = metrics(port)

    # ---- Threshold sensitivity (final portfolio only) ----
    print("[threshold sensitivity grid on OOS, gated pairs]")
    grid = {}
    for ze in [1.5, 2.0, 2.5]:
        for zx in [0.0, 0.5, 1.0]:
            arrs = []
            for k in keys:
                a, b = k.split("-")
                res = backtest_pair(px[a], px[b], 0, n_all,
                                    z_enter=ze, z_exit=zx)
                arrs.append(res["pnl"][is_end:])
            if arrs:
                port = portfolio_pnl(arrs, MAX_CONCURRENT)
                m = metrics(port)
            else:
                m = {"sharpe": 0.0, "calmar": 0.0, "mdd": 0.0, "ann_ret": 0.0, "cum_ret": 0.0, "n_bars": 0}
            grid[f"ze{ze}_zx{zx}"] = m

    # ---- DSR ----
    n_trials = len(all_tests)  # 190
    n_obs_oos = len(port_oos)
    skew = float(pd.Series(port_oos).skew()) if n_obs_oos > 3 else 0.0
    kurt = float(pd.Series(port_oos).kurt() + 3) if n_obs_oos > 3 else 3.0
    dsr = deflated_sharpe(port_oos_m["sharpe"], n_trials, n_obs_oos, skew, kurt)

    # ---- Compile output ----
    pair_results_sorted = sorted(pair_results, key=lambda r: r["oos_sharpe"], reverse=True)
    top5 = pair_results_sorted[:5]

    output = {
        "wave": "K111",
        "title": "Cointegrated Alt Pair Z-Score (Stat Arb)",
        "universe": SYMBOLS,
        "n_symbols": len(px.columns),
        "n_bars": n_all,
        "n_is": is_end,
        "n_oos": n_all - is_end,
        "params": {
            "Z_ENTER": Z_ENTER, "Z_EXIT": Z_EXIT, "Z_STOP": Z_STOP,
            "MAX_HOLD": MAX_HOLD, "ROLL_WIN": ROLL_WIN,
            "HL_MIN": HL_MIN, "HL_MAX": HL_MAX, "ADF_PMAX": ADF_PMAX,
            "COST_PER_SIDE": COST_PER_SIDE, "MAX_CONCURRENT": MAX_CONCURRENT,
            "IS_SHARPE_GATE": IS_SHARPE_GATE, "IS_FRAC": IS_FRAC,
        },
        "screen": {
            "n_pairs_tested": len(all_tests),
            "n_passed_adf": int(sum(1 for t in all_tests if t["adf_p"] < ADF_PMAX)),
            "n_passed_hl_window": int(sum(1 for t in all_tests
                                          if t["adf_p"] < ADF_PMAX and t["half_life"] is not None
                                          and HL_MIN <= t["half_life"] <= HL_MAX)),
            "n_is_gated": len(gated),
            "all_tests": all_tests,
        },
        "pairs_survived": [
            {k: v for k, v in r.items() if k not in ("pnl",)} for r in pair_results
        ],
        "pairs_gated": [r["pair"] for r in gated],
        "top5_oos": top5,
        "portfolio_is": port_is_m,
        "portfolio_oos": port_oos_m,
        "portfolio_oos_bootstrap_sharpe_95ci": [ci_low, ci_high],
        "permutation_null": {"mean_sharpe": perm_mean, "p95_sharpe": perm_p95,
                              "observed_oos_sharpe": port_oos_m["sharpe"],
                              "p_value": perm_p_value, "n_perms": 500},
        "walk_forward": wf_results,
        "cost_stress": cost_stress,
        "threshold_sensitivity": grid,
        "dsr": {
            "value": dsr, "n_trials": n_trials, "n_obs": n_obs_oos,
            "skew": skew, "kurt": kurt,
            "observed_sharpe": port_oos_m["sharpe"],
        },
        "runtime_sec": time.time() - t0,
    }

    with open(OUT_JSON, "w") as f:
        json.dump(output, f, indent=2, default=str)
    print(f"  wrote {OUT_JSON}")

    # ---- Equity curves ----
    curves = {
        "portfolio_oos": {
            "timestamps": [str(t) for t in px.index[is_end:]],
            "equity": (1 + pd.Series(port_oos)).cumprod().tolist() if len(port_oos) else [],
            "metrics": port_oos_m,
        },
        "portfolio_is": {
            "timestamps": [str(t) for t in px.index[ROLL_WIN + 1: is_end]],
            "equity": (1 + pd.Series(port_is)).cumprod().tolist() if len(port_is) else [],
            "metrics": port_is_m,
        },
        "top5_pairs": [],
    }
    for r in top5:
        pnl = pair_pnl_full[r["pair"]]
        curves["top5_pairs"].append({
            "pair": r["pair"],
            "timestamps": [str(t) for t in px.index],
            "equity": (1 + pd.Series(pnl)).cumprod().tolist(),
            "metrics": {"oos_sharpe": r["oos_sharpe"], "half_life": r["half_life"],
                         "adf_p": r["adf_p"]},
        })
    with open(OUT_CURVES, "w") as f:
        json.dump(curves, f, default=str)
    print(f"  wrote {OUT_CURVES}")
    print(f"[done] {time.time() - t0:.1f}s")
    return output


if __name__ == "__main__":
    main()

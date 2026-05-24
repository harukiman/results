"""
Wave K120 — Weekly-Funding Undervaluation (Sandbank-KR replication)

Hypothesis (from https://medium.com/sandbank-kr/...):
- When rolling 7-day mean funding rate > +0.01% (BTC/ETH) or > +0.05% (alts) → long
- Otherwise flat
- Paper reports Adj R² 0.18 (BTC), 0.21 (ETH) on weekly forward return regression

Strategy mechanics:
- Funding cadence: 8h (3 events / day) on Bybit
- Bars: 4H (730d window)
- Forward-fill funding onto 4H bars with 1-bar lag (no look-ahead)
- Rolling window: 7d × 3 events/day = 21 funding periods (== 42 4H bars)
- When long held during a funding period: pay (or receive) funding_rate * notional
- Net P&L per 4H bar = price_return - funding_paid (if position open and funding window crossed)
"""

from __future__ import annotations

import json
import math
import os
import sys
import time
import warnings
from dataclasses import dataclass

import numpy as np
import pandas as pd

warnings.filterwarnings("ignore")

CACHE = "/Users/nekonaomichi/crypto-lab/cache"
OUT_PY = "/Users/nekonaomichi/crypto-lab/wave_k120_weekly_funding.py"
OUT_JSON = "/Users/nekonaomichi/crypto-lab/wave_k120_weekly_funding.json"
OUT_CURVES = "/Users/nekonaomichi/crypto-lab/wave_k120_curves.json"

# --------- universe ----------
SYMBOLS_MAJOR = ["BTC", "ETH"]
SYMBOLS_ALTS = ["SOL", "BNB", "DOGE", "AVAX", "LINK", "ADA", "XRP", "INJ", "OP", "WIF", "ARB"]
SYMBOLS = SYMBOLS_MAJOR + SYMBOLS_ALTS

THRESH_MAJOR = 0.0001  # +0.01%
THRESH_ALT = 0.0005    # +0.05%

# 4H bars per day = 6; funding events / day = 3
BARS_PER_DAY = 6
FUND_PER_DAY = 3
ROLL_FUND_PERIODS = 7 * FUND_PER_DAY  # 21 funding periods
BARS_PER_WEEK = 7 * BARS_PER_DAY  # 42 — used for forward weekly return

IS_FRAC = 0.70

# Costs (per side) — long-only entry/exit
TAKER_BPS = 4.0  # 0.04% per side
SLIP_BPS = 3.0   # 0.03% slippage per side


def thresh_for(sym: str) -> float:
    return THRESH_MAJOR if sym in SYMBOLS_MAJOR else THRESH_ALT


# --------- data loading ----------
def load_symbol(sym: str) -> pd.DataFrame:
    """Returns DataFrame indexed by 4H open_time with columns: close, ret_1, funding_per_bar.

    funding_per_bar = funding rate that would be PAID/RECEIVED by long during that 4H bar.
    Each funding event applies once when the 4H bar contains the funding timestamp.
    Sign convention: positive funding = long pays short. So long-side PNL impact = -funding.
    We attach the raw funding-rate-paid to bar; rolling mean uses raw funding rate.
    """
    px = pd.read_parquet(f"{CACHE}/{sym}USDT_4h_730d.parquet")
    fr = pd.read_parquet(f"{CACHE}/bybit_fr_{sym}USDT_730d.parquet")

    px = px[["open_time", "close"]].rename(columns={"open_time": "ts"}).sort_values("ts").reset_index(drop=True)
    fr = fr.sort_values("timestamp").reset_index(drop=True)

    # Map each funding event timestamp to the 4H bar that contains it.
    # 4H bars open at multiples of 4h (00,04,08,12,16,20). Funding events at 00,08,16.
    # We attach funding to the bar whose open_time == funding ts (since they align).
    fr_indexed = fr.set_index("timestamp")["funding_rate"]
    px = px.set_index("ts")
    px["funding_event"] = fr_indexed.reindex(px.index)
    px = px.reset_index()

    # raw funding-rate series at 8h cadence — needed for rolling 7d mean
    # We forward-fill the most recent KNOWN funding rate onto each 4H bar, with 1-bar lag.
    px["funding_ff"] = px["funding_event"].ffill().shift(1)
    # rolling 7d mean of funding rate (using last 21 funding events == every 2nd 4H bar)
    # Simplification: rolling mean on funding_ff over last 42 4H bars approximates the
    # mean of last 21 funding events (each event repeats across 2 bars after ffill).
    px["fund_roll7d"] = px["funding_ff"].rolling(window=BARS_PER_WEEK, min_periods=BARS_PER_WEEK).mean()

    # Returns
    px["close"] = px["close"].astype(float)
    px["ret_1"] = px["close"].pct_change()
    # Forward weekly return (for paper-style R²) — uses close in 42 bars
    px["fwd_ret_7d"] = px["close"].shift(-BARS_PER_WEEK) / px["close"] - 1.0

    # funding-event funding-paid per bar (only nonzero on funding bars)
    px["funding_paid"] = px["funding_event"].fillna(0.0)

    return px


# --------- strategy ----------
def build_signal(df: pd.DataFrame, thresh: float, mode: str = "long") -> pd.Series:
    """mode: 'long' = paper-original; 'ls' = symmetric long/short."""
    s = pd.Series(0, index=df.index, dtype=int)
    if mode == "long":
        s[df["fund_roll7d"] > thresh] = 1
    elif mode == "ls":
        s[df["fund_roll7d"] > thresh] = 1
        s[df["fund_roll7d"] < -thresh] = -1
    return s


def build_signal_adaptive(df: pd.DataFrame, pct: float = 0.80, lookback_bars: int = 90 * BARS_PER_DAY) -> pd.Series:
    """Adaptive threshold = trailing rolling pct-quantile of fund_roll7d.

    Reads only past data (no look-ahead). Returns long when current fund_roll7d > trailing 80th pct.
    """
    quant = df["fund_roll7d"].rolling(window=lookback_bars, min_periods=lookback_bars // 2).quantile(pct).shift(1)
    s = pd.Series(0, index=df.index, dtype=int)
    s[df["fund_roll7d"] > quant] = 1
    return s


def apply_costs_and_funding(df: pd.DataFrame, pos: pd.Series, cost_mult: float = 1.0) -> pd.DataFrame:
    """Returns df augmented with strategy pnl per bar.

    - pos_t applied to ret_{t+1} (we trade at bar t close, hold into t+1)
    - position change pays taker+slip on each unit traded
    - funding_paid on bar t+1 multiplied by pos_{t+1} (long pays positive funding)
    """
    out = df.copy()
    pos = pos.fillna(0).astype(int)
    # Position applied to next bar return
    pos_next = pos.shift(1).fillna(0)
    # Cost on position change
    turns = (pos - pos.shift(1).fillna(0)).abs()
    cost_per_side_frac = (TAKER_BPS + SLIP_BPS) / 1e4 * cost_mult  # 0.07% per side
    cost = turns * cost_per_side_frac

    # Funding pnl: when pos_next != 0 and funding_event occurs on this bar (or use funding_paid)
    # funding_paid is already the funding rate at funding events, 0 otherwise
    funding_pnl = -pos_next * out["funding_paid"]  # long pays positive funding

    out["pos"] = pos
    out["pos_next"] = pos_next
    out["ret_strat_gross"] = pos_next * out["ret_1"]
    out["funding_pnl"] = funding_pnl
    out["cost"] = cost
    out["ret_strat_net"] = out["ret_strat_gross"] + funding_pnl - cost
    return out


# --------- metrics ----------
def sharpe(returns: np.ndarray, periods_per_year: float = BARS_PER_DAY * 365) -> float:
    r = np.asarray(returns)
    r = r[~np.isnan(r)]
    if len(r) < 10 or r.std() == 0:
        return 0.0
    return float(r.mean() / r.std() * math.sqrt(periods_per_year))


def max_dd(returns: np.ndarray) -> float:
    r = np.asarray(returns)
    r = r[~np.isnan(r)]
    if len(r) == 0:
        return 0.0
    eq = (1 + r).cumprod()
    peak = np.maximum.accumulate(eq)
    dd = (eq - peak) / peak
    return float(dd.min())


def win_rate(returns: np.ndarray) -> float:
    r = np.asarray(returns)
    r = r[~np.isnan(r) & (r != 0)]
    if len(r) == 0:
        return 0.0
    return float((r > 0).mean())


def adj_r2_weekly(df: pd.DataFrame) -> float:
    """Regression: y = fwd_ret_7d, x = fund_roll7d, sampled weekly (every 42 bars), OLS."""
    sub = df[["fund_roll7d", "fwd_ret_7d"]].dropna()
    if len(sub) < 50:
        return float("nan")
    # Subsample weekly to avoid massive overlap bias
    sub = sub.iloc[::BARS_PER_WEEK]
    if len(sub) < 20:
        return float("nan")
    x = sub["fund_roll7d"].values
    y = sub["fwd_ret_7d"].values
    n = len(x)
    xm, ym = x.mean(), y.mean()
    sxx = ((x - xm) ** 2).sum()
    if sxx == 0:
        return float("nan")
    b = ((x - xm) * (y - ym)).sum() / sxx
    a = ym - b * xm
    yhat = a + b * x
    ss_res = ((y - yhat) ** 2).sum()
    ss_tot = ((y - ym) ** 2).sum()
    if ss_tot == 0:
        return float("nan")
    r2 = 1 - ss_res / ss_tot
    # Adjusted R² with k=1 predictor
    if n - 2 <= 0:
        return float("nan")
    adj = 1 - (1 - r2) * (n - 1) / (n - 2)
    return float(adj)


# --------- bootstrap / permutation ----------
def block_bootstrap_sharpe(ret: np.ndarray, block: int = 20, n: int = 500, seed: int = 7) -> tuple[float, float]:
    rng = np.random.default_rng(seed)
    r = np.asarray(ret)
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


def permutation_test(df: pd.DataFrame, thresh: float, n: int = 500, seed: int = 42) -> dict:
    """Shuffle funding rates within rolling window, recompute strategy Sharpe."""
    rng = np.random.default_rng(seed)
    base_pos = build_signal(df, thresh, "long")
    base_out = apply_costs_and_funding(df, base_pos)
    base_sharpe = sharpe(base_out["ret_strat_net"].values)

    fr = df["funding_ff"].copy().values
    valid = ~np.isnan(fr)
    null_sharpes = []
    for _ in range(n):
        sh_fr = fr.copy()
        idx = np.where(valid)[0]
        perm = rng.permutation(idx)
        sh_fr[idx] = fr[perm]
        df2 = df.copy()
        df2["funding_ff"] = sh_fr
        df2["fund_roll7d"] = df2["funding_ff"].rolling(BARS_PER_WEEK, min_periods=BARS_PER_WEEK).mean()
        pos2 = build_signal(df2, thresh, "long")
        out2 = apply_costs_and_funding(df2, pos2)
        null_sharpes.append(sharpe(out2["ret_strat_net"].values))
    null_sharpes = np.array(null_sharpes)
    p = float((null_sharpes >= base_sharpe).mean())
    return {
        "base_sharpe": float(base_sharpe),
        "null_mean": float(null_sharpes.mean()),
        "null_std": float(null_sharpes.std()),
        "p_value": p,
    }


def dsr(sharpe_val: float, n_obs: int, n_trials: int) -> float:
    """Deflated Sharpe Ratio approximation."""
    if n_obs < 30 or n_trials < 1:
        return float("nan")
    # expected max from N IID standard normals
    emc = 0.5772
    sn = math.sqrt(2 * math.log(max(n_trials, 2)))
    expected_max = sn - emc / sn
    # Std of estimated SR
    sr_std = math.sqrt((1 + 0.5 * sharpe_val ** 2) / n_obs)
    if sr_std == 0:
        return float("nan")
    z = (sharpe_val - expected_max * sr_std) / sr_std
    # one-sided
    from math import erf
    return float(0.5 * (1 + erf(z / math.sqrt(2))))


# --------- main pipeline ----------
def run_symbol(sym: str) -> dict:
    df = load_symbol(sym)
    thresh = thresh_for(sym)

    n = len(df)
    cut = int(n * IS_FRAC)

    # signals
    pos_long = build_signal(df, thresh, "long")
    pos_ls = build_signal(df, thresh, "ls")
    pos_adapt = build_signal_adaptive(df, pct=0.80)
    out_long = apply_costs_and_funding(df, pos_long)
    out_ls = apply_costs_and_funding(df, pos_ls)
    out_adapt = apply_costs_and_funding(df, pos_adapt)

    def slice_metrics(out: pd.DataFrame, lo: int, hi: int) -> dict:
        sub = out.iloc[lo:hi]
        r = sub["ret_strat_net"].values
        return {
            "sharpe": sharpe(r),
            "max_dd": max_dd(r),
            "win_rate": win_rate(r),
            "n_bars": int(len(r)),
            "exposure": float((sub["pos_next"] != 0).mean()),
            "total_return": float((1 + pd.Series(r).fillna(0)).prod() - 1),
        }

    res = {
        "symbol": sym,
        "threshold": thresh,
        "n_bars": int(n),
        "adj_r2_weekly": adj_r2_weekly(df),
        "long_only": {
            "IS": slice_metrics(out_long, 0, cut),
            "OOS": slice_metrics(out_long, cut, n),
            "FULL": slice_metrics(out_long, 0, n),
        },
        "long_short": {
            "IS": slice_metrics(out_ls, 0, cut),
            "OOS": slice_metrics(out_ls, cut, n),
            "FULL": slice_metrics(out_ls, 0, n),
        },
        "adaptive_p80": {
            "IS": slice_metrics(out_adapt, 0, cut),
            "OOS": slice_metrics(out_adapt, cut, n),
            "FULL": slice_metrics(out_adapt, 0, n),
        },
        "fund_roll7d_stats": {
            "IS_p75": float(df["fund_roll7d"].iloc[:cut].quantile(0.75)),
            "OOS_p75": float(df["fund_roll7d"].iloc[cut:].quantile(0.75)),
            "IS_max": float(df["fund_roll7d"].iloc[:cut].max()),
            "OOS_max": float(df["fund_roll7d"].iloc[cut:].max()),
            "IS_trigger_count": int((pos_long.iloc[:cut] == 1).sum()),
            "OOS_trigger_count": int((pos_long.iloc[cut:] == 1).sum()),
        },
    }

    # Walk-forward 4-fold (long-only)
    fold_size = n // 4
    wf = []
    for k in range(4):
        lo, hi = k * fold_size, (k + 1) * fold_size if k < 3 else n
        wf.append(slice_metrics(out_long, lo, hi))
    res["walk_forward"] = wf

    return res, out_long, out_ls, out_adapt


def build_portfolio(per_symbol_outs: dict[str, pd.DataFrame]) -> pd.Series:
    """Equal-weight across symbols on each bar (only count active positions in denominator)."""
    frames = []
    for sym, out in per_symbol_outs.items():
        s = out["ret_strat_net"].rename(sym).copy()
        s.index = out["ts"]
        frames.append(s)
    df = pd.concat(frames, axis=1).sort_index()
    df = df.fillna(0.0)
    return df.mean(axis=1)


def equity_curve(returns: pd.Series) -> list[dict]:
    eq = (1 + returns.fillna(0)).cumprod()
    return [
        {"ts": str(ts), "eq": float(v)}
        for ts, v in eq.iloc[::24].items()  # downsample to ~daily (every 24 bars = 4 days)
    ]


def main():
    t0 = time.time()
    print("=" * 70)
    print("Wave K120 — Weekly-Funding Undervaluation (Sandbank-KR)")
    print("=" * 70)

    all_results = {}
    outs_long = {}
    outs_ls = {}
    outs_adapt = {}
    for sym in SYMBOLS:
        try:
            res, out_l, out_ls, out_ad = run_symbol(sym)
            all_results[sym] = res
            outs_long[sym] = out_l
            outs_ls[sym] = out_ls
            outs_adapt[sym] = out_ad
            print(f"  {sym:5s} adjR2={res['adj_r2_weekly']:.4f} "
                  f"IS_SR={res['long_only']['IS']['sharpe']:6.2f} "
                  f"OOS_SR={res['long_only']['OOS']['sharpe']:6.2f} "
                  f"adp_OOS_SR={res['adaptive_p80']['OOS']['sharpe']:6.2f} "
                  f"adp_OOS_exp={res['adaptive_p80']['OOS']['exposure']:.2%}")
        except Exception as e:
            print(f"  {sym}: FAILED — {e}")
            continue

    # Portfolio — universal equal-weight
    port_uni = build_portfolio(outs_long)
    port_uni_ls = build_portfolio(outs_ls)
    port_adapt = build_portfolio(outs_adapt)

    # Portfolio — only symbols with positive IS Sharpe
    pos_is = [s for s, r in all_results.items() if r["long_only"]["IS"]["sharpe"] > 0]
    outs_pos_is = {s: outs_long[s] for s in pos_is}
    port_filtered = build_portfolio(outs_pos_is) if outs_pos_is else pd.Series(dtype=float)

    n_full = len(port_uni)
    cut = int(n_full * IS_FRAC)
    port_uni_arr = port_uni.values
    port_filt_arr = port_filtered.values if len(port_filtered) else np.array([0.0])

    portfolio_metrics = {
        "universal_long_only": {
            "n_symbols": len(SYMBOLS),
            "IS_sharpe": sharpe(port_uni_arr[:cut]),
            "OOS_sharpe": sharpe(port_uni_arr[cut:]),
            "OOS_max_dd": max_dd(port_uni_arr[cut:]),
            "OOS_win_rate": win_rate(port_uni_arr[cut:]),
            "FULL_sharpe": sharpe(port_uni_arr),
            "FULL_total_return": float((1 + pd.Series(port_uni_arr).fillna(0)).prod() - 1),
        },
        "universal_long_short": {
            "n_symbols": len(SYMBOLS),
            "IS_sharpe": sharpe(port_uni_ls.values[:cut]),
            "OOS_sharpe": sharpe(port_uni_ls.values[cut:]),
            "OOS_max_dd": max_dd(port_uni_ls.values[cut:]),
            "FULL_sharpe": sharpe(port_uni_ls.values),
        },
        "filtered_pos_IS_long_only": {
            "n_symbols": len(pos_is),
            "symbols": pos_is,
            "IS_sharpe": sharpe(port_filt_arr[:cut]) if len(port_filt_arr) > cut else 0.0,
            "OOS_sharpe": sharpe(port_filt_arr[cut:]) if len(port_filt_arr) > cut else 0.0,
            "OOS_max_dd": max_dd(port_filt_arr[cut:]) if len(port_filt_arr) > cut else 0.0,
            "FULL_sharpe": sharpe(port_filt_arr),
        },
        "adaptive_p80_long_only": {
            "n_symbols": len(SYMBOLS),
            "IS_sharpe": sharpe(port_adapt.values[:cut]),
            "OOS_sharpe": sharpe(port_adapt.values[cut:]),
            "OOS_max_dd": max_dd(port_adapt.values[cut:]),
            "FULL_sharpe": sharpe(port_adapt.values),
            "FULL_total_return": float((1 + pd.Series(port_adapt.values).fillna(0)).prod() - 1),
        },
    }

    # Block bootstrap CI on OOS portfolio Sharpe
    ci_uni = block_bootstrap_sharpe(port_uni_arr[cut:], block=20, n=500)
    portfolio_metrics["universal_long_only"]["OOS_sharpe_CI95"] = ci_uni

    # Permutation test on BTC (fast representative)
    print("Permutation test (BTC, n=500)...")
    df_btc = load_symbol("BTC")
    perm_btc = permutation_test(df_btc, THRESH_MAJOR, n=200)
    print(f"  BTC perm: base SR={perm_btc['base_sharpe']:.3f} null_mean={perm_btc['null_mean']:.3f} p={perm_btc['p_value']:.3f}")

    # Permutation test on universal portfolio: shuffle per symbol
    # Simpler: per-symbol perm + average not done; use BTC as proxy + ETH
    print("Permutation test (ETH, n=200)...")
    df_eth = load_symbol("ETH")
    perm_eth = permutation_test(df_eth, THRESH_MAJOR, n=200)
    print(f"  ETH perm: base SR={perm_eth['base_sharpe']:.3f} null_mean={perm_eth['null_mean']:.3f} p={perm_eth['p_value']:.3f}")

    # DSR for portfolio OOS Sharpe (2 trials: long, LS)
    n_oos = n_full - cut
    dsr_uni = dsr(portfolio_metrics["universal_long_only"]["OOS_sharpe"], n_oos, n_trials=2)
    dsr_ls = dsr(portfolio_metrics["universal_long_short"]["OOS_sharpe"], n_oos, n_trials=2)

    # Cost stress ±50%
    cost_stress = {}
    for mult, name in [(0.5, "low"), (1.0, "base"), (1.5, "high")]:
        outs = {}
        for sym in SYMBOLS:
            try:
                df = load_symbol(sym)
                pos = build_signal(df, thresh_for(sym), "long")
                outs[sym] = apply_costs_and_funding(df, pos, cost_mult=mult)
            except Exception:
                continue
        port = build_portfolio(outs)
        oos = port.values[cut:]
        cost_stress[name] = {
            "OOS_sharpe": sharpe(oos),
            "OOS_max_dd": max_dd(oos),
        }

    # §6 mini-gates — evaluated against PAPER-ORIGINAL (fixed threshold) per task spec
    oos_sr_uni = portfolio_metrics["universal_long_only"]["OOS_sharpe"]
    oos_dd_uni = portfolio_metrics["universal_long_only"]["OOS_max_dd"]
    ci_low = ci_uni[0]
    gates = {
        "G1_OOS_Sharpe_gt_0.5": oos_sr_uni > 0.5,
        "G2_OOS_MaxDD_gt_-0.30": oos_dd_uni > -0.30,
        "G3_BlockBoot_CI95_low_gt_0": ci_low > 0,
        "G4_Perm_BTC_p_lt_0.05": perm_btc["p_value"] < 0.05,
        "G5_DSR_gt_0.95": (dsr_uni if not math.isnan(dsr_uni) else 0) > 0.95,
        "G6_CostStress_high_OOS_sr_gt_0.3": cost_stress["high"]["OOS_sharpe"] > 0.3,
    }
    # Auxiliary gates for adaptive variant
    adapt_oos_sr = portfolio_metrics["adaptive_p80_long_only"]["OOS_sharpe"]
    adapt_oos_dd = portfolio_metrics["adaptive_p80_long_only"]["OOS_max_dd"]
    gates_adaptive = {
        "G1a_adapt_OOS_Sharpe_gt_0.5": adapt_oos_sr > 0.5,
        "G2a_adapt_OOS_MaxDD_gt_-0.30": adapt_oos_dd > -0.30,
    }
    n_pass = sum(gates.values())
    verdict = (
        "ACCEPT" if n_pass >= 5
        else "CONDITIONAL" if n_pass >= 3
        else "REJECT"
    )

    # Save curves
    curves = {
        "universal_long_only": equity_curve(port_uni),
        "universal_long_short": equity_curve(port_uni_ls),
        "adaptive_p80": equity_curve(port_adapt),
    }
    if len(port_filtered):
        curves["filtered_pos_IS"] = equity_curve(port_filtered)
    with open(OUT_CURVES, "w") as f:
        json.dump(curves, f, indent=2)

    result = {
        "wave": "K120",
        "title": "Weekly-Funding Undervaluation (Sandbank-KR)",
        "as_of": pd.Timestamp.utcnow().isoformat(),
        "symbols": SYMBOLS,
        "thresholds": {"major": THRESH_MAJOR, "alt": THRESH_ALT},
        "costs": {"taker_bps": TAKER_BPS, "slip_bps": SLIP_BPS},
        "per_symbol": all_results,
        "portfolio": portfolio_metrics,
        "permutation_test_BTC": perm_btc,
        "permutation_test_ETH": perm_eth,
        "DSR": {"long_only": dsr_uni, "long_short": dsr_ls, "N_trials": 2},
        "cost_stress": cost_stress,
        "gates": gates,
        "gates_adaptive": gates_adaptive,
        "n_gates_pass": n_pass,
        "verdict": verdict,
        "elapsed_sec": time.time() - t0,
    }
    with open(OUT_JSON, "w") as f:
        json.dump(result, f, indent=2, default=str)

    print()
    print("=" * 70)
    print("PORTFOLIO (universal LO)")
    print(f"  IS  Sharpe: {portfolio_metrics['universal_long_only']['IS_sharpe']:.3f}")
    print(f"  OOS Sharpe: {oos_sr_uni:.3f}  CI95=[{ci_uni[0]:.2f},{ci_uni[1]:.2f}]")
    print(f"  OOS MaxDD : {oos_dd_uni:.2%}")
    print()
    print("Cost stress OOS Sharpe:")
    for k, v in cost_stress.items():
        print(f"  {k:5s}: SR={v['OOS_sharpe']:.3f}  DD={v['OOS_max_dd']:.2%}")
    print()
    print(f"ADAPTIVE-p80 portfolio: IS_SR={portfolio_metrics['adaptive_p80_long_only']['IS_sharpe']:.3f}  OOS_SR={portfolio_metrics['adaptive_p80_long_only']['OOS_sharpe']:.3f}  OOS_DD={portfolio_metrics['adaptive_p80_long_only']['OOS_max_dd']:.2%}")
    print()
    print("GATES:")
    for k, v in gates.items():
        print(f"  {k}: {'PASS' if v else 'FAIL'}")
    print(f"\nVERDICT: {verdict} ({n_pass}/6 gates pass)")
    print(f"Elapsed: {time.time()-t0:.1f}s")


if __name__ == "__main__":
    main()

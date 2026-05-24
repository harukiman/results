"""
Wave K116 — vol_only Cross-Section Sort (K112 salvage, expanded universe)

PRE-REGISTERED (no IS factor tuning, no cadence shopping):
  - Single factor: inverse 30-day realized vol
  - Cadence: weekly (Friday last 4H bar)
  - Universe: cache filtered to >=4000 bars (expanded ~55 symbols)
  - Long top decile, short bottom decile (low-vol minus high-vol), equal-weight, dollar-neutral
  - Cost: 0.07% per leg per side on turnover
  - N_trials = 1 for DSR (pre-registered)
"""
from __future__ import annotations

import glob
import json
import os
import time
from typing import Dict, List, Tuple

import numpy as np
import pandas as pd

CACHE_DIR = "/Users/nekonaomichi/crypto-lab/cache"
OUT_PY = "/Users/nekonaomichi/crypto-lab/wave_k116_vol_only.py"
OUT_JSON = "/Users/nekonaomichi/crypto-lab/wave_k116_vol_only.json"
OUT_CURVES = "/Users/nekonaomichi/crypto-lab/wave_k116_curves.json"

# Pre-registered params
VOL_LOOKBACK = 180      # 30 days * 6 4H-bars/day
CADENCE_BARS = 42       # weekly = 7d * 6 bars/day
COST_BPS = 7.0          # 0.07% per leg per side
DECILE_FRAC = 0.10
MIN_BARS = 4000
OOS_FRAC = 0.30
EMBARGO = 5
RNG_SEED = 20260524

ANN_FACTOR_BARS = 2190.0  # 365 * 6 4H-bars / yr
ANN_FACTOR_WEEKS = 52.0


def load_universe() -> Tuple[pd.DataFrame, List[str]]:
    files = sorted(glob.glob(os.path.join(CACHE_DIR, "*_4h_730d.parquet")))
    files = [f for f in files if "hist_premium" not in os.path.basename(f)]
    frames: Dict[str, pd.DataFrame] = {}
    for f in files:
        sym = os.path.basename(f).replace("_4h_730d.parquet", "")
        df = pd.read_parquet(f)
        if len(df) < MIN_BARS:
            continue
        df = df.copy()
        df["open_time"] = pd.to_datetime(df["open_time"])
        df = df.sort_values("open_time").drop_duplicates("open_time")
        df = df.set_index("open_time")
        frames[sym] = df[["close"]].rename(columns={"close": sym})
    # Align on intersection of timestamps (use outer join, then forward fill, then keep rows where all present)
    closes = pd.concat([frames[s] for s in sorted(frames)], axis=1)
    # use the latest common start
    closes = closes.dropna(how="any")
    syms = list(closes.columns)
    return closes, syms


def realized_vol(returns: pd.DataFrame, lookback: int) -> pd.DataFrame:
    return returns.rolling(lookback, min_periods=lookback).std() * np.sqrt(ANN_FACTOR_BARS)


def weekly_rebal_dates(idx: pd.DatetimeIndex, cadence: int = CADENCE_BARS, warmup: int = VOL_LOOKBACK) -> np.ndarray:
    # use every cadence-th bar after warmup, lagged by 1 -> we'll use signal at t-1, trade from t
    starts = np.arange(warmup + 1, len(idx), cadence)
    return starts


def compute_weights(rank_signal: pd.Series, n: int) -> pd.Series:
    """Long bottom-decile of vol (= top of inverse-vol), short top-decile of vol.
    Signal: realized vol (lower = better). We long low vol, short high vol.
    Equal-weight within sleeve, dollar-neutral."""
    valid = rank_signal.dropna()
    k = max(1, int(round(len(valid) * DECILE_FRAC)))
    sorted_idx = valid.sort_values().index  # ascending vol
    longs = sorted_idx[:k]
    shorts = sorted_idx[-k:]
    w = pd.Series(0.0, index=rank_signal.index)
    w.loc[longs] = 0.5 / len(longs)
    w.loc[shorts] = -0.5 / len(shorts)
    return w


def run_backtest(closes: pd.DataFrame) -> dict:
    syms = list(closes.columns)
    rets = closes.pct_change().fillna(0.0)
    vol = realized_vol(rets, VOL_LOOKBACK)

    rebal_pts = weekly_rebal_dates(closes.index)
    n = len(closes)

    bar_pnl = np.zeros(n)
    weight_history: List[Tuple[int, pd.Series]] = []
    per_sym_pnl = pd.DataFrame(0.0, index=closes.index, columns=syms)
    cost_history = np.zeros(n)

    current_w = pd.Series(0.0, index=syms)
    next_rebal_idx = 0
    last_w = pd.Series(0.0, index=syms)

    for i in range(n):
        # Apply weights (set at previous rebal) to today's returns
        ret_today = rets.iloc[i]
        contrib = current_w * ret_today
        bar_pnl[i] = contrib.sum()
        per_sym_pnl.iloc[i] = contrib.values

        # Rebalance at end-of-bar i if i is a rebal point: new weights apply NEXT bar
        if next_rebal_idx < len(rebal_pts) and i == rebal_pts[next_rebal_idx]:
            # Use signal from bar i-1 (lagged)
            sig = vol.iloc[i - 1]
            new_w = compute_weights(sig, len(syms))
            # turnover cost: |delta w| * cost (per leg). Cost is per side per leg.
            turnover = (new_w - current_w).abs().sum()
            # apply cost at next bar (we'll subtract here from this bar pnl as proxy for execution slippage)
            cost = turnover * (COST_BPS / 1e4)
            cost_history[i] = cost
            bar_pnl[i] -= cost
            current_w = new_w.reindex(syms).fillna(0.0)
            weight_history.append((i, current_w.copy()))
            last_w = current_w.copy()
            next_rebal_idx += 1

    portfolio_eq = (1.0 + pd.Series(bar_pnl, index=closes.index)).cumprod()
    return {
        "rets": pd.Series(bar_pnl, index=closes.index),
        "equity": portfolio_eq,
        "per_sym_pnl": per_sym_pnl,
        "weights_history": weight_history,
        "costs": pd.Series(cost_history, index=closes.index),
        "rebal_pts": rebal_pts,
    }


# ---- Metrics --------------------------------------------------------------

def annualize_sharpe(rets: pd.Series) -> float:
    r = rets.dropna().values
    if r.std(ddof=1) == 0 or len(r) < 5:
        return 0.0
    return float(r.mean() / r.std(ddof=1) * np.sqrt(ANN_FACTOR_BARS))


def annualize_sortino(rets: pd.Series) -> float:
    r = rets.dropna().values
    down = r[r < 0]
    if len(down) < 2 or down.std(ddof=1) == 0:
        return 0.0
    return float(r.mean() / down.std(ddof=1) * np.sqrt(ANN_FACTOR_BARS))


def max_drawdown(equity: pd.Series) -> float:
    peak = equity.cummax()
    dd = (equity / peak - 1.0).min()
    return float(dd)


def calmar(rets: pd.Series, equity: pd.Series) -> float:
    ann_ret = (equity.iloc[-1] ** (ANN_FACTOR_BARS / max(1, len(rets)))) - 1.0
    mdd = abs(max_drawdown(equity))
    if mdd < 1e-9:
        return 0.0
    return float(ann_ret / mdd)


def annual_return(rets: pd.Series) -> float:
    eq = (1.0 + rets).prod()
    return float(eq ** (ANN_FACTOR_BARS / max(1, len(rets))) - 1.0)


def annual_vol(rets: pd.Series) -> float:
    return float(rets.std(ddof=1) * np.sqrt(ANN_FACTOR_BARS))


def win_rate(rets: pd.Series) -> float:
    nz = rets[rets != 0]
    if len(nz) == 0:
        return 0.0
    return float((nz > 0).mean())


def metrics_pack(rets: pd.Series, label: str) -> dict:
    eq = (1.0 + rets).cumprod()
    return {
        "label": label,
        "n_bars": int(len(rets)),
        "ann_return": annual_return(rets),
        "ann_vol": annual_vol(rets),
        "sharpe": annualize_sharpe(rets),
        "sortino": annualize_sortino(rets),
        "max_dd": max_drawdown(eq),
        "calmar": calmar(rets, eq),
        "win_rate": win_rate(rets),
        "final_equity": float(eq.iloc[-1]),
    }


# ---- §6 audit -------------------------------------------------------------

def walk_forward(rets: pd.Series, n_folds: int = 4, embargo: int = EMBARGO) -> dict:
    n = len(rets)
    fold_size = n // (n_folds + 1)
    is_sharpes, oos_sharpes = [], []
    for k in range(n_folds):
        train_end = fold_size * (k + 1)
        test_start = train_end + embargo
        test_end = min(test_start + fold_size, n)
        if test_end <= test_start + 10:
            continue
        is_r = rets.iloc[:train_end]
        oos_r = rets.iloc[test_start:test_end]
        is_sharpes.append(annualize_sharpe(is_r))
        oos_sharpes.append(annualize_sharpe(oos_r))
    return {
        "is_sharpes": is_sharpes,
        "oos_sharpes": oos_sharpes,
        "is_mean": float(np.mean(is_sharpes)) if is_sharpes else 0.0,
        "oos_mean": float(np.mean(oos_sharpes)) if oos_sharpes else 0.0,
    }


def cpcv_pbo(rets: pd.Series, n_splits: int = 10, embargo: int = EMBARGO) -> dict:
    """Lightweight PBO via single-strategy CPCV: split into n_splits chunks, evaluate IS vs OOS Sharpe,
    PBO = fraction of folds where OOS rank < median (i.e., underperforms vs IS expectation).
    For single strategy we compare IS Sharpe rank vs OOS Sharpe rank across folds."""
    n = len(rets)
    chunk = n // n_splits
    is_perf, oos_perf = [], []
    for k in range(n_splits):
        a = k * chunk
        b = (k + 1) * chunk if k < n_splits - 1 else n
        oos = rets.iloc[a:b]
        is_ = pd.concat([rets.iloc[:max(0, a - embargo)], rets.iloc[min(n, b + embargo):]])
        if len(is_) < 30 or len(oos) < 30:
            continue
        is_perf.append(annualize_sharpe(is_))
        oos_perf.append(annualize_sharpe(oos))
    is_perf = np.array(is_perf)
    oos_perf = np.array(oos_perf)
    if len(is_perf) < 2:
        return {"pbo": 1.0, "is": [], "oos": []}
    # For single-strategy PBO proxy: fraction of folds where OOS Sharpe < median of IS Sharpe distribution
    median_is = float(np.median(is_perf))
    underperf = int((oos_perf < median_is).sum())
    pbo = underperf / len(oos_perf)
    return {
        "pbo": float(pbo),
        "is": is_perf.tolist(),
        "oos": oos_perf.tolist(),
        "n_folds": len(is_perf),
    }


def deflated_sharpe(rets: pd.Series, n_trials: int = 1) -> dict:
    """DSR per Bailey & Lopez de Prado.
    For N=1 (pre-registered), DSR reduces to PSR vs benchmark=0."""
    r = rets.dropna().values
    if len(r) < 30:
        return {"dsr": 0.0, "psr": 0.0, "z": 0.0, "p": 1.0, "sharpe": 0.0}
    sr_bar = float(np.mean(r) / np.std(r, ddof=1)) if np.std(r, ddof=1) > 0 else 0.0
    skew = float(pd.Series(r).skew())
    kurt = float(pd.Series(r).kurtosis())  # excess kurtosis
    T = len(r)
    # Annualized Sharpe (per-bar -> annual)
    sr_ann = sr_bar * np.sqrt(ANN_FACTOR_BARS)
    # PSR vs zero
    denom = np.sqrt(1.0 - skew * sr_bar + (kurt / 4.0) * (sr_bar ** 2))
    if denom <= 0:
        denom = 1e-9
    z = sr_bar * np.sqrt(T - 1) / denom
    from math import erf, sqrt as msqrt
    cdf = 0.5 * (1 + erf(z / msqrt(2)))
    psr = float(cdf)
    # DSR with N_trials
    if n_trials <= 1:
        dsr_threshold = 0.0
    else:
        # Expected max of N normal SRs
        from math import log
        em = (1 - 0.5772) * (2 * log(n_trials)) ** 0.5 + 0.5772 * (2 * log(max(2, n_trials))) ** 0.5
        # standard SR std
        sr_std = 1.0 / np.sqrt(T)
        dsr_threshold = em * sr_std
    z_def = (sr_bar - dsr_threshold) * np.sqrt(T - 1) / denom
    cdf_def = 0.5 * (1 + erf(z_def / msqrt(2)))
    dsr = float(cdf_def)
    p_val = 2 * (1 - max(cdf, 1 - cdf))
    return {
        "sharpe_ann": float(sr_ann),
        "sharpe_per_bar": sr_bar,
        "psr": psr,
        "dsr": dsr,
        "z": float(z),
        "p": float(p_val),
        "skew": skew,
        "kurt": kurt,
        "n_trials": n_trials,
        "T": T,
    }


def block_bootstrap(rets: pd.Series, block: int = 20, n_iter: int = 1000, seed: int = RNG_SEED) -> dict:
    rng = np.random.default_rng(seed)
    r = rets.dropna().values
    n = len(r)
    if n < block * 5:
        return {"mean": 0.0, "ci_low": 0.0, "ci_high": 0.0, "p_gt0": 0.0}
    n_blocks = n // block
    samples = []
    for _ in range(n_iter):
        starts = rng.integers(0, n - block + 1, size=n_blocks)
        boot = np.concatenate([r[s:s + block] for s in starts])
        sr = boot.mean() / boot.std(ddof=1) * np.sqrt(ANN_FACTOR_BARS) if boot.std(ddof=1) > 0 else 0.0
        samples.append(sr)
    samples = np.array(samples)
    return {
        "mean": float(samples.mean()),
        "ci_low": float(np.percentile(samples, 2.5)),
        "ci_high": float(np.percentile(samples, 97.5)),
        "p_gt0": float((samples > 0).mean()),
    }


def permutation_test(closes: pd.DataFrame, n_iter: int = 500, seed: int = RNG_SEED) -> dict:
    """Shuffle ranks within each weekly cross-section. We don't shuffle returns; we shuffle which
    symbol the LONG/SHORT goes to within each rebal, holding aggregate structure fixed.

    This is approximated by: at each rebal, randomly assign weights (still dollar-neutral, deciles)
    and recompute pnl. Compare distribution of shuffled Sharpes vs realized."""
    rng = np.random.default_rng(seed)
    syms = list(closes.columns)
    rets = closes.pct_change().fillna(0.0)
    n = len(closes)
    rebal_pts = weekly_rebal_dates(closes.index)
    k = max(1, int(round(len(syms) * DECILE_FRAC)))

    perm_sharpes = []
    for it in range(n_iter):
        current_w = pd.Series(0.0, index=syms)
        next_rebal_idx = 0
        bar_pnl = np.zeros(n)
        for i in range(n):
            contrib = current_w * rets.iloc[i]
            bar_pnl[i] = contrib.sum()
            if next_rebal_idx < len(rebal_pts) and i == rebal_pts[next_rebal_idx]:
                perm = rng.permutation(len(syms))
                longs = [syms[j] for j in perm[:k]]
                shorts = [syms[j] for j in perm[k:2 * k]]
                new_w = pd.Series(0.0, index=syms)
                new_w.loc[longs] = 0.5 / k
                new_w.loc[shorts] = -0.5 / k
                turnover = (new_w - current_w).abs().sum()
                bar_pnl[i] -= turnover * (COST_BPS / 1e4)
                current_w = new_w
                next_rebal_idx += 1
        sr = bar_pnl.mean() / bar_pnl.std(ddof=1) * np.sqrt(ANN_FACTOR_BARS) if bar_pnl.std(ddof=1) > 0 else 0.0
        perm_sharpes.append(sr)
    perm_sharpes = np.array(perm_sharpes)
    return {
        "mean": float(perm_sharpes.mean()),
        "std": float(perm_sharpes.std()),
        "q95": float(np.percentile(perm_sharpes, 95)),
        "q05": float(np.percentile(perm_sharpes, 5)),
        "samples": perm_sharpes.tolist(),
    }


def cost_stress(closes: pd.DataFrame, multipliers: List[float]) -> dict:
    global COST_BPS
    base = COST_BPS
    results = {}
    for m in multipliers:
        COST_BPS = base * m
        bt = run_backtest(closes)
        results[f"x{m}"] = {
            "cost_bps": COST_BPS,
            "sharpe": annualize_sharpe(bt["rets"]),
            "ann_return": annual_return(bt["rets"]),
        }
    COST_BPS = base
    return results


# ---- Diagnostics ----------------------------------------------------------

def per_decile_breakdown(closes: pd.DataFrame, n_deciles: int = 10) -> dict:
    """Compute long-only return of each decile sleeve (uncosted) for diagnostic."""
    syms = list(closes.columns)
    rets = closes.pct_change().fillna(0.0)
    vol = realized_vol(rets, VOL_LOOKBACK)
    rebal_pts = weekly_rebal_dates(closes.index)
    n = len(closes)

    decile_pnl = np.zeros((n, n_deciles))
    current_ws: List[pd.Series] = [pd.Series(0.0, index=syms) for _ in range(n_deciles)]
    next_rebal_idx = 0
    for i in range(n):
        for d in range(n_deciles):
            decile_pnl[i, d] = (current_ws[d] * rets.iloc[i]).sum()
        if next_rebal_idx < len(rebal_pts) and i == rebal_pts[next_rebal_idx]:
            sig = vol.iloc[i - 1]
            valid = sig.dropna()
            if len(valid) >= n_deciles:
                sorted_syms = valid.sort_values().index
                sleeve_size = max(1, len(sorted_syms) // n_deciles)
                for d in range(n_deciles):
                    a = d * sleeve_size
                    b = (d + 1) * sleeve_size if d < n_deciles - 1 else len(sorted_syms)
                    sleeve = sorted_syms[a:b]
                    w = pd.Series(0.0, index=syms)
                    if len(sleeve) > 0:
                        w.loc[sleeve] = 1.0 / len(sleeve)
                    current_ws[d] = w
            next_rebal_idx += 1
    out = {}
    for d in range(n_deciles):
        r = pd.Series(decile_pnl[:, d], index=closes.index)
        out[f"D{d+1}"] = {
            "ann_return": annual_return(r),
            "sharpe": annualize_sharpe(r),
        }
    return out


def per_symbol_drag(per_sym_pnl: pd.DataFrame) -> dict:
    totals = per_sym_pnl.sum().sort_values()
    return {
        "worst": totals.head(10).to_dict(),
        "best": totals.tail(10).iloc[::-1].to_dict(),
    }


# ---- Main -----------------------------------------------------------------

def main():
    t0 = time.time()
    print("Loading universe...")
    closes, syms = load_universe()
    print(f"Universe: {len(syms)} symbols x {len(closes)} bars; range {closes.index[0]} -> {closes.index[-1]}")

    print("Running full backtest...")
    bt = run_backtest(closes)
    rets = bt["rets"]
    eq = bt["equity"]

    # Single split: OOS = last 30%
    n = len(rets)
    is_end = int(n * (1 - OOS_FRAC))
    is_r = rets.iloc[:is_end]
    oos_r = rets.iloc[is_end + EMBARGO:]
    print(f"IS: {len(is_r)} bars, OOS: {len(oos_r)} bars")

    portfolio_metrics = metrics_pack(rets, "FULL")
    is_metrics = metrics_pack(is_r, "IS")
    oos_metrics = metrics_pack(oos_r, "OOS")

    # n_trades = number of rebalances
    n_trades = len(bt["rebal_pts"])
    portfolio_metrics["n_trades"] = n_trades

    print("Per-decile breakdown...")
    decile = per_decile_breakdown(closes)
    print("Per-symbol drag...")
    drag = per_symbol_drag(bt["per_sym_pnl"])

    print("§6 audit: walk-forward...")
    wf = walk_forward(rets, n_folds=4)
    print("§6 audit: CPCV PBO...")
    pbo = cpcv_pbo(rets, n_splits=10)
    print("§6 audit: DSR...")
    dsr = deflated_sharpe(rets, n_trials=1)
    dsr_oos = deflated_sharpe(oos_r, n_trials=1)
    print("§6 audit: block bootstrap (OOS)...")
    boot = block_bootstrap(oos_r, block=20, n_iter=1000)
    print("§6 audit: permutation test (n=500)...")
    perm = permutation_test(closes, n_iter=500)
    realized_oos_sr = oos_metrics["sharpe"]
    perm_p = float((np.array(perm["samples"]) >= realized_oos_sr).mean())
    perm["p_value_vs_realized_oos"] = perm_p
    print("§6 audit: cost stress...")
    stress = cost_stress(closes, [0.5, 1.0, 1.5])

    # Gates
    g1 = oos_metrics["sharpe"] > 0.5
    g2 = pbo["pbo"] < 0.3
    g3 = dsr["psr"] > 0.95  # pre-reg DSR = PSR > 95%

    # Top-5 contributors equity curves
    sym_totals = bt["per_sym_pnl"].sum().sort_values(ascending=False)
    top5 = sym_totals.head(5).index.tolist()
    top5_curves = {s: bt["per_sym_pnl"][s].cumsum().tolist() for s in top5}

    out = {
        "universe_size": len(syms),
        "n_bars": len(closes),
        "date_range": [str(closes.index[0]), str(closes.index[-1])],
        "params": {
            "vol_lookback_bars": VOL_LOOKBACK,
            "cadence_bars": CADENCE_BARS,
            "cost_bps": COST_BPS,
            "decile_frac": DECILE_FRAC,
            "min_bars": MIN_BARS,
        },
        "portfolio": portfolio_metrics,
        "IS": is_metrics,
        "OOS": oos_metrics,
        "decile_breakdown": decile,
        "symbol_drag": drag,
        "audit": {
            "walk_forward": wf,
            "cpcv_pbo": pbo,
            "DSR": dsr,
            "DSR_OOS": dsr_oos,
            "block_bootstrap_OOS": boot,
            "permutation": {k: v for k, v in perm.items() if k != "samples"},
            "cost_stress": stress,
        },
        "gates": {
            "G1_OOS_Sh_gt_0.5": bool(g1),
            "G2_PBO_lt_0.3": bool(g2),
            "G3_DSR_PSR_gt_0.95": bool(g3),
        },
        "symbols": syms,
        "wall_time_sec": round(time.time() - t0, 1),
    }

    with open(OUT_JSON, "w") as f:
        json.dump(out, f, indent=2, default=str)
    print(f"Wrote {OUT_JSON}")

    curves = {
        "timestamps": [str(t) for t in closes.index],
        "portfolio_equity": eq.tolist(),
        "is_equity": (1.0 + is_r).cumprod().tolist(),
        "oos_equity": (1.0 + oos_r).cumprod().tolist(),
        "is_timestamps": [str(t) for t in is_r.index],
        "oos_timestamps": [str(t) for t in oos_r.index],
        "top5_symbols": top5,
        "top5_curves": top5_curves,
        "perm_samples": perm["samples"][:200],
    }
    with open(OUT_CURVES, "w") as f:
        json.dump(curves, f, default=str)
    print(f"Wrote {OUT_CURVES}")
    print(f"Wall time: {out['wall_time_sec']}s")

    # Summary
    print("\n=== SUMMARY ===")
    print(f"Universe: {len(syms)} syms x {len(closes)} bars")
    print(f"Portfolio Sharpe: {portfolio_metrics['sharpe']:.3f}  IS: {is_metrics['sharpe']:.3f}  OOS: {oos_metrics['sharpe']:.3f}")
    print(f"OOS ann_ret: {oos_metrics['ann_return']:.4f}  MaxDD: {oos_metrics['max_dd']:.4f}")
    print(f"PBO: {pbo['pbo']:.3f}  DSR (PSR vs 0): {dsr['psr']:.3f}  z={dsr['z']:.2f}")
    print(f"Bootstrap CI [{boot['ci_low']:.3f}, {boot['ci_high']:.3f}] p(>0)={boot['p_gt0']:.3f}")
    print(f"Permutation p (OOS Sh vs perm dist): {perm_p:.3f}")
    print(f"Gates: G1={g1} G2={g2} G3={g3}")
    return out


if __name__ == "__main__":
    main()

"""
Wave K127 — BIS Crypto Carry Cross-Section (R4-7 / R2 #37)

Hypothesis (BIS WP1087):
  Cross-sectional sort on perpetual funding rate.
  Long bottom-decile (cheap-to-fund, short pays long)
  Short top-decile (expensive-to-fund, long pays short)
  Reported IS Sharpe 7-12 on majors.

Pre-registered method:
  - Per 8h funding event
  - Trailing 7d mean funding (21 events), lag 1 (no look-ahead)
  - Rank cross-section, long bottom-K, short top-K, dollar-neutral, equal weight
  - PnL = price return + funding received (long) - funding paid (short) - cost
  - 730d, IS 70 / OOS 30, walk-forward 4-fold
  - Permutation (n=500) shuffling funding ranks cross-sectionally
  - Block bootstrap (n=500)
  - DSR N_trials=1 (will run N_trials=3 if Sharpe >> 1)

Variants (3, to keep DSR honest):
  V_top_bottom_3  : 3L/3S, 8h hold
  V_top_bottom_5  : 5L/5S, 8h hold
  V_top_bottom_3_24h : 3L/3S, 24h hold (rebalance every 3rd funding)
"""

import json
import os
import time
import warnings
from pathlib import Path

import numpy as np
import pandas as pd
from scipy import stats

warnings.filterwarnings("ignore")

ROOT = Path("/Users/nekonaomichi/crypto-lab")
CACHE = ROOT / "cache"

SYMBOLS = [
    "BTC", "ETH", "SOL", "BNB", "DOGE", "AVAX", "LINK", "ADA",
    "XRP", "INJ", "OP", "WIF", "BONK", "SHIB", "ARB",
]

# Costs (round-trip per leg of position change): 7 bps total (fee + slip)
COST_BPS = 7.0
FUND_LOOKBACK_EVENTS = 21  # 7 days * 3 events/day
ANN_FACTOR_8H = np.sqrt(365 * 3)
ANN_FACTOR_24H = np.sqrt(365)
IS_FRAC = 0.70
SEED = 20260524


# ---------------------------------------------------------------- data load
def load_fr(sym):
    p = CACHE / f"bybit_fr_{sym}USDT_730d.parquet"
    if not p.exists():
        return None
    df = pd.read_parquet(p)
    df["timestamp"] = pd.to_datetime(df["timestamp"])
    df = df.set_index("timestamp").sort_index()
    df = df[~df.index.duplicated(keep="last")]
    return df["funding_rate"].astype(float).rename(sym)


def load_px(sym):
    p = CACHE / f"{sym}USDT_4h_730d.parquet"
    if not p.exists():
        return None
    df = pd.read_parquet(p)
    df["open_time"] = pd.to_datetime(df["open_time"])
    df = df.set_index("open_time").sort_index()
    df = df[~df.index.duplicated(keep="last")]
    return df["close"].astype(float).rename(sym)


def build_panels():
    fr_dict, px_dict = {}, {}
    for s in SYMBOLS:
        fr = load_fr(s)
        px = load_px(s)
        if fr is None or px is None:
            print(f"  skip {s} (missing data)")
            continue
        fr_dict[s] = fr
        px_dict[s] = px

    fr_panel = pd.concat(fr_dict.values(), axis=1).sort_index()
    px_panel = pd.concat(px_dict.values(), axis=1).sort_index()

    # Restrict FR panel to events all symbols share (drop early NaN heavy rows)
    fr_panel = fr_panel.dropna(thresh=int(fr_panel.shape[1] * 0.8))

    # For each FR event timestamp, get the price at that time
    # FR fires every 8h on 00:00/08:00/16:00 UTC which align with 4h bars
    px_at_fr = px_panel.reindex(fr_panel.index, method="ffill")

    return fr_panel, px_at_fr


# ------------------------------------------------------------- backtest core
def backtest_xs(fr_panel, px_at_fr, k=3, hold_n_events=1, cost_bps=COST_BPS):
    """
    Cross-sectional funding-rate carry, executed at every funding event.

    fr_panel       : T x N funding rates (8h cadence)
    px_at_fr       : T x N close at FR timestamp (4h grid, reindexed)
    k              : long bottom-k, short top-k
    hold_n_events  : how many 8h events to hold each position (1 = 8h, 3 = 24h)
    """
    # Trailing 7d mean funding, lagged by 1 event to avoid look-ahead
    trailing = fr_panel.rolling(FUND_LOOKBACK_EVENTS, min_periods=FUND_LOOKBACK_EVENTS).mean()
    signal = trailing.shift(1)

    # Subsample to rebalance grid (every hold_n_events events)
    rebal_idx = signal.index[::hold_n_events]

    sig_r = signal.loc[rebal_idx]
    fr_r = fr_panel.loc[rebal_idx]
    px_r = px_at_fr.loc[rebal_idx]

    T = len(rebal_idx)
    N = fr_panel.shape[1]

    rets = np.zeros(T)
    fund_pnl_arr = np.zeros(T)
    price_pnl_arr = np.zeros(T)
    cost_arr = np.zeros(T)
    pos_long_count = pd.Series(0, index=fr_panel.columns, dtype=int)
    pos_short_count = pd.Series(0, index=fr_panel.columns, dtype=int)

    prev_w = np.zeros(N)
    cols = list(fr_panel.columns)

    for t in range(T - 1):
        row = sig_r.iloc[t].values
        valid_mask = ~np.isnan(row)
        if valid_mask.sum() < 2 * k + 1:
            prev_w = np.zeros(N)
            continue

        valid_idx = np.where(valid_mask)[0]
        ordered = valid_idx[np.argsort(row[valid_idx])]  # ascending: lowest funding first
        if len(ordered) < 2 * k:
            prev_w = np.zeros(N)
            continue

        longs = ordered[:k]
        shorts = ordered[-k:]

        w = np.zeros(N)
        w[longs] = +1.0 / k
        w[shorts] = -1.0 / k

        for li in longs:
            pos_long_count.iloc[li] += 1
        for si in shorts:
            pos_short_count.iloc[si] += 1

        # Realized 8h * hold_n_events price return: px_{t+1}/px_t - 1
        px_now = px_r.iloc[t].values
        px_next = px_r.iloc[t + 1].values
        with np.errstate(invalid="ignore", divide="ignore"):
            pr = px_next / px_now - 1.0
        pr = np.where(np.isfinite(pr), pr, 0.0)

        # Funding paid/received over the hold window.
        # Convention: positive funding => longs pay shorts.
        # Pnl from funding for a position w over the hold:
        # sum of funding events inside [t, t+1) at this rebalancing grid
        # = sum_{j in window} fr_panel[j] * (-w)  (longs lose funding when fr>0)
        # We aggregate across the underlying 8h events:
        start = fr_panel.index.get_loc(rebal_idx[t])
        end = fr_panel.index.get_loc(rebal_idx[t + 1])
        fr_window = fr_panel.iloc[start:end].fillna(0.0).values  # (hold_n_events, N)
        fr_sum = fr_window.sum(axis=0)
        funding_ret = -(w * fr_sum)  # long+fr>0 pays, short+fr>0 receives
        # Above: w>0 (long) and fr>0 means longs pay, so PnL contribution is -w*fr (negative).
        # w<0 (short) and fr>0 means shorts receive, -w*fr = +|w|*fr (positive). Correct.

        # Cost: full turnover from prev to new position
        turn = np.abs(w - prev_w).sum()
        cost = turn * (cost_bps / 1e4)

        price_pnl = float((w * pr).sum())
        fund_pnl = float(funding_ret.sum())
        rets[t] = price_pnl + fund_pnl - cost
        price_pnl_arr[t] = price_pnl
        fund_pnl_arr[t] = fund_pnl
        cost_arr[t] = cost

        prev_w = w

    # Drop terminal zero
    rets = rets[:-1]
    fund_pnl_arr = fund_pnl_arr[:-1]
    price_pnl_arr = price_pnl_arr[:-1]
    cost_arr = cost_arr[:-1]
    idx = rebal_idx[:-1][:len(rets)]

    return {
        "rets": pd.Series(rets, index=idx),
        "fund_pnl": pd.Series(fund_pnl_arr, index=idx),
        "price_pnl": pd.Series(price_pnl_arr, index=idx),
        "cost": pd.Series(cost_arr, index=idx),
        "long_count": pos_long_count,
        "short_count": pos_short_count,
    }


# ---------------------------------------------------------------- stats
def perf_stats(rets, ann_factor):
    rets = pd.Series(rets).dropna()
    if rets.std() == 0 or len(rets) < 5:
        return dict(sharpe=0.0, sortino=0.0, calmar=0.0, max_dd=0.0,
                    win_rate=0.0, ann_ret=0.0, ann_vol=0.0, n=int(len(rets)))
    mu = rets.mean()
    sd = rets.std()
    sharpe = mu / sd * ann_factor
    downside = rets[rets < 0].std()
    sortino = mu / downside * ann_factor if downside and downside > 0 else 0.0
    equity = (1 + rets).cumprod()
    peak = equity.cummax()
    dd = (equity / peak - 1).min()
    ann_ret = (1 + mu) ** (ann_factor ** 2) - 1  # because ann_factor = sqrt(periods/yr)
    calmar = ann_ret / abs(dd) if dd < 0 else 0.0
    win_rate = float((rets > 0).mean())
    return dict(
        sharpe=float(sharpe), sortino=float(sortino), calmar=float(calmar),
        max_dd=float(dd), win_rate=win_rate, ann_ret=float(ann_ret),
        ann_vol=float(sd * ann_factor), n=int(len(rets)),
    )


def deflated_sharpe_ratio(sr_hat, n_obs, n_trials, rets):
    rets = pd.Series(rets).dropna()
    if len(rets) < 5:
        return 0.0
    skew = float(stats.skew(rets))
    kurt = float(stats.kurtosis(rets, fisher=True))
    # Bailey & Lopez de Prado expected max Sharpe under null
    euler = 0.5772156649
    if n_trials > 1:
        e_max = (1 - euler) * stats.norm.ppf(1 - 1 / n_trials) + \
                euler * stats.norm.ppf(1 - 1 / (n_trials * np.e))
    else:
        e_max = 0.0
    sr0 = e_max / np.sqrt(n_obs)
    denom = np.sqrt(1 - skew * sr_hat + (kurt / 4.0) * sr_hat ** 2)
    if denom <= 0:
        return 0.0
    z = (sr_hat - sr0) * np.sqrt(n_obs - 1) / denom
    return float(stats.norm.cdf(z))


def walk_forward(fr_panel, px_at_fr, k, hold_n, n_folds=4):
    """Re-run backtest on each fold and report Sharpe stability."""
    T = len(fr_panel)
    fold_size = T // n_folds
    out = []
    for f in range(n_folds):
        s = f * fold_size
        e = (f + 1) * fold_size if f < n_folds - 1 else T
        sub_fr = fr_panel.iloc[s:e]
        sub_px = px_at_fr.iloc[s:e]
        try:
            r = backtest_xs(sub_fr, sub_px, k=k, hold_n_events=hold_n)["rets"]
        except Exception:
            r = pd.Series(dtype=float)
        ann = ANN_FACTOR_8H if hold_n == 1 else ANN_FACTOR_24H
        s_ = perf_stats(r, ann)
        out.append({"fold": f, **s_})
    return out


def permutation_test(fr_panel, px_at_fr, k, hold_n, n_iter=500, seed=SEED):
    """Shuffle funding ranks cross-sectionally per row to destroy signal."""
    rng = np.random.default_rng(seed)
    ann = ANN_FACTOR_8H if hold_n == 1 else ANN_FACTOR_24H
    actual_sr = perf_stats(
        backtest_xs(fr_panel, px_at_fr, k=k, hold_n_events=hold_n)["rets"], ann
    )["sharpe"]

    null_sr = np.zeros(n_iter)
    fr_vals = fr_panel.values.copy()
    for i in range(n_iter):
        permuted = fr_vals.copy()
        # Shuffle each row independently across columns (preserve marginals)
        for r in range(permuted.shape[0]):
            row = permuted[r]
            mask = ~np.isnan(row)
            idxs = np.where(mask)[0]
            if len(idxs) > 1:
                shuf = rng.permutation(row[idxs])
                permuted[r, idxs] = shuf
        fp = pd.DataFrame(permuted, index=fr_panel.index, columns=fr_panel.columns)
        rets = backtest_xs(fp, px_at_fr, k=k, hold_n_events=hold_n)["rets"]
        null_sr[i] = perf_stats(rets, ann)["sharpe"]
    p_val = float((null_sr >= actual_sr).mean())
    return {
        "actual_sharpe": float(actual_sr),
        "null_mean": float(null_sr.mean()),
        "null_std": float(null_sr.std()),
        "null_p95": float(np.quantile(null_sr, 0.95)),
        "p_value": p_val,
    }


def block_bootstrap_ci(rets, ann_factor, block=21, n_iter=500, seed=SEED):
    rets = pd.Series(rets).dropna().values
    if len(rets) < block * 3:
        return {"low": 0.0, "high": 0.0}
    rng = np.random.default_rng(seed + 1)
    n_blocks = len(rets) // block
    srs = np.zeros(n_iter)
    for i in range(n_iter):
        starts = rng.integers(0, len(rets) - block, size=n_blocks)
        sampled = np.concatenate([rets[s:s + block] for s in starts])
        if sampled.std() == 0:
            srs[i] = 0.0
        else:
            srs[i] = sampled.mean() / sampled.std() * ann_factor
    return {
        "low": float(np.quantile(srs, 0.025)),
        "median": float(np.quantile(srs, 0.5)),
        "high": float(np.quantile(srs, 0.975)),
    }


# ---------------------------------------------------------------- variants
VARIANTS = {
    "V_top_bottom_3":     dict(k=3, hold_n=1),
    "V_top_bottom_5":     dict(k=5, hold_n=1),
    "V_top_bottom_3_24h": dict(k=3, hold_n=3),
}


def run_variant(name, cfg, fr_panel, px_at_fr):
    print(f"  >> {name}: k={cfg['k']} hold={cfg['hold_n']}")
    ann = ANN_FACTOR_8H if cfg["hold_n"] == 1 else ANN_FACTOR_24H

    res = backtest_xs(fr_panel, px_at_fr, k=cfg["k"], hold_n_events=cfg["hold_n"])
    rets = res["rets"]

    # IS/OOS split
    n_is = int(len(rets) * IS_FRAC)
    is_rets = rets.iloc[:n_is]
    oos_rets = rets.iloc[n_is:]

    is_stats = perf_stats(is_rets, ann)
    oos_stats = perf_stats(oos_rets, ann)
    full_stats = perf_stats(rets, ann)

    # Decomposition
    fund_pnl_total = float(res["fund_pnl"].sum())
    price_pnl_total = float(res["price_pnl"].sum())
    cost_total = float(res["cost"].sum())

    # Walk-forward
    wf = walk_forward(fr_panel, px_at_fr, k=cfg["k"], hold_n=cfg["hold_n"], n_folds=4)

    # Cost stress
    res_lo = backtest_xs(fr_panel, px_at_fr, k=cfg["k"], hold_n_events=cfg["hold_n"],
                         cost_bps=COST_BPS * 0.5)
    res_hi = backtest_xs(fr_panel, px_at_fr, k=cfg["k"], hold_n_events=cfg["hold_n"],
                         cost_bps=COST_BPS * 1.5)
    cost_stress = {
        "low_50pct":  perf_stats(res_lo["rets"], ann)["sharpe"],
        "base_100pct": full_stats["sharpe"],
        "high_150pct": perf_stats(res_hi["rets"], ann)["sharpe"],
    }

    # Permutation (lighter for 24h variant since fewer events but slower iteration)
    n_perm = 500
    perm = permutation_test(fr_panel, px_at_fr, k=cfg["k"], hold_n=cfg["hold_n"],
                            n_iter=n_perm)

    # Bootstrap CI on full sample
    boot = block_bootstrap_ci(rets, ann, block=21, n_iter=500)

    # DSR
    dsr_1 = deflated_sharpe_ratio(full_stats["sharpe"], len(rets), 1, rets)
    dsr_3 = deflated_sharpe_ratio(full_stats["sharpe"], len(rets), 3, rets)

    # Positioning frequency (which symbols ended long/short most often)
    long_count = res["long_count"].sort_values(ascending=False).to_dict()
    short_count = res["short_count"].sort_values(ascending=False).to_dict()

    return {
        "config": cfg,
        "n_events": int(len(rets)),
        "full": full_stats,
        "is": is_stats,
        "oos": oos_stats,
        "fund_pnl_total": fund_pnl_total,
        "price_pnl_total": price_pnl_total,
        "cost_total": cost_total,
        "walk_forward": wf,
        "cost_stress": cost_stress,
        "permutation": perm,
        "bootstrap_ci_sharpe": boot,
        "dsr_n1": dsr_1,
        "dsr_n3": dsr_3,
        "long_count": long_count,
        "short_count": short_count,
        "equity_curve": (1 + rets).cumprod().tolist(),
        "equity_idx":   [str(x) for x in rets.index],
    }


# ---------------------------------------------------------------- main
def main():
    t0 = time.time()
    print("Loading FR + price panels...")
    fr_panel, px_at_fr = build_panels()
    print(f"  FR panel: {fr_panel.shape}, range: {fr_panel.index.min()} .. {fr_panel.index.max()}")
    print(f"  Symbols kept: {list(fr_panel.columns)}")

    results = {}
    for name, cfg in VARIANTS.items():
        results[name] = run_variant(name, cfg, fr_panel, px_at_fr)

    # Save outputs
    out_path = ROOT / "wave_k127_bis_carry_xs.json"
    curves_path = ROOT / "wave_k127_curves.json"

    summary = {k: {kk: vv for kk, vv in v.items() if kk not in ("equity_curve", "equity_idx")}
               for k, v in results.items()}
    curves = {k: {"equity_curve": v["equity_curve"], "equity_idx": v["equity_idx"]}
              for k, v in results.items()}

    with open(out_path, "w") as f:
        json.dump(summary, f, indent=2, default=str)
    with open(curves_path, "w") as f:
        json.dump(curves, f, indent=2, default=str)

    elapsed = time.time() - t0
    print(f"\nDone in {elapsed:.1f}s")
    print(f"  -> {out_path}")
    print(f"  -> {curves_path}")

    # Console summary
    print("\n=== Summary ===")
    for name, r in results.items():
        full = r["full"]
        oos = r["oos"]
        perm = r["permutation"]
        print(f"{name:24s}  full SR={full['sharpe']:+.2f}  OOS SR={oos['sharpe']:+.2f}  "
              f"MaxDD={full['max_dd']:.2%}  p_perm={perm['p_value']:.3f}  DSR1={r['dsr_n1']:.3f}")


if __name__ == "__main__":
    main()

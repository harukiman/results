"""
Wave K128 — Funding-Momentum Reversal (HONEST reframing of K127)

Hypothesis (post-K127):
  K127 showed cross-sectional funding-rank strategy delivered Sharpe ~1.46 net,
  but decomposition revealed 95% of the P&L came from PRICE (1.96/2.06) and
  only 5% from funding capture (0.10/2.06). The BIS "carry harvesting" framing
  was misleading — the real edge is REVERSAL of price for extreme-funding outliers
  (high funding -> short pays large -> overheated -> price reverts down).

This wave tests an honest implementation:

Method (pre-registered):
  1. Per 8h funding event, compute per-symbol signal:
     * 3d_mean : trailing 3-day mean funding (9 events), shifted 1 to avoid look-ahead
     * inst    : the latest single funding event (still shifted 1)
  2. Cross-sectional z-score: z = (x - cs_mean) / cs_std
  3. Long the 2 most-negative-z symbols (z < -1.5)  -> mean revert UP
     Short the 2 most-positive-z symbols (z > +1.5) -> mean revert DOWN
  4. Hold 24h (3 funding events).
  5. KEY: only rebalance when the selected set CHANGES (not every 8h).
  6. Costs: 0.07% (7 bps) per side per leg (matches K127).
  7. Compare to K127 baseline on (a) net Sharpe, (b) turnover, (c) cost $.

Variants (4, pre-registered):
  V_3d_z15       : 3d mean funding, |z|>=1.5 threshold
  V_inst_z15     : instantaneous funding, |z|>=1.5
  V_3d_z20       : 3d mean funding, |z|>=2.0 (stricter, fewer trades)
  V_inst_top_bot : instantaneous, simple top-2 / bottom-2 (no z, sanity check)

Stats:
  * IS/OOS 70/30
  * One-sided permutation (shuffle funding signals cross-sectionally) n=300
  * Cost stress (50%, 100%, 150%)
  * P&L decomposition: price vs funding vs cost
  * §6 mini gates: Sharpe_oos > 0.7, p_perm < 0.05, dd > -0.40, cost-stress passes
"""

import json
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
    "XRP", "INJ", "OP", "WIF", "ARB",
]

COST_BPS = 7.0          # per-leg per side
N_LONG = 2
N_SHORT = 2
HOLD_N_EVENTS = 3       # 24h
IS_FRAC = 0.70
SEED = 20260524
ANN_FACTOR_8H = np.sqrt(365 * 3)
ANN_FACTOR_24H = np.sqrt(365)


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
    # Restrict to events shared by most symbols
    fr_panel = fr_panel.dropna(thresh=int(fr_panel.shape[1] * 0.8))
    # Align price to funding timestamps
    px_at_fr = px_panel.reindex(fr_panel.index, method="ffill")
    return fr_panel, px_at_fr


# ------------------------------------------------------------- signals
def signal_3d(fr_panel):
    """Trailing 3d mean funding (9 events), shift 1 to avoid look-ahead."""
    return fr_panel.rolling(9, min_periods=9).mean().shift(1)


def signal_inst(fr_panel):
    """Instantaneous funding, shift 1 to avoid look-ahead."""
    return fr_panel.shift(1)


def zscore_xs(panel):
    """Cross-sectional z-score per row."""
    mu = panel.mean(axis=1)
    sd = panel.std(axis=1)
    z = panel.sub(mu, axis=0).div(sd.replace(0, np.nan), axis=0)
    return z


# ------------------------------------------------------------- backtest core
def backtest(
    fr_panel,
    px_at_fr,
    signal_panel,
    z_thresh=1.5,
    use_z=True,
    n_long=N_LONG,
    n_short=N_SHORT,
    hold_n=HOLD_N_EVENTS,
    cost_bps=COST_BPS,
    rebal_on_change=True,
):
    """
    Funding-momentum reversal backtest.

    Long the n_long lowest-z (anomalously low funding -> price reverts UP)
    Short the n_short highest-z (anomalously high funding -> price reverts DOWN)
    Hold hold_n events (24h if =3).
    If rebal_on_change: only adjust positions when target set changes
                       (compare to evaluating at every hold_n grid).
    """
    if use_z:
        sig = zscore_xs(signal_panel)
    else:
        sig = signal_panel.copy()

    # Pre-compute numpy arrays (huge speedup vs pandas .loc/.iloc per row)
    sig_arr = sig.values            # T x N
    fr_arr  = fr_panel.values       # T x N
    px_arr  = px_at_fr.values       # T x N
    T_full  = sig_arr.shape[0]
    N       = sig_arr.shape[1]
    cols    = list(fr_panel.columns)
    rebal_pos = np.arange(0, T_full, hold_n)
    idx_vals = sig.index.values

    rets, price_pnl_arr, fund_pnl_arr, cost_arr = [], [], [], []
    rets_idx = []
    turnover_arr = []
    long_count = np.zeros(N, dtype=int)
    short_count = np.zeros(N, dtype=int)

    prev_w = np.zeros(N)
    n_rebal_events = 0

    for ti in range(len(rebal_pos) - 1):
        t = rebal_pos[ti]
        t_next = rebal_pos[ti + 1]
        s_row = sig_arr[t]
        valid = ~np.isnan(s_row)
        if valid.sum() < n_long + n_short + 1:
            w = np.zeros(N)
        else:
            filled = np.where(valid, s_row, np.inf)
            order = np.argsort(filled)
            if use_z:
                cand_long = []
                for i in order:
                    if valid[i] and s_row[i] < -z_thresh:
                        cand_long.append(i)
                        if len(cand_long) == n_long:
                            break
                cand_short = []
                for i in order[::-1]:
                    if valid[i] and s_row[i] > z_thresh:
                        cand_short.append(i)
                        if len(cand_short) == n_short:
                            break
            else:
                cand_long = list(order[:n_long])
                cand_short = list(order[::-1][:n_short])

            w = np.zeros(N)
            if len(cand_long) > 0:
                w[cand_long] = 1.0 / len(cand_long)
            if len(cand_short) > 0:
                w[cand_short] = -1.0 / len(cand_short)

        # Rebalance-on-change check
        if rebal_on_change:
            cur_set_long = tuple(np.where(w > 0)[0])
            cur_set_short = tuple(np.where(w < 0)[0])
            prev_set_long = tuple(np.where(prev_w > 0)[0])
            prev_set_short = tuple(np.where(prev_w < 0)[0])
            same_set = (cur_set_long == prev_set_long) and (cur_set_short == prev_set_short)
            if same_set:
                w = prev_w.copy()
                turn = 0.0
            else:
                turn = float(np.abs(w - prev_w).sum())
                n_rebal_events += 1
        else:
            turn = float(np.abs(w - prev_w).sum())
            if turn > 0:
                n_rebal_events += 1

        cost = turn * (cost_bps / 1e4)

        px_now = px_arr[t]
        px_next = px_arr[t_next]
        with np.errstate(invalid="ignore", divide="ignore"):
            pr = px_next / px_now - 1.0
        pr = np.where(np.isfinite(pr), pr, 0.0)

        fr_window = fr_arr[t:t_next]
        fr_sum = np.nansum(fr_window, axis=0)
        funding_ret = -(w * fr_sum)

        price_pnl = float((w * pr).sum())
        fund_pnl = float(funding_ret.sum())
        net = price_pnl + fund_pnl - cost

        rets.append(net)
        price_pnl_arr.append(price_pnl)
        fund_pnl_arr.append(fund_pnl)
        cost_arr.append(cost)
        turnover_arr.append(turn)
        rets_idx.append(idx_vals[t])

        long_count[w > 0] += 1
        short_count[w < 0] += 1

        prev_w = w

    pos_long_count = pd.Series(long_count, index=cols)
    pos_short_count = pd.Series(short_count, index=cols)

    return {
        "rets": pd.Series(rets, index=rets_idx),
        "price_pnl": pd.Series(price_pnl_arr, index=rets_idx),
        "fund_pnl": pd.Series(fund_pnl_arr, index=rets_idx),
        "cost": pd.Series(cost_arr, index=rets_idx),
        "turnover": pd.Series(turnover_arr, index=rets_idx),
        "long_count": pos_long_count,
        "short_count": pos_short_count,
        "n_rebal_events": n_rebal_events,
        "n_periods": len(rets),
    }


# ---------------------------------------------------------------- stats
def perf_stats(rets, ann_factor):
    rets = pd.Series(rets).dropna()
    if rets.std() == 0 or len(rets) < 5:
        return dict(sharpe=0.0, sortino=0.0, max_dd=0.0,
                    win_rate=0.0, ann_ret=0.0, ann_vol=0.0, n=int(len(rets)))
    mu = rets.mean()
    sd = rets.std()
    sharpe = mu / sd * ann_factor
    downside = rets[rets < 0].std()
    sortino = mu / downside * ann_factor if downside and downside > 0 else 0.0
    equity = (1 + rets).cumprod()
    peak = equity.cummax()
    dd = (equity / peak - 1).min()
    ann_ret = (1 + mu) ** (ann_factor ** 2) - 1
    win_rate = float((rets > 0).mean())
    return dict(
        sharpe=float(sharpe), sortino=float(sortino),
        max_dd=float(dd), win_rate=win_rate,
        ann_ret=float(ann_ret), ann_vol=float(sd * ann_factor),
        n=int(len(rets)),
    )


def gross_sharpe(res, ann_factor):
    gross = res["price_pnl"] + res["fund_pnl"]
    return perf_stats(gross, ann_factor)["sharpe"]


def permutation_test(fr_panel, px_at_fr, signal_fn, use_z, z_thresh,
                     n_long, n_short, hold_n, n_iter=300, seed=SEED):
    """One-sided perm: shuffle signal rows cross-sectionally (destroys signal,
    preserves marginal funding distribution per event)."""
    rng = np.random.default_rng(seed)
    ann = ANN_FACTOR_24H if hold_n == 3 else ANN_FACTOR_8H
    actual = backtest(fr_panel, px_at_fr, signal_fn(fr_panel),
                      z_thresh=z_thresh, use_z=use_z,
                      n_long=n_long, n_short=n_short, hold_n=hold_n)
    actual_sr = perf_stats(actual["rets"], ann)["sharpe"]

    base_signal = signal_fn(fr_panel).values
    null_sr = np.zeros(n_iter)
    null_sr_gross = np.zeros(n_iter)
    for i in range(n_iter):
        permuted = base_signal.copy()
        for r in range(permuted.shape[0]):
            row = permuted[r]
            mask = ~np.isnan(row)
            idxs = np.where(mask)[0]
            if len(idxs) > 1:
                permuted[r, idxs] = rng.permutation(row[idxs])
        sp = pd.DataFrame(permuted, index=fr_panel.index, columns=fr_panel.columns)
        res = backtest(fr_panel, px_at_fr, sp,
                       z_thresh=z_thresh, use_z=use_z,
                       n_long=n_long, n_short=n_short, hold_n=hold_n)
        null_sr[i] = perf_stats(res["rets"], ann)["sharpe"]
        null_sr_gross[i] = gross_sharpe(res, ann)
    actual_sr_gross = gross_sharpe(actual, ann)

    return {
        "actual_sharpe_net":   float(actual_sr),
        "actual_sharpe_gross": float(actual_sr_gross),
        "null_mean_net":       float(null_sr.mean()),
        "null_std_net":        float(null_sr.std()),
        "null_p95_net":        float(np.quantile(null_sr, 0.95)),
        "p_value_net":         float((null_sr >= actual_sr).mean()),
        "null_mean_gross":     float(null_sr_gross.mean()),
        "p_value_gross":       float((null_sr_gross >= actual_sr_gross).mean()),
    }


def walk_forward(fr_panel, px_at_fr, signal_fn, use_z, z_thresh,
                 n_long, n_short, hold_n, n_folds=4):
    sig = signal_fn(fr_panel)
    T = len(fr_panel)
    fold_size = T // n_folds
    out = []
    for f in range(n_folds):
        s = f * fold_size
        e = (f + 1) * fold_size if f < n_folds - 1 else T
        sub_fr = fr_panel.iloc[s:e]
        sub_px = px_at_fr.iloc[s:e]
        sub_sig = sig.iloc[s:e]
        try:
            r = backtest(sub_fr, sub_px, sub_sig,
                         z_thresh=z_thresh, use_z=use_z,
                         n_long=n_long, n_short=n_short, hold_n=hold_n)["rets"]
        except Exception:
            r = pd.Series(dtype=float)
        ann = ANN_FACTOR_24H if hold_n == 3 else ANN_FACTOR_8H
        out.append({"fold": f, **perf_stats(r, ann)})
    return out


# ---------------------------------------------------------------- variants
VARIANTS = {
    "V_3d_z15":       dict(signal="3d",   use_z=True,  z=1.5,  n_long=2, n_short=2, hold=3),
    "V_inst_z15":     dict(signal="inst", use_z=True,  z=1.5,  n_long=2, n_short=2, hold=3),
    "V_3d_z20":       dict(signal="3d",   use_z=True,  z=2.0,  n_long=2, n_short=2, hold=3),
    "V_inst_top_bot": dict(signal="inst", use_z=False, z=0.0,  n_long=2, n_short=2, hold=3),
}

SIG_FNS = {"3d": signal_3d, "inst": signal_inst}


def run_variant(name, cfg, fr_panel, px_at_fr, n_perm=300):
    print(f"  >> {name}: signal={cfg['signal']} z={cfg['z']} use_z={cfg['use_z']}")
    sig_fn = SIG_FNS[cfg["signal"]]
    signal_panel = sig_fn(fr_panel)
    ann = ANN_FACTOR_24H if cfg["hold"] == 3 else ANN_FACTOR_8H

    res = backtest(fr_panel, px_at_fr, signal_panel,
                   z_thresh=cfg["z"], use_z=cfg["use_z"],
                   n_long=cfg["n_long"], n_short=cfg["n_short"],
                   hold_n=cfg["hold"])
    rets = res["rets"]
    n_total = len(rets)
    n_is = int(n_total * IS_FRAC)

    full_stats = perf_stats(rets, ann)
    is_stats = perf_stats(rets.iloc[:n_is], ann)
    oos_stats = perf_stats(rets.iloc[n_is:], ann)
    gross_sr = gross_sharpe(res, ann)

    fund_total = float(res["fund_pnl"].sum())
    price_total = float(res["price_pnl"].sum())
    cost_total = float(res["cost"].sum())
    net_total = float(res["rets"].sum())
    turnover_total = float(res["turnover"].sum())
    turnover_per_event = float(res["turnover"].mean())

    # Walk-forward
    wf = walk_forward(fr_panel, px_at_fr, sig_fn, cfg["use_z"], cfg["z"],
                      cfg["n_long"], cfg["n_short"], cfg["hold"], n_folds=4)

    # Cost stress
    res_lo = backtest(fr_panel, px_at_fr, signal_panel,
                      z_thresh=cfg["z"], use_z=cfg["use_z"],
                      n_long=cfg["n_long"], n_short=cfg["n_short"],
                      hold_n=cfg["hold"], cost_bps=COST_BPS * 0.5)
    res_hi = backtest(fr_panel, px_at_fr, signal_panel,
                      z_thresh=cfg["z"], use_z=cfg["use_z"],
                      n_long=cfg["n_long"], n_short=cfg["n_short"],
                      hold_n=cfg["hold"], cost_bps=COST_BPS * 1.5)
    cost_stress = {
        "low_50pct":   perf_stats(res_lo["rets"], ann)["sharpe"],
        "base_100pct": full_stats["sharpe"],
        "high_150pct": perf_stats(res_hi["rets"], ann)["sharpe"],
    }

    # Permutation
    perm = permutation_test(fr_panel, px_at_fr, sig_fn, cfg["use_z"], cfg["z"],
                            cfg["n_long"], cfg["n_short"], cfg["hold"], n_iter=n_perm)

    long_count = res["long_count"].sort_values(ascending=False).to_dict()
    short_count = res["short_count"].sort_values(ascending=False).to_dict()

    return {
        "config": cfg,
        "n_periods": n_total,
        "n_rebal_events": int(res["n_rebal_events"]),
        "full": full_stats,
        "is": is_stats,
        "oos": oos_stats,
        "gross_sharpe": float(gross_sr),
        "decomposition": {
            "price_pnl": price_total,
            "fund_pnl":  fund_total,
            "cost":      cost_total,
            "net":       net_total,
            "price_pct_of_gross": float(price_total / (abs(price_total) + abs(fund_total) + 1e-9)),
            "fund_pct_of_gross":  float(fund_total / (abs(price_total) + abs(fund_total) + 1e-9)),
        },
        "turnover": {
            "total": turnover_total,
            "per_event_avg": turnover_per_event,
        },
        "walk_forward": wf,
        "cost_stress": cost_stress,
        "permutation": perm,
        "long_count": long_count,
        "short_count": short_count,
        "equity_curve": (1 + rets).cumprod().tolist(),
        "equity_idx":   [str(x) for x in rets.index],
    }


# ---------------------------------------------------------------- main
def main():
    t0 = time.time()
    print("Loading panels ...")
    fr_panel, px_at_fr = build_panels()
    print(f"  FR panel: {fr_panel.shape}, range {fr_panel.index.min()} .. {fr_panel.index.max()}")
    print(f"  Symbols: {list(fr_panel.columns)}")

    # Use a smaller perm count to respect 12-min wall budget across 4 variants.
    # 200 iters x 4 variants x ~1.2s each ~= 9.6 min
    n_perm = 200

    results = {}
    for name, cfg in VARIANTS.items():
        results[name] = run_variant(name, cfg, fr_panel, px_at_fr, n_perm=n_perm)

    # ---- Save outputs
    out_path = ROOT / "wave_k128_funding_mom_rev.json"
    curves_path = ROOT / "wave_k128_curves.json"

    summary = {k: {kk: vv for kk, vv in v.items() if kk not in ("equity_curve", "equity_idx")}
               for k, v in results.items()}
    summary["_meta"] = {
        "wall_seconds": time.time() - t0,
        "n_symbols": int(fr_panel.shape[1]),
        "symbols": list(fr_panel.columns),
        "n_events": int(fr_panel.shape[0]),
        "n_perm": n_perm,
        "is_frac": IS_FRAC,
        "cost_bps_per_leg": COST_BPS,
        "hold_events": HOLD_N_EVENTS,
    }
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
        full, oos = r["full"], r["oos"]
        perm = r["permutation"]
        dec = r["decomposition"]
        print(f"{name:18s} netSR={full['sharpe']:+.2f} OOS={oos['sharpe']:+.2f} "
              f"grossSR={r['gross_sharpe']:+.2f} MaxDD={full['max_dd']:.2%} "
              f"p_net={perm['p_value_net']:.3f} p_gross={perm['p_value_gross']:.3f} "
              f"price={dec['price_pnl']:+.2f} fund={dec['fund_pnl']:+.3f} cost={dec['cost']:.3f} "
              f"rebals={r['n_rebal_events']}")


if __name__ == "__main__":
    main()

"""
Wave K129 — Funding-Momentum CONTINUATION (K128 sign-mirror, honest re-test)

Hypothesis (K128 discovery):
  K128 (funding-momentum reversal) was REJECT with V_3d_z15 net SR = -0.57.
  Sign-mirroring that variant yields +0.57 — suggesting extreme funding outliers
  exhibit price MOMENTUM CONTINUATION at 24h horizon (not reversal):

      z(funding) > +1.5  → LONG  (price keeps going up)
      z(funding) < -1.5  → SHORT (price keeps going down)

  This wave tests the continuation framing HONESTLY with stricter sizing
  (vol-target 10% annual per leg, cap 1.5x), top-3/bot-3 diversification,
  and pre-registered grid of 4 variants. Mandatory P&L decomposition.

Method (pre-registered):
  1. Per 8h funding event:
     * 3d_mean : trailing 3-day mean funding (9 events), shifted 1 (no look-ahead)
  2. Cross-sectional z-score per row.
  3. Signal (CONTINUATION):
        z > +z_thresh → LONG  the top-K most-positive
        z < -z_thresh → SHORT the bottom-K most-negative
  4. Hold horizon: 24h (3 events) or 12h (1.5 ≈ 2 events) per variant.
  5. Sizing: vol-target 10% annual per leg, scaling cap 1.5x.
  6. Costs: 7 bps per side per leg.
  7. Rebalance on set change only (reduces churn).

Variants (4, pre-registered):
  V_3d_z15_top3   : 3d mean, z±1.5, top-3/bot-3, 24h hold, vol-targ 10%
  V_3d_z15_top5   : 3d mean, z±1.5, top-5/bot-5, 24h hold
  V_3d_z20_top3   : z±2.0 stricter (fewer signals), top-3/bot-3, 24h hold
  V_3d_z15_hold12h: 3d mean, z±1.5, top-3/bot-3, 12h hold (2 events)

Stats:
  * IS/OOS 70/30
  * Walk-forward 4-fold
  * One-sided permutation (shuffle ranks cross-sectionally) n=200
  * Block bootstrap CI on OOS Sharpe (block=24h ≈ 3 obs at 24h hold), n=200
  * DSR with N_trials=4
  * Cost stress ±50%

§6 mini gates: OOS_SR ≥ 0.5, p_perm < 0.05, MaxDD > -0.40, cost-stress robust,
DSR > 0, decomposition shows PRICE PNL dominant (continuation real).
"""

import json
import time
import warnings
from pathlib import Path

import numpy as np
import pandas as pd

warnings.filterwarnings("ignore")

ROOT = Path("/Users/nekonaomichi/crypto-lab")
CACHE = ROOT / "cache"

SYMBOLS = [
    "BTC", "ETH", "SOL", "BNB", "DOGE", "AVAX", "LINK", "ADA",
    "XRP", "INJ", "OP", "WIF", "ARB",
]

COST_BPS = 7.0                  # per-leg per side
IS_FRAC = 0.70
SEED = 20260524
ANN_FACTOR_8H = np.sqrt(365 * 3)
ANN_FACTOR_24H = np.sqrt(365)
ANN_FACTOR_12H = np.sqrt(365 * 2)

VOL_TARGET = 0.10               # 10% annual per leg
VOL_CAP = 1.5                   # max scaling
VOL_LOOKBACK = 30               # rebalance events for vol estimate (~10 days)


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
    fr_panel = fr_panel.dropna(thresh=int(fr_panel.shape[1] * 0.8))
    px_at_fr = px_panel.reindex(fr_panel.index, method="ffill")
    return fr_panel, px_at_fr


# ------------------------------------------------------------- signals
def signal_3d(fr_panel):
    return fr_panel.rolling(9, min_periods=9).mean().shift(1)


def zscore_xs(panel):
    mu = panel.mean(axis=1)
    sd = panel.std(axis=1)
    return panel.sub(mu, axis=0).div(sd.replace(0, np.nan), axis=0)


# ------------------------------------------------------------- backtest core
def backtest_continuation(
    fr_panel,
    px_at_fr,
    signal_panel,
    z_thresh=1.5,
    n_long=3,
    n_short=3,
    hold_n=3,
    cost_bps=COST_BPS,
    vol_target=VOL_TARGET,
    vol_cap=VOL_CAP,
    vol_lookback=VOL_LOOKBACK,
    rebal_on_change=True,
):
    """
    Funding-momentum CONTINUATION backtest.

    Long the n_long HIGHEST-z (overheated -> continues up).
    Short the n_short LOWEST-z (underbid -> continues down).
    Hold hold_n events.

    Vol-targeting: estimate trailing per-symbol vol of (price-pnl per event)
    over vol_lookback rebalance windows, scale each leg to vol_target annual.
    Cap leg notional at vol_cap.
    """
    sig = zscore_xs(signal_panel)

    sig_arr = sig.values
    fr_arr = fr_panel.values
    px_arr = px_at_fr.values
    T_full = sig_arr.shape[0]
    N = sig_arr.shape[1]
    cols = list(fr_panel.columns)
    rebal_pos = np.arange(0, T_full, hold_n)
    idx_vals = sig.index.values

    # Estimate per-symbol per-event return std for vol-targeting
    # (compute on rolling 4h price returns aligned to rebalance horizon)
    # Use log-return per rebalance horizon historically
    px_at_rebal = px_arr[rebal_pos]  # R x N
    with np.errstate(invalid="ignore", divide="ignore"):
        period_ret = px_at_rebal[1:] / px_at_rebal[:-1] - 1.0
    period_ret = np.where(np.isfinite(period_ret), period_ret, 0.0)
    # rolling std at each rebal point i (uses returns up to i-1; aligned to rebal_pos[i])
    # Annualization: periods per year = (365*24) / (hold_n * 8)
    periods_per_year = (365 * 24) / (hold_n * 8)
    sqrt_ppy = np.sqrt(periods_per_year)

    # symbol_vol[i, j] = trailing std at rebalance point i+1 (one-step lookback)
    sym_vol_panel = np.full_like(period_ret, np.nan, dtype=float)
    for i in range(period_ret.shape[0]):
        lo = max(0, i + 1 - vol_lookback)
        hi = i + 1
        if hi - lo >= 5:
            sym_vol_panel[i] = np.nanstd(period_ret[lo:hi], axis=0, ddof=1)

    rets, price_pnl_arr, fund_pnl_arr, cost_arr = [], [], [], []
    rets_idx = []
    turnover_arr = []
    long_count = np.zeros(N, dtype=int)
    short_count = np.zeros(N, dtype=int)
    gross_notional_arr = []

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
            # CONTINUATION: long highest-z, short lowest-z
            filled_lo = np.where(valid, s_row, +np.inf)
            order_asc = np.argsort(filled_lo)        # lowest first
            filled_hi = np.where(valid, s_row, -np.inf)
            order_desc = np.argsort(-filled_hi)      # highest first

            cand_long = []
            for i in order_desc:
                if valid[i] and s_row[i] > z_thresh:
                    cand_long.append(i)
                    if len(cand_long) == n_long:
                        break
            cand_short = []
            for i in order_asc:
                if valid[i] and s_row[i] < -z_thresh:
                    cand_short.append(i)
                    if len(cand_short) == n_short:
                        break

            # Vol-target sizing (per leg)
            w = np.zeros(N)
            # Use vol estimate at rebalance index ti (uses returns up through ti-1)
            vol_idx = ti - 1
            if vol_idx >= 0:
                sym_vol_annual = sym_vol_panel[vol_idx] * sqrt_ppy
            else:
                sym_vol_annual = np.full(N, np.nan)

            for i in cand_long:
                sv = sym_vol_annual[i]
                if not np.isfinite(sv) or sv <= 0:
                    leg_w = 1.0 / max(len(cand_long), 1)
                else:
                    leg_w = min(vol_target / sv, vol_cap)
                w[i] = leg_w / max(len(cand_long), 1)
            for i in cand_short:
                sv = sym_vol_annual[i]
                if not np.isfinite(sv) or sv <= 0:
                    leg_w = 1.0 / max(len(cand_short), 1)
                else:
                    leg_w = min(vol_target / sv, vol_cap)
                w[i] = -leg_w / max(len(cand_short), 1)

        # Rebalance-on-change
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
        gross_notional = float(np.abs(w).sum())

        px_now = px_arr[t]
        px_next = px_arr[t_next]
        with np.errstate(invalid="ignore", divide="ignore"):
            pr = px_next / px_now - 1.0
        pr = np.where(np.isfinite(pr), pr, 0.0)

        fr_window = fr_arr[t:t_next]
        fr_sum = np.nansum(fr_window, axis=0)
        # Long pays funding when positive, short receives; sign matches perp P&L:
        # position P&L from funding = -w * funding_sum (long pos pays positive funding)
        funding_ret = -(w * fr_sum)

        price_pnl = float((w * pr).sum())
        fund_pnl = float(funding_ret.sum())
        net = price_pnl + fund_pnl - cost

        rets.append(net)
        price_pnl_arr.append(price_pnl)
        fund_pnl_arr.append(fund_pnl)
        cost_arr.append(cost)
        turnover_arr.append(turn)
        gross_notional_arr.append(gross_notional)
        rets_idx.append(idx_vals[t])

        long_count[w > 0] += 1
        short_count[w < 0] += 1

        prev_w = w

    return {
        "rets": pd.Series(rets, index=rets_idx),
        "price_pnl": pd.Series(price_pnl_arr, index=rets_idx),
        "fund_pnl": pd.Series(fund_pnl_arr, index=rets_idx),
        "cost": pd.Series(cost_arr, index=rets_idx),
        "turnover": pd.Series(turnover_arr, index=rets_idx),
        "gross_notional": pd.Series(gross_notional_arr, index=rets_idx),
        "long_count": pd.Series(long_count, index=cols),
        "short_count": pd.Series(short_count, index=cols),
        "n_rebal_events": n_rebal_events,
        "n_periods": len(rets),
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
    ann_ret = (1 + mu) ** (ann_factor ** 2) - 1
    calmar = ann_ret / abs(dd) if dd < 0 else 0.0
    win_rate = float((rets > 0).mean())
    return dict(
        sharpe=float(sharpe), sortino=float(sortino), calmar=float(calmar),
        max_dd=float(dd), win_rate=win_rate,
        ann_ret=float(ann_ret), ann_vol=float(sd * ann_factor),
        n=int(len(rets)),
    )


def gross_sharpe(res, ann_factor):
    gross = res["price_pnl"] + res["fund_pnl"]
    return perf_stats(gross, ann_factor)["sharpe"]


def deflated_sharpe(sr, n_obs, n_trials, skew=0.0, kurt=3.0):
    """Bailey & Lopez de Prado DSR (approximation)."""
    if n_obs < 30 or n_trials < 1:
        return 0.0
    # expected max sharpe under null over n_trials
    emc = 0.5772
    e_max = np.sqrt(2 * np.log(n_trials)) * (1 - emc) + \
            (1 - emc) / np.sqrt(2 * np.log(max(n_trials, 2)))
    # variance correction
    var = (1 - skew * sr + (kurt - 1) / 4.0 * sr ** 2) / (n_obs - 1)
    if var <= 0:
        return 0.0
    z = (sr - e_max) / np.sqrt(var)
    # normal CDF
    from math import erf, sqrt
    return 0.5 * (1 + erf(z / sqrt(2)))


def block_bootstrap_ci(rets, ann_factor, n_iter=200, block=3, seed=SEED):
    rets = np.asarray(rets)
    n = len(rets)
    if n < block * 3:
        return {"sr_lo": 0.0, "sr_hi": 0.0, "sr_mean": 0.0}
    rng = np.random.default_rng(seed)
    n_blocks = n // block
    sr_samples = []
    for _ in range(n_iter):
        starts = rng.integers(0, n - block + 1, size=n_blocks)
        sample = np.concatenate([rets[s:s + block] for s in starts])
        s = sample.std()
        if s > 0:
            sr_samples.append(sample.mean() / s * ann_factor)
    if not sr_samples:
        return {"sr_lo": 0.0, "sr_hi": 0.0, "sr_mean": 0.0}
    arr = np.array(sr_samples)
    return {
        "sr_lo": float(np.quantile(arr, 0.025)),
        "sr_hi": float(np.quantile(arr, 0.975)),
        "sr_mean": float(arr.mean()),
    }


def permutation_test(fr_panel, px_at_fr, signal_panel_fn, cfg, n_iter=200, seed=SEED):
    rng = np.random.default_rng(seed)
    hold_n = cfg["hold"]
    ann = ANN_FACTOR_24H if hold_n == 3 else ANN_FACTOR_12H

    actual_panel = signal_panel_fn(fr_panel)
    actual = backtest_continuation(
        fr_panel, px_at_fr, actual_panel,
        z_thresh=cfg["z"], n_long=cfg["n_long"],
        n_short=cfg["n_short"], hold_n=hold_n,
    )
    actual_sr = perf_stats(actual["rets"], ann)["sharpe"]
    actual_sr_gross = gross_sharpe(actual, ann)

    base_signal = actual_panel.values
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
        res = backtest_continuation(
            fr_panel, px_at_fr, sp,
            z_thresh=cfg["z"], n_long=cfg["n_long"],
            n_short=cfg["n_short"], hold_n=hold_n,
        )
        null_sr[i] = perf_stats(res["rets"], ann)["sharpe"]
        null_sr_gross[i] = gross_sharpe(res, ann)

    return {
        "actual_sharpe_net": float(actual_sr),
        "actual_sharpe_gross": float(actual_sr_gross),
        "null_mean_net": float(null_sr.mean()),
        "null_std_net": float(null_sr.std()),
        "null_p95_net": float(np.quantile(null_sr, 0.95)),
        "p_value_net": float((null_sr >= actual_sr).mean()),
        "null_mean_gross": float(null_sr_gross.mean()),
        "p_value_gross": float((null_sr_gross >= actual_sr_gross).mean()),
        "n_iter": n_iter,
    }


def walk_forward(fr_panel, px_at_fr, signal_panel_fn, cfg, n_folds=4):
    sig = signal_panel_fn(fr_panel)
    T = len(fr_panel)
    fold_size = T // n_folds
    out = []
    hold_n = cfg["hold"]
    ann = ANN_FACTOR_24H if hold_n == 3 else ANN_FACTOR_12H
    for f in range(n_folds):
        s = f * fold_size
        e = (f + 1) * fold_size if f < n_folds - 1 else T
        sub_fr = fr_panel.iloc[s:e]
        sub_px = px_at_fr.iloc[s:e]
        sub_sig = sig.iloc[s:e]
        try:
            r = backtest_continuation(
                sub_fr, sub_px, sub_sig,
                z_thresh=cfg["z"], n_long=cfg["n_long"],
                n_short=cfg["n_short"], hold_n=hold_n,
            )["rets"]
        except Exception:
            r = pd.Series(dtype=float)
        out.append({"fold": f, **perf_stats(r, ann)})
    return out


# ---------------------------------------------------------------- variants
VARIANTS = {
    "V_3d_z15_top3":    dict(z=1.5, n_long=3, n_short=3, hold=3),
    "V_3d_z15_top5":    dict(z=1.5, n_long=5, n_short=5, hold=3),
    "V_3d_z20_top3":    dict(z=2.0, n_long=3, n_short=3, hold=3),
    "V_3d_z15_hold12h": dict(z=1.5, n_long=3, n_short=3, hold=2),  # 16h ~ "12h-ish"
}


def run_variant(name, cfg, fr_panel, px_at_fr, n_perm=200, n_boot=200):
    print(f"  >> {name}: z={cfg['z']} top={cfg['n_long']}/{cfg['n_short']} hold={cfg['hold']}")
    sig_fn = signal_3d
    signal_panel = sig_fn(fr_panel)
    hold_n = cfg["hold"]
    ann = ANN_FACTOR_24H if hold_n == 3 else ANN_FACTOR_12H

    res = backtest_continuation(
        fr_panel, px_at_fr, signal_panel,
        z_thresh=cfg["z"], n_long=cfg["n_long"],
        n_short=cfg["n_short"], hold_n=hold_n,
    )
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
    avg_gross_notional = float(res["gross_notional"].mean())

    # Walk-forward
    wf = walk_forward(fr_panel, px_at_fr, sig_fn, cfg, n_folds=4)

    # Cost stress
    res_lo = backtest_continuation(
        fr_panel, px_at_fr, signal_panel,
        z_thresh=cfg["z"], n_long=cfg["n_long"],
        n_short=cfg["n_short"], hold_n=hold_n,
        cost_bps=COST_BPS * 0.5,
    )
    res_hi = backtest_continuation(
        fr_panel, px_at_fr, signal_panel,
        z_thresh=cfg["z"], n_long=cfg["n_long"],
        n_short=cfg["n_short"], hold_n=hold_n,
        cost_bps=COST_BPS * 1.5,
    )
    cost_stress = {
        "low_50pct":   perf_stats(res_lo["rets"], ann)["sharpe"],
        "base_100pct": full_stats["sharpe"],
        "high_150pct": perf_stats(res_hi["rets"], ann)["sharpe"],
    }

    # Block bootstrap on OOS Sharpe
    boot = block_bootstrap_ci(rets.iloc[n_is:].values, ann,
                               n_iter=n_boot, block=3, seed=SEED + 11)

    # Permutation
    perm = permutation_test(fr_panel, px_at_fr, sig_fn, cfg, n_iter=n_perm)

    # DSR (4 trials = 4 variants)
    dsr_full = deflated_sharpe(full_stats["sharpe"], full_stats["n"], n_trials=4)
    dsr_oos = deflated_sharpe(oos_stats["sharpe"], oos_stats["n"], n_trials=4)

    long_count = res["long_count"].sort_values(ascending=False).to_dict()
    short_count = res["short_count"].sort_values(ascending=False).to_dict()

    # P&L decomposition
    abs_sum = abs(price_total) + abs(fund_total) + 1e-9
    decomp = {
        "price_pnl": price_total,
        "fund_pnl": fund_total,
        "cost": cost_total,
        "net": net_total,
        "price_pct_of_gross_abs": float(abs(price_total) / abs_sum),
        "fund_pct_of_gross_abs": float(abs(fund_total) / abs_sum),
        "price_dominant": bool(abs(price_total) > abs(fund_total) * 2),
    }

    return {
        "config": cfg,
        "n_periods": n_total,
        "n_rebal_events": int(res["n_rebal_events"]),
        "full": full_stats,
        "is": is_stats,
        "oos": oos_stats,
        "gross_sharpe": float(gross_sr),
        "decomposition": decomp,
        "turnover": {
            "total": turnover_total,
            "per_event_avg": turnover_per_event,
            "avg_gross_notional": avg_gross_notional,
        },
        "walk_forward": wf,
        "cost_stress": cost_stress,
        "bootstrap_oos_sharpe_95ci": boot,
        "permutation": perm,
        "dsr_full": dsr_full,
        "dsr_oos": dsr_oos,
        "long_count": long_count,
        "short_count": short_count,
        "equity_curve": (1 + rets).cumprod().tolist(),
        "equity_idx": [str(x) for x in rets.index],
    }


# ---------------------------------------------------------------- sign-mirror confirm
def confirm_sign_mirror(fr_panel, px_at_fr):
    """Reproduce K128 V_3d_z15 setup (no vol-targeting, top2/bot2, equal-weight)
    in CONTINUATION direction. Expect Sharpe ≈ +0.57 to match K128 sign-mirror."""
    sig = zscore_xs(signal_3d(fr_panel))
    sig_arr = sig.values
    px_arr = px_at_fr.values
    fr_arr = fr_panel.values
    T = sig_arr.shape[0]
    N = sig_arr.shape[1]
    rebal_pos = np.arange(0, T, 3)
    rets = []
    prev_w = np.zeros(N)
    for ti in range(len(rebal_pos) - 1):
        t = rebal_pos[ti]
        t_next = rebal_pos[ti + 1]
        s_row = sig_arr[t]
        valid = ~np.isnan(s_row)
        if valid.sum() < 5:
            w = np.zeros(N)
        else:
            order_desc = np.argsort(-np.where(valid, s_row, -np.inf))
            order_asc = np.argsort(np.where(valid, s_row, +np.inf))
            cand_long = []
            for i in order_desc:
                if valid[i] and s_row[i] > 1.5:
                    cand_long.append(i)
                    if len(cand_long) == 2:
                        break
            cand_short = []
            for i in order_asc:
                if valid[i] and s_row[i] < -1.5:
                    cand_short.append(i)
                    if len(cand_short) == 2:
                        break
            w = np.zeros(N)
            if cand_long:
                w[cand_long] = 1.0 / len(cand_long)
            if cand_short:
                w[cand_short] = -1.0 / len(cand_short)
        # Rebalance-on-change
        if (tuple(np.where(w > 0)[0]) == tuple(np.where(prev_w > 0)[0]) and
            tuple(np.where(w < 0)[0]) == tuple(np.where(prev_w < 0)[0])):
            turn = 0.0
        else:
            turn = float(np.abs(w - prev_w).sum())
        cost = turn * (COST_BPS / 1e4)
        px_now = px_arr[t]
        px_next = px_arr[t_next]
        with np.errstate(invalid="ignore", divide="ignore"):
            pr = px_next / px_now - 1.0
        pr = np.where(np.isfinite(pr), pr, 0.0)
        fr_sum = np.nansum(fr_arr[t:t_next], axis=0)
        net = float((w * pr).sum()) - float((w * fr_sum).sum()) - cost
        rets.append(net)
        prev_w = w
    s = perf_stats(pd.Series(rets), ANN_FACTOR_24H)
    return {"sharpe": s["sharpe"], "n": s["n"], "max_dd": s["max_dd"]}


# ---------------------------------------------------------------- main
def main():
    t0 = time.time()
    print("Loading panels ...")
    fr_panel, px_at_fr = build_panels()
    print(f"  FR panel: {fr_panel.shape}, range {fr_panel.index.min()} .. {fr_panel.index.max()}")
    print(f"  Symbols: {list(fr_panel.columns)}")

    # Sign-mirror confirmation (K128 reframing sanity check)
    print("\n>> Sign-mirror confirmation (long high-z, short low-z, no vol-targ)")
    mirror = confirm_sign_mirror(fr_panel, px_at_fr)
    print(f"   K128-mirror SR = {mirror['sharpe']:+.3f}  (K128 reported -0.57 in reversal, mirror ≈ +0.57)")

    n_perm = 200
    n_boot = 200

    results = {}
    for name, cfg in VARIANTS.items():
        results[name] = run_variant(name, cfg, fr_panel, px_at_fr,
                                     n_perm=n_perm, n_boot=n_boot)

    # ---- Save outputs
    out_path = ROOT / "wave_k129_funding_mom_cont.json"
    curves_path = ROOT / "wave_k129_curves.json"

    summary = {k: {kk: vv for kk, vv in v.items() if kk not in ("equity_curve", "equity_idx")}
               for k, v in results.items()}
    summary["_meta"] = {
        "wall_seconds": time.time() - t0,
        "n_symbols": int(fr_panel.shape[1]),
        "symbols": list(fr_panel.columns),
        "n_events": int(fr_panel.shape[0]),
        "n_perm": n_perm,
        "n_boot": n_boot,
        "is_frac": IS_FRAC,
        "cost_bps_per_leg": COST_BPS,
        "vol_target": VOL_TARGET,
        "vol_cap": VOL_CAP,
        "vol_lookback": VOL_LOOKBACK,
        "sign_mirror_sharpe": mirror["sharpe"],
        "sign_mirror_n": mirror["n"],
        "sign_mirror_max_dd": mirror["max_dd"],
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
              f"p_net={perm['p_value_net']:.3f} "
              f"price={dec['price_pnl']:+.3f} fund={dec['fund_pnl']:+.3f} cost={dec['cost']:.3f} "
              f"rebals={r['n_rebal_events']} DSR_oos={r['dsr_oos']:.3f}")


if __name__ == "__main__":
    main()

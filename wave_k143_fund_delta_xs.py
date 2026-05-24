"""
Wave K143 — Funding-Rate ΔXS (CHANGE-based) Predictor (R5-3 / Presto Research)

Hypothesis (Presto Research):
  Cross-sectional sort by funding rate CHANGE (Δ), not level.
    Δfr_n = fr_now − fr_(now − n events)   (e.g. n=21 → 7-day change)
  - Symbols with biggest funding INCREASE → over-heating → expected reversal → SHORT
  - Symbols with biggest funding DECREASE → cooling     → expected mean-revert → LONG
  Presto reports 12.5% R² on 7d single-asset; XS rank should work better than ts.

Distinction from prior funding waves:
  K127 (level rank): low Sharpe ~0.5 OOS
  K133 (level z-score reversal): ACCEPT 5/6 gates (V_rev_3d_z15 OOS_SR=0.83)
  K143 (CHANGE rank reversal): NEW dimension — independence vs K133 to be verified

Variants (4, pre-registered):
  V_d7_h5_top3 : 7d Δ (21 events), hold 5d (15 events), top-3 / bot-3  [PRIMARY]
  V_d3_h3_top3 : 3d Δ ( 9 events), hold 3d ( 9 events), top-3 / bot-3
  V_d14_h7_top3: 14d Δ (42 events), hold 7d (21 events), top-3 / bot-3
  V_d7_h5_top5 : 7d Δ (21 events), hold 5d (15 events), top-5 / bot-5  (broader)

Stats:
  730d, IS 70% / OOS 30%
  Walk-forward 4-fold
  One-sided permutation (cross-sectional rank shuffle) n=300
  Block bootstrap CI on OOS Sharpe n=300
  DSR N_trials=4
  Cost stress ±50%
  P&L decomposition price vs funding vs cost

Correlation check vs K133 V_rev_3d_z15 (best level-based reversal).

§6 mini gates: OOS_SR ≥ 0.5, p_perm < 0.05, MaxDD > -0.40,
cost-stress robust, DSR_oos > 0.5, price_dominant.
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

# 14 symbols (SHIB has no Bybit FR cache; BONK uses 1000BONK FR)
SYMBOLS = [
    "BTC", "ETH", "SOL", "BNB", "DOGE", "AVAX", "LINK", "ADA",
    "XRP", "INJ", "OP", "WIF", "BONK", "ARB",
]

COST_BPS = 7.0
IS_FRAC = 0.70
SEED = 20260524

ANN_FACTOR_3D = np.sqrt(365 / 3)
ANN_FACTOR_5D = np.sqrt(365 / 5)
ANN_FACTOR_7D = np.sqrt(365 / 7)

VOL_TARGET = 0.10
VOL_CAP = 1.5
VOL_LOOKBACK = 30


# ------------------------------------------------------------- data load
FR_FILE_OVERRIDES = {
    "BONK": "bybit_fr_1000BONKUSDT_730d.parquet",
}
PX_FILE_OVERRIDES = {
    "BONK": "BONKUSDT_4h_730d.parquet",
}


def load_fr(sym):
    fname = FR_FILE_OVERRIDES.get(sym, f"bybit_fr_{sym}USDT_730d.parquet")
    p = CACHE / fname
    if not p.exists():
        return None
    df = pd.read_parquet(p)
    df["timestamp"] = pd.to_datetime(df["timestamp"])
    df = df.set_index("timestamp").sort_index()
    df = df[~df.index.duplicated(keep="last")]
    return df["funding_rate"].astype(float).rename(sym)


def load_px(sym):
    fname = PX_FILE_OVERRIDES.get(sym, f"{sym}USDT_4h_730d.parquet")
    p = CACHE / fname
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
            print(f"  skip {s} (fr={fr is not None}, px={px is not None})")
            continue
        fr_dict[s] = fr
        px_dict[s] = px
    fr_panel = pd.concat(fr_dict.values(), axis=1).sort_index()
    px_panel = pd.concat(px_dict.values(), axis=1).sort_index()
    fr_panel = fr_panel.dropna(thresh=int(fr_panel.shape[1] * 0.8))
    px_at_fr = px_panel.reindex(fr_panel.index, method="ffill")
    return fr_panel, px_at_fr


# ------------------------------------------------------------- Δ signal
def delta_signal(fr_panel, n_events):
    """Δfr = fr − fr.shift(n_events), then lag 1 to avoid look-ahead."""
    return (fr_panel - fr_panel.shift(n_events)).shift(1)


# ------------------------------------------------------------- backtest (rank-based REVERSAL on Δ)
def backtest_delta_rank(
    fr_panel,
    px_at_fr,
    signal_panel,
    n_long=3,
    n_short=3,
    hold_n=15,
    cost_bps=COST_BPS,
    vol_target=VOL_TARGET,
    vol_cap=VOL_CAP,
    vol_lookback=VOL_LOOKBACK,
    rebal_on_change=True,
):
    """Rank cross-sectionally by Δfr:
       biggest Δfr (top n_short) → SHORT (overheating, expect mean-revert down)
       smallest Δfr (bot n_long) → LONG (cooling, expect mean-revert up)
    """
    sig_arr = signal_panel.values
    fr_arr = fr_panel.values
    px_arr = px_at_fr.values
    T_full = sig_arr.shape[0]
    N = sig_arr.shape[1]
    cols = list(fr_panel.columns)
    rebal_pos = np.arange(0, T_full, hold_n)
    idx_vals = signal_panel.index.values

    # period-by-period (rebal-spaced) returns for vol estimation
    px_at_rebal = px_arr[rebal_pos]
    with np.errstate(invalid="ignore", divide="ignore"):
        period_ret = px_at_rebal[1:] / px_at_rebal[:-1] - 1.0
    period_ret = np.where(np.isfinite(period_ret), period_ret, 0.0)
    periods_per_year = (365 * 24) / (hold_n * 8)
    sqrt_ppy = np.sqrt(periods_per_year)

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
        if valid.sum() < n_long + n_short:
            w = np.zeros(N)
        else:
            # rank by Δfr: SHORT top (biggest +Δ), LONG bottom (biggest -Δ)
            filled_hi = np.where(valid, s_row, -np.inf)
            order_desc = np.argsort(-filled_hi)  # descending
            filled_lo = np.where(valid, s_row, +np.inf)
            order_asc = np.argsort(filled_lo)    # ascending

            cand_short = [int(i) for i in order_desc[:n_short] if valid[i]]
            cand_long = [int(i) for i in order_asc[:n_long] if valid[i]]

            # avoid degenerate overlap (very small N): drop overlapping members
            overlap = set(cand_short) & set(cand_long)
            cand_short = [i for i in cand_short if i not in overlap]
            cand_long = [i for i in cand_long if i not in overlap]

            w = np.zeros(N)
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
        funding_ret = -(w * fr_sum)  # long pays positive funding

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
    if n_obs < 20 or n_trials < 1:
        return 0.0
    emc = 0.5772
    e_max = np.sqrt(2 * np.log(n_trials)) * (1 - emc) + \
            (1 - emc) / np.sqrt(2 * np.log(max(n_trials, 2)))
    var = (1 - skew * sr + (kurt - 1) / 4.0 * sr ** 2) / (n_obs - 1)
    if var <= 0:
        return 0.0
    z = (sr - e_max) / np.sqrt(var)
    from math import erf, sqrt
    return 0.5 * (1 + erf(z / sqrt(2)))


def block_bootstrap_ci(rets, ann_factor, n_iter=300, block=3, seed=SEED):
    rets = np.asarray(rets)
    n = len(rets)
    if n < block * 3:
        return {"sr_lo": 0.0, "sr_hi": 0.0, "sr_mean": 0.0}
    rng = np.random.default_rng(seed)
    n_blocks = max(1, n // block)
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


def permutation_test(fr_panel, px_at_fr, signal_panel_fn, cfg, n_iter=300, seed=SEED):
    rng = np.random.default_rng(seed)
    hold_n = cfg["hold"]
    ann = cfg["ann"]

    actual_panel = signal_panel_fn(fr_panel)
    actual = backtest_delta_rank(
        fr_panel, px_at_fr, actual_panel,
        n_long=cfg["n_long"], n_short=cfg["n_short"], hold_n=hold_n,
    )
    actual_sr = perf_stats(actual["rets"], ann)["sharpe"]
    actual_sr_gross = gross_sharpe(actual, ann)

    base_signal = actual_panel.values
    null_sr = np.zeros(n_iter)
    null_sr_gross = np.zeros(n_iter)
    for i in range(n_iter):
        permuted = base_signal.copy()
        # cross-sectional shuffle row-wise (keeps marginal distribution per row)
        for r in range(permuted.shape[0]):
            row = permuted[r]
            mask = ~np.isnan(row)
            idxs = np.where(mask)[0]
            if len(idxs) > 1:
                permuted[r, idxs] = rng.permutation(row[idxs])
        sp = pd.DataFrame(permuted, index=fr_panel.index, columns=fr_panel.columns)
        res = backtest_delta_rank(
            fr_panel, px_at_fr, sp,
            n_long=cfg["n_long"], n_short=cfg["n_short"], hold_n=hold_n,
        )
        null_sr[i] = perf_stats(res["rets"], ann)["sharpe"]
        null_sr_gross[i] = gross_sharpe(res, ann)

    return {
        "actual_sharpe_net": float(actual_sr),
        "actual_sharpe_gross": float(actual_sr_gross),
        "null_mean_net": float(null_sr.mean()),
        "null_std_net": float(null_sr.std()),
        "null_p95_net": float(np.quantile(null_sr, 0.95)),
        # one-sided: prob null >= actual (positive edge under reversal direction)
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
    ann = cfg["ann"]
    for f in range(n_folds):
        s = f * fold_size
        e = (f + 1) * fold_size if f < n_folds - 1 else T
        sub_fr = fr_panel.iloc[s:e]
        sub_px = px_at_fr.iloc[s:e]
        sub_sig = sig.iloc[s:e]
        try:
            r = backtest_delta_rank(
                sub_fr, sub_px, sub_sig,
                n_long=cfg["n_long"], n_short=cfg["n_short"], hold_n=hold_n,
            )["rets"]
        except Exception:
            r = pd.Series(dtype=float)
        out.append({"fold": f, **perf_stats(r, ann)})
    return out


# ---------------------------------------------------------------- variants
# Δ window (events) and hold (events): 3d=9, 5d=15, 7d=21, 14d=42
VARIANTS = {
    "V_d7_h5_top3":  dict(d_win=21, n_long=3, n_short=3, hold=15, ann=ANN_FACTOR_5D),  # PRIMARY
    "V_d3_h3_top3":  dict(d_win=9,  n_long=3, n_short=3, hold=9,  ann=ANN_FACTOR_3D),
    "V_d14_h7_top3": dict(d_win=42, n_long=3, n_short=3, hold=21, ann=ANN_FACTOR_7D),
    "V_d7_h5_top5":  dict(d_win=21, n_long=5, n_short=5, hold=15, ann=ANN_FACTOR_5D),
}
N_TRIALS_DSR = 4


def run_variant(name, cfg, fr_panel, px_at_fr, n_perm=300, n_boot=300):
    print(f"  >> {name}: Δwin={cfg['d_win']}ev ({cfg['d_win']*8/24:.1f}d) "
          f"top={cfg['n_long']}/{cfg['n_short']} hold={cfg['hold']}ev "
          f"({cfg['hold']*8/24:.1f}d)")
    sig_fn = lambda fp: delta_signal(fp, cfg["d_win"])
    signal_panel = sig_fn(fr_panel)
    hold_n = cfg["hold"]
    ann = cfg["ann"]

    res = backtest_delta_rank(
        fr_panel, px_at_fr, signal_panel,
        n_long=cfg["n_long"], n_short=cfg["n_short"], hold_n=hold_n,
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

    wf = walk_forward(fr_panel, px_at_fr, sig_fn, cfg, n_folds=4)

    res_lo = backtest_delta_rank(
        fr_panel, px_at_fr, signal_panel,
        n_long=cfg["n_long"], n_short=cfg["n_short"], hold_n=hold_n,
        cost_bps=COST_BPS * 0.5,
    )
    res_hi = backtest_delta_rank(
        fr_panel, px_at_fr, signal_panel,
        n_long=cfg["n_long"], n_short=cfg["n_short"], hold_n=hold_n,
        cost_bps=COST_BPS * 1.5,
    )
    cost_stress = {
        "low_50pct":   perf_stats(res_lo["rets"], ann)["sharpe"],
        "base_100pct": full_stats["sharpe"],
        "high_150pct": perf_stats(res_hi["rets"], ann)["sharpe"],
    }

    boot = block_bootstrap_ci(rets.iloc[n_is:].values, ann,
                               n_iter=n_boot, block=3, seed=SEED + 11)

    perm = permutation_test(fr_panel, px_at_fr, sig_fn, cfg, n_iter=n_perm)

    dsr_full = deflated_sharpe(full_stats["sharpe"], full_stats["n"], n_trials=N_TRIALS_DSR)
    dsr_oos = deflated_sharpe(oos_stats["sharpe"], oos_stats["n"], n_trials=N_TRIALS_DSR)

    long_count = res["long_count"].sort_values(ascending=False).to_dict()
    short_count = res["short_count"].sort_values(ascending=False).to_dict()

    abs_sum = abs(price_total) + abs(fund_total) + 1e-9
    decomp = {
        "price_pnl": price_total,
        "fund_pnl": fund_total,
        "cost": cost_total,
        "net": net_total,
        "price_pct_of_gross_abs": float(abs(price_total) / abs_sum),
        "fund_pct_of_gross_abs": float(abs(fund_total) / abs_sum),
        "price_dominant": bool(abs(price_total) > abs(fund_total) * 2),
        "price_same_sign_as_net": bool(np.sign(price_total) == np.sign(net_total) and net_total != 0),
    }

    gates = {
        "oos_sr_ge_0_5":   bool(oos_stats["sharpe"] >= 0.5),
        "p_perm_lt_0_05":  bool(perm["p_value_net"] < 0.05),
        "max_dd_gt_neg40": bool(full_stats["max_dd"] > -0.40),
        "cost_stress_robust": bool(cost_stress["high_150pct"] >= 0.5 * cost_stress["base_100pct"]
                                   if cost_stress["base_100pct"] > 0 else False),
        "dsr_oos_pos":     bool(dsr_oos > 0.5),
        "price_dominant":  bool(decomp["price_dominant"]),
    }
    gates["pass_count"] = int(sum(1 for v in gates.values() if v is True))
    gates["all_pass"] = bool(all(v for k, v in gates.items() if k not in ("pass_count", "all_pass")))

    return {
        "config": {k: v for k, v in cfg.items() if k != "ann"},
        "ann_factor": float(ann),
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
        "gates": gates,
        "equity_curve": (1 + rets).cumprod().tolist(),
        "equity_idx": [str(x) for x in rets.index],
        "_rets_for_corr": rets.to_dict(),  # used internally for K133 correlation
    }


# ---------------------------------------------------------------- K133 correlation
def correlation_vs_k133(results):
    """Compute return correlation between each K143 variant and K133 V_rev_3d_z15."""
    k133_curves_path = ROOT / "wave_k133_curves.json"
    if not k133_curves_path.exists():
        return {"_note": "K133 curves not found", "k133_variant": None}
    try:
        with open(k133_curves_path) as f:
            k133 = json.load(f)
    except Exception as e:
        return {"_note": f"K133 curve load failed: {e}", "k133_variant": None}

    target = "V_rev_3d_z15"  # best K133 variant (OOS_SR=0.83, 5/6 gates)
    if target not in k133:
        # fall back to first available
        target = list(k133.keys())[0]
    k133_eq = pd.Series(k133[target]["equity_curve"], index=pd.to_datetime(k133[target]["equity_idx"]))
    k133_ret = k133_eq.pct_change().dropna()

    out = {"k133_variant": target,
           "k133_n_returns": int(len(k133_ret))}
    per_variant = {}
    for name, r in results.items():
        k143_ret = pd.Series(r["_rets_for_corr"])
        k143_ret.index = pd.to_datetime(k143_ret.index)
        joined = pd.concat([k143_ret.rename("k143"), k133_ret.rename("k133")],
                           axis=1, join="inner").dropna()
        if len(joined) < 10:
            per_variant[name] = {"rho": None, "n_overlap": int(len(joined)),
                                 "note": "insufficient overlap"}
            continue
        rho = float(joined.corr().iloc[0, 1])
        per_variant[name] = {
            "rho": rho,
            "n_overlap": int(len(joined)),
            "abs_rho": float(abs(rho)),
            "same_edge": bool(abs(rho) > 0.7),
            "independent": bool(abs(rho) < 0.3),
        }
    out["per_variant"] = per_variant
    return out


# ---------------------------------------------------------------- main
def main():
    t0 = time.time()
    print("Loading panels ...")
    fr_panel, px_at_fr = build_panels()
    print(f"  FR panel: {fr_panel.shape}, range {fr_panel.index.min()} .. {fr_panel.index.max()}")
    print(f"  Symbols ({fr_panel.shape[1]}): {list(fr_panel.columns)}")

    n_perm = 300
    n_boot = 300

    results = {}
    for name, cfg in VARIANTS.items():
        results[name] = run_variant(name, cfg, fr_panel, px_at_fr,
                                     n_perm=n_perm, n_boot=n_boot)
        elapsed = time.time() - t0
        print(f"     [elapsed {elapsed:.1f}s]")

    # K133 correlation check
    corr = correlation_vs_k133(results)

    # strip rets-for-corr from output before saving
    for r in results.values():
        r.pop("_rets_for_corr", None)

    out_path = ROOT / "wave_k143_fund_delta_xs.json"
    curves_path = ROOT / "wave_k143_curves.json"

    summary = {k: {kk: vv for kk, vv in v.items() if kk not in ("equity_curve", "equity_idx")}
               for k, v in results.items()}
    summary["_meta"] = {
        "wall_seconds": time.time() - t0,
        "n_symbols": int(fr_panel.shape[1]),
        "symbols": list(fr_panel.columns),
        "n_events": int(fr_panel.shape[0]),
        "n_perm": n_perm,
        "n_boot": n_boot,
        "n_trials_dsr": N_TRIALS_DSR,
        "is_frac": IS_FRAC,
        "cost_bps_per_leg": COST_BPS,
        "vol_target": VOL_TARGET,
        "vol_cap": VOL_CAP,
        "vol_lookback": VOL_LOOKBACK,
        "wave": "K143",
        "research_source": "Presto Research R5-3",
        "direction": "REVERSAL on Δfr (top Δ → SHORT, bot Δ → LONG)",
        "signal_kind": "cross-sectional rank of funding CHANGE (Δ)",
    }
    summary["_k133_correlation"] = corr

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

    print("\n=== K143 Summary (Δfr Reversal) ===")
    for name, r in results.items():
        full, oos = r["full"], r["oos"]
        perm = r["permutation"]
        dec = r["decomposition"]
        g = r["gates"]
        print(f"{name:18s} netSR={full['sharpe']:+.2f} OOS={oos['sharpe']:+.2f} "
              f"grossSR={r['gross_sharpe']:+.2f} MaxDD={full['max_dd']:.2%} "
              f"p_net={perm['p_value_net']:.3f} "
              f"price={dec['price_pnl']:+.3f} fund={dec['fund_pnl']:+.3f} "
              f"cost={dec['cost']:.3f} rebals={r['n_rebal_events']} "
              f"DSR_oos={r['dsr_oos']:.3f} gates={g['pass_count']}/6")

    print(f"\n=== Correlation vs K133 ({corr.get('k133_variant')}) ===")
    for name, c in corr.get("per_variant", {}).items():
        rho = c.get("rho")
        rho_s = f"{rho:+.3f}" if rho is not None else "n/a"
        tag = ""
        if c.get("same_edge"): tag = "  [SAME EDGE |ρ|>0.7]"
        elif c.get("independent"): tag = "  [INDEPENDENT |ρ|<0.3]"
        print(f"  {name:18s} rho={rho_s} n_overlap={c.get('n_overlap')}{tag}")


if __name__ == "__main__":
    main()

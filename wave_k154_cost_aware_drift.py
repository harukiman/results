"""
Wave K154 — Cost-Aware Designed FR Drift (variant of K153)

K153 finding:
  Gross SR +0.51 (signal exists) but 4100 trades × 14bp roundtrip cost = 0.68
  overwhelmed gross PnL +0.30 → net SR negative → REJECT.

K154 hypothesis (cost-aware fix):
  Use rarer trigger (|z|>3) + much longer hold (15-30 events = 5-10 days)
  to dramatically reduce turnover while preserving the underlying signal.
  Additionally test a CONTINUATION variant (reverse direction): when realized FR
  is extreme vs design, does price actually CONTINUE rather than mean-revert?

Variants (single-config focus per spec):
  V_z3_h15            : per-sym fade, |z|>3 trigger, 15-event max hold (~5d)
  V_z3_h30            : per-sym fade, |z|>3 trigger, 30-event max hold (~10d)
  V_z25_h30_xs        : XS, top-3 long / bot-3 short (sorted by z), 30-event hold
  V_z3_continuation   : per-sym CONTINUATION (z>+3 → LONG, z<-3 → SHORT),
                        15-event hold — opposite direction of fade.

Stats (same as K153):
  730d data, IS 70% / OOS 30%
  Walk-forward 4-fold
  Cross-sectional row-shuffle permutation n=300
  Block bootstrap CI on OOS Sharpe n=300
  DSR with N_trials=4
  Cost stress ±50% (base 7 bp per side per leg)
  Correlation with K133 reversal (orthogonality check for ensemble)

§6 mini gates: OOS_SR≥0.5, p_perm<0.05, MaxDD>-0.40,
cost-stress robust, DSR_oos>0.5, price_dominant.
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

# Same universe as K153 (FR ∩ premium)
SYMBOLS = [
    "ADA", "APT", "ARB", "ARKM", "AVAX", "BNB", "BOME", "BTC", "DOGE", "DOT",
    "ENA", "ETH", "INJ", "JTO", "JUP", "LINK", "MANTA", "NEAR", "ONDO", "OP",
    "SEI", "SOL", "STRK", "SUI", "TAO", "TIA", "WIF", "WLD", "XRP",
]

COST_BPS = 7.0
IS_FRAC = 0.70
SEED = 20260524

ANN_FACTOR_EVENT = np.sqrt(365.25 * 3)

VOL_TARGET = 0.10
VOL_CAP = 1.5
VOL_LOOKBACK = 30

IR_FLOOR_8H = 1e-4
PREMIUM_CLAMP = 5e-4
DESIGN_STD_LB = 30 * 3


# --------------------------------------------------------- data loading
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


def load_premium(sym):
    p = CACHE / f"hist_premium_{sym}USDT_4h_730d.parquet"
    if not p.exists():
        return None
    df = pd.read_parquet(p)
    df["timestamp"] = pd.to_datetime(df["timestamp"])
    df = df.set_index("timestamp").sort_index()
    df = df[~df.index.duplicated(keep="last")]
    return df["premium_close"].astype(float).rename(sym)


def build_panels():
    fr_dict, px_dict, pr_dict = {}, {}, {}
    for s in SYMBOLS:
        fr = load_fr(s)
        px = load_px(s)
        pr = load_premium(s)
        if fr is None or px is None or pr is None:
            print(f"  skip {s} (fr={fr is not None}, px={px is not None}, prem={pr is not None})")
            continue
        fr_dict[s] = fr
        px_dict[s] = px
        pr_dict[s] = pr
    fr_panel = pd.concat(fr_dict.values(), axis=1).sort_index()
    px_panel = pd.concat(px_dict.values(), axis=1).sort_index()
    pr_panel = pd.concat(pr_dict.values(), axis=1).sort_index()
    fr_panel = fr_panel.dropna(thresh=int(fr_panel.shape[1] * 0.7))
    px_at_fr = px_panel.reindex(fr_panel.index, method="ffill")
    pr_at_fr = pr_panel.reindex(fr_panel.index, method="ffill")
    return fr_panel, px_at_fr, pr_at_fr


# --------------------------------------------------------- design FR
def design_fr_panel(pr_at_fr):
    p = pr_at_fr.values
    delta = IR_FLOOR_8H - p
    delta_clip = np.clip(delta, -PREMIUM_CLAMP, +PREMIUM_CLAMP)
    design = p + delta_clip
    return pd.DataFrame(design, index=pr_at_fr.index, columns=pr_at_fr.columns)


def build_z_signal(fr_panel, design_panel, lookback=DESIGN_STD_LB):
    resid = fr_panel - design_panel
    rolling_std = resid.rolling(lookback, min_periods=lookback // 2).std()
    z = resid / rolling_std.replace(0, np.nan)
    return z.shift(1)


# --------------------------------------------------------- per-sym backtest
def backtest_per_symbol(
    fr_panel, px_at_fr, z_panel,
    z_enter=3.0, z_exit=0.5, max_hold_events=15,
    direction="fade",  # "fade" or "continuation"
    cost_bps=COST_BPS,
    vol_target=VOL_TARGET, vol_cap=VOL_CAP, vol_lookback=VOL_LOOKBACK,
):
    """Per-symbol stateful trigger.
       direction='fade'         : sign = -sign(z)  (z>+thr → SHORT, z<-thr → LONG)
       direction='continuation' : sign = +sign(z)  (z>+thr → LONG,  z<-thr → SHORT)
    """
    sign_mult = -1.0 if direction == "fade" else +1.0
    fr_arr = fr_panel.values
    px_arr = px_at_fr.values
    z_arr = z_panel.values
    T, N = fr_arr.shape
    cols = list(fr_panel.columns)

    with np.errstate(invalid="ignore", divide="ignore"):
        lr = np.log(px_arr[1:] / px_arr[:-1])
    lr = np.where(np.isfinite(lr), lr, 0.0)
    sym_vol = np.full((T, N), np.nan, dtype=float)
    for t in range(1, T):
        lo = max(0, t - vol_lookback)
        if t - lo >= 5:
            sym_vol[t] = np.nanstd(lr[lo:t], axis=0, ddof=1) * np.sqrt(3 * 365.25)

    in_pos = np.zeros(N, dtype=bool)
    pos_sign = np.zeros(N, dtype=float)
    pos_size = np.zeros(N, dtype=float)
    pos_age = np.zeros(N, dtype=int)

    rets_per_event = np.zeros(T)
    price_per_event = np.zeros(T)
    fund_per_event = np.zeros(T)
    cost_per_event = np.zeros(T)
    turnover_per_event = np.zeros(T)
    long_count = np.zeros(N, dtype=int)
    short_count = np.zeros(N, dtype=int)
    n_trades = 0

    for t in range(1, T):
        prev_w = pos_sign * pos_size

        for i in range(N):
            z = z_arr[t, i]
            if in_pos[i]:
                pos_age[i] += 1
                exit_now = False
                if np.isfinite(z) and abs(z) < z_exit:
                    exit_now = True
                if pos_age[i] >= max_hold_events:
                    exit_now = True
                # for fade: exit if z flips sign (signal invalidated)
                # for continuation: exit if z flips sign (trend reversed)
                if np.isfinite(z) and np.sign(z) == -np.sign(pos_sign[i]) * sign_mult and abs(z) > 0.5:
                    exit_now = True
                if exit_now:
                    in_pos[i] = False
                    pos_sign[i] = 0.0
                    pos_size[i] = 0.0
                    pos_age[i] = 0
            else:
                if np.isfinite(z) and abs(z) > z_enter:
                    sv = sym_vol[t, i]
                    if not np.isfinite(sv) or sv <= 0:
                        size = 1.0
                    else:
                        size = min(vol_target / sv, vol_cap)
                    pos_sign[i] = sign_mult * np.sign(z)
                    pos_size[i] = size
                    in_pos[i] = True
                    pos_age[i] = 0
                    n_trades += 1
                    if pos_sign[i] > 0:
                        long_count[i] += 1
                    else:
                        short_count[i] += 1

        cur_w = pos_sign * pos_size
        turn = float(np.abs(cur_w - prev_w).sum())
        c = turn * (cost_bps / 1e4)

        with np.errstate(invalid="ignore", divide="ignore"):
            pr_event = px_arr[t] / px_arr[t - 1] - 1.0
        pr_event = np.where(np.isfinite(pr_event), pr_event, 0.0)
        fr_event = fr_arr[t]
        fr_event = np.where(np.isfinite(fr_event), fr_event, 0.0)

        price_pnl = float((prev_w * pr_event).sum())
        fund_pnl = -float((prev_w * fr_event).sum())
        net = price_pnl + fund_pnl - c

        price_per_event[t] = price_pnl
        fund_per_event[t] = fund_pnl
        cost_per_event[t] = c
        rets_per_event[t] = net
        turnover_per_event[t] = turn

    idx = fr_panel.index
    return {
        "rets": pd.Series(rets_per_event, index=idx),
        "price_pnl": pd.Series(price_per_event, index=idx),
        "fund_pnl": pd.Series(fund_per_event, index=idx),
        "cost": pd.Series(cost_per_event, index=idx),
        "turnover": pd.Series(turnover_per_event, index=idx),
        "long_count": pd.Series(long_count, index=cols),
        "short_count": pd.Series(short_count, index=cols),
        "n_trades": int(n_trades),
        "n_periods": int(T),
    }


# --------------------------------------------------------- XS rebal backtest
def backtest_xs(
    fr_panel, px_at_fr, z_panel,
    n_long=3, n_short=3, hold_n=30, z_thresh=2.5,
    cost_bps=COST_BPS,
    vol_target=VOL_TARGET, vol_cap=VOL_CAP, vol_lookback=VOL_LOOKBACK,
    rebal_on_change=True,
):
    """Cross-sectional rebal every hold_n events:
       - Long lowest n_long z values where z < -z_thresh
       - Short highest n_short z values where z > +z_thresh
    """
    fr_arr = fr_panel.values
    px_arr = px_at_fr.values
    z_arr = z_panel.values
    T, N = fr_arr.shape
    cols = list(fr_panel.columns)
    rebal_pos = np.arange(0, T, hold_n)
    idx_vals = fr_panel.index.values

    with np.errstate(invalid="ignore", divide="ignore"):
        lr = np.log(px_arr[1:] / px_arr[:-1])
    lr = np.where(np.isfinite(lr), lr, 0.0)
    sym_vol = np.full((T, N), np.nan, dtype=float)
    for t in range(1, T):
        lo = max(0, t - vol_lookback)
        if t - lo >= 5:
            sym_vol[t] = np.nanstd(lr[lo:t], axis=0, ddof=1) * np.sqrt(3 * 365.25)

    rets, price_pnl_arr, fund_pnl_arr, cost_arr = [], [], [], []
    rets_idx, turnover_arr, gross_arr = [], [], []
    long_count = np.zeros(N, dtype=int)
    short_count = np.zeros(N, dtype=int)
    prev_w = np.zeros(N)
    n_rebal_events = 0

    for ti in range(len(rebal_pos) - 1):
        t = rebal_pos[ti]
        t_next = rebal_pos[ti + 1]
        z_row = z_arr[t]
        valid = np.isfinite(z_row)
        if valid.sum() < n_long + n_short + 1:
            w = np.zeros(N)
        else:
            filled_hi = np.where(valid, z_row, -np.inf)
            order_desc = np.argsort(-filled_hi)
            filled_lo = np.where(valid, z_row, +np.inf)
            order_asc = np.argsort(filled_lo)

            # SHORT side: highest positive z exceeding threshold
            cand_short = []
            for i in order_desc:
                if valid[i] and z_row[i] > z_thresh:
                    cand_short.append(i)
                    if len(cand_short) == n_short:
                        break
            # LONG side: lowest z below -threshold
            cand_long = []
            for i in order_asc:
                if valid[i] and z_row[i] < -z_thresh:
                    cand_long.append(i)
                    if len(cand_long) == n_long:
                        break

            w = np.zeros(N)
            sva = sym_vol[t] if t < T else np.full(N, np.nan)
            for i in cand_long:
                sv = sva[i]
                if not np.isfinite(sv) or sv <= 0:
                    leg = 1.0 / max(len(cand_long), 1)
                else:
                    leg = min(vol_target / sv, vol_cap)
                w[i] = leg / max(len(cand_long), 1)
            for i in cand_short:
                sv = sva[i]
                if not np.isfinite(sv) or sv <= 0:
                    leg = 1.0 / max(len(cand_short), 1)
                else:
                    leg = min(vol_target / sv, vol_cap)
                w[i] = -leg / max(len(cand_short), 1)

        if rebal_on_change:
            cur_l = tuple(np.where(w > 0)[0])
            cur_s = tuple(np.where(w < 0)[0])
            prev_l = tuple(np.where(prev_w > 0)[0])
            prev_s = tuple(np.where(prev_w < 0)[0])
            if cur_l == prev_l and cur_s == prev_s:
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
        gross = float(np.abs(w).sum())

        px_now = px_arr[t]
        px_next = px_arr[t_next]
        with np.errstate(invalid="ignore", divide="ignore"):
            pr = px_next / px_now - 1.0
        pr = np.where(np.isfinite(pr), pr, 0.0)

        fr_window = fr_arr[t:t_next]
        fr_sum = np.nansum(fr_window, axis=0)
        fund = -(w * fr_sum)

        price_pnl = float((w * pr).sum())
        fund_pnl = float(fund.sum())
        net = price_pnl + fund_pnl - cost

        rets.append(net)
        price_pnl_arr.append(price_pnl)
        fund_pnl_arr.append(fund_pnl)
        cost_arr.append(cost)
        turnover_arr.append(turn)
        gross_arr.append(gross)
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
        "gross_notional": pd.Series(gross_arr, index=rets_idx),
        "long_count": pd.Series(long_count, index=cols),
        "short_count": pd.Series(short_count, index=cols),
        "n_rebal_events": n_rebal_events,
        "n_periods": len(rets),
    }


# --------------------------------------------------------- stats
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


def _run_cfg(fr_panel, px_at_fr, z_panel, cfg, cost_bps=COST_BPS):
    is_xs = cfg.get("kind") == "xs"
    if is_xs:
        res = backtest_xs(fr_panel, px_at_fr, z_panel,
                          n_long=cfg["n_long"], n_short=cfg["n_short"],
                          hold_n=cfg["hold"], z_thresh=cfg.get("z_thresh", 2.5),
                          cost_bps=cost_bps)
        ann = np.sqrt((365.25 * 3) / cfg["hold"])
    else:
        res = backtest_per_symbol(fr_panel, px_at_fr, z_panel,
                                  z_enter=cfg["z_enter"], z_exit=cfg["z_exit"],
                                  max_hold_events=cfg["max_hold"],
                                  direction=cfg.get("direction", "fade"),
                                  cost_bps=cost_bps)
        ann = ANN_FACTOR_EVENT
    return res, ann


def permutation_test_xs(fr_panel, px_at_fr, z_panel, cfg, n_iter=300, seed=SEED):
    rng = np.random.default_rng(seed)
    actual, ann = _run_cfg(fr_panel, px_at_fr, z_panel, cfg)
    actual_sr = perf_stats(actual["rets"], ann)["sharpe"]
    actual_sr_g = gross_sharpe(actual, ann)

    base = z_panel.values
    null_sr = np.zeros(n_iter)
    null_sr_g = np.zeros(n_iter)
    for k in range(n_iter):
        permuted = base.copy()
        for r in range(permuted.shape[0]):
            row = permuted[r]
            mask = np.isfinite(row)
            idxs = np.where(mask)[0]
            if len(idxs) > 1:
                permuted[r, idxs] = rng.permutation(row[idxs])
        zp = pd.DataFrame(permuted, index=z_panel.index, columns=z_panel.columns)
        res, ann_use = _run_cfg(fr_panel, px_at_fr, zp, cfg)
        null_sr[k] = perf_stats(res["rets"], ann_use)["sharpe"]
        null_sr_g[k] = gross_sharpe(res, ann_use)

    return {
        "actual_sharpe_net": float(actual_sr),
        "actual_sharpe_gross": float(actual_sr_g),
        "null_mean_net": float(null_sr.mean()),
        "null_std_net": float(null_sr.std()),
        "null_p95_net": float(np.quantile(null_sr, 0.95)),
        "p_value_net": float((null_sr >= actual_sr).mean()),
        "null_mean_gross": float(null_sr_g.mean()),
        "p_value_gross": float((null_sr_g >= actual_sr_g).mean()),
        "n_iter": int(n_iter),
    }


def walk_forward(fr_panel, px_at_fr, z_panel, cfg, n_folds=4):
    T = len(fr_panel)
    fold_size = T // n_folds
    out = []
    for f in range(n_folds):
        s = f * fold_size
        e = (f + 1) * fold_size if f < n_folds - 1 else T
        sub_fr = fr_panel.iloc[s:e]
        sub_px = px_at_fr.iloc[s:e]
        sub_z = z_panel.iloc[s:e]
        try:
            res, ann = _run_cfg(sub_fr, sub_px, sub_z, cfg)
            r = res["rets"]
        except Exception:
            r = pd.Series(dtype=float)
            ann = ANN_FACTOR_EVENT
        out.append({"fold": f, **perf_stats(r, ann)})
    return out


# --------------------------------------------------------- variants
VARIANTS = {
    "V_z3_h15":          dict(kind="psym", z_enter=3.0, z_exit=0.5, max_hold=15, direction="fade"),
    "V_z3_h30":          dict(kind="psym", z_enter=3.0, z_exit=0.5, max_hold=30, direction="fade"),
    "V_z25_h30_xs":      dict(kind="xs",   n_long=3,    n_short=3,  hold=30, z_thresh=2.5),
    "V_z3_continuation": dict(kind="psym", z_enter=3.0, z_exit=0.5, max_hold=15, direction="continuation"),
}
N_TRIALS_DSR = 4


def run_variant(name, cfg, fr_panel, px_at_fr, z_panel,
                n_perm=300, n_boot=300):
    is_xs = cfg.get("kind") == "xs"
    if is_xs:
        print(f"  >> {name}: XS top={cfg['n_long']}/{cfg['n_short']} z_thresh={cfg.get('z_thresh',2.5)} hold={cfg['hold']}")
    else:
        print(f"  >> {name}: per-sym z_enter=±{cfg['z_enter']} z_exit=±{cfg['z_exit']} "
              f"max_hold={cfg['max_hold']} dir={cfg.get('direction','fade')}")
    res, ann = _run_cfg(fr_panel, px_at_fr, z_panel, cfg)

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

    wf = walk_forward(fr_panel, px_at_fr, z_panel, cfg, n_folds=4)

    # cost stress
    res_lo, _ = _run_cfg(fr_panel, px_at_fr, z_panel, cfg, cost_bps=COST_BPS * 0.5)
    res_hi, _ = _run_cfg(fr_panel, px_at_fr, z_panel, cfg, cost_bps=COST_BPS * 1.5)
    cost_stress = {
        "low_50pct":   perf_stats(res_lo["rets"], ann)["sharpe"],
        "base_100pct": full_stats["sharpe"],
        "high_150pct": perf_stats(res_hi["rets"], ann)["sharpe"],
    }

    boot = block_bootstrap_ci(rets.iloc[n_is:].values, ann,
                               n_iter=n_boot, block=3, seed=SEED + 11)
    perm = permutation_test_xs(fr_panel, px_at_fr, z_panel, cfg, n_iter=n_perm)

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

    n_trades = int(res.get("n_trades", res.get("n_rebal_events", 0)))

    return {
        "config": cfg,
        "ann_factor": float(ann),
        "n_periods": n_total,
        "n_trades_or_rebals": n_trades,
        "full": full_stats,
        "is": is_stats,
        "oos": oos_stats,
        "gross_sharpe": float(gross_sr),
        "decomposition": decomp,
        "turnover": {
            "total": turnover_total,
            "per_event_avg": turnover_per_event,
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
        "rets_series": rets.tolist(),
    }


# --------------------------------------------------------- correlation w/ K133
def correlation_with_k133(results, k133_curves_path):
    """For each K154 variant, compute correlation of net returns with each K133
       variant (REVERSAL strategy). Aggregate K154 returns over each K133 rebal
       window so series align.
    """
    out = {}
    try:
        with open(k133_curves_path) as f:
            k133 = json.load(f)
    except Exception as ex:
        return {"k133_load_error": str(ex)}

    for var_name, vd in results.items():
        if var_name.startswith("_"):
            continue
        k154_rets = pd.Series(vd["rets_series"],
                              index=pd.to_datetime(vd["equity_idx"]))
        sub = {}
        for k133_name, d in k133.items():
            try:
                eq = pd.Series(d["equity_curve"], index=pd.to_datetime(d["equity_idx"]))
                ret = eq.pct_change().dropna()
                k133_idx = ret.index
                agg = []
                valid_idx = []
                for i in range(1, len(k133_idx)):
                    lo, hi = k133_idx[i - 1], k133_idx[i]
                    w = k154_rets[(k154_rets.index > lo) & (k154_rets.index <= hi)]
                    if len(w) > 0:
                        agg.append(w.sum())
                        valid_idx.append(hi)
                if not agg:
                    continue
                s = pd.Series(agg, index=valid_idx)
                aligned = pd.concat([s, ret.loc[valid_idx]], axis=1, join="inner").dropna()
                if len(aligned) > 5:
                    rho = float(aligned.iloc[:, 0].corr(aligned.iloc[:, 1]))
                    sub[k133_name] = {"rho": rho, "n_overlap": int(len(aligned))}
            except Exception as ex:
                sub[k133_name] = {"error": str(ex)}
        out[var_name] = sub
    return out


# --------------------------------------------------------- main
def main():
    t0 = time.time()
    print("Loading panels ...")
    fr_panel, px_at_fr, pr_at_fr = build_panels()
    print(f"  FR panel: {fr_panel.shape}, range {fr_panel.index.min()} .. {fr_panel.index.max()}")
    print(f"  Symbols ({fr_panel.shape[1]}): {list(fr_panel.columns)}")

    print("Building design FR and z-score signal ...")
    design = design_fr_panel(pr_at_fr)
    z_panel = build_z_signal(fr_panel, design)
    z_abs = np.abs(z_panel.values)
    print(f"  z stats: mean={float(np.nanmean(z_panel.values)):.3f} "
          f"std={float(np.nanstd(z_panel.values)):.3f} "
          f"|z|>2 frac={float(np.nanmean(z_abs > 2)):.4f} "
          f"|z|>3 frac={float(np.nanmean(z_abs > 3)):.4f}")

    n_perm = 300
    n_boot = 300

    results = {}
    for name, cfg in VARIANTS.items():
        results[name] = run_variant(name, cfg, fr_panel, px_at_fr, z_panel,
                                     n_perm=n_perm, n_boot=n_boot)
        print(f"     [elapsed {time.time() - t0:.1f}s]")

    print("Correlation with K133 (per K154 variant) ...")
    corr = correlation_with_k133(results, ROOT / "wave_k133_curves.json")
    for k, v in corr.items():
        if isinstance(v, dict):
            for kk, vv in v.items():
                print(f"  {k} <-> K133::{kk}: {vv}")
        else:
            print(f"  {k}: {v}")

    out_path = ROOT / "wave_k154_cost_aware_drift.json"
    curves_path = ROOT / "wave_k154_curves.json"

    summary = {k: {kk: vv for kk, vv in v.items()
                   if kk not in ("equity_curve", "equity_idx", "rets_series")}
               for k, v in results.items()}
    summary["_correlation_k133"] = corr
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
        "vol_lookback_events": VOL_LOOKBACK,
        "design_std_lookback_events": DESIGN_STD_LB,
        "ir_floor_8h": IR_FLOOR_8H,
        "premium_clamp": PREMIUM_CLAMP,
        "wave": "K154",
        "parent_wave": "K153",
        "purpose": "Cost-aware variant of K153: rare events (z>3) + long hold (15-30) to reduce turnover",
        "design_formula": "design = premium + clip(IR_floor - premium, -PREMIUM_CLAMP, +PREMIUM_CLAMP)",
        "signal": "z = (realized_FR - design_FR) / rolling_30d_std(realized - design)",
        "direction_default": "FADE (z>+thr → SHORT; z<-thr → LONG); V_z3_continuation REVERSES",
    }
    curves = {k: {"equity_curve": v["equity_curve"],
                  "equity_idx": v["equity_idx"]}
              for k, v in results.items()}

    with open(out_path, "w") as f:
        json.dump(summary, f, indent=2, default=str)
    with open(curves_path, "w") as f:
        json.dump(curves, f, indent=2, default=str)

    elapsed = time.time() - t0
    print(f"\nDone in {elapsed:.1f}s")
    print(f"  -> {out_path}")
    print(f"  -> {curves_path}")

    print("\n=== Summary (K154 Cost-Aware Designed FR Drift) ===")
    print(f"{'variant':22s} {'netSR':>7s} {'OOS':>7s} {'grossSR':>8s} {'MaxDD':>7s} "
          f"{'p_perm':>7s} {'price':>9s} {'fund':>9s} {'cost':>8s} {'n':>5s} {'gates':>6s}")
    for name, r in results.items():
        full, oos = r["full"], r["oos"]
        perm = r["permutation"]
        dec = r["decomposition"]
        g = r["gates"]
        print(f"{name:22s} {full['sharpe']:+7.2f} {oos['sharpe']:+7.2f} "
              f"{r['gross_sharpe']:+8.2f} {full['max_dd']:7.2%} "
              f"{perm['p_value_net']:7.3f} {dec['price_pnl']:+9.4f} "
              f"{dec['fund_pnl']:+9.4f} {dec['cost']:8.4f} "
              f"{r['n_trades_or_rebals']:5d} {g['pass_count']:>3d}/6")

    # K153 baseline reminder
    print("\n=== K153 baseline (for comparison) ===")
    try:
        with open(ROOT / "wave_k153_designed_fr_drift.json") as f:
            k153 = json.load(f)
        for nm, r in k153.items():
            if nm.startswith("_"):
                continue
            print(f"  {nm:14s} netSR={r['full']['sharpe']:+.2f} grossSR={r['gross_sharpe']:+.2f} "
                  f"cost={r['decomposition']['cost']:.4f} n={r['n_trades_or_rebals']}")
    except Exception as ex:
        print(f"  k153 load error: {ex}")


if __name__ == "__main__":
    main()

"""
Wave K153 — Designed Funding-Rate Drift (R6-2, arxiv 2506.08573 July 2025)

Hypothesis (arxiv 2506.08573):
  Decompose realized funding into "design components":
    - Interest-rate floor (constant, ~0.01% per 8h for current crypto)
    - Premium-index component (from mark-vs-index basis)
    - Realized FR = floor + premium + residual
  When realized FR deviates strongly from "design target", price reverts
  toward spot in 8-24h.

Signal:
    z = (realized_FR - design_FR) / rolling_30d_std(realized_FR - design_FR)
    |z| > 2 → fade (SHORT if z>+2; LONG if z<-2)

Hold: until z returns to |z|<0.5 OR max 3 days (per-symbol variants).

Variants:
  V_z2_h3d    : ±2σ,   3d max hold   (PRIMARY)
  V_z25_h3d   : ±2.5σ stricter
  V_z2_h1d    : ±2σ,   1d max hold
  V_z2_xs     : cross-sectional top-3 / bot-3, 3d hold

Stats:
  730d, IS 70% / OOS 30%
  Walk-forward 4-fold
  One-sided permutation (cross-sectional shuffle) n=300
  Block bootstrap CI on OOS Sharpe n=300
  DSR N_trials=4
  Cost stress ±50% (cost_bps = 7 per side per leg)
  Correlation with K133 / K127 OOS returns

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

# Intersection: bybit_fr_*_730d AND hist_premium_*_4h_730d
SYMBOLS = [
    "ADA", "APT", "ARB", "ARKM", "AVAX", "BNB", "BOME", "BTC", "DOGE", "DOT",
    "ENA", "ETH", "INJ", "JTO", "JUP", "LINK", "MANTA", "NEAR", "ONDO", "OP",
    "SEI", "SOL", "STRK", "SUI", "TAO", "TIA", "WIF", "WLD", "XRP",
]

COST_BPS = 7.0
IS_FRAC = 0.70
SEED = 20260524

# Per-event ann factor: 365.25 * 3 events/day = 1096
ANN_FACTOR_EVENT = np.sqrt(365.25 * 3)

VOL_TARGET = 0.10
VOL_CAP = 1.5
VOL_LOOKBACK = 30  # 8h events

# Paper's interest-rate floor ~ 0.01% per 8h
IR_FLOOR_8H = 1e-4
PREMIUM_CLAMP = 5e-4   # ±0.05% cap on (ir - premium) component (Bybit-style)
DESIGN_STD_LB = 30 * 3  # 30d rolling std in 8h events


# --------------------------------------------------------- data loading
FR_FILE_OVERRIDES = {}     # no overrides — symbols match
PX_FILE_OVERRIDES = {}     # no overrides — 4h_730d exists for all selected


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
    # use close
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
    # Align price to FR timestamps via ffill
    px_at_fr = px_panel.reindex(fr_panel.index, method="ffill")
    # Premium 4h → 8h: take latest <= FR ts (within prior 8h)
    # For simplicity ffill premium to FR index
    pr_at_fr = pr_panel.reindex(fr_panel.index, method="ffill")
    return fr_panel, px_at_fr, pr_at_fr


# --------------------------------------------------------- design FR
def design_fr_panel(pr_at_fr):
    """Bybit-style design FR formula (paper R6-2 simplified):
       design = premium + clamp(IR_floor - premium, -PREMIUM_CLAMP, +PREMIUM_CLAMP)

       Limit case:
         - premium ≈ IR  → design ≈ IR
         - premium >> IR → design ≈ premium + clamp(IR-premium, -cap, cap)
                                  = premium - cap (when premium-IR > cap)
       i.e. design tracks premium when premium is large, floors at IR otherwise.
    """
    p = pr_at_fr.values
    delta = IR_FLOOR_8H - p
    delta_clip = np.clip(delta, -PREMIUM_CLAMP, +PREMIUM_CLAMP)
    design = p + delta_clip
    return pd.DataFrame(design, index=pr_at_fr.index, columns=pr_at_fr.columns)


# --------------------------------------------------------- z-score signal
def build_z_signal(fr_panel, design_panel, lookback=DESIGN_STD_LB):
    """z = (realized - design) / rolling_std(realized - design, lookback)
       Shift 1 to avoid look-ahead.
    """
    resid = fr_panel - design_panel
    rolling_std = resid.rolling(lookback, min_periods=lookback // 2).std()
    z = resid / rolling_std.replace(0, np.nan)
    return z.shift(1)


# --------------------------------------------------------- backtest per-symbol fade
def backtest_per_symbol(
    fr_panel, px_at_fr, z_panel,
    z_enter=2.0, z_exit=0.5, max_hold_events=9,
    cost_bps=COST_BPS,
    vol_target=VOL_TARGET, vol_cap=VOL_CAP, vol_lookback=VOL_LOOKBACK,
):
    """Per-symbol stateful fade:
       enter when |z|>z_enter, hold until |z|<z_exit or hold>=max_hold_events.
       Position size: vol-targeted, capped.
       Per-symbol weight = sign(-z) * min(vol_target/sym_vol_ann, vol_cap) / N_active
       (Equal-weight active legs, normalized at each rebal for portfolio.)
    """
    fr_arr = fr_panel.values
    px_arr = px_at_fr.values
    z_arr = z_panel.values
    T, N = fr_arr.shape
    cols = list(fr_panel.columns)

    # sym vol on 8h events log-rets
    with np.errstate(invalid="ignore", divide="ignore"):
        lr = np.log(px_arr[1:] / px_arr[:-1])
    lr = np.where(np.isfinite(lr), lr, 0.0)
    sym_vol = np.full((T, N), np.nan, dtype=float)
    for t in range(1, T):
        lo = max(0, t - vol_lookback)
        if t - lo >= 5:
            sym_vol[t] = np.nanstd(lr[lo:t], axis=0, ddof=1) * np.sqrt(3 * 365.25)

    # State per symbol
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
        prev_w = pos_sign * pos_size  # net per-sym weight (before update)

        for i in range(N):
            z = z_arr[t, i]
            if in_pos[i]:
                pos_age[i] += 1
                # Exit conditions
                exit_now = False
                if np.isfinite(z) and abs(z) < z_exit:
                    exit_now = True
                if pos_age[i] >= max_hold_events:
                    exit_now = True
                # also exit if z flips sign
                if np.isfinite(z) and np.sign(z) == -pos_sign[i] and abs(z) > 0.5:
                    # z went opposite way → exit (fade is invalidated)
                    exit_now = True
                if exit_now:
                    in_pos[i] = False
                    pos_sign[i] = 0.0
                    pos_size[i] = 0.0
                    pos_age[i] = 0
            else:
                # Entry conditions
                if np.isfinite(z) and abs(z) > z_enter:
                    # fade direction: sign = -sign(z)
                    sv = sym_vol[t, i]
                    if not np.isfinite(sv) or sv <= 0:
                        size = 1.0
                    else:
                        size = min(vol_target / sv, vol_cap)
                    pos_sign[i] = -np.sign(z)
                    pos_size[i] = size
                    in_pos[i] = True
                    pos_age[i] = 0
                    n_trades += 1
                    if pos_sign[i] > 0:
                        long_count[i] += 1
                    else:
                        short_count[i] += 1

        # New weights (per-symbol, NOT normalized to gross 1 — vol-targeted)
        cur_w = pos_sign * pos_size
        turn = float(np.abs(cur_w - prev_w).sum())
        # cost
        c = turn * (cost_bps / 1e4)

        # PnL over [t, t+1]: but we use t-1→t since price aligned at fr ts
        # Use period return from t-1 to t (price already ffill'd to fr ts)
        with np.errstate(invalid="ignore", divide="ignore"):
            pr_event = px_arr[t] / px_arr[t - 1] - 1.0
        pr_event = np.where(np.isfinite(pr_event), pr_event, 0.0)
        # Funding paid at event t: longs pay positive FR
        fr_event = fr_arr[t]
        fr_event = np.where(np.isfinite(fr_event), fr_event, 0.0)

        # Note: positions taken at t apply forward; here we credit/debit on entering bar
        # For simplicity treat weight cur_w as being held through period t-1 → t
        # (i.e. position decided at t-1 using z_panel shifted, applied to ret t-1→t)
        # We'll shift indices accordingly: use prev_w for PnL.
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


# --------------------------------------------------------- backtest XS rebal
def backtest_xs(
    fr_panel, px_at_fr, z_panel,
    n_long=3, n_short=3, hold_n=9,
    cost_bps=COST_BPS,
    vol_target=VOL_TARGET, vol_cap=VOL_CAP, vol_lookback=VOL_LOOKBACK,
    rebal_on_change=True,
):
    """Cross-sectional rebal every hold_n events:
       - Long lowest n_long z values (most-negative resid: fade)
       - Short highest n_short z values
       Vol-target per leg, equal-weight within leg.
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

            # SHORT: highest positive z (fade)
            cand_short = []
            for i in order_desc:
                if valid[i] and z_row[i] > 0:
                    cand_short.append(i)
                    if len(cand_short) == n_short:
                        break
            # LONG: lowest negative z (fade)
            cand_long = []
            for i in order_asc:
                if valid[i] and z_row[i] < 0:
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


def permutation_test_xs(fr_panel, px_at_fr, z_panel, cfg, n_iter=300, seed=SEED):
    """Cross-sectional row shuffle of z_panel — preserves time-series autocorr
    but breaks cross-sectional pick. Works for both per-sym and XS variants.
    """
    rng = np.random.default_rng(seed)
    is_xs = cfg.get("kind") == "xs"
    ann = ANN_FACTOR_EVENT

    if is_xs:
        actual = backtest_xs(fr_panel, px_at_fr, z_panel,
                             n_long=cfg["n_long"], n_short=cfg["n_short"],
                             hold_n=cfg["hold"])
        ann_xs = np.sqrt((365.25 * 3) / cfg["hold"])
        actual_sr = perf_stats(actual["rets"], ann_xs)["sharpe"]
        actual_sr_g = gross_sharpe(actual, ann_xs)
    else:
        actual = backtest_per_symbol(fr_panel, px_at_fr, z_panel,
                                     z_enter=cfg["z_enter"], z_exit=cfg["z_exit"],
                                     max_hold_events=cfg["max_hold"])
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
        if is_xs:
            res = backtest_xs(fr_panel, px_at_fr, zp,
                              n_long=cfg["n_long"], n_short=cfg["n_short"],
                              hold_n=cfg["hold"])
            ann_use = np.sqrt((365.25 * 3) / cfg["hold"])
        else:
            res = backtest_per_symbol(fr_panel, px_at_fr, zp,
                                      z_enter=cfg["z_enter"], z_exit=cfg["z_exit"],
                                      max_hold_events=cfg["max_hold"])
            ann_use = ann
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
    is_xs = cfg.get("kind") == "xs"
    for f in range(n_folds):
        s = f * fold_size
        e = (f + 1) * fold_size if f < n_folds - 1 else T
        sub_fr = fr_panel.iloc[s:e]
        sub_px = px_at_fr.iloc[s:e]
        sub_z = z_panel.iloc[s:e]
        try:
            if is_xs:
                r = backtest_xs(sub_fr, sub_px, sub_z,
                                n_long=cfg["n_long"], n_short=cfg["n_short"],
                                hold_n=cfg["hold"])["rets"]
                ann = np.sqrt((365.25 * 3) / cfg["hold"])
            else:
                r = backtest_per_symbol(sub_fr, sub_px, sub_z,
                                        z_enter=cfg["z_enter"], z_exit=cfg["z_exit"],
                                        max_hold_events=cfg["max_hold"])["rets"]
                ann = ANN_FACTOR_EVENT
        except Exception:
            r = pd.Series(dtype=float)
            ann = ANN_FACTOR_EVENT
        out.append({"fold": f, **perf_stats(r, ann)})
    return out


# --------------------------------------------------------- variants
VARIANTS = {
    "V_z2_h3d":  dict(kind="psym", z_enter=2.0, z_exit=0.5, max_hold=9),   # PRIMARY
    "V_z25_h3d": dict(kind="psym", z_enter=2.5, z_exit=0.5, max_hold=9),
    "V_z2_h1d":  dict(kind="psym", z_enter=2.0, z_exit=0.5, max_hold=3),
    "V_z2_xs":   dict(kind="xs",   n_long=3,    n_short=3,  hold=9),
}
N_TRIALS_DSR = 4


def run_variant(name, cfg, fr_panel, px_at_fr, z_panel,
                n_perm=300, n_boot=300):
    is_xs = cfg.get("kind") == "xs"
    if is_xs:
        print(f"  >> {name}: XS top={cfg['n_long']}/{cfg['n_short']} hold={cfg['hold']} events")
        res = backtest_xs(fr_panel, px_at_fr, z_panel,
                          n_long=cfg["n_long"], n_short=cfg["n_short"],
                          hold_n=cfg["hold"])
        ann = np.sqrt((365.25 * 3) / cfg["hold"])
    else:
        print(f"  >> {name}: per-sym z_enter=±{cfg['z_enter']} z_exit=±{cfg['z_exit']} max_hold={cfg['max_hold']}")
        res = backtest_per_symbol(fr_panel, px_at_fr, z_panel,
                                  z_enter=cfg["z_enter"], z_exit=cfg["z_exit"],
                                  max_hold_events=cfg["max_hold"])
        ann = ANN_FACTOR_EVENT

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
    if is_xs:
        res_lo = backtest_xs(fr_panel, px_at_fr, z_panel,
                             n_long=cfg["n_long"], n_short=cfg["n_short"],
                             hold_n=cfg["hold"], cost_bps=COST_BPS * 0.5)
        res_hi = backtest_xs(fr_panel, px_at_fr, z_panel,
                             n_long=cfg["n_long"], n_short=cfg["n_short"],
                             hold_n=cfg["hold"], cost_bps=COST_BPS * 1.5)
    else:
        res_lo = backtest_per_symbol(fr_panel, px_at_fr, z_panel,
                                     z_enter=cfg["z_enter"], z_exit=cfg["z_exit"],
                                     max_hold_events=cfg["max_hold"],
                                     cost_bps=COST_BPS * 0.5)
        res_hi = backtest_per_symbol(fr_panel, px_at_fr, z_panel,
                                     z_enter=cfg["z_enter"], z_exit=cfg["z_exit"],
                                     max_hold_events=cfg["max_hold"],
                                     cost_bps=COST_BPS * 1.5)
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


# --------------------------------------------------------- correlation w/ K133, K127
def correlation_with_others(results, k133_curves_path, k127_curves_path):
    """Compute correlation of K153 PRIMARY (V_z2_h3d) net returns with K133 (REVERSAL)
       and K127 (BIS Carry) net returns, using full-window where overlap exists.
    """
    out = {}
    primary = results.get("V_z2_h3d")
    if primary is None:
        return out
    k153_rets = pd.Series(primary["rets_series"],
                           index=pd.to_datetime(primary["equity_idx"]))

    # K133: per-variant equity at rebal points (every 5 days = 15 events)
    try:
        with open(k133_curves_path) as f:
            k133 = json.load(f)
        for var_name, d in k133.items():
            eq = pd.Series(d["equity_curve"], index=pd.to_datetime(d["equity_idx"]))
            ret = eq.pct_change().dropna()
            # Resample K153 (3 events/day) to align to K133 rebal points (15 events/rebal):
            # Aggregate K153 returns over each K133 rebal window
            k133_idx = ret.index
            k153_agg = []
            valid_idx = []
            for i in range(1, len(k133_idx)):
                lo, hi = k133_idx[i - 1], k133_idx[i]
                w = k153_rets[(k153_rets.index > lo) & (k153_rets.index <= hi)]
                if len(w) > 0:
                    k153_agg.append(w.sum())
                    valid_idx.append(hi)
            if not k153_agg:
                continue
            k153_s = pd.Series(k153_agg, index=valid_idx)
            aligned = pd.concat([k153_s, ret.loc[valid_idx]], axis=1, join="inner").dropna()
            if len(aligned) > 5:
                rho = float(aligned.iloc[:, 0].corr(aligned.iloc[:, 1]))
                out[f"K133::{var_name}"] = {"rho": rho, "n_overlap": int(len(aligned))}
    except Exception as ex:
        out["K133_error"] = str(ex)

    # K127: per-event PnL net
    try:
        with open(k127_curves_path) as f:
            k127 = json.load(f)
        ts = pd.to_datetime(k127["timestamps"])
        k127_ret = pd.Series(k127["pnl_net"], index=ts)
        aligned = pd.concat([k153_rets, k127_ret], axis=1, join="inner").dropna()
        if len(aligned) > 5:
            rho = float(aligned.iloc[:, 0].corr(aligned.iloc[:, 1]))
            out["K127::primary"] = {"rho": rho, "n_overlap": int(len(aligned))}
    except Exception as ex:
        out["K127_error"] = str(ex)

    return out


# --------------------------------------------------------- main
def main():
    t0 = time.time()
    print("Loading panels ...")
    fr_panel, px_at_fr, pr_at_fr = build_panels()
    print(f"  FR panel: {fr_panel.shape}, range {fr_panel.index.min()} .. {fr_panel.index.max()}")
    print(f"  Symbols ({fr_panel.shape[1]}): {list(fr_panel.columns)}")
    print(f"  Premium aligned: {pr_at_fr.shape}, non-null frac: {float(pr_at_fr.notna().mean().mean()):.3f}")

    print("Building design FR and z-score signal ...")
    design = design_fr_panel(pr_at_fr)
    z_panel = build_z_signal(fr_panel, design)
    print(f"  z stats: mean={float(np.nanmean(z_panel.values)):.3f} "
          f"std={float(np.nanstd(z_panel.values)):.3f} "
          f"|z|>2 frac={float(np.nanmean(np.abs(z_panel.values) > 2)):.4f}")

    n_perm = 300
    n_boot = 300

    results = {}
    for name, cfg in VARIANTS.items():
        results[name] = run_variant(name, cfg, fr_panel, px_at_fr, z_panel,
                                     n_perm=n_perm, n_boot=n_boot)
        print(f"     [elapsed {time.time() - t0:.1f}s]")

    print("Correlation with K133 / K127 ...")
    corr = correlation_with_others(
        results,
        ROOT / "wave_k133_curves.json",
        ROOT / "wave_k127_curves.json",
    )
    for k, v in corr.items():
        print(f"  {k}: {v}")

    # Save outputs
    out_path = ROOT / "wave_k153_designed_fr_drift.json"
    curves_path = ROOT / "wave_k153_curves.json"

    summary = {k: {kk: vv for kk, vv in v.items()
                   if kk not in ("equity_curve", "equity_idx", "rets_series")}
               for k, v in results.items()}
    summary["_correlation"] = corr
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
        "wave": "K153",
        "source_paper": "arxiv 2506.08573 (July 2025) — R6-2 Designed Funding-Rate Drift",
        "design_formula": "design = premium + clip(IR_floor - premium, -PREMIUM_CLAMP, +PREMIUM_CLAMP)",
        "signal": "z = (realized_FR - design_FR) / rolling_30d_std(realized - design)",
        "direction": "FADE: z>+thr → SHORT; z<-thr → LONG",
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

    print("\n=== Summary (DESIGNED FR DRIFT FADE) ===")
    for name, r in results.items():
        full, oos = r["full"], r["oos"]
        perm = r["permutation"]
        dec = r["decomposition"]
        g = r["gates"]
        print(f"{name:14s} netSR={full['sharpe']:+.2f} OOS={oos['sharpe']:+.2f} "
              f"grossSR={r['gross_sharpe']:+.2f} MaxDD={full['max_dd']:.2%} "
              f"p={perm['p_value_net']:.3f} "
              f"price={dec['price_pnl']:+.4f} fund={dec['fund_pnl']:+.4f} "
              f"cost={dec['cost']:.4f} n={r['n_trades_or_rebals']} "
              f"DSR_oos={r['dsr_oos']:.2f} gates={g['pass_count']}/6")

    print("\n=== Correlation with K133 / K127 ===")
    for k, v in corr.items():
        print(f"  {k}: {v}")


if __name__ == "__main__":
    main()

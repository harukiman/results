"""
Wave K157 — FYpGE Cross-Section (R6-16, 1Token institutional metric)
====================================================================
Hypothesis (Bybit + 1Token Jan-Feb 2026)
  Funding Yield per Gross Exposure (FYpGE) = cumulative_funding / gross_notional.
  Used by 11 institutional teams managing $4B+. Captures funding-income EFFICIENCY
  (not just funding LEVEL like K127 BIS).

  Long top-decile FYpGE   (highest funding income per exposure = "funding rich")
  Short bottom-decile FYpGE (low or negative yield per exposure)
  Weekly rebalance, dollar-neutral, equal weight.

Difference vs existing FR strategies (K127, K133):
  - K127 BIS CARRY    : rank on funding LEVEL, long cheap / short expensive.
  - K133 FR REVERSAL  : z-score of funding, fade extremes (long cheap, short pricy).
  - K157 FYpGE        : rank on funding INCOME / EXPOSURE = funding × constant_proxy.
                         Same sort direction as K127 but normalised by activity.

Method (pre-registered, per 8h funding event)
  1. cumulative_funding_7d = sum of last 21 funding rates
  2. gross_notional_proxy = 30d median USD volume / 365 / 3 (per-event proxy)
  3. FYpGE = cumulative_funding_7d * 100 / gross_notional_proxy (in %)
  4. Lag 1 event
  5. Cross-section rank by FYpGE
  6. Long top-3 (highest FYpGE), short bottom-3 (lowest/negative)
  7. Hold 7 days (variants: 3d, 14d)
  8. Costs: 0.07% (7 bps) per side per leg

Variants
  V_top3_h7   : top-3 / bot-3, 7d hold (PRIMARY)
  V_top5_h7   : top-5 / bot-5, 7d hold (breadth)
  V_top3_h14  : top-3 / bot-3, 14d hold (less turnover)
  V_top3_h3   : top-3 / bot-3, 3d hold (more agility)

Stats
  730d, IS 70% / OOS 30%
  Walk-forward 4-fold
  One-sided permutation (cross-sectional shuffle) n=300
  Block bootstrap CI on OOS Sharpe n=300
  DSR N_trials=4
  Cost stress ±50%
  Correlation with K127/K133 returns
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

# 15-symbol universe (BIS/1Token majors + actives present in cache)
SYMBOLS = [
    "BTC", "ETH", "SOL", "BNB", "DOGE", "AVAX", "LINK", "ADA",
    "XRP", "INJ", "OP", "WIF", "BONK", "ARB", "DOT",
]

COST_BPS = 7.0                  # 0.07% per side per leg
FUND_LOOKBACK_EVENTS = 21       # 7d * 3 funding events/day
VOL_MEDIAN_LOOKBACK_4H = 30 * 6 # 30 days at 4h cadence
IS_FRAC = 0.70
SEED = 20260524
N_TRIALS_DSR = 4
N_PERM = 300
N_BOOT = 300

ANN_FACTOR_3D = np.sqrt(365 / 3)
ANN_FACTOR_7D = np.sqrt(365 / 7)
ANN_FACTOR_14D = np.sqrt(365 / 14)

FR_FILE_OVERRIDES = {
    "BONK": "bybit_fr_1000BONKUSDT_730d.parquet",
}
PX_FILE_OVERRIDES = {
    "BONK": "BONKUSDT_4h_730d.parquet",
}


# --------------------------------------------------------------------- I/O
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


def load_px_and_qvol(sym):
    fname = PX_FILE_OVERRIDES.get(sym, f"{sym}USDT_4h_730d.parquet")
    p = CACHE / fname
    if not p.exists():
        return None, None
    df = pd.read_parquet(p)
    df["open_time"] = pd.to_datetime(df["open_time"])
    df = df.set_index("open_time").sort_index()
    df = df[~df.index.duplicated(keep="last")]
    close = df["close"].astype(float).rename(sym)
    qvol = df["quote_volume"].astype(float).rename(sym)
    return close, qvol


def build_panels():
    fr_dict, px_dict, qv_dict = {}, {}, {}
    for s in SYMBOLS:
        fr = load_fr(s)
        px, qv = load_px_and_qvol(s)
        if fr is None or px is None or qv is None:
            print(f"  skip {s} (missing data)")
            continue
        fr_dict[s] = fr
        px_dict[s] = px
        qv_dict[s] = qv

    fr_panel = pd.concat(fr_dict.values(), axis=1).sort_index()
    px_panel = pd.concat(px_dict.values(), axis=1).sort_index()
    qv_panel = pd.concat(qv_dict.values(), axis=1).sort_index()

    fr_panel = fr_panel.dropna(thresh=int(fr_panel.shape[1] * 0.8))

    # Rolling 30d median quote-volume on the 4h grid (per-bar USD volume)
    qv_med_4h = qv_panel.rolling(VOL_MEDIAN_LOOKBACK_4H,
                                 min_periods=VOL_MEDIAN_LOOKBACK_4H // 2).median()

    # Reindex onto FR event grid; ffill so each FR event has the latest 30d median
    px_at_fr = px_panel.reindex(fr_panel.index, method="ffill")
    qv_med_at_fr = qv_med_4h.reindex(fr_panel.index, method="ffill")

    return fr_panel, px_at_fr, qv_med_at_fr


# --------------------------------------------------------------------- signal
def build_fypge(fr_panel, qv_med_at_fr):
    """
    FYpGE = cumulative_funding_7d (sum last 21 events) * 100
             / gross_notional_proxy_per_event
    gross_notional_proxy_per_event = 30d-median(bar-USD-volume) * (4h-bars/day) / 3
                                    = 30d-median * 6 / 3 = 30d-median * 2
      That equals "daily volume / 3" (the 3 funding events per day),
      i.e. the original "30d_med_USD_vol / 365 / 3" but DAILY-scaled
      since our qv is per-bar.

    But the spec literally says: "30-day median USD volume / 365 / 3".
      Interpreting 'USD volume' as the trailing 30d TOTAL ⇒ rolling 30d sum.
      Per-event proxy = (trailing 30d total) / 30 / 3   (per-day / per-event)

    We use the canonical reading: per-event proxy = 30d-median-daily-volume / 3.
      30d-median-daily-volume ≈ median(per-bar) * 6 (6 bars per day).
    """
    cum_fr = fr_panel.rolling(FUND_LOOKBACK_EVENTS,
                              min_periods=FUND_LOOKBACK_EVENTS).sum()
    daily_vol_proxy = qv_med_at_fr * 6.0          # 4h bars per day = 6
    per_event_proxy = daily_vol_proxy / 3.0       # 3 funding events per day
    # Avoid division by zero / extremely small values
    per_event_proxy = per_event_proxy.replace(0, np.nan)
    fypge = (cum_fr * 100.0) / per_event_proxy
    # Lag by 1 event (no look-ahead) — done at sort time
    return fypge.shift(1), cum_fr.shift(1), per_event_proxy.shift(1)


# --------------------------------------------------------------------- backtest
def backtest_fypge_xs(fr_panel, px_at_fr, signal_panel,
                      k=3, hold_n=21, cost_bps=COST_BPS):
    """
    fr_panel       : T x N funding rates at 8h events
    px_at_fr       : T x N close at FR timestamps
    signal_panel   : T x N FYpGE values (already lagged)
    k              : long top-k FYpGE / short bot-k FYpGE
    hold_n         : hold horizon in 8h events (21 = 7d, 9 = 3d, 42 = 14d)
    """
    sig_arr = signal_panel.values
    fr_arr = fr_panel.values
    px_arr = px_at_fr.values
    T = sig_arr.shape[0]
    N = sig_arr.shape[1]
    cols = list(fr_panel.columns)
    idx_vals = fr_panel.index.values

    rebal_pos = np.arange(0, T, hold_n)

    rets, fund_pnl_arr, price_pnl_arr, cost_arr = [], [], [], []
    turnover_arr, gross_notional_arr = [], []
    rets_idx = []
    long_count = np.zeros(N, dtype=int)
    short_count = np.zeros(N, dtype=int)

    prev_w = np.zeros(N)
    n_rebal_events = 0

    for ti in range(len(rebal_pos) - 1):
        t = rebal_pos[ti]
        t_next = rebal_pos[ti + 1]
        row = sig_arr[t]
        valid = ~np.isnan(row)

        if valid.sum() < 2 * k + 1:
            w = np.zeros(N)
        else:
            valid_idx = np.where(valid)[0]
            # ascending FYpGE: lowest first, highest last
            ordered = valid_idx[np.argsort(row[valid_idx])]
            shorts = ordered[:k]      # bottom-k = lowest FYpGE (short)
            longs = ordered[-k:]      # top-k   = highest FYpGE (long)
            w = np.zeros(N)
            w[longs] = +1.0 / k
            w[shorts] = -1.0 / k

        # Compare set-change for rebalancing accounting
        if not np.array_equal(np.sign(w), np.sign(prev_w)):
            n_rebal_events += 1

        turn = float(np.abs(w - prev_w).sum())
        cost = turn * (cost_bps / 1e4)
        gross_notional = float(np.abs(w).sum())

        # Realised hold-period return
        px_now = px_arr[t]
        px_next = px_arr[t_next]
        with np.errstate(invalid="ignore", divide="ignore"):
            pr = px_next / px_now - 1.0
        pr = np.where(np.isfinite(pr), pr, 0.0)

        # Funding pnl: long pays when funding > 0
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


# --------------------------------------------------------------------- stats
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


def deflated_sharpe(sr, n_obs, n_trials, skew=0.0, kurt=3.0):
    if n_obs < 20 or n_trials < 1:
        return 0.0
    emc = 0.5772
    e_max = np.sqrt(2 * np.log(max(n_trials, 2))) * (1 - emc) + \
            (1 - emc) / np.sqrt(2 * np.log(max(n_trials, 2)))
    var = (1 - skew * sr + (kurt - 1) / 4.0 * sr ** 2) / max(n_obs - 1, 1)
    if var <= 0:
        return 0.0
    from math import erf, sqrt
    z = (sr - e_max) / np.sqrt(var)
    return float(0.5 * (1 + erf(z / sqrt(2))))


def block_bootstrap_ci(rets, ann_factor, n_iter=N_BOOT, block=3, seed=SEED):
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


def permutation_test(fr_panel, px_at_fr, signal_panel, cfg,
                     n_iter=N_PERM, seed=SEED):
    """Shuffle FYpGE ranks cross-sectionally per row."""
    rng = np.random.default_rng(seed)
    ann = cfg["ann"]
    hold_n = cfg["hold"]
    k = cfg["k"]

    actual = backtest_fypge_xs(fr_panel, px_at_fr, signal_panel,
                                k=k, hold_n=hold_n)
    actual_sr = perf_stats(actual["rets"], ann)["sharpe"]

    base = signal_panel.values
    null_sr = np.zeros(n_iter)
    for i in range(n_iter):
        permuted = base.copy()
        for r in range(permuted.shape[0]):
            row = permuted[r]
            mask = ~np.isnan(row)
            idxs = np.where(mask)[0]
            if len(idxs) > 1:
                permuted[r, idxs] = rng.permutation(row[idxs])
        sp = pd.DataFrame(permuted, index=signal_panel.index,
                          columns=signal_panel.columns)
        res = backtest_fypge_xs(fr_panel, px_at_fr, sp, k=k, hold_n=hold_n)
        null_sr[i] = perf_stats(res["rets"], ann)["sharpe"]

    return {
        "actual_sharpe": float(actual_sr),
        "null_mean": float(null_sr.mean()),
        "null_std": float(null_sr.std()),
        "null_p95": float(np.quantile(null_sr, 0.95)),
        "p_value": float((null_sr >= actual_sr).mean()),
        "n_iter": n_iter,
    }


def walk_forward(fr_panel, px_at_fr, signal_panel, cfg, n_folds=4):
    T = len(fr_panel)
    fold_size = T // n_folds
    out = []
    for f in range(n_folds):
        s = f * fold_size
        e = (f + 1) * fold_size if f < n_folds - 1 else T
        sub_fr = fr_panel.iloc[s:e]
        sub_px = px_at_fr.iloc[s:e]
        sub_sig = signal_panel.iloc[s:e]
        try:
            r = backtest_fypge_xs(sub_fr, sub_px, sub_sig,
                                  k=cfg["k"], hold_n=cfg["hold"])["rets"]
        except Exception:
            r = pd.Series(dtype=float)
        out.append({"fold": f, **perf_stats(r, cfg["ann"])})
    return out


# --------------------------------------------------------------------- variants
VARIANTS = {
    "V_top3_h7":  dict(k=3, hold=21, ann=ANN_FACTOR_7D),   # PRIMARY (7d)
    "V_top5_h7":  dict(k=5, hold=21, ann=ANN_FACTOR_7D),
    "V_top3_h14": dict(k=3, hold=42, ann=ANN_FACTOR_14D),
    "V_top3_h3":  dict(k=3, hold=9,  ann=ANN_FACTOR_3D),
}


def run_variant(name, cfg, fr_panel, px_at_fr, signal_panel,
                n_perm=N_PERM, n_boot=N_BOOT):
    print(f"  >> {name}: k={cfg['k']} hold={cfg['hold']} ev "
          f"({cfg['hold']*8/24:.1f}d)")
    ann = cfg["ann"]
    hold_n = cfg["hold"]
    k = cfg["k"]

    res = backtest_fypge_xs(fr_panel, px_at_fr, signal_panel, k=k, hold_n=hold_n)
    rets = res["rets"]
    n_total = len(rets)
    n_is = int(n_total * IS_FRAC)

    # Diagnostic — flipped direction (long bot-FYpGE / short top-FYpGE).
    # NOT a separately registered variant; for sign-validation only.
    flipped_rets = -res["rets"]
    flipped_full = perf_stats(flipped_rets, ann)

    full_stats = perf_stats(rets, ann)
    is_stats = perf_stats(rets.iloc[:n_is], ann)
    oos_stats = perf_stats(rets.iloc[n_is:], ann)

    gross = res["price_pnl"] + res["fund_pnl"]
    gross_sr = perf_stats(gross, ann)["sharpe"]

    fund_total = float(res["fund_pnl"].sum())
    price_total = float(res["price_pnl"].sum())
    cost_total = float(res["cost"].sum())
    net_total = float(res["rets"].sum())
    turnover_total = float(res["turnover"].sum())
    turnover_per_event = float(res["turnover"].mean())
    avg_gross_notional = float(res["gross_notional"].mean())

    wf = walk_forward(fr_panel, px_at_fr, signal_panel, cfg, n_folds=4)

    res_lo = backtest_fypge_xs(fr_panel, px_at_fr, signal_panel,
                                k=k, hold_n=hold_n, cost_bps=COST_BPS * 0.5)
    res_hi = backtest_fypge_xs(fr_panel, px_at_fr, signal_panel,
                                k=k, hold_n=hold_n, cost_bps=COST_BPS * 1.5)
    cost_stress = {
        "low_50pct":   perf_stats(res_lo["rets"], ann)["sharpe"],
        "base_100pct": full_stats["sharpe"],
        "high_150pct": perf_stats(res_hi["rets"], ann)["sharpe"],
    }

    boot = block_bootstrap_ci(rets.iloc[n_is:].values, ann,
                               n_iter=n_boot, block=3, seed=SEED + 11)

    perm = permutation_test(fr_panel, px_at_fr, signal_panel, cfg, n_iter=n_perm)

    skew_v = float(stats.skew(rets.dropna())) if len(rets.dropna()) > 5 else 0.0
    kurt_v = float(stats.kurtosis(rets.dropna(), fisher=False)) if len(rets.dropna()) > 5 else 3.0
    dsr_full = deflated_sharpe(full_stats["sharpe"], full_stats["n"],
                                n_trials=N_TRIALS_DSR, skew=skew_v, kurt=kurt_v)
    dsr_oos = deflated_sharpe(oos_stats["sharpe"], oos_stats["n"],
                               n_trials=N_TRIALS_DSR, skew=skew_v, kurt=kurt_v)

    long_count = res["long_count"].sort_values(ascending=False).to_dict()
    short_count = res["short_count"].sort_values(ascending=False).to_dict()

    abs_sum = abs(price_total) + abs(fund_total) + 1e-9
    decomp = {
        "price_pnl": price_total,
        "fund_pnl": fund_total,
        "cost": cost_total,
        "net": net_total,
        "fund_pct_of_gross_abs": float(abs(fund_total) / abs_sum),
        "price_pct_of_gross_abs": float(abs(price_total) / abs_sum),
        "fund_dominant": bool(abs(fund_total) > abs(price_total)),
        "price_dominant": bool(abs(price_total) > abs(fund_total)),
    }

    # §6 gates (institutional bar)
    gates = {
        "oos_sr_ge_0_5":      bool(oos_stats["sharpe"] >= 0.5),
        "p_perm_lt_0_05":     bool(perm["p_value"] < 0.05),
        "max_dd_gt_neg40":    bool(full_stats["max_dd"] > -0.40),
        "cost_stress_robust": bool(cost_stress["high_150pct"] >= 0.5 * cost_stress["base_100pct"]
                                   if cost_stress["base_100pct"] > 0 else False),
        "dsr_oos_ge_0_5":     bool(dsr_oos >= 0.5),
        "wf_majority_pos":    bool(sum(1 for f in wf if f["sharpe"] > 0) >= 3),
    }
    gates["pass_count"] = int(sum(1 for v in gates.values() if v is True))
    gates["all_pass"] = bool(all(v for k_, v in gates.items()
                                  if k_ not in ("pass_count", "all_pass")))

    return {
        "config": {kk: vv for kk, vv in cfg.items() if kk != "ann"},
        "ann_factor": float(ann),
        "n_periods": n_total,
        "n_rebal_events": int(res["n_rebal_events"]),
        "full": full_stats,
        "is": is_stats,
        "oos": oos_stats,
        "flipped_direction_full_sharpe": float(flipped_full["sharpe"]),
        "flipped_direction_full_maxdd": float(flipped_full["max_dd"]),
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
        "_rets_series": rets,   # internal; stripped before save
    }


# --------------------------------------------------------------------- correlation w K127 / K133
def load_existing_curve(path, key):
    """
    Return pd.Series of period returns for a previous strategy variant.
    Supports two schemas:
      A) {variant: {"equity_curve": [...], "equity_idx": [...]}}    (K133)
      B) {"timestamps": [...], "pnl_net": [...], ...}               (K127)
    `key` is the variant name in schema A, or a label hint in schema B.
    """
    if not Path(path).exists():
        return None
    with open(path) as f:
        d = json.load(f)
    # Schema A
    if key in d and isinstance(d[key], dict) and "equity_curve" in d[key]:
        eq = pd.Series(d[key]["equity_curve"])
        idx = pd.to_datetime(d[key]["equity_idx"])
        eq.index = idx
        return eq.pct_change().dropna()
    # Schema B (single record): pnl_net directly == per-event return
    if "timestamps" in d and "pnl_net" in d:
        idx = pd.to_datetime(d["timestamps"])
        s = pd.Series(d["pnl_net"], index=idx)
        s = s[s != 0]
        return s
    return None


def correlate_with_existing(k157_rets, label_pairs):
    """label_pairs : list of (label, path, key)."""
    out = {}
    for label, path, key in label_pairs:
        other = load_existing_curve(path, key)
        if other is None or other.empty:
            out[label] = {"available": False, "n_overlap": 0}
            continue
        # Align by resampling both to daily mean returns then inner-join
        a = k157_rets.resample("1D").sum()
        b = other.resample("1D").sum()
        joined = pd.concat([a, b], axis=1, join="inner").dropna()
        joined.columns = ["k157", label]
        if len(joined) < 10 or joined["k157"].std() == 0 or joined[label].std() == 0:
            out[label] = {"available": True, "n_overlap": int(len(joined)),
                          "corr": 0.0, "note": "insufficient overlap or zero variance"}
            continue
        corr = float(joined["k157"].corr(joined[label]))
        out[label] = {
            "available": True,
            "n_overlap": int(len(joined)),
            "corr_daily": corr,
            "abs_corr": abs(corr),
            "orthogonal_lt_0_3": bool(abs(corr) < 0.3),
        }
    return out


# --------------------------------------------------------------------- main
def main():
    t0 = time.time()
    print("Loading FR + price + qvol panels ...")
    fr_panel, px_at_fr, qv_med_at_fr = build_panels()
    print(f"  FR panel : {fr_panel.shape}, "
          f"range {fr_panel.index.min()} .. {fr_panel.index.max()}")
    print(f"  Symbols  : {list(fr_panel.columns)}")

    print("Building FYpGE signal ...")
    fypge, cum_fr, per_event_proxy = build_fypge(fr_panel, qv_med_at_fr)
    print(f"  FYpGE coverage: "
          f"{(~fypge.isna()).sum().sum() / fypge.size * 100:.1f}% non-NaN")
    print(f"  FYpGE summary (%): mean={fypge.stack().mean():.4f} "
          f"std={fypge.stack().std():.4f} "
          f"p05={fypge.stack().quantile(0.05):.4f} "
          f"p95={fypge.stack().quantile(0.95):.4f}")

    results = {}
    for name, cfg in VARIANTS.items():
        results[name] = run_variant(name, cfg, fr_panel, px_at_fr, fypge,
                                     n_perm=N_PERM, n_boot=N_BOOT)
        elapsed = time.time() - t0
        print(f"     [elapsed {elapsed:.1f}s]")

    # ----------------------------------------------- cross-strategy correlation
    print("\nCorrelating K157 (primary) returns with K127 / K133 variants ...")
    primary_rets = results["V_top3_h7"]["_rets_series"]
    correlation_block = correlate_with_existing(
        primary_rets,
        [
            ("K127_top_bottom_3",     str(ROOT / "wave_k127_curves.json"), "V_top_bottom_3"),
            ("K127_top_bottom_5",     str(ROOT / "wave_k127_curves.json"), "V_top_bottom_5"),
            ("K127_top_bottom_3_24h", str(ROOT / "wave_k127_curves.json"), "V_top_bottom_3_24h"),
            ("K133_rev_5d_z15",       str(ROOT / "wave_k133_curves.json"), "V_rev_5d_z15"),
            ("K133_rev_7d_z15",       str(ROOT / "wave_k133_curves.json"), "V_rev_7d_z15"),
            ("K133_rev_3d_z15",       str(ROOT / "wave_k133_curves.json"), "V_rev_3d_z15"),
            ("K133_rev_5d_z20",       str(ROOT / "wave_k133_curves.json"), "V_rev_5d_z20"),
        ],
    )
    for k, v in correlation_block.items():
        print(f"   {k:24s} {v}")

    # ----------------------------------------------- save
    out_path = ROOT / "wave_k157_fypge_xs.json"
    curves_path = ROOT / "wave_k157_curves.json"

    # Strip internal series
    summary = {}
    for name, v in results.items():
        slim = {kk: vv for kk, vv in v.items()
                if kk not in ("equity_curve", "equity_idx", "_rets_series")}
        summary[name] = slim
    summary["_correlation_with_existing"] = correlation_block
    summary["_meta"] = {
        "wave": "K157",
        "wall_seconds": time.time() - t0,
        "n_symbols": int(fr_panel.shape[1]),
        "symbols": list(fr_panel.columns),
        "n_events": int(fr_panel.shape[0]),
        "n_perm": N_PERM,
        "n_boot": N_BOOT,
        "n_trials_dsr": N_TRIALS_DSR,
        "is_frac": IS_FRAC,
        "cost_bps_per_leg": COST_BPS,
        "fund_lookback_events": FUND_LOOKBACK_EVENTS,
        "vol_median_lookback_4h_bars": VOL_MEDIAN_LOOKBACK_4H,
        "metric_source": "1Token / Bybit institutional FYpGE",
        "metric": "FYpGE = cum_funding_7d * 100 / (30d_med_daily_qvol / 3)",
        "primary_variant": "V_top3_h7",
        "fypge_summary_pct": {
            "mean": float(fypge.stack().mean()),
            "std": float(fypge.stack().std()),
            "p05": float(fypge.stack().quantile(0.05)),
            "p50": float(fypge.stack().quantile(0.50)),
            "p95": float(fypge.stack().quantile(0.95)),
        },
    }

    curves = {name: {"equity_curve": v["equity_curve"],
                     "equity_idx": v["equity_idx"]}
              for name, v in results.items()}

    with open(out_path, "w") as f:
        json.dump(summary, f, indent=2, default=str)
    with open(curves_path, "w") as f:
        json.dump(curves, f, indent=2, default=str)

    elapsed = time.time() - t0
    print(f"\nDone in {elapsed:.1f}s")
    print(f"  -> {out_path}")
    print(f"  -> {curves_path}")

    # Console summary
    print("\n=== K157 FYpGE Summary ===")
    for name, r in results.items():
        full, oos = r["full"], r["oos"]
        perm = r["permutation"]
        dec = r["decomposition"]
        g = r["gates"]
        print(f"{name:14s} netSR={full['sharpe']:+.2f} OOS={oos['sharpe']:+.2f} "
              f"grossSR={r['gross_sharpe']:+.2f} MaxDD={full['max_dd']:.2%} "
              f"p={perm['p_value']:.3f} "
              f"price={dec['price_pnl']:+.3f} fund={dec['fund_pnl']:+.3f} "
              f"cost={dec['cost']:.3f} DSR_oos={r['dsr_oos']:.3f} gates={g['pass_count']}/6")


if __name__ == "__main__":
    main()

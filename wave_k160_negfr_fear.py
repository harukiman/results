"""
Wave K160 — Negative Funding-Rate + Extreme-Fear Contrarian LONG (R6-7)

Hypothesis (Spotedcrypto):
  When funding rate < -0.01% (negative)  AND  F&G index < 20 (extreme fear):
    - crowded SHORT positioning + retail capitulation = bottom signal
    - enter LONG basket, hold 1-3 days, profit from squeeze

Data:
  FR cache     : cache/bybit_fr_{SYM}USDT_730d.parquet (8h cadence)
  Price        : cache/{SYM}USDT_4h_730d.parquet (4h)
  F&G          : alternative.me /fng/?limit=2000 (daily)

Method (pre-registered):
  1. Fetch F&G daily history.
  2. Lag F&G by 1 day (yesterday's reading; no look-ahead).
  3. Reindex FR (8h) and F&G (daily) to 4H bars, forward-fill.
  4. Per symbol per 4H bar t: signal_t = (bybit_fr_lag1 < THR_FR) AND (fng_lag1 < THR_FNG)
  5. When signal True at close of bar t-1 → enter LONG at bar t open, hold H bars.
  6. Equal-weight basket across symbols that fire.
  7. Costs: 7 bp per side (14 bp roundtrip).

Variants:
  V_strict   : FR<-0.01%   F&G<20  hold=18 bars (3d)   (PRIMARY)
  V_loose_fr : FR<-0.005%  F&G<25  hold=18 bars (3d)
  V_strict_5d: FR<-0.01%   F&G<20  hold=30 bars (5d)
  V_btc_only : BTCUSDT only — FR<-0.01% F&G<20 hold=18 bars

Stats:
  730d, IS/OOS 70/30 split (by time)
  Walk-forward 4 folds (OOS-SR per fold)
  Permutation: shuffle F&G time-series n=300
  Block bootstrap CI on OOS Sharpe n=300 (block=6 bars = 1d)
  DSR N_trials=4
  Cost stress ±50%
  Per-symbol decomposition

§6 mini-gates:
  OOS_SR ≥ 0.5, p_perm < 0.05, MaxDD > -0.40,
  cost-stress robust, DSR_oos > 0.5, price_dominant.
"""

import json
import time
import urllib.request
import warnings
from pathlib import Path

import numpy as np
import pandas as pd

warnings.filterwarnings("ignore")

ROOT = Path("/Users/nekonaomichi/crypto-lab")
CACHE = ROOT / "cache"

# 15-symbol Bybit FR universe (intersect with 4h_730d price + bybit_fr_730d)
SYMBOLS = [
    "BTC", "ETH", "SOL", "XRP", "DOGE",
    "AVAX", "ADA", "LINK", "BNB", "DOT",
    "SUI", "APT", "NEAR", "ARB", "OP",
]

COST_BPS = 7.0          # per side (each entry, each exit)
IS_FRAC = 0.70
SEED = 20260524
BARS_PER_DAY = 6        # 4h bars per day
ANN_FACTOR_BAR = np.sqrt(365.25 * BARS_PER_DAY)
N_TRIALS_DSR = 4
FNG_URL = "https://api.alternative.me/fng/?limit=2000"
FNG_CACHE = CACHE / "fng_alternative_me.parquet"


# =====================================================================
#                         DATA LOADING
# =====================================================================
def fetch_fng(force_refresh=False):
    """Fetch full F&G history from alternative.me and cache as parquet.
    Returns a daily Series indexed by date (UTC midnight) of int values 0..100.
    """
    if FNG_CACHE.exists() and not force_refresh:
        try:
            df = pd.read_parquet(FNG_CACHE)
            df.index = pd.to_datetime(df.index)
            return df["value"].astype(float)
        except Exception:
            pass
    print(f"  fetching F&G from {FNG_URL} ...")
    req = urllib.request.Request(FNG_URL, headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(req, timeout=60) as r:
        data = json.loads(r.read())
    rows = []
    for d in data["data"]:
        ts = pd.to_datetime(int(d["timestamp"]), unit="s", utc=True).tz_convert(None)
        rows.append((ts.normalize(), int(d["value"]), d.get("value_classification", "")))
    df = pd.DataFrame(rows, columns=["date", "value", "classification"])
    df = df.sort_values("date").drop_duplicates(subset=["date"]).set_index("date")
    df.to_parquet(FNG_CACHE)
    return df["value"].astype(float)


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
    """Returns 4H-indexed panels for FR (ffill), F&G (ffill from daily, lag 1d),
    and price (close).  Lag is applied so that at bar t we use yesterday's F&G
    and the most recent FR strictly before t (the 8h cadence aligns at 0/4/8/12/16/20).
    """
    fng_daily = fetch_fng()

    fr_dict, px_dict = {}, {}
    for s in SYMBOLS:
        fr = load_fr(s)
        px = load_px(s)
        if fr is None or px is None:
            print(f"  skip {s} (fr={fr is not None}, px={px is not None})")
            continue
        fr_dict[s] = fr
        px_dict[s] = px

    px_panel = pd.concat(px_dict.values(), axis=1).sort_index()
    px_panel = px_panel.dropna(thresh=int(px_panel.shape[1] * 0.7))

    # Use 4H bars as master index
    bar_index = px_panel.index

    # FR: 8h cadence → reindex to 4H bars, ffill. Then shift by 1 bar so that
    # at bar t we use FR known at bar t-1 close (no look-ahead).
    fr_panel = pd.concat([fr_dict[s].reindex(bar_index, method="ffill")
                          for s in px_panel.columns], axis=1)
    fr_panel.columns = px_panel.columns
    fr_panel = fr_panel.shift(1)

    # F&G: daily → reindex to 4H bars, ffill. Then shift 1 day = 6 bars
    # so that at bar t we use F&G from yesterday's reading.
    fng_bar = fng_daily.reindex(bar_index, method="ffill")
    fng_bar = fng_bar.shift(BARS_PER_DAY)

    return fr_panel, px_panel, fng_bar, fng_daily


# =====================================================================
#                          SIGNAL & BACKTEST
# =====================================================================
def build_signal_panel(fr_panel, fng_bar, thr_fr, thr_fng):
    """signal[t, sym] = (fr[t, sym] < thr_fr) AND (fng[t] < thr_fng)
    where fr and fng are already lagged for no look-ahead.
    """
    fng_arr = fng_bar.values[:, None]  # (T, 1)
    fr_arr = fr_panel.values           # (T, N)
    sig = (fr_arr < thr_fr) & (fng_arr < thr_fng)
    sig = sig & np.isfinite(fr_arr) & np.isfinite(fng_arr)
    return pd.DataFrame(sig, index=fr_panel.index, columns=fr_panel.columns)


def backtest_basket(px_panel, sig_panel, hold_bars, cost_bps=COST_BPS,
                    symbols_subset=None):
    """Equal-weight basket LONG.

    State per symbol:
      - if not in position and signal[t-1]==True (already lagged): enter at close[t-1]
        and hold for hold_bars bars; close at close[t-1+hold].
      - if in position: keep until bar-counter expires.
      - Position size = 1.0 per symbol while in position. Portfolio return at
        bar t is the average per-bar return across all symbols currently in
        position (i.e. equal-weight basket; if no positions, return 0).
      - Cost: 2 * (cost_bps/1e4) charged at the entry bar (round-trip) and
        amortized across hold_bars? — Instead, charge entry cost at entry bar
        and exit cost at exit bar so equity reflects them at the right time.

    Returns Series indexed by bar timestamp.
    """
    if symbols_subset is not None:
        px = px_panel[symbols_subset]
        sig = sig_panel[symbols_subset]
    else:
        px = px_panel
        sig = sig_panel

    px_arr = px.values.astype(float)
    sig_arr = sig.values.astype(bool)
    T, N = px_arr.shape

    in_pos = np.zeros(N, dtype=bool)
    age = np.zeros(N, dtype=int)
    n_trades = 0
    long_count = np.zeros(N, dtype=int)
    rets = np.zeros(T)
    gross_rets = np.zeros(T)
    cost_arr = np.zeros(T)
    nactive_arr = np.zeros(T, dtype=int)
    trade_log = []  # (sym_idx, entry_bar, exit_bar, ret_gross)

    # per-bar log return
    with np.errstate(invalid="ignore", divide="ignore"):
        lr = np.zeros_like(px_arr)
        lr[1:] = np.log(px_arr[1:] / px_arr[:-1])
    lr = np.where(np.isfinite(lr), lr, 0.0)

    for t in range(1, T):
        # 1) Identify which positions are active during bar t (using state from t-1)
        active = in_pos.copy()
        nactive = int(active.sum())
        nactive_arr[t] = nactive

        # 2) Gross return for bar t = mean over currently active symbols
        if nactive > 0:
            mean_lr = float(lr[t, active].mean())
            gross_rets[t] = np.expm1(mean_lr)
        else:
            gross_rets[t] = 0.0

        # 3) Increment age for active; close those whose age reached hold_bars
        new_in_pos = in_pos.copy()
        n_closed = 0
        for i in range(N):
            if in_pos[i]:
                age[i] += 1
                if age[i] >= hold_bars:
                    new_in_pos[i] = False
                    age[i] = 0
                    n_closed += 1
        in_pos = new_in_pos

        # 4) Open new positions on signals fired at t-1 (sig already lag-safe)
        n_opened = 0
        sig_row = sig_arr[t - 1]
        for i in range(N):
            if sig_row[i] and not in_pos[i] and np.isfinite(px_arr[t, i]):
                in_pos[i] = True
                age[i] = 1  # entered at start of bar t; consumes 1 bar
                n_opened += 1
                n_trades += 1
                long_count[i] += 1

        # 5) Costs: 7 bp on each side. Average across active weights.
        #    Active size scales with nactive (each position contributes 1/N_active to basket).
        #    For book-keeping: when a position opens or closes, the basket
        #    weight allocated to it changes — for simplicity use turnover-based:
        #    cost_bar = cost_bps * (n_opened + n_closed) / max(nactive_post, 1)
        nactive_post = int(in_pos.sum())
        denom = max(nactive_post, nactive, 1)
        cost_bar = (cost_bps / 1e4) * (n_opened + n_closed) / denom
        cost_arr[t] = cost_bar

        rets[t] = gross_rets[t] - cost_bar

    return {
        "rets": pd.Series(rets, index=px.index),
        "gross_rets": pd.Series(gross_rets, index=px.index),
        "cost": pd.Series(cost_arr, index=px.index),
        "nactive": pd.Series(nactive_arr, index=px.index),
        "long_count": pd.Series(long_count, index=px.columns),
        "n_trades": int(n_trades),
        "n_periods": int(T),
    }


# =====================================================================
#                             STATS
# =====================================================================
def perf_stats(rets, ann_factor=ANN_FACTOR_BAR):
    rets = pd.Series(rets).dropna()
    if len(rets) < 5 or rets.std() == 0:
        return dict(sharpe=0.0, sortino=0.0, calmar=0.0, max_dd=0.0,
                    win_rate=0.0, ann_ret=0.0, ann_vol=0.0, n=int(len(rets)))
    mu = rets.mean()
    sd = rets.std()
    sharpe = mu / sd * ann_factor
    downside = rets[rets < 0].std()
    sortino = mu / downside * ann_factor if downside and downside > 0 else 0.0
    equity = (1 + rets).cumprod()
    peak = equity.cummax()
    dd = float((equity / peak - 1).min())
    # annualised return via compounding
    ann_ret = float((1 + mu) ** (ann_factor ** 2) - 1)
    calmar = ann_ret / abs(dd) if dd < 0 else 0.0
    return dict(
        sharpe=float(sharpe), sortino=float(sortino), calmar=float(calmar),
        max_dd=float(dd), win_rate=float((rets > 0).mean()),
        ann_ret=float(ann_ret), ann_vol=float(sd * ann_factor),
        n=int(len(rets)),
    )


def deflated_sharpe(sr, n_obs, n_trials, skew=0.0, kurt=3.0):
    if n_obs < 20 or n_trials < 1:
        return 0.0
    emc = 0.5772
    e_max = (np.sqrt(2 * np.log(max(n_trials, 2))) * (1 - emc)
             + (1 - emc) / np.sqrt(2 * np.log(max(n_trials, 2))))
    var = (1 - skew * sr + (kurt - 1) / 4.0 * sr ** 2) / (n_obs - 1)
    if var <= 0:
        return 0.0
    z = (sr - e_max) / np.sqrt(var)
    from math import erf, sqrt
    return 0.5 * (1 + erf(z / sqrt(2)))


def block_bootstrap_ci(rets, ann_factor=ANN_FACTOR_BAR,
                       n_iter=300, block=6, seed=SEED):
    rets = np.asarray(rets)
    n = len(rets)
    if n < block * 3:
        return {"sr_lo": 0.0, "sr_hi": 0.0, "sr_mean": 0.0}
    rng = np.random.default_rng(seed)
    n_blocks = max(1, n // block)
    out = []
    for _ in range(n_iter):
        starts = rng.integers(0, n - block + 1, size=n_blocks)
        sample = np.concatenate([rets[s:s + block] for s in starts])
        s = sample.std()
        if s > 0:
            out.append(sample.mean() / s * ann_factor)
    if not out:
        return {"sr_lo": 0.0, "sr_hi": 0.0, "sr_mean": 0.0}
    arr = np.array(out)
    return {"sr_lo": float(np.quantile(arr, 0.025)),
            "sr_hi": float(np.quantile(arr, 0.975)),
            "sr_mean": float(arr.mean())}


def permutation_test(px_panel, fng_bar, fr_panel, cfg, n_iter=300, seed=SEED):
    """Shuffle the F&G time series (block permutation) to break correlation
    between F&G regime and forward returns while keeping FR & price intact.
    Tests whether the F&G filter adds genuine information."""
    rng = np.random.default_rng(seed)

    actual_sig = build_signal_panel(fr_panel, fng_bar, cfg["thr_fr"], cfg["thr_fng"])
    actual_res = backtest_basket(px_panel, actual_sig, cfg["hold_bars"],
                                  symbols_subset=cfg.get("symbols"))
    actual_sr = perf_stats(actual_res["rets"])["sharpe"]
    actual_sr_g = perf_stats(actual_res["gross_rets"])["sharpe"]

    base = fng_bar.values.copy()
    n = len(base)
    block = BARS_PER_DAY * 7  # 1-week blocks
    n_blocks = max(1, n // block)

    null_sr = np.zeros(n_iter)
    null_sr_g = np.zeros(n_iter)
    for k in range(n_iter):
        # circular block permutation
        block_starts = rng.integers(0, n - block + 1, size=n_blocks)
        perm = np.concatenate([base[s:s + block] for s in block_starts])
        # pad to length n
        if len(perm) < n:
            perm = np.concatenate([perm, base[:n - len(perm)]])
        else:
            perm = perm[:n]
        fng_perm = pd.Series(perm, index=fng_bar.index)
        sig = build_signal_panel(fr_panel, fng_perm, cfg["thr_fr"], cfg["thr_fng"])
        res = backtest_basket(px_panel, sig, cfg["hold_bars"],
                              symbols_subset=cfg.get("symbols"))
        null_sr[k] = perf_stats(res["rets"])["sharpe"]
        null_sr_g[k] = perf_stats(res["gross_rets"])["sharpe"]

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


def walk_forward(px_panel, fng_bar, fr_panel, cfg, n_folds=4):
    T = len(px_panel)
    fold_size = T // n_folds
    out = []
    for f in range(n_folds):
        s = f * fold_size
        e = (f + 1) * fold_size if f < n_folds - 1 else T
        sub_px = px_panel.iloc[s:e]
        sub_fr = fr_panel.iloc[s:e]
        sub_fng = fng_bar.iloc[s:e]
        sig = build_signal_panel(sub_fr, sub_fng, cfg["thr_fr"], cfg["thr_fng"])
        try:
            r = backtest_basket(sub_px, sig, cfg["hold_bars"],
                                symbols_subset=cfg.get("symbols"))["rets"]
        except Exception:
            r = pd.Series(dtype=float)
        out.append({"fold": f, **perf_stats(r)})
    return out


# =====================================================================
#                         VARIANT DRIVER
# =====================================================================
VARIANTS = {
    "V_strict":    dict(thr_fr=-1e-4,  thr_fng=20, hold_bars=18, symbols=None),  # PRIMARY
    "V_loose_fr":  dict(thr_fr=-5e-5,  thr_fng=25, hold_bars=18, symbols=None),
    "V_strict_5d": dict(thr_fr=-1e-4,  thr_fng=20, hold_bars=30, symbols=None),
    "V_btc_only":  dict(thr_fr=-1e-4,  thr_fng=20, hold_bars=18, symbols=["BTC"]),
}


def run_variant(name, cfg, px_panel, fng_bar, fr_panel, n_perm=300, n_boot=300):
    sub = cfg.get("symbols")
    print(f"  >> {name}: thr_fr={cfg['thr_fr']:.2e} thr_fng<{cfg['thr_fng']} "
          f"hold={cfg['hold_bars']}bars sym={'ALL' if sub is None else sub}")

    sig = build_signal_panel(fr_panel, fng_bar, cfg["thr_fr"], cfg["thr_fng"])
    res = backtest_basket(px_panel, sig, cfg["hold_bars"], symbols_subset=sub)

    rets = res["rets"]
    n_total = len(rets)
    n_is = int(n_total * IS_FRAC)

    full_stats = perf_stats(rets)
    is_stats = perf_stats(rets.iloc[:n_is])
    oos_stats = perf_stats(rets.iloc[n_is:])
    gross_sr = perf_stats(res["gross_rets"])["sharpe"]

    # Signal frequency diagnostics
    sig_frac = float(sig.values.mean()) if sub is None else float(sig[sub].values.mean())
    n_sig_bars = int(sig.values.sum()) if sub is None else int(sig[sub].values.sum())

    wf = walk_forward(px_panel, fng_bar, fr_panel, cfg, n_folds=4)

    # Cost stress
    res_lo = backtest_basket(px_panel, sig, cfg["hold_bars"],
                             cost_bps=COST_BPS * 0.5, symbols_subset=sub)
    res_hi = backtest_basket(px_panel, sig, cfg["hold_bars"],
                             cost_bps=COST_BPS * 1.5, symbols_subset=sub)
    cost_stress = {
        "low_50pct":   perf_stats(res_lo["rets"])["sharpe"],
        "base_100pct": full_stats["sharpe"],
        "high_150pct": perf_stats(res_hi["rets"])["sharpe"],
    }

    boot = block_bootstrap_ci(rets.iloc[n_is:].values,
                               n_iter=n_boot, block=BARS_PER_DAY, seed=SEED + 11)
    perm = permutation_test(px_panel, fng_bar, fr_panel, cfg, n_iter=n_perm)

    dsr_full = deflated_sharpe(full_stats["sharpe"], full_stats["n"], N_TRIALS_DSR)
    dsr_oos = deflated_sharpe(oos_stats["sharpe"], oos_stats["n"], N_TRIALS_DSR)

    long_count = res["long_count"].sort_values(ascending=False).to_dict()

    # Decomposition: this strat is LONG-only price PnL; "fund_pnl" is implicit
    # because longs RECEIVE negative funding rate (we don't book it explicitly
    # in 4H bars — pricing of FR earnings would require 8h schedule; included
    # as separate diagnostic below).
    price_total = float(res["gross_rets"].sum())
    cost_total = float(res["cost"].sum())
    net_total = float(res["rets"].sum())

    # Estimate funding income: average FR while in pos × n_active_bars
    # (rough: positions are long, FR<0 ⇒ longs receive |FR| each 8h event).
    # Per 4H bar a long receives FR/2 if held for half an 8h window. Simple
    # accounting: sum (avg fr per bar × indicator-of-position × bar-fraction-of-8h)
    fr_arr = fr_panel.values
    if sub is None:
        active_cols = list(range(fr_panel.shape[1]))
    else:
        active_cols = [px_panel.columns.get_loc(s) for s in sub]
    # Reconstruct in_pos over time
    # For diagnostic only — approximate via signal-shifted (entry → hold)
    sig_arr = sig.values
    in_pos_log = np.zeros_like(sig_arr, dtype=bool)
    for j in active_cols:
        age = 0
        for t in range(1, sig_arr.shape[0]):
            if in_pos_log[t - 1, j]:
                age += 1
                if age < cfg["hold_bars"]:
                    in_pos_log[t, j] = True
                else:
                    age = 0
            if not in_pos_log[t, j] and sig_arr[t - 1, j]:
                in_pos_log[t, j] = True
                age = 1
    fr_when_long = np.where(in_pos_log, fr_arr, 0.0)
    # Long receives -FR per 8h event; 1 bar = 4h = half an 8h cycle ⇒ multiply 0.5
    fund_pnl_per_active = -np.nansum(fr_when_long) * 0.5
    # normalize by mean basket size (approx avg n_active)
    avg_active = float(res["nactive"].mean()) if float(res["nactive"].mean()) > 0 else 1.0
    fund_total = float(fund_pnl_per_active / max(avg_active, 1.0))

    abs_sum = abs(price_total) + abs(fund_total) + 1e-9
    decomp = {
        "price_pnl": price_total,
        "fund_pnl_est": fund_total,
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
    gates["pass_count"] = int(sum(1 for k, v in gates.items() if v is True))
    gates["all_pass"] = bool(all(v for k, v in gates.items()
                                  if k not in ("pass_count", "all_pass")))

    return {
        "config": cfg,
        "n_periods": n_total,
        "n_trades": res["n_trades"],
        "n_signal_bars": n_sig_bars,
        "signal_freq": sig_frac,
        "avg_basket_size": float(res["nactive"].mean()),
        "avg_basket_when_active": float(res["nactive"][res["nactive"] > 0].mean())
                                  if (res["nactive"] > 0).any() else 0.0,
        "full": full_stats,
        "is": is_stats,
        "oos": oos_stats,
        "gross_sharpe": float(gross_sr),
        "decomposition": decomp,
        "walk_forward": wf,
        "cost_stress": cost_stress,
        "bootstrap_oos_sharpe_95ci": boot,
        "permutation": perm,
        "dsr_full": dsr_full,
        "dsr_oos": dsr_oos,
        "long_count": long_count,
        "gates": gates,
        "equity_curve": (1 + rets).cumprod().tolist(),
        "equity_idx": [str(x) for x in rets.index],
        "rets_series": rets.tolist(),
    }


# =====================================================================
#                              MAIN
# =====================================================================
def main():
    t0 = time.time()
    print("Loading panels ...")
    fr_panel, px_panel, fng_bar, fng_daily = build_panels()
    print(f"  px panel: {px_panel.shape} {px_panel.index.min()} .. {px_panel.index.max()}")
    print(f"  Symbols ({px_panel.shape[1]}): {list(px_panel.columns)}")
    print(f"  FR panel (lag1): {fr_panel.shape}, non-null frac: "
          f"{float(fr_panel.notna().mean().mean()):.3f}")
    print(f"  F&G daily: {len(fng_daily)} entries  "
          f"({fng_daily.index.min().date()} .. {fng_daily.index.max().date()})  "
          f"min={fng_daily.min():.0f} max={fng_daily.max():.0f}")
    print(f"  F&G bar series: {fng_bar.shape}  "
          f"frac<20={(fng_bar < 20).mean():.4f}  frac<25={(fng_bar < 25).mean():.4f}")
    print(f"  FR signal density: frac(fr<-1e-4)={(fr_panel.values < -1e-4).mean():.4f}  "
          f"frac(fr<-5e-5)={(fr_panel.values < -5e-5).mean():.4f}")

    n_perm = 300
    n_boot = 300

    results = {}
    for name, cfg in VARIANTS.items():
        results[name] = run_variant(name, cfg, px_panel, fng_bar, fr_panel,
                                     n_perm=n_perm, n_boot=n_boot)
        print(f"     [elapsed {time.time() - t0:.1f}s]")

    out_path = ROOT / "wave_k160_negfr_fear.json"
    curves_path = ROOT / "wave_k160_curves.json"

    summary = {k: {kk: vv for kk, vv in v.items()
                   if kk not in ("equity_curve", "equity_idx", "rets_series")}
               for k, v in results.items()}
    summary["_fng_data_meta"] = {
        "source": FNG_URL,
        "first_date": str(fng_daily.index.min().date()),
        "last_date": str(fng_daily.index.max().date()),
        "n_days": int(len(fng_daily)),
        "value_range": [int(fng_daily.min()), int(fng_daily.max())],
        "mean": float(fng_daily.mean()),
        "frac_lt_20_all_history": float((fng_daily < 20).mean()),
        "frac_lt_25_all_history": float((fng_daily < 25).mean()),
        "frac_lt_20_in_window": float((fng_bar < 20).mean()),
    }
    summary["_meta"] = {
        "wall_seconds": time.time() - t0,
        "n_symbols": int(px_panel.shape[1]),
        "symbols": list(px_panel.columns),
        "n_bars": int(px_panel.shape[0]),
        "n_perm": n_perm,
        "n_boot": n_boot,
        "n_trials_dsr": N_TRIALS_DSR,
        "is_frac": IS_FRAC,
        "cost_bps_per_side": COST_BPS,
        "bars_per_day": BARS_PER_DAY,
        "ann_factor_bar": float(ANN_FACTOR_BAR),
        "wave": "K160",
        "source": "Spotedcrypto R6-7 — Negative FR + Extreme Fear contrarian LONG",
        "signal_logic": "(bybit_fr_lag1 < THR_FR) AND (fng_lag1day < THR_FNG) -> LONG hold H bars",
        "permutation_method": "1-week block circular shuffle of F&G time series",
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

    print("\n=== Summary (NEG-FR + EXTREME-FEAR LONG) ===")
    for name, r in results.items():
        full, oos = r["full"], r["oos"]
        perm = r["permutation"]
        g = r["gates"]
        print(f"{name:14s} netSR={full['sharpe']:+.2f}  OOS={oos['sharpe']:+.2f}  "
              f"grossSR={r['gross_sharpe']:+.2f}  MaxDD={full['max_dd']:+.2%}  "
              f"p={perm['p_value_net']:.3f}  trades={r['n_trades']}  "
              f"DSR_oos={r['dsr_oos']:.2f}  gates={g['pass_count']}/6")


if __name__ == "__main__":
    main()

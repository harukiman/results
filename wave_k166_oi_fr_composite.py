"""
Wave K166 — OI-Weighted FR Composite (R6-4 XT-exchange framework)
==================================================================

Hypothesis (XT Medium / R6-4)
  "OI rising + FR positive" 1-2 days before breakout  →  LONG signal
  "OI falling + FR neutral" => drainage                →  FADE (short)

Pre-registered Method
  Per 8h funding event timestamp:
    fr_now    = Bybit funding rate (cache, 8h cadence)
    oi_proxy  = rolling 7d volume / rolling 30d volume  (volume momentum)
    oi_delta  = oi_proxy - 1   (positive = OI/volume rising)

  Signals:
    LONG  : oi_delta > +oi_thr  AND  fr > +fr_thr_bp / 1e4
    FADE  : oi_delta < -oi_thr  AND  |fr| < fr_neutral_bp / 1e4   → SHORT

  Hold: 2 days (= 6 × 8h events = 12 × 4H bars)
  Cost: 7 bp per side (14 bp roundtrip)

Variants (all pre-registered)
  V_primary    : oi_thr=+0.20, fr_thr_bp=+0.5, fr_neutral_bp=0.5, both sides
  V_loose      : oi_thr=+0.10, fr_thr_bp=+0.3, fr_neutral_bp=0.3, both sides
  V_strict     : oi_thr=+0.30, fr_thr_bp=+1.0, fr_neutral_bp=1.0, both sides
  V_long_only  : primary thresholds, LONG side only

DATA HONESTY
------------
Real Bybit OI is not cached for 730d (Bybit OI API limited to 200 records
~ recent only).  We substitute volume momentum (7d/30d quote_volume ratio)
as the OI-proxy.  Economic rationale: in a leveraged-derivative venue, sustained
turnover expansion at flat-or-rising price typically tracks open-interest growth
(longs being added), while turnover collapse tracks liquidation / OI bleed.
This proxy is imperfect (it mixes spot-like vs leverage flow) but is the only
730d-history proxy available without paid Glassnode-tier data.  Labelled
throughout.

Audit (per §6)
  730d window, IS/OOS 70/30 (chronological)
  Walk-forward 4 folds
  Permutation n=200 (block-shuffle FR series, keep OI-proxy & price intact)
  Block bootstrap n=200 on OOS Sharpe (1d blocks)
  Deflated Sharpe with N_trials = 4
  Cost stress ×0.5 / ×1.5
  Decomposition (price PnL vs funding PnL vs cost)

§6 Mini-gates
  OOS_SR ≥ 0.5, p_perm < 0.05, MaxDD > -0.40,
  cost-stress robust, DSR_oos > 0.5, price_dominant.
"""

from __future__ import annotations

import json
import time
import warnings
from pathlib import Path

import numpy as np
import pandas as pd

warnings.filterwarnings("ignore")

ROOT = Path("/Users/nekonaomichi/crypto-lab")
CACHE = ROOT / "cache"

# 15 Bybit-FR universe (same as K160, intersect with 4h_730d price)
SYMBOLS = [
    "BTC", "ETH", "SOL", "XRP", "DOGE",
    "AVAX", "ADA", "LINK", "BNB", "DOT",
    "SUI", "APT", "NEAR", "ARB", "OP",
]

COST_BPS = 7.0           # per side
IS_FRAC = 0.70
SEED = 20260524
BARS_PER_DAY = 6         # 4h bars
ANN_FACTOR_BAR = np.sqrt(365.25 * BARS_PER_DAY)
N_TRIALS_DSR = 4
HOLD_BARS_DEFAULT = 12   # 2 days = 12 × 4H bars
VOL_FAST_DAYS = 7        # numerator window for oi_proxy
VOL_SLOW_DAYS = 30       # denominator window


# =====================================================================
#                         DATA LOADING
# =====================================================================
def load_fr(sym: str) -> pd.Series | None:
    p = CACHE / f"bybit_fr_{sym}USDT_730d.parquet"
    if not p.exists():
        return None
    df = pd.read_parquet(p)
    df["timestamp"] = pd.to_datetime(df["timestamp"])
    df = df.set_index("timestamp").sort_index()
    df = df[~df.index.duplicated(keep="last")]
    return df["funding_rate"].astype(float).rename(sym)


def load_px(sym: str) -> pd.DataFrame | None:
    p = CACHE / f"{sym}USDT_4h_730d.parquet"
    if not p.exists():
        return None
    df = pd.read_parquet(p)
    df["open_time"] = pd.to_datetime(df["open_time"])
    df = df.set_index("open_time").sort_index()
    df = df[~df.index.duplicated(keep="last")]
    return df[["close", "quote_volume"]].astype(float)


def build_panels() -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    """Returns (price_panel, oi_proxy_panel, fr_panel) on 4H index, lag-safe."""
    px_dict, vol_dict, fr_dict = {}, {}, {}
    for s in SYMBOLS:
        px = load_px(s)
        fr = load_fr(s)
        if px is None or fr is None:
            print(f"  skip {s} (px={px is not None}, fr={fr is not None})")
            continue
        px_dict[s] = px["close"].rename(s)
        vol_dict[s] = px["quote_volume"].rename(s)
        fr_dict[s] = fr

    px_panel = pd.concat(px_dict.values(), axis=1).sort_index()
    px_panel = px_panel.dropna(thresh=int(px_panel.shape[1] * 0.7))
    bar_index = px_panel.index

    vol_panel = pd.concat([vol_dict[s].reindex(bar_index)
                           for s in px_panel.columns], axis=1)
    vol_panel.columns = px_panel.columns

    # OI proxy: rolling daily-sum of 4H quote_volume, then 7d/30d ratio
    fast_bars = BARS_PER_DAY * VOL_FAST_DAYS
    slow_bars = BARS_PER_DAY * VOL_SLOW_DAYS
    vol_fast = vol_panel.rolling(fast_bars, min_periods=fast_bars // 2).mean()
    vol_slow = vol_panel.rolling(slow_bars, min_periods=slow_bars // 2).mean()
    oi_proxy = (vol_fast / vol_slow).replace([np.inf, -np.inf], np.nan)

    # FR (8h) → 4H ffill
    fr_panel = pd.concat([fr_dict[s].reindex(bar_index, method="ffill")
                          for s in px_panel.columns], axis=1)
    fr_panel.columns = px_panel.columns

    # Lag both signals by 1 bar to enforce no look-ahead (use info known at t-1
    # close to enter at bar t open).
    oi_proxy = oi_proxy.shift(1)
    fr_panel = fr_panel.shift(1)

    return px_panel, oi_proxy, fr_panel


# =====================================================================
#                         SIGNAL & BACKTEST
# =====================================================================
def build_signal_panel(oi_proxy: pd.DataFrame,
                       fr_panel: pd.DataFrame,
                       cfg: dict) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Returns (long_sig, short_sig).  Both panels are bool (T, N).

    LONG  : oi_delta > +oi_thr AND fr > +fr_long_bp/1e4
    SHORT : oi_delta < -oi_thr AND |fr| < fr_neut_bp/1e4
    """
    oi_delta = oi_proxy.values - 1.0
    fr_arr = fr_panel.values

    long_sig = ((oi_delta > +cfg["oi_thr"]) &
                (fr_arr > +cfg["fr_long_bp"] / 1e4) &
                np.isfinite(oi_delta) & np.isfinite(fr_arr))

    if cfg.get("long_only", False):
        short_sig = np.zeros_like(long_sig, dtype=bool)
    else:
        short_sig = ((oi_delta < -cfg["oi_thr"]) &
                     (np.abs(fr_arr) < cfg["fr_neut_bp"] / 1e4) &
                     np.isfinite(oi_delta) & np.isfinite(fr_arr))

    long_df = pd.DataFrame(long_sig, index=oi_proxy.index, columns=oi_proxy.columns)
    short_df = pd.DataFrame(short_sig, index=oi_proxy.index, columns=oi_proxy.columns)
    return long_df, short_df


def backtest_long_short(px_panel: pd.DataFrame,
                        long_sig: pd.DataFrame,
                        short_sig: pd.DataFrame,
                        fr_panel: pd.DataFrame,
                        hold_bars: int,
                        cost_bps: float = COST_BPS):
    """Equal-weight basket, LONG and SHORT positions per symbol.

    State per symbol:
      - if not in pos and long_sig[t-1] → enter LONG at bar t, hold hold_bars.
      - if not in pos and short_sig[t-1] → enter SHORT at bar t, hold hold_bars.
      - long signal beats short if both fire (long signal evaluated first; per
        construction the thresholds make this mutually exclusive anyway).
    """
    px = px_panel
    px_arr = px.values.astype(float)
    fr_arr = fr_panel.values.astype(float)
    long_arr = long_sig.values.astype(bool)
    short_arr = short_sig.values.astype(bool)
    T, N = px_arr.shape

    side = np.zeros(N, dtype=np.int8)   # +1 long, -1 short, 0 flat
    age = np.zeros(N, dtype=int)
    n_trades_long = 0
    n_trades_short = 0
    long_count = np.zeros(N, dtype=int)
    short_count = np.zeros(N, dtype=int)
    rets = np.zeros(T)
    gross_rets = np.zeros(T)
    fund_rets = np.zeros(T)        # funding accrual diagnostic
    cost_arr = np.zeros(T)
    nactive_arr = np.zeros(T, dtype=int)

    with np.errstate(invalid="ignore", divide="ignore"):
        lr = np.zeros_like(px_arr)
        lr[1:] = np.log(px_arr[1:] / px_arr[:-1])
    lr = np.where(np.isfinite(lr), lr, 0.0)

    for t in range(1, T):
        # active positions during bar t (state from t-1)
        active_mask = side != 0
        nactive = int(active_mask.sum())
        nactive_arr[t] = nactive

        # Gross bar return = signed mean over active legs
        if nactive > 0:
            sgn = side[active_mask].astype(float)
            mean_lr = float((sgn * lr[t, active_mask]).mean())
            gross_rets[t] = np.expm1(mean_lr)
        else:
            gross_rets[t] = 0.0

        # Funding accrual: longs PAY +FR, shorts RECEIVE +FR (per 8h event).
        # 4H bar ≈ 0.5 × 8h cycle → multiply by 0.5.
        if nactive > 0:
            fr_now = fr_arr[t]
            fr_signed = np.where(active_mask, -side.astype(float) * fr_now, 0.0)
            fund_rets[t] = float(fr_signed.sum() / max(nactive, 1) * 0.5)
        else:
            fund_rets[t] = 0.0

        # age increment + close
        n_closed = 0
        for i in range(N):
            if side[i] != 0:
                age[i] += 1
                if age[i] >= hold_bars:
                    side[i] = 0
                    age[i] = 0
                    n_closed += 1

        # open new positions on signals from t-1
        n_opened = 0
        for i in range(N):
            if side[i] == 0 and np.isfinite(px_arr[t, i]):
                if long_arr[t - 1, i]:
                    side[i] = +1
                    age[i] = 1
                    n_opened += 1
                    n_trades_long += 1
                    long_count[i] += 1
                elif short_arr[t - 1, i]:
                    side[i] = -1
                    age[i] = 1
                    n_opened += 1
                    n_trades_short += 1
                    short_count[i] += 1

        # cost charged each transition (entry & exit)
        nactive_post = int((side != 0).sum())
        denom = max(nactive_post, nactive, 1)
        cost_bar = (cost_bps / 1e4) * (n_opened + n_closed) / denom
        cost_arr[t] = cost_bar

        rets[t] = gross_rets[t] + fund_rets[t] - cost_bar

    return {
        "rets": pd.Series(rets, index=px.index),
        "gross_rets": pd.Series(gross_rets, index=px.index),
        "fund_rets": pd.Series(fund_rets, index=px.index),
        "cost": pd.Series(cost_arr, index=px.index),
        "nactive": pd.Series(nactive_arr, index=px.index),
        "long_count": pd.Series(long_count, index=px.columns),
        "short_count": pd.Series(short_count, index=px.columns),
        "n_trades_long": int(n_trades_long),
        "n_trades_short": int(n_trades_short),
        "n_trades": int(n_trades_long + n_trades_short),
        "n_periods": int(T),
    }


# =====================================================================
#                              STATS
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
                       n_iter=200, block=BARS_PER_DAY, seed=SEED):
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


def permutation_test(px_panel, oi_proxy, fr_panel, cfg,
                     n_iter=200, seed=SEED):
    """Block-permute the FR panel (rows = time, columns = symbols) to break
    correlation between FR regime and oi_proxy / forward returns while leaving
    oi_proxy & price intact. Tests whether the FR layer of the composite adds
    real information."""
    rng = np.random.default_rng(seed)

    # Actual
    long_sig, short_sig = build_signal_panel(oi_proxy, fr_panel, cfg)
    actual_res = backtest_long_short(px_panel, long_sig, short_sig,
                                      fr_panel, cfg["hold_bars"])
    actual_sr = perf_stats(actual_res["rets"])["sharpe"]
    actual_sr_g = perf_stats(actual_res["gross_rets"])["sharpe"]

    base = fr_panel.values.copy()
    T, N = base.shape
    block = BARS_PER_DAY * 7  # 1-week blocks
    n_blocks = max(1, T // block)

    null_sr = np.zeros(n_iter)
    null_sr_g = np.zeros(n_iter)
    for k in range(n_iter):
        starts = rng.integers(0, T - block + 1, size=n_blocks)
        perm = np.concatenate([base[s:s + block] for s in starts], axis=0)
        if perm.shape[0] < T:
            perm = np.concatenate([perm, base[:T - perm.shape[0]]], axis=0)
        else:
            perm = perm[:T]
        fr_perm = pd.DataFrame(perm, index=fr_panel.index, columns=fr_panel.columns)
        long_s, short_s = build_signal_panel(oi_proxy, fr_perm, cfg)
        res = backtest_long_short(px_panel, long_s, short_s,
                                   fr_perm, cfg["hold_bars"])
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


def walk_forward(px_panel, oi_proxy, fr_panel, cfg, n_folds=4):
    T = len(px_panel)
    fold_size = T // n_folds
    out = []
    for f in range(n_folds):
        s = f * fold_size
        e = (f + 1) * fold_size if f < n_folds - 1 else T
        sub_px = px_panel.iloc[s:e]
        sub_oi = oi_proxy.iloc[s:e]
        sub_fr = fr_panel.iloc[s:e]
        long_s, short_s = build_signal_panel(sub_oi, sub_fr, cfg)
        try:
            r = backtest_long_short(sub_px, long_s, short_s, sub_fr,
                                     cfg["hold_bars"])["rets"]
        except Exception:
            r = pd.Series(dtype=float)
        out.append({"fold": f, **perf_stats(r)})
    return out


# =====================================================================
#                         VARIANTS
# =====================================================================
VARIANTS = {
    "V_primary":   dict(oi_thr=0.20, fr_long_bp=0.5, fr_neut_bp=0.5,
                        hold_bars=HOLD_BARS_DEFAULT, long_only=False),
    "V_loose":     dict(oi_thr=0.10, fr_long_bp=0.3, fr_neut_bp=0.3,
                        hold_bars=HOLD_BARS_DEFAULT, long_only=False),
    "V_strict":    dict(oi_thr=0.30, fr_long_bp=1.0, fr_neut_bp=1.0,
                        hold_bars=HOLD_BARS_DEFAULT, long_only=False),
    "V_long_only": dict(oi_thr=0.20, fr_long_bp=0.5, fr_neut_bp=0.5,
                        hold_bars=HOLD_BARS_DEFAULT, long_only=True),
}


def run_variant(name, cfg, px_panel, oi_proxy, fr_panel,
                n_perm=200, n_boot=200):
    print(f"  >> {name}: oi±{cfg['oi_thr']} fr_long>{cfg['fr_long_bp']}bp "
          f"|fr_neut|<{cfg['fr_neut_bp']}bp hold={cfg['hold_bars']} "
          f"long_only={cfg['long_only']}")

    long_sig, short_sig = build_signal_panel(oi_proxy, fr_panel, cfg)
    res = backtest_long_short(px_panel, long_sig, short_sig, fr_panel,
                               cfg["hold_bars"])

    rets = res["rets"]
    n_total = len(rets)
    n_is = int(n_total * IS_FRAC)

    full_stats = perf_stats(rets)
    is_stats = perf_stats(rets.iloc[:n_is])
    oos_stats = perf_stats(rets.iloc[n_is:])
    gross_sr = perf_stats(res["gross_rets"])["sharpe"]

    sig_freq_long = float(long_sig.values.mean())
    sig_freq_short = float(short_sig.values.mean())
    n_sig_long = int(long_sig.values.sum())
    n_sig_short = int(short_sig.values.sum())

    wf = walk_forward(px_panel, oi_proxy, fr_panel, cfg, n_folds=4)

    # Cost stress
    res_lo = backtest_long_short(px_panel, long_sig, short_sig, fr_panel,
                                   cfg["hold_bars"], cost_bps=COST_BPS * 0.5)
    res_hi = backtest_long_short(px_panel, long_sig, short_sig, fr_panel,
                                   cfg["hold_bars"], cost_bps=COST_BPS * 1.5)
    cost_stress = {
        "low_50pct":   perf_stats(res_lo["rets"])["sharpe"],
        "base_100pct": full_stats["sharpe"],
        "high_150pct": perf_stats(res_hi["rets"])["sharpe"],
    }

    boot = block_bootstrap_ci(rets.iloc[n_is:].values,
                              n_iter=n_boot, block=BARS_PER_DAY, seed=SEED + 11)
    perm = permutation_test(px_panel, oi_proxy, fr_panel, cfg,
                            n_iter=n_perm, seed=SEED + 23)

    dsr_full = deflated_sharpe(full_stats["sharpe"], full_stats["n"], N_TRIALS_DSR)
    dsr_oos = deflated_sharpe(oos_stats["sharpe"], oos_stats["n"], N_TRIALS_DSR)

    price_total = float(res["gross_rets"].sum())
    fund_total = float(res["fund_rets"].sum())
    cost_total = float(res["cost"].sum())
    net_total = float(res["rets"].sum())
    abs_sum = abs(price_total) + abs(fund_total) + 1e-9
    decomp = {
        "price_pnl": price_total,
        "fund_pnl": fund_total,
        "cost": cost_total,
        "net": net_total,
        "price_pct_of_gross_abs": float(abs(price_total) / abs_sum),
        "fund_pct_of_gross_abs": float(abs(fund_total) / abs_sum),
        "price_dominant": bool(abs(price_total) > abs(fund_total) * 2),
        "price_same_sign_as_net": bool(
            np.sign(price_total) == np.sign(net_total) and net_total != 0
        ),
    }

    gates = {
        "oos_sr_ge_0_5":   bool(oos_stats["sharpe"] >= 0.5),
        "p_perm_lt_0_05":  bool(perm["p_value_net"] < 0.05),
        "max_dd_gt_neg40": bool(full_stats["max_dd"] > -0.40),
        "cost_stress_robust": bool(
            cost_stress["high_150pct"] >= 0.5 * cost_stress["base_100pct"]
            if cost_stress["base_100pct"] > 0 else False
        ),
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
        "n_trades_long": res["n_trades_long"],
        "n_trades_short": res["n_trades_short"],
        "n_signal_bars_long": n_sig_long,
        "n_signal_bars_short": n_sig_short,
        "signal_freq_long": sig_freq_long,
        "signal_freq_short": sig_freq_short,
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
        "long_count": res["long_count"].sort_values(ascending=False).to_dict(),
        "short_count": res["short_count"].sort_values(ascending=False).to_dict(),
        "gates": gates,
        "equity_curve": (1 + rets).cumprod().tolist(),
        "equity_idx": [str(x) for x in rets.index],
    }


# =====================================================================
#                               MAIN
# =====================================================================
def main():
    t0 = time.time()
    print("[K166] Loading panels...")
    px_panel, oi_proxy, fr_panel = build_panels()
    print(f"  px panel: {px_panel.shape} "
          f"{px_panel.index.min()} .. {px_panel.index.max()}")
    print(f"  Symbols ({px_panel.shape[1]}): {list(px_panel.columns)}")
    oi_delta_arr = oi_proxy.values - 1.0
    print(f"  oi_proxy non-null: "
          f"{float(np.isfinite(oi_delta_arr).mean()):.3f}")
    print(f"  frac oi_delta>+0.2: {float((oi_delta_arr > +0.2).mean()):.4f}  "
          f"<-0.2: {float((oi_delta_arr < -0.2).mean()):.4f}")
    print(f"  frac oi_delta>+0.1: {float((oi_delta_arr > +0.1).mean()):.4f}  "
          f"<-0.1: {float((oi_delta_arr < -0.1).mean()):.4f}")
    print(f"  frac fr>+0.5bp: {float((fr_panel.values > 5e-5).mean()):.4f}  "
          f"|fr|<0.5bp: {float((np.abs(fr_panel.values) < 5e-5).mean()):.4f}")

    n_perm = 200
    n_boot = 200

    results = {}
    for name, cfg in VARIANTS.items():
        results[name] = run_variant(name, cfg, px_panel, oi_proxy, fr_panel,
                                     n_perm=n_perm, n_boot=n_boot)
        print(f"     [elapsed {time.time() - t0:.1f}s]")

    out_path = ROOT / "wave_k166_oi_fr_composite.json"
    curves_path = ROOT / "wave_k166_curves.json"

    summary = {k: {kk: vv for kk, vv in v.items()
                   if kk not in ("equity_curve", "equity_idx")}
               for k, v in results.items()}
    summary["_meta"] = {
        "wall_seconds": time.time() - t0,
        "n_symbols": int(px_panel.shape[1]),
        "symbols": list(px_panel.columns),
        "n_bars": int(px_panel.shape[0]),
        "first_ts": str(px_panel.index.min()),
        "last_ts": str(px_panel.index.max()),
        "n_perm": n_perm,
        "n_boot": n_boot,
        "n_trials_dsr": N_TRIALS_DSR,
        "is_frac": IS_FRAC,
        "cost_bps_per_side": COST_BPS,
        "bars_per_day": BARS_PER_DAY,
        "ann_factor_bar": float(ANN_FACTOR_BAR),
        "hold_bars_default": HOLD_BARS_DEFAULT,
        "vol_fast_days": VOL_FAST_DAYS,
        "vol_slow_days": VOL_SLOW_DAYS,
        "wave": "K166",
        "source": "R6-4 XT-exchange — OI-weighted FR Composite",
        "signal_logic_long": "(oi_delta>+oi_thr AND fr>+fr_long_bp/1e4) -> LONG hold H bars",
        "signal_logic_short": "(oi_delta<-oi_thr AND |fr|<fr_neut_bp/1e4) -> SHORT hold H bars",
        "oi_proxy_definition": (
            "vol_proxy = rolling 7d quote_volume / rolling 30d quote_volume; "
            "oi_delta = vol_proxy - 1. Substitutes for real Bybit OI which is "
            "not cached at 730d cadence."
        ),
        "data_honesty_note": (
            "Volume-momentum proxy mixes spot-like and leverage flow; "
            "true OI delta would be cleaner. This proxy captures sustained "
            "turnover expansion vs contraction at the 7d/30d horizon."
        ),
        "permutation_method": "1-week block circular shuffle of FR panel rows",
    }

    curves = {k: {"equity_curve": v["equity_curve"],
                  "equity_idx": v["equity_idx"]}
              for k, v in results.items()}

    with open(out_path, "w") as f:
        json.dump(summary, f, indent=2, default=str)
    with open(curves_path, "w") as f:
        json.dump(curves, f, indent=2, default=str)

    elapsed = time.time() - t0
    print(f"\n[K166] Done in {elapsed:.1f}s")
    print(f"  -> {out_path}")
    print(f"  -> {curves_path}")

    print("\n=== K166 Summary (OI-weighted FR Composite) ===")
    for name, r in results.items():
        full, oos = r["full"], r["oos"]
        perm = r["permutation"]
        g = r["gates"]
        print(f"{name:14s} netSR={full['sharpe']:+.2f}  OOS={oos['sharpe']:+.2f}  "
              f"grossSR={r['gross_sharpe']:+.2f}  MaxDD={full['max_dd']:+.2%}  "
              f"p={perm['p_value_net']:.3f}  trades={r['n_trades']} "
              f"(L={r['n_trades_long']}/S={r['n_trades_short']})  "
              f"DSR_oos={r['dsr_oos']:.2f}  gates={g['pass_count']}/6")


if __name__ == "__main__":
    main()

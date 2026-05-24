"""
Wave K164 — Detrended Stablecoin Velocity (K162 salvage path)
================================================================================
K162 verdict was REJECT due to secular non-stationarity:
  - WF folds degraded 1.70 -> 1.12 -> 0.78 -> 0.17 (V_p90_top)
  - Raw velocity = DEX_vol/stable_mcap rose 2.6x -> 6x through 2024-25, so
    "absolute" thresholds (90th-percentile of raw, z>2 of raw on 90d window)
    fired increasingly often in late period regardless of regime.
  - OOS Sharpe collapsed to ~0 across all 3 variants.

K164 salvage hypothesis
  The economic mechanism (velocity SPIKE relative to its OWN trend signals
  capital rotation into risk-on) is plausible, but the implementation must
  be:
    (a) Detrended  -> divide by 365d rolling mean of velocity (removes
        secular adoption growth, leaves only "relative excess turnover")
    (b) Relative spike -> 30d z-score of detrended series (short-window
        spike against detrended baseline)
    (c) Long-only via BTC bull filter (BTC > 200d SMA) so we only express
        velocity excess as a LONG bet during regimes where risk-on
        actually pays.  Velocity can also spike during liquidation cascades
        (forced DEX volume), so unconditional longs are dangerous.

Pre-registered method (single, no overfitting loop)
  1. Reuse K162 cache: cache/k135_stable_history.parquet (USDT+USDC+DAI mcap),
     cache/k162_dex_vol.parquet (DefiLlama aggregate DEX volume).
  2. velocity_t   = dex_vol_t / stable_mcap_t.
  3. vel_smooth   = velocity.rolling(7).mean()         (same as K162 base)
  4. vel_trend    = vel_smooth.rolling(365).mean()     (secular component)
  5. vel_detrend  = vel_smooth / vel_trend             (relative excess, ~1.0)
  6. z30          = (vel_detrend - vel_detrend.rolling(30).mean())
                    / vel_detrend.rolling(30).std()    (short spike)
  7. BTC filter   = BTC_close > BTC_close.rolling(200).mean()
  8. Signal state machine (lag-1 execution):
       V_primary       : enter LONG when btc_bull AND z30 > 1.5 ;
                          exit when z30 < 0.5  (no other filter on exit)
       V_no_btc_filter : enter LONG when z30 > 1.5 ; exit when z30 < 0.5
                         (ablation - measures value of BTC filter)
       V_long_short    : btc_bull AND z30>1.5 -> LONG ;
                         (not btc_bull) AND z30<-1.5 -> SHORT ;
                         exit long when |z30|<0.5 ; exit short when |z30|<0.5
  9. Basket: BTC, ETH, SOL, BNB, DOGE, AVAX, LINK equal-weight
     (identical to K162 - like-for-like comparison).
  10. Cost: 7 bps per side (4 taker + 3 slippage).
  11. No max-hold: exit is endogenous (z<0.5).

Audit
  IS/OOS 70/30 ; walk-forward 4-fold ; permutation n=200 (circular shift) ;
  block bootstrap n=200 (block=20) on OOS portfolio ; DSR with
  n_trials = 3 variants * 7 syms + 3 portfolios = 24 ; cost stress 0.5/1.5x.

Key K162-vs-K164 comparison questions
  Q1: Did detrend (step 4-5) flatten vel_detrend per-year (mean ~1.0, std stable)?
  Q2: Did WF fold variance shrink (vs K162 fold 0 -> 3 monotonic decay)?
  Q3: Does the BTC filter actually add OOS Sharpe (V_primary vs V_no_btc_filter)?
  Q4: Does long-short symmetry hold? (V_long_short)

Output
  wave_k164_velocity_detrended.py     (this file)
  wave_k164_velocity_detrended.json   (full audit + comparison)
  wave_k164_curves.json               (equity curves for each variant)

Constraints
  Python 3.11, < 12 min, no paid APIs.
"""

from __future__ import annotations

import json
import math
import os
import time
import warnings
from math import erf

import numpy as np
import pandas as pd

warnings.filterwarnings("ignore")

CACHE = "/Users/nekonaomichi/crypto-lab/cache"
OUT_JSON = "/Users/nekonaomichi/crypto-lab/wave_k164_velocity_detrended.json"
OUT_CURVES = "/Users/nekonaomichi/crypto-lab/wave_k164_curves.json"
DEFI_STABLE_CACHE = f"{CACHE}/k135_stable_history.parquet"
DEX_VOL_CACHE = f"{CACHE}/k162_dex_vol.parquet"

# ---------- universe ----------
SYMBOLS = ["BTC", "ETH", "DOGE", "SOL", "BNB", "AVAX", "LINK"]
PRIMARY = ["BTC", "ETH"]

# ---------- design constants ----------
PERIODS_PER_YEAR = 365
IS_FRAC = 0.70

TAKER_BPS = 4.0
SLIP_BPS = 3.0
COST_PER_SIDE = (TAKER_BPS + SLIP_BPS) / 1e4   # 7 bps = 0.07%

VEL_SMOOTH = 7        # smooth raw velocity
TREND_WIN = 365       # detrend window (secular component)
Z_WIN = 30            # short-window z-score
BTC_MA_WIN = 200      # BTC trend filter window

Z_LONG_ENTRY = 1.5
Z_SHORT_ENTRY = -1.5
Z_LONG_EXIT = 0.5
Z_SHORT_EXIT = -0.5   # abs(z) < 0.5 to exit short

VARIANTS = ["V_primary", "V_no_btc_filter", "V_long_short"]


# ---------- data ----------
def load_dex_volume() -> pd.DataFrame:
    if not os.path.exists(DEX_VOL_CACHE):
        raise FileNotFoundError(
            f"missing {DEX_VOL_CACHE}; run K162 first to populate cache"
        )
    df = pd.read_parquet(DEX_VOL_CACHE)
    print(f"  [cache] DEX vol (last={df.index.max().date()}, n={len(df)})")
    return df


def load_stable_mcap() -> pd.DataFrame:
    if not os.path.exists(DEFI_STABLE_CACHE):
        raise FileNotFoundError(
            f"missing {DEFI_STABLE_CACHE}; run K135 first to populate cache"
        )
    df = pd.read_parquet(DEFI_STABLE_CACHE)
    print(f"  [cache] stable mcap (last={df.index.max().date()}, n={len(df)})")
    return df


def load_close_panel() -> pd.DataFrame:
    frames = []
    for sym in SYMBOLS:
        path = None
        for d in (1200, 730, 365):
            p = f"{CACHE}/{sym}USDT_1d_{d}d.parquet"
            if os.path.exists(p):
                path = p
                break
        if path is None:
            raise FileNotFoundError(f"no daily parquet for {sym}")
        df = pd.read_parquet(path)[["open_time", "close"]].rename(
            columns={"open_time": "ts"}
        )
        df["ts"] = pd.to_datetime(df["ts"]).dt.normalize()
        df = df.sort_values("ts").drop_duplicates("ts").set_index("ts")
        df = df.rename(columns={"close": sym})
        frames.append(df.astype(float))
    panel = pd.concat(frames, axis=1).sort_index()
    return panel


# ---------- signals ----------
def build_signals(stable: pd.DataFrame, dex_vol: pd.DataFrame, btc_close: pd.Series) -> pd.DataFrame:
    """Compute detrended velocity, z30, BTC bull filter, then state machines.

    Notes
      * We compute velocity / trend / z on the FULL stable+dex history
        (so the 365d rolling mean has data to warm up) BEFORE intersecting
        with the price panel.  This preserves more usable signal days.
      * BTC bull filter is computed on btc_close (panel); when btc_close is
        NaN (pre-listing) we treat btc_bull as NaN -> conservatively NO long.
    """
    common = stable.index.intersection(dex_vol.index)
    s = stable.loc[common].copy()
    v = dex_vol.loc[common, "dex_vol_usd"]

    velocity = v / s["TOTAL"]
    vel_smooth = velocity.rolling(VEL_SMOOTH).mean()

    # secular detrend
    vel_trend = vel_smooth.rolling(TREND_WIN).mean()
    vel_detrend = vel_smooth / vel_trend       # ~1.0 on average

    # short-window z
    mu = vel_detrend.rolling(Z_WIN).mean()
    sd = vel_detrend.rolling(Z_WIN).std()
    z30 = (vel_detrend - mu) / sd

    out = pd.DataFrame({
        "velocity": velocity,
        "vel_smooth": vel_smooth,
        "vel_trend": vel_trend,
        "vel_detrend": vel_detrend,
        "z30": z30,
    }, index=s.index)

    # join BTC trend filter
    btc = btc_close.reindex(out.index)
    btc_ma = btc.rolling(BTC_MA_WIN).mean()
    out["btc_close"] = btc
    out["btc_ma200"] = btc_ma
    out["btc_bull"] = (btc > btc_ma).astype(float)
    # if either btc or ma is nan, btc_bull is 0 (no long via filter)
    out.loc[btc.isna() | btc_ma.isna(), "btc_bull"] = 0.0

    n = len(out)
    z_v = z30.values
    bull_v = out["btc_bull"].values

    # ---- V_primary: btc_bull AND z>1.5 long, exit z<0.5 ----
    sig_p = np.zeros(n)
    state = 0
    for i in range(1, n):
        if np.isnan(z_v[i]):
            sig_p[i] = state
            continue
        if state == 0:
            if bull_v[i] == 1.0 and z_v[i] > Z_LONG_ENTRY:
                state = 1
        else:  # state==1 long
            if z_v[i] < Z_LONG_EXIT:
                state = 0
        sig_p[i] = state

    # ---- V_no_btc_filter: z>1.5 long, exit z<0.5 ----
    sig_n = np.zeros(n)
    state = 0
    for i in range(1, n):
        if np.isnan(z_v[i]):
            sig_n[i] = state
            continue
        if state == 0:
            if z_v[i] > Z_LONG_ENTRY:
                state = 1
        else:
            if z_v[i] < Z_LONG_EXIT:
                state = 0
        sig_n[i] = state

    # ---- V_long_short: btc_bull AND z>1.5 -> +1 ;
    #                   NOT btc_bull AND z<-1.5 -> -1 ;
    #                   exit when |z|<0.5 ----
    sig_ls = np.zeros(n)
    state = 0
    for i in range(1, n):
        if np.isnan(z_v[i]):
            sig_ls[i] = state
            continue
        if state == 0:
            if bull_v[i] == 1.0 and z_v[i] > Z_LONG_ENTRY:
                state = 1
            elif bull_v[i] == 0.0 and z_v[i] < Z_SHORT_ENTRY:
                state = -1
        elif state == 1:
            if abs(z_v[i]) < Z_LONG_EXIT:
                state = 0
        elif state == -1:
            if abs(z_v[i]) < Z_LONG_EXIT:
                state = 0
        sig_ls[i] = state

    out["V_primary"] = sig_p
    out["V_no_btc_filter"] = sig_n
    out["V_long_short"] = sig_ls
    return out


# ---------- pnl ----------
def per_symbol_pnl(price: pd.Series, position: pd.Series, cost_mult: float = 1.0) -> pd.DataFrame:
    ret = price.pct_change()
    pos_lag = position.shift(1).fillna(0.0)
    pnl_gross = pos_lag * ret
    turn = (position - position.shift(1).fillna(0.0)).abs()
    cost = turn * COST_PER_SIDE * cost_mult
    return pd.DataFrame({
        "ret": ret,
        "pos_lag": pos_lag,
        "pnl_gross": pnl_gross,
        "cost": cost,
        "pnl_net": pnl_gross - cost,
    })


def variant_portfolio(price_panel: pd.DataFrame, sig: pd.Series, cost_mult: float = 1.0) -> dict:
    pnl_by_sym = {}
    master_idx = price_panel.index
    for sym in price_panel.columns:
        df = pd.concat([price_panel[sym].rename("price"), sig.rename("pos")], axis=1).dropna()
        if len(df) < 30:
            continue
        pnl = per_symbol_pnl(df["price"], df["pos"], cost_mult=cost_mult)
        pnl = pnl.reindex(master_idx).fillna(0.0)
        pnl_by_sym[sym] = pnl
    pnl_net_concat = pd.concat({k: v["pnl_net"] for k, v in pnl_by_sym.items()}, axis=1)
    active_mask = price_panel.notna()[pnl_net_concat.columns]
    n_active = active_mask.sum(axis=1).clip(lower=1)
    port = (pnl_net_concat * active_mask).sum(axis=1) / n_active
    return {"per_symbol": pnl_by_sym, "portfolio": port}


# ---------- metrics ----------
def sharpe(returns, ppy: float = PERIODS_PER_YEAR) -> float:
    r = np.asarray(returns, dtype=float)
    r = r[~np.isnan(r)]
    if len(r) < 10 or r.std() == 0:
        return 0.0
    return float(r.mean() / r.std() * math.sqrt(ppy))


def max_dd(returns) -> float:
    r = np.asarray(returns, dtype=float)
    r = r[~np.isnan(r)]
    if len(r) == 0:
        return 0.0
    eq = (1 + r).cumprod()
    peak = np.maximum.accumulate(eq)
    return float(((eq - peak) / peak).min())


def win_rate(returns) -> float:
    r = np.asarray(returns, dtype=float)
    r = r[~np.isnan(r) & (r != 0)]
    if len(r) == 0:
        return 0.0
    return float((r > 0).mean())


def block_bootstrap_sharpe(ret: np.ndarray, block: int = 20, n: int = 200, seed: int = 7):
    rng = np.random.default_rng(seed)
    r = np.asarray(ret, dtype=float)
    r = r[~np.isnan(r)]
    if len(r) < block * 2:
        return (0.0, 0.0)
    n_blocks = max(1, len(r) // block)
    samples = []
    for _ in range(n):
        starts = rng.integers(0, len(r) - block, size=n_blocks)
        sample = np.concatenate([r[s:s + block] for s in starts])
        samples.append(sharpe(sample))
    samples = np.array(samples)
    return (float(np.percentile(samples, 2.5)), float(np.percentile(samples, 97.5)))


def dsr(sharpe_ann: float, n_obs: int, n_trials: int, ppy: float = PERIODS_PER_YEAR) -> float:
    if n_obs < 30 or n_trials < 1:
        return float("nan")
    sharpe_pb = sharpe_ann / math.sqrt(ppy)
    emc = 0.5772
    sn = math.sqrt(2 * math.log(max(n_trials, 2)))
    expected_max = sn - emc / sn
    sr_std = math.sqrt((1 + 0.5 * sharpe_pb ** 2) / n_obs)
    if sr_std == 0:
        return float("nan")
    z = (sharpe_pb - expected_max * sr_std) / sr_std
    return float(0.5 * (1 + erf(z / math.sqrt(2))))


def slice_metrics(port: pd.Series, lo: int, hi: int) -> dict:
    sub = port.iloc[lo:hi].values
    return {
        "sharpe": sharpe(sub),
        "max_dd": max_dd(sub),
        "win_rate": win_rate(sub),
        "n_bars": int(len(sub)),
        "total_return": float((1 + pd.Series(sub).fillna(0)).prod() - 1),
        "ann_return": float(pd.Series(sub).fillna(0).mean() * PERIODS_PER_YEAR),
        "ann_vol": float(pd.Series(sub).fillna(0).std() * math.sqrt(PERIODS_PER_YEAR)),
    }


def walk_forward_4fold(port_returns: pd.Series) -> list:
    n = len(port_returns)
    fold_size = n // 4
    wf = []
    for k in range(4):
        lo, hi = k * fold_size, (k + 1) * fold_size if k < 3 else n
        sub = port_returns.values[lo:hi]
        wf.append({
            "fold": k,
            "sharpe": sharpe(sub),
            "max_dd": max_dd(sub),
            "total_return": float((1 + pd.Series(sub).fillna(0)).prod() - 1),
            "n_bars": int(len(sub)),
        })
    return wf


def permutation_test_signal(price_panel: pd.DataFrame, sig: pd.Series, n: int = 200, seed: int = 42) -> dict:
    rng = np.random.default_rng(seed)
    base = variant_portfolio(price_panel, sig)["portfolio"]
    base_sr = sharpe(base.values)
    sig_vals = sig.values
    n_len = len(sig_vals)
    min_shift = max(60, Z_WIN * 2)
    null_srs = []
    for _ in range(n):
        shift = int(rng.integers(min_shift, max(min_shift + 1, n_len - min_shift)))
        perm = np.concatenate([sig_vals[shift:], sig_vals[:shift]])
        sig_perm = pd.Series(perm, index=sig.index)
        port_perm = variant_portfolio(price_panel, sig_perm)["portfolio"]
        null_srs.append(sharpe(port_perm.values))
    null_srs = np.array(null_srs)
    p = float((null_srs >= base_sr).mean())
    return {
        "base_sharpe": float(base_sr),
        "null_mean": float(null_srs.mean()),
        "null_std": float(null_srs.std()),
        "null_p95": float(np.percentile(null_srs, 95)),
        "p_value": p,
        "n": int(n),
    }


def equity_curve(returns: pd.Series, every: int = 1) -> list:
    eq = (1 + returns.fillna(0)).cumprod()
    return [{"ts": str(ts.date()), "eq": float(v)} for ts, v in eq.iloc[::every].items()]


# ---------- gates ----------
def evaluate_gates(metrics: dict, perm: dict, dsr_val: float) -> dict:
    oos = metrics["OOS"]
    is_ = metrics["IS"]
    boot_lo = metrics.get("OOS_sharpe_CI95", (0, 0))[0]
    gates = {
        "G1_OOS_sharpe_ge_1": oos["sharpe"] >= 1.0,
        "G2_OOS_maxdd_gt_-30%": oos["max_dd"] > -0.30,
        "G3_OOS_boot_lower_gt_0": boot_lo > 0.0,
        "G4_perm_p_lt_5%": perm["p_value"] < 0.05,
        "G5_DSR_gt_95%": (not math.isnan(dsr_val)) and dsr_val > 0.95,
        "G6_OOSdivIS_ge_0.5": (is_["sharpe"] > 0 and oos["sharpe"] / max(is_["sharpe"], 1e-9) >= 0.5)
                              or (is_["sharpe"] <= 0 and oos["sharpe"] > 0),
    }
    gates["passed"] = sum(bool(v) for v in gates.values())
    gates["total"] = len(gates) - 1
    return gates


# ---------- stationarity diagnostics ----------
def stationarity_diag(series: pd.Series) -> dict:
    """Per-year mean/std + variance ratio to assess detrending success."""
    s = series.dropna()
    by_year = s.groupby(s.index.year).agg(["mean", "std", "min", "max", "count"])
    yr_dict = {int(yr): {k: float(v) for k, v in row.items() if k != "count"}
               for yr, row in by_year.iterrows()}
    # ratio: max-year mean / min-year mean (cross-year drift)
    means = by_year["mean"].values
    if len(means) >= 2 and means.min() > 0:
        cross_yr_drift_ratio = float(means.max() / means.min())
    else:
        cross_yr_drift_ratio = float("nan")
    stds = by_year["std"].values
    if len(stds) >= 2 and stds.min() > 0:
        cross_yr_std_ratio = float(stds.max() / stds.min())
    else:
        cross_yr_std_ratio = float("nan")
    return {
        "by_year": yr_dict,
        "cross_year_mean_ratio": cross_yr_drift_ratio,
        "cross_year_std_ratio": cross_yr_std_ratio,
        "overall_mean": float(s.mean()),
        "overall_std": float(s.std()),
    }


# ---------- main ----------
def main():
    t0 = time.time()
    print("=" * 78)
    print("Wave K164 — Detrended Stablecoin Velocity (K162 salvage)")
    print("=" * 78)

    print("Loading stablecoin market cap...")
    stable = load_stable_mcap()
    print(f"  range: {stable.index.min().date()} -> {stable.index.max().date()}")

    print("Loading DefiLlama DEX volume...")
    dex = load_dex_volume()
    print(f"  range: {dex.index.min().date()} -> {dex.index.max().date()}")

    print("Loading price panel...")
    panel = load_close_panel()
    print(f"  panel shape: {panel.shape}  range: {panel.index.min().date()} -> {panel.index.max().date()}")

    btc_close = panel["BTC"]

    print("Building signals (detrend + z30 + BTC filter)...")
    sigs = build_signals(stable, dex, btc_close)
    print(f"  raw vel mean={sigs['velocity'].mean():.4f}  range=[{sigs['velocity'].min():.4f},{sigs['velocity'].max():.4f}]")
    print(f"  vel_detrend mean={sigs['vel_detrend'].mean():.4f}  std={sigs['vel_detrend'].std():.4f}")
    print(f"  z30 mean={sigs['z30'].mean():.4f}  std={sigs['z30'].std():.4f}  >1.5 frac={(sigs['z30']>1.5).mean():.4f}")

    # intersect with price panel
    common = sigs.index.intersection(panel.index)
    sigs = sigs.loc[common]
    panel = panel.loc[common]
    print(f"  intersection: {len(common)} days, {common.min().date()} -> {common.max().date()}")

    # stationarity diagnostics
    raw_diag = stationarity_diag(sigs["velocity"])
    det_diag = stationarity_diag(sigs["vel_detrend"])
    z_diag = stationarity_diag(sigs["z30"])

    print("\n  RAW velocity by year:")
    for yr, row in raw_diag["by_year"].items():
        print(f"    {yr}: mean={row['mean']:.4f}  std={row['std']:.4f}")
    print(f"  cross_year_mean_ratio (raw): {raw_diag['cross_year_mean_ratio']:.2f}")

    print("\n  DETRENDED velocity by year (should be ~1.0):")
    for yr, row in det_diag["by_year"].items():
        print(f"    {yr}: mean={row['mean']:.4f}  std={row['std']:.4f}")
    print(f"  cross_year_mean_ratio (detrend): {det_diag['cross_year_mean_ratio']:.2f}")

    print("\n  Z30 by year (should be ~N(0,1)):")
    for yr, row in z_diag["by_year"].items():
        print(f"    {yr}: mean={row['mean']:.3f}  std={row['std']:.3f}")

    btc_bull_frac = float(sigs["btc_bull"].mean())
    print(f"\n  BTC bull-regime fraction (over intersection): {btc_bull_frac:.3f}")

    n_full = len(panel)
    cut = int(n_full * IS_FRAC)

    results = {
        "meta": {
            "task": "Wave K164 Detrended Stablecoin Velocity (K162 salvage)",
            "salvage_target": "K162 secular non-stationarity (WF folds 1.70->0.17)",
            "method": (
                "velocity = DEX_vol/stable_mcap; "
                "smooth 7d; detrend by /365d_mean; "
                "z30 = 30d z-score of detrended; "
                "BTC bull filter = close > 200d_MA; "
                "long when bull AND z>1.5, exit z<0.5"
            ),
            "symbols": SYMBOLS,
            "primary": PRIMARY,
            "date_range": [str(common.min().date()), str(common.max().date())],
            "n_days": n_full,
            "IS_cut": cut,
            "cost_per_side_bps": (TAKER_BPS + SLIP_BPS),
            "vel_smooth_days": VEL_SMOOTH,
            "trend_win_days": TREND_WIN,
            "z_win_days": Z_WIN,
            "btc_ma_win_days": BTC_MA_WIN,
            "z_long_entry": Z_LONG_ENTRY,
            "z_long_exit": Z_LONG_EXIT,
            "z_short_entry": Z_SHORT_ENTRY,
            "variants": VARIANTS,
            "btc_bull_frac": btc_bull_frac,
        },
        "stationarity_diag": {
            "raw_velocity": raw_diag,
            "vel_detrend": det_diag,
            "z30": z_diag,
        },
        "snapshot_last": {
            "date": str(sigs.index.max().date()),
            "velocity": float(sigs["velocity"].iloc[-1]) if not np.isnan(sigs["velocity"].iloc[-1]) else None,
            "vel_detrend": float(sigs["vel_detrend"].iloc[-1]) if not np.isnan(sigs["vel_detrend"].iloc[-1]) else None,
            "z30": float(sigs["z30"].iloc[-1]) if not np.isnan(sigs["z30"].iloc[-1]) else None,
            "btc_bull": int(sigs["btc_bull"].iloc[-1]),
            "V_primary": float(sigs["V_primary"].iloc[-1]),
            "V_no_btc_filter": float(sigs["V_no_btc_filter"].iloc[-1]),
            "V_long_short": float(sigs["V_long_short"].iloc[-1]),
        },
        "variants": {},
    }

    curves = {}

    for v in VARIANTS:
        print(f"\n— variant {v} —")
        sig_series = sigs[v]
        out = variant_portfolio(panel, sig_series)
        port = out["portfolio"]
        per_sym = {}
        for sym, pnl in out["per_symbol"].items():
            per_sym[sym] = {
                "IS": slice_metrics(pnl["pnl_net"], 0, cut),
                "OOS": slice_metrics(pnl["pnl_net"], cut, n_full),
                "FULL": slice_metrics(pnl["pnl_net"], 0, n_full),
                "n_trades_approx": int((pnl["pos_lag"].diff().abs() > 0).sum()),
                "time_in_market_pct": float((pnl["pos_lag"].abs() > 0).mean() * 100),
            }
        is_m = slice_metrics(port, 0, cut)
        oos_m = slice_metrics(port, cut, n_full)
        full_m = slice_metrics(port, 0, n_full)
        ci = block_bootstrap_sharpe(port.values[cut:], block=20, n=200)
        wf = walk_forward_4fold(port)
        port_lo = variant_portfolio(panel, sig_series, cost_mult=0.5)["portfolio"]
        port_hi = variant_portfolio(panel, sig_series, cost_mult=1.5)["portfolio"]
        cost_stress = {
            "cost_x0.5_OOS_sharpe": sharpe(port_lo.values[cut:]),
            "cost_x1.0_OOS_sharpe": oos_m["sharpe"],
            "cost_x1.5_OOS_sharpe": sharpe(port_hi.values[cut:]),
        }
        print(f"  running permutation (n=200)...")
        perm = permutation_test_signal(panel, sig_series, n=200, seed=164 + VARIANTS.index(v))
        n_trials = 3 * len(SYMBOLS) + 3
        dsr_val = dsr(oos_m["sharpe"], n_full - cut, n_trials)
        gates = evaluate_gates(
            {"IS": is_m, "OOS": oos_m, "FULL": full_m, "OOS_sharpe_CI95": ci},
            perm,
            dsr_val,
        )
        print(f"  IS sr={is_m['sharpe']:.2f}  OOS sr={oos_m['sharpe']:.2f}  perm_p={perm['p_value']:.3f}  DSR={dsr_val:.3f}  gates {gates['passed']}/{gates['total']}")
        print(f"  WF folds: {[round(x['sharpe'],2) for x in wf]}")

        results["variants"][v] = {
            "portfolio": {
                "IS": is_m,
                "OOS": oos_m,
                "FULL": full_m,
                "OOS_sharpe_CI95": ci,
                "walk_forward_4fold": wf,
                "cost_stress": cost_stress,
                "permutation": perm,
                "DSR": dsr_val,
                "n_trials_DSR": n_trials,
                "gates": gates,
                "time_in_market_pct": float((sig_series.abs() > 0).mean() * 100),
                "n_signal_flips": int((sig_series.diff().abs() > 0).sum()),
            },
            "per_symbol": per_sym,
        }
        curves[v] = equity_curve(port, every=1)
        for sym in PRIMARY:
            if sym in out["per_symbol"]:
                curves[f"{v}__{sym}"] = equity_curve(out["per_symbol"][sym]["pnl_net"], every=1)

    # signal tail
    tail = sigs[["velocity", "vel_detrend", "z30", "btc_bull"] + VARIANTS].tail(60)
    results["signal_tail_60d"] = [
        {
            "date": str(idx.date()),
            "velocity": float(row["velocity"]) if not math.isnan(row["velocity"]) else None,
            "vel_detrend": float(row["vel_detrend"]) if not math.isnan(row["vel_detrend"]) else None,
            "z30": float(row["z30"]) if not math.isnan(row["z30"]) else None,
            "btc_bull": int(row["btc_bull"]),
            **{v: float(row[v]) for v in VARIANTS},
        }
        for idx, row in tail.iterrows()
    ]

    # k162 comparison
    k162_path = "/Users/nekonaomichi/crypto-lab/wave_k162_stable_velocity.json"
    k162_compare = {}
    if os.path.exists(k162_path):
        try:
            with open(k162_path) as f:
                k162 = json.load(f)
            k162_compare = {
                "k162_variants": {
                    v: {
                        "IS_sharpe": k162["variants"][v]["portfolio"]["IS"]["sharpe"],
                        "OOS_sharpe": k162["variants"][v]["portfolio"]["OOS"]["sharpe"],
                        "perm_p": k162["variants"][v]["portfolio"]["permutation"]["p_value"],
                        "DSR": k162["variants"][v]["portfolio"]["DSR"],
                        "gates_passed": k162["variants"][v]["portfolio"]["gates"]["passed"],
                        "wf_sharpes": [x["sharpe"] for x in k162["variants"][v]["portfolio"]["walk_forward_4fold"]],
                    }
                    for v in k162.get("variants", {})
                },
                "k162_date_range": k162.get("meta", {}).get("date_range"),
            }
        except Exception as e:
            k162_compare = {"error": str(e)}
    results["k162_comparison"] = k162_compare

    results["elapsed_sec"] = time.time() - t0

    with open(OUT_JSON, "w") as f:
        json.dump(results, f, indent=2, default=str)
    with open(OUT_CURVES, "w") as f:
        json.dump(curves, f, indent=2, default=str)

    print(f"\nWrote: {OUT_JSON}")
    print(f"Wrote: {OUT_CURVES}")
    print(f"Elapsed: {results['elapsed_sec']:.1f}s")

    print("\n" + "=" * 78)
    print("K164 VARIANT SUMMARY (portfolio)")
    print("=" * 78)
    print(f"{'variant':22s}  {'IS sr':>7s}  {'OOS sr':>7s}  {'OOS DD':>7s}  {'TIM%':>5s}  {'flips':>5s}  {'perm_p':>7s}  {'DSR':>6s}  {'gates':>6s}")
    for v in VARIANTS:
        p = results["variants"][v]["portfolio"]
        print(f"{v:22s}  {p['IS']['sharpe']:>7.2f}  {p['OOS']['sharpe']:>7.2f}  {p['OOS']['max_dd']:>7.2%}  {p['time_in_market_pct']:>5.1f}  {p['n_signal_flips']:>5d}  {p['permutation']['p_value']:>7.3f}  {p['DSR']:>6.3f}  {p['gates']['passed']:>2d}/{p['gates']['total']:<2d}")

    print("\nK162 vs K164 comparison (OOS Sharpe):")
    if k162_compare and "k162_variants" in k162_compare:
        print(f"  K162 V_p90_top OOS={k162_compare['k162_variants']['V_p90_top']['OOS_sharpe']:.2f}  "
              f"V_zscore_2 OOS={k162_compare['k162_variants']['V_zscore_2']['OOS_sharpe']:.2f}  "
              f"V_combo_inflow OOS={k162_compare['k162_variants']['V_combo_inflow']['OOS_sharpe']:.2f}")
    for v in VARIANTS:
        p = results["variants"][v]["portfolio"]
        print(f"  K164 {v}: OOS={p['OOS']['sharpe']:.2f}  WF folds={[round(x['sharpe'],2) for x in p['walk_forward_4fold']]}")


if __name__ == "__main__":
    main()

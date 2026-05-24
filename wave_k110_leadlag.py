"""Wave K110 — BTC->ETH->Alt lead-lag cascade strategy.

Hypothesis: BTC leads ETH leads mid-cap alts at 4H-24H horizon. Use lagged BTC
and ETH returns as features to forecast alt-coin direction.

Outputs:
- /Users/nekonaomichi/crypto-lab/wave_k110_leadlag.json
- /Users/nekonaomichi/crypto-lab/wave_k110_curves.json
"""

from __future__ import annotations

import json
import os
import time
import warnings
from dataclasses import dataclass, asdict
from typing import Dict, List, Tuple

import numpy as np
import pandas as pd
from scipy import stats
from statsmodels.tsa.stattools import grangercausalitytests, ccf

warnings.filterwarnings("ignore")

# -----------------------------------------------------------------------------
# Config
# -----------------------------------------------------------------------------
CACHE_DIR = "/Users/nekonaomichi/crypto-lab/cache"
OUT_RESULTS = "/Users/nekonaomichi/crypto-lab/wave_k110_leadlag.json"
OUT_CURVES = "/Users/nekonaomichi/crypto-lab/wave_k110_curves.json"

ALL_SYMBOLS = [
    "BTC", "ETH", "SOL", "BNB", "DOGE", "AVAX", "LINK", "ADA", "XRP", "INJ",
    "OP", "WIF", "BONK", "SHIB", "ARB", "DOT", "APT", "ATOM", "AAVE", "FLOKI",
    "BOME",
]
LEADERS = ["BTC", "ETH"]
ALTS = [s for s in ALL_SYMBOLS if s not in LEADERS]

# Cost model: taker 0.04% + slippage 0.03% each side = 14 bp round-trip
COST_ROUNDTRIP = 0.0014
COST_THRESHOLD_FACTOR = 2.0  # predicted move must exceed 2x cost

# Vol regime filter
VOL_Z_BLOCK = 2.0

# Horizons (bars)
HORIZONS = [1, 3, 6]

# In-sample fraction
IS_FRAC = 0.70

# Annualization for 4H bars
BARS_PER_YEAR = int(365.25 * 24 / 4)  # 2191

# Permutation/bootstrap
N_PERM = 500
N_BOOT = 500
BOOT_BLOCK = 20

RNG = np.random.default_rng(20260524)


# -----------------------------------------------------------------------------
# Data loading
# -----------------------------------------------------------------------------
def load_close_series() -> pd.DataFrame:
    series = {}
    for s in ALL_SYMBOLS:
        p = os.path.join(CACHE_DIR, f"{s}USDT_4h_730d.parquet")
        if not os.path.exists(p):
            print(f"  skip {s}: file missing")
            continue
        d = pd.read_parquet(p, columns=["open_time", "close"])
        d = d.drop_duplicates(subset=["open_time"]).sort_values("open_time")
        d = d.set_index("open_time")["close"].astype(float)
        series[s] = d
    df = pd.concat(series, axis=1)
    df = df.sort_index()
    # Forward-fill at most 1 bar to handle alignment hiccups
    df = df.ffill(limit=1)
    df = df.dropna(how="any")
    return df


# -----------------------------------------------------------------------------
# Feature engineering
# -----------------------------------------------------------------------------
def build_features(prices: pd.DataFrame) -> Dict[str, pd.DataFrame]:
    """Return per-symbol feature frames with log returns aligned."""
    log_close = np.log(prices)
    rets = log_close.diff()
    rets = rets.dropna()

    btc_r = rets["BTC"]
    eth_r = rets["ETH"]
    btc_vol = btc_r.rolling(60).std()
    btc_volz = (btc_vol - btc_vol.rolling(180).mean()) / btc_vol.rolling(180).std()
    btc_24h_sum = btc_r.rolling(24).sum()  # 24-bar = 4 days roughly
    funding_proxy = np.sign(btc_24h_sum)
    btc_mag_std = btc_r.rolling(120).std()

    out = {}
    for sym in ALTS:
        if sym not in rets.columns:
            continue
        a_r = rets[sym]
        f = pd.DataFrame(index=rets.index)
        for lag in (1, 2, 3, 4):
            f[f"btc_lag{lag}"] = btc_r.shift(lag)
            f[f"eth_lag{lag}"] = eth_r.shift(lag)
        f["alt_lag1"] = a_r.shift(1)
        f["alt_lag2"] = a_r.shift(2)
        f["btc_volz_lag1"] = btc_volz.shift(1)
        f["btc_mag_std"] = btc_mag_std.shift(1)
        f["funding_proxy_lag1"] = funding_proxy.shift(1)
        f["alt_ret"] = a_r  # contemporaneous (for target construction)
        out[sym] = f.dropna()
    return out


# -----------------------------------------------------------------------------
# Statistical lead-lag verification
# -----------------------------------------------------------------------------
def granger_min_p(x_lead: pd.Series, y_target: pd.Series, max_lag: int = 4) -> Tuple[float, int]:
    """Run Granger causality x_lead -> y_target; return (min_p, lag_of_min_p).

    statsmodels grangercausalitytests expects data[:, 0] is the variable being
    predicted, data[:, 1] is the candidate cause.
    """
    df = pd.concat([y_target, x_lead], axis=1, keys=["y", "x"]).dropna()
    if len(df) < 200:
        return (1.0, 0)
    try:
        res = grangercausalitytests(df[["y", "x"]].values, maxlag=max_lag, verbose=False)
    except Exception:
        return (1.0, 0)
    p_by_lag = {}
    for lag, r in res.items():
        # use ssr_ftest
        p_by_lag[lag] = r[0]["ssr_ftest"][1]
    min_lag = min(p_by_lag, key=p_by_lag.get)
    return (float(p_by_lag[min_lag]), int(min_lag))


def ccf_peak_lag(x_lead: pd.Series, y_target: pd.Series, max_lag: int = 6) -> Tuple[int, float]:
    """Return lag (>=0) where corr(y_t, x_{t-lag}) is maximal in absolute value."""
    df = pd.concat([y_target, x_lead], axis=1, keys=["y", "x"]).dropna()
    if len(df) < 200:
        return (0, 0.0)
    best_lag, best_abs, best_val = 0, -1.0, 0.0
    for lag in range(0, max_lag + 1):
        if lag == 0:
            c = df["y"].corr(df["x"])
        else:
            c = df["y"].corr(df["x"].shift(lag))
        if pd.notna(c) and abs(c) > best_abs:
            best_abs, best_val, best_lag = abs(c), float(c), lag
    return (best_lag, best_val)


# -----------------------------------------------------------------------------
# Strategy variants (signal generation)
# -----------------------------------------------------------------------------
def signal_v1_ols(feat: pd.DataFrame, horizon: int, lookback: int = 180) -> pd.Series:
    """Rolling OLS forecast: regress alt_ret_{t} on BTC lag features."""
    cols = [f"btc_lag{l}" for l in (1, 2, 3, 4)] + [f"eth_lag{l}" for l in (1, 2, 3, 4)]
    X = feat[cols].values
    y = feat["alt_ret"].values
    n = len(feat)
    pred = np.full(n, np.nan)
    # rolling estimation: at index i use rows [i-lookback:i] for fit, predict at i
    for i in range(lookback, n):
        Xw = X[i - lookback:i]
        yw = y[i - lookback:i]
        # least squares
        try:
            beta, *_ = np.linalg.lstsq(np.column_stack([np.ones(lookback), Xw]), yw, rcond=None)
        except Exception:
            continue
        xi = np.concatenate([[1.0], X[i]])
        pred[i] = float(xi @ beta)
    pred = pd.Series(pred, index=feat.index, name="pred")
    # Position: long if pred > threshold, short if pred < -threshold; magnitude scaled to expected H-bar move
    # We treat pred as 1-bar forecast; multiply by sqrt(horizon) for H-bar approximation.
    pred_h = pred * np.sqrt(horizon)
    thr = COST_THRESHOLD_FACTOR * COST_ROUNDTRIP
    sig = np.where(pred_h > thr, 1.0, np.where(pred_h < -thr, -1.0, 0.0))
    return pd.Series(sig, index=feat.index, name="sig")


def signal_v2_sign(feat: pd.DataFrame, mag_thr_sigma: float = 1.0) -> pd.Series:
    """Sign rule: if BTC last-1 AND last-2 same sign with magnitude > mag_thr_sigma * std."""
    b1 = feat["btc_lag1"]
    b2 = feat["btc_lag2"]
    sigma = feat["btc_mag_std"]
    long_cond = (b1 > mag_thr_sigma * sigma) & (b2 > 0)
    short_cond = (b1 < -mag_thr_sigma * sigma) & (b2 < 0)
    sig = pd.Series(0.0, index=feat.index)
    sig[long_cond] = 1.0
    sig[short_cond] = -1.0
    return sig


def signal_v3_agreement(feat: pd.DataFrame, mag_thr_sigma: float = 1.0) -> pd.Series:
    """BTC & ETH agreement: both signs equal, BTC magnitude > thr."""
    b1 = feat["btc_lag1"]
    e1 = feat["eth_lag1"]
    sigma = feat["btc_mag_std"]
    long_cond = (b1 > mag_thr_sigma * sigma) & (e1 > 0)
    short_cond = (b1 < -mag_thr_sigma * sigma) & (e1 < 0)
    sig = pd.Series(0.0, index=feat.index)
    sig[long_cond] = 1.0
    sig[short_cond] = -1.0
    return sig


def apply_vol_filter(sig: pd.Series, feat: pd.DataFrame) -> pd.Series:
    block = feat["btc_volz_lag1"] > VOL_Z_BLOCK
    sig = sig.copy()
    sig[block.values] = 0.0
    return sig


# -----------------------------------------------------------------------------
# Backtest engine (non-overlapping H-bar holds)
# -----------------------------------------------------------------------------
def backtest_signal(sig: pd.Series, alt_ret: pd.Series, horizon: int) -> pd.Series:
    """Return per-trade PnL series.

    Position taken at bar t if sig[t] != 0 and we're not already in a trade.
    Hold for `horizon` bars; PnL = sum of alt_ret over [t+1, t+horizon] * sign - cost.
    """
    sig_v = sig.values
    ret_v = alt_ret.values
    idx = alt_ret.index
    n = len(idx)
    trade_times: List[pd.Timestamp] = []
    trade_pnls: List[float] = []
    i = 0
    while i < n - horizon:
        s = sig_v[i]
        if s != 0.0 and not np.isnan(s):
            pnl_log = float(np.nansum(ret_v[i + 1:i + 1 + horizon])) * s
            # convert log return to simple; for small returns approx equal; subtract cost
            pnl = (np.exp(pnl_log) - 1.0) - COST_ROUNDTRIP
            trade_times.append(idx[i])
            trade_pnls.append(pnl)
            i += horizon + 1  # non-overlapping
        else:
            i += 1
    return pd.Series(trade_pnls, index=pd.DatetimeIndex(trade_times))


def bar_pnl_series(sig: pd.Series, alt_ret: pd.Series, horizon: int) -> pd.Series:
    """Convert trade-by-trade PnL to a bar-indexed PnL series (for portfolio aggregation).

    Sets PnL at the exit bar (entry + horizon)."""
    sig_v = sig.values
    ret_v = alt_ret.values
    idx = alt_ret.index
    n = len(idx)
    bar_pnl = np.zeros(n)
    i = 0
    while i < n - horizon:
        s = sig_v[i]
        if s != 0.0 and not np.isnan(s):
            pnl_log = float(np.nansum(ret_v[i + 1:i + 1 + horizon])) * s
            pnl = (np.exp(pnl_log) - 1.0) - COST_ROUNDTRIP
            exit_i = i + horizon
            bar_pnl[exit_i] += pnl
            i += horizon + 1
        else:
            i += 1
    return pd.Series(bar_pnl, index=idx)


# -----------------------------------------------------------------------------
# Metrics
# -----------------------------------------------------------------------------
def sharpe(pnl_bar: pd.Series) -> float:
    """Annualized Sharpe assuming pnl_bar is per-4H-bar series. Zero-fill OK."""
    if pnl_bar.std(ddof=0) == 0 or len(pnl_bar) < 10:
        return 0.0
    return float(pnl_bar.mean() / pnl_bar.std(ddof=0) * np.sqrt(BARS_PER_YEAR))


def equity_curve(pnl_bar: pd.Series) -> pd.Series:
    return (1.0 + pnl_bar).cumprod()


def max_drawdown(eq: pd.Series) -> float:
    peak = eq.cummax()
    dd = (eq / peak - 1.0).min()
    return float(dd)


def calmar(pnl_bar: pd.Series) -> float:
    eq = equity_curve(pnl_bar)
    if len(eq) < 2:
        return 0.0
    years = (eq.index[-1] - eq.index[0]).total_seconds() / (365.25 * 86400)
    if years <= 0:
        return 0.0
    cagr = eq.iloc[-1] ** (1 / years) - 1.0
    mdd = max_drawdown(eq)
    if mdd >= 0:
        return 0.0
    return float(cagr / abs(mdd))


def win_rate_from_trades(trade_pnls: pd.Series) -> float:
    if len(trade_pnls) == 0:
        return 0.0
    return float((trade_pnls > 0).mean())


# -----------------------------------------------------------------------------
# Permutation & bootstrap
# -----------------------------------------------------------------------------
def permutation_null_sharpe(
    feats_by_alt: Dict[str, pd.DataFrame],
    selected_alts: List[str],
    horizon: int,
    n_perm: int = N_PERM,
    mag_thr: float = 1.0,
) -> np.ndarray:
    """Shuffle BTC returns (preserving timeline) and re-run V2 across selected alts.

    Returns array of null portfolio Sharpes.
    """
    # Build base alt return arrays
    btc_ref = feats_by_alt[selected_alts[0]]["btc_lag1"].copy()
    # actually need underlying BTC returns; we can use btc_lag1 shifted back by 1
    # Easier: extract BTC returns once
    btc_r = btc_ref.shift(-1)  # bring lag1 back to contemporaneous
    btc_r = btc_r.dropna()

    nulls = np.empty(n_perm)
    for p in range(n_perm):
        perm = btc_r.sample(frac=1.0, random_state=int(RNG.integers(0, 2**31 - 1))).values
        perm_series = pd.Series(perm, index=btc_r.index)
        # Rebuild "btc_lag1" and "btc_lag2" from permuted series
        b1 = perm_series.shift(1)
        b2 = perm_series.shift(2)
        sigma = perm_series.rolling(120).std().shift(1)
        port_bar = None
        n_used = 0
        for sym in selected_alts:
            feat = feats_by_alt[sym]
            common_idx = feat.index.intersection(b1.index)
            if len(common_idx) < 200:
                continue
            f2 = feat.loc[common_idx].copy()
            f2["btc_lag1"] = b1.loc[common_idx]
            f2["btc_lag2"] = b2.loc[common_idx]
            f2["btc_mag_std"] = sigma.loc[common_idx]
            sig = signal_v2_sign(f2, mag_thr_sigma=mag_thr)
            sig = apply_vol_filter(sig, f2)
            bp = bar_pnl_series(sig, f2["alt_ret"], horizon)
            if port_bar is None:
                port_bar = bp.copy()
            else:
                port_bar = port_bar.add(bp, fill_value=0.0)
            n_used += 1
        if port_bar is None or n_used == 0:
            nulls[p] = 0.0
            continue
        port_bar = port_bar / n_used
        nulls[p] = sharpe(port_bar)
    return nulls


def block_bootstrap_sharpe(pnl_bar: pd.Series, n_boot: int = N_BOOT, block: int = BOOT_BLOCK) -> Tuple[float, float, float]:
    """Stationary block bootstrap CI for annualized Sharpe."""
    arr = pnl_bar.values
    n = len(arr)
    if n < block * 2:
        return (0.0, 0.0, 0.0)
    n_blocks = n // block
    boots = np.empty(n_boot)
    for b in range(n_boot):
        starts = RNG.integers(0, n - block + 1, size=n_blocks)
        sample = np.concatenate([arr[s:s + block] for s in starts])
        if sample.std(ddof=0) == 0:
            boots[b] = 0.0
        else:
            boots[b] = sample.mean() / sample.std(ddof=0) * np.sqrt(BARS_PER_YEAR)
    lo, hi = np.quantile(boots, [0.025, 0.975])
    return (float(boots.mean()), float(lo), float(hi))


def deflated_sharpe(observed_sr: float, n_trials: int, sample_size: int) -> float:
    """Bailey-Lopez de Prado DSR (simplified, normal assumption).

    Returns DSR (probability that true SR > 0 given observed SR and N trials).
    """
    if n_trials <= 1 or sample_size < 20:
        return 0.0
    # Expected max of N standard normals
    emc = 0.5772156649
    e_max = (1 - emc) * stats.norm.ppf(1 - 1.0 / n_trials) + emc * stats.norm.ppf(1 - 1.0 / (n_trials * np.e))
    sr_se = np.sqrt(1.0 / (sample_size - 1))
    z = (observed_sr - e_max * sr_se) / sr_se
    return float(stats.norm.cdf(z))


# -----------------------------------------------------------------------------
# Walk-forward
# -----------------------------------------------------------------------------
def walk_forward(pnl_bar: pd.Series, n_folds: int = 4) -> List[Dict]:
    n = len(pnl_bar)
    fold_size = n // n_folds
    out = []
    for f in range(n_folds):
        seg = pnl_bar.iloc[f * fold_size:(f + 1) * fold_size]
        out.append({
            "fold": f,
            "n": int(len(seg)),
            "sharpe": sharpe(seg),
            "ret_total": float((1 + seg).prod() - 1),
            "mdd": max_drawdown(equity_curve(seg)),
        })
    return out


# -----------------------------------------------------------------------------
# Main pipeline
# -----------------------------------------------------------------------------
def main():
    t0 = time.time()
    print("=" * 70)
    print("Wave K110 — BTC->ETH->Alt lead-lag cascade")
    print("=" * 70)

    prices = load_close_series()
    print(f"Loaded prices: {prices.shape}, range {prices.index[0]} -> {prices.index[-1]}")

    feats_by_alt = build_features(prices)
    print(f"Features built for {len(feats_by_alt)} alts")

    # ---- 1. Statistical lead-lag verification ----
    btc_r = np.log(prices["BTC"]).diff()
    eth_r = np.log(prices["ETH"]).diff()
    granger_results: Dict[str, Dict] = {}
    ccf_results: Dict[str, Dict] = {}
    for sym in feats_by_alt:
        a_r = np.log(prices[sym]).diff()
        gp_b, gl_b = granger_min_p(btc_r, a_r, max_lag=4)
        gp_e, gl_e = granger_min_p(eth_r, a_r, max_lag=4)
        cl_b, cv_b = ccf_peak_lag(btc_r, a_r, max_lag=6)
        cl_e, cv_e = ccf_peak_lag(eth_r, a_r, max_lag=6)
        granger_results[sym] = {
            "btc_min_p": gp_b, "btc_best_lag": gl_b,
            "eth_min_p": gp_e, "eth_best_lag": gl_e,
        }
        ccf_results[sym] = {
            "btc_peak_lag": cl_b, "btc_peak_corr": cv_b,
            "eth_peak_lag": cl_e, "eth_peak_corr": cv_e,
        }
        print(f"  {sym:6s} granger(btc) p={gp_b:.4f} lag={gl_b} | granger(eth) p={gp_e:.4f} lag={gl_e} | ccf(btc) lag={cl_b} corr={cv_b:+.3f}")

    # Filter: keep alts with at least BTC OR ETH granger p < 0.10
    qualified_alts = [s for s, r in granger_results.items() if min(r["btc_min_p"], r["eth_min_p"]) < 0.10]
    print(f"\nQualified by Granger p<0.10: {qualified_alts}")
    if len(qualified_alts) == 0:
        qualified_alts = list(feats_by_alt.keys())  # fallback so pipeline produces something
        print("  (no alt passed; falling back to all)")

    # ---- 2. Per-alt backtest of variants & horizons (IS only for selection) ----
    per_alt_results: Dict[str, Dict] = {}
    is_pnl_bar: Dict[Tuple[str, str, int, float], pd.Series] = {}
    oos_pnl_bar: Dict[Tuple[str, str, int, float], pd.Series] = {}
    full_pnl_bar: Dict[Tuple[str, str, int, float], pd.Series] = {}

    mag_thresholds = [0.5, 1.0, 2.0]
    # Total candidate count: alts * (1 OLS + 3 V2 thr + 3 V3 thr) * 3 horizons
    # = ~19 alts * 7 * 3 = ~399 -> cap by qualified_alts and one horizon scan per variant later

    # To stay under 100 parametrizations, evaluate only on qualified_alts (already filtered),
    # cap to top 8 if >8.
    if len(qualified_alts) > 8:
        # rank by combined granger evidence
        ranks = sorted(qualified_alts,
                       key=lambda s: min(granger_results[s]["btc_min_p"], granger_results[s]["eth_min_p"]))
        qualified_alts = ranks[:8]
        print(f"Capped to top-8 by Granger: {qualified_alts}")

    # Param grid: 8 alts * 7 variants (OLS-1, V2-{0.5,1,2}, V3-{0.5,1,2}) * 3 horizons = 168 -> too many.
    # Restrict OLS to horizon=1 only, V2/V3 to all 3 horizons, mag_thr=1.0 default for full grid,
    # plus mag sensitivity at H=3 only.
    candidates = []
    for sym in qualified_alts:
        # OLS at H in {1,3,6} with default
        for H in HORIZONS:
            candidates.append(("V1_OLS", sym, H, 1.0))
        # V2 at all H, mag=1.0
        for H in HORIZONS:
            candidates.append(("V2_sign", sym, H, 1.0))
        # V3 at all H, mag=1.0
        for H in HORIZONS:
            candidates.append(("V3_agree", sym, H, 1.0))
        # Mag sensitivity at H=3 for V2/V3
        for mt in (0.5, 2.0):
            candidates.append(("V2_sign", sym, 3, mt))
            candidates.append(("V3_agree", sym, 3, mt))
    print(f"Total candidates: {len(candidates)}")

    for (variant, sym, H, mag) in candidates:
        feat = feats_by_alt[sym]
        if variant == "V1_OLS":
            sig = signal_v1_ols(feat, horizon=H, lookback=180)
        elif variant == "V2_sign":
            sig = signal_v2_sign(feat, mag_thr_sigma=mag)
        elif variant == "V3_agree":
            sig = signal_v3_agreement(feat, mag_thr_sigma=mag)
        else:
            continue
        sig = apply_vol_filter(sig, feat)
        pnl_bar = bar_pnl_series(sig, feat["alt_ret"], horizon=H)
        split = int(len(pnl_bar) * IS_FRAC)
        is_p = pnl_bar.iloc[:split]
        oos_p = pnl_bar.iloc[split:]
        key = (variant, sym, H, mag)
        is_pnl_bar[key] = is_p
        oos_pnl_bar[key] = oos_p
        full_pnl_bar[key] = pnl_bar
        per_alt_results.setdefault(sym, {})[f"{variant}_H{H}_mag{mag}"] = {
            "is_sharpe": sharpe(is_p),
            "oos_sharpe": sharpe(oos_p),
            "is_trades": int((is_p != 0).sum()),
            "oos_trades": int((oos_p != 0).sum()),
            "is_total_ret": float((1 + is_p).prod() - 1),
            "oos_total_ret": float((1 + oos_p).prod() - 1),
        }

    # ---- 3. Pick best variant per alt by IS Sharpe (with min trade count) ----
    best_per_alt: Dict[str, Dict] = {}
    for sym in qualified_alts:
        best = None
        for (variant, s, H, mag), pnl in is_pnl_bar.items():
            if s != sym:
                continue
            n_tr = int((pnl != 0).sum())
            if n_tr < 20:
                continue
            sh = sharpe(pnl)
            if best is None or sh > best["is_sharpe"]:
                best = {"variant": variant, "horizon": H, "mag": mag,
                        "is_sharpe": sh, "n_trades_is": n_tr}
        if best is not None:
            key = (best["variant"], sym, best["horizon"], best["mag"])
            best["oos_sharpe"] = sharpe(oos_pnl_bar[key])
            best["oos_trades"] = int((oos_pnl_bar[key] != 0).sum())
            best_per_alt[sym] = best

    print("\nBest per-alt (by IS Sharpe):")
    for sym, info in best_per_alt.items():
        print(f"  {sym:6s} {info['variant']:9s} H={info['horizon']} mag={info['mag']:.1f} | IS Sh={info['is_sharpe']:+.2f} ({info['n_trades_is']} tr) | OOS Sh={info['oos_sharpe']:+.2f} ({info['oos_trades']} tr)")

    # ---- 4. Portfolio: equal-weight across alts passing IS Sharpe > 1.0 ----
    selected = [s for s, info in best_per_alt.items() if info["is_sharpe"] > 1.0]
    print(f"\nSelected for portfolio (IS Sharpe > 1.0): {selected}")
    if len(selected) == 0:
        # Fallback: take any with positive OOS for diagnostic, but flag fail
        print("  No alt passed IS>1.0 — falling back to IS>0.3 for diagnostic")
        selected = [s for s, info in best_per_alt.items() if info["is_sharpe"] > 0.3]

    portfolio_metrics: Dict = {}
    curves_payload: Dict = {}
    perm_p_value = None
    boot_ci = None

    if len(selected) > 0:
        # Build per-alt full PnL series for portfolio
        full_series_list = []
        per_alt_full_pnl = {}
        for sym in selected:
            info = best_per_alt[sym]
            key = (info["variant"], sym, info["horizon"], info["mag"])
            full_series_list.append(full_pnl_bar[key])
            per_alt_full_pnl[sym] = full_pnl_bar[key]
        port_full = pd.concat(full_series_list, axis=1, keys=selected).fillna(0.0)
        port_bar = port_full.mean(axis=1)  # equal weight

        split = int(len(port_bar) * IS_FRAC)
        port_is = port_bar.iloc[:split]
        port_oos = port_bar.iloc[split:]

        portfolio_metrics = {
            "selected_alts": selected,
            "n_alts": len(selected),
            "is_sharpe": sharpe(port_is),
            "oos_sharpe": sharpe(port_oos),
            "full_sharpe": sharpe(port_bar),
            "is_calmar": calmar(port_is),
            "oos_calmar": calmar(port_oos),
            "is_mdd": max_drawdown(equity_curve(port_is)),
            "oos_mdd": max_drawdown(equity_curve(port_oos)),
            "is_total_ret": float((1 + port_is).prod() - 1),
            "oos_total_ret": float((1 + port_oos).prod() - 1),
            "is_win_rate_bar": float((port_is[port_is != 0] > 0).mean()) if (port_is != 0).sum() > 0 else 0.0,
            "oos_win_rate_bar": float((port_oos[port_oos != 0] > 0).mean()) if (port_oos != 0).sum() > 0 else 0.0,
            "walk_forward": walk_forward(port_bar, n_folds=4),
        }

        # ---- 5. Permutation null (use most-common config among selected for V2) ----
        # Use V2_sign at the modal horizon
        from collections import Counter
        horizon_counter = Counter(best_per_alt[s]["horizon"] for s in selected)
        perm_horizon = horizon_counter.most_common(1)[0][0]
        print(f"\nRunning permutation null (n={N_PERM}, V2_sign, H={perm_horizon}, mag=1.0)...")
        t_perm = time.time()
        null_sharpes = permutation_null_sharpe(feats_by_alt, selected, horizon=perm_horizon,
                                               n_perm=N_PERM, mag_thr=1.0)
        # Compare against the actual V2-only portfolio Sharpe at same horizon
        v2_series = []
        for sym in selected:
            key = ("V2_sign", sym, perm_horizon, 1.0)
            if key in full_pnl_bar:
                v2_series.append(full_pnl_bar[key])
        if len(v2_series) > 0:
            v2_port = pd.concat(v2_series, axis=1, keys=selected[:len(v2_series)]).fillna(0.0).mean(axis=1)
            v2_full_sharpe = sharpe(v2_port)
        else:
            v2_full_sharpe = 0.0
        perm_p_value = float((null_sharpes >= v2_full_sharpe).mean())
        print(f"  perm complete in {time.time()-t_perm:.1f}s; V2 portfolio Sharpe={v2_full_sharpe:.3f}, perm p={perm_p_value:.4f}")
        print(f"  null distribution: mean={null_sharpes.mean():.3f}, std={null_sharpes.std():.3f}, q95={np.quantile(null_sharpes,0.95):.3f}")

        # ---- 6. Block bootstrap CI on portfolio (best-config) ----
        print("Running block bootstrap CI on portfolio (best-config)...")
        boot_mean, boot_lo, boot_hi = block_bootstrap_sharpe(port_bar, n_boot=N_BOOT, block=BOOT_BLOCK)
        boot_ci = {"mean": boot_mean, "ci_lo": boot_lo, "ci_hi": boot_hi}
        print(f"  bootstrap Sharpe mean={boot_mean:.3f}, 95% CI=[{boot_lo:.3f}, {boot_hi:.3f}]")

        # ---- DSR ----
        n_trials = len(candidates)  # total searched
        sample_size = int((port_bar != 0).sum())
        dsr = deflated_sharpe(portfolio_metrics["full_sharpe"], n_trials, sample_size)
        portfolio_metrics["dsr"] = dsr
        portfolio_metrics["n_trials"] = n_trials
        portfolio_metrics["dsr_sample_size"] = sample_size
        print(f"DSR={dsr:.4f} (n_trials={n_trials}, sample_size={sample_size})")

        # ---- Equity curves payload ----
        port_eq = equity_curve(port_bar)
        curves_payload["portfolio"] = {
            "timestamps": [t.isoformat() for t in port_eq.index],
            "equity": port_eq.tolist(),
            "is_end_idx": split,
        }
        curves_payload["per_alt"] = {}
        for sym in selected:
            info = best_per_alt[sym]
            key = (info["variant"], sym, info["horizon"], info["mag"])
            eq = equity_curve(full_pnl_bar[key])
            curves_payload["per_alt"][sym] = {
                "variant": info["variant"],
                "horizon": info["horizon"],
                "mag": info["mag"],
                "timestamps": [t.isoformat() for t in eq.index],
                "equity": eq.tolist(),
            }

    # ---- Compile & write ----
    results = {
        "wave": "K110",
        "ts": time.strftime("%Y-%m-%d %H:%M:%S"),
        "hypothesis": "BTC->ETH->Alt lead-lag cascade",
        "data_range": {
            "start": str(prices.index[0]),
            "end": str(prices.index[-1]),
            "n_bars": int(len(prices)),
        },
        "config": {
            "horizons": HORIZONS,
            "cost_roundtrip": COST_ROUNDTRIP,
            "cost_threshold_factor": COST_THRESHOLD_FACTOR,
            "vol_z_block": VOL_Z_BLOCK,
            "is_frac": IS_FRAC,
            "n_perm": N_PERM,
            "n_boot": N_BOOT,
            "boot_block": BOOT_BLOCK,
        },
        "granger_results": granger_results,
        "ccf_results": ccf_results,
        "qualified_alts": qualified_alts,
        "candidates_tested": len(candidates),
        "per_alt_variant_results": per_alt_results,
        "best_per_alt": best_per_alt,
        "portfolio_metrics": portfolio_metrics,
        "permutation_p_value": perm_p_value,
        "bootstrap_ci": boot_ci,
    }

    with open(OUT_RESULTS, "w") as f:
        json.dump(results, f, indent=2, default=str)
    with open(OUT_CURVES, "w") as f:
        json.dump(curves_payload, f, default=str)

    print(f"\nWrote {OUT_RESULTS}")
    print(f"Wrote {OUT_CURVES}")
    print(f"Total wall time: {time.time()-t0:.1f}s")


if __name__ == "__main__":
    main()

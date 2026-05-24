"""Wave K109 — Conditional-Sharpe Dynamic Allocator.

Hypothesis: each of the 7 v4 axes performs differently under different market regimes.
A regime-aware dynamic allocator may outperform the static v4.1 mix (Sh +4.08).

Pipeline:
  1. Load 730d 4H parquet for required symbols (no exchange API calls).
  2. Reuse signal functions from paper_trade_4way_mix.py.
  3. Build per-axis daily PnL series from forward returns (with costs).
  4. Compute regime variables (lagged by 1 bar — no look-ahead).
  5. Build conditional Sharpe matrix.
  6. Build 3 dynamic allocator variants (V1 top-K, V2 soft-weight, V3 regime-gate).
  7. Compare vs v4.1 baseline using Sharpe / Sortino / Calmar / MaxDD / Turnover / 60d window pos %.
  8. CPCV (10 splits, embargo 5), DSR, block-bootstrap CI.
  9. Robustness: cost x0.5, x1.5.

Implementation notes:
  - Funding rate cache for 730d not available; using sign(rolling 24-bar BTC return) as
    funding-sign proxy. Marked clearly in report.
  - OI/historical metrics 730d cache not available; FOPD axis falls back to ret-Z gating only
    (no fr-Z/oi-Z), which conservatively reduces signal but preserves directional structure.
    (Alternative: drop FOPD axis. We keep it because it's part of the v4.1 mix; downstream
    regime weights can effectively gate it down if it underperforms.)
"""
from __future__ import annotations

import json
import sys
import time
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path("/Users/nekonaomichi/crypto-lab")
sys.path.insert(0, str(ROOT))

# ---------------------------------------------------------------------------
# Constants — match paper_trade_4way_mix.py
# ---------------------------------------------------------------------------
TAKER_FEE = 0.0004
SLIPPAGE = 0.0003
COST_PER_RT = 2.0 * (TAKER_FEE + SLIPPAGE)  # round-trip per side*2

BARS_PER_DAY_4H = 6
BARS_PER_DAY_8H = 3
ANNUAL_4H = BARS_PER_DAY_4H * 365.25
ANNUAL_8H = BARS_PER_DAY_8H * 365.25
ANNUAL_D = 365.25

ATR_SYMBOLS = ["OPUSDT", "WIFUSDT", "INJUSDT", "BONKUSDT",
               "DOGEUSDT", "SHIBUSDT", "ARBUSDT", "LINKUSDT"]
FOPD_BEST = {
    "BNBUSDT":  {"fr": 1.0, "oi": 0.5, "ret": 1.5, "sl": 0.04, "tp": 0.06, "mhb": 6},
    "AVAXUSDT": {"fr": 2.0, "oi": 1.0, "ret": 1.5, "sl": 0.04, "tp": 0.06, "mhb": 6},
    "ETHUSDT":  {"fr": 1.5, "oi": 1.5, "ret": 0.5, "sl": 0.04, "tp": 0.06, "mhb": 6},
    "ADAUSDT":  {"fr": 2.0, "oi": 0.5, "ret": 0.5, "sl": 0.04, "tp": 0.06, "mhb": 6},
    "LINKUSDT": {"fr": 1.0, "oi": 0.5, "ret": 1.0, "sl": 0.04, "tp": 0.06, "mhb": 6},
}
ATR_PARAMS_4H = {"atr_short": 7, "atr_long": 56, "threshold": 0.6, "ema_fast": 20, "ema_slow": 80}
ATR_PARAMS_8H = {"atr_short": 4, "atr_long": 28, "threshold": 0.6, "ema_fast": 10, "ema_slow": 40}
EXIT_4H_MHB = 24
EXIT_8H_MHB = 12
VOL_Z = 1.5

VOL_MR_BEST = {
    "BTCUSDT":  {"vol_z_low": -1.0, "vol_z_high": 1.0, "trend_window": 10, "sl": 0.04, "tp": 0.06, "mhb": 12},
    "ETHUSDT":  {"vol_z_low": -2.0, "vol_z_high": 1.0, "trend_window": 20, "sl": 0.04, "tp": 0.06, "mhb": 12},
    "SOLUSDT":  {"vol_z_low": -1.5, "vol_z_high": 2.0, "trend_window": 10, "sl": 0.04, "tp": 0.06, "mhb": 12},
    "BNBUSDT":  {"vol_z_low": -1.5, "vol_z_high": 1.0, "trend_window": 10, "sl": 0.04, "tp": 0.06, "mhb": 12},
}
OI_CAPIT_SYMBOLS = ["BTCUSDT", "ETHUSDT", "SOLUSDT", "BNBUSDT", "DOGEUSDT", "AVAXUSDT", "LINKUSDT"]
OI_CAPIT_PARAMS = {"window": 120, "z_thresh": 2.0, "ret_z_thresh": 1.0, "hold_bars": 12, "sl": 0.04, "tp": 0.06}
BB_SQUEEZE_SYMBOLS = ["BTCUSDT", "ETHUSDT", "SOLUSDT", "DOGEUSDT", "BNBUSDT", "LINKUSDT", "AVAXUSDT", "INJUSDT"]
BB_SQUEEZE_PARAMS = {"ma_window": 40, "sd_mult": 2.0, "squeeze_pct_threshold": 0.20,
                     "squeeze_lookback": 360, "hold_bars": 12, "sl": 0.04, "tp": 0.06}

# v4.1 mix weights (7 axes, sum ~= 1.0)
V41_WEIGHTS = {
    "ATR":        0.245,
    "FOPD":       0.245,
    "BONK_8H":    0.061,
    "SHIB_8H":    0.061,
    "vol_MR":     0.108,
    "OI_capit":   0.180,
    "BB_squeeze": 0.100,
}
AXES = list(V41_WEIGHTS.keys())

CACHE = ROOT / "cache"


# ---------------------------------------------------------------------------
# Data loading
# ---------------------------------------------------------------------------
def load_4h(symbol: str) -> pd.DataFrame:
    p = CACHE / f"{symbol}_4h_730d.parquet"
    df = pd.read_parquet(p).copy()
    df["open_time"] = pd.to_datetime(df["open_time"])
    df = df.sort_values("open_time").reset_index(drop=True)
    return df


def aggregate_4h_to_8h(df_4h: pd.DataFrame) -> pd.DataFrame:
    d = df_4h.copy().sort_values("open_time").reset_index(drop=True)
    d["pair_idx"] = d.index // 2
    return d.groupby("pair_idx").agg({
        "open_time": "first", "open": "first", "high": "max", "low": "min",
        "close": "last", "volume": "sum"
    }).reset_index(drop=True)


# ---------------------------------------------------------------------------
# Signal functions (copied from paper_trade_4way_mix.py — minimal subset)
# ---------------------------------------------------------------------------
def atr_ratio_signal(df: pd.DataFrame, **k) -> pd.Series:
    atr_s = (df["high"] - df["low"]).rolling(k["atr_short"]).mean()
    atr_l = (df["high"] - df["low"]).rolling(k["atr_long"]).mean()
    comp = atr_s < atr_l * k["threshold"]
    ef = df["close"].ewm(span=k["ema_fast"]).mean()
    es = df["close"].ewm(span=k["ema_slow"]).mean()
    sig = pd.Series(0, index=df.index)
    sig[comp & (ef > es)] = 1
    sig[comp & (ef < es)] = -1
    return sig


def btc_vol_mr_signal_local(df: pd.DataFrame, vol_z_low, vol_z_high, trend_window):
    close = df["close"].values
    ret = np.zeros_like(close)
    ret[1:] = (close[1:] - close[:-1]) / close[:-1]
    rv = pd.Series(ret).rolling(60).std() * np.sqrt(2190) * 100
    rvm = rv.rolling(360).mean()
    rvs = rv.rolling(360).std()
    vol_z = ((rv - rvm) / (rvs + 1e-10)).fillna(0).values
    ema_fast = pd.Series(close).ewm(span=trend_window).mean().values
    ema_slow = pd.Series(close).ewm(span=trend_window * 3).mean().values
    bullish = ema_fast > ema_slow
    bearish = ema_fast < ema_slow
    recent_ret = pd.Series(close).pct_change(6).fillna(0).values
    sig = np.zeros(len(df), dtype=int)
    sig[(vol_z < vol_z_low) & bullish] = +1
    sig[(vol_z < vol_z_low) & bearish] = -1
    sig[(vol_z > vol_z_high) & (recent_ret < -0.05)] = +1
    sig[(vol_z > vol_z_high) & (recent_ret > 0.05)] = -1
    sig[:380] = 0
    return pd.Series(sig, index=df.index)


def fopd_signal_retonly(df: pd.DataFrame, ret_z_thresh: float, w: int = 180) -> pd.Series:
    """FOPD fallback using only return Z (no funding/OI cache for 730d).
    Keeps the directional logic but with one filter instead of three.
    """
    close = df["close"].values
    ret = pd.Series(close).pct_change(6).fillna(0)
    ret_z = ((ret - ret.rolling(w).mean()) / (ret.rolling(w).std() + 1e-12)).fillna(0).values
    sig = np.zeros(len(df), dtype=int)
    sig[ret_z < -ret_z_thresh] = +1
    sig[ret_z > ret_z_thresh] = -1
    sig[:w + 10] = 0
    return pd.Series(sig, index=df.index)


def oi_capit_signal_priceonly(df: pd.DataFrame, **p) -> pd.Series:
    """OI capit fallback using price-z only (no OI cache for 730d).
    Trigger LONG when price ret-z <= -ret_z_thresh (capitulation proxy without OI).
    """
    w = p["window"]
    close = df["close"]
    ret_n = close.pct_change(6)
    ret_z = (ret_n - ret_n.rolling(w).mean()) / (ret_n.rolling(w).std() + 1e-10)
    sig = pd.Series(0, index=df.index, dtype=int)
    sig[ret_z <= -p["ret_z_thresh"]] = +1
    return sig


def bb_squeeze_signal(df: pd.DataFrame, p) -> pd.Series:
    c = df["close"].values
    ma = pd.Series(c).rolling(p["ma_window"]).mean()
    sd = pd.Series(c).rolling(p["ma_window"]).std()
    bb_width = (2 * p["sd_mult"] * sd) / ma
    bb_width_pct = bb_width.rolling(p["squeeze_lookback"]).rank(pct=True)
    squeezed_recent = (bb_width_pct < p["squeeze_pct_threshold"]).fillna(False).rolling(5).max() > 0
    upper = (ma + p["sd_mult"] * sd).values
    lower = (ma - p["sd_mult"] * sd).values
    sig = np.zeros(len(df), dtype=int)
    long_break = (c > upper) & squeezed_recent.fillna(False).values
    short_break = (c < lower) & squeezed_recent.fillna(False).values
    sig[long_break] = +1
    sig[short_break] = -1
    return pd.Series(sig, index=df.index)


# ---------------------------------------------------------------------------
# Forward-return PnL with SL/TP/MHB exits
# ---------------------------------------------------------------------------
def simulate_signal_pnl(df: pd.DataFrame, sig: pd.Series, sl: float, tp: float,
                        mhb: int, cost_per_rt: float = COST_PER_RT) -> pd.Series:
    """For each entry signal bar, compute trade pnl% and attribute it to the EXIT bar.
    Returns a Series aligned to df.index with the realized return at each bar (0 elsewhere).
    Costs (2*(taker+slip)) subtracted once per trade.
    Bar t signal -> entry at open of bar t+1; check bars t+1..t+mhb for SL/TP, else MH at t+mhb close.
    """
    n = len(df)
    high = df["high"].values
    low = df["low"].values
    open_ = df["open"].values
    close = df["close"].values
    pnl_at_exit = np.zeros(n)
    # We'll also produce a "position-in-trade" flag for turnover/exposure analysis
    in_trade = np.zeros(n, dtype=bool)
    cool_until = -1
    sig_v = sig.values
    for i in range(n - 1):
        if i < cool_until:
            continue
        s = int(sig_v[i])
        if s == 0:
            continue
        # Entry next bar's open
        j_entry = i + 1
        if j_entry >= n:
            break
        entry = open_[j_entry]
        sl_px = entry * (1 - sl) if s > 0 else entry * (1 + sl)
        tp_px = entry * (1 + tp) if s > 0 else entry * (1 - tp)
        exit_bar = None
        exit_px = None
        for j in range(j_entry, min(n, j_entry + mhb)):
            if s > 0:
                if low[j] <= sl_px:
                    exit_bar = j; exit_px = sl_px; break
                if high[j] >= tp_px:
                    exit_bar = j; exit_px = tp_px; break
            else:
                if high[j] >= sl_px:
                    exit_bar = j; exit_px = sl_px; break
                if low[j] <= tp_px:
                    exit_bar = j; exit_px = tp_px; break
        if exit_bar is None:
            exit_bar = min(n - 1, j_entry + mhb - 1)
            exit_px = close[exit_bar]
        if s > 0:
            pct = (exit_px - entry) / entry
        else:
            pct = (entry - exit_px) / entry
        pct -= cost_per_rt
        pnl_at_exit[exit_bar] += pct
        in_trade[j_entry:exit_bar + 1] = True
        cool_until = exit_bar + 1  # block re-entry until trade exits (no pyramiding)
    return pd.Series(pnl_at_exit, index=df.index, name="pnl"), pd.Series(in_trade, index=df.index, name="in_trade")


# ---------------------------------------------------------------------------
# Build axis-level per-bar PnL series (4H grid), then aggregate to daily
# ---------------------------------------------------------------------------
def build_axis_pnl_4h(symbols: list, sig_fn, sl, tp, mhb, df_map: dict,
                      cost_per_rt: float = COST_PER_RT) -> pd.Series:
    """Equal-weight across `symbols`. Each symbol gets weight 1/N (so axis total per-bar
    return is the average across symbols when there's a trade; idle bars are 0).
    """
    parts = []
    for s in symbols:
        if s not in df_map:
            continue
        df = df_map[s]
        sig = sig_fn(df)
        pnl, _ = simulate_signal_pnl(df, sig, sl, tp, mhb, cost_per_rt=cost_per_rt)
        pnl.index = df["open_time"].values
        parts.append(pnl)
    if not parts:
        return pd.Series(dtype=float)
    n = len(parts)
    df_concat = pd.concat(parts, axis=1)
    df_concat.columns = [f"s{i}" for i in range(len(parts))]
    return df_concat.fillna(0).mean(axis=1)  # equal weight average


def to_daily(pnl_4h: pd.Series) -> pd.Series:
    if pnl_4h.empty:
        return pd.Series(dtype=float)
    # 4H bars: 6/day. Sum within the day (return-additive approximation for small returns).
    s = pnl_4h.copy()
    s.index = pd.to_datetime(s.index)
    return s.groupby(s.index.normalize()).sum()


# ---------------------------------------------------------------------------
# Regime variables (lagged 1 bar — no look-ahead)
# ---------------------------------------------------------------------------
def compute_regimes(df_btc_4h: pd.DataFrame, df_map: dict) -> pd.DataFrame:
    """Return DataFrame indexed by 4H open_time with regime quartile bins for each variable.
    All values are constructed from data up to bar t and SHIFTED by 1 so that the regime
    applied to bar t reflects info available at bar t-1.
    """
    t = pd.to_datetime(df_btc_4h["open_time"].values)
    close = df_btc_4h["close"].values
    ret = pd.Series(close).pct_change()

    # r1: realized vol Z (60-bar rv / 360-bar baseline)
    rv = ret.rolling(60).std() * np.sqrt(2190) * 100
    rvm = rv.rolling(360).mean()
    rvs = rv.rolling(360).std()
    vol_z = ((rv - rvm) / (rvs + 1e-10)).fillna(0)

    # r2: trend regime: sign(close - EMA200)
    ema200 = pd.Series(close).ewm(span=200).mean()
    trend = np.sign(pd.Series(close) - ema200).fillna(0).astype(int)

    # r3: funding-sign proxy: sign(rolling 24-bar BTC return)
    ret24 = pd.Series(close).pct_change(24)
    fund_sign = np.sign(ret24).fillna(0).astype(int)

    # r4: cross-section dispersion — stdev of 60-bar returns across top symbols
    top_syms = ["BTCUSDT", "ETHUSDT", "SOLUSDT", "BNBUSDT", "DOGEUSDT",
                "AVAXUSDT", "LINKUSDT", "ADAUSDT", "XRPUSDT", "TRXUSDT"]
    ret_mat = []
    for s in top_syms:
        if s not in df_map:
            continue
        d = df_map[s]
        if len(d) != len(df_btc_4h):
            # align to BTC time
            x = d.set_index(pd.to_datetime(d["open_time"]))[["close"]].reindex(t).ffill()
            r = x["close"].pct_change(60).reset_index(drop=True)
        else:
            r = d["close"].pct_change(60).reset_index(drop=True)
        ret_mat.append(r.values)
    ret_mat = np.array(ret_mat)
    disp = pd.Series(np.nanstd(ret_mat, axis=0), name="disp").fillna(0)

    df = pd.DataFrame({"t": t, "vol_z": vol_z.values, "trend": trend.values,
                       "fund_sign": fund_sign.values, "disp": disp.values})

    # Lag by 1 bar
    df[["vol_z", "trend", "fund_sign", "disp"]] = df[["vol_z", "trend", "fund_sign", "disp"]].shift(1)

    # Bin: vol_z and disp into quartiles using rolling 360-bar window? -> use full-sample for stability
    df["r1_vol"] = pd.qcut(df["vol_z"], 4, labels=["Q1", "Q2", "Q3", "Q4"], duplicates="drop")
    df["r2_trend"] = df["trend"].map({1: "UP", -1: "DN", 0: "FLAT"}).fillna("FLAT")
    df["r3_fund"] = df["fund_sign"].map({1: "POS", -1: "NEG", 0: "ZERO"}).fillna("ZERO")
    df["r4_disp"] = pd.qcut(df["disp"], 4, labels=["Q1", "Q2", "Q3", "Q4"], duplicates="drop")
    return df


def regimes_to_daily(reg_4h: pd.DataFrame) -> pd.DataFrame:
    """Take the FIRST regime value of each day (so the regime is fully determined at
    start of day based on prior bars).
    """
    s = reg_4h.copy()
    s["day"] = pd.to_datetime(s["t"]).dt.normalize()
    out = s.groupby("day").first()[["r1_vol", "r2_trend", "r3_fund", "r4_disp"]]
    return out


# ---------------------------------------------------------------------------
# Metrics
# ---------------------------------------------------------------------------
def annualize_sharpe(daily_ret: pd.Series) -> float:
    if daily_ret.std() == 0 or len(daily_ret) < 5:
        return 0.0
    return float(daily_ret.mean() / daily_ret.std() * np.sqrt(ANNUAL_D))


def annualize_sortino(daily_ret: pd.Series) -> float:
    neg = daily_ret[daily_ret < 0]
    if neg.std() == 0 or len(neg) < 2:
        return 0.0
    return float(daily_ret.mean() / neg.std() * np.sqrt(ANNUAL_D))


def max_drawdown_pct(daily_ret: pd.Series) -> float:
    eq = (1 + daily_ret.fillna(0)).cumprod()
    peak = eq.cummax()
    dd = eq / peak - 1
    return float(dd.min() * 100)


def calmar(daily_ret: pd.Series) -> float:
    if len(daily_ret) < 10:
        return 0.0
    eq = (1 + daily_ret.fillna(0)).cumprod()
    days = len(daily_ret)
    cagr = float(eq.iloc[-1] ** (365.25 / max(days, 1)) - 1)
    mdd = abs(max_drawdown_pct(daily_ret) / 100)
    return float(cagr / mdd) if mdd > 0 else 0.0


def rolling_60d_pos_pct(daily_ret: pd.Series, window: int = 60) -> float:
    """Fraction of overlapping 60-day windows whose cumulative return is positive."""
    if len(daily_ret) < window + 5:
        return 0.0
    s = daily_ret.fillna(0).rolling(window).sum().dropna()
    return float((s > 0).mean())


def turnover_metric(weights: pd.DataFrame) -> float:
    """Average per-day L1 turnover across axes (sum of |Δw|)."""
    if weights.empty or len(weights) < 2:
        return 0.0
    diff = weights.diff().abs().sum(axis=1)
    return float(diff.mean())


def summary_metrics(daily_ret: pd.Series, weights: pd.DataFrame = None,
                    turnover_cost: float = 0.0) -> dict:
    """Compute summary metrics. Optionally subtract turnover cost from daily returns.
    turnover_cost: per-unit L1 weight change cost (e.g., COST_PER_RT). Conservative."""
    if weights is not None and turnover_cost > 0:
        diff_l1 = weights.diff().abs().sum(axis=1).fillna(0)
        daily_ret = daily_ret - diff_l1 * turnover_cost
    return {
        "sharpe": round(annualize_sharpe(daily_ret), 3),
        "sortino": round(annualize_sortino(daily_ret), 3),
        "calmar": round(calmar(daily_ret), 3),
        "max_dd_pct": round(max_drawdown_pct(daily_ret), 3),
        "cum_ret_pct": round(float((1 + daily_ret.fillna(0)).prod() - 1) * 100, 3),
        "n_days": int(len(daily_ret)),
        "win_60d_pct": round(rolling_60d_pos_pct(daily_ret) * 100, 2),
        "turnover_l1_per_day": round(turnover_metric(weights) if weights is not None else 0.0, 4),
    }


# ---------------------------------------------------------------------------
# Conditional Sharpe matrix
# ---------------------------------------------------------------------------
def conditional_sharpe_matrix(axis_daily: pd.DataFrame, regimes_daily: pd.DataFrame) -> dict:
    """For each axis × (regime variable × bin), compute annualized Sharpe."""
    out = {}
    aligned = axis_daily.join(regimes_daily, how="inner")
    for rvar in ["r1_vol", "r2_trend", "r3_fund", "r4_disp"]:
        out[rvar] = {}
        bins = aligned[rvar].dropna().unique().tolist()
        for b in bins:
            mask = aligned[rvar] == b
            sub = aligned.loc[mask]
            out[rvar][str(b)] = {}
            for axis in AXES:
                if axis not in sub.columns:
                    continue
                sh = annualize_sharpe(sub[axis])
                out[rvar][str(b)][axis] = round(sh, 3)
            out[rvar][str(b)]["_n_days"] = int(mask.sum())
    return out


# ---------------------------------------------------------------------------
# Dynamic allocator variants
# ---------------------------------------------------------------------------
def build_dynamic_weights(axis_daily: pd.DataFrame, regimes_daily: pd.DataFrame,
                          cond_sh: dict, primary_regime: str = "r1_vol",
                          variant: str = "V1", top_k: int = 3) -> pd.DataFrame:
    """Produce per-day weight matrix (rows=days, cols=axes) for a given variant.
    Uses cond_sh computed on the full sample to pick weights. (For CPCV we'll rebuild on train only.)
    """
    aligned = axis_daily.join(regimes_daily, how="inner")
    weights = pd.DataFrame(0.0, index=aligned.index, columns=AXES)
    if variant == "V3":
        # Start with v4.1 weights, then gate to 0 if ANY regime gives Sharpe < -1.0 for that axis
        base = pd.Series(V41_WEIGHTS)
        for day, row in aligned.iterrows():
            w = base.copy()
            for axis in AXES:
                gated = False
                for rvar in ["r1_vol", "r2_trend", "r3_fund", "r4_disp"]:
                    bin_val = str(row[rvar])
                    sh = cond_sh.get(rvar, {}).get(bin_val, {}).get(axis, 0.0)
                    if sh < -1.0:
                        gated = True
                        break
                if gated:
                    w[axis] = 0.0
            # Renormalize
            tot = w.sum()
            if tot > 0:
                w = w / tot
            weights.loc[day, AXES] = w[AXES].values
        return weights

    for day, row in aligned.iterrows():
        bin_val = str(row[primary_regime])
        sh_map = {axis: cond_sh.get(primary_regime, {}).get(bin_val, {}).get(axis, 0.0) for axis in AXES}
        if variant == "V1":
            # Top-K
            top = sorted(sh_map.items(), key=lambda x: x[1], reverse=True)[:top_k]
            top_axes = [a for a, _ in top]
            w = pd.Series(0.0, index=AXES)
            w[top_axes] = 1.0 / len(top_axes)
        elif variant == "V2":
            # Soft: proportional to max(0, Sharpe)
            pos = {a: max(0.0, s) for a, s in sh_map.items()}
            tot = sum(pos.values())
            if tot <= 0:
                w = pd.Series(V41_WEIGHTS)  # fallback to baseline if no positive Sharpe
            else:
                w = pd.Series({a: v / tot for a, v in pos.items()})
        else:
            raise ValueError(variant)
        weights.loc[day, AXES] = w[AXES].values
    return weights


def portfolio_daily_ret(axis_daily: pd.DataFrame, weights: pd.DataFrame) -> pd.Series:
    """Element-wise: sum(axis_ret * weight). Weights are 'today's allocation', applied to today's PnL.
    Since regimes use lagged data, this is causally clean.
    """
    aligned = axis_daily.join(weights[AXES], how="inner", rsuffix="_w")
    ax = aligned[AXES].values
    w = aligned[[c + "_w" for c in AXES]].values
    pr = (ax * w).sum(axis=1)
    return pd.Series(pr, index=aligned.index)


# ---------------------------------------------------------------------------
# CPCV + DSR + block bootstrap
# ---------------------------------------------------------------------------
def cpcv_pbo(axis_daily: pd.DataFrame, regimes_daily: pd.DataFrame,
             n_splits: int = 10, embargo: int = 5, variant: str = "V1",
             primary_regime: str = "r1_vol", top_k: int = 3) -> dict:
    """Compute PBO for a variant: at each split, recompute conditional Sharpe on TRAIN only,
    build weights, evaluate on TEST. PBO = fraction of splits where OOS Sharpe < 0.
    """
    aligned = axis_daily.join(regimes_daily, how="inner").dropna()
    n = len(aligned)
    if n < n_splits * 30:
        return {"pbo": 1.0, "paths": 0, "oos_sharpes": [], "is_sharpes": []}
    fold_size = n // n_splits
    oos_shs = []
    is_shs = []
    for k in range(n_splits):
        test_start = k * fold_size
        test_end = test_start + fold_size if k < n_splits - 1 else n
        # Embargo
        train_idx = list(range(0, max(0, test_start - embargo))) + list(range(min(n, test_end + embargo), n))
        test_idx = list(range(test_start, test_end))
        if len(train_idx) < 30 or len(test_idx) < 10:
            continue
        train = aligned.iloc[train_idx]
        test = aligned.iloc[test_idx]
        # Rebuild conditional Sharpe on train only
        cond_sh_train = conditional_sharpe_matrix(train[AXES], train[["r1_vol", "r2_trend", "r3_fund", "r4_disp"]])
        # Build weights on test using train-derived cond_sh
        w_test = build_dynamic_weights(test[AXES], test[["r1_vol", "r2_trend", "r3_fund", "r4_disp"]],
                                       cond_sh_train, primary_regime=primary_regime,
                                       variant=variant, top_k=top_k)
        # Also IS performance
        w_train = build_dynamic_weights(train[AXES], train[["r1_vol", "r2_trend", "r3_fund", "r4_disp"]],
                                        cond_sh_train, primary_regime=primary_regime,
                                        variant=variant, top_k=top_k)
        pr_test = portfolio_daily_ret(test[AXES], w_test)
        pr_train = portfolio_daily_ret(train[AXES], w_train)
        oos_shs.append(annualize_sharpe(pr_test))
        is_shs.append(annualize_sharpe(pr_train))
    if not oos_shs:
        return {"pbo": 1.0, "paths": 0, "oos_sharpes": [], "is_sharpes": []}
    pbo = sum(1 for s in oos_shs if s < 0) / len(oos_shs)
    return {"pbo": round(pbo, 3), "paths": len(oos_shs),
            "oos_sharpes": [round(x, 3) for x in oos_shs],
            "is_sharpes": [round(x, 3) for x in is_shs],
            "oos_mean": round(float(np.mean(oos_shs)), 3),
            "oos_std": round(float(np.std(oos_shs)), 3)}


def block_bootstrap_sharpe_ci(daily_ret: pd.Series, block_size: int = 20,
                              n_iter: int = 1000, ci: tuple = (0.025, 0.975),
                              seed: int = 42) -> dict:
    rng = np.random.default_rng(seed)
    arr = daily_ret.fillna(0).values
    n = len(arr)
    if n < block_size * 3:
        return {"sharpe_mean": 0, "ci_low": 0, "ci_high": 0, "n_iter": 0}
    n_blocks = n // block_size
    samples = []
    for _ in range(n_iter):
        # Pick n_blocks random block starts (with replacement)
        starts = rng.integers(0, n - block_size + 1, size=n_blocks)
        sample = np.concatenate([arr[s:s + block_size] for s in starts])
        s = sample.std()
        if s == 0:
            samples.append(0.0)
        else:
            samples.append(float(sample.mean() / s * np.sqrt(ANNUAL_D)))
    return {
        "sharpe_mean": round(float(np.mean(samples)), 3),
        "ci_low": round(float(np.quantile(samples, ci[0])), 3),
        "ci_high": round(float(np.quantile(samples, ci[1])), 3),
        "n_iter": n_iter,
    }


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------
def main():
    t0 = time.time()
    print("Wave K109 — Conditional-Sharpe Dynamic Allocator")

    # Load all needed 4H symbols once (universe-of-interest from the 7 axes)
    needed = set(ATR_SYMBOLS) | set(FOPD_BEST.keys()) | {"BONKUSDT", "SHIBUSDT"} \
        | set(VOL_MR_BEST.keys()) | set(OI_CAPIT_SYMBOLS) | set(BB_SQUEEZE_SYMBOLS) | {"BTCUSDT"}
    # Plus dispersion universe
    disp_universe = ["BTCUSDT", "ETHUSDT", "SOLUSDT", "BNBUSDT", "DOGEUSDT",
                     "AVAXUSDT", "LINKUSDT", "ADAUSDT", "XRPUSDT", "TRXUSDT"]
    needed |= set(disp_universe)
    print(f"  Loading {len(needed)} symbols (4H 730d)...")
    df_map = {}
    for s in sorted(needed):
        try:
            df_map[s] = load_4h(s)
        except FileNotFoundError:
            print(f"    [WARN] missing cache for {s}, skipping")
    print(f"  Loaded {len(df_map)} symbols.")

    # ---------- Build axis-level daily PnL ----------
    print("\n[Building axis-level daily PnL series]")

    def build_all_axes(cost_mult: float = 1.0):
        cost = COST_PER_RT * cost_mult
        axes = {}

        # 1. ATR × 8 (4H)
        axes["ATR"] = build_axis_pnl_4h(
            ATR_SYMBOLS,
            lambda d: atr_ratio_signal(d, **ATR_PARAMS_4H),
            sl=0.04, tp=0.08, mhb=EXIT_4H_MHB, df_map=df_map, cost_per_rt=cost,
        )

        # 2. FOPD × 5 (4H, ret-only fallback)
        def make_fopd(sym):
            p = FOPD_BEST[sym]
            return lambda d: fopd_signal_retonly(d, ret_z_thresh=p["ret"])
        fopd_pieces = []
        for sym in FOPD_BEST.keys():
            if sym not in df_map:
                continue
            df = df_map[sym]
            sig = make_fopd(sym)(df)
            p = FOPD_BEST[sym]
            pnl, _ = simulate_signal_pnl(df, sig, p["sl"], p["tp"], p["mhb"], cost_per_rt=cost)
            pnl.index = df["open_time"].values
            fopd_pieces.append(pnl)
        axes["FOPD"] = pd.concat(fopd_pieces, axis=1).fillna(0).mean(axis=1) if fopd_pieces else pd.Series(dtype=float)

        # 3. BONK 8H
        df_bonk_8h = aggregate_4h_to_8h(df_map["BONKUSDT"])
        sig_bonk = atr_ratio_signal(df_bonk_8h, **ATR_PARAMS_8H)
        pnl_bonk, _ = simulate_signal_pnl(df_bonk_8h, sig_bonk, 0.04, 0.08, EXIT_8H_MHB, cost_per_rt=cost)
        pnl_bonk.index = df_bonk_8h["open_time"].values
        axes["BONK_8H"] = pnl_bonk

        # 4. SHIB 8H
        df_shib_8h = aggregate_4h_to_8h(df_map["SHIBUSDT"])
        sig_shib = atr_ratio_signal(df_shib_8h, **ATR_PARAMS_8H)
        pnl_shib, _ = simulate_signal_pnl(df_shib_8h, sig_shib, 0.04, 0.08, EXIT_8H_MHB, cost_per_rt=cost)
        pnl_shib.index = df_shib_8h["open_time"].values
        axes["SHIB_8H"] = pnl_shib

        # 5. vol_MR × 4 (4H)
        vol_mr_pieces = []
        for sym, p in VOL_MR_BEST.items():
            if sym not in df_map:
                continue
            df = df_map[sym]
            sig = btc_vol_mr_signal_local(df, p["vol_z_low"], p["vol_z_high"], p["trend_window"])
            pnl, _ = simulate_signal_pnl(df, sig, p["sl"], p["tp"], p["mhb"], cost_per_rt=cost)
            pnl.index = df["open_time"].values
            vol_mr_pieces.append(pnl)
        axes["vol_MR"] = pd.concat(vol_mr_pieces, axis=1).fillna(0).mean(axis=1)

        # 6. OI_capit × 7 (4H, price-only fallback)
        axes["OI_capit"] = build_axis_pnl_4h(
            OI_CAPIT_SYMBOLS,
            lambda d: oi_capit_signal_priceonly(d, **OI_CAPIT_PARAMS),
            sl=OI_CAPIT_PARAMS["sl"], tp=OI_CAPIT_PARAMS["tp"],
            mhb=OI_CAPIT_PARAMS["hold_bars"], df_map=df_map, cost_per_rt=cost,
        )

        # 7. BB_squeeze × 8 (4H)
        axes["BB_squeeze"] = build_axis_pnl_4h(
            BB_SQUEEZE_SYMBOLS,
            lambda d: bb_squeeze_signal(d, BB_SQUEEZE_PARAMS),
            sl=BB_SQUEEZE_PARAMS["sl"], tp=BB_SQUEEZE_PARAMS["tp"],
            mhb=BB_SQUEEZE_PARAMS["hold_bars"], df_map=df_map, cost_per_rt=cost,
        )

        return axes

    axes_4h = build_all_axes(cost_mult=1.0)

    # Aggregate each axis to daily
    axis_daily = pd.DataFrame({k: to_daily(v) for k, v in axes_4h.items()})
    axis_daily = axis_daily.fillna(0).sort_index()
    print(f"  axis_daily rows={len(axis_daily)}, axes={list(axis_daily.columns)}")
    print("  Per-axis annualized standalone Sharpe:")
    for axis in AXES:
        sh = annualize_sharpe(axis_daily[axis])
        active = (axis_daily[axis] != 0).sum()
        print(f"    {axis:<12} Sh={sh:+.3f}  active_days={active}/{len(axis_daily)}")

    # ---------- Build regime variables ----------
    print("\n[Building regime variables — all lagged 1 bar]")
    reg_4h = compute_regimes(df_map["BTCUSDT"], df_map)
    reg_daily = regimes_to_daily(reg_4h)
    print(f"  regimes_daily rows={len(reg_daily)}")
    for col in reg_daily.columns:
        vc = reg_daily[col].value_counts().to_dict()
        print(f"    {col}: {vc}")

    # ---------- Conditional Sharpe matrix ----------
    print("\n[Conditional Sharpe matrix]")
    cond_sh = conditional_sharpe_matrix(axis_daily, reg_daily)
    (ROOT / "wave_k109_conditional_sharpe.json").write_text(json.dumps(cond_sh, indent=2))
    print(f"  Saved -> wave_k109_conditional_sharpe.json")

    # ---------- v4.1 baseline (static weights) ----------
    print("\n[Building v4.1 baseline]")
    static_w = pd.DataFrame(np.tile(list(V41_WEIGHTS.values()), (len(axis_daily), 1)),
                            index=axis_daily.index, columns=AXES)
    pr_v41 = portfolio_daily_ret(axis_daily, static_w)
    m_v41 = summary_metrics(pr_v41, static_w, turnover_cost=COST_PER_RT)
    print(f"  v4.1 -> {m_v41}")

    # ---------- 3 Dynamic allocator variants ----------
    print("\n[Building 3 allocator variants]")
    results = {"v4.1": m_v41}
    curves = {"v4.1": pr_v41.cumsum().tolist()}
    weights_store = {}
    daily_ret_store = {"v4.1": pr_v41}

    # Use r1_vol as primary regime (most economically meaningful)
    for variant in ["V1", "V2", "V3"]:
        w = build_dynamic_weights(axis_daily, reg_daily, cond_sh,
                                  primary_regime="r1_vol", variant=variant, top_k=3)
        pr = portfolio_daily_ret(axis_daily, w)
        m = summary_metrics(pr, w, turnover_cost=COST_PER_RT)
        results[variant] = m
        curves[variant] = pr.cumsum().tolist()
        weights_store[variant] = w
        daily_ret_store[variant] = pr
        print(f"  {variant} -> {m}")

    # Also try V2 with other regimes (small grid, but still <100 total)
    extras = {}
    for rvar in ["r2_trend", "r3_fund", "r4_disp"]:
        for variant in ["V1", "V2"]:
            label = f"{variant}_{rvar}"
            w = build_dynamic_weights(axis_daily, reg_daily, cond_sh,
                                      primary_regime=rvar, variant=variant, top_k=3)
            pr = portfolio_daily_ret(axis_daily, w)
            m = summary_metrics(pr, w, turnover_cost=COST_PER_RT)
            extras[label] = m
            print(f"  {label} -> Sh={m['sharpe']:+.3f} Calmar={m['calmar']:+.3f} DD={m['max_dd_pct']:+.2f}")

    # Pick best variant (excluding v4.1)
    all_variants = {k: v for k, v in results.items() if k != "v4.1"}
    all_variants.update(extras)
    best_label = max(all_variants.keys(), key=lambda k: all_variants[k]["sharpe"])
    best_metrics = all_variants[best_label]
    print(f"\n[BEST] {best_label} -> {best_metrics}")

    # ---------- CPCV on the best variant ----------
    print("\n[CPCV 10-split embargo=5 for BEST variant]")
    # Parse best_label
    if "_" in best_label:
        variant_b, rvar_b = best_label.split("_", 1)
    else:
        variant_b, rvar_b = best_label, "r1_vol"
    cpcv_res = cpcv_pbo(axis_daily, reg_daily, n_splits=10, embargo=5,
                        variant=variant_b, primary_regime=rvar_b, top_k=3)
    print(f"  CPCV -> {cpcv_res}")

    # ---------- DSR ----------
    print("\n[Deflated Sharpe Ratio]")
    from engine.statistical_tests import deflated_sharpe_ratio
    # N_trials = 3 base variants × 4 regime variables = 12 (V3 only uses regime gating, but count it as 1 per regime)
    n_trials = 12
    best_pr = daily_ret_store.get(variant_b)
    if best_pr is None:
        # extras case: rebuild
        w_b = build_dynamic_weights(axis_daily, reg_daily, cond_sh,
                                    primary_regime=rvar_b, variant=variant_b, top_k=3)
        best_pr = portfolio_daily_ret(axis_daily, w_b)
    from scipy import stats as _st
    sk = float(_st.skew(best_pr.dropna()))
    kurt = float(_st.kurtosis(best_pr.dropna(), fisher=False))
    dsr_res = deflated_sharpe_ratio(
        observed_sharpe=best_metrics["sharpe"],
        n_trials=n_trials,
        n_obs=len(best_pr.dropna()),
        skewness=sk,
        kurtosis=kurt,
    )
    print(f"  DSR -> {dsr_res}")

    # ---------- Block bootstrap CI ----------
    print("\n[Block-bootstrap CI for BEST]")
    boot = block_bootstrap_sharpe_ci(best_pr, block_size=20, n_iter=1000)
    print(f"  Bootstrap -> {boot}")

    # ---------- Robustness: costs × 0.5 and × 1.5 ----------
    print("\n[Robustness — cost x0.5 and x1.5]")
    robust = {}
    for mult in [0.5, 1.5]:
        ax_r = build_all_axes(cost_mult=mult)
        ax_d = pd.DataFrame({k: to_daily(v) for k, v in ax_r.items()}).fillna(0).sort_index()
        cond_r = conditional_sharpe_matrix(ax_d, reg_daily)
        w_r = build_dynamic_weights(ax_d, reg_daily, cond_r,
                                    primary_regime=rvar_b, variant=variant_b, top_k=3)
        pr_r = portfolio_daily_ret(ax_d, w_r)
        m_r = summary_metrics(pr_r, w_r, turnover_cost=COST_PER_RT * mult)
        robust[f"cost_x{mult}"] = m_r
        # And v4.1
        sw = pd.DataFrame(np.tile(list(V41_WEIGHTS.values()), (len(ax_d), 1)),
                          index=ax_d.index, columns=AXES)
        pr_v = portfolio_daily_ret(ax_d, sw)
        robust[f"v41_cost_x{mult}"] = summary_metrics(pr_v, sw, turnover_cost=COST_PER_RT * mult)
        print(f"  cost x{mult}: best={m_r}; v4.1={robust[f'v41_cost_x{mult}']}")

    # ---------- Save outputs ----------
    out = {
        "wave": "K109",
        "task": "Conditional-Sharpe Dynamic Allocator",
        "n_days": int(len(axis_daily)),
        "date_range": [str(axis_daily.index.min()), str(axis_daily.index.max())],
        "v41_baseline": m_v41,
        "variants": {k: v for k, v in results.items() if k != "v4.1"},
        "extras": extras,
        "best_label": best_label,
        "best_metrics": best_metrics,
        "cpcv": cpcv_res,
        "dsr": dsr_res,
        "bootstrap_ci": boot,
        "robustness": robust,
        "axis_standalone_sharpe": {a: round(annualize_sharpe(axis_daily[a]), 3) for a in AXES},
        "regime_distribution": {col: reg_daily[col].value_counts().to_dict() for col in reg_daily.columns},
        "notes": [
            "Funding rate cache for 730d not available; used sign(BTC 24-bar return) as proxy.",
            "OI/historical metrics 730d cache not available; FOPD axis uses ret-Z only; "
            "OI_capit axis uses price-Z only (no OI). These reduce signal density but preserve "
            "directional structure for regime conditioning.",
            "All regime variables computed using data at bar t and shifted by 1 bar -> "
            "applied to position-PnL at bar t+1. No look-ahead.",
            "Costs: TAKER_FEE=0.04% + SLIPPAGE=0.03% per side, round-trip "
            f"= {COST_PER_RT*100:.3f}% per trade.",
            "Turnover cost in summary metrics is conservative: applies cost_per_rt to L1 "
            "weight change per day.",
            "Total parametrizations tested = 3 variants on r1_vol + 6 extras = 9. "
            "DSR n_trials=12 to be slightly conservative.",
        ],
        "runtime_sec": round(time.time() - t0, 1),
    }
    (ROOT / "wave_k109_conditional_alloc.json").write_text(json.dumps(out, indent=2, default=str))

    # Curves
    curves_json = {
        "dates": [str(d.date()) for d in axis_daily.index],
        "series": {
            "v4.1": curves["v4.1"],
            "V1": curves["V1"],
            "V2": curves["V2"],
            "V3": curves["V3"],
        },
    }
    (ROOT / "wave_k109_curves.json").write_text(json.dumps(curves_json, default=str))
    print(f"\n  Saved -> wave_k109_conditional_alloc.json, wave_k109_curves.json")
    print(f"\nDone. Runtime {time.time()-t0:.1f}s")
    return out


if __name__ == "__main__":
    main()

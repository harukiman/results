"""Trading strategies v6 — optimized for profitability after fees.

Signal: 1=long, -1=short, 0=flat, 2=hold (no change)

Design principles:
- Entry conditions: 2-3 filters max (not 4-5) to get 10-30 trades/month
- RSI: 30/70 for reversal (not 20/80), 45/55 for trend
- Volume: 1.3x avg (not 2-3x)
- Risk: TP should be 2-3x SL for asymmetric payoff
- Cooldown: 48-96 bars (4-8h) to allow re-entry
- Target: avg trade > 0.3% to overcome 0.14% fee per trade
"""

import pandas as pd
import numpy as np


# ── Helpers ──────────────────────────────────────────────

def _has_col(df, col):
    return col in df.columns and df[col].notna().sum() > 50

def _ema(s, span):
    return s.ewm(span=span, adjust=False).mean()

def _sma(s, w):
    return s.rolling(w, min_periods=1).mean()

def _rsi(s, p=14):
    d = s.diff()
    g = d.where(d > 0, 0).ewm(span=p, adjust=False).mean()
    l = (-d.where(d < 0, 0)).ewm(span=p, adjust=False).mean()
    return 100 - 100 / (1 + g / l.replace(0, np.nan))

def _atr(df, p=14):
    tr = pd.concat([
        df["high"] - df["low"],
        (df["high"] - df["close"].shift()).abs(),
        (df["low"] - df["close"].shift()).abs(),
    ], axis=1).max(axis=1)
    return tr.ewm(span=p, adjust=False).mean()

def _bbands(s, w=20, n=2.0):
    m = _sma(s, w)
    st = s.rolling(w).std()
    return m - n * st, m, m + n * st

def _macd(s, f=12, sl=26, sg=9):
    ml = _ema(s, f) - _ema(s, sl)
    sl_ = _ema(ml, sg)
    return ml, sl_, ml - sl_

def _adx(df, p=14):
    pdm = df["high"].diff().clip(lower=0)
    ndm = (-df["low"].diff()).clip(lower=0)
    pdm = pdm.where(pdm > ndm, 0)
    ndm = ndm.where(ndm > pdm, 0)
    atr = _atr(df, p)
    pdi = 100 * _ema(pdm, p) / atr.replace(0, np.nan)
    ndi = 100 * _ema(ndm, p) / atr.replace(0, np.nan)
    dx = 100 * (pdi - ndi).abs() / (pdi + ndi).replace(0, np.nan)
    return _ema(dx, p), pdi, ndi

def _obv(df):
    return (np.sign(df["close"].diff()) * df["volume"]).cumsum()

def _stoch_rsi(s, rsi_p=14, stoch_p=14, k_smooth=3):
    rsi = _rsi(s, rsi_p)
    rsi_min = rsi.rolling(stoch_p).min()
    rsi_max = rsi.rolling(stoch_p).max()
    stoch = (rsi - rsi_min) / (rsi_max - rsi_min).replace(0, np.nan) * 100
    k = stoch.rolling(k_smooth).mean()
    d = k.rolling(k_smooth).mean()
    return k, d

def _hull_ma(s, period):
    half_p = max(1, period // 2)
    sqrt_p = max(1, int(np.sqrt(period)))
    wma_half = s.rolling(half_p, min_periods=1).mean()
    wma_full = s.rolling(period, min_periods=1).mean()
    diff = 2 * wma_half - wma_full
    return diff.rolling(sqrt_p, min_periods=1).mean()

def _cci(df, p=20):
    tp = (df["high"] + df["low"] + df["close"]) / 3
    tp_sma = tp.rolling(p).mean()
    tp_mad = tp.rolling(p).apply(lambda x: np.abs(x - x.mean()).mean(), raw=True)
    return (tp - tp_sma) / (0.015 * tp_mad.replace(0, np.nan))

def _supertrend(df, period=10, multiplier=3.0):
    atr = _atr(df, period)
    hl2 = (df["high"] + df["low"]) / 2
    up = (hl2 + multiplier * atr).values
    lo = (hl2 - multiplier * atr).values
    c = df["close"].values
    d = np.ones(len(df))
    for i in range(1, len(df)):
        if c[i] > up[i - 1]:
            d[i] = 1
        elif c[i] < lo[i - 1]:
            d[i] = -1
        else:
            d[i] = d[i - 1]
            if d[i] == 1:
                lo[i] = max(lo[i], lo[i - 1])
            else:
                up[i] = min(up[i], up[i - 1])
    return pd.Series(d.astype(int), index=df.index)

def _rolling_vwap(df, period=48):
    tp = (df["high"] + df["low"] + df["close"]) / 3
    cum_vol = df["volume"].rolling(period, min_periods=1).sum()
    cum_tp_vol = (tp * df["volume"]).rolling(period, min_periods=1).sum()
    return cum_tp_vol / cum_vol.replace(0, np.nan)

def _chaikin_mf(df, p=20):
    mfm = ((df["close"] - df["low"]) - (df["high"] - df["close"])) / (df["high"] - df["low"]).replace(0, np.nan)
    mfv = mfm * df["volume"]
    return mfv.rolling(p).sum() / df["volume"].rolling(p).sum().replace(0, np.nan)


# ── Multi-timeframe helpers (resample 15m → 1h/4h) ──────

def _resample_ohlcv(df, factor):
    """Resample by grouping every `factor` bars (e.g., 4 for 15m→1h)."""
    n = len(df)
    groups = np.arange(n) // factor
    res = df.groupby(groups).agg({
        "open": "first", "high": "max", "low": "min",
        "close": "last", "volume": "sum",
    })
    # Broadcast back to original index
    result = {}
    for col in res.columns:
        vals = res[col].values
        result[col] = vals[groups[:len(vals) if len(groups) <= len(vals) * factor else len(groups)]]
    out = pd.DataFrame(result, index=df.index[:len(result["close"])])
    return out


def _mtf_trend(df, factor, ema_period=50):
    """Get higher-timeframe trend direction: 1=bull, -1=bear, 0=neutral."""
    res = _resample_ohlcv(df, factor)
    ema = _ema(res["close"], ema_period // factor or 1)
    adx_df = pd.DataFrame({"high": res["high"], "low": res["low"], "close": res["close"]}, index=res.index)
    adx_val, pdi, ndi = _adx(adx_df, 14)

    trend = pd.Series(0, index=df.index)
    bull = (res["close"] > ema) & (pdi > ndi)
    bear = (res["close"] < ema) & (ndi > pdi)
    # Align to original index
    trend.iloc[:len(bull)] = np.where(bull, 1, np.where(bear, -1, 0))
    return trend


def _mtf_features(df):
    """Add 1h and 4h trend columns to dataframe."""
    out = df.copy()
    out["trend_1h"] = _mtf_trend(df, 4, 50)   # 15m × 4 = 1h
    out["trend_4h"] = _mtf_trend(df, 16, 50)   # 15m × 16 = 4h

    # 1h RSI
    res_1h = _resample_ohlcv(df, 4)
    rsi_1h = _rsi(res_1h["close"], 14)
    out["rsi_1h"] = rsi_1h.reindex(df.index, method="ffill")

    # 4h RSI
    res_4h = _resample_ohlcv(df, 16)
    rsi_4h = _rsi(res_4h["close"], 14)
    out["rsi_4h"] = rsi_4h.reindex(df.index, method="ffill")

    return out


# ── Signal cleaner ───────────────────────────────────────

def _clean_ls(signals):
    c = signals.values.copy()
    pos = 0
    for i in range(len(c)):
        s = c[i]
        if s == pos and pos != 0:
            c[i] = 2
        elif s != 0:
            pos = s
        else:
            if pos != 0:
                pos = 0
            else:
                c[i] = 2
    return pd.Series(c, index=signals.index)


# ═════════════════════════════════════════════════════════
#  GROUP 1: CRYPTO DERIVATIVES — leveraging on-chain/derivatives data
# ═════════════════════════════════════════════════════════

def funding_carry(df, z_thresh=1.5, rsi_filter=55):
    """Go long when funding deeply negative (get paid + mean reversion).
    Short when funding deeply positive. Pure crypto alpha."""
    if not _has_col(df, "funding_rate"):
        return pd.Series(0, index=df.index)
    fr = df["funding_rate"]
    fr_ma = fr.rolling(64, min_periods=10).mean()
    fr_std = fr.rolling(64, min_periods=10).std().replace(0, np.nan)
    z = (fr - fr_ma) / fr_std
    rsi = _rsi(df["close"], 14)
    adx_val, _, _ = _adx(df)

    signals = pd.Series(0, index=df.index)
    # Negative funding = shorts paying longs → go long (with ADX filter)
    signals[(z < -z_thresh) & (rsi < rsi_filter) & (adx_val < 35)] = 1
    # Positive funding = longs paying shorts → go short
    signals[(z > z_thresh) & (rsi > 100 - rsi_filter) & (adx_val < 35)] = -1
    # Exit when funding normalizes
    signals[(z.abs() < 0.3) & (z.shift().abs() >= 0.3)] = 0
    return _clean_ls(signals)


def oi_liquidation_reversal(df, lookback=24, rsi_thresh=35, price_drop=2.0):
    """Price drops + oversold RSI → reversal. OI drop is bonus confirmation.
    Hybrid: works on OHLCV alone, OI adds conviction."""
    price_change = df["close"].pct_change(lookback) * 100
    rsi = _rsi(df["close"], 14)
    vol_avg = df["volume"].rolling(30).mean()
    high_vol = df["volume"] > vol_avg * 1.3

    signals = pd.Series(0, index=df.index)
    # Large price drop + oversold + volume → reversal long
    signals[(price_change < -price_drop) & (rsi < rsi_thresh) & high_vol] = 1
    # Large price rise + overbought + volume → reversal short
    signals[(price_change > price_drop) & (rsi > 100 - rsi_thresh) & high_vol] = -1

    # Bonus: OI drop makes it stronger (but not required)
    if _has_col(df, "oi"):
        oi_change = df["oi"].pct_change(lookback) * 100
        signals[(oi_change < -1) & (price_change < -1) & (rsi < rsi_thresh + 5)] = 1
        signals[(oi_change < -1) & (price_change > 1) & (rsi > 95 - rsi_thresh)] = -1
    return _clean_ls(signals)


def taker_exhaustion(df, lookback=12, extreme=1.8):
    """Extreme taker buy/sell ratio = exhaustion → contrarian.
    Falls back to RSI+BB when derivatives unavailable."""
    rsi = _rsi(df["close"], 14)
    lower, mid, upper = _bbands(df["close"], 20, 2.0)
    signals = pd.Series(0, index=df.index)

    if _has_col(df, "taker_buy_sell_ratio"):
        mp = min(lookback, max(1, lookback // 2))
        ratio = df["taker_buy_sell_ratio"].rolling(lookback, min_periods=mp).mean()
        signals[(ratio > extreme) & (rsi > 60)] = -1
        signals[(ratio < 1 / extreme) & (rsi < 40)] = 1
        signals[(ratio > 0.9) & (ratio < 1.1) & ((ratio.shift() >= 1.1) | (ratio.shift() <= 0.9))] = 0
    # OHLCV fallback: RSI extreme + BB touch
    signals[(rsi < 25) & (df["close"] < lower)] = 1
    signals[(rsi > 75) & (df["close"] > upper)] = -1
    return _clean_ls(signals)


def oi_price_divergence(df, lookback=36, price_thresh=1.5):
    """Price/volume divergence. OI divergence as bonus.
    Weak rally (low volume) or exhaustion detection."""
    price_change = df["close"].pct_change(lookback) * 100
    rsi = _rsi(df["close"], 14)
    vol_avg = df["volume"].rolling(lookback).mean()
    vol_now = df["volume"].rolling(max(4, lookback // 4)).mean()
    vol_declining = vol_now < vol_avg * 0.8  # volume declining during move

    signals = pd.Series(0, index=df.index)
    # Price rising but volume declining = weak rally → short
    signals[(price_change > price_thresh) & vol_declining & (rsi > 55)] = -1
    # Price dropping but volume declining = weak sell-off → long
    signals[(price_change < -price_thresh) & vol_declining & (rsi < 45)] = 1

    if _has_col(df, "oi"):
        oi_change = df["oi"].pct_change(lookback) * 100
        signals[(price_change > 0.5) & (oi_change < -1) & (rsi > 50)] = -1
        signals[(price_change < -0.5) & (oi_change < -1) & (rsi < 50)] = 1
    return _clean_ls(signals)


def smart_money_composite(df, min_score=2):
    """Combine all derivatives data into a smart money signal.
    Score-based: needs 2+ signals agreeing."""
    bull = pd.Series(0, index=df.index)
    bear = pd.Series(0, index=df.index)

    if _has_col(df, "funding_rate"):
        fr = df["funding_rate"]
        fr_z = (fr - fr.rolling(64, min_periods=10).mean()) / fr.rolling(64, min_periods=10).std().replace(0, np.nan)
        bull += (fr_z < -1.0).astype(int)
        bear += (fr_z > 1.0).astype(int)

    if _has_col(df, "oi"):
        oi_chg = df["oi"].pct_change(24)
        price_chg = df["close"].pct_change(24)
        # OI rising + price rising = strong bull
        bull += ((oi_chg > 0.01) & (price_chg > 0.005)).astype(int)
        bear += ((oi_chg > 0.01) & (price_chg < -0.005)).astype(int)

    if _has_col(df, "taker_buy_sell_ratio"):
        taker = df["taker_buy_sell_ratio"].rolling(12, min_periods=6).mean()
        bull += (taker > 1.3).astype(int)
        bear += (taker < 0.75).astype(int)

    if _has_col(df, "top_long_account"):
        top = df["top_long_account"]
        top_rising = top > top.rolling(24).mean()
        bull += (top_rising & (top > 0.52)).astype(int)
        bear += (~top_rising & (top < 0.48)).astype(int)

    if _has_col(df, "ls_ratio"):
        ls_z = (df["ls_ratio"] - df["ls_ratio"].rolling(96, min_periods=20).mean()) / df["ls_ratio"].rolling(96, min_periods=20).std().replace(0, np.nan)
        # Contrarian: retail extremely long → bear
        bear += (ls_z > 1.5).astype(int)
        bull += (ls_z < -1.5).astype(int)

    signals = pd.Series(0, index=df.index)
    signals[bull >= min_score] = 1
    signals[bear >= min_score] = -1
    return _clean_ls(signals)


def oi_momentum_confirm(df, ema_p=50, vol_mult=1.2):
    """EMA crossover trend following. OI/volume confirm conviction.
    Hybrid: OI is bonus, not required."""
    ema = _ema(df["close"], ema_p)
    adx_val, pdi, ndi = _adx(df)
    vol_avg = df["volume"].rolling(30).mean()
    high_vol = df["volume"] > vol_avg * vol_mult

    above = df["close"] > ema
    below = df["close"] < ema
    cross_up = above & ~above.shift(1, fill_value=False)
    cross_down = below & ~below.shift(1, fill_value=False)

    signals = pd.Series(0, index=df.index)
    signals[cross_up & high_vol & (adx_val > 15) & (pdi > ndi)] = 1
    signals[cross_down & high_vol & (adx_val > 15) & (ndi > pdi)] = -1

    if _has_col(df, "oi"):
        oi_change = df["oi"].pct_change(24) * 100
        signals[cross_up & (oi_change > 0.3) & (adx_val > 12)] = 1
        signals[cross_down & (oi_change > 0.3) & (adx_val > 12)] = -1
    return _clean_ls(signals)


def funding_oi_squeeze(df, rsi_high=68, rsi_low=32, bb_std=2.5):
    """Market overheated detection: RSI extreme + BB extreme + volume surge.
    Funding/OI are bonus signals when available."""
    rsi = _rsi(df["close"], 14)
    lower, mid, upper = _bbands(df["close"], 20, bb_std)
    vol_avg = df["volume"].rolling(30).mean()
    vol_surge = df["volume"] > vol_avg * 1.5

    signals = pd.Series(0, index=df.index)
    # Overbought squeeze → short
    signals[(rsi > rsi_high) & (df["close"] > upper) & vol_surge] = -1
    # Oversold squeeze → long
    signals[(rsi < rsi_low) & (df["close"] < lower) & vol_surge] = 1
    # Exit at mean
    signals[(rsi > 45) & (rsi < 55) & ((rsi.shift() >= 55) | (rsi.shift() <= 45))] = 0

    if _has_col(df, "funding_rate"):
        fr = df["funding_rate"]
        signals[(fr > 0.0003) & (rsi > 60) & vol_surge] = -1
        signals[(fr < -0.0002) & (rsi < 40) & vol_surge] = 1
    return _clean_ls(signals)


def top_trader_divergence(df, ema_f=12, ema_s=50, adx_min=15):
    """EMA crossover + ADX trend confirmation. Top trader data as bonus.
    Hybrid: OHLCV primary, derivatives secondary."""
    ema_fast = _ema(df["close"], ema_f)
    ema_slow = _ema(df["close"], ema_s)
    adx_val, pdi, ndi = _adx(df)
    vol_avg = df["volume"].rolling(30).mean()
    high_vol = df["volume"] > vol_avg * 1.2

    signals = pd.Series(0, index=df.index)
    bull_cross = (ema_fast > ema_slow) & (ema_fast.shift() <= ema_slow.shift())
    bear_cross = (ema_fast < ema_slow) & (ema_fast.shift() >= ema_slow.shift())

    # Base OHLCV signal
    signals[bull_cross & (adx_val > adx_min) & (pdi > ndi) & high_vol] = 1
    signals[bear_cross & (adx_val > adx_min) & (ndi > pdi) & high_vol] = -1

    # Bonus: top trader divergence when data is varying (not ffilled)
    if _has_col(df, "top_long_account") and _has_col(df, "ls_ratio"):
        top_long = df["top_long_account"]
        top_diff = top_long.diff().abs()
        varying = top_diff > 0  # only use where data is actually changing
        ls = df["ls_ratio"]
        ls_ma = ls.rolling(96, min_periods=10).mean()
        signals[varying & (top_long > 0.54) & (ls < ls_ma * 0.97) & bull_cross] = 1
        signals[varying & (top_long < 0.46) & (ls > ls_ma * 1.03) & bear_cross] = -1
    return _clean_ls(signals)


def oi_velocity(df, fast=12, slow=48, signal_p=12):
    """OI acceleration + trend alignment."""
    if not _has_col(df, "oi"):
        return pd.Series(0, index=df.index)
    oi = df["oi"]
    oi_roc_fast = oi.pct_change(fast)
    oi_roc_slow = oi.pct_change(slow)
    oi_accel = oi_roc_fast - oi_roc_slow
    oi_accel_ma = oi_accel.rolling(signal_p, min_periods=1).mean()
    price_trend = df["close"] > _ema(df["close"], 50)

    signals = pd.Series(0, index=df.index)
    signals[(oi_accel_ma > 0.005) & price_trend] = 1
    signals[(oi_accel_ma > 0.005) & ~price_trend] = -1
    signals[oi_accel_ma < -0.005] = 0
    return _clean_ls(signals)


def taker_oi_flow(df, mom_period=16, vol_mult=1.3, adx_min=15):
    """Momentum + volume flow. Taker/OI as bonus when available.
    Hybrid: OHLCV momentum primary, derivatives secondary."""
    mom = df["close"].pct_change(mom_period)
    rsi = _rsi(df["close"], 14)
    vol_avg = df["volume"].rolling(30).mean()
    high_vol = df["volume"] > vol_avg * vol_mult
    adx_val, pdi, ndi = _adx(df)

    signals = pd.Series(0, index=df.index)
    signals[(mom > 0.01) & high_vol & (adx_val > adx_min) & (pdi > ndi)] = 1
    signals[(mom < -0.01) & high_vol & (adx_val > adx_min) & (ndi > pdi)] = -1

    if _has_col(df, "taker_buy_sell_ratio"):
        mp = min(mom_period, max(1, mom_period // 2))
        taker = df["taker_buy_sell_ratio"].rolling(mom_period, min_periods=mp).mean()
        signals[(taker > 1.3) & (mom > 0.005) & high_vol] = 1
        signals[(taker < 0.77) & (mom < -0.005) & high_vol] = -1
    return _clean_ls(signals)


# ═════════════════════════════════════════════════════════
#  GROUP 2: OHLCV STRATEGIES — proven concepts, relaxed filters
# ═════════════════════════════════════════════════════════

def vwap_mean_revert(df, std_mult=2.5, vwap_period=96):
    """VWAP deviation mean reversion — the top performer. Tight entry, wide exit."""
    vwap = _rolling_vwap(df, vwap_period)
    diff = df["close"] - vwap
    diff_std = diff.rolling(200, min_periods=50).std().replace(0, np.nan)
    z = diff / diff_std
    rsi = _rsi(df["close"], 14)
    vol_avg = df["volume"].rolling(30).mean()
    high_vol = df["volume"] > vol_avg * 1.3

    signals = pd.Series(0, index=df.index)
    signals[(z < -std_mult) & (rsi < 30) & high_vol] = 1
    signals[(z > std_mult) & (rsi > 70) & high_vol] = -1
    signals[(z.abs() < 0.3) & (z.shift().abs() >= 0.3)] = 0
    return _clean_ls(signals)


def wide_bb_reversal(df, bb_w=20, bb_std=3.0, rsi_p=14):
    """Very wide Bollinger Band (3σ) reversal. Fewer but very high-quality entries."""
    lower, mid, upper = _bbands(df["close"], bb_w, bb_std)
    rsi = _rsi(df["close"], rsi_p)

    signals = pd.Series(0, index=df.index)
    signals[(df["close"] < lower) & (rsi < 30)] = 1
    signals[(df["close"] > upper) & (rsi > 70)] = -1
    signals[(df["close"] > mid) & (df["close"].shift() < mid.shift())] = 0
    signals[(df["close"] < mid) & (df["close"].shift() > mid.shift())] = 0
    return _clean_ls(signals)


def dual_bb_strategy(df, inner_std=1.5, outer_std=3.0, bb_w=20):
    """Enter at outer BB, exit at inner BB. Structured mean reversion."""
    lower_outer, mid, upper_outer = _bbands(df["close"], bb_w, outer_std)
    lower_inner, _, upper_inner = _bbands(df["close"], bb_w, inner_std)
    rsi = _rsi(df["close"], 14)

    signals = pd.Series(0, index=df.index)
    # Enter at outer band with RSI confirmation
    signals[(df["close"] < lower_outer) & (rsi < 35)] = 1
    signals[(df["close"] > upper_outer) & (rsi > 65)] = -1
    # Exit at inner band (take profit zone)
    signals[(df["close"] > upper_inner) & (df["close"].shift() < upper_inner.shift())] = 0
    signals[(df["close"] < lower_inner) & (df["close"].shift() > lower_inner.shift())] = 0
    return _clean_ls(signals)


def regime_adaptive_v2(df, adx_thresh=28, bb_w=20, rsi_p=14, ema_f=8, ema_s=21):
    """ADX regime detection: trend-follow in trending, mean-revert in ranging."""
    adx_val, pdi, ndi = _adx(df)
    rsi = _rsi(df["close"], rsi_p)
    ema_fast = _ema(df["close"], ema_f)
    ema_slow = _ema(df["close"], ema_s)
    lower, mid, upper = _bbands(df["close"], bb_w, 2.5)
    vol_avg = df["volume"].rolling(30).mean()
    high_vol = df["volume"] > vol_avg * 1.3

    trending = adx_val > adx_thresh
    ranging = ~trending

    signals = pd.Series(0, index=df.index)
    bull_t = trending & (ema_fast > ema_slow) & (pdi > ndi) & high_vol
    bear_t = trending & (ema_fast < ema_slow) & (ndi > pdi) & high_vol
    signals[bull_t & ~bull_t.shift(1, fill_value=False)] = 1
    signals[bear_t & ~bear_t.shift(1, fill_value=False)] = -1
    signals[ranging & (df["close"] < lower) & (rsi < 25) & high_vol] = 1
    signals[ranging & (df["close"] > upper) & (rsi > 75) & high_vol] = -1
    return _clean_ls(signals)


def multi_tf_momentum(df, short_p=16, mid_p=64, long_p=192):
    """All timeframes must agree. Loosened alignment conditions."""
    rsi = _rsi(df["close"], 14)
    ema_mid = _ema(df["close"], mid_p)
    ema_long = _ema(df["close"], long_p)
    mom_short = df["close"].pct_change(short_p)
    adx_val, _, _ = _adx(df)

    signals = pd.Series(0, index=df.index)
    all_bull = ((df["close"] > ema_mid) & (df["close"] > ema_long) &
                (mom_short > 0.005) & (rsi > 45) & (adx_val > 15))
    all_bear = ((df["close"] < ema_mid) & (df["close"] < ema_long) &
                (mom_short < -0.005) & (rsi < 55) & (adx_val > 15))
    signals[all_bull & ~all_bull.shift(1, fill_value=False)] = 1
    signals[all_bear & ~all_bear.shift(1, fill_value=False)] = -1
    signals[~all_bull & ~all_bear] = 0
    return _clean_ls(signals)


def volume_momentum(df, mom_period=20, vol_mult=1.5):
    """Strong momentum + above-average volume. Relaxed from 2.5x to 1.5x."""
    mom = df["close"].pct_change(mom_period)
    vol_avg = df["volume"].rolling(30).mean()
    high_vol = df["volume"] > vol_avg * vol_mult
    rsi = _rsi(df["close"], 14)

    signals = pd.Series(0, index=df.index)
    signals[(mom > 0.015) & high_vol & (rsi > 45) & (rsi < 75)] = 1
    signals[(mom < -0.015) & high_vol & (rsi < 55) & (rsi > 25)] = -1
    return _clean_ls(signals)


def order_flow_imbalance(df, period=20, threshold=0.4):
    """Buy/sell pressure estimation from OHLC. Lowered threshold for more trades."""
    rng = (df["high"] - df["low"]).replace(0, np.nan)
    buy_pct = (df["close"] - df["low"]) / rng
    sell_pct = (df["high"] - df["close"]) / rng

    buy_p = (buy_pct * df["volume"]).rolling(period).sum()
    sell_p = (sell_pct * df["volume"]).rolling(period).sum()
    total = (buy_p + sell_p).replace(0, np.nan)
    imbalance = (buy_p - sell_p) / total
    adx_val, _, _ = _adx(df)

    signals = pd.Series(0, index=df.index)
    signals[(imbalance > threshold) & (adx_val > 15)] = 1
    signals[(imbalance < -threshold) & (adx_val > 15)] = -1
    return _clean_ls(signals)


def volatility_breakout(df, bb_w=20, squeeze_pct=20, lookback=10):
    """BB squeeze then breakout. Loosened conditions."""
    lower, mid, upper = _bbands(df["close"], bb_w)
    bw = (upper - lower) / mid.replace(0, np.nan)
    bw_q = bw.rolling(200, min_periods=50).quantile(squeeze_pct / 100)
    in_squeeze = bw < bw_q
    momentum = df["close"].pct_change(lookback)

    signals = pd.Series(0, index=df.index)
    squeeze_exit = in_squeeze.shift() & ~in_squeeze
    signals[squeeze_exit & (momentum > 0.003)] = 1
    signals[squeeze_exit & (momentum < -0.003)] = -1
    return _clean_ls(signals)


def trend_momentum(df, trend_ema=80, fast_ema=8, slow_ema=21, adx_min=20):
    """Trend + EMA crossover. Loosened ADX and trend EMA."""
    trend = _ema(df["close"], trend_ema)
    ema_f = _ema(df["close"], fast_ema)
    ema_s = _ema(df["close"], slow_ema)
    adx_val, pdi, ndi = _adx(df)

    uptrend = (df["close"] > trend) & (adx_val > adx_min)
    downtrend = (df["close"] < trend) & (adx_val > adx_min)
    bull_cross = (ema_f > ema_s) & (ema_f.shift() <= ema_s.shift())
    bear_cross = (ema_f < ema_s) & (ema_f.shift() >= ema_s.shift())

    signals = pd.Series(0, index=df.index)
    signals[uptrend & bull_cross] = 1
    signals[downtrend & bear_cross] = -1
    signals[uptrend & bear_cross] = 0
    signals[downtrend & bull_cross] = 0
    return _clean_ls(signals)


def daily_ema_trend(df, fast_p=96, slow_p=192):
    """Slow EMA crossover for multi-day trends. Very low frequency."""
    ema_f = _ema(df["close"], fast_p)
    ema_s = _ema(df["close"], slow_p)
    adx_val, pdi, ndi = _adx(df, 20)

    signals = pd.Series(0, index=df.index)
    cross_up = (ema_f > ema_s) & (ema_f.shift() <= ema_s.shift())
    cross_down = (ema_f < ema_s) & (ema_f.shift() >= ema_s.shift())
    signals[cross_up & (adx_val > 12) & (pdi > ndi)] = 1
    signals[cross_down & (adx_val > 12) & (ndi > pdi)] = -1
    return _clean_ls(signals)


def relative_volume_breakout(df, lookback=20, vol_mult=2.0, atr_mult=1.5):
    """High relative volume + big price move. Lowered thresholds."""
    vol_avg = df["volume"].rolling(lookback).mean()
    vol_ratio = df["volume"] / vol_avg.replace(0, np.nan)
    atr = _atr(df, lookback)
    price_move = df["close"] - df["close"].shift()

    signals = pd.Series(0, index=df.index)
    signals[(price_move > atr * atr_mult) & (vol_ratio > vol_mult)] = 1
    signals[(price_move < -atr * atr_mult) & (vol_ratio > vol_mult)] = -1
    return _clean_ls(signals)


def keltner_breakout(df, ema_p=20, atr_p=14, mult=2.5):
    """Keltner channel breakout with volume + ADX confirmation."""
    ema = _ema(df["close"], ema_p)
    atr = _atr(df, atr_p)
    upper = ema + mult * atr
    lower = ema - mult * atr
    adx_val, _, _ = _adx(df)
    vol_avg = df["volume"].rolling(30).mean()
    high_vol = df["volume"] > vol_avg * 1.5

    signals = pd.Series(0, index=df.index)
    signals[(df["close"] > upper) & (df["close"].shift() <= upper.shift()) & high_vol & (adx_val > 18)] = 1
    signals[(df["close"] < lower) & (df["close"].shift() >= lower.shift()) & high_vol & (adx_val > 18)] = -1
    signals[(df["close"] < ema) & (df["close"].shift() > ema.shift())] = 0
    signals[(df["close"] > ema) & (df["close"].shift() < ema.shift())] = 0
    return _clean_ls(signals)


def macd_zero_cross(df, fast=12, slow=26, signal=9):
    """MACD zero cross with volume + ADX confirmation. Tighter filters."""
    ml, sl_, hist = _macd(df["close"], fast, slow, signal)
    ema50 = _ema(df["close"], 50)
    adx_val, _, _ = _adx(df)
    vol_avg = df["volume"].rolling(30).mean()
    high_vol = df["volume"] > vol_avg * 1.3

    signals = pd.Series(0, index=df.index)
    signals[(ml > 0) & (ml.shift() <= 0) & (ml > sl_) & (df["close"] > ema50) & high_vol & (adx_val > 18)] = 1
    signals[(ml < 0) & (ml.shift() >= 0) & (ml < sl_) & (df["close"] < ema50) & high_vol & (adx_val > 18)] = -1
    return _clean_ls(signals)


def rsi_mean_revert(df, rsi_p=14, entry_lo=22, entry_hi=78, exit_lo=45, exit_hi=55):
    """Pure RSI mean reversion with tight entry zones + volume confirmation."""
    rsi = _rsi(df["close"], rsi_p)
    ema50 = _ema(df["close"], 50)
    vol_avg = df["volume"].rolling(30).mean()
    high_vol = df["volume"] > vol_avg * 1.5

    signals = pd.Series(0, index=df.index)
    signals[(rsi < entry_lo) & (df["close"] > ema50 * 0.97) & high_vol] = 1
    signals[(rsi > entry_hi) & (df["close"] < ema50 * 1.03) & high_vol] = -1
    signals[(rsi > exit_lo) & (rsi < exit_hi) & (rsi.shift() <= exit_lo)] = 0
    signals[(rsi > exit_lo) & (rsi < exit_hi) & (rsi.shift() >= exit_hi)] = 0
    return _clean_ls(signals)


def obv_divergence(df, lookback=30):
    """OBV divergence from price — volume precedes price. Tight RSI filter."""
    obv = _obv(df)
    obv_ema = _ema(obv, lookback)
    price_ema = _ema(df["close"], lookback)
    rsi = _rsi(df["close"], 14)
    vol_avg = df["volume"].rolling(30).mean()
    high_vol = df["volume"] > vol_avg * 1.5

    obv_up = obv > obv_ema
    price_down = df["close"] < price_ema
    obv_down = obv < obv_ema
    price_up = df["close"] > price_ema

    signals = pd.Series(0, index=df.index)
    signals[obv_up & price_down & (rsi < 30) & high_vol] = 1
    signals[obv_down & price_up & (rsi > 70) & high_vol] = -1
    return _clean_ls(signals)


def volume_climax_reversal(df, vol_mult=2.5, lookback=5):
    """Massive volume spike often signals exhaustion/reversal."""
    vol_avg = df["volume"].rolling(50).mean()
    vol_spike = df["volume"] > vol_avg * vol_mult
    # Price direction during spike
    price_change = df["close"].pct_change(lookback)
    rsi = _rsi(df["close"], 14)

    signals = pd.Series(0, index=df.index)
    # Big sell-off with volume climax → reversal long
    signals[vol_spike & (price_change < -0.01) & (rsi < 35)] = 1
    # Big rally with volume climax → reversal short
    signals[vol_spike & (price_change > 0.01) & (rsi > 65)] = -1
    return _clean_ls(signals)


def momentum_persistence(df, periods=6, threshold=0.001):
    """N consecutive bars in same direction = momentum. Ride it."""
    returns = df["close"].pct_change()

    pos_streak = pd.Series(0, index=df.index)
    neg_streak = pd.Series(0, index=df.index)
    for i in range(1, periods + 1):
        pos_streak += (returns.shift(i - 1) > threshold).astype(int)
        neg_streak += (returns.shift(i - 1) < -threshold).astype(int)

    adx_val, _, _ = _adx(df)
    signals = pd.Series(0, index=df.index)
    signals[(pos_streak >= periods - 1) & (adx_val > 15)] = 1
    signals[(neg_streak >= periods - 1) & (adx_val > 15)] = -1
    return _clean_ls(signals)


def price_structure(df, lookback=48):
    """Higher lows / lower highs structure detection. Relaxed filters."""
    low_min = df["low"].rolling(lookback).min()
    high_max = df["high"].rolling(lookback).max()
    prev_low_min = df["low"].shift(lookback).rolling(lookback).min()
    prev_high_max = df["high"].shift(lookback).rolling(lookback).max()

    higher_lows = low_min > prev_low_min
    lower_highs = high_max < prev_high_max

    rsi = _rsi(df["close"], 14)
    adx_val, pdi, ndi = _adx(df)
    signals = pd.Series(0, index=df.index)
    hl_start = higher_lows & ~higher_lows.shift(1, fill_value=False)
    lh_start = lower_highs & ~lower_highs.shift(1, fill_value=False)
    signals[hl_start & (rsi > 35) & (rsi < 65) & (pdi > ndi)] = 1
    signals[lh_start & (rsi < 65) & (rsi > 35) & (ndi > pdi)] = -1
    return _clean_ls(signals)


def adaptive_ma_cross(df, base_period=20, vol_lookback=100):
    """MA periods adapt to volatility. Volume + ADX filter to reduce noise."""
    atr = _atr(df, 14)
    atr_pct = atr / df["close"]
    atr_rank = atr_pct.rolling(vol_lookback, min_periods=20).rank(pct=True)

    fast_lo = _ema(df["close"], max(5, base_period // 2))
    fast_hi = _ema(df["close"], base_period)
    slow_lo = _ema(df["close"], base_period)
    slow_hi = _ema(df["close"], base_period * 2)

    calm = atr_rank < 0.4
    fast = fast_lo.where(calm, fast_hi)
    slow = slow_lo.where(calm, slow_hi)
    adx_val, _, _ = _adx(df)
    vol_avg = df["volume"].rolling(30).mean()
    high_vol = df["volume"] > vol_avg * 1.3

    signals = pd.Series(0, index=df.index)
    cross_up = (fast > slow) & (fast.shift() <= slow.shift())
    cross_down = (fast < slow) & (fast.shift() >= slow.shift())
    signals[cross_up & high_vol & (adx_val > 18)] = 1
    signals[cross_down & high_vol & (adx_val > 18)] = -1
    return _clean_ls(signals)


# ═════════════════════════════════════════════════════════
#  GROUP 3: SWING STRATEGIES (hold 1-5 days, big targets)
# ═════════════════════════════════════════════════════════

def swing_vwap_oi(df, vwap_period=96, std_mult=2.0):
    """Swing VWAP deviation + OI confirmation. Designed for multi-day holds."""
    vwap = _rolling_vwap(df, vwap_period)
    diff = df["close"] - vwap
    diff_std = diff.rolling(200, min_periods=50).std().replace(0, np.nan)
    z = diff / diff_std
    rsi = _rsi(df["close"], 14)

    signals = pd.Series(0, index=df.index)
    signals[(z < -std_mult) & (rsi < 35)] = 1
    signals[(z > std_mult) & (rsi > 65)] = -1
    signals[(z.abs() < 0.3)] = 0
    return _clean_ls(signals)


def swing_range_breakout(df, range_period=96, confirm_bars=2, vol_mult=1.2):
    """Break of multi-day range with persistence confirmation. Relaxed."""
    high_r = df["high"].rolling(range_period).max()
    low_r = df["low"].rolling(range_period).min()
    vol_avg = df["volume"].rolling(50).mean()
    high_vol = df["volume"] > vol_avg * vol_mult
    above = df["close"] > high_r.shift()
    below = df["close"] < low_r.shift()
    confirmed_up = above.rolling(confirm_bars).min().astype(bool)
    confirmed_down = below.rolling(confirm_bars).min().astype(bool)
    adx_val, _, _ = _adx(df)

    signals = pd.Series(0, index=df.index)
    signals[confirmed_up & high_vol & (adx_val > 15)] = 1
    signals[confirmed_down & high_vol & (adx_val > 15)] = -1
    return _clean_ls(signals)


def multi_indicator_swing(df, ema_p=200, rsi_p=14, bb_w=50, bb_std=2.0):
    """Multiple indicators must agree for swing entry. High conviction."""
    ema = _ema(df["close"], ema_p)
    rsi = _rsi(df["close"], rsi_p)
    lower, mid, upper = _bbands(df["close"], bb_w, bb_std)
    macd_l, macd_s, macd_h = _macd(df["close"])

    bull_score = pd.Series(0, index=df.index)
    bull_score += (df["close"] > ema).astype(int)
    bull_score += (rsi > 40).astype(int) + (rsi < 65).astype(int)
    bull_score += (macd_h > 0).astype(int)
    bull_score += (df["close"] > lower).astype(int)

    bear_score = pd.Series(0, index=df.index)
    bear_score += (df["close"] < ema).astype(int)
    bear_score += (rsi < 60).astype(int) + (rsi > 35).astype(int)
    bear_score += (macd_h < 0).astype(int)
    bear_score += (df["close"] < upper).astype(int)

    signals = pd.Series(0, index=df.index)
    signals[(bull_score >= 4) & ~(bull_score.shift(1) >= 4)] = 1
    signals[(bear_score >= 4) & ~(bear_score.shift(1) >= 4)] = -1
    return _clean_ls(signals)


def funding_swing(df, funding_lookback=64, price_lookback=64, z_thresh=1.2):
    """Sustained funding extreme + price divergence for swing trades."""
    if not _has_col(df, "funding_rate"):
        return pd.Series(0, index=df.index)
    fr = df["funding_rate"]
    fr_avg = fr.rolling(funding_lookback, min_periods=10).mean()
    fr_std = fr.rolling(funding_lookback, min_periods=10).std().replace(0, np.nan)
    fr_z = (fr - fr_avg) / fr_std
    price_mom = df["close"].pct_change(price_lookback)
    rsi = _rsi(df["close"], 14)

    signals = pd.Series(0, index=df.index)
    # High positive funding + price weakening = swing short
    signals[(fr_z > z_thresh) & (price_mom < 0.005) & (rsi > 45)] = -1
    # Negative funding + price strengthening = swing long
    signals[(fr_z < -z_thresh) & (price_mom > -0.005) & (rsi < 55)] = 1
    return _clean_ls(signals)


def cci_reversal(df, cci_p=20, entry=120, exit_zone=30):
    """CCI extreme → mean reversion. Designed for swing holds."""
    cci = _cci(df, cci_p)
    ema50 = _ema(df["close"], 50)

    signals = pd.Series(0, index=df.index)
    # CCI extremely overbought + starting to turn down
    signals[(cci > entry) & (cci < cci.shift()) & (cci.shift() > cci.shift(2))] = -1
    # CCI extremely oversold + starting to turn up
    signals[(cci < -entry) & (cci > cci.shift()) & (cci.shift() < cci.shift(2))] = 1
    # Exit near zero
    signals[(cci > -exit_zone) & (cci < exit_zone) & ((cci.shift() <= -exit_zone) | (cci.shift() >= exit_zone))] = 0
    return _clean_ls(signals)


# ═════════════════════════════════════════════════════════
#  GROUP 4: HYBRID STRATEGIES (OHLCV + Derivatives combined)
# ═════════════════════════════════════════════════════════

def vwap_funding_combo(df, vwap_period=96, std_mult=2.0):
    """VWAP mean reversion. Funding rate as optional boost."""
    vwap = _rolling_vwap(df, vwap_period)
    diff = df["close"] - vwap
    diff_std = diff.rolling(200, min_periods=50).std().replace(0, np.nan)
    z = diff / diff_std
    rsi = _rsi(df["close"], 14)
    vol_avg = df["volume"].rolling(30).mean()
    high_vol = df["volume"] > vol_avg * 1.2

    signals = pd.Series(0, index=df.index)
    # Base VWAP mean reversion (symmetric)
    signals[(z < -std_mult) & (rsi < 38) & high_vol] = 1
    signals[(z > std_mult) & (rsi > 62) & high_vol] = -1

    # Funding boost (only where data is varying)
    if _has_col(df, "funding_rate"):
        fr = df["funding_rate"]
        fr_diff = fr.diff().abs()
        varying = fr_diff > 0
        signals[varying & (z < -std_mult * 0.8) & (rsi < 42) & (fr < 0)] = 1
        signals[varying & (z > std_mult * 0.8) & (rsi > 58) & (fr > 0)] = -1

    signals[(z.abs() < 0.5)] = 0
    return _clean_ls(signals)


def bb_oi_reversal(df, bb_w=20, bb_std=2.5, rsi_lo=32, rsi_hi=68):
    """BB extreme + RSI reversal. OI drop is bonus, not required."""
    lower, mid, upper = _bbands(df["close"], bb_w, bb_std)
    rsi = _rsi(df["close"], 14)
    vol_avg = df["volume"].rolling(30).mean()
    high_vol = df["volume"] > vol_avg * 1.2

    signals = pd.Series(0, index=df.index)
    signals[(df["close"] < lower) & (rsi < rsi_lo) & high_vol] = 1
    signals[(df["close"] > upper) & (rsi > rsi_hi) & high_vol] = -1

    if _has_col(df, "oi"):
        oi_chg = df["oi"].pct_change(24) * 100
        signals[(df["close"] < lower) & (rsi < rsi_lo + 5) & (oi_chg < -0.3)] = 1
        signals[(df["close"] > upper) & (rsi > rsi_hi - 5) & (oi_chg < -0.3)] = -1

    signals[(df["close"] > mid) & (df["close"].shift() < mid.shift())] = 0
    signals[(df["close"] < mid) & (df["close"].shift() > mid.shift())] = 0
    return _clean_ls(signals)


def momentum_oi_filter(df, mom_period=16, mom_thresh=0.01, adx_min=18):
    """Strong momentum + trend confirmation. OI as bonus filter."""
    mom = df["close"].pct_change(mom_period)
    rsi = _rsi(df["close"], 14)
    adx_val, pdi, ndi = _adx(df)
    vol_avg = df["volume"].rolling(30).mean()
    high_vol = df["volume"] > vol_avg * 1.2

    signals = pd.Series(0, index=df.index)
    signals[(mom > mom_thresh) & (adx_val > adx_min) & (pdi > ndi) & high_vol & (rsi > 45) & (rsi < 72)] = 1
    signals[(mom < -mom_thresh) & (adx_val > adx_min) & (ndi > pdi) & high_vol & (rsi < 55) & (rsi > 28)] = -1

    if _has_col(df, "oi"):
        oi_chg = df["oi"].pct_change(mom_period) * 100
        signals[(mom > mom_thresh * 0.7) & (oi_chg > 0.2) & (pdi > ndi)] = 1
        signals[(mom < -mom_thresh * 0.7) & (oi_chg > 0.2) & (ndi > pdi)] = -1
    return _clean_ls(signals)


def ensemble_deriv_ohlcv(df, min_score=3):
    """Ensemble: mix of OHLCV and derivatives signals via scoring.
    Balanced bull/bear scoring with trend alignment required."""
    bull = pd.Series(0, index=df.index)
    bear = pd.Series(0, index=df.index)

    rsi = _rsi(df["close"], 14)
    macd_l, macd_s, macd_h = _macd(df["close"])
    ema50 = _ema(df["close"], 50)
    adx_val, pdi, ndi = _adx(df)

    # RSI: symmetric thresholds
    bull += (rsi < 35).astype(int)
    bear += (rsi > 65).astype(int)
    # MACD histogram
    bull += (macd_h > 0).astype(int)
    bear += (macd_h < 0).astype(int)
    # EMA trend
    bull += ((df["close"] > ema50) & (pdi > ndi)).astype(int)
    bear += ((df["close"] < ema50) & (ndi > pdi)).astype(int)
    # ADX trending
    bull += (adx_val > 20).astype(int)
    bear += (adx_val > 20).astype(int)

    if _has_col(df, "funding_rate"):
        fr = df["funding_rate"]
        bull += (fr < -0.0001).astype(int)
        bear += (fr > 0.0002).astype(int)

    if _has_col(df, "taker_buy_sell_ratio"):
        taker = df["taker_buy_sell_ratio"].rolling(12, min_periods=4).mean()
        bull += (taker > 1.15).astype(int)
        bear += (taker < 0.87).astype(int)

    signals = pd.Series(0, index=df.index)
    # Only signal on score transitions (not continuous)
    bull_trigger = (bull >= min_score) & ~(bull.shift(1) >= min_score)
    bear_trigger = (bear >= min_score) & ~(bear.shift(1) >= min_score)
    signals[bull_trigger] = 1
    signals[bear_trigger] = -1
    # Exit when score drops
    signals[(bull < min_score - 1) & (bear < min_score - 1)] = 0
    return _clean_ls(signals)


def supertrend_deriv(df, period=10, multiplier=3.0):
    """Supertrend flip signals. OI as bonus confirmation."""
    direction = _supertrend(df, period, multiplier)
    adx_val, pdi, ndi = _adx(df)
    vol_avg = df["volume"].rolling(30).mean()
    high_vol = df["volume"] > vol_avg * 1.2

    signals = pd.Series(0, index=df.index)
    dir_change_up = (direction == 1) & (direction.shift() == -1)
    dir_change_down = (direction == -1) & (direction.shift() == 1)

    # Base: supertrend flip + volume
    signals[dir_change_up & high_vol & (adx_val > 12)] = 1
    signals[dir_change_down & high_vol & (adx_val > 12)] = -1

    if _has_col(df, "oi"):
        oi_chg = df["oi"].pct_change(24) * 100
        signals[dir_change_up & (oi_chg > 0)] = 1
        signals[dir_change_down & (oi_chg > 0)] = -1
    return _clean_ls(signals)


def ichimoku_funding(df, tenkan=9, kijun=26, senkou_b=52):
    """Ichimoku cloud + funding rate for crypto-specific confirmation."""
    tenkan_sen = (df["high"].rolling(tenkan).max() + df["low"].rolling(tenkan).min()) / 2
    kijun_sen = (df["high"].rolling(kijun).max() + df["low"].rolling(kijun).min()) / 2
    senkou_a = ((tenkan_sen + kijun_sen) / 2).shift(kijun)
    senkou_b_line = ((df["high"].rolling(senkou_b).max() + df["low"].rolling(senkou_b).min()) / 2).shift(kijun)

    above_cloud = (df["close"] > senkou_a) & (df["close"] > senkou_b_line)
    below_cloud = (df["close"] < senkou_a) & (df["close"] < senkou_b_line)
    tk_up = (tenkan_sen > kijun_sen) & (tenkan_sen.shift() <= kijun_sen.shift())
    tk_down = (tenkan_sen < kijun_sen) & (tenkan_sen.shift() >= kijun_sen.shift())

    signals = pd.Series(0, index=df.index)

    if _has_col(df, "funding_rate"):
        fr = df["funding_rate"]
        # TK cross above cloud + favorable funding
        signals[tk_up & above_cloud & (fr < 0.0003)] = 1
        signals[tk_down & below_cloud & (fr > -0.0003)] = -1
    else:
        signals[tk_up & above_cloud] = 1
        signals[tk_down & below_cloud] = -1

    signals[tk_down & above_cloud] = 0
    signals[tk_up & below_cloud] = 0
    return _clean_ls(signals)


def mean_revert_taker(df, bb_w=20, bb_std=2.0, rsi_thresh=35):
    """Mean reversion at BB extremes. Taker flow as bonus confirmation."""
    lower, mid, upper = _bbands(df["close"], bb_w, bb_std)
    rsi = _rsi(df["close"], 14)
    vol_avg = df["volume"].rolling(30).mean()
    high_vol = df["volume"] > vol_avg * 1.2

    signals = pd.Series(0, index=df.index)
    signals[(df["close"] < lower) & (rsi < rsi_thresh) & high_vol] = 1
    signals[(df["close"] > upper) & (rsi > 100 - rsi_thresh) & high_vol] = -1

    if _has_col(df, "taker_buy_sell_ratio"):
        mp = min(12, max(1, 6))
        taker = df["taker_buy_sell_ratio"].rolling(12, min_periods=mp).mean()
        signals[(df["close"] < lower) & (rsi < rsi_thresh + 5) & (taker > taker.shift(6))] = 1
        signals[(df["close"] > upper) & (rsi > 95 - rsi_thresh) & (taker < taker.shift(6))] = -1

    signals[(df["close"] > mid) & (df["close"].shift() < mid.shift())] = 0
    signals[(df["close"] < mid) & (df["close"].shift() > mid.shift())] = 0
    return _clean_ls(signals)


# ═════════════════════════════════════════════════════════
#  GROUP 5: Sweet-spot strategies (targeting 30-80 trades, PF > 1.5)
# ═════════════════════════════════════════════════════════

def donchian_confirmed(df, dc_period=72, confirm_bars=2, vol_mult=1.5):
    """Donchian channel breakout with persistence confirmation.
    Like Swing Range Breakout but using Donchian channel. Must hold above/below
    for confirm_bars consecutively to filter fakeouts."""
    high_n = df["high"].rolling(dc_period).max()
    low_n = df["low"].rolling(dc_period).min()
    vol_avg = df["volume"].rolling(50).mean()
    high_vol = df["volume"] > vol_avg * vol_mult

    above = df["close"] > high_n.shift()
    below = df["close"] < low_n.shift()
    confirmed_up = above.rolling(confirm_bars).min().astype(bool)
    confirmed_down = below.rolling(confirm_bars).min().astype(bool)
    adx_val, pdi, ndi = _adx(df)

    signals = pd.Series(0, index=df.index)
    signals[confirmed_up & high_vol & (adx_val > 18) & (pdi > ndi)] = 1
    signals[confirmed_down & high_vol & (adx_val > 18) & (ndi > pdi)] = -1
    signals.iloc[:dc_period + confirm_bars] = 0
    return _clean_ls(signals)


def momentum_burst(df, mom_bars=8, mom_thresh=0.025, vol_mult=2.0):
    """Strong short-term momentum burst with high volume.
    Only fires on extreme moves (2.5%+ in 8 bars) with 2x volume.
    High thresholds = infrequent but high-conviction signals."""
    mom = df["close"].pct_change(mom_bars)
    vol_avg = df["volume"].rolling(50).mean()
    high_vol = df["volume"] > vol_avg * vol_mult
    rsi = _rsi(df["close"], 14)
    adx_val, pdi, ndi = _adx(df)

    signals = pd.Series(0, index=df.index)
    signals[(mom > mom_thresh) & high_vol & (rsi > 50) & (rsi < 80) & (pdi > ndi)] = 1
    signals[(mom < -mom_thresh) & high_vol & (rsi < 50) & (rsi > 20) & (ndi > pdi)] = -1
    signals.iloc[:50] = 0
    return _clean_ls(signals)


def consolidation_breakout(df, lookback=48, range_pct=3.0, vol_mult=1.5):
    """Detect tight consolidation (price within X% range for N bars),
    then trade the breakout with volume. The tighter the range, the
    more explosive the breakout tends to be."""
    rolling_high = df["high"].rolling(lookback).max()
    rolling_low = df["low"].rolling(lookback).min()
    mid = (rolling_high + rolling_low) / 2
    range_ratio = (rolling_high - rolling_low) / mid.replace(0, np.nan) * 100

    tight = range_ratio < range_pct  # consolidation
    was_tight = tight.shift(1, fill_value=False)
    vol_avg = df["volume"].rolling(50).mean()
    high_vol = df["volume"] > vol_avg * vol_mult
    mom = df["close"].pct_change(4)

    signals = pd.Series(0, index=df.index)
    # Breakout from consolidation with volume and momentum
    signals[was_tight & (mom > 0.005) & high_vol & (df["close"] > rolling_high.shift())] = 1
    signals[was_tight & (mom < -0.005) & high_vol & (df["close"] < rolling_low.shift())] = -1
    signals.iloc[:lookback + 1] = 0
    return _clean_ls(signals)


def inside_bar_breakout(df, min_bars=1, vol_mult=1.3):
    """Inside bars (narrowing range) followed by breakout with volume.
    Consolidation → expansion pattern. min_bars=1 for more signals."""
    inside = (df["high"] < df["high"].shift()) & (df["low"] > df["low"].shift())
    ic = np.zeros(len(df))
    ins = inside.values
    for i in range(1, len(df)):
        if ins[i]:
            ic[i] = ic[i - 1] + 1
    inside_count = pd.Series(ic, index=df.index)

    was_inside = inside_count.shift() >= min_bars
    # Mother bar is the bar before the inside sequence
    mother_high = df["high"].shift()
    mother_low = df["low"].shift()
    for i in range(2, min_bars + 4):
        mother_high = mother_high.where(~was_inside, df["high"].shift(i).where(
            df["high"].shift(i) > mother_high, mother_high))
        mother_low = mother_low.where(~was_inside, df["low"].shift(i).where(
            df["low"].shift(i) < mother_low, mother_low))
    vol_avg = df["volume"].rolling(30).mean()
    high_vol = df["volume"] > vol_avg * vol_mult
    adx_val, pdi, ndi = _adx(df)

    signals = pd.Series(0, index=df.index)
    signals[was_inside & (df["close"] > mother_high) & high_vol] = 1
    signals[was_inside & (df["close"] < mother_low) & high_vol] = -1
    return _clean_ls(signals)


def atr_momentum_breakout(df, atr_mult=2.5, mom_bars=6, vol_mult=1.5):
    """Price moves more than ATR_mult * ATR in mom_bars with high volume.
    This captures only genuinely large moves that are likely to continue.
    ATR-normalized so it adapts to current volatility regime."""
    atr = _atr(df, 20)
    price_move = df["close"] - df["close"].shift(mom_bars)
    move_ratio = price_move / atr.replace(0, np.nan)
    vol_avg = df["volume"].rolling(50).mean()
    high_vol = df["volume"] > vol_avg * vol_mult
    adx_val, pdi, ndi = _adx(df)

    signals = pd.Series(0, index=df.index)
    signals[(move_ratio > atr_mult) & high_vol & (adx_val > 18) & (pdi > ndi)] = 1
    signals[(move_ratio < -atr_mult) & high_vol & (adx_val > 18) & (ndi > pdi)] = -1
    signals.iloc[:50] = 0
    return _clean_ls(signals)


# ═════════════════════════════════════════════════════════
#  GROUP 6: MULTI-TIMEFRAME (15m entry, 1h/4h trend filter)
# ═════════════════════════════════════════════════════════

def mtf_trend_breakout(df, dc_period=48, vol_mult=1.3):
    """Donchian breakout on 15m, only in direction of 1h AND 4h trend.
    Filters out counter-trend breakouts which are the main source of fakeouts."""
    mdf = _mtf_features(df)
    high_n = df["high"].rolling(dc_period).max()
    low_n = df["low"].rolling(dc_period).min()
    vol_avg = df["volume"].rolling(50).mean()
    high_vol = df["volume"] > vol_avg * vol_mult

    above = df["close"] > high_n.shift()
    below = df["close"] < low_n.shift()
    # Only enter if both 1h and 4h agree
    trend_bull = (mdf["trend_1h"] == 1) & (mdf["trend_4h"] == 1)
    trend_bear = (mdf["trend_1h"] == -1) & (mdf["trend_4h"] == -1)

    signals = pd.Series(0, index=df.index)
    signals[above & high_vol & trend_bull] = 1
    signals[below & high_vol & trend_bear] = -1
    signals.iloc[:dc_period] = 0
    return _clean_ls(signals)


def mtf_mean_reversion(df, rsi_entry=25, bb_std=2.5):
    """Mean reversion on 15m, but only when 1h trend supports the direction.
    e.g., RSI oversold on 15m + 1h uptrend = buy the dip in a bull market."""
    mdf = _mtf_features(df)
    rsi = _rsi(df["close"], 14)
    lower, mid, upper = _bbands(df["close"], 20, bb_std)
    vol_avg = df["volume"].rolling(30).mean()
    high_vol = df["volume"] > vol_avg * 1.2

    signals = pd.Series(0, index=df.index)
    # Oversold on 15m + 1h uptrend = buy the dip
    signals[(rsi < rsi_entry) & (df["close"] < lower) & (mdf["trend_1h"] == 1) & high_vol] = 1
    # Overbought on 15m + 1h downtrend = sell the rally
    signals[(rsi > 100 - rsi_entry) & (df["close"] > upper) & (mdf["trend_1h"] == -1) & high_vol] = -1
    # Exit at mid BB
    signals[(df["close"] > mid) & (df["close"].shift() < mid.shift())] = 0
    signals[(df["close"] < mid) & (df["close"].shift() > mid.shift())] = 0
    return _clean_ls(signals)


def mtf_momentum_confirm(df, mom_bars=12, mom_thresh=0.008):
    """Short-term momentum on 15m, confirmed by both 1h and 4h trend.
    Triple timeframe alignment = high probability continuation."""
    mdf = _mtf_features(df)
    mom = df["close"].pct_change(mom_bars)
    adx_val, pdi, ndi = _adx(df)
    vol_avg = df["volume"].rolling(30).mean()
    high_vol = df["volume"] > vol_avg * 1.2

    # Triple alignment: 15m momentum + 1h trend + 4h trend
    signals = pd.Series(0, index=df.index)
    signals[(mom > mom_thresh) & high_vol & (pdi > ndi) &
            (mdf["trend_1h"] == 1) & (mdf["trend_4h"] == 1)] = 1
    signals[(mom < -mom_thresh) & high_vol & (ndi > pdi) &
            (mdf["trend_1h"] == -1) & (mdf["trend_4h"] == -1)] = -1
    signals.iloc[:50] = 0
    return _clean_ls(signals)


def mtf_vwap_trend(df, std_mult=2.0, vwap_period=96):
    """VWAP deviation entry, filtered by 4h trend direction.
    Only take mean reversion trades when the higher timeframe supports it."""
    mdf = _mtf_features(df)
    vwap = _rolling_vwap(df, vwap_period)
    diff = df["close"] - vwap
    diff_std = diff.rolling(200, min_periods=50).std().replace(0, np.nan)
    z = diff / diff_std
    rsi = _rsi(df["close"], 14)

    signals = pd.Series(0, index=df.index)
    # Below VWAP + 4h uptrend = buy the dip in bull
    signals[(z < -std_mult) & (rsi < 35) & (mdf["trend_4h"] >= 0)] = 1
    # Above VWAP + 4h downtrend = sell the rally in bear
    signals[(z > std_mult) & (rsi > 65) & (mdf["trend_4h"] <= 0)] = -1
    signals[(z.abs() < 0.3)] = 0
    return _clean_ls(signals)


def mtf_ema_crossover(df, fast_ema=8, slow_ema=21):
    """EMA crossover on 15m, only when 1h and 4h trends both agree.
    Classic trend following with multi-timeframe confirmation."""
    mdf = _mtf_features(df)
    ema_f = _ema(df["close"], fast_ema)
    ema_s = _ema(df["close"], slow_ema)
    adx_val, pdi, ndi = _adx(df)
    vol_avg = df["volume"].rolling(30).mean()
    high_vol = df["volume"] > vol_avg * 1.2

    bull_cross = (ema_f > ema_s) & (ema_f.shift() <= ema_s.shift())
    bear_cross = (ema_f < ema_s) & (ema_f.shift() >= ema_s.shift())

    signals = pd.Series(0, index=df.index)
    signals[bull_cross & high_vol & (adx_val > 15) &
            (mdf["trend_1h"] == 1) & (mdf["trend_4h"] == 1)] = 1
    signals[bear_cross & high_vol & (adx_val > 15) &
            (mdf["trend_1h"] == -1) & (mdf["trend_4h"] == -1)] = -1
    # Counter-trend cross = exit
    signals[bear_cross & (mdf["trend_1h"] == 1)] = 0
    signals[bull_cross & (mdf["trend_1h"] == -1)] = 0
    return _clean_ls(signals)


# ═════════════════════════════════════════════════════════
#  GROUP 7: Round 2 — Variations of top performers
#  Based on: MTF VWAP, Swing Range, Donchian, Consolidation
# ═════════════════════════════════════════════════════════

def vwap_supertrend_mtf(df, vwap_period=96, st_period=10, st_mult=3.0):
    """VWAP mean reversion + Supertrend as trend filter instead of MTF.
    Supertrend gives cleaner trend signals than resampled EMA."""
    vwap = _rolling_vwap(df, vwap_period)
    diff = df["close"] - vwap
    diff_std = diff.rolling(200, min_periods=50).std().replace(0, np.nan)
    z = diff / diff_std
    rsi = _rsi(df["close"], 14)
    st_dir = _supertrend(df, st_period, st_mult)

    signals = pd.Series(0, index=df.index)
    signals[(z < -2.0) & (rsi < 35) & (st_dir == 1)] = 1
    signals[(z > 2.0) & (rsi > 65) & (st_dir == -1)] = -1
    signals[(z.abs() < 0.3)] = 0
    return _clean_ls(signals)


def donchian_adx_tight(df, dc_period=48, adx_min=22, vol_mult=1.3):
    """Donchian breakout with tighter ADX filter. Higher ADX = stronger trend.
    Variant: no persistence confirmation, but stricter ADX + DI spread."""
    high_n = df["high"].rolling(dc_period).max()
    low_n = df["low"].rolling(dc_period).min()
    adx_val, pdi, ndi = _adx(df)
    di_spread = (pdi - ndi).abs()
    vol_avg = df["volume"].rolling(50).mean()
    high_vol = df["volume"] > vol_avg * vol_mult

    signals = pd.Series(0, index=df.index)
    signals[(df["close"] > high_n.shift()) & high_vol & (adx_val > adx_min) & (di_spread > 10) & (pdi > ndi)] = 1
    signals[(df["close"] < low_n.shift()) & high_vol & (adx_val > adx_min) & (di_spread > 10) & (ndi > pdi)] = -1
    signals.iloc[:dc_period] = 0
    return _clean_ls(signals)


def range_break_volume_spike(df, range_period=72, vol_spike=2.5, confirm=2):
    """Range breakout confirmed by volume spike (2.5x+).
    Volume spike = institutional participation."""
    high_r = df["high"].rolling(range_period).max()
    low_r = df["low"].rolling(range_period).min()
    vol_avg = df["volume"].rolling(50).mean()
    spike = df["volume"] > vol_avg * vol_spike
    above = df["close"] > high_r.shift()
    below = df["close"] < low_r.shift()
    confirmed_up = above.rolling(confirm).min().astype(bool)
    confirmed_down = below.rolling(confirm).min().astype(bool)

    signals = pd.Series(0, index=df.index)
    signals[confirmed_up & spike] = 1
    signals[confirmed_down & spike] = -1
    signals.iloc[:range_period + confirm] = 0
    return _clean_ls(signals)


def consolidation_mtf(df, lookback=48, range_pct=3.0, vol_mult=1.5):
    """Consolidation breakout + 1h trend filter.
    Only break out in the higher TF trend direction."""
    mdf = _mtf_features(df)
    rolling_high = df["high"].rolling(lookback).max()
    rolling_low = df["low"].rolling(lookback).min()
    mid = (rolling_high + rolling_low) / 2
    range_ratio = (rolling_high - rolling_low) / mid.replace(0, np.nan) * 100
    tight = range_ratio < range_pct
    was_tight = tight.shift(1, fill_value=False)
    vol_avg = df["volume"].rolling(50).mean()
    high_vol = df["volume"] > vol_avg * vol_mult
    mom = df["close"].pct_change(4)

    signals = pd.Series(0, index=df.index)
    signals[was_tight & (mom > 0.005) & high_vol & (df["close"] > rolling_high.shift()) & (mdf["trend_1h"] == 1)] = 1
    signals[was_tight & (mom < -0.005) & high_vol & (df["close"] < rolling_low.shift()) & (mdf["trend_1h"] == -1)] = -1
    signals.iloc[:lookback + 1] = 0
    return _clean_ls(signals)


def vwap_cci_combo(df, vwap_period=96, cci_thresh=100):
    """VWAP deviation + CCI extreme for double confirmation.
    Both indicators must agree for entry."""
    vwap = _rolling_vwap(df, vwap_period)
    diff = df["close"] - vwap
    diff_std = diff.rolling(200, min_periods=50).std().replace(0, np.nan)
    z = diff / diff_std
    cci = _cci(df)
    vol_avg = df["volume"].rolling(30).mean()
    high_vol = df["volume"] > vol_avg * 1.3

    signals = pd.Series(0, index=df.index)
    signals[(z < -1.5) & (cci < -cci_thresh) & high_vol] = 1
    signals[(z > 1.5) & (cci > cci_thresh) & high_vol] = -1
    signals[(z.abs() < 0.5) | ((cci > -30) & (cci < 30))] = 0
    return _clean_ls(signals)


def donchian_rsi_filter(df, dc_period=72, rsi_hi=60, rsi_lo=40):
    """Donchian breakout only when RSI confirms momentum direction.
    No entry when RSI contradicts breakout."""
    high_n = df["high"].rolling(dc_period).max()
    low_n = df["low"].rolling(dc_period).min()
    rsi = _rsi(df["close"], 14)
    adx_val, pdi, ndi = _adx(df)
    vol_avg = df["volume"].rolling(50).mean()
    high_vol = df["volume"] > vol_avg * 1.3

    signals = pd.Series(0, index=df.index)
    signals[(df["close"] > high_n.shift()) & (rsi > rsi_hi) & high_vol & (pdi > ndi)] = 1
    signals[(df["close"] < low_n.shift()) & (rsi < rsi_lo) & high_vol & (ndi > pdi)] = -1
    signals.iloc[:dc_period] = 0
    return _clean_ls(signals)


def swing_bb_breakout(df, bb_w=50, bb_std=2.0, confirm=2, vol_mult=1.5):
    """Wide BB breakout on swing timeframe (50-period BB).
    Like Consolidation Breakout but using BB squeeze detection."""
    lower, mid, upper = _bbands(df["close"], bb_w, bb_std)
    bw = (upper - lower) / mid.replace(0, np.nan)
    bw_q20 = bw.rolling(200, min_periods=50).quantile(0.2)
    in_squeeze = bw < bw_q20

    vol_avg = df["volume"].rolling(50).mean()
    high_vol = df["volume"] > vol_avg * vol_mult
    above = df["close"] > upper
    below = df["close"] < lower
    confirmed_up = above.rolling(confirm).min().astype(bool)
    confirmed_down = below.rolling(confirm).min().astype(bool)
    was_squeeze = in_squeeze.shift(confirm)

    signals = pd.Series(0, index=df.index)
    signals[confirmed_up & high_vol & was_squeeze] = 1
    signals[confirmed_down & high_vol & was_squeeze] = -1
    return _clean_ls(signals)


def mtf_donchian_momentum(df, dc_period=48, mom_bars=8, vol_mult=1.3):
    """Donchian breakout + short-term momentum + 4h trend.
    Triple confirmation: price > channel, momentum positive, 4h bullish."""
    mdf = _mtf_features(df)
    high_n = df["high"].rolling(dc_period).max()
    low_n = df["low"].rolling(dc_period).min()
    mom = df["close"].pct_change(mom_bars)
    vol_avg = df["volume"].rolling(50).mean()
    high_vol = df["volume"] > vol_avg * vol_mult

    signals = pd.Series(0, index=df.index)
    signals[(df["close"] > high_n.shift()) & (mom > 0.005) & high_vol & (mdf["trend_4h"] == 1)] = 1
    signals[(df["close"] < low_n.shift()) & (mom < -0.005) & high_vol & (mdf["trend_4h"] == -1)] = -1
    signals.iloc[:dc_period] = 0
    return _clean_ls(signals)


def hull_vwap_cross(df, hull_p=24, vwap_period=96):
    """Hull MA crossing VWAP as entry signal.
    Hull MA is faster than EMA, catches turns earlier."""
    hull = _hull_ma(df["close"], hull_p)
    vwap = _rolling_vwap(df, vwap_period)
    rsi = _rsi(df["close"], 14)
    adx_val, pdi, ndi = _adx(df)

    cross_up = (hull > vwap) & (hull.shift() <= vwap.shift())
    cross_down = (hull < vwap) & (hull.shift() >= vwap.shift())

    signals = pd.Series(0, index=df.index)
    signals[cross_up & (rsi > 40) & (rsi < 70) & (pdi > ndi) & (adx_val > 15)] = 1
    signals[cross_down & (rsi < 60) & (rsi > 30) & (ndi > pdi) & (adx_val > 15)] = -1
    return _clean_ls(signals)


def stoch_rsi_breakout(df, dc_period=48, stoch_lo=20, stoch_hi=80):
    """Donchian breakout confirmed by Stoch RSI momentum."""
    high_n = df["high"].rolling(dc_period).max()
    low_n = df["low"].rolling(dc_period).min()
    k, d = _stoch_rsi(df["close"])
    vol_avg = df["volume"].rolling(50).mean()
    high_vol = df["volume"] > vol_avg * 1.3

    signals = pd.Series(0, index=df.index)
    signals[(df["close"] > high_n.shift()) & (k > stoch_hi) & (k > d) & high_vol] = 1
    signals[(df["close"] < low_n.shift()) & (k < stoch_lo) & (k < d) & high_vol] = -1
    signals.iloc[:dc_period] = 0
    return _clean_ls(signals)


# ═════════════════════════════════════════════════════════
#  GROUP 8: Robust strategies — minimal params, symmetric, regime-agnostic
#  Goal: Low PBO via simplicity and fewer degrees of freedom
# ═════════════════════════════════════════════════════════

def pure_momentum_simple(df, lookback=20):
    """Simplest possible momentum: long if up N bars, short if down.
    No indicators, just raw price change. Hard to overfit."""
    ret = df["close"].pct_change(lookback)
    signals = pd.Series(0, index=df.index)
    signals[ret > 0.02] = 1
    signals[ret < -0.02] = -1
    return _clean_ls(signals)


def ema_cross_simple(df, fast=10, slow=40):
    """Simplest EMA cross. No ADX, no volume, no RSI.
    Minimal degrees of freedom = hard to overfit."""
    ef = _ema(df["close"], fast)
    es = _ema(df["close"], slow)
    signals = pd.Series(0, index=df.index)
    signals[(ef > es) & (ef.shift() <= es.shift())] = 1
    signals[(ef < es) & (ef.shift() >= es.shift())] = -1
    return _clean_ls(signals)


def channel_follow(df, period=50):
    """Follow the channel: above mid = long, below mid = short.
    Uses Donchian midline as trend proxy. Very simple."""
    hi = df["high"].rolling(period).max()
    lo = df["low"].rolling(period).min()
    mid = (hi + lo) / 2
    signals = pd.Series(0, index=df.index)
    cross_up = (df["close"] > mid) & (df["close"].shift() <= mid.shift())
    cross_down = (df["close"] < mid) & (df["close"].shift() >= mid.shift())
    signals[cross_up] = 1
    signals[cross_down] = -1
    signals.iloc[:period] = 0
    return _clean_ls(signals)


def atr_channel_breakout(df, period=30, mult=2.0):
    """ATR-based channel. Breakout = price moves mult*ATR from EMA.
    Adapts to volatility automatically. 1 param = minimal overfit."""
    ema = _ema(df["close"], period)
    atr = _atr(df, period)
    upper = ema + mult * atr
    lower = ema - mult * atr
    signals = pd.Series(0, index=df.index)
    signals[(df["close"] > upper) & (df["close"].shift() <= upper.shift())] = 1
    signals[(df["close"] < lower) & (df["close"].shift() >= lower.shift())] = -1
    signals[(df["close"] < ema) & (df["close"].shift() >= ema.shift())] = 0
    signals[(df["close"] > ema) & (df["close"].shift() <= ema.shift())] = 0
    return _clean_ls(signals)


def supertrend_simple(df, period=10, mult=3.0):
    """Pure Supertrend with no extra filters. Classic trend following."""
    d = _supertrend(df, period, mult)
    signals = pd.Series(0, index=df.index)
    signals[(d == 1) & (d.shift() == -1)] = 1
    signals[(d == -1) & (d.shift() == 1)] = -1
    return _clean_ls(signals)


def rsi_trend_simple(df, rsi_p=14, upper=65, lower=35):
    """RSI trend: >65 = long (strong trend), <35 = short.
    Not mean reversion but trend-following RSI. Counter-intuitive but works."""
    rsi = _rsi(df["close"], rsi_p)
    signals = pd.Series(0, index=df.index)
    signals[(rsi > upper) & (rsi.shift() <= upper)] = 1
    signals[(rsi < lower) & (rsi.shift() >= lower)] = -1
    signals[(rsi < 50) & (rsi.shift() >= 50)] = 0
    signals[(rsi > 50) & (rsi.shift() <= 50)] = 0
    return _clean_ls(signals)


def volatility_regime(df, vol_lookback=50, slow_ema=100):
    """Low vol = trend follow with EMA, high vol = stay flat.
    Regime detection via ATR percentile. Simple and robust."""
    atr = _atr(df, 14)
    atr_pct = atr / df["close"]
    atr_rank = atr_pct.rolling(vol_lookback, min_periods=20).rank(pct=True)
    ema = _ema(df["close"], slow_ema)
    low_vol = atr_rank < 0.5  # calm market

    signals = pd.Series(0, index=df.index)
    cross_up = (df["close"] > ema) & (df["close"].shift() <= ema.shift())
    cross_down = (df["close"] < ema) & (df["close"].shift() >= ema.shift())
    signals[cross_up & low_vol] = 1
    signals[cross_down & low_vol] = -1
    signals[~low_vol] = 0
    return _clean_ls(signals)


def macd_histogram_flip(df, fast=12, slow=26, sig=9):
    """Trade MACD histogram direction changes. Simple, no extra filters."""
    _, _, hist = _macd(df["close"], fast, slow, sig)
    signals = pd.Series(0, index=df.index)
    signals[(hist > 0) & (hist.shift() <= 0)] = 1
    signals[(hist < 0) & (hist.shift() >= 0)] = -1
    return _clean_ls(signals)


def twin_range_filter(df, fast_p=24, slow_p=72):
    """Fast and slow Donchian channels must agree.
    Breakout on fast + confirmed by slow channel direction."""
    fast_hi = df["high"].rolling(fast_p).max()
    fast_lo = df["low"].rolling(fast_p).min()
    slow_hi = df["high"].rolling(slow_p).max()
    slow_lo = df["low"].rolling(slow_p).min()
    slow_mid = (slow_hi + slow_lo) / 2

    signals = pd.Series(0, index=df.index)
    signals[(df["close"] > fast_hi.shift()) & (df["close"] > slow_mid)] = 1
    signals[(df["close"] < fast_lo.shift()) & (df["close"] < slow_mid)] = -1
    signals.iloc[:slow_p] = 0
    return _clean_ls(signals)


def price_vs_sma_200(df, sma_p=200, entry_dist=0.03):
    """Classic: buy when price crosses above SMA200, sell below.
    With distance filter: only enter when >3% away from SMA to avoid whipsaw."""
    sma = _sma(df["close"], sma_p)
    dist = (df["close"] - sma) / sma

    signals = pd.Series(0, index=df.index)
    signals[(dist > entry_dist) & (dist.shift() <= entry_dist)] = 1
    signals[(dist < -entry_dist) & (dist.shift() >= -entry_dist)] = -1
    signals[(dist.abs() < 0.005) & (dist.shift().abs() >= 0.005)] = 0
    signals.iloc[:sma_p] = 0
    return _clean_ls(signals)


# ═════════════════════════════════════════════════════════
#  REGISTRY — with optimized risk parameters
# ═════════════════════════════════════════════════════════

STRATEGIES = {
    # ── Group 1: Crypto Derivatives ──────────────────
    "Funding Carry": {
        "fn": funding_carry,
        "desc": "ファンディング逆張りキャリートレード。負のファンディングでロング。",
        "default_params": {"z_thresh": 1.5, "rsi_filter": 55},
        "param_grid": {"z_thresh": [1.2, 1.5, 2.0, 2.5], "rsi_filter": [50, 55, 60]},
        "risk": {"cooldown_bars": 4},
    },
    "OI Liquidation Reversal": {
        "fn": oi_liquidation_reversal,
        "desc": "急落後の反転狙い。OI低下はボーナス確認。",
        "default_params": {"lookback": 24, "rsi_thresh": 35, "price_drop": 2.0},
        "param_grid": {"lookback": [12, 24, 36], "rsi_thresh": [30, 35, 40], "price_drop": [1.5, 2.0, 3.0]},
        "risk": {"cooldown_bars": 4},
    },
    "OI Price Divergence": {
        "fn": oi_price_divergence,
        "desc": "価格/出来高ダイバージェンス。OIはボーナス。",
        "default_params": {"lookback": 36, "price_thresh": 1.5},
        "param_grid": {"lookback": [16, 24, 36, 48], "price_thresh": [0.5, 1.0, 1.5, 2.0, 3.0]},
        "risk": {"cooldown_bars": 2},
    },
    "Smart Money Composite": {
        "fn": smart_money_composite,
        "desc": "複数デリバティブ指標のスコアリング。2+で発動。",
        "default_params": {"min_score": 2},
        "param_grid": {"min_score": [2, 3, 4]},
        "risk": {"cooldown_bars": 4},
    },
    "OI Velocity": {
        "fn": oi_velocity,
        "desc": "OI加速度+トレンド方向でモメンタム検出。",
        "default_params": {"fast": 4, "slow": 16, "signal_p": 4},
        "param_grid": {"fast": [2, 4, 8], "slow": [8, 16, 24], "signal_p": [4, 8]},
        "risk": {"cooldown_bars": 6},
    },

    # ── Group 2: OHLCV Strategies ────────────────────
    "VWAP Mean Reversion": {
        "fn": vwap_mean_revert,
        "desc": "VWAP乖離+RSI+出来高確認。タイトエントリー、ワイドTP。",
        "default_params": {"std_mult": 2.5, "vwap_period": 96},
        "param_grid": {"std_mult": [2.0, 2.5, 3.0], "vwap_period": [48, 96, 144]},
        "risk": {"cooldown_bars": 4},
    },
    "Wide BB Reversal": {
        "fn": wide_bb_reversal,
        "desc": "ワイドBB(3σ)反転。極端値のみの高確度エントリー。",
        "default_params": {"bb_w": 20, "bb_std": 3.0, "rsi_p": 14},
        "param_grid": {"bb_std": [2.5, 3.0, 3.5], "rsi_p": [10, 14]},
        "risk": {"cooldown_bars": 4},
    },
    "Dual BB Strategy": {
        "fn": dual_bb_strategy,
        "desc": "外BBでエントリー、内BBで利確。構造的平均回帰。",
        "default_params": {"inner_std": 1.5, "outer_std": 3.0, "bb_w": 20},
        "param_grid": {"inner_std": [1.0, 1.5, 2.0], "outer_std": [2.5, 3.0, 3.5], "bb_w": [15, 20, 30]},
        "risk": {"cooldown_bars": 4},
    },
    "Volume Momentum": {
        "fn": volume_momentum,
        "desc": "モメンタム+出来高。1.5x出来高フィルター（緩和版）。",
        "default_params": {"mom_period": 20, "vol_mult": 1.5},
        "param_grid": {"mom_period": [8, 12, 16, 20, 30], "vol_mult": [1.0, 1.2, 1.5, 2.0]},
        "risk": {"cooldown_bars": 2},
    },
    "Order Flow Imbalance": {
        "fn": order_flow_imbalance,
        "desc": "売買圧力推定+ADXフィルター。閾値緩和版。",
        "default_params": {"period": 20, "threshold": 0.4},
        "param_grid": {"period": [10, 14, 20, 30], "threshold": [0.2, 0.3, 0.4, 0.5]},
        "risk": {"cooldown_bars": 2},
    },
    "Relative Volume Breakout": {
        "fn": relative_volume_breakout,
        "desc": "高相対出来高+価格ブレイク。閾値低下版。",
        "default_params": {"lookback": 20, "vol_mult": 2.0, "atr_mult": 1.5},
        "param_grid": {"vol_mult": [1.5, 2.0, 2.5, 3.0], "atr_mult": [0.8, 1.0, 1.5, 2.0]},
        "risk": {"cooldown_bars": 2},
    },
    "Keltner Breakout": {
        "fn": keltner_breakout,
        "desc": "ケルトナーチャネルブレイクアウト+出来高+ADXフィルター。",
        "default_params": {"ema_p": 20, "atr_p": 14, "mult": 2.5},
        "param_grid": {"ema_p": [15, 20, 30], "mult": [2.0, 2.5, 3.0]},
        "risk": {"cooldown_bars": 6},
    },
    "OBV Divergence": {
        "fn": obv_divergence,
        "desc": "OBV/価格ダイバージェンス+タイトRSI+出来高。",
        "default_params": {"lookback": 30},
        "param_grid": {"lookback": [20, 30, 40, 50]},
        "risk": {"cooldown_bars": 4},
    },
    "Volume Climax Reversal": {
        "fn": volume_climax_reversal,
        "desc": "出来高クライマックス=疲弊→反転。",
        "default_params": {"vol_mult": 2.5, "lookback": 5},
        "param_grid": {"vol_mult": [2.0, 2.5, 3.0, 4.0], "lookback": [3, 5, 8]},
        "risk": {"cooldown_bars": 6},
    },
    "Momentum Persistence": {
        "fn": momentum_persistence,
        "desc": "N連続同方向バー=モメンタム。ADXフィルター付き。",
        "default_params": {"periods": 6, "threshold": 0.001},
        "param_grid": {"periods": [4, 5, 6, 8], "threshold": [0.0005, 0.001, 0.002]},
        "risk": {"cooldown_bars": 4},
    },
    "Daily EMA Trend": {
        "fn": daily_ema_trend,
        "desc": "24h EMAクロス。超低頻度スイングトレード。ワイドトレーリング。",
        "default_params": {"fast_p": 96, "slow_p": 192},
        "param_grid": {"fast_p": [64, 96, 128], "slow_p": [144, 192, 288]},
        "risk": {"cooldown_bars": 4},
    },

    # ── Group 3: Swing ───────────────────────────────
    "Swing VWAP+OI": {
        "fn": swing_vwap_oi,
        "desc": "スイングVWAP乖離。長期保有向け。ワイドTP。",
        "default_params": {"vwap_period": 96, "std_mult": 2.0},
        "param_grid": {"vwap_period": [64, 96, 144], "std_mult": [1.5, 2.0, 2.5, 3.0]},
        "risk": {"cooldown_bars": 4},
    },
    "Swing Range Breakout": {
        "fn": swing_range_breakout,
        "desc": "レンジブレイク+持続性確認。緩和版。",
        "default_params": {"range_period": 96, "confirm_bars": 2, "vol_mult": 1.2},
        "param_grid": {"range_period": [24, 48, 72, 96, 144], "confirm_bars": [1, 2, 3], "vol_mult": [0.8, 1.0, 1.2, 1.5]},
        "risk": {"cooldown_bars": 2},
    },
    "Funding Swing": {
        "fn": funding_swing,
        "desc": "持続ファンディング極端値+価格乖離でスイング。",
        "default_params": {"funding_lookback": 64, "price_lookback": 64, "z_thresh": 1.5},
        "param_grid": {"funding_lookback": [32, 64, 96], "price_lookback": [32, 64], "z_thresh": [1.0, 1.5, 2.0]},
        "risk": {"cooldown_bars": 4},
    },

    # ── Group 5: Sweet-spot (breakout + persistence + trailing) ──
    "Donchian Confirmed": {
        "fn": donchian_confirmed,
        "desc": "ドンチャン持続性確認ブレイクアウト。confirm_barsで偽ブレイク排除。",
        "default_params": {"dc_period": 72, "confirm_bars": 2, "vol_mult": 1.5},
        "param_grid": {"dc_period": [24, 36, 48, 72, 96, 144], "confirm_bars": [1, 2, 3], "vol_mult": [1.0, 1.2, 1.5, 2.0]},
        "risk": {"cooldown_bars": 4},
    },
    "Momentum Burst": {
        "fn": momentum_burst,
        "desc": "極端なモメンタム+高出来高。高閾値で低頻度高確度。",
        "default_params": {"mom_bars": 8, "mom_thresh": 0.025, "vol_mult": 2.0},
        "param_grid": {"mom_bars": [4, 6, 8, 12, 16], "mom_thresh": [0.008, 0.01, 0.015, 0.02, 0.025], "vol_mult": [1.0, 1.2, 1.5, 2.0]},
        "risk": {"cooldown_bars": 4},
    },
    "Consolidation Breakout": {
        "fn": consolidation_breakout,
        "desc": "狭レンジ収束後のブレイクアウト。ボラ収縮→爆発的拡大。",
        "default_params": {"lookback": 48, "range_pct": 3.0, "vol_mult": 1.5},
        "param_grid": {"lookback": [36, 48, 72, 96], "range_pct": [1.5, 2.0, 3.0, 4.0], "vol_mult": [1.5, 2.0, 2.5]},
        "risk": {"cooldown_bars": 4},
    },
    "Inside Bar Breakout": {
        "fn": inside_bar_breakout,
        "desc": "インサイドバー後のブレイクアウト。ボラ収縮→拡大パターン。",
        "default_params": {"min_bars": 1, "vol_mult": 1.3},
        "param_grid": {"min_bars": [1, 2, 3], "vol_mult": [0.8, 1.0, 1.2, 1.5]},
        "risk": {"cooldown_bars": 2},
    },
    "ATR Momentum Breakout": {
        "fn": atr_momentum_breakout,
        "desc": "ATR正規化モメンタム。ボラ適応型。大きな動きのみ捕捉。",
        "default_params": {"atr_mult": 2.5, "mom_bars": 6, "vol_mult": 1.5},
        "param_grid": {"atr_mult": [2.0, 2.5, 3.0, 4.0], "mom_bars": [4, 6, 8, 12], "vol_mult": [1.5, 2.0, 2.5, 3.0]},
        "risk": {"cooldown_bars": 6},
    },

    # ── Group 6: Multi-timeframe strategies (15m entry, 1h/4h filter) ──
    "MTF Trend Breakout": {
        "fn": mtf_trend_breakout,
        "desc": "15mブレイクアウト + 1h/4hトレンドフィルター。上位足の方向のみエントリー。",
        "default_params": {"dc_period": 48, "vol_mult": 1.3},
        "param_grid": {"dc_period": [24, 36, 48, 72, 96], "vol_mult": [1.0, 1.3, 1.5, 2.0]},
        "risk": {"cooldown_bars": 4},
    },
    "MTF Mean Reversion": {
        "fn": mtf_mean_reversion,
        "desc": "15m RSI極端値 + 1hトレンド方向で平均回帰。逆張りだが上位足順張り。",
        "default_params": {"rsi_entry": 25, "bb_std": 2.5},
        "param_grid": {"rsi_entry": [20, 25, 30], "bb_std": [2.0, 2.5, 3.0]},
        "risk": {"cooldown_bars": 4},
    },
    "MTF Momentum Confirm": {
        "fn": mtf_momentum_confirm,
        "desc": "15mモメンタム + 1h/4hトレンド一致で高確度エントリー。",
        "default_params": {"mom_bars": 12, "mom_thresh": 0.008},
        "param_grid": {"mom_bars": [6, 8, 12, 16], "mom_thresh": [0.005, 0.008, 0.012, 0.015]},
        "risk": {"cooldown_bars": 4},
    },
    "MTF VWAP Trend": {
        "fn": mtf_vwap_trend,
        "desc": "VWAP乖離エントリー + 4hトレンド方向フィルター。",
        "default_params": {"std_mult": 2.0, "vwap_period": 96},
        "param_grid": {"std_mult": [1.5, 2.0, 2.5, 3.0], "vwap_period": [48, 96, 144]},
        "risk": {"cooldown_bars": 4},
    },
    "MTF EMA Crossover": {
        "fn": mtf_ema_crossover,
        "desc": "15m EMAクロス + 1h/4hトレンド一致。マルチタイムフレーム順張り。",
        "default_params": {"fast_ema": 8, "slow_ema": 21},
        "param_grid": {"fast_ema": [5, 8, 12], "slow_ema": [15, 21, 30, 50]},
        "risk": {"cooldown_bars": 4},
    },

    # ── Group 7: Round 2 — Variations of winners ────────
    "VWAP Supertrend MTF": {
        "fn": vwap_supertrend_mtf,
        "desc": "VWAP乖離+Supertrendトレンドフィルター。MTF代替。",
        "default_params": {"vwap_period": 96, "st_period": 10, "st_mult": 3.0},
        "param_grid": {"vwap_period": [48, 96, 144], "st_period": [7, 10, 14], "st_mult": [2.5, 3.0, 3.5]},
        "risk": {"cooldown_bars": 4},
    },
    "Donchian ADX Tight": {
        "fn": donchian_adx_tight,
        "desc": "ドンチャン+高ADX+DI乖離。強トレンドのみ。",
        "default_params": {"dc_period": 48, "adx_min": 22, "vol_mult": 1.3},
        "param_grid": {"dc_period": [24, 36, 48, 72], "adx_min": [18, 22, 28], "vol_mult": [1.0, 1.3, 1.5]},
        "risk": {"cooldown_bars": 4},
    },
    "Range Break Volume Spike": {
        "fn": range_break_volume_spike,
        "desc": "レンジブレイク+出来高スパイク(2.5x+)。機関参入。",
        "default_params": {"range_period": 72, "vol_spike": 2.5, "confirm": 2},
        "param_grid": {"range_period": [36, 48, 72, 96], "vol_spike": [2.0, 2.5, 3.0], "confirm": [1, 2]},
        "risk": {"cooldown_bars": 4},
    },
    "Consolidation MTF": {
        "fn": consolidation_mtf,
        "desc": "収束ブレイク+1hトレンドフィルター。勝者バリエーション。",
        "default_params": {"lookback": 48, "range_pct": 3.0, "vol_mult": 1.5},
        "param_grid": {"lookback": [36, 48, 72], "range_pct": [2.0, 3.0, 4.0], "vol_mult": [1.3, 1.5, 2.0]},
        "risk": {"cooldown_bars": 4},
    },
    "VWAP CCI Combo": {
        "fn": vwap_cci_combo,
        "desc": "VWAP乖離+CCI極端値の二重確認。",
        "default_params": {"vwap_period": 96, "cci_thresh": 100},
        "param_grid": {"vwap_period": [48, 96, 144], "cci_thresh": [80, 100, 120, 150]},
        "risk": {"cooldown_bars": 4},
    },
    "Donchian RSI Filter": {
        "fn": donchian_rsi_filter,
        "desc": "ドンチャン+RSI方向一致。RSI逆行時エントリー回避。",
        "default_params": {"dc_period": 72, "rsi_hi": 60, "rsi_lo": 40},
        "param_grid": {"dc_period": [36, 48, 72, 96], "rsi_hi": [55, 60, 65], "rsi_lo": [35, 40, 45]},
        "risk": {"cooldown_bars": 4},
    },
    "Swing BB Breakout": {
        "fn": swing_bb_breakout,
        "desc": "BB50スクイーズ後のブレイクアウト+持続性確認。",
        "default_params": {"bb_w": 50, "bb_std": 2.0, "confirm": 2, "vol_mult": 1.5},
        "param_grid": {"bb_w": [30, 50, 72], "bb_std": [1.5, 2.0, 2.5], "confirm": [1, 2], "vol_mult": [1.3, 1.5, 2.0]},
        "risk": {"cooldown_bars": 4},
    },
    "MTF Donchian Momentum": {
        "fn": mtf_donchian_momentum,
        "desc": "ドンチャン+モメンタム+4hトレンド。三重確認。",
        "default_params": {"dc_period": 48, "mom_bars": 8, "vol_mult": 1.3},
        "param_grid": {"dc_period": [24, 36, 48, 72], "mom_bars": [6, 8, 12], "vol_mult": [1.0, 1.3, 1.5]},
        "risk": {"cooldown_bars": 4},
    },
    "Hull VWAP Cross": {
        "fn": hull_vwap_cross,
        "desc": "HullMAとVWAPのクロス。高速MA+出来高加重平均。",
        "default_params": {"hull_p": 24, "vwap_period": 96},
        "param_grid": {"hull_p": [16, 24, 36], "vwap_period": [48, 96, 144]},
        "risk": {"cooldown_bars": 4},
    },
    "StochRSI Breakout": {
        "fn": stoch_rsi_breakout,
        "desc": "ドンチャンブレイク+StochRSIモメンタム確認。",
        "default_params": {"dc_period": 48, "stoch_lo": 20, "stoch_hi": 80},
        "param_grid": {"dc_period": [24, 36, 48, 72], "stoch_lo": [15, 20, 25], "stoch_hi": [75, 80, 85]},
        "risk": {"cooldown_bars": 4},
    },

    # ── Group 8: Robust — minimal params, hard to overfit ──
    "Pure Momentum": {
        "fn": pure_momentum_simple,
        "desc": "最シンプルなモメンタム。N期間リターンのみ。",
        "default_params": {"lookback": 20},
        "param_grid": {"lookback": [8, 12, 16, 20, 30, 48]},
        "risk": {"cooldown_bars": 4},
    },
    "EMA Cross Simple": {
        "fn": ema_cross_simple,
        "desc": "最シンプルEMAクロス。フィルターなし。",
        "default_params": {"fast": 10, "slow": 40},
        "param_grid": {"fast": [5, 8, 10, 15], "slow": [20, 30, 40, 60]},
        "risk": {"cooldown_bars": 4},
    },
    "Channel Follow": {
        "fn": channel_follow,
        "desc": "ドンチャン中央線クロス。トレンドフォロー。",
        "default_params": {"period": 50},
        "param_grid": {"period": [20, 30, 50, 72, 96]},
        "risk": {"cooldown_bars": 4},
    },
    "ATR Channel Breakout": {
        "fn": atr_channel_breakout,
        "desc": "ATRチャネルブレイク。ボラ適応+1パラメータ。",
        "default_params": {"period": 30, "mult": 2.0},
        "param_grid": {"period": [20, 30, 50], "mult": [1.5, 2.0, 2.5, 3.0]},
        "risk": {"cooldown_bars": 4},
    },
    "Supertrend Simple": {
        "fn": supertrend_simple,
        "desc": "純粋Supertrend。追加フィルターなし。",
        "default_params": {"period": 10, "mult": 3.0},
        "param_grid": {"period": [7, 10, 14, 20], "mult": [2.0, 2.5, 3.0, 3.5]},
        "risk": {"cooldown_bars": 4},
    },
    "RSI Trend": {
        "fn": rsi_trend_simple,
        "desc": "RSIトレンドフォロー(逆張りではない)。>65ロング、<35ショート。",
        "default_params": {"rsi_p": 14, "upper": 65, "lower": 35},
        "param_grid": {"rsi_p": [10, 14, 20], "upper": [60, 65, 70], "lower": [30, 35, 40]},
        "risk": {"cooldown_bars": 4},
    },
    "Volatility Regime": {
        "fn": volatility_regime,
        "desc": "低ボラ時のみEMAトレンドフォロー。高ボラ時フラット。",
        "default_params": {"vol_lookback": 50, "slow_ema": 100},
        "param_grid": {"vol_lookback": [30, 50, 72], "slow_ema": [50, 100, 150]},
        "risk": {"cooldown_bars": 4},
    },
    "MACD Histogram Flip": {
        "fn": macd_histogram_flip,
        "desc": "MACDヒストグラム反転。シンプルモメンタム。",
        "default_params": {"fast": 12, "slow": 26, "sig": 9},
        "param_grid": {"fast": [8, 12], "slow": [20, 26, 34], "sig": [7, 9, 12]},
        "risk": {"cooldown_bars": 4},
    },
    "Twin Range Filter": {
        "fn": twin_range_filter,
        "desc": "高速/低速ドンチャン一致。二重ブレイク確認。",
        "default_params": {"fast_p": 24, "slow_p": 72},
        "param_grid": {"fast_p": [16, 24, 36], "slow_p": [48, 72, 96]},
        "risk": {"cooldown_bars": 4},
    },
    "SMA200 Trend": {
        "fn": price_vs_sma_200,
        "desc": "SMA200基準トレンド。3%乖離でエントリー。",
        "default_params": {"sma_p": 200, "entry_dist": 0.03},
        "param_grid": {"sma_p": [100, 150, 200], "entry_dist": [0.02, 0.03, 0.05]},
        "risk": {"cooldown_bars": 4},
    },
}


# ═════════════════════════════════════════════════════════
#  GROUP 5: FEATURE-ENGINEERED STRATEGIES (flearn.pdf inspired)
# ═════════════════════════════════════════════════════════

# ── FFD (Fractional Differencing) helpers ────────────────

def _ffd_weights(d, window):
    """Fixed-width fractional differencing weights (flearn.pdf p.16)."""
    w = np.empty(window, dtype=float)
    w[0] = 1.0
    for k in range(1, window):
        w[k] = -w[k - 1] * (d - k + 1) / k
    # Threshold: drop tiny weights
    w[np.abs(w) < 1e-4] = 0
    return w[::-1]  # oldest first


def _frac_diff_ffd(series, d, window=50):
    """Apply FFD to a price series. Preserves memory while achieving stationarity."""
    w = _ffd_weights(d, window)
    vals = series.values.astype(float)
    out = np.full(len(vals), np.nan)
    for i in range(window, len(vals)):
        chunk = vals[i - window:i]
        if not np.any(np.isnan(chunk)):
            out[i] = np.dot(w, chunk)
    return pd.Series(out, index=series.index)


def ffd_momentum(df, d=0.4, window=50, z_thresh=1.5):
    """FFD(d=0.4)で定常化した価格のz-scoreでモメンタム検出。
    flearn.pdf: 分数次差分はメモリーを残しつつ定常性を確保。"""
    ffd = _frac_diff_ffd(df["close"], d, window)
    ffd_mean = ffd.rolling(100, min_periods=30).mean()
    ffd_std = ffd.rolling(100, min_periods=30).std().replace(0, np.nan)
    z = (ffd - ffd_mean) / ffd_std

    vol_avg = df["volume"].rolling(30).mean()
    high_vol = df["volume"] > vol_avg * 1.2

    signals = pd.Series(0, index=df.index)
    signals[(z > z_thresh) & high_vol] = 1
    signals[(z < -z_thresh) & high_vol] = -1
    signals[(z.abs() < 0.3) & (z.shift().abs() >= 0.3)] = 0
    return _clean_ls(signals)


def ffd_mean_revert(df, d=0.3, window=40, z_entry=2.0, z_exit=0.5):
    """FFD z-score 逆張り。大きく乖離→平均回帰を狙う。"""
    ffd = _frac_diff_ffd(df["close"], d, window)
    ffd_mean = ffd.rolling(120, min_periods=40).mean()
    ffd_std = ffd.rolling(120, min_periods=40).std().replace(0, np.nan)
    z = (ffd - ffd_mean) / ffd_std
    rsi = _rsi(df["close"], 14)

    signals = pd.Series(0, index=df.index)
    signals[(z < -z_entry) & (rsi < 35)] = 1
    signals[(z > z_entry) & (rsi > 65)] = -1
    signals[(z.abs() < z_exit) & (z.shift().abs() >= z_exit)] = 0
    return _clean_ls(signals)


# ── Entropy / Information features ──────────────────────

def _approx_entropy(series, m=2, r_mult=0.2, window=50):
    """Approximate entropy over rolling window. Low entropy = predictable."""
    out = pd.Series(np.nan, index=series.index)
    vals = series.values.astype(float)
    for i in range(window + m, len(vals)):
        seg = vals[i - window:i]
        if np.any(np.isnan(seg)):
            continue
        r = r_mult * np.std(seg)
        if r == 0:
            continue
        # Simplified: count template matches
        count_m = 0
        count_m1 = 0
        n = len(seg)
        for j in range(n - m):
            for k in range(j + 1, n - m):
                if np.max(np.abs(seg[j:j+m] - seg[k:k+m])) < r:
                    count_m += 1
                    if j + m < n and k + m < n:
                        if abs(seg[j+m] - seg[k+m]) < r:
                            count_m1 += 1
        if count_m > 0 and count_m1 > 0:
            out.iloc[i] = -np.log(count_m1 / count_m)
    return out


def entropy_regime(df, window=50, low_q=0.3, high_q=0.7):
    """低エントロピー（予測可能）時にトレンドフォロー、高時はフラット。
    flearn.pdf: 市場レジーム検出。"""
    ret = df["close"].pct_change()
    # Simplified entropy: use return distribution flatness
    roll_kurt = ret.rolling(window, min_periods=20).kurt()
    roll_skew = ret.rolling(window, min_periods=20).skew()
    # High kurtosis = fat tails = unpredictable
    kurt_q_lo = roll_kurt.rolling(200, min_periods=50).quantile(low_q)
    kurt_q_hi = roll_kurt.rolling(200, min_periods=50).quantile(high_q)

    predictable = roll_kurt < kurt_q_lo  # low kurtosis = more normal = predictable
    ema_f = _ema(df["close"], 12)
    ema_s = _ema(df["close"], 50)
    adx_val, pdi, ndi = _adx(df)

    signals = pd.Series(0, index=df.index)
    signals[predictable & (ema_f > ema_s) & (pdi > ndi) & (adx_val > 15)] = 1
    signals[predictable & (ema_f < ema_s) & (ndi > pdi) & (adx_val > 15)] = -1
    return _clean_ls(signals)


# ── Price acceleration / 2nd derivative ─────────────────

def price_acceleration(df, fast_p=8, slow_p=24, accel_thresh=0.001):
    """価格の加速度（2階差分）でエントリー。加速が正→ロング。
    1次モメンタムだけでなく加速の変化点を捉える。"""
    mom = df["close"].pct_change(fast_p)
    mom_slow = df["close"].pct_change(slow_p)
    accel = mom.diff(fast_p)  # 2nd derivative
    accel_smooth = accel.ewm(span=fast_p).mean()

    adx_val, pdi, ndi = _adx(df)
    vol_avg = df["volume"].rolling(30).mean()
    high_vol = df["volume"] > vol_avg * 1.2

    signals = pd.Series(0, index=df.index)
    # Acceleration turning positive + trend aligned
    signals[(accel_smooth > accel_thresh) & (mom_slow > 0) & high_vol & (adx_val > 12)] = 1
    signals[(accel_smooth < -accel_thresh) & (mom_slow < 0) & high_vol & (adx_val > 12)] = -1
    # Deceleration → exit
    signals[(accel_smooth.abs() < accel_thresh * 0.3) & (accel_smooth.shift().abs() >= accel_thresh * 0.3)] = 0
    return _clean_ls(signals)


# ── Ornstein-Uhlenbeck mean reversion speed ─────────────

def ou_mean_revert(df, lookback=96, half_life_max=48, z_entry=1.8):
    """OU過程の半減期を推定。短い半減期=速い平均回帰→逆張り有効。
    flearn.pdf: 定常性とメモリーのジレンマの実践的解法。"""
    close = df["close"]
    log_price = np.log(close)
    delta = log_price.diff()
    lag = log_price.shift()

    # Rolling OLS: delta = a + b * lag + eps → half_life = -ln(2) / b
    # Vectorized via rolling covariance/variance
    xy_cov = delta.rolling(lookback, min_periods=20).cov(lag)
    x_var = lag.rolling(lookback, min_periods=20).var()
    b = xy_cov / x_var.replace(0, np.nan)
    hl_raw = -np.log(2) / b
    half_life = hl_raw.where(b < 0, np.nan)

    # Mean revert only when half-life is short enough
    can_revert = half_life < half_life_max
    spread = log_price - log_price.rolling(lookback).mean()
    spread_std = spread.rolling(lookback).std().replace(0, np.nan)
    z = spread / spread_std
    rsi = _rsi(close, 14)

    signals = pd.Series(0, index=df.index)
    signals[can_revert & (z < -z_entry) & (rsi < 35)] = 1
    signals[can_revert & (z > z_entry) & (rsi > 65)] = -1
    signals[(z.abs() < 0.5) & (z.shift().abs() >= 0.5)] = 0
    return _clean_ls(signals)


# ── Multi-factor scoring ────────────────────────────────

def multi_factor_score(df, score_thresh=3, mom_p=20, vol_lookback=30):
    """複数ファクターのスコア合算。flearn.pdf: アンサンブル的にシグナルを合成。
    各ファクターが独立に±1を投票し、閾値超で合意エントリー。"""
    close = df["close"]
    rsi = _rsi(close, 14)
    adx_val, pdi, ndi = _adx(df)
    atr = _atr(df, 14)
    ema_f = _ema(close, 12)
    ema_s = _ema(close, 50)
    mom = close.pct_change(mom_p)
    vol_avg = df["volume"].rolling(vol_lookback).mean()
    vol_ratio = df["volume"] / vol_avg.replace(0, np.nan)
    lower, mid, upper = _bbands(close, 20, 2.0)

    bull = pd.Series(0, index=df.index)
    bear = pd.Series(0, index=df.index)

    # Factor 1: EMA trend
    bull += (ema_f > ema_s).astype(int)
    bear += (ema_f < ema_s).astype(int)

    # Factor 2: RSI momentum
    bull += (rsi > 50).astype(int)
    bear += (rsi < 50).astype(int)

    # Factor 3: ADX directional
    bull += ((adx_val > 15) & (pdi > ndi)).astype(int)
    bear += ((adx_val > 15) & (ndi > pdi)).astype(int)

    # Factor 4: Momentum
    bull += (mom > 0.005).astype(int)
    bear += (mom < -0.005).astype(int)

    # Factor 5: Volume confirmation
    bull += (vol_ratio > 1.2).astype(int)
    bear += (vol_ratio > 1.2).astype(int)

    # Factor 6: BB position
    bull += (close < lower).astype(int)  # oversold → contrarian long
    bear += (close > upper).astype(int)  # overbought → contrarian short

    signals = pd.Series(0, index=df.index)
    signals[bull >= score_thresh] = 1
    signals[bear >= score_thresh] = -1
    return _clean_ls(signals)


# ── Volatility-of-volatility ───────────────────────────

def vol_of_vol_breakout(df, atr_p=14, vov_p=50, vov_thresh=0.3):
    """ボラティリティのボラティリティが低い→収束→ブレイクアウト。
    BBスクイーズの上位版。ボラ自体の変動率を見る。"""
    atr = _atr(df, atr_p)
    atr_pct = atr / df["close"] * 100
    vov = atr_pct.rolling(vov_p, min_periods=20).std() / atr_pct.rolling(vov_p, min_periods=20).mean().replace(0, np.nan)

    # Low VoV = vol is stable and compressed → breakout imminent
    low_vov = vov < vov.rolling(200, min_periods=50).quantile(vov_thresh)
    mom = df["close"].pct_change(10)
    adx_val, pdi, ndi = _adx(df)
    vol_avg = df["volume"].rolling(30).mean()
    high_vol = df["volume"] > vol_avg * 1.3

    signals = pd.Series(0, index=df.index)
    # VoV was low → now expanding + direction
    expanding = ~low_vov & low_vov.shift(1, fill_value=False)
    signals[expanding & (mom > 0.005) & high_vol & (pdi > ndi)] = 1
    signals[expanding & (mom < -0.005) & high_vol & (ndi > pdi)] = -1
    return _clean_ls(signals)


# ── Return distribution skew ───────────────────────────

def skew_momentum(df, lookback=48, skew_thresh=0.5, mom_confirm=0.003):
    """リターン分布の歪度(skew)でモメンタム方向を強化。
    正のスキュー=上方テールが大きい=さらに上昇しやすい。"""
    ret = df["close"].pct_change()
    roll_skew = ret.rolling(lookback, min_periods=20).skew()
    mom = df["close"].pct_change(lookback // 2)
    ema_f = _ema(df["close"], 12)
    ema_s = _ema(df["close"], 50)
    adx_val, _, _ = _adx(df)

    signals = pd.Series(0, index=df.index)
    # Positive skew + upward momentum + trend
    signals[(roll_skew > skew_thresh) & (mom > mom_confirm) & (ema_f > ema_s) & (adx_val > 12)] = 1
    # Negative skew + downward momentum + trend
    signals[(roll_skew < -skew_thresh) & (mom < -mom_confirm) & (ema_f < ema_s) & (adx_val > 12)] = -1
    return _clean_ls(signals)


# ── Adaptive lookback (volatility-scaled) ──────────────

def adaptive_channel(df, base_period=30, atr_scale=True, mult=2.0):
    """ATRに応じてルックバック期間を動的調整するチャネル。
    高ボラ→短い窓、低ボラ→長い窓。市場レジームに適応。"""
    atr = _atr(df, 14)
    atr_norm = atr / atr.rolling(200, min_periods=50).mean().replace(0, np.nan)

    # Adaptive period: high vol → shorter, low vol → longer
    period = (base_period / atr_norm.clip(0.5, 2.0)).fillna(base_period).astype(int).clip(10, 100)

    close = df["close"]
    high = df["high"]
    low = df["low"]

    # Vectorized via numpy arrays to avoid slow pandas iloc loop
    h_arr = high.values.astype(float)
    l_arr = low.values.astype(float)
    p_arr = period.values
    n = len(df)
    upper_arr = np.full(n, np.nan)
    lower_arr = np.full(n, np.nan)
    for i in range(base_period, n):
        p = int(p_arr[i])
        s = max(0, i - p)
        upper_arr[i] = h_arr[s:i].max()
        lower_arr[i] = l_arr[s:i].min()
    upper = pd.Series(upper_arr, index=df.index)
    lower = pd.Series(lower_arr, index=df.index)

    mid = (upper + lower) / 2
    adx_val, pdi, ndi = _adx(df)

    signals = pd.Series(0, index=df.index)
    signals[(close > upper.shift()) & (pdi > ndi) & (adx_val > 15)] = 1
    signals[(close < lower.shift()) & (ndi > pdi) & (adx_val > 15)] = -1
    signals[(close < mid) & (close.shift() >= mid.shift())] = 0
    signals[(close > mid) & (close.shift() <= mid.shift())] = 0
    return _clean_ls(signals)


# ── Volume-weighted momentum divergence ─────────────────

def vwm_divergence(df, mom_p=20, vol_p=20, div_thresh=0.3):
    """出来高加重モメンタムと単純モメンタムの乖離で偽ブレイクを検出。
    出来高を伴わないモメンタムは持続しない→逆張り。"""
    close = df["close"]
    ret = close.pct_change()
    # Volume-weighted momentum
    vw_mom = (ret * df["volume"]).rolling(mom_p).sum() / df["volume"].rolling(mom_p).sum().replace(0, np.nan)
    # Simple momentum
    simple_mom = close.pct_change(mom_p)

    # Divergence: simple mom says up but vw_mom disagrees
    div = simple_mom - vw_mom * 100  # scale adjustment
    rsi = _rsi(close, 14)
    adx_val, _, _ = _adx(df)

    signals = pd.Series(0, index=df.index)
    # Price up but volume-weighted says weak → short (divergence)
    signals[(simple_mom > 0.01) & (vw_mom < 0) & (rsi > 60) & (adx_val < 30)] = -1
    # Price down but volume-weighted says support → long
    signals[(simple_mom < -0.01) & (vw_mom > 0) & (rsi < 40) & (adx_val < 30)] = 1
    return _clean_ls(signals)


# ── Register new strategies ─────────────────────────────

STRATEGIES.update({
    "FFD Momentum": {
        "fn": ffd_momentum,
        "desc": "FFD(分数次差分)z-scoreモメンタム。メモリーと定常性を両立(flearn.pdf)。",
        "param_grid": {"d": [0.3, 0.4, 0.5], "window": [30, 50, 72], "z_thresh": [1.0, 1.5, 2.0]},
        "risk": {"cooldown_bars": 4},
    },
    "FFD Mean Revert": {
        "fn": ffd_mean_revert,
        "desc": "FFDで定常化した価格の逆張り。大きなz乖離→平均回帰。",
        "param_grid": {"d": [0.2, 0.3, 0.4], "window": [30, 40, 60], "z_entry": [1.5, 2.0, 2.5], "z_exit": [0.3, 0.5]},
        "risk": {"cooldown_bars": 4},
    },
    "Entropy Regime": {
        "fn": entropy_regime,
        "desc": "尖度ベースのレジーム検出。低尖度(予測可能)時のみトレンドフォロー。",
        "param_grid": {"window": [30, 50, 72], "low_q": [0.2, 0.3], "high_q": [0.7, 0.8]},
        "risk": {"cooldown_bars": 4},
    },
    "Price Acceleration": {
        "fn": price_acceleration,
        "desc": "価格2階差分(加速度)でエントリー。変化点を捉える。",
        "param_grid": {"fast_p": [6, 8, 12], "slow_p": [16, 24, 36], "accel_thresh": [0.0005, 0.001, 0.002]},
        "risk": {"cooldown_bars": 4},
    },
    "OU Mean Revert": {
        "fn": ou_mean_revert,
        "desc": "Ornstein-Uhlenbeck半減期推定。短半減期=高速平均回帰→逆張り。",
        "param_grid": {"lookback": [72, 96, 128], "half_life_max": [24, 48, 72], "z_entry": [1.5, 1.8, 2.2]},
        "risk": {"cooldown_bars": 4},
    },
    "Multi Factor Score": {
        "fn": multi_factor_score,
        "desc": "6ファクター投票型シグナル。アンサンブルで偽シグナル排除。",
        "param_grid": {"score_thresh": [3, 4, 5], "mom_p": [10, 20, 30], "vol_lookback": [20, 30, 50]},
        "risk": {"cooldown_bars": 4},
    },
    "VoV Breakout": {
        "fn": vol_of_vol_breakout,
        "desc": "ボラのボラ(VoV)収束→ブレイクアウト。BBスクイーズの上位版。",
        "param_grid": {"atr_p": [10, 14, 20], "vov_p": [30, 50, 72], "vov_thresh": [0.2, 0.3, 0.4]},
        "risk": {"cooldown_bars": 2},
    },
    "Skew Momentum": {
        "fn": skew_momentum,
        "desc": "リターン分布の歪度でモメンタム強化。正スキュー+上昇→ロング。",
        "param_grid": {"lookback": [24, 48, 72], "skew_thresh": [0.3, 0.5, 0.8], "mom_confirm": [0.002, 0.003, 0.005]},
        "risk": {"cooldown_bars": 4},
    },
    "Adaptive Channel": {
        "fn": adaptive_channel,
        "desc": "ATR適応型ルックバックチャネル。高ボラ→短窓、低ボラ→長窓。",
        "param_grid": {"base_period": [20, 30, 50], "mult": [1.5, 2.0, 2.5]},
        "risk": {"cooldown_bars": 4},
    },
    "VWM Divergence": {
        "fn": vwm_divergence,
        "desc": "出来高加重モメンタムと単純モメンタムの乖離。偽ブレイク逆張り。",
        "param_grid": {"mom_p": [10, 20, 30], "vol_p": [10, 20, 30], "div_thresh": [0.2, 0.3, 0.5]},
        "risk": {"cooldown_bars": 4},
    },
})


# ══════════════════════════════════════════════════════════
# GROUP 6: α≥100%+DD抑制+右肩上がり特化戦略
# ──────────────────────────────────────────────────────────
# 目標: α≥100%, OOS α≈IS α, MaxDD>-15%, R²>0.7
# 手法: メタラベリング, レジーム適応, DD制御, アンサンブル強化
# ══════════════════════════════════════════════════════════


# ── Meta-labeling on multi_st ─────────────────────────────

def meta_multi_st(df, base_p=7, base_mult=2.5, atr_pctile=40,
                  vol_ratio=1.2, rsi_filter=35, dd_limit=8):
    """multi_st(コンセンサス)にメタラベリングを適用。
    基本シグナル + ATRパーセンタイル + 出来高確認 + RSIフィルタ +
    ドローダウン制御で高確信トレードのみ通す。
    flearn.pdf: メタラベリング=1stモデルのシグナルを2ndモデルで選別。"""
    close = df["close"]
    high = df["high"]
    low = df["low"]

    # Base signal: multi_st consensus (3 supertrend vote)
    c = close.values
    params_list = [(base_p, base_mult), (base_p + 4, base_mult + 0.5),
                   (base_p + 10, base_mult + 1.0)]
    sigs = []
    for period, mult in params_list:
        atr_v = _atr(df, period).values
        hl2 = ((high + low) / 2).values
        up_b = hl2 - mult * atr_v
        dn_b = hl2 + mult * atr_v
        trend = np.ones(len(df))
        for j in range(1, len(df)):
            if c[j] > dn_b[j - 1]:
                trend[j] = 1
            elif c[j] < up_b[j - 1]:
                trend[j] = -1
            else:
                trend[j] = trend[j - 1]
        sigs.append(trend)
    consensus = sigs[0] + sigs[1] + sigs[2]
    base_sig = pd.Series(np.where(consensus >= 2, 1, np.where(consensus <= -2, -1, 0)),
                         index=df.index)

    # ── Meta-label features ──
    atr = _atr(df, 14)
    atr_pct = atr / close * 100
    atr_rank = atr_pct.rolling(200, min_periods=50).rank(pct=True) * 100
    vol_ma = df["volume"].rolling(20).mean()
    vol_spike = df["volume"] / vol_ma.replace(0, np.nan)
    rsi = _rsi(close, 14)

    # Equity-based DD control: track running equity
    equity = np.ones(len(df))
    peak_eq = 1.0
    dd_flag = np.zeros(len(df))  # 1 = in drawdown lockout
    ret = close.pct_change().fillna(0).values
    pos = 0
    for i in range(1, len(df)):
        if pos != 0:
            equity[i] = equity[i-1] * (1 + ret[i] * pos)
        else:
            equity[i] = equity[i-1]
        peak_eq = max(peak_eq, equity[i])
        dd_pct = (peak_eq - equity[i]) / peak_eq * 100
        if dd_pct > dd_limit:
            dd_flag[i] = 1
        sig_i = int(base_sig.iloc[i]) if i < len(base_sig) else 0
        pos = sig_i if sig_i != 0 else pos
    dd_mask = pd.Series(dd_flag, index=df.index)

    # Meta-label filter: pass only high-confidence trades
    sig = base_sig.copy()
    # Block trades when ATR rank is extreme (too volatile or too quiet)
    sig[(atr_rank < atr_pctile * 0.5) | (atr_rank > 100 - atr_pctile * 0.3)] = 0
    # Require volume confirmation
    sig[vol_spike < vol_ratio] = 0
    # RSI sanity: don't buy overbought, don't sell oversold
    sig[(sig == 1) & (rsi > 100 - rsi_filter)] = 0
    sig[(sig == -1) & (rsi < rsi_filter)] = 0
    # DD circuit breaker
    sig[dd_mask == 1] = 0

    return _clean_ls(sig)


# ── Regime-adaptive supertrend ────────────────────────────

def regime_supertrend(df, fast_p=7, slow_p=14, fast_mult=2.0, slow_mult=3.5,
                      vol_lookback=100, vol_thresh=50):
    """ボラティリティレジームに応じてスーパートレンドのパラメータを動的切替。
    低ボラ期→高速パラメータ(素早く反応), 高ボラ期→鈍感パラメータ(ノイズ耐性)。
    レジーム検出はATRパーセンタイルランク。"""
    close = df["close"]
    high = df["high"]
    low = df["low"]

    atr = _atr(df, 14)
    atr_pct = atr / close * 100
    atr_rank = atr_pct.rolling(vol_lookback, min_periods=30).rank(pct=True) * 100
    high_vol = atr_rank > vol_thresh

    # Compute both fast and slow supertrend
    def _st(p, m):
        atr_v = _atr(df, p).values
        hl2 = ((high + low) / 2).values
        up = hl2 - m * atr_v
        dn = hl2 + m * atr_v
        c = close.values
        t = np.ones(len(df))
        for j in range(1, len(df)):
            if c[j] > dn[j-1]: t[j] = 1
            elif c[j] < up[j-1]: t[j] = -1
            else: t[j] = t[j-1]
        return t

    fast_trend = _st(fast_p, fast_mult)
    slow_trend = _st(slow_p, slow_mult)

    # Select regime-appropriate trend
    hv = high_vol.values
    sig = np.where(hv, slow_trend, fast_trend)

    # ADX filter: only trade in trending markets
    adx_val, pdi, ndi = _adx(df)
    sig[(adx_val < 15).values] = 0

    return _clean_ls(pd.Series(sig.astype(int), index=df.index))


# ── Pullback-entry trend following ────────────────────────

def trend_pullback(df, trend_p=50, pullback_rsi=35, atr_p=14, entry_atr_mult=0.5):
    """強いトレンド中にプルバックを待ってからエントリー。
    エントリー価格が有利→DDが低い+リスクリワード改善。"""
    close = df["close"]
    ema_trend = _ema(close, trend_p)
    rsi = _rsi(close, 14)
    atr = _atr(df, atr_p)
    adx_val, pdi, ndi = _adx(df)

    # Trend direction
    up_trend = (close > ema_trend) & (pdi > ndi) & (adx_val > 18)
    dn_trend = (close < ema_trend) & (ndi > pdi) & (adx_val > 18)

    # Pullback detection: price dips toward EMA + RSI drops
    near_ema_up = (close - ema_trend).abs() < atr * entry_atr_mult
    near_ema_dn = (ema_trend - close).abs() < atr * entry_atr_mult

    signals = pd.Series(0, index=df.index)
    # Buy on pullback in uptrend
    signals[up_trend & (rsi < pullback_rsi + 15) & near_ema_up] = 1
    # Sell on rally in downtrend
    signals[dn_trend & (rsi > 100 - pullback_rsi - 15) & near_ema_dn] = -1

    return _clean_ls(signals)


# ── Drawdown-controlled momentum ──────────────────────────

def dd_controlled_momentum(df, mom_p=20, ema_p=50, dd_thresh=5, recovery_bars=20):
    """モメンタム戦略にドローダウンサーキットブレーカーを組込み。
    エクイティがピークからdd_thresh%以上下落→トレード停止。
    recovery_bars期間でエクイティが回復→再開。MaxDD抑制に特化。"""
    close = df["close"]
    mom = close.pct_change(mom_p)
    ema = _ema(close, ema_p)
    adx_val, pdi, ndi = _adx(df)
    rsi = _rsi(close, 14)

    # Base momentum signal
    base = pd.Series(0, index=df.index)
    base[(mom > 0.01) & (close > ema) & (pdi > ndi) & (adx_val > 15) & (rsi < 75)] = 1
    base[(mom < -0.01) & (close < ema) & (ndi > pdi) & (adx_val > 15) & (rsi > 25)] = -1

    # DD circuit breaker
    ret = close.pct_change().fillna(0).values
    sig_vals = base.values.copy()
    equity = 1.0
    peak = 1.0
    lockout_until = 0
    pos = 0
    for i in range(len(df)):
        if pos != 0:
            equity *= (1 + ret[i] * pos)
        peak = max(peak, equity)
        dd_pct = (peak - equity) / peak * 100

        if dd_pct > dd_thresh:
            lockout_until = i + recovery_bars

        if i < lockout_until:
            sig_vals[i] = 0

        pos = sig_vals[i] if sig_vals[i] != 0 else pos

    return _clean_ls(pd.Series(sig_vals.astype(int), index=df.index))


# ── Adaptive trailing momentum ────────────────────────────

def adaptive_trail_trend(df, st_p=10, st_mult=2.5, trail_atr_mult=1.5, ema_confirm=30):
    """スーパートレンド + ATR適応型内部トレイリングストップ。
    シグナル関数内でトレイリングを管理→backtest.pyのトレイリングと独立。
    利益を伸ばしつつDDを抑制。"""
    close = df["close"]
    high = df["high"]
    low = df["low"]
    atr = _atr(df, st_p)

    # Supertrend for direction
    atr_v = atr.values
    hl2 = ((high + low) / 2).values
    up = hl2 - st_mult * atr_v
    dn = hl2 + st_mult * atr_v
    c = close.values
    trend = np.ones(len(df))
    for j in range(1, len(df)):
        if c[j] > dn[j-1]: trend[j] = 1
        elif c[j] < up[j-1]: trend[j] = -1
        else: trend[j] = trend[j-1]

    ema_f = _ema(close, ema_confirm).values

    # Internal adaptive trailing stop
    sig = np.zeros(len(df))
    pos = 0
    entry_p = 0.0
    trail_p = 0.0
    for i in range(1, len(df)):
        t = int(trend[i])
        trail_dist = atr_v[i] * trail_atr_mult

        if pos == 0:
            # Enter if trend + EMA confirm
            if t == 1 and c[i] > ema_f[i]:
                sig[i] = 1
                pos = 1
                entry_p = c[i]
                trail_p = c[i] - trail_dist
            elif t == -1 and c[i] < ema_f[i]:
                sig[i] = -1
                pos = -1
                entry_p = c[i]
                trail_p = c[i] + trail_dist
        elif pos == 1:
            trail_p = max(trail_p, c[i] - trail_dist)
            if c[i] < trail_p or t == -1:
                sig[i] = 0  # exit
                pos = 0
            else:
                sig[i] = 2  # hold
        elif pos == -1:
            trail_p = min(trail_p, c[i] + trail_dist)
            if c[i] > trail_p or t == 1:
                sig[i] = 0
                pos = 0
            else:
                sig[i] = 2

    return pd.Series(sig.astype(int), index=df.index)


# ── Momentum cascade (multi-horizon consensus) ────────────

def momentum_cascade(df, fast=5, mid=20, slow=60, adx_min=15, vol_mult=1.1):
    """短期・中期・長期モメンタムの3段カスケード。
    全てのタイムホライゾンが同方向→高確信エントリー。
    独立シグナルの一致→過学習耐性が高くOOS安定。"""
    close = df["close"]
    mom_f = close.pct_change(fast)
    mom_m = close.pct_change(mid)
    mom_s = close.pct_change(slow)
    adx_val, pdi, ndi = _adx(df)
    vol_ma = df["volume"].rolling(20).mean()
    vol_ok = df["volume"] > vol_ma * vol_mult

    signals = pd.Series(0, index=df.index)
    # All 3 horizons agree + trend strength + volume
    signals[(mom_f > 0) & (mom_m > 0) & (mom_s > 0) &
            (pdi > ndi) & (adx_val > adx_min) & vol_ok] = 1
    signals[(mom_f < 0) & (mom_m < 0) & (mom_s < 0) &
            (ndi > pdi) & (adx_val > adx_min) & vol_ok] = -1

    return _clean_ls(signals)


# ── Breakout retest confirmation ──────────────────────────

def breakout_retest(df, channel_p=30, retest_bars=10, atr_p=14, atr_cushion=0.3):
    """チャネルブレイクアウト後のリテスト(戻り)確認エントリー。
    初回ブレイクは見送り→リテストで耐えたら確認エントリー。
    エントリー価格が大幅に改善→DD低減+R/R向上。(ベクトル化版)"""
    close = df["close"]
    high = df["high"]
    low = df["low"]
    atr = _atr(df, atr_p)
    hh = high.rolling(channel_p).max()
    ll = low.rolling(channel_p).min()

    # Detect breakouts
    break_up = (close > hh.shift()).astype(float).fillna(0)
    break_dn = (close < ll.shift()).astype(float).fillna(0)

    # "any breakout in past retest_bars" = rolling max over shifted window
    recent_break_up = break_up.shift(1).rolling(retest_bars, min_periods=1).max().fillna(0) > 0
    recent_break_dn = break_dn.shift(1).rolling(retest_bars, min_periods=1).max().fillna(0) > 0

    # Breakout level = channel high/low from retest_bars ago
    bo_level_up = hh.shift(retest_bars)
    bo_level_dn = ll.shift(retest_bars)
    cushion = atr * atr_cushion

    adx_val, pdi, ndi = _adx(df)

    # Long: recent breakout up + price near breakout level + trend confirmation
    long_sig = (recent_break_up
                & (close <= bo_level_up + cushion) & (close >= bo_level_up - cushion)
                & (pdi > ndi) & (adx_val > 15))

    # Short: recent breakout down + price near breakout level + trend confirmation
    short_sig = (recent_break_dn
                 & (close >= bo_level_dn - cushion) & (close <= bo_level_dn + cushion)
                 & (ndi > pdi) & (adx_val > 15))

    signals = pd.Series(0, index=df.index)
    signals[long_sig] = 1
    signals[short_sig] = -1

    return _clean_ls(signals)


# ── Dual supertrend + EMA ribbon ──────────────────────────

def dual_st_ribbon(df, st1_p=7, st1_m=2.0, st2_p=14, st2_m=3.0,
                   ema1=8, ema2=21, ema3=55):
    """2つのスーパートレンド + 3本EMAリボン。
    5つの独立シグナルの多数決→極めて高い過学習耐性。"""
    close = df["close"]
    high = df["high"]
    low = df["low"]

    def _st(p, m):
        atr_v = _atr(df, p).values
        hl2 = ((high + low) / 2).values
        up = hl2 - m * atr_v
        dn = hl2 + m * atr_v
        c = close.values
        t = np.ones(len(df))
        for j in range(1, len(df)):
            if c[j] > dn[j-1]: t[j] = 1
            elif c[j] < up[j-1]: t[j] = -1
            else: t[j] = t[j-1]
        return t

    st1 = _st(st1_p, st1_m)
    st2 = _st(st2_p, st2_m)
    e1 = _ema(close, ema1).values
    e2 = _ema(close, ema2).values
    e3 = _ema(close, ema3).values
    c = close.values

    # Score: each indicator votes
    score = np.zeros(len(df))
    score += np.where(st1 == 1, 1, -1)
    score += np.where(st2 == 1, 1, -1)
    score += np.where(e1 > e2, 1, -1)
    score += np.where(e2 > e3, 1, -1)
    score += np.where(c > e3, 1, -1)

    signals = pd.Series(np.where(score >= 4, 1, np.where(score <= -4, -1, 0)),
                         index=df.index)
    return _clean_ls(signals)


# ── Equity-smoothed trend ─────────────────────────────────

def equity_smooth_trend(df, st_p=10, st_mult=2.5, smooth_p=5, equity_ma=20):
    """スーパートレンドシグナルのエクイティ曲線を平滑化し、
    エクイティが右肩下がりの期間はシグナルをオフ。
    結果: エクイティカーブのR²を最大化。"""
    close = df["close"]
    high = df["high"]
    low = df["low"]

    atr_v = _atr(df, st_p).values
    hl2 = ((high + low) / 2).values
    up = hl2 - st_mult * atr_v
    dn = hl2 + st_mult * atr_v
    c = close.values
    trend = np.ones(len(df))
    for j in range(1, len(df)):
        if c[j] > dn[j-1]: trend[j] = 1
        elif c[j] < up[j-1]: trend[j] = -1
        else: trend[j] = trend[j-1]

    # Simulate equity from the base trend signal
    ret = np.diff(c, prepend=c[0]) / np.maximum(c, 1e-10)
    eq = np.ones(len(df))
    pos = 0
    for i in range(1, len(df)):
        if pos != 0:
            eq[i] = eq[i-1] * (1 + ret[i] * pos)
        else:
            eq[i] = eq[i-1]
        pos = int(trend[i])

    # Smooth equity and check slope
    eq_ma = pd.Series(eq).rolling(equity_ma, min_periods=5).mean().values
    eq_slope = np.zeros(len(df))
    for i in range(smooth_p, len(df)):
        eq_slope[i] = eq_ma[i] - eq_ma[i - smooth_p]

    # Only trade when equity is rising
    sig = np.zeros(len(df))
    for i in range(len(df)):
        if eq_slope[i] > 0:
            sig[i] = trend[i]
        else:
            sig[i] = 0

    return _clean_ls(pd.Series(sig.astype(int), index=df.index))


# ── Register GROUP 6 strategies ──────────────────────────

STRATEGIES.update({
    "Meta Multi ST": {
        "fn": meta_multi_st,
        "desc": "multi_stにメタラベリング適用。ATR/出来高/RSI/DD制御で高確信トレードのみ通す。",
        "param_grid": {"base_p": [5, 7, 10], "base_mult": [2.0, 2.5, 3.0],
                       "atr_pctile": [40], "vol_ratio": [1.0, 1.2],
                       "rsi_filter": [35], "dd_limit": [5, 8]},
        "risk": {"cooldown_bars": 4},
    },
    "Regime Supertrend": {
        "fn": regime_supertrend,
        "desc": "ボラレジーム適応型ST。低ボラ→高速反応、高ボラ→鈍感。レジーム切替でDD抑制。",
        "param_grid": {"fast_p": [5, 7], "slow_p": [14, 20],
                       "fast_mult": [1.5, 2.0], "slow_mult": [3.0, 3.5],
                       "vol_thresh": [40, 50]},
        "risk": {"cooldown_bars": 4},
    },
    "Trend Pullback": {
        "fn": trend_pullback,
        "desc": "トレンド中のプルバック待ちエントリー。有利なエントリー価格→DD低減。",
        "param_grid": {"trend_p": [30, 50, 72], "pullback_rsi": [30, 35, 40],
                       "entry_atr_mult": [0.3, 0.5, 0.8]},
        "risk": {"cooldown_bars": 4},
    },
    "DD Controlled Momentum": {
        "fn": dd_controlled_momentum,
        "desc": "DDサーキットブレーカー付きモメンタム。エクイティDD>閾値→停止→回復後再開。",
        "param_grid": {"mom_p": [10, 20, 30], "ema_p": [30, 50, 72],
                       "dd_thresh": [3, 5, 8], "recovery_bars": [10, 20, 30]},
        "risk": {"cooldown_bars": 4},
    },
    "Adaptive Trail Trend": {
        "fn": adaptive_trail_trend,
        "desc": "ST+ATR適応トレイリング。内部でトレイリング管理→利益を伸ばしDD抑制。",
        "param_grid": {"st_p": [7, 10, 14], "st_mult": [2.0, 2.5, 3.0],
                       "trail_atr_mult": [1.0, 1.5, 2.0], "ema_confirm": [20, 30, 50]},
        "risk": {"cooldown_bars": 4},
    },
    "Momentum Cascade": {
        "fn": momentum_cascade,
        "desc": "短期/中期/長期モメンタム3段カスケード。全一致→高確信。OOS安定性重視。",
        "param_grid": {"fast": [3, 5, 8], "mid": [15, 20, 30], "slow": [40, 60, 80],
                       "adx_min": [12, 15], "vol_mult": [1.0, 1.2]},
        "risk": {"cooldown_bars": 4},
    },
    "Breakout Retest": {
        "fn": breakout_retest,
        "desc": "チャネルBOのリテスト確認エントリー。偽BO排除+有利エントリー→DD低減。",
        "param_grid": {"channel_p": [20, 30, 50], "retest_bars": [5, 10, 15],
                       "atr_cushion": [0.2, 0.3, 0.5]},
        "risk": {"cooldown_bars": 4},
    },
    "Dual ST Ribbon": {
        "fn": dual_st_ribbon,
        "desc": "2xST+3xEMAリボン。5つの独立投票→過学習耐性最大化。",
        "param_grid": {"st1_p": [5, 7], "st1_m": [1.5, 2.0],
                       "st2_p": [14, 20], "st2_m": [3.0, 3.5],
                       "ema1": [8], "ema2": [21], "ema3": [55]},
        "risk": {"cooldown_bars": 4},
    },
    "Equity Smooth Trend": {
        "fn": equity_smooth_trend,
        "desc": "STのエクイティ曲線を平滑化し下降期をカット。R²最大化特化。",
        "param_grid": {"st_p": [7, 10, 14], "st_mult": [2.0, 2.5, 3.0],
                       "smooth_p": [3, 5, 8], "equity_ma": [15, 20, 30]},
        "risk": {"cooldown_bars": 4},
    },
})


# ── Combo strategy (for programmatic generation) ───────────

def combo_signal(df, entry_type, ep1, ep2, filter_type, fp1, fp2):
    """Flexible entry + filter combo. Used to generate novel strategies."""
    close = df["close"]
    high = df["high"]
    low = df["low"]

    # ---- Entry signal ----
    if entry_type == "ema":
        f = _ema(close, int(ep1))
        s = _ema(close, int(ep2))
        sig = pd.Series(np.where(f > s, 1, np.where(f < s, -1, 0)), index=df.index)
    elif entry_type == "rsi":
        r = _rsi(close, int(ep1))
        sig = pd.Series(np.where(r < ep2, 1, np.where(r > 100 - ep2, -1, 0)), index=df.index)
    elif entry_type == "bb":
        lo, mid, hi = _bbands(close, int(ep1), ep2)
        sig = pd.Series(np.where(close > hi, 1, np.where(close < lo, -1, 0)), index=df.index)
    elif entry_type == "donchian":
        hh = high.rolling(int(ep1)).max()
        ll = low.rolling(int(ep1)).min()
        sig = pd.Series(np.where(close >= hh, 1, np.where(close <= ll, -1, 0)), index=df.index)
    elif entry_type == "macd":
        ml, sl_, hist = _macd(close, int(ep1), int(ep2), 9)
        sig = pd.Series(np.where(ml > sl_, 1, np.where(ml < sl_, -1, 0)), index=df.index)
    elif entry_type == "roc":
        roc = close.pct_change(int(ep1)) * 100
        sig = pd.Series(np.where(roc > ep2, 1, np.where(roc < -ep2, -1, 0)), index=df.index)
    elif entry_type == "stoch":
        lo_min = low.rolling(int(ep1)).min()
        hi_max = high.rolling(int(ep1)).max()
        k = 100 * (close - lo_min) / (hi_max - lo_min + 1e-10)
        sig = pd.Series(np.where(k < ep2, 1, np.where(k > 100 - ep2, -1, 0)), index=df.index)
    elif entry_type == "supertrend":
        atr_v = _atr(df, int(ep1)).values
        hl2 = ((high + low) / 2).values
        up = hl2 - ep2 * atr_v
        dn = hl2 + ep2 * atr_v
        c = close.values
        trend = np.ones(len(df))
        for i in range(1, len(df)):
            if c[i] > dn[i - 1]:
                trend[i] = 1
            elif c[i] < up[i - 1]:
                trend[i] = -1
            else:
                trend[i] = trend[i - 1]
        sig = pd.Series(trend.astype(int), index=df.index)
    elif entry_type == "vwap":
        typical = (high + low + close) / 3
        vwap = (typical * df["volume"]).rolling(int(ep1)).sum() / df["volume"].rolling(int(ep1)).sum()
        dist = (close - vwap) / vwap * 100
        sig = pd.Series(np.where(dist > ep2, 1, np.where(dist < -ep2, -1, 0)), index=df.index)
    elif entry_type == "hull":
        h1 = _ema(close, int(ep1) // 2)
        h2 = _ema(close, int(ep1))
        hull = _ema(2 * h1 - h2, max(2, int(ep1 ** 0.5)))
        sig = pd.Series(np.where(close > hull * (1 + ep2 / 1000), 1,
                                  np.where(close < hull * (1 - ep2 / 1000), -1, 0)), index=df.index)
    elif entry_type == "cci":
        typical = (high + low + close) / 3
        sma_tp = _sma(typical, int(ep1))
        std_tp = typical.rolling(int(ep1)).std()
        cci = (typical - sma_tp) / (0.012 * std_tp + 1e-10)
        sig = pd.Series(np.where(cci > ep2, 1, np.where(cci < -ep2, -1, 0)), index=df.index)
    elif entry_type == "keltner":
        mid = _ema(close, int(ep1))
        atr_v = _atr(df, int(ep1))
        upper = mid + ep2 * atr_v
        lower = mid - ep2 * atr_v
        sig = pd.Series(np.where(close > upper, 1, np.where(close < lower, -1, 0)), index=df.index)
    elif entry_type == "williams":
        hh = high.rolling(int(ep1)).max()
        ll = low.rolling(int(ep1)).min()
        wr = -100 * (hh - close) / (hh - ll + 1e-10)
        sig = pd.Series(np.where(wr > -ep2, 1, np.where(wr < -(100 - ep2), -1, 0)), index=df.index)
    elif entry_type == "dmi":
        p = int(ep1)
        pdm = high.diff().clip(lower=0)
        ndm = (-low.diff()).clip(lower=0)
        pdm_f = pdm.where(pdm > ndm, 0)
        ndm_f = ndm.where(ndm > pdm, 0)
        atr_v = _atr(df, p)
        pdi = 100 * _ema(pdm_f, p) / atr_v.replace(0, np.nan)
        ndi = 100 * _ema(ndm_f, p) / atr_v.replace(0, np.nan)
        dx = 100 * (pdi - ndi).abs() / (pdi + ndi + 1e-10)
        adx_v = _ema(dx, p)
        sig = pd.Series(np.where((pdi > ndi) & (adx_v > ep2), 1,
                                  np.where((ndi > pdi) & (adx_v > ep2), -1, 0)), index=df.index)
    elif entry_type == "ichimoku":
        tenkan = (high.rolling(int(ep1)).max() + low.rolling(int(ep1)).min()) / 2
        kijun = (high.rolling(int(ep2)).max() + low.rolling(int(ep2)).min()) / 2
        sig = pd.Series(np.where((tenkan > kijun) & (close > kijun), 1,
                                  np.where((tenkan < kijun) & (close < kijun), -1, 0)), index=df.index)
    elif entry_type == "multi_st":
        # Consensus of 3 supertrend instances — reduces overfitting
        c = close.values
        params_list = [(int(ep1), ep2), (int(ep1) + 4, ep2 + 0.5), (int(ep1) + 10, ep2 + 1.0)]
        sigs = []
        for period, mult in params_list:
            atr_v = _atr(df, period).values
            hl2 = ((high + low) / 2).values
            up_b = hl2 - mult * atr_v
            dn_b = hl2 + mult * atr_v
            trend = np.ones(len(df))
            for j in range(1, len(df)):
                if c[j] > dn_b[j - 1]:
                    trend[j] = 1
                elif c[j] < up_b[j - 1]:
                    trend[j] = -1
                else:
                    trend[j] = trend[j - 1]
            sigs.append(trend)
        consensus = sigs[0] + sigs[1] + sigs[2]
        sig = pd.Series(np.where(consensus >= 2, 1, np.where(consensus <= -2, -1, 0)),
                         index=df.index)
    elif entry_type == "st_ema":
        # Supertrend + EMA confirmation — two independent trend signals
        atr_v = _atr(df, int(ep1)).values
        hl2 = ((high + low) / 2).values
        up_b = hl2 - 2.5 * atr_v
        dn_b = hl2 + 2.5 * atr_v
        c = close.values
        trend = np.ones(len(df))
        for j in range(1, len(df)):
            if c[j] > dn_b[j - 1]:
                trend[j] = 1
            elif c[j] < up_b[j - 1]:
                trend[j] = -1
            else:
                trend[j] = trend[j - 1]
        ema_f = _ema(close, int(ep1))
        ema_s = _ema(close, int(ep2))
        ema_sig = np.where(ema_f > ema_s, 1, np.where(ema_f < ema_s, -1, 0))
        sig = pd.Series(np.where((trend == 1) & (ema_sig == 1), 1,
                                  np.where((trend == -1) & (ema_sig == -1), -1, 0)),
                         index=df.index)
    elif entry_type == "st_breakout":
        # Supertrend trend + Donchian breakout: enter only on breakout confirmed by ST
        # ep1 = ST period, ep2 = Donchian period (overloaded)
        st_trend = _supertrend_raw(df, int(ep1), 2.5)  # fixed ST mult 2.5
        dch_p = int(ep2)
        hh = high.rolling(dch_p).max().shift(1)
        ll = low.rolling(dch_p).min().shift(1)
        # Continuous signal: ST direction, but only when breakout confirms
        breakout_long = close >= hh
        breakout_short = close <= ll
        sig = pd.Series(0, index=df.index)
        # Enter on breakout, stay while ST agrees
        in_pos = 0
        sig_v = sig.values
        st_v = st_trend
        bl_v = breakout_long.values
        bs_v = breakout_short.values
        for i in range(1, len(df)):
            if bl_v[i] and st_v[i] == 1:
                in_pos = 1
            elif bs_v[i] and st_v[i] == -1:
                in_pos = -1
            elif in_pos == 1 and st_v[i] == -1:
                in_pos = 0
            elif in_pos == -1 and st_v[i] == 1:
                in_pos = 0
            sig_v[i] = in_pos
        sig = pd.Series(sig_v, index=df.index)
    elif entry_type == "st_rsi":
        # Supertrend direction + RSI momentum confirmation
        # ep1 = ST period, ep2 = RSI period
        st_trend = _supertrend_raw(df, int(ep1), 2.5)
        rsi_v = _rsi(close, int(ep2))
        # Long: ST bullish + RSI recovering from oversold (crosses above 40)
        # Short: ST bearish + RSI falling from overbought (crosses below 60)
        sig = pd.Series(np.where((st_trend == 1) & (rsi_v > 40) & (rsi_v < 70), 1,
                                  np.where((st_trend == -1) & (rsi_v < 60) & (rsi_v > 30), -1, 0)),
                         index=df.index)
    elif entry_type == "st_macd":
        # Supertrend + MACD histogram momentum
        # ep1 = ST period, ep2 = MACD slow period
        st_trend = _supertrend_raw(df, int(ep1), 2.5)
        ml, sl_, hist = _macd(close, 12, int(ep2), 9)
        sig = pd.Series(np.where((st_trend == 1) & (hist > 0), 1,
                                  np.where((st_trend == -1) & (hist < 0), -1, 0)),
                         index=df.index)
    elif entry_type == "bb_squeeze":
        # Bollinger Band squeeze breakout — low vol → expansion
        # ep1 = BB period, ep2 = Keltner multiplier
        bb_lo, bb_mid, bb_hi = _bbands(close, int(ep1), 2.0)
        atr_v = _atr(df, int(ep1))
        kelt_hi = _ema(close, int(ep1)) + ep2 * atr_v
        kelt_lo = _ema(close, int(ep1)) - ep2 * atr_v
        squeeze = (bb_hi < kelt_hi) & (bb_lo > kelt_lo)  # BB inside Keltner = squeeze
        mom = close - _sma(close, int(ep1))
        # Signal: when squeeze releases and momentum has direction
        was_squeeze = squeeze.shift(1).fillna(False)
        sig = pd.Series(np.where(was_squeeze & ~squeeze & (mom > 0), 1,
                                  np.where(was_squeeze & ~squeeze & (mom < 0), -1, 0)),
                         index=df.index)
        # Hold position until opposite signal
        sig_v = sig.values
        for i in range(1, len(sig_v)):
            if sig_v[i] == 0:
                sig_v[i] = sig_v[i - 1]
        sig = pd.Series(sig_v, index=df.index)
    elif entry_type == "pivot_st":
        # Pivot point breakout confirmed by Supertrend
        # ep1 = ST period, ep2 = lookback for pivot (unused, fixed)
        st_trend = _supertrend_raw(df, int(ep1), 2.5)
        # Pivot highs/lows using rolling window
        pivot_p = 10
        pivot_high = high.rolling(pivot_p * 2 + 1, center=True).max()
        pivot_low = low.rolling(pivot_p * 2 + 1, center=True).min()
        # Resistance = recent pivot high, Support = recent pivot low
        resistance = pivot_high.shift(pivot_p + 1)
        support = pivot_low.shift(pivot_p + 1)
        sig = pd.Series(np.where((close > resistance) & (st_trend == 1), 1,
                                  np.where((close < support) & (st_trend == -1), -1, 0)),
                         index=df.index)
        sig_v = sig.values
        for i in range(1, len(sig_v)):
            if sig_v[i] == 0:
                sig_v[i] = sig_v[i - 1]
        sig = pd.Series(sig_v, index=df.index)
    elif entry_type == "mean_rev_st":
        # Mean reversion entries IN DIRECTION of Supertrend trend
        # Buy dips in uptrend, sell rallies in downtrend
        # ep1 = ST period, ep2 = BB period for mean-rev bands
        st_trend = _supertrend_raw(df, int(ep1), 2.5)
        bb_lo, bb_mid, bb_hi = _bbands(close, int(ep2), 2.0)
        # Long: ST bullish + price touches lower BB (dip buy)
        # Short: ST bearish + price touches upper BB (rally sell)
        sig = pd.Series(np.where((st_trend == 1) & (close <= bb_lo), 1,
                                  np.where((st_trend == -1) & (close >= bb_hi), -1, 0)),
                         index=df.index)
        sig_v = sig.values
        for i in range(1, len(sig_v)):
            if sig_v[i] == 0:
                sig_v[i] = sig_v[i - 1]
        sig = pd.Series(sig_v, index=df.index)
    else:
        sig = pd.Series(0, index=df.index)

    # ---- Filter ----
    if filter_type == "trend":
        ema_t = _ema(close, int(fp1))
        sig = sig.copy()
        sig[(sig == 1) & (close < ema_t)] = 0
        sig[(sig == -1) & (close > ema_t)] = 0
    elif filter_type == "rsi":
        r = _rsi(close, int(fp1))
        sig = sig.copy()
        sig[(sig == 1) & (r > fp2)] = 0
        sig[(sig == -1) & (r < 100 - fp2)] = 0
    elif filter_type == "volume":
        vol_ma = df["volume"].rolling(int(fp1)).mean()
        sig = sig.copy()
        sig[df["volume"] < vol_ma * fp2] = 0
    elif filter_type == "mtf":
        htf = close.rolling(int(fp1)).mean()
        htf_ema = _ema(htf, int(fp2))
        sig = sig.copy()
        sig[(sig == 1) & (htf < htf_ema)] = 0
        sig[(sig == -1) & (htf > htf_ema)] = 0
    elif filter_type == "slow_st":
        # Slow Supertrend directional filter on same timeframe
        # fp1 = slow ST period, fp2 = slow ST multiplier
        slow_trend = _supertrend_raw(df, int(fp1), fp2)
        sig = sig.copy()
        sig[(sig == 1) & (slow_trend == -1)] = 0
        sig[(sig == -1) & (slow_trend == 1)] = 0
    elif filter_type == "htf_st":
        # True multi-timeframe: resample to higher TF, compute Supertrend, filter
        # fp1 = resample factor (4=1h, 8=2h, 16=4h, 24=6h from 15m base)
        # fp2 = HTF Supertrend multiplier (period fixed at 10)
        # IMPORTANT: 1-bar lag to avoid look-ahead bias — use htf_trend[j-1] for period j
        rf = max(2, int(fp1))
        n = len(df)
        htf_bars = n // rf
        if htf_bars >= 30:
            # Resample OHLCV
            htf_close = np.array([close.values[min((i+1)*rf-1, n-1)] for i in range(htf_bars)])
            htf_high = np.array([high.values[i*rf:min((i+1)*rf, n)].max() for i in range(htf_bars)])
            htf_low = np.array([low.values[i*rf:min((i+1)*rf, n)].min() for i in range(htf_bars)])
            # ATR on HTF
            htf_p = 10  # fixed period for HTF
            htf_tr = np.zeros(htf_bars)
            for j in range(1, htf_bars):
                htf_tr[j] = max(htf_high[j] - htf_low[j],
                                abs(htf_high[j] - htf_close[j-1]),
                                abs(htf_low[j] - htf_close[j-1]))
            htf_tr[0] = htf_high[0] - htf_low[0]
            htf_atr = np.zeros(htf_bars)
            htf_atr[:htf_p] = htf_tr[:htf_p].mean()
            for j in range(htf_p, htf_bars):
                htf_atr[j] = (htf_atr[j-1] * (htf_p - 1) + htf_tr[j]) / htf_p
            # Supertrend on HTF
            htf_hl2 = (htf_high + htf_low) / 2
            htf_up = htf_hl2 - fp2 * htf_atr
            htf_dn = htf_hl2 + fp2 * htf_atr
            htf_trend = np.ones(htf_bars)
            for j in range(1, htf_bars):
                if htf_close[j] > htf_dn[j-1]: htf_trend[j] = 1
                elif htf_close[j] < htf_up[j-1]: htf_trend[j] = -1
                else: htf_trend[j] = htf_trend[j-1]
            # Forward-fill with 1-bar lag: period j uses htf_trend[j-1]
            ltf_trend = np.zeros(n)
            ltf_trend[:rf] = htf_trend[0]  # first HTF bar: use initial trend
            for j in range(1, htf_bars):
                start = j * rf
                end = min((j+1) * rf, n)
                ltf_trend[start:end] = htf_trend[j - 1]  # lagged by 1 HTF bar
            if htf_bars * rf < n:
                ltf_trend[htf_bars*rf:] = htf_trend[htf_bars - 1]
            sig = sig.copy()
            sig[(sig == 1) & (ltf_trend == -1)] = 0
            sig[(sig == -1) & (ltf_trend == 1)] = 0
    elif filter_type == "htf_ema":
        # MTF EMA filter: resample to higher TF, compute EMA trend direction
        # fp1 = resample factor, fp2 = EMA period on HTF
        # IMPORTANT: 1-bar lag — use completed HTF bar's EMA for next period
        rf = max(2, int(fp1))
        n = len(df)
        htf_bars = n // rf
        if htf_bars >= 30:
            htf_close = np.array([close.values[min((i+1)*rf-1, n-1)] for i in range(htf_bars)])
            ema_p = max(2, int(fp2))
            htf_ema_v = np.zeros(htf_bars)
            htf_ema_v[0] = htf_close[0]
            alpha_v = 2.0 / (ema_p + 1)
            for j in range(1, htf_bars):
                htf_ema_v[j] = alpha_v * htf_close[j] + (1 - alpha_v) * htf_ema_v[j-1]
            # Forward-fill with 1-bar lag: period j uses values from bar j-1
            ltf_ema = np.zeros(n)
            ltf_htf_close = np.zeros(n)
            ltf_ema[:rf] = htf_ema_v[0]
            ltf_htf_close[:rf] = htf_close[0]
            for j in range(1, htf_bars):
                start = j * rf
                end = min((j+1) * rf, n)
                ltf_ema[start:end] = htf_ema_v[j - 1]       # lagged
                ltf_htf_close[start:end] = htf_close[j - 1]  # lagged
            if htf_bars * rf < n:
                ltf_ema[htf_bars*rf:] = htf_ema_v[htf_bars - 1]
                ltf_htf_close[htf_bars*rf:] = htf_close[htf_bars - 1]
            sig = sig.copy()
            sig[(sig == 1) & (ltf_htf_close < ltf_ema)] = 0
            sig[(sig == -1) & (ltf_htf_close > ltf_ema)] = 0
    elif filter_type == "atr":
        atr_v = _atr(df, int(fp1))
        atr_pct = atr_v / close * 100
        sig = sig.copy()
        sig[atr_pct < fp2] = 0
    elif filter_type == "oi":
        if _has_col(df, "oi"):
            oi_chg = df["oi"].pct_change(int(fp1)) * 100
            sig = sig.copy()
            sig[oi_chg.abs() < fp2] = 0

    sig = sig.fillna(0).astype(int)
    return sig


def combo_dual_signal(df, entry_type, ep1, ep2, f1_type, f1p1, f1p2, f2_type, f2p1, f2p2):
    """Entry + two filters for higher selectivity and robustness."""
    sig = combo_signal(df, entry_type, ep1, ep2, f1_type, f1p1, f1p2)
    # Apply second filter on the already-filtered signal
    close = df["close"]
    high = df["high"]
    low = df["low"]

    if f2_type == "trend":
        ema_t = _ema(close, int(f2p1))
        sig = sig.copy()
        sig[(sig == 1) & (close < ema_t)] = 0
        sig[(sig == -1) & (close > ema_t)] = 0
    elif f2_type == "rsi":
        r = _rsi(close, int(f2p1))
        sig = sig.copy()
        sig[(sig == 1) & (r > f2p2)] = 0
        sig[(sig == -1) & (r < 100 - f2p2)] = 0
    elif f2_type == "volume":
        vol_ma = df["volume"].rolling(int(f2p1)).mean()
        sig = sig.copy()
        sig[df["volume"] < vol_ma * f2p2] = 0
    elif f2_type == "mtf":
        htf = close.rolling(int(f2p1)).mean()
        htf_ema = _ema(htf, int(f2p2))
        sig = sig.copy()
        sig[(sig == 1) & (htf < htf_ema)] = 0
        sig[(sig == -1) & (htf > htf_ema)] = 0
    elif f2_type == "atr":
        atr_v = _atr(df, int(f2p1))
        atr_pct = atr_v / close * 100
        sig = sig.copy()
        sig[atr_pct < f2p2] = 0
    elif f2_type == "oi":
        if _has_col(df, "oi"):
            oi_chg = df["oi"].pct_change(int(f2p1)) * 100
            sig = sig.copy()
            sig[oi_chg.abs() < f2p2] = 0

    sig = sig.fillna(0).astype(int)
    return sig


# ══════════════════════════════════════════════════════════
# GROUP 7: Saturation-breaking strategies
# ══════════════════════════════════════════════════════════
# Tips-driven design:
# - supertrend+none is king (OOS=37.5%) → build on supertrend core
# - Filters hurt OOS → improve signal quality instead of filtering
# - 60-100 trades = best OOS → aim for selective entries
# - DD=-26% is the ceiling problem → pullback entries + adaptive exits
# - Market autocorr ≈ 0 → need regime awareness


def _supertrend_raw(df, p, mult):
    """Returns supertrend direction array: +1 or -1."""
    atr_v = _atr(df, p).values
    hl2 = ((df["high"] + df["low"]) / 2).values
    up = hl2 - mult * atr_v
    dn = hl2 + mult * atr_v
    c = df["close"].values
    t = np.ones(len(df))
    for j in range(1, len(df)):
        if c[j] > dn[j-1]: t[j] = 1
        elif c[j] < up[j-1]: t[j] = -1
        else: t[j] = t[j-1]
    return t


# ── 1. Consensus Voting: 7 independent indicators ──────────

def consensus_vote(df, vote_thresh=5, st_p=10, st_m=2.5, ema_f=9, ema_s=21,
                   rsi_p=14, macd_f=12, macd_s=26):
    """7つの独立インジケーターの多数決。
    シグナルが独立=OOS安定性最大。投票閾値でトレード数を制御。"""
    close = df["close"]
    high = df["high"]
    low = df["low"]

    score = np.zeros(len(df))

    # 1. Supertrend
    st = _supertrend_raw(df, st_p, st_m)
    score += st

    # 2. EMA crossover
    e_f = _ema(close, ema_f).values
    e_s = _ema(close, ema_s).values
    score += np.where(e_f > e_s, 1, -1)

    # 3. RSI momentum
    rsi = _rsi(close, rsi_p).values
    score += np.where(rsi > 55, 1, np.where(rsi < 45, -1, 0))

    # 4. MACD
    ml, sl_, hist = _macd(close, macd_f, macd_s, 9)
    score += np.where(ml.values > sl_.values, 1, -1)

    # 5. Price vs SMA50
    sma50 = close.rolling(50, min_periods=20).mean().values
    score += np.where(close.values > sma50, 1, -1)

    # 6. ADX trend strength
    adx_val, pdi, ndi = _adx(df)
    score += np.where((pdi > ndi) & (adx_val > 20), 1,
                      np.where((ndi > pdi) & (adx_val > 20), -1, 0))

    # 7. Donchian breakout (20-period)
    hh = high.rolling(20).max().values
    ll = low.rolling(20).min().values
    c = close.values
    score += np.where(c >= hh, 1, np.where(c <= ll, -1, 0))

    signals = pd.Series(
        np.where(score >= vote_thresh, 1, np.where(score <= -vote_thresh, -1, 0)),
        index=df.index)
    return _clean_ls(signals)


# ── 2. ST Pullback Sniper: supertrend + RSI pullback ──────

def st_pullback_sniper(df, st_p=10, st_m=2.5, rsi_p=14, rsi_ob=65, rsi_os=35,
                       atr_p=14, pullback_atr=0.5):
    """スーパートレンドでトレンド方向を決め、RSIプルバックで有利なエントリー。
    エントリー価格が改善→DD低減+R/R向上。トレード数60-100で安定。"""
    close = df["close"]
    st = _supertrend_raw(df, st_p, st_m)
    rsi = _rsi(close, rsi_p).values
    atr = _atr(df, atr_p).values
    c = close.values
    ema20 = _ema(close, 20).values

    # Vectorized: ST direction + RSI pullback + price near EMA
    st_up = pd.Series(st, index=df.index) == 1
    st_dn = pd.Series(st, index=df.index) == -1
    ema20_s = pd.Series(ema20, index=df.index)
    atr_s = pd.Series(atr, index=df.index)
    rsi_s = pd.Series(rsi, index=df.index)

    long_sig = st_up & (rsi_s < rsi_os) & (close < ema20_s + atr_s * pullback_atr)
    short_sig = st_dn & (rsi_s > rsi_ob) & (close > ema20_s - atr_s * pullback_atr)

    signals = pd.Series(0, index=df.index)
    signals[long_sig] = 1
    signals[short_sig] = -1
    return _clean_ls(signals)


# ── 3. Derivative Flow: OI + Funding + Taker ──────────────

def derivative_flow(df, oi_p=24, funding_extreme=0.01, taker_thresh=1.1,
                    confirm_bars=3):
    """デリバティブデータ(OI/Funding/Taker)をプライマリシグナルとして使用。
    価格だけでなく市場参加者の行動から方向性を判断。"""
    close = df["close"]
    signals = pd.Series(0, index=df.index)

    has_oi = _has_col(df, "oi")
    has_fr = _has_col(df, "funding_rate")
    has_taker = _has_col(df, "taker_buy_sell_ratio")

    if not (has_oi and has_fr):
        ema_f = _ema(close, 12)
        ema_s = _ema(close, 50)
        signals = pd.Series(np.where(ema_f > ema_s, 1, np.where(ema_f < ema_s, -1, 0)), index=df.index)
        return _clean_ls(signals)

    oi = df["oi"]
    fr = df["funding_rate"]
    oi_chg = oi.pct_change(oi_p)
    price_chg = close.pct_change(oi_p)

    bull_accum = (oi_chg > 0.02) & (price_chg > 0.005)
    bear_accum = (oi_chg > 0.02) & (price_chg < -0.005)

    fr_bull = fr < -funding_extreme
    fr_bear = fr > funding_extreme

    if has_taker:
        taker = df["taker_buy_sell_ratio"]
        taker_bull = taker > taker_thresh
        taker_bear = taker < (1 / taker_thresh)
    else:
        taker_bull = pd.Series(True, index=df.index)
        taker_bear = pd.Series(True, index=df.index)

    adx_val, pdi, ndi = _adx(df)
    trending = adx_val > 15

    long_sig = bull_accum & (fr_bull | taker_bull) & trending & (pdi > ndi)
    short_sig = bear_accum & (fr_bear | taker_bear) & trending & (ndi > pdi)

    signals[long_sig] = 1
    signals[short_sig] = -1
    return _clean_ls(signals)


# ── 4. Volatility Squeeze Breakout ─────────────────────────

def vol_squeeze_breakout(df, bb_p=20, bb_std=2.0, kc_p=20, kc_mult=1.5,
                         squeeze_bars=5):
    """ボリンジャーバンドがケルトナーチャネル内に収縮(スクイーズ)後の
    ブレイクアウトを検出。圧縮からの爆発→大きなα。"""
    close = df["close"]

    bb_lo, bb_mid, bb_hi = _bbands(close, bb_p, bb_std)

    kc_mid = _ema(close, kc_p)
    kc_atr = _atr(df, kc_p)
    kc_hi = kc_mid + kc_mult * kc_atr
    kc_lo = kc_mid - kc_mult * kc_atr

    squeeze = (bb_lo > kc_lo) & (bb_hi < kc_hi)
    squeeze_count = squeeze.astype(float).rolling(squeeze_bars, min_periods=1).sum()
    was_squeezed = squeeze_count >= squeeze_bars

    release = was_squeezed.shift(1).fillna(False) & ~squeeze
    mom = close - close.shift(squeeze_bars)

    adx_val, pdi, ndi = _adx(df)

    signals = pd.Series(0, index=df.index)
    signals[release & (mom > 0) & (pdi > ndi)] = 1
    signals[release & (mom < 0) & (ndi > pdi)] = -1
    return _clean_ls(signals)


# ── 5. Adaptive Multi-ST (volatility-adjusted multiplier) ──

def adaptive_multi_st(df, base_p=10, min_mult=1.5, max_mult=4.0, vol_lookback=100,
                      n_st=3):
    """ボラティリティに応じてST乗数を動的調整する複数STの合意。
    低ボラ期: 小さい乗数(敏感)、高ボラ期: 大きい乗数(鈍感)。"""
    close = df["close"]
    atr = _atr(df, 14)
    atr_pctile = atr.rolling(vol_lookback, min_periods=30).rank(pct=True)

    adaptive_mult = min_mult + (max_mult - min_mult) * atr_pctile.fillna(0.5)

    periods = [max(5, base_p - 3), base_p, base_p + 5][:n_st]
    score = np.zeros(len(df))
    for p in periods:
        mult_arr = adaptive_mult.values
        atr_v = _atr(df, p).values
        hl2 = ((df["high"] + df["low"]) / 2).values
        c = close.values
        t = np.ones(len(df))
        for j in range(1, len(df)):
            up_j = hl2[j] - mult_arr[j] * atr_v[j]
            dn_j = hl2[j] + mult_arr[j] * atr_v[j]
            if c[j] > dn_j: t[j] = 1
            elif c[j] < up_j: t[j] = -1
            else: t[j] = t[j-1]
        score += t

    thresh = n_st
    signals = pd.Series(
        np.where(score >= thresh, 1, np.where(score <= -thresh, -1, 0)),
        index=df.index)
    return _clean_ls(signals)


# ── 6. Regime Switch: trend-follow + mean-revert hybrid ────

def regime_switch(df, adx_thresh=25, st_p=10, st_m=2.5, rsi_p=14,
                  mr_entry=30, mr_exit=50):
    """ADXでレジーム判定。高ADX=STフォロー、低ADX=RSI逆張り。"""
    close = df["close"]
    adx_val, pdi, ndi = _adx(df)
    rsi = _rsi(close, rsi_p)
    st = _supertrend_raw(df, st_p, st_m)

    trending = adx_val > adx_thresh

    signals = pd.Series(0, index=df.index)
    signals[trending & (st == 1)] = 1
    signals[trending & (st == -1)] = -1
    ranging = ~trending & (adx_val > 10)
    signals[ranging & (rsi < mr_entry)] = 1
    signals[ranging & (rsi > 100 - mr_entry)] = -1
    signals[ranging & (rsi > mr_exit) & (rsi < 100 - mr_exit)] = 0

    return _clean_ls(signals)


# ── 7. Funding Squeeze ────────────────────────────────────

def funding_squeeze(df, funding_p=48, funding_z=1.5, st_p=10, st_m=2.5,
                    cooldown=8):
    """ファンディングレート極端値+ST転換で逆張り。スクイーズ捕捉。"""
    close = df["close"]
    signals = pd.Series(0, index=df.index)

    if not _has_col(df, "funding_rate"):
        return signals

    fr = df["funding_rate"]
    fr_mean = fr.rolling(funding_p, min_periods=10).mean()
    fr_std = fr.rolling(funding_p, min_periods=10).std().replace(0, np.nan)
    fr_z = (fr - fr_mean) / fr_std

    st = _supertrend_raw(df, st_p, st_m)
    st_series = pd.Series(st, index=df.index)
    st_flip_up = (st_series == 1) & (st_series.shift(1) == -1)
    st_flip_dn = (st_series == -1) & (st_series.shift(1) == 1)

    signals[st_flip_up & (fr_z < -funding_z)] = 1
    signals[st_flip_dn & (fr_z > funding_z)] = -1

    return _clean_ls(signals)


# ── 8. OI Divergence Reversal ──────────────────────────────

def oi_divergence(df, oi_p=24, price_p=24, div_thresh=0.03, confirm_p=5):
    """OI/価格ダイバージェンスで転換点検出。"""
    close = df["close"]
    signals = pd.Series(0, index=df.index)

    if not _has_col(df, "oi"):
        return signals

    oi = df["oi"]
    price_chg = close.pct_change(price_p)
    oi_chg = oi.pct_change(oi_p)

    rsi = _rsi(close, 14)

    bull_div = (price_chg < -div_thresh) & (oi_chg > div_thresh)
    bear_div = (price_chg > div_thresh) & (oi_chg < -div_thresh)

    signals[bull_div & (rsi < 40)] = 1
    signals[bear_div & (rsi > 60)] = -1

    return _clean_ls(signals)


# ── Register GROUP 7 strategies ──────────────────────────
STRATEGIES.update({
    "G7 Consensus Vote 5": {
        "fn": consensus_vote,
        "desc": "7指標多数決(閾値5)。独立シグナルの合意→OOS安定性最大化。",
        "param_grid": {"vote_thresh": [4, 5], "st_p": [10, 14], "st_m": [2.0, 2.5, 3.0],
                       "ema_f": [9], "ema_s": [21]},
        "risk": {"cooldown_bars": 4},
    },
    "G7 Consensus Vote 6": {
        "fn": consensus_vote,
        "desc": "7指標多数決(閾値6)。超高確信エントリーのみ。少数精鋭。",
        "param_grid": {"vote_thresh": [5, 6], "st_p": [10, 14], "st_m": [2.0, 2.5, 3.0],
                       "ema_f": [9, 12], "ema_s": [21, 30]},
        "risk": {"cooldown_bars": 2},
    },
    "G7 ST Pullback Sniper": {
        "fn": st_pullback_sniper,
        "desc": "STトレンド+RSIプルバック。有利価格エントリー→DD低減。",
        "param_grid": {"st_p": [10, 14], "st_m": [2.0, 2.5, 3.0],
                       "rsi_ob": [55, 60, 65], "rsi_os": [35, 40, 45],
                       "pullback_atr": [0.5, 1.0, 2.0]},
        "risk": {"cooldown_bars": 2},
    },
    "G7 Derivative Flow": {
        "fn": derivative_flow,
        "desc": "OI+ファンディング+Taker比率のデリバティブフロー分析。",
        "param_grid": {"oi_p": [12, 24, 48], "funding_extreme": [0.005, 0.01, 0.02],
                       "taker_thresh": [1.05, 1.1, 1.2]},
        "risk": {"cooldown_bars": 4},
    },
    "G7 Vol Squeeze": {
        "fn": vol_squeeze_breakout,
        "desc": "BB<KC検出→スクイーズ解放BO。圧縮後の爆発を捕捉。",
        "param_grid": {"bb_p": [15, 20], "bb_std": [1.5, 2.0],
                       "kc_p": [15, 20], "kc_mult": [1.0, 1.5],
                       "squeeze_bars": [3, 5, 8]},
        "risk": {"cooldown_bars": 4},
    },
    "G7 Adaptive Multi-ST": {
        "fn": adaptive_multi_st,
        "desc": "ボラ適応型マルチST合意。市場環境に自動適応。",
        "param_grid": {"base_p": [7, 10, 14], "min_mult": [1.0, 1.5],
                       "max_mult": [3.0, 4.0], "vol_lookback": [50, 100]},
        "risk": {"cooldown_bars": 4},
    },
    "G7 Regime Switch": {
        "fn": regime_switch,
        "desc": "ADXレジーム判定。トレンド=ST追従、レンジ=RSI逆張り。",
        "param_grid": {"adx_thresh": [20, 25, 30], "st_p": [10, 14], "st_m": [2.0, 2.5, 3.0],
                       "mr_entry": [25, 30, 35]},
        "risk": {"cooldown_bars": 4},
    },
    "G7 Funding Squeeze": {
        "fn": funding_squeeze,
        "desc": "ファンディング極値+ST転換→スクイーズ逆張り。",
        "param_grid": {"funding_p": [24, 48, 96], "funding_z": [1.0, 1.5, 2.0],
                       "st_p": [10, 14], "st_m": [2.0, 2.5, 3.0]},
        "risk": {"cooldown_bars": 4},
    },
    "G7 OI Divergence": {
        "fn": oi_divergence,
        "desc": "OI/価格ダイバージェンス転換点検出。",
        "param_grid": {"oi_p": [12, 24, 48], "price_p": [12, 24, 48],
                       "div_thresh": [0.02, 0.03, 0.05]},
        "risk": {"cooldown_bars": 4},
    },
    # ── Leveraged variants of best strategies (1.5x-2x) ──
    "G7 Consensus 5 Lev1.5": {
        "fn": consensus_vote,
        "desc": "7指標合意 + 1.5xレバレッジ。α増幅。",
        "param_grid": {"vote_thresh": [4, 5], "st_p": [10, 14], "st_m": [2.0, 2.5, 3.0],
                       "ema_f": [9], "ema_s": [21]},
        "risk": {"cooldown_bars": 4, "leverage": 1.5},
    },
    "G7 Consensus 5 Lev2": {
        "fn": consensus_vote,
        "desc": "7指標合意 + 2xレバレッジ。α最大化。",
        "param_grid": {"vote_thresh": [5, 6], "st_p": [10, 14], "st_m": [2.0, 2.5, 3.0],
                       "ema_f": [9], "ema_s": [21]},
        "risk": {"cooldown_bars": 4, "leverage": 2.0},
    },
    "G7 ST Pullback Lev1.5": {
        "fn": st_pullback_sniper,
        "desc": "STプルバック + 1.5xレバレッジ。DD抑制したエントリーにレバ適用。",
        "param_grid": {"st_p": [10, 14], "st_m": [2.0, 2.5, 3.0],
                       "rsi_ob": [55, 60, 65], "rsi_os": [35, 40, 45],
                       "pullback_atr": [0.5, 1.0, 2.0]},
        "risk": {"cooldown_bars": 2, "leverage": 1.5},
    },
    "G7 ST Pullback Lev2": {
        "fn": st_pullback_sniper,
        "desc": "STプルバック + 2xレバレッジ。高精度エントリー×レバ。",
        "param_grid": {"st_p": [10, 14], "st_m": [2.0, 2.5, 3.0],
                       "rsi_ob": [55, 60], "rsi_os": [40, 45],
                       "pullback_atr": [1.0, 2.0]},
        "risk": {"cooldown_bars": 2, "leverage": 2.0},
    },
    "G7 Regime Switch Lev1.5": {
        "fn": regime_switch,
        "desc": "レジーム適応型 + 1.5xレバレッジ。",
        "param_grid": {"adx_thresh": [20, 25, 30], "st_p": [10, 14], "st_m": [2.0, 2.5, 3.0],
                       "mr_entry": [25, 30, 35]},
        "risk": {"cooldown_bars": 4, "leverage": 1.5},
    },
    "G7 Adaptive MST Lev1.5": {
        "fn": adaptive_multi_st,
        "desc": "ボラ適応マルチST + 1.5xレバレッジ。",
        "param_grid": {"base_p": [7, 10, 14], "min_mult": [1.0, 1.5],
                       "max_mult": [3.0, 4.0], "vol_lookback": [50, 100]},
        "risk": {"cooldown_bars": 4, "leverage": 1.5},
    },
    "G7 Adaptive MST Lev2": {
        "fn": adaptive_multi_st,
        "desc": "ボラ適応マルチST + 2xレバレッジ。",
        "param_grid": {"base_p": [7, 10, 14], "min_mult": [1.0, 1.5],
                       "max_mult": [3.0, 4.0], "vol_lookback": [50, 100]},
        "risk": {"cooldown_bars": 4, "leverage": 2.0},
    },
})


# ══════════════════════════════════════════════════════════
# GROUP 8: Composite (複合) strategies
# ══════════════════════════════════════════════════════════
# Multiple sub-strategies combined for all-weather equity curves.
# Key: different signals dominate in different regimes.
# Combining complementary signals → lower DD + higher cross-regime α.


def _regime_detect(df, method, lookback):
    """Detect market regime. Returns array: 1=trending, -1=ranging, 0=neutral."""
    close = df["close"].values
    high = df["high"].values
    low = df["low"].values
    n = len(df)

    if method == "adx":
        adx_val, pdi, ndi = _adx(df, lookback)
        adx_v = adx_val if isinstance(adx_val, np.ndarray) else adx_val.values
        # ADX > 25 = trending, < 20 = ranging
        return np.where(adx_v > 25, 1, np.where(adx_v < 20, -1, 0))

    elif method == "atr_pctile":
        atr_v = _atr(df, 14).values
        atr_pct = atr_v / close * 100
        # Rolling percentile of ATR
        regime = np.zeros(n)
        for i in range(lookback, n):
            window = atr_pct[max(0, i - lookback):i]
            pctile = (atr_pct[i] - window.min()) / (window.max() - window.min() + 1e-10)
            if pctile > 0.7:
                regime[i] = -1  # High vol → mean-reversion
            elif pctile < 0.3:
                regime[i] = 1   # Low vol → trend-following
        return regime

    elif method == "slope":
        # Price slope: EMA direction and strength
        ema_v = _ema(pd.Series(close), lookback).values
        slope = np.zeros(n)
        for i in range(lookback, n):
            s = (ema_v[i] / ema_v[i - lookback] - 1) * 100
            if s > 2:
                slope[i] = 1   # Bull trend
            elif s < -2:
                slope[i] = -1  # Bear trend
        return slope

    return np.zeros(n)


def composite_regime_signal(df, sub1_type, sub1_p1, sub1_p2,
                            sub2_type, sub2_p1, sub2_p2,
                            regime_method, regime_lookback):
    """Regime-switching composite: uses sub1 in trending markets, sub2 in ranging.

    (複) Composite strategy — combines two complementary sub-strategies
    with automatic regime detection for all-weather performance.
    """
    close = df["close"]
    n = len(df)

    # Generate signals from both sub-strategies
    sig1 = combo_signal(df, sub1_type, sub1_p1, sub1_p2, "none", 0, 0)
    sig2 = combo_signal(df, sub2_type, sub2_p1, sub2_p2, "none", 0, 0)

    # Detect regime
    regime = _regime_detect(df, regime_method, int(regime_lookback))

    # Combine: trending regime → sub1, ranging regime → sub2, neutral → vote
    combined = np.zeros(n, dtype=int)
    s1 = sig1.values
    s2 = sig2.values
    for i in range(n):
        if regime[i] == 1:      # Trending
            combined[i] = s1[i]
        elif regime[i] == -1:   # Ranging
            combined[i] = s2[i]
        else:                    # Neutral: agree or flat
            if s1[i] == s2[i]:
                combined[i] = s1[i]
            else:
                combined[i] = 0  # Disagree → flat (risk-off)

    return pd.Series(combined, index=df.index)


def composite_vote_signal(df, e1_type, e1_p1, e1_p2,
                          e2_type, e2_p1, e2_p2,
                          e3_type, e3_p1, e3_p2,
                          vote_thresh):
    """Multi-strategy voting composite: 3 sub-strategies vote.

    (複) Composite — signals agree → enter; disagree → flat.
    vote_thresh: minimum agreement (2=majority, 3=unanimous).
    """
    # Generate signals from 3 sub-strategies
    s1 = combo_signal(df, e1_type, e1_p1, e1_p2, "none", 0, 0).values
    s2 = combo_signal(df, e2_type, e2_p1, e2_p2, "none", 0, 0).values
    s3 = combo_signal(df, e3_type, e3_p1, e3_p2, "none", 0, 0).values

    # Count votes
    n = len(df)
    combined = np.zeros(n, dtype=int)
    vt = int(vote_thresh)
    for i in range(n):
        longs = (s1[i] == 1) + (s2[i] == 1) + (s3[i] == 1)
        shorts = (s1[i] == -1) + (s2[i] == -1) + (s3[i] == -1)
        if longs >= vt:
            combined[i] = 1
        elif shorts >= vt:
            combined[i] = -1
        else:
            # Partial agreement: hold previous position
            if i > 0:
                combined[i] = combined[i - 1] if (longs > 0 or shorts > 0) else 0
            else:
                combined[i] = 0

    return pd.Series(combined, index=df.index)


def composite_adaptive_signal(df, trend_type, trend_p1, trend_p2,
                              mr_type, mr_p1, mr_p2,
                              adx_period, adx_thresh):
    """Adaptive composite: mean-rev in trends (buy dips), trend-follow in ranges.

    (複) Key insight: mean_rev_st buys dips within supertrend trends and
    OUTPERFORMS pure supertrend in trending markets. Use MR for trends,
    trend-follow signal for breakout confirmation in weak-trend periods.
    """
    close = df["close"]
    n = len(df)

    # Mean-reversion signal (dominant: works in both regimes)
    sig_mr = combo_signal(df, mr_type, mr_p1, mr_p2, "none", 0, 0).values
    # Trend-following signal (confirmation: used when trend is weak for breakouts)
    sig_trend = combo_signal(df, trend_type, trend_p1, trend_p2, "none", 0, 0).values

    # ADX for regime detection
    adx_val, pdi, ndi = _adx(df, int(adx_period))
    adx_v = adx_val if isinstance(adx_val, np.ndarray) else adx_val.values
    thresh = float(adx_thresh)

    combined = np.zeros(n, dtype=int)
    for i in range(n):
        if adx_v[i] > thresh:
            # Strong trend → mean-rev (buy dips in uptrend, sell rallies in downtrend)
            combined[i] = sig_mr[i]
        else:
            # Weak/no trend → need both to agree, else flat (risk-off)
            if sig_mr[i] == sig_trend[i]:
                combined[i] = sig_mr[i]
            else:
                combined[i] = 0  # Disagree → flat

    return pd.Series(combined, index=df.index)


def composite_ddguard_signal(df, entry_type, ep1, ep2,
                             guard_lookback, guard_threshold,
                             recovery_mult):
    """DD-guard composite: wraps any signal with drawdown-triggered risk-off.

    (複) Goes flat when price drops > guard_threshold% from its recent high
    within the lookback window. Re-enters only after partial recovery.
    This reduces DD without requiring equity-curve-based overlays
    (which fail on OOS2 because equity history resets).

    guard_lookback: bars to track rolling high
    guard_threshold: % drop from rolling high to trigger risk-off (e.g. 5.0 = 5%)
    recovery_mult: fraction of threshold to recover before re-entry (0.5 = 50%)
    """
    sig = combo_signal(df, entry_type, ep1, ep2, "none", 0, 0).values.copy()
    close = df["close"].values
    high = df["high"].values
    n = len(df)
    lb = int(guard_lookback)
    thresh = float(guard_threshold) / 100.0  # Convert pct to fraction
    rec = float(recovery_mult)

    risk_off = False

    for i in range(lb, n):
        # Rolling high over lookback (uses rolling window, not fixed peak)
        rolling_hi = high[max(0, i - lb):i + 1].max()
        dd = (close[i] / rolling_hi - 1)

        if not risk_off:
            if dd < -thresh:
                risk_off = True
                sig[i] = 0
        else:
            # Recovery: price must be within thresh*rec of rolling high.
            # rec=0.3 → recover at 3% from rolling high (strict)
            # rec=0.5 → recover at 5% (moderate)
            # rec=1.0 → same as threshold (loose)
            # Using rolling_high (not fixed peak) so recovery is
            # achievable even after prolonged bear markets.
            if dd > -thresh * rec:
                risk_off = False
            else:
                sig[i] = 0

    return pd.Series(sig, index=df.index)


def composite_ddguard_hold_signal(df, entry_type, ep1, ep2,
                                  guard_lookback, guard_threshold,
                                  recovery_mult):
    """DD-guard HOLD mode: holds existing positions during risk-off, only blocks NEW entries.

    (複) Unlike flat DDGuard which closes positions, this preserves open trades
    and only prevents new entries during drawdown. This increases trade count
    while still reducing DD (avoids entering at peaks before drops).

    Uses signal=2 (hold) during risk-off instead of 0 (flat).
    """
    sig = combo_signal(df, entry_type, ep1, ep2, "none", 0, 0).values.copy()
    close = df["close"].values
    high = df["high"].values
    n = len(df)
    lb = int(guard_lookback)
    thresh = float(guard_threshold) / 100.0
    rec = float(recovery_mult)

    risk_off = False

    for i in range(lb, n):
        rolling_hi = high[max(0, i - lb):i + 1].max()
        dd = (close[i] / rolling_hi - 1)

        if not risk_off:
            if dd < -thresh:
                risk_off = True
                sig[i] = 2
        else:
            if dd > -thresh * rec:
                risk_off = False
            else:
                sig[i] = 2  # Hold, don't close

    return pd.Series(sig, index=df.index)


def composite_dual_regime_signal(df, bull_type, bull_p1, bull_p2,
                                 bear_type, bear_p1, bear_p2,
                                 ema_period, flat_band):
    """Dual-regime composite: different signals for bull and bear markets.

    (複) Uses long-term EMA slope to detect bull/bear market.
    Bull: use bull_type signal (e.g., mean_rev_st for dip-buying)
    Bear: use bear_type signal (e.g., mean_rev_st with different params for short-selling)
    Transition zone (flat_band): go flat (risk-off)
    """
    close = df["close"]
    n = len(df)

    sig_bull = combo_signal(df, bull_type, bull_p1, bull_p2, "none", 0, 0).values
    sig_bear = combo_signal(df, bear_type, bear_p1, bear_p2, "none", 0, 0).values

    # Long-term EMA for trend direction
    ema_v = _ema(close, int(ema_period)).values
    fb = float(flat_band) / 100.0  # Convert pct

    combined = np.zeros(n, dtype=int)
    for i in range(int(ema_period), n):
        slope = close.values[i] / ema_v[i] - 1
        if slope > fb:      # Bull
            combined[i] = sig_bull[i]
        elif slope < -fb:   # Bear
            combined[i] = sig_bear[i]
        else:               # Transition → flat (risk-off)
            combined[i] = 0

    return pd.Series(combined, index=df.index)


def composite_riskoff_signal(df, entry_type, ep1, ep2,
                             filter_type, fp1, fp2,
                             riskoff_method, riskoff_thresh):
    """Risk-off composite: goes flat during dangerous regimes.

    (複) Wraps any base signal with a risk-off overlay that forces flat
    during regime transitions (the source of most DD events).
    """
    # Base signal
    sig = combo_signal(df, entry_type, ep1, ep2, filter_type, fp1, fp2).values.copy()
    close = df["close"].values
    n = len(df)

    if riskoff_method == "vol_spike":
        # Risk-off when ATR spikes above threshold percentile
        atr_v = _atr(df, 14).values
        atr_pct = atr_v / close * 100
        lookback = 200
        for i in range(lookback, n):
            window = atr_pct[max(0, i - lookback):i]
            pctile = (atr_pct[i] - window.min()) / (window.max() - window.min() + 1e-10)
            if pctile > riskoff_thresh:
                sig[i] = 0  # High vol → flat
    elif riskoff_method == "dd_pause":
        # Risk-off: go flat when equity is in drawdown
        # Use price as proxy: when price drops > thresh% from recent high
        lookback = int(riskoff_thresh * 1000)  # e.g., 0.05 → 50 bars
        if lookback < 10:
            lookback = 50
        peak = close[0]
        for i in range(n):
            if close[i] > peak:
                peak = close[i]
            dd = (close[i] / peak - 1)
            if dd < -riskoff_thresh:
                sig[i] = 0  # Price in drawdown → flat
    elif riskoff_method == "regime_trans":
        # Risk-off during regime transitions (ADX crossing threshold)
        adx_val, _, _ = _adx(df, 14)
        adx_v = adx_val if isinstance(adx_val, np.ndarray) else adx_val.values
        for i in range(1, n):
            # Transition: ADX crossed threshold in last 5 bars
            cross = False
            for j in range(max(0, i - 5), i):
                if (adx_v[j] > riskoff_thresh * 100) != (adx_v[i] > riskoff_thresh * 100):
                    cross = True
                    break
            if cross:
                sig[i] = 0

    return pd.Series(sig, index=df.index)


def composite_ddguard_staged_signal(df, entry_type, ep1, ep2,
                                     guard_lookback, hold_threshold, flat_threshold,
                                     recovery_mult):
    """Staged DD-guard: two-level price-drawdown protection.

    (複) Stage 1 (hold_threshold, e.g., 7%): signal=2 (hold existing, block new entries)
         Stage 2 (flat_threshold, e.g., 15%): signal=0 (go flat, close everything)
         Recovery: resume when price recovers to recovery_mult * hold_threshold from high.

    This preserves positions during small dips (more trades survive) while
    going flat during big crashes (DD protected). Best of DDG-flat and DDG-hold.
    """
    sig = combo_signal(df, entry_type, int(ep1), int(ep2), "none", 0, 0).values.copy()
    close = df["close"].values
    n = len(df)
    lb = int(guard_lookback)
    hold_th = float(hold_threshold) / 100.0
    flat_th = float(flat_threshold) / 100.0
    rec = float(recovery_mult)

    state = 0  # 0=normal, 1=hold, 2=flat
    for i in range(n):
        start = max(0, i - lb)
        rolling_high = close[start:i + 1].max()
        price_dd = (close[i] / rolling_high - 1)

        if state == 0:
            if price_dd < -flat_th:
                state = 2
                sig[i] = 0
            elif price_dd < -hold_th:
                state = 1
                sig[i] = 2
        elif state == 1:
            if price_dd < -flat_th:
                state = 2
                sig[i] = 0
            elif price_dd > -hold_th * rec:
                state = 0
            else:
                sig[i] = 2
        elif state == 2:
            if price_dd > -flat_th * rec:
                state = 0
            else:
                sig[i] = 0

    return pd.Series(sig, index=df.index)


def composite_ddguard_regime_signal(df, bull_type, bull_p1, bull_p2,
                                     bear_type, bear_p1, bear_p2,
                                     guard_lookback, guard_threshold,
                                     recovery_mult):
    """DDGuard-Regime: switches to bear strategy instead of going flat.

    (複) Normal: use bull strategy (e.g., mean_rev_st for dip-buying).
    DDGuard triggered: switch to bear strategy (e.g., supertrend for trend-following shorts).
    Recovery: switch back to bull strategy.

    This eliminates trade-free periods during bear markets while still
    protecting DD by avoiding the wrong strategy in the wrong regime.
    """
    sig_bull = combo_signal(df, bull_type, int(bull_p1), int(bull_p2), "none", 0, 0).values
    sig_bear = combo_signal(df, bear_type, int(bear_p1), int(bear_p2), "none", 0, 0).values
    close = df["close"].values
    high = df["high"].values
    n = len(df)
    lb = int(guard_lookback)
    thresh = float(guard_threshold) / 100.0
    rec = float(recovery_mult)

    combined = sig_bull.copy()
    risk_off = False

    for i in range(lb, n):
        rolling_hi = high[max(0, i - lb):i + 1].max()
        dd = (close[i] / rolling_hi - 1)

        if not risk_off:
            if dd < -thresh:
                risk_off = True
                combined[i] = sig_bear[i]
        else:
            if dd > -thresh * rec:
                risk_off = False
                combined[i] = sig_bull[i]
            else:
                combined[i] = sig_bear[i]

    return pd.Series(combined, index=df.index)


def composite_ddguard_volgate_signal(df, entry_type, ep1, ep2,
                                      guard_lookback, guard_threshold,
                                      recovery_mult, vol_atr_lb, vol_threshold):
    """DDGuard + Volatility gate: double protection via price DD + ATR filtering.

    (複) Same as DDGuard but adds ATR-based volatility gate:
    - DDGuard: goes flat when price drops from rolling high
    - Vol gate: goes flat when ATR/close exceeds threshold
    Together they catch ~80%+ of crash entries (DDGuard catches price-DD crashes,
    vol gate catches high-volatility periods even before price DD triggers).

    vol_atr_lb: ATR lookback bars (e.g. 48 = 12h for 15m bars)
    vol_threshold: ATR/close ratio threshold × 1000 (e.g. 3.5 = 0.35%)
    """
    import numpy as np
    sig = combo_signal(df, entry_type, ep1, ep2, "none", 0, 0).values.copy()
    close = df["close"].values
    high = df["high"].values
    low = df["low"].values
    n = len(df)
    lb = int(guard_lookback)
    thresh = float(guard_threshold) / 100.0
    rec = float(recovery_mult)
    v_lb = int(vol_atr_lb)
    v_thresh = float(vol_threshold) / 1000.0  # Convert from ‰ to ratio

    # Pre-compute ATR
    tr = np.maximum(high - low,
                    np.maximum(np.abs(high - np.roll(close, 1)),
                               np.abs(low - np.roll(close, 1))))
    tr[0] = high[0] - low[0]
    atr = pd.Series(tr).rolling(v_lb, min_periods=1).mean().values

    risk_off = False
    vol_off = False

    for i in range(max(lb, v_lb), n):
        # DDGuard check
        rolling_hi = high[max(0, i - lb):i + 1].max()
        dd = (close[i] / rolling_hi - 1)

        if not risk_off:
            if dd < -thresh:
                risk_off = True
        else:
            if dd > -thresh * rec:
                risk_off = False

        # Vol gate check
        atr_ratio = atr[i] / close[i] if close[i] > 0 else 0
        vol_off = atr_ratio > v_thresh

        if risk_off or vol_off:
            sig[i] = 0

    return pd.Series(sig, index=df.index)


def composite_adaptive_ddguard_signal(df, entry_type, ep1, ep2,
                                       guard_lookback, bear_threshold,
                                       bull_threshold, trend_lookback,
                                       recovery_mult):
    """Adaptive DDGuard: tight guard in bear, loose guard in bull.

    (複) Uses SMA(trend_lookback) as regime indicator:
    - Price < SMA → bear regime → tight threshold (bear_threshold%)
    - Price > SMA → bull regime → loose threshold (bull_threshold%)

    This solves the core dilemma:
    - Bear: tight guard catches crashes early → DD protected
    - Bull: loose guard lets corrections run → OOS2 alpha preserved

    bear_threshold: % drop to trigger guard in bear regime (e.g. 3.0 = 3%)
    bull_threshold: % drop to trigger guard in bull regime (e.g. 10.0 = 10%)
    trend_lookback: SMA period for regime detection (e.g. 500 bars ≈ 5 days)
    """
    import numpy as np
    sig = combo_signal(df, entry_type, int(ep1), int(ep2), "none", 0, 0).values.copy()
    close = df["close"].values
    high = df["high"].values
    n = len(df)
    lb = int(guard_lookback)
    bear_th = float(bear_threshold) / 100.0
    bull_th = float(bull_threshold) / 100.0
    trend_lb = int(trend_lookback)
    rec = float(recovery_mult)

    # Pre-compute SMA for trend detection
    sma = pd.Series(close).rolling(trend_lb, min_periods=1).mean().values

    risk_off = False
    # Track which threshold was active when risk_off triggered
    active_thresh = bear_th

    for i in range(lb, n):
        rolling_hi = high[max(0, i - lb):i + 1].max()
        dd = (close[i] / rolling_hi - 1)

        # Determine current regime
        is_bull = close[i] > sma[i]
        cur_thresh = bull_th if is_bull else bear_th

        if not risk_off:
            if dd < -cur_thresh:
                risk_off = True
                active_thresh = cur_thresh
                sig[i] = 0
        else:
            # Recovery: use the threshold that triggered the risk-off
            if dd > -active_thresh * rec:
                risk_off = False
            else:
                sig[i] = 0

    return pd.Series(sig, index=df.index)

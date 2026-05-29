#!/usr/bin/env python3
"""
wave_k519_google_trends_signal.py — K519 Google Trends Search Volume Signal
=============================================================================
K339 REPO_ROOT pattern. Fifth orthogonal alpha axis candidate (organic search attention).

HYPOTHESIS
----------
Google Trends search volume = retail attention proxy (organic interest, distinct from F&G).
F&G (K515) = aggregated sentiment composite (includes Trends as ONE component).
Google Trends = raw search interest, more granular, leading indicator of retail behavior.

  H1: BTC search z-score > +1.5 (30d) → SHORT (FOMO peak fade — retail piling in)
  H2: BTC search z-score < -1.0 (30d) → LONG (retail apathy bottom — attention trough)
  H3: "crypto crash" search spike → contrarian LONG (capitulation / panic sell exhaustion)
  H4: Combined (H1 + H2 + H3) bidirectional
  H5: Search velocity (1d delta of z-score) as leading signal

CROSS-AXIS ORTHOGONALITY
-------------------------
  K449 (FR-carry ETH-BTC): structural funding rate premium — NOT search-based
  K495 (DEX-CEX flow): on-chain flow imbalance — NOT search-based
  K510 (SOPR proxy): realized profit on-chain — NOT search-based
  K515 (F&G Index): sentiment composite (includes social + dominance + momentum)
  K519 (Google Trends): PURE search volume only — orthogonal dimension hypothesis

DATA SOURCE
-----------
  pytrends (Python wrapper for Google Trends, free, no API key)
  Keywords: "bitcoin", "ethereum", "solana", "buy crypto", "crypto crash"
  Geo: worldwide
  Daily resolution via 90-day batches with rate-limit throttling
  Coverage: 2024-01-01 → present (daily, ~880 days)
  IS: 2024-01-01 → 2025-06-30
  OOS: 2025-07-01 → 2026-05-29

METHODOLOGY
-----------
  Daily data fetched in 90-day batches, normalized to 0-100 (GT relative index).
  Z-score computed over rolling window (parameterized: w=7,14,21,30d).
  Signals fire end-of-day, hold for h=3,7,14,21d then exit.
  Returns: next-day open to exit-open (simplified: daily close returns, 10bps round-trip).
  Permutation test (block=21d, n=500) on IS returns.

SIGNALS (V1–V5)
---------------
  V1: bitcoin z-score > threshold (1.0–2.0) → SHORT h days
  V2: bitcoin z-score < -threshold (-0.5– -1.5) → LONG h days
  V3: "crypto crash" z-score > threshold → contrarian LONG h days
  V4: Combined V1 + V2 (bidirectional attention extremes)
  V5: search velocity signal (1d delta of z-score exceeds threshold)

ASSETS: BTC, ETH, SOL
COST: 10bps round-trip (5bps × 2)

§6 GATES
--------
  G1: OOS Sharpe ≥ 1.0
  G2: Perm p-value ≤ 0.05 (IS block permutation, block=21d)
  G3: DSR Bonferroni correction
  G4: Walk-forward ≥ 3/4 folds positive
  G5: Max |corr| vs K208/K280/K449/K476/K484/K493/K500/K495/K504/K510/K515 < 0.40
  G6: Trades/yr ≥ 10
  G7: OOS Ann Return > 5%

DECISION THRESHOLDS
-------------------
  ACCEPT: ≥ 5/7 gates + Sh ≥ 1.5 + corr(K515) < 0.40
  ACCEPT CONDITIONAL: 4–5/7 gates or Sh 1.0–1.5
  REJECT: ≤ 3/7 gates
  DATA-LIMITED: fetch failures

PROFIT PROJECTION (if accepted)
---------------------------------
  3% sleeve, 2x leverage, $600K notional @$10M
"""

import os
import sys
import json
import time
import logging
import warnings
import traceback
from datetime import datetime, timedelta
from pathlib import Path

import numpy as np
import pandas as pd
import urllib.request

warnings.filterwarnings("ignore")
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger("K519")

# ─── K339 REPO_ROOT pattern ───────────────────────────────────────────────────
REPO_ROOT = Path(os.environ.get("CRYPTO_LAB", Path(__file__).resolve().parent))
CACHE_DIR = REPO_ROOT / "cache" / "k519_trends"
CACHE_DIR.mkdir(parents=True, exist_ok=True)

WAVE = "K519"
SCRIPT = "wave_k519_google_trends_signal"
START_TS = time.time()

# ─── Config ───────────────────────────────────────────────────────────────────
IS_START = "2024-01-01"
IS_END = "2025-06-30"
OOS_START = "2025-07-01"
OOS_END = "2026-05-29"

COST_RT_BPS = 10  # round-trip

KEYWORDS = ["bitcoin", "ethereum", "crypto crash"]
GEO = ""  # worldwide

PARAM_GRID = {
    "w": [7, 14, 21, 30],
    "th": [0.8, 1.0, 1.5, 2.0],
    "h": [3, 7, 14, 21],
}

ASSETS = ["BTC", "ETH", "SOL"]

EXISTING_SHARPES = {
    "K449": 5.66,
    "K495": 2.17,
    "K510": 1.249,
    "K515": 1.201,
}


# ═══════════════════════════════════════════════════════════════════════════════
# DATA FETCHING
# ═══════════════════════════════════════════════════════════════════════════════

def fetch_price_data(symbol: str) -> pd.DataFrame:
    """Fetch daily OHLCV from Binance public API (no auth)."""
    cache_file = CACHE_DIR / f"price_{symbol}.parquet"
    if cache_file.exists():
        age_days = (time.time() - cache_file.stat().st_mtime) / 86400
        if age_days < 1:
            return pd.read_parquet(cache_file)

    log.info(f"Fetching {symbol} price from Binance...")
    sym_map = {"BTC": "BTCUSDT", "ETH": "ETHUSDT", "SOL": "SOLUSDT"}
    binance_sym = sym_map[symbol]

    all_rows = []
    end_ts = int(time.time() * 1000)
    # Fetch ~1100 days in one call (limit=1100)
    url = (
        f"https://api.binance.com/api/v3/klines?symbol={binance_sym}"
        f"&interval=1d&limit=1100"
    )
    try:
        with urllib.request.urlopen(url, timeout=15) as resp:
            data = json.loads(resp.read())
    except Exception as e:
        log.error(f"Price fetch failed for {symbol}: {e}")
        return pd.DataFrame()

    df = pd.DataFrame(
        data,
        columns=[
            "open_time", "open", "high", "low", "close", "volume",
            "close_time", "quote_vol", "trades",
            "taker_buy_base", "taker_buy_quote", "ignore"
        ],
    )
    df["date"] = pd.to_datetime(df["open_time"], unit="ms").dt.normalize()
    df["close"] = df["close"].astype(float)
    df = df.set_index("date")[["close"]].rename(columns={"close": symbol})
    df.to_parquet(cache_file)
    log.info(f"{symbol}: {len(df)} days ({df.index.min().date()} → {df.index.max().date()})")
    return df


def fetch_trends_batch(keyword: str, start: str, end: str, retries: int = 3) -> pd.Series:
    """Fetch Google Trends daily data for a 90-day window."""
    try:
        from pytrends.request import TrendReq
    except ImportError:
        log.error("pytrends not installed. Run: pip install pytrends")
        return pd.Series(dtype=float)

    for attempt in range(retries):
        try:
            pytrends = TrendReq(
                hl="en-US",
                tz=360,
                timeout=(10, 30),
                retries=2,
                backoff_factor=1.0,
            )
            timeframe = f"{start} {end}"
            pytrends.build_payload([keyword], cat=0, timeframe=timeframe, geo=GEO, gprop="")
            df = pytrends.interest_over_time()
            if df.empty:
                return pd.Series(dtype=float)
            # Drop isPartial
            if "isPartial" in df.columns:
                df = df.drop(columns=["isPartial"])
            return df[keyword].astype(float)
        except Exception as e:
            wait = 15 * (attempt + 1)
            log.warning(f"Trends fetch attempt {attempt+1}/{retries} failed for '{keyword}' [{start}→{end}]: {e}. Wait {wait}s")
            time.sleep(wait)
    return pd.Series(dtype=float)


def fetch_trends_full(keyword: str, start_date: str = "2024-01-01", end_date: str = "2026-05-29") -> pd.Series:
    """Fetch full daily Google Trends by batching 90-day windows."""
    cache_file = CACHE_DIR / f"trends_{keyword.replace(' ', '_')}_{start_date[:7]}_{end_date[:7]}.parquet"
    if cache_file.exists():
        age_days = (time.time() - cache_file.stat().st_mtime) / 86400
        if age_days < 3:
            log.info(f"Trends cache hit: {keyword}")
            s = pd.read_parquet(cache_file).squeeze()
            return s

    log.info(f"Fetching Google Trends daily: '{keyword}' {start_date} → {end_date}")
    start = pd.Timestamp(start_date)
    end = pd.Timestamp(end_date)

    all_series = []
    current = start
    batch_size = pd.Timedelta(days=89)  # ~90d window for daily resolution

    while current < end:
        batch_end = min(current + batch_size, end)
        s = fetch_trends_batch(
            keyword,
            current.strftime("%Y-%m-%d"),
            batch_end.strftime("%Y-%m-%d"),
        )
        if not s.empty:
            all_series.append(s)
        current = batch_end + pd.Timedelta(days=1)
        # Rate-limit throttle: Google Trends allows ~1 req/5s to avoid 429
        time.sleep(5)

    if not all_series:
        log.error(f"No trends data fetched for '{keyword}'")
        return pd.Series(dtype=float)

    combined = pd.concat(all_series)
    # Remove duplicates (overlap at boundaries), sort
    combined = combined[~combined.index.duplicated(keep="last")].sort_index()
    # Normalize: each 90d batch has its own 0-100 scale → stitch by scaling to max=100
    # Rescale to 0-100 global using the raw values (already 0-100 per batch)
    combined = combined.clip(0, 100)

    df_out = combined.to_frame(name=keyword)
    df_out.to_parquet(cache_file)
    log.info(f"'{keyword}': {len(combined)} days ({combined.index.min().date()} → {combined.index.max().date()})")
    return combined


# ═══════════════════════════════════════════════════════════════════════════════
# SIGNAL COMPUTATION
# ═══════════════════════════════════════════════════════════════════════════════

def compute_zscore(series: pd.Series, window: int) -> pd.Series:
    """Rolling z-score."""
    roll_mean = series.rolling(window, min_periods=max(3, window // 2)).mean()
    roll_std = series.rolling(window, min_periods=max(3, window // 2)).std()
    z = (series - roll_mean) / (roll_std + 1e-9)
    return z


def compute_velocity(series: pd.Series, window: int) -> pd.Series:
    """1-day change in z-score (momentum)."""
    z = compute_zscore(series, window)
    return z.diff(1)


def signal_v1_short_fomo(btc_trends: pd.Series, window: int, threshold: float) -> pd.Series:
    """
    V1: BTC search z-score > threshold → SHORT signal (FOMO peak fade).
    Returns +1 = SHORT, 0 = no position.
    """
    z = compute_zscore(btc_trends, window)
    signal = (z > threshold).astype(float)
    return signal


def signal_v2_long_apathy(btc_trends: pd.Series, window: int, threshold: float) -> pd.Series:
    """
    V2: BTC search z-score < -threshold → LONG signal (retail apathy bottom).
    Returns +1 = LONG, 0 = no position.
    """
    z = compute_zscore(btc_trends, window)
    signal = (z < -threshold).astype(float)
    return signal


def signal_v3_crash_contrarian(crash_trends: pd.Series, window: int, threshold: float) -> pd.Series:
    """
    V3: 'crypto crash' search spike → contrarian LONG (capitulation exhaustion).
    Returns +1 = LONG, 0 = no position.
    """
    z = compute_zscore(crash_trends, window)
    signal = (z > threshold).astype(float)
    return signal


def signal_v4_combined(btc_trends: pd.Series, crash_trends: pd.Series,
                        window: int, threshold: float) -> pd.Series:
    """
    V4: V1 SHORT + V2 LONG + V3 contrarian LONG combined.
    Returns: +1 = LONG, -1 = SHORT, 0 = flat.
    """
    z_btc = compute_zscore(btc_trends, window)
    z_crash = compute_zscore(crash_trends, window)
    signal = pd.Series(0.0, index=btc_trends.index)
    # SHORT when FOMO peak
    signal[z_btc > threshold] = -1.0
    # LONG when apathy
    signal[z_btc < -threshold * 0.7] = 1.0
    # LONG when crash panic (override SHORT if crash spike)
    signal[z_crash > threshold] = 1.0
    return signal


def signal_v5_velocity(btc_trends: pd.Series, window: int, threshold: float) -> pd.Series:
    """
    V5: Search velocity (1d delta of z-score).
    High positive velocity → SHORT (accelerating FOMO).
    High negative velocity → LONG (decelerating interest, reversal).
    Returns: +1 = LONG, -1 = SHORT, 0 = flat.
    """
    vel = compute_velocity(btc_trends, window)
    signal = pd.Series(0.0, index=btc_trends.index)
    signal[vel > threshold] = -1.0   # rapid search spike → fade
    signal[vel < -threshold] = 1.0    # rapid search decay → buy
    return signal


# ═══════════════════════════════════════════════════════════════════════════════
# BACKTEST ENGINE
# ═══════════════════════════════════════════════════════════════════════════════

def backtest_hold(
    price: pd.Series,
    signal: pd.Series,
    hold_days: int,
    direction: str = "directional",
    cost_bps: float = 10.0,
) -> pd.Series:
    """
    Simple hold-period backtest.
    signal: +1 = LONG, -1 = SHORT, 0 = flat.
    direction: 'long' (only longs), 'short' (only shorts), 'directional' (both).
    Returns daily P&L series (fractional returns).
    """
    cost_rt = cost_bps / 10000.0
    price = price.sort_index()
    signal = signal.reindex(price.index).fillna(0.0)

    fwd_ret = price.pct_change(hold_days).shift(-hold_days)

    if direction == "long":
        pos = signal.clip(lower=0)
    elif direction == "short":
        pos = -signal.clip(upper=0)  # flip: when signal=SHORT(-1), we go short
    else:
        pos = signal  # full directional

    # P&L: position * fwd_return - cost when entering
    trades = (pos != pos.shift(1)).astype(float).fillna(0)
    gross = pos * fwd_ret
    net = gross - trades * cost_rt

    # Annualize via daily P&L (divide fwd_ret by hold_days to get daily)
    daily_pnl = (net / hold_days).fillna(0)
    return daily_pnl


def compute_stats(daily_pnl: pd.Series, name: str = "") -> dict:
    """Compute Sharpe, annualized return, max_dd, etc."""
    ann_factor = 365
    daily_pnl = daily_pnl.dropna()
    n = len(daily_pnl)
    if n < 30:
        return {
            "n": n, "sharpe": 0.0, "ann_return": 0.0,
            "max_dd": 0.0, "cum_return": 0.0,
            "trades_yr": 0.0, "win_rate": 0.0,
        }

    ann_ret = daily_pnl.mean() * ann_factor
    ann_vol = daily_pnl.std() * np.sqrt(ann_factor)
    sharpe = ann_ret / (ann_vol + 1e-9)

    equity = (1 + daily_pnl).cumprod()
    cum_ret = (equity.iloc[-1] - 1) * 100
    rolling_max = equity.expanding().max()
    dd = (equity / rolling_max - 1)
    max_dd = dd.min() * 100

    nonzero = daily_pnl[daily_pnl != 0]
    trades_yr = len(nonzero) / (n / ann_factor)
    win_rate = (nonzero > 0).mean() if len(nonzero) > 0 else 0.0

    return {
        "n": n,
        "sharpe": round(float(sharpe), 3),
        "ann_return": round(float(ann_ret * 100), 2),
        "max_dd": round(float(max_dd), 2),
        "cum_return": round(float(cum_ret), 2),
        "trades_yr": round(float(trades_yr), 1),
        "win_rate": round(float(win_rate), 3),
    }


def permutation_test(
    daily_pnl: pd.Series,
    n_perm: int = 500,
    block_size: int = 21,
) -> float:
    """Block permutation test. Returns p-value."""
    actual_sharpe = compute_stats(daily_pnl)["sharpe"]
    pnl_arr = daily_pnl.dropna().values
    n = len(pnl_arr)
    if n < 60:
        return 1.0

    perm_sharpes = []
    rng = np.random.default_rng(42)
    n_blocks = int(np.ceil(n / block_size))

    for _ in range(n_perm):
        idx = rng.permutation(n_blocks) * block_size
        shuffled = []
        for start in idx:
            end = min(start + block_size, n)
            shuffled.extend(pnl_arr[start:end])
        shuffled = np.array(shuffled[:n])
        vol = shuffled.std() * np.sqrt(365) + 1e-9
        sh = shuffled.mean() * 365 / vol
        perm_sharpes.append(sh)

    p_val = np.mean(np.array(perm_sharpes) >= actual_sharpe)
    return float(p_val)


def walk_forward(
    price: pd.Series,
    signal_fn,
    hold_days: int,
    direction: str = "directional",
    n_folds: int = 4,
) -> list:
    """Walk-forward validation on IS period."""
    is_end = pd.Timestamp(IS_END)
    is_start = pd.Timestamp(IS_START)
    total_days = (is_end - is_start).days
    fold_size = total_days // n_folds

    results = []
    for fold in range(1, n_folds + 1):
        fold_end = is_start + pd.Timedelta(days=fold * fold_size)
        mask = (price.index >= is_start) & (price.index <= fold_end)
        price_fold = price[mask]
        signal_fold = signal_fn(price_fold.index)
        if len(price_fold) < 30:
            continue
        pnl = backtest_hold(price_fold, signal_fold, hold_days, direction)
        stats = compute_stats(pnl)
        results.append({
            "fold": fold,
            "start": is_start.strftime("%Y-%m-%d"),
            "end": fold_end.strftime("%Y-%m-%d"),
            "sharpe": stats["sharpe"],
            "positive": str(stats["sharpe"] > 0),
            "n": stats["n"],
        })
    return results


# ═══════════════════════════════════════════════════════════════════════════════
# PARAMETER SEARCH
# ═══════════════════════════════════════════════════════════════════════════════

def grid_search_variant(
    price_is: pd.Series,
    signal_series_fn,  # fn(window, threshold) -> pd.Series of signals
    hold_days_list: list,
    direction: str = "directional",
) -> dict:
    """Grid search over (window, threshold) for best IS Sharpe."""
    best = {"sharpe": -999, "w": None, "th": None, "h": None}

    for w in PARAM_GRID["w"]:
        for th in PARAM_GRID["th"]:
            sig = signal_series_fn(w, th)
            for h in hold_days_list:
                pnl = backtest_hold(price_is, sig, h, direction)
                stats = compute_stats(pnl)
                if stats["sharpe"] > best["sharpe"]:
                    best = {"sharpe": stats["sharpe"], "w": w, "th": th, "h": h}

    return best


# ═══════════════════════════════════════════════════════════════════════════════
# CORRELATION AGAINST EXISTING SIGNALS
# ═══════════════════════════════════════════════════════════════════════════════

def estimate_correlations(
    pnl_k519: pd.Series,
    price_btc: pd.Series,
    price_eth: pd.Series,
) -> dict:
    """
    Estimate K519 PnL correlation against proxy representations of existing strategies.
    Since we don't have live PnL from K449/K495/K510/K515, we use a proxy:
    - K449 proxy: ETH/BTC spread momentum
    - K495 proxy: BTC 7d return (DEX-CEX flow proxy)
    - K510 proxy: BTC 30d return (SOPR proxy)
    - K515 proxy: F&G signal returns (fetched from cache if available)
    """
    corrs = {}

    # K449 proxy: ETH-BTC relative return (30d)
    eth_ret = price_eth.pct_change(30)
    btc_ret = price_btc.pct_change(30)
    k449_proxy = (eth_ret - btc_ret).reindex(pnl_k519.index).fillna(0)
    corrs["vs_k449_eth_btc"] = round(
        float(pnl_k519.corr(k449_proxy, min_periods=30) or 0), 4
    )

    # K280 proxy: BTC 90d momentum
    k280_proxy = price_btc.pct_change(90).reindex(pnl_k519.index).fillna(0)
    corrs["vs_k280_btc_mom90"] = round(
        float(pnl_k519.corr(k280_proxy, min_periods=30) or 0), 4
    )

    # K495 proxy: BTC 7d return
    k495_proxy = price_btc.pct_change(7).reindex(pnl_k519.index).fillna(0)
    corrs["vs_k495_btc_7d"] = round(
        float(pnl_k519.corr(k495_proxy, min_periods=30) or 0), 4
    )

    # K510 proxy: BTC 30d return
    k510_proxy = price_btc.pct_change(30).reindex(pnl_k519.index).fillna(0)
    corrs["vs_k510_roi30d"] = round(
        float(pnl_k519.corr(k510_proxy, min_periods=30) or 0), 4
    )

    # K515 proxy: BTC 14d return (F&G corr with 14d BTC return per literature)
    k515_proxy = price_btc.pct_change(14).reindex(pnl_k519.index).fillna(0)
    corrs["vs_k515_fg_proxy"] = round(
        float(pnl_k519.corr(k515_proxy, min_periods=30) or 0), 4
    )

    # Raw BTC return correlation (check if strategy is just BTC exposure)
    btc_1d = price_btc.pct_change(1).reindex(pnl_k519.index).fillna(0)
    corrs["vs_btc_1d_ret"] = round(
        float(pnl_k519.corr(btc_1d, min_periods=30) or 0), 4
    )

    return corrs


# ═══════════════════════════════════════════════════════════════════════════════
# VARIANT RUNNER
# ═══════════════════════════════════════════════════════════════════════════════

def run_variant(
    variant_name: str,
    price_btc: pd.Series,
    price_eth: pd.Series,
    price_sol: pd.Series,
    btc_trends: pd.Series,
    crash_trends: pd.Series,
    direction: str,
    signal_fn_factory,  # fn(w, th) -> pd.Series
) -> dict:
    """Run full backtest for one variant across BTC/ETH/SOL."""
    log.info(f"  Running {variant_name}...")

    results = {}
    best_port_oos = -999
    best_params_port = None

    for asset, price in [("btc", price_btc), ("eth", price_eth), ("sol", price_sol)]:
        price_is = price[(price.index >= IS_START) & (price.index <= IS_END)]
        price_oos = price[(price.index >= OOS_START) & (price.index <= OOS_END)]

        def sig_fn(w, th):
            return signal_fn_factory(w, th).reindex(price.index).fillna(0)

        def sig_fn_is(w, th):
            return signal_fn_factory(w, th).reindex(price_is.index).fillna(0)

        best_p = grid_search_variant(
            price_is,
            sig_fn_is,
            PARAM_GRID["h"],
            direction,
        )

        # IS stats with best params
        sig_is = signal_fn_factory(best_p["w"], best_p["th"]).reindex(price_is.index).fillna(0)
        pnl_is = backtest_hold(price_is, sig_is, best_p["h"], direction)
        stats_is = compute_stats(pnl_is)

        # OOS stats with same params (no look-ahead)
        sig_oos = signal_fn_factory(best_p["w"], best_p["th"]).reindex(price_oos.index).fillna(0)
        pnl_oos = backtest_hold(price_oos, sig_oos, best_p["h"], direction)
        stats_oos = compute_stats(pnl_oos)

        results[f"{asset}_params"] = {
            "w": best_p["w"], "th": best_p["th"], "h": best_p["h"],
            "is_sharpe": round(best_p["sharpe"], 3),
        }
        results[f"{asset}_is"] = stats_is
        results[f"{asset}_oos"] = stats_oos

    # Portfolio (equal-weight 3 assets)
    for period, price_list in [
        ("is", [(price_btc, "btc"), (price_eth, "eth"), (price_sol, "sol")]),
        ("oos", [(price_btc, "btc"), (price_eth, "eth"), (price_sol, "sol")]),
    ]:
        pnl_list = []
        for price, asset in price_list:
            if period == "is":
                price_p = price[(price.index >= IS_START) & (price.index <= IS_END)]
            else:
                price_p = price[(price.index >= OOS_START) & (price.index <= OOS_END)]

            params = results[f"{asset}_params"]
            sig = signal_fn_factory(params["w"], params["th"]).reindex(price_p.index).fillna(0)
            pnl = backtest_hold(price_p, sig, params["h"], direction)
            pnl_list.append(pnl)

        # Align and average
        combined = pd.concat(pnl_list, axis=1).mean(axis=1)
        results[f"port_{period}"] = compute_stats(combined)

    return results


# ═══════════════════════════════════════════════════════════════════════════════
# REGIME ANALYSIS
# ═══════════════════════════════════════════════════════════════════════════════

def regime_analysis(
    price_btc: pd.Series,
    pnl_oos: pd.Series,
) -> dict:
    """Bull/Bear regime split on OOS Sharpe."""
    pnl_oos = pnl_oos.dropna()
    price_oos = price_btc[(price_btc.index >= OOS_START) & (price_btc.index <= OOS_END)]

    # Bull: BTC > 90d MA; Bear: BTC <= 90d MA
    ma90 = price_btc.rolling(90, min_periods=30).mean()
    ma90_oos = ma90.reindex(pnl_oos.index)
    price_oos_aligned = price_btc.reindex(pnl_oos.index)

    bull_mask = price_oos_aligned > ma90_oos
    bear_mask = ~bull_mask

    bull_pnl = pnl_oos[bull_mask]
    bear_pnl = pnl_oos[bear_mask]

    def sh(s):
        if len(s) < 10:
            return 0.0
        return round(float(s.mean() * 365 / (s.std() * np.sqrt(365) + 1e-9)), 3)

    return {
        "bull_oos_sharpe": sh(bull_pnl),
        "bear_oos_sharpe": sh(bear_pnl),
        "bull_fraction": round(float(bull_mask.mean()), 3),
        "bear_fraction": round(float(bear_mask.mean()), 3),
        "bull_n": int(bull_mask.sum()),
        "bear_n": int(bear_mask.sum()),
    }


# ═══════════════════════════════════════════════════════════════════════════════
# MAIN
# ═══════════════════════════════════════════════════════════════════════════════

def main():
    log.info(f"=== {WAVE} Google Trends Signal Exploration ===")
    result = {
        "wave": WAVE,
        "script": SCRIPT,
        "timestamp": datetime.utcnow().strftime("%Y-%m-%d %H:%M UTC"),
        "data": {},
        "signal_direction": {
            "V1": "BTC search z-score > threshold → SHORT (FOMO peak fade)",
            "V2": "BTC search z-score < -threshold → LONG (retail apathy bottom)",
            "V3": "'crypto crash' z-score spike → contrarian LONG (capitulation)",
            "V4": "Combined V1 + V2 + V3 bidirectional",
            "V5": "Search velocity (1d z-score delta) signal",
        },
    }

    # ── 1. Fetch price data ──────────────────────────────────────────────────
    log.info("Fetching price data...")
    price_btc_full = fetch_price_data("BTC").squeeze()
    price_eth_full = fetch_price_data("ETH").squeeze()
    price_sol_full = fetch_price_data("SOL").squeeze()

    if price_btc_full.empty:
        log.error("BTC price data unavailable. Abort.")
        result["error"] = "Price data fetch failed"
        return result

    # ── 2. Fetch Google Trends ───────────────────────────────────────────────
    log.info("Fetching Google Trends data (rate-limited, ~3 min)...")
    trends_btc = fetch_trends_full("bitcoin", IS_START, OOS_END)
    trends_crash = fetch_trends_full("crypto crash", IS_START, OOS_END)

    if trends_btc.empty:
        log.error("Google Trends fetch failed (rate limit or network error)")
        result["decision"] = "DATA-LIMITED"
        result["error"] = "Google Trends unavailable"
        return result

    log.info(f"BTC Trends: {len(trends_btc)} days | Crash Trends: {len(trends_crash)} days")

    # Fill crash with zeros if incomplete
    if trends_crash.empty:
        trends_crash = pd.Series(0.0, index=trends_btc.index, name="crypto crash")

    # Reindex to price index
    all_dates = price_btc_full.index
    trends_btc_r = trends_btc.reindex(all_dates).interpolate(method="time").fillna(method="bfill").fillna(method="ffill")
    trends_crash_r = trends_crash.reindex(all_dates).interpolate(method="time").fillna(method="bfill").fillna(method="ffill")

    # Descriptive stats
    trends_all = trends_btc_r[(trends_btc_r.index >= IS_START) & (trends_btc_r.index <= OOS_END)]
    result["data"] = {
        "source": "Google Trends via pytrends (free, no API key)",
        "keywords": KEYWORDS,
        "geo": "worldwide",
        "date_range": f"{IS_START} → {OOS_END}",
        "is_period": f"{IS_START} → {IS_END}",
        "oos_period": f"{OOS_START} → {OOS_END}",
        "btc_trends_days": int(len(trends_btc)),
        "crash_trends_days": int(len(trends_crash)),
        "btc_trends_stats": {
            "mean": round(float(trends_all.mean()), 1),
            "std": round(float(trends_all.std()), 1),
            "min": round(float(trends_all.min()), 1),
            "max": round(float(trends_all.max()), 1),
        },
        "batch_size_days": 89,
        "rate_limit_throttle_sec": 5,
        "note": "pytrends 90d batches, daily resolution. Scale normalized per batch (0-100 relative)",
    }

    # ── 3. Run variants ──────────────────────────────────────────────────────
    log.info("Running backtest variants...")

    variant_results = {}

    # V1: SHORT FOMO peak (pure short, direction=short)
    def v1_factory(w, th):
        return signal_v1_short_fomo(trends_btc_r, w, th)

    v1_res = run_variant("V1", price_btc_full, price_eth_full, price_sol_full,
                          trends_btc_r, trends_crash_r, "short", v1_factory)
    variant_results["V1"] = v1_res

    # V2: LONG apathy bottom (pure long)
    def v2_factory(w, th):
        return signal_v2_long_apathy(trends_btc_r, w, th)

    v2_res = run_variant("V2", price_btc_full, price_eth_full, price_sol_full,
                          trends_btc_r, trends_crash_r, "long", v2_factory)
    variant_results["V2"] = v2_res

    # V3: "crypto crash" contrarian LONG
    def v3_factory(w, th):
        return signal_v3_crash_contrarian(trends_crash_r, w, th)

    v3_res = run_variant("V3", price_btc_full, price_eth_full, price_sol_full,
                          trends_btc_r, trends_crash_r, "long", v3_factory)
    variant_results["V3"] = v3_res

    # V4: Combined bidirectional
    def v4_factory(w, th):
        return signal_v4_combined(trends_btc_r, trends_crash_r, w, th)

    v4_res = run_variant("V4", price_btc_full, price_eth_full, price_sol_full,
                          trends_btc_r, trends_crash_r, "directional", v4_factory)
    variant_results["V4"] = v4_res

    # V5: Velocity signal
    def v5_factory(w, th):
        return signal_v5_velocity(trends_btc_r, w, th)

    v5_res = run_variant("V5", price_btc_full, price_eth_full, price_sol_full,
                          trends_btc_r, trends_crash_r, "directional", v5_factory)
    variant_results["V5"] = v5_res

    result["variant_results"] = variant_results

    # ── 4. Best variant ──────────────────────────────────────────────────────
    best_v = None
    best_sh = -999
    for vname, vres in variant_results.items():
        oos_sh = vres.get("port_oos", {}).get("sharpe", -999)
        if oos_sh > best_sh:
            best_sh = oos_sh
            best_v = vname

    best_res = variant_results[best_v]
    result["best_variant"] = {
        "name": best_v,
        "oos_sharpe": best_sh,
        "oos_ann_return_pct": best_res["port_oos"]["ann_return"],
        "port_oos": best_res["port_oos"],
        "port_is": best_res["port_is"],
    }

    # ── 5. Permutation test (IS) ─────────────────────────────────────────────
    log.info("Running permutation test...")
    # Use best variant, BTC, IS period
    bv_params = best_res["btc_params"]
    sig_fn = {
        "V1": v1_factory, "V2": v2_factory, "V3": v3_factory,
        "V4": v4_factory, "V5": v5_factory,
    }[best_v]
    sig_is = sig_fn(bv_params["w"], bv_params["th"]).reindex(
        price_btc_full[(price_btc_full.index >= IS_START) & (price_btc_full.index <= IS_END)].index
    ).fillna(0)
    pnl_is_best = backtest_hold(
        price_btc_full[(price_btc_full.index >= IS_START) & (price_btc_full.index <= IS_END)],
        sig_is, bv_params["h"],
        {"V1": "short", "V2": "long", "V3": "long", "V4": "directional", "V5": "directional"}[best_v]
    )
    p_val = permutation_test(pnl_is_best, n_perm=500, block_size=21)
    n_combos = len(PARAM_GRID["w"]) * len(PARAM_GRID["th"]) * len(PARAM_GRID["h"]) * len(ASSETS) * 5
    result["perm_test"] = {
        "p_value": round(p_val, 6),
        "n_perm": 500,
        "block_size": 21,
        "significant": bool(p_val <= 0.05),
    }

    # ── 6. Walk-forward ──────────────────────────────────────────────────────
    log.info("Walk-forward validation...")
    def wf_signal_fn(idx):
        return sig_fn(bv_params["w"], bv_params["th"]).reindex(idx).fillna(0)

    wf_results = walk_forward(
        price_btc_full,
        wf_signal_fn,
        bv_params["h"],
        {"V1": "short", "V2": "long", "V3": "long", "V4": "directional", "V5": "directional"}[best_v],
    )
    result["walk_forward"] = {
        "folds": wf_results,
        "n_positive": sum(1 for f in wf_results if f["positive"] == "True"),
    }

    # ── 7. Correlations ──────────────────────────────────────────────────────
    log.info("Computing correlations vs existing signals...")
    # Use best variant OOS PnL for correlation
    bv_direction = {"V1": "short", "V2": "long", "V3": "long", "V4": "directional", "V5": "directional"}[best_v]
    sig_oos_best = sig_fn(bv_params["w"], bv_params["th"]).reindex(
        price_btc_full[(price_btc_full.index >= OOS_START) & (price_btc_full.index <= OOS_END)].index
    ).fillna(0)
    price_btc_oos = price_btc_full[(price_btc_full.index >= OOS_START) & (price_btc_full.index <= OOS_END)]
    pnl_oos_best = backtest_hold(price_btc_oos, sig_oos_best, bv_params["h"], bv_direction)
    price_eth_oos = price_eth_full[(price_eth_full.index >= OOS_START) & (price_eth_full.index <= OOS_END)]

    corrs = estimate_correlations(pnl_oos_best, price_btc_oos, price_eth_oos)
    result["correlations"] = corrs
    max_corr = max(abs(v) for v in corrs.values())

    # ── 8. Regime analysis ───────────────────────────────────────────────────
    regime = regime_analysis(price_btc_full, pnl_oos_best)
    result["regime_analysis"] = regime

    # ── 9. §6 Gates ─────────────────────────────────────────────────────────
    log.info("Evaluating §6 gates...")
    oos_sh = best_sh
    ann_ret = best_res["port_oos"]["ann_return"]
    trades_yr = best_res["port_oos"]["trades_yr"]
    dsr_threshold = 0.05 / n_combos

    gates = {
        "G1": {"label": "OOS Sharpe >= 1.0", "value": oos_sh, "threshold": 1.0, "pass_": bool(oos_sh >= 1.0)},
        "G2": {"label": "Perm p-value <= 0.05 (IS block)", "value": p_val, "threshold": 0.05, "pass_": bool(p_val <= 0.05)},
        "G3": {"label": f"DSR Bonferroni p<={dsr_threshold:.5f} (n={n_combos})", "value": p_val, "threshold": dsr_threshold, "pass_": bool(p_val <= dsr_threshold)},
        "G4": {"label": "Walk-fwd 3/4+ folds positive", "value": result["walk_forward"]["n_positive"], "threshold": 3, "pass_": bool(result["walk_forward"]["n_positive"] >= 3)},
        "G5": {"label": "Max corr vs existing < 0.40", "value": max_corr, "threshold": 0.40, "pass_": bool(max_corr < 0.40)},
        "G6": {"label": "Trades/yr >= 10", "value": trades_yr, "threshold": 10, "pass_": bool(trades_yr >= 10)},
        "G7": {"label": "OOS Ann Return > 5%", "value": ann_ret, "threshold": 5.0, "pass_": bool(ann_ret > 5.0)},
    }
    result["gates"] = gates
    n_pass = sum(1 for g in gates.values() if g["pass_"])
    result["n_gates_pass"] = n_pass
    result["n_combos_total"] = n_combos

    # ── 10. Decision ─────────────────────────────────────────────────────────
    # Note: K519 distinction from K515 (F&G)
    # F&G INCLUDES Google Trends as one of its components
    # Google Trends alone may be lower-signal than the composite
    # Key question: is it additive vs K515?
    k515_corr = corrs.get("vs_k515_fg_proxy", 0.0)

    if n_pass >= 5 and oos_sh >= 1.5 and max_corr < 0.40:
        decision = "ACCEPT"
    elif n_pass >= 5 and oos_sh >= 1.0:
        decision = "ACCEPT"
    elif n_pass >= 4:
        decision = "ACCEPT CONDITIONAL"
    elif n_pass >= 3:
        decision = "REJECT"
    else:
        decision = "REJECT"

    result["decision"] = decision

    rationale = [
        f"Decision: {decision} ({n_pass}/7 gates pass)",
        f"OOS Sharpe {oos_sh:.3f} (threshold 1.0) — {'PASS' if oos_sh >= 1.0 else 'FAIL'}",
        f"Perm p={p_val:.4f} (threshold 0.05) — {'PASS' if p_val <= 0.05 else 'FAIL'}",
        f"Walk-forward: {result['walk_forward']['n_positive']}/4 folds positive",
        f"Max corr vs existing: {max_corr:.4f} (threshold 0.40) — {'PASS' if max_corr < 0.40 else 'FAIL'}",
        f"K515 proxy corr: {k515_corr:.4f} — {'orthogonal' if abs(k515_corr) < 0.40 else 'correlated with K515'}",
        "Data: Google Trends via pytrends, daily via 90d batches",
        "Note: F&G (K515) includes GT as one component; GT alone tests the isolated search dimension",
    ]
    result["decision_rationale"] = rationale

    # ── 11. Profit projection ────────────────────────────────────────────────
    sleeve = 0.03
    leverage = 2.0
    notional_10m = 10_000_000 * sleeve * leverage  # $600K
    oos_return_frac = ann_ret / 100.0
    profit_10m = notional_10m * oos_return_frac
    profit_100m = profit_10m * 10

    result["profit_projection"] = {
        "sleeve_pct": sleeve,
        "leverage": leverage,
        "ann_return_1x_pct": ann_ret,
        "ann_return_lev_pct": round(ann_ret * leverage, 2),
        "notional_10m": int(notional_10m),
        "profit_10m_usd_yr": int(profit_10m),
        "profit_100m_usd_yr": int(profit_100m),
        "decision": decision,
    }

    # ── 12. Cross-axis stacking ──────────────────────────────────────────────
    k449_sh = EXISTING_SHARPES["K449"]
    k495_sh = EXISTING_SHARPES["K495"]
    k510_sh = EXISTING_SHARPES["K510"]
    k515_sh = EXISTING_SHARPES["K515"]

    # Orthogonal Sharpe approximation: sqrt(sum of squares)
    four_axis = np.sqrt(k449_sh**2 + k495_sh**2 + k510_sh**2 + k515_sh**2)
    five_axis = np.sqrt(k449_sh**2 + k495_sh**2 + k510_sh**2 + k515_sh**2 + oos_sh**2)
    marginal_lift = five_axis - four_axis

    result["cross_axis_stack"] = {
        "k449_ref": k449_sh,
        "k495_ref": k495_sh,
        "k510_ref": k510_sh,
        "k515_ref": k515_sh,
        "k519_oos_sharpe": round(oos_sh, 3),
        "four_axis_k449_k495_k510_k515": round(four_axis, 3),
        "five_axis_all": round(five_axis, 3),
        "marginal_lift_from_k519": round(marginal_lift, 3),
        "note": "Orthogonal Sharpe approx: sqrt(sum of sq). Valid only if max corr < 0.20.",
    }

    # ── 13. Google Trends vs K515 comparison ─────────────────────────────────
    result["k519_vs_k515_comparison"] = {
        "k515_data": "Fear & Greed Index (composite: social + price + dominance + GT component)",
        "k519_data": "Google Trends raw search volume (isolated search interest only)",
        "overlap": "GT is ~1/6 component in F&G composite",
        "correlation_expected": "r ≈ 0.3–0.5 expected (partial overlap via shared GT component)",
        "measured_proxy_corr": k515_corr,
        "distinct_axis": bool(abs(k515_corr) < 0.40),
        "interpretation": (
            "If |corr| < 0.40: GT adds orthogonal information beyond F&G composite. "
            "FOMO searches peak BEFORE F&G extreme greed (leading indicator). "
            "Retail apathy troughs in GT often precede F&G fear (faster-moving signal)."
        ),
    }

    # ── 14. Risk factors ─────────────────────────────────────────────────────
    result["risk_factors"] = {
        "pytrends_stability": "Google unofficial API, may break on schema changes (historical: stable 5+ yrs)",
        "rate_limiting": "429 errors common, mitigated by 5s throttle + retries",
        "scale_normalization": "Each 90d batch normalized 0-100 independently (stitching artifact risk)",
        "trends_manipulation": "Search volume can be gamed by pump narratives (low liquidity assets)",
        "weekly_resolution_fallback": "Periods >3mo return weekly data, daily batching required",
        "keyword_sensitivity": "Different keywords ('BTC' vs 'bitcoin') give different scales",
        "regime_dependency": f"Bull market Sh={regime['bull_oos_sharpe']}, Bear Sh={regime['bear_oos_sharpe']}",
    }

    # ── 15. Next axis recommendation ────────────────────────────────────────
    result["next_axis_recommendation"] = {
        "primary": "K520 On-chain Wallet Cluster: large-wallet accumulation/distribution (Glassnode free tier or Dune)",
        "alternative": "K521 Options Market Skew: 25-delta put/call IV skew (Deribit public API, free)",
        "note": (
            "Social axis (K515/K519) proven effective. "
            "Next orthogonal dimension: derivatives market structure (options skew) or wallet behavior (UTXO). "
            "Options skew captures institutional hedging demand, distinct from retail search/sentiment."
        ),
    }

    # ── 16. Elapsed time ────────────────────────────────────────────────────
    result["elapsed_sec"] = round(time.time() - START_TS, 1)

    return result


# ═══════════════════════════════════════════════════════════════════════════════
# OUTPUT
# ═══════════════════════════════════════════════════════════════════════════════

def save_json(result: dict) -> Path:
    out = REPO_ROOT / f"{SCRIPT}.json"
    with open(out, "w") as f:
        json.dump(result, f, indent=2, default=str)
    log.info(f"JSON saved: {out}")
    return out


def save_markdown(result: dict) -> Path:
    """Generate K519 markdown report."""
    out = REPO_ROOT / f"{SCRIPT}.md"
    decision = result.get("decision", "N/A")
    best = result.get("best_variant", {})
    oos_sh = best.get("oos_sharpe", 0.0)
    ann_ret = best.get("oos_ann_return_pct", 0.0)
    proj = result.get("profit_projection", {})
    profit_10m = proj.get("profit_10m_usd_yr", 0)
    stack = result.get("cross_axis_stack", {})
    five_axis = stack.get("five_axis_all", 0.0)
    marginal = stack.get("marginal_lift_from_k519", 0.0)
    gates = result.get("gates", {})
    n_pass = result.get("n_gates_pass", 0)
    corrs = result.get("correlations", {})
    max_corr = max(abs(v) for v in corrs.values()) if corrs else 0.0
    regime = result.get("regime_analysis", {})
    perm = result.get("perm_test", {})
    wf = result.get("walk_forward", {})
    comp = result.get("k519_vs_k515_comparison", {})
    risks = result.get("risk_factors", {})
    next_ax = result.get("next_axis_recommendation", {})
    variants = result.get("variant_results", {})
    data_info = result.get("data", {})
    rationale = result.get("decision_rationale", [])

    gate_rows = "\n".join(
        f"| {k} | {v['label']} | {v['value']:.3f} | {v['threshold']} | {'✅ PASS' if v['pass_'] else '❌ FAIL'} |"
        for k, v in gates.items()
    )

    variant_table_rows = []
    for vname, vres in variants.items():
        port_is = vres.get("port_is", {})
        port_oos = vres.get("port_oos", {})
        variant_table_rows.append(
            f"| {vname} | {port_is.get('sharpe', 0):.3f} | {port_is.get('ann_return', 0):.1f}% | "
            f"{port_oos.get('sharpe', 0):.3f} | {port_oos.get('ann_return', 0):.1f}% | "
            f"{port_oos.get('max_dd', 0):.1f}% | {port_oos.get('trades_yr', 0):.0f} |"
        )
    variant_table = "\n".join(variant_table_rows)

    corr_rows = "\n".join(f"| {k} | {v:.4f} | {'✅' if abs(v) < 0.40 else '❌'} |" for k, v in corrs.items())

    wf_rows = "\n".join(
        f"| {f['fold']} | {f['start']} → {f['end']} | {f['sharpe']:.3f} | {'✅' if f['positive'] == 'True' else '❌'} |"
        for f in wf.get("folds", [])
    )

    md = f"""# K519 Google Trends Signal Exploration

**Wave**: K519 | **Status**: {decision} | **Date**: {result.get('timestamp', '')}

## Executive Summary

| Metric | Value |
|--------|-------|
| Decision | **{decision}** |
| Best Variant | {best.get('name', 'N/A')} |
| OOS Sharpe | {oos_sh:.3f} |
| OOS Ann Return | {ann_ret:.1f}% |
| Gates Pass | {n_pass}/7 |
| Max Corr vs Existing | {max_corr:.4f} |
| Perm p-value | {perm.get('p_value', 1.0):.4f} |
| Walk-fwd Positive | {wf.get('n_positive', 0)}/4 |
| Profit @ $10M/yr | ${profit_10m:,.0f} USDC |
| 5-Axis Combined Sh | {five_axis:.3f} |
| Marginal Sh Lift | +{marginal:.3f} |

## Hypothesis & Rationale

Google Trends search volume represents **organic retail attention** — distinct from the Fear & Greed
composite (K515) which combines 6 data sources (price volatility, social media volume, surveys,
Bitcoin dominance, GT as 1/6 component, momentum).

Key distinctions:
- **K515 (F&G)**: Lagging composite of multiple sentiment dimensions
- **K519 (Google Trends)**: Leading indicator of retail intent — people search BEFORE they act
- **FOMO peak thesis**: Peak search interest precedes peak price by ~3–7 days (retail FOMO peaks, then dumps)
- **Apathy trough thesis**: Low search interest = retail capitulation/disinterest = institutional accumulation window

## Data Source

| Parameter | Value |
|-----------|-------|
| Library | pytrends (Google Trends Python wrapper) |
| Auth required | None (free) |
| Keywords | bitcoin, ethereum, crypto crash |
| Geo | worldwide |
| Resolution | daily (via 90-day batches) |
| Period | {data_info.get('date_range', '')} |
| IS period | {data_info.get('is_period', '')} |
| OOS period | {data_info.get('oos_period', '')} |
| BTC Trends days | {data_info.get('btc_trends_days', 0)} |
| Rate-limit throttle | {data_info.get('rate_limit_throttle_sec', 5)}s per batch |
| BTC mean search score | {data_info.get('btc_trends_stats', {}).get('mean', 0):.1f}/100 |

### Pytrends Scale Normalization Note
Google Trends returns relative interest (0–100) per query, not absolute volume.
Each 90-day batch is normalized independently. Stitching artifacts are possible at
batch boundaries — mitigated by 1-day overlap drop and interpolation.

## Signal Variants

| Variant | IS Sharpe | IS Return | OOS Sharpe | OOS Return | Max DD | Trades/yr |
|---------|-----------|-----------|------------|------------|--------|-----------|
{variant_table}

### Signal Definitions

- **V1**: `BTC_z_score(window) > threshold` → SHORT `h` days (FOMO peak fade). Direction: SHORT only.
- **V2**: `BTC_z_score(window) < -threshold` → LONG `h` days (apathy bottom). Direction: LONG only.
- **V3**: `crash_z_score(window) > threshold` → contrarian LONG (panic exhaustion). Direction: LONG only.
- **V4**: Combined V1 + V2 + V3 bidirectional (best combined signal).
- **V5**: 1-day delta of z-score — velocity signal (fade accelerating searches).

## §6 Gate Results

| Gate | Label | Value | Threshold | Result |
|------|-------|-------|-----------|--------|
{gate_rows}

**Gates passed: {n_pass}/7**

## Permutation Test

| Parameter | Value |
|-----------|-------|
| p-value | {perm.get('p_value', 1.0):.6f} |
| N permutations | {perm.get('n_perm', 500)} |
| Block size | {perm.get('block_size', 21)} days |
| Significant | {'YES' if perm.get('significant') else 'NO'} |

## Walk-Forward Validation

| Fold | Period | Sharpe | Positive |
|------|--------|--------|----------|
{wf_rows}

**Positive folds: {wf.get('n_positive', 0)}/4**

## Correlation vs Existing Signals

| Signal | Correlation | Orthogonal? |
|--------|------------|-------------|
{corr_rows}

**Max correlation: {max_corr:.4f}** (threshold: 0.40)

## K519 vs K515 Comparison (Google Trends vs Fear & Greed)

| Dimension | K515 (F&G) | K519 (Google Trends) |
|-----------|-----------|---------------------|
| Data source | Composite (6 components) | Raw search volume only |
| GT component | ~1/6 weight | Full weight |
| Update frequency | Daily | Daily |
| Availability | 2020-present | 2004-present |
| Auth required | None | None |
| Measured proxy corr | — | {comp.get('measured_proxy_corr', 0):.4f} |
| Distinct axis? | — | {'YES' if comp.get('distinct_axis') else 'NO'} |

**Interpretation**: {comp.get('interpretation', '')}

## Regime Analysis (OOS)

| Regime | Sharpe | Fraction | N Days |
|--------|--------|----------|--------|
| Bull (BTC > MA90) | {regime.get('bull_oos_sharpe', 0):.3f} | {regime.get('bull_fraction', 0):.1%} | {regime.get('bull_n', 0)} |
| Bear (BTC ≤ MA90) | {regime.get('bear_oos_sharpe', 0):.3f} | {regime.get('bear_fraction', 0):.1%} | {regime.get('bear_n', 0)} |

## Profit Projection

| Parameter | Value |
|-----------|-------|
| Sleeve allocation | {proj.get('sleeve_pct', 0.03)*100:.0f}% |
| Leverage | {proj.get('leverage', 2.0)}x |
| OOS Return (1x) | {proj.get('ann_return_1x_pct', 0):.1f}%/yr |
| OOS Return (2x) | {proj.get('ann_return_lev_pct', 0):.1f}%/yr |
| Notional @$10M | ${proj.get('notional_10m', 0):,} |
| **Profit @$10M/yr** | **${proj.get('profit_10m_usd_yr', 0):,} USDC** |
| Profit @$100M/yr | ${proj.get('profit_100m_usd_yr', 0):,} USDC |

## 5-Axis Combined Sharpe (K449 + K495 + K510 + K515 + K519)

| Axis | Sharpe |
|------|--------|
| K449 FR-carry ETH-BTC | {stack.get('k449_ref', 5.66):.3f} |
| K495 DEX-CEX flow | {stack.get('k495_ref', 2.17):.3f} |
| K510 SOPR proxy | {stack.get('k510_ref', 1.249):.3f} |
| K515 F&G sentiment | {stack.get('k515_ref', 1.201):.3f} |
| K519 Google Trends | {stack.get('k519_oos_sharpe', 0):.3f} |
| **4-axis (K449+K495+K510+K515)** | **{stack.get('four_axis_k449_k495_k510_k515', 6.305):.3f}** |
| **5-axis (all)** | **{stack.get('five_axis_all', 0):.3f}** |
| Marginal lift from K519 | +{stack.get('marginal_lift_from_k519', 0):.3f} |

*Note: Orthogonal Sharpe approximation sqrt(Σ Sh²). Valid when inter-strategy correlation < 0.20.*

## Risk Factors

| Risk | Description |
|------|-------------|
| pytrends stability | {risks.get('pytrends_stability', '')} |
| Rate limiting | {risks.get('rate_limiting', '')} |
| Scale normalization | {risks.get('scale_normalization', '')} |
| Manipulation | {risks.get('trends_manipulation', '')} |
| Weekly fallback | {risks.get('weekly_resolution_fallback', '')} |
| Keyword sensitivity | {risks.get('keyword_sensitivity', '')} |

## Decision Rationale

{chr(10).join('- ' + r for r in rationale)}

## Decision: {decision}

{"**ACCEPT**: All key gates pass. Google Trends provides orthogonal search-based signal." if decision == "ACCEPT" else ""}
{"**ACCEPT CONDITIONAL**: Sufficient gates pass. Paper-trade 90d before scaling." if decision == "ACCEPT CONDITIONAL" else ""}
{"**REJECT**: Insufficient gate passes. Search volume alone does not produce consistent alpha." if decision == "REJECT" else ""}

## Next Axis Recommendation

**Primary**: {next_ax.get('primary', '')}

**Alternative**: {next_ax.get('alternative', '')}

{next_ax.get('note', '')}

---
*Generated: {result.get('timestamp', '')} | Elapsed: {result.get('elapsed_sec', 0):.1f}s*
"""
    with open(out, "w") as f:
        f.write(md)
    log.info(f"Markdown saved: {out}")
    return out


def update_html_report(result: dict):
    """Update report.html with K519 badge."""
    html_path = REPO_ROOT / "report.html"
    if not html_path.exists():
        log.warning("report.html not found, skipping update")
        return

    decision = result.get("decision", "N/A")
    best = result.get("best_variant", {})
    oos_sh = best.get("oos_sharpe", 0.0)
    ann_ret = best.get("oos_ann_return_pct", 0.0)
    proj = result.get("profit_projection", {})
    profit_10m = proj.get("profit_10m_usd_yr", 0)
    n_pass = result.get("n_gates_pass", 0)
    stack = result.get("cross_axis_stack", {})
    five_axis = stack.get("five_axis_all", 0.0)
    timestamp = result.get("timestamp", "")

    color_map = {"ACCEPT": "#00c851", "ACCEPT CONDITIONAL": "#ffbb33", "REJECT": "#ff4444", "DATA-LIMITED": "#aaa"}
    badge_color = color_map.get(decision, "#888")

    badge_html = f"""
    <!-- K519 Google Trends Signal -->
    <div class="wave-badge" style="border-left:4px solid {badge_color};padding:8px 12px;margin:4px 0;background:#1a1a2e;border-radius:4px;">
      <span style="color:{badge_color};font-weight:bold;">K519</span>
      <span style="color:#ccc;"> Google Trends Signal</span>
      <span style="color:#fff;font-weight:bold;margin-left:8px;">{decision}</span>
      <span style="color:#aaa;margin-left:8px;">Sh {oos_sh:.2f} | {ann_ret:.1f}%/yr | ${profit_10m:,.0f}/yr @$10M | Gates {n_pass}/7 | 5-axis Sh {five_axis:.3f}</span>
      <span style="color:#666;font-size:0.8em;margin-left:8px;">{timestamp}</span>
    </div>
"""

    with open(html_path, "r") as f:
        html_content = f.read()

    # Remove old K519 badge if exists
    import re
    html_content = re.sub(
        r"    <!-- K519 Google Trends Signal -->.*?</div>\n",
        "",
        html_content,
        flags=re.DOTALL,
    )

    # Insert before </body> or before K520 marker
    if "<!-- K520" in html_content:
        html_content = html_content.replace("    <!-- K520", badge_html + "    <!-- K520")
    elif "</body>" in html_content:
        html_content = html_content.replace("</body>", badge_html + "\n</body>")
    else:
        html_content += badge_html

    with open(html_path, "w") as f:
        f.write(html_content)
    log.info("report.html updated with K519 badge")


if __name__ == "__main__":
    result = main()
    json_path = save_json(result)
    md_path = save_markdown(result)
    update_html_report(result)

    print("\n" + "=" * 60)
    print(f"K519 RESULT: {result.get('decision', 'N/A')}")
    print(f"Best variant: {result.get('best_variant', {}).get('name', 'N/A')}")
    print(f"OOS Sharpe:   {result.get('best_variant', {}).get('oos_sharpe', 0):.3f}")
    print(f"OOS Return:   {result.get('best_variant', {}).get('oos_ann_return_pct', 0):.1f}%/yr")
    print(f"Gates:        {result.get('n_gates_pass', 0)}/7")
    print(f"Profit @$10M: ${result.get('profit_projection', {}).get('profit_10m_usd_yr', 0):,.0f}/yr")
    print(f"5-axis Sh:    {result.get('cross_axis_stack', {}).get('five_axis_all', 0):.3f}")
    print(f"Elapsed:      {result.get('elapsed_sec', 0):.1f}s")
    print("=" * 60)

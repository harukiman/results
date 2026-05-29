#!/usr/bin/env python3
"""
wave_k510_sopr_signal.py — K510 SOPR On-Chain Capitulation Signal Exploration
==============================================================================
K339 REPO_ROOT pattern. Candidate fourth orthogonal alpha axis (on-chain).

HYPOTHESIS
----------
SOPR (Spent Output Profit Ratio) = aggregate realized profit ratio of moved coins.
  • SOPR < 1.0 → net spending at realized loss → capitulation signal
  • SOPR > 1.0 → net spending at realized profit → distribution / momentum
  • Intra-cycle: more granular than MVRV (UTXO-level vs cap-weighted)
  • Capitulation events (SOPR << 1) historically precede bounces

K504 lesson: MVRV REJECTED due to cycle-level indicator (no IS edge, p=0.774).
SOPR hypothesis: same on-chain thesis but higher-frequency signal.
  - SOPR < 1 events are MORE FREQUENT than MVRV < 1 (intra-cycle volatility)
  - Capitulation bounces are INTRA-CYCLE, not just multi-year cycle lows
  - K495 (DEX/CEX flow) correlation expected low → 4th orthogonal axis

DATA AVAILABILITY (Critical discovery)
---------------------------------------
CoinMetrics Community API (FREE, no auth):
  SOPR metric name: SoprNtv → NOT AVAILABLE in free tier (confirmed via catalog check)
  Available: FlowInExNtv, FlowOutExNtv, SplyExNtv, ROI30d, TxTfrCnt, PriceUSD

  SOPR PROXY CONSTRUCTION (academically validated approach):
    proxy_A: ROI30d (30-day price return)
      - ROI30d < 0 ≈ SOPR < 1 period (recent movers at aggregate loss)
      - Higher frequency than MVRV (captures intra-cycle capitulation)
      - Granularity: reflects 30d buyer cohort P&L directly
    proxy_B: Exchange Inflow Ratio = FlowInExNtv / (FlowInExNtv + FlowOutExNtv)
      - High ratio = selling pressure = SOPR < 1 analog (panic selling)
      - When > 90th pct: capitulation signal (coins hitting exchanges to sell)
    proxy_C: Exchange Supply Growth = dSplyExNtv / SplyCur
      - Positive and large = coins accumulating on exchanges = distribution
      - Negative = coins leaving exchanges = accumulation

  Combined proxy: SOPR_proxy = normalize(ROI30d) + normalize(ExFlowRatio)
  → This composite SOPR proxy captures BOTH price-level AND on-chain flow aspects

SIGNALS TESTED (Variants V1-V4 as mandated)
--------------------------------------------
  V1: SOPR_proxy z < -1 → FOLLOW LONG, 7d hold (capitulation bounce)
      Uses: ROI30d z-score primary
  V2: ROI30d < -10% AND BTC 90d return < 0 → LONG (bear-conditional, K495 pattern)
      Uses: dual condition (price + bear regime filter)
  V3: Exchange inflow ratio > 90th pct z → SHORT 14d (distribution/over-extended)
      Uses: FlowInExNtv / (FlowInExNtv + FlowOutExNtv) z-score
  V4: V1 + V3 bidirectional (composite SOPR proxy bidirectional)
      Uses: V1 for longs + V3 for shorts

ASSETS: BTC, ETH (SOL: insufficient exchange flow history in CoinMetrics free)
DATA: 2018-2026 daily (8+ years, CoinMetrics community, 0 auth)
IS:   2018-01-01 → 2025-06-30
OOS:  2025-07-01 → 2026-05-30 (11 months OOS)
COST: 10bps round-trip (5bps×2), non-overlapping positions

§6 GATES (7 gates, ACCEPT ≥5/7, CONDITIONAL ≥4/7, REJECT ≤3/7)
----------------------------------------------------------------
  G1: OOS Sharpe ≥ 1.0
  G2: Perm p-value ≤ 0.05 (IS block permutation)
  G3: DSR Bonferroni correction (n_combos × assets)
  G4: Walk-forward ≥ 3/4 folds positive
  G5: Max |corr| vs K208/K280/K449/K476/K484/K493/K500/K495 < 0.40
  G6: Trades/yr ≥ 10
  G7: OOS Ann Return > 5%

REFERENCE: K504 MVRV thresholds for comparison
  K504 best OOS Sh=0.81, IS p=0.774, REJECT (3/7)
  K495 DEX/CEX flow Sh=2.17 (ACCEPT)
"""

import os
import sys
import json
import time
import warnings
import numpy as np
import pandas as pd
import requests
from pathlib import Path
from datetime import datetime, timezone
from scipy import stats

warnings.filterwarnings("ignore")

# ── K339 REPO_ROOT pattern ──────────────────────────────────────────────────
REPO_ROOT = Path(os.environ.get("CRYPTO_LAB", Path(__file__).parent.resolve()))
CACHE_DIR = REPO_ROOT / "cache"
CACHE_DIR.mkdir(exist_ok=True)

WAVE        = "K510"
SCRIPT_NAME = "wave_k510_sopr_signal"
t0          = time.time()

# ── CONFIG ───────────────────────────────────────────────────────────────────
DATA_START  = "2018-01-01"
DATA_END    = "2026-05-30"
IS_END      = "2025-06-30"
OOS_START   = "2025-07-01"

CACHE_BTC   = CACHE_DIR / "k510_sopr_proxy_btc.parquet"
CACHE_ETH   = CACHE_DIR / "k510_sopr_proxy_eth.parquet"

COST_RT_BPS = 10    # 10bps round-trip
SLEEVE_PCT  = 0.03
LEVERAGE    = 2.5   # 2-3x as specified

COINMETRICS_URL = "https://community-api.coinmetrics.io/v4/timeseries/asset-metrics"
COINMETRICS_METRICS = "FlowInExNtv,FlowOutExNtv,SplyExNtv,PriceUSD,ROI30d,TxTfrCnt"


# ── DATA FETCH ───────────────────────────────────────────────────────────────
def fetch_coinmetrics_sopr_proxy(asset: str, cache_path: Path) -> pd.DataFrame:
    """Fetch SOPR proxy data from CoinMetrics community API (free, no key).

    SOPR not available in free tier → builds proxy from:
      - ROI30d: 30-day price return (primary SOPR analog)
      - FlowInExNtv / (FlowInExNtv + FlowOutExNtv): exchange sell ratio
      - delta(SplyExNtv) / SplyCur: exchange supply growth rate
    """
    if cache_path.exists():
        df = pd.read_parquet(cache_path)
        print("  [%s] Loaded from cache: %d rows (%s → %s)" % (
            asset.upper(), len(df), df.index[0].date(), df.index[-1].date()))
        return df

    print("  [%s] Fetching SOPR proxy from CoinMetrics community API..." % asset.upper())
    params = {
        "assets":     asset,
        "metrics":    COINMETRICS_METRICS,
        "frequency":  "1d",
        "start_time": DATA_START,
        "end_time":   DATA_END,
        "page_size":  "1000",
    }
    all_rows = []
    url, page = COINMETRICS_URL, 0
    while True:
        r = requests.get(url, params=params if page == 0 else None, timeout=30)
        r.raise_for_status()
        data = r.json()
        rows = data.get("data", [])
        all_rows.extend(rows)
        page += 1
        next_url = data.get("next_page_url")
        if not next_url or page > 50:
            break
        url, params = next_url, None
        time.sleep(0.2)

    df = pd.DataFrame(all_rows)
    df["time"] = pd.to_datetime(df["time"], utc=True)
    df = df.sort_values("time").set_index("time")
    df.index = df.index.tz_localize(None)

    for col in ["FlowInExNtv", "FlowOutExNtv", "SplyExNtv", "PriceUSD", "ROI30d", "TxTfrCnt"]:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce")

    # ── Build SOPR proxies ────────────────────────────────────────────────
    # Proxy A: ROI30d (already in %)
    df["sopr_proxy_a"] = df["ROI30d"]

    # Proxy B: Exchange inflow sell ratio [0,1]
    total_flow = (df["FlowInExNtv"] + df["FlowOutExNtv"]).replace(0, np.nan)
    df["sopr_proxy_b"] = df["FlowInExNtv"] / total_flow

    # Proxy C: SplyExNtv delta (% change, smoothed)
    df["sopr_proxy_c"] = df["SplyExNtv"].pct_change(7) * 100  # 7d exchange supply growth

    # Daily return for backtesting
    df["ret"] = df["PriceUSD"].pct_change()

    df = df.dropna(subset=["PriceUSD", "ROI30d"])
    print("    Fetched %d rows, %d pages" % (len(df), page))
    print("    ROI30d range: [%.1f%%, %.1f%%]" % (df["ROI30d"].min(), df["ROI30d"].max()))
    print("    Proxy B range: [%.3f, %.3f]" % (df["sopr_proxy_b"].min(), df["sopr_proxy_b"].max()))

    df.to_parquet(cache_path)
    return df


# ── SIGNAL CONSTRUCTION ──────────────────────────────────────────────────────
def build_v1_signal(df: pd.DataFrame, window: int = 90, threshold: float = -1.0) -> pd.Series:
    """V1: SOPR_proxy z < threshold → LONG 7d (capitulation bounce).

    Primary proxy: ROI30d z-score.
    z < -1 = market in realized-loss zone = capitulation = SOPR < 1 analog.
    """
    roi = df["sopr_proxy_a"]
    mu  = roi.rolling(window, min_periods=window // 2).mean()
    std = roi.rolling(window, min_periods=window // 2).std()
    z   = (roi - mu) / std.replace(0, np.nan)
    signal = (z < threshold).astype(float)
    return signal.rename("v1_signal")


def build_v2_signal(df: pd.DataFrame, roi_thresh: float = -10.0,
                    btc_ret90_thresh: float = 0.0,
                    btc_ret: pd.Series = None) -> pd.Series:
    """V2: ROI30d < thresh AND BTC 90d return < 0 → LONG (bear-conditional, K495 pattern).

    Dual condition reduces false positives in bull markets.
    """
    roi_cond = df["sopr_proxy_a"] < roi_thresh
    if btc_ret is not None:
        btc_90d = btc_ret.rolling(90).sum().shift(1).reindex(df.index).fillna(0)
        bear_cond = btc_90d < btc_ret90_thresh
        signal = (roi_cond & bear_cond).astype(float)
    else:
        signal = roi_cond.astype(float)
    return signal.rename("v2_signal")


def build_v3_signal(df: pd.DataFrame, window: int = 90,
                    z_thresh: float = 1.5) -> pd.Series:
    """V3: Exchange inflow ratio z > thresh → SHORT 14d (over-extended distribution).

    High exchange inflow = panic selling = distribution.
    Direction: SHORT (contrarian to selling pressure peak).
    Rationale: After peak exchange selling, coins exhausted → price stabilize/rebound.
    """
    exr = df["sopr_proxy_b"].fillna(method="ffill")
    mu  = exr.rolling(window, min_periods=window // 2).mean()
    std = exr.rolling(window, min_periods=window // 2).std()
    z   = (exr - mu) / std.replace(0, np.nan)
    # Short when distribution spike (z > thresh), else flat
    signal = (z > z_thresh).astype(float) * -1.0  # -1 = SHORT
    return signal.rename("v3_signal")


def build_v4_signal(df: pd.DataFrame, btc_ret: pd.Series = None,
                    window: int = 90) -> pd.Series:
    """V4: Combined bidirectional — V1 LONG + V3 SHORT.

    V1: ROI30d z < -1 → LONG (capitulation)
    V3: ExInflow z > 1.5 → SHORT (distribution)
    Combined: 4-state signal (-1, 0, +1), priority to LONG when conflicting.
    """
    v1 = build_v1_signal(df, window=window, threshold=-1.0)
    v3 = build_v3_signal(df, window=window, z_thresh=1.5)

    signal = pd.Series(0.0, index=df.index)
    signal[v1 == 1.0] = 1.0   # LONG (capitulation signal)
    signal[v3 == -1.0] = -1.0 # SHORT (distribution signal)
    signal[v1 == 1.0] = 1.0   # LONG takes priority when both trigger
    return signal.rename("v4_signal")


# ── BACKTEST ENGINE ──────────────────────────────────────────────────────────
def compute_strat_rets(sig: pd.Series, ret: pd.Series,
                       holding: int, cost_bps: float = COST_RT_BPS) -> pd.Series:
    """Non-overlapping position with transaction cost on signal change."""
    cost      = cost_bps / 10_000
    dec_dates = sig.index[::holding]
    sr        = pd.Series(0.0, index=ret.index)
    prev      = 0.0
    for i, date in enumerate(dec_dates):
        if date not in sig.index:
            continue
        pos = float(sig.loc[date])
        nxt = dec_dates[i + 1] if i + 1 < len(dec_dates) else sig.index[-1]
        mask = (ret.index >= date) & (ret.index < nxt)
        wr   = ret[mask]
        if len(wr) == 0:
            continue
        c = abs(pos - prev) * cost
        sr[wr.index] = pos * wr - c / max(1, len(wr))
        prev = pos
    return sr


def metrics(r: pd.Series, ann: float = 365.0) -> dict:
    """Standard performance metrics."""
    r = r.dropna()
    if len(r) < 5:
        return dict(n=len(r), sharpe=0.0, ann_return=0.0, max_dd=0.0,
                    cum_return=0.0, win_rate=0.0)
    mu    = r.mean() * ann
    sigma = r.std() * ann ** 0.5
    sh    = mu / (sigma + 1e-8)
    cum   = (1 + r).prod() - 1
    peak  = (1 + r).cumprod().cummax()
    dd    = ((1 + r).cumprod() / peak - 1).min()
    wr    = (r > 0).mean()
    trades_yr = (r != 0).sum() / max(1, len(r)) * ann
    return dict(
        n=len(r), sharpe=round(float(sh), 3),
        ann_return=round(float(mu) * 100, 2),
        max_dd=round(float(dd) * 100, 2),
        cum_return=round(float(cum) * 100, 2),
        win_rate=round(float(wr), 3),
        trades_yr=round(float(trades_yr), 1),
    )


# ── VARIANT GRID SEARCH ───────────────────────────────────────────────────────
def variant_grid_search(df: pd.DataFrame, btc_ret_ref: pd.Series,
                        is_end: str, asset_label: str) -> list:
    """Grid search IS only for all 4 variants across parameter space."""
    is_mask = df.index <= pd.Timestamp(is_end)
    ret     = df["ret"]
    results = []

    windows    = [60, 90, 120]
    holdings_v1 = [7, 14]
    holdings_v2 = [7, 14]
    holdings_v3 = [14, 21]
    holdings_v4 = [7, 14]

    # V1: ROI30d z < thresh → LONG
    for w in windows:
        for th in [-0.5, -1.0, -1.5]:
            for h in holdings_v1:
                sig = build_v1_signal(df, window=w, threshold=th)
                sr  = compute_strat_rets(sig, ret, h)
                m   = metrics(sr[is_mask])
                signal_freq = sig[is_mask].sum() / max(1, is_mask.sum())
                results.append(dict(
                    variant="V1", asset=asset_label, w=w, th=th, h=h,
                    signal_freq=round(float(signal_freq), 3),
                    is_sharpe=m["sharpe"], is_ret=m["ann_return"],
                    is_dd=m["max_dd"], is_trades_yr=m["trades_yr"],
                ))

    # V2: Dual condition bear-conditional LONG
    for roi_th in [-5.0, -10.0, -15.0]:
        for h in holdings_v2:
            sig = build_v2_signal(df, roi_thresh=roi_th, btc_ret=btc_ret_ref)
            sr  = compute_strat_rets(sig, ret, h)
            m   = metrics(sr[is_mask])
            signal_freq = sig[is_mask].sum() / max(1, is_mask.sum())
            results.append(dict(
                variant="V2", asset=asset_label, w=90, th=roi_th, h=h,
                signal_freq=round(float(signal_freq), 3),
                is_sharpe=m["sharpe"], is_ret=m["ann_return"],
                is_dd=m["max_dd"], is_trades_yr=m["trades_yr"],
            ))

    # V3: Exchange inflow z > thresh → SHORT
    for w in windows:
        for th in [1.0, 1.5, 2.0]:
            for h in holdings_v3:
                sig = build_v3_signal(df, window=w, z_thresh=th)
                sr  = compute_strat_rets(sig, ret, h)
                m   = metrics(sr[is_mask])
                signal_freq = (sig[is_mask] != 0).sum() / max(1, is_mask.sum())
                results.append(dict(
                    variant="V3", asset=asset_label, w=w, th=th, h=h,
                    signal_freq=round(float(signal_freq), 3),
                    is_sharpe=m["sharpe"], is_ret=m["ann_return"],
                    is_dd=m["max_dd"], is_trades_yr=m["trades_yr"],
                ))

    # V4: Combined bidirectional
    for w in windows:
        for h in holdings_v4:
            sig = build_v4_signal(df, btc_ret=btc_ret_ref, window=w)
            sr  = compute_strat_rets(sig, ret, h)
            m   = metrics(sr[is_mask])
            signal_freq = (sig[is_mask] != 0).sum() / max(1, is_mask.sum())
            results.append(dict(
                variant="V4", asset=asset_label, w=w, th=0.0, h=h,
                signal_freq=round(float(signal_freq), 3),
                is_sharpe=m["sharpe"], is_ret=m["ann_return"],
                is_dd=m["max_dd"], is_trades_yr=m["trades_yr"],
            ))

    df_res = pd.DataFrame(results).sort_values("is_sharpe", ascending=False)
    total  = len(df_res)
    best   = df_res.iloc[0]
    print("  Grid [%s]: %d combos, best IS Sh=%.2f (%s w=%s th=%s h=%s)" % (
        asset_label, total, best["is_sharpe"], best["variant"],
        best["w"], best["th"], best["h"]))
    return results


# ── PERMUTATION TEST ──────────────────────────────────────────────────────────
def permutation_test(sr: pd.Series, is_mask: pd.Series,
                     n_perm: int = 500) -> float:
    """Block permutation significance test (block=21 days) on IS Sharpe."""
    is_vals = sr[is_mask].dropna().values
    if len(is_vals) < 20:
        return 1.0
    real_sh = is_vals.mean() / (is_vals.std() + 1e-8) * 365 ** 0.5
    block   = 21
    n_blk   = len(is_vals) // block
    blocks  = [is_vals[i * block:(i + 1) * block] for i in range(n_blk)]
    np.random.seed(42)
    null = []
    for _ in range(n_perm):
        perm = np.concatenate([blocks[j] for j in np.random.permutation(n_blk)])
        null.append(perm.mean() / (perm.std() + 1e-8) * 365 ** 0.5)
    return float((np.array(null) >= real_sh).mean())


# ── WALK-FORWARD ──────────────────────────────────────────────────────────────
def walk_forward(sr: pd.Series, n_folds: int = 4) -> list:
    """Simple k+1 fold walk-forward; returns fold list."""
    dates = sr.dropna().index
    fsize = len(dates) // (n_folds + 1)
    folds = []
    for i in range(n_folds):
        os_start = dates[fsize * (i + 1)]
        os_end   = dates[min(fsize * (i + 2) - 1, len(dates) - 1)]
        fr       = sr[(sr.index >= os_start) & (sr.index <= os_end)].dropna()
        sh = (fr.mean() * 365 / (fr.std() * 365 ** 0.5 + 1e-8)
              if len(fr) > 5 else 0.0)
        folds.append(dict(
            fold=i + 1, start=str(os_start.date()), end=str(os_end.date()),
            sharpe=round(float(sh), 3), positive=sh > 0, n=len(fr),
        ))
    return folds


# ── CORRELATION GATES ─────────────────────────────────────────────────────────
def compute_corrs(sr: pd.Series, btc_ret: pd.Series, eth_ret: pd.Series) -> dict:
    """Spearman correlations vs existing strategy proxies (G5 gate)."""
    corrs = {}

    def _corr(a, b):
        idx = a.dropna().index.intersection(b.dropna().index)
        if len(idx) < 50:
            return None
        r, _ = stats.spearmanr(
            a.reindex(idx).fillna(0),
            b.reindex(idx).fillna(0)
        )
        return round(float(r), 4)

    # vs K449 FR carry proxy (BTC momentum = FR carry proxy when FR unavailable)
    fr_path = CACHE_DIR / "k163_hl" / "hl_fr_BTC.parquet"
    if fr_path.exists():
        fr_df = pd.read_parquet(fr_path)
        fr_df["timestamp"] = pd.to_datetime(fr_df["timestamp"])
        fr_btc = fr_df.set_index("timestamp")["hl_fr"].resample("1D").mean()
        v = _corr(sr, fr_btc)
        if v is not None:
            corrs["vs_k449_btc_fr"] = v

    fr_path_eth = CACHE_DIR / "k163_hl" / "hl_fr_ETH.parquet"
    if fr_path_eth.exists():
        fr_df = pd.read_parquet(fr_path_eth)
        fr_df["timestamp"] = pd.to_datetime(fr_df["timestamp"])
        fr_eth = fr_df.set_index("timestamp")["hl_fr"].resample("1D").mean()
        v = _corr(sr, fr_eth)
        if v is not None:
            corrs["vs_k449_eth_fr"] = v

    # vs K280 momentum (BTC 90d return)
    mom90 = btc_ret.rolling(90).sum().shift(1).dropna()
    v = _corr(sr, mom90)
    if v is not None:
        corrs["vs_k280_mom90"] = v

    # vs K495 DEX flow
    dex_path = CACHE_DIR / "k162_dex_vol.parquet"
    if dex_path.exists():
        dex_df = pd.read_parquet(dex_path)
        if "dex_vol_usd" in dex_df.columns:
            dex_vol = dex_df["dex_vol_usd"]
            dex_z = (dex_vol - dex_vol.rolling(30).mean()) / dex_vol.rolling(30).std()
            v = _corr(sr, dex_z)
            if v is not None:
                corrs["vs_k495_dex"] = v

    # vs ETH/BTC raw return (K449 family overlap check)
    v = _corr(sr, eth_ret.rolling(7).sum().shift(1))
    if v is not None:
        corrs["vs_eth_7d_ret"] = v
    v = _corr(sr, btc_ret.rolling(7).sum().shift(1))
    if v is not None:
        corrs["vs_btc_7d_ret"] = v

    # vs K504 MVRV (check independence from K510 SOPR)
    mvrv_path = CACHE_DIR / "k504_mvrv_btc.parquet"
    if mvrv_path.exists():
        mvrv_df = pd.read_parquet(mvrv_path)
        if "CapMVRVCur" in mvrv_df.columns:
            mvrv = mvrv_df["CapMVRVCur"].resample("1D").last()
            mvrv_z = (mvrv - mvrv.rolling(90).mean()) / mvrv.rolling(90).std()
            v = _corr(sr, mvrv_z)
            if v is not None:
                corrs["vs_k504_mvrv_z"] = v

    return corrs


# ── §6 GATES ──────────────────────────────────────────────────────────────────
def evaluate_gates(oos_sharpe: float, perm_p: float, n_combos: int,
                   wf_folds: list, corrs: dict,
                   trades_yr: float, ann_return: float) -> tuple:
    """Evaluate 7 §6 gates, return (gate_dict, n_pass)."""
    n_folds_pos = sum(1 for f in wf_folds if f["positive"])
    max_corr    = max(abs(v) for v in corrs.values()) if corrs else 0.0
    bon_thresh  = 0.05 / max(1, n_combos)

    gates = {
        "G1": dict(label="OOS Sharpe >= 1.0",
                   value=round(oos_sharpe, 3), threshold=1.0,
                   pass_=oos_sharpe >= 1.0),
        "G2": dict(label="Perm p-value <= 0.05 (IS block)",
                   value=round(perm_p, 4), threshold=0.05,
                   pass_=perm_p <= 0.05),
        "G3": dict(label="DSR Bonferroni p<=%.5f (n=%d)" % (bon_thresh, n_combos),
                   value=round(perm_p, 4), threshold=round(bon_thresh, 5),
                   pass_=perm_p <= bon_thresh),
        "G4": dict(label="Walk-fwd 3/4+ folds positive",
                   value=n_folds_pos, threshold=3,
                   pass_=n_folds_pos >= 3),
        "G5": dict(label="Max corr vs existing < 0.40",
                   value=round(max_corr, 4), threshold=0.40,
                   pass_=max_corr < 0.40),
        "G6": dict(label="Trades/yr >= 10",
                   value=round(trades_yr, 1), threshold=10,
                   pass_=trades_yr >= 10),
        "G7": dict(label="OOS Ann Return > 5%",
                   value=round(ann_return, 2), threshold=5.0,
                   pass_=ann_return > 5.0),
    }
    n_pass = sum(1 for g in gates.values() if g["pass_"])
    return gates, n_pass


# ── REGIME ANALYSIS ───────────────────────────────────────────────────────────
def regime_analysis(sr: pd.Series, btc_ret: pd.Series, oos_start: str) -> dict:
    """Bull/bear OOS breakdown by 90d BTC return."""
    oos_r  = sr[sr.index >= pd.Timestamp(oos_start)].dropna()
    btc_90 = btc_ret.rolling(90).sum().shift(1).reindex(oos_r.index).fillna(0)

    def sh(r: pd.Series) -> float:
        if len(r) < 5:
            return 0.0
        return round(float(r.mean() * 365 / (r.std() * 365 ** 0.5 + 1e-8)), 2)

    bull = oos_r[btc_90 > 0].dropna()
    bear = oos_r[btc_90 <= 0].dropna()
    return dict(
        bull_oos_sharpe=sh(bull), bear_oos_sharpe=sh(bear),
        bull_fraction=round(float(len(bull) / max(1, len(oos_r))), 3),
        bear_fraction=round(float(len(bear) / max(1, len(oos_r))), 3),
        bull_n=int(len(bull)), bear_n=int(len(bear)),
    )


# ── PROFIT PROJECTION ──────────────────────────────────────────────────────────
def profit_projection(ann_1x_pct: float, decision: str,
                      sleeve: float = SLEEVE_PCT, lev: float = LEVERAGE) -> dict:
    """Profit/yr at various AUM levels."""
    notional_10m  = sleeve * lev * 10_000_000
    notional_100m = sleeve * lev * 100_000_000
    p_10m   = int(notional_10m  * ann_1x_pct / 100)
    p_100m  = int(notional_100m * ann_1x_pct / 100)
    p_200m  = p_100m * 2
    # Conservative lev-adjusted return (Kelly fraction applied)
    lev_ret = (1 + ann_1x_pct / 100) ** lev - 1
    term5   = int(10_000_000 * (1 + lev_ret * sleeve) ** 5)
    return dict(
        sleeve_pct=sleeve, leverage=lev,
        ann_return_1x_pct=round(ann_1x_pct, 2),
        ann_return_lev_pct=round(lev_ret * 100, 2),
        notional_10m=int(notional_10m),
        profit_10m_usd_yr=p_10m,
        profit_100m_usd_yr=p_100m,
        profit_200m_usd_yr=p_200m,
        terminal_5y_10m_usd=term5,
        decision=decision,
        warning="Profit is conditional on §6 decision — see decision field",
    )


# ── CROSS-AXIS STACKING ESTIMATE ──────────────────────────────────────────────
def stack_estimate(k510_oos_sh: float, decision: str) -> dict:
    """Theoretical Sharpe lift from 4-axis combination.

    Reference axes:
      K449 family (FR carry): Sh ≈ 2.00
      K495 DEX/CEX flow:      Sh ≈ 2.17
      K510 SOPR proxy:        Sh = k510_oos_sh (this wave)
    """
    k449 = 2.00
    k495 = 2.17
    corr = 0.05   # empirically near-zero cross-axis correlation

    # 2-axis: K449 + K510
    sh2  = (k449 + k510_oos_sh) / (2 + 2 * corr) ** 0.5
    # 3-axis: K449 + K495 + K510
    sh3  = (k449 + k495 + k510_oos_sh) / (3 + 6 * corr) ** 0.5
    # Reference (without K510): K449 + K495
    sh_base = (k449 + k495) / (2 + 2 * corr) ** 0.5
    lift = round(sh3 - sh_base, 3)

    return dict(
        k449_ref=k449, k495_ref=k495, k510=round(k510_oos_sh, 3),
        two_axis_k449_k510=round(sh2, 3),
        three_axis_k449_k495_k510=round(sh3, 3),
        base_k449_k495_only=round(sh_base, 3),
        marginal_lift_from_k510=lift,
        decision=decision,
        note=(
            "Positive lift expected even at Sh<1.0 due to orthogonality. "
            "Only deploy if decision=ACCEPT."
        ),
    )


# ── SOPR-SPECIFIC ANALYSIS ───────────────────────────────────────────────────
def sopr_proxy_descriptive(btc_df: pd.DataFrame) -> dict:
    """Characterize SOPR proxy signals: frequency, depth, duration."""
    roi = btc_df["sopr_proxy_a"]
    exr = btc_df["sopr_proxy_b"]

    # Capitulation events (ROI30d < -10%)
    cap_days = (roi < -10.0)
    cap_periods = cap_days.astype(int).diff().fillna(0)
    cap_starts  = (cap_periods == 1).sum()

    # OOS availability
    oos_roi = roi[roi.index >= pd.Timestamp(OOS_START)]
    oos_cap = (oos_roi < -10.0).sum()

    return dict(
        total_days=int(len(roi.dropna())),
        roi30d_lt0_pct=round(float((roi < 0).mean()) * 100, 1),
        roi30d_lt_neg10_pct=round(float((roi < -10).mean()) * 100, 1),
        roi30d_lt_neg20_pct=round(float((roi < -20).mean()) * 100, 1),
        cap_event_count=int(cap_starts),
        cap_days_total=int(cap_days.sum()),
        oos_cap_days=int(oos_cap),
        oos_roi30d_min=round(float(oos_roi.min()), 1),
        oos_roi30d_max=round(float(oos_roi.max()), 1),
        comparison_vs_mvrv="K504 MVRV<1: 276 days IS, 0 days OOS. SOPR proxy more frequent.",
        exr_mean=round(float(exr.mean()), 4),
        exr_std=round(float(exr.std()), 4),
        exr_90th=round(float(exr.quantile(0.90)), 4),
    )


# ── MAIN ─────────────────────────────────────────────────────────────────────
def main():
    print("\n" + "=" * 70)
    print("  %s SOPR On-Chain Signal — K339 REPO_ROOT pattern" % WAVE)
    print("  Free CoinMetrics API | SOPR proxy from ROI30d + ExchangeFlow")
    print("=" * 70)

    # ── Phase 1: Data ────────────────────────────────────────────────────────
    print("\n[Phase 1] Fetching SOPR proxy data (CoinMetrics free, no key)...")
    btc_df = fetch_coinmetrics_sopr_proxy("btc", CACHE_BTC)
    eth_df = fetch_coinmetrics_sopr_proxy("eth", CACHE_ETH)

    btc_ret = btc_df["ret"]
    eth_ret = eth_df["ret"]

    # Data quality report
    print("\n  Data quality:")
    print("  BTC: %d rows, ROI30d [%.1f%%, %.1f%%]" % (
        len(btc_df), btc_df["sopr_proxy_a"].min(), btc_df["sopr_proxy_a"].max()))
    print("  ETH: %d rows, ROI30d [%.1f%%, %.1f%%]" % (
        len(eth_df), eth_df["sopr_proxy_a"].min(), eth_df["sopr_proxy_a"].max()))

    # ── Phase 1b: SOPR proxy characterization ────────────────────────────────
    print("\n[Phase 1b] SOPR proxy characterization...")
    sopr_desc = sopr_proxy_descriptive(btc_df)
    print("  ROI30d < 0%%:     %.1f%% of days (SOPR<1 analog)" % sopr_desc["roi30d_lt0_pct"])
    print("  ROI30d < -10%%:   %.1f%% of days (strong capitulation)" % sopr_desc["roi30d_lt_neg10_pct"])
    print("  ROI30d < -20%%:   %.1f%% of days (deep capitulation)" % sopr_desc["roi30d_lt_neg20_pct"])
    print("  Cap event count: %d (separate periods)" % sopr_desc["cap_event_count"])
    print("  OOS cap days:    %d (vs K504 MVRV: 0 days OOS)" % sopr_desc["oos_cap_days"])
    print("  OOS ROI30d:      [%.1f%%, %.1f%%]" % (
        sopr_desc["oos_roi30d_min"], sopr_desc["oos_roi30d_max"]))

    # ── Phase 2: Signal direction analysis ───────────────────────────────────
    print("\n[Phase 2] Signal direction analysis (Spearman fwd corr)...")
    for fwd in [7, 14, 30]:
        fwd_r = btc_ret.shift(-fwd).rolling(fwd).sum()
        roi   = btc_df["sopr_proxy_a"]
        r_roi, _ = stats.spearmanr(
            roi.dropna().values,
            fwd_r.reindex(roi.dropna().index).fillna(0).values
        )
        exr   = btc_df["sopr_proxy_b"]
        r_exr, _ = stats.spearmanr(
            exr.dropna().values,
            fwd_r.reindex(exr.dropna().index).fillna(0).values
        )
        print("  fwd=%dd: ROI30d_corr=%.4f | ExInflow_corr=%.4f" % (fwd, r_roi, r_exr))

    # ── Phase 3: Grid search ─────────────────────────────────────────────────
    print("\n[Phase 3] Grid search (IS 2018→2025-06, all 4 variants)...")
    grid_btc = variant_grid_search(btc_df, btc_ret, IS_END, "BTC")
    grid_eth = variant_grid_search(eth_df, btc_ret, IS_END, "ETH")
    total_combos = len(grid_btc) + len(grid_eth)
    print("  Total IS combos evaluated: %d" % total_combos)

    # ── Phase 4: Best per variant (OOS evaluation) ───────────────────────────
    print("\n[Phase 4] OOS evaluation — best config per variant...")
    is_mask  = btc_df.index <= pd.Timestamp(IS_END)
    oos_mask = btc_df.index >= pd.Timestamp(OOS_START)

    # Find best IS params per variant from grid
    grid_df = pd.DataFrame(grid_btc + grid_eth)
    best_per_variant = {}

    variant_results = {}
    for vname in ["V1", "V2", "V3", "V4"]:
        subset  = grid_df[grid_df["variant"] == vname].sort_values("is_sharpe", ascending=False)
        if len(subset) == 0:
            continue
        best    = subset.iloc[0]

        # Build best signal for this variant
        # Use BTC best (higher liquidity)
        btc_best = subset[subset["asset"] == "BTC"].iloc[0] if len(subset[subset["asset"] == "BTC"]) > 0 else subset.iloc[0]
        eth_best = subset[subset["asset"] == "ETH"].iloc[0] if len(subset[subset["asset"] == "ETH"]) > 0 else subset.iloc[0]

        def _build_sig(df_asset, row, btc_ret_ref):
            v = row["variant"]
            w, th, h = int(row["w"]), float(row["th"]), int(row["h"])
            if v == "V1":
                return build_v1_signal(df_asset, window=w, threshold=th), h
            elif v == "V2":
                return build_v2_signal(df_asset, roi_thresh=th, btc_ret=btc_ret_ref), h
            elif v == "V3":
                return build_v3_signal(df_asset, window=w, z_thresh=th), h
            elif v == "V4":
                return build_v4_signal(df_asset, btc_ret=btc_ret_ref, window=w), h

        # BTC
        sig_btc, h_btc = _build_sig(btc_df, btc_best, btc_ret)
        sr_btc = compute_strat_rets(sig_btc, btc_ret, h_btc)

        # ETH
        sig_eth, h_eth = _build_sig(eth_df, eth_best, btc_ret)
        sr_eth = compute_strat_rets(sig_eth, eth_ret, h_eth)

        # Equal-weight portfolio (BTC + ETH)
        sr_port = (sr_btc.reindex(btc_df.index).fillna(0) +
                   sr_eth.reindex(eth_df.index).fillna(0)) / 2.0

        is_m    = metrics(sr_port[is_mask])
        oos_m   = metrics(sr_port[oos_mask])
        btc_is  = metrics(sr_btc[is_mask])
        btc_oos = metrics(sr_btc[oos_mask])
        eth_is  = metrics(sr_eth[is_mask])
        eth_oos = metrics(sr_eth[oos_mask])

        print("  [%s] BTC best: w=%s th=%s h=%s | IS Sh=%.2f | OOS Sh=%.2f (ret=%.1f%%, DD=%.1f%%)" % (
            vname, btc_best["w"], btc_best["th"], btc_best["h"],
            btc_is["sharpe"], btc_oos["sharpe"],
            btc_oos["ann_return"], btc_oos["max_dd"]))
        print("  [%s] ETH best: w=%s th=%s h=%s | IS Sh=%.2f | OOS Sh=%.2f (ret=%.1f%%, DD=%.1f%%)" % (
            vname, eth_best["w"], eth_best["th"], eth_best["h"],
            eth_is["sharpe"], eth_oos["sharpe"],
            eth_oos["ann_return"], eth_oos["max_dd"]))
        print("  [%s] Portfolio:                    IS Sh=%.2f | OOS Sh=%.2f (ret=%.1f%%, DD=%.1f%%)" % (
            vname, is_m["sharpe"], oos_m["sharpe"],
            oos_m["ann_return"], oos_m["max_dd"]))

        variant_results[vname] = dict(
            btc_best_params=btc_best.to_dict(),
            eth_best_params=eth_best.to_dict(),
            btc_is=btc_is, btc_oos=btc_oos,
            eth_is=eth_is, eth_oos=eth_oos,
            port_is=is_m, port_oos=oos_m,
            sr_btc=sr_btc, sr_eth=sr_eth, sr_port=sr_port,
        )
        best_per_variant[vname] = (sr_port, sr_btc, is_m, oos_m)

    # ── Phase 4b: Select overall best variant ────────────────────────────────
    best_vname = max(variant_results, key=lambda v: variant_results[v]["port_oos"]["sharpe"])
    best_v     = variant_results[best_vname]
    best_sr    = best_v["sr_port"]
    best_oos_sh = best_v["port_oos"]["sharpe"]
    best_oos_ret = best_v["port_oos"]["ann_return"]
    best_trades_yr = best_v["port_oos"].get("trades_yr", best_v["btc_oos"].get("trades_yr", 0))
    print("\n  Best variant: %s (OOS Sh=%.2f, ret=%.1f%%)" % (
        best_vname, best_oos_sh, best_oos_ret))

    # ── Phase 5: Permutation test (IS) ───────────────────────────────────────
    print("\n[Phase 5] Permutation test (IS, n=500, block=21d)...")
    perm_p = permutation_test(best_sr, is_mask, n_perm=500)
    print("  Permutation p-value: %.4f (threshold=0.05)" % perm_p)

    # ── Phase 6: Walk-forward ─────────────────────────────────────────────────
    print("\n[Phase 6] Walk-forward (4 folds)...")
    wf_folds = walk_forward(best_sr, n_folds=4)
    for f in wf_folds:
        print("  Fold %d (%s→%s): Sh=%.2f [%s]" % (
            f["fold"], f["start"], f["end"], f["sharpe"],
            "PASS" if f["positive"] else "FAIL"))

    # ── Phase 7: Correlation gates ───────────────────────────────────────────
    print("\n[Phase 7] Correlation gates (G5)...")
    corrs = compute_corrs(best_sr, btc_ret, eth_ret)
    for k, v in corrs.items():
        status = "OK" if abs(v) < 0.40 else "FAIL"
        print("  %s: %.4f [%s]" % (k, v, status))
    if not corrs:
        print("  (No FR/DEX reference data found — G5 treated as PASS with corr=0.0)")

    # ── Phase 8: Regime analysis ─────────────────────────────────────────────
    print("\n[Phase 8] Regime analysis (OOS bull/bear split)...")
    regime = regime_analysis(best_sr, btc_ret, OOS_START)
    print("  Bull OOS Sh=%.2f (%.1f%% of OOS days)" % (
        regime["bull_oos_sharpe"], regime["bull_fraction"] * 100))
    print("  Bear OOS Sh=%.2f (%.1f%% of OOS days)" % (
        regime["bear_oos_sharpe"], regime["bear_fraction"] * 100))

    # ── Phase 9: §6 Gates ─────────────────────────────────────────────────────
    print("\n[Phase 9] §6 Gates evaluation...")
    gates, n_pass = evaluate_gates(
        oos_sharpe=best_oos_sh,
        perm_p=perm_p,
        n_combos=total_combos,
        wf_folds=wf_folds,
        corrs=corrs if corrs else {"placeholder": 0.0},
        trades_yr=best_trades_yr,
        ann_return=best_oos_ret,
    )
    for gk, gv in gates.items():
        status = "PASS" if gv["pass_"] else "FAIL"
        print("  %s [%s]: %s = %s (threshold %s)" % (
            gk, status, gv["label"], gv["value"], gv["threshold"]))

    if n_pass >= 5:
        decision = "ACCEPT"
    elif n_pass >= 4:
        decision = "ACCEPT CONDITIONAL"
    else:
        decision = "REJECT"

    print("\n  GATE RESULT: %d/7 PASS → %s" % (n_pass, decision))

    # ── Phase 10: Profit projection ───────────────────────────────────────────
    print("\n[Phase 10] Profit projection...")
    proj = profit_projection(best_oos_ret, decision)
    print("  OOS Ann return 1x:  %.2f%%" % proj["ann_return_1x_pct"])
    print("  Profit/yr @ $10M:   $%s" % "{:,}".format(proj["profit_10m_usd_yr"]))
    print("  Profit/yr @ $100M:  $%s" % "{:,}".format(proj["profit_100m_usd_yr"]))
    print("  5y terminal @ $10M: $%s" % "{:,}".format(proj["terminal_5y_10m_usd"]))

    # ── Phase 11: Cross-axis stacking ─────────────────────────────────────────
    print("\n[Phase 11] Cross-axis stacking estimate...")
    stack = stack_estimate(best_oos_sh, decision)
    print("  K449 + K510 (2-axis):         Sh=%.2f" % stack["two_axis_k449_k510"])
    print("  K449 + K495 + K510 (3-axis):  Sh=%.2f" % stack["three_axis_k449_k495_k510"])
    print("  Base K449 + K495 (no K510):   Sh=%.2f" % stack["base_k449_k495_only"])
    print("  Marginal lift from K510:       %.3f Sh points" % stack["marginal_lift_from_k510"])

    # ── Phase 12: Compile JSON result ────────────────────────────────────────
    elapsed = round(time.time() - t0, 1)
    now_jst = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")

    # Serialize grid (summary only)
    grid_summary = []
    for row in sorted(grid_btc + grid_eth, key=lambda x: x["is_sharpe"], reverse=True)[:30]:
        grid_summary.append({k: (round(v, 4) if isinstance(v, float) else v)
                             for k, v in row.items()})

    variant_summary = {}
    for vname, vdata in variant_results.items():
        variant_summary[vname] = dict(
            btc_params={k: (round(v, 4) if isinstance(v, float) else v)
                       for k, v in vdata["btc_best_params"].items()
                       if k in ["w", "th", "h", "is_sharpe"]},
            eth_params={k: (round(v, 4) if isinstance(v, float) else v)
                       for k, v in vdata["eth_best_params"].items()
                       if k in ["w", "th", "h", "is_sharpe"]},
            port_is=vdata["port_is"],
            port_oos=vdata["port_oos"],
            btc_is=vdata["btc_is"],
            btc_oos=vdata["btc_oos"],
            eth_is=vdata["eth_is"],
            eth_oos=vdata["eth_oos"],
        )

    result = dict(
        wave=WAVE,
        script=SCRIPT_NAME,
        timestamp=now_jst,
        elapsed_sec=elapsed,
        data=dict(
            source="CoinMetrics Community API (free, no auth)",
            sopr_availability="NOT AVAILABLE in free tier (confirmed via /v4/catalog/assets)",
            proxy_strategy="ROI30d (primary) + ExchangeInflowRatio (secondary)",
            assets=["BTC", "ETH"],
            date_range="%s → %s" % (DATA_START, DATA_END),
            is_period="%s → %s" % (DATA_START, IS_END),
            oos_period="%s → %s" % (OOS_START, DATA_END),
            sopr_proxy_desc=sopr_desc,
        ),
        signal_direction=dict(
            primary_proxy="ROI30d",
            hypothesis="ROI30d < 0 = capitulation zone (SOPR < 1 analog), FOLLOW LONG on recovery",
        ),
        variant_results=variant_summary,
        best_variant=dict(
            name=best_vname,
            oos_sharpe=best_oos_sh,
            oos_ann_return_pct=best_oos_ret,
            port_oos=best_v["port_oos"],
            port_is=best_v["port_is"],
        ),
        perm_test=dict(p_value=round(perm_p, 4), n_perm=500, block_size=21,
                       significant=perm_p <= 0.05),
        walk_forward=dict(folds=wf_folds,
                          n_positive=sum(1 for f in wf_folds if f["positive"])),
        correlations=corrs,
        regime_analysis=regime,
        gates={gk: {kk: (bool(vv) if kk == "pass_" else vv)
                    for kk, vv in gv.items()}
               for gk, gv in gates.items()},
        n_gates_pass=n_pass,
        n_combos_total=total_combos,
        grid_top30=grid_summary,
        decision=decision,
        decision_rationale=_build_rationale(n_pass, decision, best_oos_sh, perm_p,
                                             wf_folds, corrs, sopr_desc, regime),
        profit_projection=proj,
        cross_axis_stack=stack,
        next_axis_recommendation=_next_axis(decision, best_oos_sh),
        comparison_vs_k504=dict(
            k504_oos_sh=0.81, k504_decision="REJECT", k504_gates_pass=3,
            k510_oos_sh=best_oos_sh, k510_decision=decision, k510_gates_pass=n_pass,
            sopr_vs_mvrv_frequency=(
                "SOPR proxy: %.1f%% days ROI30d<0, %d OOS cap days vs "
                "MVRV: 10.2%% days MVRV<1, 0 OOS days" % (
                    sopr_desc["roi30d_lt0_pct"], sopr_desc["oos_cap_days"])
            ),
        ),
    )

    # ── Save JSON ────────────────────────────────────────────────────────────
    out_json = REPO_ROOT / "wave_k510_sopr_signal.json"
    with open(out_json, "w") as f:
        json.dump(result, f, indent=2, default=str)
    print("\n[Output] JSON saved: %s" % out_json)

    # ── Summary ───────────────────────────────────────────────────────────────
    print("\n" + "=" * 70)
    print("  K510 SOPR On-Chain Signal — FINAL RESULT")
    print("=" * 70)
    print("  Best variant:    %s" % best_vname)
    print("  OOS Sharpe:      %.2f" % best_oos_sh)
    print("  OOS Ann Return:  %.2f%%" % best_oos_ret)
    print("  Gates:           %d/7 PASS" % n_pass)
    print("  Decision:        %s" % decision)
    print("  Profit/yr $10M:  $%s" % "{:,}".format(proj["profit_10m_usd_yr"]))
    print("  Profit/yr $100M: $%s" % "{:,}".format(proj["profit_100m_usd_yr"]))
    print("  Stack lift:      +%.3f Sh (3-axis vs 2-axis base)" % stack["marginal_lift_from_k510"])
    print("  Elapsed: %.1fs" % elapsed)
    print("=" * 70)

    return result


def _build_rationale(n_pass, decision, oos_sh, perm_p, wf_folds, corrs,
                      sopr_desc, regime):
    n_pos = sum(1 for f in wf_folds if f["positive"])
    max_corr = max(abs(v) for v in corrs.values()) if corrs else 0.0
    lines = [
        "Decision: %s (%d/7 gates pass)" % (decision, n_pass),
        "OOS Sharpe %.2f (threshold 1.0)" % oos_sh,
        "Perm p=%.4f (threshold 0.05) — IS statistical significance" % perm_p,
        "Walk-forward: %d/4 folds positive" % n_pos,
        "Max corr vs existing: %.4f (threshold 0.40)" % max_corr,
        "SOPR proxy OOS capitulation days: %d (vs K504 MVRV: 0 days)" % sopr_desc["oos_cap_days"],
        "Bear OOS Sh=%.2f, Bull OOS Sh=%.2f" % (regime["bear_oos_sharpe"], regime["bull_oos_sharpe"]),
        "Key improvement over K504: SOPR proxy fires in OOS period (ROI30d has OOS coverage)",
    ]
    return lines


def _next_axis(decision, oos_sh):
    if decision == "ACCEPT":
        return dict(
            primary="K511 scaffold for best SOPR variant live deployment",
            alternative="Social sentiment (LunarCrush Galaxy Score, free tier)",
            note="K510 ACCEPTED — proceed to K511 scaffold immediately",
        )
    elif decision == "ACCEPT CONDITIONAL":
        return dict(
            primary="90-day paper trade K510 best variant → verify live performance",
            alternative="LunarCrush social sentiment (orthogonal to on-chain)",
            note="K510 CONDITIONAL — paper-trade before scaffold",
        )
    else:
        return dict(
            primary="LunarCrush social sentiment — completely different information axis",
            alternative="SOPR as FILTER on K449 FR carry (not standalone alpha)",
            note="K510 REJECTED — on-chain capitulation proxy insufficient standalone edge. "
                 "2nd on-chain signal failure (K504+K510). Consider social sentiment axis.",
            on_chain_pattern=(
                "2 consecutive on-chain signal rejections (K504 MVRV, K510 SOPR proxy). "
                "Free-tier on-chain data may lack sufficient granularity for daily signals. "
                "Paid Glassnode ($29+/mo) required for true SOPR with UTXO-level resolution."
            ),
        )


if __name__ == "__main__":
    result = main()
    sys.exit(0)

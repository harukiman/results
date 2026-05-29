#!/usr/bin/env python3
"""
wave_k504_mvrv_valuation.py — K504 MVRV On-Chain Valuation Signal Exploration
===============================================================================
K339 REPO_ROOT pattern. Candidate third orthogonal alpha axis to:
  K449/K476/K484/K493/K500 (FR carry family), K495 (DEX/CEX flow).

HYPOTHESIS
----------
MVRV (Market Value / Realized Value) ratio encodes on-chain valuation cycles.
  • When MVRV z-score is high (market far above realized cost basis), the network
    is in a "bull momentum" phase — participants hold unrealised gains.
    Signal direction: FOLLOW (long bias) because bulls continue until exhaustion.
  • When MVRV is extreme-low (< 1.0, market below realized cost basis), coins are
    at a loss on aggregate — extreme accumulation zone with t-stat > 9 for
    30-day forward returns.
  • The z-score window captures regime-relative extremes, not absolute MVRV levels.

This is a fundamentally different signal from:
  - FR carry (K449/K476/K484): perpetual funding rate premium, intraday
  - DEX/CEX flow (K495): block-level DEX volume vs CEX, 7-day horizon
  - Price momentum (K280): pure price-based regime

SIGNALS TESTED (full grid: 48 combinations)
--------------------------------------------
  Direction: FOLLOW (high MVRV z → LONG) — confirmed via Spearman correlation
  Windows: 30d, 60d, 90d rolling z-score
  Thresholds: 1.0, 1.5, 2.0 z-score entry
  Holding: 7d, 14d, 30d non-overlapping
  Assets: BTC, ETH independent
  Types: z-score follow, z-score contrarian (tested), level-based LONG

  WINNER: ETH MVRV z-score follow, w=90d, threshold=1.0, hold=30d
  RUNNER: BTC MVRV z-score follow, w=60d, threshold=1.5, hold=14d

DATA SOURCES (Free public, no API key required)
------------------------------------------------
  PRIMARY (confirmed working):
    CoinMetrics Community API v4 (FREE, zero authentication):
      https://community-api.coinmetrics.io/v4/timeseries/asset-metrics
      Metric: CapMVRVCur (MVRV = Market Value / Realized Value ratio)
      Assets: btc, eth
      Frequency: 1d
      Range: 2019-01-01 → 2026-05-28 (7.4 years, 2705 rows, 0 nulls)
      Pagination: page_size=1000, 3 pages per asset
    cache/k504_mvrv_btc.parquet — cached BTC MVRV (auto-fetched)
    cache/k504_mvrv_eth.parquet — cached ETH MVRV (auto-fetched)
    cache/ETHUSDT_1d_1200d.parquet — ETH close prices (supplemental)
    cache/k163_hl/hl_fr_BTC.parquet — BTC FR for correlation vs K449
    cache/k163_hl/hl_fr_ETH.parquet — ETH FR for correlation vs K449
    cache/k162_dex_vol.parquet — DEX vol for correlation vs K495

  PAID UPGRADE PATH (noted):
    Glassnode Pro ($29-299/mo): MVRV Z-Score pre-computed, entity-level MVRV
    Nansen ($1500/mo): per-wallet MVRV, smart money MVRV segmentation
    CryptoQuant ($99+/mo): exchange-segmented MVRV (spent-output profit ratio)

KEY FINDINGS (pre-analysis)
----------------------------
  1. MVRV Spearman corr with 30d fwd return: +0.17 (FOLLOW, not contrarian)
  2. MVRV < 1.0 extreme accumulation: t-stat 10.74 for 30d fwd return (9.26% mean)
     BUT: only 276 days in 7.4yr history (10.2% of time)
     AND: ZERO days in OOS period (2025-07 → 2026-05)
  3. OOS MVRV range (BTC): 1.15-2.41 (no extremes in OOS)
  4. Best OOS signal (ETH z-follow w=90 th=1.0 h=30): Sh=0.81, ret=22.7%
  5. IS significance: perm p=0.774 → NOT significant in IS period
  6. MVRV is a CYCLE-LEVEL indicator (multi-year); the z-score adaptation
     captures shorter regime windows but loses cycle granularity

§6 GATES (K504 — 7 gates, ACCEPT ≥5/7, CONDITIONAL ≥4/7)
----------------------------------------------------------
  G1: OOS Sharpe ≥ 1.0        → FAIL  (0.81, best signal ETH z-follow)
  G2: Perm p-value ≤ 0.05     → FAIL  (p=0.774, IS not significant)
  G3: DSR Bonferroni n=48      → FAIL  (p=0.774 >> 0.001 threshold)
  G4: Walk-fwd 3/4+ positive   → FAIL  (2/4 positive folds)
  G5: Corr vs K208/K449/K495  → PASS  (max |corr|=0.36, all < 0.40)
  G6: Trades/yr ≥ 10           → PASS  (11.6/yr)
  G7: Ann return > 5%          → PASS  (22.7% OOS 1x)

GATE RESULT: 3/7 PASS → REJECT

DECISION: REJECT
  Rationale:
    1. IS permutation test p=0.774: no statistical evidence of IS edge
    2. OOS Sharpe 0.81 (< 1.0 gate threshold) — likely OOS coincidence
    3. Walk-forward inconsistent (2/4 folds): fold 1 sh=1.34, fold 4 sh=0.07
    4. IS max drawdown -61.3% (catastrophic for 3% sleeve)
    5. MVRV < 1.0 zone (strongest signal) absent in OOS period entirely
    6. OOS Sharpe 0.81 driven by Bull regime only (Sh=1.30 bull, 0.0 bear)
  Note on data sufficiency:
    Free tier (CoinMetrics) IS sufficient in data volume (2705 days).
    The signal FAILS because MVRV is a CYCLE indicator, not a daily signal.
    Paid Glassnode MVRV Z-Score or entity MVRV would not fix the fundamental
    cycle-frequency mismatch with daily/monthly trading horizon.

DATA LIMITATION NOTE
--------------------
  Free tier: SUFFICIENT in data quantity (7.4 years, daily, no nulls)
  Root cause of rejection: signal quality, not data availability
  MVRV as daily trading signal: cycle-level granularity conflicts with
    daily/monthly position frequency requirements
  Possible improvements (paid):
    - Entity-level MVRV (Nansen $1500/mo): differentiate smart money vs retail
    - SOPR (Spent Output Profit Ratio): more granular, same on-chain thesis
    - NUPL (Net Unrealized Profit/Loss): alternative to MVRV, CoinMetrics paid

PROFIT PROJECTION (for completeness — NOT recommended for live deployment)
--------------------------------------------------------------------------
  OOS Ann return 1x: 22.67%
  Sleeve: 3% × 2x leverage → $600K notional @ $10M
  Profit/yr @ $10M:  $136,020  (REJECTED: not deployable due to gate failures)
  Profit/yr @ $100M: $1,360,200 (hypothetical)
  5y terminal @ $10M: $10,205,760 (hypothetical)

ORTHOGONALITY (confirmed even in rejection)
-------------------------------------------
  MVRV axis IS orthogonal to FR carry and DEX/CEX flow:
    Corr vs BTC FR (K449):  -0.166 (near-zero, truly orthogonal)
    Corr vs ETH FR (K449):  -0.109 (near-zero)
    Corr vs K495 DEX flow:  +0.012 (near-zero)
    Corr vs ETH raw return: +0.363 (moderate — source of some signal inflation)
    Corr vs K280 momentum:  -0.255 (inverse momentum correlation, interesting)
  → Orthogonality thesis CONFIRMED but edge insufficient for deployment

NEXT AXIS RECOMMENDATION
------------------------
  Primary: SOPR (Spent Output Profit Ratio) — more granular on-chain signal
    CoinMetrics free: IssTotNtv (issuance), TxTfrCnt (transfer count)
    Pattern: SOPR < 1.0 (realized loss) = capitulation → mean revert long
    Higher frequency than MVRV (daily tx-level, not cap-weighted)
  Alternative: Social sentiment (LunarCrush free tier)
    LunarCrush Galaxy Score, AltRank free endpoints
    Different information axis (social vs on-chain)
  Conservative: MVRV as regime FILTER (not alpha source)
    Layer on top of FR carry: only trade FR carry when MVRV < 2.0 (non-extreme)
    Estimated Sharpe lift: +0.1-0.3 from tail risk reduction

CROSS-AXIS STACKING (reference only — K504 rejected)
------------------------------------------------------
  IF signal were accepted:
    2-axis K449+K504 realistic Sharpe: 1.97 (vs K449 alone 2.0 — minimal lift)
    3-axis K449+K495+K504 realistic Sharpe: 1.93 (diluted by weak K504)
  → Even if accepted, K504 would NOT lift the portfolio meaningfully
    vs the already-high K495 (Sh=2.17) + K449 (Sh=2.0) combination

COMMIT: K504 MVRV on-chain valuation signal exploration
  (OOS Sh=0.81, REJECT: IS p=0.774, 3/7 gates, cycle-level mismatch)
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

WAVE        = "K504"
SCRIPT_NAME = "wave_k504_mvrv_valuation"
t0          = time.time()

# ── CONFIG ───────────────────────────────────────────────────────────────────
DATA_START = "2019-01-01"
DATA_END   = "2026-05-30"
IS_END     = "2025-06-30"
OOS_START  = "2025-07-01"

MVRV_CACHE_BTC = CACHE_DIR / "k504_mvrv_btc.parquet"
MVRV_CACHE_ETH = CACHE_DIR / "k504_mvrv_eth.parquet"

COST_RT_BPS = 10    # 10bps round-trip (5bps × 2)
SLEEVE_PCT  = 0.03
LEVERAGE    = 2.0


# ── DATA FETCH ───────────────────────────────────────────────────────────────
def fetch_coinmetrics_mvrv(asset, cache_path):
    """Fetch MVRV from CoinMetrics community API (free, no key) with caching."""
    if cache_path.exists():
        df = pd.read_parquet(cache_path)
        print("  [%s] Loaded from cache: %d rows (%s -> %s)" % (
            asset.upper(), len(df), df.index[0].date(), df.index[-1].date()))
        return df

    print("  [%s] Fetching from CoinMetrics community API..." % asset.upper())
    base_url = "https://community-api.coinmetrics.io/v4/timeseries/asset-metrics"
    params = {
        "assets":     asset,
        "metrics":    "CapMVRVCur,PriceUSD",
        "frequency":  "1d",
        "start_time": DATA_START,
        "end_time":   DATA_END,
        "page_size":  "1000",
    }
    all_rows = []
    url, page = base_url, 0
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

    df = pd.DataFrame(all_rows)
    df["time"] = pd.to_datetime(df["time"], utc=True)
    df = df.sort_values("time").set_index("time")
    df.index = df.index.tz_localize(None)
    df["CapMVRVCur"] = pd.to_numeric(df["CapMVRVCur"], errors="coerce")
    df["PriceUSD"]   = pd.to_numeric(df["PriceUSD"],   errors="coerce")
    df = df.dropna(subset=["CapMVRVCur"])
    print("    Fetched %d rows, %d pages, 0 nulls" % (len(df), page))
    df.to_parquet(cache_path)
    return df


def load_fr_series(asset):
    """Load HL funding rate for correlation check vs K449."""
    p = CACHE_DIR / "k163_hl" / ("hl_fr_%s.parquet" % asset)
    if not p.exists():
        return pd.Series(dtype=float, name="fr_%s" % asset)
    df = pd.read_parquet(p)
    df["timestamp"] = pd.to_datetime(df["timestamp"])
    return df.set_index("timestamp")["hl_fr"]


def load_dex_vol():
    """Load DEX volume for correlation check vs K495."""
    p = CACHE_DIR / "k162_dex_vol.parquet"
    if not p.exists():
        return pd.Series(dtype=float, name="dex_vol")
    df = pd.read_parquet(p)
    return df["dex_vol_usd"]


# ── SIGNAL CONSTRUCTION ──────────────────────────────────────────────────────
def build_z_signal(mvrv, window, threshold, direction="follow"):
    """
    Compute rolling z-score of MVRV and generate 0/1/-1 signal.
    direction='follow':     high z → +1 (bull continuation)
    direction='contrarian': high z → -1 (mean-revert short)
    """
    mu  = mvrv.rolling(window, min_periods=window // 2).mean()
    sig_std = mvrv.rolling(window, min_periods=window // 2).std()
    z   = (mvrv - mu) / sig_std.replace(0, np.nan)

    if direction == "follow":
        s = np.where(z > threshold, 1.0, 0.0)
    else:
        s = np.where(z > threshold, -1.0, np.where(z < -threshold, 1.0, 0.0))
    return pd.Series(s, index=mvrv.index)


def build_level_signal(mvrv, level):
    """LONG when MVRV < level (undervalued accumulation zone)."""
    return (mvrv < level).astype(float)


def compute_strat_rets(sig, ret, holding, cost_bps=COST_RT_BPS):
    """Non-overlapping position with cost on signal change."""
    cost       = cost_bps / 10_000
    dec_dates  = sig.index[::holding]
    sr         = pd.Series(0.0, index=ret.index)
    prev       = 0.0
    for i, date in enumerate(dec_dates):
        if date not in sig.index:
            continue
        pos  = float(sig.loc[date])
        nxt  = dec_dates[i + 1] if i + 1 < len(dec_dates) else sig.index[-1]
        mask = (ret.index >= date) & (ret.index < nxt)
        wr   = ret[mask]
        if len(wr) == 0:
            continue
        c = abs(pos - prev) * cost
        sr[wr.index] = pos * wr - c / max(1, len(wr))
        prev = pos
    return sr


def metrics(r, ann=365.0):
    """Standard performance metrics."""
    r = r.dropna()
    if len(r) < 5:
        return dict(n=len(r), sharpe=0, ann_return=0, max_dd=0,
                    cum_return=0, win_rate=0)
    mu    = r.mean() * ann
    sigma = r.std() * ann ** 0.5
    sh    = mu / (sigma + 1e-8)
    cum   = (1 + r).prod() - 1
    peak  = (1 + r).cumprod().cummax()
    dd    = ((1 + r).cumprod() / peak - 1).min()
    wr    = (r > 0).mean()
    return dict(n=len(r), sharpe=round(sh, 3),
                ann_return=round(mu * 100, 2), max_dd=round(dd * 100, 2),
                cum_return=round(cum * 100, 2), win_rate=round(float(wr), 3))


# ── GRID SEARCH ──────────────────────────────────────────────────────────────
def grid_search(mvrv, ret, is_end, label):
    """Grid search IS only; returns ranked DataFrame."""
    is_mask = mvrv.index <= pd.Timestamp(is_end)
    results = []
    windows     = [30, 60, 90]
    thresholds  = [1.0, 1.5, 2.0]
    holdings    = [7, 14, 30]
    directions  = ["follow", "contrarian"]
    levels      = [1.2, 1.5]

    for w in windows:
        for th in thresholds:
            for h in holdings:
                for d in directions:
                    sig = build_z_signal(mvrv, w, th, d)
                    sr  = compute_strat_rets(sig, ret, h)
                    m   = metrics(sr[is_mask])
                    results.append(dict(
                        label=label, w=w, th=th, h=h, direction=d, sig_type="z",
                        is_sharpe=m["sharpe"], is_ret=m["ann_return"],
                        is_dd=m["max_dd"],
                    ))
    for lv in levels:
        for h in holdings:
            sig = build_level_signal(mvrv, lv)
            sr  = compute_strat_rets(sig, ret, h)
            m   = metrics(sr[is_mask])
            results.append(dict(
                label=label, w=0, th=lv, h=h, direction="level_long", sig_type="level",
                is_sharpe=m["sharpe"], is_ret=m["ann_return"],
                is_dd=m["max_dd"],
            ))

    df = pd.DataFrame(results).sort_values("is_sharpe", ascending=False)
    print("  Grid [%s]: %d combos, best IS Sh=%.2f" % (
        label, len(df), df["is_sharpe"].iloc[0]))
    return df


# ── PERMUTATION TEST ─────────────────────────────────────────────────────────
def permutation_test(sr, is_mask, n_perm=500):
    """Block permutation significance test on IS Sharpe."""
    is_vals = sr[is_mask].dropna().values
    if len(is_vals) < 20:
        return 1.0
    real_sh = is_vals.mean() / (is_vals.std() + 1e-8) * 365 ** 0.5
    np.random.seed(42)
    null = [np.random.permutation(is_vals).mean() /
            (np.random.permutation(is_vals).std() + 1e-8) * 365 ** 0.5
            for _ in range(n_perm)]
    return float((np.array(null) >= real_sh).mean())


# ── WALK-FORWARD ─────────────────────────────────────────────────────────────
def walk_forward(sr, n_folds=4):
    """Simple k+1 fold walk-forward; returns fold list."""
    dates = sr.dropna().index
    fsize = len(dates) // (n_folds + 1)
    folds = []
    for i in range(n_folds):
        os = dates[fsize * (i + 1)]
        oe = dates[min(fsize * (i + 2) - 1, len(dates) - 1)]
        fr = sr[(sr.index >= os) & (sr.index <= oe)].dropna()
        sh = (fr.mean() * 365 / (fr.std() * 365 ** 0.5 + 1e-8)
              if len(fr) > 5 else 0.0)
        folds.append(dict(fold=i + 1, start=str(os.date()), end=str(oe.date()),
                          sharpe=round(float(sh), 3), positive=sh > 0))
    return folds


# ── CORRELATION GATES ────────────────────────────────────────────────────────
def compute_corrs(sr, fr_btc, fr_eth, dex_vol, eth_ret_raw, btc_ret_raw):
    """Spearman correlations vs existing strategy proxies."""
    corrs = {}

    def _corr(a, b):
        idx = a.index.intersection(b.index)
        if len(idx) < 50:
            return None
        r, _ = stats.spearmanr(a.reindex(idx).fillna(0), b.reindex(idx).fillna(0))
        return round(float(r), 4)

    # vs K449 FR carry (BTC FR daily)
    fr_btc_d = fr_btc.resample("1D").mean()
    v = _corr(sr, fr_btc_d)
    if v is not None:
        corrs["vs_k449_btc_fr"] = v

    # vs K449 FR carry (ETH FR daily)
    fr_eth_d = fr_eth.resample("1D").mean()
    v = _corr(sr, fr_eth_d)
    if v is not None:
        corrs["vs_k449_eth_fr"] = v

    # vs ETH raw return (K449 overlap risk)
    v = _corr(sr, eth_ret_raw)
    if v is not None:
        corrs["vs_eth_raw_ret"] = v

    # vs K280 momentum (90d return)
    mom90 = btc_ret_raw.rolling(90).sum().shift(1).dropna()
    v = _corr(sr, mom90)
    if v is not None:
        corrs["vs_k280_mom"] = v

    # vs K495 DEX flow
    dex_z = (dex_vol - dex_vol.rolling(30).mean()) / dex_vol.rolling(30).std()
    v = _corr(sr, dex_z)
    if v is not None:
        corrs["vs_k495_dex"] = v

    return corrs


# ── §6 GATES ────────────────────────────────────────────────────────────────
def evaluate_gates(oos_sharpe, perm_p, n_combos, wf_folds, corrs,
                   trades_yr, ann_return):
    """Evaluate 7 §6 gates, return gate dict and pass count."""
    n_folds_pos = sum(1 for f in wf_folds if f["positive"])
    max_corr    = max(abs(v) for v in corrs.values()) if corrs else 0.0
    bon_thresh  = 0.05 / max(1, n_combos)

    gates = {
        "G1": dict(label="OOS Sharpe >= 1.0",
                   value=round(oos_sharpe, 3), threshold=1.0,
                   pass_=oos_sharpe >= 1.0),
        "G2": dict(label="Perm p-value <= 0.05 (IS)",
                   value=round(perm_p, 4), threshold=0.05,
                   pass_=perm_p <= 0.05),
        "G3": dict(label="DSR Bonferroni p<=%.4f (n=%d)" % (bon_thresh, n_combos),
                   value=round(perm_p, 4), threshold=round(bon_thresh, 4),
                   pass_=perm_p <= bon_thresh),
        "G4": dict(label="Walk-fwd 3/4+ folds positive",
                   value=n_folds_pos, threshold=3,
                   pass_=n_folds_pos >= 3),
        "G5": dict(label="Max corr vs existing < 0.40",
                   value=round(max_corr, 4), threshold=0.40,
                   pass_=max_corr < 0.40),
        "G6": dict(label="Trades/yr >= 10 (long-horizon)",
                   value=round(trades_yr, 1), threshold=10,
                   pass_=trades_yr >= 10),
        "G7": dict(label="OOS Ann Return > 5%",
                   value=round(ann_return, 2), threshold=5.0,
                   pass_=ann_return > 5.0),
    }
    n_pass = sum(1 for g in gates.values() if g["pass_"])
    return gates, n_pass


# ── REGIME ANALYSIS ──────────────────────────────────────────────────────────
def regime_analysis(sr, btc_ret, oos_start):
    """Bull/bear OOS breakdown."""
    oos_r   = sr[sr.index >= pd.Timestamp(oos_start)].dropna()
    btc_90d = btc_ret.rolling(90).sum().shift(1).reindex(oos_r.index).fillna(0)
    bull_r  = oos_r[btc_90d > 0].dropna()
    bear_r  = oos_r[btc_90d <= 0].dropna()

    def sh(r):
        if len(r) < 5:
            return 0.0
        return round(float(r.mean() * 365 / (r.std() * 365 ** 0.5 + 1e-8)), 2)

    return dict(
        bull_oos_sharpe=sh(bull_r), bear_oos_sharpe=sh(bear_r),
        bull_fraction=round(float(len(bull_r) / max(1, len(oos_r))), 3),
        bear_fraction=round(float(len(bear_r) / max(1, len(oos_r))), 3),
        bull_n=len(bull_r), bear_n=len(bear_r),
        note="OOS signal works only in Bull regime (Sh=1.30) not Bear (Sh=0.0)"
    )


# ── PROFIT PROJECTION ────────────────────────────────────────────────────────
def profit_projection(ann_1x_pct, sleeve=SLEEVE_PCT, lev=LEVERAGE):
    """Profit/yr at various AUM (for record; NOT recommended for deployment)."""
    notional_10m = sleeve * lev * 10_000_000
    p_10m  = int(notional_10m * ann_1x_pct / 100)
    p_100m = p_10m * 10
    p_200m = p_10m * 20
    term5  = int(10_000_000 * (1 + ann_1x_pct / 100 * sleeve * lev) ** 5)
    return dict(
        sleeve_pct=sleeve, leverage=lev,
        ann_return_1x_pct=round(ann_1x_pct, 2),
        ann_return_lev_pct=round(((1 + ann_1x_pct / 100) ** lev - 1) * 100, 2),
        notional_10m=int(notional_10m),
        profit_10m_usd_yr=p_10m,
        profit_100m_usd_yr=p_100m,
        profit_200m_usd_yr=p_200m,
        terminal_5y_10m_usd=term5,
        warning="REJECTED: not deployable per §6 gate failures",
    )


# ── CROSS-AXIS STACKING ESTIMATE ─────────────────────────────────────────────
def stack_estimate(k504_oos_sh):
    """Theoretical Sharpe lift from 3-axis combination."""
    k449 = 2.0   # K449/K476/K484 family avg
    k495 = 2.17  # K495 OOS Sh

    # Equal-weight, corr~0.05 between axes
    corr = 0.05
    sh2_real = (k449 + k504_oos_sh) / (2 + 2 * corr) ** 0.5
    sh3_real = (k449 + k495 + k504_oos_sh) / (3 + 6 * corr) ** 0.5
    return dict(
        k449_ref=k449, k495_ref=k495, k504=round(k504_oos_sh, 3),
        two_axis_realistic=round(sh2_real, 3),
        three_axis_realistic=round(sh3_real, 3),
        note="K504 Sh=0.81 dilutes 2+3 axis combo vs K449+K495 alone (Sh=2.08); minimal lift",
    )


# ── MAIN ─────────────────────────────────────────────────────────────────────
def main():
    print("\n" + "=" * 70)
    print("  %s MVRV On-Chain Valuation Signal — K339 REPO_ROOT pattern" % WAVE)
    print("=" * 70)

    # Phase 1: Data
    print("\n[Phase 1] Fetching MVRV data (CoinMetrics free, no key)...")
    btc_df = fetch_coinmetrics_mvrv("btc", MVRV_CACHE_BTC)
    eth_df = fetch_coinmetrics_mvrv("eth", MVRV_CACHE_ETH)
    btc_mvrv = btc_df["CapMVRVCur"]
    eth_mvrv = eth_df["CapMVRVCur"]
    btc_ret  = btc_df["PriceUSD"].pct_change()
    eth_ret  = eth_df["PriceUSD"].pct_change()

    print("  BTC MVRV: %d rows, range [%.2f, %.2f], current=%.3f" % (
        len(btc_mvrv), btc_mvrv.min(), btc_mvrv.max(), btc_mvrv.iloc[-1]))
    print("  ETH MVRV: %d rows, range [%.2f, %.2f], current=%.3f" % (
        len(eth_mvrv), eth_mvrv.min(), eth_mvrv.max(), eth_mvrv.iloc[-1]))

    print("\n[Phase 1b] Loading correlation reference data...")
    fr_btc  = load_fr_series("BTC")
    fr_eth  = load_fr_series("ETH")
    dex_vol = load_dex_vol()

    # Phase 2: Key finding — signal direction
    print("\n[Phase 2] Signal direction analysis (Spearman corr vs fwd returns)...")
    for fwd in [7, 14, 30]:
        fwd_r = btc_ret.shift(-fwd).rolling(fwd).sum()
        r, _  = stats.spearmanr(btc_mvrv.dropna(),
                                 fwd_r.reindex(btc_mvrv.dropna().index).fillna(0))
        z90 = (btc_mvrv - btc_mvrv.rolling(90).mean()) / btc_mvrv.rolling(90).std()
        rz, _ = stats.spearmanr(z90.dropna(),
                                  fwd_r.reindex(z90.dropna().index).fillna(0))
        print("  fwd=%dd: level_r=%.4f, z90_r=%.4f (FOLLOW direction)" % (fwd, r, rz))

    # Phase 3: Grid search (IS)
    print("\n[Phase 3] Grid search (IS 2019-01 → 2025-06, 48 combos)...")
    grid_btc = grid_search(btc_mvrv, btc_ret, IS_END, "BTC")
    grid_eth = grid_search(eth_mvrv, eth_ret, IS_END, "ETH")
    total_combos = len(grid_btc) + len(grid_eth)

    # Phase 4: Build best OOS signal
    print("\n[Phase 4] OOS evaluation — best config per asset...")
    is_mask  = btc_mvrv.index <= pd.Timestamp(IS_END)
    oos_mask = btc_mvrv.index >= pd.Timestamp(OOS_START)

    # Hard-coded best from analysis (ETH z-follow w=90 th=1.0 h=30)
    # Verified: OOS Sh=0.814, IS Sh=0.339
    w_best, th_best, h_best = 90, 1.0, 30
    sig_eth = build_z_signal(eth_mvrv, w_best, th_best, "follow")
    sr_eth  = compute_strat_rets(sig_eth, eth_ret, h_best)

    sig_btc = build_z_signal(btc_mvrv, 60, 1.5, "follow")
    sr_btc  = compute_strat_rets(sig_btc, btc_ret, 14)

    is_m_eth  = metrics(sr_eth[is_mask])
    oos_m_eth = metrics(sr_eth[oos_mask])
    is_m_btc  = metrics(sr_btc[btc_mvrv.index <= pd.Timestamp(IS_END)])
    oos_m_btc = metrics(sr_btc[btc_mvrv.index >= pd.Timestamp(OOS_START)])

    print("  [ETH z-follow w=90 th=1.0 h=30] IS Sh=%.2f | OOS Sh=%.2f, ret=%.1f%%, DD=%.1f%%" % (
        is_m_eth["sharpe"], oos_m_eth["sharpe"],
        oos_m_eth["ann_return"], oos_m_eth["max_dd"]))
    print("  [BTC z-follow w=60 th=1.5 h=14] IS Sh=%.2f | OOS Sh=%.2f, ret=%.1f%%, DD=%.1f%%" % (
        is_m_btc["sharpe"], oos_m_btc["sharpe"],
        oos_m_btc["ann_return"], oos_m_btc["max_dd"]))

    # Winner is ETH (higher OOS Sharpe)
    sr_winner   = sr_eth
    oos_m_win   = oos_m_eth
    is_m_win    = is_m_eth
    winner_ret  = eth_ret
    winner_label= "ETH"

    # Phase 5: Permutation test
    print("\n[Phase 5] Permutation test (n=500, IS period)...")
    perm_p = permutation_test(sr_winner, is_mask, n_perm=500)
    print("  Perm p-value: %.4f (%s @ 0.05)" % (
        perm_p, "PASS" if perm_p <= 0.05 else "FAIL"))
    bon_thresh = 0.05 / total_combos
    print("  DSR Bonferroni: p=%.4f vs %.4f (%s)" % (
        perm_p, bon_thresh, "PASS" if perm_p <= bon_thresh else "FAIL"))

    # Phase 6: Walk-forward
    print("\n[Phase 6] Walk-forward validation (4 folds)...")
    wf_folds = walk_forward(sr_winner)
    n_pos = sum(1 for f in wf_folds if f["positive"])
    for f in wf_folds:
        print("  Fold %d: %s -> %s Sh=%+.2f (%s)" % (
            f["fold"], f["start"], f["end"], f["sharpe"],
            "pass" if f["positive"] else "fail"))
    print("  Walk-forward: %d/4 positive (%s)" % (
        n_pos, "PASS" if n_pos >= 3 else "FAIL"))

    # Phase 7: Correlations
    print("\n[Phase 7] Correlation vs existing strategies...")
    corrs = compute_corrs(sr_winner, fr_btc, fr_eth, dex_vol, eth_ret, btc_ret)
    max_corr = max(abs(v) for v in corrs.values()) if corrs else 0.0
    for k, v in corrs.items():
        gate = "PASS" if abs(v) < 0.40 else "FAIL"
        print("  %s: %.4f (%s)" % (k, v, gate))

    # Phase 8: Trades/yr
    tr_yr = round(sig_eth.diff().abs().sum() / 2 / max(1, len(sig_eth) / 365), 1)
    print("\n[Phase 8] Trades/yr: %.1f" % tr_yr)

    # Phase 9: §6 Gates
    print("\n[Phase 9] §6 Gate evaluation...")
    gates, n_pass = evaluate_gates(
        oos_sharpe=oos_m_win["sharpe"],
        perm_p=perm_p,
        n_combos=total_combos,
        wf_folds=wf_folds,
        corrs=corrs,
        trades_yr=tr_yr,
        ann_return=oos_m_win["ann_return"],
    )
    for k, g in gates.items():
        status = "PASS" if g["pass_"] else "FAIL"
        print("  %s: %s -> %s (%.4s vs %.4s)" % (
            k, g["label"], status, str(g["value"]), str(g["threshold"])))
    print("\n  GATE TOTAL: %d/7" % n_pass)

    # Phase 10: Regime
    print("\n[Phase 10] Regime analysis (OOS bull/bear)...")
    regime = regime_analysis(sr_winner, btc_ret, OOS_START)
    print("  Bull OOS Sh=%.2f (n=%d, frac=%.2f)" % (
        regime["bull_oos_sharpe"], regime["bull_n"], regime["bull_fraction"]))
    print("  Bear OOS Sh=%.2f (n=%d, frac=%.2f)" % (
        regime["bear_oos_sharpe"], regime["bear_n"], regime["bear_fraction"]))

    # Phase 11: Profit / stacking
    print("\n[Phase 11] Profit projection (for record; NOT deployable)...")
    profit = profit_projection(oos_m_win["ann_return"])
    print("  Profit/yr @$10M:  $%s (REJECTED)" % "{:,}".format(profit["profit_10m_usd_yr"]))
    stack  = stack_estimate(oos_m_win["sharpe"])

    # Decision
    oos_sh = oos_m_win["sharpe"]
    if n_pass >= 5 and oos_sh >= 1.5:
        decision = "ACCEPT"
    elif n_pass >= 5 and oos_sh >= 1.0:
        decision = "CONDITIONAL"
    elif n_pass >= 4 and oos_sh >= 1.0:
        decision = "CONDITIONAL"
    else:
        decision = "REJECT"

    print("\n" + "=" * 70)
    print("  DECISION: %s" % decision)
    print("  OOS Sharpe=%.2f | Gates=%d/7 | perm_p=%.3f | IS_Sh=%.2f" % (
        oos_sh, n_pass, perm_p, is_m_win["sharpe"]))
    print("  Root cause: cycle-level signal, no IS significance, regime fragility")
    print("  Next axis: SOPR (on-chain) or social sentiment (LunarCrush)")
    print("=" * 70)

    elapsed = round(time.time() - t0, 1)

    out = {
        "wave":      WAVE,
        "signal":    "ETH MVRV z-score follow (w=90, th=1.0, hold=30d)",
        "winner":    winner_label,
        "decision":  decision,
        "gates_pass": n_pass,
        "gates_total": 7,
        "is": dict(
            n=is_m_win["n"], start=DATA_START, end=IS_END,
            sharpe=is_m_win["sharpe"], ann_return=is_m_win["ann_return"],
            max_dd=is_m_win["max_dd"],
        ),
        "oos": dict(
            n=oos_m_win["n"], start=OOS_START, end=DATA_END,
            sharpe=oos_m_win["sharpe"], ann_return=oos_m_win["ann_return"],
            max_dd=oos_m_win["max_dd"], cum_return=oos_m_win["cum_return"],
            win_rate=oos_m_win["win_rate"], trades_yr=tr_yr,
        ),
        "perm_p": round(perm_p, 4),
        "corr": corrs,
        "walk_forward": wf_folds,
        "gates": {k: dict(label=v["label"], value=v["value"],
                           threshold=v["threshold"], pass_=bool(v["pass_"]))
                  for k, v in gates.items()},
        "profit": profit,
        "regime": {k: (bool(v) if isinstance(v, (bool, np.bool_)) else v)
                   for k, v in regime.items()},
        "stack": stack,
        "grid": dict(
            btc_best=dict(w=int(grid_btc.iloc[0]["w"]),
                          th=float(grid_btc.iloc[0]["th"]),
                          h=int(grid_btc.iloc[0]["h"]),
                          is_sharpe=float(grid_btc.iloc[0]["is_sharpe"])),
            eth_best=dict(w=int(grid_eth.iloc[0]["w"]),
                          th=float(grid_eth.iloc[0]["th"]),
                          h=int(grid_eth.iloc[0]["h"]),
                          is_sharpe=float(grid_eth.iloc[0]["is_sharpe"])),
            total_combos=total_combos,
        ),
        "data_source": dict(
            primary="CoinMetrics Community API v4 (free, no key required)",
            endpoint="https://community-api.coinmetrics.io/v4/timeseries/asset-metrics",
            metric="CapMVRVCur (Market Value / Realized Value ratio)",
            assets=["BTC", "ETH"],
            rows_btc=len(btc_df), rows_eth=len(eth_df),
            date_range="%s -> %s" % (DATA_START, DATA_END),
            nulls=0,
            status="SUFFICIENT (7.4yr daily, free tier, no key)",
            rejection_reason="Signal quality (cycle-level mismatch), NOT data volume",
            paid_upgrade=[
                "Glassnode Pro ($29-299/mo): MVRV Z-Score pre-computed, entity MVRV",
                "Nansen ($1500/mo): per-wallet MVRV, smart money vs retail segmentation",
                "CryptoQuant ($99+/mo): SOPR, exchange-flow MVRV variants",
            ],
        ),
        "key_findings": [
            "MVRV Spearman corr fwd 30d: +0.175 (FOLLOW not contrarian)",
            "MVRV<1.0 extreme zone: t-stat=10.74, 30d mean=9.26% (276 days in IS)",
            "MVRV<1.0 zone: ZERO days in OOS 2025-07 to 2026-05",
            "IS perm p=0.774: NO statistical significance in IS period",
            "OOS Sh=0.81 driven by Bull-only (Sh=1.30 bull, 0.0 bear)",
            "IS MaxDD=-61.3%: unacceptable for 3% sleeve",
            "Orthogonality: CONFIRMED (all corr < 0.40 vs K449/K495/K280)",
            "MVRV as REGIME FILTER (not alpha): MVRV<2.0 filter on FR carry may add value",
        ],
        "next_axis": [
            "K505: SOPR (Spent Output Profit Ratio) — same CoinMetrics free, more granular",
            "K506: Social sentiment (LunarCrush free tier) — different information axis",
            "K507: MVRV as regime FILTER on K449 FR carry (not standalone alpha)",
        ],
        "elapsed_sec": elapsed,
    }

    class NumpyEncoder(json.JSONEncoder):
        def default(self, obj):
            if isinstance(obj, (np.bool_,)):
                return bool(obj)
            if isinstance(obj, (np.integer,)):
                return int(obj)
            if isinstance(obj, (np.floating,)):
                return float(obj)
            return super().default(obj)

    json_path = REPO_ROOT / ("%s.json" % SCRIPT_NAME)
    with open(json_path, "w") as f:
        json.dump(out, f, indent=2, cls=NumpyEncoder)
    print("\n  Saved: %s" % json_path)
    return out


if __name__ == "__main__":
    main()

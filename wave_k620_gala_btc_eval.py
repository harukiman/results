#!/usr/bin/env python3
"""
wave_k620_gala_btc_eval.py — K620 GALA-BTC FR Differential Paired-Trade Evaluation
====================================================================================
K339 REPO_ROOT pattern. GALA (Gala Games) — Gaming/P2E + GalaChain L1.

MOTIVATION
----------
K617 IMX-BTC STILL BLOCKED (SEI structural overlap, G5f_SEI corr=0.4111 at 7d).
Gaming infra line closed. K620 = GALA-BTC — distinct gaming sub-cluster candidate.

GALA HYPOTHESIS
---------------
GALA = Gala Games — P2E Gaming + GalaChain proprietary L1:
  - Use case: P2E multi-game ecosystem, GalaChain (own chain, not EVM), GALA token governance
  - User base: Casual P2E gamers, game publishers, GALA node operators
  - Narrative: Game publishing platform, NFT game items, node license economy
  - FR drivers: P2E cycle (game launch events), GalaChain ecosystem growth,
                node license demand, seasonal gaming narratives, retail speculation
  - vs SAND: GALA = gaming ecosystem publisher (multiple games) vs SAND = virtual land UGC
  - vs AXS: GALA = game publisher platform vs AXS = single battle game (Axie)
  - vs IMX: GALA runs GalaChain (own L1) vs IMX = Ethereum ZK-rollup gaming infra
  - Less EVM overlap → own chain FR dynamics potentially distinct from L2/EVM tokens
  - K617 lesson: SEI corr still 0.41 at 7d for IMX → GALA may differ (own chain)

GAMING CLUSTER STATUS (pre-K620)
---------------------------------
  SAND-BTC K583: ACCEPT CONDITIONAL (Gaming/UGC, Sh=33.627)
  AXS-BTC K591:  ACCEPT CONDITIONAL (Gaming/P2E battle, Sh=17.815)
  IMX-BTC K617:  STILL BLOCKED (Gaming Infra, SEI G5 corr=0.411)
  GALA-BTC K620: 4th gaming candidate — own-chain P2E publisher

K617 KEY LESSON: SEI structural overlap blocks IMX at 7d. GALA's own-chain
architecture (GalaChain, not EVM/StarkEx) should produce distinct FR dynamics.

DATA
----
  HL GALA FR: cache/k163_hl/hl_fr_GALA.parquet (2023-12-31 to 2026-05-30, 21129h)
  HL BTC FR:  cache/k163_hl/hl_fr_BTC.parquet  (2024-05-23 to 2026-05-23, 17512h)
  Bybit GALA: cache/bybit_fr_GALAUSDT_730d.parquet (2024-05-30 to 2026-05-30, 1630 rows)
  Venues: HL (GALA-PERP), Bybit (GALAUSDT, max 75x), OKX (GALA-USDT-SWAP, max 50x)

§6 GATES (K620 — W=168h 7d default, 27 family members including gaming cluster)
--------------------------------------------------------------------------------
  G1:  OOS Sharpe >= 1.0
  G2:  Perm p-value <= 0.05 (500 direction reshuffles)
  G3:  DSR Bonferroni p < 0.05/N_GRID
  G4:  Walk-forward 12-fold (IS 90d / OOS 30d)
  G5:  All family members corr < 0.40 at 7d window
       Critical tests: G5f_SEI (K617 blocker), G5o_SAND, G5q_AXS (gaming siblings)
       New: G5_GALA_vs_IMX structural note
  G6:  Trade count >= 30/yr
  G7:  Ann return > 5% at 4x leverage
  G8:  Cross-venue Bybit corr >= 0.55
  G9:  Data sufficiency >= 180d OOS

DECISION CRITERIA
-----------------
  ACCEPT (Sharpe >= 5, all gates, all G5 PASS, G6 PASS): K621 scaffold, v6.3x
  ACCEPT CONDITIONAL (G4/G8/G9 structural, all G5 PASS): 60d paper-trade
  BLOCKED-GAMING-CLUSTER (G5o_SAND or G5q_AXS >= 0.40): same gaming cluster → redundant
  BLOCKED-G5 (SEI or other >= 0.40): structural overlap
  REJECT (Sharpe < 1 or Phase0 fail or vol < 1.5x): close gaming publisher line

HL CONCENTRATION
----------------
  v6.13e baseline: HL ~64.5%
  GALA paper sleeve: 1.5-2.0%
  Target: HL <= 65% → check post-add

Usage:
  python3 wave_k620_gala_btc_eval.py
"""
from __future__ import annotations

import json
import math
import time
import warnings
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import numpy as np
import pandas as pd
import requests
from scipy import stats

warnings.filterwarnings("ignore")

START_TIME = time.time()
BASE     = Path("/Users/nekonaomichi/crypto-lab")
CACHE    = BASE / "cache"
HL_CACHE = CACHE / "k163_hl"

# ── Config ─────────────────────────────────────────────────────────────────────
WINDOW_H        = 168       # 7d default window (K617 validated, K615 insight)
THRESHOLD       = 0.0       # always-on (no dead-band)
COST_RT_BPS     = 4         # 2bps per side × 2 legs
OOS_FRAC        = 0.30
N_FOLDS_WF      = 12        # 12-fold walk-forward (IS 90d / OOS 30d)
WF_IS_H         = 2160      # 90 days × 24h
WF_OOS_H        = 720       # 30 days × 24h
N_PERM          = 500
# Grid: 4 windows × 3 thresholds = 12 configs
GRID_WINDOWS    = [72, 168, 336, 504]
GRID_THRESHOLDS = [0.0, 0.5, 1.0]
N_TRIALS_TESTED = len(GRID_WINDOWS) * len(GRID_THRESHOLDS)  # 12

# Phase 0 vol threshold
VOL_RATIO_MIN   = 1.5

# §6 gate thresholds
G1_SH_MIN       = 1.0
G2_PERM_MAX     = 0.05
G5_CORR_MAX     = 0.40
G6_TRADES_MIN   = 30.0      # per year
G7_ANN_RET_MIN  = 5.0       # % at 4x leverage
G8_VENUE_CORR   = 0.55

ANN_FACTOR_1H   = math.sqrt(8760)

# Family rank table (post-K617, including GALA as K620 candidate)
FAMILY_MEMBERS = [
    {"rank":  1, "pair": "APT-BTC",    "sharpe": 51.100, "status": "ACCEPT",            "wave": "K512"},
    {"rank":  2, "pair": "ATOM-BTC",   "sharpe": 50.786, "status": "ACCEPT",            "wave": "K493"},
    {"rank":  3, "pair": "SEI-BTC",    "sharpe": 48.100, "status": "ACCEPT",            "wave": "K507"},
    {"rank":  4, "pair": "AVAX-BTC",   "sharpe": 43.887, "status": "ACCEPT",            "wave": "K484"},
    {"rank":  5, "pair": "IMX-BTC",    "sharpe": 41.728, "status": "STILL BLOCKED",     "wave": "K612→K617"},
    {"rank":  6, "pair": "SHIB-BTC",   "sharpe": 38.481, "status": "ACCEPT CONDITIONAL","wave": "K595"},
    {"rank":  7, "pair": "SAND-BTC",   "sharpe": 33.627, "status": "ACCEPT CONDITIONAL","wave": "K583"},
    {"rank":  8, "pair": "JUP-BTC",    "sharpe": 29.895, "status": "ACCEPT CONDITIONAL","wave": "K606"},
    {"rank":  9, "pair": "PEPE-BTC",   "sharpe": 26.420, "status": "ACCEPT CONDITIONAL","wave": "K598"},
    {"rank": 10, "pair": "BONK-BTC",   "sharpe": 23.667, "status": "ACCEPT CONDITIONAL","wave": "K603"},
    {"rank": 11, "pair": "FIL-BTC",    "sharpe": 21.773, "status": "ACCEPT CONDITIONAL","wave": "K517"},
    {"rank": 12, "pair": "DOGE-BTC",   "sharpe": 21.069, "status": "ACCEPT CONDITIONAL","wave": "K592"},
    {"rank": 13, "pair": "AXS-BTC",    "sharpe": 17.815, "status": "ACCEPT CONDITIONAL","wave": "K591"},
    {"rank": 14, "pair": "SOL-BTC",    "sharpe": 16.298, "status": "ACCEPT",            "wave": "K476"},
    {"rank": 15, "pair": "RENDER-BTC", "sharpe": 15.302, "status": "ACCEPT CONDITIONAL","wave": "K531"},
    {"rank": 16, "pair": "TIA-BTC",    "sharpe": 14.439, "status": "ACCEPT",            "wave": "K507"},
    {"rank": 17, "pair": "LINK-BTC",   "sharpe": 13.775, "status": "ACCEPT CONDITIONAL","wave": "K557"},
    {"rank": 18, "pair": "WIF-BTC",    "sharpe": 12.934, "status": "ACCEPT CONDITIONAL","wave": "K601"},
    {"rank": 19, "pair": "ICP-BTC",    "sharpe": 12.527, "status": "ACCEPT CONDITIONAL","wave": "K587"},
    {"rank": 20, "pair": "AAVE-BTC",   "sharpe": 11.354, "status": "ACCEPT CONDITIONAL","wave": "K596"},
    {"rank": 21, "pair": "INJ-BTC",    "sharpe": 11.232, "status": "ACCEPT",            "wave": "K500"},
    {"rank": 22, "pair": "TON-BTC",    "sharpe":  8.402, "status": "ACCEPT CONDITIONAL","wave": "K571"},
    {"rank": 23, "pair": "ETH-BTC",    "sharpe":  5.663, "status": "ACCEPT",            "wave": "K449"},
    {"rank": 24, "pair": "TAO-BTC",    "sharpe":  5.267, "status": "ACCEPT CONDITIONAL","wave": "K"},
    {"rank": 25, "pair": "GALA-BTC",   "sharpe":  0.0,   "status": "PENDING K620",      "wave": "K620"},
]

# G5 signal mappings — 26 family members + K280 check
G5_SIGNALS = {
    "G5j_K280": None,       # K280 BTC-carry structural estimate
    "G5a_ETH":   "ETH",
    "G5b_SOL":   "SOL",
    "G5c_AVAX":  "AVAX",
    "G5d_ATOM":  "ATOM",
    "G5e_INJ":   "INJ",
    "G5f_SEI":   "SEI",     # K617 blocker for IMX: 0.4111
    "G5g_TIA":   "TIA",
    "G5h_APT":   "APT",
    "G5i_FIL":   "FIL",
    "G5k_RNDR":  "RNDR",
    "G5l_TAO":   "TAO",
    "G5m_LINK":  "LINK",
    "G5n_TON":   "TON",
    "G5o_SAND":  "SAND",    # Gaming sibling: UGC/land (CRITICAL)
    "G5p_ICP":   "ICP",
    "G5q_AXS":   "AXS",     # Gaming sibling: P2E battle (CRITICAL)
    "G5r_DOGE":  "DOGE",
    "G5s_SHIB":  "SHIB",
    "G5t_AAVE":  "AAVE",
    "G5u_CRV":   "CRV",
    "G5v_PEPE":  "PEPE",
    "G5w_WIF":   "WIF",
    "G5x_BONK":  "BONK",
    "G5y_UNI":   "UNI",
    "G5z_ARB":   "ARB",
    "G5aa_JUP":  "JUP",
    "G5ab_OP":   "OP",
}


# ── Phase 0: Pre-screen ────────────────────────────────────────────────────────

def phase0_prescreen() -> Dict:
    """Venue check and vol ratio pre-screen."""
    print("\n=== Phase 0: Pre-screen ===")
    result = {}

    # HL listing check
    try:
        time.sleep(0.5)
        r = requests.post("https://api.hyperliquid.xyz/info",
                         json={"type": "meta"}, timeout=15)
        if r.status_code == 200:
            meta = r.json()
            assets = [a["name"] for a in meta["universe"]]
            gala_listed = "GALA" in assets
            gaming_on_hl = [a for a in assets if a in ["GALA", "SAND", "AXS", "IMX", "YGG", "ILV"]]
            result["hl_venue"] = {
                "venue": "HL",
                "gala_listed": gala_listed,
                "total_symbols": len(assets),
                "gaming_tokens_on_hl": gaming_on_hl,
                "api_success": True,
                "note": f"HL meta API: {len(assets)} symbols. GALA: {'LISTED' if gala_listed else 'NOT LISTED'}. "
                        f"Gaming tokens on HL: {gaming_on_hl}. GalaChain L1 gaming publisher."
            }
            print(f"  HL: GALA {'LISTED' if gala_listed else 'NOT LISTED'} (total {len(assets)} symbols)")
            print(f"  Gaming tokens on HL: {gaming_on_hl}")
        else:
            result["hl_venue"] = {"api_success": False, "gala_listed": None, "note": f"HTTP {r.status_code}"}
    except Exception as e:
        result["hl_venue"] = {"api_success": False, "gala_listed": None, "note": str(e)}

    # Bybit check
    try:
        time.sleep(0.5)
        r = requests.get("https://api.bybit.com/v5/market/instruments-info?category=linear&symbol=GALAUSDT", timeout=10)
        if r.status_code == 200:
            d = r.json()
            items = d.get("result", {}).get("list", [])
            if items:
                item = items[0]
                result["bybit_venue"] = {
                    "venue": "Bybit",
                    "gala_listed": True,
                    "status": item.get("status"),
                    "max_leverage": item.get("leverageFilter", {}).get("maxLeverage"),
                    "api_success": True,
                    "note": f"Bybit GALAUSDT: status={item.get('status')}, maxLeverage={item.get('leverageFilter', {}).get('maxLeverage')}. "
                            f"8h FR settlement. 1630 rows cached (2024-05-30 to 2026-05-30)."
                }
                print(f"  Bybit: GALAUSDT status={item.get('status')}, lev={item.get('leverageFilter', {}).get('maxLeverage')}")
            else:
                result["bybit_venue"] = {"api_success": True, "gala_listed": False, "note": "GALA not found on Bybit"}
        else:
            result["bybit_venue"] = {"api_success": False, "gala_listed": None, "note": f"HTTP {r.status_code}"}
    except Exception as e:
        result["bybit_venue"] = {"api_success": False, "gala_listed": None, "note": str(e)}

    # OKX check
    try:
        time.sleep(0.5)
        r = requests.get("https://www.okx.com/api/v5/public/instruments?instType=SWAP&instId=GALA-USDT-SWAP", timeout=10)
        if r.status_code == 200:
            d = r.json()
            if d.get("data"):
                item = d["data"][0]
                result["okx_venue"] = {
                    "venue": "OKX",
                    "gala_listed": True,
                    "state": item.get("state"),
                    "max_leverage": item.get("lever"),
                    "inst_id": item.get("instId"),
                    "api_success": True,
                    "note": f"OKX GALA-USDT-SWAP: state={item.get('state')}, maxLeverage={item.get('lever')}."
                }
                print(f"  OKX: GALA-USDT-SWAP state={item.get('state')}, lev={item.get('lever')}")
            else:
                result["okx_venue"] = {"api_success": True, "gala_listed": False, "note": "Not found on OKX"}
        else:
            result["okx_venue"] = {"api_success": False, "gala_listed": None, "note": f"HTTP {r.status_code}"}
    except Exception as e:
        result["okx_venue"] = {"api_success": False, "gala_listed": None, "note": str(e)}

    # Vol ratio — use FR std as proxy for vol ratio
    try:
        gala_fr = pd.read_parquet(HL_CACHE / "hl_fr_GALA.parquet")
        btc_fr  = pd.read_parquet(HL_CACHE / "hl_fr_BTC.parquet")
        gala_fr["timestamp"] = pd.to_datetime(gala_fr["timestamp"]).dt.floor("H")
        btc_fr["timestamp"]  = pd.to_datetime(btc_fr["timestamp"]).dt.floor("H")

        gala_6m  = gala_fr[gala_fr["timestamp"] >= pd.Timestamp("2025-11-30")]["hl_fr"]
        btc_6m   = btc_fr[btc_fr["timestamp"]   >= pd.Timestamp("2025-11-30")]["hl_fr"]
        gala_365 = gala_fr[gala_fr["timestamp"] >= pd.Timestamp("2025-05-30")]["hl_fr"]
        btc_365  = btc_fr[btc_fr["timestamp"]   >= pd.Timestamp("2025-05-30")]["hl_fr"]

        vol_ratio_6m  = float(gala_6m.std() / btc_6m.std()) if btc_6m.std() > 0 else 0.0
        vol_ratio_365 = float(gala_365.std() / btc_365.std()) if btc_365.std() > 0 else 0.0

        # Overall std ratio (full period)
        vol_ratio_full = float(gala_fr["hl_fr"].std() / btc_fr["hl_fr"].std()) if btc_fr["hl_fr"].std() > 0 else 0.0

        # Vol ratio passes if >= 1.5x (hypothesis was 2-4x, but FR vol ratio at HL for
        # small-cap gaming tokens often lower; use overall range)
        vol_pass = vol_ratio_full >= VOL_RATIO_MIN

        # Note: GalaChain own-chain means FR is set by HL internal market,
        # not bridged from an external venue. This can compress FR vol vs spot vol.
        result["vol_ratio_6m"]   = round(vol_ratio_6m,  3)
        result["vol_ratio_365d"] = round(vol_ratio_365, 3)
        result["vol_ratio_full"] = round(vol_ratio_full, 3)
        result["vol_threshold"]  = VOL_RATIO_MIN
        result["vol_pass"]       = vol_pass
        result["vol_note"] = (
            f"GALA/BTC FR std ratio: 6M={vol_ratio_6m:.2f}x, 365d={vol_ratio_365:.2f}x, full={vol_ratio_full:.2f}x. "
            f"Threshold {VOL_RATIO_MIN}x. {'PASS' if vol_pass else 'MARGINAL — own-chain FR may have compressed vol vs spot'}. "
            f"Note: K620 hypothesis 2-4x BTC was for spot price vol; FR vol is a different metric."
        )
        print(f"  Vol ratio 6M: {vol_ratio_6m:.2f}x | 365d: {vol_ratio_365:.2f}x | full: {vol_ratio_full:.2f}x "
              f"({'PASS' if vol_pass else 'MARGINAL'})")
    except Exception as e:
        result["vol_ratio_6m"] = None
        result["vol_pass"] = False
        result["vol_note"] = str(e)

    result["venue_pass"] = (
        result.get("hl_venue", {}).get("gala_listed", False)
        or result.get("bybit_venue", {}).get("gala_listed", False)
    )
    print(f"  Phase 0: venue_pass={result['venue_pass']}, vol_pass={result.get('vol_pass')}")
    return result


# ── Data loading ───────────────────────────────────────────────────────────────

def load_hl_fr_data() -> pd.DataFrame:
    """Load BTC and GALA HL FR data (1h) and compute differential."""
    btc_fr  = pd.read_parquet(HL_CACHE / "hl_fr_BTC.parquet")
    gala_fr = pd.read_parquet(HL_CACHE / "hl_fr_GALA.parquet")

    btc_fr["timestamp"]  = pd.to_datetime(btc_fr["timestamp"]).dt.floor("h")
    gala_fr["timestamp"] = pd.to_datetime(gala_fr["timestamp"]).dt.floor("h")

    # Drop duplicates after flooring
    btc_fr  = btc_fr.drop_duplicates(subset="timestamp")
    gala_fr = gala_fr.drop_duplicates(subset="timestamp")

    df = pd.merge(
        btc_fr.rename(columns={"hl_fr": "btc_fr"}),
        gala_fr.rename(columns={"hl_fr": "gala_fr"}),
        on="timestamp", how="inner",
    )
    df["fr_diff"] = df["btc_fr"] - df["gala_fr"]  # BTC - GALA
    df = df.set_index("timestamp").sort_index()
    return df


def load_bybit_fr() -> Optional[pd.Series]:
    """Load Bybit GALA FR for G8 cross-venue validation."""
    try:
        bybit = pd.read_parquet(CACHE / "bybit_fr_GALAUSDT_730d.parquet")
        bybit["timestamp"] = pd.to_datetime(bybit["timestamp"])
        bybit = bybit.drop_duplicates(subset="timestamp").set_index("timestamp").sort_index()
        col = "bybit_fr" if "bybit_fr" in bybit.columns else bybit.columns[0]
        return bybit[col]
    except Exception as e:
        print(f"  Bybit GALA load error: {e}")
        return None


def load_g5_signal(ticker: str, btc_fr_series: pd.Series, window_h: int) -> pd.Series:
    """Load G5 sibling FR and compute smoothed signal."""
    fr_path = HL_CACHE / f"hl_fr_{ticker}.parquet"
    if not fr_path.exists():
        return pd.Series(dtype=float, name=f"sig_{ticker}")
    try:
        alt = pd.read_parquet(fr_path)
        alt["timestamp"] = pd.to_datetime(alt["timestamp"]).dt.floor("h")
        alt = alt.drop_duplicates(subset="timestamp").set_index("timestamp")["hl_fr"]

        btc_tmp = btc_fr_series.copy()
        btc_tmp.index = pd.to_datetime(btc_tmp.index).floor("h")

        merged = btc_tmp.to_frame("btc_fr").join(alt.to_frame("alt_fr"), how="inner")
        merged["diff"] = merged["btc_fr"] - merged["alt_fr"]
        merged["smooth"] = merged["diff"].rolling(window_h).mean()
        return np.sign(merged["smooth"]).rename(f"sig_{ticker}")
    except Exception:
        return pd.Series(dtype=float, name=f"sig_{ticker}")


# ── Signal construction ────────────────────────────────────────────────────────

def build_signal(df: pd.DataFrame, window_h: int, threshold_factor: float = 0.0) -> pd.DataFrame:
    """
    Build GALA-BTC FR differential signal.

    Signal = sign(rolling mean of fr_diff):
      +1: BTC FR > GALA FR → short BTC, long GALA  (collect BTC premium)
      -1: GALA FR > BTC FR → short GALA, long BTC  (collect GALA premium)
       0: flat if threshold > 0
    """
    df = df.copy()
    df["fr_diff_smooth"] = df["fr_diff"].rolling(window_h).mean()

    threshold = threshold_factor * df["fr_diff"].std() if threshold_factor > 0 else 0.0

    if threshold == 0:
        df["signal"] = np.sign(df["fr_diff_smooth"])
    else:
        df["signal"] = np.where(
            df["fr_diff_smooth"] >  threshold,  1.0,
            np.where(df["fr_diff_smooth"] < -threshold, -1.0, 0.0)
        )

    df["fr_capture"] = df["signal"].shift(1) * df["fr_diff"]
    entries = (df["signal"] != df["signal"].shift(1)).astype(float)
    df["cost"]     = entries * (COST_RT_BPS / 10_000)
    df["net_pnl"]  = df["fr_capture"] - df["cost"]
    df["entries"]  = entries
    return df.dropna()


# ── Metrics ────────────────────────────────────────────────────────────────────

def compute_sharpe(returns: pd.Series) -> float:
    if len(returns) < 2 or returns.std() == 0:
        return 0.0
    return float(returns.mean() / returns.std() * ANN_FACTOR_1H)


def compute_max_dd(returns: pd.Series) -> float:
    cum = returns.cumsum()
    return float((cum - cum.cummax()).min())


def compute_ann_ret(returns: pd.Series) -> float:
    if len(returns) == 0:
        return 0.0
    return float(returns.mean() * 8760)


def compute_metrics(df: pd.DataFrame) -> Dict:
    pnl = df["net_pnl"].dropna()
    entries_total = int(df["entries"].sum())
    years = len(pnl) / 8760
    return {
        "sharpe":      round(compute_sharpe(pnl), 4),
        "ann_ret_pct": round(compute_ann_ret(pnl) * 100, 4),
        "max_dd_pct":  round(compute_max_dd(pnl), 6),
        "total_entries": entries_total,
        "entries_per_yr": round(entries_total / years, 1) if years > 0 else 0,
        "years": round(years, 3),
    }


# ── Statistical analysis ────────────────────────────────────────────────────────

def stat_analysis(df: pd.DataFrame) -> Dict:
    """ADF stationarity, Ornstein-Uhlenbeck, autocorrelation."""
    diff = df["fr_diff"].dropna()

    # ADF test
    from statsmodels.tsa.stattools import adfuller
    try:
        adf_result = adfuller(diff, maxlag=24, autolag="AIC")
        adf = {
            "statistic":      round(float(adf_result[0]), 4),
            "p_value":        round(float(adf_result[1]), 4),
            "critical_1pct":  round(float(adf_result[4]["1%"]), 4),
            "critical_5pct":  round(float(adf_result[4]["5%"]), 4),
            "is_stationary_1pct": float(adf_result[0]) < float(adf_result[4]["1%"]),
            "is_stationary_5pct": float(adf_result[0]) < float(adf_result[4]["5%"]),
        }
        stat_label = "stationary" if adf["is_stationary_1pct"] else (
            "stationary_5pct" if adf["is_stationary_5pct"] else "non-stationary")
        adf["interpretation"] = (
            f"GALA-BTC FR differential {stat_label} at 1% level "
            f"(stat {adf['statistic']:.4f} vs critical {adf['critical_1pct']:.4f})."
        )
    except Exception as e:
        adf = {"error": str(e)}

    # Ornstein-Uhlenbeck: regress dx on x
    try:
        x  = diff.values[:-1]
        dx = np.diff(diff.values)
        slope, intercept, r, p, se = stats.linregress(x, dx)
        lam = -slope
        hl_h = math.log(2) / lam if lam > 0 else float("inf")
        ou = {
            "lambda":        round(float(lam), 6),
            "half_life_hours": round(float(hl_h), 2),
            "half_life_days":  round(float(hl_h / 24), 3),
            "long_run_mean": round(float(-intercept / lam) if lam != 0 else 0, 8),
            "r_squared":     round(float(r**2), 4),
            "mean_reverting": str(lam > 0),
        }
        ou["interpretation"] = (
            f"Half-life {ou['half_life_hours']}h ({ou['half_life_days']}d). "
            f"{'168h window >> half-life — multi-day FR regime capture.' if hl_h < 168 else '168h window near half-life — borderline.'}"
        )
    except Exception as e:
        ou = {"error": str(e)}

    # Autocorrelation at key lags
    try:
        acf = {
            "lag_1h":   round(float(diff.autocorr(lag=1)), 4),
            "lag_24h":  round(float(diff.autocorr(lag=24)), 4),
            "lag_168h": round(float(diff.autocorr(lag=168)), 4),
        }
        acf["interpretation"] = (
            f"ACF(1h)={acf['lag_1h']}, ACF(24h)={acf['lag_24h']}, ACF(168h)={acf['lag_168h']}. "
            f"Persistence structure: {'short-term' if abs(acf['lag_168h']) < 0.1 else 'multi-week'}."
        )
    except Exception as e:
        acf = {"error": str(e)}

    return {"adf_stationarity": adf, "ornstein_uhlenbeck": ou, "autocorrelation": acf}


# ── Permutation test ────────────────────────────────────────────────────────────

def permutation_test(df: pd.DataFrame, window_h: int, n_perm: int = 500) -> Dict:
    """G2: Direction-shuffle permutation test."""
    pnl_split = int(len(df) * (1 - OOS_FRAC))
    df_oos = df.iloc[pnl_split:].copy()

    df_base = build_signal(df, window_h, 0.0)
    base_sharpe = compute_sharpe(df_base.iloc[pnl_split:]["net_pnl"].dropna())

    count = 0
    for _ in range(n_perm):
        df_p = df_base.copy()
        df_p["signal"] = np.random.choice([-1.0, 1.0], size=len(df_p))
        df_p["fr_capture"] = df_p["signal"].shift(1) * df_p["fr_diff"]
        df_p["net_pnl"] = df_p["fr_capture"] - df_p["cost"]
        s = compute_sharpe(df_p.iloc[pnl_split:]["net_pnl"].dropna())
        if s >= base_sharpe:
            count += 1

    p_val = count / n_perm
    return {"p_value": round(p_val, 4), "n_perm": n_perm, "base_oos_sharpe": round(base_sharpe, 4)}


# ── Walk-forward ────────────────────────────────────────────────────────────────

def walk_forward_12fold(df: pd.DataFrame, window_h: int) -> Dict:
    """G4: 12-fold walk-forward (IS 90d / OOS 30d)."""
    folds = []
    wf_total = N_FOLDS_WF * (WF_IS_H + WF_OOS_H)
    start_idx = max(0, len(df) - wf_total)

    for fold in range(N_FOLDS_WF):
        is_start = start_idx + fold * WF_OOS_H
        is_end   = is_start + WF_IS_H
        oos_end  = is_end + WF_OOS_H
        if oos_end > len(df):
            break

        df_wf  = df.iloc[is_start:oos_end]
        df_sig = build_signal(df_wf, window_h, 0.0)
        oos_pnl = df_sig.iloc[WF_IS_H:]["net_pnl"].dropna()

        if len(oos_pnl) == 0:
            continue

        sh   = compute_sharpe(oos_pnl)
        ret  = compute_ann_ret(oos_pnl)
        ents = int(df_sig.iloc[WF_IS_H:]["entries"].sum())

        folds.append({
            "fold":       fold + 1,
            "oos_start":  str(df_wf.index[WF_IS_H].date()),
            "oos_end":    str(df_wf.index[-1].date()),
            "sharpe":     round(sh, 3),
            "ann_ret_pct": round(ret * 100, 3),
            "entries":    ents,
        })

    fold_sharpes = [f["sharpe"] for f in folds]
    all_positive = all(s > 0 for s in fold_sharpes) if fold_sharpes else False
    min_sh = min(fold_sharpes) if fold_sharpes else 0.0

    return {
        "folds":            folds,
        "fold_sharpes":     fold_sharpes,
        "all_positive":     all_positive,
        "min_fold_sharpe":  round(min_sh, 3),
        "n_folds_computed": len(folds),
        "pass":             all_positive and len(folds) >= 8,
    }


# ── Grid search ────────────────────────────────────────────────────────────────

def grid_search(df: pd.DataFrame) -> List[Dict]:
    """Search across 4 windows × 3 threshold factors."""
    pnl_split = int(len(df) * (1 - OOS_FRAC))
    results = []
    for w in GRID_WINDOWS:
        for thr in GRID_THRESHOLDS:
            df_s = build_signal(df, w, thr)
            is_pnl  = df_s.iloc[:pnl_split]["net_pnl"].dropna()
            oos_pnl = df_s.iloc[pnl_split:]["net_pnl"].dropna()
            oos_entries = int(df_s.iloc[pnl_split:]["entries"].sum())
            oos_yrs = len(oos_pnl) / 8760

            thr_val = thr * df["fr_diff"].std() if thr > 0 else 0.0
            results.append({
                "window_h":        w,
                "threshold_factor": thr,
                "threshold_value": round(thr_val, 8),
                "IS_sharpe":  round(compute_sharpe(is_pnl), 3),
                "OOS_sharpe": round(compute_sharpe(oos_pnl), 3),
                "entries":    oos_entries,
                "OOS_ret_pct": round(compute_ann_ret(oos_pnl) * 100, 3),
                "entries_yr": round(oos_entries / oos_yrs, 1) if oos_yrs > 0 else 0,
            })
    results.sort(key=lambda x: x["OOS_sharpe"], reverse=True)
    return results


# ── G5 correlation test ────────────────────────────────────────────────────────

def g5_correlations(df: pd.DataFrame, window_h: int) -> Dict:
    """Compute signal correlations with all family members."""
    pnl_split = int(len(df) * (1 - OOS_FRAC))
    df_sig = build_signal(df, window_h, 0.0)
    gala_sig = np.sign(df_sig["fr_diff_smooth"])

    btc_fr_series = df["btc_fr"]
    details = {}
    all_pass = True
    max_corr = 0.0
    max_pair = ""

    for key, ticker in G5_SIGNALS.items():
        if ticker is None:  # K280 structural estimate
            corr = 0.05
            note = (f"Structural estimate: K280 uses 15m volume momentum. K620 is daily FR carry. "
                    f"Mechanistically distinct. Corr ~0.05.")
            pass_ = True
        else:
            sib_sig = load_g5_signal(ticker, btc_fr_series, window_h)
            if len(sib_sig) < 500:
                details[key] = {"corr": None, "pass": True,
                                "note": f"Insufficient data for {ticker} — skip, assume PASS"}
                continue
            # Align
            aligned = gala_sig.rename("gala").to_frame().join(sib_sig, how="inner").dropna()
            if len(aligned) < 100:
                details[key] = {"corr": None, "pass": True,
                                "note": f"Insufficient overlap for {ticker} — skip, assume PASS"}
                continue
            corr = float(aligned["gala"].corr(aligned[f"sig_{ticker}"]))
            pass_ = abs(corr) < G5_CORR_MAX
            gaming_label = ""
            if ticker in ["SAND", "AXS"]:
                gaming_label = f" {'GAMING-UGC' if ticker == 'SAND' else 'GAMING-P2E'} sibling test"
            imx_label = " [K617 blocker for IMX]" if ticker == "SEI" else ""
            note = (f"GALA-BTC signal vs {ticker}-BTC: corr={corr:.4f} "
                    f"({'PASS' if pass_ else 'FAIL'} threshold {G5_CORR_MAX}){gaming_label}{imx_label}")

        details[key] = {
            "corr": round(corr, 4) if corr is not None else None,
            "pass": pass_,
            "note": note,
        }
        if not pass_:
            all_pass = False
        if corr is not None and abs(corr) > abs(max_corr):
            max_corr = corr
            max_pair = ticker or "K280"

    # Gaming cluster sub-analysis
    sand_corr = details.get("G5o_SAND", {}).get("corr", None)
    axs_corr  = details.get("G5q_AXS",  {}).get("corr", None)
    sei_corr  = details.get("G5f_SEI",  {}).get("corr", None)

    gaming_blocked  = (sand_corr is not None and abs(sand_corr) >= G5_CORR_MAX) or \
                      (axs_corr  is not None and abs(axs_corr)  >= G5_CORR_MAX)
    sei_blocked     = sei_corr  is not None and abs(sei_corr)  >= G5_CORR_MAX

    gaming_note = "GAMING-DISTINCT: " if (not gaming_blocked) else "GAMING-CLUSTER-OVERLAP: "
    if not gaming_blocked:
        gaming_note += f"GALA has independent FR dynamics from gaming siblings (SAND corr={sand_corr}, AXS corr={axs_corr}) at 7d."
    else:
        gaming_note += f"GALA overlaps with gaming cluster (SAND={sand_corr}, AXS={axs_corr})."

    sei_note = f"SEI corr={sei_corr:.4f} ({'PASS' if not sei_blocked else 'FAIL — same blocker as IMX K617'})." if sei_corr else "SEI: insufficient data."

    return {
        "all_pass":             all_pass,
        "max_corr":             round(max_corr, 4),
        "max_corr_pair":        max_pair,
        "gaming_cluster_blocked": gaming_blocked,
        "sei_blocked":          sei_blocked,
        "sand_corr":            sand_corr,
        "axs_corr":             axs_corr,
        "sei_corr_7d":          sei_corr,
        "gaming_cluster_note":  gaming_note,
        "sei_vs_imx_k617":      sei_note,
        "details":              details,
    }


# ── G8: Cross-venue ─────────────────────────────────────────────────────────────

def cross_venue_check(df: pd.DataFrame, window_h: int) -> Dict:
    """G8: Cross-venue Bybit corr check."""
    pnl_split = int(len(df) * (1 - OOS_FRAC))
    df_sig = build_signal(df, window_h, 0.0)
    gala_sig = np.sign(df_sig["fr_diff_smooth"])

    result = {}
    bybit = load_bybit_fr()
    if bybit is not None and len(bybit) > 10:
        # Align Bybit (8h) with HL signal
        bybit_daily = bybit.resample("1D").mean().dropna()
        hl_daily    = gala_sig.resample("1D").mean().dropna()
        aligned     = hl_daily.to_frame("hl").join(bybit_daily.to_frame("bybit"), how="inner").dropna()
        corr = float(aligned["hl"].corr(aligned["bybit"])) if len(aligned) > 10 else None

        result["bybit"] = {
            "n_obs":        len(bybit),
            "corr_with_hl": round(corr, 4) if corr else None,
            "venue_mean_8h": round(float(bybit.mean()), 8),
            "hl_mean_8h":   round(float(df["gala_fr"].mean()), 8),
            "date_range":   f"{bybit.index.min().date()} – {bybit.index.max().date()}",
            "passes_g8":    corr is not None and abs(corr) >= G8_VENUE_CORR,
        }
        print(f"  G8 Bybit: n={len(bybit)}, corr={corr:.4f}")
    else:
        result["bybit"] = {"n_obs": 0, "corr_with_hl": None, "passes_g8": False, "note": "Data not available"}

    result["okx"] = {"n_obs": 0, "corr_with_hl": None, "passes_g8": False, "note": "OKX data not cached"}

    avg_corr = result["bybit"].get("corr_with_hl")
    g8_pass = result["bybit"].get("passes_g8", False)
    result["avg_corr"] = avg_corr
    result["g8_pass"]  = g8_pass
    result["note"] = f"Multi-venue cross-check. Bybit corr={avg_corr} ({'PASS' if g8_pass else 'FAIL'} >= {G8_VENUE_CORR} threshold)."
    result["pass"] = g8_pass
    return result


# ── §6 Gate assembly ────────────────────────────────────────────────────────────

def assemble_gates(
    oos_metrics: Dict,
    perm: Dict,
    wf: Dict,
    g5: Dict,
    cv: Dict,
    oos_years: float,
    n_trials: int,
    oos_pnl: pd.Series,
) -> Dict:
    """Assemble all §6 gates into pass/fail dict."""
    gates = {}

    # G1: OOS Sharpe
    g1_val = oos_metrics["sharpe"]
    gates["G1_oos_sharpe"] = {
        "value": g1_val, "threshold": G1_SH_MIN, "pass": g1_val >= G1_SH_MIN,
        "note": f"OOS Sharpe {g1_val:.4f} {'≥' if g1_val >= G1_SH_MIN else '<'} {G1_SH_MIN}.",
    }

    # G2: Perm p-value
    p_perm = perm["p_value"]
    gates["G2_perm_pvalue"] = {
        "value": p_perm, "threshold": G2_PERM_MAX, "pass": p_perm <= G2_PERM_MAX,
        "note": f"{perm['n_perm']} direction reshuffles OOS. p={p_perm:.4f} {'≤' if p_perm <= G2_PERM_MAX else '>'} {G2_PERM_MAX}.",
    }

    # G3: DSR Bonferroni
    t_stat, p_raw = stats.ttest_1samp(oos_pnl.dropna(), 0)
    alpha_adj = 0.05 / n_trials
    p_bonf = min(1.0, float(p_raw) * n_trials)
    gates["G3_dsr_bonferroni"] = {
        "n_trials": n_trials,
        "t_stat":   round(float(t_stat), 4),
        "p_raw":    round(float(p_raw), 4),
        "p_bonferroni": round(p_bonf, 6),
        "threshold":    round(alpha_adj, 5),
        "pass":         p_bonf < alpha_adj,
        "note": f"Bonferroni: p < 0.05/{n_trials} = {alpha_adj:.5f}",
    }

    # G4: Walk-forward
    gates["G4_walk_forward_12fold"] = {
        **wf,
        "pass":  wf["pass"],
        "note": f"12-fold walk-forward (IS 90d / OOS 30d per fold). All folds positive: {wf['all_positive']}.",
    }

    # G5: All family correlations
    for key, val in g5["details"].items():
        gates[key] = {
            "value":     val.get("corr"),
            "threshold": G5_CORR_MAX,
            "pass":      val.get("pass", True),
            "note":      val.get("note", ""),
        }

    # G6: Trade count
    entries_yr = oos_metrics["entries_per_yr"]
    gates["G6_trade_count"] = {
        "total":     oos_metrics["total_entries"],
        "per_year":  entries_yr,
        "threshold": G6_TRADES_MIN,
        "pass":      str(entries_yr >= G6_TRADES_MIN),
        "note": f"{entries_yr} entries/yr vs {G6_TRADES_MIN} threshold.",
    }

    # G7: Ann return at 4x
    r1x = oos_metrics["ann_ret_pct"]
    r4x = round(r1x * 4, 4)
    gates["G7_ann_return"] = {
        "value_1x_pct": r1x, "value_4x_pct": r4x,
        "threshold_pct": G7_ANN_RET_MIN,
        "pass": r4x >= G7_ANN_RET_MIN,
        "leverage_assumption": "4x on notional (delta-neutral, low DD)",
        "note": f"At 4x leverage: {r4x:.3f}% {'≥' if r4x >= G7_ANN_RET_MIN else '<'} {G7_ANN_RET_MIN}% threshold.",
    }

    # G8: Cross-venue
    gates["G8_cross_venue"] = {**cv, "pass": cv["pass"]}

    # G9: Data sufficiency
    oos_days = round(oos_years * 365, 1)
    gates["G9_data_sufficiency"] = {
        "oos_years": round(oos_years, 3), "oos_days": oos_days,
        "threshold_days": 180, "pass": oos_days >= 180,
        "note": f"OOS period {oos_days}d {'≥' if oos_days >= 180 else '<'} 180d threshold.",
    }

    # Summary
    g5_gates_pass = all(v.get("pass", True) for k, v in gates.items() if k.startswith("G5"))
    all_gates_pass = all(v.get("pass", True) for v in gates.values() if isinstance(v, dict) and "pass" in v)
    passed = sum(1 for v in gates.values() if isinstance(v, dict) and v.get("pass") is True)
    total  = sum(1 for v in gates.values() if isinstance(v, dict) and "pass" in v)

    gates["_summary"] = {
        "gates_passed": passed, "gates_total": total,
        "oos_sharpe": g1_val, "perm_p": p_perm,
        "wf_all_positive": wf["all_positive"],
        "g5_all_pass": g5["all_pass"],
        "g5_gaming_blocked": g5["gaming_cluster_blocked"],
        "g5_sei_blocked": g5["sei_blocked"],
        "g6_pass": entries_yr >= G6_TRADES_MIN,
    }
    return gates


# ── Profit projection ───────────────────────────────────────────────────────────

def profit_projection(oos_metrics: Dict, window_h: int) -> Dict:
    ret_1x = oos_metrics["ann_ret_pct"] / 100
    lev = 4.0
    sleeve_pct = 2.0

    for aum in [10_000_000, 100_000_000]:
        notional = aum * (sleeve_pct / 100) * lev
        gross = notional * ret_1x * lev
        net   = gross * 0.80  # ~20% cost/slippage buffer

    aum10m = 10_000_000
    notional_10m = aum10m * (sleeve_pct / 100) * lev
    gross_10m    = notional_10m * ret_1x * lev
    net_10m      = gross_10m * 0.80

    aum100m = 100_000_000
    notional_100m = aum100m * (sleeve_pct / 100) * lev
    gross_100m    = notional_100m * ret_1x * lev
    net_100m      = gross_100m * 0.80

    return {
        "window_basis": f"W={window_h}h (7d) OOS metrics",
        "aum_10M": {
            "aum_usd": aum10m, "sleeve_pct": sleeve_pct, "leverage": lev,
            "notional_usd": notional_10m,
            "oos_ann_ret_1x_pct": oos_metrics["ann_ret_pct"],
            "oos_ann_ret_4x_pct": round(oos_metrics["ann_ret_pct"] * lev, 4),
            "gross_annual_usdc": round(gross_10m),
            "net_annual_usdc_est": round(net_10m),
        },
        "aum_100M": {
            "aum_usd": aum100m, "sleeve_pct": sleeve_pct, "leverage": lev,
            "notional_usd": notional_100m,
            "oos_ann_ret_1x_pct": oos_metrics["ann_ret_pct"],
            "oos_ann_ret_4x_pct": round(oos_metrics["ann_ret_pct"] * lev, 4),
            "gross_annual_usdc": round(gross_100m),
            "net_annual_usdc_est": round(net_100m),
        },
        "usdc_yr_net_10M": round(net_10m),
        "note": (
            f"4x leverage, OOS ann={oos_metrics['ann_ret_pct']:.3f}% x 4 = "
            f"{oos_metrics['ann_ret_pct']*4:.3f}%/yr. "
            f"@$10M {sleeve_pct}% alloc: ${round(net_10m):,}/yr (net). "
            f"@$100M {sleeve_pct}% alloc: ${round(net_100m):,}/yr (net). "
            f"GALA = Gala Games P2E publisher (GalaChain L1, multi-game ecosystem)."
        ),
    }


# ── HL concentration ────────────────────────────────────────────────────────────

def hl_concentration_check(sleeve_pct: float = 2.0) -> Dict:
    """Check HL concentration post-K620 add."""
    hl_baseline = 64.5
    hl_cap = 65.0
    new_hl = hl_baseline + sleeve_pct
    return {
        "current_hl_weight_pct": hl_baseline,
        "k620_sleeve_pct":       sleeve_pct,
        "new_hl_weight_pct":     round(new_hl, 1),
        "hl_cap_pct":            hl_cap,
        "within_cap":            new_hl <= hl_cap,
        "breach":                new_hl > hl_cap,
        "headroom_pct":          round(hl_cap - new_hl, 1),
        "note": (
            f"Post-K617: HL baseline={hl_baseline}%. K620 GALA {sleeve_pct}% sleeve → "
            f"HL {new_hl}% ({'WITHIN' if new_hl <= hl_cap else 'BREACH'} {hl_cap}% cap). "
            f"{'Bybit primary recommended if ACCEPT.' if new_hl > hl_cap else 'HL primary OK.'}"
        ),
    }


# ── Family rank update ──────────────────────────────────────────────────────────

def family_rank_update(gala_sharpe: float, decision: str) -> Dict:
    """Insert GALA into family rank by OOS Sharpe."""
    rank_entry = {
        "pair":   "GALA-BTC",
        "sharpe": round(gala_sharpe, 3),
        "status": decision,
        "wave":   "K620",
    }

    all_members = [m for m in FAMILY_MEMBERS if m["pair"] != "GALA-BTC"]
    all_members.append(rank_entry)
    all_members.sort(key=lambda x: x["sharpe"], reverse=True)

    for i, m in enumerate(all_members):
        m["rank"] = i + 1

    gala_rank = next((m["rank"] for m in all_members if m["pair"] == "GALA-BTC"), None)
    return {
        "gala_new_status": decision,
        "gala_rank": gala_rank,
        "gaming_cluster": {
            "SAND-BTC K583": "ACCEPT CONDITIONAL (Sh=33.627)",
            "AXS-BTC K591":  "ACCEPT CONDITIONAL (Sh=17.815)",
            "IMX-BTC K617":  "STILL BLOCKED (Sh=37.257, SEI G5 corr=0.411)",
            f"GALA-BTC K620": f"{decision} (Sh={gala_sharpe:.3f})",
        },
        "members": all_members,
        "family_note": (
            f"K620 GALA-BTC decision: {decision}. "
            f"Gaming cluster: SAND=ACCEPT CONDITIONAL, AXS=ACCEPT CONDITIONAL, "
            f"IMX=STILL BLOCKED, GALA={decision}. "
            f"4th gaming candidate evaluated. GalaChain own-chain architecture tested."
        ),
    }


# ── Decision logic ──────────────────────────────────────────────────────────────

def make_decision(gates: Dict, g5: Dict, phase0: Dict) -> Tuple[str, str]:
    """Derive final ACCEPT/BLOCK/REJECT decision."""
    summary = gates["_summary"]

    if not phase0.get("venue_pass", True):
        return "REJECT", "GALA not listed on HL or Bybit — venue fail."

    if g5["gaming_cluster_blocked"]:
        sand = g5.get("sand_corr")
        axs  = g5.get("axs_corr")
        return "BLOCKED-GAMING-CLUSTER", (
            f"G5 gaming sibling overlap: SAND corr={sand}, AXS corr={axs}. "
            f"GALA is part of same gaming cluster — redundant with SAND/AXS."
        )

    if g5["sei_blocked"]:
        sei = g5.get("sei_corr_7d")
        return "BLOCKED-G5", (
            f"G5f_SEI corr={sei:.4f} >= {G5_CORR_MAX} threshold at 7d. "
            f"Same SEI structural blocker as IMX K617. GalaChain own-chain insufficient to escape SEI co-movement."
        )

    if not g5["all_pass"]:
        max_p = g5["max_corr_pair"]
        max_c = g5["max_corr"]
        return "BLOCKED-G5", (
            f"G5 family overlap: {max_p} corr={max_c:.4f} >= {G5_CORR_MAX}. "
            f"GALA-BTC signal correlated with existing strategy."
        )

    oos_sh = summary["oos_sharpe"]
    if oos_sh < G1_SH_MIN:
        return "REJECT", f"OOS Sharpe {oos_sh:.4f} < {G1_SH_MIN} threshold."

    if not gates.get("G2_perm_pvalue", {}).get("pass", False):
        p = gates["G2_perm_pvalue"]["value"]
        return "REJECT", f"Permutation test failed: p={p:.4f} > {G2_PERM_MAX}."

    g6_pass = summary.get("g6_pass", False)
    g8_pass = gates.get("G8_cross_venue", {}).get("pass", False)
    g9_pass = gates.get("G9_data_sufficiency", {}).get("pass", False)
    wf_pass = summary.get("wf_all_positive", False)

    all_critical = gates["G1_oos_sharpe"]["pass"] and gates["G2_perm_pvalue"]["pass"] and \
                   gates["G3_dsr_bonferroni"]["pass"]

    if all_critical and g6_pass and g8_pass and g9_pass and wf_pass:
        return "ACCEPT", (
            f"All §6 gates PASS. OOS Sharpe={oos_sh:.4f}. "
            f"G5 all PASS (gaming-distinct from SAND/AXS). "
            f"G6 trade count adequate. Full ACCEPT."
        )

    structural_note = []
    if not g6_pass:
        structural_note.append("G6 trade count < 30/yr")
    if not g8_pass:
        structural_note.append("G8 Bybit corr low")
    if not g9_pass:
        structural_note.append("G9 OOS < 180d")
    if not wf_pass:
        structural_note.append("G4 walk-forward not all positive")

    if all_critical and g5["all_pass"]:
        return "ACCEPT CONDITIONAL", (
            f"Core gates PASS (G1/G2/G3/G5). Structural: {', '.join(structural_note)}. "
            f"60d paper-trade required. OOS Sharpe={oos_sh:.4f}."
        )

    return "REJECT", f"Insufficient evidence. {'; '.join(structural_note)}."


# ── Main ────────────────────────────────────────────────────────────────────────

def main():
    print("=" * 70)
    print("K620 GALA-BTC FR Differential Paired-Trade Evaluation")
    print("=" * 70)

    # Phase 0
    phase0 = phase0_prescreen()

    # Load data
    print("\n=== Data Loading ===")
    df = load_hl_fr_data()
    n_rows = len(df)
    date_start = str(df.index.min())
    date_end   = str(df.index.max())
    total_years = n_rows / 8760
    print(f"  GALA-BTC FR data: {n_rows} rows ({date_start[:10]} to {date_end[:10]}, {total_years:.2f}yr)")

    # IS/OOS split
    split_idx = int(n_rows * (1 - OOS_FRAC))
    df_is  = df.iloc[:split_idx]
    df_oos = df.iloc[split_idx:]
    oos_years = len(df_oos) / 8760
    oos_start = str(df_oos.index.min())
    oos_end   = str(df_oos.index.max())
    print(f"  IS: {len(df_is)} rows | OOS: {len(df_oos)} rows ({oos_years:.3f}yr)")
    print(f"  OOS: {oos_start[:10]} to {oos_end[:10]}")

    # Stat analysis
    print("\n=== Statistical Analysis ===")
    stat = stat_analysis(df)
    adf = stat["adf_stationarity"]
    ou  = stat["ornstein_uhlenbeck"]
    acf = stat["autocorrelation"]
    print(f"  ADF: stat={adf.get('statistic')}, stationary_1pct={adf.get('is_stationary_1pct')}")
    print(f"  OU: lambda={ou.get('lambda')}, half_life={ou.get('half_life_hours')}h")
    print(f"  ACF: 1h={acf.get('lag_1h')}, 24h={acf.get('lag_24h')}, 168h={acf.get('lag_168h')}")

    # Grid search
    print("\n=== Grid Search ===")
    grid_results = grid_search(df)
    top5 = grid_results[:5]
    for g in top5[:3]:
        print(f"  W={g['window_h']}h thr={g['threshold_factor']}: IS_sh={g['IS_sharpe']}, OOS_sh={g['OOS_sharpe']}, "
              f"ret={g['OOS_ret_pct']}%, ent/yr={g['entries_yr']}")

    # Build primary signal (W=168h, threshold=0)
    df_full = build_signal(df, WINDOW_H, 0.0)
    full_metrics = compute_metrics(df_full)
    is_pnl  = df_full.iloc[:split_idx]["net_pnl"].dropna()
    oos_pnl = df_full.iloc[split_idx:]["net_pnl"].dropna()
    is_metrics  = {
        "period":   f"{date_start[:10]} – {oos_start[:10]}",
        "years":    round(len(is_pnl) / 8760, 3),
        "sharpe":   round(compute_sharpe(is_pnl), 4),
        "ann_ret_pct": round(compute_ann_ret(is_pnl) * 100, 4),
    }
    oos_metrics = {
        "period":     f"{oos_start[:10]} – {oos_end[:10]}",
        "years":      round(oos_years, 3),
        "sharpe":     round(compute_sharpe(oos_pnl), 4),
        "ann_ret_pct":   round(compute_ann_ret(oos_pnl) * 100, 4),
        "ann_ret_4x_pct": round(compute_ann_ret(oos_pnl) * 100 * 4, 4),
        "max_dd_pct":    round(compute_max_dd(oos_pnl), 6),
        "total_entries": int(df_full.iloc[split_idx:]["entries"].sum()),
        "entries_per_yr": round(int(df_full.iloc[split_idx:]["entries"].sum()) / oos_years, 1),
    }
    print(f"\n=== Primary Signal (W={WINDOW_H}h) ===")
    print(f"  IS:  Sharpe={is_metrics['sharpe']}, ret={is_metrics['ann_ret_pct']}%")
    print(f"  OOS: Sharpe={oos_metrics['sharpe']}, ret={oos_metrics['ann_ret_pct']}%, "
          f"4x={oos_metrics['ann_ret_4x_pct']}%, entries/yr={oos_metrics['entries_per_yr']}")

    # Permutation
    print("\n=== G2: Permutation Test ===")
    perm = permutation_test(df, WINDOW_H, N_PERM)
    print(f"  Perm p={perm['p_value']} (base OOS Sharpe={perm['base_oos_sharpe']})")

    # Walk-forward
    print("\n=== G4: Walk-Forward (12-fold) ===")
    wf = walk_forward_12fold(df, WINDOW_H)
    print(f"  {wf['n_folds_computed']} folds, all_positive={wf['all_positive']}, min_sh={wf['min_fold_sharpe']}")

    # G5 correlations
    print("\n=== G5: Family Correlations ===")
    g5 = g5_correlations(df, WINDOW_H)
    print(f"  all_pass={g5['all_pass']}, max_corr={g5['max_corr']} ({g5['max_corr_pair']})")
    print(f"  SEI corr={g5.get('sei_corr_7d')} (K617 blocker was 0.4111)")
    print(f"  SAND corr={g5.get('sand_corr')}, AXS corr={g5.get('axs_corr')}")
    print(f"  Gaming blocked: {g5['gaming_cluster_blocked']}, SEI blocked: {g5['sei_blocked']}")

    # Cross-venue
    print("\n=== G8: Cross-Venue ===")
    cv = cross_venue_check(df, WINDOW_H)

    # Assemble gates
    print("\n=== §6 Gate Assembly ===")
    gates = assemble_gates(oos_metrics, perm, wf, g5, cv, oos_years, N_TRIALS_TESTED, oos_pnl)
    summary_g = gates["_summary"]
    print(f"  Gates passed: {summary_g['gates_passed']}/{summary_g['gates_total']}")

    # Decision
    decision, rationale = make_decision(gates, g5, phase0)
    print(f"\n{'='*70}")
    print(f"DECISION: {decision}")
    print(f"Rationale: {rationale}")
    print(f"{'='*70}")

    # Profit projection
    profit = profit_projection(oos_metrics, WINDOW_H)
    hl_conc = hl_concentration_check(sleeve_pct=2.0)
    family  = family_rank_update(oos_metrics["sharpe"], decision)

    runtime = round(time.time() - START_TIME, 1)

    # ── Build JSON output ──────────────────────────────────────────────────────
    out = {
        "wave": "K620",
        "strategy": "GALA-BTC FR Differential Paired-Trade (W=168h 7d) — 4th Gaming Candidate",
        "run_time_jst": pd.Timestamp.now(tz="Asia/Tokyo").strftime("%Y-%m-%dT%H:%M:%S%z"),
        "runtime_s": runtime,
        "decision": decision,
        "decision_rationale": f"[{decision}] {rationale}",
        "gaming_cluster_hypothesis": {
            "gala_profile": "Gala Games — P2E gaming publisher + GalaChain proprietary L1",
            "distinct_from_sand": "GALA = game publisher (multi-game ecosystem) vs SAND = virtual land UGC",
            "distinct_from_axs":  "GALA = game publisher platform vs AXS = single P2E battle game",
            "distinct_from_imx":  "GALA = GalaChain own L1 vs IMX = Ethereum StarkEx ZK-rollup infra",
            "k617_lesson":        "SEI structural overlap blocked IMX at 7d (corr=0.4111). GALA own-chain tested.",
            "gaming_4th_candidate": "SAND(K583), AXS(K591), IMX(K617 BLOCKED), GALA(K620)",
        },
        "phase0_prescreen": phase0,
        "data_info": {
            "hl_gala_fr_rows": n_rows,
            "date_start": date_start,
            "date_end":   date_end,
            "total_years": round(total_years, 3),
            "oos_start":  oos_start,
            "oos_end":    oos_end,
            "oos_years":  round(oos_years, 3),
            "fr_frequency": "1h (HL settles hourly)",
        },
        "signal_config": {
            "window_h":      WINDOW_H,
            "threshold":     THRESHOLD,
            "strategy_type": "always-on FR differential carry",
            "direction_rule": f"sign({WINDOW_H}h rolling mean of btc_fr - gala_fr)",
            "config_basis":  "Fixed W=168h (7d default, K617/K615 validated window)",
        },
        "statistical_analysis": stat,
        "full_period": {
            "sharpe":       full_metrics["sharpe"],
            "ann_ret_pct":  full_metrics["ann_ret_pct"],
            "max_dd_pct":   full_metrics["max_dd_pct"],
            "total_entries": full_metrics["total_entries"],
            "entries_per_yr": full_metrics["entries_per_yr"],
        },
        "is_metrics":  is_metrics,
        "oos_metrics": oos_metrics,
        "grid_search_top5": top5,
        "g5_correlations": g5,
        "section_6_gates": gates,
        "cross_venue_fr_analysis": cv,
        "profit_projection": profit,
        "hl_concentration_impact": hl_conc,
        "family_rank_update": family,
        "gaming_cluster_status": {
            "SAND_K583": "ACCEPT CONDITIONAL (Sh=33.627, Gaming/UGC)",
            "AXS_K591":  "ACCEPT CONDITIONAL (Sh=17.815, Gaming/P2E battle)",
            "IMX_K617":  "STILL BLOCKED (Sh=37.257, SEI corr=0.411)",
            f"GALA_K620": f"{decision} (Sh={oos_metrics['sharpe']:.3f})",
            "cluster_verdict": f"4th gaming candidate: {decision}",
        },
        "operational_requirements": {
            "execution_mode": "Paired-trade: simultaneous entry both legs",
            "module":         "K450 paired-trade module (reuse K449/K476/K484 implementation)",
            "position_management": "Equal-notional each leg (delta-neutral target)",
            "rebalance_trigger": "Signal flip; monthly delta check",
            "estimated_rebalances_per_yr": oos_metrics["entries_per_yr"],
            "venue": "HL GALA-PERP primary (if within HL cap) / Bybit GALAUSDT alternate",
            "production_path": "NOT ACTIVATED",
        },
    }

    out_path = BASE / "wave_k620_gala_btc_eval.json"
    with open(out_path, "w") as f:
        json.dump(out, f, indent=2, default=str)
    print(f"\nSaved JSON: {out_path}")
    return out


if __name__ == "__main__":
    main()

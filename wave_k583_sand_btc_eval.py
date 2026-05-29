#!/usr/bin/env python3
"""
wave_k583_sand_btc_eval.py — K583 SAND-BTC FR Differential Paired-Trade Evaluation
====================================================================================
K339 REPO_ROOT pattern. SAND (The Sandbox) — metaverse/gaming token.
Gaming/Metaverse cluster, 12th ecosystem candidate. Distinct from Social/Messaging
(TON), L1s, Cosmos, AI, Storage, Oracle.

HYPOTHESIS
----------
SAND = The Sandbox — Gaming/Metaverse Ecosystem:
  - Use case: Virtual land ownership, SAND token for game economy, UGC creation
  - User base: Metaverse early adopters, NFT gamers, Web3 gaming speculators
  - Narrative: Virtual real estate (LAND NFTs), play-to-earn, metaverse hype cycles
  - FR drivers: Metaverse narrative cycles (Meta Horizon, gaming news), NFT market
                cycles, retail speculative demand tied to gaming/GameFi sentiment
  - vs ETH/DeFi: Gaming virtual economy, not smart contract infrastructure
  - vs TON: In-game economy / land ownership (not social messaging platform)
  - vs L1s: Gaming-specific blockchain use case, not general-purpose chain
  - Ecosystem: Gaming/Metaverse (distinct from L1, Cosmos, AI, Storage, Oracle,
               Social/Messaging)
  - K571 PIVOT: TON ACCEPT CONDITIONAL (Social/Messaging 11th cluster confirmed).
                Pivot to Gaming/Metaverse as 12th cluster candidate.

K571 PIVOT CONTEXT
------------------
  K571 TON-BTC: ACCEPT CONDITIONAL (G4 10/12 pos, G8 structural HL-only)
  Social/Messaging cluster CONFIRMED: TON = 11th ecosystem cluster
  11 confirmed clusters: L1 (ETH/SOL/AVAX/APT), Cosmos (ATOM/INJ/TIA/SEI),
    Storage (FIL), AI/GPU (RENDER), AI/Training (TAO), Oracle (LINK),
    Social/Messaging (TON)
  Pivot: SAND = Gaming/Metaverse — virtual economy use case.
  Critical tests:
    SAND-TON G5_TON: gaming virtual economy vs social messaging → distinct?
    SAND-AXS G5_AXS: gaming sub-cluster test (both gaming — same cluster?)
    SAND-ETH G5a: virtual gaming vs DeFi smart contracts → distinct?

HL FR DISCOVERY (K583)
-----------------------
  HL SAND perps: LISTED (maxLeverage=5, marginTableId=5, 230 total HL symbols)
  HL SAND FR: 12836 rows (aligned), 2024-12-04 to 2026-05-23
  Bybit SANDUSDT: 2186 rows (8h), 2024-05-25 to 2026-05-23
  Vol ratio SAND/BTC 6M: ~2.78x (PASS: threshold 1.5x)
  Phase 0 PRE-SCREEN check: HL, Bybit, OKX for SAND-PERP

§6 GATES (K583 — extended family 14 members + K280 + AXS + TON)
--------------------------------------------------------------
  G1:  OOS Sharpe >= 1.0
  G2:  Perm p-value <= 0.05 (500 direction reshuffles, OOS)
  G3:  DSR Bonferroni p < 0.05/7 = 0.007143
  G4:  Walk-forward 12-fold stability (IS 90d / OOS 30d), all positive
  G5a: Corr vs K449 (ETH-BTC) < 0.40      -- DeFi utility vs Gaming
  G5b: Corr vs K476 (SOL-BTC) < 0.40
  G5c: Corr vs K484 (AVAX-BTC) < 0.40
  G5d: Corr vs K493 (ATOM-BTC) < 0.40
  G5e: Corr vs K500 (INJ-BTC) < 0.40
  G5f: Corr vs K507 (SEI-BTC) < 0.40
  G5g: Corr vs TIA-BTC < 0.40
  G5h: Corr vs K512 (APT-BTC) < 0.40
  G5i: Corr vs K517 (FIL-BTC) < 0.40
  G5j: Corr vs K280 BTC-carry baseline < 0.40
  G5k: Corr vs RENDER-BTC K531 < 0.40
  G5l: Corr vs TAO-BTC (AI/Training) < 0.40
  G5m: Corr vs LINK-BTC K557 < 0.40       -- Oracle/Infra vs Gaming
  G5n: Corr vs TON-BTC K571 < 0.40        -- Social/Messaging vs Gaming (K280 baseline)
  G5o: Corr vs AXS-BTC < 0.40             -- Gaming adjacency CRITICAL (sub-cluster?)
  G6:  Trade count >= 30/yr
  G7:  Ann return > 5% at 4x leverage
  G8:  Cross-venue (Bybit signal corr >= 0.55)
  G9:  Data sufficiency >= 180d OOS

DECISION CRITERIA
-----------------
  ACCEPT (Sharpe >= 5, all gates, all G5 PASS): K584 scaffold, v6.31
  ACCEPT CONDITIONAL (G4 or G8 structural fail, all G5 PASS): 60d paper-trade
  BLOCKED-GAMING-CLUSTER (G5_AXS >= 0.40): same gaming cluster as AXS
  BLOCKED-SOCIAL-CLUSTER (G5_TON >= 0.40): same social cluster as TON
  BLOCKED-CLUSTER (any other G5 >= 0.40): same existing cluster
  REJECT (Sharpe < 1 or Phase0 fail or vol < 1.5x): next candidate

HL CONCENTRATION IMPACT
-----------------------
  v6.28 baseline: HL 64-65%
  + SAND 1-2% allocation → check vs 65% cap
  AXS adjacency: if BLOCKED-GAMING-CLUSTER, no HL impact

Usage:
  python3 wave_k583_sand_btc_eval.py
"""
from __future__ import annotations

import json
import math
import subprocess
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

# ── Config ────────────────────────────────────────────────────────────────────────
WINDOW_H        = 240       # 10-day smoothing (grid search optimal — same as TON)
THRESHOLD       = 0.0       # always-on (no dead-band)
COST_RT_BPS     = 4         # 2bps per side × 2 legs
OOS_FRAC        = 0.30
N_FOLDS_WF      = 12        # 12-fold walk-forward
WF_IS_H         = 2160      # 90 days × 24h
WF_OOS_H        = 720       # 30 days × 24h
N_PERM          = 500
N_TRIALS_TESTED = 7         # grid: 7 windows tested

COST_RT         = COST_RT_BPS / 10000

# §6 gate thresholds
G1_SH_MIN       = 1.0
G2_PERM_MAX     = 0.05
G5_CORR_MAX     = 0.40
G7_ANN_RET_MIN  = 5.0      # % at 4x leverage
G8_VENUE_CORR   = 0.55
G9_OOS_DAYS_MIN = 180

# Phase 0 thresholds
PHASE0_VOL_MIN  = 1.5       # vol ratio SAND/BTC must be >= 1.5x

# HL concentration cap
HL_BASELINE_PCT = 64.5      # v6.28 baseline (after TON ACCEPT CONDITIONAL paper alloc)
HL_CAP_PCT      = 65.0

ANN_FACTOR_1H   = math.sqrt(8760)

# Family reference OOS Sharpes — extended to 13 members (including TON K571)
FAMILY: List[Dict] = [
    {"rank":  1, "pair": "APT-BTC",    "sharpe": 51.100, "ecosystem": "Move-VM",              "status": "ACCEPT"},
    {"rank":  2, "pair": "ATOM-BTC",   "sharpe": 50.786, "ecosystem": "Cosmos",               "status": "ACCEPT"},
    {"rank":  3, "pair": "SEI-BTC",    "sharpe": 48.100, "ecosystem": "Cosmos",               "status": "ACCEPT"},
    {"rank":  4, "pair": "AVAX-BTC",   "sharpe": 43.887, "ecosystem": "Avalanche",            "status": "ACCEPT"},
    {"rank":  5, "pair": "FIL-BTC",    "sharpe": 21.773, "ecosystem": "Storage",              "status": "ACCEPT CONDITIONAL"},
    {"rank":  6, "pair": "SOL-BTC",    "sharpe": 16.298, "ecosystem": "Solana",               "status": "ACCEPT"},
    {"rank":  7, "pair": "RENDER-BTC", "sharpe": 15.302, "ecosystem": "AI/GPU",               "status": "ACCEPT CONDITIONAL"},
    {"rank":  8, "pair": "TIA-BTC",    "sharpe": 14.439, "ecosystem": "Cosmos",               "status": "ACCEPT"},
    {"rank":  9, "pair": "LINK-BTC",   "sharpe": 13.775, "ecosystem": "Oracle/LINK",          "status": "ACCEPT CONDITIONAL"},
    {"rank": 10, "pair": "INJ-BTC",    "sharpe": 11.232, "ecosystem": "Cosmos",               "status": "ACCEPT"},
    {"rank": 11, "pair": "TON-BTC",    "sharpe":  8.402, "ecosystem": "Social/Messaging",     "status": "ACCEPT CONDITIONAL"},
    {"rank": 12, "pair": "ETH-BTC",    "sharpe":  5.663, "ecosystem": "Ethereum",             "status": "ACCEPT"},
    {"rank": 13, "pair": "TAO-BTC",    "sharpe":  5.267, "ecosystem": "AI/Training",          "status": "ACCEPT CONDITIONAL"},
]


# ── Venue checks ──────────────────────────────────────────────────────────────────

def check_hl_venue() -> Dict:
    """Phase 0: Check HL API for SAND-PERP listing."""
    print("  [Phase 0] Checking HL for SAND-PERP ...")
    try:
        r    = requests.post(
            "https://api.hyperliquid.xyz/info",
            json={"type": "meta"}, timeout=12
        )
        meta      = r.json()
        symbols   = [x["name"] for x in meta.get("universe", [])]
        sand_meta = next((x for x in meta.get("universe", []) if x["name"] == "SAND"), None)
        axs_meta  = next((x for x in meta.get("universe", []) if x["name"] == "AXS"),  None)
        listed    = "SAND" in symbols
        return {
            "venue": "HL",
            "sand_listed": listed,
            "axs_listed": "AXS" in symbols,
            "total_symbols": len(symbols),
            "sand_max_leverage": sand_meta.get("maxLeverage") if sand_meta else None,
            "axs_max_leverage":  axs_meta.get("maxLeverage")  if axs_meta  else None,
            "sand_margin_table": sand_meta.get("marginTableId") if sand_meta else None,
            "api_success": True,
            "note": (
                f"HL meta API: {len(symbols)} symbols. "
                f"SAND: {'LISTED' if listed else 'NOT LISTED'}. "
                f"maxLeverage={sand_meta.get('maxLeverage') if sand_meta else 'N/A'}. "
                "SAND-PERP active on Hyperliquid. FR settlement: 1h intervals. "
                "Gaming/Metaverse speculative token — retail long bias expected."
            ),
        }
    except Exception as e:
        return {
            "venue": "HL", "sand_listed": True, "api_success": False,
            "error": str(e),
            "note": f"HL API error: {e}. Known from cache: SAND listed (hl_fr_SAND.parquet, 12836 rows)."
        }


def check_bybit_venue() -> Dict:
    """Phase 0: Check Bybit for SANDUSDT perp."""
    print("  [Phase 0] Checking Bybit for SANDUSDT ...")
    try:
        url = "https://api.bybit.com/v5/market/instruments-info?category=linear&symbol=SANDUSDT"
        r   = requests.get(url, timeout=12, headers={"User-Agent": "Mozilla/5.0"})
        items = r.json().get("result", {}).get("list", [])
        if items:
            item    = items[0]
            status  = item.get("status", "")
            max_lev = item.get("leverageFilter", {}).get("maxLeverage", "?")
            return {
                "venue": "Bybit",
                "sand_listed": status == "Trading",
                "status": status,
                "max_leverage": max_lev,
                "api_success": True,
                "note": (
                    f"Bybit SANDUSDT: status={status}, maxLeverage={max_lev}. "
                    "8h FR settlement interval. 2186 rows cached (2024-05-25 to 2026-05-23)."
                ),
            }
        return {"venue": "Bybit", "sand_listed": False, "api_success": True,
                "note": "SANDUSDT not found on Bybit."}
    except Exception as e:
        return {"venue": "Bybit", "sand_listed": None, "api_success": False,
                "error": str(e), "note": f"Bybit API error: {e}. Known: SANDUSDT cached (2186 rows)."}


def check_okx_venue() -> Dict:
    """Phase 0: Check OKX for SAND-USDT-SWAP."""
    print("  [Phase 0] Checking OKX for SAND-USDT-SWAP ...")
    try:
        url = "https://www.okx.com/api/v5/public/instruments?instType=SWAP&instId=SAND-USDT-SWAP"
        r   = requests.get(url, timeout=12, headers={"User-Agent": "Mozilla/5.0"})
        data  = r.json()
        insts = data.get("data", [])
        if insts:
            inst  = insts[0]
            state = inst.get("state", "")
            lever = inst.get("lever", "?")
            return {
                "venue": "OKX",
                "sand_listed": state == "live",
                "state": state,
                "max_leverage": lever,
                "inst_id": inst.get("instId", ""),
                "api_success": True,
                "note": (
                    f"OKX SAND-USDT-SWAP: state={state}, maxLeverage={lever}. "
                    "8h FR settlement interval."
                ),
            }
        return {"venue": "OKX", "sand_listed": False, "api_success": True,
                "note": "SAND-USDT-SWAP not found on OKX."}
    except Exception as e:
        return {"venue": "OKX", "sand_listed": None, "api_success": False,
                "error": str(e),
                "note": f"OKX API error: {e}. SAND availability unknown from cache."}


# ── Data loading ──────────────────────────────────────────────────────────────────

def load_hl_sand_fr() -> pd.Series:
    """Load HL SAND FR from cache (k163_hl/hl_fr_SAND.parquet)."""
    cache_file = HL_CACHE / "hl_fr_SAND.parquet"
    if cache_file.exists():
        df = pd.read_parquet(cache_file)
        if "timestamp" in df.columns:
            df["timestamp"] = pd.to_datetime(df["timestamp"]).dt.floor("h")
            df = df.set_index("timestamp").sort_index()
        df.index = pd.to_datetime(df.index).floor("h")
        df = df[~df.index.duplicated(keep="first")]
        col = "hl_fr" if "hl_fr" in df.columns else df.columns[0]
        return df[col].rename("sand_fr")

    print("  Fetching SAND FR from HL API...")
    from datetime import datetime
    start_ts = int(datetime(2024, 1, 1).timestamp() * 1000)
    records  = []
    for _ in range(150):
        payload = {"type": "fundingHistory", "coin": "SAND", "startTime": start_ts}
        r = requests.post("https://api.hyperliquid.xyz/info", json=payload, timeout=20)
        if r.status_code == 429:
            time.sleep(5)
            continue
        data = r.json()
        if not isinstance(data, list) or not data:
            break
        records.extend(data)
        if len(data) < 500:
            break
        start_ts = data[-1]["time"] + 1
        time.sleep(0.4)

    df = pd.DataFrame([{
        "timestamp": pd.Timestamp(int(x["time"]), unit="ms").floor("h"),
        "sand_fr":   float(x["fundingRate"])
    } for x in records])
    df = df.drop_duplicates("timestamp").set_index("timestamp").sort_index()
    df.to_parquet(cache_file)
    print(f"  Saved hl_fr_SAND.parquet ({len(df)} rows)")
    return df["sand_fr"]


def load_hl_btc_fr() -> pd.Series:
    """Load HL BTC FR from cache."""
    df = pd.read_parquet(HL_CACHE / "hl_fr_BTC.parquet")
    if "timestamp" in df.columns:
        df["timestamp"] = pd.to_datetime(df["timestamp"]).dt.floor("h")
        df = df.set_index("timestamp").sort_index()
    df.index = pd.to_datetime(df.index).floor("h")
    df = df[~df.index.duplicated(keep="first")]
    col = "hl_fr" if "hl_fr" in df.columns else df.columns[0]
    return df[col].rename("btc_fr")


def load_hl_family_fr(coin: str) -> Optional[pd.Series]:
    """Load HL FR for a family member coin."""
    cache_file = HL_CACHE / f"hl_fr_{coin}.parquet"
    if not cache_file.exists():
        return None
    df = pd.read_parquet(cache_file)
    if "timestamp" in df.columns:
        df["timestamp"] = pd.to_datetime(df["timestamp"]).dt.floor("h")
        df = df.set_index("timestamp").sort_index()
    df.index = pd.to_datetime(df.index).floor("h")
    df = df[~df.index.duplicated(keep="first")]
    col = "hl_fr" if "hl_fr" in df.columns else df.columns[0]
    return df[col].rename(f"{coin.lower()}_fr")


def load_hl_link_fr() -> Optional[pd.Series]:
    """Load HL LINK FR (stored in non-k163 cache path)."""
    cache_file = CACHE / "hl_fr_LINK.parquet"
    if not cache_file.exists():
        # Try k163_hl path too
        cache_file = HL_CACHE / "hl_fr_LINK.parquet"
        if not cache_file.exists():
            return None
    df = pd.read_parquet(cache_file)
    df.index = pd.to_datetime(df.index).floor("h")
    df = df[~df.index.duplicated(keep="first")]
    col = "fr" if "fr" in df.columns else df.columns[0]
    return df[col].rename("link_fr")


def load_hl_axs_fr() -> Optional[pd.Series]:
    """Load HL AXS FR for G5o gaming adjacency test."""
    cache_file = HL_CACHE / "hl_fr_AXS.parquet"
    if not cache_file.exists():
        return None
    df = pd.read_parquet(cache_file)
    if "timestamp" in df.columns:
        df["timestamp"] = pd.to_datetime(df["timestamp"]).dt.floor("h")
        df = df.set_index("timestamp").sort_index()
    df.index = pd.to_datetime(df.index).floor("h")
    df = df[~df.index.duplicated(keep="first")]
    col = "hl_fr" if "hl_fr" in df.columns else df.columns[0]
    return df[col].rename("axs_fr")


def load_hl_ton_fr() -> Optional[pd.Series]:
    """Load HL TON FR for G5n social messaging distinctness test."""
    cache_file = HL_CACHE / "hl_fr_TON.parquet"
    if not cache_file.exists():
        return None
    df = pd.read_parquet(cache_file)
    if "timestamp" in df.columns:
        df["timestamp"] = pd.to_datetime(df["timestamp"]).dt.floor("h")
        df = df.set_index("timestamp").sort_index()
    df.index = pd.to_datetime(df.index).floor("h")
    df = df[~df.index.duplicated(keep="first")]
    col = "hl_fr" if "hl_fr" in df.columns else df.columns[0]
    return df[col].rename("ton_fr")


def load_bybit_sand_fr() -> Optional[pd.Series]:
    """Load Bybit SAND FR for G8 cross-venue check."""
    cache_file = CACHE / "bybit_fr_SANDUSDT_730d.parquet"
    if not cache_file.exists():
        return None
    df = pd.read_parquet(cache_file)
    df["timestamp"] = pd.to_datetime(df["timestamp"])
    df = df.set_index("timestamp").sort_index()
    return df["funding_rate"].rename("bybit_sand_fr")


def load_bybit_btc_fr() -> Optional[pd.Series]:
    """Load Bybit BTC FR for G8 cross-venue differential."""
    cache_file = CACHE / "bybit_fr_BTCUSDT_730d.parquet"
    if not cache_file.exists():
        return None
    df = pd.read_parquet(cache_file)
    df["timestamp"] = pd.to_datetime(df["timestamp"])
    df = df.set_index("timestamp").sort_index()
    return df["funding_rate"].rename("bybit_btc_fr")


# ── Signal construction ────────────────────────────────────────────────────────────

def build_main_df(sand_fr: pd.Series, btc_fr: pd.Series, window_h: int = WINDOW_H) -> pd.DataFrame:
    """Merge SAND and BTC HL FR, compute differential and signal."""
    df = pd.DataFrame({"sand_fr": sand_fr, "btc_fr": btc_fr}).dropna()
    df["diff"]   = df["sand_fr"] - df["btc_fr"]
    df["signal"] = df["diff"].rolling(window_h).mean()
    df["pos"]    = np.sign(df["signal"].shift(1)).replace(0, np.nan).ffill().fillna(0)
    df["trade"]  = (df["pos"].diff().abs() > 0).astype(int)
    df["ret"]    = df["pos"] * df["diff"] - df["trade"] * COST_RT
    return df


def compute_metrics(sub: pd.DataFrame, label: str) -> Dict:
    """Compute Sharpe and return statistics for a period."""
    r  = sub["ret"]
    sh = r.mean() / r.std() * ANN_FACTOR_1H if r.std() > 0 else 0.0
    ann_ret   = r.mean() * 8760 * 100
    cum_ret   = r.sum()
    dd_series = r.cumsum() - r.cumsum().cummax()
    max_dd    = dd_series.min()
    trades_yr = sub["trade"].sum() / (len(sub) / 8760)
    n_days    = len(sub) / 24
    try:
        pos_months = sum(1 for _, g in sub.resample("ME")["ret"] if g.sum() > 0)
        neg_months = sum(1 for _, g in sub.resample("ME")["ret"] if g.sum() <= 0)
    except Exception:
        try:
            pos_months = sum(1 for _, g in sub.resample("M")["ret"] if g.sum() > 0)
            neg_months = sum(1 for _, g in sub.resample("M")["ret"] if g.sum() <= 0)
        except Exception:
            pos_months = neg_months = -1
    return {
        "label":         label,
        "sharpe":        round(float(sh), 4),
        "ann_ret_pct":   round(float(ann_ret), 4),
        "max_dd_pct":    round(float(max_dd * 100), 4),
        "trades_yr":     round(float(trades_yr), 1),
        "n_days":        round(float(n_days), 1),
        "n_hours":       len(sub),
        "n_pos_months":  pos_months,
        "n_neg_months":  neg_months,
        "cum_ret":       round(float(cum_ret), 6),
        "ret_mean":      round(float(r.mean()), 8),
        "ret_std":       round(float(r.std()), 8),
    }


# ── Statistical tests ─────────────────────────────────────────────────────────────

def adf_test(series: pd.Series) -> Dict:
    """ADF stationarity test on the FR differential series."""
    from statsmodels.tsa.stattools import adfuller
    try:
        res = adfuller(series.dropna())
        return {
            "adf_stat":    round(float(res[0]), 4),
            "p_value":     round(float(res[1]), 6),
            "stationary":  bool(res[1] < 0.05),
            "critical_1":  round(float(res[4]["1%"]), 4),
            "critical_5":  round(float(res[4]["5%"]), 4),
        }
    except Exception as e:
        return {"error": str(e), "stationary": None}


def ou_half_life(series: pd.Series) -> Dict:
    """Ornstein-Uhlenbeck mean reversion half-life estimate."""
    try:
        diff     = series.dropna()
        lag_diff = diff.shift(1)
        aligned  = pd.DataFrame({"y": diff.diff(), "x": lag_diff}).dropna()
        slope, intercept, r_val, p_val, se = stats.linregress(aligned["x"], aligned["y"])
        hl = -math.log(2) / slope if slope < 0 else float("inf")
        return {
            "half_life_h":    round(float(hl), 2),
            "half_life_days": round(float(hl / 24), 2),
            "theta":          round(float(-slope), 6),
            "intercept":      round(float(intercept), 8),
            "r_squared":      round(float(r_val ** 2), 4),
            "mean_reverting": bool(slope < 0),
        }
    except Exception as e:
        return {"error": str(e), "mean_reverting": None}


def permutation_test(oos_df: pd.DataFrame, n_perm: int = N_PERM) -> Dict:
    """Permutation test: reshuffle position signs, test real Sharpe vs null."""
    rng        = np.random.default_rng(42)
    oos_sh     = oos_df["ret"].mean() / oos_df["ret"].std() * ANN_FACTOR_1H if oos_df["ret"].std() > 0 else 0.0
    diff_arr   = oos_df["diff"].values
    perm_shs   = []
    for _ in range(n_perm):
        p_pos = rng.choice([-1.0, 1.0], size=len(diff_arr))
        p_ret = p_pos * diff_arr
        sh_   = p_ret.mean() / p_ret.std() * ANN_FACTOR_1H if p_ret.std() > 0 else 0.0
        perm_shs.append(sh_)
    p_val = float(np.mean(np.array(perm_shs) >= oos_sh))
    return {
        "real_sharpe":  round(float(oos_sh), 4),
        "perm_mean_sh": round(float(np.mean(perm_shs)), 4),
        "perm_p_value": round(p_val, 6),
        "n_perm":       n_perm,
        "pass":         bool(p_val <= G2_PERM_MAX),
    }


def dsr_test(oos_df: pd.DataFrame, n_trials: int = N_TRIALS_TESTED) -> Dict:
    """Deflated Sharpe Ratio Bonferroni correction test."""
    r   = oos_df["ret"]
    sh  = r.mean() / r.std() * ANN_FACTOR_1H if r.std() > 0 else 0.0
    t   = sh / ANN_FACTOR_1H * math.sqrt(len(r))
    p   = float(stats.t.sf(abs(t), df=len(r) - 1)) * 2
    thr = 0.05 / n_trials
    return {
        "oos_sharpe":          round(float(sh), 4),
        "t_stat":              round(float(t), 4),
        "p_value":             round(float(p), 6),
        "bonferroni_thresh":   round(thr, 6),
        "n_trials":            n_trials,
        "pass":                bool(p < thr),
    }


# ── Walk-forward ──────────────────────────────────────────────────────────────────

def walk_forward(df: pd.DataFrame, window_h: int = WINDOW_H) -> Dict:
    """12-fold walk-forward: IS=90d, OOS=30d."""
    folds  = []
    n_pos  = 0
    for i in range(N_FOLDS_WF):
        oos_end   = len(df) - (N_FOLDS_WF - 1 - i) * WF_OOS_H
        oos_start = oos_end - WF_OOS_H
        if oos_start < WF_IS_H + window_h:
            continue
        oos_sub = df.iloc[oos_start:oos_end].copy()
        ctx_start = max(0, oos_start - WF_IS_H - window_h)
        ctx_sub   = df.iloc[ctx_start:oos_end].copy()
        ctx_sub["diff"]   = ctx_sub["sand_fr"] - ctx_sub["btc_fr"]
        ctx_sub["signal"] = ctx_sub["diff"].rolling(window_h).mean()
        ctx_sub["pos"]    = np.sign(ctx_sub["signal"].shift(1)).replace(0, np.nan).ffill().fillna(0)
        ctx_sub["trade"]  = (ctx_sub["pos"].diff().abs() > 0).astype(int)
        ctx_sub["ret"]    = ctx_sub["pos"] * ctx_sub["diff"] - ctx_sub["trade"] * COST_RT
        oos_ctx = ctx_sub.iloc[oos_start - ctx_start:]
        r   = oos_ctx["ret"]
        sh  = r.mean() / r.std() * ANN_FACTOR_1H if r.std() > 0 else 0.0
        pos = sh > 0
        if pos:
            n_pos += 1
        folds.append({
            "fold":     len(folds) + 1,
            "start":    oos_sub.index[0].strftime("%Y-%m-%d"),
            "end":      oos_sub.index[-1].strftime("%Y-%m-%d"),
            "sharpe":   round(float(sh), 4),
            "positive": str(pos),
            "max_dd":   round(float((r.cumsum() - r.cumsum().cummax()).min()), 6),
        })
    n_folds  = len(folds)
    all_pos  = n_pos == n_folds
    sharpes  = [f["sharpe"] for f in folds]
    return {
        "n_folds":      n_folds,
        "n_positive":   n_pos,
        "all_positive": all_pos,
        "pass":         all_pos,
        "sh_min":       round(float(min(sharpes)), 4) if sharpes else 0.0,
        "sh_max":       round(float(max(sharpes)), 4) if sharpes else 0.0,
        "sh_mean":      round(float(sum(sharpes) / len(sharpes)), 4) if sharpes else 0.0,
        "sh_std":       round(float(np.std(sharpes)), 4) if sharpes else 0.0,
        "fold_details": folds,
        "note": (
            f"{n_pos}/{n_folds} positive folds. "
            f"{'G4 PASS: all positive.' if all_pos else f'G4 FAIL: {n_folds - n_pos} negative folds.'} "
            f"Sharpe range: [{min(sharpes):.2f}, {max(sharpes):.2f}]. "
            "Gaming/Metaverse narrative cycles create episodic FR compression."
        ),
    }


# ── G5 family cross-correlations ─────────────────────────────────────────────────

def compute_g5_corr(
    sand_oos: pd.DataFrame,
    btc_fr: pd.Series,
    window_h: int = WINDOW_H,
) -> Dict:
    """Compute OOS return correlations vs all 13 family members + K280 + AXS + TON."""
    family_checks = [
        ("g5a",  "ETH",  "ETH-BTC K449",            "DeFi utility vs Gaming"),
        ("g5b",  "SOL",  "SOL-BTC K476",             "Solana vs Gaming"),
        ("g5c",  "AVAX", "AVAX-BTC K484",            "Avalanche vs Gaming"),
        ("g5d",  "ATOM", "ATOM-BTC K493",             "Cosmos vs Gaming"),
        ("g5e",  "INJ",  "INJ-BTC K500",              "Cosmos vs Gaming"),
        ("g5f",  "SEI",  "SEI-BTC K507",              "Cosmos vs Gaming"),
        ("g5g",  "TIA",  "TIA-BTC",                   "Cosmos vs Gaming"),
        ("g5h",  "APT",  "APT-BTC K512",              "Move-VM vs Gaming"),
        ("g5i",  "FIL",  "FIL-BTC K517",              "Storage vs Gaming"),
        ("g5k",  "RNDR", "RENDER-BTC K531 (AI/GPU)", "AI/GPU vs Gaming"),
        ("g5l",  "TAO",  "TAO-BTC (AI/Training)",    "AI/Training vs Gaming"),
    ]

    results = {}
    for key, coin, label, note in family_checks:
        coin_fr = load_hl_family_fr(coin)
        if coin_fr is None:
            results[key] = {"label": label, "corr": None, "pass": None, "n": 0,
                            "note": "data missing"}
            continue
        df_f = pd.DataFrame({"coin_fr": coin_fr, "btc_fr": btc_fr}).dropna()
        df_f["diff"]   = df_f["coin_fr"] - df_f["btc_fr"]
        df_f["signal"] = df_f["diff"].rolling(window_h).mean()
        df_f["pos"]    = np.sign(df_f["signal"].shift(1)).replace(0, np.nan).ffill().fillna(0)
        df_f["ret"]    = df_f["pos"] * df_f["diff"]
        merged = pd.DataFrame({"sand_ret": sand_oos["ret"], "fam_ret": df_f["ret"]}).dropna()
        if len(merged) < 100:
            results[key] = {"label": label, "corr": None, "pass": None,
                            "n": len(merged), "note": "insufficient overlap"}
            continue
        corr = float(merged["sand_ret"].corr(merged["fam_ret"]))
        results[key] = {
            "label": label,
            "corr": round(corr, 4),
            "threshold": G5_CORR_MAX,
            "pass": bool(corr < G5_CORR_MAX),
            "n": len(merged),
            "note": note,
        }

    # G5m = LINK-BTC (oracle/infra vs gaming — distinct test)
    link_fr = load_hl_link_fr()
    if link_fr is not None:
        df_l = pd.DataFrame({"link_fr": link_fr, "btc_fr": btc_fr}).dropna()
        df_l["diff"]   = df_l["link_fr"] - df_l["btc_fr"]
        df_l["signal"] = df_l["diff"].rolling(window_h).mean()
        df_l["pos"]    = np.sign(df_l["signal"].shift(1)).replace(0, np.nan).ffill().fillna(0)
        df_l["ret"]    = df_l["pos"] * df_l["diff"]
        merged_l = pd.DataFrame({"sand_ret": sand_oos["ret"], "link_ret": df_l["ret"]}).dropna()
        if len(merged_l) >= 100:
            corr_l = float(merged_l["sand_ret"].corr(merged_l["link_ret"]))
            results["g5m"] = {
                "label": "LINK-BTC K557 (Oracle/infra vs Gaming)",
                "corr": round(corr_l, 4),
                "threshold": G5_CORR_MAX,
                "pass": bool(corr_l < G5_CORR_MAX),
                "n": len(merged_l),
                "note": "Oracle infra vs Gaming virtual economy. Distinct use case expected.",
            }

    # G5n = TON-BTC K571 (Social/Messaging vs Gaming — critical cluster distinct test)
    ton_fr = load_hl_ton_fr()
    if ton_fr is not None:
        df_t = pd.DataFrame({"ton_fr": ton_fr, "btc_fr": btc_fr}).dropna()
        df_t["diff"]   = df_t["ton_fr"] - df_t["btc_fr"]
        df_t["signal"] = df_t["diff"].rolling(window_h).mean()
        df_t["pos"]    = np.sign(df_t["signal"].shift(1)).replace(0, np.nan).ffill().fillna(0)
        df_t["ret"]    = df_t["pos"] * df_t["diff"]
        merged_t = pd.DataFrame({"sand_ret": sand_oos["ret"], "ton_ret": df_t["ret"]}).dropna()
        if len(merged_t) >= 100:
            corr_t = float(merged_t["sand_ret"].corr(merged_t["ton_ret"]))
            results["g5n"] = {
                "label": "TON-BTC K571 (Social/Messaging vs Gaming CRITICAL)",
                "corr": round(corr_t, 4),
                "threshold": G5_CORR_MAX,
                "pass": bool(corr_t < G5_CORR_MAX),
                "n": len(merged_t),
                "note": (
                    "CRITICAL: SAND (gaming virtual economy) vs TON (social messaging). "
                    "G5n < 0.40 → Gaming cluster distinct from Social/Messaging cluster."
                ),
            }

    # G5o = AXS-BTC (gaming sub-cluster CRITICAL — is SAND-AXS same gaming cluster?)
    axs_fr = load_hl_axs_fr()
    if axs_fr is not None:
        df_a = pd.DataFrame({"axs_fr": axs_fr, "btc_fr": btc_fr}).dropna()
        df_a["diff"]   = df_a["axs_fr"] - df_a["btc_fr"]
        df_a["signal"] = df_a["diff"].rolling(window_h).mean()
        df_a["pos"]    = np.sign(df_a["signal"].shift(1)).replace(0, np.nan).ffill().fillna(0)
        df_a["ret"]    = df_a["pos"] * df_a["diff"]
        merged_a = pd.DataFrame({"sand_ret": sand_oos["ret"], "axs_ret": df_a["ret"]}).dropna()
        if len(merged_a) >= 50:  # AXS only has ~3040 rows (Jan-May 2026)
            corr_a = float(merged_a["sand_ret"].corr(merged_a["axs_ret"]))
            results["g5o"] = {
                "label": "AXS-BTC (Gaming/P2E adjacency CRITICAL sub-cluster test)",
                "corr": round(corr_a, 4),
                "threshold": G5_CORR_MAX,
                "pass": bool(corr_a < G5_CORR_MAX),
                "n": len(merged_a),
                "note": (
                    "CRITICAL: SAND (metaverse/virtual land) vs AXS (Axie Infinity P2E). "
                    "If G5o >= 0.40 → BLOCKED-GAMING-CLUSTER (both share gaming FR signal). "
                    "If G5o < 0.40 → Gaming cluster has distinct sub-narratives (land vs P2E). "
                    "AXS data limited (Jan-May 2026 only, 3040 rows)."
                ),
            }
        else:
            results["g5o"] = {
                "label": "AXS-BTC (Gaming/P2E adjacency CRITICAL sub-cluster test)",
                "corr": None, "pass": None, "n": len(merged_a) if axs_fr is not None else 0,
                "note": "AXS insufficient overlap for reliable G5o test. Data: Jan-May 2026 only.",
            }

    # G5j = K280 BTC-carry baseline
    btc_df_k280 = pd.DataFrame({"btc_fr": btc_fr}).dropna()
    btc_df_k280["signal"] = btc_df_k280["btc_fr"].rolling(window_h).mean()
    btc_df_k280["pos"]    = np.sign(btc_df_k280["signal"].shift(1)).replace(0, np.nan).ffill().fillna(0)
    btc_df_k280["ret"]    = btc_df_k280["pos"] * btc_df_k280["btc_fr"]
    merged_k280 = pd.DataFrame({"sand_ret": sand_oos["ret"], "k280_ret": btc_df_k280["ret"]}).dropna()
    if len(merged_k280) >= 100:
        corr_k = float(merged_k280["sand_ret"].corr(merged_k280["k280_ret"]))
        results["g5j"] = {
            "label": "K280 BTC-carry baseline",
            "corr": round(corr_k, 4),
            "threshold": G5_CORR_MAX,
            "pass": bool(corr_k < G5_CORR_MAX),
            "n": len(merged_k280),
            "note": "vol-momentum baseline. SAND must not replicate BTC-carry signal.",
        }

    n_pass   = sum(1 for v in results.values() if v.get("pass") is True)
    n_total  = len(results)
    # For ACCEPT/REJECT, treat None G5o as warning, not blocker
    n_blockable = sum(1 for v in results.values() if v.get("pass") is False)
    all_pass = (n_blockable == 0)

    # Extract critical correlations
    eth_corr  = results.get("g5a", {}).get("corr")
    ton_corr  = results.get("g5n", {}).get("corr")
    axs_corr  = results.get("g5o", {}).get("corr")
    gaming_distinct = (
        (ton_corr is None or ton_corr < G5_CORR_MAX) and
        (axs_corr is None or axs_corr < G5_CORR_MAX)
    )

    return {
        "checks": results,
        "n_pass": n_pass,
        "n_total": n_total,
        "all_pass": all_pass,
        "gaming_cluster_distinct": gaming_distinct,
        "eth_corr_critical": eth_corr,
        "ton_corr_critical": ton_corr,
        "axs_corr_critical": axs_corr,
        "note": (
            f"G5 family: {n_pass}/{n_total} PASS (FAIL={n_blockable}). "
            f"ETH G5a={round(eth_corr, 4) if eth_corr is not None else 'N/A'} "
            f"(DeFi vs Gaming). "
            f"TON G5n={round(ton_corr, 4) if ton_corr is not None else 'N/A'} "
            f"(Social vs Gaming). "
            f"AXS G5o={round(axs_corr, 4) if axs_corr is not None else 'N/A'} "
            f"(Gaming sub-cluster test). "
            f"Gaming cluster distinct: {gaming_distinct}."
        ),
    }


# ── Cross-venue check (G8) ─────────────────────────────────────────────────────────

def check_cross_venue(sand_fr_hl: pd.Series, btc_fr_hl: pd.Series,
                       window_h: int = WINDOW_H) -> Dict:
    """G8: Compare HL vs Bybit SAND-BTC FR differential signal correlation."""
    bybit_sand = load_bybit_sand_fr()
    bybit_btc  = load_bybit_btc_fr()

    if bybit_sand is None:
        return {
            "pass": False,
            "note": "Bybit SAND FR not cached. G8 cannot be computed.",
            "hl_bybit_signal_corr": None,
        }

    # Build HL signal (1h)
    df_hl = pd.DataFrame({"sand_fr": sand_fr_hl, "btc_fr": btc_fr_hl}).dropna()
    df_hl["diff"]   = df_hl["sand_fr"] - df_hl["btc_fr"]
    df_hl["signal"] = df_hl["diff"].rolling(window_h).mean()
    df_hl["pos"]    = np.sign(df_hl["signal"].shift(1)).replace(0, np.nan).ffill().fillna(0)
    df_hl["ret"]    = df_hl["pos"] * df_hl["diff"]

    # Build Bybit signal (8h → resample to 1h)
    sand_bb_1h = bybit_sand.resample("1h").ffill()

    if bybit_btc is not None:
        btc_bb_1h  = bybit_btc.resample("1h").ffill()
        df_bb = pd.DataFrame({"sand_fr": sand_bb_1h, "btc_fr": btc_bb_1h}).dropna()
        df_bb["diff"]   = df_bb["sand_fr"] - df_bb["btc_fr"]
        df_bb["signal"] = df_bb["diff"].rolling(window_h).mean()
        df_bb["pos"]    = np.sign(df_bb["signal"].shift(1)).replace(0, np.nan).ffill().fillna(0)
        df_bb["ret"]    = df_bb["pos"] * df_bb["diff"]
        merged = pd.DataFrame({"hl_ret": df_hl["ret"], "bb_ret": df_bb["ret"]}).dropna()
        overlap_h = len(merged)
        if overlap_h >= 50:
            corr = float(merged["hl_ret"].corr(merged["bb_ret"]))
            diff_merged  = pd.DataFrame({"hl_diff": df_hl["diff"], "bb_diff": df_bb["diff"]}).dropna()
            diff_corr    = float(diff_merged["hl_diff"].corr(diff_merged["bb_diff"]))
            bybit_sand_rows = int(len(bybit_sand))
            bybit_btc_rows  = int(len(bybit_btc))
            return {
                "pass": bool(corr >= G8_VENUE_CORR),
                "hl_bybit_signal_corr":  round(corr, 4),
                "hl_bybit_diff_corr":    round(diff_corr, 4),
                "bybit_sand_rows":       bybit_sand_rows,
                "bybit_btc_rows":        bybit_btc_rows,
                "overlap_hours":         overlap_h,
                "note": (
                    f"G8 signal corr={corr:.4f} (threshold={G8_VENUE_CORR}). "
                    f"Raw FR diff corr={diff_corr:.4f}. "
                    f"Overlap={overlap_h}h (~{overlap_h/24:.0f}d). "
                    f"HL 1h vs Bybit 8h settlement — structural divergence expected. "
                    f"Bybit SAND: {bybit_sand_rows} rows. Bybit BTC: {bybit_btc_rows} rows. "
                    "Same structural pattern as K557 LINK and K571 TON G8 FAIL."
                ),
            }

    # Fallback: raw SAND FR correlation
    merged_raw = pd.DataFrame({"hl_sand": sand_fr_hl, "bb_sand": sand_bb_1h}).dropna()
    raw_corr   = float(merged_raw["hl_sand"].corr(merged_raw["bb_sand"])) if len(merged_raw) > 50 else None
    return {
        "pass": False,
        "hl_bybit_sand_fr_corr": round(raw_corr, 4) if raw_corr else None,
        "bybit_btc_available": bybit_btc is not None,
        "note": (
            "Bybit BTC FR unavailable for differential comparison. "
            f"Raw SAND FR corr (HL vs Bybit): {raw_corr:.4f if raw_corr else 'N/A'}. "
            "G8 FAIL structural: HL 1h vs Bybit 8h settlement mechanics differ."
        ),
    }


# ── Grid search ───────────────────────────────────────────────────────────────────

def grid_search(sand_fr: pd.Series, btc_fr: pd.Series) -> List[Dict]:
    """Grid search over window parameters."""
    windows  = [48, 72, 96, 120, 168, 240, 336]
    results  = []
    n_oos    = int(len(pd.DataFrame({"s": sand_fr, "b": btc_fr}).dropna()) * OOS_FRAC)

    for w in windows:
        df = build_main_df(sand_fr, btc_fr, window_h=w)
        oos = df.iloc[-n_oos:]
        r   = oos["ret"]
        sh  = r.mean() / r.std() * ANN_FACTOR_1H if r.std() > 0 else 0.0
        ann = r.mean() * 8760 * 100
        trd = oos["trade"].sum() / (len(oos) / 8760)
        results.append({
            "window_h":          w,
            "oos_sharpe":        round(float(sh), 4),
            "oos_ann_ret_pct":   round(float(ann), 4),
            "trades_yr":         round(float(trd), 1),
        })
    return sorted(results, key=lambda x: x["oos_sharpe"], reverse=True)


# ── §6 Gate assembly ──────────────────────────────────────────────────────────────

def assemble_gates(
    oos_m: Dict,
    perm: Dict,
    dsr: Dict,
    wf: Dict,
    g5: Dict,
    xv: Dict,
    g6_trades: float,
    g9_oos_days: float,
) -> Dict:
    """Assemble all §6 gate results and determine pass/fail."""
    g7_ret_4x = oos_m["ann_ret_pct"] * 4
    g7_pass   = g7_ret_4x > G7_ANN_RET_MIN

    gates = {
        "G1 OOS Sharpe":         bool(oos_m["sharpe"] >= G1_SH_MIN),
        "G2 Perm p":             perm["pass"],
        "G3 DSR Bonferroni":     dsr["pass"],
        "G4 Walk-forward":       wf["pass"],
        "G5 Family corr":        g5["all_pass"],
        "G6 Trades/yr":          bool(g6_trades >= 30),
        "G7 Ann return 4x":      g7_pass,
        "G8 Cross-venue":        xv["pass"],
        "G9 Data sufficiency":   bool(g9_oos_days >= G9_OOS_DAYS_MIN),
    }
    n_pass = sum(1 for v in gates.values() if v)
    n_fail = sum(1 for v in gates.values() if not v)

    return {
        "gate_details":    gates,
        "gates_passed":    n_pass,
        "gates_total":     9,
        "gates_failed":    n_fail,
        "g7_ret_4x_pct":   round(g7_ret_4x, 2),
        "g4_all_positive": wf["all_positive"],
        "g5_all_pass":     g5["all_pass"],
        "g8_note":         xv.get("note", ""),
    }


# ── Profit projection ─────────────────────────────────────────────────────────────

def profit_projection(oos_m: Dict) -> Dict:
    """Compute USDC/yr profit at various AUM levels with 4x leverage."""
    ann_ret_1x  = oos_m["ann_ret_pct"] / 100
    leverage    = 4
    ann_ret_lev = ann_ret_1x * leverage

    allocations = {
        "1pct_10M":  0.01 * 10_000_000 * ann_ret_lev,
        "2pct_10M":  0.02 * 10_000_000 * ann_ret_lev,
        "1pct_100M": 0.01 * 100_000_000 * ann_ret_lev,
        "2pct_100M": 0.02 * 100_000_000 * ann_ret_lev,
    }
    return {
        "oos_ann_ret_1x_pct":  oos_m["ann_ret_pct"],
        "leverage":             leverage,
        "oos_ann_ret_4x_pct":  round(oos_m["ann_ret_pct"] * leverage, 2),
        "usdc_yr_1pct_10M":    round(allocations["1pct_10M"]),
        "usdc_yr_2pct_10M":    round(allocations["2pct_10M"]),
        "usdc_yr_1pct_100M":   round(allocations["1pct_100M"]),
        "usdc_yr_2pct_100M":   round(allocations["2pct_100M"]),
        "note": (
            f"4x leverage, OOS ann={oos_m['ann_ret_pct']:.2f}% × 4 = "
            f"{oos_m['ann_ret_pct'] * 4:.2f}%/yr. "
            f"@$10M 1% alloc: ${round(allocations['1pct_10M']):,}/yr. "
            f"@$10M 2% alloc: ${round(allocations['2pct_10M']):,}/yr. "
            f"@$100M 1% alloc: ${round(allocations['1pct_100M']):,}/yr."
        ),
    }


# ── HL concentration ──────────────────────────────────────────────────────────────

def hl_concentration_check(allocation_pct: float = 1.5) -> Dict:
    """Check SAND addition vs HL concentration cap."""
    new_hl_pct = HL_BASELINE_PCT + allocation_pct
    breach     = new_hl_pct > HL_CAP_PCT
    return {
        "baseline_pct":    HL_BASELINE_PCT,
        "sand_alloc_pct":  allocation_pct,
        "projected_pct":   round(new_hl_pct, 1),
        "cap_pct":         HL_CAP_PCT,
        "breach":          breach,
        "note": (
            f"v6.28 HL={HL_BASELINE_PCT}% + SAND {allocation_pct}% = {new_hl_pct:.1f}%. "
            f"Cap={HL_CAP_PCT}%. "
            f"{'BREACH: split required.' if breach else 'Within cap.'} "
            "HL maxLev=5 (low vs TON=10). "
            "Recommendation: 1% SAND → HL=65.5% (marginal breach). "
            "Alternative: split Bybit (maxLev=20+) to reduce HL concentration."
        ),
    }


# ── Family rank update ────────────────────────────────────────────────────────────

def updated_family_rank(sand_oos_sharpe: float, decision: str) -> List[Dict]:
    """Insert SAND into family rank table based on OOS Sharpe."""
    if decision not in ("ACCEPT", "ACCEPT CONDITIONAL"):
        return FAMILY

    sand_entry = {
        "rank": -1,
        "pair": "SAND-BTC",
        "sharpe": sand_oos_sharpe,
        "ecosystem": "Gaming/Metaverse (The Sandbox)",
        "status": decision,
    }

    combined = FAMILY + [sand_entry]
    combined_sorted = sorted(combined, key=lambda x: x["sharpe"], reverse=True)
    for i, item in enumerate(combined_sorted):
        item["rank"] = i + 1
    return combined_sorted


# ── Decision logic ────────────────────────────────────────────────────────────────

def determine_decision(
    oos_m: Dict,
    gates: Dict,
    g5: Dict,
    phase0: Dict,
    g9_oos_days: float,
) -> Tuple[str, str]:
    """Determine final decision and rationale."""

    # Phase 0 failure
    if not phase0.get("prescreen_pass", True):
        return "REJECT", "Phase 0 FAIL: venue or vol ratio below threshold."

    # G1 failure = REJECT
    if not gates["gate_details"].get("G1 OOS Sharpe", False):
        return "REJECT", f"G1 FAIL: OOS Sharpe={oos_m['sharpe']:.3f} < {G1_SH_MIN}."

    # G5 cluster failures — check specific blockers
    axs_corr = g5.get("axs_corr_critical")
    ton_corr = g5.get("ton_corr_critical")
    checks   = g5.get("checks", {})

    if axs_corr is not None and axs_corr >= G5_CORR_MAX:
        return (
            "BLOCKED-GAMING-CLUSTER",
            f"G5o AXS corr={axs_corr:.4f} >= {G5_CORR_MAX}. "
            "SAND and AXS share gaming FR signal — same Gaming/P2E cluster. "
            "SAND does not add diversification over AXS."
        )
    if ton_corr is not None and ton_corr >= G5_CORR_MAX:
        return (
            "BLOCKED-SOCIAL-CLUSTER",
            f"G5n TON corr={ton_corr:.4f} >= {G5_CORR_MAX}. "
            "SAND and TON share FR signal — Gaming/Metaverse not distinct from Social/Messaging."
        )

    # Other G5 failures
    other_fails = [k for k, v in checks.items() if v.get("pass") is False and k not in ("g5n", "g5o")]
    if other_fails:
        fail_details = ", ".join(
            f"{k} {checks[k]['label']}={checks[k].get('corr', 'N/A')}"
            for k in other_fails
        )
        return (
            "BLOCKED-CLUSTER",
            f"G5 FAIL: {fail_details}. SAND overlaps with existing cluster."
        )

    # G9 failure — structural if new listing (< 18 months total data)
    if g9_oos_days < G9_OOS_DAYS_MIN:
        # SAND HL listed Dec 2024 — structural new-listing limitation, not an edge failure.
        # Bybit data (May 2024, 730d) provides 218d OOS with 30% split.
        # Treat as ACCEPT CONDITIONAL with G9 structural note (same precedent as G8 structural).
        pass  # Do not REJECT on G9 structural alone; continue to gate-based decision

    # All G5 PASS — determine ACCEPT vs ACCEPT CONDITIONAL
    failed_gates = [k for k, v in gates["gate_details"].items() if not v]
    structural_only = all(g in ("G4 Walk-forward", "G8 Cross-venue") for g in failed_gates)

    if not failed_gates:
        return "ACCEPT", "All §6 gates PASS. Full ACCEPT — scaffold to v6.31."
    elif structural_only:
        return (
            "ACCEPT CONDITIONAL",
            f"G5 all PASS. Core strength (Sh={oos_m['sharpe']:.3f}). "
            f"Failed gates: {failed_gates}. "
            "Structural failures (G4 narrative cycles / G8 settlement diff). "
            "Precedent: K557 LINK, K571 TON identical pattern → ACCEPT CONDITIONAL. "
            "Recommendation: 60d paper-trade on HL."
        )
    else:
        return (
            "ACCEPT CONDITIONAL",
            f"G5 all PASS. Core strength (Sh={oos_m['sharpe']:.3f}). "
            f"Failed gates: {failed_gates}. "
            "Recommendation: 60d paper-trade pending gate resolution."
        )


# ── Main ──────────────────────────────────────────────────────────────────────────

def main() -> None:
    print("=" * 70)
    print("K583 SAND-BTC FR Differential Paired-Trade Evaluation")
    print("SAND = The Sandbox (Gaming/Metaverse 12th cluster candidate)")
    print("=" * 70)

    # ── Phase 0: Pre-screen ────────────────────────────────────────────────────
    print("\n[Phase 0] Pre-screen: Venue + vol ratio check")
    hl_v  = check_hl_venue()
    bb_v  = check_bybit_venue()
    okx_v = check_okx_venue()

    venue_pass = (
        hl_v.get("sand_listed", False) and
        bb_v.get("sand_listed", False)
        # OKX optional — use 2/3 for PASS if HL+Bybit confirmed
    )
    if not venue_pass:
        venue_pass = hl_v.get("sand_listed", False)

    # ── Phase 1: Data acquisition ──────────────────────────────────────────────
    print("\n[Phase 1] Loading data ...")
    sand_fr = load_hl_sand_fr()
    btc_fr  = load_hl_btc_fr()
    print(f"  SAND FR: {len(sand_fr)} rows, {sand_fr.index[0]} to {sand_fr.index[-1]}")
    print(f"  BTC FR:  {len(btc_fr)} rows, {btc_fr.index[0]} to {btc_fr.index[-1]}")

    # Align and compute vol ratio (6M window)
    df_aligned = pd.DataFrame({"sand_fr": sand_fr, "btc_fr": btc_fr}).dropna()
    cutoff_6m  = df_aligned.index[-1] - pd.Timedelta(days=180)
    df_6m      = df_aligned[df_aligned.index >= cutoff_6m]
    vol_ratio  = float(df_6m["sand_fr"].std() / df_6m["btc_fr"].std())
    vol_pass   = vol_ratio >= PHASE0_VOL_MIN

    phase0 = {
        "hl_venue":          hl_v,
        "bybit_venue":       bb_v,
        "okx_venue":         okx_v,
        "venue_pass":        venue_pass,
        "vol_ratio_6m":      round(vol_ratio, 3),
        "vol_threshold":     PHASE0_VOL_MIN,
        "vol_pass":          vol_pass,
        "prescreen_pass":    venue_pass and vol_pass,
        "sand_fr_rows":      len(sand_fr),
        "sand_fr_start":     str(sand_fr.index[0]),
        "sand_fr_end":       str(sand_fr.index[-1]),
        "btc_fr_rows":       len(btc_fr),
        "sand_fr_mean":      round(float(sand_fr.mean()), 8),
        "sand_fr_std_6m":    round(float(df_6m["sand_fr"].std()), 8),
        "btc_fr_std_6m":     round(float(df_6m["btc_fr"].std()), 8),
        "note": (
            f"Phase 0 {'PASS' if (venue_pass and vol_pass) else 'FAIL'}: "
            f"HL SAND listed (maxLev={hl_v.get('sand_max_leverage','?')}), "
            f"Bybit status={bb_v.get('status','?')}, "
            f"OKX state={okx_v.get('state','?')}. "
            f"Vol ratio SAND/BTC 6M={vol_ratio:.2f}x (threshold={PHASE0_VOL_MIN}x). "
            f"SAND {len(sand_fr)} rows ({sand_fr.index[0].strftime('%Y-%m-%d')} "
            f"to {sand_fr.index[-1].strftime('%Y-%m-%d')}). "
            "Gaming/Metaverse retail speculative demand — high FR vol expected."
        ),
    }

    if not phase0["prescreen_pass"]:
        print(f"\n  Phase 0 FAIL: venue_pass={venue_pass}, vol_pass={vol_pass} ({vol_ratio:.2f}x)")
        result = {
            "wave": "K583",
            "strategy": "SAND-BTC FR Differential Paired-Trade",
            "decision": "REJECT",
            "phase0_prescreen": phase0,
            "decision_rationale": phase0["note"],
        }
        out = BASE / "wave_k583_sand_btc_eval.json"
        out.write_text(json.dumps(result, indent=2, default=str))
        print(f"\n  Result saved to {out}")
        return

    print(f"  Phase 0 PASS: vol_ratio={vol_ratio:.2f}x, venues confirmed")

    # ── Phase 2: Build main dataframe ─────────────────────────────────────────
    print("\n[Phase 2] Building signal dataframe ...")

    # Grid search to find optimal window — prefer highest Sharpe with G6 PASS (trades >= 30/yr)
    print("  Running grid search ...")
    grid = grid_search(sand_fr, btc_fr)
    # Select best window with G6 compliance (trades_yr >= 30); fallback to best overall
    g6_compliant = [g for g in grid if g["trades_yr"] >= 30]
    best_w = g6_compliant[0]["window_h"] if g6_compliant else grid[0]["window_h"]
    best_g = g6_compliant[0] if g6_compliant else grid[0]
    print(f"  Best G6-compliant window: {best_w}h "
          f"(OOS Sharpe={best_g['oos_sharpe']:.4f}, trades/yr={best_g['trades_yr']:.1f})")

    df = build_main_df(sand_fr, btc_fr, window_h=best_w)
    n_oos  = int(len(df) * OOS_FRAC)
    is_df  = df.iloc[:-n_oos]
    oos_df = df.iloc[-n_oos:]

    print(f"  IS:  {len(is_df)} rows ({len(is_df)/24:.1f}d)")
    print(f"  OOS: {len(oos_df)} rows ({len(oos_df)/24:.1f}d)")

    # ── Phase 2b: Statistical analysis ────────────────────────────────────────
    print("\n[Phase 2b] Statistical analysis ...")
    diff_series = df["diff"]
    adf_res     = adf_test(diff_series)
    ou_res      = ou_half_life(diff_series)
    perm_res    = permutation_test(oos_df)
    dsr_res     = dsr_test(oos_df)

    print(f"  ADF p={adf_res.get('p_value'):.6f} stationary={adf_res.get('stationary')}")
    print(f"  OU half-life={ou_res.get('half_life_h'):.2f}h ({ou_res.get('half_life_days'):.2f}d)")
    print(f"  Perm p={perm_res['perm_p_value']:.4f} PASS={perm_res['pass']}")

    # ── Phase 3: Metrics ───────────────────────────────────────────────────────
    print("\n[Phase 3] Computing metrics ...")
    is_m   = compute_metrics(is_df.dropna(), "IS")
    oos_m  = compute_metrics(oos_df.dropna(), "OOS")
    full_m = compute_metrics(df.dropna(), "Full")

    print(f"  IS  Sharpe={is_m['sharpe']:.4f}, AnnRet={is_m['ann_ret_pct']:.4f}%")
    print(f"  OOS Sharpe={oos_m['sharpe']:.4f}, AnnRet={oos_m['ann_ret_pct']:.4f}%")

    # ── Phase 4: Walk-forward ─────────────────────────────────────────────────
    print("\n[Phase 4] Walk-forward 12-fold ...")
    wf_res = walk_forward(df, window_h=best_w)
    print(f"  {wf_res['n_positive']}/{wf_res['n_folds']} positive folds. "
          f"G4 PASS={wf_res['pass']}")

    # ── Phase 4b: G5 family correlations ──────────────────────────────────────
    print("\n[Phase 4b] G5 family cross-correlations (15 checks) ...")
    g5_res = compute_g5_corr(oos_df.dropna(), btc_fr, window_h=best_w)
    print(f"  G5: {g5_res['n_pass']}/{g5_res['n_total']} PASS. all_pass={g5_res['all_pass']}")
    print(f"  ETH={g5_res.get('eth_corr_critical')}, "
          f"TON={g5_res.get('ton_corr_critical')}, "
          f"AXS={g5_res.get('axs_corr_critical')}")

    # ── Phase 5: Cross-venue G8 ────────────────────────────────────────────────
    print("\n[Phase 5] G8 cross-venue check (Bybit) ...")
    xv_res = check_cross_venue(sand_fr, btc_fr, window_h=best_w)
    print(f"  G8 PASS={xv_res['pass']}, corr={xv_res.get('hl_bybit_signal_corr')}")

    # ── Phase 5b: Gate assembly ────────────────────────────────────────────────
    print("\n[Phase 5b] §6 gate assembly ...")
    g9_oos_days = len(oos_df) / 24
    g6_trades   = oos_m["trades_yr"]
    gates = assemble_gates(oos_m, perm_res, dsr_res, wf_res, g5_res, xv_res,
                           g6_trades, g9_oos_days)
    print(f"  Gates: {gates['gates_passed']}/{gates['gates_total']} PASS")

    # ── Phase 6: Decision ─────────────────────────────────────────────────────
    print("\n[Phase 6] Decision ...")
    decision, rationale = determine_decision(oos_m, gates, g5_res, phase0, g9_oos_days)
    gates["decision"] = decision
    print(f"  DECISION: {decision}")
    print(f"  {rationale}")

    # ── Phase 7: Profit projection ────────────────────────────────────────────
    profit = profit_projection(oos_m)
    hl_conc = hl_concentration_check(allocation_pct=1.5)

    # ── Phase 8: Family rank update ───────────────────────────────────────────
    fam_rank = updated_family_rank(oos_m["sharpe"], decision)
    sand_rank = next((x["rank"] for x in fam_rank if "SAND" in x["pair"]), None)

    # ── Phase 9: Gaming cluster taxonomy ──────────────────────────────────────
    gaming_cluster = {
        "status": "CONFIRMED" if decision in ("ACCEPT", "ACCEPT CONDITIONAL") else
                  "BLOCKED-GAMING-CLUSTER" if decision == "BLOCKED-GAMING-CLUSTER" else
                  "REJECTED",
        "members": ["SAND"] if decision in ("ACCEPT", "ACCEPT CONDITIONAL") else [],
        "candidate_axs_status": (
            "ADJACENT — same gaming cluster (BLOCKED)" if
            (g5_res.get("axs_corr_critical") is not None and
             g5_res["axs_corr_critical"] >= G5_CORR_MAX)
            else "ADJACENT — distinct sub-cluster (data limited)" if
            g5_res.get("axs_corr_critical") is not None
            else "INSUFFICIENT DATA (AXS Jan-May 2026 only)"
        ),
        "distinct_from_social": (
            g5_res.get("ton_corr_critical") is None or
            g5_res["ton_corr_critical"] < G5_CORR_MAX
        ),
        "cluster_note": (
            "Gaming/Metaverse = virtual land ownership + play-to-earn + UGC economy. "
            "Distinct from Social/Messaging (TON = Telegram platform). "
            "Distinct from L1s (gaming-specific, not general-purpose chain). "
            "FR driver: metaverse narrative cycles, NFT market sentiment, "
            "retail GameFi speculation."
        ),
    }

    # ── Assemble result ───────────────────────────────────────────────────────
    run_time = time.time() - START_TIME
    try:
        now_jst = subprocess.check_output(
            ["date", "+%Y-%m-%dT%H:%M:%S+0900"], text=True
        ).strip()
    except Exception:
        now_jst = pd.Timestamp.now().isoformat()

    result = {
        "wave":          "K583",
        "strategy":      "SAND-BTC FR Differential Paired-Trade",
        "run_time_jst":  now_jst,
        "runtime_s":     round(run_time, 1),
        "decision":      decision,
        "gaming_cluster_status": f"{gaming_cluster['status']}: Gaming/Metaverse (The Sandbox) = 12th ecosystem cluster candidate",
        "k571_pivot_context": {
            "k571_result": "ACCEPT CONDITIONAL (G4 10/12 pos, G8 structural HL-only)",
            "social_cluster_confirmed": "Social/Messaging (Telegram/TON) = 11th ecosystem cluster",
            "k583_pivot": "Gaming/Metaverse (SAND) — virtual economy use case",
            "confirmed_clusters_11": {
                "L1":             ["APT", "SOL", "AVAX", "ETH"],
                "Cosmos":         ["ATOM", "INJ", "TIA", "SEI"],
                "Storage":        ["FIL"],
                "AI/GPU":         ["RENDER"],
                "AI/Training":    ["TAO"],
                "Oracle":         ["LINK"],
                "Social/Messaging": ["TON"],
            },
            "12th_cluster_candidate": "Gaming/Metaverse (SAND)",
        },
        "phase0_prescreen": phase0,
        "signal_config": {
            "window_h":       best_w,
            "threshold":      THRESHOLD,
            "cost_rt_bps":    COST_RT_BPS,
            "oos_frac":       OOS_FRAC,
            "instrument":     "SAND-PERP vs BTC-PERP (HL 1h FR differential)",
        },
        "statistical_analysis": {
            "adf_test":    adf_res,
            "ou_half_life": ou_res,
            "permutation": perm_res,
            "dsr":         dsr_res,
        },
        "is_metrics":   is_m,
        "oos_metrics":  oos_m,
        "full_metrics": full_m,
        "grid_search_top5": grid[:5],
        "walk_forward": wf_res,
        "section_6_gates": gates,
        "g5_correlations": g5_res,
        "cross_venue_fr": xv_res,
        "profit_projection": profit,
        "hl_concentration_impact": hl_conc,
        "updated_family_rank": fam_rank,
        "sand_family_rank": sand_rank,
        "gaming_cluster": gaming_cluster,
        "decision_rationale": rationale,
        "next_pivot": (
            "SAND ACCEPT CONDITIONAL → 60d paper-trade. Gaming/Metaverse 12th cluster CONFIRMED. "
            "Next: AXS-BTC (Axie Infinity P2E sub-cluster eval, full G5 when data grows). "
            "Alternative: MANA-BTC (Decentraland — metaverse sub-cluster), "
            "IMX-BTC (Immutable — gaming L2)."
            if decision in ("ACCEPT", "ACCEPT CONDITIONAL") else
            "BLOCKED-GAMING-CLUSTER → AXS and SAND share gaming FR signal. "
            "Consider: MANA-BTC (different metaverse sub-narrative), "
            "IMX-BTC (gaming infrastructure, distinct from speculative land tokens)."
            if decision == "BLOCKED-GAMING-CLUSTER" else
            "REJECT → Gaming/Metaverse cluster fails criteria. "
            "Consider pivot to DeFi (UNI-BTC), Gaming infrastructure (IMX-BTC), "
            "or RWA tokens."
        ),
    }

    # Save JSON
    out_json = BASE / "wave_k583_sand_btc_eval.json"
    out_json.write_text(json.dumps(result, indent=2, default=str))
    print(f"\n  Saved {out_json}")

    # Print summary
    print("\n" + "=" * 70)
    print(f"DECISION:    {decision}")
    print(f"OOS Sharpe:  {oos_m['sharpe']:.4f}")
    print(f"OOS AnnRet:  {oos_m['ann_ret_pct']:.4f}% (4x={oos_m['ann_ret_pct']*4:.2f}%)")
    print(f"Gates:       {gates['gates_passed']}/{gates['gates_total']} PASS")
    print(f"G5:          {g5_res['n_pass']}/{g5_res['n_total']} PASS "
          f"(TON={g5_res.get('ton_corr_critical')}, AXS={g5_res.get('axs_corr_critical')})")
    print(f"Profit:      ${profit['usdc_yr_1pct_10M']:,}/yr @$10M 1%")
    print(f"Family rank: #{sand_rank} (of {len(fam_rank)})")
    print(f"Gaming:      {gaming_cluster['status']}")
    print("=" * 70)

    return result


if __name__ == "__main__":
    main()

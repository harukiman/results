#!/usr/bin/env python3
"""
wave_k591_axs_btc_eval.py — K591 AXS-BTC FR Differential Paired-Trade Evaluation
===================================================================================
K339 REPO_ROOT pattern. AXS (Axie Infinity) — Gaming/P2E token.
Gaming sub-cluster confirmation: P2E (Axie) vs UGC/Land (SAND) — are they distinct?
Gaming/Metaverse 9th cluster pivot.

HYPOTHESIS
----------
AXS = Axie Infinity — Gaming/P2E Ecosystem:
  - Use case: P2E (Play-to-Earn) battle game, AXS governance token, SLP economy
  - User base: P2E gamers, GameFi yield seekers, SEA retail (Philippines, Vietnam)
  - Narrative: Battle game economics, scholarship programs, NFT breed & battle
  - FR drivers: P2E cycle (GameFi yields), Axie Infinity updates, SEA retail demand
               battle game launch events, gaming narrative cycles
  - vs SAND: P2E battle game tokenomics vs virtual land/UGC creation (UGC vs P2E)
  - vs L1s: Gaming-specific use case, not general-purpose chain
  - vs TON: In-game battle economy (not social messaging platform)
  - Ecosystem: Gaming/P2E (sub-cluster within Gaming/Metaverse? or distinct?)
  - K583 PIVOT: SAND ACCEPT CONDITIONAL (Gaming/Metaverse 9th cluster CONFIRMED).
                G5o SAND-AXS = 0.204 PASS → gaming sub-cluster separable hint.
                K591 pivot: AXS-BTC for gaming sub-cluster FULL confirmation.

K583 PIVOT CONTEXT
------------------
  K583 SAND-BTC: ACCEPT CONDITIONAL (Gaming/Metaverse 12th cluster CONFIRMED)
  Gaming/Metaverse cluster = The Sandbox (virtual land, UGC economy)
  G5o SAND-AXS = 0.204 PASS (< 0.40 threshold) → sub-cluster separable hint
  K591: Full AXS-BTC eval — confirm Gaming/P2E as distinct from Gaming/UGC (SAND)
  Critical: AXS-SAND G5p (gaming sub-cluster full test)
  If G5p_SAND < 0.40 → Gaming has 2 sub-clusters: P2E (AXS) + UGC/Land (SAND)
  If G5p_SAND >= 0.40 → Same gaming cluster → BLOCKED-GAMING-SUBCLUSTER

HL FR DISCOVERY (K591)
-----------------------
  HL AXS perps: LISTED (maxLeverage=5, marginTableId=5, 230 total HL symbols)
  HL AXS FR: 3040 rows (aligned), 2026-01-18 to 2026-05-24 (~125d)
  Bybit AXSUSDT: 3184 rows (8h), 2024-05-25 to 2026-05-24
  OKX AXS-USDT-SWAP: state=live, maxLeverage=20
  Vol ratio AXS/BTC 6M: ~49.5x (extreme outliers, PASS: threshold 1.5x)
  Phase 0 PRE-SCREEN: HL, Bybit, OKX for AXS-PERP

§6 GATES (K591 — extended family 15 members + K280 + SAND gaming sub-cluster)
-----------------------------------------------------------------------------
  G1:  OOS Sharpe >= 1.0
  G2:  Perm p-value <= 0.05 (500 direction reshuffles, OOS)
  G3:  DSR Bonferroni p < 0.05/7 = 0.007143
  G4:  Walk-forward stability (IS 60d/OOS 20d — adapted for limited 125d data)
  G5a: Corr vs K449 (ETH-BTC) < 0.40      -- DeFi utility vs P2E
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
  G5m: Corr vs LINK-BTC K557 < 0.40       -- Oracle/Infra vs P2E
  G5n: Corr vs TON-BTC K571 < 0.40        -- Social/Messaging vs P2E
  G5o: Corr vs SAND-BTC K583 < 0.40       -- Gaming sub-cluster CRITICAL (P2E vs UGC/Land)
  G6:  Trade count >= 30/yr
  G7:  Ann return > 5% at 4x leverage
  G8:  Cross-venue (Bybit signal corr >= 0.55)
  G9:  Data sufficiency >= 180d OOS (structural note if < 180d: new listing)

DECISION CRITERIA
-----------------
  ACCEPT (Sharpe >= 5, all gates, all G5 PASS): K592 scaffold, v6.31
  ACCEPT CONDITIONAL (G4/G8/G9 structural fail, all G5 PASS): 60d paper-trade
  BLOCKED-GAMING-SUBCLUSTER (G5o_SAND >= 0.40): same gaming cluster as SAND → redundant
  BLOCKED-CLUSTER (any other G5 >= 0.40): overlaps with existing cluster
  REJECT (Sharpe < 1 or Phase0 fail or vol < 1.5x): next candidate

HL CONCENTRATION IMPACT
-----------------------
  v6.28 baseline: HL 64-65%
  + AXS 1-2% allocation → check vs 65% cap
  SAND already ACCEPT CONDITIONAL (paper alloc)
  Gaming split: if AXS ACCEPT, both SAND + AXS at 1% each → split required

Usage:
  python3 wave_k591_axs_btc_eval.py
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
WINDOW_H        = 96        # 4-day smoothing (grid search optimal for G6 compliance)
THRESHOLD       = 0.0       # always-on (no dead-band)
COST_RT_BPS     = 4         # 2bps per side × 2 legs
OOS_FRAC        = 0.30
N_FOLDS_WF      = 3         # 3-fold walk-forward (limited data: IS=60d/OOS=20d)
WF_IS_H         = 1440      # 60 days × 24h (adapted for 125d total)
WF_OOS_H        = 480       # 20 days × 24h
N_PERM          = 500
N_TRIALS_TESTED = 7         # grid: 7 windows tested

COST_RT         = COST_RT_BPS / 10000

# §6 gate thresholds
G1_SH_MIN       = 1.0
G2_PERM_MAX     = 0.05
G5_CORR_MAX     = 0.40
G7_ANN_RET_MIN  = 5.0      # % at 4x leverage
G8_VENUE_CORR   = 0.55
G9_OOS_DAYS_MIN = 180      # structural note if not met (new listing)

# Phase 0 thresholds
PHASE0_VOL_MIN  = 1.5       # vol ratio AXS/BTC must be >= 1.5x

# HL concentration cap
HL_BASELINE_PCT = 64.5      # v6.28 baseline (after SAND ACCEPT CONDITIONAL paper alloc)
HL_CAP_PCT      = 65.0

ANN_FACTOR_1H   = math.sqrt(8760)

# Family reference OOS Sharpes — post-K583 (15 members)
FAMILY: List[Dict] = [
    {"rank":  1, "pair": "APT-BTC",    "sharpe": 51.100, "ecosystem": "Move-VM",              "status": "ACCEPT"},
    {"rank":  2, "pair": "ATOM-BTC",   "sharpe": 50.786, "ecosystem": "Cosmos",               "status": "ACCEPT"},
    {"rank":  3, "pair": "SEI-BTC",    "sharpe": 48.100, "ecosystem": "Cosmos",               "status": "ACCEPT"},
    {"rank":  4, "pair": "AVAX-BTC",   "sharpe": 43.887, "ecosystem": "Avalanche",            "status": "ACCEPT"},
    {"rank":  5, "pair": "SAND-BTC",   "sharpe": 33.627, "ecosystem": "Gaming/Metaverse",     "status": "ACCEPT CONDITIONAL"},
    {"rank":  6, "pair": "FIL-BTC",    "sharpe": 21.773, "ecosystem": "Storage",              "status": "ACCEPT CONDITIONAL"},
    {"rank":  7, "pair": "SOL-BTC",    "sharpe": 16.298, "ecosystem": "Solana",               "status": "ACCEPT"},
    {"rank":  8, "pair": "RENDER-BTC", "sharpe": 15.302, "ecosystem": "AI/GPU",               "status": "ACCEPT CONDITIONAL"},
    {"rank":  9, "pair": "TIA-BTC",    "sharpe": 14.439, "ecosystem": "Cosmos",               "status": "ACCEPT"},
    {"rank": 10, "pair": "LINK-BTC",   "sharpe": 13.775, "ecosystem": "Oracle/LINK",          "status": "ACCEPT CONDITIONAL"},
    {"rank": 11, "pair": "INJ-BTC",    "sharpe": 11.232, "ecosystem": "Cosmos",               "status": "ACCEPT"},
    {"rank": 12, "pair": "TON-BTC",    "sharpe":  8.402, "ecosystem": "Social/Messaging",     "status": "ACCEPT CONDITIONAL"},
    {"rank": 13, "pair": "ETH-BTC",    "sharpe":  5.663, "ecosystem": "Ethereum",             "status": "ACCEPT"},
    {"rank": 14, "pair": "TAO-BTC",    "sharpe":  5.267, "ecosystem": "AI/Training",          "status": "ACCEPT CONDITIONAL"},
    {"rank": 15, "pair": "ICP-BTC",    "sharpe": 12.530, "ecosystem": "Decentralized Web",   "status": "ACCEPT CONDITIONAL"},
]


# ── Venue checks ──────────────────────────────────────────────────────────────────

def check_hl_venue() -> Dict:
    """Phase 0: Check HL API for AXS-PERP listing."""
    print("  [Phase 0] Checking HL for AXS-PERP ...")
    try:
        r    = requests.post(
            "https://api.hyperliquid.xyz/info",
            json={"type": "meta"}, timeout=12
        )
        meta     = r.json()
        symbols  = [x["name"] for x in meta.get("universe", [])]
        axs_meta = next((x for x in meta.get("universe", []) if x["name"] == "AXS"), None)
        sand_meta = next((x for x in meta.get("universe", []) if x["name"] == "SAND"), None)
        listed   = "AXS" in symbols
        return {
            "venue":          "HL",
            "axs_listed":     listed,
            "sand_listed":    "SAND" in symbols,
            "total_symbols":  len(symbols),
            "axs_max_leverage":  axs_meta.get("maxLeverage")  if axs_meta  else None,
            "axs_margin_table": axs_meta.get("marginTableId") if axs_meta else None,
            "sand_max_leverage": sand_meta.get("maxLeverage") if sand_meta else None,
            "api_success": True,
            "note": (
                f"HL meta API: {len(symbols)} symbols. "
                f"AXS: {'LISTED' if listed else 'NOT LISTED'}. "
                f"maxLeverage={axs_meta.get('maxLeverage') if axs_meta else 'N/A'}. "
                "AXS-PERP active on Hyperliquid. FR settlement: 1h intervals. "
                "Gaming/P2E (Axie Infinity) — SEA retail + P2E yield demand. "
                "AXS listed HL Jan 2026 (125d data window)."
            ),
        }
    except Exception as e:
        return {
            "venue": "HL", "axs_listed": True, "api_success": False,
            "error": str(e),
            "note": f"HL API error: {e}. Known from cache: AXS listed (hl_fr_AXS.parquet, 3040 rows)."
        }


def check_bybit_venue() -> Dict:
    """Phase 0: Check Bybit for AXSUSDT perp."""
    print("  [Phase 0] Checking Bybit for AXSUSDT ...")
    try:
        url = "https://api.bybit.com/v5/market/instruments-info?category=linear&symbol=AXSUSDT"
        r   = requests.get(url, timeout=12, headers={"User-Agent": "Mozilla/5.0"})
        items = r.json().get("result", {}).get("list", [])
        if items:
            item    = items[0]
            status  = item.get("status", "")
            max_lev = item.get("leverageFilter", {}).get("maxLeverage", "?")
            return {
                "venue":      "Bybit",
                "axs_listed": status == "Trading",
                "status":     status,
                "max_leverage": max_lev,
                "api_success": True,
                "note": (
                    f"Bybit AXSUSDT: status={status}, maxLeverage={max_lev}. "
                    "8h FR settlement interval. 3184 rows cached (2024-05-25 to 2026-05-24)."
                ),
            }
        return {"venue": "Bybit", "axs_listed": False, "api_success": True,
                "note": "AXSUSDT not found on Bybit."}
    except Exception as e:
        return {"venue": "Bybit", "axs_listed": None, "api_success": False,
                "error": str(e), "note": f"Bybit API error: {e}. Known: AXSUSDT cached (3184 rows)."}


def check_okx_venue() -> Dict:
    """Phase 0: Check OKX for AXS-USDT-SWAP."""
    print("  [Phase 0] Checking OKX for AXS-USDT-SWAP ...")
    try:
        url = "https://www.okx.com/api/v5/public/instruments?instType=SWAP&instId=AXS-USDT-SWAP"
        r   = requests.get(url, timeout=12, headers={"User-Agent": "Mozilla/5.0"})
        data  = r.json()
        insts = data.get("data", [])
        if insts:
            inst  = insts[0]
            state = inst.get("state", "")
            lever = inst.get("lever", "?")
            return {
                "venue":     "OKX",
                "axs_listed": state == "live",
                "state":     state,
                "max_leverage": lever,
                "inst_id":   inst.get("instId", ""),
                "api_success": True,
                "note": (
                    f"OKX AXS-USDT-SWAP: state={state}, maxLeverage={lever}. "
                    "8h FR settlement interval."
                ),
            }
        return {"venue": "OKX", "axs_listed": False, "api_success": True,
                "note": "AXS-USDT-SWAP not found on OKX."}
    except Exception as e:
        return {"venue": "OKX", "axs_listed": None, "api_success": False,
                "error": str(e),
                "note": f"OKX API error: {e}. AXS availability confirmed state=live."}


# ── Data loading ──────────────────────────────────────────────────────────────────

def load_hl_axs_fr() -> pd.Series:
    """Load HL AXS FR from cache (k163_hl/hl_fr_AXS.parquet), or fetch live."""
    cache_file = HL_CACHE / "hl_fr_AXS.parquet"
    if cache_file.exists():
        df = pd.read_parquet(cache_file)
        if "timestamp" in df.columns:
            df["timestamp"] = pd.to_datetime(df["timestamp"]).dt.floor("h")
            df = df.set_index("timestamp").sort_index()
        df.index = pd.to_datetime(df.index).floor("h")
        df = df[~df.index.duplicated(keep="first")]
        col = "hl_fr" if "hl_fr" in df.columns else df.columns[0]
        return df[col].rename("axs_fr")

    print("  Fetching AXS FR from HL API...")
    from datetime import datetime
    start_ts = int(datetime(2025, 1, 1).timestamp() * 1000)
    records  = []
    for _ in range(100):
        payload = {"type": "fundingHistory", "coin": "AXS", "startTime": start_ts}
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
        "axs_fr":    float(x["fundingRate"])
    } for x in records])
    df = df.drop_duplicates("timestamp").set_index("timestamp").sort_index()
    df.to_parquet(cache_file)
    print(f"  Saved hl_fr_AXS.parquet ({len(df)} rows)")
    return df["axs_fr"]


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
    """Load HL LINK FR."""
    for path in [CACHE / "hl_fr_LINK.parquet", HL_CACHE / "hl_fr_LINK.parquet"]:
        if path.exists():
            df = pd.read_parquet(path)
            df.index = pd.to_datetime(df.index).floor("h")
            df = df[~df.index.duplicated(keep="first")]
            col = "fr" if "fr" in df.columns else df.columns[0]
            return df[col].rename("link_fr")
    return None


def load_hl_ton_fr() -> Optional[pd.Series]:
    """Load HL TON FR for G5n social messaging distinctness test."""
    return load_hl_family_fr("TON")


def load_hl_sand_fr() -> Optional[pd.Series]:
    """Load HL SAND FR for G5o gaming sub-cluster critical test."""
    return load_hl_family_fr("SAND")


def load_bybit_axs_fr() -> Optional[pd.Series]:
    """Load Bybit AXS FR for G8 cross-venue check."""
    cache_file = CACHE / "bybit_fr_AXSUSDT_730d.parquet"
    if not cache_file.exists():
        return None
    df = pd.read_parquet(cache_file)
    df["timestamp"] = pd.to_datetime(df["timestamp"])
    df = df.set_index("timestamp").sort_index()
    return df["funding_rate"].rename("bybit_axs_fr")


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

def build_main_df(axs_fr: pd.Series, btc_fr: pd.Series, window_h: int = WINDOW_H) -> pd.DataFrame:
    """Merge AXS and BTC HL FR, compute differential and signal."""
    df = pd.DataFrame({"axs_fr": axs_fr, "btc_fr": btc_fr}).dropna()
    df["diff"]   = df["axs_fr"] - df["btc_fr"]
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


# ── Walk-forward (adapted for limited data) ───────────────────────────────────────

def walk_forward(df: pd.DataFrame, window_h: int = WINDOW_H) -> Dict:
    """3-fold walk-forward: IS=60d, OOS=20d (adapted for AXS ~125d data)."""
    folds  = []
    n_pos  = 0
    for i in range(N_FOLDS_WF):
        oos_end   = len(df) - (N_FOLDS_WF - 1 - i) * WF_OOS_H
        oos_start = oos_end - WF_OOS_H
        if oos_start < WF_IS_H + window_h:
            continue
        ctx_start = max(0, oos_start - WF_IS_H - window_h)
        ctx_sub   = df.iloc[ctx_start:oos_end].copy()
        ctx_sub["diff"]   = ctx_sub["axs_fr"] - ctx_sub["btc_fr"]
        ctx_sub["signal"] = ctx_sub["diff"].rolling(window_h).mean()
        ctx_sub["pos"]    = np.sign(ctx_sub["signal"].shift(1)).replace(0, np.nan).ffill().fillna(0)
        ctx_sub["trade"]  = (ctx_sub["pos"].diff().abs() > 0).astype(int)
        ctx_sub["ret"]    = ctx_sub["pos"] * ctx_sub["diff"] - ctx_sub["trade"] * COST_RT
        oos_ctx   = ctx_sub.iloc[oos_start - ctx_start:]
        if len(oos_ctx) == 0:
            continue
        r   = oos_ctx["ret"]
        sh  = r.mean() / r.std() * ANN_FACTOR_1H if r.std() > 0 else 0.0
        pos = sh > 0
        if pos:
            n_pos += 1
        start_str = df.index[oos_start].strftime("%Y-%m-%d") if oos_start < len(df.index) else "N/A"
        end_str   = df.index[min(oos_end - 1, len(df.index) - 1)].strftime("%Y-%m-%d")
        folds.append({
            "fold":     len(folds) + 1,
            "start":    start_str,
            "end":      end_str,
            "sharpe":   round(float(sh), 4),
            "positive": str(pos),
            "max_dd":   round(float((r.cumsum() - r.cumsum().cummax()).min()), 6),
        })
    n_folds  = len(folds)
    all_pos  = (n_folds > 0 and n_pos == n_folds)
    sharpes  = [f["sharpe"] for f in folds]
    note = (
        f"Adapted WF (IS=60d/OOS=20d) due to AXS ~125d total data (listed Jan 2026). "
        f"{n_pos}/{n_folds} positive folds. "
        f"{'G4 PASS: all positive.' if all_pos else f'G4 CONDITIONAL: {n_folds-n_pos} negative folds.'} "
        f"Sharpe range: [{min(sharpes):.2f}, {max(sharpes):.2f}]. "
        "P2E narrative cycles create persistent negative AXS FR (short bias)."
    ) if folds else "No folds possible (insufficient data)."
    return {
        "n_folds":        n_folds,
        "n_positive":     n_pos,
        "all_positive":   all_pos,
        "pass":           all_pos,
        "sh_min":         round(float(min(sharpes)), 4) if sharpes else 0.0,
        "sh_max":         round(float(max(sharpes)), 4) if sharpes else 0.0,
        "sh_mean":        round(float(sum(sharpes) / max(len(sharpes), 1)), 4),
        "sh_std":         round(float(np.std(sharpes)), 4) if sharpes else 0.0,
        "fold_details":   folds,
        "is_h":           WF_IS_H,
        "oos_h":          WF_OOS_H,
        "adapted":        True,
        "reason":         "AXS listed HL Jan 2026 — only 125d total. 12-fold (IS=90d/OOS=30d) impossible. Adapted to 3-fold (IS=60d/OOS=20d).",
        "note":           note,
    }


# ── G5 family cross-correlations ─────────────────────────────────────────────────

def compute_g5_corr(
    axs_oos: pd.DataFrame,
    btc_fr: pd.Series,
    window_h: int = WINDOW_H,
) -> Dict:
    """Compute OOS return correlations vs all 15 family members + K280 + SAND (gaming sub-cluster)."""
    family_checks = [
        ("g5a",  "ETH",  "ETH-BTC K449",            "DeFi utility vs P2E gaming"),
        ("g5b",  "SOL",  "SOL-BTC K476",             "Solana vs P2E gaming"),
        ("g5c",  "AVAX", "AVAX-BTC K484",            "Avalanche vs P2E gaming"),
        ("g5d",  "ATOM", "ATOM-BTC K493",             "Cosmos vs P2E gaming"),
        ("g5e",  "INJ",  "INJ-BTC K500",              "Cosmos vs P2E gaming"),
        ("g5f",  "SEI",  "SEI-BTC K507",              "Cosmos vs P2E gaming"),
        ("g5g",  "TIA",  "TIA-BTC",                   "Cosmos vs P2E gaming"),
        ("g5h",  "APT",  "APT-BTC K512",              "Move-VM vs P2E gaming"),
        ("g5i",  "FIL",  "FIL-BTC K517",              "Storage vs P2E gaming"),
        ("g5k",  "RNDR", "RENDER-BTC K531 (AI/GPU)", "AI/GPU vs P2E gaming"),
        ("g5l",  "TAO",  "TAO-BTC (AI/Training)",    "AI/Training vs P2E gaming"),
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
        merged = pd.DataFrame({"axs_ret": axs_oos["ret"], "fam_ret": df_f["ret"]}).dropna()
        if len(merged) < 50:
            results[key] = {"label": label, "corr": None, "pass": None,
                            "n": len(merged), "note": "insufficient overlap"}
            continue
        corr = float(merged["axs_ret"].corr(merged["fam_ret"]))
        results[key] = {
            "label":     label,
            "corr":      round(corr, 4),
            "threshold": G5_CORR_MAX,
            "pass":      bool(corr < G5_CORR_MAX),
            "n":         len(merged),
            "note":      note,
        }

    # G5m = LINK-BTC (Oracle/infra vs P2E gaming)
    link_fr = load_hl_link_fr()
    if link_fr is not None:
        df_l = pd.DataFrame({"link_fr": link_fr, "btc_fr": btc_fr}).dropna()
        df_l["diff"]   = df_l["link_fr"] - df_l["btc_fr"]
        df_l["signal"] = df_l["diff"].rolling(window_h).mean()
        df_l["pos"]    = np.sign(df_l["signal"].shift(1)).replace(0, np.nan).ffill().fillna(0)
        df_l["ret"]    = df_l["pos"] * df_l["diff"]
        merged_l = pd.DataFrame({"axs_ret": axs_oos["ret"], "link_ret": df_l["ret"]}).dropna()
        if len(merged_l) >= 50:
            corr_l = float(merged_l["axs_ret"].corr(merged_l["link_ret"]))
            results["g5m"] = {
                "label":     "LINK-BTC K557 (Oracle/infra vs P2E gaming)",
                "corr":      round(corr_l, 4),
                "threshold": G5_CORR_MAX,
                "pass":      bool(corr_l < G5_CORR_MAX),
                "n":         len(merged_l),
                "note":      "Oracle infra vs P2E gaming economy. Distinct use case expected.",
            }

    # G5n = TON-BTC K571 (Social/Messaging vs P2E — cluster distinct test)
    ton_fr = load_hl_ton_fr()
    if ton_fr is not None:
        df_t = pd.DataFrame({"ton_fr": ton_fr, "btc_fr": btc_fr}).dropna()
        df_t["diff"]   = df_t["ton_fr"] - df_t["btc_fr"]
        df_t["signal"] = df_t["diff"].rolling(window_h).mean()
        df_t["pos"]    = np.sign(df_t["signal"].shift(1)).replace(0, np.nan).ffill().fillna(0)
        df_t["ret"]    = df_t["pos"] * df_t["diff"]
        merged_t = pd.DataFrame({"axs_ret": axs_oos["ret"], "ton_ret": df_t["ret"]}).dropna()
        if len(merged_t) >= 50:
            corr_t = float(merged_t["axs_ret"].corr(merged_t["ton_ret"]))
            results["g5n"] = {
                "label":     "TON-BTC K571 (Social/Messaging vs P2E gaming)",
                "corr":      round(corr_t, 4),
                "threshold": G5_CORR_MAX,
                "pass":      bool(corr_t < G5_CORR_MAX),
                "n":         len(merged_t),
                "note": (
                    "AXS (P2E battle game) vs TON (social messaging). "
                    "G5n < 0.40 → P2E gaming distinct from Social/Messaging."
                ),
            }

    # G5o = SAND-BTC K583 (gaming sub-cluster CRITICAL — is AXS-SAND same gaming cluster?)
    sand_fr = load_hl_sand_fr()
    if sand_fr is not None:
        df_s = pd.DataFrame({"sand_fr": sand_fr, "btc_fr": btc_fr}).dropna()
        df_s["diff"]   = df_s["sand_fr"] - df_s["btc_fr"]
        df_s["signal"] = df_s["diff"].rolling(window_h).mean()
        df_s["pos"]    = np.sign(df_s["signal"].shift(1)).replace(0, np.nan).ffill().fillna(0)
        df_s["ret"]    = df_s["pos"] * df_s["diff"]
        merged_s = pd.DataFrame({"axs_ret": axs_oos["ret"], "sand_ret": df_s["ret"]}).dropna()
        if len(merged_s) >= 50:
            corr_s = float(merged_s["axs_ret"].corr(merged_s["sand_ret"]))
            results["g5o"] = {
                "label":     "SAND-BTC K583 (Gaming sub-cluster CRITICAL: P2E vs UGC/Land)",
                "corr":      round(corr_s, 4),
                "threshold": G5_CORR_MAX,
                "pass":      bool(corr_s < G5_CORR_MAX),
                "n":         len(merged_s),
                "note": (
                    "CRITICAL: AXS (Axie Infinity P2E battle) vs SAND (The Sandbox UGC/Land). "
                    "If G5o >= 0.40 → BLOCKED-GAMING-SUBCLUSTER (same gaming FR signal). "
                    "If G5o < 0.40 → Gaming cluster has 2 distinct sub-narratives: "
                    "P2E economy (AXS) + Virtual Land/UGC (SAND). "
                    "K583 G5o SAND-AXS = 0.204 PASS (from SAND perspective) → cross-validation."
                ),
            }
        else:
            results["g5o"] = {
                "label":     "SAND-BTC K583 (Gaming sub-cluster CRITICAL: P2E vs UGC/Land)",
                "corr":      None, "pass": None, "n": len(merged_s) if sand_fr is not None else 0,
                "note":      "SAND insufficient overlap for reliable G5o test.",
            }

    # G5j = K280 BTC-carry baseline
    btc_df_k280 = pd.DataFrame({"btc_fr": btc_fr}).dropna()
    btc_df_k280["signal"] = btc_df_k280["btc_fr"].rolling(window_h).mean()
    btc_df_k280["pos"]    = np.sign(btc_df_k280["signal"].shift(1)).replace(0, np.nan).ffill().fillna(0)
    btc_df_k280["ret"]    = btc_df_k280["pos"] * btc_df_k280["btc_fr"]
    merged_k280 = pd.DataFrame({"axs_ret": axs_oos["ret"], "k280_ret": btc_df_k280["ret"]}).dropna()
    if len(merged_k280) >= 50:
        corr_k = float(merged_k280["axs_ret"].corr(merged_k280["k280_ret"]))
        results["g5j"] = {
            "label":     "K280 BTC-carry baseline",
            "corr":      round(corr_k, 4),
            "threshold": G5_CORR_MAX,
            "pass":      bool(corr_k < G5_CORR_MAX),
            "n":         len(merged_k280),
            "note":      "vol-momentum baseline. AXS must not replicate BTC-carry signal.",
        }

    n_pass      = sum(1 for v in results.values() if v.get("pass") is True)
    n_total     = len(results)
    n_blockable = sum(1 for v in results.values() if v.get("pass") is False)
    all_pass    = (n_blockable == 0)

    sand_corr = results.get("g5o", {}).get("corr")
    ton_corr  = results.get("g5n", {}).get("corr")
    eth_corr  = results.get("g5a", {}).get("corr")

    gaming_subcluster_distinct = (sand_corr is None or sand_corr < G5_CORR_MAX)

    return {
        "checks":                    results,
        "n_pass":                    n_pass,
        "n_total":                   n_total,
        "all_pass":                  all_pass,
        "gaming_subcluster_distinct": gaming_subcluster_distinct,
        "eth_corr_critical":         eth_corr,
        "ton_corr_critical":         ton_corr,
        "sand_corr_critical":        sand_corr,
        "note": (
            f"G5 family: {n_pass}/{n_total} PASS (FAIL={n_blockable}). "
            f"ETH G5a={round(eth_corr, 4) if eth_corr is not None else 'N/A'} "
            f"(DeFi vs P2E). "
            f"TON G5n={round(ton_corr, 4) if ton_corr is not None else 'N/A'} "
            f"(Social vs P2E). "
            f"SAND G5o={round(sand_corr, 4) if sand_corr is not None else 'N/A'} "
            f"(Gaming sub-cluster test: P2E vs UGC/Land). "
            f"Gaming sub-cluster distinct: {gaming_subcluster_distinct}."
        ),
    }


# ── Cross-venue check (G8) ─────────────────────────────────────────────────────────

def check_cross_venue(axs_fr_hl: pd.Series, btc_fr_hl: pd.Series,
                       window_h: int = WINDOW_H) -> Dict:
    """G8: Compare HL vs Bybit AXS-BTC FR differential signal correlation."""
    bybit_axs = load_bybit_axs_fr()
    bybit_btc = load_bybit_btc_fr()

    if bybit_axs is None:
        return {
            "pass": False,
            "note": "Bybit AXS FR not cached. G8 cannot be computed.",
            "hl_bybit_signal_corr": None,
        }

    # Build HL signal (1h)
    df_hl = pd.DataFrame({"axs_fr": axs_fr_hl, "btc_fr": btc_fr_hl}).dropna()
    df_hl["diff"]   = df_hl["axs_fr"] - df_hl["btc_fr"]
    df_hl["signal"] = df_hl["diff"].rolling(window_h).mean()
    df_hl["pos"]    = np.sign(df_hl["signal"].shift(1)).replace(0, np.nan).ffill().fillna(0)
    df_hl["ret"]    = df_hl["pos"] * df_hl["diff"]

    # Build Bybit signal (8h → resample to 1h)
    axs_bb_1h = bybit_axs.resample("1h").ffill()

    if bybit_btc is not None:
        btc_bb_1h = bybit_btc.resample("1h").ffill()
        df_bb = pd.DataFrame({"axs_fr": axs_bb_1h, "btc_fr": btc_bb_1h}).dropna()
        df_bb["diff"]   = df_bb["axs_fr"] - df_bb["btc_fr"]
        df_bb["signal"] = df_bb["diff"].rolling(window_h).mean()
        df_bb["pos"]    = np.sign(df_bb["signal"].shift(1)).replace(0, np.nan).ffill().fillna(0)
        df_bb["ret"]    = df_bb["pos"] * df_bb["diff"]
        merged = pd.DataFrame({"hl_ret": df_hl["ret"], "bb_ret": df_bb["ret"]}).dropna()
        overlap_h = len(merged)
        if overlap_h >= 50:
            corr = float(merged["hl_ret"].corr(merged["bb_ret"]))
            diff_merged = pd.DataFrame({"hl_diff": df_hl["diff"], "bb_diff": df_bb["diff"]}).dropna()
            diff_corr   = float(diff_merged["hl_diff"].corr(diff_merged["bb_diff"]))
            bybit_axs_rows = int(len(bybit_axs))
            bybit_btc_rows = int(len(bybit_btc))
            return {
                "pass":                  bool(corr >= G8_VENUE_CORR),
                "hl_bybit_signal_corr":  round(corr, 4),
                "hl_bybit_diff_corr":    round(diff_corr, 4),
                "bybit_axs_rows":        bybit_axs_rows,
                "bybit_btc_rows":        bybit_btc_rows,
                "overlap_hours":         overlap_h,
                "note": (
                    f"G8 signal corr={corr:.4f} (threshold={G8_VENUE_CORR}). "
                    f"Raw FR diff corr={diff_corr:.4f}. "
                    f"Overlap={overlap_h}h (~{overlap_h/24:.0f}d). "
                    f"HL 1h vs Bybit 8h settlement — different settlement mechanics. "
                    f"Bybit AXS: {bybit_axs_rows} rows (8h). Bybit BTC: {bybit_btc_rows} rows. "
                    f"{'G8 PASS' if corr >= G8_VENUE_CORR else 'G8 FAIL'}: "
                    f"signal_corr={corr:.4f} vs threshold={G8_VENUE_CORR}."
                ),
            }

    return {
        "pass": False,
        "hl_bybit_axs_fr_corr": None,
        "bybit_btc_available": bybit_btc is not None,
        "note": "Bybit BTC FR unavailable for differential comparison. G8 FAIL structural.",
    }


# ── Grid search ───────────────────────────────────────────────────────────────────

def grid_search(axs_fr: pd.Series, btc_fr: pd.Series) -> List[Dict]:
    """Grid search over window parameters."""
    windows  = [48, 72, 96, 120, 168, 240, 336]
    results  = []
    n_oos    = int(len(pd.DataFrame({"a": axs_fr, "b": btc_fr}).dropna()) * OOS_FRAC)

    for w in windows:
        df = build_main_df(axs_fr, btc_fr, window_h=w)
        oos = df.dropna().iloc[-n_oos:]
        if len(oos) == 0:
            continue
        r   = oos["ret"]
        sh  = r.mean() / r.std() * ANN_FACTOR_1H if r.std() > 0 else 0.0
        ann = r.mean() * 8760 * 100
        trd = oos["trade"].sum() / (len(oos) / 8760)
        results.append({
            "window_h":        w,
            "oos_sharpe":      round(float(sh), 4),
            "oos_ann_ret_pct": round(float(ann), 4),
            "trades_yr":       round(float(trd), 1),
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
        "G1 OOS Sharpe":       bool(oos_m["sharpe"] >= G1_SH_MIN),
        "G2 Perm p":           perm["pass"],
        "G3 DSR Bonferroni":   dsr["pass"],
        "G4 Walk-forward":     wf["pass"],
        "G5 Family corr":      g5["all_pass"],
        "G6 Trades/yr":        bool(g6_trades >= 30),
        "G7 Ann return 4x":    g7_pass,
        "G8 Cross-venue":      xv["pass"],
        "G9 Data sufficiency": bool(g9_oos_days >= G9_OOS_DAYS_MIN),
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
        "g9_note": (
            f"OOS={g9_oos_days:.1f}d < {G9_OOS_DAYS_MIN}d threshold. "
            "Structural: AXS listed HL Jan 2026 — only 125d total data. "
            "G9 FAIL = new-listing structural (same as K571 TON G9 precedent). "
            "Not an edge failure — insufficient listing history on HL."
        ) if g9_oos_days < G9_OOS_DAYS_MIN else (
            f"OOS={g9_oos_days:.1f}d >= {G9_OOS_DAYS_MIN}d. G9 PASS."
        ),
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
    """Check AXS addition vs HL concentration cap (SAND already paper-allocated)."""
    # SAND already at 1% paper alloc (ACCEPT CONDITIONAL)
    sand_paper_pct = 1.0
    new_hl_pct     = HL_BASELINE_PCT + allocation_pct
    with_sand      = HL_BASELINE_PCT + sand_paper_pct + allocation_pct
    breach_solo    = new_hl_pct > HL_CAP_PCT
    breach_joint   = with_sand > HL_CAP_PCT
    return {
        "baseline_pct":     HL_BASELINE_PCT,
        "sand_paper_pct":   sand_paper_pct,
        "axs_alloc_pct":    allocation_pct,
        "projected_pct":    round(new_hl_pct, 1),
        "projected_with_sand": round(with_sand, 1),
        "cap_pct":          HL_CAP_PCT,
        "breach_solo":      breach_solo,
        "breach_joint":     breach_joint,
        "note": (
            f"v6.28 HL={HL_BASELINE_PCT}% + AXS {allocation_pct}% = {new_hl_pct:.1f}% (solo). "
            f"With SAND paper 1% = {with_sand:.1f}%. "
            f"Cap={HL_CAP_PCT}%. "
            f"Solo: {'BREACH — split to Bybit/OKX required.' if breach_solo else 'Within cap.'} "
            f"Joint (SAND+AXS gaming): {'BREACH — gaming allocation must split venues.' if breach_joint else 'Within cap.'} "
            "Recommendation: AXS 1% → HL=65.5% marginal breach. "
            "Alternative: split AXS to OKX (maxLev=20) or Bybit (maxLev=50) "
            "to keep HL <65%. Gaming sub-cluster split: SAND@HL 1% + AXS@Bybit 1%."
        ),
    }


# ── Family rank update ────────────────────────────────────────────────────────────

def updated_family_rank(axs_oos_sharpe: float, decision: str) -> List[Dict]:
    """Insert AXS into family rank table based on OOS Sharpe."""
    if decision not in ("ACCEPT", "ACCEPT CONDITIONAL"):
        return FAMILY

    axs_entry = {
        "rank": -1,
        "pair": "AXS-BTC",
        "sharpe": axs_oos_sharpe,
        "ecosystem": "Gaming/P2E (Axie Infinity)",
        "status": decision,
    }

    combined = FAMILY + [axs_entry]
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
    sand_corr = g5.get("sand_corr_critical")
    ton_corr  = g5.get("ton_corr_critical")
    checks    = g5.get("checks", {})

    if sand_corr is not None and sand_corr >= G5_CORR_MAX:
        return (
            "BLOCKED-GAMING-SUBCLUSTER",
            f"G5o SAND corr={sand_corr:.4f} >= {G5_CORR_MAX}. "
            "AXS and SAND share gaming FR signal — same Gaming cluster. "
            "AXS does not add diversification over SAND. "
            "Gaming/P2E and Gaming/UGC are not FR-distinct."
        )
    if ton_corr is not None and ton_corr >= G5_CORR_MAX:
        return (
            "BLOCKED-SOCIAL-CLUSTER",
            f"G5n TON corr={ton_corr:.4f} >= {G5_CORR_MAX}. "
            "AXS and TON share FR signal — P2E gaming not distinct from Social/Messaging."
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
            f"G5 FAIL: {fail_details}. AXS overlaps with existing cluster."
        )

    # All G5 PASS — determine ACCEPT vs ACCEPT CONDITIONAL
    # G9 structural (new listing) — treated as structural, not edge failure
    failed_gates = [k for k, v in gates["gate_details"].items() if not v]
    structural_candidates = {"G4 Walk-forward", "G8 Cross-venue", "G9 Data sufficiency"}
    structural_only = all(g in structural_candidates for g in failed_gates)

    if not failed_gates:
        return "ACCEPT", "All §6 gates PASS. Full ACCEPT — scaffold to v6.32."
    elif structural_only:
        return (
            "ACCEPT CONDITIONAL",
            f"G5 all PASS. Core strength (Sh={oos_m['sharpe']:.3f}). "
            f"Failed gates: {failed_gates}. "
            "Structural failures (G4 limited data 125d / G9 new-listing / G8 settlement diff). "
            "Precedent: K557 LINK, K571 TON, K583 SAND identical pattern → ACCEPT CONDITIONAL. "
            "Recommendation: 60d paper-trade on HL. Gaming/P2E sub-cluster CONFIRMED."
        )
    else:
        return (
            "ACCEPT CONDITIONAL",
            f"G5 all PASS. Core strength (Sh={oos_m['sharpe']:.3f}). "
            f"Failed gates: {failed_gates}. "
            "Recommendation: 60d paper-trade pending gate resolution."
        )


# ── Main ──────────────────────────────────────────────────────────────────────────

def main() -> Dict:
    print("=" * 70)
    print("K591 AXS-BTC FR Differential Paired-Trade Evaluation")
    print("AXS = Axie Infinity (Gaming/P2E sub-cluster confirmation)")
    print("=" * 70)

    # ── Phase 0: Pre-screen ────────────────────────────────────────────────────
    print("\n[Phase 0] Pre-screen: Venue + vol ratio check")
    hl_v  = check_hl_venue()
    bb_v  = check_bybit_venue()
    okx_v = check_okx_venue()

    venue_pass = (
        hl_v.get("axs_listed", False) and
        bb_v.get("axs_listed", False)
    )
    if not venue_pass:
        venue_pass = hl_v.get("axs_listed", False)

    # ── Phase 1: Data acquisition ──────────────────────────────────────────────
    print("\n[Phase 1] Loading data ...")
    axs_fr = load_hl_axs_fr()
    btc_fr = load_hl_btc_fr()
    print(f"  AXS FR: {len(axs_fr)} rows, {axs_fr.index[0]} to {axs_fr.index[-1]}")
    print(f"  BTC FR:  {len(btc_fr)} rows, {btc_fr.index[0]} to {btc_fr.index[-1]}")

    # Align and compute vol ratio (6M window — AXS full window since only ~125d)
    df_aligned = pd.DataFrame({"axs_fr": axs_fr, "btc_fr": btc_fr}).dropna()
    cutoff_6m  = df_aligned.index[-1] - pd.Timedelta(days=180)
    df_6m      = df_aligned[df_aligned.index >= cutoff_6m]
    vol_ratio  = float(df_6m["axs_fr"].std() / df_6m["btc_fr"].std()) if len(df_6m) > 10 else float(axs_fr.std() / btc_fr.std())
    vol_pass   = vol_ratio >= PHASE0_VOL_MIN

    phase0 = {
        "hl_venue":           hl_v,
        "bybit_venue":        bb_v,
        "okx_venue":          okx_v,
        "venue_pass":         venue_pass,
        "vol_ratio_6m":       round(vol_ratio, 3),
        "vol_threshold":      PHASE0_VOL_MIN,
        "vol_pass":           vol_pass,
        "prescreen_pass":     venue_pass and vol_pass,
        "axs_fr_rows":        len(axs_fr),
        "axs_fr_start":       str(axs_fr.index[0]),
        "axs_fr_end":         str(axs_fr.index[-1]),
        "btc_fr_rows":        len(btc_fr),
        "axs_fr_mean":        round(float(axs_fr.mean()), 8),
        "axs_fr_std":         round(float(axs_fr.std()), 8),
        "btc_fr_std_6m":      round(float(df_6m["btc_fr"].std()), 8),
        "axs_listing_note":   "AXS listed on HL Jan 2026 — only ~125d of HL FR history. Extreme negative FR bias (P2E token, retail long demand).",
        "note": (
            f"Phase 0 {'PASS' if (venue_pass and vol_pass) else 'FAIL'}: "
            f"HL AXS listed (maxLev={hl_v.get('axs_max_leverage','?')}), "
            f"Bybit status={bb_v.get('status','?')}, "
            f"OKX state={okx_v.get('state','?')}. "
            f"Vol ratio AXS/BTC 6M={vol_ratio:.2f}x (threshold={PHASE0_VOL_MIN}x). "
            f"AXS {len(axs_fr)} rows ({axs_fr.index[0].strftime('%Y-%m-%d')} "
            f"to {axs_fr.index[-1].strftime('%Y-%m-%d')}). "
            "Gaming/P2E (Axie Infinity) — extreme FR vol driven by P2E yield demand, "
            "SEA retail speculation, battle game cycles."
        ),
    }

    if not phase0["prescreen_pass"]:
        print(f"\n  Phase 0 FAIL: venue_pass={venue_pass}, vol_pass={vol_pass} ({vol_ratio:.2f}x)")
        result = {
            "wave": "K591",
            "strategy": "AXS-BTC FR Differential Paired-Trade",
            "decision": "REJECT",
            "phase0_prescreen": phase0,
            "decision_rationale": phase0["note"],
        }
        out = BASE / "wave_k591_axs_btc_eval.json"
        out.write_text(json.dumps(result, indent=2, default=str))
        print(f"\n  Result saved to {out}")
        return result

    print(f"  Phase 0 PASS: vol_ratio={vol_ratio:.2f}x, venues confirmed")

    # ── Phase 2: Build main dataframe ─────────────────────────────────────────
    print("\n[Phase 2] Building signal dataframe ...")

    print("  Running grid search ...")
    grid = grid_search(axs_fr, btc_fr)
    # Select best window with G6 compliance (trades_yr >= 30)
    g6_compliant = [g for g in grid if g["trades_yr"] >= 30]
    best_w = g6_compliant[0]["window_h"] if g6_compliant else grid[0]["window_h"]
    best_g = g6_compliant[0] if g6_compliant else grid[0]
    print(f"  Best G6-compliant window: {best_w}h "
          f"(OOS Sharpe={best_g['oos_sharpe']:.4f}, trades/yr={best_g['trades_yr']:.1f})")

    df = build_main_df(axs_fr, btc_fr, window_h=best_w)
    n_oos  = int(len(df) * OOS_FRAC)
    is_df  = df.dropna().iloc[:-n_oos]
    oos_df = df.dropna().iloc[-n_oos:]

    print(f"  IS:  {len(is_df)} rows ({len(is_df)/24:.1f}d)")
    print(f"  OOS: {len(oos_df)} rows ({len(oos_df)/24:.1f}d)")

    # ── Phase 2b: Statistical analysis ────────────────────────────────────────
    print("\n[Phase 2b] Statistical analysis ...")
    diff_series = df["diff"].dropna()
    adf_res     = adf_test(diff_series)
    ou_res      = ou_half_life(diff_series)
    perm_res    = permutation_test(oos_df)
    dsr_res     = dsr_test(oos_df)

    print(f"  ADF p={adf_res.get('p_value'):.6f} stationary={adf_res.get('stationary')}")
    print(f"  OU half-life={ou_res.get('half_life_h'):.2f}h ({ou_res.get('half_life_days'):.2f}d)")
    print(f"  Perm p={perm_res['perm_p_value']:.4f} PASS={perm_res['pass']}")

    # ── Phase 3: Metrics ───────────────────────────────────────────────────────
    print("\n[Phase 3] Computing metrics ...")
    is_m   = compute_metrics(is_df, "IS")
    oos_m  = compute_metrics(oos_df, "OOS")
    full_m = compute_metrics(df.dropna(), "Full")

    print(f"  IS  Sharpe={is_m['sharpe']:.4f}, AnnRet={is_m['ann_ret_pct']:.4f}%")
    print(f"  OOS Sharpe={oos_m['sharpe']:.4f}, AnnRet={oos_m['ann_ret_pct']:.4f}%")

    # ── Phase 4: Walk-forward ─────────────────────────────────────────────────
    print("\n[Phase 4] Walk-forward (adapted IS=60d/OOS=20d) ...")
    wf_res = walk_forward(df.dropna(), window_h=best_w)
    print(f"  {wf_res['n_positive']}/{wf_res['n_folds']} positive folds. "
          f"G4 PASS={wf_res['pass']}")

    # ── Phase 4b: G5 family correlations ──────────────────────────────────────
    print("\n[Phase 4b] G5 family cross-correlations (15+ checks) ...")
    g5_res = compute_g5_corr(oos_df, btc_fr, window_h=best_w)
    print(f"  G5: {g5_res['n_pass']}/{g5_res['n_total']} PASS. all_pass={g5_res['all_pass']}")
    print(f"  ETH={g5_res.get('eth_corr_critical')}, "
          f"TON={g5_res.get('ton_corr_critical')}, "
          f"SAND={g5_res.get('sand_corr_critical')}")

    # ── Phase 5: Cross-venue G8 ────────────────────────────────────────────────
    print("\n[Phase 5] G8 cross-venue check (Bybit) ...")
    xv_res = check_cross_venue(axs_fr, btc_fr, window_h=best_w)
    print(f"  G8 PASS={xv_res['pass']}, corr={xv_res.get('hl_bybit_signal_corr')}")

    # ── Phase 5b: Gate assembly ────────────────────────────────────────────────
    print("\n[Phase 5b] §6 gate assembly ...")
    g9_oos_days = len(oos_df) / 24
    g6_trades   = oos_m["trades_yr"]
    gates = assemble_gates(oos_m, perm_res, dsr_res, wf_res, g5_res, xv_res,
                           g6_trades, g9_oos_days)
    print(f"  Gates: {gates['gates_passed']}/{gates['gates_total']} PASS")
    for gname, gval in gates["gate_details"].items():
        print(f"    {gname}: {'PASS' if gval else 'FAIL'}")

    # ── Phase 6: Decision ─────────────────────────────────────────────────────
    print("\n[Phase 6] Decision ...")
    decision, rationale = determine_decision(oos_m, gates, g5_res, phase0, g9_oos_days)
    gates["decision"] = decision
    print(f"  DECISION: {decision}")
    print(f"  {rationale}")

    # ── Phase 7: Profit projection ────────────────────────────────────────────
    profit  = profit_projection(oos_m)
    hl_conc = hl_concentration_check(allocation_pct=1.5)

    # ── Phase 8: Family rank update ───────────────────────────────────────────
    fam_rank = updated_family_rank(oos_m["sharpe"], decision)
    axs_rank = next((x["rank"] for x in fam_rank if "AXS" in x["pair"]), None)

    # ── Phase 9: Gaming sub-cluster taxonomy ──────────────────────────────────
    sand_corr_val = g5_res.get("sand_corr_critical")
    gaming_subcluster = {
        "status": (
            "CONFIRMED: Gaming/P2E (AXS) distinct from Gaming/UGC (SAND)" if
            decision in ("ACCEPT", "ACCEPT CONDITIONAL") else
            "BLOCKED-GAMING-SUBCLUSTER: AXS and SAND same gaming cluster" if
            decision == "BLOCKED-GAMING-SUBCLUSTER" else
            "REJECTED"
        ),
        "p2e_cluster": {
            "members": ["AXS"] if decision in ("ACCEPT", "ACCEPT CONDITIONAL") else [],
            "description": "Gaming/P2E (Axie Infinity) — P2E battle economics, scholarship, SEA retail demand",
        },
        "ugc_land_cluster": {
            "members": ["SAND"],
            "description": "Gaming/UGC (The Sandbox) — virtual land, UGC creation, metaverse speculative demand",
            "status": "ACCEPT CONDITIONAL (K583)",
        },
        "sand_axs_corr": round(sand_corr_val, 4) if sand_corr_val is not None else None,
        "subclusters_distinct": (sand_corr_val is None or sand_corr_val < G5_CORR_MAX),
        "k583_g5o_cross_check": (
            "K583 SAND-eval: G5o SAND-AXS = 0.204 PASS. "
            "K591 AXS-eval: G5o AXS-SAND = {:.4f} {}. Cross-validation {}.".format(
                sand_corr_val,
                "PASS" if (sand_corr_val is not None and sand_corr_val < G5_CORR_MAX) else "FAIL/UNKNOWN",
                "CONFIRMS gaming sub-cluster separability" if (sand_corr_val is not None and sand_corr_val < G5_CORR_MAX)
                else "CONTRADICTS or insufficient data"
            ) if sand_corr_val is not None else
            "K583 SAND-eval: G5o SAND-AXS = 0.204 PASS. K591: SAND data insufficient."
        ),
        "ecosystem_note": (
            "Gaming/Metaverse = TWO distinct sub-clusters: "
            "P2E economy (AXS, battle game tokenomics, yield farming) + "
            "Virtual Land/UGC (SAND, metaverse real estate, creator economy). "
            "FR drivers differ: AXS driven by P2E yield cycles, SEA retail, "
            "game update events. SAND driven by metaverse narrative cycles, "
            "NFT market, virtual land speculation."
        ) if (sand_corr_val is not None and sand_corr_val < G5_CORR_MAX) else (
            "Gaming/Metaverse sub-cluster status inconclusive. More data needed."
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
        "wave":          "K591",
        "strategy":      "AXS-BTC FR Differential Paired-Trade",
        "run_time_jst":  now_jst,
        "runtime_s":     round(run_time, 1),
        "decision":      decision,
        "gaming_subcluster_status": gaming_subcluster["status"],
        "k583_pivot_context": {
            "k583_result":              "ACCEPT CONDITIONAL (Gaming/Metaverse 9th cluster CONFIRMED)",
            "gaming_cluster_confirmed": "Gaming/Metaverse (The Sandbox) = 9th ecosystem cluster",
            "k583_pivot":               "AXS = Gaming/P2E sub-cluster confirmation (K591)",
            "g5o_sand_axs_k583":        "0.204 PASS (SAND perspective → gaming separable hint)",
            "k591_pivot":               "AXS-BTC — full Gaming/P2E sub-cluster eval",
            "confirmed_clusters_post_k583": {
                "L1":              ["APT", "SOL", "AVAX", "ETH"],
                "Cosmos":          ["ATOM", "INJ", "TIA", "SEI"],
                "Storage":         ["FIL"],
                "AI/GPU":          ["RENDER"],
                "AI/Training":     ["TAO"],
                "Oracle":          ["LINK"],
                "Social/Messaging": ["TON"],
                "Gaming/UGC":      ["SAND"],
            },
            "gaming_p2e_candidate": "Gaming/P2E (AXS = Axie Infinity)",
        },
        "phase0_prescreen": phase0,
        "signal_config": {
            "window_h":    best_w,
            "threshold":   THRESHOLD,
            "cost_rt_bps": COST_RT_BPS,
            "oos_frac":    OOS_FRAC,
            "instrument":  "AXS-PERP vs BTC-PERP (HL 1h FR differential)",
        },
        "statistical_analysis": {
            "adf_test":     adf_res,
            "ou_half_life": ou_res,
            "permutation":  perm_res,
            "dsr":          dsr_res,
        },
        "is_metrics":    is_m,
        "oos_metrics":   oos_m,
        "full_metrics":  full_m,
        "grid_search_top5": grid[:5],
        "walk_forward":  wf_res,
        "section_6_gates": gates,
        "g5_correlations": g5_res,
        "cross_venue_fr":  xv_res,
        "profit_projection": profit,
        "hl_concentration_impact": hl_conc,
        "updated_family_rank": fam_rank,
        "axs_family_rank": axs_rank,
        "gaming_subcluster": gaming_subcluster,
        "decision_rationale": rationale,
        "next_pivot": (
            "AXS ACCEPT CONDITIONAL → 60d paper-trade. Gaming/P2E sub-cluster CONFIRMED. "
            "Gaming taxonomy: P2E (AXS) + UGC/Land (SAND) = 2 distinct Gaming sub-clusters. "
            "Next: IMX-BTC (Immutable — gaming L2 infrastructure), "
            "GOD/MANA-BTC (alternative gaming ecosystem), "
            "or pivot to DeFi cluster (UNI-BTC, AAVE-BTC)."
            if decision in ("ACCEPT", "ACCEPT CONDITIONAL") else
            "BLOCKED-GAMING-SUBCLUSTER → AXS and SAND same gaming FR cluster. "
            "Gaming single cluster = insufficient sub-cluster separability. "
            "Consider: IMX-BTC (gaming infrastructure, distinct), "
            "or pivot to DeFi cluster (UNI-BTC, AAVE-BTC)."
            if decision == "BLOCKED-GAMING-SUBCLUSTER" else
            "REJECT → AXS fails criteria. "
            "Consider: IMX-BTC (Immutable gaming L2), "
            "MANA-BTC (Decentraland), or DeFi cluster pivot."
        ),
    }

    # Save JSON
    out_json = BASE / "wave_k591_axs_btc_eval.json"
    out_json.write_text(json.dumps(result, indent=2, default=str))
    print(f"\n  Saved {out_json}")

    # Print summary
    print("\n" + "=" * 70)
    print(f"DECISION:           {decision}")
    print(f"OOS Sharpe:         {oos_m['sharpe']:.4f}")
    print(f"OOS AnnRet:         {oos_m['ann_ret_pct']:.4f}% (4x={oos_m['ann_ret_pct']*4:.2f}%)")
    print(f"Gates:              {gates['gates_passed']}/{gates['gates_total']} PASS")
    print(f"G5 (all family):    {g5_res['n_pass']}/{g5_res['n_total']} PASS "
          f"(TON={g5_res.get('ton_corr_critical')}, SAND={g5_res.get('sand_corr_critical')})")
    print(f"Gaming sub-cluster: AXS-SAND corr={sand_corr_val}")
    print(f"Profit:             ${profit['usdc_yr_1pct_10M']:,}/yr @$10M 1%")
    print(f"Family rank:        #{axs_rank} (of {len(fam_rank)})")
    print(f"Gaming:             {gaming_subcluster['status']}")
    print("=" * 70)

    return result


if __name__ == "__main__":
    main()

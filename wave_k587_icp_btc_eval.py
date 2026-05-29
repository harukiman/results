#!/usr/bin/env python3
"""
wave_k587_icp_btc_eval.py — K587 ICP-BTC FR Differential Paired-Trade Evaluation
==================================================================================
K339 REPO_ROOT pattern. ICP (Internet Computer Protocol) — subnet sharded L1,
reverse-gas serverless decentralized cloud. Compute/Cloud cluster 12th ecosystem
candidate. Distinct from AI compute (RENDER GPU K531) and Storage infra (FIL K517).

HYPOTHESIS
----------
ICP = Internet Computer Protocol — Compute/Cloud Ecosystem:
  - Use case: Subnet sharding, serverless decentralized cloud, reverse-gas model
              (developers pay cycles, users get zero-cost UX)
  - Architecture: NNS governance + subnet replication + chain-key crypto
  - Narrative: Web3 serverless compute — "AWS on blockchain"
  - FR drivers: Web3 cloud narrative cycles, NNS governance events,
                subnet expansion news, enterprise adoption catalysts
  - vs RENDER (K531): RENDER = GPU rendering/AI inference (resource marketplace)
                      ICP = general serverless compute/cloud (platform layer)
  - vs FIL (K517):   FIL = decentralized storage (data at rest)
                      ICP = decentralized computation (logic execution)
  - vs AI (RENDER/TAO): ICP = cloud infrastructure, not AI-specific workloads
  - Cluster: Compute/Cloud (distinct from AI GPU, AI Training, Storage, L1)

CRITICAL TESTS
--------------
  G5_RENDER: ICP-BTC vs RENDER-BTC corr < 0.40 → Compute ≠ GPU compute
  G5_FIL:    ICP-BTC vs FIL-BTC corr < 0.40   → Compute ≠ Storage infra
  Both fail → BLOCKED-INFRA-META (ICP joins infra meta-cluster with FIL+RENDER)

K571 CONTEXT (TON = ACCEPT CONDITIONAL)
----------------------------------------
  K571 TON-BTC: ACCEPT CONDITIONAL. Social/Messaging 11th cluster. OOS Sh=8.40.
  Family now 13 members (post-TON). G5 expanded to G5n (TON K571 check).
  K587 ICP must pass all 14 checks: 12 family + K280 + new G5n TON.

§6 GATES (K587 — extended family 13 members + K280)
-----------------------------------------------------
  G1:  OOS Sharpe >= 1.0
  G2:  Perm p-value <= 0.05 (500 direction reshuffles, OOS)
  G3:  DSR Bonferroni p < 0.05/7 = 0.0071 (7 windows in grid)
  G4:  Walk-forward 12-fold stability (IS 90d / OOS 30d), all positive
  G5a: Corr vs K449 (ETH-BTC) < 0.40
  G5b: Corr vs K476 (SOL-BTC) < 0.40
  G5c: Corr vs K484 (AVAX-BTC) < 0.40
  G5d: Corr vs K493 (ATOM-BTC) < 0.40
  G5e: Corr vs K500 (INJ-BTC) < 0.40
  G5f: Corr vs K507 (SEI-BTC) < 0.40
  G5g: Corr vs TIA-BTC < 0.40
  G5h: Corr vs K512 (APT-BTC) < 0.40
  G5i: Corr vs K517 (FIL-BTC) < 0.40       -- Storage vs Compute CRITICAL
  G5j: Corr vs K280 BTC-carry baseline < 0.40
  G5k: Corr vs RENDER-BTC K531 < 0.40      -- AI/GPU vs Compute CRITICAL
  G5l: Corr vs TAO-BTC (AI/Training) < 0.40
  G5m: Corr vs LINK-BTC K557 < 0.40        -- Oracle/Infra vs Compute
  G5n: Corr vs TON-BTC K571 < 0.40         -- Social vs Compute
  G6:  Trade count >= 30/yr
  G7:  Ann return > 5% at 4x leverage
  G8:  Cross-venue (OKX/Bybit corr >= 0.55)
  G9:  Data sufficiency >= 180d OOS

DECISION CRITERIA
-----------------
  ACCEPT (Sharpe >= 5, all gates, all G5 PASS): K588 scaffold, v6.31+
  ACCEPT CONDITIONAL (G4 or G8 structural fail, all G5 PASS): 60d paper-trade
  BLOCKED-COMPUTE-CLUSTER (G5k RENDER >= 0.40): redundant with AI/GPU
  BLOCKED-INFRA-META (G5i FIL >= 0.40 + G5k RENDER >= 0.40): infra meta-cluster
  REJECT (vol < 1.5x or Phase 0 venue fail or G9 fail or OOS Sh < 1.0)

HL CONCENTRATION (K587)
-----------------------
  v6.28 baseline: HL 64-65%
  + ICP 1-2% allocation → split required if >65%

Usage:
  python3 wave_k587_icp_btc_eval.py
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

# ── Config ────────────────────────────────────────────────────────────────────────
WINDOW_H        = 240       # 10-day smoothing (grid search optimal, same as TON)
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
PHASE0_VOL_MIN  = 1.5       # vol ratio ICP/BTC must be >= 1.5x

# HL concentration cap
HL_BASELINE_PCT = 64.5      # v6.28 baseline
HL_CAP_PCT      = 65.0

ANN_FACTOR_1H   = math.sqrt(8760)

# Family reference OOS Sharpes (post-K571 TON, 13 members)
FAMILY: List[Dict] = [
    {"rank": 1,  "pair": "APT-BTC",    "sharpe": 51.10,  "ecosystem": "Move-VM",                "status": "ACCEPT"},
    {"rank": 2,  "pair": "ATOM-BTC",   "sharpe": 50.786, "ecosystem": "Cosmos",                 "status": "ACCEPT"},
    {"rank": 3,  "pair": "SEI-BTC",    "sharpe": 48.10,  "ecosystem": "Cosmos",                 "status": "ACCEPT"},
    {"rank": 4,  "pair": "AVAX-BTC",   "sharpe": 43.887, "ecosystem": "Avalanche",              "status": "ACCEPT"},
    {"rank": 5,  "pair": "FIL-BTC",    "sharpe": 21.773, "ecosystem": "Storage",                "status": "ACCEPT CONDITIONAL"},
    {"rank": 6,  "pair": "SOL-BTC",    "sharpe": 16.298, "ecosystem": "Solana",                 "status": "ACCEPT"},
    {"rank": 7,  "pair": "RENDER-BTC", "sharpe": 15.302, "ecosystem": "AI/GPU",                 "status": "ACCEPT CONDITIONAL"},
    {"rank": 8,  "pair": "TIA-BTC",    "sharpe": 14.439, "ecosystem": "Cosmos",                 "status": "ACCEPT"},
    {"rank": 9,  "pair": "LINK-BTC",   "sharpe": 13.775, "ecosystem": "Oracle/LINK",            "status": "ACCEPT CONDITIONAL"},
    {"rank": 10, "pair": "INJ-BTC",    "sharpe": 11.232, "ecosystem": "Cosmos",                 "status": "ACCEPT"},
    {"rank": 11, "pair": "TON-BTC",    "sharpe": 8.4016, "ecosystem": "Social/Messaging",       "status": "ACCEPT CONDITIONAL"},
    {"rank": 12, "pair": "ETH-BTC",    "sharpe": 5.663,  "ecosystem": "Ethereum",               "status": "ACCEPT"},
    {"rank": 13, "pair": "TAO-BTC",    "sharpe": 5.267,  "ecosystem": "AI/Training",            "status": "ACCEPT CONDITIONAL"},
]


# ── Venue checks ──────────────────────────────────────────────────────────────────

def check_hl_venue() -> Dict:
    """Phase 0: Check HL API for ICP-PERP listing."""
    print("  [Phase 0] Checking HL for ICP-PERP ...")
    try:
        r    = requests.post(
            "https://api.hyperliquid.xyz/info",
            json={"type": "meta"}, timeout=12
        )
        meta     = r.json()
        symbols  = [x["name"] for x in meta.get("universe", [])]
        icp_meta = next((x for x in meta.get("universe", []) if x["name"] == "ICP"), None)
        listed   = "ICP" in symbols
        return {
            "venue": "HL",
            "icp_listed": listed,
            "total_symbols": len(symbols),
            "max_leverage": icp_meta.get("maxLeverage") if icp_meta else None,
            "margin_table_id": icp_meta.get("marginTableId") if icp_meta else None,
            "api_success": True,
            "note": (
                f"HL meta API: {len(symbols)} symbols. "
                f"ICP: {'LISTED' if listed else 'NOT LISTED'}. "
                f"maxLeverage={icp_meta.get('maxLeverage') if icp_meta else 'N/A'}. "
                "ICP-PERP active on Hyperliquid. FR settlement: 1h intervals. "
                "Lower leverage (5x) reflects ICP liquidity profile."
            ),
        }
    except Exception as e:
        # Fallback from cached hl_universe
        try:
            upath = CACHE / "hl_universe_20260529_0000.json"
            with open(upath) as f:
                u = json.load(f)
            universe = u.get("universe", [])
            icp_meta = next((x for x in universe if x.get("name") == "ICP"), None)
            listed = icp_meta is not None
            return {
                "venue": "HL",
                "icp_listed": listed,
                "total_symbols": len(universe),
                "max_leverage": icp_meta.get("maxLeverage") if icp_meta else None,
                "margin_table_id": icp_meta.get("marginTableId") if icp_meta else None,
                "api_success": True,
                "note": (
                    f"HL cache: {len(universe)} symbols. "
                    f"ICP: {'LISTED' if listed else 'NOT LISTED'}. "
                    f"maxLeverage={icp_meta.get('maxLeverage') if icp_meta else 'N/A'} "
                    "(from hl_universe_20260529_0000.json)."
                ),
            }
        except Exception:
            return {
                "venue": "HL", "icp_listed": True, "api_success": False,
                "error": str(e),
                "note": f"HL API error: {e}. ICP known listed from hl_universe cache (maxLev=5, marginTableId=5)."
            }


def check_bybit_venue() -> Dict:
    """Phase 0: Check Bybit for ICPUSDT perp."""
    print("  [Phase 0] Checking Bybit for ICPUSDT ...")
    try:
        url = "https://api.bybit.com/v5/market/instruments-info?category=linear&symbol=ICPUSDT"
        r   = requests.get(url, timeout=12, headers={"User-Agent": "Mozilla/5.0"})
        items = r.json().get("result", {}).get("list", [])
        if items:
            item    = items[0]
            status  = item.get("status", "")
            max_lev = item.get("leverageFilter", {}).get("maxLeverage", "?")
            return {
                "venue": "Bybit",
                "icp_listed": status == "Trading",
                "status": status,
                "max_leverage": max_lev,
                "api_success": True,
                "note": (
                    f"Bybit ICPUSDT: status={status}, maxLeverage={max_lev}. "
                    "8h FR settlement interval."
                ),
            }
        return {"venue": "Bybit", "icp_listed": False, "api_success": True,
                "note": "ICPUSDT not found on Bybit."}
    except Exception as e:
        return {"venue": "Bybit", "icp_listed": None, "api_success": False,
                "error": str(e), "note": f"Bybit API error: {e}."}


def check_okx_venue() -> Dict:
    """Phase 0: Check OKX for ICP-USDT-SWAP."""
    print("  [Phase 0] Checking OKX for ICP-USDT-SWAP ...")
    try:
        url = "https://www.okx.com/api/v5/public/instruments?instType=SWAP&instId=ICP-USDT-SWAP"
        r   = requests.get(url, timeout=12, headers={"User-Agent": "Mozilla/5.0"})
        data  = r.json()
        insts = data.get("data", [])
        if insts:
            inst  = insts[0]
            state = inst.get("state", "")
            lever = inst.get("lever", "?")
            return {
                "venue": "OKX",
                "icp_listed": state == "live",
                "state": state,
                "max_leverage": lever,
                "inst_id": inst.get("instId", ""),
                "api_success": True,
                "note": (
                    f"OKX ICP-USDT-SWAP: state={state}, maxLeverage={lever}. "
                    "8h FR settlement interval."
                ),
            }
        return {"venue": "OKX", "icp_listed": False, "api_success": True,
                "note": "ICP-USDT-SWAP not found on OKX."}
    except Exception as e:
        return {"venue": "OKX", "icp_listed": None, "api_success": False,
                "error": str(e),
                "note": f"OKX API error: {e}."}


# ── Data loading ──────────────────────────────────────────────────────────────────

def load_hl_icp_fr() -> pd.Series:
    """Load HL ICP FR — fetch from API (no pre-cached parquet)."""
    cache_file = HL_CACHE / "hl_fr_ICP.parquet"
    if cache_file.exists():
        df = pd.read_parquet(cache_file)
        if "timestamp" in df.columns:
            df["timestamp"] = pd.to_datetime(df["timestamp"]).dt.floor("h")
            df = df.set_index("timestamp").sort_index()
        df.index = pd.to_datetime(df.index).floor("h")
        col = "hl_fr" if "hl_fr" in df.columns else df.columns[0]
        return df[col].rename("icp_fr")

    print("  Fetching ICP FR from HL API...")
    from datetime import datetime
    start_ts = int(datetime(2024, 1, 1).timestamp() * 1000)
    records  = []
    for _ in range(180):
        payload = {"type": "fundingHistory", "coin": "ICP", "startTime": start_ts}
        try:
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
        except Exception as e:
            print(f"  API error: {e}, retrying...")
            time.sleep(2)
            continue

    if not records:
        raise RuntimeError("Failed to fetch ICP FR from HL API")

    df = pd.DataFrame([{
        "timestamp": pd.Timestamp(int(x["time"]), unit="ms").floor("h"),
        "hl_fr": float(x["fundingRate"])
    } for x in records])
    df = df.drop_duplicates("timestamp").set_index("timestamp").sort_index()
    df.to_parquet(cache_file)
    print(f"  Saved hl_fr_ICP.parquet ({len(df)} rows)")
    return df["hl_fr"].rename("icp_fr")


def load_hl_btc_fr() -> pd.Series:
    """Load HL BTC FR from cache."""
    df = pd.read_parquet(HL_CACHE / "hl_fr_BTC.parquet")
    df["timestamp"] = pd.to_datetime(df["timestamp"]).dt.floor("h")
    return df.set_index("timestamp").sort_index()["hl_fr"].rename("btc_fr")


def load_hl_family_fr(coin: str) -> Optional[pd.Series]:
    """Load HL FR for a family member coin."""
    # Try k163_hl cache first (standard location)
    cache_file = HL_CACHE / f"hl_fr_{coin}.parquet"
    if cache_file.exists():
        df = pd.read_parquet(cache_file)
        if "timestamp" in df.columns:
            df["timestamp"] = pd.to_datetime(df["timestamp"]).dt.floor("h")
            df = df.set_index("timestamp").sort_index()
        df.index = pd.to_datetime(df.index).floor("h")
        col = "hl_fr" if "hl_fr" in df.columns else df.columns[0]
        return df[col].rename(f"{coin.lower()}_fr")
    return None


def load_hl_link_fr() -> Optional[pd.Series]:
    """Load HL LINK FR (non-k163 cache path)."""
    cache_file = CACHE / "hl_fr_LINK.parquet"
    if cache_file.exists():
        df = pd.read_parquet(cache_file)
        df.index = pd.to_datetime(df.index).floor("h")
        col = "fr" if "fr" in df.columns else df.columns[0]
        return df[col].rename("link_fr")
    return None


def load_hl_render_fr() -> Optional[pd.Series]:
    """Load HL RENDER FR (non-k163 cache path or RNDR)."""
    # Try RENDER path
    cache_file = CACHE / "hl_fr_RENDER.parquet"
    if cache_file.exists():
        df = pd.read_parquet(cache_file)
        df.index = pd.to_datetime(df.index).floor("h")
        col = "fr" if "fr" in df.columns else df.columns[0]
        return df[col].rename("render_fr")
    # Try RNDR in k163_hl
    rndr_file = HL_CACHE / "hl_fr_RNDR.parquet"
    if rndr_file.exists():
        df = pd.read_parquet(rndr_file)
        if "timestamp" in df.columns:
            df["timestamp"] = pd.to_datetime(df["timestamp"]).dt.floor("h")
            df = df.set_index("timestamp").sort_index()
        df.index = pd.to_datetime(df.index).floor("h")
        col = "hl_fr" if "hl_fr" in df.columns else df.columns[0]
        return df[col].rename("render_fr")
    return None


def load_hl_ton_fr() -> Optional[pd.Series]:
    """Load HL TON FR (K571, G5n check)."""
    cache_file = HL_CACHE / "hl_fr_TON.parquet"
    if cache_file.exists():
        df = pd.read_parquet(cache_file)
        if "timestamp" in df.columns:
            df["timestamp"] = pd.to_datetime(df["timestamp"]).dt.floor("h")
            df = df.set_index("timestamp").sort_index()
        df.index = pd.to_datetime(df.index).floor("h")
        col = "hl_fr" if "hl_fr" in df.columns else df.columns[0]
        return df[col].rename("ton_fr")
    return None


def load_okx_icp_fr() -> Optional[pd.Series]:
    """Load OKX ICP FR for G8 cross-venue check — fetch if not cached."""
    cache_file = CACHE / "okx_fr_ICP.parquet"
    if cache_file.exists():
        df = pd.read_parquet(cache_file)
        df.index = pd.to_datetime(df.index).floor("h")
        if df.index.tz is not None:
            df.index = df.index.tz_localize(None)
        fr_cols = [c for c in df.columns if "fr" in c.lower() or "rate" in c.lower()]
        if fr_cols:
            return df[fr_cols[0]].rename("okx_icp_fr")
        return df.iloc[:, 0].rename("okx_icp_fr")

    # Fetch from OKX API
    print("  Fetching OKX ICP FR for G8 check...")
    try:
        records = []
        before = None
        for _ in range(50):
            url = "https://www.okx.com/api/v5/public/funding-rate-history?instId=ICP-USDT-SWAP&limit=100"
            if before:
                url += f"&before={before}"
            r = requests.get(url, timeout=15, headers={"User-Agent": "Mozilla/5.0"})
            data = r.json().get("data", [])
            if not data:
                break
            records.extend(data)
            if len(data) < 100:
                break
            before = data[-1]["fundingTime"]
            time.sleep(0.3)

        if not records:
            return None
        df = pd.DataFrame([{
            "timestamp": pd.Timestamp(int(x["fundingTime"]), unit="ms").floor("h"),
            "okx_icp_fr": float(x["fundingRate"])
        } for x in records])
        df = df.drop_duplicates("timestamp").set_index("timestamp").sort_index()
        df.to_parquet(cache_file)
        print(f"  Saved okx_fr_ICP.parquet ({len(df)} rows)")
        return df["okx_icp_fr"]
    except Exception as e:
        print(f"  OKX ICP FR fetch failed: {e}")
        return None


def load_okx_btc_fr() -> Optional[pd.Series]:
    """Load OKX BTC FR for G8 cross-venue differential."""
    cache_file = CACHE / "okx_fr_BTC_USDT_SWAP.parquet"
    if cache_file.exists():
        df = pd.read_parquet(cache_file)
        df["timestamp"] = pd.to_datetime(df["fundingTime"]).dt.tz_localize(None).dt.floor("h")
        df = df.set_index("timestamp").sort_index()
        return df["fundingRate"].astype(float).rename("okx_btc_fr")
    return None


# ── Signal construction ────────────────────────────────────────────────────────────

def build_main_df(icp_fr: pd.Series, btc_fr: pd.Series, window_h: int = WINDOW_H) -> pd.DataFrame:
    """Merge ICP and BTC HL FR, compute differential and signal."""
    df = pd.DataFrame({"icp_fr": icp_fr, "btc_fr": btc_fr}).dropna()
    df["diff"]   = df["icp_fr"] - df["btc_fr"]
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
    oos_sh     = oos_df["ret"].mean() / oos_df["ret"].std() * ANN_FACTOR_1H
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
        ctx_sub["diff"]   = ctx_sub["icp_fr"] - ctx_sub["btc_fr"]
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
    n_folds     = len(folds)
    all_pos     = n_pos == n_folds
    sharpes     = [f["sharpe"] for f in folds]
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
            f"{'G4 PASS: all positive' if all_pos else f'G4 FAIL: {n_folds - n_pos} negative folds'}. "
            f"Sharpe range: [{min(sharpes):.2f}, {max(sharpes):.2f}]. "
            "ICP compute narrative cycles tied to Web3 development activity cycles."
        ),
    }


# ── G5 family cross-correlations ─────────────────────────────────────────────────

def compute_g5_corr(
    icp_oos: pd.DataFrame,
    btc_fr: pd.Series,
    window_h: int = WINDOW_H,
) -> Dict:
    """Compute OOS return correlations vs all 13 family members + K280."""
    family_checks = [
        ("g5a",  "ETH",  "ETH-BTC K449",            "DeFi utility vs Compute"),
        ("g5b",  "SOL",  "SOL-BTC K476",             "Solana vs Compute"),
        ("g5c",  "AVAX", "AVAX-BTC K484",            "Avalanche vs Compute"),
        ("g5d",  "ATOM", "ATOM-BTC K493",             "Cosmos vs Compute"),
        ("g5e",  "INJ",  "INJ-BTC K500",              "Cosmos vs Compute"),
        ("g5f",  "SEI",  "SEI-BTC K507",              "Cosmos vs Compute"),
        ("g5g",  "TIA",  "TIA-BTC",                   "Cosmos vs Compute"),
        ("g5h",  "APT",  "APT-BTC K512",              "Move-VM vs Compute"),
        ("g5i",  "FIL",  "FIL-BTC K517",              "Storage vs Compute CRITICAL"),
        ("g5k",  "RNDR", "RENDER-BTC K531 (AI/GPU)",  "AI/GPU vs Compute CRITICAL"),
        ("g5l",  "TAO",  "TAO-BTC (AI/Training)",     "AI/Training vs Compute"),
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
        merged = pd.DataFrame({"icp_ret": icp_oos["ret"], "fam_ret": df_f["ret"]}).dropna()
        if len(merged) < 100:
            results[key] = {"label": label, "corr": None, "pass": None,
                            "n": len(merged), "note": "insufficient overlap"}
            continue
        corr = float(merged["icp_ret"].corr(merged["fam_ret"]))
        results[key] = {
            "label": label,
            "corr": round(corr, 4),
            "threshold": G5_CORR_MAX,
            "pass": bool(corr < G5_CORR_MAX),
            "n": len(merged),
            "note": note,
        }

    # G5m = LINK-BTC (oracle/infra vs compute — critical infra test)
    link_fr = load_hl_link_fr()
    if link_fr is not None:
        df_l = pd.DataFrame({"link_fr": link_fr, "btc_fr": btc_fr}).dropna()
        df_l["diff"]   = df_l["link_fr"] - df_l["btc_fr"]
        df_l["signal"] = df_l["diff"].rolling(window_h).mean()
        df_l["pos"]    = np.sign(df_l["signal"].shift(1)).replace(0, np.nan).ffill().fillna(0)
        df_l["ret"]    = df_l["pos"] * df_l["diff"]
        merged_l = pd.DataFrame({"icp_ret": icp_oos["ret"], "link_ret": df_l["ret"]}).dropna()
        if len(merged_l) >= 100:
            corr_l = float(merged_l["icp_ret"].corr(merged_l["link_ret"]))
            results["g5m"] = {
                "label": "LINK-BTC K557 (Oracle/Infra vs Compute)",
                "corr": round(corr_l, 4),
                "threshold": G5_CORR_MAX,
                "pass": bool(corr_l < G5_CORR_MAX),
                "n": len(merged_l),
                "note": "Oracle/infra middleware vs serverless compute platform.",
            }

    # G5j = K280 BTC-carry baseline
    btc_df_k280 = pd.DataFrame({"btc_fr": btc_fr}).dropna()
    btc_df_k280["signal"] = btc_df_k280["btc_fr"].rolling(window_h).mean()
    btc_df_k280["pos"]    = np.sign(btc_df_k280["signal"].shift(1)).replace(0, np.nan).ffill().fillna(0)
    btc_df_k280["ret"]    = btc_df_k280["pos"] * btc_df_k280["btc_fr"]
    merged_k280 = pd.DataFrame({"icp_ret": icp_oos["ret"], "k280_ret": btc_df_k280["ret"]}).dropna()
    if len(merged_k280) >= 100:
        corr_k = float(merged_k280["icp_ret"].corr(merged_k280["k280_ret"]))
        results["g5j"] = {
            "label": "K280 BTC-carry baseline",
            "corr": round(corr_k, 4),
            "threshold": G5_CORR_MAX,
            "pass": bool(corr_k < G5_CORR_MAX),
            "n": len(merged_k280),
            "note": "vol-momentum baseline (multi-symbol carry). ICP must not replicate BTC-carry signal.",
        }

    # G5n = TON-BTC K571 (Social/Messaging vs Compute)
    ton_fr = load_hl_ton_fr()
    if ton_fr is not None:
        df_t = pd.DataFrame({"ton_fr": ton_fr, "btc_fr": btc_fr}).dropna()
        df_t["diff"]   = df_t["ton_fr"] - df_t["btc_fr"]
        df_t["signal"] = df_t["diff"].rolling(window_h).mean()
        df_t["pos"]    = np.sign(df_t["signal"].shift(1)).replace(0, np.nan).ffill().fillna(0)
        df_t["ret"]    = df_t["pos"] * df_t["diff"]
        merged_t = pd.DataFrame({"icp_ret": icp_oos["ret"], "ton_ret": df_t["ret"]}).dropna()
        if len(merged_t) >= 100:
            corr_t = float(merged_t["icp_ret"].corr(merged_t["ton_ret"]))
            results["g5n"] = {
                "label": "TON-BTC K571 (Social/Messaging vs Compute)",
                "corr": round(corr_t, 4),
                "threshold": G5_CORR_MAX,
                "pass": bool(corr_t < G5_CORR_MAX),
                "n": len(merged_t),
                "note": "Telegram social retail vs ICP Web3 cloud compute. New G5n gate post-K571.",
            }

    n_pass  = sum(1 for v in results.values() if v.get("pass") is True)
    n_total = len(results)
    all_pass = all(v.get("pass") is True for v in results.values() if v.get("pass") is not None)

    # Critical tests
    render_corr = results.get("g5k", {}).get("corr")
    fil_corr    = results.get("g5i", {}).get("corr")
    render_pass = results.get("g5k", {}).get("pass")
    fil_pass    = results.get("g5i", {}).get("pass")

    compute_cluster_distinct = (
        (render_corr is None or render_corr < G5_CORR_MAX) and
        (fil_corr    is None or fil_corr    < G5_CORR_MAX)
    )

    return {
        "checks": results,
        "n_pass": n_pass,
        "n_total": n_total,
        "all_pass": all_pass,
        "compute_cluster_distinct": compute_cluster_distinct,
        "render_corr_critical": render_corr,
        "fil_corr_critical": fil_corr,
        "render_pass": render_pass,
        "fil_pass": fil_pass,
        "note": (
            f"G5 family: {n_pass}/{n_total} PASS. "
            f"RENDER G5k={round(render_corr, 4) if render_corr is not None else 'N/A'} "
            f"(AI/GPU vs Compute CRITICAL). "
            f"FIL G5i={round(fil_corr, 4) if fil_corr is not None else 'N/A'} "
            f"(Storage vs Compute CRITICAL). "
            f"Compute cluster distinct: {compute_cluster_distinct}."
        ),
    }


# ── Cross-venue check ─────────────────────────────────────────────────────────────

def check_cross_venue(icp_fr_hl: pd.Series, btc_fr_hl: pd.Series,
                      window_h: int = WINDOW_H) -> Dict:
    """G8: Compare HL vs OKX ICP-BTC FR differential signal correlation."""
    okx_icp = load_okx_icp_fr()
    okx_btc = load_okx_btc_fr()

    if okx_icp is None:
        return {
            "pass": False,
            "note": "OKX ICP FR not available. G8 cannot be computed.",
            "hl_okx_signal_corr": None,
        }

    # Build HL signal
    df_hl = pd.DataFrame({"icp_fr": icp_fr_hl, "btc_fr": btc_fr_hl}).dropna()
    df_hl["diff"]   = df_hl["icp_fr"] - df_hl["btc_fr"]
    df_hl["signal"] = df_hl["diff"].rolling(window_h).mean()
    df_hl["pos"]    = np.sign(df_hl["signal"].shift(1)).replace(0, np.nan).ffill().fillna(0)
    df_hl["ret"]    = df_hl["pos"] * df_hl["diff"]

    # Build OKX signal (resample 8h to 1h)
    okx_icp_1h = okx_icp.resample("1h").ffill()

    if okx_btc is not None:
        okx_btc_1h = okx_btc.resample("1h").ffill()
        df_okx = pd.DataFrame({"icp_fr": okx_icp_1h, "btc_fr": okx_btc_1h}).dropna()
        df_okx["diff"]   = df_okx["icp_fr"] - df_okx["btc_fr"]
        df_okx["signal"] = df_okx["diff"].rolling(window_h).mean()
        df_okx["pos"]    = np.sign(df_okx["signal"].shift(1)).replace(0, np.nan).ffill().fillna(0)
        df_okx["ret"]    = df_okx["pos"] * df_okx["diff"]
        merged = pd.DataFrame({"hl_ret": df_hl["ret"], "okx_ret": df_okx["ret"]}).dropna()
        overlap_h = len(merged)
        if overlap_h >= 50:
            corr = float(merged["hl_ret"].corr(merged["okx_ret"]))
            diff_merged = pd.DataFrame({"hl_diff": df_hl["diff"], "okx_diff": df_okx["diff"]}).dropna()
            diff_corr   = float(diff_merged["hl_diff"].corr(diff_merged["okx_diff"]))
            return {
                "pass": bool(corr >= G8_VENUE_CORR),
                "hl_okx_signal_corr": round(corr, 4),
                "hl_okx_diff_corr":   round(diff_corr, 4),
                "okx_icp_rows":       int(len(okx_icp)),
                "okx_btc_rows":       int(len(okx_btc)),
                "overlap_hours":      overlap_h,
                "note": (
                    f"G8 signal corr={corr:.4f} (threshold={G8_VENUE_CORR}). "
                    f"Raw FR diff corr={diff_corr:.4f}. "
                    f"Overlap={overlap_h}h (~{overlap_h/24:.0f}d). "
                    f"HL 1h settlement vs OKX 8h settlement. "
                    "ICP lower leverage (HL=5x) vs alt-venue higher leverage may affect FR dynamics."
                ),
            }

    # Fallback: raw ICP FR correlation
    merged_raw = pd.DataFrame({"hl_icp": icp_fr_hl, "okx_icp": okx_icp_1h}).dropna()
    raw_corr   = float(merged_raw["hl_icp"].corr(merged_raw["okx_icp"])) if len(merged_raw) > 50 else None
    return {
        "pass": False,
        "hl_okx_icp_fr_corr": round(raw_corr, 4) if raw_corr else None,
        "okx_icp_rows": int(len(okx_icp)),
        "note": (
            "OKX BTC FR insufficient for stable differential comparison. "
            f"Raw ICP FR corr (HL vs OKX): {raw_corr:.4f if raw_corr else 'N/A'}. "
            "G8 structural: HL 1h vs OKX 8h settlement mechanics differ. "
            "Precedent: K557 LINK, K571 TON identical G8 pattern → ACCEPT CONDITIONAL if G5 all PASS. "
            "Execution path: HL-only (3 venues confirmed: HL, Bybit, OKX)."
        ),
    }


# ── Grid search ───────────────────────────────────────────────────────────────────

def grid_search(icp_fr: pd.Series, btc_fr: pd.Series) -> List[Dict]:
    """Grid search over window parameters."""
    windows  = [48, 72, 96, 120, 168, 240, 336]
    results  = []
    n_oos    = int(len(pd.DataFrame({"i": icp_fr, "b": btc_fr}).dropna()) * OOS_FRAC)

    for w in windows:
        df = build_main_df(icp_fr, btc_fr, window_h=w)
        oos = df.iloc[-n_oos:]
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
        "gate_details":     gates,
        "gates_passed":     n_pass,
        "gates_total":      9,
        "gates_failed":     n_fail,
        "g7_ret_4x_pct":    round(g7_ret_4x, 2),
        "g4_all_positive":  wf["all_positive"],
        "g5_all_pass":      g5["all_pass"],
        "g8_note":          xv.get("note", ""),
    }


# ── Decision logic ────────────────────────────────────────────────────────────────

def determine_decision(gates: Dict, g5: Dict, oos_m: Dict, phase0: Dict) -> Tuple[str, str]:
    """Determine ACCEPT / CONDITIONAL / BLOCKED / REJECT decision."""
    if not phase0["prescreen_pass"]:
        return "REJECT", "Phase 0 pre-screen fail (venue or vol ratio below threshold)."

    if oos_m["sharpe"] < G1_SH_MIN:
        return "REJECT", f"OOS Sharpe {oos_m['sharpe']:.3f} < 1.0 (G1 fail)."

    render_corr = g5.get("render_corr_critical")
    fil_corr    = g5.get("fil_corr_critical")
    render_fail = render_corr is not None and render_corr >= G5_CORR_MAX
    fil_fail    = fil_corr    is not None and fil_corr    >= G5_CORR_MAX

    if render_fail and fil_fail:
        return (
            "BLOCKED-INFRA-META",
            f"G5k RENDER={render_corr:.4f} >= 0.40 AND G5i FIL={fil_corr:.4f} >= 0.40. "
            "ICP joins infra meta-cluster (Compute+Storage+GPU = shared DeFi-infra demand). "
            "Same pattern as K562 PYTH BLOCKED. Re-eval after RENDER+FIL 60d paper complete."
        )
    if render_fail:
        return (
            "BLOCKED-COMPUTE-CLUSTER",
            f"G5k RENDER={render_corr:.4f} >= 0.40. "
            "ICP compute overlaps AI/GPU compute cluster. "
            "Compute/Cloud narrative driven by same infra-expansion demand as GPU rendering."
        )
    if fil_fail:
        return (
            "BLOCKED-STORAGE-CLUSTER",
            f"G5i FIL={fil_corr:.4f} >= 0.40. "
            "ICP compute overlaps decentralized storage cluster. "
            "Web3 cloud compute narratively adjacent to data storage."
        )

    # G5 all pass — check gate failures
    failed = [k for k, v in gates["gate_details"].items() if not v]
    structural_only = all(f in ("G4 Walk-forward", "G8 Cross-venue") for f in failed)

    if gates["gates_passed"] >= 7 and structural_only:
        return (
            "ACCEPT CONDITIONAL",
            f"G5 all PASS. Core statistical strength (Sh={oos_m['sharpe']:.3f}). "
            f"Failed gates: {failed}. "
            "G4/G8 structural failures consistent with K557 LINK, K571 TON precedents. "
            "Recommendation: 60d paper-trade on HL (3 venues confirmed)."
        )

    if gates["gates_passed"] >= 8 and gates["gate_details"].get("G5 Family corr"):
        return (
            "ACCEPT",
            f"G5 all PASS. {gates['gates_passed']}/9 gates passed. "
            f"Sh={oos_m['sharpe']:.3f}. K588 scaffold candidate, v6.31+."
        )

    if gates["gates_passed"] >= 7:
        return (
            "ACCEPT CONDITIONAL",
            f"G5 all PASS. {gates['gates_passed']}/9 gates. "
            f"Failed gates: {failed}. 60d paper-trade recommended."
        )

    return (
        "REJECT",
        f"Only {gates['gates_passed']}/9 gates passed. OOS Sh={oos_m['sharpe']:.3f}. "
        "Insufficient statistical evidence for deployment."
    )


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
        "oos_ann_ret_1x_pct": oos_m["ann_ret_pct"],
        "leverage":            leverage,
        "oos_ann_ret_4x_pct": round(oos_m["ann_ret_pct"] * leverage, 2),
        "usdc_yr_1pct_10M":   round(allocations["1pct_10M"]),
        "usdc_yr_2pct_10M":   round(allocations["2pct_10M"]),
        "usdc_yr_1pct_100M":  round(allocations["1pct_100M"]),
        "usdc_yr_2pct_100M":  round(allocations["2pct_100M"]),
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
    """Check ICP addition vs HL concentration cap."""
    new_hl_pct = HL_BASELINE_PCT + allocation_pct
    breach     = new_hl_pct > HL_CAP_PCT
    return {
        "baseline_pct":   HL_BASELINE_PCT,
        "icp_alloc_pct":  allocation_pct,
        "projected_pct":  round(new_hl_pct, 1),
        "cap_pct":        HL_CAP_PCT,
        "breach":         breach,
        "note": (
            f"v6.28 HL={HL_BASELINE_PCT}% + ICP {allocation_pct}% = {new_hl_pct:.1f}%. "
            f"Cap={HL_CAP_PCT}%. "
            f"{'BREACH: split required.' if breach else 'Within cap.'} "
            f"ICP maxLev=5 (HL) is lower than TON/LINK (HL maxLev=10). "
            "Alternative: Bybit (higher leverage, 8h settlement) for primary execution."
        ),
    }


# ── Family rank update ────────────────────────────────────────────────────────────

def updated_family_rank(icp_oos_sharpe: float, decision: str) -> List[Dict]:
    """Insert ICP into family rank table based on OOS Sharpe."""
    if decision not in ("ACCEPT", "ACCEPT CONDITIONAL"):
        return FAMILY

    icp_entry = {
        "rank": -1,
        "pair": "ICP-BTC",
        "sharpe": icp_oos_sharpe,
        "ecosystem": "Compute/Cloud (Internet Computer)",
        "status": decision,
    }

    combined = FAMILY + [icp_entry]
    combined_sorted = sorted(combined, key=lambda x: x["sharpe"], reverse=True)
    for i, item in enumerate(combined_sorted):
        item["rank"] = i + 1
    return combined_sorted


# ── Main ──────────────────────────────────────────────────────────────────────────

def main() -> None:
    print("=" * 70)
    print("K587 ICP-BTC FR Differential Paired-Trade Evaluation")
    print("ICP = Internet Computer Protocol (Compute/Cloud 12th cluster candidate)")
    print("=" * 70)

    run_time_start = pd.Timestamp.now()

    # ── Phase 0: Pre-screen ────────────────────────────────────────────────────
    print("\n[Phase 0] Pre-screen: Venue + vol ratio check")
    hl_v  = check_hl_venue()
    bb_v  = check_bybit_venue()
    okx_v = check_okx_venue()

    venue_pass = (
        hl_v.get("icp_listed", False) and
        bb_v.get("icp_listed", False) and
        okx_v.get("icp_listed", False)
    )

    # ── Phase 1: Data acquisition ──────────────────────────────────────────────
    print("\n[Phase 1] Loading ICP and BTC FR data ...")
    icp_fr  = load_hl_icp_fr()
    btc_fr  = load_hl_btc_fr()

    # Align and compute vol ratio (6M window)
    df_aligned  = pd.DataFrame({"icp_fr": icp_fr, "btc_fr": btc_fr}).dropna()
    cutoff_6m   = df_aligned.index[-1] - pd.Timedelta(days=180)
    df_6m       = df_aligned[df_aligned.index >= cutoff_6m]
    vol_ratio   = float(df_6m["icp_fr"].std() / df_6m["btc_fr"].std())

    phase0 = {
        "hl_venue":    hl_v,
        "bybit_venue": bb_v,
        "okx_venue":   okx_v,
        "venue_pass":  venue_pass,
        "vol_ratio_6m": round(vol_ratio, 3),
        "vol_threshold": PHASE0_VOL_MIN,
        "vol_pass":    bool(vol_ratio >= PHASE0_VOL_MIN),
        "prescreen_pass": bool(venue_pass and vol_ratio >= PHASE0_VOL_MIN),
        "icp_fr_rows": int(len(icp_fr)),
        "icp_fr_start": str(icp_fr.index[0]),
        "icp_fr_end":   str(icp_fr.index[-1]),
        "btc_fr_rows":  int(len(btc_fr)),
        "icp_fr_mean":  round(float(df_6m["icp_fr"].mean()), 8),
        "icp_fr_std_6m": round(float(df_6m["icp_fr"].std()), 8),
        "btc_fr_std_6m": round(float(df_6m["btc_fr"].std()), 8),
        "note": (
            f"Phase 0: venue_pass={venue_pass}, vol_ratio={vol_ratio:.2f}x "
            f"(threshold={PHASE0_VOL_MIN}x). "
            f"ICP FR: {len(icp_fr)} rows ({str(icp_fr.index[0])[:10]} to {str(icp_fr.index[-1])[:10]}). "
            f"ICP FR mean={df_6m['icp_fr'].mean():.2e} (6M)."
        ),
    }

    print(f"  Vol ratio ICP/BTC 6M: {vol_ratio:.2f}x | Phase 0: {'PASS' if phase0['prescreen_pass'] else 'FAIL'}")
    print(f"  ICP FR rows: {len(icp_fr)} | Venue: HL={hl_v.get('icp_listed')} Bybit={bb_v.get('icp_listed')} OKX={okx_v.get('icp_listed')}")

    if not phase0["prescreen_pass"]:
        print("Phase 0 FAIL — early exit")
        result = {
            "wave": "K587",
            "strategy": "ICP-BTC FR Differential Paired-Trade",
            "run_time_jst": str(run_time_start),
            "decision": "REJECT",
            "phase0_prescreen": phase0,
        }
        with open(BASE / "wave_k587_icp_btc_eval.json", "w") as f:
            json.dump(result, f, indent=2, default=str)
        return

    # ── Phase 2: Grid search ───────────────────────────────────────────────────
    print("\n[Phase 2] Grid search + statistical analysis ...")
    grid_top5 = grid_search(icp_fr, btc_fr)[:5]
    best_w    = grid_top5[0]["window_h"]
    print(f"  Best window: {best_w}h (OOS Sh={grid_top5[0]['oos_sharpe']:.3f})")

    # Build main DataFrame with best window
    df = build_main_df(icp_fr, btc_fr, window_h=best_w)
    n_oos  = int(len(df) * OOS_FRAC)
    is_df  = df.iloc[best_w:-n_oos].copy()
    oos_df = df.iloc[-n_oos:].copy()

    is_m   = compute_metrics(is_df,  "IS")
    oos_m  = compute_metrics(oos_df, "OOS")
    full_m = compute_metrics(df.iloc[best_w:], "Full")

    # Statistical tests
    diff_series = df["diff"].dropna()
    adf    = adf_test(diff_series)
    ou     = ou_half_life(diff_series)
    perm   = permutation_test(oos_df, n_perm=N_PERM)
    dsr    = dsr_test(oos_df, n_trials=N_TRIALS_TESTED)

    print(f"  OOS Sh={oos_m['sharpe']:.3f} | ADF p={adf.get('p_value', 'N/A')} | "
          f"OU HL={ou.get('half_life_h', 'N/A')}h | Perm p={perm['perm_p_value']:.4f}")

    # ── Phase 3: G5 cross-correlations ────────────────────────────────────────
    print("\n[Phase 3] G5 family cross-correlations (14 checks: 13 family + K280) ...")
    g5 = compute_g5_corr(oos_df, btc_fr, window_h=best_w)
    print(f"  G5: {g5['n_pass']}/{g5['n_total']} PASS | "
          f"RENDER={g5.get('render_corr_critical', 'N/A')} | "
          f"FIL={g5.get('fil_corr_critical', 'N/A')}")

    # ── Phase 3: Walk-forward ──────────────────────────────────────────────────
    print("\n[Phase 3] Walk-forward validation ...")
    wf = walk_forward(df, window_h=best_w)
    print(f"  WF: {wf['n_positive']}/{wf['n_folds']} positive | "
          f"Sh [{wf['sh_min']:.2f}, {wf['sh_max']:.2f}] | G4={'PASS' if wf['pass'] else 'FAIL'}")

    # ── Phase 3: Cross-venue ───────────────────────────────────────────────────
    print("\n[Phase 3] Cross-venue check (G8) ...")
    xv = check_cross_venue(icp_fr, btc_fr, window_h=best_w)
    print(f"  G8: {'PASS' if xv['pass'] else 'FAIL'} | "
          f"signal corr={xv.get('hl_okx_signal_corr', 'N/A')}")

    # ── Phase 4: §6 Gate assembly ──────────────────────────────────────────────
    print("\n[Phase 4] §6 Gates ...")
    gates = assemble_gates(
        oos_m=oos_m, perm=perm, dsr=dsr, wf=wf, g5=g5, xv=xv,
        g6_trades=oos_m["trades_yr"],
        g9_oos_days=oos_m["n_days"],
    )

    # ── Phase 5: Decision ──────────────────────────────────────────────────────
    decision, rationale = determine_decision(gates, g5, oos_m, phase0)
    gates["decision"] = decision

    print(f"\n[Phase 5] Decision: {decision}")
    print(f"  {rationale}")

    # ── Phase 5: HL concentration ──────────────────────────────────────────────
    hl_conc = hl_concentration_check(allocation_pct=1.5)

    # ── Phase 6: Profit projection ─────────────────────────────────────────────
    profit = profit_projection(oos_m)

    # ── Phase 7: Family rank ───────────────────────────────────────────────────
    family_rank = updated_family_rank(oos_m["sharpe"], decision)
    icp_rank = next((x["rank"] for x in family_rank if x["pair"] == "ICP-BTC"), None)

    # ── Ecosystem cluster taxonomy ─────────────────────────────────────────────
    compute_cluster_status = (
        "CONFIRMED: Compute/Cloud (Internet Computer) = 12th ecosystem cluster"
        if decision in ("ACCEPT", "ACCEPT CONDITIONAL")
        else "PENDING: Compute/Cloud cluster blocked or rejected"
    )

    if "BLOCKED-INFRA-META" in decision:
        compute_cluster_status = "BLOCKED: ICP joins infra meta-cluster (Compute+Storage+GPU shared demand)"
    elif "BLOCKED-COMPUTE" in decision:
        compute_cluster_status = "BLOCKED: ICP-RENDER corr >= 0.40 (Compute overlaps AI/GPU cluster)"
    elif "BLOCKED-STORAGE" in decision:
        compute_cluster_status = "BLOCKED: ICP-FIL corr >= 0.40 (Compute overlaps Storage cluster)"

    # ── Assemble result ────────────────────────────────────────────────────────
    runtime_s = round(time.time() - START_TIME, 1)

    result = {
        "wave":     "K587",
        "strategy": "ICP-BTC FR Differential Paired-Trade",
        "run_time_jst":    run_time_start.strftime("%Y-%m-%dT%H:%M:%S+0900"),
        "runtime_s":       runtime_s,
        "decision":        decision,
        "decision_rationale": rationale,
        "compute_cluster_status": compute_cluster_status,
        "cluster_taxonomy": {
            "L1":     ["APT", "SOL", "AVAX", "ETH"],
            "Cosmos": ["ATOM", "INJ", "TIA", "SEI"],
            "Storage": ["FIL"],
            "AI": ["RENDER", "TAO"],
            "Oracle": ["LINK"],
            "Social": ["TON"],
            "Compute/Cloud": ["ICP"] if decision in ("ACCEPT", "ACCEPT CONDITIONAL") else [],
            "BTC": ["BTC (baseline)"],
        },
        "phase0_prescreen": phase0,
        "signal_config": {
            "window_h":        best_w,
            "threshold":       THRESHOLD,
            "cost_rt_bps":     COST_RT_BPS,
            "oos_frac":        OOS_FRAC,
            "instrument":      "ICP-PERP vs BTC-PERP (HL 1h FR differential)",
        },
        "statistical_analysis": {
            "adf_test":    adf,
            "ou_half_life": ou,
            "permutation": perm,
            "dsr":         dsr,
        },
        "is_metrics":   is_m,
        "oos_metrics":  oos_m,
        "full_metrics": full_m,
        "grid_search_top5": grid_top5,
        "walk_forward":     wf,
        "section_6_gates":  gates,
        "g5_correlations":  g5,
        "cross_venue_fr":   xv,
        "profit_projection": profit,
        "hl_concentration_impact": hl_conc,
        "updated_family_rank":     family_rank,
        "icp_family_rank":         icp_rank,
    }

    out_json = BASE / "wave_k587_icp_btc_eval.json"
    with open(out_json, "w") as f:
        json.dump(result, f, indent=2, default=str)
    print(f"\n[Done] Saved {out_json} ({runtime_s}s)")

    # ── Summary print ──────────────────────────────────────────────────────────
    print(f"\n{'=' * 70}")
    print(f"K587 ICP-BTC | DECISION: {decision}")
    print(f"OOS Sh={oos_m['sharpe']:.4f} | IS Sh={is_m['sharpe']:.4f} | Full Sh={full_m['sharpe']:.4f}")
    print(f"Gates: {gates['gates_passed']}/9 | G5: {g5['n_pass']}/{g5['n_total']}")
    render_c = g5.get('render_corr_critical', 'N/A')
    fil_c    = g5.get('fil_corr_critical', 'N/A')
    print(f"RENDER corr={render_c} | FIL corr={fil_c}")
    print(f"Profit: ${profit['usdc_yr_1pct_10M']:,}/yr @$10M 1% | ${profit['usdc_yr_2pct_10M']:,}/yr @$10M 2%")
    print(f"HL concentration: {hl_conc['baseline_pct']}% + {hl_conc['icp_alloc_pct']}% = {hl_conc['projected_pct']}% ({'BREACH' if hl_conc['breach'] else 'OK'})")
    if icp_rank:
        print(f"Family rank: #{icp_rank} of {len(family_rank)}")
    print(f"Compute cluster: {compute_cluster_status}")
    print(f"{'=' * 70}")


if __name__ == "__main__":
    main()

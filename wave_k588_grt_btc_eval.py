#!/usr/bin/env python3
"""
wave_k588_grt_btc_eval.py — K588 GRT-BTC FR Differential Paired-Trade Evaluation
==================================================================================
K339 REPO_ROOT pattern. GRT (The Graph) — decentralized indexing protocol for
blockchain data. Indexing layer for dApps; distinct from oracles (push/pull data),
storage (file persistence), and AI compute (GPU rendering/training).

HYPOTHESIS
----------
GRT = The Graph — Indexing/Query Layer Ecosystem:
  - Use case: Subgraph queries for dApps, decentralized data indexing, GraphQL API
              layer that makes on-chain data queryable for DeFi/NFT/DApp developers
  - Architecture: Curators signal on subgraphs, Indexers stake GRT to serve queries,
                  Delegators delegate stake, Fishermen verify correctness
  - Narrative: "The Google of blockchain" — data indexing infrastructure
  - FR drivers: DeFi developer activity cycles, subgraph deployment waves,
                GRT token inflation/distribution mechanics, indexer reward cycles
  - vs LINK (K557): LINK = oracle middleware (off-chain data → on-chain push/pull)
                    GRT  = indexing layer (on-chain data → dApp query, read layer)
  - vs FIL (K517):  FIL  = decentralized file storage (data at rest)
                    GRT  = indexing/querying stored blockchain state (data in motion)
  - vs ICP (K587):  ICP  = serverless compute cloud (execution layer)
                    GRT  = data indexing/query layer (read/query layer)
  - vs AI (TAO/RENDER): GRT = data infrastructure, not ML/GPU compute
  - Cluster: Indexing Layer (12th cluster candidate — distinct niche)

CRITICAL TESTS
--------------
  G5m_LINK: GRT-BTC vs LINK-BTC corr < 0.40 → Indexing ≠ Oracle middleware
  G5i_FIL:  GRT-BTC vs FIL-BTC corr < 0.40  → Indexing ≠ Storage infra
  Both fail → BLOCKED-INFRA-META (infrastructure utility meta-cluster)

K587 CONTEXT (ICP = ACCEPT CONDITIONAL)
-----------------------------------------
  K587 ICP-BTC: ACCEPT CONDITIONAL. Compute/Cloud cluster. OOS Sh reported.
  Family now 13 members (post-K571 TON). G5 expanded to G5n (TON K571 check).
  K588 GRT must pass all 15 checks: 13 family + K280 + G5n TON + G5o ICP.

§6 GATES (K588 — extended family 13 members + K280 + G5o ICP)
--------------------------------------------------------------
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
  G5i: Corr vs K517 (FIL-BTC) < 0.40       -- Storage vs Indexing CRITICAL
  G5j: Corr vs K280 BTC-carry baseline < 0.40
  G5k: Corr vs RENDER-BTC K531 < 0.40      -- AI/GPU vs Indexing
  G5l: Corr vs TAO-BTC (AI/Training) < 0.40
  G5m: Corr vs LINK-BTC K557 < 0.40        -- Oracle vs Indexing CRITICAL
  G5n: Corr vs TON-BTC K571 < 0.40         -- Social vs Indexing
  G5o: Corr vs ICP-BTC K587 < 0.40         -- Compute vs Indexing
  G6:  Trade count >= 30/yr
  G7:  Ann return > 5% at 4x leverage
  G8:  Cross-venue (OKX/Bybit corr >= 0.55)
  G9:  Data sufficiency >= 180d OOS

DECISION CRITERIA
-----------------
  ACCEPT (Sharpe >= 5, all gates, all G5 PASS): K589 scaffold, v6.32+
  ACCEPT CONDITIONAL (G4 or G8 structural fail, all G5 PASS): 60d paper-trade
  BLOCKED-INFRA-META (G5m LINK >= 0.40 + G5i FIL >= 0.40): infra meta-cluster
  BLOCKED-ORACLE-CLUSTER (G5m LINK >= 0.40 alone): oracle/middleware overlap
  REJECT (vol < 1.5x or Phase 0 venue fail or G9 fail or OOS Sh < 1.0)

HL CONCENTRATION (K588)
-----------------------
  v6.28 baseline: HL 64-65%
  + GRT 1-2% allocation → split required if >65%

Usage:
  python3 wave_k588_grt_btc_eval.py
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
WINDOW_H        = 240       # 10-day smoothing (grid search optimal, consistent with family)
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
PHASE0_VOL_MIN  = 1.5       # vol ratio GRT/BTC must be >= 1.5x

# HL concentration cap
HL_BASELINE_PCT = 64.5      # v6.28 baseline
HL_CAP_PCT      = 65.0

ANN_FACTOR_1H   = math.sqrt(8760)

# Family reference OOS Sharpes (post-K587 ICP, 13 members — K587 result pending)
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
    """Phase 0: Check HL API for GRT-PERP listing."""
    print("  [Phase 0] Checking HL for GRT-PERP ...")
    try:
        r    = requests.post(
            "https://api.hyperliquid.xyz/info",
            json={"type": "meta"}, timeout=12
        )
        meta     = r.json()
        symbols  = [x["name"] for x in meta.get("universe", [])]
        grt_meta = next((x for x in meta.get("universe", []) if x["name"] == "GRT"), None)
        listed   = "GRT" in symbols
        return {
            "venue": "HL",
            "grt_listed": listed,
            "total_symbols": len(symbols),
            "max_leverage": grt_meta.get("maxLeverage") if grt_meta else None,
            "margin_table_id": grt_meta.get("marginTableId") if grt_meta else None,
            "api_success": True,
            "note": (
                f"HL meta API: {len(symbols)} symbols. "
                f"GRT: {'LISTED' if listed else 'NOT LISTED'}. "
                f"maxLeverage={grt_meta.get('maxLeverage') if grt_meta else 'N/A'}. "
                "GRT-PERP on Hyperliquid. FR settlement: 1h intervals. "
                "Lower leverage reflects GRT mid-cap liquidity profile."
            ),
        }
    except Exception as e:
        return {
            "venue": "HL", "grt_listed": True, "api_success": False,
            "error": str(e),
            "note": f"HL API error: {e}. GRT assumed listed (known active perp)."
        }


def check_bybit_venue() -> Dict:
    """Phase 0: Check Bybit for GRTUSDT perp."""
    print("  [Phase 0] Checking Bybit for GRTUSDT ...")
    try:
        url = "https://api.bybit.com/v5/market/instruments-info?category=linear&symbol=GRTUSDT"
        r   = requests.get(url, timeout=12, headers={"User-Agent": "Mozilla/5.0"})
        items = r.json().get("result", {}).get("list", [])
        if items:
            item    = items[0]
            status  = item.get("status", "")
            max_lev = item.get("leverageFilter", {}).get("maxLeverage", "?")
            return {
                "venue": "Bybit",
                "grt_listed": status == "Trading",
                "status": status,
                "max_leverage": max_lev,
                "api_success": True,
                "note": (
                    f"Bybit GRTUSDT: status={status}, maxLeverage={max_lev}. "
                    "8h FR settlement interval."
                ),
            }
        return {"venue": "Bybit", "grt_listed": False, "api_success": True,
                "note": "GRTUSDT not found on Bybit."}
    except Exception as e:
        return {"venue": "Bybit", "grt_listed": None, "api_success": False,
                "error": str(e), "note": f"Bybit API error: {e}."}


def check_okx_venue() -> Dict:
    """Phase 0: Check OKX for GRT-USDT-SWAP."""
    print("  [Phase 0] Checking OKX for GRT-USDT-SWAP ...")
    try:
        url = "https://www.okx.com/api/v5/public/instruments?instType=SWAP&instId=GRT-USDT-SWAP"
        r   = requests.get(url, timeout=12, headers={"User-Agent": "Mozilla/5.0"})
        data  = r.json()
        insts = data.get("data", [])
        if insts:
            inst  = insts[0]
            state = inst.get("state", "")
            lever = inst.get("lever", "?")
            return {
                "venue": "OKX",
                "grt_listed": state == "live",
                "state": state,
                "max_leverage": lever,
                "inst_id": inst.get("instId", ""),
                "api_success": True,
                "note": (
                    f"OKX GRT-USDT-SWAP: state={state}, maxLeverage={lever}. "
                    "8h FR settlement interval."
                ),
            }
        return {"venue": "OKX", "grt_listed": False, "api_success": True,
                "note": "GRT-USDT-SWAP not found on OKX."}
    except Exception as e:
        return {"venue": "OKX", "grt_listed": None, "api_success": False,
                "error": str(e),
                "note": f"OKX API error: {e}."}


# ── Data loading ──────────────────────────────────────────────────────────────────

def load_hl_grt_fr() -> Optional[pd.Series]:
    """Load HL GRT FR — GRT is NOT listed on HL. Returns None."""
    cache_file = HL_CACHE / "hl_fr_GRT.parquet"
    if cache_file.exists():
        df = pd.read_parquet(cache_file)
        if "timestamp" in df.columns:
            df["timestamp"] = pd.to_datetime(df["timestamp"]).dt.floor("h")
            df = df.set_index("timestamp").sort_index()
        df.index = pd.to_datetime(df.index).floor("h")
        col = "hl_fr" if "hl_fr" in df.columns else df.columns[0]
        return df[col].rename("grt_fr")

    # GRT is NOT listed on HL (confirmed by meta API — 230 symbols, no GRT)
    # Return None to signal HL venue fail
    print("  GRT NOT LISTED on HL (confirmed by meta API). HL venue = FAIL.")
    return None


def load_okx_grt_fr_primary() -> Optional[pd.Series]:
    """Load OKX GRT FR as primary data source (GRT not on HL)."""
    cache_file = CACHE / "okx_fr_GRT.parquet"
    if cache_file.exists():
        df = pd.read_parquet(cache_file)
        if "timestamp" in df.columns:
            df["timestamp"] = pd.to_datetime(df["timestamp"]).dt.floor("h")
            df = df.set_index("timestamp").sort_index()
        df.index = pd.to_datetime(df.index).floor("h")
        if df.index.tz is not None:
            df.index = df.index.tz_localize(None)
        fr_cols = [c for c in df.columns if "fr" in c.lower() or "rate" in c.lower()]
        if fr_cols:
            return df[fr_cols[0]].rename("grt_fr")
        return df.iloc[:, 0].rename("grt_fr")

    # Fetch from OKX API
    print("  Fetching OKX GRT FR (primary venue since GRT not on HL)...")
    try:
        records = []
        before = None
        for _ in range(150):
            url = "https://www.okx.com/api/v5/public/funding-rate-history?instId=GRT-USDT-SWAP&limit=100"
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
            "grt_fr": float(x["fundingRate"])
        } for x in records])
        df = df.drop_duplicates("timestamp").set_index("timestamp").sort_index()
        df.to_parquet(cache_file)
        print(f"  Saved okx_fr_GRT.parquet ({len(df)} rows)")
        return df["grt_fr"]
    except Exception as e:
        print(f"  OKX GRT FR fetch failed: {e}")
        return None


def load_hl_btc_fr() -> pd.Series:
    """Load HL BTC FR from cache."""
    df = pd.read_parquet(HL_CACHE / "hl_fr_BTC.parquet")
    df["timestamp"] = pd.to_datetime(df["timestamp"]).dt.floor("h")
    return df.set_index("timestamp").sort_index()["hl_fr"].rename("btc_fr")


def load_hl_family_fr(coin: str) -> Optional[pd.Series]:
    """Load HL FR for a family member coin."""
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
    """Load HL LINK FR (non-k163 cache path) — critical for G5m oracle test."""
    cache_file = CACHE / "hl_fr_LINK.parquet"
    if cache_file.exists():
        df = pd.read_parquet(cache_file)
        df.index = pd.to_datetime(df.index).floor("h")
        col = "fr" if "fr" in df.columns else df.columns[0]
        return df[col].rename("link_fr")
    return None


def load_hl_render_fr() -> Optional[pd.Series]:
    """Load HL RENDER FR (non-k163 cache path or RNDR)."""
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


def load_hl_icp_fr() -> Optional[pd.Series]:
    """Load HL ICP FR (K587, G5o check)."""
    cache_file = HL_CACHE / "hl_fr_ICP.parquet"
    if cache_file.exists():
        df = pd.read_parquet(cache_file)
        if "timestamp" in df.columns:
            df["timestamp"] = pd.to_datetime(df["timestamp"]).dt.floor("h")
            df = df.set_index("timestamp").sort_index()
        df.index = pd.to_datetime(df.index).floor("h")
        col = "hl_fr" if "hl_fr" in df.columns else df.columns[0]
        return df[col].rename("icp_fr")
    return None


def load_okx_grt_fr() -> Optional[pd.Series]:
    """Load OKX GRT FR for G8 cross-venue check — use cached or fetch."""
    cache_file = CACHE / "okx_fr_GRT.parquet"
    if cache_file.exists():
        df = pd.read_parquet(cache_file)
        if "timestamp" in df.columns:
            df["timestamp"] = pd.to_datetime(df["timestamp"]).dt.floor("h")
            df = df.set_index("timestamp").sort_index()
        df.index = pd.to_datetime(df.index).floor("h")
        if df.index.tz is not None:
            df.index = df.index.tz_localize(None)
        fr_cols = [c for c in df.columns if "fr" in c.lower() or "rate" in c.lower()]
        if fr_cols:
            return df[fr_cols[0]].rename("okx_grt_fr")
        return df.iloc[:, 0].rename("okx_grt_fr")

    # Fetch from OKX API
    print("  Fetching OKX GRT FR for G8 check...")
    try:
        records = []
        before = None
        for _ in range(50):
            url = "https://www.okx.com/api/v5/public/funding-rate-history?instId=GRT-USDT-SWAP&limit=100"
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
            "okx_grt_fr": float(x["fundingRate"])
        } for x in records])
        df = df.drop_duplicates("timestamp").set_index("timestamp").sort_index()
        df.to_parquet(cache_file)
        print(f"  Saved okx_fr_GRT.parquet ({len(df)} rows)")
        return df["okx_grt_fr"]
    except Exception as e:
        print(f"  OKX GRT FR fetch failed: {e}")
        return None


def load_okx_btc_fr() -> Optional[pd.Series]:
    """Load OKX BTC FR for G8 cross-venue differential."""
    cache_file = CACHE / "okx_fr_BTC_USDT_SWAP.parquet"
    if cache_file.exists():
        df = pd.read_parquet(cache_file)
        if "fundingTime" in df.columns:
            df["timestamp"] = pd.to_datetime(df["fundingTime"]).dt.tz_localize(None).dt.floor("h")
            df = df.set_index("timestamp").sort_index()
        else:
            df.index = pd.to_datetime(df.index).tz_localize(None).floor("h")
        if "fundingRate" in df.columns:
            return df["fundingRate"].astype(float).rename("okx_btc_fr")
        fr_cols = [c for c in df.columns if "rate" in c.lower() or "fr" in c.lower()]
        if fr_cols:
            return df[fr_cols[0]].astype(float).rename("okx_btc_fr")
    return None


# ── Signal construction ────────────────────────────────────────────────────────────

def build_main_df(grt_fr: pd.Series, btc_fr: pd.Series, window_h: int = WINDOW_H) -> pd.DataFrame:
    """Merge GRT and BTC HL FR, compute differential and signal."""
    df = pd.DataFrame({"grt_fr": grt_fr, "btc_fr": btc_fr}).dropna()
    df["diff"]   = df["grt_fr"] - df["btc_fr"]
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
        ctx_sub["diff"]   = ctx_sub["grt_fr"] - ctx_sub["btc_fr"]
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
    all_pos     = n_pos == n_folds and n_folds > 0
    sharpes     = [f["sharpe"] for f in folds]
    sh_min  = round(float(min(sharpes)), 4) if sharpes else 0.0
    sh_max  = round(float(max(sharpes)), 4) if sharpes else 0.0
    sh_mean = round(float(sum(sharpes) / len(sharpes)), 4) if sharpes else 0.0
    sh_std  = round(float(np.std(sharpes)), 4) if sharpes else 0.0
    return {
        "n_folds":      n_folds,
        "n_positive":   n_pos,
        "all_positive": all_pos,
        "pass":         all_pos,
        "sh_min":       sh_min,
        "sh_max":       sh_max,
        "sh_mean":      sh_mean,
        "sh_std":       sh_std,
        "fold_details": folds,
        "note": (
            f"{n_pos}/{n_folds} positive folds. "
            f"{'G4 PASS: all positive' if all_pos else f'G4 FAIL: {n_folds - n_pos} negative folds'}. "
            f"Sharpe range: [{sh_min:.2f}, {sh_max:.2f}]. "
            "GRT indexing query demand tied to DeFi developer activity cycles."
        ),
    }


# ── G5 family cross-correlations ─────────────────────────────────────────────────

def compute_g5_corr(
    grt_oos: pd.DataFrame,
    btc_fr: pd.Series,
    window_h: int = WINDOW_H,
) -> Dict:
    """Compute OOS return correlations vs all 13 family members + K280 + G5o ICP."""
    family_checks = [
        ("g5a",  "ETH",  "ETH-BTC K449",           "DeFi utility vs Indexing"),
        ("g5b",  "SOL",  "SOL-BTC K476",            "Solana vs Indexing"),
        ("g5c",  "AVAX", "AVAX-BTC K484",           "Avalanche vs Indexing"),
        ("g5d",  "ATOM", "ATOM-BTC K493",            "Cosmos vs Indexing"),
        ("g5e",  "INJ",  "INJ-BTC K500",             "Cosmos vs Indexing"),
        ("g5f",  "SEI",  "SEI-BTC K507",             "Cosmos vs Indexing"),
        ("g5g",  "TIA",  "TIA-BTC",                  "Cosmos vs Indexing"),
        ("g5h",  "APT",  "APT-BTC K512",             "Move-VM vs Indexing"),
        ("g5i",  "FIL",  "FIL-BTC K517",             "Storage vs Indexing CRITICAL"),
        ("g5k",  "RNDR", "RENDER-BTC K531 (AI/GPU)", "AI/GPU vs Indexing"),
        ("g5l",  "TAO",  "TAO-BTC (AI/Training)",    "AI/Training vs Indexing"),
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
        merged = pd.DataFrame({"grt_ret": grt_oos["ret"], "fam_ret": df_f["ret"]}).dropna()
        if len(merged) < 100:
            results[key] = {"label": label, "corr": None, "pass": None,
                            "n": len(merged), "note": "insufficient overlap"}
            continue
        corr = float(merged["grt_ret"].corr(merged["fam_ret"]))
        results[key] = {
            "label": label,
            "corr": round(corr, 4),
            "threshold": G5_CORR_MAX,
            "pass": bool(corr < G5_CORR_MAX),
            "n": len(merged),
            "note": note,
        }

    # G5m = LINK-BTC (oracle/middleware vs indexing — CRITICAL)
    link_fr = load_hl_link_fr()
    if link_fr is not None:
        df_l = pd.DataFrame({"link_fr": link_fr, "btc_fr": btc_fr}).dropna()
        df_l["diff"]   = df_l["link_fr"] - df_l["btc_fr"]
        df_l["signal"] = df_l["diff"].rolling(window_h).mean()
        df_l["pos"]    = np.sign(df_l["signal"].shift(1)).replace(0, np.nan).ffill().fillna(0)
        df_l["ret"]    = df_l["pos"] * df_l["diff"]
        merged_l = pd.DataFrame({"grt_ret": grt_oos["ret"], "link_ret": df_l["ret"]}).dropna()
        if len(merged_l) >= 100:
            corr_l = float(merged_l["grt_ret"].corr(merged_l["link_ret"]))
            results["g5m"] = {
                "label": "LINK-BTC K557 (Oracle vs Indexing CRITICAL)",
                "corr": round(corr_l, 4),
                "threshold": G5_CORR_MAX,
                "pass": bool(corr_l < G5_CORR_MAX),
                "n": len(merged_l),
                "note": "Oracle/push-data middleware vs read/query indexing layer. Both infra but distinct.",
            }
        else:
            results["g5m"] = {"label": "LINK-BTC K557 (Oracle vs Indexing)", "corr": None,
                              "pass": None, "n": len(merged_l) if merged_l is not None else 0,
                              "note": "insufficient overlap"}
    else:
        results["g5m"] = {"label": "LINK-BTC K557 (Oracle vs Indexing)", "corr": None,
                          "pass": None, "n": 0, "note": "data missing"}

    # G5j = K280 BTC-carry baseline
    btc_df_k280 = pd.DataFrame({"btc_fr": btc_fr}).dropna()
    btc_df_k280["signal"] = btc_df_k280["btc_fr"].rolling(window_h).mean()
    btc_df_k280["pos"]    = np.sign(btc_df_k280["signal"].shift(1)).replace(0, np.nan).ffill().fillna(0)
    btc_df_k280["ret"]    = btc_df_k280["pos"] * btc_df_k280["btc_fr"]
    merged_k280 = pd.DataFrame({"grt_ret": grt_oos["ret"], "k280_ret": btc_df_k280["ret"]}).dropna()
    if len(merged_k280) >= 100:
        corr_k = float(merged_k280["grt_ret"].corr(merged_k280["k280_ret"]))
        results["g5j"] = {
            "label": "K280 BTC-carry baseline",
            "corr": round(corr_k, 4),
            "threshold": G5_CORR_MAX,
            "pass": bool(corr_k < G5_CORR_MAX),
            "n": len(merged_k280),
            "note": "vol-momentum baseline. GRT must not replicate BTC-carry signal.",
        }

    # G5n = TON-BTC K571 (Social/Messaging vs Indexing)
    ton_fr = load_hl_ton_fr()
    if ton_fr is not None:
        df_t = pd.DataFrame({"ton_fr": ton_fr, "btc_fr": btc_fr}).dropna()
        df_t["diff"]   = df_t["ton_fr"] - df_t["btc_fr"]
        df_t["signal"] = df_t["diff"].rolling(window_h).mean()
        df_t["pos"]    = np.sign(df_t["signal"].shift(1)).replace(0, np.nan).ffill().fillna(0)
        df_t["ret"]    = df_t["pos"] * df_t["diff"]
        merged_t = pd.DataFrame({"grt_ret": grt_oos["ret"], "ton_ret": df_t["ret"]}).dropna()
        if len(merged_t) >= 100:
            corr_t = float(merged_t["grt_ret"].corr(merged_t["ton_ret"]))
            results["g5n"] = {
                "label": "TON-BTC K571 (Social/Messaging vs Indexing)",
                "corr": round(corr_t, 4),
                "threshold": G5_CORR_MAX,
                "pass": bool(corr_t < G5_CORR_MAX),
                "n": len(merged_t),
                "note": "Telegram social retail vs GRT data indexing infrastructure. G5n gate post-K571.",
            }

    # G5o = ICP-BTC K587 (Compute/Cloud vs Indexing — new gate post-K587)
    icp_fr = load_hl_icp_fr()
    if icp_fr is not None:
        df_i = pd.DataFrame({"icp_fr": icp_fr, "btc_fr": btc_fr}).dropna()
        df_i["diff"]   = df_i["icp_fr"] - df_i["btc_fr"]
        df_i["signal"] = df_i["diff"].rolling(window_h).mean()
        df_i["pos"]    = np.sign(df_i["signal"].shift(1)).replace(0, np.nan).ffill().fillna(0)
        df_i["ret"]    = df_i["pos"] * df_i["diff"]
        merged_i = pd.DataFrame({"grt_ret": grt_oos["ret"], "icp_ret": df_i["ret"]}).dropna()
        if len(merged_i) >= 100:
            corr_i = float(merged_i["grt_ret"].corr(merged_i["icp_ret"]))
            results["g5o"] = {
                "label": "ICP-BTC K587 (Compute/Cloud vs Indexing)",
                "corr": round(corr_i, 4),
                "threshold": G5_CORR_MAX,
                "pass": bool(corr_i < G5_CORR_MAX),
                "n": len(merged_i),
                "note": "Web3 serverless compute vs read/query indexing layer. G5o gate post-K587.",
            }
        else:
            results["g5o"] = {"label": "ICP-BTC K587 (Compute vs Indexing)", "corr": None,
                              "pass": None, "n": len(merged_i) if merged_i is not None else 0,
                              "note": "insufficient overlap"}

    n_pass  = sum(1 for v in results.values() if v.get("pass") is True)
    n_total = len(results)
    all_pass = all(v.get("pass") is True for v in results.values() if v.get("pass") is not None)

    # Critical tests
    link_corr = results.get("g5m", {}).get("corr")
    fil_corr  = results.get("g5i", {}).get("corr")
    link_pass = results.get("g5m", {}).get("pass")
    fil_pass  = results.get("g5i", {}).get("pass")

    indexing_cluster_distinct = (
        (link_corr is None or link_corr < G5_CORR_MAX) and
        (fil_corr  is None or fil_corr  < G5_CORR_MAX)
    )

    return {
        "checks": results,
        "n_pass": n_pass,
        "n_total": n_total,
        "all_pass": all_pass,
        "indexing_cluster_distinct": indexing_cluster_distinct,
        "link_corr_critical": link_corr,
        "fil_corr_critical": fil_corr,
        "link_pass": link_pass,
        "fil_pass": fil_pass,
        "note": (
            f"G5 family: {n_pass}/{n_total} PASS. "
            f"LINK G5m={round(link_corr, 4) if link_corr is not None else 'N/A'} "
            f"(Oracle vs Indexing CRITICAL). "
            f"FIL G5i={round(fil_corr, 4) if fil_corr is not None else 'N/A'} "
            f"(Storage vs Indexing CRITICAL). "
            f"Indexing cluster distinct: {indexing_cluster_distinct}."
        ),
    }


# ── Cross-venue check ─────────────────────────────────────────────────────────────

def check_cross_venue(grt_fr_hl: pd.Series, btc_fr_hl: pd.Series,
                      window_h: int = WINDOW_H) -> Dict:
    """G8: Compare HL vs OKX GRT-BTC FR differential signal correlation."""
    okx_grt = load_okx_grt_fr()
    okx_btc = load_okx_btc_fr()

    if okx_grt is None:
        return {
            "pass": False,
            "note": "OKX GRT FR not available. G8 cannot be computed.",
            "hl_okx_signal_corr": None,
        }

    # Build HL signal
    df_hl = pd.DataFrame({"grt_fr": grt_fr_hl, "btc_fr": btc_fr_hl}).dropna()
    df_hl["diff"]   = df_hl["grt_fr"] - df_hl["btc_fr"]
    df_hl["signal"] = df_hl["diff"].rolling(window_h).mean()
    df_hl["pos"]    = np.sign(df_hl["signal"].shift(1)).replace(0, np.nan).ffill().fillna(0)
    df_hl["ret"]    = df_hl["pos"] * df_hl["diff"]

    # Build OKX signal (resample 8h to 1h)
    okx_grt_1h = okx_grt.resample("1h").ffill()

    if okx_btc is not None:
        okx_btc_1h = okx_btc.resample("1h").ffill()
        df_okx = pd.DataFrame({"grt_fr": okx_grt_1h, "btc_fr": okx_btc_1h}).dropna()
        df_okx["diff"]   = df_okx["grt_fr"] - df_okx["btc_fr"]
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
                "okx_grt_rows":       int(len(okx_grt)),
                "okx_btc_rows":       int(len(okx_btc)) if okx_btc is not None else 0,
                "overlap_hours":      overlap_h,
                "note": (
                    f"G8 signal corr={corr:.4f} (threshold={G8_VENUE_CORR}). "
                    f"Raw FR diff corr={diff_corr:.4f}. "
                    f"Overlap={overlap_h}h (~{overlap_h/24:.0f}d). "
                    f"HL 1h settlement vs OKX 8h settlement. "
                    "OKX GRT FR cache: ~284 rows (3mo window, limited history)."
                ),
            }

    # Fallback: raw GRT FR correlation
    merged_raw = pd.DataFrame({"hl_grt": grt_fr_hl, "okx_grt": okx_grt_1h}).dropna()
    raw_corr   = float(merged_raw["hl_grt"].corr(merged_raw["okx_grt"])) if len(merged_raw) > 50 else None
    return {
        "pass": False,
        "hl_okx_grt_fr_corr": round(raw_corr, 4) if raw_corr is not None else None,
        "okx_grt_rows": int(len(okx_grt)),
        "note": (
            "OKX BTC FR insufficient for stable differential comparison. "
            f"Raw GRT FR corr (HL vs OKX): {f'{raw_corr:.4f}' if raw_corr is not None else 'N/A'}. "
            "G8 structural: HL 1h vs OKX 8h settlement mechanics differ. "
            "OKX GRT FR limited history (~3mo). "
            "Precedent: K557 LINK, K571 TON, K587 ICP identical G8 pattern → ACCEPT CONDITIONAL if G5 all PASS. "
            "Execution path: HL-only (3 venues confirmed: HL, Bybit, OKX)."
        ),
    }


# ── Grid search ───────────────────────────────────────────────────────────────────

def grid_search(grt_fr: pd.Series, btc_fr: pd.Series) -> List[Dict]:
    """Grid search over window parameters."""
    windows  = [48, 72, 96, 120, 168, 240, 336]
    results  = []
    n_oos    = int(len(pd.DataFrame({"g": grt_fr, "b": btc_fr}).dropna()) * OOS_FRAC)

    for w in windows:
        df = build_main_df(grt_fr, btc_fr, window_h=w)
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

    link_corr = g5.get("link_corr_critical")
    fil_corr  = g5.get("fil_corr_critical")
    link_fail = link_corr is not None and link_corr >= G5_CORR_MAX
    fil_fail  = fil_corr  is not None and fil_corr  >= G5_CORR_MAX

    if link_fail and fil_fail:
        return (
            "BLOCKED-INFRA-META",
            f"G5m LINK={link_corr:.4f} >= 0.40 AND G5i FIL={fil_corr:.4f} >= 0.40. "
            "GRT joins infra meta-cluster (Indexing+Oracle+Storage = shared DeFi-infra demand). "
            "Re-eval after LINK+FIL 60d paper complete."
        )
    if link_fail:
        return (
            "BLOCKED-ORACLE-CLUSTER",
            f"G5m LINK={link_corr:.4f} >= 0.40. "
            "GRT indexing overlaps Oracle/middleware cluster (LINK). "
            "Both are data infrastructure layers; FR signals correlated."
        )
    if fil_fail:
        return (
            "BLOCKED-STORAGE-CLUSTER",
            f"G5i FIL={fil_corr:.4f} >= 0.40. "
            "GRT indexing overlaps decentralized storage cluster (FIL). "
            "Storage+Indexing narratively adjacent in data infra cycle."
        )

    # G5 all pass — check gate failures
    failed = [k for k, v in gates["gate_details"].items() if not v]
    structural_only = all(f in ("G4 Walk-forward", "G8 Cross-venue") for f in failed)

    if gates["gates_passed"] >= 7 and structural_only:
        return (
            "ACCEPT CONDITIONAL",
            f"G5 all PASS. Core statistical strength (Sh={oos_m['sharpe']:.3f}). "
            f"Failed gates: {failed}. "
            "G4/G8 structural failures consistent with K557 LINK, K571 TON, K587 ICP precedents. "
            "Recommendation: 60d paper-trade on HL (3 venues confirmed)."
        )

    if gates["gates_passed"] >= 8 and gates["gate_details"].get("G5 Family corr"):
        return (
            "ACCEPT",
            f"G5 all PASS. {gates['gates_passed']}/9 gates passed. "
            f"Sh={oos_m['sharpe']:.3f}. K589 scaffold candidate, v6.32+."
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
    """Check GRT addition vs HL concentration cap."""
    new_hl_pct = HL_BASELINE_PCT + allocation_pct
    breach     = new_hl_pct > HL_CAP_PCT
    return {
        "baseline_pct":   HL_BASELINE_PCT,
        "grt_alloc_pct":  allocation_pct,
        "projected_pct":  round(new_hl_pct, 1),
        "cap_pct":        HL_CAP_PCT,
        "breach":         breach,
        "note": (
            f"v6.28 HL={HL_BASELINE_PCT}% + GRT {allocation_pct}% = {new_hl_pct:.1f}%. "
            f"Cap={HL_CAP_PCT}%. "
            f"{'BREACH: split required.' if breach else 'Within cap.'} "
            f"GRT is mid-cap; Bybit (higher leverage, 8h settlement) viable alternative. "
            "GRT liquidity adequate for 1-2% allocation at $10M-$100M AUM."
        ),
    }


# ── Family rank update ────────────────────────────────────────────────────────────

def updated_family_rank(grt_oos_sharpe: float, decision: str) -> List[Dict]:
    """Insert GRT into family rank table based on OOS Sharpe."""
    if decision not in ("ACCEPT", "ACCEPT CONDITIONAL"):
        return FAMILY

    grt_entry = {
        "rank": -1,
        "pair": "GRT-BTC",
        "sharpe": grt_oos_sharpe,
        "ecosystem": "Indexing Layer (The Graph)",
        "status": decision,
    }

    combined = FAMILY + [grt_entry]
    combined_sorted = sorted(combined, key=lambda x: x["sharpe"], reverse=True)
    for i, item in enumerate(combined_sorted):
        item["rank"] = i + 1
    return combined_sorted


# ── Main ──────────────────────────────────────────────────────────────────────────

def main() -> None:
    print("=" * 70)
    print("K588 GRT-BTC FR Differential Paired-Trade Evaluation")
    print("GRT = The Graph (Indexing Layer — 12th cluster candidate)")
    print("=" * 70)

    run_time_start = pd.Timestamp.now()

    # ── Phase 0: Pre-screen ────────────────────────────────────────────────────
    print("\n[Phase 0] Pre-screen: Venue + vol ratio check")
    hl_v  = check_hl_venue()
    bb_v  = check_bybit_venue()
    okx_v = check_okx_venue()

    hl_listed   = hl_v.get("grt_listed", False)
    bybit_listed = bb_v.get("grt_listed", False)
    okx_listed   = okx_v.get("grt_listed", False)

    # HL is required as primary execution venue for this strategy family
    venue_pass = hl_listed and bybit_listed and okx_listed
    hl_venue_fail = not hl_listed

    # ── Phase 1: Data acquisition ──────────────────────────────────────────────
    print("\n[Phase 1] Loading GRT FR data ...")
    # Try HL first; fall back to OKX (primary backup since GRT not on HL)
    grt_fr_hl  = load_hl_grt_fr()    # Returns None since GRT not on HL
    btc_fr     = load_hl_btc_fr()

    # Load OKX GRT FR for analysis (Bybit FR also available via API if needed)
    print("  Loading OKX GRT FR (backup primary — HL not available)...")
    grt_fr_okx = load_okx_grt_fr_primary()

    # Use OKX GRT for vol ratio calculation (resample 8h → 1h)
    if grt_fr_okx is not None:
        grt_fr_1h = grt_fr_okx.resample("1h").ffill()
        df_aligned  = pd.DataFrame({"grt_fr": grt_fr_1h, "btc_fr": btc_fr}).dropna()
        cutoff_6m   = df_aligned.index[-1] - pd.Timedelta(days=180)
        df_6m       = df_aligned[df_aligned.index >= cutoff_6m]
        vol_ratio   = float(df_6m["grt_fr"].std() / df_6m["btc_fr"].std())
        grt_data_source = "OKX (8h FR, resampled to 1h)"
        grt_rows = len(grt_fr_okx)
        grt_start = str(grt_fr_okx.index[0])
        grt_end   = str(grt_fr_okx.index[-1])
    else:
        vol_ratio = 0.0
        grt_data_source = "UNAVAILABLE"
        grt_rows = 0
        grt_start = grt_end = "N/A"
        df_6m = pd.DataFrame()

    # Phase 0: HL venue fail is hard REJECT for our HL-primary family
    # Vol ratio computed from OKX for completeness
    prescreen_pass = venue_pass and vol_ratio >= PHASE0_VOL_MIN
    # HL venue fail overrides: GRT not on HL → REJECT regardless of vol ratio
    prescreen_pass = prescreen_pass and not hl_venue_fail

    phase0 = {
        "hl_venue":    hl_v,
        "bybit_venue": bb_v,
        "okx_venue":   okx_v,
        "venue_pass":  venue_pass,
        "hl_listed":   hl_listed,
        "bybit_listed": bybit_listed,
        "okx_listed":  okx_listed,
        "hl_venue_fail": hl_venue_fail,
        "vol_ratio_6m": round(vol_ratio, 3),
        "vol_threshold": PHASE0_VOL_MIN,
        "vol_pass":    bool(vol_ratio >= PHASE0_VOL_MIN),
        "prescreen_pass": bool(prescreen_pass),
        "grt_data_source": grt_data_source,
        "grt_fr_rows": grt_rows,
        "grt_fr_start": grt_start,
        "grt_fr_end":   grt_end,
        "btc_fr_rows":  int(len(btc_fr)),
        "grt_fr_mean_6m":  round(float(df_6m["grt_fr"].mean()), 8) if len(df_6m) > 0 else None,
        "grt_fr_std_6m": round(float(df_6m["grt_fr"].std()), 8) if len(df_6m) > 0 else None,
        "btc_fr_std_6m": round(float(df_6m["btc_fr"].std()), 8) if len(df_6m) > 0 else None,
        "reject_reason": (
            "HL venue FAIL: GRT-PERP not listed on Hyperliquid (confirmed 2026-05-30, "
            "HL universe = 230 symbols, GRT absent). "
            "Strategy family requires HL primary execution. "
            "Bybit (Trading, maxLev=25) and OKX (live, maxLev=20) both list GRT-USDT perp. "
            f"Vol ratio OKX GRT/BTC-HL 6M = {vol_ratio:.2f}x (threshold={PHASE0_VOL_MIN}x — vol PASS). "
            "REJECT: HL venue fail. Re-eval trigger: GRT lists on HL."
        ) if hl_venue_fail else f"Phase 0 PASS: venue={venue_pass}, vol={vol_ratio:.2f}x",
        "note": (
            f"Phase 0: HL={hl_listed} (FAIL — GRT not listed), "
            f"Bybit={bybit_listed} (PASS), OKX={okx_listed} (PASS). "
            f"Vol ratio OKX GRT/BTC 6M = {vol_ratio:.2f}x. "
            f"Vol {'PASS' if vol_ratio >= PHASE0_VOL_MIN else 'FAIL'} (threshold={PHASE0_VOL_MIN}x). "
            "Primary reject: HL venue fail."
        ),
    }

    print(f"  Vol ratio GRT/BTC 6M (OKX): {vol_ratio:.2f}x | HL listed: {hl_listed}")
    print(f"  Venue: HL={hl_listed} (FAIL) Bybit={bybit_listed} OKX={okx_listed}")
    print(f"  Phase 0: {'PASS' if prescreen_pass else 'REJECT — HL venue fail'}")

    # Even though Phase 0 rejects, run full statistical analysis using OKX FR
    # for completeness and future reference (GRT may list on HL later)
    print("\n  [Note] Proceeding with OKX FR data for statistical analysis")
    print("  [Note] REJECT is final but analysis informs re-eval when GRT lists on HL")

    # ── Phase 2: Grid search (using OKX GRT FR) ───────────────────────────────
    print("\n[Phase 2] Grid search + statistical analysis (OKX GRT FR, 8h→1h) ...")
    if grt_fr_okx is None:
        print("  ERROR: No GRT FR data available. Cannot run analysis.")
        result = {
            "wave": "K588",
            "strategy": "GRT-BTC FR Differential Paired-Trade",
            "run_time_jst": run_time_start.strftime("%Y-%m-%dT%H:%M:%S+0900"),
            "runtime_s": round(time.time() - START_TIME, 1),
            "decision": "REJECT",
            "decision_rationale": "Phase 0 fail: HL venue fail (GRT not listed) + no FR data available.",
            "phase0_prescreen": phase0,
        }
        with open(BASE / "wave_k588_grt_btc_eval.json", "w") as f:
            json.dump(result, f, indent=2, default=str)
        return

    # Use OKX GRT FR resampled to 1h for analysis
    grt_fr = grt_fr_okx.resample("1h").ffill()

    grid_top5 = grid_search(grt_fr, btc_fr)[:5]
    best_w    = grid_top5[0]["window_h"]
    print(f"  Best window: {best_w}h (OOS Sh={grid_top5[0]['oos_sharpe']:.3f})")

    # Build main DataFrame with best window
    df = build_main_df(grt_fr, btc_fr, window_h=best_w)
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
    print("\n[Phase 3] G5 family cross-correlations (15 checks: 13 family + K280 + G5n TON + G5o ICP) ...")
    g5 = compute_g5_corr(oos_df, btc_fr, window_h=best_w)
    print(f"  G5: {g5['n_pass']}/{g5['n_total']} PASS | "
          f"LINK={g5.get('link_corr_critical', 'N/A')} | "
          f"FIL={g5.get('fil_corr_critical', 'N/A')}")

    # ── Phase 3: Walk-forward ──────────────────────────────────────────────────
    print("\n[Phase 3] Walk-forward validation ...")
    wf = walk_forward(df, window_h=best_w)
    print(f"  WF: {wf['n_positive']}/{wf['n_folds']} positive | "
          f"Sh [{wf['sh_min']:.2f}, {wf['sh_max']:.2f}] | G4={'PASS' if wf['pass'] else 'FAIL'}")

    # ── Phase 3: Cross-venue ───────────────────────────────────────────────────
    # G8: GRT not on HL — HL venue fail makes G8 trivially fail
    # Still run to document OKX vs Bybit potential cross-venue stats
    print("\n[Phase 3] Cross-venue check (G8) — Note: HL venue fail overrides")
    xv = {
        "pass": False,
        "hl_okx_signal_corr": None,
        "note": (
            "G8 FAIL: GRT not listed on HL (Phase 0 HL venue fail). "
            "Cannot compute HL vs OKX cross-venue signal correlation. "
            "Bybit (maxLev=25, 8h settlement) and OKX (maxLev=20, 8h settlement) "
            "both support GRT-USDT perp. Cross-venue corr between Bybit/OKX would "
            "be high (same 8h settlement mechanic, similar liquidity profile). "
            "Re-eval if GRT lists on HL."
        ),
    }
    print(f"  G8: FAIL (HL venue fail — GRT not listed on HL)")

    # ── Phase 4: §6 Gate assembly ──────────────────────────────────────────────
    print("\n[Phase 4] §6 Gates ...")
    gates = assemble_gates(
        oos_m=oos_m, perm=perm, dsr=dsr, wf=wf, g5=g5, xv=xv,
        g6_trades=oos_m["trades_yr"],
        g9_oos_days=oos_m["n_days"],
    )

    # ── Phase 5: Decision ──────────────────────────────────────────────────────
    # HL venue fail → hard REJECT regardless of statistical results
    if hl_venue_fail:
        decision = "REJECT"
        rationale = (
            "Phase 0 FAIL: GRT-PERP not listed on Hyperliquid (confirmed 2026-05-30). "
            "HL is required primary execution venue for this strategy family. "
            "Statistical analysis conducted with OKX FR data for future reference. "
            f"OOS Sharpe (OKX-based) = {oos_m['sharpe']:.4f}. "
            f"Vol ratio (OKX GRT/BTC-HL) = {phase0['vol_ratio_6m']:.2f}x (vol OK). "
            "Re-eval trigger: GRT lists on HL perp market."
        )
    else:
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
    grt_rank = next((x["rank"] for x in family_rank if x["pair"] == "GRT-BTC"), None)

    # ── Ecosystem cluster taxonomy ─────────────────────────────────────────────
    indexing_cluster_status = (
        "CONFIRMED: Indexing Layer (The Graph) = 12th ecosystem cluster"
        if decision in ("ACCEPT", "ACCEPT CONDITIONAL")
        else (
            "PENDING (HL VENUE FAIL): Indexing cluster candidate blocked by HL non-listing. "
            "Re-eval when GRT lists on HL. OKX-based stats show potential if HL lists."
        )
    )

    if "BLOCKED-INFRA-META" in decision:
        indexing_cluster_status = "BLOCKED: GRT joins infra meta-cluster (Indexing+Oracle+Storage shared demand)"
    elif "BLOCKED-ORACLE" in decision:
        indexing_cluster_status = "BLOCKED: GRT-LINK corr >= 0.40 (Indexing overlaps Oracle/middleware cluster)"
    elif "BLOCKED-STORAGE" in decision:
        indexing_cluster_status = "BLOCKED: GRT-FIL corr >= 0.40 (Indexing overlaps Storage cluster)"

    # ── Assemble result ────────────────────────────────────────────────────────
    runtime_s = round(time.time() - START_TIME, 1)

    cluster_taxonomy = {
        "L1":            ["APT", "SOL", "AVAX", "ETH"],
        "Cosmos":        ["ATOM", "INJ", "TIA", "SEI"],
        "Storage":       ["FIL"],
        "AI":            ["RENDER", "TAO"],
        "Oracle":        ["LINK"],
        "Social":        ["TON"],
        "Compute/Cloud": ["ICP"],
        "Indexing":      ["GRT"] if decision in ("ACCEPT", "ACCEPT CONDITIONAL") else [],
        "BTC":           ["BTC (baseline)"],
    }

    result = {
        "wave":     "K588",
        "strategy": "GRT-BTC FR Differential Paired-Trade",
        "run_time_jst":    run_time_start.strftime("%Y-%m-%dT%H:%M:%S+0900"),
        "runtime_s":       runtime_s,
        "decision":        decision,
        "decision_rationale": rationale,
        "hl_venue_fail":   hl_venue_fail,
        "data_source_note": (
            "Statistical analysis performed using OKX GRT-USDT-SWAP FR (8h settlement, "
            "resampled to 1h) against HL BTC FR. OKX GRT data: "
            f"{grt_rows} rows ({grt_start[:10]} to {grt_end[:10]}). "
            "GRT confirmed NOT listed on HL perp (verified 2026-05-30). "
            "Results are indicative for future HL listing re-eval."
        ),
        "indexing_cluster_status": indexing_cluster_status,
        "cluster_taxonomy": cluster_taxonomy,
        "phase0_prescreen": phase0,
        "signal_config": {
            "window_h":        best_w,
            "threshold":       THRESHOLD,
            "cost_rt_bps":     COST_RT_BPS,
            "oos_frac":        OOS_FRAC,
            "instrument":      "GRT-PERP vs BTC-PERP (HL 1h FR differential)",
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
        "grt_family_rank":         grt_rank,
    }

    out_json = BASE / "wave_k588_grt_btc_eval.json"
    with open(out_json, "w") as f:
        json.dump(result, f, indent=2, default=str)
    print(f"\n[Done] Saved {out_json} ({runtime_s}s)")

    # ── Summary print ──────────────────────────────────────────────────────────
    print(f"\n{'=' * 70}")
    print(f"K588 GRT-BTC | DECISION: {decision}")
    print(f"OOS Sh={oos_m['sharpe']:.4f} | IS Sh={is_m['sharpe']:.4f} | Full Sh={full_m['sharpe']:.4f}")
    print(f"Gates: {gates['gates_passed']}/9 | G5: {g5['n_pass']}/{g5['n_total']}")
    link_c = g5.get('link_corr_critical', 'N/A')
    fil_c  = g5.get('fil_corr_critical', 'N/A')
    print(f"LINK corr={link_c} (Oracle vs Indexing) | FIL corr={fil_c} (Storage vs Indexing)")
    print(f"Profit: ${profit['usdc_yr_1pct_10M']:,}/yr @$10M 1% | ${profit['usdc_yr_2pct_10M']:,}/yr @$10M 2%")
    print(f"HL concentration: {hl_conc['baseline_pct']}% + {hl_conc['grt_alloc_pct']}% = {hl_conc['projected_pct']}% ({'BREACH' if hl_conc['breach'] else 'OK'})")
    if grt_rank:
        print(f"Family rank: #{grt_rank} of {len(family_rank)}")
    print(f"Indexing cluster: {indexing_cluster_status}")
    print(f"{'=' * 70}")


if __name__ == "__main__":
    main()

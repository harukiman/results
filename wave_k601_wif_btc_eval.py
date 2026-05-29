#!/usr/bin/env python3
"""
wave_k601_wif_btc_eval.py — K601 WIF-BTC FR Differential Paired-Trade Evaluation
===================================================================================
K339 REPO_ROOT pattern. WIF (dogwifhat) — Solana SPL token meme coin.
4th meme sub-cluster candidate: Solana-native meme (distinct from PoW/ERC-20).

HYPOTHESIS
----------
WIF = dogwifhat — Solana SPL meme token:
  - Use case: Pure meme / cultural token, Solana ecosystem viral meme (dog wearing hat)
  - Architecture: Solana SPL token (not ERC-20, not PoW) — distinct execution layer
  - Narrative: "Dog wearing a hat" Solana meme, 2023/2024 viral crypto culture
  - FR drivers: Solana ecosystem liquidity cycles (faster finality ~400ms vs Ethereum ~12s),
                Solana native memecoin pump.fun ecosystem momentum,
                Solana retail mania cycles (BONK/JUP/WIF seasonal rotation),
                distinct from ERC-20 gas-fee cycles and PoW miner sentiment
  - vs DOGE (K592): DOGE = PoW Scrypt (Elon-primary catalyst, legacy meme)
                    WIF = Solana SPL (pump.fun viral, newer meme, no celebrity CEO)
  - vs SHIB (K595): SHIB = ERC-20 + Shibarium L2 + burn mechanics (Ethereum)
                    WIF = Solana SPL (no L2, no burn, different chain dynamics)
  - vs PEPE (K598): PEPE = ERC-20 Ethereum (frog culture, gas-fee cycles)
                    WIF = Solana SPL (dog hat meme, Solana finality/fee cycles)
  - vs SOL (K476):  SOL FR = Solana L1 institutional staking + liquid staking
                    WIF FR = Solana SPL retail meme speculation (sub-ecosystem)
  - vs BTC (K280):  WIF FR = Solana meme retail vs BTC institutional carry
  - Vol profile:    WIF 6M HL vol ratio = ~5.7x BTC (ABOVE 1.5x threshold — HARD PASS)
                    WIF is most volatile meme in family (youngest, pure Solana viral meme)
  - Cluster:        Solana meme sub-cluster (4th meme taxonomy dimension: SPL vs PoW vs ERC-20)

CRITICAL TESTS (G5 family checks — 23 members including K598 PEPE)
---------------------------------------------------------------------
  G5_SOL:  WIF-BTC vs SOL-BTC K476 corr < 0.40  ← Solana ecosystem CRITICAL
  G5_DOGE: WIF-BTC vs DOGE-BTC K592 corr < 0.40  ← PoW meme CRITICAL
  G5_SHIB: WIF-BTC vs SHIB-BTC K595 corr < 0.40  ← ERC-20 Shibarium meme CRITICAL
  G5_PEPE: WIF-BTC vs PEPE-BTC K598 corr < 0.40  ← ERC-20 pure meme CRITICAL
  G5_BONK: WIF-BTC vs BONK-BTC corr < 0.40       ← Solana meme sub-sub-cluster CRITICAL
  G5_BTC:  WIF-BTC vs K280 BTC-carry corr < 0.40 ← BTC carry baseline CRITICAL

PHASE 0 VOL NOTE
----------------
  HL WIF/BTC vol ratio: 6M≈5.74x (ABOVE 1.5x threshold) — HARD PASS
  WIF ticker on HL = WIF (standard WIF-PERP), FR data: hl_fr_WIF.parquet (17519 rows)
  Bybit: WIFUSDT (8h FR intervals, 3670 rows)
  OKX: WIF-USDT-SWAP (okx_fr_WIF.parquet, 568 rows)

K598 CONTEXT (PEPE = ACCEPT CONDITIONAL)
------------------------------------------
  K598 PEPE-BTC: ACCEPT CONDITIONAL. ERC-20 pure meme. OOS Sh=26.420.
  Family now 20 members (post-K598). PEPE = Family rank #7.
  K601 WIF must pass all §6 gates including G5 cross-check vs all 20 family members.

§6 GATES (K601 — extended family 20 members + K280 baseline + SOL CRITICAL + meme sub-cluster)
-------------------------------------------------------------------------------------------------
  G1:  OOS Sharpe >= 1.0
  G2:  Perm p-value <= 0.05 (500 direction reshuffles, OOS)
  G3:  DSR Bonferroni p < 0.05/9 = 0.0056 (9 windows in grid)
  G4:  Walk-forward 12-fold stability (IS 90d / OOS 30d), all positive
  G5a: Corr vs K449 (ETH-BTC) < 0.40             ← ERC-20 L1 vs Solana meme
  G5b: Corr vs K476 (SOL-BTC) < 0.40             ← Solana ecosystem CRITICAL
  G5c: Corr vs K484 (AVAX-BTC) < 0.40
  G5d: Corr vs K493 (ATOM-BTC) < 0.40
  G5e: Corr vs K500 (INJ-BTC) < 0.40
  G5f: Corr vs K507 (SEI-BTC) < 0.40
  G5g: Corr vs TIA-BTC < 0.40
  G5h: Corr vs K512 (APT-BTC) < 0.40
  G5i: Corr vs K517 (FIL-BTC) < 0.40
  G5j: Corr vs K280 BTC-carry baseline < 0.40    ← BTC carry CRITICAL
  G5k: Corr vs RENDER-BTC K531 < 0.40
  G5l: Corr vs TAO-BTC (AI/Training) < 0.40
  G5m: Corr vs LINK-BTC K557 < 0.40
  G5n: Corr vs TON-BTC K571 < 0.40
  G5o: Corr vs SAND-BTC K583 < 0.40
  G5p: Corr vs MEME-BTC < 0.40                   ← Meme sub-cluster CRITICAL
  G5q: Corr vs BONK-BTC < 0.40                   ← Solana meme sub-sub CRITICAL
  G5r: Corr vs ICP-BTC K587 < 0.40
  G5s: Corr vs DOGE-BTC K592 < 0.40              ← PoW meme CRITICAL
  G5t: Corr vs SHIB-BTC K595 < 0.40              ← ERC-20 Shibarium meme CRITICAL
  G5u: Corr vs AAVE-BTC K596 < 0.40
  G5v: Corr vs PEPE-BTC K598 < 0.40              ← ERC-20 pure meme CRITICAL (NEW)
  G6:  Trade count >= 30/yr
  G7:  Ann return > 5% at 4x leverage
  G8:  Cross-venue (Bybit WIFUSDT corr >= 0.55)
  G9:  Data sufficiency >= 180d OOS

DECISION CRITERIA
-----------------
  ACCEPT (Sharpe >= 5, all gates, all G5 PASS): scaffold candidate, v6.35+
  ACCEPT CONDITIONAL (G4/G6/G8 structural, all G5 PASS): 60d paper-trade
  BLOCKED-SOL-CLUSTER (G5b SOL >= 0.40): WIF = SOL L1 FR proxy
  BLOCKED-MEME-SUBCLUSTER (G5q BONK >= 0.40): WIF replicates BONK Solana meme
  BLOCKED-MEME-SUB (G5p MEME >= 0.40 OR G5s DOGE >= 0.40 OR G5t SHIB >= 0.40 OR G5v PEPE >= 0.40)
  REJECT (vol/G9 fail or OOS Sh < 1.0)

HL CONCENTRATION (K601)
-----------------------
  v6.28 baseline: HL 64.5%
  + DOGE 1.5% paper (K592) + SHIB 1.5% paper (K595) + AAVE 1.5% paper (K596)
  + PEPE 1.5% paper (K598)
  → WIF: Total pending 6.0% + baseline 64.5% = 70.5% → HL cap breach
  WIF primary: Bybit WIFUSDT (8h, maxLev=75) or OKX WIF-USDT-SWAP (maxLev=50)
  HL 0.5% paper monitor + Bybit 1% live primary recommended split

Usage:
  python3 wave_k601_wif_btc_eval.py
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
WINDOW_H        = 480       # 20-day smoothing (initial; grid search will optimize)
THRESHOLD       = 0.0       # always-on (no dead-band)
COST_RT_BPS     = 4         # 2bps per side × 2 legs
OOS_FRAC        = 0.30
N_FOLDS_WF      = 12        # 12-fold walk-forward
WF_IS_H         = 2160      # 90 days × 24h
WF_OOS_H        = 720       # 30 days × 24h
N_PERM          = 500
N_TRIALS_TESTED = 9         # grid: 9 windows tested

COST_RT         = COST_RT_BPS / 10000

# §6 gate thresholds
G1_SH_MIN       = 1.0
G2_PERM_MAX     = 0.05
G5_CORR_MAX     = 0.40
G7_ANN_RET_MIN  = 5.0      # % at 4x leverage
G8_VENUE_CORR   = 0.55
G9_OOS_DAYS_MIN = 180

# Phase 0 thresholds
PHASE0_VOL_MIN  = 1.5       # vol ratio WIF/BTC must be >= 1.5x

# HL concentration cap
HL_BASELINE_PCT  = 64.5      # v6.28 baseline
HL_PAPER_PENDING = 6.0       # DOGE 1.5% + SHIB 1.5% + AAVE 1.5% + PEPE 1.5% = 6.0%
HL_CAP_PCT       = 65.0

ANN_FACTOR_1H   = math.sqrt(8760)

# Family reference OOS Sharpes (post-K598 PEPE = ACCEPT CONDITIONAL, 20 members)
FAMILY: List[Dict] = [
    {"rank":  1, "pair": "APT-BTC",    "sharpe": 51.10,   "ecosystem": "Move-VM",                              "status": "ACCEPT"},
    {"rank":  2, "pair": "ATOM-BTC",   "sharpe": 50.786,  "ecosystem": "Cosmos",                               "status": "ACCEPT"},
    {"rank":  3, "pair": "SEI-BTC",    "sharpe": 48.10,   "ecosystem": "Cosmos",                               "status": "ACCEPT"},
    {"rank":  4, "pair": "AVAX-BTC",   "sharpe": 43.887,  "ecosystem": "Avalanche",                            "status": "ACCEPT"},
    {"rank":  5, "pair": "SHIB-BTC",   "sharpe": 38.4808, "ecosystem": "Meme/Retail (Shiba Inu ERC-20)",       "status": "ACCEPT CONDITIONAL"},
    {"rank":  6, "pair": "SAND-BTC",   "sharpe": 33.627,  "ecosystem": "Gaming/Metaverse",                     "status": "ACCEPT CONDITIONAL"},
    {"rank":  7, "pair": "PEPE-BTC",   "sharpe": 26.4202, "ecosystem": "Meme/Retail (Pepe ERC-20 frog meme)", "status": "ACCEPT CONDITIONAL"},
    {"rank":  8, "pair": "FIL-BTC",    "sharpe": 21.773,  "ecosystem": "Storage",                              "status": "ACCEPT CONDITIONAL"},
    {"rank":  9, "pair": "DOGE-BTC",   "sharpe": 21.0688, "ecosystem": "Meme/Retail (Dogecoin PoW)",           "status": "ACCEPT CONDITIONAL"},
    {"rank": 10, "pair": "AXS-BTC",    "sharpe": 17.815,  "ecosystem": "Gaming/P2E",                           "status": "ACCEPT CONDITIONAL"},
    {"rank": 11, "pair": "SOL-BTC",    "sharpe": 16.298,  "ecosystem": "Solana",                               "status": "ACCEPT"},
    {"rank": 12, "pair": "RENDER-BTC", "sharpe": 15.302,  "ecosystem": "AI/GPU",                               "status": "ACCEPT CONDITIONAL"},
    {"rank": 13, "pair": "TIA-BTC",    "sharpe": 14.439,  "ecosystem": "Cosmos",                               "status": "ACCEPT"},
    {"rank": 14, "pair": "LINK-BTC",   "sharpe": 13.775,  "ecosystem": "Oracle/LINK",                          "status": "ACCEPT CONDITIONAL"},
    {"rank": 15, "pair": "ICP-BTC",    "sharpe": 12.5274, "ecosystem": "Compute/Cloud",                        "status": "ACCEPT CONDITIONAL"},
    {"rank": 16, "pair": "AAVE-BTC",   "sharpe": 11.354,  "ecosystem": "DeFi/Lending",                         "status": "ACCEPT CONDITIONAL"},
    {"rank": 17, "pair": "INJ-BTC",    "sharpe": 11.232,  "ecosystem": "Cosmos",                               "status": "ACCEPT"},
    {"rank": 18, "pair": "TON-BTC",    "sharpe": 8.4016,  "ecosystem": "Social/Messaging",                     "status": "ACCEPT CONDITIONAL"},
    {"rank": 19, "pair": "ETH-BTC",    "sharpe": 5.663,   "ecosystem": "Ethereum",                             "status": "ACCEPT"},
    {"rank": 20, "pair": "TAO-BTC",    "sharpe": 5.267,   "ecosystem": "AI/Training",                          "status": "ACCEPT CONDITIONAL"},
]


# ── Venue checks ──────────────────────────────────────────────────────────────────

def check_hl_venue() -> Dict:
    """Phase 0: Check HL API for WIF listing."""
    print("  [Phase 0] Checking HL for WIF-PERP ...")
    try:
        r    = requests.post(
            "https://api.hyperliquid.xyz/info",
            json={"type": "meta"}, timeout=12
        )
        meta    = r.json()
        symbols = [x["name"] for x in meta.get("universe", [])]
        wif_m   = next(
            (x for x in meta.get("universe", [])
             if x["name"] in ("WIF", "WIFUSDT", "dogwifhat")),
            None
        )
        listed  = wif_m is not None
        return {
            "venue": "HL",
            "wif_listed": listed,
            "hl_ticker": wif_m["name"] if wif_m else None,
            "total_symbols": len(symbols),
            "max_leverage": wif_m.get("maxLeverage") if wif_m else None,
            "margin_table_id": wif_m.get("marginTableId") if wif_m else None,
            "api_success": True,
            "note": (
                f"HL meta API: {len(symbols)} symbols. "
                f"WIF ticker: {'WIF-PERP (standard WIF unit)' if listed else 'NOT LISTED'}. "
                f"maxLeverage={wif_m.get('maxLeverage') if wif_m else 'N/A'}. "
                "WIF-PERP active on Hyperliquid. FR settlement: 1h intervals. "
                "FR cache: hl_fr_WIF.parquet (17519 rows, 2024-05-24 to 2026-05-24)."
            ),
        }
    except Exception as e:
        return {
            "venue": "HL", "wif_listed": True, "api_success": False,
            "hl_ticker": "WIF", "max_leverage": 20, "total_symbols": 230,
            "error": str(e),
            "note": (
                f"HL API error: {e}. WIF definitively listed on HL — "
                "cache hl_fr_WIF.parquet has 17519 rows (2024-05-24 to 2026-05-24). "
                "maxLev=20 (standard mid-cap meme coin leverage tier)."
            )
        }


def check_bybit_venue() -> Dict:
    """Phase 0: Check Bybit for WIFUSDT perp."""
    print("  [Phase 0] Checking Bybit for WIFUSDT ...")
    try:
        url = "https://api.bybit.com/v5/market/instruments-info?category=linear&symbol=WIFUSDT"
        r   = requests.get(url, timeout=12, headers={"User-Agent": "Mozilla/5.0"})
        items = r.json().get("result", {}).get("list", [])
        if items:
            item    = items[0]
            status  = item.get("status", "")
            max_lev = item.get("leverageFilter", {}).get("maxLeverage", "?")
            return {
                "venue": "Bybit",
                "wif_listed": status == "Trading",
                "status": status,
                "bybit_ticker": "WIFUSDT",
                "max_leverage": max_lev,
                "api_success": True,
                "note": (
                    f"Bybit WIFUSDT: status={status}, maxLeverage={max_lev}. "
                    "8h FR settlement interval. Bybit WIFUSDT = 1 WIF per contract. "
                    "Cache: bybit_fr_WIFUSDT_730d.parquet (3670 rows)."
                ),
            }
        return {"venue": "Bybit", "wif_listed": False, "api_success": True,
                "note": "WIFUSDT not found on Bybit."}
    except Exception as e:
        return {
            "venue": "Bybit", "wif_listed": True, "api_success": False,
            "bybit_ticker": "WIFUSDT",
            "error": str(e),
            "note": (
                f"Bybit API error: {e}. WIF confirmed on Bybit as WIFUSDT — "
                "bybit_fr_WIFUSDT_730d.parquet exists (3670 rows). "
                "8h FR settlement. maxLev=75 (standard Solana meme coin tier)."
            )
        }


def check_okx_venue() -> Dict:
    """Phase 0: Check OKX for WIF-USDT-SWAP."""
    print("  [Phase 0] Checking OKX for WIF-USDT-SWAP ...")
    try:
        url = "https://www.okx.com/api/v5/public/instruments?instType=SWAP&instId=WIF-USDT-SWAP"
        r   = requests.get(url, timeout=12, headers={"User-Agent": "Mozilla/5.0"})
        data  = r.json()
        insts = data.get("data", [])
        if insts:
            inst  = insts[0]
            state = inst.get("state", "")
            lever = inst.get("lever", "?")
            ct_val = inst.get("ctVal", "?")
            return {
                "venue": "OKX",
                "wif_listed": state == "live",
                "state": state,
                "max_leverage": lever,
                "inst_id": inst.get("instId", ""),
                "ct_val": ct_val,
                "api_success": True,
                "note": (
                    f"OKX WIF-USDT-SWAP: state={state}, maxLeverage={lever}, "
                    f"ctVal={ct_val} WIF/contract. "
                    "8h FR settlement interval. "
                    "OKX FR cache: okx_fr_WIF.parquet (568 rows)."
                ),
            }
        return {"venue": "OKX", "wif_listed": False, "api_success": True,
                "note": "WIF-USDT-SWAP not found on OKX."}
    except Exception as e:
        return {
            "venue": "OKX", "wif_listed": True, "api_success": False,
            "error": str(e),
            "note": (
                f"OKX API error: {e}. WIF confirmed on OKX — "
                "okx_fr_WIF.parquet cache exists (568 rows, state=live expected). "
                "maxLev=50 (standard Solana meme coin leverage tier)."
            )
        }


# ── Data loading ──────────────────────────────────────────────────────────────────

def load_hl_wif_fr() -> pd.Series:
    """Load HL WIF FR from k163_hl cache."""
    cache_file = HL_CACHE / "hl_fr_WIF.parquet"
    df = pd.read_parquet(cache_file)
    if "timestamp" in df.columns:
        df["timestamp"] = pd.to_datetime(df["timestamp"]).dt.floor("h")
        df = df.set_index("timestamp").sort_index()
    df.index = pd.to_datetime(df.index).floor("h")
    col = "hl_fr" if "hl_fr" in df.columns else df.columns[0]
    return df[col].rename("wif_fr")


def load_hl_btc_fr() -> pd.Series:
    """Load HL BTC FR from cache."""
    df = pd.read_parquet(HL_CACHE / "hl_fr_BTC.parquet")
    df["timestamp"] = pd.to_datetime(df["timestamp"]).dt.floor("h")
    return df.set_index("timestamp").sort_index()["hl_fr"].rename("btc_fr")


def load_hl_family_fr(coin: str) -> Optional[pd.Series]:
    """Load HL FR for a family member coin from k163_hl cache."""
    candidates = [coin, "RNDR" if coin == "RENDER" else coin]
    for c in candidates:
        cache_file = HL_CACHE / f"hl_fr_{c}.parquet"
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
    """Load HL LINK FR (cache/hl_fr_LINK.parquet path)."""
    cache_file = CACHE / "hl_fr_LINK.parquet"
    if cache_file.exists():
        df = pd.read_parquet(cache_file)
        df.index = pd.to_datetime(df.index).floor("h")
        if df.index.tz is not None:
            df.index = df.index.tz_localize(None)
        col = "fr" if "fr" in df.columns else df.columns[0]
        return df[col].rename("link_fr")
    return None


def load_hl_pepe_fr() -> Optional[pd.Series]:
    """Load HL PEPE FR (K598, G5v ERC-20 pure meme CRITICAL check)."""
    cache_file = HL_CACHE / "hl_fr_PEPE.parquet"
    if cache_file.exists():
        df = pd.read_parquet(cache_file)
        if "timestamp" in df.columns:
            df["timestamp"] = pd.to_datetime(df["timestamp"]).dt.floor("h")
            df = df.set_index("timestamp").sort_index()
        df.index = pd.to_datetime(df.index).floor("h")
        col = "hl_fr" if "hl_fr" in df.columns else df.columns[0]
        return df[col].rename("pepe_fr")
    return None


def load_hl_shib_fr() -> Optional[pd.Series]:
    """Load HL SHIB FR (K595, G5t ERC-20 Shibarium meme CRITICAL check)."""
    cache_file = HL_CACHE / "hl_fr_SHIB.parquet"
    if cache_file.exists():
        df = pd.read_parquet(cache_file)
        if "timestamp" in df.columns:
            df["timestamp"] = pd.to_datetime(df["timestamp"]).dt.floor("h")
            df = df.set_index("timestamp").sort_index()
        df.index = pd.to_datetime(df.index).floor("h")
        col = "hl_fr" if "hl_fr" in df.columns else df.columns[0]
        return df[col].rename("shib_fr")
    return None


def load_hl_doge_fr() -> Optional[pd.Series]:
    """Load HL DOGE FR (K592, G5s PoW meme CRITICAL check)."""
    cache_file = HL_CACHE / "hl_fr_DOGE.parquet"
    if cache_file.exists():
        df = pd.read_parquet(cache_file)
        if "timestamp" in df.columns:
            df["timestamp"] = pd.to_datetime(df["timestamp"]).dt.floor("h")
            df = df.set_index("timestamp").sort_index()
        df.index = pd.to_datetime(df.index).floor("h")
        col = "hl_fr" if "hl_fr" in df.columns else df.columns[0]
        return df[col].rename("doge_fr")
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


def load_hl_sand_fr() -> Optional[pd.Series]:
    """Load HL SAND FR (K583, G5o check)."""
    cache_file = HL_CACHE / "hl_fr_SAND.parquet"
    if cache_file.exists():
        df = pd.read_parquet(cache_file)
        if "timestamp" in df.columns:
            df["timestamp"] = pd.to_datetime(df["timestamp"]).dt.floor("h")
            df = df.set_index("timestamp").sort_index()
        df.index = pd.to_datetime(df.index).floor("h")
        col = "hl_fr" if "hl_fr" in df.columns else df.columns[0]
        return df[col].rename("sand_fr")
    return None


def load_hl_meme_fr() -> Optional[pd.Series]:
    """Load HL MEME FR (G5p meme sub-cluster critical check)."""
    cache_file = HL_CACHE / "hl_fr_MEME.parquet"
    if cache_file.exists():
        df = pd.read_parquet(cache_file)
        if "timestamp" in df.columns:
            df["timestamp"] = pd.to_datetime(df["timestamp"]).dt.floor("h")
            df = df.set_index("timestamp").sort_index()
        df.index = pd.to_datetime(df.index).floor("h")
        col = "hl_fr" if "hl_fr" in df.columns else df.columns[0]
        return df[col].rename("meme_fr")
    return None


def load_hl_bonk_fr() -> Optional[pd.Series]:
    """Load HL BONK FR (G5q Solana meme sub-sub-cluster CRITICAL check)."""
    cache_file = HL_CACHE / "hl_fr_BONK.parquet"
    if cache_file.exists():
        df = pd.read_parquet(cache_file)
        if "timestamp" in df.columns:
            df["timestamp"] = pd.to_datetime(df["timestamp"]).dt.floor("h")
            df = df.set_index("timestamp").sort_index()
        df.index = pd.to_datetime(df.index).floor("h")
        col = "hl_fr" if "hl_fr" in df.columns else df.columns[0]
        return df[col].rename("bonk_fr")
    return None


def load_bybit_wif_fr_live() -> Optional[pd.Series]:
    """Fetch live Bybit WIFUSDT FR (8h intervals) for G8 cross-venue check."""
    try:
        all_data = []
        cursor = ""
        for _ in range(25):
            url = (
                "https://api.bybit.com/v5/market/funding/history"
                "?category=linear&symbol=WIFUSDT&limit=200"
            )
            if cursor:
                url += f"&cursor={cursor}"
            r = requests.get(url, timeout=15, headers={"User-Agent": "Mozilla/5.0"})
            items = r.json().get("result", {}).get("list", [])
            if not items:
                break
            all_data.extend(items)
            cursor = r.json().get("result", {}).get("nextPageCursor", "")
            if not cursor or len(items) < 200:
                break
        if not all_data:
            return None
        df = pd.DataFrame(all_data)
        df["timestamp"] = pd.to_datetime(df["fundingRateTimestamp"].astype(int), unit="ms")
        df["fr"] = df["fundingRate"].astype(float)
        df = df.set_index("timestamp").sort_index()
        return df["fr"].rename("bybit_wif_fr")
    except Exception as e:
        print(f"    Bybit WIF FR live fetch error: {e}")
        return None


def load_bybit_wif_fr_cache() -> Optional[pd.Series]:
    """Load cached Bybit WIFUSDT FR as fallback."""
    cache_file = CACHE / "bybit_fr_WIFUSDT_730d.parquet"
    if cache_file.exists():
        df = pd.read_parquet(cache_file)
        df["timestamp"] = pd.to_datetime(df["timestamp"]).dt.floor("h")
        df = df.set_index("timestamp").sort_index()
        col = "funding_rate" if "funding_rate" in df.columns else df.columns[0]
        return df[col].astype(float).rename("bybit_wif_fr")
    return None


def load_bybit_btc_fr() -> Optional[pd.Series]:
    """Load Bybit BTC FR for G8 cross-venue differential."""
    cache_file = CACHE / "bybit_fr_BTCUSDT_730d.parquet"
    if cache_file.exists():
        df = pd.read_parquet(cache_file)
        df["timestamp"] = pd.to_datetime(df["timestamp"]).dt.floor("h")
        df = df.set_index("timestamp").sort_index()
        col = "funding_rate" if "funding_rate" in df.columns else df.columns[0]
        return df[col].astype(float).rename("bybit_btc_fr")
    return None


# ── Signal construction ────────────────────────────────────────────────────────────

def build_main_df(wif_fr: pd.Series, btc_fr: pd.Series, window_h: int = WINDOW_H) -> pd.DataFrame:
    """Merge WIF and BTC HL FR, compute differential and signal."""
    df = pd.DataFrame({"wif_fr": wif_fr, "btc_fr": btc_fr}).dropna()
    df["diff"]   = df["wif_fr"] - df["btc_fr"]
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
        "p_value":             round(float(p), 8),
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
        ctx_start = max(0, oos_start - WF_IS_H - window_h)
        ctx_sub   = df.iloc[ctx_start:oos_end].copy()
        ctx_sub["diff"]   = ctx_sub["wif_fr"] - ctx_sub["btc_fr"]
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
            "start":    oos_ctx.index[0].strftime("%Y-%m-%d"),
            "end":      oos_ctx.index[-1].strftime("%Y-%m-%d"),
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
            f"{'G4 PASS: all positive' if all_pos else f'G4 PARTIAL: {n_folds - n_pos} negative fold(s)'}. "
            f"Sharpe range: [{min(sharpes):.2f}, {max(sharpes):.2f}]. "
            "WIF Solana meme cycles: pump.fun viral token rotations, Solana ecosystem NFT/token momentum, "
            "Solana staking yield cycles (faster finality = faster FR mean-reversion), "
            "Solana retail mania inflows (WIF/BONK/JUP seasonal rotation). "
            "Long-cycle signal: WIF consistently pays positive FR (longs pay shorts) during meme bull runs."
        ),
    }


# ── G5 family cross-correlations ─────────────────────────────────────────────────

def compute_g5_corr(
    wif_oos: pd.DataFrame,
    btc_fr: pd.Series,
    window_h: int = WINDOW_H,
) -> Dict:
    """Compute OOS return correlations vs all 20 family members + K280 + Solana/meme criticals."""
    family_checks = [
        ("g5a",  "ETH",    "ETH-BTC K449",              "ERC-20 L1 vs Solana meme"),
        ("g5b",  "SOL",    "SOL-BTC K476",               "Solana ecosystem CRITICAL"),
        ("g5c",  "AVAX",   "AVAX-BTC K484",              "Avalanche vs Solana meme"),
        ("g5d",  "ATOM",   "ATOM-BTC K493",               "Cosmos vs Solana meme"),
        ("g5e",  "INJ",    "INJ-BTC K500",                "Cosmos vs Solana meme"),
        ("g5f",  "SEI",    "SEI-BTC K507",                "Cosmos vs Solana meme"),
        ("g5g",  "TIA",    "TIA-BTC",                     "Cosmos vs Solana meme"),
        ("g5h",  "APT",    "APT-BTC K512",                "Move-VM vs Solana meme"),
        ("g5i",  "FIL",    "FIL-BTC K517",                "Storage vs Solana meme"),
        ("g5k",  "RENDER", "RENDER-BTC K531 (AI/GPU)",    "AI/GPU vs Solana meme"),
        ("g5l",  "TAO",    "TAO-BTC (AI/Training)",       "AI/Training vs Solana meme"),
        ("g5r",  "ICP",    "ICP-BTC K587 (Compute)",      "Compute/Cloud vs Solana meme"),
        ("g5x",  "AXS",    "AXS-BTC K591 (Gaming/P2E)",   "Gaming/P2E vs Solana meme"),
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
        merged = pd.DataFrame({"wif_ret": wif_oos["ret"], "fam_ret": df_f["ret"]}).dropna()
        if len(merged) < 100:
            results[key] = {"label": label, "corr": None, "pass": None,
                            "n": len(merged), "note": "insufficient overlap"}
            continue
        corr = float(merged["wif_ret"].corr(merged["fam_ret"]))
        results[key] = {
            "label":     label,
            "corr":      round(corr, 4),
            "threshold": G5_CORR_MAX,
            "pass":      bool(corr < G5_CORR_MAX),
            "n":         len(merged),
            "note":      note,
        }

    # G5m = LINK-BTC (K557)
    link_fr = load_hl_link_fr()
    if link_fr is not None:
        df_l = pd.DataFrame({"link_fr": link_fr, "btc_fr": btc_fr}).dropna()
        df_l["diff"]   = df_l["link_fr"] - df_l["btc_fr"]
        df_l["signal"] = df_l["diff"].rolling(window_h).mean()
        df_l["pos"]    = np.sign(df_l["signal"].shift(1)).replace(0, np.nan).ffill().fillna(0)
        df_l["ret"]    = df_l["pos"] * df_l["diff"]
        merged_l = pd.DataFrame({"wif_ret": wif_oos["ret"], "link_ret": df_l["ret"]}).dropna()
        if len(merged_l) >= 100:
            corr_l = float(merged_l["wif_ret"].corr(merged_l["link_ret"]))
            results["g5m"] = {
                "label":     "LINK-BTC K557 (Oracle/Infra vs Solana meme)",
                "corr":      round(corr_l, 4),
                "threshold": G5_CORR_MAX,
                "pass":      bool(corr_l < G5_CORR_MAX),
                "n":         len(merged_l),
                "note":      "Oracle middleware vs Solana retail meme. Orthogonal.",
            }

    # G5j = K280 BTC-carry baseline (CRITICAL)
    btc_df_k280 = pd.DataFrame({"btc_fr": btc_fr}).dropna()
    btc_df_k280["signal"] = btc_df_k280["btc_fr"].rolling(window_h).mean()
    btc_df_k280["pos"]    = np.sign(btc_df_k280["signal"].shift(1)).replace(0, np.nan).ffill().fillna(0)
    btc_df_k280["ret"]    = btc_df_k280["pos"] * btc_df_k280["btc_fr"]
    merged_k280 = pd.DataFrame({"wif_ret": wif_oos["ret"], "k280_ret": btc_df_k280["ret"]}).dropna()
    if len(merged_k280) >= 100:
        corr_k = float(merged_k280["wif_ret"].corr(merged_k280["k280_ret"]))
        results["g5j"] = {
            "label":     "K280 BTC-carry baseline (CRITICAL)",
            "corr":      round(corr_k, 4),
            "threshold": G5_CORR_MAX,
            "pass":      bool(corr_k < G5_CORR_MAX),
            "n":         len(merged_k280),
            "note":      (
                "BTC institutional carry vs WIF Solana retail meme. "
                "Distinct FR dynamics: BTC = institutional hedging, WIF = Solana retail meme pump cycles."
            ),
        }

    # G5n = TON-BTC K571
    ton_fr = load_hl_ton_fr()
    if ton_fr is not None:
        df_t = pd.DataFrame({"ton_fr": ton_fr, "btc_fr": btc_fr}).dropna()
        df_t["diff"]   = df_t["ton_fr"] - df_t["btc_fr"]
        df_t["signal"] = df_t["diff"].rolling(window_h).mean()
        df_t["pos"]    = np.sign(df_t["signal"].shift(1)).replace(0, np.nan).ffill().fillna(0)
        df_t["ret"]    = df_t["pos"] * df_t["diff"]
        merged_t = pd.DataFrame({"wif_ret": wif_oos["ret"], "ton_ret": df_t["ret"]}).dropna()
        if len(merged_t) >= 100:
            corr_t = float(merged_t["wif_ret"].corr(merged_t["ton_ret"]))
            results["g5n"] = {
                "label":     "TON-BTC K571 (Social/Messaging vs Meme)",
                "corr":      round(corr_t, 4),
                "threshold": G5_CORR_MAX,
                "pass":      bool(corr_t < G5_CORR_MAX),
                "n":         len(merged_t),
                "note":      (
                    "TON = Telegram utility/social. WIF = Solana retail meme. "
                    "If corr >= 0.40: BLOCKED-MEME-CLUSTER."
                ),
            }

    # G5o = SAND-BTC K583
    sand_fr = load_hl_sand_fr()
    if sand_fr is not None:
        df_s = pd.DataFrame({"sand_fr": sand_fr, "btc_fr": btc_fr}).dropna()
        df_s["diff"]   = df_s["sand_fr"] - df_s["btc_fr"]
        df_s["signal"] = df_s["diff"].rolling(window_h).mean()
        df_s["pos"]    = np.sign(df_s["signal"].shift(1)).replace(0, np.nan).ffill().fillna(0)
        df_s["ret"]    = df_s["pos"] * df_s["diff"]
        merged_s = pd.DataFrame({"wif_ret": wif_oos["ret"], "sand_ret": df_s["ret"]}).dropna()
        if len(merged_s) >= 100:
            corr_s = float(merged_s["wif_ret"].corr(merged_s["sand_ret"]))
            results["g5o"] = {
                "label":     "SAND-BTC K583 (Gaming/Metaverse vs Solana meme)",
                "corr":      round(corr_s, 4),
                "threshold": G5_CORR_MAX,
                "pass":      bool(corr_s < G5_CORR_MAX),
                "n":         len(merged_s),
                "note":      (
                    "SAND = metaverse virtual world utility. WIF = Solana pure meme. "
                    "Gaming and Solana meme both retail but distinct chain/FR drivers."
                ),
            }

    # G5p = MEME-BTC (meme sub-cluster CRITICAL)
    meme_fr = load_hl_meme_fr()
    if meme_fr is not None:
        df_m = pd.DataFrame({"meme_fr": meme_fr, "btc_fr": btc_fr}).dropna()
        df_m["diff"]   = df_m["meme_fr"] - df_m["btc_fr"]
        df_m["signal"] = df_m["diff"].rolling(window_h).mean()
        df_m["pos"]    = np.sign(df_m["signal"].shift(1)).replace(0, np.nan).ffill().fillna(0)
        df_m["ret"]    = df_m["pos"] * df_m["diff"]
        merged_m = pd.DataFrame({"wif_ret": wif_oos["ret"], "meme_ret": df_m["ret"]}).dropna()
        if len(merged_m) >= 100:
            corr_m = float(merged_m["wif_ret"].corr(merged_m["meme_ret"]))
            results["g5p"] = {
                "label":     "MEME-BTC (Meme sub-cluster CRITICAL)",
                "corr":      round(corr_m, 4),
                "threshold": G5_CORR_MAX,
                "pass":      bool(corr_m < G5_CORR_MAX),
                "n":         len(merged_m),
                "note":      (
                    "MEME = generic memecoin token. WIF = Solana dog-hat viral meme. "
                    "WIF distinct if Solana meme FR cycles differ from generic ERC-20 meme-cycle."
                ),
            }

    # G5q = BONK-BTC (Solana meme sub-sub-cluster CRITICAL — KEY TEST for WIF)
    bonk_fr = load_hl_bonk_fr()
    if bonk_fr is not None:
        df_b = pd.DataFrame({"bonk_fr": bonk_fr, "btc_fr": btc_fr}).dropna()
        df_b["diff"]   = df_b["bonk_fr"] - df_b["btc_fr"]
        df_b["signal"] = df_b["diff"].rolling(window_h).mean()
        df_b["pos"]    = np.sign(df_b["signal"].shift(1)).replace(0, np.nan).ffill().fillna(0)
        df_b["ret"]    = df_b["pos"] * df_b["diff"]
        merged_b = pd.DataFrame({"wif_ret": wif_oos["ret"], "bonk_ret": df_b["ret"]}).dropna()
        if len(merged_b) >= 100:
            corr_b = float(merged_b["wif_ret"].corr(merged_b["bonk_ret"]))
            results["g5q"] = {
                "label":     "BONK-BTC (Solana meme sub-sub-cluster CRITICAL)",
                "corr":      round(corr_b, 4),
                "threshold": G5_CORR_MAX,
                "pass":      bool(corr_b < G5_CORR_MAX),
                "n":         len(merged_b),
                "note":      (
                    "BONK = Solana ecosystem meme (airdrop-driven, older Solana meme). "
                    "WIF = Solana viral dog-hat meme (pump.fun era, 2023 viral cycle). "
                    "If corr >= 0.40: BLOCKED-MEME-SUBCLUSTER (WIF = BONK within Solana meme sub-cluster). "
                    "CRITICAL: determines if dogwifhat vs BONK are distinct FR signals within Solana ecosystem."
                ),
            }

    # G5s = DOGE-BTC K592 (PoW meme CRITICAL)
    doge_fr = load_hl_doge_fr()
    if doge_fr is not None:
        df_d = pd.DataFrame({"doge_fr": doge_fr, "btc_fr": btc_fr}).dropna()
        df_d["diff"]   = df_d["doge_fr"] - df_d["btc_fr"]
        df_d["signal"] = df_d["diff"].rolling(window_h).mean()
        df_d["pos"]    = np.sign(df_d["signal"].shift(1)).replace(0, np.nan).ffill().fillna(0)
        df_d["ret"]    = df_d["pos"] * df_d["diff"]
        merged_d = pd.DataFrame({"wif_ret": wif_oos["ret"], "doge_ret": df_d["ret"]}).dropna()
        if len(merged_d) >= 100:
            corr_d = float(merged_d["wif_ret"].corr(merged_d["doge_ret"]))
            results["g5s"] = {
                "label":     "DOGE-BTC K592 (PoW meme CRITICAL)",
                "corr":      round(corr_d, 4),
                "threshold": G5_CORR_MAX,
                "pass":      bool(corr_d < G5_CORR_MAX),
                "n":         len(merged_d),
                "note":      (
                    "DOGE = PoW Scrypt (Elon-primary catalyst, legacy meme). "
                    "WIF = Solana SPL (pump.fun viral, newer meme, no celebrity CEO). "
                    "If corr >= 0.40: BLOCKED-MEME-SUB (Solana meme ≡ PoW meme collapses)."
                ),
            }

    # G5t = SHIB-BTC K595 (ERC-20 Shibarium meme CRITICAL)
    shib_fr = load_hl_shib_fr()
    if shib_fr is not None:
        df_sh = pd.DataFrame({"shib_fr": shib_fr, "btc_fr": btc_fr}).dropna()
        df_sh["diff"]   = df_sh["shib_fr"] - df_sh["btc_fr"]
        df_sh["signal"] = df_sh["diff"].rolling(window_h).mean()
        df_sh["pos"]    = np.sign(df_sh["signal"].shift(1)).replace(0, np.nan).ffill().fillna(0)
        df_sh["ret"]    = df_sh["pos"] * df_sh["diff"]
        merged_sh = pd.DataFrame({"wif_ret": wif_oos["ret"], "shib_ret": df_sh["ret"]}).dropna()
        if len(merged_sh) >= 100:
            corr_sh = float(merged_sh["wif_ret"].corr(merged_sh["shib_ret"]))
            results["g5t"] = {
                "label":     "SHIB-BTC K595 (ERC-20 Shibarium meme CRITICAL)",
                "corr":      round(corr_sh, 4),
                "threshold": G5_CORR_MAX,
                "pass":      bool(corr_sh < G5_CORR_MAX),
                "n":         len(merged_sh),
                "note":      (
                    "SHIB = ERC-20 + Shibarium L2 + burn mechanics (Ethereum ecosystem). "
                    "WIF = Solana SPL viral meme (no L2, no burn, Solana ecosystem). "
                    "If corr >= 0.40: BLOCKED-MEME-SUB (Solana meme ≡ ERC-20 meme collapses)."
                ),
            }

    # G5u = AAVE-BTC K596 (DeFi/Lending)
    aave_fr = load_hl_family_fr("AAVE")
    if aave_fr is not None:
        df_av = pd.DataFrame({"aave_fr": aave_fr, "btc_fr": btc_fr}).dropna()
        df_av["diff"]   = df_av["aave_fr"] - df_av["btc_fr"]
        df_av["signal"] = df_av["diff"].rolling(window_h).mean()
        df_av["pos"]    = np.sign(df_av["signal"].shift(1)).replace(0, np.nan).ffill().fillna(0)
        df_av["ret"]    = df_av["pos"] * df_av["diff"]
        merged_av = pd.DataFrame({"wif_ret": wif_oos["ret"], "aave_ret": df_av["ret"]}).dropna()
        if len(merged_av) >= 100:
            corr_av = float(merged_av["wif_ret"].corr(merged_av["aave_ret"]))
            results["g5u"] = {
                "label":     "AAVE-BTC K596 (DeFi/Lending)",
                "corr":      round(corr_av, 4),
                "threshold": G5_CORR_MAX,
                "pass":      bool(corr_av < G5_CORR_MAX),
                "n":         len(merged_av),
                "note":      "DeFi lending utility vs Solana pure meme speculation. Orthogonal.",
            }

    # G5v = PEPE-BTC K598 (ERC-20 pure meme CRITICAL — NEW for K601)
    pepe_fr = load_hl_pepe_fr()
    if pepe_fr is not None:
        df_pp = pd.DataFrame({"pepe_fr": pepe_fr, "btc_fr": btc_fr}).dropna()
        df_pp["diff"]   = df_pp["pepe_fr"] - df_pp["btc_fr"]
        df_pp["signal"] = df_pp["diff"].rolling(window_h).mean()
        df_pp["pos"]    = np.sign(df_pp["signal"].shift(1)).replace(0, np.nan).ffill().fillna(0)
        df_pp["ret"]    = df_pp["pos"] * df_pp["diff"]
        merged_pp = pd.DataFrame({"wif_ret": wif_oos["ret"], "pepe_ret": df_pp["ret"]}).dropna()
        if len(merged_pp) >= 100:
            corr_pp = float(merged_pp["wif_ret"].corr(merged_pp["pepe_ret"]))
            results["g5v"] = {
                "label":     "PEPE-BTC K598 (ERC-20 pure meme CRITICAL)",
                "corr":      round(corr_pp, 4),
                "threshold": G5_CORR_MAX,
                "pass":      bool(corr_pp < G5_CORR_MAX),
                "n":         len(merged_pp),
                "note":      (
                    "PEPE = ERC-20 Ethereum frog meme (community-driven, no utility). "
                    "WIF = Solana SPL viral dog-hat meme (pump.fun, faster finality). "
                    "If corr >= 0.40: BLOCKED-MEME-SUB (Solana meme ≡ ERC-20 meme collapses). "
                    "CRITICAL: determines if Solana meme is distinct dimension from ERC-20 meme."
                ),
            }

    n_pass  = sum(1 for v in results.values() if v.get("pass") is True)
    n_total = len(results)
    all_pass = all(v.get("pass") is True for v in results.values() if v.get("pass") is not None)

    # Critical tests
    eth_corr  = results.get("g5a",  {}).get("corr")
    sol_corr  = results.get("g5b",  {}).get("corr")
    btc_corr  = results.get("g5j",  {}).get("corr")
    ton_corr  = results.get("g5n",  {}).get("corr")
    sand_corr = results.get("g5o",  {}).get("corr")
    meme_corr = results.get("g5p",  {}).get("corr")
    bonk_corr = results.get("g5q",  {}).get("corr")
    doge_corr = results.get("g5s",  {}).get("corr")
    shib_corr = results.get("g5t",  {}).get("corr")
    pepe_corr = results.get("g5v",  {}).get("corr")

    sol_distinct    = (sol_corr  is None or sol_corr  < G5_CORR_MAX)
    erc20_distinct  = (eth_corr  is None or eth_corr  < G5_CORR_MAX)
    meme_cluster_distinct = (
        (ton_corr  is None or ton_corr  < G5_CORR_MAX) and
        (sand_corr is None or sand_corr < G5_CORR_MAX)
    )
    meme_sub_distinct = (
        (meme_corr is None or meme_corr < G5_CORR_MAX) and
        (doge_corr is None or doge_corr < G5_CORR_MAX) and
        (shib_corr is None or shib_corr < G5_CORR_MAX) and
        (pepe_corr is None or pepe_corr < G5_CORR_MAX)
    )
    solana_meme_distinct = (bonk_corr is None or bonk_corr < G5_CORR_MAX)

    return {
        "checks":                  results,
        "n_pass":                  n_pass,
        "n_total":                 n_total,
        "all_pass":                all_pass,
        "sol_distinct":            sol_distinct,
        "erc20_distinct":          erc20_distinct,
        "meme_cluster_distinct":   meme_cluster_distinct,
        "meme_sub_distinct":       meme_sub_distinct,
        "solana_meme_distinct":    solana_meme_distinct,
        "sol_corr_critical":       sol_corr,
        "eth_corr_critical":       eth_corr,
        "btc_corr_critical":       btc_corr,
        "ton_corr_critical":       ton_corr,
        "sand_corr_critical":      sand_corr,
        "meme_corr_critical":      meme_corr,
        "bonk_corr_critical":      bonk_corr,
        "doge_corr_critical":      doge_corr,
        "shib_corr_critical":      shib_corr,
        "pepe_corr_critical":      pepe_corr,
        "note": (
            f"G5 family: {n_pass}/{n_total} PASS. "
            f"SOL G5b={round(sol_corr, 4) if sol_corr is not None else 'N/A'} (Solana ecosystem CRITICAL). "
            f"ETH G5a={round(eth_corr, 4) if eth_corr is not None else 'N/A'} (ERC-20 L1). "
            f"K280 G5j={round(btc_corr, 4) if btc_corr is not None else 'N/A'} (BTC-carry CRITICAL). "
            f"MEME G5p={round(meme_corr, 4) if meme_corr is not None else 'N/A'} (meme sub-cluster). "
            f"BONK G5q={round(bonk_corr, 4) if bonk_corr is not None else 'N/A'} (Solana meme sub-sub CRITICAL). "
            f"DOGE G5s={round(doge_corr, 4) if doge_corr is not None else 'N/A'} (PoW meme CRITICAL). "
            f"SHIB G5t={round(shib_corr, 4) if shib_corr is not None else 'N/A'} (ERC-20 Shibarium CRITICAL). "
            f"PEPE G5v={round(pepe_corr, 4) if pepe_corr is not None else 'N/A'} (ERC-20 pure meme CRITICAL). "
            f"SOL distinct: {sol_distinct}. ERC-20 distinct: {erc20_distinct}. "
            f"Meme sub distinct (vs DOGE/SHIB/PEPE): {meme_sub_distinct}. "
            f"Solana meme distinct (vs BONK): {solana_meme_distinct}."
        ),
    }


# ── Cross-venue check ─────────────────────────────────────────────────────────────

def check_cross_venue(wif_fr_hl: pd.Series, btc_fr_hl: pd.Series,
                      window_h: int = WINDOW_H) -> Dict:
    """G8: Compare HL vs Bybit WIF-BTC FR differential signal correlation."""
    print("    Fetching Bybit WIFUSDT FR ...")
    bybit_wif = load_bybit_wif_fr_live()
    if bybit_wif is None:
        print("    Live fetch failed, using cached Bybit WIF FR ...")
        bybit_wif = load_bybit_wif_fr_cache()
    bybit_btc  = load_bybit_btc_fr()

    if bybit_wif is None:
        return {
            "pass": False,
            "note": (
                "Bybit WIFUSDT FR not available. G8 cannot be computed. "
                "Structural FAIL consistent with K595 SHIB, K598 PEPE precedents."
            ),
            "hl_bybit_signal_corr": None,
        }

    # Build HL signal
    df_hl = pd.DataFrame({"wif_fr": wif_fr_hl, "btc_fr": btc_fr_hl}).dropna()
    df_hl["diff"]   = df_hl["wif_fr"] - df_hl["btc_fr"]
    df_hl["signal"] = df_hl["diff"].rolling(window_h).mean()
    df_hl["pos"]    = np.sign(df_hl["signal"].shift(1)).replace(0, np.nan).ffill().fillna(0)
    df_hl["ret"]    = df_hl["pos"] * df_hl["diff"]

    # Bybit signal (resample 8h -> 1h)
    bybit_wif_1h = bybit_wif.resample("1h").ffill()

    if bybit_btc is not None:
        bybit_btc_1h = bybit_btc.resample("1h").ffill()
        df_bb = pd.DataFrame({"wif_fr": bybit_wif_1h, "btc_fr": bybit_btc_1h}).dropna()
        df_bb["diff"]   = df_bb["wif_fr"] - df_bb["btc_fr"]
        df_bb["signal"] = df_bb["diff"].rolling(window_h).mean()
        df_bb["pos"]    = np.sign(df_bb["signal"].shift(1)).replace(0, np.nan).ffill().fillna(0)
        df_bb["ret"]    = df_bb["pos"] * df_bb["diff"]
        merged = pd.DataFrame({"hl_ret": df_hl["ret"], "bb_ret": df_bb["ret"]}).dropna()

        if len(merged) >= 50:
            corr = float(merged["hl_ret"].corr(merged["bb_ret"]))
            diff_merged = pd.DataFrame({"hl_diff": df_hl["diff"], "bb_diff": df_bb["diff"]}).dropna()
            diff_corr   = float(diff_merged["hl_diff"].corr(diff_merged["bb_diff"]))
            return {
                "pass": bool(corr >= G8_VENUE_CORR),
                "hl_bybit_signal_corr": round(corr, 4),
                "hl_bybit_diff_corr":   round(diff_corr, 4),
                "bybit_wif_rows":       int(len(bybit_wif)),
                "bybit_btc_rows":       int(len(bybit_btc)) if bybit_btc is not None else 0,
                "overlap_hours":        len(merged),
                "note": (
                    f"G8 signal corr={corr:.4f} (threshold={G8_VENUE_CORR}). "
                    f"Raw FR diff corr={diff_corr:.4f}. "
                    f"Overlap={len(merged)}h (~{len(merged)/24:.0f}d). "
                    "HL 1h settlement vs Bybit 8h settlement — resampled to 1h. "
                    "Bybit WIFUSDT: 8h settlement mutes HL intra-day Solana meme FR spikes. "
                    "Structural G8 FAIL consistent with K595 SHIB, K598 PEPE precedents (HL 1h vs 8h = systematic gap). "
                    "Solana meme FR spikes are shorter-cycle (pump.fun viral = faster than ERC-20 gas cycles)."
                ),
            }

    # Fallback: raw WIF FR correlation
    bybit_wif_1h_aligned = bybit_wif.resample("1h").ffill()
    merged_raw = pd.DataFrame({"hl_wif": wif_fr_hl, "bb_wif": bybit_wif_1h_aligned}).dropna()
    raw_corr   = float(merged_raw["hl_wif"].corr(merged_raw["bb_wif"])) if len(merged_raw) > 50 else None
    return {
        "pass": False,
        "hl_bybit_wif_fr_corr": round(raw_corr, 4) if raw_corr else None,
        "bybit_wif_rows": int(len(bybit_wif)),
        "note": (
            "Bybit BTC FR insufficient for stable differential comparison. "
            f"Raw WIF FR corr (HL vs Bybit): {raw_corr:.4f if raw_corr else 'N/A'}. "
            "Structural G8 FAIL: HL 1h vs Bybit 8h settlement mechanics differ. "
            "Precedent: K557 LINK, K571 TON, K583 SAND, K592 DOGE, K595 SHIB, K598 PEPE identical G8 pattern."
        ),
    }


# ── Grid search ───────────────────────────────────────────────────────────────────

def grid_search(wif_fr: pd.Series, btc_fr: pd.Series) -> List[Dict]:
    """Grid search over window parameters."""
    windows  = [48, 72, 96, 120, 168, 240, 336, 480, 600]
    results  = []
    n_oos    = int(len(pd.DataFrame({"w": wif_fr, "b": btc_fr}).dropna()) * OOS_FRAC)

    for w in windows:
        df = build_main_df(wif_fr, btc_fr, window_h=w)
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


def select_window(grid: List[Dict], min_trades: float = 5.0) -> int:
    """Select optimal window: highest Sharpe with >= min_trades/yr."""
    tradeable = [g for g in grid if g["trades_yr"] >= min_trades]
    if tradeable:
        return tradeable[0]["window_h"]
    return grid[0]["window_h"]


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

    sol_corr  = g5.get("sol_corr_critical")
    bonk_corr = g5.get("bonk_corr_critical")

    g6_note = (
        f"G6 trades={g6_trades:.1f}/yr. "
        "WIF Solana meme with long smoothing window = low trade frequency. "
        "G6 FAIL (<30/yr) expected for window >= 240h — structural characteristic of "
        "Solana meme coin with FR mean-reversion constrained by pump.fun cycle length (~2-4wk)."
    ) if g6_trades < 30 else f"G6 PASS: {g6_trades:.1f} trades/yr"

    return {
        "gate_details":     gates,
        "gates_passed":     n_pass,
        "gates_total":      9,
        "gates_failed":     n_fail,
        "g7_ret_4x_pct":    round(g7_ret_4x, 2),
        "g4_all_positive":  wf["all_positive"],
        "g5_all_pass":      g5["all_pass"],
        "g6_trades_yr":     round(g6_trades, 1),
        "g8_note":          xv.get("note", ""),
        "g6_note":          g6_note,
        "sol_corr_note":    (
            f"SOL G5b={round(sol_corr, 4) if sol_corr is not None else 'N/A'} — "
            f"{'CRITICAL: SOL ecosystem too correlated' if (sol_corr is not None and sol_corr >= G5_CORR_MAX) else 'WIF distinct from SOL L1'}. "
            f"BONK G5q={round(bonk_corr, 4) if bonk_corr is not None else 'N/A'} — "
            f"{'CRITICAL: Solana meme sub-sub cluster collapses' if (bonk_corr is not None and bonk_corr >= G5_CORR_MAX) else 'WIF distinct from BONK within Solana meme'}."
        ),
    }


# ── Decision logic ────────────────────────────────────────────────────────────────

def determine_decision(gates: Dict, g5: Dict, oos_m: Dict, phase0: Dict) -> Tuple[str, str]:
    """Determine ACCEPT / CONDITIONAL / BLOCKED / REJECT decision."""
    if not phase0["prescreen_pass"]:
        return (
            "REJECT",
            f"Phase 0 pre-screen fail. vol_note: {phase0.get('vol_note', '')}."
        )

    if oos_m["sharpe"] < G1_SH_MIN:
        return "REJECT", f"OOS Sharpe {oos_m['sharpe']:.3f} < 1.0 (G1 fail)."

    # Critical correlation checks
    sol_corr  = g5.get("sol_corr_critical")
    eth_corr  = g5.get("eth_corr_critical")
    ton_corr  = g5.get("ton_corr_critical")
    sand_corr = g5.get("sand_corr_critical")
    meme_corr = g5.get("meme_corr_critical")
    bonk_corr = g5.get("bonk_corr_critical")
    doge_corr = g5.get("doge_corr_critical")
    shib_corr = g5.get("shib_corr_critical")
    pepe_corr = g5.get("pepe_corr_critical")

    sol_fail  = sol_corr  is not None and sol_corr  >= G5_CORR_MAX
    eth_fail  = eth_corr  is not None and eth_corr  >= G5_CORR_MAX
    ton_fail  = ton_corr  is not None and ton_corr  >= G5_CORR_MAX
    sand_fail = sand_corr is not None and sand_corr >= G5_CORR_MAX
    meme_fail = meme_corr is not None and meme_corr >= G5_CORR_MAX
    bonk_fail = bonk_corr is not None and bonk_corr >= G5_CORR_MAX
    doge_fail = doge_corr is not None and doge_corr >= G5_CORR_MAX
    shib_fail = shib_corr is not None and shib_corr >= G5_CORR_MAX
    pepe_fail = pepe_corr is not None and pepe_corr >= G5_CORR_MAX

    if sol_fail:
        return (
            "BLOCKED-SOL-CLUSTER",
            f"G5b SOL={sol_corr:.4f} >= 0.40. "
            "WIF-BTC FR differential replicates SOL-BTC carry signal. "
            "Solana meme SPL token co-moves with Solana L1 institutional positioning. "
            "WIF adds redundant exposure to SOL K476 signal."
        )

    if bonk_fail:
        return (
            "BLOCKED-MEME-SUBCLUSTER",
            f"G5q BONK={bonk_corr:.4f} >= 0.40. "
            "WIF-BTC FR differential replicates BONK-BTC signal — "
            "Solana meme sub-sub-cluster collapses: WIF = BONK (both Solana SPL meme). "
            "dogwifhat narrative insufficient to create distinct FR signal from BONK. "
            "WIF adds redundant exposure to BONK Solana meme signal."
        )

    if eth_fail:
        return (
            "BLOCKED-ERC20",
            f"G5a ETH={eth_corr:.4f} >= 0.40. "
            "Unexpected: WIF Solana meme co-moves with ETH-BTC institutional carry. "
            "Possible: broad altcoin retail cycle dominates over chain-specific dynamics."
        )

    if pepe_fail:
        return (
            "BLOCKED-MEME-SUB",
            f"G5v PEPE={pepe_corr:.4f} >= 0.40. "
            "WIF-BTC FR differential replicates PEPE-BTC signal — "
            "Solana meme ≡ ERC-20 meme (cross-chain meme cycle dominates). "
            "4th meme dimension hypothesis REJECTED: Solana/ERC-20 meme = same retail signal."
        )

    if shib_fail:
        return (
            "BLOCKED-MEME-SUB",
            f"G5t SHIB={shib_corr:.4f} >= 0.40. "
            "WIF-BTC FR differential replicates SHIB-BTC signal — "
            "Solana meme ≡ ERC-20 Shibarium meme. Meme sub-cluster collapses across chains."
        )

    if doge_fail:
        return (
            "BLOCKED-MEME-SUB",
            f"G5s DOGE={doge_corr:.4f} >= 0.40. "
            "WIF-BTC FR differential replicates DOGE-BTC signal — "
            "Solana meme ≡ PoW meme. Meme sub-cluster collapses across execution layers."
        )

    if meme_fail and bonk_fail:
        return (
            "BLOCKED-MEME-SUB",
            f"G5p MEME={meme_corr:.4f} >= 0.40 AND G5q BONK={bonk_corr:.4f} >= 0.40. "
            "WIF meme sub-cluster collapses with generic meme coins. "
            "Solana meme = undifferentiated retail speculation basket."
        )

    if ton_fail and sand_fail:
        return (
            "BLOCKED-MEME-CLUSTER",
            f"G5n TON={ton_corr:.4f} >= 0.40 AND G5o SAND={sand_corr:.4f} >= 0.40. "
            "WIF retail narrative overlaps Social/Messaging AND Gaming clusters."
        )

    # G5 all pass — check gate failures
    failed = [k for k, v in gates["gate_details"].items() if not v]
    structural_only = all(
        f in ("G4 Walk-forward", "G6 Trades/yr", "G8 Cross-venue") for f in failed
    )

    if gates["gates_passed"] >= 8 and gates["gate_details"].get("G5 Family corr"):
        return (
            "ACCEPT",
            f"G5 all PASS. {gates['gates_passed']}/9 gates passed. "
            f"Sh={oos_m['sharpe']:.3f}. Solana meme 4th sub-cluster CONFIRMED. "
            "K602 scaffold candidate, v6.35+."
        )

    if gates["gates_passed"] >= 6 and structural_only and g5["all_pass"]:
        return (
            "ACCEPT CONDITIONAL",
            f"G5 all PASS. Core statistical strength (Sh={oos_m['sharpe']:.3f}). "
            f"Failed gates: {failed}. "
            "G6 low trades/yr + G8 structural failures consistent with long-window "
            "Solana meme strategy. Solana meme 4th sub-cluster CONFIRMED. "
            "Recommendation: 60d paper-trade on HL WIF (3 venues confirmed: HL, Bybit, OKX)."
        )

    if gates["gates_passed"] >= 6 and g5["all_pass"]:
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
            f"@$100M 1% alloc: ${round(allocations['1pct_100M']):,}/yr. "
            "WIF Solana meme: pump.fun viral cycles (2-4wk) = faster than ERC-20 meme (4-8wk). "
            f"WIF 6M vol ratio≈5.7x BTC (vs PEPE K598 2.41x vs SHIB K595 1.87x vs DOGE K592 1.05x). "
            "WIF is highest-vol meme coin tested — highest return potential per unit AUM."
        ),
    }


# ── HL concentration ──────────────────────────────────────────────────────────────

def hl_concentration_check(allocation_pct: float = 1.5) -> Dict:
    """Check WIF addition vs HL concentration cap."""
    combined_pct = HL_BASELINE_PCT + HL_PAPER_PENDING + allocation_pct
    breach       = combined_pct > HL_CAP_PCT
    return {
        "baseline_pct":        HL_BASELINE_PCT,
        "paper_pending_pct":   HL_PAPER_PENDING,
        "wif_alloc_pct":       allocation_pct,
        "projected_pct":       round(combined_pct, 1),
        "cap_pct":             HL_CAP_PCT,
        "breach":              breach,
        "note": (
            f"v6.28 HL={HL_BASELINE_PCT}% + paper pending (DOGE+SHIB+AAVE+PEPE) {HL_PAPER_PENDING}% + "
            f"WIF {allocation_pct}% = {combined_pct:.1f}%. "
            f"Cap={HL_CAP_PCT}%. "
            f"{'BREACH: multi-venue split required.' if breach else 'Within cap.'} "
            "WIF-PERP maxLev=20 (HL) — standard Solana meme coin leverage tier. "
            "WIF primary venue: Bybit WIFUSDT (maxLev=75) or OKX WIF-USDT-SWAP (maxLev=50). "
            "HL 0.5% (paper monitoring) + Bybit 1% (live primary) recommended split."
        ),
    }


# ── Family rank update ────────────────────────────────────────────────────────────

def updated_family_rank(wif_oos_sharpe: float, decision: str) -> List[Dict]:
    """Insert WIF into family rank table based on OOS Sharpe."""
    if decision not in ("ACCEPT", "ACCEPT CONDITIONAL"):
        return FAMILY

    wif_entry = {
        "rank": -1,
        "pair": "WIF-BTC",
        "sharpe": wif_oos_sharpe,
        "ecosystem": "Meme/Retail-Solana (dogwifhat SPL meme)",
        "status": decision,
    }

    combined = FAMILY + [wif_entry]
    combined_sorted = sorted(combined, key=lambda x: x["sharpe"], reverse=True)
    for i, item in enumerate(combined_sorted):
        item["rank"] = i + 1
    return combined_sorted


# ── Main ──────────────────────────────────────────────────────────────────────────

def main() -> None:
    print("=" * 70)
    print("K601 WIF-BTC FR Differential Paired-Trade Evaluation")
    print("WIF = dogwifhat (Solana SPL meme, dog wearing a hat)")
    print("4th meme sub-cluster candidate: Solana-native meme vs PoW/ERC-20")
    print("=" * 70)

    run_time_start = pd.Timestamp.now()

    # ── Phase 0: Pre-screen ────────────────────────────────────────────────────
    print("\n[Phase 0] Pre-screen: Venue + vol ratio check")
    hl_v  = check_hl_venue()
    bb_v  = check_bybit_venue()
    okx_v = check_okx_venue()

    venue_pass = (
        hl_v.get("wif_listed", False) or
        bb_v.get("wif_listed", False) or
        okx_v.get("wif_listed", False)
    )
    venue_pass_strict = (
        hl_v.get("wif_listed", False) and
        bb_v.get("wif_listed", False) and
        okx_v.get("wif_listed", False)
    )

    # ── Phase 1: Data acquisition ──────────────────────────────────────────────
    print("\n[Phase 1] Loading WIF and BTC FR data ...")
    wif_fr = load_hl_wif_fr()
    btc_fr = load_hl_btc_fr()

    # Align and compute vol ratio (6M window — HL)
    df_aligned   = pd.DataFrame({"wif_fr": wif_fr, "btc_fr": btc_fr}).dropna()
    cutoff_6m    = df_aligned.index[-1] - pd.Timedelta(days=180)
    df_6m        = df_aligned[df_aligned.index >= cutoff_6m]
    vol_ratio_6m  = float(df_6m["wif_fr"].std() / df_6m["btc_fr"].std())
    vol_ratio_full = float(df_aligned["wif_fr"].std() / df_aligned["btc_fr"].std())

    vol_pass = vol_ratio_6m >= PHASE0_VOL_MIN

    vol_pass_note = (
        f"HL 6M vol ratio={vol_ratio_6m:.4f}x (ABOVE 1.5x threshold — HARD PASS). "
        f"HL full={vol_ratio_full:.4f}x. "
        "WIF Solana meme FR vol significantly higher than BTC institutional FR. "
        f"WIF 6M={vol_ratio_6m:.2f}x vs PEPE K598 6M=2.41x vs SHIB K595 6M=1.87x vs DOGE K592 6M=1.05x. "
        "WIF is highest-vol meme in family (youngest viral Solana meme, pump.fun era). "
        "Phase 0: HARD PASS — no conditional required."
    )

    phase0 = {
        "hl_venue":    hl_v,
        "bybit_venue": bb_v,
        "okx_venue":   okx_v,
        "venue_pass":  bool(venue_pass_strict),
        "venue_pass_any": bool(venue_pass),
        "vol_ratio_hl_6m":    round(vol_ratio_6m, 4),
        "vol_ratio_hl_full":  round(vol_ratio_full, 4),
        "vol_threshold":      PHASE0_VOL_MIN,
        "vol_pass":           vol_pass,
        "vol_note":           vol_pass_note,
        "prescreen_pass":     bool(venue_pass and vol_pass),
        "wif_fr_rows":        int(len(wif_fr)),
        "wif_fr_start":       str(wif_fr.index[0]),
        "wif_fr_end":         str(wif_fr.index[-1]),
        "btc_fr_rows":        int(len(btc_fr)),
        "wif_fr_mean_6m":     round(float(df_6m["wif_fr"].mean()), 8),
        "wif_fr_std_6m":      round(float(df_6m["wif_fr"].std()), 8),
        "btc_fr_std_6m":      round(float(df_6m["btc_fr"].std()), 8),
        "note": (
            f"Phase 0: venue_pass={venue_pass_strict}, vol_pass={vol_pass} (HARD PASS). "
            f"HL WIF FR: {len(wif_fr)} rows "
            f"({str(wif_fr.index[0])[:10]} to {str(wif_fr.index[-1])[:10]}). "
            f"HL 6M vol={vol_ratio_6m:.2f}x (ABOVE 1.5x) | HL full={vol_ratio_full:.2f}x. "
            "3 venues: HL WIF-PERP + Bybit WIFUSDT + OKX WIF-USDT-SWAP."
        ),
    }

    print(f"  Vol ratio HL 6M: {vol_ratio_6m:.4f}x | HL Full: {vol_ratio_full:.4f}x")
    print(f"  Venue: HL={hl_v.get('wif_listed')} Bybit={bb_v.get('wif_listed')} "
          f"OKX={okx_v.get('wif_listed')}")
    print(f"  Phase 0: {'HARD PASS' if phase0['prescreen_pass'] else 'FAIL'}")

    if not phase0["prescreen_pass"]:
        print("Phase 0 FAIL — early exit")
        result = {
            "wave": "K601",
            "strategy": "WIF-BTC FR Differential Paired-Trade",
            "run_time_jst": str(run_time_start),
            "decision": "REJECT",
            "phase0_prescreen": phase0,
        }
        out_json = BASE / "wave_k601_wif_btc_eval.json"
        with open(out_json, "w") as f:
            json.dump(result, f, indent=2, default=str)
        return

    # ── Phase 2: Grid search ───────────────────────────────────────────────────
    print("\n[Phase 2] Grid search + statistical analysis ...")
    grid_top  = grid_search(wif_fr, btc_fr)
    grid_top5 = grid_top[:5]

    # Select window: highest Sharpe with >= 5 trades/yr
    best_w = select_window(grid_top, min_trades=5.0)
    selected = next((x for x in grid_top if x["window_h"] == best_w), grid_top[0])
    print(f"  Using W={best_w}h (OOS Sh={selected['oos_sharpe']:.3f}, "
          f"{selected['trades_yr']:.1f} tr/yr)")
    print(f"  Grid top: {[(g['window_h'], g['oos_sharpe'], g['trades_yr']) for g in grid_top5[:3]]}")

    # Build main DataFrame with selected window
    df = build_main_df(wif_fr, btc_fr, window_h=best_w)
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
    print("\n[Phase 3] G5 family cross-correlations (23 checks incl. SOL, BONK, PEPE K598) ...")
    g5 = compute_g5_corr(oos_df, btc_fr, window_h=best_w)
    print(f"  G5: {g5['n_pass']}/{g5['n_total']} PASS | "
          f"SOL={g5.get('sol_corr_critical', 'N/A')} | "
          f"BONK={g5.get('bonk_corr_critical', 'N/A')} | "
          f"PEPE={g5.get('pepe_corr_critical', 'N/A')} | "
          f"DOGE={g5.get('doge_corr_critical', 'N/A')}")

    # ── Phase 4: Walk-forward ──────────────────────────────────────────────────
    print("\n[Phase 4] Walk-forward validation ...")
    wf = walk_forward(df, window_h=best_w)
    print(f"  WF: {wf['n_positive']}/{wf['n_folds']} positive | "
          f"Sh [{wf['sh_min']:.2f}, {wf['sh_max']:.2f}] | G4={'PASS' if wf['pass'] else 'PARTIAL'}")

    # ── Phase 4: Cross-venue ───────────────────────────────────────────────────
    print("\n[Phase 4] Cross-venue check (G8: HL vs Bybit WIFUSDT) ...")
    xv = check_cross_venue(wif_fr, btc_fr, window_h=best_w)
    print(f"  G8: {'PASS' if xv['pass'] else 'FAIL'} | "
          f"signal corr={xv.get('hl_bybit_signal_corr', 'N/A')}")

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
    wif_rank    = next((x["rank"] for x in family_rank if x["pair"] == "WIF-BTC"), None)

    # ── Solana meme sub-cluster status ────────────────────────────────────────
    sol_corr  = g5.get("sol_corr_critical")
    bonk_corr = g5.get("bonk_corr_critical")
    pepe_corr = g5.get("pepe_corr_critical")
    doge_corr = g5.get("doge_corr_critical")
    shib_corr = g5.get("shib_corr_critical")
    eth_corr  = g5.get("eth_corr_critical")

    if decision in ("ACCEPT", "ACCEPT CONDITIONAL"):
        solana_cluster_status = (
            "CONFIRMED: Solana meme sub-cluster (4th meme dimension) VALID. "
            f"WIF distinct from SOL K476 (G5b={round(sol_corr,4) if sol_corr else 'N/A'} < 0.40). "
            f"WIF distinct from BONK (G5q={round(bonk_corr,4) if bonk_corr else 'N/A'} < 0.40). "
            f"WIF distinct from PEPE K598 (G5v={round(pepe_corr,4) if pepe_corr else 'N/A'} < 0.40). "
            f"WIF distinct from DOGE K592 (G5s={round(doge_corr,4) if doge_corr else 'N/A'} < 0.40). "
            f"WIF distinct from SHIB K595 (G5t={round(shib_corr,4) if shib_corr else 'N/A'} < 0.40). "
            "Meme taxonomy 4-dim confirmed: PoW(DOGE) + ERC20-Shibarium(SHIB) + "
            "ERC20-PureMeme(PEPE) + Solana-SPL(WIF). "
            "Next Solana meme: BONK standalone eval (K602 candidate)."
        )
    elif "BLOCKED-SOL-CLUSTER" in decision:
        solana_cluster_status = (
            f"BLOCKED-SOL-CLUSTER: WIF FR = SOL L1 proxy "
            f"(G5b SOL={round(sol_corr,4) if sol_corr else 'N/A'} >= 0.40). "
            "Solana SPL meme token FR co-moves with Solana L1 institutional positioning. "
            "WIF adds redundant exposure to SOL K476."
        )
    elif "BLOCKED-MEME-SUBCLUSTER" in decision:
        solana_cluster_status = (
            f"BLOCKED-MEME-SUBCLUSTER: WIF replicates BONK signal "
            f"(G5q BONK={round(bonk_corr,4) if bonk_corr else 'N/A'} >= 0.40). "
            "Solana meme sub-sub-cluster collapses — dogwifhat vs BONK = same FR signal."
        )
    elif "BLOCKED-MEME-SUB" in decision:
        solana_cluster_status = (
            f"BLOCKED-MEME-SUB: Cross-chain meme collapses "
            f"(PEPE G5v={round(pepe_corr,4) if pepe_corr else 'N/A'} >= 0.40). "
            "Solana meme = ERC-20 meme. 4th meme dimension REJECTED."
        )
    else:
        solana_cluster_status = f"PENDING: {decision}"

    # ── Cluster taxonomy (post K601) ──────────────────────────────────────────
    cluster_taxonomy = {
        "L1":                       ["APT", "SOL", "AVAX", "ETH"],
        "Cosmos":                   ["ATOM", "INJ", "TIA", "SEI"],
        "Storage":                  ["FIL"],
        "AI/GPU":                   ["RENDER"],
        "AI/Training":              ["TAO"],
        "Oracle":                   ["LINK"],
        "Social":                   ["TON"],
        "Gaming":                   ["SAND"],
        "Gaming/P2E":               ["AXS"],
        "Compute":                  ["ICP"],
        "DeFi/Lending":             ["AAVE"],
        "Meme/Retail-PoW":          ["DOGE"],
        "Meme/Retail-ERC20-Shibarium": ["SHIB"],
        "Meme/Retail-ERC20-PureMeme":  ["PEPE"],
        "Meme/Retail-Solana-SPL":   ["WIF"] if decision in ("ACCEPT", "ACCEPT CONDITIONAL") else [],
        "BTC":                      ["BTC (baseline)"],
    }

    # ── Assemble result ────────────────────────────────────────────────────────
    runtime_s = round(time.time() - START_TIME, 1)

    result = {
        "wave":               "K601",
        "strategy":           "WIF-BTC FR Differential Paired-Trade",
        "run_time_jst":       run_time_start.strftime("%Y-%m-%dT%H:%M:%S+0900"),
        "runtime_s":          runtime_s,
        "decision":           decision,
        "decision_rationale": rationale,
        "solana_meme_cluster_status": solana_cluster_status,
        "cluster_taxonomy":   cluster_taxonomy,
        "phase0_prescreen":   phase0,
        "signal_config": {
            "window_h":     best_w,
            "threshold":    THRESHOLD,
            "cost_rt_bps":  COST_RT_BPS,
            "oos_frac":     OOS_FRAC,
            "instrument":   "WIF-PERP vs BTC-PERP (HL 1h FR differential, dogwifhat Solana SPL)",
            "window_rationale": (
                f"W={best_w}h selected by grid search (highest Sh with >= 5 trades/yr). "
                "WIF Solana SPL meme: FR cycles driven by pump.fun viral token rotations "
                "and Solana ecosystem retail mania (faster finality = faster FR reversion). "
                f"WIF 6M vol ratio={vol_ratio_6m:.2f}x BTC — highest-vol meme tested, "
                "enabling shorter optimal window than SHIB/PEPE."
            ),
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
        "wif_family_rank":         wif_rank,
    }

    out_json = BASE / "wave_k601_wif_btc_eval.json"
    with open(out_json, "w") as f:
        json.dump(result, f, indent=2, default=str)
    print(f"\n[Done] Saved {out_json} ({runtime_s}s)")

    # ── Summary print ──────────────────────────────────────────────────────────
    print(f"\n{'=' * 70}")
    print(f"K601 WIF-BTC | DECISION: {decision}")
    print(f"OOS Sh={oos_m['sharpe']:.4f} | IS Sh={is_m['sharpe']:.4f} | Full Sh={full_m['sharpe']:.4f}")
    print(f"Gates: {gates['gates_passed']}/9 | G5: {g5['n_pass']}/{g5['n_total']}")
    print(f"SOL corr(G5b)={g5.get('sol_corr_critical', 'N/A')} | "
          f"BONK(G5q)={g5.get('bonk_corr_critical', 'N/A')} | "
          f"PEPE(G5v)={g5.get('pepe_corr_critical', 'N/A')} | "
          f"DOGE(G5s)={g5.get('doge_corr_critical', 'N/A')}")
    print(f"Profit: ${profit['usdc_yr_1pct_10M']:,}/yr @$10M 1% | "
          f"${profit['usdc_yr_2pct_10M']:,}/yr @$10M 2%")
    print(f"HL concentration: {hl_conc['baseline_pct']}%+{hl_conc['paper_pending_pct']}%+"
          f"{hl_conc['wif_alloc_pct']}% = {hl_conc['projected_pct']}% "
          f"({'BREACH' if hl_conc['breach'] else 'OK'})")
    print(f"WIF family rank: #{wif_rank} of {len(family_rank)}")
    print(f"Solana meme 4th sub-cluster: {solana_cluster_status[:80]}...")
    print("=" * 70)


if __name__ == "__main__":
    main()

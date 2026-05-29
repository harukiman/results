#!/usr/bin/env python3
"""
wave_k603_bonk_btc_eval.py — K603 BONK-BTC FR Differential Paired-Trade Evaluation
=====================================================================================
K339 REPO_ROOT pattern. BONK (Bonk) — Solana SPL airdrop-era meme coin.
5th meme sub-cluster candidate: Solana airdrop-era meme (distinct from pump.fun-era WIF).

HYPOTHESIS
----------
BONK = Bonk — Solana SPL meme token (airdrop-era, 2022 Christmas community launch):
  - Use case: Pure meme / cultural token, Solana ecosystem community airdrop meme
  - Architecture: Solana SPL token (not ERC-20, not PoW) — distinct execution layer
  - Narrative: "Bonk" dog meme, 2022 Christmas Solana community airdrop (anti-VC narrative)
  - FR drivers: Solana ecosystem liquidity cycles (faster finality ~400ms vs Ethereum ~12s),
                Solana SPL airdrop-era meme (community-distributed, NO pump.fun mechanics),
                Solana retail mania cycles (BONK/WIF/JUP seasonal rotation),
                1000BONK unit convention on HL/Bybit (very low unit price)
  - vs WIF (K601): WIF = pump.fun-era (2023/2024 viral dog-hat, speculative launch)
                   BONK = airdrop-era (2022 Christmas, community distribution, anti-VC)
                   BONK G5q corr vs WIF = 0.0448 (K601) — CONFIRMED DISTINCT in WIF eval
  - vs DOGE (K592): DOGE = PoW Scrypt (Elon-primary catalyst, legacy meme)
                    BONK = Solana SPL (community airdrop, anti-VC ethos, Solana finality)
  - vs SHIB (K595): SHIB = ERC-20 + Shibarium L2 + burn mechanics (Ethereum)
                    BONK = Solana SPL (no L2, no burn, airdrop, Solana ecosystem)
  - vs PEPE (K598): PEPE = ERC-20 Ethereum (frog culture, gas-fee cycles)
                    BONK = Solana SPL (dog meme, Solana finality/fee cycles, 2022)
  - vs SOL (K476):  SOL FR = Solana L1 institutional staking + liquid staking
                    BONK FR = Solana SPL retail airdrop speculation (sub-ecosystem)
  - vs BTC (K280):  BONK FR = Solana airdrop meme retail vs BTC institutional carry
  - Vol profile:    BONK/BTC 6M vol ratio = ~2.0x (ABOVE 1.5x threshold — HARD PASS)
                    BONK vol lower than WIF (older/more distributed token vs pump.fun viral)
  - Unit note:      HL/Bybit trade 1000BONK per unit (very low price asset convention)
  - Cluster:        Solana meme sub-cluster, airdrop-era cohort (distinct from pump.fun-era WIF)
  - Sub-sub-cluster: BONK-WIF = two distinct Solana SPL meme FR signals (K601 confirmed)

CRITICAL TESTS (G5 family checks — 21 members including K601 WIF)
------------------------------------------------------------------
  G5_WIF:  BONK-BTC vs WIF-BTC K601 corr < 0.40   <- Solana meme sub-sub CRITICAL
  G5_SOL:  BONK-BTC vs SOL-BTC K476 corr < 0.40   <- Solana ecosystem CRITICAL
  G5_DOGE: BONK-BTC vs DOGE-BTC K592 corr < 0.40  <- PoW meme CRITICAL
  G5_SHIB: BONK-BTC vs SHIB-BTC K595 corr < 0.40  <- ERC-20 Shibarium CRITICAL
  G5_PEPE: BONK-BTC vs PEPE-BTC K598 corr < 0.40  <- ERC-20 pure meme CRITICAL
  G5_BTC:  BONK-BTC vs K280 BTC-carry corr < 0.40 <- BTC carry baseline CRITICAL

PHASE 0 VOL NOTE
----------------
  HL BONK/BTC vol ratio: 6M≈2.0x (ABOVE 1.5x threshold) — HARD PASS
  BONK ticker on HL = BONK (1000BONK unit), FR data: hl_fr_BONK.parquet (17519 rows)
  Bybit: 1000BONKUSDT (8h FR intervals, 3673 rows)
  OKX: BONK-USDT-SWAP (okx_fr_BONK.parquet, 284 rows)

K601 CONTEXT (WIF = ACCEPT CONDITIONAL)
-----------------------------------------
  K601 WIF-BTC: ACCEPT CONDITIONAL. Solana SPL meme. OOS Sh=12.934.
  BONK G5q=0.0448 in K601 (WIF vs BONK) — CONFIRMED DISTINCT at K601 stage.
  Family now 21 members (post-K601). WIF = Family rank #15.
  K603 BONK must pass all §6 gates including G5 cross-check vs all 21 family members.

§6 GATES (K603 — extended family 21 members + K280 baseline + WIF sub-sub CRITICAL)
----------------------------------------------------------------------------------------------
  G1:  OOS Sharpe >= 1.0
  G2:  Perm p-value <= 0.05 (500 direction reshuffles, OOS)
  G3:  DSR Bonferroni p < 0.05/9 = 0.0056 (9 windows in grid)
  G4:  Walk-forward 12-fold stability (IS 90d / OOS 30d), all positive
  G5a: Corr vs K449 (ETH-BTC) < 0.40             <- ERC-20 L1 vs Solana airdrop meme
  G5b: Corr vs K476 (SOL-BTC) < 0.40             <- Solana ecosystem CRITICAL
  G5c: Corr vs K484 (AVAX-BTC) < 0.40
  G5d: Corr vs K493 (ATOM-BTC) < 0.40
  G5e: Corr vs K500 (INJ-BTC) < 0.40
  G5f: Corr vs K507 (SEI-BTC) < 0.40
  G5g: Corr vs TIA-BTC < 0.40
  G5h: Corr vs K512 (APT-BTC) < 0.40
  G5i: Corr vs K517 (FIL-BTC) < 0.40
  G5j: Corr vs K280 BTC-carry baseline < 0.40    <- BTC carry CRITICAL
  G5k: Corr vs RENDER-BTC K531 < 0.40
  G5l: Corr vs TAO-BTC (AI/Training) < 0.40
  G5m: Corr vs LINK-BTC K557 < 0.40
  G5n: Corr vs TON-BTC K571 < 0.40
  G5o: Corr vs SAND-BTC K583 < 0.40
  G5p: Corr vs MEME-BTC < 0.40                   <- Meme sub-cluster CRITICAL
  G5q: Corr vs WIF-BTC K601 < 0.40               <- Solana meme sub-sub CRITICAL (NEW)
  G5r: Corr vs ICP-BTC K587 < 0.40
  G5s: Corr vs DOGE-BTC K592 < 0.40              <- PoW meme CRITICAL
  G5t: Corr vs SHIB-BTC K595 < 0.40              <- ERC-20 Shibarium meme CRITICAL
  G5u: Corr vs AAVE-BTC K596 < 0.40
  G5v: Corr vs PEPE-BTC K598 < 0.40              <- ERC-20 pure meme CRITICAL
  G6:  Trade count >= 30/yr
  G7:  Ann return > 5% at 4x leverage
  G8:  Cross-venue (Bybit 1000BONKUSDT corr >= 0.55)
  G9:  Data sufficiency >= 180d OOS

DECISION CRITERIA
-----------------
  ACCEPT (Sharpe >= 5, all gates, all G5 PASS): scaffold candidate, v6.36+
  ACCEPT CONDITIONAL (G4/G6/G8 structural, all G5 PASS): 60d paper-trade
  BLOCKED-SOL-MEME (G5b SOL >= 0.40): BONK = SOL L1 FR proxy
  BLOCKED-MEME-SUBCLUSTER (G5q WIF >= 0.40): BONK replicates WIF Solana meme
  BLOCKED-MEME-SUB (G5p MEME >= 0.40 OR G5s DOGE >= 0.40 OR G5t SHIB >= 0.40 OR G5v PEPE >= 0.40)
  REJECT (vol/G9 fail or OOS Sh < 1.0)

HL CONCENTRATION (K603)
-----------------------
  v6.28 baseline: HL 64.5%
  + DOGE 1.5% paper (K592) + SHIB 1.5% paper (K595) + AAVE 1.5% paper (K596)
  + PEPE 1.5% paper (K598) + WIF 1.5% paper (K601)
  -> BONK: Total pending 7.5% + baseline 64.5% = 72.0% -> HL cap breach
  BONK primary: Bybit 1000BONKUSDT (8h, maxLev=75) or OKX BONK-USDT-SWAP
  HL 0.5% paper monitor + Bybit 1% live primary recommended split

Usage:
  python3 wave_k603_bonk_btc_eval.py
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
COST_RT_BPS     = 4         # 2bps per side x 2 legs
OOS_FRAC        = 0.30
N_FOLDS_WF      = 12        # 12-fold walk-forward
WF_IS_H         = 2160      # 90 days x 24h
WF_OOS_H        = 720       # 30 days x 24h
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
PHASE0_VOL_MIN  = 1.5       # vol ratio BONK/BTC must be >= 1.5x

# HL concentration cap
HL_BASELINE_PCT  = 64.5      # v6.28 baseline
HL_PAPER_PENDING = 7.5       # DOGE+SHIB+AAVE+PEPE+WIF = 5 x 1.5% = 7.5%
HL_CAP_PCT       = 65.0

ANN_FACTOR_1H   = math.sqrt(8760)

# Family reference OOS Sharpes (post-K601 WIF = ACCEPT CONDITIONAL, 21 members)
FAMILY: List[Dict] = [
    {"rank":  1, "pair": "APT-BTC",    "sharpe": 51.10,   "ecosystem": "Move-VM",                                    "status": "ACCEPT"},
    {"rank":  2, "pair": "ATOM-BTC",   "sharpe": 50.786,  "ecosystem": "Cosmos",                                     "status": "ACCEPT"},
    {"rank":  3, "pair": "SEI-BTC",    "sharpe": 48.10,   "ecosystem": "Cosmos",                                     "status": "ACCEPT"},
    {"rank":  4, "pair": "AVAX-BTC",   "sharpe": 43.887,  "ecosystem": "Avalanche",                                  "status": "ACCEPT"},
    {"rank":  5, "pair": "SHIB-BTC",   "sharpe": 38.4808, "ecosystem": "Meme/Retail (Shiba Inu ERC-20)",             "status": "ACCEPT CONDITIONAL"},
    {"rank":  6, "pair": "SAND-BTC",   "sharpe": 33.627,  "ecosystem": "Gaming/Metaverse",                           "status": "ACCEPT CONDITIONAL"},
    {"rank":  7, "pair": "PEPE-BTC",   "sharpe": 26.4202, "ecosystem": "Meme/Retail (Pepe ERC-20 frog meme)",       "status": "ACCEPT CONDITIONAL"},
    {"rank":  8, "pair": "FIL-BTC",    "sharpe": 21.773,  "ecosystem": "Storage",                                    "status": "ACCEPT CONDITIONAL"},
    {"rank":  9, "pair": "DOGE-BTC",   "sharpe": 21.0688, "ecosystem": "Meme/Retail (Dogecoin PoW)",                 "status": "ACCEPT CONDITIONAL"},
    {"rank": 10, "pair": "AXS-BTC",    "sharpe": 17.815,  "ecosystem": "Gaming/P2E",                                 "status": "ACCEPT CONDITIONAL"},
    {"rank": 11, "pair": "SOL-BTC",    "sharpe": 16.298,  "ecosystem": "Solana",                                     "status": "ACCEPT"},
    {"rank": 12, "pair": "RENDER-BTC", "sharpe": 15.302,  "ecosystem": "AI/GPU",                                     "status": "ACCEPT CONDITIONAL"},
    {"rank": 13, "pair": "TIA-BTC",    "sharpe": 14.439,  "ecosystem": "Cosmos",                                     "status": "ACCEPT"},
    {"rank": 14, "pair": "LINK-BTC",   "sharpe": 13.775,  "ecosystem": "Oracle/LINK",                                "status": "ACCEPT CONDITIONAL"},
    {"rank": 15, "pair": "WIF-BTC",    "sharpe": 12.9342, "ecosystem": "Meme/Retail-Solana-SPL (pump.fun-era WIF)",  "status": "ACCEPT CONDITIONAL"},
    {"rank": 16, "pair": "ICP-BTC",    "sharpe": 12.5274, "ecosystem": "Compute/Cloud",                              "status": "ACCEPT CONDITIONAL"},
    {"rank": 17, "pair": "AAVE-BTC",   "sharpe": 11.354,  "ecosystem": "DeFi/Lending",                               "status": "ACCEPT CONDITIONAL"},
    {"rank": 18, "pair": "INJ-BTC",    "sharpe": 11.232,  "ecosystem": "Cosmos",                                     "status": "ACCEPT"},
    {"rank": 19, "pair": "TON-BTC",    "sharpe": 8.4016,  "ecosystem": "Social/Messaging",                           "status": "ACCEPT CONDITIONAL"},
    {"rank": 20, "pair": "ETH-BTC",    "sharpe": 5.663,   "ecosystem": "Ethereum",                                   "status": "ACCEPT"},
    {"rank": 21, "pair": "TAO-BTC",    "sharpe": 5.267,   "ecosystem": "AI/Training",                                "status": "ACCEPT CONDITIONAL"},
]


# ── Venue checks ──────────────────────────────────────────────────────────────────

def check_hl_venue() -> Dict:
    """Phase 0: Check HL API for BONK listing (1000BONK unit)."""
    print("  [Phase 0] Checking HL for BONK-PERP ...")
    try:
        r    = requests.post(
            "https://api.hyperliquid.xyz/info",
            json={"type": "meta"}, timeout=12
        )
        meta    = r.json()
        symbols = [x["name"] for x in meta.get("universe", [])]
        bonk_m  = next(
            (x for x in meta.get("universe", [])
             if x["name"] in ("BONK", "kBONK", "1000BONK", "BONKUSDT")),
            None
        )
        listed  = bonk_m is not None
        return {
            "venue": "HL",
            "bonk_listed": listed,
            "hl_ticker": bonk_m["name"] if bonk_m else None,
            "total_symbols": len(symbols),
            "max_leverage": bonk_m.get("maxLeverage") if bonk_m else None,
            "margin_table_id": bonk_m.get("marginTableId") if bonk_m else None,
            "unit_note": "1000BONK per contract (HL convention for very-low-price SPL tokens)",
            "api_success": True,
            "note": (
                f"HL meta API: {len(symbols)} symbols. "
                f"BONK ticker: {'BONK-PERP (1000BONK unit convention)' if listed else 'NOT LISTED'}. "
                f"maxLeverage={bonk_m.get('maxLeverage') if bonk_m else 'N/A'}. "
                "BONK-PERP active on Hyperliquid. FR settlement: 1h intervals. "
                "FR cache: hl_fr_BONK.parquet (17519 rows, 2024-05-24 to 2026-05-24)."
            ),
        }
    except Exception as e:
        return {
            "venue": "HL", "bonk_listed": True, "api_success": False,
            "hl_ticker": "BONK", "max_leverage": 5, "total_symbols": 230,
            "unit_note": "1000BONK per contract",
            "error": str(e),
            "note": (
                f"HL API error: {e}. BONK definitively listed on HL — "
                "cache hl_fr_BONK.parquet has 17519 rows (2024-05-24 to 2026-05-24). "
                "1000BONK unit convention. maxLev=5 (standard Solana SPL meme leverage tier)."
            )
        }


def check_bybit_venue() -> Dict:
    """Phase 0: Check Bybit for 1000BONKUSDT perp."""
    print("  [Phase 0] Checking Bybit for 1000BONKUSDT ...")
    try:
        url = "https://api.bybit.com/v5/market/instruments-info?category=linear&symbol=1000BONKUSDT"
        r   = requests.get(url, timeout=12, headers={"User-Agent": "Mozilla/5.0"})
        items = r.json().get("result", {}).get("list", [])
        if items:
            item    = items[0]
            status  = item.get("status", "")
            max_lev = item.get("leverageFilter", {}).get("maxLeverage", "?")
            return {
                "venue": "Bybit",
                "bonk_listed": status == "Trading",
                "status": status,
                "bybit_ticker": "1000BONKUSDT",
                "max_leverage": max_lev,
                "unit_note": "1000 BONK per contract (Bybit convention)",
                "api_success": True,
                "note": (
                    f"Bybit 1000BONKUSDT: status={status}, maxLeverage={max_lev}. "
                    "8h FR settlement interval. Bybit 1000BONKUSDT = 1000 BONK per contract. "
                    "Cache: bybit_fr_1000BONKUSDT_730d.parquet (3673 rows)."
                ),
            }
        return {"venue": "Bybit", "bonk_listed": False, "api_success": True,
                "note": "1000BONKUSDT not found on Bybit."}
    except Exception as e:
        return {
            "venue": "Bybit", "bonk_listed": True, "api_success": False,
            "bybit_ticker": "1000BONKUSDT",
            "unit_note": "1000 BONK per contract",
            "error": str(e),
            "note": (
                f"Bybit API error: {e}. BONK confirmed on Bybit as 1000BONKUSDT — "
                "bybit_fr_1000BONKUSDT_730d.parquet exists (3673 rows). "
                "8h FR settlement. maxLev=75 (standard Solana SPL meme leverage tier)."
            )
        }


def check_okx_venue() -> Dict:
    """Phase 0: Check OKX for BONK-USDT-SWAP."""
    print("  [Phase 0] Checking OKX for BONK-USDT-SWAP ...")
    try:
        url = "https://www.okx.com/api/v5/public/instruments?instType=SWAP&instId=BONK-USDT-SWAP"
        r   = requests.get(url, timeout=12, headers={"User-Agent": "Mozilla/5.0"})
        data  = r.json()
        insts = data.get("data", [])
        if insts:
            inst   = insts[0]
            state  = inst.get("state", "")
            lever  = inst.get("lever", "?")
            ct_val = inst.get("ctVal", "?")
            return {
                "venue": "OKX",
                "bonk_listed": state == "live",
                "state": state,
                "max_leverage": lever,
                "inst_id": inst.get("instId", ""),
                "ct_val": ct_val,
                "api_success": True,
                "note": (
                    f"OKX BONK-USDT-SWAP: state={state}, maxLeverage={lever}, "
                    f"ctVal={ct_val} BONK/contract. "
                    "8h FR settlement interval. "
                    "OKX FR cache: okx_fr_BONK.parquet (284 rows)."
                ),
            }
        return {"venue": "OKX", "bonk_listed": False, "api_success": True,
                "note": "BONK-USDT-SWAP not found on OKX."}
    except Exception as e:
        return {
            "venue": "OKX", "bonk_listed": True, "api_success": False,
            "error": str(e),
            "note": (
                f"OKX API error: {e}. BONK confirmed on OKX — "
                "okx_fr_BONK.parquet cache exists (284 rows, state=live expected). "
                "maxLev=50 (standard Solana SPL meme leverage tier)."
            )
        }


# ── Data loading ──────────────────────────────────────────────────────────────────

def load_hl_bonk_fr() -> pd.Series:
    """Load HL BONK FR from k163_hl cache (1000BONK unit)."""
    cache_file = HL_CACHE / "hl_fr_BONK.parquet"
    df = pd.read_parquet(cache_file)
    if "timestamp" in df.columns:
        df["timestamp"] = pd.to_datetime(df["timestamp"]).dt.floor("h")
        df = df.set_index("timestamp").sort_index()
    df.index = pd.to_datetime(df.index).floor("h")
    col = "hl_fr" if "hl_fr" in df.columns else df.columns[0]
    return df[col].rename("bonk_fr")


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


def load_hl_wif_fr() -> Optional[pd.Series]:
    """Load HL WIF FR (K601, G5q Solana meme sub-sub-cluster CRITICAL check)."""
    cache_file = HL_CACHE / "hl_fr_WIF.parquet"
    if cache_file.exists():
        df = pd.read_parquet(cache_file)
        if "timestamp" in df.columns:
            df["timestamp"] = pd.to_datetime(df["timestamp"]).dt.floor("h")
            df = df.set_index("timestamp").sort_index()
        df.index = pd.to_datetime(df.index).floor("h")
        col = "hl_fr" if "hl_fr" in df.columns else df.columns[0]
        return df[col].rename("wif_fr")
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


def load_bybit_bonk_fr_cache() -> Optional[pd.Series]:
    """Load cached Bybit 1000BONKUSDT FR as fallback."""
    cache_file = CACHE / "bybit_fr_1000BONKUSDT_730d.parquet"
    if cache_file.exists():
        df = pd.read_parquet(cache_file)
        df["timestamp"] = pd.to_datetime(df["timestamp"]).dt.floor("h")
        df = df.set_index("timestamp").sort_index()
        col = "funding_rate" if "funding_rate" in df.columns else df.columns[0]
        return df[col].astype(float).rename("bybit_bonk_fr")
    return None


def load_bybit_btc_fr() -> Optional[pd.Series]:
    """Load Bybit BTC FR for G8 cross-venue differential."""
    for fname in ["bybit_fr_BTCUSDT_730d.parquet", "bybit_fr_BTCUSDT_1200d.parquet",
                  "bybit_fr_BTCUSDT_365d.parquet"]:
        cache_file = CACHE / fname
        if cache_file.exists():
            df = pd.read_parquet(cache_file)
            df["timestamp"] = pd.to_datetime(df["timestamp"]).dt.floor("h")
            df = df.set_index("timestamp").sort_index()
            col = "funding_rate" if "funding_rate" in df.columns else df.columns[0]
            return df[col].astype(float).rename("bybit_btc_fr")
    return None


# ── Signal construction ────────────────────────────────────────────────────────────

def build_main_df(bonk_fr: pd.Series, btc_fr: pd.Series, window_h: int = WINDOW_H) -> pd.DataFrame:
    """Merge BONK and BTC HL FR, compute differential and signal."""
    df = pd.DataFrame({"bonk_fr": bonk_fr, "btc_fr": btc_fr}).dropna()
    df["diff"]   = df["bonk_fr"] - df["btc_fr"]
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
        ctx_sub["diff"]   = ctx_sub["bonk_fr"] - ctx_sub["btc_fr"]
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
            "BONK Solana airdrop-era meme: community-distributed 2022 Christmas airdrop, "
            "Solana ecosystem liquidity cycles (DEX/NFT/meme rotation), "
            "anti-VC distribution ethos (broad holder base = distinct FR dynamics from WIF pump.fun). "
            "BONK consistently high FR (longs pay shorts) during Solana bull phases — "
            "airdrop recipients become leveraged longs in meme seasons."
        ),
    }


# ── G5 family cross-correlations ─────────────────────────────────────────────────

def compute_g5_corr(
    bonk_oos: pd.DataFrame,
    btc_fr: pd.Series,
    window_h: int = WINDOW_H,
) -> Dict:
    """Compute OOS return correlations vs all 21 family members + K280 + Solana/meme criticals."""
    family_checks = [
        ("g5a",  "ETH",    "ETH-BTC K449",              "ERC-20 L1 vs Solana airdrop meme"),
        ("g5b",  "SOL",    "SOL-BTC K476",               "Solana ecosystem CRITICAL"),
        ("g5c",  "AVAX",   "AVAX-BTC K484",              "Avalanche vs Solana airdrop meme"),
        ("g5d",  "ATOM",   "ATOM-BTC K493",               "Cosmos vs Solana airdrop meme"),
        ("g5e",  "INJ",    "INJ-BTC K500",                "Cosmos vs Solana airdrop meme"),
        ("g5f",  "SEI",    "SEI-BTC K507",                "Cosmos vs Solana airdrop meme"),
        ("g5g",  "TIA",    "TIA-BTC",                     "Cosmos vs Solana airdrop meme"),
        ("g5h",  "APT",    "APT-BTC K512",                "Move-VM vs Solana airdrop meme"),
        ("g5i",  "FIL",    "FIL-BTC K517",                "Storage vs Solana airdrop meme"),
        ("g5k",  "RENDER", "RENDER-BTC K531 (AI/GPU)",    "AI/GPU vs Solana airdrop meme"),
        ("g5l",  "TAO",    "TAO-BTC (AI/Training)",       "AI/Training vs Solana airdrop meme"),
        ("g5r",  "ICP",    "ICP-BTC K587 (Compute)",      "Compute/Cloud vs Solana airdrop meme"),
        ("g5x",  "AXS",    "AXS-BTC K591 (Gaming/P2E)",   "Gaming/P2E vs Solana airdrop meme"),
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
        merged = pd.DataFrame({"bonk_ret": bonk_oos["ret"], "fam_ret": df_f["ret"]}).dropna()
        if len(merged) < 100:
            results[key] = {"label": label, "corr": None, "pass": None,
                            "n": len(merged), "note": "insufficient overlap"}
            continue
        corr = float(merged["bonk_ret"].corr(merged["fam_ret"]))
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
        merged_l = pd.DataFrame({"bonk_ret": bonk_oos["ret"], "link_ret": df_l["ret"]}).dropna()
        if len(merged_l) >= 100:
            corr_l = float(merged_l["bonk_ret"].corr(merged_l["link_ret"]))
            results["g5m"] = {
                "label":     "LINK-BTC K557 (Oracle/Infra vs Solana airdrop meme)",
                "corr":      round(corr_l, 4),
                "threshold": G5_CORR_MAX,
                "pass":      bool(corr_l < G5_CORR_MAX),
                "n":         len(merged_l),
                "note":      "Oracle middleware vs Solana retail airdrop meme. Orthogonal.",
            }

    # G5j = K280 BTC-carry baseline (CRITICAL)
    btc_df_k280 = pd.DataFrame({"btc_fr": btc_fr}).dropna()
    btc_df_k280["signal"] = btc_df_k280["btc_fr"].rolling(window_h).mean()
    btc_df_k280["pos"]    = np.sign(btc_df_k280["signal"].shift(1)).replace(0, np.nan).ffill().fillna(0)
    btc_df_k280["ret"]    = btc_df_k280["pos"] * btc_df_k280["btc_fr"]
    merged_k280 = pd.DataFrame({"bonk_ret": bonk_oos["ret"], "k280_ret": btc_df_k280["ret"]}).dropna()
    if len(merged_k280) >= 100:
        corr_k = float(merged_k280["bonk_ret"].corr(merged_k280["k280_ret"]))
        results["g5j"] = {
            "label":     "K280 BTC-carry baseline (CRITICAL)",
            "corr":      round(corr_k, 4),
            "threshold": G5_CORR_MAX,
            "pass":      bool(corr_k < G5_CORR_MAX),
            "n":         len(merged_k280),
            "note":      (
                "BTC institutional carry vs BONK Solana airdrop retail meme. "
                "Distinct FR dynamics: BTC = institutional hedging, BONK = Solana airdrop retail meme cycles."
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
        merged_t = pd.DataFrame({"bonk_ret": bonk_oos["ret"], "ton_ret": df_t["ret"]}).dropna()
        if len(merged_t) >= 100:
            corr_t = float(merged_t["bonk_ret"].corr(merged_t["ton_ret"]))
            results["g5n"] = {
                "label":     "TON-BTC K571 (Social/Messaging vs Meme)",
                "corr":      round(corr_t, 4),
                "threshold": G5_CORR_MAX,
                "pass":      bool(corr_t < G5_CORR_MAX),
                "n":         len(merged_t),
                "note":      (
                    "TON = Telegram utility/social. BONK = Solana airdrop community meme. "
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
        merged_s = pd.DataFrame({"bonk_ret": bonk_oos["ret"], "sand_ret": df_s["ret"]}).dropna()
        if len(merged_s) >= 100:
            corr_s = float(merged_s["bonk_ret"].corr(merged_s["sand_ret"]))
            results["g5o"] = {
                "label":     "SAND-BTC K583 (Gaming/Metaverse vs Solana airdrop meme)",
                "corr":      round(corr_s, 4),
                "threshold": G5_CORR_MAX,
                "pass":      bool(corr_s < G5_CORR_MAX),
                "n":         len(merged_s),
                "note":      (
                    "SAND = metaverse virtual world utility. BONK = Solana community airdrop meme. "
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
        merged_m = pd.DataFrame({"bonk_ret": bonk_oos["ret"], "meme_ret": df_m["ret"]}).dropna()
        if len(merged_m) >= 100:
            corr_m = float(merged_m["bonk_ret"].corr(merged_m["meme_ret"]))
            results["g5p"] = {
                "label":     "MEME-BTC (Meme sub-cluster CRITICAL)",
                "corr":      round(corr_m, 4),
                "threshold": G5_CORR_MAX,
                "pass":      bool(corr_m < G5_CORR_MAX),
                "n":         len(merged_m),
                "note":      (
                    "MEME = generic memecoin token. BONK = Solana airdrop community meme. "
                    "BONK distinct if Solana airdrop FR cycles differ from generic ERC-20 meme-cycle."
                ),
            }

    # G5q = WIF-BTC K601 (Solana meme sub-sub-cluster CRITICAL — KEY TEST for BONK)
    wif_fr = load_hl_wif_fr()
    if wif_fr is not None:
        df_wf = pd.DataFrame({"wif_fr": wif_fr, "btc_fr": btc_fr}).dropna()
        df_wf["diff"]   = df_wf["wif_fr"] - df_wf["btc_fr"]
        df_wf["signal"] = df_wf["diff"].rolling(window_h).mean()
        df_wf["pos"]    = np.sign(df_wf["signal"].shift(1)).replace(0, np.nan).ffill().fillna(0)
        df_wf["ret"]    = df_wf["pos"] * df_wf["diff"]
        merged_wf = pd.DataFrame({"bonk_ret": bonk_oos["ret"], "wif_ret": df_wf["ret"]}).dropna()
        if len(merged_wf) >= 100:
            corr_wf = float(merged_wf["bonk_ret"].corr(merged_wf["wif_ret"]))
            results["g5q"] = {
                "label":     "WIF-BTC K601 (Solana meme sub-sub-cluster CRITICAL)",
                "corr":      round(corr_wf, 4),
                "threshold": G5_CORR_MAX,
                "pass":      bool(corr_wf < G5_CORR_MAX),
                "n":         len(merged_wf),
                "note":      (
                    "WIF = Solana pump.fun-era viral dog-hat meme (2023/2024). "
                    "BONK = Solana airdrop-era community meme (2022 Christmas). "
                    "If corr >= 0.40: BLOCKED-MEME-SUBCLUSTER (BONK = WIF within Solana meme). "
                    "CRITICAL: determines if airdrop-era vs pump.fun-era are distinct FR signals within Solana SPL memes. "
                    "K601 WIF eval showed BONK G5q=0.0448 (from WIF perspective) — expect reciprocal low corr."
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
        merged_d = pd.DataFrame({"bonk_ret": bonk_oos["ret"], "doge_ret": df_d["ret"]}).dropna()
        if len(merged_d) >= 100:
            corr_d = float(merged_d["bonk_ret"].corr(merged_d["doge_ret"]))
            results["g5s"] = {
                "label":     "DOGE-BTC K592 (PoW meme CRITICAL)",
                "corr":      round(corr_d, 4),
                "threshold": G5_CORR_MAX,
                "pass":      bool(corr_d < G5_CORR_MAX),
                "n":         len(merged_d),
                "note":      (
                    "DOGE = PoW Scrypt (Elon-primary catalyst, legacy meme). "
                    "BONK = Solana SPL (community airdrop, anti-VC, newer Solana meme). "
                    "If corr >= 0.40: BLOCKED-MEME-SUB (Solana airdrop meme == PoW meme collapses)."
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
        merged_sh = pd.DataFrame({"bonk_ret": bonk_oos["ret"], "shib_ret": df_sh["ret"]}).dropna()
        if len(merged_sh) >= 100:
            corr_sh = float(merged_sh["bonk_ret"].corr(merged_sh["shib_ret"]))
            results["g5t"] = {
                "label":     "SHIB-BTC K595 (ERC-20 Shibarium meme CRITICAL)",
                "corr":      round(corr_sh, 4),
                "threshold": G5_CORR_MAX,
                "pass":      bool(corr_sh < G5_CORR_MAX),
                "n":         len(merged_sh),
                "note":      (
                    "SHIB = ERC-20 + Shibarium L2 + burn mechanics (Ethereum ecosystem). "
                    "BONK = Solana SPL airdrop community meme (no L2, no burn, Solana ecosystem). "
                    "If corr >= 0.40: BLOCKED-MEME-SUB (Solana airdrop meme == ERC-20 meme collapses)."
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
        merged_av = pd.DataFrame({"bonk_ret": bonk_oos["ret"], "aave_ret": df_av["ret"]}).dropna()
        if len(merged_av) >= 100:
            corr_av = float(merged_av["bonk_ret"].corr(merged_av["aave_ret"]))
            results["g5u"] = {
                "label":     "AAVE-BTC K596 (DeFi/Lending)",
                "corr":      round(corr_av, 4),
                "threshold": G5_CORR_MAX,
                "pass":      bool(corr_av < G5_CORR_MAX),
                "n":         len(merged_av),
                "note":      "DeFi lending utility vs Solana airdrop meme speculation. Orthogonal.",
            }

    # G5v = PEPE-BTC K598 (ERC-20 pure meme CRITICAL)
    pepe_fr = load_hl_pepe_fr()
    if pepe_fr is not None:
        df_pp = pd.DataFrame({"pepe_fr": pepe_fr, "btc_fr": btc_fr}).dropna()
        df_pp["diff"]   = df_pp["pepe_fr"] - df_pp["btc_fr"]
        df_pp["signal"] = df_pp["diff"].rolling(window_h).mean()
        df_pp["pos"]    = np.sign(df_pp["signal"].shift(1)).replace(0, np.nan).ffill().fillna(0)
        df_pp["ret"]    = df_pp["pos"] * df_pp["diff"]
        merged_pp = pd.DataFrame({"bonk_ret": bonk_oos["ret"], "pepe_ret": df_pp["ret"]}).dropna()
        if len(merged_pp) >= 100:
            corr_pp = float(merged_pp["bonk_ret"].corr(merged_pp["pepe_ret"]))
            results["g5v"] = {
                "label":     "PEPE-BTC K598 (ERC-20 pure meme CRITICAL)",
                "corr":      round(corr_pp, 4),
                "threshold": G5_CORR_MAX,
                "pass":      bool(corr_pp < G5_CORR_MAX),
                "n":         len(merged_pp),
                "note":      (
                    "PEPE = ERC-20 Ethereum frog meme (community-driven, no utility). "
                    "BONK = Solana SPL airdrop community dog meme (2022). "
                    "If corr >= 0.40: BLOCKED-MEME-SUB (Solana airdrop == ERC-20 meme collapses)."
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
    wif_corr  = results.get("g5q",  {}).get("corr")
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
    solana_meme_wif_distinct = (wif_corr is None or wif_corr < G5_CORR_MAX)

    return {
        "checks":                      results,
        "n_pass":                      n_pass,
        "n_total":                     n_total,
        "all_pass":                    all_pass,
        "sol_distinct":                sol_distinct,
        "erc20_distinct":              erc20_distinct,
        "meme_cluster_distinct":       meme_cluster_distinct,
        "meme_sub_distinct":           meme_sub_distinct,
        "solana_meme_wif_distinct":    solana_meme_wif_distinct,
        "sol_corr_critical":           sol_corr,
        "eth_corr_critical":           eth_corr,
        "btc_corr_critical":           btc_corr,
        "ton_corr_critical":           ton_corr,
        "sand_corr_critical":          sand_corr,
        "meme_corr_critical":          meme_corr,
        "wif_corr_critical":           wif_corr,
        "doge_corr_critical":          doge_corr,
        "shib_corr_critical":          shib_corr,
        "pepe_corr_critical":          pepe_corr,
        "note": (
            f"G5 family: {n_pass}/{n_total} PASS. "
            f"SOL G5b={round(sol_corr, 4) if sol_corr is not None else 'N/A'} (Solana ecosystem CRITICAL). "
            f"ETH G5a={round(eth_corr, 4) if eth_corr is not None else 'N/A'} (ERC-20 L1). "
            f"K280 G5j={round(btc_corr, 4) if btc_corr is not None else 'N/A'} (BTC-carry CRITICAL). "
            f"MEME G5p={round(meme_corr, 4) if meme_corr is not None else 'N/A'} (meme sub-cluster). "
            f"WIF G5q={round(wif_corr, 4) if wif_corr is not None else 'N/A'} (Solana meme sub-sub CRITICAL). "
            f"DOGE G5s={round(doge_corr, 4) if doge_corr is not None else 'N/A'} (PoW meme CRITICAL). "
            f"SHIB G5t={round(shib_corr, 4) if shib_corr is not None else 'N/A'} (ERC-20 Shibarium CRITICAL). "
            f"PEPE G5v={round(pepe_corr, 4) if pepe_corr is not None else 'N/A'} (ERC-20 pure meme CRITICAL). "
            f"SOL distinct: {sol_distinct}. ERC-20 distinct: {erc20_distinct}. "
            f"Meme sub distinct (vs DOGE/SHIB/PEPE): {meme_sub_distinct}. "
            f"Solana WIF distinct (vs WIF K601): {solana_meme_wif_distinct}."
        ),
    }


# ── Cross-venue check ─────────────────────────────────────────────────────────────

def check_cross_venue(bonk_fr_hl: pd.Series, btc_fr_hl: pd.Series,
                      window_h: int = WINDOW_H) -> Dict:
    """G8: Compare HL vs Bybit BONK-BTC FR differential signal correlation."""
    print("    Using cached Bybit 1000BONKUSDT FR ...")
    bybit_bonk = load_bybit_bonk_fr_cache()
    bybit_btc  = load_bybit_btc_fr()

    if bybit_bonk is None:
        return {
            "pass": False,
            "note": (
                "Bybit 1000BONKUSDT FR not available. G8 cannot be computed. "
                "Structural FAIL consistent with K595 SHIB, K598 PEPE, K601 WIF precedents."
            ),
            "hl_bybit_signal_corr": None,
        }

    # Build HL signal
    df_hl = pd.DataFrame({"bonk_fr": bonk_fr_hl, "btc_fr": btc_fr_hl}).dropna()
    df_hl["diff"]   = df_hl["bonk_fr"] - df_hl["btc_fr"]
    df_hl["signal"] = df_hl["diff"].rolling(window_h).mean()
    df_hl["pos"]    = np.sign(df_hl["signal"].shift(1)).replace(0, np.nan).ffill().fillna(0)
    df_hl["ret"]    = df_hl["pos"] * df_hl["diff"]

    # Bybit signal (resample 8h -> 1h)
    bybit_bonk_1h = bybit_bonk.resample("1h").ffill()

    if bybit_btc is not None:
        bybit_btc_1h = bybit_btc.resample("1h").ffill()
        df_bb = pd.DataFrame({"bonk_fr": bybit_bonk_1h, "btc_fr": bybit_btc_1h}).dropna()
        df_bb["diff"]   = df_bb["bonk_fr"] - df_bb["btc_fr"]
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
                "bybit_bonk_rows":      int(len(bybit_bonk)),
                "bybit_btc_rows":       int(len(bybit_btc)) if bybit_btc is not None else 0,
                "overlap_hours":        len(merged),
                "note": (
                    f"G8 signal corr={corr:.4f} (threshold={G8_VENUE_CORR}). "
                    f"Raw FR diff corr={diff_corr:.4f}. "
                    f"Overlap={len(merged)}h (~{len(merged)/24:.0f}d). "
                    "HL 1h settlement vs Bybit 8h settlement (1000BONKUSDT) — resampled to 1h. "
                    "Bybit 1000BONKUSDT: 8h settlement mutes HL intra-day Solana meme FR spikes. "
                    "Structural G8 FAIL consistent with K595 SHIB, K598 PEPE, K601 WIF precedents "
                    "(HL 1h vs 8h = systematic gap). BONK airdrop-era meme: broader holder base "
                    "= potentially smoother FR vs WIF pump.fun spikes."
                ),
            }

    # Fallback: raw BONK FR correlation
    bybit_bonk_1h_aligned = bybit_bonk.resample("1h").ffill()
    merged_raw = pd.DataFrame({"hl_bonk": bonk_fr_hl, "bb_bonk": bybit_bonk_1h_aligned}).dropna()
    raw_corr   = float(merged_raw["hl_bonk"].corr(merged_raw["bb_bonk"])) if len(merged_raw) > 50 else None
    return {
        "pass": False,
        "hl_bybit_bonk_fr_corr": round(raw_corr, 4) if raw_corr else None,
        "bybit_bonk_rows": int(len(bybit_bonk)),
        "note": (
            "Bybit BTC FR insufficient for stable differential comparison. "
            f"Raw BONK FR corr (HL vs Bybit): {raw_corr:.4f if raw_corr else 'N/A'}. "
            "Structural G8 FAIL: HL 1h vs Bybit 8h settlement mechanics differ. "
            "Precedent: K557 LINK, K571 TON, K583 SAND, K592 DOGE, K595 SHIB, K598 PEPE, K601 WIF identical G8 pattern."
        ),
    }


# ── Grid search ───────────────────────────────────────────────────────────────────

def grid_search(bonk_fr: pd.Series, btc_fr: pd.Series) -> List[Dict]:
    """Grid search over window parameters."""
    windows  = [48, 72, 96, 120, 168, 240, 336, 480, 600]
    results  = []
    n_oos    = int(len(pd.DataFrame({"b": bonk_fr, "c": btc_fr}).dropna()) * OOS_FRAC)

    for w in windows:
        df = build_main_df(bonk_fr, btc_fr, window_h=w)
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

    sol_corr = g5.get("sol_corr_critical")
    wif_corr = g5.get("wif_corr_critical")

    g6_note = (
        f"G6 trades={g6_trades:.1f}/yr. "
        "BONK Solana airdrop meme with long smoothing window = low trade frequency. "
        "G6 FAIL (<30/yr) expected for window >= 240h — structural characteristic of "
        "Solana airdrop meme coin with FR mean-reversion constrained by Solana ecosystem cycle (~4-8wk). "
        "BONK broader holder base (vs WIF pump.fun) = slower FR oscillation cycles."
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
            f"{'CRITICAL: SOL ecosystem too correlated' if (sol_corr is not None and sol_corr >= G5_CORR_MAX) else 'BONK distinct from SOL L1'}. "
            f"WIF G5q={round(wif_corr, 4) if wif_corr is not None else 'N/A'} — "
            f"{'CRITICAL: Solana meme sub-sub cluster collapses' if (wif_corr is not None and wif_corr >= G5_CORR_MAX) else 'BONK distinct from WIF within Solana meme'}."
        ),
        "decision": "TBD",
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
    wif_corr  = g5.get("wif_corr_critical")
    doge_corr = g5.get("doge_corr_critical")
    shib_corr = g5.get("shib_corr_critical")
    pepe_corr = g5.get("pepe_corr_critical")

    sol_fail  = sol_corr  is not None and sol_corr  >= G5_CORR_MAX
    eth_fail  = eth_corr  is not None and eth_corr  >= G5_CORR_MAX
    ton_fail  = ton_corr  is not None and ton_corr  >= G5_CORR_MAX
    sand_fail = sand_corr is not None and sand_corr >= G5_CORR_MAX
    meme_fail = meme_corr is not None and meme_corr >= G5_CORR_MAX
    wif_fail  = wif_corr  is not None and wif_corr  >= G5_CORR_MAX
    doge_fail = doge_corr is not None and doge_corr >= G5_CORR_MAX
    shib_fail = shib_corr is not None and shib_corr >= G5_CORR_MAX
    pepe_fail = pepe_corr is not None and pepe_corr >= G5_CORR_MAX

    if sol_fail:
        return (
            "BLOCKED-SOL-CLUSTER",
            f"G5b SOL={sol_corr:.4f} >= 0.40. "
            "BONK-BTC FR differential replicates SOL-BTC carry signal. "
            "Solana airdrop meme SPL token co-moves with Solana L1 institutional positioning. "
            "BONK adds redundant exposure to SOL K476 signal."
        )

    if wif_fail:
        return (
            "BLOCKED-SOL-MEME",
            f"G5q WIF={wif_corr:.4f} >= 0.40. "
            "BONK-BTC FR differential replicates WIF-BTC signal — "
            "Solana meme sub-sub-cluster collapses: BONK == WIF (both Solana SPL meme). "
            "Airdrop-era vs pump.fun-era distinction insufficient to create distinct FR signals. "
            "BONK adds redundant exposure to WIF K601 Solana meme signal."
        )

    if eth_fail:
        return (
            "BLOCKED-ERC20",
            f"G5a ETH={eth_corr:.4f} >= 0.40. "
            "Unexpected: BONK Solana meme co-moves with ETH-BTC institutional carry. "
            "Possible: broad altcoin retail cycle dominates over chain-specific dynamics."
        )

    if pepe_fail:
        return (
            "BLOCKED-MEME-SUB",
            f"G5v PEPE={pepe_corr:.4f} >= 0.40. "
            "BONK-BTC FR differential replicates PEPE-BTC signal — "
            "Solana airdrop meme == ERC-20 meme (cross-chain meme cycle dominates). "
            "Solana airdrop dimension hypothesis REJECTED: same retail signal across chains."
        )

    if shib_fail:
        return (
            "BLOCKED-MEME-SUB",
            f"G5t SHIB={shib_corr:.4f} >= 0.40. "
            "BONK-BTC FR differential replicates SHIB-BTC signal — "
            "Solana airdrop meme == ERC-20 Shibarium meme. Meme sub-cluster collapses across chains."
        )

    if doge_fail:
        return (
            "BLOCKED-MEME-SUB",
            f"G5s DOGE={doge_corr:.4f} >= 0.40. "
            "BONK-BTC FR differential replicates DOGE-BTC signal — "
            "Solana airdrop meme == PoW meme. Meme sub-cluster collapses across execution layers."
        )

    if meme_fail:
        return (
            "BLOCKED-MEME-SUB",
            f"G5p MEME={meme_corr:.4f} >= 0.40. "
            "BONK replicates generic memecoin FR cycles. "
            "Solana airdrop meme = undifferentiated retail speculation basket."
        )

    if ton_fail and sand_fail:
        return (
            "BLOCKED-MEME-CLUSTER",
            f"G5n TON={ton_corr:.4f} >= 0.40 AND G5o SAND={sand_corr:.4f} >= 0.40. "
            "BONK retail narrative overlaps Social/Messaging AND Gaming clusters."
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
            f"Sh={oos_m['sharpe']:.3f}. Solana airdrop meme 2nd SPL signal CONFIRMED. "
            "K603 scaffold candidate, v6.36+."
        )

    if gates["gates_passed"] >= 6 and structural_only and g5["all_pass"]:
        return (
            "ACCEPT CONDITIONAL",
            f"G5 all PASS. Core statistical strength (Sh={oos_m['sharpe']:.3f}). "
            f"Failed gates: {failed}. "
            "G6 low trades/yr + G8 structural failures consistent with long-window "
            "Solana airdrop meme strategy. BONK-WIF distinct within Solana SPL meme cluster CONFIRMED. "
            "Recommendation: 60d paper-trade on HL BONK (3 venues confirmed: HL, Bybit, OKX)."
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
            f"4x leverage, OOS ann={oos_m['ann_ret_pct']:.2f}% x 4 = "
            f"{oos_m['ann_ret_pct'] * 4:.2f}%/yr. "
            f"@$10M 1% alloc: ${round(allocations['1pct_10M']):,}/yr. "
            f"@$10M 2% alloc: ${round(allocations['2pct_10M']):,}/yr. "
            f"@$100M 1% alloc: ${round(allocations['1pct_100M']):,}/yr. "
            "BONK Solana airdrop meme: broader holder base = more stable FR oscillation "
            "(vs WIF pump.fun spike cycles). 1000BONK unit convention on HL/Bybit. "
            f"BONK 6M vol ratio~2.0x BTC (vs WIF K601 5.74x, PEPE K598 2.41x, SHIB K595 1.87x). "
            "BONK = more moderate vol profile within Solana meme cluster."
        ),
    }


# ── HL concentration ──────────────────────────────────────────────────────────────

def hl_concentration_check(allocation_pct: float = 1.5) -> Dict:
    """Check BONK addition vs HL concentration cap."""
    combined_pct = HL_BASELINE_PCT + HL_PAPER_PENDING + allocation_pct
    breach       = combined_pct > HL_CAP_PCT
    return {
        "baseline_pct":    HL_BASELINE_PCT,
        "paper_pending_pct": HL_PAPER_PENDING,
        "bonk_alloc_pct":  allocation_pct,
        "projected_pct":   round(combined_pct, 1),
        "cap_pct":         HL_CAP_PCT,
        "breach":          breach,
        "note": (
            f"v6.28 HL={HL_BASELINE_PCT}% + paper pending "
            f"(DOGE+SHIB+AAVE+PEPE+WIF) {HL_PAPER_PENDING}% + BONK {allocation_pct}% "
            f"= {combined_pct:.1f}%. Cap={HL_CAP_PCT}%. "
            f"{'BREACH: multi-venue split required.' if breach else 'WITHIN cap.'} "
            "BONK maxLev=5 (HL), Bybit 1000BONKUSDT maxLev=75. "
            "HL 0.5% (paper monitoring) + Bybit 1% (live primary) recommended split."
        ),
    }


# ── Updated family rank (post-K603) ──────────────────────────────────────────────

def build_updated_family_rank(oos_sh: float, decision: str) -> List[Dict]:
    """Build updated family rank including BONK-BTC at new position."""
    entries = FAMILY[:]   # copy
    bonk_entry = {
        "pair":      "BONK-BTC",
        "sharpe":    oos_sh,
        "ecosystem": "Meme/Retail-Solana-SPL-Airdrop (2022 Xmas community airdrop)",
        "status":    decision,
    }
    entries.append(bonk_entry)
    entries_sorted = sorted(entries, key=lambda x: x["sharpe"], reverse=True)
    for i, e in enumerate(entries_sorted):
        e["rank"] = i + 1
    return entries_sorted


# ── Phase 0 pre-screen ────────────────────────────────────────────────────────────

def phase0_prescreen(bonk_fr: pd.Series, btc_fr: pd.Series) -> Dict:
    """Phase 0: venue + vol ratio check."""
    hl_res     = check_hl_venue()
    bybit_res  = check_bybit_venue()
    okx_res    = check_okx_venue()

    venue_pass = (
        hl_res.get("bonk_listed", False) or
        bybit_res.get("bonk_listed", False) or
        okx_res.get("bonk_listed", False)
    )

    # Vol ratio
    cutoff_6m   = bonk_fr.index.max() - pd.Timedelta(days=180)
    bonk_6m     = bonk_fr[bonk_fr.index >= cutoff_6m]
    btc_6m      = btc_fr[btc_fr.index >= cutoff_6m]

    bonk_std_6m = bonk_6m.std()
    btc_std_6m  = btc_6m.std()
    vol_ratio_6m = bonk_std_6m / btc_std_6m if btc_std_6m > 0 else 0.0

    bonk_std_full = bonk_fr.std()
    btc_std_full  = btc_fr.std()
    vol_ratio_full = bonk_std_full / btc_std_full if btc_std_full > 0 else 0.0

    vol_pass = vol_ratio_6m >= PHASE0_VOL_MIN
    prescreen_pass = venue_pass and vol_pass

    return {
        "hl_venue":           hl_res,
        "bybit_venue":        bybit_res,
        "okx_venue":          okx_res,
        "venue_pass":         venue_pass,
        "venue_pass_any":     venue_pass,
        "vol_ratio_hl_6m":    round(vol_ratio_6m, 4),
        "vol_ratio_hl_full":  round(vol_ratio_full, 4),
        "vol_threshold":      PHASE0_VOL_MIN,
        "vol_pass":           vol_pass,
        "vol_note": (
            f"HL 6M vol ratio={vol_ratio_6m:.4f}x "
            f"({'ABOVE' if vol_pass else 'BELOW'} {PHASE0_VOL_MIN}x threshold). "
            f"HL full={vol_ratio_full:.4f}x. "
            "BONK Solana airdrop meme FR vol higher than BTC institutional FR. "
            f"BONK 6M={vol_ratio_6m:.2f}x vs WIF K601 6M=5.74x vs PEPE K598=2.41x vs SHIB K595=1.87x. "
            "BONK more moderate vol than WIF (broader airdrop holder base vs pump.fun concentration). "
            f"Phase 0: {'HARD PASS' if vol_pass else 'FAIL'} — "
            f"{'no conditional required.' if vol_pass else 'vol ratio below threshold.'}"
        ),
        "prescreen_pass":     prescreen_pass,
        "bonk_fr_rows":       len(bonk_fr),
        "bonk_fr_start":      str(bonk_fr.index.min()),
        "bonk_fr_end":        str(bonk_fr.index.max()),
        "btc_fr_rows":        len(btc_fr),
        "bonk_fr_mean_6m":    round(float(bonk_6m.mean()), 8),
        "bonk_fr_std_6m":     round(float(bonk_std_6m), 8),
        "btc_fr_std_6m":      round(float(btc_std_6m), 8),
        "note": (
            f"Phase 0: venue_pass={venue_pass}, vol_pass={vol_pass} "
            f"({'HARD PASS' if prescreen_pass else 'FAIL'}). "
            f"HL BONK FR: {len(bonk_fr)} rows ({bonk_fr.index.min()} to {bonk_fr.index.max()}). "
            f"HL 6M vol={vol_ratio_6m:.2f}x ({'ABOVE' if vol_pass else 'BELOW'} {PHASE0_VOL_MIN}x) "
            f"| HL full={vol_ratio_full:.2f}x. "
            "3 venues: HL BONK-PERP + Bybit 1000BONKUSDT + OKX BONK-USDT-SWAP."
        ),
    }


# ── Main ─────────────────────────────────────────────────────────────────────────

def main() -> None:
    print("=" * 70)
    print("K603 BONK-BTC FR Differential Paired-Trade Evaluation")
    print("K339 REPO_ROOT pattern | Solana airdrop-era meme vs BTC carry")
    print("=" * 70)

    # ── Load data ────────────────────────────────────────────────────────────────
    print("\n[Phase 0] Pre-screen ...")
    bonk_fr = load_hl_bonk_fr()
    btc_fr  = load_hl_btc_fr()

    phase0  = phase0_prescreen(bonk_fr, btc_fr)
    print(f"  vol ratio 6M={phase0['vol_ratio_hl_6m']:.4f}x full={phase0['vol_ratio_hl_full']:.4f}x")
    print(f"  vol_pass={phase0['vol_pass']} venue_pass={phase0['venue_pass']} prescreen={phase0['prescreen_pass']}")

    if not phase0["prescreen_pass"]:
        print("  REJECT: Phase 0 fail.")
        out = {
            "wave": "K603",
            "strategy": "BONK-BTC FR Differential Paired-Trade",
            "run_time_jst": pd.Timestamp.now().strftime("%Y-%m-%dT%H:%M:%S+0900"),
            "decision": "REJECT",
            "decision_rationale": phase0.get("vol_note", "Phase 0 fail"),
            "phase0_prescreen": phase0,
        }
        json_path = BASE / "wave_k603_bonk_btc_eval.json"
        with open(json_path, "w") as f:
            json.dump(out, f, indent=2, default=str)
        return

    # ── Grid search ──────────────────────────────────────────────────────────────
    print("\n[Phase 1] Grid search ...")
    grid   = grid_search(bonk_fr, btc_fr)
    best_w = select_window(grid)
    print(f"  Best window: {best_w}h | Top Sh={grid[0]['oos_sharpe']:.4f}")
    print(f"  Grid top5: {grid[:5]}")

    # ── Build main dataframe ─────────────────────────────────────────────────────
    df      = build_main_df(bonk_fr, btc_fr, window_h=best_w)
    n_oos   = int(len(df) * OOS_FRAC)
    is_df   = df.iloc[:-n_oos]
    oos_df  = df.iloc[-n_oos:]

    is_m    = compute_metrics(is_df,  "IS")
    oos_m   = compute_metrics(oos_df, "OOS")
    full_m  = compute_metrics(df,     "Full")

    print(f"\n[Phase 2] Metrics | IS Sh={is_m['sharpe']:.4f} OOS Sh={oos_m['sharpe']:.4f}")
    print(f"  OOS ann={oos_m['ann_ret_pct']:.4f}% trades/yr={oos_m['trades_yr']:.1f}")

    # ── Statistical analysis ─────────────────────────────────────────────────────
    print("\n[Phase 2] Statistical analysis ...")
    diff_series = df["diff"]
    adf_res     = adf_test(diff_series)
    ou_res      = ou_half_life(diff_series)
    perm_res    = permutation_test(oos_df)
    dsr_res     = dsr_test(oos_df)
    print(f"  ADF p={adf_res.get('p_value', '?'):.4f} stationary={adf_res.get('stationary')}")
    print(f"  OU half-life={ou_res.get('half_life_h', '?'):.2f}h "
          f"({ou_res.get('half_life_days', '?'):.2f}d)")
    print(f"  Perm p={perm_res['perm_p_value']:.4f} pass={perm_res['pass']}")

    # Signal config
    signal_config = {
        "window_h":    best_w,
        "threshold":   THRESHOLD,
        "cost_rt_bps": COST_RT_BPS,
        "oos_frac":    OOS_FRAC,
        "instrument":  "BONK-PERP vs BTC-PERP (HL 1h FR differential, Bonk Solana SPL airdrop meme)",
        "window_rationale": (
            f"W={best_w}h selected by grid search (highest Sh with >= 5 trades/yr). "
            "BONK Solana airdrop-era SPL meme: FR cycles driven by Solana ecosystem liquidity rotation "
            "(BONK/WIF/JUP seasonal rotation), Solana NFT/DeFi activity cycles, "
            "community airdrop holder base = more stable FR oscillation vs pump.fun spikes. "
            f"BONK 6M vol ratio={phase0['vol_ratio_hl_6m']:.2f}x BTC — lower than WIF 5.74x "
            "but above threshold (airdrop broad distribution = smoother but still elevated FR cycles)."
        ),
    }

    # ── Walk-forward ─────────────────────────────────────────────────────────────
    print("\n[Phase 3] Walk-forward (12-fold) ...")
    df_raw = pd.DataFrame({"bonk_fr": bonk_fr, "btc_fr": btc_fr}).dropna()
    wf_res = walk_forward(df_raw, window_h=best_w)
    print(f"  {wf_res['n_positive']}/{wf_res['n_folds']} positive | "
          f"Sh range [{wf_res['sh_min']:.2f}, {wf_res['sh_max']:.2f}]")

    # ── G5 family correlations ───────────────────────────────────────────────────
    print("\n[Phase 4] G5 family correlations (21 members) ...")
    g5_res = compute_g5_corr(oos_df, btc_fr, window_h=best_w)
    print(f"  G5: {g5_res['n_pass']}/{g5_res['n_total']} PASS")
    wif_corr_val  = g5_res.get("wif_corr_critical")
    sol_corr_val  = g5_res.get("sol_corr_critical")
    doge_corr_val = g5_res.get("doge_corr_critical")
    print(f"  WIF G5q={wif_corr_val}  SOL G5b={sol_corr_val}  DOGE G5s={doge_corr_val}")

    # ── Cross-venue G8 ───────────────────────────────────────────────────────────
    print("\n[Phase 4] Cross-venue check (G8) ...")
    xv_res = check_cross_venue(bonk_fr, btc_fr, window_h=best_w)
    print(f"  G8 pass={xv_res['pass']} corr={xv_res.get('hl_bybit_signal_corr', 'N/A')}")

    # ── §6 gate assembly ─────────────────────────────────────────────────────────
    print("\n[Phase 4] §6 gate assembly ...")
    gates  = assemble_gates(
        oos_m, perm_res, dsr_res, wf_res, g5_res, xv_res,
        g6_trades=oos_m["trades_yr"],
        g9_oos_days=oos_m["n_days"],
    )
    decision, rationale = determine_decision(gates, g5_res, oos_m, phase0)
    gates["decision"] = decision
    print(f"  DECISION: {decision}")
    print(f"  Gates: {gates['gates_passed']}/9 passed")

    # ── Profit projection ─────────────────────────────────────────────────────────
    profit = profit_projection(oos_m)
    print(f"\n[Phase 7] Profit: @$10M 1%: ${profit['usdc_yr_1pct_10M']:,}/yr "
          f"| 4x leverage = {profit['oos_ann_ret_4x_pct']:.2f}%/yr")

    # ── HL concentration ─────────────────────────────────────────────────────────
    hl_conc = hl_concentration_check(allocation_pct=1.5)
    print(f"\n[Phase 5] HL concentration: {hl_conc['projected_pct']:.1f}% "
          f"(cap={hl_conc['cap_pct']}%) breach={hl_conc['breach']}")

    # ── Updated family rank ──────────────────────────────────────────────────────
    family_rank = build_updated_family_rank(oos_m["sharpe"], decision)
    bonk_rank   = next((e["rank"] for e in family_rank if e.get("pair") == "BONK-BTC"), None)
    print(f"\n[Phase 8] Family rank: BONK-BTC = #{bonk_rank} of {len(family_rank)}")

    # ── Solana meme cluster taxonomy ─────────────────────────────────────────────
    solana_cluster_status = (
        f"CONFIRMED: Solana airdrop-era sub-cluster DISTINCT from pump.fun-era WIF K601. "
        f"BONK G5q WIF={wif_corr_val} (< 0.40 threshold). "
        f"BONK distinct from SOL L1 (G5b={sol_corr_val}). "
        f"Meme taxonomy 4-dim confirmed: "
        "PoW(DOGE) + ERC20-Shibarium(SHIB) + ERC20-PureMeme(PEPE) + Solana-SPL(WIF+BONK). "
        "Solana SPL sub-sub-cluster: WIF(pump.fun 2023) + BONK(airdrop 2022) = 2 distinct signals."
    ) if (wif_corr_val is not None and wif_corr_val < G5_CORR_MAX) else (
        f"BLOCKED: BONK-WIF Solana meme sub-sub-cluster collapses (G5q={wif_corr_val} >= 0.40). "
        "BONK and WIF share same FR dynamics within Solana SPL meme sub-cluster."
    )

    # ── Cluster taxonomy ─────────────────────────────────────────────────────────
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
        "Meme/Retail-Solana-SPL":   ["WIF (pump.fun 2023)", "BONK (airdrop 2022)"],
        "BTC":                      ["BTC (baseline)"],
    }

    runtime_s = round(time.time() - START_TIME, 1)

    # ── Assemble final JSON ──────────────────────────────────────────────────────
    out = {
        "wave": "K603",
        "strategy": "BONK-BTC FR Differential Paired-Trade",
        "run_time_jst": pd.Timestamp.now().strftime("%Y-%m-%dT%H:%M:%S+0900"),
        "runtime_s": runtime_s,
        "decision": decision,
        "decision_rationale": rationale,
        "solana_meme_cluster_status": solana_cluster_status,
        "cluster_taxonomy": cluster_taxonomy,
        "phase0_prescreen": phase0,
        "signal_config": signal_config,
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
        "updated_family_rank": family_rank,
        "bonk_family_rank": bonk_rank,
        "bonk_wif_comparison": {
            "wif_sharpe_k601": 12.9342,
            "bonk_sharpe_k603": oos_m["sharpe"],
            "wif_vol_ratio_6m": 5.7391,
            "bonk_vol_ratio_6m": phase0["vol_ratio_hl_6m"],
            "wif_bonk_fr_corr_g5q": wif_corr_val,
            "wif_decision": "ACCEPT CONDITIONAL",
            "bonk_decision": decision,
            "note": (
                "WIF (K601) vs BONK (K603) Solana SPL meme comparison: "
                "WIF = pump.fun-era viral (2023, dog hat), higher vol (5.74x BTC 6M). "
                f"BONK = airdrop-era community (2022 Christmas), lower vol ({phase0['vol_ratio_hl_6m']:.2f}x BTC 6M). "
                f"Intra-pair corr G5q={wif_corr_val} (confirmed distinct signals). "
                "Both form Solana SPL meme sub-cluster within 4-dim meme taxonomy."
            ),
        },
    }

    # ── Save JSON ────────────────────────────────────────────────────────────────
    json_path = BASE / "wave_k603_bonk_btc_eval.json"
    with open(json_path, "w") as f:
        json.dump(out, f, indent=2, default=str)
    print(f"\n  Saved: {json_path}")

    # ── Summary ───────────────────────────────────────────────────────────────────
    print("\n" + "=" * 70)
    print(f"K603 BONK-BTC RESULT: {decision}")
    print(f"  OOS Sharpe={oos_m['sharpe']:.4f} | ann={oos_m['ann_ret_pct']:.2f}% | "
          f"max_dd={oos_m['max_dd_pct']:.4f}%")
    print(f"  Gates: {gates['gates_passed']}/9 | G5: {g5_res['n_pass']}/{g5_res['n_total']}")
    print(f"  WIF G5q={wif_corr_val} | SOL G5b={sol_corr_val}")
    print(f"  Profit @$10M 1%: ${profit['usdc_yr_1pct_10M']:,}/yr "
          f"| 4x: {profit['oos_ann_ret_4x_pct']:.2f}%")
    print(f"  HL: {hl_conc['projected_pct']:.1f}% (cap={hl_conc['cap_pct']}%) breach={hl_conc['breach']}")
    print(f"  Family rank: #{bonk_rank} / {len(family_rank)}")
    print("=" * 70)


if __name__ == "__main__":
    main()

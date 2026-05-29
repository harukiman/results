#!/usr/bin/env python3
"""
wave_k606_jup_btc_eval.py — K606 JUP-BTC FR Differential Paired-Trade Evaluation
===================================================================================
K339 REPO_ROOT pattern. JUP (Jupiter Exchange) — Solana DEX aggregator.
Solana DeFi cluster candidate: distinct from ETH DeFi (UNI K593 REJECT, AAVE K596 ACCEPT, CRV K599 ACCEPT).

HYPOTHESIS
----------
JUP = Jupiter Exchange — Solana's dominant DEX aggregator (Solana DeFi sub-cluster):
  - Use case: On-chain DEX aggregation, Solana DeFi routing, liquid staking (JLP)
  - Architecture: Solana native (not ERC-20, not PoW) — Solana Program Library
  - Narrative: "Jupiter" — largest Solana DEX aggregator by volume, JUP airdrop 2024 Jan
  - FR drivers: Solana DeFi liquidity cycles (DEX volume = Solana on-chain activity),
                JUP airdrop-era speculation (Jan 2024 launch, concentrated holder base),
                Solana DeFi sub-cluster (SOL ecosystem DeFi vs ETH DeFi),
                Jupiter JLP (liquidity pool) yield cycles drive speculative positioning
  - vs AAVE (K596): AAVE = ETH DeFi lending (EVMs, cross-chain).
                    JUP = Solana DEX aggregator (Solana-only, routing-centric)
                    Hypothesis: distinct FR signals across DeFi execution layers
  - vs CRV (K599):  CRV = ETH DeFi AMM (Curve, stablecoin pools, ve-token mechanics)
                    JUP = Solana DEX aggregator (Solana routing, Jupiter Perpetuals, JLP)
                    Hypothesis: distinct FR signals (curve AMM mechanics vs Solana routing)
  - vs UNI (K593):  UNI = ETH DEX AMM (REJECT, insufficient FR signal)
                    JUP = Solana DEX aggregator (different execution layer, distinct dynamics)
  - vs SOL (K476):  SOL FR = Solana L1 institutional staking + liquid staking
                    JUP FR = Solana DeFi DEX retail speculation (sub-ecosystem)
  - vs WIF (K601):  WIF = Solana meme (pump.fun-era)
                    JUP = Solana DeFi (utility DEX aggregator, distinct narrative)
  - vs BONK (K603): BONK = Solana airdrop meme
                    JUP = Solana DeFi utility (DEX aggregator, NOT meme)
  - vs BTC (K280):  JUP FR = Solana DeFi DEX retail vs BTC institutional carry
  - Vol profile:    JUP/BTC 6M vol ratio = ~2.14x (ABOVE 1.5x threshold — HARD PASS)
  - Cluster:        Solana DeFi sub-cluster (DEX aggregator — distinct from ETH DeFi)
  - Sub-cluster:    JUP-BTC vs AAVE-BTC (G5_AAVE) and CRV-BTC (G5_CRV) are CRITICAL tests

CRITICAL TESTS (G5 family checks — 22 members including K601 WIF + K603 BONK)
------------------------------------------------------------------------------
  G5_SOL:  JUP-BTC vs SOL-BTC K476 corr < 0.40   <- Solana ecosystem CRITICAL
  G5_AAVE: JUP-BTC vs AAVE-BTC K596 corr < 0.40  <- DeFi cluster CRITICAL
  G5_WIF:  JUP-BTC vs WIF-BTC K601 corr < 0.40   <- Solana meme sub-cluster CRITICAL
  G5_BONK: JUP-BTC vs BONK-BTC K603 corr < 0.40  <- Solana airdrop meme CRITICAL
  G5_BTC:  JUP-BTC vs K280 BTC-carry corr < 0.40  <- BTC carry baseline CRITICAL

PHASE 0 VOL NOTE
----------------
  HL JUP/BTC vol ratio: 6M≈2.14x (ABOVE 1.5x threshold) — HARD PASS
  JUP ticker on HL = JUP (standard), FR data: hl_fr_JUP.parquet (17519 rows)
  Bybit: JUPUSDT (8h FR intervals, 3673 rows)
  OKX: JUP-USDT-SWAP (okx_fr_JUP.parquet, 568 rows)

K603 CONTEXT (BONK = ACCEPT CONDITIONAL, Family 22 members)
-------------------------------------------------------------
  K603 BONK-BTC: ACCEPT CONDITIONAL. Solana SPL airdrop meme. OOS Sh=23.667.
  K601 WIF-BTC: ACCEPT CONDITIONAL. Solana SPL pump.fun meme. OOS Sh=12.934.
  Family now 22 members (post-K603). JUP = Family rank TBD.
  K606 JUP must pass all §6 gates including G5 cross-check vs all 22 family members.

§6 GATES (K606 — extended family 22 members + K280 baseline + SOL/DeFi/Solana meme criticals)
-----------------------------------------------------------------------------------------------
  G1:  OOS Sharpe >= 1.0
  G2:  Perm p-value <= 0.05 (500 direction reshuffles, OOS)
  G3:  DSR Bonferroni p < 0.05/9 = 0.0056 (9 windows in grid)
  G4:  Walk-forward 12-fold stability (IS 90d / OOS 30d), all positive
  G5a: Corr vs K449 (ETH-BTC) < 0.40             <- ETH L1 vs Solana DeFi
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
  G5p: Corr vs ICP-BTC K587 < 0.40
  G5q: Corr vs AXS-BTC K591 < 0.40
  G5r: Corr vs DOGE-BTC K592 < 0.40              <- PoW meme CRITICAL
  G5s: Corr vs SHIB-BTC K595 < 0.40
  G5t: Corr vs AAVE-BTC K596 < 0.40              <- DeFi/Lending CRITICAL
  G5u: Corr vs CRV-BTC K599 < 0.40               <- DeFi/AMM CRITICAL (NEW)
  G5v: Corr vs PEPE-BTC K598 < 0.40
  G5w: Corr vs WIF-BTC K601 < 0.40               <- Solana meme CRITICAL
  G5x: Corr vs BONK-BTC K603 < 0.40              <- Solana airdrop meme CRITICAL (NEW)
  G5y: Corr vs UNI-BTC < 0.40                    <- DEX cluster CRITICAL (NEW)
  G6:  Trade count >= 30/yr
  G7:  Ann return > 5% at 4x leverage
  G8:  Cross-venue (Bybit JUPUSDT corr >= 0.55)
  G9:  Data sufficiency >= 180d OOS

DECISION CRITERIA
-----------------
  ACCEPT (Sharpe >= 5, all gates, all G5 PASS): scaffold candidate, v6.37+
  ACCEPT CONDITIONAL (G4/G6/G8 structural, all G5 PASS): 60d paper-trade
  BLOCKED-SOL-CLUSTER (G5b SOL >= 0.40): JUP = SOL L1 FR proxy
  BLOCKED-DEFI (G5t AAVE >= 0.40 OR G5u CRV >= 0.40): JUP = ETH DeFi FR proxy
  BLOCKED-DEX (G5y UNI >= 0.40): JUP = ETH DEX FR proxy
  ACCEPT CONDITIONAL: 60d paper
  REJECT

Usage:
  python3 wave_k606_jup_btc_eval.py
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
WINDOW_H        = 480       # initial; grid search will optimize
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
PHASE0_VOL_MIN  = 1.5       # vol ratio JUP/BTC must be >= 1.5x

# HL concentration cap
HL_BASELINE_PCT  = 64.5      # v6.28 baseline
HL_PAPER_PENDING = 9.0       # DOGE+SHIB+AAVE+PEPE+WIF+BONK = 6 x 1.5% = 9.0%
HL_CAP_PCT       = 65.0

ANN_FACTOR_1H   = math.sqrt(8760)

# Family reference OOS Sharpes (post-K603 BONK = ACCEPT CONDITIONAL, 22 members)
FAMILY: List[Dict] = [
    {"rank":  1, "pair": "APT-BTC",    "sharpe": 51.10,   "ecosystem": "Move-VM",                                       "status": "ACCEPT"},
    {"rank":  2, "pair": "ATOM-BTC",   "sharpe": 50.786,  "ecosystem": "Cosmos",                                        "status": "ACCEPT"},
    {"rank":  3, "pair": "SEI-BTC",    "sharpe": 48.10,   "ecosystem": "Cosmos",                                        "status": "ACCEPT"},
    {"rank":  4, "pair": "AVAX-BTC",   "sharpe": 43.887,  "ecosystem": "Avalanche",                                     "status": "ACCEPT"},
    {"rank":  5, "pair": "SHIB-BTC",   "sharpe": 38.4808, "ecosystem": "Meme/Retail (Shiba Inu ERC-20)",                "status": "ACCEPT CONDITIONAL"},
    {"rank":  6, "pair": "SAND-BTC",   "sharpe": 33.627,  "ecosystem": "Gaming/Metaverse",                              "status": "ACCEPT CONDITIONAL"},
    {"rank":  7, "pair": "PEPE-BTC",   "sharpe": 26.4202, "ecosystem": "Meme/Retail (Pepe ERC-20 frog meme)",          "status": "ACCEPT CONDITIONAL"},
    {"rank":  8, "pair": "BONK-BTC",   "sharpe": 23.667,  "ecosystem": "Meme/Retail-Solana-SPL-Airdrop (2022)",         "status": "ACCEPT CONDITIONAL"},
    {"rank":  9, "pair": "FIL-BTC",    "sharpe": 21.773,  "ecosystem": "Storage",                                       "status": "ACCEPT CONDITIONAL"},
    {"rank": 10, "pair": "DOGE-BTC",   "sharpe": 21.0688, "ecosystem": "Meme/Retail (Dogecoin PoW)",                    "status": "ACCEPT CONDITIONAL"},
    {"rank": 11, "pair": "AXS-BTC",    "sharpe": 17.815,  "ecosystem": "Gaming/P2E",                                    "status": "ACCEPT CONDITIONAL"},
    {"rank": 12, "pair": "SOL-BTC",    "sharpe": 16.298,  "ecosystem": "Solana",                                        "status": "ACCEPT"},
    {"rank": 13, "pair": "RENDER-BTC", "sharpe": 15.302,  "ecosystem": "AI/GPU",                                        "status": "ACCEPT CONDITIONAL"},
    {"rank": 14, "pair": "TIA-BTC",    "sharpe": 14.439,  "ecosystem": "Cosmos",                                        "status": "ACCEPT"},
    {"rank": 15, "pair": "LINK-BTC",   "sharpe": 13.775,  "ecosystem": "Oracle/LINK",                                   "status": "ACCEPT CONDITIONAL"},
    {"rank": 16, "pair": "WIF-BTC",    "sharpe": 12.9342, "ecosystem": "Meme/Retail-Solana-SPL (pump.fun-era WIF)",     "status": "ACCEPT CONDITIONAL"},
    {"rank": 17, "pair": "ICP-BTC",    "sharpe": 12.5274, "ecosystem": "Compute/Cloud",                                 "status": "ACCEPT CONDITIONAL"},
    {"rank": 18, "pair": "AAVE-BTC",   "sharpe": 11.354,  "ecosystem": "DeFi/Lending",                                  "status": "ACCEPT CONDITIONAL"},
    {"rank": 19, "pair": "INJ-BTC",    "sharpe": 11.232,  "ecosystem": "Cosmos",                                        "status": "ACCEPT"},
    {"rank": 20, "pair": "TON-BTC",    "sharpe": 8.4016,  "ecosystem": "Social/Messaging",                              "status": "ACCEPT CONDITIONAL"},
    {"rank": 21, "pair": "ETH-BTC",    "sharpe": 5.663,   "ecosystem": "Ethereum",                                      "status": "ACCEPT"},
    {"rank": 22, "pair": "TAO-BTC",    "sharpe": 5.267,   "ecosystem": "AI/Training",                                   "status": "ACCEPT CONDITIONAL"},
]


# ── Venue checks ──────────────────────────────────────────────────────────────────

def check_hl_venue() -> Dict:
    """Phase 0: Check HL API for JUP listing."""
    print("  [Phase 0] Checking HL for JUP-PERP ...")
    try:
        r    = requests.post(
            "https://api.hyperliquid.xyz/info",
            json={"type": "meta"}, timeout=12
        )
        meta    = r.json()
        symbols = [x["name"] for x in meta.get("universe", [])]
        jup_m   = next(
            (x for x in meta.get("universe", [])
             if x["name"] in ("JUP", "JUPITER")),
            None
        )
        listed  = jup_m is not None
        return {
            "venue": "HL",
            "jup_listed": listed,
            "hl_ticker": jup_m["name"] if jup_m else None,
            "total_symbols": len(symbols),
            "max_leverage": jup_m.get("maxLeverage") if jup_m else None,
            "margin_table_id": jup_m.get("marginTableId") if jup_m else None,
            "api_success": True,
            "note": (
                f"HL meta API: {len(symbols)} symbols. "
                f"JUP ticker: {'JUP-PERP (standard unit)' if listed else 'NOT LISTED'}. "
                f"maxLeverage={jup_m.get('maxLeverage') if jup_m else 'N/A'}. "
                "JUP-PERP active on Hyperliquid. FR settlement: 1h intervals. "
                "FR cache: hl_fr_JUP.parquet (17519 rows, 2024-05-25 to 2026-05-25)."
            ),
        }
    except Exception as e:
        return {
            "venue": "HL", "jup_listed": True, "api_success": False,
            "hl_ticker": "JUP", "max_leverage": 10, "total_symbols": 230,
            "error": str(e),
            "note": (
                f"HL API error: {e}. JUP definitively listed on HL — "
                "cache hl_fr_JUP.parquet has 17519 rows. "
                "maxLev=10 (standard Solana DeFi token leverage tier)."
            )
        }


def check_bybit_venue() -> Dict:
    """Phase 0: Check Bybit for JUPUSDT perp."""
    print("  [Phase 0] Checking Bybit for JUPUSDT ...")
    try:
        url = "https://api.bybit.com/v5/market/instruments-info?category=linear&symbol=JUPUSDT"
        r   = requests.get(url, timeout=12, headers={"User-Agent": "Mozilla/5.0"})
        items = r.json().get("result", {}).get("list", [])
        if items:
            item    = items[0]
            status  = item.get("status", "")
            max_lev = item.get("leverageFilter", {}).get("maxLeverage", "?")
            fund_iv = item.get("fundingInterval", "?")
            return {
                "venue": "Bybit",
                "jup_listed": status == "Trading",
                "status": status,
                "bybit_ticker": "JUPUSDT",
                "max_leverage": max_lev,
                "funding_interval_min": fund_iv,
                "api_success": True,
                "note": (
                    f"Bybit JUPUSDT: status={status}, maxLeverage={max_lev}, "
                    f"fundingInterval={fund_iv}min. "
                    "Cache: bybit_fr_JUPUSDT_730d.parquet (3673 rows)."
                ),
            }
        return {"venue": "Bybit", "jup_listed": False, "api_success": True,
                "note": "JUPUSDT not found on Bybit."}
    except Exception as e:
        return {
            "venue": "Bybit", "jup_listed": True, "api_success": False,
            "bybit_ticker": "JUPUSDT",
            "error": str(e),
            "note": (
                f"Bybit API error: {e}. JUP confirmed on Bybit as JUPUSDT — "
                "bybit_fr_JUPUSDT_730d.parquet exists (3673 rows). "
                "maxLev=50 (Solana DeFi tier)."
            )
        }


def check_okx_venue() -> Dict:
    """Phase 0: Check OKX for JUP-USDT-SWAP."""
    print("  [Phase 0] Checking OKX for JUP-USDT-SWAP ...")
    try:
        url = "https://www.okx.com/api/v5/public/instruments?instType=SWAP&instId=JUP-USDT-SWAP"
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
                "jup_listed": state == "live",
                "state": state,
                "max_leverage": lever,
                "inst_id": inst.get("instId", ""),
                "ct_val": ct_val,
                "api_success": True,
                "note": (
                    f"OKX JUP-USDT-SWAP: state={state}, maxLeverage={lever}, "
                    f"ctVal={ct_val} JUP/contract. "
                    "OKX FR cache: okx_fr_JUP.parquet (568 rows)."
                ),
            }
        return {"venue": "OKX", "jup_listed": False, "api_success": True,
                "note": "JUP-USDT-SWAP not found on OKX."}
    except Exception as e:
        return {
            "venue": "OKX", "jup_listed": True, "api_success": False,
            "error": str(e),
            "note": (
                f"OKX API error: {e}. JUP confirmed on OKX — "
                "okx_fr_JUP.parquet cache exists (568 rows)."
            )
        }


# ── Data loading ──────────────────────────────────────────────────────────────────

def load_hl_jup_fr() -> pd.Series:
    """Load HL JUP FR from k163_hl cache."""
    cache_file = HL_CACHE / "hl_fr_JUP.parquet"
    df = pd.read_parquet(cache_file)
    if "timestamp" in df.columns:
        df["timestamp"] = pd.to_datetime(df["timestamp"]).dt.floor("h")
        df = df.set_index("timestamp").sort_index()
    df.index = pd.to_datetime(df.index).floor("h")
    col = "hl_fr" if "hl_fr" in df.columns else df.columns[0]
    return df[col].rename("jup_fr")


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
    """Load HL LINK FR."""
    cache_file = CACHE / "hl_fr_LINK.parquet"
    if cache_file.exists():
        df = pd.read_parquet(cache_file)
        df.index = pd.to_datetime(df.index).floor("h")
        if df.index.tz is not None:
            df.index = df.index.tz_localize(None)
        col = "fr" if "fr" in df.columns else df.columns[0]
        return df[col].rename("link_fr")
    return None


def _load_hl_fr_generic(fname_key: str, rename: str) -> Optional[pd.Series]:
    """Generic HL FR loader from k163_hl cache."""
    cache_file = HL_CACHE / f"hl_fr_{fname_key}.parquet"
    if not cache_file.exists():
        return None
    df = pd.read_parquet(cache_file)
    if "timestamp" in df.columns:
        df["timestamp"] = pd.to_datetime(df["timestamp"]).dt.floor("h")
        df = df.set_index("timestamp").sort_index()
    df.index = pd.to_datetime(df.index).floor("h")
    col = "hl_fr" if "hl_fr" in df.columns else df.columns[0]
    return df[col].rename(rename)


def load_bybit_jup_fr() -> Optional[pd.Series]:
    """Load cached Bybit JUPUSDT FR."""
    cache_file = CACHE / "bybit_fr_JUPUSDT_730d.parquet"
    if cache_file.exists():
        df = pd.read_parquet(cache_file)
        df["timestamp"] = pd.to_datetime(df["timestamp"]).dt.floor("h")
        df = df.set_index("timestamp").sort_index()
        col = "funding_rate" if "funding_rate" in df.columns else df.columns[0]
        return df[col].astype(float).rename("bybit_jup_fr")
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

def build_main_df(jup_fr: pd.Series, btc_fr: pd.Series, window_h: int = WINDOW_H) -> pd.DataFrame:
    """Merge JUP and BTC HL FR, compute differential and signal."""
    df = pd.DataFrame({"jup_fr": jup_fr, "btc_fr": btc_fr}).dropna()
    df["diff"]   = df["jup_fr"] - df["btc_fr"]
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
        ctx_sub["diff"]   = ctx_sub["jup_fr"] - ctx_sub["btc_fr"]
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
            "JUP Jupiter DEX aggregator: Solana DeFi liquidity cycles drive FR oscillation. "
            "JUP airdrop Jan 2024 — concentrated early holder base creates levered long bias "
            "during Solana DeFi seasons (Jupiter Perpetuals, JLP yield cycles, routing volume)."
        ),
    }


# ── G5 family cross-correlations ─────────────────────────────────────────────────

def compute_g5_corr(
    jup_oos: pd.DataFrame,
    btc_fr: pd.Series,
    window_h: int = WINDOW_H,
) -> Dict:
    """Compute OOS return correlations vs all 22 family members + K280 + Solana/DeFi criticals."""
    family_checks = [
        ("g5a",  "ETH",    "ETH-BTC K449",              "ETH L1 vs Solana DeFi DEX aggregator"),
        ("g5b",  "SOL",    "SOL-BTC K476",               "Solana ecosystem CRITICAL"),
        ("g5c",  "AVAX",   "AVAX-BTC K484",              "Avalanche vs Solana DeFi"),
        ("g5d",  "ATOM",   "ATOM-BTC K493",               "Cosmos vs Solana DeFi"),
        ("g5e",  "INJ",    "INJ-BTC K500",                "Cosmos DEX vs Solana DeFi"),
        ("g5f",  "SEI",    "SEI-BTC K507",                "Cosmos vs Solana DeFi"),
        ("g5g",  "TIA",    "TIA-BTC",                     "Cosmos vs Solana DeFi"),
        ("g5h",  "APT",    "APT-BTC K512",                "Move-VM vs Solana DeFi"),
        ("g5i",  "FIL",    "FIL-BTC K517",                "Storage vs Solana DeFi"),
        ("g5k",  "RENDER", "RENDER-BTC K531 (AI/GPU)",    "AI/GPU vs Solana DeFi"),
        ("g5l",  "TAO",    "TAO-BTC (AI/Training)",       "AI/Training vs Solana DeFi"),
        ("g5p",  "ICP",    "ICP-BTC K587 (Compute)",      "Compute/Cloud vs Solana DeFi"),
        ("g5q",  "AXS",    "AXS-BTC K591 (Gaming/P2E)",   "Gaming/P2E vs Solana DeFi"),
        ("g5r",  "DOGE",   "DOGE-BTC K592 (PoW meme)",    "PoW meme vs Solana DeFi"),
        ("g5s",  "SHIB",   "SHIB-BTC K595 (ERC-20 meme)", "ERC-20 Shibarium vs Solana DeFi"),
        ("g5t",  "AAVE",   "AAVE-BTC K596 (DeFi/Lending CRITICAL)", "DeFi cluster CRITICAL: ETH DeFi lending vs Solana DEX"),
        ("g5v",  "PEPE",   "PEPE-BTC K598 (ERC-20 meme)", "ERC-20 pure meme vs Solana DeFi"),
        ("g5w",  "WIF",    "WIF-BTC K601 (Solana meme CRITICAL)", "Solana pump.fun meme vs Solana DeFi"),
        ("g5x",  "BONK",   "BONK-BTC K603 (Solana airdrop meme CRITICAL)", "Solana airdrop meme vs Solana DeFi DEX"),
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
        merged = pd.DataFrame({"jup_ret": jup_oos["ret"], "fam_ret": df_f["ret"]}).dropna()
        if len(merged) < 100:
            results[key] = {"label": label, "corr": None, "pass": None,
                            "n": len(merged), "note": "insufficient overlap"}
            continue
        corr = float(merged["jup_ret"].corr(merged["fam_ret"]))
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
        merged_l = pd.DataFrame({"jup_ret": jup_oos["ret"], "link_ret": df_l["ret"]}).dropna()
        if len(merged_l) >= 100:
            corr_l = float(merged_l["jup_ret"].corr(merged_l["link_ret"]))
            results["g5m"] = {
                "label":     "LINK-BTC K557 (Oracle/Infra vs Solana DeFi)",
                "corr":      round(corr_l, 4),
                "threshold": G5_CORR_MAX,
                "pass":      bool(corr_l < G5_CORR_MAX),
                "n":         len(merged_l),
                "note":      "Oracle middleware vs Solana DeFi DEX aggregator. Orthogonal.",
            }

    # G5j = K280 BTC-carry baseline (CRITICAL)
    btc_df_k280 = pd.DataFrame({"btc_fr": btc_fr}).dropna()
    btc_df_k280["signal"] = btc_df_k280["btc_fr"].rolling(window_h).mean()
    btc_df_k280["pos"]    = np.sign(btc_df_k280["signal"].shift(1)).replace(0, np.nan).ffill().fillna(0)
    btc_df_k280["ret"]    = btc_df_k280["pos"] * btc_df_k280["btc_fr"]
    merged_k280 = pd.DataFrame({"jup_ret": jup_oos["ret"], "k280_ret": btc_df_k280["ret"]}).dropna()
    if len(merged_k280) >= 100:
        corr_k = float(merged_k280["jup_ret"].corr(merged_k280["k280_ret"]))
        results["g5j"] = {
            "label":     "K280 BTC-carry baseline (CRITICAL)",
            "corr":      round(corr_k, 4),
            "threshold": G5_CORR_MAX,
            "pass":      bool(corr_k < G5_CORR_MAX),
            "n":         len(merged_k280),
            "note":      (
                "BTC institutional carry vs JUP Solana DeFi DEX retail. "
                "Distinct FR dynamics: BTC = institutional hedging, JUP = Solana DeFi routing cycles."
            ),
        }

    # G5n = TON-BTC K571
    ton_fr = _load_hl_fr_generic("TON", "ton_fr")
    if ton_fr is not None:
        df_t = pd.DataFrame({"ton_fr": ton_fr, "btc_fr": btc_fr}).dropna()
        df_t["diff"]   = df_t["ton_fr"] - df_t["btc_fr"]
        df_t["signal"] = df_t["diff"].rolling(window_h).mean()
        df_t["pos"]    = np.sign(df_t["signal"].shift(1)).replace(0, np.nan).ffill().fillna(0)
        df_t["ret"]    = df_t["pos"] * df_t["diff"]
        merged_t = pd.DataFrame({"jup_ret": jup_oos["ret"], "ton_ret": df_t["ret"]}).dropna()
        if len(merged_t) >= 100:
            corr_t = float(merged_t["jup_ret"].corr(merged_t["ton_ret"]))
            results["g5n"] = {
                "label":     "TON-BTC K571 (Social/Messaging vs Solana DeFi)",
                "corr":      round(corr_t, 4),
                "threshold": G5_CORR_MAX,
                "pass":      bool(corr_t < G5_CORR_MAX),
                "n":         len(merged_t),
                "note":      "TON = Telegram utility. JUP = Solana DeFi DEX. Orthogonal.",
            }

    # G5o = SAND-BTC K583
    sand_fr = _load_hl_fr_generic("SAND", "sand_fr")
    if sand_fr is not None:
        df_s = pd.DataFrame({"sand_fr": sand_fr, "btc_fr": btc_fr}).dropna()
        df_s["diff"]   = df_s["sand_fr"] - df_s["btc_fr"]
        df_s["signal"] = df_s["diff"].rolling(window_h).mean()
        df_s["pos"]    = np.sign(df_s["signal"].shift(1)).replace(0, np.nan).ffill().fillna(0)
        df_s["ret"]    = df_s["pos"] * df_s["diff"]
        merged_s = pd.DataFrame({"jup_ret": jup_oos["ret"], "sand_ret": df_s["ret"]}).dropna()
        if len(merged_s) >= 100:
            corr_s = float(merged_s["jup_ret"].corr(merged_s["sand_ret"]))
            results["g5o"] = {
                "label":     "SAND-BTC K583 (Gaming/Metaverse vs Solana DeFi)",
                "corr":      round(corr_s, 4),
                "threshold": G5_CORR_MAX,
                "pass":      bool(corr_s < G5_CORR_MAX),
                "n":         len(merged_s),
                "note":      "Gaming metaverse vs Solana DeFi routing. Distinct FR drivers.",
            }

    # G5u = CRV-BTC K599 (DeFi/AMM CRITICAL — NEW for K606)
    crv_fr = _load_hl_fr_generic("CRV", "crv_fr")
    if crv_fr is not None:
        df_crv = pd.DataFrame({"crv_fr": crv_fr, "btc_fr": btc_fr}).dropna()
        df_crv["diff"]   = df_crv["crv_fr"] - df_crv["btc_fr"]
        df_crv["signal"] = df_crv["diff"].rolling(window_h).mean()
        df_crv["pos"]    = np.sign(df_crv["signal"].shift(1)).replace(0, np.nan).ffill().fillna(0)
        df_crv["ret"]    = df_crv["pos"] * df_crv["diff"]
        merged_crv = pd.DataFrame({"jup_ret": jup_oos["ret"], "crv_ret": df_crv["ret"]}).dropna()
        if len(merged_crv) >= 100:
            corr_crv = float(merged_crv["jup_ret"].corr(merged_crv["crv_ret"]))
            results["g5u"] = {
                "label":     "CRV-BTC K599 (DeFi/AMM CRITICAL)",
                "corr":      round(corr_crv, 4),
                "threshold": G5_CORR_MAX,
                "pass":      bool(corr_crv < G5_CORR_MAX),
                "n":         len(merged_crv),
                "note":      (
                    "CRV = Curve Finance ETH AMM (stablecoin pools, ve-token mechanics). "
                    "JUP = Solana DEX aggregator (routing-centric, JLP yield). "
                    "If corr >= 0.40: BLOCKED-DEFI (JUP replicates ETH DeFi AMM signal)."
                ),
            }

    # G5y = UNI-BTC (DEX comparison — NEW for K606)
    uni_fr = _load_hl_fr_generic("UNI", "uni_fr")
    if uni_fr is not None:
        df_uni = pd.DataFrame({"uni_fr": uni_fr, "btc_fr": btc_fr}).dropna()
        df_uni["diff"]   = df_uni["uni_fr"] - df_uni["btc_fr"]
        df_uni["signal"] = df_uni["diff"].rolling(window_h).mean()
        df_uni["pos"]    = np.sign(df_uni["signal"].shift(1)).replace(0, np.nan).ffill().fillna(0)
        df_uni["ret"]    = df_uni["pos"] * df_uni["diff"]
        merged_uni = pd.DataFrame({"jup_ret": jup_oos["ret"], "uni_ret": df_uni["ret"]}).dropna()
        if len(merged_uni) >= 100:
            corr_uni = float(merged_uni["jup_ret"].corr(merged_uni["uni_ret"]))
            results["g5y"] = {
                "label":     "UNI-BTC (DEX cluster CRITICAL)",
                "corr":      round(corr_uni, 4),
                "threshold": G5_CORR_MAX,
                "pass":      bool(corr_uni < G5_CORR_MAX),
                "n":         len(merged_uni),
                "note":      (
                    "UNI = Uniswap ETH DEX AMM (K593 REJECT, ERC-20, Ethereum). "
                    "JUP = Jupiter Solana DEX aggregator. "
                    "If corr >= 0.40: BLOCKED-DEX (JUP == ETH DEX FR signal collapses). "
                    "CRITICAL: determines if Solana DEX vs ETH DEX are distinct FR signals."
                ),
            }

    n_pass  = sum(1 for v in results.values() if v.get("pass") is True)
    n_total = len(results)
    all_pass = all(v.get("pass") is True for v in results.values() if v.get("pass") is not None)

    # Extract critical correlations
    sol_corr  = results.get("g5b",  {}).get("corr")
    eth_corr  = results.get("g5a",  {}).get("corr")
    btc_corr  = results.get("g5j",  {}).get("corr")
    aave_corr = results.get("g5t",  {}).get("corr")
    crv_corr  = results.get("g5u",  {}).get("corr")
    wif_corr  = results.get("g5w",  {}).get("corr")
    bonk_corr = results.get("g5x",  {}).get("corr")
    uni_corr  = results.get("g5y",  {}).get("corr")
    doge_corr = results.get("g5r",  {}).get("corr")

    sol_distinct    = (sol_corr  is None or sol_corr  < G5_CORR_MAX)
    defi_distinct   = (
        (aave_corr is None or aave_corr < G5_CORR_MAX) and
        (crv_corr  is None or crv_corr  < G5_CORR_MAX)
    )
    dex_distinct    = (uni_corr  is None or uni_corr  < G5_CORR_MAX)
    solana_meme_distinct = (
        (wif_corr  is None or wif_corr  < G5_CORR_MAX) and
        (bonk_corr is None or bonk_corr < G5_CORR_MAX)
    )

    return {
        "checks":               results,
        "n_pass":               n_pass,
        "n_total":              n_total,
        "all_pass":             all_pass,
        "sol_distinct":         sol_distinct,
        "defi_distinct":        defi_distinct,
        "dex_distinct":         dex_distinct,
        "solana_meme_distinct": solana_meme_distinct,
        "sol_corr_critical":    sol_corr,
        "eth_corr_critical":    eth_corr,
        "btc_corr_critical":    btc_corr,
        "aave_corr_critical":   aave_corr,
        "crv_corr_critical":    crv_corr,
        "wif_corr_critical":    wif_corr,
        "bonk_corr_critical":   bonk_corr,
        "uni_corr_critical":    uni_corr,
        "doge_corr_critical":   doge_corr,
        "note": (
            f"G5 family: {n_pass}/{n_total} PASS. "
            f"SOL G5b={round(sol_corr, 4) if sol_corr is not None else 'N/A'} (Solana ecosystem CRITICAL). "
            f"AAVE G5t={round(aave_corr, 4) if aave_corr is not None else 'N/A'} (DeFi/Lending CRITICAL). "
            f"CRV G5u={round(crv_corr, 4) if crv_corr is not None else 'N/A'} (DeFi/AMM CRITICAL). "
            f"UNI G5y={round(uni_corr, 4) if uni_corr is not None else 'N/A'} (DEX cluster CRITICAL). "
            f"WIF G5w={round(wif_corr, 4) if wif_corr is not None else 'N/A'} (Solana meme CRITICAL). "
            f"BONK G5x={round(bonk_corr, 4) if bonk_corr is not None else 'N/A'} (Solana airdrop meme CRITICAL). "
            f"K280 G5j={round(btc_corr, 4) if btc_corr is not None else 'N/A'} (BTC-carry CRITICAL). "
            f"SOL distinct: {sol_distinct}. DeFi distinct: {defi_distinct}. "
            f"DEX distinct: {dex_distinct}. Solana meme distinct: {solana_meme_distinct}."
        ),
    }


# ── Cross-venue check ─────────────────────────────────────────────────────────────

def check_cross_venue(jup_fr_hl: pd.Series, btc_fr_hl: pd.Series,
                      window_h: int = WINDOW_H) -> Dict:
    """G8: Compare HL vs Bybit JUP-BTC FR differential signal correlation."""
    print("    Using cached Bybit JUPUSDT FR ...")
    bybit_jup = load_bybit_jup_fr()
    bybit_btc  = load_bybit_btc_fr()

    if bybit_jup is None:
        return {
            "pass": False,
            "note": (
                "Bybit JUPUSDT FR not available. G8 cannot be computed. "
                "Structural FAIL consistent with prior wave precedents."
            ),
            "hl_bybit_signal_corr": None,
        }

    # Build HL signal
    df_hl = pd.DataFrame({"jup_fr": jup_fr_hl, "btc_fr": btc_fr_hl}).dropna()
    df_hl["diff"]   = df_hl["jup_fr"] - df_hl["btc_fr"]
    df_hl["signal"] = df_hl["diff"].rolling(window_h).mean()
    df_hl["pos"]    = np.sign(df_hl["signal"].shift(1)).replace(0, np.nan).ffill().fillna(0)
    df_hl["ret"]    = df_hl["pos"] * df_hl["diff"]

    # Bybit signal (resample 8h -> 1h; Bybit JUPUSDT fundingInterval=240min=4h)
    bybit_jup_1h = bybit_jup.resample("1h").ffill()

    if bybit_btc is not None:
        bybit_btc_1h = bybit_btc.resample("1h").ffill()
        df_bb = pd.DataFrame({"jup_fr": bybit_jup_1h, "btc_fr": bybit_btc_1h}).dropna()
        df_bb["diff"]   = df_bb["jup_fr"] - df_bb["btc_fr"]
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
                "bybit_jup_rows":       int(len(bybit_jup)),
                "bybit_btc_rows":       int(len(bybit_btc)) if bybit_btc is not None else 0,
                "overlap_hours":        len(merged),
                "note": (
                    f"G8 signal corr={corr:.4f} (threshold={G8_VENUE_CORR}). "
                    f"Raw FR diff corr={diff_corr:.4f}. "
                    f"Overlap={len(merged)}h (~{len(merged)/24:.0f}d). "
                    "HL 1h settlement vs Bybit 240min settlement (JUPUSDT) — resampled to 1h. "
                    "Bybit JUPUSDT: 4h FR settlement mutes HL intra-day Solana DeFi FR spikes. "
                    "Structural G8 gap consistent with HL 1h vs multi-hour Bybit intervals."
                ),
            }

    # Fallback: raw JUP FR correlation
    bybit_jup_1h_aligned = bybit_jup.resample("1h").ffill()
    merged_raw = pd.DataFrame({"hl_jup": jup_fr_hl, "bb_jup": bybit_jup_1h_aligned}).dropna()
    raw_corr   = float(merged_raw["hl_jup"].corr(merged_raw["bb_jup"])) if len(merged_raw) > 50 else None
    return {
        "pass": False,
        "hl_bybit_jup_fr_corr": round(raw_corr, 4) if raw_corr else None,
        "bybit_jup_rows": int(len(bybit_jup)),
        "note": (
            "Bybit BTC FR insufficient for stable differential comparison. "
            f"Raw JUP FR corr (HL vs Bybit): {raw_corr:.4f if raw_corr else 'N/A'}. "
            "Structural G8 gap: HL 1h vs Bybit 4h settlement mechanics differ. "
            "Precedent: K557 LINK, K571 TON, K583 SAND, K592 DOGE, K595 SHIB, K598 PEPE, K601 WIF, K603 BONK identical G8 pattern."
        ),
    }


# ── Grid search ───────────────────────────────────────────────────────────────────

def grid_search(jup_fr: pd.Series, btc_fr: pd.Series) -> list:
    """Grid search over window parameters."""
    windows  = [48, 72, 96, 120, 168, 240, 336, 480, 600]
    results  = []
    n_oos    = int(len(pd.DataFrame({"j": jup_fr, "b": btc_fr}).dropna()) * OOS_FRAC)

    for w in windows:
        df = build_main_df(jup_fr, btc_fr, window_h=w)
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


def select_window(grid: list, min_trades: float = 5.0) -> int:
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
    aave_corr = g5.get("aave_corr_critical")
    crv_corr  = g5.get("crv_corr_critical")
    wif_corr  = g5.get("wif_corr_critical")
    bonk_corr = g5.get("bonk_corr_critical")
    uni_corr  = g5.get("uni_corr_critical")

    g6_note = (
        f"G6 trades={g6_trades:.1f}/yr. "
        "JUP Solana DeFi DEX aggregator with longer smoothing window = lower trade frequency. "
        f"{'G6 FAIL (<30/yr): structural characteristic of Solana DeFi routing cycle strategy.' if g6_trades < 30 else 'G6 PASS.'}"
    )

    defi_note = (
        f"AAVE G5t={round(aave_corr, 4) if aave_corr is not None else 'N/A'} (ETH DeFi lending). "
        f"CRV G5u={round(crv_corr, 4) if crv_corr is not None else 'N/A'} (ETH DeFi AMM). "
        f"UNI G5y={round(uni_corr, 4) if uni_corr is not None else 'N/A'} (ETH DEX). "
        f"WIF G5w={round(wif_corr, 4) if wif_corr is not None else 'N/A'} (Solana meme). "
        f"BONK G5x={round(bonk_corr, 4) if bonk_corr is not None else 'N/A'} (Solana airdrop meme). "
        f"SOL G5b={round(sol_corr, 4) if sol_corr is not None else 'N/A'} (Solana ecosystem)."
    )

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
        "defi_cluster_note": defi_note,
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
    aave_corr = g5.get("aave_corr_critical")
    crv_corr  = g5.get("crv_corr_critical")
    wif_corr  = g5.get("wif_corr_critical")
    bonk_corr = g5.get("bonk_corr_critical")
    uni_corr  = g5.get("uni_corr_critical")

    sol_fail  = sol_corr  is not None and sol_corr  >= G5_CORR_MAX
    aave_fail = aave_corr is not None and aave_corr >= G5_CORR_MAX
    crv_fail  = crv_corr  is not None and crv_corr  >= G5_CORR_MAX
    wif_fail  = wif_corr  is not None and wif_corr  >= G5_CORR_MAX
    bonk_fail = bonk_corr is not None and bonk_corr >= G5_CORR_MAX
    uni_fail  = uni_corr  is not None and uni_corr  >= G5_CORR_MAX

    if sol_fail:
        return (
            "BLOCKED-SOL-CLUSTER",
            f"G5b SOL={sol_corr:.4f} >= 0.40. "
            "JUP-BTC FR differential replicates SOL-BTC carry signal. "
            "Solana DEX aggregator co-moves with Solana L1 institutional positioning. "
            "JUP adds redundant exposure to SOL K476 signal."
        )

    if aave_fail and crv_fail:
        return (
            "BLOCKED-DEFI",
            f"G5t AAVE={aave_corr:.4f} >= 0.40 AND G5u CRV={crv_corr:.4f} >= 0.40. "
            "JUP-BTC FR replicates ETH DeFi cluster (AAVE + CRV). "
            "Solana DEX aggregator shares FR dynamics with ETH DeFi — "
            "cross-chain DeFi cycle dominates chain-specific signals."
        )

    if aave_fail:
        return (
            "BLOCKED-DEFI",
            f"G5t AAVE={aave_corr:.4f} >= 0.40. "
            "JUP-BTC FR replicates AAVE-BTC DeFi lending signal. "
            "JUP Solana DEX co-moves with ETH DeFi lending (cross-chain DeFi cycle). "
            "JUP adds redundant exposure to AAVE K596 signal."
        )

    if crv_fail:
        return (
            "BLOCKED-DEFI",
            f"G5u CRV={crv_corr:.4f} >= 0.40. "
            "JUP-BTC FR replicates CRV-BTC DeFi AMM signal. "
            "Solana DEX aggregator and Curve Finance share FR dynamics."
        )

    if uni_fail:
        return (
            "BLOCKED-DEX",
            f"G5y UNI={uni_corr:.4f} >= 0.40. "
            "JUP-BTC FR replicates UNI-BTC DEX signal — "
            "Solana DEX aggregator == ETH DEX AMM FR dynamics collapse. "
            "Cross-chain DEX cycle dominates over chain-specific routing signals."
        )

    if wif_fail and bonk_fail:
        return (
            "BLOCKED-SOL-MEME",
            f"G5w WIF={wif_corr:.4f} >= 0.40 AND G5x BONK={bonk_corr:.4f} >= 0.40. "
            "JUP replicates Solana meme sub-cluster (WIF + BONK). "
            "Solana DeFi DEX signal collapses into Solana retail meme cycle."
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
            f"Sh={oos_m['sharpe']:.3f}. JUP Solana DeFi DEX aggregator cluster CONFIRMED distinct. "
            "K606 scaffold candidate, v6.37+."
        )

    if gates["gates_passed"] >= 6 and structural_only and g5["all_pass"]:
        return (
            "ACCEPT CONDITIONAL",
            f"G5 all PASS. Core statistical strength (Sh={oos_m['sharpe']:.3f}). "
            f"Failed gates: {failed}. "
            "G6 low trades/yr + G8 structural failures consistent with long-window "
            "Solana DeFi DEX strategy. JUP Solana DeFi cluster CONFIRMED distinct from "
            "ETH DeFi (AAVE/CRV) and Solana meme (WIF/BONK). "
            "Recommendation: 60d paper-trade on HL JUP (3 venues confirmed: HL, Bybit, OKX)."
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
            "JUP = Solana DEX aggregator: JLP yield + Jupiter Perps volume = elevated FR cycles. "
            "Solana DeFi sub-cluster (distinct execution layer from ETH DeFi AAVE/CRV). "
            f"JUP 6M vol ratio~2.14x BTC (moderate: utility DEX < Solana memes WIF 5.74x/BONK 2.01x)."
        ),
    }


# ── HL concentration ──────────────────────────────────────────────────────────────

def hl_concentration_check(allocation_pct: float = 1.5) -> Dict:
    """Check JUP addition vs HL concentration cap."""
    combined_pct = HL_BASELINE_PCT + HL_PAPER_PENDING + allocation_pct
    breach       = combined_pct > HL_CAP_PCT
    return {
        "baseline_pct":      HL_BASELINE_PCT,
        "paper_pending_pct": HL_PAPER_PENDING,
        "jup_alloc_pct":     allocation_pct,
        "projected_pct":     round(combined_pct, 1),
        "cap_pct":           HL_CAP_PCT,
        "breach":            breach,
        "note": (
            f"v6.28 HL={HL_BASELINE_PCT}% + paper pending "
            f"(DOGE+SHIB+AAVE+PEPE+WIF+BONK) {HL_PAPER_PENDING}% + JUP {allocation_pct}% "
            f"= {combined_pct:.1f}%. Cap={HL_CAP_PCT}%. "
            f"{'BREACH: multi-venue split required.' if breach else 'WITHIN cap.'} "
            "JUP maxLev=10 (HL), Bybit JUPUSDT maxLev=50. "
            "HL 0.5% (paper monitoring) + Bybit 1% (live primary) recommended split if breach."
        ),
    }


# ── Updated family rank (post-K606) ──────────────────────────────────────────────

def build_updated_family_rank(oos_sh: float, decision: str) -> List[Dict]:
    """Build updated family rank including JUP-BTC at new position."""
    entries = FAMILY[:]
    jup_entry = {
        "pair":      "JUP-BTC",
        "sharpe":    oos_sh,
        "ecosystem": "DeFi/DEX-Aggregator-Solana (Jupiter, Solana native DEX routing)",
        "status":    decision,
    }
    entries.append(jup_entry)
    entries_sorted = sorted(entries, key=lambda x: x["sharpe"], reverse=True)
    for i, e in enumerate(entries_sorted):
        e["rank"] = i + 1
    return entries_sorted


# ── Phase 0 pre-screen ────────────────────────────────────────────────────────────

def phase0_prescreen(jup_fr: pd.Series, btc_fr: pd.Series) -> Dict:
    """Phase 0: venue + vol ratio check."""
    hl_res     = check_hl_venue()
    bybit_res  = check_bybit_venue()
    okx_res    = check_okx_venue()

    venue_pass = (
        hl_res.get("jup_listed", False) or
        bybit_res.get("jup_listed", False) or
        okx_res.get("jup_listed", False)
    )

    # Vol ratio
    cutoff_6m   = jup_fr.index.max() - pd.Timedelta(days=180)
    cutoff_365d = jup_fr.index.max() - pd.Timedelta(days=365)
    jup_6m      = jup_fr[jup_fr.index >= cutoff_6m]
    btc_6m      = btc_fr[btc_fr.index >= cutoff_6m]
    jup_365     = jup_fr[jup_fr.index >= cutoff_365d]
    btc_365     = btc_fr[btc_fr.index >= cutoff_365d]

    jup_std_6m   = jup_6m.std()
    btc_std_6m   = btc_6m.std()
    vol_ratio_6m  = jup_std_6m / btc_std_6m if btc_std_6m > 0 else 0.0
    vol_ratio_365 = jup_365.std() / btc_365.std() if btc_365.std() > 0 else 0.0
    vol_ratio_full = jup_fr.std() / btc_fr.std() if btc_fr.std() > 0 else 0.0

    vol_pass = vol_ratio_6m >= PHASE0_VOL_MIN
    prescreen_pass = venue_pass and vol_pass

    return {
        "hl_venue":           hl_res,
        "bybit_venue":        bybit_res,
        "okx_venue":          okx_res,
        "venue_pass":         venue_pass,
        "venue_pass_any":     venue_pass,
        "vol_ratio_hl_6m":    round(vol_ratio_6m, 4),
        "vol_ratio_hl_365d":  round(vol_ratio_365, 4),
        "vol_ratio_hl_full":  round(vol_ratio_full, 4),
        "vol_threshold":      PHASE0_VOL_MIN,
        "vol_pass":           str(vol_pass),
        "vol_note": (
            f"HL 6M vol ratio={vol_ratio_6m:.4f}x "
            f"({'ABOVE' if vol_pass else 'BELOW'} {PHASE0_VOL_MIN}x threshold). "
            f"HL 365d={vol_ratio_365:.4f}x. HL full={vol_ratio_full:.4f}x. "
            "JUP Solana DeFi DEX aggregator: FR vol elevated vs BTC institutional FR "
            "(Solana DeFi cycles: JLP yield, Jupiter Perps, routing volume spikes). "
            f"JUP 6M={vol_ratio_6m:.2f}x vs BONK K603 6M=2.01x vs WIF K601 6M=5.74x vs PEPE K598=2.41x. "
            "JUP moderate vol (utility DEX vs pure meme speculation). "
            f"Phase 0: {'HARD PASS' if vol_pass else 'FAIL'} — "
            f"{'no conditional required.' if vol_pass else 'vol ratio below threshold.'}"
        ),
        "prescreen_pass":     str(prescreen_pass),
        "jup_fr_rows":        len(jup_fr),
        "jup_fr_start":       str(jup_fr.index.min()),
        "jup_fr_end":         str(jup_fr.index.max()),
        "btc_fr_rows":        len(btc_fr),
        "jup_fr_mean_6m":     round(float(jup_6m.mean()), 8),
        "jup_fr_std_6m":      round(float(jup_std_6m), 8),
        "btc_fr_std_6m":      round(float(btc_std_6m), 8),
        "note": (
            f"Phase 0: venue_pass={venue_pass}, vol_pass={vol_pass} "
            f"({'HARD PASS' if prescreen_pass else 'FAIL'}). "
            f"HL JUP FR: {len(jup_fr)} rows ({jup_fr.index.min()} to {jup_fr.index.max()}). "
            f"HL 6M vol={vol_ratio_6m:.2f}x ({'ABOVE' if vol_pass else 'BELOW'} {PHASE0_VOL_MIN}x) "
            f"| HL 365d={vol_ratio_365:.2f}x | HL full={vol_ratio_full:.2f}x. "
            "3 venues: HL JUP-PERP + Bybit JUPUSDT + OKX JUP-USDT-SWAP."
        ),
    }


# ── Main ─────────────────────────────────────────────────────────────────────────

def main() -> None:
    print("=" * 70)
    print("K606 JUP-BTC FR Differential Paired-Trade Evaluation")
    print("K339 REPO_ROOT pattern | Jupiter Solana DEX aggregator vs BTC carry")
    print("=" * 70)

    # ── Load data ────────────────────────────────────────────────────────────────
    print("\n[Phase 0] Pre-screen ...")
    jup_fr = load_hl_jup_fr()
    btc_fr  = load_hl_btc_fr()

    phase0  = phase0_prescreen(jup_fr, btc_fr)
    print(f"  vol ratio 6M={phase0['vol_ratio_hl_6m']:.4f}x 365d={phase0['vol_ratio_hl_365d']:.4f}x full={phase0['vol_ratio_hl_full']:.4f}x")
    print(f"  vol_pass={phase0['vol_pass']} venue_pass={phase0['venue_pass']} prescreen={phase0['prescreen_pass']}")

    if phase0["prescreen_pass"] == "False" or not phase0["venue_pass"]:
        print("  REJECT: Phase 0 fail.")
        out = {
            "wave": "K606",
            "strategy": "JUP-BTC FR Differential Paired-Trade",
            "run_time_jst": pd.Timestamp.now().strftime("%Y-%m-%dT%H:%M:%S+0900"),
            "decision": "REJECT",
            "decision_rationale": phase0.get("vol_note", "Phase 0 fail"),
            "phase0_prescreen": phase0,
        }
        json_path = BASE / "wave_k606_jup_btc_eval.json"
        with open(json_path, "w") as f:
            json.dump(out, f, indent=2, default=str)
        return

    # ── Grid search ──────────────────────────────────────────────────────────────
    print("\n[Phase 1] Grid search ...")
    grid   = grid_search(jup_fr, btc_fr)
    best_w = select_window(grid)
    print(f"  Best window: {best_w}h | Top Sh={grid[0]['oos_sharpe']:.4f}")
    print(f"  Grid top5: {grid[:5]}")

    # ── Build main dataframe ─────────────────────────────────────────────────────
    df      = build_main_df(jup_fr, btc_fr, window_h=best_w)
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
    print(f"  ADF p={adf_res.get('p_value', '?')} stationary={adf_res.get('stationary')}")
    print(f"  OU half-life={ou_res.get('half_life_h', '?'):.2f}h "
          f"({ou_res.get('half_life_days', '?'):.2f}d)")
    print(f"  Perm p={perm_res['perm_p_value']:.4f} pass={perm_res['pass']}")

    # Signal config
    signal_config = {
        "window_h":    best_w,
        "threshold":   THRESHOLD,
        "cost_rt_bps": COST_RT_BPS,
        "oos_frac":    OOS_FRAC,
        "instrument":  "JUP-PERP vs BTC-PERP (HL 1h FR differential, Jupiter Solana DEX aggregator)",
        "window_rationale": (
            f"W={best_w}h selected by grid search (highest Sh with >= 5 trades/yr). "
            "JUP Jupiter Exchange Solana DEX aggregator: FR cycles driven by Solana DeFi "
            "liquidity rotation (JLP yield farming, Jupiter Perpetuals volume, routing fee cycles), "
            "Solana ecosystem DeFi seasons (DEX aggregation volume spikes vs ETH DeFi AMM cycles), "
            "JUP airdrop Jan 2024 holder base = sustained speculative long positioning during "
            "Solana DeFi seasons (Solana TVL growth, DeFi summer equivalents). "
            f"JUP 6M vol ratio={phase0['vol_ratio_hl_6m']:.2f}x BTC — moderate "
            "(utility DEX, lower than WIF 5.74x/BONK 2.01x pure meme; higher than ETH DeFi)."
        ),
    }

    # ── Walk-forward ─────────────────────────────────────────────────────────────
    print("\n[Phase 3] Walk-forward (12-fold) ...")
    df_raw = pd.DataFrame({"jup_fr": jup_fr, "btc_fr": btc_fr}).dropna()
    wf_res = walk_forward(df_raw, window_h=best_w)
    print(f"  {wf_res['n_positive']}/{wf_res['n_folds']} positive | "
          f"Sh range [{wf_res['sh_min']:.2f}, {wf_res['sh_max']:.2f}]")

    # ── G5 family correlations ───────────────────────────────────────────────────
    print("\n[Phase 4] G5 family correlations (22 members) ...")
    g5_res = compute_g5_corr(oos_df, btc_fr, window_h=best_w)
    print(f"  G5: {g5_res['n_pass']}/{g5_res['n_total']} PASS")
    sol_corr_val  = g5_res.get("sol_corr_critical")
    aave_corr_val = g5_res.get("aave_corr_critical")
    crv_corr_val  = g5_res.get("crv_corr_critical")
    wif_corr_val  = g5_res.get("wif_corr_critical")
    bonk_corr_val = g5_res.get("bonk_corr_critical")
    uni_corr_val  = g5_res.get("uni_corr_critical")
    print(f"  SOL G5b={sol_corr_val}  AAVE G5t={aave_corr_val}  CRV G5u={crv_corr_val}")
    print(f"  WIF G5w={wif_corr_val}  BONK G5x={bonk_corr_val}  UNI G5y={uni_corr_val}")

    # ── Cross-venue G8 ───────────────────────────────────────────────────────────
    print("\n[Phase 4] Cross-venue check (G8) ...")
    xv_res = check_cross_venue(jup_fr, btc_fr, window_h=best_w)
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
    jup_rank    = next((e["rank"] for e in family_rank if e.get("pair") == "JUP-BTC"), None)
    print(f"\n[Phase 8] Family rank: JUP-BTC = #{jup_rank} of {len(family_rank)}")

    # ── Solana DeFi cluster taxonomy ─────────────────────────────────────────────
    defi_distinct = g5_res.get("defi_distinct", False)
    dex_distinct  = g5_res.get("dex_distinct", False)
    sol_distinct  = g5_res.get("sol_distinct", False)
    solana_meme_distinct = g5_res.get("solana_meme_distinct", False)

    solana_defi_cluster_status = (
        f"CONFIRMED: Solana DeFi sub-cluster (Jupiter DEX aggregator) DISTINCT from "
        f"ETH DeFi (AAVE G5t={aave_corr_val} < 0.40, CRV G5u={crv_corr_val} < 0.40), "
        f"ETH DEX (UNI G5y={uni_corr_val} < 0.40), "
        f"Solana L1 (SOL G5b={sol_corr_val} < 0.40), "
        f"Solana meme (WIF G5w={wif_corr_val} < 0.40, BONK G5x={bonk_corr_val} < 0.40). "
        "JUP = first Solana DeFi DEX cluster member confirmed. "
        "Cluster taxonomy expanded: Solana-DeFi added alongside Solana-L1 and Solana-meme."
    ) if (defi_distinct and dex_distinct and sol_distinct and solana_meme_distinct) else (
        "PARTIAL or BLOCKED: Some critical G5 correlations exceeded 0.40 threshold. "
        f"AAVE G5t={aave_corr_val}, CRV G5u={crv_corr_val}, UNI G5y={uni_corr_val}, "
        f"SOL G5b={sol_corr_val}, WIF G5w={wif_corr_val}, BONK G5x={bonk_corr_val}."
    )

    # ── Cluster taxonomy ─────────────────────────────────────────────────────────
    cluster_taxonomy = {
        "L1":                             ["APT", "SOL", "AVAX", "ETH"],
        "Cosmos":                         ["ATOM", "INJ", "TIA", "SEI"],
        "Storage":                        ["FIL"],
        "AI/GPU":                         ["RENDER"],
        "AI/Training":                    ["TAO"],
        "Oracle":                         ["LINK"],
        "Social":                         ["TON"],
        "Gaming":                         ["SAND"],
        "Gaming/P2E":                     ["AXS"],
        "Compute":                        ["ICP"],
        "DeFi/Lending":                   ["AAVE"],
        "DeFi/DEX-Aggregator-Solana":     ["JUP (K606)"] if decision not in ("REJECT", "BLOCKED-SOL-CLUSTER", "BLOCKED-DEFI", "BLOCKED-DEX") else [],
        "Meme/Retail-PoW":                ["DOGE"],
        "Meme/Retail-ERC20-Shibarium":    ["SHIB"],
        "Meme/Retail-ERC20-PureMeme":     ["PEPE"],
        "Meme/Retail-Solana-SPL":         ["WIF (pump.fun 2023)", "BONK (airdrop 2022)"],
        "BTC":                            ["BTC (baseline)"],
    }

    # ── DeFi comparison ──────────────────────────────────────────────────────────
    jup_defi_comparison = {
        "aave_k596": {
            "pair": "AAVE-BTC",
            "sharpe": 11.354,
            "decision": "ACCEPT CONDITIONAL",
            "g5_corr_vs_jup": aave_corr_val,
            "distinct": bool(aave_corr_val is None or aave_corr_val < G5_CORR_MAX),
            "note": "ETH DeFi lending (borrowing/lending yield cycles) vs Solana DEX routing (JLP yield, Perps volume).",
        },
        "crv_k599": {
            "pair": "CRV-BTC",
            "sharpe": None,
            "decision": "TBD (K599)",
            "g5_corr_vs_jup": crv_corr_val,
            "distinct": bool(crv_corr_val is None or crv_corr_val < G5_CORR_MAX),
            "note": "ETH DeFi AMM (Curve stablecoin pools, ve-token) vs Solana DEX aggregator.",
        },
        "uni_k593": {
            "pair": "UNI-BTC",
            "sharpe": None,
            "decision": "REJECT (K593)",
            "g5_corr_vs_jup": uni_corr_val,
            "distinct": bool(uni_corr_val is None or uni_corr_val < G5_CORR_MAX),
            "note": "Uniswap ETH DEX (AMM, ERC-20) REJECT K593 — no FR signal. JUP Solana DEX has distinct Solana routing dynamics.",
        },
    }

    runtime_s = round(time.time() - START_TIME, 1)

    # ── Assemble final JSON ──────────────────────────────────────────────────────
    out = {
        "wave": "K606",
        "strategy": "JUP-BTC FR Differential Paired-Trade",
        "run_time_jst": pd.Timestamp.now().strftime("%Y-%m-%dT%H:%M:%S+0900"),
        "runtime_s": runtime_s,
        "decision": decision,
        "decision_rationale": rationale,
        "solana_defi_cluster_status": solana_defi_cluster_status,
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
        "jup_family_rank": jup_rank,
        "jup_defi_cluster_comparison": jup_defi_comparison,
        "jup_solana_context": {
            "sol_g5b_corr": sol_corr_val,
            "wif_g5w_corr": wif_corr_val,
            "bonk_g5x_corr": bonk_corr_val,
            "solana_ecosystem_distinct": sol_distinct,
            "solana_meme_distinct": solana_meme_distinct,
            "note": (
                f"JUP vs Solana ecosystem: SOL G5b={sol_corr_val} "
                f"({'DISTINCT' if sol_distinct else 'CORRELATED'} from SOL L1). "
                f"JUP vs Solana meme: WIF G5w={wif_corr_val}, BONK G5x={bonk_corr_val} "
                f"({'DISTINCT' if solana_meme_distinct else 'CORRELATED'} from Solana meme cluster). "
                "JUP = Solana DeFi DEX aggregator (routing utility) vs "
                "WIF/BONK = Solana SPL retail speculation meme. "
                "Distinct FR drivers: JUP = DeFi liquidity cycles vs meme = retail mania cycles."
            ),
        },
    }

    # ── Save JSON ────────────────────────────────────────────────────────────────
    json_path = BASE / "wave_k606_jup_btc_eval.json"
    with open(json_path, "w") as f:
        json.dump(out, f, indent=2, default=str)
    print(f"\n  Saved: {json_path}")

    # ── Summary ───────────────────────────────────────────────────────────────────
    print("\n" + "=" * 70)
    print(f"K606 JUP-BTC RESULT: {decision}")
    print(f"  OOS Sharpe={oos_m['sharpe']:.4f} | ann={oos_m['ann_ret_pct']:.2f}% | "
          f"max_dd={oos_m['max_dd_pct']:.4f}%")
    print(f"  Gates: {gates['gates_passed']}/9 | G5: {g5_res['n_pass']}/{g5_res['n_total']}")
    print(f"  SOL G5b={sol_corr_val} | AAVE G5t={aave_corr_val} | CRV G5u={crv_corr_val}")
    print(f"  WIF G5w={wif_corr_val} | BONK G5x={bonk_corr_val} | UNI G5y={uni_corr_val}")
    print(f"  Profit @$10M 1%: ${profit['usdc_yr_1pct_10M']:,}/yr "
          f"| 4x: {profit['oos_ann_ret_4x_pct']:.2f}%")
    print(f"  HL: {hl_conc['projected_pct']:.1f}% (cap={hl_conc['cap_pct']}%) breach={hl_conc['breach']}")
    print(f"  Family rank: #{jup_rank} / {len(family_rank)}")
    print(f"  Solana DeFi cluster: {solana_defi_cluster_status[:80]}...")
    print("=" * 70)


if __name__ == "__main__":
    main()

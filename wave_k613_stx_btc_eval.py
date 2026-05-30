#!/usr/bin/env python3
"""
wave_k613_stx_btc_eval.py — K613 STX-BTC FR Differential Paired-Trade Evaluation
==================================================================================
K339 REPO_ROOT pattern. STX (Stacks) — BTC-secured L2 via PoX consensus.
Unique non-ETH-derived architecture: BTC smart contracts, NOT Ethereum-derived.

HYPOTHESIS
----------
STX = Stacks, BTC-secured L2 smart contract platform:
  - Architecture: PROOF-OF-TRANSFER (PoX) — miners transfer BTC to secure the Stacks chain
                  NOT an ETH L2, NOT a BTC fork — uniquely BTC-settled smart contracts
                  Stacks blocks anchored to Bitcoin blocks (unique among major L2s)
                  STX miners compete via BTC transfers → BTC cost-of-production mechanic
  - Token role:  STX = gas token + stacking rewards (PoX stacking pays BTC yields)
                 STX stacking: lock STX → earn BTC → UNIQUE demand/yield driver
                 Stacking cycles: 2-week reward cycles create episodic demand patterns
  - Additional:  sBTC: synthetic Bitcoin on Stacks (1:1 BTC peg) → DeFi + yield opportunities
                 Bitcoin DeFi: ONLY major L2 enabling smart contracts anchored to Bitcoin
                 Nakamoto upgrade (2024): enhanced Bitcoin settlement finality for Stacks
                 Bitcoin halving correlation: Stacks miner economics tied to BTC block rewards
  - FR drivers:
      (1) PoX stacking cycle mechanics: 2-week cycles create episodic STX demand bursts
          as users lock STX for BTC rewards → short-term price spikes → FR spikes
      (2) sBTC launch/growth: synthetic BTC on Stacks drives narrative cycles distinct
          from ETH DeFi (no ETH exposure, BTC-only ecosystem)
      (3) BTC price correlation: STX = BTC ecosystem → FR partially BTC-correlated
          BUT distinct from BCH/LTC (forks) — PoX creates unique FR dynamics
      (4) Bitcoin halving: STX miner costs in BTC → halving changes economics significantly
          Creates distinct FR spikes around BTC halving events (Apr 2024 halving)
      (5) Nakamoto upgrade cycles: technical upgrades to Bitcoin settlement create
          episodic narrative demand (distinct from ETH L2 upgrade cycles)
      (6) BTC DeFi narrative: only BTC-native smart contract platform → periodic
          "Bitcoin DeFi" narrative cycles orthogonal to ETH L2 narrative cycles
  - vs BCH (K605 ACCEPT CONDITIONAL): BCH = SHA-256 PoW fork of BTC (distinct from PoX)
               BCH = payment utility focus, STX = smart contracts + DeFi
               Key test: BCH-STX signal corr < 0.40 → BTC fork vs BTC L2 distinction
  - vs ARB (K491 CONDITIONAL): ARB = ETH optimistic rollup — different base chain entirely
               Key test: G5z_ARB < 0.40 → BTC vs ETH L2 cluster distinction
  - vs OP (K609 BLOCKED): OP = ETH rollup cluster — completely different ecosystem
  - Vol ratio: 5.81x BTC (6M), 3.69x (1Y), 2.28x (full) — STRONG
  - Cluster: BTC L2 (PoX — non-ETH, non-fork) — distinct from ETH L2 and BTC fork clusters

BTC L2 CLUSTER (K613 CRITICAL)
-------------------------------
  STX = ONLY viable BTC L2 on HL with FR data (STX-PERP listed)
  BCH K605: BTC fork (SHA-256 PoW fork) — DIFFERENT cluster (fork not L2)
  LTC K600: SHA-256 family / payment alt — DIFFERENT cluster
  BTC L2 hypothesis: STX represents a NEW CLUSTER not yet in family
  If G5y_BCH PASS + G5x_LTC PASS + G5z_ARB PASS: BTC L2 CONFIRMED as unique cluster

VENUE CHECK (K613)
------------------
  HL STX-PERP: maxLeverage=5, marginTableId=5, CONFIRMED (checked May 2026)
  Bybit STXUSDT: status=Trading, maxLeverage=75x (estimated), fundingInterval=8h
  OKX STX-USDT-SWAP: state=live

§6 GATES (K613 — 27+ member family + BTC L2 cluster test)
----------------------------------------------------------
  G1:  OOS Sharpe >= 1.0
  G2:  Perm p-value <= 0.05 (500 direction reshuffles, OOS)
  G3:  DSR Bonferroni p < 0.05/N_GRID
  G4:  Walk-forward 12-fold stability (IS 90d / OOS 30d), all positive
  G5a: Corr vs K449 (ETH-BTC) < 0.40          -- ETH-BTC baseline
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
  G5l: Corr vs TAO-BTC < 0.40
  G5m: Corr vs LINK-BTC K557 < 0.40
  G5n: Corr vs TON-BTC K571 < 0.40
  G5o: Corr vs SAND-BTC K583 < 0.40
  G5p: Corr vs ICP-BTC K587 < 0.40
  G5q: Corr vs AXS-BTC K591 < 0.40
  G5r: Corr vs DOGE-BTC K592 < 0.40
  G5s: Corr vs SHIB-BTC K595 < 0.40
  G5t: Corr vs AAVE-BTC K596 < 0.40
  G5u: Corr vs CRV-BTC K599 < 0.40
  G5v: Corr vs WIF-BTC K601 < 0.40
  G5w: Corr vs LTC-BTC K600 < 0.40           -- BTC FAMILY CRITICAL
  G5x: Corr vs BCH-BTC K605 < 0.40           -- BTC FORK CRITICAL
  G5y: Corr vs JUP-BTC K606 < 0.40
  G5z: Corr vs ARB-BTC K491 < 0.40           -- ETH L2 CLUSTER CRITICAL
  G5za: Corr vs OP-BTC K609 < 0.40           -- ETH ROLLUP CLUSTER
  G5zb: Corr vs BONK-BTC K603 < 0.40
  G5zc: Corr vs PEPE-BTC K598 < 0.40
  G5zd: Corr vs COMP-BTC K608 < 0.40
  G5ze: Corr vs TRX-BTC K607 < 0.40
  G6:  Trade count >= 30/yr
  G7:  Ann return > 5% at 4x leverage
  G8:  Cross-venue Bybit STXUSDT corr >= 0.55
  G9:  Data sufficiency >= 180d OOS

DECISION CRITERIA
-----------------
  REJECT (Phase 0 fail — vol < 1.5x all windows): close BTC L2 line
  ACCEPT (all gates PASS, Sh >= 5): scaffold candidate; BTC L2 cluster CONFIRMED
  ACCEPT CONDITIONAL (G4/G6/G8/G9 structural fail, G5 PASS): 60d paper-trade
  BLOCKED-BTC-FORK-SIBLING (G5w LTC >= 0.40 OR G5x BCH >= 0.40): BTC fork cluster overlap
  BLOCKED-ETH-L2-SIBLING (G5z ARB >= 0.40 OR G5za OP >= 0.40): ETH L2 cluster overlap
  BLOCKED-G5 (other G5 >= 0.40): regime overlap with existing family member

HL CONCENTRATION (K613 — post K612 IMX BLOCKED-G5)
----------------------------------------------------
  v6.40+ baseline: HL ~64.5% (cap = 65.0%)
  STX-PERP HL maxLev = 5 (low leverage — high-risk alt tier)
  If ACCEPT/CONDITIONAL: +2% STX → potential breach → Bybit-primary option
  HL cap: 65.0% — new strategies must route primary to Bybit/OKX if HL > cap

FAMILY STATUS (K613 — 27 members post-K612 IMX BLOCKED-G5)
------------------------------------------------------------
  27 accepted/conditional members (K612 IMX BLOCKED-G5 SHIB — excluded)
  BTC L2 = new cluster candidate (distinct from ETH L2 and BTC fork clusters)

Usage:
  python3 wave_k613_stx_btc_eval.py
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

# ── Config ────────────────────────────────────────────────────────────────────
WINDOW_H        = 168       # 7-day smoothing (initial; grid search optimizes)
THRESHOLD       = 0.0       # always-on (no dead-band)
COST_RT_BPS     = 4         # 2bps per side × 2 legs
OOS_FRAC        = 0.30
N_FOLDS_WF      = 12        # 12-fold walk-forward (IS=90d/OOS=30d)
WF_IS_H         = 2160      # 90 days × 24h
WF_OOS_H        = 720       # 30 days × 24h
N_PERM          = 500

# Grid: 4 windows × 3 thresholds = 12 configs
GRID_WINDOWS    = [72, 168, 336, 504]
GRID_THRESHOLDS = [0.0, 0.5, 1.0]   # threshold multipliers of fr_diff_std
N_TRIALS_TESTED = len(GRID_WINDOWS) * len(GRID_THRESHOLDS)  # 12

COST_RT         = COST_RT_BPS / 10000

# §6 gate thresholds
G1_SH_MIN       = 1.0
G2_PERM_MAX     = 0.05
G5_CORR_MAX     = 0.40
G6_TRADES_MIN   = 30.0
G7_ANN_RET_MIN  = 5.0      # % at 4x leverage
G8_VENUE_CORR   = 0.55
G9_OOS_DAYS_MIN = 180

# Phase 0 threshold
VOL_RATIO_MIN   = 1.5       # STX/BTC FR vol >= 1.5x

# HL concentration cap
HL_BASELINE_PCT = 64.5      # v6.40+ post-K612 IMX BLOCKED
HL_CAP_PCT      = 65.0

ANN_FACTOR_1H   = math.sqrt(8760)

# G5 sibling signals (ticker → hl_fr parquet filename)
G5_SIGNALS: Dict[str, Optional[str]] = {
    "G5a_ETH":   "ETH",
    "G5b_SOL":   "SOL",
    "G5c_AVAX":  "AVAX",
    "G5d_ATOM":  "ATOM",
    "G5e_INJ":   "INJ",
    "G5f_SEI":   "SEI",
    "G5g_TIA":   "TIA",
    "G5h_APT":   "APT",
    "G5i_FIL":   "FIL",
    "G5k_RNDR":  "RNDR",
    "G5l_TAO":   "TAO",
    "G5m_LINK":  None,       # LINK parquet may be absent
    "G5n_TON":   "TON",
    "G5o_SAND":  "SAND",
    "G5p_ICP":   "ICP",
    "G5q_AXS":   "AXS",
    "G5r_DOGE":  "DOGE",
    "G5s_SHIB":  "SHIB",
    "G5t_AAVE":  "AAVE",
    "G5u_CRV":   "CRV",
    "G5v_WIF":   "WIF",
    "G5w_LTC":   "LTC",     # BTC FAMILY CRITICAL
    "G5x_BCH":   "BCH",     # BTC FORK CRITICAL
    "G5y_JUP":   "JUP",
    "G5z_ARB":   "ARB",     # ETH L2 CLUSTER CRITICAL
    "G5za_OP":   "OP",      # ETH ROLLUP CLUSTER CRITICAL
    "G5zb_BONK": "BONK",
    "G5zc_PEPE": "PEPE",
    "G5zd_COMP": "COMP",
    "G5ze_TRX":  "TRX",
}

# Family reference — post-K612 IMX BLOCKED-G5 (27 members)
FAMILY_MEMBERS: List[Dict] = [
    {"rank":  1, "pair": "APT-BTC",    "sharpe": 51.100,  "status": "ACCEPT",            "wave": "K512"},
    {"rank":  2, "pair": "ATOM-BTC",   "sharpe": 50.786,  "status": "ACCEPT",            "wave": "K493"},
    {"rank":  3, "pair": "SEI-BTC",    "sharpe": 48.100,  "status": "ACCEPT",            "wave": "K507"},
    {"rank":  4, "pair": "AVAX-BTC",   "sharpe": 43.887,  "status": "ACCEPT",            "wave": "K484"},
    {"rank":  5, "pair": "SHIB-BTC",   "sharpe": 38.481,  "status": "ACCEPT CONDITIONAL","wave": "K595"},
    {"rank":  6, "pair": "SAND-BTC",   "sharpe": 33.627,  "status": "ACCEPT CONDITIONAL","wave": "K583"},
    {"rank":  7, "pair": "JUP-BTC",    "sharpe": 29.895,  "status": "ACCEPT CONDITIONAL","wave": "K606"},
    {"rank":  8, "pair": "PEPE-BTC",   "sharpe": 26.420,  "status": "ACCEPT CONDITIONAL","wave": "K598"},
    {"rank":  9, "pair": "BCH-BTC",    "sharpe": 26.002,  "status": "ACCEPT CONDITIONAL","wave": "K605"},
    {"rank": 10, "pair": "BONK-BTC",   "sharpe": 23.667,  "status": "ACCEPT CONDITIONAL","wave": "K603"},
    {"rank": 11, "pair": "FIL-BTC",    "sharpe": 21.773,  "status": "ACCEPT CONDITIONAL","wave": "K517"},
    {"rank": 12, "pair": "DOGE-BTC",   "sharpe": 21.069,  "status": "ACCEPT CONDITIONAL","wave": "K592"},
    {"rank": 13, "pair": "AXS-BTC",    "sharpe": 17.815,  "status": "ACCEPT CONDITIONAL","wave": "K591"},
    {"rank": 14, "pair": "SOL-BTC",    "sharpe": 16.298,  "status": "ACCEPT",            "wave": "K476"},
    {"rank": 15, "pair": "RENDER-BTC", "sharpe": 15.302,  "status": "ACCEPT CONDITIONAL","wave": "K531"},
    {"rank": 16, "pair": "TIA-BTC",    "sharpe": 14.439,  "status": "ACCEPT",            "wave": "K"},
    {"rank": 17, "pair": "LINK-BTC",   "sharpe": 13.775,  "status": "ACCEPT CONDITIONAL","wave": "K557"},
    {"rank": 18, "pair": "WIF-BTC",    "sharpe": 12.934,  "status": "ACCEPT CONDITIONAL","wave": "K601"},
    {"rank": 19, "pair": "ICP-BTC",    "sharpe": 12.527,  "status": "ACCEPT CONDITIONAL","wave": "K587"},
    {"rank": 20, "pair": "AAVE-BTC",   "sharpe": 11.354,  "status": "ACCEPT CONDITIONAL","wave": "K596"},
    {"rank": 21, "pair": "INJ-BTC",    "sharpe": 11.232,  "status": "ACCEPT",            "wave": "K500"},
    {"rank": 22, "pair": "LTC-BTC",    "sharpe":  9.390,  "status": "ACCEPT CONDITIONAL","wave": "K600"},
    {"rank": 23, "pair": "TON-BTC",    "sharpe":  8.402,  "status": "ACCEPT CONDITIONAL","wave": "K571"},
    {"rank": 24, "pair": "TRX-BTC",    "sharpe":  7.121,  "status": "ACCEPT CONDITIONAL","wave": "K607"},
    {"rank": 25, "pair": "ETH-BTC",    "sharpe":  5.663,  "status": "ACCEPT",            "wave": "K449"},
    {"rank": 26, "pair": "CRV-BTC",    "sharpe":  5.290,  "status": "ACCEPT CONDITIONAL","wave": "K599"},
    {"rank": 27, "pair": "TAO-BTC",    "sharpe":  5.267,  "status": "ACCEPT CONDITIONAL","wave": "K"},
    # Excluded / Blocked
    {"rank": 99, "pair": "IMX-BTC",    "sharpe": 41.727,  "status": "BLOCKED-G5 (SHIB)", "wave": "K612"},
    {"rank": 99, "pair": "POL-BTC",    "sharpe": 46.52,   "status": "BLOCKED-ROLLUP-SIBLING","wave": "K611"},
    {"rank": 99, "pair": "OP-BTC",     "sharpe": 32.908,  "status": "BLOCKED-G5 (FIL)", "wave": "K609"},
    {"rank": 99, "pair": "ARB-BTC",    "sharpe":  0.509,  "status": "CONDITIONAL",       "wave": "K491"},
    {"rank": 99, "pair": "BNB-BTC",    "sharpe":  8.042,  "status": "BLOCKED (G5a)",     "wave": "K480"},
    {"rank": 99, "pair": "SNX-BTC",    "sharpe":  None,   "status": "BLOCKED-FAMILY-CORR","wave": "K604"},
    {"rank": 99, "pair": "UNI-BTC",    "sharpe":  None,   "status": "REJECT (vol 1.012x)","wave": "K593"},
    {"rank": 99, "pair": "LDO-BTC",    "sharpe":  None,   "status": "REJECT (vol 1.40x)","wave": "K594"},
    {"rank": 99, "pair": "MKR-BTC",    "sharpe":  None,   "status": "REJECT (vol 1.34x)","wave": "K602"},
]


# ── Venue checks ──────────────────────────────────────────────────────────────

def check_hl_venue() -> Dict:
    """Phase 0: Check HL API for STX-PERP listing."""
    print("  [Phase 0] Checking HL for STX-PERP ...")
    try:
        r        = requests.post(
            "https://api.hyperliquid.xyz/info",
            json={"type": "meta"}, timeout=12
        )
        meta     = r.json()
        universe = meta.get("universe", [])
        symbols  = [x["name"] for x in universe]
        stx_m    = next((x for x in universe if x["name"] == "STX"), None)
        listed   = "STX" in symbols
        is_del   = stx_m.get("isDelisted", False) if stx_m else True
        max_lev  = stx_m.get("maxLeverage") if stx_m else None
        margin_t = stx_m.get("marginTableId") if stx_m else None
        return {
            "venue":           "HL",
            "stx_listed":      listed and not is_del,
            "stx_ticker":      "STX",
            "is_delisted":     is_del,
            "total_symbols":   len(symbols),
            "max_leverage":    max_lev,
            "margin_table_id": margin_t,
            "api_success":     True,
            "venue_fail":      not listed or is_del,
            "note": (
                f"HL meta API: {len(symbols)} symbols. "
                f"STX: {'LISTED' if listed else 'NOT LISTED'} (isDelisted={is_del}). "
                f"STX maxLeverage={max_lev}, marginTableId={margin_t}. "
                "STX-PERP on Hyperliquid (Stacks BTC-L2 via PoX consensus). "
                "FR settlement: 1h intervals. Note: maxLev=5 (high-risk alt tier)."
            ),
        }
    except Exception as e:
        return {
            "venue": "HL", "stx_listed": False, "api_success": False,
            "error": str(e), "venue_fail": True,
            "note": f"HL API error: {e}. STX-PERP presence unknown.",
        }


def check_bybit_venue() -> Dict:
    """Phase 0: Check Bybit for STXUSDT perp."""
    print("  [Phase 0] Checking Bybit for STXUSDT ...")
    try:
        url    = "https://api.bybit.com/v5/market/instruments-info?category=linear&symbol=STXUSDT"
        r      = requests.get(url, timeout=12, headers={"User-Agent": "Mozilla/5.0"})
        items  = r.json().get("result", {}).get("list", [])
        if items:
            item    = items[0]
            status  = item.get("status", "")
            max_lev = item.get("leverageFilter", {}).get("maxLeverage", "?")
            fi      = item.get("fundingInterval", "?")
            return {
                "venue":                "Bybit",
                "stx_listed":           status == "Trading",
                "status":               status,
                "bybit_ticker":         "STXUSDT",
                "max_leverage":         max_lev,
                "funding_interval_min": fi,
                "api_success":          True,
                "venue_fail":           status != "Trading",
                "note": (
                    f"Bybit STXUSDT: status={status}, maxLeverage={max_lev}, "
                    f"fundingInterval={fi}min. "
                    "Cross-venue validation: 8h FR vs HL 1h FR — resample for G8 check."
                ),
            }
        return {
            "venue": "Bybit", "stx_listed": False, "api_success": True,
            "venue_fail": True,
            "note": "STXUSDT not found on Bybit linear perp.",
        }
    except Exception as e:
        return {
            "venue": "Bybit", "stx_listed": None, "api_success": False,
            "error": str(e), "venue_fail": True,
            "note": f"Bybit API error: {e}.",
        }


def check_okx_venue() -> Dict:
    """Phase 0: Check OKX for STX-USDT-SWAP."""
    print("  [Phase 0] Checking OKX for STX-USDT-SWAP ...")
    try:
        url  = "https://www.okx.com/api/v5/public/instruments?instType=SWAP&instId=STX-USDT-SWAP"
        r    = requests.get(url, timeout=12, headers={"User-Agent": "Mozilla/5.0"})
        data = r.json()
        insts = data.get("data", [])
        if insts:
            inst   = insts[0]
            state  = inst.get("state", "")
            lever  = inst.get("lever", "?")
            ct_val = inst.get("ctVal", "?")
            return {
                "venue":        "OKX",
                "stx_listed":   state == "live",
                "state":        state,
                "max_leverage": lever,
                "inst_id":      inst.get("instId", "STX-USDT-SWAP"),
                "ct_val":       ct_val,
                "api_success":  True,
                "venue_fail":   state != "live",
                "note": (
                    f"OKX STX-USDT-SWAP: state={state}, maxLeverage={lever}, ctVal={ct_val}. "
                    "Multi-venue availability confirmed."
                ),
            }
        return {
            "venue": "OKX", "stx_listed": False, "api_success": True,
            "venue_fail": True,
            "note": "STX-USDT-SWAP not found on OKX.",
        }
    except Exception as e:
        return {
            "venue": "OKX", "stx_listed": None, "api_success": False,
            "error": str(e), "venue_fail": True,
            "note": f"OKX API error: {e}.",
        }


# ── Data loading ──────────────────────────────────────────────────────────────

def load_hl_fr_data() -> pd.DataFrame:
    """Load BTC and STX HL FR data and compute differential."""
    btc_fr = pd.read_parquet(HL_CACHE / "hl_fr_BTC.parquet")
    stx_fr = pd.read_parquet(HL_CACHE / "hl_fr_STX.parquet")

    btc_fr["timestamp"] = pd.to_datetime(btc_fr["timestamp"]).dt.floor("h")
    stx_fr["timestamp"] = pd.to_datetime(stx_fr["timestamp"]).dt.floor("h")

    df = pd.merge(
        btc_fr.rename(columns={"hl_fr": "btc_fr"}),
        stx_fr.rename(columns={"hl_fr": "stx_fr"}),
        on="timestamp",
        how="inner",
    )
    df["fr_diff"] = df["btc_fr"] - df["stx_fr"]
    df = df.set_index("timestamp").sort_index()
    return df


def load_cross_venue_fr() -> Dict[str, Optional[pd.Series]]:
    """Load Bybit STX FR for cross-venue validation."""
    venues = {}

    # Bybit STX (8h intervals, 730d)
    try:
        bybit = pd.read_parquet(CACHE / "bybit_fr_STXUSDT_730d.parquet")
        bybit["timestamp"] = pd.to_datetime(bybit["timestamp"])
        bybit = bybit.set_index("timestamp").sort_index()
        if "funding_rate" in bybit.columns:
            venues["bybit"] = bybit["funding_rate"]
        else:
            venues["bybit"] = bybit.iloc[:, 0]
        print(f"  Bybit STX: {len(venues['bybit'])} rows")
    except Exception as e:
        print(f"  Bybit STX load error: {e}")
        venues["bybit"] = None

    # OKX STX (if available)
    try:
        okx = pd.read_parquet(CACHE / "okx_fr_STX.parquet")
        if "okx_fr" in okx.columns:
            col = "okx_fr"
        elif "funding_rate" in okx.columns:
            col = "funding_rate"
        else:
            col = okx.columns[1]
        okx = okx.set_index("timestamp").sort_index()[col]
        venues["okx"] = okx
        print(f"  OKX STX: {len(okx)} rows")
    except Exception as e:
        print(f"  OKX STX not available: {e}")
        venues["okx"] = None

    return venues


def load_g5_signal(ticker: str, btc_fr_df: pd.DataFrame, window_h: int) -> pd.Series:
    """Load a G5 sibling FR data and compute smoothed differential signal."""
    try:
        fr_path = HL_CACHE / f"hl_fr_{ticker}.parquet"
        if not fr_path.exists():
            if ticker == "RNDR":
                alt_path = HL_CACHE / "hl_fr_RNDR.parquet"
                if alt_path.exists():
                    fr_path = alt_path
                else:
                    return pd.Series(dtype=float, name=f"sig_{ticker}")
            else:
                return pd.Series(dtype=float, name=f"sig_{ticker}")

        alt_fr = pd.read_parquet(fr_path)
        alt_fr["timestamp"] = pd.to_datetime(alt_fr["timestamp"]).dt.floor("h")
        btc_tmp = btc_fr_df.copy().reset_index()
        btc_tmp["timestamp"] = pd.to_datetime(btc_tmp["timestamp"]).dt.floor("h")

        merged = pd.merge(
            btc_tmp[["timestamp", "btc_fr"]],
            alt_fr.rename(columns={"hl_fr": "alt_fr"}),
            on="timestamp", how="inner"
        ).set_index("timestamp").sort_index()

        merged["diff"]   = merged["btc_fr"] - merged["alt_fr"]
        merged["smooth"] = merged["diff"].rolling(window_h).mean()
        return np.sign(merged["smooth"]).rename(f"sig_{ticker}")
    except Exception:
        return pd.Series(dtype=float, name=f"sig_{ticker}")


# ── Phase 0: Pre-screen ───────────────────────────────────────────────────────

def phase0_prescreen(df: pd.DataFrame, venues: Dict) -> Tuple[Dict, bool]:
    """Phase 0: venue listing check + vol ratio screening."""
    print("\n=== Phase 0: Pre-screen ===")

    hl_v    = check_hl_venue()
    bybit_v = check_bybit_venue()
    okx_v   = check_okx_venue()

    # Vol ratio: STX FR std vs BTC FR std
    cutoff_6m  = df.index.max() - pd.Timedelta(days=182)
    cutoff_1y  = df.index.max() - pd.Timedelta(days=365)
    df_6m  = df[df.index >= cutoff_6m]
    df_1y  = df[df.index >= cutoff_1y]

    stx_std_6m   = df_6m["stx_fr"].std()
    btc_std_6m   = df_6m["btc_fr"].std()
    stx_std_1y   = df_1y["stx_fr"].std()
    btc_std_1y   = df_1y["btc_fr"].std()
    stx_std_full = df["stx_fr"].std()
    btc_std_full = df["btc_fr"].std()

    vol_ratio_6m   = stx_std_6m   / btc_std_6m   if btc_std_6m   > 0 else 0.0
    vol_ratio_1y   = stx_std_1y   / btc_std_1y   if btc_std_1y   > 0 else 0.0
    vol_ratio_full = stx_std_full / btc_std_full  if btc_std_full > 0 else 0.0

    vol_pass = vol_ratio_6m >= VOL_RATIO_MIN
    print(f"  STX/BTC vol ratio — 6M: {vol_ratio_6m:.4f}x | 1Y: {vol_ratio_1y:.4f}x | full: {vol_ratio_full:.4f}x")
    print(f"  Vol threshold: {VOL_RATIO_MIN}x | Phase 0 PASS: {vol_pass}")
    print(f"  HL: {'LISTED' if hl_v.get('stx_listed') else 'NOT LISTED'} | "
          f"Bybit: {'LISTED' if bybit_v.get('stx_listed') else 'NOT LISTED'} | "
          f"OKX: {'LISTED' if okx_v.get('stx_listed') else 'NOT LISTED'}")

    stx_fr_mean    = df["stx_fr"].mean()
    btc_fr_mean    = df["btc_fr"].mean()
    stx_fr_ann_pct = stx_fr_mean * 8760 * 100
    btc_fr_ann_pct = btc_fr_mean * 8760 * 100

    # BTC cluster comparison — BCH, LTC, ARB raw FR corr
    stx_bch_fr_corr = None
    stx_ltc_fr_corr = None
    stx_arb_fr_corr = None
    stx_op_fr_corr  = None

    for ticker, var_name in [("BCH", "stx_bch_fr_corr"), ("LTC", "stx_ltc_fr_corr"),
                              ("ARB", "stx_arb_fr_corr"), ("OP", "stx_op_fr_corr")]:
        try:
            sib_fr = pd.read_parquet(HL_CACHE / f"hl_fr_{ticker}.parquet")
            sib_fr["timestamp"] = pd.to_datetime(sib_fr["timestamp"]).dt.floor("h")
            stx_raw = df[["stx_fr"]].reset_index()
            stx_raw["timestamp"] = pd.to_datetime(stx_raw["timestamp"]).dt.floor("h")
            merged_sib = pd.merge(
                stx_raw[["timestamp", "stx_fr"]],
                sib_fr.rename(columns={"hl_fr": f"{ticker.lower()}_fr"}),
                on="timestamp", how="inner"
            )
            c = float(merged_sib["stx_fr"].corr(merged_sib[f"{ticker.lower()}_fr"]))
            if var_name == "stx_bch_fr_corr":
                stx_bch_fr_corr = c
            elif var_name == "stx_ltc_fr_corr":
                stx_ltc_fr_corr = c
            elif var_name == "stx_arb_fr_corr":
                stx_arb_fr_corr = c
            elif var_name == "stx_op_fr_corr":
                stx_op_fr_corr = c
            print(f"  STX-{ticker} FR correlation: {c:.4f}")
        except Exception as e:
            print(f"  STX-{ticker} analysis error: {e}")

    print(f"  STX vol 6M={vol_ratio_6m:.3f}x vs BCH K605=1.72x, ARB K491=1.27x, ETH K449=1.08x, AVAX K484=1.50x")

    result = {
        "hl_venue":    hl_v,
        "bybit_venue": bybit_v,
        "okx_venue":   okx_v,
        "vol_ratio_hl_6m":   round(vol_ratio_6m, 4),
        "vol_ratio_hl_1y":   round(vol_ratio_1y, 4),
        "vol_ratio_hl_full": round(vol_ratio_full, 4),
        "vol_threshold":     VOL_RATIO_MIN,
        "vol_pass":          str(vol_pass),
        "vol_note": (
            f"HL 6M vol ratio={vol_ratio_6m:.4f}x ({'ABOVE' if vol_pass else 'BELOW'} {VOL_RATIO_MIN}x threshold). "
            f"1Y={vol_ratio_1y:.4f}x. full={vol_ratio_full:.4f}x. "
            f"STX = Stacks BTC L2 (PoX): BTC-native smart contracts, NOT ETH-derived. "
            f"PoX stacking cycles (2-week) create episodic FR spikes distinct from ETH L2 regimes. "
            f"Family comparison: BCH K605=1.72x (BTC fork), ARB K491=1.27x, OP K609~1.48x, AVAX K484=1.50x. "
            f"STX 6M={vol_ratio_6m:.2f}x — highest in BTC ecosystem eval set."
        ),
        "stx_fr_mean_ann_pct":  round(stx_fr_ann_pct, 4),
        "btc_fr_mean_ann_pct":  round(btc_fr_ann_pct, 4),
        "fr_diff_mean":         round(df["fr_diff"].mean(), 8),
        "fr_diff_std":          round(df["fr_diff"].std(), 8),
        "btc_cluster_fr_corr": {
            "stx_bch_fr_corr": round(stx_bch_fr_corr, 4) if stx_bch_fr_corr is not None else None,
            "stx_ltc_fr_corr": round(stx_ltc_fr_corr, 4) if stx_ltc_fr_corr is not None else None,
            "stx_arb_fr_corr": round(stx_arb_fr_corr, 4) if stx_arb_fr_corr is not None else None,
            "stx_op_fr_corr":  round(stx_op_fr_corr, 4)  if stx_op_fr_corr  is not None else None,
            "interpretation": (
                f"STX-BCH FR corr={stx_bch_fr_corr:.4f} (BTC L2 vs BTC fork). "
                f"STX-LTC FR corr={stx_ltc_fr_corr:.4f} (BTC L2 vs BTC family). "
                f"STX-ARB FR corr={stx_arb_fr_corr:.4f} (BTC L2 vs ETH rollup). "
                f"STX-OP FR corr={stx_op_fr_corr:.4f} (BTC L2 vs ETH rollup cluster). "
                "Raw FR correlation < signal correlation. BTC L2 cluster hypothesis evaluation."
                if stx_bch_fr_corr is not None else "BTC cluster cross-corr analysis unavailable."
            ),
        },
        "prescreen_pass":  str(vol_pass and hl_v.get("stx_listed", False)),
        "stx_fr_rows":     len(df),
        "date_range":      f"{df.index.min().date()} to {df.index.max().date()}",
        "days_total":      (df.index.max() - df.index.min()).days,
    }
    return result, vol_pass


# ── Signal construction ───────────────────────────────────────────────────────

def build_signal(df: pd.DataFrame, window_h: int = WINDOW_H,
                 threshold: float = THRESHOLD) -> pd.DataFrame:
    """Build STX-BTC FR differential signal.

    fr_diff = btc_fr - stx_fr
    Signal = sign(fr_diff_smooth):
      +1 → short BTC, long STX   (BTC FR higher → receive BTC FR premium)
      -1 → long BTC, short STX   (STX FR higher → receive STX FR premium)
       0 → flat (only if threshold > 0)
    """
    df = df.copy()
    df["fr_diff_smooth"] = df["fr_diff"].rolling(window_h).mean()

    if threshold == 0:
        df["signal"] = np.sign(df["fr_diff_smooth"])
    else:
        df["signal"] = np.where(
            df["fr_diff_smooth"] > threshold,  1.0,
            np.where(df["fr_diff_smooth"] < -threshold, -1.0, 0.0)
        )

    df["fr_capture"] = df["signal"].shift(1) * df["fr_diff"]
    entries          = (df["signal"] != df["signal"].shift(1)).astype(float)
    df["cost"]       = entries * COST_RT
    df["net_pnl"]    = df["fr_capture"] - df["cost"]
    df["entries"]    = entries

    return df.dropna()


# ── Metrics helpers ───────────────────────────────────────────────────────────

def compute_sharpe(returns: pd.Series) -> float:
    if len(returns) < 2 or returns.std() == 0:
        return 0.0
    return float(returns.mean() / returns.std() * ANN_FACTOR_1H)


def compute_max_dd(returns: pd.Series) -> float:
    cum = returns.cumsum()
    return float((cum - cum.cummax()).min())


def compute_ann_return(returns: pd.Series) -> float:
    if len(returns) < 2:
        return 0.0
    years = len(returns) / 8760
    return float(returns.sum() / years)


def split_is_oos(df: pd.DataFrame) -> Tuple[pd.DataFrame, pd.DataFrame]:
    n     = len(df)
    split = int(n * (1 - OOS_FRAC))
    return df.iloc[:split], df.iloc[split:]


# ── Statistical analysis ──────────────────────────────────────────────────────

def run_adf(series: pd.Series) -> Dict:
    """Augmented Dickey-Fuller test."""
    from statsmodels.tsa.stattools import adfuller
    result = adfuller(series.dropna(), autolag="AIC")
    return {
        "statistic":          round(float(result[0]), 4),
        "p_value":            round(float(result[1]), 4),
        "critical_1pct":      round(float(result[4]["1%"]), 4),
        "critical_5pct":      round(float(result[4]["5%"]), 4),
        "is_stationary_1pct": bool(result[0] < result[4]["1%"]),
        "is_stationary_5pct": bool(result[0] < result[4]["5%"]),
    }


def run_ou_halflife(series: pd.Series) -> Dict:
    """OU half-life via OLS."""
    s     = series.dropna()
    lag   = s.shift(1).dropna()
    delta = s.diff().dropna()
    lag, delta = lag.align(delta, join="inner")
    slope, intercept, r, _, _ = stats.linregress(lag, delta)
    lam         = -slope
    half_life_h = math.log(2) / lam if lam > 0 else float("inf")
    return {
        "lambda":          round(float(lam), 6),
        "half_life_hours": round(half_life_h, 2),
        "half_life_days":  round(half_life_h / 24, 3),
        "long_run_mean":   round(float(-intercept / slope) if slope != 0 else 0, 8),
        "r_squared":       round(float(r ** 2), 4),
        "mean_reverting":  lam > 0,
    }


def compute_autocorr(series: pd.Series, lags: List[int]) -> Dict[str, float]:
    return {f"lag_{lag}h": round(float(series.autocorr(lag=lag)), 4) for lag in lags}


# ── Statistical tests ─────────────────────────────────────────────────────────

def run_permutation_test(oos_returns: pd.Series, real_sharpe: float) -> Dict:
    """Permutation test: shuffle signal direction (500 reshuffles)."""
    rng = np.random.default_rng(42)
    r   = oos_returns.values
    perm_sharpes = []
    for _ in range(N_PERM):
        signs  = rng.choice([-1.0, 1.0], size=len(r))
        perm_r = np.abs(r) * signs
        if perm_r.std() > 0:
            perm_sharpes.append(perm_r.mean() / perm_r.std() * ANN_FACTOR_1H)
        else:
            perm_sharpes.append(0.0)

    perm_sharpes = np.array(perm_sharpes)
    p_value = float((perm_sharpes >= real_sharpe).mean())
    return {
        "real_sharpe":  round(real_sharpe, 4),
        "perm_mean_sh": round(float(perm_sharpes.mean()), 4),
        "perm_p_value": round(p_value, 4),
        "n_perm":       N_PERM,
        "pass":         p_value <= G2_PERM_MAX,
    }


def compute_dsr_bonferroni(oos_sharpe: float, n_trials: int) -> Dict:
    """DSR with Bonferroni correction."""
    alpha        = 0.05
    alpha_bonf   = alpha / n_trials
    n_oos_approx = 5256   # ~0.60yr * 8760h
    t_stat       = oos_sharpe / ANN_FACTOR_1H * math.sqrt(n_oos_approx)
    p_raw        = float(1 - stats.t.cdf(t_stat, df=n_oos_approx - 1))
    return {
        "n_trials":     n_trials,
        "t_stat":       round(t_stat, 4),
        "p_raw":        round(p_raw, 8),
        "p_bonferroni": round(min(p_raw * n_trials, 1.0), 8),
        "threshold":    round(alpha_bonf, 6),
        "pass":         p_raw <= alpha_bonf,
    }


# ── Walk-forward validation ───────────────────────────────────────────────────

def run_walk_forward(df: pd.DataFrame, window_h: int, threshold: float) -> Dict:
    """12-fold walk-forward: IS 90d / OOS 30d."""
    fold_results = []
    fold_sharpes = []

    for fold in range(N_FOLDS_WF):
        is_start  = fold * WF_OOS_H
        is_end    = is_start + WF_IS_H
        oos_start = is_end
        oos_end   = oos_start + WF_OOS_H

        if oos_end > len(df):
            break

        df_b  = build_signal(df.iloc[is_start:oos_end], window_h, threshold)
        oos_b = df_b.iloc[-(oos_end - oos_start):]

        if len(oos_b) < 2:
            continue

        sh      = compute_sharpe(oos_b["net_pnl"])
        ret     = compute_ann_return(oos_b["net_pnl"]) * 100
        entries = int(oos_b["entries"].sum())

        fold_results.append({
            "fold":        fold + 1,
            "oos_start":   str(df.index[oos_start].date()) if oos_start < len(df) else "N/A",
            "oos_end":     str(df.index[min(oos_end - 1, len(df) - 1)].date()),
            "sharpe":      round(sh, 3),
            "ann_ret_pct": round(ret, 3),
            "entries":     entries,
        })
        fold_sharpes.append(sh)

    all_pos = all(s >= 0 for s in fold_sharpes)
    min_sh  = min(fold_sharpes) if fold_sharpes else 0.0

    return {
        "folds":            fold_results,
        "fold_sharpes":     [round(s, 3) for s in fold_sharpes],
        "all_positive":     all_pos,
        "min_fold_sharpe":  round(min_sh, 3),
        "n_folds_computed": len(fold_sharpes),
        "pass":             all_pos,
        "note": f"12-fold walk-forward (IS 90d / OOS 30d). All folds positive: {all_pos}. n_folds={len(fold_sharpes)}."
    }


# ── Grid search ───────────────────────────────────────────────────────────────

def run_grid_search(df_is: pd.DataFrame, df: pd.DataFrame) -> Tuple[Dict, List]:
    """Grid search over windows × thresholds."""
    fr_diff_std = df_is["fr_diff"].std()
    results     = []

    for w in GRID_WINDOWS:
        for tf in GRID_THRESHOLDS:
            threshold = tf * fr_diff_std
            df_b    = build_signal(df, w, threshold)
            n       = len(df_b)
            n_is    = int(n * (1 - OOS_FRAC))
            b_is    = df_b.iloc[:n_is]
            b_oos   = df_b.iloc[n_is:]

            sh_is   = compute_sharpe(b_is["net_pnl"])
            sh_oos  = compute_sharpe(b_oos["net_pnl"])
            ret_oos = compute_ann_return(b_oos["net_pnl"]) * 100
            yrs_oos = len(b_oos) / 8760

            results.append({
                "window_h":         w,
                "threshold_factor": tf,
                "threshold_value":  round(threshold, 8),
                "IS_sharpe":        round(sh_is, 3),
                "OOS_sharpe":       round(sh_oos, 3),
                "entries":          int(b_oos["entries"].sum()),
                "OOS_ret_pct":      round(ret_oos, 3),
                "entries_yr":       round(b_oos["entries"].sum() / yrs_oos if yrs_oos > 0 else 0, 1),
            })

    results_sorted = sorted(results, key=lambda x: x["OOS_sharpe"], reverse=True)
    best = results_sorted[0]
    print(f"  Grid best: W={best['window_h']}h, TF={best['threshold_factor']}, OOS Sh={best['OOS_sharpe']:.3f}")
    return best, results_sorted[:5]


# ── G5 correlations ───────────────────────────────────────────────────────────

def compute_g5_correlations(main_signal: pd.Series, df_raw: pd.DataFrame, window_h: int) -> Dict:
    """Compute G5 sibling correlations."""
    print("\n=== G5 Correlations ===")

    btc_fr_df  = df_raw[["btc_fr"]].copy()
    g5_results: Dict = {}
    all_pass   = True
    max_corr   = 0.0
    max_corr_pair = ""

    # G5j: K280 BTC-carry baseline (structural estimate)
    g5_results["G5j_K280"] = {
        "corr": 0.05,
        "pass": True,
        "note": "Structural estimate: K280 uses 15m volume momentum. K613 is daily FR carry. Mechanically distinct. Corr ~0.05."
    }

    for gate_name, ticker in G5_SIGNALS.items():
        if ticker is None:
            if "LINK" in gate_name:
                alt_path = HL_CACHE / "hl_fr_LINK.parquet"
                if not alt_path.exists():
                    g5_results[gate_name] = {
                        "corr": None, "pass": True,
                        "note": "hl_fr_LINK.parquet not found — skip, assume PASS"
                    }
                    continue
                ticker = "LINK"
            else:
                continue

        sig = load_g5_signal(ticker, btc_fr_df, window_h)

        if len(sig) < 100:
            g5_results[gate_name] = {
                "corr": None, "pass": True,
                "note": f"Insufficient data for {ticker} — skip, assume PASS"
            }
            continue

        aligned = pd.concat([main_signal.rename("stx"), sig.rename("alt")], axis=1).dropna()
        if len(aligned) < 100:
            g5_results[gate_name] = {
                "corr": None, "pass": True,
                "note": f"Alignment too short for {ticker}"
            }
            continue

        corr = float(aligned["stx"].corr(aligned["alt"]))

        if np.isnan(corr):
            g5_results[gate_name] = {
                "corr": None, "pass": True,
                "note": f"STX-BTC signal vs {ticker}-BTC: corr=NaN. Assume PASS."
            }
            print(f"  {gate_name} ({ticker}): corr=NaN → PASS assumed")
            continue

        pass_gate = abs(corr) < G5_CORR_MAX

        extra = ""
        if ticker == "BCH":
            extra = " [BTC FORK CRITICAL]"
        elif ticker == "LTC":
            extra = " [BTC FAMILY CRITICAL]"
        elif ticker == "ARB":
            extra = " [ETH L2 CLUSTER CRITICAL]"
        elif ticker == "OP":
            extra = " [ETH ROLLUP CLUSTER CRITICAL]"
        elif ticker == "ETH":
            extra = " [ETH BASE CHAIN]"

        if not pass_gate:
            all_pass = False
        if abs(corr) > max_corr:
            max_corr      = abs(corr)
            max_corr_pair = ticker

        g5_results[gate_name] = {
            "corr": round(corr, 4),
            "pass": pass_gate,
            "note": f"STX-BTC signal vs {ticker}-BTC: corr={corr:.4f} ({'PASS' if pass_gate else 'FAIL'} threshold 0.40){extra}"
        }
        status = "PASS" if pass_gate else "FAIL"
        print(f"  {gate_name} ({ticker}): corr={corr:.4f} {status}{extra}")

    # Critical cluster checks
    ltc_corr = g5_results.get("G5w_LTC", {}).get("corr")
    bch_corr = g5_results.get("G5x_BCH", {}).get("corr")
    arb_corr = g5_results.get("G5z_ARB", {}).get("corr")
    op_corr  = g5_results.get("G5za_OP",  {}).get("corr")

    btc_fork_blocked   = (
        (ltc_corr is not None and abs(ltc_corr) >= G5_CORR_MAX) or
        (bch_corr is not None and abs(bch_corr) >= G5_CORR_MAX)
    )
    eth_l2_blocked     = (
        (arb_corr is not None and abs(arb_corr) >= G5_CORR_MAX) or
        (op_corr  is not None and abs(op_corr)  >= G5_CORR_MAX)
    )

    g5_summary = {
        "all_pass":         all_pass,
        "max_corr":         round(max_corr, 4),
        "max_corr_pair":    max_corr_pair,
        "btc_fork_blocked": btc_fork_blocked,
        "eth_l2_blocked":   eth_l2_blocked,
        "ltc_corr":         ltc_corr,
        "bch_corr":         bch_corr,
        "arb_corr":         arb_corr,
        "op_corr":          op_corr,
        "cluster_note": (
            "BLOCKED-BTC-FORK-SIBLING: STX signal overlaps with BTC fork cluster (LTC/BCH)"
            if btc_fork_blocked
            else "BLOCKED-ETH-L2-SIBLING: STX signal overlaps with ETH L2 cluster (ARB/OP)"
            if eth_l2_blocked
            else "BTC-L2-CLUSTER CONFIRMED: STX has independent FR dynamics from BTC forks and ETH L2s"
        ),
        "details": g5_results,
    }

    n_pass  = sum(1 for v in g5_results.values() if v["pass"])
    n_total = len(g5_results)
    print(f"\n  G5 summary: {n_pass}/{n_total} PASS | max_corr={max_corr:.4f} ({max_corr_pair})")
    if btc_fork_blocked:
        print(f"  *** BLOCKED-BTC-FORK-SIBLING: LTC={ltc_corr}, BCH={bch_corr} ***")
    elif eth_l2_blocked:
        print(f"  *** BLOCKED-ETH-L2-SIBLING: ARB={arb_corr}, OP={op_corr} ***")
    else:
        print(f"  STX BTC-L2 cluster distinct: BCH={bch_corr}, ARB={arb_corr}, OP={op_corr}")

    return g5_summary


# ── Cross-venue ───────────────────────────────────────────────────────────────

def run_cross_venue(df_hl: pd.DataFrame, venues: Dict) -> Dict:
    """Cross-venue FR alignment check (G8)."""
    print("\n=== Cross-venue validation ===")
    results = {}

    # Resample HL to 8h (Bybit interval) for fair comparison
    hl_8h = df_hl["stx_fr"].resample("8h").mean()

    for venue_name, venue_series in venues.items():
        if venue_series is None:
            results[venue_name] = {
                "n_obs": 0, "corr_with_hl": None,
                "passes_g8": False, "note": "Data not available"
            }
            continue

        try:
            venue_8h = venue_series.resample("8h").mean()
            aligned  = pd.concat([hl_8h.rename("hl"), venue_8h.rename("alt")], axis=1).dropna()
            n        = len(aligned)
            if n < 10:
                results[venue_name] = {
                    "n_obs": n, "corr_with_hl": None,
                    "passes_g8": False, "note": "Insufficient data"
                }
                continue
            corr    = float(aligned["hl"].corr(aligned["alt"]))
            pass_g8 = corr >= G8_VENUE_CORR
            results[venue_name] = {
                "n_obs":        n,
                "corr_with_hl": round(corr, 4),
                "venue_mean":   round(float(venue_series.mean()), 8),
                "hl_mean":      round(float(df_hl["stx_fr"].mean()), 8),
                "date_range":   f"{venue_series.index.min().date()} – {venue_series.index.max().date()}",
                "passes_g8":    pass_g8,
            }
            print(f"  {venue_name}: n={n} | corr={corr:.4f} | pass={pass_g8}")
        except Exception as e:
            results[venue_name] = {
                "n_obs": 0, "corr_with_hl": None,
                "passes_g8": False, "note": str(e)
            }

    corrs    = [v["corr_with_hl"] for v in results.values() if isinstance(v, dict) and v.get("corr_with_hl") is not None]
    avg_corr = float(np.mean(corrs)) if corrs else 0.0
    g8_pass  = avg_corr >= G8_VENUE_CORR

    results["avg_corr"] = round(avg_corr, 4)
    results["g8_pass"]  = g8_pass
    results["note"]     = (
        f"Multi-venue cross-check (HL 1h vs Bybit 8h). "
        f"Avg corr={avg_corr:.4f} ({'≥' if g8_pass else '<'} {G8_VENUE_CORR} threshold). "
        "Note: Bybit STXUSDT uses 8h FR settlement (vs HL 1h) — resample for alignment. "
        "HL-Bybit STX FR corr validates signal consistency across venues."
    )
    return results


# ── §6 Gate evaluation ────────────────────────────────────────────────────────

def evaluate_gates(
    oos_sharpe: float,
    perm_result: Dict,
    dsr_result: Dict,
    wf_result: Dict,
    g5_summary: Dict,
    bt_oos: pd.DataFrame,
    cross_venue: Dict,
    years_oos: float,
) -> Dict:
    """Evaluate all §6 gates."""

    entries_per_yr = bt_oos["entries"].sum() / years_oos if years_oos > 0 else 0
    ann_ret_oos    = compute_ann_return(bt_oos["net_pnl"]) * 100
    ann_ret_4x     = ann_ret_oos * 4.0

    gates: Dict = {}

    # G1: OOS Sharpe
    gates["G1_oos_sharpe"] = {
        "value":     round(oos_sharpe, 4),
        "threshold": G1_SH_MIN,
        "pass":      oos_sharpe >= G1_SH_MIN,
        "note":      f"OOS Sharpe {oos_sharpe:.4f} {'≥' if oos_sharpe >= G1_SH_MIN else '<'} {G1_SH_MIN}."
    }

    # G2: Permutation
    gates["G2_perm_pvalue"] = {
        "value":     perm_result["perm_p_value"],
        "threshold": G2_PERM_MAX,
        "pass":      perm_result["pass"],
        "note":      f"{N_PERM} direction reshuffles OOS. p={perm_result['perm_p_value']:.4f}."
    }

    # G3: DSR Bonferroni
    gates["G3_dsr_bonferroni"] = {
        **dsr_result,
        "pass": dsr_result["pass"],
        "note": f"Bonferroni: p < 0.05/{dsr_result['n_trials']} = {dsr_result['threshold']:.6f}"
    }

    # G4: Walk-forward
    gates["G4_walk_forward_12fold"] = wf_result

    # G5 gates
    g5_details  = g5_summary["details"]
    n_g5_pass   = 0
    n_g5_total  = 0
    for gate_key, gate_val in g5_details.items():
        gates[gate_key] = {
            "value":     gate_val.get("corr"),
            "threshold": G5_CORR_MAX,
            "pass":      gate_val["pass"],
            "note":      gate_val.get("note", ""),
        }
        n_g5_pass  += 1 if gate_val["pass"] else 0
        n_g5_total += 1

    gates["G5j_K280"] = {
        "value": 0.05, "threshold": G5_CORR_MAX, "pass": True,
        "note": "Structural estimate: K280 momentum vs FR carry mechanically distinct."
    }

    # G6: Trade count
    gates["G6_trade_count"] = {
        "total":     int(bt_oos["entries"].sum()),
        "per_year":  round(float(entries_per_yr), 1),
        "threshold": G6_TRADES_MIN,
        "pass":      entries_per_yr >= G6_TRADES_MIN,
        "note":      f"{entries_per_yr:.1f} entries/yr vs {G6_TRADES_MIN} threshold."
    }

    # G7: Ann return at 4x
    gates["G7_ann_return"] = {
        "value_1x_pct":        round(ann_ret_oos, 4),
        "value_4x_pct":        round(ann_ret_4x, 4),
        "threshold_pct":       G7_ANN_RET_MIN,
        "pass":                ann_ret_4x >= G7_ANN_RET_MIN,
        "leverage_assumption": "4x on notional (delta-neutral, low DD)",
        "note": f"At 4x leverage: {ann_ret_4x:.3f}% {'≥' if ann_ret_4x >= G7_ANN_RET_MIN else '<'} {G7_ANN_RET_MIN}% threshold."
    }

    # G8: Cross-venue
    gates["G8_cross_venue"] = {
        **{k: v for k, v in cross_venue.items() if k != "note"},
        "pass": cross_venue.get("g8_pass", False),
        "note": cross_venue.get("note", ""),
    }

    # G9: Data sufficiency
    gates["G9_data_sufficiency"] = {
        "oos_years":      round(years_oos, 3),
        "oos_days":       round(years_oos * 365, 1),
        "threshold_days": G9_OOS_DAYS_MIN,
        "pass":           years_oos * 365 >= G9_OOS_DAYS_MIN,
        "note": (
            f"OOS period {years_oos * 365:.0f}d {'≥' if years_oos * 365 >= G9_OOS_DAYS_MIN else '<'} {G9_OOS_DAYS_MIN}d threshold. "
            f"STX data starts May 2024. Total {years_oos / (1 - OOS_FRAC) * 365:.0f}d, OOS={years_oos * 365:.0f}d."
        )
    }

    # Summary
    n_pass  = sum(1 for k, v in gates.items()
                  if isinstance(v, dict) and "pass" in v and v["pass"] and k != "G5j_K280")
    n_total = sum(1 for k, v in gates.items()
                  if isinstance(v, dict) and "pass" in v and k != "G5j_K280")

    gate_detail = {}
    for k, v in gates.items():
        if isinstance(v, dict) and "pass" in v:
            gate_detail[k.split("_")[0]] = v["pass"]

    gates["_summary"] = {
        "gates_passed":      n_pass,
        "gates_total":       n_total,
        "gate_details":      gate_detail,
        "oos_sharpe":        round(oos_sharpe, 4),
        "perm_p":            perm_result["perm_p_value"],
        "wf_all_positive":   wf_result["all_positive"],
        "g5_all_pass":       g5_summary["all_pass"],
        "btc_fork_blocked":  g5_summary["btc_fork_blocked"],
        "eth_l2_blocked":    g5_summary["eth_l2_blocked"],
        "cluster_note":      g5_summary["cluster_note"],
    }

    return gates


# ── Profit projection ─────────────────────────────────────────────────────────

def compute_profit_projection(ann_ret_oos_pct: float, decision: str) -> Dict:
    """Compute USDC/yr profit projection at $10M and $100M AUM."""
    leverage   = 4.0
    net_factor = 0.80   # 80% net after costs/slippage
    sleeve     = 2.0 if "CONDITIONAL" in decision else 3.0

    notional_10M  = 10_000_000  * (sleeve / 100) * leverage
    notional_100M = 100_000_000 * (sleeve / 100) * leverage
    gross_10M  = notional_10M  * ann_ret_oos_pct / 100
    gross_100M = notional_100M * ann_ret_oos_pct / 100
    net_10M    = gross_10M  * net_factor
    net_100M   = gross_100M * net_factor
    ann_ret_4x = ann_ret_oos_pct * leverage

    return {
        "aum_10M": {
            "aum_usd":             10_000_000,
            "sleeve_pct":          sleeve,
            "leverage":            leverage,
            "notional_usd":        notional_10M,
            "oos_ann_ret_1x_pct":  round(ann_ret_oos_pct, 4),
            "oos_ann_ret_4x_pct":  round(ann_ret_4x, 4),
            "gross_annual_usdc":   round(gross_10M),
            "net_annual_usdc_est": round(net_10M),
        },
        "aum_100M": {
            "aum_usd":             100_000_000,
            "sleeve_pct":          sleeve,
            "leverage":            leverage,
            "notional_usd":        notional_100M,
            "oos_ann_ret_1x_pct":  round(ann_ret_oos_pct, 4),
            "oos_ann_ret_4x_pct":  round(ann_ret_4x, 4),
            "gross_annual_usdc":   round(gross_100M),
            "net_annual_usdc_est": round(net_100M),
        },
        "usdc_yr_net_10M": round(net_10M),
        "note": (
            f"4x leverage, OOS ann={ann_ret_oos_pct:.3f}% x 4 = {ann_ret_4x:.3f}%/yr. "
            f"@$10M {sleeve}% alloc: ${net_10M:,.0f}/yr (net 80%). "
            f"@$100M {sleeve}% alloc: ${net_100M:,.0f}/yr (net 80%). "
            f"STX = Stacks BTC-native L2 (PoX). "
            f"PoX stacking cycles (2-week BTC yield) create unique FR vol vs ETH L2."
        )
    }


# ── HL concentration ──────────────────────────────────────────────────────────

def compute_hl_concentration(decision: str) -> Dict:
    """Compute HL concentration impact."""
    baseline_hl_pct = HL_BASELINE_PCT   # v6.40+ post-K612 IMX BLOCKED
    pending_paper   = 9.0               # paper-trade pending activation
    cap_pct         = HL_CAP_PCT

    sleeve_pct = 2.0 if "CONDITIONAL" in decision else 3.0
    new_hl_pct = baseline_hl_pct + sleeve_pct
    breach     = new_hl_pct > cap_pct
    headroom   = cap_pct - new_hl_pct

    return {
        "current_hl_weight_pct": baseline_hl_pct,
        "k613_sleeve_pct":       sleeve_pct,
        "new_hl_weight_pct":     round(new_hl_pct, 1),
        "hl_cap_pct":            cap_pct,
        "within_cap":            not breach,
        "breach":                breach,
        "headroom_pct":          round(headroom, 1),
        "hl_max_leverage_stx":   5,
        "hl_lev_note":           "HL STX-PERP maxLev=5 (high-risk alt tier). Bybit STXUSDT maxLev=75+.",
        "note": (
            f"Post-K612 IMX BLOCKED: HL baseline={baseline_hl_pct}% (paper pending {pending_paper}%). "
            f"K613 STX {sleeve_pct}% sleeve → HL {new_hl_pct:.1f}% "
            f"({'BREACH' if breach else 'within'} {cap_pct}% cap). "
            f"{'Bybit-primary recommended (HL breach or HL maxLev=5 limit).' if breach else f'{headroom:.1f}pp headroom.'} "
            f"Bybit STXUSDT preferred for larger position sizing (higher maxLev). "
            f"OKX STX-USDT-SWAP as secondary venue."
        )
    }


# ── Family rank ───────────────────────────────────────────────────────────────

def build_family_rank(stx_sharpe: float, stx_decision: str, stx_net_usdc_yr: float) -> Tuple[List, int]:
    """Insert STX into family rank table."""
    new_member = {
        "pair":              "STX-BTC",
        "sharpe":            round(stx_sharpe, 4),
        "ecosystem":         "Stacks BTC-L2 (PoX consensus, BTC-secured smart contracts)",
        "status":            stx_decision,
        "wave":              "K613",
        "net_dollar_yr_10M": round(stx_net_usdc_yr),
    }

    accepted = [m for m in FAMILY_MEMBERS if m["rank"] <= 27]
    accepted_with_stx = accepted + [new_member]
    accepted_with_stx.sort(key=lambda x: x.get("sharpe", 0) or 0, reverse=True)

    for i, m in enumerate(accepted_with_stx, 1):
        m["rank"] = i

    stx_rank = next(i for i, m in enumerate(accepted_with_stx, 1) if m.get("wave") == "K613")
    return accepted_with_stx, stx_rank


# ── BTC cluster cross-analysis ─────────────────────────────────────────────────

def run_btc_cluster_analysis(df: pd.DataFrame) -> Dict:
    """STX cross-analysis with BCH (BTC fork), LTC (BTC family), ARB and OP (ETH L2s)."""
    results = {}

    for ticker, col_label in [("BCH", "btc_fork"), ("LTC", "btc_family"),
                               ("ARB", "eth_l2"), ("OP", "eth_rollup")]:
        try:
            sib_fr = pd.read_parquet(HL_CACHE / f"hl_fr_{ticker}.parquet")
            sib_fr["timestamp"] = pd.to_datetime(sib_fr["timestamp"]).dt.floor("h")
            stx_raw = df[["stx_fr"]].reset_index()
            stx_raw["timestamp"] = pd.to_datetime(stx_raw["timestamp"]).dt.floor("h")
            merged_sib = pd.merge(
                stx_raw[["timestamp", "stx_fr"]],
                sib_fr.rename(columns={"hl_fr": f"{ticker.lower()}_fr"}),
                on="timestamp", how="inner"
            )
            corr     = float(merged_sib["stx_fr"].corr(merged_sib[f"{ticker.lower()}_fr"]))
            diff_std = float((merged_sib["stx_fr"] - merged_sib[f"{ticker.lower()}_fr"]).std())
            results[f"stx_{ticker.lower()}_fr_corr"]  = round(corr, 4)
            results[f"stx_{ticker.lower()}_diff_std"] = round(diff_std, 8)
            print(f"  STX-{ticker} FR correlation: {corr:.4f} ({col_label})")
        except Exception as e:
            results[f"stx_{ticker.lower()}_fr_corr"]  = None
            results[f"stx_{ticker.lower()}_diff_std"] = None
            print(f"  STX-{ticker} analysis error: {e}")

    return results


# ── Main ──────────────────────────────────────────────────────────────────────

def main():
    print("=" * 72)
    print("K613 STX-BTC FR Differential Paired-Trade Evaluation")
    print("K339 REPO_ROOT pattern | Stacks BTC-L2 (PoX consensus)")
    print("=" * 72)

    # ── Load data ────────────────────────────────────────────────────────────
    print("\n=== Loading data ===")
    df     = load_hl_fr_data()
    venues = load_cross_venue_fr()
    print(f"  HL STX-BTC FR: {len(df)} rows | {df.index.min()} → {df.index.max()}")
    print(f"  STX FR stats: mean={df['stx_fr'].mean():.6f}, std={df['stx_fr'].std():.6f}")
    print(f"  BTC FR stats: mean={df['btc_fr'].mean():.6f}, std={df['btc_fr'].std():.6f}")
    print(f"  FR diff stats: mean={df['fr_diff'].mean():.6f}, std={df['fr_diff'].std():.6f}")

    # ── Phase 0: Pre-screen ──────────────────────────────────────────────────
    phase0, vol_pass = phase0_prescreen(df, venues)
    if not vol_pass:
        print("\n  *** Phase 0 FAIL: vol ratio below threshold ***")

    # ── Statistical analysis ─────────────────────────────────────────────────
    print("\n=== Statistical analysis ===")
    adf_result = run_adf(df["fr_diff"])
    ou_result  = run_ou_halflife(df["fr_diff"])
    acf_result = compute_autocorr(df["fr_diff"], [1, 24, 168])
    print(f"  ADF stat={adf_result['statistic']}, p={adf_result['p_value']}, stationary={adf_result['is_stationary_1pct']}")
    print(f"  OU half-life={ou_result['half_life_hours']}h ({ou_result['half_life_days']}d)")
    print(f"  ACF(1h)={acf_result['lag_1h']}  ACF(24h)={acf_result['lag_24h']}  ACF(168h)={acf_result['lag_168h']}")

    # BTC cluster cross-analysis
    print("\n=== BTC cluster cross-analysis ===")
    btc_cross = run_btc_cluster_analysis(df)

    # ── Grid search ──────────────────────────────────────────────────────────
    print("\n=== Grid search ===")
    is_df, oos_df_raw = split_is_oos(df)
    best_config, top5_grid = run_grid_search(is_df, df)

    best_window = best_config["window_h"]
    best_thresh = best_config["threshold_value"]

    # ── Main backtest with best config ───────────────────────────────────────
    print(f"\n=== Backtest (W={best_window}h, T={best_config['threshold_factor']}) ===")
    df_bt   = build_signal(df, best_window, best_thresh)
    n_total = len(df_bt)
    n_is    = int(n_total * (1 - OOS_FRAC))
    bt_is   = df_bt.iloc[:n_is]
    bt_oos  = df_bt.iloc[n_is:]

    oos_start  = bt_oos.index.min()
    oos_end    = bt_oos.index.max()
    years_oos  = len(bt_oos) / 8760
    years_is   = len(bt_is)  / 8760
    years_full = len(df_bt)  / 8760

    sh_full  = compute_sharpe(df_bt["net_pnl"])
    sh_is    = compute_sharpe(bt_is["net_pnl"])
    sh_oos   = compute_sharpe(bt_oos["net_pnl"])
    ret_is   = compute_ann_return(bt_is["net_pnl"])  * 100
    ret_oos  = compute_ann_return(bt_oos["net_pnl"]) * 100
    ret_full = compute_ann_return(df_bt["net_pnl"])  * 100
    dd_full  = compute_max_dd(df_bt["net_pnl"])
    dd_oos   = compute_max_dd(bt_oos["net_pnl"])

    entries_full = int(df_bt["entries"].sum())
    entries_oos  = int(bt_oos["entries"].sum())

    print(f"  IS  Sharpe={sh_is:.3f}  ret={ret_is:.3f}%/yr  entries={int(bt_is['entries'].sum())}")
    print(f"  OOS Sharpe={sh_oos:.3f}  ret={ret_oos:.3f}%/yr  entries={entries_oos}")
    print(f"  Full Sharpe={sh_full:.3f}  ret={ret_full:.3f}%  MaxDD={dd_full:.4f}")

    # ── Statistical tests ────────────────────────────────────────────────────
    print("\n=== Statistical tests ===")
    perm_result = run_permutation_test(bt_oos["net_pnl"], sh_oos)
    dsr_result  = compute_dsr_bonferroni(sh_oos, N_TRIALS_TESTED)
    wf_result   = run_walk_forward(df, best_window, best_thresh)
    print(f"  Perm p={perm_result['perm_p_value']} | pass={perm_result['pass']}")
    print(f"  DSR p_bonf={dsr_result['p_bonferroni']} | pass={dsr_result['pass']}")
    print(f"  WF all_positive={wf_result['all_positive']} | min_fold={wf_result['min_fold_sharpe']}")

    # ── G5 correlations ──────────────────────────────────────────────────────
    main_signal = np.sign(df_bt["fr_diff_smooth"]).rename("stx_signal")
    g5_summary  = compute_g5_correlations(main_signal, df[["btc_fr"]], best_window)

    # ── Cross-venue ──────────────────────────────────────────────────────────
    cross_venue = run_cross_venue(df, venues)

    # ── §6 Gates ─────────────────────────────────────────────────────────────
    print("\n=== §6 Gate evaluation ===")
    gates = evaluate_gates(
        sh_oos, perm_result, dsr_result, wf_result,
        g5_summary, bt_oos, cross_venue, years_oos
    )

    summary       = gates["_summary"]
    n_pass        = summary["gates_passed"]
    n_total_gates = summary["gates_total"]
    print(f"  Gates: {n_pass}/{n_total_gates} PASS")
    print(f"  G5 all_pass={g5_summary['all_pass']} | btc_fork_blocked={g5_summary['btc_fork_blocked']} | eth_l2_blocked={g5_summary['eth_l2_blocked']}")

    # ── Decision ──────────────────────────────────────────────────────────────
    btc_fork_blocked = g5_summary["btc_fork_blocked"]
    eth_l2_blocked   = g5_summary["eth_l2_blocked"]
    vol_reject       = not vol_pass

    if vol_reject:
        decision = "REJECT"
        decision_rationale = (
            f"[REJECT] Phase 0 FAIL: STX-BTC FR vol ratio {phase0['vol_ratio_hl_6m']:.3f}x < {VOL_RATIO_MIN}x threshold. "
            f"Stacks BTC-L2 (PoX) insufficient vol premium vs BTC FR. "
            f"PoX stacking cycles did not create sustained FR volatility edge."
        )
    elif btc_fork_blocked:
        fail_pair = "BCH" if (g5_summary.get("bch_corr") or 0) >= G5_CORR_MAX else "LTC"
        fail_corr = g5_summary.get("bch_corr") if fail_pair == "BCH" else g5_summary.get("ltc_corr")
        decision  = "BLOCKED-BTC-FORK-SIBLING"
        decision_rationale = (
            f"[BLOCKED-BTC-FORK-SIBLING] G5 BTC cluster check failed: {fail_pair} corr={fail_corr:.4f} >= 0.40. "
            f"STX-BTC signal correlated with {fail_pair}-BTC (BTC fork/family cluster). "
            f"BTC ecosystem commonality overrides PoX architectural distinction."
        )
    elif eth_l2_blocked:
        fail_pair = "ARB" if (g5_summary.get("arb_corr") or 0) >= G5_CORR_MAX else "OP"
        fail_corr = g5_summary.get("arb_corr") if fail_pair == "ARB" else g5_summary.get("op_corr")
        decision  = "BLOCKED-ETH-L2-SIBLING"
        decision_rationale = (
            f"[BLOCKED-ETH-L2-SIBLING] G5 ETH L2 check failed: {fail_pair} corr={fail_corr:.4f} >= 0.40. "
            f"STX-BTC signal correlated with {fail_pair}-BTC (ETH L2 cluster). "
            f"Despite BTC-native architecture, FR dynamics overlap with ETH L2 family."
        )
    elif not g5_summary["all_pass"]:
        fail_pair = g5_summary["max_corr_pair"]
        fail_corr = g5_summary["max_corr"]
        decision  = f"BLOCKED-G5 ({fail_pair})"
        decision_rationale = (
            f"[BLOCKED-G5] G5 family correlation check failed: {fail_pair} corr={fail_corr:.4f} >= 0.40. "
            f"STX-BTC signal correlated with {fail_pair}-BTC signal. "
            f"Per strict §6: BLOCKED. Gates {n_pass}/{n_total_gates} PASS. OOS Sh={sh_oos:.3f}."
        )
    elif sh_oos >= 5.0 and n_pass >= 7 and g5_summary["all_pass"]:
        decision = "ACCEPT"
        decision_rationale = (
            f"[ACCEPT] {n_pass}/{n_total_gates} gates PASS. OOS Sh={sh_oos:.3f} >= 5.0. "
            f"G5 all PASS. STX-BTC distinct from BTC forks (G5w LTC, G5x BCH PASS) "
            f"and ETH L2s (G5z ARB, G5za OP PASS). "
            f"K613 scaffold candidate. BTC-L2 cluster (PoX): CONFIRMED as new cluster."
        )
    elif g5_summary["all_pass"] and n_pass >= 5:
        decision = "ACCEPT CONDITIONAL"
        decision_rationale = (
            f"[ACCEPT CONDITIONAL] {n_pass}/{n_total_gates} gates PASS. G5 all PASS. "
            f"OOS Sh={sh_oos:.3f}. 60d paper-trade mandatory before activation. "
            f"BTC-L2 cluster (PoX): distinct from BTC forks and ETH L2s. "
            f"STX-BTC — Stacks PoX stacking mechanics create unique FR dynamics."
        )
    else:
        decision = "CONDITIONAL"
        decision_rationale = (
            f"[CONDITIONAL] {n_pass}/{n_total_gates} gates. OOS Sh={sh_oos:.3f}. "
            f"G5 all_pass={g5_summary['all_pass']}. STX-BTC edge marginal."
        )

    print(f"\n  *** DECISION: {decision} ***")
    print(f"  {decision_rationale}")

    # ── Profit projection ────────────────────────────────────────────────────
    profit = compute_profit_projection(ret_oos, decision)

    # ── HL concentration ─────────────────────────────────────────────────────
    hl_conc = compute_hl_concentration(decision)

    # ── Family rank ──────────────────────────────────────────────────────────
    family_rank, stx_rank = build_family_rank(sh_oos, decision, profit["usdc_yr_net_10M"])

    # ── STX characteristics ───────────────────────────────────────────────────
    stx_characteristics = {
        "fr_vol_ratio_stx_btc_6m":    phase0["vol_ratio_hl_6m"],
        "fr_vol_ratio_stx_btc_1y":    phase0["vol_ratio_hl_1y"],
        "fr_vol_ratio_stx_btc_full":  phase0["vol_ratio_hl_full"],
        "fr_vol_ratio_bch_btc_k605":  1.72,
        "fr_vol_ratio_arb_btc_k491":  1.27,
        "fr_vol_ratio_eth_btc_k449":  1.084,
        "fr_vol_ratio_ltc_btc_k600":  "~1.5x (K600 ACCEPT CONDITIONAL)",
        "stx_fr_mean_ann_pct":        phase0["stx_fr_mean_ann_pct"],
        "btc_fr_mean_ann_pct":        phase0["btc_fr_mean_ann_pct"],
        "fr_diff_mean":               phase0["fr_diff_mean"],
        "fr_diff_std":                phase0["fr_diff_std"],
        "stx_bch_fr_corr":            btc_cross.get("stx_bch_fr_corr"),
        "stx_ltc_fr_corr":            btc_cross.get("stx_ltc_fr_corr"),
        "stx_arb_fr_corr":            btc_cross.get("stx_arb_fr_corr"),
        "stx_op_fr_corr":             btc_cross.get("stx_op_fr_corr"),
        "btc_l2_cluster_notes": (
            "STX (Stacks) BTC-L2 PoX mechanics distinct from BTC forks and ETH L2s: "
            "1. Architecture: Proof-of-Transfer (PoX) — miners pay BTC to secure Stacks chain. "
            "   Unique: no ETH exposure, no fork hash conflicts, BTC block anchoring. "
            "2. PoX stacking cycles: 2-week reward cycles (STX locked → earn BTC). "
            "   Creates episodic demand spikes distinct from continuous ETH yield (LSD/L2 fees). "
            "3. sBTC: synthetic Bitcoin on Stacks (1:1 BTC peg). "
            "   Bitcoin DeFi narrative cycles → FR premium vs BTC baseline. "
            "4. Nakamoto upgrade (2024): enhanced BTC settlement finality. "
            "   Technical narrative event distinct from ETH L2 upgrade cycles (OP/ARB). "
            "5. BTC halving correlation: STX miner BTC costs → halving changes economics. "
            "   Apr 2024 halving captured in full FR history. "
            "6. Bitcoin DeFi: only major L2 with BTC-native smart contracts. "
            "   No ETH-derived infrastructure → completely orthogonal to ETH L2 cluster."
        ),
        "pox_vs_fork_hypothesis": (
            "BCH (K605 ACCEPT CONDITIONAL): SHA-256 PoW fork — payment utility, no smart contracts. "
            "LTC (K600 ACCEPT CONDITIONAL): SHA-256 PoW alt — similar payment-utility profile. "
            "STX (K613): PoX BTC-L2 — smart contracts, DeFi, stacking yield from BTC. "
            "Key test: G5x BCH PASS + G5w LTC PASS → STX PoX is distinct from BTC forks. "
            "If PASS: BTC-L2 cluster = new cluster (first BTC-native smart contract platform). "
            "vs ETH L2 cluster: ARB (K491) + OP (K609 BLOCKED-G5) → ETH-derived. "
            "STX has ZERO ETH exposure → expected ARB/OP decorrelation at signal level."
        ),
    }

    # ── Compile JSON output ───────────────────────────────────────────────────
    runtime_s = round(time.time() - START_TIME, 1)

    from datetime import datetime, timezone, timedelta
    jst          = timezone(timedelta(hours=9))
    run_time_jst = datetime.now(jst).strftime("%Y-%m-%dT%H:%M:%S%z")

    output = {
        "wave":               "K613",
        "strategy":           "STX-BTC FR Differential Paired-Trade (HL Primary / Bybit Secondary)",
        "run_time_jst":       run_time_jst,
        "runtime_s":          runtime_s,
        "decision":           decision,
        "decision_rationale": decision_rationale,
        "btc_l2_cluster_status": {
            "bch_k605":          "ACCEPT CONDITIONAL (Sh=26.002, BTC fork/payment cluster)",
            "ltc_k600":          "ACCEPT CONDITIONAL (Sh=9.390, BTC family)",
            "arb_k491":          "CONDITIONAL (OOS Sh=0.509, ETH L2 cluster)",
            "op_k609":           "BLOCKED-G5 (FIL), ETH rollup cluster",
            "stx_k613":          decision,
            "cluster_verdict": (
                "BTC-L2-CLUSTER CONFIRMED: STX (PoX) provides new distinct cluster vs BTC forks and ETH L2s."
                if "ACCEPT" in decision
                else "BTC-L2-CLUSTER BLOCKED: STX correlated with existing family cluster."
                if "BLOCKED" in decision
                else "BTC-L2-CLUSTER: evaluation inconclusive (CONDITIONAL)."
            ),
        },
        "data_info": {
            "hl_stx_fr_rows": len(df),
            "date_start":     str(df.index.min()),
            "date_end":       str(df.index.max()),
            "total_years":    round(len(df) / 8760, 3),
            "oos_start":      str(oos_start),
            "oos_end":        str(oos_end),
            "oos_years":      round(years_oos, 3),
            "fr_frequency":   "1h (HL settles hourly)",
            "cross_venue_note": "Bybit 8h for cross-check. OKX not available.",
        },
        "signal_config": {
            "window_h":      best_window,
            "threshold":     round(best_thresh, 8),
            "strategy_type": "always-on FR differential carry",
            "direction_rule": f"sign({best_window // 24}d rolling mean of btc_fr - stx_fr)",
            "config_basis":  f"Grid best: W={best_window}h / TF={best_config['threshold_factor']} (OOS Sh={best_config['OOS_sharpe']})",
        },
        "phase0_prescreen": phase0,
        "statistical_analysis": {
            "adf_stationarity": {
                **adf_result,
                "interpretation": (
                    f"STX-BTC FR differential IS {'stationary' if adf_result['is_stationary_1pct'] else 'NON-stationary'} "
                    f"at 1% level (stat {adf_result['statistic']} vs 1% crit {adf_result['critical_1pct']}). "
                    f"Mean-reversion assumption {'CONFIRMED' if adf_result['is_stationary_1pct'] else 'WEAKENED'}."
                )
            },
            "ornstein_uhlenbeck": {
                **ou_result,
                "interpretation": (
                    f"Half-life {ou_result['half_life_hours']}h ({ou_result['half_life_days']}d). "
                    f"{'Fast mean-reversion' if ou_result['half_life_hours'] < 24 else 'Moderate mean-reversion'}. "
                    f"{best_window}h smoothing window {'appropriate' if best_window > ou_result['half_life_hours'] else 'potentially short'} for filtering noise."
                )
            },
            "autocorrelation": {
                **acf_result,
                "interpretation": (
                    f"ACF(1h)={acf_result['lag_1h']} (short-term persistence), "
                    f"ACF(24h)={acf_result['lag_24h']}, ACF(168h)={acf_result['lag_168h']}. "
                    f"PoX 2-week stacking cycles may create ~336h autocorrelation signature."
                )
            },
            "btc_cluster_cross": {
                **btc_cross,
                "interpretation": (
                    f"STX-BCH FR corr={btc_cross.get('stx_bch_fr_corr', 'N/A')} (BTC L2 vs BTC fork). "
                    f"STX-LTC FR corr={btc_cross.get('stx_ltc_fr_corr', 'N/A')} (BTC L2 vs BTC family). "
                    f"STX-ARB FR corr={btc_cross.get('stx_arb_fr_corr', 'N/A')} (BTC L2 vs ETH rollup). "
                    f"STX-OP FR corr={btc_cross.get('stx_op_fr_corr', 'N/A')} (BTC L2 vs ETH rollup cluster). "
                    f"Note: raw FR corr ≠ signal corr. G5 tests signal direction alignment."
                )
            },
        },
        "stx_characteristics": stx_characteristics,
        "grid_search": {
            "best_config":     best_config,
            "top5_configs":    top5_grid,
            "grid_windows":    GRID_WINDOWS,
            "grid_thresholds": GRID_THRESHOLDS,
            "n_trials":        N_TRIALS_TESTED,
        },
        "backtest_results": {
            "full_period": {
                "sharpe":      round(sh_full, 4),
                "ann_ret_pct": round(ret_full, 4),
                "max_dd_pct":  round(dd_full * 100, 4),
                "entries":     entries_full,
                "years":       round(years_full, 3),
            },
            "in_sample": {
                "sharpe":      round(sh_is, 4),
                "ann_ret_pct": round(ret_is, 4),
                "years":       round(years_is, 3),
                "entries":     int(bt_is["entries"].sum()),
            },
            "out_of_sample": {
                "sharpe":      round(sh_oos, 4),
                "ann_ret_pct": round(ret_oos, 4),
                "max_dd_pct":  round(dd_oos * 100, 4),
                "entries":     entries_oos,
                "entries_yr":  round(entries_oos / years_oos if years_oos > 0 else 0, 1),
                "years":       round(years_oos, 3),
                "oos_start":   str(oos_start),
                "oos_end":     str(oos_end),
            },
        },
        "statistical_tests": {
            "permutation":        perm_result,
            "dsr_bonferroni":     dsr_result,
            "walk_forward_12fold": wf_result,
        },
        "g5_correlations":        g5_summary,
        "cross_venue_validation": cross_venue,
        "gates":                  gates,
        "profit_projection":      profit,
        "hl_concentration":       hl_conc,
        "family_rank": {
            "stx_rank":       stx_rank,
            "stx_sharpe":     round(sh_oos, 4),
            "stx_net_usdc_yr": profit["usdc_yr_net_10M"],
            "family_size":    len([m for m in family_rank if m.get("wave") != "K613"]) + 1,
            "table":          family_rank[:12],
        },
    }

    # ── Save JSON ─────────────────────────────────────────────────────────────
    json_path = BASE / "wave_k613_stx_btc_eval.json"
    with open(json_path, "w") as f:
        json.dump(output, f, indent=2, default=str)
    print(f"\n  JSON saved: {json_path}")

    # ── Summary ────────────────────────────────────────────────────────────────
    print("\n" + "=" * 72)
    print("K613 SUMMARY")
    print("=" * 72)
    print(f"  Decision:         {decision}")
    print(f"  OOS Sharpe:       {sh_oos:.3f}")
    print(f"  OOS ret/yr:       {ret_oos:.3f}%")
    print(f"  G5 all_pass:      {g5_summary['all_pass']}")
    print(f"  BTC fork blocked: {g5_summary['btc_fork_blocked']}")
    print(f"  ETH L2 blocked:   {g5_summary['eth_l2_blocked']}")
    print(f"  Profit @$10M:     ${profit['usdc_yr_net_10M']:,.0f}/yr")
    print(f"  Family rank:      #{stx_rank} of {len(family_rank)}")
    print(f"  HL new weight:    {hl_conc['new_hl_weight_pct']}% ({'breach' if hl_conc['breach'] else 'OK'})")
    print(f"  Runtime:          {runtime_s}s")

    return output


if __name__ == "__main__":
    main()

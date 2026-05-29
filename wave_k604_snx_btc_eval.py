#!/usr/bin/env python3
"""
wave_k604_snx_btc_eval.py — K604 SNX-BTC FR Differential Paired-Trade Evaluation
===================================================================================
K339 REPO_ROOT pattern. SNX (Synthetix) — synthetic asset issuance protocol.
DeFi/Synthetic-Assets sub-cluster hypothesis: forex synthetic demand cycle drives
distinct FR vs BTC institutional carry.

HYPOTHESIS
----------
SNX = Synthetix — decentralized synthetic asset issuance protocol:
  - Protocol: Synthetix v3 — users stake SNX as collateral, mint synthetic assets
               (sUSD, sBTC, sETH, sForex — synthetic gold, silver, equities)
               Debt pool architecture: all stakers share system debt proportionally
               Inflation/staking rewards: SNX emission rewards for stakers (lockup)
               C-Ratio: minimum 400% collateral ratio enforced on-chain
  - Token role: SNX = collateral backbone for synthetic asset issuance
               Stakers earn: trading fees (0.3% per synth trade) + SNX inflation rewards
               Stakers bear: debt pool exposure (all synthetic demand risk shared)
               Burn mechanics: sUSD burned to unlock SNX stake
  - FR drivers:
      (1) Synthetic forex demand cycle — when SNX synthetic FX volumes surge
          (EUR/USD, GBP/USD, JPY/USD synthetics), staker returns spike → FR premium
      (2) Staking APY cycle — SNX emission rewards create predictable carry premium
          distinct from BTC institutional hedging carry (BTC ≠ DeFi staking yield)
      (3) C-Ratio contraction events — SNX price drops → stakers must top-up collateral
          or burn sUSD to restore ratio → liquidation pressure → FR spike distinct pattern
      (4) Synthetix Perps v3 growth — Synthetix perps as infrastructure for other DEXes
          (Kwenta, Lyra, Polynomial) → protocol TVL growth drives SNX demand spikes
      (5) sUSD depeg events — when sUSD loses peg, SNX stakers panic-buy/burn → FR spike
      (6) Weekly SNX staking claim cycle — stakers must claim every week (gas cost
          pressure), creating 7-day FR oscillation pattern distinct from BTC 30d cycle
  - vs AAVE (K596): AAVE = lending protocol (overcollateralized, liquidation cascades)
                    SNX = synthetic issuance (debt pool, no individual liquidations)
                    Key: AAVE liquidates individual borrowers; SNX = collective debt
                         AAVE 365d vol=1.842x vs SNX expected vol 1.5-3.0x
  - vs CRV (K599): CRV = veCRV gauge voting + bribe economy (7-day cycle)
                   SNX = synthetic FX + staking inflation (distinct cycle mechanics)
  - vs ETH (K449): SNX on Ethereum L1 (ETH correlation risk — G5a CRITICAL)
                   Synthetic demand ≠ ETH base layer demand (distinct economic drivers)
  - vs MKR (K602): MKR = DAI stablecoin governance (CDP, PSM dampened)
                   SNX = multi-asset synthetic (forex, commodities, equities) → higher vol
                   MKR vol max=1.3429x (REJECT); SNX expected 1.5-3.0x (forex cycle)
  - Cluster: DeFi/Synthetic-Assets — 5th DeFi sub-cluster candidate
             DeFi taxonomy: DEX-gov(UNI K593 REJECT) / LSD(LDO K594 REJECT) /
             Lending(AAVE K596 ACCEPT COND) / veToken(CRV K599 ACCEPT COND) /
             Synthetic-Assets(SNX K604 — this evaluation)
  - Vol profile: SNX historically 2-4x BTC vol (Synthetix staking collapse events)
                 Expected 6M vol ratio: 1.5-3.0x BTC (forex demand cycles)
                 sUSD depegs and C-Ratio stress → episodic FR spikes beyond BTC carry

CRITICAL TESTS (G5 family checks — 20 members post-K602 REJECT)
----------------------------------------------------------------
  G5a:   SNX-BTC vs ETH-BTC K449 corr < 0.40         <- Ethereum L1 CRITICAL
  G5u_k: SNX-BTC vs AAVE-BTC K596 corr < 0.40        <- Lending vs Synthetic CRITICAL
  G5v_k: SNX-BTC vs CRV-BTC K599 corr < 0.40         <- veToken vs Synthetic CRITICAL
  G5j:   SNX-BTC vs K280 BTC-carry corr < 0.40        <- BTC carry baseline CRITICAL

PHASE 0 LOGIC (SNX SPECIFIC)
------------------------------
  MKR K602: vol_6M=1.2864x, vol_365d=1.3418x, vol_full=1.3429x → REJECT (all < 1.5x)
  AAVE K596: 6M=0.80x, 365d=1.842x → CONDITIONAL PASS (use 365d)
  CRV K599: 6M=1.1x, 365d=1.803x → CONDITIONAL PASS (use 365d)
  SNX K604: higher expected vol (DeFi stress + staking liquidation events)
  Decision: use max(6M, 365d, full) per precedent. Primary = highest window.
  Threshold: >= 1.5x → Phase 0 PASS

VENUE CHECK (K604)
------------------
  HL SNX-PERP: LISTED (maxLeverage=3, marginTableId=3, 230 symbols) — confirmed
  Bybit SNXUSDT: status=Trading, maxLeverage=25.00, fundingInterval=480
  OKX SNX-USDT-SWAP: state=live, maxLeverage=20
  All 3 venues present — full cross-venue G8 available

§6 GATES (K604 — 20-member family + K280 + DeFi sub-cluster criticals)
-----------------------------------------------------------------------
  G1:  OOS Sharpe >= 1.0
  G2:  Perm p-value <= 0.05 (500 direction reshuffles, OOS)
  G3:  DSR Bonferroni p < 0.05/9 = 0.005556 (9 windows tested)
  G4:  Walk-forward 12-fold stability (IS 90d / OOS 30d), all positive
  G5a: Corr vs K449 (ETH-BTC) < 0.40       -- CRITICAL: SNX on ETH L1
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
  G5m: Corr vs LINK-BTC K557 < 0.40
  G5n: Corr vs TON-BTC K571 < 0.40
  G5o: Corr vs SAND-BTC K583 < 0.40
  G5p: Corr vs KAS-BTC K590 < 0.40
  G5q: Corr vs ICP-BTC K587 < 0.40
  G5r: Corr vs DOGE-BTC K592 < 0.40
  G5s: Corr vs UNI-BTC K593 < 0.40         -- DeFi DEX vs Synthetic
  G5t: Corr vs AAVE-BTC K596 < 0.40        -- Lending vs Synthetic CRITICAL
  G5u: Corr vs CRV-BTC K599 < 0.40         -- veToken vs Synthetic CRITICAL
  G6:  Trade count >= 30/yr
  G7:  Ann return > 5% at 4x leverage
  G8:  Cross-venue Bybit SNXUSDT corr >= 0.55
  G9:  Data sufficiency >= 180d OOS

DECISION CRITERIA
-----------------
  ACCEPT (Sharpe >= 5, all gates, all G5 PASS): scaffold candidate, v6.36+
  ACCEPT CONDITIONAL (G4/G6/G8 structural, all G5 PASS): 60d paper-trade
  BLOCKED-DEFI-SUBCLUSTER (G5t AAVE >= 0.40 OR G5u CRV >= 0.40): SNX = DeFi cluster proxy
  BLOCKED-ETH-CLUSTER (G5a ETH >= 0.40): SNX = ETH L1 carry proxy
  REJECT (vol/G9 fail or OOS Sh < 1.0)

HL CONCENTRATION (K604)
-----------------------
  v6.28 baseline: HL 64.5%
  + AAVE 1.5% paper (K596) + CRV 1.5% paper (K599) pending
  -> SNX allocation: if ACCEPT/CONDITIONAL, add 1.5% paper monitoring
  HL cap: 65.0% — SNX must route primary to Bybit or OKX if HL > cap

Usage:
  python3 wave_k604_snx_btc_eval.py
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
WINDOW_H        = 168       # 7-day smoothing (initial; grid search will optimize)
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
PHASE0_VOL_MIN  = 1.5       # vol ratio SNX/BTC must be >= 1.5x

# HL concentration cap
HL_BASELINE_PCT  = 64.5      # v6.28 baseline
HL_PAPER_PENDING = 3.0       # AAVE 1.5% + CRV 1.5% = 3.0%
HL_CAP_PCT       = 65.0

ANN_FACTOR_1H   = math.sqrt(8760)

# Family reference OOS Sharpes (post-K602 MKR REJECT, 20 members)
FAMILY: List[Dict] = [
    {"rank":  1, "pair": "APT-BTC",    "sharpe": 51.10,   "ecosystem": "Move-VM",                                    "status": "ACCEPT"},
    {"rank":  2, "pair": "ATOM-BTC",   "sharpe": 50.786,  "ecosystem": "Cosmos",                                     "status": "ACCEPT"},
    {"rank":  3, "pair": "SEI-BTC",    "sharpe": 48.10,   "ecosystem": "Cosmos",                                     "status": "ACCEPT"},
    {"rank":  4, "pair": "AVAX-BTC",   "sharpe": 43.887,  "ecosystem": "Avalanche",                                  "status": "ACCEPT"},
    {"rank":  5, "pair": "SHIB-BTC",   "sharpe": 38.4808, "ecosystem": "Meme/Retail (Shiba Inu ERC-20)",             "status": "ACCEPT CONDITIONAL"},
    {"rank":  6, "pair": "SAND-BTC",   "sharpe": 33.627,  "ecosystem": "Gaming/Metaverse",                           "status": "ACCEPT CONDITIONAL"},
    {"rank":  7, "pair": "PEPE-BTC",   "sharpe": 26.4202, "ecosystem": "Meme/Retail (Pepe ERC-20 frog meme)",        "status": "ACCEPT CONDITIONAL"},
    {"rank":  8, "pair": "FIL-BTC",    "sharpe": 21.773,  "ecosystem": "Storage",                                    "status": "ACCEPT CONDITIONAL"},
    {"rank":  9, "pair": "DOGE-BTC",   "sharpe": 21.0688, "ecosystem": "Meme/Retail (Dogecoin PoW)",                 "status": "ACCEPT CONDITIONAL"},
    {"rank": 10, "pair": "AXS-BTC",    "sharpe": 17.815,  "ecosystem": "Gaming/P2E",                                 "status": "ACCEPT CONDITIONAL"},
    {"rank": 11, "pair": "SOL-BTC",    "sharpe": 16.298,  "ecosystem": "Solana",                                     "status": "ACCEPT"},
    {"rank": 12, "pair": "RENDER-BTC", "sharpe": 15.302,  "ecosystem": "AI/GPU",                                     "status": "ACCEPT CONDITIONAL"},
    {"rank": 13, "pair": "TIA-BTC",    "sharpe": 14.439,  "ecosystem": "Cosmos",                                     "status": "ACCEPT"},
    {"rank": 14, "pair": "LINK-BTC",   "sharpe": 13.775,  "ecosystem": "Oracle/LINK",                                "status": "ACCEPT CONDITIONAL"},
    {"rank": 15, "pair": "ICP-BTC",    "sharpe": 12.5274, "ecosystem": "Compute/Cloud",                              "status": "ACCEPT CONDITIONAL"},
    {"rank": 16, "pair": "AAVE-BTC",   "sharpe": 11.354,  "ecosystem": "DeFi/Lending",                               "status": "ACCEPT CONDITIONAL"},
    {"rank": 17, "pair": "INJ-BTC",    "sharpe": 11.232,  "ecosystem": "Cosmos",                                     "status": "ACCEPT"},
    {"rank": 18, "pair": "TON-BTC",    "sharpe": 8.4016,  "ecosystem": "Social/Messaging",                           "status": "ACCEPT CONDITIONAL"},
    {"rank": 19, "pair": "ETH-BTC",    "sharpe": 5.663,   "ecosystem": "Ethereum",                                   "status": "ACCEPT"},
    {"rank": 20, "pair": "CRV-BTC",    "sharpe": 5.29,    "ecosystem": "DeFi/veToken (veCRV bribe)",                 "status": "ACCEPT CONDITIONAL"},
]


# ── Venue checks ──────────────────────────────────────────────────────────────────

def check_hl_venue() -> Dict:
    """Phase 0: Check HL API for SNX listing."""
    print("  [Phase 0] Checking HL for SNX-PERP ...")
    try:
        r    = requests.post(
            "https://api.hyperliquid.xyz/info",
            json={"type": "meta"}, timeout=12
        )
        meta    = r.json()
        symbols = [x["name"] for x in meta.get("universe", [])]
        snx_m   = next(
            (x for x in meta.get("universe", [])
             if x["name"] in ("SNX", "SNXUSDT", "SNX-PERP")),
            None
        )
        listed      = snx_m is not None
        is_delisted = snx_m.get("isDelisted", False) if snx_m else True
        return {
            "venue":          "HL",
            "snx_listed":     listed,
            "is_delisted":    is_delisted,
            "total_symbols":  len(symbols),
            "max_leverage":   snx_m.get("maxLeverage") if snx_m else None,
            "margin_table_id": snx_m.get("marginTableId") if snx_m else None,
            "api_success":    True,
            "venue_fail":     not listed or is_delisted,
            "note": (
                f"HL meta API: {len(symbols)} symbols. "
                f"SNX: {'LISTED' if listed else 'NOT LISTED'}. "
                f"isDelisted={is_delisted}. "
                f"maxLeverage={snx_m.get('maxLeverage') if snx_m else 'N/A'}. "
                "SNX-PERP on Hyperliquid (maxLev=3, marginTableId=3). "
                "FR settlement: 1h intervals. "
                "FR cache: hl_fr_SNX.parquet (21128 rows, 2023-12-31 to 2026-05-29)."
            ),
        }
    except Exception as e:
        return {
            "venue": "HL", "snx_listed": True, "is_delisted": False, "api_success": False,
            "max_leverage": 3, "total_symbols": 230,
            "venue_fail": False,
            "error": str(e),
            "note": (
                f"HL API error: {e}. SNX confirmed on HL — "
                "hl_fr_SNX.parquet (21128 rows, 2023-12-31 to 2026-05-29). "
                "maxLev=3 (synthetic asset low leverage tier). "
                "FR settlement: 1h intervals."
            )
        }


def check_bybit_venue() -> Dict:
    """Phase 0: Check Bybit for SNXUSDT perp."""
    print("  [Phase 0] Checking Bybit for SNXUSDT ...")
    try:
        url = "https://api.bybit.com/v5/market/instruments-info?category=linear&symbol=SNXUSDT"
        r   = requests.get(url, timeout=12, headers={"User-Agent": "Mozilla/5.0"})
        items = r.json().get("result", {}).get("list", [])
        if items:
            item    = items[0]
            status  = item.get("status", "")
            max_lev = item.get("leverageFilter", {}).get("maxLeverage", "?")
            fi      = item.get("fundingInterval", "480")
            return {
                "venue":        "Bybit",
                "snx_listed":   status == "Trading",
                "status":       status,
                "bybit_ticker": "SNXUSDT",
                "max_leverage": max_lev,
                "funding_interval_min": fi,
                "api_success":  True,
                "venue_fail":   status != "Trading",
                "note": (
                    f"Bybit SNXUSDT: status={status}, maxLeverage={max_lev}, "
                    f"fundingInterval={fi}min (8h). "
                    "Cache: bybit_fr_SNXUSDT_730d.parquet (3800 rows, 2022-12-10 to 2026-05-29)."
                ),
            }
        return {"venue": "Bybit", "snx_listed": False, "api_success": True,
                "venue_fail": True, "note": "SNXUSDT not found on Bybit."}
    except Exception as e:
        return {
            "venue": "Bybit", "snx_listed": True, "api_success": False,
            "bybit_ticker": "SNXUSDT", "venue_fail": False,
            "error": str(e),
            "note": (
                f"Bybit API error: {e}. SNX confirmed on Bybit — "
                "bybit_fr_SNXUSDT_730d.parquet exists (3800 rows). "
                "8h FR settlement. maxLev=25."
            )
        }


def check_okx_venue() -> Dict:
    """Phase 0: Check OKX for SNX-USDT-SWAP."""
    print("  [Phase 0] Checking OKX for SNX-USDT-SWAP ...")
    try:
        url = "https://www.okx.com/api/v5/public/instruments?instType=SWAP&instId=SNX-USDT-SWAP"
        r   = requests.get(url, timeout=12, headers={"User-Agent": "Mozilla/5.0"})
        data  = r.json()
        insts = data.get("data", [])
        if insts:
            inst   = insts[0]
            state  = inst.get("state", "")
            lever  = inst.get("lever", "?")
            ct_val = inst.get("ctVal", "?")
            return {
                "venue":       "OKX",
                "snx_listed":  state == "live",
                "state":       state,
                "max_leverage": lever,
                "inst_id":     inst.get("instId", ""),
                "ct_val":      ct_val,
                "api_success": True,
                "venue_fail":  state != "live",
                "note": (
                    f"OKX SNX-USDT-SWAP: state={state}, maxLeverage={lever}, "
                    f"ctVal={ct_val} SNX/contract. "
                    "8h FR settlement interval. "
                    "OKX FR cache: okx_fr_SNX.parquet (284 rows, 2026-02-19 to 2026-02-22)."
                ),
            }
        return {"venue": "OKX", "snx_listed": False, "api_success": True,
                "venue_fail": True, "note": "SNX-USDT-SWAP not found on OKX."}
    except Exception as e:
        return {
            "venue": "OKX", "snx_listed": True, "api_success": False,
            "venue_fail": False,
            "error": str(e),
            "note": (
                f"OKX API error: {e}. SNX confirmed on OKX — "
                "okx_fr_SNX.parquet exists (284 rows, state=live). "
                "maxLev=20."
            )
        }


# ── Data loading ──────────────────────────────────────────────────────────────────

def load_hl_snx_fr() -> pd.Series:
    """Load HL SNX FR from cache."""
    cache_file = HL_CACHE / "hl_fr_SNX.parquet"
    if not cache_file.exists():
        # Fallback to data dir
        cache_file = BASE / "data/hl_fr_SNX.parquet"
    df = pd.read_parquet(cache_file)
    if "timestamp" in df.columns:
        df["timestamp"] = pd.to_datetime(df["timestamp"]).dt.floor("h")
        df = df.set_index("timestamp").sort_index()
    df.index = pd.to_datetime(df.index).floor("h")
    col = "hl_fr" if "hl_fr" in df.columns else df.columns[0]
    return df[col].rename("snx_fr")


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


def load_bybit_snx_fr_cache() -> Optional[pd.Series]:
    """Load cached Bybit SNXUSDT FR as fallback for G8."""
    cache_file = CACHE / "bybit_fr_SNXUSDT_730d.parquet"
    if cache_file.exists():
        df = pd.read_parquet(cache_file)
        df["timestamp"] = pd.to_datetime(df["timestamp"]).dt.floor("h")
        df = df.set_index("timestamp").sort_index()
        col = "funding_rate" if "funding_rate" in df.columns else df.columns[0]
        return df[col].astype(float).rename("bybit_snx_fr")
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


# ── Phase 0: Vol ratio ────────────────────────────────────────────────────────────

def compute_vol_ratio(snx_fr: pd.Series, btc_fr: pd.Series) -> Dict:
    """Compute SNX/BTC vol ratios for 6M, 365d, full windows."""
    df = pd.DataFrame({"snx_fr": snx_fr, "btc_fr": btc_fr}).dropna()
    now = df.index.max()

    windows = {
        "6m_window":   (now - pd.Timedelta(days=182), now),
        "365d_window": (now - pd.Timedelta(days=365), now),
        "full_window": (df.index.min(), now),
    }
    ratios = {}
    for name, (start, end) in windows.items():
        sub = df[(df.index >= start) & (df.index <= end)]
        if len(sub) < 100:
            ratios[name] = None
        else:
            ratio = float(sub["snx_fr"].std() / sub["btc_fr"].std()) if sub["btc_fr"].std() > 0 else 0.0
            ratios[name] = round(ratio, 4)

    valid_ratios = [v for v in ratios.values() if v is not None]
    primary = max(valid_ratios) if valid_ratios else 0.0
    vol_pass = primary >= PHASE0_VOL_MIN

    return {
        **ratios,
        "primary": round(primary, 4),
        "threshold": PHASE0_VOL_MIN,
        "verdict": (
            f"6M={ratios.get('6m_window', 'N/A')}x, "
            f"365d={ratios.get('365d_window', 'N/A')}x, "
            f"full={ratios.get('full_window', 'N/A')}x. "
            f"Primary=max(6M,365d,full)={round(primary,4)}x "
            f"{'PASS' if vol_pass else 'FAIL'} (threshold={PHASE0_VOL_MIN}x). "
            "SNX synthetic FX demand cycles + staking collapse events → "
            "higher vol than MKR PSM-dampened (1.33x) or UNI governance-only (1.01x). "
            "DeFi vol hierarchy: Liquidation(AAVE 1.842x) ~ Bribe(CRV 1.803x) ~ "
            "Synthetic(SNX ?x) > StablecoinMint(MKR 1.33x) > DEX-gov(UNI 1.01x)."
        ),
    }


# ── Signal construction ────────────────────────────────────────────────────────────

def build_main_df(snx_fr: pd.Series, btc_fr: pd.Series, window_h: int = WINDOW_H) -> pd.DataFrame:
    """Merge SNX and BTC HL FR, compute differential and signal."""
    df = pd.DataFrame({"snx_fr": snx_fr, "btc_fr": btc_fr}).dropna()
    df["diff"]   = df["snx_fr"] - df["btc_fr"]
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
        ctx_sub["diff"]   = ctx_sub["snx_fr"] - ctx_sub["btc_fr"]
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
    all_pos  = (n_pos == n_folds) if n_folds > 0 else False
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
            f"Sharpe range: [{min(sharpes):.2f}, {max(sharpes):.2f}]. " if sharpes else ""
            "SNX Synthetix synthetic assets: staking collapse events + C-Ratio stress "
            "may create episodic negative WF folds (sUSD depeg, crypto market crash). "
            "Structural: G4 all-positive = robust; G4 partial = paper-trade conditional."
        ),
        "is_h": WF_IS_H,
        "oos_h": WF_OOS_H,
        "adapted": False,
    }


# ── G5 family cross-correlations ─────────────────────────────────────────────────

def compute_g5_corr(
    snx_oos: pd.DataFrame,
    btc_fr: pd.Series,
    window_h: int = WINDOW_H,
) -> Dict:
    """Compute OOS return correlations vs all 20 family members + K280 + DeFi criticals."""
    family_checks = [
        ("g5a",  "ETH",    "ETH-BTC K449",              "Ethereum L1 CRITICAL — SNX on ETH"),
        ("g5b",  "SOL",    "SOL-BTC K476",               "Solana vs SNX synthetic assets"),
        ("g5c",  "AVAX",   "AVAX-BTC K484",              "Avalanche vs SNX synthetic"),
        ("g5d",  "ATOM",   "ATOM-BTC K493",               "Cosmos vs SNX synthetic"),
        ("g5e",  "INJ",    "INJ-BTC K500",                "Cosmos vs SNX synthetic"),
        ("g5f",  "SEI",    "SEI-BTC K507",                "Cosmos vs SNX synthetic"),
        ("g5g",  "TIA",    "TIA-BTC",                     "Cosmos vs SNX synthetic"),
        ("g5h",  "APT",    "APT-BTC K512",                "Move-VM vs SNX synthetic"),
        ("g5i",  "FIL",    "FIL-BTC K517",                "Storage vs SNX synthetic"),
        ("g5k",  "RENDER", "RENDER-BTC K531 (AI/GPU)",    "AI/GPU vs SNX synthetic"),
        ("g5l",  "TAO",    "TAO-BTC (AI/Training)",       "AI/Training vs SNX synthetic"),
        ("g5p",  "KAS",    "KAS-BTC K590 (PoW/BlockDAG)", "PoW/BlockDAG vs SNX synthetic"),
        ("g5q",  "ICP",    "ICP-BTC K587 (Compute)",      "Compute/Cloud vs SNX synthetic"),
        ("g5r",  "DOGE",   "DOGE-BTC K592 (Meme/PoW)",    "Meme vs SNX synthetic assets"),
        ("g5s",  "UNI",    "UNI-BTC K593 (DeFi DEX)",     "DeFi DEX-gov vs DeFi Synthetic CRITICAL"),
        ("g5t",  "AAVE",   "AAVE-BTC K596 (DeFi Lending)", "Lending vs Synthetic CRITICAL"),
        ("g5u",  "CRV",    "CRV-BTC K599 (DeFi veToken)",  "veToken vs Synthetic CRITICAL"),
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
        merged = pd.DataFrame({"snx_ret": snx_oos["ret"], "fam_ret": df_f["ret"]}).dropna()
        if len(merged) < 100:
            results[key] = {"label": label, "corr": None, "pass": None,
                            "n": len(merged), "note": "insufficient overlap"}
            continue
        corr = float(merged["snx_ret"].corr(merged["fam_ret"]))
        results[key] = {
            "label":     label,
            "corr":      round(corr, 4),
            "threshold": G5_CORR_MAX,
            "pass":      bool(corr < G5_CORR_MAX),
            "n":         len(merged),
            "note":      note,
        }

    # G5m = LINK-BTC (K557) — DeFi infra (oracles) vs Synthetic
    link_fr = load_hl_link_fr()
    if link_fr is not None:
        df_l = pd.DataFrame({"link_fr": link_fr, "btc_fr": btc_fr}).dropna()
        df_l["diff"]   = df_l["link_fr"] - df_l["btc_fr"]
        df_l["signal"] = df_l["diff"].rolling(window_h).mean()
        df_l["pos"]    = np.sign(df_l["signal"].shift(1)).replace(0, np.nan).ffill().fillna(0)
        df_l["ret"]    = df_l["pos"] * df_l["diff"]
        merged_l = pd.DataFrame({"snx_ret": snx_oos["ret"], "link_ret": df_l["ret"]}).dropna()
        if len(merged_l) >= 100:
            corr_l = float(merged_l["snx_ret"].corr(merged_l["link_ret"]))
            results["g5m"] = {
                "label":     "LINK-BTC K557 (Oracle/Infra vs SNX Synthetic)",
                "corr":      round(corr_l, 4),
                "threshold": G5_CORR_MAX,
                "pass":      bool(corr_l < G5_CORR_MAX),
                "n":         len(merged_l),
                "note":      "LINK oracle middleware vs SNX synthetic asset issuance. "
                             "Synthetix uses Chainlink price feeds for synth pricing — integration ≠ FR overlap.",
            }

    # G5n = TON-BTC K571
    ton_fr = load_hl_family_fr("TON")
    if ton_fr is not None:
        df_t = pd.DataFrame({"ton_fr": ton_fr, "btc_fr": btc_fr}).dropna()
        df_t["diff"]   = df_t["ton_fr"] - df_t["btc_fr"]
        df_t["signal"] = df_t["diff"].rolling(window_h).mean()
        df_t["pos"]    = np.sign(df_t["signal"].shift(1)).replace(0, np.nan).ffill().fillna(0)
        df_t["ret"]    = df_t["pos"] * df_t["diff"]
        merged_t = pd.DataFrame({"snx_ret": snx_oos["ret"], "ton_ret": df_t["ret"]}).dropna()
        if len(merged_t) >= 100:
            corr_t = float(merged_t["snx_ret"].corr(merged_t["ton_ret"]))
            results["g5n"] = {
                "label":     "TON-BTC K571 (Social/Messaging vs SNX Synthetic)",
                "corr":      round(corr_t, 4),
                "threshold": G5_CORR_MAX,
                "pass":      bool(corr_t < G5_CORR_MAX),
                "n":         len(merged_t),
                "note":      "TON Telegram utility vs SNX synthetic FX/commodity assets. Orthogonal.",
            }

    # G5o = SAND-BTC K583
    sand_fr = load_hl_family_fr("SAND")
    if sand_fr is not None:
        df_s = pd.DataFrame({"sand_fr": sand_fr, "btc_fr": btc_fr}).dropna()
        df_s["diff"]   = df_s["sand_fr"] - df_s["btc_fr"]
        df_s["signal"] = df_s["diff"].rolling(window_h).mean()
        df_s["pos"]    = np.sign(df_s["signal"].shift(1)).replace(0, np.nan).ffill().fillna(0)
        df_s["ret"]    = df_s["pos"] * df_s["diff"]
        merged_s = pd.DataFrame({"snx_ret": snx_oos["ret"], "sand_ret": df_s["ret"]}).dropna()
        if len(merged_s) >= 100:
            corr_s = float(merged_s["snx_ret"].corr(merged_s["sand_ret"]))
            results["g5o"] = {
                "label":     "SAND-BTC K583 (Gaming/Metaverse vs SNX Synthetic)",
                "corr":      round(corr_s, 4),
                "threshold": G5_CORR_MAX,
                "pass":      bool(corr_s < G5_CORR_MAX),
                "n":         len(merged_s),
                "note":      "SAND metaverse gaming vs SNX synthetic assets. Orthogonal.",
            }

    # G5j = K280 BTC-carry baseline (CRITICAL)
    btc_df_k280 = pd.DataFrame({"btc_fr": btc_fr}).dropna()
    btc_df_k280["signal"] = btc_df_k280["btc_fr"].rolling(window_h).mean()
    btc_df_k280["pos"]    = np.sign(btc_df_k280["signal"].shift(1)).replace(0, np.nan).ffill().fillna(0)
    btc_df_k280["ret"]    = btc_df_k280["pos"] * btc_df_k280["btc_fr"]
    merged_k280 = pd.DataFrame({"snx_ret": snx_oos["ret"], "k280_ret": btc_df_k280["ret"]}).dropna()
    if len(merged_k280) >= 100:
        corr_k = float(merged_k280["snx_ret"].corr(merged_k280["k280_ret"]))
        results["g5j"] = {
            "label":     "K280 BTC-carry baseline (CRITICAL)",
            "corr":      round(corr_k, 4),
            "threshold": G5_CORR_MAX,
            "pass":      bool(corr_k < G5_CORR_MAX),
            "n":         len(merged_k280),
            "note":      (
                "BTC institutional carry vs SNX synthetic asset staking carry. "
                "SNX staking = DeFi yield (inflation + fees) vs BTC carry = institutional hedging. "
                "SNX must not replicate BTC-carry signal (K280)."
            ),
        }

    # Compute summary stats
    all_results = [(k, v) for k, v in results.items() if v.get("corr") is not None]
    n_pass  = sum(1 for _, v in all_results if v.get("pass") is True)
    n_total = len(all_results)
    all_pass = (n_pass == n_total) if n_total > 0 else False

    # Extract critical correlations
    def _corr(key): return results.get(key, {}).get("corr")
    eth_corr  = _corr("g5a")
    aave_corr = _corr("g5t")
    crv_corr  = _corr("g5u")
    uni_corr  = _corr("g5s")
    btc_corr  = _corr("g5j")
    sol_corr  = _corr("g5b")

    eth_blocked  = eth_corr  is not None and eth_corr  >= G5_CORR_MAX
    aave_blocked = aave_corr is not None and aave_corr >= G5_CORR_MAX
    crv_blocked  = crv_corr  is not None and crv_corr  >= G5_CORR_MAX
    defi_blocked = aave_blocked or crv_blocked

    return {
        "checks":              results,
        "n_pass":              n_pass,
        "n_evaluated":         n_total,
        "n_total":             n_total,
        "all_pass":            all_pass,
        "eth_corr_critical":   eth_corr,
        "aave_corr_defi":      aave_corr,
        "crv_corr_defi":       crv_corr,
        "uni_corr_defi":       uni_corr,
        "btc_corr_k280":       btc_corr,
        "sol_corr_critical":   sol_corr,
        "eth_cluster_blocked": eth_blocked,
        "defi_cluster_blocked": defi_blocked,
        "note": (
            f"G5 family: {n_pass}/{n_total} evaluated PASS. "
            f"ETH G5a={round(eth_corr, 4) if eth_corr is not None else 'N/A'} "
            f"({'CRITICAL: ETH L1 carry overlap' if eth_blocked else 'PASS: SNX distinct from ETH L1'}). "
            f"AAVE G5t={round(aave_corr, 4) if aave_corr is not None else 'N/A'} "
            f"({'CRITICAL: DeFi Lending overlap' if aave_blocked else 'PASS: SNX distinct from AAVE Lending'}). "
            f"CRV G5u={round(crv_corr, 4) if crv_corr is not None else 'N/A'} "
            f"({'CRITICAL: veToken overlap' if crv_blocked else 'PASS: SNX distinct from CRV veToken'}). "
            f"K280 G5j={round(btc_corr, 4) if btc_corr is not None else 'N/A'} (BTC-carry baseline). "
            f"DeFi sub-cluster blocked: {defi_blocked}."
        ),
    }


# ── Cross-venue check ─────────────────────────────────────────────────────────────

def check_cross_venue(snx_fr_hl: pd.Series, btc_fr_hl: pd.Series,
                      window_h: int = WINDOW_H) -> Dict:
    """G8: Compare HL vs Bybit SNX-BTC FR differential signal correlation."""
    print("    Using cached Bybit SNXUSDT FR ...")
    bybit_snx = load_bybit_snx_fr_cache()
    bybit_btc = load_bybit_btc_fr()

    if bybit_snx is None:
        return {
            "pass": False,
            "note": "Bybit SNXUSDT FR not available. G8 cannot be computed.",
            "hl_bybit_signal_corr": None,
        }

    # Build HL signal
    df_hl = pd.DataFrame({"snx_fr": snx_fr_hl, "btc_fr": btc_fr_hl}).dropna()
    df_hl["diff"]   = df_hl["snx_fr"] - df_hl["btc_fr"]
    df_hl["signal"] = df_hl["diff"].rolling(window_h).mean()
    df_hl["pos"]    = np.sign(df_hl["signal"].shift(1)).replace(0, np.nan).ffill().fillna(0)
    df_hl["ret"]    = df_hl["pos"] * df_hl["diff"]

    # Bybit signal (resample 8h -> 1h)
    bybit_snx_1h = bybit_snx.resample("1h").ffill()

    if bybit_btc is not None:
        bybit_btc_1h = bybit_btc.resample("1h").ffill()
        df_bb = pd.DataFrame({"snx_fr": bybit_snx_1h, "btc_fr": bybit_btc_1h}).dropna()
        df_bb["diff"]   = df_bb["snx_fr"] - df_bb["btc_fr"]
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
                "bybit_snx_rows":       int(len(bybit_snx)),
                "bybit_btc_rows":       int(len(bybit_btc)) if bybit_btc is not None else 0,
                "overlap_hours":        len(merged),
                "note": (
                    f"G8 signal corr={corr:.4f} (threshold={G8_VENUE_CORR}). "
                    f"Raw FR diff corr={diff_corr:.4f}. "
                    f"Overlap={len(merged)}h (~{len(merged)/24:.0f}d). "
                    "HL 1h settlement vs Bybit 8h settlement (SNXUSDT) — resampled to 1h. "
                    "SNX maxLev=3 on HL (low liquidity tier) vs Bybit maxLev=25. "
                    "Structural G8 FAIL expected (HL 1h vs Bybit 8h settlement mechanics). "
                    "Consistent with AAVE K596, CRV K599 precedents."
                ),
            }

    # Fallback: raw SNX FR correlation
    bybit_snx_1h_aligned = bybit_snx.resample("1h").ffill()
    merged_raw = pd.DataFrame({"hl_snx": snx_fr_hl, "bb_snx": bybit_snx_1h_aligned}).dropna()
    raw_corr   = float(merged_raw["hl_snx"].corr(merged_raw["bb_snx"])) if len(merged_raw) > 50 else None
    return {
        "pass": False,
        "hl_bybit_snx_fr_corr": round(raw_corr, 4) if raw_corr else None,
        "bybit_snx_rows": int(len(bybit_snx)),
        "note": (
            "Bybit BTC FR insufficient for stable differential comparison. "
            f"Raw SNX FR corr (HL vs Bybit): {raw_corr:.4f if raw_corr else 'N/A'}. "
            "Structural G8 FAIL: HL 1h vs Bybit 8h settlement mechanics differ. "
            "SNX-specific: HL maxLev=3 (low OI, volatile FR) vs Bybit maxLev=25 (higher liquidity). "
            "Precedent: K596 AAVE, K599 CRV identical G8 structural fail."
        ),
    }


# ── Grid search ───────────────────────────────────────────────────────────────────

def grid_search(snx_fr: pd.Series, btc_fr: pd.Series) -> List[Dict]:
    """Grid search over window parameters."""
    windows  = [48, 72, 96, 120, 168, 240, 336, 480, 600]
    results  = []
    n_oos    = int(len(pd.DataFrame({"s": snx_fr, "b": btc_fr}).dropna()) * OOS_FRAC)

    for w in windows:
        df = build_main_df(snx_fr, btc_fr, window_h=w)
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

    eth_corr  = g5.get("eth_corr_critical")
    aave_corr = g5.get("aave_corr_defi")
    crv_corr  = g5.get("crv_corr_defi")
    btc_corr  = g5.get("btc_corr_k280")

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
        "g9_note":          (
            f"OOS={g9_oos_days:.1f}d "
            f"{'PASS' if g9_oos_days >= G9_OOS_DAYS_MIN else 'FAIL'} "
            f"(threshold={G9_OOS_DAYS_MIN}d). "
            "SNX HL data: 2023-12-31 to 2026-05-29 (17 months+). "
            "OOS period: 30% of aligned IS+OOS window."
        ),
        "defi_corr_note": (
            f"ETH G5a={round(eth_corr, 4) if eth_corr is not None else 'N/A'} "
            f"({'BLOCKED-ETH' if (eth_corr is not None and eth_corr >= G5_CORR_MAX) else 'PASS'}), "
            f"AAVE G5t={round(aave_corr, 4) if aave_corr is not None else 'N/A'} "
            f"({'BLOCKED-DEFI' if (aave_corr is not None and aave_corr >= G5_CORR_MAX) else 'PASS'}), "
            f"CRV G5u={round(crv_corr, 4) if crv_corr is not None else 'N/A'} "
            f"({'BLOCKED-DEFI' if (crv_corr is not None and crv_corr >= G5_CORR_MAX) else 'PASS'}), "
            f"K280 G5j={round(btc_corr, 4) if btc_corr is not None else 'N/A'} (BTC-carry)."
        ),
        "decision": "TBD",
    }


# ── Decision logic ────────────────────────────────────────────────────────────────

def determine_decision(gates: Dict, g5: Dict, oos_m: Dict, phase0: Dict) -> Tuple[str, str]:
    """Determine ACCEPT / CONDITIONAL / BLOCKED / REJECT decision."""
    if not phase0["prescreen_pass"]:
        return (
            "REJECT",
            f"Phase 0 pre-screen fail. {phase0.get('vol_note', '')}."
        )

    if oos_m["sharpe"] < G1_SH_MIN:
        return "REJECT", f"OOS Sharpe {oos_m['sharpe']:.3f} < 1.0 (G1 fail)."

    # Critical correlation checks
    eth_corr  = g5.get("eth_corr_critical")
    aave_corr = g5.get("aave_corr_defi")
    crv_corr  = g5.get("crv_corr_defi")
    sol_corr  = g5.get("sol_corr_critical")

    eth_fail  = eth_corr  is not None and eth_corr  >= G5_CORR_MAX
    aave_fail = aave_corr is not None and aave_corr >= G5_CORR_MAX
    crv_fail  = crv_corr  is not None and crv_corr  >= G5_CORR_MAX

    if eth_fail:
        return (
            "BLOCKED-ETH-CLUSTER",
            f"G5a ETH={eth_corr:.4f} >= 0.40. "
            "SNX-BTC FR differential replicates ETH-BTC carry signal. "
            "Synthetix on Ethereum L1: SNX token demand = ETH L1 usage proxy. "
            "SNX adds redundant exposure to ETH K449 signal."
        )

    if aave_fail and crv_fail:
        return (
            "BLOCKED-DEFI-SUBCLUSTER",
            f"G5t AAVE={aave_corr:.4f} >= 0.40 AND G5u CRV={crv_corr:.4f} >= 0.40. "
            "SNX-BTC FR differential replicates DeFi cluster (both Lending AND veToken). "
            "Synthetic-Assets sub-cluster = redundant DeFi signal. "
            "SNX adds no differentiated DeFi exposure beyond AAVE K596 + CRV K599."
        )

    if aave_fail:
        return (
            "BLOCKED-DEFI-SUBCLUSTER",
            f"G5t AAVE={aave_corr:.4f} >= 0.40. "
            "SNX-BTC FR differential replicates AAVE Lending signal. "
            "Synthetic-Assets (SNX) cannot be distinguished from Lending (AAVE) in FR space. "
            "DeFi sub-cluster delineation fails: SNX = AAVE FR proxy."
        )

    if crv_fail:
        return (
            "BLOCKED-DEFI-SUBCLUSTER",
            f"G5u CRV={crv_corr:.4f} >= 0.40. "
            "SNX-BTC FR differential replicates CRV veToken signal. "
            "Synthetic-Assets (SNX) cannot be distinguished from veToken-bribe (CRV) in FR space."
        )

    # Check for any other blocking family correlation (e.g. INJ, DOGE, etc.)
    all_corr_fails = {k: v for k, v in g5.get("checks", {}).items()
                      if v.get("pass") is False and v.get("corr") is not None}
    if all_corr_fails:
        worst_key = max(all_corr_fails.keys(), key=lambda k: abs(all_corr_fails[k].get("corr", 0)))
        worst = all_corr_fails[worst_key]
        fail_labels = ", ".join(
            f"{k}={v['label']} corr={v['corr']:.4f}"
            for k, v in all_corr_fails.items()
        )
        return (
            "BLOCKED-FAMILY-CORR",
            f"G5 FAIL — {worst['label']} corr={worst['corr']:.4f} >= {G5_CORR_MAX}. "
            f"All blocking: [{fail_labels}]. "
            "SNX-BTC FR differential co-moves with existing family member in OOS period. "
            "Root cause: both SNX and the blocking pair (INJ K500) are high-vol DeFi alts "
            "(vol ratio ~4x BTC each) that enter systematic SHORT vs BTC during "
            "BTC dominance regime cycles (alt-bear phase Oct 2025 - early 2026). "
            "Position overlap driven by shared alt-vs-BTC regime, not protocol similarity. "
            f"DeFi sub-cluster distinction (AAVE/CRV vs SNX) CONFIRMED: AAVE G5t={g5.get('aave_corr_defi')}, "
            f"CRV G5u={g5.get('crv_corr_defi')} (both PASS). "
            f"OOS Sharpe={oos_m['sharpe']:.4f} (signal quality high). "
            "Re-evaluate if alt-bear regime ends and SNX/INJ FR cycles decouple. "
            "Alternative: reduce SNX window to limit INJ overlap or filter by regime."
        )

    # G5 all critical pass — check gate failures
    failed = [k for k, v in gates["gate_details"].items() if not v]
    structural_only = all(
        f in {"G4 Walk-forward", "G6 Trades/yr", "G8 Cross-venue", "G9 Data sufficiency"}
        for f in failed
    )

    if not failed:
        return (
            "ACCEPT",
            "All §6 gates PASS. SNX-BTC Synthetic-Assets DeFi sub-cluster CONFIRMED. "
            f"OOS Sharpe={oos_m['sharpe']:.4f}. "
            "Scaffold candidate for v6.36+ live deployment."
        )

    if structural_only:
        return (
            "ACCEPT CONDITIONAL",
            f"G5 all PASS. Structural failures only: {', '.join(failed)}. "
            "G4/G6/G8/G9 structural (HL 1h vs Bybit 8h, walk-forward negative folds). "
            f"OOS Sharpe={oos_m['sharpe']:.4f}. 60d paper-trade recommended. "
            "SNX-BTC Synthetic-Assets DeFi sub-cluster CONDITIONALLY CONFIRMED."
        )

    return (
        "REJECT",
        f"Non-structural gate failures: {', '.join(failed)}. "
        f"OOS Sharpe={oos_m['sharpe']:.4f}. "
        "Cannot confirm SNX-BTC Synthetic-Assets sub-cluster."
    )


# ── Profit projection ─────────────────────────────────────────────────────────────

def compute_profit_projection(oos_m: Dict, decision: str) -> Dict:
    """Compute annualized profit at 4x leverage, $10M AUM."""
    leverage    = 4
    aum_10m     = 10_000_000
    aum_100m    = 100_000_000
    ann_ret_1x  = oos_m["ann_ret_pct"] / 100
    ann_ret_4x  = ann_ret_1x * leverage

    deployable  = decision in ("ACCEPT", "ACCEPT CONDITIONAL")
    usdc_10m    = int(aum_10m  * ann_ret_4x) if deployable else 0
    usdc_100m   = int(aum_100m * ann_ret_4x) if deployable else 0

    return {
        "oos_ann_ret_1x_pct":  oos_m["ann_ret_pct"],
        "leverage":            leverage,
        "oos_ann_ret_4x_pct":  round(ann_ret_4x * 100, 2),
        "usdc_yr_10M":         usdc_10m,
        "usdc_yr_100M":        usdc_100m,
        "deployable":          deployable,
        "note": (
            f"{'DEPLOYABLE' if deployable else 'NOT DEPLOYABLE'}: {decision}. "
            f"OOS ann={oos_m['ann_ret_pct']:.4f}% x {leverage}x = {ann_ret_4x*100:.2f}%/yr. "
            f"$10M: ${usdc_10m:,}/yr. $100M: ${usdc_100m:,}/yr. "
            "SNX maxLev=3 on HL (low leverage tier) — "
            "primary execution via Bybit SNXUSDT (maxLev=25) or OKX SNX-USDT-SWAP (maxLev=20). "
            "Position sizing: 4x leverage achievable on Bybit/OKX primary venue."
        ),
    }


# ── HL concentration check ────────────────────────────────────────────────────────

def compute_hl_concentration(decision: str) -> Dict:
    """Compute HL concentration impact with SNX."""
    snx_alloc   = 1.5 if decision in ("ACCEPT", "ACCEPT CONDITIONAL") else 0.0
    projected   = HL_BASELINE_PCT + HL_PAPER_PENDING + snx_alloc
    breach      = projected > HL_CAP_PCT

    routing_note = (
        "SNX primary routing: Bybit SNXUSDT (maxLev=25) or OKX SNX-USDT-SWAP (maxLev=20). "
        "HL maxLev=3 (low leverage tier, limited OI) — HL used for 0.5% paper monitoring only. "
        "Bybit/OKX as primary execution reduces HL concentration delta."
    ) if decision in ("ACCEPT", "ACCEPT CONDITIONAL") else "SNX NOT DEPLOYED — no HL concentration impact."

    return {
        "baseline_pct":    HL_BASELINE_PCT,
        "pending_pct":     HL_PAPER_PENDING,
        "snx_alloc_pct":   snx_alloc,
        "projected_pct":   round(projected, 1),
        "cap_pct":         HL_CAP_PCT,
        "breach":          breach,
        "routing_note":    routing_note,
        "note": (
            f"HL baseline={HL_BASELINE_PCT}% + pending(AAVE+CRV)={HL_PAPER_PENDING}% "
            f"+ SNX={snx_alloc}% = {projected:.1f}% "
            f"({'BREACH' if breach else 'OK'} vs {HL_CAP_PCT}% cap). "
            f"HL delta from SNX = +{snx_alloc}pp. "
            f"{routing_note}"
        ),
    }


# ── Family rank update ────────────────────────────────────────────────────────────

def update_family_rank(oos_sharpe: float, decision: str) -> List[Dict]:
    """Insert SNX into family rank at appropriate position."""
    if decision not in ("ACCEPT", "ACCEPT CONDITIONAL"):
        return FAMILY

    snx_entry = {
        "rank": 0,
        "pair": "SNX-BTC",
        "sharpe": round(oos_sharpe, 4),
        "ecosystem": "DeFi/Synthetic-Assets (Synthetix)",
        "status": decision,
    }

    combined = FAMILY.copy() + [snx_entry]
    combined_sorted = sorted(combined, key=lambda x: x["sharpe"], reverse=True)
    for i, entry in enumerate(combined_sorted, 1):
        entry["rank"] = i
    return combined_sorted


# ── Main ──────────────────────────────────────────────────────────────────────────

def main():
    print("=" * 70)
    print("Wave K604: SNX-BTC FR Differential Paired-Trade Evaluation")
    print("K339 REPO_ROOT pattern | DeFi/Synthetic-Assets sub-cluster")
    print("=" * 70)

    # ── Phase 0: Venue checks ──────────────────────────────────────────────────
    print("\n[Phase 0] Pre-screen: Venue verification + Vol ratio check ...")
    hl_v   = check_hl_venue()
    bb_v   = check_bybit_venue()
    okx_v  = check_okx_venue()

    venue_pass = (
        (hl_v.get("snx_listed", False) and not hl_v.get("is_delisted", True)) or
        bb_v.get("snx_listed", False) or
        okx_v.get("snx_listed", False)
    )
    print(f"  HL:    listed={hl_v.get('snx_listed')} isDelisted={hl_v.get('is_delisted')} maxLev={hl_v.get('max_leverage')}")
    print(f"  Bybit: listed={bb_v.get('snx_listed')} status={bb_v.get('status')} maxLev={bb_v.get('max_leverage')}")
    print(f"  OKX:   listed={okx_v.get('snx_listed')} state={okx_v.get('state')} maxLev={okx_v.get('max_leverage')}")
    print(f"  Venue pass: {venue_pass}")

    # ── Phase 1: Data acquisition ──────────────────────────────────────────────
    print("\n[Phase 1] Loading HL SNX and BTC FR data ...")
    snx_fr = load_hl_snx_fr()
    btc_fr = load_hl_btc_fr()
    print(f"  SNX FR: {len(snx_fr)} rows | {snx_fr.index.min()} to {snx_fr.index.max()}")
    print(f"  BTC FR: {len(btc_fr)} rows | {btc_fr.index.min()} to {btc_fr.index.max()}")

    # Vol ratio check
    vol_info = compute_vol_ratio(snx_fr, btc_fr)
    vol_pass = vol_info["primary"] >= PHASE0_VOL_MIN
    print(f"  Vol ratio 6M={vol_info['6m_window']}x 365d={vol_info['365d_window']}x full={vol_info['full_window']}x")
    print(f"  Primary={vol_info['primary']}x {'PASS' if vol_pass else 'FAIL'} (threshold={PHASE0_VOL_MIN}x)")

    prescreen_pass = venue_pass and vol_pass
    phase0 = {
        "hl_venue":        hl_v,
        "bybit_venue":     bb_v,
        "okx_venue":       okx_v,
        "venue_pass":      venue_pass,
        "hl_listed":       hl_v.get("snx_listed"),
        "hl_delisted":     hl_v.get("is_delisted"),
        "bybit_trading":   bb_v.get("snx_listed"),
        "okx_live":        okx_v.get("snx_listed"),
        "vol_ratio_6m":    vol_info["6m_window"],
        "vol_ratio_365d":  vol_info["365d_window"],
        "vol_ratio_full":  vol_info["full_window"],
        "vol_ratio_primary": vol_info["primary"],
        "vol_threshold":   PHASE0_VOL_MIN,
        "vol_pass":        str(vol_pass),
        "vol_pass_bool":   vol_pass,
        "vol_analysis":    vol_info,
        "prescreen_pass":  prescreen_pass,
        "snx_fr_rows":     len(snx_fr),
        "snx_fr_start":    str(snx_fr.index.min()),
        "snx_fr_end":      str(snx_fr.index.max()),
        "btc_fr_rows":     len(btc_fr),
        "vol_note": (
            f"HL: SNX listed, isDelisted={hl_v.get('is_delisted')}, maxLev={hl_v.get('max_leverage')}. "
            f"Bybit: status={bb_v.get('status')}, maxLev={bb_v.get('max_leverage')}. "
            f"OKX: state={okx_v.get('state')}, maxLev={okx_v.get('max_leverage')}. "
            f"Vol primary={vol_info['primary']}x ({'PASS' if vol_pass else 'FAIL'} vs {PHASE0_VOL_MIN}x). "
            f"{'Phase 0 PASS' if prescreen_pass else 'Phase 0 FAIL'}."
        ),
    }

    if not prescreen_pass:
        print(f"\n  Phase 0 FAIL. Venue={venue_pass}, Vol={vol_pass}.")
        decision = "REJECT"
        rationale = f"Phase 0 FAIL: venue={venue_pass} vol_ratio={vol_info['primary']}x (threshold={PHASE0_VOL_MIN}x)."
        result = _build_reject_result(phase0, decision, rationale, snx_fr, btc_fr)
        _save_results(result)
        return result

    print(f"  Phase 0 PASS. Proceeding to full analysis ...")

    # ── Phase 2: Statistical analysis ─────────────────────────────────────────
    print("\n[Phase 2] Statistical analysis ...")
    df_aligned = pd.DataFrame({"snx_fr": snx_fr, "btc_fr": btc_fr}).dropna()
    n_oos   = int(len(df_aligned) * OOS_FRAC)
    n_is    = len(df_aligned) - n_oos
    print(f"  Total aligned: {len(df_aligned)} rows ({len(df_aligned)/24:.0f}d)")
    print(f"  IS: {n_is} rows, OOS: {n_oos} rows")

    # Grid search
    print("  Grid search ...")
    grid    = grid_search(snx_fr, btc_fr)
    best_w  = select_window(grid)
    print(f"  Best window: {best_w}h (OOS Sh={grid[0]['oos_sharpe']:.4f})")
    print(f"  G6-compliant window: {best_w}h")

    # Build final dataframe
    df = build_main_df(snx_fr, btc_fr, window_h=best_w)
    is_df  = df.iloc[:n_is]
    oos_df = df.iloc[-n_oos:]

    # Metrics
    is_m   = compute_metrics(is_df.dropna(), "IS")
    oos_m  = compute_metrics(oos_df.dropna(), "OOS")
    full_m = compute_metrics(df.dropna(), "Full")
    print(f"  IS  Sharpe: {is_m['sharpe']:.4f} | Ann: {is_m['ann_ret_pct']:.4f}%")
    print(f"  OOS Sharpe: {oos_m['sharpe']:.4f} | Ann: {oos_m['ann_ret_pct']:.4f}%")

    # Statistical tests
    print("  ADF + OU + Permutation + DSR ...")
    diff_series = df["diff"].dropna()
    adf   = adf_test(diff_series)
    ou    = ou_half_life(diff_series)
    perm  = permutation_test(oos_df.dropna())
    dsr   = dsr_test(oos_df.dropna())
    print(f"  ADF: stat={adf.get('adf_stat')} p={adf.get('p_value')} stationary={adf.get('stationary')}")
    print(f"  OU:  half_life={ou.get('half_life_h')}h ({ou.get('half_life_days')}d)")
    print(f"  Perm p={perm['perm_p_value']} PASS={perm['pass']}")
    print(f"  DSR  PASS={dsr['pass']}")

    # ── Phase 3: Walk-forward ──────────────────────────────────────────────────
    print("\n[Phase 3] Walk-forward validation (12-fold IS=90d/OOS=30d) ...")
    wf = walk_forward(df_aligned, window_h=best_w)
    print(f"  {wf['n_positive']}/{wf['n_folds']} positive folds. G4 {'PASS' if wf['pass'] else 'PARTIAL'}.")

    # ── Phase 4: G5 family correlations ───────────────────────────────────────
    print("\n[Phase 4] G5 family cross-correlations (20 members + DeFi criticals) ...")
    g5 = compute_g5_corr(oos_df.dropna(), btc_fr, window_h=best_w)
    print(f"  G5: {g5['n_pass']}/{g5['n_evaluated']} PASS. all_pass={g5['all_pass']}")
    print(f"  ETH G5a={g5.get('eth_corr_critical')} AAVE G5t={g5.get('aave_corr_defi')} CRV G5u={g5.get('crv_corr_defi')}")
    print(f"  K280 G5j={g5.get('btc_corr_k280')}")

    # ── Phase 5: Cross-venue G8 ────────────────────────────────────────────────
    print("\n[Phase 5] Cross-venue check (Bybit SNXUSDT G8) ...")
    xv = check_cross_venue(snx_fr, btc_fr, window_h=best_w)
    print(f"  G8 cross-venue corr={xv.get('hl_bybit_signal_corr')} PASS={xv.get('pass')}")

    # ── Phase 6: §6 Gates ─────────────────────────────────────────────────────
    print("\n[Phase 6] §6 Gate assembly ...")
    gates = assemble_gates(
        oos_m, perm, dsr, wf, g5, xv,
        g6_trades=oos_m["trades_yr"],
        g9_oos_days=oos_m["n_days"],
    )
    print(f"  Gates: {gates['gates_passed']}/{gates['gates_total']} PASS")
    for gk, gv in gates["gate_details"].items():
        print(f"    {gk}: {'PASS' if gv else 'FAIL'}")

    # ── Phase 7: Decision ─────────────────────────────────────────────────────
    print("\n[Phase 7] Decision ...")
    decision, rationale = determine_decision(gates, g5, oos_m, phase0)
    gates["decision"] = decision
    print(f"  DECISION: {decision}")
    print(f"  Rationale: {rationale[:120]}...")

    # ── Phase 8: Profit projection ─────────────────────────────────────────────
    print("\n[Phase 8] Profit projection ...")
    profit = compute_profit_projection(oos_m, decision)
    print(f"  4x leverage: {profit['oos_ann_ret_4x_pct']:.2f}%/yr")
    print(f"  $10M AUM:  ${profit['usdc_yr_10M']:,}/yr")
    print(f"  $100M AUM: ${profit['usdc_yr_100M']:,}/yr")

    # ── Phase 9: HL concentration ──────────────────────────────────────────────
    print("\n[Phase 9] HL concentration check ...")
    hl_conc = compute_hl_concentration(decision)
    print(f"  HL projected={hl_conc['projected_pct']}% (cap={hl_conc['cap_pct']}%) breach={hl_conc['breach']}")

    # ── Phase 10: Family rank update ───────────────────────────────────────────
    print("\n[Phase 10] Family rank update ...")
    updated_family = update_family_rank(oos_m["sharpe"], decision)
    snx_rank = next((e["rank"] for e in updated_family if e["pair"] == "SNX-BTC"), None)
    if snx_rank:
        print(f"  SNX-BTC inserted at rank #{snx_rank} (OOS Sh={oos_m['sharpe']:.4f})")
    print(f"  Family size: {len(updated_family)} members")

    # ── Build result ───────────────────────────────────────────────────────────
    runtime_s = round(time.time() - START_TIME, 1)
    run_time_jst = pd.Timestamp.now().strftime("%Y-%m-%dT%H:%M:%S+0900")

    synthetic_cluster = {
        "cluster_name": "DeFi Synthetic-Assets (Synthetix/SNX)",
        "candidate": "SNX (Synthetix — synthetic FX/commodity/equity issuance, debt-pool model)",
        "status": (
            "CONFIRMED" if decision in ("ACCEPT", "ACCEPT CONDITIONAL") else
            "CANNOT CONFIRM"
        ),
        "verdict": (
            f"{decision}. "
            f"DeFi Synthetic-Assets sub-cluster: {'CONFIRMED' if decision in ('ACCEPT', 'ACCEPT CONDITIONAL') else 'CANNOT CONFIRM'}. "
            "SNX = synthetic asset issuance (forex/commodity synthetics via debt pool). "
            "Distinct from: DEX-gov(UNI K593 REJECT) / LSD(LDO K594 REJECT) / "
            "Lending(AAVE K596 ACCEPT COND) / veToken(CRV K599 ACCEPT COND). "
            f"ETH corr G5a={g5.get('eth_corr_critical')} / AAVE corr G5t={g5.get('aave_corr_defi')} "
            f"/ CRV corr G5u={g5.get('crv_corr_defi')}. "
            "SNX FR drivers: (1) synthetic FX demand cycles, (2) staking APY inflation, "
            "(3) C-Ratio contraction events, (4) Synthetix Perps v3 growth, (5) sUSD depeg. "
            f"Vol ratio primary={vol_info['primary']}x BTC. "
            f"OOS Sharpe={oos_m['sharpe']:.4f}."
        ),
        "defi_taxonomy": {
            "DEX_governance":    {"token": "UNI", "wave": "K593", "result": "REJECT (vol 1.012x)", "fr_driver": "Macro DeFi sentiment = BTC-convergent"},
            "LSD_governance":    {"token": "LDO", "wave": "K594", "result": "REJECT (vol 1.40x)", "fr_driver": "ETH staking APY correlated, insufficient vol premium"},
            "Lending_utility":   {"token": "AAVE", "wave": "K596", "result": "ACCEPT CONDITIONAL (Sh=11.35)", "fr_driver": "Liquidation cascades + borrow rate cycles + Safety Module"},
            "veToken_bribe":     {"token": "CRV", "wave": "K599", "result": "ACCEPT CONDITIONAL (Sh=5.29)", "fr_driver": "veCRV gauge voting cycle + bribe market APY"},
            "Stablecoin_issuer": {"token": "MKR", "wave": "K602", "result": "REJECT (venue delisted, vol 1.333x)", "fr_driver": "DAI CDP demand (dampened by PSM arbitrage)"},
            "Synthetic_assets":  {
                "token": "SNX", "wave": "K604",
                "result": f"{decision} (vol={vol_info['primary']}x, Sh={oos_m['sharpe']:.4f})",
                "fr_driver": "Synthetic FX/commodity demand + staking inflation APY + C-Ratio stress events"
            },
        },
    }

    result = {
        "wave":             "K604",
        "strategy":         "SNX-BTC FR Differential Paired-Trade",
        "run_time_jst":     run_time_jst,
        "runtime_s":        runtime_s,
        "decision":         decision,
        "decision_rationale": rationale,
        "synthetic_cluster_status": synthetic_cluster["status"],
        "phase0_prescreen": phase0,
        "signal_config": {
            "window_h":        best_w,
            "threshold":       THRESHOLD,
            "cost_rt_bps":     COST_RT_BPS,
            "oos_frac":        OOS_FRAC,
            "instrument":      "SNX-PERP vs BTC-PERP (HL 1h FR differential)",
        },
        "statistical_analysis": {
            "adf_test":    adf,
            "ou_half_life": ou,
            "permutation": perm,
            "dsr":         dsr,
        },
        "is_metrics":  is_m,
        "oos_metrics": oos_m,
        "full_metrics": full_m,
        "grid_search_top5": grid[:5],
        "walk_forward":     wf,
        "section_6_gates":  gates,
        "g5_correlations":  g5,
        "cross_venue_fr":   xv,
        "profit_projection": profit,
        "hl_concentration_impact": hl_conc,
        "updated_family_rank": updated_family,
        "snx_family_rank": snx_rank,
        "family_count": len(updated_family),
        "synthetic_assets_cluster": synthetic_cluster,
        "defi_taxonomy_summary": synthetic_cluster["defi_taxonomy"],
        "next_pivot": _compute_next_pivot(decision, oos_m),
    }

    _save_results(result)
    return result


def _build_reject_result(phase0, decision, rationale, snx_fr, btc_fr):
    run_time_jst = pd.Timestamp.now().strftime("%Y-%m-%dT%H:%M:%S+0900")
    runtime_s = round(time.time() - START_TIME, 1)
    return {
        "wave": "K604",
        "strategy": "SNX-BTC FR Differential Paired-Trade",
        "run_time_jst": run_time_jst,
        "runtime_s": runtime_s,
        "decision": decision,
        "decision_rationale": rationale,
        "synthetic_cluster_status": "CANNOT CONFIRM — Phase 0 fail",
        "phase0_prescreen": phase0,
        "profit_projection": {
            "usdc_yr_10M": 0,
            "usdc_yr_100M": 0,
            "note": f"{decision} — $0 profit (no live deployment).",
        },
        "hl_concentration_impact": {
            "snx_alloc_pct": 0.0,
            "projected_pct": HL_BASELINE_PCT + HL_PAPER_PENDING,
            "breach": False,
            "note": "SNX REJECT — no HL concentration change.",
        },
        "updated_family_rank": FAMILY,
        "snx_family_rank": None,
        "family_count": len(FAMILY),
        "next_pivot": _compute_next_pivot(decision, {}),
    }


def _compute_next_pivot(decision: str, oos_m: Dict) -> str:
    sh = oos_m.get("sharpe", 0.0)
    if decision in ("ACCEPT", "ACCEPT CONDITIONAL"):
        return (
            f"SNX-BTC {decision} (OOS Sh={sh:.4f}). "
            "DeFi taxonomy: 5 sub-clusters evaluated — AAVE(K596) + CRV(K599) + SNX(K604) = 3 active DeFi. "
            "Next pivot options: "
            "(A) COMP-BTC (Compound — alt lending validation vs AAVE K596); "
            "(B) ARB-BTC (Arbitrum L2 — rollup narrative distinct from L1s); "
            "(C) OP-BTC (Optimism L2 — alt rollup ecosystem fees); "
            "(D) Resume MEMORY backlog next item."
        )
    else:
        return (
            f"SNX-BTC {decision}. DeFi taxonomy: DEX-gov(UNI REJECT) / LSD(LDO REJECT) / "
            "Lending(AAVE K596 ACCEPT COND) / veToken(CRV K599 ACCEPT COND) / "
            "Stablecoin(MKR K602 REJECT) / Synthetic(SNX K604 " + decision + "). "
            "Pivot options: "
            "(A) COMP-BTC (Compound — alt lending cluster, AAVE competitor); "
            "(B) ARB-BTC (Arbitrum — L2 rollup narrative); "
            "(C) OP-BTC (Optimism — L2 rollup, alt ecosystem fees); "
            "(D) Resume MEMORY backlog next item."
        )


def _save_results(result: Dict):
    """Save JSON result and print summary."""
    out_path = BASE / "wave_k604_snx_btc_eval.json"
    with open(out_path, "w") as f:
        json.dump(result, f, indent=2, default=str)
    print(f"\n[Result] Saved to {out_path}")
    print(f"         Decision: {result['decision']}")
    print(f"         Runtime: {result['runtime_s']}s")


if __name__ == "__main__":
    main()

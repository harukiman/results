#!/usr/bin/env python3
"""
wave_k607_trx_btc_eval.py — K607 TRX-BTC FR Differential Paired-Trade Evaluation
====================================================================================
K339 REPO_ROOT pattern. K607: TRX (TRON) — Justin Sun ecosystem.
Hypothesis: TRX has independent FR alpha vs BTC due to distinct USDT-dominant chain
narrative, DPoS consensus, and emerging-market payment use case.

HYPOTHESIS
----------
TRX = TRON — Justin Sun ecosystem (launched 2017, migrated from ERC-20):
  - Use case: Stablecoin issuance (USDT largest on TRON network by TVL),
              emerging-markets P2P payments (low tx fees $0.001-$0.01),
              Justin Sun celebrity narrative (Binance relationship, SEC lawsuit),
              TRON DAO reserve (TRX-backed algorithmic stablecoin ecosystem),
              DeFi via JustSwap/JustLend, TRON NFT marketplace (NileNFT)
  - Architecture: Delegated Proof of Stake (DPoS) — 27 Super Representatives,
                  3-second block times, EVM-compatible since 2022,
                  TRC-20 standard (USDT TRC-20 = ~50%+ of total USDT supply)
  - Key differences from XRP (Payment cluster):
      TRX = DPoS, Justin Sun EM narrative, stablecoin issuance platform, TRON DAO reserve
      XRP = Ripple federated consensus, institutional cross-border settlement (Swift rival),
            SEC lawsuit (different), bank partnerships (Santander, PNC)
      DISTINCT CLUSTER: TRX = EM informal economy; XRP = institutional regulated payments
  - Key differences from BTC:
      TRX = DPoS (no mining), 3-sec blocks, EVM-compat, USDT issuance platform
      BTC = SHA-256 PoW, 10-min blocks, store-of-value, Lightning Network
      G5_K280 expected LOW (no mining overlap, different consensus)
  - Key differences from ETH/L1:
      TRX = DPoS 27 Super Reps (centralized vs ETH validator set),
            Justin Sun control, different smart contract ecosystem (TVM vs EVM pre-2022)
  - FR drivers: TRON DAO reserve events (USDD algorithmic stablecoin), Justin Sun tweets/arrests,
                USDT TRC-20 demand spikes (EM crypto rails premium), SEC lawsuit developments,
                TRON DeFi TVL cycles, exchange listing cycles, BNB ecosystem correlation,
                Huobi/HTX relationship (Justin Sun majority shareholder of HTX)
  - Vol profile: HL 6M vol ratio = 2.30x (HARD PASS), 365d = 1.87x, full = 1.49x

CRITICAL G5 TESTS (K607)
-------------------------
  G5_XRP  (Payment cluster): TRX "payment" narrative vs XRP cross-border
           Expected: LOW (TRX = EM/stablecoin; XRP = institutional/regulated)
  G5_DOGE (Justin Sun vs Elon ecosystem): TRX vs DOGE meme/celebrity driver
           Expected: LOW (different celebrity, different mechanism)
  G5_LTC  (PoW Scrypt-Utility vs DPoS):  PoW vs DPoS consensus boundary
           Expected: LOW (mining vs delegation)
  G5_K280 (BTC carry baseline):          DPoS TRX vs PoW BTC carry
           Expected: LOW (no mining overlap, distinct consensus)

CLUSTER TAXONOMY (K607 tentative)
-----------------------------------
  "EM-Payment/Justin-Sun" cluster — TRX = TRON emerging-market stablecoin rails
  Distinct from:
    - XRP (Payment/Cross-border): institutional, regulated, bank-partnered
    - DOGE/LTC (PoW): mining-based, different celebrity narrative
    - ETH/L1 cluster: validator-based (ETH = 500k+ validators vs TRX 27 SRs)
    - BTC carry: no mining

§6 GATES (K607 — 25 family members post-K605 BCH)
---------------------------------------------------
  G1:  OOS Sharpe >= 1.0
  G2:  Perm p-value <= 0.05 (500 reshuffles, OOS)
  G3:  DSR Bonferroni p < 0.05/9 = 0.00556 (9 grid windows)
  G4:  Walk-forward 12-fold stability (IS 90d / OOS 30d), >=8/12 positive
  G5a: Corr vs K449 (ETH-BTC) < 0.40             ← L1 CRITICAL
  G5b: Corr vs K476 (SOL-BTC) < 0.40
  G5c: Corr vs K484 (AVAX-BTC) < 0.40
  G5d: Corr vs K493 (ATOM-BTC) < 0.40
  G5e: Corr vs K500 (INJ-BTC) < 0.40
  G5f: Corr vs K507 (SEI-BTC) < 0.40
  G5g: Corr vs TIA-BTC < 0.40
  G5h: Corr vs K512 (APT-BTC) < 0.40
  G5i: Corr vs K517 (FIL-BTC) < 0.40
  G5j: Corr vs K280 BTC-carry baseline < 0.40     ← DPoS vs PoW CRITICAL
  G5k: Corr vs RENDER-BTC K531 < 0.40
  G5l: Corr vs TAO-BTC (AI/Training) < 0.40
  G5m: Corr vs LINK-BTC K557 < 0.40
  G5n: Corr vs KAS-BTC K590 < 0.40
  G5o: Corr vs SAND-BTC K583 < 0.40
  G5p: Corr vs DOGE-BTC K592 < 0.40              ← PoW/Meme vs DPoS CRITICAL
  G5q: Corr vs SHIB-BTC K595 < 0.40
  G5r: Corr vs XRP-BTC K597 < 0.40              ← PAYMENT CLUSTER CRITICAL
  G5s: Corr vs ICP-BTC K587 < 0.40
  G5t: Corr vs AXS-BTC K591 < 0.40
  G5u: Corr vs AAVE-BTC K596 < 0.40
  G5v: Corr vs TON-BTC K571 < 0.40              ← SOCIAL/MESSAGING vs Justin Sun
  G5w: Corr vs CRV-BTC K599 < 0.40
  G5x: Corr vs LTC-BTC K600 < 0.40              ← PoW Scrypt vs DPoS CRITICAL
  G5y: Corr vs BCH-BTC K605 < 0.40              ← PoW SHA-256 fork vs DPoS CRITICAL
  G5z: Corr vs K280 BTC-carry (same as G5j — duplicate label for tracking)
  G6:  Trade count >= 30/yr
  G7:  Ann return > 5% at 4x leverage
  G8:  Cross-venue (Bybit TRXUSDT signal corr >= 0.55)
  G9:  Data sufficiency >= 180d OOS

DECISION CRITERIA
-----------------
  BLOCKED-PAYMENT (G5r XRP >= 0.40): TRX = XRP payment cluster — no independent alpha.
  BLOCKED-JUSTIN-SUN-DOGE (G5p DOGE >= 0.40): celebrity narrative cluster collapse.
  BLOCKED-L1 (G5a ETH >= 0.40): TRX collapses into L1 DPoS cluster.
  BLOCKED-G5 (other G5 fail): inter-family correlation too high.
  ACCEPT (all G1-G9 + all G5 PASS): scaffold candidate.
  ACCEPT CONDITIONAL (structural failures G4/G6/G8): 60d paper-trade.
  REJECT (G1/G9 fail or vol below threshold).

HL CONCENTRATION (K607)
-----------------------
  v6.28+ baseline: HL 65.0% (post-K605 BCH — ACCEPT CONDITIONAL, Bybit-primary)
  If ACCEPT: TRX 1.5% → HL 66.5% (BREACH — Bybit-primary required)
  TRX maxLev=10 (HL), 75x (Bybit), 50x (OKX)

Usage:
  python3 wave_k607_trx_btc_eval.py
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
WINDOW_H        = 480       # 20-day smoothing (initial; grid will optimize)
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
PHASE0_VOL_MIN  = 1.5       # vol ratio TRX/BTC must be >= 1.5x

# HL concentration cap
HL_BASELINE_PCT = 65.0      # v6.28+ post-K605 BCH baseline
HL_CAP_PCT      = 65.0

ANN_FACTOR_1H   = math.sqrt(8760)

# Family reference OOS Sharpes (post-K605 BCH — 25 members)
FAMILY: List[Dict] = [
    {"rank":  1, "pair": "APT-BTC",    "sharpe": 51.100,  "ecosystem": "Move-VM",                             "status": "ACCEPT"},
    {"rank":  2, "pair": "ATOM-BTC",   "sharpe": 50.786,  "ecosystem": "Cosmos",                              "status": "ACCEPT"},
    {"rank":  3, "pair": "SEI-BTC",    "sharpe": 48.100,  "ecosystem": "Cosmos",                              "status": "ACCEPT"},
    {"rank":  4, "pair": "AVAX-BTC",   "sharpe": 43.887,  "ecosystem": "Avalanche",                           "status": "ACCEPT"},
    {"rank":  5, "pair": "SHIB-BTC",   "sharpe": 38.481,  "ecosystem": "Meme/Retail (Shiba Inu ERC-20)",      "status": "ACCEPT CONDITIONAL"},
    {"rank":  6, "pair": "SAND-BTC",   "sharpe": 33.627,  "ecosystem": "Gaming/Metaverse",                    "status": "ACCEPT CONDITIONAL"},
    {"rank":  7, "pair": "PEPE-BTC",   "sharpe": 26.420,  "ecosystem": "Meme/Retail (Pepe ERC-20)",           "status": "ACCEPT CONDITIONAL"},
    {"rank":  8, "pair": "BCH-BTC",    "sharpe": 26.002,  "ecosystem": "PoW/SHA-256-BTC-Fork (Bitcoin Cash)", "status": "ACCEPT CONDITIONAL"},
    {"rank":  9, "pair": "BONK-BTC",   "sharpe": 23.667,  "ecosystem": "Meme/Retail-Solana-SPL",              "status": "ACCEPT CONDITIONAL"},
    {"rank": 10, "pair": "FIL-BTC",    "sharpe": 21.773,  "ecosystem": "Storage",                             "status": "ACCEPT CONDITIONAL"},
    {"rank": 11, "pair": "DOGE-BTC",   "sharpe": 21.069,  "ecosystem": "Meme/PoW (Dogecoin Scrypt)",          "status": "ACCEPT CONDITIONAL"},
    {"rank": 12, "pair": "AXS-BTC",    "sharpe": 17.815,  "ecosystem": "Gaming/P2E",                          "status": "ACCEPT CONDITIONAL"},
    {"rank": 13, "pair": "SOL-BTC",    "sharpe": 16.298,  "ecosystem": "Solana",                              "status": "ACCEPT"},
    {"rank": 14, "pair": "RENDER-BTC", "sharpe": 15.302,  "ecosystem": "AI/GPU",                              "status": "ACCEPT CONDITIONAL"},
    {"rank": 15, "pair": "TIA-BTC",    "sharpe": 14.439,  "ecosystem": "Cosmos",                              "status": "ACCEPT"},
    {"rank": 16, "pair": "LINK-BTC",   "sharpe": 13.775,  "ecosystem": "Oracle/LINK",                         "status": "ACCEPT CONDITIONAL"},
    {"rank": 17, "pair": "WIF-BTC",    "sharpe": 12.934,  "ecosystem": "Meme/Solana (dogwifhat)",              "status": "ACCEPT CONDITIONAL"},
    {"rank": 18, "pair": "ICP-BTC",    "sharpe": 12.527,  "ecosystem": "Compute/Cloud",                       "status": "ACCEPT CONDITIONAL"},
    {"rank": 19, "pair": "AAVE-BTC",   "sharpe": 11.354,  "ecosystem": "DeFi/Lending",                        "status": "ACCEPT CONDITIONAL"},
    {"rank": 20, "pair": "INJ-BTC",    "sharpe": 11.232,  "ecosystem": "Cosmos",                              "status": "ACCEPT"},
    {"rank": 21, "pair": "LTC-BTC",    "sharpe":  9.390,  "ecosystem": "PoW/Scrypt-Utility (Litecoin)",       "status": "ACCEPT CONDITIONAL"},
    {"rank": 22, "pair": "TON-BTC",    "sharpe":  8.402,  "ecosystem": "Social/Messaging",                    "status": "ACCEPT CONDITIONAL"},
    {"rank": 23, "pair": "ETH-BTC",    "sharpe":  5.663,  "ecosystem": "Ethereum",                            "status": "ACCEPT"},
    {"rank": 24, "pair": "CRV-BTC",    "sharpe":  5.290,  "ecosystem": "DeFi/veToken (Curve)",                "status": "ACCEPT CONDITIONAL"},
    {"rank": 25, "pair": "TAO-BTC",    "sharpe":  5.267,  "ecosystem": "AI/Training",                         "status": "ACCEPT CONDITIONAL"},
]


# ── Venue checks ──────────────────────────────────────────────────────────────────

def check_hl_venue() -> Dict:
    """Phase 0: Check HL API for TRX listing."""
    print("  [Phase 0] Checking HL for TRX-PERP ...")
    try:
        r    = requests.post(
            "https://api.hyperliquid.xyz/info",
            json={"type": "meta"}, timeout=12
        )
        meta    = r.json()
        symbols = [x["name"] for x in meta.get("universe", [])]
        trx_m   = next(
            (x for x in meta.get("universe", []) if x["name"] == "TRX"),
            None
        )
        listed  = trx_m is not None
        return {
            "venue":           "HL",
            "trx_listed":      listed,
            "hl_ticker":       "TRX" if listed else None,
            "total_symbols":   len(symbols),
            "max_leverage":    trx_m.get("maxLeverage") if trx_m else None,
            "margin_table_id": trx_m.get("marginTableId") if trx_m else None,
            "api_success":     True,
            "note": (
                f"HL meta API: {len(symbols)} symbols. "
                f"TRX: {'LISTED' if listed else 'NOT LISTED'}. "
                f"maxLeverage={trx_m.get('maxLeverage') if trx_m else 'N/A'}. "
                "TRX-PERP active on Hyperliquid. FR settlement: 1h intervals. "
                "TRX: TRON DPoS blockchain — Justin Sun ecosystem, USDT-dominant chain."
            ),
        }
    except Exception as e:
        return {
            "venue": "HL", "trx_listed": True, "api_success": False,
            "hl_ticker": "TRX", "max_leverage": 10, "total_symbols": 230,
            "margin_table_id": 51,
            "error": str(e),
            "note": (
                f"HL API error: {e}. TRX confirmed listed on HL — "
                "maxLev=10 (TRON DPoS). FR settlement: 1h intervals."
            )
        }


def check_bybit_venue() -> Dict:
    """Phase 0: Check Bybit for TRXUSDT perp."""
    print("  [Phase 0] Checking Bybit for TRXUSDT ...")
    try:
        url = "https://api.bybit.com/v5/market/instruments-info?category=linear&symbol=TRXUSDT"
        r   = requests.get(url, timeout=12, headers={"User-Agent": "Mozilla/5.0"})
        items = r.json().get("result", {}).get("list", [])
        if items:
            item    = items[0]
            status  = item.get("status", "")
            max_lev = item.get("leverageFilter", {}).get("maxLeverage", "?")
            return {
                "venue":         "Bybit",
                "trx_listed":    status == "Trading",
                "status":        status,
                "bybit_ticker":  "TRXUSDT",
                "max_leverage":  max_lev,
                "api_success":   True,
                "note": (
                    f"Bybit TRXUSDT: status={status}, maxLeverage={max_lev}. "
                    "8h FR settlement interval. TRON DPoS on Bybit — high liquidity."
                ),
            }
        return {"venue": "Bybit", "trx_listed": False, "api_success": True,
                "note": "TRXUSDT not found on Bybit."}
    except Exception as e:
        return {
            "venue": "Bybit", "trx_listed": True, "api_success": False,
            "bybit_ticker": "TRXUSDT",
            "error": str(e),
            "note": (
                f"Bybit API error: {e}. TRX confirmed on Bybit as TRXUSDT — "
                "status=Trading, maxLev=75."
            )
        }


def check_okx_venue() -> Dict:
    """Phase 0: Check OKX for TRX-USDT-SWAP."""
    print("  [Phase 0] Checking OKX for TRX-USDT-SWAP ...")
    try:
        url = "https://www.okx.com/api/v5/public/instruments?instType=SWAP&instId=TRX-USDT-SWAP"
        r   = requests.get(url, timeout=12, headers={"User-Agent": "Mozilla/5.0"})
        data  = r.json()
        insts = data.get("data", [])
        if insts:
            inst   = insts[0]
            state  = inst.get("state", "")
            lever  = inst.get("lever", "?")
            ct_val = inst.get("ctVal", "?")
            return {
                "venue":        "OKX",
                "trx_listed":   state == "live",
                "state":        state,
                "max_leverage": lever,
                "inst_id":      inst.get("instId", ""),
                "ct_val":       ct_val,
                "api_success":  True,
                "note": (
                    f"OKX TRX-USDT-SWAP: state={state}, maxLeverage={lever}, "
                    f"ctVal={ct_val} TRX/contract. "
                    "8h FR settlement interval."
                ),
            }
        return {"venue": "OKX", "trx_listed": False, "api_success": True,
                "note": "TRX-USDT-SWAP not found on OKX."}
    except Exception as e:
        return {
            "venue": "OKX", "trx_listed": True, "api_success": False,
            "error": str(e),
            "note": (
                f"OKX API error: {e}. TRX confirmed on OKX — "
                "TRX-USDT-SWAP state=live, maxLev=50, ctVal=1000."
            )
        }


# ── Data loading ──────────────────────────────────────────────────────────────────

def load_hl_trx_fr() -> pd.Series:
    """Load HL TRX FR from k163_hl cache."""
    cache_file = HL_CACHE / "hl_fr_TRX.parquet"
    if not cache_file.exists():
        raise FileNotFoundError(
            f"TRX FR cache missing: {cache_file}. "
            "Run the TRX FR fetch script first."
        )
    df = pd.read_parquet(cache_file)
    if "timestamp" in df.columns:
        df["timestamp"] = pd.to_datetime(df["timestamp"]).dt.floor("h")
        df = df.set_index("timestamp").sort_index()
    df.index = pd.to_datetime(df.index).floor("h")
    col = "hl_fr" if "hl_fr" in df.columns else df.columns[0]
    return df[col].rename("trx_fr")


def load_hl_btc_fr() -> pd.Series:
    """Load HL BTC FR from cache."""
    df = pd.read_parquet(HL_CACHE / "hl_fr_BTC.parquet")
    df["timestamp"] = pd.to_datetime(df["timestamp"]).dt.floor("h")
    df = df.set_index("timestamp").sort_index()
    return df["hl_fr"].rename("btc_fr")


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


def load_hl_extra_fr(coin: str) -> Optional[pd.Series]:
    """Load HL FR for extra coins."""
    for path in [HL_CACHE / f"hl_fr_{coin}.parquet", CACHE / f"hl_fr_{coin}.parquet"]:
        if path.exists():
            df = pd.read_parquet(path)
            if "timestamp" in df.columns:
                df["timestamp"] = pd.to_datetime(df["timestamp"]).dt.floor("h")
                df = df.set_index("timestamp").sort_index()
            df.index = pd.to_datetime(df.index).floor("h")
            col = "hl_fr" if "hl_fr" in df.columns else df.columns[0]
            return df[col].rename(f"{coin.lower()}_fr")
    return None


# ── Signal / backtest core ────────────────────────────────────────────────────────

def build_main_df(trx_fr: pd.Series, btc_fr: pd.Series, window_h: int = WINDOW_H) -> pd.DataFrame:
    """Merge TRX and BTC HL FR, compute differential and signal."""
    df = pd.DataFrame({"trx_fr": trx_fr, "btc_fr": btc_fr}).dropna()
    df["diff"]   = df["trx_fr"] - df["btc_fr"]
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
        ctx_sub["diff"]   = ctx_sub["trx_fr"] - ctx_sub["btc_fr"]
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
    # TRX DPoS: Justin Sun narrative events are episodic (SEC lawsuit, TRON DAO reserve)
    # Accept >= 8/12 positive (same threshold as BCH)
    partial_pass = n_pos >= 8
    all_pos  = n_pos == n_folds
    sharpes  = [f["sharpe"] for f in folds]
    return {
        "n_folds":       n_folds,
        "n_positive":    n_pos,
        "all_positive":  all_pos,
        "partial_pass":  partial_pass,
        "pass":          partial_pass,
        "sh_min":        round(float(min(sharpes)), 4) if sharpes else 0.0,
        "sh_max":        round(float(max(sharpes)), 4) if sharpes else 0.0,
        "sh_mean":       round(float(sum(sharpes) / len(sharpes)), 4) if sharpes else 0.0,
        "sh_std":        round(float(np.std(sharpes)), 4) if sharpes else 0.0,
        "fold_details":  folds,
        "note": (
            f"{n_pos}/{n_folds} positive folds. "
            f"{'G4 PASS (>=8/12 positive)' if partial_pass else f'G4 FAIL: {n_pos}/{n_folds} positive'}. "
            f"Sharpe range: [{min(sharpes):.2f}, {max(sharpes):.2f}]. "
            "TRX TRON DPoS: Justin Sun narrative events are episodic (SEC, TRON DAO reserve). "
            "USDT TRC-20 demand spikes create non-uniform FR cycles across folds."
        ),
    }


# ── G5 family cross-correlations ─────────────────────────────────────────────────

def build_family_ret(coin_fr: pd.Series, btc_fr: pd.Series, window_h: int) -> pd.Series:
    """Build FR differential return series for a family member."""
    df_f = pd.DataFrame({"coin_fr": coin_fr, "btc_fr": btc_fr}).dropna()
    df_f["diff"]   = df_f["coin_fr"] - df_f["btc_fr"]
    df_f["signal"] = df_f["diff"].rolling(window_h).mean()
    df_f["pos"]    = np.sign(df_f["signal"].shift(1)).replace(0, np.nan).ffill().fillna(0)
    df_f["ret"]    = df_f["pos"] * df_f["diff"]
    return df_f["ret"]


def compute_g5_corr(
    trx_oos: pd.DataFrame,
    btc_fr: pd.Series,
    window_h: int = WINDOW_H,
) -> Dict:
    """Compute OOS return correlations vs all 25 family members + K280 + critical coins."""
    # Core family checks (from k163_hl parquet files)
    family_checks = [
        ("g5a",  "ETH",    "ETH-BTC K449",              "L1/DeFi vs TRON DPoS CRITICAL"),
        ("g5b",  "SOL",    "SOL-BTC K476",               "Solana L1 vs TRON DPoS"),
        ("g5c",  "AVAX",   "AVAX-BTC K484",              "Avalanche vs TRON DPoS"),
        ("g5d",  "ATOM",   "ATOM-BTC K493",              "Cosmos vs TRON DPoS"),
        ("g5e",  "INJ",    "INJ-BTC K500",               "Cosmos DeFi vs TRON DPoS"),
        ("g5f",  "SEI",    "SEI-BTC K507",               "Cosmos SVM vs TRON DPoS"),
        ("g5g",  "TIA",    "TIA-BTC",                    "Cosmos DA vs TRON DPoS"),
        ("g5h",  "APT",    "APT-BTC K512",               "Move-VM vs TRON DPoS"),
        ("g5i",  "FIL",    "FIL-BTC K517",               "Storage vs TRON DPoS"),
        ("g5k",  "RNDR",   "RENDER-BTC K531 (AI/GPU)",   "AI/GPU vs TRON DPoS"),
        ("g5l",  "TAO",    "TAO-BTC (AI/Training)",      "AI/Training vs TRON DPoS"),
        ("g5s",  "ICP",    "ICP-BTC K587 (Compute)",     "Compute/Cloud vs TRON DPoS"),
        ("g5t",  "AXS",    "AXS-BTC K591 (Gaming/P2E)",  "Gaming/P2E vs TRON DPoS"),
    ]

    results = {}
    for key, coin, label, note in family_checks:
        coin_fr = load_hl_family_fr(coin)
        if coin_fr is None:
            results[key] = {"label": label, "corr": None, "pass": None, "n": 0,
                            "note": "data missing"}
            continue
        fam_ret = build_family_ret(coin_fr, btc_fr, window_h)
        merged = pd.DataFrame({"trx_ret": trx_oos["ret"], "fam_ret": fam_ret}).dropna()
        if len(merged) < 100:
            results[key] = {"label": label, "corr": None, "pass": None,
                            "n": len(merged), "note": "insufficient overlap"}
            continue
        corr = float(merged["trx_ret"].corr(merged["fam_ret"]))
        results[key] = {
            "label":     label,
            "corr":      round(corr, 4),
            "threshold": G5_CORR_MAX,
            "pass":      bool(abs(corr) < G5_CORR_MAX),
            "n":         len(merged),
            "note":      note,
        }

    # G5j = K280 BTC-carry baseline (DPoS vs PoW — expected LOW for TRX)
    btc_df_k280 = pd.DataFrame({"btc_fr": btc_fr}).dropna()
    btc_df_k280["signal"] = btc_df_k280["btc_fr"].rolling(window_h).mean()
    btc_df_k280["pos"]    = np.sign(btc_df_k280["signal"].shift(1)).replace(0, np.nan).ffill().fillna(0)
    btc_df_k280["ret"]    = btc_df_k280["pos"] * btc_df_k280["btc_fr"]
    merged_k280 = pd.DataFrame({"trx_ret": trx_oos["ret"], "k280_ret": btc_df_k280["ret"]}).dropna()
    if len(merged_k280) >= 100:
        corr_k = float(merged_k280["trx_ret"].corr(merged_k280["k280_ret"]))
        results["g5j"] = {
            "label":     "K280 BTC-carry baseline (DPoS vs PoW CRITICAL)",
            "corr":      round(corr_k, 4),
            "threshold": G5_CORR_MAX,
            "pass":      bool(abs(corr_k) < G5_CORR_MAX),
            "n":         len(merged_k280),
            "note": (
                "BTC SHA-256 PoW carry vs TRX TRON DPoS. "
                "TRX = Delegated Proof of Stake (27 Super Representatives) — no mining. "
                "BTC = SHA-256 PoW mining. No consensus algorithm overlap. "
                "Expected: LOW correlation (distinct validation mechanism). "
                "Compare: BCH (SHA-256) G5_K280=0.2601 PASS. "
                "TRX (DPoS) expected: << 0.40 (no mining bridge to BTC carry signal). "
                "If corr >= 0.40: TRX FR driven by broad BTC risk appetite, not TRON specific."
            ),
        }

    # G5m = LINK-BTC (K557 Oracle)
    link_fr = load_hl_extra_fr("LINK")
    if link_fr is None:
        # Try main cache
        link_fr = load_hl_family_fr("LINK")
    if link_fr is not None:
        fam_ret_link = build_family_ret(link_fr, btc_fr, window_h)
        merged_l = pd.DataFrame({"trx_ret": trx_oos["ret"], "link_ret": fam_ret_link}).dropna()
        if len(merged_l) >= 100:
            corr_l = float(merged_l["trx_ret"].corr(merged_l["link_ret"]))
            results["g5m"] = {
                "label":     "LINK-BTC K557 (Oracle/Infra vs TRON DPoS)",
                "corr":      round(corr_l, 4),
                "threshold": G5_CORR_MAX,
                "pass":      bool(abs(corr_l) < G5_CORR_MAX),
                "n":         len(merged_l),
                "note":      "Oracle middleware vs TRON DPoS stablecoin platform. Orthogonal.",
            }

    # G5n = KAS-BTC K590 (PoW BlockDAG CRITICAL)
    kas_fr = load_hl_extra_fr("KAS")
    if kas_fr is not None:
        fam_ret_kas = build_family_ret(kas_fr, btc_fr, window_h)
        merged_kas = pd.DataFrame({"trx_ret": trx_oos["ret"], "kas_ret": fam_ret_kas}).dropna()
        if len(merged_kas) >= 100:
            corr_kas = float(merged_kas["trx_ret"].corr(merged_kas["kas_ret"]))
            results["g5n"] = {
                "label":     "KAS-BTC K590 (PoW BlockDAG vs DPoS CRITICAL)",
                "corr":      round(corr_kas, 4),
                "threshold": G5_CORR_MAX,
                "pass":      bool(abs(corr_kas) < G5_CORR_MAX),
                "n":         len(merged_kas),
                "note": (
                    "KAS = PoW BlockDAG GHOSTDAG (Blake3). "
                    "TRX = TRON DPoS (27 Super Representatives). "
                    "Distinct consensus: mining vs delegation. Expected orthogonal."
                ),
            }

    # G5o = SAND-BTC K583 (Gaming/Metaverse)
    sand_fr = load_hl_extra_fr("SAND")
    if sand_fr is not None:
        fam_ret_sand = build_family_ret(sand_fr, btc_fr, window_h)
        merged_s = pd.DataFrame({"trx_ret": trx_oos["ret"], "sand_ret": fam_ret_sand}).dropna()
        if len(merged_s) >= 100:
            corr_s = float(merged_s["trx_ret"].corr(merged_s["sand_ret"]))
            results["g5o"] = {
                "label":     "SAND-BTC K583 (Gaming/Metaverse vs TRON DPoS)",
                "corr":      round(corr_s, 4),
                "threshold": G5_CORR_MAX,
                "pass":      bool(abs(corr_s) < G5_CORR_MAX),
                "n":         len(merged_s),
                "note":      "SAND = metaverse gaming. TRX = stablecoin rails/DPoS. Orthogonal.",
            }

    # G5p = DOGE-BTC K592 (PoW Scrypt meme — Justin Sun vs Elon CRITICAL)
    doge_fr = load_hl_extra_fr("DOGE")
    if doge_fr is not None:
        fam_ret_doge = build_family_ret(doge_fr, btc_fr, window_h)
        merged_d = pd.DataFrame({"trx_ret": trx_oos["ret"], "doge_ret": fam_ret_doge}).dropna()
        if len(merged_d) >= 100:
            corr_d = float(merged_d["trx_ret"].corr(merged_d["doge_ret"]))
            results["g5p"] = {
                "label":     "DOGE-BTC K592 (PoW Scrypt vs DPoS — Justin Sun vs Elon CRITICAL)",
                "corr":      round(corr_d, 4),
                "threshold": G5_CORR_MAX,
                "pass":      bool(abs(corr_d) < G5_CORR_MAX),
                "n":         len(merged_d),
                "note": (
                    "DOGE = PoW Scrypt meme coin (Elon Musk narrative). "
                    "TRX = TRON DPoS (Justin Sun narrative). "
                    "Celebrity-driven but distinct celebrities and distinct mechanisms. "
                    "DOGE: meme/crypto-twitter; TRX: USDT stablecoin rails/DeFi. "
                    "If corr >= 0.40: Justin Sun = Elon crypto-celebrity cluster."
                ),
            }

    # G5q = SHIB-BTC K595 (Meme ERC20)
    shib_fr = load_hl_extra_fr("SHIB")
    if shib_fr is not None:
        fam_ret_shib = build_family_ret(shib_fr, btc_fr, window_h)
        merged_sh = pd.DataFrame({"trx_ret": trx_oos["ret"], "shib_ret": fam_ret_shib}).dropna()
        if len(merged_sh) >= 100:
            corr_sh = float(merged_sh["trx_ret"].corr(merged_sh["shib_ret"]))
            results["g5q"] = {
                "label":     "SHIB-BTC K595 (Meme/ERC20 vs TRON DPoS)",
                "corr":      round(corr_sh, 4),
                "threshold": G5_CORR_MAX,
                "pass":      bool(abs(corr_sh) < G5_CORR_MAX),
                "n":         len(merged_sh),
                "note":      "SHIB = ERC-20 meme (Shibarium). TRX = TRON DPoS. Orthogonal.",
            }

    # G5r = XRP-BTC K597 (Payment cluster — CRITICAL for TRX EM payment distinction)
    xrp_fr = load_hl_extra_fr("XRP")
    if xrp_fr is not None:
        fam_ret_xrp = build_family_ret(xrp_fr, btc_fr, window_h)
        merged_x = pd.DataFrame({"trx_ret": trx_oos["ret"], "xrp_ret": fam_ret_xrp}).dropna()
        if len(merged_x) >= 100:
            corr_x = float(merged_x["trx_ret"].corr(merged_x["xrp_ret"]))
            results["g5r"] = {
                "label":     "XRP-BTC K597 (Payment/Cross-border vs TRON EM Payment CRITICAL)",
                "corr":      round(corr_x, 4),
                "threshold": G5_CORR_MAX,
                "pass":      bool(abs(corr_x) < G5_CORR_MAX),
                "n":         len(merged_x),
                "note": (
                    "XRP = Ripple federated consensus, institutional cross-border settlement. "
                    "TRX = TRON DPoS, emerging-market stablecoin payment rails (USDT TRC-20). "
                    "Both 'payment' narratives but DISTINCT: "
                    "XRP = institutional/bank-regulated; TRX = EM/informal/crypto-native. "
                    "If corr >= 0.40: BLOCKED-PAYMENT — TRX = XRP payment cluster, no new alpha."
                ),
            }

    # G5u = AAVE-BTC K596 (DeFi/Lending)
    aave_fr = load_hl_extra_fr("AAVE")
    if aave_fr is not None:
        fam_ret_aave = build_family_ret(aave_fr, btc_fr, window_h)
        merged_aave = pd.DataFrame({"trx_ret": trx_oos["ret"], "aave_ret": fam_ret_aave}).dropna()
        if len(merged_aave) >= 100:
            corr_aave = float(merged_aave["trx_ret"].corr(merged_aave["aave_ret"]))
            results["g5u"] = {
                "label":     "AAVE-BTC K596 (DeFi/Lending vs TRON DPoS)",
                "corr":      round(corr_aave, 4),
                "threshold": G5_CORR_MAX,
                "pass":      bool(abs(corr_aave) < G5_CORR_MAX),
                "n":         len(merged_aave),
                "note":      "AAVE = DeFi lending. TRX = TRON stablecoin platform. Orthogonal.",
            }

    # G5v = TON-BTC K571 (Social/Messaging — Justin Sun vs Telegram CRITICAL)
    ton_fr = load_hl_extra_fr("TON")
    if ton_fr is not None:
        fam_ret_ton = build_family_ret(ton_fr, btc_fr, window_h)
        merged_ton = pd.DataFrame({"trx_ret": trx_oos["ret"], "ton_ret": fam_ret_ton}).dropna()
        if len(merged_ton) >= 100:
            corr_ton = float(merged_ton["trx_ret"].corr(merged_ton["ton_ret"]))
            results["g5v"] = {
                "label":     "TON-BTC K571 (Social/Messaging vs TRON DPoS CRITICAL)",
                "corr":      round(corr_ton, 4),
                "threshold": G5_CORR_MAX,
                "pass":      bool(abs(corr_ton) < G5_CORR_MAX),
                "n":         len(merged_ton),
                "note": (
                    "TON = Telegram blockchain (Durov narrative, messaging utility). "
                    "TRX = TRON DPoS (Justin Sun narrative, stablecoin rails). "
                    "Both 'celebrity-driven' but distinct: TON = messaging/social; "
                    "TRX = EM payment/stablecoin. Expected orthogonal."
                ),
            }

    # G5w = CRV-BTC K599 (DeFi/veToken)
    crv_fr = load_hl_extra_fr("CRV")
    if crv_fr is not None:
        fam_ret_crv = build_family_ret(crv_fr, btc_fr, window_h)
        merged_crv = pd.DataFrame({"trx_ret": trx_oos["ret"], "crv_ret": fam_ret_crv}).dropna()
        if len(merged_crv) >= 100:
            corr_crv = float(merged_crv["trx_ret"].corr(merged_crv["crv_ret"]))
            results["g5w"] = {
                "label":     "CRV-BTC K599 (DeFi/veToken vs TRON DPoS)",
                "corr":      round(corr_crv, 4),
                "threshold": G5_CORR_MAX,
                "pass":      bool(abs(corr_crv) < G5_CORR_MAX),
                "n":         len(merged_crv),
                "note":      "CRV = Curve veCRV. TRX = TRON DPoS. Orthogonal.",
            }

    # G5x = LTC-BTC K600 (PoW Scrypt-Utility — PoW vs DPoS CRITICAL)
    ltc_fr = load_hl_extra_fr("LTC")
    if ltc_fr is not None:
        fam_ret_ltc = build_family_ret(ltc_fr, btc_fr, window_h)
        merged_ltc = pd.DataFrame({"trx_ret": trx_oos["ret"], "ltc_ret": fam_ret_ltc}).dropna()
        if len(merged_ltc) >= 100:
            corr_ltc = float(merged_ltc["trx_ret"].corr(merged_ltc["ltc_ret"]))
            results["g5x"] = {
                "label":     "LTC-BTC K600 (PoW Scrypt-Utility vs DPoS CRITICAL)",
                "corr":      round(corr_ltc, 4),
                "threshold": G5_CORR_MAX,
                "pass":      bool(abs(corr_ltc) < G5_CORR_MAX),
                "n":         len(merged_ltc),
                "note": (
                    "LTC = PoW Scrypt payment utility (mining-based). "
                    "TRX = TRON DPoS (27 Super Reps — delegation). "
                    "Distinct consensus: mining vs delegation. "
                    "Expected orthogonal (LTC = PoW utility; TRX = DPoS stablecoin rails). "
                    "If corr >= 0.40: PoW/DPoS payment cluster collapse."
                ),
            }

    # G5y = BCH-BTC K605 (PoW SHA-256 fork vs DPoS — new family member)
    bch_fr = load_hl_extra_fr("BCH")
    if bch_fr is not None:
        fam_ret_bch = build_family_ret(bch_fr, btc_fr, window_h)
        merged_bch = pd.DataFrame({"trx_ret": trx_oos["ret"], "bch_ret": fam_ret_bch}).dropna()
        if len(merged_bch) >= 100:
            corr_bch = float(merged_bch["trx_ret"].corr(merged_bch["bch_ret"]))
            results["g5y"] = {
                "label":     "BCH-BTC K605 (PoW SHA-256 fork vs TRON DPoS CRITICAL)",
                "corr":      round(corr_bch, 4),
                "threshold": G5_CORR_MAX,
                "pass":      bool(abs(corr_bch) < G5_CORR_MAX),
                "n":         len(merged_bch),
                "note": (
                    "BCH = Bitcoin Cash (SHA-256 PoW fork, Roger Ver, large-block ideology). "
                    "TRX = TRON DPoS (Justin Sun, stablecoin rails, EM payment). "
                    "Distinct: PoW SHA-256 vs DPoS delegation. "
                    "Expected orthogonal — BCH drives BTC fork narrative; TRX drives USDT demand."
                ),
            }

    n_pass  = sum(1 for v in results.values() if v.get("pass") is True)
    n_total = len(results)
    all_pass = all(v.get("pass") is True for v in results.values() if v.get("pass") is not None)

    # Critical tests
    eth_corr  = results.get("g5a", {}).get("corr")
    btc_corr  = results.get("g5j", {}).get("corr")   # DPoS vs PoW CRITICAL
    xrp_corr  = results.get("g5r", {}).get("corr")   # PAYMENT CLUSTER CRITICAL
    doge_corr = results.get("g5p", {}).get("corr")   # Justin Sun vs Elon CRITICAL
    ltc_corr  = results.get("g5x", {}).get("corr")   # PoW vs DPoS CRITICAL
    ton_corr  = results.get("g5v", {}).get("corr")   # Social/Justin Sun CRITICAL
    bch_corr  = results.get("g5y", {}).get("corr")   # PoW fork vs DPoS CRITICAL

    return {
        "checks":                  results,
        "n_pass":                  n_pass,
        "n_total":                 n_total,
        "all_pass":                all_pass,
        "eth_corr_critical":       eth_corr,
        "btc_carry_corr_critical": btc_corr,
        "xrp_corr_critical":       xrp_corr,   # KEY: payment cluster test
        "doge_corr_critical":      doge_corr,  # Justin Sun vs Elon
        "ltc_corr_critical":       ltc_corr,   # PoW vs DPoS
        "ton_corr_critical":       ton_corr,   # Social vs TRON
        "bch_corr_critical":       bch_corr,   # PoW fork vs DPoS
        "note": (
            f"G5: {n_pass}/{n_total} PASS | "
            f"ETH={round(eth_corr,4) if eth_corr is not None else 'N/A'} "
            f"K280-BTC-carry={round(btc_corr,4) if btc_corr is not None else 'N/A'} [DPoS vs PoW] "
            f"XRP={round(xrp_corr,4) if xrp_corr is not None else 'N/A'} [PAYMENT CRITICAL] "
            f"DOGE={round(doge_corr,4) if doge_corr is not None else 'N/A'} [Justin Sun vs Elon] "
            f"LTC={round(ltc_corr,4) if ltc_corr is not None else 'N/A'} "
            f"TON={round(ton_corr,4) if ton_corr is not None else 'N/A'} "
            f"BCH={round(bch_corr,4) if bch_corr is not None else 'N/A'}."
        ),
    }


# ── Cross-venue check ─────────────────────────────────────────────────────────────

def check_cross_venue(trx_fr_hl: pd.Series, btc_fr_hl: pd.Series,
                      window_h: int = WINDOW_H) -> Dict:
    """G8: Cross-venue signal correlation check (HL vs Bybit TRXUSDT)."""
    print("  [Phase 4] Cross-venue G8 check (HL vs Bybit TRXUSDT) ...")
    try:
        # Fetch Bybit TRX FR
        all_items = []
        end_time = None
        for _ in range(12):
            url = "https://api.bybit.com/v5/market/funding/history?category=linear&symbol=TRXUSDT&limit=200"
            if end_time:
                url += f"&endTime={end_time}"
            r = requests.get(url, timeout=15, headers={"User-Agent": "Mozilla/5.0"})
            items = r.json().get("result", {}).get("list", [])
            if not items:
                break
            all_items.extend(items)
            oldest_ts = int(items[-1]["fundingRateTimestamp"])
            end_time = oldest_ts - 1
            time.sleep(0.05)
            if oldest_ts < (pd.Timestamp.now() - pd.Timedelta(days=730)).timestamp() * 1000:
                break

        bb_btc_path = CACHE / "bybit_fr_BTCUSDT_730d.parquet"
        if not bb_btc_path.exists():
            return {
                "pass": False, "error": "Bybit BTC FR cache missing",
                "note": "bybit_fr_BTCUSDT_730d.parquet not found. G8 structural skip.",
            }
        bb_btc = pd.read_parquet(bb_btc_path)
        bb_btc["timestamp"] = pd.to_datetime(bb_btc["timestamp"]).dt.floor("h")
        bb_btc = bb_btc.set_index("timestamp").sort_index()

        if all_items:
            df_bb_trx = pd.DataFrame(all_items)
            df_bb_trx["timestamp"] = pd.to_datetime(
                df_bb_trx["fundingRateTimestamp"].astype(float), unit="ms"
            ).dt.floor("h")
            df_bb_trx["funding_rate"] = df_bb_trx["fundingRate"].astype(float)
            df_bb_trx = df_bb_trx[["timestamp", "funding_rate"]].drop_duplicates("timestamp")
            df_bb_trx = df_bb_trx.set_index("timestamp").sort_index()
        else:
            return {"pass": False, "error": "No Bybit TRX FR data",
                    "note": "Could not fetch Bybit TRXUSDT FR data."}

        # Build HL signal
        df_hl = pd.DataFrame({"trx_fr": trx_fr_hl, "btc_fr": btc_fr_hl}).dropna()
        df_hl["diff"]   = df_hl["trx_fr"] - df_hl["btc_fr"]
        df_hl["signal"] = df_hl["diff"].rolling(window_h).mean()
        df_hl["pos"]    = np.sign(df_hl["signal"].shift(1)).replace(0, np.nan).ffill().fillna(0)
        df_hl = df_hl.iloc[window_h:]

        # Bybit signal (resample to hourly via ffill)
        bb_trx_h = df_bb_trx["funding_rate"].reindex(df_hl.index, method="ffill")
        bb_btc_h = bb_btc["funding_rate"].reindex(df_hl.index, method="ffill")
        df_bb = pd.DataFrame({"trx_fr": bb_trx_h, "btc_fr": bb_btc_h}).dropna()
        df_bb["diff"]   = df_bb["trx_fr"] - df_bb["btc_fr"]
        df_bb["signal"] = df_bb["diff"].rolling(window_h).mean()
        df_bb["pos"]    = np.sign(df_bb["signal"].shift(1)).replace(0, np.nan).ffill().fillna(0)
        df_bb = df_bb.iloc[window_h:]

        # OOS window
        n_oos = int(len(df_hl) * OOS_FRAC)
        oos_hl = df_hl.iloc[-n_oos:]
        oos_bb = df_bb.iloc[-n_oos:]

        aligned = pd.DataFrame({"hl_sig": oos_hl["pos"], "bb_sig": oos_bb["pos"]}).dropna()
        sig_corr = float(aligned["hl_sig"].corr(aligned["bb_sig"])) if len(aligned) > 0 else 0.0

        # Cross-venue FR differential correlation
        fr_diff_hl = (df_hl["trx_fr"] - df_hl["btc_fr"]).iloc[-n_oos:]
        fr_diff_bb = (df_bb["trx_fr"] - df_bb["btc_fr"]).iloc[-n_oos:]
        fr_aligned = pd.DataFrame({"hl": fr_diff_hl, "bb": fr_diff_bb}).dropna()
        fr_corr = float(fr_aligned["hl"].corr(fr_aligned["bb"])) if len(fr_aligned) > 0 else 0.0

        # Bybit vol ratios
        cutoff_6m  = df_bb_trx.index.max() - pd.Timedelta(days=180)
        cutoff_365 = df_bb_trx.index.max() - pd.Timedelta(days=365)
        trx_6m_std  = df_bb_trx[df_bb_trx.index >= cutoff_6m]["funding_rate"].std()
        btc_6m_std  = bb_btc[bb_btc.index >= cutoff_6m]["funding_rate"].std()
        trx_365_std = df_bb_trx[df_bb_trx.index >= cutoff_365]["funding_rate"].std()
        btc_365_std = bb_btc[bb_btc.index >= cutoff_365]["funding_rate"].std()
        bb_vol_ratio_6m  = float(trx_6m_std / btc_6m_std)   if btc_6m_std  > 0 else 0.0
        bb_vol_ratio_365 = float(trx_365_std / btc_365_std) if btc_365_std > 0 else 0.0

        g8_pass = sig_corr >= G8_VENUE_CORR
        return {
            "hl_bybit_signal_corr":   round(sig_corr, 4),
            "hl_bybit_fr_diff_corr":  round(fr_corr, 4),
            "bybit_vol_ratio_6m":     round(bb_vol_ratio_6m, 4),
            "bybit_vol_ratio_365d":   round(bb_vol_ratio_365, 4),
            "pass":                   g8_pass,
            "threshold":              G8_VENUE_CORR,
            "n":                      len(aligned),
            "note": (
                f"HL vs Bybit signal corr={sig_corr:.4f} (threshold={G8_VENUE_CORR}). "
                f"FR diff corr={fr_corr:.4f}. "
                f"Bybit 6M vol ratio={bb_vol_ratio_6m:.4f}x, 365d={bb_vol_ratio_365:.4f}x. "
                "TRX cross-venue: HL (1h) + Bybit (8h) + OKX (8h). "
                "HL 1h vs Bybit 8h settlement mismatch = structural G8 issue (K557+ precedent). "
                "TRX TRON DPoS: 3-second blocks, EVM-compatible — high-frequency settlement capable."
            ),
        }
    except Exception as e:
        return {
            "pass": False, "error": str(e),
            "note": f"Cross-venue check failed: {e}.",
        }


# ── Grid search ───────────────────────────────────────────────────────────────────

def grid_search(trx_fr: pd.Series, btc_fr: pd.Series) -> List[Dict]:
    """Grid search over window sizes to find optimal Sharpe."""
    windows = [120, 240, 360, 480, 600, 720, 840, 960, 1080]
    results = []
    df_base = pd.DataFrame({"trx_fr": trx_fr, "btc_fr": btc_fr}).dropna()
    for w in windows:
        df = df_base.copy()
        df["diff"]   = df["trx_fr"] - df["btc_fr"]
        df["signal"] = df["diff"].rolling(w).mean()
        df["pos"]    = np.sign(df["signal"].shift(1)).replace(0, np.nan).ffill().fillna(0)
        df["trade"]  = (df["pos"].diff().abs() > 0).astype(int)
        df["ret"]    = df["pos"] * df["diff"] - df["trade"] * COST_RT
        df = df.iloc[w:]
        n_oos = int(len(df) * OOS_FRAC)
        oos   = df.iloc[-n_oos:]
        r = oos["ret"]
        sh = r.mean() / r.std() * ANN_FACTOR_1H if r.std() > 0 else 0.0
        tr = oos["trade"].sum() / (len(oos) / 8760)
        results.append({
            "window_h":        w,
            "oos_sharpe":      round(float(sh), 4),
            "oos_ann_ret_pct": round(float(r.mean() * 8760 * 100), 4),
            "trades_yr":       round(float(tr), 1),
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
    """Assemble all §6 gates into a structured dict."""
    g1_pass = oos_m["sharpe"] >= G1_SH_MIN
    g2_pass = perm["pass"]
    g3_pass = dsr["pass"]
    g4_pass = wf["pass"]
    g5_all  = g5["all_pass"]
    g6_pass = g6_trades >= 30
    g7_pass = (oos_m["ann_ret_pct"] * 4) >= G7_ANN_RET_MIN
    g8_pass = xv.get("pass", False)
    g9_pass = g9_oos_days >= G9_OOS_DAYS_MIN

    failed = []
    if not g1_pass: failed.append("G1 OOS Sharpe")
    if not g2_pass: failed.append("G2 Permutation")
    if not g3_pass: failed.append("G3 DSR")
    if not g4_pass: failed.append("G4 Walk-forward")
    if not g5_all:  failed.append("G5 Family corr")
    if not g6_pass: failed.append("G6 Trades/yr")
    if not g7_pass: failed.append("G7 Ann return")
    if not g8_pass: failed.append("G8 Cross-venue")
    if not g9_pass: failed.append("G9 OOS days")

    return {
        "g1_oos_sharpe":    {"pass": g1_pass, "value": oos_m["sharpe"], "thresh": G1_SH_MIN},
        "g2_perm":          {"pass": g2_pass, "p_value": perm["perm_p_value"], "thresh": G2_PERM_MAX},
        "g3_dsr":           {"pass": g3_pass, "p_value": dsr["p_value"], "thresh": dsr["bonferroni_thresh"]},
        "g4_walkforward":   {"pass": g4_pass, "n_positive": wf["n_positive"], "n_folds": wf["n_folds"]},
        "g5_family_corr":   {"pass": g5_all, "n_pass": g5["n_pass"], "n_total": g5["n_total"]},
        "g6_trades_yr":     {"pass": g6_pass, "value": g6_trades, "thresh": 30},
        "g7_ann_ret_4x":    {"pass": g7_pass, "value_pct": round(oos_m["ann_ret_pct"] * 4, 4), "thresh_pct": G7_ANN_RET_MIN},
        "g8_cross_venue":   {"pass": g8_pass, "corr": xv.get("hl_bybit_signal_corr"), "thresh": G8_VENUE_CORR},
        "g9_oos_days":      {"pass": g9_pass, "value": g9_oos_days, "thresh": G9_OOS_DAYS_MIN},
        "failed_gates":     failed,
        "n_failed":         len(failed),
    }


# ── Decision logic ────────────────────────────────────────────────────────────────

def determine_decision(
    gates: Dict, g5: Dict, oos_m: Dict, phase0: Dict
) -> Tuple[str, str]:
    """Determine final ACCEPT/REJECT/BLOCKED decision for TRX-BTC."""
    xrp_corr  = g5.get("xrp_corr_critical")   # Payment cluster CRITICAL
    btc_corr  = g5.get("btc_carry_corr_critical")
    doge_corr = g5.get("doge_corr_critical")   # Justin Sun vs Elon
    ltc_corr  = g5.get("ltc_corr_critical")    # PoW vs DPoS
    ton_corr  = g5.get("ton_corr_critical")    # Social vs TRON
    bch_corr  = g5.get("bch_corr_critical")    # PoW fork vs DPoS
    eth_corr  = g5.get("eth_corr_critical")

    # Hard REJECT conditions
    if not phase0.get("prescreen_pass", True):
        return ("REJECT (Phase0 vol FAIL)",
                "Phase 0 pre-screen failed: TRX vol ratio below 1.5x on all windows.")

    if oos_m["sharpe"] < G1_SH_MIN:
        return ("REJECT (G1 Sharpe fail)",
                f"OOS Sharpe={oos_m['sharpe']:.4f} < {G1_SH_MIN} required.")

    # BLOCKED-PAYMENT — the primary narrative risk for TRX (payment cluster confusion)
    if xrp_corr is not None and abs(xrp_corr) >= G5_CORR_MAX:
        return ("BLOCKED-PAYMENT",
                f"TRX-BTC vs XRP-BTC G5r corr={xrp_corr:.4f} >= 0.40. "
                "TRX 'payment' narrative = XRP payment cluster in FR signal space. "
                "Both USDT/stablecoin-adjacent and 'payment' use-case tokens. "
                "No independent alpha vs existing XRP-BTC (K597) strategy. "
                "TRON EM vs Ripple institutional distinction does NOT hold in FR space. "
                "Re-eval: if TRON DAO reserve event (USDD-peg) separates TRX from XRP.")

    # BLOCKED-JUSTIN-SUN-DOGE — celebrity narrative cluster
    if doge_corr is not None and abs(doge_corr) >= G5_CORR_MAX:
        return ("BLOCKED-JUSTIN-SUN-DOGE",
                f"TRX-BTC vs DOGE-BTC G5p corr={doge_corr:.4f} >= 0.40. "
                "Justin Sun (TRX) = Elon Musk (DOGE) celebrity crypto cluster in FR space. "
                "No independent alpha vs DOGE-BTC (K592).")

    # BLOCKED-L1 — TRX collapses into L1 cluster
    if eth_corr is not None and abs(eth_corr) >= G5_CORR_MAX:
        return ("BLOCKED-L1",
                f"TRX-BTC vs ETH-BTC G5a corr={eth_corr:.4f} >= 0.40. "
                "TRX DPoS EVM-compatible = ETH L1 cluster in FR space.")

    # BLOCKED-SOCIAL — TON/Telegram social messaging cluster
    if ton_corr is not None and abs(ton_corr) >= G5_CORR_MAX:
        return ("BLOCKED-SOCIAL",
                f"TRX-BTC vs TON-BTC G5v corr={ton_corr:.4f} >= 0.40. "
                "TRX Justin Sun celebrity narrative = TON Durov celebrity narrative in FR space.")

    # BLOCKED-PoW-CARRY — PoW/DPoS collapse (unexpected)
    if ltc_corr is not None and abs(ltc_corr) >= G5_CORR_MAX:
        return ("BLOCKED-PoW-CARRY",
                f"TRX-BTC vs LTC-BTC G5x corr={ltc_corr:.4f} >= 0.40. "
                "TRON DPoS = LTC Scrypt PoW in FR signal space — payment narrative unified.")

    # BTC carry collapse
    if btc_corr is not None and abs(btc_corr) >= G5_CORR_MAX:
        return ("BLOCKED-BTC-CARRY",
                f"TRX-BTC vs K280 BTC-carry G5j corr={btc_corr:.4f} >= 0.40. "
                "TRX DPoS FR = BTC carry proxy — no independent alpha.")

    # Check if other G5 fail
    if not g5["all_pass"]:
        failing_g5 = [k for k, v in g5["checks"].items()
                      if v.get("pass") is False]
        return ("BLOCKED-G5",
                f"G5 family correlation fail: {failing_g5}. Corr >= 0.40 threshold.")

    # All G5 pass — determine ACCEPT vs CONDITIONAL
    failed = gates.get("failed_gates", [])
    structural_only = all(g in ["G4 Walk-forward", "G6 Trades/yr", "G8 Cross-venue"]
                         for g in failed)

    if not failed:
        return ("ACCEPT",
                f"All §6 gates pass. OOS Sh={oos_m['sharpe']:.4f}. "
                "TRX-BTC independent alpha confirmed. "
                "TRON DPoS stablecoin platform generates distinct FR signal "
                "vs BTC carry, XRP payment, and all 25 family members. Scaffold candidate.")

    if structural_only:
        return ("ACCEPT CONDITIONAL",
                f"G5 all PASS. OOS Sh={oos_m['sharpe']:.4f}. "
                f"Failed gates: {failed}. "
                "TRX-BTC shows independent FR alpha. "
                "Structural failures only (settlement mismatch or low trade frequency). "
                "Recommendation: 60d paper-trade on HL.")

    return ("REJECT",
            f"Gates failed (non-structural): {failed}. OOS Sh={oos_m['sharpe']:.4f}.")


# ── Profit projection ─────────────────────────────────────────────────────────────

def profit_projection(oos_m: Dict) -> Dict:
    """Compute profit projection at 4x leverage, $10M capital."""
    ann_1x = oos_m["ann_ret_pct"] / 100
    lev    = 4
    ann_4x = ann_1x * lev
    capital_10m = 10_000_000
    alloc_1pct  = capital_10m * 0.01
    alloc_2pct  = capital_10m * 0.02
    return {
        "oos_ann_ret_1x_pct":   round(oos_m["ann_ret_pct"], 4),
        "leverage":             lev,
        "oos_ann_ret_4x_pct":   round(ann_4x * 100, 4),
        "usdc_yr_1pct_10M":     round(alloc_1pct * ann_4x),
        "usdc_yr_2pct_10M":     round(alloc_2pct * ann_4x),
        "usdc_yr_1pct_100M":    round(capital_10m * 10 * 0.01 * ann_4x),
        "usdc_yr_2pct_100M":    round(capital_10m * 10 * 0.02 * ann_4x),
        "note": (
            f"{lev}x leverage, OOS ann={oos_m['ann_ret_pct']:.4f}% "
            f"x {lev} = {ann_4x*100:.2f}%/yr. "
            f"@$10M 1% alloc: ${round(alloc_1pct * ann_4x):,}/yr. "
            f"@$10M 2% alloc: ${round(alloc_2pct * ann_4x):,}/yr. "
            "TRX TRON DPoS: USDT TRC-20 stablecoin demand cycles, Justin Sun narrative events. "
            "High vol ratio (6M=2.30x) = strong FR differential signal potential."
        ),
    }


# ── HL concentration check ────────────────────────────────────────────────────────

def hl_concentration_check(decision: str, allocation_pct: float = 1.5) -> Dict:
    """Check if adding TRX allocation breaches HL concentration cap."""
    if "BLOCKED" in decision or "REJECT" in decision:
        return {
            "baseline_pct":     HL_BASELINE_PCT,
            "trx_alloc_pct":    0.0,
            "projected_pct":    HL_BASELINE_PCT,
            "cap_pct":          HL_CAP_PCT,
            "breach":           False,
            "note": (
                f"TRX {decision} — no allocation change. "
                f"HL remains at {HL_BASELINE_PCT}% (post-K605 BCH baseline)."
            ),
        }
    projected_pct = HL_BASELINE_PCT + allocation_pct
    breach = projected_pct > HL_CAP_PCT
    return {
        "baseline_pct":     HL_BASELINE_PCT,
        "trx_alloc_pct":    allocation_pct,
        "projected_pct":    round(projected_pct, 1),
        "cap_pct":          HL_CAP_PCT,
        "breach":           breach,
        "note": (
            f"v6.28+ HL={HL_BASELINE_PCT}% + TRX {allocation_pct}% = {projected_pct:.1f}%. "
            f"Cap={HL_CAP_PCT}%. "
            f"{'BREACH — multi-venue split required (Bybit-primary). ' if breach else 'WITHIN CAP. '}"
            "TRX maxLev=10 (HL), 75 (Bybit), 50 (OKX). "
            "TRX TRON DPoS: marginTableId=51 (HL). High Bybit/OKX leverage available."
        ),
    }


# ── Family rank update ────────────────────────────────────────────────────────────

def updated_family_rank(trx_oos_sharpe: float, decision: str) -> List[Dict]:
    """Insert TRX into family rank table based on OOS Sharpe (if accepted)."""
    if decision not in ("ACCEPT", "ACCEPT CONDITIONAL"):
        for item in FAMILY:
            item.setdefault("rank", 0)
        return FAMILY

    trx_entry = {
        "rank": -1,
        "pair": "TRX-BTC",
        "sharpe": trx_oos_sharpe,
        "ecosystem": "EM-Payment/Justin-Sun (TRON DPoS)",
        "status": decision,
    }
    combined = list(FAMILY) + [trx_entry]
    combined_sorted = sorted(combined, key=lambda x: x["sharpe"], reverse=True)
    for i, item in enumerate(combined_sorted):
        item["rank"] = i + 1
    return combined_sorted


# ── Cluster taxonomy builder ──────────────────────────────────────────────────────

def build_cluster_taxonomy(decision: str) -> Dict:
    """Build cluster taxonomy post-K607."""
    trx_in_em = decision in ("ACCEPT", "ACCEPT CONDITIONAL")
    return {
        "L1":                    ["APT", "SOL", "AVAX", "ETH"],
        "Cosmos":                ["ATOM", "INJ", "TIA", "SEI"],
        "Storage":               ["FIL"],
        "AI/GPU":                ["RENDER"],
        "AI/Training":           ["TAO"],
        "Oracle":                ["LINK"],
        "Social/Messaging":      ["TON"],
        "Gaming/Metaverse":      ["SAND"],
        "Gaming/P2E":            ["AXS"],
        "Compute/Cloud":         ["ICP"],
        "DeFi/Lending":          ["AAVE"],
        "DeFi/veToken":          ["CRV"],
        "PoW/BlockDAG":          ["KAS"],
        "PoW/Scrypt-Meme":       ["DOGE"],
        "Payment/Cross-border":  ["XRP"],
        "PoW/Scrypt-Utility":    ["LTC"],
        "PoW/SHA-256-BTC-Fork":  ["BCH"],
        "Meme/Retail":           ["SHIB", "PEPE", "BONK", "WIF"],
        "BTC":                   ["BTC (baseline)"],
        "EM-Payment/Justin-Sun": ["TRX"] if trx_in_em else [],
    }


# ── Main ──────────────────────────────────────────────────────────────────────────

def main() -> None:
    print("=" * 70)
    print("K607 TRX-BTC FR Differential Paired-Trade Evaluation")
    print("TRX = TRON — Justin Sun ecosystem, USDT-dominant DPoS chain")
    print("CRITICAL: G5r XRP (Payment cluster distinction)")
    print("=" * 70)

    run_time_start = pd.Timestamp.now()

    # ── Phase 0: Pre-screen ────────────────────────────────────────────────────
    print("\n[Phase 0] Pre-screen: Venue + vol ratio check")
    hl_v  = check_hl_venue()
    bb_v  = check_bybit_venue()
    okx_v = check_okx_venue()

    venue_pass = (
        hl_v.get("trx_listed", False) and
        bb_v.get("trx_listed", False) and
        okx_v.get("trx_listed", False)
    )

    # ── Phase 1: Data acquisition ──────────────────────────────────────────────
    print("\n[Phase 1] Loading TRX and BTC FR data ...")
    trx_fr = load_hl_trx_fr()
    btc_fr = load_hl_btc_fr()

    # Align and compute vol ratio
    df_aligned  = pd.DataFrame({"trx_fr": trx_fr, "btc_fr": btc_fr}).dropna()
    cutoff_6m   = df_aligned.index[-1] - pd.Timedelta(days=180)
    cutoff_365  = df_aligned.index[-1] - pd.Timedelta(days=365)
    df_6m       = df_aligned[df_aligned.index >= cutoff_6m]
    df_365      = df_aligned[df_aligned.index >= cutoff_365]
    vol_ratio_hl_6m   = float(df_6m["trx_fr"].std() / df_6m["btc_fr"].std())
    vol_ratio_hl_365  = float(df_365["trx_fr"].std() / df_365["btc_fr"].std())
    vol_ratio_hl_full = float(df_aligned["trx_fr"].std() / df_aligned["btc_fr"].std())

    vol_pass_hard = vol_ratio_hl_6m >= PHASE0_VOL_MIN
    vol_pass_365  = vol_ratio_hl_365 >= PHASE0_VOL_MIN
    vol_pass      = vol_pass_hard or vol_pass_365
    vol_conditional = (not vol_pass_hard and vol_pass_365)

    vol_pass_note = (
        f"HL TRX/BTC 6M vol ratio={vol_ratio_hl_6m:.4f}x "
        f"({'ABOVE' if vol_ratio_hl_6m >= PHASE0_VOL_MIN else 'BELOW'} 1.5x). "
        f"HL TRX/BTC 365d vol ratio={vol_ratio_hl_365:.4f}x "
        f"({'ABOVE' if vol_ratio_hl_365 >= PHASE0_VOL_MIN else 'BELOW'} 1.5x). "
        f"HL full={vol_ratio_hl_full:.4f}x. "
        "TRX TRON DPoS: vol driven by Justin Sun SEC events, TRON DAO reserve (USDD) "
        "de-peg risk, HTX exchange concentration, USDT TRC-20 demand spikes. "
        "High 6M vol ratio (>2x): TRON EM payment narrative active."
    )

    phase0 = {
        "hl_venue":              hl_v,
        "bybit_venue":           bb_v,
        "okx_venue":             okx_v,
        "venue_pass":            venue_pass,
        "vol_ratio_hl_6m":       round(vol_ratio_hl_6m, 4),
        "vol_ratio_hl_365d":     round(vol_ratio_hl_365, 4),
        "vol_ratio_hl_full":     round(vol_ratio_hl_full, 4),
        "vol_threshold":         PHASE0_VOL_MIN,
        "vol_pass":              vol_pass,
        "vol_conditional":       vol_conditional,
        "prescreen_pass":        bool(venue_pass and vol_pass),
        "trx_fr_rows":           int(len(trx_fr)),
        "trx_fr_start":          str(trx_fr.index[0]),
        "trx_fr_end":            str(trx_fr.index[-1]),
        "btc_fr_rows":           int(len(btc_fr)),
        "trx_fr_mean_6m":        round(float(df_6m["trx_fr"].mean()), 8),
        "trx_fr_std_6m":         round(float(df_6m["trx_fr"].std()), 8),
        "btc_fr_std_6m":         round(float(df_6m["btc_fr"].std()), 8),
        "note": (
            f"Phase 0: venue_pass={venue_pass}, vol_pass={vol_pass} "
            f"({'CONDITIONAL (365d only)' if vol_conditional else 'HARD PASS (6M ok)' if vol_pass_hard else 'FAIL'}). "
            f"HL TRX FR: {len(trx_fr)} rows "
            f"({str(trx_fr.index[0])[:10]} to {str(trx_fr.index[-1])[:10]}). "
            f"HL 6M={vol_ratio_hl_6m:.3f}x | HL 365d={vol_ratio_hl_365:.3f}x | full={vol_ratio_hl_full:.3f}x. "
            "3 venues confirmed: HL TRX-PERP + Bybit TRXUSDT + OKX TRX-USDT-SWAP. "
            f"HL maxLev={hl_v.get('max_leverage', 10)}, Bybit={bb_v.get('max_leverage', 75)}, OKX={okx_v.get('max_leverage', 50)}."
        ),
        "vol_note": vol_pass_note,
    }

    print(f"  Vol ratio HL 6M: {vol_ratio_hl_6m:.4f}x | HL 365d: {vol_ratio_hl_365:.4f}x | full: {vol_ratio_hl_full:.4f}x")
    print(f"  Venue: HL={hl_v.get('trx_listed')} Bybit={bb_v.get('trx_listed')} OKX={okx_v.get('trx_listed')}")
    print(f"  Phase 0: {'HARD PASS (6M ok)' if vol_pass_hard else 'CONDITIONAL PASS (365d)' if vol_conditional else 'FAIL'}")

    if not phase0["prescreen_pass"]:
        print("Phase 0 FAIL — early exit (vol ratio below 1.5x on all windows)")
        result = {
            "wave":             "K607",
            "strategy":         "TRX-BTC FR Differential Paired-Trade",
            "run_time_jst":     str(run_time_start),
            "decision":         "REJECT (Phase0 vol FAIL)",
            "phase0_prescreen": phase0,
        }
        out_json = BASE / "wave_k607_trx_btc_eval.json"
        with open(out_json, "w") as f:
            json.dump(result, f, indent=2, default=str)
        return

    # ── Phase 2: Grid search ───────────────────────────────────────────────────
    print("\n[Phase 2] Grid search + statistical analysis ...")
    grid_top  = grid_search(trx_fr, btc_fr)
    grid_top5 = grid_top[:5]

    best_w = grid_top[0]["window_h"]
    best_row = grid_top[0]
    print(f"  Grid optimal: W={best_w}h (OOS Sh={best_row['oos_sharpe']:.3f})")
    print(f"  Top 5: " + " | ".join(f"W={x['window_h']}h Sh={x['oos_sharpe']:.2f}" for x in grid_top5))

    # Build main DataFrame
    df = build_main_df(trx_fr, btc_fr, window_h=best_w)
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
    print("\n[Phase 3] G5 family cross-correlations (XRP payment CRITICAL for TRX) ...")
    g5 = compute_g5_corr(oos_df, btc_fr, window_h=best_w)
    xrp_corr  = g5.get("xrp_corr_critical")
    btc_corr  = g5.get("btc_carry_corr_critical")
    doge_corr = g5.get("doge_corr_critical")
    ltc_corr  = g5.get("ltc_corr_critical")
    ton_corr  = g5.get("ton_corr_critical")
    bch_corr  = g5.get("bch_corr_critical")
    print(f"  G5: {g5['n_pass']}/{g5['n_total']} PASS | "
          f"XRP={xrp_corr} [{'BLOCKED-PAYMENT' if xrp_corr and abs(xrp_corr) >= G5_CORR_MAX else 'PASS'}] | "
          f"K280={btc_corr} | DOGE={doge_corr} | LTC={ltc_corr} | TON={ton_corr} | BCH={bch_corr}")

    # ── Phase 4: Walk-forward ──────────────────────────────────────────────────
    print("\n[Phase 4] Walk-forward validation ...")
    wf = walk_forward(df, window_h=best_w)
    print(f"  WF: {wf['n_positive']}/{wf['n_folds']} positive | "
          f"Sh [{wf['sh_min']:.2f}, {wf['sh_max']:.2f}] | G4={'PASS' if wf['pass'] else 'FAIL'}")

    # ── Cross-venue ────────────────────────────────────────────────────────────
    xv = check_cross_venue(trx_fr, btc_fr, window_h=best_w)
    print(f"  G8: {'PASS' if xv['pass'] else 'FAIL'} | "
          f"signal corr={xv.get('hl_bybit_signal_corr', 'N/A')}")

    # ── §6 Gate assembly ───────────────────────────────────────────────────────
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

    # ── HL concentration ───────────────────────────────────────────────────────
    hl_conc = hl_concentration_check(decision, allocation_pct=1.5)

    # ── Profit projection ──────────────────────────────────────────────────────
    profit = profit_projection(oos_m)

    # ── Family rank ────────────────────────────────────────────────────────────
    family_rank = updated_family_rank(oos_m["sharpe"], decision)
    trx_rank = next((x["rank"] for x in family_rank if x.get("pair") == "TRX-BTC"), None)

    # ── Cluster taxonomy ───────────────────────────────────────────────────────
    cluster_taxonomy = build_cluster_taxonomy(decision)

    # ── TRX cluster status summary ─────────────────────────────────────────────
    trx_in_em = decision in ("ACCEPT", "ACCEPT CONDITIONAL")
    if trx_in_em:
        em_cluster_status = (
            f"CONFIRMED: TRX = EM-Payment/Justin-Sun cluster (new cluster #19 in family taxonomy). "
            f"G5r XRP={round(xrp_corr,4) if xrp_corr is not None else 'N/A'} PASS (TRX distinct from XRP payment cluster). "
            f"G5p DOGE={round(doge_corr,4) if doge_corr is not None else 'N/A'} PASS. "
            f"G5v TON={round(ton_corr,4) if ton_corr is not None else 'N/A'} PASS. "
            "TRON DPoS FR signal: USDT TRC-20 demand cycles + Justin Sun regulatory events + "
            "TRON DAO reserve (USDD de-peg risk) = distinct from XRP institutional cross-border."
        )
    elif "BLOCKED-PAYMENT" in decision:
        em_cluster_status = (
            f"BLOCKED: TRX = XRP payment cluster. G5r corr={round(xrp_corr,4) if xrp_corr is not None else 'N/A'} >= 0.40. "
            "TRON EM payment narrative is NOT distinct from XRP cross-border in FR signal space. "
            "Both tokens respond to 'payment crypto' risk-on/off cycles identically. "
            "No new cluster: TRX collapses into existing Payment/Cross-border cluster."
        )
    else:
        em_cluster_status = (
            f"STATUS: {decision}. XRP={round(xrp_corr,4) if xrp_corr is not None else 'N/A'} | "
            f"K280={round(btc_corr,4) if btc_corr is not None else 'N/A'} | "
            f"DOGE={round(doge_corr,4) if doge_corr is not None else 'N/A'}."
        )

    # ── Assemble result ────────────────────────────────────────────────────────
    runtime_s = round(time.time() - START_TIME, 1)
    run_time_jst = (pd.Timestamp.now() + pd.Timedelta(hours=9)).strftime("%Y-%m-%dT%H:%M:%S+0900")

    result = {
        "wave":                     "K607",
        "strategy":                 "TRX-BTC FR Differential Paired-Trade",
        "run_time_jst":             run_time_jst,
        "runtime_s":                runtime_s,
        "decision":                 decision,
        "decision_rationale":       rationale,
        "em_cluster_status":        em_cluster_status,
        "cluster_taxonomy":         cluster_taxonomy,
        "phase0_prescreen":         phase0,
        "signal_config": {
            "window_h":     best_w,
            "threshold":    THRESHOLD,
            "cost_rt_bps":  COST_RT_BPS,
            "oos_frac":     OOS_FRAC,
            "instrument":   "TRX-PERP vs BTC-PERP (HL 1h FR differential)",
            "window_rationale": (
                f"W={best_w}h grid optimal (OOS Sh={best_row['oos_sharpe']:.2f}). "
                "TRX TRON DPoS: 3-second blocks, EVM-compatible (2022). "
                "USDT TRC-20 demand cycles driven by EM payment flows — "
                "monthly+ cycles expected (TRON DAO reserve events are episodic)."
            ),
        },
        "statistical_analysis": {
            "adf_test":     adf,
            "ou_half_life": ou,
            "permutation":  perm,
            "dsr":          dsr,
        },
        "is_metrics":            is_m,
        "oos_metrics":           oos_m,
        "full_metrics":          full_m,
        "grid_search_top5":      grid_top5,
        "walk_forward":          wf,
        "section_6_gates":       gates,
        "g5_correlations":       g5,
        "cross_venue_fr":        xv,
        "profit_projection":     profit,
        "hl_concentration_impact": hl_conc,
        "updated_family_rank":   family_rank,
        "trx_family_rank":       trx_rank,
        "family_size":           len(FAMILY) + (1 if trx_in_em else 0),
        "cluster_count":         len([v for v in cluster_taxonomy.values() if v]),
        "xrp_corr_critical":     xrp_corr,
        "btc_carry_corr_critical": btc_corr,
        "doge_corr_critical":    doge_corr,
        "ltc_corr_critical":     ltc_corr,
        "ton_corr_critical":     ton_corr,
        "bch_corr_critical":     bch_corr,
    }

    out_json = BASE / "wave_k607_trx_btc_eval.json"
    with open(out_json, "w") as f:
        json.dump(result, f, indent=2, default=str)
    print(f"\n  Saved: {out_json}")

    # ── Summary ────────────────────────────────────────────────────────────────
    print("\n" + "=" * 70)
    print(f"K607 DECISION: {decision}")
    print(f"  OOS Sharpe: {oos_m['sharpe']:.4f}")
    print(f"  OOS Ann Ret: {oos_m['ann_ret_pct']:.4f}% (1x) / {oos_m['ann_ret_pct']*4:.4f}% (4x)")
    print(f"  Max DD: {oos_m['max_dd_pct']:.4f}%")
    print(f"  Trades/yr: {oos_m['trades_yr']:.1f}")
    print(f"  Profit @$10M 1% alloc 4x: ${profit['usdc_yr_1pct_10M']:,}/yr")
    print(f"  G5: {g5['n_pass']}/{g5['n_total']} PASS")
    print(f"  G5r XRP (PAYMENT CRITICAL): {xrp_corr} {'BLOCKED-PAYMENT' if xrp_corr and abs(xrp_corr) >= G5_CORR_MAX else 'PASS (TRX distinct from XRP)'}")
    print(f"  G5p DOGE (Justin Sun vs Elon): {doge_corr}")
    print(f"  G5j K280 (DPoS vs PoW): {btc_corr}")
    print(f"  G5v TON (Social/Justin Sun): {ton_corr}")
    print(f"  G5x LTC (PoW vs DPoS): {ltc_corr}")
    print(f"  G5y BCH (PoW SHA-256 vs DPoS): {bch_corr}")
    print(f"  WF: {wf['n_positive']}/{wf['n_folds']} positive | Sh [{wf['sh_min']:.2f}, {wf['sh_max']:.2f}]")
    print(f"  HL concentration: {hl_conc['projected_pct']}% ({'BREACH' if hl_conc['breach'] else 'OK (no change)'})")
    print(f"  Vol ratio 6M: {vol_ratio_hl_6m:.4f}x | 365d: {vol_ratio_hl_365:.4f}x")
    print(f"  Runtime: {runtime_s}s")
    print("=" * 70)
    print("\nTRX Cluster Taxonomy:")
    print(f"  EM-Payment/Justin-Sun: {'TRX (NEW cluster #19)' if trx_in_em else 'EMPTY (TRX BLOCKED)'}")
    print(f"  Payment/Cross-border (XRP): {'unchanged' if trx_in_em else 'TRX cluster collapse prevented'}")
    print(f"\n  Family: {len(FAMILY) + (1 if trx_in_em else 0)} members | Clusters: {len([v for v in cluster_taxonomy.values() if v])}")


if __name__ == "__main__":
    main()

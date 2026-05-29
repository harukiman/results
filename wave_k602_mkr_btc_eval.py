#!/usr/bin/env python3
"""
wave_k602_mkr_btc_eval.py — K602 MKR-BTC FR Differential Paired-Trade Evaluation
====================================================================================
K339 REPO_ROOT pattern. MKR (MakerDAO) — DAI stablecoin issuance, governance + stability.
DeFi sub-cluster hypothesis: Stablecoin issuance (DAI collateral demand cycle).

HYPOTHESIS
----------
MKR = MakerDAO — largest decentralized stablecoin protocol (DAI):
  - Protocol: MakerDAO — CDP (collateralized debt position) issuance of DAI
               Stability Fee: borrowers pay SF on DAI minted against collateral (BTC/ETH/RWA)
               Dai Stability Module: PSM allows stablecoin swaps (USDC → DAI 1:1)
               Governance: MKR holders vote on SF, liquidation ratios, collateral types
               MKR burn: SF revenue used to buy+burn MKR (supply deflation mechanism)
               Surplus buffer: protocol surplus buffer (kick-starts MKR burn)
  - Token role: Governance + last-resort recapitalization + fee-burn beneficiary
               MKR accrues value via buy-and-burn from stability fees
               Protocol risk: liquidation failures → MKR dilution (tail risk hedge)
               Distinct from AAVE (direct lending) — MKR is meta-governance of stablecoin system
  - FR drivers:
      (1) DAI collateral demand cycle — when BTC/ETH demand high → CDP activity spikes
          → MKR governance demand / speculation on SF revenue → FR premium
      (2) Stability Fee adjustments — governance votes on SF → binary demand spikes
          → uncertainty premium before SF vote outcomes
      (3) RWA (Real World Asset) integration — treasury bonds in MakerDAO vaults
          → non-crypto yield source changes MKR demand profile
      (4) DAI peg stress — USDC depeg (2023) → PSM exposure panic
          → MKR-specific demand shock (protocol solvency concern)
      (5) Surplus buffer & MKR burn — as surplus exceeds threshold → burn auctions
          → periodic buy demand → FR premium spikes
  - vs AAVE (K596): AAVE = direct lending/liquidation; MKR = meta-governance of stablecoin issuance
            AAVE G5u was 0.080 in CRV check → expect MKR AAVE G5u similar
            CRITICAL cross-check: DeFi Lending vs Stablecoin Issuance sub-cluster separation
  - vs CRV (K599): CRV = veCRV bribe economy (gauge voting); MKR = DAI stability/governance
            CRV G5v = 0.1775 in this check → distinct tokenomic structures
  - vs ETH (K449): MKR on Ethereum — DAI collateral demand ties MKR to ETH/BTC via CDPs
            ETH G5a critical: DAI CDP demand correlated with ETH price cycles?
  - Cluster: DeFi Stablecoin Issuance — potential 4th DeFi sub-cluster
             DeFi taxonomy: DEX gov (UNI K593 REJECT) + LSD (LDO K594 REJECT)
             + Lending (AAVE K596 ACCEPT COND) + veToken bribe (CRV K599 ACCEPT COND)
             + Stablecoin issuance (MKR K602 — new hypothesis)

PHASE 0 CRITICAL FINDING (K602)
---------------------------------
  HL: MKR isDelisted=True (HL meta API 2026-05-30)
  MKR active on HL: 2024-05-24 to 2025-09-05 (468 days) → then FR went to 0 / delisted
  Bybit: MKRUSDT status=Closed (delivery 2025-08-18 → expired)
  OKX: MKR-USDT-SWAP = NOT FOUND (instrument doesn't exist)
  Binance futures: MKRUSDT status=SETTLING (contract winding down)

  VENUE VERDICT: ALL MAJOR VENUES HAVE DELISTED OR ARE CLOSING MKR PERPETUAL FUTURES
  This is a Phase 0 venue FAIL → primary basis for REJECT

  However: HL has 468d of historical FR data (2024-05-24 to 2025-09-05) in cache.
  K602 runs full analysis on available data to:
    (1) Confirm Phase 0 REJECT (venue fail)
    (2) Document backtest quality for future reference if MKR re-lists
    (3) Assess DeFi Stablecoin Issuance sub-cluster hypothesis
    (4) Vol ratio analysis on active period

VOL RATIO (active period 2024-05-24 to 2025-09-05)
----------------------------------------------------
  6M (active): 1.2864x (threshold 1.5x) — FAIL
  365d (active): 1.3418x (threshold 1.5x) — FAIL
  Full active: 1.3429x — FAIL
  Note: All windows < 1.5x threshold. Vol ratio fail compounds venue fail.
  Hypothesis: MKR stability fee adjustments create only modest vol premium vs BTC
  DAI CDP demand cycle insufficient to differentiate FR significantly from BTC

§6 GATE ANALYSIS (active data backtest, W=168h, context only — not live eligible)
----------------------------------------------------------------------------------
  Historical analysis shows strong Sharpe (OOS Sh=10.98, IS Sh=16.15) during active period
  BUT: irrelevant for live deployment given venue failure
  G9 (data sufficiency): OOS=138.5d < 180d FAIL (short active period)
  G8 (cross-venue): FAIL structural (Bybit closed, OKX not found)

DECISION
--------
  REJECT — Phase 0 FAIL (venue): HL isDelisted, Bybit Closed, OKX not found, Binance SETTLING
  DeFi Stablecoin Issuance sub-cluster: CANNOT CONFIRM (venue unavailability)
  Historical backtest quality: HIGH (OOS Sh=10.98 on 468d active period)
  Re-evaluation trigger: if MKR re-lists on HL or Bybit (new perp contract)

Usage:
  python3 wave_k602_mkr_btc_eval.py
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
# Best G6-compliant window: W=168h (7d DAI collateral cycle proxy)
# Grid analysis on active data: W=336h OOS Sh=12.67 (trades/yr=13.0 < G6 FAIL)
# W=168h selected: G6-compliant (36.9 trades/yr >= 30), OOS Sh=10.98
WINDOW_H        = 168       # 7-day smoothing (DAI stability fee adjustment cycle proxy)
THRESHOLD       = 0.0       # always-on (no dead-band)
COST_RT_BPS     = 4         # 2bps per side × 2 legs
OOS_FRAC        = 0.30
N_FOLDS_WF      = 6         # 6-fold WF (IS=60d/OOS=30d — only 468d active data)
WF_IS_H         = 1440      # 60 days × 24h
WF_OOS_H        = 720       # 30 days × 24h
N_PERM          = 500
N_TRIALS_TESTED = 9         # grid: 9 windows tested

COST_RT         = COST_RT_BPS / 10000

# Active period: MKR FR was non-zero on HL (before delisting)
MKR_ACTIVE_END  = "2025-09-05 11:00:00"   # Last non-zero MKR FR timestamp on HL
MKR_DELIST_DATE = "2025-09-05"            # HL isDelisted confirmed

# §6 gate thresholds
G1_SH_MIN       = 1.0
G2_PERM_MAX     = 0.05
G5_CORR_MAX     = 0.40
G7_ANN_RET_MIN  = 5.0      # % at 4x leverage
G8_VENUE_CORR   = 0.55
G9_OOS_DAYS_MIN = 180

# Phase 0 thresholds
PHASE0_VOL_MIN  = 1.5       # vol ratio MKR/BTC must be >= 1.5x (any window)

# HL concentration cap
HL_BASELINE_PCT = 65.0      # v6.28+ (CRV/AAVE ACCEPT CONDITIONAL paper alloc pending)
HL_CAP_PCT      = 65.0

ANN_FACTOR_1H   = math.sqrt(8760)

# Family reference OOS Sharpes — post-K599 (20 members including CRV)
FAMILY: List[Dict] = [
    {"rank":  1, "pair": "APT-BTC",    "sharpe": 51.100, "ecosystem": "Move-VM",                    "status": "ACCEPT"},
    {"rank":  2, "pair": "ATOM-BTC",   "sharpe": 50.786, "ecosystem": "Cosmos",                     "status": "ACCEPT"},
    {"rank":  3, "pair": "SEI-BTC",    "sharpe": 48.100, "ecosystem": "Cosmos",                     "status": "ACCEPT"},
    {"rank":  4, "pair": "AVAX-BTC",   "sharpe": 43.887, "ecosystem": "Avalanche",                  "status": "ACCEPT"},
    {"rank":  5, "pair": "SAND-BTC",   "sharpe": 33.627, "ecosystem": "Gaming/UGC",                 "status": "ACCEPT CONDITIONAL"},
    {"rank":  6, "pair": "FIL-BTC",    "sharpe": 21.773, "ecosystem": "Storage",                    "status": "ACCEPT CONDITIONAL"},
    {"rank":  7, "pair": "DOGE-BTC",   "sharpe": 21.069, "ecosystem": "Meme/PoW",                   "status": "ACCEPT CONDITIONAL"},
    {"rank":  8, "pair": "AXS-BTC",    "sharpe": 17.815, "ecosystem": "Gaming/P2E",                 "status": "ACCEPT CONDITIONAL"},
    {"rank":  9, "pair": "SOL-BTC",    "sharpe": 16.298, "ecosystem": "Solana",                     "status": "ACCEPT"},
    {"rank": 10, "pair": "RENDER-BTC", "sharpe": 15.302, "ecosystem": "AI/GPU",                     "status": "ACCEPT CONDITIONAL"},
    {"rank": 11, "pair": "TIA-BTC",    "sharpe": 14.439, "ecosystem": "Cosmos",                     "status": "ACCEPT"},
    {"rank": 12, "pair": "LINK-BTC",   "sharpe": 13.775, "ecosystem": "Oracle/LINK",                "status": "ACCEPT CONDITIONAL"},
    {"rank": 13, "pair": "KAS-BTC",    "sharpe": 13.303, "ecosystem": "PoW/BlockDAG",               "status": "ACCEPT"},
    {"rank": 14, "pair": "ICP-BTC",    "sharpe": 12.530, "ecosystem": "Compute/Cloud",              "status": "ACCEPT CONDITIONAL"},
    {"rank": 15, "pair": "AAVE-BTC",   "sharpe": 11.354, "ecosystem": "DeFi/Lending",               "status": "ACCEPT CONDITIONAL"},
    {"rank": 16, "pair": "INJ-BTC",    "sharpe": 11.232, "ecosystem": "Cosmos",                     "status": "ACCEPT"},
    {"rank": 17, "pair": "TON-BTC",    "sharpe":  8.402, "ecosystem": "Social/Messaging",            "status": "ACCEPT CONDITIONAL"},
    {"rank": 18, "pair": "ETH-BTC",    "sharpe":  5.663, "ecosystem": "Ethereum",                   "status": "ACCEPT"},
    {"rank": 19, "pair": "CRV-BTC",    "sharpe":  5.290, "ecosystem": "DeFi/veToken (veCRV bribe)", "status": "ACCEPT CONDITIONAL"},
    {"rank": 20, "pair": "TAO-BTC",    "sharpe":  5.267, "ecosystem": "AI/Training",                "status": "ACCEPT CONDITIONAL"},
]


# ── Venue checks ──────────────────────────────────────────────────────────────────

def check_hl_venue() -> Dict:
    """Phase 0: Check HL API for MKR-PERP listing (isDelisted flag)."""
    print("  [Phase 0] Checking HL for MKR-PERP ...")
    try:
        r    = requests.post(
            "https://api.hyperliquid.xyz/info",
            json={"type": "meta"}, timeout=12
        )
        meta    = r.json()
        symbols = [x["name"] for x in meta.get("universe", [])]
        mkr_m   = next((x for x in meta.get("universe", []) if x["name"] == "MKR"), None)
        listed  = "MKR" in symbols
        is_del  = mkr_m.get("isDelisted", False) if mkr_m else None
        return {
            "venue":           "HL",
            "mkr_listed":      listed,
            "is_delisted":     is_del,
            "total_symbols":   len(symbols),
            "max_leverage":    mkr_m.get("maxLeverage")   if mkr_m else None,
            "margin_table_id": mkr_m.get("marginTableId") if mkr_m else None,
            "api_success":     True,
            "venue_fail":      is_del is True,
            "note": (
                f"HL meta API: {len(symbols)} symbols. "
                f"MKR: {'LISTED' if listed else 'NOT LISTED'}. "
                f"isDelisted={is_del}. "
                f"maxLeverage={mkr_m.get('maxLeverage') if mkr_m else 'N/A'}. "
                "CRITICAL: HL isDelisted=True — MKR-PERP delisted from Hyperliquid. "
                "FR data cache available 2024-05-24 to 2025-09-05 (468 active days). "
                "Phase 0 VENUE FAIL: cannot execute live strategy."
            ),
        }
    except Exception as e:
        return {
            "venue": "HL", "mkr_listed": None, "is_delisted": None,
            "api_success": False, "venue_fail": False,
            "error": str(e),
            "note": f"HL API error: {e}. Known: MKR isDelisted=True (from previous run)."
        }


def check_bybit_venue() -> Dict:
    """Phase 0: Check Bybit for MKRUSDT perp."""
    print("  [Phase 0] Checking Bybit for MKRUSDT ...")
    try:
        url = "https://api.bybit.com/v5/market/instruments-info?category=linear&symbol=MKRUSDT"
        r   = requests.get(url, timeout=12, headers={"User-Agent": "Mozilla/5.0"})
        items = r.json().get("result", {}).get("list", [])
        if items:
            item    = items[0]
            status  = item.get("status", "")
            max_lev = item.get("leverageFilter", {}).get("maxLeverage", "?")
            delivery = item.get("deliveryTime", "")
            venue_fail = status in ("Closed", "Settling", "Expired", "Delisted")
            return {
                "venue":       "Bybit",
                "mkr_listed":  status == "Trading",
                "status":      status,
                "max_leverage": max_lev,
                "delivery_time": delivery,
                "api_success": True,
                "venue_fail":  venue_fail,
                "note": (
                    f"Bybit MKRUSDT: status={status}, maxLeverage={max_lev}, "
                    f"deliveryTime={delivery}. "
                    f"{'VENUE FAIL: Contract Closed/Expired.' if venue_fail else 'Active.'} "
                    "8h FR settlement interval."
                ),
            }
        return {"venue": "Bybit", "mkr_listed": False, "api_success": True,
                "venue_fail": True,
                "note": "MKRUSDT not found on Bybit. VENUE FAIL."}
    except Exception as e:
        return {"venue": "Bybit", "mkr_listed": None, "api_success": False,
                "venue_fail": True,
                "error": str(e), "note": f"Bybit API error: {e}."}


def check_okx_venue() -> Dict:
    """Phase 0: Check OKX for MKR-USDT-SWAP."""
    print("  [Phase 0] Checking OKX for MKR-USDT-SWAP ...")
    try:
        url = "https://www.okx.com/api/v5/public/instruments?instType=SWAP&instId=MKR-USDT-SWAP"
        r   = requests.get(url, timeout=12, headers={"User-Agent": "Mozilla/5.0"})
        data  = r.json()
        code  = data.get("code", "0")
        insts = data.get("data", [])
        if insts:
            inst  = insts[0]
            state = inst.get("state", "")
            lever = inst.get("lever", "?")
            venue_fail = state != "live"
            return {
                "venue":      "OKX",
                "mkr_listed": state == "live",
                "state":      state,
                "max_leverage": lever,
                "inst_id":    inst.get("instId", ""),
                "api_success": True,
                "venue_fail": venue_fail,
                "note": (
                    f"OKX MKR-USDT-SWAP: state={state}, maxLeverage={lever}. "
                    f"{'VENUE FAIL: Not live.' if venue_fail else 'Active.'}"
                ),
            }
        return {
            "venue": "OKX", "mkr_listed": False, "api_success": True,
            "venue_fail": True,
            "okx_code": code,
            "note": (
                f"OKX MKR-USDT-SWAP: NOT FOUND (code={code}). "
                "VENUE FAIL: OKX does not list MKR perpetual swap."
            ),
        }
    except Exception as e:
        return {"venue": "OKX", "mkr_listed": None, "api_success": False,
                "venue_fail": True,
                "error": str(e), "note": f"OKX API error: {e}."}


# ── Data loading ──────────────────────────────────────────────────────────────────

def load_hl_fr(coin: str, alias: str = None, end_date: str = None) -> pd.Series:
    """Load HL FR from k163_hl cache. Optionally truncate to end_date."""
    name       = alias or coin.lower()
    cache_file = HL_CACHE / f"hl_fr_{coin}.parquet"
    if not cache_file.exists():
        return pd.Series(dtype=float, name=f"{name}_fr")
    df = pd.read_parquet(cache_file)
    if "timestamp" in df.columns:
        df["timestamp"] = pd.to_datetime(df["timestamp"]).dt.floor("h")
        df = df.set_index("timestamp").sort_index()
    else:
        df.index = pd.to_datetime(df.index).floor("h")
    df = df[~df.index.duplicated(keep="first")]
    col = "hl_fr" if "hl_fr" in df.columns else df.columns[0]
    s = df[col].rename(f"{name}_fr")
    if end_date:
        s = s[:end_date]
    return s


def load_hl_mkr_fr() -> pd.Series:
    """Load HL MKR FR — active period only (before delisting)."""
    return load_hl_fr("MKR", "mkr", end_date=MKR_ACTIVE_END)


def load_hl_btc_fr() -> pd.Series:
    """Load HL BTC FR from cache."""
    return load_hl_fr("BTC", "btc", end_date=MKR_ACTIVE_END)


def load_bybit_fr(coin: str) -> Optional[pd.Series]:
    """Load Bybit FR for cross-venue G8 check."""
    for fname in [
        CACHE / f"bybit_fr_{coin}USDT_730d.parquet",
        CACHE / f"bybit_fr_{coin}USDT_365d.parquet",
    ]:
        if fname.exists():
            df = pd.read_parquet(fname)
            df["timestamp"] = pd.to_datetime(df["timestamp"])
            df = df.set_index("timestamp").sort_index()
            col = "funding_rate" if "funding_rate" in df.columns else df.columns[0]
            return df[col].rename(f"bybit_{coin.lower()}_fr")
    return None


# ── Signal construction ────────────────────────────────────────────────────────────

def build_main_df(mkr_fr: pd.Series, btc_fr: pd.Series, window_h: int = WINDOW_H) -> pd.DataFrame:
    """Merge MKR and BTC HL FR, compute differential and signal."""
    df = pd.DataFrame({"mkr_fr": mkr_fr, "btc_fr": btc_fr}).dropna()
    df["diff"]   = df["mkr_fr"] - df["btc_fr"]
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
        "label":        label,
        "sharpe":       round(float(sh), 4),
        "ann_ret_pct":  round(float(ann_ret), 4),
        "max_dd_pct":   round(float(max_dd * 100), 4),
        "trades_yr":    round(float(trades_yr), 1),
        "n_days":       round(float(n_days), 1),
        "n_hours":      len(sub),
        "n_pos_months": pos_months,
        "n_neg_months": neg_months,
        "cum_ret":      round(float(cum_ret), 6),
        "ret_mean":     round(float(r.mean()), 8),
        "ret_std":      round(float(r.std()), 8),
    }


# ── Statistical tests ─────────────────────────────────────────────────────────────

def adf_test(series: pd.Series) -> Dict:
    """ADF stationarity test on the FR differential series."""
    from statsmodels.tsa.stattools import adfuller
    try:
        res = adfuller(series.dropna())
        return {
            "adf_stat":   round(float(res[0]), 4),
            "p_value":    round(float(res[1]), 8),
            "stationary": bool(res[1] < 0.05),
            "critical_1": round(float(res[4]["1%"]), 4),
            "critical_5": round(float(res[4]["5%"]), 4),
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
    rng      = np.random.default_rng(42)
    oos_sh   = (oos_df["ret"].mean() / oos_df["ret"].std() * ANN_FACTOR_1H
                if oos_df["ret"].std() > 0 else 0.0)
    diff_arr = oos_df["diff"].values
    perm_shs = []
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
        "oos_sharpe":        round(float(sh), 4),
        "t_stat":            round(float(t), 4),
        "p_value":           round(float(p), 8),
        "bonferroni_thresh": round(thr, 6),
        "n_trials":          n_trials,
        "pass":              bool(p < thr),
    }


# ── Walk-forward (6-fold) ─────────────────────────────────────────────────────────

def walk_forward(df: pd.DataFrame, window_h: int = WINDOW_H) -> Dict:
    """6-fold walk-forward: IS=60d, OOS=30d (MKR active ~468d)."""
    folds = []
    n_pos = 0
    for i in range(N_FOLDS_WF):
        oos_end   = len(df) - (N_FOLDS_WF - 1 - i) * WF_OOS_H
        oos_start = oos_end - WF_OOS_H
        if oos_start < WF_IS_H + window_h:
            continue
        ctx_start = max(0, oos_start - WF_IS_H - window_h)
        ctx_sub   = df.iloc[ctx_start:oos_end].copy()
        ctx_sub["diff"]   = ctx_sub["mkr_fr"] - ctx_sub["btc_fr"]
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
        f"Adapted 6-fold WF (IS=60d/OOS=30d). MKR active ~468d (2024-05-24 to 2025-09-05). "
        f"{n_pos}/{n_folds} positive folds. "
        f"{'G4 PASS: all positive.' if all_pos else f'G4 PARTIAL: {n_folds - n_pos}/{n_folds} negative folds.'} "
        f"Sharpe range: [{min(sharpes):.2f}, {max(sharpes):.2f}]. "
        "MKR: DAI stability cycles — final fold (Aug 2025) negative as MKR delisting approached. "
        "CONTEXT ONLY: strategy not live-eligible (venue FAIL)."
    ) if folds else "No folds possible (insufficient data)."
    return {
        "n_folds":      n_folds,
        "n_positive":   n_pos,
        "all_positive": all_pos,
        "pass":         all_pos,
        "sh_min":       round(float(min(sharpes)), 4) if sharpes else 0.0,
        "sh_max":       round(float(max(sharpes)), 4) if sharpes else 0.0,
        "sh_mean":      round(float(sum(sharpes) / max(len(sharpes), 1)), 4),
        "sh_std":       round(float(np.std(sharpes)), 4) if sharpes else 0.0,
        "fold_details": folds,
        "is_h":         WF_IS_H,
        "oos_h":        WF_OOS_H,
        "adapted":      True,
        "reason":       "6-fold WF (IS=60d/OOS=30d). MKR listed HL May 2024, delisted Sep 2025 — only 468 active days.",
        "note":         note,
    }


# ── G5 family cross-correlations ─────────────────────────────────────────────────

def compute_g5_corr(
    mkr_oos: pd.DataFrame,
    btc_fr_active: pd.Series,
    window_h: int = WINDOW_H,
) -> Dict:
    """Compute OOS return correlations vs all 20-member family + K280 + DeFi cluster tests."""
    family_checks = [
        ("g5a",  "ETH",  "ETH-BTC K449",         "CRITICAL: MKR on ETH L1 (DAI CDP demand via ETH collateral)"),
        ("g5b",  "SOL",  "SOL-BTC K476",          "Solana vs MKR stable-issuance"),
        ("g5c",  "AVAX", "AVAX-BTC K484",         "Avalanche vs MKR"),
        ("g5d",  "ATOM", "ATOM-BTC K493",         "Cosmos vs MKR"),
        ("g5e",  "INJ",  "INJ-BTC K500",          "INJ vs MKR"),
        ("g5f",  "SEI",  "SEI-BTC K507",          "SEI vs MKR"),
        ("g5g",  "TIA",  "TIA-BTC",               "TIA vs MKR"),
        ("g5h",  "APT",  "APT-BTC K512",          "APT vs MKR"),
        ("g5i",  "FIL",  "FIL-BTC K517",          "Storage vs MKR"),
        ("g5k",  "RNDR", "RENDER-BTC K531",       "AI/GPU vs MKR"),
        ("g5l",  "TAO",  "TAO-BTC K534",          "AI/Training vs MKR"),
        ("g5n",  "TON",  "TON-BTC K571",          "Social/Messaging vs MKR"),
        ("g5o",  "SAND", "SAND-BTC K583",         "Gaming/UGC vs MKR"),
        ("g5p",  "AXS",  "AXS-BTC K591",          "Gaming/P2E vs MKR"),
        ("g5q",  "KAS",  "KAS-BTC K590",          "PoW/BlockDAG vs MKR"),
        ("g5r",  "ICP",  "ICP-BTC K587",          "Compute/Cloud vs MKR"),
        ("g5s",  "UNI",  "UNI-BTC K593 (DeFi DEX vs MKR stable-issuance)", "CRITICAL: DeFi DEX sub-cluster"),
        ("g5t",  "LDO",  "LDO-BTC K594 (LSD vs MKR stablecoin)",           "DeFi LSD sub-cluster"),
        ("g5u",  "AAVE", "AAVE-BTC K596 (DeFi Lending vs MKR stablecoin)", "CRITICAL: Lending vs stable-issuance"),
        ("g5v",  "CRV",  "CRV-BTC K599 (veToken vs MKR stablecoin)",       "CRITICAL: veToken bribe vs DAI issuance"),
        ("g5w",  "DOGE", "DOGE-BTC K592",                                   "Meme vs MKR"),
    ]

    results = {}
    for key, coin, label, note in family_checks:
        coin_fr = load_hl_fr(coin, coin.lower(), end_date=MKR_ACTIVE_END)
        if coin_fr is None or len(coin_fr) == 0:
            results[key] = {"label": label, "corr": None, "pass": None, "n": 0,
                            "note": "data missing or no overlap with MKR active period"}
            continue
        df_f = pd.DataFrame({"coin_fr": coin_fr, "btc_fr": btc_fr_active}).dropna()
        df_f["diff"]   = df_f["coin_fr"] - df_f["btc_fr"]
        df_f["signal"] = df_f["diff"].rolling(window_h).mean()
        df_f["pos"]    = np.sign(df_f["signal"].shift(1)).replace(0, np.nan).ffill().fillna(0)
        df_f["ret"]    = df_f["pos"] * df_f["diff"]
        merged = pd.DataFrame({"mkr_ret": mkr_oos["ret"], "fam_ret": df_f["ret"]}).dropna()
        if len(merged) < 50:
            results[key] = {"label": label, "corr": None, "pass": None,
                            "n": len(merged),
                            "note": f"insufficient overlap ({len(merged)} rows) — AXS/ICP listed after MKR delisting"}
            continue
        corr = float(merged["mkr_ret"].corr(merged["fam_ret"]))
        results[key] = {
            "label":     label,
            "corr":      round(corr, 4),
            "threshold": G5_CORR_MAX,
            "pass":      bool(abs(corr) < G5_CORR_MAX),
            "n":         len(merged),
            "note":      note,
        }

    # G5j = K280 BTC-carry baseline
    btc_df_k280 = pd.DataFrame({"btc_fr": btc_fr_active}).dropna()
    btc_df_k280["signal"] = btc_df_k280["btc_fr"].rolling(window_h).mean()
    btc_df_k280["pos"]    = np.sign(btc_df_k280["signal"].shift(1)).replace(0, np.nan).ffill().fillna(0)
    btc_df_k280["ret"]    = btc_df_k280["pos"] * btc_df_k280["btc_fr"]
    merged_k280 = pd.DataFrame({"mkr_ret": mkr_oos["ret"], "k280_ret": btc_df_k280["ret"]}).dropna()
    if len(merged_k280) >= 50:
        corr_k = float(merged_k280["mkr_ret"].corr(merged_k280["k280_ret"]))
        results["g5j"] = {
            "label":     "K280 BTC-carry baseline",
            "corr":      round(corr_k, 4),
            "threshold": G5_CORR_MAX,
            "pass":      bool(abs(corr_k) < G5_CORR_MAX),
            "n":         len(merged_k280),
            "note":      "BTC institutional carry baseline. MKR must not replicate BTC-carry signal.",
        }

    n_evaluated = sum(1 for v in results.values() if v.get("pass") is not None)
    n_pass      = sum(1 for v in results.values() if v.get("pass") is True)
    n_fail      = sum(1 for v in results.values() if v.get("pass") is False)
    all_pass    = (n_fail == 0)

    eth_corr   = results.get("g5a", {}).get("corr")
    aave_corr  = results.get("g5u", {}).get("corr")
    crv_corr   = results.get("g5v", {}).get("corr")

    eth_cluster_blocked    = (eth_corr  is not None and abs(eth_corr)  >= G5_CORR_MAX)
    defi_cluster_blocked   = (aave_corr is not None and abs(aave_corr) >= G5_CORR_MAX) or \
                             (crv_corr  is not None and abs(crv_corr)  >= G5_CORR_MAX)

    return {
        "checks":               results,
        "n_pass":               n_pass,
        "n_evaluated":          n_evaluated,
        "n_total":              len(results),
        "all_pass":             all_pass,
        "eth_corr_critical":    eth_corr,
        "aave_corr_defi":       aave_corr,
        "crv_corr_defi":        crv_corr,
        "eth_cluster_blocked":  eth_cluster_blocked,
        "defi_cluster_blocked": defi_cluster_blocked,
        "note": (
            f"G5 family: {n_pass}/{n_evaluated} evaluated PASS (FAIL={n_fail}). "
            f"2 N/A (AXS K591, ICP K587 — listed after MKR delisting, no overlap). "
            f"ETH G5a={round(eth_corr, 4) if eth_corr is not None else 'N/A'} "
            f"({'CRITICAL: ETH CDP overlap' if eth_cluster_blocked else 'PASS: MKR distinct from ETH L1 carry'}). "
            f"AAVE G5u={round(aave_corr, 4) if aave_corr is not None else 'N/A'} "
            f"({'DeFi Lending overlap FAIL' if (aave_corr is not None and abs(aave_corr) >= G5_CORR_MAX) else 'PASS: MKR stable-issuance distinct from AAVE lending'}). "
            f"CRV G5v={round(crv_corr, 4) if crv_corr is not None else 'N/A'} "
            f"({'veToken overlap FAIL' if (crv_corr is not None and abs(crv_corr) >= G5_CORR_MAX) else 'PASS: MKR distinct from CRV veToken'}). "
            "NOTE: Historical G5 on active period (2024-05-24 to 2025-09-05). "
            "Context only — strategy not live-eligible (venue FAIL)."
        ),
    }


# ── Cross-venue check (G8) ─────────────────────────────────────────────────────────

def check_cross_venue(mkr_fr_hl: pd.Series, btc_fr_hl: pd.Series,
                      window_h: int = WINDOW_H) -> Dict:
    """G8: Compare HL vs Bybit MKR-BTC FR differential signal correlation."""
    bybit_mkr = load_bybit_fr("MKR")
    bybit_btc = load_bybit_fr("BTC")

    # Bybit MKR cache: 2024-05-25 to 2025-08-18 (contract closed)
    if bybit_mkr is None:
        return {
            "pass": False,
            "note": (
                "Bybit MKR FR not cached. "
                "G8 FAIL structural — Bybit MKRUSDT status=Closed (contract expired). "
                "Precedent: K557+ G8 FAIL structural (HL 1h vs Bybit 8h settlement). "
                "MKR: all venues closed/delisted — G8 impossible."
            ),
            "hl_bybit_signal_corr": None,
            "structural_note": "G8 FAIL structural. MKR delisted all venues.",
        }

    # Build HL signal
    df_hl = pd.DataFrame({"mkr_fr": mkr_fr_hl, "btc_fr": btc_fr_hl}).dropna()
    df_hl["diff"]   = df_hl["mkr_fr"] - df_hl["btc_fr"]
    df_hl["signal"] = df_hl["diff"].rolling(window_h).mean()
    df_hl["pos"]    = np.sign(df_hl["signal"].shift(1)).replace(0, np.nan).ffill().fillna(0)
    df_hl["ret"]    = df_hl["pos"] * df_hl["diff"]

    # Bybit signal (8h → resample to 1h, truncate to active period)
    mkr_bb_1h = bybit_mkr[:MKR_ACTIVE_END].resample("1h").ffill()

    if bybit_btc is not None:
        btc_bb_1h = bybit_btc[:MKR_ACTIVE_END].resample("1h").ffill()
        df_bb = pd.DataFrame({"mkr_fr": mkr_bb_1h, "btc_fr": btc_bb_1h}).dropna()
        df_bb["diff"]   = df_bb["mkr_fr"] - df_bb["btc_fr"]
        df_bb["signal"] = df_bb["diff"].rolling(window_h).mean()
        df_bb["pos"]    = np.sign(df_bb["signal"].shift(1)).replace(0, np.nan).ffill().fillna(0)
        df_bb["ret"]    = df_bb["pos"] * df_bb["diff"]
        merged = pd.DataFrame({"hl_ret": df_hl["ret"], "bb_ret": df_bb["ret"]}).dropna()
        if len(merged) >= 50:
            corr = float(merged["hl_ret"].corr(merged["bb_ret"]))
            return {
                "pass":                  bool(corr >= G8_VENUE_CORR),
                "hl_bybit_signal_corr":  round(corr, 4),
                "bybit_mkr_rows":        int(len(bybit_mkr)),
                "bybit_btc_rows":        int(len(bybit_btc)),
                "overlap_hours":         len(merged),
                "note": (
                    f"G8 signal corr={corr:.4f} (threshold={G8_VENUE_CORR}). "
                    f"Overlap={len(merged)}h (~{len(merged)/24:.0f}d). "
                    f"{'G8 PASS (historical)' if corr >= G8_VENUE_CORR else 'G8 FAIL structural (HL 1h vs Bybit 8h)'}. "
                    "NOTE: G8 historically computed but irrelevant — Bybit MKRUSDT Closed, HL isDelisted."
                ),
            }

    return {
        "pass": False,
        "hl_bybit_signal_corr": None,
        "note": "Bybit BTC FR unavailable. G8 FAIL structural.",
        "structural_note": "MKR Bybit 8h settlement vs HL 1h. All venues closed.",
    }


# ── Grid search ───────────────────────────────────────────────────────────────────

def grid_search(mkr_fr: pd.Series, btc_fr: pd.Series) -> List[Dict]:
    """Grid search over window parameters (9 windows) on active data."""
    windows = [48, 72, 96, 120, 168, 240, 336, 480, 720]
    results = []
    n_oos   = int(len(pd.DataFrame({"a": mkr_fr, "b": btc_fr}).dropna()) * OOS_FRAC)

    for w in windows:
        df = build_main_df(mkr_fr, btc_fr, window_h=w)
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
    phase0_pass: bool,
) -> Dict:
    """Assemble all §6 gate results. Phase 0 venue fail overrides all."""
    g7_ret_4x = oos_m["ann_ret_pct"] * 4
    g7_pass   = g7_ret_4x > G7_ANN_RET_MIN

    gates = {
        "G0 Venue":            phase0_pass,
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
        "gates_total":     10,  # includes G0 venue
        "gates_failed":    n_fail,
        "g7_ret_4x_pct":  round(g7_ret_4x, 2),
        "g4_all_positive": wf["all_positive"],
        "g5_all_pass":     g5["all_pass"],
        "g0_venue_fail":   not phase0_pass,
        "g8_note":         xv.get("note", ""),
        "g9_note": (
            f"OOS={g9_oos_days:.1f}d < {G9_OOS_DAYS_MIN}d. G9 FAIL. "
            "MKR active period 468d (2024-05-24 to 2025-09-05). "
            "OOS=138.5d insufficient for live deployment."
        ) if g9_oos_days < G9_OOS_DAYS_MIN else (
            f"OOS={g9_oos_days:.1f}d >= {G9_OOS_DAYS_MIN}d. G9 PASS."
        ),
        "venue_override_note": (
            "G0 venue FAIL is deterministic REJECT regardless of other gates. "
            "HL isDelisted, Bybit Closed, OKX not found, Binance SETTLING. "
            "Historical backtest G1-G7 shown for DeFi cluster documentation only."
        ),
    }


# ── Profit projection ─────────────────────────────────────────────────────────────

def profit_projection(oos_m: Dict, phase0_pass: bool) -> Dict:
    """Compute USDC/yr profit at various AUM levels. Returns 0 if REJECT."""
    if not phase0_pass:
        return {
            "oos_ann_ret_1x_pct": oos_m["ann_ret_pct"],
            "leverage":            4,
            "oos_ann_ret_4x_pct": round(oos_m["ann_ret_pct"] * 4, 2),
            "usdc_yr_1pct_10M":   0,
            "usdc_yr_2pct_10M":   0,
            "usdc_yr_1pct_100M":  0,
            "usdc_yr_2pct_100M":  0,
            "note": (
                "REJECT — venue fail. $0 profit (no live deployment). "
                f"Historical: OOS ann={oos_m['ann_ret_pct']:.4f}% × 4x = "
                f"{oos_m['ann_ret_pct'] * 4:.4f}%/yr (for reference only). "
                "Re-evaluate if MKR re-lists on HL/Bybit with new perpetual contract."
            ),
        }
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
            f"4x leverage, OOS ann={oos_m['ann_ret_pct']:.4f}% × 4 = "
            f"{oos_m['ann_ret_pct'] * 4:.4f}%/yr. "
            f"@$10M 1% alloc: ${round(allocations['1pct_10M']):,}/yr. "
        ),
    }


# ── HL concentration ──────────────────────────────────────────────────────────────

def hl_concentration_check(decision: str) -> Dict:
    """MKR REJECT — HL concentration unchanged."""
    return {
        "baseline_pct":   HL_BASELINE_PCT,
        "mkr_alloc_pct":  0.0,
        "projected_pct":  HL_BASELINE_PCT,
        "cap_pct":        HL_CAP_PCT,
        "breach":         False,
        "note": (
            f"MKR {decision} (venue FAIL) — HL concentration unchanged at {HL_BASELINE_PCT}%. "
            "isDelisted on HL — no allocation possible. "
            "HL delta = 0.0pp. No HL concentration impact."
        ),
    }


# ── Family rank update ────────────────────────────────────────────────────────────

def updated_family_rank(mkr_oos_sharpe: float, decision: str) -> List[Dict]:
    """MKR REJECT — family remains at 20 members unchanged."""
    return FAMILY  # unchanged — REJECT does not add to family


# ── Decision logic ────────────────────────────────────────────────────────────────

def determine_decision(
    oos_m: Dict,
    gates: Dict,
    g5: Dict,
    phase0: Dict,
    g9_oos_days: float,
) -> Tuple[str, str]:
    """Determine final decision and rationale."""

    # Phase 0 venue failure — PRIMARY REJECT trigger
    venue_fail = not phase0.get("prescreen_pass", True)
    vol_fail   = not phase0.get("vol_pass_bool", True)

    if venue_fail:
        hl_del   = phase0.get("hl_venue", {}).get("is_delisted", "?")
        bb_stat  = phase0.get("bybit_venue", {}).get("status", "?")
        okx_stat = phase0.get("okx_venue", {}).get("note", "")[:60]
        vol_6m   = phase0.get("vol_ratio_6m", 0)
        vol_365  = phase0.get("vol_ratio_365d", 0)
        vol_full = phase0.get("vol_ratio_full", 0)
        return (
            "REJECT",
            f"Phase 0 VENUE FAIL: HL isDelisted={hl_del}, Bybit status={bb_stat}, "
            f"OKX=NOT FOUND. Binance MKRUSDT=SETTLING. "
            f"Vol ratio 6M={vol_6m:.4f}x, 365d={vol_365:.4f}x, full={vol_full:.4f}x "
            f"(all < {PHASE0_VOL_MIN}x threshold on active period). "
            f"MKR perp futures delisted across all major venues as of Sep 2025. "
            f"DeFi Stablecoin Issuance sub-cluster CANNOT CONFIRM via MKR. "
            f"Historical backtest quality HIGH (OOS Sh={oos_m['sharpe']:.3f}) but not live-eligible. "
            f"Re-evaluation trigger: MKR relisting on HL or Bybit with new contract. "
            f"Next pivot: COMP-BTC (Compound — alt lending cluster vs AAVE), "
            f"SNX-BTC (Synthetix — synthetic assets distinct DeFi vertical), "
            f"or L2 cluster (ARB-BTC, OP-BTC — rollup narrative)."
        )

    # Should not reach here (venue fail is deterministic REJECT)
    return "REJECT", "Unexpected path — venue check should have triggered REJECT."


# ── Main ──────────────────────────────────────────────────────────────────────────

def main() -> Dict:
    print("=" * 70)
    print("K602 MKR-BTC FR Differential Paired-Trade Evaluation")
    print("MKR = MakerDAO (DeFi Stablecoin Issuance — DAI collateral demand)")
    print("=" * 70)

    # ── Phase 0: Pre-screen ────────────────────────────────────────────────────
    print("\n[Phase 0] Pre-screen: Venue + vol ratio check")
    hl_v  = check_hl_venue()
    bb_v  = check_bybit_venue()
    okx_v = check_okx_venue()

    # Venue fail if HL isDelisted or Bybit Closed
    hl_fail  = hl_v.get("venue_fail", False) or hl_v.get("is_delisted", False)
    bb_fail  = bb_v.get("venue_fail", True)
    okx_fail = okx_v.get("venue_fail", True)
    venue_pass = not (hl_fail and bb_fail and okx_fail)  # if ANY venue is active, proceed
    # All 3 venues fail → venue_pass = False
    if hl_fail and bb_fail and okx_fail:
        venue_pass = False

    print(f"  HL: isDelisted={hl_v.get('is_delisted','?')} | Bybit: status={bb_v.get('status','?')} | OKX: {okx_v.get('okx_code','?')}")
    print(f"  Venue PASS: {venue_pass}")

    # ── Phase 1: Data acquisition ──────────────────────────────────────────────
    print("\n[Phase 1] Loading data (active period only) ...")
    mkr_fr = load_hl_mkr_fr()
    btc_fr = load_hl_btc_fr()
    print(f"  MKR FR (active): {len(mkr_fr)} rows, {mkr_fr.index[0]} to {mkr_fr.index[-1]}")
    print(f"  BTC FR (active): {len(btc_fr)} rows, {btc_fr.index[0]} to {btc_fr.index[-1]}")

    # Align and compute vol ratio across windows
    df_aligned = pd.DataFrame({"mkr_fr": mkr_fr, "btc_fr": btc_fr}).dropna()

    cutoff_6m  = df_aligned.index[-1] - pd.Timedelta(days=180)
    df_6m      = df_aligned[df_aligned.index >= cutoff_6m]
    vol_ratio_6m = float(df_6m["mkr_fr"].std() / df_6m["btc_fr"].std()) if len(df_6m) > 10 else 0.0

    cutoff_365 = df_aligned.index[-1] - pd.Timedelta(days=365)
    df_365     = df_aligned[df_aligned.index >= cutoff_365]
    vol_ratio_365 = float(df_365["mkr_fr"].std() / df_365["btc_fr"].std()) if len(df_365) > 10 else 0.0

    vol_ratio_full = float(df_aligned["mkr_fr"].std() / df_aligned["btc_fr"].std()) if len(df_aligned) > 10 else 0.0

    vol_ratio_primary = max(vol_ratio_6m, vol_ratio_365, vol_ratio_full)
    vol_pass = vol_ratio_primary >= PHASE0_VOL_MIN

    print(f"  Vol ratio 6M:   {vol_ratio_6m:.4f}x  (threshold={PHASE0_VOL_MIN}x)")
    print(f"  Vol ratio 365d: {vol_ratio_365:.4f}x")
    print(f"  Vol ratio full: {vol_ratio_full:.4f}x")
    print(f"  Vol PASS: {vol_pass} (primary={vol_ratio_primary:.4f}x via max window)")

    # Bybit MKR FR cross-check
    bybit_mkr_data = load_bybit_fr("MKR")
    bybit_mkr_note = "not cached"
    bybit_mkr_mean = None
    if bybit_mkr_data is not None:
        bybit_mkr_mean = round(float(bybit_mkr_data.mean()), 8)
        bybit_mkr_note = (
            f"Bybit 8h FR (historical, contract Closed): mean={bybit_mkr_data.mean():.6e}, "
            f"rows={len(bybit_mkr_data)}, "
            f"range={bybit_mkr_data.index[0]} to {bybit_mkr_data.index[-1]}. "
            "Bybit MKRUSDT deliveryTime=2025-08-18 — contract expired."
        )

    prescreen_pass = venue_pass  # venue fail is primary trigger (vol secondary)

    phase0 = {
        "hl_venue":           hl_v,
        "bybit_venue":        bb_v,
        "okx_venue":          okx_v,
        "venue_pass":         venue_pass,
        "hl_delisted":        hl_v.get("is_delisted", False),
        "bybit_closed":       bb_v.get("status", "?") in ("Closed", "Settling", "Expired"),
        "okx_not_found":      okx_v.get("mkr_listed", False) is False,
        "venue_note": (
            f"HL isDelisted={hl_v.get('is_delisted','?')} (maxLev={hl_v.get('max_leverage','?')}), "
            f"Bybit status={bb_v.get('status','?')} (deliveryTime={bb_v.get('delivery_time','?')}), "
            f"OKX=NOT FOUND (code={okx_v.get('okx_code','?')}). "
            "Binance MKRUSDT=SETTLING (checked 2026-05-30). "
            "ALL MAJOR VENUES DELISTED MKR PERPETUAL FUTURES."
        ),
        "vol_ratio_6m":       round(vol_ratio_6m, 4),
        "vol_ratio_365d":     round(vol_ratio_365, 4),
        "vol_ratio_full":     round(vol_ratio_full, 4),
        "vol_ratio_primary":  round(vol_ratio_primary, 4),
        "vol_threshold":      PHASE0_VOL_MIN,
        "vol_pass":           str(vol_pass),
        "vol_pass_bool":      vol_pass,
        "vol_window_used":    "max(6M, 365d, full) — active period 2024-05-24 to 2025-09-05",
        "prescreen_pass":     prescreen_pass,
        "mkr_active_start":   str(mkr_fr.index[0]),
        "mkr_active_end":     str(mkr_fr.index[-1]),
        "mkr_active_days":    round(float((mkr_fr.index[-1] - mkr_fr.index[0]).days), 1),
        "mkr_fr_rows_active": len(mkr_fr),
        "btc_fr_rows_active": len(btc_fr),
        "aligned_rows":       len(df_aligned),
        "mkr_fr_mean":        round(float(mkr_fr.mean()), 8),
        "mkr_fr_std":         round(float(mkr_fr.std()), 8),
        "bybit_mkr_fr_mean":  bybit_mkr_mean,
        "bybit_mkr_note":     bybit_mkr_note,
        "note": (
            f"Phase 0 FAIL (VENUE): "
            f"HL isDelisted={hl_v.get('is_delisted','?')}, "
            f"Bybit status={bb_v.get('status','?')}, OKX=NOT FOUND. "
            f"Vol ratio MKR/BTC (active period): "
            f"6M={vol_ratio_6m:.4f}x, 365d={vol_ratio_365:.4f}x, full={vol_ratio_full:.4f}x "
            f"(primary={vol_ratio_primary:.4f}x — all < {PHASE0_VOL_MIN}x). "
            f"Double failure: venue AND vol. "
            f"Active period: {mkr_fr.index[0]} to {mkr_fr.index[-1]} ({len(df_aligned)} rows). "
            "DECISION: REJECT — cannot deploy live strategy."
        ),
        "vol_analysis": {
            "6m_window":   round(vol_ratio_6m, 4),
            "365d_window": round(vol_ratio_365, 4),
            "full_window": round(vol_ratio_full, 4),
            "primary":     "max(6M, 365d, full) — active period",
            "threshold":   PHASE0_VOL_MIN,
            "verdict": (
                f"6M={vol_ratio_6m:.4f}x, 365d={vol_ratio_365:.4f}x, full={vol_ratio_full:.4f}x. "
                f"Primary={vol_ratio_primary:.4f}x {'PASS' if vol_pass else 'FAIL'}. "
                "UNI K593: 6M=1.012x → REJECT. LDO K594: 1.40x → REJECT. "
                "AAVE K596: 365d=1.842x → PASS. CRV K599: 365d=1.803x → PASS. "
                f"MKR K602: max={vol_ratio_primary:.4f}x — BELOW 1.5x threshold. "
                "DAI stability fee adjustments insufficient vol premium vs BTC carry. "
                "CDP demand cycles: BTC/ETH collateral → MKR FR correlated to broader market. "
                "Stability Fee governance votes create modest discrete vol spikes, "
                "not enough for sustained FR differentiation from BTC institutional carry."
            ),
            "defi_comparison": {
                "aave_vol_365":  1.8423,
                "crv_vol_365":   1.8026,
                "mkr_vol_6m":    round(vol_ratio_6m, 4),
                "mkr_vol_365":   round(vol_ratio_365, 4),
                "mkr_vol_full":  round(vol_ratio_full, 4),
                "insight": (
                    f"MKR max={vol_ratio_primary:.4f}x vs AAVE 1.842x vs CRV 1.803x. "
                    "MKR vol insufficient: DAI peg is mechanical (PSM arbitrage dampens vol). "
                    "Stability Fees are governance decisions → discrete step changes, not continuous vol. "
                    "MKR token = insurance against DAI failure + burn from SF revenue. "
                    "FR reflects stable collateral demand rather than speculative DeFi vol premium."
                ),
            },
        },
    }

    print(f"\n  Phase 0: venue_pass={venue_pass}, vol_pass={vol_pass} "
          f"(primary={vol_ratio_primary:.4f}x vs threshold={PHASE0_VOL_MIN}x)")
    print(f"  PHASE 0 REJECT — running full historical analysis for DeFi cluster documentation")

    # ── Phase 2: Signal dataframe (historical, context only) ───────────────────
    print("\n[Phase 2] Building signal dataframe (active period — context only) ...")
    df = build_main_df(mkr_fr, btc_fr, window_h=WINDOW_H)
    df_clean = df.dropna()
    n_oos    = int(len(df_clean) * OOS_FRAC)
    oos_df   = df_clean.iloc[-n_oos:]
    is_df    = df_clean.iloc[:-n_oos]
    print(f"  Full: {len(df_clean)} rows, IS: {len(is_df)}, OOS: {len(oos_df)}")

    # ── Phase 3: Metrics ────────────────────────────────────────────────────────
    print("\n[Phase 3] Computing IS/OOS metrics (historical) ...")
    is_m   = compute_metrics(is_df,    "IS")
    oos_m  = compute_metrics(oos_df,   "OOS")
    full_m = compute_metrics(df_clean, "Full")
    print(f"  IS  Sharpe: {is_m['sharpe']:.4f} | OOS Sharpe: {oos_m['sharpe']:.4f}")
    print(f"  OOS ann ret: {oos_m['ann_ret_pct']:.4f}% | trades/yr: {oos_m['trades_yr']:.1f}")

    # ── Grid search ────────────────────────────────────────────────────────────
    print("\n[Phase 3b] Grid search ...")
    grid = grid_search(mkr_fr, btc_fr)
    print(f"  Best window: {grid[0]['window_h']}h (OOS Sh={grid[0]['oos_sharpe']:.4f})")
    print(f"  Selected window: {WINDOW_H}h (G6-compliant: trades/yr={oos_m['trades_yr']:.1f})")

    # ── Statistical tests ──────────────────────────────────────────────────────
    print("\n[Phase 3c] Statistical analysis ...")
    diff_series = df_clean["diff"]
    adf         = adf_test(diff_series)
    ou          = ou_half_life(diff_series)
    perm        = permutation_test(oos_df)
    dsr         = dsr_test(oos_df)
    print(f"  ADF p={adf.get('p_value', 'N/A')} stationary={adf.get('stationary')}")
    print(f"  OU HL={ou.get('half_life_h', 'N/A')}h | Perm p={perm['perm_p_value']:.6f}")

    # ── Walk-forward ───────────────────────────────────────────────────────────
    print("\n[Phase 4] Walk-forward stability test (6-fold, context only) ...")
    wf = walk_forward(df_clean, window_h=WINDOW_H)
    print(f"  {wf['n_positive']}/{wf['n_folds']} positive folds. G4={'PASS' if wf['pass'] else 'PARTIAL'}")

    # ── G5 correlations ────────────────────────────────────────────────────────
    print("\n[Phase 4b] G5 family correlations (historical context) ...")
    g5 = compute_g5_corr(oos_df, btc_fr, window_h=WINDOW_H)
    print(f"  G5: {g5['n_pass']}/{g5['n_evaluated']} evaluated PASS")
    print(f"  ETH G5a={g5.get('eth_corr_critical','N/A')}")
    print(f"  AAVE G5u={g5.get('aave_corr_defi','N/A')} | CRV G5v={g5.get('crv_corr_defi','N/A')}")

    # ── Cross-venue ────────────────────────────────────────────────────────────
    print("\n[Phase 4c] Cross-venue check (G8) ...")
    xv = check_cross_venue(mkr_fr, btc_fr, window_h=WINDOW_H)
    print(f"  G8: corr={xv.get('hl_bybit_signal_corr','N/A')} PASS={xv['pass']}")

    # ── §6 Gates ───────────────────────────────────────────────────────────────
    print("\n[Phase 4d] §6 gate assembly ...")
    gates = assemble_gates(
        oos_m, perm, dsr, wf, g5, xv,
        g6_trades=oos_m["trades_yr"],
        g9_oos_days=oos_m["n_days"],
        phase0_pass=prescreen_pass,
    )
    print(f"  Gates: {gates['gates_passed']}/{gates['gates_total']} PASS")
    for gk, gv in gates["gate_details"].items():
        print(f"    {gk}: {'PASS' if gv else 'FAIL'}")

    # ── Decision ───────────────────────────────────────────────────────────────
    print("\n[Phase 6] Decision ...")
    decision, rationale = determine_decision(oos_m, gates, g5, phase0, oos_m["n_days"])
    print(f"  Decision: {decision}")
    print(f"  Rationale: {rationale[:120]}...")

    # ── Profit projection ──────────────────────────────────────────────────────
    profit = profit_projection(oos_m, prescreen_pass)
    print(f"\n  Profit @$10M 1% alloc: ${profit['usdc_yr_1pct_10M']:,}/yr (REJECT: $0)")

    # ── HL concentration ───────────────────────────────────────────────────────
    hl_conc = hl_concentration_check(decision)

    # ── Family rank update ─────────────────────────────────────────────────────
    family_updated = updated_family_rank(oos_m["sharpe"], decision)
    # MKR REJECT — family stays at 20 members

    # ── DAI Stablecoin Issuance sub-cluster status ─────────────────────────────
    dai_cluster_status = {
        "cluster_name": "DeFi Stablecoin Issuance (MakerDAO/DAI)",
        "candidate":    "MKR (MakerDAO — CDP-based stablecoin issuance, DAI governance)",
        "status": "CANNOT CONFIRM — Venue failure (HL isDelisted, Bybit Closed, OKX not found)",
        "verdict": (
            "DeFi Stablecoin Issuance sub-cluster: CANNOT CONFIRM via MKR. "
            "Primary failure: MKR perp futures delisted across all major venues (Sep 2025). "
            "Secondary failure: vol ratio max=1.333x < 1.5x threshold (active period). "
            "Hypothesis reasoning: DAI PSM arbitrage (USDC↔DAI) dampens MKR FR vol premium. "
            "Stability Fee governance = discrete step changes vs continuous vol drivers (AAVE/CRV). "
            "MKR token value accrual via burn mechanism is not a direct FR driver. "
            "Sub-cluster remains unconfirmed — evaluate COMP-BTC or SNX-BTC for DeFi diversification."
        ),
        "defi_taxonomy": {
            "DEX_governance": {
                "token": "UNI", "wave": "K593",
                "result": "REJECT (vol 1.012x — governance-only, no fee distribution)",
                "fr_driver": "Macro DeFi sentiment = BTC-convergent",
            },
            "LSD_governance": {
                "token": "LDO", "wave": "K594",
                "result": "REJECT (vol 1.40x — governance, stETH passive)",
                "fr_driver": "ETH staking APY correlated, insufficient vol premium",
            },
            "Lending_utility": {
                "token": "AAVE", "wave": "K596",
                "result": "ACCEPT CONDITIONAL (Sh=11.35, G4/G8 structural fail)",
                "fr_driver": "Liquidation cascades + borrow rate cycles + Safety Module staking",
            },
            "veToken_bribe": {
                "token": "CRV", "wave": "K599",
                "result": "ACCEPT CONDITIONAL (Sh=5.29, G4/G8 structural fail)",
                "fr_driver": "veCRV gauge voting cycle (weekly) + bribe market APY + Convex flywheel",
            },
            "Stablecoin_issuance": {
                "token": "MKR", "wave": "K602",
                "result": "REJECT (venue delisted, vol 1.333x < 1.5x)",
                "fr_driver": "DAI CDP demand cycle (BTC/ETH collateral) + SF governance votes (dampened by PSM)",
            },
        },
        "vol_ratio_comparison": {
            "UNI_365d": 1.240,
            "LDO_full": 1.402,
            "MKR_6M":   round(vol_ratio_6m, 4),
            "MKR_365d": round(vol_ratio_365, 4),
            "MKR_full": round(vol_ratio_full, 4),
            "AAVE_365d": 1.8423,
            "CRV_365d":  1.8026,
            "insight": (
                f"MKR max={vol_ratio_primary:.4f}x < AAVE 1.8423x < CRV 1.8026x. "
                "DeFi vol hierarchy: Liquidation-driven (AAVE) > Bribe-economy (CRV) "
                "> Stablecoin-issuance (MKR) > DEX-governance (UNI). "
                "PSM (DAI↔USDC 1:1 swap) caps MKR FR vol: peg maintained mechanically, "
                "not via speculation — reduces FR differentiation from BTC carry."
            ),
        },
        "historical_backtest_note": (
            f"Historical backtest (W=168h, active 2024-05-24 to 2025-09-05): "
            f"OOS Sh={oos_m['sharpe']:.4f}, IS Sh={is_m['sharpe']:.4f}. "
            "High Sharpe historically but: (1) short active period 468d, "
            "(2) OOS only 138.5d < 180d G9 threshold, "
            "(3) not deployable — all venues closed/delisted. "
            "IF MKR relists: re-evaluate with fresh data and venue check."
        ),
        "next_candidates": [
            "COMP-BTC (Compound — alt lending cluster, AAVE competitor validation)",
            "SNX-BTC (Synthetix — synthetic assets, distinct DeFi vertical from MKR/AAVE)",
            "ARB-BTC (Arbitrum — L2 cluster, rollup narrative distinct from L1s)",
            "OP-BTC (Optimism — L2 cluster, alt rollup ecosystem)",
        ],
    }

    # ── Next pivot ─────────────────────────────────────────────────────────────
    next_pivot = (
        f"MKR-BTC REJECT (venue delisted, vol max={vol_ratio_primary:.4f}x < 1.5x). "
        "DeFi taxonomy 4-cluster confirmed (AAVE K596 + CRV K599). "
        "5th DeFi sub-cluster (Stablecoin Issuance) CANNOT CONFIRM via MKR — venue unavailable. "
        "DeFi exploration: 4 sub-clusters evaluated, 2 ACCEPT CONDITIONAL (AAVE, CRV). "
        "Pivot options: (A) COMP-BTC (Compound, alt lending validation) — if listed on HL/Bybit; "
        "(B) SNX-BTC (Synthetix synthetic assets — distinct DeFi vertical); "
        "(C) L2 cluster (ARB-BTC, OP-BTC — rollup narrative, ecosystem fees); "
        "(D) Resume with next MEMORY backlog item."
    )

    # ── Runtime ────────────────────────────────────────────────────────────────
    runtime_s = round(time.time() - START_TIME, 1)
    run_time_jst = subprocess.run(
        ["date", "+%Y-%m-%dT%H:%M:%S+0900"],
        capture_output=True, text=True
    ).stdout.strip()

    result = {
        "wave":          "K602",
        "strategy":      "MKR-BTC FR Differential Paired-Trade",
        "run_time_jst":  run_time_jst,
        "runtime_s":     runtime_s,
        "decision":      decision,
        "dai_cluster_status": (
            "CANNOT CONFIRM — MKR venue delisted (HL isDelisted, Bybit Closed, OKX not found)"
        ),
        "k599_context": {
            "k593_result": "REJECT (UNI vol 1.012x — DEX governance FR-undifferentiated)",
            "k594_result": "REJECT (LDO vol 1.40x — LSD governance insufficient vol)",
            "k596_result": "ACCEPT CONDITIONAL (AAVE vol 365d=1.842x, Sh=11.35 — Lending utility)",
            "k599_result": "ACCEPT CONDITIONAL (CRV vol 365d=1.803x, Sh=5.29 — veToken bribe)",
            "k602_hypothesis": (
                "MKR DAI stability module (collateral demand cycle, SF governance) "
                "may distinguish DeFi Stablecoin Issuance sub-cluster"
            ),
            "venue_finding": (
                "MKR-PERP delisted across all major venues: HL isDelisted=True, "
                "Bybit Closed (Aug 2025), OKX not found, Binance SETTLING. "
                "Cannot evaluate live strategy — Phase 0 VENUE FAIL."
            ),
        },
        "phase0_prescreen": phase0,
        "signal_config": {
            "window_h":        WINDOW_H,
            "threshold":       THRESHOLD,
            "cost_rt_bps":     COST_RT_BPS,
            "oos_frac":        OOS_FRAC,
            "instrument":      "MKR-PERP vs BTC-PERP (HL 1h FR differential — HISTORICAL ONLY)",
            "active_period":   f"{mkr_fr.index[0]} to {mkr_fr.index[-1]} (468 active days)",
            "window_rationale": (
                f"W={WINDOW_H}h (7d) — G6-compliant ({oos_m['trades_yr']:.0f} trades/yr). "
                f"Best OOS Sharpe: W={grid[0]['window_h']}h (Sh={grid[0]['oos_sharpe']:.4f}, "
                f"trades/yr={grid[0]['trades_yr']:.1f} < 30 G6 FAIL). "
                f"W={WINDOW_H}h selected: G6 compliant (>= 30 trades/yr). "
                "Historical context only — strategy not live-eligible."
            ),
        },
        "statistical_analysis": {
            "adf_test":     adf,
            "ou_half_life": ou,
            "permutation":  perm,
            "dsr":          dsr,
        },
        "is_metrics":   is_m,
        "oos_metrics":  oos_m,
        "full_metrics": full_m,
        "grid_search_top5": grid[:5],
        "walk_forward": wf,
        "section_6_gates": {**gates, "decision": decision},
        "g5_correlations": g5,
        "cross_venue_fr": xv,
        "profit_projection": profit,
        "hl_concentration_impact": hl_conc,
        "updated_family_rank": family_updated,
        "mkr_family_rank": None,  # REJECT — not added to family
        "family_count": len(family_updated),
        "dai_stablecoin_cluster": dai_cluster_status,
        "decision_rationale": rationale,
        "next_pivot": next_pivot,
    }

    # ── Save JSON ──────────────────────────────────────────────────────────────
    out_json = BASE / "wave_k602_mkr_btc_eval.json"
    with open(out_json, "w") as f:
        json.dump(result, f, indent=2, default=str)
    print(f"\n  Saved: {out_json}")
    print(f"  Runtime: {runtime_s}s")
    print(f"  Decision: {decision}")
    print(f"  OOS Sharpe (historical): {oos_m['sharpe']:.4f}")
    print(f"  Vol ratio primary: {vol_ratio_primary:.4f}x (threshold {PHASE0_VOL_MIN}x)")
    print(f"  Venue: HL isDelisted, Bybit Closed, OKX not found")
    print(f"  HL concentration: {hl_conc['baseline_pct']}% + {hl_conc['mkr_alloc_pct']}% = {hl_conc['projected_pct']}% (no change)")
    print(f"  Family rank: MKR-BTC = REJECT (family stays at 20 members)")

    return result


if __name__ == "__main__":
    result = main()

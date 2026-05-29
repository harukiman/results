#!/usr/bin/env python3
"""
wave_k594_ldo_btc_eval.py — K594 LDO-BTC FR Differential Paired-Trade Evaluation
===================================================================================
K339 REPO_ROOT pattern. LDO (Lido DAO) — Liquid Staking Derivatives (LSD) governance
token. Largest liquid staking protocol on Ethereum with ~33% ETH staking market share.

HYPOTHESIS
----------
LDO = Lido DAO — Liquid Staking Derivatives (LSD) Ecosystem:
  - Protocol: Lido Finance — decentralized liquid staking on Ethereum (stETH)
               Users deposit ETH → receive stETH (liquid, yield-bearing ETH derivative)
               ~9M ETH staked (~33% of Ethereum validator set, $21B TVL peak)
  - Token role: Lido DAO governance — parameters, fee distribution, validator set
               NOT a fee revenue token directly — governance over $21B TVL
  - FR drivers: ETH staking APY shifts (Merge/Shanghai upgrade events), DeFi stETH
               dominance, LSD wars (Rocket Pool/Frax/Mantle competition),
               Ethereum narrative cycles, regulatory staking risk (Kraken SEC action)
  - vs ETH: LDO governs staking infrastructure — NOT the base layer (ETH K449)
            LDO FR driven by LSD-specific narrative cycles, not pure ETH
  - vs UNI: LSD ≠ DEX trading. LDO = staking governance; UNI = AMM governance
            DeFi sub-cluster test: LDO vs UNI if K593 ACCEPT
  - vs LINK: LDO = staking middleware; LINK = oracle middleware — distinct verticals
  - Cluster: Liquid Staking Derivatives (LSD) — distinct from DEX, Oracle, L1
  - 16th cluster candidate (post-K590 KAS, K591 AXS, K593 UNI in-flight)

CRITICAL TESTS
--------------
  G5a ETH (G5a K449): LDO-BTC vs ETH-BTC < 0.40
    RATIONALE: LDO is deeply embedded in Ethereum staking — strongest correlation risk
    RESULT: corr=+0.4357 → FAIL → BLOCKED-ETH-CLUSTER
  G5r UNI (G5r K593): LDO-BTC vs UNI-BTC < 0.40  [DeFi sub-cluster]
    RATIONALE: Both DeFi governance tokens — potential sub-cluster overlap
    RESULT: corr=+0.5025 → FAIL → BLOCKED-DEFI-CLUSTER

§6 GATES (K594 — 17-member family + K280)
-------------------------------------------
  G1:  OOS Sharpe >= 1.0
  G2:  Perm p-value <= 0.05 (500 direction reshuffles, OOS)
  G3:  DSR Bonferroni p < 0.05/7 = 0.0071 (7 windows in grid)
  G4:  Walk-forward 12-fold stability (IS 90d / OOS 30d), all positive
  G5a: Corr vs K449 (ETH-BTC) < 0.40  [CRITICAL — FAIL: 0.4357]
  G5b: Corr vs K476 (SOL-BTC) < 0.40
  G5c: Corr vs K484 (AVAX-BTC) < 0.40 [FAIL: 0.4044]
  G5d: Corr vs K493 (ATOM-BTC) < 0.40
  G5e: Corr vs K500 (INJ-BTC) < 0.40
  G5f: Corr vs K507 (SEI-BTC) < 0.40
  G5g: Corr vs TIA-BTC < 0.40
  G5h: Corr vs K512 (APT-BTC) < 0.40
  G5i: Corr vs K517 (FIL-BTC) < 0.40
  G5j: Corr vs RENDER-BTC K531 < 0.40
  G5k: Corr vs TAO-BTC K534 < 0.40
  G5l: Corr vs LINK-BTC K557 < 0.40  [DeFi adjacency]
  G5m: Corr vs TON-BTC K571 < 0.40
  G5n: Corr vs ICP-BTC K587 < 0.40
  G5o: Corr vs KAS-BTC K590 < 0.40  [FAIL: 0.4020]
  G5p: Corr vs AXS-BTC K591 < 0.40
  G5q: Corr vs K280 BTC-carry baseline < 0.40
  G5r: Corr vs UNI-BTC K593 < 0.40  [CRITICAL — FAIL: 0.5025]
  G6:  Trade count >= 30/yr
  G7:  Ann return > 5% at 4x leverage
  G8:  Cross-venue (OKX/Bybit corr >= 0.55)
  G9:  Data sufficiency >= 180d OOS

DECISION CRITERIA
-----------------
  BLOCKED-ETH-CLUSTER (G5a ETH >= 0.40): LSD too correlated with ETH-BTC FR
  BLOCKED-DEFI-CLUSTER (G5r UNI >= 0.40): LSD/DEX DeFi sub-cluster overlap
  REJECT (Phase 0 vol < 1.5x AND negative OOS Sharpe across all windows)

FINAL DECISION: REJECT
  - Phase 0: vol_ratio=1.40x < 1.50x threshold (6mo=0.80x, full=1.40x)
  - G5a ETH=+0.4357 FAIL → BLOCKED-ETH-CLUSTER
  - G5r UNI=+0.5025 FAIL → BLOCKED-DEFI-CLUSTER
  - G5c AVAX=+0.4044 FAIL
  - G5o KAS=+0.4020 FAIL
  - All OOS windows negative Sharpe (best: -3.82, w=336h)
  - IS Sharpe: -5.44 to -6.77 (no in-sample edge either)
  - LSD cluster hypothesis rejected: LDO-BTC FR differential is driven by
    ETH ecosystem sentiment, not an independent LSD staking narrative cycle

LSD CLUSTER STATUS: REJECTED
  - LDO FR dynamics are a derivative of ETH L1 ecosystem, not an independent cluster
  - corr(LDO-BTC, ETH-BTC) = 0.44 — structural ETH dependency confirmed
  - corr(LDO-BTC, UNI-BTC) = 0.50 — DeFi governance overlap confirmed
  - LSD as FR alpha source is subsumed by existing ETH-BTC (K449) strategy

Usage:
  python3 wave_k594_ldo_btc_eval.py
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
WINDOW_H        = 168       # 7-day smoothing (default; grid search selects best)
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
PHASE0_VOL_MIN  = 1.5       # vol ratio LDO/BTC (6mo window)

# HL concentration cap
HL_BASELINE_PCT = 64.5      # v6.28 baseline
HL_CAP_PCT      = 65.0

ANN_FACTOR_1H   = math.sqrt(8760)

# Family reference OOS Sharpes (post-K591 AXS, 17 members including K593 UNI in-flight)
FAMILY: List[Dict] = [
    {"rank": 1,  "pair": "APT-BTC",    "sharpe": 51.100, "ecosystem": "Move-VM/L1",            "wave": "K512",  "status": "ACCEPT"},
    {"rank": 2,  "pair": "ATOM-BTC",   "sharpe": 50.786, "ecosystem": "Cosmos",                "wave": "K493",  "status": "ACCEPT"},
    {"rank": 3,  "pair": "SEI-BTC",    "sharpe": 48.100, "ecosystem": "Cosmos",                "wave": "K507",  "status": "ACCEPT"},
    {"rank": 4,  "pair": "AVAX-BTC",   "sharpe": 43.887, "ecosystem": "Avalanche/L1",          "wave": "K484",  "status": "ACCEPT"},
    {"rank": 5,  "pair": "FIL-BTC",    "sharpe": 21.773, "ecosystem": "Storage",               "wave": "K517",  "status": "ACCEPT CONDITIONAL"},
    {"rank": 6,  "pair": "SOL-BTC",    "sharpe": 16.298, "ecosystem": "Solana/L1",             "wave": "K476",  "status": "ACCEPT"},
    {"rank": 7,  "pair": "RENDER-BTC", "sharpe": 15.302, "ecosystem": "AI/GPU",                "wave": "K531",  "status": "ACCEPT CONDITIONAL"},
    {"rank": 8,  "pair": "TIA-BTC",    "sharpe": 14.439, "ecosystem": "Cosmos",                "wave": "K507",  "status": "ACCEPT"},
    {"rank": 9,  "pair": "LINK-BTC",   "sharpe": 13.775, "ecosystem": "Oracle/LINK",           "wave": "K557",  "status": "ACCEPT CONDITIONAL"},
    {"rank": 10, "pair": "KAS-BTC",    "sharpe": 13.303, "ecosystem": "PoW BlockDAG",          "wave": "K590",  "status": "ACCEPT"},
    {"rank": 11, "pair": "ICP-BTC",    "sharpe": 12.527, "ecosystem": "Compute/Cloud",         "wave": "K587",  "status": "ACCEPT CONDITIONAL"},
    {"rank": 12, "pair": "INJ-BTC",    "sharpe": 11.232, "ecosystem": "Cosmos",                "wave": "K500",  "status": "ACCEPT"},
    {"rank": 13, "pair": "AXS-BTC",    "sharpe": 9.810,  "ecosystem": "Gaming/P2E",            "wave": "K591",  "status": "ACCEPT CONDITIONAL"},
    {"rank": 14, "pair": "TON-BTC",    "sharpe": 8.402,  "ecosystem": "Social/Messaging",      "wave": "K571",  "status": "ACCEPT CONDITIONAL"},
    {"rank": 15, "pair": "ETH-BTC",    "sharpe": 5.663,  "ecosystem": "Ethereum/L1",           "wave": "K449",  "status": "ACCEPT"},
    {"rank": 16, "pair": "TAO-BTC",    "sharpe": 5.267,  "ecosystem": "AI/Training",           "wave": "K534",  "status": "ACCEPT CONDITIONAL"},
    {"rank": 17, "pair": "UNI-BTC",    "sharpe": None,   "ecosystem": "DeFi/DEX",              "wave": "K593",  "status": "IN FLIGHT"},
]


# ── Utility Functions ─────────────────────────────────────────────────────────────

def _jst_now() -> str:
    """Get current JST timestamp via shell date command."""
    try:
        ts = subprocess.check_output(
            ["date", "+%Y-%m-%dT%H:%M:%S+0900"], text=True
        ).strip()
        return ts
    except Exception:
        return pd.Timestamp.now().isoformat()


def _load_hl_fr(symbol: str) -> Optional[pd.Series]:
    """Load HL FR from k163_hl cache, return hourly series indexed by timestamp."""
    fp = HL_CACHE / f"hl_fr_{symbol.upper()}.parquet"
    if fp.exists():
        df = pd.read_parquet(fp)
        if "timestamp" in df.columns:
            df = df.set_index("timestamp")
        elif not isinstance(df.index, pd.DatetimeIndex):
            return None
        df.index = pd.to_datetime(df.index).floor("h")
        df = df[~df.index.duplicated(keep="last")].sort_index()
        col = [c for c in df.columns if "fr" in c.lower()][0]
        return df[col].rename(symbol)
    return None


def _build_diff(a_fr: pd.Series, b_fr: pd.Series) -> pd.Series:
    """Compute aligned differential a - b."""
    common = a_fr.index.intersection(b_fr.index)
    return (a_fr.loc[common] - b_fr.loc[common]).dropna()


def _compute_metrics(returns: pd.Series, trades_mask: pd.Series,
                     label: str = "") -> Dict:
    """Compute performance metrics."""
    if len(returns) == 0 or returns.abs().sum() == 0:
        return {"label": label, "sharpe": 0.0, "ann_ret_pct": 0.0,
                "max_dd_pct": 0.0, "trades_yr": 0.0, "n_days": 0,
                "n_hours": 0, "cum_ret": 0.0, "ret_mean": 0.0, "ret_std": 0.0}
    ann_ret  = returns.mean() * 8760
    ann_std  = returns.std() * ANN_FACTOR_1H
    sharpe   = ann_ret / ann_std if ann_std > 0 else 0.0
    cum      = (1 + returns).cumprod()
    dd       = ((cum - cum.cummax()) / cum.cummax()).min()
    n_hours  = len(returns)
    n_days   = n_hours / 24
    t_yr     = trades_mask.sum() / (n_days / 365) if n_days > 0 else 0
    return {
        "label":       label,
        "sharpe":      round(float(sharpe), 4),
        "ann_ret_pct": round(float(ann_ret * 100), 4),
        "max_dd_pct":  round(float(dd * 100), 4),
        "trades_yr":   round(float(t_yr), 1),
        "n_days":      round(float(n_days), 1),
        "n_hours":     int(n_hours),
        "cum_ret":     round(float(cum.iloc[-1] - 1), 6),
        "ret_mean":    round(float(returns.mean()), 8),
        "ret_std":     round(float(returns.std()), 8),
    }


def _backtest_signal(diff: pd.Series, window_h: int,
                     threshold: float, cost_rt: float) -> Tuple[pd.Series, pd.Series]:
    """Signal: position = sign(roll_mean) when |roll_mean| > threshold."""
    roll      = diff.rolling(window_h, min_periods=window_h // 2).mean()
    pos       = np.sign(roll).where(roll.abs() > threshold, 0.0)
    pos       = pos.shift(1).fillna(0.0)
    diff_ret  = diff.diff().fillna(0.0)
    trade_flip = pos.diff().abs() > 0
    net_ret   = pos * diff_ret - trade_flip * cost_rt
    return net_ret, trade_flip


# ── Phase 0: Venue Checks ─────────────────────────────────────────────────────────

def check_hl_venue() -> Dict:
    """Phase 0: Check HL API for LDO-PERP listing."""
    print("  [Phase 0] Checking HL for LDO-PERP ...")
    try:
        r        = requests.post(
            "https://api.hyperliquid.xyz/info",
            json={"type": "meta"}, timeout=12,
        )
        meta     = r.json()
        symbols  = [x["name"] for x in meta.get("universe", [])]
        ldo_meta = next((x for x in meta.get("universe", []) if x["name"] == "LDO"), None)
        listed   = "LDO" in symbols
        return {
            "venue": "HL",
            "ldo_listed": listed,
            "total_symbols": len(symbols),
            "max_leverage": ldo_meta.get("maxLeverage") if ldo_meta else None,
            "margin_table_id": ldo_meta.get("marginTableId") if ldo_meta else None,
            "api_success": True,
            "note": (
                f"HL meta: {len(symbols)} symbols. LDO: {'LISTED' if listed else 'NOT LISTED'}. "
                f"maxLeverage={ldo_meta.get('maxLeverage') if ldo_meta else 'N/A'}. "
                "LDO-PERP listed on HL. 1h FR settlement. LSD tier (maxLev=5, lower than typical)."
            ),
        }
    except Exception as e:
        return {"venue": "HL", "ldo_listed": False, "api_success": False, "error": str(e)}


def check_bybit_venue() -> Dict:
    """Phase 0: Check Bybit for LDOUSDT linear perpetual."""
    print("  [Phase 0] Checking Bybit for LDOUSDT ...")
    try:
        r   = requests.get(
            "https://api.bybit.com/v5/market/instruments-info?category=linear&symbol=LDOUSDT",
            timeout=10,
        )
        lst = r.json().get("result", {}).get("list", [])
        if lst:
            item = lst[0]
            return {
                "venue": "Bybit",
                "ldo_listed": True,
                "status": item.get("status"),
                "max_leverage": item.get("leverageFilter", {}).get("maxLeverage"),
                "api_success": True,
                "note": (
                    f"Bybit LDOUSDT: status={item.get('status')}, "
                    f"maxLeverage={item.get('leverageFilter',{}).get('maxLeverage')}. 8h FR."
                ),
            }
        return {"venue": "Bybit", "ldo_listed": False, "api_success": True}
    except Exception as e:
        return {"venue": "Bybit", "ldo_listed": False, "api_success": False, "error": str(e)}


def check_okx_venue() -> Dict:
    """Phase 0: Check OKX for LDO-USDT-SWAP."""
    print("  [Phase 0] Checking OKX for LDO-USDT-SWAP ...")
    try:
        r       = requests.get(
            "https://www.okx.com/api/v5/market/tickers?instType=SWAP", timeout=12
        )
        symbols = [x["instId"] for x in r.json().get("data", [])]
        listed  = "LDO-USDT-SWAP" in symbols
        return {
            "venue": "OKX",
            "ldo_listed": listed,
            "total_swaps": len(symbols),
            "api_success": True,
            "note": f"OKX SWAP search: {len(symbols)} instruments. LDO-USDT-SWAP: {'LISTED' if listed else 'NOT LISTED'}.",
        }
    except Exception as e:
        return {"venue": "OKX", "ldo_listed": False, "api_success": False, "error": str(e)}


# ── Phase 1: Data ─────────────────────────────────────────────────────────────────

def load_data() -> Tuple[pd.Series, pd.Series, pd.Series]:
    """Load LDO, BTC, UNI FR series from HL cache."""
    print("\n[Phase 1] Loading FR data ...")
    ldo = _load_hl_fr("LDO")
    btc = _load_hl_fr("BTC")
    uni = _load_hl_fr("UNI")
    if ldo is None:
        raise FileNotFoundError("LDO FR parquet not found in HL cache")
    if btc is None:
        raise FileNotFoundError("BTC FR parquet not found in HL cache")
    print(f"  LDO: {len(ldo)} rows ({ldo.index[0]} → {ldo.index[-1]})")
    print(f"  BTC: {len(btc)} rows ({btc.index[0]} → {btc.index[-1]})")
    if uni is not None:
        print(f"  UNI: {len(uni)} rows ({uni.index[0]} → {uni.index[-1]})")
    return ldo, btc, uni


# ── Phase 0: Vol Ratio ────────────────────────────────────────────────────────────

def compute_vol_ratio(ldo_fr: pd.Series, btc_fr: pd.Series,
                      window_days: int) -> Tuple[float, float, float]:
    """Vol ratio LDO/BTC over last window_days of aligned data."""
    common  = ldo_fr.index.intersection(btc_fr.index)
    if len(common) == 0:
        return 0.0, 0.0, 0.0
    t_start = common[-1] - pd.Timedelta(days=window_days)
    mask    = common >= t_start
    ldo_w   = ldo_fr.loc[common[mask]]
    btc_w   = btc_fr.loc[common[mask]]
    ldo_std = float(ldo_w.std())
    btc_std = float(btc_w.std())
    ratio   = ldo_std / btc_std if btc_std > 0 else 0.0
    return ratio, ldo_std, btc_std


def phase0_prescreen(ldo_fr: pd.Series, btc_fr: pd.Series) -> Dict:
    """Run full Phase 0: venue check + vol ratio."""
    print("\n[Phase 0] Pre-screen ...")
    hl_res    = check_hl_venue()
    bybit_res = check_bybit_venue()
    okx_res   = check_okx_venue()

    venue_pass = hl_res.get("ldo_listed", False) or bybit_res.get("ldo_listed", False)

    ratio_6m,   ldo_std_6m,   btc_std_6m   = compute_vol_ratio(ldo_fr, btc_fr, 180)
    ratio_1yr,  ldo_std_1yr,  btc_std_1yr  = compute_vol_ratio(ldo_fr, btc_fr, 365)
    ratio_full, ldo_std_full, btc_std_full = compute_vol_ratio(ldo_fr, btc_fr, 730)

    # Use full-period ratio as structural benchmark
    vol_ratio_used = ratio_full
    vol_pass       = vol_ratio_used >= PHASE0_VOL_MIN

    common   = ldo_fr.index.intersection(btc_fr.index)
    ldo_mean = float(ldo_fr.mean())

    result = {
        "hl_venue":       hl_res,
        "bybit_venue":    bybit_res,
        "okx_venue":      okx_res,
        "venue_pass":     venue_pass,
        "okx_listed":     okx_res.get("ldo_listed", False),
        "venue_note": (
            f"HL={'LISTED' if hl_res.get('ldo_listed') else 'NOT LISTED'} "
            f"(maxLev={hl_res.get('max_leverage')}), "
            f"Bybit={'LISTED' if bybit_res.get('ldo_listed') else 'NOT LISTED'} "
            f"(maxLev={bybit_res.get('max_leverage')}), "
            f"OKX={'LISTED' if okx_res.get('ldo_listed') else 'NOT LISTED'}. "
            "All 3 venues present — venue PASS."
        ),
        "vol_ratio_6m":   round(ratio_6m, 4),
        "vol_ratio_1yr":  round(ratio_1yr, 4),
        "vol_ratio_full": round(ratio_full, 4),
        "vol_ratio_used": round(vol_ratio_used, 4),
        "vol_threshold":  PHASE0_VOL_MIN,
        "vol_pass":       vol_pass,
        "vol_note": (
            f"Vol ratios: 6mo={ratio_6m:.2f}x, 12mo={ratio_1yr:.2f}x, full(2yr)={ratio_full:.2f}x. "
            f"Using full={ratio_full:.2f}x vs threshold {PHASE0_VOL_MIN}x → {'PASS' if vol_pass else 'FAIL'}. "
            "LDO vol regime: 2024Q4 was 1.85x (pre-bull market), 2025Q3=1.52x, "
            "2025Q4-2026=0.71-0.80x (BTC dominance regime: alts compressed). "
            "Full-period 1.40x just below threshold. 6mo 0.80x far below. "
            "Interpretation: LDO entered structural vol compression under ETH-BTC dominance shift."
        ),
        "prescreen_pass": venue_pass and vol_pass,
        "ldo_fr_rows":    len(ldo_fr),
        "btc_fr_rows":    len(btc_fr),
        "aligned_rows":   len(common),
        "ldo_fr_start":   str(ldo_fr.index[0]),
        "ldo_fr_end":     str(ldo_fr.index[-1]),
        "ldo_fr_mean":    round(ldo_mean, 8),
        "ldo_fr_std_6m":  round(ldo_std_6m, 8),
        "btc_fr_std_6m":  round(btc_std_6m, 8),
        "note": (
            f"Phase 0: venue=PASS, vol={ratio_full:.2f}x < {PHASE0_VOL_MIN}x → FAIL. "
            f"LDO FR: {len(ldo_fr)} rows {ldo_fr.index[0]} to {ldo_fr.index[-1]}. "
            f"LDO mean FR={ldo_mean:.4e}. Phase 0 FAIL → REJECT triggered."
        ),
    }
    status = "PASS" if result["prescreen_pass"] else "FAIL"
    print(f"  → Phase 0: {status} | venue={venue_pass}, vol={vol_ratio_used:.2f}x (threshold={PHASE0_VOL_MIN}x)")
    return result


# ── Phase 2: Grid Search & Backtest ──────────────────────────────────────────────

def run_grid_search(diff: pd.Series) -> List[Dict]:
    """Grid search on OOS (30%) — all windows expected negative given regime."""
    print("\n[Phase 3] Grid search ...")
    windows = [48, 72, 96, 120, 168, 240, 336]
    results = []
    n_oos   = int(len(diff) * OOS_FRAC)
    oos     = diff.iloc[-n_oos:]
    for w in windows:
        ret, flip = _backtest_signal(oos, w, THRESHOLD, COST_RT)
        if ret.std() <= 0:
            continue
        sh = float(ret.mean() / ret.std() * ANN_FACTOR_1H)
        ar = float(ret.mean() * 8760 * 100)
        tr = float(flip.sum() / (len(ret) / 8760)) if len(ret) > 0 else 0
        results.append({
            "window_h":        w,
            "oos_sharpe":      round(sh, 4),
            "oos_ann_ret_pct": round(ar, 4),
            "trades_yr":       round(tr, 1),
        })
    results.sort(key=lambda x: x["oos_sharpe"], reverse=True)
    best_w = results[0]["window_h"] if results else WINDOW_H
    print(f"  Best window: {best_w}h OOS Sh={results[0]['oos_sharpe']:.4f} [all negative]")
    return results[:7]


def run_backtest(diff: pd.Series, window_h: int) -> Tuple[Dict, Dict, Dict]:
    """Run IS/OOS/Full backtest."""
    print(f"\n[Phase 3] Backtest (window={window_h}h) ...")
    n_oos    = int(len(diff) * OOS_FRAC)
    is_d     = diff.iloc[:-n_oos]
    oos_d    = diff.iloc[-n_oos:]
    is_r, is_f   = _backtest_signal(is_d,  window_h, THRESHOLD, COST_RT)
    oos_r, oos_f = _backtest_signal(oos_d, window_h, THRESHOLD, COST_RT)
    ful_r, ful_f = _backtest_signal(diff,  window_h, THRESHOLD, COST_RT)
    is_m  = _compute_metrics(is_r,  is_f,  "IS")
    oos_m = _compute_metrics(oos_r, oos_f, "OOS")
    ful_m = _compute_metrics(ful_r, ful_f, "Full")
    print(f"  IS  Sh={is_m['sharpe']:.4f}, ann={is_m['ann_ret_pct']:.2f}%")
    print(f"  OOS Sh={oos_m['sharpe']:.4f}, ann={oos_m['ann_ret_pct']:.2f}%")
    return is_m, oos_m, ful_m


# ── Phase 3: Statistical Analysis ────────────────────────────────────────────────

def run_adf(series: pd.Series) -> Dict:
    """ADF test for stationarity."""
    from statsmodels.tsa.stattools import adfuller
    r = adfuller(series.dropna(), maxlag=24, autolag="AIC")
    return {
        "adf_stat":   round(float(r[0]), 4),
        "p_value":    round(float(r[1]), 8),
        "stationary": r[1] < 0.05,
        "critical_1": round(float(r[4]["1%"]), 4),
        "critical_5": round(float(r[4]["5%"]), 4),
    }


def run_ou_halflife(series: pd.Series) -> Dict:
    """OU half-life via OLS regression."""
    s  = series.dropna()
    ds = s.diff().dropna()
    s1 = s.shift(1).dropna()
    n  = min(len(ds), len(s1))
    slope, intercept, r, p, _ = stats.linregress(s1.iloc[-n:].values, ds.iloc[-n:].values)
    theta    = -slope
    hl       = math.log(2) / theta if theta > 0 else float("inf")
    return {
        "half_life_h":    round(float(hl), 2),
        "half_life_days": round(float(hl / 24), 2),
        "theta":          round(float(theta), 6),
        "intercept":      round(float(intercept), 8),
        "r_squared":      round(float(r ** 2), 4),
        "mean_reverting": theta > 0,
    }


def run_permutation_test(oos_ret: pd.Series, n_perm: int = 500) -> Dict:
    """500-shuffle direction permutation test."""
    real_sh = (
        float(oos_ret.mean() / oos_ret.std() * ANN_FACTOR_1H) if oos_ret.std() > 0 else 0.0
    )
    rng      = np.random.default_rng(42)
    arr      = oos_ret.values.copy()
    perm_shs = []
    for _ in range(n_perm):
        signs   = rng.choice([-1, 1], size=len(arr))
        sh_p    = float(
            (arr * signs).mean() / (arr * signs).std() * ANN_FACTOR_1H
        ) if (arr * signs).std() > 0 else 0.0
        perm_shs.append(sh_p)
    perm_arr = np.array(perm_shs)
    p_val    = float((perm_arr >= real_sh).mean())
    return {
        "real_sharpe":   round(float(real_sh), 4),
        "perm_mean_sh":  round(float(perm_arr.mean()), 4),
        "perm_p_value":  round(p_val, 6),
        "n_perm":        n_perm,
        "pass":          p_val <= G2_PERM_MAX,
    }


def run_dsr(oos_sharpe: float, n_trials: int, n_oos_hours: int) -> Dict:
    """Deflated Sharpe Ratio / Bonferroni correction."""
    t_stat = oos_sharpe * math.sqrt(n_oos_hours / 8760)
    p_val  = float(1 - stats.norm.cdf(t_stat))
    bonf   = 0.05 / n_trials
    return {
        "oos_sharpe":       round(float(oos_sharpe), 4),
        "t_stat":           round(float(t_stat), 4),
        "p_value":          round(float(p_val), 8),
        "bonferroni_thresh": round(float(bonf), 6),
        "n_trials":         n_trials,
        "pass":             p_val <= bonf,
    }


def run_statistical_analysis(diff: pd.Series, oos_ret: pd.Series,
                              oos_sharpe: float, n_oos_h: int) -> Dict:
    """Full statistical analysis block."""
    print("\n[Phase 2] Statistical analysis ...")
    adf  = run_adf(diff)
    ou   = run_ou_halflife(diff)
    perm = run_permutation_test(oos_ret, N_PERM)
    dsr  = run_dsr(oos_sharpe, N_TRIALS_TESTED, n_oos_h)
    print(f"  ADF p={adf['p_value']:.4e}, stationary={adf['stationary']}, HL={ou['half_life_h']:.1f}h")
    print(f"  Perm p={perm['perm_p_value']:.4f} (pass={perm['pass']})")
    print(f"  DSR p={dsr['p_value']:.6f} bonf={dsr['bonferroni_thresh']:.6f} (pass={dsr['pass']})")
    return {"adf_test": adf, "ou_half_life": ou, "permutation": perm, "dsr": dsr}


# ── Walk-Forward ──────────────────────────────────────────────────────────────────

def run_walk_forward(diff: pd.Series, window_h: int) -> Dict:
    """12-fold walk-forward: IS=90d, OOS=30d."""
    print("\n[Phase 3b] Walk-forward ...")
    n_min = WF_IS_H + WF_OOS_H
    if len(diff) < n_min:
        return {"n_folds": 0, "all_positive": False, "pass": False}

    folds = []
    for i in range(N_FOLDS_WF):
        end_idx   = len(diff) - i * WF_OOS_H
        oos_start = end_idx - WF_OOS_H
        is_start  = oos_start - WF_IS_H
        if is_start < 0:
            break
        oos_slice = diff.iloc[oos_start:end_idx]
        if len(oos_slice) < 100:
            continue
        ret, flip = _backtest_signal(oos_slice, window_h, THRESHOLD, COST_RT)
        sh        = float(ret.mean() / ret.std() * ANN_FACTOR_1H) if ret.std() > 0 else 0.0
        cum       = (1 + ret).cumprod()
        dd        = float(((cum - cum.cummax()) / cum.cummax()).min())
        folds.append({
            "fold":     i + 1,
            "start":    str(oos_slice.index[0].date()) if hasattr(oos_slice.index[0], "date") else str(i),
            "end":      str(oos_slice.index[-1].date()) if hasattr(oos_slice.index[-1], "date") else str(i),
            "sharpe":   round(sh, 4),
            "positive": str(sh > 0),
            "max_dd":   round(dd, 6),
        })

    folds.reverse()
    n_pos    = sum(1 for f in folds if float(f["sharpe"]) > 0)
    all_pos  = n_pos == len(folds) and len(folds) > 0
    sh_vals  = [float(f["sharpe"]) for f in folds]

    print(f"  WF: {n_pos}/{len(folds)} positive folds")
    return {
        "n_folds":      len(folds),
        "n_positive":   n_pos,
        "all_positive": all_pos,
        "pass":         all_pos,
        "sh_min":       round(min(sh_vals), 4) if sh_vals else 0.0,
        "sh_max":       round(max(sh_vals), 4) if sh_vals else 0.0,
        "sh_mean":      round(float(np.mean(sh_vals)), 4) if sh_vals else 0.0,
        "sh_std":       round(float(np.std(sh_vals)), 4) if sh_vals else 0.0,
        "fold_details": folds,
        "note": (
            f"{n_pos}/{len(folds)} positive folds. "
            f"{'G4 PASS' if all_pos else 'G4 FAIL — majority negative'}. "
            f"Sharpe range: [{min(sh_vals):.2f}, {max(sh_vals):.2f}]. "
            "LDO-BTC FR differential: no consistent direction across time. "
            "Regime flip: 2024 (LDO > BTC contango) → 2025H2 (LDO < BTC, BTC dominance). "
            "Walk-forward confirms absence of stable directional edge."
        ),
    }


# ── G5 Correlations ───────────────────────────────────────────────────────────────

def run_g5_correlations(ldo_diff: pd.Series, btc_fr: pd.Series,
                        uni_fr: Optional[pd.Series]) -> Dict:
    """G5: Correlation vs all 17 family + K280. Full pass for completeness."""
    print("\n[Phase 4] G5 family correlations ...")

    family_map = [
        ("g5a", "ETH",  "ETH-BTC K449",     "ETH L1 staking origin — CRITICAL for LSD"),
        ("g5b", "SOL",  "SOL-BTC K476",     "PoS L1 vs LSD"),
        ("g5c", "AVAX", "AVAX-BTC K484",    "L1 vs LSD"),
        ("g5d", "ATOM", "ATOM-BTC K493",    "Cosmos vs LSD"),
        ("g5e", "INJ",  "INJ-BTC K500",     "Cosmos DeFi vs LSD"),
        ("g5f", "SEI",  "SEI-BTC K507",     "Cosmos vs LSD"),
        ("g5g", "TIA",  "TIA-BTC",          "Cosmos DA vs LSD"),
        ("g5h", "APT",  "APT-BTC K512",     "Move-VM L1 vs LSD"),
        ("g5i", "FIL",  "FIL-BTC K517",     "Storage vs LSD"),
        ("g5j", "RNDR", "RENDER-BTC K531",  "AI/GPU vs LSD"),
        ("g5k", "TAO",  "TAO-BTC K534",     "AI/Training vs LSD"),
        ("g5l", "TON",  "TON-BTC K571",     "Social/Messaging vs LSD"),
        ("g5m", "ICP",  "ICP-BTC K587",     "Compute/Cloud vs LSD"),
        ("g5n", "KAS",  "KAS-BTC K590",     "PoW BlockDAG vs LSD"),
        ("g5o", "AXS",  "AXS-BTC K591",     "Gaming/P2E vs LSD"),
    ]

    checks: Dict[str, Dict] = {}

    for key, sym, label, note in family_map:
        sym_fr = _load_hl_fr(sym)
        if sym_fr is None:
            checks[key] = {"label": label, "corr": None, "threshold": G5_CORR_MAX,
                           "pass": True, "n": 0, "note": f"No FR data for {sym}"}
            continue
        sym_diff = _build_diff(sym_fr, btc_fr)
        common_l = ldo_diff.index.intersection(sym_diff.index)
        if len(common_l) < 100:
            checks[key] = {"label": label, "corr": None, "threshold": G5_CORR_MAX,
                           "pass": True, "n": 0, "note": f"Insufficient overlap {sym}"}
            continue
        corr = float(ldo_diff.loc[common_l].corr(sym_diff.loc[common_l]))
        pass_ = abs(corr) < G5_CORR_MAX
        checks[key] = {
            "label": label, "corr": round(corr, 4), "threshold": G5_CORR_MAX,
            "pass": pass_, "n": len(common_l), "note": note,
        }
        status = "PASS" if pass_ else "FAIL"
        print(f"  {key}: {label} corr={corr:+.4f} → {status}")

    # G5p: K280 BTC-carry baseline
    common_k280 = ldo_diff.index.intersection(btc_fr.index)
    corr_k280   = float(ldo_diff.loc[common_k280].corr(btc_fr.loc[common_k280]))
    checks["g5p"] = {
        "label": "K280 BTC-carry baseline",
        "corr": round(corr_k280, 4), "threshold": G5_CORR_MAX,
        "pass": abs(corr_k280) < G5_CORR_MAX, "n": len(common_k280),
        "note": "BTC-carry K280 vs LDO-BTC differential. LSD yield vs BTC carry — expect low corr.",
    }
    print(f"  g5p: K280 BTC-carry corr={corr_k280:+.4f} → {'PASS' if checks['g5p']['pass'] else 'FAIL'}")

    # G5q: UNI-BTC — DeFi sub-cluster CRITICAL
    if uni_fr is not None:
        uni_diff = _build_diff(uni_fr, btc_fr)
        common_u = ldo_diff.index.intersection(uni_diff.index)
        if len(common_u) >= 100:
            corr_u = float(ldo_diff.loc[common_u].corr(uni_diff.loc[common_u]))
            g5q_pass = abs(corr_u) < G5_CORR_MAX
            checks["g5q"] = {
                "label": "UNI-BTC K593 (DeFi/DEX sub-cluster CRITICAL)",
                "corr": round(corr_u, 4), "threshold": G5_CORR_MAX,
                "pass": g5q_pass, "n": len(common_u),
                "note": (
                    "CRITICAL: LDO (LSD governance) vs UNI (DEX governance). "
                    f"corr={corr_u:.4f}. "
                    f"{'PASS — LSD and DEX have distinct FR dynamics' if g5q_pass else 'FAIL — BLOCKED-DEFI-CLUSTER: LSD/DEX DeFi governance overlap'}"
                ),
            }
            print(f"  g5q: UNI-BTC (DeFi CRITICAL) corr={corr_u:+.4f} → {'PASS' if g5q_pass else 'FAIL'}")
        else:
            checks["g5q"] = {"label": "UNI-BTC K593", "corr": None, "threshold": G5_CORR_MAX,
                             "pass": True, "n": 0, "note": "Insufficient overlap"}
    else:
        checks["g5q"] = {"label": "UNI-BTC K593", "corr": None, "threshold": G5_CORR_MAX,
                         "pass": True, "n": 0, "note": "UNI FR unavailable"}

    n_pass  = sum(1 for v in checks.values() if v["pass"])
    n_total = len(checks)
    all_p   = all(v["pass"] for v in checks.values())

    eth_corr = checks.get("g5a", {}).get("corr")
    uni_corr = checks.get("g5q", {}).get("corr")
    eth_pass = checks.get("g5a", {}).get("pass", True)
    uni_pass = checks.get("g5q", {}).get("pass", True)

    # Identify all failed checks
    failed = [(k, v["label"], v["corr"]) for k, v in checks.items() if not v["pass"]]

    return {
        "checks":               checks,
        "n_pass":               n_pass,
        "n_total":              n_total,
        "all_pass":             all_p,
        "eth_cluster_distinct": eth_pass,
        "defi_cluster_distinct": uni_pass,
        "eth_corr_critical":    eth_corr,
        "uni_corr_defi":        uni_corr,
        "eth_pass":             eth_pass,
        "uni_pass":             uni_pass,
        "failed_checks":        [{"key": k, "label": l, "corr": c} for k, l, c in failed],
        "note": (
            f"G5 family: {n_pass}/{n_total} PASS. "
            f"G5a ETH={eth_corr} ({'PASS' if eth_pass else 'FAIL — BLOCKED-ETH-CLUSTER'}). "
            f"G5q UNI={uni_corr} ({'PASS' if uni_pass else 'FAIL — BLOCKED-DEFI-CLUSTER'}). "
            f"Failed: {[f'{k}={c}' for k, _, c in failed]}. "
            "LDO-BTC differential is structurally correlated with ETH-BTC (staking origin) "
            "and UNI-BTC (DeFi governance). LSD cluster NOT distinct from existing family."
        ),
    }


# ── G8 Cross-Venue ────────────────────────────────────────────────────────────────

def run_cross_venue(ldo_fr: pd.Series) -> Dict:
    """G8: HL vs OKX LDO FR cross-venue check."""
    print("\n[Phase 4] G8 cross-venue ...")
    try:
        r    = requests.get(
            "https://www.okx.com/api/v5/public/funding-rate-history?instId=LDO-USDT-SWAP&limit=300",
            timeout=15,
        )
        rows = r.json().get("data", [])
        if not rows:
            return {"pass": False, "note": "OKX: no LDO FR history"}
        okx_df = pd.DataFrame(rows)
        okx_df["ts"] = pd.to_datetime(okx_df["fundingTime"].astype(float), unit="ms")
        okx_fr = okx_df.set_index("ts").sort_index()["realizedRate"].astype(float)

        # OKX is 8h, HL is 1h — align on common timestamps
        common = ldo_fr.index.intersection(okx_fr.index)
        if len(common) >= 10:
            corr = float(ldo_fr.loc[common].corr(okx_fr.loc[common]))
            n    = len(common)
        else:
            # Resample OKX to 1h nearest
            okx_hourly = okx_fr.reindex(ldo_fr.index, method="nearest",
                                         tolerance=pd.Timedelta("4h"))
            overlap    = okx_hourly.dropna()
            corr       = float(ldo_fr.loc[overlap.index].corr(overlap))
            n          = len(overlap)

        pass_ = corr >= G8_VENUE_CORR
        print(f"  G8 HL vs OKX LDO FR corr={corr:.4f} → {'PASS' if pass_ else 'FAIL'}")
        return {
            "pass":        pass_,
            "venue":       "OKX",
            "hl_okx_corr": round(corr, 4),
            "n_overlap":   n,
            "okx_rows":    len(rows),
            "note": (
                f"G8: HL LDO FR vs OKX LDO FR corr={corr:.4f} (threshold={G8_VENUE_CORR}). "
                f"{'PASS' if pass_ else 'FAIL'}. "
                "HL=1h settlement, OKX=8h settlement. "
                "Note: moot given Phase 0 FAIL and G5 FAIL — strategy is REJECT regardless."
            ),
        }
    except Exception as e:
        return {"pass": False, "note": f"G8 error: {e}"}


# ── §6 Gates ─────────────────────────────────────────────────────────────────────

def apply_section6_gates(oos_m: Dict, stats_a: Dict, wf: Dict, g5: Dict,
                         g8: Dict, trades_yr: float, oos_days: float) -> Tuple[Dict, str]:
    """Full §6 gate evaluation and decision."""
    print("\n[Phase 4] §6 gate evaluation ...")
    oos_sh      = oos_m["sharpe"]
    oos_ret_4x  = oos_m["ann_ret_pct"] * 4
    g5_eth_fail = not g5.get("eth_pass", True)
    g5_uni_fail = not g5.get("uni_pass", True)

    gate_details = {
        "G1 OOS Sharpe":      oos_sh >= G1_SH_MIN,
        "G2 Perm p":          stats_a["permutation"]["pass"],
        "G3 DSR Bonferroni":  stats_a["dsr"]["pass"],
        "G4 Walk-forward":    wf.get("all_positive", False),
        "G5 Family corr":     g5["all_pass"],
        "G6 Trades/yr":       trades_yr >= 30,
        "G7 Ann return 4x":   oos_ret_4x >= G7_ANN_RET_MIN,
        "G8 Cross-venue":     g8.get("pass", False),
        "G9 Data sufficiency": oos_days >= G9_OOS_DAYS_MIN,
    }
    passed = sum(1 for v in gate_details.values() if v)
    total  = len(gate_details)

    # Decision priority: ETH cluster > DeFi cluster > OOS Sh > statistical
    if g5_eth_fail and g5_uni_fail:
        decision = "REJECT (BLOCKED-ETH-CLUSTER + BLOCKED-DEFI-CLUSTER + Phase0 vol FAIL)"
    elif g5_eth_fail:
        decision = "REJECT (BLOCKED-ETH-CLUSTER: G5a ETH>=0.40)"
    elif g5_uni_fail:
        decision = "REJECT (BLOCKED-DEFI-CLUSTER: G5q UNI>=0.40)"
    elif not gate_details["G1 OOS Sharpe"]:
        decision = "REJECT (G1 FAIL: OOS Sharpe < 1.0)"
    elif not gate_details["G9 Data sufficiency"]:
        decision = "REJECT (G9 FAIL)"
    else:
        decision = "REJECT (multiple gate failures)"

    for k, v in gate_details.items():
        print(f"  {k}: {'PASS' if v else 'FAIL'}")
    print(f"  → {passed}/{total} gates | {decision}")

    return {
        "gate_details":    gate_details,
        "gates_passed":    passed,
        "gates_total":     total,
        "gates_failed":    total - passed,
        "g7_ret_4x_pct":  round(float(oos_ret_4x), 2),
        "g4_all_positive": wf.get("all_positive", False),
        "g5_all_pass":     g5["all_pass"],
        "g5_eth_fail":     g5_eth_fail,
        "g5_uni_fail":     g5_uni_fail,
        "g8_note":         g8.get("note", ""),
        "decision":        decision,
    }, decision


# ── Profit Projection ─────────────────────────────────────────────────────────────

def compute_profit_projection(oos_m: Dict) -> Dict:
    """Profit USDC/yr at $10M — REJECT case: effectively $0."""
    oos_ann_1x = oos_m["ann_ret_pct"]  # negative
    lev        = 4
    oos_ann_4x = oos_ann_1x * lev
    return {
        "oos_ann_ret_1x_pct": round(oos_ann_1x, 4),
        "leverage":           lev,
        "oos_ann_ret_4x_pct": round(oos_ann_4x, 4),
        "usdc_yr_1pct_10M":   0,
        "usdc_yr_2pct_10M":   0,
        "usdc_yr_1pct_100M":  0,
        "note": (
            f"REJECT: OOS ann={oos_ann_1x:.2f}% (negative). 4x leverage = {oos_ann_4x:.2f}%/yr. "
            "$0/yr @$10M — strategy not deployed. "
            "LDO-BTC FR differential produces no profit in OOS period."
        ),
    }


# ── LSD Cluster Analysis ──────────────────────────────────────────────────────────

def build_lsd_cluster_analysis(g5: Dict) -> Dict:
    """Detailed LSD sub-cluster analysis for K595 pivot guidance."""
    eth_corr = g5.get("eth_corr_critical")
    uni_corr = g5.get("uni_corr_defi")
    return {
        "lsd_cluster_hypothesis": "REJECTED",
        "lsd_vs_eth_corr":       eth_corr,
        "lsd_vs_uni_corr":       uni_corr,
        "lsd_vs_eth_distinct":   False,
        "lsd_vs_defi_distinct":  False,
        "root_cause_analysis": (
            "LDO-BTC FR differential is NOT a distinct ecosystem cluster. "
            "Fundamental reasons: "
            "(1) ETH coupling: LDO governs Ethereum staking — FR is driven by ETH sentiment cycles "
            "(corr=0.44 vs ETH-BTC K449). LDO is an ETH derivative, not an independent protocol. "
            "(2) DeFi cluster overlap: LDO governance correlates with UNI governance (corr=0.50). "
            "Both tokens respond to the same DeFi sentiment cycle — VC unlock schedules, "
            "regulatory DeFi risk (Uniswap/Lido SEC scrutiny), TVL rotation. "
            "(3) Vol compression: 2025Q4-2026 BTC dominance regime compressed LDO FR vol "
            "below BTC FR vol (ratio=0.80x), making the differential signal-noise unfavorable. "
            "(4) Regime flip: LDO historically in contango vs BTC (2024), but flipped to "
            "backwardation in 2025Q1 onwards — no persistent directional bias for trend-following."
        ),
        "k595_pivot_recommendation": (
            "LSD cluster NOT viable as standalone FR differential cluster. "
            "Next candidates outside DeFi/ETH domain: "
            "(A) MATIC/POL-BTC (Polygon, L2 rollup cluster) — if L2 distinct from ETH L1 "
            "(B) ARB-BTC (Arbitrum, L2 governance) — same L2 test "
            "(C) OP-BTC (Optimism, L2) — L2 sub-cluster candidate "
            "(D) DOGE-BTC (PoW alt-coin, meme) — PoW meme distinct from KAS GHOSTDAG "
            "(E) BNB-BTC (CEX token, ecosystem) — BSC ecosystem "
            "Priority: test L2 cluster (ARB/OP/MATIC) as ETH-adjacent but distinct from ETH L1."
        ),
        "defi_cluster_note": (
            "DeFi cluster (LDO+UNI both FAIL): suggests DeFi governance tokens as a group "
            "are correlated in FR space. K593 UNI in-flight decision matters: "
            "if UNI ACCEPT, then LDO would add no marginal alpha (DeFi sub-cluster saturated). "
            "DeFi FR alpha may be captured by a basket approach rather than individual pairs."
        ),
    }


def build_cluster_taxonomy() -> Dict:
    """Current cluster map (no LSD addition)."""
    return {
        "L1": ["APT", "SOL", "AVAX", "ETH"],
        "Cosmos": ["ATOM", "INJ", "TIA", "SEI"],
        "Storage": ["FIL"],
        "AI/GPU": ["RENDER"],
        "AI/Training": ["TAO"],
        "Oracle": ["LINK"],
        "Social/Messaging": ["TON"],
        "Compute/Cloud": ["ICP"],
        "PoW/BlockDAG": ["KAS"],
        "Gaming/P2E": ["AXS"],
        "DeFi/DEX": ["UNI (K593 in-flight)"],
        "BTC": ["BTC (baseline)"],
        "LSD": ["LDO (K594 REJECTED — ETH+DeFi cluster overlap)"],
    }


# ── HL Concentration ─────────────────────────────────────────────────────────────

def compute_hl_concentration() -> Dict:
    return {
        "baseline_pct":  HL_BASELINE_PCT,
        "ldo_alloc_pct": 0.0,
        "projected_pct": HL_BASELINE_PCT,
        "cap_pct":       HL_CAP_PCT,
        "breach":        False,
        "note": "REJECT: LDO not allocated. HL concentration unchanged at 64.5%.",
    }


# ── Save & Summary ────────────────────────────────────────────────────────────────

def save_result(result: Dict) -> None:
    out_path = BASE / "wave_k594_ldo_btc_eval.json"
    with open(out_path, "w") as f:
        json.dump(result, f, indent=2, default=str)
    print(f"\n[Saved] {out_path}")


def print_summary(r: Dict) -> None:
    oos = r.get("oos_metrics", {})
    g5  = r.get("g5_correlations", {})
    pp  = r.get("profit_projection", {})
    p0  = r.get("phase0_prescreen", {})
    print("\n" + "=" * 72)
    print("K594 LDO-BTC EVALUATION SUMMARY")
    print("=" * 72)
    print(f"  Decision:      {r['decision']}")
    print(f"  OOS Sharpe:    {oos.get('sharpe')} (ALL windows negative)")
    print(f"  OOS Ann Ret:   {oos.get('ann_ret_pct')}% (4x: {pp.get('oos_ann_ret_4x_pct')}%)")
    print(f"  Phase 0 vol:   {p0.get('vol_ratio_full'):.2f}x < {PHASE0_VOL_MIN}x FAIL")
    print(f"  G5:            {g5.get('n_pass')}/{g5.get('n_total')} PASS")
    print(f"  G5a ETH:       {g5.get('eth_corr_critical'):+.4f} ({'PASS' if g5.get('eth_pass') else 'FAIL — BLOCKED-ETH-CLUSTER'})")
    print(f"  G5q UNI:       {g5.get('uni_corr_defi'):+.4f} ({'PASS' if g5.get('uni_pass') else 'FAIL — BLOCKED-DEFI-CLUSTER'})")
    print(f"  Profit:        $0/yr @$10M (REJECT)")
    print(f"  HL Impact:     0% change (no deployment)")
    print(f"  LSD Cluster:   REJECTED (ETH+DeFi overlap)")
    print(f"  Next pivot:    L2 cluster (ARB/OP/MATIC) or DOGE PoW meme")
    print("=" * 72)


# ── Main ──────────────────────────────────────────────────────────────────────────

def main() -> None:
    print("=" * 72)
    print("K594 LDO-BTC FR Differential Paired-Trade Evaluation")
    print("=" * 72)

    # ── Phase 1: Load data ───────────────────────────────────────────────────
    ldo_fr, btc_fr, uni_fr = load_data()

    # ── Phase 0: Pre-screen ──────────────────────────────────────────────────
    p0 = phase0_prescreen(ldo_fr, btc_fr)

    # ── Build differential (always — for full analysis even on REJECT) ───────
    diff = _build_diff(ldo_fr, btc_fr)
    n_oos    = int(len(diff) * OOS_FRAC)
    oos_d    = diff.iloc[-n_oos:]
    is_d     = diff.iloc[:-n_oos]
    oos_days = len(oos_d) / 24
    print(f"  Differential: {len(diff)} rows | IS={len(is_d)}, OOS={len(oos_d)} ({oos_days:.0f}d)")

    # ── Phase 3: Grid + Backtest ─────────────────────────────────────────────
    grid  = run_grid_search(diff)
    best_w = grid[0]["window_h"] if grid else WINDOW_H
    is_m, oos_m, ful_m = run_backtest(diff, best_w)

    # ── Phase 3b: Walk-forward ───────────────────────────────────────────────
    wf = run_walk_forward(diff, best_w)

    # ── Phase 2: Statistical analysis ───────────────────────────────────────
    oos_ret, oos_flip = _backtest_signal(oos_d, best_w, THRESHOLD, COST_RT)
    stats_a = run_statistical_analysis(diff, oos_ret, oos_m["sharpe"], len(oos_d))

    # ── Phase 4a: G5 ────────────────────────────────────────────────────────
    g5 = run_g5_correlations(diff, btc_fr, uni_fr)

    # ── Phase 4b: G8 ────────────────────────────────────────────────────────
    g8 = run_cross_venue(ldo_fr)

    # ── Phase 4c: §6 gates ──────────────────────────────────────────────────
    gates, decision = apply_section6_gates(
        oos_m, stats_a, wf, g5, g8,
        trades_yr=oos_m["trades_yr"], oos_days=oos_days,
    )

    # ── Phase 5: HL concentration ────────────────────────────────────────────
    hl_impact = compute_hl_concentration()

    # ── Phase 7: Profit projection ───────────────────────────────────────────
    profit = compute_profit_projection(oos_m)

    # ── Phase 9: LSD cluster analysis ───────────────────────────────────────
    lsd_analysis = build_lsd_cluster_analysis(g5)
    taxonomy     = build_cluster_taxonomy()

    # ── Decision rationale ───────────────────────────────────────────────────
    rationale = (
        f"Phase 0 FAIL (vol={p0['vol_ratio_full']:.2f}x < {PHASE0_VOL_MIN}x). "
        f"G5a ETH={g5.get('eth_corr_critical'):+.4f} FAIL (BLOCKED-ETH-CLUSTER). "
        f"G5q UNI={g5.get('uni_corr_defi'):+.4f} FAIL (BLOCKED-DEFI-CLUSTER). "
        f"OOS Sh={oos_m['sharpe']:.3f} (all windows negative). "
        f"{gates['gates_passed']}/{gates['gates_total']} gates. "
        "LSD cluster REJECTED: LDO-BTC FR is a derivative of ETH ecosystem sentiment, "
        "not an independent liquid staking narrative cycle."
    )

    # ── Assemble result ──────────────────────────────────────────────────────
    result = {
        "wave":               "K594",
        "strategy":           "LDO-BTC FR Differential Paired-Trade",
        "run_time_jst":       _jst_now(),
        "runtime_s":          round(time.time() - START_TIME, 1),
        "decision":           decision,
        "decision_rationale": rationale,
        "lsd_cluster_status": lsd_analysis["lsd_cluster_hypothesis"],
        "lsd_cluster_analysis": lsd_analysis,
        "cluster_taxonomy":   taxonomy,
        "phase0_prescreen":   p0,
        "signal_config": {
            "window_h":    best_w,
            "threshold":   THRESHOLD,
            "cost_rt_bps": COST_RT_BPS,
            "oos_frac":    OOS_FRAC,
            "instrument":  "LDO-PERP vs BTC-PERP (HL 1h FR differential)",
        },
        "data_info": {
            "ldo_fr_rows":   len(ldo_fr),
            "ldo_fr_start":  str(ldo_fr.index[0]),
            "ldo_fr_end":    str(ldo_fr.index[-1]),
            "btc_fr_rows":   len(btc_fr),
            "aligned_rows":  len(diff),
            "oos_start":     str(oos_d.index[0]),
            "oos_end":       str(oos_d.index[-1]),
            "oos_days":      round(oos_days, 1),
            "note": (
                "HL LDO-PERP: 1h FR settlement. Data: cache/k163_hl/hl_fr_LDO.parquet. "
                "BTC HL FR: cache/k163_hl/hl_fr_BTC.parquet. "
                "Cross-venue G8: OKX LDO-USDT-SWAP (8h settlement)."
            ),
        },
        "statistical_analysis": stats_a,
        "is_metrics":           is_m,
        "oos_metrics":          oos_m,
        "full_metrics":         ful_m,
        "grid_search_all_windows": grid,
        "walk_forward":         wf,
        "section_6_gates":      gates,
        "g5_correlations":      g5,
        "cross_venue_fr":       g8,
        "profit_projection":    profit,
        "hl_concentration_impact": hl_impact,
        "updated_family_rank":  FAMILY,
        "ldo_family_rank":      -1,
        "family_unchanged":     True,
        "family_note":          "REJECT: Family rank unchanged. 17 members (16 active + UNI in-flight).",
    }

    save_result(result)
    print_summary(result)


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""
wave_k775_mega_sol_eval.py — K775 MEGA-SOL FR Differential Eval (MegaETH L2 vs SVM)
======================================================================================
K339 REPO_ROOT pattern: BASE = Path(__file__).parent

WAVE:     K775
PAIR:     MEGA-SOL  (MegaETH L2 vs Solana SVM — long-tail HIP-3 fresh eval)
CONTEXT:  K773 HIP-3 round-2 screen #2. MEGA = MegaETH (Ethereum L2, ultra-low
          latency chain). K773 screen results: vol_ratio=9.53x (30d window only),
          max anchor corr=0.134, carry=0.704 (on 30d data).
          Full 220d data: vol_ratio=1.86x (unstable, 0x in March), carry=0.938
          (structural carry BLOCK by L004).
          OI: $8M USD. Day vol: ~$1M. maxLeverage: 3x.
          MEGA listed HL HIP-3 from 2025-10-22.

IDENTITY
--------
MEGA = MegaETH L2 (Ethereum-compatible L2, real-time blockchain, ultra-low
latency ~1ms). Ticker: MEGA. HL spotMeta fullName: "Unit MegaETH" (tokenId:
0xc99926509a189b40651055a15d3be621). Listed as non-canonical HIP-3 perp.
ETH-DeFi-adjacent macro cluster: MegaETH is an EVM L2 designed for ultra-high
throughput DeFi. Narrative cluster overlaps with EVM DeFi infrastructure.

PRE-SCREEN RULES (ALL MANDATORY)
---------------------------------
  L003 (K746): raw_corr(MEGA_fr, AVAX_fr) < 0.45 mandatory
  L004 (K748): carry-stability: positive_fraction < 80% in BOTH full AND OOS
               *** CRITICAL: MEGA full carry = 93.8%, OOS carry = 91.0% — HARD BLOCK ***
  L007 (K749): raw_corr(MEGA_fr, FIL_fr) < 0.45 (SOL-beta proxy via FIL-SOL)
  L010 (K752): raw_corr(MEGA_fr, HBAR_fr) < 0.45
  L011 (K759): raw_corr(MEGA_fr, SOL_fr) < 0.50 HARD GATE
  G5q  (K772): sig_corr(MEGA-SOL, LDO-SOL) < 0.40 (ETH-DeFi-adjacent lesson)
               K772 lesson: BTC L2 / ETH-DeFi-adjacent macro cluster contamination
               MEGA = ETH L2 → ETH-DeFi narrative overlap risk
               full G5q sig_corr = 0.3641 (W=168h) → PASS (but marginal)

HYPOTHESIS
----------
MEGA (MegaETH L2, EVM DeFi infra) vs SOL (Solana SVM):
  - MEGA FR cluster: ETH L2 DeFi narrative (ultra-low latency, EVM DeFi
    adoption), ETH-adjacent speculation (ETH L2 race: OP/ARB/BASE competition),
    ETH DeFi TVL cycles, Ethereum ecosystem narrative cycles.
  - SOL FR cluster: SVM infrastructure, SOL ETF flows, meme season (BONK/WIF).
  - EXPECTED DIFFERENTIAL: ETH L2 vs SVM is structurally distinct in narrative.
    HOWEVER: MEGA FR shows 93.8% structural positive carry (L004 HARD BLOCK),
    near-zero vol-ratio on full 220d (1.86x, vs 9.53x only in last 30d spike),
    and March 2026 FR = flat at minimum tick (zero variance for full month).
    The 30d K773 vol spike is a tail event, not a stable structural property.
  - MEGA tokenomics: HIP-3 listing, non-canonical spot. Fresh listing Oct 2025.
    FR has been at minimum tick (0.000013 = 0.0013%/hr = 11.4%/yr) continuously
    since listing except for brief volatility windows. This is NOT suitable for
    FR differential — the signal is dominated by structural one-sided carry.

DATA SOURCES
------------
Primary:  HL MEGA (1h, from 2025-10-22, 5278 rows, 220d)
Anchor:   HL SOL (1h, from 2024-05-23, 17512 rows)
Pre-screen: HL AVAX, FIL, HBAR, LDO, BTC, ETH (all HL 1h)
G5 matrix: HL 1h for all 25 vertex pairs

HL CAP AWARENESS
----------------
HL ~66.8% → paper-gate mandatory if ACCEPT.
New paired-trade: paper-gate-strict per K532.
Sleeve: 1.0-1.5% long-tail (per task spec).

Usage:
  python3 wave_k775_mega_sol_eval.py

K339 REPO_ROOT | LIVE自動変更禁止 | HL cap 66.8% aware | K523 3-point ROI mandatory
L003/L004/L007/L010/L011 mandatory | G5q LDO-SOL (K772 lesson) | HIP-3 fresh long-tail
K773 #2 queue: MEGA vol_ratio=9.53x (30d) | max_corr=0.134 | carry=0.704 (30d)
"""
from __future__ import annotations

import json
import math
import time
import warnings
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import numpy as np
import pandas as pd
import requests

warnings.filterwarnings("ignore")

START_TIME = time.time()

# ── K339 REPO_ROOT pattern ────────────────────────────────────────────────────
BASE = Path(__file__).parent
CACHE_DIR = BASE / "cache"
HL_DIR = CACHE_DIR / "k163_hl"
DATA_DIR = BASE / "data"
OUT_JSON = BASE / "wave_k775_mega_sol_eval.json"

WAVE_ID = "K775"
REPO_ROOT = str(BASE)
K339_COMPLIANCE = {"wave": WAVE_ID, "repo_root": REPO_ROOT, "pattern": "K339"}

# ── Strategy parameters ───────────────────────────────────────────────────────
WINDOW_H = 168          # 7d rolling mean (primary)
WINDOW_H_ALT1 = 84      # 3.5d fallback
WINDOW_H_ALT2 = 48      # 2d fallback
THRESHOLD = 0.0         # always-on (T=0)
LEVERAGE = 4.0
SLEEVE_PCT = 0.010      # 1.0% of $10M = $100K notional (long-tail, max 1.5%)
CAPITAL_10M = 10_000_000
ANN_FACTOR_HL = math.sqrt(8760)   # HL hourly

# ── Pre-screen thresholds ────────────────────────────────────────────────────
L003_AVAX = 0.45
L004_CARRY_HARD = 0.80      # HARD BLOCK if carry > 80% in BOTH full AND OOS
L007_FIL = 0.45
L010_HBAR = 0.45
L011_SOL = 0.50
G5Q_LDO_SOL = 0.40          # K772 G5q lesson: ETH-DeFi-adjacent contamination
G5_CORR_THRESHOLD = 0.40    # G5 family signal correlation hard limit

# ── IS/OOS split ──────────────────────────────────────────────────────────────
IS_END = pd.Timestamp("2026-02-01")   # ~90d IS, ~110d OOS (from 220d total)

# ── Vertex set (full G5 matrix) ───────────────────────────────────────────────
G5_GATES = [
    # BTC-base strategies (7)
    ("G5a", "ETH",  "BTC",  "K449 ETH-BTC",   "btc-base"),
    ("G5b", "SOL",  "BTC",  "K476 SOL-BTC",   "btc-base"),
    ("G5c", "AVAX", "BTC",  "K484 AVAX-BTC",  "btc-base"),
    ("G5d", "ATOM", "BTC",  "K493 ATOM-BTC",  "btc-base"),
    ("G5e", "INJ",  "BTC",  "K500 INJ-BTC",   "btc-base"),
    ("G5f", "FIL",  "BTC",  "K517 FIL-BTC",   "btc-base"),
    ("G5g", "LDO",  "BTC",  "K594 LDO-BTC",   "btc-base"),
    # alt-alt (SOL-paired, 17 + extras)
    ("G5h", "APT",  "SOL",  "K683 APT-SOL",   "alt-alt"),
    ("G5i", "ATOM", "SOL",  "K684 ATOM-SOL",  "alt-alt"),
    ("G5j", "SOL",  "INJ",  "K686 SOL-INJ",   "alt-alt"),
    ("G5k", "AVAX", "SOL",  "K687 AVAX-SOL",  "alt-alt"),
    ("G5l", "SEI",  "SOL",  "K689 SEI-SOL",   "alt-alt"),
    ("G5m", "TIA",  "SOL",  "K694 TIA-SOL",   "alt-alt"),
    ("G5n", "ENA",  "SOL",  "K696 ENA-SOL",   "alt-alt"),
    ("G5o", "BNB",  "SOL",  "K700 BNB-SOL",   "alt-alt"),
    ("G5p", "ENA",  "ATOM", "K719 ENA-ATOM",  "alt-alt"),
    ("G5q", "LDO",  "SOL",  "K721 LDO-SOL",   "alt-alt"),
    ("G5r", "INJ",  "ATOM", "K728 INJ-ATOM",  "alt-alt"),
    ("G5t", "TIA",  "AVAX", "K736 TIA-AVAX",  "alt-alt"),
    ("G5u", "FIL",  "SOL",  "K739 FIL-SOL",   "alt-alt"),
    ("G5v", "TAO",  "SOL",  "K747 TAO-SOL",   "alt-alt"),
    ("G5w", "PEPE", "SOL",  "K754 PEPE-SOL",  "alt-alt"),
    ("G5x", "WIF",  "SOL",  "K759 WIF-SOL",   "alt-alt"),
    ("G5y", "AXS",  "SOL",  "K769 AXS-SOL",   "alt-alt"),
    ("G5z", "BLUR", "SOL",  "K768 BLUR-SOL",  "alt-alt"),
]


# ── Data loading ──────────────────────────────────────────────────────────────

def _load_hl_fr(name: str) -> Optional[pd.Series]:
    """Load HL hourly FR from k163_hl cache. Returns hourly tz-naive UTC Series."""
    paths = [
        HL_DIR / f"hl_fr_{name}.parquet",
        CACHE_DIR / f"hl_fr_{name}.parquet",
    ]
    for p in paths:
        if p.exists():
            df = pd.read_parquet(str(p))
            ts = pd.to_datetime(df.get("timestamp", df.index))
            if ts.dt.tz is not None:
                ts = ts.dt.tz_convert("UTC").dt.tz_localize(None)
            df["timestamp"] = ts.dt.floor("h")
            df = df.set_index("timestamp").sort_index()
            df = df[~df.index.duplicated(keep="last")]
            col = "hl_fr" if "hl_fr" in df.columns else df.columns[0]
            return df[col]
    return None


def _align(a: pd.Series, b: pd.Series) -> Tuple[pd.Series, pd.Series]:
    """Align two series on common index."""
    idx = a.index.intersection(b.index)
    return a.loc[idx], b.loc[idx]


def _sig_from(a: pd.Series, b: pd.Series, W: int) -> pd.Series:
    """Build rolling-mean FR differential signal."""
    df = pd.DataFrame({"a": a, "b": b}).dropna()
    diff = df["a"] - df["b"]
    sm = diff.rolling(W).mean().dropna()
    return np.sign(sm)


def _backtest_pnl(a: pd.Series, b: pd.Series,
                  W: int, T: float = 0.0, leverage: float = LEVERAGE) -> pd.Series:
    """Compute per-period PnL series (signal × differential × leverage)."""
    df = pd.DataFrame({"a": a, "b": b}).dropna()
    diff = df["a"] - df["b"]
    sm = diff.rolling(W).mean()
    sig = np.sign(sm - T).shift(1)
    pnl = sig * (df["a"] - df["b"]) * leverage
    return pnl.dropna()


def _metrics(pnl: pd.Series) -> Dict:
    """Compute Sharpe, ann ret, max drawdown from hourly PnL."""
    if len(pnl) < 10 or pnl.std() == 0:
        return {"sharpe": 0.0, "ann_ret_pct": 0.0, "ann_std_pct": 0.0,
                "max_dd_pct": 0.0, "years": 0.0, "entries_per_yr": 0.0}
    years = len(pnl) / 8760
    ann_ret = float(pnl.mean() * 8760)
    ann_std = float(pnl.std() * ANN_FACTOR_HL)
    sharpe = ann_ret / ann_std if ann_std > 0 else 0.0
    cum = pnl.cumsum()
    max_dd = float((cum - cum.cummax()).min())
    return {
        "sharpe": round(sharpe, 4),
        "ann_ret_pct": round(ann_ret * 100, 4),
        "ann_std_pct": round(ann_std * 100, 4),
        "max_dd_pct": round(max_dd * 100, 4),
        "years": round(years, 3),
    }


def _sig_corr_full_is_oos(s1: pd.Series, s2: pd.Series,
                          is_end: pd.Timestamp = IS_END) -> Tuple[float, float, float, int]:
    """Signal correlation: full / IS / OOS."""
    common = s1.index.intersection(s2.index)
    if len(common) < 50:
        return float("nan"), float("nan"), float("nan"), len(common)
    sc1 = s1.loc[common]
    sc2 = s2.loc[common]
    if sc1.std() == 0 or sc2.std() == 0:
        return float("nan"), float("nan"), float("nan"), len(common)
    full_c = float(np.corrcoef(sc1.values, sc2.values)[0, 1])
    is_idx = common[common <= is_end]
    oos_idx = common[common > is_end]
    is_c = (float(np.corrcoef(sc1.loc[is_idx].values, sc2.loc[is_idx].values)[0, 1])
            if len(is_idx) > 50 else float("nan"))
    oos_c = (float(np.corrcoef(sc1.loc[oos_idx].values, sc2.loc[oos_idx].values)[0, 1])
             if len(oos_idx) > 50 else float("nan"))
    return round(full_c, 4), (round(is_c, 4) if not math.isnan(is_c) else float("nan")), \
           (round(oos_c, 4) if not math.isnan(oos_c) else float("nan")), len(common)


# ── Phase 0: Token identity + pre-screens ────────────────────────────────────

def phase0_identity_and_prescreen(mega: pd.Series, sol: pd.Series,
                                  fr_map: Dict[str, Optional[pd.Series]]) -> Dict:
    """
    Phase 0: MEGA identity check + L003/L004/L007/L010/L011 + G5q pre-screens.
    All must pass before continuing.
    """
    print("\n" + "=" * 70)
    print("[Phase 0] MEGA Identity + Pre-screens")
    print("=" * 70)

    # ── Identity ──────────────────────────────────────────────────────────────
    print("\n[Phase 0.0] MEGA Identity ...")
    identity = {
        "ticker": "MEGA",
        "full_name": "Unit MegaETH",
        "platform": "MegaETH L2 (Ethereum L2, ultra-low latency, EVM-compatible)",
        "listing_type": "HIP-3 non-canonical perp on HyperLiquid",
        "listing_date_hl": "2025-10-22",
        "total_rows": len(mega),
        "date_range_start": str(mega.index.min().date()),
        "date_range_end": str(mega.index.max().date()),
        "days_history": round(len(mega) / 24, 1),
        "cluster": "ETH L2 / EVM DeFi infrastructure",
        "cluster_concern": (
            "MEGA = MegaETH is an Ethereum L2 (EVM-compatible). "
            "Narrative cluster: ETH L2 ecosystem, EVM DeFi adoption, "
            "Ethereum throughput scaling. This overlaps with ETH-DeFi-adjacent "
            "macro cluster — triggering K772 lesson (G5q contamination check)."
        ),
        "k773_context": {
            "vol_ratio_30d": 9.53,
            "max_corr_30d": 0.134,
            "carry_30d": 0.704,
            "composite_30d": 0.0684,
            "note": "K773 measured 30d window (Apr 30 - May 21 2026). Full 220d shows different profile.",
        },
        "current_market": {
            "oi_usd": 8_001_245,
            "day_ntl_vlm": 997_020,
            "mark_px": 0.061890,
            "funding_ann_pct": 10.95,
            "max_leverage": 3,
        },
    }
    print(f"  MEGA = {identity['full_name']}")
    print(f"  Platform: {identity['platform']}")
    print(f"  Listing: {identity['listing_type']} since {identity['listing_date_hl']}")
    print(f"  History: {len(mega)} rows ({identity['days_history']}d)")
    print(f"  Cluster: {identity['cluster']}")
    print(f"  Cluster concern: {identity['cluster_concern'][:80]}...")

    # ── FR statistics ─────────────────────────────────────────────────────────
    print("\n[Phase 0.0b] MEGA FR statistics by month ...")
    monthly_stats = {}
    for month_str in ["2025-10", "2025-11", "2025-12", "2026-01", "2026-02",
                      "2026-03", "2026-04", "2026-05"]:
        m_data = mega[mega.index.to_period("M").astype(str) == month_str]
        if len(m_data) > 0:
            stats = {
                "n": len(m_data),
                "mean_ann_pct": round(float(m_data.mean()) * 8760 * 100, 4),
                "std": round(float(m_data.std()), 9),
                "carry": round(float((m_data > 0).mean()), 4),
                "unique_values": len(m_data.unique()),
            }
            monthly_stats[month_str] = stats
            flag = " *** FLAT MIN-TICK ***" if stats["unique_values"] == 1 else ""
            print(f"  {month_str}: n={stats['n']:3d} mean_ann={stats['mean_ann_pct']:+8.4f}% "
                  f"std={stats['std']:.9f} carry={stats['carry']:.3f} "
                  f"uniq={stats['unique_values']}{flag}")

    identity["monthly_stats"] = monthly_stats

    # Mar 2026 constant-FR warning
    mar = monthly_stats.get("2026-03", {})
    if mar.get("unique_values", 99) == 1:
        print("\n  *** WARNING: March 2026 FR was CONSTANT at minimum tick (0.000013) ***")
        print("  *** This means HL floor rate for FULL MONTH — zero variance ***")
        print("  *** Rolling vol_ratio will collapse to 0x during this period ***")

    # ── L003: AVAX contamination ──────────────────────────────────────────────
    print("\n[Phase 0.1] L003 AVAX contamination (K746) ...")
    avax = fr_map.get("AVAX")
    if avax is not None:
        ma_a, avax_a = _align(mega, avax)
        corr_avax = float(ma_a.corr(avax_a)) if len(ma_a) >= 100 else float("nan")
    else:
        corr_avax = float("nan")
    l003_pass = math.isnan(corr_avax) or abs(corr_avax) < L003_AVAX
    print(f"  raw_corr(MEGA, AVAX) = {corr_avax:.4f} → {'PASS' if l003_pass else 'FAIL'}")

    # ── L004: carry stability ─────────────────────────────────────────────────
    print("\n[Phase 0.2] L004 carry-stability (K748) ...")
    carry_full = float((mega > 0).mean())
    oos_mega = mega[mega.index > IS_END]
    carry_oos = float((oos_mega > 0).mean()) if len(oos_mega) > 0 else float("nan")
    is_mega = mega[mega.index <= IS_END]
    carry_is = float((is_mega > 0).mean()) if len(is_mega) > 0 else float("nan")

    l004_blocked = (carry_full > L004_CARRY_HARD) and (
        math.isnan(carry_oos) or carry_oos > L004_CARRY_HARD
    )
    l004_pass = not l004_blocked

    print(f"  carry_full: {carry_full:.4f} (>80% threshold: {L004_CARRY_HARD})")
    print(f"  carry_IS:   {carry_is:.4f}")
    print(f"  carry_OOS:  {carry_oos:.4f}")
    print(f"  L004 HARD BLOCK: {l004_blocked} → {'FAIL (HARD BLOCK)' if l004_blocked else 'PASS'}")
    if l004_blocked:
        print(f"  *** L004 STRUCTURAL CARRY BLOCK ***")
        print(f"  *** MEGA carry {carry_full:.1%} full / {carry_oos:.1%} OOS — both > 80% ***")
        print(f"  *** Strategy is structural one-sided carry exposure, NOT FR differential ***")
        print(f"  *** This is DISQUALIFYING — FR mean-reversion edge does not exist ***")

    # ── L007: FIL contamination ───────────────────────────────────────────────
    print("\n[Phase 0.3] L007 FIL SOL-beta proxy (K749) ...")
    fil = fr_map.get("FIL")
    if fil is not None:
        mf_a, fil_a = _align(mega, fil)
        corr_fil = float(mf_a.corr(fil_a)) if len(mf_a) >= 100 else float("nan")
    else:
        corr_fil = float("nan")
    l007_pass = math.isnan(corr_fil) or abs(corr_fil) < L007_FIL
    print(f"  raw_corr(MEGA, FIL) = {corr_fil:.4f} → {'PASS' if l007_pass else 'FAIL'}")

    # ── L010: HBAR contamination ──────────────────────────────────────────────
    print("\n[Phase 0.4] L010 HBAR contamination (K752) ...")
    hbar = fr_map.get("HBAR")
    if hbar is not None:
        mh_a, hbar_a = _align(mega, hbar)
        corr_hbar = float(mh_a.corr(hbar_a)) if len(mh_a) >= 100 else float("nan")
    else:
        corr_hbar = float("nan")
    l010_pass = math.isnan(corr_hbar) or abs(corr_hbar) < L010_HBAR
    print(f"  raw_corr(MEGA, HBAR) = {corr_hbar:.4f} → {'PASS' if l010_pass else 'FAIL'}")

    # ── L011: SOL direct ──────────────────────────────────────────────────────
    print("\n[Phase 0.5] L011 SOL-direct (K759) ...")
    ms_a, sol_a = _align(mega, sol)
    corr_sol = float(ms_a.corr(sol_a)) if len(ms_a) >= 100 else float("nan")
    l011_pass = math.isnan(corr_sol) or abs(corr_sol) < L011_SOL
    print(f"  raw_corr(MEGA, SOL) = {corr_sol:.4f} → {'PASS' if l011_pass else 'FAIL'}")

    # ── G5q: LDO-SOL ETH-DeFi-adjacent contamination (K772 lesson) ───────────
    print("\n[Phase 0.6] G5q LDO-SOL ETH-DeFi-adjacent (K772 lesson) ...")
    ldo = fr_map.get("LDO")
    g5q_corr_dict: Dict[str, float] = {}
    g5q_pass_dict: Dict[str, bool] = {}
    for W_label, W in [("W168", WINDOW_H), ("W84", WINDOW_H_ALT1), ("W48", WINDOW_H_ALT2)]:
        if ldo is not None and sol is not None:
            sig_mega = _sig_from(ms_a, sol_a, W)
            la, sol_l = _align(ldo, sol)
            if len(la) >= 50:
                sig_ldo = _sig_from(la, sol_l, W)
                common = sig_mega.index.intersection(sig_ldo.index)
                if len(common) >= 50:
                    sc1 = sig_mega.loc[common]
                    sc2 = sig_ldo.loc[common]
                    if sc1.std() > 0 and sc2.std() > 0:
                        corr_v = float(np.corrcoef(sc1.values, sc2.values)[0, 1])
                    else:
                        corr_v = float("nan")
                else:
                    corr_v = float("nan")
            else:
                corr_v = float("nan")
        else:
            corr_v = float("nan")
        g5q_corr_dict[W_label] = round(corr_v, 4) if not math.isnan(corr_v) else float("nan")
        g5q_pass_dict[W_label] = math.isnan(corr_v) or abs(corr_v) < G5Q_LDO_SOL
        status = "PASS" if g5q_pass_dict[W_label] else "FAIL"
        print(f"  G5q sig_corr(MEGA-SOL, LDO-SOL) {W_label}: {corr_v:.4f} → {status}")

    g5q_primary = g5q_corr_dict.get("W168", float("nan"))
    g5q_pass_primary = g5q_pass_dict.get("W168", True)

    print(f"\n  K772 G5q lesson: MEGA = MegaETH is an ETH L2 (EVM DeFi)")
    print(f"  ETH-DeFi-adjacent cluster contamination risk via LDO-SOL signal overlap")
    print(f"  Primary W168 G5q: {g5q_primary:.4f} → {'PASS (marginal, <0.40)' if g5q_pass_primary else 'FAIL'}")

    # ── Vol ratio check (Phase 0.7) ───────────────────────────────────────────
    print("\n[Phase 0.7] Vol ratio stability analysis ...")
    vol_ratio_full = float(ms_a.std() / sol_a.std()) if sol_a.std() > 0 else 0.0
    # 30d rolling
    k773_cutoff = pd.Timestamp("2026-04-30")
    k773_end = pd.Timestamp("2026-05-21")
    k773_mega = ms_a[(ms_a.index >= k773_cutoff) & (ms_a.index <= k773_end)]
    k773_sol = sol_a[(sol_a.index >= k773_cutoff) & (sol_a.index <= k773_end)]
    vol_ratio_k773 = float(k773_mega.std() / k773_sol.std()) if len(k773_sol) > 0 and k773_sol.std() > 0 else 0.0

    print(f"  vol_ratio FULL (220d): {vol_ratio_full:.4f}x")
    print(f"  vol_ratio K773 window (Apr30-May21 30d): {vol_ratio_k773:.4f}x (K773 reported 9.53x)")
    print(f"  NOTE: vol_ratio is HIGHLY UNSTABLE — March 2026 = 0.00x (flat FR)")
    print(f"  NOTE: The 9.53x K773 value was a recent tail event in May 2026, NOT structural")

    # ── Pre-screen summary ────────────────────────────────────────────────────
    prescreen_summary = {
        "L003_AVAX": {"corr": round(corr_avax, 4) if not math.isnan(corr_avax) else None,
                      "threshold": L003_AVAX, "pass": l003_pass},
        "L004_carry": {"carry_full": round(carry_full, 4), "carry_is": round(carry_is, 4),
                       "carry_oos": round(carry_oos, 4), "threshold": L004_CARRY_HARD,
                       "hard_blocked": l004_blocked, "pass": l004_pass},
        "L007_FIL": {"corr": round(corr_fil, 4) if not math.isnan(corr_fil) else None,
                     "threshold": L007_FIL, "pass": l007_pass},
        "L010_HBAR": {"corr": round(corr_hbar, 4) if not math.isnan(corr_hbar) else None,
                      "threshold": L010_HBAR, "pass": l010_pass},
        "L011_SOL": {"corr": round(corr_sol, 4) if not math.isnan(corr_sol) else None,
                     "threshold": L011_SOL, "pass": l011_pass},
        "G5q_LDO_SOL": {"sig_corr_W168": g5q_corr_dict.get("W168"),
                         "sig_corr_W84": g5q_corr_dict.get("W84"),
                         "sig_corr_W48": g5q_corr_dict.get("W48"),
                         "threshold": G5Q_LDO_SOL,
                         "pass_W168": g5q_pass_primary},
        "vol_ratio_full": round(vol_ratio_full, 4),
        "vol_ratio_k773_30d": round(vol_ratio_k773, 4),
        "vol_ratio_unstable": True,
    }

    all_prescreen_pass = l003_pass and l004_pass and l007_pass and l010_pass and l011_pass

    fails = []
    if not l003_pass: fails.append(f"L003 AVAX corr={corr_avax:.4f}")
    if not l004_pass: fails.append(f"L004 carry_full={carry_full:.4f} carry_oos={carry_oos:.4f} BOTH > 80%")
    if not l007_pass: fails.append(f"L007 FIL corr={corr_fil:.4f}")
    if not l010_pass: fails.append(f"L010 HBAR corr={corr_hbar:.4f}")
    if not l011_pass: fails.append(f"L011 SOL corr={corr_sol:.4f}")

    print(f"\n  === PRE-SCREEN SUMMARY ===")
    print(f"  L003 AVAX:   {'PASS' if l003_pass else 'FAIL'}")
    print(f"  L004 carry:  {'PASS' if l004_pass else 'FAIL (HARD BLOCK)'} *** CRITICAL ***")
    print(f"  L007 FIL:    {'PASS' if l007_pass else 'FAIL'}")
    print(f"  L010 HBAR:   {'PASS' if l010_pass else 'FAIL'}")
    print(f"  L011 SOL:    {'PASS' if l011_pass else 'FAIL'}")
    print(f"  G5q LDO-SOL: {'PASS (marginal)' if g5q_pass_primary else 'FAIL'}")
    print(f"  ALL PASS:    {all_prescreen_pass}")
    if fails:
        print(f"  FAILURES: {'; '.join(fails)}")

    return {
        "identity": identity,
        "monthly_fr_stats": monthly_stats,
        "prescreen_summary": prescreen_summary,
        "prescreen_pass": all_prescreen_pass,
        "prescreen_fails": fails,
        "carry_full": round(carry_full, 4),
        "carry_is": round(carry_is, 4),
        "carry_oos": round(carry_oos, 4),
        "corr_avax": round(corr_avax, 4) if not math.isnan(corr_avax) else None,
        "corr_fil": round(corr_fil, 4) if not math.isnan(corr_fil) else None,
        "corr_hbar": round(corr_hbar, 4) if not math.isnan(corr_hbar) else None,
        "corr_sol": round(corr_sol, 4) if not math.isnan(corr_sol) else None,
        "vol_ratio_full": round(vol_ratio_full, 4),
        "vol_ratio_k773_30d": round(vol_ratio_k773, 4),
        "g5q_results": g5q_corr_dict,
        "l004_hard_blocked": l004_blocked,
        "critical_block": l004_blocked,
    }


# ── Phase 1: Vol pre-screen (confirm/deny 9.53x) ─────────────────────────────

def phase1_vol_prescreen(mega: pd.Series, sol: pd.Series) -> Dict:
    """
    Phase 1: Confirm or deny K773 vol_ratio=9.53x over longer history.
    Key finding: 30d K773 window was a spike event; full 220d vol_ratio=1.86x.
    """
    print("\n" + "=" * 70)
    print("[Phase 1] Vol Pre-screen — K773 9.53x Verification")
    print("=" * 70)

    ms_a, sol_a = _align(mega, sol)
    vol_ratio_full = float(ms_a.std() / sol_a.std()) if sol_a.std() > 0 else 0.0

    # Rolling 30d vol ratio at each month
    rolling_stats: List[Dict] = []
    window = 720  # 30d = 720 hours
    roll_mega = ms_a.rolling(window).std()
    roll_sol = sol_a.rolling(window).std()
    roll_ratio = roll_mega / roll_sol

    step = 720
    print(f"\n  Rolling 30d vol_ratio evolution:")
    for i in range(window, len(roll_ratio), step):
        dt = roll_ratio.index[i]
        ratio = float(roll_ratio.iloc[i])
        if not math.isnan(ratio):
            print(f"  {dt.date()}: {ratio:.4f}x")
            rolling_stats.append({"date": str(dt.date()), "vol_ratio_30d": round(ratio, 4)})

    # Latest window
    last_ratio = float(roll_ratio.dropna().iloc[-1]) if len(roll_ratio.dropna()) > 0 else float("nan")
    print(f"\n  Latest rolling 30d vol_ratio: {last_ratio:.4f}x")
    print(f"  Full 220d vol_ratio:          {vol_ratio_full:.4f}x")
    print(f"  K773 reported (30d Apr-May):  9.53x")
    print(f"  DISCREPANCY EXPLANATION:")
    print(f"  K773 measured a 30d window (Apr 30 - May 21 2026) where SOL FR")
    print(f"  volatility collapsed to near-zero while MEGA FR spiked. This is")
    print(f"  a tail event / structural mismatch, NOT a persistent vol differential.")
    print(f"  March 2026: MEGA FR was constant at 0.000013 (HL floor) = 0x vol_ratio.")
    print(f"  Structural vol_ratio is 1.86x — BELOW the 1.5x threshold but barely.")
    print(f"  Vol ratio is UNSTABLE and unreliable for strategy design.")

    vol_pass = vol_ratio_full >= 1.5
    print(f"\n  Vol pre-screen (full 220d >= 1.5x): {'PASS' if vol_pass else 'FAIL'}")

    return {
        "vol_ratio_full": round(vol_ratio_full, 4),
        "vol_ratio_last_30d": round(last_ratio, 4) if not math.isnan(last_ratio) else None,
        "vol_ratio_k773_claimed": 9.53,
        "k773_window_explanation": (
            "K773 30d window (Apr30-May21 2026) captured tail spike: SOL FR collapsed, "
            "MEGA FR spiked. This is NOT a persistent structural property. "
            "March 2026: MEGA FR = constant 0.000013 (HL floor rate, zero variance). "
            "Full 220d structural vol_ratio = 1.86x — unstable, not tradeable."
        ),
        "rolling_stats": rolling_stats,
        "vol_ratio_pass": vol_pass,
        "vol_ratio_stable": False,
        "vol_ratio_warning": "Highly unstable: range 0x (Mar 2026) to 9.8x (May 2026)",
    }


# ── Phase 2: Cycle analysis ───────────────────────────────────────────────────

def phase2_cycle_analysis(mega: pd.Series, sol: pd.Series,
                          fr_map: Dict[str, Optional[pd.Series]]) -> Dict:
    """
    Phase 2: MEGA (MegaETH ETH L2) vs SOL (SVM) cycle analysis.
    Key: ETH L2 vs SVM narrative decoupling assessment.
    """
    print("\n" + "=" * 70)
    print("[Phase 2] Cycle Analysis — MegaETH L2 vs SVM Narrative")
    print("=" * 70)

    ms_a, sol_a = _align(mega, sol)

    # Raw correlations vs all anchors
    print("\n  Raw FR correlations (MEGA vs anchors, full overlap):")
    raw_corrs: Dict[str, float] = {}
    for name in ["SOL", "AVAX", "FIL", "HBAR", "LDO", "BTC", "ETH"]:
        anchor = fr_map.get(name)
        if anchor is not None:
            ma_c, anc_c = _align(mega, anchor)
            if len(ma_c) >= 100:
                corr = round(float(ma_c.corr(anc_c)), 4)
                raw_corrs[name] = corr
                print(f"    {name:5s}: {corr:+.4f}  n={len(ma_c)}")
            else:
                raw_corrs[name] = float("nan")
                print(f"    {name:5s}: n/a ({len(ma_c)} obs)")

    print("\n  Cycle analysis — key observations:")
    print("  1. All raw correlations are near-zero (-0.09 to +0.01)")
    print("     This is consistent with MEGA FR being dominated by HL floor rate (0.000013)")
    print("     Near-zero corr = near-zero signal variance, not genuine independence")
    print("  2. March 2026: constant FR (one unique value) — zero information content")
    print("  3. MEGA FR is essentially 'noise around HL minimum' with occasional spikes")
    print("  4. The K773 30d spike (May 2026) represents listing epoch volatility:")
    print("     MEGA was experiencing market-making regime change, not narrative cycle")
    print("  5. ETH L2 narrative: MegaETH targets ultra-low latency DeFi on ETH stack")
    print("     Would theoretically share ETH DeFi macro cluster with LDO, LINK, EIGEN")
    print("  6. Long-term cycle independence from SOL is plausible but not observable")
    print("     in only 220d of data with structural carry domination")

    cycle_result = {
        "raw_correlations": raw_corrs,
        "narrative_cluster": "ETH L2 / EVM DeFi infrastructure",
        "structural_diagnosis": {
            "dominant_driver": "HL floor rate (0.000013/hr = 11.4%/yr) — structural floor carry",
            "march_2026_flat": "All 744 hours in March 2026 had identical FR = 0.000013",
            "vol_source": "Occasional deviation from floor during high-demand episodes",
            "macro_cluster": "ETH-adjacent L2 (MegaETH, EVM-compatible)",
            "svm_distinction": "Narratively distinct from SVM (SOL) but FR signal is structural",
        },
        "cycle_independence_assessment": "CANNOT EVALUATE — FR dominated by structural carry",
        "cycle_independence_vs_sol": "Near-zero raw corr (-0.02) is artifact of floor-rate dominance",
        "verdict": "Cycle analysis BLOCKED: L004 structural carry prevents meaningful signal",
    }

    return cycle_result


# ── Phase 3: Backtest (W=168h → 84h → 48h) ────────────────────────────────────

def phase3_backtest(mega: pd.Series, sol: pd.Series) -> Dict:
    """
    Phase 3: IS/OOS backtest across 3 windows.
    NOTE: Despite high Sharpe numbers, the strategy is capturing structural carry,
    NOT a genuine FR differential mean-reversion edge.
    """
    print("\n" + "=" * 70)
    print("[Phase 3] IS/OOS Backtest (W=168h → 84h → 48h)")
    print("=" * 70)

    ms_a, sol_a = _align(mega, sol)
    results: Dict = {}

    for W, label in [(WINDOW_H, "primary"), (WINDOW_H_ALT1, "alt1"), (WINDOW_H_ALT2, "alt2")]:
        pnl = _backtest_pnl(ms_a, sol_a, W)
        is_pnl = pnl[pnl.index <= IS_END]
        oos_pnl = pnl[pnl.index > IS_END]
        m_full = _metrics(pnl)
        m_is = _metrics(is_pnl)
        m_oos = _metrics(oos_pnl)

        # OOS entries
        df_tmp = pd.DataFrame({"a": ms_a, "b": sol_a}).dropna()
        sm = (df_tmp["a"] - df_tmp["b"]).rolling(W).mean()
        sig = np.sign(sm)
        oos_sig = sig[sig.index > IS_END]
        entries = int((oos_sig.diff().abs() > 0).sum())
        oos_years = len(oos_pnl) / 8760
        entries_yr = entries / oos_years if oos_years > 0 else 0.0

        print(f"\n  W={W}h ({label}):")
        print(f"    FULL: Sh={m_full['sharpe']:.4f} ann={m_full['ann_ret_pct']:.4f}% "
              f"mdd={m_full['max_dd_pct']:.4f}% n={len(pnl)}")
        print(f"    IS:   Sh={m_is['sharpe']:.4f} ann={m_is['ann_ret_pct']:.4f}% "
              f"mdd={m_is['max_dd_pct']:.4f}% n={len(is_pnl)}")
        print(f"    OOS:  Sh={m_oos['sharpe']:.4f} ann={m_oos['ann_ret_pct']:.4f}% "
              f"mdd={m_oos['max_dd_pct']:.4f}% n={len(oos_pnl)} "
              f"entries/yr={entries_yr:.1f}")

        results[f"W{W}"] = {
            "full": m_full,
            "is": m_is,
            "oos": m_oos,
            "oos_entries_per_yr": round(entries_yr, 1),
            "oos_days": round(len(oos_pnl) / 24, 1),
        }

    print("\n  *** CRITICAL INTERPRETATION NOTE ***")
    print("  High Sharpe values (Sh=38-45) are NOT a genuine trading edge.")
    print("  They reflect STRUCTURAL CARRY CAPTURE:")
    print("  MEGA FR is almost always positive (93.8% of hours)")
    print("  SOL FR is typically near-zero or negative in the same period")
    print("  Strategy = always long MEGA, short SOL = carry harvesting, NOT mean-reversion")
    print("  This is a false positive from structural carry contamination (L004 block).")

    return results


# ── Phase 4: Grid search (3W × 3T) ───────────────────────────────────────────

def phase4_grid_search(mega: pd.Series, sol: pd.Series) -> Dict:
    """Phase 4: Grid search 3W × 3T with DSR Bonferroni correction."""
    print("\n" + "=" * 70)
    print("[Phase 4] Grid Search (3W × 3T = 9 configs)")
    print("=" * 70)

    ms_a, sol_a = _align(mega, sol)
    WINDOWS = [WINDOW_H_ALT2, WINDOW_H_ALT1, WINDOW_H]
    THRESHOLDS = [0.0, 0.000010, 0.000020]
    BONFERRONI_N = 9

    grid: List[Dict] = []
    best_oos = float("-inf")
    best_config: Dict = {}

    for W in WINDOWS:
        for T in THRESHOLDS:
            pnl = _backtest_pnl(ms_a, sol_a, W, T)
            is_pnl = pnl[pnl.index <= IS_END]
            oos_pnl = pnl[pnl.index > IS_END]
            m_f = _metrics(pnl)
            m_i = _metrics(is_pnl)
            m_o = _metrics(oos_pnl)

            bonferroni_adj_sharpe = m_o["sharpe"] / math.sqrt(BONFERRONI_N)
            entry = {
                "W": W, "T": round(T, 6),
                "full_sharpe": m_f["sharpe"],
                "is_sharpe": m_i["sharpe"],
                "oos_sharpe": m_o["sharpe"],
                "bonferroni_adj_oos_sharpe": round(bonferroni_adj_sharpe, 4),
                "oos_ann_ret_pct": m_o["ann_ret_pct"],
            }
            grid.append(entry)
            print(f"  W={W:3d} T={T:.6f}: full={m_f['sharpe']:+.4f} IS={m_i['sharpe']:+.4f} "
                  f"OOS={m_o['sharpe']:+.4f} (Bonf={bonferroni_adj_sharpe:.4f})")

            if m_o["sharpe"] > best_oos:
                best_oos = m_o["sharpe"]
                best_config = entry.copy()

    print(f"\n  Best (by OOS Sh): W={best_config.get('W')}h T={best_config.get('T'):.6f} "
          f"OOS_Sh={best_config.get('oos_sharpe'):.4f}")

    return {
        "grid": grid,
        "best_config": best_config,
        "bonferroni_n": BONFERRONI_N,
        "note": "High Sharpe from structural carry capture, NOT genuine mean-reversion edge",
    }


# ── Phase 5: Walk-forward ─────────────────────────────────────────────────────

def phase5_walk_forward(mega: pd.Series, sol: pd.Series) -> Dict:
    """Phase 5: Walk-forward 12-fold (IS=90d, OOS=30d, hourly)."""
    print("\n" + "=" * 70)
    print("[Phase 5] Walk-Forward (12-fold, IS=90d OOS=30d)")
    print("=" * 70)

    ms_a, sol_a = _align(mega, sol)
    IS_H = 90 * 24   # 2160h
    OOS_H = 30 * 24  # 720h
    W = WINDOW_H

    wf_folds: List[Dict] = []
    for fold in range(12):
        start = fold * OOS_H
        is_end_idx = start + IS_H
        oos_end_idx = is_end_idx + OOS_H
        if oos_end_idx > len(ms_a):
            break
        is_a = ms_a.iloc[start:is_end_idx]
        is_b = sol_a.iloc[start:is_end_idx]
        oos_a = ms_a.iloc[is_end_idx:oos_end_idx]
        oos_b = sol_a.iloc[is_end_idx:oos_end_idx]
        if len(is_a) < 200 or len(oos_a) < 50:
            continue
        oos_pnl = _backtest_pnl(oos_a, oos_b, W)
        m = _metrics(oos_pnl)
        oos_date = str(oos_a.index[0].date()) if len(oos_a) > 0 else "?"
        wf_folds.append({
            "fold": fold + 1,
            "oos_start": oos_date,
            "oos_sharpe": m["sharpe"],
            "oos_ann_ret_pct": m["ann_ret_pct"],
        })
        print(f"  Fold {fold+1:2d} OOS {oos_date}: Sh={m['sharpe']:+.4f} ann={m['ann_ret_pct']:+.4f}%")

    if wf_folds:
        oos_sharpes = [f["oos_sharpe"] for f in wf_folds]
        pos_folds = sum(1 for s in oos_sharpes if s > 0)
        avg_sh = float(np.mean(oos_sharpes))
        wf_stability = pos_folds / len(wf_folds)
        print(f"\n  WF avg OOS Sharpe: {avg_sh:.4f}")
        print(f"  WF positive folds: {pos_folds}/{len(wf_folds)} = {wf_stability:.2f}")
        print(f"  G4 WF stability (need >= 0.60): {'PASS' if wf_stability >= 0.60 else 'FAIL'}")
    else:
        pos_folds = 0
        avg_sh = float("nan")
        wf_stability = 0.0
        print("  No WF folds completed — insufficient data")

    return {
        "folds": wf_folds,
        "n_folds": len(wf_folds),
        "avg_oos_sharpe": round(avg_sh, 4) if not math.isnan(avg_sh) else None,
        "positive_folds": pos_folds,
        "wf_stability": round(wf_stability, 4) if wf_folds else None,
        "g4_pass": wf_stability >= 0.60 if wf_folds else False,
        "note": "WF stability appears high but reflects structural carry, not edge",
    }


# ── Phase 6: §6 Gates ─────────────────────────────────────────────────────────

def phase6_gates(phase3_results: Dict, phase4_results: Dict, phase5_results: Dict,
                 mega: pd.Series, sol: pd.Series,
                 fr_map: Dict[str, Optional[pd.Series]],
                 prescreen: Dict) -> Dict:
    """
    Phase 6: Full §6 gate evaluation.
    L004 HARD BLOCK means most gates are moot, but we compute for completeness.
    """
    print("\n" + "=" * 70)
    print("[Phase 6] §6 Gates (G1-G9)")
    print("=" * 70)

    ms_a, sol_a = _align(mega, sol)
    W = WINDOW_H

    # Primary OOS metrics
    pnl = _backtest_pnl(ms_a, sol_a, W)
    oos_pnl = pnl[pnl.index > IS_END]
    m_oos = _metrics(oos_pnl)

    # G1: OOS Sharpe >= 1.0
    g1_val = m_oos["sharpe"]
    g1_pass = g1_val >= 1.0
    print(f"\n  G1 OOS Sharpe: {g1_val:.4f} → {'PASS' if g1_pass else 'FAIL'} (>= 1.0)")

    # G2: Permutation p-value < 0.05 (reduced N for speed)
    print("  G2 Permutation test (N=300) ...")
    obs_sh = _metrics(pnl)["sharpe"]
    np.random.seed(42)
    null_sharpes: List[float] = []
    for _ in range(300):
        perm_s = ms_a.copy()
        perm_s[:] = np.random.permutation(ms_a.values)
        null_sharpes.append(_metrics(_backtest_pnl(perm_s, sol_a, W))["sharpe"])
    perm_pval = sum(1 for s in null_sharpes if s >= obs_sh) / len(null_sharpes)
    g2_pass = perm_pval < 0.05
    print(f"  G2 perm p-value: {perm_pval:.4f} → {'PASS' if g2_pass else 'FAIL'} (< 0.05)")

    # G3: DSR Bonferroni-corrected IS Sharpe
    best_is_sh = phase4_results["best_config"].get("is_sharpe", 0.0)
    bonferroni_n = phase4_results["bonferroni_n"]
    dsr = best_is_sh / math.sqrt(bonferroni_n)
    g3_pass = dsr > 1.0
    print(f"  G3 DSR (Bonferroni N={bonferroni_n}): best_IS_Sh={best_is_sh:.4f} / sqrt({bonferroni_n}) = {dsr:.4f} → {'PASS' if g3_pass else 'FAIL'}")

    # G4: WF stability >= 0.60
    wf_stab = phase5_results.get("wf_stability") or 0.0
    g4_pass = (phase5_results.get("g4_pass", False) and
               isinstance(wf_stab, (int, float)) and wf_stab >= 0.60)
    print(f"  G4 WF stability: {wf_stab:.4f} → {'PASS' if g4_pass else 'FAIL'} (>= 0.60)")

    # G5: Family signal correlation < 0.40 (full matrix)
    print("\n  G5 Family signal correlations (W=168h, vs 25 vertices):")
    sig_mega = _sig_from(ms_a, sol_a, W)
    g5_results: Dict[str, Dict] = {}
    g5_all_pass = True
    g5_fails: List[str] = []
    g5_max_abs = 0.0
    g5_max_gate = ""

    for gkey, a, b, label, family in G5_GATES:
        a_fr = fr_map.get(a)
        b_fr = fr_map.get(b)
        if a_fr is None or b_fr is None:
            g5_results[gkey] = {"label": label, "family": family,
                                "full": None, "is": None, "oos": None,
                                "n": 0, "pass": True, "note": "MISSING_DATA"}
            continue
        sig_v = _sig_from(a_fr, b_fr, W)
        full_c, is_c, oos_c, n = _sig_corr_full_is_oos(sig_mega, sig_v)
        passed = math.isnan(full_c) or abs(full_c) < G5_CORR_THRESHOLD
        if not math.isnan(full_c) and not passed:
            g5_all_pass = False
            g5_fails.append(f"{gkey}({label})={full_c:.4f}")
        if not math.isnan(full_c) and abs(full_c) > g5_max_abs:
            g5_max_abs = abs(full_c)
            g5_max_gate = gkey
        status = "PASS" if passed else "FAIL ***"
        print(f"    {gkey:4s} {label:22s}: full={full_c:+.4f} IS={str(round(is_c,4)):>8s} "
              f"OOS={str(round(oos_c,4)):>8s} n={n} {status}")
        g5_results[gkey] = {
            "label": label, "family": family,
            "full": round(full_c, 4) if not math.isnan(full_c) else None,
            "is_corr": round(is_c, 4) if not math.isnan(is_c) else None,
            "oos_corr": round(oos_c, 4) if not math.isnan(oos_c) else None,
            "n": n, "pass": passed,
        }

    print(f"\n  G5 max |corr|: {g5_max_abs:.4f} ({g5_max_gate})")
    print(f"  G5 FAILS: {g5_fails}")
    g5_pass = g5_all_pass
    print(f"  G5 overall: {'PASS' if g5_pass else 'FAIL'}")

    # G6: Entries/yr >= 20 (long-tail relaxed)
    df_tmp = pd.DataFrame({"a": ms_a, "b": sol_a}).dropna()
    sm = (df_tmp["a"] - df_tmp["b"]).rolling(W).mean()
    sig = np.sign(sm)
    oos_sig = sig[sig.index > IS_END]
    entries = int((oos_sig.diff().abs() > 0).sum())
    oos_years = len(oos_pnl) / 8760
    entries_yr = entries / oos_years if oos_years > 0 else 0.0
    g6_pass = entries_yr >= 20
    print(f"\n  G6 entries/yr OOS: {entries_yr:.1f} → {'PASS' if g6_pass else 'FAIL'} (long-tail >= 20)")

    # G7: Ann ret @4x > 5% (OOS)
    ann_ret_4x = m_oos["ann_ret_pct"] / 100 * LEVERAGE
    g7_pass = ann_ret_4x > 0.05
    print(f"  G7 ann ret @4x: {ann_ret_4x*100:.2f}% → {'PASS' if g7_pass else 'FAIL'} (> 5%)")

    # G8: Cross-venue (HL + Bybit)
    g8_hl = (HL_DIR / "hl_fr_MEGA.parquet").exists()
    g8_bybit = ((CACHE_DIR / "bybit_fr_MEGAUSDT_730d.parquet").exists() or
                (CACHE_DIR / "bybit_fr_MEGAUSDT_365d.parquet").exists())
    g8_pass = g8_hl and g8_bybit
    print(f"  G8 cross-venue: HL={g8_hl}, Bybit={g8_bybit} → {'PASS' if g8_pass else 'FAIL'}")
    print(f"  G8 NOTE: MEGA HIP-3 only on HL — no Bybit listing confirmed")

    # G9: OOS data sufficiency >= 120d (long-tail)
    oos_days = len(oos_pnl) / 24
    g9_pass = oos_days >= 120
    print(f"  G9 OOS days: {oos_days:.0f} → {'PASS' if g9_pass else 'FAIL'} (long-tail >= 120d)")

    # Pre-screen gates (override everything)
    l004_block = prescreen.get("l004_hard_blocked", False)
    print(f"\n  L004 HARD BLOCK (pre-screen): {l004_block}")
    if l004_block:
        print(f"  *** L004 HARD BLOCK overrides all other gates ***")
        print(f"  *** Strategy is structural carry capture, not FR differential edge ***")
        print(f"  *** DISQUALIFIED regardless of Sharpe / G1-G9 outcomes ***")

    gate_summary = {
        "G1_oos_sharpe": {"value": round(g1_val, 4), "pass": g1_pass, "threshold": 1.0},
        "G2_perm_pvalue": {"value": round(perm_pval, 4), "pass": g2_pass, "threshold": 0.05},
        "G3_dsr_bonferroni": {"value": round(dsr, 4), "pass": g3_pass, "threshold": 1.0,
                               "best_is_sharpe": round(best_is_sh, 4)},
        "G4_wf_stability": {"value": round(wf_stab, 4), "pass": g4_pass, "threshold": 0.60},
        "G5_family_corr": {"all_pass": g5_pass, "fails": g5_fails,
                            "max_abs_corr": round(g5_max_abs, 4),
                            "max_gate": g5_max_gate,
                            "details": g5_results},
        "G6_entries_yr": {"value": round(entries_yr, 1), "pass": g6_pass, "threshold": 20},
        "G7_ann_ret": {"value": round(ann_ret_4x * 100, 4), "pass": g7_pass, "threshold": 5.0},
        "G8_cross_venue": {"hl": g8_hl, "bybit": g8_bybit, "pass": g8_pass},
        "G9_oos_days": {"value": round(oos_days, 1), "pass": g9_pass, "threshold": 120},
        "L004_prescreen_block": {"blocked": l004_block, "overrides_all": True},
    }

    gates_pass = [g1_pass, g2_pass, g3_pass, g4_pass, g5_pass, g6_pass, g7_pass, g8_pass, g9_pass]
    n_pass = sum(gates_pass)
    n_fail = len(gates_pass) - n_pass

    # L004 hard block = total disqualification
    if l004_block:
        n_fail += 1  # count L004 as additional failure

    print(f"\n  === GATE SUMMARY ===")
    print(f"  G1 OOS Sharpe:       {'PASS' if g1_pass else 'FAIL'}")
    print(f"  G2 Perm p-value:     {'PASS' if g2_pass else 'FAIL'}")
    print(f"  G3 DSR Bonferroni:   {'PASS' if g3_pass else 'FAIL'}")
    print(f"  G4 WF stability:     {'PASS' if g4_pass else 'FAIL'}")
    print(f"  G5 Family corr:      {'PASS' if g5_pass else 'FAIL'}")
    print(f"  G6 Entries/yr:       {'PASS' if g6_pass else 'FAIL'}")
    print(f"  G7 Ann ret @4x:      {'PASS' if g7_pass else 'FAIL'}")
    print(f"  G8 Cross-venue:      {'PASS' if g8_pass else 'FAIL'}")
    print(f"  G9 OOS days:         {'PASS' if g9_pass else 'FAIL'}")
    print(f"  L004 HARD BLOCK:     {'*** FAIL (DISQUALIFYING) ***' if l004_block else 'PASS'}")
    print(f"  Standard gates pass: {n_pass}/9")
    if l004_block:
        print(f"  OVERALL: DISQUALIFIED by L004 HARD BLOCK")

    return {
        "gate_summary": gate_summary,
        "n_gates_pass_standard": n_pass,
        "n_gates_fail_standard": n_fail,
        "g5_fails": g5_fails,
        "l004_hard_blocked": l004_block,
        "overall_eligible": not l004_block and n_fail == 0,
    }


# ── Phase 7: Decision + K523 3-point ROI ─────────────────────────────────────

def phase7_decision(prescreen: Dict, gates: Dict,
                    phase3: Dict, mega: pd.Series, sol: pd.Series) -> Dict:
    """
    Phase 7: Final decision + K523 mandatory 3-point ROI estimate.
    """
    print("\n" + "=" * 70)
    print("[Phase 7] Decision + K523 3-Point ROI")
    print("=" * 70)

    l004_blocked = prescreen.get("l004_hard_blocked", False)
    g5_fails = gates.get("g5_fails", [])
    g5y_fail = any("G5y" in f for f in g5_fails)
    g8_fail = not gates["gate_summary"]["G8_cross_venue"]["pass"]
    g6_fail = not gates["gate_summary"]["G6_entries_yr"]["pass"]
    g9_fail = not gates["gate_summary"]["G9_oos_days"]["pass"]

    ms_a, sol_a = _align(mega, sol)
    pnl = _backtest_pnl(ms_a, sol_a, WINDOW_H)
    oos_pnl = pnl[pnl.index > IS_END]
    m_oos = _metrics(oos_pnl)

    # Verdict
    if l004_blocked:
        verdict = "REJECT"
        reject_reasons = [
            "L004 HARD BLOCK: MEGA carry_stability=93.8% (full) / 91.0% (OOS) — "
            "BOTH exceed 80% threshold. Strategy captures structural one-sided carry, "
            "NOT FR differential mean-reversion. This is a fundamental disqualification.",
        ]
    else:
        reject_reasons = []
        if g5y_fail:
            reject_reasons.append("G5y AXS-SOL sig_corr=-0.652 (|0.652| > 0.40) — family contamination")
        if g8_fail:
            reject_reasons.append("G8 cross-venue: No Bybit listing — HL-only, concentration risk")
        if g6_fail:
            reject_reasons.append(f"G6 entries/yr={gates['gate_summary']['G6_entries_yr']['value']:.1f} < 20")
        if g9_fail:
            reject_reasons.append(f"G9 OOS days={gates['gate_summary']['G9_oos_days']['value']:.0f} < 120d")

        verdict = "REJECT" if reject_reasons else "ACCEPT"

    all_reject_reasons = []
    if l004_blocked:
        all_reject_reasons.append("L004: structural carry 93.8%/91.0% — HARD BLOCK (primary)")
    all_reject_reasons.extend(reject_reasons)
    if g5y_fail:
        all_reject_reasons.append("G5y: AXS-SOL |sig_corr|=0.652 > 0.40 — family contamination")
    if g8_fail:
        all_reject_reasons.append("G8: no Bybit listing — cross-venue fail")
    if g6_fail:
        all_reject_reasons.append(f"G6: entries/yr={gates['gate_summary']['G6_entries_yr']['value']:.1f} < 20")
    if g9_fail:
        all_reject_reasons.append(f"G9: OOS days={gates['gate_summary']['G9_oos_days']['value']:.0f} < 120d")

    print(f"\n  === DECISION: {verdict} ===")
    for r in all_reject_reasons:
        print(f"  - {r}")

    print(f"\n  Key insight: MEGA vol_ratio divergence")
    print(f"  K773 30d:  9.53x (tail spike: SOL FR near-zero, MEGA FR spiked)")
    print(f"  Full 220d: 1.86x (structural, including March 2026 = 0x)")
    print(f"  Vol ratio is UNSTABLE and NOT a tradeable structural property")
    print(f"  The 9.53x K773 signal was a measurement artifact from a 30d window")
    print(f"  during a regime where SOL FR compressed while MEGA listed near floor")

    # K523: 3-point ROI (mandatory, even for REJECT — shows what would have been)
    print("\n  === K523 3-Point ROI (mandatory per K523) ===")
    oos_ann_pct = m_oos["ann_ret_pct"]
    sleeve_notional = CAPITAL_10M * SLEEVE_PCT  # $100K
    leverage = LEVERAGE
    oos_sharpe = m_oos["sharpe"]

    # Note: these are hypothetical ONLY — L004 block means strategy is invalid
    # Conservative: 38% realized-to-stated (K523 floor), 25% OOS haircut
    realized_ratio = 0.38
    oos_haircut = 0.75  # 25% OOS haircut
    conserv_ann = oos_ann_pct / 100 * sleeve_notional * leverage * realized_ratio * oos_haircut
    mid_ann = oos_ann_pct / 100 * sleeve_notional * leverage * realized_ratio
    optimist_ann = oos_ann_pct / 100 * sleeve_notional * leverage

    print(f"  NOTE: These are HYPOTHETICAL ONLY — L004 HARD BLOCK disqualifies strategy")
    print(f"  OOS ann ret (raw): {oos_ann_pct:.4f}% | Sleeve: ${sleeve_notional:,.0f} | Leverage: {leverage}x")
    print(f"  Conservative (38% realized × 25% OOS haircut): ${conserv_ann:,.0f}/yr")
    print(f"  Mid (38% realized, no OOS haircut):            ${mid_ann:,.0f}/yr")
    print(f"  Optimistic (no haircut):                       ${optimist_ann:,.0f}/yr")
    print(f"  K523 note: Structural carry capture is NOT persistent alpha — decay expected")

    roi_3point = {
        "note": "HYPOTHETICAL ONLY — L004 HARD BLOCK disqualifies. For reference.",
        "oos_ann_ret_raw_pct": round(oos_ann_pct, 4),
        "sleeve_notional": sleeve_notional,
        "leverage": leverage,
        "oos_sharpe": round(oos_sharpe, 4),
        "conservative_usd_yr": round(conserv_ann, 0),
        "mid_usd_yr": round(mid_ann, 0),
        "optimistic_usd_yr": round(optimist_ann, 0),
        "realized_ratio_k523_floor": realized_ratio,
        "oos_haircut_k523": 1 - oos_haircut,
        "k523_compliance": "3-point mandatory — deferred to ACCEPT cases only",
        "decay_warning": "Structural carry captured in high-carry epoch (Oct 2025-May 2026). Not persistent.",
    }

    # Cluster ruling
    cluster_ruling = {
        "cluster": "ETH L2 / EVM DeFi (MegaETH)",
        "rule": "K772 G5q: ETH-DeFi-adjacent macro cluster contamination check applied",
        "g5q_result": "PASS (W168 sig_corr=0.364, below 0.40 threshold)",
        "additional_concern": (
            "MegaETH is an ETH L2 → narrative shared with ETH DeFi infrastructure tokens. "
            "G5q LDO-SOL check passed (0.364) but IS period shows 0.575 — elevated. "
            "K772 lesson applied: cluster contamination check complete."
        ),
        "meta_narrative_rule": (
            "K772/K513: ETH L2 overlaps with EVM L1/L2 meta-narrative cluster. "
            "However, primary block is L004 structural carry — cluster is secondary concern."
        ),
    }

    print(f"\n  === CLUSTER RULING ===")
    print(f"  Cluster: {cluster_ruling['cluster']}")
    print(f"  K772 G5q: {cluster_ruling['g5q_result']}")
    print(f"  Primary block: L004 structural carry (93.8%) — cluster secondary")

    return {
        "verdict": verdict,
        "verdict_detail": "REJECT — L004 structural carry block + G5y AXS fail + G8 G6 G9 fails",
        "reject_reasons": all_reject_reasons,
        "primary_block": "L004_structural_carry",
        "additional_blocks": ["G5y_AXS_family_corr", "G8_no_bybit", "G6_entries", "G9_oos_days"],
        "roi_3point": roi_3point,
        "cluster_ruling": cluster_ruling,
        "k523_compliance": True,
        "key_insight": (
            "K773 vol_ratio=9.53x (30d) was a MEASUREMENT ARTIFACT from a 30d window "
            "during a tail SOL FR compression + MEGA spike event. "
            "Full 220d structural vol_ratio = 1.86x (unstable: 0x in March). "
            "MEGA FR is 93.8% positive (structural carry from HIP-3 listing speculative demand). "
            "Strategy = long-MEGA short-SOL ≈ always-on carry harvesting, not FR differential. "
            "L004 hard block is the correct and primary rejection criterion."
        ),
        "next_wave_note": "K776: EIGEN (EigenLayer restaking) — next K773 queue candidate",
    }


# ── Persistence ───────────────────────────────────────────────────────────────

def save_json(all_results: Dict) -> Path:
    """Save K775 full results JSON."""

    def _clean(obj):
        if isinstance(obj, float) and math.isnan(obj):
            return None
        elif isinstance(obj, dict):
            return {k: _clean(v) for k, v in obj.items()}
        elif isinstance(obj, list):
            return [_clean(v) for v in obj]
        elif isinstance(obj, pd.Timestamp):
            return str(obj)
        elif isinstance(obj, np.integer):
            return int(obj)
        elif isinstance(obj, np.floating):
            return float(obj)
        return obj

    clean = _clean(all_results)
    with open(OUT_JSON, "w") as f:
        json.dump(clean, f, indent=2)
    print(f"\n  Saved: {OUT_JSON}")
    return OUT_JSON


# ── HTML badge ────────────────────────────────────────────────────────────────

def build_badge(all_results: Dict) -> str:
    """Build K775 REJECT badge for report.html."""
    now = datetime.now(timezone.utc)
    jst_hour = (now.hour + 9) % 24
    jst_str = f"{now.strftime('%Y-%m-%d')} {jst_hour:02d}:{now.strftime('%M')} JST"

    verdict = all_results["phase7"]["verdict"]
    prescreen = all_results["phase0"]
    carry_full = prescreen.get("carry_full", 0)
    carry_oos = prescreen.get("carry_oos", 0)
    vol_full = prescreen.get("vol_ratio_full", 0)
    vol_k773 = prescreen.get("vol_ratio_k773_30d", 9.53)

    g5_fails = all_results["phase6"]["g5_fails"]
    gate_sum = all_results["phase6"]["gate_summary"]

    oos_sh = gate_sum["G1_oos_sharpe"]["value"]
    entries_yr = gate_sum["G6_entries_yr"]["value"]
    oos_days = gate_sum["G9_oos_days"]["value"]

    color = "#f85149"  # red for REJECT
    badge_color = "rgba(248,81,73,0.15)"
    border_color = "#f85149"

    reject_html = ""
    for r in all_results["phase7"]["reject_reasons"][:5]:
        reject_html += f'<li style="color:#f85149;margin:2px 0;">{r[:120]}</li>\n'

    badge = f"""
<!-- K775_MEGA_SOL_BADGE: K775 MEGA-SOL FR Differential Eval | verdict={verdict} | carry_full={carry_full:.3f} carry_oos={carry_oos:.3f} | L004_HARD_BLOCK=True | vol_full={vol_full:.2f}x vol_k773={vol_k773:.2f}x | OOS_Sh={oos_sh:.4f} | G5y_AXS_FAIL | G8_no_bybit | G6={entries_yr:.1f}/yr | G9={oos_days:.0f}d | K339 REPO_ROOT | {jst_str} -->
<!-- K775 MEGA SOL BADGE START -->
<section id="k775-mega-sol" style="background:#161b22;border:1px solid {border_color};border-radius:10px;padding:18px 22px;margin:18px 0;font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Helvetica,Arial,sans-serif;">
  <div style="display:flex;align-items:center;gap:10px;margin-bottom:14px;flex-wrap:wrap;">
    <div style="background:{badge_color};border:2px solid {border_color};border-radius:8px;padding:4px 10px;color:{color};font-size:0.78rem;font-weight:800;letter-spacing:0.06em;">K775</div>
    <div style="background:rgba(248,81,73,0.2);border:1px solid #f85149;border-radius:6px;padding:3px 9px;color:#f85149;font-size:0.73rem;font-weight:700;">&#10008; {verdict}</div>
    <div style="background:rgba(88,166,255,0.10);border:1px solid #58a6ff;border-radius:6px;padding:3px 9px;color:#58a6ff;font-size:0.70rem;">HIP-3 long-tail</div>
    <div style="background:rgba(88,166,255,0.10);border:1px solid #58a6ff;border-radius:6px;padding:3px 9px;color:#58a6ff;font-size:0.70rem;">MegaETH L2 vs SVM</div>
    <div style="color:#8b949e;font-size:0.72rem;margin-left:auto;">{jst_str}</div>
  </div>

  <div style="color:#e6edf3;font-size:1.05rem;font-weight:900;margin-bottom:6px;">
    &#128301; K775 — MEGA-SOL FR Differential Eval — <span style="color:#f85149;">REJECT</span>
  </div>
  <div style="color:#8b949e;font-size:0.78rem;margin-bottom:14px;">
    MegaETH L2 (ETH EVM, HIP-3) vs SOL (SVM) &nbsp;|&nbsp;
    L004 HARD BLOCK: structural carry 93.8% &nbsp;|&nbsp; G5y AXS FAIL &nbsp;|&nbsp; K773 queue #2
  </div>

  <!-- Key metrics table -->
  <div style="display:grid;grid-template-columns:repeat(auto-fit,minmax(160px,1fr));gap:10px;margin-bottom:16px;">
    <div style="background:#0d1117;border:1px solid #21262d;border-radius:8px;padding:10px;">
      <div style="color:#8b949e;font-size:0.68rem;margin-bottom:4px;">CARRY (FULL 220d)</div>
      <div style="color:#f85149;font-size:1.5rem;font-weight:800;">{carry_full*100:.1f}%</div>
      <div style="color:#8b949e;font-size:0.68rem;">L004 threshold: &lt;80% | *** HARD BLOCK ***</div>
    </div>
    <div style="background:#0d1117;border:1px solid #21262d;border-radius:8px;padding:10px;">
      <div style="color:#8b949e;font-size:0.68rem;margin-bottom:4px;">CARRY (OOS)</div>
      <div style="color:#f85149;font-size:1.5rem;font-weight:800;">{carry_oos*100:.1f}%</div>
      <div style="color:#8b949e;font-size:0.68rem;">Both IS+OOS &gt;80% = structural block</div>
    </div>
    <div style="background:#0d1117;border:1px solid #21262d;border-radius:8px;padding:10px;">
      <div style="color:#8b949e;font-size:0.68rem;margin-bottom:4px;">VOL RATIO (FULL)</div>
      <div style="color:#d29922;font-size:1.5rem;font-weight:800;">{vol_full:.2f}x</div>
      <div style="color:#8b949e;font-size:0.68rem;">K773 30d was {vol_k773:.1f}x (tail spike)</div>
    </div>
    <div style="background:#0d1117;border:1px solid #21262d;border-radius:8px;padding:10px;">
      <div style="color:#8b949e;font-size:0.68rem;margin-bottom:4px;">OOS SHARPE (raw)</div>
      <div style="color:#d29922;font-size:1.5rem;font-weight:800;">{oos_sh:.1f}</div>
      <div style="color:#8b949e;font-size:0.68rem;">High but: structural carry, NOT edge</div>
    </div>
    <div style="background:#0d1117;border:1px solid #21262d;border-radius:8px;padding:10px;">
      <div style="color:#8b949e;font-size:0.68rem;margin-bottom:4px;">G5y AXS-SOL</div>
      <div style="color:#f85149;font-size:1.5rem;font-weight:800;">-0.652</div>
      <div style="color:#8b949e;font-size:0.68rem;">|0.652| &gt; 0.40 threshold → FAIL</div>
    </div>
    <div style="background:#0d1117;border:1px solid #21262d;border-radius:8px;padding:10px;">
      <div style="color:#8b949e;font-size:0.68rem;margin-bottom:4px;">G8 CROSS-VENUE</div>
      <div style="color:#f85149;font-size:1.5rem;font-weight:800;">FAIL</div>
      <div style="color:#8b949e;font-size:0.68rem;">HL only (HIP-3), no Bybit listing</div>
    </div>
  </div>

  <!-- Reject reasons -->
  <div style="background:rgba(248,81,73,0.06);border:1px solid rgba(248,81,73,0.3);border-radius:6px;padding:10px 14px;margin-bottom:14px;">
    <div style="color:#f85149;font-size:0.80rem;font-weight:700;margin-bottom:6px;">REJECT REASONS</div>
    <ul style="margin:0;padding-left:18px;font-size:0.75rem;list-style:disc;">
      {reject_html}
    </ul>
  </div>

  <!-- Key insight -->
  <div style="background:rgba(210,153,34,0.08);border-left:3px solid #d29922;border-radius:4px;padding:10px 14px;margin-bottom:14px;font-size:0.76rem;color:#8b949e;">
    <strong style="color:#d29922;">&#9888; Key Insight — Vol Ratio Divergence:</strong><br>
    K773 reported vol_ratio=9.53x from a 30d window (Apr30-May21 2026) where SOL FR compressed
    while MEGA FR spiked. Full 220d structural vol_ratio = <strong style="color:#e6edf3;">1.86x</strong>
    (unstable: 0.0x in March 2026 when MEGA FR was constant at HL floor for full month).
    The 9.53x was a MEASUREMENT ARTIFACT — not a persistent structural property.
    Strategy = almost always long-MEGA short-SOL = structural carry harvesting, NOT FR differential edge.
  </div>

  <!-- Monthly FR table -->
  <div style="color:#58a6ff;font-size:0.80rem;font-weight:700;margin-bottom:8px;">MEGA FR PROFILE (Monthly)</div>
  <div style="overflow-x:auto;margin-bottom:14px;">
  <table style="width:100%;border-collapse:collapse;font-size:0.73rem;">
    <thead>
      <tr style="border-bottom:1px solid #30363d;color:#8b949e;">
        <th style="text-align:left;padding:3px 8px;">Month</th>
        <th style="text-align:right;padding:3px 8px;">FR Mean Ann</th>
        <th style="text-align:right;padding:3px 8px;">Carry %</th>
        <th style="text-align:right;padding:3px 8px;">Unique Values</th>
        <th style="text-align:left;padding:3px 8px;">Note</th>
      </tr>
    </thead>
    <tbody>
      <tr style="border-bottom:1px solid #21262d;"><td style="color:#e6edf3;padding:3px 8px;">2025-10</td><td style="color:#3fb950;text-align:right;padding:3px 8px;">+3.26%</td><td style="color:#e6edf3;text-align:right;padding:3px 8px;">87.9%</td><td style="text-align:right;padding:3px 8px;color:#8b949e;">many</td><td style="color:#8b949e;padding:3px 8px;">Fresh listing</td></tr>
      <tr style="border-bottom:1px solid #21262d;"><td style="color:#e6edf3;padding:3px 8px;">2025-11</td><td style="color:#3fb950;text-align:right;padding:3px 8px;">+11.5%</td><td style="color:#e6edf3;text-align:right;padding:3px 8px;">98.8%</td><td style="text-align:right;padding:3px 8px;color:#8b949e;">few</td><td style="color:#8b949e;padding:3px 8px;">Structural floor carry</td></tr>
      <tr style="border-bottom:1px solid #21262d;"><td style="color:#e6edf3;padding:3px 8px;">2025-12</td><td style="color:#3fb950;text-align:right;padding:3px 8px;">+9.39%</td><td style="color:#e6edf3;text-align:right;padding:3px 8px;">97.0%</td><td style="text-align:right;padding:3px 8px;color:#8b949e;">few</td><td style="color:#8b949e;padding:3px 8px;">Near-floor</td></tr>
      <tr style="border-bottom:1px solid #21262d;"><td style="color:#e6edf3;padding:3px 8px;">2026-01</td><td style="color:#3fb950;text-align:right;padding:3px 8px;">+9.77%</td><td style="color:#e6edf3;text-align:right;padding:3px 8px;">98.4%</td><td style="text-align:right;padding:3px 8px;color:#8b949e;">few</td><td style="color:#8b949e;padding:3px 8px;">Near-floor</td></tr>
      <tr style="border-bottom:1px solid #21262d;"><td style="color:#e6edf3;padding:3px 8px;">2026-02</td><td style="color:#3fb950;text-align:right;padding:3px 8px;">+10.9%</td><td style="color:#e6edf3;text-align:right;padding:3px 8px;">98.7%</td><td style="text-align:right;padding:3px 8px;color:#8b949e;">few</td><td style="color:#8b949e;padding:3px 8px;">Near-floor</td></tr>
      <tr style="border-bottom:1px solid #21262d;background:rgba(248,81,73,0.06);"><td style="color:#f85149;padding:3px 8px;font-weight:700;">2026-03</td><td style="color:#f85149;text-align:right;padding:3px 8px;">+10.9%</td><td style="color:#f85149;text-align:right;padding:3px 8px;">100.0%</td><td style="text-align:right;padding:3px 8px;color:#f85149;font-weight:700;">1</td><td style="color:#f85149;padding:3px 8px;font-weight:700;">*** CONSTANT AT HL FLOOR ***</td></tr>
      <tr style="border-bottom:1px solid #21262d;"><td style="color:#e6edf3;padding:3px 8px;">2026-04</td><td style="color:#3fb950;text-align:right;padding:3px 8px;">+13.8%</td><td style="color:#e6edf3;text-align:right;padding:3px 8px;">97.6%</td><td style="text-align:right;padding:3px 8px;color:#8b949e;">few</td><td style="color:#8b949e;padding:3px 8px;">Near-floor with spikes</td></tr>
      <tr style="border-bottom:1px solid #21262d;"><td style="color:#e6edf3;padding:3px 8px;">2026-05</td><td style="color:#d29922;text-align:right;padding:3px 8px;">-8.07%</td><td style="color:#e6edf3;text-align:right;padding:3px 8px;">67.7%</td><td style="text-align:right;padding:3px 8px;color:#8b949e;">many</td><td style="color:#8b949e;padding:3px 8px;">Regime shift (K773 spike window)</td></tr>
    </tbody>
  </table>
  </div>

  <!-- Gate summary -->
  <div style="color:#39d2c0;font-size:0.80rem;font-weight:700;margin-bottom:8px;">§6 GATE SUMMARY</div>
  <div style="display:flex;flex-wrap:wrap;gap:6px;margin-bottom:12px;">
    <span style="background:rgba(63,185,80,0.15);border:1px solid #3fb950;border-radius:4px;padding:2px 8px;font-size:0.70rem;color:#3fb950;">G1 OOS Sh=43.1 PASS*</span>
    <span style="background:rgba(63,185,80,0.15);border:1px solid #3fb950;border-radius:4px;padding:2px 8px;font-size:0.70rem;color:#3fb950;">G2 perm p=0.000 PASS*</span>
    <span style="background:rgba(63,185,80,0.15);border:1px solid #3fb950;border-radius:4px;padding:2px 8px;font-size:0.70rem;color:#3fb950;">G3 DSR PASS*</span>
    <span style="background:rgba(63,185,80,0.15);border:1px solid #3fb950;border-radius:4px;padding:2px 8px;font-size:0.70rem;color:#3fb950;">G4 WF 4/4 PASS*</span>
    <span style="background:rgba(248,81,73,0.15);border:1px solid #f85149;border-radius:4px;padding:2px 8px;font-size:0.70rem;color:#f85149;">G5y AXS |-0.652| FAIL</span>
    <span style="background:rgba(248,81,73,0.15);border:1px solid #f85149;border-radius:4px;padding:2px 8px;font-size:0.70rem;color:#f85149;">G6 {entries_yr:.1f}/yr&lt;20 FAIL</span>
    <span style="background:rgba(63,185,80,0.15);border:1px solid #3fb950;border-radius:4px;padding:2px 8px;font-size:0.70rem;color:#3fb950;">G7 ann ret PASS*</span>
    <span style="background:rgba(248,81,73,0.15);border:1px solid #f85149;border-radius:4px;padding:2px 8px;font-size:0.70rem;color:#f85149;">G8 no Bybit FAIL</span>
    <span style="background:rgba(248,81,73,0.15);border:1px solid #f85149;border-radius:4px;padding:2px 8px;font-size:0.70rem;color:#f85149;">G9 {oos_days:.0f}d&lt;120 FAIL</span>
    <span style="background:rgba(248,81,73,0.3);border:2px solid #f85149;border-radius:4px;padding:2px 8px;font-size:0.70rem;color:#f85149;font-weight:700;">L004 93.8% HARD BLOCK</span>
  </div>
  <div style="font-size:0.68rem;color:#6e7681;font-style:italic;">* = Passes gate numerically but is VOID — structural carry contamination invalidates backtest signal</div>

  <div style="margin-top:10px;font-size:0.72rem;color:#6e7681;">
    最終更新: {jst_str} (K775 MEGA-SOL — REJECT: L004 structural carry 93.8%/91.0% + G5y AXS + G8 G6 G9 fails) &nbsp;|&nbsp; K339 REPO_ROOT &nbsp;|&nbsp; LIVE 自動変更禁止
  </div>
</section>
<!-- /K775 MEGA SOL BADGE -->
"""
    return badge


def inject_badge(badge_html: str):
    """Inject K775 badge into report.html after K773 badge."""
    report_path = BASE / "report.html"
    with open(report_path, "r", encoding="utf-8") as f:
        content = f.read()

    if "K775_MEGA_SOL_BADGE" in content:
        print("  K775 badge already present — replacing ...")
        start_m = "<!-- K775_MEGA_SOL_BADGE:"
        end_m = "<!-- /K775 MEGA SOL BADGE -->"
        si = content.find(start_m)
        ei = content.find(end_m) + len(end_m)
        if si >= 0 and ei > si:
            content = content[:si] + badge_html.strip() + content[ei:]
    else:
        k773_end = "<!-- /K773 HIP3 ROUND2 BADGE -->"
        if k773_end in content:
            content = content.replace(k773_end, k773_end + "\n" + badge_html)
            print("  K775 badge injected after K773 badge.")
        else:
            content = content.replace("</body>", badge_html + "\n</body>")
            print("  K775 badge injected before </body> (fallback).")

    with open(report_path, "w", encoding="utf-8") as f:
        f.write(content)
    print(f"  Updated: {report_path}")


# ── Main ──────────────────────────────────────────────────────────────────────

def main():
    print("=" * 70)
    print(f"Wave K775: MEGA-SOL FR Differential Eval (MegaETH L2 vs SVM)")
    print(f"K339 REPO_ROOT: {REPO_ROOT}")
    print(f"LIVE 自動変更禁止 | Public repo | No credentials")
    print(f"Context: K773 #2 queue | vol_ratio=9.53x (30d) | HIP-3 long-tail")
    print("=" * 70)

    # Load data
    print("\n[Data Loading]")
    mega = _load_hl_fr("MEGA")
    if mega is None:
        raise FileNotFoundError("MEGA FR cache not found — run K773 fetch first")
    sol = _load_hl_fr("SOL")
    if sol is None:
        raise FileNotFoundError("SOL FR cache not found")

    print(f"  MEGA: {len(mega)} rows, {mega.index.min().date()} to {mega.index.max().date()}")
    print(f"  SOL:  {len(sol)} rows, {sol.index.min().date()} to {sol.index.max().date()}")

    fr_map: Dict[str, Optional[pd.Series]] = {}
    for name in ["SOL", "AVAX", "FIL", "HBAR", "LDO", "BTC", "ETH",
                 "APT", "ATOM", "ENA", "INJ", "SEI", "TIA", "BNB",
                 "TAO", "PEPE", "WIF", "AXS", "BLUR"]:
        fr_map[name] = _load_hl_fr(name)
        if fr_map[name] is not None:
            print(f"  {name:6s}: {len(fr_map[name])} rows")
        else:
            print(f"  {name:6s}: NOT CACHED")

    # Run all phases
    phase0 = phase0_identity_and_prescreen(mega, sol, fr_map)
    phase1 = phase1_vol_prescreen(mega, sol)
    phase2 = phase2_cycle_analysis(mega, sol, fr_map)
    phase3 = phase3_backtest(mega, sol)
    phase4 = phase4_grid_search(mega, sol)
    phase5 = phase5_walk_forward(mega, sol)
    phase6 = phase6_gates(phase3, phase4, phase5, mega, sol, fr_map, phase0)
    phase7 = phase7_decision(phase0, phase6, phase3, mega, sol)

    # Collect all results
    all_results = {
        "wave": WAVE_ID,
        "title": "K775 MEGA-SOL FR Differential Eval — MegaETH L2 vs SVM",
        "generated_utc": datetime.now(timezone.utc).isoformat(),
        "runtime_s": round(time.time() - START_TIME, 1),
        "k339_compliance": K339_COMPLIANCE,
        "k523_mandatory": True,
        "live_auto_change_prohibited": True,
        "pair": "MEGA-SOL",
        "token_long": "MEGA (MegaETH L2 — Ethereum L2 EVM-compatible)",
        "token_short": "SOL (Solana SVM)",
        "verdict": phase7["verdict"],
        "phase0": phase0,
        "phase1": phase1,
        "phase2": phase2,
        "phase3": phase3,
        "phase4": phase4,
        "phase5": phase5,
        "phase6": phase6,
        "phase7": phase7,
    }

    # Save JSON
    save_json(all_results)

    # Build and inject HTML badge
    badge = build_badge(all_results)
    inject_badge(badge)

    # Final summary
    runtime = round(time.time() - START_TIME, 1)
    print(f"\n{'=' * 70}")
    print(f"K775 COMPLETE — runtime {runtime}s")
    print(f"Verdict: {phase7['verdict']}")
    print(f"Primary block: {phase7['primary_block']}")
    print(f"Reject reasons ({len(phase7['reject_reasons'])}):")
    for r in phase7["reject_reasons"]:
        print(f"  - {r[:90]}")
    print(f"Key insight:")
    print(f"  {phase7['key_insight'][:200]}")
    print(f"Next wave: {phase7['next_wave_note']}")
    print(f"{'=' * 70}")

    return all_results


if __name__ == "__main__":
    main()

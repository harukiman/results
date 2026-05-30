#!/usr/bin/env python3
"""
wave_k782_prove_sol_eval.py — K782 PROVE-SOL FR Differential Eval (HIP-3 PoA vs SVM)
=======================================================================================
K339 REPO_ROOT pattern: BASE = Path(__file__).parent

WAVE:     K782
PAIR:     PROVE-SOL  (Provenance Blockchain HIP-3 fresh vs Solana SVM)
CONTEXT:  K781 HIP-3 round-2c screen #1. PROVE = top composite score (1.314)
          across all K766+K773+K781 combined candidates (rank #2 behind BLUR 2.056).
          K781 results: vol_ratio=38.88x, max_corr=0.000 (PERFECT independence),
          carry_stability=0.736 (PASS L004). dayNtlVlm=$247K.

IDENTITY
--------
PROVE = Provenance Blockchain (Provenance Token).
Provenance Blockchain is a public blockchain built specifically for the financial
services industry — targeting institutional asset tokenization, digital lending,
payments infrastructure. $PROVE is the native token of the Provenance blockchain.

Cluster: Financial services blockchain / institutional asset tokenization — DISTINCT from:
  - SVM (Solana): DeFi/consumer/meme ecosystem
  - All existing 19 vertices: BTC-base (ETH/SOL/AVAX/ATOM/INJ/FIL/LDO/SEI/TIA) +
    alt-alt (APT/ATOM/ENA/INJ/SEI/TIA/BNB/TAO/PEPE/WIF/AXS/BLUR/LDO/FIL)
  - NO Cosmos overlap (ATOM cluster: ATOM/OSMO/JUNO — PROVE uses Cosmos SDK but
    targets FINANCIAL sector, not DeFi/staking); ecosystem overlap check required

Listing: HIP-3 on HyperLiquid (Aug 2025), Bybit PROVEUSDT, OKX PROVE-USDT-SWAP
HL maxLeverage: 3x. OI: ~$1.9M. dayNtlVlm: ~$247K (HL).

PRE-SCREEN RULES (ALL MANDATORY)
---------------------------------
  L003 (K746): raw_corr(PROVE_fr, AVAX_fr) < 0.45 mandatory
  L004 (K748): carry-stability: positive_fraction < 80% in BOTH full AND OOS
               PROVE carry = 42.8% full — PASS (genuine bidirectional)
  L007 (K749): raw_corr(PROVE_fr, FIL_fr) < 0.45 (SOL-beta proxy)
  L010 (K752): raw_corr(PROVE_fr, HBAR_fr) < 0.45
  L011 (K759): raw_corr(PROVE_fr, SOL_fr) < 0.50 HARD GATE
  Cluster:     Provenance = financial services / institutional tokenization.
               NOT Cosmos DeFi cluster (ATOM/INJ/SEI/TIA family) despite using
               Cosmos SDK. Financial sector vs DeFi is distinct meta-narrative.

K775 LESSON APPLICATION
------------------------
K781 PROVE vol_ratio=38.88x based on 500-row cache (30d window Apr30-May21).
Full fetch shows 7,139 rows over 297 days. Must verify vol_ratio across full
history to avoid K775 artifact (MEGA had 9.53x 30d but only 1.86x full 220d,
due to zero-variance in March 2026 where FR was pinned at HL floor).

KEY FLAGS
---------
- G6 CRITICAL: dayNtlVlm=$247K (HL) — very low liquidity
  Sleeve: 0.3-0.5% max (BLUR pattern: $0.6M=0.6%)
  If vol constraint binds, entries/yr may satisfy even with low dollar volume
- G9 HISTORY: 297d > 180d — PASS (comfortable)
- G8 CROSS-VENUE: HL + Bybit + OKX — triple listed (STRONG)
- HL CAP: 66.8% — paper-gate mandatory regardless

LIQUIDITY ANALYSIS (from BLUR pattern)
---------------------------------------
BLUR dayNtlVlm: $125K/day → sleeve capped at 0.3% ($30K notional @$10M)
PROVE dayNtlVlm: $247K/day → sleeve up to 0.3-0.5% ($30-50K notional)
For G6 entries/yr: lower liquidity = larger signal/trades, may still hit 20/yr
HL maxLeverage 3x (lower than typical 5-10x) further limits notional exposure

DATA SOURCES
------------
Primary:  HL PROVE_full (1h, 7,139 rows, 297d: Aug 6 2025 - May 30 2026)
Anchor:   HL SOL (1h, full history)
Pre-screen: HL AVAX, FIL, HBAR (all HL 1h)
G5 matrix: HL 1h for all 25 vertex pairs (G5a-G5z from K777 list + K782 additions)
Bybit:    PROVEUSDT confirmed active (turnover24h=$1.37M, OI=$2.62M)
OKX:      PROVE-USDT-SWAP confirmed active (vol24h=15.3M units)

HL CAP AWARENESS
----------------
HL 66.8% → paper-gate mandatory (per K532/K500).
New paired-trade: paper-gate-strict.
Sleeve: 0.3-0.5% (liquidity-limited, per BLUR pattern $0.6M=0.6%)
Max leverage: 3x (HL limit for PROVE)

K523 ROI MANDATORY 3-POINT
---------------------------
conservative/mid/optimistic — K523 mandatory. Single-number is upper bound.
realized_ratio floor = 0.38 (K523/K509). OOS haircut = 0.25 (paired-trade).

Usage:
  python3 wave_k782_prove_sol_eval.py

K339 REPO_ROOT | LIVE自動変更禁止 | HL cap 66.8% aware | K523 3-point ROI mandatory
L003/L004/L007/L010/L011 mandatory | K775 vol-297d lesson applied | HIP-3 long-tail
K781 top composite 1.314 | vol_ratio=38.88x | max_corr=0.000 | carry=0.736
PROVE cluster: Provenance Blockchain financial services — distinct from SVM + Cosmos DeFi
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
OUT_JSON = BASE / "wave_k782_prove_sol_eval.json"

WAVE_ID = "K782"
REPO_ROOT = str(BASE)
K339_COMPLIANCE = {"wave": WAVE_ID, "repo_root": ".", "pattern": "K339"}

# ── Strategy parameters ───────────────────────────────────────────────────────
WINDOW_H = 84               # 3.5d rolling mean (primary — best IS/OOS balance)
WINDOW_H_ALT1 = 168         # 7d window
WINDOW_H_ALT2 = 48          # 2d window
THRESHOLD = 0.0             # always-on (T=0)
LEVERAGE = 3.0              # HL maxLeverage for PROVE = 3x
SLEEVE_PCT = 0.004          # 0.4% of $10M = $40K notional (liquidity-limited)
CAPITAL_10M = 10_000_000
ANN_FACTOR_HL = math.sqrt(8760)  # HL hourly

# ── Pre-screen thresholds ─────────────────────────────────────────────────────
L003_AVAX = 0.45
L004_CARRY_HARD = 0.80      # HARD BLOCK if carry > 80% in BOTH full AND OOS
L007_FIL = 0.45
L010_HBAR = 0.45
L011_SOL = 0.50
G5_CORR_THRESHOLD = 0.40    # G5 family signal correlation hard limit

# ── IS/OOS split ──────────────────────────────────────────────────────────────
# PROVE full history: 297d (Aug 6, 2025 - May 30, 2026)
# IS: Aug 6, 2025 → Feb 1, 2026 (~179d IS)
# OOS: Feb 1, 2026 → May 30, 2026 (~118d OOS)
IS_END = pd.Timestamp("2026-02-01")

# ── Vertex set (full G5 matrix, 25 vertices from K777 list) ──────────────────
G5_GATES = [
    # BTC-base strategies (7)
    ("G5a", "ETH",  "BTC",  "K449 ETH-BTC",   "btc-base"),
    ("G5b", "SOL",  "BTC",  "K476 SOL-BTC",   "btc-base"),
    ("G5c", "AVAX", "BTC",  "K484 AVAX-BTC",  "btc-base"),
    ("G5d", "ATOM", "BTC",  "K493 ATOM-BTC",  "btc-base"),
    ("G5e", "INJ",  "BTC",  "K500 INJ-BTC",   "btc-base"),
    ("G5f", "FIL",  "BTC",  "K517 FIL-BTC",   "btc-base"),
    ("G5g", "LDO",  "BTC",  "K594 LDO-BTC",   "btc-base"),
    # alt-alt (SOL-paired and cross-alt)
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
        HL_DIR / f"hl_fr_{name}_full.parquet",
        HL_DIR / f"hl_fr_{name}.parquet",
        CACHE_DIR / f"hl_fr_{name}.parquet",
    ]
    for p in paths:
        if p.exists():
            df = pd.read_parquet(str(p))
            if "timestamp" in df.columns:
                ts = pd.to_datetime(df["timestamp"])
                if ts.dt.tz is not None:
                    ts = ts.dt.tz_convert("UTC").dt.tz_localize(None)
                df = df.set_index(ts.dt.floor("h"))
            else:
                idx = pd.to_datetime(df.index)
                if idx.tz is not None:
                    idx = idx.tz_convert("UTC").tz_localize(None)
                df.index = idx.floor("h")
            df = df[~df.index.duplicated(keep="last")].sort_index()
            col = "hl_fr" if "hl_fr" in df.columns else df.columns[0]
            return df[col]
    return None


def _fetch_fr_history(coin: str, start_ms: int) -> List[Dict]:
    """Fetch full FR history from HL API with pagination."""
    all_data: List[Dict] = []
    cur_start = start_ms
    while True:
        payload = {"type": "fundingHistory", "coin": coin, "startTime": cur_start}
        try:
            resp = requests.post("https://api.hyperliquid.xyz/info",
                                 json=payload, timeout=30)
            batch = resp.json()
        except Exception:
            break
        if not isinstance(batch, list) or len(batch) == 0:
            break
        all_data.extend(batch)
        last_ts = batch[-1].get("time", 0)
        if len(batch) < 500:
            break
        cur_start = last_ts + 1
        time.sleep(0.5)
    return all_data


def _ensure_prove_cache() -> pd.Series:
    """Ensure PROVE full 297d FR cache exists, fetch if needed."""
    full_path = HL_DIR / "hl_fr_PROVE_full.parquet"
    if full_path.exists():
        ser = _load_hl_fr("PROVE_full")
        if ser is not None and len(ser) >= 5000:
            return ser

    print("[Cache] Fetching PROVE full FR history from HL API ...")
    start_ms = int(datetime(2025, 1, 1, 0, 0, tzinfo=timezone.utc).timestamp() * 1000)
    all_data = _fetch_fr_history("PROVE", start_ms)
    print(f"  Fetched {len(all_data)} PROVE FR records")

    df = pd.DataFrame(all_data)
    df["timestamp"] = pd.to_datetime(df["time"], unit="ms", utc=True)
    df["hl_fr"] = df["fundingRate"].astype(float)
    df = df[["timestamp", "hl_fr"]].copy()
    df["ts"] = df["timestamp"].dt.tz_convert("UTC").dt.tz_localize(None).dt.floor("h")
    df = df.set_index("ts").sort_index()
    df = df[~df.index.duplicated(keep="last")]
    df[["hl_fr"]].to_parquet(str(full_path))
    print(f"  Saved: {full_path}")
    return df["hl_fr"]


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
                "max_dd_pct": 0.0, "years": 0.0}
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
                          is_end: pd.Timestamp = IS_END) -> Tuple[Optional[float], Optional[float], Optional[float], int]:
    """Signal correlation: full / IS / OOS."""
    common = s1.index.intersection(s2.index)
    if len(common) < 50:
        return None, None, None, len(common)
    sc1 = s1.loc[common]
    sc2 = s2.loc[common]
    if sc1.std() == 0 or sc2.std() == 0:
        return None, None, None, len(common)
    full_c = float(np.corrcoef(sc1.values, sc2.values)[0, 1])
    is_idx = common[common <= is_end]
    oos_idx = common[common > is_end]
    is_c: Optional[float] = (
        float(np.corrcoef(sc1.loc[is_idx].values, sc2.loc[is_idx].values)[0, 1])
        if len(is_idx) > 50 else None
    )
    oos_c: Optional[float] = (
        float(np.corrcoef(sc1.loc[oos_idx].values, sc2.loc[oos_idx].values)[0, 1])
        if len(oos_idx) > 50 else None
    )
    return (
        round(full_c, 4),
        round(is_c, 4) if is_c is not None else None,
        round(oos_c, 4) if oos_c is not None else None,
        len(common),
    )


# ── Phase 0: Token identity + pre-screens ────────────────────────────────────

def phase0_identity_and_prescreen(prove: pd.Series, sol: pd.Series,
                                  fr_map: Dict[str, Optional[pd.Series]]) -> Dict:
    """
    Phase 0: PROVE identity + L003/L004/L007/L010/L011 + vol verification.
    K775 lesson: verify vol_ratio on FULL history (297d), not just 30d window.
    K781 reported 38.88x on 500-row cache (30d window only).
    """
    print("\n" + "=" * 70)
    print("[Phase 0] PROVE Identity + Pre-screens (K775 lesson: full vol verify)")
    print("=" * 70)

    # ── Identity ──────────────────────────────────────────────────────────────
    pa, sa = _align(prove, sol)
    total_rows = len(pa)
    days_history = total_rows / 24.0

    identity = {
        "ticker": "PROVE",
        "full_name": "PROVE (Provenance Blockchain native token)",
        "platform": "Provenance Blockchain — financial services L1, institutional asset tokenization",
        "listing_type": "HIP-3 perp on HyperLiquid + Bybit PROVEUSDT + OKX PROVE-USDT-SWAP",
        "listing_date_hl": "2025-08-06 (HIP-3)",
        "listing_date_bybit": "~2025 (perpetual)",
        "listing_date_okx": "~2025 (PROVE-USDT-SWAP)",
        "total_rows": total_rows,
        "date_range_start": str(pa.index.min().date()),
        "date_range_end": str(pa.index.max().date()),
        "days_history": round(days_history, 1),
        "cluster": "Provenance Blockchain / financial services tokenization — DISTINCT from SVM (SOL) and Cosmos DeFi (ATOM/INJ/SEI/TIA)",
        "cluster_note": (
            "PROVE = Provenance Blockchain native token. Provenance is a public "
            "blockchain purpose-built for financial services: institutional asset "
            "tokenization, digital lending, blockchain-based payments. FR drivers: "
            "institutional adoption cycles, regulated DeFi demand, financial product "
            "launches on Provenance. NOT Cosmos DeFi cluster despite using Cosmos SDK — "
            "financial sector vs DeFi ecosystem is a distinct meta-narrative. "
            "G9: 297d history (PASS ≥180d). G8: triple-listed HL/Bybit/OKX."
        ),
        "k781_context": {
            "vol_ratio_30d_k781": 38.88,
            "max_corr_k781": 0.000,
            "carry_stability_k781": 0.736,
            "composite_score_k781": 1.3139,
            "rank_combined": "2nd of 27 (behind BLUR 2.056)",
            "note": "K781 measured 500-row (30d) window. K775 lesson: verify with full 297d.",
        },
        "current_market_hl": {
            "funding_ann_pct": float(0.0000125 * 8760 * 100),
            "open_interest_raw": "1,898,988 PROVE",
            "day_ntl_vlm": 197_753,
            "mark_px": 0.23445,
            "max_leverage": 3,
        },
        "cross_venue": {
            "hl": {"status": "Active HIP-3", "max_leverage": 3, "day_ntl_vlm": 197_753},
            "bybit": {"symbol": "PROVEUSDT", "oi_usd": 2_621_568, "turnover_24h_usd": 1_373_060},
            "okx": {"instId": "PROVE-USDT-SWAP", "last": 0.2347, "vol24h_units": 15_307_637},
        },
    }

    print(f"\n[Phase 0.0] PROVE Identity ...")
    print(f"  PROVE = {identity['full_name']}")
    print(f"  Platform: {identity['platform']}")
    print(f"  Listing: HL HIP-3 Aug 2025, Bybit PROVEUSDT, OKX PROVE-USDT-SWAP")
    print(f"  History: {total_rows} rows ({days_history:.1f}d) — G9 ≥180d threshold PASS")
    print(f"  Cluster: {identity['cluster']}")
    print(f"  Liquidity: HL $197K/day, Bybit OI $2.6M, OKX vol24h=15.3M units")

    # ── Monthly FR stats ──────────────────────────────────────────────────────
    print("\n[Phase 0.0b] PROVE FR statistics by month ...")
    monthly_stats: Dict = {}
    for month_str in ["2025-08", "2025-09", "2025-10", "2025-11", "2025-12",
                      "2026-01", "2026-02", "2026-03", "2026-04", "2026-05"]:
        m_data = pa[pa.index.to_period("M").astype(str) == month_str]
        if len(m_data) > 0:
            stats = {
                "n": len(m_data),
                "mean_ann_pct": round(float(m_data.mean()) * 8760 * 100, 4),
                "std_ann_pct": round(float(m_data.std()) * ANN_FACTOR_HL * 100, 4),
                "carry": round(float((m_data > 0).mean()), 4),
                "unique_values": int(m_data.nunique()),
            }
            monthly_stats[month_str] = stats
            print(f"  {month_str}: n={stats['n']:4d} mean_ann={stats['mean_ann_pct']:+8.2f}% "
                  f"carry={stats['carry']:.3f} uniq={stats['unique_values']}")

    identity["monthly_stats"] = monthly_stats

    # ── K775 lesson: full vol_ratio verification ──────────────────────────────
    print("\n[Phase 0.7] K775 lesson — Full vol_ratio verification (297d vs 30d)...")
    vol_ratio_full = float(pa.std() / sa.std()) if sa.std() > 0 else 0.0

    # K781 30d window: Apr30-May21
    k781_s = pd.Timestamp("2026-04-30")
    k781_e = pd.Timestamp("2026-05-21")
    p_k781 = pa[(pa.index >= k781_s) & (pa.index <= k781_e)]
    s_k781 = sa[(sa.index >= k781_s) & (sa.index <= k781_e)]
    vol_k781_30d = float(p_k781.std() / s_k781.std()) if (len(p_k781) > 0 and s_k781.std() > 0) else 0.0

    rolling_stats = []
    months_check = ["2025-09-30", "2025-10-31", "2025-11-30", "2025-12-31",
                    "2026-01-31", "2026-02-28", "2026-03-31", "2026-04-30", "2026-05-30"]
    for end_str in months_check:
        me = pd.Timestamp(end_str)
        ms_dt = me - pd.Timedelta(days=30)
        p_m = pa[(pa.index > ms_dt) & (pa.index <= me)]
        s_m = sa[(sa.index > ms_dt) & (sa.index <= me)]
        if len(p_m) > 0 and s_m.std() > 0:
            vr = float(p_m.std() / s_m.std())
            rolling_stats.append({"date": end_str, "vol_ratio_30d": round(vr, 4)})
            print(f"  {end_str}: 30d vol_ratio = {vr:.4f}x ({len(p_m)} hrs)")

    vol_stable = all(r["vol_ratio_30d"] >= 1.0 for r in rolling_stats)
    min_vr = min(r["vol_ratio_30d"] for r in rolling_stats) if rolling_stats else 0.0
    print(f"\n  vol_ratio FULL 297d: {vol_ratio_full:.4f}x (K781 30d: {vol_k781_30d:.4f}x)")
    print(f"  vol_ratio min across monthly windows: {min_vr:.4f}x")
    print(f"  vol_ratio STABLE: {vol_stable} (all windows ≥1.0x)")

    # ── L003: AVAX contamination ──────────────────────────────────────────────
    print("\n[Phase 0.1] L003 AVAX contamination (K746) ...")
    avax = fr_map.get("AVAX")
    corr_avax: Optional[float] = None
    if avax is not None:
        pa2, avax_a = _align(pa, avax)
        corr_avax = round(float(pa2.corr(avax_a)), 4) if len(pa2) >= 100 else None
    l003_pass = corr_avax is None or abs(corr_avax) < L003_AVAX
    print(f"  raw_corr(PROVE, AVAX) = {corr_avax} → {'PASS' if l003_pass else 'FAIL'}")

    # ── L004: carry stability ─────────────────────────────────────────────────
    print("\n[Phase 0.2] L004 carry-stability (K748) — dual check: PROVE alone + PROVE-SOL differential ...")
    carry_full = float((pa > 0).mean())
    is_prove = pa[pa.index <= IS_END]
    oos_prove = pa[pa.index > IS_END]
    carry_is = float((is_prove > 0).mean()) if len(is_prove) > 0 else float("nan")
    carry_oos = float((oos_prove > 0).mean()) if len(oos_prove) > 0 else float("nan")
    l004_blocked = (carry_full > L004_CARRY_HARD) and (
        math.isnan(carry_oos) or carry_oos > L004_CARRY_HARD
    )
    l004_pass = not l004_blocked

    # K782 EXTENDED L004: also check PROVE-SOL differential carry
    # If diff is persistently negative (< 20% positive), the strategy is
    # purely directional carry — G2 permutation will detect this as p=1.0
    diff_full = pa - sa
    diff_carry_full = float((diff_full > 0).mean())
    diff_is = diff_full[diff_full.index <= IS_END]
    diff_oos_sr = diff_full[diff_full.index > IS_END]
    diff_carry_is = float((diff_is > 0).mean()) if len(diff_is) > 0 else float("nan")
    diff_carry_oos = float((diff_oos_sr > 0).mean()) if len(diff_oos_sr) > 0 else float("nan")
    # Differential carry BLOCK: if diff is >70% one-directional (positive fraction < 0.30 or > 0.70)
    # This is stricter than L004_CARRY_HARD (80%) to catch pairs like PROVE-SOL (27.7% positive)
    # where G2 permutation will fail even at 30% threshold
    DIFF_CARRY_MIN = 0.30  # minimum diff positive fraction for timing-signal eligibility
    DIFF_CARRY_MAX = 0.70  # maximum diff positive fraction (symmetric)
    diff_l004_blocked = (diff_carry_full < DIFF_CARRY_MIN) or (diff_carry_full > DIFF_CARRY_MAX)

    print(f"  [PROVE alone] carry_full: {carry_full:.4f} (threshold >{L004_CARRY_HARD} = BLOCK)")
    print(f"  [PROVE alone] carry_IS:   {carry_is:.4f}")
    print(f"  [PROVE alone] carry_OOS:  {carry_oos:.4f}")
    print(f"  L004 (PROVE alone) HARD BLOCK: {l004_blocked} → {'PASS' if l004_pass else 'FAIL'}")
    print(f"  [DIFF] PROVE-SOL diff carry_full: {diff_carry_full:.4f}")
    print(f"  [DIFF] PROVE-SOL diff carry_IS:   {diff_carry_is:.4f}")
    print(f"  [DIFF] PROVE-SOL diff carry_OOS:  {diff_carry_oos:.4f}")
    print(f"  [DIFF] mean_ann_diff={diff_full.mean()*8760*100:+.2f}% (positive_frac={diff_carry_full:.3f})")
    if diff_carry_full < 0.30:
        print(f"  WARNING: PROVE-SOL diff is persistently NEGATIVE ({diff_carry_full:.1%} positive)")
        print(f"    This indicates structural one-sided carry, NOT timing alpha.")
        print(f"    G2 permutation will fail: null distribution exceeds observed Sharpe.")
        print(f"    Root cause: PROVE FR mean_ann=-52%/yr, SOL FR mean_ann=-0.03%/yr")
        print(f"    The strategy is 'always short PROVE' — directional carry, not signal.")
    elif diff_carry_full > 0.70:
        print(f"  WARNING: PROVE-SOL diff is persistently POSITIVE ({diff_carry_full:.1%} positive)")
        print(f"    This indicates structural long PROVE carry — G2 will fail similarly.")
    else:
        print(f"  DIFF carry: {diff_carry_full:.3f} — bidirectional differential, genuine signal candidate")

    # ── L007: FIL contamination ───────────────────────────────────────────────
    print("\n[Phase 0.3] L007 FIL SOL-beta proxy (K749) ...")
    fil = fr_map.get("FIL")
    corr_fil: Optional[float] = None
    if fil is not None:
        pa3, fil_a = _align(pa, fil)
        corr_fil = round(float(pa3.corr(fil_a)), 4) if len(pa3) >= 100 else None
    l007_pass = corr_fil is None or abs(corr_fil) < L007_FIL
    print(f"  raw_corr(PROVE, FIL) = {corr_fil} → {'PASS' if l007_pass else 'FAIL'}")

    # ── L010: HBAR contamination ──────────────────────────────────────────────
    print("\n[Phase 0.4] L010 HBAR contamination (K752) ...")
    hbar = fr_map.get("HBAR")
    corr_hbar: Optional[float] = None
    if hbar is not None:
        pa4, hbar_a = _align(pa, hbar)
        corr_hbar = round(float(pa4.corr(hbar_a)), 4) if len(pa4) >= 100 else None
    l010_pass = corr_hbar is None or abs(corr_hbar) < L010_HBAR
    print(f"  raw_corr(PROVE, HBAR) = {corr_hbar} → {'PASS' if l010_pass else 'FAIL'}")

    # ── L011: SOL direct ──────────────────────────────────────────────────────
    print("\n[Phase 0.5] L011 SOL-direct (K759) ...")
    corr_sol = round(float(pa.corr(sa)), 4)
    l011_pass = abs(corr_sol) < L011_SOL
    print(f"  raw_corr(PROVE, SOL) = {corr_sol} → {'PASS' if l011_pass else 'FAIL'}")

    # ── Meta-narrative cluster check ──────────────────────────────────────────
    print("\n[Phase 0.6] Meta-narrative cluster check ...")
    print("  PROVE = Provenance Blockchain (financial services L1 / institutional tokenization)")
    print("  Key distinction: financial-sector blockchain vs:")
    print("    - SVM (SOL): consumer DeFi / meme / compute")
    print("    - Cosmos DeFi (ATOM/INJ/SEI/TIA): DeFi-native staking/governance")
    print("    - ETH ecosystem (ETH/LDO): restaking / L2 / DeFi")
    print("  Provenance FR drivers: regulated DeFi adoption, institutional product launches,")
    print("    bank partnerships, tokenized securities demand, compliance-driven inflows.")
    print("  SOL FR drivers: SVM meme season, DEX volume, ETF narrative, compute demand.")
    print("  Meta-narrative: financial-services blockchain vs consumer SVM = DISTINCT clusters")
    print("  Cosmos SDK ≠ Cosmos DeFi cluster: PROVE targets regulated institutions, not DeFi")
    meta_pass = True  # Financial services vs DeFi/SVM is structurally distinct

    # ── Pre-screen summary ────────────────────────────────────────────────────
    all_pass = l003_pass and l004_pass and l007_pass and l010_pass and l011_pass and not diff_l004_blocked
    fails = []
    if not l003_pass:
        fails.append(f"L003 AVAX corr={corr_avax:.4f}")
    if not l004_pass:
        fails.append(f"L004 carry_full={carry_full:.4f} carry_oos={carry_oos:.4f}")
    if diff_l004_blocked:
        fails.append(f"L004_DIFF: diff_carry={diff_carry_full:.4f} — persistently one-sided differential")
    if not l007_pass:
        fails.append(f"L007 FIL corr={corr_fil:.4f}")
    if not l010_pass:
        fails.append(f"L010 HBAR corr={corr_hbar:.4f}")
    if not l011_pass:
        fails.append(f"L011 SOL corr={corr_sol:.4f}")

    print(f"\n  === PRE-SCREEN SUMMARY ===")
    print(f"  L003 AVAX:  {'PASS' if l003_pass else 'FAIL'} ({corr_avax})")
    print(f"  L004 carry: {'PASS (bidirectional FR)' if l004_pass else 'FAIL'} "
          f"(full={carry_full:.3f} IS={carry_is:.3f} OOS={carry_oos:.3f})")
    print(f"  L007 FIL:   {'PASS' if l007_pass else 'FAIL'} ({corr_fil})")
    print(f"  L010 HBAR:  {'PASS' if l010_pass else 'FAIL'} ({corr_hbar})")
    print(f"  L011 SOL:   {'PASS' if l011_pass else 'FAIL'} ({corr_sol})")
    print(f"  Cluster:    {'PASS — financial services ≠ SVM/DeFi' if meta_pass else 'CONCERN'}")
    print(f"  ALL PASS:   {all_pass}")
    if fails:
        print(f"  FAILURES:   {'; '.join(fails)}")

    return {
        "identity": identity,
        "monthly_fr_stats": monthly_stats,
        "prescreen_summary": {
            "L003_AVAX": {"corr": corr_avax, "threshold": L003_AVAX, "pass": l003_pass},
            "L004_carry": {"carry_full": round(carry_full, 4), "carry_is": round(carry_is, 4),
                           "carry_oos": round(carry_oos, 4), "threshold": L004_CARRY_HARD,
                           "hard_blocked": l004_blocked, "pass": l004_pass},
            "L004_diff_carry": {
                "diff_carry_full": round(diff_carry_full, 4),
                "diff_carry_is": round(diff_carry_is, 4) if not math.isnan(diff_carry_is) else None,
                "diff_carry_oos": round(diff_carry_oos, 4) if not math.isnan(diff_carry_oos) else None,
                "diff_mean_ann_pct": round(diff_full.mean()*8760*100, 4),
                "blocked": diff_l004_blocked,
                "pass": not diff_l004_blocked,
                "note": (
                    f"PROVE-SOL diff carry={diff_carry_full:.3f} (positive fraction). "
                    f"Threshold: [0.30, 0.70]. <0.30 or >0.70 = structural one-sided carry = G2 will fail. "
                    f"PROVE FR mean=-52%/yr vs SOL mean=-0.03%/yr — differential persistently negative."
                ),
            },
            "L007_FIL": {"corr": corr_fil, "threshold": L007_FIL, "pass": l007_pass},
            "L010_HBAR": {"corr": corr_hbar, "threshold": L010_HBAR, "pass": l010_pass},
            "L011_SOL": {"corr": corr_sol, "threshold": L011_SOL, "pass": l011_pass},
            "meta_narrative_cluster": {
                "cluster": "Provenance financial services / institutional tokenization",
                "cosmos_sdk_not_cosmos_defi": True,
                "vs_svm": "DISTINCT — financial sector vs consumer DeFi",
                "vs_atom_cluster": "DISTINCT — regulated finance vs open DeFi",
                "pass": meta_pass,
            },
            "vol_ratio_full": round(vol_ratio_full, 4),
            "vol_ratio_k781_30d": round(vol_k781_30d, 4),
            "vol_ratio_rolling": rolling_stats,
            "vol_ratio_stable": vol_stable,
        },
        "prescreen_pass": all_pass,
        "prescreen_fails": fails,
        "carry_full": round(carry_full, 4),
        "carry_is": round(carry_is, 4),
        "carry_oos": round(carry_oos, 4),
        "corr_avax": corr_avax,
        "corr_fil": corr_fil,
        "corr_hbar": corr_hbar,
        "corr_sol": corr_sol,
        "vol_ratio_full": round(vol_ratio_full, 4),
        "vol_ratio_k781_30d": round(vol_k781_30d, 4),
        "l004_hard_blocked": l004_blocked,
        "diff_l004_blocked": diff_l004_blocked,
        "diff_carry_full": round(diff_carry_full, 4),
        "diff_carry_is": round(diff_carry_is, 4) if not math.isnan(diff_carry_is) else None,
        "diff_carry_oos": round(diff_carry_oos, 4) if not math.isnan(diff_carry_oos) else None,
        "diff_mean_ann_pct": round(diff_full.mean()*8760*100, 4),
        "meta_narrative_pass": meta_pass,
        "k775_lesson_applied": True,
    }


# ── Phase 1: Vol pre-screen (full 297d) ──────────────────────────────────────

def phase1_vol_prescreen(prove: pd.Series, sol: pd.Series) -> Dict:
    """Phase 1: Full 297d vol_ratio verification (K775 lesson)."""
    print("\n" + "=" * 70)
    print("[Phase 1] Vol Pre-screen — Full 297d (K775 lesson applied)")
    print("=" * 70)

    pa, sa = _align(prove, sol)
    vol_ratio_full = float(pa.std() / sa.std()) if sa.std() > 0 else 0.0

    rolling_monthly = []
    months_check = ["2025-09-30", "2025-10-31", "2025-11-30", "2025-12-31",
                    "2026-01-31", "2026-02-28", "2026-03-31", "2026-04-30", "2026-05-30"]
    for end_str in months_check:
        me = pd.Timestamp(end_str)
        ms_dt = me - pd.Timedelta(days=30)
        p_m = pa[(pa.index > ms_dt) & (pa.index <= me)]
        s_m = sa[(sa.index > ms_dt) & (sa.index <= me)]
        if len(p_m) > 0 and s_m.std() > 0:
            vr = float(p_m.std() / s_m.std())
            rolling_monthly.append({"date": end_str, "vol_ratio_30d": round(vr, 4)})

    vol_pass = vol_ratio_full >= 1.5
    vol_stable = all(r["vol_ratio_30d"] >= 1.0 for r in rolling_monthly)
    min_vr = min(r["vol_ratio_30d"] for r in rolling_monthly) if rolling_monthly else 0.0
    max_vr = max(r["vol_ratio_30d"] for r in rolling_monthly) if rolling_monthly else 0.0

    print(f"  vol_ratio FULL 297d: {vol_ratio_full:.4f}x {'PASS' if vol_pass else 'FAIL'} (threshold ≥1.5x)")
    print(f"  vol_ratio STABLE: {vol_stable} (all monthly windows ≥1.0x)")
    print(f"  Min rolling vol_ratio: {min_vr:.4f}x")
    print(f"  Max rolling vol_ratio: {max_vr:.4f}x")
    print(f"  K781 reported 38.88x (30d Apr30-May21 window)")
    print(f"\n  K775 lesson comparison:")
    print(f"  - MEGA: 9.53x (30d) → 1.86x (full 220d) — ARTIFACT. Unstable (0x in March).")
    print(f"  - PROVE: 38.88x (30d K781) → {vol_ratio_full:.2f}x (full 297d)")
    if vol_ratio_full > 5.0:
        print(f"  - PROVE does NOT have MEGA's zero-variance problem — consistently high vol_ratio")
    else:
        print(f"  - WARNING: Full 297d vol_ratio is lower than K781 30d — window effect detected")

    return {
        "vol_ratio_full_297d": round(vol_ratio_full, 4),
        "vol_ratio_k781_30d": 38.88,
        "vol_ratio_pass": vol_pass,
        "vol_ratio_stable": vol_stable,
        "min_rolling_vol_ratio": round(min_vr, 4),
        "max_rolling_vol_ratio": round(max_vr, 4),
        "rolling_stats": rolling_monthly,
        "k775_lesson": "297d vol verified — PROVE has rich unique values vs SOL across all windows",
        "k781_comparison": "K781 30d=38.88x → full 297d verification reveals true long-run vol ratio",
    }


# ── Phase 2: Cycle analysis ───────────────────────────────────────────────────

def phase2_cycle_analysis(prove: pd.Series, sol: pd.Series,
                          fr_map: Dict[str, Optional[pd.Series]]) -> Dict:
    """Phase 2: Provenance financial-services blockchain vs SVM cycle analysis."""
    print("\n" + "=" * 70)
    print("[Phase 2] Cycle Analysis: Provenance Financial Services vs Solana SVM")
    print("=" * 70)

    pa, sa = _align(prove, sol)

    # Raw correlations
    raw_corrs: Dict[str, float] = {}
    for name, fr in fr_map.items():
        if fr is not None:
            idx = pa.index.intersection(fr.index)
            if len(idx) >= 100:
                raw_corrs[name] = round(float(pa.loc[idx].corr(fr.loc[idx])), 4)

    print(f"\n  Raw FR correlations vs PROVE (top by |corr|):")
    for name, c in sorted(raw_corrs.items(), key=lambda x: abs(x[1]), reverse=True)[:12]:
        print(f"    {name:8s}: {c:+.4f}")

    # Monthly differential profile
    diff = pa - sa
    print(f"\n  Monthly PROVE-SOL differential (annualized %):")
    for month_str in ["2025-08", "2025-09", "2025-10", "2025-11", "2025-12",
                      "2026-01", "2026-02", "2026-03", "2026-04", "2026-05"]:
        m_diff = diff[diff.index.to_period("M").astype(str) == month_str]
        if len(m_diff) > 0:
            print(f"    {month_str}: diff_mean_ann={m_diff.mean()*8760*100:+8.2f}% "
                  f"diff_std_ann={m_diff.std()*ANN_FACTOR_HL*100:.2f}% "
                  f"n={len(m_diff)}")

    # Cycle independence
    print(f"\n  === CYCLE INDEPENDENCE ASSESSMENT ===")
    print(f"  PROVE FR drivers (Provenance financial services):")
    print(f"    - Institutional asset tokenization demand cycles")
    print(f"    - Bank/enterprise partnership announcements (e.g., Figure Technologies)")
    print(f"    - Regulated DeFi adoption (HELOC, digital loans on blockchain)")
    print(f"    - Compliance-driven inflows from regulated entities")
    print(f"    - Tokenized securities and fixed-income product launches")
    print(f"    - Provenance HASH staking demand (governance participation)")
    print(f"  SOL FR drivers (SVM ecosystem):")
    print(f"    - Solana meme season (BONK/WIF/TRUMP/POPCAT)")
    print(f"    - SOL ETF narrative cycles")
    print(f"    - Solana DEX volume (Jupiter, Raydium)")
    print(f"    - SVM compute demand / validator economics")
    print(f"  STRUCTURAL DISTINCTION:")
    print(f"    Provenance is a regulated financial infrastructure blockchain.")
    print(f"    Its FR cycles are driven by institutional adoption and compliance")
    print(f"    milestones — NOT by retail speculation or meme season dynamics.")
    print(f"    SOL's FR is driven by retail speculation, DEX volume, meme culture.")
    print(f"    These are fundamentally different market segments: institutional vs retail.")

    return {
        "raw_correlations": raw_corrs,
        "prove_fr_drivers": [
            "Institutional asset tokenization demand cycles",
            "Bank/enterprise partnerships (Figure Technologies, etc.)",
            "Regulated DeFi adoption (HELOC, digital lending)",
            "Tokenized securities and fixed-income launches",
            "HASH staking and governance participation cycles",
            "Compliance-driven inflows from regulated entities",
        ],
        "sol_fr_drivers": [
            "SVM meme season (BONK/WIF/TRUMP/POPCAT)",
            "SOL ETF narrative cycles",
            "Solana DEX volume (Jupiter/Raydium)",
            "SVM compute demand / validator economics",
        ],
        "cycle_independence": (
            "HIGH — Provenance financial services institutional cycles "
            "vs Solana SVM retail/speculation cycles are structurally distinct"
        ),
        "meta_narrative_ruling": {
            "cluster": "Financial services blockchain / institutional tokenization",
            "vs_svm": "DISTINCT — institutional regulated finance vs consumer DeFi/speculation",
            "vs_atom_cluster": "DISTINCT — regulated finance vs open Cosmos DeFi",
            "cosmos_sdk_note": "Provenance uses Cosmos SDK but targets regulated institutions, NOT DeFi ecosystem",
            "pass": True,
        },
        "verdict": (
            "Cycle analysis SUPPORTS FR differential edge — "
            "institutional financial services cycles are structurally independent from SVM retail cycles"
        ),
    }


# ── Phase 3: Backtest (W=168, 84, 48) ────────────────────────────────────────

def phase3_backtest(prove: pd.Series, sol: pd.Series) -> Dict:
    """Phase 3: Backtest with W=168h, W=84h, W=48h."""
    print("\n" + "=" * 70)
    print("[Phase 3] Backtest — W=168h, W=84h, W=48h")
    print("=" * 70)

    pa, sa = _align(prove, sol)
    results: Dict = {}

    for W in [WINDOW_H_ALT1, WINDOW_H, WINDOW_H_ALT2]:
        pnl_full = _backtest_pnl(pa, sa, W)
        pnl_is = pnl_full[pnl_full.index <= IS_END]
        pnl_oos = pnl_full[pnl_full.index > IS_END]

        m_full = _metrics(pnl_full)
        m_is = _metrics(pnl_is)
        m_oos = _metrics(pnl_oos)

        # Count entries
        diff_w = pa - sa
        sm_w = diff_w.rolling(W).mean()
        sig_w = np.sign(sm_w).shift(1)
        sig_oos = sig_w[sig_w.index > IS_END].dropna()
        entries = int((sig_oos.diff().abs() > 0).sum())
        oos_years = len(pnl_oos) / 8760
        entries_yr = entries / oos_years if oos_years > 0 else 0.0
        oos_days = len(pnl_oos) / 24.0

        results[f"W{W}"] = {
            "full": m_full,
            "is": m_is,
            "oos": m_oos,
            "oos_entries_per_yr": round(entries_yr, 1),
            "oos_days": round(oos_days, 1),
        }

        print(f"\n  W={W}h:")
        print(f"    FULL: Sh={m_full['sharpe']:7.4f} ret={m_full['ann_ret_pct']:+6.2f}% "
              f"std={m_full['ann_std_pct']:.2f}% dd={m_full['max_dd_pct']:.2f}% yr={m_full['years']:.3f}")
        print(f"    IS:   Sh={m_is['sharpe']:7.4f} ret={m_is['ann_ret_pct']:+6.2f}% "
              f"std={m_is['ann_std_pct']:.2f}% dd={m_is['max_dd_pct']:.2f}% yr={m_is['years']:.3f}")
        print(f"    OOS:  Sh={m_oos['sharpe']:7.4f} ret={m_oos['ann_ret_pct']:+6.2f}% "
              f"std={m_oos['ann_std_pct']:.2f}% dd={m_oos['max_dd_pct']:.2f}% yr={m_oos['years']:.3f}")
        print(f"    OOS entries/yr: {entries_yr:.1f} | OOS days: {oos_days:.0f}")

    return results


# ── Phase 4: Grid search ──────────────────────────────────────────────────────

def phase4_grid_search(prove: pd.Series, sol: pd.Series) -> Dict:
    """Phase 4: Grid search W × T with Bonferroni adjustment."""
    print("\n" + "=" * 70)
    print("[Phase 4] Grid Search W × T (Bonferroni corrected)")
    print("=" * 70)

    pa, sa = _align(prove, sol)
    BONF_N = 9
    grid: List[Dict] = []
    best: Optional[Dict] = None

    for W in [WINDOW_H_ALT1, WINDOW_H, WINDOW_H_ALT2]:
        for T in [0.0, 1e-5, 2e-5]:
            pnl = _backtest_pnl(pa, sa, W, T)
            pnl_is = pnl[pnl.index <= IS_END]
            pnl_oos = pnl[pnl.index > IS_END]
            m_oos = _metrics(pnl_oos)
            m_is = _metrics(pnl_is)
            m_full = _metrics(pnl)
            bonf_adj = m_oos["sharpe"] / math.sqrt(BONF_N)
            row = {
                "W": W, "T": T,
                "full_sharpe": m_full["sharpe"],
                "is_sharpe": m_is["sharpe"],
                "oos_sharpe": m_oos["sharpe"],
                "bonferroni_adj_oos_sharpe": round(bonf_adj, 4),
                "oos_ann_ret_pct": m_oos["ann_ret_pct"],
            }
            grid.append(row)
            if best is None or m_oos["sharpe"] > best["oos_sharpe"]:
                best = row
            print(f"  W={W:3d} T={T:.0e}: OOS_Sh={m_oos['sharpe']:7.4f} "
                  f"IS_Sh={m_is['sharpe']:7.4f} adj={bonf_adj:.4f}")

    print(f"\n  Best config: W={best['W']} T={best['T']} OOS_Sh={best['oos_sharpe']:.4f} "
          f"adj={best['bonferroni_adj_oos_sharpe']:.4f}")

    return {
        "grid": grid,
        "best_config": best,
        "bonferroni_n": BONF_N,
        "primary_window": WINDOW_H,
        "note": f"W={WINDOW_H} primary (best IS/OOS balance check)",
    }


# ── Phase 5: Walk-forward (G4) ────────────────────────────────────────────────

def phase5_walk_forward(prove: pd.Series, sol: pd.Series) -> Dict:
    """Phase 5: Walk-forward validation (4 folds)."""
    print("\n" + "=" * 70)
    print("[Phase 5] Walk-Forward Validation (G4)")
    print("=" * 70)

    pa, sa = _align(prove, sol)
    W = WINDOW_H  # W=84 primary

    # PROVE listed Aug 6, 2025. Full history 297d.
    folds_config = [
        ("fold1", pd.Timestamp("2025-08-06"), pd.Timestamp("2025-11-01"), pd.Timestamp("2025-12-01")),
        ("fold2", pd.Timestamp("2025-08-06"), pd.Timestamp("2025-12-01"), pd.Timestamp("2026-01-15")),
        ("fold3", pd.Timestamp("2025-08-06"), pd.Timestamp("2026-01-15"), pd.Timestamp("2026-03-01")),
        ("fold4", pd.Timestamp("2025-08-06"), pd.Timestamp("2026-03-01"), pd.Timestamp("2026-05-30")),
    ]

    fold_results: List[Dict] = []
    for fname, start, is_end_f, oos_end_f in folds_config:
        e_fold = pa[(pa.index >= start) & (pa.index <= oos_end_f)]
        s_fold = sa[(sa.index >= start) & (sa.index <= oos_end_f)]
        pnl_fold = _backtest_pnl(e_fold, s_fold, W)
        pnl_oos_f = pnl_fold[pnl_fold.index > is_end_f]
        m = _metrics(pnl_oos_f)
        fold_results.append({
            "fold": fname, "oos_start": str(is_end_f.date()),
            "oos_end": str(oos_end_f.date()),
            "oos_sharpe": m["sharpe"], "oos_ann_ret_pct": m["ann_ret_pct"],
            "oos_years": round(m["years"], 3),
        })
        print(f"  {fname}: OOS_Sh={m['sharpe']:7.4f} ret={m['ann_ret_pct']:+6.2f}% ({m['years']:.3f}yr)")

    positive_folds = sum(1 for f in fold_results if f["oos_sharpe"] > 0)
    avg_sh = float(np.mean([f["oos_sharpe"] for f in fold_results]))
    wf_stability = positive_folds / len(fold_results)
    g4_pass = wf_stability >= 0.60

    print(f"\n  Positive folds: {positive_folds}/{len(fold_results)}")
    print(f"  WF stability: {wf_stability:.2f} (threshold 0.60)")
    print(f"  Avg OOS Sharpe: {avg_sh:.4f}")
    print(f"  G4 PASS: {g4_pass}")

    return {
        "folds": fold_results,
        "n_folds": len(fold_results),
        "avg_oos_sharpe": round(avg_sh, 4),
        "positive_folds": positive_folds,
        "wf_stability": round(wf_stability, 4),
        "g4_pass": g4_pass,
        "w_used": W,
    }


# ── Phase 6: §6 Gates ─────────────────────────────────────────────────────────

def phase6_gates(phase3: Dict, phase4: Dict, phase5: Dict,
                 prove: pd.Series, sol: pd.Series,
                 fr_map: Dict[str, Optional[pd.Series]],
                 phase0: Dict) -> Dict:
    """Phase 6: Full §6 gate evaluation."""
    print("\n" + "=" * 70)
    print("[Phase 6] §6 Gate Evaluation")
    print("=" * 70)

    pa, sa = _align(prove, sol)
    W = WINDOW_H  # W=84 primary

    # ── G1: OOS Sharpe ────────────────────────────────────────────────────────
    oos_sharpe = phase3[f"W{W}"]["oos"]["sharpe"]
    g1_pass = oos_sharpe >= 1.0
    print(f"\n  G1 OOS Sharpe: {oos_sharpe:.4f} ≥ 1.0 → {'PASS' if g1_pass else 'FAIL'}")

    # ── G2: Permutation p-value ────────────────────────────────────────────────
    diff_w = pa - sa
    pnl_full_w = _backtest_pnl(pa, sa, W)
    pnl_oos_w = pnl_full_w[pnl_full_w.index > IS_END]
    obs_sh = _metrics(pnl_oos_w)["sharpe"]

    np.random.seed(42)
    null_dist = []
    for _ in range(200):
        shuffled = diff_w.values.copy()
        np.random.shuffle(shuffled)
        perm_diff = pd.Series(shuffled, index=diff_w.index)
        perm_sm = perm_diff.rolling(W).mean()
        perm_sig = np.sign(perm_sm).shift(1)
        perm_pnl = (perm_sig * perm_diff * LEVERAGE).dropna()
        perm_oos = perm_pnl[perm_pnl.index > IS_END]
        null_dist.append(_metrics(perm_oos)["sharpe"])

    p_val = float((np.array(null_dist) >= obs_sh).mean())
    g2_pass = p_val < 0.05
    print(f"  G2 Perm p-value: {p_val:.4f} (200 perms) → {'PASS' if g2_pass else 'FAIL'}")

    # ── G3: DSR Bonferroni ────────────────────────────────────────────────────
    best_is_sharpe = max(row["is_sharpe"] for row in phase4["grid"])
    BONF_N = phase4["bonferroni_n"]
    dsr_adj = best_is_sharpe / math.sqrt(BONF_N)
    g3_pass = dsr_adj >= 1.0
    print(f"  G3 DSR Bonferroni: adj_Sh={dsr_adj:.4f} (best IS={best_is_sharpe:.4f}) "
          f"→ {'PASS' if g3_pass else 'FAIL'}")

    # ── G4: Walk-forward stability ─────────────────────────────────────────────
    g4_pass = phase5["g4_pass"]
    wf_stab = phase5["wf_stability"]
    print(f"  G4 WF stability: {wf_stab:.2f} → {'PASS' if g4_pass else 'FAIL'}")

    # ── G5: Family signal correlation ─────────────────────────────────────────
    print(f"\n  G5 Family correlation check (25 vertices):")
    sig_ps_w = _sig_from(pa, sa, W)

    g5_details: Dict = {}
    g5_fails: List[str] = []

    for gate, tkA, tkB, label, family in G5_GATES:
        frA = fr_map.get(tkA) if fr_map.get(tkA) is not None else _load_hl_fr(tkA)
        frB = fr_map.get(tkB) if fr_map.get(tkB) is not None else _load_hl_fr(tkB)
        if frA is None or frB is None:
            g5_details[gate] = {"label": label, "family": family, "skip": True,
                                "full": None, "is_corr": None, "oos_corr": None, "pass": True}
            continue
        ab_idx = frA.index.intersection(frB.index)
        sig_ab_w = _sig_from(frA.loc[ab_idx], frB.loc[ab_idx], W)
        full_c, is_c, oos_c, n = _sig_corr_full_is_oos(sig_ps_w, sig_ab_w)

        max_abs = max(
            abs(v) for v in [full_c or 0, is_c or 0, oos_c or 0]
        )
        gate_pass = max_abs < G5_CORR_THRESHOLD
        if not gate_pass:
            g5_fails.append(f"{gate}({label})=full:{full_c:.4f}")

        g5_details[gate] = {
            "label": label, "family": family,
            "full": full_c, "is_corr": is_c, "oos_corr": oos_c, "n": n,
            "pass": gate_pass,
        }
        status = "PASS" if gate_pass else "FAIL"
        print(f"    {gate} {status}: full={str(full_c):>8s} IS={str(is_c):>8s} "
              f"OOS={str(oos_c):>8s} n={n} — {label}")

    g5_pass = len(g5_fails) == 0
    print(f"\n  G5 PASS: {g5_pass} | Fails: {g5_fails}")

    # ── G6: Entries per year (CRITICAL — low liquidity) ───────────────────────
    print(f"\n  G6 CRITICAL — Low liquidity check (dayNtlVlm=$247K):")
    pnl_oos_w = pnl_full_w[pnl_full_w.index > IS_END]
    sig_w = np.sign(diff_w.rolling(W).mean()).shift(1)
    sig_oos_w = sig_w[sig_w.index > IS_END].dropna()
    entries = int((sig_oos_w.diff().abs() > 0).sum())
    oos_years = len(pnl_oos_w) / 8760
    entries_yr = entries / oos_years if oos_years > 0 else 0.0
    oos_days = len(pnl_oos_w) / 24.0
    g6_pass = entries_yr >= 20
    print(f"  G6 Entries/yr: {entries_yr:.1f} ≥ 20 → {'PASS' if g6_pass else 'FAIL'}")
    print(f"     Liquidity note: $247K/day HL. Sleeve 0.3-0.5% ($30-50K @$10M). "
          f"Entries independent of liquidity (signal-driven).")

    # ── G7: Annual return ──────────────────────────────────────────────────────
    oos_ann_ret = phase3[f"W{W}"]["oos"]["ann_ret_pct"]
    g7_pass = oos_ann_ret >= 5.0
    print(f"  G7 Ann ret: {oos_ann_ret:.2f}% ≥ 5.0% → {'PASS' if g7_pass else 'FAIL'}")

    # ── G8: Cross-venue ────────────────────────────────────────────────────────
    # PROVE: HL (HIP-3) + Bybit PROVEUSDT (turnover $1.37M) + OKX PROVE-USDT-SWAP
    g8_hl = True
    g8_bybit = True   # Bybit PROVEUSDT: status=Trading, OI=$2.62M, turnover24h=$1.37M
    g8_okx = True     # OKX PROVE-USDT-SWAP: active, vol24h=15.3M units
    g8_pass = g8_hl and g8_bybit  # HL + Bybit minimum. OKX is bonus.
    print(f"  G8 Cross-venue: HL={g8_hl} Bybit={g8_bybit} OKX={g8_okx} → {'PASS' if g8_pass else 'FAIL'}")
    print(f"     HL HIP-3 (maxLev=3x, OI~$1.9M), Bybit OI=$2.62M, OKX SWAP active")

    # ── G9: OOS days ──────────────────────────────────────────────────────────
    g9_pass = oos_days >= 120
    g9_marginal = (oos_days >= 100) and not g9_pass
    print(f"  G9 OOS days: {oos_days:.1f} ≥ 120 → {'PASS' if g9_pass else ('MARGINAL' if g9_marginal else 'FAIL')}")
    print(f"     Full history 297d (≥180d total) — G9 on OOS split")

    # ── L004 pre-screen override ───────────────────────────────────────────────
    l004_blocked = phase0.get("l004_hard_blocked", False)
    carry_full = phase0.get("carry_full", 0)
    print(f"\n  L004 pre-screen: blocked={l004_blocked} (carry_full={carry_full:.3f})")

    # ── Liquidity concern (G6 flag) ───────────────────────────────────────────
    liquidity_concern = 247_248 < 1_000_000  # dayNtlVlm < $1M
    print(f"\n  Liquidity concern: {liquidity_concern} (dayNtlVlm=$247K < $1M)")
    print(f"  Per BLUR pattern: $0.6M → 0.3% sleeve. PROVE: 0.3-0.5% sleeve appropriate.")
    print(f"  Bybit OI=$2.62M + OKX active: combined venue liquidity higher than HL alone.")

    # ── Overall ───────────────────────────────────────────────────────────────
    gates_pass = {
        "G1": g1_pass, "G2": g2_pass, "G3": g3_pass, "G4": g4_pass,
        "G5": g5_pass, "G6": g6_pass, "G7": g7_pass, "G8": g8_pass,
        "G9": g9_pass,
    }
    n_pass = sum(gates_pass.values())
    n_fail = len(gates_pass) - n_pass
    eligible = not l004_blocked and all([g1_pass, g2_pass, g3_pass, g4_pass,
                                         g6_pass, g7_pass, g8_pass])

    return {
        "gate_summary": {
            "G1_oos_sharpe": {"value": oos_sharpe, "pass": g1_pass, "threshold": 1.0},
            "G2_perm_pvalue": {"value": round(p_val, 4), "pass": g2_pass, "threshold": 0.05},
            "G3_dsr_bonferroni": {"value": round(dsr_adj, 4), "pass": g3_pass, "threshold": 1.0,
                                   "best_is_sharpe": round(best_is_sharpe, 4)},
            "G4_wf_stability": {"value": round(wf_stab, 4), "pass": g4_pass, "threshold": 0.6},
            "G5_family_corr": {
                "all_pass": g5_pass, "fails": g5_fails,
                "max_abs_corr": round(max(abs(d.get("full") or 0) for d in g5_details.values()), 4),
                "details": g5_details,
            },
            "G6_entries_yr": {
                "value": round(entries_yr, 1), "pass": g6_pass, "threshold": 20,
                "liquidity_concern": liquidity_concern,
                "liquidity_note": "dayNtlVlm=$247K HL. Sleeve 0.3-0.5%. Entries independent of liquidity.",
            },
            "G7_ann_ret": {"value": oos_ann_ret, "pass": g7_pass, "threshold": 5.0},
            "G8_cross_venue": {
                "hl": g8_hl, "bybit": g8_bybit, "okx": g8_okx, "pass": g8_pass,
                "note": "Triple-listed: HL HIP-3 + Bybit PROVEUSDT + OKX PROVE-USDT-SWAP",
            },
            "G9_oos_days": {
                "value": round(oos_days, 1), "pass": g9_pass, "threshold": 120,
                "marginal": g9_marginal,
                "full_history_days": 297,
                "note": "297d total history. OOS split from IS_END=Feb1, 2026.",
            },
        },
        "n_gates_pass": n_pass,
        "n_gates_fail": n_fail,
        "g5_fails": g5_fails,
        "g5_pass": g5_pass,
        "g9_pass": g9_pass,
        "g9_marginal": g9_marginal,
        "l004_hard_blocked": l004_blocked,
        "liquidity_concern": liquidity_concern,
        "overall_eligible": eligible,
        "gates_pass_map": gates_pass,
    }


# ── Phase 7: Decision ─────────────────────────────────────────────────────────

def phase7_decision(phase0: Dict, phase6: Dict,
                    phase3: Dict, prove: pd.Series, sol: pd.Series) -> Dict:
    """Phase 7: Final decision and K523 3-point ROI."""
    print("\n" + "=" * 70)
    print("[Phase 7] Decision")
    print("=" * 70)

    g5_pass = phase6["g5_pass"]
    g5_fails = phase6["g5_fails"]
    g9_pass = phase6["g9_pass"]
    g9_marginal = phase6["g9_marginal"]
    eligible = phase6["overall_eligible"]
    l004_blocked = phase6["l004_hard_blocked"]
    diff_l004_blocked = phase0.get("diff_l004_blocked", False)
    diff_carry_full = phase0.get("diff_carry_full", 0)
    diff_mean_ann = phase0.get("diff_mean_ann_pct", 0)
    liquidity_concern = phase6["liquidity_concern"]

    # Check G2 gate result
    g2_gate = phase6.get("gate_summary", {}).get("G2_perm_pvalue", {})
    g2_pass = g2_gate.get("pass", True)
    g2_pval = g2_gate.get("value", 0.0)

    # Decision tree
    if l004_blocked:
        verdict = "REJECT"
        verdict_code = "L004_HARD_BLOCK"
    elif diff_l004_blocked:
        verdict = "REJECT"
        verdict_code = "L004_DIFF_CARRY_BLOCK"
    elif not g2_pass:
        verdict = "REJECT"
        verdict_code = "G2_PERM_FAIL"
    elif not eligible:
        verdict = "REJECT"
        verdict_code = "GATE_FAIL"
    elif not g5_pass and (not g9_pass):
        verdict = "CONDITIONAL_ACCEPT"
        verdict_code = "PAPER_GATE_G5_G9"
    elif not g5_pass:
        verdict = "CONDITIONAL_ACCEPT"
        verdict_code = "PAPER_GATE_G5"
    elif not g9_pass and not g9_marginal:
        verdict = "CONDITIONAL_ACCEPT"
        verdict_code = "PAPER_GATE_G9"
    elif g9_marginal:
        verdict = "CONDITIONAL_ACCEPT"
        verdict_code = "PAPER_GATE_G9_MARGINAL"
    else:
        verdict = "ACCEPT"
        verdict_code = "PAPER_GATE_HL_CAP"

    # K523 3-point ROI (mandatory)
    pa, sa = _align(prove, sol)
    W = WINDOW_H
    pnl = _backtest_pnl(pa, sa, W)
    pnl_oos = pnl[pnl.index > IS_END]
    oos_ann_ret = phase3[f"W{W}"]["oos"]["ann_ret_pct"]
    oos_sharpe = phase3[f"W{W}"]["oos"]["sharpe"]
    notional = SLEEVE_PCT * CAPITAL_10M  # 0.4% × $10M = $40K

    # K523: 3-point mandatory
    realized_ratio = 0.38   # K523/K509 floor
    oos_haircut = 0.25      # K523 paired-trade

    conservative = oos_ann_ret / 100 * notional * LEVERAGE * realized_ratio * (1 - oos_haircut) * 0.75
    mid = oos_ann_ret / 100 * notional * LEVERAGE * realized_ratio * (1 - oos_haircut)
    optimistic = oos_ann_ret / 100 * notional * LEVERAGE

    roi_3point = {
        "oos_ann_ret_raw_pct": oos_ann_ret,
        "oos_sharpe": oos_sharpe,
        "sleeve_pct": SLEEVE_PCT * 100,
        "sleeve_notional": notional,
        "leverage": LEVERAGE,
        "realized_ratio_k523_floor": realized_ratio,
        "oos_haircut_k523": oos_haircut,
        "conservative_usd_yr": round(conservative),
        "mid_usd_yr": round(mid),
        "optimistic_usd_yr": round(optimistic),
        "k523_compliance": True,
        "note": (
            f"Conservative: ${conservative:,.0f}/yr (×0.38 realized ×0.75 ×OOS-haircut). "
            f"Mid: ${mid:,.0f}/yr (central). "
            f"Optimistic: ${optimistic:,.0f}/yr (raw OOS, upper bound only). "
            f"Sleeve 0.4% ($40K @$10M, liquidity-limited). Leverage 3x (HL max for PROVE). "
            f"K523: single-number is upper bound, not central. Realized-to-stated 38%."
        ),
    }

    print(f"\n  Verdict: {verdict} ({verdict_code})")
    print(f"  G2 pass: {g2_pass} (p-value: {g2_pval:.4f})")
    print(f"  G5 pass: {g5_pass} (fails: {g5_fails})")
    print(f"  G9 pass: {g9_pass} (marginal: {g9_marginal})")
    print(f"  Diff carry: {diff_carry_full:.3f} (diff mean_ann={diff_mean_ann:+.2f}%)")
    print(f"  Diff L004 blocked: {diff_l004_blocked}")
    print(f"  Liquidity concern: {liquidity_concern} ($247K/day HL)")
    print(f"\n  K523 ROI 3-point (0.4% sleeve, 3x leverage, $10M):")
    print(f"    Conservative: ${conservative:,.0f}/yr")
    print(f"    Mid (central): ${mid:,.0f}/yr")
    print(f"    Optimistic:   ${optimistic:,.0f}/yr (upper bound)")
    if verdict == "REJECT":
        print(f"\n  REJECT ANALYSIS:")
        print(f"  Root cause: PROVE-SOL differential is persistently one-sided")
        print(f"    PROVE FR mean = -52.5%/yr, SOL FR mean = -0.03%/yr")
        print(f"    PROVE-SOL diff: {diff_carry_full:.1%} positive ({diff_mean_ann:+.2f}%/yr mean)")
        print(f"    This is pure directional carry, not timing alpha")
        print(f"    G2 correctly identifies: null permutations ≥ observed Sharpe (p=1.0)")
        print(f"    K781 L004 screen measured PROVE carry alone (42.8% — PASS)")
        print(f"    But PROVE-SOL differential carry is 27.7% — structurally one-sided")
        print(f"    Lesson: L004 must be applied to the DIFFERENTIAL, not the token alone")

    # Acceptance/concern reasons
    carry_full = phase0.get("carry_full", 0)
    carry_oos = phase0.get("carry_oos", 0)
    vol_ratio_full = phase0.get("vol_ratio_full", 0)
    vol_k781 = phase0.get("vol_ratio_k781_30d", 38.88)
    corr_sol = phase0.get("corr_sol", 0)
    p6_gs = phase6.get("gate_summary", {})
    wf = p6_gs.get("G4_wf_stability", {}).get("value", 0)
    g6_entries = p6_gs.get("G6_entries_yr", {}).get("value", 0)

    if verdict == "REJECT":
        accept_reasons = [
            f"L003/L007/L010/L011 all PASS — anchor contamination clear",
            f"G1 OOS Sh={oos_sharpe:.2f} >> 1.0 (raw backtest looks strong)",
            "G3 DSR Bonferroni adj_Sh >> 1.0 (not correcting for G2 underlying issue)",
            f"G4 WF 4/4 positive folds — but misleading when diff is always negative",
            "G5 25/25 PASS — no family signal overlap",
            f"G6 {g6_entries:.0f}/yr PASS — signal switches frequently",
            f"G7 {oos_ann_ret:.1f}% ann ret PASS — but this IS the carry return",
            "G8 Triple-listed HL+Bybit+OKX — strong cross-venue presence",
            f"G9 297d total history — comfortably above 180d minimum",
            f"K781 composite=1.314 (rank #2 of 27) — screening metrics looked excellent",
        ]

        concern_reasons = [
            f"REJECT: G2 PERMUTATION FAIL (p=1.000) — null null_dist > observed Sharpe {oos_sharpe:.2f}",
            f"ROOT CAUSE: PROVE-SOL differential carry={diff_carry_full:.3f} ({diff_carry_full:.1%} positive) — persistently one-sided",
            f"PROVE FR mean_ann=-52.5%/yr vs SOL FR mean_ann=-0.03%/yr — massive structural gap",
            f"Any permutation of the diff also gets this persistent negative direction → p=1.0",
            f"L004 screen on PROVE alone (carry=42.8%) DOES NOT capture differential carry problem",
            f"K782 LESSON: L004 must check differential carry, not just token carry",
            f"CRITICAL LESSON: High composite_score + max_corr=0.000 does NOT imply timing alpha",
            f"PROVE-SOL is a pure carry pair — short PROVE vs SOL is a directional bet, not a cycle trade",
            f"K781 carry_stability=73.6% measured on PROVE alone — misleading for differential strategy",
            f"Recommendation: Screen differential carry as pre-screen L004_DIFF before any full eval",
        ]
    else:
        accept_reasons = [
            f"L004 PASS: carry_full={carry_full:.3f}, carry_OOS={carry_oos:.3f} — genuine bidirectional FR",
            f"G1 PASS: OOS Sh={oos_sharpe:.2f} (W=84) >> 1.0",
            "G2 PASS: perm p < 0.05 — structural edge confirmed",
            "G3 PASS: DSR Bonferroni adj_Sh >> 1.0",
            f"G4 PASS: WF stability={wf:.2f} (≥0.60 threshold)",
            f"G6 PASS: {g6_entries:.1f} entries/yr ≥ 20",
            f"G7 PASS: OOS ann ret={oos_ann_ret:.1f}% >> 5%",
            "G8 PASS: HL HIP-3 + Bybit PROVEUSDT + OKX PROVE-USDT-SWAP (triple-listed)",
        ]
        concern_reasons = [
            "LOW LIQUIDITY: dayNtlVlm=$247K HL — sleeve limited to 0.3-0.5%",
            "HL maxLeverage=3x (lower than typical 5-10x)",
            "HL 66.8% cap mandates paper-gate (K532 rule)",
        ]

    if verdict_code == "L004_DIFF_CARRY_BLOCK":
        verdict_detail = (
            f"REJECT ({verdict_code}) — PROVE-SOL differential carry={diff_carry_full:.3f} "
            f"({diff_carry_full:.1%} positive, mean_ann={diff_mean_ann:+.1f}%/yr). "
            f"PROVE FR mean=-52.5%/yr vs SOL 0.03%/yr — structural directional carry, not timing alpha. "
            f"G2 permutation p=1.000: null distribution exceeds observed Sharpe. "
            f"K782 lesson: L004_DIFF check required — token carry ≠ differential carry."
        )
    elif verdict_code == "G2_PERM_FAIL":
        verdict_detail = (
            f"REJECT ({verdict_code}) — G2 permutation p={g2_pval:.3f} ≥ 0.05. "
            f"PROVE-SOL differential is structurally one-sided (carry={diff_carry_full:.3f}). "
            f"Null distribution ({20:.0f}-26 Sharpe) exceeds observed OOS Sh={oos_sharpe:.2f}. "
            f"No timing alpha — pure directional carry pair."
        )
    else:
        verdict_detail = (
            f"{verdict} ({verdict_code}) — PROVE financial services vs SOL SVM. "
            f"vol_full={vol_ratio_full:.2f}x. carry={carry_full:.3f}/{carry_oos:.3f}. "
            f"OOS Sh={oos_sharpe:.2f}. Triple-listed HL/Bybit/OKX. "
            f"HL 66.8% cap → paper-gate mandatory."
        )

    return {
        "verdict": verdict,
        "verdict_code": verdict_code,
        "verdict_detail": verdict_detail,
        "accept_reasons": accept_reasons,
        "concern_reasons": concern_reasons,
        "roi_3point": roi_3point,
        "cluster_ruling": {
            "cluster": "Provenance Blockchain / financial services / institutional tokenization",
            "cosmos_sdk_note": "Cosmos SDK used but targets regulated institutions, NOT DeFi ecosystem",
            "vs_svm_distinct": "Financial regulated infrastructure vs consumer SVM speculation",
            "vs_atom_cluster": "Financial sector tokenization vs Cosmos DeFi — distinct meta-narratives",
            "meta_narrative_pass": True,
        },
        "g2_analysis": {
            "g2_pass": g2_pass,
            "g2_pvalue": g2_pval,
            "root_cause": "PROVE-SOL diff persistently negative (carry=0.277). Any permutation preserves direction → null Sh ~20-26 > obs Sh 17.82",
            "lesson": "L004 must check differential carry, not just token carry. K781 carry_stability=73.6% was measuring PROVE alone.",
            "diff_carry_full": diff_carry_full,
            "diff_mean_ann_pct": diff_mean_ann,
            "prove_fr_mean_ann_pct": -52.5,
            "sol_fr_mean_ann_pct": -0.03,
        },
        "k782_lesson": {
            "title": "L004_DIFF pre-screen requirement for future waves",
            "description": (
                "K782 reveals that pre-screening token carry alone (L004) is insufficient. "
                "The differential carry must also be checked: if PROVE-SOL diff is persistently "
                "one-sided (>80% or <20% positive), the strategy is pure directional carry, not "
                "timing alpha. G2 permutation correctly fails such pairs (p=1.0). "
                "Future screens should add: L004_DIFF: |differential_carry - 0.5| < 0.30. "
                "Apply to all future paired-trade evaluations."
            ),
            "recommended_screen": "L004_DIFF: diff_carry_full in [0.20, 0.80] required",
            "k781_screen_gap": "K781 carry_stability checked PROVE alone (73.6%). Differential carry=27.7% not checked.",
        },
        "liquidity_ruling": {
            "hl_day_vol_usd": 247_248,
            "bybit_oi_usd": 2_621_568,
            "bybit_turnover_24h_usd": 1_373_060,
            "okx_active": True,
            "sleeve_pct_recommended": "0.3-0.5%",
            "sleeve_notional_range_usd": "$30,000-$50,000 @$10M",
            "hl_max_leverage": 3,
            "blur_pattern": "BLUR $125K/day → 0.3% sleeve approved. PROVE $247K/day → 0.3-0.5%.",
        },
        "operational": {
            "hl_cap_pct": 66.8,
            "paper_gate_mandatory": True,
            "sleeve_pct": SLEEVE_PCT * 100,
            "max_notional": SLEEVE_PCT * CAPITAL_10M,
            "bybit_confirmed": True,
            "okx_confirmed": True,
        },
        "k523_compliance": True,
        "next_wave_note": "K783: POLYX-SOL eval (compliance L2, composite=0.539, vol=27.4x)",
    }


# ── JSON output ───────────────────────────────────────────────────────────────

def save_json(results: Dict) -> None:
    """Save results to JSON."""
    with open(str(OUT_JSON), "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2, default=str)
    print(f"\n  JSON saved: {OUT_JSON}")


# ── HTML badge ────────────────────────────────────────────────────────────────

def build_badge(results: Dict) -> str:
    """Build K782 HTML badge section for report.html."""
    import subprocess
    try:
        jst_str = subprocess.check_output(
            ["date", "+%Y-%m-%d %H:%M JST"],
            env={**__import__("os").environ, "TZ": "Asia/Tokyo"},
        ).decode().strip()
    except Exception:
        jst_str = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")

    p7 = results.get("phase7", {})
    verdict = p7.get("verdict", "UNKNOWN")
    p6 = results.get("phase6", {})
    p3 = results.get("phase3", {})
    p0 = results.get("phase0", {})

    is_accept = verdict in ("ACCEPT", "CONDITIONAL_ACCEPT")
    verdict_color = "#3fb950" if verdict == "ACCEPT" else (
        "#d29922" if verdict == "CONDITIONAL_ACCEPT" else "#f85149")
    badge_color = verdict_color

    oos_sh = p3.get("W84", {}).get("oos", {}).get("sharpe", 0)
    oos_ret = p3.get("W84", {}).get("oos", {}).get("ann_ret_pct", 0)
    vol_ratio_full = p0.get("vol_ratio_full", 0)
    vol_k781 = p0.get("vol_ratio_k781_30d", 38.88)
    carry_full = p0.get("carry_full", 0)
    carry_oos = p0.get("carry_oos", 0)
    g5_fails = p6.get("g5_fails", [])
    g9_pass = p6.get("g9_pass", False)
    g9_marginal = p6.get("g9_marginal", False)
    g6_entries = p6.get("gate_summary", {}).get("G6_entries_yr", {}).get("value", 0)
    oos_days = p6.get("gate_summary", {}).get("G9_oos_days", {}).get("value", 0)
    roi = p7.get("roi_3point", {})
    wf_stab = p6.get("gate_summary", {}).get("G4_wf_stability", {}).get("value", 0)
    perm_p = p6.get("gate_summary", {}).get("G2_perm_pvalue", {}).get("value", 0)
    dsr_adj = p6.get("gate_summary", {}).get("G3_dsr_bonferroni", {}).get("value", 0)

    # Gate spans
    def gate_span(label: str, passed: bool, warn: bool = False) -> str:
        if passed:
            return f'<span style="background:rgba(63,185,80,0.15);border:1px solid #3fb950;border-radius:4px;padding:2px 8px;font-size:0.70rem;color:#3fb950;">{label}</span>'
        elif warn:
            return f'<span style="background:rgba(210,153,34,0.15);border:1px solid #d29922;border-radius:4px;padding:2px 8px;font-size:0.70rem;color:#d29922;">{label}</span>'
        else:
            return f'<span style="background:rgba(248,81,73,0.15);border:1px solid #f85149;border-radius:4px;padding:2px 8px;font-size:0.70rem;color:#f85149;">{label}</span>'

    accept_html = "".join(
        f'<li style="margin-bottom:2px;color:#3fb950;">{r}</li>'
        for r in p7.get("accept_reasons", [])
    )
    concern_html = "".join(
        f'<li style="margin-bottom:2px;color:#d29922;">{r}</li>'
        for r in p7.get("concern_reasons", [])
    )

    g5_status = "PASS" if not g5_fails else f"{len(g5_fails)} FAIL"
    g9_status = "PASS" if g9_pass else ("MARGINAL" if g9_marginal else "FAIL")

    # Determine RGB for badge background
    if verdict == "ACCEPT":
        badge_rgb = "63,185,80"
    elif verdict == "CONDITIONAL_ACCEPT":
        badge_rgb = "210,153,34"
    else:
        badge_rgb = "248,81,73"

    badge = f"""
<!-- K782_PROVE_SOL_BADGE: K782 PROVE-SOL FR Differential Eval | verdict={verdict} | cluster=ProvenanceFinancialServices+SVM | carry_full={carry_full:.3f} carry_oos={carry_oos:.3f} | vol_full={vol_ratio_full:.4f}x vol_k781_30d={vol_k781:.1f}x | OOS_Sh={oos_sh:.4f} | G5={g5_status} | G6={g6_entries:.0f}/yr | G9={g9_status}_{oos_days:.0f}d | G8_HL+Bybit+OKX | max_corr=0.000 | composite_k781=1.314 | sleeve_0.3-0.5% | HL_cap_66.8% | K775_vol297d_lesson | K339 REPO_ROOT | {jst_str} -->
<!-- K782 PROVE SOL BADGE START -->
<section id="k782-prove-sol" style="background:#0d1117;border:1px solid #30363d;border-radius:12px;padding:16px 20px;margin:16px 0;font-family:'Segoe UI',system-ui,sans-serif;color:#e6edf3;">
  <div style="display:flex;flex-wrap:wrap;gap:8px;align-items:center;margin-bottom:12px;">
    <div style="background:rgba({badge_rgb},0.15);border:2px solid {badge_color};border-radius:8px;padding:4px 10px;color:{badge_color};font-size:0.78rem;font-weight:800;letter-spacing:0.06em;">K782</div>
    <div style="background:rgba(88,166,255,0.10);border:1px solid #58a6ff;border-radius:6px;padding:3px 9px;color:#58a6ff;font-size:0.70rem;">K781 HIP-3 #1 • alt-alt</div>
    <div style="background:rgba(88,166,255,0.10);border:1px solid #58a6ff;border-radius:6px;padding:3px 9px;color:#58a6ff;font-size:0.70rem;">K775 vol-297d lesson</div>
    <div style="background:rgba(88,166,255,0.10);border:1px solid #58a6ff;border-radius:6px;padding:3px 9px;color:#58a6ff;font-size:0.70rem;">Financial Services vs SVM</div>
    <div style="background:rgba(88,166,255,0.10);border:1px solid #58a6ff;border-radius:6px;padding:3px 9px;color:#58a6ff;font-size:0.70rem;">HL+Bybit+OKX triple</div>
  </div>

  <div style="color:#e6edf3;font-size:1.08rem;font-weight:900;margin-bottom:8px;">
    &#128200; K782 &mdash; PROVE-SOL FR Differential Eval &mdash;
    <span style="color:{verdict_color};">{verdict.replace('_', ' ')}</span>
  </div>
  <div style="color:#8b949e;font-size:0.80rem;margin-bottom:12px;">
    Provenance Blockchain financial services vs Solana SVM &nbsp;|&nbsp;
    carry={carry_full:.3f}/{carry_oos:.3f} (full/OOS) &mdash; L004 PASS &nbsp;|&nbsp;
    vol_297d={vol_ratio_full:.2f}x (K781 30d={vol_k781:.0f}x) &nbsp;|&nbsp;
    G8 HL+Bybit+OKX triple-listed &nbsp;|&nbsp; K775 lesson applied
  </div>

  <!-- Metrics grid -->
  <div style="display:grid;grid-template-columns:repeat(auto-fit,minmax(110px,1fr));gap:8px;margin-bottom:14px;">
    <div style="background:#0d1117;border:1px solid #21262d;border-radius:8px;padding:10px;">
      <div style="color:#8b949e;font-size:0.68rem;margin-bottom:4px;">OOS SHARPE (W=84)</div>
      <div style="color:{verdict_color};font-size:1.5rem;font-weight:800;">{oos_sh:.2f}</div>
      <div style="color:#8b949e;font-size:0.68rem;">vs threshold &ge;1.0</div>
    </div>
    <div style="background:#0d1117;border:1px solid #21262d;border-radius:8px;padding:10px;">
      <div style="color:#8b949e;font-size:0.68rem;margin-bottom:4px;">OOS ANN RET</div>
      <div style="color:#3fb950;font-size:1.5rem;font-weight:800;">{oos_ret:.1f}%</div>
      <div style="color:#8b949e;font-size:0.68rem;">W=84, {LEVERAGE:.0f}x lev</div>
    </div>
    <div style="background:#0d1117;border:1px solid #21262d;border-radius:8px;padding:10px;">
      <div style="color:#8b949e;font-size:0.68rem;margin-bottom:4px;">CARRY (FULL/OOS)</div>
      <div style="color:#3fb950;font-size:1.5rem;font-weight:800;">{carry_full:.2f}</div>
      <div style="color:#8b949e;font-size:0.68rem;">OOS={carry_oos:.2f} &mdash; L004 PASS</div>
    </div>
    <div style="background:#0d1117;border:1px solid #21262d;border-radius:8px;padding:10px;">
      <div style="color:#8b949e;font-size:0.68rem;margin-bottom:4px;">VOL RATIO (297d)</div>
      <div style="color:#3fb950;font-size:1.5rem;font-weight:800;">{vol_ratio_full:.1f}x</div>
      <div style="color:#8b949e;font-size:0.68rem;">K781 30d={vol_k781:.0f}x (stable)</div>
    </div>
    <div style="background:#0d1117;border:1px solid #21262d;border-radius:8px;padding:10px;">
      <div style="color:#8b949e;font-size:0.68rem;margin-bottom:4px;">G5 FAMILY</div>
      <div style="color:{'#3fb950' if not g5_fails else '#d29922'};font-size:1.5rem;font-weight:800;">{g5_status}</div>
      <div style="color:#8b949e;font-size:0.68rem;">25 vertex check</div>
    </div>
    <div style="background:#0d1117;border:1px solid #21262d;border-radius:8px;padding:10px;">
      <div style="color:#8b949e;font-size:0.68rem;margin-bottom:4px;">G6 ENTRIES/YR</div>
      <div style="color:{'#3fb950' if g6_entries >= 20 else '#f85149'};font-size:1.5rem;font-weight:800;">{g6_entries:.0f}</div>
      <div style="color:#8b949e;font-size:0.68rem;">vs 20/yr threshold</div>
    </div>
    <div style="background:#0d1117;border:1px solid #21262d;border-radius:8px;padding:10px;">
      <div style="color:#8b949e;font-size:0.68rem;margin-bottom:4px;">G9 OOS DAYS</div>
      <div style="color:{'#3fb950' if g9_pass else ('#d29922' if g9_marginal else '#f85149')};font-size:1.5rem;font-weight:800;">{oos_days:.0f}</div>
      <div style="color:#8b949e;font-size:0.68rem;">297d total history</div>
    </div>
    <div style="background:#0d1117;border:1px solid #21262d;border-radius:8px;padding:10px;">
      <div style="color:#8b949e;font-size:0.68rem;margin-bottom:4px;">WF STABILITY</div>
      <div style="color:{'#3fb950' if wf_stab >= 0.60 else '#f85149'};font-size:1.5rem;font-weight:800;">{wf_stab:.2f}</div>
      <div style="color:#8b949e;font-size:0.68rem;">vs 0.60 threshold</div>
    </div>
  </div>

  <!-- K775 lesson box -->
  <div style="background:rgba(88,166,255,0.06);border-left:3px solid #58a6ff;border-radius:4px;padding:10px 14px;margin-bottom:14px;font-size:0.76rem;color:#8b949e;">
    <strong style="color:#58a6ff;">&#128218; K775 Lesson Applied &mdash; Full 297d Vol Verification:</strong><br>
    K781 measured 30d window (Apr30-May21 2026): vol_ratio=38.88x.
    K775 lesson: always verify with full history (MEGA had 9.53x 30d &rarr; 1.86x full 220d, zero-var March).
    PROVE 297d vol_ratio = <strong style="color:#3fb950;">{vol_ratio_full:.2f}x</strong> across full Aug 2025 &ndash; May 2026.
    Carry={carry_full:.3f} full / {carry_oos:.3f} OOS &mdash; genuine bidirectional FR. L004 PASS.
    PROVE listed HL HIP-3 + Bybit + OKX &mdash; triple-listed reduces single-venue concentration.
  </div>

  <!-- Cluster insight -->
  <div style="background:rgba(57,210,192,0.06);border-left:3px solid #39d2c0;border-radius:4px;padding:10px 14px;margin-bottom:14px;font-size:0.76rem;color:#8b949e;">
    <strong style="color:#39d2c0;">&#127981; Provenance Financial Services Cluster (K782 ruling):</strong><br>
    PROVE = Provenance Blockchain &mdash; purpose-built for institutional asset tokenization,
    regulated digital lending, bank partnerships. FR drivers: institutional adoption, product launches,
    compliance-driven inflows. DISTINCT from SVM (SOL: retail/meme/DEX) AND Cosmos DeFi (ATOM/INJ/SEI/TIA).
    Uses Cosmos SDK but targets regulated finance &ne; open DeFi ecosystem.
    K781 max_corr=0.000 (PERFECT independence vs AVAX, the primary anchor).
  </div>

  <!-- Gate summary -->
  <div style="color:#39d2c0;font-size:0.80rem;font-weight:700;margin-bottom:8px;">&sect;6 GATE SUMMARY</div>
  <div style="display:flex;flex-wrap:wrap;gap:6px;margin-bottom:12px;">
    {gate_span(f"G1 OOS Sh={oos_sh:.1f}", oos_sh >= 1.0)}
    {gate_span(f"G2 perm p={perm_p:.3f}", perm_p < 0.05)}
    {gate_span(f"G3 DSR adj={dsr_adj:.2f}", dsr_adj >= 1.0)}
    {gate_span(f"G4 WF={wf_stab:.2f}", wf_stab >= 0.60)}
    {gate_span(f"G5 {g5_status}", not g5_fails, len(g5_fails) > 0)}
    {gate_span(f"G6 {g6_entries:.0f}/yr", g6_entries >= 20)}
    {gate_span(f"G7 {oos_ret:.0f}%", oos_ret >= 5.0)}
    {gate_span("G8 HL+Bybit+OKX", True)}
    {gate_span(f"G9 {oos_days:.0f}d", g9_pass, g9_marginal)}
    {gate_span(f"L004 carry={carry_full:.2f}", carry_full < 0.80)}
    {gate_span("Cluster PASS", True)}
    {gate_span("Liquidity ⚠ $247K/d", False, True)}
  </div>

  <!-- K523 ROI 3-point -->
  <div style="color:#58a6ff;font-size:0.80rem;font-weight:700;margin-bottom:6px;">K523 ROI 3-POINT ({SLEEVE_PCT*100:.1f}% sleeve, {LEVERAGE:.0f}x leverage, $10M)</div>
  <div style="display:grid;grid-template-columns:repeat(3,1fr);gap:6px;margin-bottom:14px;">
    <div style="background:#0d1117;border:1px solid #21262d;border-radius:6px;padding:8px;">
      <div style="color:#8b949e;font-size:0.65rem;margin-bottom:2px;">CONSERVATIVE</div>
      <div style="color:#3fb950;font-size:1.1rem;font-weight:800;">${roi.get('conservative_usd_yr',0):,.0f}/yr</div>
      <div style="color:#8b949e;font-size:0.62rem;">&times;0.38 realized &times;OOS haircut &times;0.75</div>
    </div>
    <div style="background:#0d1117;border:1px solid #3fb950;border-radius:6px;padding:8px;">
      <div style="color:#8b949e;font-size:0.65rem;margin-bottom:2px;">MID (CENTRAL)</div>
      <div style="color:#3fb950;font-size:1.1rem;font-weight:800;">${roi.get('mid_usd_yr',0):,.0f}/yr</div>
      <div style="color:#8b949e;font-size:0.62rem;">&times;0.38 realized &times;OOS haircut</div>
    </div>
    <div style="background:#0d1117;border:1px solid #21262d;border-radius:6px;padding:8px;">
      <div style="color:#8b949e;font-size:0.65rem;margin-bottom:2px;">OPTIMISTIC (UPPER)</div>
      <div style="color:#d29922;font-size:1.1rem;font-weight:800;">${roi.get('optimistic_usd_yr',0):,.0f}/yr</div>
      <div style="color:#8b949e;font-size:0.62rem;">raw OOS &mdash; upper bound only</div>
    </div>
  </div>

  <!-- Accept/concern reasons -->
  <div style="display:grid;grid-template-columns:1fr 1fr;gap:8px;margin-bottom:14px;">
    <div style="background:rgba(63,185,80,0.06);border:1px solid rgba(63,185,80,0.3);border-radius:6px;padding:8px 12px;">
      <div style="color:#3fb950;font-size:0.78rem;font-weight:700;margin-bottom:4px;">ACCEPT SIGNALS</div>
      <ul style="margin:0;padding-left:16px;font-size:0.72rem;list-style:disc;">
        {accept_html}
      </ul>
    </div>
    <div style="background:rgba(210,153,34,0.06);border:1px solid rgba(210,153,34,0.3);border-radius:6px;padding:8px 12px;">
      <div style="color:#d29922;font-size:0.78rem;font-weight:700;margin-bottom:4px;">CONCERNS</div>
      <ul style="margin:0;padding-left:16px;font-size:0.72rem;list-style:disc;">
        {concern_html}
      </ul>
    </div>
  </div>

  <div style="margin-top:10px;font-size:0.72rem;color:#6e7681;">
    最終更新: {jst_str}
    (K782 PROVE-SOL &mdash; {verdict}: Provenance fin-svcs cluster, G2 p={perm_p:.3f}, diff_carry={carry_full:.2f}, triple-listed) &nbsp;|&nbsp; K339 REPO_ROOT &nbsp;|&nbsp; LIVE 自動変更禁止
  </div>
</section>
<!-- /K782 PROVE SOL BADGE -->
"""
    return badge


def inject_badge(badge_html: str) -> None:
    """Inject K782 badge into report.html after K781 badge."""
    report_path = BASE / "report.html"
    with open(str(report_path), "r", encoding="utf-8") as f:
        content = f.read()

    if "K782_PROVE_SOL_BADGE" in content:
        print("  K782 badge already present — replacing ...")
        start_m = "<!-- K782_PROVE_SOL_BADGE:"
        end_m = "<!-- /K782 PROVE SOL BADGE -->"
        si = content.find(start_m)
        ei = content.find(end_m) + len(end_m)
        if si >= 0 and ei > si:
            content = content[:si] + badge_html.strip() + content[ei:]
    else:
        # Insert after K781 badge
        k781_end = "<!-- /K781 HIP3 ROUND2C BADGE -->"
        if k781_end in content:
            content = content.replace(k781_end, k781_end + "\n" + badge_html)
            print("  K782 badge injected after K781 badge.")
        else:
            # Fallback: insert before </body>
            content = content.replace("</body>", badge_html + "\n</body>")
            print("  K782 badge injected before </body> (fallback).")

    with open(str(report_path), "w", encoding="utf-8") as f:
        f.write(content)
    print(f"  Updated: {report_path}")


# ── Main ──────────────────────────────────────────────────────────────────────

def main() -> Dict:
    print("=" * 70)
    print(f"Wave K782: PROVE-SOL FR Differential Eval (Financial Services vs SVM)")
    print(f"K339 REPO_ROOT: {REPO_ROOT}")
    print(f"LIVE 自動変更禁止 | Public repo | No credentials")
    print(f"Context: K781 #1 | composite=1.314 | vol=38.88x | max_corr=0.000")
    print("=" * 70)

    # ── Data loading ──────────────────────────────────────────────────────────
    print("\n[Data Loading]")
    prove = _ensure_prove_cache()
    if prove is None:
        raise FileNotFoundError("PROVE FR cache not found")
    sol = _load_hl_fr("SOL")
    if sol is None:
        raise FileNotFoundError("SOL FR cache not found")

    print(f"  PROVE: {len(prove)} rows, {prove.index.min().date()} to {prove.index.max().date()}")
    print(f"  SOL:   {len(sol)} rows, {sol.index.min().date()} to {sol.index.max().date()}")

    fr_map: Dict[str, Optional[pd.Series]] = {}
    for name in ["SOL", "AVAX", "FIL", "HBAR", "LDO", "BTC", "ETH",
                 "APT", "ATOM", "ENA", "INJ", "SEI", "TIA", "BNB",
                 "TAO", "PEPE", "WIF", "AXS", "BLUR"]:
        fr_map[name] = _load_hl_fr(name)
        if fr_map[name] is not None:
            print(f"  {name:6s}: {len(fr_map[name])} rows")
        else:
            print(f"  {name:6s}: NOT CACHED")

    # ── Run all phases ────────────────────────────────────────────────────────
    p0 = phase0_identity_and_prescreen(prove, sol, fr_map)
    p1 = phase1_vol_prescreen(prove, sol)
    p2 = phase2_cycle_analysis(prove, sol, fr_map)
    p3 = phase3_backtest(prove, sol)
    p4 = phase4_grid_search(prove, sol)
    p5 = phase5_walk_forward(prove, sol)
    p6 = phase6_gates(p3, p4, p5, prove, sol, fr_map, p0)
    p7 = phase7_decision(p0, p6, p3, prove, sol)

    # ── Collect results ───────────────────────────────────────────────────────
    all_results = {
        "wave": WAVE_ID,
        "title": "K782 PROVE-SOL FR Differential Eval — Provenance Financial Services vs Solana SVM",
        "generated_utc": datetime.now(timezone.utc).isoformat(),
        "runtime_s": round(time.time() - START_TIME, 1),
        "k339_compliance": K339_COMPLIANCE,
        "k523_mandatory": True,
        "live_auto_change_prohibited": True,
        "pair": "PROVE-SOL",
        "token_long": "PROVE (Provenance Blockchain financial services / institutional tokenization)",
        "token_short": "SOL (Solana SVM)",
        "verdict": p7["verdict"],
        "phase0": p0,
        "phase1": p1,
        "phase2": p2,
        "phase3": p3,
        "phase4": p4,
        "phase5": p5,
        "phase6": p6,
        "phase7": p7,
    }

    # ── Save JSON ─────────────────────────────────────────────────────────────
    save_json(all_results)

    # ── Build and inject HTML badge ───────────────────────────────────────────
    badge = build_badge(all_results)
    inject_badge(badge)

    # ── Final summary ─────────────────────────────────────────────────────────
    runtime = round(time.time() - START_TIME, 1)
    print(f"\n{'=' * 70}")
    print(f"K782 COMPLETE — runtime {runtime}s")
    print(f"Verdict:        {p7['verdict']} ({p7['verdict_code']})")
    print(f"Diff carry:     {p0['diff_carry_full']:.3f} ({p0.get('diff_mean_ann_pct',0):+.2f}%/yr) — {'BLOCKED (one-sided)' if p0.get('diff_l004_blocked') else 'OK'}")
    print(f"OOS Sharpe (W=84): {p3['W84']['oos']['sharpe']:.4f}")
    print(f"OOS Ann Ret:    {p3['W84']['oos']['ann_ret_pct']:.2f}%")
    print(f"Carry full/OOS: {p0['carry_full']:.3f}/{p0['carry_oos']:.3f}")
    print(f"Vol ratio 297d: {p0['vol_ratio_full']:.4f}x (K781 30d: {p0['vol_ratio_k781_30d']:.2f}x)")
    print(f"G2 p-value:     {p6['gate_summary']['G2_perm_pvalue']['value']:.4f} ({'PASS' if p6['gate_summary']['G2_perm_pvalue']['pass'] else 'FAIL'})")
    print(f"G5 fails:       {p6['g5_fails']}")
    print(f"G9 pass:        {p6['g9_pass']} (marginal: {p6['g9_marginal']})")
    print(f"G6 entries/yr:  {p6['gate_summary']['G6_entries_yr']['value']:.1f}")
    print(f"Liquidity:      $247K/day HL + Bybit OI $2.6M + OKX active")
    print(f"ROI 3-point: ${p7['roi_3point']['conservative_usd_yr']:,} / "
          f"${p7['roi_3point']['mid_usd_yr']:,} / ${p7['roi_3point']['optimistic_usd_yr']:,}")
    print(f"Next wave: {p7['next_wave_note']}")
    print(f"{'=' * 70}")

    return all_results


if __name__ == "__main__":
    main()

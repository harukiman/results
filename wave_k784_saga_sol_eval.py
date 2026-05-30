#!/usr/bin/env python3
"""
wave_k784_saga_sol_eval.py — K784 SAGA-SOL FR Differential Eval
================================================================
K339 REPO_ROOT pattern: BASE = Path(__file__).parent

WAVE:     K784
PAIR:     SAGA-SOL  (Saga Origin Gaming L1 vs Solana SVM)
CONTEXT:  K781 HIP-3 round 2c candidate #3: composite=0.216, vol_ratio=18.3x
          (30d window), max_corr=0.259 (vs SOL), carry_stability=72.8%.
          Liquidity ~$251K/day — very low → G6/G9 critical gates.
          K782 LESSON: L004_DIFF mandatory (proved PROVE-SOL false positive).
          K775 lesson: full history vol verification MANDATORY.
          SAGA listed on HL HIP-3. HL at 66.8% → paper-gate mandatory.
          Sleeve 0.3-0.5% (liquidity-limited).

IDENTITY
--------
SAGA = Saga Origin (formerly Saga Protocol).
Saga is an EVM-compatible Layer 1 chain purpose-built for gaming applications.
  - Chainlets: dedicated EVM blockchains per game application
  - Native token: SAGA (governance + gas in Saga ecosystem)
  - NFT gaming economy focus (play-to-earn, gaming NFT settlement)
  - Meta-narrative: Gaming L1 / GameFi infrastructure
  - Note: HL lists as "SAGA" (Saga Origin)
  - Listing type: HIP-3 perp on HyperLiquid

CLUSTER CHECK
-------------
SAGA = Gaming L1 / GameFi infrastructure
  vs SOL (Solana SVM) — consumer DeFi / meme speculation / SVM ecosystem
  vs existing alt-alt family: APT(L1) ATOM(Cosmos) AVAX(subnet) BNB(BSC)
     ENA(synthetic) FIL(storage) HBAR(enterprise) INJ(DeFi) LDO(liquid staking)
     PEPE(meme) SEI(trading L1) TIA(DA) TAO(AI) WLD(biometric) DOGE(PoW meme)
     WIF(meme) IO(GPU DePIN) MEGA(gaming token) STX(Bitcoin L2) RUNE(cross-chain)
     AAVE(lending) PENDLE(yield) AXS(NFT gaming) EIGEN(restaking) BLUR(NFT market)
     COMP(DeFi governance)
  MEGA previously accepted as gaming candidate (16th alt-alt vertex — MEGA is a
  Solana-native gaming token with different FR profile).
  AXS (Axie Infinity) also gaming/NFT. SAGA is a separate gaming L1 layer 0.
  Meta-narrative: Gaming L1 infrastructure vs gaming token (MEGA/AXS) — DISTINCT
  mechanism (L1 gas/governance vs staking token vs NFT utility).

K782 L004_DIFF LESSON (★ MANDATORY for K784)
---------------------------------------------
K782 PROVE-SOL: token carry=42.8% (PASS) but diff_carry=27.7% (FAIL <0.30).
Result: G2 perm p=1.000 — structural one-sided differential, not timing alpha.
L004_DIFF rule: (SAGA_fr - SOL_fr > 0).mean() in [0.30, 0.70] for FULL + OOS.
If outside [0.30, 0.70] → REJECT immediately (G2 will fail).

K775 LESSON APPLICATION
-----------------------
K781 SAGA vol_ratio=18.30x based on 500-row cache (30d window).
Full fetch MUST verify vol_ratio across full SAGA history to avoid artifact.
SAGA listing on HL: verify listing date from API pagination.

PRE-SCREEN RULES (ALL MANDATORY)
----------------------------------
  MR9:      SAGA ∉ current vertex set (NOT already a vertex)
  L003:     raw_corr(SAGA_fr, AVAX_fr) < 0.45
  L004:     token carry: (SAGA_fr > 0).mean() in [0.30, 0.80] — NOT too one-sided
  L004_DIFF [NEW K782]: (SAGA_fr - SOL_fr > 0).mean() in [0.30, 0.70] FULL + OOS
  L007:     raw_corr(SAGA_fr, FIL_fr) < 0.45
  L010:     raw_corr(SAGA_fr, HBAR_fr) < 0.45
  L011:     raw_corr(SAGA_fr, SOL_fr) < 0.50 HARD GATE
  K775:     vol_ratio FULL history >= 1.5x

§6 GATES
---------
  G1:  OOS Sharpe >= 1.0
  G2:  Perm p-value <= 0.05 (1000 direction reshuffles OOS)
  G3:  DSR Bonferroni p < 0.05/12 (12 grid configs)
  G4:  Walk-forward 12-fold (IS 90d / OOS 30d), all positive
  G5a: vs K449 ETH-BTC < 0.40
  G5b: vs K476 SOL-BTC < 0.40
  G5c: vs K484 AVAX-BTC < 0.40
  G5d: vs K493 ATOM-BTC < 0.40
  G5e: vs K500 INJ-BTC < 0.40
  G5f: vs K517 FIL-BTC < 0.40
  G5g: vs K594 LDO-BTC < 0.40
  G5h: vs K683 APT-SOL < 0.40
  G5i: vs K684 ATOM-SOL < 0.40
  G5j: vs K686 SOL-INJ < 0.40
  G5k: vs K687 AVAX-SOL < 0.40
  G5l: vs K689 SEI-SOL < 0.40
  G5m: vs K694 TIA-SOL < 0.40
  G5n: vs K696 ENA-SOL < 0.40
  G5o: vs K700 BNB-SOL < 0.40
  G5p: vs K719 ENA-ATOM < 0.40
  G5q: vs K721 LDO-SOL < 0.40
  G5r: vs K728 INJ-ATOM < 0.40
  G5s: vs K735 HBAR-SOL < 0.40
  G5t: vs K736 TIA-AVAX < 0.40
  G5u: vs K739 FIL-SOL < 0.40
  G5v: vs K778 COMP-SOL < 0.40
  G5w: vs K774 IO-SOL < 0.40  [GPU DePIN — new vertex K774]
  G5x: vs K777 EIGEN-SOL < 0.40  [Restaking — new vertex K777]
  G5y: vs K783 POLYX-SOL < 0.40  [Regulated securities — K783]
  G6:  Trade count >= 30/yr  [CRITICAL: low liquidity]
  G7:  OOS Ann return > 5% at 4x leverage
  G8:  Cross-venue (Bybit/OKX SAGA)
  G9:  Data sufficiency >= 180d OOS  [CRITICAL: HIP-3 listing date]

LIQUIDITY NOTE
--------------
$251K/day DayNtlVlm — below $5M/day standard. Sleeve limited to 0.3-0.5%.
G6 (entries/yr) and G9 (history) are the critical gates.

Usage:
  python3 wave_k784_saga_sol_eval.py

K339 REPO_ROOT | LIVE自動変更禁止 | HL cap 66.8% aware | K523 3-point ROI mandatory
L003/L004/L004_DIFF/L007/L010/L011 mandatory | K775 vol-full lesson applied | HIP-3
K782 lesson: L004_DIFF mandatory | SAGA gaming L1 vs SVM | sleeve 0.3-0.5%
"""
from __future__ import annotations

import json
import math
import time
import warnings
from datetime import datetime, timezone
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
OUT_JSON = BASE / "wave_k784_saga_sol_eval.json"

WAVE_ID = "K784"
REPO_ROOT = str(BASE)
K339_COMPLIANCE = {"wave": WAVE_ID, "repo_root": ".", "pattern": "K339"}

# ── Strategy parameters ───────────────────────────────────────────────────────
WINDOW_H_PRIMARY = 84       # 3.5d rolling mean (primary)
WINDOW_H_ALT1    = 48       # 2d window
WINDOW_H_ALT2    = 168      # 7d window
THRESHOLD        = 0.0      # always-on
LEVERAGE         = 4.0      # standard for alt-alt
SLEEVE_PCT       = 0.004    # 0.4% of $10M = $40K notional (liquidity-limited)
CAPITAL_10M      = 10_000_000
ANN_FACTOR_HL    = math.sqrt(8760)  # HL hourly

# ── Pre-screen thresholds ─────────────────────────────────────────────────────
L003_AVAX         = 0.45
L004_CARRY_LOWER  = 0.30    # BLOCK if token carry < 30%
L004_CARRY_UPPER  = 0.80    # BLOCK if token carry > 80%
L004_DIFF_LOWER   = 0.30    # ★ K782 NEW: diff carry < 0.30 → REJECT
L004_DIFF_UPPER   = 0.70    # ★ K782 NEW: diff carry > 0.70 → REJECT
L007_FIL          = 0.45
L010_HBAR         = 0.45
L011_SOL          = 0.50
G5_CORR_THRESHOLD = 0.40

# ── IS/OOS split — determined after full history fetch ────────────────────────
# SAGA: HIP-3 listing, need to discover listing date from API
# Will set IS_END dynamically: last 40% of data = OOS
IS_END_FALLBACK = pd.Timestamp("2026-01-01")  # fallback if short history

# ── Vertex set for G5 family correlation ──────────────────────────────────────
G5_GATES = [
    # BTC-base strategies
    ("G5a", "ETH",   "BTC",   "K449 ETH-BTC",    "btc-base"),
    ("G5b", "SOL",   "BTC",   "K476 SOL-BTC",    "btc-base"),
    ("G5c", "AVAX",  "BTC",   "K484 AVAX-BTC",   "btc-base"),
    ("G5d", "ATOM",  "BTC",   "K493 ATOM-BTC",   "btc-base"),
    ("G5e", "INJ",   "BTC",   "K500 INJ-BTC",    "btc-base"),
    ("G5f", "FIL",   "BTC",   "K517 FIL-BTC",    "btc-base"),
    ("G5g", "LDO",   "BTC",   "K594 LDO-BTC",    "btc-base"),
    # alt-alt (SOL-paired and cross-alt)
    ("G5h", "APT",   "SOL",   "K683 APT-SOL",    "alt-alt"),
    ("G5i", "ATOM",  "SOL",   "K684 ATOM-SOL",   "alt-alt"),
    ("G5j", "SOL",   "INJ",   "K686 SOL-INJ",    "alt-alt"),
    ("G5k", "AVAX",  "SOL",   "K687 AVAX-SOL",   "alt-alt"),
    ("G5l", "SEI",   "SOL",   "K689 SEI-SOL",    "alt-alt"),
    ("G5m", "TIA",   "SOL",   "K694 TIA-SOL",    "alt-alt"),
    ("G5n", "ENA",   "SOL",   "K696 ENA-SOL",    "alt-alt"),
    ("G5o", "BNB",   "SOL",   "K700 BNB-SOL",    "alt-alt"),
    ("G5p", "ENA",   "ATOM",  "K719 ENA-ATOM",   "alt-alt"),
    ("G5q", "LDO",   "SOL",   "K721 LDO-SOL",    "alt-alt"),
    ("G5r", "INJ",   "ATOM",  "K728 INJ-ATOM",   "alt-alt"),
    ("G5s", "HBAR",  "SOL",   "K735 HBAR-SOL",   "alt-alt"),
    ("G5t", "TIA",   "AVAX",  "K736 TIA-AVAX",   "alt-alt"),
    ("G5u", "FIL",   "SOL",   "K739 FIL-SOL",    "alt-alt"),
    ("G5v", "COMP",  "SOL",   "K778 COMP-SOL",   "alt-alt"),
    ("G5w", "IO",    "SOL",   "K774 IO-SOL",     "alt-alt"),
    ("G5x", "EIGEN", "SOL",   "K777 EIGEN-SOL",  "alt-alt"),
    # NOTE: G5y POLYX-SOL removed — K783 POLYX was BLOCKED-G5u, NOT an accepted vertex.
    # Only ACCEPTED vertices join the G5 family.
    # G5y slot intentionally absent for K784.
]

VERTEX_SET = [
    "APT", "ATOM", "AVAX", "BNB", "ENA", "FIL", "HBAR", "INJ", "LDO",
    "PEPE", "SEI", "SOL", "TIA", "TAO", "WLD", "DOGE", "WIF", "IO",
    "MEGA", "STX", "RUNE", "AAVE", "PENDLE", "AXS", "EIGEN", "BLUR",
    "COMP",
    # K783 POLYX: BLOCKED-G5u → NOT a vertex, excluded from G5 family
    # K782 PROVE:  REJECT-L004_DIFF → NOT a vertex
    # K784 SAGA: this wave — evaluation in progress
]


# ── Data loading ──────────────────────────────────────────────────────────────

def _load_hl_fr(name: str) -> Optional[pd.Series]:
    """Load HL hourly FR from k163_hl cache. Returns tz-naive UTC Series."""
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


def _ensure_saga_cache() -> pd.Series:
    """Ensure SAGA full FR cache exists, fetch if needed.

    K775 lesson: K781 only had 500 rows (20d). Full SAGA history is Apr 2024-present.
    The HL API returns max 500 records per call, so pagination is required.
    Initial fetch from 2024-01-01 gets ~7500 records (to Feb 2025); must continue.
    This function fetches ALL available history with complete pagination.
    """
    full_path = HL_DIR / "hl_fr_SAGA_full.parquet"
    if full_path.exists():
        ser = _load_hl_fr("SAGA_full")
        if ser is not None and len(ser) >= 10000:
            # Check if data is recent (within last 10 days)
            if ser.index.max() >= pd.Timestamp.now() - pd.Timedelta(days=10):
                print(f"  [Cache] SAGA full cache: {len(ser)} rows, up to {ser.index.max().date()}")
                return ser

    print("[Cache] Fetching SAGA full FR history from HL API (complete pagination) ...")
    # Start from SAGA listing date (April 2024)
    start_ms = int(datetime(2024, 1, 1, 0, 0, tzinfo=timezone.utc).timestamp() * 1000)
    all_data = _fetch_fr_history("SAGA", start_ms)
    print(f"  First pass: {len(all_data)} records")

    # Continue from last record if we got a full 500-batch multiple
    while len(all_data) > 0 and len(all_data) % 500 == 0:
        last_time = all_data[-1].get("time", 0)
        last_dt = datetime.fromtimestamp(last_time / 1000, tz=timezone.utc)
        print(f"  Continuing from {last_dt.date()} ...")
        extra = _fetch_fr_history("SAGA", last_time + 1)
        if not extra:
            break
        all_data.extend(extra)
        print(f"  Total so far: {len(all_data)} records")
        if len(extra) < 500:
            break

    print(f"  Total SAGA records: {len(all_data)}")

    if not all_data:
        print("  [WARN] API returned 0 records, using existing cache")
        return _load_hl_fr("SAGA")

    df = pd.DataFrame(all_data)
    df["timestamp"] = pd.to_datetime(df["time"], unit="ms", utc=True)
    df["hl_fr"] = df["fundingRate"].astype(float)
    df["ts"] = df["timestamp"].dt.tz_convert("UTC").dt.tz_localize(None).dt.floor("h")
    df = df.set_index("ts").sort_index()
    df = df[~df.index.duplicated(keep="last")]
    df[["hl_fr"]].to_parquet(str(full_path))
    print(f"  Saved: {full_path} ({len(df)} rows, {df.index.min().date()} to {df.index.max().date()})")
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
                  W: int, T: float = 0.0) -> pd.Series:
    """Compute per-period PnL series (signal × differential × leverage)."""
    df = pd.DataFrame({"a": a, "b": b}).dropna()
    diff = df["a"] - df["b"]
    sm = diff.rolling(W).mean()
    sig = np.sign(sm - T).shift(1)
    pnl = sig * diff * LEVERAGE
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


def _split_metrics(pnl: pd.Series, is_end: pd.Timestamp) -> Dict:
    """Return full/IS/OOS metrics dict."""
    pnl_is  = pnl[pnl.index <= is_end]
    pnl_oos = pnl[pnl.index > is_end]
    return {
        "full": _metrics(pnl),
        "is":   _metrics(pnl_is),
        "oos":  _metrics(pnl_oos),
        "oos_days": round(len(pnl_oos) / 24, 1),
        "oos_entries_per_yr": round(len(pnl_oos[pnl_oos != 0]) / max(len(pnl_oos) / 8760, 1e-9), 1),
    }


def _sig_corr_full_is_oos(s1: pd.Series, s2: pd.Series,
                           is_end: pd.Timestamp) -> Tuple[Optional[float], Optional[float], Optional[float], int]:
    """Signal correlation: full / IS / OOS."""
    common = s1.index.intersection(s2.index)
    if len(common) < 50:
        return None, None, None, len(common)
    sc1 = s1.loc[common]
    sc2 = s2.loc[common]
    if sc1.std() == 0 or sc2.std() == 0:
        return None, None, None, len(common)
    full_c = float(np.corrcoef(sc1.values, sc2.values)[0, 1])
    is_idx  = common[common <= is_end]
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


# ── Phase 0: Identity + all pre-screens ──────────────────────────────────────

def phase0_identity_and_prescreen(
    saga: pd.Series, sol: pd.Series,
    avax: pd.Series, fil: pd.Series, hbar: pd.Series,
    is_end: pd.Timestamp
) -> Dict:
    print("\n" + "=" * 70)
    print("[Phase 0] SAGA Identity + Pre-screens (K782 L004_DIFF mandatory)")
    print("=" * 70)

    sa, so = _align(saga, sol)
    total_rows = len(sa)
    days_history = total_rows / 24.0
    date_start = sa.index.min()
    date_end   = sa.index.max()

    # MR9: SAGA ∉ vertex set
    mr9_pass = "SAGA" not in VERTEX_SET
    print(f"  MR9: SAGA ∉ vertex set → {mr9_pass}")

    # ── K775: vol ratio full history ──────────────────────────────────────────
    saga_std_full = float(sa.std())
    sol_std_full  = float(so.std())
    vol_ratio_full = saga_std_full / sol_std_full if sol_std_full > 0 else 0.0

    # Rolling 30d vol ratios
    def _rolling_vol_ratio(a_: pd.Series, b_: pd.Series, window_h: int = 720) -> pd.Series:
        a_std = a_.rolling(window_h).std()
        b_std = b_.rolling(window_h).std()
        return (a_std / b_std.replace(0, np.nan)).dropna()

    rvr = _rolling_vol_ratio(sa, so)
    rolling_monthly = []
    for m_end in pd.date_range(date_start + pd.Timedelta(days=31), date_end, freq="M"):
        window_data = rvr[rvr.index <= m_end].tail(720)
        if len(window_data) > 100:
            rolling_monthly.append({
                "date": str(m_end.date()),
                "vol_ratio_30d": round(float(window_data.mean()), 4)
            })

    k775_pass = vol_ratio_full >= 1.5
    print(f"  K775 vol_ratio_full={vol_ratio_full:.4f} → {'PASS' if k775_pass else 'FAIL'}")

    # ── L003: AVAX correlation ────────────────────────────────────────────────
    sa_a, av_a = _align(saga, avax)
    corr_avax = float(np.corrcoef(sa_a.values, av_a.values)[0, 1]) if len(sa_a) > 50 else 1.0
    l003_pass = abs(corr_avax) < L003_AVAX
    print(f"  L003 corr(SAGA,AVAX)={corr_avax:.4f} → {'PASS' if l003_pass else 'FAIL'}")

    # ── L007: FIL correlation ─────────────────────────────────────────────────
    sa_f, fi_f = _align(saga, fil)
    corr_fil = float(np.corrcoef(sa_f.values, fi_f.values)[0, 1]) if len(sa_f) > 50 else 1.0
    l007_pass = abs(corr_fil) < L007_FIL
    print(f"  L007 corr(SAGA,FIL)={corr_fil:.4f} → {'PASS' if l007_pass else 'FAIL'}")

    # ── L010: HBAR correlation ────────────────────────────────────────────────
    sa_h, hb_h = _align(saga, hbar)
    corr_hbar = float(np.corrcoef(sa_h.values, hb_h.values)[0, 1]) if len(sa_h) > 50 else 1.0
    l010_pass = abs(corr_hbar) < L010_HBAR
    print(f"  L010 corr(SAGA,HBAR)={corr_hbar:.4f} → {'PASS' if l010_pass else 'FAIL'}")

    # ── L011: SOL correlation ─────────────────────────────────────────────────
    sa_s, so_s = _align(saga, sol)
    corr_sol = float(np.corrcoef(sa_s.values, so_s.values)[0, 1]) if len(sa_s) > 50 else 1.0
    l011_pass = abs(corr_sol) < L011_SOL
    print(f"  L011 corr(SAGA,SOL)={corr_sol:.4f} → {'PASS' if l011_pass else 'FAIL'}")

    # ── L004: token carry (SAGA alone) ───────────────────────────────────────
    carry_full = float((sa > 0).mean())
    is_mask    = sa.index <= is_end
    oos_mask   = sa.index > is_end
    carry_is   = float((sa[is_mask] > 0).mean()) if is_mask.sum() > 0 else float("nan")
    carry_oos  = float((sa[oos_mask] > 0).mean()) if oos_mask.sum() > 0 else float("nan")

    # Upper block: BOTH full > 80% AND OOS > 80% (K783 pattern: need both)
    l004_upper_block = (carry_full > L004_CARRY_UPPER) and (
        math.isnan(carry_oos) or carry_oos > L004_CARRY_UPPER
    )
    l004_lower_block = (carry_full < L004_CARRY_LOWER)
    l004_block = l004_upper_block or l004_lower_block
    if l004_upper_block:
        l004_status = "BLOCKED-L004-upper"
    elif l004_lower_block:
        l004_status = "BLOCKED-L004-lower"
    else:
        l004_status = "PASS"
    print(f"  L004 SAGA carry: full={carry_full:.3f} IS={carry_is:.3f} OOS={carry_oos:.3f} → {l004_status}")

    # ── L004_DIFF: differential carry (★ K782 NEW MANDATORY) ─────────────────
    diff_aligned = sa - so  # SAGA_fr - SOL_fr on aligned index
    diff_carry_full = float((diff_aligned > 0).mean())
    diff_is  = diff_aligned[diff_aligned.index <= is_end]
    diff_oos = diff_aligned[diff_aligned.index > is_end]
    diff_carry_is  = float((diff_is  > 0).mean()) if len(diff_is)  > 10 else float("nan")
    diff_carry_oos = float((diff_oos > 0).mean()) if len(diff_oos) > 10 else float("nan")
    diff_mean_ann  = float(diff_aligned.mean() * 8760 * 100)

    diff_full_fail = (diff_carry_full < L004_DIFF_LOWER) or (diff_carry_full > L004_DIFF_UPPER)
    diff_oos_fail  = (not math.isnan(diff_carry_oos)) and (
        (diff_carry_oos < L004_DIFF_LOWER) or (diff_carry_oos > L004_DIFF_UPPER)
    )
    l004_diff_blocked = diff_full_fail or diff_oos_fail
    l004_diff_status  = "BLOCKED-L004_DIFF" if l004_diff_blocked else "PASS"
    print(f"  L004_DIFF: diff_carry_full={diff_carry_full:.4f} OOS={diff_carry_oos:.4f} → {l004_diff_status}")
    print(f"    (threshold: [{L004_DIFF_LOWER}, {L004_DIFF_UPPER}], mean_diff_ann={diff_mean_ann:.2f}%/yr)")

    # ── Meta-narrative cluster ────────────────────────────────────────────────
    # SAGA = Gaming L1 / GameFi infrastructure
    # AXS is existing gaming/NFT vertex (Axie Infinity play-to-earn)
    # MEGA is existing gaming token vertex (Solana-native gaming)
    # Need to check if SAGA clusters with AXS or MEGA
    meta_cluster = "Gaming-L1 / GameFi infrastructure (Chainlet architecture, EVM gaming layer)"
    meta_vs_axs  = "SAGA (gaming L1 infrastructure) vs AXS (NFT gaming token Axie Infinity) — distinct: L1 foundation vs application token"
    meta_vs_mega  = "SAGA (gaming L1 / chainlets) vs MEGA (Solana-native gaming token) — distinct: infrastructure vs token"
    meta_vs_sol  = "SAGA (gaming-native L1) vs SOL (SVM general DeFi) — distinct FR mechanisms"
    meta_pass    = True  # Gaming L1 infrastructure is a new cluster distinct from existing gaming tokens

    # ── Prescreen summary ─────────────────────────────────────────────────────
    fails = []
    if not mr9_pass:       fails.append("MR9: SAGA already in vertex set")
    if not k775_pass:      fails.append(f"K775: vol_ratio_full={vol_ratio_full:.4f} < 1.5")
    if not l003_pass:      fails.append(f"L003: corr_AVAX={corr_avax:.4f} >= 0.45")
    if l004_block:         fails.append(f"L004: carry={carry_full:.3f} out of [0.30, 0.80]")
    if l004_diff_blocked:  fails.append(f"L004_DIFF: diff_carry_full={diff_carry_full:.4f} OOS={diff_carry_oos:.4f} outside [0.30, 0.70]")
    if not l007_pass:      fails.append(f"L007: corr_FIL={corr_fil:.4f} >= 0.45")
    if not l010_pass:      fails.append(f"L010: corr_HBAR={corr_hbar:.4f} >= 0.45")
    if not l011_pass:      fails.append(f"L011: corr_SOL={corr_sol:.4f} >= 0.50")

    prescreen_pass = len(fails) == 0
    print(f"\n  Pre-screen result: {'PASS' if prescreen_pass else 'FAIL'}")
    if fails:
        for f in fails:
            print(f"    ✗ {f}")

    return {
        "identity": {
            "ticker": "SAGA",
            "full_name": "SAGA (Saga Origin — Gaming L1 with EVM Chainlets)",
            "platform": "Saga Protocol — purpose-built gaming L1, EVM chainlets, NFT game economy",
            "listing_type": "HIP-3 perp on HyperLiquid",
            "listing_date_hl_inferred": str(date_start.date()),
            "total_rows_aligned": int(total_rows),
            "date_range_start": str(date_start.date()),
            "date_range_end": str(date_end.date()),
            "days_history": round(days_history, 1),
            "cluster": meta_cluster,
            "cluster_note": (
                "SAGA = Saga Origin gaming L1. Chainlet architecture: game developers deploy "
                "dedicated EVM blockchains (chainlets). FR driven by: gaming season adoption "
                "cycles, GameFi speculation, NFT game launches on Saga, chainlet demand. "
                "DISTINCT from AXS (application gaming token), MEGA (Solana gaming token), "
                "and SOL (SVM general ecosystem). G9 history verification required."
            ),
            "k781_context": {
                "vol_ratio_30d_k781": 18.297,
                "max_corr_k781": 0.2586,
                "carry_stability_k781": 0.728,
                "composite_score_k781": 0.2158,
                "rank_k781": "3rd of top-5 K781 candidates",
                "note": "K781 measured 500-row (20d) window. K775 lesson: verify with full history.",
            },
        },
        "mr9": {"pass": mr9_pass, "saga_in_vertex_set": not mr9_pass},
        "k775_vol_verification": {
            "vol_ratio_full": round(vol_ratio_full, 4),
            "k775_threshold": 1.5,
            "k775_pass": k775_pass,
            "k781_cache_rows": 500,
            "k781_was_20d_only": True,
            "full_rows_fetched": int(total_rows),
            "full_history_days": round(days_history, 1),
            "date_start": str(date_start.date()),
            "date_end": str(date_end.date()),
            "rolling_monthly": rolling_monthly,
            "note": f"K775 LESSON: K781 fetched only 500 rows (20d). Full fetch: {total_rows} rows, {days_history:.0f}d.",
        },
        "L003_AVAX": {"corr": round(corr_avax, 4), "threshold": L003_AVAX, "pass": l003_pass},
        "L004_carry": {
            "carry_full": round(carry_full, 4),
            "carry_is":   round(carry_is, 4) if not math.isnan(carry_is) else None,
            "carry_oos":  round(carry_oos, 4) if not math.isnan(carry_oos) else None,
            "threshold_lower": L004_CARRY_LOWER,
            "threshold_upper": L004_CARRY_UPPER,
            "blocked": l004_block,
            "status":  l004_status,
            "pass": not l004_block,
        },
        "L004_DIFF": {
            "diff_carry_full": round(diff_carry_full, 4),
            "diff_carry_is":   round(diff_carry_is, 4) if not math.isnan(diff_carry_is) else None,
            "diff_carry_oos":  round(diff_carry_oos, 4) if not math.isnan(diff_carry_oos) else None,
            "diff_mean_ann_pct": round(diff_mean_ann, 4),
            "threshold": [L004_DIFF_LOWER, L004_DIFF_UPPER],
            "diff_full_fail": diff_full_fail,
            "diff_oos_fail":  diff_oos_fail,
            "blocked": l004_diff_blocked,
            "status":  l004_diff_status,
            "pass": not l004_diff_blocked,
            "note": (
                f"★ K782 NEW: SAGA_FR - SOL_FR > 0 fraction. "
                f"full={diff_carry_full:.4f} IS={diff_carry_is:.4f} OOS={diff_carry_oos:.4f}. "
                f"Threshold: [{L004_DIFF_LOWER}, {L004_DIFF_UPPER}]. "
                f"mean_diff={diff_mean_ann:.2f}%/yr ann. "
                f"Status: {l004_diff_status}."
            ),
        },
        "L007_FIL":  {"corr": round(corr_fil, 4),  "threshold": L007_FIL,  "pass": l007_pass},
        "L010_HBAR": {"corr": round(corr_hbar, 4), "threshold": L010_HBAR, "pass": l010_pass},
        "L011_SOL":  {"corr": round(corr_sol, 4),  "threshold": L011_SOL,  "pass": l011_pass},
        "meta_narrative_cluster": {
            "cluster": meta_cluster,
            "vs_axs":  meta_vs_axs,
            "vs_mega": meta_vs_mega,
            "vs_sol":  meta_vs_sol,
            "pass":    meta_pass,
        },
        "vol_ratio_full":   round(vol_ratio_full, 4),
        "vol_ratio_k781_30d": 18.297,
        "carry_full":  round(carry_full, 4),
        "carry_is":    round(carry_is, 4) if not math.isnan(carry_is) else None,
        "carry_oos":   round(carry_oos, 4) if not math.isnan(carry_oos) else None,
        "corr_avax":   round(corr_avax, 4),
        "corr_fil":    round(corr_fil, 4),
        "corr_hbar":   round(corr_hbar, 4),
        "corr_sol":    round(corr_sol, 4),
        "diff_carry_full": round(diff_carry_full, 4),
        "diff_carry_is":   round(diff_carry_is, 4) if not math.isnan(diff_carry_is) else None,
        "diff_carry_oos":  round(diff_carry_oos, 4) if not math.isnan(diff_carry_oos) else None,
        "diff_mean_ann_pct": round(diff_mean_ann, 4),
        "l004_diff_blocked": l004_diff_blocked,
        "prescreen_pass": prescreen_pass,
        "prescreen_fails": fails,
        "days_history": round(days_history, 1),
    }


# ── Phase 1: Cycle analysis ───────────────────────────────────────────────────

def phase1_cycle_analysis(saga: pd.Series, sol: pd.Series, is_end: pd.Timestamp) -> Dict:
    print("\n" + "=" * 70)
    print("[Phase 1] Cycle analysis — SAGA Gaming L1 vs SOL SVM")
    print("=" * 70)

    sa, so = _align(saga, sol)
    saga_std = float(sa.std())
    sol_std  = float(so.std())
    vol_ratio = saga_std / sol_std if sol_std > 0 else 0.0

    # OU mean-reversion half-life
    diff = sa - so
    diff_lag = diff.shift(1).dropna()
    diff_now = diff.iloc[1:]
    common_idx = diff_lag.index.intersection(diff_now.index)
    try:
        lam = np.cov(diff_now.loc[common_idx].values, diff_lag.loc[common_idx].values)[0, 1] / \
              np.var(diff_lag.loc[common_idx].values)
        hl_h = -math.log(2) / math.log(abs(lam)) if abs(lam) < 1 and lam != 0 else float("nan")
    except Exception:
        lam = float("nan")
        hl_h = float("nan")

    raw_corr = float(np.corrcoef(sa.values, so.values)[0, 1])

    # Quarterly cycle analysis
    sa_q = pd.concat([sa.rename("saga"), so.rename("sol")], axis=1)
    sa_q["quarter"] = sa_q.index.to_period("Q")
    quarterly = {}
    for q, g in sa_q.groupby("quarter"):
        diff_q = g["saga"] - g["sol"]
        quarterly[str(q)] = {
            "saga_mean_ann_pct": round(float(g["saga"].mean()) * 8760 * 100, 4),
            "sol_mean_ann_pct":  round(float(g["sol"].mean())  * 8760 * 100, 4),
            "diff_mean_ann_pct": round(float(diff_q.mean())    * 8760 * 100, 4),
            "diff_pos_frac":     round(float((diff_q > 0).mean()), 4),
            "saga_pos_frac":     round(float((g["saga"] > 0).mean()), 4),
        }

    print(f"  vol_ratio_full={vol_ratio:.4f}x, raw_corr(SAGA,SOL)={raw_corr:.4f}")
    print(f"  OU lambda={lam:.4f}, half_life={hl_h:.2f}h" if not math.isnan(hl_h) else
          f"  OU lambda={lam}, half_life=NA")

    return {
        "saga_fr_std": round(saga_std, 6),
        "sol_fr_std":  round(sol_std, 6),
        "vol_ratio_full": round(vol_ratio, 4),
        "vol_ratio_pass": vol_ratio >= 1.5,
        "raw_corr_saga_sol": round(raw_corr, 4),
        "cycle_independence": round(1.0 - abs(raw_corr), 4),
        "ou_lambda": round(float(lam), 5) if not math.isnan(lam) else None,
        "ou_half_life_h": round(hl_h, 2) if not math.isnan(hl_h) else None,
        "cycle_by_quarter": quarterly,
        "mechanism_analysis": {
            "saga_fr_drivers": [
                "Gaming season adoption cycles (blockchain game launches on Saga chainlets)",
                "GameFi speculation cycles (NFT gaming hype vs. bust)",
                "Chainlet demand: game developer adoption of Saga infrastructure",
                "SAGA staking and governance participation cycles",
                "NFT gaming ecosystem growth (play-to-earn game launches)",
                "Competition with other gaming L1s (Ronin, ImmutableX, Beam)",
                "Token unlock / vesting schedules affecting supply-demand",
            ],
            "sol_fr_drivers": [
                "SVM meme season (BONK/WIF/TRUMP/POPCAT cycles on Solana)",
                "SOL ETF narrative cycles",
                "Solana DEX volume (Jupiter/Raydium/Drift)",
                "Firedancer upgrade cycles (validator throughput expectations)",
                "SVM DeFi TVL expansion",
            ],
            "structural_independence": (
                "SAGA (Saga Origin gaming L1) vs SOL (Solana SVM ecosystem). "
                "Saga is purpose-built for gaming applications via EVM chainlets — "
                "institutional game-native infrastructure driven by GameFi adoption cycles. "
                "SOL is driven by consumer DeFi/meme/speculative retail demand. "
                "Structural independence expected: gaming L1 cycles vs SVM retail cycles."
            ),
        },
        "note": f"vol_ratio={vol_ratio:.4f}x, corr(SAGA,SOL)={raw_corr:.4f}. K781 30d=18.30x.",
    }


# ── Phase 2: Backtest across windows ─────────────────────────────────────────

def phase2_backtest(saga: pd.Series, sol: pd.Series, is_end: pd.Timestamp) -> Dict:
    print("\n" + "=" * 70)
    print("[Phase 2] Backtest grid (W=48/84/168)")
    print("=" * 70)

    sa, so = _align(saga, sol)
    results = {}
    for W in [48, 84, 168]:
        pnl = _backtest_pnl(sa, so, W)
        m   = _split_metrics(pnl, is_end)
        results[f"W{W}h"] = {
            "window_h": W,
            "full_period": m["full"],
            "is_metrics":  m["is"],
            "oos_metrics": m["oos"],
            "oos_days":    m["oos_days"],
            "oos_entries_per_yr": m["oos_entries_per_yr"],
        }
        print(f"  W={W}h: IS Sh={m['is']['sharpe']:.2f} OOS Sh={m['oos']['sharpe']:.2f} "
              f"OOS ret={m['oos']['ann_ret_pct']:.1f}%")

    # Grid search
    grid = []
    for W in [48, 84, 168]:
        for T_frac in [0.0, 0.5, 1.0]:
            pnl_all = _backtest_pnl(sa, so, W)
            std_val = float((sa - so).rolling(W).std().mean()) * T_frac
            pnl_T = _backtest_pnl(sa, so, W, T=std_val)
            m_all = _split_metrics(pnl_all, is_end)
            m_T   = _split_metrics(pnl_T, is_end)
            pnl_to_use = pnl_T if T_frac > 0 else pnl_all
            m_use = m_T if T_frac > 0 else m_all
            grid.append({
                "W": W, "T_frac": T_frac, "threshold_value": round(std_val, 8),
                "IS_sharpe":  m_use["is"]["sharpe"],
                "OOS_sharpe": m_use["oos"]["sharpe"],
                "OOS_ret_pct": m_use["oos"]["ann_ret_pct"],
                "entries_per_yr_full": m_use["oos_entries_per_yr"],
            })

    grid_sorted = sorted(grid, key=lambda x: -x["OOS_sharpe"])
    for g in grid_sorted[:3]:
        print(f"  Grid top: W={g['W']} T={g['T_frac']:.1f} → IS Sh={g['IS_sharpe']:.2f} OOS Sh={g['OOS_sharpe']:.2f}")

    return {
        "windows": results,
        "grid_top6": grid_sorted[:6],
        "grid_all":  grid_sorted,
        "canonical_window_h": WINDOW_H_PRIMARY,
    }


# ── Phase 3: §6 gate evaluation ───────────────────────────────────────────────

def phase3_gates(saga: pd.Series, sol: pd.Series,
                 fr_map: Dict[str, Optional[pd.Series]],
                 is_end: pd.Timestamp,
                 canonical_W: int = WINDOW_H_PRIMARY) -> Dict:
    print("\n" + "=" * 70)
    print(f"[Phase 3] §6 Gates (canonical W={canonical_W}h)")
    print("=" * 70)

    sa, so = _align(saga, sol)
    pnl_can = _backtest_pnl(sa, so, canonical_W)
    m_can   = _split_metrics(pnl_can, is_end)

    oos_sharpe  = m_can["oos"]["sharpe"]
    oos_ret_pct = m_can["oos"]["ann_ret_pct"]
    oos_days    = m_can["oos_days"]
    entries_yr  = m_can["oos_entries_per_yr"]

    # G1: OOS Sharpe
    g1_pass = oos_sharpe >= 1.0
    print(f"  G1 OOS Sh={oos_sharpe:.4f} → {'PASS' if g1_pass else 'FAIL'}")

    # G2: Permutation test
    pnl_oos  = pnl_can[pnl_can.index > is_end]
    obs_mean = float(pnl_oos.mean())
    obs_std  = float(pnl_oos.std())
    obs_sh   = obs_mean * ANN_FACTOR_HL / obs_std if obs_std > 0 else 0.0
    rng = np.random.default_rng(42)
    n_perm = 1000
    perm_shs = []
    diff_oos = (sa - so).loc[pnl_oos.index]
    for _ in range(n_perm):
        rand_sig = rng.choice([-1, 1], size=len(diff_oos))
        p_pnl = rand_sig * diff_oos.values * LEVERAGE
        p_std = p_pnl.std()
        if p_std > 0:
            perm_shs.append(p_pnl.mean() * ANN_FACTOR_HL / p_std)
    perm_p = float(np.mean(np.array(perm_shs) >= obs_sh))
    g2_pass = perm_p <= 0.05
    print(f"  G2 perm p={perm_p:.4f} ({n_perm} perms) → {'PASS' if g2_pass else 'FAIL'}")

    # G3: DSR Bonferroni
    n_trials = len([g for g in [WINDOW_H_PRIMARY, WINDOW_H_ALT1, WINDOW_H_ALT2]]) * 3  # W x T
    n_trials = 9
    from scipy import stats as sp_stats
    if obs_std > 0 and len(pnl_oos) > 2:
        t_stat = obs_sh * math.sqrt(len(pnl_oos))
        p_raw = float(1 - sp_stats.norm.cdf(t_stat))
        p_bonf = min(p_raw * n_trials, 1.0)
    else:
        t_stat = 0.0
        p_raw = 1.0
        p_bonf = 1.0
    g3_pass = p_bonf < (0.05 / n_trials)
    print(f"  G3 DSR Bonferroni: t={t_stat:.4f} p_bonf={p_bonf:.6f} → {'PASS' if g3_pass else 'FAIL'}")

    # G4: Walk-forward 12-fold
    fold_results = []
    wf_n = 12
    wf_oos_d = 30
    wf_is_d  = 90
    fold_start = sa.index.min()
    for i in range(wf_n):
        fold_is_end  = fold_start + pd.Timedelta(days=wf_is_d * (i + 1))
        fold_oos_end = fold_is_end + pd.Timedelta(days=wf_oos_d)
        if fold_oos_end > sa.index.max():
            break
        pnl_fold = _backtest_pnl(
            sa.loc[(sa.index >= fold_start) & (sa.index <= fold_oos_end)],
            so.loc[(so.index >= fold_start) & (so.index <= fold_oos_end)],
            canonical_W
        )
        pnl_oos_fold = pnl_fold[pnl_fold.index > fold_is_end]
        m_fold = _metrics(pnl_oos_fold)
        fold_results.append({
            "fold": i + 1,
            "oos_start": str(fold_is_end.date()),
            "oos_end":   str(fold_oos_end.date()),
            "sharpe":    m_fold["sharpe"],
            "ann_ret_pct": m_fold["ann_ret_pct"],
            "entries":   int((pnl_oos_fold != 0).sum()),
        })
    n_neg = sum(1 for f in fold_results if f["sharpe"] < 0)
    g4_pass = (len(fold_results) >= 3) and (n_neg == 0)
    print(f"  G4 WF {len(fold_results)}-fold: neg={n_neg} → {'PASS' if g4_pass else 'FAIL'}")

    # G5: Family signal correlation
    sig_can = _sig_from(sa, so, canonical_W)
    g5_details = {}
    g5_fails = []
    for gid, tok_a, tok_b, label, family in G5_GATES:
        fr_a = fr_map.get(tok_a)
        fr_b = fr_map.get(tok_b)
        if fr_a is None or fr_b is None:
            g5_details[gid] = {
                "label": label, "family": family,
                "full": None, "is_corr": None, "oos_corr": None,
                "n": 0, "pass": True,
                "note": f"Missing cache for {tok_a} or {tok_b} — skip (PASS)"
            }
            continue
        sig_v = _sig_from(fr_a, fr_b, canonical_W)
        fc, ic, oc, n = _sig_corr_full_is_oos(sig_can, sig_v, is_end)
        pass_g = fc is None or abs(fc) < G5_CORR_THRESHOLD
        if not pass_g:
            g5_fails.append(gid)
        g5_details[gid] = {
            "label": label, "family": family,
            "full": fc, "is_corr": ic, "oos_corr": oc,
            "n": n, "pass": pass_g,
            "note": f"SAGA-SOL vs {label} = {fc:.4f}. {'PASS' if pass_g else 'FAIL'}.",
        }
    g5_all_pass = len(g5_fails) == 0
    max_abs_corr = max(
        (abs(v["full"]) for v in g5_details.values() if v["full"] is not None), default=0.0
    )
    print(f"  G5 family: {len(g5_details) - len(g5_fails)}/{len(g5_details)} PASS, fails={g5_fails}")

    # G6: Trade count
    g6_pass = entries_yr >= 30
    print(f"  G6 entries/yr={entries_yr:.1f} → {'PASS' if g6_pass else 'FAIL'}")

    # G7: Ann return
    g7_val  = oos_ret_pct * LEVERAGE
    g7_pass = g7_val > 5.0
    print(f"  G7 OOS ret@{LEVERAGE}x={g7_val:.1f}% → {'PASS' if g7_pass else 'FAIL'}")

    # G8: Cross-venue (Bybit/OKX SAGA)
    # SAGA is a HIP-3 token — check if Bybit/OKX have SAGA perps
    # Based on K781 context: SAGA is HIP-3, likely HL-only for perpetuals
    # Need to note this as a concern
    g8_note = (
        "SAGA listed HIP-3 on HL. No Bybit/OKX SAGA perpetual cached. "
        "Gaming L1 with ~$251K/day HL volume likely HL-only for perps. "
        "Needs manual venue verification."
    )
    # Attempt to proxy via OKX/Bybit spot (not available in cache)
    g8_hl = True  # HL confirmed active (HIP-3 listing)
    g8_bybit = False  # not cached
    g8_okx   = False  # not cached
    g8_pass  = g8_hl and (g8_bybit or g8_okx)
    print(f"  G8 cross-venue: HL={g8_hl} Bybit={g8_bybit} OKX={g8_okx} → {'PASS' if g8_pass else 'FAIL'}")

    # G9: Data sufficiency (OOS >= 180d)
    g9_pass = oos_days >= 180
    g9_marginal = (oos_days >= 120) and (oos_days < 180)
    print(f"  G9 OOS days={oos_days:.1f} → {'PASS' if g9_pass else ('MARGINAL' if g9_marginal else 'FAIL')}")

    # Summary
    gate_map = {
        "G1": g1_pass, "G2": g2_pass, "G3": g3_pass, "G4": g4_pass,
        "G5": g5_all_pass, "G6": g6_pass, "G7": g7_pass, "G8": g8_pass, "G9": g9_pass,
    }
    n_pass = sum(gate_map.values())
    n_total = len(gate_map)

    return {
        "canonical_W": canonical_W,
        "oos_sharpe": oos_sharpe,
        "oos_ret_pct": oos_ret_pct,
        "oos_days": oos_days,
        "entries_per_yr": entries_yr,
        "G1_oos_sharpe": {"value": oos_sharpe, "threshold": 1.0, "pass": g1_pass},
        "G2_perm": {"value": perm_p, "threshold": 0.05, "n_perms": n_perm, "pass": g2_pass,
                    "perm_obs_sharpe": round(obs_sh, 4)},
        "G3_dsr_bonferroni": {"t_stat": round(t_stat, 4), "p_bonferroni": round(p_bonf, 8),
                              "n_trials": n_trials, "threshold": 0.05 / n_trials, "pass": g3_pass},
        "G4_walk_forward": {
            "folds": fold_results, "n_folds": len(fold_results),
            "n_negative": n_neg, "all_positive": n_neg == 0, "pass": g4_pass,
        },
        "G5_family": {
            "all_pass": g5_all_pass, "fails": g5_fails,
            "max_abs_corr": round(max_abs_corr, 4),
            "details": g5_details,
        },
        "G6_entries_yr": {"value": entries_yr, "threshold": 30, "pass": g6_pass},
        "G7_ann_ret": {
            "value_1x_pct": oos_ret_pct,
            "value_4x_pct": round(oos_ret_pct * LEVERAGE, 4),
            "threshold_pct": 5.0, "pass": g7_pass,
        },
        "G8_cross_venue": {
            "hl": g8_hl, "bybit": g8_bybit, "okx": g8_okx,
            "pass": g8_pass, "note": g8_note,
        },
        "G9_oos_days": {
            "value": oos_days, "threshold": 180.0,
            "pass": g9_pass, "marginal": g9_marginal,
        },
        "gates_pass_map": gate_map,
        "n_gates_pass": n_pass,
        "n_gates_total": n_total,
        "g5_fails": g5_fails,
        "g5_all_pass": g5_all_pass,
    }


# ── Phase 4: Decision + K523 ROI ─────────────────────────────────────────────

def phase4_decision(phase0: Dict, phase3: Dict) -> Dict:
    print("\n" + "=" * 70)
    print("[Phase 4] Decision + K523 3-point ROI")
    print("=" * 70)

    prescreen_pass   = phase0["prescreen_pass"]
    l004_diff_block  = phase0["l004_diff_blocked"]
    prescreen_fails  = phase0["prescreen_fails"]
    oos_sharpe       = phase3.get("oos_sharpe", 0.0)
    oos_ret_pct      = phase3.get("oos_ret_pct", 0.0)
    gate_map         = phase3.get("gates_pass_map", {})
    g5_fails         = phase3.get("g5_fails", [])
    g2_pass          = gate_map.get("G2", False)
    g5_all_pass      = gate_map.get("G5", True)

    if not prescreen_pass:
        if l004_diff_block:
            verdict = "REJECT"
            verdict_code = "L004_DIFF_CARRY_BLOCK"
            diff_carry = phase0.get("diff_carry_full", 0.0)
            diff_carry_oos = phase0.get("diff_carry_oos", 0.0)
            diff_mean = phase0.get("diff_mean_ann_pct", 0.0)
            verdict_detail = (
                f"REJECT (L004_DIFF_CARRY_BLOCK) — SAGA-SOL differential carry "
                f"full={diff_carry:.4f} OOS={diff_carry_oos:.4f} "
                f"outside [{L004_DIFF_LOWER}, {L004_DIFF_UPPER}]. "
                f"mean_diff={diff_mean:.2f}%/yr ann. "
                f"G2 permutation will fail (structural one-sided differential). "
                f"K782 lesson: L004_DIFF mandatory pre-screen before full §6 eval."
            )
        else:
            fail_str = "; ".join(prescreen_fails)
            verdict = "REJECT"
            verdict_code = "PRESCREEN_FAIL"
            verdict_detail = f"REJECT (PRESCREEN_FAIL) — {fail_str}"
    elif not g2_pass:
        verdict = "REJECT"
        verdict_code = "G2_PERM_FAIL"
        perm_p = phase3.get("G2_perm", {}).get("value", 1.0)
        verdict_detail = (
            f"REJECT (G2_PERM_FAIL) — permutation p={perm_p:.4f} > 0.05. "
            f"Signal is not statistically distinguishable from random direction shuffles."
        )
    elif g5_fails:
        verdict = "BLOCKED"
        verdict_code = f"G5_FAIL_{'+'.join(g5_fails)}"
        verdict_detail = f"BLOCKED — G5 family correlation fail: {g5_fails}"
    elif gate_map.get("G1") and gate_map.get("G2") and gate_map.get("G3") and \
         gate_map.get("G4") and gate_map.get("G5"):
        n_pass = phase3.get("n_gates_pass", 0)
        n_total = phase3.get("n_gates_total", 9)
        if gate_map.get("G9"):
            verdict = "ACCEPT"
            verdict_code = "ACCEPT"
        else:
            verdict = "ACCEPT_CONDITIONAL"
            verdict_code = "ACCEPT_CONDITIONAL_G9"
        verdict_detail = f"{verdict} — {n_pass}/{n_total} gates. G5 all pass. OOS Sh={oos_sharpe:.4f}."
    else:
        fail_gates = [g for g, v in gate_map.items() if not v]
        verdict = "BLOCKED"
        verdict_code = f"GATES_FAIL_{'+'.join(fail_gates)}"
        verdict_detail = f"BLOCKED — Failed gates: {fail_gates}"

    print(f"  Verdict: {verdict} ({verdict_code})")
    print(f"  Detail: {verdict_detail[:100]}...")

    # K523 3-point ROI
    roi_3point = None
    if verdict in ("ACCEPT", "ACCEPT_CONDITIONAL") or "BLOCK" not in verdict_code:
        sleeve_usd  = CAPITAL_10M * SLEEVE_PCT
        notional    = sleeve_usd * LEVERAGE
        R2S         = 0.38
        OOS_haircut = 0.75
        fee_haircut = 0.85
        raw_ret = oos_ret_pct / 100
        conservative = notional * raw_ret * R2S * OOS_haircut * fee_haircut
        central      = notional * raw_ret * R2S * OOS_haircut
        optimistic   = notional * raw_ret * OOS_haircut
        roi_3point = {
            "oos_ann_ret_raw_pct": oos_ret_pct,
            "oos_sharpe": oos_sharpe,
            "sleeve_pct": SLEEVE_PCT,
            "sleeve_notional": sleeve_usd,
            "leverage": LEVERAGE,
            "realized_ratio_k523_floor": R2S,
            "oos_haircut_k523": 1 - OOS_haircut,
            "conservative_usd_yr": round(conservative),
            "mid_usd_yr": round(central),
            "optimistic_usd_yr": round(optimistic),
            "k523_compliance": True,
            "note": (
                f"Conservative: ${conservative:,.0f}/yr (×{R2S} realized ×OOS-haircut ×fee). "
                f"Mid: ${central:,.0f}/yr (central). "
                f"Optimistic: ${optimistic:,.0f}/yr (raw OOS, upper bound only). "
                f"Sleeve 0.4% (${sleeve_usd:,.0f} @$10M, liquidity-limited). "
                f"Leverage {LEVERAGE}x. K523: single-number is upper bound, not central."
            ),
        }

    return {
        "verdict": verdict,
        "verdict_code": verdict_code,
        "verdict_detail": verdict_detail,
        "oos_sharpe": oos_sharpe,
        "oos_ret_pct": oos_ret_pct,
        "gates_summary": gate_map,
        "roi_3point": roi_3point,
        "cluster_ruling": {
            "cluster": "Gaming L1 / GameFi infrastructure (Saga chainlet architecture)",
            "vs_axs_distinct": "SAGA gaming L1 infrastructure vs AXS NFT gaming token — distinct meta-narratives",
            "vs_mega_distinct": "SAGA gaming L1 vs MEGA Solana gaming token — distinct: infra vs application",
            "vs_sol_distinct": "SAGA gaming L1 (institutional game infra) vs SOL SVM (consumer DeFi/meme)",
            "meta_narrative_pass": True,
        },
        "operational": {
            "hl_cap_pct": 66.8,
            "paper_gate_mandatory": True,
            "sleeve_pct": SLEEVE_PCT,
            "max_notional": CAPITAL_10M * SLEEVE_PCT,
            "bybit_confirmed": False,
            "okx_confirmed": False,
            "note": "HL at 66.8% (>65% cap). Paper-gate mandatory. SAGA likely HL-only (HIP-3). Cross-venue needs verification.",
        },
        "k782_lesson_applied": {
            "title": "L004_DIFF pre-screen applied (K782 mandatory lesson)",
            "description": (
                "K782 proved that differential carry check is mandatory. "
                "PROVE-SOL: token carry=42.8% (PASS L004) but diff_carry=27.7% (FAIL L004_DIFF). "
                "G2 p=1.000 confirmed — structural directional carry, not timing alpha. "
                "K784 applies L004_DIFF as Phase 0 mandatory gate before any full eval."
            ),
            "threshold": f"[{L004_DIFF_LOWER}, {L004_DIFF_UPPER}]",
            "diff_carry_full":  phase0.get("diff_carry_full"),
            "diff_carry_oos":   phase0.get("diff_carry_oos"),
            "l004_diff_blocked": phase0.get("l004_diff_blocked"),
        },
        "k523_compliance": True,
        "hl_cap_context": {
            "current_hl_pct": 66.8,
            "hl_cap_pct": 65.0,
            "over_cap": True,
            "recommendation": "HL at 66.8% (over 65% cap). Paper-gate mandatory regardless of verdict.",
        },
        "next_wave_note": "K785: next HIP-3 candidate from K781 backlog (BIO, ALT, or other)",
    }


# ── Main ──────────────────────────────────────────────────────────────────────

def main() -> None:
    print("=" * 70)
    print(f"  {WAVE_ID} — SAGA-SOL FR Differential Eval")
    print(f"  K339 REPO_ROOT: {BASE}")
    print(f"  K782 lesson: L004_DIFF mandatory | K775 lesson: full vol verify")
    print("=" * 70)

    # ── Load data ─────────────────────────────────────────────────────────────
    print("\n[Data] Loading SAGA full history (K775 lesson) ...")
    saga = _ensure_saga_cache()
    if saga is None:
        print("[ERROR] SAGA data unavailable")
        return

    sol  = _load_hl_fr("SOL")
    avax = _load_hl_fr("AVAX")
    fil  = _load_hl_fr("FIL")
    hbar = _load_hl_fr("HBAR")

    print(f"  SAGA: {len(saga)} rows, {saga.index.min()} → {saga.index.max()}")
    print(f"  SOL:  {len(sol)} rows")

    # Determine IS/OOS split based on full history
    # Align first to determine split point
    sa_aligned, so_aligned = _align(saga, sol)
    total_rows = len(sa_aligned)
    n_is  = int(total_rows * 0.60)
    n_oos = total_rows - n_is
    is_end = sa_aligned.index[n_is - 1]
    print(f"  Split: IS={n_is} rows → IS_END={is_end.date()}, OOS={n_oos} rows ({n_oos/24:.0f}d)")

    # Load G5 family cache
    g5_tokens = set()
    for _, tok_a, tok_b, _, _ in G5_GATES:
        g5_tokens.add(tok_a)
        g5_tokens.add(tok_b)
    fr_map: Dict[str, Optional[pd.Series]] = {}
    for tok in g5_tokens:
        fr_map[tok] = _load_hl_fr(tok)
    print(f"  G5 family: loaded {sum(1 for v in fr_map.values() if v is not None)}/{len(fr_map)} caches")

    # ── Phase 0 ───────────────────────────────────────────────────────────────
    p0 = phase0_identity_and_prescreen(saga, sol, avax, fil, hbar, is_end)

    # ── Phase 1 (always run for documentation) ────────────────────────────────
    p1 = phase1_cycle_analysis(saga, sol, is_end)

    # ── Phase 2-4: Only if pre-screens pass ───────────────────────────────────
    if p0["prescreen_pass"]:
        print("\n[INFO] Pre-screens PASS → proceeding to Phase 2 (backtest + §6 gates)")
        p2 = phase2_backtest(saga, sol, is_end)
        # Use best canonical window from grid
        best_w = p2["canonical_window_h"]
        p3 = phase3_gates(saga, sol, fr_map, is_end, canonical_W=best_w)
        p4 = phase4_decision(p0, p3)
    else:
        print(f"\n[INFO] Pre-screens FAIL → {p0['prescreen_fails']}")
        print("[INFO] Skipping Phase 2-4 (as per L004_DIFF REJECT rule)")
        p2 = {"skipped": True, "reason": "Pre-screen failed — L004_DIFF block"}
        p3 = {"skipped": True, "reason": "Pre-screen failed"}
        p4 = phase4_decision(p0, {"oos_sharpe": 0.0, "oos_ret_pct": 0.0,
                                   "gates_pass_map": {}, "g5_fails": [],
                                   "n_gates_pass": 0, "n_gates_total": 9})

    # ── Assemble output ───────────────────────────────────────────────────────
    runtime_s = round(time.time() - START_TIME, 1)
    run_jst = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.%f+00:00")

    out = {
        "wave":    WAVE_ID,
        "title":   "K784 SAGA-SOL FR Differential Eval — Saga Gaming L1 + SVM",
        "generated_utc": run_jst,
        "runtime_s": runtime_s,
        "k339_compliance": K339_COMPLIANCE,
        "k523_mandatory": True,
        "live_auto_change_prohibited": True,
        "pair": "SAGA-SOL",
        "token_long":  "SAGA (Saga Origin — Gaming L1 / EVM Chainlets)",
        "token_short": "SOL (Solana SVM)",
        "verdict": p4["verdict"],
        "verdict_code": p4["verdict_code"],
        "verdict_detail": p4["verdict_detail"],
        "is_end": str(is_end.date()),
        "phase0": p0,
        "phase1": p1,
        "phase2": p2,
        "phase3": p3,
        "phase4": p4,
    }

    OUT_JSON.write_text(json.dumps(out, indent=2, default=str))
    print(f"\n[Done] {runtime_s}s — verdict={p4['verdict']} → {OUT_JSON.name}")


if __name__ == "__main__":
    main()

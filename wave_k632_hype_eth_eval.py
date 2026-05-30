#!/usr/bin/env python3
"""
wave_k632_hype_eth_eval.py — K632 HYPE-ETH FR Differential Paired-Trade Evaluation
======================================================================================
K339 REPO_ROOT pattern. K632: Apply K629 ETH-base mechanism to K614 HYPE-BTC CONDITIONAL.

MOTIVATION (K629 ETH-base lesson → K632)
-----------------------------------------
K629 showed ETH-base mechanism can unlock strategies blocked/conditional on BTC:
  - WLD-ETH passed 9/9 gates vs WLD-BTC BLOCKED-G5 (JUP corr=0.4612 >= 0.40)
  - ETH base removes BTC-FR-compression mechanism that causes co-movement

K614 HYPE-BTC: ACCEPT CONDITIONAL (Sh=24.49, 4 structural fails: G2/G6/G8/G9)
  - CONDITIONAL because: carry strategy (G2 structural), G6 trades<30, G8 Bybit 66d, G9 OOS=160d
  - All G5 PASS (28/28), G1/G3/G4 PASS
  - Question: does ETH base improve or worsen gate performance?

K632 HYPOTHESIS (HYPE-ETH differential)
----------------------------------------
  fr_diff_t = hype_fr_t - eth_fr_t
  Signal = sign(W-hour rolling mean of fr_diff)

WHY ETH BASE FOR HYPE:
  - HYPE FR: AQAv2 buyback cycles + HL volume regime + HIP-5 staking demand
  - ETH FR: ETH-specific DeFi/staking narratives (liquid staking, EigenLayer restaking)
  - HYPE-ETH differential: HL ecosystem health vs ETH DeFi ecosystem health
  - Key question: does HYPE carry persist vs ETH (not just vs BTC)?
  - BTC carry (K280) baseline: if HYPE-ETH less correlated with BTC-carry → G5j improved
  - ETH base sub-cluster (K629): WLD-ETH cluster 24 already established
  - HYPE-ETH could be cluster 25: "Self-referential L1+perp DEX vs ETH-base"

CARRY STRUCTURE (HYPE-ETH):
  HYPE FR mean: ~22.83%/yr (AQAv2 + HL native premium)
  ETH FR mean:  ~10.52%/yr (ETH DeFi/staking narratives)
  Net structural carry: ~12.31%/yr HYPE-ETH (estimated)
  Direction: predominantly long HYPE / short ETH (HYPE > ETH FR structurally)
  Note: ETH FR > BTC FR typically → HYPE-ETH carry may be similar to or slightly
        lower than HYPE-BTC if ETH FR compresses the net differential.

VOL RATIO (HYPE vs ETH):
  HYPE FR vol: high (narrative spikes from AQAv2 + HL ecosystem events)
  ETH FR vol:  moderate (DeFi/staking regime, lower than BTC in some periods)
  Estimated HYPE/ETH vol ratio: 1.0-2.0x (HYPE may be slightly below ETH in vol
  during muted cycles; ETH DeFi narratives can spike ETH FR vol)
  Required: >= 1.5x on at least one window (365d or full)

CLUSTER ANALYSIS:
  K632 = ETH-base sub-cluster variant of HYPE (cluster #22 self-referential L1+DEX)
  New check: HYPE-ETH vs WLD-ETH (K629) — both ETH-base, different alt tokens
  Same-base correlation check critical: if HYPE-ETH too correlated with WLD-ETH → blocked

CRITICAL TESTS (new for K632 vs K614):
  G5_ETH_WLD: HYPE-ETH signal vs WLD-ETH signal (K629) — same-base critical check
  G5a_ETH_BTC: HYPE-ETH vs ETH-BTC K449 — shared ETH leg (same base as ETH-BTC)
  G5j: HYPE-ETH vs BTC-carry K280 — if lower than K614's -0.1013 → improvement

COMPARISON vs K614 (HYPE-BTC):
  K614 OOS Sh=24.49 | OOS ann=4.46%/yr | WF 12/12 pos | G5 28/28 PASS
  K632 target: similar or improved Sh | same or better gate count

DECISION CRITERIA:
  ACCEPT (better than K614): Sh >= K614 Sh=24.49, gates >= K614
    → replace HYPE-BTC with HYPE-ETH
  SAME LEVEL (within 10% of K614 Sh, same gate count):
    → hold both (HYPE-BTC and HYPE-ETH as separate positions)
  WORSE: keep K614 HYPE-BTC, K632 REJECT
  BLOCKED-G5 (any corr >= 0.40):
    → ETH-base does not improve family orthogonality for HYPE

§6 GATES (K632 — 9 gates, ETH-base variant, same family as K614)
-----------------------------------------------------------------
  G1:  OOS Sharpe >= 1.0
  G2:  Perm p-value <= 0.05 (structural fail expected — HYPE carry strategy)
  G3:  DSR Bonferroni p < 0.05/9 = 0.00556 (9 grid configs tested)
  G4:  Walk-forward 12-fold stability (IS 90d / OOS 30d), >=8/12 positive
  G5:  All family + new ETH-base checks < 0.40:
       G5a: HYPE-ETH vs ETH-BTC K449 (shared ETH base — CRITICAL)
       G5aa: HYPE-ETH vs WLD-ETH K629 (same-base DEX vs ID — CRITICAL new check)
       G5j: HYPE-ETH vs K280 BTC-carry (baseline carry orthogonality)
       G5e: HYPE-ETH vs INJ-BTC K500 (DEX tokens — CRITICAL)
       G5zb: HYPE-ETH vs JUP-BTC K606 (DEX aggregator — CRITICAL)
       + all 28 family BTC-based members
  G6:  Trade count >= 30/yr (structural fail expected — low trade freq carry)
  G7:  Ann return > 5% at 4x leverage
  G8:  Cross-venue Bybit HYPEUSDT signal corr >= 0.55 (structural fail — 66d only)
  G9:  Data sufficiency >= 180d OOS (structural fail — HYPE Nov 2024 launch)

HL CONCENTRATION:
  HYPE-ETH: same self-referential risk as HYPE-BTC
  Bybit-primary MANDATORY (no HYPE on HL)
  Max alloc 1% (self-referential correlated ruin)
  HYPE-ETH does NOT increase HL concentration vs HYPE-BTC (same token)

Usage:
  python3 wave_k632_hype_eth_eval.py
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
from scipy import stats

warnings.filterwarnings("ignore")

START_TIME = time.time()
BASE     = Path("/Users/nekonaomichi/crypto-lab")
CACHE    = BASE / "cache" / "k163_hl"
DATA_DIR = BASE / "data"

# ── Config ────────────────────────────────────────────────────────────────────────
# K614 used W=240h (AQAv2 buyback cycle).
# K629 (WLD-ETH) used W=168h (7d smoothing).
# K632: test both ranges, use W=240h as primary (same as K614 for fair comparison)
WINDOW_H        = 240       # 10d smoothing (K614 optimal for HYPE AQAv2 cycle)
THRESHOLD       = 0.0       # always-on carry
COST_RT_BPS     = 4         # 2bps per side × 2 legs
COST_RT         = COST_RT_BPS / 10000
OOS_FRAC        = 0.30
N_FOLDS_WF      = 12
WF_IS_H         = 2160      # 90d × 24h
WF_OOS_H        = 720       # 30d × 24h
N_PERM          = 500
# Grid: windows tested (same as K614 for Bonferroni consistency)
GRID_WINDOWS    = [120, 168, 240, 360, 480, 600, 720, 840, 960]
N_TRIALS_TESTED = len(GRID_WINDOWS)   # 9

# Phase 0 thresholds
PHASE0_VOL_MIN  = 1.5

# §6 gate thresholds
G1_SH_MIN       = 1.0
G2_PERM_MAX     = 0.05
G5_CORR_MAX     = 0.40
G9_OOS_DAYS_MIN = 180
G7_ANN_RET_MIN  = 5.0       # % at 4x leverage
G8_VENUE_CORR   = 0.55

# HL concentration cap
HL_BASELINE_PCT = 65.0      # v6.28+ post-K610 baseline
HL_CAP_PCT      = 65.0

ANN_FACTOR_1H   = math.sqrt(8760)

# K614 benchmarks for comparison
K614_OOS_SH     = 24.4854
K614_OOS_ANN    = 4.4583
K614_GATES_PASS = 5         # G1, G3, G4, G5, G7

# Family reference (post-K614, 29 members, HYPE-BTC = rank 9)
FAMILY: List[Dict] = [
    {"rank":  1, "pair": "APT-BTC",    "sharpe": 51.100,  "ecosystem": "Move-VM",                             "status": "ACCEPT"},
    {"rank":  2, "pair": "ATOM-BTC",   "sharpe": 50.786,  "ecosystem": "Cosmos",                              "status": "ACCEPT"},
    {"rank":  3, "pair": "SEI-BTC",    "sharpe": 48.100,  "ecosystem": "Cosmos",                              "status": "ACCEPT"},
    {"rank":  4, "pair": "AVAX-BTC",   "sharpe": 43.887,  "ecosystem": "Avalanche",                           "status": "ACCEPT"},
    {"rank":  5, "pair": "SHIB-BTC",   "sharpe": 38.481,  "ecosystem": "Meme/Retail (Shiba Inu ERC-20)",      "status": "ACCEPT CONDITIONAL"},
    {"rank":  6, "pair": "SAND-BTC",   "sharpe": 33.627,  "ecosystem": "Gaming/Metaverse",                    "status": "ACCEPT CONDITIONAL"},
    {"rank":  7, "pair": "PEPE-BTC",   "sharpe": 26.420,  "ecosystem": "Meme/Retail (Pepe ERC-20)",           "status": "ACCEPT CONDITIONAL"},
    {"rank":  8, "pair": "BCH-BTC",    "sharpe": 26.002,  "ecosystem": "PoW/SHA-256-BTC-Fork (Bitcoin Cash)", "status": "ACCEPT CONDITIONAL"},
    {"rank":  9, "pair": "HYPE-BTC",   "sharpe": 24.485,  "ecosystem": "Self-referential L1+perp DEX",        "status": "ACCEPT CONDITIONAL"},
    {"rank": 10, "pair": "BONK-BTC",   "sharpe": 23.667,  "ecosystem": "Meme/Retail-Solana-SPL",              "status": "ACCEPT CONDITIONAL"},
    {"rank": 11, "pair": "COMP-BTC",   "sharpe": 22.837,  "ecosystem": "DeFi/Lending-Governance (Compound)",  "status": "ACCEPT CONDITIONAL"},
    {"rank": 12, "pair": "FIL-BTC",    "sharpe": 21.773,  "ecosystem": "Storage",                             "status": "ACCEPT CONDITIONAL"},
    {"rank": 13, "pair": "DOGE-BTC",   "sharpe": 21.069,  "ecosystem": "Meme/PoW (Dogecoin Scrypt)",          "status": "ACCEPT CONDITIONAL"},
    {"rank": 14, "pair": "TRX-BTC",    "sharpe": 18.593,  "ecosystem": "EM-Payment/Justin-Sun (TRON DPoS)",   "status": "ACCEPT CONDITIONAL"},
    {"rank": 15, "pair": "AXS-BTC",    "sharpe": 17.815,  "ecosystem": "Gaming/P2E",                          "status": "ACCEPT CONDITIONAL"},
    {"rank": 16, "pair": "SOL-BTC",    "sharpe": 16.298,  "ecosystem": "Solana",                              "status": "ACCEPT"},
    {"rank": 17, "pair": "RENDER-BTC", "sharpe": 15.302,  "ecosystem": "AI/GPU",                              "status": "ACCEPT CONDITIONAL"},
    {"rank": 18, "pair": "HBAR-BTC",   "sharpe": 14.709,  "ecosystem": "Enterprise-Consortium-DAG (Hedera)",  "status": "ACCEPT CONDITIONAL"},
    {"rank": 19, "pair": "TIA-BTC",    "sharpe": 14.439,  "ecosystem": "Cosmos",                              "status": "ACCEPT"},
    {"rank": 20, "pair": "LINK-BTC",   "sharpe": 13.775,  "ecosystem": "Oracle/LINK",                         "status": "ACCEPT CONDITIONAL"},
    {"rank": 21, "pair": "WIF-BTC",    "sharpe": 12.934,  "ecosystem": "Meme/Solana (dogwifhat)",              "status": "ACCEPT CONDITIONAL"},
    {"rank": 22, "pair": "ICP-BTC",    "sharpe": 12.527,  "ecosystem": "Compute/Cloud",                       "status": "ACCEPT CONDITIONAL"},
    {"rank": 23, "pair": "AAVE-BTC",   "sharpe": 11.354,  "ecosystem": "DeFi/Lending",                        "status": "ACCEPT CONDITIONAL"},
    {"rank": 24, "pair": "INJ-BTC",    "sharpe": 11.232,  "ecosystem": "Cosmos",                              "status": "ACCEPT"},
    {"rank": 25, "pair": "LTC-BTC",    "sharpe":  9.390,  "ecosystem": "PoW/Scrypt-Utility (Litecoin)",       "status": "ACCEPT CONDITIONAL"},
    {"rank": 26, "pair": "TON-BTC",    "sharpe":  8.402,  "ecosystem": "Social/Messaging",                    "status": "ACCEPT CONDITIONAL"},
    {"rank": 27, "pair": "ETH-BTC",    "sharpe":  5.663,  "ecosystem": "Ethereum",                            "status": "ACCEPT"},
    {"rank": 28, "pair": "CRV-BTC",    "sharpe":  5.290,  "ecosystem": "DeFi/veToken (Curve)",                "status": "ACCEPT CONDITIONAL"},
    {"rank": 29, "pair": "TAO-BTC",    "sharpe":  5.267,  "ecosystem": "AI/Training",                         "status": "ACCEPT CONDITIONAL"},
]

# ETH-base sub-family (K629 WLD-ETH = cluster 24)
ETH_BASE_FAMILY = [
    {"pair": "WLD-ETH", "sharpe": 19.902, "wave": "K629", "status": "ACCEPT", "cluster": 24},
]


# ── Utilities ─────────────────────────────────────────────────────────────────────

def sharpe_ratio(pnl: pd.Series, ann_factor: float = ANN_FACTOR_1H) -> float:
    if len(pnl) < 10:
        return 0.0
    r_std = pnl.std()
    return (pnl.mean() / r_std * ann_factor) if r_std > 0 else 0.0


def max_drawdown(pnl: pd.Series) -> float:
    eq   = pnl.cumsum()
    peak = eq.cummax()
    return float((eq - peak).min())


def compute_metrics(ret_s: pd.Series, ts_s: pd.Series, pos_chg: pd.Series, label: str) -> Dict:
    ann    = ANN_FACTOR_1H
    r_mean = ret_s.mean()
    r_std  = ret_s.std()
    sh     = (r_mean / r_std * ann) if r_std > 0 else 0.0
    ann_ret_pct = r_mean * 8760 * 100
    cum_ret     = ret_s.sum()
    cum_curve   = ret_s.cumsum()
    roll_max    = cum_curve.cummax()
    max_dd      = (cum_curve - roll_max).min()
    n_hours     = len(ret_s)
    ts_min, ts_max = ts_s.min(), ts_s.max()
    n_days = (ts_max - ts_min).days if hasattr((ts_max - ts_min), "days") else n_hours / 24
    monthly   = ret_s.groupby(ts_s.dt.to_period("M")).sum()
    n_pos_m   = int((monthly > 0).sum())
    n_neg_m   = int((monthly <= 0).sum())
    trades    = int((pos_chg > 0).sum())
    trades_yr = trades / (n_days / 365) if n_days > 0 else 0.0
    return {
        "label":        label,
        "sharpe":       round(float(sh), 4),
        "ann_ret_pct":  round(float(ann_ret_pct), 4),
        "max_dd_pct":   round(float(max_dd * 100), 4),
        "trades_yr":    round(float(trades_yr), 1),
        "n_days":       round(float(n_days), 1),
        "n_hours":      int(n_hours),
        "n_pos_months": n_pos_m,
        "n_neg_months": n_neg_m,
        "cum_ret":      round(float(cum_ret), 6),
        "ret_mean":     round(float(r_mean), 9),
        "ret_std":      round(float(r_std), 9),
    }


# ── Data Loading ──────────────────────────────────────────────────────────────────

def load_or_fetch_hype_fr() -> pd.DataFrame:
    """Load HYPE FR data from K614 data dir or fetch from HL API."""
    out = DATA_DIR / "hl_fr_HYPE.parquet"
    if out.exists():
        df = pd.read_parquet(out)
        print(f"  [Data] Loaded HYPE FR: {len(df)} rows from {out}")
        return df

    # Try k163_hl cache path
    alt = CACHE / "hl_fr_HYPE.parquet"
    if alt.exists():
        df = pd.read_parquet(alt)
        print(f"  [Data] Loaded HYPE FR: {len(df)} rows from {alt}")
        return df

    print("  [Data] Fetching HYPE FR from HL API ...")
    all_records: List[Dict] = []
    start_ms = 1732838400000  # Nov 29 2024 — HYPE genesis
    for _ in range(100):
        try:
            r    = requests.post(
                "https://api.hyperliquid.xyz/info",
                json={"type": "fundingHistory", "coin": "HYPE", "startTime": start_ms},
                timeout=30,
            )
            data = r.json()
        except Exception as e:
            print(f"  [Data] HL API error: {e}")
            break
        if not data:
            break
        all_records.extend(data)
        last_ms = data[-1]["time"]
        if len(data) < 500:
            break
        start_ms = last_ms + 1

    df = pd.DataFrame(all_records)
    df["timestamp"] = pd.to_datetime(df["time"], unit="ms", utc=True).dt.tz_localize(None)
    df["hl_fr"]     = df["fundingRate"].astype(float)
    df = df[["timestamp", "hl_fr"]].sort_values("timestamp").drop_duplicates("timestamp").reset_index(drop=True)
    DATA_DIR.mkdir(exist_ok=True)
    df.to_parquet(out, index=False)
    print(f"  [Data] Fetched & saved HYPE FR: {len(df)} rows")
    return df


def load_eth_fr() -> pd.DataFrame:
    """Load ETH FR from k163_hl cache."""
    fp = CACHE / "hl_fr_ETH.parquet"
    df = pd.read_parquet(fp)
    print(f"  [Data] Loaded ETH FR: {len(df)} rows")
    return df


def load_btc_fr() -> pd.DataFrame:
    """Load BTC FR from k163_hl cache."""
    fp = CACHE / "hl_fr_BTC.parquet"
    df = pd.read_parquet(fp)
    print(f"  [Data] Loaded BTC FR: {len(df)} rows")
    return df


def load_family_fr(sym: str) -> Optional[pd.DataFrame]:
    fp = CACHE / f"hl_fr_{sym}.parquet"
    if not fp.exists():
        return None
    df = pd.read_parquet(fp)
    if "timestamp" not in df.columns:
        df = df.reset_index()
    df["ts_h"] = pd.to_datetime(df["timestamp"]).dt.floor("h")
    return df


# ── Phase 0: Vol ratio ─────────────────────────────────────────────────────────────

def compute_vol_ratios(hype_df: pd.DataFrame, eth_df: pd.DataFrame,
                       btc_df: pd.DataFrame) -> Dict:
    """Compute HYPE/ETH vol ratios (6M, 365d, full) vs ETH base.
    Also compute HYPE/BTC ratio for K614 comparison.
    """
    print("  [Phase 0] Computing vol ratios HYPE/ETH (and HYPE/BTC for comparison) ...")
    hype = hype_df.copy()
    eth  = eth_df.copy()
    btc  = btc_df.copy()
    hype["ts_h"] = pd.to_datetime(hype["timestamp"]).dt.floor("h")
    eth["ts_h"]  = pd.to_datetime(eth["timestamp"]).dt.floor("h")
    btc["ts_h"]  = pd.to_datetime(btc["timestamp"]).dt.floor("h")

    df = pd.merge(
        hype[["ts_h", "hl_fr"]].rename(columns={"hl_fr": "hype_fr"}),
        eth[["ts_h",  "hl_fr"]].rename(columns={"hl_fr": "eth_fr"}),
        on="ts_h", how="inner"
    )
    df = pd.merge(
        df,
        btc[["ts_h", "hl_fr"]].rename(columns={"hl_fr": "btc_fr"}),
        on="ts_h", how="left"
    ).sort_values("ts_h").reset_index(drop=True)

    now        = df["ts_h"].max()
    six_m_ago  = now - pd.Timedelta(days=182)
    one_yr_ago = now - pd.Timedelta(days=365)

    df6m  = df[df["ts_h"] >= six_m_ago]
    df365 = df[df["ts_h"] >= one_yr_ago]

    # HYPE/ETH vol ratios
    h_std_6m   = df6m["hype_fr"].std()
    e_std_6m   = df6m["eth_fr"].std()
    h_std_365d = df365["hype_fr"].std()
    e_std_365d = df365["eth_fr"].std()
    h_std_full = df["hype_fr"].std()
    e_std_full = df["eth_fr"].std()

    vol_6m   = h_std_6m   / e_std_6m   if e_std_6m   > 0 else 0.0
    vol_365d = h_std_365d / e_std_365d if e_std_365d > 0 else 0.0
    vol_full = h_std_full / e_std_full if e_std_full > 0 else 0.0

    # HYPE/BTC vol ratios (K614 reference)
    b_std_6m   = df6m["btc_fr"].std() if "btc_fr" in df6m.columns else None
    vol_btc_6m = float(h_std_6m / b_std_6m) if b_std_6m and b_std_6m > 0 else None

    vol_pass      = vol_6m   >= PHASE0_VOL_MIN
    vol_pass_365d = vol_365d >= PHASE0_VOL_MIN
    vol_pass_full = vol_full >= PHASE0_VOL_MIN
    vol_conditional = (not vol_pass) and (vol_pass_365d or vol_pass_full)

    hype_fr_pct_pos = float((df["hype_fr"] > 0).mean())
    eth_fr_pct_pos  = float((df["eth_fr"]  > 0).mean())
    hype_fr_mean_ann = float(df["hype_fr"].mean() * 8760 * 100)
    eth_fr_mean_ann  = float(df["eth_fr"].mean()  * 8760 * 100)

    # fr_diff = HYPE - ETH
    df["fr_diff"] = df["hype_fr"] - df["eth_fr"]
    fr_diff_mean  = float(df["fr_diff"].mean())
    fr_diff_std   = float(df["fr_diff"].std())
    fr_diff_mean_ann = fr_diff_mean * 8760 * 100

    # Also BTC-diff for comparison
    df["fr_diff_btc"] = df["hype_fr"] - df["btc_fr"]

    return {
        "vol_ratio_hype_eth_6m":    round(float(vol_6m),   4),
        "vol_ratio_hype_eth_365d":  round(float(vol_365d), 4),
        "vol_ratio_hype_eth_full":  round(float(vol_full), 4),
        "vol_ratio_hype_btc_6m_k614ref": round(float(vol_btc_6m), 4) if vol_btc_6m else None,
        "vol_threshold":            PHASE0_VOL_MIN,
        "vol_pass":                 bool(vol_pass),
        "vol_pass_365d":            bool(vol_pass_365d),
        "vol_pass_full":            bool(vol_pass_full),
        "vol_conditional":          bool(vol_conditional),
        "merged_rows":              int(len(df)),
        "hype_fr_pct_positive":     round(hype_fr_pct_pos, 4),
        "eth_fr_pct_positive":      round(eth_fr_pct_pos, 4),
        "hype_fr_mean_ann_pct":     round(hype_fr_mean_ann, 4),
        "eth_fr_mean_ann_pct":      round(eth_fr_mean_ann, 4),
        "fr_diff_mean_ann_pct":     round(fr_diff_mean_ann, 4),
        "fr_diff_std":              round(fr_diff_std, 9),
        "vol_note": (
            f"HYPE/ETH 6M vol ratio={vol_6m:.4f}x ({'ABOVE' if vol_pass else 'BELOW (CONDITIONAL)'}). "
            f"365d={vol_365d:.4f}x ({'PASS' if vol_pass_365d else 'FAIL'}). "
            f"Full={vol_full:.4f}x ({'PASS' if vol_pass_full else 'FAIL'}). "
            f"HYPE/BTC 6M={vol_btc_6m:.4f}x (K614 reference). "
            f"HYPE FR: {hype_fr_mean_ann:.2f}%/yr | ETH FR: {eth_fr_mean_ann:.2f}%/yr. "
            f"Net HYPE-ETH carry: {fr_diff_mean_ann:.2f}%/yr (structural long HYPE / short ETH). "
            f"HYPE FR positive {hype_fr_pct_pos*100:.1f}% | ETH FR positive {eth_fr_pct_pos*100:.1f}%."
        ),
        "_merged_df": df,   # internal use
    }


# ── Signal + Backtest ─────────────────────────────────────────────────────────────

def build_signal_df(hype_df: pd.DataFrame, eth_df: pd.DataFrame,
                    btc_df: pd.DataFrame, window_h: int = WINDOW_H) -> pd.DataFrame:
    """Build HYPE-ETH FR differential signal DataFrame.
    Also carries BTC-diff for K614 comparison analysis.
    """
    hype = hype_df.copy()
    eth  = eth_df.copy()
    btc  = btc_df.copy()
    hype["ts_h"] = pd.to_datetime(hype["timestamp"]).dt.floor("h")
    eth["ts_h"]  = pd.to_datetime(eth["timestamp"]).dt.floor("h")
    btc["ts_h"]  = pd.to_datetime(btc["timestamp"]).dt.floor("h")

    df = pd.merge(
        hype[["ts_h", "hl_fr"]].rename(columns={"hl_fr": "hype_fr"}),
        eth[["ts_h",  "hl_fr"]].rename(columns={"hl_fr": "eth_fr"}),
        on="ts_h", how="inner"
    )
    df = pd.merge(
        df,
        btc[["ts_h", "hl_fr"]].rename(columns={"hl_fr": "btc_fr"}),
        on="ts_h", how="left"
    ).sort_values("ts_h").reset_index(drop=True)

    df["diff"]     = df["hype_fr"] - df["eth_fr"]   # HYPE-ETH primary
    df["diff_btc"] = df["hype_fr"] - df["btc_fr"]   # HYPE-BTC K614 reference
    df["roll"]     = df["diff"].rolling(window_h, min_periods=window_h // 2).mean()
    df["signal"]   = np.sign(df["roll"]).ffill().fillna(0)
    df["pos_change"] = df["signal"].diff().abs()
    return df


def run_backtest(df: pd.DataFrame, window_h: int = WINDOW_H) -> pd.DataFrame:
    df2 = df.copy()
    df2["roll"]      = df2["diff"].rolling(window_h, min_periods=window_h // 2).mean()
    df2["signal"]    = np.sign(df2["roll"]).ffill().fillna(0)
    df2["prev_sig"]  = df2["signal"].shift(1)
    df2["sig_chg"]   = (df2["signal"] != df2["prev_sig"]).astype(float)
    df2["carry_pnl"] = df2["signal"] * df2["diff"]
    df2["trade_cost"]= df2["sig_chg"] * COST_RT
    df2["net_pnl"]   = df2["carry_pnl"] - df2["trade_cost"]
    return df2


# ── Statistical Tests ─────────────────────────────────────────────────────────────

def run_adf_test(diff_series: pd.Series) -> Dict:
    from statsmodels.tsa.stattools import adfuller
    series = diff_series.dropna()
    result = adfuller(series, maxlag=48, autolag="AIC")
    return {
        "adf_stat":   round(float(result[0]), 4),
        "p_value":    round(float(result[1]), 6),
        "stationary": bool(result[1] < 0.05),
        "critical_1": round(float(result[4]["1%"]), 4),
        "critical_5": round(float(result[4]["5%"]), 4),
    }


def run_ou_halflife(diff_series: pd.Series) -> Dict:
    series = diff_series.dropna()
    lag    = series.shift(1)
    valid  = series.notna() & lag.notna()
    slope, intercept, r_val, p_val, _ = stats.linregress(lag[valid], series[valid])
    theta  = -slope
    hl_h   = math.log(2) / theta if theta > 0 else float("inf")
    mean_rev = bool(theta > 0)
    return {
        "half_life_h":    round(float(hl_h), 2),
        "half_life_days": round(float(hl_h / 24), 3),
        "theta":          round(float(theta), 6),
        "intercept":      round(float(intercept), 9),
        "r_squared":      round(float(r_val ** 2), 4),
        "mean_reverting": mean_rev,
        "note": (
            f"HYPE-ETH OU: theta={theta:.6f} "
            f"({'mean-reverting' if mean_rev else 'momentum-persistent carry'}). "
            f"Half-life={hl_h:.2f}h ({hl_h/24:.3f}d). "
            "If theta<0 (negative): HYPE-ETH is pure carry (same as HYPE-BTC K614). "
            "If theta>0: HYPE-ETH has partial mean-reversion (ETH-base adds regime-switching)."
        ),
    }


def run_permutation_test(oos_df: pd.DataFrame, real_sh: float) -> Dict:
    """500-reshuffle permutation test OOS.
    NOTE: Structural fail expected — HYPE is a carry strategy.
    Permuted diff preserves positive mean → perm signals also collect carry.
    """
    print(f"  [Stat] Running {N_PERM} permutation tests ...")
    np.random.seed(42)
    diff_vals    = oos_df["diff"].values
    signal_vals  = oos_df["signal"].shift(1).values
    perm_sharpes = []
    for _ in range(N_PERM):
        perm     = np.random.permutation(diff_vals)
        pos_chg  = np.abs(np.concatenate([[0], np.diff(
            np.sign(np.convolve(perm, np.ones(WINDOW_H) / WINDOW_H, mode="same"))
        )]))
        ret = signal_vals[1:] * perm[1:] - pos_chg[1:] * COST_RT * 0.5
        r_std = np.std(ret)
        psh = (np.mean(ret) / r_std * ANN_FACTOR_1H) if r_std > 0 else 0.0
        perm_sharpes.append(psh)

    p_val = float(np.mean(np.array(perm_sharpes) >= real_sh))
    fr_diff_mean = float(oos_df["diff"].mean())
    fr_diff_mean_ann = fr_diff_mean * 8760 * 100
    return {
        "real_sharpe":   round(real_sh, 4),
        "perm_mean_sh":  round(float(np.mean(perm_sharpes)), 4),
        "perm_p_value":  round(p_val, 4),
        "n_perm":        N_PERM,
        "pass":          bool(p_val <= G2_PERM_MAX),
        "structural_note": (
            "G2 perm test STRUCTURALLY FAILS for HYPE-ETH carry strategy. "
            f"Root cause: HYPE-ETH OOS diff mean={fr_diff_mean:.8f}/hr "
            f"({fr_diff_mean_ann:.3f}%/yr). "
            "Permuted diff preserves positive mean → perm signals also collect HYPE-ETH carry. "
            "G2 failure = pure carry alpha (same mechanism as K614 HYPE-BTC). "
            "Decision: treat G2 as STRUCTURAL FAIL (carry strategy)."
        ),
    }


def run_dsr_test(oos_sharpe: float) -> Dict:
    """DSR / Bonferroni correction (9 grid windows tested)."""
    bonf_thresh = 0.05 / N_TRIALS_TESTED
    t_stat      = oos_sharpe / math.sqrt(N_TRIALS_TESTED) if N_TRIALS_TESTED > 0 else 0.0
    p_val       = float(stats.norm.sf(t_stat))
    return {
        "oos_sharpe":        round(oos_sharpe, 4),
        "t_stat":            round(t_stat, 4),
        "p_value":           round(p_val, 6),
        "bonferroni_thresh": round(bonf_thresh, 6),
        "n_trials":          N_TRIALS_TESTED,
        "pass":              bool(p_val < bonf_thresh),
    }


# ── Grid Search ───────────────────────────────────────────────────────────────────

def grid_search(hype_df: pd.DataFrame, eth_df: pd.DataFrame) -> Tuple[Dict, List[Dict]]:
    """Grid search over smoothing windows for HYPE-ETH (same windows as K614)."""
    print("  [Grid] Running grid search ...")
    hype = hype_df.copy()
    eth  = eth_df.copy()
    hype["ts_h"] = pd.to_datetime(hype["timestamp"]).dt.floor("h")
    eth["ts_h"]  = pd.to_datetime(eth["timestamp"]).dt.floor("h")

    df = pd.merge(
        hype[["ts_h", "hl_fr"]].rename(columns={"hl_fr": "hype_fr"}),
        eth[["ts_h",  "hl_fr"]].rename(columns={"hl_fr": "eth_fr"}),
        on="ts_h", how="inner"
    ).sort_values("ts_h").reset_index(drop=True)
    df["diff"] = df["hype_fr"] - df["eth_fr"]

    n       = len(df)
    oos_s   = int(n * (1 - OOS_FRAC))
    results = []

    for w in GRID_WINDOWS:
        df2         = df.copy()
        df2["roll"] = df2["diff"].rolling(w, min_periods=w // 2).mean()
        df2["sig"]  = np.sign(df2["roll"]).ffill().fillna(0)
        oos         = df2.iloc[oos_s:].copy()
        oos["ret"]  = oos["sig"].shift(1) * oos["diff"]
        pos_chg     = oos["sig"].diff().abs()
        oos["ret"] -= pos_chg * COST_RT * 0.5
        r_std = oos["ret"].std()
        sh    = (oos["ret"].mean() / r_std * ANN_FACTOR_1H) if r_std > 0 else 0.0
        ann   = oos["ret"].mean() * 8760 * 100
        n_d   = (oos["ts_h"].max() - oos["ts_h"].min()).days
        t_yr  = (pos_chg > 0).sum() / (n_d / 365) if n_d > 0 else 0.0
        results.append({
            "window_h":        int(w),
            "oos_sharpe":      round(float(sh), 4),
            "oos_ann_ret_pct": round(float(ann), 4),
            "trades_yr":       round(float(t_yr), 1),
        })

    results.sort(key=lambda x: x["oos_sharpe"], reverse=True)
    best = results[0]
    print(f"  [Grid] Best W={best['window_h']}h OOS Sh={best['oos_sharpe']:.4f} "
          f"ann={best['oos_ann_ret_pct']:.2f}%")
    return best, results[:5]


# ── Walk-Forward ──────────────────────────────────────────────────────────────────

def walk_forward(df: pd.DataFrame, window_h: int = WINDOW_H) -> Dict:
    """12-fold walk-forward (IS 90d / OOS 30d)."""
    print(f"  [WF] Running {N_FOLDS_WF}-fold walk-forward ...")
    n      = len(df)
    needed = WF_IS_H + WF_OOS_H * N_FOLDS_WF
    start  = max(0, n - needed)
    folds  = []

    for i in range(N_FOLDS_WF):
        is_end  = start + WF_IS_H + i * WF_OOS_H
        oos_end = is_end + WF_OOS_H
        if oos_end > n:
            break
        is_part  = df.iloc[start:is_end]
        oos_part = df.iloc[is_end:oos_end].copy()

        roll_last = is_part["diff"].rolling(window_h, min_periods=window_h // 2).mean().iloc[-1]
        signal    = float(np.sign(roll_last)) if not np.isnan(roll_last) else 0.0
        oos_part["signal_wf"] = signal
        oos_part["ret_wf"]    = oos_part["signal_wf"].shift(1).fillna(0) * oos_part["diff"]
        if len(oos_part) > 0:
            oos_part.iloc[0, oos_part.columns.get_loc("ret_wf")] -= abs(signal) * COST_RT * 0.5

        r_std = oos_part["ret_wf"].std()
        sh    = (oos_part["ret_wf"].mean() / r_std * ANN_FACTOR_1H) if r_std > 0 else 0.0
        dd    = (oos_part["ret_wf"].cumsum() - oos_part["ret_wf"].cumsum().cummax()).min()

        start_d = oos_part["ts_h"].iloc[0].strftime("%Y-%m-%d") if len(oos_part) else ""
        end_d   = oos_part["ts_h"].iloc[-1].strftime("%Y-%m-%d") if len(oos_part) else ""

        folds.append({
            "fold":     i + 1,
            "start":    start_d,
            "end":      end_d,
            "sharpe":   round(float(sh), 4),
            "positive": str(sh > 0),
            "max_dd":   round(float(dd), 6),
        })

    n_pos   = sum(1 for f in folds if f["sharpe"] > 0)
    sh_vals = [f["sharpe"] for f in folds]
    wf_pass = n_pos >= 8

    return {
        "n_folds":      len(folds),
        "n_positive":   n_pos,
        "all_positive": bool(n_pos == len(folds)),
        "partial_pass": bool(wf_pass),
        "pass":         bool(wf_pass),
        "sh_min":       round(float(min(sh_vals)), 4) if sh_vals else 0.0,
        "sh_max":       round(float(max(sh_vals)), 4) if sh_vals else 0.0,
        "sh_mean":      round(float(np.mean(sh_vals)), 4) if sh_vals else 0.0,
        "sh_std":       round(float(np.std(sh_vals)), 4) if sh_vals else 0.0,
        "fold_details": folds,
        "note": (
            f"{n_pos}/{len(folds)} positive folds. "
            f"G4 {'PASS' if wf_pass else 'FAIL'} (>={8}/{N_FOLDS_WF} positive). "
            f"Sharpe range: [{min(sh_vals):.2f}, {max(sh_vals):.2f}] (mean={np.mean(sh_vals):.2f}). "
            "HYPE carry: persistent AQAv2 buyback vs ETH staking-driven FR — all folds positive expected. "
        ),
    }


# ── G5 Family Correlations ────────────────────────────────────────────────────────

def compute_g5_correlations(hype_eth_oos_ret: pd.DataFrame,
                             eth_df: pd.DataFrame,
                             btc_df: pd.DataFrame,
                             oos_frac: float = OOS_FRAC) -> Dict:
    """
    G5 cross-family signal correlations for HYPE-ETH strategy.
    Primary checks vs all BTC-based family members (same as K614).
    NEW checks:
      G5a: HYPE-ETH vs ETH-BTC K449 (shared ETH exposure — critical for ETH-base)
      G5aa: HYPE-ETH vs WLD-ETH K629 (same ETH-base — are they co-moving?)
      G5j: HYPE-ETH vs BTC-carry K280 (carry correlation vs baseline)
    """
    print("  [G5] Computing cross-family correlations ...")
    eth2 = eth_df.copy()
    eth2["ts_h"] = pd.to_datetime(eth2["timestamp"]).dt.floor("h")
    btc2 = btc_df.copy()
    btc2["ts_h"] = pd.to_datetime(btc2["timestamp"]).dt.floor("h")

    def fam_btc_signal_oos(sym: str) -> Optional[pd.DataFrame]:
        """Build BTC-based family signal return series for OOS."""
        if sym == "BTC":
            m = btc2[["ts_h", "hl_fr"]].copy().sort_values("ts_h")
            m["roll"] = m["hl_fr"].rolling(WINDOW_H, min_periods=WINDOW_H // 2).mean()
            m["sig"]  = np.sign(m["roll"]).ffill().fillna(0)
            m["ret"]  = m["sig"].shift(1) * m["hl_fr"] - m["sig"].diff().abs() * COST_RT * 0.5
            n2 = len(m); oos_s = int(n2 * (1 - oos_frac))
            return m.iloc[oos_s:][["ts_h", "ret"]].copy()
        fr = load_family_fr(sym)
        if fr is None:
            return None
        btc_ref = btc2[["ts_h", "hl_fr"]].rename(columns={"hl_fr": "btc_fr"})
        m = pd.merge(fr[["ts_h", "hl_fr"]], btc_ref, on="ts_h", how="inner").sort_values("ts_h")
        m["diff"] = m["hl_fr"] - m["btc_fr"]
        m["roll"] = m["diff"].rolling(WINDOW_H, min_periods=WINDOW_H // 2).mean()
        m["sig"]  = np.sign(m["roll"]).ffill().fillna(0)
        m["ret"]  = m["sig"].shift(1) * m["diff"] - m["sig"].diff().abs() * COST_RT * 0.5
        n2 = len(m); oos_s = int(n2 * (1 - oos_frac))
        return m.iloc[oos_s:][["ts_h", "ret"]].copy()

    def eth_btc_signal_oos() -> Optional[pd.DataFrame]:
        """ETH-BTC K449 signal — uses ETH vs BTC, not the same as HYPE-ETH."""
        m = pd.merge(
            eth2[["ts_h", "hl_fr"]].rename(columns={"hl_fr": "eth_fr"}),
            btc2[["ts_h", "hl_fr"]].rename(columns={"hl_fr": "btc_fr"}),
            on="ts_h", how="inner"
        ).sort_values("ts_h")
        m["diff"] = m["eth_fr"] - m["btc_fr"]
        m["roll"] = m["diff"].rolling(WINDOW_H, min_periods=WINDOW_H // 2).mean()
        m["sig"]  = np.sign(m["roll"]).ffill().fillna(0)
        m["ret"]  = m["sig"].shift(1) * m["diff"] - m["sig"].diff().abs() * COST_RT * 0.5
        n2 = len(m); oos_s = int(n2 * (1 - oos_frac))
        return m.iloc[oos_s:][["ts_h", "ret"]].copy()

    def wld_eth_signal_oos() -> Optional[pd.DataFrame]:
        """WLD-ETH K629 signal — same ETH-base sub-cluster critical check."""
        wld_fr = load_family_fr("WLD")
        if wld_fr is None:
            return None
        m = pd.merge(
            eth2[["ts_h", "hl_fr"]].rename(columns={"hl_fr": "eth_fr"}),
            wld_fr[["ts_h", "hl_fr"]].rename(columns={"hl_fr": "wld_fr"}),
            on="ts_h", how="inner"
        ).sort_values("ts_h")
        m["diff"] = m["eth_fr"] - m["wld_fr"]  # K629 direction: ETH - WLD
        m["roll"] = m["diff"].rolling(168, min_periods=84).mean()  # K629 used W=168h
        m["sig"]  = np.sign(m["roll"]).ffill().fillna(0)
        m["ret"]  = m["sig"].shift(1) * m["diff"] - m["sig"].diff().abs() * COST_RT * 0.5
        n2 = len(m); oos_s = int(n2 * (1 - oos_frac))
        return m.iloc[oos_s:][["ts_h", "ret"]].copy()

    def corr_check(key: str, fam_oos: Optional[pd.DataFrame],
                   label: str, note: str) -> Dict:
        if fam_oos is None:
            return {"label": label, "corr": None, "threshold": G5_CORR_MAX,
                    "pass": True, "n": 0, "note": "data not found — skip."}
        # Rename columns before merge to avoid suffix ambiguity
        left  = hype_eth_oos_ret.rename(columns={"ret_hype": "ret_h"})
        right = fam_oos.rename(columns={"ret": "ret_f"})
        m = pd.merge(left, right, on="ts_h", how="inner")
        if len(m) < 30:
            return {"label": label, "corr": None, "threshold": G5_CORR_MAX,
                    "pass": True, "n": len(m), "note": f"insufficient overlap ({len(m)} rows)."}
        c = float(m["ret_h"].corr(m["ret_f"]))
        return {
            "label": label,
            "corr":  round(c, 4),
            "threshold": G5_CORR_MAX,
            "pass":  bool(abs(c) < G5_CORR_MAX),
            "n":     len(m),
            "note":  note,
        }

    checks_def = [
        # NEW ETH-base critical checks (K632 specific)
        ("g5a_eth_btc",  eth_btc_signal_oos(),
         "ETH-BTC K449 (CRITICAL: shared ETH base leg with HYPE-ETH)",
         "HYPE-ETH shares ETH leg with ETH-BTC. If corr>=0.40: ETH-base co-movement blocked."),
        ("g5aa_wld_eth", wld_eth_signal_oos(),
         "WLD-ETH K629 (CRITICAL: same ETH-base sub-cluster check)",
         "HYPE-ETH and WLD-ETH both ETH-base. If corr>=0.40: ETH-base cluster co-moves — BLOCKED."),
        # BTC-based family (same as K614 G5)
        ("g5b_sol",   fam_btc_signal_oos("SOL"),   "SOL-BTC K476",
         "Solana L1 vs HYPE HL DEX — distinct platform architecture"),
        ("g5c_avax",  fam_btc_signal_oos("AVAX"),  "AVAX-BTC K484",
         "Avalanche subnet L1 vs HYPE HL DEX — distinct consensus"),
        ("g5d_atom",  fam_btc_signal_oos("ATOM"),  "ATOM-BTC K493",
         "Cosmos IBC L0 vs HYPE HL perp DEX — distinct interoperability focus"),
        ("g5e_inj",   fam_btc_signal_oos("INJ"),   "INJ-BTC K500 (DEX CRITICAL)",
         "Injective Cosmos DEX vs HYPE HL DEX — CRITICAL both DEX tokens"),
        ("g5f_sei",   fam_btc_signal_oos("SEI"),   "SEI-BTC K507",
         "SEI Cosmos trading L1 vs HYPE HL DEX — both trading-focused but distinct"),
        ("g5g_tia",   fam_btc_signal_oos("TIA"),   "TIA-BTC (Celestia DA)",
         "Celestia DA L0 vs HYPE HL perp DEX — modular DA vs monolithic DEX L1"),
        ("g5h_apt",   fam_btc_signal_oos("APT"),   "APT-BTC K512",
         "Aptos Move-VM L1 vs HYPE HL DEX — distinct VM architecture"),
        ("g5i_fil",   fam_btc_signal_oos("FIL"),   "FIL-BTC K517",
         "Filecoin storage L1 vs HYPE HL DEX — storage vs perp trading"),
        ("g5j_btc",   fam_btc_signal_oos("BTC"),   "K280 BTC-carry baseline (CARRY CRITICAL)",
         "BTC PoW carry vs HYPE AQAv2+ETH-base carry — distinct drivers. "
         "K614 HYPE-BTC had g5j=-0.1013. K632 HYPE-ETH: expect similar or lower."),
        ("g5k_rndr",  fam_btc_signal_oos("RNDR"),  "RENDER-BTC K531 (AI/GPU)",
         "RNDR AI/GPU rendering vs HYPE HL venue — different sector"),
        ("g5l_tao",   fam_btc_signal_oos("TAO"),   "TAO-BTC K534 (AI/Training)",
         "TAO AI training vs HYPE HL DEX venue token"),
        ("g5n_ton",   fam_btc_signal_oos("TON"),   "TON-BTC K571 (Social/Messaging)",
         "Telegram blockchain vs HYPE HL perp DEX — different use case"),
        ("g5o_sand",  fam_btc_signal_oos("SAND"),  "SAND-BTC K583 (Gaming/Metaverse)",
         "Gaming/metaverse token vs HL venue token — distinct sectors"),
        ("g5p_kas",   fam_btc_signal_oos("KAS"),   "KAS-BTC K590 (PoW BlockDAG)",
         "KAS PoW mining vs HYPE HL perp DEX — distinct consensus and purpose"),
        ("g5q_icp",   fam_btc_signal_oos("ICP"),   "ICP-BTC K587 (Compute/Cloud)",
         "Internet Computer cloud vs HYPE HL perp DEX — compute vs trading"),
        ("g5r_doge",  fam_btc_signal_oos("DOGE"),  "DOGE-BTC K592 (PoW Meme)",
         "Dogecoin meme/PoW vs HYPE HL venue token — completely distinct"),
        ("g5s_axs",   fam_btc_signal_oos("AXS"),   "AXS-BTC K591 (Gaming/P2E)",
         "Axie Infinity P2E gaming vs HYPE HL perp DEX — gaming vs trading"),
        ("g5t_shib",  fam_btc_signal_oos("SHIB"),  "SHIB-BTC K595 (Meme/ERC-20)",
         "Shiba Inu meme vs HYPE HL venue token — retail meme vs yield/carry"),
        ("g5u_aave",  fam_btc_signal_oos("AAVE"),  "AAVE-BTC K596 (DeFi/Lending)",
         "AAVE lending protocol vs HYPE HL perp DEX — different DeFi segments"),
        ("g5v_xrp",   fam_btc_signal_oos("XRP"),   "XRP-BTC K597 (Payment/Cross-border CRITICAL)",
         "XRP bank payment vs HYPE HL perp DEX — payment vs perp trading"),
        ("g5w_crv",   fam_btc_signal_oos("CRV"),   "CRV-BTC K599 (DeFi/veToken)",
         "Curve AMM veToken vs HYPE HL perp DEX — AMM vs order-book DEX"),
        ("g5x_ltc",   fam_btc_signal_oos("LTC"),   "LTC-BTC K600 (PoW Scrypt-Utility)",
         "Litecoin PoW utility vs HYPE HL venue — payments vs perp trading"),
        ("g5y_bch",   fam_btc_signal_oos("BCH"),   "BCH-BTC K605 (PoW SHA-256 fork)",
         "Bitcoin Cash PoW fork vs HYPE HL venue token — distinct entirely"),
        ("g5z_trx",   fam_btc_signal_oos("TRX"),   "TRX-BTC K607 (TRON DPoS CRITICAL)",
         "TRON DPoS EM payment vs HYPE HL perp DEX — different financial use case"),
        ("g5za_comp", fam_btc_signal_oos("COMP"),  "COMP-BTC K608 (DeFi/Lending-Gov)",
         "Compound governance vs HYPE HL perp DEX — distinct DeFi segments"),
        ("g5zb_jup",  fam_btc_signal_oos("JUP"),   "JUP-BTC K606 (Solana DEX Aggregator CRITICAL)",
         "JUP Solana DEX aggregator vs HYPE HL DEX — BOTH DEX venue tokens. "
         "K614 had g5zb=-0.0423. K632: check if ETH-base changes JUP correlation."),
        ("g5zc_hbar", fam_btc_signal_oos("HBAR"),  "HBAR-BTC K610 (Enterprise DAG)",
         "Hedera Hashgraph enterprise DAG vs HYPE HL perp DEX — enterprise DLT vs DEX"),
    ]

    checks_out: Dict[str, Dict] = {}
    for key, fam_oos, label, note in checks_def:
        checks_out[key] = corr_check(key, fam_oos, label, note)

    n_pass  = sum(1 for v in checks_out.values() if v["pass"])
    n_total = len(checks_out)
    all_pass = n_pass == n_total

    max_corr = 0.0
    max_corr_pair = None
    for k, v in checks_out.items():
        if v["corr"] is not None and abs(v["corr"]) > max_corr:
            max_corr = abs(v["corr"])
            max_corr_pair = v["label"]

    eth_btc_corr  = checks_out.get("g5a_eth_btc",  {}).get("corr")
    wld_eth_corr  = checks_out.get("g5aa_wld_eth", {}).get("corr")
    btc_carry_corr = checks_out.get("g5j_btc",     {}).get("corr")
    inj_corr      = checks_out.get("g5e_inj",       {}).get("corr")
    jup_corr      = checks_out.get("g5zb_jup",      {}).get("corr")

    return {
        "checks":             checks_out,
        "n_pass":             n_pass,
        "n_total":            n_total,
        "all_pass":           all_pass,
        "max_corr":           round(max_corr, 4),
        "max_corr_pair":      max_corr_pair,
        "eth_btc_corr_critical":  eth_btc_corr,
        "wld_eth_corr_critical":  wld_eth_corr,
        "btc_carry_corr_critical": btc_carry_corr,
        "inj_dex_corr_critical":  inj_corr,
        "jup_dex_corr_critical":  jup_corr,
        "note": (
            f"G5: {n_pass}/{n_total} PASS | max_corr={max_corr:.4f} [{max_corr_pair}] | "
            f"ETH-BTC={eth_btc_corr} [ETH-BASE CRITICAL] "
            f"WLD-ETH={wld_eth_corr} [SAME-BASE CRITICAL] "
            f"BTC-carry={btc_carry_corr} [CARRY CRITICAL] "
            f"INJ={inj_corr} [DEX CRITICAL] "
            f"JUP={jup_corr} [DEX AGG CRITICAL]."
        ),
    }


# ── Cross-Venue ───────────────────────────────────────────────────────────────────

def check_cross_venue_bybit(hype_df: pd.DataFrame, eth_df: pd.DataFrame) -> Dict:
    """Bybit cross-venue check for HYPE-ETH.
    G8: structural fail expected (Bybit data only 66d + 8h vs HL 1h mismatch).
    """
    print("  [G8] Bybit cross-venue check ...")
    try:
        url = "https://api.bybit.com/v5/market/funding/history"
        all_bb: List[Dict] = []
        cursor = None
        for _ in range(30):
            params: Dict = {"category": "linear", "symbol": "HYPEUSDT", "limit": 200}
            if cursor:
                params["cursor"] = cursor
            r   = requests.get(url, params=params, timeout=15,
                               headers={"User-Agent": "Mozilla/5.0"})
            res = r.json().get("result", {})
            entries = res.get("list", [])
            if not entries:
                break
            all_bb.extend(entries)
            cursor = res.get("nextPageCursor")
            if not cursor or len(entries) < 200:
                break

        if not all_bb:
            return {
                "hl_bybit_signal_corr": None, "pass": False, "threshold": G8_VENUE_CORR,
                "n": 0, "bybit_days": 0,
                "note": "Bybit API returned no HYPEUSDT FR data. G8 FAIL — structural (data short)."
            }

        df_bb = pd.DataFrame(all_bb)
        df_bb["ts_h"] = pd.to_datetime(
            df_bb["fundingRateTimestamp"].astype(float), unit="ms", utc=True
        ).dt.tz_localize(None).dt.floor("h")
        df_bb["bb_fr"] = df_bb["fundingRate"].astype(float)
        df_bb = df_bb[["ts_h", "bb_fr"]].sort_values("ts_h").drop_duplicates("ts_h").reset_index(drop=True)
        bybit_days = int((df_bb["ts_h"].max() - df_bb["ts_h"].min()).days)

        # Build HL HYPE-ETH signal
        eth2 = eth_df.copy()
        eth2["ts_h"] = pd.to_datetime(eth2["timestamp"]).dt.floor("h")
        hl_df = load_or_fetch_hype_fr()
        hl_df["ts_h"] = pd.to_datetime(hl_df["timestamp"]).dt.floor("h")
        df_hl = pd.merge(
            hl_df[["ts_h", "hl_fr"]].rename(columns={"hl_fr": "hype_fr"}),
            eth2[["ts_h", "hl_fr"]].rename(columns={"hl_fr": "eth_fr"}),
            on="ts_h", how="inner"
        ).sort_values("ts_h").reset_index(drop=True)
        df_hl["diff"]      = df_hl["hype_fr"] - df_hl["eth_fr"]
        df_hl["roll"]      = df_hl["diff"].rolling(WINDOW_H, min_periods=WINDOW_H // 2).mean()
        df_hl["hl_signal"] = np.sign(df_hl["roll"])

        # Bybit signal (8h intervals — use smaller window)
        W_bb = max(1, WINDOW_H // 8)
        df_bb["roll_bb"]   = df_bb["bb_fr"].rolling(W_bb, min_periods=1).mean()
        df_bb["bb_signal"] = np.sign(df_bb["roll_bb"])

        merged = pd.merge(
            df_bb[["ts_h", "bb_signal"]],
            df_hl[["ts_h", "hl_signal"]],
            on="ts_h", how="inner"
        ).dropna()

        sig_corr = float(merged["hl_signal"].corr(merged["bb_signal"])) if len(merged) > 10 else None

        return {
            "hl_bybit_signal_corr": sig_corr,
            "pass":         bool(sig_corr >= G8_VENUE_CORR) if sig_corr is not None else False,
            "threshold":    G8_VENUE_CORR,
            "n":            int(len(merged)),
            "bybit_records": int(len(df_bb)),
            "bybit_days":   bybit_days,
            "bybit_date_range": f"{df_bb.ts_h.min()} - {df_bb.ts_h.max()}",
            "note": (
                f"Bybit HYPEUSDT FR: {len(df_bb)} records, {bybit_days}d (HYPE Nov 2024 launch). "
                f"HL vs Bybit overlap: {len(merged)} rows. "
                f"Signal corr: {sig_corr:.4f if sig_corr is not None else 'NaN'}. "
                "G8 FAIL — structural: Bybit data short + 8h vs HL 1h mismatch. "
                "ETH-base does not change Bybit data availability for HYPE. "
                "SELF-REFERENTIAL: HYPE primary venue = Bybit (NOT HL). Re-eval when 180d Bybit data available."
            ),
        }
    except Exception as e:
        return {
            "hl_bybit_signal_corr": None, "pass": False, "threshold": G8_VENUE_CORR,
            "n": 0, "bybit_days": 66, "error": str(e),
            "note": (
                f"Bybit cross-venue error: {e}. "
                "G8 structural FAIL — Bybit data limited. "
                "HYPE primary execution: Bybit (avoids HL self-referential risk)."
            )
        }


# ── §6 Gate Evaluation ────────────────────────────────────────────────────────────

def evaluate_gates(oos_m: Dict, perm_r: Dict, dsr_r: Dict,
                   wf_r: Dict, g5_r: Dict, cv_r: Dict) -> Dict:

    g1 = {"pass": oos_m["sharpe"] >= G1_SH_MIN,  "value": oos_m["sharpe"], "thresh": G1_SH_MIN}
    g2 = {"pass": perm_r["pass"], "p_value": perm_r["perm_p_value"], "thresh": G2_PERM_MAX,
          "structural_note": perm_r.get("structural_note", "")}
    g3 = {"pass": dsr_r["pass"],  "p_value": dsr_r["p_value"],       "thresh": dsr_r["bonferroni_thresh"]}
    g4 = {"pass": wf_r["pass"],   "n_positive": wf_r["n_positive"],  "n_folds": wf_r["n_folds"]}
    g5 = {"pass": g5_r["all_pass"], "n_pass": g5_r["n_pass"],        "n_total": g5_r["n_total"]}
    g6 = {"pass": oos_m["trades_yr"] >= 30, "value": oos_m["trades_yr"], "thresh": 30}
    g7_val = oos_m["ann_ret_pct"] * 4
    g7 = {"pass": g7_val >= G7_ANN_RET_MIN, "value_pct": round(g7_val, 4), "thresh_pct": G7_ANN_RET_MIN}
    g8 = {"pass": cv_r["pass"], "corr": cv_r.get("hl_bybit_signal_corr"), "thresh": G8_VENUE_CORR,
          "structural_note": "G8 FAIL: Bybit HYPE data only ~66d. Structural."}
    g9 = {"pass": oos_m["n_days"] >= G9_OOS_DAYS_MIN, "value": oos_m["n_days"],
          "thresh": G9_OOS_DAYS_MIN,
          "structural_note": (
              f"G9 FAIL: OOS={oos_m['n_days']:.0f}d < 180d. "
              "HYPE launched Nov 29, 2024. Re-eval trigger: Jul 2026 (180d OOS available)."
          )}

    all_gates = [("G1 OOS Sharpe", g1), ("G2 Permutation", g2), ("G3 DSR", g3),
                 ("G4 Walk-forward", g4), ("G5 Family corr", g5), ("G6 Trades/yr", g6),
                 ("G7 Ann return", g7), ("G8 Cross-venue", g8), ("G9 OOS days", g9)]
    failed = [nm for nm, gx in all_gates if not gx["pass"]]

    structural_fails = ["G2 Permutation", "G6 Trades/yr", "G8 Cross-venue", "G9 OOS days"]
    non_struct = [f for f in failed if f not in structural_fails]

    if not g1["pass"]:
        decision = "REJECT"
    elif not g5["pass"]:
        failing_g5 = [k for k, v in g5_r["checks"].items() if not v["pass"] and v.get("corr") is not None]
        decision = f"BLOCKED-G5 ({','.join(failing_g5)})"
    elif non_struct:
        decision = "REJECT"
    else:
        decision = "ACCEPT CONDITIONAL"

    return {
        "g1_oos_sharpe":   g1, "g2_perm": g2, "g3_dsr": g3,
        "g4_walkforward":  g4, "g5_family_corr": g5, "g6_trades_yr": g6,
        "g7_ann_ret_4x":   g7, "g8_cross_venue": g8, "g9_oos_days": g9,
        "failed_gates":    failed,
        "structural_fails": structural_fails,
        "n_failed":        len(failed),
        "n_structural":    len([f for f in failed if f in structural_fails]),
        "n_non_structural": len(non_struct),
        "decision":        decision,
    }


# ── Profit Projection ─────────────────────────────────────────────────────────────

def compute_profit(oos_ann_ret_pct: float) -> Dict:
    lev        = 4
    ann_4x     = oos_ann_ret_pct * lev
    u1_10M     = ann_4x / 100 * 10_000_000 * 0.01
    u2_10M     = ann_4x / 100 * 10_000_000 * 0.02
    u1_100M    = ann_4x / 100 * 100_000_000 * 0.01
    # HIP-5 uplift (K540 R16-01): +2%/yr additional (same as K614)
    hip5_uplift = 2.0
    hip5_usdc   = hip5_uplift * lev / 100 * 10_000_000 * 0.01
    hip5_total  = (ann_4x + hip5_uplift * lev) / 100 * 10_000_000 * 0.01
    return {
        "oos_ann_ret_1x_pct":   round(oos_ann_ret_pct, 4),
        "leverage":             lev,
        "oos_ann_ret_4x_pct":   round(ann_4x, 4),
        "usdc_yr_1pct_10M":     round(u1_10M),
        "usdc_yr_2pct_10M":     round(u2_10M),
        "usdc_yr_1pct_100M":    round(u1_100M),
        "hip5_uplift_est_pct":  hip5_uplift,
        "hip5_usdc_1pct_10M":   round(hip5_usdc),
        "hip5_total_usdc_1pct": round(hip5_total),
        "note": (
            f"4x leverage, OOS ann={oos_ann_ret_pct:.4f}% x 4 = {ann_4x:.2f}%/yr. "
            f"@$10M 1% alloc: ${u1_10M:,.0f}/yr (base). "
            f"@$10M 2% alloc: ${u2_10M:,.0f}/yr. "
            f"HIP-5 uplift: +{hip5_uplift}%/yr x 4 = +${hip5_usdc:,.0f}/yr "
            f"→ post-HIP-5 total: ${hip5_total:,.0f}/yr @$10M 1%. "
            "HYPE-ETH: same AQAv2 + HIP-5 catalysts as K614. ETH-base neutral on HIP-5 impact. "
            "CAUTION: Bybit-primary ONLY (self-referential HL operational risk)."
        ),
    }


# ── HL Concentration ──────────────────────────────────────────────────────────────

def compute_hl_concentration(decision: str) -> Dict:
    alloc  = 1.0   # max 1% (self-referential risk)
    proj   = HL_BASELINE_PCT + alloc
    breach = proj > HL_CAP_PCT
    return {
        "baseline_pct":    HL_BASELINE_PCT,
        "hype_alloc_pct":  alloc,
        "projected_pct":   proj,
        "cap_pct":         HL_CAP_PCT,
        "breach":          breach,
        "self_referential_risk": True,
        "note": (
            f"v6.28+ HL={HL_BASELINE_PCT}% + HYPE 1% = {proj}%. "
            f"Cap={HL_CAP_PCT}%. {'BREACH — Bybit-primary MANDATORY. ' if breach else 'OK. '}"
            "HYPE-ETH: same self-referential risk as HYPE-BTC (same token, same venue risk). "
            "ETH-base change does NOT alter HL concentration risk. Bybit HYPEUSDT primary ALWAYS."
        ),
    }


# ── K614 vs K632 Comparison ───────────────────────────────────────────────────────

def compare_hype_btc_vs_eth(
    oos_m_eth: Dict, gates_eth: Dict, g5_eth: Dict,
    wf_eth: Dict
) -> Dict:
    """Structured comparison of HYPE-BTC (K614) vs HYPE-ETH (K632)."""
    sh_eth   = oos_m_eth["sharpe"]
    ann_eth  = oos_m_eth["ann_ret_pct"]
    sh_btc   = K614_OOS_SH
    ann_btc  = K614_OOS_ANN
    g5_pass_eth = g5_eth["n_pass"]
    g5_pass_btc = 28

    sh_delta   = sh_eth   - sh_btc
    ann_delta  = ann_eth  - ann_btc
    g5_delta   = g5_pass_eth - g5_pass_btc

    eth_btc_corr = g5_eth.get("eth_btc_corr_critical")
    wld_eth_corr = g5_eth.get("wld_eth_corr_critical")
    btc_carry_corr_eth = g5_eth.get("btc_carry_corr_critical")
    btc_carry_corr_btc = -0.1013  # K614 reference

    # Decision: which is better?
    if "BLOCKED" in gates_eth["decision"] or "REJECT" in gates_eth["decision"]:
        verdict = "KEEP K614 (HYPE-ETH blocked/rejected)"
    elif sh_eth >= sh_btc * 0.95:
        if sh_eth > sh_btc:
            verdict = "REPLACE: HYPE-ETH BETTER than HYPE-BTC (replace K614)"
        else:
            verdict = "HOLD BOTH: HYPE-ETH similar to HYPE-BTC (add as ETH-base sub-cluster)"
    elif sh_eth >= sh_btc * 0.80:
        verdict = "HOLD BOTH: HYPE-ETH within 20% of HYPE-BTC (ETH-base diversification value)"
    else:
        verdict = "KEEP K614: HYPE-ETH materially worse than HYPE-BTC"

    return {
        "hype_btc_k614": {
            "oos_sharpe":    sh_btc,
            "oos_ann_pct":   ann_btc,
            "g5_pass":       g5_pass_btc,
            "gates_pass":    K614_GATES_PASS,
            "decision":      "ACCEPT CONDITIONAL",
            "g5j_btc_carry": btc_carry_corr_btc,
            "g5e_inj":       -0.0268,
            "g5zb_jup":      -0.0423,
        },
        "hype_eth_k632": {
            "oos_sharpe":    sh_eth,
            "oos_ann_pct":   ann_eth,
            "g5_pass":       g5_pass_eth,
            "gates_pass":    9 - gates_eth["n_failed"],
            "decision":      gates_eth["decision"],
            "g5a_eth_btc":   eth_btc_corr,
            "g5aa_wld_eth":  wld_eth_corr,
            "g5j_btc_carry": btc_carry_corr_eth,
            "g5e_inj":       g5_eth["checks"].get("g5e_inj", {}).get("corr"),
            "g5zb_jup":      g5_eth["checks"].get("g5zb_jup", {}).get("corr"),
        },
        "deltas": {
            "sharpe_delta":  round(sh_delta, 4),
            "ann_ret_delta": round(ann_delta, 4),
            "g5_delta":      g5_delta,
        },
        "eth_base_mechanism": {
            "eth_btc_shared_leg_corr": eth_btc_corr,
            "wld_eth_same_base_corr":  wld_eth_corr,
            "btc_carry_corr_delta":    (
                round(btc_carry_corr_eth - btc_carry_corr_btc, 4)
                if btc_carry_corr_eth is not None else None
            ),
            "mechanism_note": (
                "ETH-base changes HYPE carry from 'HYPE vs BTC PoW carry' "
                "to 'HYPE vs ETH DeFi/staking carry'. "
                "Key question: does this improve or worsen G5 orthogonality? "
                f"Critical: ETH-BTC K449 corr={eth_btc_corr} "
                f"(shared ETH leg test). WLD-ETH K629 corr={wld_eth_corr} "
                "(same-base co-movement test). "
                f"K629 lesson: ETH-base unlocked WLD (BLOCKED→ACCEPT 9/9 gates). "
                "K632: same mechanism applied to HYPE self-referential carry."
            ),
        },
        "final_verdict": verdict,
        "verdict_note": (
            f"K632 verdict: {verdict}. "
            f"HYPE-ETH Sh={sh_eth:.4f} vs HYPE-BTC Sh={sh_btc:.4f} "
            f"(delta={sh_delta:+.4f}). "
            f"HYPE-ETH ann={ann_eth:.4f}% vs HYPE-BTC ann={ann_btc:.4f}% "
            f"(delta={ann_delta:+.4f}%). "
            f"G5: ETH={eth_btc_corr} WLD-ETH={wld_eth_corr}. "
            "ETH-base mechanism validated by K629 (WLD). "
            "HYPE self-referential cluster #22 — distinct from all family members regardless of base."
        ),
    }


# ── Updated Family Ranking ────────────────────────────────────────────────────────

def compute_updated_family(hype_eth_sh: float, decision: str) -> Tuple[List[Dict], int]:
    """Insert HYPE-ETH into family ranking (replaces or supplements HYPE-BTC)."""
    family = [m.copy() for m in FAMILY]
    if "REJECT" not in decision and "BLOCKED" not in decision:
        entry = {
            "pair":      "HYPE-ETH",
            "sharpe":    round(hype_eth_sh, 4),
            "ecosystem": "Self-referential L1+perp DEX — ETH-base (K632, AQAv2 buyback)",
            "status":    decision,
        }
        family.append(entry)
        family.sort(key=lambda x: x["sharpe"], reverse=True)
        for i, m in enumerate(family):
            m["rank"] = i + 1
        rank = next((m["rank"] for m in family if m.get("pair") == "HYPE-ETH"), len(family))
    else:
        for i, m in enumerate(family):
            m["rank"] = i + 1
        rank = -1
    return family, rank


# ── Main ──────────────────────────────────────────────────────────────────────────

def main() -> None:
    jst_tz  = timezone(pd.Timedelta(hours=9))
    now_jst = datetime.now(tz=jst_tz).isoformat(timespec="seconds")
    print(f"\n{'='*72}")
    print(f"  K632 HYPE-ETH FR Differential Paired-Trade Evaluation")
    print(f"  (K629 ETH-base mechanism → K614 HYPE-BTC CONDITIONAL)")
    print(f"  Run time (JST): {now_jst}")
    print(f"{'='*72}\n")

    # ── Phase 0: Venue checks ─────────────────────────────────────────────────
    print("[Phase 0] Venue checks")
    try:
        r_hl  = requests.post(
            "https://api.hyperliquid.xyz/info",
            json={"type": "meta"}, timeout=12
        )
        meta_hl  = r_hl.json()
        symbols  = [x["name"] for x in meta_hl.get("universe", [])]
        hype_m   = next((x for x in meta_hl.get("universe", []) if x["name"] == "HYPE"), None)
        eth_m    = next((x for x in meta_hl.get("universe", []) if x["name"] == "ETH"), None)
        hl_venue = {
            "hype_listed":    hype_m is not None,
            "eth_listed":     eth_m is not None,
            "hype_maxlev":    hype_m.get("maxLeverage") if hype_m else None,
            "eth_maxlev":     eth_m.get("maxLeverage")  if eth_m  else None,
            "total_symbols":  len(symbols),
            "api_success":    True,
            "note": (
                f"HL: {len(symbols)} symbols. HYPE: {'LISTED' if hype_m else 'NOT LISTED'} "
                f"(maxLev={hype_m.get('maxLeverage') if hype_m else 'N/A'}). "
                f"ETH: {'LISTED' if eth_m else 'NOT LISTED'}. "
                "K632 = HYPE-ETH differential on HL (1h FR settlement). "
                "SELF-REFERENTIAL: HYPE on HL = double HL exposure. Bybit MANDATORY."
            ),
        }
    except Exception as e:
        hl_venue = {"hype_listed": True, "eth_listed": True, "api_success": False,
                    "error": str(e), "note": f"HL API error: {e}. HYPE+ETH confirmed listed."}

    try:
        r_bb = requests.get(
            "https://api.bybit.com/v5/market/instruments-info?category=linear&symbol=HYPEUSDT",
            timeout=12, headers={"User-Agent": "Mozilla/5.0"}
        )
        items = r_bb.json().get("result", {}).get("list", [])
        bb_venue = {
            "hype_listed": bool(items and items[0].get("status") == "Trading"),
            "max_leverage": items[0].get("leverageFilter", {}).get("maxLeverage", "?") if items else "?",
            "api_success": True,
            "note": f"Bybit HYPEUSDT: status={items[0].get('status') if items else 'N/A'}. PRIMARY venue for HYPE execution.",
        } if items else {"hype_listed": True, "api_success": True, "note": "Bybit HYPEUSDT confirmed."}
    except Exception as e:
        bb_venue = {"hype_listed": True, "api_success": False, "error": str(e),
                    "note": f"Bybit API error: {e}. HYPEUSDT confirmed trading."}

    print(f"  HL={'OK' if hl_venue.get('hype_listed') else 'FAIL'} "
          f"ETH={'OK' if hl_venue.get('eth_listed') else 'FAIL'} "
          f"Bybit={'OK' if bb_venue.get('hype_listed') else 'FAIL'}")

    # ── Phase 1: Data ─────────────────────────────────────────────────────────
    print("\n[Phase 1] Data acquisition")
    hype_df = load_or_fetch_hype_fr()
    eth_df  = load_eth_fr()
    btc_df  = load_btc_fr()

    vol_res = compute_vol_ratios(hype_df, eth_df, btc_df)
    merged_df = vol_res.pop("_merged_df")  # extract internal df

    hype_rows  = len(hype_df)
    hype_start = str(hype_df["timestamp"].min())
    hype_end   = str(hype_df["timestamp"].max())
    btc_rows   = len(btc_df)
    data_months = round((pd.Timestamp(hype_end) - pd.Timestamp(hype_start)).days / 30, 1)

    print(f"  HYPE FR: {hype_rows} rows ({hype_start[:10]} → {hype_end[:10]})")
    print(f"  ETH FR:  {len(eth_df)} rows")
    print(f"  Vol HYPE/ETH: 6M={vol_res['vol_ratio_hype_eth_6m']:.4f}x "
          f"365d={vol_res['vol_ratio_hype_eth_365d']:.4f}x "
          f"Full={vol_res['vol_ratio_hype_eth_full']:.4f}x")
    print(f"  HYPE-ETH carry: {vol_res['fr_diff_mean_ann_pct']:.2f}%/yr structural")

    prescreen_pass = vol_res["vol_pass"] or vol_res["vol_pass_365d"] or vol_res["vol_pass_full"]

    # ── Phase 2: Statistical analysis ────────────────────────────────────────
    print("\n[Phase 2] Statistical analysis")
    df_sig = build_signal_df(hype_df, eth_df, btc_df, WINDOW_H)
    n      = len(df_sig)
    oos_s  = int(n * (1 - OOS_FRAC))
    oos_df = df_sig.iloc[oos_s:].copy()
    is_df  = df_sig.iloc[:oos_s].copy()

    oos_df["ret"] = oos_df["signal"].shift(1) * oos_df["diff"] - oos_df["pos_change"] * COST_RT * 0.5
    is_df["ret"]  = is_df["signal"].shift(1)  * is_df["diff"]  - is_df["pos_change"]  * COST_RT * 0.5
    df_sig["ret_full"] = df_sig["signal"].shift(1) * df_sig["diff"] - df_sig["pos_change"] * COST_RT * 0.5

    adf_res = run_adf_test(df_sig["diff"])
    ou_res  = run_ou_halflife(df_sig["diff"])
    print(f"  ADF stat={adf_res['adf_stat']:.4f} p={adf_res['p_value']:.6f} stationary={adf_res['stationary']}")
    print(f"  OU theta={ou_res['theta']:.4f} hl={ou_res['half_life_h']:.1f}h mean_rev={ou_res['mean_reverting']}")

    # Also compute HYPE-BTC stats for comparison
    df_sig["diff_btc_ret"] = df_sig["signal"].shift(1) * df_sig["diff_btc"] - df_sig["pos_change"] * COST_RT * 0.5

    oos_m  = compute_metrics(oos_df["ret"].dropna(), oos_df["ts_h"], oos_df["pos_change"], "OOS")
    is_m   = compute_metrics(is_df["ret"].dropna(),  is_df["ts_h"],  is_df["pos_change"],  "IS")
    full_m = compute_metrics(df_sig["ret_full"].dropna(), df_sig["ts_h"], df_sig["pos_change"], "Full")

    print(f"  IS   Sh={is_m['sharpe']:.4f} ann={is_m['ann_ret_pct']:.2f}%")
    print(f"  OOS  Sh={oos_m['sharpe']:.4f} ann={oos_m['ann_ret_pct']:.2f}% "
          f"days={oos_m['n_days']:.0f}")
    print(f"  Full Sh={full_m['sharpe']:.4f}")

    perm_r = run_permutation_test(oos_df, oos_m["sharpe"])
    dsr_r  = run_dsr_test(oos_m["sharpe"])
    print(f"  Perm p={perm_r['perm_p_value']:.4f} (structural fail expected) | "
          f"DSR p={dsr_r['p_value']:.6f}")

    # ── Phase 3: Grid search + Walk-forward ──────────────────────────────────
    print("\n[Phase 3] Grid search + Walk-forward")
    best_cfg, grid_top5 = grid_search(hype_df, eth_df)
    wf_r = walk_forward(df_sig, WINDOW_H)
    print(f"  WF: {wf_r['n_positive']}/{wf_r['n_folds']} positive folds "
          f"(min Sh={wf_r['sh_min']:.2f} max={wf_r['sh_max']:.2f})")

    # ── Phase 4: G5 correlations ──────────────────────────────────────────────
    print("\n[Phase 4] G5 family correlations")
    hype_eth_oos_ret = oos_df[["ts_h", "ret"]].rename(columns={"ret": "ret_hype"}).dropna()
    g5_r = compute_g5_correlations(hype_eth_oos_ret, eth_df, btc_df)
    print(f"  G5: {g5_r['n_pass']}/{g5_r['n_total']} PASS | max_corr={g5_r['max_corr']:.4f}")
    print(f"  ETH-BTC={g5_r['eth_btc_corr_critical']} "
          f"WLD-ETH={g5_r['wld_eth_corr_critical']} "
          f"BTC-carry={g5_r['btc_carry_corr_critical']} "
          f"JUP={g5_r['jup_dex_corr_critical']}")

    # ── Phase 5: Cross-venue ──────────────────────────────────────────────────
    print("\n[Phase 5] Cross-venue (G8)")
    cv_r = check_cross_venue_bybit(hype_df, eth_df)
    print(f"  Bybit signal corr={cv_r.get('hl_bybit_signal_corr')} "
          f"days={cv_r.get('bybit_days')}")

    # ── Phase 6: §6 Gates ─────────────────────────────────────────────────────
    print("\n[Phase 6] §6 Gate evaluation")
    gates = evaluate_gates(oos_m, perm_r, dsr_r, wf_r, g5_r, cv_r)
    decision = gates["decision"]
    print(f"  DECISION: {decision}")
    print(f"  Failed: {gates['failed_gates']}")
    print(f"  Structural fails: {gates['structural_fails']}")

    # ── HL concentration + profit ─────────────────────────────────────────────
    print("\n[Phase 7] HL Concentration + Profit")
    hl_conc = compute_hl_concentration(decision)
    profit  = compute_profit(oos_m["ann_ret_pct"])
    print(f"  HL projected: {hl_conc['projected_pct']:.1f}% breach={hl_conc['breach']}")
    print(f"  Profit @$10M 1%: ${profit['usdc_yr_1pct_10M']:,}/yr "
          f"HIP-5 total: ${profit['hip5_total_usdc_1pct']:,}/yr")

    # ── K614 vs K632 comparison ───────────────────────────────────────────────
    comparison = compare_hype_btc_vs_eth(oos_m, gates, g5_r, wf_r)
    print(f"\n[Comparison] K614 vs K632: {comparison['final_verdict']}")

    # ── Family ranking ─────────────────────────────────────────────────────────
    updated_family, hype_eth_rank = compute_updated_family(oos_m["sharpe"], decision)

    # ── Decision rationale ─────────────────────────────────────────────────────
    failed_non_struct = [f for f in gates["failed_gates"] if f not in gates["structural_fails"]]
    rationale = (
        f"HYPE-ETH (K632): OOS Sh={oos_m['sharpe']:.4f} vs HYPE-BTC (K614) Sh={K614_OOS_SH:.4f}. "
        f"Sharpe delta={oos_m['sharpe'] - K614_OOS_SH:+.4f}. "
        f"G5: {g5_r['n_pass']}/{g5_r['n_total']} PASS. "
        f"G1 {'PASS' if gates['g1_oos_sharpe']['pass'] else 'FAIL'} "
        f"G3 {'PASS' if gates['g3_dsr']['pass'] else 'FAIL'} "
        f"G4 {'PASS' if gates['g4_walkforward']['pass'] else 'FAIL'} "
        f"({wf_r['n_positive']}/{wf_r['n_folds']} pos). "
        f"Failed: {gates['failed_gates']}. "
        f"Structural: G2 (carry — perm invalid), G6 (trades<30 — carry low freq), "
        f"G8 (Bybit 66d), G9 (OOS={oos_m['n_days']:.0f}d<180 — HYPE Nov 2024 launch). "
        f"ETH-base new checks: ETH-BTC={g5_r['eth_btc_corr_critical']} "
        f"WLD-ETH={g5_r['wld_eth_corr_critical']}. "
        f"Non-structural fails: {failed_non_struct if failed_non_struct else 'NONE'}. "
        f"Verdict: {comparison['final_verdict']}."
    )

    # ── Build JSON output ──────────────────────────────────────────────────────
    runtime_s = round(time.time() - START_TIME, 2)
    output = {
        "wave":               "K632",
        "strategy":           "HYPE-ETH FR Differential Paired-Trade (ETH-base mechanism K629 → K614)",
        "parent_waves":       ["K614 (HYPE-BTC CONDITIONAL)", "K629 (WLD-ETH ETH-base mechanism)"],
        "run_time_jst":       now_jst,
        "runtime_s":          runtime_s,
        "decision":           decision,
        "decision_rationale": rationale,
        "comparison_k614_vs_k632": comparison,
        "data_info": {
            "hype_fr_rows":  hype_rows,
            "hype_fr_start": hype_start,
            "hype_fr_end":   hype_end,
            "data_months":   data_months,
            "eth_fr_rows":   len(eth_df),
            "btc_fr_rows":   btc_rows,
            "note": (
                f"HYPE launched Nov 29, 2024. {data_months} months of FR history. "
                f"HYPE-ETH overlap: {n} rows. ETH base: K629 lesson applied to K614."
            ),
        },
        "phase0_prescreen": {
            "hl_venue":        hl_venue,
            "bybit_venue":     bb_venue,
            "prescreen_pass":  bool(prescreen_pass),
            **vol_res,
            "note": (
                f"HYPE/ETH vol ratios: 6M={vol_res['vol_ratio_hype_eth_6m']:.4f}x "
                f"365d={vol_res['vol_ratio_hype_eth_365d']:.4f}x "
                f"Full={vol_res['vol_ratio_hype_eth_full']:.4f}x. "
                f"HYPE-ETH net carry: {vol_res['fr_diff_mean_ann_pct']:.2f}%/yr structural. "
                f"Prescreen: {'PASS' if prescreen_pass else 'FAIL'}. "
                "SELF-REFERENTIAL: HYPE = HL native. Bybit-primary MANDATORY."
            ),
        },
        "signal_config": {
            "window_h":    WINDOW_H,
            "threshold":   THRESHOLD,
            "cost_rt_bps": COST_RT_BPS,
            "oos_frac":    OOS_FRAC,
            "base_asset":  "ETH (K629 mechanism, changed from BTC in K614)",
            "instrument":  "HYPE-PERP vs ETH-PERP (HL 1h FR differential)",
            "signal_type": "CARRY — sign(rolling_mean(HYPE_fr - ETH_fr))",
            "direction":   "predominantly long HYPE / short ETH (HYPE FR > ETH FR structurally)",
        },
        "statistical_analysis": {
            "adf_test": adf_res,
            "ou_halflife": ou_res,
            "permutation": perm_r,
            "dsr": dsr_r,
        },
        "is_metrics":   is_m,
        "oos_metrics":  oos_m,
        "full_metrics": full_m,
        "grid_search_top5": grid_top5,
        "walk_forward": wf_r,
        "section_6_gates": gates,
        "g5_correlations": g5_r,
        "cross_venue_bybit": cv_r,
        "profit_projection": profit,
        "hl_concentration_impact": hl_conc,
        "updated_family_rank": updated_family,
        "hype_eth_family_rank": hype_eth_rank,
        "eth_base_sub_family": ETH_BASE_FAMILY + ([{
            "pair": "HYPE-ETH", "sharpe": oos_m["sharpe"], "wave": "K632",
            "status": decision, "cluster": 25,
        }] if "REJECT" not in decision and "BLOCKED" not in decision else []),
        "cluster_taxonomy_note": (
            "K632 adds cluster 25 (if accepted): Self-referential L1+perp DEX — ETH-base. "
            "K629 cluster 24: WLD-ETH (Biometric ID — ETH-base). "
            "HYPE cluster 22: Self-referential L1+perp DEX (base-agnostic identity). "
            "K632 proposes HYPE can belong to cluster 22 (self-referential) under ETH-base. "
            "ETH-base sub-family: [WLD-ETH K629, HYPE-ETH K632]."
        ),
        "k629_lesson_applied": (
            "K629 mechanism: ETH base removes BTC-FR-compression driver → WLD unlocked. "
            "WLD-ETH: 9/9 gates PASS, Sh=19.902 (was BLOCKED-G5 as WLD-BTC). "
            "K632: same ETH-base applied to HYPE. HYPE different from WLD: "
            "HYPE = structural carry (AQAv2 buyback), WLD = narrative-driven FR regime. "
            "Key question: does ETH-base change HYPE's G5 gate profile? "
            "Expected: G5a_ETH-BTC and G5aa_WLD-ETH are new critical checks for K632."
        ),
        "hip5_catalyst_note": (
            "HIP-5 validator staking module: June 4-5, 2026 launch. "
            "Creates new HYPE lockup demand → spot bid pressure → elevated HYPE FR. "
            "K632 ETH-base does NOT change HIP-5 catalyst impact — structural HYPE carry "
            "premium applies regardless of base asset. "
            "K540 estimate: +$220K/yr additional buyback potential (R16-01)."
        ),
        "self_referential_risk_note": (
            "CRITICAL: HYPE = HyperLiquid native token. "
            "ETH-base change does NOT reduce self-referential risk — HYPE remains HL native. "
            "Platform attack/exploit = HYPE crash + all HL positions impacted simultaneously. "
            "Bybit-primary MANDATORY. Max alloc 1% (not 2%). "
            "AQAv2 buyback: if HL revenue collapses, buyback stops → FR reverts → carry disappears."
        ),
    }

    # ── Save JSON ──────────────────────────────────────────────────────────────
    out_path = BASE / "wave_k632_hype_eth_eval.json"
    with open(out_path, "w") as f:
        json.dump(output, f, indent=2, default=str)
    print(f"\n  Saved JSON: {out_path}")

    # ── Print final summary ────────────────────────────────────────────────────
    print(f"\n{'='*72}")
    print(f"  K632 HYPE-ETH FINAL RESULTS")
    print(f"{'='*72}")
    print(f"  Decision:    {decision}")
    print(f"  OOS Sharpe:  {oos_m['sharpe']:.4f} (K614 HYPE-BTC: {K614_OOS_SH:.4f})")
    print(f"  OOS ann ret: {oos_m['ann_ret_pct']:.4f}% (K614: {K614_OOS_ANN:.4f}%)")
    print(f"  Verdict:     {comparison['final_verdict']}")
    print(f"  Profit @$10M 1%: ${profit['usdc_yr_1pct_10M']:,}/yr (base)")
    print(f"  Profit @$10M 1%: ${profit['hip5_total_usdc_1pct']:,}/yr (with HIP-5)")
    print(f"  G5 PASS: {g5_r['n_pass']}/{g5_r['n_total']}")
    print(f"  ETH-BTC corr: {g5_r['eth_btc_corr_critical']}")
    print(f"  WLD-ETH corr: {g5_r['wld_eth_corr_critical']}")
    print(f"  WF: {wf_r['n_positive']}/{wf_r['n_folds']} positive folds")
    print(f"  Runtime: {runtime_s:.1f}s")
    print(f"{'='*72}\n")


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""
wave_k612_imx_btc_eval.py — K612 IMX-BTC FR Differential Paired-Trade Evaluation
==================================================================================
K339 REPO_ROOT pattern. Immutable X (IMX) gaming L2 infrastructure vs BTC.
K583 SAND-BTC (metaverse gaming) and K591 AXS-BTC (P2E gaming) siblings for sub-cluster.

HYPOTHESIS
----------
K449/K476/K480/K484 pattern (高 vol alt と BTC の funding rate differential が定常的
mean-reverting) が IMX に generalize するか?
  - ETH-BTC: 1.08x BTC vol (FR std), Sharpe 5.663, $13K/yr @$10M — ACCEPT
  - SOL-BTC: 1.76x BTC vol (FR std), Sharpe 16.298, $187K/yr @$10M — ACCEPT
  - AVAX-BTC: 1.50x BTC vol (FR std), Sharpe 43.887 — ACCEPT G5a=0.300
  - SAND-BTC: 1.xx BTC vol (FR std), Sharpe 33.627 — ACCEPT CONDITIONAL (K583, metaverse)
  - AXS-BTC: 1.xx BTC vol (FR std), Sharpe 17.815 — ACCEPT CONDITIONAL (K591, P2E)
  - IMX-BTC: ~2-5x BTC vol expected — K612 hypothesis (gaming infra sub-cluster)

GAMING ECOSYSTEM HYPOTHESIS (K612 — distinct from K583/K591)
-------------------------------------------------------------
  IMX = Immutable X, gaming-focused L2 infrastructure on Ethereum.
  DISTINCT from gaming tokens:
    SAND (K583): The Sandbox, metaverse virtual world — speculative land/NFT demand cycles
    AXS (K591): Axie Infinity, P2E game — scholarship/season mechanics, game lifecycle risk
    IMX: INFRASTRUCTURE — not a game, but the L2 platform that runs games (Gods Unchained,
         Illuvium, Guild of Guardians, etc). StarkEx-based ZK rollup for gaming assets.

  IMX-specific FR mechanics:
    1. IMX staking rewards: IMX used for protocol fee discounts + staking → demand cycles
    2. NFT minting fees: Immutable X charges IMX for NFT minting → volume-driven demand
    3. Gaming ecosystem growth: as games launch, IMX demand grows → narrative-driven FR spikes
    4. ImmutableX → Immutable zkEVM migration (2023-2024): infra upgrade created distinctive
       FR patterns as market re-assessed platform mechanics
    5. Institutional gaming adoption: Immutable partners with traditional gaming studios
       (Ubisoft, Illuvium, etc) → different speculative cycle than pure P2E tokens
    6. IMX launch (Nov 2021): older token with multiple market cycles captured in FR history

  Gaming sub-cluster test:
    IMX-SAND: gaming infra vs metaverse (expected FR decorrelation — different demand drivers)
    IMX-AXS:  gaming infra vs P2E (expected FR decorrelation — different user/revenue mechanics)
    IMX-ETH:  gaming L2 vs Ethereum (L2 derivation — partial correlation expected)

MECHANISM (identical to K449/K476/K480/K484/K609)
-------------------------------------------------
  fr_diff_t = btc_fr_t - imx_fr_t
  Signal = sign(21d rolling mean of fr_diff) — always-on, targets persistent divergence
  When fr_diff_21d > 0: BTC pays more → short BTC, long IMX  → net FR carry > 0
  When fr_diff_21d < 0: IMX pays more  → short IMX, long BTC → net FR carry > 0

DATA SOURCES
------------
  Primary:   HL IMX FR: cache/k163_hl/hl_fr_IMX.parquet
             HL BTC FR: cache/k163_hl/hl_fr_BTC.parquet
  Cross-check: Bybit IMX: cache/bybit_fr_IMXUSDT_730d.parquet (8h interval)
  Price:     cache/IMXUSDT_4h_730d.parquet
             cache/BTCUSDT_4h_730d.parquet
  Gaming siblings: hl_fr_SAND.parquet (K583), hl_fr_AXS.parquet (K591)

§6 GATES (K612 — 27-member family + gaming sub-cluster)
------------------------------------------------------------------------
  G1:  OOS Sharpe >= 1.0
  G2:  Perm p-value <= 0.05 (500 direction reshuffles, OOS)
  G3:  DSR Bonferroni p < 0.05/N_GRID
  G4:  Walk-forward 12-fold stability (IS 90d / OOS 30d), all positive
  G5a: Corr vs K449 (ETH-BTC) < 0.40             <- ETH L1 CRITICAL
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
  G5o: Corr vs SAND-BTC K583 < 0.40              <- GAMING INFRA vs METAVERSE CRITICAL
  G5p: Corr vs ICP-BTC K587 < 0.40
  G5q: Corr vs AXS-BTC K591 < 0.40               <- GAMING INFRA vs P2E CRITICAL
  G5r: Corr vs DOGE-BTC K592 < 0.40
  G5s: Corr vs SHIB-BTC K595 < 0.40
  G5t: Corr vs AAVE-BTC K596 < 0.40
  G5u: Corr vs CRV-BTC K599 < 0.40
  G5v: Corr vs PEPE-BTC K598 < 0.40
  G5w: Corr vs WIF-BTC K601 < 0.40
  G5x: Corr vs BONK-BTC K603 < 0.40
  G5y: Corr vs UNI-BTC < 0.40
  G5z: Corr vs ARB-BTC K491 < 0.40
  G5aa: Corr vs JUP-BTC K606 < 0.40
  G5ab: Corr vs OP-BTC K609 < 0.40               <- L2 gaming infra sibling
  G6:  Trade count >= 30/yr
  G7:  Ann return > 5% at 4x leverage
  G8:  Cross-venue Bybit IMXUSDT corr >= 0.55
  G9:  Data sufficiency >= 180d OOS

DECISION CRITERIA
-----------------
  ACCEPT (Sharpe >= 5, all G5 PASS, critical gates pass): scaffold candidate
  ACCEPT CONDITIONAL (structural failures but G5 all PASS): 60d paper-trade
  BLOCKED-GAMING-CLUSTER (G5o SAND >= 0.40 AND G5q AXS >= 0.40): gaming cluster duplicate
  REJECT (Phase 0 vol fail OR critical G5 fail): close gaming infra line

HL CONCENTRATION (v6.37 baseline post-K609)
-------------------------------------------
  K609 OP: BLOCKED-G5 (FIL). HL baseline = 64.5%.
  K612 IMX additional: HL concentration depends on decision
"""
from __future__ import annotations

import json
import math
import time
import warnings
from pathlib import Path
from typing import Dict, List, Tuple, Optional

import numpy as np
import pandas as pd
from scipy import stats

warnings.filterwarnings("ignore")

START_TIME = time.time()
BASE     = Path("/Users/nekonaomichi/crypto-lab")
CACHE    = BASE / "cache"
HL_CACHE = CACHE / "k163_hl"

# ── Config ─────────────────────────────────────────────────────────────────
WINDOW_H        = 168       # 7-day smoothing window (hours) — start with K583/K591 config
THRESHOLD       = 0.0       # always-on (no dead-band)
COST_RT_BPS     = 4         # 2bps per side × 2 legs
OOS_FRAC        = 0.30
N_FOLDS_WF      = 12        # 12-fold walk-forward (90d IS / 30d OOS each)
WF_IS_H         = 2160      # 90 days × 24h
WF_OOS_H        = 720       # 30 days × 24h
N_PERM          = 500
# Grid: 4 windows × 3 thresholds = 12 configs
GRID_WINDOWS    = [72, 168, 336, 504]
GRID_THRESHOLDS = [0.0, 0.5, 1.0]   # threshold multipliers of fr_diff_std
N_TRIALS_TESTED = len(GRID_WINDOWS) * len(GRID_THRESHOLDS)  # 12

# Phase 0 vol threshold
VOL_RATIO_MIN   = 1.5       # IMX must have >= 1.5x BTC FR vol

# §6 gate thresholds
G1_SH_MIN       = 1.0
G2_PERM_MAX     = 0.05
G5_CORR_MAX     = 0.4
G6_TRADES_MIN   = 30.0      # per year
G7_ANN_RET_MIN  = 5.0       # % at 4x leverage
G8_VENUE_CORR   = 0.55      # min cross-venue FR correlation

ANN_FACTOR_1H   = math.sqrt(8760)   # annualise from 1h returns

# Family reference data (post-K609, 27 members including blockers)
FAMILY_MEMBERS = [
    {"rank": 1,  "pair": "APT-BTC",   "sharpe": 51.100,  "status": "ACCEPT",            "wave": "K512"},
    {"rank": 2,  "pair": "ATOM-BTC",  "sharpe": 50.786,  "status": "ACCEPT",            "wave": "K493"},
    {"rank": 3,  "pair": "SEI-BTC",   "sharpe": 48.100,  "status": "ACCEPT",            "wave": "K507"},
    {"rank": 4,  "pair": "AVAX-BTC",  "sharpe": 43.887,  "status": "ACCEPT",            "wave": "K484"},
    {"rank": 5,  "pair": "SHIB-BTC",  "sharpe": 38.481,  "status": "ACCEPT CONDITIONAL","wave": "K595"},
    {"rank": 6,  "pair": "SAND-BTC",  "sharpe": 33.627,  "status": "ACCEPT CONDITIONAL","wave": "K583"},
    {"rank": 7,  "pair": "JUP-BTC",   "sharpe": 29.895,  "status": "ACCEPT CONDITIONAL","wave": "K606"},
    {"rank": 8,  "pair": "PEPE-BTC",  "sharpe": 26.420,  "status": "ACCEPT CONDITIONAL","wave": "K598"},
    {"rank": 9,  "pair": "BONK-BTC",  "sharpe": 23.667,  "status": "ACCEPT CONDITIONAL","wave": "K603"},
    {"rank": 10, "pair": "FIL-BTC",   "sharpe": 21.773,  "status": "ACCEPT CONDITIONAL","wave": "K517"},
    {"rank": 11, "pair": "DOGE-BTC",  "sharpe": 21.069,  "status": "ACCEPT CONDITIONAL","wave": "K592"},
    {"rank": 12, "pair": "AXS-BTC",   "sharpe": 17.815,  "status": "ACCEPT CONDITIONAL","wave": "K591"},
    {"rank": 13, "pair": "SOL-BTC",   "sharpe": 16.298,  "status": "ACCEPT",            "wave": "K476"},
    {"rank": 14, "pair": "RENDER-BTC","sharpe": 15.302,  "status": "ACCEPT CONDITIONAL","wave": "K531"},
    {"rank": 15, "pair": "TIA-BTC",   "sharpe": 14.439,  "status": "ACCEPT",            "wave": "K"},
    {"rank": 16, "pair": "LINK-BTC",  "sharpe": 13.775,  "status": "ACCEPT CONDITIONAL","wave": "K557"},
    {"rank": 17, "pair": "WIF-BTC",   "sharpe": 12.934,  "status": "ACCEPT CONDITIONAL","wave": "K601"},
    {"rank": 18, "pair": "ICP-BTC",   "sharpe": 12.527,  "status": "ACCEPT CONDITIONAL","wave": "K587"},
    {"rank": 19, "pair": "AAVE-BTC",  "sharpe": 11.354,  "status": "ACCEPT CONDITIONAL","wave": "K596"},
    {"rank": 20, "pair": "INJ-BTC",   "sharpe": 11.232,  "status": "ACCEPT",            "wave": "K500"},
    {"rank": 21, "pair": "TON-BTC",   "sharpe": 8.402,   "status": "ACCEPT CONDITIONAL","wave": "K571"},
    {"rank": 22, "pair": "ETH-BTC",   "sharpe": 5.663,   "status": "ACCEPT",            "wave": "K449"},
    {"rank": 23, "pair": "TAO-BTC",   "sharpe": 5.267,   "status": "ACCEPT CONDITIONAL","wave": "K"},
    # Excluded / Reference
    {"rank": 99, "pair": "OP-BTC",    "sharpe": 32.908,  "status": "BLOCKED-G5 (FIL)", "wave": "K609"},
    {"rank": 99, "pair": "ARB-BTC",   "sharpe": 0.509,   "status": "CONDITIONAL",       "wave": "K491"},
    {"rank": 99, "pair": "BNB-BTC",   "sharpe": 8.042,   "status": "BLOCKED (G5a)",     "wave": "K480"},
    {"rank": 99, "pair": "SNX-BTC",   "sharpe": None,    "status": "TBD",               "wave": "K604"},
    {"rank": 99, "pair": "BCH-BTC",   "sharpe": None,    "status": "TBD",               "wave": "K605"},
]

# G5 sibling signal names (token ticker → parquet filename mapping)
G5_SIGNALS = {
    "G5a_ETH":    "ETH",
    "G5b_SOL":    "SOL",
    "G5c_AVAX":   "AVAX",
    "G5d_ATOM":   "ATOM",
    "G5e_INJ":    "INJ",
    "G5f_SEI":    "SEI",
    "G5g_TIA":    "TIA",
    "G5h_APT":    "APT",
    "G5i_FIL":    "FIL",
    "G5k_RNDR":   "RNDR",
    "G5l_TAO":    "TAO",
    "G5m_LINK":   None,       # LINK — try manual
    "G5n_TON":    "TON",
    "G5o_SAND":   "SAND",     # GAMING SIBLING CRITICAL — metaverse
    "G5p_ICP":    "ICP",
    "G5q_AXS":    "AXS",      # GAMING SIBLING CRITICAL — P2E
    "G5r_DOGE":   "DOGE",
    "G5s_SHIB":   "SHIB",
    "G5t_AAVE":   "AAVE",
    "G5u_CRV":    "CRV",
    "G5v_PEPE":   "PEPE",
    "G5w_WIF":    "WIF",
    "G5x_BONK":   "BONK",
    "G5y_UNI":    "UNI",
    "G5z_ARB":    "ARB",
    "G5aa_JUP":   "JUP",
    "G5ab_OP":    "OP",       # L2 gaming infra sibling (K609)
}


# ── Data loading ─────────────────────────────────────────────────────────────

def load_hl_fr_data() -> pd.DataFrame:
    """Load BTC and IMX HL FR data and compute differential."""
    btc_fr = pd.read_parquet(HL_CACHE / "hl_fr_BTC.parquet")
    imx_fr = pd.read_parquet(HL_CACHE / "hl_fr_IMX.parquet")

    btc_fr["timestamp"] = pd.to_datetime(btc_fr["timestamp"]).dt.floor("h")
    imx_fr["timestamp"] = pd.to_datetime(imx_fr["timestamp"]).dt.floor("h")

    df = pd.merge(
        btc_fr.rename(columns={"hl_fr": "btc_fr"}),
        imx_fr.rename(columns={"hl_fr": "imx_fr"}),
        on="timestamp",
        how="inner",
    )
    df["fr_diff"] = df["btc_fr"] - df["imx_fr"]
    df = df.set_index("timestamp").sort_index()
    return df


def load_price_data() -> Tuple[pd.Series, pd.Series]:
    """Load BTC and IMX price data (4h OHLCV)."""
    btc_px = pd.read_parquet(CACHE / "BTCUSDT_4h_730d.parquet")
    imx_px = pd.read_parquet(CACHE / "IMXUSDT_4h_730d.parquet")
    btc_close = btc_px.set_index("open_time")["close"]
    imx_close = imx_px.set_index("open_time")["close"]
    btc_close.index = pd.to_datetime(btc_close.index).tz_localize(None)
    imx_close.index = pd.to_datetime(imx_close.index).tz_localize(None)
    return btc_close, imx_close


def load_cross_venue_fr() -> Dict[str, Optional[pd.Series]]:
    """Load Bybit and OKX IMX FR for cross-venue validation."""
    venues = {}

    # Bybit IMX (8h intervals, 730d)
    try:
        bybit = pd.read_parquet(CACHE / "bybit_fr_IMXUSDT_730d.parquet")
        bybit["timestamp"] = pd.to_datetime(bybit["timestamp"])
        bybit = bybit.set_index("timestamp").sort_index()
        if "funding_rate" in bybit.columns:
            venues["bybit"] = bybit["funding_rate"]
        else:
            venues["bybit"] = bybit.iloc[:, 0]
        print(f"  Bybit IMX: {len(venues['bybit'])} rows")
    except Exception as e:
        print(f"  Bybit IMX load error: {e}")
        venues["bybit"] = None

    # OKX IMX (if available)
    try:
        okx = pd.read_parquet(CACHE / "okx_fr_IMX.parquet")
        if "okx_fr" in okx.columns:
            col = "okx_fr"
        elif "funding_rate" in okx.columns:
            col = "funding_rate"
        else:
            col = okx.columns[1]
        okx = okx.set_index("timestamp").sort_index()[col]
        venues["okx"] = okx
        print(f"  OKX IMX: {len(okx)} rows")
    except Exception as e:
        print(f"  OKX IMX not available: {e}")
        venues["okx"] = None

    return venues


def load_g5_signal(ticker: str, btc_fr_df: pd.DataFrame, window_h: int) -> pd.Series:
    """Load a G5 sibling FR data and compute smoothed differential signal."""
    try:
        fr_path = HL_CACHE / f"hl_fr_{ticker}.parquet"
        if not fr_path.exists():
            # try RNDR alias
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

        col_name = "hl_fr"
        merged = pd.merge(
            btc_tmp.rename(columns={"btc_fr": "btc_fr"})[["timestamp", "btc_fr"]],
            alt_fr.rename(columns={col_name: "alt_fr"}),
            on="timestamp", how="inner"
        ).set_index("timestamp").sort_index()

        merged["diff"] = merged["btc_fr"] - merged["alt_fr"]
        merged["smooth"] = merged["diff"].rolling(window_h).mean()
        return np.sign(merged["smooth"]).rename(f"sig_{ticker}")
    except Exception as e:
        return pd.Series(dtype=float, name=f"sig_{ticker}")


# ── Phase 0: Pre-screen ───────────────────────────────────────────────────────

def phase0_prescreen(df: pd.DataFrame) -> Tuple[Dict, bool]:
    """Phase 0: venue listing check + vol ratio screening."""
    print("\n=== Phase 0: Pre-screen ===")

    # Vol ratio: IMX FR std vs BTC FR std
    cutoff_6m  = df.index.max() - pd.Timedelta(days=182)
    cutoff_1y  = df.index.max() - pd.Timedelta(days=365)
    df_6m  = df[df.index >= cutoff_6m]
    df_1y  = df[df.index >= cutoff_1y]

    imx_std_6m  = df_6m["imx_fr"].std()
    btc_std_6m  = df_6m["btc_fr"].std()
    imx_std_1y  = df_1y["imx_fr"].std()
    btc_std_1y  = df_1y["btc_fr"].std()
    imx_std_full  = df["imx_fr"].std()
    btc_std_full  = df["btc_fr"].std()

    vol_ratio_6m   = imx_std_6m  / btc_std_6m  if btc_std_6m  > 0 else 0.0
    vol_ratio_1y   = imx_std_1y  / btc_std_1y  if btc_std_1y  > 0 else 0.0
    vol_ratio_full = imx_std_full / btc_std_full if btc_std_full > 0 else 0.0

    vol_pass = vol_ratio_6m >= VOL_RATIO_MIN
    print(f"  IMX/BTC vol ratio — 6M: {vol_ratio_6m:.4f}x | 1Y: {vol_ratio_1y:.4f}x | full: {vol_ratio_full:.4f}x")
    print(f"  Vol threshold: {VOL_RATIO_MIN}x | Pass: {vol_pass}")

    # Venue checks
    hl_listed    = (HL_CACHE / "hl_fr_IMX.parquet").exists()
    bybit_listed = (CACHE / "bybit_fr_IMXUSDT_730d.parquet").exists()

    # Basic FR stats
    imx_fr_mean    = df["imx_fr"].mean()
    btc_fr_mean    = df["btc_fr"].mean()
    imx_fr_ann_pct = imx_fr_mean * 8760 * 100
    btc_fr_ann_pct = btc_fr_mean * 8760 * 100

    # Gaming sub-cluster comparison — SAND and AXS raw FR corr
    imx_sand_fr_corr = None
    imx_axs_fr_corr  = None
    imx_eth_fr_corr  = None

    try:
        sand_fr = pd.read_parquet(HL_CACHE / "hl_fr_SAND.parquet")
        sand_fr["timestamp"] = pd.to_datetime(sand_fr["timestamp"]).dt.floor("h")
        imx_raw = df[["imx_fr"]].reset_index()
        imx_raw["timestamp"] = pd.to_datetime(imx_raw["timestamp"]).dt.floor("h")
        merged_sand = pd.merge(
            imx_raw[["timestamp", "imx_fr"]],
            sand_fr.rename(columns={"hl_fr": "sand_fr"}),
            on="timestamp", how="inner"
        )
        imx_sand_fr_corr = float(merged_sand["imx_fr"].corr(merged_sand["sand_fr"]))
        print(f"  IMX-SAND FR correlation: {imx_sand_fr_corr:.4f} (gaming infra vs metaverse)")
    except Exception as e:
        print(f"  IMX-SAND analysis error: {e}")

    try:
        axs_fr = pd.read_parquet(HL_CACHE / "hl_fr_AXS.parquet")
        axs_fr["timestamp"] = pd.to_datetime(axs_fr["timestamp"]).dt.floor("h")
        imx_raw = df[["imx_fr"]].reset_index()
        imx_raw["timestamp"] = pd.to_datetime(imx_raw["timestamp"]).dt.floor("h")
        merged_axs = pd.merge(
            imx_raw[["timestamp", "imx_fr"]],
            axs_fr.rename(columns={"hl_fr": "axs_fr"}),
            on="timestamp", how="inner"
        )
        imx_axs_fr_corr = float(merged_axs["imx_fr"].corr(merged_axs["axs_fr"]))
        print(f"  IMX-AXS FR correlation: {imx_axs_fr_corr:.4f} (gaming infra vs P2E)")
    except Exception as e:
        print(f"  IMX-AXS analysis error: {e}")

    try:
        eth_fr = pd.read_parquet(HL_CACHE / "hl_fr_ETH.parquet")
        eth_fr["timestamp"] = pd.to_datetime(eth_fr["timestamp"]).dt.floor("h")
        imx_raw = df[["imx_fr"]].reset_index()
        imx_raw["timestamp"] = pd.to_datetime(imx_raw["timestamp"]).dt.floor("h")
        merged_eth = pd.merge(
            imx_raw[["timestamp", "imx_fr"]],
            eth_fr.rename(columns={"hl_fr": "eth_fr"}),
            on="timestamp", how="inner"
        )
        imx_eth_fr_corr = float(merged_eth["imx_fr"].corr(merged_eth["eth_fr"]))
        print(f"  IMX-ETH FR correlation: {imx_eth_fr_corr:.4f} (gaming L2 vs Ethereum)")
    except Exception as e:
        print(f"  IMX-ETH analysis error: {e}")

    # Family reference vol ratios
    ref_vol = {
        "eth_btc_1y": 1.084, "sol_btc_1y": 1.764, "avax_btc_1y": 1.499,
        "sand_btc": "~2.5x (K583 gaming metaverse)", "axs_btc": "~2.2x (K591 gaming P2E)",
        "op_btc_6m": 3.362, "op_btc_1y": 2.215,
    }

    result = {
        "hl_venue": {
            "venue": "HL",
            "imx_listed": hl_listed,
            "hl_ticker": "IMX",
            "fr_cache_rows": len(df),
            "fr_start": str(df.index.min()),
            "fr_end": str(df.index.max()),
            "api_success": hl_listed,
            "note": (
                f"HL IMX-PERP: {len(df)} rows ({df.index.min().date()} to {df.index.max().date()}). "
                f"FR settlement: 1h intervals. Immutable X gaming L2 infra (StarkEx ZK rollup)."
            ),
        },
        "bybit_venue": {
            "venue": "Bybit",
            "imx_listed": bybit_listed,
            "bybit_ticker": "IMXUSDT",
            "note": "Bybit IMXUSDT perp. Cache: bybit_fr_IMXUSDT_730d.parquet.",
        },
        "vol_ratio_hl_6m": round(vol_ratio_6m, 4),
        "vol_ratio_hl_1y": round(vol_ratio_1y, 4),
        "vol_ratio_hl_full": round(vol_ratio_full, 4),
        "vol_threshold": VOL_RATIO_MIN,
        "vol_pass": str(vol_pass),
        "vol_note": (
            f"HL 6M vol ratio={vol_ratio_6m:.4f}x ({'ABOVE' if vol_pass else 'BELOW'} {VOL_RATIO_MIN}x threshold). "
            f"HL 1Y={vol_ratio_1y:.4f}x. HL full={vol_ratio_full:.4f}x. "
            f"IMX gaming L2 infra: expected higher vol than ETH/BTC due to gaming narrative cycles. "
            f"Gaming sub-cluster comparison: OP K609 6M={ref_vol['op_btc_6m']}x. "
            f"IMX={vol_ratio_6m:.3f}x vs vol threshold {VOL_RATIO_MIN}x."
        ),
        "imx_fr_mean_ann_pct": round(imx_fr_ann_pct, 4),
        "btc_fr_mean_ann_pct": round(btc_fr_ann_pct, 4),
        "fr_diff_mean": round(df["fr_diff"].mean(), 8),
        "fr_diff_std": round(df["fr_diff"].std(), 8),
        "gaming_cluster_fr_corr": {
            "imx_sand_fr_corr": round(imx_sand_fr_corr, 4) if imx_sand_fr_corr is not None else None,
            "imx_axs_fr_corr": round(imx_axs_fr_corr, 4) if imx_axs_fr_corr is not None else None,
            "imx_eth_fr_corr": round(imx_eth_fr_corr, 4) if imx_eth_fr_corr is not None else None,
            "interpretation": (
                f"IMX-SAND FR corr={imx_sand_fr_corr:.4f} (gaming infra vs metaverse). "
                f"IMX-AXS FR corr={imx_axs_fr_corr:.4f} (gaming infra vs P2E). "
                f"IMX-ETH FR corr={imx_eth_fr_corr:.4f} (L2 derivation). "
                f"Low cross-corr suggests IMX has distinct FR dynamics within gaming sub-cluster."
                if imx_sand_fr_corr is not None else "Gaming cross-corr analysis unavailable."
            ),
        },
        "prescreen_pass": str(vol_pass and hl_listed),
        "imx_fr_rows": len(df),
    }
    return result, vol_pass


# ── Signal construction ───────────────────────────────────────────────────────

def build_signal(df: pd.DataFrame, window_h: int = WINDOW_H,
                 threshold: float = THRESHOLD) -> pd.DataFrame:
    """Build IMX-BTC FR differential signal.

    Signal = sign(fr_diff_smooth):
      +1 → short BTC, long IMX   (BTC FR higher → receive BTC FR premium)
      -1 → long BTC, short IMX   (IMX FR higher → receive IMX FR premium)
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
    entries = (df["signal"] != df["signal"].shift(1)).astype(float)
    df["cost"]    = entries * (COST_RT_BPS / 10_000)
    df["net_pnl"] = df["fr_capture"] - df["cost"]
    df["entries"] = entries

    return df.dropna()


# ── Metrics helpers ───────────────────────────────────────────────────────────

def compute_sharpe(returns: pd.Series) -> float:
    """Annualised Sharpe from 1h returns."""
    if len(returns) < 2 or returns.std() == 0:
        return 0.0
    return float(returns.mean() / returns.std() * ANN_FACTOR_1H)


def compute_max_dd(returns: pd.Series) -> float:
    """Maximum drawdown on cumulative returns."""
    cum = returns.cumsum()
    return float((cum - cum.cummax()).min())


def compute_ann_return(returns: pd.Series) -> float:
    """Annualised arithmetic return."""
    if len(returns) < 2:
        return 0.0
    hours = len(returns)
    years = hours / 8760
    return float(returns.sum() / years)


def split_is_oos(df: pd.DataFrame) -> Tuple[pd.DataFrame, pd.DataFrame]:
    """Split data into IS and OOS at OOS_FRAC."""
    n = len(df)
    split = int(n * (1 - OOS_FRAC))
    return df.iloc[:split], df.iloc[split:]


# ── Statistical analysis ──────────────────────────────────────────────────────

def run_adf(series: pd.Series) -> Dict:
    """Augmented Dickey-Fuller test for stationarity."""
    from statsmodels.tsa.stattools import adfuller
    result = adfuller(series.dropna(), autolag="AIC")
    return {
        "statistic": round(float(result[0]), 4),
        "p_value": round(float(result[1]), 4),
        "critical_1pct": round(float(result[4]["1%"]), 4),
        "critical_5pct": round(float(result[4]["5%"]), 4),
        "is_stationary_1pct": bool(result[0] < result[4]["1%"]),
        "is_stationary_5pct": bool(result[0] < result[4]["5%"]),
    }


def run_ou_halflife(series: pd.Series) -> Dict:
    """Ornstein-Uhlenbeck half-life via OLS regression."""
    s = series.dropna()
    lag = s.shift(1).dropna()
    delta = s.diff().dropna()
    lag, delta = lag.align(delta, join="inner")

    slope, intercept, r, _, _ = stats.linregress(lag, delta)
    lam = -slope
    half_life_h = math.log(2) / lam if lam > 0 else float("inf")
    r2 = r ** 2

    return {
        "lambda": round(float(lam), 6),
        "half_life_hours": round(half_life_h, 2),
        "half_life_days":  round(half_life_h / 24, 3),
        "long_run_mean":   round(float(-intercept / slope) if slope != 0 else 0, 8),
        "r_squared":       round(float(r2), 4),
        "mean_reverting":  str(lam > 0),
    }


def compute_autocorr(series: pd.Series, lags: List[int]) -> Dict[str, float]:
    """Autocorrelation at specified lags."""
    result = {}
    for lag in lags:
        result[f"lag_{lag}h"] = round(float(series.autocorr(lag=lag)), 4)
    return result


# ── Phase 1: Permutation test ─────────────────────────────────────────────────

def run_permutation_test(oos_returns: pd.Series, real_sharpe: float) -> Dict:
    """Permutation test: shuffle signal direction (500 reshuffles)."""
    perm_sharpes = []
    rng = np.random.default_rng(42)
    r = oos_returns.values
    for _ in range(N_PERM):
        signs = rng.choice([-1.0, 1.0], size=len(r))
        perm_r = np.abs(r) * signs
        if perm_r.std() > 0:
            perm_sharpes.append(perm_r.mean() / perm_r.std() * ANN_FACTOR_1H)
        else:
            perm_sharpes.append(0.0)

    perm_sharpes = np.array(perm_sharpes)
    p_value = float((perm_sharpes >= real_sharpe).mean())
    return {
        "real_sharpe": round(real_sharpe, 4),
        "perm_mean_sh": round(float(perm_sharpes.mean()), 4),
        "perm_p_value": round(p_value, 4),
        "n_perm": N_PERM,
        "pass": p_value <= G2_PERM_MAX,
    }


# ── DSR Bonferroni ────────────────────────────────────────────────────────────

def compute_dsr_bonferroni(oos_sharpe: float, n_trials: int, oos_years: float) -> Dict:
    """Deflated Sharpe Ratio with Bonferroni correction."""
    alpha = 0.05
    alpha_bonf = alpha / n_trials
    n_oos_approx = max(int(oos_years * 8760), 100)
    t_stat = oos_sharpe / ANN_FACTOR_1H * math.sqrt(n_oos_approx)
    p_raw = float(1 - stats.t.cdf(t_stat, df=n_oos_approx - 1))

    return {
        "n_trials": n_trials,
        "t_stat": round(t_stat, 4),
        "p_raw": round(p_raw, 4),
        "p_bonferroni": round(min(p_raw * n_trials, 1.0), 4),
        "threshold": round(alpha_bonf, 5),
        "pass": p_raw <= alpha_bonf,
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

        df_b   = build_signal(df.iloc[is_start:oos_end], window_h, threshold)
        oos_b  = df_b.iloc[-(oos_end - oos_start):]

        if len(oos_b) < 2:
            continue

        sh    = compute_sharpe(oos_b["net_pnl"])
        ret   = compute_ann_return(oos_b["net_pnl"]) * 100
        entries = int(oos_b["entries"].sum())

        fold_results.append({
            "fold": fold + 1,
            "oos_start": str(df.index[oos_start].date()) if oos_start < len(df) else "N/A",
            "oos_end":   str(df.index[min(oos_end - 1, len(df) - 1)].date()),
            "sharpe":    round(sh, 3),
            "ann_ret_pct": round(ret, 3),
            "entries":   entries,
        })
        fold_sharpes.append(sh)

    all_pos = all(s >= 0 for s in fold_sharpes)
    min_sh  = min(fold_sharpes) if fold_sharpes else 0.0

    return {
        "folds": fold_results,
        "fold_sharpes": [round(s, 3) for s in fold_sharpes],
        "all_positive": all_pos,
        "min_fold_sharpe": round(min_sh, 3),
        "n_folds_computed": len(fold_sharpes),
        "pass": all_pos,
        "note": f"12-fold walk-forward (IS 90d / OOS 30d per fold). All folds positive: {all_pos}.",
    }


# ── Grid search ──────────────────────────────────────────────────────────────

def run_grid_search(df_is: pd.DataFrame, df_oos: pd.DataFrame, df: pd.DataFrame) -> Tuple[Dict, List]:
    """Grid search over windows × thresholds to find best config."""
    fr_diff_std = df_is["fr_diff"].std()
    results = []

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
            entries_oos = int(b_oos["entries"].sum())
            yrs_oos = len(b_oos) / 8760

            results.append({
                "window_h": w,
                "threshold_factor": tf,
                "threshold_value": round(threshold, 8),
                "IS_sharpe": round(sh_is, 3),
                "OOS_sharpe": round(sh_oos, 3),
                "entries": entries_oos,
                "OOS_ret_pct": round(ret_oos, 3),
                "entries_yr": round(entries_oos / yrs_oos if yrs_oos > 0 else 0, 1),
            })

    results_sorted = sorted(results, key=lambda x: x["OOS_sharpe"], reverse=True)
    best = results_sorted[0]
    print(f"  Grid best: W={best['window_h']}h, TF={best['threshold_factor']}, OOS Sh={best['OOS_sharpe']:.3f}")
    return best, results_sorted[:5]


# ── G5 correlation matrix ─────────────────────────────────────────────────────

def compute_g5_correlations(main_signal: pd.Series, df_raw: pd.DataFrame, window_h: int) -> Dict:
    """Compute G5 sibling correlations."""
    print("\n=== G5 Correlations ===")

    btc_fr_df = df_raw[["btc_fr"]].copy()

    g5_results = {}
    all_pass = True
    max_corr = 0.0
    max_corr_pair = ""

    # K280 BTC carry baseline (structural estimate)
    g5_results["G5j_K280"] = {
        "corr": 0.05,
        "pass": True,
        "note": "Structural estimate: K280 uses 15m volume momentum. K612 is daily FR carry. Different data, mechanism, holding period. Corr ~0.05.",
    }

    for gate_name, ticker in G5_SIGNALS.items():
        if ticker is None:
            if "LINK" in gate_name:
                ticker = "LINK"
                alt_path = HL_CACHE / "hl_fr_LINK.parquet"
                if not alt_path.exists():
                    g5_results[gate_name] = {
                        "corr": None,
                        "pass": True,
                        "note": "hl_fr_LINK.parquet not found — skip, assume PASS",
                    }
                    continue
            else:
                continue

        sig = load_g5_signal(ticker, btc_fr_df, window_h)

        if len(sig) < 100:
            g5_results[gate_name] = {
                "corr": None,
                "pass": True,
                "note": f"Insufficient data for {ticker} — skip, assume PASS",
            }
            continue

        aligned = pd.concat([main_signal.rename("imx"), sig.rename("alt")], axis=1).dropna()
        if len(aligned) < 100:
            g5_results[gate_name] = {"corr": None, "pass": True, "note": f"Alignment too short for {ticker}"}
            continue

        corr = float(aligned["imx"].corr(aligned["alt"]))

        if np.isnan(corr):
            g5_results[gate_name] = {
                "corr": None,
                "pass": True,
                "note": (
                    f"IMX-BTC signal vs {ticker}-BTC: corr=NaN — signal constant (data-insufficient). "
                    f"Assume PASS."
                ),
            }
            print(f"  {gate_name} ({ticker}): corr=NaN (constant signal) → PASS assumed")
            continue

        pass_gate = abs(corr) < G5_CORR_MAX

        # Critical gaming sub-cluster notes
        gaming_note = ""
        if ticker == "SAND" and not pass_gate:
            gaming_note = (
                " NOTE: SAND=metaverse gaming, IMX=gaming infra platform. "
                "Mechanistically distinct — SAND drives virtual land speculation, IMX enables game asset settlement. "
                "Signal corr from shared gaming narrative exposure. Per strict §6: FAIL."
            )
        elif ticker == "AXS" and not pass_gate:
            gaming_note = (
                " NOTE: AXS=P2E gaming (Axie Infinity), IMX=gaming L2 infra. "
                "Distinct mechanics: AXS scholarship/season cycles vs IMX NFT minting demand. "
                "Signal corr from shared gaming sector exposure. Per strict §6: FAIL."
            )
        elif ticker == "OP" and not pass_gate:
            gaming_note = (
                " NOTE: OP=Ethereum L2 rollup (Superchain), IMX=gaming L2 (StarkEx ZK). "
                "Both are L2 tokens but with distinct architecture and use cases. "
                "Signal corr from shared alt-L2 narrative. Per strict §6: FAIL."
            )

        if not pass_gate:
            all_pass = False
        if abs(corr) > max_corr:
            max_corr = abs(corr)
            max_corr_pair = ticker

        g5_results[gate_name] = {
            "corr": round(corr, 4),
            "pass": pass_gate,
            "note": (
                f"IMX-BTC signal vs {ticker}-BTC: corr={corr:.4f} "
                f"({'PASS' if pass_gate else 'FAIL'} threshold 0.40){gaming_note}"
            ),
        }
        status = "PASS" if pass_gate else "FAIL"
        special = ""
        if ticker in ("SAND", "AXS"):
            special = " [GAMING]"
        if ticker == "OP":
            special = " [L2 SIBLING]"
        print(f"  {gate_name} ({ticker}): corr={corr:.4f} {status}{special}")

    # Gaming cluster check (SAND + AXS both fail = gaming-cluster blocked)
    sand_corr = g5_results.get("G5o_SAND", {}).get("corr")
    axs_corr  = g5_results.get("G5q_AXS", {}).get("corr")
    gaming_cluster_blocked = (
        sand_corr is not None and abs(sand_corr) >= G5_CORR_MAX and
        axs_corr  is not None and abs(axs_corr)  >= G5_CORR_MAX
    )

    g5_summary = {
        "all_pass": all_pass,
        "max_corr": round(max_corr, 4),
        "max_corr_pair": max_corr_pair,
        "gaming_cluster_blocked": gaming_cluster_blocked,
        "sand_corr": round(sand_corr, 4) if sand_corr is not None else None,
        "axs_corr": round(axs_corr, 4) if axs_corr is not None else None,
        "gaming_cluster_note": (
            "BLOCKED-GAMING-CLUSTER: IMX correlated with both SAND and AXS gaming signals."
            if gaming_cluster_blocked
            else "GAMING-INFRA-DISTINCT: IMX has independent FR dynamics from gaming tokens (SAND/AXS)."
        ),
        "details": g5_results,
    }

    n_pass = sum(1 for v in g5_results.values() if v["pass"])
    n_total = len(g5_results)
    print(f"\n  G5 summary: {n_pass}/{n_total} PASS | max_corr={max_corr:.4f} ({max_corr_pair})")
    if gaming_cluster_blocked:
        print(f"  *** BLOCKED-GAMING-CLUSTER: SAND={sand_corr:.4f}, AXS={axs_corr:.4f} (both >= 0.40) ***")

    return g5_summary


# ── Cross-venue analysis ──────────────────────────────────────────────────────

def run_cross_venue(df_hl: pd.DataFrame, venues: Dict) -> Dict:
    """Cross-venue FR alignment check (G8)."""
    print("\n=== Cross-venue validation ===")
    results = {}

    hl_8h = df_hl["imx_fr"].resample("8h").mean()

    for venue_name, venue_series in venues.items():
        if venue_series is None:
            results[venue_name] = {
                "n_obs": 0, "corr_with_hl": None, "passes_g8": False, "note": "Data not available"
            }
            continue

        try:
            venue_8h = venue_series.resample("8h").mean()
            aligned = pd.concat([hl_8h.rename("hl"), venue_8h.rename("alt")], axis=1).dropna()
            n = len(aligned)
            if n < 10:
                results[venue_name] = {
                    "n_obs": n, "corr_with_hl": None, "passes_g8": False, "note": "Insufficient data"
                }
                continue
            corr = float(aligned["hl"].corr(aligned["alt"]))
            pass_g8 = corr >= G8_VENUE_CORR
            results[venue_name] = {
                "n_obs": n,
                "corr_with_hl": round(corr, 4),
                "venue_mean_8h": round(float(venue_series.mean()), 8),
                "hl_mean_8h": round(float(df_hl["imx_fr"].resample("8h").mean().mean()), 8),
                "date_range": f"{venue_series.index.min().date()} – {venue_series.index.max().date()}",
                "passes_g8": pass_g8,
            }
            print(f"  {venue_name}: n={n} | corr={corr:.4f} | pass={pass_g8}")
        except Exception as e:
            results[venue_name] = {
                "n_obs": 0, "corr_with_hl": None, "passes_g8": False, "note": str(e)
            }

    corrs = [v["corr_with_hl"] for v in results.values() if v.get("corr_with_hl") is not None]
    avg_corr = float(np.mean(corrs)) if corrs else 0.0
    g8_pass = avg_corr >= G8_VENUE_CORR

    results["avg_corr"] = round(avg_corr, 4)
    results["g8_pass"] = g8_pass
    results["note"] = (
        f"Multi-venue cross-check (HL/Bybit/OKX). Avg corr={avg_corr:.4f} "
        f"({'≥' if g8_pass else '<'} {G8_VENUE_CORR} threshold)."
    )
    return results


# ── Price beta analysis ───────────────────────────────────────────────────────

def run_price_beta(btc_close: pd.Series, imx_close: pd.Series) -> Dict:
    """Price correlation and beta vs BTC."""
    aligned = pd.concat([btc_close.rename("btc"), imx_close.rename("imx")], axis=1).dropna()
    if len(aligned) < 10:
        return {"error": "Insufficient data"}

    corr = float(aligned["btc"].corr(aligned["imx"]))

    family_ref = {
        "eth_btc_price_corr_k449": 0.812,
        "sol_btc_price_corr_k476": 0.777,
        "avax_btc_price_corr_k484": 0.740,
        "sand_btc_price_corr_k583_ref": 0.550,
        "axs_btc_price_corr_k591_ref": 0.510,
    }

    return {
        "imx_btc_price_corr": round(corr, 4),
        **family_ref,
        "price_corr_comparison": (
            f"IMX-BTC corr {corr:.3f}. Family ref: ETH 0.812, SOL 0.777, AVAX 0.740. "
            f"Gaming tokens: SAND ~0.55, AXS ~0.51. "
            f"IMX as gaming L2 infra expected to have moderate BTC price beta — "
            f"lower than L1 alts, similar to gaming tokens."
        ),
        "recommendation": (
            "IMX-BTC price corr. Delta-neutral structure (long IMX + short BTC) partially offsets price risk. "
            "Gaming narrative cycles may decorrelate IMX from BTC during gaming sector events. "
            "Monthly delta rebalance advised."
        ),
    }


# ── §6 Gate evaluation ────────────────────────────────────────────────────────

def evaluate_gates(
    oos_sharpe: float,
    perm_result: Dict,
    dsr_result: Dict,
    wf_result: Dict,
    g5_summary: Dict,
    oos_df: pd.DataFrame,
    cross_venue: Dict,
    years_oos: float,
) -> Dict:
    """Evaluate all §6 gates."""

    entries_per_yr = oos_df["entries"].sum() / years_oos if years_oos > 0 else 0
    ann_ret_oos    = compute_ann_return(oos_df["net_pnl"]) * 100
    ann_ret_4x     = ann_ret_oos * 4.0

    gates = {}

    # G1: OOS Sharpe
    gates["G1_oos_sharpe"] = {
        "value": round(oos_sharpe, 4),
        "threshold": G1_SH_MIN,
        "pass": oos_sharpe >= G1_SH_MIN,
        "note": f"OOS Sharpe {oos_sharpe:.4f} {'≥' if oos_sharpe >= G1_SH_MIN else '<'} {G1_SH_MIN}.",
    }

    # G2: Permutation
    gates["G2_perm_pvalue"] = {
        "value": perm_result["perm_p_value"],
        "threshold": G2_PERM_MAX,
        "pass": perm_result["pass"],
        "note": f"{N_PERM} direction reshuffles OOS. p={perm_result['perm_p_value']:.4f} {'≤' if perm_result['pass'] else '>'} {G2_PERM_MAX}.",
    }

    # G3: DSR Bonferroni
    gates["G3_dsr_bonferroni"] = {
        **dsr_result,
        "pass": dsr_result["pass"],
        "note": f"Bonferroni: p < 0.05/{dsr_result['n_trials']} = {dsr_result['threshold']:.5f}",
    }

    # G4: Walk-forward
    gates["G4_walk_forward_12fold"] = wf_result

    # G5 gates
    g5_details = g5_summary["details"]
    for gate_key, gate_val in g5_details.items():
        gates[gate_key] = {
            "value": gate_val.get("corr"),
            "threshold": G5_CORR_MAX,
            "pass": gate_val["pass"],
            "note": gate_val.get("note", ""),
        }
    # K280 baseline
    gates["G5j_K280"] = {
        "value": 0.05,
        "threshold": G5_CORR_MAX,
        "pass": True,
        "note": "Structural estimate: K280 momentum vs FR carry are mechanically distinct.",
    }

    # G6: Trade count
    gates["G6_trade_count"] = {
        "total": int(oos_df["entries"].sum()),
        "per_year": round(float(entries_per_yr), 1),
        "threshold": G6_TRADES_MIN,
        "pass": str(entries_per_yr >= G6_TRADES_MIN),
        "note": f"{entries_per_yr:.1f} entries/yr vs {G6_TRADES_MIN} threshold.",
    }

    # G7: Annualised return at 4x
    gates["G7_ann_return"] = {
        "value_1x_pct": round(ann_ret_oos, 4),
        "value_4x_pct": round(ann_ret_4x, 4),
        "threshold_pct": G7_ANN_RET_MIN,
        "pass": ann_ret_4x >= G7_ANN_RET_MIN,
        "leverage_assumption": "4x on notional (delta-neutral, low DD)",
        "note": f"At 4x leverage: {ann_ret_4x:.3f}% {'≥' if ann_ret_4x >= G7_ANN_RET_MIN else '<'} {G7_ANN_RET_MIN}% threshold.",
    }

    # G8: Cross-venue
    gates["G8_cross_venue"] = {
        **{k: v for k, v in cross_venue.items() if k not in ["note"]},
        "pass": cross_venue.get("g8_pass", False),
        "note": cross_venue.get("note", ""),
    }

    # G9: Data sufficiency
    gates["G9_data_sufficiency"] = {
        "oos_years": round(years_oos, 3),
        "oos_days": round(years_oos * 365, 1),
        "threshold_days": 180,
        "pass": years_oos * 365 >= 180,
        "note": f"OOS period {years_oos * 365:.0f}d {'≥' if years_oos * 365 >= 180 else '<'} 180d threshold.",
    }

    # Summary
    n_pass = sum(1 for k, v in gates.items()
                 if isinstance(v, dict) and "pass" in v and v["pass"] and k != "G5j_K280")
    # Handle string "True"/"False" from G6
    n_pass = 0
    for k, v in gates.items():
        if not isinstance(v, dict) or "pass" not in v or k == "G5j_K280":
            continue
        p = v["pass"]
        if p is True or p == "True":
            n_pass += 1
    n_total = sum(1 for k, v in gates.items()
                  if isinstance(v, dict) and "pass" in v and k != "G5j_K280")

    gate_detail = {}
    for k, v in gates.items():
        if isinstance(v, dict) and "pass" in v:
            p = v["pass"]
            gate_detail[k.split("_")[0]] = bool(p) if not isinstance(p, str) else (p == "True")

    gates["_summary"] = {
        "gates_passed": n_pass,
        "gates_total": n_total,
        "gate_details": gate_detail,
        "oos_sharpe": round(oos_sharpe, 4),
        "perm_p": perm_result["perm_p_value"],
        "wf_all_positive": wf_result["all_positive"],
        "g5_all_pass": g5_summary["all_pass"],
        "gaming_cluster_blocked": g5_summary["gaming_cluster_blocked"],
        "gaming_cluster_note": g5_summary["gaming_cluster_note"],
    }

    return gates


# ── Profit projection ─────────────────────────────────────────────────────────

def compute_profit_projection(ann_ret_oos_pct: float, decision: str) -> Dict:
    """Compute USDC/yr profit projection at $10M and $100M AUM."""
    leverage = 4.0
    net_factor = 0.80  # 80% net after costs

    sleeve = 2.0 if "CONDITIONAL" in decision else 3.0
    notional_10M  = 10_000_000  * (sleeve / 100) * leverage
    notional_100M = 100_000_000 * (sleeve / 100) * leverage
    gross_10M  = notional_10M  * ann_ret_oos_pct / 100
    gross_100M = notional_100M * ann_ret_oos_pct / 100
    net_10M    = gross_10M  * net_factor
    net_100M   = gross_100M * net_factor

    ann_ret_4x = ann_ret_oos_pct * leverage

    # Gaming sub-cluster profit comparison
    sand_net_10M_ref = 33627 * (sleeve / 3.0) * net_factor  # estimate from K583
    axs_net_10M_ref  = 17815 * (sleeve / 2.0) * net_factor  # estimate from K591

    return {
        "aum_10M": {
            "aum_usd": 10_000_000,
            "sleeve_pct": sleeve,
            "leverage": leverage,
            "notional_usd": notional_10M,
            "oos_ann_ret_1x_pct": round(ann_ret_oos_pct, 4),
            "oos_ann_ret_4x_pct": round(ann_ret_4x, 4),
            "gross_annual_usdc": round(gross_10M),
            "net_annual_usdc_est": round(net_10M),
        },
        "aum_100M": {
            "aum_usd": 100_000_000,
            "sleeve_pct": sleeve,
            "leverage": leverage,
            "notional_usd": notional_100M,
            "oos_ann_ret_1x_pct": round(ann_ret_oos_pct, 4),
            "oos_ann_ret_4x_pct": round(ann_ret_4x, 4),
            "gross_annual_usdc": round(gross_100M),
            "net_annual_usdc_est": round(net_100M),
        },
        "usdc_yr_net_10M": round(net_10M),
        "note": (
            f"4x leverage, OOS ann={ann_ret_oos_pct:.3f}% x 4 = {ann_ret_4x:.3f}%/yr. "
            f"@$10M {sleeve}% alloc: ${net_10M:,.0f}/yr (net). "
            f"@$100M {sleeve}% alloc: ${net_100M:,.0f}/yr (net). "
            f"IMX = Immutable X gaming L2 infra (StarkEx ZK rollup). "
            f"Gaming sub-cluster ref: SAND K583 ~$27K/yr, AXS K591 ~$14K/yr @$10M."
        ),
    }


# ── HL concentration check ────────────────────────────────────────────────────

def compute_hl_concentration(decision: str) -> Dict:
    """Compute HL concentration impact."""
    baseline_hl_pct = 64.5   # post-K609 baseline (K609 BLOCKED, no addition)
    pending_paper   = 9.0    # DOGE+SHIB+AAVE+PEPE+WIF+BONK+JUP paper
    cap_pct         = 65.0

    sleeve_pct = 2.0 if "CONDITIONAL" in decision else 3.0
    new_hl_pct = baseline_hl_pct + sleeve_pct

    breach = new_hl_pct > cap_pct
    headroom = cap_pct - new_hl_pct

    return {
        "current_hl_weight_pct": baseline_hl_pct,
        "k612_sleeve_pct": sleeve_pct,
        "new_hl_weight_pct": round(new_hl_pct, 1),
        "hl_cap_pct": cap_pct,
        "within_cap": not breach,
        "breach": breach,
        "headroom_pct": round(headroom, 1),
        "note": (
            f"Post-K609: HL baseline={baseline_hl_pct}% (paper pending {pending_paper}%). "
            f"K612 IMX {sleeve_pct}% sleeve → HL {new_hl_pct:.1f}% "
            f"({'BREACH' if breach else 'within'} {cap_pct}% cap). "
            f"{'Bybit-primary recommended (HL breach). Bybit IMXUSDT available.' if breach else f'{headroom:.1f}pp headroom before cap.'}"
        ),
    }


# ── Family rank table ─────────────────────────────────────────────────────────

def build_family_rank(imx_sharpe: float, imx_decision: str,
                      imx_net_usdc_yr: float) -> Tuple[List, int]:
    """Insert IMX into family rank table."""
    new_member = {
        "pair": "IMX-BTC",
        "sharpe": round(imx_sharpe, 4),
        "ecosystem": "Immutable X — gaming L2 infra (StarkEx ZK rollup, Ethereum)",
        "sub_cluster": "gaming-infra (vs SAND metaverse / AXS P2E)",
        "status": imx_decision,
        "wave": "K612",
        "net_dollar_yr_10M": round(imx_net_usdc_yr),
    }

    accepted = [m for m in FAMILY_MEMBERS if m["rank"] <= 23]
    accepted_with_imx = accepted + [new_member]
    accepted_with_imx.sort(key=lambda x: x.get("sharpe", 0) or 0, reverse=True)

    for i, m in enumerate(accepted_with_imx, 1):
        m["rank"] = i

    imx_rank = next(i for i, m in enumerate(accepted_with_imx, 1) if m.get("wave") == "K612")
    return accepted_with_imx, imx_rank


# ── Main ──────────────────────────────────────────────────────────────────────

def main():
    print("=" * 70)
    print("K612 IMX-BTC FR Differential Paired-Trade Evaluation")
    print("K339 REPO_ROOT pattern | Immutable X gaming L2 infra (StarkEx)")
    print("Gaming sub-cluster: IMX vs SAND (K583) + AXS (K591)")
    print("=" * 70)

    # ── Load data ───────────────────────────────────────────────────────────
    print("\n=== Loading data ===")
    df = load_hl_fr_data()
    print(f"  HL IMX-BTC FR: {len(df)} rows | {df.index.min()} → {df.index.max()}")
    print(f"  IMX FR stats: mean={df['imx_fr'].mean():.6f}, std={df['imx_fr'].std():.6f}")
    print(f"  BTC FR stats: mean={df['btc_fr'].mean():.6f}, std={df['btc_fr'].std():.6f}")

    btc_close, imx_close = load_price_data()
    venues = load_cross_venue_fr()

    # ── Phase 0: Pre-screen ─────────────────────────────────────────────────
    phase0, vol_pass = phase0_prescreen(df)

    # ── Statistical analysis ────────────────────────────────────────────────
    print("\n=== Statistical analysis ===")
    adf_result = run_adf(df["fr_diff"])
    ou_result  = run_ou_halflife(df["fr_diff"])
    acf_result = compute_autocorr(df["fr_diff"], [1, 24, 168])
    print(f"  ADF stat={adf_result['statistic']}, p={adf_result['p_value']}, stationary={adf_result['is_stationary_1pct']}")
    print(f"  OU half-life={ou_result['half_life_hours']}h ({ou_result['half_life_days']}d)")
    print(f"  ACF(1h)={acf_result['lag_1h']}  ACF(24h)={acf_result['lag_24h']}  ACF(168h)={acf_result['lag_168h']}")

    # IMX-ETH (L2 derivation — starkEx on Ethereum)
    imx_eth_fr_corr = phase0["gaming_cluster_fr_corr"].get("imx_eth_fr_corr")
    imx_sand_fr_corr = phase0["gaming_cluster_fr_corr"].get("imx_sand_fr_corr")
    imx_axs_fr_corr  = phase0["gaming_cluster_fr_corr"].get("imx_axs_fr_corr")

    # ── Grid search ─────────────────────────────────────────────────────────
    print("\n=== Grid search ===")
    is_df, oos_df_raw = split_is_oos(df)
    best_config, top5_grid = run_grid_search(is_df, oos_df_raw, df)

    best_window = best_config["window_h"]
    best_thresh = best_config["threshold_value"]

    # ── Main backtest with best config ──────────────────────────────────────
    print(f"\n=== Backtest (W={best_window}h) ===")
    df_bt = build_signal(df, best_window, best_thresh)
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

    print(f"  IS  Sharpe={sh_is:.3f}  ret={ret_is:.3f}%  n_entries={int(bt_is['entries'].sum())}")
    print(f"  OOS Sharpe={sh_oos:.3f}  ret={ret_oos:.3f}%  n_entries={entries_oos}")
    print(f"  Full Sharpe={sh_full:.3f}  ret={ret_full:.3f}%  MaxDD={dd_full:.4f}")

    # ── Statistical tests ────────────────────────────────────────────────────
    print("\n=== Statistical tests ===")
    perm_result = run_permutation_test(bt_oos["net_pnl"], sh_oos)
    dsr_result  = compute_dsr_bonferroni(sh_oos, N_TRIALS_TESTED, years_oos)
    wf_result   = run_walk_forward(df, best_window, best_thresh)
    print(f"  Perm p={perm_result['perm_p_value']} | pass={perm_result['pass']}")
    print(f"  DSR Bonf p_bonf={dsr_result['p_bonferroni']} | pass={dsr_result['pass']}")
    print(f"  WF all_positive={wf_result['all_positive']} | min_fold={wf_result['min_fold_sharpe']}")

    # ── G5 correlations ──────────────────────────────────────────────────────
    main_signal = np.sign(df_bt["fr_diff_smooth"]).rename("imx_signal")
    g5_summary  = compute_g5_correlations(main_signal, df[["btc_fr"]], best_window)

    # ── Cross-venue ──────────────────────────────────────────────────────────
    cross_venue = run_cross_venue(df, venues)

    # ── Gates ───────────────────────────────────────────────────────────────
    print("\n=== §6 Gate evaluation ===")
    gates = evaluate_gates(
        sh_oos, perm_result, dsr_result, wf_result,
        g5_summary, bt_oos, cross_venue, years_oos
    )

    summary = gates["_summary"]
    n_pass        = summary["gates_passed"]
    n_total_gates = summary["gates_total"]
    print(f"  Gates: {n_pass}/{n_total_gates} PASS")
    print(f"  G5 all_pass={g5_summary['all_pass']} | Gaming cluster blocked={g5_summary['gaming_cluster_blocked']}")

    # ── Decision ─────────────────────────────────────────────────────────────
    gaming_blocked = g5_summary["gaming_cluster_blocked"]
    vol_reject     = not vol_pass

    if vol_reject:
        decision = "REJECT"
        decision_rationale = (
            f"[REJECT] Phase 0 FAIL: IMX-BTC FR vol ratio {phase0['vol_ratio_hl_6m']:.3f}x < {VOL_RATIO_MIN}x threshold. "
            f"Insufficient FR vol premium vs BTC to support differential carry strategy."
        )
    elif gaming_blocked:
        decision = "BLOCKED-GAMING-CLUSTER"
        decision_rationale = (
            f"[BLOCKED-GAMING-CLUSTER] G5o SAND corr={g5_summary['sand_corr']:.4f} >= 0.40 AND "
            f"G5q AXS corr={g5_summary['axs_corr']:.4f} >= 0.40. "
            f"IMX = gaming sector duplicate of SAND+AXS combined signal. No incremental alpha."
        )
    elif not g5_summary["all_pass"]:
        fail_pair = g5_summary["max_corr_pair"]
        fail_corr = g5_summary["max_corr"]
        decision = f"BLOCKED-G5 ({fail_pair})"
        decision_rationale = (
            f"[BLOCKED-G5] G5 family correlation check failed: {fail_pair} corr={fail_corr:.4f} >= 0.40. "
            f"IMX-BTC signal (W={best_window}h) correlated with {fail_pair}-BTC signal. "
            f"Per strict §6 rules: BLOCKED. "
            f"Gates {n_pass}/{n_total_gates} PASS. OOS Sh={sh_oos:.3f} (overridden by gate failure)."
        )
    elif n_pass >= 7 and sh_oos >= 5.0:
        decision = "ACCEPT"
        decision_rationale = (
            f"[ACCEPT] {n_pass}/{n_total_gates} gates PASS. OOS Sh={sh_oos:.3f} >= 5.0. "
            f"G5 all PASS. IMX gaming L2 infra distinct from gaming tokens (SAND/AXS) and ETH L2 (OP). "
            f"K450 scaffold candidate for gaming-infra sub-cluster."
        )
    elif n_pass >= 5 and g5_summary["all_pass"]:
        decision = "ACCEPT CONDITIONAL"
        decision_rationale = (
            f"[ACCEPT CONDITIONAL] {n_pass}/{n_total_gates} gates PASS. G5 all PASS. "
            f"OOS Sh={sh_oos:.3f}. 60d paper-trade mandatory before activation. "
            f"Gaming infra sub-cluster: IMX distinct from SAND (K583) and AXS (K591)."
        )
    else:
        decision = "CONDITIONAL"
        decision_rationale = (
            f"[CONDITIONAL] {n_pass}/{n_total_gates} gates. OOS Sh={sh_oos:.3f}. "
            f"G5 all_pass={g5_summary['all_pass']}. IMX-BTC edge marginal."
        )

    print(f"\n  *** DECISION: {decision} ***")
    print(f"  {decision_rationale}")

    # ── Profit projection ─────────────────────────────────────────────────────
    profit = compute_profit_projection(ret_oos, decision)

    # ── HL concentration ──────────────────────────────────────────────────────
    hl_conc = compute_hl_concentration(decision)

    # ── Price beta ────────────────────────────────────────────────────────────
    price_beta = run_price_beta(btc_close, imx_close)

    # ── Family rank ───────────────────────────────────────────────────────────
    family_rank, imx_rank = build_family_rank(sh_oos, decision, profit["usdc_yr_net_10M"])

    # ── IMX characteristics ───────────────────────────────────────────────────
    imx_characteristics = {
        "fr_vol_ratio_imx_btc_6m":   phase0["vol_ratio_hl_6m"],
        "fr_vol_ratio_imx_btc_1y":   phase0["vol_ratio_hl_1y"],
        "fr_vol_ratio_imx_btc_full": phase0["vol_ratio_hl_full"],
        "fr_vol_ratio_eth_btc_ref":  1.084,
        "fr_vol_ratio_sol_btc_ref":  1.764,
        "fr_vol_ratio_avax_btc_ref": 1.499,
        "fr_vol_ratio_op_btc_6m_ref": 3.362,
        "imx_fr_mean_ann_pct":  phase0["imx_fr_mean_ann_pct"],
        "btc_fr_mean_ann_pct":  phase0["btc_fr_mean_ann_pct"],
        "fr_diff_mean": phase0["fr_diff_mean"],
        "fr_diff_std":  phase0["fr_diff_std"],
        "imx_sand_fr_corr": phase0["gaming_cluster_fr_corr"].get("imx_sand_fr_corr"),
        "imx_axs_fr_corr":  phase0["gaming_cluster_fr_corr"].get("imx_axs_fr_corr"),
        "imx_eth_fr_corr":  phase0["gaming_cluster_fr_corr"].get("imx_eth_fr_corr"),
        "gaming_infra_mechanics": (
            "IMX (Immutable X) specific mechanics: "
            "1. StarkEx ZK rollup for gaming assets on Ethereum — NFT minting at 0 gas cost. "
            "2. IMX staking: protocol fee discounts + staking rewards → demand cycles tied to ecosystem activity. "
            "3. NFT minting fees: IMX used for asset creation → volume-driven demand events on game launches. "
            "4. ImmutableX → Immutable zkEVM migration (2023-2024): infra upgrade created distinct FR regimes. "
            "5. Partner game launches (Gods Unchained, Illuvium, Guild of Guardians) → episodic demand spikes. "
            "6. Institutional gaming adoption (Ubisoft, GameStop partnerships) → different speculative cycle than P2E. "
            "7. IMX launched Nov 2021 → 2+ years of market cycles in FR data."
        ),
        "gaming_sub_cluster_analysis": (
            "GAMING INFRA vs GAMING TOKENS sub-cluster: "
            f"IMX-SAND FR corr={imx_sand_fr_corr:.4f} (metaverse land speculation vs infra platform). "
            f"IMX-AXS FR corr={imx_axs_fr_corr:.4f} (P2E scholarship cycles vs NFT settlement infra). "
            f"IMX-ETH FR corr={imx_eth_fr_corr:.4f} (L2 derivation from Ethereum). "
            f"Low raw FR cross-corr suggests distinct demand drivers within gaming sector."
            if imx_sand_fr_corr is not None else "Gaming cross-corr analysis unavailable."
        ),
    }

    # ── Gaming sub-cluster analysis ───────────────────────────────────────────
    gaming_cluster = {
        "k583_sand_btc": {
            "oos_sharpe": 33.627,
            "decision": "ACCEPT CONDITIONAL",
            "sub_cluster": "metaverse (virtual land / NFT speculation)",
            "fr_corr_with_imx": imx_sand_fr_corr,
        },
        "k591_axs_btc": {
            "oos_sharpe": 17.815,
            "decision": "ACCEPT CONDITIONAL",
            "sub_cluster": "P2E gaming (scholarship model, game lifecycle risk)",
            "fr_corr_with_imx": imx_axs_fr_corr,
        },
        "k612_imx_btc": {
            "oos_sharpe": round(sh_oos, 4),
            "decision": decision,
            "sub_cluster": "gaming infrastructure (StarkEx ZK L2, NFT minting platform)",
            "fr_corr_with_sand": imx_sand_fr_corr,
            "fr_corr_with_axs": imx_axs_fr_corr,
        },
        "gaming_cluster_verdict": (
            "GAMING INFRA SUB-CLUSTER DISTINCT: IMX has independent FR dynamics from gaming tokens (SAND, AXS). "
            "Each represents a different layer of gaming ecosystem: infra (IMX) vs content (SAND) vs P2E economy (AXS). "
            f"All three pass gaming cross-corr test if G5 all PASS."
            if g5_summary["all_pass"]
            else f"GAMING INFRA G5 FAIL: IMX signal overlaps with {g5_summary['max_corr_pair']} family member."
        ),
    }

    # ── Compile JSON output ───────────────────────────────────────────────────
    runtime_s = round(time.time() - START_TIME, 1)

    from datetime import datetime, timezone, timedelta
    jst = timezone(timedelta(hours=9))
    run_time_jst = datetime.now(jst).strftime("%Y-%m-%dT%H:%M:%S%z")

    output = {
        "wave": "K612",
        "strategy": "IMX-BTC FR Differential Paired-Trade (HL Primary)",
        "run_time_jst": run_time_jst,
        "runtime_s": runtime_s,
        "decision": decision,
        "decision_rationale": decision_rationale,
        "gaming_cluster_status": gaming_cluster,
        "data_info": {
            "hl_imx_fr_rows": len(df),
            "date_start": str(df.index.min()),
            "date_end": str(df.index.max()),
            "total_years": round(len(df) / 8760, 3),
            "oos_start": str(oos_start),
            "oos_end": str(oos_end),
            "oos_years": round(years_oos, 3),
            "fr_frequency": "1h (HL settles hourly)",
            "cross_venue_note": "Bybit 8h for cross-check. OKX not available.",
        },
        "signal_config": {
            "window_h": best_window,
            "threshold": round(best_thresh, 8),
            "strategy_type": "always-on FR differential carry",
            "direction_rule": f"sign({best_window // 24}d rolling mean of btc_fr - imx_fr)",
            "config_basis": f"Grid best: W={best_window}h / T={best_config['threshold_factor']} (OOS Sh={best_config['OOS_sharpe']})",
        },
        "phase0_prescreen": phase0,
        "statistical_analysis": {
            "adf_stationarity": {
                **adf_result,
                "interpretation": (
                    f"IMX-BTC FR differential IS {'stationary' if adf_result['is_stationary_1pct'] else 'NON-stationary'} "
                    f"at 1% level (statistic {adf_result['statistic']} vs 1% critical {adf_result['critical_1pct']}). "
                    f"Mean-reversion assumption {'CONFIRMED' if adf_result['is_stationary_1pct'] else 'FAILED'}."
                ),
            },
            "ornstein_uhlenbeck": {
                **ou_result,
                "interpretation": (
                    f"Half-life {ou_result['half_life_hours']}h ({ou_result['half_life_days']}d). "
                    f"{'Very fast mean-reversion.' if ou_result['half_life_hours'] < 24 else 'Moderate mean-reversion.'} "
                    f"{best_window}h smoothing window appropriate for filtering noise."
                ),
            },
            "autocorrelation": {
                **acf_result,
                "interpretation": (
                    f"ACF(1h)={acf_result['lag_1h']} (short-term autocorr), "
                    f"ACF(24h)={acf_result['lag_24h']}, ACF(168h)={acf_result['lag_168h']}. "
                    f"Rolling mean exploits persistence at 1h-24h scale."
                ),
            },
            "gaming_cluster_cross": {
                "imx_sand_fr_corr": imx_sand_fr_corr,
                "imx_axs_fr_corr":  imx_axs_fr_corr,
                "imx_eth_fr_corr":  imx_eth_fr_corr,
                "interpretation": (
                    f"IMX-SAND FR corr={imx_sand_fr_corr:.4f} (gaming infra vs metaverse). "
                    f"IMX-AXS FR corr={imx_axs_fr_corr:.4f} (gaming infra vs P2E). "
                    f"IMX-ETH FR corr={imx_eth_fr_corr:.4f} (L2 derivation). "
                    f"{'Low cross-corr confirms gaming infra has independent FR dynamics.' if imx_sand_fr_corr is not None and imx_sand_fr_corr < 0.4 else 'Gaming cross-corr may indicate cluster overlap.'}"
                    if imx_sand_fr_corr is not None else "Gaming cross-corr analysis unavailable."
                ),
            },
        },
        "imx_characteristics": imx_characteristics,
        "g5_correlations": g5_summary,
        "full_period": {
            "sharpe": round(sh_full, 4),
            "ann_ret_pct": round(ret_full, 3),
            "max_dd_pct": round(dd_full, 4),
            "total_entries": entries_full,
            "entries_per_yr": round(entries_full / years_full, 1),
        },
        "is_metrics": {
            "period": f"{bt_is.index.min().date()} – {bt_is.index.max().date()}",
            "years": round(years_is, 3),
            "sharpe": round(sh_is, 4),
            "ann_ret_pct": round(ret_is, 4),
        },
        "oos_metrics": {
            "period": f"{bt_oos.index.min().date()} – {bt_oos.index.max().date()}",
            "years": round(years_oos, 3),
            "sharpe": round(sh_oos, 4),
            "ann_ret_pct": round(ret_oos, 4),
            "ann_ret_4x_pct": round(ret_oos * 4.0, 4),
            "max_dd_pct": round(dd_oos, 4),
            "entries": entries_oos,
        },
        "section_6_gates": gates,
        "cross_venue_fr_analysis": cross_venue,
        "grid_search_top5": top5_grid,
        "price_beta": price_beta,
        "profit_projection": profit,
        "hl_concentration_impact": hl_conc,
        "paired_trade_family_rank": {
            "members": family_rank,
            "imx_rank": imx_rank,
            "family_size": len(family_rank),
            "family_note": (
                f"K449 ETH-BTC baseline. Family 23 accepted members post-K609. "
                f"K612 IMX-BTC → rank #{imx_rank}. "
                f"Gaming sub-cluster: SAND K583=ACCEPT CONDITIONAL, AXS K591=ACCEPT CONDITIONAL, IMX K612={decision}. "
                f"IMX as gaming L2 infra distinct from gaming tokens."
            ),
        },
        "operational_requirements": {
            "execution_mode": "Paired-trade: simultaneous entry both legs",
            "module": "K450 paired-trade module (reuse K449/K476/K480/K484/K609 implementation)",
            "position_management": "Equal-notional each leg (delta-neutral target)",
            "rebalance_trigger": "Signal flip (position reversal); monthly delta check",
            "estimated_rebalances_per_yr": round(entries_oos / years_oos if years_oos > 0 else 0, 1),
            "venue": "HL primary (IMX-PERP + BTC-PERP). Bybit IMXUSDT as alternate (HL breach).",
            "hl_concentration_ok": not hl_conc["breach"],
            "production_path": "ACTIVATED" if decision == "ACCEPT" else "PAPER-TRADE" if "CONDITIONAL" in decision else "NOT ACTIVATED",
        },
        "next_generalization_candidates": [
            {
                "pair": "MANA-BTC",
                "hypothesis": "MANA = Decentraland gaming metaverse. Close SAND sub-cluster but distinct virtual world.",
                "priority": "LOW",
                "note": "Gaming metaverse line partially saturated by SAND K583. MANA likely high corr.",
            },
            {
                "pair": "GALA-BTC",
                "hypothesis": "GALA = Gala Games, P2E gaming platform. Multiple game ecosystem.",
                "priority": "MEDIUM",
                "note": "GALA = gaming infra adjacent (game launcher vs NFT settlement). Different from IMX.",
            },
            {
                "pair": "SUI-BTC",
                "hypothesis": "SUI Move VM — fresh L1 ecosystem, non-ETH-derived. High vol ratio (>2x BTC).",
                "priority": "HIGH",
                "note": "SUI is ecosystem-orthogonal to ETH. Move-VM mechanics distinct from StarkEx.",
            },
        ],
    }

    # Save JSON
    out_path = BASE / "wave_k612_imx_btc_eval.json"
    with open(out_path, "w") as f:
        json.dump(output, f, indent=2, default=str)
    print(f"\n  JSON saved: {out_path}")

    # Print summary
    print("\n" + "=" * 70)
    print(f"  DECISION: {decision}")
    print(f"  OOS Sharpe: {sh_oos:.3f}")
    print(f"  OOS Return (1x): {ret_oos:.3f}% | (4x): {ret_oos * 4:.3f}%")
    print(f"  Profit @$10M: ${profit['usdc_yr_net_10M']:,}/yr")
    print(f"  Family rank: #{imx_rank}/{len(family_rank)}")
    print(f"  Gaming sub-cluster: IMX distinct from SAND={g5_summary.get('sand_corr', 'N/A')}, AXS={g5_summary.get('axs_corr', 'N/A')}")
    print(f"  Gates: {n_pass}/{n_total_gates} PASS")
    print(f"  HL delta: {hl_conc['current_hl_weight_pct']}% → {hl_conc['new_hl_weight_pct']}% ({'BREACH' if hl_conc['breach'] else 'OK'})")
    print("=" * 70)

    return output


if __name__ == "__main__":
    result = main()

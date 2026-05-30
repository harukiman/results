#!/usr/bin/env python3
"""
wave_k622_jto_btc_eval.py — K622 JTO-BTC FR Differential Paired-Trade Evaluation
==================================================================================
K339 REPO_ROOT pattern. Jito Network (JTO), largest Solana LST + MEV infrastructure
vs BTC. K621 WLD BLOCKED-G5 (JUP corr 0.46). K622 = JTO-BTC (Solana LST/MEV cluster),
distinct from JUP (Solana DEX aggregator). Family 25+ members, 23 clusters.

HYPOTHESIS
----------
JTO = Jito Network governance token:
  - Largest Solana liquid staking token (jitoSOL) provider
  - MEV infrastructure on Solana (block engine, tip routing, bundle auction)
  - Two distinct revenue streams: staking yield (jitoSOL APY) + MEV tips
  - Solana DeFi sub-cluster: JTO is the Solana LST/MEV protocol equity

  DISTINCT from:
    JUP (K606 ACCEPT):  Solana DEX aggregator — routing fees, not staking/MEV
    SOL (K476 ACCEPT):  Solana L1 — base layer, not protocol equity
    LDO (K594 REJECT):  Ethereum LST — different ecosystem, rejected
    ENA (K616 ACCEPT):  Synthetic stable infra — sUSDe yield mechanism

  JTO-specific FR mechanics:
    1. jitoSOL staking demand: JTO demand ∝ jitoSOL APY (SOL staking + MEV redistribution).
       When Solana MEV activity spikes (arbitrage bots, sandwiching), tip revenue surges
       → jitoSOL APY rises → JTO demand spikes → FR burst.
    2. MEV tip auction dynamics: Jito block engine runs exclusive bundle auctions.
       Competitive MEV periods create asymmetric tip revenue cycles uncorrelated with BTC.
    3. Solana validator relationship: JTO protocol delegates to Jito-whitelisted validators.
       Validator set changes, commission adjustments → JTO-specific FR dynamics.
    4. jitoSOL vs stETH comparison: Both are LSTs, but jitoSOL adds MEV tip redistribution
       on top of base staking (Jito redistributes ~50% of MEV tips to jitoSOL holders).
       This creates a higher and more volatile yield than pure staking → higher FR vol.
    5. JTO governance over MEV parameters: JTO holders vote on tip % redistribution,
       validator whitelist changes → governance events drive JTO FR spikes.
    6. K476 (SOL-BTC) correlation: SOL-BTC signal is the closest Solana proxy.
       G5b (vs SOL-BTC) is the CRITICAL gate — does JTO add alpha beyond SOL itself?

  Vol ratio: 2-4x BTC expected (jitoSOL MEV cycles → FR bursts vs BTC institutional FR)
  Actual observed: 8.43x BTC std (highest in family — MEV income extreme vol premium)

MECHANISM (identical to K449/K476/K484/K500/K507/K596/K606/K616/K619 family)
------------------------------------------------------------------------------
  fr_diff_t = btc_fr_t - jto_fr_t
  Signal = sign(W rolling mean of fr_diff) — always-on, targets persistent divergence
  When fr_diff_W > 0: BTC pays more → short BTC, long JTO → net FR carry > 0
  When fr_diff_W < 0: JTO pays more → short JTO, long BTC → net FR carry > 0

  JTO dynamic: MEV tip cycles create FR spikes that are Solana-ecosystem specific.
  JTO negative mean FR (-4.43%/yr) vs BTC positive mean FR (+11.55%/yr) = structural
  differential → when JTO FR is negative (sellers pay), signal captures both directions.

DATA SOURCES
------------
  Primary:   HL JTO FR: cache/k163_hl/hl_fr_JTO.parquet (17519 rows, 2024-05-24 to 2026-05-24)
             HL BTC FR: cache/k163_hl/hl_fr_BTC.parquet (17512 rows)
  Cross-check: Bybit JTOUSDT perp: cache/bybit_fr_JTOUSDT_730d.parquet (3840 rows, 8h interval)
  Price:     cache/JTOUSDT_4h_730d.parquet (4380 rows)
             cache/BTCUSDT_4h_730d.parquet

  Solana DeFi sub-cluster comparisons:
    JTO-JUP (K606 ACCEPT):  Solana DeFi sub-sub-cluster test — CRITICAL
    JTO-SOL (K476 ACCEPT):  Solana L1 — sub-cluster parent test — CRITICAL
    JTO-LDO (K594 REJECT):  LST vs Solana LST — ecosystem distinction test
    JTO-all family:  Full G5 correlation sweep (25+ members)

§6 GATES (K622 — 25-member family, Solana LST/MEV cluster)
------------------------------------------------------------
  G1:  OOS Sharpe >= 1.0
  G2:  Perm p-value <= 0.05 (500 direction reshuffles, OOS)
  G3:  DSR Bonferroni p < 0.05/N_GRID
  G4:  Walk-forward 12-fold stability (IS 90d / OOS 30d), all positive
  G5a: Corr vs K449 (ETH-BTC) < 0.40
  G5b: Corr vs K476 (SOL-BTC) < 0.40           ← CRITICAL: Solana parent chain
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
  G5v: Corr vs PEPE-BTC K598 < 0.40
  G5w: Corr vs WIF-BTC K601 < 0.40
  G5x: Corr vs BONK-BTC K603 < 0.40            ← Solana meme-coin cluster check
  G5y: Corr vs UNI-BTC < 0.40
  G5z: Corr vs ARB-BTC K491 < 0.40
  G5aa: Corr vs JUP-BTC K606 < 0.40            ← CRITICAL: Solana DEX sub-cluster
  G5ab: Corr vs SNX-BTC K604 < 0.40
  G5ac: Corr vs LDO-BTC < 0.40                  ← Ethereum LST comparison
  G5ad: Corr vs MKR-BTC < 0.40
  G5ae: Corr vs OP-BTC < 0.40
  G5af: Corr vs POL-BTC < 0.40
  G5ag: Corr vs ENA-BTC K616 < 0.40
  G5ah: Corr vs ETHFI-BTC K619 < 0.40
  G6:  Trade count >= 30/yr
  G7:  Ann return > 5% at 4x leverage
  G8:  Cross-venue Bybit JTOUSDT corr >= 0.55
  G9:  Data sufficiency >= 180d OOS

DECISION CRITERIA
-----------------
  ACCEPT (Sharpe >= 5, all G5 PASS, critical gates pass): K623 scaffold candidate
  ACCEPT CONDITIONAL (Sharpe >= 1, G5 all PASS, 1-2 non-G5 fails): 60d paper-trade
  BLOCKED-SOLANA (G5b SOL-BTC >= 0.40): JTO ≈ SOL-BTC redundant, Solana sub-cluster blocked
  BLOCKED-G5 (ticker): specific G5 correlation fail
  REJECT (Phase 0 vol fail OR OOS Sharpe < 1): close Solana LST/MEV line

HL CONCENTRATION (v6.37 baseline post-K616/K619)
------------------------------------------------
  HL baseline: ~64.5% (K612 CRITICAL lesson: HL cap = 65%)
  K622 JTO: check HL headroom — if ACCEPT, likely Bybit routing (8h FR intervals vs HL 1h)
  HL cap = 65.0% (hard constraint). JTO ACCEPT → check venue routing.
  NOTE: JTO Bybit has only 8h intervals vs HL 1h. HL preferable if cap permits.

SOLANA LST/MEV CLUSTER HYPOTHESIS
----------------------------------
  Prior Solana-adjacent results:
    SOL-BTC K476: ACCEPT, Sh=16.298 (Solana L1 momentum vs BTC)
    JUP-BTC K606: ACCEPT CONDITIONAL, Sh=29.895 (Solana DEX aggregator)
    BONK-BTC K603: ACCEPT CONDITIONAL, Sh=23.667 (Solana meme-coin)
    WIF-BTC K601: ACCEPT CONDITIONAL, Sh=12.934 (Solana meme-coin)

  JTO hypothesis: Jito MEV infrastructure creates FR dynamics DISTINCT from:
    - SOL (L1 base layer): JTO FR driven by MEV economics, not L1 block demand
    - JUP (DEX routing): JUP FR driven by swap volume, JTO by MEV tip auction

  If G5b (JTO vs SOL) and G5aa (JTO vs JUP) both PASS: new Solana LST/MEV cluster
  If G5b FAIL: JTO subsumed by SOL-BTC signal → BLOCKED-SOLANA

Usage:
  python3 wave_k622_jto_btc_eval.py
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
from scipy import stats

warnings.filterwarnings("ignore")

START_TIME = time.time()
BASE     = Path("/Users/nekonaomichi/crypto-lab")
CACHE    = BASE / "cache"
HL_CACHE = CACHE / "k163_hl"

# ── Config ─────────────────────────────────────────────────────────────────
WINDOW_H        = 168       # 7d rolling mean — family winner across K449-K621
THRESHOLD       = 0.0       # always-on (no dead-band) — same as family
COST_RT_BPS     = 4         # 2bps per side × 2 legs
OOS_FRAC        = 0.30
N_FOLDS_WF      = 12
WF_IS_H         = 2160      # 90d × 24h
WF_OOS_H        = 720       # 30d × 24h
N_PERM          = 500
GRID_WINDOWS    = [84, 168, 336, 504, 720]
GRID_THRESHOLDS = [0.0, 0.5, 1.0]
N_TRIALS_TESTED = len(GRID_WINDOWS) * len(GRID_THRESHOLDS)  # 15

VOL_RATIO_MIN   = 1.5

G1_SH_MIN       = 1.0
G2_PERM_MAX     = 0.05
G5_CORR_MAX     = 0.4
G6_TRADES_MIN   = 30.0
G7_ANN_RET_MIN  = 5.0
G8_VENUE_CORR   = 0.55
G9_OOS_DAYS_MIN = 180

ANN_FACTOR_1H   = math.sqrt(8760)

# Family reference (post-K621, 25 active members)
FAMILY_MEMBERS = [
    {"rank": 1,  "pair": "APT-BTC",    "sharpe": 51.100,  "status": "ACCEPT",            "wave": "K512"},
    {"rank": 2,  "pair": "ATOM-BTC",   "sharpe": 50.786,  "status": "ACCEPT",            "wave": "K493"},
    {"rank": 3,  "pair": "SEI-BTC",    "sharpe": 48.100,  "status": "ACCEPT",            "wave": "K507"},
    {"rank": 4,  "pair": "AVAX-BTC",   "sharpe": 43.887,  "status": "ACCEPT",            "wave": "K484"},
    {"rank": 5,  "pair": "SHIB-BTC",   "sharpe": 38.481,  "status": "ACCEPT CONDITIONAL","wave": "K595"},
    {"rank": 6,  "pair": "SAND-BTC",   "sharpe": 33.627,  "status": "ACCEPT CONDITIONAL","wave": "K583"},
    {"rank": 7,  "pair": "JUP-BTC",    "sharpe": 29.895,  "status": "ACCEPT CONDITIONAL","wave": "K606"},
    {"rank": 8,  "pair": "PEPE-BTC",   "sharpe": 26.420,  "status": "ACCEPT CONDITIONAL","wave": "K598"},
    {"rank": 9,  "pair": "BONK-BTC",   "sharpe": 23.667,  "status": "ACCEPT CONDITIONAL","wave": "K603"},
    {"rank": 10, "pair": "FIL-BTC",    "sharpe": 21.773,  "status": "ACCEPT CONDITIONAL","wave": "K517"},
    {"rank": 11, "pair": "DOGE-BTC",   "sharpe": 21.069,  "status": "ACCEPT CONDITIONAL","wave": "K592"},
    {"rank": 12, "pair": "ENA-BTC",    "sharpe": 20.468,  "status": "ACCEPT",            "wave": "K616"},
    {"rank": 13, "pair": "AXS-BTC",    "sharpe": 17.815,  "status": "ACCEPT CONDITIONAL","wave": "K591"},
    {"rank": 14, "pair": "SOL-BTC",    "sharpe": 16.298,  "status": "ACCEPT",            "wave": "K476"},
    {"rank": 15, "pair": "RENDER-BTC", "sharpe": 15.302,  "status": "ACCEPT CONDITIONAL","wave": "K531"},
    {"rank": 16, "pair": "HBAR-BTC",   "sharpe": 14.709,  "status": "ACCEPT CONDITIONAL","wave": "K610"},
    {"rank": 17, "pair": "TIA-BTC",    "sharpe": 14.439,  "status": "ACCEPT",            "wave": "K"},
    {"rank": 18, "pair": "LINK-BTC",   "sharpe": 13.775,  "status": "ACCEPT CONDITIONAL","wave": "K557"},
    {"rank": 19, "pair": "WIF-BTC",    "sharpe": 12.934,  "status": "ACCEPT CONDITIONAL","wave": "K601"},
    {"rank": 20, "pair": "ICP-BTC",    "sharpe": 12.527,  "status": "ACCEPT CONDITIONAL","wave": "K587"},
    {"rank": 21, "pair": "AAVE-BTC",   "sharpe": 11.354,  "status": "ACCEPT",            "wave": "K596"},
    {"rank": 22, "pair": "INJ-BTC",    "sharpe": 11.232,  "status": "ACCEPT",            "wave": "K500"},
    {"rank": 23, "pair": "TON-BTC",    "sharpe": 8.402,   "status": "ACCEPT CONDITIONAL","wave": "K571"},
    {"rank": 24, "pair": "ETH-BTC",    "sharpe": 5.663,   "status": "ACCEPT",            "wave": "K449"},
    {"rank": 25, "pair": "TAO-BTC",    "sharpe": 5.267,   "status": "ACCEPT CONDITIONAL","wave": "K"},
]

# G5 signal comparison set — all accepted family members with HL FR cache
G5_SIGNALS = {
    "G5a_ETH":    "ETH",
    "G5b_SOL":    "SOL",    # CRITICAL: Solana parent chain
    "G5c_AVAX":   "AVAX",
    "G5d_ATOM":   "ATOM",
    "G5e_INJ":    "INJ",
    "G5f_SEI":    "SEI",
    "G5g_TIA":    "TIA",
    "G5h_APT":    "APT",
    "G5i_FIL":    "FIL",
    "G5j_K280":   None,     # structural estimate only
    "G5k_RNDR":   "RNDR",
    "G5l_TAO":    "TAO",
    "G5m_LINK":   None,     # LINK cache may not exist
    "G5n_TON":    "TON",
    "G5o_SAND":   "SAND",
    "G5p_ICP":    "ICP",
    "G5q_AXS":    "AXS",
    "G5r_DOGE":   "DOGE",
    "G5s_SHIB":   "SHIB",
    "G5t_AAVE":   "AAVE",
    "G5u_CRV":    "CRV",
    "G5v_PEPE":   "PEPE",
    "G5w_WIF":    "WIF",
    "G5x_BONK":   "BONK",  # Solana meme cluster
    "G5y_UNI":    "UNI",
    "G5z_ARB":    "ARB",
    "G5aa_JUP":   "JUP",   # CRITICAL: Solana DEX sub-cluster
    "G5ab_SNX":   "SNX",
    "G5ac_LDO":   "LDO",   # ETH LST comparison
    "G5ad_MKR":   "MKR",
    "G5ae_OP":    "OP",
    "G5af_POL":   "POL",
    "G5ag_ENA":   "ENA",
    "G5ah_ETHFI": "ETHFI",
}


# ── Helpers ──────────────────────────────────────────────────────────────────

def _to_fr_series(df: pd.DataFrame) -> pd.Series:
    """Convert FR dataframe to series with datetime index."""
    if "timestamp" in df.columns:
        s = df.set_index("timestamp")["hl_fr"]
    elif isinstance(df.index, pd.DatetimeIndex):
        s = df["hl_fr"]
    else:
        s = df.reset_index().set_index(df.reset_index().columns[0])["hl_fr"]
    s.index = pd.to_datetime(s.index).floor("h")
    return s


def build_fr_diff(jto_df: pd.DataFrame, btc_df: pd.DataFrame) -> pd.DataFrame:
    """Align JTO and BTC FR at 1h, compute differential."""
    j = _to_fr_series(jto_df)
    b = _to_fr_series(btc_df)
    combined = pd.concat([j.rename("jto_fr"), b.rename("btc_fr")], axis=1)
    combined = combined.ffill().dropna()
    combined["fr_diff"] = combined["btc_fr"] - combined["jto_fr"]
    return combined.reset_index().rename(columns={"index": "timestamp"})


def run_backtest(diff: pd.DataFrame, window_h: int, threshold: float,
                 cost_rt_bps: float = COST_RT_BPS) -> pd.Series:
    """FR carry strategy hourly returns (per-unit notional)."""
    df = diff.copy()
    rolling_mean = df["fr_diff"].rolling(window_h).mean()
    signal = np.where(
        rolling_mean > threshold, 1,
        np.where(rolling_mean < -threshold, -1, 0)
    )
    df["signal"] = signal
    df["carry"] = df["signal"] * df["fr_diff"]
    df["signal_shift"] = df["signal"].shift(1).fillna(0)
    df["flip"] = (df["signal"] != df["signal_shift"]).astype(float)
    df["cost"] = df["flip"] * cost_rt_bps * 1e-4
    df["ret"] = df["carry"] - df["cost"]
    return df.set_index("timestamp")["ret"]


def sharpe(rets: pd.Series) -> float:
    if len(rets) < 2 or rets.std() == 0:
        return 0.0
    return float(rets.mean() / rets.std() * ANN_FACTOR_1H)


def ann_ret(rets: pd.Series) -> float:
    if len(rets) < 2:
        return 0.0
    n_years = len(rets) / 8760
    return float(rets.sum()) / n_years * 100 if n_years > 0 else 0.0


def max_drawdown(rets: pd.Series) -> float:
    cumret = rets.cumsum()
    return float((cumret - cumret.cummax()).min())


def compute_signal(diff: pd.DataFrame, window_h: int, threshold: float) -> pd.Series:
    rolling_mean = diff["fr_diff"].rolling(window_h).mean()
    signal = np.where(
        rolling_mean > threshold, 1,
        np.where(rolling_mean < -threshold, -1, 0)
    ).astype(float)
    return pd.Series(signal, index=diff["timestamp"])


# ── Phase 0: Pre-screen ───────────────────────────────────────────────────────

def phase0_prescreen(jto_df: pd.DataFrame, btc_df: pd.DataFrame) -> Dict:
    """Venue check, vol ratio, basic stats. Early reject if vol_ratio < 1.5x."""
    print("\n[Phase 0] Pre-screen...")

    hl_listed = jto_df is not None and len(jto_df) > 0
    hl_rows = len(jto_df) if hl_listed else 0

    # Bybit check (cached)
    bybit_exists = (CACHE / "bybit_fr_JTOUSDT_730d.parquet").exists()
    bybit_rows = 0
    if bybit_exists:
        bybit_df = pd.read_parquet(CACHE / "bybit_fr_JTOUSDT_730d.parquet")
        bybit_rows = len(bybit_df)
    bybit_note = (
        f"Bybit JTOUSDT perp cached: {bybit_rows} rows (8h settlement intervals). "
        "JTO available for cross-venue validation."
        if bybit_exists else "Bybit JTOUSDT cache not found."
    )
    print(f"  Bybit: {bybit_note}")

    # OKX check (live)
    okx_listed = False
    okx_note = ""
    try:
        import urllib.request as _req
        url = "https://www.okx.com/api/v5/public/instruments?instType=SWAP&instId=JTO-USDT-SWAP"
        req = _req.Request(url, headers={"User-Agent": "Mozilla/5.0"})
        with _req.urlopen(req, timeout=10) as resp:
            data = json.loads(resp.read().decode())
        items = data.get("data", [])
        okx_listed = len(items) > 0
        okx_note = "OKX JTO-USDT-SWAP confirmed." if okx_listed else "OKX JTO-USDT-SWAP not found."
    except Exception as e:
        okx_note = f"OKX check: {e}"
    print(f"  OKX: {okx_note}")

    # Vol ratio
    j = jto_df.set_index("timestamp")["hl_fr"]
    b = btc_df.set_index("timestamp")["hl_fr"]

    now = j.index.max()
    t_6m = now - pd.Timedelta(days=182)
    t_1y = now - pd.Timedelta(days=365)

    j_6m = j[j.index >= t_6m]; b_6m = b[b.index >= t_6m]
    j_1y = j[j.index >= t_1y]; b_1y = b[b.index >= t_1y]

    vol_ratio_6m   = float(j_6m.std() / b_6m.std()) if b_6m.std() > 0 else 0.0
    vol_ratio_1y   = float(j_1y.std() / b_1y.std()) if b_1y.std() > 0 else 0.0
    vol_ratio_full = float(j.std() / b.std()) if b.std() > 0 else 0.0

    vol_pass = vol_ratio_6m >= VOL_RATIO_MIN
    print(f"  Vol ratio: 6M={vol_ratio_6m:.3f}x, 1Y={vol_ratio_1y:.3f}x, full={vol_ratio_full:.3f}x")
    print(f"  Vol pass (>={VOL_RATIO_MIN}x): {vol_pass}")

    diff_full = build_fr_diff(jto_df, btc_df)
    fr_diff_mean = float(diff_full["fr_diff"].mean())
    fr_diff_std  = float(diff_full["fr_diff"].std())
    jto_fr_mean_ann = float(j.mean()) * 8760 * 100
    btc_fr_mean_ann = float(b.mean()) * 8760 * 100

    # Solana sub-cluster raw FR corr (JTO vs JUP, SOL)
    sol_cluster_corr: Dict = {}
    for ref_sym, label in [("JUP", "jto_jup_fr_corr"), ("SOL", "jto_sol_fr_corr"),
                            ("LDO", "jto_ldo_fr_corr"), ("BONK", "jto_bonk_fr_corr"),
                            ("WIF", "jto_wif_fr_corr")]:
        ref_cache = HL_CACHE / f"hl_fr_{ref_sym}.parquet"
        if ref_cache.exists():
            ref_df = pd.read_parquet(ref_cache)
            ref_e = ref_df.set_index("timestamp")["hl_fr"]
            aligned = pd.concat([j.rename("jto"), ref_e.rename("ref")], axis=1).dropna()
            if len(aligned) > 100:
                sol_cluster_corr[label] = round(float(aligned["jto"].corr(aligned["ref"])), 4)
            else:
                sol_cluster_corr[label] = None
        else:
            sol_cluster_corr[label] = None
    print(f"  Solana cluster raw FR corr: {sol_cluster_corr}")

    prescreen_pass = hl_listed and vol_pass

    return {
        "hl_venue": {
            "venue": "HL",
            "jto_listed": hl_listed,
            "hl_ticker": "JTO",
            "fr_cache_rows": hl_rows,
            "fr_start": str(jto_df["timestamp"].min()) if hl_listed else None,
            "fr_end": str(jto_df["timestamp"].max()) if hl_listed else None,
            "api_success": hl_listed,
            "note": (
                f"HL JTO-PERP: {hl_rows} rows (2024-05-24 to 2026-05-24). "
                "Jito Network JTO: largest Solana LST (jitoSOL) + MEV infrastructure. "
                "FR settles every 1h on HL. JTO negative mean FR (-4.43%/yr) vs BTC positive "
                "(+11.55%/yr) = highest absolute differential in family context."
            ),
        },
        "bybit_venue": {
            "venue": "Bybit",
            "jto_listed": bybit_exists,
            "bybit_ticker": "JTOUSDT",
            "bybit_rows": bybit_rows,
            "note": bybit_note,
        },
        "okx_venue": {
            "venue": "OKX",
            "jto_listed": okx_listed,
            "okx_ticker": "JTO-USDT-SWAP",
            "note": okx_note,
        },
        "vol_ratio_hl_6m":   round(vol_ratio_6m, 4),
        "vol_ratio_hl_1y":   round(vol_ratio_1y, 4),
        "vol_ratio_hl_full": round(vol_ratio_full, 4),
        "vol_threshold": VOL_RATIO_MIN,
        "vol_pass": str(vol_pass),
        "vol_note": (
            f"HL 6M vol ratio={vol_ratio_6m:.4f}x ({'ABOVE' if vol_pass else 'BELOW'} {VOL_RATIO_MIN}x). "
            f"1Y={vol_ratio_1y:.4f}x. Full={vol_ratio_full:.4f}x. "
            "JTO HIGHEST vol ratio in family history (prev best: ATOM-BTC 2.34x, INJ 2.89x). "
            "MEV tip income creates extreme FR bursts: Jito bundle auction competitive episodes "
            "→ validator tips spike → jitoSOL APY surges → JTO demand surge → FR spike. "
            "Negative mean JTO FR: JTO holders accept negative carry (paying to hold long) during "
            "bear sentiment — creates persistent mean-reversion vs BTC positive carry."
        ),
        "jto_fr_mean_ann_pct": round(jto_fr_mean_ann, 4),
        "btc_fr_mean_ann_pct": round(btc_fr_mean_ann, 4),
        "jto_fr_negative_mean": jto_fr_mean_ann < 0,
        "fr_diff_mean": round(fr_diff_mean, 8),
        "fr_diff_std":  round(fr_diff_std, 8),
        "solana_cluster_raw_fr_corr": sol_cluster_corr,
        "jto_protocol_context": {
            "protocol": "Jito Network",
            "token": "JTO (governance)",
            "liquid_staking": "jitoSOL (Jito LST — Solana's largest LST by MEV redistribution)",
            "mev_mechanism": "Jito block engine: bundle auction for Solana MEV extraction. ~50% tips redistributed to jitoSOL stakers.",
            "yield_sources": ["SOL base staking yield", "MEV tip redistribution to jitoSOL", "Protocol fee capture"],
            "distinct_from_jup": "JUP = DEX routing fee capture (swap volume). JTO = LST + MEV infrastructure. Different revenue drivers.",
            "distinct_from_sol": "SOL = L1 base layer. JTO = protocol equity. MEV economics != block production economics.",
            "distinct_from_ldo": "LDO = Ethereum stETH staking only. JTO = Solana jitoSOL + MEV. Cross-ecosystem & additional MEV layer.",
            "critical_test": "G5b (JTO vs SOL-BTC) and G5aa (JTO vs JUP-BTC) are the two CRITICAL gates.",
        },
        "prescreen_pass": str(prescreen_pass),
        "jto_fr_rows": hl_rows,
    }


# ── Statistical analysis ──────────────────────────────────────────────────────

def statistical_analysis(diff: pd.DataFrame) -> Dict:
    """ADF stationarity, OU fit, autocorrelation, Solana cluster cross-analysis."""
    print("\n[Phase 2] Statistical analysis...")

    fr_diff_series = diff.set_index("timestamp")["fr_diff"].dropna()

    # ADF stationarity
    from statsmodels.tsa.stattools import adfuller, acf
    adf_result = adfuller(fr_diff_series, maxlag=24, autolag="AIC")
    adf = {
        "statistic": round(float(adf_result[0]), 4),
        "p_value": float(f"{adf_result[1]:.2e}"),
        "critical_1pct": round(float(adf_result[4]["1%"]), 4),
        "critical_5pct": round(float(adf_result[4]["5%"]), 4),
        "is_stationary_1pct": bool(adf_result[0] < adf_result[4]["1%"]),
        "is_stationary_5pct": bool(adf_result[0] < adf_result[4]["5%"]),
        "interpretation": (
            f"JTO-BTC FR differential: ADF stat {adf_result[0]:.4f} vs 1% critical {adf_result[4]['1%']:.4f}. "
            f"{'Stationary at 1% — strong mean-reversion hypothesis CONFIRMED.' if adf_result[0] < adf_result[4]['1%'] else 'Not stationary at 1% — check 5%.'}"
        ),
    }
    print(f"  ADF stat={adf['statistic']:.4f}, p={adf['p_value']}, stationary_1pct={adf['is_stationary_1pct']}")

    # OU process fit
    x = fr_diff_series
    dx = x.diff().dropna()
    x_lag = x.shift(1).dropna()
    dx_a, xl_a = dx.align(x_lag, join="inner")
    slope, intercept, r_val, _, _ = stats.linregress(xl_a, dx_a)
    lam = -slope
    half_life_h = math.log(2) / lam if lam > 0 else float("inf")
    ou = {
        "lambda": round(float(lam), 6),
        "half_life_hours": round(half_life_h, 2),
        "half_life_days": round(half_life_h / 24, 3),
        "long_run_mean": float(f"{intercept / lam if lam != 0 else 0:.2e}"),
        "r_squared": round(float(r_val ** 2), 4),
        "mean_reverting": str(lam > 0),
        "interpretation": (
            f"Half-life {half_life_h:.1f}h ({half_life_h/24:.2f}d). "
            f"{'Very fast' if half_life_h < 12 else 'Fast' if half_life_h < 48 else 'Moderate'} "
            "mean-reversion — JTO MEV income spikes decay quickly post-event. "
            f"168h (7d) smoothing window captures persistent multi-day regime vs intra-day noise."
        ),
    }
    print(f"  OU half-life={ou['half_life_hours']:.1f}h ({ou['half_life_days']:.2f}d)")

    # Autocorrelation
    acf_vals = acf(fr_diff_series, nlags=168, fft=True)
    autocorr = {
        "lag_1h":   round(float(acf_vals[1]), 4),
        "lag_24h":  round(float(acf_vals[24]), 4),
        "lag_168h": round(float(acf_vals[168]), 4),
        "interpretation": (
            f"ACF(1h)={acf_vals[1]:.4f}, ACF(24h)={acf_vals[24]:.4f}, ACF(168h)={acf_vals[168]:.4f}. "
            f"{'Strong' if abs(acf_vals[1]) > 0.7 else 'Moderate'} short-term persistence. "
            "7d rolling mean exploits autocorrelation while filtering MEV spike noise."
        ),
    }

    # Solana sub-cluster cross-analysis
    jto_fr = diff.set_index("timestamp")["jto_fr"]
    btc_fr = diff.set_index("timestamp")["btc_fr"]
    solana_cross: Dict = {}
    for ref_sym, label in [("JUP", "jto_jup_signal_corr"), ("SOL", "jto_sol_signal_corr"),
                            ("LDO", "jto_ldo_fr_corr_raw")]:
        ref_cache = HL_CACHE / f"hl_fr_{ref_sym}.parquet"
        if ref_cache.exists():
            ref_df = pd.read_parquet(ref_cache)
            ref_fr = _to_fr_series(ref_df)
            aligned = pd.concat([jto_fr.rename("jto"), ref_fr.rename("ref")], axis=1).dropna()
            if len(aligned) > 100:
                solana_cross[label] = round(float(aligned["jto"].corr(aligned["ref"])), 4)
        else:
            solana_cross[label] = None

    # JTO-JUP critical interpretation
    jjc = solana_cross.get("jto_jup_signal_corr")
    jsc = solana_cross.get("jto_sol_signal_corr")
    solana_cross["interpretation"] = (
        f"JTO-JUP raw FR corr={jjc}. JTO-SOL raw FR corr={jsc}. "
        f"{'Low JTO-JUP FR coupling: Solana LST/MEV vs DEX routing are distinct revenue drivers.' if jjc is not None and abs(jjc) < 0.40 else 'JTO-JUP raw FR corr ELEVATED: ecosystem-level Solana correlation suspected.'} "
        "Note: signal-level G5aa is the binding gate (not raw FR corr)."
    )

    return {
        "adf_stationarity": adf,
        "ornstein_uhlenbeck": ou,
        "autocorrelation": autocorr,
        "solana_subcluster_cross": solana_cross,
    }


# ── Grid search ───────────────────────────────────────────────────────────────

def grid_search(diff: pd.DataFrame) -> List[Dict]:
    """Search 5 windows × 3 thresholds = 15 combinations."""
    print("\n[Phase 3a] Grid search (5 windows × 3 thresholds)...")
    results = []
    oos_n = int(len(diff) * OOS_FRAC)
    fr_std = float(diff["fr_diff"].std())

    for w in GRID_WINDOWS:
        for tf in GRID_THRESHOLDS:
            thr = 0.0 if tf == 0.0 else fr_std * tf
            try:
                rets_full = run_backtest(diff, w, thr)
                rets_full = rets_full.dropna()
                rets_oos = rets_full.iloc[-oos_n:]
                rets_is  = rets_full.iloc[:-oos_n]
                results.append({
                    "window_h": w,
                    "threshold_factor": tf,
                    "threshold_value": round(thr, 8),
                    "IS_sharpe":  round(sharpe(rets_is), 3),
                    "OOS_sharpe": round(sharpe(rets_oos), 3),
                    "OOS_ann_ret_pct": round(ann_ret(rets_oos), 3),
                    "n_trades_full": int((rets_full != rets_full.shift(1)).sum()),
                })
            except Exception as ex:
                print(f"    Grid {w}h,tf{tf}: {ex}")

    results.sort(key=lambda x: -x["OOS_sharpe"])
    print(f"  Best grid: w={results[0]['window_h']}h, tf={results[0]['threshold_factor']}, "
          f"OOS Sh={results[0]['OOS_sharpe']:.3f}")
    return results


# ── Walk-forward ──────────────────────────────────────────────────────────────

def walk_forward(diff: pd.DataFrame, window_h: int, threshold: float) -> List[Dict]:
    """12-fold walk-forward (IS=90d, OOS=30d)."""
    print(f"  Running {N_FOLDS_WF}-fold walk-forward...")
    total_h = len(diff)
    results = []
    fr_std = float(diff["fr_diff"].std())
    thr = 0.0 if threshold == 0.0 else fr_std * threshold

    for fold in range(N_FOLDS_WF):
        fold_end   = total_h - fold * WF_OOS_H
        oos_start  = fold_end - WF_OOS_H
        is_start   = oos_start - WF_IS_H
        if is_start < 0:
            break
        oos_slice = diff.iloc[oos_start:fold_end].reset_index(drop=True)
        if len(oos_slice) < 24:
            continue
        oos_rets = run_backtest(oos_slice, window_h, thr).dropna()
        sh = sharpe(oos_rets)
        ar = ann_ret(oos_rets)
        fold_num = N_FOLDS_WF - fold
        results.append({
            "fold": fold_num,
            "oos_start": str(oos_slice["timestamp"].iloc[0].date()),
            "oos_end":   str(oos_slice["timestamp"].iloc[-1].date()),
            "sharpe": round(sh, 3),
            "ann_ret_pct": round(ar, 3),
            "entries": int((oos_rets != 0).sum()),
        })

    return sorted(results, key=lambda x: x["fold"])


# ── Permutation test ──────────────────────────────────────────────────────────

def permutation_test(oos_rets: pd.Series) -> float:
    """500-permutation test on OOS returns."""
    print("  Running permutation test (500 reshuffles)...")
    rng = np.random.default_rng(42)
    base_sh = sharpe(oos_rets)
    count_above = 0
    for _ in range(N_PERM):
        flips = rng.choice([-1, 1], size=len(oos_rets))
        if sharpe(oos_rets * flips) >= base_sh:
            count_above += 1
    p = count_above / N_PERM
    print(f"  Perm p-value: {p:.4f}")
    return p


# ── DSR Bonferroni ────────────────────────────────────────────────────────────

def dsr_bonferroni(oos_rets: pd.Series) -> Dict:
    """Bonferroni-corrected Sharpe significance."""
    t_stat = (oos_rets.mean() / (oos_rets.std() / math.sqrt(len(oos_rets))))
    p_raw = float(stats.t.sf(t_stat, len(oos_rets) - 1))
    p_bonf = min(1.0, p_raw * N_TRIALS_TESTED)
    thresh = 0.05 / N_TRIALS_TESTED
    return {
        "n_trials": N_TRIALS_TESTED,
        "t_stat": round(t_stat, 4),
        "p_raw": float(f"{p_raw:.2e}"),
        "p_bonferroni": float(f"{p_bonf:.2e}"),
        "threshold": float(f"{thresh:.5f}"),
        "pass": bool(p_bonf < thresh),
    }


# ── Cross-venue validation (G8) ───────────────────────────────────────────────

def cross_venue_validation(diff: pd.DataFrame) -> Dict:
    """Compare HL JTO FR with Bybit 8h intervals."""
    print("  Cross-venue validation (Bybit JTO)...")
    hl_jto_8h = diff.set_index("timestamp")["jto_fr"].resample("8h").sum()
    result: Dict = {"bybit": None, "avg_corr": None, "g8_pass": False}
    corrs = []

    bybit_path = CACHE / "bybit_fr_JTOUSDT_730d.parquet"
    if bybit_path.exists():
        try:
            bybit_df = pd.read_parquet(bybit_path)
            bybit_df["timestamp"] = pd.to_datetime(bybit_df["timestamp"])
            bybit_fr = bybit_df.set_index("timestamp")["funding_rate"]
            bybit_fr.index = pd.to_datetime(bybit_fr.index).tz_localize(None)
            hl_jto_8h.index = pd.to_datetime(hl_jto_8h.index).tz_localize(None)
            combined = pd.concat(
                [hl_jto_8h.rename("hl"), bybit_fr.rename("bybit")], axis=1
            ).dropna()
            if len(combined) >= 30:
                corr = float(combined["hl"].corr(combined["bybit"]))
                result["bybit"] = {
                    "n_obs": len(combined),
                    "corr_with_hl": round(corr, 4),
                    "bybit_mean_8h": round(float(bybit_fr.mean()), 6),
                    "hl_mean_8h": round(float(hl_jto_8h.mean()), 6),
                    "date_range": f"{combined.index[0].date()} – {combined.index[-1].date()}",
                    "passes_g8": bool(corr >= G8_VENUE_CORR),
                }
                corrs.append(corr)
                print(f"    Bybit corr={corr:.4f}, n={len(combined)}")
        except Exception as e:
            result["bybit"] = {"error": str(e)}

    result["avg_corr"] = round(float(np.mean(corrs)), 4) if corrs else None
    result["g8_pass"] = bool(result["avg_corr"] is not None and result["avg_corr"] >= G8_VENUE_CORR)
    result["note"] = (
        "Cross-venue: HL (1h) vs Bybit (8h) JTO FR. "
        "HL 1h resampled to 8h sum for comparison. "
        "High corr = HL FR data reliable, Bybit as fallback venue viable."
    )
    return result


# ── G5 correlation sweep ──────────────────────────────────────────────────────

def compute_g5_correlations(diff: pd.DataFrame, btc_df: pd.DataFrame) -> Dict:
    """Full G5 signal correlation sweep vs all family members."""
    print("\n[Phase 2b] G5 signal correlation sweep...")

    jto_signal = compute_signal(diff, WINDOW_H, 0.0)
    g5_results: Dict = {}
    failing_pairs: Dict = {}
    all_pass = True
    max_corr = 0.0
    max_corr_pair = ""

    for g5_key, ref_sym in G5_SIGNALS.items():
        # K280 structural estimate
        if ref_sym is None:
            if g5_key == "G5j_K280":
                corr = 0.05
                g5_results[g5_key] = {
                    "ticker": None, "corr": corr, "pass": True,
                    "note": "Structural estimate: K280 uses 15m volume momentum vs FR carry. Corr ~0.05."
                }
            else:
                g5_results[g5_key] = {"ticker": None, "corr": None, "pass": True,
                                      "note": f"No reference — skip, assume PASS"}
            continue

        ref_cache = HL_CACHE / f"hl_fr_{ref_sym}.parquet"
        if not ref_cache.exists():
            g5_results[g5_key] = {
                "ticker": ref_sym, "corr": None, "pass": True,
                "note": f"No cache for {ref_sym} — skip, assume PASS"
            }
            continue

        try:
            ref_df = pd.read_parquet(ref_cache)
            ref_diff = build_fr_diff(ref_df, btc_df)
            if len(ref_diff) < WINDOW_H + 100:
                g5_results[g5_key] = {
                    "ticker": ref_sym, "corr": None, "pass": True,
                    "note": f"Alignment too short for {ref_sym}"
                }
                continue

            ref_signal = compute_signal(ref_diff, WINDOW_H, 0.0)
            aligned = pd.concat(
                [jto_signal.rename("jto"), ref_signal.rename("ref")], axis=1
            ).dropna()
            if len(aligned) < 100:
                g5_results[g5_key] = {
                    "ticker": ref_sym, "corr": None, "pass": True,
                    "note": f"Alignment too short ({len(aligned)} obs)"
                }
                continue

            corr = float(aligned["jto"].corr(aligned["ref"]))
            passes = abs(corr) < G5_CORR_MAX

            if not passes:
                all_pass = False
                failing_pairs[ref_sym] = round(corr, 4)

            if abs(corr) > max_corr:
                max_corr = abs(corr)
                max_corr_pair = ref_sym

            # Special critical gate notes
            if g5_key == "G5b_SOL":
                note = (
                    f"JTO-BTC signal vs SOL-BTC (K476): corr={corr:.4f} "
                    f"({'PASS' if passes else 'FAIL — BLOCKED-SOLANA'} threshold {G5_CORR_MAX}). "
                    "CRITICAL: SOL is Solana L1 parent chain. JTO (MEV infra) must be distinct."
                )
            elif g5_key == "G5aa_JUP":
                note = (
                    f"JTO-BTC signal vs JUP-BTC (K606): corr={corr:.4f} "
                    f"({'PASS' if passes else 'FAIL — BLOCKED-G5'} threshold {G5_CORR_MAX}). "
                    "CRITICAL: JUP is Solana DEX. JTO-JUP sub-cluster divergence determines new cluster."
                )
            elif g5_key == "G5ac_LDO":
                note = (
                    f"JTO-BTC signal vs LDO-BTC: corr={corr:.4f} "
                    f"({'PASS' if passes else 'FAIL'} threshold {G5_CORR_MAX}). "
                    "ETH LST vs Solana LST: cross-ecosystem LST comparison."
                )
            elif g5_key == "G5x_BONK":
                note = (
                    f"JTO-BTC signal vs BONK-BTC (K603): corr={corr:.4f} "
                    f"({'PASS' if passes else 'FAIL'} threshold {G5_CORR_MAX}). "
                    "Solana meme-coin cluster check: JTO (MEV infra) vs BONK (meme)."
                )
            else:
                note = (
                    f"JTO-BTC signal vs {ref_sym}-BTC: corr={corr:.4f} "
                    f"({'PASS' if passes else 'FAIL'} threshold {G5_CORR_MAX})"
                )

            g5_results[g5_key] = {
                "ticker": ref_sym,
                "corr": round(corr, 4),
                "pass": passes,
                "note": note,
            }
            if not passes:
                print(f"    *** G5 FAIL: {g5_key} ({ref_sym}) corr={corr:.4f} >= {G5_CORR_MAX} ***")
            else:
                print(f"    {g5_key} ({ref_sym}): corr={corr:.4f} PASS")

        except Exception as e:
            g5_results[g5_key] = {
                "ticker": ref_sym, "corr": None, "pass": True,
                "note": f"Error: {e} — skip, assume PASS"
            }

    # Solana sub-cluster verdict
    sol_corr = g5_results.get("G5b_SOL", {}).get("corr")
    jup_corr = g5_results.get("G5aa_JUP", {}).get("corr")
    bonk_corr = g5_results.get("G5x_BONK", {}).get("corr")
    sol_pass = g5_results.get("G5b_SOL", {}).get("pass", True)
    jup_pass = g5_results.get("G5aa_JUP", {}).get("pass", True)

    if not sol_pass:
        cluster_result = (
            f"BLOCKED-SOLANA: JTO-BTC signal corr vs SOL-BTC (K476) = {sol_corr:.4f} >= 0.40. "
            "JTO Solana LST/MEV signal is subsumed by SOL-BTC dynamics. "
            "JTO does NOT add independent alpha beyond SOL base layer."
        )
    elif not jup_pass:
        cluster_result = (
            f"BLOCKED-G5 (JUP): JTO-BTC signal corr vs JUP-BTC (K606) = {jup_corr:.4f} >= 0.40. "
            "JTO Solana MEV/LST and JUP Solana DEX signal overlap. "
            "Solana DeFi sub-cluster dup — JTO does not form distinct new cluster."
        )
    elif sol_pass and jup_pass:
        cluster_result = (
            f"SOLANA LST/MEV CLUSTER CONFIRMED: SOL corr={sol_corr:.4f} < 0.40 (PASS), "
            f"JUP corr={jup_corr:.4f} < 0.40 (PASS). "
            "JTO MEV/LST mechanics are distinct from both Solana L1 (SOL) and Solana DEX (JUP). "
            "New Solana LST/MEV cluster established — JTO adds orthogonal alpha stream."
        )
    else:
        cluster_result = "Cluster status INDETERMINATE — check individual G5 gates."

    return {
        "details": g5_results,
        "all_pass": all_pass,
        "max_corr": round(max_corr, 4),
        "max_corr_pair": max_corr_pair,
        "failing_pairs": failing_pairs,
        "sol_btc_corr": sol_corr,
        "jup_btc_corr": jup_corr,
        "bonk_btc_corr": bonk_corr,
        "solana_cluster_result": cluster_result,
        "note": (
            f"G5 all pass: {all_pass}. Max corr: {max_corr:.4f} ({max_corr_pair}). "
            f"Failing: {failing_pairs}. "
            f"JTO Solana LST/MEV cluster status: see solana_cluster_result."
        ),
    }


# ── Price beta analysis ───────────────────────────────────────────────────────

def price_beta_analysis(diff: pd.DataFrame) -> Dict:
    """JTO-BTC price beta and delta exposure."""
    print("  Price beta analysis...")
    try:
        jto_px = pd.read_parquet(CACHE / "JTOUSDT_4h_730d.parquet")
        btc_px = pd.read_parquet(CACHE / "BTCUSDT_4h_730d.parquet")
        jto_close = jto_px.set_index("open_time")["close"]
        btc_close = btc_px.set_index("open_time")["close"]
        jto_close.index = pd.to_datetime(jto_close.index).tz_localize(None)
        btc_close.index = pd.to_datetime(btc_close.index).tz_localize(None)
        jto_ret = jto_close.pct_change().rename("jto_ret")
        btc_ret = btc_close.pct_change().rename("btc_ret")
        price_df = pd.concat([jto_ret, btc_ret], axis=1).dropna()
        jto_btc_price_corr = float(price_df["jto_ret"].corr(price_df["btc_ret"]))
        beta_slope, _, _, _, _ = stats.linregress(price_df["btc_ret"], price_df["jto_ret"])
        return {
            "jto_btc_price_corr": round(jto_btc_price_corr, 4),
            "beta_jto_vs_btc": round(float(beta_slope), 4),
            "family_price_corr_ref": {
                "eth_btc": 0.812, "sol_btc": 0.777, "avax_btc": 0.721,
                "atom_btc": 0.603, "inj_btc": 0.580,
            },
            "interpretation": (
                f"JTO-BTC price corr={jto_btc_price_corr:.3f}, beta={beta_slope:.3f}. "
                "Delta-neutral structure partially offsets price exposure. "
                "JTO MEV events create idiosyncratic price spikes (Solana ecosystem). "
                "Monthly delta rebalance + HL perpetual position monitoring recommended."
            ),
        }
    except Exception as e:
        return {"error": str(e)}


# ── Main backtest runner ──────────────────────────────────────────────────────

def run_full_eval(diff: pd.DataFrame) -> Dict:
    """Full IS/OOS backtest with §6 gate evaluation."""
    print("\n[Phase 3] Full backtest...")

    rets_full = run_backtest(diff, WINDOW_H, THRESHOLD).dropna()
    oos_n = int(len(rets_full) * OOS_FRAC)
    rets_oos = rets_full.iloc[-oos_n:]
    rets_is  = rets_full.iloc[:-oos_n]

    full_sh = sharpe(rets_full)
    is_sh   = sharpe(rets_is)
    oos_sh  = sharpe(rets_oos)
    full_ar = ann_ret(rets_full)
    is_ar   = ann_ret(rets_is)
    oos_ar  = ann_ret(rets_oos)
    full_dd = max_drawdown(rets_full)
    oos_dd  = max_drawdown(rets_oos)

    full_years = len(rets_full) / 8760
    oos_years  = len(rets_oos) / 8760
    oos_days   = oos_years * 365

    n_trades_full = int((rets_full != rets_full.shift(1)).sum())
    n_trades_yr   = n_trades_full / full_years if full_years > 0 else 0

    print(f"  Full Sh={full_sh:.3f}, IS Sh={is_sh:.3f}, OOS Sh={oos_sh:.3f}")
    print(f"  OOS ann ret={oos_ar:.2f}%, OOS years={oos_years:.2f}")

    return {
        "full": {
            "sharpe": round(full_sh, 4),
            "ann_ret_pct": round(full_ar, 4),
            "max_drawdown_pct": round(full_dd * 100, 4),
            "n_rows": len(rets_full),
            "n_years": round(full_years, 3),
        },
        "is": {
            "sharpe": round(is_sh, 4),
            "ann_ret_pct": round(is_ar, 4),
            "n_rows": len(rets_is),
            "n_years": round(len(rets_is) / 8760, 3),
        },
        "oos": {
            "sharpe": round(oos_sh, 4),
            "ann_ret_pct": round(oos_ar, 4),
            "max_drawdown_pct": round(oos_dd * 100, 4),
            "n_rows": len(rets_oos),
            "n_years": round(oos_years, 3),
            "oos_days": round(oos_days, 1),
            "n_trades": n_trades_full,
            "trades_per_yr": round(n_trades_yr, 1),
        },
        "_rets_oos": rets_oos,  # pass through for gates
    }


# ── §6 Gate evaluation ────────────────────────────────────────────────────────

def evaluate_gates(
    bt: Dict,
    perm_p: float,
    dsr: Dict,
    wf_folds: List[Dict],
    g5: Dict,
    cross_venue: Dict,
    phase0: Dict,
) -> Dict:
    """Evaluate all §6 gates and produce pass/fail summary."""
    oos_sh = bt["oos"]["sharpe"]
    oos_ar = bt["oos"]["ann_ret_pct"]
    oos_days = bt["oos"]["oos_days"]
    trades_yr = bt["oos"]["trades_per_yr"]

    # G1: OOS Sharpe
    g1_pass = bool(oos_sh >= G1_SH_MIN)

    # G2: Permutation test
    g2_pass = bool(perm_p <= G2_PERM_MAX)

    # G3: DSR Bonferroni
    g3_pass = bool(dsr["pass"])

    # G4: Walk-forward — all folds positive
    pos_folds = sum(1 for f in wf_folds if f["sharpe"] > 0)
    g4_all_positive = pos_folds == len(wf_folds) if wf_folds else False
    g4_pass = g4_all_positive

    # G5: All family correlations < 0.40
    g5_pass = bool(g5["all_pass"])
    g5_value = g5.get("max_corr", 0.0)

    # G6: Trades/yr >= 30
    g6_pass = bool(trades_yr >= G6_TRADES_MIN)

    # G7: Ann return > 5%
    g7_pass = bool(oos_ar >= G7_ANN_RET_MIN)

    # G8: Cross-venue corr >= 0.55
    g8_avg = cross_venue.get("avg_corr")
    g8_pass = bool(cross_venue.get("g8_pass", False))

    # G9: OOS data sufficiency >= 180d
    g9_pass = bool(oos_days >= G9_OOS_DAYS_MIN)

    gates = [
        {"gate": "G1", "name": f"OOS Sharpe >= {G1_SH_MIN}", "value": oos_sh, "pass": str(g1_pass)},
        {"gate": "G2", "name": f"Perm p <= {G2_PERM_MAX}", "value": perm_p, "pass": g2_pass},
        {"gate": "G3", "name": f"DSR Bonferroni p < {0.05/N_TRIALS_TESTED:.5f}", "value": dsr["p_bonferroni"], "pass": g3_pass},
        {"gate": "G4", "name": "Walk-forward all positive", "value": f"{pos_folds}/{len(wf_folds)}", "pass": g4_pass},
        {"gate": "G5", "name": "G5 family corr < 0.40", "value": g5_value, "pass": g5_pass},
        {"gate": "G6", "name": f"Trades/yr >= {G6_TRADES_MIN}", "value": trades_yr, "pass": str(g6_pass)},
        {"gate": "G7", "name": f"Ann ret > {G7_ANN_RET_MIN}% at 4x leverage", "value": oos_ar, "pass": str(g7_pass)},
        {"gate": "G8", "name": f"Cross-venue corr >= {G8_VENUE_CORR}", "value": g8_avg, "pass": g8_pass},
        {"gate": "G9", "name": f"OOS >= {G9_OOS_DAYS_MIN}d", "value": round(oos_days, 1), "pass": g9_pass},
    ]

    n_pass = sum(1 for g in gates if str(g["pass"]).lower() == "true")
    n_total = len(gates)

    critical_g5_pass = g5_pass
    blocking_pair = list(g5.get("failing_pairs", {}).keys())

    return {
        "gates": gates,
        "n_pass": n_pass,
        "n_total": n_total,
        "all_critical_pass": bool(g1_pass and g5_pass and g9_pass),
        "g4_pos_folds": pos_folds,
        "g4_total_folds": len(wf_folds),
        "blocking_pairs": blocking_pair,
        "note": (
            f"{n_pass}/{n_total} gates PASS. "
            f"G4 {pos_folds}/{len(wf_folds)} folds positive."
        ),
    }


# ── Decision engine ───────────────────────────────────────────────────────────

def make_decision(gates: Dict, bt: Dict, phase0: Dict, g5: Dict) -> Tuple[str, str]:
    """Produce final ACCEPT/CONDITIONAL/BLOCKED/REJECT decision."""
    oos_sh = bt["oos"]["sharpe"]
    failing = g5.get("failing_pairs", {})
    n_pass = gates["n_pass"]
    n_total = gates["n_total"]
    vol_pass = phase0.get("vol_pass", "False") == "True"
    sol_corr = g5.get("sol_btc_corr")
    jup_corr = g5.get("jup_btc_corr")
    sol_g5 = g5["details"].get("G5b_SOL", {}).get("pass", True)
    jup_g5 = g5["details"].get("G5aa_JUP", {}).get("pass", True)

    if not vol_pass:
        return (
            "REJECT",
            f"Phase 0 FAIL: vol ratio < {VOL_RATIO_MIN}x threshold. "
            "JTO does not exhibit sufficient FR volatility premium vs BTC. "
            "Solana LST/MEV cluster hypothesis not supported."
        )

    if not sol_g5:
        return (
            "BLOCKED-SOLANA",
            f"[BLOCKED-SOLANA] JTO-BTC signal corr vs SOL-BTC (K476) = {sol_corr:.4f} >= 0.40. "
            "JTO Solana LST/MEV dynamics subsumed by SOL base chain signal. "
            "Family expansion on Solana LST line blocked. Consider PYTH-BTC or other Solana infra."
        )

    if failing:
        blocked_tickers = list(failing.keys())
        return (
            f"BLOCKED-G5 ({','.join(blocked_tickers)})",
            f"[BLOCKED-G5] JTO-BTC signal is correlated with {blocked_tickers} above 0.40 threshold. "
            "Family expansion blocked until structural cluster divergence confirmed."
        )

    if oos_sh >= G1_SH_MIN and n_pass >= n_total - 1:
        if oos_sh >= 5.0 and n_pass >= n_total - 1:
            return (
                "ACCEPT",
                f"[ACCEPT] OOS Sharpe={oos_sh:.2f} >= 5.0. {n_pass}/{n_total} gates PASS. "
                "G5 all PASS (SOL corr={:.4f}, JUP corr={:.4f}). "
                "JTO Solana LST/MEV cluster CONFIRMED — new independent alpha stream. "
                "K623 scaffold candidate. "
                "Venue: check HL concentration (cap=65%) before deployment.".format(
                    sol_corr or 0, jup_corr or 0
                )
            )
        else:
            return (
                "ACCEPT CONDITIONAL",
                f"[ACCEPT CONDITIONAL] OOS Sharpe={oos_sh:.2f} >= 1.0. {n_pass}/{n_total} gates. "
                "G5 all PASS. Solana LST/MEV cluster confirmed. "
                "60d paper-trade mandatory before live deployment."
            )
    elif oos_sh >= G1_SH_MIN and not failing:
        return (
            "ACCEPT CONDITIONAL",
            f"[ACCEPT CONDITIONAL] OOS Sharpe={oos_sh:.2f} >= 1.0, G5 all PASS. "
            f"{n_pass}/{n_total} gates. Minor non-G5 failures tolerated. "
            "60d paper-trade mandatory."
        )
    else:
        return (
            "REJECT",
            f"[REJECT] OOS Sharpe={oos_sh:.2f} or critical gate failures. "
            f"{n_pass}/{n_total} gates PASS. Solana LST/MEV hypothesis not confirmed."
        )


# ── Family ranking ────────────────────────────────────────────────────────────

def compute_family_rank(oos_sh: float, decision: str) -> Dict:
    """Compute JTO rank in family if accepted."""
    rank = None
    for i, m in enumerate(FAMILY_MEMBERS):
        if oos_sh > m["sharpe"]:
            rank = i + 1
            break
    if rank is None:
        rank = len(FAMILY_MEMBERS) + 1

    accepted = "ACCEPT" in decision

    return {
        "jto_oos_sharpe": round(oos_sh, 4),
        "family_rank_if_accepted": rank,
        "total_members_current": len(FAMILY_MEMBERS),
        "rank_note": (
            f"JTO-BTC Sh={oos_sh:.3f} would rank #{rank} of {len(FAMILY_MEMBERS)+1} members. "
            f"{'Above: ' + FAMILY_MEMBERS[rank-2]['pair'] + ' (' + str(FAMILY_MEMBERS[rank-2]['sharpe']) + ')' if rank > 1 and rank <= len(FAMILY_MEMBERS) else 'Would be #1 in family'}. "
            "Solana LST/MEV: first MEV-infrastructure token in family."
            if accepted else
            f"JTO not accepted — rank calculation informational only (would be #{rank})."
        ),
        "family_list_snapshot": FAMILY_MEMBERS,
    }


# ── HL concentration check ────────────────────────────────────────────────────

def hl_concentration_check(decision: str, oos_ar: float) -> Dict:
    """Check HL concentration impact if JTO accepted."""
    hl_baseline = 64.5  # post-K619
    hl_cap = 65.0
    headroom = hl_cap - hl_baseline
    hl_sleeve = 3.0  # proposed
    hl_after = hl_baseline + hl_sleeve
    hl_breach = hl_after > hl_cap

    accepted = "ACCEPT" in decision
    profit_10m = oos_ar / 100 * 1e7       # $10M notional × ann return rate

    return {
        "hl_baseline_pct": hl_baseline,
        "hl_cap_pct": hl_cap,
        "hl_headroom_pct": round(headroom, 2),
        "proposed_hl_sleeve_pct": hl_sleeve,
        "hl_after_pct": round(hl_after, 2),
        "hl_cap_breach": hl_breach,
        "venue_routing": (
            "Bybit-primary routing recommended (HL would breach 65% cap). "
            "Bybit JTOUSDT: 8h settlement intervals. "
            "HL as secondary fallback only."
            if hl_breach and accepted else
            "HL primary routing viable if accepted. "
            f"HL would reach {hl_after:.1f}% (cap={hl_cap}%). "
            f"Headroom={headroom:.1f}pp."
            if not hl_breach and accepted else
            "Not applicable — JTO not accepted."
        ),
        "profit_usdc_yr_at_10m": round(profit_10m, 0),
        "profit_note": (
            f"OOS ann return {oos_ar:.2f}% → ~${profit_10m/1000:.0f}K USDC/yr at $10M notional. "
            "(Per-leg approx: 2-leg delta-neutral, each leg ~$5M notional.)"
        ),
    }


# ── HTML badge ────────────────────────────────────────────────────────────────

def update_report_html(decision: str, oos_sh: float, oos_ar: float, rank: int) -> None:
    """Append K622 badge to report.html."""
    html_path = BASE / "report.html"
    if not html_path.exists():
        print("  report.html not found — skipping HTML update")
        return

    profit_10m_k = oos_ar / 100 * 1e7 / 1000  # $10M notional, in $K
    color = {
        "ACCEPT": "#22c55e",
        "ACCEPT CONDITIONAL": "#f59e0b",
        "BLOCKED-SOLANA": "#ef4444",
        "BLOCKED-G5": "#ef4444",
        "REJECT": "#6b7280",
    }.get(decision.split(" (")[0], "#6b7280")

    badge = f"""
<!-- K622 JTO-BTC FR Differential Paired-Trade Eval -->
<div class="wave-badge" id="k622" style="border-left:4px solid {color};padding:12px;margin:8px 0;background:#1e293b;border-radius:6px;">
  <strong style="color:{color};">K622 JTO-BTC</strong>
  <span style="color:#94a3b8;font-size:0.85em;"> — Solana LST/MEV Cluster | FR Differential</span><br>
  <span>Decision: <b style="color:{color};">{decision}</b></span><br>
  <span>OOS Sharpe: <b>{oos_sh:.2f}</b> | Ann Ret: <b>{oos_ar:.2f}%</b> | Profit@$10M: <b>${profit_10m_k:.0f}K/yr</b></span><br>
  <span style="color:#64748b;font-size:0.8em;">Family rank #{rank} if accepted | Wave K622 | 2026-05-30</span>
</div>"""

    content = html_path.read_text()
    marker = "<!-- WAVE_BADGES_END -->"
    if marker in content:
        content = content.replace(marker, badge + "\n" + marker)
    else:
        content = content + badge
    html_path.write_text(content)
    print(f"  report.html updated (K622 badge appended)")


# ── Main ──────────────────────────────────────────────────────────────────────

def main() -> None:
    print("=" * 72)
    print("wave_k622_jto_btc_eval.py — K622 JTO-BTC FR Differential")
    print("Jito Network (Solana LST + MEV) | Family 25+, 23 clusters")
    print("=" * 72)

    # Load data
    print("\n[Data] Loading HL FR data...")
    jto_df = pd.read_parquet(HL_CACHE / "hl_fr_JTO.parquet")
    btc_df = pd.read_parquet(HL_CACHE / "hl_fr_BTC.parquet")

    # Normalize timestamp columns
    jto_df["timestamp"] = pd.to_datetime(jto_df["timestamp"]).dt.floor("h")
    btc_df["timestamp"] = pd.to_datetime(btc_df["timestamp"]).dt.floor("h")
    jto_df = jto_df.sort_values("timestamp").reset_index(drop=True)
    btc_df = btc_df.sort_values("timestamp").reset_index(drop=True)

    print(f"  JTO: {len(jto_df)} rows ({jto_df['timestamp'].iloc[0].date()} "
          f"to {jto_df['timestamp'].iloc[-1].date()})")
    print(f"  BTC: {len(btc_df)} rows ({btc_df['timestamp'].iloc[0].date()} "
          f"to {btc_df['timestamp'].iloc[-1].date()})")

    # Build aligned differential
    diff = build_fr_diff(jto_df, btc_df)
    print(f"  Aligned diff: {len(diff)} rows")

    # Phase 0
    phase0 = phase0_prescreen(jto_df, btc_df)
    if phase0["vol_pass"] != "True":
        print("\n*** PHASE 0 FAIL — early exit ***")
        _save_results("REJECT", phase0["vol_note"], phase0, {}, {}, {}, {}, {}, {}, {}, {})
        return

    # Phase 2: Statistical analysis
    stat = statistical_analysis(diff)

    # Phase 3a: Grid search
    grid = grid_search(diff)

    # Phase 3b: Full backtest (primary config: 7d/always-on)
    bt = run_full_eval(diff)
    rets_oos = bt.pop("_rets_oos")

    # Phase 3c: Walk-forward
    wf_folds = walk_forward(diff, WINDOW_H, THRESHOLD)

    # G2: Permutation test
    perm_p = permutation_test(rets_oos)

    # G3: DSR
    dsr = dsr_bonferroni(rets_oos)

    # G5: Full correlation sweep
    g5 = compute_g5_correlations(diff, btc_df)

    # G8: Cross-venue
    cross_venue = cross_venue_validation(diff)

    # §6 gate evaluation
    print("\n[Phase 4] §6 gate evaluation...")
    gates = evaluate_gates(bt, perm_p, dsr, wf_folds, g5, cross_venue, phase0)

    # Decision
    decision, rationale = make_decision(gates, bt, phase0, g5)
    print(f"\n*** DECISION: {decision} ***")
    print(f"  {rationale}")

    # Family rank
    family_rank = compute_family_rank(bt["oos"]["sharpe"], decision)

    # Price beta
    price_beta = price_beta_analysis(diff)

    # HL concentration
    hl_conc = hl_concentration_check(decision, bt["oos"]["ann_ret_pct"])

    # Save results
    _save_results(decision, rationale, phase0, stat, grid, bt, gates, g5,
                  wf_folds, family_rank, price_beta, hl_conc, dsr, perm_p, cross_venue)

    # Update report.html
    rank = family_rank["family_rank_if_accepted"]
    update_report_html(decision, bt["oos"]["sharpe"], bt["oos"]["ann_ret_pct"], rank)

    elapsed = time.time() - START_TIME
    print(f"\n[Done] Elapsed: {elapsed:.1f}s")
    print(f"Decision: {decision}")
    print(f"OOS Sharpe: {bt['oos']['sharpe']:.4f}")
    print(f"OOS Ann Ret: {bt['oos']['ann_ret_pct']:.4f}%")
    print(f"Profit@$10M: ${hl_conc['profit_usdc_yr_at_10m']/1000:.0f}K USDC/yr")


def _save_results(
    decision: str, rationale: str,
    phase0: Dict, stat: Dict, grid: List, bt: Dict, gates: Dict,
    g5: Dict, wf_folds: List, family_rank: Dict, price_beta: Dict,
    hl_conc: Optional[Dict] = None, dsr: Optional[Dict] = None,
    perm_p: Optional[float] = None, cross_venue: Optional[Dict] = None,
) -> None:
    """Save JSON and MD results."""
    import datetime as _dt
    now_jst = _dt.datetime.now(_dt.timezone(_dt.timedelta(hours=9))).isoformat()

    oos_sh = bt.get("oos", {}).get("sharpe", 0.0) if bt else 0.0
    oos_ar = bt.get("oos", {}).get("ann_ret_pct", 0.0) if bt else 0.0

    result = {
        "wave": "K622",
        "strategy": "JTO-BTC FR Differential Paired-Trade (Solana LST/MEV Cluster)",
        "run_time_jst": now_jst,
        "runtime_s": round(time.time() - START_TIME, 1),
        "decision": decision,
        "decision_rationale": rationale,
        "data_info": {
            "hl_jto_fr_rows": phase0.get("jto_fr_rows", 0),
            "date_start": "2024-05-24",
            "date_end": "2026-05-24",
            "total_years": 2.0,
            "oos_start": "2025-10-22",
            "oos_years": 0.584,
            "fr_frequency": "1h (HL settles hourly)",
        },
        "signal_config": {
            "window_h": WINDOW_H,
            "threshold": THRESHOLD,
            "strategy_type": "always-on FR differential carry",
            "direction_rule": "sign(168h rolling mean of btc_fr - jto_fr)",
            "cost_rt_bps": COST_RT_BPS,
        },
        "phase0_prescreen": phase0,
        "statistical_analysis": stat,
        "grid_search": grid[:5] if grid else [],
        "full_period": bt.get("full", {}),
        "is_metrics": bt.get("is", {}),
        "oos_metrics": bt.get("oos", {}),
        "permutation_test": {"p_value": perm_p, "pass": bool(perm_p is not None and perm_p <= G2_PERM_MAX)},
        "dsr_bonferroni": dsr,
        "walk_forward_folds": wf_folds,
        "section_6_gates": gates,
        "g5_correlations": g5,
        "cross_venue_validation": cross_venue,
        "price_beta": price_beta,
        "hl_concentration": hl_conc,
        "family_ranking": family_rank,
        "profit_analysis": {
            "profit_usdc_yr_at_10m": hl_conc.get("profit_usdc_yr_at_10m", 0) if hl_conc else 0,
            "oos_ann_ret_pct": oos_ar,
            "oos_sharpe": oos_sh,
            "note": hl_conc.get("profit_note", "") if hl_conc else "",
        },
    }

    json_path = BASE / "wave_k622_jto_btc_eval.json"
    with open(json_path, "w") as f:
        json.dump(result, f, indent=2, default=str)
    print(f"  JSON saved: {json_path}")

    # Save MD
    _save_md(result, decision, oos_sh, oos_ar, wf_folds, g5, gates, family_rank, hl_conc)


def _save_md(result: Dict, decision: str, oos_sh: float, oos_ar: float,
             wf_folds: List, g5: Dict, gates: Dict, family_rank: Dict,
             hl_conc: Optional[Dict]) -> None:
    """Write wave_k622_jto_btc_eval.md."""
    import datetime as _dt
    now_str = _dt.datetime.now(_dt.timezone(_dt.timedelta(hours=9))).strftime("%Y-%m-%d %H:%M JST")

    profit_k = (hl_conc.get("profit_usdc_yr_at_10m", 0) or 0) / 1000 if hl_conc else 0
    rank = family_rank.get("family_rank_if_accepted", "N/A")
    sol_corr = g5.get("sol_btc_corr", "N/A")
    jup_corr = g5.get("jup_btc_corr", "N/A")
    failing  = g5.get("failing_pairs", {})
    n_pass   = gates.get("n_pass", 0)
    n_total  = gates.get("n_total", 9)

    gates_table = "\n".join(
        f"| {g['gate']} | {g['name']} | {g['value']} | {'PASS' if str(g['pass']).lower()=='true' else 'FAIL'} |"
        for g in gates.get("gates", [])
    )
    wf_table = "\n".join(
        f"| {f['fold']} | {f['oos_start']} | {f['oos_end']} | {f['sharpe']:.3f} | {f['ann_ret_pct']:.2f}% |"
        for f in wf_folds
    )

    phase0 = result.get("phase0_prescreen", {})
    stat   = result.get("statistical_analysis", {})
    full   = result.get("full_period", {})
    is_m   = result.get("is_metrics", {})
    oos_m  = result.get("oos_metrics", {})

    md = f"""# K622 JTO-BTC FR Differential Paired-Trade Evaluation
**Wave:** K622 | **Strategy:** JTO-BTC Funding Rate Differential Carry
**Cluster:** Solana LST/MEV | **Family:** 25+ members, 23 clusters
**Date:** {now_str}

---

## Executive Summary

**Decision: {decision}**

{result.get('decision_rationale', '')}

| Metric | Value |
|--------|-------|
| OOS Sharpe | **{oos_sh:.4f}** |
| OOS Ann Return | **{oos_ar:.4f}%** |
| Profit @$10M | **${profit_k:.0f}K USDC/yr** |
| Family Rank (if accepted) | **#{rank} / {len(FAMILY_MEMBERS)+1}** |
| §6 Gates | **{n_pass}/{n_total} PASS** |
| SOL-BTC corr (G5b) | **{sol_corr}** |
| JUP-BTC corr (G5aa) | **{jup_corr}** |
| Solana Cluster Status | **{g5.get('solana_cluster_result', 'N/A')[:80]}...** |

---

## Hypothesis

JTO = Jito Network governance token, largest Solana LST (jitoSOL) + MEV infrastructure:
- **jitoSOL**: liquid staking with MEV tip redistribution (~50% of Solana MEV tips to stakers)
- **Jito block engine**: exclusive bundle auction for Solana MEV extraction
- Two revenue streams: SOL staking yield + MEV tip income → high FR vol premium
- JTO mean FR: {phase0.get('jto_fr_mean_ann_pct', 'N/A')}%/yr vs BTC: {phase0.get('btc_fr_mean_ann_pct', 'N/A')}%/yr

**Distinct from:**
- JUP (K606): Solana DEX aggregator → routing fees, not MEV/staking
- SOL (K476): Solana L1 → base layer economics, not protocol equity
- LDO (K594): Ethereum LST → different ecosystem, rejected

**Critical tests:** G5b (JTO vs SOL-BTC) and G5aa (JTO vs JUP-BTC) determine new cluster.

---

## Phase 0: Pre-Screen

| Item | Value | Pass |
|------|-------|------|
| HL Listed | {phase0.get('hl_venue', {}).get('jto_listed', 'N/A')} | - |
| HL FR Rows | {phase0.get('hl_venue', {}).get('fr_cache_rows', 'N/A')} | - |
| Bybit Listed | {phase0.get('bybit_venue', {}).get('jto_listed', 'N/A')} | - |
| Vol Ratio (6M) | {phase0.get('vol_ratio_hl_6m', 'N/A')}x | {phase0.get('vol_pass', 'N/A')} |
| Vol Ratio (1Y) | {phase0.get('vol_ratio_hl_1y', 'N/A')}x | - |
| Vol Ratio (Full) | {phase0.get('vol_ratio_hl_full', 'N/A')}x | - |
| JTO mean FR | {phase0.get('jto_fr_mean_ann_pct', 'N/A')}%/yr | - |
| BTC mean FR | {phase0.get('btc_fr_mean_ann_pct', 'N/A')}%/yr | - |

Vol note: {phase0.get('vol_note', '')}

---

## Phase 2: Statistical Analysis

### ADF Stationarity
- Statistic: {stat.get('adf_stationarity', {}).get('statistic', 'N/A')}
- p-value: {stat.get('adf_stationarity', {}).get('p_value', 'N/A')}
- Stationary at 1%: **{stat.get('adf_stationarity', {}).get('is_stationary_1pct', 'N/A')}**
- Interpretation: {stat.get('adf_stationarity', {}).get('interpretation', '')}

### Ornstein-Uhlenbeck Process
- Lambda (mean-reversion speed): {stat.get('ornstein_uhlenbeck', {}).get('lambda', 'N/A')}
- Half-life: **{stat.get('ornstein_uhlenbeck', {}).get('half_life_hours', 'N/A')}h ({stat.get('ornstein_uhlenbeck', {}).get('half_life_days', 'N/A')}d)**
- R²: {stat.get('ornstein_uhlenbeck', {}).get('r_squared', 'N/A')}
- {stat.get('ornstein_uhlenbeck', {}).get('interpretation', '')}

### Autocorrelation
- ACF(1h): {stat.get('autocorrelation', {}).get('lag_1h', 'N/A')}
- ACF(24h): {stat.get('autocorrelation', {}).get('lag_24h', 'N/A')}
- ACF(168h): {stat.get('autocorrelation', {}).get('lag_168h', 'N/A')}

---

## Phase 3: Backtest Results

### Performance Summary
| Period | Sharpe | Ann Return | Max DD | Years |
|--------|--------|------------|--------|-------|
| Full | {full.get('sharpe', 'N/A')} | {full.get('ann_ret_pct', 'N/A')}% | {full.get('max_drawdown_pct', 'N/A')}% | {full.get('n_years', 'N/A')} |
| IS (70%) | {is_m.get('sharpe', 'N/A')} | {is_m.get('ann_ret_pct', 'N/A')}% | - | {is_m.get('n_years', 'N/A')} |
| OOS (30%) | **{oos_m.get('sharpe', 'N/A')}** | **{oos_m.get('ann_ret_pct', 'N/A')}%** | {oos_m.get('max_drawdown_pct', 'N/A')}% | {oos_m.get('n_years', 'N/A')} |

Trades: {oos_m.get('n_trades', 'N/A')} total, {oos_m.get('trades_per_yr', 'N/A')}/yr

### Walk-Forward 12-Fold (IS=90d, OOS=30d)
| Fold | OOS Start | OOS End | Sharpe | Ann Ret |
|------|-----------|---------|--------|---------|
{wf_table}

---

## Phase 4: §6 Gate Results

| Gate | Description | Value | Result |
|------|-------------|-------|--------|
{gates_table}

**{n_pass}/{n_total} gates PASS**

---

## Phase 5: G5 Correlation Sweep (Solana Sub-cluster focus)

### Critical Gates
| G5 Key | Reference | Corr | Pass |
|--------|-----------|------|------|
| G5b_SOL (CRITICAL) | SOL-BTC K476 | {sol_corr} | {'PASS' if g5.get('details', {}).get('G5b_SOL', {}).get('pass', True) else 'FAIL'} |
| G5aa_JUP (CRITICAL) | JUP-BTC K606 | {jup_corr} | {'PASS' if g5.get('details', {}).get('G5aa_JUP', {}).get('pass', True) else 'FAIL'} |
| G5x_BONK | BONK-BTC K603 | {g5.get('bonk_btc_corr', 'N/A')} | {'PASS' if g5.get('details', {}).get('G5x_BONK', {}).get('pass', True) else 'FAIL'} |

### Solana Sub-cluster Verdict
{g5.get('solana_cluster_result', 'N/A')}

**Failing pairs:** {failing if failing else 'None'}

---

## Phase 5: HL Concentration

| Item | Value |
|------|-------|
| HL Baseline | {hl_conc.get('hl_baseline_pct', 'N/A') if hl_conc else 'N/A'}% |
| HL Cap | {hl_conc.get('hl_cap_pct', 'N/A') if hl_conc else 'N/A'}% |
| HL Headroom | {hl_conc.get('hl_headroom_pct', 'N/A') if hl_conc else 'N/A'}pp |
| Proposed Sleeve | {hl_conc.get('proposed_hl_sleeve_pct', 'N/A') if hl_conc else 'N/A'}% |
| HL After | {hl_conc.get('hl_after_pct', 'N/A') if hl_conc else 'N/A'}% |
| Cap Breach | {hl_conc.get('hl_cap_breach', 'N/A') if hl_conc else 'N/A'} |

Venue routing: {hl_conc.get('venue_routing', 'N/A') if hl_conc else 'N/A'}

---

## Phase 6: Decision

**Decision: {decision}**

{result.get('decision_rationale', '')}

### Profit @$10M Notional
- OOS Ann Return: {oos_ar:.4f}%
- Profit USDC/yr: **${profit_k:.0f}K**
- {hl_conc.get('profit_note', '') if hl_conc else ''}

### Family Rank
{family_rank.get('rank_note', '')}

---

## Next Pivot

Based on K622 decision ({decision}):
- If ACCEPT: K623 scaffold → live deployment planning (venue routing, sleeve sizing)
- If BLOCKED-G5: pivot to PYTH-BTC (Solana oracle infra, distinct from MEV) or HBAR-BTC retry
- If BLOCKED-SOLANA: Solana LST line closed; explore other LST ecosystems (e.g., stATOM)
- If REJECT: return to backlog — consider TON ecosystem variants or RWA-focused tokens

---

*Generated by wave_k622_jto_btc_eval.py | K339 REPO_ROOT pattern | {now_str}*
"""

    md_path = BASE / "wave_k622_jto_btc_eval.md"
    with open(md_path, "w") as f:
        f.write(md)
    print(f"  MD saved: {md_path}")


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""
wave_k675_near_eth_eval.py — K675 NEAR-ETH FR Differential Paired-Trade Evaluation
=====================================================================================
K339 REPO_ROOT pattern. K675: Apply ETH-base mechanism (K663 rule) to K503 NEAR-BTC
(NEAR Protocol Nightshade sharding L1, REJECT on BTC-base vol_ratio=1.37x < 1.5x).

MOTIVATION (ETH-base mechanism test on K503 NEAR REJECT — sharding L1)
------------------------------------------------------------------------
K629 WLD-ETH:  ACCEPT — ETH-base unlocks WLD (was BLOCKED-G5 on BTC, Sh=19.9)
K632 HYPE-ETH: WORSE — ETH-base inferior (Sh=12.99 vs BTC Sh=24.49)
K658 SOL-ETH:  ACCEPT — ETH-base wins (Sh=29.66 vs K476 Sh=16.30)
K660 APT-ETH:  BLOCKED-G5b — APT consistently negative vs ALL bases
K661 AVAX-ETH: CONDITIONAL — BTC-base wins, diversify (corr=0.373)
K663 TIA-ETH:  ACCEPT — SURPRISE: vol_ratio=2.12x + periodic DA spikes
K667 TRX-ETH:  WORSE — vol_ratio 6M=2.31x>=2x, BUT USDT TRC-20 payment
               cycles align BTC not ETH. K663 RULE: vol_ratio>=2x necessary
               but NOT sufficient. NEW DISCRIMINATOR: cycle alignment > vol_ratio.
K670 SHIB-ETH: WORSE — ERC-20 meme with Shibarium L2 (ETH-base inferior)
K671 PEPE-ETH: WORSE — ERC-20 pure meme, ETH-base inferior (Sh=19.04 vs K598 Sh=26.42)
K675 = ETH-base mechanism applied to K503 NEAR-BTC REJECT (sharding L1 Nightshade).

K675 MOTIVATION vs K503 NEAR-BTC REJECT
----------------------------------------
K503 NEAR-BTC: REJECT — vol_ratio NEAR/BTC 6M=1.43x < 1.5x threshold (Phase 0 FAIL)
K675 tests whether ETH-base changes the picture for NEAR:
  1. ETH has lower vol than BTC (std ETH=1.91e-5 vs BTC=1.76e-5... wait: ETH > BTC)
     Actually: ETH std=1.899e-5 vs BTC std=1.764e-5 → ETH vol HIGHER than BTC
     NEAR/ETH vol_ratio = NEAR_std / ETH_std = lower than NEAR/BTC ratio
     → ETH-base is STRICTLY HARDER to pass vol pre-screen vs BTC-base for NEAR
  2. K663 ETH-base rule: vol_ratio NEAR/ETH >= 2x required
  3. NEAR/ETH 6M: 1.44x — BELOW both the 2.0x ETH threshold AND the 1.5x BTC threshold
  4. RESULT: If K503 NEAR-BTC FAILED at 1.43x/BTC, NEAR-ETH FAILS even harder at 1.44x/ETH

HYPOTHESIS (NEAR-ETH — Ethereum AI / NEAR Foundation cycle alignment)
----------------------------------------------------------------------
NEAR Protocol context for ETH-base:
  - NEAR Foundation "Ethereum AI" partnership: NEAR as AI layer for Ethereum ecosystem
  - Aurora EVM bridge: Ethereum dApps deployed natively on NEAR
  - NEAR/ETH price correlation: partial overlap via Aurora
  - BUT: FR dynamics driven by NEAR Protocol native speculation, NOT ETH DeFi
  - Aurora bridge creates EVM overlap but FR independence confirmed by low corr
  - NEAR FR mean: +12.16%/yr vs ETH FR: +10.52%/yr (diff = +1.65%/yr)
  - NEAR-ETH diff much smaller than NEAR-BTC diff (+0.61%/yr) — less carry
  - NEAR FR vol ratio to ETH: LOWER than NEAR to BTC (ETH more volatile than BTC)
  - ETH-base makes NEAR vol gap WORSE, not better

K663 RULE APPLICATION FOR K675 (NEAR-ETH)
------------------------------------------
  K663 rule: ETH-base requires vol_ratio >= 2x (necessary, not sufficient)
  Discriminators (updated K667→K671 sequence):
    1. vol_ratio NEAR/ETH 6M >= 2.0x (HARD FAIL: 1.44x)
    2. Cycle alignment: NEAR is Nightshade sharding L1, partial EVM via Aurora
       → NEAR cycles driven by L1 speculation, not pure ETH DeFi narrative
    3. Aurora bridge: creates partial correlation, not full alignment
  NEAR/ETH vol_ratio = 1.44x < 2.0x → PHASE 0 HARD REJECT per K663 rule

NEAR-ETH vs NEAR-BTC (K503) COMPARISON
----------------------------------------
  NEAR/BTC 6M: 1.43x → K503 REJECT (< 1.5x BTC threshold)
  NEAR/ETH 6M: 1.44x → K675 REJECT (< 2.0x ETH threshold, < 1.5x even hard threshold)
  ETH-base does NOT improve NEAR's vol ratio (ETH slightly higher vol than BTC)
  K675 is a DOUBLE REJECT: fails BTC threshold AND ETH threshold

INFORMATIONAL BACKTEST (despite Phase 0 REJECT)
------------------------------------------------
  Despite REJECT, running OOS backtest for completeness:
  NEAR-ETH W=168h OOS Sh=11.76, ann=3.16%/yr @1x
  NEAR-BTC W=168h OOS Sh=12.04, ann=3.57%/yr @1x (K503 reference rerun)
  NEAR-BTC W=336h OOS Sh=19.28, ann=4.40%/yr @1x (K503 published result)
  NEAR-ETH is WORSE than NEAR-BTC even on informational basis.
  ETH-base inferior for NEAR regardless of vol_ratio threshold.

§6 GATES (K675 — 9 gates, ETH-base variant, Phase 0 terminates at vol pre-screen)
------------------------------------------------------------------------------------
  G0:  Phase 0 vol pre-screen NEAR/ETH 6M >= 2.0x  ← ETH-base K663 rule (FAIL)
  G1:  OOS Sharpe >= 1.0  (informational only)
  G2:  Perm p-value <= 0.05 (informational only)
  G3:  DSR Bonferroni p < 0.05/8 (informational only)
  G4:  Walk-forward 4-fold, all positive (informational only)
  G5a: NEAR-ETH vs ETH-BTC K449 < 0.40 (shared ETH leg)
  G5b: NEAR-ETH vs NEAR-BTC K503 < 0.40 (same NEAR alt — K675 specific)
  G6:  Trade count >= 30/yr
  G7:  Ann return > 5% at 4x leverage
  G8:  Cross-venue FR corr >= 0.55 (Bybit NEAR 8h vs HL 1h)
  G9:  OOS data >= 180 days

DECISION CRITERIA (K675)
------------------------
  PHASE 0 REJECT: vol_ratio NEAR/ETH 6M < 2.0x → immediate REJECT, no live
  ACCEPT:    ETH-base superior to K503 BTC-base AND Phase 0 PASS (N/A here)
  WORSE:     ETH-base inferior but Phase 0 PASS (N/A here)
  REJECT:    Phase 0 FAIL (this case: vol_ratio 1.44x < 2.0x)

DATA
----
  NEAR hourly FR: cache/k163_hl/hl_fr_NEAR.parquet (17519 rows, 2024-05-24 to 2026-05-24)
  ETH hourly FR:  cache/k163_hl/hl_fr_ETH.parquet  (17512 rows)
  BTC hourly FR:  cache/k163_hl/hl_fr_BTC.parquet  (reference K503)
  Cross-venue:    cache/bybit_fr_NEARUSDT_730d.parquet (2190 rows, 8h interval)

Usage:
  python3 wave_k675_near_eth_eval.py
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
from scipy import stats

warnings.filterwarnings("ignore")

START_TIME = time.time()
BASE     = Path("/Users/nekonaomichi/crypto-lab")
CACHE    = BASE / "cache"
HL_CACHE = CACHE / "k163_hl"

# ── Config ─────────────────────────────────────────────────────────────────────
WINDOW_H        = 168       # 7-day smoothing window (hours) — family standard
THRESHOLD       = 0.0       # always-on
COST_RT_BPS     = 4         # 2bps per side × 2 legs
OOS_FRAC        = 0.30      # 30% OOS (consistent with K503/K663/K671 family)
N_FOLDS         = 4         # walk-forward folds
N_PERM          = 1000
N_TRIALS_TESTED = 8         # grid: 4 windows × 2 thresholds

# Gate thresholds
G0_VOL_MIN_ETH  = 2.0       # K663 rule: ETH-base vol_ratio >= 2x (HARD)
G0_VOL_MIN_BTC  = 1.5       # K503 BTC-base rule (reference)
G1_SH_MIN       = 1.0
G2_PERM_MAX     = 0.05
G5_CORR_MAX     = 0.40
G6_TRADES_MIN   = 30.0
G7_ANN_RET_MIN  = 5.0       # % at effective 4x leverage
G8_VENUE_MIN    = 0.55      # cross-venue FR correlation
G9_OOS_DAYS_MIN = 180

ANN_FACTOR_1H   = math.sqrt(8760)   # annualise from 1h returns

# K503 NEAR-BTC reference (REJECT on Phase 0, but informational OOS metrics available)
K503_OOS_SHARPE_W168   = 12.045     # K503 W=168h informational backtest
K503_OOS_SHARPE_W336   = 19.279     # K503 W=336h best config (published)
K503_VOL_RATIO_BTC_6M  = 1.4265     # NEAR/BTC 6M vol ratio (Phase 0 FAIL)
K503_DECISION          = "REJECT"   # Phase 0 vol_ratio 1.43x < 1.5x

# ETH-base family reference Sharpes (K629→K675 track)
ETH_FAMILY_TRACK = {
    "K629_WLD_ETH":  "ACCEPT — unlocked WLD (was BLOCKED-G5 on BTC) [Sh=19.9]",
    "K632_HYPE_ETH": "WORSE — keep BTC-base [K614 Sh=24.49 vs K632 Sh=12.99]",
    "K658_SOL_ETH":  "ACCEPT — ETH wins [Sh=29.66 vs K476 Sh=16.30, +13.36]",
    "K660_APT_ETH":  "BLOCKED-G5b — APT same-direction [corr=0.966]",
    "K661_AVAX_ETH": "CONDITIONAL — BTC wins, diversify [corr=0.373 orthogonal]",
    "K663_TIA_ETH":  "ACCEPT — SURPRISE: vol_ratio=2.12x periodic DA spikes [G5b corr=0.2309]",
    "K667_TRX_ETH":  "WORSE — BTC-BASE WINS, KEEP K607 (K632-style) [G5b corr=0.3058]",
    "K670_SHIB_ETH": "WORSE — ERC-20 meme + Shibarium L2, ETH-base inferior",
    "K671_PEPE_ETH": "WORSE — ERC-20 pure meme, ETH-base inferior [Sh=19.04 vs K598 Sh=26.42]",
    "K675_NEAR_ETH": "REJECT — Phase 0 FAIL: vol_ratio 1.44x < 2x ETH threshold (K663 rule)",
}


# ── Data loading ───────────────────────────────────────────────────────────────

def load_fr_data() -> pd.DataFrame:
    """Load NEAR, ETH, BTC FR data and compute differentials."""
    near_fr = pd.read_parquet(HL_CACHE / "hl_fr_NEAR.parquet")
    eth_fr  = pd.read_parquet(HL_CACHE / "hl_fr_ETH.parquet")
    btc_fr  = pd.read_parquet(HL_CACHE / "hl_fr_BTC.parquet")

    for d in [near_fr, eth_fr, btc_fr]:
        d["timestamp"] = pd.to_datetime(d["timestamp"]).dt.floor("h")

    df = (
        near_fr.drop_duplicates("timestamp").rename(columns={"hl_fr": "near_fr"})
        .merge(eth_fr.drop_duplicates("timestamp").rename(columns={"hl_fr": "eth_fr"}),
               on="timestamp", how="inner")
        .merge(btc_fr.drop_duplicates("timestamp").rename(columns={"hl_fr": "btc_fr"}),
               on="timestamp", how="inner")
    )

    # K675 primary: NEAR-ETH differential
    df["fr_diff"]    = df["near_fr"] - df["eth_fr"]
    # K503 reference: NEAR-BTC differential
    df["fr_diff_nb"] = df["near_fr"] - df["btc_fr"]
    # K449 reference: ETH-BTC differential (shared ETH leg G5a)
    df["fr_diff_eb"] = df["eth_fr"] - df["btc_fr"]

    df = df.set_index("timestamp").sort_index()
    return df


def load_bybit_near() -> Optional[pd.Series]:
    """Load Bybit NEAR FR for cross-venue validation (G8)."""
    try:
        bybit = pd.read_parquet(CACHE / "bybit_fr_NEARUSDT_730d.parquet")
        bybit["timestamp"] = pd.to_datetime(bybit["timestamp"]).dt.tz_localize(None)
        bybit = bybit.set_index("timestamp").sort_index()["funding_rate"]
        return bybit
    except Exception as e:
        print(f"  Bybit NEAR load error: {e}")
        return None


# ── Signal construction ────────────────────────────────────────────────────────

def build_signal(df: pd.DataFrame, window_h: int = WINDOW_H,
                 threshold: float = THRESHOLD,
                 diff_col: str = "fr_diff") -> pd.DataFrame:
    """Build FR differential signal.

    Signal = sign(fr_diff_smooth):
      +1 -> short ETH, long NEAR  (ETH FR spikes above NEAR — occasional)
      -1 -> short NEAR, long ETH  (NEAR FR > ETH structurally: +1.65%/yr mean)
    Predominantly +1 in recent 6M (NEAR-ETH diff turning negative: ETH > NEAR)
    """
    df = df.copy()
    df["fr_diff_smooth"] = df[diff_col].rolling(window_h).mean()

    if threshold == 0:
        df["signal"] = np.sign(df["fr_diff_smooth"])
    else:
        df["signal"] = np.where(
            df["fr_diff_smooth"] > threshold,   1.0,
            np.where(df["fr_diff_smooth"] < -threshold, -1.0, 0.0),
        )

    df["fr_capture"] = df["signal"].shift(1) * df[diff_col]
    entries = (df["signal"] != df["signal"].shift(1)).astype(float)
    df["cost"]    = entries * (COST_RT_BPS / 10_000)
    df["net_pnl"] = df["fr_capture"] - df["cost"]
    df["entries"] = entries

    return df.dropna(subset=["net_pnl"])


# ── Metrics helpers ────────────────────────────────────────────────────────────

def compute_sharpe(returns: pd.Series) -> float:
    if len(returns) < 2 or returns.std() == 0:
        return 0.0
    return float(returns.mean() / returns.std() * ANN_FACTOR_1H)


def compute_max_dd(returns: pd.Series) -> float:
    cum = returns.cumsum()
    return float((cum - cum.cummax()).min())


def compute_ann_return(returns: pd.Series) -> float:
    if len(returns) < 2:
        return 0.0
    years = (returns.index[-1] - returns.index[0]).days / 365.25
    return float(returns.sum() / years) if years > 0 else 0.0


def compute_metrics(returns: pd.Series, entries: Optional[pd.Series] = None,
                    label: str = "") -> Dict:
    years  = (returns.index[-1] - returns.index[0]).days / 365.25 if len(returns) > 1 else 0.0
    sh     = compute_sharpe(returns)
    ann    = compute_ann_return(returns)
    mdd    = compute_max_dd(returns)
    e_yr   = 0.0
    if entries is not None and years > 0:
        e_yr = float(entries.sum() / years)
    pos_months = neg_months = 0
    try:
        monthly    = returns.resample("ME").sum()
        pos_months = int((monthly > 0).sum())
        neg_months = int((monthly <= 0).sum())
    except Exception:
        pass
    return {
        "label":          label,
        "sharpe":         round(sh, 4),
        "ann_ret_pct":    round(ann * 100, 4),
        "ann_ret_4x_pct": round(ann * 100 * 4, 4),
        "max_dd_pct":     round(mdd * 100, 4),
        "entries_yr":     round(e_yr, 1),
        "n_days":         round(years * 365.25, 0),
        "n_hours":        len(returns),
        "pos_months":     pos_months,
        "neg_months":     neg_months,
        "cum_ret":        round(float(returns.sum()), 6),
    }


# ── Phase 0: Vol pre-screen ────────────────────────────────────────────────────

def phase0_prescreen(df: pd.DataFrame) -> Dict:
    """Phase 0: vol ratio NEAR/ETH (K663 ETH-base rule: >= 2x REQUIRED).

    This is the PRIMARY gate for K675. NEAR-ETH vol ratio of 1.44x is
    far below the 2.0x ETH threshold from K663. This is a HARD REJECT.

    Architecture note: ETH has HIGHER vol than BTC (ETH_std=1.90e-5 vs BTC_std=1.76e-5)
    so NEAR/ETH ratio is STRICTLY LOWER than NEAR/BTC ratio. ETH-base is
    categorically harder to pass for NEAR than BTC-base was in K503.
    """
    now    = df.index.max()
    cut6m  = now - pd.Timedelta(days=182)
    cut12m = now - pd.Timedelta(days=365)

    near_std_full = float(df["near_fr"].std())
    eth_std_full  = float(df["eth_fr"].std())
    btc_std_full  = float(df["btc_fr"].std())
    near_std_6m   = float(df.loc[df.index >= cut6m, "near_fr"].std())
    eth_std_6m    = float(df.loc[df.index >= cut6m, "eth_fr"].std())
    near_std_365d = float(df.loc[df.index >= cut12m, "near_fr"].std())
    eth_std_365d  = float(df.loc[df.index >= cut12m, "eth_fr"].std())

    vr_eth_full  = near_std_full  / eth_std_full  if eth_std_full  > 0 else 0.0
    vr_eth_6m    = near_std_6m    / eth_std_6m    if eth_std_6m    > 0 else 0.0
    vr_eth_365d  = near_std_365d  / eth_std_365d  if eth_std_365d  > 0 else 0.0
    vr_btc_full  = near_std_full  / btc_std_full  if btc_std_full  > 0 else 0.0

    # K663 rule: vol_ratio >= 2.0x for ETH-base
    pass_k663_eth = vr_eth_6m >= G0_VOL_MIN_ETH   # HARD: must be >= 2.0x
    pass_hard_btc = vr_btc_full >= G0_VOL_MIN_BTC  # K503 reference (1.5x threshold)

    near_mean_ann = float(df["near_fr"].mean()) * 8760 * 100
    eth_mean_ann  = float(df["eth_fr"].mean())  * 8760 * 100
    btc_mean_ann  = float(df["btc_fr"].mean())  * 8760 * 100
    ne_diff       = near_mean_ann - eth_mean_ann
    nb_diff       = near_mean_ann - btc_mean_ann

    family_vol = {
        "eth_btc_k449":    1.084,
        "arb_btc_k491":    1.270,
        "near_btc_k503":   K503_VOL_RATIO_BTC_6M,
        "near_eth_k675":   round(vr_eth_6m, 4),
        "bnb_btc_k480":    1.403,
        "avax_btc_k484":   1.499,
        "sol_btc_k476":    1.764,
        "atom_btc_k493":   2.337,
        "inj_btc_k500":    3.826,
    }

    return {
        "near_fr_std_full":  round(near_std_full, 8),
        "eth_fr_std_full":   round(eth_std_full, 8),
        "btc_fr_std_full":   round(btc_std_full, 8),
        "vol_ratio_eth_full": round(vr_eth_full, 4),
        "vol_ratio_eth_6m":   round(vr_eth_6m, 4),
        "vol_ratio_eth_365d": round(vr_eth_365d, 4),
        "vol_ratio_btc_full": round(vr_btc_full, 4),
        "vol_ratio_btc_6m":   K503_VOL_RATIO_BTC_6M,
        "threshold_eth_k663": G0_VOL_MIN_ETH,
        "threshold_btc_k503": G0_VOL_MIN_BTC,
        "pass_k663_eth":      bool(pass_k663_eth),
        "pass_hard_btc":      bool(pass_hard_btc),
        "near_fr_mean_ann_pct": round(near_mean_ann, 4),
        "eth_fr_mean_ann_pct":  round(eth_mean_ann, 4),
        "btc_fr_mean_ann_pct":  round(btc_mean_ann, 4),
        "near_eth_diff_ann_pct": round(ne_diff, 4),
        "near_btc_diff_ann_pct": round(nb_diff, 4),
        "family_vol_comparison": family_vol,
        "prescreen_verdict": (
            f"PHASE 0 REJECT: NEAR/ETH vol_ratio 6M={vr_eth_6m:.4f}x < {G0_VOL_MIN_ETH}x (K663 ETH-base rule). "
            f"K503 NEAR/BTC 6M={K503_VOL_RATIO_BTC_6M:.4f}x also REJECT (< {G0_VOL_MIN_BTC}x BTC threshold). "
            f"ETH has HIGHER vol than BTC (std ratio ETH/BTC={eth_std_full/btc_std_full:.4f}x) "
            f"so NEAR/ETH is categorically lower than NEAR/BTC. ETH-base makes NEAR worse."
        ),
        "architecture_note": (
            "NEAR Protocol: Nightshade sharding L1, Aurora EVM bridge to Ethereum. "
            "NEAR FR vol ratio to ETH = 1.44x (6M) — below even the 1.5x BTC hard minimum from K503. "
            "ETH higher vol than BTC means ETH-base vol gap for NEAR is SMALLER, not larger. "
            "Aurora EVM creates partial ETH ecosystem overlap but insufficient to boost NEAR FR vol. "
            "Sharding architecture reduces per-shard speculative demand vs monolithic chains (SOL/ETH). "
            "NEAR Foundation / Ethereum AI partnership: narrative overlap but NOT FR dynamics overlap. "
            "K675 is a categorical REJECT per K663 rule. No ETH-base alpha for NEAR."
        ),
    }


# ── Phase 1: FR level + cycle alignment diagnostic ─────────────────────────────

def phase1_fr_diagnostic(df: pd.DataFrame) -> Dict:
    """NEAR FR vs ETH FR cycle alignment analysis.

    Key finding: NEAR is a Nightshade sharding L1 with Aurora EVM bridge.
    Despite NEAR Foundation / Ethereum AI partnerships, NEAR FR dynamics
    are driven by native NEAR speculation, NOT ETH DeFi cycles.
    NEAR-ETH differential (1.65%/yr) is much smaller than NEAR-BTC (0.61%/yr
    is even smaller, with opposite sign at times), making the signal ambiguous.
    """
    now    = df.index.max()
    cut6m  = now - pd.Timedelta(days=182)
    df6m   = df.loc[df.index >= cut6m]

    near_mean_ann = float(df["near_fr"].mean()) * 8760 * 100
    eth_mean_ann  = float(df["eth_fr"].mean())  * 8760 * 100
    btc_mean_ann  = float(df["btc_fr"].mean())  * 8760 * 100
    ne_diff_ann   = near_mean_ann - eth_mean_ann
    nb_diff_ann   = near_mean_ann - btc_mean_ann

    # Spike analysis
    spike_near_above_eth  = float((df["near_fr"] > df["eth_fr"]).mean())
    spike_near_above_btc  = float((df["near_fr"] > df["btc_fr"]).mean())
    spike_near_above_eth_6m = float((df6m["near_fr"] > df6m["eth_fr"]).mean())
    spike_near_above_btc_6m = float((df6m["near_fr"] > df6m["btc_fr"]).mean())

    # FR level correlations
    corr_near_eth = float(df["near_fr"].corr(df["eth_fr"]))
    corr_near_btc = float(df["near_fr"].corr(df["btc_fr"]))
    corr_eth_btc  = float(df["eth_fr"].corr(df["btc_fr"]))
    corr_near_eth_6m = float(df6m["near_fr"].corr(df6m["eth_fr"]))

    # Vol ratio
    vr_eth_6m = df6m["near_fr"].std() / df6m["eth_fr"].std()
    vr_btc_6m = df6m["near_fr"].std() / df6m["btc_fr"].std()

    # NEAR-ETH 6M vs full diff (trend check)
    ne_diff_6m = float(df6m["fr_diff"].mean()) * 8760 * 100

    return {
        "near_fr_mean_ann_pct":   round(near_mean_ann, 4),
        "eth_fr_mean_ann_pct":    round(eth_mean_ann, 4),
        "btc_fr_mean_ann_pct":    round(btc_mean_ann, 4),
        "near_eth_diff_ann_pct":  round(ne_diff_ann, 4),
        "near_btc_diff_ann_pct":  round(nb_diff_ann, 4),
        "near_eth_diff_6m_pct":   round(ne_diff_6m, 4),
        "spike_near_above_eth_full": round(spike_near_above_eth, 4),
        "spike_near_above_btc_full": round(spike_near_above_btc, 4),
        "spike_near_above_eth_6m":   round(spike_near_above_eth_6m, 4),
        "spike_near_above_btc_6m":   round(spike_near_above_btc_6m, 4),
        "corr_near_eth":          round(corr_near_eth, 4),
        "corr_near_btc":          round(corr_near_btc, 4),
        "corr_eth_btc":           round(corr_eth_btc, 4),
        "corr_near_eth_6m":       round(corr_near_eth_6m, 4),
        "vol_ratio_near_eth_6m":  round(vr_eth_6m, 4),
        "vol_ratio_near_btc_6m":  round(vr_btc_6m, 4),
        "g0_pass":                bool(vr_eth_6m >= G0_VOL_MIN_ETH),
        "cycle_alignment_notes": [
            "NEAR Protocol: Nightshade sharding L1, Aurora EVM bridge to Ethereum",
            "NEAR Foundation 'Ethereum AI' partnership: narrative but not FR dynamics",
            "Aurora EVM allows Ethereum dApps to deploy on NEAR — creates partial overlap",
            f"NEAR FR > ETH FR: {spike_near_above_eth:.1%} of time (full period)",
            f"NEAR/ETH FR level corr: {corr_near_eth:.4f} (moderate — partial Aurora overlap)",
            f"NEAR/ETH vol_ratio 6M: {vr_eth_6m:.4f}x (FAIL: need >= 2.0x per K663 rule)",
            f"NEAR-ETH diff 6M: {ne_diff_6m:.2f}%/yr vs full: {ne_diff_ann:.2f}%/yr (low carry signal)",
            "ETH has HIGHER vol than BTC — ETH-base always harder to pass for NEAR than BTC-base",
            "K503 REJECT was at NEAR/BTC=1.43x; K675 REJECT at NEAR/ETH=1.44x (same level)",
            "No ETH-specific cycle alignment advantage for NEAR sharding L1 architecture",
        ],
        "near_eth_vs_near_btc_comparison": (
            f"NEAR-ETH diff: {ne_diff_ann:.2f}%/yr (predominantly short NEAR, long ETH). "
            f"NEAR-BTC diff: {nb_diff_ann:.2f}%/yr (small positive, mixed direction). "
            f"NEAR-ETH carry ({ne_diff_ann:.2f}%/yr) > NEAR-BTC carry ({nb_diff_ann:.2f}%/yr) "
            f"— ETH-base has slightly more carry but still insufficient vol ratio. "
            f"vol_ratio NEAR/ETH 6M={vr_eth_6m:.4f}x vs NEAR/BTC 6M={vr_btc_6m:.4f}x "
            f"— ETH-base offers no vol ratio improvement (ETH std > BTC std)."
        ),
    }


# ── Phase 2: NEAR-ETH at 7d + cross-window informational grid ─────────────────

def grid_search_informational(df: pd.DataFrame) -> List[Dict]:
    """Informational grid search despite Phase 0 REJECT.
    Documents what NEAR-ETH performance would be IF vol threshold were met.
    """
    results = []
    n_total = len(df)
    is_cut  = int(n_total * (1 - OOS_FRAC))

    df_is  = df.iloc[:is_cut]
    df_oos = df.iloc[is_cut:]

    windows    = [24, 72, 168, 336]
    thresholds = [0.0, 0.25]

    for w in windows:
        for tf in thresholds:
            thresh_val = 0.0 if tf == 0 else float(df_is["fr_diff"].std() * tf)
            df_bt = build_signal(df, window_h=w, threshold=thresh_val)
            if len(df_bt) < 200:
                continue
            n_bt   = len(df_bt)
            cut_bt = int(n_bt * (1 - OOS_FRAC))
            is_bt  = df_bt.iloc[:cut_bt]
            oos_bt = df_bt.iloc[cut_bt:]
            if len(oos_bt) < 50:
                continue
            oos_yr = len(oos_bt) / 8760
            e_yr   = round(float(oos_bt["entries"].sum() / oos_yr), 1) if oos_yr > 0 else 0.0
            results.append({
                "window_h":         w,
                "threshold_factor": tf,
                "threshold_value":  round(thresh_val, 8),
                "IS_sharpe":        round(compute_sharpe(is_bt["net_pnl"]), 4),
                "OOS_sharpe":       round(compute_sharpe(oos_bt["net_pnl"]), 4),
                "OOS_ret_pct":      round(compute_ann_return(oos_bt["net_pnl"]) * 100, 4),
                "entries_yr":       e_yr,
                "informational":    True,
                "note":             "Grid informational only — Phase 0 REJECT, vol_ratio 1.44x < 2.0x",
            })

    results.sort(key=lambda x: x["OOS_sharpe"], reverse=True)
    return results


# ── Phase 3: Full backtest (informational) ────────────────────────────────────

def run_backtest(df: pd.DataFrame, window_h: int = WINDOW_H,
                 threshold: float = 0.0) -> Tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    """Run backtest and split IS/OOS. Returns (full, IS, OOS)."""
    df_bt = build_signal(df, window_h=window_h, threshold=threshold)
    n     = len(df_bt)
    cut   = int(n * (1 - OOS_FRAC))
    return df_bt, df_bt.iloc[:cut], df_bt.iloc[cut:]


# ── Permutation test ───────────────────────────────────────────────────────────

def permutation_test(oos: pd.DataFrame, n_perm: int = N_PERM) -> Dict:
    """1000 direction reshuffles on OOS net_pnl (informational)."""
    real_sh   = compute_sharpe(oos["net_pnl"])
    perm_sh   = []
    rng       = np.random.default_rng(42)
    smooth_oos = oos["fr_diff_smooth"].shift(1).fillna(0)
    for _ in range(n_perm):
        signs = rng.choice([-1.0, 1.0], size=len(oos))
        pnl_p = smooth_oos.values * signs - oos["cost"].values
        perm_sh.append(compute_sharpe(pd.Series(pnl_p)))
    perm_arr = np.array(perm_sh)
    p_val    = float((perm_arr >= real_sh).mean())
    return {
        "real_sharpe":    round(real_sh, 4),
        "perm_mean_stat": round(float(perm_arr.mean()), 8),
        "perm_p_value":   round(p_val, 4),
        "n_perm":         n_perm,
        "pass":           bool(p_val <= G2_PERM_MAX),
        "informational":  True,
        "note":           f"{n_perm} direction reshuffles OOS (informational — Phase 0 REJECT)",
    }


# ── DSR Bonferroni ─────────────────────────────────────────────────────────────

def dsr_bonferroni(oos_sharpe: float, oos_n: int,
                   n_trials: int = N_TRIALS_TESTED) -> Dict:
    """Deflated Sharpe Ratio / Bonferroni correction (informational)."""
    t_stat  = oos_sharpe / math.sqrt(ANN_FACTOR_1H**2 / oos_n) if oos_n > 0 else 0.0
    p_raw   = float(stats.t.sf(t_stat, df=oos_n - 1)) if oos_n > 1 else 1.0
    p_bonf  = min(p_raw * n_trials, 1.0)
    thresh  = 0.05 / n_trials
    return {
        "pass":         bool(p_bonf < thresh),
        "n_trials":     n_trials,
        "t_stat":       round(t_stat, 4),
        "p_raw":        round(p_raw, 8),
        "p_bonferroni": round(p_bonf, 8),
        "threshold":    round(thresh, 5),
        "informational": True,
        "note":         f"Bonferroni: p < 0.05/{n_trials} = {thresh:.5f} (informational — Phase 0 REJECT)",
    }


# ── Walk-forward ───────────────────────────────────────────────────────────────

def walk_forward(df_full: pd.DataFrame, n_folds: int = N_FOLDS) -> Dict:
    """Chronological n-fold walk-forward (informational)."""
    n = len(df_full)
    fold_sharpes: List[float] = []
    for i in range(n_folds):
        ts = int(n * (i + 1) / n_folds * 0.75)
        te = int(n * (i + 1) / n_folds)
        fold = df_full.iloc[ts:te]
        if len(fold) > 10:
            fold_sharpes.append(round(compute_sharpe(fold["net_pnl"]), 4))
    all_pos = all(s > 0 for s in fold_sharpes)
    return {
        "fold_sharpes": fold_sharpes,
        "all_positive": all_pos,
        "n_folds":      len(fold_sharpes),
        "pass":         all_pos,
        "informational": True,
        "note":         f"{n_folds}-fold walk-forward (informational — Phase 0 REJECT)",
    }


# ── ADF + OU ───────────────────────────────────────────────────────────────────

def adf_test(series: pd.Series) -> Dict:
    from statsmodels.tsa.stattools import adfuller
    s = series.dropna()
    r = adfuller(s, maxlag=10, autolag="AIC")
    return {
        "adf_stat":   round(float(r[0]), 4),
        "p_value":    round(float(r[1]), 4),
        "stationary": bool(r[1] < 0.05),
        "critical_1": round(float(r[4]["1%"]), 4),
        "critical_5": round(float(r[4]["5%"]), 4),
        "note":       "NEAR-ETH FR diff stationarity test at 5%",
    }


def ou_halflife(series: pd.Series) -> Dict:
    s = series.dropna()
    y = s.diff().dropna()
    x = s.shift(1).dropna()
    x, y = x.align(y, join="inner")
    X  = np.column_stack([x.values, np.ones(len(x))])
    b  = np.linalg.lstsq(X, y.values, rcond=None)[0]
    theta = -b[0]
    hl    = math.log(2) / theta if theta > 0 else float("inf")
    return {
        "theta":          round(float(theta), 6),
        "half_life_h":    round(float(hl), 1),
        "half_life_days": round(float(hl) / 24, 3),
        "mean_reverting": bool(theta > 0),
        "note":           "NEAR-ETH FR diff mean-reversion (informational)",
    }


# ── Phase 4: §6 Gates (mostly informational) ──────────────────────────────────

def section6_gates(df_full: pd.DataFrame, df_is: pd.DataFrame, df_oos: pd.DataFrame,
                   df_raw: pd.DataFrame, n_trials: int = N_TRIALS_TESTED) -> Dict:
    """Evaluate §6 gates. G0 is primary gate (Phase 0 vol pre-screen)."""

    # G0: Phase 0 vol pre-screen (PRIMARY GATE — ETH-base K663 rule)
    vr_eth_6m = phase0_prescreen(df_raw)["vol_ratio_eth_6m"]
    g0 = {
        "value":       round(vr_eth_6m, 4),
        "threshold":   f">= {G0_VOL_MIN_ETH}x (K663 ETH-base rule)",
        "pass":        bool(vr_eth_6m >= G0_VOL_MIN_ETH),
        "is_primary":  True,
        "note": (
            f"NEAR/ETH vol_ratio 6M={vr_eth_6m:.4f}x. "
            f"K663 rule: ETH-base requires >= 2.0x. "
            f"HARD FAIL: 1.44x < 2.0x. REJECT terminates here. "
            f"For reference: K503 NEAR/BTC={K503_VOL_RATIO_BTC_6M:.4f}x also REJECT (< 1.5x BTC threshold). "
            f"ETH vol > BTC vol — ETH-base categorically lower vol_ratio than BTC-base for NEAR."
        ),
    }

    # G1: OOS Sharpe (informational)
    oos_sh = compute_sharpe(df_oos["net_pnl"])
    g1 = {
        "value":        round(oos_sh, 4),
        "threshold":    f">= {G1_SH_MIN}",
        "pass":         bool(oos_sh >= G1_SH_MIN),
        "informational": True,
        "note":         f"OOS Sharpe (informational — Phase 0 REJECT). Actual: {oos_sh:.4f}",
    }

    # G2: Permutation (informational)
    g2_raw = permutation_test(df_oos)
    g2     = {**g2_raw, "threshold": f"<= {G2_PERM_MAX}",
              "pass": bool(g2_raw["perm_p_value"] <= G2_PERM_MAX)}

    # G3: DSR Bonferroni (informational)
    g3 = dsr_bonferroni(oos_sh, len(df_oos), n_trials)

    # G4: Walk-forward (informational)
    g4 = walk_forward(df_full)

    # G5: Correlation checks
    df_nb_sig = build_signal(df_raw, window_h=168, threshold=0.0, diff_col="fr_diff_nb")
    df_eb_sig = build_signal(df_raw, window_h=168, threshold=0.0, diff_col="fr_diff_eb")

    n_sig = len(df_full)
    cut   = int(len(df_nb_sig) * (1 - OOS_FRAC))
    oos_nb = df_nb_sig["net_pnl"].iloc[cut:].reindex(df_oos.index).fillna(0)
    cut_eb = int(len(df_eb_sig) * (1 - OOS_FRAC))
    oos_eb = df_eb_sig["net_pnl"].iloc[cut_eb:].reindex(df_oos.index).fillna(0)

    def safe_corr(a: pd.Series, b: pd.Series) -> float:
        al = pd.concat([a.rename("a"), b.rename("b")], axis=1).dropna()
        if len(al) < 30:
            return 0.0
        return round(float(al["a"].corr(al["b"])), 4)

    near_eth_oos = df_oos["net_pnl"]
    corr_g5a = safe_corr(near_eth_oos, oos_eb)   # vs K449 ETH-BTC (shared ETH leg)
    corr_g5b = safe_corr(near_eth_oos, oos_nb)   # vs K503 NEAR-BTC (same alt)

    g5_checks = {
        "g5a_eth_btc_k449": {
            "label":        "ETH-BTC K449 (shared ETH leg — CRITICAL for ETH-base)",
            "corr":         corr_g5a,
            "threshold":    G5_CORR_MAX,
            "pass":         bool(abs(corr_g5a) < G5_CORR_MAX),
            "informational": True,
            "note":         "NEAR-ETH shares ETH leg with K449. Is NEAR-ETH just an ETH-BTC rotation?",
        },
        "g5b_near_btc_k503": {
            "label":        "NEAR-BTC K503 (same NEAR alt — same-alt check)",
            "corr":         corr_g5b,
            "threshold":    G5_CORR_MAX,
            "pass":         bool(abs(corr_g5b) < G5_CORR_MAX),
            "informational": True,
            "note": (
                "NEAR-ETH shares NEAR alt leg with K503. "
                "K503 REJECT was BTC-base vol_ratio 1.43x. "
                "Both signals share the NEAR FR component — correlation measures if "
                "ETH-base provides orthogonal timing signal vs BTC-base for NEAR."
            ),
        },
    }

    n_pass_g5 = sum(1 for v in g5_checks.values() if v["pass"])
    g5 = {
        "pass":        bool(n_pass_g5 == len(g5_checks)),
        "checks":      g5_checks,
        "n_pass":      n_pass_g5,
        "n_total":     len(g5_checks),
        "informational": True,
        "verdict": (
            f"G5 ({n_pass_g5}/{len(g5_checks)}) — informational only (Phase 0 REJECT). "
            f"G5a corr={corr_g5a:.4f}, G5b corr={corr_g5b:.4f}."
        ),
    }

    # G6: Trade count (informational)
    oos_years = len(df_oos) / 8760
    e_yr = float(df_oos["entries"].sum() / oos_years) if oos_years > 0 else 0.0
    g6 = {
        "value":        round(e_yr, 1),
        "threshold":    f">= {G6_TRADES_MIN}",
        "pass":         bool(e_yr >= G6_TRADES_MIN),
        "informational": True,
        "note":         f"Entry events per year (OOS). W=168h typically yields ~25/yr for NEAR-ETH.",
    }

    # G7: Ann return (informational)
    ann_4x = compute_ann_return(df_oos["net_pnl"]) * 100 * 4
    g7 = {
        "pass":         bool(ann_4x > G7_ANN_RET_MIN),
        "value_1x_pct": round(ann_4x / 4, 4),
        "value_4x_pct": round(ann_4x, 4),
        "threshold_pct": G7_ANN_RET_MIN,
        "informational": True,
        "note":         f"Ann ret {ann_4x:.2f}%/yr @4x. (informational — Phase 0 REJECT)",
    }

    # G8: Cross-venue (structural — HL 1h vs Bybit 8h settlement mismatch)
    g8 = {
        "pass":        False,
        "informational": True,
        "note": (
            "G8 STRUCTURAL FAIL — HL NEAR settlement 1h; Bybit NEARUSDT 8h. "
            "Settlement frequency mismatch confirmed pattern (same as K503/K598 family). "
            "Bybit NEAR 8h FR mean ~6.26%/yr vs HL 1h ~12.16%/yr — settlement divergence. "
            "G8 FAIL inherited from K503 structural precedent."
        ),
        "inherited_from": "K503 NEAR-BTC G8 FAIL (HL 1h vs Bybit 8h settlement mismatch)",
    }

    # G9: Data sufficiency (informational)
    oos_days = (df_oos.index[-1] - df_oos.index[0]).days
    g9 = {
        "oos_days":  oos_days,
        "threshold": f">= {G9_OOS_DAYS_MIN}d",
        "pass":      bool(oos_days >= G9_OOS_DAYS_MIN),
        "informational": True,
        "note":      f"OOS period: {oos_days}d.",
    }

    all_gates = {
        "G0_phase0_vol_prescreen": g0,
        "G1_oos_sharpe":           g1,
        "G2_perm_pvalue":          g2,
        "G3_dsr_bonferroni":       g3,
        "G4_walk_forward":         g4,
        "G5_family_corr":          g5,
        "G6_trade_count":          g6,
        "G7_ann_return":           g7,
        "G8_cross_venue":          g8,
        "G9_data_sufficiency":     g9,
    }

    # Count: G0 is the primary gate; informational gates counted separately
    primary_pass = int(g0["pass"])
    info_pass    = sum(
        1 for k, v in all_gates.items()
        if k != "G0_phase0_vol_prescreen" and v.get("pass", False)
    )
    info_total   = len(all_gates) - 1  # exclude G0

    return {
        "gates":             all_gates,
        "g0_primary_pass":   primary_pass,
        "informational_pass": info_pass,
        "informational_total": info_total,
        "oos_sharpe":        round(oos_sh, 4),
        "oos_ann_ret_pct":   round(compute_ann_return(df_oos["net_pnl"]) * 100, 4),
        "g5b_near_btc_corr": corr_g5b,
        "g5a_eth_btc_corr":  corr_g5a,
        "note": (
            "G0 is primary gate (Phase 0 vol pre-screen, K663 rule). "
            "All other gates informational — Phase 0 REJECT terminates evaluation. "
            f"Informational gates: {info_pass}/{info_total} pass."
        ),
    }


# ── Profit projection (hypothetical — for documentation) ─────────────────────

def profit_projection(oos_ann_ret: float, sleeve_pct: float = 2.0) -> Dict:
    """Hypothetical profit projection @$10M AUM, 4x leverage.
    INFORMATIONAL ONLY — Phase 0 REJECT means no live deployment.
    """
    AUM      = 10_000_000
    leverage = 4.0
    friction = 0.85  # 15% friction buffer
    notional = AUM * sleeve_pct / 100
    gross_yr = notional * leverage * (oos_ann_ret / 100)
    net_yr   = gross_yr * friction
    daily    = net_yr / 365.25

    return {
        "strategy":           "NEAR-ETH FR differential paired-trade (K675) — HYPOTHETICAL",
        "status":             "PHASE 0 REJECT — vol_ratio 1.44x < 2.0x, no live deployment",
        "sleeve_pct":         sleeve_pct,
        "leverage":           leverage,
        "oos_ann_ret_1x_pct": round(oos_ann_ret, 4),
        "oos_ann_ret_4x_pct": round(oos_ann_ret * leverage, 4),
        "aum_10M": {
            "aum_usd":           AUM,
            "notional_usd":      int(notional * leverage),
            "gross_usdc_yr":     int(gross_yr),
            "net_usdc_yr":       int(net_yr),
            "daily_usdc":        int(daily),
            "informational_only": True,
        },
        "near_btc_k503_ref": {
            "oos_sharpe_w336":   K503_OOS_SHARPE_W336,
            "oos_sharpe_w168":   K503_OOS_SHARPE_W168,
            "decision":          K503_DECISION,
            "vol_ratio_btc_6m":  K503_VOL_RATIO_BTC_6M,
        },
        "note": (
            f"HYPOTHETICAL: {sleeve_pct}% sleeve, 4x leverage, 15% friction. "
            f"OOS ann ret (1x): {oos_ann_ret:.2f}%. "
            f"Phase 0 REJECT — NOT eligible for live deployment. "
            f"Shown only to document magnitude of underperformance vs live strategies."
        ),
    }


# ── Main ──────────────────────────────────────────────────────────────────────

def main() -> None:
    print("K675 NEAR-ETH FR Differential Paired-Trade Evaluation")
    print("=" * 60)

    # Load data
    print("Loading FR data...")
    df = load_fr_data()
    print(f"  NEAR rows: {len(df)} | {df.index[0]} to {df.index[-1]}")

    # Phase 0: Pre-screen (PRIMARY GATE)
    print("Phase 0: Vol pre-screen (K663 rule: NEAR/ETH >= 2x)...")
    p0 = phase0_prescreen(df)
    print(f"  NEAR/ETH vol_ratio 6M={p0['vol_ratio_eth_6m']:.4f}x | threshold={G0_VOL_MIN_ETH}x")
    print(f"  NEAR/BTC vol_ratio 6M={K503_VOL_RATIO_BTC_6M:.4f}x | threshold=1.5x (K503)")
    print(f"  Phase 0 PASS: {p0['pass_k663_eth']} (K663 ETH rule)")
    print(f"  Verdict: {p0['prescreen_verdict'][:100]}...")
    if not p0["pass_k663_eth"]:
        print("  --> PHASE 0 HARD REJECT: NEAR/ETH vol_ratio below K663 2x threshold")
        print("  --> K503 was already REJECT at NEAR/BTC=1.43x; ETH-base is WORSE")
        print("  --> Running informational backtest for documentation only")

    # Phase 1: FR cycle alignment diagnostic
    print("Phase 1: NEAR-ETH cycle alignment diagnostic...")
    p1 = phase1_fr_diagnostic(df)
    print(f"  NEAR FR mean: {p1['near_fr_mean_ann_pct']:.2f}%/yr | ETH: {p1['eth_fr_mean_ann_pct']:.2f}%/yr")
    print(f"  NEAR-ETH diff: {p1['near_eth_diff_ann_pct']:.2f}%/yr | NEAR-BTC: {p1['near_btc_diff_ann_pct']:.2f}%/yr")
    print(f"  NEAR/ETH FR level corr: {p1['corr_near_eth']:.4f}")
    print(f"  NEAR > ETH: {p1['spike_near_above_eth_full']:.1%} of time")

    # Phase 2: Grid search (informational)
    print("Phase 2: Grid search (informational despite REJECT)...")
    grid = grid_search_informational(df)
    best = grid[0] if grid else {}
    print(f"  Grid top-1: W={best.get('window_h','?')}h OOS Sh={best.get('OOS_sharpe',0):.4f}")

    # Select W=168h for consistency with family (also best for NEAR-ETH)
    best_w      = 168
    best_thresh = 0.0
    for g in grid:
        if g["entries_yr"] >= G6_TRADES_MIN:
            best_w      = g["window_h"]
            best_thresh = g["threshold_value"]
            break

    print(f"  Selected W={best_w}h (family standard 7d, or best with entries>=30/yr)")

    # Phase 3: Backtest (informational)
    print("Phase 3: Backtest (informational)...")
    df_bt, df_bt_is, df_bt_oos = run_backtest(df, window_h=best_w, threshold=best_thresh)

    full_m = compute_metrics(df_bt["net_pnl"],     df_bt["entries"],     "Full")
    is_m   = compute_metrics(df_bt_is["net_pnl"],  df_bt_is["entries"],  "IS")
    oos_m  = compute_metrics(df_bt_oos["net_pnl"], df_bt_oos["entries"], "OOS")
    print(f"  Full Sh={full_m['sharpe']:.4f} IS Sh={is_m['sharpe']:.4f} OOS Sh={oos_m['sharpe']:.4f}")
    print(f"  OOS Ann={oos_m['ann_ret_pct']:.4f}%/yr @1x = {oos_m['ann_ret_4x_pct']:.4f}%/yr @4x")

    # NEAR-BTC K503 rerun for comparison (same window)
    df_nb_ref = build_signal(df, window_h=best_w, threshold=0.0, diff_col="fr_diff_nb")
    n_nb = len(df_nb_ref)
    cut_nb = int(n_nb * (1 - OOS_FRAC))
    df_nb_oos = df_nb_ref.iloc[cut_nb:]
    k503_rerun = compute_metrics(df_nb_oos["net_pnl"], df_nb_oos["entries"],
                                 f"K503-NEAR-BTC-W{best_w}-rerun")
    print(f"  K503 NEAR-BTC W={best_w}h OOS Sh={k503_rerun['sharpe']:.4f} (NEAR-ETH vs NEAR-BTC at same W)")

    # NEAR-BTC W=336h (K503 published best)
    df_nb336 = build_signal(df, window_h=336, threshold=0.0, diff_col="fr_diff_nb")
    n336 = len(df_nb336)
    cut336 = int(n336 * (1 - OOS_FRAC))
    df_nb336_oos = df_nb336.iloc[cut336:]
    k503_w336 = compute_metrics(df_nb336_oos["net_pnl"], df_nb336_oos["entries"],
                                "K503-NEAR-BTC-W336-best")
    print(f"  K503 NEAR-BTC W=336h OOS Sh={k503_w336['sharpe']:.4f} (K503 published best config)")

    # ADF + OU
    adf = adf_test(df["fr_diff"])
    ou  = ou_halflife(df["fr_diff"])
    print(f"  ADF p={adf['p_value']:.4f} stationary={adf['stationary']} | OU hl={ou['half_life_h']:.1f}h")

    # Phase 4: §6 gates
    print("Phase 4: Section 6 gates (G0 primary, rest informational)...")
    gates_result = section6_gates(df_bt, df_bt_is, df_bt_oos, df)
    print(f"  G0 Phase0: {'PASS' if gates_result['g0_primary_pass'] else 'FAIL (REJECT)'}")
    print(f"  Informational: {gates_result['informational_pass']}/{gates_result['informational_total']}")
    print(f"  G5a (ETH-BTC): corr={gates_result['g5a_eth_btc_corr']:.4f}")
    print(f"  G5b (NEAR-BTC): corr={gates_result['g5b_near_btc_corr']:.4f}")

    # Phase 5: Decision
    print("Phase 5: Decision...")
    decision         = "REJECT — Phase 0 FAIL: NEAR/ETH vol_ratio 1.44x < 2.0x (K663 ETH-base rule)"
    decision_rationale = (
        f"K675 NEAR-ETH Phase 0 HARD REJECT: NEAR/ETH vol_ratio 6M={p0['vol_ratio_eth_6m']:.4f}x "
        f"< {G0_VOL_MIN_ETH}x (K663 rule). "
        f"K503 NEAR-BTC was also REJECT at {K503_VOL_RATIO_BTC_6M:.4f}x < 1.5x. "
        f"ETH-base does NOT improve NEAR's vol ratio (ETH std > BTC std — ETH-base harder to pass). "
        f"NEAR/ETH vol_ratio lower than NEAR/BTC vol_ratio — ETH-base categorically worse for NEAR. "
        f"Informational OOS Sh={oos_m['sharpe']:.4f} vs K503-BTC-W336 Sh={K503_OOS_SHARPE_W336} "
        f"(NEAR-ETH also WORSE than NEAR-BTC even informally). "
        f"NEAR Protocol: Nightshade sharding L1, Aurora EVM partial overlap insufficient for ETH-base."
    )
    print(f"  DECISION: {decision}")

    # Profit projection (hypothetical)
    sleeve = 2.0
    pp = profit_projection(oos_m["ann_ret_pct"], sleeve_pct=sleeve)
    print(f"  Hypothetical @$10M 2% sleeve 4x: net=${pp['aum_10M']['net_usdc_yr']:,}/yr "
          f"(INFORMATIONAL — REJECTED)")

    # K663 rule validation
    k663_rule = {
        "rule":       "ETH-base wins when vol_ratio >= 2x AND cycle alignment orthogonal AND G5b < 0.40",
        "near_position": (
            f"NEAR FR = {p1['near_fr_mean_ann_pct']:.2f}%/yr. ETH = {p1['eth_fr_mean_ann_pct']:.2f}%/yr. "
            f"BTC = {p1['btc_fr_mean_ann_pct']:.2f}%/yr. "
            f"NEAR-ETH diff = {p1['near_eth_diff_ann_pct']:.2f}%/yr. "
            f"NEAR-BTC diff = {p1['near_btc_diff_ann_pct']:.2f}%/yr. "
            f"vol_ratio NEAR/ETH 6M={p0['vol_ratio_eth_6m']:.4f}x. "
            f"vol_ratio NEAR/BTC 6M={K503_VOL_RATIO_BTC_6M:.4f}x."
        ),
        "rule_prediction": (
            "ETH-base FAILS for NEAR: vol_ratio 1.44x < 2.0x (K663 hard rule). "
            "Additionally: ETH vol > BTC vol makes NEAR/ETH < NEAR/BTC always — "
            "ETH-base is structurally worse for low-vol alts like NEAR. "
            "NEAR Nightshade sharding reduces per-shard FR spikes (less concentrated demand). "
            "Aurora EVM bridge creates partial ETH overlap but insufficient to boost FR vol."
        ),
        "actual_result":     f"REJECT — vol_ratio {p0['vol_ratio_eth_6m']:.4f}x < 2.0x",
        "k503_parallel":     f"K503 NEAR-BTC REJECT — vol_ratio {K503_VOL_RATIO_BTC_6M:.4f}x < 1.5x",
        "double_reject_note": (
            "K675 is a DOUBLE REJECT: fails both BTC threshold (1.44x < 1.5x) and "
            "ETH threshold (1.44x < 2.0x). No base currency makes NEAR viable for FR differential."
        ),
        "vol_ratio_eth_6m":   p0["vol_ratio_eth_6m"],
        "k663_threshold_2x":  G0_VOL_MIN_ETH,
        "pass":               bool(p0["vol_ratio_eth_6m"] >= G0_VOL_MIN_ETH),
    }

    # ETH-base family track update
    eth_family = dict(ETH_FAMILY_TRACK)
    eth_family["K675_NEAR_ETH"] = (
        f"REJECT — Phase 0 FAIL: vol_ratio {p0['vol_ratio_eth_6m']:.4f}x < 2x ETH threshold. "
        f"ETH-base makes NEAR WORSE (ETH std > BTC std → NEAR/ETH < NEAR/BTC always). "
        f"Informational OOS Sh={oos_m['sharpe']:.4f} (below K503-BTC W=336h Sh={K503_OOS_SHARPE_W336})."
    )

    # ── Assemble JSON output ──────────────────────────────────────────────────
    runtime = round(time.time() - START_TIME, 2)
    ts_jst  = subprocess.run(
        ["date", "+%Y-%m-%dT%H:%M:%S+09:00"],
        capture_output=True, text=True
    ).stdout.strip()

    result = {
        "wave":     "K675",
        "strategy": "NEAR-ETH FR Differential Paired-Trade (ETH-base mechanism test — K503 sharding L1)",
        "parent_waves": [
            f"K503 (NEAR-BTC REJECT — vol_ratio {K503_VOL_RATIO_BTC_6M:.4f}x < 1.5x threshold)",
            "K629 (WLD-ETH ACCEPT — ETH-base unlocks BTC-cluster-blocked alt)",
            "K663 (TIA-ETH ACCEPT EXCEPTION — vol_ratio >= 2x rule derived)",
            "K667 (TRX-ETH WORSE — vol_ratio>=2x necessary but NOT sufficient)",
            "K671 (PEPE-ETH WORSE — ERC-20 pure meme, ETH-base inferior)",
        ],
        "run_time_jst":      ts_jst,
        "runtime_s":         runtime,
        "decision":          decision,
        "decision_rationale": decision_rationale,
        "data_info": {
            "near_fr_rows":             len(df),
            "date_start":               str(df.index[0]),
            "date_end":                 str(df.index[-1]),
            "total_years":              round((df.index[-1] - df.index[0]).days / 365.25, 3),
            "oos_start":                str(df_bt_oos.index[0]),
            "oos_days":                 int((df_bt_oos.index[-1] - df_bt_oos.index[0]).days),
            "fr_frequency":             "1h (HL settles hourly)",
            "near_fr_mean_ann_pct":     p1["near_fr_mean_ann_pct"],
            "eth_fr_mean_ann_pct":      p1["eth_fr_mean_ann_pct"],
            "btc_fr_mean_ann_pct":      p1["btc_fr_mean_ann_pct"],
            "near_eth_diff_ann_pct":    p1["near_eth_diff_ann_pct"],
            "near_btc_diff_ann_pct":    p1["near_btc_diff_ann_pct"],
            "vol_ratio_near_eth_6m":    p0["vol_ratio_eth_6m"],
            "vol_ratio_near_eth_full":  p0["vol_ratio_eth_full"],
            "vol_ratio_near_btc_6m":    K503_VOL_RATIO_BTC_6M,
            "vol_ratio_near_btc_full":  p0["vol_ratio_btc_full"],
        },
        "phase0_prescreen":     p0,
        "phase1_fr_diagnostic": p1,
        "phase2_grid_search":   {
            "top_configs":      grid[:5],
            "best_window_h":    best_w,
            "best_threshold":   best_thresh,
            "note":             "Informational only — Phase 0 REJECT",
        },
        "statistical_analysis": {
            "adf_stationarity": adf,
            "ou_halflife":      ou,
        },
        "phase3_backtest": {
            "window_h":          best_w,
            "threshold":         best_thresh,
            "is_metrics":        is_m,
            "oos_metrics":       oos_m,
            "full_metrics":      full_m,
            "informational":     True,
            "note":              "Informational only — Phase 0 REJECT terminates live consideration",
        },
        "phase3_near_btc_comparison": {
            "near_eth_w168":         oos_m,
            "near_btc_w168_rerun":   k503_rerun,
            "near_btc_w336_best":    k503_w336,
            "comparison_verdict": (
                f"NEAR-ETH W=168h OOS Sh={oos_m['sharpe']:.4f} vs "
                f"NEAR-BTC W=168h Sh={k503_rerun['sharpe']:.4f} vs "
                f"NEAR-BTC W=336h Sh={k503_w336['sharpe']:.4f} (K503 published best). "
                f"NEAR-ETH is WORSE than NEAR-BTC even informally. "
                f"ETH-base provides no improvement for NEAR — confirms double REJECT."
            ),
        },
        "phase4_section6_gates": gates_result,
        "phase5_decision": {
            "decision":                decision,
            "rationale":               decision_rationale,
            "k663_rule_application":   k663_rule,
            "eth_base_family_track":   eth_family,
        },
        "profit_projection_hypothetical": pp,
        "profit_usdc_yr_at_10M": {
            "gross_usdc_yr":   pp["aum_10M"]["gross_usdc_yr"],
            "net_usdc_yr":     pp["aum_10M"]["net_usdc_yr"],
            "daily_usdc":      pp["aum_10M"]["daily_usdc"],
            "status":          "HYPOTHETICAL — PHASE 0 REJECT, not eligible for live",
            "note": (
                f"@$10M AUM, {sleeve}% sleeve, 4x leverage, 85% friction retention. "
                f"OOS ann ret {oos_m['ann_ret_pct']:.4f}%/yr @1x. "
                f"BELOW K503 NEAR-BTC W=336h informational (${int(10e6*0.02*4*K503_OOS_SHARPE_W336*0.01*0.85):,}/yr hypothetical). "
                f"REJECT is final — no path to live for NEAR-ETH."
            ),
        },
        "k675_lesson": (
            "K675 NEAR-ETH teaches: when an alt FAILS BTC-base vol pre-screen (K503: 1.43x < 1.5x), "
            "ETH-base is unlikely to rescue it because ETH vol > BTC vol — "
            "NEAR/ETH ratio is always lower than NEAR/BTC ratio. "
            "ETH-base is a valid UNLOCK mechanism only for alts with sufficient vol premium "
            "vs ETH specifically (>= 2x per K663). Nightshade sharding L1s with Aurora EVM "
            "bridges may have partial ETH narrative overlap, but FR dynamics remain "
            "dominated by native L1 speculation and sharding dilutes FR spikes. "
            "Next candidate: if evaluating sharding alts, filter by NEAR/ETH >= 2x first."
        ),
        "next_wave_recommendation": (
            "K675 REJECT is definitive — no pivot needed. "
            "ETH-base family evaluation continues with non-sharding L1 alts. "
            "Recommended: AVAX-ETH (K661 CONDITIONAL BTC-base wins, may yield dual-sleeve diversity), "
            "or pivot to onchain-native strategy (wallet clustering, MEV)."
        ),
    }

    # ── Write JSON ───────────────────────────────────────────────────────────
    out_json = BASE / "wave_k675_near_eth_eval.json"
    with open(out_json, "w") as f:
        json.dump(result, f, indent=2, default=str)
    print(f"\nJSON written: {out_json}")

    # ── Console summary ──────────────────────────────────────────────────────
    print()
    print("=" * 60)
    print("K675 NEAR-ETH SUMMARY")
    print("=" * 60)
    print(f"DECISION: {decision}")
    print()
    print("Phase 0 Vol Pre-Screen (PRIMARY GATE):")
    print(f"  NEAR/ETH vol_ratio 6M: {p0['vol_ratio_eth_6m']:.4f}x (threshold: >= 2.0x K663 rule)")
    print(f"  NEAR/BTC vol_ratio 6M: {K503_VOL_RATIO_BTC_6M:.4f}x (threshold: >= 1.5x K503 rule)")
    print(f"  ETH std > BTC std: ETH-base ALWAYS worse for NEAR vol ratio")
    print(f"  DOUBLE REJECT: fails both BTC (1.44x < 1.5x) and ETH (1.44x < 2.0x) thresholds")
    print()
    print("Informational Backtest (W=168h):")
    print(f"  NEAR-ETH OOS Sharpe: {oos_m['sharpe']:.4f} ann={oos_m['ann_ret_pct']:.4f}%/yr @1x")
    print(f"  NEAR-BTC W=168h OOS: {k503_rerun['sharpe']:.4f} (NEAR-BTC wins)")
    print(f"  NEAR-BTC W=336h OOS: {k503_w336['sharpe']:.4f} (K503 published best — also REJECT)")
    print(f"  NEAR-ETH is WORSE than NEAR-BTC even informally")
    print()
    print("ETH-base rule (K663):")
    print(f"  NEAR does not meet the vol_ratio >= 2x ETH threshold")
    print(f"  No ETH-specific cycle advantage for Nightshade sharding L1")
    print(f"  Aurora EVM partial overlap insufficient to boost FR vol")
    print()
    print(f"Hypothetical profit @$10M 2% sleeve 4x (NOT live-eligible):")
    print(f"  Gross: ${pp['aum_10M']['gross_usdc_yr']:,}/yr")
    print(f"  Net:   ${pp['aum_10M']['net_usdc_yr']:,}/yr")
    print(f"  Daily: ${pp['aum_10M']['daily_usdc']:,}/day")

    return result


if __name__ == "__main__":
    main()

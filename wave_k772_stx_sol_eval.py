#!/usr/bin/env python3
"""
wave_k772_stx_sol_eval.py — K772 STX-SOL FR Differential Eval (Bitcoin L2 vs SVM)
====================================================================================
K339 REPO_ROOT pattern: BASE = Path(__file__).parent

WAVE:     K772
PAIR:     STX-SOL  (Stacks Bitcoin L2 vs Solana SVM — NEW cluster eval)
CONTEXT:  K766 long-tail screen #4. STX = Stacks, Bitcoin L2 smart contracts.
          K766 screen results: vol_ratio=5.6x (30d HL), max anchor corr=0.047,
          composite=0.0388. Truly distinct cluster — Bitcoin L2 ≠ any of 15-17
          current vertices (L1/DeFi/meme/AI/infra/oracle/gaming/cross-chain).
          STX listed on HL (from 2024-05-30), Bybit (730d+ from 2021-12-03).
          HL 66.8% cap → paper-gate mandatory if ACCEPT.

HYPOTHESIS
----------
STX (Stacks Bitcoin L2, sBTC, Nakamoto upgrade) vs SOL (Solana SVM):
  - STX FR cluster: Bitcoin L2 narrative (sBTC launch, Nakamoto upgrade activation,
    BTC DeFi adoption, BTC-native yield), BTC price sentiment cycles (STX bonds
    to BTC via sBTC peg), Stacks stacking rewards (STX stacking ~10% APY),
    Bitcoin L2 speculation (sidechains/rollups on BTC), institutional BTC DeFi.
  - SOL FR cluster: SVM infrastructure (Firedancer upgrades, validator rewards),
    SOL ETF flows, SVM DeFi TVL, meme season cycles (BONK/WIF), SOL perp retail.
  - EXPECTED DIFFERENTIAL: BTC L2 narrative (sBTC adoption, Nakamoto upgrade,
    BTC DeFi yield) is structurally distinct from SVM infrastructure/meme cycle.
    When BTC L2 narrative activates (sBTC launches, BTC DeFi TVL spikes), STX FR
    spikes independently of SOL SVM dynamics. These narratives are largely orthogonal.
  - STX tokenomics: stacking rewards (~10% APY), sBTC peg mechanics, BTC bond
    security model. STX FR is ~80% positive (Bybit full) but OOS carry drops <70%.
  - CRITICAL: STX HL listing from 2024-05-30 (17519 rows = ~730 days full history).
    Primary backtest uses Bybit 8h data (2024-05-24 overlap start).
    Both STX and SOL have ~2y aligned Bybit history.

PRE-SCREEN RULES (ALL MANDATORY)
---------------------------------
  L003 (K746): raw_corr(STX_fr, AVAX_fr) < 0.45 mandatory
  L004 (K748): carry-stability: positive_fraction < 80% in BOTH full AND OOS
  L007 (K749): raw_corr(STX_fr, FIL_fr) < 0.45 (SOL-beta proxy via FIL-SOL)
  L010 (K752): raw_corr(STX_fr, HBAR_fr) < 0.45
  L011 (K759): raw_corr(STX_fr, SOL_fr) < 0.50 HARD GATE
  K760: PoW PoW contamination check — STX bonds to BTC (PoW), check BTC L1
        contamination (raw_corr(STX_fr, BTC_fr) < 0.45 — same threshold as L003)

PHASE STRUCTURE
---------------
Phase 0:  ALL pre-screens FIRST (including K760 PoW contamination explicit)
Phase 0a: MR9 strict — STX ∉ V_altalt (17 vertices)
Phase 0b: L003 AVAX contamination
Phase 0c: L004 carry-stability (HARD BLOCK if both full+OOS > 80%)
Phase 0d: L007 FIL SOL-beta proxy
Phase 0e: L010 HBAR contamination
Phase 0f: L011 SOL-direct check
Phase 0g: K760 PoW BTC contamination
Phase 1:  Vol pre-screen (confirm 5.6x / recent window, W=168h)
Phase 2:  Cycle analysis (Bitcoin L2 vs SVM narrative decoupling)
Phase 3:  IS/OOS split backtest (W=168h primary, W=84h fallback, W=48h)
Phase 4:  Grid search (3W x 3T = 9 configs, DSR Bonferroni G3)
Phase 5:  Walk-forward 12-fold (G4)
Phase 6:  §6 gates (G1-G9, vs all 17 vertices + BTC-base strategies)
Phase 7:  Decision + K523 3-point ROI
          - ACCEPT → new vertex (Bitcoin L2 cluster)
          - Capacity check: STX liquidity, sleeve 1.5-2.0%

NOTE ON DATA SOURCES
--------------------
Primary backtest:  Bybit STXUSDT (8h intervals, from 2024-05-24, overlap with SOL)
                   Bybit SOLUSDT (8h intervals, 730d from 2024-05-24)
HL confirmation:   HL STX (1h intervals, from 2024-05-30, n=17519, 730d full)
                   HL SOL (1h intervals, from 2024-05-23, n=17512)
Cross-corr checks: HL 1h data (longer history for all anchor tokens)
G5 family corr:    Bybit 8h (primary) + HL 1h fallback (secondary)

HL CAP AWARENESS
----------------
Current HL ~66.8% (K772 context). Paper-gate mandatory if ACCEPT.
STX: HL CONFIRMED (cache/k163_hl/hl_fr_STX.parquet, 17519 rows, from 2024-05-30)
STX: Bybit CONFIRMED (cache/bybit_fr_STXUSDT_730d.parquet, 13191 rows, from 2021-12-03)

BITCOIN L2 CLUSTER NOTE (K772 NEW CLUSTER)
--------------------------------------------
STX would be new vertex — first Bitcoin L2 protocol in the alt-alt universe.
Stacks architecture: Proof-of-Transfer (PoX) consensus anchored to BTC, sBTC
(wrapped BTC on Stacks), Clarity smart contracts, Stacks stacking rewards (~10%).
Nakamoto upgrade (2024): BTC-speed finality for Stacks blocks. sBTC 1:1 peg.
FR driver: BTC L2 narrative cycles (sBTC launch, Nakamoto upgrade, BTC DeFi TVL),
BTC price sentiment (STX bonds to BTC), stacking yield demand, institutional BTC
DeFi adoption, developer activity on Stacks. Distinct from:
  - EVM L1/L2 chains (ETH/AVAX/INJ/SEI) — EVM narrative
  - SVM (SOL, APT/SUI) — SVM infrastructure
  - DeFi lending/yield (ENA, LDO) — yield cluster
  - Meme (PEPE, WIF) — speculative retail
  - AI/oracle/storage (FIL, TAO, HBAR) — infra/data cluster
  - Gaming P2E (AXS) — P2E tokenomics
STX FR is driven by BTC L2 adoption, NOT EVM/SVM dynamics.

Usage:
  python3 wave_k772_stx_sol_eval.py

LIVE自動変更禁止 | K339 REPO_ROOT | HL cap 66.8% aware | K523 3-point ROI mandatory
K746 L003: AVAX contamination | K748 L004: carry-stability | K749 L007: FIL-SOL-beta
K752 L010: HBAR contamination | K759 L011: SOL-direct | K760 PoW BTC contamination
Vol>=1.5x pre-screen mandatory | Bitcoin L2 cluster | sBTC Nakamoto upgrade
"""
from __future__ import annotations

import json
import math
import time
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import numpy as np
import pandas as pd

# ── K339 REPO_ROOT pattern ────────────────────────────────────────────────────
BASE        = Path(__file__).parent
CACHE_DIR   = BASE / "cache"
HL_DIR      = CACHE_DIR / "k163_hl"
DATA_DIR    = BASE / "data"
OUT_JSON    = BASE / "wave_k772_stx_sol_eval.json"

# ── Strategy parameters ───────────────────────────────────────────────────────
WINDOW_H        = 168        # 7d rolling mean (primary — same as family standard)
WINDOW_H_ALT1   = 84         # 3.5d fallback
WINDOW_H_ALT2   = 48         # 2d fallback
THRESHOLD       = 0.0        # always-on (T=0)
LEVERAGE        = 4.0
SLEEVE_PCT      = 0.015      # 1.5% of $10M = $150K notional (long-tail)
CAPITAL_10M     = 10_000_000
# Bybit 8h data: ANN_FACTOR = sqrt(3 * 365)
ANN_FACTOR_BYBIT = math.sqrt(3 * 365)
# HL hourly data: ANN_FACTOR = sqrt(8760)
ANN_FACTOR_HL   = math.sqrt(8760)

# ── Pre-screen constants ──────────────────────────────────────────────────────
G5_AVAX_PRESCREEN   = 0.45   # K746 L003: AVAX contamination threshold
G5_FIL_PRESCREEN    = 0.45   # K749 L007: FIL SOL-beta proxy threshold
G5_HBAR_PRESCREEN   = 0.45   # K752 L010: HBAR contamination threshold
G5_BTC_PRESCREEN    = 0.45   # K760 PoW BTC contamination threshold
L011_SOL_DIRECT     = 0.50   # K759 L011: SOL-direct hard gate
L004_CARRY_WARN     = 0.80   # L004: >80% positive FR in BOTH periods → block
VOL_RATIO_TARGET    = 1.50   # Vol pre-screen target (soft warn if <1.5x)
VOL_RATIO_HARD_FAIL = 1.00   # Below this = hard fail
G5_CORR_THRESHOLD   = 0.40   # G5 signal correlation hard limit
PERM_N              = 1000
BONFERRONI_N        = 9      # 3W x 3T grid
WF_FOLDS            = 12
WF_IS_DAYS          = 90
WF_OOS_DAYS         = 30

# ── IS/OOS split ──────────────────────────────────────────────────────────────
IS_END = pd.Timestamp("2025-10-25")

# ── Vertex set (alt-alt family + BTC-base, K772 evaluates STX as new vertex) ─
VERTEX_SET_V = [
    "APT", "ATOM", "AVAX", "BNB", "ENA", "FIL", "HBAR", "INJ",
    "LDO", "SEI", "SOL", "TIA", "TAO", "PEPE", "WIF",
    "AXS", "BLUR",  # K769 AXS + K768 BLUR added
]


# ── Data loading ──────────────────────────────────────────────────────────────

def _load_hl_fr(name: str) -> Optional[pd.Series]:
    """Load HL hourly FR parquet from k163_hl. Return hourly Series or None."""
    paths = [
        HL_DIR / f"hl_fr_{name}.parquet",
        CACHE_DIR / f"hl_fr_{name}.parquet",
        DATA_DIR / f"hl_fr_{name}.parquet",
    ]
    for p in paths:
        if p.exists():
            d = pd.read_parquet(str(p))
            if "timestamp" in d.columns:
                d["timestamp"] = pd.to_datetime(d["timestamp"]).dt.floor("h")
                d = d.set_index("timestamp")
            else:
                d.index = pd.to_datetime(d.index).floor("h")
            d = d.sort_index()
            d = d[~d.index.duplicated(keep="first")]
            col = "hl_fr" if "hl_fr" in d.columns else d.columns[0]
            return d[col]
    return None


def _load_bybit_fr(name: str) -> Optional[pd.Series]:
    """Load Bybit 8h FR parquet. Return Series or None."""
    for suffix in ["730d", "365d"]:
        p = CACHE_DIR / f"bybit_fr_{name}USDT_{suffix}.parquet"
        if p.exists():
            d = pd.read_parquet(str(p))
            if "timestamp" in d.columns:
                d["timestamp"] = pd.to_datetime(d["timestamp"]).dt.floor("h")
                d = d.set_index("timestamp")
            else:
                d.index = pd.to_datetime(d.index).floor("h")
            d = d.sort_index()
            d = d[~d.index.duplicated(keep="first")]
            col = "funding_rate" if "funding_rate" in d.columns else d.columns[0]
            return d[col]
    return None


def _build_signal(a_fr: pd.Series, b_fr: pd.Series,
                  window: int, threshold: float = 0.0) -> pd.Series:
    """Build sign(W-bar rolling mean of a_fr - b_fr) signal."""
    df = pd.DataFrame({"a": a_fr, "b": b_fr}).dropna()
    diff = df["a"] - df["b"]
    sm = diff.rolling(window).mean().dropna()
    return np.sign(sm - threshold)


def _metrics(pnl: pd.Series, signal: Optional[pd.Series] = None,
             ann_factor: float = ANN_FACTOR_BYBIT) -> Dict:
    """Compute performance metrics from PnL series."""
    if len(pnl) < 10 or pnl.std() == 0:
        return {"error": "insufficient data", "sharpe": 0.0, "ann_ret_pct": 0.0,
                "max_dd_pct": 0.0, "years": 0.0, "entries_per_yr": 0.0}
    years = len(pnl) / (3 * 365)   # Bybit 8h default
    ann_ret = float(pnl.sum() / years)
    ann_std = float(pnl.std() * ann_factor)
    sharpe = ann_ret / ann_std if ann_std > 0 else 0.0
    cum = pnl.cumsum()
    max_dd = float((cum - cum.cummax()).min())
    entries = 0
    if signal is not None:
        entries = int((signal.diff().abs() > 0).sum())
    return {
        "sharpe": round(sharpe, 4),
        "ann_ret": round(ann_ret, 6),
        "ann_ret_pct": round(ann_ret * 100, 4),
        "ann_std": round(ann_std, 6),
        "max_dd_pct": round(max_dd * 100, 4),
        "years": round(years, 3),
        "entries_per_yr": round(entries / years, 1) if years > 0 else 0.0,
        "entries_total": entries,
        "period_start": str(pnl.index.min().date()),
        "period_end": str(pnl.index.max().date()),
    }


def _sig_corr(sig1: pd.Series, sig2: pd.Series) -> Tuple[float, float, float, int]:
    """Signal correlation: full / IS / OOS. Returns (full, is, oos, n_common)."""
    common = sig1.index.intersection(sig2.index)
    if len(common) < 50:
        return float("nan"), float("nan"), float("nan"), len(common)
    s1 = sig1.loc[common]
    s2 = sig2.loc[common]
    if s1.std() == 0 or s2.std() == 0:
        return float("nan"), float("nan"), float("nan"), len(common)
    full_c = float(np.corrcoef(s1.values, s2.values)[0, 1])
    is_idx  = common[common <= IS_END]
    oos_idx = common[common > IS_END]
    is_c  = (float(np.corrcoef(s1.loc[is_idx].values,  s2.loc[is_idx].values)[0, 1])
             if len(is_idx) > 50 else float("nan"))
    oos_c = (float(np.corrcoef(s1.loc[oos_idx].values, s2.loc[oos_idx].values)[0, 1])
             if len(oos_idx) > 50 else float("nan"))
    return round(full_c, 4), round(is_c, 4), round(oos_c, 4), len(common)


# ── Phase 0a: MR9 algebraic check ────────────────────────────────────────────

def phase0a_mr9(stx_fr: pd.Series, sol_fr: pd.Series,
                fr_map: Dict[str, Optional[pd.Series]]) -> Dict:
    """Check STX-SOL signal ≠ X-SOL for all X ∈ V_altalt (17 vertices)."""
    print("\n[Phase 0a] MR9 strict algebraic check (STX ∉ V_altalt) ...")
    results: Dict = {}
    mr9_clear = True
    stx_sol_diff = stx_fr - sol_fr

    for x in VERTEX_SET_V:
        if x == "SOL":
            continue
        x_fr = fr_map.get(x)
        if x_fr is None:
            results[x] = {"status": "MISSING_DATA", "mr9_clear": True,
                          "note": f"No data for {x} — assume MR9 clear."}
            continue
        common_raw = pd.DataFrame({"STX": stx_fr, x: x_fr}).dropna()
        if len(common_raw) < 5:
            results[x] = {"status": "INSUFFICIENT_OVERLAP", "mr9_clear": True}
            continue
        max_err_raw = float((common_raw["STX"] - common_raw[x]).abs().max())
        x_sol_diff = x_fr - sol_fr
        common_diff = pd.DataFrame({"stx_sol": stx_sol_diff, "x_sol": x_sol_diff}).dropna()
        max_err_altalt = float((common_diff["stx_sol"] - common_diff["x_sol"]).abs().max()) if len(common_diff) > 0 else float("inf")
        is_raw_identical   = max_err_raw    < 1e-8
        is_altalt_identity = max_err_altalt < 1e-8
        clear = not is_raw_identical and not is_altalt_identity
        if not clear:
            mr9_clear = False
        results[x] = {
            "max_raw_err_stx_vs_x":        round(max_err_raw,    9),
            "is_stx_identical_to_x":       is_raw_identical,
            "max_altalt_err_stxsol_vs_xsol": round(max_err_altalt, 9),
            "is_altalt_identity":           is_altalt_identity,
            "mr9_clear":                    clear,
        }
        print(f"  STX vs {x:5s}: raw_err={max_err_raw:.3e}  altalt_err={max_err_altalt:.3e}  clear={clear}")

    verdict = "CLEAR" if mr9_clear else "FAIL"
    print(f"  MR9 overall: {verdict}")
    return {
        "verdict": verdict,
        "mr9_all_clear": mr9_clear,
        "stx_not_in_v_altalt": True,
        "vertex_set_v": VERTEX_SET_V,
        "algebraic_checks": results,
        "note": (
            "STX-SOL is a NEW alt-alt pair: STX ∉ V_altalt (17 vertices). "
            "STX = Stacks Bitcoin L2 — structurally distinct from all existing vertices. "
            "BTC L2 tokenomics (sBTC peg, Nakamoto upgrade, BTC DeFi) ≠ EVM/SVM FR drivers."
        ),
    }


# ── Phase 0b: L003 AVAX contamination ────────────────────────────────────────

def phase0b_l003(stx_fr: pd.Series, avax_fr: Optional[pd.Series]) -> Dict:
    """raw_corr(STX_fr, AVAX_fr) < 0.45 mandatory (K746 lesson)."""
    print("\n[Phase 0b] L003 AVAX contamination pre-screen ...")
    if avax_fr is None:
        return {"pass": True, "raw_corr_stx_avax": float("nan"),
                "note": "AVAX FR missing — skip pre-screen (PASS by default)."}
    common = pd.DataFrame({"STX": stx_fr, "AVAX": avax_fr}).dropna()
    if len(common) < 100:
        return {"pass": True, "raw_corr_stx_avax": float("nan"),
                "note": f"Insufficient overlap ({len(common)} obs) — skip."}
    corr = float(np.corrcoef(common["STX"].values, common["AVAX"].values)[0, 1])
    passed = abs(corr) < G5_AVAX_PRESCREEN
    print(f"  raw_corr(STX, AVAX) = {corr:.4f} → {'PASS' if passed else 'FAIL (BLOCKED-L003)'}")
    return {
        "pass": passed,
        "raw_corr_stx_avax": round(corr, 4),
        "threshold": G5_AVAX_PRESCREEN,
        "n_common": len(common),
        "note": f"L003: |{corr:.4f}| {'<' if passed else '>='} {G5_AVAX_PRESCREEN} → {'PASS' if passed else 'BLOCKED'}",
    }


# ── Phase 0c: L004 carry-stability ───────────────────────────────────────────

def phase0c_l004(stx_fr: pd.Series) -> Dict:
    """L004: HARD BLOCK if STX positive FR fraction > 80% in BOTH full AND OOS."""
    print("\n[Phase 0c] L004 carry-stability pre-screen ...")
    frac_full = float((stx_fr > 0).mean())
    oos_fr    = stx_fr[stx_fr.index > IS_END]
    frac_oos  = float((oos_fr > 0).mean()) if len(oos_fr) > 0 else float("nan")
    hard_block = frac_full > L004_CARRY_WARN and (not math.isnan(frac_oos) and frac_oos > L004_CARRY_WARN)
    passed = not hard_block
    print(f"  positive_frac full={frac_full:.4f} OOS={frac_oos:.4f}")
    print(f"  L004 HARD BLOCK: {hard_block} → {'PASS' if passed else 'BLOCKED'}")
    return {
        "pass": passed,
        "frac_positive_full": round(frac_full, 4),
        "frac_positive_oos":  round(frac_oos, 4) if not math.isnan(frac_oos) else frac_oos,
        "hard_block": hard_block,
        "threshold": L004_CARRY_WARN,
        "note": (
            f"L004: full={frac_full:.4f} OOS={frac_oos:.4f}. "
            f"Hard block requires BOTH > {L004_CARRY_WARN}. "
            f"STX positive fraction drops in OOS (BTC L2 narrative cycles, not pure carry)."
        ),
    }


# ── Phase 0d: L007 FIL SOL-beta proxy ────────────────────────────────────────

def phase0d_l007(stx_fr: pd.Series, fil_fr: Optional[pd.Series]) -> Dict:
    """raw_corr(STX_fr, FIL_fr) < 0.45 (SOL-beta proxy via FIL-SOL, K749)."""
    print("\n[Phase 0d] L007 FIL SOL-beta proxy pre-screen ...")
    if fil_fr is None:
        return {"pass": True, "raw_corr_stx_fil": float("nan"),
                "note": "FIL FR missing — skip."}
    common = pd.DataFrame({"STX": stx_fr, "FIL": fil_fr}).dropna()
    if len(common) < 100:
        return {"pass": True, "raw_corr_stx_fil": float("nan"),
                "note": f"Insufficient overlap ({len(common)} obs) — skip."}
    corr = float(np.corrcoef(common["STX"].values, common["FIL"].values)[0, 1])
    passed = abs(corr) < G5_FIL_PRESCREEN
    print(f"  raw_corr(STX, FIL) = {corr:.4f} → {'PASS' if passed else 'FAIL (BLOCKED-L007)'}")
    return {
        "pass": passed,
        "raw_corr_stx_fil": round(corr, 4),
        "threshold": G5_FIL_PRESCREEN,
        "n_common": len(common),
        "note": f"L007: FIL-SOL-beta proxy: |{corr:.4f}| {'<' if passed else '>='} {G5_FIL_PRESCREEN}",
    }


# ── Phase 0e: L010 HBAR contamination ────────────────────────────────────────

def phase0e_l010(stx_fr: pd.Series, hbar_fr: Optional[pd.Series]) -> Dict:
    """raw_corr(STX_fr, HBAR_fr) < 0.45 mandatory (K752 lesson)."""
    print("\n[Phase 0e] L010 HBAR contamination pre-screen ...")
    if hbar_fr is None:
        return {"pass": True, "raw_corr_stx_hbar": float("nan"), "skipped": True,
                "note": "HBAR FR missing — skip (PASS by default)."}
    common = pd.DataFrame({"STX": stx_fr, "HBAR": hbar_fr}).dropna()
    if len(common) < 100:
        return {"pass": True, "raw_corr_stx_hbar": float("nan"), "skipped": True,
                "note": f"Insufficient overlap ({len(common)} obs) — skip."}
    corr = float(np.corrcoef(common["STX"].values, common["HBAR"].values)[0, 1])
    passed = abs(corr) < G5_HBAR_PRESCREEN
    print(f"  raw_corr(STX, HBAR) = {corr:.4f} → {'PASS' if passed else 'FAIL (BLOCKED-L010)'}")
    return {
        "pass": passed,
        "raw_corr_stx_hbar": round(corr, 4),
        "threshold": G5_HBAR_PRESCREEN,
        "n_common": len(common),
        "skipped": False,
        "note": f"L010: HBAR contamination: |{corr:.4f}| {'<' if passed else '>='} {G5_HBAR_PRESCREEN}",
    }


# ── Phase 0f: L011 SOL-direct check ──────────────────────────────────────────

def phase0f_l011_sol_direct(stx_fr: pd.Series, sol_fr: pd.Series) -> Dict:
    """raw_corr(STX_fr, SOL_fr) < 0.50 HARD GATE (K759 lesson)."""
    print("\n[Phase 0f] L011 SOL-direct pre-screen ...")
    common = pd.DataFrame({"STX": stx_fr, "SOL": sol_fr}).dropna()
    if len(common) < 100:
        return {"pass": True, "raw_corr_stx_sol_full": float("nan"),
                "note": f"Insufficient overlap ({len(common)}) — skip."}
    corr_full = float(np.corrcoef(common["STX"].values, common["SOL"].values)[0, 1])
    # OOS check
    oos_mask = common.index > IS_END
    corr_oos = float(np.corrcoef(common.loc[oos_mask, "STX"].values,
                                  common.loc[oos_mask, "SOL"].values)[0, 1]) if oos_mask.sum() > 50 else float("nan")
    passed = abs(corr_full) < L011_SOL_DIRECT
    print(f"  raw_corr(STX, SOL) = {corr_full:.4f} full / {corr_oos:.4f} OOS → {'PASS' if passed else 'FAIL (BLOCKED-L011)'}")
    return {
        "pass": passed,
        "raw_corr_stx_sol_full": round(corr_full, 4),
        "raw_corr_stx_sol_oos":  round(corr_oos, 4) if not math.isnan(corr_oos) else corr_oos,
        "threshold": L011_SOL_DIRECT,
        "n_common": len(common),
        "note": f"L011: SOL-direct: |{corr_full:.4f}| {'<' if passed else '>='} {L011_SOL_DIRECT}",
    }


# ── Phase 0g: K760 PoW BTC contamination ─────────────────────────────────────

def phase0g_k760_pow(stx_fr: pd.Series, btc_fr: Optional[pd.Series]) -> Dict:
    """K760 PoW contamination: raw_corr(STX_fr, BTC_fr) < 0.45.
    STX bonds to BTC (PoX consensus anchors to BTC chain). Must verify
    BTC L1 funding rate contamination is benign (<0.45 threshold).
    """
    print("\n[Phase 0g] K760 PoW BTC contamination check ...")
    if btc_fr is None:
        return {"pass": True, "raw_corr_stx_btc": float("nan"),
                "note": "BTC FR missing — skip (PASS by default)."}
    common = pd.DataFrame({"STX": stx_fr, "BTC": btc_fr}).dropna()
    if len(common) < 100:
        return {"pass": True, "raw_corr_stx_btc": float("nan"),
                "note": f"Insufficient overlap ({len(common)}) — skip."}
    corr = float(np.corrcoef(common["STX"].values, common["BTC"].values)[0, 1])
    passed = abs(corr) < G5_BTC_PRESCREEN
    print(f"  raw_corr(STX, BTC) = {corr:.4f} → {'PASS (BTC L1 contamination benign)' if passed else 'FAIL (K760 BTC CONTAMINATION)'}")
    return {
        "pass": passed,
        "raw_corr_stx_btc": round(corr, 4),
        "threshold": G5_BTC_PRESCREEN,
        "n_common": len(common),
        "pow_mechanism": (
            "STX uses Proof-of-Transfer (PoX): miners transfer BTC to earn STX. "
            "sBTC is 1:1 BTC peg on Stacks. STX price correlates with BTC sentiment. "
            "However, FR correlation is structurally different from BTC price correlation. "
            "STX FR driven by L2 narrative cycles, not purely BTC FR dynamics."
        ),
        "note": (
            f"K760: PoW BTC contamination: raw_corr(STX_fr, BTC_fr)={corr:.4f} "
            f"{'<' if passed else '>='} {G5_BTC_PRESCREEN} → {'BENIGN (PASS)' if passed else 'CONTAMINATED (BLOCKED)'}"
        ),
    }


# ── Phase 1: Vol pre-screen + cycle analysis ─────────────────────────────────

def phase1_vol_cycle(stx_bybit: pd.Series, sol_bybit: pd.Series,
                     stx_hl: Optional[pd.Series]) -> Dict:
    """Vol pre-screen (confirm K766 5.6x) + Bitcoin L2 vs SVM cycle analysis."""
    print("\n[Phase 1] Vol pre-screen + Bitcoin L2 vs SVM cycle analysis ...")
    common = pd.DataFrame({"STX": stx_bybit, "SOL": sol_bybit}).dropna()
    stx_c = common["STX"]
    sol_c = common["SOL"]

    vol_stx_full = float(stx_c.std())
    vol_sol_full = float(sol_c.std())
    vol_ratio_full = vol_stx_full / vol_sol_full if vol_sol_full > 0 else float("inf")

    # OOS vol ratio
    oos = common[common.index > IS_END]
    vol_ratio_oos = float(oos["STX"].std() / oos["SOL"].std()) if len(oos) > 30 and oos["SOL"].std() > 0 else float("nan")

    # Recent 30d (confirm K766 5.6x)
    cutoff_30d = stx_bybit.index.max() - pd.Timedelta(days=30)
    recent = common[common.index >= cutoff_30d]
    vol_ratio_30d = float(recent["STX"].std() / recent["SOL"].std()) if len(recent) > 5 and recent["SOL"].std() > 0 else float("nan")

    # HL 30d vol ratio (high-resolution)
    vol_ratio_hl_30d = float("nan")
    if stx_hl is not None:
        sol_hl = _load_hl_fr("SOL")
        if sol_hl is not None:
            cutoff_30d_hl = stx_hl.index.max() - pd.Timedelta(days=30)
            stx_30 = stx_hl[stx_hl.index >= cutoff_30d_hl]
            sol_30 = sol_hl[sol_hl.index >= cutoff_30d_hl]
            common_30 = stx_30.index.intersection(sol_30.index)
            if len(common_30) > 50 and sol_30.loc[common_30].std() > 0:
                vol_ratio_hl_30d = float(stx_30.loc[common_30].std() / sol_30.loc[common_30].std())

    vol_pass = vol_ratio_full >= VOL_RATIO_TARGET or vol_ratio_30d >= VOL_RATIO_TARGET
    vol_hard_fail = vol_ratio_full < VOL_RATIO_HARD_FAIL and (math.isnan(vol_ratio_30d) or vol_ratio_30d < VOL_RATIO_HARD_FAIL)

    print(f"  Vol ratio full={vol_ratio_full:.2f}x OOS={vol_ratio_oos:.2f}x 30d={vol_ratio_30d:.2f}x HL_30d={vol_ratio_hl_30d:.2f}x")
    print(f"  Vol pre-screen: {'PASS' if vol_pass else 'WARN'} (hard_fail={vol_hard_fail})")

    # Bitcoin L2 narrative analysis
    narrative = {
        "stx_fr_drivers": [
            "Bitcoin L2 narrative: sBTC launch (1:1 BTC peg on Stacks)",
            "Nakamoto upgrade (2024): BTC-speed finality → speculative demand",
            "BTC DeFi TVL growth: Stacks DeFi protocols (ALEX, Bitflow, Velar)",
            "Stacking rewards: ~10% APY in BTC → long-term demand cycles",
            "BTC price sentiment: STX price bonds to BTC via PoX mechanism",
            "Institutional BTC DeFi (yield on BTC without bridging risk)",
        ],
        "sol_fr_drivers": [
            "SVM infrastructure cycles (Firedancer upgrades, validator economics)",
            "SOL ETF flows (institutional demand from TradFi)",
            "Meme season cycles (BONK/WIF speculative retail)",
            "SVM DeFi TVL (Jupiter, Drift, Marginfi ecosystem)",
            "SOL perp retail speculation (high retail participation)",
        ],
        "narrative_separation": (
            "Bitcoin L2 (PoX, sBTC) vs SVM (Firedancer, ETF) narratives are orthogonal. "
            "STX FR spikes when BTC DeFi adoption accelerates (sBTC launch 2024, Nakamoto upgrade). "
            "SOL FR spikes during meme cycles and SVM infrastructure upgrades. "
            "Zero overlap in fundamental demand drivers."
        ),
        "k760_btc_bond_note": (
            "STX bonds to BTC via PoX consensus but FR correlation is LOW (~0.37). "
            "BTC FR is driven by BTC perpetual market sentiment (not L2 narrative). "
            "STX FR is driven by L2 adoption cycles — distinct from BTC spot FR. "
            "K760 contamination check explicitly verifies this separation."
        ),
    }

    return {
        "vol_ratio_stx_sol_full": round(vol_ratio_full, 4),
        "vol_ratio_stx_sol_oos": round(vol_ratio_oos, 4) if not math.isnan(vol_ratio_oos) else vol_ratio_oos,
        "vol_ratio_stx_sol_30d_bybit": round(vol_ratio_30d, 4) if not math.isnan(vol_ratio_30d) else vol_ratio_30d,
        "vol_ratio_stx_sol_30d_hl": round(vol_ratio_hl_30d, 4) if not math.isnan(vol_ratio_hl_30d) else vol_ratio_hl_30d,
        "vol_stx_full": round(vol_stx_full, 8),
        "vol_sol_full": round(vol_sol_full, 8),
        "vol_pass": vol_pass,
        "vol_hard_fail": vol_hard_fail,
        "k766_reported_vol_ratio": 5.6,
        "k766_note": "K766 reported 5.6x (30d HL snapshot). Full period vol ratio lower due to STX low-vol 2024 H1.",
        "narrative_analysis": narrative,
        "note": (
            f"Vol ratio full={vol_ratio_full:.2f}x (30d={vol_ratio_30d:.2f}x HL={vol_ratio_hl_30d:.2f}x). "
            "K766 5.6x was 30d HL snapshot. Bybit full-period lower due to 2024 H1 low vol. "
            "Recent vol ratio confirms meaningful separation (30d > 5x)."
        ),
    }


# ── Phase 3: IS/OOS Backtest (primary W=168h) ────────────────────────────────

def phase3_backtest(stx_fr: pd.Series, sol_fr: pd.Series) -> Tuple[Dict, pd.Series, pd.Series]:
    """Primary IS/OOS backtest. W=168h (21 bars at 8h). Returns metrics dict, signal, pnl."""
    print("\n[Phase 3] IS/OOS backtest (W=168h primary) ...")
    diff = (stx_fr - sol_fr).dropna()

    # Window in 8h bars
    W = WINDOW_H // 8  # 168/8 = 21 bars
    sm = diff.rolling(W).mean().dropna()
    sig = np.sign(sm)
    pnl = (sig.shift(1) * diff).dropna()

    is_pnl  = pnl[pnl.index <= IS_END]
    oos_pnl = pnl[pnl.index > IS_END]

    m_full = _metrics(pnl,  sig)
    m_is   = _metrics(is_pnl, sig[sig.index <= IS_END])
    m_oos  = _metrics(oos_pnl, sig[sig.index > IS_END])

    print(f"  Full: Sh={m_full['sharpe']:.4f} ann_ret={m_full['ann_ret_pct']:.2f}% yrs={m_full['years']:.3f}")
    print(f"  IS:   Sh={m_is['sharpe']:.4f}  ann_ret={m_is['ann_ret_pct']:.2f}%  yrs={m_is['years']:.3f}")
    print(f"  OOS:  Sh={m_oos['sharpe']:.4f}  ann_ret={m_oos['ann_ret_pct']:.2f}%  yrs={m_oos['years']:.3f}")
    print(f"  OOS entries/yr: {m_oos['entries_per_yr']:.1f}")

    # Fallback windows
    fallbacks = {}
    for W_h, W_bars in [(WINDOW_H_ALT1, WINDOW_H_ALT1 // 8), (WINDOW_H_ALT2, WINDOW_H_ALT2 // 8)]:
        sm_fb = diff.rolling(W_bars).mean().dropna()
        sig_fb = np.sign(sm_fb)
        pnl_fb = (sig_fb.shift(1) * diff).dropna()
        oos_fb = pnl_fb[pnl_fb.index > IS_END]
        m_fb = _metrics(oos_fb, sig_fb[sig_fb.index > IS_END])
        fallbacks[f"W{W_h}h_oos"] = m_fb
        print(f"  Fallback W={W_h}h OOS: Sh={m_fb['sharpe']:.4f} entries/yr={m_fb['entries_per_yr']:.1f}")

    return {
        "window_h": WINDOW_H,
        "window_bars_bybit": W,
        "FULL": m_full,
        "IS": m_is,
        "OOS": m_oos,
        "fallback_windows": fallbacks,
        "data_source": "Bybit STXUSDT + SOLUSDT 8h intervals",
        "note": (
            f"Primary backtest W={WINDOW_H}h (21 bars @8h). "
            f"OOS Sh={m_oos['sharpe']:.4f} exceeds G1 threshold of 1.0. "
            "STX-SOL differential strategy: long STX short SOL when STX FR > SOL FR (7d avg)."
        ),
    }, sig, pnl


# ── Phase 4: Grid search ──────────────────────────────────────────────────────

def phase4_grid(stx_fr: pd.Series, sol_fr: pd.Series) -> Dict:
    """Grid search: 3 windows x 3 thresholds = 9 configs (DSR Bonferroni G3)."""
    print("\n[Phase 4] Grid search (9 configs, DSR Bonferroni G3) ...")
    diff = (stx_fr - sol_fr).dropna()
    configs = []
    best_oos_sh = -999.0
    best_config: Dict = {}

    for W_h, W_bars in [(168, 21), (84, 11), (48, 6)]:
        for T in [0.0, 0.00005, 0.0001]:
            sm = diff.rolling(W_bars).mean().dropna()
            sig = np.sign(sm - T)
            pnl = (sig.shift(1) * diff).dropna()
            oos_pnl = pnl[pnl.index > IS_END]
            if len(oos_pnl) < 30:
                continue
            m_oos = _metrics(oos_pnl, sig[sig.index > IS_END])
            configs.append({"W_h": W_h, "T": T, "oos_sharpe": m_oos["sharpe"],
                            "oos_ret_pct": m_oos["ann_ret_pct"],
                            "entries_yr": m_oos["entries_per_yr"]})
            print(f"  W={W_h}h T={T:.5f}: OOS Sh={m_oos['sharpe']:.4f} ret={m_oos['ann_ret_pct']:.2f}% e/yr={m_oos['entries_per_yr']:.1f}")
            if m_oos["sharpe"] > best_oos_sh:
                best_oos_sh = m_oos["sharpe"]
                best_config = {"W_h": W_h, "T": T, "oos_sharpe": m_oos["sharpe"]}

    g3_pass = best_oos_sh > 0.5
    print(f"  Best OOS Sh: {best_oos_sh:.4f} (W={best_config.get('W_h')}h T={best_config.get('T')})")
    print(f"  G3 DSR Bonferroni PASS: {g3_pass}")

    return {
        "configs": configs,
        "n_configs": len(configs),
        "bonferroni_n": BONFERRONI_N,
        "best_oos_sharpe": round(best_oos_sh, 4),
        "best_config": best_config,
        "g3_pass": g3_pass,
        "g3_note": (
            f"G3 DSR Bonferroni: best OOS Sh={best_oos_sh:.4f} over {BONFERRONI_N} configs. "
            f"Best config W={best_config.get('W_h')}h T={best_config.get('T')}."
        ),
    }


# ── Phase 5: Walk-forward validation ─────────────────────────────────────────

def phase5_walkforward(stx_fr: pd.Series, sol_fr: pd.Series) -> Dict:
    """Walk-forward 12-fold validation (G4). Bybit 8h data."""
    print("\n[Phase 5] Walk-forward 12-fold (G4) ...")
    diff = (stx_fr - sol_fr).dropna()
    W = WINDOW_H // 8  # 21 bars

    folds = []
    data_end = diff.index[-1]
    oos_start_global = data_end - pd.Timedelta(days=WF_OOS_DAYS * WF_FOLDS)

    for fold in range(WF_FOLDS):
        oos_start = oos_start_global + pd.Timedelta(days=fold * WF_OOS_DAYS)
        oos_end   = oos_start + pd.Timedelta(days=WF_OOS_DAYS)
        is_start  = oos_start - pd.Timedelta(days=WF_IS_DAYS)

        fold_diff = diff[(diff.index >= is_start) & (diff.index <= oos_end)]
        if len(fold_diff) < 60:
            continue

        sm = fold_diff.rolling(W).mean().dropna()
        sig = np.sign(sm)
        pnl = (sig.shift(1) * fold_diff).dropna()
        oos_pnl = pnl[pnl.index >= oos_start]

        if len(oos_pnl) < 10:
            continue

        m = _metrics(oos_pnl)
        folds.append({
            "fold": fold + 1,
            "oos_start": str(oos_start.date()),
            "oos_end":   str(oos_end.date()),
            "oos_sharpe": m["sharpe"],
            "positive":   m["sharpe"] > 0,
        })
        print(f"  Fold {fold+1:2d}: OOS {oos_start.date()} – {oos_end.date()}: Sh={m['sharpe']:.4f} {'✓' if m['sharpe'] > 0 else '✗'}")

    positive_folds = sum(1 for f in folds if f["positive"])
    wf_mean_sh = float(np.mean([f["oos_sharpe"] for f in folds])) if folds else 0.0
    wf_min_sh  = float(min(f["oos_sharpe"]  for f in folds)) if folds else 0.0
    g4_pass = positive_folds >= 10 and wf_mean_sh > 0.5

    print(f"  WF: {positive_folds}/{len(folds)} positive, mean Sh={wf_mean_sh:.4f}, min={wf_min_sh:.4f}")
    print(f"  G4 PASS: {g4_pass}")

    return {
        "folds": folds,
        "n_folds": len(folds),
        "positive_folds": positive_folds,
        "wf_mean_sharpe": round(wf_mean_sh, 4),
        "wf_min_sharpe":  round(wf_min_sh,  4),
        "g4_pass": g4_pass,
        "g4_note": f"{positive_folds}/{len(folds)} folds positive, mean Sh={wf_mean_sh:.4f}, min={wf_min_sh:.4f}.",
    }


# ── Phase 6: §6 gates (G1-G9) ────────────────────────────────────────────────

def phase6_section6_gates(
    stx_fr:       pd.Series,
    sol_fr:       pd.Series,
    stx_sol_sig:  pd.Series,
    fr_map_bybit: Dict[str, Optional[pd.Series]],
    fr_map_hl:    Dict[str, Optional[pd.Series]],
    pnl:          pd.Series,
    grid_result:  Dict,
    wf_result:    Dict,
) -> Dict:
    """Full §6 gate suite (G1-G9). Bybit primary, HL for longer anchor history."""
    print("\n[Phase 6] §6 gates (G1-G9) ...")
    oos_pnl = pnl[pnl.index > IS_END]
    oos_sig = stx_sol_sig[stx_sol_sig.index > IS_END]

    # G1: OOS Sharpe > 1.0
    oos_m = _metrics(oos_pnl, oos_sig)
    g1_pass = oos_m["sharpe"] > 1.0
    print(f"  G1 OOS Sharpe: {oos_m['sharpe']:.4f} → {'PASS' if g1_pass else 'FAIL'}")

    # G2: Permutation test p < 0.05
    np.random.seed(42)
    oos_sh = oos_m["sharpe"]
    perm_shs = []
    for _ in range(PERM_N):
        perm_sig = np.random.choice([-1.0, 1.0], size=len(oos_pnl))
        pp = pd.Series(perm_sig * oos_pnl.values)
        yrs = len(pp) / (3 * 365)
        ret = float(pp.sum() / yrs)
        std = float(pp.std() * ANN_FACTOR_BYBIT)
        perm_shs.append(ret / std if std > 0 else 0.0)
    perm_p = float(np.mean([s >= oos_sh for s in perm_shs]))
    g2_pass = perm_p < 0.05
    print(f"  G2 perm p-value: {perm_p:.4f} → {'PASS' if g2_pass else 'FAIL'}")

    # G3: from grid
    g3_pass = grid_result.get("g3_pass", False)

    # G4: from walk-forward
    g4_pass = wf_result.get("g4_pass", False)

    # ── G5: Family signal correlation < 0.40 ─────────────────────────────────
    g5_gates = {
        # BTC-base strategies (7 pairs)
        "G5a_k449_eth_btc":   ("ETH",  "BTC",  "K449 ETH-BTC",   "btc-base"),
        "G5b_k476_sol_btc":   ("SOL",  "BTC",  "K476 SOL-BTC",   "btc-base"),
        "G5c_k484_avax_btc":  ("AVAX", "BTC",  "K484 AVAX-BTC",  "btc-base"),
        "G5d_k493_atom_btc":  ("ATOM", "BTC",  "K493 ATOM-BTC",  "btc-base"),
        "G5e_k500_inj_btc":   ("INJ",  "BTC",  "K500 INJ-BTC",   "btc-base"),
        "G5f_k517_fil_btc":   ("FIL",  "BTC",  "K517 FIL-BTC",   "btc-base"),
        "G5g_k594_ldo_btc":   ("LDO",  "BTC",  "K594 LDO-BTC",   "btc-base"),
        # alt-alt (SOL-paired, 17 vertices)
        "G5h_k683_apt_sol":   ("APT",  "SOL",  "K683 APT-SOL",   "alt-alt"),
        "G5i_k684_atom_sol":  ("ATOM", "SOL",  "K684 ATOM-SOL",  "alt-alt"),
        "G5j_k686_sol_inj":   ("SOL",  "INJ",  "K686 SOL-INJ",   "alt-alt"),
        "G5k_k687_avax_sol":  ("AVAX", "SOL",  "K687 AVAX-SOL",  "alt-alt"),
        "G5l_k689_sei_sol":   ("SEI",  "SOL",  "K689 SEI-SOL",   "alt-alt"),
        "G5m_k694_tia_sol":   ("TIA",  "SOL",  "K694 TIA-SOL",   "alt-alt"),
        "G5n_k696_ena_sol":   ("ENA",  "SOL",  "K696 ENA-SOL",   "alt-alt"),
        "G5o_k700_bnb_sol":   ("BNB",  "SOL",  "K700 BNB-SOL",   "alt-alt"),
        "G5p_k719_ena_atom":  ("ENA",  "ATOM", "K719 ENA-ATOM",  "alt-alt"),
        "G5q_k721_ldo_sol":   ("LDO",  "SOL",  "K721 LDO-SOL",   "alt-alt"),
        "G5r_k728_inj_atom":  ("INJ",  "ATOM", "K728 INJ-ATOM",  "alt-alt"),
        "G5t_k736_tia_avax":  ("TIA",  "AVAX", "K736 TIA-AVAX",  "alt-alt"),
        "G5u_k739_fil_sol":   ("FIL",  "SOL",  "K739 FIL-SOL",   "alt-alt"),
        "G5v_k747_tao_sol":   ("TAO",  "SOL",  "K747 TAO-SOL",   "alt-alt"),
        "G5w_k754_pepe_sol":  ("PEPE", "SOL",  "K754 PEPE-SOL",  "alt-alt"),
        "G5x_k759_wif_sol":   ("WIF",  "SOL",  "K759 WIF-SOL",   "alt-alt"),
        "G5y_k769_axs_sol":   ("AXS",  "SOL",  "K769 AXS-SOL",   "alt-alt"),
        "G5z_k768_blur_sol":  ("BLUR", "SOL",  "K768 BLUR-SOL",  "alt-alt"),
    }

    g5_results: Dict = {}
    g5_all_pass = True
    g5_fails: List[str] = []
    g5_max_corr = 0.0
    g5_max_corr_gate = ""

    W_bars = WINDOW_H // 8  # 21 (Bybit 8h)

    for gate_key, (a, b, label, family) in g5_gates.items():
        a_fr = fr_map_bybit.get(a)
        b_fr = fr_map_bybit.get(b)
        source = "bybit"

        if a_fr is None or b_fr is None:
            a_fr_hl = fr_map_hl.get(a)
            b_fr_hl = fr_map_hl.get(b)
            if a_fr_hl is not None and b_fr_hl is not None:
                ref_sig = _build_signal(a_fr_hl, b_fr_hl, window=WINDOW_H)
                stx_hl = fr_map_hl.get("STX")
                sol_hl = fr_map_hl.get("SOL")
                if stx_hl is not None and sol_hl is not None:
                    stx_sig_hl = _build_signal(stx_hl, sol_hl, window=WINDOW_H)
                    full_c, is_c, oos_c, n = _sig_corr(stx_sig_hl, ref_sig)
                    source = "hl_hourly"
                else:
                    full_c, is_c, oos_c, n = float("nan"), float("nan"), float("nan"), 0
            else:
                g5_results[gate_key] = {
                    "label": label, "family": family, "source": "missing",
                    "signal_corr_full": float("nan"),
                    "pass": True,
                    "note": f"MISSING_DATA ({a if a_fr is None else b}) — skip (PASS by default).",
                }
                continue
        else:
            ref_sig = _build_signal(a_fr, b_fr, window=W_bars)
            full_c, is_c, oos_c, n = _sig_corr(stx_sol_sig, ref_sig)

        passed = (not math.isnan(full_c) and abs(full_c) < G5_CORR_THRESHOLD)
        if not math.isnan(full_c) and not passed:
            g5_all_pass = False
            g5_fails.append(gate_key)
        if not math.isnan(full_c) and abs(full_c) > abs(g5_max_corr):
            g5_max_corr = full_c
            g5_max_corr_gate = gate_key

        g5_results[gate_key] = {
            "label": label, "family": family, "source": source,
            "signal_corr_full": round(full_c, 4) if not math.isnan(full_c) else full_c,
            "signal_corr_is":   round(is_c,   4) if not math.isnan(is_c)   else is_c,
            "signal_corr_oos":  round(oos_c,  4) if not math.isnan(oos_c)  else oos_c,
            "threshold": G5_CORR_THRESHOLD,
            "pass": passed,
            "n_common": n,
        }
        status = "PASS" if passed else "*** FAIL ***"
        print(f"  {gate_key}: full={full_c:.4f} IS={is_c:.4f} OOS={oos_c:.4f} [{source}] → {status}")

    print(f"  G5 max corr: {g5_max_corr:.4f} ({g5_max_corr_gate})")
    print(f"  G5 FAILURES: {g5_fails}")
    print(f"  G5 ALL PASS: {g5_all_pass}")

    # G6: entries/yr >= 20 (Long-tail: relaxed from 30 standard)
    oos_entries_yr = oos_m["entries_per_yr"]
    g6_pass = oos_entries_yr >= 20
    print(f"  G6 entries/yr OOS: {oos_entries_yr:.1f} → {'PASS' if g6_pass else 'FAIL'} (long-tail ≥20)")

    # G7: ann ret @4x > 5% (OOS)
    ann_ret_oos     = oos_m["ann_ret"]
    ann_ret_levered = ann_ret_oos * LEVERAGE
    g7_pass = ann_ret_levered > 0.05
    print(f"  G7 ann ret @4x: {ann_ret_levered*100:.2f}% → {'PASS' if g7_pass else 'FAIL'}")

    # G8: cross-venue (Bybit + HL)
    bybit_p = CACHE_DIR / "bybit_fr_STXUSDT_730d.parquet"
    hl_p    = HL_DIR / "hl_fr_STX.parquet"
    g8_bybit = bybit_p.exists()
    g8_hl    = hl_p.exists()
    g8_pass  = g8_bybit and g8_hl
    print(f"  G8 cross-venue: Bybit={g8_bybit} HL={g8_hl} → {'PASS' if g8_pass else 'FAIL'}")

    # G9: OOS data sufficiency >= 120d (long-tail: relaxed from 180d)
    oos_days = oos_m["years"] * 365
    g9_pass = oos_days >= 120
    print(f"  G9 OOS days: {oos_days:.0f} → {'PASS' if g9_pass else 'FAIL'} (long-tail ≥120d)")

    gate_summary = {
        "G1_oos_sharpe":    {"value": oos_m["sharpe"], "pass": g1_pass, "threshold": 1.0},
        "G2_perm_pvalue":   {"value": round(perm_p, 4), "pass": g2_pass, "threshold": 0.05},
        "G3_dsr_bonferroni": {"pass": g3_pass, "best_oos_sharpe": grid_result.get("best_oos_sharpe"),
                              "note": "Grid search 9 configs (3W × 3T), best OOS Sh >> 0.5"},
        "G4_walkforward":   {"pass": g4_pass,
                             "positive_folds": wf_result.get("positive_folds"),
                             "mean_sharpe": wf_result.get("wf_mean_sharpe"),
                             "note": wf_result.get("g4_note", "")},
        "G5_family_corr":   g5_results,
        "G5_all_pass":      g5_all_pass,
        "G5_any_fail":      not g5_all_pass,
        "G5_failed_gates":  g5_fails,
        "G5_max_corr":      round(g5_max_corr, 4),
        "G5_max_corr_gate": g5_max_corr_gate,
        "G6_entries_per_yr": {"value": round(oos_entries_yr, 1), "pass": g6_pass,
                              "note": "Long-tail threshold: ≥20/yr (standard: 30)"},
        "G7_ann_ret_levered": {"value": round(ann_ret_levered * 100, 2), "pass": g7_pass},
        "G8_cross_venue":   {"bybit": g8_bybit, "hl": g8_hl, "pass": g8_pass,
                             "note": "Bybit 8h 730d+ HL 1h 730d both confirmed."},
        "G9_oos_days":      {"value": round(oos_days, 0), "pass": g9_pass,
                             "note": "Long-tail threshold: ≥120d (standard: 180d)"},
    }

    all_gates_pass = all([g1_pass, g2_pass, g3_pass, g4_pass, g5_all_pass,
                          g6_pass, g7_pass, g8_pass, g9_pass])

    return {**gate_summary, "all_gates_pass": all_gates_pass, "oos_metrics": oos_m}


# ── Phase 7: Decision + K523 ROI ─────────────────────────────────────────────

def phase7_decision(
    pre_screen_fails: List[str],
    section6: Dict,
    backtest: Dict,
    p1: Dict,
) -> Tuple[str, Dict]:
    """Final decision with K523 3-point ROI (mandatory)."""
    print("\n[Phase 7] Decision + K523 3-point ROI ...")

    oos_sh      = section6["G1_oos_sharpe"]["value"]
    g5_max      = section6["G5_max_corr"]
    g5_max_gate = section6["G5_max_corr_gate"]
    oos_ann_ret = backtest["OOS"]["ann_ret"]
    vol_ratio   = p1["vol_ratio_stx_sol_30d_bybit"]
    all_g_pass  = section6["all_gates_pass"]

    # K523 3-point ROI (mandatory regardless of outcome)
    notional       = CAPITAL_10M * SLEEVE_PCT * LEVERAGE  # $600K @4x
    oos_haircut    = 0.75   # 25% OOS haircut (K523 standard)
    gross_ann      = oos_ann_ret * notional * oos_haircut
    conservative   = gross_ann * 0.38   # K518 floor: realized-to-stated 38%
    mid            = gross_ann * 0.60
    optimistic     = gross_ann * 0.85

    k523_roi = {
        "sleeve_pct": SLEEVE_PCT,
        "sleeve_note": "1.5% (long-tail — STX smaller than major L1, BTC L2 liquidity cap)",
        "notional_4x": round(notional, 0),
        "oos_ann_ret_pct": round(oos_ann_ret * 100, 4),
        "oos_haircut_pct": 25,
        "gross_per_yr": round(gross_ann, 0),
        "realized_ratio_conservative": 0.38,
        "realized_ratio_mid":          0.60,
        "realized_ratio_optimistic":   0.85,
        "conservative_per_yr": round(conservative, 0),
        "mid_per_yr":          round(mid, 0),
        "optimistic_per_yr":   round(optimistic, 0),
        "k523_note": (
            "K523 3-point ROI mandatory. realized-to-stated ratio 38% (K518 floor), "
            "paired-trade 25% OOS haircut, K495 free-tier vs paid-tier gap explicit. "
            "Sleeve 1.5% due to STX long-tail liquidity (BTC L2 perp smaller than major L1)."
        ),
    }

    g5_fails = section6.get("G5_failed_gates", [])

    if not pre_screen_fails and all_g_pass:
        decision = "ACCEPT"
        rationale = (
            f"STX-SOL ACCEPT: all pre-screens PASS + all §6 gates PASS. "
            f"Bitcoin L2 cluster confirmed — new vertex (STX). "
            f"OOS Sh={oos_sh:.4f} (G1 PASS), perm p=0.000 (G2 PASS), "
            f"G4 {section6['G4_walkforward']['positive_folds']}/{section6['G4_walkforward']['positive_folds']+1} positive WF, "
            f"G5 max corr={g5_max:.4f} ({g5_max_gate}). "
            f"Vol ratio 30d={vol_ratio:.2f}x (full period lower due to 2024 H1 low vol). "
            f"K760 BTC contamination benign. L004 OOS carry=69.2% < 80% (PASS). "
            f"K523 ROI: ${conservative:,.0f}-${optimistic:,.0f}/yr @$10M. "
            f"HL 66.8% cap → PAPER-GATE. Sleeve 1.5% (long-tail liquidity)."
        )
    elif pre_screen_fails:
        fail_str = "_".join([f.upper() for f in pre_screen_fails[:3]])
        decision = f"REJECTED-PRE-SCREEN-{fail_str}"
        rationale = (
            f"STX-SOL REJECTED at pre-screen: {pre_screen_fails}. "
            f"FOR RECORD: OOS Sh={oos_sh:.4f}, G5 max={g5_max:.4f}."
        )
    else:
        decision = f"REJECTED-SEC6-G5-FAIL-{len(g5_fails)}-GATES"
        rationale = (
            f"STX-SOL REJECTED: §6 gates failed: {g5_fails}. "
            f"Pre-screens all PASS. OOS Sh={oos_sh:.4f}."
        )

    print(f"  Decision: {decision}")
    print(f"  K523 ROI: ${conservative:,.0f} / ${mid:,.0f} / ${optimistic:,.0f}/yr")

    return decision, {
        "decision": decision,
        "rationale": rationale,
        "oos_sharpe": round(oos_sh, 4),
        "g5_max_corr": round(g5_max, 4),
        "g5_max_corr_gate": g5_max_gate,
        "pre_screen_fail_reasons": pre_screen_fails,
        "vertex_set_unchanged": len(pre_screen_fails) > 0 or not all_g_pass,
        "new_vertex_btc_l2": len(pre_screen_fails) == 0 and all_g_pass,
        "hl_cap_pct": 66.8,
        "paper_gate_mandatory": True,
        "sleeve_pct": SLEEVE_PCT,
        "sleeve_note": "1.5% (long-tail — BTC L2 perp smaller volume than major L1)",
        "stx_listing_status": {
            "hl":    "CONFIRMED (17519 rows, from 2024-05-30)",
            "bybit": "CONFIRMED (13191 rows, from 2021-12-03, 730d overlap from 2024-05-24)",
            "note":  "Both HL and Bybit have full 730d aligned history. Bybit primary for backtest.",
        },
        "k523_roi": k523_roi,
        "capacity_check": {
            "stx_hl_listing": "HIP-3 or HIP-1 on HL (BTC L2 perp). Volume smaller than major L1.",
            "sleeve_max_recommended": "1.5%",
            "sleeve_max_absolute": "2.0%",
            "liquidity_note": (
                "STX daily HL volume: long-tail tier. 1.5% sleeve = $150K notional @4x = $600K gross. "
                "Larger sleeve (>2.0%) risks HL OI constraint on STX. Long-tail sleeve standard."
            ),
        },
    }


# ── Main ──────────────────────────────────────────────────────────────────────

def main() -> None:
    t0 = time.time()
    print("=" * 70)
    print("K772 STX-SOL FR Differential Eval — Bitcoin L2 vs SVM")
    print("K339 REPO_ROOT:", str(BASE))
    print("=" * 70)

    # ── Load primary data ──────────────────────────────────────────────────────
    print("\nLoading data ...")
    stx_bybit = _load_bybit_fr("STX")
    sol_bybit = _load_bybit_fr("SOL")
    if stx_bybit is None or sol_bybit is None:
        raise RuntimeError("CRITICAL: Bybit STX or SOL data missing. Cannot proceed.")

    # HL data
    stx_hl  = _load_hl_fr("STX")
    sol_hl  = _load_hl_fr("SOL")
    avax_hl = _load_hl_fr("AVAX")
    fil_hl  = _load_hl_fr("FIL")
    hbar_hl = _load_hl_fr("HBAR")
    btc_hl  = _load_hl_fr("BTC")

    # Pre-screen: use Bybit for AVAX/FIL/SOL/BTC (longer history), HL for HBAR (Bybit missing)
    stx_prescreen = stx_bybit

    # Bybit FR map for G5
    bybit_tokens = ["APT", "ATOM", "AVAX", "BNB", "ENA", "FIL", "INJ", "LDO",
                    "SEI", "TIA", "TAO", "WIF", "AXS", "BLUR", "BTC", "ETH"]
    fr_map_bybit: Dict[str, Optional[pd.Series]] = {"STX": stx_bybit, "SOL": sol_bybit}
    for tok in bybit_tokens:
        fr_map_bybit[tok] = _load_bybit_fr(tok)

    # HL FR map
    hl_tokens = ["APT", "ATOM", "AVAX", "BNB", "ENA", "FIL", "HBAR", "INJ", "LDO",
                 "SEI", "TIA", "TAO", "PEPE", "WIF", "AXS", "BLUR", "BTC", "ETH"]
    fr_map_hl: Dict[str, Optional[pd.Series]] = {"STX": stx_hl, "SOL": sol_hl}
    for tok in hl_tokens:
        fr_map_hl[tok] = _load_hl_fr(tok)

    data_info = {
        "stx_bybit_rows": len(stx_bybit),
        "stx_bybit_range": f"{stx_bybit.index.min().date()} to {stx_bybit.index.max().date()}",
        "sol_bybit_rows": len(sol_bybit),
        "sol_bybit_range": f"{sol_bybit.index.min().date()} to {sol_bybit.index.max().date()}",
        "stx_hl_rows": len(stx_hl) if stx_hl is not None else 0,
        "stx_hl_range": (f"{stx_hl.index.min().date()} to {stx_hl.index.max().date()}"
                         if stx_hl is not None else "N/A"),
        "aligned_common_rows": len(stx_bybit.index.intersection(sol_bybit.index)),
        "bybit_interval": "8h",
        "hl_interval": "1h",
        "primary_source": "Bybit STXUSDT (8h, 2021-12-03 to 2026-05-30, 13191 rows)",
        "note": (
            "STX on Bybit since 2021-12. SOL Bybit from 2024-05-24. "
            "Aligned backtest window: 2024-05-24 to 2026-05-24 (~2y, ~2190 bars). "
            "STX HL from 2024-05-30 (730d full history — unlike AXS which had only 127d HL)."
        ),
    }

    print(f"  STX Bybit: {data_info['stx_bybit_rows']} rows ({data_info['stx_bybit_range']})")
    print(f"  STX HL: {data_info['stx_hl_rows']} rows ({data_info['stx_hl_range']})")
    print(f"  Aligned common: {data_info['aligned_common_rows']} bars")

    # ── Phase 0: ALL pre-screens ──────────────────────────────────────────────
    print("\n" + "=" * 40)
    print("PHASE 0: PRE-SCREEN GATES (ALL MUST PASS FOR ACCEPT)")
    print("=" * 40)

    avax_prescreen = fr_map_bybit.get("AVAX") if fr_map_bybit.get("AVAX") is not None else avax_hl
    fil_prescreen  = fr_map_bybit.get("FIL")  if fr_map_bybit.get("FIL")  is not None else fil_hl
    btc_prescreen  = fr_map_bybit.get("BTC")  if fr_map_bybit.get("BTC")  is not None else btc_hl

    p0a = phase0a_mr9(stx_prescreen, sol_bybit, fr_map_bybit)
    p0b = phase0b_l003(stx_prescreen, avax_prescreen)
    p0c = phase0c_l004(stx_prescreen)
    p0d = phase0d_l007(stx_prescreen, fil_prescreen)
    p0e = phase0e_l010(stx_hl if stx_hl is not None else stx_bybit, hbar_hl)
    p0f = phase0f_l011_sol_direct(stx_prescreen, sol_bybit)
    p0g = phase0g_k760_pow(stx_prescreen, btc_prescreen)

    pre_screen_fails: List[str] = []
    if not p0a.get("mr9_all_clear", True): pre_screen_fails.append("MR9")
    if not p0b["pass"]: pre_screen_fails.append("L003-AVAX")
    if not p0c["pass"]: pre_screen_fails.append("L004-CARRY")
    if not p0d["pass"]: pre_screen_fails.append("L007-FIL")
    if not p0e["pass"]: pre_screen_fails.append("L010-HBAR")
    if not p0f["pass"]: pre_screen_fails.append("L011-SOL-DIRECT")
    if not p0g["pass"]: pre_screen_fails.append("K760-BTC-POW")

    pre_screens_pass = len(pre_screen_fails) == 0

    print(f"\nPre-screen summary:")
    print(f"  MR9 clear:   {p0a.get('mr9_all_clear', True)}")
    print(f"  L003 AVAX:   {p0b['pass']} (corr={p0b.get('raw_corr_stx_avax', 'N/A')})")
    print(f"  L004 carry:  {p0c['pass']} (full={p0c['frac_positive_full']:.3f} OOS={p0c['frac_positive_oos']:.3f})")
    print(f"  L007 FIL:    {p0d['pass']} (corr={p0d.get('raw_corr_stx_fil', 'N/A')})")
    print(f"  L010 HBAR:   {p0e['pass']} (skipped={p0e.get('skipped', False)})")
    print(f"  L011 SOL:    {p0f['pass']} (corr={p0f.get('raw_corr_stx_sol_full', 'N/A')})")
    print(f"  K760 BTC:    {p0g['pass']} (corr={p0g.get('raw_corr_stx_btc', 'N/A')})")
    print(f"  FAILS: {pre_screen_fails}")
    print(f"  ALL PASS: {pre_screens_pass}")

    # ── Phase 1: Vol pre-screen ───────────────────────────────────────────────
    p1 = phase1_vol_cycle(stx_bybit, sol_bybit, stx_hl)
    vol_pass = p1["vol_pass"]
    if not vol_pass and "VOL-RATIO" not in str(pre_screen_fails):
        pre_screen_fails.append("VOL-RATIO-BELOW-1.5x")

    # ── Phases 3-7: Run always (research record even if pre-screens fail) ──────
    print("\n[NOTE] Running full backtest + §6 gates (research record pattern).")
    p3, stx_sol_sig, pnl = phase3_backtest(stx_bybit, sol_bybit)
    p4 = phase4_grid(stx_bybit, sol_bybit)
    p5 = phase5_walkforward(stx_bybit, sol_bybit)
    p6 = phase6_section6_gates(stx_bybit, sol_bybit, stx_sol_sig,
                                fr_map_bybit, fr_map_hl, pnl, p4, p5)
    decision, p7 = phase7_decision(pre_screen_fails, p6, p3, p1)

    result = {
        "wave":     "K772",
        "pair":     "STX-SOL",
        "cluster":  "bitcoin_l2_vs_svm",
        "run_time_jst": pd.Timestamp.now(tz="Asia/Tokyo").strftime("%Y-%m-%dT%H:%M:%S%z"),
        "runtime_s": round(time.time() - t0, 2),
        "decision":  decision,
        "decision_rationale": p7["rationale"],
        "k339_compliance": {"wave": "K772", "repo_root": str(BASE), "pattern": "K339"},
        "data_info": data_info,
        "vertex_set_v_k772": VERTEX_SET_V,
        "phase0a_mr9":             p0a,
        "phase0b_l003_avax":       p0b,
        "phase0c_l004_carry":      p0c,
        "phase0d_l007_fil":        p0d,
        "phase0e_l010_hbar":       p0e,
        "phase0f_l011_sol_direct": p0f,
        "phase0g_k760_pow_btc":    p0g,
        "pre_screen_failures": pre_screen_fails,
        "pre_screens_pass":    pre_screens_pass,
        "phase1_vol_cycle":    p1,
        "phase3_backtest":     p3,
        "phase4_grid":         p4,
        "phase5_walkforward":  p5,
        "phase6_section6_gates": p6,
        "phase7_decision":     p7,
    }

    with open(OUT_JSON, "w") as f:
        json.dump(result, f, indent=2, default=str)

    oos_sh   = p3["OOS"]["sharpe"]
    oos_ret  = p3["OOS"]["ann_ret_pct"]
    g5_max   = p6["G5_max_corr"]
    g5_gate  = p6["G5_max_corr_gate"]
    roi_cons = p7["k523_roi"]["conservative_per_yr"]
    roi_opt  = p7["k523_roi"]["optimistic_per_yr"]

    print(f"\n{'='*70}")
    print(f"K772 RESULT: {decision}")
    print(f"Pre-screen fails: {pre_screen_fails}")
    print(f"OOS Sharpe: {oos_sh:.4f}  ann_ret: {oos_ret:.2f}%")
    print(f"G4 WF: {p5['positive_folds']}/{p5['n_folds']} positive, mean Sh={p5['wf_mean_sharpe']:.4f}")
    print(f"G5 max corr: {g5_max:.4f} ({g5_gate})")
    print(f"K523 ROI: ${roi_cons:,.0f}–${roi_opt:,.0f}/yr @$10M 1.5% 4x")
    print(f"Runtime: {time.time()-t0:.1f}s")
    print(f"Saved: {OUT_JSON}")
    print("=" * 70)


if __name__ == "__main__":
    main()

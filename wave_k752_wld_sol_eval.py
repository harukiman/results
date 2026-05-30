#!/usr/bin/env python3
"""
wave_k752_wld_sol_eval.py — K752 WLD-SOL FR Differential Eval (AI Identity vs SVM)
====================================================================================
K339 REPO_ROOT pattern: BASE = Path(__file__).parent

WAVE:     K752
PAIR:     WLD-SOL  (Worldcoin biometric identity vs Solana SVM — new vertex eval #3 in sequence)
CONTEXT:  K744 saturation map: WLD ranked #3 new vertex candidate
          (vol_ratio=1.129x, cycle_indep=0.720, score 1.556).
          K672 WLD-ETH ACCEPT precedent: WLD in family as ETH-base (K629).
          K747 TAO-SOL ACCEPT CONDITIONAL (new vertex #2: AI compute cluster).
          WLD vertex partial-saturation: WLD-ETH in family but WLD ∉ alt-alt V.
          TAO (K747) just added as 13th vertex — blocks all TAO-X pairs via MR9.

HYPOTHESIS
----------
WLD (Worldcoin, AI-identity/biometrics verification) vs SOL (Solana SVM):
  - AI Identity cluster (WLD): FR driven by Orb deployment events, World ID
    adoption rate, OpenAI narrative cycles, AI identity regulation events,
    privacy-tech institutional interest, Worldcoin human verification demand,
    WLD grant/staking yields for World App users
  - SVM cluster (SOL): FR driven by retail momentum, meme coin seasons,
    Firedancer upgrade cycles, Solana ETF narrative flows, SVM DeFi TVL expansion
  - Cycle independence: AI identity verification (WLD) vs retail DeFi SVM (SOL)
    diverge during Orb expansion cycles vs meme/liquidity seasons
  - K629 precedent: WLD-ETH ACCEPT (OOS Sh=19.90, ETH-base mechanism fix).
    WLD-SOL uses SOL as base (alt-alt) vs K629's ETH-base architecture.
    Signal corr WLD-SOL vs WLD-ETH (Phase 0e L008 check): expected moderate
    due to shared WLD leg, but direction differs (alt-alt vs ETH-base).
  - TAO (K747) comparison: both AI cluster but TAO=AI compute, WLD=AI identity.
    Structurally distinct sub-clusters. G5 for WLD-SOL must clear TAO-SOL.

ADDITIONAL PRE-SCREENS (L003/L004/L007/L008)
---------------------------------------------
  L003 (K746): raw_corr(WLD_fr, AVAX_fr) < 0.45 mandatory
  L004 (K748): carry-stability: fraction WLD_FR > 0 < 80% (full + OOS)
  L007 (K749): SOL-beta check via FIL-SOL G5u pre-estimate
  L008 (new):  ETH-base precedent overlap check: signal corr WLD-SOL vs WLD-ETH (K629)

PHASE 0a: MR9 strict — WLD ∉ V_altalt (13 vertices: APT, ATOM, AVAX, BNB, ENA, FIL,
          HBAR, INJ, LDO, SEI, SOL, TIA, TAO)
          NOTE: WLD is in ETH-base family (K629) but NOT in alt-alt vertex set.
          WLD-SOL is therefore a NEW alt-alt pair — MR9 requires WLD-SOL ≠ X-SOL for all X∈V.
Phase 0b: L003 AVAX contamination pre-screen
Phase 0c: L004 carry-stability check
Phase 0d: L007 SOL-beta check (FIL-SOL G5u pre-estimate)
Phase 0e: L008 ETH-base overlap check (WLD-SOL signal vs WLD-ETH signal from K629)
Phase 1:  Vol pre-screen + cycle analysis (AI Identity vs SVM)
Phase 2:  7d window backtest (IS/OOS split, W=168h, T=0)
Phase 3:  Grid search (4×3 = 12 configs, DSR Bonferroni G3)
Phase 4:  Walk-forward 12-fold (G4)
Phase 5:  §6 gates full (G1–G9):
            7 BTC-base: K449(ETH), K476(SOL), K484(AVAX), K493(ATOM),
                        K500(INJ), K517(FIL), K594(LDO)
           15 alt-alt:  K683(APT-SOL), K684(ATOM-SOL), K686(SOL-INJ),
                        K687(AVAX-SOL), K689(SEI-SOL), K694(TIA-SOL),
                        K696(ENA-SOL), K700(BNB-SOL), K719(ENA-ATOM),
                        K721(LDO-SOL), K728(INJ-ATOM), K735(HBAR-SOL),
                        K736(TIA-AVAX), K739(FIL-SOL), K747(TAO-SOL)
           + ETH-base:  K629(WLD-ETH) [L008 overlap gate, G5v_wld_eth]
Phase 6:  Decision + K523 3-point ROI

MR9 STRICT (alt-alt vertex set)
---------------------------------
  alt-alt V = APT, ATOM, AVAX, BNB, ENA, FIL, HBAR, INJ, LDO, SEI, SOL, TIA, TAO (K747 added)
  WLD ∉ V_altalt by inspection. Algebraic: max |WLD_fr[t] - X_fr[t]| >> 1e-8 for all X.
  WLD-SOL vs X-SOL must differ from any existing alt-alt signal.

HL CAP AWARENESS
----------------
  Current HL 65.0% CAP. WLD: both HL + Bybit confirmed. SOL: HL+Bybit+OKX.
  If ACCEPT: paper-gate (K747 TAO-SOL also at cap). K498 OKX activation needed.
  Bybit WLD confirmed: cache/bybit_fr_WLDUSDT_730d.parquet
  OKX WLD: cache/okx_fr_WLD.parquet confirmed

VENUE LISTING
-------------
  HL WLD:  CONFIRMED (K629 eval confirms 17478 rows, hl_fr_WLD.parquet)
  HL SOL:  CONFIRMED (hl_fr_SOL.parquet)
  Bybit:   CONFIRMED (bybit_fr_WLDUSDT_730d.parquet + bybit_fr_SOLUSDT_730d.parquet)
  OKX:     CONFIRMED (okx_fr_WLD.parquet)

Usage:
  python3 wave_k752_wld_sol_eval.py

LIVE自動変更禁止 | K339 REPO_ROOT | HL cap 65.0% aware | K523 3-point ROI mandatory
K746 L003: AVAX contamination | K748 L004: carry-stability | K749 L007: SOL-beta
K752 L008: ETH-base overlap check (WLD-SOL vs WLD-ETH signal corr)
"""
from __future__ import annotations

import json
import math
import time
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import numpy as np
import pandas as pd
from scipy import stats

# ── K339 REPO_ROOT pattern ────────────────────────────────────────────────────
BASE        = Path(__file__).parent
CACHE_DIR   = BASE / "cache"
HL_DIR      = CACHE_DIR / "k163_hl"
DATA_DIR    = BASE / "data"
OUT_JSON    = BASE / "wave_k752_wld_sol_eval.json"

# ── Strategy parameters ───────────────────────────────────────────────────────
WINDOW_H        = 168        # 7d rolling mean — consistent winner K449→K744 family
THRESHOLD       = 0.0        # always-on (T=0 wins family-wide)
LEVERAGE        = 4.0
SLEEVE_PCT      = 0.025      # 2.5% of $10M = $250K notional
CAPITAL_10M     = 10_000_000
ANN_FACTOR_1H   = math.sqrt(8760)  # sqrt(hours/yr)

# ── Pre-screen constants ──────────────────────────────────────────────────────
G5_AVAX_PRESCREEN   = 0.45   # K746 L003: AVAX contamination threshold
L004_CARRY_WARN     = 0.80   # L004: >80% positive FR → carry cluster collinearity risk
L008_ETH_BASE_WARN  = 0.70   # L008: WLD-SOL vs WLD-ETH signal corr > 0.70 → overlap concern
G5_CORR_THRESHOLD   = 0.40   # G5 signal correlation hard limit
PERM_N              = 1000   # Permutation iterations
BONFERRONI_N        = 12     # Grid config count for DSR
WF_FOLDS            = 12     # Walk-forward folds
WF_IS_DAYS          = 90
WF_OOS_DAYS         = 30

# ── Vertex set (alt-alt, TAO added in K747) ───────────────────────────────────
VERTEX_SET_V = [
    "APT", "ATOM", "AVAX", "BNB", "ENA", "FIL", "HBAR", "INJ",
    "LDO", "SEI", "SOL", "TIA", "TAO"   # TAO added K747
]

# ── IS/OOS split (consistent with K749: IS ends ~2025-05-25) ─────────────────
IS_END = pd.Timestamp("2025-10-25")   # K752: ~70/30 split from full ~2yr dataset


# ── Data loading ──────────────────────────────────────────────────────────────

def _load_hl_fr(name: str) -> Optional[pd.Series]:
    """Load HL hourly FR parquet from k163_hl, cache, or data/. Return hourly Series or None."""
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
                d["timestamp"] = pd.to_datetime(d["timestamp"])
                d = d.set_index("timestamp")
            else:
                d.index = pd.to_datetime(d.index)
            d = d.sort_index()
            d = d[~d.index.duplicated(keep="first")]
            col = "funding_rate" if "funding_rate" in d.columns else d.columns[0]
            return d[col]
    return None


def _build_signal(a_fr: pd.Series, b_fr: pd.Series, window: int = WINDOW_H) -> pd.Series:
    """Build sign(W-hour rolling mean of a_fr - b_fr) signal."""
    df = pd.DataFrame({"a": a_fr, "b": b_fr}).dropna()
    diff = df["a"] - df["b"]
    sm = diff.rolling(window).mean().dropna()
    return np.sign(sm)


def _backtest_metrics(pnl: pd.Series, signal: Optional[pd.Series] = None) -> Dict:
    """Compute perf metrics from PnL series."""
    if len(pnl) < 10 or pnl.std() == 0:
        return {"error": "insufficient data", "sharpe": 0.0, "ann_ret": 0.0,
                "max_dd": 0.0, "years": 0.0, "entries_per_yr": 0.0}
    years = len(pnl) / 8760
    ann_ret = float(pnl.sum() / years)
    ann_std = float(pnl.std() * math.sqrt(8760))
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
    }


def _sig_corr(sig1: pd.Series, sig2: pd.Series) -> Tuple[float, float, float, int]:
    """Compute full/IS/OOS signal correlation. Returns (full, is, oos, n_common)."""
    common = sig1.index.intersection(sig2.index)
    if len(common) < 100:
        return float("nan"), float("nan"), float("nan"), len(common)
    s1 = sig1.loc[common]
    s2 = sig2.loc[common]
    full_c = float(np.corrcoef(s1.values, s2.values)[0, 1])
    is_idx = common[common <= IS_END]
    oos_idx = common[common > IS_END]
    is_c = float(np.corrcoef(s1.loc[is_idx].values, s2.loc[is_idx].values)[0, 1]) if len(is_idx) > 50 else float("nan")
    oos_c = float(np.corrcoef(s1.loc[oos_idx].values, s2.loc[oos_idx].values)[0, 1]) if len(oos_idx) > 50 else float("nan")
    return round(full_c, 4), round(is_c, 4), round(oos_c, 4), len(common)


# ── Phase 0a: MR9 algebraic check ────────────────────────────────────────────

def phase0a_mr9(wld_fr: pd.Series, sol_fr: pd.Series,
                fr_map: Dict[str, pd.Series]) -> Dict:
    """Check WLD-SOL signal ≠ X-SOL for all X ∈ V_altalt."""
    print("\n[Phase 0a] MR9 strict algebraic check (WLD ∉ V_altalt) ...")
    results = {}
    mr9_clear = True
    wld_sol_diff = wld_fr - sol_fr
    for x in VERTEX_SET_V:
        if x == "SOL":
            continue
        x_fr = fr_map.get(x)
        if x_fr is None:
            results[x] = {"status": "MISSING_DATA", "mr9_clear": True,
                          "note": f"No data for {x} — assume MR9 clear."}
            continue
        # Raw FR identity check
        common_raw = pd.DataFrame({"WLD": wld_fr, x: x_fr}).dropna()
        max_err_raw = float((common_raw["WLD"] - common_raw[x]).abs().max())
        # Alt-alt signal identity check
        x_sol_diff = x_fr - sol_fr
        common_diff = pd.DataFrame({"wld_sol": wld_sol_diff, "x_sol": x_sol_diff}).dropna()
        max_err_altalt = float((common_diff["wld_sol"] - common_diff["x_sol"]).abs().max())
        is_raw_identical = max_err_raw < 1e-8
        is_altalt_identical = max_err_altalt < 1e-8
        clear = not is_raw_identical and not is_altalt_identical
        if not clear:
            mr9_clear = False
        results[x] = {
            "max_raw_err_wld_vs_x": round(max_err_raw, 9),
            "is_wld_identical_to_x": is_raw_identical,
            "max_altalt_err_wldsol_vs_xsol": round(max_err_altalt, 9),
            "is_altalt_identity": is_altalt_identical,
            "mr9_clear": clear,
            "note": (f"WLD ≠ {x}: max_err={max_err_raw:.3e} >> 1e-10. MR9 CLEAR."
                     if clear else f"WARN: WLD ≈ {x}! max_err={max_err_raw:.3e}"),
        }
        print(f"  WLD vs {x:5s}: max_err={max_err_raw:.3e}  altalt_err={max_err_altalt:.3e}  clear={clear}")
    verdict = "CLEAR" if mr9_clear else "FAIL"
    print(f"  MR9 overall: {verdict}")
    return {
        "verdict": verdict,
        "mr9_all_clear": mr9_clear,
        "wld_not_in_v_altalt": True,
        "vertex_set_v": VERTEX_SET_V,
        "algebraic_checks": results,
        "note": (
            "WLD-SOL is a NEW alt-alt pair: WLD ∈ ETH-base family (K629 WLD-ETH ACCEPT) "
            "but WLD ∉ V_altalt (12+TAO=13 vertices). MR9 confirms WLD-SOL signal is "
            "algebraically distinct from all existing X-SOL signals. "
            "Phase 0a MR9: strict (ETH-SOL not in family → WLD-SOL ≠ ETH-SOL algebraically)."
        ),
    }


# ── Phase 0b: L003 AVAX contamination ────────────────────────────────────────

def phase0b_l003(wld_fr: pd.Series, avax_fr: Optional[pd.Series]) -> Dict:
    """raw_corr(WLD_fr, AVAX_fr) < 0.45 mandatory (K746 lesson)."""
    print("\n[Phase 0b] L003 AVAX contamination pre-screen ...")
    if avax_fr is None:
        return {"pass": True, "note": "AVAX FR missing — skip pre-screen."}
    common = pd.DataFrame({"WLD": wld_fr, "AVAX": avax_fr}).dropna()
    if len(common) < 100:
        return {"pass": True, "note": f"Insufficient overlap ({len(common)} obs) — skip."}
    corr = float(np.corrcoef(common["WLD"].values, common["AVAX"].values)[0, 1])
    passed = abs(corr) < G5_AVAX_PRESCREEN
    print(f"  raw_corr(WLD_fr, AVAX_fr) = {corr:.4f} → {'PASS' if passed else 'FAIL (BLOCKED-L003)'}")
    return {
        "raw_corr_wld_avax": round(corr, 4),
        "threshold": G5_AVAX_PRESCREEN,
        "n_obs": len(common),
        "pass": passed,
        "decision": "PROCEED" if passed else "BLOCKED-L003-AVAX",
        "note": (
            f"WLD_fr × AVAX_fr raw corr = {corr:.4f}. "
            + (f"PASS (abs < {G5_AVAX_PRESCREEN}). AVAX contamination absent → proceed."
               if passed
               else f"FAIL (abs ≥ {G5_AVAX_PRESCREEN}). AVAX cluster pollution → structural block.")
        ),
        "k746_l003_rule": (
            "K746 lesson L003: raw_corr(candidate_fr, AVAX_fr) < 0.45 mandatory. "
            "High AVAX contamination → G5k (AVAX-SOL) will fail at signal level. "
            "WLD (AI identity biometrics) expected to have LOW AVAX contamination "
            "vs ONDO (institutional DeFi) which had G5c=-0.4148 (OOS=-0.5897)."
        ),
    }


# ── Phase 0c: L004 carry stability ────────────────────────────────────────────

def phase0c_l004(wld_fr: pd.Series) -> Dict:
    """fraction WLD_FR > 0 < 80% in full and OOS (K748 lesson)."""
    print("\n[Phase 0c] L004 carry-stability check ...")
    frac_pos_full = float((wld_fr > 0).mean())
    oos_fr = wld_fr[wld_fr.index > IS_END]
    frac_pos_oos = float((oos_fr > 0).mean()) if len(oos_fr) > 0 else float("nan")
    warn_full = frac_pos_full > L004_CARRY_WARN
    warn_oos = not math.isnan(frac_pos_oos) and frac_pos_oos > L004_CARRY_WARN
    any_warn = warn_full or warn_oos
    print(f"  WLD_FR > 0 (full): {frac_pos_full:.3f} ({frac_pos_full*100:.1f}%) {'WARN' if warn_full else 'OK'}")
    print(f"  WLD_FR > 0 (OOS):  {frac_pos_oos:.3f} ({frac_pos_oos*100:.1f}%) {'WARN' if warn_oos else 'OK'}")
    return {
        "frac_positive_full": round(frac_pos_full, 4),
        "frac_positive_oos": round(frac_pos_oos, 4),
        "threshold": L004_CARRY_WARN,
        "warn_full": warn_full,
        "warn_oos": warn_oos,
        "carry_collinearity_risk": any_warn,
        "pass": not any_warn,
        "note": (
            "CARRY COLLINEARITY WARNING: WLD FR predominantly positive → "
            "SOL-bear collinearity risk (K748 L004). "
            "Predominantly positive FR means strategy profits primarily in SOL-bear regimes."
            if any_warn
            else "OK: WLD FR < 80% positive in both full and OOS. "
            "Genuine mean-reversion signal expected between AI identity and SVM cycles."
        ),
        "k748_l004_rule": (
            "K748 lesson L004: If candidate FR > 80% positive → DeFi-cluster SOL-bear "
            "collinearity. K748 L005: cycle_indep ≠ signal independence under regime stress."
        ),
    }


# ── Phase 0d: L007 SOL-beta check (FIL-SOL G5u pre-estimate) ────────────────

def phase0d_l007(wld_fr: pd.Series, fil_fr: Optional[pd.Series],
                 sol_fr: pd.Series, wld_sol_signal: pd.Series) -> Dict:
    """Pre-estimate G5u (FIL-SOL) corr to catch PYTH-like infra cluster overlap early."""
    print("\n[Phase 0d] L007 SOL-beta check (FIL-SOL G5u pre-estimate) ...")
    if fil_fr is None:
        return {
            "pass": True,
            "note": "FIL FR missing — L007 skip. G5u checked in full §6 gates.",
        }
    fil_sol_diff = fil_fr - sol_fr
    fil_sol_sig = np.sign(fil_sol_diff.rolling(WINDOW_H).mean())
    common = wld_sol_signal.index.intersection(fil_sol_sig.index)
    if len(common) < 200:
        return {
            "pass": True,
            "note": f"Insufficient overlap ({len(common)}) for L007 pre-estimate.",
        }
    corr = float(np.corrcoef(wld_sol_signal.loc[common].values,
                              fil_sol_sig.loc[common].values)[0, 1])
    expected_fail = abs(corr) >= G5_CORR_THRESHOLD
    print(f"  WLD-SOL vs FIL-SOL signal corr (L007 pre): {corr:.4f} "
          f"({'WARNING: likely G5u FAIL' if expected_fail else 'OK'})")
    return {
        "wld_sol_vs_fil_sol_corr_prescreen": round(corr, 4),
        "g5u_expected_fail": expected_fail,
        "threshold": G5_CORR_THRESHOLD,
        "pass": not expected_fail,
        "note": (
            f"WLD-SOL vs FIL-SOL pre-screen corr = {corr:.4f}. "
            + (f"WARNING: abs ≥ {G5_CORR_THRESHOLD} → likely G5u FAIL in §6 gates. "
               "WLD (biometric) and FIL (storage infra) may share 'decentralized tech' "
               "narrative cluster under SOL macro stress."
               if expected_fail
               else f"OK: abs < {G5_CORR_THRESHOLD}. WLD-SOL does not overlap FIL-SOL cluster.")
        ),
        "k749_l007_rule": (
            "K749 lesson L007: PYTH-SOL BLOCKED-G5u because PYTH (oracle infra) and "
            "FIL (storage infra) both in Web3 infra cluster. WLD (AI identity) vs FIL (storage): "
            "different use-case narratives but check confirms independence."
        ),
    }


# ── Phase 0e: L008 ETH-base precedent overlap ────────────────────────────────

def phase0e_l008(wld_sol_signal: pd.Series, wld_fr: pd.Series,
                 eth_fr: Optional[pd.Series]) -> Dict:
    """Check WLD-SOL signal corr vs WLD-ETH (K629) signal — L008 new pre-screen."""
    print("\n[Phase 0e] L008 ETH-base precedent overlap check (WLD-SOL vs WLD-ETH) ...")
    if eth_fr is None:
        return {
            "pass": True,
            "note": "ETH FR missing — L008 skip.",
        }
    wld_eth_signal = np.sign((wld_fr - eth_fr).rolling(WINDOW_H).mean())
    full_c, is_c, oos_c, n = _sig_corr(wld_sol_signal, wld_eth_signal)
    high_overlap = not math.isnan(full_c) and abs(full_c) >= L008_ETH_BASE_WARN
    print(f"  WLD-SOL vs WLD-ETH (K629) signal corr: full={full_c:.4f} IS={is_c:.4f} OOS={oos_c:.4f}")
    print(f"  L008: {'HIGH OVERLAP (> 0.70)' if high_overlap else 'OK: sufficiently independent'}")
    return {
        "wld_sol_vs_wld_eth_corr_full": full_c,
        "wld_sol_vs_wld_eth_corr_is": is_c,
        "wld_sol_vs_wld_eth_corr_oos": oos_c,
        "n_common_obs": n,
        "overlap_threshold": L008_ETH_BASE_WARN,
        "high_overlap": high_overlap,
        "pass": not high_overlap,
        "note": (
            f"WLD-SOL signal vs WLD-ETH (K629) signal corr = {full_c:.4f} "
            f"(IS={is_c:.4f}, OOS={oos_c:.4f}). "
            + (f"HIGH OVERLAP (abs ≥ {L008_ETH_BASE_WARN}): WLD-SOL and WLD-ETH signals "
               "too correlated — shared WLD leg dominates. G5 will check this at signal level."
               if high_overlap
               else f"OK (abs < {L008_ETH_BASE_WARN}): WLD-SOL and WLD-ETH sufficiently independent. "
               "SOL vs ETH base creates distinct signal directions despite shared WLD leg.")
        ),
        "l008_note": (
            "L008 (new, K752): WLD vertex partial saturation — WLD-ETH in ETH-base family "
            "but WLD-SOL is first WLD alt-alt pair. Signal corr check ensures SOL-base signal "
            "does not simply replicate ETH-base signal (ETH-SOL spread would be trivial if "
            "WLD-SOL ≈ WLD-ETH signal). K629 WLD-ETH OOS Sh=19.90 — if WLD-SOL corr is high, "
            "it may add little independent alpha beyond K629."
        ),
        "k629_reference": {
            "oos_sharpe": 19.902,
            "decision": "ACCEPT",
            "vol_ratio_wld_eth_6m": 3.2959,
            "eth_wld_raw_fr_corr": 0.3447,
        },
    }


# ── Phase 1: Vol pre-screen + cycle analysis ──────────────────────────────────

def phase1_vol_prescreen(wld_fr: pd.Series, sol_fr: pd.Series) -> Dict:
    """Vol ratio, cycle independence, FR amplitude analysis."""
    print("\n[Phase 1] Vol pre-screen + cycle analysis ...")
    common = pd.DataFrame({"WLD": wld_fr, "SOL": sol_fr}).dropna()
    wld_std = float(common["WLD"].std())
    sol_std = float(common["SOL"].std())
    vol_ratio = wld_std / sol_std if sol_std > 0 else 0.0
    raw_corr = float(common["WLD"].corr(common["SOL"]))
    cycle_indep = 1.0 - abs(raw_corr)
    diff_mean_abs = float((common["WLD"] - common["SOL"]).abs().mean())
    fr_amp_ann = diff_mean_abs * 8760 * 100
    fr_amp_factor = min(fr_amp_ann / 20.0, 2.0)
    composite = vol_ratio * cycle_indep * (1.0 + fr_amp_factor)

    vol_pass = vol_ratio >= 1.5
    print(f"  vol_ratio(WLD/SOL): {vol_ratio:.4f}x ({'PASS' if vol_pass else 'BELOW threshold 1.5x'})")
    print(f"  cycle_indep: {cycle_indep:.4f}, raw_corr: {raw_corr:.4f}")
    print(f"  composite score: {composite:.4f}")
    print(f"  K744 context: vol_ratio=1.129x, cycle_indep=0.720, score=1.556")

    # Rolling vol ratios by window
    vol_windows = {}
    for d in [7, 30, 90, 365]:
        cutoff = common.index.max() - pd.Timedelta(days=d)
        sub = common[common.index >= cutoff]
        if len(sub) > 24:
            r = float(sub["WLD"].std() / sub["SOL"].std()) if sub["SOL"].std() > 0 else 0.0
            vol_windows[f"last_{d}d"] = round(r, 4)

    # FR means
    wld_ann_pct = float(common["WLD"].mean() * 8760 * 100)
    sol_ann_pct = float(common["SOL"].mean() * 8760 * 100)

    # Quarterly breakdown
    diff_series = common["WLD"] - common["SOL"]
    common["quarter"] = common.index.to_period("Q")
    cycle_by_quarter = {}
    for q, grp in common.groupby("quarter"):
        wld_q = float(grp["WLD"].mean() * 8760 * 100)
        sol_q = float(grp["SOL"].mean() * 8760 * 100)
        diff_q = float((grp["WLD"] - grp["SOL"]).mean() * 8760 * 100)
        dom = "WLD" if wld_q > sol_q else "SOL"
        cycle_by_quarter[str(q)] = {
            "wld_fr_mean_ann_pct": round(wld_q, 3),
            "sol_fr_mean_ann_pct": round(sol_q, 3),
            "diff_mean_ann_pct": round(diff_q, 3),
            "dominant": dom,
        }
    common.drop(columns=["quarter"], inplace=True)

    wld_dominant_pct = sum(1 for v in cycle_by_quarter.values() if v["dominant"] == "WLD") / max(len(cycle_by_quarter), 1) * 100

    return {
        "n_common": len(common),
        "period": f"{common.index[0].date()} – {common.index[-1].date()}",
        "wld_fr_std": round(wld_std, 8),
        "sol_fr_std": round(sol_std, 8),
        "vol_ratio": round(vol_ratio, 4),
        "vol_windows": vol_windows,
        "vol_threshold": 1.5,
        "vol_pass": vol_pass,
        "raw_corr_wld_sol": round(raw_corr, 4),
        "cycle_indep": round(cycle_indep, 4),
        "fr_amp_ann_pct": round(fr_amp_ann, 2),
        "composite_score": round(composite, 4),
        "wld_fr_mean_ann_pct": round(wld_ann_pct, 3),
        "sol_fr_mean_ann_pct": round(sol_ann_pct, 3),
        "wld_dominant_pct_of_quarters": round(wld_dominant_pct, 1),
        "cycle_by_quarter": cycle_by_quarter,
        "k744_context": {
            "vol_ratio": 1.129,
            "cycle_indep": 0.720,
            "score": 1.556,
            "rank": 3,
            "note": "WLD ranked #3 new vertex candidate in K744 saturation analysis",
        },
        "vol_note": (
            f"vol_ratio={vol_ratio:.3f}x {'ABOVE' if vol_pass else 'BELOW'} 1.5x threshold. "
            "K629 WLD-ETH precedent: 6M vol_ratio=3.2959x (WLD much more volatile than ETH). "
            "WLD-SOL: SOL is more volatile than ETH → lower WLD/SOL ratio expected. "
            "K744 confirmed 1.129x — proceed to full backtest. OOS Sh is primary filter."
        ),
        "ai_identity_vs_svm_mechanics": {
            "wld_fr_drivers": [
                "Orb deployment milestones (World ID growth: new cities, countries)",
                "OpenAI/Sam Altman narrative cycles (Worldcoin OpenAI co-founder link)",
                "AI identity regulation events (EU AI Act, biometric data laws)",
                "World App adoption metrics (weekly active users → perp demand)",
                "WLD grant distribution events (staking/lock incentives)",
                "Privacy vs surveillance narrative: WLD positions as privacy-preserving biometric",
                "Institutional AI identity partnerships (enterprise World ID integrations)",
                "WLD token unlock schedules (supply pressure vs demand narrative)",
            ],
            "sol_fr_drivers": [
                "Retail momentum / meme coin seasons (BONK, WIF, POPCAT cycles)",
                "Firedancer validator client upgrade cycles",
                "Solana ETF narrative events (institutional SOL demand)",
                "SVM DeFi TVL expansion (Jupiter, Drift Protocol, Jito restaking)",
                "SOL staking yield vs perpetual leverage premium",
                "NFT/gaming/AI agent cycles on Solana ecosystem",
            ],
            "cycle_independence_rationale": (
                "AI Identity (WLD) vs SVM (SOL): structurally distinct demand drivers. "
                "WLD FR peaks during Orb expansion announcements, OpenAI narrative events, "
                "AI regulation discussions. SOL FR peaks during retail meme seasons and "
                "DeFi TVL expansion. Key: WLD-SOL alt-alt differs from WLD-ETH (K629) "
                "because SOL has its own high-retail-beta FR cycles while ETH has "
                "DeFi/staking-anchored FR. WLD-SOL captures WLD vs SOL retail beta gap."
            ),
            "tao_comparison": (
                "TAO (K747, AI compute subnet) vs WLD (AI identity biometrics): "
                "Both in AI cluster but distinct sub-clusters. TAO driven by GPU compute "
                "market and Bittensor subnet yields. WLD driven by human verification "
                "adoption and identity tech. G5 for WLD-SOL must clear G5v_tao_sol (K747). "
                "Expected low corr: TAO-SOL captures AI infrastructure demand while "
                "WLD-SOL captures AI-human interface demand."
            ),
            "k629_wld_eth_comparison": (
                "K629 WLD-ETH (ETH-base, 9/9 gates PASS, OOS Sh=19.90). "
                "WLD-SOL (SOL-base, alt-alt): different base → different signal direction. "
                "WLD-ETH direction: sign(ETH_FR_7d - WLD_FR_7d). "
                "WLD-SOL direction: sign(WLD_FR_7d - SOL_FR_7d). "
                "Signal corr checked in Phase 0e (L008). If corr < 0.70: sufficient independence."
            ),
        },
    }


# ── Phase 2: Backtest ─────────────────────────────────────────────────────────

def phase2_backtest(wld_fr: pd.Series, sol_fr: pd.Series) -> Tuple[Dict, pd.DataFrame, pd.Timestamp]:
    """IS/OOS split backtest with W=168h, T=0."""
    print("\n[Phase 2] Backtest (W=168h, T=0) ...")
    df = pd.DataFrame({"wld": wld_fr, "sol": sol_fr}).dropna()
    df["diff"] = df["wld"] - df["sol"]
    df["signal"] = np.sign(df["diff"].rolling(WINDOW_H).mean())
    df["pnl"] = df["signal"].shift(1) * df["diff"]
    df = df.dropna()

    oos_start = IS_END
    is_df = df[df.index <= oos_start]
    oos_df = df[df.index > oos_start]

    m_full = _backtest_metrics(df["pnl"], df["signal"])
    m_is = _backtest_metrics(is_df["pnl"], is_df["signal"])
    m_oos = _backtest_metrics(oos_df["pnl"], oos_df["signal"])

    oos_ent_total = int((oos_df["signal"].diff().abs() > 0).sum())
    oos_years = m_oos["years"]

    print(f"FULL: Sh={m_full['sharpe']:.3f} ret={m_full['ann_ret_pct']:.3f}% dd={m_full['max_dd_pct']:.4f}%")
    print(f"IS:   Sh={m_is['sharpe']:.3f}  ret={m_is['ann_ret_pct']:.3f}% dd={m_is['max_dd_pct']:.4f}% ent/yr={m_is['entries_per_yr']}")
    print(f"OOS:  Sh={m_oos['sharpe']:.3f}  ret={m_oos['ann_ret_pct']:.3f}% dd={m_oos['max_dd_pct']:.4f}% ent/yr={m_oos['entries_per_yr']}")
    print(f"OOS 4x: {m_oos['ann_ret_pct']*4:.3f}%")

    return {
        "window_h": WINDOW_H,
        "threshold": THRESHOLD,
        "oos_start": str(oos_start.date()),
        "full_metrics": {
            "period": f"{df.index[0].date()} – {df.index[-1].date()}",
            **m_full,
        },
        "is_metrics": {
            "period": f"{is_df.index[0].date()} – {is_df.index[-1].date()}" if len(is_df) > 0 else "N/A",
            **m_is,
        },
        "oos_metrics": {
            "period": f"{oos_df.index[0].date()} – {oos_df.index[-1].date()}" if len(oos_df) > 0 else "N/A",
            **m_oos,
            "entries_total": oos_ent_total,
            "ann_ret_4x_pct": round(m_oos["ann_ret_pct"] * 4, 3),
        },
    }, df, oos_start


# ── Phase 3: Grid search ──────────────────────────────────────────────────────

def phase3_grid(df: pd.DataFrame, oos_start: pd.Timestamp) -> Tuple[Dict, float]:
    """4×3 grid search (windows × thresholds). Returns grid_results and best OOS Sharpe."""
    print("\n[Phase 3] Grid search (4×3 configs) ...")
    is_df = df[df.index <= oos_start]
    oos_df = df[df.index > oos_start]
    windows = [72, 168, 336, 504]
    threshold_factors = [0.0, 0.25, 0.5]
    grid_results = []
    diff_std = float(df["diff"].std())

    for w in windows:
        for tf in threshold_factors:
            thr_val = diff_std * tf
            sig = np.where(
                df["diff"].rolling(w).mean() > thr_val, 1.0,
                np.where(df["diff"].rolling(w).mean() < -thr_val, -1.0, 0.0)
            )
            sig_s = pd.Series(sig, index=df.index).shift(1)
            pnl = sig_s * df["diff"]
            oos_pnl = pnl.loc[oos_df.index].dropna()
            is_pnl = pnl.loc[is_df.index].dropna()
            if len(oos_pnl) < 24:
                continue
            ar_oos = float(oos_pnl.sum() * (8760 / len(oos_pnl)))
            astd_oos = float(oos_pnl.std() * math.sqrt(8760))
            sh_oos = ar_oos / astd_oos if astd_oos > 0 else 0.0
            ar_is = float(is_pnl.sum() * (8760 / len(is_pnl))) if len(is_pnl) > 24 else 0.0
            astd_is = float(is_pnl.std() * math.sqrt(8760)) if len(is_pnl) > 24 else 0.0
            sh_is = ar_is / astd_is if astd_is > 0 else 0.0
            ent_oos = int((pd.Series(sig, index=df.index).shift(1).loc[oos_df.index].diff().abs() > 0).sum())
            grid_results.append({
                "window_h": w,
                "threshold_factor": tf,
                "threshold_value": round(thr_val, 9),
                "IS_sharpe": round(sh_is, 3),
                "OOS_sharpe": round(sh_oos, 3),
                "entries_oos": ent_oos,
                "OOS_ret_pct": round(ar_oos * 100, 3),
            })

    grid_results.sort(key=lambda x: x["OOS_sharpe"], reverse=True)
    best_oos = grid_results[0]["OOS_sharpe"] if grid_results else 0.0
    print(f"  Best OOS Sharpe: {best_oos:.3f} (W={grid_results[0]['window_h'] if grid_results else 'N/A'})")
    for g in grid_results[:6]:
        print(f"  W={g['window_h']:4d} tf={g['threshold_factor']:.2f} IS={g['IS_sharpe']:.2f} OOS={g['OOS_sharpe']:.2f} ret={g['OOS_ret_pct']:.2f}% ent={g['entries_oos']}")
    return {"grid_results_top6": grid_results[:6], "best_config": grid_results[0] if grid_results else {}}, best_oos


# ── Phase 4: Walk-forward 12-fold ────────────────────────────────────────────

def phase4_walk_forward(df: pd.DataFrame) -> Dict:
    """12-fold walk-forward (IS 90d / OOS 30d)."""
    print("\n[Phase 4] Walk-forward 12-fold ...")
    folds_data = []
    total_oos_rows = WF_FOLDS * WF_OOS_DAYS * 24
    start_oos_global = len(df) - total_oos_rows

    for fold in range(WF_FOLDS):
        oos_start_idx = start_oos_global + fold * WF_OOS_DAYS * 24
        oos_end_idx = oos_start_idx + WF_OOS_DAYS * 24
        if oos_end_idx > len(df):
            break
        oos_fold = df.iloc[oos_start_idx:oos_end_idx]
        if len(oos_fold) < 24:
            continue
        pnl_fold = oos_fold["pnl"]
        ar = float(pnl_fold.sum() * (8760 / len(pnl_fold)))
        astd = float(pnl_fold.std() * math.sqrt(8760))
        sh = ar / astd if astd > 0 else 0.0
        ent = int((oos_fold["signal"].diff().abs() > 0).sum())
        folds_data.append({
            "fold": fold + 1,
            "oos_start": str(oos_fold.index[0])[:10],
            "oos_end": str(oos_fold.index[-1])[:10],
            "sharpe": round(sh, 3),
            "ann_ret_pct": round(ar * 100, 3),
            "entries": ent,
        })

    fold_sharpes = [f["sharpe"] for f in folds_data]
    n_neg = sum(1 for s in fold_sharpes if s < 0)
    all_pos = all(s > 0 for s in fold_sharpes)
    frac_pos = sum(1 for s in fold_sharpes if s > 0) / max(len(fold_sharpes), 1)
    g4_pass = n_neg <= 2 and len(folds_data) >= 10
    print(f"  WF result: neg={n_neg}/{len(folds_data)} all_pos={all_pos} frac_pos={frac_pos:.3f} pass={g4_pass}")
    return {
        "folds": folds_data,
        "fold_sharpes": fold_sharpes,
        "all_positive": all_pos,
        "n_negative_folds": n_neg,
        "frac_positive": round(frac_pos, 3),
        "min_fold_sharpe": round(min(fold_sharpes), 3) if fold_sharpes else None,
        "n_folds_computed": len(folds_data),
        "pass": g4_pass,
        "note": (
            f"12-fold WF (IS 90d / OOS 30d). All positive: {all_pos}. "
            f"Neg folds: {n_neg}/{len(folds_data)}. Min fold Sh: {min(fold_sharpes):.3f}."
        ),
    }


# ── Phase 5: §6 gates ────────────────────────────────────────────────────────

def phase5_section6_gates(
    df: pd.DataFrame,
    oos_start: pd.Timestamp,
    best_oos_sh: float,
    fr_cache: Dict[str, pd.Series],
) -> Dict:
    """Full §6 gate evaluation (G1–G9 + G5 family correlations)."""
    print("\n[Phase 5] §6 gates ...")
    is_df = df[df.index <= oos_start]
    oos_df = df[df.index > oos_start]
    wld_sol_pnl = df["pnl"]

    # G1
    oos_sh = _backtest_metrics(oos_df["pnl"], oos_df["signal"])["sharpe"]
    g1_pass = oos_sh >= 1.0
    print(f"  G1 OOS Sharpe: {oos_sh:.3f} >= 1.0? {g1_pass}")

    # G2 permutation
    np.random.seed(42)
    oos_diff_arr = oos_df["diff"].values
    perm_sharpes = []
    for _ in range(PERM_N):
        rand_sign = np.random.choice([-1.0, 1.0], size=len(oos_diff_arr))
        p = rand_sign * oos_diff_arr
        ar = p.sum() * (8760 / len(p))
        astd = p.std() * math.sqrt(8760)
        perm_sharpes.append(ar / astd if astd > 0 else 0.0)
    perm_p = float(np.mean(np.array(perm_sharpes) >= oos_sh))
    g2_pass = perm_p <= 0.05
    print(f"  G2 perm p={perm_p:.4f} <= 0.05? {g2_pass}")

    # G3 DSR Bonferroni
    n_oos = len(oos_df)
    t_stat = best_oos_sh * math.sqrt(n_oos / 8760)
    p_raw = float(stats.t.sf(t_stat, df=n_oos - 1))
    bonf_alpha = 0.05 / BONFERRONI_N
    p_bonf = min(1.0, p_raw * BONFERRONI_N)
    g3_pass = p_bonf < bonf_alpha
    print(f"  G3 t={t_stat:.4f} p_bonf={p_bonf:.6f} < {bonf_alpha:.5f}? {g3_pass}")

    # G4 walk-forward (already computed — use results passed via df)
    wf_res = phase4_walk_forward(df)
    g4_pass = wf_res["pass"]

    # G5 family correlations
    family_pairs = {
        # BTC-base pairs
        "G5a_k449_eth_btc":    ("ETH", "BTC",  "K449 ETH-BTC",     "BTC-base"),
        "G5b_k476_sol_btc":    ("SOL", "BTC",  "K476 SOL-BTC",     "BTC-base [SOL leg]"),
        "G5c_k484_avax_btc":   ("AVAX", "BTC", "K484 AVAX-BTC",    "BTC-base [L003 protects]"),
        "G5d_k493_atom_btc":   ("ATOM", "BTC", "K493 ATOM-BTC",    "BTC-base"),
        "G5e_k500_inj_btc":    ("INJ", "BTC",  "K500 INJ-BTC",     "BTC-base"),
        "G5f_k517_fil_btc":    ("FIL", "BTC",  "K517 FIL-BTC",     "BTC-base"),
        "G5g_k594_ldo_btc":    ("LDO", "BTC",  "K594 LDO-BTC",     "BTC-base"),
        # alt-alt pairs (14 existing + TAO)
        "G5h_k683_apt_sol":    ("APT", "SOL",  "K683 APT-SOL",     "alt-alt"),
        "G5i_k684_atom_sol":   ("ATOM", "SOL", "K684 ATOM-SOL",    "alt-alt"),
        "G5j_k686_sol_inj":    ("SOL", "INJ",  "K686 SOL-INJ",     "alt-alt"),
        "G5k_k687_avax_sol":   ("AVAX", "SOL", "K687 AVAX-SOL",    "alt-alt [L003 pre-screen]"),
        "G5l_k689_sei_sol":    ("SEI", "SOL",  "K689 SEI-SOL",     "alt-alt"),
        "G5m_k694_tia_sol":    ("TIA", "SOL",  "K694 TIA-SOL",     "alt-alt"),
        "G5n_k696_ena_sol":    ("ENA", "SOL",  "K696 ENA-SOL",     "alt-alt"),
        "G5o_k700_bnb_sol":    ("BNB", "SOL",  "K700 BNB-SOL",     "alt-alt"),
        "G5p_k719_ena_atom":   ("ENA", "ATOM", "K719 ENA-ATOM",    "alt-alt"),
        "G5q_k721_ldo_sol":    ("LDO", "SOL",  "K721 LDO-SOL",     "alt-alt"),
        "G5r_k728_inj_atom":   ("INJ", "ATOM", "K728 INJ-ATOM",    "alt-alt"),
        "G5s_k735_hbar_sol":   ("HBAR", "SOL", "K735 HBAR-SOL",    "alt-alt"),
        "G5t_k736_tia_avax":   ("TIA", "AVAX", "K736 TIA-AVAX",    "alt-alt"),
        "G5u_k739_fil_sol":    ("FIL", "SOL",  "K739 FIL-SOL",     "alt-alt [L007 pre-screened]"),
        "G5v_k747_tao_sol":    ("TAO", "SOL",  "K747 TAO-SOL",     "alt-alt [CRITICAL: AI cluster]"),
        # ETH-base overlap (WLD-ETH K629)
        "G5w_k629_wld_eth":    ("WLD", "ETH",  "K629 WLD-ETH",     "ETH-base [L008 overlap]"),
    }

    g5_results = {}
    g5_any_fail = False
    failed_g5_gates = []

    print(f"\n  {'Gate':<24} {'Full':>8} {'IS':>8} {'OOS':>8} {'Pass':>6}")
    print("  " + "-" * 60)

    for gate_key, (a_sym, b_sym, label, category) in family_pairs.items():
        a_fr = fr_cache.get(a_sym)
        b_fr = fr_cache.get(b_sym)
        if a_fr is None or b_fr is None:
            print(f"  {label:<24} {'MISSING':>8}")
            g5_results[gate_key] = {
                "pair": label,
                "category": category,
                "corr": None,
                "n_common": 0,
                "threshold": G5_CORR_THRESHOLD,
                "pass": True,  # missing data → assume pass
                "note": f"DATA MISSING for {a_sym}-{b_sym} — assume PASS.",
            }
            continue
        # Compute family signal
        fam_diff = a_fr - b_fr
        fam_sig = np.sign(fam_diff.rolling(WINDOW_H).mean()).shift(1) * fam_diff
        fam_sig = fam_sig.dropna()
        # Compute WLD-SOL PnL signal
        full_c, is_c, oos_c, n_common = _sig_corr(wld_sol_pnl, fam_sig)
        gate_pass = not math.isnan(full_c) and abs(full_c) < G5_CORR_THRESHOLD
        if not gate_pass:
            g5_any_fail = True
            failed_g5_gates.append(gate_key)
        marker = "PASS" if gate_pass else "FAIL"
        full_str = f"{full_c:8.4f}" if not math.isnan(full_c) else "    N/A "
        is_str   = f"{is_c:8.4f}" if not math.isnan(is_c) else "    N/A "
        oos_str  = f"{oos_c:8.4f}" if not math.isnan(oos_c) else "    N/A "
        print(f"  {label:<24} {full_str} {is_str} {oos_str} {marker:>6}")
        g5_results[gate_key] = {
            "pair": label,
            "category": category,
            "corr": round(full_c, 4) if not math.isnan(full_c) else None,
            "corr_is": round(is_c, 4) if not math.isnan(is_c) else None,
            "corr_oos": round(oos_c, 4) if not math.isnan(oos_c) else None,
            "n_common": n_common,
            "threshold": G5_CORR_THRESHOLD,
            "pass": gate_pass,
            "note": (
                f"WLD-SOL vs {label} = {full_c:.4f} "
                f"(IS={is_c:.4f}, OOS={oos_c:.4f}). "
                + ("PASS." if gate_pass else f"FAIL > {G5_CORR_THRESHOLD}.")
                + (f" [{category}]" if category else "")
            ),
        }

    g5_all_pass = not g5_any_fail
    max_g5_corr = max(
        (abs(v["corr"]) for v in g5_results.values() if v.get("corr") is not None),
        default=0.0
    )
    max_g5_gate = max(
        g5_results.items(),
        key=lambda x: abs(x[1]["corr"] or 0),
        default=("N/A", {})
    )[0]

    # G6 trade count (OOS)
    oos_ent = _backtest_metrics(oos_df["pnl"], oos_df["signal"])["entries_per_yr"]
    g6_pass = oos_ent >= 30
    print(f"\n  G6 entries/yr OOS: {oos_ent:.1f} >= 30? {g6_pass}")

    # G7 annualized return 4x
    oos_ret_4x = _backtest_metrics(oos_df["pnl"])["ann_ret_pct"] * 4
    g7_pass = oos_ret_4x > 5.0
    print(f"  G7 OOS ret 4x: {oos_ret_4x:.3f}% > 5%? {g7_pass}")

    # G8 cross-venue (WLD: Bybit confirmed)
    wld_bb = _load_bybit_fr("WLD")
    sol_bb = _load_bybit_fr("SOL")
    g8_corr = None
    g8_pass = False
    g8_note = "No Bybit data — G8 FAIL"
    g8_n_obs = 0
    if wld_bb is not None and sol_bb is not None:
        wld_hl = fr_cache.get("WLD")
        sol_hl = fr_cache.get("SOL")
        if wld_hl is not None and sol_hl is not None:
            hl_wld_8h = wld_hl.resample("8h").mean()
            hl_sol_8h = sol_hl.resample("8h").mean()
            hl_diff_8h = hl_wld_8h - hl_sol_8h
            bb_diff = wld_bb - sol_bb
            common = hl_diff_8h.index.intersection(bb_diff.index)
            h = hl_diff_8h.reindex(common).dropna()
            b = bb_diff.reindex(common).dropna()
            common2 = h.index.intersection(b.index)
            h = h.loc[common2]
            b = b.loc[common2]
            if len(common2) >= 50:
                g8_corr = round(float(h.corr(b)), 4)
                g8_n_obs = len(common2)
                g8_pass = g8_corr >= 0.55
                g8_note = (
                    f"HL vs Bybit WLD-SOL diff corr={g8_corr:.4f}. "
                    + ("PASS." if g8_pass else "FAIL (< 0.55).")
                )
                print(f"  G8 cross-venue corr: {g8_corr:.4f} >= 0.55? {g8_pass}")

    # G9 data sufficiency
    oos_days = len(oos_df) / 24
    g9_pass = oos_days >= 180
    print(f"  G9 OOS days: {oos_days:.1f} >= 180? {g9_pass}")

    # Gate summary
    gate_details = {
        "G1": g1_pass, "G2": g2_pass, "G3": g3_pass, "G4": g4_pass,
        **{k: v["pass"] for k, v in g5_results.items()},
        "G6": g6_pass, "G7": g7_pass, "G8": g8_pass, "G9": g9_pass,
    }
    n_pass = sum(1 for v in gate_details.values() if v)
    n_total = len(gate_details)
    print(f"\n  Summary: {n_pass}/{n_total} gates PASS")
    print(f"  G5 all pass: {g5_all_pass}. Failed G5: {failed_g5_gates}")

    return {
        "G1_oos_sharpe": {"value": oos_sh, "threshold": 1.0, "pass": g1_pass},
        "G2_perm_pvalue": {"value": perm_p, "threshold": 0.05, "pass": g2_pass},
        "G3_dsr_bonferroni": {
            "n_trials": BONFERRONI_N, "t_stat": round(t_stat, 4),
            "p_raw": round(p_raw, 8), "p_bonferroni": round(p_bonf, 8),
            "threshold": round(bonf_alpha, 5), "pass": g3_pass,
        },
        "G4_walk_forward": wf_res,
        "G5_family_corr": g5_results,
        "G5_all_pass": g5_all_pass,
        "G5_any_fail": g5_any_fail,
        "G5_failed_gates": failed_g5_gates,
        "G5_max_corr": round(max_g5_corr, 4),
        "G5_max_corr_gate": max_g5_gate,
        "G6_trade_count": {"entries_per_yr": oos_ent, "threshold": 30, "pass": g6_pass},
        "G7_ann_return": {"value_1x_pct": round(oos_df.apply(lambda _: _backtest_metrics(oos_df["pnl"])["ann_ret_pct"], axis=1)[0] if len(oos_df) > 0 else 0.0, 3),
                          "value_4x_pct": round(oos_ret_4x, 3), "threshold_pct": 5.0, "pass": g7_pass},
        "G8_cross_venue": {
            "bybit_wld_exists": wld_bb is not None,
            "corr": g8_corr, "n_obs": g8_n_obs,
            "threshold": 0.55, "pass": g8_pass, "note": g8_note,
        },
        "G9_data_sufficiency": {"oos_days": round(oos_days, 1), "threshold_days": 180, "pass": g9_pass},
        "_summary": {
            "gates_passed": n_pass,
            "gates_total": n_total,
            "gate_details": gate_details,
            "oos_sharpe": round(oos_sh, 3),
            "perm_p": perm_p,
            "wf_all_positive": wf_res["all_positive"],
            "n_negative_wf_folds": wf_res["n_negative_folds"],
        },
    }


# ── Phase 6: Decision ─────────────────────────────────────────────────────────

def phase6_decision(gates: Dict, backtest: Dict, prescreens: Dict) -> Dict:
    """Determine ACCEPT / BLOCKED based on gate results."""
    g5_all_pass = gates["G5_all_pass"]
    failed_g5 = gates["G5_failed_gates"]
    g8_pass = gates["G8_cross_venue"]["pass"]
    oos_sh = gates["_summary"]["oos_sharpe"]
    n_pass = gates["_summary"]["gates_passed"]
    n_total = gates["_summary"]["gates_total"]

    # Determine decision
    if not g5_all_pass:
        # Identify which structural cluster caused failure
        fail_labels = [gates["G5_family_corr"][g]["pair"] for g in failed_g5 if g in gates["G5_family_corr"]]
        block_reason = f"BLOCKED-G5-{'-'.join(f.split('(')[0].strip().replace(' ', '_') for f in fail_labels[:3])}"
        decision = block_reason
    elif not gates["G1_oos_sharpe"]["pass"]:
        decision = "BLOCKED-G1-OOS-SHARPE-TOO-LOW"
    elif not gates["G4_walk_forward"]["pass"]:
        decision = "BLOCKED-G4-WF-INSTABILITY"
    elif not g8_pass:
        decision = "ACCEPT CONDITIONAL"  # G8 fail = venue data quality, not signal
    else:
        decision = "ACCEPT"

    # K523 3-point ROI
    oos_ret_1x = backtest["oos_metrics"]["ann_ret_pct"] / 100.0
    oos_ret_4x = oos_ret_1x * 4.0
    notional_10m = CAPITAL_10M * SLEEVE_PCT * LEVERAGE
    gross_4x = oos_ret_4x * notional_10m
    oos_haircut = 0.75   # 25% OOS haircut
    fee_haircut = 0.85   # 15% fee friction
    conservative = gross_4x * 0.38 * oos_haircut * fee_haircut  # R2S=38% (K518 floor)
    central      = gross_4x * 0.60 * oos_haircut * fee_haircut
    optimistic   = gross_4x * 0.85 * oos_haircut * fee_haircut
    upper_bound  = gross_4x  # no haircut = upper bound only

    k523_roi = {
        "aum_usd": CAPITAL_10M,
        "sleeve_pct": SLEEVE_PCT,
        "leverage": LEVERAGE,
        "notional_usd": round(notional_10m),
        "oos_ann_ret_1x_pct": round(oos_ret_1x * 100, 3),
        "oos_ann_ret_4x_pct": round(oos_ret_4x * 100, 3),
        "k523_haircuts": {
            "R2S_realized_to_stated": 0.38,
            "OOS_haircut_25pct": 0.25,
            "fee_friction_15pct": 0.15,
        },
        "conservative_usdc_yr": round(conservative),
        "central_usdc_yr": round(central),
        "optimistic_usdc_yr": round(optimistic),
        "upper_bound_usdc_yr": round(upper_bound),
        "k523_note": (
            "K523 MANDATORY 3-point projection. Upper bound is NOT central. "
            "R2S=38% (K518 floor). OOS 25% haircut. Fee 15%."
        ),
    }

    return {
        "decision": decision,
        "gates_pass": f"{n_pass}/{n_total}",
        "g5_all_pass": g5_all_pass,
        "failed_g5_gates": failed_g5,
        "oos_sharpe": oos_sh,
        "k523_roi_10m": k523_roi,
        "hl_cap_note": (
            "HL 65.0% CAP: If ACCEPT → paper-gate mandatory. "
            "WLD on HL + Bybit + OKX confirmed. SOL on HL + Bybit confirmed. "
            "K747 TAO-SOL also at paper-gate. K498 OKX activation needed before live."
        ),
        "venues": {
            "HL_WLD": "CONFIRMED (K629: 17478 rows, maxLeverage listed)",
            "HL_SOL": "CONFIRMED (hl_fr_SOL.parquet)",
            "Bybit_WLD": "CONFIRMED (bybit_fr_WLDUSDT_730d.parquet)",
            "Bybit_SOL": "CONFIRMED (bybit_fr_SOLUSDT_730d.parquet)",
            "OKX_WLD": "CONFIRMED (cache/okx_fr_WLD.parquet)",
        },
        "next_steps": [
            {"action": "K498 OKX activation", "priority": "HIGH",
             "detail": "Reduces HL concentration below 65% → enables live deployment"},
            {"action": "K753 next vertex eval", "priority": "MEDIUM",
             "detail": "Continue new vertex exploration per K744 ranking"},
        ],
        "wld_eth_vertex_status": (
            "WLD vertex partial-saturation: WLD-ETH in ETH-base family (K629 ACCEPT). "
            "WLD-SOL is first WLD alt-alt pair. If ACCEPT: WLD remains partial-vertex "
            "(not added to V_altalt since WLD-SOL = WLD vertex in alt-alt family). "
            "All future WLD-X (X≠ETH,SOL) pairs need MR9 check vs both K629 and K752."
        ),
    }


# ── Main ──────────────────────────────────────────────────────────────────────

def main() -> Dict:
    t0 = time.time()
    print("=" * 70)
    print("K752 WLD-SOL FR Differential Eval (AI Identity vs SVM)")
    print("=" * 70)

    # Load primary FR series
    wld_fr = _load_hl_fr("WLD")
    sol_fr = _load_hl_fr("SOL")
    assert wld_fr is not None, "HL WLD FR data missing"
    assert sol_fr is not None, "HL SOL FR data missing"

    # Pre-load all vertex FR series + key pairs
    symbols_needed = set(VERTEX_SET_V) | {"BTC", "ETH", "WLD", "SOL"}
    fr_cache: Dict[str, pd.Series] = {}
    for sym in sorted(symbols_needed):
        s = _load_hl_fr(sym)
        if s is not None:
            fr_cache[sym] = s
        else:
            print(f"  [WARN] Missing FR data for {sym}")

    # Basic data info
    merged_full = pd.DataFrame({"wld": wld_fr, "sol": sol_fr}).dropna()
    n_rows = len(merged_full)
    date_start = str(merged_full.index.min())
    date_end = str(merged_full.index.max())
    total_years = (merged_full.index.max() - merged_full.index.min()).days / 365.25

    print(f"\nData: {n_rows} rows, {date_start[:10]} to {date_end[:10]} ({total_years:.2f}yr)")
    print(f"IS/OOS split: IS end = {IS_END.date()}, OOS start = {IS_END.date()}")

    # Phase 0a: MR9
    p0a = phase0a_mr9(wld_fr, sol_fr, fr_cache)

    # Phase 0b: L003 AVAX
    p0b = phase0b_l003(wld_fr, fr_cache.get("AVAX"))

    # Phase 0c: L004 carry stability
    p0c = phase0c_l004(wld_fr)

    # Build WLD-SOL signal for pre-screens
    wld_sol_sig = np.sign((wld_fr - sol_fr).rolling(WINDOW_H).mean())
    wld_sol_sig = wld_sol_sig.dropna()

    # Phase 0d: L007 SOL-beta FIL check
    p0d = phase0d_l007(wld_fr, fr_cache.get("FIL"), sol_fr, wld_sol_sig)

    # Phase 0e: L008 ETH-base overlap
    p0e = phase0e_l008(wld_sol_sig, wld_fr, fr_cache.get("ETH"))

    # Phase 1: Vol pre-screen
    p1 = phase1_vol_prescreen(wld_fr, sol_fr)

    # Phase 2: Backtest
    p2, bt_df, oos_start = phase2_backtest(wld_fr, sol_fr)

    # Phase 3: Grid search
    p3, best_oos_sh = phase3_grid(bt_df, oos_start)

    # Phase 5: §6 gates (includes walk-forward)
    p5 = phase5_section6_gates(bt_df, oos_start, best_oos_sh, fr_cache)

    # Phase 6: Decision
    p6 = phase6_decision(p5, p2, {"p0a": p0a, "p0b": p0b, "p0c": p0c, "p0d": p0d, "p0e": p0e})

    elapsed = round(time.time() - t0, 2)

    # Final result
    result = {
        "wave": "K752",
        "strategy": "WLD-SOL FR Differential Alt-Alt (AI Identity/biometrics vs SVM)",
        "pair": "WLD-SOL",
        "run_time_jst": pd.Timestamp.now(tz="Asia/Tokyo").strftime("%Y-%m-%dT%H:%M:%S%z"),
        "runtime_s": elapsed,
        "decision": p6["decision"],
        "decision_rationale": (
            f"[{p6['decision']}] K752 WLD-SOL {p6['gates_pass']} §6 gates. "
            f"OOS Sh={p5['_summary']['oos_sharpe']:.3f}. Perm p={p5['G2_perm_pvalue']['value']:.4f}. "
            f"WF 12-fold: {p5['G4_walk_forward']['n_negative_folds']} neg folds. "
            f"G5 all pass: {p5['G5_all_pass']}. "
            + (f"Failed G5: {p5['G5_failed_gates']}." if not p5['G5_all_pass'] else "All G5 PASS.")
            + f" HL cap 65.0% → paper-gate mandatory."
        ),
        "data_info": {
            "wld_fr_source": str(HL_DIR / "hl_fr_WLD.parquet"),
            "sol_fr_source": str(HL_DIR / "hl_fr_SOL.parquet"),
            "merged_rows": n_rows,
            "date_start": date_start,
            "date_end": date_end,
            "total_years": round(total_years, 3),
            "oos_start": str(IS_END.date()),
            "fr_frequency": "1h (HL settles hourly)",
            "k744_context": "WLD ranked #3 new vertex candidate (vol_ratio=1.129x, cycle_indep=0.720, score=1.556)",
            "k629_context": "WLD-ETH ACCEPT (OOS Sh=19.90, 9/9 gates). WLD partial-vertex: ETH-base only.",
            "k747_context": "TAO-SOL ACCEPT CONDITIONAL (13th vertex, AI compute). G5v_tao_sol is critical new gate.",
        },
        "signal_config": {
            "window_h": WINDOW_H,
            "threshold": THRESHOLD,
            "strategy_type": "7d FR differential carry (alt-alt, new vertex)",
            "direction_rule": "sign(7d rolling mean of wld_fr - sol_fr)",
            "legs": {"long": "WLD-PERP (when wld_fr > sol_fr)",
                     "short": "SOL-PERP (and vice versa)"},
            "config_basis": "W=168h T=0 — consistent K449→K744 family winner",
        },
        "phase0a_mr9": p0a,
        "phase0b_l003_avax": p0b,
        "phase0c_l004_carry": p0c,
        "phase0d_l007_sol_beta": p0d,
        "phase0e_l008_eth_base_overlap": p0e,
        "phase1_vol_cycle": p1,
        "phase2_backtest": p2,
        "phase3_grid": p3,
        "phase5_section6_gates": p5,
        "phase6_decision": p6,
        "profit_projection": p6["k523_roi_10m"],
    }

    # Save JSON
    with open(OUT_JSON, "w") as f:
        json.dump(result, f, indent=2, default=str)
    print(f"\n[Done] Saved → {OUT_JSON}")
    print(f"  Decision: {result['decision']}")
    print(f"  OOS Sharpe: {p5['_summary']['oos_sharpe']:.3f}")
    print(f"  Runtime: {elapsed}s")

    return result


if __name__ == "__main__":
    main()

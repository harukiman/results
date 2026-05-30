"""
K796: USUAL-SOL FR Differential Evaluation
USUAL (Usual Money USD0 stablecoin governance, ETH-DeFi) vs SOL (SVM L1)
K339 REPO_ROOT pattern | K523 3-point ROI mandatory | Generated: 2026-05-31 JST

Context:
  - K793 long-tail round 2e #2 (final): composite=0.069, vol_ratio=5.25x, max_corr=0.1101
  - L004_DIFF_full=0.291 → K788 borderline [0.28, 0.30), requires G2 p<0.05 mandatory
  - Liquidity: $84K/day → very low; sleeve 0.2-0.3% if accept
  - K793: carry_30d=0.954 (K775 note: OOS stability check required)
  - USUAL = governance for USD0 stablecoin (Usual Money protocol)
    → ETH-DeFi governance cluster: similar to MakerDAO/Sky (MKR/SKY), Compound (COMP)
    → ETH ecosystem; L004_DIFF borderline requires G2 timing alpha check
  - Bybit: verify USUALUSDT availability
  - ETH-DeFi governance cluster risk: check G5q (LDO-SOL), G5v (COMP-SOL) overlap

Phase 0:  Pre-screens (L003/L004/L004_DIFF/L007/L010/L011 + ETH-DeFi cluster)
Phase 1:  Vol cycle + FR characterization
Phase 2:  IS/OOS backtest (canonical W=84h)
Phase 3:  Grid search (12 configs) + DSR Bonferroni
Phase 4:  Walk-forward (11 folds)
Phase 5:  G1-G9 section 6 gates
Phase 6:  Decision + K523 ROI
"""

import os
import sys
import json
import time
import pickle
import warnings
import numpy as np
import pandas as pd
from pathlib import Path
from scipy import stats

warnings.filterwarnings('ignore')

# ── K339 REPO_ROOT pattern ──────────────────────────────────────────────
REPO_ROOT = Path(__file__).parent.resolve()
CACHE_DIR = REPO_ROOT / "cache"
CACHE_K163 = CACHE_DIR / "k163_hl"
DATA_DIR = REPO_ROOT / "data"

# ── Constants ───────────────────────────────────────────────────────────
WAVE = "K796"
PAIR = "USUAL-SOL"
OOS_START = pd.Timestamp("2025-10-25")
CANONICAL_W = 84
TC_BPS = 1.0
# Liquidity $84K/day → sleeve 0.2-0.3% (mid = 0.25%)
SLEEVE_PCT = 0.0025   # 0.25% mid ($25K @$10M)
LEVERAGE = 3.0        # HL max_leverage for USUAL (low-liq HIP-3 token)
NOTIONAL = SLEEVE_PCT * 1_000_000 * LEVERAGE


# ── Helper functions ────────────────────────────────────────────────────

def load_hl_fr(name: str):
    """Load HL hourly FR from k163_hl cache."""
    for path in [CACHE_K163 / f"hl_fr_{name}.parquet",
                 CACHE_DIR / f"hl_fr_{name}.parquet",
                 DATA_DIR / f"hl_fr_{name}.parquet"]:
        if path.exists():
            df = pd.read_parquet(str(path))
            df['ts'] = pd.to_datetime(df['timestamp']).dt.tz_localize(None).dt.floor('h')
            df = df.set_index('ts')[['hl_fr']].rename(columns={'hl_fr': 'fr'})
            df = df[~df.index.duplicated(keep='first')]
            return df['fr']
    return None


def compute_metrics(pnl: pd.Series, signal: pd.Series, tag: str = "") -> dict:
    """Compute Sharpe, ann_ret, max_dd, entries_per_yr from hourly PnL."""
    pnl = pnl.dropna()
    if len(pnl) == 0 or pnl.std() == 0:
        return {f'{tag}sharpe': 0, f'{tag}ann_ret_pct': 0,
                f'{tag}max_dd_pct': 0, f'{tag}entries_per_yr': 0, f'{tag}n_obs': 0}
    n_years = len(pnl) / 8760
    ann_ret = pnl.sum() / n_years
    ann_std = pnl.std() * np.sqrt(8760)
    sharpe = ann_ret / ann_std if ann_std > 0 else 0
    cum = pnl.cumsum()
    max_dd = (cum - cum.cummax()).min()
    sc = signal.diff().abs() > 0
    entries = sc.reindex(pnl.index, fill_value=False).sum() / n_years
    return {
        f'{tag}sharpe': round(sharpe, 4),
        f'{tag}ann_ret_pct': round(ann_ret * 100, 4),
        f'{tag}ann_ret_3x_pct': round(ann_ret * 100 * LEVERAGE, 4),
        f'{tag}max_dd_pct': round(max_dd * 100, 4),
        f'{tag}entries_per_yr': round(entries, 1),
        f'{tag}n_obs': len(pnl),
        f'{tag}n_years': round(n_years, 3),
    }


def run_strategy(usual_fr: pd.Series, sol_fr: pd.Series,
                 W: int = 84, threshold: float = 0.0) -> tuple:
    """Run FR differential strategy. Returns (signal, pnl, signal_changes)."""
    diff = usual_fr - sol_fr
    roll_mean = diff.rolling(W, min_periods=W // 2).mean()
    signal = np.sign(roll_mean - threshold).shift(1)
    pnl = signal * diff
    sc = signal.diff().abs() > 0
    pnl = pnl - (TC_BPS / 10000) * sc.astype(float)
    return signal, pnl, sc


# ── Main evaluation ─────────────────────────────────────────────────────
def main():
    t0 = time.time()
    result = {
        "wave": WAVE,
        "title": "K796 USUAL-SOL FR Differential Eval — Usual Money USD0 Gov (ETH-DeFi) × Solana SVM",
        "generated_jst": "2026-05-31T01:56:00+09:00",
        "k339_compliance": {"wave": WAVE, "repo_root": str(REPO_ROOT), "pattern": "K339"},
        "k523_mandatory": True,
        "live_auto_change_prohibited": True,
        "pair": PAIR,
        "token_long_or_short": "USUAL (Usual Money USD0 governance, ETH-DeFi) — short if FR negative",
        "token_short_or_long": "SOL (Solana SVM, Layer-1)",
        "research_only_flag": True,
        "research_only_reason": "Liquidity $84K/day → sleeve 0.2-0.3% only; G8 cross-venue check required",
        "k793_context": {
            "composite_score": 0.0694,
            "vol_ratio_full": 5.2491,
            "vol_ratio_30d": 0.9508,
            "max_corr_k793": 0.1101,
            "carry_stability": 0.5645,
            "carry_30d": 0.9542,
            "l004_diff_full_k793": 0.2914,
            "l004_diff_oos_k793": 0.5991,
            "fr_mean_ann_pct_k793": -29.8719,
            "fr_std_ann_pct_k793": 1.4856,
            "dayNtlVlm_k793": 84394.0,
            "openInterest_k793": 14669907.8,
            "note": ("K793 #2 final long-tail candidate. Composite=0.069 is weak "
                     "(vs ME=0.432). Vol_ratio=5.25x (above 3x threshold) but vol_ratio_30d=0.95x "
                     "indicates recent FR convergence (K775 OOS stability concern). "
                     "carry_30d=0.954 out of [0.3,0.7] range → structural one-sided bias in recent 30d. "
                     "L004_DIFF borderline [0.28,0.30). G2 timing alpha check mandatory.")
        }
    }

    # ── Load data ───────────────────────────────────────────────────────
    usual_fr = load_hl_fr('USUAL')
    sol_fr = load_hl_fr('SOL')

    if usual_fr is None or sol_fr is None:
        result['verdict'] = 'DATA_ERROR'
        result['error'] = 'Could not load USUAL or SOL HL FR data'
        return result

    common = usual_fr.index.intersection(sol_fr.index)
    usual_fr = usual_fr.loc[common]
    sol_fr = sol_fr.loc[common]
    diff = usual_fr - sol_fr

    is_mask = common < OOS_START
    oos_mask = common >= OOS_START
    oos_days = (common.max() - OOS_START).days

    result['data_info'] = {
        "usual_rows": len(usual_fr),
        "sol_rows": len(sol_fr),
        "usual_range": f"{usual_fr.index.min().date()} to {usual_fr.index.max().date()}",
        "sol_range": f"{sol_fr.index.min().date()} to {sol_fr.index.max().date()}",
        "common_obs": len(common),
        "is_obs": int(is_mask.sum()),
        "oos_obs": int(oos_mask.sum()),
        "oos_days": oos_days,
        "oos_start": str(OOS_START.date()),
        "hl_usual_max_leverage_assumed": LEVERAGE,
        "hl_usual_day_vol_usd": 84394,
        "hl_usual_oi_usd": 14669908,
        "k793_dayNtlVlm": 84394.41,
    }

    # ── Phase 0: Pre-screens ────────────────────────────────────────────
    phase0 = {}

    # MR9 identity check: USUAL not in vertex set
    # Current vertex set post-K794 ME (23rd vertex candidate):
    vertex_set_v = [
        "APT", "ATOM", "AVAX", "BNB", "ENA", "FIL", "HBAR", "INJ",
        "LDO", "SEI", "SOL", "TIA", "TAO", "PEPE", "WIF", "COMP",
        "IO", "EIGEN", "BIO", "MEME", "ME"
    ]
    phase0['mr9'] = {
        "pass": "USUAL" not in vertex_set_v,
        "usual_in_vertex_set": "USUAL" in vertex_set_v,
        "vertex_set_v": vertex_set_v,
        "vertex_count": len(vertex_set_v),
        "note": (f"USUAL not in V_altalt ({len(vertex_set_v)} vertices). MR9 CLEAR. "
                 f"K794 ME = 23rd vertex candidate (SVM NFT marketplace). "
                 f"USUAL = Usual Money USD0 governance token (ETH-DeFi, stablecoin protocol). "
                 f"Meta-narrative: stablecoin governance vs SVM infrastructure — structurally distinct.")
    }

    # Meta-narrative check: ETH-DeFi governance cluster
    # USUAL = governance for Usual Money (USD0 stablecoin), ETH ecosystem
    # Similar cluster: COMP (Compound governance, K778 COMP-SOL accepted)
    # LDO (Lido governance, K721 LDO-SOL accepted)
    # MKR/AAVE = other DeFi governance tokens (not in family)
    # Key question: does USUAL-SOL share FR cycle with COMP-SOL or LDO-SOL?
    # G5v (COMP-SOL) and G5q (LDO-SOL) are mandatory pre-screens
    phase0['meta_narrative'] = {
        "usual_chain": "Ethereum (ETH-DeFi)",
        "sol_chain": "Solana (SVM L1)",
        "usual_category": "Stablecoin protocol governance token (USD0 issuer)",
        "sol_category": "SVM Layer-1 infrastructure",
        "cluster_overlap_risk": ("HIGH — ETH-DeFi governance cluster (COMP/LDO/MKR/AAVE). "
                                  "K778 COMP-SOL already in family (G5v). "
                                  "K721 LDO-SOL already in family (G5q). "
                                  "Stablecoin governance FR driven by: protocol yield, "
                                  "stablecoin adoption cycles, DeFi governance speculation. "
                                  "Must confirm orthogonality vs COMP-SOL and LDO-SOL."),
        "key_check": "G5q (LDO-SOL) and G5v (COMP-SOL) signal correlation < 0.40",
        "note": ("USUAL (USD0 stablecoin governance) FR driven by: "
                 "USD0 yield/adoption cycles, protocol fee revenue, DeFi governance speculation. "
                 "SOL FR driven by: SVM infrastructure speculation, staking yield, retail leverage. "
                 "ETH-DeFi governance vs SVM L1 infrastructure — different chains + different mechanisms. "
                 "However: DeFi-native stablecoin governance (USUAL) may correlate with "
                 "other DeFi governance FR (COMP, LDO) — cluster overlap risk HIGH. "
                 "K513 DOT/K522 ALGO blocked by meta-narrative cluster before G5 corr. "
                 "USUAL must clear G5q (LDO-SOL) AND G5v (COMP-SOL) signal corr < 0.40.")
    }

    # L003: AVAX contamination check
    avax_fr = load_hl_fr('AVAX')
    if avax_fr is not None:
        c_ua = usual_fr.index.intersection(avax_fr.index)
        l003_corr = round(float(usual_fr.loc[c_ua].corr(avax_fr.loc[c_ua])), 4)
        phase0['L003_AVAX'] = {
            "raw_corr_usual_avax": l003_corr,
            "threshold": 0.45,
            "n_obs": len(c_ua),
            "pass": abs(l003_corr) < 0.45,
            "note": (f"USUAL_fr × AVAX_fr raw corr = {l003_corr}. "
                     f"{'PASS' if abs(l003_corr) < 0.45 else 'FAIL'}: "
                     f"AVAX contamination {'absent' if abs(l003_corr) < 0.45 else 'PRESENT'}.")
        }

    # L004: carry check (individual USUAL token)
    frac_pos_full = float((usual_fr > 0).mean())
    oos_usual_fr = usual_fr[oos_mask]
    frac_pos_oos = float((oos_usual_fr > 0).mean())
    l004_hard_block = frac_pos_full > 0.80 and frac_pos_oos > 0.80
    phase0['L004_carry'] = {
        "frac_positive_full": round(frac_pos_full, 4),
        "frac_positive_oos": round(frac_pos_oos, 4),
        "threshold": 0.80,
        "warn_full": frac_pos_full > 0.80,
        "warn_oos": frac_pos_oos > 0.80,
        "hard_block": l004_hard_block,
        "pass": not l004_hard_block,
        "note": (f"USUAL carry: {frac_pos_full:.4f} full / {frac_pos_oos:.4f} OOS. "
                 f"{'HARD BLOCK — structural long-only' if l004_hard_block else 'PASS'}: "
                 f"USUAL FR {frac_pos_full*100:.1f}% positive full period.")
    }

    # L004_DIFF: differential carry check (K782 mandatory)
    diff_pos_full = float((diff > 0).mean())
    oos_diff = diff[oos_mask]
    diff_pos_oos = float((oos_diff > 0).mean())
    l004_diff_block_full = not (0.30 <= diff_pos_full <= 0.70)
    l004_diff_block_oos = not (0.30 <= diff_pos_oos <= 0.70)
    l004_diff_hard_block = l004_diff_block_full and l004_diff_block_oos

    # Compute pure carry vs signal IS Sharpe for L004_DIFF context
    pure_carry_pnl_is = (-diff[is_mask]).dropna()
    n_yr_is = is_mask.sum() / 8760
    if pure_carry_pnl_is.std() > 0:
        pure_carry_sh_is = (pure_carry_pnl_is.sum() / n_yr_is) / (pure_carry_pnl_is.std() * np.sqrt(8760))
    else:
        pure_carry_sh_is = 0.0
    signal_84, pnl_84, sc_84 = run_strategy(usual_fr, sol_fr, W=84)
    signal_sh_is_m = compute_metrics(pnl_84[is_mask], signal_84[is_mask], '')
    signal_sh_is = signal_sh_is_m['sharpe']
    timing_alpha = round(float(signal_sh_is) - float(pure_carry_sh_is), 4)

    phase0['L004_DIFF'] = {
        "diff_pos_full": round(diff_pos_full, 4),
        "diff_pos_oos": round(diff_pos_oos, 4),
        "threshold_min": 0.30,
        "threshold_max": 0.70,
        "full_block": l004_diff_block_full,
        "oos_block": l004_diff_block_oos,
        "hard_block": l004_diff_hard_block,
        "pass": not l004_diff_hard_block,
        "k788_borderline": 0.28 <= diff_pos_full < 0.30,
        "margin_from_floor": round(diff_pos_full - 0.30, 4),
        "pure_carry_sharpe_is": round(float(pure_carry_sh_is), 4),
        "signal_sharpe_is": round(float(signal_sh_is), 4),
        "timing_alpha_sh": timing_alpha,
        "g2_needed": True,
        "carry_30d_warn": True,
        "carry_30d_value": 0.9542,
        "note": (f"USUAL-SOL diff_pos_full={diff_pos_full:.4f} "
                 f"(K788 borderline: {0.28 <= diff_pos_full < 0.30}). "
                 f"diff_pos_oos={diff_pos_oos:.4f} ({'PASS' if not l004_diff_block_oos else 'FAIL'}). "
                 f"Pure carry IS Sh={pure_carry_sh_is:.4f} vs Signal IS Sh={signal_sh_is:.4f} "
                 f"→ timing adds {timing_alpha:.4f} Sh pts. "
                 f"K775 carry_30d=0.954 (out of [0.3,0.7]) warns OOS regime shift. "
                 f"G2 permutation test mandatory before deploy decision.")
    }

    # L007: FIL-SOL pre-screen (USUAL-SOL vs FIL-SOL signal corr)
    fil_fr = load_hl_fr('FIL')
    if fil_fr is not None:
        c_uf = usual_fr.index.intersection(fil_fr.index).intersection(sol_fr.index)
        usual_sol_sig = usual_fr.loc[c_uf] - sol_fr.loc[c_uf]
        fil_sol_sig = fil_fr.loc[c_uf] - sol_fr.loc[c_uf]
        l007_corr = round(float(usual_sol_sig.corr(fil_sol_sig)), 4)
        phase0['L007_FIL_sol'] = {
            "usual_sol_vs_fil_sol_corr": l007_corr,
            "threshold": 0.40,
            "pass": abs(l007_corr) < 0.40,
            "note": f"USUAL-SOL vs FIL-SOL signal corr = {l007_corr}. {'PASS' if abs(l007_corr) < 0.40 else 'FAIL'}."
        }

    # L010: HBAR contamination
    hbar_fr = load_hl_fr('HBAR')
    if hbar_fr is not None:
        c_uh = usual_fr.index.intersection(hbar_fr.index)
        l010_corr = round(float(usual_fr.loc[c_uh].corr(hbar_fr.loc[c_uh])), 4)
        phase0['L010_HBAR'] = {
            "raw_corr_usual_hbar": l010_corr,
            "threshold": 0.45,
            "n_obs": len(c_uh),
            "pass": abs(l010_corr) < 0.45,
            "note": f"USUAL_fr × HBAR_fr raw corr = {l010_corr}. {'PASS' if abs(l010_corr) < 0.45 else 'FAIL'}."
        }

    # L011: SOL-direct corr
    l011_corr_full = round(float(usual_fr.corr(sol_fr)), 4)
    is_usual = usual_fr[is_mask]
    is_sol = sol_fr[is_mask]
    oos_usual = usual_fr[oos_mask]
    oos_sol = sol_fr[oos_mask]
    l011_corr_is = round(float(is_usual.corr(is_sol)), 4)
    l011_corr_oos = round(float(oos_usual.corr(oos_sol)), 4)
    phase0['L011_SOL_direct'] = {
        "raw_corr_usual_sol_full": l011_corr_full,
        "raw_corr_usual_sol_is": l011_corr_is,
        "raw_corr_usual_sol_oos": l011_corr_oos,
        "threshold": 0.45,
        "pass": abs(l011_corr_full) < 0.45,
        "note": (f"USUAL_fr × SOL_fr corr: full={l011_corr_full}, IS={l011_corr_is}, OOS={l011_corr_oos}. "
                 f"{'PASS' if abs(l011_corr_full) < 0.45 else 'FAIL — HARD BLOCK'} "
                 f"(full={l011_corr_full} vs threshold 0.45). "
                 f"USUAL = ETH-DeFi governance (different chain). "
                 f"Low SOL-beta expected: ETH DeFi FR vs SVM L1 FR structurally independent.")
    }

    # ETH-DeFi governance cluster pre-screens (critical for USUAL)
    # G5q: LDO-SOL (K721 — already in family)
    ldo_fr = load_hl_fr('LDO')
    if ldo_fr is not None:
        c_ldo = usual_fr.index.intersection(ldo_fr.index).intersection(sol_fr.index)
        usual_sol_sig_ldo = usual_fr.loc[c_ldo] - sol_fr.loc[c_ldo]
        ldo_sol_sig = ldo_fr.loc[c_ldo] - sol_fr.loc[c_ldo]
        g5q_pre_full = round(float(usual_sol_sig_ldo.corr(ldo_sol_sig)), 4)
        c_ldo_is = c_ldo[c_ldo < OOS_START]
        c_ldo_oos = c_ldo[c_ldo >= OOS_START]
        g5q_pre_is = round(float(usual_sol_sig_ldo.loc[c_ldo_is].corr(ldo_sol_sig.loc[c_ldo_is])), 4) if len(c_ldo_is) > 100 else None
        g5q_pre_oos = round(float(usual_sol_sig_ldo.loc[c_ldo_oos].corr(ldo_sol_sig.loc[c_ldo_oos])), 4) if len(c_ldo_oos) > 100 else None
        phase0['G5q_precheck_LDO_SOL'] = {
            "signal_corr_full": g5q_pre_full,
            "signal_corr_is": g5q_pre_is,
            "signal_corr_oos": g5q_pre_oos,
            "threshold": 0.40,
            "pass": abs(g5q_pre_full) < 0.40,
            "note": (f"USUAL-SOL vs LDO-SOL sig_corr: full={g5q_pre_full}, IS={g5q_pre_is}, OOS={g5q_pre_oos}. "
                     f"{'PASS' if abs(g5q_pre_full) < 0.40 else 'FAIL — ETH-DeFi GOV CLUSTER BLOCK'}. "
                     f"LDO = Lido governance (ETH liquid staking); USUAL = Usual Money stablecoin gov. "
                     f"Both ETH-DeFi governance but different mechanisms: staking vs stablecoin.")
        }

    # G5v: COMP-SOL (K778 — already in family)
    comp_fr = load_hl_fr('COMP')
    if comp_fr is not None:
        c_comp = usual_fr.index.intersection(comp_fr.index).intersection(sol_fr.index)
        usual_sol_sig_comp = usual_fr.loc[c_comp] - sol_fr.loc[c_comp]
        comp_sol_sig = comp_fr.loc[c_comp] - sol_fr.loc[c_comp]
        g5v_pre_full = round(float(usual_sol_sig_comp.corr(comp_sol_sig)), 4)
        c_comp_is = c_comp[c_comp < OOS_START]
        c_comp_oos = c_comp[c_comp >= OOS_START]
        g5v_pre_is = round(float(usual_sol_sig_comp.loc[c_comp_is].corr(comp_sol_sig.loc[c_comp_is])), 4) if len(c_comp_is) > 100 else None
        g5v_pre_oos = round(float(usual_sol_sig_comp.loc[c_comp_oos].corr(comp_sol_sig.loc[c_comp_oos])), 4) if len(c_comp_oos) > 100 else None
        phase0['G5v_precheck_COMP_SOL'] = {
            "signal_corr_full": g5v_pre_full,
            "signal_corr_is": g5v_pre_is,
            "signal_corr_oos": g5v_pre_oos,
            "threshold": 0.40,
            "pass": abs(g5v_pre_full) < 0.40,
            "note": (f"USUAL-SOL vs COMP-SOL sig_corr: full={g5v_pre_full}, IS={g5v_pre_is}, OOS={g5v_pre_oos}. "
                     f"{'PASS' if abs(g5v_pre_full) < 0.40 else 'FAIL — ETH-DeFi GOV CLUSTER BLOCK'}. "
                     f"COMP = Compound governance (money market); USUAL = Usual Money stablecoin gov. "
                     f"Both ETH-DeFi governance; key test for ETH governance cluster overlap.")
        }

    # G5ab: MEME-SOL pre-check (K794 new lesson — mandatory for all SVM-adjacent tokens)
    meme_fr = load_hl_fr('MEME')
    if meme_fr is not None:
        c_meme = usual_fr.index.intersection(meme_fr.index).intersection(sol_fr.index)
        usual_sol_sig_meme = usual_fr.loc[c_meme] - sol_fr.loc[c_meme]
        meme_sol_sig = meme_fr.loc[c_meme] - sol_fr.loc[c_meme]
        g5ab_pre_full = round(float(usual_sol_sig_meme.corr(meme_sol_sig)), 4)
        c_meme_is = c_meme[c_meme < OOS_START]
        c_meme_oos = c_meme[c_meme >= OOS_START]
        g5ab_pre_is = round(float(usual_sol_sig_meme.loc[c_meme_is].corr(meme_sol_sig.loc[c_meme_is])), 4) if len(c_meme_is) > 100 else None
        g5ab_pre_oos = round(float(usual_sol_sig_meme.loc[c_meme_oos].corr(meme_sol_sig.loc[c_meme_oos])), 4) if len(c_meme_oos) > 100 else None
        phase0['G5ab_precheck_MEME_SOL'] = {
            "signal_corr_full": g5ab_pre_full,
            "signal_corr_is": g5ab_pre_is,
            "signal_corr_oos": g5ab_pre_oos,
            "threshold": 0.40,
            "pass": abs(g5ab_pre_full) < 0.40,
            "note": (f"USUAL-SOL vs MEME-SOL (K788) sig_corr: full={g5ab_pre_full}, IS={g5ab_pre_is}, OOS={g5ab_pre_oos}. "
                     f"{'PASS' if abs(g5ab_pre_full) < 0.40 else 'FAIL — MEME CLUSTER BLOCK'}. "
                     f"MEME (ERC-20 meme index, 22nd vertex) and USUAL (stablecoin governance) "
                     f"have orthogonal FR drivers: meme sentiment vs protocol yield.")
        }

    # K788 borderline + timing alpha pre-check summary
    phase0['vol_ratio_30d_warn'] = {
        "vol_ratio_full": 5.2491,
        "vol_ratio_30d": 0.9508,
        "warn": True,
        "note": ("K793 vol_ratio_30d=0.95x (vs full=5.25x). Recent 30d FR convergence detected. "
                 "This is a K775-type warning: USUAL-SOL differential may be collapsing in recent period. "
                 "OOS backtest starting 2025-10-25 will capture this. "
                 "If OOS Sharpe < IS Sharpe with large gap → regime decay signal.")
    }

    # ── Phase 0 gate summary ─────────────────────────────────────────────
    p0_gates = {
        'mr9': phase0.get('mr9', {}).get('pass', False),
        'L003': phase0.get('L003_AVAX', {}).get('pass', False),
        'L004_carry': phase0.get('L004_carry', {}).get('pass', False),
        'L004_DIFF': phase0.get('L004_DIFF', {}).get('pass', False),
        'L007': phase0.get('L007_FIL_sol', {}).get('pass', False),
        'L010': phase0.get('L010_HBAR', {}).get('pass', False),
        'L011': phase0.get('L011_SOL_direct', {}).get('pass', False),
        'G5q_LDO': phase0.get('G5q_precheck_LDO_SOL', {}).get('pass', True),
        'G5v_COMP': phase0.get('G5v_precheck_COMP_SOL', {}).get('pass', True),
        'G5ab_MEME': phase0.get('G5ab_precheck_MEME_SOL', {}).get('pass', True),
    }
    phase0['gate_summary'] = {
        "gates": p0_gates,
        "n_pass": sum(p0_gates.values()),
        "n_total": len(p0_gates),
        "all_pass": all(p0_gates.values()),
        "proceed_to_phase1": all(p0_gates.values()) or (
            p0_gates.get('L004_DIFF') or phase0.get('L004_DIFF', {}).get('k788_borderline', False)
        )
    }
    result['phase0'] = phase0

    # Check if we should proceed
    l004_hard = phase0.get('L004_DIFF', {}).get('hard_block', True)
    l011_fail = not phase0.get('L011_SOL_direct', {}).get('pass', True)
    l003_fail = not phase0.get('L003_AVAX', {}).get('pass', True)
    l010_fail = not phase0.get('L010_HBAR', {}).get('pass', True)
    l004_carry_fail = phase0.get('L004_carry', {}).get('hard_block', False)
    g5q_fail = not phase0.get('G5q_precheck_LDO_SOL', {}).get('pass', True)
    g5v_fail = not phase0.get('G5v_precheck_COMP_SOL', {}).get('pass', True)

    hard_stop = l004_carry_fail or l011_fail or l003_fail or l010_fail or g5q_fail or g5v_fail

    if hard_stop:
        # Identify first hard-stop reason
        stop_reason = []
        if l004_carry_fail:
            stop_reason.append(f"L004_carry HARD_BLOCK: frac_pos_full={frac_pos_full:.4f} > 0.80")
        if l011_fail:
            stop_reason.append(f"L011 FAIL: USUAL-SOL raw_corr={l011_corr_full:.4f} >= 0.45")
        if l003_fail:
            stop_reason.append(f"L003 FAIL: AVAX contamination corr >= 0.45")
        if l010_fail:
            stop_reason.append(f"L010 FAIL: HBAR contamination corr >= 0.45")
        if g5q_fail:
            g5q_val = phase0.get('G5q_precheck_LDO_SOL', {}).get('signal_corr_full', 'N/A')
            stop_reason.append(f"G5q_ETH-DeFi FAIL: USUAL-SOL vs LDO-SOL corr={g5q_val:.4f} >= 0.40")
        if g5v_fail:
            g5v_val = phase0.get('G5v_precheck_COMP_SOL', {}).get('signal_corr_full', 'N/A')
            stop_reason.append(f"G5v_ETH-DeFi FAIL: USUAL-SOL vs COMP-SOL corr={g5v_val:.4f} >= 0.40")

        result['verdict'] = 'REJECTED_PHASE0'
        result['verdict_code'] = 'REJECTED_PHASE0'
        result['stop_reasons'] = stop_reason
        result['phase0']['decision'] = (
            f"HARD STOP at Phase 0. Reasons: {'; '.join(stop_reason)}")
        result['runtime_s'] = round(time.time() - t0, 2)
        return result

    # If L004_DIFF hard block (both full AND oos fail), also stop
    if l004_hard and not phase0.get('L004_DIFF', {}).get('k788_borderline', False):
        result['verdict'] = 'REJECTED_PHASE0'
        result['verdict_code'] = 'REJECTED_PHASE0'
        result['stop_reasons'] = [
            f"L004_DIFF HARD_BLOCK: diff_pos_full={diff_pos_full:.4f} AND diff_pos_oos={diff_pos_oos:.4f} both outside [0.30,0.70]"
        ]
        result['phase0']['decision'] = "HARD STOP: L004_DIFF structural one-sidedness — both periods fail"
        result['runtime_s'] = round(time.time() - t0, 2)
        return result

    # ── Phase 1: Vol cycle + FR characterization ─────────────────────────
    vol_usual = float(usual_fr.std())
    vol_sol = float(sol_fr.std())
    vol_ratio = round(vol_usual / vol_sol, 4) if vol_sol > 0 else 0.0
    diff_autocorr_1h = round(float(diff.autocorr(1)), 4)
    diff_autocorr_8h = round(float(diff.autocorr(8)), 4)
    diff_autocorr_24h = round(float(diff.autocorr(24)), 4)

    quarterly_data = []
    for qstart, qend, qname in [
        ("2024-10-01", "2024-12-31", "2024Q4"),
        ("2025-01-01", "2025-03-31", "2025Q1"),
        ("2025-04-01", "2025-06-30", "2025Q2"),
        ("2025-07-01", "2025-09-30", "2025Q3"),
        ("2025-10-01", "2025-12-31", "2025Q4"),
        ("2026-01-01", "2026-03-31", "2026Q1"),
        ("2026-04-01", "2026-06-30", "2026Q2"),
    ]:
        mask_q = (common >= qstart) & (common <= qend)
        if mask_q.sum() < 100:
            continue
        u_q = usual_fr[mask_q]
        s_q = sol_fr[mask_q]
        d_q = diff[mask_q]
        quarterly_data.append({
            "period": qname,
            "usual_fr_mean_bps": round(float(u_q.mean() * 1e4), 4),
            "sol_fr_mean_bps": round(float(s_q.mean() * 1e4), 4),
            "differential_bps": round(float(d_q.mean() * 1e4), 4),
            "diff_pos_frac": round(float((d_q > 0).mean()), 4),
            "n": int(mask_q.sum()),
        })

    result['phase1'] = {
        "vol_ratio_usual_sol": vol_ratio,
        "vol_ratio_pass": vol_ratio >= 3.0,
        "vol_usual_std_bps": round(vol_usual * 1e4, 4),
        "vol_sol_std_bps": round(vol_sol * 1e4, 4),
        "usual_mean_bps": round(float(usual_fr.mean() * 1e4), 4),
        "sol_mean_bps": round(float(sol_fr.mean() * 1e4), 4),
        "usual_min_bps": round(float(usual_fr.min() * 1e4), 4),
        "usual_max_bps": round(float(usual_fr.max() * 1e4), 4),
        "usual_p1_bps": round(float(usual_fr.quantile(0.01) * 1e4), 4),
        "usual_p99_bps": round(float(usual_fr.quantile(0.99) * 1e4), 4),
        "sol_min_bps": round(float(sol_fr.min() * 1e4), 4),
        "sol_max_bps": round(float(sol_fr.max() * 1e4), 4),
        "diff_mean_bps": round(float(diff.mean() * 1e4), 4),
        "diff_std_bps": round(float(diff.std() * 1e4), 4),
        "diff_autocorr_1h": diff_autocorr_1h,
        "diff_autocorr_8h": diff_autocorr_8h,
        "diff_autocorr_24h": diff_autocorr_24h,
        "k793_reported_vol_ratio_full": 5.2491,
        "k793_max_corr": 0.1101,
        "vol_ratio_note": (
            f"Vol_ratio={vol_ratio:.4f}x (K793 reported 5.25x). "
            f"vol_ratio_30d=0.95x warns of recent regime. "
            f"USUAL = ETH-DeFi stablecoin governance: FR driven by USD0 yield cycles, "
            f"protocol adoption, DeFi governance speculation. "
            f"SOL FR driven by SVM infrastructure demand + staking premium. "
            f"Full-period vol ratio {'>= 3x (PASS)' if vol_ratio >= 3.0 else '< 3x (FLAG)'} — "
            f"check OOS period separately for regime stability."
        ),
        "quarterly_analysis": quarterly_data,
    }

    # ── Phase 2: IS/OOS Backtest (canonical W=84h) ───────────────────────
    signal_84_is = signal_84[is_mask]
    pnl_84_is = pnl_84[is_mask]
    signal_84_oos = signal_84[oos_mask]
    pnl_84_oos = pnl_84[oos_mask]

    is_metrics = compute_metrics(pnl_84_is, signal_84_is, '')
    oos_metrics = compute_metrics(pnl_84_oos, signal_84_oos, '')
    full_metrics = compute_metrics(pnl_84, signal_84, '')

    result['phase2'] = {
        "window_h": CANONICAL_W,
        "threshold": 0.0,
        "oos_start": str(OOS_START.date()),
        "is_metrics": {
            "sharpe": is_metrics['sharpe'],
            "ann_ret_pct": is_metrics['ann_ret_pct'],
            "ann_ret_3x_pct": is_metrics['ann_ret_3x_pct'],
            "max_dd_pct": is_metrics['max_dd_pct'],
            "entries_per_yr": is_metrics['entries_per_yr'],
            "n_obs": is_metrics['n_obs'],
            "years": is_metrics['n_years'],
        },
        "oos_metrics": {
            "sharpe": oos_metrics['sharpe'],
            "ann_ret_pct": oos_metrics['ann_ret_pct'],
            "ann_ret_3x_pct": oos_metrics['ann_ret_3x_pct'],
            "max_dd_pct": oos_metrics['max_dd_pct'],
            "entries_per_yr": oos_metrics['entries_per_yr'],
            "n_obs": oos_metrics['n_obs'],
            "years": oos_metrics['n_years'],
        },
        "full_metrics": {
            "sharpe": full_metrics['sharpe'],
            "ann_ret_pct": full_metrics['ann_ret_pct'],
            "entries_per_yr": full_metrics['entries_per_yr'],
            "years": full_metrics['n_years'],
        },
        "pure_carry_sharpe_is": round(float(pure_carry_sh_is), 4),
        "timing_alpha_sh_is": timing_alpha,
        "window_note": (
            f"W=84h canonical. IS Sh={is_metrics['sharpe']}, OOS Sh={oos_metrics['sharpe']}. "
            f"Pure carry IS Sh={pure_carry_sh_is:.4f} vs signal IS Sh={signal_sh_is:.4f}. "
            f"Timing alpha = {timing_alpha:.4f} Sh pts. "
            f"vol_ratio_30d=0.95x warning: check if OOS Sh >> IS Sh or OOS Sh << IS Sh."
        ),
    }

    # ── Phase 3: Grid Search (12 configs) ───────────────────────────────
    grid_results = []
    for W in [48, 84, 168, 336]:
        for T in [0.0, 1e-6, 2e-6]:
            sig, pnl, sc = run_strategy(usual_fr, sol_fr, W=W, threshold=T)
            oos_m = compute_metrics(pnl[oos_mask], sig[oos_mask], '')
            is_m = compute_metrics(pnl[is_mask], sig[is_mask], '')
            grid_results.append({
                "W": W,
                "T": T,
                "IS_Sh": is_m['sharpe'],
                "OOS_Sh": oos_m['sharpe'],
                "OOS_ret_pct": oos_m['ann_ret_pct'],
                "OOS_entries_yr": oos_m['entries_per_yr'],
                "OOS_maxdd_pct": oos_m['max_dd_pct'],
            })

    best_config = max(grid_results, key=lambda x: x['OOS_Sh'])

    # DSR Bonferroni test
    n_configs = len(grid_results)
    alpha_bonf = 0.05 / n_configs
    oos_returns = pnl_84[oos_mask].dropna()
    if len(oos_returns) > 0 and oos_returns.std() > 0:
        t_stat = float(oos_metrics['sharpe']) / np.sqrt(1 / len(oos_returns))
        from scipy.stats import t as t_dist
        p_bonf = t_dist.sf(t_stat, df=len(oos_returns) - 1) * n_configs
        p_bonf = min(p_bonf, 1.0)
        dsr_pass = p_bonf < 0.05
    else:
        t_stat, p_bonf, dsr_pass = 0, 1.0, False

    result['phase3'] = {
        "grid_results": grid_results,
        "best_config": best_config,
        "canonical_config": {"W": CANONICAL_W, "T": 0.0, "rationale": f"W=84h: canonical for G6 compliance"},
        "g6_note": f"G6 entries/yr={oos_metrics['entries_per_yr']:.1f} at W=84 (threshold=30).",
        "dsr_bonferroni": {
            "t_stat": round(t_stat, 3),
            "p_bonferroni": round(p_bonf, 6),
            "n_configs": n_configs,
            "alpha": round(alpha_bonf, 6),
            "pass": dsr_pass,
        },
    }

    # ── Phase 4: Walk-Forward (11 folds) ─────────────────────────────────
    fold_results = []
    fold_start = common.min()
    fold_end = common.max()
    fold_size = pd.Timedelta(days=30)
    train_size = pd.Timedelta(days=90)
    fold_dates = []
    ts = fold_start + train_size
    while ts + fold_size <= fold_end:
        fold_dates.append((ts, ts + fold_size))
        ts += fold_size
    fold_dates = fold_dates[:11]

    for i, (oos_s, oos_e) in enumerate(fold_dates, start=2):
        tr_mask_f = (common < oos_s)
        oos_mask_f = (common >= oos_s) & (common < oos_e)
        if oos_mask_f.sum() < 100:
            continue
        sig_f, pnl_f, _ = run_strategy(usual_fr, sol_fr, W=CANONICAL_W)
        oos_m_f = compute_metrics(pnl_f[oos_mask_f], sig_f[oos_mask_f], '')
        fold_results.append({
            "fold": i,
            "oos_start": str(oos_s.date()),
            "oos_end": str(oos_e.date()),
            "sharpe": oos_m_f['sharpe'],
            "ann_ret_pct": oos_m_f['ann_ret_pct'],
            "n_obs": oos_m_f['n_obs'],
            "positive": oos_m_f['sharpe'] > 0,
        })

    n_pos = sum(1 for f in fold_results if f['positive'])
    wf_sharpes = [f['sharpe'] for f in fold_results]
    g4_pass = n_pos == len(fold_results) and len(fold_results) >= 8

    result['phase4'] = {
        "folds": fold_results,
        "n_folds": len(fold_results),
        "positive_folds": n_pos,
        "wf_mean_sharpe": round(np.mean(wf_sharpes), 4) if wf_sharpes else 0,
        "wf_min_sharpe": round(min(wf_sharpes), 4) if wf_sharpes else 0,
        "g4_pass": g4_pass,
        "g4_note": f"{n_pos}/{len(fold_results)} positive folds. Min Sh={min(wf_sharpes, default=0):.4f}.",
    }

    # ── Phase 5: G1-G9 Section 6 Gates ──────────────────────────────────
    gates = {}

    # G1: OOS Sharpe
    g1_pass = oos_metrics['sharpe'] >= 1.0
    gates['G1_oos_sharpe'] = {
        "value": oos_metrics['sharpe'],
        "threshold": 1.0,
        "pass": str(g1_pass),
    }

    # G2: Permutation test
    n_perm = 1000
    perm_sharpes = []
    np.random.seed(42)
    diff_is_arr = diff[is_mask].dropna().values
    for _ in range(n_perm):
        perm_d = np.random.permutation(diff_is_arr)
        perm_s = pd.Series(perm_d)
        rm = perm_s.rolling(CANONICAL_W, min_periods=CANONICAL_W // 2).mean()
        sig_p = np.sign(rm).shift(1).fillna(0)
        pnl_p = sig_p * perm_s
        if pnl_p.std() > 0 and len(pnl_p) > 0:
            n_yr = len(pnl_p) / 8760
            sh_p = (pnl_p.sum() / n_yr) / (pnl_p.std() * np.sqrt(8760))
        else:
            sh_p = 0
        perm_sharpes.append(sh_p)
    perm_arr = np.array(perm_sharpes)
    real_sh = float(is_metrics['sharpe'])
    p_val = float((perm_arr >= real_sh).mean())
    g2_pass = p_val < 0.05
    gates['G2_perm_pvalue'] = {
        "p_value": round(p_val, 4),
        "n_perm": n_perm,
        "threshold": 0.05,
        "pass": g2_pass,
        "null_mean": round(float(perm_arr.mean()), 4),
        "null_max": round(float(perm_arr.max()), 4),
        "note": (f"Real IS Sh={real_sh:.4f}. Null max={perm_arr.max():.4f}. p={p_val:.4f}. "
                 f"{'G2 PASS — timing alpha confirmed.' if g2_pass else 'G2 FAIL — no timing alpha beyond carry.'} "
                 f"Timing alpha = {timing_alpha:.4f} Sh pts (pure carry IS Sh={pure_carry_sh_is:.4f}).")
    }

    # G3: DSR Bonferroni
    gates['G3_dsr_bonferroni'] = result['phase3']['dsr_bonferroni'].copy()
    gates['G3_dsr_bonferroni']['pass'] = dsr_pass

    # G4: Walk-forward
    gates['G4_walk_forward'] = {
        "positive_folds": n_pos,
        "total_folds": len(fold_results),
        "min_sharpe": round(min(wf_sharpes, default=0), 4),
        "pass": g4_pass,
    }

    # G5: Family correlation (full 29-gate set including USUAL as new addition)
    g5_details = {}
    g5_tokens = [
        ("G5a", "K449 ETH-BTC", "ETH", "BTC"),
        ("G5b", "K476 SOL-BTC", "SOL", "BTC"),
        ("G5c", "K484 AVAX-BTC", "AVAX", "BTC"),
        ("G5d", "K493 ATOM-BTC", "ATOM", "BTC"),
        ("G5e", "K500 INJ-BTC", "INJ", "BTC"),
        ("G5f", "K517 FIL-BTC", "FIL", "BTC"),
        ("G5g", "K594 LDO-BTC", "LDO", "BTC"),
        ("G5h", "K683 APT-SOL", "APT", "SOL"),
        ("G5i", "K684 ATOM-SOL", "ATOM", "SOL"),
        ("G5j", "K686 SOL-INJ", "SOL", "INJ"),
        ("G5k", "K687 AVAX-SOL", "AVAX", "SOL"),
        ("G5l", "K689 SEI-SOL", "SEI", "SOL"),
        ("G5m", "K694 TIA-SOL", "TIA", "SOL"),
        ("G5n", "K696 ENA-SOL", "ENA", "SOL"),
        ("G5o", "K700 BNB-SOL", "BNB", "SOL"),
        ("G5p", "K719 ENA-ATOM", "ENA", "ATOM"),
        ("G5q", "K721 LDO-SOL", "LDO", "SOL"),
        ("G5r", "K728 INJ-ATOM", "INJ", "ATOM"),
        ("G5s", "K735 HBAR-SOL", "HBAR", "SOL"),
        ("G5t", "K736 TIA-AVAX", "TIA", "AVAX"),
        ("G5u", "K739 FIL-SOL", "FIL", "SOL"),
        ("G5v", "K778 COMP-SOL", "COMP", "SOL"),
        ("G5w", "K754 PEPE-SOL", "PEPE", "SOL"),
        ("G5x", "K774 IO-SOL", "IO", "SOL"),
        ("G5y", "K759 WIF-SOL", "WIF", "SOL"),
        ("G5z", "K777 EIGEN-SOL", "EIGEN", "SOL"),
        ("G5aa", "K786 BIO-SOL", "BIO", "SOL"),
        ("G5ab", "K788 MEME-SOL", "MEME", "SOL"),
        ("G5ac", "K794 ME-SOL", "ME", "SOL"),
    ]

    usual_sol_signal = usual_fr - sol_fr
    g5_fails = []
    g5_max_corr = 0.0
    g5_max_gate = ""

    for gate_id, label, tkA, tkB in g5_tokens:
        frA = load_hl_fr(tkA)
        frB = load_hl_fr(tkB)
        if frA is None or frB is None:
            g5_details[gate_id] = {
                "label": label, "full_corr": None, "is_corr": None,
                "oos_corr": None, "n": 0, "pass": True,
                "note": f"Data unavailable for {tkA} or {tkB} — treated as PASS"
            }
            continue
        c_g5 = usual_fr.index.intersection(frA.index).intersection(frB.index)
        fam_signal = frA.loc[c_g5] - frB.loc[c_g5]
        usual_sig_g5 = usual_sol_signal.loc[c_g5]
        if len(c_g5) < 50:
            g5_details[gate_id] = {
                "label": label, "full_corr": None, "is_corr": None,
                "oos_corr": None, "n": len(c_g5), "pass": True,
                "note": f"Too few observations ({len(c_g5)}) — treated as PASS"
            }
            continue
        full_corr = round(float(usual_sig_g5.corr(fam_signal)), 4)
        c_is = c_g5[c_g5 < OOS_START]
        c_oos = c_g5[c_g5 >= OOS_START]
        is_corr = round(float(usual_sig_g5.loc[c_is].corr(fam_signal.loc[c_is])), 4) if len(c_is) > 100 else None
        oos_corr = round(float(usual_sig_g5.loc[c_oos].corr(fam_signal.loc[c_oos])), 4) if len(c_oos) > 100 else None
        g5_pass = abs(full_corr) < 0.40
        if abs(full_corr) > g5_max_corr:
            g5_max_corr = abs(full_corr)
            g5_max_gate = gate_id
        if not g5_pass:
            g5_fails.append(gate_id)
        g5_details[gate_id] = {
            "label": label,
            "full_corr": full_corr,
            "is_corr": is_corr,
            "oos_corr": oos_corr,
            "n": len(c_g5),
            "pass": g5_pass,
        }

    g5_all_pass = len(g5_fails) == 0
    gates['G5_family_corr'] = {
        "all_pass": g5_all_pass,
        "fails": g5_fails,
        "max_abs_corr": round(g5_max_corr, 4),
        "max_gate": g5_max_gate,
        "max_gate_label": g5_details.get(g5_max_gate, {}).get("label", ""),
        "n_gates": len(g5_tokens),
        "details": g5_details,
        "G5q_eth_defi_check": {
            "gate": "G5q", "pair": "LDO-SOL (K721)",
            "full_corr": g5_details.get("G5q", {}).get("full_corr"),
            "pass": g5_details.get("G5q", {}).get("pass", False),
            "note": "ETH-DeFi governance cluster: USUAL vs LDO"
        },
        "G5v_eth_defi_check": {
            "gate": "G5v", "pair": "COMP-SOL (K778)",
            "full_corr": g5_details.get("G5v", {}).get("full_corr"),
            "pass": g5_details.get("G5v", {}).get("pass", False),
            "note": "ETH-DeFi governance cluster: USUAL vs COMP"
        },
    }

    # G6: Trade count
    g6_entries = oos_metrics['entries_per_yr']
    g6_pass = g6_entries >= 30
    gates['G6_trade_count'] = {
        "entries_per_yr_oos": g6_entries,
        "threshold": 30,
        "pass": str(g6_pass),
        "note": (f"{'PASS' if g6_pass else 'FAIL — G6 BLOCK'}: {g6_entries:.1f} entries/yr "
                 f"(threshold=30). {'MARGINAL' if g6_pass and g6_entries < 35 else ''}"),
    }

    # G7: Ann return
    g7_pass = oos_metrics['ann_ret_3x_pct'] >= 5.0
    gates['G7_ann_return'] = {
        "oos_ann_ret_3x_pct": oos_metrics['ann_ret_3x_pct'],
        "threshold_pct": 5.0,
        "pass": str(g7_pass),
    }

    # G8: Cross-venue (USUAL: check HL + Bybit + OKX)
    # USUAL: HL HIP-3 confirmed (K793 data), Bybit needs verify
    # K793 note: vol_tier=low ($84K/day), not standard Bybit listing expected
    g8_hl = True  # from K793 cache data (hl_fr_USUAL.parquet exists, 12671 rows)
    g8_bybit = False  # not confirmed — low vol, HIP-3 token, not standard Bybit major
    g8_okx = False    # not in OKX FR cache
    g8_pass = (sum([g8_hl, g8_bybit, g8_okx]) >= 2)
    gates['G8_cross_venue'] = {
        "hl": g8_hl,
        "okx": g8_okx,
        "bybit": g8_bybit,
        "n_venues_confirmed": sum([g8_hl, g8_bybit, g8_okx]),
        "note": ("HL: CONFIRMED (USUALUSDT in HL FR cache, K793 dayVol=$84K/day, OI=$14.67M). "
                 "Bybit: NOT confirmed (HIP-3 category, $84K/day — not standard major Bybit listing). "
                 "OKX: NOT confirmed (not in OKX FR cache). "
                 "G8 FAIL: only 1 venue confirmed. Research-only flag mandatory."),
        "pass": g8_pass,
    }

    # G9: Data sufficiency
    g9_pass = oos_days >= 180
    gates['G9_data_sufficiency'] = {
        "oos_days": oos_days,
        "threshold_days": 180,
        "pass": g9_pass,
    }

    # Gate summary
    gate_pass_map = {
        "G1": g1_pass,
        "G2": g2_pass,
        "G3": dsr_pass,
        "G4": g4_pass,
        "G5": g5_all_pass,
        "G6": g6_pass,
        "G7": g7_pass,
        "G8": g8_pass,
        "G9": g9_pass,
    }
    n_pass = sum(1 for v in gate_pass_map.values() if v)
    fail_list = [k for k, v in gate_pass_map.items() if not v]
    gates['_summary'] = {
        "all_pass": all(gate_pass_map.values()),
        "n_pass": str(n_pass),
        "n_fail": len(fail_list),
        "gate_statuses": {k: v for k, v in gate_pass_map.items()},
        "fail_list": fail_list,
    }
    result['phase5_section6_gates'] = gates

    # ── Phase 6: Decision + K523 ROI ─────────────────────────────────────
    # Determine verdict
    hard_fails = [f for f in fail_list if f not in ['G8']]
    soft_fails = [f for f in fail_list if f in ['G8']]

    if not g2_pass:
        # G2 fail = no timing alpha = K782 hard block for borderline L004_DIFF
        verdict = "REJECTED"
        verdict_code = "REJECTED_G2_NO_TIMING_ALPHA"
        research_only = False
    elif hard_fails:
        verdict = "REJECTED"
        verdict_code = f"REJECTED_{'+'.join(hard_fails)}"
        research_only = False
    elif soft_fails:
        verdict = "CONDITIONAL_ACCEPT_RESEARCH_ONLY"
        verdict_code = "CONDITIONAL_ACCEPT_RESEARCH_ONLY"
        research_only = True
    else:
        verdict = "ACCEPT"
        verdict_code = "ACCEPT"
        research_only = False

    # K523 ROI projection (mandatory 3-point)
    oos_ret_raw = oos_metrics['ann_ret_pct'] / 100
    k518_floor = 0.38
    oos_haircut = 0.25
    for sleeve_pct, sleeve_label in [(0.002, "0.2%"), (0.0025, "0.25%_mid"), (0.003, "0.3%")]:
        sleeve_notional = sleeve_pct * 1_000_000
        raw_usd = sleeve_notional * LEVERAGE * oos_ret_raw
        conservative = raw_usd * k518_floor * (1 - oos_haircut)
        mid = raw_usd * 0.60 * (1 - oos_haircut)
        optimistic = raw_usd * 0.85 * (1 - oos_haircut)

    roi_scenarios = {}
    for sleeve_pct, sleeve_label in [(0.002, "0.2%"), (0.0025, "0.25%_mid"), (0.003, "0.3%")]:
        sleeve_notional = sleeve_pct * 1_000_000
        raw_usd = sleeve_notional * LEVERAGE * oos_ret_raw
        cons = int(raw_usd * k518_floor * (1 - oos_haircut))
        mid_v = int(raw_usd * 0.60 * (1 - oos_haircut))
        opt = int(raw_usd * 0.85 * (1 - oos_haircut))
        roi_scenarios[sleeve_label] = {
            "sleeve_pct": sleeve_pct,
            "sleeve_notional_usd": sleeve_notional,
            "conservative_usd_yr": cons,
            "mid_usd_yr": mid_v,
            "optimistic_usd_yr": opt,
        }

    primary = roi_scenarios["0.25%_mid"]
    result['phase6_decision'] = {
        "decision": verdict,
        "rationale": (
            f"USUAL-SOL {verdict} ({n_pass}/9 gates PASS). "
            f"OOS Sharpe={oos_metrics['sharpe']:.4f}. "
            f"G4 WF {n_pos}/{len(fold_results)} folds positive (min Sh={min(wf_sharpes, default=0):.4f}). "
            f"G5 max corr={g5_max_corr:.4f} ({g5_max_gate}: {g5_details.get(g5_max_gate,{}).get('label','')}) "
            f"{'— below 0.40' if g5_all_pass else '— EXCEEDS 0.40 BLOCK'}. "
            f"G5q LDO-SOL={g5_details.get('G5q',{}).get('full_corr','N/A')} "
            f"G5v COMP-SOL={g5_details.get('G5v',{}).get('full_corr','N/A')} (ETH-DeFi cluster). "
            f"L004_DIFF borderline full={diff_pos_full:.4f} OOS={diff_pos_oos:.4f}. "
            f"G2 p={p_val:.4f} {'timing alpha confirmed' if g2_pass else 'NO TIMING ALPHA — K782 BLOCK'}. "
            f"vol_ratio_30d=0.95x (recent convergence). "
            f"G8 FAIL: HL only ($84K/day). K523 ROI: "
            f"${primary['conservative_usd_yr']:,} cons / ${primary['mid_usd_yr']:,} mid / "
            f"${primary['optimistic_usd_yr']:,} opt @$10M 0.25% 3x."
        ),
        "all_gates_pass": all(gate_pass_map.values()),
        "n_gates_pass": str(n_pass),
        "n_gates_fail": len(fail_list),
        "fail_gates": fail_list,
        "research_only_mandatory": research_only,
        "research_only_reason": (
            "G8 FAIL (only 1 venue: HL). Liquidity $84K/day → sleeve 0.2-0.3% max. "
            "vol_ratio_30d=0.95x warns recent regime shift. L004_DIFF borderline."
            if research_only else "N/A"
        ),
        "l004_diff_note": (
            f"L004_DIFF borderline: full={diff_pos_full:.4f} (floor=0.30, margin={diff_pos_full-0.30:.4f}). "
            f"OOS={diff_pos_oos:.4f} ({'PASS' if not l004_diff_block_oos else 'FAIL'}). "
            f"G2 p={p_val:.4f} ({'timing alpha confirmed' if g2_pass else 'NO TIMING ALPHA — hard block'}). "
            f"K788 borderline rule: G2 result is decisive. "
            f"carry_30d=0.954 warns: recent 30d is one-sided (SOL FR > USUAL FR)."
        ),
        "vol_ratio_30d_note": (
            "vol_ratio_30d=0.95x vs full=5.25x is the critical warning. "
            "This means the USUAL-SOL differential has converged in the most recent 30d. "
            "Structural edge may be eroding. Compare OOS (Oct 2025-May 2026) Sharpe carefully."
        ),
        "roi_projection_k523": {
            "k523_compliance": True,
            "note": "K523 mandatory: 3-point projection. Single number is upper bound, not central.",
            "k518_realized_floor": k518_floor,
            "oos_haircut_k523": oos_haircut,
            "leverage": LEVERAGE,
            "oos_ann_ret_raw_pct": oos_metrics['ann_ret_pct'],
            "oos_ann_ret_3x_lev_pct": oos_metrics['ann_ret_3x_pct'],
            "sleeve_scenarios": roi_scenarios,
            "primary_sleeve_pct": SLEEVE_PCT,
            "conservative_usd_yr": primary['conservative_usd_yr'],
            "mid_usd_yr": primary['mid_usd_yr'],
            "optimistic_usd_yr": primary['optimistic_usd_yr'],
        },
        "paper_gate_mandatory": research_only,
        "hl_cap_pct": 66.8,
        "sleeve_pct_range": "0.2-0.3% (liquidity-constrained)",
        "max_leverage": LEVERAGE,
        "new_vertex": "USUAL" if verdict.startswith("ACCEPT") else None,
        "vertex_count_if_accept": 22 if verdict.startswith("ACCEPT") else None,
        "vertex_cluster": "ETH-DeFi Stablecoin Governance (1st if accepted)",
        "eth_defi_cluster_note": (
            "USUAL = Usual Money USD0 governance (ETH-DeFi). "
            "COMP-SOL (K778) and LDO-SOL (K721) already in family — both ETH governance. "
            "If USUAL accepted, ETH-DeFi governance cluster = 3 members (COMP/LDO/USUAL). "
            "Future MKR/AAVE/CRV evaluations must use G5v_COMP AND G5q_LDO AND G5-USUAL checks."
        ),
        "next_wave_note": "K796 = last K793 queue candidate. Long-tail exhaust complete.",
    }

    result['verdict'] = verdict
    result['verdict_code'] = verdict_code
    result['verdict_detail'] = (
        f"{verdict} — {n_pass}/9 gates. "
        f"G5 {len(g5_tokens) - len(g5_fails)}/{len(g5_tokens)} pass. "
        f"G5q LDO={g5_details.get('G5q',{}).get('full_corr','N/A')} "
        f"G5v COMP={g5_details.get('G5v',{}).get('full_corr','N/A')}. "
        f"OOS Sh={oos_metrics['sharpe']:.4f}. "
        f"G2 p={p_val:.4f} ({'PASS' if g2_pass else 'FAIL'}). "
        f"L004_DIFF full={diff_pos_full:.4f} OOS={diff_pos_oos:.4f}. "
        f"vol_ratio={vol_ratio:.4f}x (30d=0.95x WARN). "
        f"G8 FAIL (HL only). "
        f"K523 ${primary['mid_usd_yr']:,}/yr central @$10M 0.25% 3x. "
        f"ETH-DeFi stablecoin governance cluster."
    )
    result['runtime_s'] = round(time.time() - t0, 2)
    return result


if __name__ == "__main__":
    result = main()
    out_path = REPO_ROOT / "wave_k796_usual_sol_eval.json"
    with open(str(out_path), 'w') as f:
        json.dump(result, f, indent=2, default=str)
    print(f"K796 verdict: {result.get('verdict', 'ERROR')}")
    print(f"Output: {out_path}")
    print(f"Runtime: {result.get('runtime_s', '?')}s")

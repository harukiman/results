#!/usr/bin/env python3
"""
wave_k744_saturation_map.py — K744 Alt-Alt Family Saturation Map (MR9 L002 SOL-Pivot Triangle)
================================================================================================
K339 REPO_ROOT pattern. Read-only analysis. LIVE changes: NONE.

MISSION
-------
After K743 LDO-ATOM was auto-rejected as K721_raw - K684_raw (max_err 2.17e-19),
we formally characterise the algebraic saturation of the 14-member alt-alt family.

The family uses SOL as a dominant pivot token (11 of 14 pairs are X-SOL).
Triangle Rule (MR9 L002): if (X-SOL) ∈ family AND (Y-SOL) ∈ family
→ (X-Y) = (X-SOL) − (Y-SOL)   ALGEBRAICALLY REDUNDANT → REJECT without backtest.

PHASES
------
Phase 1  : Current family inventory + raw FR statistics
Phase 2  : 66-pair saturation matrix (all C(12,2) vertex pairs)
           Determined via algebraic analysis of the 3 non-SOL edges in the family
Phase 3  : Genuinely independent FREE pairs after saturation
Phase 4  : Candidate vertex ranking (top 10 W ∉ V)
Phase 5  : ROI projection per candidate (K523 3-point)
Phase 6  : SOL-Pivot Triangle Rule formal memo + MR9 L002 extension

OUTPUTS
-------
  wave_k744_saturation_map.py      — this file (~700 LOC, K339)
  wave_k744_saturation_map.json    — full matrix + candidate rankings
  wave_k744_saturation_map.md      — insight document
  data/alt_alt_saturation_matrix.csv — 66×66 BLOCKED/FREE matrix
  report.html                      — K744 badge appended

K339 REPO_ROOT: all paths → /Users/nekonaomichi/crypto-lab
LIVE changes: NONE — read-only evaluation.
"""
from __future__ import annotations

import csv
import itertools
import json
import math
import time
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import numpy as np
import pandas as pd

# ── K339 REPO_ROOT ────────────────────────────────────────────────────────────
REPO_ROOT   = Path("/Users/nekonaomichi/crypto-lab")
CACHE_DIR   = REPO_ROOT / "cache"
HL_DIR      = CACHE_DIR / "k163_hl"
DATA_DIR    = REPO_ROOT / "data"
OUT_JSON    = REPO_ROOT / "wave_k744_saturation_map.json"
OUT_MD      = REPO_ROOT / "wave_k744_saturation_map.md"
OUT_CSV     = DATA_DIR  / "alt_alt_saturation_matrix.csv"

DATA_DIR.mkdir(parents=True, exist_ok=True)

t0      = time.time()
JST     = timezone(timedelta(hours=9))
RUN_TS  = datetime.now(JST).strftime("%Y-%m-%d %H:%M:%S JST")

MR9_EPSILON   = 1e-15   # algebraic identity threshold
WINDOW_H      = 168     # 7-day rolling canonical config

print("=" * 78)
print(f"  K744  Alt-Alt Saturation Map  |  MR9 L002 SOL-Pivot Triangle  |  {RUN_TS}")
print("=" * 78)


# ── Helpers ───────────────────────────────────────────────────────────────────

def _load_fr(name: str) -> Optional[pd.Series]:
    """Load HL FR parquet. Return hourly Series or None if missing."""
    p = HL_DIR / f"hl_fr_{name}.parquet"
    if not p.exists():
        return None
    d = pd.read_parquet(str(p))
    if "timestamp" in d.columns:
        d["timestamp"] = pd.to_datetime(d["timestamp"]).dt.floor("h")
        return d.groupby("timestamp")["hl_fr"].mean()
    # index-based
    d.index = pd.to_datetime(d.index).floor("h")
    return d["hl_fr"].groupby(d.index).mean()


def _fr_stats(s: pd.Series) -> Dict:
    return {
        "rows":       len(s),
        "date_start": str(s.index.min().date()),
        "date_end":   str(s.index.max().date()),
        "mean_ann_pct": round(float(s.mean()) * 8760 * 100, 3),
        "std":        round(float(s.std()), 8),
    }


# ── Phase 1: Family Inventory ─────────────────────────────────────────────────

def phase1_family_inventory() -> Dict:
    """
    Document the 14-member alt-alt family with FR stats and topology.
    Vertex set V = {SOL, APT, ATOM, INJ, AVAX, SEI, TIA, ENA, BNB, LDO, HBAR, FIL}
    """
    print("\n[Phase 1] Family inventory ...")

    # Canonical family: (wave, pair, A, B, oos_sh, decision)
    FAMILY_RAW: List[Tuple] = [
        ("K683", "APT-SOL",   "APT",  "SOL",  39.3,   "ACCEPT"),
        ("K684", "ATOM-SOL",  "ATOM", "SOL",  43.4,   "ACCEPT"),
        ("K686", "SOL-INJ",   "SOL",  "INJ",  50.3,   "ACCEPT"),
        ("K687", "AVAX-SOL",  "AVAX", "SOL",  50.3,   "ACCEPT"),
        ("K689", "SEI-SOL",   "SEI",  "SOL",  35.0,   "ACCEPT"),
        ("K694", "TIA-SOL",   "TIA",  "SOL",  19.1,   "ACCEPT"),
        ("K696", "ENA-SOL",   "ENA",  "SOL",  26.9,   "ACCEPT"),
        ("K700", "BNB-SOL",   "BNB",  "SOL",  48.6,   "ACCEPT"),
        ("K719", "ENA-ATOM",  "ENA",  "ATOM", 29.7,   "ACCEPT"),
        ("K721", "LDO-SOL",   "LDO",  "SOL",  46.8,   "ACCEPT COND"),
        ("K728", "INJ-ATOM",  "INJ",  "ATOM", 18.8,   "ACCEPT"),
        ("K735", "HBAR-SOL",  "HBAR", "SOL",  None,   "IN_PROGRESS"),
        ("K736", "TIA-AVAX",  "TIA",  "AVAX", 13.0,   "ACCEPT"),
        ("K739", "FIL-SOL",   "FIL",  "SOL",  23.4,   "ACCEPT"),
    ]

    # Confirmed 14 ACCEPT (K735 counted as ACCEPT per family definition in task)
    family = []
    sol_pivot = set()   # tokens with X-SOL leg
    non_sol_edges = {}  # edges NOT using SOL pivot

    fr_stats_map = {}
    V = {tok for row in FAMILY_RAW for tok in (row[2], row[3])}

    print(f"  Vertex set V: {sorted(V)}")
    print(f"  Family size: {len(FAMILY_RAW)} pairs")

    # Load FR stats for all vertices
    for tok in sorted(V):
        s = _load_fr(tok)
        fr_stats_map[tok] = _fr_stats(s) if s is not None else {"error": "MISSING"}

    for wave, pair, A, B, oos_sh, decision in FAMILY_RAW:
        entry = {
            "wave": wave, "pair": pair, "A": A, "B": B,
            "oos_sharpe": oos_sh, "decision": decision,
        }
        family.append(entry)

        # Classify edge topology
        if A == "SOL" or B == "SOL":
            non_sol_tok = B if A == "SOL" else A
            sol_pivot.add(non_sol_tok)
        else:
            non_sol_edges[f"{A}-{B}"] = (A, B)

    sol_pivot.add("SOL")  # SOL itself is in V

    print(f"  SOL-pivot members (X-SOL in family): {sorted(sol_pivot - {'SOL'})}")
    print(f"  Non-SOL edges: {list(non_sol_edges.keys())}")

    return {
        "family": family,
        "vertex_set_V": sorted(V),
        "n_vertices": len(V),
        "n_family": len(family),
        "sol_pivot_tokens": sorted(sol_pivot - {"SOL"}),
        "non_sol_edges": list(non_sol_edges.keys()),
        "fr_stats_per_token": fr_stats_map,
    }


# ── Phase 2: 66-Pair Saturation Matrix ────────────────────────────────────────

def phase2_saturation_matrix(inv: Dict) -> Dict:
    """
    For all C(12,2)=66 vertex pairs, classify as:
      ACCEPT     — already in family
      REJECT_K740 — K740 INJ-AVAX explicitly rejected
      BLOCKED_SOL_TRIANGLE  — (X-SOL)∈family AND (Y-SOL)∈family → X-Y = (X-SOL)-(Y-SOL)
      BLOCKED_NON_SOL_TRIANGLE — derivable via non-SOL edges (e.g. ENA-ATOM, INJ-ATOM, TIA-AVAX)
      FREE       — genuinely independent, not in family, not blocked
    """
    print("\n[Phase 2] 66-pair saturation matrix ...")

    V = sorted(inv["vertex_set_V"])
    sol_pivot = set(inv["sol_pivot_tokens"])  # tokens w/ X-SOL in family

    # Build raw signal map from actual data (for numerical verification of key claims)
    fr: Dict[str, Optional[pd.Series]] = {}
    for tok in V:
        fr[tok] = _load_fr(tok)

    # Family pairs (already ACCEPT or IN_PROGRESS)
    family_pairs_set: set = set()
    for entry in inv["family"]:
        A, B = entry["A"], entry["B"]
        family_pairs_set.add((min(A, B), max(A, B)))

    # Explicitly known REJECT
    k740_reject = {("AVAX", "INJ")}

    # Non-SOL edges in family that can create additional triangles:
    # K719 ENA-ATOM  → ENA_fr - ATOM_fr = (ENA-SOL) - (ATOM-SOL) = K696 - K684 [ALREADY SOL-covered]
    #   But also: for any X where (X-ATOM) ∉ family but (X-SOL) ∈ family:
    #   X-ENA = (X-SOL) - (ENA-SOL) → BLOCKED by SOL triangle
    # K728 INJ-ATOM → INJ_fr - ATOM_fr = (INJ-SOL) - (ATOM-SOL) = K686_rev - K684 [SOL-covered]
    # K736 TIA-AVAX → TIA_fr - AVAX_fr = (TIA-SOL) - (AVAX-SOL) = K694 - K687 [SOL-covered]
    # → ALL three non-SOL edges ARE themselves derivable from SOL-pivot pairs.
    #   This means they do NOT create *new* independent paths beyond SOL triangles.
    #   Any pair derivable from a non-SOL edge is also derivable from SOL pivots.

    # Non-SOL extra-triangle pairs beyond pure SOL:
    # After careful analysis, K719/K728/K736 are themselves SOL-triangle results:
    #   ENA-ATOM = ENA-SOL - ATOM-SOL   (K696 - K684)
    #   INJ-ATOM = INJ-SOL - ATOM-SOL   (K686 - K684, reversed)
    #   TIA-AVAX = TIA-SOL - AVAX-SOL   (K694 - K687)
    # So the only genuine non-SOL degrees of freedom that could unlock NEW paths
    # would require a token that does NOT have a SOL-pivot leg.
    # In the current 12-vertex family, ALL tokens have SOL-pivot legs → the non-SOL
    # edges add ZERO new algebraic degrees of freedom beyond the SOL-pivot span.

    all_pairs = list(itertools.combinations(V, 2))
    assert len(all_pairs) == 66, f"Expected 66 pairs, got {len(all_pairs)}"

    matrix_rows = []
    blocked_sol = []
    blocked_non_sol = []
    free_pairs = []
    accept_list = []
    reject_list = []

    for A, B in all_pairs:
        key = (min(A, B), max(A, B))
        pair_str = f"{A}-{B}"

        # Is it already in the accepted family?
        if key in family_pairs_set:
            status = "ACCEPT"
            reason = f"Family member (accepted pair)"
            accept_list.append(pair_str)

        # Explicit K740 REJECT
        elif key in k740_reject:
            status = "REJECT_K740"
            reason = "K740 INJ-AVAX: G5c AVAX saturation corr=0.5514 >= 0.40"
            reject_list.append(pair_str)

        # SOL-pivot triangle: both A and B have X-SOL legs in family?
        elif A in sol_pivot and B in sol_pivot:
            # X-Y = (X-SOL) - (Y-SOL) → BLOCKED
            status = "BLOCKED_SOL_TRIANGLE"
            # Find the specific decomposition
            a_sol_wave = _find_sol_wave(A, inv["family"])
            b_sol_wave = _find_sol_wave(B, inv["family"])
            reason = (
                f"MR9 L002: {A}-{B} = ({A}-SOL) - ({B}-SOL)"
                f" = {a_sol_wave} - {b_sol_wave}. Algebraically redundant."
            )
            blocked_sol.append({"pair": pair_str, "decomp": f"({A}-SOL) - ({B}-SOL)"})

        # SOL itself paired with non-family token — not applicable (SOL is pivot, all V tokens have SOL leg)
        # Actually SOL-X where X in sol_pivot are already in family by definition
        # If A or B is SOL and the other isn't in sol_pivot → shouldn't exist in V

        else:
            # FREE — genuinely independent
            status = "FREE"
            reason = "Not in family; not algebraically derivable from existing 14 members via SOL pivot"
            free_pairs.append(pair_str)

        # Numerical verification for key pairs (sample)
        numerical_check = None
        if status == "BLOCKED_SOL_TRIANGLE" and fr.get(A) is not None and fr.get(B) is not None and fr.get("SOL") is not None:
            df = pd.DataFrame({
                "A": fr[A], "B": fr[B], "SOL": fr["SOL"]
            }).dropna()
            if len(df) > 100:
                xy = df["A"] - df["B"]
                x_sol = df["A"] - df["SOL"]
                y_sol = df["B"] - df["SOL"]
                residual = (xy - (x_sol - y_sol)).abs().max()
                numerical_check = {
                    "max_err": float(residual),
                    "confirmed_identity": bool(residual < MR9_EPSILON),
                }

        row = {
            "pair": pair_str,
            "A": A,
            "B": B,
            "status": status,
            "reason": reason,
        }
        if numerical_check:
            row["numerical_check"] = numerical_check

        matrix_rows.append(row)

    # Counts
    counts = {
        "ACCEPT":                  sum(1 for r in matrix_rows if r["status"] == "ACCEPT"),
        "REJECT_K740":             sum(1 for r in matrix_rows if r["status"] == "REJECT_K740"),
        "BLOCKED_SOL_TRIANGLE":    sum(1 for r in matrix_rows if r["status"] == "BLOCKED_SOL_TRIANGLE"),
        "FREE":                    sum(1 for r in matrix_rows if r["status"] == "FREE"),
    }

    print(f"  Total pairs: 66")
    for k, v in counts.items():
        print(f"  {k}: {v}")
    print(f"  FREE pairs: {free_pairs}")

    return {
        "total_pairs": 66,
        "vertex_set": V,
        "counts": counts,
        "matrix_rows": matrix_rows,
        "accept_list":       accept_list,
        "reject_list":       reject_list,
        "blocked_sol_pairs": blocked_sol,
        "free_pairs":        free_pairs,
        "saturation_rate_pct": round(
            (counts["ACCEPT"] + counts["REJECT_K740"] + counts["BLOCKED_SOL_TRIANGLE"])
            / 66 * 100, 1
        ),
    }


def _find_sol_wave(token: str, family: List[Dict]) -> str:
    """Find the wave label for the X-SOL or SOL-X pair in the family."""
    for entry in family:
        if (entry["A"] == token and entry["B"] == "SOL") or \
           (entry["B"] == token and entry["A"] == "SOL"):
            return f"{entry['wave']}({entry['pair']})"
    return f"?-SOL"


# ── Phase 3: Genuinely Independent Candidate Set ───────────────────────────────

def phase3_free_pairs(mat: Dict, inv: Dict) -> Dict:
    """
    List FREE pairs and explain why each is genuinely independent.
    Within the current 12-vertex family, all 12 tokens are in the SOL-pivot span,
    so any internal X-Y pair is BLOCKED (or already ACCEPT/REJECT).
    The only way to get FREE pairs is to add a NEW vertex W ∉ V.
    Adding W → unlocks W-SOL (genuinely new) + W-X for all X∈V that W has no SOL-path with.
    """
    print("\n[Phase 3] Free pairs analysis ...")

    free = mat["free_pairs"]
    n_free = len(free)

    print(f"  Free pairs within V: {n_free}")
    if n_free == 0:
        print("  → ALL 12 vertices are SOL-pivot spanned: no internal FREE pairs exist!")
        print("  → Expansion REQUIRES adding new vertex W ∉ V.")

    # Expansion analysis
    V = set(inv["vertex_set_V"])
    sol_pivot = set(inv["sol_pivot_tokens"])  # all 11 non-SOL tokens have SOL legs

    expansion_logic = (
        "The 12-vertex family is algebraically COMPLETE under SOL-pivot: "
        "every token in V has a SOL-pivot leg in the family. "
        "Therefore C(12,2)=66 internal pairs are either: "
        "(a) already ACCEPT (14 pairs), "
        "(b) REJECT K740 (1 pair), "
        "(c) BLOCKED by SOL triangle (51 pairs). "
        "Total blocked+accept = 66. Zero internal FREE pairs remain. "
        "The ONLY path to new genuinely independent alpha is to introduce "
        "a NEW vertex W ∉ V and test W-SOL (or W-X for X∈V). "
        "Adding W-SOL unlocks: W-SOL (1 new degree of freedom) "
        "and makes W-X for all X∈sol_pivot into BLOCKED pairs under the extended triangle rule."
    )

    new_vertex_unlocks = {
        "W_SOL_pair": "1 new genuinely independent pair",
        "W_X_pairs_after_accept": (
            f"Once W-SOL is accepted, W-X for all X∈sol_pivot "
            f"({len(sol_pivot)} tokens) are BLOCKED by extended triangle rule. "
            "But if W has meaningful cluster independence from all existing tokens, "
            "W-ATOM, W-AVAX etc. might offer independent degrees if W-ATOM∉family and W-AVAX∉family. "
            "Key insight: W-X ≠ W-SOL - X-SOL unless W-SOL AND X-SOL are BOTH in family. "
            "So: (W-ATOM) is FREE until W-SOL is accepted. After W-SOL accepted, W-ATOM=W-SOL - ATOM-SOL → BLOCKED."
        ),
        "optimal_strategy": (
            "Test W-SOL first. If ACCEPT → 1 new sleeve. "
            "DO NOT then test W-ATOM, W-INJ etc. — they become redundant. "
            "OR: test W-AVAX if AVAX cluster gives different cycle timing than SOL cluster. "
            "But W-AVAX is genuinely independent only if W-SOL ∉ family. "
            "Best single-vertex addition ROI = W-SOL (max vol ratio, max capacity)."
        ),
    }

    print(f"  Expansion insight: New vertex W → test W-SOL first.")
    print(f"  After W-SOL ACCEPT: W-X pairs for all X∈V become BLOCKED.")

    return {
        "internal_free_pairs": free,
        "n_internal_free":     n_free,
        "saturation_note":     "All 12 vertices span the SOL-pivot algebraic group. Zero internal FREE pairs.",
        "expansion_logic":     expansion_logic,
        "new_vertex_unlocks":  new_vertex_unlocks,
    }


# ── Phase 4: Candidate Vertex Ranking ─────────────────────────────────────────

def phase4_candidate_ranking() -> Dict:
    """
    Rank new vertex candidates W ∉ V by expected ROI for W-SOL pair.

    Scoring rubric:
      vol_ratio    : std(W) / std(SOL) — higher → more signal amplitude
      cycle_indep  : 1 - |corr(W_fr, SOL_fr)| — independence from SOL
      hl_listed    : bool — must be on Hyperliquid
      fr_amplitude : mean_ann_pct of |W-SOL diff| estimate
      cluster      : distinct from existing 12-vertex cluster taxonomy

    Available in cache (Hyperliquid listed): AAVE, BONK, CRV, JUP, KAS, MKR,
      NEAR, ONDO, OP, PENDLE, PEPE, PYTH, RNDR, SHIB, SUI, TAO, TON, UNI, WIF, WLD

    NOT in cache or NOT on HL: LINK, MATIC, ARB, GMX, DOGE, RUNE, FTM, FLOW, ROSE

    ARB: in cache? Let's check. DOGE: in cache.
    """
    print("\n[Phase 4] Candidate vertex ranking ...")

    sol = _load_fr("SOL")
    avax = _load_fr("AVAX")
    atom = _load_fr("ATOM")

    # Tokens available in HL cache (confirmed from ls output)
    HL_AVAILABLE = [
        "AAVE", "BONK", "CRV", "JUP", "KAS", "MKR", "NEAR", "ONDO",
        "OP", "PENDLE", "PEPE", "PYTH", "RNDR", "SHIB", "SUI", "TAO",
        "TON", "UNI", "WIF", "WLD",
        # Also check from full cache list
        "ARB", "DOGE", "ALGO", "DOT",  # from cache: yes
    ]
    # Also from cache: ALGO, ARB, DOGE, DOT, ETH, BTC (but ETH/BTC/DOT/ALGO already evaluated or in BTC-base family)
    # Exclude tokens already in V
    V_SET = {'SOL','APT','ATOM','INJ','AVAX','SEI','TIA','ENA','BNB','LDO','HBAR','FIL'}
    # Also exclude: BTC, ETH (not alt-alt targets), HBAR (in V but no cache)

    EXCLUDE = V_SET | {'BTC', 'ETH'}

    candidates_raw = []

    for tok in sorted(set(HL_AVAILABLE) - EXCLUDE):
        s = _load_fr(tok)
        if s is None:
            continue

        # Align with SOL
        df = pd.DataFrame({"W": s, "SOL": sol}).dropna()
        if len(df) < 1000:
            continue

        w_std  = float(df["W"].std())
        sol_std = float(df["SOL"].std())
        vol_ratio = w_std / sol_std if sol_std > 0 else 0.0
        raw_corr  = float(df["W"].corr(df["SOL"]))
        cycle_indep = 1.0 - abs(raw_corr)

        # FR amplitude: mean absolute differential
        diff = (df["W"] - df["SOL"]).abs()
        fr_amp_ann = float(diff.mean()) * 8760 * 100  # %/yr annualised mean |diff|

        # Smoothed differential signal quality
        diff_smooth = (df["W"] - df["SOL"]).rolling(168).mean().dropna()
        diff_std_smooth = float(diff_smooth.std()) if len(diff_smooth) > 0 else 0.0

        # W-AVAX and W-ATOM alignment (secondary pivot quality check)
        df_avax = pd.DataFrame({"W": s, "AVAX": avax}).dropna()
        w_avax_ratio = float(df_avax["W"].std() / df_avax["AVAX"].std()) if len(df_avax) > 100 else 0.0
        w_avax_corr  = float(df_avax["W"].corr(df_avax["AVAX"])) if len(df_avax) > 100 else 0.0

        df_atom = pd.DataFrame({"W": s, "ATOM": atom}).dropna()
        w_atom_corr  = float(df_atom["W"].corr(df_atom["ATOM"])) if len(df_atom) > 100 else 0.0

        w_mean_ann = float(s.mean()) * 8760 * 100

        # Composite score: vol_ratio * cycle_indep * (1 + fr_amp_factor)
        # We want high vol ratio AND low correlation with SOL → distinct cycle
        fr_amp_factor = min(fr_amp_ann / 20.0, 2.0)  # cap at 2.0 for 40%/yr amplitude
        composite = vol_ratio * cycle_indep * (1.0 + fr_amp_factor)

        candidates_raw.append({
            "token":          tok,
            "vol_ratio_vs_SOL": round(vol_ratio, 4),
            "raw_corr_SOL":    round(raw_corr, 4),
            "cycle_indep":    round(cycle_indep, 4),
            "fr_amp_ann_pct": round(fr_amp_ann, 2),
            "diff_std_smooth": round(diff_std_smooth, 8),
            "w_mean_ann_pct": round(w_mean_ann, 2),
            "w_std":          round(w_std, 8),
            "vol_ratio_vs_AVAX": round(w_avax_ratio, 4),
            "raw_corr_AVAX":  round(w_avax_corr, 4),
            "raw_corr_ATOM":  round(w_atom_corr, 4),
            "composite_score": round(composite, 4),
            "n_rows":         len(df),
            "hl_listed":      True,  # all in cache are HL-listed
        })

    # Sort by composite score descending
    candidates_raw.sort(key=lambda x: x["composite_score"], reverse=True)

    # Annotate top 10 with cluster taxonomy
    cluster_map = {
        "TAO":    "AI/DePin — Bittensor decentralised ML network, unique tokenomics",
        "INJ":    "Cosmos DeFi-perp (already in V)",
        "ONDO":   "RWA/tokenised treasuries — Real World Asset, distinct FR cycle",
        "PENDLE": "Yield-trading DeFi — fixed-rate split, yield tokenisation",
        "PEPE":   "Meme-speculative — pure sentiment FR driver, distinct cycle",
        "WIF":    "Meme-SOL ecosystem — SOL narrative overlap risk",
        "BONK":   "Meme-SOL ecosystem — SOL narrative overlap risk",
        "PYTH":   "Oracle/data-provider — SOL ecosystem but distinct use-case",
        "KAS":    "PoW L1 alternative — GPU miner FR driver, distinct cycle",
        "WLD":    "AI identity/biometrics — distinct cluster from L1s",
        "TON":    "Telegram-native L1 — CEX/social-native FR driver",
        "JUP":    "Jupiter DEX aggregator — SOL DEX ecosystem, high SOL corr risk",
        "NEAR":   "Platform L1 (sharding) — closed per K532 Governance v5 NEAR BLOCKED",
        "OP":     "Optimistic rollup L2 — ETH ecosystem, distinct from SOL cluster",
        "AAVE":   "DeFi lending — blue-chip, low vol ratio but distinct cycle",
        "CRV":    "DeFi AMM — low vol ratio, governance tokenomics",
        "MKR":    "DeFi CDPs/RWA (Spark) — low vol ratio but distinct cluster",
        "UNI":    "DeFi DEX — low vol ratio, ETH ecosystem governance",
        "SUI":    "SVM-adjacent L1 — high ecosystem corr with SOL",
        "SHIB":   "Meme ERC20 — ETH ecosystem, distinct from SOL memes",
        "RNDR":   "AI/GPU compute — DePin sector, distinct cycle",
        "ALGO":   "Enterprise utility L1 — BLOCKED per K532 Governance v5 ALGO closed",
        "ARB":    "ETH L2 — BLOCKED per K532 Governance v5 ARB closed",
        "DOT":    "Relay-chain L1 — BLOCKED per K532 Governance v5 DOT closed",
    }

    # Governance v5 closed lines — exclude from ranking
    GOVERNANCE_BLOCKED = {"NEAR", "ALGO", "ARB", "DOT"}

    top_candidates = []
    for c in candidates_raw:
        tok = c["token"]
        if tok in GOVERNANCE_BLOCKED:
            c["blocked"] = f"K532 Governance v5 CLOSED: {tok}"
            c["eligible"] = False
        else:
            c["cluster"] = cluster_map.get(tok, "Unknown — needs classification")
            c["eligible"] = True
            if c["vol_ratio_vs_SOL"] < 0.5:
                c["note"] = "Low vol ratio < 0.5x — borderline for meaningful W-SOL signal"

        top_candidates.append(c)

    eligible = [c for c in top_candidates if c.get("eligible", True) and not c.get("blocked")]
    blocked  = [c for c in top_candidates if c.get("blocked")]

    print(f"  Total candidates analysed: {len(candidates_raw)}")
    print(f"  Governance-blocked: {len(blocked)}")
    print(f"  Eligible top-10:")
    for i, c in enumerate(eligible[:10], 1):
        print(f"    {i:2d}. {c['token']:8s} vol_ratio={c['vol_ratio_vs_SOL']:.3f}  "
              f"cycle_indep={c['cycle_indep']:.3f}  score={c['composite_score']:.4f}")

    return {
        "all_candidates": top_candidates,
        "eligible_top10": eligible[:10],
        "governance_blocked": [c["token"] for c in blocked],
        "first_pair_recommendation": _recommend_first_pair(eligible[:10]),
    }


def _recommend_first_pair(top10: List[Dict]) -> Dict:
    """Pick the single best first pair to test (W-SOL or W-AVAX)."""
    if not top10:
        return {"recommendation": "No eligible candidates found"}

    best = top10[0]
    tok = best["token"]

    # W-SOL is always the recommended first test (maximises vol ratio and opens SOL-pivot family)
    # Exception: if W has high SOL corr (>0.4), consider W-AVAX or W-ATOM as first test
    corr_sol = abs(best["raw_corr_SOL"])
    if corr_sol > 0.4:
        pivot = "AVAX"
        rationale = (
            f"{tok} has raw_corr(SOL)={best['raw_corr_SOL']:.3f} > 0.4 threshold. "
            f"Test {tok}-AVAX first to avoid SOL cluster saturation. "
            f"vol_ratio({tok}/AVAX)={best['vol_ratio_vs_AVAX']:.3f}"
        )
    else:
        pivot = "SOL"
        rationale = (
            f"{tok} has raw_corr(SOL)={best['raw_corr_SOL']:.3f} ≤ 0.4. "
            f"Test {tok}-SOL first — direct SOL-pivot extension. "
            f"vol_ratio({tok}/SOL)={best['vol_ratio_vs_SOL']:.3f}"
        )

    return {
        "first_pair":   f"{tok}-{pivot}",
        "token":        tok,
        "pivot":        pivot,
        "rationale":    rationale,
        "wave_label":   "K745",
        "composite_score": best["composite_score"],
    }


# ── Phase 5: ROI Projections ──────────────────────────────────────────────────

def phase5_roi_projections(cand: Dict) -> Dict:
    """
    K523 3-point ROI projection per candidate (conservative / mid / optimistic).

    Reference calibration from accepted family:
      K683 APT-SOL    OOS Sh=39.3  →  ~$180K/yr @$10M (est)
      K684 ATOM-SOL   OOS Sh=43.4  →  ~$170K/yr @$10M (est)
      K696 ENA-SOL    OOS Sh=26.9  →  ~$130K/yr @$10M (est)
      K694 TIA-SOL    OOS Sh=19.1  →  ~$105K/yr @$10M (est)
      K739 FIL-SOL    OOS Sh=23.4  →  ~$122K/yr @$10M (est)
      K736 TIA-AVAX   OOS Sh=13.0  →  ~$75K/yr @$10M (est)

    K523 haircuts:
      realized_to_stated  = 0.38  (K518 floor)
      oos_haircut         = 0.25  (paired-trade 25% OOS haircut)
      gross_to_net        = 0.85  (15% fee + slippage)
      conservative = stated * 0.38 * 0.75 * 0.85
      central      = stated * 0.50 * 0.85
      optimistic   = stated * 0.65 * 0.85

    Gross ROI estimate per token (from vol_ratio and FR amplitude):
      gross_est_annual ≈ vol_ratio * SOL_base_gross * cycle_indep_factor
      SOL_base_gross ≈ $200K/yr @$10M @1% sleeve (from K683/K684 average)
    """
    print("\n[Phase 5] ROI projections ...")

    SOL_BASE_GROSS = 200_000  # USD/yr @$10M @1% sleeve (conservative)
    R2S = 0.38   # realized-to-stated ratio (K518)
    OOS_HC = 0.25  # paired-trade OOS haircut
    FEE_HC = 0.15  # gross-to-net haircut

    projections = []

    for c in cand["eligible_top10"]:
        tok = c["token"]
        vr  = c["vol_ratio_vs_SOL"]
        ci  = c["cycle_indep"]

        # Gross estimate (stated upper bound)
        gross_est = SOL_BASE_GROSS * vr * (0.5 + 0.5 * ci)  # blend of vol and indep

        # K523 3-point
        conservative = gross_est * R2S * (1 - OOS_HC) * (1 - FEE_HC)
        central      = gross_est * 0.50 * (1 - FEE_HC)
        optimistic   = gross_est * 0.65 * (1 - FEE_HC)

        projections.append({
            "token":         tok,
            "pair":          f"{tok}-SOL",
            "gross_est_usd_yr": round(gross_est),
            "k523_conservative_usd_yr": round(conservative),
            "k523_central_usd_yr":      round(central),
            "k523_optimistic_usd_yr":   round(optimistic),
            "vol_ratio":     c["vol_ratio_vs_SOL"],
            "cycle_indep":   c["cycle_indep"],
            "composite_score": c["composite_score"],
            "note":          (
                f"K523: conservative ${conservative:,.0f} / "
                f"central ${central:,.0f} / "
                f"optimistic ${optimistic:,.0f} /yr @$10M @1% sleeve. "
                f"Upper bound ${gross_est:,.0f} — NOT central estimate (K523 rule)."
            ),
        })

    # Wave priority order K745-K754
    wave_queue = []
    for i, p in enumerate(projections[:10], start=745):
        wave_queue.append({
            "wave": f"K{i}",
            "pair": p["pair"],
            "token": p["token"],
            "priority_rank": i - 744,
            "central_usd_yr": p["k523_central_usd_yr"],
            "rationale": (
                f"vol_ratio={p['vol_ratio']:.3f}, cycle_indep={p['cycle_indep']:.3f}, "
                f"score={p['composite_score']:.4f}"
            ),
        })

    print(f"  Wave queue K745-K{744+len(wave_queue)}:")
    for wq in wave_queue:
        print(f"    {wq['wave']}: {wq['pair']} (central ${wq['central_usd_yr']:,}/yr)")

    return {
        "projections": projections,
        "wave_queue": wave_queue,
        "k523_methodology": {
            "realized_to_stated_ratio": R2S,
            "oos_haircut": OOS_HC,
            "fee_haircut": FEE_HC,
            "sol_base_gross_usd_yr": SOL_BASE_GROSS,
            "note": (
                "K523 mandatory 3-point projection. Upper bound = gross_est. "
                "Central is NOT upper bound. R2S=0.38 from K518 floor. "
                "OOS haircut=25% from paired-trade family rule."
            ),
        },
    }


# ── Phase 6: Saturation Insight Memo ──────────────────────────────────────────

def phase6_saturation_memo(inv: Dict, mat: Dict, ph3: Dict) -> Dict:
    """
    Formal documentation of MR9 L002 SOL-Pivot Triangle Rule.
    """
    print("\n[Phase 6] Saturation insight memo ...")

    memo = {
        "title": "MR9 L002: SOL-Pivot Triangle Rule — Formal Specification",
        "wave": "K744",
        "date": RUN_TS,
        "rule_statement": (
            "THEOREM (SOL-Pivot Triangle Rule): "
            "Let F be an alt-alt family using SOL as a dominant pivot token. "
            "If both (X-SOL) ∈ F and (Y-SOL) ∈ F, then "
            "(X-Y)_raw = (X-SOL)_raw − (Y-SOL)_raw identically "
            "(machine precision, max_err < 1e-15). "
            "Therefore, the pair (X-Y) carries ZERO marginal alpha beyond {F} "
            "and MUST be rejected at MR9 pre-check without backtest."
        ),
        "proof": (
            "Let X_fr, Y_fr, S_fr denote funding-rate time series. "
            "(X-Y)_raw = X_fr − Y_fr. "
            "(X-SOL)_raw = X_fr − S_fr. "
            "(Y-SOL)_raw = Y_fr − S_fr. "
            "(X-SOL)_raw − (Y-SOL)_raw = (X_fr − S_fr) − (Y_fr − S_fr) = X_fr − Y_fr = (X-Y)_raw. QED. "
            "Numerical confirmation: K743 LDO-ATOM max_err = 2.17e-19 << 1e-15 (K743, 2026-05-30)."
        ),
        "generalization": (
            "The rule applies to ANY 3 tokens A, B, C where two of the three "
            "pair differentials are already in the family. "
            "In general: for any graph G on vertices V where signal(u-v) = fr_u − fr_v, "
            "the signal space has dimension |V|−1 (spanning tree). "
            "Adding more than |V|−1 edges introduces linear dependencies. "
            "The SOL-pivot family with 12 vertices can support at most 11 algebraically "
            "independent pairs. The current 14-member family has 3 linearly dependent members "
            "(K719 ENA-ATOM, K728 INJ-ATOM, K736 TIA-AVAX) which were accepted because "
            "their SIGNAL correlation differs (strategy uses sign thresholding + smoothing), "
            "but at raw differential level they ARE dependent."
        ),
        "family_saturation_stats": {
            "n_vertices": inv["n_vertices"],
            "max_independent_pairs": inv["n_vertices"] - 1,  # spanning tree
            "n_family_members": inv["n_family"],
            "n_total_pairs": 66,
            "n_blocked": mat["counts"]["BLOCKED_SOL_TRIANGLE"],
            "n_accept": mat["counts"]["ACCEPT"],
            "n_reject_k740": mat["counts"]["REJECT_K740"],
            "n_free_internal": mat["counts"]["FREE"],
            "saturation_pct": mat["saturation_rate_pct"],
        },
        "expansion_strategy": (
            "To generate genuinely new alpha from this family: "
            "(1) Add new vertex W ∉ V. Test W-SOL first. "
            "(2) Once W-SOL ACCEPT: W-X for all X∈sol_pivot are BLOCKED. "
            "    Do NOT test W-ATOM, W-INJ, W-TIA etc. after W-SOL ACCEPT. "
            "(3) Exception: W-AVAX or W-ATOM if W-SOL is NOT in family. "
            "    This preserves independence until the SOL leg is added. "
            "(4) Cluster independence of W from all 12 existing vertices "
            "    is the primary filter — meta-narrative overlap trumps G5 corr."
        ),
        "mr9_update": {
            "lesson_id": "MR9_L002",
            "first_confirmed": "K743 LDO-ATOM (2026-05-30)",
            "extended_by": "K744 (2026-05-30) — full family saturation map",
            "key_insight": (
                "Signal correlation ≠ algebraic independence. "
                "K721 (LDO-SOL) × K684 (ATOM-SOL) signal corr = 0.133 (low), "
                "yet K743 (LDO-ATOM) = K721_raw − K684_raw EXACTLY. "
                "MR9 STRICT checks algebraic identity (raw FR), NOT signal correlation. "
                "Use spanning-tree counting: with 12 vertices, max 11 independent pairs."
            ),
        },
    }

    print(f"  Memo: {memo['title']}")
    print(f"  Saturation: {mat['saturation_rate_pct']}% of 66 pairs BLOCKED or ACCEPTED")
    print(f"  Max independent pairs for 12 vertices: {inv['n_vertices'] - 1}")

    return memo


# ── CSV Matrix Writer ──────────────────────────────────────────────────────────

def write_saturation_csv(mat: Dict) -> None:
    """Write 66-row CSV with pair, A, B, status, reason columns."""
    print(f"\n[CSV] Writing saturation matrix → {OUT_CSV} ...")
    rows = mat["matrix_rows"]

    with open(str(OUT_CSV), "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=["pair","A","B","status","reason"])
        writer.writeheader()
        for row in rows:
            writer.writerow({
                "pair":   row["pair"],
                "A":      row["A"],
                "B":      row["B"],
                "status": row["status"],
                "reason": row.get("reason", ""),
            })
    print(f"  Written {len(rows)} rows.")


# ── Markdown Builder ───────────────────────────────────────────────────────────

def build_md(result: Dict) -> str:
    inv  = result["phase1_family_inventory"]
    mat  = result["phase2_saturation_matrix"]
    ph3  = result["phase3_free_pairs"]
    ph4  = result["phase4_candidate_ranking"]
    ph5  = result["phase5_roi_projections"]
    ph6  = result["phase6_saturation_memo"]
    fpr  = ph4["first_pair_recommendation"]

    top10 = ph4["eligible_top10"]
    proj  = ph5["projections"]
    wq    = ph5["wave_queue"]

    # Build tables
    family_rows = "\n".join(
        f"| {e['wave']} | {e['pair']} | {e['A']} | {e['B']} | "
        f"{e['oos_sharpe'] or 'N/A'} | {e['decision']} |"
        for e in inv["family"]
    )

    matrix_summary = "\n".join(
        f"| {status} | {count} | {round(count/66*100,1)}% |"
        for status, count in mat["counts"].items()
    )

    cand_rows = "\n".join(
        f"| {i+1} | {c['token']} | {c['vol_ratio_vs_SOL']:.3f} | "
        f"{c['raw_corr_SOL']:.3f} | {c['cycle_indep']:.3f} | "
        f"{c.get('fr_amp_ann_pct', 0):.1f}%/yr | {c['composite_score']:.4f} |"
        for i, c in enumerate(top10)
    )

    proj_rows = "\n".join(
        f"| {p['pair']} | ${p['k523_conservative_usd_yr']:,} | "
        f"${p['k523_central_usd_yr']:,} | ${p['k523_optimistic_usd_yr']:,} | "
        f"${p['gross_est_usd_yr']:,} |"
        for p in proj
    )

    wave_rows = "\n".join(
        f"| {w['wave']} | {w['pair']} | ${w['central_usd_yr']:,} | {w['rationale']} |"
        for w in wq
    )

    blocked_count = mat["counts"]["BLOCKED_SOL_TRIANGLE"]
    free_count    = mat["counts"]["FREE"]

    return f"""# K744 Alt-Alt Family Saturation Map (MR9 L002 SOL-Pivot Triangle)

**Wave**: K744
**Run time**: {result['run_time_jst']}
**K339 REPO_ROOT**: /Users/nekonaomichi/crypto-lab
**LIVE changes**: NONE — read-only analysis

---

## Executive Summary

After K743 LDO-ATOM was auto-rejected as `K721_raw − K684_raw` (max_err=2.17e-19),
K744 formally characterises the algebraic saturation of the 14-member alt-alt family.

**Key findings:**
- Vertex set V = 12 tokens, all connected to SOL via X-SOL pivot legs
- 66 total C(12,2) pairs: {mat["counts"]["ACCEPT"]} ACCEPT | {mat["counts"]["REJECT_K740"]} REJECT | {blocked_count} BLOCKED_SOL_TRIANGLE | {free_count} FREE internal
- **Saturation: {mat["saturation_rate_pct"]}%** of all vertex-pair space is consumed
- Maximum algebraically independent pairs for 12 vertices = **11** (spanning tree bound)
- **Zero internal FREE pairs remain** — expansion requires adding a new vertex W ∉ V
- Top candidate: **{fpr['first_pair']}** (wave K745)

---

## Phase 1: Family Inventory (14 Members)

| Wave | Pair | A | B | OOS Sharpe | Decision |
|------|------|---|---|-----------|---------|
{family_rows}

**Vertex set V** ({inv["n_vertices"]} tokens): {', '.join(inv["vertex_set_V"])}

**SOL-pivot tokens** (have X-SOL in family): {', '.join(inv["sol_pivot_tokens"])}

**Non-SOL edges** (K719, K728, K736 — themselves derivable from SOL-pivot pairs):
{', '.join(inv["non_sol_edges"])}

---

## Phase 2: Algebraic Saturation Matrix (66 Pairs)

| Status | Count | % of 66 |
|--------|-------|---------|
{matrix_summary}

### SOL-Pivot Triangle Rule (MR9 L002)

For any X, Y ∈ V where both X-SOL and Y-SOL are in the family:

```
(X-Y)_raw = (X-SOL)_raw − (Y-SOL)_raw
max_err < 1e-15 (machine precision)
```

**{blocked_count} pairs blocked** by this rule (all pairs X-Y where X,Y both have SOL-pivot legs).

### Non-SOL Edges Are Also SOL-Derivable

The 3 non-SOL edges in the family are themselves SOL-triangle results:
- K719 ENA-ATOM = K696(ENA-SOL) − K684(ATOM-SOL)
- K728 INJ-ATOM = K686(SOL-INJ, reversed) − K684(ATOM-SOL)
- K736 TIA-AVAX = K694(TIA-SOL) − K687(AVAX-SOL)

This means they add **zero additional algebraic degrees of freedom** beyond the SOL-pivot span.

---

## Phase 3: Genuinely Independent Candidate Set

**Internal FREE pairs: {free_count}**

All 12 vertices are SOL-pivot spanned. The current 12-vertex family is algebraically COMPLETE:
every vertex V has a SOL-pivot leg → all C(12,2)=66 internal pairs are consumed.

**Spanning tree bound**: Max independent pairs = |V| − 1 = {inv["n_vertices"] - 1}.
The family has {inv["n_family"]} members → {inv["n_family"] - (inv["n_vertices"]-1)} linearly dependent
members (K719/K728/K736, which were accepted due to strategy-level independence, not raw-level).

### Expansion Strategy

The ONLY path to genuinely new alpha from this family is to introduce **new vertex W ∉ V**:
1. Test **W-SOL** first → 1 new independent degree of freedom
2. Once W-SOL ACCEPTED: all W-X (X ∈ sol_pivot) become BLOCKED by extended triangle rule
3. Exception: W-AVAX or W-ATOM can be tested BEFORE W-SOL is accepted
4. Cluster independence of W from all 12 existing vertices = primary pre-screen filter

---

## Phase 4: Candidate Vertex Ranking (Top 10 W)

**Scoring**: composite = vol_ratio × cycle_indep × (1 + fr_amp_factor)

| Rank | Token | Vol Ratio/SOL | Corr/SOL | Cycle Indep | FR Amp | Score |
|------|-------|--------------|---------|------------|--------|-------|
{cand_rows}

**Governance-blocked** (K532 v5 closed lines): {', '.join(ph4["governance_blocked"])}

### First Pair Recommendation

**{fpr["first_pair"]}** (Wave {fpr["wave_label"]})

{fpr["rationale"]}

---

## Phase 5: ROI Projections (K523 3-Point Mandatory)

@$10M @1% sleeve. K523 haircuts: R2S=0.38, OOS=25%, fee=15%.
Upper bound = gross_est (NOT central estimate per K523 rule).

| Pair | Conservative | Central | Optimistic | Upper Bound |
|------|-------------|---------|-----------|------------|
{proj_rows}

### Wave Priority Queue K745–K{744+len(wq)}

| Wave | Pair | Central $/yr | Rationale |
|------|------|-------------|-----------|
{wave_rows}

---

## Phase 6: MR9 L002 SOL-Pivot Triangle Rule (Formal Memo)

### Theorem

{ph6["rule_statement"]}

### Proof

{ph6["proof"]}

### Generalisation

{ph6["generalization"]}

### Family Saturation Statistics

| Metric | Value |
|--------|-------|
| Vertices \|V\| | {ph6["family_saturation_stats"]["n_vertices"]} |
| Max independent pairs (spanning tree) | {ph6["family_saturation_stats"]["max_independent_pairs"]} |
| Current family members | {ph6["family_saturation_stats"]["n_family_members"]} |
| Total C(12,2) pairs | 66 |
| Blocked (SOL triangle) | {ph6["family_saturation_stats"]["n_blocked"]} |
| Accept | {ph6["family_saturation_stats"]["n_accept"]} |
| Reject K740 | {ph6["family_saturation_stats"]["n_reject_k740"]} |
| Free internal | {ph6["family_saturation_stats"]["n_free_internal"]} |
| Saturation % | {ph6["family_saturation_stats"]["saturation_pct"]}% |

### Expansion Strategy

{ph6["expansion_strategy"]}

### MR9 Update

**Lesson**: {ph6["mr9_update"]["key_insight"]}

**First confirmed**: {ph6["mr9_update"]["first_confirmed"]}
**Extended by**: {ph6["mr9_update"]["extended_by"]}

---

## Deliverables

- `wave_k744_saturation_map.py` — K339 analysis script
- `wave_k744_saturation_map.json` — full matrix + candidate rankings
- `wave_k744_saturation_map.md` — this insight document
- `data/alt_alt_saturation_matrix.csv` — 66-row BLOCKED/FREE matrix
- `report.html` — K744 badge

---

*K339 REPO_ROOT | LIVE自動変更禁止 | {result['run_time_jst']}*
"""


# ── Report HTML Badge ──────────────────────────────────────────────────────────

def update_report_html(result: Dict) -> None:
    """Prepend K744 badge to report.html."""
    print(f"\n[HTML] Updating report.html ...")
    report_path = REPO_ROOT / "report.html"

    if not report_path.exists():
        print("  report.html not found — skip")
        return

    ph4 = result["phase4_candidate_ranking"]
    ph5 = result["phase5_roi_projections"]
    mat = result["phase2_saturation_matrix"]
    fpr = ph4["first_pair_recommendation"]
    top1 = ph4["eligible_top10"][0] if ph4["eligible_top10"] else {}
    proj1 = ph5["projections"][0] if ph5["projections"] else {}
    wq = ph5["wave_queue"]
    wq_str = " | ".join(f"{w['wave']} {w['pair']}" for w in wq[:5])

    ts = result["run_time_jst"]
    blocked = mat["counts"]["BLOCKED_SOL_TRIANGLE"]
    accept  = mat["counts"]["ACCEPT"]
    free    = mat["counts"]["FREE"]

    top1_tok  = top1.get("token", "TAO")
    top1_score = top1.get("composite_score", 0)
    proj1_cen = proj1.get("k523_central_usd_yr", 0)
    proj1_opt = proj1.get("k523_optimistic_usd_yr", 0)

    badge_comment = (
        f"<!-- K744_SATURATION_MAP: MR9 L002 SOL-Pivot Triangle Rule | "
        f"66 vertex pairs: {accept} ACCEPT | 1 REJECT_K740 | {blocked} BLOCKED_SOL_TRIANGLE | {free} FREE | "
        f"Saturation={mat['saturation_rate_pct']}% | Max independent=11 (spanning tree) | "
        f"All 12 vertices SOL-pivot spanned → zero internal FREE pairs | "
        f"New vertex required for expansion | "
        f"Top candidate: {fpr['first_pair']} (K745) | "
        f"top10: {', '.join(c['token'] for c in ph4['eligible_top10'][:5])} | "
        f"K523 {top1_tok}-SOL: central ${proj1_cen:,}/yr optimistic ${proj1_opt:,}/yr @$10M | "
        f"wave queue: {wq_str} | "
        f"K339 REPO_ROOT | {ts} -->"
    )

    badge_html = f"""
<!-- K744 SATURATION MAP BADGE -->
<div id="k744-badge" style="background:linear-gradient(135deg,#0a001a 0%,#001428 30%,#001a14 70%,#0a001a 100%);border:3px solid #a78bfa;border-radius:14px;padding:16px 22px;margin:0 0 16px 0;box-shadow:0 0 40px rgba(167,139,250,0.30),0 4px 24px rgba(167,139,250,0.15);font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',sans-serif;">
  <div style="display:flex;align-items:center;gap:12px;margin-bottom:10px;">
    <div style="background:rgba(167,139,250,0.15);border:2px solid #a78bfa;border-radius:8px;padding:4px 10px;color:#a78bfa;font-size:0.78rem;font-weight:800;letter-spacing:0.06em;">K744</div>
    <div style="color:#a78bfa;font-size:1.10rem;font-weight:900;letter-spacing:0.03em;margin-bottom:0;">&#128202; K744 Alt-Alt Saturation Map &mdash; MR9 L002 SOL-Pivot Triangle Rule &mdash; {ts}</div>
  </div>
  <div style="display:grid;grid-template-columns:repeat(auto-fit,minmax(200px,1fr));gap:8px;margin-bottom:10px;">
    <div style="background:rgba(0,0,0,0.3);border-radius:8px;padding:8px 12px;">
      <div style="color:#8b949e;font-size:0.65rem;font-weight:700;letter-spacing:0.08em;text-transform:uppercase;margin-bottom:3px;">SATURATION STATUS</div>
      <div style="color:#c9d1d9;font-size:0.82rem;font-weight:600;">{accept} ACCEPT | 1 REJECT | {blocked} BLOCKED | {free} FREE</div>
      <div style="color:#a78bfa;font-size:0.70rem;font-weight:700;">Saturation: {mat['saturation_rate_pct']}% / 66 pairs</div>
    </div>
    <div style="background:rgba(0,0,0,0.3);border-radius:8px;padding:8px 12px;">
      <div style="color:#8b949e;font-size:0.65rem;font-weight:700;letter-spacing:0.08em;text-transform:uppercase;margin-bottom:3px;">SPANNING TREE</div>
      <div style="color:#c9d1d9;font-size:0.82rem;font-weight:600;">Max independent: 11 pairs (|V|&#x2212;1)</div>
      <div style="color:#fbbf24;font-size:0.70rem;font-weight:700;">Zero internal FREE pairs — expansion requires W&#x2209;V</div>
    </div>
    <div style="background:rgba(0,0,0,0.3);border-radius:8px;padding:8px 12px;">
      <div style="color:#8b949e;font-size:0.65rem;font-weight:700;letter-spacing:0.08em;text-transform:uppercase;margin-bottom:3px;">TOP CANDIDATE</div>
      <div style="color:#34d399;font-size:0.88rem;font-weight:800;">{fpr['first_pair']} &rarr; K745</div>
      <div style="color:#c9d1d9;font-size:0.70rem;font-weight:600;">score={top1_score:.4f} | K523 central ${proj1_cen:,}/yr</div>
    </div>
    <div style="background:rgba(0,0,0,0.3);border-radius:8px;padding:8px 12px;">
      <div style="color:#8b949e;font-size:0.65rem;font-weight:700;letter-spacing:0.08em;text-transform:uppercase;margin-bottom:3px;">WAVE QUEUE</div>
      <div style="color:#c9d1d9;font-size:0.75rem;font-weight:600;">{wq_str}</div>
    </div>
  </div>
  <div style="background:rgba(167,139,250,0.08);border:1px solid rgba(167,139,250,0.25);border-radius:6px;padding:8px 12px;margin-bottom:8px;">
    <div style="color:#a78bfa;font-size:0.72rem;font-weight:700;margin-bottom:4px;">MR9 L002 SOL-Pivot Triangle Rule (K743→K744 formalised)</div>
    <div style="color:#8b949e;font-size:0.68rem;line-height:1.5;">
      If (X&#x2212;SOL)&#x2208;family AND (Y&#x2212;SOL)&#x2208;family &rarr; (X&#x2212;Y) = (X&#x2212;SOL) &#x2212; (Y&#x2212;SOL) [algebraically redundant, max_err&lt;1e&#x2212;15].
      All 12 vertices are SOL-pivot spanned &rarr; 51 triangle-blocked pairs. K743 LDO-ATOM confirmed (2.17e&#x2212;19).
      Strategy: add new vertex W (W&#x2212;SOL first), not W&#x2212;X after W&#x2212;SOL accepted.
    </div>
  </div>
  <div style="display:flex;justify-content:space-between;align-items:center;flex-wrap:wrap;gap:6px;">
    <div style="color:#8b949e;font-size:0.60rem;">K744 Saturation Map | data/alt_alt_saturation_matrix.csv (66 rows) | wave_k744_saturation_map.{{py,json,md}}</div>
    <div style="color:#a78bfa;font-size:0.68rem;font-weight:700;">K744</div>
  </div>
</div>"""

    content = report_path.read_text(encoding="utf-8")

    # Find insertion point: after the last K743 badge comment
    k743_anchor = "<!-- K743 LDO-ATOM ALT-ALT MR9 STRICT REJECT BADGE -->"
    k744_marker = "<!-- K744 SATURATION MAP BADGE -->"

    if k744_marker in content:
        print("  K744 badge already present — skip insert")
        # But update the timestamp in the header
        return

    if k743_anchor in content:
        insert_pos = content.index(k743_anchor)
        new_content = (
            content[:insert_pos]
            + badge_comment + "\n"
            + badge_html + "\n"
            + content[insert_pos:]
        )
    else:
        # Fallback: insert before k743-badge div
        anchor2 = '<div id="k743-badge"'
        if anchor2 in content:
            insert_pos = content.index(anchor2)
            new_content = (
                content[:insert_pos]
                + badge_comment + "\n"
                + badge_html + "\n"
                + content[insert_pos:]
            )
        else:
            # Last resort: prepend after <body
            body_tag = "<body"
            if body_tag in content:
                idx = content.index(body_tag)
                idx = content.index(">", idx) + 1
                new_content = (
                    content[:idx]
                    + "\n" + badge_comment + "\n" + badge_html + "\n"
                    + content[idx:]
                )
            else:
                print("  Could not find insertion point — skip")
                return

    # Update 最終更新 header line
    import re
    ts_pattern = r"最終更新:.*?(?=&nbsp;|</)"
    ts_replacement = (
        f"最終更新: {ts} "
        f"(K744 Alt-Alt Saturation Map | MR9 L002 SOL-Pivot Triangle | "
        f"66 pairs: {accept} ACCEPT {blocked} BLOCKED {free} FREE | "
        f"Saturation {mat['saturation_rate_pct']}% | Top candidate {fpr['first_pair']} K745 | K339 REPO_ROOT) "
    )
    new_content = re.sub(ts_pattern, ts_replacement, new_content, count=1)

    report_path.write_text(new_content, encoding="utf-8")
    print(f"  report.html updated ({len(new_content):,} chars)")


# ── Main ──────────────────────────────────────────────────────────────────────

def main() -> None:
    print()

    # Phase 1
    inv  = phase1_family_inventory()

    # Phase 2
    mat  = phase2_saturation_matrix(inv)

    # Phase 3
    ph3  = phase3_free_pairs(mat, inv)

    # Phase 4
    ph4  = phase4_candidate_ranking()

    # Phase 5
    ph5  = phase5_roi_projections(ph4)

    # Phase 6
    ph6  = phase6_saturation_memo(inv, mat, ph3)

    elapsed = time.time() - t0

    result = {
        "wave":            "K744",
        "title":           "Alt-Alt Family Saturation Map (MR9 L002 SOL-Pivot Triangle Rule)",
        "run_time_jst":    RUN_TS,
        "runtime_s":       round(elapsed, 2),
        "phase1_family_inventory":  inv,
        "phase2_saturation_matrix": mat,
        "phase3_free_pairs":        ph3,
        "phase4_candidate_ranking": ph4,
        "phase5_roi_projections":   ph5,
        "phase6_saturation_memo":   ph6,
        "k339_compliance": {
            "repo_root":    str(REPO_ROOT),
            "out_json":     str(OUT_JSON),
            "out_md":       str(OUT_MD),
            "out_csv":      str(OUT_CSV),
            "live_changes": "NONE — read-only evaluation",
            "pattern":      "K339 REPO_ROOT",
        },
    }

    # Write JSON
    with open(str(OUT_JSON), "w", encoding="utf-8") as fh:
        json.dump(result, fh, indent=2, ensure_ascii=False)
    print(f"\n  JSON → {OUT_JSON}")

    # Write CSV
    write_saturation_csv(mat)

    # Write MD
    md = build_md(result)
    with open(str(OUT_MD), "w", encoding="utf-8") as fh:
        fh.write(md)
    print(f"  MD   → {OUT_MD}")

    # Update report.html
    update_report_html(result)

    print(f"\n  Elapsed: {elapsed:.2f}s")
    print("=" * 78)
    print(f"  K744 COMPLETE")
    print(f"  Saturation: {mat['saturation_rate_pct']}% | "
          f"BLOCKED: {mat['counts']['BLOCKED_SOL_TRIANGLE']} | "
          f"FREE: {mat['counts']['FREE']} internal | "
          f"Top candidate: {ph4['first_pair_recommendation']['first_pair']} → K745")
    print("=" * 78)


if __name__ == "__main__":
    main()

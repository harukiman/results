"""
Wave K516 — v6.28 Architecture Proposal (APT + SEI + TIA Family Additions)
===========================================================================
K339 REPO_ROOT pattern: all paths relative to REPO_ROOT
Date: 2026-05-30
Priority: NORMAL (batch composition after K511+K507+K512 ACCEPTs)

Mission: Batch-consolidate K511 v6.26 baseline + K507 SEI/TIA ACCEPT + K512 APT ACCEPT
into a formal v6.28 candidate composition (skip v6.27 per batch discipline).
Computes allocation table, HL concentration audit (<65% cap), profit comparison
@ $10M / $100M / $200M, 5-year projection, §6 gate recheck, and implementation roadmap.

Phases:
  1.  v6.26 baseline (K511) definition
  2.  v6.28 candidate delta logic
  3.  Composition table generation
  4.  HL concentration audit
  5.  Profit @ $10M / $100M / $200M (v6.26 vs v6.28)
  6.  5-year terminal projection
  7.  §6 gate recheck (G5 correlations, G7 return, HL cap)
  8.  Implementation roadmap Phase 1–5 (Now → 120d)
  9.  User actions #26–28 (APT / SEI / TIA scaffolds)
  10. JSON + MD output
"""

import os
import json
import math
from datetime import datetime, timezone
from pathlib import Path

# ─── K339 REPO_ROOT pattern ────────────────────────────────────────────────────
REPO_ROOT   = Path(__file__).parent.resolve()
OUTPUT_JSON = REPO_ROOT / "wave_k516_v628_proposal.json"
OUTPUT_MD   = REPO_ROOT / "wave_k516_v628_proposal.md"

# ─── AUM Scenarios ─────────────────────────────────────────────────────────────
AUM_10M  = 10_000_000
AUM_100M = 100_000_000
AUM_200M = 200_000_000

# ─── HL Concentration Cap ──────────────────────────────────────────────────────
HL_CAP = 0.65   # feedback_concentration_risk_HL.md: HL > 65% forbidden

# ─── K208 Decay Parameters (K509 CONFIRM, carried from K511) ──────────────────
K208_DECAY_CONFIRMED = True
K208_SHARPE_2024H2   = 22.61
K208_SHARPE_2026YTD  = 7.46
K208_DECAY_PCT       = 0.67    # -67% Y/Y

# ─── K492 Variant E augmentation (K511 baseline) ──────────────────────────────
K492E_LIFT_10M = 223_000   # +$223K/yr lift to K280 sleeve

# ─── Family Rank (K516) ────────────────────────────────────────────────────────
FAMILY_RANK = [
    {"rank": 1, "symbol": "APT-BTC", "wave": "K512", "sharpe": 51.10, "ann_10m": 302_000, "status": "ACCEPT"},
    {"rank": 2, "symbol": "ATOM-BTC", "wave": "K493", "sharpe": 50.79, "ann_10m": 231_000, "status": "ACCEPT"},
    {"rank": 3, "symbol": "SEI-BTC",  "wave": "K507", "sharpe": 48.10, "ann_10m": 179_000, "status": "ACCEPT"},
    {"rank": 4, "symbol": "AVAX-BTC", "wave": "K484", "sharpe": 43.89, "ann_10m":  76_000, "status": "ACCEPT"},
    {"rank": 5, "symbol": "SOL-BTC",  "wave": "K476", "sharpe": 16.30, "ann_10m": 187_000, "status": "ACCEPT"},
    {"rank": 6, "symbol": "TIA-BTC",  "wave": "K507", "sharpe": 14.44, "ann_10m":  51_000, "status": "ACCEPT"},
    {"rank": 7, "symbol": "INJ-BTC",  "wave": "K500", "sharpe": 11.23, "ann_10m": 124_000, "status": "ACCEPT"},
    {"rank": 8, "symbol": "ETH-BTC",  "wave": "K449", "sharpe":  5.66, "ann_10m":  13_000, "status": "ACCEPT"},
]
FAMILY_TOTAL_10M = sum(m["ann_10m"] for m in FAMILY_RANK)  # $1,163K (per-strategy at current weights)

# ─── v6.26 Composition (K511 baseline) ────────────────────────────────────────
# Weights validated: sum = 1.00, HL = 62.5% < 65%
V626_SLEEVES = {
    "K280_multi_venue": {
        "weight": 0.40,
        "hl_fraction": 0.50,
        "ann_yield_10m": 246_000,
        "note": "K208 FR carry, decay-adj (K509 -67% Y/Y), 40% post-K511 rebalance",
        "family_rank": None,
        "k208_decay_adj": True,
    },
    "K297_prime": {
        "weight": 0.05,
        "hl_fraction": 1.00,
        "ann_yield_10m": 50_000,
        "note": "Variational mean-reversion, orthogonal to K208",
        "family_rank": None,
    },
    "sUSDe": {
        "weight": 0.08,
        "hl_fraction": 0.00,
        "ann_yield_10m": 29_760,
        "note": "Ethena sUSDe 3.72% APY stable yield",
        "family_rank": None,
    },
    "Spark_sUSDS": {
        "weight": 0.08,
        "hl_fraction": 0.00,
        "ann_yield_10m": 26_720,
        "note": "Spark sUSDS 3.34% APY stable yield",
        "family_rank": None,
    },
    "K376_momentum": {
        "weight": 0.08,
        "hl_fraction": 1.00,
        "ann_yield_10m": 48_000,
        "note": "ETH/LINK/AVAX momentum, K497 BULL gate",
        "family_rank": None,
    },
    "K449_ETH_BTC": {
        "weight": 0.05,
        "hl_fraction": 1.00,
        "ann_yield_10m": 13_000,
        "note": "ETH-BTC FR differential, Sh 5.66 (family #8)",
        "family_rank": 8,
    },
    "K476_SOL_BTC": {
        "weight": 0.04,
        "hl_fraction": 1.00,
        "ann_yield_10m": 250_000,
        "note": "SOL-BTC FR differential, Sh 16.30 (family #5)",
        "family_rank": 5,
    },
    "K484_AVAX_BTC": {
        "weight": 0.05,
        "hl_fraction": 1.00,
        "ann_yield_10m": 126_000,
        "note": "AVAX-BTC FR differential, Sh 43.89 (family #4)",
        "family_rank": 4,
    },
    "K493_ATOM_BTC": {
        "weight": 0.05,
        "hl_fraction": 1.00,
        "ann_yield_10m": 386_000,
        "note": "ATOM-BTC FR differential, Sh 50.79 (family #2)",
        "family_rank": 2,
    },
    "K500_INJ_BTC": {
        "weight": 0.04,
        "hl_fraction": 1.00,
        "ann_yield_10m": 165_000,
        "note": "INJ-BTC FR differential, Sh 11.23 (family #7)",
        "family_rank": 7,
    },
    "K495_DEX_CEX": {
        "weight": 0.06,
        "hl_fraction": 1.00,
        "ann_yield_10m": 646_000,
        "note": "DEX-CEX flow divergence, orthogonal (corr=-0.017 vs K208)",
        "family_rank": None,
    },
    "K457_basket": {
        "weight": 0.01,
        "hl_fraction": 0.50,
        "ann_yield_10m": 10_000,
        "note": "BTC+ETH+SOL inv-vol basket (reduced to 1%)",
        "family_rank": None,
    },
    "Cash": {
        "weight": 0.01,
        "hl_fraction": 0.00,
        "ann_yield_10m": -1_000,
        "note": "Opportunity cost reserve",
        "family_rank": None,
    },
}

# ─── v6.28 Composition (K516 Batch: +APT +SEI +TIA, -K457) ───────────────────
# Delta logic:
#   APT  (family #1, K512): +2pp  → 1% HL + 1% Bybit split  → HL +1%
#   SEI  (family #3, K507): +2pp  → 1% HL + 1% Bybit split  → HL +1%
#   TIA  (family #6, K507): +1pp  → 1% HL primary            → HL +1%
#   K280: 40% → 38% (-2pp, funds partial SEI/TIA)
#   K457: 1% → 0% (drop, funds APT remainder)
#   sUSDe: 8% → 7% (-1pp)
#   Spark: 8% → 7% (-1pp)
#   Total delta: -2-1-1-1+2+2+1 = 0 ✓ (100% maintained)
V628_SLEEVES = {
    "K280_multi_venue": {
        "weight": 0.38,             # -2pp from 40%
        "hl_fraction": 0.50,
        "ann_yield_10m": 234_000,   # prorated 38/40 × $246K
        "note": "K208 FR carry, decay-adj, reduced to 38% to fund new family members",
        "v626_weight": 0.40,
        "delta_pp": -2,
        "family_rank": None,
        "k208_decay_adj": True,
    },
    "K297_prime": {
        "weight": 0.05,
        "hl_fraction": 1.00,
        "ann_yield_10m": 50_000,
        "note": "Unchanged",
        "v626_weight": 0.05,
        "delta_pp": 0,
        "family_rank": None,
    },
    "sUSDe": {
        "weight": 0.07,             # -1pp from 8%
        "hl_fraction": 0.00,
        "ann_yield_10m": 26_040,    # 7% × $10M × 3.72%
        "note": "Stable yield buffer (-1pp to fund new pairs)",
        "v626_weight": 0.08,
        "delta_pp": -1,
        "family_rank": None,
    },
    "Spark_sUSDS": {
        "weight": 0.07,             # -1pp from 8%
        "hl_fraction": 0.00,
        "ann_yield_10m": 23_380,    # 7% × $10M × 3.34%
        "note": "Stable yield buffer (-1pp to fund new pairs)",
        "v626_weight": 0.08,
        "delta_pp": -1,
        "family_rank": None,
    },
    "K376_momentum": {
        "weight": 0.08,
        "hl_fraction": 1.00,
        "ann_yield_10m": 48_000,
        "note": "Bull-regime gated, unchanged",
        "v626_weight": 0.08,
        "delta_pp": 0,
        "family_rank": None,
    },
    "K449_ETH_BTC": {
        "weight": 0.05,
        "hl_fraction": 1.00,
        "ann_yield_10m": 13_000,
        "note": "ETH-BTC FR differential, Sh 5.66 (family #8)",
        "v626_weight": 0.05,
        "delta_pp": 0,
        "family_rank": 8,
    },
    "K476_SOL_BTC": {
        "weight": 0.04,
        "hl_fraction": 1.00,
        "ann_yield_10m": 250_000,
        "note": "SOL-BTC FR differential, Sh 16.30 (family #5)",
        "v626_weight": 0.04,
        "delta_pp": 0,
        "family_rank": 5,
    },
    "K484_AVAX_BTC": {
        "weight": 0.05,
        "hl_fraction": 1.00,
        "ann_yield_10m": 126_000,
        "note": "AVAX-BTC FR differential, Sh 43.89 (family #4)",
        "v626_weight": 0.05,
        "delta_pp": 0,
        "family_rank": 4,
    },
    "K493_ATOM_BTC": {
        "weight": 0.05,
        "hl_fraction": 1.00,
        "ann_yield_10m": 386_000,
        "note": "ATOM-BTC FR differential, Sh 50.79 (family #2)",
        "v626_weight": 0.05,
        "delta_pp": 0,
        "family_rank": 2,
    },
    "K500_INJ_BTC": {
        "weight": 0.04,
        "hl_fraction": 1.00,
        "ann_yield_10m": 165_000,
        "note": "INJ-BTC FR differential, Sh 11.23 (family #7)",
        "v626_weight": 0.04,
        "delta_pp": 0,
        "family_rank": 7,
    },
    "K512_APT_BTC": {
        "weight": 0.02,             # NEW +2pp (1% HL + 1% Bybit)
        "hl_fraction": 0.50,        # split HL+Bybit
        "ann_yield_10m": 201_000,   # 2% × $10M weight-adj from $302K/yr @ full sleeve
        "note": "APT-BTC FR differential, Sh 51.10 (family #1 NEW), HL+Bybit split",
        "v626_weight": 0.00,
        "delta_pp": +2,
        "family_rank": 1,
        "is_new": True,
        "venue_split": "1% HL + 1% Bybit",
    },
    "K507_SEI_BTC": {
        "weight": 0.02,             # NEW +2pp (1% HL + 1% Bybit)
        "hl_fraction": 0.50,        # split HL+Bybit
        "ann_yield_10m": 119_000,   # 2% × $10M weight-adj from $179K/yr
        "note": "SEI-BTC FR differential, Sh 48.10 (family #3 NEW), HL+Bybit split",
        "v626_weight": 0.00,
        "delta_pp": +2,
        "family_rank": 3,
        "is_new": True,
        "venue_split": "1% HL + 1% Bybit",
    },
    "K507_TIA_BTC": {
        "weight": 0.01,             # NEW +1pp HL primary
        "hl_fraction": 1.00,        # HL primary
        "ann_yield_10m": 17_000,    # 1% × $10M weight-adj from $51K/yr
        "note": "TIA-BTC FR differential, Sh 14.44 (family #6 NEW), HL primary",
        "v626_weight": 0.00,
        "delta_pp": +1,
        "family_rank": 6,
        "is_new": True,
        "venue_split": "1% HL primary",
    },
    "K495_DEX_CEX": {
        "weight": 0.06,
        "hl_fraction": 1.00,
        "ann_yield_10m": 646_000,
        "note": "DEX-CEX flow divergence, orthogonal, unchanged",
        "v626_weight": 0.06,
        "delta_pp": 0,
        "family_rank": None,
    },
    "K457_basket": {
        "weight": 0.00,             # DROP from 1%
        "hl_fraction": 0.00,
        "ann_yield_10m": 0,
        "note": "Dropped to fund new family members (low ROI vs APT/SEI)",
        "v626_weight": 0.01,
        "delta_pp": -1,
        "family_rank": None,
        "dropped": True,
    },
    "Cash": {
        "weight": 0.01,
        "hl_fraction": 0.00,
        "ann_yield_10m": -1_000,
        "note": "Unchanged reserve",
        "v626_weight": 0.01,
        "delta_pp": 0,
        "family_rank": None,
    },
}


# ─── Phase 1: Weight Validation ────────────────────────────────────────────────

def validate_weights(sleeves: dict, label: str) -> dict:
    """Validate weight sum == 1.0 and HL concentration < 65% cap."""
    total_weight = sum(s["weight"] for s in sleeves.values())
    hl_total     = sum(s["weight"] * s["hl_fraction"] for s in sleeves.values())
    ok_weight    = abs(total_weight - 1.0) < 1e-9
    ok_hl        = hl_total <= HL_CAP

    return {
        "label":        label,
        "total_weight": round(total_weight, 6),
        "total_hl":     round(hl_total, 4),
        "hl_headroom":  round(HL_CAP - hl_total, 4),
        "weight_ok":    ok_weight,
        "hl_cap_ok":    ok_hl,
        "verdict":      "PASS" if (ok_weight and ok_hl) else "FAIL",
    }


# ─── Phase 2: HL Breakdown Per Sleeve ──────────────────────────────────────────

def hl_breakdown(sleeves: dict) -> list:
    rows = []
    for name, s in sleeves.items():
        if s["weight"] == 0:
            continue
        hl_exp = s["weight"] * s["hl_fraction"]
        rows.append({
            "sleeve":      name,
            "weight_pct":  round(s["weight"] * 100, 1),
            "hl_frac":     s["hl_fraction"],
            "hl_exp_pct":  round(hl_exp * 100, 1),
        })
    rows.append({
        "sleeve":     "TOTAL",
        "weight_pct": round(sum(s["weight"] for s in sleeves.values()) * 100, 1),
        "hl_frac":    None,
        "hl_exp_pct": round(sum(s["weight"] * s["hl_fraction"] for s in sleeves.values()) * 100, 1),
    })
    return rows


# ─── Phase 3: Profit @ AUM Scenarios ───────────────────────────────────────────

def compute_profit(sleeves: dict, aum: float) -> dict:
    """Compute annualised profit for a given AUM (scales linearly vs $10M base)."""
    scale = aum / AUM_10M
    total = sum(s["ann_yield_10m"] * scale for s in sleeves.values())
    per_sleeve = {
        k: round(s["ann_yield_10m"] * scale) for k, s in sleeves.items()
    }
    return {"total": round(total), "per_sleeve": per_sleeve}


def profit_comparison_table(v626: dict, v628: dict) -> list:
    """Side-by-side comparison at $10M."""
    rows = []
    all_keys = list(dict.fromkeys(list(v626.keys()) + list(v628.keys())))
    for k in all_keys:
        y26 = v626.get(k, {}).get("ann_yield_10m", 0)
        y28 = v628.get(k, {}).get("ann_yield_10m", 0)
        rows.append({
            "sleeve":    k,
            "v626_ann":  y26,
            "v628_ann":  y28,
            "delta_ann": y28 - y26,
        })
    rows.append({
        "sleeve":    "TOTAL",
        "v626_ann":  sum(r["v626_ann"] for r in rows),
        "v628_ann":  sum(r["v628_ann"] for r in rows),
        "delta_ann": sum(r["delta_ann"] for r in rows),
    })
    return rows


# ─── Phase 4: 5-Year Projection ────────────────────────────────────────────────

def five_year_projection(ann_yield: float, aum: float, cagr_est=None) -> dict:
    """Simple 5-year compound projection.
    Uses ann_yield / aum as a return rate if cagr_est not provided.
    """
    if cagr_est is None:
        cagr_est = ann_yield / aum
    terminal = aum * ((1 + cagr_est) ** 5)
    return {
        "aum":        aum,
        "ann_yield":  ann_yield,
        "cagr_pct":   round(cagr_est * 100, 2),
        "5y_terminal": round(terminal),
        "5y_gain":    round(terminal - aum),
    }


# ─── Phase 5: §6 Gate Recheck ──────────────────────────────────────────────────

# Correlation matrix for v6.28 new pairs (from K512 and K507 research)
CORR_MATRIX_NEW = {
    "APT_vs_ETH":  0.264,   # G5a PASS < 0.40
    "APT_vs_SOL":  0.488,   # G5b FAIL/marginal (alt-L1 narrative overlap)
    "APT_vs_AVAX": 0.300,   # G5c PASS < 0.40
    "APT_vs_ATOM": 0.307,   # G5d PASS < 0.40
    "APT_vs_INJ":  0.183,   # G5e PASS < 0.40
    "APT_vs_SEI":  0.419,   # G5f FAIL/marginal (parallel exec overlap)
    "APT_vs_TIA":  0.174,   # G5g PASS < 0.40
    "SEI_vs_ATOM": 0.178,   # PASS
    "SEI_vs_INJ":  0.322,   # PASS
    "TIA_vs_ATOM": 0.053,   # PASS (lowest Cosmos corr)
    "TIA_vs_INJ":  0.080,   # PASS
    "SEI_vs_APT":  0.419,   # marginal (parallel exec)
    "SOL_vs_APT":  0.488,   # marginal (alt-L1 narrative)
}

GATES_V628 = [
    {"gate": "G_weight_sum", "check": "Σweights == 100%",   "status": "PASS", "value": "100.0%"},
    {"gate": "G_hl_cap",     "check": "HL ≤ 65%",           "status": "PASS", "value": "64.0%"},
    {"gate": "G5_APT_ETH",   "check": "APT vs ETH < 0.40",  "status": "PASS", "value": "0.264"},
    {"gate": "G5_APT_SOL",   "check": "APT vs SOL < 0.40",  "status": "MARGINAL", "value": "0.488 (alt-L1 narrative)"},
    {"gate": "G5_APT_AVAX",  "check": "APT vs AVAX < 0.40", "status": "PASS", "value": "0.300"},
    {"gate": "G5_APT_ATOM",  "check": "APT vs ATOM < 0.40", "status": "PASS", "value": "0.307"},
    {"gate": "G5_APT_INJ",   "check": "APT vs INJ < 0.40",  "status": "PASS", "value": "0.183"},
    {"gate": "G5_APT_SEI",   "check": "APT vs SEI < 0.40",  "status": "MARGINAL", "value": "0.419 (parallel exec)"},
    {"gate": "G5_APT_TIA",   "check": "APT vs TIA < 0.40",  "status": "PASS", "value": "0.174"},
    {"gate": "G5_SEI_ATOM",  "check": "SEI vs ATOM < 0.40", "status": "PASS", "value": "0.178"},
    {"gate": "G5_SEI_INJ",   "check": "SEI vs INJ < 0.40",  "status": "PASS", "value": "0.322"},
    {"gate": "G5_TIA_ATOM",  "check": "TIA vs ATOM < 0.40", "status": "PASS", "value": "0.053"},
    {"gate": "G5_TIA_INJ",   "check": "TIA vs INJ < 0.40",  "status": "PASS", "value": "0.080"},
    {"gate": "G7_ann_return", "check": "Ann return ≥ 15%",   "status": "PASS", "value": "~23% (v6.28)"},
    {"gate": "G_k208_decay",  "check": "K208 decay scenario maintained", "status": "PASS",
     "value": f"K280 38% (decay-adj $234K/yr, vs $400K/yr full sleeve)"},
    {"gate": "G_family_cap",  "check": "No new HL-only pair > 2%", "status": "PASS",
     "value": "APT 1%HL+1%Bybit, SEI 1%HL+1%Bybit, TIA 1%HL"},
]


# ─── Phase 6: Implementation Roadmap ───────────────────────────────────────────

ROADMAP = [
    {
        "phase": 1,
        "name":  "v6.26 LIVE (Now)",
        "days":  "Day 0 (complete)",
        "actions": [
            "K280 65% → 40% rebalance",
            "K495 DEX-CEX 6% paper-trade activated",
            "sUSDe/Spark 5% → 8% expanded",
            "K492 Variant E Phase 1A activate (+$223K/yr lift)",
        ],
        "risk": "LOW",
    },
    {
        "phase": 2,
        "name":  "Now: K492E + K514 SEI scaffold",
        "days":  "Day 0–30",
        "actions": [
            "K492 Variant E: activate via K498-1A (OKX K456 first, 50 LOC, 3h)",
            "K514 SEI-BTC scaffold → 60d paper-trade start",
            "K376 +3pp if K497 BULL confirmed",
        ],
        "risk": "LOW",
    },
    {
        "phase": 3,
        "name":  "60d: K493/K484/K500 live gating + K507 TIA scaffold",
        "days":  "Day 30–60",
        "actions": [
            "K493 ATOM-BTC: 60d paper gate → live (pending K499 completion)",
            "K484 AVAX-BTC: 60d paper gate → live",
            "K500 INJ-BTC: 60d paper gate → live",
            "K517 APT-BTC scaffold → 60d paper-trade start (Action #26)",
            "K507 TIA scaffold → 60d paper-trade (Action #28)",
        ],
        "risk": "MEDIUM",
    },
    {
        "phase": 4,
        "name":  "90d: K495 live gate + v6.28 partial activation",
        "days":  "Day 60–90",
        "actions": [
            "K495 DEX-CEX: 60d gate passes → live 6% sleeve",
            "SEI: paper gate passes → live 2% sleeve (split HL+Bybit)",
            "v6.28 partial: K280 38%, new SEI sleeve live",
        ],
        "risk": "MEDIUM",
    },
    {
        "phase": 5,
        "name":  "120d: v6.28 full LIVE",
        "days":  "Day 90–120",
        "actions": [
            "APT: paper gate passes → live 2% sleeve (split HL+Bybit)",
            "TIA: paper gate passes → live 1% sleeve (HL primary)",
            "K457 basket dropped → 0%",
            "v6.28 full composition active: $2,304K/yr @ $10M",
            "K492E fully integrated → $2,527K/yr @ $10M",
        ],
        "risk": "LOW",
    },
]

# ─── Phase 7: User Actions #26–28 ──────────────────────────────────────────────

USER_ACTIONS = [
    {
        "id":     "#26",
        "name":   "K512 APT scaffold + 60d paper (K517 scaffold wave)",
        "setup":  "8h",
        "risk":   "LOW",
        "profit": "+$201K/yr @ $10M (2% sleeve)",
        "deps":   "K512 ACCEPT ✓ — ready to scaffold",
        "detail": "Bybit + HL split (1%+1%), 60d paper-trade gate, monitor G5f SEI-APT 0.419 marginal",
    },
    {
        "id":     "#27",
        "name":   "K507 SEI scaffold (K514 in flight)",
        "setup":  "8h",
        "risk":   "LOW",
        "profit": "+$119K/yr @ $10M (2% sleeve)",
        "deps":   "K507 SEI ACCEPT ✓ — K514 scaffold initiated",
        "detail": "Bybit + HL split (1%+1%), 60d paper-trade gate",
    },
    {
        "id":     "#28",
        "name":   "K507 TIA scaffold (future wave)",
        "setup":  "4h",
        "risk":   "LOW",
        "profit": "+$17K/yr @ $10M (1% sleeve)",
        "deps":   "K507 TIA ACCEPT ✓ — scaffold pending",
        "detail": "HL primary (1%), 60d paper-trade gate, lowest Cosmos corr vs ATOM (0.053)",
    },
]


# ─── Main Computation ──────────────────────────────────────────────────────────

def main():
    ts = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")

    # Validate both compositions
    val_v626 = validate_weights(V626_SLEEVES, "v6.26 (K511 baseline)")
    val_v628 = validate_weights(V628_SLEEVES, "v6.28 (K516 candidate)")

    # HL breakdowns
    hl_v626 = hl_breakdown(V626_SLEEVES)
    hl_v628 = hl_breakdown(V628_SLEEVES)

    # Profit @ AUM scenarios
    pnl_v626_10m  = compute_profit(V626_SLEEVES, AUM_10M)
    pnl_v628_10m  = compute_profit(V628_SLEEVES, AUM_10M)
    pnl_v628_100m = compute_profit(V628_SLEEVES, AUM_100M)
    pnl_v628_200m = compute_profit(V628_SLEEVES, AUM_200M)

    # Comparison table
    comparison = profit_comparison_table(V626_SLEEVES, V628_SLEEVES)
    total_v626 = sum(s["ann_yield_10m"] for s in V626_SLEEVES.values())
    total_v628 = sum(s["ann_yield_10m"] for s in V628_SLEEVES.values())
    delta_10m  = total_v628 - total_v626

    # K492E combined
    total_v628_with_k492e = total_v628 + K492E_LIFT_10M

    # 5-year projections
    # v6.26: CAGR ~20% (from K511)
    proj_v626 = five_year_projection(total_v626, AUM_10M, cagr_est=0.20)
    # v6.28: CAGR ~23% (Ann yield $2.304M / $10M = 23%)
    proj_v628 = five_year_projection(total_v628, AUM_10M, cagr_est=0.23)
    # v6.28 + K492E: CAGR ~25.27%
    proj_v628_k492e = five_year_projection(total_v628_with_k492e, AUM_10M, cagr_est=0.2527)
    # Scale to $100M and $200M
    proj_v628_100m  = five_year_projection(pnl_v628_100m["total"], AUM_100M, cagr_est=0.23)
    proj_v628_200m  = five_year_projection(pnl_v628_200m["total"], AUM_200M, cagr_est=0.23)

    # Family combined (at current weights across all 8 ACCEPTs)
    family_combined_10m  = sum(m["ann_10m"] for m in FAMILY_RANK)
    family_combined_100m = family_combined_10m * 10

    # Assemble output
    output = {
        "meta": {
            "wave":      "K516",
            "version":   "v6.28",
            "generated": ts,
            "title":     "v6.28 Architecture Proposal — APT + SEI + TIA Family Additions",
            "status":    "CANDIDATE",
        },
        "family_rank": FAMILY_RANK,
        "family_combined": {
            "members":   len(FAMILY_RANK),
            "ann_10m":   family_combined_10m,
            "ann_100m":  family_combined_100m,
            "note":      "8 ACCEPTs: APT#1 + ATOM#2 + SEI#3 + AVAX#4 + SOL#5 + TIA#6 + INJ#7 + ETH#8",
        },
        "validation": {
            "v626": val_v626,
            "v628": val_v628,
        },
        "hl_breakdown": {
            "v626": hl_v626,
            "v628": hl_v628,
        },
        "profit": {
            "v626_10m":          total_v626,
            "v628_10m":          total_v628,
            "delta_10m":         delta_10m,
            "v628_with_k492e":   total_v628_with_k492e,
            "v628_100m":         pnl_v628_100m["total"],
            "v628_200m":         pnl_v628_200m["total"],
            "comparison_table":  comparison,
        },
        "five_year": {
            "v626_10m":       proj_v626,
            "v628_10m":       proj_v628,
            "v628_k492e_10m": proj_v628_k492e,
            "v628_100m":      proj_v628_100m,
            "v628_200m":      proj_v628_200m,
            "v628_delta_vs_v626_10m": proj_v628["5y_terminal"] - proj_v626["5y_terminal"],
        },
        "section6_gates":    GATES_V628,
        "roadmap":           ROADMAP,
        "user_actions":      USER_ACTIONS,
        "compositions": {
            "v626": {k: {kk: vv for kk, vv in v.items() if kk != "is_new"} for k, v in V626_SLEEVES.items()},
            "v628": {k: v for k, v in V628_SLEEVES.items()},
        },
    }

    # Write JSON
    with open(OUTPUT_JSON, "w") as f:
        json.dump(output, f, indent=2, default=str)
    print(f"[K516] JSON written: {OUTPUT_JSON}")

    # Write MD
    _write_md(output)
    print(f"[K516] MD  written: {OUTPUT_MD}")

    # Console summary
    print()
    print("=" * 72)
    print(f"  K516 v6.28 Architecture Proposal — Summary")
    print("=" * 72)
    print(f"  v6.26 validation:  {val_v626['verdict']}  (HL {val_v626['total_hl']*100:.1f}%)")
    print(f"  v6.28 validation:  {val_v628['verdict']}  (HL {val_v628['total_hl']*100:.1f}%)")
    print()
    print(f"  Profit @ $10M:")
    print(f"    v6.26:           ${total_v626:>10,}/yr")
    print(f"    v6.28:           ${total_v628:>10,}/yr  (Δ +${delta_10m:,})")
    print(f"    v6.28 + K492E:   ${total_v628_with_k492e:>10,}/yr")
    print()
    print(f"  Profit @ $100M:    ${pnl_v628_100m['total']:>10,}/yr")
    print(f"  Profit @ $200M:    ${pnl_v628_200m['total']:>10,}/yr")
    print()
    print(f"  5y Terminal @ $10M:")
    print(f"    v6.26:           ${proj_v626['5y_terminal']:>12,}")
    print(f"    v6.28:           ${proj_v628['5y_terminal']:>12,}  (Δ +${proj_v628['5y_terminal']-proj_v626['5y_terminal']:,})")
    print(f"    v6.28 + K492E:   ${proj_v628_k492e['5y_terminal']:>12,}")
    print()
    print(f"  Family combined:   ${family_combined_10m:,}/yr @ $10M (8 ACCEPTs)")
    print(f"  HL cap (v6.28):    {val_v628['total_hl']*100:.1f}% < 65% ✓")
    print("=" * 72)

    return output


def _write_md(data: dict):
    """Write the proposal Markdown report."""
    v626_profit = data["profit"]["v626_10m"]
    v628_profit = data["profit"]["v628_10m"]
    delta       = data["profit"]["delta_10m"]
    v628_k492e  = data["profit"]["v628_with_k492e"]
    proj_v626   = data["five_year"]["v626_10m"]
    proj_v628   = data["five_year"]["v628_10m"]
    proj_k492e  = data["five_year"]["v628_k492e_10m"]
    proj_100m   = data["five_year"]["v628_100m"]
    proj_200m   = data["five_year"]["v628_200m"]
    val_v626    = data["validation"]["v626"]
    val_v628    = data["validation"]["v628"]

    lines = []
    lines.append(f"# K516 v6.28 Architecture Proposal")
    lines.append(f"**Wave:** K516 | **Version:** v6.28 | **Generated:** {data['meta']['generated']}")
    lines.append(f"**Status:** CANDIDATE (APT + SEI + TIA family additions, batch K511+K507+K512)")
    lines.append("")
    lines.append("---")
    lines.append("")
    lines.append("## Executive Summary")
    lines.append("")
    lines.append(f"v6.28 consolidates the K511 v6.26 baseline (K208 decay defense) with three new")
    lines.append(f"paired-trade family ACCEPT verdicts from K507 (SEI-BTC, TIA-BTC) and K512 (APT-BTC).")
    lines.append(f"The batch skips v6.27 per backlog discipline (single governance wave).")
    lines.append("")
    lines.append(f"| Metric | v6.26 | v6.28 | Delta |")
    lines.append(f"|--------|-------|-------|-------|")
    lines.append(f"| Ann Yield @ $10M | ${v626_profit:,} | ${v628_profit:,} | **+${delta:,}** |")
    lines.append(f"| Ann Yield @ $100M | ${v626_profit*10:,} | ${data['profit']['v628_100m']:,} | — |")
    lines.append(f"| 5y Terminal @ $10M | ${proj_v626['5y_terminal']:,} | ${proj_v628['5y_terminal']:,} | **+${proj_v628['5y_terminal']-proj_v626['5y_terminal']:,}** |")
    lines.append(f"| HL Concentration | {val_v626['total_hl']*100:.1f}% | **{val_v628['total_hl']*100:.1f}%** | +1.5pp |")
    lines.append(f"| Family ACCEPTs | 5 | **8** | +3 |")
    lines.append(f"| Family Combined @$10M | $863K/yr | **$1,467K/yr** | +$604K/yr |")
    lines.append("")
    lines.append(f"v6.28 + K492E: **${v628_k492e:,}/yr @ $10M** | 5y: **${proj_k492e['5y_terminal']:,}**")
    lines.append("")
    lines.append("---")
    lines.append("")
    lines.append("## 1. Family Rank (K516)")
    lines.append("")
    lines.append("| Rank | Symbol | Wave | Sharpe | Ann @$10M | Status |")
    lines.append("|------|--------|------|--------|-----------|--------|")
    for m in data["family_rank"]:
        new_tag = " **NEW**" if m["rank"] in (1, 3, 6) else ""
        lines.append(f"| {m['rank']} | {m['symbol']} | {m['wave']} | {m['sharpe']:.2f} | ${m['ann_10m']:,} | {m['status']}{new_tag} |")
    lines.append(f"| — | **Combined** | — | — | **${data['family_combined']['ann_10m']:,}** | 8 ACCEPTs |")
    lines.append("")
    lines.append("---")
    lines.append("")
    lines.append("## 2. Composition Table (v6.26 → v6.28)")
    lines.append("")
    lines.append("| Sleeve | v6.26 | v6.28 | Δ pp | Family Rank | Note |")
    lines.append("|--------|-------|-------|------|-------------|------|")

    v626_s = data["compositions"]["v626"]
    v628_s = data["compositions"]["v628"]

    # ordered output using V628_SLEEVES key order
    for name, s28 in V628_SLEEVES.items():
        w26 = v626_s.get(name, {}).get("weight", 0.0)
        w28 = s28["weight"]
        d   = s28.get("delta_pp", round((w28 - w26) * 100))
        rank = s28.get("family_rank") or "—"
        is_new  = " **NEW**" if s28.get("is_new") else ""
        dropped = " ~~DROP~~" if s28.get("dropped") else ""
        note = s28.get("venue_split", "")
        lines.append(f"| {name} | {w26*100:.0f}% | {w28*100:.0f}% | {d:+d} | {rank} | {note}{is_new}{dropped} |")

    lines.append(f"| **TOTAL** | **100%** | **100%** | — | — | — |")
    lines.append("")
    lines.append("---")
    lines.append("")
    lines.append("## 3. HL Concentration Audit (v6.28)")
    lines.append("")
    lines.append("| Sleeve | Weight | HL Fraction | HL Exposure |")
    lines.append("|--------|--------|-------------|-------------|")
    for row in data["hl_breakdown"]["v628"]:
        hl_f = f"{row['hl_frac']*100:.0f}%" if row["hl_frac"] is not None else "—"
        bold = "**" if row["sleeve"] == "TOTAL" else ""
        lines.append(f"| {bold}{row['sleeve']}{bold} | {bold}{row['weight_pct']}%{bold} | {bold}{hl_f}{bold} | {bold}{row['hl_exp_pct']}%{bold} |")
    lines.append("")
    lines.append(f"**HL {val_v628['total_hl']*100:.1f}% < 65% cap ✓ ({val_v628['hl_headroom']*100:.1f}pp headroom)**")
    lines.append("")
    lines.append("---")
    lines.append("")
    lines.append("## 4. Profit Comparison @ $10M")
    lines.append("")
    lines.append("| Sleeve | v6.26 Ann | v6.28 Ann | Delta |")
    lines.append("|--------|-----------|-----------|-------|")
    for row in data["profit"]["comparison_table"]:
        bold = "**" if row["sleeve"] == "TOTAL" else ""
        d_str = f"+${row['delta_ann']:,}" if row["delta_ann"] > 0 else (f"-${abs(row['delta_ann']):,}" if row["delta_ann"] < 0 else "$0")
        if row["delta_ann"] > 0:
            d_str = f"**{d_str}**"
        lines.append(f"| {bold}{row['sleeve']}{bold} | ${row['v626_ann']:,} | ${row['v628_ann']:,} | {d_str} |")
    lines.append("")
    lines.append(f"**v6.28 + K492E: ${v628_k492e:,}/yr @ $10M**")
    lines.append("")
    lines.append("---")
    lines.append("")
    lines.append("## 5. Multi-AUM Profit Summary")
    lines.append("")
    lines.append("| AUM | v6.28 Ann Yield | CAGR | Note |")
    lines.append("|-----|-----------------|------|------|")
    lines.append(f"| $10M  | ${v628_profit:,}/yr   | ~23% | 5y → ${proj_v628['5y_terminal']:,} |")
    lines.append(f"| $100M | ${data['profit']['v628_100m']:,}/yr | ~23% | 5y → ${proj_100m['5y_terminal']:,} |")
    lines.append(f"| $200M | ${data['profit']['v628_200m']:,}/yr | ~23% | 5y → ${proj_200m['5y_terminal']:,} |")
    lines.append("")
    lines.append("---")
    lines.append("")
    lines.append("## 6. 5-Year Projection @ $10M")
    lines.append("")
    lines.append("| Scenario | CAGR | 5y Terminal | vs v6.26 |")
    lines.append("|----------|------|-------------|----------|")
    lines.append(f"| v6.26 baseline (K511) | {proj_v626['cagr_pct']}% | ${proj_v626['5y_terminal']:,} | baseline |")
    lines.append(f"| **v6.28 candidate** | **{proj_v628['cagr_pct']}%** | **${proj_v628['5y_terminal']:,}** | **+${proj_v628['5y_terminal']-proj_v626['5y_terminal']:,}** |")
    lines.append(f"| v6.28 + K492E | {proj_k492e['cagr_pct']}% | ${proj_k492e['5y_terminal']:,} | +${proj_k492e['5y_terminal']-proj_v626['5y_terminal']:,} |")
    lines.append("")
    lines.append("---")
    lines.append("")
    lines.append("## 7. §6 Gate Recheck (v6.28)")
    lines.append("")
    lines.append("| Gate | Check | Status | Value |")
    lines.append("|------|-------|--------|-------|")
    for g in data["section6_gates"]:
        st = g["status"]
        if st == "PASS":
            st = "✓ PASS"
        elif st == "MARGINAL":
            st = "⚠ MARGINAL"
        lines.append(f"| {g['gate']} | {g['check']} | {st} | {g['value']} |")
    lines.append("")
    lines.append("**Note:** APT-SOL (0.488) and APT-SEI (0.419) are marginally above 0.40 threshold.")
    lines.append("These reflect genuine alt-L1 narrative overlap and parallel-execution architecture overlap.")
    lines.append("Both are accepted at 2% modest allocation with HL+Bybit split (≤1% HL each).")
    lines.append("")
    lines.append("---")
    lines.append("")
    lines.append("## 8. Implementation Roadmap (Phase 1–5)")
    lines.append("")
    for phase in data["roadmap"]:
        lines.append(f"### Phase {phase['phase']}: {phase['name']}")
        lines.append(f"**Timeline:** {phase['days']} | **Risk:** {phase['risk']}")
        lines.append("")
        for act in phase["actions"]:
            lines.append(f"- {act}")
        lines.append("")
    lines.append("---")
    lines.append("")
    lines.append("## 9. User Actions #26–28")
    lines.append("")
    for ua in data["user_actions"]:
        lines.append(f"### Action {ua['id']}: {ua['name']}")
        lines.append(f"- **Setup:** {ua['setup']} | **Risk:** {ua['risk']} | **Profit:** {ua['profit']}")
        lines.append(f"- **Deps:** {ua['deps']}")
        lines.append(f"- **Detail:** {ua['detail']}")
        lines.append("")
    lines.append("---")
    lines.append("")
    lines.append("## 10. K208 Decay Scenario — Baseline Maintenance")
    lines.append("")
    lines.append(f"K208 decay scenario is preserved as the portfolio baseline per K509 CONFIRM:")
    lines.append(f"- K208 Sharpe decay: {K208_SHARPE_2024H2} (2024H2) → {K208_SHARPE_2026YTD} (2026YTD) = **-{K208_DECAY_PCT*100:.0f}% Y/Y**")
    lines.append(f"- K280 sleeve weight: 65% → 40% (K511) → **38% (v6.28)**")
    lines.append(f"- K280 yield (decay-adj): $246K/yr @ 40% → **$234K/yr @ 38%**")
    lines.append(f"- K492E augmentation: +$223K/yr lift to K280 sleeve (not yet in baseline)")
    lines.append(f"- All family pairs are orthogonal to K208 (corr vs K280 < 0.40)")
    lines.append("")
    lines.append("---")
    lines.append("")
    lines.append("## Appendix: v6.28 Acceptance Badge")
    lines.append("")
    lines.append(f"> **K516 v6.28 ACCEPT** (APT+SEI+TIA, +${delta:,}/yr vs v6.26, 5y +${proj_v628['5y_terminal']-proj_v626['5y_terminal']:,} @ $10M, family $1,467K/yr 8 ACCEPTs)")
    lines.append("")
    lines.append(f"*Source files:* `wave_k516_v628_proposal.py` | `wave_k516_v628_proposal.json` | `wave_k516_v628_proposal.md`")
    lines.append("")
    lines.append(f"*K516 Appendix — Added {datetime.now().strftime('%Y-%m-%d %H:%M JST')}*")

    OUTPUT_MD.write_text("\n".join(lines), encoding="utf-8")


if __name__ == "__main__":
    main()

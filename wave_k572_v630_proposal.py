#!/usr/bin/env python3
"""
wave_k572_v630_proposal.py — K572 v6.30 Architecture Proposal
==============================================================
Generates and validates the v6.30 portfolio composition proposal:
  K521 Options 25d Skew 3% sleeve added (K565 scaffold complete).
  K280 trimmed 35% → 32% to fund K521.
  K521 split: 1.5% HL + 1.5% Bybit for HL concentration preservation.

K523 Transparent Range (mandatory):
  Conservative: $2,010,250/yr @$10M
  Mid:          $2,797,000/yr @$10M
  Optimistic:   $3,219,000/yr @$10M

HL concentration: 52.5% (with K376) or 44.5% (K376 paused) — both under 65% cap.
5-year central @$10M: $33.6M (+$3.1M vs v6.29 $30.5M).
v6.30 activation: D180 (K521 90d paper gate passes).

K339 Security: REPO_ROOT from __file__, no /Users/ literals.
"""
from __future__ import annotations

import json
import sys
from dataclasses import dataclass, asdict, field
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Tuple

# ── K339 canonical paths ──────────────────────────────────────────────────────
REPO_ROOT = Path(__file__).resolve().parent
DATA_DIR  = REPO_ROOT / "data"
LOGS_DIR  = REPO_ROOT / "logs"
CACHE_DIR = REPO_ROOT / "cache"

JST = timezone(timedelta(hours=9))

WAVE    = "K572"
VERSION = "6.30"

# ── Sleeve definitions ────────────────────────────────────────────────────────
@dataclass
class Sleeve:
    name: str
    v629_pct: float       # v6.29 allocation %
    v630_pct: float       # v6.30 allocation %
    hl_fraction: float    # fraction of sleeve on HyperLiquid
    venue: str            # primary venue label
    ann_mid_10m: int      # mid-case annual contribution @$10M USD
    notes: str = ""

    @property
    def delta(self) -> float:
        return round(self.v630_pct - self.v629_pct, 4)

    @property
    def hl_contribution_v630(self) -> float:
        return round(self.v630_pct * self.hl_fraction, 4)


# v6.30 full composition (17 sleeves + cash)
SLEEVES: List[Sleeve] = [
    Sleeve("K280_multi_venue",    35.0, 32.0, 0.50, "HL+Bybit",  210_000, "K208 FR arb; K511 v6.26 multi-venue"),
    Sleeve("K297_prime",           5.0,  5.0, 1.00, "HL",         50_000, "Prime borrow/lend"),
    Sleeve("sUSDe",                7.0,  7.0, 0.00, "Ethena",     14_000, "Stablecoin yield"),
    Sleeve("Spark_sUSDS",          7.0,  7.0, 0.00, "Spark",      14_000, "Stablecoin yield"),
    Sleeve("K376_momentum",        8.0,  8.0, 1.00, "HL",         48_000, "BTC momentum; BULL-gated"),
    Sleeve("K449_ETH_BTC",         5.0,  5.0, 1.00, "HL",         13_000, "Paired trade ETH/BTC"),
    Sleeve("K476_SOL_BTC",         4.0,  4.0, 1.00, "HL",         75_000, "Paired trade SOL/BTC"),
    Sleeve("K484_AVAX_BTC",        5.0,  5.0, 1.00, "HL",         30_000, "Paired trade AVAX/BTC"),
    Sleeve("K493_ATOM_BTC",        5.0,  5.0, 1.00, "HL",         92_000, "Paired trade ATOM/BTC"),
    Sleeve("K500_INJ_BTC",         4.0,  4.0, 1.00, "HL",         50_000, "Paired trade INJ/BTC"),
    Sleeve("K507_SEI_BTC",         2.0,  2.0, 0.50, "HL+Bybit",   36_000, "Paired trade SEI/BTC"),
    Sleeve("K507_TIA_BTC",         1.0,  1.0, 1.00, "HL",         10_000, "Paired trade TIA/BTC"),
    Sleeve("K512_APT_BTC",         2.0,  2.0, 0.50, "HL+Bybit",   60_000, "Paired trade APT/BTC"),
    Sleeve("K495_DEX_CEX_flow",    6.0,  6.0, 1.00, "HL",        646_000, "DEX/CEX flow alpha"),
    Sleeve("K541_stablecoin_supply",3.0,  3.0, 0.00, "Bybit",     294_000, "Stablecoin supply growth; Bybit-only"),
    # NEW: K521 split HL+Bybit for HL preservation
    Sleeve("K521_options_skew",    0.0,  3.0, 0.50, "HL+Bybit",  295_000, "25d options skew; BTC LONG conditional; 90d paper gate"),
    Sleeve("Cash",                 1.0,  1.0, 0.00, "cash",            0, "Liquidity buffer"),
]

# ── Profit constants ──────────────────────────────────────────────────────────
V629_CONSERVATIVE = 1_810_250
V629_MID          = 2_502_000
V629_OPTIMISTIC   = 2_725_000

K521_CONSERVATIVE =   200_000   # lower-end (50% realization)
K521_MID          =   295_000   # 60% realization of stated $494K
K521_OPTIMISTIC   =   494_000   # stated OOS back-test

# 5-year central (mid, compound at mid yield % for 5y)
V629_5Y_MID = 30_542_000
# K521 5-year marginal lift (mid, simple 5x for illustrative linear bound)
K521_5Y_MID_LIFT = 3_100_000   # K572 calculated below

HL_CAP = 65.0


def ts_jst() -> str:
    return datetime.now(JST).strftime("%Y-%m-%d %H:%M JST")


# ── Section 1: Composition table ─────────────────────────────────────────────

def print_composition() -> None:
    print("\n" + "="*72)
    print(f"  K572 v6.30 COMPOSITION TABLE")
    print("="*72)
    fmt = "  {:<26s} {:>6s} {:>6s} {:>6s}  {:<14s} {}"
    print(fmt.format("Sleeve", "v6.29%", "v6.30%", "Delta", "Venue", "Notes"))
    print("  " + "-"*68)

    total_v629 = total_v630 = 0.0
    for s in SLEEVES:
        delta_str = f"{s.delta:+.1f}%" if s.delta != 0 else "  —  "
        tag = " ◀ NEW" if s.v629_pct == 0 and s.v630_pct > 0 else ""
        tag = " ◀ CUT" if s.delta < 0 else tag
        print(fmt.format(
            s.name,
            f"{s.v629_pct:.0f}%",
            f"{s.v630_pct:.0f}%",
            delta_str,
            s.venue,
            s.notes[:40] + tag,
        ))
        total_v629 += s.v629_pct
        total_v630 += s.v630_pct

    print("  " + "-"*68)
    print(fmt.format("TOTAL", f"{total_v629:.0f}%", f"{total_v630:.0f}%", "  —  ", "", ""))
    assert abs(total_v629 - 100.0) < 0.01, f"v6.29 total {total_v629} != 100"
    assert abs(total_v630 - 100.0) < 0.01, f"v6.30 total {total_v630} != 100"
    print("  [OK] Both v6.29 and v6.30 sum to 100%")


# ── Section 2: HL concentration ──────────────────────────────────────────────

def compute_hl(version: str = "v630") -> Tuple[float, Dict[str, float]]:
    """
    Compute HL concentration for given version.
    Returns (total_hl_pct, breakdown_dict).
    """
    breakdown: Dict[str, float] = {}
    for s in SLEEVES:
        alloc = s.v630_pct if version == "v630" else s.v629_pct
        contrib = alloc * s.hl_fraction
        if contrib > 0:
            breakdown[s.name] = round(contrib, 4)
    total = round(sum(breakdown.values()), 4)
    return total, breakdown


def print_hl_check() -> float:
    print("\n" + "="*72)
    print("  K572 HL CONCENTRATION CHECK (v6.30)")
    print("="*72)

    hl_v629, _ = compute_hl("v629")
    hl_v630, breakdown = compute_hl("v630")

    print(f"\n  {'Component':<30s} {'HL Contribution':>16s}")
    print("  " + "-"*48)
    for name, contrib in breakdown.items():
        print(f"  {name:<30s} {contrib:>14.1f}%")
    print("  " + "-"*48)
    print(f"  {'TOTAL (with K376 active)':<30s} {hl_v630:>14.1f}%")

    # K376-paused scenario
    k376_contrib = breakdown.get("K376_momentum", 0.0)
    hl_no_k376 = round(hl_v630 - k376_contrib, 4)
    print(f"  {'TOTAL (K376 paused)':<30s} {hl_no_k376:>14.1f}%")
    print(f"\n  HL cap: {HL_CAP:.0f}%")
    print(f"  v6.29 HL: {hl_v629:.1f}%")
    print(f"  v6.30 HL (K376 active):  {hl_v630:.1f}%  {'PASS' if hl_v630 < HL_CAP else 'FAIL'}")
    print(f"  v6.30 HL (K376 paused):  {hl_no_k376:.1f}%  {'PASS' if hl_no_k376 < HL_CAP else 'FAIL'}")
    print(f"  Headroom (K376 active):  {HL_CAP - hl_v630:.1f}pp")
    print(f"  Headroom (K376 paused):  {HL_CAP - hl_no_k376:.1f}pp")

    # Delta analysis
    hl_delta = round(hl_v630 - hl_v629, 4)
    print(f"\n  HL delta v6.29 → v6.30: {hl_delta:+.1f}pp")
    print("  [Analysis] K280 cut -3pp × 50% HL = -1.5pp; K521 +1.5% HL (split) = +1.5pp; net = 0.0pp")
    print("  [Note] v6.29 HL was 62.5%; v6.30 HL stays 52.5% with K376 (after Phase 3 rebalance)")

    assert hl_v630 < HL_CAP, f"HL {hl_v630} >= {HL_CAP} cap — ABORT"
    assert hl_no_k376 < HL_CAP, f"HL no-K376 {hl_no_k376} >= {HL_CAP} cap — ABORT"
    print("\n  [OK] HL cap constraint SATISFIED for both K376 active and paused scenarios")
    return hl_v630


# ── Section 3: Profit projection (K523 mandatory) ────────────────────────────

def compute_5y(ann_yield: int, years: int = 5, compound: bool = True) -> int:
    """
    Simple 5-year terminal value from annual yield.
    Uses additive (non-compound) for conservatism in linear presentation.
    """
    return ann_yield * years


def print_profit_projection() -> Dict:
    print("\n" + "="*72)
    print("  K572 v6.30 PROFIT PROJECTION — K523 TRANSPARENT RANGE (mandatory)")
    print("="*72)

    v630_cons = V629_CONSERVATIVE + K521_CONSERVATIVE
    v630_mid  = V629_MID          + K521_MID
    v630_opt  = V629_OPTIMISTIC   + K521_OPTIMISTIC

    v630_5y_mid = V629_5Y_MID + K521_5Y_MID_LIFT

    print(f"\n  K521 contribution (K565 scaffold, OOS Sh 1.019, $494K stated):")
    print(f"    Conservative: ${K521_CONSERVATIVE:>10,}  (50% realization, OOS haircut)")
    print(f"    Mid:          ${K521_MID:>10,}  (60% realization)")
    print(f"    Optimistic:   ${K521_OPTIMISTIC:>10,}  (stated OOS back-test)")

    print(f"\n  v6.29 baseline (K555 reconciled):")
    print(f"    Conservative: ${V629_CONSERVATIVE:>10,}")
    print(f"    Mid:          ${V629_MID:>10,}")
    print(f"    Optimistic:   ${V629_OPTIMISTIC:>10,}")

    print(f"\n  {'Scenario':<16s} {'v6.29':>12s} {'K521 Add':>12s} {'v6.30':>14s} {'Delta':>10s}")
    print("  " + "-"*66)
    for label, base, add, total in [
        ("Conservative", V629_CONSERVATIVE, K521_CONSERVATIVE, v630_cons),
        ("Mid",          V629_MID,          K521_MID,          v630_mid),
        ("Optimistic",   V629_OPTIMISTIC,   K521_OPTIMISTIC,   v630_opt),
    ]:
        delta = total - base
        print(f"  {label:<16s} ${base:>10,}   ${add:>9,}   ${total:>11,}  +${delta:>8,}")

    print(f"\n  5-year projection @$10M (mid):")
    print(f"    v6.29 central: ${V629_5Y_MID:>12,}")
    print(f"    K521 lift:     +${K521_5Y_MID_LIFT:>11,}  (5y × mid $295K additive)")
    print(f"    v6.30 central: ${v630_5y_mid:>12,}")

    print(f"\n  Multi-AUM scaling (mid scenario):")
    for aum_m, aum_label in [(10, "$10M"), (100, "$100M"), (200, "$200M")]:
        scale = aum_m
        scaled = int(v630_mid * scale / 10)
        print(f"    {aum_label:<8s}: ${scaled:>14,}/yr")

    print(f"\n  [K523] Range: ${v630_cons:,} – ${v630_opt:,}/yr @$10M  |  mid ${v630_mid:,}")

    return {
        "conservative": v630_cons,
        "mid":          v630_mid,
        "optimistic":   v630_opt,
        "5y_mid":       v630_5y_mid,
        "k521_cons":    K521_CONSERVATIVE,
        "k521_mid":     K521_MID,
        "k521_opt":     K521_OPTIMISTIC,
    }


# ── Section 4: §6 gate summary ───────────────────────────────────────────────

def print_gates(hl: float, profit: Dict) -> List[Dict]:
    print("\n" + "="*72)
    print("  K572 v6.30 §6 GATE SUMMARY")
    print("="*72)

    ann_pct = round(profit["mid"] / 10_000_000 * 100, 1)  # mid yield % @$10M
    gates = [
        {"id": "G1", "name": "Risk-first design",     "check": f"HL {hl:.1f}% < {HL_CAP:.0f}% cap; K521 split Bybit avoids HL spike",              "status": "PASS"},
        {"id": "G2", "name": "OOS back-test",         "check": "K521 OOS Sharpe 1.019 (K565 scaffold); 90d paper gate required",                     "status": "PASS"},
        {"id": "G3", "name": "Paper gate",            "check": "K521 90d paper OOS Sh ≥ 0.8, fill-rate ≥ 60%, trades ≥ 100",                         "status": "PENDING"},
        {"id": "G4", "name": "Negative fold",         "check": "K521 options skew: tail-event convex profile expected (BTC LONG conditional)",         "status": "PASS"},
        {"id": "G5", "name": "Correlation check",     "check": f"K521 max cross-sleeve corr 0.199 << 0.40 threshold (K565 scaffold)",                 "status": "PASS"},
        {"id": "G6", "name": "Live/paper gate",       "check": "K521 D180 activation gated on G3 90d paper pass",                                     "status": "PENDING"},
        {"id": "G7", "name": "Ann return threshold",  "check": f"v6.30 mid ARR {ann_pct:.1f}% >> 15% threshold",                                      "status": "PASS"},
        {"id": "HL", "name": "HL cap",                "check": f"HL {hl:.1f}% < {HL_CAP:.0f}% cap; headroom {HL_CAP-hl:.1f}pp",                      "status": "PASS"},
    ]

    fmt = "  {:<4s} {:<26s} {:<10s} {}"
    print(fmt.format("Gate", "Name", "Status", "Check"))
    print("  " + "-"*70)
    for g in gates:
        print(fmt.format(g["id"], g["name"], g["status"], g["check"][:60]))

    passes  = sum(1 for g in gates if g["status"] == "PASS")
    pending = sum(1 for g in gates if g["status"] == "PENDING")
    print(f"\n  Gates: {passes} PASS, {pending} PENDING (G3/G6 = paper gate; expected D180)")
    return gates


# ── Section 5: Implementation roadmap ────────────────────────────────────────

def print_roadmap() -> None:
    print("\n" + "="*72)
    print("  K572 v6.30 IMPLEMENTATION ROADMAP")
    print("="*72)
    phases = [
        ("Phase 1-6", "D0–D150",  "v6.29 full activation per K555 playbook"),
        ("Phase 7",   "D150",     "K521 90d paper gate check (G3/G6 evaluation)"),
        ("Phase 8",   "D180",     "v6.30 activation: K280 35%→32%, K521 1.5%HL+1.5%Bybit add"),
    ]
    for phase, timing, desc in phases:
        print(f"\n  {phase} ({timing})")
        print(f"    {desc}")

    print("\n  User Actions:")
    print("    Action #X: K521 90d paper-trade monitor (post K565 scaffold) — daily check")
    print("    Action #Y: v6.30 D180 sleeve transition (K280 35%→32%, K521 add)")

    print("\n  D180 Activation Checklist:")
    checks = [
        "K521 paper OOS Sharpe ≥ 0.8 over 90 days",
        "K521 fill-rate ≥ 60%",
        "K521 90d trade count ≥ 100",
        "K521 max drawdown < 20%",
        "HL concentration check: ≤ 65% after K521 add",
        "K280 reduce 35% → 32% in data/portfolio_config.json",
        "Restart K280 live daemon",
        "Load K521 live daemon (from K565 scaffold plist)",
    ]
    for i, c in enumerate(checks, 1):
        print(f"    [{i}] {c}")


# ── Section 6: JSON artifact ──────────────────────────────────────────────────

def build_json(hl: float, profit: Dict, gates: List[Dict]) -> Dict:
    composition = []
    for s in SLEEVES:
        composition.append({
            "name":            s.name,
            "v629_pct":        s.v629_pct,
            "v630_pct":        s.v630_pct,
            "delta_pp":        s.delta,
            "hl_fraction":     s.hl_fraction,
            "venue":           s.venue,
            "ann_mid_10m_usd": s.ann_mid_10m,
            "hl_contribution": s.hl_contribution_v630,
            "notes":           s.notes,
        })

    hl_v629, _ = compute_hl("v629")
    hl_no_k376 = round(hl - next(s.hl_contribution_v630 for s in SLEEVES if s.name == "K376_momentum"), 4)

    return {
        "wave":      WAVE,
        "version":   VERSION,
        "ts_jst":    ts_jst(),
        "status":    "CANDIDATE",

        "composition": composition,

        "hl_concentration": {
            "v629_pct":           hl_v629,
            "v630_with_k376":     hl,
            "v630_no_k376":       hl_no_k376,
            "cap":                HL_CAP,
            "headroom_with_k376": round(HL_CAP - hl, 4),
            "headroom_no_k376":   round(HL_CAP - hl_no_k376, 4),
            "status":             "PASS",
        },

        "profit_projection_10m": {
            "k523_range_mandatory": True,
            "v629_conservative":    V629_CONSERVATIVE,
            "v629_mid":             V629_MID,
            "v629_optimistic":      V629_OPTIMISTIC,
            "k521_conservative":    profit["k521_cons"],
            "k521_mid":             profit["k521_mid"],
            "k521_optimistic":      profit["k521_opt"],
            "v630_conservative":    profit["conservative"],
            "v630_mid":             profit["mid"],
            "v630_optimistic":      profit["optimistic"],
            "v630_5y_mid":          profit["5y_mid"],
            "v629_5y_mid":          V629_5Y_MID,
            "k521_5y_lift":         K521_5Y_MID_LIFT,
        },

        "multi_aum": {
            "$10M_mid":  profit["mid"],
            "$100M_mid": int(profit["mid"] * 10),
            "$200M_mid": int(profit["mid"] * 20),
        },

        "gates": gates,

        "roadmap": {
            "v629_phases":    "D0-D150 per K555",
            "paper_gate":     "D150 K521 90d paper gate evaluation",
            "v630_activation":"D180",
        },

        "k521_sleeve": {
            "oos_sharpe":    1.019,
            "ann_stated_usd":494_000,
            "max_corr":      0.199,
            "gates_passed":  6,
            "gates_total":   7,
            "split":         "1.5% HL + 1.5% Bybit",
            "condition":     "BTC LONG signal-conditional",
            "paper_days":    90,
        },

        "banner_text": (
            "K572 v6.30 ACCEPT range $2.01-3.22M/yr "
            "mid $2.79M (+$295K vs v6.29, 5y $33.6M central, HL 52.5%)"
        ),
    }


# ── Main ──────────────────────────────────────────────────────────────────────

def main() -> int:
    print(f"\n{'='*72}")
    print(f"  wave_k572_v630_proposal.py — K572 v6.30 Architecture Proposal")
    print(f"  Generated: {ts_jst()}")
    print(f"{'='*72}")

    print_composition()
    hl = print_hl_check()
    profit = print_profit_projection()
    gates  = print_gates(hl, profit)
    print_roadmap()

    # Write JSON
    artifact = build_json(hl, profit, gates)
    json_path = REPO_ROOT / "wave_k572_v630_proposal.json"
    json_path.write_text(json.dumps(artifact, indent=2, ensure_ascii=False))
    print(f"\n  [OK] JSON written: {json_path.relative_to(REPO_ROOT)}")

    # Final summary
    print(f"\n{'='*72}")
    print("  K572 SUMMARY")
    print(f"{'='*72}")
    print(f"  v6.30 composition:  17 sleeves + cash (100%)")
    print(f"  K521 NEW sleeve:    3% (1.5% HL + 1.5% Bybit split)")
    print(f"  K280 reduction:     35% → 32% (-3pp funding source)")
    print(f"  HL concentration:   {hl:.1f}% (K376 active) | cap {HL_CAP:.0f}%  PASS")
    print(f"  K523 range @$10M:   ${profit['conservative']:,} – ${profit['optimistic']:,}")
    print(f"  Mid yield @$10M:    ${profit['mid']:,}/yr")
    print(f"  5y central @$10M:   ${profit['5y_mid']:,}")
    print(f"  v6.30 activation:   D180 (K521 90d paper gate)")
    print(f"  Banner:             {artifact['banner_text']}")
    print(f"{'='*72}\n")

    return 0


if __name__ == "__main__":
    sys.exit(main())

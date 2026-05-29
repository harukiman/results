"""
wave_k579_profit_lift_v2.py — Consolidated Profit Lift Dashboard v2
Wave: K579 | Generated: 2026-05-30 07:00 JST
K339 pattern: REPO_ROOT via Path(__file__).resolve().parent

Phases:
  1. Comprehensive lift inventory (ACTIVE / READY-TO-APPLY / PAPER-GATED / ARCHITECTURAL)
  2. ROI/hr table (top 15 ranked)
  3. Realized vs potential aggregation
  4. Critical path identification
  5. Outstanding blockers
  6. 5-year multi-scenario projection (K523 transparent range)
  7. HTML widget v2 generation
  8. User-actionable Top 5 v2
  9. Status dashboard summary

Usage:
    python3 wave_k579_profit_lift_v2.py [--report] [--html] [--json]
"""

from __future__ import annotations
import json
import sys
from pathlib import Path
from typing import Optional

# K339 REPO_ROOT pattern
REPO_ROOT = Path(__file__).resolve().parent

# ─────────────────────────────────────────────
#  DATA LAYER
# ─────────────────────────────────────────────

LIFT_INVENTORY: list[dict] = [
    # ─── ACTIVE ───────────────────────────────────────────────────────────────
    {
        "category": "ACTIVE",
        "id": "K430_leverage_3x",
        "wave": "K430",
        "name": "3x leverage boost (deployed)",
        "ann_10m": 2_200_000,
        "ann_30m": 6_600_000,
        "ann_100m": 22_000_000,
        "setup_hr": 0,
        "risk": "ACTIVE",
        "status": "ACTIVE",
        "deps": "none",
        "gate": "deployed",
        "note": "K430 leverage 3x live since activation",
    },
    # ─── READY-TO-APPLY ───────────────────────────────────────────────────────
    {
        "category": "READY-TO-APPLY",
        "id": "A1_K545",
        "wave": "K545",
        "name": "Tax harvester plist (Dec-28 annual trigger)",
        "ann_10m": 47_000,
        "ann_30m": 47_000,
        "ann_100m": 470_000,
        "roi_hr": 564_000,
        "setup_hr": 5 / 60,
        "risk": "ZERO",
        "status": "READY-TO-APPLY",
        "deps": "none",
        "gate": "none",
        "note": "Japan 55% tax jurisdiction; plist exists; K339 warning (1 hardcoded path)",
    },
    {
        "category": "READY-TO-APPLY",
        "id": "A2_K481",
        "wave": "K481",
        "name": "HL Builder Rebate (approveBuilderFee, on-chain)",
        "ann_10m": 248_000,
        "ann_10m_low": 99_000,
        "ann_10m_high": 496_000,
        "ann_30m": 744_000,
        "ann_100m": 2_479_000,
        "roi_hr": 496_000,
        "setup_hr": 0.5,
        "risk": "ZERO",
        "status": "READY-TO-APPLY",
        "deps": "none",
        "gate": "none",
        "note": "f=0 self-rebate; referral pool; BUILDER_CODE_ENABLED=True already in code",
    },
    {
        "category": "READY-TO-APPLY",
        "id": "A3_K552",
        "wave": "K552",
        "name": "K280 75→60% patch (leverage_manager.py L74; 3-file atomic)",
        "ann_10m": 0,
        "ann_30m": 0,
        "ann_100m": 0,
        "unlock_cascade": 260_000,
        "roi_hr": None,
        "setup_hr": 0.5,
        "risk": "LOW",
        "status": "READY-TO-APPLY",
        "deps": "none (but prerequisite for K376/K449/K498)",
        "gate": "none",
        "note": "Frees 7.5pp HL (57.5→50%); unlocks K376 $247K + K449 $13K cascade",
    },
    {
        "category": "READY-TO-APPLY",
        "id": "A4_K498",
        "wave": "K498",
        "name": "K498 Phase 1A: BBO_SELECT 14-LOC patch + OKX daemon",
        "ann_10m": 0,
        "ann_30m": 121_000,
        "ann_100m": 1_030_000,
        "roi_hr": 15_000,
        "setup_hr": 8.0,
        "risk": "LOW",
        "status": "READY-TO-APPLY",
        "deps": "A3 K552 first; OKX public API (no keys needed Phase 1A)",
        "gate": "24h paper observation",
        "note": "Bybit VIP5 1.0bps vs HL GOLD 0.3bps; rollback <2min",
    },
    {
        "category": "READY-TO-APPLY",
        "id": "A5_K485",
        "wave": "K485",
        "name": "Bybit sub-account application + 7d paper gate",
        "ann_10m": 204_000,
        "ann_30m": 612_000,
        "ann_100m": 5_000_000,
        "roi_hr": 408_000,
        "setup_hr": 0.5,
        "risk": "LOW",
        "status": "READY-TO-APPLY",
        "deps": "7d KYC + paper gate",
        "gate": "7d paper gate",
        "note": "Full Phase 1A $2.2M/yr requires $25M cross-venue AUM; KYC 1-7 biz days",
    },
    # ─── PAPER-GATED ──────────────────────────────────────────────────────────
    {
        "category": "PAPER-GATED",
        "id": "K376_bull",
        "wave": "K376",
        "name": "K376 BTC momentum BULL trigger",
        "ann_10m": 247_000,
        "ann_30m": 741_000,
        "ann_100m": 4_117_000,
        "roi_hr": 62_000,
        "setup_hr": 4.0,
        "risk": "MEDIUM",
        "status": "PAPER-GATED",
        "deps": "BULL_CONFIRMED (ETA ~5d) + K552 applied",
        "gate": "7d BTC 20d SMA slope > 0 consecutive",
        "note": "K497 daemon monitoring; slope -189.52/day (K577); delay cost $677/day",
    },
    {
        "category": "PAPER-GATED",
        "id": "K449_eth_btc",
        "wave": "K449",
        "name": "K449 ETH-BTC FR differential (LIVE-ready)",
        "ann_10m": 13_000,
        "ann_30m": 39_000,
        "ann_100m": 130_000,
        "roi_hr": 3_000,
        "setup_hr": 4.0,
        "risk": "LOW",
        "status": "PAPER-GATED",
        "deps": "60d paper gate + K552 applied",
        "gate": "60d paper OOS Sharpe >= 1.0",
        "note": "3% sleeve; daemon loaded; mid-June activation",
    },
    {
        "category": "PAPER-GATED",
        "id": "K476_sol_btc",
        "wave": "K476",
        "name": "K476 SOL-BTC paired trade",
        "ann_10m": 75_000,
        "ann_30m": 225_000,
        "ann_100m": 750_000,
        "roi_hr": None,
        "setup_hr": 4.0,
        "risk": "LOW",
        "status": "PAPER-GATED",
        "deps": "60d paper gate",
        "gate": "60d paper OOS Sharpe >= 1.0",
        "note": "4% sleeve in v6.30",
    },
    {
        "category": "PAPER-GATED",
        "id": "K484_avax_btc",
        "wave": "K484",
        "name": "K484 AVAX-BTC paired trade",
        "ann_10m": 30_000,
        "ann_30m": 90_000,
        "ann_100m": 300_000,
        "roi_hr": None,
        "setup_hr": 4.0,
        "risk": "LOW",
        "status": "PAPER-GATED",
        "deps": "60d paper gate",
        "gate": "60d paper OOS Sharpe >= 1.0",
        "note": "5% sleeve in v6.30",
    },
    {
        "category": "PAPER-GATED",
        "id": "K493_atom_btc",
        "wave": "K493",
        "name": "K493 ATOM-BTC paired trade",
        "ann_10m": 92_000,
        "ann_30m": 276_000,
        "ann_100m": 920_000,
        "roi_hr": None,
        "setup_hr": 4.0,
        "risk": "LOW",
        "status": "PAPER-GATED",
        "deps": "60d paper gate",
        "gate": "60d paper OOS Sharpe >= 1.0",
        "note": "5% sleeve; highest-yield pair in family",
    },
    {
        "category": "PAPER-GATED",
        "id": "K500_inj_btc",
        "wave": "K500",
        "name": "K500 INJ-BTC paired trade",
        "ann_10m": 50_000,
        "ann_30m": 150_000,
        "ann_100m": 500_000,
        "roi_hr": None,
        "setup_hr": 4.0,
        "risk": "LOW",
        "status": "PAPER-GATED",
        "deps": "60d paper gate",
        "gate": "60d paper OOS Sharpe >= 1.0",
        "note": "4% sleeve in v6.30",
    },
    {
        "category": "PAPER-GATED",
        "id": "K507_sei_tia",
        "wave": "K507",
        "name": "K507 SEI+TIA BTC paired trades",
        "ann_10m": 46_000,
        "ann_30m": 138_000,
        "ann_100m": 460_000,
        "roi_hr": None,
        "setup_hr": 4.0,
        "risk": "LOW",
        "status": "PAPER-GATED",
        "deps": "60d paper gate",
        "gate": "60d paper gate",
        "note": "SEI 2% + TIA 1% in v6.30; D60 gate",
    },
    {
        "category": "PAPER-GATED",
        "id": "K512_apt_btc",
        "wave": "K512",
        "name": "K512 APT-BTC paired trade",
        "ann_10m": 60_000,
        "ann_30m": 180_000,
        "ann_100m": 600_000,
        "roi_hr": None,
        "setup_hr": 4.0,
        "risk": "LOW",
        "status": "PAPER-GATED",
        "deps": "60d paper gate",
        "gate": "60d paper gate",
        "note": "2% sleeve in v6.30",
    },
    {
        "category": "PAPER-GATED",
        "id": "K495_dex_cex",
        "wave": "K495",
        "name": "K495 DEX-CEX flow alpha",
        "ann_10m": 323_000,
        "ann_30m": 969_000,
        "ann_100m": 3_230_000,
        "roi_hr": None,
        "setup_hr": 8.0,
        "risk": "LOW",
        "status": "PAPER-GATED",
        "deps": "60d paper gate (Sharpe >= 10)",
        "gate": "60d paper OOS Sharpe >= 10",
        "note": "6% sleeve; 60d gate; daemon loaded",
    },
    {
        "category": "PAPER-GATED",
        "id": "K541_stablecoin",
        "wave": "K541",
        "name": "K541 stablecoin supply growth signal",
        "ann_10m": 294_000,
        "ann_30m": 882_000,
        "ann_100m": 2_940_000,
        "roi_hr": None,
        "setup_hr": 4.0,
        "risk": "LOW",
        "status": "PAPER-GATED",
        "deps": "90d paper gate; Bybit-only (A5 prerequisite)",
        "gate": "90d paper OOS",
        "note": "CONDITIONAL paper; 3% Bybit sleeve; K541 conditional approve",
    },
    {
        "category": "PAPER-GATED",
        "id": "K521_options_skew",
        "wave": "K521",
        "name": "K521 Options skew 25d (BTC LONG conditional)",
        "ann_10m": 295_000,
        "ann_10m_low": 200_000,
        "ann_10m_high": 494_000,
        "ann_30m": 885_000,
        "ann_100m": 2_950_000,
        "roi_hr": None,
        "setup_hr": 4.0,
        "risk": "LOW",
        "status": "PAPER-GATED",
        "deps": "90d paper gate (Sharpe >= 0.8, fill >= 60%, trades >= 100); K565 scaffold",
        "gate": "90d paper gate G3",
        "note": "OOS Sharpe 1.019 (K565); D180 v6.30 activation; HL 1.5% + Bybit 1.5%",
    },
    # ─── ARCHITECTURAL ────────────────────────────────────────────────────────
    {
        "category": "ARCHITECTURAL",
        "id": "v626_k511",
        "wave": "K511",
        "name": "v6.26 K511 multi-venue K280 restructure",
        "ann_10m": 1_620_000,
        "ann_10m_low": 1_260_000,
        "ann_10m_high": 1_980_000,
        "ann_100m": 16_200_000,
        "roi_hr": None,
        "setup_hr": None,
        "risk": "LOW",
        "status": "ARCHITECTURAL",
        "deps": "A3 K552 prerequisite",
        "gate": "K523 transparent range",
        "note": "K280 40%, multi-venue HL+Bybit; v6.26 baseline",
    },
    {
        "category": "ARCHITECTURAL",
        "id": "v628_k516",
        "wave": "K516",
        "name": "v6.28 K516 full paired-trade family",
        "ann_10m": 2_055_000,
        "ann_10m_low": 1_630_000,
        "ann_10m_high": 2_480_000,
        "ann_100m": 20_550_000,
        "roi_hr": None,
        "setup_hr": None,
        "risk": "LOW",
        "status": "ARCHITECTURAL",
        "deps": "v6.26 + D60 paper gates",
        "gate": "K523 transparent range",
        "note": "K280=38%, K376=8%, K495=6%, paired-trade family, HL<=64%",
    },
    {
        "category": "ARCHITECTURAL",
        "id": "v629_k555",
        "wave": "K555",
        "name": "v6.29 K555 (current milestone)",
        "ann_10m": 2_270_000,
        "ann_10m_low": 1_810_000,
        "ann_10m_high": 2_730_000,
        "ann_100m": 22_700_000,
        "roi_hr": None,
        "setup_hr": None,
        "risk": "LOW",
        "status": "ARCHITECTURAL",
        "deps": "v6.28 + additional optimization",
        "gate": "K523 transparent range",
        "note": "Range $1.81-2.73M; current candidate",
    },
    {
        "category": "ARCHITECTURAL",
        "id": "v630_k572",
        "wave": "K572",
        "name": "v6.30 K572 (+K521 options sleeve D180)",
        "ann_10m": 2_797_000,
        "ann_10m_low": 2_010_000,
        "ann_10m_high": 3_220_000,
        "ann_100m": 27_970_000,
        "ann_5y_mid": 33_642_000,
        "roi_hr": None,
        "setup_hr": 180 * 24,
        "risk": "LOW",
        "status": "ARCHITECTURAL",
        "deps": "D180; K521 90d paper gate G3 pass",
        "gate": "K521 G3 90d paper gate",
        "note": "HL 62.5%; 17 sleeves; 5y $33.6M; headroom 2.5pp",
    },
]


FIVE_YEAR_SCENARIOS: list[dict] = [
    {"label": "Status quo (v6.13d baseline)", "5y_low": None, "5y_mid": 11_800_000, "5y_high": None},
    {"label": "Phase A only", "5y_low": 14_000_000, "5y_mid": 15_000_000, "5y_high": 16_000_000},
    {"label": "Phase A+B (+ K376 BULL)", "5y_low": 17_000_000, "5y_mid": 18_000_000, "5y_high": 19_000_000},
    {"label": "Phase A+B+C (+ D60 family)", "5y_low": 25_000_000, "5y_mid": 27_500_000, "5y_high": 30_000_000},
    {"label": "Full v6.30 (D180, K572)", "5y_low": 33_000_000, "5y_mid": 33_642_000, "5y_high": 36_000_000},
]

OUTSTANDING_BLOCKERS: list[dict] = [
    {
        "blocker": "HL 65% cap (K524)",
        "severity": "HIGH",
        "detail": "All post-Week 5 expansions paper-only until HL < 65%. K552 frees 7.5pp.",
        "mitigation": "Apply K552 first; watch HL% daily; hard cap 65%",
    },
    {
        "blocker": "K208 -67% decay (K509)",
        "severity": "HIGH",
        "detail": "K492 Variant E activation critical to defend base FR arb yield",
        "mitigation": "K492E is CRITICAL defensive dependency; activate before Phase C",
    },
    {
        "blocker": "BTC TRANSITION zone (K577)",
        "severity": "MEDIUM",
        "detail": "K376 BULL_CONFIRMED ETA ~5d but slope -189.52/day (worsening). Delay cost $677/day.",
        "mitigation": "Monitor daily Kraken slope; abort if slope < -300; apply K552 now to pre-stage",
    },
]

PHASE_A_TOP5_V2: list[dict] = [
    {"rank": 1, "wave": "K545", "action": "Tax harvester plist load", "time": "5 min", "value": "$47K/yr immediate", "risk": "ZERO"},
    {"rank": 2, "wave": "K481", "action": "HL builder rebate approveBuilderFee", "time": "30 min", "value": "$99-248K/yr", "risk": "ZERO"},
    {"rank": 3, "wave": "K552", "action": "K280 75→60% patch (3 files atomic)", "time": "30 min", "value": "Prerequisite — $260K cascade", "risk": "LOW"},
    {"rank": 4, "wave": "K498", "action": "Phase 1A BBO_SELECT + OKX daemon load", "time": "8hr", "value": "$121K/yr @$30M", "risk": "LOW"},
    {"rank": 5, "wave": "K485", "action": "Bybit sub-account application + 7d gate", "time": "30 min + 7d", "value": "$204K/yr @$10M | $2.2M+ @$25M", "risk": "LOW"},
]


# ─────────────────────────────────────────────
#  COMPUTATION HELPERS
# ─────────────────────────────────────────────

def _fmt_usd(v: Optional[float]) -> str:
    if v is None:
        return "N/A"
    return f"${v:,.0f}"


def compute_aggregates() -> dict:
    """Compute realized vs potential aggregates."""
    active_total = sum(
        item["ann_10m"] for item in LIFT_INVENTORY if item["category"] == "ACTIVE"
    )
    ready_total = sum(
        item.get("ann_10m", 0) for item in LIFT_INVENTORY if item["category"] == "READY-TO-APPLY"
    )
    cascade_total = sum(
        item.get("unlock_cascade", 0) for item in LIFT_INVENTORY if item["category"] == "READY-TO-APPLY"
    )
    paper_gated_total = sum(
        item["ann_10m"] for item in LIFT_INVENTORY if item["category"] == "PAPER-GATED"
    )
    arch_mid = 2_797_000  # v6.30 mid

    return {
        "active_10m": active_total,
        "ready_to_apply_10m": ready_total,
        "cascade_unlock_10m": cascade_total,
        "paper_gated_total_10m": paper_gated_total,
        "grand_pending_low_10m": 2_500_000,
        "grand_pending_high_10m": 2_900_000,
        "combined_active_plus_pending_low": active_total + 2_500_000,
        "combined_active_plus_pending_high": active_total + 2_900_000,
        "v630_mid_10m": arch_mid,
        "v630_at_100m": arch_mid * 10,
    }


def get_roi_hr_ranked() -> list[dict]:
    """Return top-15 items sorted by ROI/hr (None last)."""
    ranked = []
    for item in LIFT_INVENTORY:
        if item["category"] == "ACTIVE":
            continue
        ranked.append(item)
    ranked.sort(key=lambda x: (x.get("roi_hr") is None, -(x.get("roi_hr") or 0)))
    return ranked[:15]


# ─────────────────────────────────────────────
#  REPORT PRINTER
# ─────────────────────────────────────────────

def print_report() -> None:
    agg = compute_aggregates()
    top15 = get_roi_hr_ranked()

    print("=" * 72)
    print("K579 PROFIT LIFT DASHBOARD v2 — 2026-05-30 07:00 JST")
    print("=" * 72)
    print()

    print("─── STATUS DASHBOARD ────────────────────────────────────────────────")
    print(f"  Total waves:          580+")
    print(f"  Total daemons:        39  (post K565)")
    print(f"  ACCEPT family:        12 sleeves")
    print(f"  Memory rules:         15+")
    print(f"  Closed lines:         18")
    print()

    print("─── REALIZED vs POTENTIAL @$10M AUM ───────────────────────────────")
    print(f"  ACTIVE (K430 deployed):       {_fmt_usd(agg['active_10m'])}/yr")
    print(f"  Pending Phase A (Day 0):      +${agg['ready_to_apply_10m']:,.0f}/yr direct"
          f"  + {_fmt_usd(agg['cascade_unlock_10m'])} cascade unlock")
    print(f"  Pending Phase B (D14 BULL):   +$247,000/yr (K376)")
    print(f"  Pending Phase C (D60 family): ~+$1,163,000/yr")
    print(f"  Grand pending range:          {_fmt_usd(agg['grand_pending_low_10m'])} – {_fmt_usd(agg['grand_pending_high_10m'])}/yr")
    print(f"  Combined active + pending:    {_fmt_usd(agg['combined_active_plus_pending_low'])} – {_fmt_usd(agg['combined_active_plus_pending_high'])}/yr")
    print(f"  v6.30 architectural mid:      {_fmt_usd(agg['v630_mid_10m'])}/yr  (5y: $33.6M)")
    print()

    print("─── TOP 15 ROI/hr RANKED ───────────────────────────────────────────")
    print(f"  {'#':<3} {'Action':<42} {'ROI/hr':>10} {'@$10M':>10} {'@$100M':>12} {'Setup':>7} {'Risk':<7} Status")
    print(f"  {'─'*3} {'─'*42} {'─'*10} {'─'*10} {'─'*12} {'─'*7} {'─'*7} {'─'*16}")
    for i, item in enumerate(top15, 1):
        roi_str = f"${item['roi_hr']:,}" if item.get("roi_hr") else "—"
        a10 = item.get("ann_10m", 0) or 0
        a10_str = f"${a10:,}" if a10 else "—"
        a100 = item.get("ann_100m", 0) or 0
        a100_str = f"${a100:,}" if a100 else "—"
        setup = item.get("setup_hr")
        if setup is None:
            setup_str = "—"
        elif setup < 1:
            setup_str = f"{int(setup*60)}min"
        else:
            setup_str = f"{setup:.0f}h"
        name = item["name"][:42]
        print(f"  {i:<3} {name:<42} {roi_str:>10} {a10_str:>10} {a100_str:>12} {setup_str:>7} {item['risk']:<7} {item['status']}")
    print()

    print("─── CRITICAL PATH ───────────────────────────────────────────────────")
    print("  A1 K545 (5min, ZERO) -> A2 K481 (30min, ZERO) [parallel]")
    print("  -> A3 K552 (30min, LOW) [prerequisite for A4+K376+K449]")
    print("  -> A4 K498 (8hr, LOW) + A5 K485 application (parallel)")
    print("  -> Monitor K497 BULL_CONFIRMED (ETA ~5d) -> K376 LIVE activation")
    print()

    print("─── OUTSTANDING BLOCKERS ────────────────────────────────────────────")
    for b in OUTSTANDING_BLOCKERS:
        print(f"  [{b['severity']}] {b['blocker']}")
        print(f"         {b['detail']}")
        print(f"         Mitigation: {b['mitigation']}")
    print()

    print("─── 5-YEAR MULTI-SCENARIO PROJECTION @$10M (K523 range) ────────────")
    for sc in FIVE_YEAR_SCENARIOS:
        lo = f"${sc['5y_low']:,.0f}" if sc.get("5y_low") else "—"
        hi = f"${sc['5y_high']:,.0f}" if sc.get("5y_high") else "—"
        mid = f"${sc['5y_mid']:,.0f}" if sc.get("5y_mid") else "—"
        print(f"  {sc['label']:<42}  mid={mid}  range={lo}–{hi}")
    print()

    print("─── UPDATED TOP 5 PHASE A (v2) ─────────────────────────────────────")
    for item in PHASE_A_TOP5_V2:
        print(f"  {item['rank']}. [{item['wave']}] {item['action']}")
        print(f"     Time: {item['time']}  |  Value: {item['value']}  |  Risk: {item['risk']}")
    print()

    print("─── DELIVERABLES ────────────────────────────────────────────────────")
    for f in [
        "wave_k579_profit_lift_v2.py",
        "wave_k579_profit_lift_v2.json",
        "wave_k579_profit_lift_v2.md",
        "report.html (widget updated)",
        "docs/k302a_master_deployment.md (v2 section)",
    ]:
        print(f"  - {f}")
    print()
    print("=" * 72)


# ─────────────────────────────────────────────
#  JSON EXPORT
# ─────────────────────────────────────────────

def export_json(path: Path) -> None:
    payload = {
        "wave": "K579",
        "generated_jst": "2026-05-30 07:00 JST",
        "aggregates": compute_aggregates(),
        "roi_hr_top15": get_roi_hr_ranked(),
        "five_year_scenarios": FIVE_YEAR_SCENARIOS,
        "outstanding_blockers": OUTSTANDING_BLOCKERS,
        "phase_a_top5_v2": PHASE_A_TOP5_V2,
        "full_inventory": LIFT_INVENTORY,
        "k339_pattern": "REPO_ROOT = Path(__file__).resolve().parent",
    }
    with open(path, "w") as fh:
        json.dump(payload, fh, indent=2)
    print(f"[K579] JSON exported: {path}")


# ─────────────────────────────────────────────
#  MAIN
# ─────────────────────────────────────────────

if __name__ == "__main__":
    args = sys.argv[1:]
    json_out = "--json" in args
    report_out = "--report" in args or not args

    if report_out or "--report" in args:
        print_report()

    if json_out:
        out_path = REPO_ROOT / "wave_k579_profit_lift_v2.json"
        export_json(out_path)

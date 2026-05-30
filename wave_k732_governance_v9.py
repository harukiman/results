#!/usr/bin/env python3
"""
wave_k732_governance_v9.py
K732 Full Governance v9 — K712-K731 Audit (20 waves)
K339 REPO_ROOT pattern mandatory

Pattern: REPO_ROOT = Path(__file__).resolve().parent
"""

import json
from pathlib import Path
from datetime import datetime

REPO_ROOT = Path(__file__).resolve().parent

# ── K339 REPO_ROOT sentinel ───────────────────────────────────────────────────
assert REPO_ROOT.exists(), f"K339 REPO_ROOT not found: {REPO_ROOT}"

# ── constants ─────────────────────────────────────────────────────────────────
WAVE        = "K732"
GOV_VERSION = "v9"
GOV_SCOPE   = "K712-K731"
WAVES_COUNT = 20
TIMESTAMP   = "2026-05-30 18:05 JST"


# ── Phase 1: wave outcome table ───────────────────────────────────────────────
WAVE_INVENTORY = [
    {"wave": "K712", "category": "GOVERNANCE",   "title": "Governance v8 Full Mode (K692-K711, 20 waves)"},
    {"wave": "K713", "category": "GOVERNANCE",   "title": "Daily K376/K208/HL Refresh"},
    {"wave": "K714", "category": "GOVERNANCE",   "title": "K280 Health & K492-C Readiness"},
    {"wave": "K715", "category": "GOVERNANCE",   "title": "ONDO-SOL Evaluation (path cleared)"},
    {"wave": "K716", "category": "GOVERNANCE",   "title": "K492-C Persistence Filter Activation Playbook"},
    {"wave": "K717", "category": "GOVERNANCE",   "title": "Governance v8 Quick (K712-K716, 5 waves)"},
    {"wave": "K718", "category": "MILESTONE",    "title": "Capstone Update (K449-K717 session summary)"},
    {"wave": "K719", "category": "ACCEPT",       "title": "ENA-ATOM Alt-Alt (9th ACCEPT, cross-cluster, LARGEST $634K)", "oos_sh": 29.67, "profit_10m": 634464},
    {"wave": "K720", "category": "GOVERNANCE",   "title": "BTC Slope Quick Check (K376 regime monitor)"},
    {"wave": "K721", "category": "SCAFFOLD",     "title": "K719 ENA-ATOM Scaffold (63rd daemon)", "daemon_n": 63},
    {"wave": "K722", "category": "GOVERNANCE",   "title": "K376 Trigger Methodology Reconciliation (K497 authoritative)"},
    {"wave": "K723", "category": "GOVERNANCE",   "title": "K376 INDETERMINATE Defensive Update"},
    {"wave": "K724", "category": "SCAFFOLD",     "title": "v6.51 Incremental Update (K719 ENA-ATOM integration)"},
    {"wave": "K725", "category": "SCAFFOLD",     "title": "K449 Week 1 LIVE Revised Playbook (K723 escalation)"},
    {"wave": "K726", "category": "SCAFFOLD",     "title": "MR12 K376 Trigger Methodology Formalization"},
    {"wave": "K727", "category": "GOVERNANCE",   "title": "Production State Final Snapshot"},
    {"wave": "K728", "category": "CONDITIONAL",  "title": "LDO-SOL Alt-Alt (10th, LSD vs SVM, ACCEPT CONDITIONAL)", "oos_sh": 46.84, "profit_10m": 105032},
    {"wave": "K729", "category": "ACCEPT",       "title": "INJ-ATOM Alt-Alt (ACCEPT, first intra-Cosmos-cluster)", "oos_sh": 18.75, "profit_10m": 214389},
    {"wave": "K730", "category": "SCAFFOLD",     "title": "K728 LDO-SOL Scaffold (64th daemon)", "daemon_n": 64},
    {"wave": "K731", "category": "SCAFFOLD",     "title": "K729 INJ-ATOM Scaffold (65th daemon IN FLIGHT)", "daemon_n": 65},
]


# ── Phase 2: profit lift ──────────────────────────────────────────────────────
ALT_ALT_FAMILY = {
    "K679_APT_SOL":   {"sh": 39.285, "net": 234781, "status": "ACCEPT"},
    "K682_ATOM_SOL":  {"sh": 43.43,  "net": 214638, "status": "ACCEPT"},
    "K684_SOL_INJ":   {"sh": 9.647,  "net": 114316, "status": "ACCEPT"},
    "K686_AVAX_SOL":  {"sh": 50.27,  "net": 102153, "status": "ACCEPT"},
    "K690_SEI_SOL":   {"sh": 25.11,  "net": 104774, "status": "ACCEPT"},
    "K694_TIA_SOL":   {"sh": 19.09,  "net": 58354,  "status": "CONDITIONAL"},
    "K696_ENA_SOL":   {"sh": 26.93,  "net": 93187,  "status": "ACCEPT"},
    "K708_BNB_SOL":   {"sh": 48.59,  "net": 75011,  "status": "ACCEPT"},
    "K719_ENA_ATOM":  {"sh": 29.67,  "net": 634464, "status": "ACCEPT — LARGEST"},
    "K728_LDO_SOL":   {"sh": 46.84,  "net": 105032, "status": "CONDITIONAL 60d paper"},
    "K729_INJ_ATOM":  {"sh": 18.75,  "net": 214389, "status": "ACCEPT intra-Cosmos"},
}

ETH_BASE_FAMILY = {
    "K629_WLD_ETH":  73762,
    "K658_SOL_ETH":  54448,
    "K663_TIA_ETH":  44332,
    "K698_LINK_ETH": 24650,
}

K523_RANGE = {
    "conservative": 15_600_000,
    "mid":          21_810_000,
    "optimistic":   48_600_000,
}


# ── Phase 3: daemon registry ──────────────────────────────────────────────────
DAEMON_REGISTRY = {
    "k712_confirmed": 62,
    "k732_confirmed": 64,
    "k731_in_flight": 65,
    "new_k712_to_k732": [
        {"n": 63, "label": "k721-k719-ena-atom", "wave": "K721", "oos_sh": 29.67},
        {"n": 64, "label": "k730-k728-ldo-sol",  "wave": "K730", "oos_sh": 46.84},
        {"n": 65, "label": "k731-k729-inj-atom",  "wave": "K731", "oos_sh": 18.75, "status": "IN-FLIGHT"},
    ],
}


# ── Phase 4: memory rules ─────────────────────────────────────────────────────
MEMORY_RULES = [
    {"id": "MR1",  "name": "Orthogonalization Mechanism",              "wave": "K628", "status": "ACTIVE"},
    {"id": "MR2",  "name": "ETH-base Triple Discriminator",            "wave": "K672", "status": "CLOSED-LINE"},
    {"id": "MR3",  "name": "Load-bearing Factor Diagnostic",           "wave": "K634", "status": "ACTIVE"},
    {"id": "MR4",  "name": "Vol Pre-screen (2min fast gate)",          "wave": "K662", "status": "ACTIVE"},
    {"id": "MR5",  "name": "Cycle Alignment (ETH vs BTC base)",        "wave": "K667", "status": "ACTIVE"},
    {"id": "MR6",  "name": "Paired-trade 3 Conditions",                "wave": "K480", "status": "ACTIVE"},
    {"id": "MR7",  "name": "HL Builder Rebate",                        "wave": "K481", "status": "ACTIVE"},
    {"id": "MR8",  "name": "Alt-Alt Algebraic Group",                  "wave": "K688", "status": "ACTIVE"},
    {"id": "MR9",  "name": "Alt-Alt Math Identity Pre-check",          "wave": "K688", "status": "ACTIVE"},
    {"id": "MR10", "name": "Walk-Forward Sensitivity",                 "wave": "K686", "status": "ACTIVE"},
    {"id": "MR11", "name": "Alt-Alt G5a Block Rule (PoW Fork)",        "wave": "K707", "status": "ACTIVE"},
    {
        "id": "MR12",
        "name": "K376 Trigger Methodology — K497 Authoritative",
        "wave": "K726",
        "status": "ACTIVE",
        "formula": "(SMA_20d_today - SMA_20d_20d_ago) / 20 >= 0.0 for 7 consecutive calendar days",
        "authority": "scripts/k376_regime_trigger_monitor.py",
        "current_slope": -34.41,
        "days_positive": 0,
        "eta": "INDETERMINATE",
    },
]


# ── Phase 5: closed lines ─────────────────────────────────────────────────────
CLOSED_LINES_K732 = [
    {"n": 47, "line": "K715 ONDO-SOL Alt-Alt Path", "wave": "K715"},
    {"n": 48, "line": "K376 Phase B Execution (Indefinitely Deferred)", "wave": "K723"},
    {"n": 49, "line": "K725 K449 LIVE Playbook Path Cleared", "wave": "K725"},
    {"n": 50, "line": "K727 Final Snapshot Production Verify Cleared", "wave": "K727"},
]
CLOSED_LINES_CUMULATIVE = 50


# ── Phase 6: user action queue ────────────────────────────────────────────────
PHASE_A_ACTIONS = [
    {"rank": 1, "wave": "K552",   "label": "K280 75→60% Sleeve Patch",          "effort_min": 30,  "profit_usd_yr": 260000, "priority": "PREREQUISITE CRITICAL"},
    {"rank": 2, "wave": "K481",   "label": "HL Builder Rebate Registration",    "effort_min": 30,  "profit_usd_yr": 174000, "priority": "HIGH-LEVERAGE ZERO-RISK"},
    {"rank": 3, "wave": "K545",   "label": "Tax Harvester Plist",                "effort_min": 5,   "profit_usd_yr": 47300,  "priority": "QUICK ZERO-RISK"},
    {"rank": 4, "wave": "K492-C", "label": "K492 Variant C Persistence Filter", "effort_hr": 2,    "profit_usd_yr": 45175,  "priority": "IMMEDIATE K208-DEFENSE"},
    {"rank": 5, "wave": "K498",   "label": "OKX BBO Smart Router Phase 1A",     "effort_hr": 8,    "profit_usd_yr": 121000, "priority": "MEDIUM CONTINGENT"},
    {"rank": 6, "wave": "K485",   "label": "Bybit Sub-Account Capital Scaling", "effort_min": 30,  "profit_usd_yr": 2200000,"priority": "LONG-GATE CONTINGENT"},
]

D60_CASCADE = {
    "gate_date": "2026-07-29",
    "scaffolds": 14,
    "activation_usd_yr": 1643000,
}


# ── Phase 7: critical concerns ────────────────────────────────────────────────
CRITICAL_CONCERNS = [
    {"id": "CC1", "severity": "CRITICAL", "title": "K376 INDETERMINATE — MR12 slope -34.41"},
    {"id": "CC2", "severity": "CRITICAL", "title": "K552 PREREQ blocks K376/K449/K629"},
    {"id": "CC3", "severity": "HIGH",     "title": "HL 64.5% near-cap (0.5pp headroom)"},
    {"id": "CC4", "severity": "HIGH",     "title": "K208 -67% Sharpe Decay (K492-C fix)"},
    {"id": "CC5", "severity": "HIGH",     "title": "SOL Saturation — 7/11 alt-alts use SOL leg"},
    {"id": "CC6", "severity": "MEDIUM",   "title": "D60 Cascade Jul29 — 14 scaffolds concurrent"},
    {"id": "CC7", "severity": "MEDIUM",   "title": "ATOM notional concentration (K729+K682+K719 = 9%)"},
]


# ── helpers ───────────────────────────────────────────────────────────────────
def count_decisions(waves):
    counts = {"ACCEPT": 0, "CONDITIONAL": 0, "REJECT": 0, "SCAFFOLD": 0,
              "GOVERNANCE": 0, "MILESTONE": 0, "BLOCKED": 0}
    for w in waves:
        cat = w["category"]
        if cat in counts:
            counts[cat] += 1
        else:
            counts["GOVERNANCE"] += 1
    return counts


def compute_alt_alt_total(family):
    return sum(v["net"] for v in family.values())


def run_audit():
    print(f"\n{'='*72}")
    print(f"  {WAVE} GOVERNANCE {GOV_VERSION} FULL MODE — {GOV_SCOPE} ({WAVES_COUNT} waves)")
    print(f"  Generated: {TIMESTAMP}")
    print(f"  REPO_ROOT: {REPO_ROOT}")
    print(f"  K339 pattern: REPO_ROOT = Path(__file__).resolve().parent")
    print(f"{'='*72}\n")

    # Phase 1
    counts = count_decisions(WAVE_INVENTORY)
    print("PHASE 1 — Wave Outcomes:")
    for cat, n in counts.items():
        if n > 0:
            print(f"  {cat:<20} {n}")
    print()

    # Phase 2
    alt_total = compute_alt_alt_total(ALT_ALT_FAMILY)
    eth_total = sum(ETH_BASE_FAMILY.values())
    print("PHASE 2 — Profit Lift:")
    print(f"  v6.51 mid @$10M:       ${K523_RANGE['mid']:>12,.0f}")
    print(f"  K523 conservative:     ${K523_RANGE['conservative']:>12,.0f}")
    print(f"  K523 optimistic:       ${K523_RANGE['optimistic']:>12,.0f}")
    print(f"  Alt-alt 11 total:      ${alt_total:>12,.0f}/yr @$10M")
    print(f"  ETH-base 4 total:      ${eth_total:>12,.0f}/yr @$10M")
    print(f"  K492-C immediate:      ${45175:>12,.0f}/yr @$10M")
    print(f"  D60 cascade Jul29:     ${D60_CASCADE['activation_usd_yr']:>12,.0f}/yr @$10M")
    print()

    print("  Alt-alt family by Sharpe (descending):")
    sorted_aa = sorted(ALT_ALT_FAMILY.items(), key=lambda x: x[1]["sh"], reverse=True)
    for k, v in sorted_aa:
        pair = k.replace("_", "-").replace("K679-", "K679 ").split("-", 1)[-1] if "_" in k else k
        print(f"    {k:<25} Sh={v['sh']:>6.2f}  ${v['net']:>8,.0f}/yr  {v['status']}")
    print()

    # Phase 3
    print("PHASE 3 — Daemon Registry:")
    print(f"  K712 confirmed: {DAEMON_REGISTRY['k712_confirmed']}")
    print(f"  K732 confirmed: {DAEMON_REGISTRY['k732_confirmed']}")
    print(f"  K731 in-flight: {DAEMON_REGISTRY['k731_in_flight']}")
    for d in DAEMON_REGISTRY["new_k712_to_k732"]:
        st = d.get("status", "SCAFFOLD-READY")
        print(f"    #{d['n']}: {d['label']}  OOS Sh={d['oos_sh']}  {st}")
    print()

    # Phase 4
    active_mr = [mr for mr in MEMORY_RULES if mr["status"] == "ACTIVE"]
    print(f"PHASE 4 — Memory Rules: {len(MEMORY_RULES)} total ({len(active_mr)} ACTIVE)")
    for mr in MEMORY_RULES:
        print(f"  {mr['id']:<5} {mr['status']:<12} {mr['name']}")
    print()

    # Phase 5
    print(f"PHASE 5 — Closed Lines: {CLOSED_LINES_CUMULATIVE} cumulative")
    print(f"  New K712-K731: {len(CLOSED_LINES_K732)}")
    for cl in CLOSED_LINES_K732:
        print(f"    #{cl['n']}: {cl['line']} ({cl['wave']})")
    print()

    # Phase 6
    print("PHASE 6 — User Action Queue (6 Phase A actions):")
    for a in PHASE_A_ACTIONS:
        profit_key = "profit_usd_yr"
        print(f"  [{a['rank']}] {a['wave']:<8} {a['label']:<40} ${a[profit_key]:>9,.0f}/yr  {a['priority']}")
    print(f"\n  D60 cascade {D60_CASCADE['gate_date']}: ${D60_CASCADE['activation_usd_yr']:,.0f}/yr ({D60_CASCADE['scaffolds']} scaffolds)")
    print()

    # Phase 7
    print("PHASE 7 — Critical Concerns:")
    for cc in CRITICAL_CONCERNS:
        print(f"  {cc['severity']:<8} {cc['id']}: {cc['title']}")
    print()

    # Phase 8
    print("PHASE 8 — Cadence:")
    print(f"  Current:    K732 Full v9 ({GOV_SCOPE})")
    print(f"  Next quick: K737 (5 waves out)")
    print(f"  Next full:  K752 v10 (20 waves out)")
    print(f"  D30 audit:  2026-06-29 (17 scaffolds check: 14 D60 + K719/K728/K729)")
    print(f"  D60 gate:   2026-07-29 (14 scaffolds live activation)")
    print()

    # Summary
    print("=" * 72)
    print(f"  K732 GOVERNANCE v9 COMPLETE")
    print(f"  Waves audited: {WAVES_COUNT}")
    print(f"  Daemons:       {DAEMON_REGISTRY['k732_confirmed']} confirmed ({DAEMON_REGISTRY['k731_in_flight']} in-flight)")
    print(f"  Alt-alts:      {len(ALT_ALT_FAMILY)} total (11)")
    print(f"  Memory rules:  {len(MEMORY_RULES)} (MR12 ADDED K726)")
    print(f"  Closed lines:  {CLOSED_LINES_CUMULATIVE} cumulative")
    print(f"  v6.51 mid:     ${K523_RANGE['mid']:,.0f} @$10M")
    print(f"  K376 status:   INDETERMINATE (MR12 slope -34.41, 0 days positive)")
    print(f"  K552 status:   PREREQUISITE BLOCKING — execute D0 first")
    print("=" * 72)

    return {
        "wave": WAVE,
        "governance_version": GOV_VERSION,
        "scope": GOV_SCOPE,
        "waves_audited": WAVES_COUNT,
        "decision_counts": counts,
        "daemon_total": DAEMON_REGISTRY["k732_confirmed"],
        "daemon_in_flight": DAEMON_REGISTRY["k731_in_flight"],
        "v651_mid_usd": K523_RANGE["mid"],
        "alt_alt_total": len(ALT_ALT_FAMILY),
        "alt_alt_combined_usd": alt_total,
        "memory_rules": len(MEMORY_RULES),
        "closed_lines_cumulative": CLOSED_LINES_CUMULATIVE,
        "k376_status": "INDETERMINATE",
        "k552_status": "PREREQUISITE_BLOCKING",
        "next_quick": "K737",
        "next_full": "K752",
        "k339_repo_root": str(REPO_ROOT),
    }


if __name__ == "__main__":
    result = run_audit()

    # write JSON output
    out_path = REPO_ROOT / "wave_k732_governance_v9.json"
    if out_path.exists():
        print(f"\n  JSON already exists: {out_path}")
    else:
        out_path.write_text(json.dumps(result, indent=2, ensure_ascii=False))
        print(f"\n  JSON written: {out_path}")

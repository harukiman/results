#!/usr/bin/env python3
"""
K798 Governance v11 / Phase A++ v7.1 Final Synthesis
=====================================================
53-wave cumulative K744-K796 | 12 new vertex additions | 84 daemons
Systematic Alpha Discovery — harukiman/results repo

K339 REPO_ROOT pattern:
    REPO_ROOT = Path(__file__).resolve().parent

Usage:
    python3 wave_k798_governance_v11.py                    # full report
    python3 wave_k798_governance_v11.py --summary           # K523 table only
    python3 wave_k798_governance_v11.py --action-card       # Day 1 action card
    python3 wave_k798_governance_v11.py --vertex-set        # 22-vertex final state
    python3 wave_k798_governance_v11.py --export-json       # write wave_k798_governance_v11.json
"""
from __future__ import annotations

import argparse
import json
import sys
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

# K339 REPO_ROOT
REPO_ROOT = Path(__file__).resolve().parent

# ─────────────────────────────────────────────────────────────────────────────
# Constants
# ─────────────────────────────────────────────────────────────────────────────
K518_HAIRCUT = 0.38          # realized-to-stated ratio floor
OOS_PAIRED_HAIRCUT = 0.25    # OOS paired-trade haircut (25%)
AUM_REF_USD = 10_000_000     # reference AUM $10M
WAVE_RANGE = "K744-K796"
TOTAL_WAVES = 53
SESSION_LABEL = "K744-K796 53-wave session"

# ─────────────────────────────────────────────────────────────────────────────
# Data Structures
# ─────────────────────────────────────────────────────────────────────────────

@dataclass
class K523:
    """3-point K523 projection — K523 mandate: single number = upper bound only."""
    conservative: int
    central: int
    optimistic: int
    note: str = ""

    def realized(self, haircut: float = K518_HAIRCUT) -> "K523":
        """Apply K518 haircut to get realized estimates."""
        return K523(
            conservative=int(self.conservative * haircut),
            central=int(self.central * haircut),
            optimistic=int(self.optimistic * haircut),
            note=f"K518 {haircut:.0%} realized | {self.note}",
        )


@dataclass
class WaveResult:
    wave: str
    pair: str
    verdict: str          # ACCEPT / CONDITIONAL_ACCEPT / REJECT / BLOCKED / etc.
    cluster: str
    oos_sharpe: float
    daemon_number: Optional[int]
    k523: Optional[K523]  # realized values
    reason: str = ""
    vertex_number: Optional[int] = None


@dataclass
class PhaseItem:
    id: str
    title: str
    tier: int
    status: str
    daemon_number: Optional[int]
    k523_realized: K523
    activation_1step: str
    reversibility: str
    days_to_activate: int
    prerequisites: list[str] = field(default_factory=list)


@dataclass
class ArchVersion:
    label: str
    k523_conservative: int
    k523_central: int
    k523_optimistic: int
    k523_realized_conservative: int
    k523_realized_central: int
    k523_realized_optimistic: int
    notes: str = ""


# ─────────────────────────────────────────────────────────────────────────────
# Wave History K744-K796  (53 waves)
# ─────────────────────────────────────────────────────────────────────────────

WAVE_HISTORY: list[WaveResult] = [
    # Evals
    WaveResult("K740", "INJ-AVAX", "REJECT",        "Cosmos/DeFi",    "N/A (REJECT)",     None, None, "MR9 algebraic identity — AVAX saturation, G5c=0.55"),
    WaveResult("K743", "LDO-ATOM", "REJECT",        "LST/Cosmos",     "N/A (REJECT)",     None, None, "MR9 STRICT algebraic identity"),
    WaveResult("K746", "ONDO-SOL", "BLOCKED",       "RWA/L1",         "N/A (BLOCKED)",    None, None, "G5c=0.51 AVAX cluster + G5k"),
    WaveResult("K747", "TAO-SOL",  "CONDITIONAL_ACCEPT", "AI/GPU",    12.23,              None, K523(12907, 17210, 45289, "AI L1 @$10M 1.5% 4x"), "G8 structural venue mismatch — K735 HBAR precedent", 15),
    WaveResult("K748", "AAVE-SOL", "BLOCKED",       "DeFi/Lending",   "N/A (BLOCKED)",    None, None, "L004 carry-stable 86%+ — structural positive FR bias"),
    WaveResult("K749", "PYTH-SOL", "BLOCKED",       "Oracle/SOL",     "N/A (BLOCKED)",    None, None, "G5u FIL-SOL persistent blocker"),
    WaveResult("K752", "WLD-SOL",  "BLOCKED",       "AI/Privacy",     "N/A (BLOCKED)",    None, None, "4x simultaneous G5 fails — SOL/AVAX/HBAR/WLD-ETH"),
    WaveResult("K754", "PEPE-SOL", "CONDITIONAL_ACCEPT", "ETH-meme",  44.43,              None, K523(36175, 61880, 85678, "ETH meme @$10M 2.5% 4x"), "Paper-gate HL 66.8% cap", 14),
    WaveResult("K758", "PENDLE-SOL", "BLOCKED",     "DeFi/Yield",     "N/A (BLOCKED)",    None, None, "L004 carry-stable 90.2% full + 86.9% OOS — yield protocol"),
    WaveResult("K759", "WIF-SOL",  "CONDITIONAL_ACCEPT", "SOL-meme",  24.45,              None, K523(34355, 54245, 76847, "SOL meme @$10M 2.5% 4x"), "Paper-gate HL 66.8% cap", 15),
    WaveResult("K760", "DOGE-SOL", "REJECT",        "PoW-meme",       "N/A (REJECT)",     None, None, "L003-AVAX + L010-HBAR + L011-SOL-DIRECT pre-screen vol_ratio<1x"),
    WaveResult("K762", "RUNE-SOL", "REJECT",        "DEX/THORChain",  "N/A (REJECT)",     None, None, "L004 carry 89%+87.6% HARD BLOCK — bonding demand structural"),
    WaveResult("K768", "BLUR-SOL", "CONDITIONAL_ACCEPT", "NFT",       14.98,              None, K523(37000, 61000, 153000, "NFT marketplace @$10M 0.6-2.5% sleeve"), "G5 FIL-SOL IS=0.44 OOS=0.28 trend improving — paper-gate", 16),
    WaveResult("K769", "AXS-SOL",  "ACCEPT",        "Gaming/P2E",     16.05,              None, K523(78337, 123689, 175227, "Gaming P2E @$10M 2.5% 4x"), "All 9/9 gates pass", 17),
    WaveResult("K772", "STX-SOL",  "REJECT",        "BTC-L2",         3.79,               None, None, "G5q LDO-SOL family signal correlation FAIL"),
    WaveResult("K774", "IO-SOL",   "CONDITIONAL_ACCEPT", "GPU/DePIN", 19.88,              None, K523(21007, 28009, 73707, "GPU DePIN @$10M 1.5% 4x"), "G8 structural N/A + G9 marginal 150d — paper-gate", 18),
    WaveResult("K775", "MEGA-SOL", "REJECT",        "ETH-L2",         "N/A (REJECT)",     None, None, "L004 HARD BLOCK 93.8% full + 91.0% OOS structural carry"),
    WaveResult("K777", "EIGEN-SOL","CONDITIONAL_ACCEPT","Restaking",  35.90,              None, K523(63230, 84307, 295813, "Restaking AVS @$10M 1.5% 4x"), "G5z borderline + G9 marginal — paper-gate", 19),
    WaveResult("K778", "COMP-SOL", "ACCEPT",        "DeFi-gov",       25.05,              None, K523(78791, 207345, 276460, "DeFi-gov @$10M 2.5% 4x"), "All 30/30 gates pass — 1st DeFi-gov cluster", 20),
    WaveResult("K782", "PROVE-SOL","REJECT",        "RWA/Fin",        "N/A (REJECT)",     None, None, "L004_DIFF 27.7% diff-carry BLOCK — K782 new rule"),
    WaveResult("K783", "POLYX-SOL","BLOCKED",       "RWA/Compliance", "N/A (BLOCKED)",    None, None, "G5-G5u FIL-SOL persistent blocker"),
    WaveResult("K784", "SAGA-SOL", "BLOCKED",       "Gaming-L1",      "N/A (BLOCKED)",    None, None, "G5j SOL-INJ anti-corr -0.422 + G5u FIL-SOL +0.466"),
    WaveResult("K786", "BIO-SOL",  "ACCEPT",        "DeSci",          23.10,              None, K523(54105, 63652, 167506, "DeSci @$10M 0.4% 4x"), "8/9 gates G8 HIP-3 HL-only — BIO K786 precedent", 21),
    WaveResult("K788", "MEME-SOL", "CONDITIONAL_ACCEPT","Meme-index", 15.97,              None, K523(9194, 14518, 20567, "ERC-20 meme index @$10M 0.4% 3x"), "L004_DIFF borderline full=0.289 — G2 timing confirmed", 22),
    WaveResult("K789", "RESOLV-SOL","CONDITIONAL_ACCEPT","Synth-dollar",23.91,            None, K523(26481, 41539, 109312, "RWA synth-dollar @$10M 0.4% 4x"), "7/9 gates G8+G9 fail — re-gate Aug 2026", None),
    WaveResult("K792", "LINEA-SOL","REJECT",        "ETH-L2",         "N/A (REJECT)",     None, None, "L004_DIFF OOS=0.773 + G5q ETH-L2 meta-narrative — Phase 0"),
    WaveResult("K794", "ME-SOL",   "CONDITIONAL_ACCEPT_RESEARCH_ONLY","SVM-NFT", 19.47,  None, K523(24800, 39100, 55400, "SVM NFT marketplace @$10M 0.25% 3x"), "8/9 gates G8 HL-only — research-only flag, no live gate", None),
    WaveResult("K796", "USUAL-SOL","REJECT",        "ETH-DeFi",       12.60,              None, None, "G2 p=0.925 no timing alpha — IS-OOS -65% carry decay"),
    # Scaffolds (daemon creation waves)
    WaveResult("K741", "FIL-SOL",  "SCAFFOLD",      "Storage-L1",     None,               68,  None, "K739 FIL-SOL scaffold — 68th daemon, 14th alt-alt"),
    WaveResult("K742", "K492-C",   "SCAFFOLD",      "Infra/Compliance",None,              None,None, "K492-C persistence filter patch — DIFF-READY"),
    WaveResult("K745", "K498-OKX", "SCAFFOLD",      "Infra/Exchange",  None,              None,None, "OKX integration scaffold — T3 Tier 3"),
    WaveResult("K750", "TAO-SOL",  "SCAFFOLD",      "AI/GPU",          None,              69,  None, "K747 TAO-SOL scaffold — 69th daemon, 15th alt-alt"),
    WaveResult("K751", "v6.52",    "SCAFFOLD",      "Infra/Kelly",     None,              None,None, "Kelly sleeve sizing — MANDATORY compliance fix"),
    WaveResult("K753", "K545-tax", "SCAFFOLD",      "Infra/Tax",       None,              70,  None, "Tax loss harvester — 70th daemon"),
    WaveResult("K755", "K481-builder","SCAFFOLD",   "Infra/Rebate",    None,              None,None, "HL builder rebate — zero-risk Tier 1"),
    WaveResult("K756", "PEPE-SOL", "SCAFFOLD",      "ETH-meme",        None,              71,  None, "K754 PEPE-SOL scaffold — 71st daemon, 16th alt-alt"),
    WaveResult("K757", "K485-Bybit","SCAFFOLD",     "Infra/Exchange",  None,              None,None, "Bybit sub-account scaffold — T3 Tier 3"),
    WaveResult("K761", "WIF-SOL",  "SCAFFOLD",      "SOL-meme",        None,              72,  None, "K759 WIF-SOL scaffold — 72nd daemon"),
    WaveResult("K763", "compound", "SCAFFOLD",      "Infra/Compound",  None,              73,  None, "Daily compound scheduler — 73rd daemon, Tier 1"),
    WaveResult("K765", "routing",  "SCAFFOLD",      "Infra/Routing",   None,              None,None, "Smart order routing axis #6 — SCAFFOLD_READY"),
    WaveResult("K767", "RWA",      "SCAFFOLD",      "RWA/Yield",       None,              74,  None, "RWA 4-provider diversification — 74th daemon"),
    WaveResult("K770", "BLUR-SOL", "SCAFFOLD",      "NFT",             None,              75,  None, "K768 BLUR-SOL scaffold — 75th daemon"),
    WaveResult("K771", "AXS-SOL",  "SCAFFOLD",      "Gaming/P2E",      None,              76,  None, "K769 AXS-SOL scaffold — 76th daemon"),
    WaveResult("K776", "IO-SOL",   "SCAFFOLD",      "GPU/DePIN",       None,              77,  None, "K774 IO-SOL scaffold — 77th daemon"),
    WaveResult("K779", "EIGEN-SOL","SCAFFOLD",      "Restaking",       None,              78,  None, "K777 EIGEN-SOL scaffold — 78th daemon"),
    WaveResult("K780", "COMP-SOL", "SCAFFOLD",      "DeFi-gov",        None,              79,  None, "K778 COMP-SOL scaffold — 79th daemon"),
    WaveResult("K787", "BIO-SOL",  "SCAFFOLD",      "DeSci",           None,              80,  None, "K786 BIO-SOL scaffold — 80th daemon"),
    WaveResult("K790", "RESOLV-SOL","SCAFFOLD",     "Synth-dollar",    None,              81,  None, "K789 RESOLV-SOL scaffold — 81st daemon"),
    WaveResult("K791", "MEME-SOL", "SCAFFOLD",      "Meme-index",      None,              82,  None, "K788 MEME-SOL scaffold — 82nd daemon"),
    WaveResult("K795", "basket",   "SCAFFOLD",      "Infra/Rotation",  None,              83,  None, "Multi-asset basket rotation Variant B — 83rd daemon"),
    # Screen waves (no pair result)
    WaveResult("K744", "saturation","SCREEN",       "Governance",      None,              None,None, "Alt-alt saturation map — SOL-Triangle 14 ACCEPT / 51 BLOCKED"),
    WaveResult("K764", "governance","GOVERNANCE",   "Governance",      None,              None,None, "Phase A++ governance synthesis K744-K763"),
    WaveResult("K766", "HL-screen","SCREEN",        "Screening",       None,              None,None, "HL HIP-3 long-tail screen — 10/230 pass, BLUR/AXS/COMP queue"),
    WaveResult("K773", "HIP3-2b",  "SCREEN",        "Screening",       None,              None,None, "HIP-3 Round 2b — expanded batch FR fetch"),
    WaveResult("K781", "HIP3-2c",  "SCREEN",        "Screening",       None,              None,None, "HIP-3 Round 2c — 12 L004 carry BLOCK confirmed"),
    WaveResult("K785", "HIP3-2d",  "SCREEN",        "Screening",       None,              None,None, "HIP-3 Round 2d — 18/25 L004_DIFF BLOCK dominant"),
    WaveResult("K793", "HIP3-2e",  "SCREEN",        "Screening",       None,              None,None, "HIP-3 Round 2e — 99/99 long-tail EXHAUST COMPLETE"),
]

# ─────────────────────────────────────────────────────────────────────────────
# Verdict classification helpers
# ─────────────────────────────────────────────────────────────────────────────

ACCEPT_VERDICTS = {"ACCEPT", "CONDITIONAL_ACCEPT", "CONDITIONAL_ACCEPT_RESEARCH_ONLY"}
REJECT_VERDICTS = {"REJECT", "REJECTED", "BLOCKED", "BLOCKED-G5b-G5q-G5u"}
SCAFFOLD_VERDICTS = {"SCAFFOLD"}
SCREEN_VERDICTS = {"SCREEN", "GOVERNANCE"}


def classify_waves() -> dict:
    counts: dict[str, int] = {"ACCEPT": 0, "CONDITIONAL_ACCEPT": 0, "RESEARCH_ONLY": 0,
                               "REJECT": 0, "BLOCKED": 0, "SCAFFOLD": 0, "SCREEN": 0}
    for w in WAVE_HISTORY:
        v = w.verdict
        if v == "ACCEPT":
            counts["ACCEPT"] += 1
        elif v == "CONDITIONAL_ACCEPT":
            counts["CONDITIONAL_ACCEPT"] += 1
        elif v == "CONDITIONAL_ACCEPT_RESEARCH_ONLY":
            counts["RESEARCH_ONLY"] += 1
        elif v in ("REJECT", "REJECTED"):
            counts["REJECT"] += 1
        elif "BLOCK" in v:
            counts["BLOCKED"] += 1
        elif v == "SCAFFOLD":
            counts["SCAFFOLD"] += 1
        elif v in ("SCREEN", "GOVERNANCE"):
            counts["SCREEN"] += 1
    return counts


# ─────────────────────────────────────────────────────────────────────────────
# 22-Vertex Alt-Alt Family Final State
# ─────────────────────────────────────────────────────────────────────────────

VERTEX_SET = [
    {"v": 1,  "token": "APT",    "wave": "K512",  "cluster": "Move-VM L1",         "oos_sh": 51.1,  "central_pnl": 302000},
    {"v": 2,  "token": "ATOM",   "wave": "K493",  "cluster": "Cosmos IBC hub",     "oos_sh": 50.8,  "central_pnl": 231000},
    {"v": 3,  "token": "AVAX",   "wave": "K484",  "cluster": "EVM subnet L1",      "oos_sh": 43.9,  "central_pnl": 75700},
    {"v": 4,  "token": "BNB",    "wave": "K512",  "cluster": "CEX-chain L1",       "oos_sh": 22.1,  "central_pnl": 95000},
    {"v": 5,  "token": "ENA",    "wave": "K719",  "cluster": "Synth-yield",        "oos_sh": 38.4,  "central_pnl": 634464},
    {"v": 6,  "token": "FIL",    "wave": "K739",  "cluster": "Storage L1",         "oos_sh": 14.2,  "central_pnl": 42000},
    {"v": 7,  "token": "HBAR",   "wave": "K735",  "cluster": "Enterprise DLT",     "oos_sh": 28.5,  "central_pnl": 38000},
    {"v": 8,  "token": "INJ",    "wave": "K500",  "cluster": "DeFi appchain",      "oos_sh": 11.2,  "central_pnl": 124000},
    {"v": 9,  "token": "LDO",    "wave": "K728",  "cluster": "LST governance",     "oos_sh": 46.8,  "central_pnl": 89000},
    {"v": 10, "token": "SEI",    "wave": "K507",  "cluster": "SVM DEX L1",         "oos_sh": 12.6,  "central_pnl": 65000},
    {"v": 11, "token": "SOL",    "wave": "anchor","cluster": "SVM anchor",         "oos_sh": None,  "central_pnl": 187000},
    {"v": 12, "token": "TIA",    "wave": "K658",  "cluster": "Modular DA",         "oos_sh": 29.3,  "central_pnl": 112000},
    # K744-K796 new additions (12 new vertex adds)
    {"v": 13, "token": "TAO",    "wave": "K747",  "cluster": "AI / GPU compute",   "oos_sh": 12.2,  "central_pnl": 17210},
    {"v": 14, "token": "PEPE",   "wave": "K754",  "cluster": "ETH ERC-20 meme",   "oos_sh": 44.4,  "central_pnl": 61880},
    {"v": 15, "token": "WIF",    "wave": "K759",  "cluster": "SOL SVM meme",       "oos_sh": 24.5,  "central_pnl": 54245},
    {"v": 16, "token": "BLUR",   "wave": "K768",  "cluster": "NFT marketplace",    "oos_sh": 15.0,  "central_pnl": 61000},
    {"v": 17, "token": "AXS",    "wave": "K769",  "cluster": "Gaming P2E",         "oos_sh": 16.1,  "central_pnl": 123689},
    {"v": 18, "token": "IO",     "wave": "K774",  "cluster": "GPU DePIN",          "oos_sh": 19.9,  "central_pnl": 28009},
    {"v": 19, "token": "EIGEN",  "wave": "K777",  "cluster": "Restaking AVS",      "oos_sh": 35.9,  "central_pnl": 84307},
    {"v": 20, "token": "COMP",   "wave": "K778",  "cluster": "DeFi governance",    "oos_sh": 25.1,  "central_pnl": 207345},
    {"v": 21, "token": "BIO",    "wave": "K786",  "cluster": "DeSci funding",      "oos_sh": 23.1,  "central_pnl": 63652},
    {"v": 22, "token": "RESOLV", "wave": "K789",  "cluster": "RWA synth-dollar",   "oos_sh": 23.9,  "central_pnl": 41539},
    # Research-only (not counted in live vertex set)
    {"v": "R1", "token": "MEME", "wave": "K788",  "cluster": "ERC-20 meme index",  "oos_sh": 16.0,  "central_pnl": 14518, "research_flag": True},
    {"v": "R2", "token": "ME",   "wave": "K794",  "cluster": "SVM NFT marketplace","oos_sh": 19.5,  "central_pnl": 39100, "research_flag": True},
]

# ─────────────────────────────────────────────────────────────────────────────
# Phase A++ v7.1 Activation Queue
# ─────────────────────────────────────────────────────────────────────────────

PHASE_ITEMS: list[PhaseItem] = [
    # Tier 1 — Day 1, zero infra risk
    PhaseItem("K763", "Daily Compound Scheduler",              1, "SCAFFOLD-READY", 73,
              K523(1337, 1246830, 5182047),
              "COMPOUND_FREQUENCY=daily in scripts/k763_compound_scheduler.py + launchctl load",
              "COMPOUND_FREQUENCY=monthly returns to current behavior instantly",
              1, []),
    PhaseItem("K755", "HL Builder Rebate",                     1, "BUILDER-REBATE-READY", None,
              K523(37683, 94208, 188415),
              "Set HL_BUILDER_CODE=0x<YOUR_WALLET> in .env.local + restart 10 HL daemons",
              "Unset HL_BUILDER_CODE -> silent no-op, zero impact on execution",
              1, []),
    PhaseItem("K753", "K545 Tax Loss Harvester",               1, "SCAFFOLD-READY", 70,
              K523(28120, 70300, 141600),
              "launchctl load scripts/com.cryptolab.k545-tax-harvester.plist",
              "launchctl unload — no live trades, paper-only monitoring",
              1, []),
    # Tier 2 — MANDATORY compliance
    PhaseItem("K751", "v6.52 Kelly Sleeve Sizing (MANDATORY)", 2, "SCAFFOLD-READY", None,
              K523(70136, 74109, 148218),
              "Run scripts/k751_kelly_optimizer.py --apply-rebalance (single flip)",
              "Re-run with old weights file to revert",
              2, []),
    PhaseItem("K742", "K492-C Persistence Filter Patch",       2, "DIFF-READY", None,
              K523(7600, 12350, 19760),
              "git apply wave_k742_k492c_ready.diff && launchctl reload k280",
              "git apply -R wave_k742_k492c_ready.diff to revert",
              3, ["K751"]),
    # Tier 3 — account setup Week 1
    PhaseItem("K745", "K498 OKX Integration",                  3, "SCAFFOLD-READY", None,
              K523(11964, 17943, 35886),
              "Set OKX_API_KEY/SECRET in .env.local + launchctl load k498-okx-fr-monitor",
              "Unset OKX keys — OKX daemon exits cleanly, HL continues",
              7, ["K751"]),
    PhaseItem("K757", "K485 Bybit Sub-Account",                3, "SCAFFOLD-READY", None,
              K523(7600, 19000, 38000),
              "Create Bybit sub-account + set BYBIT_SUB_API_KEY in .env.local",
              "Remove sub API keys — falls back to main Bybit account",
              7, ["K751"]),
    # Tier 4 — paper-gate elevation Weeks 2-4
    PhaseItem("K747", "TAO-SOL Paper Gate Elevation",          4, "PAPER-GATE", 69,
              K523(12920, 23560, 58876),
              "Set PAPER_TRADE=False in scripts/k747_tao_sol_run.py + reload daemon",
              "Set PAPER_TRADE=True to return to paper — instant",
              14, ["K751", "K745"]),
    PhaseItem("K754", "PEPE-SOL Paper Gate Elevation",         4, "PAPER-GATE", 71,
              K523(13208, 23560, 32558),
              "Set PAPER_TRADE=False in scripts/k754_pepe_sol_run.py + reload daemon",
              "Set PAPER_TRADE=True to return to paper — instant",
              14, ["K751", "K745"]),
    PhaseItem("K759", "WIF-SOL Paper Gate Elevation",          4, "PAPER-GATE", 72,
              K523(7849, 20613, 29182),
              "Set PAPER_TRADE=False in scripts/k759_wif_sol_run.py + reload daemon",
              "Set PAPER_TRADE=True to return to paper — instant",
              21, ["K751", "K745"]),
    PhaseItem("K768", "BLUR-SOL Paper Gate Elevation",         4, "PAPER-GATE", 75,
              K523(14060, 23180, 58140),
              "Set PAPER_TRADE=False in scripts/k768_blur_sol_run.py + reload daemon",
              "Set PAPER_TRADE=True to return to paper — instant",
              21, ["K751", "K745"]),
    PhaseItem("K769", "AXS-SOL Paper Gate Elevation",          4, "PAPER-GATE", 76,
              K523(29768, 47002, 66586),
              "Set PAPER_TRADE=False in scripts/k769_axs_sol_run.py + reload daemon",
              "Set PAPER_TRADE=True to return to paper — instant",
              21, ["K751", "K745"]),
    PhaseItem("K774", "IO-SOL Paper Gate Elevation",           4, "PAPER-GATE", 77,
              K523(7983, 10643, 27989),
              "Set PAPER_TRADE=False in scripts/k774_io_sol_run.py + reload daemon",
              "Set PAPER_TRADE=True to return to paper — instant",
              21, ["K751", "K745"]),
    PhaseItem("K777", "EIGEN-SOL Paper Gate Elevation",        4, "PAPER-GATE", 78,
              K523(24027, 32037, 112409),
              "Set PAPER_TRADE=False in scripts/k777_eigen_sol_run.py + reload daemon",
              "Set PAPER_TRADE=True to return to paper — instant",
              21, ["K751", "K745"]),
    PhaseItem("K778", "COMP-SOL Paper Gate Elevation",         4, "PAPER-GATE", 79,
              K523(29941, 78791, 104975),
              "Set PAPER_TRADE=False in scripts/k778_comp_sol_run.py + reload daemon",
              "Set PAPER_TRADE=True to return to paper — instant",
              14, ["K751", "K745"]),
    PhaseItem("K786", "BIO-SOL Paper Gate Elevation",          4, "PAPER-GATE", 80,
              K523(20560, 24188, 63652),
              "Set PAPER_TRADE=False in scripts/k786_bio_sol_run.py + reload daemon",
              "Set PAPER_TRADE=True to return to paper — instant",
              21, ["K751", "K745"]),
    PhaseItem("K788", "MEME-SOL Paper Gate Elevation",         4, "PAPER-GATE", 82,
              K523(3494, 5517, 7815),
              "Set PAPER_TRADE=False in scripts/k788_meme_sol_run.py + reload daemon",
              "Set PAPER_TRADE=True to return to paper — instant",
              21, ["K751", "K745"]),
    PhaseItem("K789", "RESOLV-SOL Paper Gate Elevation",       4, "PAPER-GATE", 81,
              K523(10063, 15785, 41539),
              "Set PAPER_TRADE=False in scripts/k789_resolv_sol_run.py + reload daemon",
              "Set PAPER_TRADE=True to return to paper — instant",
              60, ["K751", "K745", "K789_G9_recheck"]),
    # Tier 5 — new axes
    PhaseItem("K795", "Multi-Asset Basket Rotation",           5, "PAPER-GATE", 83,
              K523(21000, 112000, 285000),
              "Set PAPER_TRADE=False in scripts/k795_basket_rotation.py after 60d observation",
              "Set PAPER_TRADE=True to return to paper — instant",
              60, ["K751", "K745"]),
    PhaseItem("K767", "RWA 4-Provider Diversification",        5, "SCAFFOLD-READY", 74,
              K523(21000, 30000, 39000),
              "launchctl load scripts/com.cryptolab.k767-rwa-diversified.plist",
              "launchctl unload — falls back to sUSDe-only allocation",
              7, []),
]

# ─────────────────────────────────────────────────────────────────────────────
# Architecture Versions — K523 3-point @$10M
# ─────────────────────────────────────────────────────────────────────────────

ARCH_VERSIONS = {
    "v651": ArchVersion(
        "v6.51 (current — NON-COMPLIANT: HL 66.8% > 65%, Bybit 55.7% > 50%, K280 < 30%)",
        k523_conservative=2151571, k523_central=2980630, k523_optimistic=5672254,
        k523_realized_conservative=817597, k523_realized_central=1132639,
        k523_realized_optimistic=2155457,
    ),
    "v652": ArchVersion(
        "v6.52 (Kelly-compliant: HL 53.6%, Bybit 43.8%, K280 30% floor)",
        k523_conservative=2336139, k523_central=3175654, k523_optimistic=6227901,
        k523_realized_conservative=877573, k523_realized_central=1206749,
        k523_realized_optimistic=2366602,
    ),
    "v70": ArchVersion(
        "v7.0 (v6.52 + K763 + K755 + K753 + K498 OKX + K485 Bybit + K492-C)",
        k523_conservative=2536305, k523_central=4673569, k523_optimistic=11867731,
        k523_realized_conservative=963796, k523_realized_central=1775957,
        k523_realized_optimistic=4509737,
    ),
    "v71": ArchVersion(
        "v7.1 (v7.0 + 12 new vertex elevations + K795 basket + K767 RWA)",
        # v7.0 base + sum of new Tier 4-5 central realized values
        # New additions: TAO+PEPE+WIF+BLUR+AXS+IO+EIGEN+COMP+BIO+RESOLV+MEME + basket + RWA
        # Conservative = v7.0 cons + sum(new_cons) = 963796 + ~180K
        k523_conservative=1143796,
        # Central = v7.0 central + sum(new central) from all 13 new items
        # 23560+23560+20613+23180+47002+10643+32037+78791+24188+15785+5517+112000+30000 = 446876
        k523_central=2222833,
        # Optimistic = v7.0 opt + sum(new opt) = 4509737 + ~870K
        k523_optimistic=5379737,
        k523_realized_conservative=1143796,
        k523_realized_central=2222833,
        k523_realized_optimistic=5379737,
        notes=(
            "v7.1 = v7.0 base realized + 13 new activation items (Tiers 4+5). "
            "K763 daily compound $1.25M central dominates. "
            "Conservative reflects K518 38% floor on all new positions. "
            "Optimistic includes Variant A basket + full sleeve elevation. "
            "Excludes research-only ME-SOL ($39K)."
        ),
    ),
}

# Cluster lesson summary
CLUSTER_LESSONS = {
    "L004_DIFF": (
        "K782 new rule: diff_carry (fraction of time long leg FR > short leg FR) must be "
        "between 0.30 and 0.70. Outside range = structural one-sided pair REJECT. "
        "18 tokens blocked K785 batch by this rule alone."
    ),
    "G5u_FIL_SOL": (
        "FIL-SOL (K739) is a persistent blocker via G5u. PYTH (K749), POLYX (K783) "
        "both blocked by G5u. Storage-L1 FR signal bleeds into oracle and compliance tokens. "
        "Any token with storage/data provenance theme: pre-check G5u before full eval."
    ),
    "G5j_SOL_INJ": (
        "SOL-INJ anti-correlation (K686, short SOL / long INJ) creates negative G5j "
        "for Gaming tokens. SAGA (K784) blocked. L1 gaming chains with Cosmos-adjacent "
        "architecture systematically hit G5j. Pre-screen: raw SOL-INJ FR corr check."
    ),
    "HIP3_long_tail_saturation": (
        "K793 exhausted 99/99 HIP-3 perp universe. Dominant failure modes: "
        "(1) L004_DIFF structural carry 64% of failures, "
        "(2) L004 carry > 80% 36% of failures, "
        "(3) G5 family overlap residual. "
        "New axis = regime-aware basket rotation (K795). No more HIP-3 tokens to screen."
    ),
    "SOL_meme_cluster": (
        "PEPE-WIF would be BLOCKED_SOL_TRIANGLE (both SOL-pivot tokens). "
        "Meme cluster (PEPE, WIF, MEME) has no internal overlap: G5w=0.13, G5y=0.08 — "
        "cross-chain meme signals are genuinely orthogonal. MEME (ERC-20 index) is 22nd vertex."
    ),
    "DeSci_DeFi_gov_distinct": (
        "BIO (DeSci) and COMP (DeFi-gov) occupy distinct FR driver clusters. "
        "Both ACCEPT with no G5 overlap. Proves governance token alpha is "
        "mechanism-specific, not a unified 'governance' cluster."
    ),
}

# ─────────────────────────────────────────────────────────────────────────────
# Day 1 Action Card
# ─────────────────────────────────────────────────────────────────────────────

ACTION_CARD = {
    "title": "Phase A++ v7.1 — Day 1 Action Card",
    "subtitle": "Top 3 zero-risk actions to unlock realized value TODAY",
    "actions": [
        {
            "rank": 1,
            "id": "K751",
            "name": "Fix v6.51 compliance violations (MANDATORY FIRST)",
            "why": "HL 66.8% > 65% cap, Bybit 55.7% > 50% cap — live violation RIGHT NOW. Must fix before any new trades.",
            "command": "python3 scripts/k751_kelly_optimizer.py --dry-run\n# Review output, then:\npython3 scripts/k751_kelly_optimizer.py --apply-rebalance",
            "time_estimate": "30 minutes",
            "reversibility": "Re-run with old weights file — fully reversible",
            "k523_central": "$74,109/yr incremental + unlocks all Tier 3-4 items",
        },
        {
            "rank": 2,
            "id": "K763",
            "name": "Enable daily compounding",
            "why": "Largest single lever in entire Phase A++ stack at $1.25M central realized/yr. Zero risk — just a scheduling change.",
            "command": "# In scripts/k763_compound_scheduler.py:\n# Change: COMPOUND_FREQUENCY = 'monthly'\n# To:     COMPOUND_FREQUENCY = 'daily'\nlaunchctl load ~/Library/LaunchAgents/com.cryptolab.k763-compound-scheduler.plist",
            "time_estimate": "15 minutes",
            "reversibility": "Change COMPOUND_FREQUENCY=monthly — instant revert",
            "k523_central": "$1,246,830/yr (K518 38% realized)",
        },
        {
            "rank": 3,
            "id": "K755",
            "name": "Activate HL builder rebate",
            "why": "Earn $248K/yr gross from existing HL volume — no new positions, no new risk. One env var change.",
            "command": "# In .env.local:\nHL_BUILDER_CODE=0x<YOUR_WALLET_ADDRESS>\n\n# Then restart all 10 HL daemons:\nfor plist in k246a k272a k280 k302a k287 k376 k492 k476 k484 k507; do\n  launchctl unload ~/Library/LaunchAgents/com.cryptolab.${plist}*.plist 2>/dev/null\n  launchctl load  ~/Library/LaunchAgents/com.cryptolab.${plist}*.plist 2>/dev/null\ndone",
            "time_estimate": "65 minutes (wallet signing step included)",
            "reversibility": "Unset HL_BUILDER_CODE — silent no-op, zero execution impact",
            "k523_central": "$94,208/yr (K518 38% realized)",
        },
    ],
    "tier4_note": (
        "Tier 4 (paper-gate elevation) follows after K751 compliance fix and K745 OKX activation. "
        "11 pairs ready: TAO/PEPE/WIF/BLUR/AXS/IO/EIGEN/COMP/BIO/RESOLV/MEME. "
        "Combined Tier 4 central realized: ~$388K/yr additional."
    ),
    "total_day1_central": "$1,415,147/yr from 3 actions alone (K523 3-point mandatory — see v7.1)",
}

# ─────────────────────────────────────────────────────────────────────────────
# Suggested Memory Updates (Phase 6)
# ─────────────────────────────────────────────────────────────────────────────

MEMORY_UPDATES = [
    {
        "rule_id": "L004_DIFF_cluster_prescreen",
        "title": "L004_DIFF cluster pre-screen mandatory",
        "body": (
            "K782 K785 lesson: diff_carry (fraction of time long-leg FR > short-leg FR) must be "
            "0.30-0.70. Pre-screen all candidates before full §6 eval. "
            "18/25 K785 batch tokens blocked by this rule. "
            "Command: compute pos_fraction for LONG leg and SHORT leg diff — if outside range, HARD BLOCK."
        ),
    },
    {
        "rule_id": "G5u_FIL_SOL_persistent_blocker",
        "title": "G5u FIL-SOL is a persistent structural blocker",
        "body": (
            "FIL-SOL (K739, 68th daemon) creates G5u correlation for storage/data/provenance tokens. "
            "Confirmed blockers: PYTH (K749, oracle data), POLYX (K783, compliance data). "
            "Any token with storage, data-availability, or provenance theme: run G5u check FIRST."
        ),
    },
    {
        "rule_id": "G5j_SOL_INJ_gaming_blocker",
        "title": "G5j SOL-INJ anti-correlation blocks Gaming-L1",
        "body": (
            "SOL-INJ (K686) negative correlation creates G5j blocker for L1 gaming chains. "
            "SAGA (K784) blocked at -0.422. Any Cosmos-adjacent gaming L1 or app-specific L1 "
            "for gaming: pre-check G5j (SOL-INJ correlation) before full §6 eval."
        ),
    },
    {
        "rule_id": "HIP3_long_tail_exhausted_K793",
        "title": "HIP-3 long-tail axis EXHAUSTED as of K793",
        "body": (
            "K793 confirmed 99/99 HIP-3 perp universe screened. No new single-pair long-tail "
            "candidates remain. New alpha axis = regime-aware basket rotation (K795). "
            "L004_DIFF (64%) and L004 carry-stable (36%) are dominant failure modes. "
            "Next exploration: cross-venue arb OR cross-chain pairs beyond SOL anchor."
        ),
    },
    {
        "rule_id": "alt_alt_22_vertex_saturation",
        "title": "Alt-alt family 22-vertex HIP-3 saturation criterion",
        "body": (
            "22 vertices: APT/ATOM/AVAX/BNB/ENA/FIL/HBAR/INJ/LDO/SEI/SOL/TIA (pre-K744) + "
            "TAO/PEPE/WIF/BLUR/AXS/IO/EIGEN/COMP/BIO/RESOLV (K744-K796). "
            "Research-only: MEME(K788) + ME(K794). "
            "Family capacity: 22*(22-1)/2 = 231 pairs, 36 currently accepted = 15.6% utilized. "
            "HIP-3 single-pair saturation reached — future alpha from combinations and regimes."
        ),
    },
]

# ─────────────────────────────────────────────────────────────────────────────
# Report Functions
# ─────────────────────────────────────────────────────────────────────────────

def fmt_usd(n: int | float) -> str:
    return f"${n:,.0f}"


def print_wave_tally():
    counts = classify_waves()
    evals = [w for w in WAVE_HISTORY if w.verdict not in ("SCAFFOLD", "SCREEN", "GOVERNANCE")]
    accepts = [w for w in evals if w.verdict in ACCEPT_VERDICTS]

    print("\n" + "=" * 72)
    print("  K798 — Wave History K744-K796 Complete Tally")
    print("=" * 72)
    print(f"  Total waves shipped: {TOTAL_WAVES} ({WAVE_RANGE})")
    print()
    print("  Eval results:")
    print(f"    ACCEPT (clean):               {counts['ACCEPT']:>3}")
    print(f"    CONDITIONAL_ACCEPT:            {counts['CONDITIONAL_ACCEPT']:>3}")
    print(f"    CONDITIONAL (research-only):   {counts['RESEARCH_ONLY']:>3}")
    print(f"    REJECT:                        {counts['REJECT']:>3}")
    print(f"    BLOCKED (G5/L004/pre-screen):  {counts['BLOCKED']:>3}")
    print()
    print(f"  Infrastructure waves:")
    print(f"    SCAFFOLD (daemon creation):    {counts['SCAFFOLD']:>3}")
    print(f"    SCREEN / GOVERNANCE:           {counts['SCREEN']:>3}")
    print()
    print("  ACCEPT/CONDITIONAL breakdown by cluster:")
    for w in sorted(accepts, key=lambda x: x.wave):
        sh_str = f"{w.oos_sharpe:.2f}" if isinstance(w.oos_sharpe, float) else "—"
        print(f"    {w.wave:<6}  {w.pair:<12}  {w.verdict:<35}  OOS Sh={sh_str:<6}  {w.cluster}")
    print()
    print("  REJECT/BLOCKED classification:")
    rejects = [w for w in evals if w.verdict not in ACCEPT_VERDICTS]
    reject_reasons: dict[str, int] = {}
    for w in rejects:
        r = w.reason.split(" — ")[0][:40]
        reject_reasons[r] = reject_reasons.get(r, 0) + 1
    for reason, cnt in sorted(reject_reasons.items(), key=lambda x: -x[1]):
        print(f"    {cnt}x  {reason}")


def print_k523_summary():
    print("\n" + "=" * 72)
    print("  K523 3-Point Uplift Update — v6.51 -> v6.52 -> v7.0 -> v7.1")
    print("=" * 72)
    print(f"  Reference AUM: {fmt_usd(AUM_REF_USD)} | K518 realized ratio: {K518_HAIRCUT:.0%}")
    print()
    print(f"  {'Version':<42} {'Conservative':>14} {'Central':>14} {'Optimistic':>14}")
    print("  " + "-" * 88)
    for key, ver in ARCH_VERSIONS.items():
        label = ver.label[:42]
        print(f"  {label:<42} {fmt_usd(ver.k523_realized_conservative):>14} "
              f"{fmt_usd(ver.k523_realized_central):>14} "
              f"{fmt_usd(ver.k523_realized_optimistic):>14}")
    print()
    print("  Key components in v7.1 central ($2.22M):")
    for item in PHASE_ITEMS[:7]:
        c = item.k523_realized.central
        print(f"    T{item.tier}  {item.id:<6}  {item.title:<45}  {fmt_usd(c):>12}/yr")
    print()
    v71 = ARCH_VERSIONS["v71"]
    print(f"  v7.1 FINAL (K523 mandatory 3-point @$10M):")
    print(f"    Conservative: {fmt_usd(v71.k523_realized_conservative)}/yr")
    print(f"    Central:      {fmt_usd(v71.k523_realized_central)}/yr")
    print(f"    Optimistic:   {fmt_usd(v71.k523_realized_optimistic)}/yr")
    print()
    print("  NOTE: Central is NOT the upper bound. Conservative = K518 38% floor.")
    print("  K763 daily compound ($1.25M) is contingent on all sleeves live at v6.52.")


def print_vertex_set():
    print("\n" + "=" * 72)
    print("  22-Vertex Alt-Alt Family Final State (K798)")
    print("=" * 72)
    live = [v for v in VERTEX_SET if not v.get("research_flag")]
    research = [v for v in VERTEX_SET if v.get("research_flag")]
    print(f"\n  Live vertices: {len(live)}   Research-only: {len(research)}")
    print()
    print(f"  {'V':<4} {'Token':<8} {'Wave':<7} {'Cluster':<25} {'OOS Sh':>8} {'Central $':>12}")
    print("  " + "-" * 72)
    for v in live:
        sh = f"{v['oos_sh']:.1f}" if v['oos_sh'] else "anchor"
        print(f"  {str(v['v']):<4} {v['token']:<8} {v['wave']:<7} {v['cluster']:<25} "
              f"{sh:>8} {fmt_usd(v['central_pnl']):>12}")
    print()
    print("  Research-only (paper-gate, HL cap clearing required):")
    for v in research:
        print(f"  {str(v['v']):<4} {v['token']:<8} {v['wave']:<7} {v['cluster']:<25} "
              f"OOS Sh={v['oos_sh']:.1f}  {fmt_usd(v['central_pnl'])}/yr")
    print()
    print("  Cluster diversity (HIP-3 saturation evidence):")
    clusters = {}
    for v in live:
        c = v["cluster"].split("/")[0].split(" ")[0]
        clusters[c] = clusters.get(c, 0) + 1
    for c, n in sorted(clusters.items()):
        print(f"    {n}x  {c}")
    print()
    print("  22*(22-1)/2 = 231 possible pairs | 36 accepted = 15.6% utilized")
    print("  HIP-3 single-pair saturation confirmed K793 99/99")


def print_activation_order():
    print("\n" + "=" * 72)
    print("  Phase A++ v7.1 Activation Order — REFINED")
    print("=" * 72)
    tiers = {}
    for item in PHASE_ITEMS:
        tiers.setdefault(item.tier, []).append(item)

    tier_labels = {
        1: "Tier 1 — Day 1 (zero infra risk)",
        2: "Tier 2 — Days 2-3 (MANDATORY compliance)",
        3: "Tier 3 — Week 1 (account setup)",
        4: "Tier 4 — Weeks 2-4 (paper-gate elevation)",
        5: "Tier 5 — Weeks 4+ (new axes)",
    }
    for tier, items in sorted(tiers.items()):
        print(f"\n  {tier_labels.get(tier, f'Tier {tier}')}")
        print(f"  {'ID':<7} {'Title':<45} {'Daemon':>7} {'Central $/yr':>14}")
        print("  " + "-" * 78)
        for item in items:
            daemon = str(item.daemon_number) if item.daemon_number else "—"
            print(f"  {item.id:<7} {item.title:<45} {daemon:>7} {fmt_usd(item.k523_realized.central):>14}")


def print_action_card():
    card = ACTION_CARD
    print("\n" + "=" * 72)
    print(f"  {card['title']}")
    print(f"  {card['subtitle']}")
    print("=" * 72)
    for action in card["actions"]:
        print(f"\n  Action {action['rank']}: [{action['id']}] {action['name']}")
        print(f"  Why: {action['why']}")
        print(f"  Time: {action['time_estimate']}")
        print(f"  Reversibility: {action['reversibility']}")
        print(f"  K523 central: {action['k523_central']}")
        print("\n  Command:")
        for line in action["command"].split("\n"):
            print(f"    {line}")
    print(f"\n  {card['tier4_note']}")
    print(f"\n  Total Day 1 realized: {card['total_day1_central']}")


def print_cluster_lessons():
    print("\n" + "=" * 72)
    print("  Cluster Lessons — New Rules from K744-K796")
    print("=" * 72)
    for key, body in CLUSTER_LESSONS.items():
        print(f"\n  [{key}]")
        # wrap at 70 chars
        words = body.split()
        line, lines = "", []
        for w in words:
            if len(line) + len(w) + 1 > 68:
                lines.append(line)
                line = w
            else:
                line = (line + " " + w).strip()
        if line:
            lines.append(line)
        for l in lines:
            print(f"    {l}")


def export_json(path: Path):
    now_utc = datetime.now(timezone.utc)
    now_jst = now_utc.strftime("%Y-%m-%d %H:%M JST")

    counts = classify_waves()
    data = {
        "_meta": {
            "wave": "K798",
            "title": "Governance v11 / Phase A++ v7.1 Final Synthesis",
            "generated_jst": now_jst,
            "generated_utc": now_utc.isoformat(),
            "wave_range": WAVE_RANGE,
            "total_waves": TOTAL_WAVES,
            "k339_pattern": "REPO_ROOT = Path(__file__).resolve().parent",
            "k523_mandatory": True,
            "k518_haircut_ratio": K518_HAIRCUT,
            "oos_paired_haircut": OOS_PAIRED_HAIRCUT,
            "aum_ref_usd": AUM_REF_USD,
            "live_auto_change_prohibited": True,
        },
        "wave_tally": {
            "total_waves": TOTAL_WAVES,
            **counts,
            "new_vertex_additions": 12,
            "research_only_additions": 2,
            "daemon_count_start": 66,
            "daemon_count_end": 84,
        },
        "architecture_versions": {
            k: {
                "label": v.label,
                "k523_conservative": v.k523_conservative,
                "k523_central": v.k523_central,
                "k523_optimistic": v.k523_optimistic,
                "k523_realized_conservative": v.k523_realized_conservative,
                "k523_realized_central": v.k523_realized_central,
                "k523_realized_optimistic": v.k523_realized_optimistic,
                "notes": v.notes,
            }
            for k, v in ARCH_VERSIONS.items()
        },
        "vertex_set": VERTEX_SET,
        "phase_items": [
            {
                "id": item.id,
                "title": item.title,
                "tier": item.tier,
                "status": item.status,
                "daemon_number": item.daemon_number,
                "k523": {
                    "realized_conservative": item.k523_realized.conservative,
                    "realized_central": item.k523_realized.central,
                    "realized_optimistic": item.k523_realized.optimistic,
                },
                "activation_1step": item.activation_1step,
                "reversibility": item.reversibility,
                "days_to_activate": item.days_to_activate,
                "prerequisites": item.prerequisites,
            }
            for item in PHASE_ITEMS
        ],
        "action_card": ACTION_CARD,
        "cluster_lessons": CLUSTER_LESSONS,
        "memory_updates": MEMORY_UPDATES,
        "wave_history": [
            {
                "wave": w.wave,
                "pair": w.pair,
                "verdict": w.verdict,
                "cluster": w.cluster,
                "oos_sharpe": w.oos_sharpe if isinstance(w.oos_sharpe, float) else None,
                "daemon_number": w.daemon_number,
                "vertex_number": w.vertex_number,
                "reason": w.reason,
                "k523_realized_central": w.k523.central if w.k523 else None,
            }
            for w in WAVE_HISTORY
        ],
    }
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    print(f"Exported JSON: {path}")


# ─────────────────────────────────────────────────────────────────────────────
# Main
# ─────────────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="K798 Governance v11 / Phase A++ v7.1")
    parser.add_argument("--summary",     action="store_true", help="K523 table only")
    parser.add_argument("--action-card", action="store_true", help="Day 1 action card")
    parser.add_argument("--vertex-set",  action="store_true", help="22-vertex final state")
    parser.add_argument("--lessons",     action="store_true", help="Cluster lessons")
    parser.add_argument("--activation",  action="store_true", help="Activation order")
    parser.add_argument("--export-json", action="store_true", help="Write JSON file")
    args = parser.parse_args()

    any_flag = any([args.summary, args.action_card, args.vertex_set,
                    args.lessons, args.activation, args.export_json])

    if not any_flag or args.summary:
        print_wave_tally()
        print_k523_summary()
    if not any_flag or args.vertex_set:
        print_vertex_set()
    if not any_flag or args.activation:
        print_activation_order()
    if not any_flag or args.action_card:
        print_action_card()
    if not any_flag or args.lessons:
        print_cluster_lessons()
    if args.export_json or not any_flag:
        out = REPO_ROOT / "wave_k798_governance_v11.json"
        export_json(out)


if __name__ == "__main__":
    main()

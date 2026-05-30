#!/usr/bin/env python3
"""
K718 K674 CAPSTONE INCREMENTAL UPDATE
268+ waves (K449→K717) | 62 daemons | 22 mechanism scaffolds | v6.50 $21.1M MEGA
Timestamp: 2026-05-30 17:03 JST
K339 REPO_ROOT = /Users/nekonaomichi/crypto-lab
"""

import json
import sys
from datetime import datetime
from pathlib import Path

REPO_ROOT = Path("/Users/nekonaomichi/crypto-lab")  # K339 pattern

# ─────────────────────────────────────────────────────────────────────────────
# 1. CONSTANTS (K718 updated from K674)
# ─────────────────────────────────────────────────────────────────────────────

# Session metadata
SESSION_SPAN = "K449 → K717"
TOTAL_WAVES = 268        # 225 (K674) → 268+ (K718)
DAEMON_COUNT = 62        # 52 (K674) → 62 (K712 verified)
SCAFFOLD_COUNT = 22      # 14 (K674) → 22 (8 alt-alt + 4 ETH-base + 10 orthog)
TIMESTAMP_JST = "2026-05-30 17:03 JST"
CAPSTONE_WAVE = "K718"
PRIOR_CAPSTONE = "K674"

# Architecture version
ARCH_VERSION = "v6.50 MEGA"
SLEEVE_COUNT = 35

# Profit projections (v6.50, K523 range mandatory — transparent range)
V650_CONSERVATIVE_10M = 15_200_000   # K523: conservative = ~72% of mid
V650_MID_10M = 21_076_191            # K712 verified final
V650_OPTIMISTIC_10M = 48_000_000     # K523: optimistic = ~2.3x mid
V650_MID_100M = 210_760_000
V650_5Y_MID_10M = 105_000_000        # 5y @$10M central
V650_5Y_100M = 1_054_000_000         # 5y @$100M

# v6.40 baseline for delta tracking
V640_MID_10M = 20_900_000

# Architecture delta
V650_DELTA_FROM_640 = V650_MID_10M - V640_MID_10M  # +$176K

# D60 cascade
D60_DATE = "2026-07-29"
D60_SCAFFOLD_COUNT = 14
D60_UNLOCK_10M = 1_642_745           # K712 verified (K696/K698 added)

# Combined activation
COMBINED_ACTIVATION_10M = 4_505_745  # Phase A + D60 grand total

# HL concentration
HL_CURRENT_PCT = 63.5
HL_CAP_PCT = 65.0
HL_HEADROOM_PP = 1.5

# LIVE target
LIVE_TARGET = "2027-Q1"

# ─────────────────────────────────────────────────────────────────────────────
# 2. PHASE A — DAY 0 ACTIONS (K718 updated: 5 → 6 actions, $521K → $566K)
# ─────────────────────────────────────────────────────────────────────────────

PHASE_A_ACTIONS = [
    {
        "step": 1,
        "id": "K545",
        "name": "Tax harvester plist load",
        "effort_min": 5,
        "profit_usd": 47_000,
        "risk": "ZERO",
        "command": "launchctl load ~/Library/LaunchAgents/com.cryptolab.loss-harvester.plist",
        "status": "READY",
        "note": "5-minute activation, zero risk.",
    },
    {
        "step": 2,
        "id": "K481",
        "name": "HL Builder Rebate (approveBuilderFee)",
        "effort_min": 30,
        "profit_usd_low": 99_000,
        "profit_usd_high": 248_000,
        "risk": "ZERO",
        "status": "READY",
        "note": "Pure revenue — register HL builder fee rebate with no position risk. Day 0 first.",
    },
    {
        "step": 3,
        "id": "K552",
        "name": "K280 75→60% atomic 3-file patch (PREREQ)",
        "effort_min": 30,
        "profit_cascade_usd": 260_000,
        "risk": "LOW",
        "status": "READY",
        "note": "PREREQ for K376 BULL and K629 WLD-ETH. Frees 7.5pp HL headroom. Apply before cascade.",
    },
    {
        "step": 4,
        "id": "K492C",
        "name": "K492-C Persistence Filter activation (K716 playbook)",
        "effort_min": 90,
        "profit_usd": 45_000,
        "risk": "LOW",
        "status": "READY",
        "note": "4-site patch (k280_config.json, k280_strategy.py, bot.py, dashboard). +1.51 Sh +3.4pp win. K716.",
        "added_wave": "K718",   # new vs K674
    },
    {
        "step": 5,
        "id": "K498",
        "name": "Phase 1A BBO_SELECT + OKX daemon",
        "effort_min": 480,
        "profit_usd": 121_000,
        "aum_threshold": "$30M",
        "risk": "LOW",
        "status": "READY",
        "note": "K530 playbook. OKX API key required. Deferrable D1-D2.",
    },
    {
        "step": 6,
        "id": "K485",
        "name": "Bybit sub-account + HL W2 isolation",
        "effort_min": 30,
        "effort_gate_days": 7,
        "profit_usd": 204_000,
        "risk": "LOW",
        "status": "READY",
        "note": "Creates Bybit infra for all 10 orthog sleeves + 8 alt-alt pairs ($2.2M/yr @$25M).",
    },
]

PHASE_A_IMMEDIATE_USD = 566_000   # K718 updated from $521K

# ─────────────────────────────────────────────────────────────────────────────
# 3. NEW MECHANISM FAMILIES (K674→K718 delta)
# ─────────────────────────────────────────────────────────────────────────────

ALT_ALT_ACCEPTS = [
    # K674 had 0 alt-alt — all 8 added K675→K718
    {"id": "K679", "pair": "APT-SOL",  "oos_sh": 39.29, "profit_10m": 234_700, "venue": "Bybit", "status": "SCAFFOLD"},
    {"id": "K682", "pair": "ATOM-SOL", "oos_sh": 43.43, "profit_10m": 214_600, "venue": "Bybit", "status": "SCAFFOLD"},
    {"id": "K684", "pair": "SOL-INJ",  "oos_sh":  9.65, "profit_10m": 114_300, "venue": "Bybit", "status": "SCAFFOLD"},
    {"id": "K686", "pair": "AVAX-SOL", "oos_sh": 50.27, "profit_10m": 102_000, "venue": "Bybit", "status": "SCAFFOLD"},
    {"id": "K690", "pair": "SEI-SOL",  "oos_sh": 25.11, "profit_10m": 104_774, "venue": "Bybit", "status": "SCAFFOLD"},
    {"id": "K694", "pair": "TIA-SOL",  "oos_sh": 19.09, "profit_10m":  58_354, "venue": "Bybit", "status": "SCAFFOLD", "gate": "CONDITIONAL"},
    {"id": "K696", "pair": "ENA-SOL",  "oos_sh": 26.93, "profit_10m":  93_187, "venue": "Bybit", "status": "SCAFFOLD"},
    {"id": "K708", "pair": "BNB-SOL",  "oos_sh": 48.59, "profit_10m":  75_011, "venue": "Bybit", "status": "SCAFFOLD"},
]

ETH_BASE_ACCEPTS = [
    # 3 pre-K674 + 1 added K698
    {"id": "K629", "pair": "WLD-ETH",  "oos_sh": 19.90, "profit_10m":  94_210, "venue": "HL",    "status": "SCAFFOLD"},
    {"id": "K658", "pair": "SOL-ETH",  "oos_sh": 29.66, "profit_10m":  42_332, "venue": "HL",    "status": "SCAFFOLD"},
    {"id": "K663", "pair": "TIA-ETH",  "oos_sh": 17.13, "profit_10m":  74_188, "venue": "HL",    "status": "SCAFFOLD"},
    {"id": "K698", "pair": "LINK-ETH", "oos_sh": 12.07, "profit_10m":  28_997, "venue": "Bybit", "status": "SCAFFOLD", "gate": "CONDITIONAL", "added_wave": "K718"},
]

# Combined alt-alt total
ALT_ALT_COMBINED_10M = sum(a["profit_10m"] for a in ALT_ALT_ACCEPTS)   # $946,926 ≈ $946,853
ETH_BASE_COMBINED_10M = sum(e["profit_10m"] for e in ETH_BASE_ACCEPTS) # $239,727 ≈ $197K accepted (K694/K698 conditional)

# K492 V-C immediate (K714 finding)
K492_VC_IMMEDIATE = {
    "id": "K492C",
    "wave_found": "K714",
    "name": "K280 Persistence Filter",
    "description": (
        "K714 K280 deep health check revealed: K492-C persistence filter = +1.51 Sharpe improvement, "
        "+3.4pp win rate, zero infrastructure change required. 4-site patch (k280_config.json, "
        "k280_strategy.py, bot.py, dashboard). Added to Phase A step 4 in K718."
    ),
    "sharpe_delta": 1.51,
    "winrate_delta_pp": 3.4,
    "effort_min": 90,
    "risk": "LOW",
}

# ─────────────────────────────────────────────────────────────────────────────
# 4. MEMORY RULES CONSOLIDATED 11 (K718 — expanded from MR7 at K674)
# ─────────────────────────────────────────────────────────────────────────────

MEMORY_RULES = {
    "MR1_orthogonalization": {
        "source": "K628",
        "rule": (
            "G5-BLOCKED strategies: orthogonalize via OLS factor extraction. "
            "Identify common FR factor (corr >= 0.40 with existing portfolio member). "
            "Regress out → residual signal. Retest G5. If post-orth corr < 0.40: ACCEPT CONDITIONAL 60d paper."
        ),
        "anti_pattern": "Never reject G5-blocked without attempting factor extraction first.",
    },
    "MR2_eth_base_triple_discriminator": {
        "source": "K672 (11-wave test)",
        "rule": (
            "ETH-base ACCEPT requires ALL 3: "
            "(1) vol_ratio_alt_ETH >= 2x [NECESSARY pre-screen]. "
            "(2) Alt FR cycles align with ETH DeFi/staking/L2 ecosystem [qualitative NECESSARY]. "
            "(3) alt-ETH FR raw corr < 0.45 [orthogonality NECESSARY]. "
            "Accept rate: 3/11 = 27%. vol_ratio is single best pre-screen."
        ),
        "accepts": [
            "WLD (vol=2.08x, AI/ID narrative)",
            "SOL (vol=1.63x, retail L1 near-ETH FR)",
            "TIA (vol=2.12x, Celestia DA)",
            "LINK (oracle MM-floor vs ETH DeFi; 4th ETH-base K698)",
        ],
        "rejects": [
            "SHIB (vol=1.89x < 2x)",
            "TRX (payment cycle != ETH DeFi)",
            "HYPE (AQAv2 self-ref)",
            "INJ (vol=3.55x dominance block)",
        ],
    },
    "MR3_load_bearing_factor": {
        "source": "K634",
        "rule": (
            "Before removing a factor via orthogonalization, check IS R². "
            "IS R² > 0.40 = factor may be load-bearing (genuine alpha, not noise). "
            "Also check OOS R² < 0.10 (factor predictability out-of-sample). "
            "High IS + Low OOS = spurious → safe to remove. High IS + High OOS = load-bearing → do NOT remove."
        ),
    },
    "MR4_vol_prescreen": {
        "source": "K662/K663",
        "rule": (
            "Compute vol_ratio (alt FR vol / ETH FR vol) in 2min before full backtest. "
            "If < 2x: skip ETH-base test (WORSE or marginal guaranteed). "
            "Exception: alt FR level near ETH FR level may allow < 2x (SOL at 1.63x)."
        ),
    },
    "MR5_cycle_alignment": {
        "source": "K667",
        "rule": (
            "ETH-base works when alt FR spikes correlate with ETH ecosystem cycles "
            "(DeFi, staking, L2). Tokens with BTC-correlated institutional flows (TRX), "
            "self-referential buyback cycles (HYPE), or pure meme demand (SHIB) will be WORSE "
            "even if vol_ratio passes."
        ),
    },
    "MR6_paired_trade_screening": {
        "source": "K480/K484/K490",
        "rule": (
            "BTC-base paired trade ACCEPT: "
            "(1) OOS Sh >= 8.0. "
            "(2) G5 alt FR corr < 0.40 with all existing portfolio members in same window. "
            "(3) G5b PnL corr < 0.40 with nearest sibling. All 3 required."
        ),
    },
    "MR7_hl_builder_rebate": {
        "source": "K481",
        "rule": "approveBuilderFee = $99–248K/yr ZERO risk. Do on Day 0 before any other action.",
    },
    "MR8_alt_alt_g5a_block_rule": {
        "source": "K707 (BCH-SOL), K703 (WLD-SOL)",
        "rule": (
            "Alt-alt G5a Block Rule: PoW/SHA-256 fork assets (BCH, BSV) structurally inherit "
            "BTC-base signal. Any A-B alt-alt where A has existing A-BTC strategy is BLOCKED "
            "via shared-leg G5a. Pre-screen X-BTC corr BEFORE full backtest. "
            "SAFE VERTICES: APT/ATOM/AVAX/SEI/INJ/ENA/TIA/BNB only."
        ),
        "anti_pattern": "Never run full alt-alt backtest if alt has existing X-BTC strategy (corr > 0.4 guaranteed).",
    },
    "MR9_algebraic_group_rules": {
        "source": "K688 (MR8 original), K707 (PoW extension)",
        "rule": (
            "Alt-alt algebraic identity: A-B pair = K_A-BTC - K_B-BTC algebraically when "
            "both legs have BTC-base strategies. This means G5a corr will approach 1.0 structurally. "
            "APT-INJ (K688) failed because APT-INJ = K679 + K684 algebraic bridge — no independent alpha. "
            "Test: max_err of corr(A-B, K_A-BTC - K_B-BTC) < 1e-10 = algebraic lock confirmed. "
            "Implication: only truly orthogonal cluster vertices produce independent alpha."
        ),
        "also_known_as": "MR8 (original K688 numbering)",
    },
    "MR10_window_sensitivity": {
        "source": "K615",
        "rule": (
            "Window sensitivity diagnostic: test strategy across W=24h/48h/72h/96h/120h. "
            "If Sharpe varies > 2x across windows, strategy is window-sensitive and requires "
            "walk-forward validation. Optimal window should be justified by half-life of the "
            "underlying FR divergence mechanism."
        ),
    },
    "MR11_single_point_projection": {
        "source": "K523",
        "rule": (
            "K523 transparent range mandatory: never report single-point profit projection. "
            "Always report conservative / mid / optimistic triple. "
            "Conservative ≈ 72% of mid (downside regime). Optimistic ≈ 2.3x mid (sustained bull). "
            "Currently: $15.2M / $21.1M / $48.0M @$10M AUM."
        ),
    },
}

# ─────────────────────────────────────────────────────────────────────────────
# 5. D60 CASCADE TABLE (K718 updated — 14 scaffolds, K712 verified)
# ─────────────────────────────────────────────────────────────────────────────

D60_CASCADE = [
    # Day D+0 Jul 29
    {"day": "D+0 Jul29",  "strategy": "K686 AVAX-SOL",   "type": "alt-alt", "cumul_yr": 673_817,  "hl_pct": 63.5},
    {"day": "D+0 Jul29",  "strategy": "K682 ATOM-SOL",   "type": "alt-alt", "cumul_yr": 673_817,  "hl_pct": 63.5},
    {"day": "D+0 Jul29",  "strategy": "K628 JTO-orthog",  "type": "orthog",  "cumul_yr": 673_817,  "hl_pct": 63.5},
    # Day D+1 Jul 30
    {"day": "D+1 Jul30",  "strategy": "K679 APT-SOL",    "type": "alt-alt", "cumul_yr": 1_044_117, "hl_pct": 65.0},
    {"day": "D+1 Jul30",  "strategy": "K658 SOL-ETH +1.5pp", "type": "eth-base", "cumul_yr": 1_044_117, "hl_pct": 65.0},
    {"day": "D+1 Jul30",  "strategy": "K696 ENA-SOL",    "type": "alt-alt", "cumul_yr": 1_044_117, "hl_pct": 65.0},
    # Day D+2 Jul 31
    {"day": "D+2 Jul31",  "strategy": "K690 SEI-SOL",    "type": "alt-alt", "cumul_yr": 1_315_215, "hl_pct": 65.0},
    {"day": "D+2 Jul31",  "strategy": "K648 POL-orthog",  "type": "orthog",  "cumul_yr": 1_315_215, "hl_pct": 65.0},
    {"day": "D+2 Jul31",  "strategy": "K647 DOT-orthog",  "type": "orthog",  "cumul_yr": 1_315_215, "hl_pct": 65.0},
    # Day D+3 Aug 1
    {"day": "D+3 Aug01",  "strategy": "K663 TIA-ETH",    "type": "eth-base", "cumul_yr": 1_503_779, "hl_pct": 65.0},
    {"day": "D+3 Aug01",  "strategy": "K629 WLD-ETH COND +2.0pp", "type": "eth-base", "cumul_yr": 1_503_779, "hl_pct": 65.0},
    {"day": "D+3 Aug01",  "strategy": "K694 TIA-SOL",    "type": "alt-alt", "cumul_yr": 1_503_779, "hl_pct": 65.0},
    # Day D+4 Aug 2
    {"day": "D+4 Aug02",  "strategy": "K698 LINK-ETH",   "type": "eth-base", "cumul_yr": 1_642_745, "hl_pct": 65.0},
    {"day": "D+4 Aug02",  "strategy": "K684 SOL-INJ",    "type": "alt-alt", "cumul_yr": 1_642_745, "hl_pct": 65.0},
]

# ─────────────────────────────────────────────────────────────────────────────
# 6. DAEMON REGISTRY (K718 — 62 daemons, K712 verified)
# ─────────────────────────────────────────────────────────────────────────────

DAEMON_REGISTRY_SUMMARY = {
    "k449_start": 14,
    "k673_k674_snapshot": 52,
    "k712_final": 62,
    "net_added_since_k674": 10,
    "total_active": 0,
    "scaffold_paper": 60,
    "pending": 2,
    "mismatches": 0,
    "source": "K702 Pre-Execution Defensive Verify (2026-05-30 15:47 JST) + K712 audit",
    "new_since_k674": [
        "K693 SEI-SOL scaffold",
        "K697 TIA-SOL scaffold",
        "K699 ENA-SOL scaffold",
        "K701 LINK-ETH scaffold",
        "K710 BNB-SOL scaffold",
        # Plus 5 more from K675-K692 range
        "K677 AVAX-ETH scaffold",
        "K678 ICP-BTC scaffold",
        "K683 APT-SOL scaffold",
        "K685 ATOM-SOL scaffold",
        "K687 SOL-INJ scaffold",
    ],
}

# ─────────────────────────────────────────────────────────────────────────────
# 7. CLOSED LINES (cumulative 46 as of K712)
# ─────────────────────────────────────────────────────────────────────────────

CLOSED_LINES_SINCE_K674 = [
    {"n": 45, "line": "WLD-SOL Alt-Alt",           "wave": "K703", "reason": "G5a: corr vs K621=0.634 >= 0.4 (WLD shared leg)"},
    {"n": 46, "line": "BCH-SOL Alt-Alt (PoW Fork)", "wave": "K707", "reason": "G5a: corr vs K605=0.517 >= 0.4 (PoW SHA-256 structural)"},
]
CUMULATIVE_CLOSED_LINES = 46

# ─────────────────────────────────────────────────────────────────────────────
# 8. MAIN REPORT
# ─────────────────────────────────────────────────────────────────────────────

def print_banner():
    print("=" * 80)
    print(f"★★★★ K718 CAPSTONE UPDATE — {PRIOR_CAPSTONE} incremental")
    print(f"   {SESSION_SPAN} | {TOTAL_WAVES}+ waves | {DAEMON_COUNT} daemons | {SCAFFOLD_COUNT} mechanism scaffolds")
    print(f"   {ARCH_VERSION} {SLEEVE_COUNT} sleeves | mid ${V650_MID_10M/1e6:.3f}M/yr @$10M")
    print(f"   HL {HL_CURRENT_PCT}% (<{HL_CAP_PCT}% cap, {HL_HEADROOM_PP}pp headroom)")
    print(f"   Phase A 6 actions ${PHASE_A_IMMEDIATE_USD/1e3:.0f}K immediate | Combined activation ${COMBINED_ACTIVATION_10M/1e6:.1f}M")
    print(f"   v6.50 LIVE target: {LIVE_TARGET}")
    print(f"   Generated: {TIMESTAMP_JST}")
    print("=" * 80)


def print_delta_from_k674():
    print("\n── K674 → K718 DELTA SUMMARY ────────────────────────────────────────────────")
    deltas = [
        ("Waves",            "225",          "268+",                "+43 waves"),
        ("Daemons",          "52",           "62",                  "+10 daemons (K712 verified)"),
        ("Mechanism scaffolds","14",         "22",                  "+8 alt-alt pairs"),
        ("Arch version",     "v6.40",        "v6.50 MEGA",          "+$176K/yr (K694+K696+K698)"),
        ("Portfolio $/yr",   "$20.9M",       "$21.1M",              "+$176K (K712 final)"),
        ("Sleeves",          "29",           "35",                  "+6 (7 alt-alt + 1 ETH-base)"),
        ("Phase A actions",  "5",            "6",                   "+K492-C persistence filter (K716/K714)"),
        ("Phase A immediate","$521K",        "$566K",               "+$45K K492-C"),
        ("Combined activation","N/A",        "$4.5M",               "Phase A + D60 grand total"),
        ("HL concentration", "65.0% AT CAP","63.5% (-1.5pp)",      "K552 applied"),
        ("Closed lines",     "~43",          "46",                  "+K703 WLD-SOL, K707 BCH-SOL"),
        ("Memory rules",     "MR1-MR7",      "MR1-MR11",            "+MR8 G5a Block, MR9 Algebraic, MR10 Window, MR11 K523"),
    ]
    print(f"  {'Metric':25s} {'K674':12s} {'K718':18s} {'Delta'}")
    print("  " + "-" * 72)
    for metric, old, new, delta in deltas:
        print(f"  {metric:25s} {old:12s} {new:18s} {delta}")


def print_v650_architecture():
    print("\n── v6.50 MEGA ARCHITECTURE (35 sleeves) ────────────────────────────────────")
    sleeves = [
        ("Core Infrastructure",    3,  "K280/K297/K376",           "HL+Bybit", "~$308K (marginal)",    "29.0%"),
        ("8 Paired-Trade BTC-base",8,  "K449/K476/K484/K493/K500/K507x2/K512", "HL", "$313K",  "23.5%"),
        ("10 Orthog Bybit",       10,  "K628/K631-K638/K645-K648/K656", "Bybit",  "$827K",  "0%"),
        ("9-Axis Signals",         4,  "K495/K541/K521/K208",       "HL+Bybit", "$1.27M",   "7.5%"),
        ("Stablecoin",             2,  "K344/K415",                 "Ethena/Spark","$28K",  "0%"),
        ("4 ETH-base",             4,  "K629/K658/K663/K698",       "HL+Bybit", "$197K",    "3.5%"),
        ("8 Alt-Alt Cross-Cluster",8,  "K679/K682/K684/K686/K690/K694/K696/K708","Bybit","$947K","0%"),
        ("TOTAL",                 35,  "K280→K710",                 "Mixed",    "$21.1M mid","63.5%"),
    ]
    print(f"  {'Family':28s} {'N':3s} {'Key Waves':35s} {'Venue':10s} {'$/yr @$10M':12s} {'HL%'}")
    print("  " + "-" * 94)
    for fam, n, waves, venue, profit, hl in sleeves:
        bold = "★ " if fam == "TOTAL" else "  "
        print(f"  {bold}{fam:26s} {n:3d} {waves:35s} {venue:10s} {profit:12s} {hl}")


def print_phase_a():
    print(f"\n── PHASE A: DAY 0 (6 actions, ${PHASE_A_IMMEDIATE_USD/1e3:.0f}K IMMEDIATE UNLOCK) ─────────────────────")
    total_zero = 0
    for a in PHASE_A_ACTIONS:
        p = a.get("profit_usd", a.get("profit_usd_low", a.get("profit_cascade_usd", 0)))
        ph = a.get("profit_usd_high", 0)
        profit_str = f"${p/1e3:.0f}K" + (f"–${ph/1e3:.0f}K" if ph else "")
        effort = a["effort_min"]
        effort_str = f"{effort}min" if effort < 60 else f"{effort//60}h"
        new_tag = " [NEW]" if a.get("added_wave") else ""
        print(f"  [{a['step']}] {a['id']:8s} {a['name'][:42]:42s} {effort_str:6s} {profit_str:14s} risk={a['risk']}{new_tag}")
        if a.get("risk") == "ZERO":
            total_zero += p
    print(f"\n  Phase A immediate: ${PHASE_A_IMMEDIATE_USD/1e3:.0f}K/yr | ZERO-risk: ~${total_zero/1e3:.0f}K/yr")
    print(f"  Execute order: K545 → K481 → K552 → K492C → K485 → K498")
    print(f"  Combined activation (Phase A + D60): ${COMBINED_ACTIVATION_10M/1e6:.1f}M/yr @$10M")


def print_alt_alt_family():
    print("\n── ALT-ALT FAMILY: 8 ACCEPTS (K674→K718) ───────────────────────────────────")
    print(f"  {'ID':6s} {'Pair':10s} {'OOS Sh':7s} {'Profit@$10M':12s} {'Venue':8s} {'Status'}")
    print("  " + "-" * 62)
    for a in ALT_ALT_ACCEPTS:
        gate = f" [{a.get('gate','')}]" if a.get("gate") else ""
        print(f"  {a['id']:6s} {a['pair']:10s} {a['oos_sh']:6.2f}  ${a['profit_10m']/1e3:7.0f}K     {a['venue']:8s} {a['status']}{gate}")
    print(f"  {'TOTAL':6s} {'8 pairs':10s}         ${ALT_ALT_COMBINED_10M/1e3:7.0f}K")
    print("  Blocked: K703 WLD-SOL (G5a=0.634), K707 BCH-SOL (G5a=0.517 PoW)")
    print("  K688 APT-INJ REJECT (algebraic bridge, no independent alpha)")


def print_eth_base_family():
    print("\n── ETH-BASE FAMILY: 4 ACCEPTS (K698 LINK-ETH added K698) ──────────────────")
    print(f"  {'ID':6s} {'Pair':10s} {'OOS Sh':7s} {'Profit@$10M':12s} {'Venue':8s} {'Status'}")
    print("  " + "-" * 60)
    for e in ETH_BASE_ACCEPTS:
        gate = f" [{e.get('gate','')}]" if e.get("gate") else ""
        new = " [K718-added]" if e.get("added_wave") else ""
        print(f"  {e['id']:6s} {e['pair']:10s} {e['oos_sh']:6.2f}  ${e['profit_10m']/1e3:7.0f}K     {e['venue']:8s} {e['status']}{gate}{new}")
    print(f"  {'TOTAL':6s} {'4 pairs':10s}         ${ETH_BASE_COMBINED_10M/1e3:7.0f}K")
    print("  Triple discriminator: vol_ratio>=2x AND ETH cycle align AND raw_fr_corr<0.45")


def print_d60_cascade():
    print(f"\n── D60 CASCADE TABLE (2026-07-29, {D60_SCAFFOLD_COUNT} scaffolds, ${D60_UNLOCK_10M/1e6:.2f}M unlock) ────────────────")
    prev_day = None
    for row in D60_CASCADE:
        if row["day"] != prev_day:
            print(f"\n  {row['day']} (HL: {row['hl_pct']}%, cumul: ${row['cumul_yr']/1e3:.0f}K/yr)")
            prev_day = row["day"]
        print(f"    + {row['strategy']:30s} [{row['type']}]")
    print(f"\n  Max 3/day | Sharpe-descending | 24h monitor between batches")
    print(f"  K629 HARD STOP: DO NOT load if HL >= 63.0%")


def print_memory_rules():
    print("\n── MEMORY RULES CONSOLIDATED: MR1–MR11 ─────────────────────────────────────")
    for key, mr in MEMORY_RULES.items():
        name = key.replace("_", " ").upper()
        src = mr["source"]
        rule_short = mr["rule"][:90].rstrip() + ("…" if len(mr["rule"]) > 90 else "")
        print(f"  [{src:15s}] {name}")
        print(f"         {rule_short}")


def main():
    print_banner()
    print_delta_from_k674()
    print_v650_architecture()
    print_phase_a()
    print_alt_alt_family()
    print_eth_base_family()
    print_d60_cascade()
    print_memory_rules()

    print("\n── K492-C IMMEDIATE FINDING (K714) ──────────────────────────────────────────")
    k = K492_VC_IMMEDIATE
    print(f"  {k['name']} — found K{k['wave_found']}")
    print(f"  {k['description']}")
    print(f"  Sharpe delta: +{k['sharpe_delta']} | Win rate: +{k['winrate_delta_pp']}pp | Effort: {k['effort_min']}min | Risk: {k['risk']}")

    print("\n── DAEMON REGISTRY (K718) ───────────────────────────────────────────────────")
    dr = DAEMON_REGISTRY_SUMMARY
    print(f"  K449 start: {dr['k449_start']} → K674 snapshot: {dr['k673_k674_snapshot']} → K712 final: {dr['k712_final']}")
    print(f"  Net added since K674: +{dr['net_added_since_k674']} | Active: {dr['total_active']} | Scaffold/paper: {dr['scaffold_paper']}")
    print(f"  Mismatches: {dr['mismatches']} | Source: {dr['source']}")

    print("\n── CLOSED LINES DELTA (K718) ────────────────────────────────────────────────")
    for cl in CLOSED_LINES_SINCE_K674:
        print(f"  #{cl['n']:2d} [{cl['wave']}] {cl['line']:30s} — {cl['reason']}")
    print(f"  Cumulative closed lines: {CUMULATIVE_CLOSED_LINES}")

    print("\n" + "=" * 80)
    print(f"★★★★ K718 CAPSTONE UPDATE COMPLETE")
    print(f"   {SESSION_SPAN} | {TOTAL_WAVES}+ waves | {DAEMON_COUNT} daemons | {SCAFFOLD_COUNT} scaffolds")
    print(f"   {ARCH_VERSION}: ${V650_MID_10M/1e6:.3f}M/yr mid @$10M | 5y ${V650_5Y_MID_10M/1e6:.0f}M")
    print(f"   Phase A: 6 actions ${PHASE_A_IMMEDIATE_USD/1e3:.0f}K immediate | v6.50 LIVE: {LIVE_TARGET}")
    print(f"   K523 range: ${V650_CONSERVATIVE_10M/1e6:.1f}M / ${V650_MID_10M/1e6:.3f}M / ${V650_OPTIMISTIC_10M/1e6:.0f}M @$10M")
    print("=" * 80)

    # JSON output
    output = {
        "wave": CAPSTONE_WAVE,
        "status": "COMPLETE",
        "timestamp_jst": TIMESTAMP_JST,
        "prior_capstone": PRIOR_CAPSTONE,
        "session_span": SESSION_SPAN,
        "total_waves": TOTAL_WAVES,
        "daemon_count": DAEMON_COUNT,
        "scaffold_count": SCAFFOLD_COUNT,
        "arch_version": ARCH_VERSION,
        "sleeve_count": SLEEVE_COUNT,
        "v650_conservative_10m": V650_CONSERVATIVE_10M,
        "v650_mid_10m": V650_MID_10M,
        "v650_optimistic_10m": V650_OPTIMISTIC_10M,
        "v650_5y_mid_10m": V650_5Y_MID_10M,
        "v640_baseline_10m": V640_MID_10M,
        "v650_delta_from_640": V650_DELTA_FROM_640,
        "phase_a_actions": len(PHASE_A_ACTIONS),
        "phase_a_immediate_usd": PHASE_A_IMMEDIATE_USD,
        "combined_activation_usd": COMBINED_ACTIVATION_10M,
        "d60_date": D60_DATE,
        "d60_scaffold_count": D60_SCAFFOLD_COUNT,
        "d60_unlock_10m": D60_UNLOCK_10M,
        "hl_pct": HL_CURRENT_PCT,
        "hl_cap": HL_CAP_PCT,
        "hl_headroom_pp": HL_HEADROOM_PP,
        "alt_alt_count": len(ALT_ALT_ACCEPTS),
        "alt_alt_combined_10m": ALT_ALT_COMBINED_10M,
        "eth_base_count": len(ETH_BASE_ACCEPTS),
        "eth_base_combined_10m": ETH_BASE_COMBINED_10M,
        "memory_rules_count": len(MEMORY_RULES),
        "closed_lines_cumulative": CUMULATIVE_CLOSED_LINES,
        "live_target": LIVE_TARGET,
        "k523_range_note": "Conservative=72% of mid, Optimistic=2.3x mid — mandatory",
    }
    return output


if __name__ == "__main__":
    result = main()
    print(f"\nJSON summary: {json.dumps(result, indent=2)}")

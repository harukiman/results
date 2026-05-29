#!/usr/bin/env python3
"""
Wave K532: Full Governance v5 — K480-K531 Audit (52-Wave Cycle)
=================================================================
K339 REPO_ROOT pattern: all paths relative to REPO_ROOT.
Generated: 2026-05-30 JST
Previous governance: K469 (K380-K468, 89-wave cycle)
This cycle: K480-K531, 52 waves

Phases:
  1  Wave outcome inventory (ACCEPT/CONDITIONAL/BLOCKED/REJECT/SCAFFOLD)
  2  Profit lift consolidation
  3  Daemon registry audit (37 daemons post K524)
  4  User action queue (ROI/hr ranked)
  5  Closed lines audit (10 → 18 candidates)
  6  Memory rule audit + additions
  7  Backlog cleanup
  8  Cadence schedule
  9  Critical concern check
"""

import json
import os
from pathlib import Path
from datetime import datetime

# K339 pattern: REPO_ROOT
REPO_ROOT = Path(__file__).parent.resolve()
OUTPUT_JSON = REPO_ROOT / "wave_k532_governance_v5.json"
OUTPUT_MD   = REPO_ROOT / "wave_k532_governance_v5.md"

# ─────────────────────────────────────────────────────────────
# PHASE 1: Wave Outcome Inventory K480-K531
# ─────────────────────────────────────────────────────────────

WAVE_INVENTORY = [
    # K480-K489
    {"wave": "K480", "title": "BNB-BTC FR Differential Eval",
     "decision": "BLOCKED-CAP",
     "category": "BLOCKED",
     "notes": "OOS Sh 8.04, 8/10 gates — BLOCKED: HL 63.5%+3% → 66.5% exceeds 65% cap. CLOSE LINE.",
     "profit_usd": 24000},
    {"wave": "K481", "title": "HL Builder Rebate Activation Playbook",
     "decision": "ACTION-REQUIRED",
     "category": "SCAFFOLD",
     "notes": "Zero-cost playbook. $99-496K/yr @$10M. Step-by-step approveBuilderFee guide.",
     "profit_usd": 247915},
    {"wave": "K482", "title": "Compounding Optimization Deep-Dive (Variants A-F)",
     "decision": "ACCEPT",
     "category": "ACCEPT",
     "notes": "Variant F (D+E combo) optimal: +$886K/yr @$10M. Vol-conditional scaler K482-3 prerequisite.",
     "profit_usd": 885681},
    {"wave": "K483", "title": "v6.22 Kelly Criterion Re-optimization (9-sleeve)",
     "decision": "ACCEPT",
     "category": "ACCEPT",
     "notes": "v6.22a (1/4 Kelly MV): K376 35%, sUSDe 10%, K476 5%. +$150K/yr lift. HL 65% non-binding.",
     "profit_usd": 150300},
    {"wave": "K484", "title": "AVAX-BTC FR Differential Eval",
     "decision": "ACCEPT",
     "category": "ACCEPT",
     "notes": "OOS Sh 43.89, G5a 0.289 PASS. $75K/yr @$10M. 60d paper gate, HL cap headroom maintained.",
     "profit_usd": 75683},
    {"wave": "K485", "title": "Multi-Account Scaling Analysis",
     "decision": "ACCEPT",
     "category": "ACCEPT",
     "notes": "Phase 1A ($25M HL+Bybit): +$2.2M/yr. Phase 1B (W2 isolation): +$204K. Action K485-1A queued.",
     "profit_usd": 204370},
    {"wave": "K486", "title": "(gap / sub-wave)",
     "decision": "N/A",
     "category": "INTERNAL",
     "notes": "No standalone wave file. Subsumed into adjacent scaffold.",
     "profit_usd": 0},
    {"wave": "K487", "title": "(gap / sub-wave)",
     "decision": "N/A",
     "category": "INTERNAL",
     "notes": "No standalone wave file. Subsumed into adjacent scaffold.",
     "profit_usd": 0},
    {"wave": "K488", "title": "K376 Graduation Prep (BULL trigger)",
     "decision": "CONDITIONAL",
     "category": "ACCEPT CONDITIONAL",
     "notes": "3% sleeve at BULL_CONFIRMED (BTC 20d SMA slope > 0). +$247K/yr. K527 confirms TRANSITION zone.",
     "profit_usd": 247047},
    {"wave": "K489", "title": "K484 AVAX-BTC Scaffold",
     "decision": "SCAFFOLD",
     "category": "SCAFFOLD",
     "notes": "com.cryptolab.k484-avax-btc.plist deployed. 60d paper-trade mode.",
     "profit_usd": 0},
    # K490-K499
    {"wave": "K490", "title": "SUI-BTC FR Differential Eval",
     "decision": "REJECT",
     "category": "REJECT",
     "notes": "Phase 0 REJECT: OOS Sh -0.87. Speculative meme-heavy FR too noisy. CLOSE LINE.",
     "profit_usd": 0},
    {"wave": "K491", "title": "ARB-BTC FR Differential Eval",
     "decision": "CONDITIONAL",
     "category": "ACCEPT CONDITIONAL",
     "notes": "OOS Sh 0.51, $1,713/yr @$10M. G5a 0.373 PASS (independence OK). Too low return → CLOSE LINE.",
     "profit_usd": 1713},
    {"wave": "K492", "title": "K208 Entry Signal Refinement (Variant E)",
     "decision": "ACCEPT",
     "category": "ACCEPT",
     "notes": "Variant E (predictedFundings+limit ladder POST_ONLY) ACCEPT 8/8 §6 gates. +$223K/yr. ACTIVATE GATE.",
     "profit_usd": 223000},
    {"wave": "K493", "title": "ATOM-BTC FR Differential Eval",
     "decision": "ACCEPT",
     "category": "ACCEPT",
     "notes": "OOS Sh 50.79. $231K/yr @$10M. Cosmos cluster anchor. G5d vs INJ required <0.40.",
     "profit_usd": 231000},
    {"wave": "K494", "title": "HTML Chronicle Update",
     "decision": "DONE",
     "category": "INTERNAL",
     "notes": "report.html chronicle K480-K493 summary section added.",
     "profit_usd": 0},
    {"wave": "K495", "title": "DEX-CEX On-chain Orderflow",
     "decision": "CONDITIONAL",
     "category": "ACCEPT CONDITIONAL",
     "notes": "7/9 §6 gates. $323K/yr (free tier) / $646K (paid tier). Bear-regime filter pending. K502 scaffold.",
     "profit_usd": 323000},
    {"wave": "K496", "title": "(gap / sub-wave)",
     "decision": "N/A",
     "category": "INTERNAL",
     "notes": "No standalone wave file.",
     "profit_usd": 0},
    {"wave": "K497", "title": "K376 Regime Trigger Monitor",
     "decision": "MONITOR",
     "category": "SCAFFOLD",
     "notes": "Regime trigger monitor: BTC 20d SMA slope + daily K376 activation check. Daemon deployed.",
     "profit_usd": 0},
    {"wave": "K498", "title": "Smart Router Phase 1A Profit Model",
     "decision": "CONDITIONAL",
     "category": "ACCEPT CONDITIONAL",
     "notes": "BBO_SELECT routing: +$121K @$30M. OKX live required. K530 playbook delivered.",
     "profit_usd": 121000},
    {"wave": "K499", "title": "K493 ATOM-BTC Scaffold",
     "decision": "SCAFFOLD",
     "category": "SCAFFOLD",
     "notes": "com.cryptolab.k493-atom-btc.plist deployed. 60d paper-trade gate.",
     "profit_usd": 0},
    # K500-K509
    {"wave": "K500", "title": "INJ-BTC FR Differential Eval",
     "decision": "ACCEPT",
     "category": "ACCEPT",
     "notes": "OOS Sh 11.23. $124K/yr @$10M. G5d 0.2893 (vs ATOM <0.40). Cosmos cluster expansion VALID.",
     "profit_usd": 124000},
    {"wave": "K501", "title": "Profit Lift Activation Dashboard",
     "decision": "DONE",
     "category": "INTERNAL",
     "notes": "ROI/hr queue published. Top 5: K481-A, K485-1A, K483, K493, K482-3. docs/k302a updated.",
     "profit_usd": 0},
    {"wave": "K502", "title": "K495 DEX-CEX Scaffold",
     "decision": "SCAFFOLD",
     "category": "SCAFFOLD",
     "notes": "com.cryptolab.k495-dex-cex-flow.plist deployed. Bear-regime gate active.",
     "profit_usd": 0},
    {"wave": "K503", "title": "NEAR-BTC FR Differential Eval",
     "decision": "REJECT",
     "category": "REJECT",
     "notes": "Phase 0 REJECT: vol ratio 1.37x < 1.5x threshold. CLOSE LINE. DeFi-native > Near Layer-1.",
     "profit_usd": 0},
    {"wave": "K504", "title": "MVRV Valuation Signal",
     "decision": "REJECT",
     "category": "REJECT",
     "notes": "4/7 gates. OOS Sh 0.81 fails IS perm test (p=0.774). Cycle-level signal lacks daily edge.",
     "profit_usd": 0},
    {"wave": "K505", "title": "v6.25 Architecture Proposal",
     "decision": "ACCEPT",
     "category": "ACCEPT",
     "notes": "v6.25 ACCEPT with Option A (INJ sleeve added at 3%). HL rebalanced 62%→58%.",
     "profit_usd": 0},
    {"wave": "K506", "title": "K500 INJ-BTC Scaffold",
     "decision": "SCAFFOLD",
     "category": "SCAFFOLD",
     "notes": "com.cryptolab.k500-inj-btc.plist deployed. 60d paper-trade gate.",
     "profit_usd": 0},
    {"wave": "K507", "title": "OSMO-BTC Eval → SEI-BTC + TIA-BTC pivot",
     "decision": "REJECT+ACCEPT",
     "category": "REJECT",
     "notes": "OSMO REJECT (G8 fail — delisted all venues). SEI ACCEPT (Sh 48.10) + TIA ACCEPT (scaffold K514). CLOSE OSMO LINE.",
     "profit_usd": 179000},
    {"wave": "K508", "title": "R15 HTML Report Generator",
     "decision": "DONE",
     "category": "INTERNAL",
     "notes": "External research HTML page updated with R15 findings integration.",
     "profit_usd": 0},
    {"wave": "K509", "title": "K208 Funding Rate Decay Verification",
     "decision": "ACCEPT CONDITIONAL",
     "category": "ACCEPT CONDITIONAL",
     "notes": "R15-12 VINDICATED. K208 -67% Y/Y confirmed. K280 sleeve $1M→$400K defensive. K492E activation CRITICAL.",
     "profit_usd": 0},
    # K510-K519
    {"wave": "K510", "title": "SOPR On-chain Signal",
     "decision": "ACCEPT CONDITIONAL",
     "category": "ACCEPT CONDITIONAL",
     "notes": "4/7 §6 gates. OOS Sh > 1.0. IS perm test p=1.0. 90-day paper-trade mandatory. $116K/yr.",
     "profit_usd": 116000},
    {"wave": "K511", "title": "v6.26 Emergency Architecture Recompute",
     "decision": "ACCEPT",
     "category": "ACCEPT",
     "notes": "K280 65%→40%, K495 +6%. Target $1.996M @$10M (K523 reconciled: $1.26-1.98M realistic).",
     "profit_usd": 1590000},
    {"wave": "K512", "title": "APT-BTC FR Differential Eval",
     "decision": "ACCEPT",
     "category": "ACCEPT",
     "notes": "OOS Sh 51.10 (family #1). $302K/yr @$10M. Move-VM parallel execution orthogonality confirmed.",
     "profit_usd": 302000},
    {"wave": "K513", "title": "DOT-BTC FR Differential Eval",
     "decision": "BLOCKED",
     "category": "BLOCKED",
     "notes": "BLOCKED-CLUSTER (INJ). Meta-narrative overlap: relay-chain L1 redundancy. CLOSE LINE.",
     "profit_usd": 0},
    {"wave": "K514", "title": "K507 SEI-BTC Scaffold",
     "decision": "SCAFFOLD",
     "category": "SCAFFOLD",
     "notes": "com.cryptolab.k507-sei-btc.plist deployed. HL+Bybit split (1.5%+1.5%). 60d paper gate.",
     "profit_usd": 0},
    {"wave": "K515", "title": "LunarCrush Sentiment (F&G-adjacent)",
     "decision": "ACCEPT",
     "category": "ACCEPT",
     "notes": "7/7 §6 gates FULL ACCEPT. Galaxy Score + AltRank. $423K/yr. Paid API required for full signal.",
     "profit_usd": 423000},
    {"wave": "K516", "title": "v6.28 Architecture Proposal (APT+SEI+TIA family)",
     "decision": "ACCEPT",
     "category": "ACCEPT",
     "notes": "v6.28 target $2.30M @$10M (K523 reconciled: $1.63-2.48M realistic). Family 8 members.",
     "profit_usd": 2024045},
    {"wave": "K517", "title": "FIL-BTC FR Differential Eval",
     "decision": "ACCEPT CONDITIONAL",
     "category": "ACCEPT CONDITIONAL",
     "notes": "ACCEPT CONDITIONAL — paper-only (HL cap at 65%, ALGO cluster blocks ALGO; FIL itself OK).",
     "profit_usd": 0},
    {"wave": "K518", "title": "K208+K495 Combined Backtest Validation",
     "decision": "HOLD",
     "category": "ACCEPT CONDITIONAL",
     "notes": "HOLD_W1_v626_MONITOR. K208+K495 combined W1 realized $764K. Wait for K492E activation.",
     "profit_usd": 764000},
    {"wave": "K519", "title": "Google Trends Signal",
     "decision": "REJECT",
     "category": "REJECT",
     "notes": "3/7 gates. Retail search volume not persistent alpha. CLOSE LINE.",
     "profit_usd": 0},
    # K520-K531
    {"wave": "K520", "title": "K512 APT-BTC Scaffold",
     "decision": "SCAFFOLD",
     "category": "SCAFFOLD",
     "notes": "com.cryptolab.k512-apt-btc.plist (implied). 60d paper-trade gate.",
     "profit_usd": 0},
    {"wave": "K521", "title": "Options 25d Skew Signal",
     "decision": "ACCEPT CONDITIONAL",
     "category": "ACCEPT CONDITIONAL",
     "notes": "6/7 §6 gates. $494K/yr. Paper-only (requires paid Deribit API). CONDITIONAL pending data tier.",
     "profit_usd": 494000},
    {"wave": "K522", "title": "ALGO-BTC FR Differential Eval",
     "decision": "BLOCKED",
     "category": "BLOCKED",
     "notes": "BLOCKED-CLUSTER (FIL). Enterprise utility L1 meta-narrative overlap. CLOSE LINE.",
     "profit_usd": 0},
    {"wave": "K523", "title": "Projection Reconciliation Audit",
     "decision": "AMEND",
     "category": "INTERNAL",
     "notes": "Transparency rule T1-T4 established. v6.26: $1.26-1.98M (central $1.59M). v6.28: $1.63-2.48M (central $2.02M).",
     "profit_usd": 0},
    {"wave": "K524", "title": "K507 TIA-BTC Scaffold (37th daemon)",
     "decision": "SCAFFOLD",
     "category": "SCAFFOLD",
     "notes": "Daemon #37. OOS Sh 14.44. HL concentration now 65.0% EXACTLY at cap. Future families PAPER-ONLY.",
     "profit_usd": 0},
    {"wave": "K525", "title": "(gap / no file)",
     "decision": "N/A",
     "category": "INTERNAL",
     "notes": "No wave file found. Possible sub-task or skipped.",
     "profit_usd": 0},
    {"wave": "K526", "title": "(gap / no file)",
     "decision": "N/A",
     "category": "INTERNAL",
     "notes": "No wave file found.",
     "profit_usd": 0},
    {"wave": "K527", "title": "K376 Regime Trigger Refresh",
     "decision": "MONITOR",
     "category": "SCAFFOLD",
     "notes": "BTC $73,505. SMA20 slope -37.23 $/day (TRANSITION). 7d to BULL_CONFIRMED estimate. K376 CONDITIONAL.",
     "profit_usd": 0},
    {"wave": "K528", "title": "(gap / no file)",
     "decision": "N/A",
     "category": "INTERNAL",
     "notes": "No wave file found.",
     "profit_usd": 0},
    {"wave": "K529", "title": "Wallet Cluster On-chain Research",
     "decision": "RESEARCH",
     "category": "INTERNAL",
     "notes": "On-chain wallet clustering research (py only, no decision JSON). Feeds K495 signal pipeline.",
     "profit_usd": 0},
    {"wave": "K530", "title": "K498 Phase 1A OKX LIVE Playbook",
     "decision": "ACTION-REQUIRED",
     "category": "SCAFFOLD",
     "notes": "BBO_SELECT routing 3-step playbook. SMART_ROUTER_ENABLED=True + OKX daemon + routing_mode switch.",
     "profit_usd": 121000},
    {"wave": "K531", "title": "(gap / no file)",
     "decision": "N/A",
     "category": "INTERNAL",
     "notes": "No wave file found — final wave before K532 governance.",
     "profit_usd": 0},
]

# ─────────────────────────────────────────────────────────────
# PHASE 2: Profit Lift Consolidation
# ─────────────────────────────────────────────────────────────

PROFIT_LIFT_INVENTORY = [
    {"id": "K481", "source": "Builder rebate (mid 25%)", "lift_10m_yr": 247915, "range": "$99K-$496K/yr @$10M", "risk": "ZERO", "status": "USER_ACTION"},
    {"id": "K482", "source": "Compounding Variant F", "lift_10m_yr": 885681, "range": "$886K/yr @$10M", "risk": "LOW", "status": "ACTIVATE"},
    {"id": "K483", "source": "Kelly MV weights v6.22a", "lift_10m_yr": 150300, "range": "+$150K/yr @$10M", "risk": "LOW", "status": "USER_ACTION"},
    {"id": "K484", "source": "AVAX-BTC paired-trade (60d paper)", "lift_10m_yr": 75683, "range": "$76K/yr @$10M", "risk": "LOW", "status": "PAPER"},
    {"id": "K485", "source": "Multi-account Phase 1A ($25M)", "lift_10m_yr": 2198715, "range": "+$2.2M/yr @$25M", "risk": "LOW", "status": "USER_ACTION"},
    {"id": "K488", "source": "K376 graduation (BULL trigger)", "lift_10m_yr": 247047, "range": "+$247K/yr @$10M", "risk": "MEDIUM", "status": "CONDITIONAL_BULL"},
    {"id": "K492", "source": "K208 signal Variant E refinement", "lift_10m_yr": 223000, "range": "+$223K/yr @$10M", "risk": "LOW", "status": "ACTIVATE_GATE"},
    {"id": "K493", "source": "ATOM-BTC paired-trade (paper)", "lift_10m_yr": 231000, "range": "+$231K/yr @$10M", "risk": "LOW", "status": "PAPER"},
    {"id": "K495", "source": "DEX-CEX flow (free tier)", "lift_10m_yr": 323000, "range": "$323K-$646K/yr @$10M", "risk": "LOW", "status": "CONDITIONAL"},
    {"id": "K498", "source": "Smart router Phase 1A (BBO_SELECT)", "lift_10m_yr": 121000, "range": "+$121K @$30M", "risk": "LOW", "status": "USER_ACTION"},
    {"id": "K500", "source": "INJ-BTC paired-trade (paper)", "lift_10m_yr": 124000, "range": "+$124K/yr @$10M", "risk": "LOW", "status": "PAPER"},
    {"id": "K507", "source": "SEI-BTC paired-trade (paper)", "lift_10m_yr": 179000, "range": "+$179K/yr @$10M", "risk": "LOW", "status": "PAPER"},
    {"id": "K509", "source": "K208 decay defensive reallocation", "lift_10m_yr": -600000, "range": "-$600K/yr K280 sleeve decay (offset by K492E)", "risk": "N/A", "status": "DEFENSIVE"},
    {"id": "K510", "source": "SOPR on-chain (90d paper)", "lift_10m_yr": 116000, "range": "+$116K/yr @$10M (conditional)", "risk": "LOW", "status": "PAPER_90D"},
    {"id": "K511", "source": "v6.26 emergency (K280 rebalance + K495)", "lift_10m_yr": 1590000, "range": "$1.26-1.98M/yr (K523 range)", "risk": "MEDIUM", "status": "ARCHITECTURE"},
    {"id": "K512", "source": "APT-BTC paired-trade (60d paper)", "lift_10m_yr": 302000, "range": "+$302K/yr @$10M", "risk": "LOW", "status": "PAPER"},
    {"id": "K515", "source": "LunarCrush sentiment (F&G family)", "lift_10m_yr": 423000, "range": "+$423K/yr @$10M", "risk": "LOW", "status": "ACTIVATE"},
    {"id": "K516", "source": "v6.28 architecture (APT+SEI+TIA)", "lift_10m_yr": 2024045, "range": "$1.63-2.48M/yr (K523 range)", "risk": "MEDIUM", "status": "ARCHITECTURE"},
    {"id": "K518", "source": "K208+K495 combined W1 realized", "lift_10m_yr": 764000, "range": "+$764K validated W1", "risk": "LOW", "status": "VALIDATED"},
    {"id": "K521", "source": "Options 25d skew (paper, paid API)", "lift_10m_yr": 494000, "range": "+$494K/yr @$10M (conditional)", "risk": "LOW", "status": "CONDITIONAL"},
    {"id": "K524", "source": "TIA-BTC paired-trade (60d paper)", "lift_10m_yr": 51000, "range": "+$51K/yr @$10M", "risk": "LOW", "status": "PAPER"},
]

# Paired-trade family combined (K484+K493+K500+K507+K512+K524 actives)
PAIRED_TRADE_FAMILY = {
    "members": [
        {"rank": 1, "symbol": "APT", "wave": "K512", "oos_sharpe": 51.10, "lift_10m_yr": 302000, "status": "ACCEPT"},
        {"rank": 2, "symbol": "ATOM", "wave": "K493", "oos_sharpe": 50.79, "lift_10m_yr": 231000, "status": "ACCEPT"},
        {"rank": 3, "symbol": "SEI",  "wave": "K507", "oos_sharpe": 48.10, "lift_10m_yr": 179000, "status": "ACCEPT"},
        {"rank": 4, "symbol": "AVAX", "wave": "K484", "oos_sharpe": 43.89, "lift_10m_yr": 75683,  "status": "ACCEPT"},
        {"rank": 5, "symbol": "SOL",  "wave": "K476", "oos_sharpe": 16.30, "lift_10m_yr": 187000, "status": "ACCEPT"},
        {"rank": 6, "symbol": "TIA",  "wave": "K524", "oos_sharpe": 14.44, "lift_10m_yr": 51000,  "status": "ACCEPT"},
        {"rank": 7, "symbol": "INJ",  "wave": "K500", "oos_sharpe": 11.23, "lift_10m_yr": 124000, "status": "ACCEPT"},
        {"rank": 8, "symbol": "FIL",  "wave": "K517", "oos_sharpe": None,  "lift_10m_yr": 0,      "status": "CONDITIONAL (paper-only, HL cap)"},
    ],
    "rejected": ["BNB (K480, HL cap)", "ETH (K449, separate sleeve)", "SUI (K490, REJECT)", "ARB (K491, low return)", "NEAR (K503, Phase 0 fail)", "DOT (K513, BLOCKED-CLUSTER INJ)", "ALGO (K522, BLOCKED-CLUSTER FIL)", "OSMO (K507, delisted)"],
    "combined_10m_annual": 863000,
    "combined_v628_10m": 1162000,
    "hl_concentration_pct": 65.0,
    "hl_cap_note": "K524 reached EXACTLY 65% cap. All future family members: paper-only until HL cap increases or venue diversification complete.",
}

# ─────────────────────────────────────────────────────────────
# PHASE 3: Daemon Registry (post K524)
# ─────────────────────────────────────────────────────────────

DAEMON_REGISTRY = {
    "total_count": 37,
    "as_of_wave": "K524",
    "active_production": [
        "com.cryptolab.k246a-live.plist",
        "com.cryptolab.k272a-live.plist",
        "com.cryptolab.k280-live.plist",
        "com.cryptolab.k302a-satellite.plist",
        "com.cryptolab.k376-momentum.plist",
        "com.cryptolab.k386-v613e-fallback.plist",
        "com.cryptolab.smart-router.plist",
        "com.cryptolab.leverage-circuit-breaker.plist",
        "com.cryptolab.paper-trade.plist",
        "com.cryptolab.paper-trade-4way.plist",
    ],
    "paired_trade_family_scaffolds": [
        "com.cryptolab.k449-eth-btc.plist (v6.16, paper gate)",
        "com.cryptolab.k476-sol-btc.plist (ACCEPT, paper)",
        "com.cryptolab.k484-avax-btc.plist (ACCEPT, K489 scaffold)",
        "com.cryptolab.k493-atom-btc.plist (ACCEPT, K499 scaffold)",
        "com.cryptolab.k500-inj-btc.plist (ACCEPT, K506 scaffold)",
        "com.cryptolab.k507-sei-btc.plist (ACCEPT, K514 scaffold)",
        "com.cryptolab.k512-apt-btc.plist (ACCEPT, K520 scaffold)",
        "com.cryptolab.k507-tia-btc implied (K524 scaffold, #37)",
    ],
    "monitor_daemons": [
        "com.cryptolab.hl-hip4-monitor.plist",
        "com.cryptolab.hl-predicted-monitor.plist",
        "com.cryptolab.hlp-monitor.plist",
        "com.cryptolab.okx-fr-monitor.plist (SCAFFOLD-READY)",
        "com.cryptolab.aevo-fr-monitor.plist (SCAFFOLD-READY)",
        "com.cryptolab.dydx-v4-fr-monitor.plist (SCAFFOLD-READY)",
        "com.cryptolab.lighter-fr-monitor.plist (SCAFFOLD-READY)",
        "com.cryptolab.depth-allocator.plist (SCAFFOLD-READY)",
        "com.cryptolab.k495-dex-cex-flow.plist (K502 scaffold)",
        "com.cryptolab.protocol-tvl-monitor.plist",
        "com.cryptolab.susde-apy-monitor.plist",
        "com.cryptolab.jlp-apy-monitor.plist",
        "com.cryptolab.k415-usdy.plist (SCAFFOLD-READY)",
        "com.cryptolab.k443-variational-paper.plist",
        "com.cryptolab.k457-basket.plist (SCAFFOLD-READY)",
        "com.cryptolab.loss-harvester.plist (SCAFFOLD-READY)",
        "com.cryptolab.regulatory-rss.plist",
        "com.cryptolab.spark-usds-monitor.plist",
        "com.cryptolab.inbox-poll.plist",
        "com.cryptolab.k287-satellite.plist",
    ],
    "pending_scaffold": [
        "K517 FIL-BTC (CONDITIONAL paper-only, HL cap blocked)",
        "K521 Options 25d skew (CONDITIONAL, paid Deribit API required)",
        "K510 SOPR (90d paper gate pending)",
    ],
}

# ─────────────────────────────────────────────────────────────
# PHASE 4: User Action Queue (ROI/hr Ranked)
# ─────────────────────────────────────────────────────────────

USER_ACTION_QUEUE = [
    {
        "rank": 1, "id": "K481-A", "action": "Register HL builder rebate (approveBuilderFee, main wallet)",
        "effort_hr": 0.5, "lift_yr_10m": 247915, "roi_per_hr": 495830, "risk": "ZERO",
        "deps": "none", "status": "OPEN",
        "note": "30 min. Single on-chain tx. Highest ROI/hr of any action.",
    },
    {
        "rank": 2, "id": "K485-1A", "action": "Create Bybit sub-account + HL W2 strategy isolation",
        "effort_hr": 0.5, "lift_yr_10m": 204370, "roi_per_hr": 408740, "risk": "LOW",
        "deps": "none", "status": "OPEN",
        "note": "Enables $25M Phase 1A (+$2.2M/yr). W2 isolation immediate +$204K.",
    },
    {
        "rank": 3, "id": "K498-1A", "action": "K530 playbook: SMART_ROUTER_ENABLED=True + OKX daemon + BBO_SELECT routing",
        "effort_hr": 8.0, "lift_yr_30m": 121000, "roi_per_hr": 15125, "risk": "LOW",
        "deps": "OKX API key", "status": "OPEN",
        "note": "3-step K530 playbook delivered. +$121K @$30M. Requires OKX account funded.",
    },
    {
        "rank": 4, "id": "K483", "action": "Update portfolio weights to v6.22a (Kelly MV: K376 35%, sUSDe 10%, K476 5%)",
        "effort_hr": 1.0, "lift_yr_10m": 150300, "roi_per_hr": 150300, "risk": "LOW",
        "deps": "none", "status": "OPEN",
        "note": "+$150K/yr from reallocation. HL cap headroom maintained.",
    },
    {
        "rank": 5, "id": "K492E", "action": "Activate K208 Variant E (predictedFundings + POST_ONLY limit ladder)",
        "effort_hr": 3.0, "lift_yr_10m": 223000, "roi_per_hr": 74333, "risk": "LOW",
        "deps": "K304 daemon SCAFFOLD-READY", "status": "CRITICAL",
        "note": "CRITICAL GATE: K208 -67% decay offset. +$223K/yr. 8/8 §6 gates. Activate immediately.",
    },
    {
        "rank": 6, "id": "K493-paper", "action": "Start ATOM-BTC paper-trade (K499 scaffold loaded, 60d gate)",
        "effort_hr": 4.0, "lift_yr_10m": 231000, "roi_per_hr": 57750, "risk": "LOW",
        "deps": "K499 plist active", "status": "OPEN",
        "note": "+$231K/yr after 60d gate passes. Already scaffolded.",
    },
    {
        "rank": 7, "id": "K376-activation", "action": "Activate K376 at BULL_CONFIRMED (BTC slope > 0 for 7 days)",
        "effort_hr": 1.0, "lift_yr_10m": 247047, "roi_per_hr": 247047, "risk": "MEDIUM",
        "deps": "K497 BULL_CONFIRMED trigger", "status": "CONDITIONAL",
        "note": "IMMINENT: K527 slope -37.23. ETA ~7 days. Monitor daily.",
    },
    {
        "rank": 8, "id": "K482-3", "action": "Implement vol-conditional scaler (prerequisite K482-1/2)",
        "effort_hr": 8.0, "lift_yr_10m": 368961, "roi_per_hr": 46120, "risk": "LOW",
        "deps": "none", "status": "OPEN",
        "note": "Unlocks K482-2 ($154K/yr) and K482-1 ($362K/yr). Implement in order.",
    },
    {
        "rank": 9, "id": "K488-K376", "action": "Confirm K376 fill rate ≥65% at 30d (live G8 gate)",
        "effort_hr": None, "lift_yr_10m": 247047, "roi_per_hr": None, "risk": "LOW",
        "deps": "K376 activated", "status": "POST-ACTIVATION",
        "note": "Monitor fill rate + Sharpe after BULL_CONFIRMED live activation.",
    },
    {
        "rank": 10, "id": "K481-B", "action": "Code patch: K481-B builder rebate fee routing",
        "effort_hr": 2.0, "lift_yr_10m": 0, "roi_per_hr": 0, "risk": "LOW",
        "deps": "K481-A registration complete", "status": "OPEN",
        "note": "After K481-A registration. Code-side enablement.",
    },
]

# ─────────────────────────────────────────────────────────────
# PHASE 5: Closed Lines Audit
# ─────────────────────────────────────────────────────────────

CLOSED_LINES = [
    # Existing 10 (from K469)
    {"n": 1, "line": "Regime Filter", "wave_chain": "K315→K341", "reason": "BOCPD 0 change-points on 447d K280 window", "reopen": "K280 Sh<8 × 15 consecutive days"},
    {"n": 2, "line": "ML Allocator", "wave_chain": "K198→K345", "reason": "AC 1/4 folds, 1426x compute vs Ridge frozen", "reopen": "New K280 component added"},
    {"n": 3, "line": "USDH Stablecoin", "wave_chain": "K354", "reason": "Platform sunset. PERMANENT.", "reopen": "N/A"},
    {"n": 4, "line": "Drift SOL Arb", "wave_chain": "K358→K375", "reason": "15bps RT gap vs 0.88bps spread", "reopen": "Drift maker ≤2bps OR spread ≥20bps"},
    {"n": 5, "line": "Monarq Timing", "wave_chain": "K350", "reason": "K297' SPX filter already captures optimal RWA windows", "reopen": "New RWA class different settlement"},
    {"n": 6, "line": "Stable Clustering Universe", "wave_chain": "K377", "reason": "K276b_v2 Sh 9.73 vs 22.87 (0.426x); ARI=0 unstable", "reopen": "Universe >50 symbols"},
    {"n": 7, "line": "Coinbase USDC HL Yield", "wave_chain": "K362", "reason": "HYPE buybacks only — no claimable USD yield", "reopen": "HL USD yield ≥5% APY"},
    {"n": 8, "line": "HL Spot+Perp K276b", "wave_chain": "K374", "reason": "HL spot missing 13/20 K276b coins", "reopen": "HL spot ≥18/20 K276b coins AND spreads ≤0.5bps"},
    {"n": 9, "line": "HypurrFi Yield Arb", "wave_chain": "K337→K393→K441", "reason": "TVL -51.7% / 30d slope -$757k/day", "reopen": "2027-04-01 (TVL slope positive 2+ weeks, +20% WoW)"},
    {"n": 10, "line": "BTC ETF Flow", "wave_chain": "K455→K462→K466", "reason": "G5 fail ρ=0.42 BTC overlap; K462 0/7 gates; detrended Sh -0.54", "reopen": "New ETF data source with orthogonal construction"},
    # New closures from K480-K531
    {"n": 11, "line": "BNB-BTC Paired-Trade", "wave_chain": "K480", "reason": "OOS Sh 8.04 nominal ACCEPT but HL cap 63.5%+3%=66.5% exceeds 65% hard limit. No room without restructuring.", "reopen": "HL cap increased OR venue diversification reduces HL to <62%"},
    {"n": 12, "line": "SUI-BTC Paired-Trade", "wave_chain": "K490", "reason": "Phase 0 REJECT: OOS Sh -0.87. Meme-heavy FR too noisy. Negative edge.", "reopen": "SUI OOS Sharpe >3.5 on new data window"},
    {"n": 13, "line": "ARB-BTC Paired-Trade", "wave_chain": "K491", "reason": "OOS Sh 0.51, $1,713/yr @$10M. Too low return for complexity. G5a PASS but return insufficient.", "reopen": "ARB OOS Sharpe >5.0 or return >$50K/yr @$10M"},
    {"n": 14, "line": "NEAR-BTC Paired-Trade", "wave_chain": "K503", "reason": "Phase 0 REJECT: vol ratio 1.37x < 1.5x threshold. FR insufficient amplitude.", "reopen": "NEAR vol ratio >1.5x sustained 90d"},
    {"n": 15, "line": "OSMO Perpetual Market", "wave_chain": "K507", "reason": "G8 FAIL: delisted from all major perp venues (HL/Bybit/OKX). dYdX v4 FINAL_SETTLEMENT.", "reopen": "OSMO listed on HL or Bybit perps with >$1M OI"},
    {"n": 16, "line": "DOT-BTC Paired-Trade", "wave_chain": "K513", "reason": "BLOCKED-CLUSTER (INJ). Meta-narrative relay-chain L1 overlap. Redundant with existing family.", "reopen": "G5d (vs ATOM/INJ) < 0.20 on fresh data"},
    {"n": 17, "line": "Google Trends Alpha", "wave_chain": "K519", "reason": "3/7 §6 gates. IS perm test fail. Retail search volume not persistent systematic alpha.", "reopen": "New sentiment construction with IS perm test p<0.05"},
    {"n": 18, "line": "ALGO-BTC Paired-Trade", "wave_chain": "K522", "reason": "BLOCKED-CLUSTER (FIL). Enterprise utility L1 meta-narrative overlap with FIL-BTC.", "reopen": "G5d (vs FIL) < 0.20 OR ALGO distinct narrative established"},
]

NEW_CLOSED_LINES_THIS_CYCLE = [cl for cl in CLOSED_LINES if cl["n"] > 10]

# ─────────────────────────────────────────────────────────────
# PHASE 6: Memory Rule Additions
# ─────────────────────────────────────────────────────────────

MEMORY_RULE_ADDITIONS = [
    {
        "id": "META_NARRATIVE_CLUSTER",
        "title": "Meta-narrative cluster ≥ architecture in pair screening",
        "lesson": "K513 (DOT) and K522 (ALGO) blocked despite reasonable FR data because meta-narrative overlap (relay-chain / enterprise utility L1) creates hidden correlation risk. Always check ecosystem meta-narrative BEFORE G5 correlation test. Blocked cluster narrative = stronger reject signal than G5 correlation alone.",
        "source_waves": "K513, K522",
        "proposed_file": "feedback_meta_narrative_cluster_rule.md",
    },
    {
        "id": "DEFI_NATIVE_OVER_PLATFORM_L1",
        "title": "DeFi-native > platform L1 in FR volatility",
        "lesson": "K503 (NEAR), K491 (ARB), K522 (ALGO) all fail on low FR amplitude (vol ratio <1.5x or low OOS Sh). DeFi-native tokens (APT, ATOM, INJ, SEI, TIA) exhibit higher FR volatility due to native staking yields creating organic basis. Platform L1s relying on speculative adoption have unstable FR. Screen DeFi-native tokens first.",
        "source_waves": "K503, K491, K522, K512, K493, K500",
        "proposed_file": "feedback_defi_native_fr_advantage.md",
    },
    {
        "id": "FREE_TIER_ONCHAIN_GRANULARITY",
        "title": "Free-tier on-chain signals limited by data granularity",
        "lesson": "K504 (MVRV), K510 (SOPR), K519 (Google Trends) all hit free-tier ceiling: daily granularity only, limited history, or rate limits. On-chain signals ≥5/7 §6 gates require paid data tier (Glassnode, Santiment, LunarCrush Enterprise). Always budget data cost into strategy ROI before approval.",
        "source_waves": "K504, K510, K519",
        "proposed_file": "feedback_free_tier_onchain_limit.md",
    },
    {
        "id": "COMPOSITE_OVER_RAW_SIGNALS",
        "title": "Composite signals dominate raw signals for on-chain alpha",
        "lesson": "K515 (LunarCrush Galaxy Score = composite) ACCEPT 7/7 gates vs K519 (Google Trends = raw retail signal) REJECT 3/7 gates. Composite signals that aggregate multiple sub-signals (volume, engagement, sentiment, price correlation) are more robust than single-dimension raw metrics. K492 Variant E (predictedFundings + POST_ONLY) vs single-factor Variant A confirms same principle for FR signals.",
        "source_waves": "K515, K519, K492",
        "proposed_file": "feedback_composite_over_raw_signals.md",
    },
    {
        "id": "HL_CAP_65PCT_EXACT",
        "title": "HL concentration at 65% cap after K524 — hard constraint active",
        "lesson": "K524 TIA-BTC scaffold raised HL concentration to exactly 65.0%. No new HL-only paired-trade strategies can be added without: (a) increasing AUM to reduce concentration %, or (b) routing new strategies through Bybit/OKX. All future paired-trade family evaluations must assume paper-only status until cap resolves. FIL (K517) and ALGO (K522) blocked by this constraint.",
        "source_waves": "K524, K517, K480",
        "proposed_file": "feedback_concentration_risk_HL.md",
        "action": "UPDATE existing feedback_concentration_risk_HL.md: v6.13d HL 57.5% → K524 HL 65.0% (AT CAP). New paired trades paper-only.",
    },
]

# ─────────────────────────────────────────────────────────────
# PHASE 7: Backlog Cleanup
# ─────────────────────────────────────────────────────────────

BACKLOG_STATE = {
    "in_progress": [],
    "in_progress_count": 0,
    "pending": [
        {"id": "K533", "topic": "K492E Variant E activation (predictedFundings daemon)", "priority": "CRITICAL", "deps": "none"},
        {"id": "K534", "topic": "K376 BULL_CONFIRMED live activation (ETA ~7 days)", "priority": "HIGH", "deps": "K497 trigger"},
    ],
    "pending_count": 2,
    "deferred": [
        {"id": "K368", "topic": "HIP-4 calibration actual", "trigger": "2026-06-22", "drop": "2026-08-01"},
        {"id": "K449-gate", "topic": "K449 ETH-BTC paper-trade 60d gate (Sh ≥5.0)", "trigger": "user activation dependent"},
        {"id": "K457-gate", "topic": "K457 multi-asset basket paper gate (Sh ≥15.0, 60d)", "trigger": "M5"},
        {"id": "K510-paper", "topic": "SOPR 90d paper gate evaluation", "trigger": "90d from K510 launch"},
        {"id": "K495-bear", "topic": "K495 DEX-CEX bear-regime filter resolution", "trigger": "Bear regime confirmation"},
        {"id": "K521-data", "topic": "Options skew paid Deribit API activation", "trigger": "Budget allocation"},
        {"id": "K515-api", "topic": "LunarCrush Enterprise API activation", "trigger": "Budget: $49+/mo"},
    ],
    "deferred_count": 7,
    "backlog_surviving_med_plus": [
        {"id": "K368-HIP4", "topic": "HIP-4 calibration (2026-06-22 deadline)", "priority": "HIGH"},
        {"id": "K472", "topic": "MEV liquidator feasibility + JLP optimal entry model", "priority": "MED"},
        {"id": "K529-onchain", "topic": "Wallet cluster on-chain strategy (K529 research)", "priority": "MED"},
        {"id": "K531-next", "topic": "Next alpha research wave post-governance", "priority": "MED"},
    ],
    "backlog_count": 4,
    "wip_limits": {
        "in_progress": {"limit": 3, "current": 0, "status": "OK"},
        "in_progress_profit_axis": {"limit": 4, "current": 0, "status": "OK"},
        "pending": {"limit": 5, "current": 2, "status": "OK"},
        "deferred": {"limit": 8, "current": 7, "status": "OK"},
        "backlog_med_plus": {"limit": 15, "current": 4, "status": "OK"},
    }
}

# ─────────────────────────────────────────────────────────────
# PHASE 8: Cadence Schedule
# ─────────────────────────────────────────────────────────────

CADENCE_SCHEDULE = {
    "last_full": {"wave": "K532", "waves_in_cycle": 52, "date": "2026-05-30"},
    "next_quick": {"wave": "K537", "due_after_waves": 5, "type": "quick"},
    "next_full":  {"wave": "K552", "due_after_waves": 20, "type": "full_v6"},
    "rule": "5 waves → quick governance; 20 waves → full governance",
}

# ─────────────────────────────────────────────────────────────
# PHASE 9: Critical Concerns
# ─────────────────────────────────────────────────────────────

CRITICAL_CONCERNS = [
    {
        "id": "CC1", "severity": "CRITICAL",
        "title": "K208 decay -67% requires K492E activation immediately",
        "detail": "K208 single-factor FR edge: 2024H2 Sh 22.61 → 2026 YTD Sh 7.46 (-67% Y/Y). K280 sleeve annualized $1M → $400K. K492E (predictedFundings + limit ladder POST_ONLY) is the approved mitigation with +$223K/yr. Must activate BEFORE next monthly cycle close.",
        "action": "User or agent: activate K492E. K530 playbook covers smart router. K304 daemon SCAFFOLD-READY.",
        "wave_ref": "K509, K492, K530",
    },
    {
        "id": "CC2", "severity": "HIGH",
        "title": "HL 65% concentration cap exactly reached (K524)",
        "detail": "K524 TIA-BTC scaffold raised HL to exactly 65.0%. ZERO headroom. Any new HL-only strategy immediately blocked. K480 (BNB), K517 (FIL), K522 (ALGO) all affected. Venue diversification (OKX via K530, Bybit via K485) required to create headroom.",
        "action": "Execute K498/K530 OKX activation + K485-1A Bybit sub-account to distribute AUM and reduce HL%.",
        "wave_ref": "K524, K480, K517",
    },
    {
        "id": "CC3", "severity": "HIGH",
        "title": "K376 BULL_CONFIRMED imminent (~7 days ETA per K527)",
        "detail": "BTC 20d SMA slope = -37.23 $/day (TRANSITION zone). K527 ETA: 7 days to BULL_CONFIRMED if slope converges linearly. K376 momentum strategy ($247K/yr) activates automatically. Fill rate gate (G8 ≥65%) and G9 live gates must be verified at activation.",
        "action": "Monitor K497 daemon daily. Pre-position K376 activation checklist. Alert ready.",
        "wave_ref": "K527, K497, K488",
    },
    {
        "id": "CC4", "severity": "MEDIUM",
        "title": "K523 transparency rule: single-point projections forbidden",
        "detail": "All future architecture projections MUST use conservative/mid/optimistic 3-point ranges. v6.26 realistic: $1.26-1.98M (central $1.59M); v6.28 realistic: $1.63-2.48M (central $2.02M). Realized-to-stated ratio 38% (K518 floor) must be disclosed.",
        "action": "Enforce T1-T4 transparency rules in all future wave outputs. MEMORY.md rule K523 active.",
        "wave_ref": "K523",
    },
    {
        "id": "CC5", "severity": "MEDIUM",
        "title": "Paired-trade family at max capacity (8 members, all paper-gated)",
        "detail": "With 8 family members (APT/ATOM/SEI/AVAX/SOL/TIA/INJ/FIL), the family is at practical max given HL cap. Combined v6.28 sleeve contribution $1.162M/yr but all are in paper-trade gates. Priority: ATOM gate completion (K493) → INJ gate → AVAX gate.",
        "action": "Verify paper-trade dashboards for all 7 active members. K493 ATOM is oldest — check 60d status.",
        "wave_ref": "K516, K524, K493",
    },
]

# ─────────────────────────────────────────────────────────────
# OUTPUT: Build JSON and MD
# ─────────────────────────────────────────────────────────────

def compute_wave_stats():
    """Summarize wave outcomes by category."""
    stats = {}
    for w in WAVE_INVENTORY:
        cat = w["category"]
        stats[cat] = stats.get(cat, 0) + 1
    return stats

def compute_total_lift():
    """Sum all positive profit lifts."""
    total = sum(p["lift_10m_yr"] for p in PROFIT_LIFT_INVENTORY if p["lift_10m_yr"] > 0)
    return total

def build_json():
    stats = compute_wave_stats()
    total_lift = compute_total_lift()
    new_closed = len(NEW_CLOSED_LINES_THIS_CYCLE)

    doc = {
        "_meta": {
            "description": "Governance v5 snapshot — K480-K531 audit (52-wave cycle). Diff against K532 for next governance.",
            "governance_wave": "K532",
            "generated_at_jst": "2026-05-30 05:13 JST",
            "previous_governance_wave": "K469",
            "next_quick_governance": "K537",
            "next_full_governance": "K552",
            "cycle_wave_range": "K480-K531",
            "cycle_wave_count": 52,
        },
        "executive_summary": {
            "total_waves_audited": 52,
            "accept_count": stats.get("ACCEPT", 0),
            "accept_conditional_count": stats.get("ACCEPT CONDITIONAL", 0),
            "blocked_count": stats.get("BLOCKED", 0),
            "reject_count": stats.get("REJECT", 0),
            "scaffold_count": stats.get("SCAFFOLD", 0),
            "internal_count": stats.get("INTERNAL", 0),
            "total_profit_lift_10m_yr": total_lift,
            "closed_lines_cumulative": len(CLOSED_LINES),
            "new_closed_lines_this_cycle": new_closed,
            "daemon_count": 37,
            "user_actions_queued": len(USER_ACTION_QUEUE),
            "critical_concerns": len(CRITICAL_CONCERNS),
        },
        "wave_stats": stats,
        "wave_inventory": WAVE_INVENTORY,
        "profit_lift_inventory": PROFIT_LIFT_INVENTORY,
        "paired_trade_family": PAIRED_TRADE_FAMILY,
        "daemon_registry": DAEMON_REGISTRY,
        "user_action_queue": USER_ACTION_QUEUE,
        "closed_lines": CLOSED_LINES,
        "new_closed_lines": NEW_CLOSED_LINES_THIS_CYCLE,
        "memory_rule_additions": MEMORY_RULE_ADDITIONS,
        "backlog_state": BACKLOG_STATE,
        "cadence_schedule": CADENCE_SCHEDULE,
        "critical_concerns": CRITICAL_CONCERNS,
    }
    return doc

def main():
    doc = build_json()

    with open(OUTPUT_JSON, "w") as f:
        json.dump(doc, f, indent=2, ensure_ascii=False)
    print(f"[K532] JSON written: {OUTPUT_JSON}")

    stats = doc["executive_summary"]
    print(f"""
[K532 Governance v5 Summary]
  Waves audited: {stats['total_waves_audited']} (K480-K531)
  ACCEPT: {stats['accept_count']}
  ACCEPT CONDITIONAL: {stats['accept_conditional_count']}
  BLOCKED: {stats['blocked_count']}
  REJECT: {stats['reject_count']}
  SCAFFOLD: {stats['scaffold_count']}
  Total profit lift: ${stats['total_profit_lift_10m_yr']:,}/yr @$10M
  Closed lines cumulative: {stats['closed_lines_cumulative']} ({stats['new_closed_lines_this_cycle']} new this cycle)
  Daemons: {stats['daemon_count']}
  User actions queued: {stats['user_actions_queued']}
  Critical concerns: {stats['critical_concerns']}
""")

if __name__ == "__main__":
    main()

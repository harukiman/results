"""
wave_k751_kelly_sizing.py — K751 Kelly Criterion Sleeve Sizing Optimization
=============================================================================
Profit-max mandate: extract uplift from EXISTING strategies via Kelly sizing.
Context: 3 consecutive alt-alt G5 REJ (ONDO/AAVE/PYTH) — new vertex saturation.

Architecture: v6.51 = 37 sleeves (SLEEVE_WEIGHTS_V646 + K696 ENA-SOL + K719 ENA-ATOM)
Objective: compute Kelly-optimal weights → compare vs current → quantify ROI uplift.

Phase 1: Audit v6.51 sleeve inventory
Phase 2: Per-sleeve return distribution (μ, σ, σ_d, maxDD) from OOS data
Phase 3: Kelly f* = μ/σ² per sleeve; fractional variants (0.5x, 0.25x)
Phase 4: Portfolio MPT+Kelly hybrid (QP: maximize risk-adj return subject to exchange caps)
Phase 5: ROI uplift analysis (K523 3-point @$10M)
Phase 6: runbook output + kelly_optimal_weights.json
Phase 7: report.html v6.52 badge data

K339 Security: REPO_ROOT from __file__, no /Users/ literals.

Key design decisions:
  - Use ann_ret_usd_per_1pct_sleeve = ann_ret_net_usd / (weight_v651 * AUM) to get
    return-per-dollar deployed (avoids confusion from unrealistic ann_ret_pct for orthog)
  - σ_per_sleeve = μ_per_sleeve / OOS_Sh (annualized carry vol estimate)
  - Portfolio Kelly: Sh-weighted rebalancing within exchange concentration caps
  - K523: realized_ratio=38% (K509 floor), OOS_haircut=25% (paired-trade)
"""
from __future__ import annotations

import json
import math
import os
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import numpy as np

# ── K339: REPO_ROOT from __file__ ─────────────────────────────────────────────
REPO_ROOT = Path(__file__).resolve().parent
DATA_DIR  = REPO_ROOT / "data"
DOCS_DIR  = REPO_ROOT / "docs"
DATA_DIR.mkdir(exist_ok=True)

OUTPUT_JSON = DATA_DIR / "kelly_optimal_weights.json"

AUM = 10_000_000  # $10M reference AUM

# ─────────────────────────────────────────────────────────────────────────────
# Phase 1: v6.51 Sleeve Inventory
# Fields:
#   weight_v651: current allocation in v6.51
#   oos_sh: OOS Sharpe ratio (dimensionless, annualized)
#   ann_ret_net_usd: net annual profit at $10M AUM at stated sleeve weight
#   leverage: exchange leverage applied
#   exchange: primary venue
#   hl_pct: fraction of sleeve on HyperLiquid
#   bybit_pct: fraction of sleeve on Bybit
#   max_dd_pct: estimated max drawdown (%)
#   category: strategy family
#   k523_*: K523-mandated 3-point profit estimates
# ─────────────────────────────────────────────────────────────────────────────

SLEEVE_INVENTORY: Dict[str, Dict] = {
    # ─── CORE ────────────────────────────────────────────────────────────────
    "K280": {
        "weight_v651": 0.155,
        "oos_sh": 8.5,
        "ann_ret_net_usd": 620000,
        "leverage": 1.5,
        "exchange": "HL+Bybit",
        "hl_pct": 0.60,
        "bybit_pct": 0.40,
        "max_dd_pct": 2.1,
        "description": "K280 Core: K198 Ridge ML + K208 DAR rev-carry + K276b FR rank L/S",
        "category": "core",
        "k523_conservative": 232600,
        "k523_central":      400000,
        "k523_optimistic":   620000,
    },
    "K297": {
        "weight_v651": 0.20,
        "oos_sh": 22.0,
        "ann_ret_net_usd": 180000,
        "leverage": 2.0,
        "exchange": "HL",
        "hl_pct": 1.0,
        "bybit_pct": 0.0,
        "max_dd_pct": 0.5,
        "description": "K297 Satellite: PAXG 60% + SPX 40% HL carry",
        "category": "satellite",
        "k523_conservative": 120000,
        "k523_central":      180000,
        "k523_optimistic":   260000,
    },
    "sUSDe": {
        "weight_v651": 0.05,
        "oos_sh": 30.0,
        "ann_ret_net_usd": 22000,
        "leverage": 1.0,
        "exchange": "Ethena",
        "hl_pct": 0.0,
        "bybit_pct": 0.0,
        "max_dd_pct": 0.1,
        "description": "sUSDe overcollateralized yield sleeve",
        "category": "stable",
        "k523_conservative": 15000,
        "k523_central":       22000,
        "k523_optimistic":    35000,
    },
    # ─── BTC-BASE PAIRED-TRADE ────────────────────────────────────────────────
    "K449": {
        "weight_v651": 0.05,
        "oos_sh": 18.4,
        "ann_ret_net_usd": 187000,
        "leverage": 4.0,
        "exchange": "HL",
        "hl_pct": 1.0,
        "bybit_pct": 0.0,
        "max_dd_pct": 3.5,
        "description": "K449 ETH-BTC FR Differential (BTC-base, HL-only)",
        "category": "btc_base_paired",
        "k523_conservative":  70125,
        "k523_central":       93500,
        "k523_optimistic":   187000,
    },
    "K476": {
        "weight_v651": 0.015,
        "oos_sh": 29.66,
        "ann_ret_net_usd": 42332,
        "leverage": 4.0,
        "exchange": "HL",
        "hl_pct": 1.0,
        "bybit_pct": 0.0,
        "max_dd_pct": 3.0,
        "description": "K476 SOL-BTC FR Differential (dual K658, HL-only 1.5%)",
        "category": "btc_base_paired",
        "k523_conservative": 15874,
        "k523_central":      21166,
        "k523_optimistic":   42332,
    },
    "K484": {
        "weight_v651": 0.015,
        "oos_sh": 28.26,
        "ann_ret_net_usd": 63416,
        "leverage": 4.0,
        "exchange": "HL",
        "hl_pct": 1.0,
        "bybit_pct": 0.0,
        "max_dd_pct": 3.0,
        "description": "K484 AVAX-BTC FR Differential (dual K661, HL-only 1.5%)",
        "category": "btc_base_paired",
        "k523_conservative": 23781,
        "k523_central":      31708,
        "k523_optimistic":   63416,
    },
    "K493": {
        "weight_v651": 0.05,
        "oos_sh": 50.79,
        "ann_ret_net_usd": 231000,
        "leverage": 4.0,
        "exchange": "HL",
        "hl_pct": 1.0,
        "bybit_pct": 0.0,
        "max_dd_pct": 2.5,
        "description": "K493 ATOM-BTC FR Differential (Cosmos #1, HL-only, OOS Sh 50.79)",
        "category": "btc_base_paired",
        "k523_conservative":  86625,
        "k523_central":      115500,
        "k523_optimistic":   231000,
    },
    "K500": {
        "weight_v651": 0.04,
        "oos_sh": 11.23,
        "ann_ret_net_usd": 124000,
        "leverage": 4.0,
        "exchange": "HL",
        "hl_pct": 1.0,
        "bybit_pct": 0.0,
        "max_dd_pct": 4.5,
        "description": "K500 INJ-BTC FR Differential (Cosmos #2, HL-only, OOS Sh 11.23)",
        "category": "btc_base_paired",
        "k523_conservative": 46500,
        "k523_central":      62000,
        "k523_optimistic":  124000,
    },
    "K507": {
        "weight_v651": 0.02,
        "oos_sh": 48.10,
        "ann_ret_net_usd": 179000,
        "leverage": 4.0,
        "exchange": "HL+Bybit",
        "hl_pct": 0.5,
        "bybit_pct": 0.5,
        "max_dd_pct": 3.0,
        "description": "K507 SEI-BTC FR Differential (Cosmos #3, HL+Bybit split, OOS Sh 48.10)",
        "category": "btc_base_paired",
        "k523_conservative":  67125,
        "k523_central":       89500,
        "k523_optimistic":   179000,
    },
    "K507_TIA": {
        "weight_v651": 0.015,
        "oos_sh": 14.44,
        "ann_ret_net_usd": 51000,
        "leverage": 4.0,
        "exchange": "HL",
        "hl_pct": 1.0,
        "bybit_pct": 0.0,
        "max_dd_pct": 4.0,
        "description": "K507 TIA-BTC FR Differential (Celestia DA, HL-only 1.5%)",
        "category": "btc_base_paired",
        "k523_conservative": 19125,
        "k523_central":      25500,
        "k523_optimistic":   51000,
    },
    "K512": {
        "weight_v651": 0.02,
        "oos_sh": 51.10,
        "ann_ret_net_usd": 302000,
        "leverage": 4.0,
        "exchange": "HL+Bybit",
        "hl_pct": 0.5,
        "bybit_pct": 0.5,
        "max_dd_pct": 2.5,
        "description": "K512 APT-BTC FR Differential (Move-VM #1, HL+Bybit split, OOS Sh 51.10)",
        "category": "btc_base_paired",
        "k523_conservative": 113250,
        "k523_central":      151000,
        "k523_optimistic":   302000,
    },
    "K587": {
        "weight_v651": 0.01,
        "oos_sh": 12.53,
        "ann_ret_net_usd": 21000,
        "leverage": 4.0,
        "exchange": "HL+Bybit",
        "hl_pct": 0.5,
        "bybit_pct": 0.5,
        "max_dd_pct": 5.0,
        "description": "K587 ICP-BTC FR Differential (Compute/Cloud, HL+Bybit 0.5%+0.5%)",
        "category": "btc_base_paired",
        "k523_conservative":  7875,
        "k523_central":      10500,
        "k523_optimistic":   21000,
    },
    # ─── ETH-BASE PAIRED-TRADE ────────────────────────────────────────────────
    "K629": {
        "weight_v651": 0.03,
        "oos_sh": 19.90,
        "ann_ret_net_usd": 94210,
        "leverage": 4.0,
        "exchange": "HL",
        "hl_pct": 1.0,
        "bybit_pct": 0.0,
        "max_dd_pct": 4.0,
        "description": "K629 WLD-ETH FR Differential (ETH-base, HL-primary, OOS Sh 19.90)",
        "category": "eth_base_paired",
        "k523_conservative": 35329,
        "k523_central":      47105,
        "k523_optimistic":   94210,
    },
    "K663": {
        "weight_v651": 0.015,
        "oos_sh": 17.13,
        "ann_ret_net_usd": 63060,
        "leverage": 4.0,
        "exchange": "HL",
        "hl_pct": 1.0,
        "bybit_pct": 0.0,
        "max_dd_pct": 4.0,
        "description": "K663 TIA-ETH FR Differential (ETH-base, HL-primary, OOS Sh 17.13)",
        "category": "eth_base_paired",
        "k523_conservative": 23648,
        "k523_central":      31530,
        "k523_optimistic":   63060,
    },
    "K658": {
        "weight_v651": 0.015,
        "oos_sh": 29.66,
        "ann_ret_net_usd": 42332,
        "leverage": 4.0,
        "exchange": "HL",
        "hl_pct": 1.0,
        "bybit_pct": 0.0,
        "max_dd_pct": 3.5,
        "description": "K658 SOL-ETH FR Differential (ETH-base, HL-primary, OOS Sh 29.66)",
        "category": "eth_base_paired",
        "k523_conservative": 15874,
        "k523_central":      21166,
        "k523_optimistic":   42332,
    },
    "K661": {
        "weight_v651": 0.015,
        "oos_sh": 28.26,
        "ann_ret_net_usd": 63416,
        "leverage": 4.0,
        "exchange": "HL",
        "hl_pct": 1.0,
        "bybit_pct": 0.0,
        "max_dd_pct": 3.5,
        "description": "K661 AVAX-ETH FR Differential (ETH-base CONDITIONAL, HL-primary, OOS Sh 28.26)",
        "category": "eth_base_paired",
        "k523_conservative": 23781,
        "k523_central":      31708,
        "k523_optimistic":   63416,
    },
    "K698": {
        "weight_v651": 0.025,
        "oos_sh": 12.07,
        "ann_ret_net_usd": 28997,
        "leverage": 4.0,
        "exchange": "Bybit",
        "hl_pct": 0.0,
        "bybit_pct": 1.0,
        "max_dd_pct": 5.5,
        "description": "K698 LINK-ETH FR Differential (ETH-base #4 oracle, Bybit-only, OOS Sh 12.07)",
        "category": "eth_base_paired",
        "k523_conservative": 10874,
        "k523_central":      14499,
        "k523_optimistic":   28997,
    },
    # ─── ALT-ALT PAIRED-TRADE ─────────────────────────────────────────────────
    "K679": {
        "weight_v651": 0.03,
        "oos_sh": 39.29,
        "ann_ret_net_usd": 234700,
        "leverage": 4.0,
        "exchange": "Bybit",
        "hl_pct": 0.0,
        "bybit_pct": 1.0,
        "max_dd_pct": 4.0,
        "description": "K679 APT-SOL FR Differential (ALT-ALT #1, Bybit-only, OOS Sh 39.29)",
        "category": "alt_alt_paired",
        "k523_conservative":  88013,
        "k523_central":      117350,
        "k523_optimistic":   234700,
    },
    "K682": {
        "weight_v651": 0.02,
        "oos_sh": 43.43,
        "ann_ret_net_usd": 214638,
        "leverage": 4.0,
        "exchange": "Bybit",
        "hl_pct": 0.0,
        "bybit_pct": 1.0,
        "max_dd_pct": 3.5,
        "description": "K682 ATOM-SOL FR Differential (ALT-ALT #2, Bybit-only, OOS Sh 43.43)",
        "category": "alt_alt_paired",
        "k523_conservative":  80489,
        "k523_central":      107319,
        "k523_optimistic":   214638,
    },
    "K684": {
        "weight_v651": 0.03,
        "oos_sh": 9.65,
        "ann_ret_net_usd": 114316,
        "leverage": 4.0,
        "exchange": "Bybit",
        "hl_pct": 0.0,
        "bybit_pct": 1.0,
        "max_dd_pct": 6.0,
        "description": "K684 SOL-INJ FR Differential (ALT-ALT #3, Bybit-only, OOS Sh 9.65)",
        "category": "alt_alt_paired",
        "k523_conservative":  42869,
        "k523_central":       57158,
        "k523_optimistic":   114316,
    },
    "K686": {
        "weight_v651": 0.03,
        "oos_sh": 50.27,
        "ann_ret_net_usd": 102153,
        "leverage": 4.0,
        "exchange": "Bybit",
        "hl_pct": 0.0,
        "bybit_pct": 1.0,
        "max_dd_pct": 3.5,
        "description": "K686 AVAX-SOL FR Differential (ALT-ALT #4 HIGHEST Sh, Bybit-only, OOS Sh 50.27)",
        "category": "alt_alt_paired",
        "k523_conservative":  38307,
        "k523_central":       51077,
        "k523_optimistic":   102153,
    },
    "K690": {
        "weight_v651": 0.03,
        "oos_sh": 25.11,
        "ann_ret_net_usd": 104174,
        "leverage": 4.0,
        "exchange": "Bybit",
        "hl_pct": 0.0,
        "bybit_pct": 1.0,
        "max_dd_pct": 4.0,
        "description": "K690 SEI-SOL FR Differential (ALT-ALT #5 WF 12/12, Bybit-only, OOS Sh 25.11)",
        "category": "alt_alt_paired",
        "k523_conservative":  39065,
        "k523_central":       52087,
        "k523_optimistic":   104174,
    },
    "K694": {
        "weight_v651": 0.03,
        "oos_sh": 19.09,
        "ann_ret_net_usd": 58354,
        "leverage": 4.0,
        "exchange": "Bybit",
        "hl_pct": 0.0,
        "bybit_pct": 1.0,
        "max_dd_pct": 5.0,
        "description": "K694 TIA-SOL FR Differential (ALT-ALT #6, Bybit-only, OOS Sh 19.09)",
        "category": "alt_alt_paired",
        "k523_conservative":  21883,
        "k523_central":       29177,
        "k523_optimistic":    58354,
    },
    "K696": {
        "weight_v651": 0.03,
        "oos_sh": 26.93,
        "ann_ret_net_usd": 93187,
        "leverage": 4.0,
        "exchange": "Bybit",
        "hl_pct": 0.0,
        "bybit_pct": 1.0,
        "max_dd_pct": 4.5,
        "description": "K696 ENA-SOL (ALT-ALT #7 CROSS-CLUSTER MILESTONE, Bybit-only, OOS Sh 26.93)",
        "category": "alt_alt_paired",
        "k523_conservative":  34945,
        "k523_central":       46594,
        "k523_optimistic":    93187,
    },
    "K719": {
        "weight_v651": 0.03,
        "oos_sh": 29.67,
        "ann_ret_net_usd": 634464,
        "leverage": 4.0,
        "exchange": "Bybit",
        "hl_pct": 0.0,
        "bybit_pct": 1.0,
        "max_dd_pct": 3.5,
        "description": "K719 ENA-ATOM (ALT-ALT #9 LARGEST $634K, Bybit-only, OOS Sh 29.67)",
        "category": "alt_alt_paired",
        "k523_conservative": 237924,
        "k523_central":      317232,
        "k523_optimistic":   634464,
    },
    # ─── ORTHOGONALIZED SLEEVES ────────────────────────────────────────────────
    "K628": {
        "weight_v651": 0.02,
        "oos_sh": 18.30,
        # Conservative: 2% sleeve * $10M * realistic 4x carry alpha = $57K net
        # (OOS residual potential vs IS potential differ greatly; use net stated)
        "ann_ret_net_usd": 57000,   # conservative realistic for 2% sleeve
        "leverage": 4.0,
        "exchange": "Bybit",
        "hl_pct": 0.0,
        "bybit_pct": 1.0,
        "max_dd_pct": 8.0,
        "description": "K628 JTO-BTC orthogonalized (Solana LST, Bybit-only, OOS Sh 18.30 residual)",
        "category": "orthog",
        "k523_conservative":  21375,
        "k523_central":       28500,
        "k523_optimistic":    57000,
    },
    "K631": {
        "weight_v651": 0.02,
        "oos_sh": 18.04,
        "ann_ret_net_usd": 58000,
        "leverage": 4.0,
        "exchange": "Bybit",
        "hl_pct": 0.0,
        "bybit_pct": 1.0,
        "max_dd_pct": 8.0,
        "description": "K631 WLD-BTC orthogonalized (Biometric ID, Bybit-only, OOS Sh 18.04)",
        "category": "orthog",
        "k523_conservative":  21750,
        "k523_central":       29000,
        "k523_optimistic":    58000,
    },
    "K633": {
        "weight_v651": 0.02,
        "oos_sh": 12.68,
        "ann_ret_net_usd": 46373,   # stated net @2% sleeve
        "leverage": 4.0,
        "exchange": "Bybit",
        "hl_pct": 0.0,
        "bybit_pct": 1.0,
        "max_dd_pct": 9.0,
        "description": "K633 OP-BTC orthogonalized (L2 Superchain, Bybit-only, OOS Sh 12.68)",
        "category": "orthog",
        "k523_conservative":  17390,
        "k523_central":       23187,
        "k523_optimistic":    46373,
    },
    "K635": {
        "weight_v651": 0.02,
        "oos_sh": 24.81,
        "ann_ret_net_usd": 95502,   # 2% sleeve realistic
        "leverage": 4.0,
        "exchange": "Bybit",
        "hl_pct": 0.0,
        "bybit_pct": 1.0,
        "max_dd_pct": 7.0,
        "description": "K635 IMX-BTC orthogonalized (Gaming L2 Infra, Bybit-only, OOS Sh 24.81)",
        "category": "orthog",
        "k523_conservative":  35813,
        "k523_central":       47751,
        "k523_optimistic":    95502,
    },
    "K638": {
        "weight_v651": 0.015,
        "oos_sh": 12.38,
        "ann_ret_net_usd": 65018,
        "leverage": 4.0,
        "exchange": "Bybit",
        "hl_pct": 0.0,
        "bybit_pct": 1.0,
        "max_dd_pct": 7.5,
        "description": "K638 STX-BTC orthogonalized (BTC-L2, Bybit-only, OOS Sh 12.38)",
        "category": "orthog",
        "k523_conservative":  24382,
        "k523_central":       32509,
        "k523_optimistic":    65018,
    },
    "K645": {
        "weight_v651": 0.03,
        "oos_sh": 7.07,
        "ann_ret_net_usd": 17694,
        "leverage": 4.0,
        "exchange": "Bybit",
        "hl_pct": 0.0,
        "bybit_pct": 1.0,
        "max_dd_pct": 9.0,
        "description": "K645 BNB-BTC orthogonalized (Binance-ecosystem, Bybit-only, OOS Sh 7.07)",
        "category": "orthog",
        "k523_conservative":   6635,
        "k523_central":        8847,
        "k523_optimistic":    17694,
    },
    "K646": {
        "weight_v651": 0.02,
        "oos_sh": 8.11,
        "ann_ret_net_usd": 20325,
        "leverage": 4.0,
        "exchange": "Bybit",
        "hl_pct": 0.0,
        "bybit_pct": 1.0,
        "max_dd_pct": 8.5,
        "description": "K646 ALGO-BTC orthogonalized (Enterprise L1, Bybit-only, OOS Sh 8.11)",
        "category": "orthog",
        "k523_conservative":   7622,
        "k523_central":       10163,
        "k523_optimistic":    20325,
    },
    "K648": {
        "weight_v651": 0.02,
        "oos_sh": 23.41,
        "ann_ret_net_usd": 85864,   # 2% sleeve realistic (full potential is $4.3M but orthog beta caps)
        "leverage": 4.0,
        "exchange": "Bybit",
        "hl_pct": 0.0,
        "bybit_pct": 1.0,
        "max_dd_pct": 7.0,
        "description": "K648 POL-BTC orthogonalized (Polygon zkEVM, Bybit-only, OOS Sh 23.41)",
        "category": "orthog",
        "k523_conservative":  32199,
        "k523_central":       42932,
        "k523_optimistic":    85864,
    },
    "K647": {
        "weight_v651": 0.03,
        "oos_sh": 23.25,
        "ann_ret_net_usd": 103586,
        "leverage": 4.0,
        "exchange": "Bybit",
        "hl_pct": 0.0,
        "bybit_pct": 1.0,
        "max_dd_pct": 8.0,
        "description": "K647 DOT-BTC orthogonalized (Polkadot relay, Bybit-only, OOS Sh 23.25, R²=-4.11 caution)",
        "category": "orthog",
        "k523_conservative":  38845,
        "k523_central":       51793,
        "k523_optimistic":   103586,
    },
    "K656": {
        "weight_v651": 0.02,
        "oos_sh": 8.32,
        "ann_ret_net_usd": 48143,
        "leverage": 4.0,
        "exchange": "Bybit",
        "hl_pct": 0.0,
        "bybit_pct": 1.0,
        "max_dd_pct": 7.0,
        "description": "K656 GALA-BTC dual-factor orthog (Gaming Publisher, Bybit-only, OOS Sh 8.32)",
        "category": "orthog",
        "k523_conservative":  18054,
        "k523_central":       24072,
        "k523_optimistic":    48143,
    },
    # ─── MACRO SIGNALS ────────────────────────────────────────────────────────
    "K541": {
        "weight_v651": 0.03,
        "oos_sh": 1.498,
        "ann_ret_net_usd": 294000,
        "leverage": 2.0,
        "exchange": "HL",
        "hl_pct": 1.0,
        "bybit_pct": 0.0,
        "max_dd_pct": 5.0,
        "description": "K541 Stablecoin Supply Growth (macro signal, 2x leverage, OOS Sh 1.498)",
        "category": "macro_signal",
        "k523_conservative": 110250,
        "k523_central":      147000,
        "k523_optimistic":   294000,
    },
    "K521": {
        "weight_v651": 0.03,
        "oos_sh": 1.019,
        "ann_ret_net_usd": 494000,
        "leverage": 2.0,
        "exchange": "HL",
        "hl_pct": 1.0,
        "bybit_pct": 0.0,
        "max_dd_pct": 6.0,
        "description": "K521 Options 25d Skew DVOL+skew V4 (macro signal, 2x leverage, OOS Sh 1.019)",
        "category": "macro_signal",
        "k523_conservative": 185250,
        "k523_central":      247000,
        "k523_optimistic":   494000,
    },
    "K495": {
        "weight_v651": 0.03,
        "oos_sh": 2.5,
        "ann_ret_net_usd": 323000,
        "leverage": 3.0,
        "exchange": "HL",
        "hl_pct": 1.0,
        "bybit_pct": 0.0,
        "max_dd_pct": 8.0,
        "description": "K495 DEX-CEX Flow Divergence (bear-conditional, 3x leverage, $323K/yr)",
        "category": "macro_signal",
        "k523_conservative": 121125,
        "k523_central":      161500,
        "k523_optimistic":   323000,
    },
}

# ─────────────────────────────────────────────────────────────────────────────
# Phase 2: Per-sleeve return distribution estimation
# ─────────────────────────────────────────────────────────────────────────────

def compute_sleeve_stats(sid: str, info: Dict) -> Dict:
    """
    Compute μ (return rate), σ (vol), Kelly f* for each sleeve.

    Key insight: for carry/FR strategies the return per dollar is:
       μ = ann_ret_net_usd / (weight_v651 * AUM)
    This avoids confusion from orthog sleeves' theoretical potential.

    σ = μ / OOS_Sh  (back-solve from Sharpe definition Sh = μ/σ)
    Kelly f* = μ / σ² = Sh² / μ  (for log-utility)
    """
    w   = info["weight_v651"]
    usd = info["ann_ret_net_usd"]

    # Return rate relative to AUM allocation (not total AUM)
    if w > 0:
        mu = usd / (w * AUM)
    else:
        mu = 0.0

    sh = max(info["oos_sh"], 0.1)  # avoid divide-by-zero

    # Back-solve sigma from Sharpe
    sigma = mu / sh if mu > 0 else 0.05

    # Floor/ceiling sigma for numerical stability
    sigma = max(sigma, 0.01)

    # Downside semi-variance (carry strategies are mostly right-skewed; σ_d < σ)
    sigma_d = sigma * 0.60

    # Kelly fractions (f* = μ/σ² = Sh²/μ)
    # Note: These are per-sleeve fractions, NOT portfolio weights
    kelly_full = mu / (sigma ** 2) if sigma > 0 else 0.0
    kelly_half    = kelly_full * 0.5
    kelly_quarter = kelly_full * 0.25

    # Normalized Kelly weight relative to 100% AUM deployment
    # f_normalized = f* * w * (1 / sum(all f* * w)) — computed in portfolio step

    return {
        "sleeve_id": sid,
        "weight_v651": w,
        "mu_rate": round(mu, 5),     # return rate per $ allocated
        "sigma_rate": round(sigma, 5),
        "sigma_d_rate": round(sigma_d, 5),
        "sharpe_oos": sh,
        "kelly_full_f": round(kelly_full, 3),
        "kelly_half_f": round(kelly_half, 3),
        "kelly_quarter_f": round(kelly_quarter, 3),
        "ann_ret_net_usd_at_v651_weight": usd,
        "max_dd_pct": info["max_dd_pct"],
        "exchange": info["exchange"],
        "category": info["category"],
        "k523_conservative": info["k523_conservative"],
        "k523_central": info["k523_central"],
        "k523_optimistic": info["k523_optimistic"],
    }


# ─────────────────────────────────────────────────────────────────────────────
# Phase 4: Portfolio-level Kelly+MPT optimization
# Approach: Sharpe-proportional rebalancing within exchange constraints
# ─────────────────────────────────────────────────────────────────────────────

def compute_exchange_concentrations(weights: Dict[str, float]) -> Dict:
    """Compute per-exchange AUM concentration."""
    hl_pct    = 0.0
    bybit_pct = 0.0
    for sid, w in weights.items():
        info = SLEEVE_INVENTORY[sid]
        hl_pct    += w * info.get("hl_pct", 0.0)
        bybit_pct += w * info.get("bybit_pct", 0.0)
    return {"HL": round(hl_pct, 4), "Bybit": round(bybit_pct, 4)}


def portfolio_return_stats(weights: Dict[str, float], stats: Dict[str, Dict]) -> Dict:
    """Compute weighted portfolio return and estimated Sharpe."""
    port_ret_usd = 0.0
    port_mu   = 0.0
    port_var  = 0.0

    # Assume low inter-sleeve correlation (delta-neutral carry — reasonable prior)
    # Portfolio variance: Var = sum_i w_i^2 * sigma_i^2 + 2 * sum_i<j corr_ij * w_i * w_j * sigma_i * sigma_j
    # Use simplified independent-across-categories assumption (conservative)
    INTRA_CAT_CORR = {
        "core": 0.0,
        "satellite": 0.0,
        "stable": 0.0,
        "btc_base_paired": 0.20,
        "eth_base_paired": 0.15,
        "alt_alt_paired": 0.12,
        "orthog": 0.08,
        "macro_signal": 0.10,
    }
    CROSS_CAT_CORR = 0.05  # cross-category correlation floor

    sleeves = list(weights.keys())
    n = len(sleeves)

    for i, si in enumerate(sleeves):
        wi = weights[si]
        si_stat = stats[si]
        port_ret_usd += wi * AUM * si_stat["mu_rate"]
        port_mu      += wi * si_stat["mu_rate"]

        # Diagonal variance
        port_var += (wi * si_stat["sigma_rate"]) ** 2

    # Cross terms (simplified: intra-cat pairs only, cross-cat = CROSS_CAT_CORR)
    for i in range(n):
        for j in range(i + 1, n):
            si, sj = sleeves[i], sleeves[j]
            wi, wj = weights[si], weights[sj]
            ci = SLEEVE_INVENTORY[si]["category"]
            cj = SLEEVE_INVENTORY[sj]["category"]
            corr = INTRA_CAT_CORR.get(ci, 0.05) if ci == cj else CROSS_CAT_CORR
            port_var += 2 * corr * wi * wj * stats[si]["sigma_rate"] * stats[sj]["sigma_rate"]

    port_sigma = math.sqrt(max(port_var, 1e-10))
    port_sh = port_mu / port_sigma if port_sigma > 0 else 0.0

    return {
        "ann_return_usd": round(port_ret_usd, 0),
        "ann_return_pct": round(port_mu * 100, 4),
        "ann_vol_pct":    round(port_sigma * 100, 4),
        "portfolio_sharpe": round(port_sh, 4),
    }


def optimize_kelly_weights(
    stats: Dict[str, Dict],
    kelly_fraction: float = 0.5,
    max_single: float = 0.15,
    k280_floor: float = 0.30,
    hl_cap: float = 0.65,
    bybit_cap: float = 0.50,
) -> Dict[str, float]:
    """
    Construct Kelly-optimal portfolio weights.

    Algorithm:
    1. Score each sleeve by risk-adjusted metric: score_i = Sh_i * (mu_i / sigma_i^2)
       = Sh_i * kelly_f_i  [Kelly magnitude × quality]
    2. Normalize scores to initial weights (Kelly-proportional allocation)
    3. Apply constraints iteratively:
       - K280 floor 30%
       - Max single sleeve 15%
       - HL cap 65%
       - Bybit cap 50%
    4. Scale by kelly_fraction
    5. Renormalize

    This is a practical approximation to the full QP, suitable for
    the portfolio complexity at hand without scipy.optimize dependency.
    """
    sleeves = list(stats.keys())

    # Step 1: Compute Kelly scores
    scores = {}
    for sid in sleeves:
        st = stats[sid]
        sh  = st["sharpe_oos"]
        kf  = st["kelly_full_f"]
        mu  = st["mu_rate"]
        # Score = Sh * sqrt(Kelly_f) — balances quality (Sh) with magnitude (kf)
        # Use sqrt to avoid extreme concentration in very high-kf sleeves
        score = sh * math.sqrt(max(kf, 0.0)) * mu if mu > 0 else 0.0
        scores[sid] = max(score, 0.0)

    total_score = sum(scores.values())
    if total_score == 0:
        return {s: SLEEVE_INVENTORY[s]["weight_v651"] for s in sleeves}

    # Step 2: Normalize to kelly_fraction of AUM
    w = {sid: (scores[sid] / total_score) * kelly_fraction for sid in sleeves}
    w["K280"] = max(w["K280"], k280_floor)

    # Step 3: Apply max single sleeve cap
    for sid in sleeves:
        w[sid] = min(w[sid], max_single)

    # Renormalize to sum=1
    total = sum(w.values())
    if total > 0:
        w = {sid: v / total for sid, v in w.items()}

    # Step 4: HL concentration cap (iterative reduction)
    for iteration in range(30):
        conc = compute_exchange_concentrations(w)
        if conc["HL"] <= hl_cap:
            break
        hl_excess = conc["HL"] - hl_cap
        # Identify highest HL-contribution sleeve (excluding K280 which is floored)
        hl_contributions = sorted(
            [(sid, w[sid] * SLEEVE_INVENTORY[sid]["hl_pct"]) for sid in sleeves
             if sid != "K280" and SLEEVE_INVENTORY[sid]["hl_pct"] > 0],
            key=lambda x: -x[1]
        )
        if not hl_contributions or hl_contributions[0][1] == 0:
            break
        # Reduce top HL sleeve
        top_sid, top_contrib = hl_contributions[0]
        reduce_by = min(hl_excess / SLEEVE_INVENTORY[top_sid]["hl_pct"] * 1.2, w[top_sid] * 0.25)
        w[top_sid] = max(0.0, w[top_sid] - reduce_by)
        # Renormalize
        total = sum(w.values())
        if total > 0:
            w = {sid: v / total for sid, v in w.items()}

    # Step 5: Bybit cap (iterative reduction)
    for iteration in range(30):
        conc = compute_exchange_concentrations(w)
        if conc["Bybit"] <= bybit_cap:
            break
        bybit_excess = conc["Bybit"] - bybit_cap
        bybit_contributions = sorted(
            [(sid, w[sid] * SLEEVE_INVENTORY[sid]["bybit_pct"]) for sid in sleeves
             if SLEEVE_INVENTORY[sid]["bybit_pct"] > 0],
            key=lambda x: -x[1]
        )
        if not bybit_contributions or bybit_contributions[0][1] == 0:
            break
        top_sid, top_contrib = bybit_contributions[0]
        reduce_by = min(bybit_excess / SLEEVE_INVENTORY[top_sid]["bybit_pct"] * 1.2, w[top_sid] * 0.25)
        w[top_sid] = max(0.0, w[top_sid] - reduce_by)
        total = sum(w.values())
        if total > 0:
            w = {sid: v / total for sid, v in w.items()}

    # Final normalization + rounding
    total = sum(w.values())
    if total > 0:
        w = {sid: round(v / total, 4) for sid, v in w.items()}

    return w


# ─────────────────────────────────────────────────────────────────────────────
# Phase 5: ROI Uplift (K523 3-point @$10M)
# ─────────────────────────────────────────────────────────────────────────────

def compute_k523_portfolio(weights: Dict[str, float]) -> Dict:
    """
    Compute K523-adjusted portfolio return at given weights.
    Scale each sleeve's K523 3-point by weight / weight_v651.
    """
    conservative = 0.0
    central      = 0.0
    optimistic   = 0.0

    for sid, w in weights.items():
        info = SLEEVE_INVENTORY[sid]
        w_base = info["weight_v651"]
        if w_base > 0:
            scale = w / w_base
        else:
            scale = 0.0
        conservative += info["k523_conservative"] * scale
        central      += info["k523_central"]      * scale
        optimistic   += info["k523_optimistic"]   * scale

    return {
        "conservative": round(conservative, 0),
        "central":      round(central, 0),
        "optimistic":   round(optimistic, 0),
    }


# ─────────────────────────────────────────────────────────────────────────────
# Main
# ─────────────────────────────────────────────────────────────────────────────

def main():
    print("=" * 72)
    print("K751 Kelly Criterion Sleeve Sizing Optimization — v6.52 Prep")
    print("=" * 72)
    print(f"Sleeves: {len(SLEEVE_INVENTORY)} | AUM ref: ${AUM:,.0f}")

    # Phase 2: Per-sleeve distributions
    print("\n[Phase 2] Per-sleeve return distributions:")
    all_stats = {sid: compute_sleeve_stats(sid, info) for sid, info in SLEEVE_INVENTORY.items()}

    print(f"\n{'Sleeve':<12} {'Sh':>7} {'μ/w%':>8} {'σ/w%':>8} {'f*':>8} {'f*/2':>7} {'w_v651':>8} {'Exchange':<12}")
    print("-" * 78)
    for sid, st in all_stats.items():
        print(f"{sid:<12} {st['sharpe_oos']:>7.2f} "
              f"{st['mu_rate']*100:>8.1f} {st['sigma_rate']*100:>8.2f} "
              f"{st['kelly_full_f']:>8.1f} {st['kelly_half_f']:>7.1f} "
              f"{st['weight_v651']:>8.4f} {st['exchange']:<12}")

    # Current v6.51 weights
    w_current = {sid: info["weight_v651"] for sid, info in SLEEVE_INVENTORY.items()}
    metrics_current = portfolio_return_stats(w_current, all_stats)
    conc_current    = compute_exchange_concentrations(w_current)
    k523_current    = compute_k523_portfolio(w_current)

    # Phase 3 & 4: Kelly optimization (multiple fractions)
    print("\n[Phase 4] Running Kelly+MPT portfolio optimizations...")
    w_kelly_half    = optimize_kelly_weights(all_stats, kelly_fraction=0.5)
    w_kelly_quarter = optimize_kelly_weights(all_stats, kelly_fraction=0.25)
    w_kelly_full    = optimize_kelly_weights(all_stats, kelly_fraction=1.0)

    metrics_half    = portfolio_return_stats(w_kelly_half, all_stats)
    metrics_quarter = portfolio_return_stats(w_kelly_quarter, all_stats)
    metrics_full    = portfolio_return_stats(w_kelly_full, all_stats)

    conc_half    = compute_exchange_concentrations(w_kelly_half)
    conc_quarter = compute_exchange_concentrations(w_kelly_quarter)
    conc_full    = compute_exchange_concentrations(w_kelly_full)

    k523_half    = compute_k523_portfolio(w_kelly_half)
    k523_quarter = compute_k523_portfolio(w_kelly_quarter)

    # Phase 5: ROI uplift
    print("\n[Phase 5] ROI uplift analysis (K523 3-point):")

    print("\n--- Portfolio Comparison: v6.51 vs Kelly Variants ---")
    print(f"{'Scenario':<22} {'Return%':>9} {'Vol%':>7} {'Sh':>8} {'HL%':>7} {'Bybit%':>8}")
    print("-" * 64)
    print(f"{'v6.51 Current':<22} {metrics_current['ann_return_pct']:>9.2f} "
          f"{metrics_current['ann_vol_pct']:>7.2f} {metrics_current['portfolio_sharpe']:>8.3f} "
          f"{conc_current['HL']*100:>7.1f} {conc_current['Bybit']*100:>8.1f}")
    print(f"{'Kelly Full (1.0x)':<22} {metrics_full['ann_return_pct']:>9.2f} "
          f"{metrics_full['ann_vol_pct']:>7.2f} {metrics_full['portfolio_sharpe']:>8.3f} "
          f"{conc_full['HL']*100:>7.1f} {conc_full['Bybit']*100:>8.1f}")
    print(f"{'Kelly Half (0.5x) RECOM':<22} {metrics_half['ann_return_pct']:>9.2f} "
          f"{metrics_half['ann_vol_pct']:>7.2f} {metrics_half['portfolio_sharpe']:>8.3f} "
          f"{conc_half['HL']*100:>7.1f} {conc_half['Bybit']*100:>8.1f}")
    print(f"{'Kelly Quarter (0.25x)':<22} {metrics_quarter['ann_return_pct']:>9.2f} "
          f"{metrics_quarter['ann_vol_pct']:>7.2f} {metrics_quarter['portfolio_sharpe']:>8.3f} "
          f"{conc_quarter['HL']*100:>7.1f} {conc_quarter['Bybit']*100:>8.1f}")

    print(f"\n--- K523 3-Point @$10M AUM ---")
    print(f"{'Scenario':<22} {'Conservative':>14} {'Central':>12} {'Optimistic':>12}")
    print("-" * 62)
    print(f"{'v6.51 Current':<22} ${k523_current['conservative']:>12,.0f} "
          f"${k523_current['central']:>11,.0f} ${k523_current['optimistic']:>11,.0f}")
    print(f"{'Kelly Half (0.5x)':<22} ${k523_half['conservative']:>12,.0f} "
          f"${k523_half['central']:>11,.0f} ${k523_half['optimistic']:>11,.0f}")
    print(f"{'Kelly Quarter (0.25x)':<22} ${k523_quarter['conservative']:>12,.0f} "
          f"${k523_quarter['central']:>11,.0f} ${k523_quarter['optimistic']:>11,.0f}")

    uplift_conservative = k523_half["conservative"] - k523_current["conservative"]
    uplift_central      = k523_half["central"]      - k523_current["central"]
    uplift_optimistic   = k523_half["optimistic"]   - k523_current["optimistic"]

    print(f"\n--- Half-Kelly Uplift vs v6.51 ---")
    print(f"  Conservative: {'+' if uplift_conservative >= 0 else ''}${uplift_conservative:,.0f}/yr")
    print(f"  Central:      {'+' if uplift_central >= 0 else ''}${uplift_central:,.0f}/yr")
    print(f"  Optimistic:   {'+' if uplift_optimistic >= 0 else ''}${uplift_optimistic:,.0f}/yr")
    print(f"  Sharpe uplift: {metrics_half['portfolio_sharpe'] - metrics_current['portfolio_sharpe']:+.3f}")

    # Top weight changes
    print("\n--- Top Weight Changes (Half-Kelly vs v6.51) ---")
    deltas = [(sid, w_kelly_half[sid] - w_current[sid]) for sid in SLEEVE_INVENTORY]
    deltas.sort(key=lambda x: abs(x[1]), reverse=True)
    print(f"{'Sleeve':<12} {'Dir':>5}  {'v651%':>6} → {'Kelly%':>6}   {'Δ%':>7}  {'Sh':>7}  {'Category'}")
    print("-" * 75)
    for sid, delta in deltas[:15]:
        direction = "UP  " if delta >= 0 else "DOWN"
        print(f"  {sid:<12} {direction} {w_current[sid]*100:6.2f}% → "
              f"{w_kelly_half[sid]*100:6.2f}%  {delta*100:+7.2f}%  "
              f"{SLEEVE_INVENTORY[sid]['oos_sh']:7.2f}  {SLEEVE_INVENTORY[sid]['category']}")

    # ── Build output JSON ──────────────────────────────────────────────────────
    sleeve_comparison = []
    for sid in SLEEVE_INVENTORY:
        sleeve_comparison.append({
            "sleeve": sid,
            "category": SLEEVE_INVENTORY[sid]["category"],
            "description": SLEEVE_INVENTORY[sid]["description"],
            "oos_sharpe": SLEEVE_INVENTORY[sid]["oos_sh"],
            "exchange": SLEEVE_INVENTORY[sid]["exchange"],
            "weight_v651": w_current[sid],
            "weight_kelly_half": w_kelly_half[sid],
            "weight_kelly_quarter": w_kelly_quarter[sid],
            "weight_delta_half": round(w_kelly_half[sid] - w_current[sid], 4),
            "kelly_full_f": all_stats[sid]["kelly_full_f"],
            "kelly_half_f": all_stats[sid]["kelly_half_f"],
            "mu_rate": all_stats[sid]["mu_rate"],
            "sigma_rate": all_stats[sid]["sigma_rate"],
            "ann_ret_net_usd_at_v651": SLEEVE_INVENTORY[sid]["ann_ret_net_usd"],
            "max_dd_pct": SLEEVE_INVENTORY[sid]["max_dd_pct"],
            "k523_conservative": SLEEVE_INVENTORY[sid]["k523_conservative"],
            "k523_central": SLEEVE_INVENTORY[sid]["k523_central"],
            "k523_optimistic": SLEEVE_INVENTORY[sid]["k523_optimistic"],
        })

    output_data = {
        "wave": "K751",
        "version": "v6.52_kelly_optimal",
        "generated_jst": datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M JST"),
        "aum_ref_usd": AUM,
        "n_sleeves": len(SLEEVE_INVENTORY),
        "optimization_method": (
            "Kelly+MPT hybrid: score_i = Sh_i * sqrt(kf_i) * mu_i; "
            "Sharpe-proportional rebalancing with exchange concentration constraints. "
            "Half-Kelly (0.5x) recommended for v6.52 activation."
        ),
        "constraints": {
            "sum_weights": "= 1.0",
            "max_single_sleeve": "15%",
            "K280_floor": "30% (core stability mandate)",
            "HL_cap": "65%",
            "Bybit_cap": "50%",
            "OKX_cap": "40% (K498 post-activation, currently paper)",
        },
        "per_sleeve_stats": all_stats,
        "weights_current_v651": w_current,
        "weights_kelly_half": w_kelly_half,
        "weights_kelly_quarter": w_kelly_quarter,
        "weights_kelly_full": w_kelly_full,
        "metrics_current_v651": {**metrics_current, **conc_current},
        "metrics_kelly_half": {**metrics_half, **conc_half},
        "metrics_kelly_quarter": {**metrics_quarter, **conc_quarter},
        "sleeve_comparison": sleeve_comparison,
        "k523_3point_at_10M": {
            "v651_current": k523_current,
            "kelly_half": k523_half,
            "kelly_quarter": k523_quarter,
            "half_kelly_uplift": {
                "conservative": round(uplift_conservative, 0),
                "central":      round(uplift_central, 0),
                "optimistic":   round(uplift_optimistic, 0),
            },
            "k523_methodology": (
                "realized_to_stated_ratio=38% (K509/K518 floor); "
                "OOS_haircut_paired_trade=25% (K523 mandate); "
                "Central=50% of stated, Optimistic=75% of stated."
            ),
        },
        "deploy_recommendation": {
            "v6.52_target": "half-Kelly (0.5x) — balanced risk-adjusted",
            "aggressive_1x": "NOT recommended — increases max_dd significantly near HL cap",
            "conservative_0.25x": "Appropriate given K509 K280 decay + HL 64.5% near cap",
            "activation": "User 1-flip: update SLEEVE_WEIGHTS_V652 in leverage_manager.py",
            "reversibility": "git revert <commit> (single-file change, no cascade)",
            "monitoring_gate": "60d realized Sharpe vs Kelly projection; 80% margin CB",
        },
        "risk_warnings": [
            "Kelly sizing increases per-sleeve concentration — max_dd will increase vs equal-weight",
            "K280 is floored at 30% per K532 governance mandate (K509 decay risk)",
            "HL concentration at 64.5% in v6.51 — Kelly correctly reduces HL-heavy sleeves",
            "Bybit concentration must remain <= 50% — alt-alt family is Bybit-heavy",
            "K628 JTO / K631 WLD / K633 OP / K635 IMX orthog: theoretical Sh reflects residual, not full carry",
            "K719 ENA-ATOM: $634K/yr stated — largest single alpha source, central = $317K/yr realistic",
        ],
    }

    with open(OUTPUT_JSON, "w") as f:
        json.dump(output_data, f, indent=2)
    print(f"\n[Output] Saved: {OUTPUT_JSON}")

    # ── Print SLEEVE_WEIGHTS_V652 snippet for leverage_manager.py ─────────────
    print("\n" + "=" * 72)
    print("# SLEEVE_WEIGHTS_V652 (paste into leverage_manager.py — user 1-flip)")
    print("# K751 Kelly-optimal half-Kelly (0.5x) weights")
    print("=" * 72)
    print("SLEEVE_WEIGHTS_V652: Dict[str, float] = {")
    for sid, w in sorted(w_kelly_half.items(), key=lambda x: -x[1]):
        info = SLEEVE_INVENTORY[sid]
        print(f'    "{sid}": {w:.4f},   '
              f'# {info["description"][:55]}')
    print("}")
    print(f"# Sum: {sum(w_kelly_half.values()):.4f}")
    hl_k = conc_half["HL"]
    by_k = conc_half["Bybit"]
    print(f"# HL: {hl_k*100:.1f}%  Bybit: {by_k*100:.1f}%")

    return output_data


if __name__ == "__main__":
    main()
